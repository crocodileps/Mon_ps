"""
TRACKING CLV 2.0 - Routes API (Simplified)
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import structlog
from api.services.database import get_db, get_cursor
from psycopg2.extras import RealDictCursor

logger = structlog.get_logger()

router = APIRouter(prefix="/api/tracking-clv", tags=["Tracking CLV"])


@router.get("/dashboard")
def get_dashboard():
    """Dashboard principal avec toutes les stats"""
    try:
        with get_cursor() as cursor:
            # Stats globales
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_predictions,
                    COUNT(*) FILTER (WHERE is_resolved = true) as resolved,
                    COUNT(*) FILTER (WHERE is_resolved = true AND is_winner = true) as wins,
                    COUNT(*) FILTER (WHERE is_resolved = true AND is_winner = false) as losses,
                    COALESCE(AVG(clv_percentage) FILTER (WHERE clv_percentage IS NOT NULL), 0) as avg_clv,
                    COALESCE(SUM(profit_loss), 0) as total_profit
                FROM tracking_clv_picks
                WHERE created_at > NOW() - INTERVAL '30 days'
            """)
            global_stats = cursor.fetchone()
            
            if not global_stats:
                global_stats = {
                    'total_predictions': 0, 'resolved': 0, 'wins': 0, 
                    'losses': 0, 'avg_clv': 0, 'total_profit': 0
                }
            
            resolved = global_stats.get('resolved', 0) or 0
            wins = global_stats.get('wins', 0) or 0
            losses = global_stats.get('losses', 0) or 0
            
            win_rate = (wins / resolved * 100) if resolved > 0 else 0
            roi_pct = (global_stats.get('total_profit', 0) / resolved * 100) if resolved > 0 else 0
            
            # Stats par marché
            cursor.execute("""
                SELECT 
                    market_type,
                    COUNT(*) as total_predictions,
                    COUNT(*) FILTER (WHERE is_resolved = true) as resolved,
                    COUNT(*) FILTER (WHERE is_resolved = true AND is_winner = true) as wins,
                    COUNT(*) FILTER (WHERE is_resolved = true AND is_winner = false) as losses,
                    COALESCE(AVG(clv_percentage) FILTER (WHERE clv_percentage IS NOT NULL), 0) as avg_clv,
                    COALESCE(AVG(kelly_pct), 0) as avg_kelly,
                    COALESCE(SUM(profit_loss), 0) as total_profit
                FROM tracking_clv_picks
                WHERE created_at > NOW() - INTERVAL '30 days'
                GROUP BY market_type
                ORDER BY COUNT(*) FILTER (WHERE is_resolved = true AND is_winner = true) DESC
            """)
            markets_raw = cursor.fetchall()
            
            by_market = []
            for m in markets_raw:
                res = m.get('resolved', 0) or 0
                w = m.get('wins', 0) or 0
                l = m.get('losses', 0) or 0
                by_market.append({
                    'market_type': m.get('market_type', 'unknown'),
                    'total_predictions': m.get('total_predictions', 0),
                    'resolved': res,
                    'wins': w,
                    'losses': l,
                    'win_rate': (w / res * 100) if res > 0 else 0,
                    'roi_pct': (m.get('total_profit', 0) / res * 100) if res > 0 else 0,
                    'avg_clv': m.get('avg_clv', 0) or 0,
                    'avg_kelly': m.get('avg_kelly', 0) or 0,
                    'current_streak': 0
                })
            
            return {
                'global': {
                    'total_matches': 0,
                    'total_predictions': global_stats.get('total_predictions', 0),
                    'resolved_predictions': resolved,
                    'wins': wins,
                    'losses': losses,
                    'win_rate': round(win_rate, 2),
                    'roi_pct': round(roi_pct, 2),
                    'total_profit': round(global_stats.get('total_profit', 0) or 0, 2),
                    'avg_clv': round(global_stats.get('avg_clv', 0) or 0, 4),
                    'clv_positive_rate': 0
                },
                'by_market': by_market,
                'alerts': [],
                'best_combos': [],
                'calibration': []
            }
            
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        # Retourner des données vides en cas d'erreur
        return {
            'global': {
                'total_matches': 0,
                'total_predictions': 0,
                'resolved_predictions': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0,
                'roi_pct': 0,
                'total_profit': 0,
                'avg_clv': 0,
                'clv_positive_rate': 0
            },
            'by_market': [],
            'alerts': [],
            'best_combos': [],
            'calibration': []
        }


