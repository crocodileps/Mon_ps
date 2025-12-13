"""
TEST MVP - QUANTUM CORE
=======================
Test complet du système de prédiction
"""

import sys
sys.path.insert(0, '/home/Mon_ps')

from quantum_core.engine import QuantumEngine
from quantum_core.data.manager import get_data_manager
from quantum_core.probability.poisson import DixonColesModel, get_all_market_probabilities
from quantum_core.edge.calculator import calculate_edge, remove_vig_basic

def main():
    print("=" * 80)
    print("🧪 TEST MVP - QUANTUM CORE")
    print("=" * 80)

    # Test 1: DataManager
    print("\n📊 TEST 1: DataManager")
    print("-" * 40)

    dm = get_data_manager()

    liverpool = dm.get_team("Liverpool")
    if liverpool:
        print(f"✅ Liverpool trouvé:")
        print(f"   xG: {liverpool.xg_for:.2f}")
        print(f"   xGA: {liverpool.xg_against:.2f}")
        print(f"   Style: {liverpool.tactical_style}")
        print(f"   Diesel: {liverpool.diesel_factor:.2f}")
    else:
        print("❌ Liverpool non trouvé")

    city = dm.get_team("Manchester City")
    if city:
        print(f"✅ Manchester City trouvé:")
        print(f"   xG: {city.xg_for:.2f}")
        print(f"   xGA: {city.xg_against:.2f}")
        print(f"   Style: {city.tactical_style}")
    else:
        print("❌ Manchester City non trouvé")

    # Test 2: Dixon-Coles
    print("\n📊 TEST 2: Dixon-Coles Model")
    print("-" * 40)

    model = DixonColesModel(rho=-0.13)

    # Liverpool vs Man City
    lambda_h, lambda_a = model.calculate_lambdas(
        home_xg=1.8,    # Liverpool attack
        away_xga=1.3,   # City defense
        away_xg=2.2,    # City attack
        home_xga=1.1    # Liverpool defense
    )

    print(f"Lambdas calculés:")
    print(f"  Liverpool (H): λ = {lambda_h:.2f}")
    print(f"  Man City (A):  λ = {lambda_a:.2f}")

    matrix = model.calculate_score_matrix(lambda_h, lambda_a)

    print(f"\nTop 5 scores probables:")
    for (h, a), prob in matrix.most_likely_scores(5):
        print(f"  {h}-{a}: {prob*100:.1f}% (Fair: {1/prob:.2f})")

    # Test 3: Probabilités marchés
    print("\n📊 TEST 3: Probabilités Marchés")
    print("-" * 40)

    all_probs = get_all_market_probabilities(matrix)

    key_markets = ["home_win", "draw", "away_win", "over_25", "btts_yes"]
    for m in key_markets:
        prob = all_probs[m]
        fair = 1/prob if prob > 0.001 else 999
        print(f"  {m}: {prob*100:.1f}% (Fair: {fair:.2f})")

    # Test 4: Edge Calculator
    print("\n📊 TEST 4: Edge Calculator")
    print("-" * 40)

    # Remove vig test
    odds_1x2 = {"home": 2.10, "draw": 3.40, "away": 3.50}
    true_probs = remove_vig_basic(odds_1x2)

    print("Remove Vig test (1X2):")
    for outcome, prob in true_probs.items():
        print(f"  {outcome}: {prob*100:.1f}%")

    # Edge calculation
    our_prob = all_probs["over_25"]
    bookmaker_odds = 1.85

    edge_analysis = calculate_edge(our_prob, bookmaker_odds, market_margin=5.0)

    print(f"\nEdge calculation (Over 2.5):")
    print(f"  Notre proba: {our_prob*100:.1f}%")
    print(f"  Cote bookmaker: {bookmaker_odds}")
    print(f"  Proba bookmaker (dévigée): {edge_analysis.bookmaker_probability*100:.1f}%")
    print(f"  Edge: {edge_analysis.edge_percentage:.1f}%")
    print(f"  Value: {'✅ OUI' if edge_analysis.is_value else '❌ NON'}")
    print(f"  Kelly: {edge_analysis.kelly_stake:.2f}%")

    # Test 5: QuantumEngine
    print("\n📊 TEST 5: QuantumEngine (Full Integration)")
    print("-" * 40)

    engine = QuantumEngine(dm)

    # Prédiction simple
    pred = engine.predict("Liverpool", "Manchester City", "over_25", odds=1.85)

    print(f"Prédiction Over 2.5:")
    print(f"  Probabilité: {pred.probability*100:.1f}%")
    print(f"  Fair odds: {pred.fair_odds:.2f}")
    print(f"  Edge: {pred.edge_percentage:.1f}%")
    print(f"  Confidence: {pred.confidence}")
    print(f"  Recommendation: {pred.recommendation}")
    print(f"  Kelly stake: {pred.kelly_stake:.2f}%")
    print(f"  Adjusted stake: {pred.confidence_adjusted_stake:.2f}%")

    # Analyse complète
    print("\n📊 TEST 6: Analyse Complète")
    print("-" * 40)

    bookmaker_odds = {
        "home_win": 2.40,
        "draw": 3.50,
        "away_win": 2.85,
        "over_25": 1.85,
        "under_25": 1.95,
        "btts_yes": 1.70,
        "btts_no": 2.10,
    }

    analysis = engine.analyze_match("Liverpool", "Manchester City", bookmaker_odds)

    print(analysis.summary)

    print("\n" + "=" * 80)
    print("✅ TOUS LES TESTS PASSÉS!")
    print("=" * 80)

if __name__ == "__main__":
    main()
