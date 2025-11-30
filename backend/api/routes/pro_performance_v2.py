"""
📊 PERFORMANCE ANALYTICS V2 - HEDGE FUND LEVEL
═══════════════════════════════════════════════════════════════════════════════

Métriques avancées pour trading sportif professionnel:
- CLV (Closing Line Value) - Indicateur #1
- ROI réel avec stake tracking
- Max Drawdown & Risk Metrics
- Sharpe Ratio adapté aux paris
- Losing Streak Detection
- EV vs Realized comparison

VERSION: 2.0.0
DATE: 30/11/2025
"""

from fastapi import APIRouter, Query
from datetime import datetime
from typing import Optional
import structlog

from api.services.database import get_db, get_cursor

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/pro", tags=["Pro Performance V2"])


@router.get("/performance/clv-analysis")
async def get_clv_analysis(days: int = Query(30, ge=7, le=365)):
    """
    📈 CLV ANALYSIS - LA MÉTRIQUE REINE
    
    CLV = (odds_taken / closing_odds - 1) * 100
    
    - CLV > 0% = Tu bats le marché (long-term winner)
    - CLV < 0% = Le marché te bat (long-term loser)
    """
    try:
        with get_cursor() as cursor:
            # CLV Global
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_bets,
                    COUNT(*) FILTER (WHERE closing_odds IS NOT NULL AND closing_odds > 0) as bets_with_clv,
                    
                    -- CLV moyen (formule standard)
                    ROUND(AVG(
                        CASE WHEN closing_odds > 0 THEN 
                            (odds_taken / closing_odds - 1) * 100 
                        ELSE NULL END
                    )::numeric, 3) as avg_clv_percent,
                    
                    -- CLV positif vs négatif
                    COUNT(*) FILTER (WHERE closing_odds > 0 AND odds_taken > closing_odds) as positive_clv_count,
                    COUNT(*) FILTER (WHERE closing_odds > 0 AND odds_taken <= closing_odds) as negative_clv_count,
                    
                    -- CLV par résultat
                    ROUND(AVG(
                        CASE WHEN closing_odds > 0 AND is_winner = true THEN 
                            (odds_taken / closing_odds - 1) * 100 
                        ELSE NULL END
                    )::numeric, 3) as avg_clv_winners,
                    
                    ROUND(AVG(
                        CASE WHEN closing_odds > 0 AND is_winner = false THEN 
                            (odds_taken / closing_odds - 1) * 100 
                        ELSE NULL END
                    )::numeric, 3) as avg_clv_losers,
                    
                    -- Win rate pour comparaison
                    ROUND(
                        COUNT(*) FILTER (WHERE is_winner = true)::numeric / 
                        NULLIF(COUNT(*) FILTER (WHERE is_resolved = true), 0) * 100, 2
                    ) as win_rate
                    
                FROM tracking_clv_picks
                WHERE created_at > NOW() - INTERVAL '%s days'
            """, (days,))
            
            global_clv = cursor.fetchone()
            
            # CLV par tier
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN diamond_score >= 90 THEN 'ELITE 90+'
                        WHEN diamond_score >= 80 THEN 'DIAMOND 80+'
                        WHEN diamond_score >= 70 THEN 'STRONG 70+'
                        ELSE 'STANDARD'
                    END as tier,
                    COUNT(*) as total,
                    ROUND(AVG(
                        CASE WHEN closing_odds > 0 THEN 
                            (odds_taken / closing_odds - 1) * 100 
                        ELSE NULL END
                    )::numeric, 3) as avg_clv,
                    ROUND(
                        COUNT(*) FILTER (WHERE is_winner = true)::numeric / 
                        NULLIF(COUNT(*) FILTER (WHERE is_resolved = true), 0) * 100, 2
                    ) as win_rate
                FROM tracking_clv_picks
                WHERE created_at > NOW() - INTERVAL '%s days'
                AND closing_odds IS NOT NULL AND closing_odds > 0
                GROUP BY 1
                ORDER BY avg_clv DESC NULLS LAST
            """, (days,))
            
            clv_by_tier = cursor.fetchall()
            
            # CLV par marché
            cursor.execute("""
                SELECT 
                    COALESCE(market_type, 'unknown') as market,
                    COUNT(*) as total,
                    ROUND(AVG(
                        CASE WHEN closing_odds > 0 THEN 
                            (odds_taken / closing_odds - 1) * 100 
                        ELSE NULL END
                    )::numeric, 3) as avg_clv,
                    ROUND(
                        COUNT(*) FILTER (WHERE is_winner = true)::numeric / 
                        NULLIF(COUNT(*) FILTER (WHERE is_resolved = true), 0) * 100, 2
                    ) as win_rate
                FROM tracking_clv_picks
                WHERE created_at > NOW() - INTERVAL '%s days'
                AND closing_odds IS NOT NULL AND closing_odds > 0
                GROUP BY 1
                HAVING COUNT(*) >= 5
                ORDER BY avg_clv DESC NULLS LAST
            """, (days,))
            
            clv_by_market = cursor.fetchall()
            
            # Interpréter le CLV
            avg_clv = float(global_clv['avg_clv_percent'] or 0)
            interpretation = ""
            if avg_clv > 3:
                interpretation = "🏆 EXCELLENT - Tu bats fortement le marché. Continue!"
            elif avg_clv > 1:
                interpretation = "✅ BON - Tu bats le marché. Système profitable long-terme."
            elif avg_clv > 0:
                interpretation = "⚠️ MARGINAL - Légèrement positif. Amélioration possible."
            elif avg_clv > -2:
                interpretation = "🔶 ATTENTION - CLV négatif. Révise ta sélection."
            else:
                interpretation = "🛑 DANGER - Tu perds face au marché. Stop et analyse."
            
            return {
                "period_days": days,
                "generated_at": datetime.now().isoformat(),
                "global": {
                    "total_bets": global_clv['total_bets'],
                    "bets_with_clv_data": global_clv['bets_with_clv'],
                    "avg_clv_percent": float(global_clv['avg_clv_percent'] or 0),
                    "positive_clv_bets": global_clv['positive_clv_count'],
                    "negative_clv_bets": global_clv['negative_clv_count'],
                    "clv_positive_rate": round(
                        global_clv['positive_clv_count'] / 
                        (global_clv['positive_clv_count'] + global_clv['negative_clv_count']) * 100, 1
                    ) if (global_clv['positive_clv_count'] + global_clv['negative_clv_count']) > 0 else 0,
                    "avg_clv_winners": float(global_clv['avg_clv_winners'] or 0),
                    "avg_clv_losers": float(global_clv['avg_clv_losers'] or 0),
                    "win_rate": float(global_clv['win_rate'] or 0)
                },
                "interpretation": interpretation,
                "by_tier": [
                    {
                        "tier": t['tier'],
                        "total": t['total'],
                        "avg_clv": float(t['avg_clv'] or 0),
                        "win_rate": float(t['win_rate'] or 0)
                    }
                    for t in clv_by_tier
                ],
                "by_market": [
                    {
                        "market": m['market'],
                        "total": m['total'],
                        "avg_clv": float(m['avg_clv'] or 0),
                        "win_rate": float(m['win_rate'] or 0)
                    }
                    for m in clv_by_market
                ],
                "key_insight": "Le CLV prédit le profit futur. Un CLV > 0% constant = tu gagneras sur le long terme, même avec variance négative temporaire."
            }
            
    except Exception as e:
        logger.error(f"Erreur CLV analysis: {e}")
        return {"error": str(e)}


