"""
Orchestrateur Multi-Agents ML
Coordonne les 4 agents et compare leurs performances
"""
import sys
import json
from datetime import datetime
from tabulate import tabulate

sys.path.append('/app')

# Import des agents
from agent_anomaly import AnomalyDetectorAgent
from agent_spread import SpreadOptimizerAgent
from agent_pattern import PatternMatcherAgent
from agent_backtest import BacktestAgent

# Configuration DB
DB_CONFIG = {
    'host': 'monps_postgres',
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}


class MultiAgentOrchestrator:
    """
    Orchestrateur qui coordonne les 4 agents ML
    """
    
    def __init__(self, db_config, bankroll=1000):
        self.db_config = db_config
        self.bankroll = bankroll
        
        # Initialiser les agents
        self.agents = {
            'Agent A (Anomaly)': AnomalyDetectorAgent(db_config),
            'Agent B (Spread)': SpreadOptimizerAgent(db_config),
            'Agent C (Pattern)': PatternMatcherAgent(db_config),
            'Agent D (Backtest)': BacktestAgent(db_config, bankroll)
        }
        
        self.signals = {}
        self.comparison = None
    
    def run_all_agents(self, top_n=5):
        """Exécute tous les agents et collecte leurs signaux"""
        print("\n" + "="*80)
        print("🤖 SYSTÈME MULTI-AGENTS ML - Mon_PS")
        print("="*80)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Bankroll: {self.bankroll}€")
        print()
        
        for agent_name, agent in self.agents.items():
            try:
                print(f"\n🔄 Exécution {agent_name}...")
                signals = agent.generate_signals(top_n=top_n)
                self.signals[agent_name] = signals
                print(f"✅ {agent_name}: {len(signals)} signaux générés")
            except Exception as e:
                print(f"❌ {agent_name}: Erreur - {e}")
                self.signals[agent_name] = []
    
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
                
                # Info spécifique selon l'agent
                if agent_name == 'Agent B (Spread)' and 'kelly_fraction' in signal:
                    print(f"     Mise Kelly: {signal['recommended_stake_pct']:.1f}% bankroll")
                    print(f"     EV: {signal['expected_value']:.3f}")
                elif agent_name == 'Agent C (Pattern)' and 'pattern_type' in signal:
                    print(f"     Pattern: {signal['pattern_type']}")
    
    def find_consensus(self):
        """Trouve les signaux sur lesquels plusieurs agents sont d'accord"""
        print("\n" + "="*80)
        print("🎯 CONSENSUS INTER-AGENTS")
        print("="*80 + "\n")
        
        # Extraire tous les matchs
        all_matches = {}
        
        for agent_name, signals in self.signals.items():
            for signal in signals:
                match = signal['match']
                if match not in all_matches:
                    all_matches[match] = []
                all_matches[match].append({
                    'agent': agent_name,
                    'direction': signal['direction'],
                    'confidence': signal['confidence']
                })
        
        # Trouver les matchs avec consensus (2+ agents)
        consensus = {m: agents for m, agents in all_matches.items() if len(agents) >= 2}
        
        if len(consensus) == 0:
            print("❌ Aucun consensus trouvé entre les agents")
            return
        
        print(f"✅ {len(consensus)} match(s) avec consensus:\n")
        
        for match, agents in consensus.items():
            print(f"🔥 {match}")
            print(f"   Identifié par {len(agents)} agents:")
            
            for agent_info in agents:
                print(f"     - {agent_info['agent']}: {agent_info['direction']} "
                      f"(confiance: {agent_info['confidence']:.1f}%)")
            
            # Calculer la direction majoritaire
            directions = [a['direction'] for a in agents]
            if len(set(directions)) == 1:
                print(f"   ✅ CONSENSUS FORT: Tous recommandent {directions[0]}")
            else:
                print(f"   ⚠️  Directions divergentes")
            print()
    
    def run_backtest(self):
        """Exécute le backtest et compare les performances"""
        print("\n" + "="*80)
        print("📈 BACKTEST COMPARATIVE")
        print("="*80 + "\n")
        
        backtest_agent = self.agents['Agent D (Backtest)']
        
        # Préparer les signaux pour backtest (exclure Agent D)
        agents_to_test = {
            name: signals 
            for name, signals in self.signals.items() 
            if name != 'Agent D (Backtest)' and len(signals) > 0
        }
        
        if len(agents_to_test) == 0:
            print("❌ Pas assez de signaux pour backtest")
            return
        
        # Comparer les stratégies
        comparison = backtest_agent.compare_strategies(agents_to_test)
        self.comparison = comparison
        
        # Afficher les résultats
        print("Résultats de simulation (bankroll initial: {}€):\n".format(self.bankroll))
        
        # Préparer le tableau
        table_data = []
        for idx, row in comparison.iterrows():
            table_data.append([
                row['strategy'],
                f"{row['final_bankroll']:.2f}€",
                f"{row['roi']:.2f}%",
                f"{row['win_rate']:.1f}%",
                row['total_trades'],
                f"{row['sharpe_ratio']:.2f}",
                f"{row['max_drawdown']:.1f}%"
            ])
        
        headers = ['Agent', 'Bankroll Final', 'ROI', 'Win Rate', 'Trades', 'Sharpe', 'Drawdown']
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
        
        # Recommandation
        print("\n")
        report = backtest_agent.generate_report(comparison)
        print(f"💡 {report['recommendation']}")
        print()
        
        print(f"🏆 Meilleur ROI: {report['best_roi']['agent']} "
              f"({report['best_roi']['value']:.2f}%, +{report['best_roi']['profit']:.2f}€)")
        print(f"📊 Meilleur Sharpe: {report['best_sharpe']['agent']} "
              f"({report['best_sharpe']['value']:.2f})")
        print(f"🎯 Meilleur Win Rate: {report['best_winrate']['agent']} "
              f"({report['best_winrate']['value']:.1f}%)")
    
    def generate_trading_plan(self):
        """Génère un plan de trading basé sur tous les agents"""
        print("\n" + "="*80)
        print("📋 PLAN DE TRADING RECOMMANDÉ")
        print("="*80 + "\n")
        
        # Utiliser les signaux de l'agent avec le meilleur ROI
        if self.comparison is not None and len(self.comparison) > 0:
            best_agent_name = self.comparison.iloc[0]['strategy']
            best_signals = self.signals.get(best_agent_name, [])
            
            print(f"Basé sur les performances de: {best_agent_name}\n")
            
            if len(best_signals) == 0:
                print("❌ Aucun signal disponible")
                return
            
            total_allocation = 0
            
            print("Recommandations de paris:\n")
            for i, signal in enumerate(best_signals[:5], 1):
                stake_pct = signal.get('recommended_stake_pct', 5.0)
                stake = (stake_pct / 100) * self.bankroll
                total_allocation += stake_pct
                
                # Parser le match pour extraire les équipes
                match_parts = signal['match'].split(' vs ')
                home_team = match_parts[0] if len(match_parts) > 0 else "Home"
                away_team = match_parts[1] if len(match_parts) > 1 else "Away"
                
                # Déterminer l'équipe à parier
                if signal['direction'] == 'BACK_HOME':
                    bet_on = f"🏠 {home_team} gagne"
                elif signal['direction'] == 'BACK_AWAY':
                    bet_on = f"✈️  {away_team} gagne"
                elif signal['direction'] == 'BACK_DRAW':
                    bet_on = "🤝 Match nul"
                else:
                    bet_on = signal['direction']
                
                print(f"{i}. {signal['match']}")
                print(f"   💰 PARIER SUR : {bet_on}")
                print(f"   💵 Mise recommandée : {stake:.2f}€ ({stake_pct:.1f}% de votre bankroll)")
                print(f"   ✅ Confiance : {signal['confidence']:.1f}%")
                if 'expected_value' in signal:
                    ev_emoji = "🔥" if signal['expected_value'] > 1 else "��"
                    print(f"   {ev_emoji} Valeur attendue (EV) : {signal['expected_value']:.2f}")
                if 'odds' in signal and isinstance(signal['odds'], dict):
                    if 'max' in signal['odds']:
                        print(f"   📊 Cote maximum : {signal['odds']['max']:.2f}")
                print()
            
            print(f"📊 Allocation totale: {total_allocation:.1f}% du bankroll")
            print(f"💰 Capital alloué: {(total_allocation/100)*self.bankroll:.2f}€")
            print(f"💵 Capital en réserve: {self.bankroll - (total_allocation/100)*self.bankroll:.2f}€")
        else:
            print("❌ Backtest non disponible - Impossible de générer un plan")
    
    def save_results(self, filename='/mnt/user-data/outputs/ml_agents_results.json'):
        """Sauvegarde les résultats en JSON"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'bankroll': self.bankroll,
            'signals': {
                agent_name: [
                    {k: str(v) if isinstance(v, datetime) else v 
                     for k, v in signal.items()}
                    for signal in signals
                ]
                for agent_name, signals in self.signals.items()
            },
            'comparison': self.comparison.to_dict('records') if self.comparison is not None else None
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Résultats sauvegardés: {filename}")



    async def send_best_opportunities_telegram(self):
        """
        Envoie les meilleures opportunités sur Telegram
        Basé sur l agent avec le meilleur ROI
        """
        from services.telegram_bot import get_telegram_bot
        import logging
        
        logger = logging.getLogger(__name__)
        bot = get_telegram_bot()
        
        if self.comparison is None or len(self.comparison) == 0:
            return {"status": "error", "message": "Backtest requis"}
        
        best_agent_name = self.comparison.iloc[0]["strategy"]
        best_signals = self.signals.get(best_agent_name, [])
        
        if not best_signals:
            return {"status": "no_signals"}
        
        sent_count = 0
        def get_best_bookmaker(home_team, away_team, direction):
            """Récupère le meilleur bookmaker pour cette opportunité"""
            import psycopg2
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            if direction == 'BACK_HOME':
                odds_col = 'home_odds'
            elif direction == 'BACK_AWAY':
                odds_col = 'away_odds'
            else:
                odds_col = 'draw_odds'
            
            query = f"""
                SELECT bookmaker, {odds_col}
                FROM odds_history
                WHERE home_team = %s AND away_team = %s
                AND {odds_col} IS NOT NULL
                ORDER BY {odds_col} DESC
                LIMIT 1
            """
            
            cursor.execute(query, (home_team, away_team))
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result else "Bookmaker inconnu"
        for signal in best_signals[:3]:
            try:
                match_parts = signal["match"].split(" vs ")
                home_team = match_parts[0] if len(match_parts) > 0 else "Home"
                away_team = match_parts[1] if len(match_parts) > 1 else "Away"
                best_bookmaker = get_best_bookmaker(home_team, away_team, signal["direction"])
                if signal["direction"] == "BACK_HOME":
                    selection = f"{home_team} Gagnant"
                elif signal["direction"] == "BACK_AWAY":
                    selection = f"{match_parts[1]} Gagnant"
                else:
                    selection = "Match Nul"
                
                stake_pct = signal.get("recommended_stake_pct", 5.0)
                stake = (stake_pct / 100) * self.bankroll
                confidence = signal.get("confidence", 50)
                risk_level = "LOW" if confidence >= 80 else "MEDIUM" if confidence >= 60 else "HIGH"
                
                opportunity = {
                    "id": f"orchestrator_{hash(signal['match'])}",
                    "match": signal["match"],
                    "league": signal.get("sport", "Sport"),
                    "commence_time": "Prochainement",
                    "bet_type": "1X2",
                    "selection": selection,
                    "odds": signal["odds"]["avg"] if isinstance(signal.get("odds"), dict) else 2.0,
                    "bookmaker": best_bookmaker,
                    "edge": signal.get("spread_pct", 0),
                    "kelly_stake": int(stake),
                    "kelly_percent": round(stake_pct, 2),
                    "confidence": int(confidence),
                    "risk_level": risk_level,
                    "agent_name": f"Agent Patron (via {best_agent_name})",
                    "analysis": signal.get("reason", "Sélectionné par orchestrator")
                }
                
                await bot.send_opportunity_alert(opportunity)
                sent_count += 1
            except Exception as e:
                logger.error(f"Erreur: {e}")
        
        return {"status": "sent", "opportunities_sent": sent_count}

def main():
    """Fonction principale"""
    orchestrator = MultiAgentOrchestrator(DB_CONFIG, bankroll=1000)
    
    # Étape 1: Exécuter tous les agents
    orchestrator.run_all_agents(top_n=5)
    
    # Étape 2: Afficher résumé des signaux
    orchestrator.display_signals_summary()
    
    # Étape 3: Trouver consensus
    orchestrator.find_consensus()
    
    # Étape 4: Backtest comparatif
    orchestrator.run_backtest()
    
    # Étape 5: Plan de trading
    orchestrator.generate_trading_plan()
    
    # Étape 6: Sauvegarder résultats
    orchestrator.save_results()
    
    print("\n" + "="*80)
    print("✅ ANALYSE TERMINÉE")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
