#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
MARKET CONVERGENCE ENGINE V2 - Sniper Market Recommendations
═══════════════════════════════════════════════════════════════════════════════

AMÉLIORATIONS V2:
- Filtre cotes minimales (exclut team_over_05 et autres marchés à cote < 1.30)
- Next Best Market si convergence sur marché faible
- Intégration prête pour Orchestrator
"""

import psycopg2
import psycopg2.extras
import logging
from typing import Dict, Optional, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': 'localhost', 'port': 5432, 'dbname': 'monps_db',
    'user': 'monps_user', 'password': 'monps_secure_password_2024'
}

# Cotes moyennes par marché (CRITIQUE: filtrer les cotes trop basses)
MARKET_TYPICAL_ODDS = {
    'team_over_05': 1.10,      # TROP BAS - À ÉVITER
    'over_15': 1.30,           # TROP BAS - À ÉVITER
    'team_over_15': 2.20,      # OK
    'over_25': 1.85,           # OK
    'over_35': 2.50,           # BON
    'under_15': 3.50,          # BON
    'under_25': 2.00,          # OK
    'under_35': 1.50,          # OK
    'btts_yes': 1.75,          # OK
    'btts_no': 2.00,           # OK
    'team_clean_sheet': 3.00,  # BON
    'team_fail_to_score': 4.50 # BON
}

# Cote minimum pour considérer un marché (AMÉLIORATION V2)
MIN_ODDS_THRESHOLD = 1.50

# Marchés de haute qualité (valeur réelle)
HIGH_VALUE_MARKETS = ['btts_yes', 'btts_no', 'over_25', 'under_25', 'over_35', 'under_35']

# Marchés opposés
OPPOSING_MARKETS = {
    'over_25': 'under_25', 'under_25': 'over_25',
    'over_35': 'under_35', 'under_35': 'over_35',
    'btts_yes': 'btts_no', 'btts_no': 'btts_yes',
}

# Marchés compatibles
COMPATIBLE_MARKETS = {
    'over_25': ['over_35', 'btts_yes'],
    'over_35': ['over_25', 'btts_yes'],
    'under_25': ['under_35', 'btts_no'],
    'under_35': ['under_25'],
    'btts_yes': ['over_25', 'over_35'],
    'btts_no': ['under_25', 'team_clean_sheet'],
}


class MarketConvergenceEngine:
    def __init__(self):
        self.conn = None
    
    def _get_conn(self):
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
        return self.conn
    
    def _is_high_value_market(self, market: str) -> bool:
        """Vérifie si le marché a une cote suffisante pour être intéressant"""
        odds = MARKET_TYPICAL_ODDS.get(market, 2.0)
        return odds >= MIN_ODDS_THRESHOLD
    
    def _get_best_valid_market(self, markets: Dict, exclude: List[str] = None) -> Optional[str]:
        """Trouve le meilleur marché avec une cote valide"""
        exclude = exclude or []
        
        # Trier par ROI
        sorted_markets = sorted(
            [(m, data) for m, data in markets.items() 
             if m not in exclude and self._is_high_value_market(m)],
            key=lambda x: x[1].get('roi', 0),
            reverse=True
        )
        
        return sorted_markets[0][0] if sorted_markets else None
    
    def get_team_best_markets(self, team_name: str, context: str = None) -> Dict:
        """Récupère les meilleurs marchés d'une équipe (filtrés par cote)"""
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("""
            SELECT market_type, win_rate, roi, market_rank, is_best_market, is_avoid_market
            FROM team_market_profiles
            WHERE team_name = %s AND is_statistically_valid = true
            ORDER BY roi DESC
        """, (team_name,))
        base_profile = cur.fetchall()
        
        if not base_profile:
            return None
        
        # Filtrer les marchés à cote trop basse
        valid_markets = [m for m in base_profile if self._is_high_value_market(m['market_type'])]
        
        if not valid_markets:
            valid_markets = base_profile  # Fallback
        
        all_markets = {m['market_type']: {
            'win_rate': float(m['win_rate']),
            'roi': float(m['roi']),
            'rank': m['market_rank'],
            'typical_odds': MARKET_TYPICAL_ODDS.get(m['market_type'], 2.0)
        } for m in base_profile}
        
        result = {
            'team': team_name,
            'best_markets': [m['market_type'] for m in valid_markets if m['is_best_market'] and self._is_high_value_market(m['market_type'])],
            'avoid_markets': [m['market_type'] for m in base_profile if m['is_avoid_market']],
            'top_market': valid_markets[0]['market_type'] if valid_markets else None,
            'top_roi': float(valid_markets[0]['roi']) if valid_markets else 0,
            'top_win_rate': float(valid_markets[0]['win_rate']) if valid_markets else 0,
            'all_markets': all_markets
        }
        
        # Contexte Home/Away
        if context in ['home', 'away']:
            cur.execute("""
                SELECT market_type, win_rate_in_context, delta_vs_baseline, is_jekyll_hyde
                FROM team_market_context
                WHERE team_name = %s AND context_type = %s AND is_significant = true
                ORDER BY delta_vs_baseline DESC
            """, (team_name, context))
            context_data = cur.fetchall()
            
            if context_data:
                result['context'] = context
                result['context_boosts'] = {m['market_type']: {
                    'context_win_rate': float(m['win_rate_in_context']),
                    'delta': float(m['delta_vs_baseline']),
                    'is_jekyll_hyde': m['is_jekyll_hyde']
                } for m in context_data if self._is_high_value_market(m['market_type'])}
        
        return result
    
    def get_h2h_override(self, team_a: str, team_b: str) -> Optional[Dict]:
        """Vérifie si un pattern H2H override les ADN individuels"""
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        t1, t2 = sorted([team_a, team_b])
        
        cur.execute("""
            SELECT market_type, win_rate, matches_last_3_years, pattern_strength, 
                   pattern_description, override_individual_dna
            FROM h2h_market_patterns
            WHERE team_a = %s AND team_b = %s AND is_pattern = true
            ORDER BY win_rate DESC
        """, (t1, t2))
        patterns = cur.fetchall()
        
        if not patterns:
            return None
        
        # Prendre le pattern le plus fort qui override ET qui a une bonne cote
        for p in patterns:
            if p['override_individual_dna'] and self._is_high_value_market(p['market_type']):
                return {
                    'market': p['market_type'],
                    'win_rate': float(p['win_rate']),
                    'matches': p['matches_last_3_years'],
                    'strength': p['pattern_strength'],
                    'description': p['pattern_description'],
                    'typical_odds': MARKET_TYPICAL_ODDS.get(p['market_type'], 2.0)
                }
        
        return None
    
    def calculate_convergence(self, home_team: str, away_team: str) -> Dict:
        """
        Calcule la convergence des marchés entre deux équipes
        AMÉLIORATION V2: Filtre les marchés à cote trop basse
        """
        home_profile = self.get_team_best_markets(home_team, context='home')
        away_profile = self.get_team_best_markets(away_team, context='away')
        
        if not home_profile or not away_profile:
            return {
                'recommended_market': None,
                'convergence_score': 0,
                'confidence': 0,
                'action': 'NO_DATA',
                'reasoning': f"Données insuffisantes pour {home_team} ou {away_team}",
                'score_modifier': 0
            }
        
        # H2H Override d'abord
        h2h_override = self.get_h2h_override(home_team, away_team)
        if h2h_override:
            return {
                'recommended_market': h2h_override['market'],
                'convergence_score': h2h_override['win_rate'],
                'confidence': min(95, h2h_override['win_rate']),
                'typical_odds': h2h_override['typical_odds'],
                'action': 'STRONG_BET',
                'source': 'h2h_override',
                'reasoning': f"H2H Pattern: {h2h_override['description']}",
                'home_best': home_profile['top_market'],
                'away_best': away_profile['top_market'],
                'score_modifier': +25  # BOOST pour l'orchestrator
            }
        
        home_top = home_profile['top_market']
        away_top = away_profile['top_market']
        
        # CAS 1: Convergence parfaite (même marché de haute valeur)
        if home_top == away_top and self._is_high_value_market(home_top):
            combined_wr = (home_profile['top_win_rate'] + away_profile['top_win_rate']) / 2
            return {
                'recommended_market': home_top,
                'convergence_score': 100,
                'confidence': min(95, combined_wr),
                'typical_odds': MARKET_TYPICAL_ODDS.get(home_top, 2.0),
                'expected_edge': (home_profile['top_roi'] + away_profile['top_roi']) / 2,
                'action': 'STRONG_BET',
                'source': 'perfect_convergence',
                'reasoning': f"Convergence parfaite: {home_team} et {away_team} = {home_top} specialists",
                'home_best': home_top,
                'away_best': away_top,
                'markets_converge': True,
                'markets_clash': False,
                'score_modifier': +20  # BOOST
            }
        
        # CAS 2: Clash total
        if home_top in OPPOSING_MARKETS and OPPOSING_MARKETS[home_top] == away_top:
            return {
                'recommended_market': None,
                'convergence_score': 0,
                'confidence': 20,
                'action': 'NO_BET',
                'source': 'market_clash',
                'reasoning': f"CLASH: {home_team}={home_top} vs {away_team}={away_top} - Imprévisible",
                'home_best': home_top,
                'away_best': away_top,
                'markets_converge': False,
                'markets_clash': True,
                'score_modifier': -30  # PÉNALITÉ
            }
        
        # CAS 3: Marchés compatibles (haute valeur seulement)
        if home_top in COMPATIBLE_MARKETS:
            compatible = COMPATIBLE_MARKETS.get(home_top, [])
            if away_top in compatible:
                # Choisir le marché avec meilleur ROI parmi les deux
                if home_profile['top_roi'] > away_profile['top_roi']:
                    best_market = home_top
                    best_wr = home_profile['top_win_rate']
                else:
                    best_market = away_top
                    best_wr = away_profile['top_win_rate']
                
                if self._is_high_value_market(best_market):
                    return {
                        'recommended_market': best_market,
                        'convergence_score': 75,
                        'confidence': min(85, best_wr),
                        'typical_odds': MARKET_TYPICAL_ODDS.get(best_market, 2.0),
                        'action': 'NORMAL_BET',
                        'source': 'compatible_markets',
                        'reasoning': f"Marchés compatibles: {home_top} + {away_top} → {best_market}",
                        'home_best': home_top,
                        'away_best': away_top,
                        'markets_converge': True,
                        'markets_clash': False,
                        'score_modifier': +10  # PETIT BOOST
                    }
        
        # CAS 4: Chercher terrain d'entente sur HIGH VALUE MARKETS uniquement
        common_strong = []
        for market in HIGH_VALUE_MARKETS:
            home_data = home_profile['all_markets'].get(market, {})
            away_data = away_profile['all_markets'].get(market, {})
            home_wr = home_data.get('win_rate', 0)
            away_wr = away_data.get('win_rate', 0)
            
            if home_wr >= 55 and away_wr >= 55:  # Seuil relevé
                common_strong.append({
                    'market': market,
                    'combined_wr': (home_wr + away_wr) / 2,
                    'home_wr': home_wr,
                    'away_wr': away_wr,
                    'typical_odds': MARKET_TYPICAL_ODDS.get(market, 2.0)
                })
        
        if common_strong:
            # Trier par combined_wr ET par cote (préférer cotes plus hautes)
            best = max(common_strong, key=lambda x: x['combined_wr'] * x['typical_odds'])
            return {
                'recommended_market': best['market'],
                'convergence_score': 60,
                'confidence': min(75, best['combined_wr']),
                'typical_odds': best['typical_odds'],
                'action': 'SMALL_BET',
                'source': 'common_strength_hv',
                'reasoning': f"Terrain d'entente HV: {best['market']} ({home_team}: {best['home_wr']:.0f}%, {away_team}: {best['away_wr']:.0f}%)",
                'home_best': home_top,
                'away_best': away_top,
                'markets_converge': False,
                'markets_clash': False,
                'score_modifier': +5  # MINI BOOST
            }
        
        # CAS 5: Aucune convergence de qualité
        return {
            'recommended_market': None,
            'convergence_score': 20,
            'confidence': 30,
            'action': 'SKIP',
            'source': 'no_quality_convergence',
            'reasoning': f"Pas de convergence qualité entre {home_team} ({home_top}) et {away_team} ({away_top})",
            'home_best': home_top,
            'away_best': away_top,
            'markets_converge': False,
            'markets_clash': False,
            'score_modifier': -15  # PÉNALITÉ
        }
    
    def get_orchestrator_modifier(self, home_team: str, away_team: str, target_market: str = None) -> Dict:
        """
        Interface pour l'Orchestrator - retourne le modifier de score
        
        Args:
            home_team: Équipe à domicile
            away_team: Équipe à l'extérieur
            target_market: Marché ciblé par l'orchestrator (optionnel)
        
        Returns:
            Dict avec score_modifier et recommended_action
        """
        convergence = self.calculate_convergence(home_team, away_team)
        
        result = {
            'score_modifier': convergence.get('score_modifier', 0),
            'recommended_market': convergence.get('recommended_market'),
            'convergence_action': convergence.get('action'),
            'confidence': convergence.get('confidence', 0),
            'reasoning': convergence.get('reasoning', ''),
            'markets_clash': convergence.get('markets_clash', False)
        }
        
        # Si l'orchestrator cible un marché spécifique, vérifier l'alignement
        if target_market and convergence.get('recommended_market'):
            if target_market == convergence['recommended_market']:
                result['alignment'] = 'PERFECT'
                result['score_modifier'] += 10
            elif target_market in COMPATIBLE_MARKETS.get(convergence['recommended_market'], []):
                result['alignment'] = 'COMPATIBLE'
                result['score_modifier'] += 5
            elif target_market in OPPOSING_MARKETS and OPPOSING_MARKETS.get(target_market) == convergence['recommended_market']:
                result['alignment'] = 'CLASH'
                result['score_modifier'] -= 20
            else:
                result['alignment'] = 'NEUTRAL'
        
        return result
    
    def analyze_match(self, home_team: str, away_team: str, verbose: bool = True) -> Dict:
        """Analyse complète avec output formaté"""
        convergence = self.calculate_convergence(home_team, away_team)
        
        if verbose:
            print(f"\n{'='*70}")
            print(f"🎯 MARKET CONVERGENCE V2: {home_team} vs {away_team}")
            print('='*70)
            
            action_emoji = {
                'STRONG_BET': '🔥', 'NORMAL_BET': '✅', 'SMALL_BET': '⚠️',
                'SKIP': '❌', 'NO_BET': '🚫', 'NO_DATA': '❓'
            }
            
            emoji = action_emoji.get(convergence['action'], '❓')
            
            print(f"\n   {emoji} ACTION: {convergence['action']}")
            print(f"   📊 Marché: {convergence.get('recommended_market', 'N/A')}")
            if convergence.get('typical_odds'):
                print(f"   💰 Cote typique: {convergence['typical_odds']:.2f}")
            print(f"   🎯 Convergence: {convergence.get('convergence_score', 0):.0f}%")
            print(f"   💪 Confidence: {convergence.get('confidence', 0):.0f}%")
            print(f"   📈 Score Modifier: {convergence.get('score_modifier', 0):+d} points")
            print(f"\n   💬 {convergence.get('reasoning', '')}")
            
            if convergence.get('home_best') and convergence.get('away_best'):
                print(f"\n   🏠 {home_team}: {convergence['home_best']}")
                print(f"   ✈️  {away_team}: {convergence['away_best']}")
        
        return convergence


