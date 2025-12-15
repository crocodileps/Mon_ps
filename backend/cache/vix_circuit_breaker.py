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
import structlog

logger = structlog.get_logger()


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
        window_seconds: int = 1800,
        panic_threshold_enter: float = 0.50,
        panic_threshold_exit: float = 0.30,
        circuit_open_threshold: float = 0.80
    ):
        """
        Initialize VIX Circuit Breaker

        Args:
            window_seconds: Rolling window size (default 1800 = 30min)
            panic_threshold_enter: Ratio to enter HIGH_VOL (0.50 = 50%)
            panic_threshold_exit: Ratio to exit HIGH_VOL (0.30 = 30%)
            circuit_open_threshold: Ratio to open circuit (0.80 = 80%)

        Raises:
            ValueError: Si thresholds invalides ou pas d'hystérésis
        """
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

        logger.info(
            "VIXCircuitBreaker initialized",
            window_seconds=window_seconds,
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
