"""
VIX Circuit Breaker - Protection Backend Panic Prolongée
Grade: Institutional Hedge Fund Perfect

Protège backend contre VIX panic prolongée via circuit breaker intelligent
avec state machine 3 modes et hystérésis anti flip-flop.

Architecture:
  - Rolling window 30min (1800 samples @ 1s)
  - State machine: NORMAL → HIGH_VOLATILITY → CIRCUIT_OPEN
  - Hystérésis 20% évite oscillations
  - Adaptive TTL selon mode

Example:
    >>> from cache.vix_circuit_breaker import vix_circuit_breaker
    >>>
    >>> # Normal operation
    >>> ttl, strategy = vix_circuit_breaker.get_adaptive_ttl("panic")
    >>> # → (0, "bypass") en mode NORMAL
    >>>
    >>> # After 15min sustained panic
    >>> # → (5, "adaptive") en mode HIGH_VOLATILITY
"""

from enum import Enum
from collections import deque
from datetime import datetime, timezone
from typing import Optional, Dict, Tuple
import time
import structlog

# Try relative import first, fall back to direct import for testing
try:
    from .adaptive_panic_quota import AdaptivePanicQuota, PanicMode
except ImportError:
    from adaptive_panic_quota import AdaptivePanicQuota, PanicMode

logger = structlog.get_logger()


# ═══════════════════════════════════════════════════════════════
# REDIS KEYS - Panic State Management (Phase 3)
# ═══════════════════════════════════════════════════════════════

PANIC_START_TS_KEY = "brain:panic_start_ts"

# Dead Man's Switch: TTL basé sur tier3 max (high_stakes) + marge sécurité
# tier3_high_stakes = 360 min = 6h
# safety_margin = 4x → 24h
# Si système crash, clé expire automatiquement après 24h
PANIC_TS_TTL_SECONDS = 86400  # 24 heures


class CircuitBreakerMode(Enum):
    """
    Circuit breaker operation modes

    NORMAL: Operation standard, VIX panic → bypass
    HIGH_VOLATILITY: Panic prolongée, VIX panic → TTL=5s
    CIRCUIT_OPEN: Panic extrême, VIX panic → TTL=10s
    """
    NORMAL = "normal"
    HIGH_VOLATILITY = "high_volatility"
    CIRCUIT_OPEN = "circuit_open"