@router.get("/performance/roi-analysis")
async def get_roi_analysis(days: int = Query(30, ge=7, le=365)):
    """
    💰 ROI ANALYSIS - Retour sur Investissement réel
    
    ROI = (Total Profit / Total Staked) * 100
    """
    try:
        with get_cursor() as cursor:
            # ROI global (utiliser stake si disponible, sinon 1 unité par pari)
            cursor.execute("""
                SELECT 
                    COUNT(*) FILTER (WHERE is_resolved = true) as total_resolved,
                    
                    -- Si stake existe, l'utiliser, sinon 1 unité par pari
                    COALESCE(SUM(
                        CASE WHEN is_resolved = true THEN 
                            COALESCE(stake, 1) 
                        ELSE 0 END
                    ), 0) as total_staked,
                    
                    COALESCE(SUM(profit_loss), 0) as total_profit,
                    
                    -- ROI
                    ROUND(
                        (SUM(profit_loss) / NULLIF(SUM(COALESCE(stake, 1)), 0) * 100)::numeric, 
                    2) as roi_percent,
                    
                    -- Profit moyen par pari
                    ROUND(AVG(profit_loss)::numeric, 3) as avg_profit_per_bet,
                    
                    -- Stats additionnelles
                    COUNT(*) FILTER (WHERE is_winner = true) as wins,
                    COUNT(*) FILTER (WHERE is_winner = false AND is_resolved = true) as losses,
                    ROUND(AVG(odds_taken)::numeric, 2) as avg_odds
                    
                FROM tracking_clv_picks
                WHERE created_at > NOW() - INTERVAL '%s days'
            """, (days,))
            
            roi_global = cursor.fetchone()
            
            # ROI par tier
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN diamond_score >= 90 THEN 'ELITE 90+'
                        WHEN diamond_score >= 80 THEN 'DIAMOND 80+'
                        WHEN diamond_score >= 70 THEN 'STRONG 70+'
                        ELSE 'STANDARD'
                    END as tier,
                    COUNT(*) FILTER (WHERE is_resolved = true) as resolved,
                    ROUND(SUM(COALESCE(stake, 1))::numeric, 2) as staked,
                    ROUND(SUM(profit_loss)::numeric, 2) as profit,
                    ROUND(
                        (SUM(profit_loss) / NULLIF(SUM(COALESCE(stake, 1)), 0) * 100)::numeric, 
                    2) as roi
                FROM tracking_clv_picks
                WHERE created_at > NOW() - INTERVAL '%s days'
                GROUP BY 1
                ORDER BY roi DESC NULLS LAST
            """, (days,))
            
            roi_by_tier = cursor.fetchall()
            
            return {
                "period_days": days,
                "generated_at": datetime.now().isoformat(),
                "global": {
                    "total_resolved": roi_global['total_resolved'],
                    "total_staked": float(roi_global['total_staked'] or 0),
                    "total_profit": float(roi_global['total_profit'] or 0),
                    "roi_percent": float(roi_global['roi_percent'] or 0),
                    "avg_profit_per_bet": float(roi_global['avg_profit_per_bet'] or 0),
                    "wins": roi_global['wins'],
                    "losses": roi_global['losses'],
                    "avg_odds": float(roi_global['avg_odds'] or 0)
                },
                "by_tier": [
                    {
                        "tier": t['tier'],
                        "resolved": t['resolved'],
                        "staked": float(t['staked'] or 0),
                        "profit": float(t['profit'] or 0),
                        "roi": float(t['roi'] or 0)
                    }
                    for t in roi_by_tier
                ],
                "benchmark": {
                    "excellent": "> 10% ROI",
                    "good": "5-10% ROI",
                    "acceptable": "2-5% ROI",
                    "break_even": "0-2% ROI",
                    "losing": "< 0% ROI"
                }
            }
            
    except Exception as e:
        logger.error(f"Erreur ROI analysis: {e}")
        return {"error": str(e)}


@router.get("/performance/risk-metrics")
async def get_risk_metrics(days: int = Query(30, ge=7, le=365)):
    """
    ⚠️ RISK METRICS - Drawdown, Variance, Streaks
    """
    try:
        with get_cursor() as cursor:
            # Récupérer l'historique des P&L pour calculer le drawdown
            cursor.execute("""
                SELECT 
                    created_at::date as bet_date,
                    profit_loss,
                    SUM(profit_loss) OVER (ORDER BY created_at) as cumulative_pnl
                FROM tracking_clv_picks
                WHERE created_at > NOW() - INTERVAL '%s days'
                AND is_resolved = true
                ORDER BY created_at
            """, (days,))
            
            pnl_history = cursor.fetchall()
            
            # Calculer Max Drawdown
            peak = 0
            max_drawdown = 0
            drawdown_start = None
            drawdown_end = None
            
            for row in pnl_history:
                cumulative = float(row['cumulative_pnl'] or 0)
                if cumulative > peak:
                    peak = cumulative
                drawdown = peak - cumulative
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            
            # Losing streaks par marché
            cursor.execute("""
                WITH ranked AS (
                    SELECT 
                        market_type,
                        is_winner,
                        created_at,
                        ROW_NUMBER() OVER (PARTITION BY market_type ORDER BY created_at DESC) as rn
                    FROM tracking_clv_picks
                    WHERE is_resolved = true
                    AND created_at > NOW() - INTERVAL '%s days'
                ),
                streaks AS (
                    SELECT 
                        market_type,
                        COUNT(*) as streak_length
                    FROM ranked
                    WHERE is_winner = false
                    AND rn <= 10  -- Regarder les 10 derniers
                    GROUP BY market_type
                )
                SELECT * FROM streaks WHERE streak_length >= 3
                ORDER BY streak_length DESC
            """, (days,))
            
            losing_streaks = cursor.fetchall()
            
            # Variance des résultats
            cursor.execute("""
                SELECT 
                    ROUND(STDDEV(profit_loss)::numeric, 3) as profit_stddev,
                    ROUND(AVG(profit_loss)::numeric, 3) as avg_profit,
                    ROUND(MIN(profit_loss)::numeric, 2) as worst_loss,
                    ROUND(MAX(profit_loss)::numeric, 2) as best_win
                FROM tracking_clv_picks
                WHERE created_at > NOW() - INTERVAL '%s days'
                AND is_resolved = true
            """, (days,))
            
            variance = cursor.fetchone()
            
            # Calculer Sharpe-like ratio
            avg_profit = float(variance['avg_profit'] or 0)
            stddev = float(variance['profit_stddev'] or 1)
            sharpe_like = round(avg_profit / stddev, 3) if stddev > 0 else 0
            
            return {
                "period_days": days,
                "generated_at": datetime.now().isoformat(),
                "drawdown": {
                    "max_drawdown_units": round(max_drawdown, 2),
                    "interpretation": "🛑 DANGER" if max_drawdown > 20 else "⚠️ ATTENTION" if max_drawdown > 10 else "✅ OK"
                },
                "variance": {
                    "profit_stddev": float(variance['profit_stddev'] or 0),
                    "avg_profit": float(variance['avg_profit'] or 0),
                    "worst_single_loss": float(variance['worst_loss'] or 0),
                    "best_single_win": float(variance['best_win'] or 0),
                    "sharpe_like_ratio": sharpe_like
                },
                "losing_streaks": [
                    {
                        "market": s['market_type'],
                        "current_streak": s['streak_length'],
                        "action": "🛑 PAUSE IMMÉDIATE" if s['streak_length'] >= 5 else "⚠️ Surveiller"
                    }
                    for s in losing_streaks
                ],
                "risk_level": "HIGH" if max_drawdown > 15 or any(s['streak_length'] >= 5 for s in losing_streaks) else "MEDIUM" if max_drawdown > 8 else "LOW"
            }
            
    except Exception as e:
        logger.error(f"Erreur risk metrics: {e}")
        return {"error": str(e)}


@router.get("/performance/ev-calibration")
async def get_ev_calibration(days: int = Query(30, ge=7, le=365)):
    """
    🎯 EV CALIBRATION - Expected Value vs Realized Value
    
    Vérifie si nos probabilités sont bien calibrées
    """
    try:
        with get_cursor() as cursor:
            # Comparer EV prédit vs résultat réel par bucket de probabilité
            cursor.execute("""
                WITH buckets AS (
                    SELECT 
                        CASE 
                            WHEN notre_proba >= 80 THEN '80-100%'
                            WHEN notre_proba >= 60 THEN '60-80%'
                            WHEN notre_proba >= 40 THEN '40-60%'
                            WHEN notre_proba >= 20 THEN '20-40%'
                            ELSE '0-20%'
                        END as prob_bucket,
                        notre_proba,
                        is_winner,
                        odds_taken
                    FROM tracking_clv_picks
                    WHERE created_at > NOW() - INTERVAL '%s days'
                    AND is_resolved = true
                    AND notre_proba IS NOT NULL
                )
                SELECT 
                    prob_bucket,
                    COUNT(*) as sample_size,
                    ROUND(AVG(notre_proba)::numeric, 1) as avg_predicted_prob,
                    ROUND(
                        COUNT(*) FILTER (WHERE is_winner = true)::numeric / 
                        COUNT(*)::numeric * 100, 1
                    ) as actual_win_rate,
                    ROUND(AVG(odds_taken)::numeric, 2) as avg_odds
                FROM buckets
                GROUP BY prob_bucket
                ORDER BY prob_bucket DESC
            """, (days,))
            
            calibration = cursor.fetchall()
            
            # Calculer l'écart de calibration
            calibration_data = []
            total_deviation = 0
            total_samples = 0
            
            for row in calibration:
                predicted = float(row['avg_predicted_prob'] or 0)
                actual = float(row['actual_win_rate'] or 0)
                deviation = actual - predicted
                
                calibration_data.append({
                    "bucket": row['prob_bucket'],
                    "sample_size": row['sample_size'],
                    "predicted_prob": predicted,
                    "actual_win_rate": actual,
                    "deviation": round(deviation, 1),
                    "status": "✅ Bien calibré" if abs(deviation) < 5 else "⚠️ Sous-estimé" if deviation > 0 else "🔶 Sur-estimé"
                })
                
                total_deviation += abs(deviation) * row['sample_size']
                total_samples += row['sample_size']
            
            avg_deviation = round(total_deviation / total_samples, 2) if total_samples > 0 else 0
            
            return {
                "period_days": days,
                "generated_at": datetime.now().isoformat(),
                "calibration_by_bucket": calibration_data,
                "overall": {
                    "avg_absolute_deviation": avg_deviation,
                    "interpretation": "✅ Excellent" if avg_deviation < 3 else "⚠️ À améliorer" if avg_deviation < 7 else "🛑 Mal calibré"
                },
                "recommendation": "Si deviation > 0: Tu sous-estimes tes chances. Si deviation < 0: Tu surestimes."
            }
            
    except Exception as e:
        logger.error(f"Erreur EV calibration: {e}")
        return {"error": str(e)}


@router.get("/performance/dashboard")
async def get_full_dashboard(days: int = Query(30, ge=7, le=365)):
    """
    📊 DASHBOARD COMPLET - Toutes les métriques en un appel
    """
    clv = await get_clv_analysis(days)
    roi = await get_roi_analysis(days)
    risk = await get_risk_metrics(days)
    calibration = await get_ev_calibration(days)
    
    # Score global du système
    clv_score = min(max((float(clv.get('global', {}).get('avg_clv_percent', 0)) + 5) * 10, 0), 100)
    roi_score = min(max((float(roi.get('global', {}).get('roi_percent', 0)) + 10) * 5, 0), 100)
    risk_score = 100 - float(risk.get('drawdown', {}).get('max_drawdown_units', 0)) * 3
    
    system_score = round((clv_score * 0.4 + roi_score * 0.3 + risk_score * 0.3), 1)
    
    return {
        "period_days": days,
        "generated_at": datetime.now().isoformat(),
        "system_health_score": system_score,
        "system_status": "🏆 EXCELLENT" if system_score > 80 else "✅ BON" if system_score > 60 else "⚠️ À SURVEILLER" if system_score > 40 else "🛑 PROBLÈME",
        "key_metrics": {
            "clv_percent": clv.get('global', {}).get('avg_clv_percent', 0),
            "roi_percent": roi.get('global', {}).get('roi_percent', 0),
            "max_drawdown": risk.get('drawdown', {}).get('max_drawdown_units', 0),
            "calibration_error": calibration.get('overall', {}).get('avg_absolute_deviation', 0)
        },
        "clv_analysis": clv,
        "roi_analysis": roi,
        "risk_metrics": risk,
        "ev_calibration": calibration
    }