def test_convergence_v2():
    """Test V2 avec filtre de cotes"""
    engine = MarketConvergenceEngine()
    
    print("═══════════════════════════════════════════════════════════════════")
    print("TEST MARKET CONVERGENCE ENGINE V2 (avec filtre cotes)")
    print("═══════════════════════════════════════════════════════════════════")
    
    test_matches = [
        ('Liverpool', 'Arsenal'),        # Avant: team_over_05 (inutile) → Maintenant?
        ('Bayern Munich', 'Barcelona'),  # Over specialists
        ('Lazio', 'Angers'),             # Under specialists
        ('Bayern Munich', 'Lazio'),      # Clash Over vs Under
        ('Real Madrid', 'Barcelona'),    # El Clasico
        ('Inter', 'AC Milan'),           # Derby Milan
    ]
    
    for home, away in test_matches:
        engine.analyze_match(home, away)
    
    # Test interface orchestrator
    print("\n" + "="*70)
    print("TEST INTERFACE ORCHESTRATOR")
    print("="*70)
    
    result = engine.get_orchestrator_modifier('Liverpool', 'Arsenal', target_market='btts_yes')
    print(f"\n   Liverpool vs Arsenal (target: btts_yes)")
    print(f"   Score Modifier: {result['score_modifier']:+d}")
    print(f"   Alignment: {result.get('alignment', 'N/A')}")
    print(f"   Recommended: {result['recommended_market']}")


if __name__ == "__main__":
    test_convergence_v2()
