"""
Tests - VIX Circuit Breaker
Grade: A++ Institutional Perfect

Tests complets du VIX Circuit Breaker:
  - Initial state
  - State transitions
  - Hystérésis
  - Adaptive TTL
  - Metrics
  - Real scenario simulation
"""

import pytest
from datetime import datetime, timezone
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cache.vix_circuit_breaker import (
    VIXCircuitBreaker,
    CircuitBreakerMode
)


def test_initial_state():
    """Test 1/9: Circuit breaker starts in NORMAL mode"""
    breaker = VIXCircuitBreaker()

    assert breaker.mode == CircuitBreakerMode.NORMAL
    assert len(breaker.panic_history) == 0
    assert breaker.get_metrics()['panic_ratio_pct'] == 0.0

    print("✅ TEST 1/9: Initial state PASS")


def test_enter_high_volatility():
    """Test 2/9: Transition NORMAL → HIGH_VOLATILITY at 50%"""
    breaker = VIXCircuitBreaker(
        window_seconds=10,
        panic_threshold_enter=0.5
    )

    # 6/10 panic (60% > 50%) - Record normals first to avoid jumping to CIRCUIT_OPEN
    for _ in range(4):
        breaker.record_panic_status("normal")
    for _ in range(6):
        breaker.record_panic_status("panic")

    assert breaker.mode == CircuitBreakerMode.HIGH_VOLATILITY
    assert breaker.get_metrics()['panic_ratio_pct'] == 60.0

    print("✅ TEST 2/9: HIGH_VOLATILITY transition PASS")


def test_hysteresis():
    """Test 3/9: Hystérésis prevents rapid oscillations"""
    breaker = VIXCircuitBreaker(
        window_seconds=10,
        panic_threshold_enter=0.5,
        panic_threshold_exit=0.3
    )

    # Phase 1: Enter HIGH_VOL (60%) - Normals first
    for _ in range(4):
        breaker.record_panic_status("normal")
    for _ in range(6):
        breaker.record_panic_status("panic")
    assert breaker.mode == CircuitBreakerMode.HIGH_VOLATILITY

    # Phase 2: Drop to 40% (> 30% exit) → STAYS HIGH_VOL
    for _ in range(6):
        breaker.record_panic_status("normal")
    for _ in range(4):
        breaker.record_panic_status("panic")
    assert breaker.mode == CircuitBreakerMode.HIGH_VOLATILITY
    assert breaker.get_metrics()['panic_ratio_pct'] == 40.0

    # Phase 3: Drop to 20% (< 30% exit) → EXITS
    for _ in range(8):
        breaker.record_panic_status("normal")
    for _ in range(2):
        breaker.record_panic_status("panic")
    assert breaker.mode == CircuitBreakerMode.NORMAL
    assert breaker.get_metrics()['panic_ratio_pct'] == 20.0

    print("✅ TEST 3/9: Hystérésis PASS")


def test_circuit_open():
    """Test 4/9: CIRCUIT_OPEN at 80% panic"""
    breaker = VIXCircuitBreaker(
        window_seconds=10,
        circuit_open_threshold=0.8
    )

    # 9/10 panic (90% > 80%)
    for _ in range(9):
        breaker.record_panic_status("panic")
    for _ in range(1):
        breaker.record_panic_status("normal")

    assert breaker.mode == CircuitBreakerMode.CIRCUIT_OPEN
    assert breaker.get_metrics()['panic_ratio_pct'] == 90.0

    print("✅ TEST 4/9: CIRCUIT_OPEN PASS")


def test_ttl_normal_mode():
    """Test 5/9: TTL in NORMAL mode"""
    breaker = VIXCircuitBreaker()

    # Normal → base TTL (test first to stay in NORMAL mode)
    ttl, strategy = breaker.get_adaptive_ttl("normal", base_ttl=60)
    assert ttl == 60
    assert strategy == "normal"

    # Warning → base TTL
    ttl, strategy = breaker.get_adaptive_ttl("warning", base_ttl=45)
    assert ttl == 45
    assert strategy == "normal"

    # Panic → bypass (test last since it adds to panic history)
    ttl, strategy = breaker.get_adaptive_ttl("panic")
    assert ttl == 0
    assert strategy == "bypass"

    print("✅ TEST 5/9: NORMAL mode TTL PASS")


def test_ttl_high_volatility():
    """Test 6/9: TTL in HIGH_VOLATILITY mode"""
    breaker = VIXCircuitBreaker(window_seconds=10)

    # Force HIGH_VOL (6/10 panic) - Normals first
    for _ in range(4):
        breaker.record_panic_status("normal")
    for _ in range(6):
        breaker.record_panic_status("panic")

    assert breaker.mode == CircuitBreakerMode.HIGH_VOLATILITY

    # Panic → TTL=5s (adaptive!)
    ttl, strategy = breaker.get_adaptive_ttl("panic")
    assert ttl == 5
    assert strategy == "adaptive"

    # Warning → TTL=10s
    ttl, strategy = breaker.get_adaptive_ttl("warning")
    assert ttl == 10
    assert strategy == "adaptive"

    # Normal → base TTL
    ttl, strategy = breaker.get_adaptive_ttl("normal", base_ttl=60)
    assert ttl == 60
    assert strategy == "normal"

    print("✅ TEST 6/9: HIGH_VOLATILITY mode TTL PASS")


