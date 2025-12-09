"""
═══════════════════════════════════════════════════════════════════════════════
🏦 AGENT DÉFENSE 2.0 - BACKTESTING
   Framework de backtesting avec CLV et Kelly
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config import THRESHOLDS


class Backtester:
    """
    Backtesting framework pour évaluer les stratégies de betting.
    
    MÉTRIQUES:
    - ROI (Return on Investment)
    - CLV (Closing Line Value) - LE PLUS IMPORTANT
    - Win Rate
    - Kelly Growth
    - Max Drawdown
    - Sharpe Ratio
    """
    
    def __init__(self, 
                 min_edge: float = 0.03,
                 max_kelly: float = 0.05,
                 bankroll: float = 1000):
        """
        Args:
            min_edge: Edge minimum pour parier
            max_kelly: Kelly maximum (fraction)
            bankroll: Bankroll initial
        """
        self.min_edge = min_edge
        self.max_kelly = max_kelly
        self.initial_bankroll = bankroll
        self.results = []
    
    def run_backtest(self, 
                     predictions: pd.DataFrame,
                     actuals: pd.DataFrame,
                     odds: pd.DataFrame = None) -> Dict[str, Any]:
        """
        Exécute le backtest.
        
        Args:
            predictions: DataFrame avec colonnes probability par marché
            actuals: DataFrame avec colonnes résultat (0/1) par marché
            odds: DataFrame avec cotes (optionnel, sinon utilise implied)
        
        Returns:
            Dict avec métriques de performance
        """
        self.results = []
        bankroll = self.initial_bankroll
        peak_bankroll = bankroll
        
        for idx in predictions.index:
            for market in predictions.columns:
                if market not in actuals.columns:
                    continue
                
                prob = predictions.loc[idx, market]
                actual = actuals.loc[idx, market]
                
                # Obtenir la cote (ou calculer depuis prob implied)
                if odds is not None and market in odds.columns:
                    odd = odds.loc[idx, market]
                else:
                    # Simuler cote avec marge bookmaker 5%
                    implied_prob = prob
                    odd = 1 / (implied_prob * 1.05) if implied_prob > 0 else 2.0
                
                # Calculer l'edge
                fair_prob = 1 / odd if odd > 0 else 0.5
                edge = prob - fair_prob
                
                # Décider si parier
                if edge < self.min_edge:
                    continue
                
                # Calculer Kelly stake
                kelly = (prob * odd - 1) / (odd - 1) if odd > 1 else 0
                kelly = max(0, min(kelly, self.max_kelly))
                
                stake = bankroll * kelly
                
                if stake < 1:  # Minimum stake
                    continue
                
                # Résultat
                if actual == 1:
                    profit = stake * (odd - 1)
                    won = True
                else:
                    profit = -stake
                    won = False
                
                bankroll += profit
                peak_bankroll = max(peak_bankroll, bankroll)
                
                self.results.append({
                    'index': idx,
                    'market': market,
                    'probability': prob,
                    'actual': actual,
                    'odd': odd,
                    'edge': edge,
                    'kelly': kelly,
                    'stake': stake,
                    'profit': profit,
                    'won': won,
                    'bankroll': bankroll,
                    'drawdown': (peak_bankroll - bankroll) / peak_bankroll
                })
        
        return self._calculate_metrics()
    
    def _calculate_metrics(self) -> Dict[str, Any]:
        """Calcule les métriques de performance."""
        if not self.results:
            return {'error': 'No bets placed'}
        
        df = pd.DataFrame(self.results)
        
        total_stakes = df['stake'].sum()
        total_profit = df['profit'].sum()
        
        metrics = {
            'total_bets': len(df),
            'total_stakes': total_stakes,
            'total_profit': total_profit,
            'roi': total_profit / total_stakes * 100 if total_stakes > 0 else 0,
            
            'win_rate': df['won'].mean() * 100,
            'avg_edge': df['edge'].mean() * 100,
            'avg_odds': df['odd'].mean(),
            
            'final_bankroll': df['bankroll'].iloc[-1],
            'peak_bankroll': df['bankroll'].max(),
            'max_drawdown': df['drawdown'].max() * 100,
            
            'profitable_markets': df.groupby('market')['profit'].sum().to_dict(),
            
            'by_market': {}
        }
        
        # Métriques par marché
        for market in df['market'].unique():
            market_df = df[df['market'] == market]
            metrics['by_market'][market] = {
                'bets': len(market_df),
                'win_rate': market_df['won'].mean() * 100,
                'roi': market_df['profit'].sum() / market_df['stake'].sum() * 100 if market_df['stake'].sum() > 0 else 0,
                'avg_edge': market_df['edge'].mean() * 100
            }
        
        # Sharpe Ratio (annualisé)
        if len(df) > 1:
            returns = df['profit'] / df['stake']
            metrics['sharpe'] = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        
        # CLV simulé (edge moyen = proxy CLV)
        metrics['clv'] = df['edge'].mean() * 100
        
        return metrics
    
    def print_report(self) -> None:
        """Affiche un rapport détaillé."""
        metrics = self._calculate_metrics()
        
        print("\n" + "=" * 80)
        print("📊 RAPPORT DE BACKTEST")
        print("=" * 80)
        
        print(f"""
   📈 PERFORMANCE GLOBALE:
      • Total paris: {metrics['total_bets']}
      • ROI: {metrics['roi']:.2f}%
      • Win Rate: {metrics['win_rate']:.1f}%
      • CLV moyen: {metrics['clv']:.2f}%
      
   💰 BANKROLL:
      • Initial: {self.initial_bankroll:.2f}
      • Final: {metrics['final_bankroll']:.2f}
      • Peak: {metrics['peak_bankroll']:.2f}
      • Max Drawdown: {metrics['max_drawdown']:.1f}%
      
   📊 RISK-ADJUSTED:
      • Sharpe Ratio: {metrics.get('sharpe', 0):.2f}
      • Edge moyen: {metrics['avg_edge']:.2f}%
      • Cote moyenne: {metrics['avg_odds']:.2f}
        """)
        
        print("   📋 PAR MARCHÉ:")
        print(f"      {'Marché':<20} {'Paris':>8} {'Win%':>8} {'ROI':>8} {'Edge':>8}")
        print("      " + "-" * 55)
        
        for market, data in sorted(metrics['by_market'].items(), key=lambda x: -x[1]['roi']):
            print(f"      {market:<20} {data['bets']:>8} {data['win_rate']:>7.1f}% {data['roi']:>7.1f}% {data['avg_edge']:>7.2f}%")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("🧪 Test Backtester")
    
    # Simuler des données
    np.random.seed(42)
    n = 100
    
    # Probabilités prédites (modèle)
    predictions = pd.DataFrame({
        'over_25': np.random.uniform(0.4, 0.7, n),
        'btts': np.random.uniform(0.45, 0.65, n)
    })
    
    # Résultats réels
    actuals = pd.DataFrame({
        'over_25': (np.random.random(n) < 0.55).astype(int),
        'btts': (np.random.random(n) < 0.52).astype(int)
    })
    
    # Cotes
    odds = pd.DataFrame({
        'over_25': np.random.uniform(1.8, 2.1, n),
        'btts': np.random.uniform(1.85, 2.05, n)
    })
    
    # Backtest
    bt = Backtester(min_edge=0.02, max_kelly=0.03)
    metrics = bt.run_backtest(predictions, actuals, odds)
    bt.print_report()
