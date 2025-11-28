"""
🔗 COMBINÉS INTELLIGENTS
Suggestions de paris combinés basées sur les corrélations et performances réelles
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import os

router = APIRouter(prefix="/api/combos", tags=["Combinés Intelligents"])

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'monps_postgres'),
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}

# Marchés rentables identifiés (basé sur données réelles)
PROFITABLE_MARKETS = {
    'dc_1x': {'win_rate': 84.8, 'profit': 13.93, 'tier': 'S'},
    'over_25': {'win_rate': 71.7, 'profit': 13.65, 'tier': 'S'},
    'draw': {'win_rate': 28.9, 'profit': 7.91, 'tier': 'A'},
    'btts_no': {'win_rate': 42.9, 'profit': 5.15, 'tier': 'A'},
    'over_15': {'win_rate': 100.0, 'profit': 2.94, 'tier': 'A'},
}

# Marchés à éviter
AVOID_MARKETS = ['away', 'dc_x2', 'under_25', 'under_15', 'over35', 'dnb_away']

# Corrélations connues entre marchés
MARKET_CORRELATIONS = {
    ('dc_1x', 'btts_no'): 0.35,  # Faible corrélation = bon pour combos
    ('over_25', 'btts_yes'): 0.72,  # Forte corrélation = pas idéal
    ('dc_1x', 'under_35'): 0.28,  # Faible = bon
    ('over_25', 'over_15'): 0.85,  # Très forte = éviter
    ('home', 'dc_1x'): 0.65,  # Moyenne
    ('draw', 'btts_no'): 0.42,  # Acceptable
}

class ComboSuggestion(BaseModel):
    match_name: str
    home_team: str
    away_team: str
    commence_time: str
    picks: List[dict]
    combined_odds: float
    expected_win_rate: float
    correlation_score: float
    recommendation: str
    risk_level: str

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

@router.get("/suggestions")
async def get_combo_suggestions(limit: int = 10):
    """
    Génère des suggestions de combinés intelligents pour les matchs à venir
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Récupérer les picks non résolus avec marchés rentables
    cur.execute("""
        SELECT 
            home_team, away_team, commence_time, market_type,
            odds_taken, diamond_score, clv_percentage, kelly_pct
        FROM tracking_clv_picks
        WHERE is_resolved = false
        AND commence_time > NOW()
        AND market_type IN ('dc_1x', 'over_25', 'btts_no', 'under_35', 'over_15', 'draw')
        AND odds_taken > 1.1
        ORDER BY commence_time, home_team
    """)
    
    picks = cur.fetchall()
    cur.close()
    conn.close()
    
    # Grouper par match
    matches = {}
    for pick in picks:
        key = f"{pick['home_team']} vs {pick['away_team']}"
        if key not in matches:
            matches[key] = {
                'home_team': pick['home_team'],
                'away_team': pick['away_team'],
                'commence_time': str(pick['commence_time']),
                'picks': []
            }
        matches[key]['picks'].append({
            'market': pick['market_type'],
            'odds': float(pick['odds_taken']) if pick['odds_taken'] else 1.5,
            'score': pick['diamond_score'] or 50,
            'clv': float(pick['clv_percentage']) if pick['clv_percentage'] else 0
        })
    
    # Générer les combinés
    suggestions = []
    for match_name, match_data in matches.items():
        if len(match_data['picks']) >= 2:
            # Trouver les meilleures combinaisons
            best_combo = find_best_combo(match_data['picks'])
            if best_combo:
                suggestions.append({
                    'match_name': match_name,
                    'home_team': match_data['home_team'],
                    'away_team': match_data['away_team'],
                    'commence_time': match_data['commence_time'],
                    'picks': best_combo['picks'],
                    'combined_odds': best_combo['combined_odds'],
                    'expected_win_rate': best_combo['expected_wr'],
                    'correlation_score': best_combo['correlation'],
                    'recommendation': best_combo['recommendation'],
                    'risk_level': best_combo['risk']
                })
    
    # Trier par expected value
    suggestions.sort(key=lambda x: x['expected_win_rate'] * x['combined_odds'], reverse=True)
    
    return {
        'count': len(suggestions[:limit]),
        'suggestions': suggestions[:limit],
        'strategy_note': "Combinés basés sur marchés rentables (dc_1x, over_25) avec faible corrélation"
    }

