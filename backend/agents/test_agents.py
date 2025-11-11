"""
Script de test pour Agent A (Anomaly) et Agent B (Spread)
"""
import os
import sys
import json
from datetime import datetime

# Configuration DB
DB_CONFIG = {
    'host': 'monps_postgres',
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}

# Import des agents
sys.path.append('/app')
from agent_anomaly import AnomalyDetectorAgent
from agent_spread import SpreadOptimizerAgent


def print_separator(title):
    """Affiche un séparateur"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def test_anomaly_agent():
    """Teste l'Agent A - Anomaly Detector"""
    print_separator("🔍 TEST AGENT A : ANOMALY DETECTOR")
    
    agent = AnomalyDetectorAgent(DB_CONFIG)
    
    try:
        # Générer signaux
        signals = agent.generate_signals(top_n=5)
        
        if len(signals) == 0:
            print("❌ Aucun signal généré par Agent A")
            return None
        
        print(f"✅ Agent A a généré {len(signals)} signaux\n")
        
        for i, signal in enumerate(signals, 1):
            print(f"Signal #{i}:")
            print(f"  Match: {signal['match']}")
            print(f"  Sport: {signal['sport']}")
            print(f"  Bookmaker: {signal['bookmaker']}")
            print(f"  Direction: {signal['direction']}")
            print(f"  Confiance: {signal['confidence']:.1f}%")
            print(f"  Cotes: Home={signal['odds']['home']:.2f}, Away={signal['odds']['away']:.2f}")
            print(f"  Raison: {signal['reason']}")
            print()
        
        return signals
        
    except Exception as e:
        print(f"❌ Erreur Agent A: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_spread_agent():
    """Teste l'Agent B - Spread Optimizer"""
    print_separator("📊 TEST AGENT B : SPREAD OPTIMIZER")
    
    agent = SpreadOptimizerAgent(DB_CONFIG, min_spread=2.0)
    
    try:
        # Générer signaux
        signals = agent.generate_signals(top_n=5)
        
        if len(signals) == 0:
            print("❌ Aucun signal généré par Agent B")
            return None
        
        print(f"✅ Agent B a généré {len(signals)} signaux\n")
        
        for i, signal in enumerate(signals, 1):
            print(f"Signal #{i}:")
            print(f"  Match: {signal['match']}")
            print(f"  Sport: {signal['sport']}")
            print(f"  Direction: {signal['direction']}")
            print(f"  Confiance: {signal['confidence']:.1f}%")
            print(f"  Spread: {signal['spread_pct']:.2f}%")
            print(f"  Cote max: {signal['odds']['max']:.2f}")
            print(f"  Prob victoire: {signal['win_probability']*100:.1f}%")
            print(f"  Kelly fraction: {signal['kelly_fraction']*100:.1f}%")
            print(f"  Mise recommandée: {signal['recommended_stake_pct']:.1f}% du bankroll")
            print(f"  Expected Value: {signal['expected_value']:.3f}")
            print(f"  Bookmakers: {signal['bookmaker_count']}")
            print(f"  Raison: {signal['reason']}")
            print()
        
        return signals
        
    except Exception as e:
        print(f"❌ Erreur Agent B: {e}")
        import traceback
        traceback.print_exc()
        return None


def compare_agents(signals_a, signals_b):
    """Compare les résultats des 2 agents"""
    print_separator("⚔️ COMPARAISON DES AGENTS")
    
    if not signals_a and not signals_b:
        print("❌ Aucun signal à comparer")
        return
    
    print(f"Agent A (Anomaly)  : {len(signals_a) if signals_a else 0} signaux")
    print(f"Agent B (Spread)   : {len(signals_b) if signals_b else 0} signaux")
    print()
    
    # Trouver les matchs en commun
    if signals_a and signals_b:
        matches_a = {s['match'] for s in signals_a}
        matches_b = {s['match'] for s in signals_b}
        common = matches_a & matches_b
        
        if common:
            print(f"🎯 {len(common)} matchs identifiés par les DEUX agents:")
            for match in common:
                print(f"  - {match}")
            print()
        
        # Top signal de chaque agent
        if signals_a:
            top_a = signals_a[0]
            print(f"🥇 Meilleur signal Agent A:")
            print(f"   {top_a['match']} - {top_a['direction']}")
            print(f"   Confiance: {top_a['confidence']:.1f}%")
            print()
        
        if signals_b:
            top_b = signals_b[0]
            print(f"🥇 Meilleur signal Agent B:")
            print(f"   {top_b['match']} - {top_b['direction']}")
            print(f"   Confiance: {top_b['confidence']:.1f}%")
            print(f"   Mise: {top_b['recommended_stake_pct']:.1f}% bankroll")
            print()


def main():
    """Fonction principale de test"""
    print_separator("�� TEST SYSTÈME MULTI-AGENTS ML - PHASE 12")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Database: {DB_CONFIG['database']}@{DB_CONFIG['host']}")
    print()
    
    # Test Agent A
    signals_a = test_anomaly_agent()
    
    # Test Agent B
    signals_b = test_spread_agent()
    
    # Comparaison
    compare_agents(signals_a, signals_b)
    
    # Résumé
    print_separator("📋 RÉSUMÉ")
    
    success_count = sum([
        signals_a is not None,
        signals_b is not None
    ])
    
    print(f"Agents testés: 2")
    print(f"Agents fonctionnels: {success_count}/2")
    print()
    
    if success_count == 2:
        print("✅ Tous les agents fonctionnent correctement!")
        print("📈 Prochaine étape: Créer les Agents C et D")
    elif success_count == 1:
        print("⚠️ 1 agent fonctionne, l'autre a des erreurs")
    else:
        print("❌ Les 2 agents ont des erreurs - vérifier la configuration")
    
    print()


if __name__ == "__main__":
    main()
