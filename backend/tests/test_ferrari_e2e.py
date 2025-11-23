"""
Ferrari Ultimate 2.0 - End-to-End Tests
Tests d'intégration complets du système
"""

import pytest
import sys
sys.path.append('/app')

from services.ferrari_smart_router import get_smart_router, RouterStrategy, EngineType
from services.ferrari_auto_promotion import get_auto_promotion_engine, PromotionDecision
from services.ferrari_realtime_tracker import get_realtime_tracker


def test_smart_router_initialization():
    """Test initialisation Smart Router"""
    router = get_smart_router(strategy=RouterStrategy.AUTO)
    assert router is not None
    assert router._current_strategy == RouterStrategy.AUTO
    print("✅ Smart Router initialized")


def test_routing_decision():
    """Test décision de routing"""
    router = get_smart_router()
    
    match_data = {
        'sport': 'soccer_epl',
        'home_team': 'Arsenal',
        'away_team': 'Chelsea'
    }
    
    engine, metadata = router.route_match_analysis(match_data)
    assert engine in [EngineType.FERRARI, EngineType.BASELINE]
    assert 'strategy' in metadata
    print(f"✅ Routing decision: {engine.value}")


def test_auto_promotion_evaluation():
    """Test évaluation auto-promotion"""
    engine = get_auto_promotion_engine()
    
    decision, analysis = engine.evaluate_variation(6, 2)
    assert decision in PromotionDecision
    assert 'variation_data' in analysis
    assert 'baseline_data' in analysis
    print(f"✅ Auto-promotion evaluation: {decision.value}")


def test_realtime_tracker():
    """Test real-time tracker"""
    tracker = get_realtime_tracker()
    
    # Track some bets
    for i in range(5):
        result = tracker.track_bet_result(
            variation_id=6,
            outcome='win' if i % 2 == 0 else 'loss',
            profit=50 if i % 2 == 0 else -25,
            stake=25,
            odds=2.5
        )
        assert 'updated_metrics' in result
    
    # Get metrics
    metrics = tracker.get_realtime_metrics(6)
    assert metrics['total_bets'] == 5
    print(f"✅ Real-time tracker: {metrics['total_bets']} bets tracked")


def test_integration_flow():
    """Test flux complet d'intégration"""
    print("\n" + "="*60)
    print("🏎️ FERRARI ULTIMATE 2.0 - END-TO-END TEST")
    print("="*60)
    
    # 1. Smart Router
    router = get_smart_router()
    match_data = {'sport': 'soccer_epl', 'home_team': 'Man Utd', 'away_team': 'Liverpool'}
    engine, _ = router.route_match_analysis(match_data)
    print(f"1. Smart Router: {engine.value} ✅")
    
    # 2. Real-time Tracker
    tracker = get_realtime_tracker()
    tracker.reset_metrics()  # Clean slate
    
    # Simulate 20 bets with good performance
    for i in range(20):
        outcome = 'win' if i < 14 else 'loss'  # 70% WR
        profit = 50 if outcome == 'win' else -25
        tracker.track_bet_result(6, outcome, profit, 25, 2.5)
    
    metrics = tracker.get_realtime_metrics(6)
    print(f"2. Tracker: {metrics['total_bets']} bets, WR {metrics['win_rate']:.1%} ✅")
    
    # 3. Auto-promotion
    promotion_engine = get_auto_promotion_engine()
    decision, analysis = promotion_engine.evaluate_variation(6, 2)
    print(f"3. Auto-promotion: {decision.value} ✅")
    
    # 4. Summary
    summary = tracker.get_performance_summary()
    print(f"4. Summary: {summary['total_variations']} variations tracked ✅")
    
    print("="*60)
    print("✅ INTEGRATION TEST PASSED!")
    print("="*60)


if __name__ == "__main__":
    test_smart_router_initialization()
    test_routing_decision()
    test_auto_promotion_evaluation()
    test_realtime_tracker()
    test_integration_flow()
    
    print("\n🎉 ALL TESTS PASSED!")
