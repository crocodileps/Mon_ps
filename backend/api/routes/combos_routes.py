import json
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


# ============================================================
# 🆕 NOUVELLES ROUTES V2 - DYNAMIQUES + HISTORIQUE
# ============================================================

@router.get("/stats-dynamic")
async def get_dynamic_market_stats():
    """
    Récupère les stats des marchés DYNAMIQUEMENT depuis la base
    (Remplace les valeurs hardcodées)
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT 
            market_type,
            COUNT(*) as total_picks,
            COUNT(*) FILTER (WHERE is_winner = true) as wins,
            COUNT(*) FILTER (WHERE is_winner = false) as losses,
            ROUND(COUNT(*) FILTER (WHERE is_winner)::numeric / NULLIF(COUNT(*), 0) * 100, 1) as win_rate,
            ROUND(AVG(odds_taken)::numeric, 2) as avg_odds,
            ROUND(SUM(profit_loss)::numeric, 2) as total_profit,
            ROUND(AVG(clv_percentage)::numeric, 2) as avg_clv
        FROM tracking_clv_picks
        WHERE is_resolved = true
        AND market_type IS NOT NULL
        GROUP BY market_type
        HAVING COUNT(*) >= 5
        ORDER BY total_profit DESC
    """)
    
    markets = cur.fetchall()
    
    # Classifier dynamiquement
    for m in markets:
        profit = float(m['total_profit'] or 0)
        wr = float(m['win_rate'] or 0)
        
        if profit > 10 and wr > 60:
            m['tier'] = 'S'
            m['status'] = '🏆 ELITE'
        elif profit > 5:
            m['tier'] = 'S'
            m['status'] = '🥇 TOP'
        elif profit > 0:
            m['tier'] = 'A'
            m['status'] = '✅ RENTABLE'
        elif profit > -5:
            m['tier'] = 'B'
            m['status'] = '⚠️ NEUTRE'
        else:
            m['tier'] = 'C'
            m['status'] = '❌ À ÉVITER'
    
    cur.close()
    conn.close()
    
    return {
        'count': len(markets),
        'markets': markets,
        'source': 'DYNAMIC - tracking_clv_picks',
        'updated_at': datetime.now().isoformat()
    }


@router.post("/save")
async def save_combo(combo_data: dict):
    """
    Sauvegarde un combo pour tracking et analyse future
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        selections = combo_data.get('selections', [])
        total_odds = combo_data.get('total_odds', 1.0)
        stake = combo_data.get('stake', 10.0)
        
        if len(selections) < 2:
            return {"error": "Minimum 2 sélections requises"}
        
        # Calculer probabilité combinée
        combined_prob = 1.0
        for sel in selections:
            if sel.get('win_rate'):
                combined_prob *= sel['win_rate'] / 100
        combined_prob *= 100
        
        # Expected Value
        ev = (combined_prob / 100) * total_odds
        
        # Kelly combo
        if total_odds > 1:
            kelly = ((combined_prob / 100) * total_odds - 1) / (total_odds - 1) * 100
            kelly = max(0, min(kelly, 25))  # Cap à 25%
        else:
            kelly = 0
        
        cur.execute("""
            INSERT INTO fg_combo_tracking 
            (selections, total_odds, num_selections, combined_probability, 
             kelly_combo, expected_value, stake, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
            RETURNING id, combo_id
        """, (
            json.dumps(selections),
            total_odds,
            len(selections),
            round(combined_prob, 2),
            round(kelly, 2),
            round(ev, 2),
            stake
        ))
        
        result = cur.fetchone()
        conn.commit()
        
        return {
            "success": True,
            "combo_id": str(result['combo_id']),
            "id": result['id'],
            "stats": {
                "total_odds": total_odds,
                "combined_probability": round(combined_prob, 2),
                "expected_value": round(ev, 2),
                "kelly_pct": round(kelly, 2),
                "potential_win": round(stake * total_odds, 2)
            }
        }
        
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()
        conn.close()


@router.get("/history")
async def get_combo_history(
    status: str = "all",
    limit: int = 50
):
    """
    Récupère l'historique des combos avec stats
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    query = """
        SELECT 
            id, combo_id, selections, total_odds, num_selections,
            combined_probability, kelly_combo, expected_value,
            status, outcome, winning_selections, stake, profit_loss,
            created_at, resolved_at
        FROM fg_combo_tracking
    """
    
    params = []
    if status != "all":
        query += " WHERE status = %s"
        params.append(status)
    
    query += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)
    
    cur.execute(query, params)
    combos = cur.fetchall()
    
    # Stats globales
    cur.execute("""
        SELECT 
            COUNT(*) as total_combos,
            COUNT(*) FILTER (WHERE status = 'won') as won,
            COUNT(*) FILTER (WHERE status = 'lost') as lost,
            COUNT(*) FILTER (WHERE status = 'pending') as pending,
            ROUND(SUM(profit_loss)::numeric, 2) as total_profit,
            ROUND(AVG(total_odds)::numeric, 2) as avg_odds,
            ROUND(AVG(num_selections)::numeric, 1) as avg_selections
        FROM fg_combo_tracking
        WHERE status != 'pending' OR status = 'pending'
    """)
    stats = cur.fetchone()
    
    cur.close()
    conn.close()
    
    # Formater les résultats
    for combo in combos:
        combo['created_at'] = str(combo['created_at']) if combo['created_at'] else None
        combo['resolved_at'] = str(combo['resolved_at']) if combo['resolved_at'] else None
        combo['combo_id'] = str(combo['combo_id']) if combo['combo_id'] else None
    
    return {
        "count": len(combos),
        "combos": combos,
        "stats": {
            "total": stats['total_combos'] or 0,
            "won": stats['won'] or 0,
            "lost": stats['lost'] or 0,
            "pending": stats['pending'] or 0,
            "win_rate": round((stats['won'] or 0) / max(1, (stats['won'] or 0) + (stats['lost'] or 0)) * 100, 1),
            "total_profit": float(stats['total_profit'] or 0),
            "avg_odds": float(stats['avg_odds'] or 0),
            "avg_selections": float(stats['avg_selections'] or 0)
        }
    }