def find_best_combo(picks: List[dict]) -> Optional[dict]:
    """Trouve la meilleure combinaison de 2-3 picks"""
    if len(picks) < 2:
        return None
    
    # Priorité aux marchés S-tier
    s_tier = [p for p in picks if p['market'] in ['dc_1x', 'over_25']]
    a_tier = [p for p in picks if p['market'] in ['btts_no', 'under_35', 'over_15', 'draw']]
    
    combo_picks = []
    
    # Stratégie: 1 S-tier + 1 A-tier (faible corrélation)
    if s_tier and a_tier:
        combo_picks = [s_tier[0], a_tier[0]]
    elif len(s_tier) >= 2:
        # 2 S-tier si pas trop corrélés
        if s_tier[0]['market'] != s_tier[1]['market']:
            combo_picks = s_tier[:2]
    elif len(a_tier) >= 2:
        combo_picks = a_tier[:2]
    
    if not combo_picks:
        return None
    
    # Calculer les métriques
    combined_odds = 1.0
    for p in combo_picks:
        combined_odds *= p['odds']
    
    # Win rate estimé (produit des probabilités individuelles)
    expected_wr = 1.0
    for p in combo_picks:
        market_stats = PROFITABLE_MARKETS.get(p['market'], {'win_rate': 50})
        expected_wr *= market_stats['win_rate'] / 100
    expected_wr *= 100
    
    # Corrélation
    if len(combo_picks) == 2:
        key = (combo_picks[0]['market'], combo_picks[1]['market'])
        correlation = MARKET_CORRELATIONS.get(key, MARKET_CORRELATIONS.get((key[1], key[0]), 0.5))
    else:
        correlation = 0.5
    
    # Recommandation
    ev = expected_wr * combined_odds / 100
    if ev > 1.2 and correlation < 0.4:
        recommendation = "🔥 EXCELLENT - Forte value, faible corrélation"
        risk = "LOW"
    elif ev > 1.0 and correlation < 0.5:
        recommendation = "✅ BON - Value positive"
        risk = "MEDIUM"
    else:
        recommendation = "⚠️ RISQUÉ - À surveiller"
        risk = "HIGH"
    
    return {
        'picks': combo_picks,
        'combined_odds': round(combined_odds, 2),
        'expected_wr': round(expected_wr, 1),
        'correlation': round(correlation, 2),
        'recommendation': recommendation,
        'risk': risk
    }

@router.get("/profitable-markets")
async def get_profitable_markets():
    """Retourne les marchés rentables avec stats"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT 
            market_type,
            COUNT(*) as total_picks,
            COUNT(*) FILTER (WHERE is_winner) as wins,
            ROUND(COUNT(*) FILTER (WHERE is_winner)::numeric / NULLIF(COUNT(*), 0) * 100, 1) as win_rate,
            ROUND(AVG(odds_taken)::numeric, 2) as avg_odds,
            ROUND(SUM(profit_loss)::numeric, 2) as total_profit
        FROM tracking_clv_picks
        WHERE is_resolved = true
        GROUP BY market_type
        HAVING COUNT(*) >= 5
        ORDER BY total_profit DESC
    """)
    
    markets = cur.fetchall()
    cur.close()
    conn.close()
    
    # Classifier
    for m in markets:
        if m['total_profit'] > 10:
            m['tier'] = 'S'
            m['status'] = '🏆 TOP'
        elif m['total_profit'] > 0:
            m['tier'] = 'A'
            m['status'] = '✅ BON'
        elif m['total_profit'] > -10:
            m['tier'] = 'B'
            m['status'] = '⚠️ NEUTRE'
        else:
            m['tier'] = 'C'
            m['status'] = '❌ À ÉVITER'
    
    return {
        'count': len(markets),
        'markets': markets,
        'best_for_combos': ['dc_1x', 'over_25', 'btts_no'],
        'avoid_in_combos': AVOID_MARKETS
    }

@router.get("/correlations")
async def get_market_correlations():
    """Retourne la matrice de corrélations entre marchés"""
    return {
        'correlations': MARKET_CORRELATIONS,
        'interpretation': {
            'low': '< 0.3 - Idéal pour combinés',
            'medium': '0.3-0.6 - Acceptable',
            'high': '> 0.6 - Éviter dans le même combiné'
        }
    }