class VIXCircuitBreaker:
    """
    VIX Panic Circuit Breaker avec Hystérésis

    Protège backend contre panic prolongée en adaptant stratégie cache.

    Rolling Window:
      - 30min (1800 seconds)
      - 1 sample/second
      - Tracks panic ratio

    State Machine:
      NORMAL → HIGH_VOLATILITY: panic_ratio > 50%
      HIGH_VOLATILITY → NORMAL: panic_ratio < 30%
      HIGH_VOLATILITY → CIRCUIT_OPEN: panic_ratio > 80%
      CIRCUIT_OPEN → HIGH_VOLATILITY: panic_ratio < 60%

    Hystérésis:
      Enter HIGH_VOL: 50% (montée)
      Exit HIGH_VOL: 30% (descente)
      → Delta 20% évite flip-flop

    TTL Strategy:
      NORMAL mode:
        - panic → TTL=0 (bypass)
        - warning/normal → base_ttl

      HIGH_VOLATILITY mode:
        - panic → TTL=5s (adaptive)
        - warning → TTL=10s
        - normal → base_ttl

      CIRCUIT_OPEN mode:
        - panic → TTL=10s (maximum protection)
        - warning → TTL=30s
        - normal → TTL=60s

    Thread-Safe: Yes (deque operations atomic)
    Performance: O(1) amortized operations
    Memory: O(window_seconds) = 1800 bytes
    """

    def __init__(
        self,
        redis_client=None,
        window_seconds: int = 1800,
        panic_threshold_enter: float = 0.50,
        panic_threshold_exit: float = 0.30,
        circuit_open_threshold: float = 0.80
    ):
        """
        Initialize VIX Circuit Breaker

        Args:
            redis_client: Optional Redis client for panic timestamp persistence
            window_seconds: Rolling window size (default 1800 = 30min)
            panic_threshold_enter: Ratio to enter HIGH_VOL (0.50 = 50%)
            panic_threshold_exit: Ratio to exit HIGH_VOL (0.30 = 30%)
            circuit_open_threshold: Ratio to open circuit (0.80 = 80%)

        Raises:
            ValueError: Si thresholds invalides ou pas d'hystérésis
        """
        # Redis client for panic timestamp persistence (Phase 3)
        self.redis = redis_client
        # Validate thresholds
        if not (0 <= panic_threshold_enter <= 1):
            raise ValueError(
                f"panic_threshold_enter must be 0-1, got {panic_threshold_enter}"
            )
        if not (0 <= panic_threshold_exit <= 1):
            raise ValueError(
                f"panic_threshold_exit must be 0-1, got {panic_threshold_exit}"
            )
        if not (0 <= circuit_open_threshold <= 1):
            raise ValueError(
                f"circuit_open_threshold must be 0-1, got {circuit_open_threshold}"
            )

        # Validate hystérésis
        if panic_threshold_exit >= panic_threshold_enter:
            raise ValueError(
                f"panic_threshold_exit ({panic_threshold_exit}) must be < "
                f"panic_threshold_enter ({panic_threshold_enter}) for hystérésis"
            )

        self.window_seconds = window_seconds
        self.panic_threshold_enter = panic_threshold_enter
        self.panic_threshold_exit = panic_threshold_exit
        self.circuit_open_threshold = circuit_open_threshold

        # Rolling window: deque with maxlen (auto-eviction)
        # Stores 0 (not panic) or 1 (panic)
        self.panic_history = deque(maxlen=window_seconds)

        # Current state
        self.mode = CircuitBreakerMode.NORMAL

        # Metrics
        self.mode_changes = []
        self.last_mode_change = None

        # ═══════════════════════════════════════════════════════════════
        # PHASE 3: Adaptive Panic Quota Integration
        # Stateless module for context-aware TTL calculation
        # ═══════════════════════════════════════════════════════════════
        self._panic_quota = AdaptivePanicQuota()

        # ═══════════════════════════════════════════════════════════════
        # Logging optimization: Track last state to log only on change
        # Prevents 8.6M logs/day in high-frequency production
        # ═══════════════════════════════════════════════════════════════
        self._last_logged_mode: Optional[str] = None
        self._last_logged_tier: Optional[int] = None

        logger.info(
            "VIXCircuitBreaker initialized",
            window_seconds=window_seconds,
            redis_enabled=redis_client is not None,
            panic_quota_enabled=True,
            thresholds={
                'enter_high_vol': panic_threshold_enter,
                'exit_high_vol': panic_threshold_exit,
                'circuit_open': circuit_open_threshold,
                'hysteresis': panic_threshold_enter - panic_threshold_exit
            }
        )

    def record_panic_status(self, vix_status: str) -> None:
        """
        Record VIX status dans rolling window

        Args:
            vix_status: 'panic' | 'warning' | 'normal'

        Side Effects:
            - Appends to panic_history
            - May trigger state transition

        Thread-Safe: Yes (deque.append atomic)
        Performance: O(1) + O(n) state check (amortized O(1))
        """
        # Convert to binary (1 = panic, 0 = not panic)
        is_panic = 1 if vix_status == "panic" else 0

        # Append to rolling window
        self.panic_history.append(is_panic)

        # Update state machine
        self._update_mode()

    def _calculate_panic_ratio(self) -> float:
        """
        Calculate panic % dans rolling window

        Returns:
            Ratio 0.0-1.0 (ex: 0.45 = 45% panic)

        Performance: O(n) sum, but highly optimized in CPython
        """
        if not self.panic_history:
            return 0.0

        panic_count = sum(self.panic_history)
        total_count = len(self.panic_history)

        return panic_count / total_count

    def _update_mode(self) -> None:
        """
        Update state machine avec hystérésis

        State Transitions:
            NORMAL → HIGH_VOLATILITY: panic > 50%
            HIGH_VOLATILITY → NORMAL: panic < 30%
            HIGH_VOLATILITY → CIRCUIT_OPEN: panic > 80%
            CIRCUIT_OPEN → HIGH_VOLATILITY: panic < 60%

        Hystérésis prevents rapid oscillations:
            Without: 50% panic → enter, 49% → exit, 50% → enter...
            With: 50% panic → enter, stays until 30% → stable
        """
        panic_ratio = self._calculate_panic_ratio()
        old_mode = self.mode

        # STATE MACHINE
        if self.mode == CircuitBreakerMode.NORMAL:
            if panic_ratio > self.panic_threshold_enter:
                self.mode = CircuitBreakerMode.HIGH_VOLATILITY
                self._log_mode_change(old_mode, panic_ratio)

        elif self.mode == CircuitBreakerMode.HIGH_VOLATILITY:
            if panic_ratio < self.panic_threshold_exit:
                self.mode = CircuitBreakerMode.NORMAL
                self._log_mode_change(old_mode, panic_ratio)
            elif panic_ratio > self.circuit_open_threshold:
                self.mode = CircuitBreakerMode.CIRCUIT_OPEN
                self._log_mode_change(old_mode, panic_ratio)

        elif self.mode == CircuitBreakerMode.CIRCUIT_OPEN:
            # Need to drop below 60% to exit
            if panic_ratio < 0.60:
                self.mode = CircuitBreakerMode.HIGH_VOLATILITY
                self._log_mode_change(old_mode, panic_ratio)

    def _log_mode_change(
        self,
        old_mode: CircuitBreakerMode,
        panic_ratio: float
    ) -> None:
        """
        Log mode transitions pour monitoring

        Log Levels:
            CRITICAL: CIRCUIT_OPEN (protection max)
            WARNING: HIGH_VOLATILITY (adaptive mode)
            INFO: NORMAL (recovery)
        """
        transition = {
            'timestamp': datetime.now(timezone.utc),
            'old_mode': old_mode.value,
            'new_mode': self.mode.value,
            'panic_ratio': panic_ratio,
            'trigger': (
                'sustained_panic'
                if self.mode != CircuitBreakerMode.NORMAL
                else 'recovery'
            )
        }

        self.mode_changes.append(transition)
        self.last_mode_change = datetime.now(timezone.utc)

        # Log avec niveau approprié
        if self.mode == CircuitBreakerMode.CIRCUIT_OPEN:
            logger.critical(
                "🚨 VIX CIRCUIT BREAKER OPENED",
                old_mode=old_mode.value,
                new_mode=self.mode.value,
                panic_ratio_pct=f"{panic_ratio:.1%}",
                message="MAXIMUM PROTECTION ACTIVE - BACKEND PROTECTED"
            )
        elif self.mode == CircuitBreakerMode.HIGH_VOLATILITY:
            if old_mode == CircuitBreakerMode.NORMAL:
                logger.warning(
                    "⚠️  VIX Circuit Breaker ACTIVATED",
                    old_mode=old_mode.value,
                    new_mode=self.mode.value,
                    panic_ratio_pct=f"{panic_ratio:.1%}",
                    message="Sustained panic detected - Adaptive TTL enabled"
                )
            else:
                logger.warning(
                    "⚠️  VIX Circuit Breaker DOWNGRADE",
                    old_mode=old_mode.value,
                    new_mode=self.mode.value,
                    panic_ratio_pct=f"{panic_ratio:.1%}"
                )
        else:
            logger.info(
                "✅ VIX Circuit Breaker DEACTIVATED",
                old_mode=old_mode.value,
                new_mode=self.mode.value,
                panic_ratio_pct=f"{panic_ratio:.1%}",
                message="Panic resolved - Normal operation"
            )

    def get_adaptive_ttl(
        self,
        vix_status: str,
        base_ttl: Optional[int] = None
    ) -> Tuple[int, str]:
        """
        Get TTL adaptatif selon circuit breaker mode

        Args:
            vix_status: 'panic' | 'warning' | 'normal'
            base_ttl: Base TTL from GoldenHour (default 60s)

        Returns:
            (ttl, strategy) tuple:
              - ttl: Cache TTL seconds
              - strategy: 'bypass' | 'adaptive' | 'normal'

        Logic Table:
            ┌──────────────┬────────┬─────────┬────────┐
            │ Mode         │ Panic  │ Warning │ Normal │
            ├──────────────┼────────┼─────────┼────────┤
            │ NORMAL       │ 0s     │ base    │ base   │
            │ HIGH_VOL     │ 5s     │ 10s     │ base   │
            │ CIRCUIT_OPEN │ 10s    │ 30s     │ 60s    │
            └──────────────┴────────┴─────────┴────────┘

        Side Effects:
            - Calls record_panic_status() → may transition
        """
        # Record status (updates state machine)
        self.record_panic_status(vix_status)

        # Default base_ttl
        if base_ttl is None:
            base_ttl = 60

        # Get TTL based on mode
        if self.mode == CircuitBreakerMode.CIRCUIT_OPEN:
            # MAXIMUM PROTECTION
            if vix_status == "panic":
                return (10, "adaptive")
            elif vix_status == "warning":
                return (30, "adaptive")
            else:
                return (60, "normal")

        elif self.mode == CircuitBreakerMode.HIGH_VOLATILITY:
            # MODERATE PROTECTION
            if vix_status == "panic":
                return (5, "adaptive")
            elif vix_status == "warning":
                return (10, "adaptive")
            else:
                return (base_ttl, "normal")

        else:  # NORMAL
            # STANDARD BEHAVIOR
            if vix_status == "panic":
                return (0, "bypass")
            else:
                return (base_ttl, "normal")

    def _manage_panic_timestamp(self, is_panic: bool) -> Optional[float]:
        """
        Manage panic start timestamp in Redis with atomic guarantees.

        Implements:
        - SETNX "First Writer Wins": Only first worker sets timestamp
        - Dead Man's Switch: Auto-expire after 24h if system crashes
        - Atomic cleanup: DELETE when panic ends

        Args:
            is_panic: Current panic state from VIX detection

        Returns:
            Panic start timestamp (float) if in panic, None otherwise

        Raises:
            Never raises - returns None on Redis errors (Fail-Safe)
        """
        if self.redis is None:
            # No Redis configured - skip persistence (backward compatibility)
            return None

        try:
            if is_panic:
                # ─────────────────────────────────────────────────────
                # SETNX "First Writer Wins"
                # Only the FIRST worker detecting panic sets the timestamp
                # All subsequent workers read the same value
                # ─────────────────────────────────────────────────────
                current_ts = time.time()

                # SET NX=True: Set only if key does NOT exist (atomic)
                # EX=86400: Dead Man's Switch - auto-expire after 24h
                was_set = self.redis.set(
                    PANIC_START_TS_KEY,
                    current_ts,
                    nx=True,  # Only set if not exists
                    ex=PANIC_TS_TTL_SECONDS  # 24h TTL (Dead Man's Switch)
                )

                if was_set:
                    logger.warning(
                        "PANIC_TIMESTAMP_INITIALIZED",
                        timestamp=current_ts,
                        ttl_seconds=PANIC_TS_TTL_SECONDS,
                        source="first_writer"
                    )

                # Read the authoritative timestamp (might be from another worker)
                stored_ts = self.redis.get(PANIC_START_TS_KEY)

                if stored_ts is not None:
                    # Refresh TTL (extend Dead Man's Switch while system is alive)
                    self.redis.expire(PANIC_START_TS_KEY, PANIC_TS_TTL_SECONDS)

                    # Handle both bytes (real Redis) and str (some clients/mocks)
                    if isinstance(stored_ts, bytes):
                        stored_ts = stored_ts.decode('utf-8')
                    return float(stored_ts)
                else:
                    # Edge case: Key expired between SET and GET (unlikely)
                    logger.error("PANIC_TS_RACE_CONDITION", action="retry_next_cycle")
                    return current_ts  # Use local timestamp as fallback

            else:
                # ─────────────────────────────────────────────────────
                # Panic ended: Clean up timestamp
                # ─────────────────────────────────────────────────────
                deleted = self.redis.delete(PANIC_START_TS_KEY)

                if deleted:
                    logger.info(
                        "PANIC_TIMESTAMP_CLEARED",
                        reason="panic_ended"
                    )

                return None

        except Exception as e:
            # ─────────────────────────────────────────────────────────
            # FAIL-SAFE: Redis down → Return None (will trigger PANIC_FULL)
            # ─────────────────────────────────────────────────────────
            logger.error(
                "REDIS_ERROR_PANIC_TS",
                error=str(e),
                action="fail_safe_mode"
            )
            return None

    def _calculate_panic_duration(self, panic_start_ts: Optional[float]) -> float:
        """
        Calculate panic duration in minutes from start timestamp.

        Args:
            panic_start_ts: Panic start timestamp from Redis (or None)

        Returns:
            Duration in minutes (0.0 if no panic or invalid timestamp)
        """
        if panic_start_ts is None:
            return 0.0

        try:
            duration_seconds = time.time() - panic_start_ts
            duration_minutes = duration_seconds / 60.0

            # Sanity check: Duration should not be negative
            if duration_minutes < 0:
                logger.warning(
                    "NEGATIVE_PANIC_DURATION",
                    duration_min=duration_minutes,
                    action="reset_to_zero"
                )
                return 0.0

            return duration_minutes

        except (TypeError, ValueError) as e:
            logger.error(
                "INVALID_PANIC_TIMESTAMP",
                timestamp=panic_start_ts,
                error=str(e)
            )
            return 0.0

    def get_ttl(
        self,
        base_ttl: int,
        vix_status: str = "normal",
        match_context: Optional[Dict] = None
    ) -> Tuple[int, str]:
        """
        Get adaptive TTL based on market volatility (VIX) and panic duration.

        Implements the complete VIX Circuit Breaker + Adaptive Panic Quota:
        1. Detect market panic via VIX-style analysis
        2. Manage panic timestamp atomically (SETNX + Dead Man's Switch)
        3. Calculate context-aware TTL via stateless AdaptivePanicQuota

        Args:
            base_ttl: Base TTL in seconds (normal conditions)
            vix_status: 'panic' | 'warning' | 'normal' (default: 'normal')
            match_context: Optional context dict with 'league', 'competition', etc.

        Returns:
            Tuple of (ttl_seconds, mode_string)

        Fail-Safe Behavior:
            If Redis is down → Returns (0, "PANIC_FULL") for maximum caution
        """
        try:
            # ═══════════════════════════════════════════════════════════════
            # STEP 1: Detect panic state
            # ═══════════════════════════════════════════════════════════════
            is_panic = (vix_status == "panic")

            # ═══════════════════════════════════════════════════════════════
            # STEP 2: Manage panic timestamp (SETNX + Dead Man's Switch)
            # ═══════════════════════════════════════════════════════════════
            panic_start_ts = self._manage_panic_timestamp(is_panic)

            # ═══════════════════════════════════════════════════════════════
            # FAIL-SAFE: Panic detected but no reliable timestamp
            # Two scenarios trigger this:
            # 1. Redis configured but error occurred → Critical failure
            # 2. Redis NOT configured → No persistence = no duration tracking
            # In BOTH cases: Better safe than sorry → PANIC_FULL
            # ═══════════════════════════════════════════════════════════════
            if is_panic and panic_start_ts is None:
                redis_status = "configured_but_error" if self.redis is not None else "not_configured"
                logger.warning(
                    "PANIC_WITHOUT_RELIABLE_TIMESTAMP",
                    redis_status=redis_status,
                    action="fail_safe_panic_full",
                    reason="cannot_calculate_duration_safely"
                )
                return (0, "PANIC_FULL")

            # ═══════════════════════════════════════════════════════════════
            # STEP 3: Calculate panic duration
            # ═══════════════════════════════════════════════════════════════
            panic_duration_min = self._calculate_panic_duration(panic_start_ts)

            # ═══════════════════════════════════════════════════════════════
            # STEP 4: Call stateless AdaptivePanicQuota for TTL decision
            # ═══════════════════════════════════════════════════════════════
            ttl, mode, metadata = self._panic_quota.calculate_ttl_strategy(
                base_ttl=base_ttl,
                panic_duration_minutes=panic_duration_min,
                match_context=match_context or {}
            )

            # ═══════════════════════════════════════════════════════════════
            # STEP 5: Log decision for observability (optimized)
            # Pattern "Log on Change": INFO only when mode/tier changes
            # DEBUG for repetitive calls (disabled in prod by default)
            # ═══════════════════════════════════════════════════════════════
            current_mode = mode.value if hasattr(mode, 'value') else str(mode)
            current_tier = metadata.get('tier', 0)

            log_data = {
                "is_panic": is_panic,
                "panic_duration_min": round(panic_duration_min, 1),
                "tier": current_tier,
                "mode": current_mode,
                "ttl_seconds": ttl,
                "match_importance": metadata.get('match_importance', 'unknown')
            }

            # Log INFO only on state change (mode or tier)
            if current_mode != self._last_logged_mode or current_tier != self._last_logged_tier:
                logger.info("VIX_TTL_STATE_CHANGE", **log_data,
                           previous_mode=self._last_logged_mode,
                           previous_tier=self._last_logged_tier)
                self._last_logged_mode = current_mode
                self._last_logged_tier = current_tier
            else:
                # Debug level for repetitive calls (can be disabled in prod)
                # NOTE: In production, configure structlog with level=INFO or higher
                # to suppress DEBUG logs and achieve 99% log volume reduction.
                # Example: structlog.configure(
                #     wrapper_class=structlog.make_filtering_bound_logger(logging.INFO)
                # )
                logger.debug("VIX_TTL_DECISION", **log_data)

            # Return mode as string for compatibility
            mode_str = mode.value if hasattr(mode, 'value') else str(mode)
            return (ttl, mode_str)

        except Exception as e:
            # ═══════════════════════════════════════════════════════════════
            # FAIL-SAFE: Any error → Maximum caution (PANIC_FULL, TTL=0)
            # Better to recalculate everything than serve stale data
            # ═══════════════════════════════════════════════════════════════
            logger.error(
                "VIX_CIRCUIT_BREAKER_ERROR",
                error=str(e),
                action="fail_safe_panic_full"
            )
            return (0, "PANIC_FULL")

    def get_metrics(self) -> Dict:
        """
        Get circuit breaker metrics

        Returns:
            Dict avec current state et statistics
        """
        panic_ratio = self._calculate_panic_ratio()

        return {
            'mode': self.mode.value,
            'panic_ratio_pct': round(panic_ratio * 100, 2),
            'window_size': len(self.panic_history),
            'window_full': len(self.panic_history) == self.window_seconds,
            'window_seconds': self.window_seconds,
            'mode_changes_count': len(self.mode_changes),
            'last_mode_change': (
                self.last_mode_change.isoformat()
                if self.last_mode_change
                else None
            ),
            'thresholds': {
                'enter_high_vol_pct': self.panic_threshold_enter * 100,
                'exit_high_vol_pct': self.panic_threshold_exit * 100,
                'circuit_open_pct': self.circuit_open_threshold * 100,
                'hysteresis_pct': (
                    self.panic_threshold_enter - self.panic_threshold_exit
                ) * 100
            }
        }

    def reset(self) -> None:
        """
        Reset circuit breaker (TESTING ONLY)

        WARNING: Ne PAS appeler en production!
        """
        self.panic_history.clear()
        self.mode = CircuitBreakerMode.NORMAL
        self.mode_changes.clear()
        self.last_mode_change = None

        logger.warning("VIXCircuitBreaker RESET - State cleared")


# Singleton instance
vix_circuit_breaker = VIXCircuitBreaker()