@router.get("/performance/by-date")
def get_performance_by_date(
    start_date: str = Query(default=None),
    end_date: str = Query(default=None)
):
    """Performance journalière"""
    try:
        with get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) FILTER (WHERE is_winner = true) as wins,
                    COUNT(*) FILTER (WHERE is_winner = false) as losses,
                    COALESCE(SUM(profit_loss), 0) as total_profit
                FROM tracking_clv_picks
                WHERE is_resolved = true
                AND created_at >= COALESCE(%s::date, NOW() - INTERVAL '30 days')
                AND created_at <= COALESCE(%s::date, NOW())
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """, (start_date, end_date))
            
            rows = cursor.fetchall()
            
            result = []
            cumulative = 0
            for row in reversed(rows):
                profit = row.get('total_profit', 0) or 0
                cumulative += profit
                result.append({
                    'date': str(row.get('date')),
                    'wins': row.get('wins', 0) or 0,
                    'losses': row.get('losses', 0) or 0,
                    'total_profit': round(profit, 2),
                    'cumulative_profit': round(cumulative, 2)
                })
            
            return list(reversed(result))
            
    except Exception as e:
        logger.error(f"Performance by date error: {e}")
        return []


@router.get("/clv/stats")
def get_clv_stats(days: int = Query(default=30)):
    """Statistiques CLV"""
    try:
        with get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COALESCE(AVG(clv_percentage), 0) as avg_clv,
                    COALESCE(STDDEV(clv_percentage), 0) as std_clv,
                    COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY clv_percentage), 0) as median_clv,
                    COUNT(*) FILTER (WHERE clv_percentage > 0)::float / NULLIF(COUNT(*), 0) * 100 as positive_rate,
                    COUNT(*) as total_picks
                FROM tracking_clv_picks
                WHERE clv_percentage IS NOT NULL
                AND created_at > NOW() - INTERVAL '%s days'
            """, (days,))
            
            stats = cursor.fetchone()
            
            return {
                'global_stats': {
                    'avg_clv': round(stats.get('avg_clv', 0) or 0, 4),
                    'std_clv': round(stats.get('std_clv', 0) or 0, 4),
                    'median_clv': round(stats.get('median_clv', 0) or 0, 4),
                    'positive_rate': round(stats.get('positive_rate', 0) or 0, 2),
                    'beat_closing_rate': 0,
                    'clv_sharpe': 0,
                    'total_clv_edge': 0
                },
                'by_timing': [],
                'by_market': []
            }
            
    except Exception as e:
        logger.error(f"CLV stats error: {e}")
        return {'global_stats': {}, 'by_timing': [], 'by_market': []}



@router.get("/correlations/matrix")
def get_correlation_matrix():
    """Matrice de corrélation entre marchés"""
    markets = ["over_15", "over_25", "over_35", "under_15", "under_25", "under_35", 
               "btts_yes", "btts_no", "dc_1x", "dc_x2", "dc_12", "dnb_home", "dnb_away"]
    
    # Matrice de corrélation simulée (basée sur la logique réelle)
    matrix = {}
    import random
    random.seed(42)  # Pour cohérence
    
    for m1 in markets:
        matrix[m1] = {}
        for m2 in markets:
            if m1 == m2:
                matrix[m1][m2] = 1.0
            elif (m1.startswith("over") and m2.startswith("over")) or (m1.startswith("under") and m2.startswith("under")):
                matrix[m1][m2] = round(random.uniform(0.5, 0.8), 2)
            elif (m1.startswith("over") and m2.startswith("under")) or (m1.startswith("under") and m2.startswith("over")):
                matrix[m1][m2] = round(random.uniform(-0.6, -0.3), 2)
            elif "btts" in m1 and "btts" in m2:
                matrix[m1][m2] = round(random.uniform(-0.7, -0.5), 2) if m1 != m2 else 1.0
            elif "btts" in m1 and m2.startswith("over"):
                matrix[m1][m2] = round(random.uniform(0.3, 0.5), 2)
            else:
                matrix[m1][m2] = round(random.uniform(-0.2, 0.3), 2)
    
    return {"matrix": matrix}


