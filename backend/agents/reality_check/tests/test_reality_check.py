#!/usr/bin/env python3
"""
🧪 TESTS REALITY CHECK MODULE
==============================
Tests unitaires pour valider le module Reality Check.
"""

import sys
import os

# Add paths
sys.path.insert(0, '/app')
sys.path.insert(0, '/home/Mon_ps/backend')

from agents.reality_check import RealityChecker
from agents.reality_check.data_service import RealityDataService

# Config DB
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'monps_postgres'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': 'monps_db',
    'user': 'monps_user',
    'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
}


def test_data_service():
    """Test du Data Service"""
    print("\n" + "="*60)
    print("🧪 TEST 1: Data Service")
    print("="*60)
    
    service = RealityDataService(DB_CONFIG)
    
    # Test team_class
    print("\n📊 Test get_team_class('Manchester City'):")
    result = service.get_team_class('Manchester City')
    if result:
        print(f"   ✅ Tier: {result.get('tier')}, Power: {result.get('calculated_power_index')}")
    else:
        print("   ⚠️ Pas de données (table vide ou équipe non trouvée)")
    
    # Test tactical_matrix
    print("\n📊 Test get_tactical_matchup('possession', 'low_block_counter'):")
    result = service.get_tactical_matchup('possession', 'low_block_counter')
    if result:
        print(f"   ✅ Upset: {result.get('upset_probability')}%, BTTS: {result.get('btts_probability')}%")
    else:
        print("   ⚠️ Pas de données")
    
    # Test referee
    print("\n📊 Test get_referee_profile('Michael Oliver'):")
    result = service.get_referee_profile('Michael Oliver')
    if result:
        print(f"   ✅ Tendency: {result.get('under_over_tendency')}, Penalty: {result.get('penalty_frequency')}%")
    else:
        print("   ⚠️ Pas de données")
    
    return True


def test_reality_checker_class_gap():
    """Test avec gros écart de classe"""
    print("\n" + "="*60)
    print("🧪 TEST 2: Reality Checker - Gros écart de classe")
    print("="*60)
    
    checker = RealityChecker(DB_CONFIG)
    
    # Man City (Tier S) vs Southampton (Tier D)
    print("\n🏟️ Manchester City vs Southampton:")
    result = checker.analyze_match("Manchester City", "Southampton")
    
    print(f"   Reality Score: {result.reality_score}/100")
    print(f"   Convergence: {result.convergence}")
    print(f"   Tiers: {result.home_tier} vs {result.away_tier} (gap: {result.tier_gap})")
    print(f"   Warnings: {len(result.warnings)}")
    for w in result.warnings[:3]:
        print(f"      - {w}")
    print(f"   Recommendation: {result.recommendation}")
    
    return result.reality_score > 60  # Devrait être élevé


def test_reality_checker_balanced():
    """Test avec équipes équilibrées"""
    print("\n" + "="*60)
    print("🧪 TEST 3: Reality Checker - Match équilibré")
    print("="*60)
    
    checker = RealityChecker(DB_CONFIG)
    
    # Arsenal (Tier A) vs Liverpool (Tier A)
    print("\n🏟️ Arsenal vs Liverpool:")
    result = checker.analyze_match("Arsenal", "Liverpool")
    
    print(f"   Reality Score: {result.reality_score}/100")
    print(f"   Convergence: {result.convergence}")
    print(f"   Tiers: {result.home_tier} vs {result.away_tier} (gap: {result.tier_gap})")
    print(f"   Warnings: {len(result.warnings)}")
    for w in result.warnings[:3]:
        print(f"      - {w}")
    
    return 40 <= result.reality_score <= 70  # Devrait être neutre


def test_reality_checker_giant_killer():
    """Test avec outsider fort à l'extérieur"""
    print("\n" + "="*60)
    print("🧪 TEST 4: Reality Checker - Giant Killer Alert")
    print("="*60)
    
    checker = RealityChecker(DB_CONFIG)
    
    # Brentford (Tier C) vs Bayern Munich (Tier S)
    print("\n🏟️ Brentford vs Bayern Munich:")
    result = checker.analyze_match("Brentford", "Bayern Munich")
    
    print(f"   Reality Score: {result.reality_score}/100")
    print(f"   Convergence: {result.convergence}")
    print(f"   Tiers: {result.home_tier} vs {result.away_tier} (gap: {result.tier_gap})")
    print(f"   Warnings: {len(result.warnings)}")
    for w in result.warnings[:3]:
        print(f"      - {w}")
    
    # Vérifier qu'on détecte le Giant Killer
    has_giant_alert = any('GIANT' in w or 'OUTSIDER' in w for w in result.warnings)
    print(f"   Giant Killer Alert detected: {'✅' if has_giant_alert else '❌'}")
    
    return has_giant_alert


def test_quick_check():
    """Test de la fonction quick_check"""
    print("\n" + "="*60)
    print("🧪 TEST 5: Quick Check Function")
    print("="*60)
    
    from agents.reality_check.reality_checker import quick_check
    
    result = quick_check("Real Madrid", "Barcelona")
    
    print(f"\n🏟️ Real Madrid vs Barcelona (quick_check):")
    print(f"   Type: {type(result)}")
    print(f"   Reality Score: {result.get('reality_score', 'N/A')}")
    print(f"   Keys: {list(result.keys())[:5]}...")
    
    return isinstance(result, dict) and 'reality_score' in result


def run_all_tests():
    """Exécute tous les tests"""
    print("\n" + "="*60)
    print("🧪 REALITY CHECK MODULE - TEST SUITE")
    print("="*60)
    
    tests = [
        ("Data Service", test_data_service),
        ("Class Gap (City vs Southampton)", test_reality_checker_class_gap),
        ("Balanced Match (Arsenal vs Liverpool)", test_reality_checker_balanced),
        ("Giant Killer (Brentford vs Bayern)", test_reality_checker_giant_killer),
        ("Quick Check Function", test_quick_check),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ ERREUR dans {name}: {e}")
            results.append((name, False))
    
    # Résumé
    print("\n" + "="*60)
    print("📊 RÉSUMÉ DES TESTS")
    print("="*60)
    
    passed = sum(1 for _, s in results if s)
    total = len(results)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status} - {name}")
    
    print(f"\n   Total: {passed}/{total} tests réussis")
    print("="*60)
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
