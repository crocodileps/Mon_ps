"""
Orchestrateur Multi-Agents ML avec Ferrari 2.0
Coordonne les 4 agents et intègre le système de variations A/B
"""
import sys
import json
from datetime import datetime
from tabulate import tabulate

sys.path.append('/app')

# Import des agents
from agents.agent_anomaly import AnomalyDetectorAgent
from agents.agent_spread import SpreadOptimizerAgent
from agents.agent_pattern import PatternMatcherAgent
from agents.agent_backtest import BacktestAgent

# Import Ferrari 2.0
from services.ferrari_middleware import get_ferrari_middleware, ferrari_middleware
from services.ferrari_integration import ferrari_service

# Configuration DB
DB_CONFIG = {
    'host': 'monps_postgres',
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}

class MultiAgentOrchestratorFerrari:
    """
    Orchestrateur Ferrari 2.0 qui coordonne les agents avec tests A/B
    """

    def __init__(self, db_config, bankroll=1000, ferrari_enabled=True):
        self.db_config = db_config
        self.bankroll = bankroll
        
        # Ferrari 2.0 Integration
        self.ferrari_enabled = ferrari_enabled
        self.ferrari_middleware = get_ferrari_middleware(db_config)
        
        # Configurer Ferrari
        ferrari_service.set_enabled(ferrari_enabled)

        # Initialiser les agents (sans Agent B si Ferrari actif)
        self.agents = {
            'Agent A (Anomaly)': AnomalyDetectorAgent(db_config),
            'Agent C (Pattern)': PatternMatcherAgent(db_config),
            'Agent D (Backtest)': BacktestAgent(db_config, bankroll)
        }
        
        # Agent B géré séparément (Ferrari ou normal)
        if not ferrari_enabled:
            self.agents['Agent B (Spread)'] = SpreadOptimizerAgent(db_config)

        self.signals = {}
        self.comparison = None

    def run_all_agents(self, top_n=5):
        """Exécute tous les agents et collecte leurs signaux"""
        print("\n" + "="*80)
        if self.ferrari_enabled:
            print("🏎️ SYSTÈME MULTI-AGENTS ML - Mon_PS avec FERRARI 2.0")
        else:
            print("🤖 SYSTÈME MULTI-AGENTS ML - Mon_PS")
        print("="*80)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Bankroll: {self.bankroll}€")
        print(f"Ferrari 2.0: {'✅ ACTIVÉ' if self.ferrari_enabled else '❌ Désactivé'}")
        print()

        # Exécuter agents standards (A, C, D)
        for agent_name, agent in self.agents.items():
            try:
                print(f"\n🔄 Exécution {agent_name}...")
                signals = agent.generate_signals(top_n=top_n)
                self.signals[agent_name] = signals
                print(f"✅ {agent_name}: {len(signals)} signaux générés")
            except Exception as e:
                print(f"❌ {agent_name}: Erreur - {e}")
                self.signals[agent_name] = []

        # Agent B : Ferrari ou Normal
        if self.ferrari_enabled:
            self._run_agent_b_ferrari()
        
        return self.signals

    def _run_agent_b_ferrari(self):
        """Exécute Agent B avec Ferrari 2.0"""
        print(f"\n🏎️ Exécution Agent B Ferrari 2.0...")
        
        try:
            # Utiliser middleware Ferrari
            signals = self.ferrari_middleware.process_opportunities()
            
            if signals:
                # Grouper par variation
                variations = {}
                for signal in signals:
                    var_id = signal.get('variation_id', 'unknown')
                    if var_id not in variations:
                        variations[var_id] = []
                    variations[var_id].append(signal)
                
                print(f"✅ Agent B Ferrari: {len(signals)} signaux générés")
                print(f"   → Répartis sur {len(variations)} variations")
                
                for var_id, var_signals in variations.items():
                    print(f"      Variation {var_id}: {len(var_signals)} signaux")
                
                self.signals['Agent B (Ferrari 2.0)'] = signals
            else:
                print("⚠️ Agent B Ferrari: Aucun signal généré")
                self.signals['Agent B (Ferrari 2.0)'] = []
                
        except Exception as e:
            print(f"❌ Agent B Ferrari: Erreur - {e}")
            import traceback
            traceback.print_exc()
            self.signals['Agent B (Ferrari 2.0)'] = []

    def display_signals_summary(self):
        """Affiche un résumé des signaux de chaque agent"""
        print("\n" + "="*80)
        print("📊 RÉSUMÉ DES SIGNAUX PAR AGENT")
        print("="*80 + "\n")

        for agent_name, signals in self.signals.items():
            print(f"\n🎯 {agent_name} - {len(signals)} signaux:")

            if len(signals) == 0:
                print("   Aucun signal")
                continue

            # Top 3 signaux
            for i, signal in enumerate(signals[:3], 1):
                print(f"\n   Signal #{i}:")
                print(f"     Match: {signal['match']}")
                print(f"     Direction: {signal['direction']}")
                print(f"     Confiance: {signal['confidence']:.1f}%")

                # Info spécifique Agent B Ferrari
                if 'ferrari_enabled' in signal and signal['ferrari_enabled']:
                    print(f"     🏎️ Variation: #{signal['variation_id']}")
                    print(f"     Assignment ID: {signal['assignment_id']}")
                    print(f"     Facteurs: {len(signal['variation_config'].get('enabled_factors', []))}")
                    if signal.get('kelly_fraction'):
                        print(f"     Mise Kelly: {signal['recommended_stake_pct']:.1f}% bankroll")
                        print(f"     EV: {signal['expected_value']:.3f}")
                elif 'kelly_fraction' in signal:
                    print(f"     Mise Kelly: {signal['recommended_stake_pct']:.1f}% bankroll")
                    print(f"     EV: {signal['expected_value']:.3f}")
                elif 'pattern_type' in signal:
                    print(f"     Pattern: {signal['pattern_type']}")

    def display_ferrari_stats(self):
        """Affiche les stats Ferrari 2.0"""
        if not self.ferrari_enabled:
            return
        
        print("\n" + "="*80)
        print("🏎️ FERRARI 2.0 - STATISTIQUES VARIATIONS")
        print("="*80 + "\n")
        
        # Récupérer stats depuis API
        try:
            import requests
            
            # Récupérer améliorations actives
            improvements = ferrari_service.get_active_improvements()
            
            if not improvements:
                print("Aucune amélioration active")
                return
            
            for imp in improvements:
                print(f"\n📊 Amélioration #{imp['id']}: {imp['agent_name']}")
                
                # Récupérer variations
                response = requests.get(
                    f"http://monps_backend:8000/strategies/improvements/{imp['id']}/variations"
                )
                
                if response.status_code == 200:
                    data = response.json()
                    variations = data['variations']
                    
                    print(f"   Total variations: {len(variations)}")
                    
                    for var in variations:
                        status = "🎯 CONTRÔLE" if var['is_control'] else "🔬 TEST"
                        print(f"\n   {status} Variation {var['id']}: {var['name']}")
                        print(f"      Matchs testés: {var['matches_tested']}")
                        print(f"      Win Rate: {var['win_rate']:.1f}%")
                        print(f"      Profit: {var['total_profit']:.2f}€")
                        print(f"      ROI: {var['roi']:.1f}%")
                        print(f"      Trafic: {var['traffic_percentage']}%")
                
        except Exception as e:
            print(f"Erreur récupération stats Ferrari: {e}")

    def record_bet_result(self, signal: dict, outcome: str, profit: float, stake: float):
        """
        Enregistre le résultat d'un pari
        
        Args:
            signal: Signal original généré
            outcome: 'win', 'loss', ou 'void'
            profit: Profit réalisé (négatif si perte)
            stake: Mise
        """
        # Si signal Ferrari, enregistrer via middleware
        if signal.get('ferrari_enabled') and signal.get('assignment_id'):
            assignment_id = signal['assignment_id']
            odds = signal['odds']['avg']
            
            success = self.ferrari_middleware.record_bet_result(
                assignment_id=assignment_id,
                outcome=outcome,
                profit=profit,
                stake=stake,
                odds=odds
            )
            
            if success:
                print(f"✅ Résultat Ferrari enregistré: {outcome} ({profit:+.2f}€)")
            else:
                print(f"❌ Erreur enregistrement résultat Ferrari")
        else:
            print(f"ℹ️ Résultat non-Ferrari: {outcome} ({profit:+.2f}€)")


def main():
    """Point d'entrée avec Ferrari"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Orchestrateur Multi-Agents avec Ferrari 2.0')
    parser.add_argument('--ferrari', action='store_true', help='Activer Ferrari 2.0')
    parser.add_argument('--no-ferrari', action='store_true', help='Désactiver Ferrari 2.0')
    parser.add_argument('--top-n', type=int, default=5, help='Nombre de signaux par agent')
    
    args = parser.parse_args()
    
    # Déterminer si Ferrari actif
    ferrari_enabled = True  # Par défaut activé
    if args.no_ferrari:
        ferrari_enabled = False
    elif args.ferrari:
        ferrari_enabled = True
    
    # Créer orchestrateur
    orchestrator = MultiAgentOrchestratorFerrari(
        DB_CONFIG, 
        bankroll=5000,
        ferrari_enabled=ferrari_enabled
    )
    
    # Exécuter agents
    orchestrator.run_all_agents(top_n=args.top_n)
    
    # Afficher résumé
    orchestrator.display_signals_summary()
    
    # Afficher stats Ferrari si activé
    if ferrari_enabled:
        orchestrator.display_ferrari_stats()
    
    print("\n" + "="*80)
    print("✅ Orchestration terminée")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()

