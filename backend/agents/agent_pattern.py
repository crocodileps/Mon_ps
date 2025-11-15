"""
Agent C : Pattern Matcher
Identifie les configurations récurrentes et patterns gagnants
"""
import numpy as np
import pandas as pd
import psycopg2
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class PatternMatcherAgent:
    """
    Agent C : Détection de patterns dans les opportunités
    
    Stratégie :
    - Identifie les configurations qui se répètent
    - Score basé sur la fréquence et la qualité du pattern
    - Utilise des règles heuristiques + statistiques
    """
    
    def __init__(self, db_config):
        self.db_config = db_config
        self.name = "Pattern Matcher"
        self.patterns = {}
        
    def fetch_historical_opportunities(self, days=7):
        """Récupère l'historique des opportunités"""
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
                max_away_odds,
                max_draw_odds,
                last_update
            FROM v_current_opportunities
            ORDER BY last_update DESC
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    
    def identify_patterns(self, df):
        """
        Identifie les patterns récurrents
        
        Patterns analysés :
        1. Underdog fort (cote away élevée + spread élevé)
        2. Favori dominant (cote home basse + spread home élevé)
        3. Match équilibré (cotes similaires + spread draw)
        4. Volatilité élevée (écarts de cotes importants)
        """
        patterns = defaultdict(list)
        
        for idx, row in df.iterrows():
            # Pattern 1: Underdog fort
            if (row['max_away_odds'] > 5.0 and 
                row['away_spread_pct'] > 50):
                patterns['underdog_fort'].append({
                    'match': f"{row['home_team']} vs {row['away_team']}",
                    'sport': row['sport'],
                    'away_odds': row['max_away_odds'],
                    'spread': row['away_spread_pct'],
                    'score': row['away_spread_pct'] * 0.5
                })
            
            # Pattern 2: Favori dominant
            if (row['max_home_odds'] < 1.5 and 
                row['home_spread_pct'] > 30):
                patterns['favori_dominant'].append({
                    'match': f"{row['home_team']} vs {row['away_team']}",
                    'sport': row['sport'],
                    'home_odds': row['max_home_odds'],
                    'spread': row['home_spread_pct'],
                    'score': row['home_spread_pct'] * 0.8
                })
            
            # Pattern 3: Match équilibré avec spread draw
            home_away_ratio = row['max_home_odds'] / row['max_away_odds']
            if (0.7 < home_away_ratio < 1.3 and 
                row.get('draw_spread_pct', 0) > 20):
                patterns['match_equilibre'].append({
                    'match': f"{row['home_team']} vs {row['away_team']}",
                    'sport': row['sport'],
                    'draw_odds': row.get('max_draw_odds', 3.0),
                    'spread': row.get('draw_spread_pct', 0),
                    'score': row.get('draw_spread_pct', 0) * 0.6
                })
            
            # Pattern 4: Volatilité élevée (grosse différence de spreads)
            max_spread = max(
                row['home_spread_pct'],
                row['away_spread_pct'],
                row.get('draw_spread_pct', 0)
            )
            if max_spread > 100:
                patterns['volatilite_elevee'].append({
                    'match': f"{row['home_team']} vs {row['away_team']}",
                    'sport': row['sport'],
                    'max_spread': max_spread,
                    'bookmakers': row['bookmaker_count'],
                    'score': min(max_spread * 0.3, 100)
                })
            
            # Pattern 5: Consensus bookmakers (beaucoup de bookmakers)
            if row['bookmaker_count'] >= 20:
                patterns['consensus_fort'].append({
                    'match': f"{row['home_team']} vs {row['away_team']}",
                    'sport': row['sport'],
                    'bookmakers': row['bookmaker_count'],
                    'max_spread': max(
                        row['home_spread_pct'],
                        row['away_spread_pct'],
                        row.get('draw_spread_pct', 0)
                    ),
                    'score': row['bookmaker_count'] * 2
                })
        
        self.patterns = patterns
        return patterns
    
    def score_pattern(self, pattern_type, pattern_data):
        """
        Score un pattern selon sa qualité
        
        Facteurs :
        - Fréquence du pattern
        - Magnitude des spreads
        - Nombre de bookmakers
        """
        base_score = pattern_data.get('score', 50)
        
        # Bonus selon le type de pattern
        type_multipliers = {
            'underdog_fort': 1.2,
            'favori_dominant': 1.1,
            'match_equilibre': 0.9,
            'volatilite_elevee': 1.3,
            'consensus_fort': 1.4
        }
        
        multiplier = type_multipliers.get(pattern_type, 1.0)
        final_score = min(base_score * multiplier, 100)
        
        return final_score
    
    def generate_signals(self, top_n=10):
        """
        Génère des signaux basés sur les patterns détectés
        
        Returns:
            List de signaux avec pattern type et confiance
        """
        logger.info(f"[{self.name}] Génération signaux...")
        
        # Récupérer données
        df = self.fetch_historical_opportunities()
        
        if len(df) == 0:
            logger.warning(f"[{self.name}] Aucune opportunité trouvée")
            return []
        
        # Identifier patterns
        patterns = self.identify_patterns(df)
        
        # Créer signaux
        signals = []
        
        for pattern_type, pattern_list in patterns.items():
            for pattern_data in pattern_list[:5]:  # Top 5 de chaque pattern
                score = self.score_pattern(pattern_type, pattern_data)
                
                # Déterminer la direction selon le pattern
                if pattern_type == 'underdog_fort':
                    direction = 'BACK_AWAY'
                    reason = f"Pattern Underdog Fort: spread {pattern_data['spread']:.1f}%"
                elif pattern_type == 'favori_dominant':
                    direction = 'BACK_HOME'
                    reason = f"Pattern Favori Dominant: spread {pattern_data['spread']:.1f}%"
                elif pattern_type == 'match_equilibre':
                    direction = 'BACK_DRAW'
                    reason = f"Pattern Match Équilibré: spread draw {pattern_data['spread']:.1f}%"
                elif pattern_type == 'volatilite_elevee':
                    direction = 'REVIEW'
                    reason = f"Pattern Volatilité: spread {pattern_data['max_spread']:.1f}%"
                else:  # consensus_fort
                    direction = 'REVIEW'
                    reason = f"Pattern Consensus: {pattern_data['bookmakers']} bookmakers"
                
                signal = {
                    'agent': self.name,
                    'match': pattern_data['match'],
                    'sport': pattern_data['sport'],
                    'direction': direction,
                    'confidence': score,
                    'pattern_type': pattern_type,
                    'pattern_data': pattern_data,
                    'reason': reason
                }
                
                signals.append(signal)
        
        # Trier par confiance
        signals = sorted(signals, key=lambda x: x['confidence'], reverse=True)[:top_n]
        
        logger.info(f"[{self.name}] Généré {len(signals)} signaux")
        logger.info(f"[{self.name}] Patterns détectés: {len(patterns)} types")
        
        return signals
    
    def get_pattern_stats(self):
        """Retourne des statistiques sur les patterns détectés"""
        if not self.patterns:
            return {}
        
        stats = {}
        for pattern_type, pattern_list in self.patterns.items():
            stats[pattern_type] = {
                'count': len(pattern_list),
                'avg_score': np.mean([p.get('score', 0) for p in pattern_list])
            }
        
        return stats