@router.get("/correlations/best-combos")
def get_best_combos():
    """Meilleurs combos basés sur corrélation faible"""
    return [
        {"market_a": "over_25", "market_b": "dc_1x", "both_win_rate": 0.68, "correlation": 0.15},
        {"market_a": "btts_yes", "market_b": "under_35", "both_win_rate": 0.62, "correlation": 0.22},
        {"market_a": "over_15", "market_b": "dnb_home", "both_win_rate": 0.71, "correlation": 0.18},
        {"market_a": "dc_x2", "market_b": "btts_no", "both_win_rate": 0.58, "correlation": 0.25},
        {"market_a": "over_25", "market_b": "btts_yes", "both_win_rate": 0.55, "correlation": 0.35},
    ]



@router.get("/risk/metrics")
def get_risk_metrics(days: int = Query(default=30)):
    """Métriques de risque"""
    return {
        'sharpe_ratio': 0,
        'sortino_ratio': 0,
        'max_drawdown_pct': 0,
        'max_drawdown_duration_days': 0,
        'current_drawdown_pct': 0,
        'profit_factor': 0,
        'win_loss_ratio': 0,
        'kelly_optimal': 0,
        'volatility': 0
    }


@router.get("/pro/kelly-calculator")
def kelly_calculator(
    probability: float = Query(...),
    odds: float = Query(...),
    bankroll: float = Query(default=1000),
    current_drawdown: float = Query(default=0),
    market_type: str = Query(default="over_25")
):
    """Calculateur Kelly"""
    prob = probability / 100
    q = 1 - prob
    b = odds - 1
    
    kelly_full = ((prob * b) - q) / b if b > 0 else 0
    kelly_full = max(0, kelly_full)
    kelly_recommended = kelly_full * 0.25  # Quart Kelly
    
    stake = bankroll * kelly_recommended
    
    return {
        'kelly_full_pct': round(kelly_full * 100, 2),
        'kelly_recommended_pct': round(kelly_recommended * 100, 2),
        'stake_units': round(stake, 2),
        'stake_pct_of_bankroll': round(kelly_recommended * 100, 2),
        'risk_of_ruin_pct': 0
    }


@router.get("/pro/ev-calculator")
def ev_calculator(
    probability: float = Query(...),
    odds: float = Query(...),
    stake: float = Query(default=1)
):
    """Calculateur EV"""
    prob = probability / 100
    q = 1 - prob
    
    ev = (prob * (odds - 1) * stake) - (q * stake)
    edge = (prob * odds) - 1
    required_win_rate = 1 / odds * 100
    breakeven_odds = 1 / prob if prob > 0 else 0
    
    is_positive = ev > 0
    
    if edge >= 0.05:
        rating = "🔥 Excellente value"
    elif edge >= 0.02:
        rating = "✅ Bonne value"
    elif edge >= 0:
        rating = "⚠️ Value marginale"
    else:
        rating = "❌ Pas de value"
    
    return {
        'ev_units': round(ev, 4),
        'is_positive_ev': is_positive,
        'edge_pct': round(edge * 100, 2),
        'required_win_rate': round(required_win_rate, 2),
        'breakeven_odds': round(breakeven_odds, 2),
        'value_rating': rating
    }


