"""
Agent B : Spread Optimizer
Optimise les paris basés sur les spreads et Kelly Criterion
"""
import numpy as np
import pandas as pd
import psycopg2
import logging

logger = logging.getLogger(__name__)


class SpreadOptimizerAgent:
    """
    Agent B : Optimisation des spreads avec Kelly Criterion
    
    Stratégie :
    - Identifie les spreads les plus élevés
    - Calcule la taille optimale du pari (Kelly)
    - Score basé sur EV (Expected Value)
    """
    
    def __init__(self, db_config, min_spread=2.0):
        self.db_config = db_config
        self.min_spread = min_spread
        self.name = "Spread Optimizer"
        
    def fetch_opportunities(self):
        """Récupère les opportunités actuelles"""
        conn = psycopg2.connect(**self.db_config)
        query = """
            SELECT 
                sport,
                home_team,
                away_team,
                home_spread_pct,
                away_spread_pct,
                draw_spread_pct,
                bookmaker_count,
                max_home_odds,
                min_home_odds,
                max_away_odds,
                min_away_odds,
                max_draw_odds,
                min_draw_odds
            FROM v_current_opportunities
            WHERE GREATEST(
                home_spread_pct, 
                away_spread_pct, 
                COALESCE(draw_spread_pct, 0)
            ) >= %s
            ORDER BY GREATEST(
                home_spread_pct, 
                away_spread_pct, 
                COALESCE(draw_spread_pct, 0)
            ) DESC
        """
        df = pd.read_sql(query, conn, params=(self.min_spread,))
        conn.close()
        return df
    
    def calculate_kelly_criterion(self, odds, win_probability):
        """
        Calcule la fraction Kelly
        
        Kelly % = (odds * p - 1) / (odds - 1)
        où p = probabilité de gagner
        """
        if win_probability <= 0 or win_probability >= 1:
            return 0.0
        
        b = odds - 1  # Net odds
        p = win_probability
        q = 1 - p
        
        kelly = (b * p - q) / b
        
        # Fractional Kelly (25% pour réduire risque)
        return max(0, kelly * 0.25)
    
    def estimate_win_probability(self, max_odds, min_odds, spread_pct):
        """
        Estime la probabilité de gagner basée sur le spread
        
        Logique :
        - Plus le spread est élevé, plus on a confiance
        - On utilise la cote moyenne comme base
        """
        avg_odds = (max_odds + min_odds) / 2
        
        # Probabilité implicite moyenne
        implied_prob = 1 / avg_odds
        
        # Ajustement basé sur le spread
        # Spread élevé = sous-évaluation = augmentation de prob
        spread_factor = 1 + (spread_pct / 100)
        
        adjusted_prob = implied_prob * spread_factor
        
        # Cap à 0.95 pour rester réaliste
        return min(adjusted_prob, 0.95)
    
    def calculate_expected_value(self, odds, win_prob):
        """
        Calcule l'EV (Expected Value)
        
        EV = (odds * win_prob) - 1
        """
        return (odds * win_prob) - 1
    
    def generate_signals(self, top_n=10):
        """
        Génère des signaux optimisés avec Kelly sizing
        
        Returns:
            List de signaux avec taille de pari recommandée
        """
        logger.info(f"[{self.name}] Génération signaux...")
        
        df = self.fetch_opportunities()
        
        if len(df) == 0:
            logger.warning(f"[{self.name}] Aucune opportunité trouvée")
            return []
        
        signals = []
        
        for idx, row in df.head(top_n).iterrows():
            # Déterminer la meilleure opportunité (home/away/draw)
            spreads = {
                'home': row['home_spread_pct'],
                'away': row['away_spread_pct'],
                'draw': row.get('draw_spread_pct', 0)
            }
            
            best_outcome = max(spreads, key=spreads.get)
            best_spread = spreads[best_outcome]
            
            # Récupérer les cotes correspondantes
            if best_outcome == 'home':
                max_odds = row['max_home_odds']
                min_odds = row['min_home_odds']
                direction = 'BACK_HOME'
            elif best_outcome == 'away':
                max_odds = row['max_away_odds']
                min_odds = row['min_away_odds']
                direction = 'BACK_AWAY'
            else:
                max_odds = row['max_draw_odds']
                min_odds = row['min_draw_odds']
                direction = 'BACK_DRAW'
            
            # Estimer probabilité de gagner
            win_prob = self.estimate_win_probability(max_odds, min_odds, best_spread)
            
            # Calculer Kelly
            kelly_fraction = self.calculate_kelly_criterion(max_odds, win_prob)
            
            # Calculer EV
            ev = self.calculate_expected_value(max_odds, win_prob)
            
            # Confiance basée sur spread et EV
            confidence = min((best_spread * 10) + (ev * 50), 100)
            
            signal = {
                'agent': self.name,
                'match': f"{row['home_team']} vs {row['away_team']}",
                'sport': row['sport'],
                'direction': direction,
                'confidence': confidence,
                'odds': {
                    'max': max_odds,
                    'min': min_odds,
                    'avg': (max_odds + min_odds) / 2
                },
                'spread_pct': best_spread,
                'win_probability': win_prob,
                'kelly_fraction': kelly_fraction,
                'expected_value': ev,
                'recommended_stake_pct': kelly_fraction * 100,  # % du bankroll
                'bookmaker_count': row['bookmaker_count'],
                'reason': f"Spread {best_spread:.2f}%, EV={ev:.3f}, Kelly={kelly_fraction*100:.1f}%"
            }
            
            signals.append(signal)
        
        logger.info(f"[{self.name}] Généré {len(signals)} signaux")
        
        return signals
    
    def backtest(self, historical_opportunities, bankroll=1000):
        """
        Backteste la stratégie sur données historiques
        
        Simule les paris avec Kelly sizing
        """
        # TODO: Implémenter quand on aura les résultats
        
        results = {
            'agent': self.name,
            'initial_bankroll': bankroll,
            'final_bankroll': bankroll,
            'roi': 0.0,
            'total_bets': 0,
            'winning_bets': 0,
            'losing_bets': 0,
            'win_rate': 0.0,
            'avg_stake': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0
        }
        
        return results