@router.post("/resolve/{combo_id}")
async def resolve_combo(combo_id: str, result: dict):
    """
    Résout un combo (won/lost/partial)
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        outcome = result.get('outcome', 'lost')  # won, lost, partial
        winning_selections = result.get('winning_selections', 0)
        
        # Récupérer le combo
        cur.execute("""
            SELECT stake, total_odds, num_selections 
            FROM fg_combo_tracking 
            WHERE combo_id = %s OR id::text = %s
        """, (combo_id, combo_id))
        
        combo = cur.fetchone()
        if not combo:
            return {"error": "Combo non trouvé"}
        
        # Calculer profit/loss
        stake = float(combo['stake'] or 10)
        total_odds = float(combo['total_odds'] or 1)
        
        if outcome == 'won':
            profit_loss = stake * total_odds - stake
            status = 'won'
        elif outcome == 'partial':
            # Calcul partiel basé sur les sélections gagnantes
            partial_odds = 1.0  # À améliorer avec les vraies cotes
            profit_loss = stake * partial_odds - stake
            status = 'partial'
        else:
            profit_loss = -stake
            status = 'lost'
        
        cur.execute("""
            UPDATE fg_combo_tracking
            SET status = %s,
                outcome = %s,
                winning_selections = %s,
                profit_loss = %s,
                resolved_at = NOW()
            WHERE combo_id = %s OR id::text = %s
            RETURNING id
        """, (status, outcome, winning_selections, round(profit_loss, 2), combo_id, combo_id))
        
        conn.commit()
        
        return {
            "success": True,
            "combo_id": combo_id,
            "status": status,
            "profit_loss": round(profit_loss, 2)
        }
        
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        cur.close()
        conn.close()


@router.get("/correlations-dynamic")
async def get_dynamic_correlations():
    """
    Calcule les corrélations RÉELLES entre marchés depuis l'historique
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Calculer les co-occurrences de victoires
    cur.execute("""
        WITH market_results AS (
            SELECT 
                home_team, away_team, commence_time::date as match_date,
                market_type,
                is_winner
            FROM tracking_clv_picks
            WHERE is_resolved = true
        ),
        pair_analysis AS (
            SELECT 
                a.market_type as market_a,
                b.market_type as market_b,
                COUNT(*) as sample_size,
                COUNT(*) FILTER (WHERE a.is_winner AND b.is_winner) as both_win,
                COUNT(*) FILTER (WHERE a.is_winner) as a_wins,
                COUNT(*) FILTER (WHERE b.is_winner) as b_wins
            FROM market_results a
            JOIN market_results b ON 
                a.home_team = b.home_team 
                AND a.away_team = b.away_team 
                AND a.match_date = b.match_date
                AND a.market_type < b.market_type
            GROUP BY a.market_type, b.market_type
            HAVING COUNT(*) >= 10
        )
        SELECT 
            market_a, market_b, sample_size,
            ROUND(a_wins::numeric / sample_size * 100, 1) as wr_a,
            ROUND(b_wins::numeric / sample_size * 100, 1) as wr_b,
            ROUND(both_win::numeric / sample_size * 100, 1) as both_wr,
            ROUND((both_win::numeric / NULLIF(a_wins * b_wins / sample_size::numeric, 0)), 2) as lift
        FROM pair_analysis
        ORDER BY lift DESC
    """)
    
    correlations = cur.fetchall()
    
    # Identifier les meilleurs et pires combos
    best_combos = []
    avoid_combos = []
    
    for c in correlations:
        lift = float(c['lift'] or 1)
        both_wr = float(c['both_wr'] or 0)
        
        if lift > 1.2 and both_wr > 30:
            best_combos.append({
                'pair': f"{c['market_a']} + {c['market_b']}",
                'win_rate': both_wr,
                'lift': lift,
                'sample': c['sample_size']
            })
        elif lift < 0.8 or both_wr < 15:
            avoid_combos.append({
                'pair': f"{c['market_a']} + {c['market_b']}",
                'win_rate': both_wr,
                'lift': lift,
                'reason': 'Corrélation négative' if lift < 0.8 else 'Win rate trop faible'
            })
    
    cur.close()
    conn.close()
    
    return {
        'correlations': correlations,
        'best_combos': sorted(best_combos, key=lambda x: x['win_rate'], reverse=True)[:5],
        'avoid_combos': avoid_combos[:5],
        'interpretation': {
            'lift > 1.2': 'Synergie positive - Bon pour combos',
            'lift 0.8-1.2': 'Indépendant - Neutre',
            'lift < 0.8': 'Anti-corrélation - À éviter ensemble'
        }
    }