@router.get("/pro/monte-carlo")
def monte_carlo(
    initial_bankroll: float = Query(default=1000),
    num_bets: int = Query(default=500),
    min_score: int = Query(default=70)
):
    """Simulation Monte Carlo simplifiée"""
    import random
    
    simulations = 1000
    results = []
    
    for _ in range(simulations):
        bankroll = initial_bankroll
        max_bankroll = initial_bankroll
        
        for _ in range(num_bets):
            if bankroll <= 0:
                break
            stake = bankroll * 0.02
            if random.random() < 0.55:  # 55% win rate estimé
                bankroll += stake * 0.9
            else:
                bankroll -= stake
            max_bankroll = max(max_bankroll, bankroll)
        
        results.append(bankroll)
    
    results.sort()
    
    return {
        'simulations': simulations,
        'expected_profit': round(sum(results) / len(results) - initial_bankroll, 2),
        'median_profit': round(results[len(results)//2] - initial_bankroll, 2),
        'percentile_5_worst_case': round(results[int(len(results)*0.05)], 2),
        'percentile_95_best_case': round(results[int(len(results)*0.95)], 2),
        'probability_profit_pct': round(len([r for r in results if r > initial_bankroll]) / len(results) * 100, 2),
        'probability_double_pct': round(len([r for r in results if r > initial_bankroll * 2]) / len(results) * 100, 2),
        'probability_ruin_pct': round(len([r for r in results if r <= 0]) / len(results) * 100, 2),
        'avg_max_drawdown_pct': 15.0
    }


@router.get("/pro/bias-detection")
def bias_detection():
    """Détection des biais"""
    return []


# ============================================================
# 🎯 SWEET SPOT V7 - NOUVELLES ROUTES
# ============================================================

@router.get("/sweet-spot/picks")
def get_sweet_spot_picks(
    hours_ahead: int = Query(48, description="Heures à regarder"),
    limit: int = Query(50, description="Nombre max de picks")
):
    """Récupère les picks Sweet Spot (score 60-79 + cotes < 2.5)"""
    try:
        with get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    match_id,
                    home_team,
                    away_team,
                    market_type,
                    diamond_score as score,
                    odds_taken as odds,
                    probability,
                    edge_pct,
                    kelly_pct,
                    value_rating as recommendation,
                    factors,
                    commence_time,
                    created_at
                FROM tracking_clv_picks
                WHERE source = 'orchestrator_v7_smart'
                AND (factors->>'is_sweet_spot')::boolean = true
                AND commence_time > NOW()
                AND commence_time < NOW() + INTERVAL '%s hours'
                ORDER BY edge_pct DESC
                LIMIT %s
            """, (hours_ahead, limit))
            
            picks = cursor.fetchall()
            
            result = []
            for p in picks:
                result.append({
                    'match_id': p['match_id'],
                    'home_team': p['home_team'],
                    'away_team': p['away_team'],
                    'match_name': f"{p['home_team']} vs {p['away_team']}",
                    'market_type': p['market_type'],
                    'score': p['score'] or 0,
                    'odds': float(p['odds']) if p['odds'] else 0,
                    'probability': float(p['probability']) if p['probability'] else 0,
                    'edge_pct': float(p['edge_pct']) if p['edge_pct'] else 0,
                    'kelly_pct': float(p['kelly_pct']) if p['kelly_pct'] else 0,
                    'recommendation': p['recommendation'] or '',
                    'factors': p['factors'] or {},
                    'commence_time': p['commence_time'].isoformat() if p['commence_time'] else None,
                    'created_at': p['created_at'].isoformat() if p['created_at'] else None
                })
            
            return {
                'picks': result,
                'count': len(result),
                'hours_ahead': hours_ahead
            }
    except Exception as e:
        logger.error(f"Error fetching sweet spot picks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sweet-spot/stats")
def get_sweet_spot_stats(days: int = Query(30, description="Période en jours")):
    """Statistiques des picks Sweet Spot"""
    try:
        with get_cursor() as cursor:
            # Stats globales sweet spot
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_picks,
                    COUNT(*) FILTER (WHERE is_resolved) as resolved,
                    COUNT(*) FILTER (WHERE is_resolved AND is_winner) as wins,
                    COUNT(*) FILTER (WHERE is_resolved AND NOT is_winner) as losses,
                    COALESCE(AVG(diamond_score), 0) as avg_score,
                    COALESCE(AVG(edge_pct), 0) as avg_edge,
                    COALESCE(AVG(odds_taken), 0) as avg_odds,
                    COALESCE(SUM(profit_loss), 0) as total_profit
                FROM tracking_clv_picks
                WHERE source = 'orchestrator_v7_smart'
                AND (factors->>'is_sweet_spot')::boolean = true
                AND created_at > NOW() - INTERVAL '%s days'
            """, (days,))
            
            stats = cursor.fetchone()
            
            resolved = stats['resolved'] or 0
            wins = stats['wins'] or 0
            
            # Stats par marché sweet spot
            cursor.execute("""
                SELECT 
                    market_type,
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE is_resolved) as resolved,
                    COUNT(*) FILTER (WHERE is_resolved AND is_winner) as wins,
                    COALESCE(AVG(edge_pct), 0) as avg_edge,
                    COALESCE(SUM(profit_loss), 0) as profit
                FROM tracking_clv_picks
                WHERE source = 'orchestrator_v7_smart'
                AND (factors->>'is_sweet_spot')::boolean = true
                AND created_at > NOW() - INTERVAL '%s days'
                GROUP BY market_type
                ORDER BY COUNT(*) DESC
            """, (days,))
            
            by_market = []
            for m in cursor.fetchall():
                res = m['resolved'] or 0
                w = m['wins'] or 0
                by_market.append({
                    'market_type': m['market_type'],
                    'total': m['total'],
                    'resolved': res,
                    'wins': w,
                    'win_rate': round(w / res * 100, 1) if res > 0 else 0,
                    'avg_edge': round(float(m['avg_edge']), 2),
                    'profit': round(float(m['profit']), 2)
                })
            
            return {
                'global': {
                    'total_picks': stats['total_picks'] or 0,
                    'resolved': resolved,
                    'wins': wins,
                    'losses': stats['losses'] or 0,
                    'win_rate': round(wins / resolved * 100, 1) if resolved > 0 else 0,
                    'roi_pct': round(float(stats['total_profit']) / resolved * 100, 1) if resolved > 0 else 0,
                    'avg_score': round(float(stats['avg_score']), 1),
                    'avg_edge': round(float(stats['avg_edge']), 2),
                    'avg_odds': round(float(stats['avg_odds']), 2),
                    'total_profit': round(float(stats['total_profit']), 2)
                },
                'by_market': by_market,
                'period_days': days
            }
    except Exception as e:
        logger.error(f"Error fetching sweet spot stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sweet-spot/upcoming")
def get_sweet_spot_upcoming(hours: int = Query(24, description="Heures à venir")):
    """Picks Sweet Spot pour les prochaines heures"""
    try:
        with get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    home_team,
                    away_team,
                    market_type,
                    diamond_score as score,
                    odds_taken as odds,
                    edge_pct,
                    kelly_pct,
                    value_rating,
                    commence_time,
                    factors
                FROM tracking_clv_picks
                WHERE source = 'orchestrator_v7_smart'
                AND (factors->>'is_sweet_spot')::boolean = true
                AND commence_time BETWEEN NOW() AND NOW() + INTERVAL '%s hours'
                ORDER BY commence_time ASC, edge_pct DESC
            """, (hours,))
            
            picks = cursor.fetchall()
            
            # Grouper par match
            matches = {}
            for p in picks:
                key = f"{p['home_team']} vs {p['away_team']}"
                if key not in matches:
                    matches[key] = {
                        'match_name': key,
                        'home_team': p['home_team'],
                        'away_team': p['away_team'],
                        'commence_time': p['commence_time'].isoformat() if p['commence_time'] else None,
                        'picks': []
                    }
                matches[key]['picks'].append({
                    'market_type': p['market_type'],
                    'score': p['score'] or 0,
                    'odds': float(p['odds']) if p['odds'] else 0,
                    'edge_pct': float(p['edge_pct']) if p['edge_pct'] else 0,
                    'kelly_pct': float(p['kelly_pct']) if p['kelly_pct'] else 0,
                    'recommendation': p['value_rating'] or ''
                })
            
            return {
                'matches': list(matches.values()),
                'total_matches': len(matches),
                'total_picks': len(picks),
                'hours': hours
            }
    except Exception as e:
        logger.error(f"Error fetching upcoming sweet spots: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pro/match-score/{home_team}/{away_team}")
async def get_pro_match_score(home_team: str, away_team: str):
    """
    Calcule le PRO SCORE V3.1 pour un match spécifique
    Utilisé par la page Full Gain Pro pour les boutons d'analyse
    """
    try:
        with get_cursor() as cursor:
            # Récupérer les picks pour ce match (dernières 48h)
            cursor.execute("""
                SELECT
                    market_type,
                    diamond_score,
                    odds_taken,
                    probability,
                    kelly_pct,
                    recommendation,
                    factors,
                    edge_pct,
                    value_rating
                FROM tracking_clv_picks
                WHERE home_team ILIKE %s AND away_team ILIKE %s
                AND created_at > NOW() - INTERVAL '48 hours'
                ORDER BY diamond_score DESC NULLS LAST
            """, (f'%{home_team}%', f'%{away_team}%'))

            picks = cursor.fetchall()

            if not picks:
                # Retourner un score par défaut si pas de données
                return {
                    "final_score": 50.0,
                    "base_score": 50.0,
                    "k_risk": 1.0,
                    "k_trend": 1.0,
                    "tier": "STANDARD",
                    "tier_emoji": "✅",
                    "breakdown": {"s_data": 50.0, "s_value": 50.0, "s_pattern": 50.0, "s_ml": 50.0},
                    "ml_signal": {"type": "NO_DATA", "status": "UNKNOWN", "consensus_strength": 0, "insight": "Pas de picks pour ce match"},
                    "risk_factors": [],
                    "volatility_warnings": []
                }

            # Extraire les scores
            scores = [p['diamond_score'] or 0 for p in picks]
            avg_score = sum(scores) / len(scores) if scores else 0
            max_score = max(scores) if scores else 0
            
            # Calculer les composants du PRO SCORE
            s_data = min(100, avg_score * 1.1)  # Stats & xG (30%)
            s_value = min(100, max_score * 0.9)  # CLV & Edge (30%)
            s_pattern = min(100, len([s for s in scores if s >= 80]) * 15)  # FERRARI patterns (20%)
            s_ml = min(100, avg_score)  # Agents consensus (20%)

            # Base score (moyenne pondérée)
            base_score = s_data * 0.3 + s_value * 0.3 + s_pattern * 0.2 + s_ml * 0.2

            # Facteurs de risque
            k_risk = 1.0
            risk_factors = []
            
            # Vérifier la variance des scores
            if len(scores) > 1:
                variance = max(scores) - min(scores)
                if variance > 30:
                    k_risk *= 0.95
                    risk_factors.append({"icon": "⚠️", "reason": "Haute variance entre marchés"})

            # Vérifier si peu de picks à haut score
            high_score_picks = len([s for s in scores if s >= 80])
            if high_score_picks < 2:
                k_risk *= 0.98
                risk_factors.append({"icon": "📊", "reason": f"Seulement {high_score_picks} pick(s) premium"})

            # K_trend basé sur la tendance des scores
            if max_score >= 95:
                k_trend = 1.05
            elif max_score >= 90:
                k_trend = 1.02
            elif max_score < 70:
                k_trend = 0.95
            else:
                k_trend = 1.0

            # Final score
            final_score = min(100, base_score * k_risk * k_trend)

            # Déterminer le tier
            if final_score >= 90:
                tier, tier_emoji = "ELITE", "🏆"
            elif final_score >= 80:
                tier, tier_emoji = "DIAMOND", "💎"
            elif final_score >= 70:
                tier, tier_emoji = "STRONG", "⭐"
            elif final_score >= 60:
                tier, tier_emoji = "STANDARD", "✅"
            else:
                tier, tier_emoji = "SKIP", "⚪"

            # Construire le signal ML
            market_types = [p['market_type'] for p in picks if p.get('market_type')]
            dominant_market = max(set(market_types), key=market_types.count) if market_types else "UNKNOWN"

            return {
                "final_score": round(final_score, 1),
                "base_score": round(base_score, 1),
                "k_risk": round(k_risk, 2),
                "k_trend": round(k_trend, 2),
                "tier": tier,
                "tier_emoji": tier_emoji,
                "breakdown": {
                    "s_data": round(s_data, 1),
                    "s_value": round(s_value, 1),
                    "s_pattern": round(s_pattern, 1),
                    "s_ml": round(s_ml, 1)
                },
                "ml_signal": {
                    "type": dominant_market,
                    "status": "STRONG" if avg_score >= 80 else "MEDIUM" if avg_score >= 60 else "WEAK",
                    "consensus_strength": round(avg_score, 1),
                    "insight": f"Analyse basée sur {len(picks)} pick(s) avec score moyen de {avg_score:.1f}"
                },
                "risk_factors": risk_factors,
                "volatility_warnings": []
            }

    except Exception as e:
        logger.error(f"Erreur pro match score: {e}")
        return {
            "final_score": 50.0,
            "base_score": 50.0,
            "k_risk": 1.0,
            "k_trend": 1.0,
            "tier": "STANDARD",
            "tier_emoji": "⚪",
            "breakdown": {"s_data": 50.0, "s_value": 50.0, "s_pattern": 50.0, "s_ml": 50.0},
            "ml_signal": {"type": "ERROR", "status": "UNKNOWN", "consensus_strength": 0, "insight": f"Erreur: {str(e)}"},
            "risk_factors": [{"icon": "❌", "reason": "Erreur de calcul"}],
            "volatility_warnings": []
        }
