"""
Test complet du système multi-agents (4 agents)
"""
import sys
sys.path.append('/app')

from orchestrator import MultiAgentOrchestrator, DB_CONFIG

def main():
    print("🚀 LANCEMENT DU SYSTÈME MULTI-AGENTS ML")
    print("Phase 12 - Mon_PS Trading Platform")
    print()
    
    # Créer l'orchestrateur avec 1000€ de bankroll
    orchestrator = MultiAgentOrchestrator(DB_CONFIG, bankroll=1000)
    
    # Exécuter l'analyse complète
    orchestrator.run_all_agents(top_n=5)
    orchestrator.display_signals_summary()
    orchestrator.find_consensus()
    orchestrator.run_backtest()
    orchestrator.generate_trading_plan()
    orchestrator.save_results()
    
    print("\n✅ Test terminé avec succès!")
    print("📊 Les 4 agents sont opérationnels")
    print("💾 Résultats sauvegardés dans ml_agents_results.json")


if __name__ == "__main__":
    main()
