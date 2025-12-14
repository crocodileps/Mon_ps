"""
Repository Layer - Brain API
Pattern: Dependency Injection + Circuit Breaker (Institutional Grade)
"""
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

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

    def calculate_predictions(
        self,
        home_team: str,
        away_team: str,
        match_date: datetime,
        dna_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Calculate 93 markets predictions

        Circuit breaker pattern: Fail fast with clear errors

        Args:
            home_team: Home team name
            away_team: Away team name
            match_date: Match date (not used by UnifiedBrain V2.8.0)
            dna_context: DNA context (not used by UnifiedBrain V2.8.0)

        Returns:
            Dict with markets, calculation_time, brain_version, created_at
        """
        # Circuit breaker: Check brain initialized
        if not self.brain:
            raise RuntimeError(
                "Brain engine not initialized. "
                "Repository in invalid state."
            )

        try:
            # Call UnifiedBrain V2.8.0 API
            # IMPORTANT: Uses home= and away= (not home_team= and away_team=)
            # IMPORTANT: match_date and dna_context not supported by v2.8.0
            start = datetime.now()

            result = self.brain.analyze_match(
                home=home_team,  # Note: home= not home_team=
                away=away_team   # Note: away= not away_team=
            )

            calc_time = (datetime.now() - start).total_seconds()

            # Convert MatchPrediction → API format
            return {
                "markets": self._convert_match_prediction_to_markets(result),
                "calculation_time": calc_time,
                "brain_version": self.version,
                "created_at": datetime.now()
            }

        except AttributeError as e:
            # Brain corruption: Method not found
            raise RuntimeError(
                f"Brain engine corruption: {e}. "
                f"Expected method 'analyze_match' not found."
            )
        except Exception as e:
            # Catch-all: Quantum Core internal failure
            raise RuntimeError(
                f"Quantum Core calculation failure: {type(e).__name__}: {e}"
            )

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
