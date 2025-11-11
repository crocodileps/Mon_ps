"""
Agent D : Backtest Engine
Teste et évalue les stratégies sur données historiques
"""
import numpy as np
import pandas as pd
import psycopg2
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class BacktestAgent:
    """
    Agent D : Backtesting des stratégies
    
    Stratégie :
    - Simule les 3 autres agents sur données passées
    - Calcule ROI, Sharpe ratio, Win rate
    - Compare les performances
    """
    
    def __init__(self, db_config, initial_bankroll=1000):
        self.db_config = db_config
        self.initial_bankroll = initial_bankroll
        self.name = "Backtest Engine"
        
    def fetch_historical_data(self, hours=24):
        """Récupère les données historiques pour backtest"""
        conn = psycopg2.connect(**self.db_config)
        
        # Récupérer les opportunités avec évolution temporelle
        query = """
            SELECT 
                match_id,
                sport,
                home_team,
                away_team,
                bookmaker,
                home_odds,
                away_odds,
                draw_odds,
                collected_at
            FROM odds_history
            WHERE collected_at >= NOW() - INTERVAL '%s hours'
            ORDER BY collected_at ASC
        """
        
        df = pd.read_sql(query, conn, params=(hours,))
        conn.close()
        
        return df
    
    def simulate_strategy(self, strategy_name, signals, actual_outcomes=None):
        """
        Simule une stratégie de trading
        
        Args:
            strategy_name: Nom de la stratégie (Agent A/B/C)
            signals: Liste des signaux générés
            actual_outcomes: Résultats réels (None pour simulation)
        
        Returns:
            Dict avec métriques de performance
        """
        bankroll = self.initial_bankroll
        trades = []
        bankroll_history = [bankroll]
        
        for signal in signals:
            # Pour l'instant, on simule avec des probabilités
            # TODO: Remplacer par vrais résultats quand disponibles
            
            # Simuler un pari
            stake_pct = signal.get('recommended_stake_pct', 5.0)  # 5% par défaut
            stake = (stake_pct / 100) * bankroll
            
            # Limiter le stake à 10% max du bankroll pour sécurité
            stake = min(stake, bankroll * 0.10)
            
            if stake > bankroll:
                continue  # Skip si pas assez de bankroll
            
            # Simuler le résultat (50% win pour l'instant)
            # TODO: Utiliser vrais résultats
            win_probability = signal.get('win_probability', 0.5)
            won = np.random.random() < win_probability
            
            if won:
                # Récupérer les cotes
                if 'odds' in signal:
                    if isinstance(signal['odds'], dict):
                        odds = signal['odds'].get('max', 2.0)
                    else:
                        odds = signal['odds']
                else:
                    odds = 2.0
                
                profit = stake * (odds - 1)
                bankroll += profit
                result = 'WIN'
            else:
                bankroll -= stake
                profit = -stake
                result = 'LOSS'
            
            trade = {
                'match': signal['match'],
                'direction': signal['direction'],
                'stake': stake,
                'profit': profit,
                'bankroll': bankroll,
                'result': result
            }
            
            trades.append(trade)
            bankroll_history.append(bankroll)
        
        # Calculer métriques
        if len(trades) == 0:
            return self._empty_metrics(strategy_name)
        
        total_profit = bankroll - self.initial_bankroll
        roi = (total_profit / self.initial_bankroll) * 100
        
        wins = [t for t in trades if t['result'] == 'WIN']
        losses = [t for t in trades if t['result'] == 'LOSS']
        
        win_rate = (len(wins) / len(trades)) * 100 if trades else 0
        
        avg_win = np.mean([t['profit'] for t in wins]) if wins else 0
        avg_loss = np.mean([abs(t['profit']) for t in losses]) if losses else 0
        
        # Calculer Sharpe Ratio (simplifié)
        returns = np.diff(bankroll_history) / bankroll_history[:-1]
        sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if len(returns) > 1 and np.std(returns) > 0 else 0
        
        # Max Drawdown
        peak = np.maximum.accumulate(bankroll_history)
        drawdown = (peak - bankroll_history) / peak
        max_drawdown = np.max(drawdown) * 100 if len(drawdown) > 0 else 0
        
        metrics = {
            'strategy': strategy_name,
            'initial_bankroll': self.initial_bankroll,
            'final_bankroll': bankroll,
            'total_profit': total_profit,
            'roi': roi,
            'total_trades': len(trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': abs(avg_win / avg_loss) if avg_loss > 0 else 0,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'trades': trades
        }
        
        return metrics
    
    def _empty_metrics(self, strategy_name):
        """Retourne des métriques vides"""
        return {
            'strategy': strategy_name,
            'initial_bankroll': self.initial_bankroll,
            'final_bankroll': self.initial_bankroll,
            'total_profit': 0,
            'roi': 0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'profit_factor': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'trades': []
        }
    
    def compare_strategies(self, agents_signals):
        """
        Compare les performances de plusieurs stratégies
        
        Args:
            agents_signals: Dict {agent_name: signals_list}
        
        Returns:
            DataFrame avec comparaison des performances
        """
        logger.info(f"[{self.name}] Comparaison de {len(agents_signals)} stratégies...")
        
        results = []
        
        for agent_name, signals in agents_signals.items():
            metrics = self.simulate_strategy(agent_name, signals)
            results.append(metrics)
        
        # Créer DataFrame pour comparaison
        df = pd.DataFrame(results)
        
        # Trier par ROI
        if len(df) > 0:
            df = df.sort_values('roi', ascending=False)
        
        return df
    
    def generate_report(self, comparison_df):
        """
        Génère un rapport de comparaison des agents
        
        Returns:
            Dict avec recommandations
        """
        if len(comparison_df) == 0:
            return {'recommendation': 'Aucune donnée disponible'}
        
        best_roi = comparison_df.iloc[0]
        best_sharpe = comparison_df.loc[comparison_df['sharpe_ratio'].idxmax()]
        best_winrate = comparison_df.loc[comparison_df['win_rate'].idxmax()]
        
        report = {
            'best_roi': {
                'agent': best_roi['strategy'],
                'value': best_roi['roi'],
                'profit': best_roi['total_profit']
            },
            'best_sharpe': {
                'agent': best_sharpe['strategy'],
                'value': best_sharpe['sharpe_ratio']
            },
            'best_winrate': {
                'agent': best_winrate['strategy'],
                'value': best_winrate['win_rate']
            },
            'recommendation': self._make_recommendation(comparison_df)
        }
        
        return report
    
    def _make_recommendation(self, df):
        """Génère une recommandation basée sur les résultats"""
        if len(df) == 0:
            return "Pas assez de données pour recommandation"
        
        best = df.iloc[0]
        
        if best['roi'] > 10:
            return f"✅ Agent {best['strategy']} recommandé (ROI: {best['roi']:.2f}%)"
        elif best['roi'] > 0:
            return f"⚠️ Agent {best['strategy']} positif mais conservateur (ROI: {best['roi']:.2f}%)"
        else:
            return f"❌ Toutes les stratégies négatives - Besoin d'optimisation"
    
    def generate_signals(self, top_n=5):
        """
        Génère des signaux basés sur le backtesting
        
        Retourne les meilleurs trades historiques
        """
        logger.info(f"[{self.name}] Analyse backtest...")
        
        # Pour l'instant, retourne des recommandations générales
        signals = [{
            'agent': self.name,
            'match': 'Analyse globale',
            'sport': 'all',
            'direction': 'BACKTEST',
            'confidence': 75,
            'reason': 'Simulation sur données historiques - Résultats en cours'
        }]
        
        return signals
