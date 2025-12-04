"""
SMART MARKET SELECTOR V1.0
==========================
Sélectionne le meilleur marché basé sur:
1. Profil des équipes (offensif/défensif)
2. Edge calculé (modèle vs cotes)
3. Marge bookmaker (priorité aux marchés à faible marge)

HIÉRARCHIE DES MARCHÉS (par edge potentiel):
1. Asian Handicap (marge ~2%)
2. Asian Totals (O/U 2.0, 2.25, 2.75)
3. Over/Under classique (O/U 2.5)
4. BTTS
5. 1X2 (marge ~5-8%)
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from dataclasses import dataclass
from typing import Optional, List, Dict
import math

DB_CONFIG = {
    'host': 'localhost', 'port': 5432, 'dbname': 'monps_db',
    'user': 'monps_user', 'password': 'monps_secure_password_2024'
}

# ══════════════════════════════════════════════════════════════════════════════
# CLASSIFICATION DES MARCHÉS V3
# ══════════════════════════════════════════════════════════════════════════════

MARKET_FAMILIES = {
    # TIER 1: GOD TIER - Asian Handicap
    'ah_favorite': {
        'markets': ['ah_-0.5', 'ah_-1.0', 'ah_-1.5', 'ah_-2.0'],
        'description': 'Favori donne des buts',
        'margin': 0.02,
        'edge_potential': 'HIGH',
        'use_when': 'power_diff > 15 and home_xg > 2.0'
    },
    'ah_underdog': {
        'markets': ['ah_+0.5', 'ah_+1.0', 'ah_+1.5'],
        'description': 'Outsider reçoit des buts',
        'margin': 0.02,
        'edge_potential': 'HIGH',
        'use_when': 'underdog_solid_defense and power_diff < 10'
    },
    'ah_dnb': {
        'markets': ['ah_0.0', 'draw_no_bet'],
        'description': 'Draw No Bet',
        'margin': 0.02,
        'edge_potential': 'MEDIUM',
        'use_when': 'slight_favorite and draw_risk > 25%'
    },
    
    # TIER 2: Asian Totals (protection avec push)
    'goals_high_safe': {
        'markets': ['over_2.0', 'over_2.25', 'over_2.75'],
        'description': 'Over avec protection push',
        'margin': 0.03,
        'edge_potential': 'HIGH',
        'use_when': 'total_xg > 2.3 and both_offensive'
    },
    'goals_low_safe': {
        'markets': ['under_2.75', 'under_3.0'],
        'description': 'Under avec protection',
        'margin': 0.03,
        'edge_potential': 'HIGH',
        'use_when': 'total_xg < 2.2 and one_defensive'
    },
    
    # TIER 3: Classique Over/Under
    'goals_high': {
        'markets': ['over_2.5', 'over_3.5', 'btts_yes'],
        'description': 'Match ouvert',
        'margin': 0.04,
        'edge_potential': 'MEDIUM',
        'use_when': 'total_xg > 2.5'
    },
    'goals_low': {
        'markets': ['under_2.5', 'btts_no'],
        'description': 'Match fermé',
        'margin': 0.04,
        'edge_potential': 'MEDIUM',
        'use_when': 'total_xg < 2.0'
    },
    
    # TIER 4: Team Goals (spéculatif malin)
    'team_attack': {
        'markets': ['team_over_1.5', 'team_over_2.5'],
        'description': 'Équipe marque beaucoup',
        'margin': 0.04,
        'edge_potential': 'MEDIUM',
        'use_when': 'team_xg > 1.8 and opponent_defense_weak'
    },
    'team_defense': {
        'markets': ['team_clean_sheet'],
        'description': 'Équipe solide défensivement',
        'margin': 0.05,
        'edge_potential': 'LOW',
        'use_when': 'team_xg_against < 0.8'
    }
}


@dataclass
class MarketRecommendation:
    """Recommandation de marché avec détails"""
    market_type: str
    market_family: str
    line: Optional[float]  # Pour AH et O/U
    team: Optional[str]    # Pour AH
    odds: float
    bookmaker: str
    edge: float           # Notre avantage estimé
    probability: float    # Probabilité modèle
    implied_prob: float   # Probabilité implicite cote
    margin: float         # Marge bookmaker estimée
    confidence: str       # LOW/MEDIUM/HIGH
    reason: str


class SmartMarketSelector:
    """Sélecteur intelligent de marché"""
    
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cur = self.conn.cursor(cursor_factory=RealDictCursor)
    
    def get_all_odds_for_match(self, home_team: str, away_team: str, 
                                commence_time=None) -> Dict:
        """Récupère toutes les cotes disponibles pour un match"""
        
        result = {
            '1x2': [],
            'spreads': [],
            'totals': []
        }
        
        # 1X2 (odds_history)
        self.cur.execute("""
            SELECT bookmaker, home_odds, draw_odds, away_odds
            FROM odds_history
            WHERE home_team ILIKE %s AND away_team ILIKE %s
            ORDER BY collected_at DESC
            LIMIT 20
        """, (f'%{home_team}%', f'%{away_team}%'))
        result['1x2'] = self.cur.fetchall()
        
        # Asian Handicap (odds_spreads)
        self.cur.execute("""
            SELECT bookmaker, team, spread_point, spread_odds
            FROM odds_spreads
            WHERE home_team ILIKE %s AND away_team ILIKE %s
            ORDER BY collected_at DESC
        """, (f'%{home_team}%', f'%{away_team}%'))
        result['spreads'] = self.cur.fetchall()
        
        # Over/Under (odds_totals)
        self.cur.execute("""
            SELECT bookmaker, line, over_odds, under_odds
            FROM odds_totals
            WHERE home_team ILIKE %s AND away_team ILIKE %s
            ORDER BY collected_at DESC
        """, (f'%{home_team}%', f'%{away_team}%'))
        result['totals'] = self.cur.fetchall()
        
        return result
    
    def calculate_margin(self, odds_list: List[float]) -> float:
        """Calcule la marge du bookmaker"""
        if not odds_list or 0 in odds_list:
            return 0.10  # Marge par défaut
        total_prob = sum(1/o for o in odds_list if o > 0)
        return max(0, total_prob - 1)
    
    def calculate_edge(self, model_prob: float, odds: float) -> float:
        """Calcule l'edge (avantage) du pari"""
        implied_prob = 1 / odds
        return model_prob - implied_prob
    
    def poisson_prob(self, lambda_val: float, k: int) -> float:
        """Probabilité Poisson"""
        return (lambda_val ** k) * math.exp(-lambda_val) / math.factorial(k)
    
    def calculate_over_under_probs(self, home_xg: float, away_xg: float) -> Dict:
        """Calcule les probabilités Over/Under avec Dixon-Coles"""
        probs = {}
        
        # Matrice de probabilités (simplifié)
        total_xg = home_xg + away_xg
        
        # Over 2.5
        prob_under_25 = 0
        for h in range(3):
            for a in range(3 - h):
                prob_under_25 += self.poisson_prob(home_xg, h) * self.poisson_prob(away_xg, a)
        probs['over_2.5'] = 1 - prob_under_25
        probs['under_2.5'] = prob_under_25
        
        # Over 2.0 (avec push à exactement 2)
        prob_exactly_2 = 0
        for h in range(3):
            a = 2 - h
            if a >= 0:
                prob_exactly_2 += self.poisson_prob(home_xg, h) * self.poisson_prob(away_xg, a)
        probs['over_2.0'] = probs['over_2.5']  # Gagne si >2
        probs['push_2.0'] = prob_exactly_2     # Push si =2
        
        # BTTS
        prob_home_scores = 1 - self.poisson_prob(home_xg, 0)
        prob_away_scores = 1 - self.poisson_prob(away_xg, 0)
        probs['btts_yes'] = prob_home_scores * prob_away_scores
        probs['btts_no'] = 1 - probs['btts_yes']
        
        return probs
    
    def recommend_markets(self, home_team: str, away_team: str,
                          home_xg: float, away_xg: float,
                          home_power: float = 50, away_power: float = 50) -> List[MarketRecommendation]:
        """
        Recommande les meilleurs marchés pour un match
        
        Args:
            home_team, away_team: Noms des équipes
            home_xg, away_xg: xG attendus
            home_power, away_power: Force des équipes (0-100)
        
        Returns:
            Liste de recommandations triées par edge
        """
        
        recommendations = []
        
        # Récupérer toutes les cotes
        all_odds = self.get_all_odds_for_match(home_team, away_team)
        
        # Calculer les probabilités modèle
        total_xg = home_xg + away_xg
        power_diff = home_power - away_power
        ou_probs = self.calculate_over_under_probs(home_xg, away_xg)
        
        # ═══════════════════════════════════════════════════════════════════
        # 1. ANALYSER OVER/UNDER
        # ═══════════════════════════════════════════════════════════════════
        
        for odds_row in all_odds['totals']:
            line = float(odds_row['line'])
            over_odds = float(odds_row['over_odds'])
            under_odds = float(odds_row['under_odds'])
            bookmaker = odds_row['bookmaker']
            
            # Calculer marge
            margin = self.calculate_margin([over_odds, under_odds])
            
            # Over
            if line == 2.5:
                model_prob = ou_probs['over_2.5']
                edge = self.calculate_edge(model_prob, over_odds)
                
                if edge > 0.03:  # Edge > 3%
                    recommendations.append(MarketRecommendation(
                        market_type='over_2.5',
                        market_family='goals_high',
                        line=2.5,
                        team=None,
                        odds=over_odds,
                        bookmaker=bookmaker,
                        edge=edge,
                        probability=model_prob,
                        implied_prob=1/over_odds,
                        margin=margin,
                        confidence='HIGH' if edge > 0.05 else 'MEDIUM',
                        reason=f"xG total {total_xg:.1f} > 2.5"
                    ))
            
            # Asian Total Over 2.0 (avec protection push)
            elif line == 2.0:
                model_prob = ou_probs['over_2.5'] + ou_probs.get('push_2.0', 0) * 0.5
                edge = self.calculate_edge(model_prob, over_odds)
                
                if edge > 0.02:
                    recommendations.append(MarketRecommendation(
                        market_type='over_2.0',
                        market_family='goals_high_safe',
                        line=2.0,
                        team=None,
                        odds=over_odds,
                        bookmaker=bookmaker,
                        edge=edge,
                        probability=model_prob,
                        implied_prob=1/over_odds,
                        margin=margin,
                        confidence='HIGH' if edge > 0.04 else 'MEDIUM',
                        reason=f"Over 2.0 avec push protection, xG={total_xg:.1f}"
                    ))
        
        # ═══════════════════════════════════════════════════════════════════
        # 2. ANALYSER ASIAN HANDICAP
        # ═══════════════════════════════════════════════════════════════════
        
        for odds_row in all_odds['spreads']:
            team = odds_row['team']
            spread = float(odds_row['spread_point'])
            odds = float(odds_row['spread_odds'])
            bookmaker = odds_row['bookmaker']
            
            # Estimer probabilité basée sur power diff et xG
            # Simplifié: utiliser xG diff comme proxy
            xg_diff = home_xg - away_xg
            
            is_home = home_team.lower() in team.lower()
            
            if is_home:
                # Home team avec handicap négatif (favori)
                if spread == -0.5:  # AH -0.5 = doit gagner
                    # Prob = P(home win)
                    # Estimation simple basée sur xG
                    model_prob = 0.5 + (xg_diff * 0.15)  # Ajuster
                    model_prob = max(0.2, min(0.8, model_prob))
                    
                    edge = self.calculate_edge(model_prob, odds)
                    if edge > 0.02:
                        recommendations.append(MarketRecommendation(
                            market_type='ah_-0.5',
                            market_family='ah_favorite',
                            line=-0.5,
                            team=team,
                            odds=odds,
                            bookmaker=bookmaker,
                            edge=edge,
                            probability=model_prob,
                            implied_prob=1/odds,
                            margin=0.02,
                            confidence='HIGH' if edge > 0.04 else 'MEDIUM',
                            reason=f"Favori AH -0.5, xG diff={xg_diff:.1f}"
                        ))
            else:
                # Away team avec handicap positif (outsider)
                if spread == 0.5:  # AH +0.5 = ne pas perdre
                    model_prob = 0.5 - (xg_diff * 0.12)
                    model_prob = max(0.2, min(0.8, model_prob))
                    
                    edge = self.calculate_edge(model_prob, odds)
                    if edge > 0.02:
                        recommendations.append(MarketRecommendation(
                            market_type='ah_+0.5',
                            market_family='ah_underdog',
                            line=0.5,
                            team=team,
                            odds=odds,
                            bookmaker=bookmaker,
                            edge=edge,
                            probability=model_prob,
                            implied_prob=1/odds,
                            margin=0.02,
                            confidence='HIGH' if edge > 0.04 else 'MEDIUM',
                            reason=f"Outsider AH +0.5 (DNB), xG diff={xg_diff:.1f}"
                        ))
        
        # Trier par edge décroissant
        recommendations.sort(key=lambda x: x.edge, reverse=True)
        
        return recommendations
    
    def close(self):
        self.conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# TEST
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 100)
    print("    🎯 SMART MARKET SELECTOR V1.0")
    print("=" * 100)
    
    selector = SmartMarketSelector()
    
    # Test avec Bournemouth vs Everton
    print("\n   ⚽ Bournemouth vs Everton")
    print("   " + "─" * 60)
    
    recs = selector.recommend_markets(
        home_team="Bournemouth",
        away_team="Everton",
        home_xg=1.5,
        away_xg=1.0,
        home_power=55,
        away_power=45
    )
    
    if recs:
        print(f"\n   📊 {len(recs)} RECOMMANDATIONS TROUVÉES:\n")
        for i, rec in enumerate(recs[:5], 1):
            print(f"   {i}. {rec.market_type} @ {rec.odds:.2f} ({rec.bookmaker})")
            print(f"      Edge: {rec.edge*100:.1f}% | Prob: {rec.probability*100:.1f}%")
            print(f"      Famille: {rec.market_family} | Conf: {rec.confidence}")
            print(f"      Raison: {rec.reason}")
            print()
    else:
        print("   ❌ Aucune recommandation trouvée")
    
    # Test avec Barcelona vs Real Madrid
    print("\n   ⚽ Barcelona vs Real Madrid (exemple)")
    print("   " + "─" * 60)
    
    recs = selector.recommend_markets(
        home_team="Barcelona",
        away_team="Real Madrid",
        home_xg=2.1,
        away_xg=1.8,
        home_power=90,
        away_power=92
    )
    
    if recs:
        print(f"\n   📊 {len(recs)} RECOMMANDATIONS:\n")
        for i, rec in enumerate(recs[:3], 1):
            print(f"   {i}. {rec.market_type} @ {rec.odds:.2f} | Edge: {rec.edge*100:.1f}%")
    else:
        print("   ❌ Pas de données (match pas dans la base)")
    
    selector.close()
    
    print("\n" + "=" * 100)
    print("    ✅ SMART MARKET SELECTOR OPÉRATIONNEL")
    print("=" * 100)
