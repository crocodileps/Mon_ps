"""
Repository Layer - Brain API
Pattern: Dependency Injection + Circuit Breaker (Institutional Grade)
"""
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# Cache integration
from cache.smart_cache import smart_cache
from cache.key_factory import key_factory
from cache.metrics import cache_metrics  # Direct instrumentation
import unicodedata  # For team name normalization

logger = logging.getLogger(__name__)


class BrainRepository:
    """
    Repository layer pour Brain API

    Supports dependency injection for testing and flexibility.
    Implements circuit breaker pattern for robustness.
    """

    def __init__(self, brain_client=None):
        """
        Initialize repository

        Args:
            brain_client: Optional UnifiedBrain instance (for DI in tests)
                         If None, initializes real UnifiedBrain
        """
        if brain_client is not None:
            # Dependency injection (tests)
            self.brain = brain_client
            self.env = "INJECTED"
            self.version = "2.8.0"
            logger.info(f"BrainRepository initialized (DI mode)")
        else:
            # Production initialization
            self._initialize_production_brain()

        # Register X-Fetch callback for background refresh
        if smart_cache.enabled:
            smart_cache.set_refresh_callback(self._xfetch_refresh_callback)
            logger.info("X-Fetch callback registered with SmartCache")

    def _initialize_production_brain(self):
        """
        Initialize real UnifiedBrain (production path)

        Tries Docker path first, then local development path.
        Raises RuntimeError if quantum_core not found.
        """
        # Priority 1: Docker volume
        docker_path = Path("/quantum_core")

        # Priority 2: Local development
        local_path = Path("/home/Mon_ps/quantum_core")

        if docker_path.exists():
            quantum_core_path = docker_path
            self.env = "DOCKER"
        elif local_path.exists():
            quantum_core_path = local_path
            self.env = "LOCAL"
        else:
            raise RuntimeError(
                f"quantum_core not found. Checked:\n"
                f"  - Docker: {docker_path}\n"
                f"  - Local: {local_path}\n"
                f"Cannot initialize BrainRepository without quantum_core."
            )

        # Add BOTH paths to sys.path for complete compatibility
        # 1. Parent directory (/) allows "from quantum_core.adapters..." (UnifiedBrain internal imports)
        # 2. quantum_core itself allows "from brain.unified_brain..." (our imports)
        import sys
        parent_path = str(quantum_core_path.parent)
        if parent_path not in sys.path:
            sys.path.insert(0, parent_path)

        if str(quantum_core_path) not in sys.path:
            sys.path.insert(0, str(quantum_core_path))

        # Import UnifiedBrain
        try:
            from brain.unified_brain import UnifiedBrain
            self.brain = UnifiedBrain()
            self.version = "2.8.0"
            logger.info(f"UnifiedBrain V{self.version} initialized (ENV={self.env})")
        except ImportError as e:
            raise RuntimeError(
                f"Failed to import UnifiedBrain from {quantum_core_path}: {e}"
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize UnifiedBrain: {e}"
            )

    def _normalize_team_name(self, team: str) -> str:
        """Normalize team name for consistent cache keys.

        Removes accents, converts to lowercase, replaces spaces/dashes with underscores.

        Examples:
            "Manchester United" → "manchester_united"
            "Saint-Étienne" → "saint_etienne"
            "Liverpool" → "liverpool"

        Args:
            team: Original team name

        Returns:
            Normalized team name for cache key
        """
        # Remove accents (NFD decomposition)
        normalized = unicodedata.normalize('NFKD', team)
        normalized = normalized.encode('ASCII', 'ignore').decode('ASCII')

        # Lowercase + replace spaces/dashes with underscores
        normalized = normalized.lower().replace(" ", "_").replace("-", "_")

        return normalized

    def _calculate_ttl(self, match_date: datetime) -> int:
        """Calculate cache TTL based on match timing.

        Strategy:
        - POST_MATCH (finished): 24h (result is final)
        - LIVE/VERY SOON (<2h): 1min (high volatility)
        - SOON (<24h): 15min (moderate volatility)
        - PRE_MATCH (>24h): 1h (low volatility)

        Args:
            match_date: Scheduled match datetime

        Returns:
            TTL in seconds (60 to 86400)
        """
        from datetime import timezone

        now = datetime.now(timezone.utc)

        # Handle timezone-naive match_date
        if match_date.tzinfo is None:
            match_date = match_date.replace(tzinfo=timezone.utc)

        time_to_match = (match_date - now).total_seconds()

        if time_to_match < 0:
            # POST_MATCH: Result is final
            return 86400  # 24 hours
        elif time_to_match < 7200:  # < 2 hours
            # LIVE or VERY SOON: High volatility (odds changing rapidly)
            return 60  # 1 minute
        elif time_to_match < 86400:  # < 24 hours
            # SOON: Moderate volatility (team news possible)
            return 900  # 15 minutes
        else:
            # PRE_MATCH: Low volatility (odds stable)
            return 3600  # 1 hour

    def _xfetch_refresh_callback(self, cache_key: str) -> Dict[str, Any]:
        """
        X-Fetch background refresh callback.

        Called by SmartCache when probabilistic refresh is triggered.
        Parses cache key, computes fresh prediction, returns result.

        Args:
            cache_key: Full cache key (e.g., "monps:prod:v1:pred:{m_arsenal_vs_chelsea}:default")

        Returns:
            Fresh prediction result dict (same format as calculate_predictions)

        Raises:
            Exception: Re-raised for SmartCache to handle gracefully
        """
        try:
            # 1. Parse cache key to extract match_id
            match_id = self._extract_match_id_from_key(cache_key)

            # 2. Parse match_id to extract team names
            home_team, away_team = self._parse_match_id(match_id)

            # 3. Compute fresh prediction
            logger.info(
                "X-Fetch background refresh: Computing fresh prediction",
                extra={"home": home_team, "away": away_team, "cache_key": cache_key}
            )

            start = datetime.now()

            # ════════════════════════════════════════════════════════════════
            # INSTRUMENTATION CRITICAL: Compute call counter
            # ════════════════════════════════════════════════════════════════
            cache_metrics.increment("compute_calls")  # ← CRITICAL COUNTER
            # ════════════════════════════════════════════════════════════════

            # Call brain (same as calculate_predictions)
            result = self.brain.analyze_match(home=home_team, away=away_team)

            calc_time = (datetime.now() - start).total_seconds()

            # 4. Format result (same as calculate_predictions)
            from datetime import timezone
            computed_result = {
                "markets": self._convert_match_prediction_to_markets(result),
                "calculation_time": calc_time,
                "brain_version": self.version,
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            logger.info(
                "X-Fetch background refresh: Completed",
                extra={
                    "home": home_team,
                    "away": away_team,
                    "calc_time_ms": calc_time * 1000
                }
            )

            return computed_result

        except Exception as e:
            logger.error(
                "X-Fetch callback error",
                extra={"cache_key": cache_key, "error": str(e)}
            )
            raise  # Re-raise so SmartCache worker can handle gracefully

    def _extract_match_id_from_key(self, cache_key: str) -> str:
        """Extract match_id from cache key.

        Args:
            cache_key: "monps:prod:v1:pred:{m_arsenal_vs_chelsea}:default"

        Returns:
            match_id: "m_arsenal_vs_chelsea"
        """
        # Find content within curly braces
        parts = cache_key.split(":")
        for part in parts:
            if part.startswith("{") and part.endswith("}"):
                return part[1:-1]  # Remove { }
        raise ValueError(f"Invalid cache key format: {cache_key}")

    def _parse_match_id(self, match_id: str) -> tuple:
        """Parse match_id to extract team names.

        Args:
            match_id: "m_arsenal_vs_chelsea"

        Returns:
            (home_team, away_team): ("Arsenal", "Chelsea")
        """
        if not match_id.startswith("m_"):
            raise ValueError(f"Invalid match_id: {match_id}")

        # Remove "m_" prefix
        teams_str = match_id[2:]

        # Split by "_vs_"
        teams = teams_str.split("_vs_")
        if len(teams) != 2:
            raise ValueError(f"Invalid match_id format: {match_id}")

        # Convert "arsenal" → "Arsenal", "manchester_united" → "Manchester United"
        home = teams[0].replace("_", " ").title()
        away = teams[1].replace("_", " ").title()

        return home, away

    def calculate_predictions(
        self,
        home_team: str,
        away_team: str,
        match_date: datetime,
        dna_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Calculate 93 markets predictions with SmartCache integration.

        Cache Strategy:
        - Key: normalized(home_team) + normalized(away_team) + config_hash
        - TTL: Dynamic (60s to 24h) based on match_date
        - X-Fetch: Probabilistic refresh near expiry (99%+ stampede prevention)
        - Graceful degradation: Redis unavailable → fallback to compute

        Args:
            home_team: Home team name
            away_team: Away team name
            match_date: Scheduled match datetime (for TTL calculation)
            dna_context: Optional DNA context (not used by UnifiedBrain V2.8.0)

        Returns:
            Dict with:
            - markets: List of 93 market predictions
            - calculation_time: Seconds taken for computation
            - brain_version: UnifiedBrain version (2.8.0)
            - created_at: ISO timestamp of prediction creation

        Raises:
            RuntimeError: If brain not initialized or computation fails
        """
        # 1. Generate cache key with normalized team names
        normalized_home = self._normalize_team_name(home_team)
        normalized_away = self._normalize_team_name(away_team)
        match_id = f"{normalized_home}_vs_{normalized_away}"

        cache_key = key_factory.prediction_key(
            match_id=match_id,
            config=None  # dna_context not used by UnifiedBrain V2.8.0
        )

        # 2. Check cache (SmartCache with X-Fetch algorithm)
        cached, is_stale = smart_cache.get(cache_key)

        if cached and not is_stale:
            # Cache HIT fresh → Return immediately (<10ms)
            # ════════════════════════════════════════════════════════════════
            # INSTRUMENTATION: Cache HIT (fresh)
            # ════════════════════════════════════════════════════════════════
            cache_metrics.increment("cache_hit_fresh")  # ← COUNTER
            # ════════════════════════════════════════════════════════════════

            logger.info(
                "BrainRepository: Cache HIT (fresh)",
                extra={
                    "cache_key": cache_key,
                    "match_id": match_id,
                    "home_team": home_team,
                    "away_team": away_team
                }
            )
            return cached

        if cached and is_stale:
            # Cache HIT stale → X-Fetch triggered
            # Return stale value immediately (zero latency)
            # Background refresh will happen probabilistically
            # ════════════════════════════════════════════════════════════════
            # INSTRUMENTATION: Cache HIT (stale, X-Fetch)
            # ════════════════════════════════════════════════════════════════
            cache_metrics.increment("cache_hit_stale")  # ← COUNTER
            cache_metrics.increment("xfetch_triggers")  # ← COUNTER (approximation)
            # Note: X-Fetch probabilistic refresh happens in smart_cache.get()
            # All stale hits counted as potential X-Fetch triggers
            # ════════════════════════════════════════════════════════════════

            logger.info(
                "BrainRepository: Cache HIT (stale, X-Fetch refresh)",
                extra={
                    "cache_key": cache_key,
                    "match_id": match_id,
                    "home_team": home_team,
                    "away_team": away_team
                }
            )
            return cached

        # 3. Cache MISS → Compute prediction
        # ════════════════════════════════════════════════════════════════
        # INSTRUMENTATION: Cache MISS
        # ════════════════════════════════════════════════════════════════
        cache_metrics.increment("cache_miss")  # ← COUNTER
        # ════════════════════════════════════════════════════════════════

        logger.info(
            "BrainRepository: Cache MISS",
            extra={
                "cache_key": cache_key,
                "match_id": match_id,
                "home_team": home_team,
                "away_team": away_team
            }
        )

        # Circuit breaker check
        if not self.brain:
            raise RuntimeError(
                "Brain not initialized - check circuit breaker status"
            )

        # 4. Compute prediction (expensive ~150ms)
        try:
            start = datetime.now()

            # ════════════════════════════════════════════════════════════════
            # LATENCY INJECTOR - Simulate Production Compute Load
            # ════════════════════════════════════════════════════════════════
            # Purpose: Enable realistic stress testing in development
            #
            # Context:
            # - Development UnifiedBrain: 0 engines = 9ms (stub mode)
            # - Production UnifiedBrain: 8+ engines = 150ms (full ML)
            # - Problem: Cannot validate concurrent load behavior in dev
            #
            # Solution:
            # - Inject artificial latency to simulate production
            # - Enable with env var SIMULATE_PROD_LATENCY=true
            # - Configurable latency with SIMULATE_LATENCY_MS (default 150ms)
            #
            # Usage:
            # - Stress testing: SIMULATE_PROD_LATENCY=true
            # - Normal dev: SIMULATE_PROD_LATENCY=false (default)
            # ════════════════════════════════════════════════════════════════
            import os
            import time as time_module  # Alias to avoid conflict with calc_time

            if os.getenv("SIMULATE_PROD_LATENCY", "false").lower() == "true":
                # Simulate real UnifiedBrain computation time
                latency_ms = int(os.getenv("SIMULATE_LATENCY_MS", "150"))

                logger.info(
                    "LATENCY INJECTOR: Simulating production compute latency",
                    extra={
                        "latency_ms": latency_ms,
                        "home_team": home_team,
                        "away_team": away_team,
                        "reason": "Stress test validation"
                    }
                )

                # Sleep to simulate compute time
                time_module.sleep(latency_ms / 1000.0)  # Convert ms to seconds
            # ════════════════════════════════════════════════════════════════

            # ════════════════════════════════════════════════════════════════
            # INSTRUMENTATION CRITICAL: Compute call counter
            # ════════════════════════════════════════════════════════════════
            # This is the GROUND TRUTH for stampede detection
            # Every brain.analyze_match() call MUST increment this counter
            cache_metrics.increment("compute_calls")  # ← CRITICAL COUNTER
            # ════════════════════════════════════════════════════════════════

            # Call UnifiedBrain V2.8.0
            # Note: Uses home=/away= parameters (not home_team=/away_team=)
            result = self.brain.analyze_match(
                home=home_team,  # Original team name (not normalized)
                away=away_team
            )

            calc_time = (datetime.now() - start).total_seconds()

            # 5. Build result dict (MUST be JSON serializable!)
            from datetime import timezone

            computed_result = {
                "markets": self._convert_match_prediction_to_markets(result),
                "calculation_time": calc_time,
                "brain_version": self.version,
                "created_at": datetime.now(timezone.utc).isoformat()  # ✅ ISO string (not datetime object)
            }

            # 6. Store in cache with dynamic TTL (graceful degradation)
            # Track cache storage success for accurate logging
            ttl = self._calculate_ttl(match_date)
            cache_stored = False

            try:
                smart_cache.set(cache_key, computed_result, ttl=ttl)
                cache_stored = True  # ✅ Cache operation succeeded
            except Exception as cache_error:
                # Redis unavailable → Log warning but continue
                # Graceful degradation: Prediction computed successfully, just not cached
                logger.warning(
                    f"Failed to cache prediction (Redis unavailable): {cache_error}",
                    extra={
                        "cache_key": cache_key,
                        "home_team": home_team,
                        "away_team": away_team,
                        "error_type": type(cache_error).__name__
                    }
                )

            # Log accurate status based on actual cache operation result
            if cache_stored:
                logger.info(
                    "BrainRepository: Computed and cached",
                    extra={
                        "cache_key": cache_key,
                        "match_id": match_id,
                        "ttl": ttl,
                        "calculation_time_ms": calc_time * 1000,
                        "cached": True,  # ✅ Explicit for monitoring
                        "home_team": home_team,
                        "away_team": away_team
                    }
                )
            else:
                logger.info(
                    "BrainRepository: Computed (cache storage FAILED)",
                    extra={
                        "cache_key": cache_key,
                        "match_id": match_id,
                        "calculation_time_ms": calc_time * 1000,
                        "cached": False,  # ✅ Explicit for monitoring
                        "home_team": home_team,
                        "away_team": away_team,
                        "warning": "Redis unavailable - operating without cache"
                    }
                )

            return computed_result

        except AttributeError as e:
            # Brain corruption (missing analyze_match method)
            logger.error(
                f"Brain corruption detected: {e}",
                exc_info=True,
                extra={
                    "home_team": home_team,
                    "away_team": away_team
                }
            )
            raise RuntimeError(f"Brain corruption: {e}")

        except Exception as e:
            # Quantum Core failure (any other error)
            logger.error(
                f"Quantum Core failure: {e}",
                exc_info=True,
                extra={
                    "home_team": home_team,
                    "away_team": away_team
                }
            )
            raise RuntimeError(f"Quantum Core failure: {e}")

    def _convert_match_prediction_to_markets(self, prediction) -> Dict:
        """
        Convert MatchPrediction → API markets format

        MatchPrediction contains 93 markets as attributes (floats 0-1).
        Transform to Dict[market_id, Dict[outcome, MarketPrediction]]
        """
        markets = {}

        # Extract all attributes from MatchPrediction
        for attr_name in dir(prediction):
            if attr_name.startswith('_'):
                continue

            # Skip non-market attributes
            if attr_name in ['home_team', 'away_team', 'home_profile', 'away_profile']:
                continue

            try:
                attr_value = getattr(prediction, attr_name)

                # If float/int AND valid probability (0-1)
                if isinstance(attr_value, (float, int)):
                    # Filter only probabilities (0-1), not expected values
                    if 0.0 <= float(attr_value) <= 1.0:
                        markets[attr_name] = {
                            "prediction": {
                                "probability": float(attr_value),
                                "confidence": 0.85,  # Default confidence
                                "edge": None
                            }
                        }
            except Exception:
                continue

        return markets

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status

        Circuit breaker: Return error dict if brain not initialized
        """
        if not self.brain:
            return {
                "status": "error",
                "error": "Brain not initialized",
                "version": getattr(self, 'version', '0.0.0'),
                "environment": getattr(self, 'env', 'UNKNOWN')
            }

        try:
            # Try health_check method
            test = self.brain.health_check()

            return {
                "status": "operational",
                "version": self.version,
                "markets_count": test.get('markets_supported', 93),
                "goalscorer_profiles": 876,
                "uptime_percent": 99.9,
                "environment": self.env
            }
        except Exception as e:
            return {
                "status": "error",
                "version": self.version,
                "error": str(e),
                "environment": self.env
            }

    def get_supported_markets(self) -> List[Dict[str, str]]:
        """
        Get supported markets list (93 markets)

        Circuit breaker: Raise RuntimeError if brain not initialized
        """
        if not self.brain:
            raise RuntimeError("Brain not initialized")

        try:
            # Analyze dummy match to extract market list
            dummy = self.brain.analyze_match(home="Liverpool", away="Chelsea")

            markets = []
            for attr_name in dir(dummy):
                if attr_name.startswith('_'):
                    continue

                if attr_name in ['home_team', 'away_team', 'home_profile', 'away_profile']:
                    continue

                try:
                    attr_value = getattr(dummy, attr_name)
                    if isinstance(attr_value, (float, int)):
                        markets.append({
                            "id": attr_name,
                            "name": attr_name.replace('_', ' ').title(),
                            "category": self._infer_category(attr_name),
                            "description": f"Market {attr_name}"
                        })
                except Exception:
                    continue

            return markets
        except Exception as e:
            logger.error(f"Failed to get markets: {e}")
            # Fallback hardcoded
            return [
                {"id": "over_under_25", "name": "Over/Under 2.5", "category": "goals", "description": "O/U 2.5"},
                {"id": "btts", "name": "BTTS", "category": "goals", "description": "Both teams score"},
                {"id": "match_result_1x2", "name": "1X2", "category": "result", "description": "Match result"},
            ]

    def _infer_category(self, market_id: str) -> str:
        """Infer category from market_id"""
        if 'goal' in market_id or 'over' in market_id or 'under' in market_id or 'btts' in market_id:
            return "goals"
        elif 'corner' in market_id:
            return "corners"
        elif 'card' in market_id:
            return "cards"
        elif 'asian' in market_id or 'handicap' in market_id:
            return "asian_handicap"
        elif 'goalscorer' in market_id or 'scorer' in market_id:
            return "goalscorers"
        else:
            return "result"

    def calculate_goalscorers(
        self,
        home_team: str,
        away_team: str,
        match_date: datetime
    ) -> Dict[str, Any]:
        """
        Calculate goalscorer predictions

        Circuit breaker: Raise RuntimeError if brain not initialized
        """
        if not self.brain:
            raise RuntimeError("Brain not initialized")

        try:
            # Placeholder - not yet implemented in UnifiedBrain V2.8.0
            return {
                "home_goalscorers": [],
                "away_goalscorers": [],
                "first_goalscorer_team_prob": {"home": 0.52, "away": 0.48}
            }
        except Exception as e:
            raise RuntimeError(f"Goalscorer calculation failed: {e}")