def test_ttl_circuit_open():
    """Test 7/9: TTL in CIRCUIT_OPEN mode"""
    breaker = VIXCircuitBreaker(window_seconds=10)

    # Force CIRCUIT_OPEN (9/10 panic)
    for _ in range(9):
        breaker.record_panic_status("panic")

    assert breaker.mode == CircuitBreakerMode.CIRCUIT_OPEN

    # Panic → TTL=10s (max protection)
    ttl, strategy = breaker.get_adaptive_ttl("panic")
    assert ttl == 10
    assert strategy == "adaptive"

    # Warning → TTL=30s
    ttl, strategy = breaker.get_adaptive_ttl("warning")
    assert ttl == 30
    assert strategy == "adaptive"

    # Normal → TTL=60s
    ttl, strategy = breaker.get_adaptive_ttl("normal")
    assert ttl == 60
    assert strategy == "normal"

    print("✅ TEST 7/9: CIRCUIT_OPEN mode TTL PASS")


def test_metrics():
    """Test 8/9: Comprehensive metrics"""
    breaker = VIXCircuitBreaker(window_seconds=10)

    # Record panic (7/10 = 70%) - Normals first
    for _ in range(3):
        breaker.record_panic_status("normal")
    for _ in range(7):
        breaker.record_panic_status("panic")

    metrics = breaker.get_metrics()

    # Validate structure
    assert 'mode' in metrics
    assert 'panic_ratio_pct' in metrics
    assert 'window_size' in metrics
    assert 'thresholds' in metrics

    # Validate values
    assert metrics['mode'] == 'high_volatility'
    assert metrics['panic_ratio_pct'] == 70.0
    assert metrics['window_size'] == 10
    assert metrics['window_full'] is True

    # Validate thresholds
    t = metrics['thresholds']
    assert t['enter_high_vol_pct'] == 50.0
    assert t['exit_high_vol_pct'] == 30.0
    assert t['circuit_open_pct'] == 80.0
    assert t['hysteresis_pct'] == 20.0

    print("✅ TEST 8/9: Metrics PASS")


def test_real_scenario():
    """Test 9/9 BONUS: Simulate real panic scenario"""
    breaker = VIXCircuitBreaker(window_seconds=60)

    print("\n" + "="*60)
    print("SIMULATION: Real Panic Scenario (60s window)")
    print("="*60)

    # Phase 1: Normal (30s)
    print("\nPhase 1: Normal operation (30s)...")
    for i in range(30):
        breaker.record_panic_status("normal")
        if i == 29:
            ttl, _ = breaker.get_adaptive_ttl("normal")
            print(f"  t=30s: Mode={breaker.mode.value}, TTL={ttl}s")

    # Phase 2: Isolated panic (5s)
    print("\nPhase 2: Isolated panic (5s)...")
    for _ in range(5):
        breaker.record_panic_status("panic")
    ttl, _ = breaker.get_adaptive_ttl("panic")
    m = breaker.get_metrics()
    print(f"  t=35s: Mode={breaker.mode.value}, TTL={ttl}s")
    print(f"         Panic ratio={m['panic_ratio_pct']:.1f}%")

    # Phase 3: Sustained panic (40s)
    print("\nPhase 3: Sustained panic (40s)...")
    for i in range(40):
        breaker.record_panic_status("panic")
        if i == 20:
            ttl, _ = breaker.get_adaptive_ttl("panic")
            m = breaker.get_metrics()
            print(f"  t=55s: Mode={breaker.mode.value}, TTL={ttl}s")
            print(f"         Panic ratio={m['panic_ratio_pct']:.1f}%")

    # Final state
    ttl, strategy = breaker.get_adaptive_ttl("panic")
    m = breaker.get_metrics()

    print(f"\n📊 Final State (t=75s):")
    print(f"  Mode: {breaker.mode.value}")
    print(f"  Panic Ratio: {m['panic_ratio_pct']:.1f}%")
    print(f"  TTL: {ttl}s (strategy={strategy})")
    print(f"  Mode Changes: {m['mode_changes_count']}")

    # Validate
    assert breaker.mode == CircuitBreakerMode.HIGH_VOLATILITY
    assert ttl == 5
    assert m['panic_ratio_pct'] > 50.0

    print("\n✅ TEST 9/9 BONUS: Real scenario PASS")
    print("="*60)


if __name__ == "__main__":
    # Run all tests
    pytest.main([__file__, "-v", "-s"])
