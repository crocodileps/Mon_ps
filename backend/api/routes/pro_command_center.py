"""
��️ FULL GAIN 3.0 PRO - COMMAND CENTER API
Endpoint unifié qui agrège TOUTES les sources de données:
- Sweet Spots + Pro Score
- FERRARI Intelligence (teams + scorers)
- Agents ML (A, B, C, D)
- Market Patterns
- BTTS V2.1
- Correlations & Combos
"""

from fastapi import APIRouter, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import structlog
from api.services.database import get_db, get_cursor

logger = structlog.get_logger()
router = APIRouter(prefix="/api/pro", tags=["Pro Command Center"])


# ============================================================================
# HEALTH & STATS
# ============================================================================

@router.get("/command-center/health")
async def health():
    """Health check du Command Center"""
    return {
        "status": "operational",
        "version": "3.0.0",
        "timestamp": datetime.now().isoformat(),
        "modules": {
            "sweet_spots": True,
            "pro_score": True,
            "ferrari_intelligence": True,
            "agents_ml": True,
            "market_patterns": True,
            "btts_v2": True,
            "scorers": True,
            "correlations": True
        }
    }


@router.get("/command-center/stats")
async def get_global_stats():
    """Statistiques globales du système"""
    try:
        with get_cursor() as cursor:
            stats = {}
            
            # Sweet Spots par tier
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE diamond_score >= 90) as elite,
                    COUNT(*) FILTER (WHERE diamond_score >= 80 AND diamond_score < 90) as diamond,
                    COUNT(*) FILTER (WHERE diamond_score >= 70 AND diamond_score < 80) as strong,
                    ROUND(AVG(diamond_score)::numeric, 1) as avg_score,
                    COUNT(*) FILTER (WHERE is_winner = true) as wins,
                    COUNT(*) FILTER (WHERE is_resolved = true) as resolved
                FROM tracking_clv_picks
                WHERE created_at > NOW() - INTERVAL '7 days'
            """)
            picks_stats = cursor.fetchone()
            
            # Teams FERRARI
            cursor.execute("SELECT COUNT(*) FROM team_intelligence")
            teams_count = cursor.fetchone()['count']
            
            # Scorers
            cursor.execute("SELECT COUNT(*) FROM scorer_intelligence WHERE season_goals > 0")
            scorers_count = cursor.fetchone()['count']
            
            # Agents analyses
            cursor.execute("""
                SELECT COUNT(*) FROM agent_analyses 
                WHERE analyzed_at > NOW() - INTERVAL '24 hours'
            """)
            agents_24h = cursor.fetchone()['count']
            
            # Patterns profitables
            cursor.execute("""
                SELECT COUNT(*) FROM market_patterns 
                WHERE is_profitable = true AND sample_size >= 10
            """)
            patterns_profitable = cursor.fetchone()['count']
            
            # Combos
            cursor.execute("SELECT COUNT(*) FROM fg_combo_tracking")
            combos_count = cursor.fetchone()['count']
            
            return {
                "picks": {
                    "total_7d": picks_stats['total'],
                    "elite_90": picks_stats['elite'],
                    "diamond_80": picks_stats['diamond'],
                    "strong_70": picks_stats['strong'],
                    "avg_score": float(picks_stats['avg_score'] or 0),
                    "wins": picks_stats['wins'],
                    "resolved": picks_stats['resolved'],
                    "win_rate": round(picks_stats['wins'] / picks_stats['resolved'] * 100, 1) if picks_stats['resolved'] > 0 else 0
                },
                "ferrari": {
                    "teams": teams_count,
                    "scorers": scorers_count
                },
                "agents": {
                    "analyses_24h": agents_24h
                },
                "patterns": {
                    "profitable": patterns_profitable
                },
                "combos": {
                    "total": combos_count
                },
                "updated_at": datetime.now().isoformat()
            }
    except Exception as e:
        logger.error(f"Erreur stats: {e}")
        return {"error": str(e)}


# ============================================================================
# MATCHES LIST - Vue principale
# ============================================================================

@router.get("/command-center/matches")
async def get_matches_with_full_data(
    min_score: int = Query(0, description="Score minimum"),
    tier: Optional[str] = Query(None, description="ELITE, DIAMOND, STRONG, ALL"),
    market_type: Optional[str] = Query(None, description="Filtrer par marché"),
    limit: int = Query(50, description="Nombre max de matchs")
):
    """
    Liste des matchs avec données agrégées de TOUTES les sources
    """
    try:
        with get_cursor() as cursor:
            # Récupérer les matchs uniques avec leurs picks
            where_clauses = ["created_at > NOW() - INTERVAL '48 hours'"]
            params = []
            
            if min_score > 0:
                where_clauses.append("diamond_score >= %s")
                params.append(min_score)
            
            if tier == "ELITE":
                where_clauses.append("diamond_score >= 90")
            elif tier == "DIAMOND":
                where_clauses.append("diamond_score >= 80")
            elif tier == "STRONG":
                where_clauses.append("diamond_score >= 70")
            
            if market_type:
                where_clauses.append("market_type ILIKE %s")
                params.append(f"%{market_type}%")
            
            where_sql = " AND ".join(where_clauses)
            
            cursor.execute(f"""
                WITH match_picks AS (
                    SELECT 
                        home_team,
                        away_team,
                        league,
                        commence_time,
                        json_agg(json_build_object(
                            'id', id,
                            'market_type', market_type,
                            'prediction', prediction,
                            'odds_taken', odds_taken,
                            'diamond_score', diamond_score,
                            'probability', probability,
                            'kelly_pct', kelly_pct,
                            'recommendation', recommendation,
                            'value_rating', value_rating
                        ) ORDER BY diamond_score DESC) as picks,
                        MAX(diamond_score) as max_score,
                        AVG(diamond_score) as avg_score,
                        COUNT(*) as picks_count
                    FROM tracking_clv_picks
                    WHERE {where_sql}
                    GROUP BY home_team, away_team, league, commence_time
                )
                SELECT * FROM match_picks
                ORDER BY max_score DESC, commence_time ASC
                LIMIT %s
            """, params + [limit])
            
            matches = cursor.fetchall()
            
            result = []
            for match in matches:
                # Calculer le tier
                max_score = match['max_score'] or 0
                if max_score >= 90:
                    tier_name, tier_emoji = "ELITE", "🏆"
                elif max_score >= 80:
                    tier_name, tier_emoji = "DIAMOND", "💎"
                elif max_score >= 70:
                    tier_name, tier_emoji = "STRONG", "⭐"
                else:
                    tier_name, tier_emoji = "STANDARD", "✅"
                
                result.append({
                    "home_team": match['home_team'],
                    "away_team": match['away_team'],
                    "league": match['league'],
                    "commence_time": match['commence_time'].isoformat() if match['commence_time'] else None,
                    "max_score": float(max_score),
                    "avg_score": round(float(match['avg_score'] or 0), 1),
                    "picks_count": match['picks_count'],
                    "tier": tier_name,
                    "tier_emoji": tier_emoji,
                    "picks": match['picks']
                })
            
            return {
                "matches": result,
                "total": len(result),
                "filters": {
                    "min_score": min_score,
                    "tier": tier,
                    "market_type": market_type
                }
            }
    except Exception as e:
        logger.error(f"Erreur matches: {e}")
        return {"error": str(e), "matches": []}


# ============================================================================
# FERRARI INTELLIGENCE - Équipes
# ============================================================================

@router.get("/command-center/team/{team_name}")
async def get_team_intelligence(team_name: str):
    """
    Intelligence FERRARI complète pour une équipe
    """
    try:
        with get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    team_name,
                    league,
                    current_style,
                    current_form,
                    current_form_points,
                    home_strength,
                    home_win_rate,
                    home_draw_rate,
                    home_loss_rate,
                    home_goals_scored_avg,
                    home_goals_conceded_avg,
                    home_btts_rate,
                    home_over25_rate,
                    home_over15_rate,
                    home_clean_sheet_rate,
                    away_strength,
                    away_win_rate,
                    away_draw_rate,
                    away_loss_rate,
                    away_goals_scored_avg,
                    away_goals_conceded_avg,
                    away_btts_rate,
                    away_over25_rate,
                    away_clean_sheet_rate,
                    draw_tendency,
                    goals_tendency,
                    btts_tendency
                FROM team_intelligence
                WHERE team_name ILIKE %s OR team_name_normalized ILIKE %s
                LIMIT 1
            """, (f"%{team_name}%", f"%{team_name}%"))
            
            team = cursor.fetchone()
            
            if not team:
                return {"error": "Équipe non trouvée", "team_name": team_name}
            
            # Récupérer les buteurs de cette équipe
            cursor.execute("""
                SELECT 
                    player_name,
                    position_primary,
                    season_goals,
                    goals_per_match,
                    goals_per_90,
                    season_assists,
                    is_penalty_taker,
                    is_freekick_taker,
                    penalty_conversion_rate,
                    season_xg,
                    xg_overperformance,
                    season_minutes,
                    preferred_foot
                FROM scorer_intelligence
                WHERE current_team ILIKE %s
                ORDER BY season_goals DESC
                LIMIT 5
            """, (f"%{team_name}%",))
            
            scorers = cursor.fetchall()
            
            return {
                "team": {
                    "name": team['team_name'],
                    "league": team['league'],
                    "style": team['current_style'],
                    "form": team['current_form'],
                    "form_points": team['current_form_points']
                },
                "home": {
                    "strength": float(team['home_strength'] or 0),
                    "win_rate": float(team['home_win_rate'] or 0),
                    "draw_rate": float(team['home_draw_rate'] or 0),
                    "loss_rate": float(team['home_loss_rate'] or 0),
                    "goals_scored": float(team['home_goals_scored_avg'] or 0),
                    "goals_conceded": float(team['home_goals_conceded_avg'] or 0),
                    "btts_rate": float(team['home_btts_rate'] or 0),
                    "over25_rate": float(team['home_over25_rate'] or 0),
                    "over15_rate": float(team['home_over15_rate'] or 0),
                    "clean_sheet_rate": float(team['home_clean_sheet_rate'] or 0)
                },
                "away": {
                    "strength": float(team['away_strength'] or 0),
                    "win_rate": float(team['away_win_rate'] or 0),
                    "draw_rate": float(team['away_draw_rate'] or 0),
                    "loss_rate": float(team['away_loss_rate'] or 0),
                    "goals_scored": float(team['away_goals_scored_avg'] or 0),
                    "goals_conceded": float(team['away_goals_conceded_avg'] or 0),
                    "btts_rate": float(team['away_btts_rate'] or 0),
                    "over25_rate": float(team['away_over25_rate'] or 0),
                    "clean_sheet_rate": float(team['away_clean_sheet_rate'] or 0)
                },
                "tendencies": {
                    "draw": team['draw_tendency'],
                    "goals": team['goals_tendency'],
                    "btts": team['btts_tendency']
                },
                "top_scorers": [
                    {
                        "name": s['player_name'],
                        "position": s['position_primary'],
                        "goals": s['season_goals'],
                        "goals_per_match": float(s['goals_per_match'] or 0),
                        "goals_per_90": float(s['goals_per_90'] or 0),
                        "assists": s['season_assists'],
                        "is_penalty_taker": s['is_penalty_taker'],
                        "is_freekick_taker": s['is_freekick_taker'],
                        "penalty_conversion": float(s['penalty_conversion_rate'] or 0),
                        "xg": float(s['season_xg'] or 0),
                        "xg_over": float(s['xg_overperformance'] or 0),
                        "minutes": s['season_minutes'],
                        "foot": s['preferred_foot']
                    }
                    for s in scorers
                ]
            }
    except Exception as e:
        logger.error(f"Erreur team intelligence: {e}")
        return {"error": str(e)}


# ============================================================================
# AGENTS ML - Analyses
# ============================================================================

@router.get("/command-center/agents/{home_team}/{away_team}")
async def get_agents_analysis(home_team: str, away_team: str):
    """
    Récupère les analyses de TOUS les agents ML pour un match
    """
    try:
        with get_cursor() as cursor:
            # Chercher les analyses des agents
            cursor.execute("""
                SELECT 
                    agent_name,
                    recommendation,
                    confidence_score,
                    reasoning,
                    factors,
                    analyzed_at
                FROM agent_analyses
                WHERE match_id ILIKE %s OR match_id ILIKE %s
                ORDER BY analyzed_at DESC
                LIMIT 20
            """, (f"%{home_team}%{away_team}%", f"%{away_team}%{home_team}%"))
            
            analyses = cursor.fetchall()
            
            # Grouper par agent
            agents_data = {}
            for a in analyses:
                agent = a['agent_name']
                if agent not in agents_data:
                    agents_data[agent] = {
                        "agent": agent,
                        "recommendation": a['recommendation'],
                        "confidence": float(a['confidence_score'] or 0),
                        "reasoning": a['reasoning'],
                        "factors": a['factors'],
                        "analyzed_at": a['analyzed_at'].isoformat() if a['analyzed_at'] else None
                    }
            
            # Calculer le consensus
            recommendations = [a['recommendation'] for a in agents_data.values() if a.get('recommendation')]
            confidences = [a['confidence'] for a in agents_data.values() if a.get('confidence')]
            
            consensus = None
            if recommendations:
                from collections import Counter
                consensus = Counter(recommendations).most_common(1)[0][0]
            
            return {
                "match": f"{home_team} vs {away_team}",
                "agents": list(agents_data.values()),
                "consensus": {
                    "recommendation": consensus,
                    "avg_confidence": round(sum(confidences) / len(confidences), 1) if confidences else 0,
                    "agents_count": len(agents_data)
                }
            }
    except Exception as e:
        logger.error(f"Erreur agents analysis: {e}")
        return {"error": str(e), "agents": []}


# ============================================================================
# MARKET PATTERNS
# ============================================================================

@router.get("/command-center/patterns")
async def get_profitable_patterns(
    market_type: Optional[str] = None,
    min_win_rate: float = 0.6,
    min_sample: int = 10
):
    """
    Patterns de marché profitables
    """
    try:
        with get_cursor() as cursor:
            where_clauses = ["win_rate >= %s", "sample_size >= %s"]
            params = [min_win_rate, min_sample]
            
            if market_type:
                where_clauses.append("market_type ILIKE %s")
                params.append(f"%{market_type}%")
            
            cursor.execute(f"""
                SELECT 
                    pattern_name,
                    pattern_code,
                    pattern_description,
                    market_type,
                    league,
                    day_of_week,
                    sample_size,
                    wins,
                    win_rate,
                    avg_odds,
                    roi,
                    profit_units,
                    confidence_score,
                    is_profitable,
                    recommendation,
                    stake_suggestion
                FROM market_patterns
                WHERE {" AND ".join(where_clauses)}
                ORDER BY roi DESC, win_rate DESC
                LIMIT 50
            """, params)
            
            patterns = cursor.fetchall()
            
            return {
                "patterns": [
                    {
                        "name": p['pattern_name'],
                        "code": p['pattern_code'],
                        "description": p['pattern_description'],
                        "market": p['market_type'],
                        "league": p['league'],
                        "day": p['day_of_week'],
                        "sample_size": p['sample_size'],
                        "wins": p['wins'],
                        "win_rate": float(p['win_rate'] or 0),
                        "avg_odds": float(p['avg_odds'] or 0),
                        "roi": float(p['roi'] or 0),
                        "profit_units": float(p['profit_units'] or 0),
                        "confidence": float(p['confidence_score'] or 0),
                        "is_profitable": p['is_profitable'],
                        "recommendation": p['recommendation'],
                        "stake": p['stake_suggestion']
                    }
                    for p in patterns
                ],
                "total": len(patterns),
                "filters": {
                    "min_win_rate": min_win_rate,
                    "min_sample": min_sample,
                    "market_type": market_type
                }
            }
    except Exception as e:
        logger.error(f"Erreur patterns: {e}")
        return {"error": str(e), "patterns": []}


# ============================================================================
# TOP SCORERS
# ============================================================================

@router.get("/command-center/scorers")
async def get_top_scorers(
    min_goals: int = 5,
    limit: int = 20
):
    """
    Top buteurs avec stats détaillées
    """
    try:
        with get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    player_name,
                    current_team,
                    nationality,
                    position_primary,
                    season_goals,
                    season_assists,
                    goals_per_match,
                    goals_per_90,
                    assists_per_90,
                    contributions_per_90,
                    minutes_per_goal,
                    season_xg,
                    xg_overperformance,
                    is_penalty_taker,
                    is_freekick_taker,
                    penalties_taken,
                    penalties_scored,
                    penalty_conversion_rate,
                    season_shots,
                    season_shots_on_target,
                    preferred_foot,
                    season_minutes,
                    season_matches
                FROM scorer_intelligence
                WHERE season_goals >= %s
                ORDER BY goals_per_match DESC, season_goals DESC
                LIMIT %s
            """, (min_goals, limit))
            
            scorers = cursor.fetchall()
            
            return {
                "scorers": [
                    {
                        "name": s['player_name'],
                        "team": s['current_team'],
                        "nationality": s['nationality'],
                        "position": s['position_primary'],
                        "goals": s['season_goals'],
                        "assists": s['season_assists'],
                        "goals_per_match": float(s['goals_per_match'] or 0),
                        "goals_per_90": float(s['goals_per_90'] or 0),
                        "assists_per_90": float(s['assists_per_90'] or 0),
                        "contributions_per_90": float(s['contributions_per_90'] or 0),
                        "minutes_per_goal": float(s['minutes_per_goal'] or 0),
                        "xg": float(s['season_xg'] or 0),
                        "xg_overperformance": float(s['xg_overperformance'] or 0),
                        "is_penalty_taker": s['is_penalty_taker'],
                        "is_freekick_taker": s['is_freekick_taker'],
                        "penalties": {
                            "taken": s['penalties_taken'],
                            "scored": s['penalties_scored'],
                            "conversion": float(s['penalty_conversion_rate'] or 0)
                        },
                        "shots": s['season_shots'],
                        "shots_on_target": s['season_shots_on_target'],
                        "foot": s['preferred_foot'],
                        "minutes": s['season_minutes'],
                        "matches": s['season_matches']
                    }
                    for s in scorers
                ],
                "total": len(scorers)
            }
    except Exception as e:
        logger.error(f"Erreur scorers: {e}")
        return {"error": str(e), "scorers": []}


# ============================================================================
# CORRELATIONS & COMBOS
# ============================================================================

@router.get("/command-center/correlations")
async def get_correlations():
    """
    Corrélations entre marchés pour les combos
    """
    try:
        with get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    id,
                    selections,
                    combined_probability,
                    expected_value,
                    status,
                    actual_result,
                    created_at
                FROM fg_combo_tracking
                ORDER BY created_at DESC
                LIMIT 30
            """)
            
            combos = cursor.fetchall()
            
            return {
                "combos": [
                    {
                        "id": c['id'],
                        "selections": c['selections'],
                        "probability": float(c['combined_probability'] or 0),
                        "ev": float(c['expected_value'] or 0),
                        "status": c['status'],
                        "result": c['actual_result'],
                        "created_at": c['created_at'].isoformat() if c['created_at'] else None
                    }
                    for c in combos
                ],
                "total": len(combos)
            }
    except Exception as e:
        logger.error(f"Erreur correlations: {e}")
        return {"error": str(e), "combos": []}


# ============================================================================
# MATCH FULL ANALYSIS - Agrégation complète
# ============================================================================

@router.get("/command-center/match/{home_team}/{away_team}")
async def get_full_match_analysis(home_team: str, away_team: str):
    """
    🎯 ANALYSE COMPLÈTE D'UN MATCH
    Agrège TOUTES les sources de données pour un match spécifique
    """
    try:
        result = {
            "match": f"{home_team} vs {away_team}",
            "generated_at": datetime.now().isoformat()
        }
        
        with get_cursor() as cursor:
            # 1. SWEET SPOTS
            cursor.execute("""
                SELECT 
                    market_type, prediction, odds_taken, diamond_score,
                    probability, kelly_pct, recommendation, value_rating, factors
                FROM tracking_clv_picks
                WHERE home_team ILIKE %s AND away_team ILIKE %s
                AND created_at > NOW() - INTERVAL '48 hours'
                ORDER BY diamond_score DESC
            """, (f"%{home_team}%", f"%{away_team}%"))
            picks = cursor.fetchall()
            
            result["sweet_spots"] = {
                "picks": [
                    {
                        "market": p['market_type'],
                        "prediction": p['prediction'],
                        "odds": float(p['odds_taken'] or 0),
                        "score": p['diamond_score'],
                        "probability": float(p['probability'] or 0),
                        "kelly": float(p['kelly_pct'] or 0),
                        "recommendation": p['recommendation'],
                        "value_rating": p['value_rating'],
                        "factors": p['factors']
                    }
                    for p in picks
                ],
                "count": len(picks),
                "max_score": max([p['diamond_score'] or 0 for p in picks]) if picks else 0,
                "avg_score": round(sum([p['diamond_score'] or 0 for p in picks]) / len(picks), 1) if picks else 0
            }
            
            # 2. PRO SCORE (calculé)
            scores = [p['diamond_score'] or 0 for p in picks]
            if scores:
                avg_score = sum(scores) / len(scores)
                max_score = max(scores)
                s_data = min(100, avg_score * 1.1)
                s_value = min(100, max_score * 0.9)
                s_pattern = min(100, len([s for s in scores if s >= 80]) * 15)
                s_ml = min(100, avg_score)
                base_score = s_data * 0.3 + s_value * 0.3 + s_pattern * 0.2 + s_ml * 0.2
                
                k_risk = 1.0
                if len(scores) > 1 and (max(scores) - min(scores)) > 30:
                    k_risk *= 0.95
                
                k_trend = 1.05 if max_score >= 95 else 1.02 if max_score >= 90 else 1.0
                final_score = min(100, base_score * k_risk * k_trend)
                
                if final_score >= 90:
                    tier, emoji = "ELITE", "🏆"
                elif final_score >= 80:
                    tier, emoji = "DIAMOND", "💎"
                elif final_score >= 70:
                    tier, emoji = "STRONG", "⭐"
                else:
                    tier, emoji = "STANDARD", "✅"
                
                result["pro_score"] = {
                    "final": round(final_score, 1),
                    "base": round(base_score, 1),
                    "tier": tier,
                    "emoji": emoji,
                    "breakdown": {
                        "s_data": round(s_data, 1),
                        "s_value": round(s_value, 1),
                        "s_pattern": round(s_pattern, 1),
                        "s_ml": round(s_ml, 1)
                    },
                    "k_risk": round(k_risk, 2),
                    "k_trend": round(k_trend, 2)
                }
            else:
                result["pro_score"] = {"final": 50, "tier": "UNKNOWN", "emoji": "❓"}
            
            # 3. FERRARI - Home Team
            cursor.execute("""
                SELECT team_name, current_style, current_form, home_strength,
                       home_win_rate, home_btts_rate, home_over25_rate,
                       home_goals_scored_avg, home_goals_conceded_avg
                FROM team_intelligence
                WHERE team_name ILIKE %s
                LIMIT 1
            """, (f"%{home_team}%",))
            home_intel = cursor.fetchone()
            
            # 4. FERRARI - Away Team
            cursor.execute("""
                SELECT team_name, current_style, current_form, away_strength,
                       away_win_rate, away_btts_rate, away_over25_rate,
                       away_goals_scored_avg, away_goals_conceded_avg
                FROM team_intelligence
                WHERE team_name ILIKE %s
                LIMIT 1
            """, (f"%{away_team}%",))
            away_intel = cursor.fetchone()
            
            result["ferrari"] = {
                "home": {
                    "name": home_intel['team_name'] if home_intel else home_team,
                    "style": home_intel['current_style'] if home_intel else "unknown",
                    "form": home_intel['current_form'] if home_intel else "unknown",
                    "strength": float(home_intel['home_strength'] or 0) if home_intel else 0,
                    "win_rate": float(home_intel['home_win_rate'] or 0) if home_intel else 0,
                    "btts_rate": float(home_intel['home_btts_rate'] or 0) if home_intel else 0,
                    "over25_rate": float(home_intel['home_over25_rate'] or 0) if home_intel else 0,
                    "goals_scored": float(home_intel['home_goals_scored_avg'] or 0) if home_intel else 0,
                    "goals_conceded": float(home_intel['home_goals_conceded_avg'] or 0) if home_intel else 0
                } if home_intel else None,
                "away": {
                    "name": away_intel['team_name'] if away_intel else away_team,
                    "style": away_intel['current_style'] if away_intel else "unknown",
                    "form": away_intel['current_form'] if away_intel else "unknown",
                    "strength": float(away_intel['away_strength'] or 0) if away_intel else 0,
                    "win_rate": float(away_intel['away_win_rate'] or 0) if away_intel else 0,
                    "btts_rate": float(away_intel['away_btts_rate'] or 0) if away_intel else 0,
                    "over25_rate": float(away_intel['away_over25_rate'] or 0) if away_intel else 0,
                    "goals_scored": float(away_intel['away_goals_scored_avg'] or 0) if away_intel else 0,
                    "goals_conceded": float(away_intel['away_goals_conceded_avg'] or 0) if away_intel else 0
                } if away_intel else None
            }
            
            # 5. TOP SCORERS des deux équipes
            cursor.execute("""
                SELECT player_name, current_team, season_goals, goals_per_match,
                       is_penalty_taker, season_xg, xg_overperformance
                FROM scorer_intelligence
                WHERE current_team ILIKE %s OR current_team ILIKE %s
                ORDER BY season_goals DESC
                LIMIT 6
            """, (f"%{home_team}%", f"%{away_team}%"))
            scorers = cursor.fetchall()
            
            result["scorers"] = [
                {
                    "name": s['player_name'],
                    "team": s['current_team'],
                    "goals": s['season_goals'],
                    "goals_per_match": float(s['goals_per_match'] or 0),
                    "is_penalty_taker": s['is_penalty_taker'],
                    "xg": float(s['season_xg'] or 0),
                    "xg_over": float(s['xg_overperformance'] or 0)
                }
                for s in scorers
            ]
            
            # 6. AGENTS ML
            cursor.execute("""
                SELECT agent_name, recommendation, confidence_score, reasoning
                FROM agent_analyses
                WHERE match_id ILIKE %s OR match_id ILIKE %s
                ORDER BY analyzed_at DESC
                LIMIT 10
            """, (f"%{home_team}%", f"%{away_team}%"))
            agents = cursor.fetchall()
            
            result["agents"] = [
                {
                    "name": a['agent_name'],
                    "recommendation": a['recommendation'],
                    "confidence": float(a['confidence_score'] or 0),
                    "reasoning": a['reasoning']
                }
                for a in agents
            ]
            
            return result
            
    except Exception as e:
        logger.error(f"Erreur full match analysis: {e}")
        return {"error": str(e), "match": f"{home_team} vs {away_team}"}


# ============================================================================
# MATCH ULTRA ANALYSIS - 100% DES DONNÉES
# ============================================================================

@router.get("/command-center/match-ultra/{home_team}/{away_team}")
async def get_ultra_match_analysis(home_team: str, away_team: str):
    """
    🎯 ANALYSE ULTRA-COMPLÈTE D'UN MATCH
    Utilise 100% des données disponibles:
    - Team Intelligence (83 colonnes)
    - Coach Intelligence (150 colonnes)
    - Scorer Intelligence (153 colonnes)
    - Odds movements
    - Smart Cache (API-Football)
    - Market Patterns
    - H2H Stats
    """
    try:
        result = {
            "match": f"{home_team} vs {away_team}",
            "generated_at": datetime.now().isoformat(),
            "data_sources_used": []
        }
        
        with get_cursor() as cursor:
            
            # ================================================================
            # 1. TEAM INTELLIGENCE COMPLET (Home)
            # ================================================================
            cursor.execute("""
                SELECT 
                    team_name, league, league_tier,
                    current_style, current_style_score, current_pressing,
                    current_form, current_form_points,
                    season_style, style_trend, style_trend_strength,
                    home_strength, home_win_rate, home_draw_rate, home_loss_rate,
                    home_goals_scored_avg, home_goals_conceded_avg,
                    home_btts_rate, home_over25_rate, home_over15_rate,
                    home_clean_sheet_rate, home_failed_to_score_rate,
                    home_profile,
                    draw_tendency, goals_tendency, btts_tendency,
                    clean_sheet_tendency, overperformance_goals, coach_style
                FROM team_intelligence
                WHERE team_name ILIKE %s
                LIMIT 1
            """, (f"%{home_team}%",))
            home_intel = cursor.fetchone()
            
            if home_intel:
                result["home_team"] = {
                    "name": home_intel['team_name'],
                    "league": home_intel['league'],
                    "league_tier": home_intel['league_tier'],
                    "style": {
                        "current": home_intel['current_style'],
                        "score": float(home_intel['current_style_score'] or 0),
                        "pressing": home_intel['current_pressing'],
                        "season": home_intel['season_style'],
                        "trend": home_intel['style_trend'],
                        "trend_strength": float(home_intel['style_trend_strength'] or 0),
                        "coach_style": home_intel['coach_style']
                    },
                    "form": {
                        "current": home_intel['current_form'],
                        "points": float(home_intel['current_form_points'] or 0)
                    },
                    "home_stats": {
                        "strength": float(home_intel['home_strength'] or 0),
                        "win_rate": float(home_intel['home_win_rate'] or 0),
                        "draw_rate": float(home_intel['home_draw_rate'] or 0),
                        "loss_rate": float(home_intel['home_loss_rate'] or 0),
                        "goals_scored": float(home_intel['home_goals_scored_avg'] or 0),
                        "goals_conceded": float(home_intel['home_goals_conceded_avg'] or 0),
                        "btts_rate": float(home_intel['home_btts_rate'] or 0),
                        "over25_rate": float(home_intel['home_over25_rate'] or 0),
                        "over15_rate": float(home_intel['home_over15_rate'] or 0),
                        "clean_sheet_rate": float(home_intel['home_clean_sheet_rate'] or 0),
                        "failed_to_score_rate": float(home_intel['home_failed_to_score_rate'] or 0),
                        "profile": home_intel['home_profile']
                    },
                    "tendencies": {
                        "draw": home_intel['draw_tendency'],
                        "goals": home_intel['goals_tendency'],
                        "btts": home_intel['btts_tendency'],
                        "clean_sheet": home_intel['clean_sheet_tendency'],
                        "overperformance": float(home_intel['overperformance_goals'] or 0)
                    }
                }
                result["data_sources_used"].append("team_intelligence_home")
            
            # ================================================================
            # 2. TEAM INTELLIGENCE COMPLET (Away)
            # ================================================================
            cursor.execute("""
                SELECT 
                    team_name, league, league_tier,
                    current_style, current_style_score, current_pressing,
                    current_form, current_form_points,
                    away_strength, away_win_rate, away_draw_rate, away_loss_rate,
                    away_goals_scored_avg, away_goals_conceded_avg,
                    away_btts_rate, away_over25_rate, away_over15_rate,
                    away_clean_sheet_rate, away_failed_to_score_rate,
                    away_profile,
                    draw_tendency, goals_tendency, btts_tendency, coach_style
                FROM team_intelligence
                WHERE team_name ILIKE %s
                LIMIT 1
            """, (f"%{away_team}%",))
            away_intel = cursor.fetchone()
            
            if away_intel:
                result["away_team"] = {
                    "name": away_intel['team_name'],
                    "league": away_intel['league'],
                    "style": {
                        "current": away_intel['current_style'],
                        "score": float(away_intel['current_style_score'] or 0),
                        "pressing": away_intel['current_pressing'],
                        "coach_style": away_intel['coach_style']
                    },
                    "form": {
                        "current": away_intel['current_form'],
                        "points": float(away_intel['current_form_points'] or 0)
                    },
                    "away_stats": {
                        "strength": float(away_intel['away_strength'] or 0),
                        "win_rate": float(away_intel['away_win_rate'] or 0),
                        "draw_rate": float(away_intel['away_draw_rate'] or 0),
                        "loss_rate": float(away_intel['away_loss_rate'] or 0),
                        "goals_scored": float(away_intel['away_goals_scored_avg'] or 0),
                        "goals_conceded": float(away_intel['away_goals_conceded_avg'] or 0),
                        "btts_rate": float(away_intel['away_btts_rate'] or 0),
                        "over25_rate": float(away_intel['away_over25_rate'] or 0),
                        "clean_sheet_rate": float(away_intel['away_clean_sheet_rate'] or 0),
                        "profile": away_intel['away_profile']
                    },
                    "tendencies": {
                        "draw": away_intel['draw_tendency'],
                        "goals": away_intel['goals_tendency'],
                        "btts": away_intel['btts_tendency']
                    }
                }
                result["data_sources_used"].append("team_intelligence_away")
            
            # ================================================================
            # 3. COACH INTELLIGENCE
            # ================================================================
            cursor.execute("""
                SELECT 
                    coach_name, nationality,
                    tactical_style, formation_primary, formation_secondary,
                    pressing_style, defensive_approach, attacking_approach,
                    buildup_style, tactical_flexibility,
                    approach_vs_stronger, approach_vs_weaker, approach_vs_similar,
                    in_game_adjustments,
                    career_win_rate, career_draw_rate, career_goals_for_avg,
                    home_win_rate as coach_home_win_rate,
                    current_team_win_rate
                FROM coach_intelligence
                WHERE current_team ILIKE %s
                LIMIT 1
            """, (f"%{home_team}%",))
            home_coach = cursor.fetchone()
            
            if home_coach:
                result["home_coach"] = {
                    "name": home_coach['coach_name'],
                    "nationality": home_coach['nationality'],
                    "tactical": {
                        "style": home_coach['tactical_style'],
                        "formation_primary": home_coach['formation_primary'],
                        "formation_secondary": home_coach['formation_secondary'],
                        "pressing": home_coach['pressing_style'],
                        "defensive": home_coach['defensive_approach'],
                        "attacking": home_coach['attacking_approach'],
                        "buildup": home_coach['buildup_style'],
                        "flexibility": home_coach['tactical_flexibility']
                    },
                    "approach": {
                        "vs_stronger": home_coach['approach_vs_stronger'],
                        "vs_weaker": home_coach['approach_vs_weaker'],
                        "vs_similar": home_coach['approach_vs_similar'],
                        "in_game_adjustments": home_coach['in_game_adjustments']
                    },
                    "stats": {
                        "career_win_rate": float(home_coach['career_win_rate'] or 0),
                        "career_draw_rate": float(home_coach['career_draw_rate'] or 0),
                        "goals_avg": float(home_coach['career_goals_for_avg'] or 0),
                        "home_win_rate": float(home_coach['coach_home_win_rate'] or 0),
                        "current_team_win_rate": float(home_coach['current_team_win_rate'] or 0)
                    }
                }
                result["data_sources_used"].append("coach_intelligence_home")
            
            # ================================================================
            # 4. SCORERS ENRICHIS (avec probabilités)
            # ================================================================
            cursor.execute("""
                SELECT 
                    player_name, current_team, position_primary,
                    season_goals, season_assists, goals_per_match, goals_per_90,
                    is_penalty_taker, is_freekick_taker,
                    penalty_conversion_rate, penalties_scored,
                    goals_right_foot, goals_left_foot, goals_header,
                    goals_inside_box, goals_outside_box,
                    anytime_scorer_prob, first_scorer_prob, two_plus_goals_prob,
                    home_goals, home_goals_per_match, home_anytime_prob,
                    away_goals, away_goals_per_match, away_anytime_prob,
                    goals_vs_top_teams, big_chance_conversion,
                    season_xg, xg_overperformance
                FROM scorer_intelligence
                WHERE current_team ILIKE %s OR current_team ILIKE %s
                ORDER BY season_goals DESC
                LIMIT 10
            """, (f"%{home_team}%", f"%{away_team}%"))
            scorers = cursor.fetchall()
            
            if scorers:
                result["scorers"] = [
                    {
                        "name": s['player_name'],
                        "team": s['current_team'],
                        "position": s['position_primary'],
                        "goals": {
                            "total": s['season_goals'],
                            "assists": s['season_assists'],
                            "per_match": float(s['goals_per_match'] or 0),
                            "per_90": float(s['goals_per_90'] or 0),
                            "home": s['home_goals'],
                            "away": s['away_goals'],
                            "vs_top_teams": s['goals_vs_top_teams']
                        },
                        "scoring_profile": {
                            "right_foot": s['goals_right_foot'],
                            "left_foot": s['goals_left_foot'],
                            "header": s['goals_header'],
                            "inside_box": s['goals_inside_box'],
                            "outside_box": s['goals_outside_box']
                        },
                        "set_pieces": {
                            "penalty_taker": s['is_penalty_taker'],
                            "freekick_taker": s['is_freekick_taker'],
                            "penalties_scored": s['penalties_scored'],
                            "penalty_conversion": float(s['penalty_conversion_rate'] or 0)
                        },
                        "probabilities": {
                            "anytime": float(s['anytime_scorer_prob'] or 0),
                            "first_scorer": float(s['first_scorer_prob'] or 0),
                            "two_plus": float(s['two_plus_goals_prob'] or 0),
                            "home_anytime": float(s['home_anytime_prob'] or 0),
                            "away_anytime": float(s['away_anytime_prob'] or 0)
                        },
                        "xg": {
                            "season": float(s['season_xg'] or 0),
                            "overperformance": float(s['xg_overperformance'] or 0),
                            "big_chance_conversion": float(s['big_chance_conversion'] or 0)
                        }
                    }
                    for s in scorers
                ]
                result["data_sources_used"].append("scorer_intelligence")
            
            # ================================================================
            # 5. ODDS MOVEMENT (Sharp Money Detection)
            # ================================================================
            cursor.execute("""
                SELECT 
                    bookmaker,
                    home_odds, draw_odds, away_odds,
                    collected_at
                FROM odds_history
                WHERE (home_team ILIKE %s AND away_team ILIKE %s)
                   OR (home_team ILIKE %s AND away_team ILIKE %s)
                ORDER BY collected_at DESC
                LIMIT 50
            """, (f"%{home_team}%", f"%{away_team}%", f"%{away_team}%", f"%{home_team}%"))
            odds_history = cursor.fetchall()
            
            if odds_history:
                # Calculer les mouvements
                first_odds = odds_history[-1] if odds_history else None
                last_odds = odds_history[0] if odds_history else None
                
                if first_odds and last_odds:
                    result["odds_movement"] = {
                        "home": {
                            "opening": float(first_odds['home_odds'] or 0),
                            "current": float(last_odds['home_odds'] or 0),
                            "movement": round(float(last_odds['home_odds'] or 0) - float(first_odds['home_odds'] or 0), 3),
                            "direction": "shortening" if (last_odds['home_odds'] or 0) < (first_odds['home_odds'] or 0) else "drifting"
                        },
                        "draw": {
                            "opening": float(first_odds['draw_odds'] or 0),
                            "current": float(last_odds['draw_odds'] or 0),
                            "movement": round(float(last_odds['draw_odds'] or 0) - float(first_odds['draw_odds'] or 0), 3)
                        },
                        "away": {
                            "opening": float(first_odds['away_odds'] or 0),
                            "current": float(last_odds['away_odds'] or 0),
                            "movement": round(float(last_odds['away_odds'] or 0) - float(first_odds['away_odds'] or 0), 3),
                            "direction": "shortening" if (last_odds['away_odds'] or 0) < (first_odds['away_odds'] or 0) else "drifting"
                        },
                        "samples": len(odds_history),
                        "period": f"{first_odds['collected_at']} to {last_odds['collected_at']}"
                    }
                    result["data_sources_used"].append("odds_history")
            
            # ================================================================
            # 6. HEAD TO HEAD
            # ================================================================
            cursor.execute("""
                SELECT *
                FROM team_head_to_head
                WHERE (team_a ILIKE %s AND team_b ILIKE %s)
                   OR (team_a ILIKE %s AND team_b ILIKE %s)
                LIMIT 1
            """, (f"%{home_team}%", f"%{away_team}%", f"%{away_team}%", f"%{home_team}%"))
            h2h = cursor.fetchone()
            
            if h2h:
                result["head_to_head"] = dict(h2h)
                result["data_sources_used"].append("team_head_to_head")
            
            # ================================================================
            # 7. LIVE STATISTICS
            # ================================================================
            cursor.execute("""
                SELECT 
                    team_name, form, matches_played,
                    wins, draws, losses,
                    goals_for, goals_against,
                    btts_pct, over_25_pct, under_25_pct,
                    clean_sheet_pct, avg_goals_scored, avg_goals_conceded
                FROM team_statistics_live
                WHERE team_name ILIKE %s OR team_name ILIKE %s
            """, (f"%{home_team}%", f"%{away_team}%"))
            live_stats = cursor.fetchall()
            
            if live_stats:
                result["live_statistics"] = [dict(s) for s in live_stats]
                result["data_sources_used"].append("team_statistics_live")
            
            # ================================================================
            # 8. MARKET PATTERNS APPLICABLES
            # ================================================================
            cursor.execute("""
                SELECT 
                    pattern_name, market_type, league,
                    win_rate, roi, sample_size, recommendation
                FROM market_patterns
                WHERE is_profitable = true
                AND (league ILIKE %s OR league IS NULL)
                ORDER BY roi DESC
                LIMIT 10
            """, (f"%{home_intel['league'] if home_intel else ''}%",))
            patterns = cursor.fetchall()
            
            if patterns:
                result["applicable_patterns"] = [
                    {
                        "name": p['pattern_name'],
                        "market": p['market_type'],
                        "league": p['league'],
                        "win_rate": float(p['win_rate'] or 0),
                        "roi": float(p['roi'] or 0),
                        "sample_size": p['sample_size'],
                        "recommendation": p['recommendation']
                    }
                    for p in patterns
                ]
                result["data_sources_used"].append("market_patterns")
            
            # ================================================================
            # 9. SWEET SPOTS
            # ================================================================
            cursor.execute("""
                SELECT 
                    market_type, prediction, odds_taken, diamond_score,
                    probability, kelly_pct, recommendation, value_rating
                FROM tracking_clv_picks
                WHERE home_team ILIKE %s AND away_team ILIKE %s
                AND created_at > NOW() - INTERVAL '48 hours'
                ORDER BY diamond_score DESC
            """, (f"%{home_team}%", f"%{away_team}%"))
            sweet_spots = cursor.fetchall()
            
            if sweet_spots:
                result["sweet_spots"] = [
                    {
                        "market": s['market_type'],
                        "prediction": s['prediction'],
                        "odds": float(s['odds_taken'] or 0),
                        "score": s['diamond_score'],
                        "probability": float(s['probability'] or 0),
                        "kelly": float(s['kelly_pct'] or 0),
                        "recommendation": s['recommendation'],
                        "value": s['value_rating']
                    }
                    for s in sweet_spots
                ]
                result["data_sources_used"].append("tracking_clv_picks")
            
            # ================================================================
            # RÉSUMÉ DES SOURCES
            # ================================================================
            result["analysis_summary"] = {
                "sources_count": len(result["data_sources_used"]),
                "data_quality": "HIGH" if len(result["data_sources_used"]) >= 5 else "MEDIUM" if len(result["data_sources_used"]) >= 3 else "LOW"
            }
            
            return result
            
    except Exception as e:
        logger.error(f"Erreur ultra match analysis: {e}")
        return {"error": str(e), "match": f"{home_team} vs {away_team}"}


# ============================================================================
# INTÉGRATION ALGOS V4/V5 + BTTS + PATRON + CONSEIL ULTIM
# ============================================================================

@router.get("/command-center/algos/{home_team}/{away_team}")
async def get_all_algos_analysis(home_team: str, away_team: str):
    """
    🧠 ANALYSE PAR TOUS LES ALGORITHMES
    - ALGO V4 Data-Driven
    - ALGO V5.1 SMART
    - BTTS V2.1 Agent
    - PATRON Diamond
    - Conseil Ultim (GPT-4)
    """
    import httpx
    
    result = {
        "match": f"{home_team} vs {away_team}",
        "generated_at": datetime.now().isoformat(),
        "algorithms": {}
    }
    
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # 1. ALGO V5.1 SMART
        try:
            resp = await client.get(f"{base_url}/api/smart/analyze/{home_team}/{away_team}")
            if resp.status_code == 200:
                result["algorithms"]["smart_v5"] = resp.json()
        except Exception as e:
            result["algorithms"]["smart_v5"] = {"error": str(e)}
        
        
        # 3. BTTS V2.1
        try:
            resp = await client.post(
                f"{base_url}/api/btts/analyze",
                json={"home_team": home_team, "away_team": away_team}
            )
            if resp.status_code == 200:
                result["algorithms"]["btts_v2"] = resp.json()
        except Exception as e:
            result["algorithms"]["btts_v2"] = {"error": str(e)}
    
    # 4. Agent Predictions (depuis DB)
    try:
        with get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    agent_name, prediction, confidence, reasoning,
                    predicted_outcome, predicted_probability
                FROM agent_predictions
                WHERE (home_team ILIKE %s AND away_team ILIKE %s)
                   OR match_id ILIKE %s
                ORDER BY created_at DESC
                LIMIT 10
            """, (f"%{home_team}%", f"%{away_team}%", f"%{home_team}%{away_team}%"))
            preds = cursor.fetchall()
            if preds:
                result["algorithms"]["agent_predictions"] = [dict(p) for p in preds]
    except Exception as e:
        result["algorithms"]["agent_predictions"] = {"error": str(e)}
    
    # 5. Conseil Ultim History
    try:
        with get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    recommended_outcome, recommended_label,
                    score, edge_reel, notre_proba, cote_moyenne,
                    risque, conseil, patron_score, patron_outcome
                FROM conseil_ultim_history
                WHERE home_team ILIKE %s AND away_team ILIKE %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (f"%{home_team}%", f"%{away_team}%"))
            conseil = cursor.fetchone()
            if conseil:
                result["algorithms"]["conseil_ultim_gpt4"] = dict(conseil)
    except Exception as e:
        result["algorithms"]["conseil_ultim_gpt4"] = {"error": str(e)}
    
    # 6. Match Results (historique)
    try:
        with get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    home_team, away_team, home_score, away_score,
                    match_date, league
                FROM matches_results
                WHERE (home_team ILIKE %s OR away_team ILIKE %s
                   OR home_team ILIKE %s OR away_team ILIKE %s)
                ORDER BY match_date DESC
                LIMIT 10
            """, (f"%{home_team}%", f"%{home_team}%", f"%{away_team}%", f"%{away_team}%"))
            results = cursor.fetchall()
            if results:
                result["historical_results"] = [dict(r) for r in results]
    except Exception as e:
        result["historical_results"] = {"error": str(e)}
    
    return result


@router.get("/command-center/full-analysis/{home_team}/{away_team}")
async def get_complete_analysis(home_team: str, away_team: str):
    """
    🎯 ANALYSE COMPLÈTE ULTIME
    Combine match-ultra + algos + tout le reste
    """
    # Récupérer l'analyse ultra
    ultra = await get_ultra_match_analysis(home_team, away_team)
    
    # Récupérer les algos
    algos = await get_all_algos_analysis(home_team, away_team)
    
    # Fusionner
    ultra["algorithms"] = algos.get("algorithms", {})
    ultra["historical_results"] = algos.get("historical_results", [])
    
    # Calculer un score global
    scores = []
    if ultra.get("pro_score", {}).get("final"):
        scores.append(ultra["pro_score"]["final"])
    if ultra.get("algorithms", {}).get("smart_v5", {}).get("score"):
        scores.append(ultra["algorithms"]["smart_v5"]["score"])
    if ultra.get("algorithms", {}).get("conseil_ultim_gpt4", {}).get("score"):
        scores.append(ultra["algorithms"]["conseil_ultim_gpt4"]["score"])
    
    if scores:
        ultra["global_score"] = {
            "average": round(sum(scores) / len(scores), 1),
            "max": max(scores),
            "min": min(scores),
            "sources_count": len(scores)
        }
    
    return ultra


# ============================================================================
# TEAM NORMALIZER ENDPOINTS
# ============================================================================

from api.services.team_normalizer import team_normalizer

@router.get("/command-center/normalize/{team_name}")
async def normalize_team_name(team_name: str):
    """
    🔄 Normalise un nom d'équipe vers son nom canonique
    """
    canonical = team_normalizer.normalize(team_name)
    aliases = team_normalizer.get_all_aliases(canonical)
    
    return {
        "input": team_name,
        "canonical": canonical,
        "aliases": aliases,
        "is_normalized": canonical != team_name
    }


@router.get("/command-center/team-mappings")
async def get_team_mappings_stats():
    """
    📊 Stats des mappings d'équipes
    """
    try:
        with get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM team_mapping) as canonical_teams,
                    (SELECT COUNT(*) FROM team_aliases) as total_aliases,
                    (SELECT COUNT(*) FROM team_name_mapping) as source_mappings,
                    (SELECT COUNT(DISTINCT source_table) FROM team_name_mapping) as source_tables
            """)
            stats = cursor.fetchone()
            
            # Top équipes avec le plus d'alias
            cursor.execute("""
                SELECT tm.team_name, COUNT(ta.id) as alias_count
                FROM team_mapping tm
                LEFT JOIN team_aliases ta ON tm.id = ta.team_mapping_id
                GROUP BY tm.team_name
                ORDER BY alias_count DESC
                LIMIT 10
            """)
            top_teams = cursor.fetchall()
            
            return {
                "stats": {
                    "canonical_teams": stats['canonical_teams'],
                    "total_aliases": stats['total_aliases'],
                    "source_mappings": stats['source_mappings'],
                    "source_tables": stats['source_tables']
                },
                "top_teams_by_aliases": [
                    {"team": t['team_name'], "aliases": t['alias_count']}
                    for t in top_teams
                ],
                "cache_size": len(team_normalizer._cache)
            }
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# BACKTESTING & PERFORMANCE SUMMARY
# ============================================================================

@router.get("/command-center/performance/summary")
async def get_performance_summary(days: int = 30):
    """
    📊 RÉSUMÉ DES PERFORMANCES DE TOUS LES SYSTÈMES
    Analyse les prédictions passées vs résultats réels
    """
    try:
        with get_cursor() as cursor:
            result = {
                "generated_at": datetime.now().isoformat(),
                "period_days": days,
                "systems": {}
            }
            
            # 1. Performance tracking_clv_picks (Sweet Spots)
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE is_resolved = true) as resolved,
                    COUNT(*) FILTER (WHERE is_winner = true) as wins,
                    COUNT(*) FILTER (WHERE is_winner = false AND is_resolved = true) as losses,
                    ROUND(AVG(diamond_score)::numeric, 1) as avg_score,
                    ROUND(SUM(profit_loss)::numeric, 2) as total_profit,
                    ROUND(
                        COUNT(*) FILTER (WHERE is_winner = true)::numeric / 
                        NULLIF(COUNT(*) FILTER (WHERE is_resolved = true), 0) * 100, 1
                    ) as win_rate,
                    -- CLV
                    ROUND(AVG(
                        CASE WHEN closing_odds > 0 THEN 
                            (odds_taken / closing_odds - 1) * 100 
                        ELSE NULL END
                    )::numeric, 3) as avg_clv,
                    -- ROI
                    ROUND(
                        (SUM(profit_loss) / NULLIF(COUNT(*) FILTER (WHERE is_resolved = true), 0) * 100)::numeric, 
                    2) as roi_percent
                FROM tracking_clv_picks
                WHERE created_at > NOW() - INTERVAL '%s days'
            """, (days,))
            sweet_spots = cursor.fetchone()
            result["systems"]["sweet_spots"] = {
                "total_picks": sweet_spots['total'],
                "resolved": sweet_spots['resolved'],
                "wins": sweet_spots['wins'],
                "losses": sweet_spots['losses'],
                "win_rate": float(sweet_spots['win_rate'] or 0),
                "avg_score": float(sweet_spots['avg_score'] or 0),
                "profit": float(sweet_spots['total_profit'] or 0),
                "avg_clv": float(sweet_spots['avg_clv'] or 0),
                "roi_percent": float(sweet_spots['roi_percent'] or 0)
            }
            
            # 2. Performance par tier
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN diamond_score >= 90 THEN 'ELITE 90+'
                        WHEN diamond_score >= 80 THEN 'DIAMOND 80+'
                        WHEN diamond_score >= 70 THEN 'STRONG 70+'
                        ELSE 'STANDARD'
                    END as tier,
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE is_resolved = true) as resolved,
                    COUNT(*) FILTER (WHERE is_winner = true) as wins,
                    ROUND(
                        COUNT(*) FILTER (WHERE is_winner = true)::numeric / 
                        NULLIF(COUNT(*) FILTER (WHERE is_resolved = true), 0) * 100, 1
                    ) as win_rate,
                    ROUND(SUM(profit_loss)::numeric, 2) as profit,
                    ROUND(AVG(
                        CASE WHEN closing_odds > 0 THEN 
                            (odds_taken / closing_odds - 1) * 100 
                        ELSE NULL END
                    )::numeric, 3) as avg_clv
                FROM tracking_clv_picks
                WHERE created_at > NOW() - INTERVAL '%s days'
                GROUP BY 1
                ORDER BY tier
            """, (days,))
            tiers = cursor.fetchall()
            result["systems"]["by_tier"] = [
                {
                    "tier": t['tier'],
                    "total": t['total'],
                    "resolved": t['resolved'],
                    "wins": t['wins'],
                    "win_rate": float(t['win_rate'] or 0),
                    "profit": float(t['profit'] or 0),
                    "avg_clv": float(t['avg_clv'] or 0)
                }
                for t in tiers
            ]
            
            # 3. Performance par type de marché
            cursor.execute("""
                SELECT 
                    COALESCE(market_type, 'unknown') as market,
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE is_resolved = true) as resolved,
                    COUNT(*) FILTER (WHERE is_winner = true) as wins,
                    ROUND(
                        COUNT(*) FILTER (WHERE is_winner = true)::numeric / 
                        NULLIF(COUNT(*) FILTER (WHERE is_resolved = true), 0) * 100, 1
                    ) as win_rate,
                    ROUND(SUM(profit_loss)::numeric, 2) as profit
                FROM tracking_clv_picks
                WHERE created_at > NOW() - INTERVAL '%s days'
                GROUP BY 1
                HAVING COUNT(*) >= 5
                ORDER BY win_rate DESC NULLS LAST
            """, (days,))
            markets = cursor.fetchall()
            result["systems"]["by_market"] = [
                {
                    "market": m['market'],
                    "total": m['total'],
                    "resolved": m['resolved'],
                    "wins": m['wins'],
                    "win_rate": float(m['win_rate'] or 0),
                    "profit": float(m['profit'] or 0)
                }
                for m in markets
            ]
            
            # 4. Performance agent_predictions
            cursor.execute("""
                SELECT 
                    agent_name,
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE was_correct = true) as correct,
                    ROUND(
                        COUNT(*) FILTER (WHERE was_correct = true)::numeric / 
                        NULLIF(COUNT(*) FILTER (WHERE was_correct IS NOT NULL), 0) * 100, 1
                    ) as accuracy,
                    ROUND(AVG(confidence)::numeric, 1) as avg_confidence,
                    ROUND(SUM(profit_loss)::numeric, 2) as profit
                FROM agent_predictions
                WHERE predicted_at > NOW() - INTERVAL '%s days'
                GROUP BY agent_name
                ORDER BY accuracy DESC NULLS LAST
            """, (days,))
            agents = cursor.fetchall()
            result["systems"]["agents"] = [
                {
                    "agent": a['agent_name'],
                    "total": a['total'],
                    "correct": a['correct'],
                    "accuracy": float(a['accuracy'] or 0),
                    "avg_confidence": float(a['avg_confidence'] or 0),
                    "profit": float(a['profit'] or 0)
                }
                for a in agents
            ]
            
            # 5. Performance conseil_ultim (GPT-4)
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE is_win = true) as wins,
                    COUNT(*) FILTER (WHERE is_win = false) as losses,
                    ROUND(
                        COUNT(*) FILTER (WHERE is_win = true)::numeric / 
                        NULLIF(COUNT(*) FILTER (WHERE is_win IS NOT NULL), 0) * 100, 1
                    ) as win_rate,
                    ROUND(AVG(score)::numeric, 1) as avg_score
                FROM conseil_ultim_history
            """)
            conseil = cursor.fetchone()
            result["systems"]["conseil_ultim_gpt4"] = {
                "total": conseil['total'],
                "wins": conseil['wins'],
                "losses": conseil['losses'],
                "win_rate": float(conseil['win_rate'] or 0),
                "avg_score": float(conseil['avg_score'] or 0)
            }
            
            # 6. Résultats récents du marché (baseline)
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_matches,
                    COUNT(*) FILTER (WHERE result = 'H') as home_wins,
                    COUNT(*) FILTER (WHERE result = 'D') as draws,
                    COUNT(*) FILTER (WHERE result = 'A') as away_wins,
                    ROUND(AVG(home_goals + away_goals)::numeric, 2) as avg_goals,
                    ROUND(
                        COUNT(*) FILTER (WHERE home_goals > 0 AND away_goals > 0)::numeric / 
                        NULLIF(COUNT(*), 0) * 100, 1
                    ) as btts_rate,
                    ROUND(
                        COUNT(*) FILTER (WHERE home_goals + away_goals > 2)::numeric / 
                        NULLIF(COUNT(*), 0) * 100, 1
                    ) as over25_rate
                FROM matches_results
                WHERE match_date > CURRENT_DATE - INTERVAL '%s days'
            """, (days,))
            recent = cursor.fetchone()
            
            if recent['total_matches'] and recent['total_matches'] > 0:
                result["market_reality"] = {
                    "matches_analyzed": recent['total_matches'],
                    "home_win_rate": round(recent['home_wins'] / recent['total_matches'] * 100, 1),
                    "draw_rate": round(recent['draws'] / recent['total_matches'] * 100, 1),
                    "away_win_rate": round(recent['away_wins'] / recent['total_matches'] * 100, 1),
                    "avg_goals": float(recent['avg_goals'] or 0),
                    "btts_rate": float(recent['btts_rate'] or 0),
                    "over25_rate": float(recent['over25_rate'] or 0)
                }
            else:
                result["market_reality"] = {"error": "Pas de données récentes"}
            
            # 7. Insights automatiques
            insights = []
            
            # Meilleur tier
            best_tier = max(result["systems"]["by_tier"], key=lambda x: x['win_rate'], default=None)
            if best_tier and best_tier['resolved'] >= 10:
                insights.append({
                    "type": "BEST_TIER",
                    "icon": "🏆",
                    "message": f"Meilleur tier: {best_tier['tier']} avec {best_tier['win_rate']}% win rate"
                })
            
            # CLV positif
            if result["systems"]["sweet_spots"]["avg_clv"] > 0:
                insights.append({
                    "type": "CLV_POSITIVE",
                    "icon": "📈",
                    "message": f"CLV positif: +{result['systems']['sweet_spots']['avg_clv']}% - Tu bats le marché!"
                })
            
            # Alerte si win rate < 45%
            if result["systems"]["sweet_spots"]["win_rate"] < 45:
                insights.append({
                    "type": "LOW_WIN_RATE",
                    "icon": "⚠️",
                    "message": f"Win rate bas: {result['systems']['sweet_spots']['win_rate']}% - Révise la sélection"
                })
            
            result["insights"] = insights
            
            return result
            
    except Exception as e:
        logger.error(f"Erreur performance summary: {e}")
        return {"error": str(e)}


@router.get("/command-center/performance/insights")
async def get_performance_insights(days: int = 30):
    """
    💡 INSIGHTS INTELLIGENTS SUR LES PERFORMANCES
    """
    try:
        with get_cursor() as cursor:
            insights = []
            
            # 1. Série perdante en cours
            cursor.execute("""
                WITH recent_bets AS (
                    SELECT 
                        is_winner,
                        ROW_NUMBER() OVER (ORDER BY created_at DESC) as rn
                    FROM tracking_clv_picks
                    WHERE is_resolved = true
                    ORDER BY created_at DESC
                    LIMIT 20
                )
                SELECT COUNT(*) as losing_streak
                FROM recent_bets
                WHERE is_winner = false
                AND rn <= (
                    SELECT COALESCE(MIN(rn) - 1, 20)
                    FROM recent_bets 
                    WHERE is_winner = true
                )
            """)
            streak = cursor.fetchone()
            if streak['losing_streak'] >= 5:
                insights.append({
                    "type": "LOSING_STREAK",
                    "severity": "HIGH" if streak['losing_streak'] >= 8 else "MEDIUM",
                    "icon": "🛑",
                    "message": f"Série de {streak['losing_streak']} pertes consécutives",
                    "action": "Réduire les stakes ou faire une pause"
                })
            
            # 2. Marché sous-performant
            cursor.execute("""
                SELECT 
                    market_type,
                    ROUND(
                        COUNT(*) FILTER (WHERE is_winner = true)::numeric / 
                        NULLIF(COUNT(*) FILTER (WHERE is_resolved = true), 0) * 100, 1
                    ) as win_rate,
                    COUNT(*) FILTER (WHERE is_resolved = true) as sample
                FROM tracking_clv_picks
                WHERE created_at > NOW() - INTERVAL '%s days'
                AND market_type IS NOT NULL
                GROUP BY market_type
                HAVING COUNT(*) FILTER (WHERE is_resolved = true) >= 10
                AND COUNT(*) FILTER (WHERE is_winner = true)::numeric / 
                    NULLIF(COUNT(*) FILTER (WHERE is_resolved = true), 0) * 100 < 40
            """, (days,))
            bad_markets = cursor.fetchall()
            for m in bad_markets:
                insights.append({
                    "type": "UNDERPERFORMING_MARKET",
                    "severity": "MEDIUM",
                    "icon": "⚠️",
                    "message": f"'{m['market_type']}' sous-performe: {m['win_rate']}% sur {m['sample']} paris",
                    "action": f"Éviter ou réduire {m['market_type']}"
                })
            
            # 3. Tier surperformant
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN diamond_score >= 90 THEN 'ELITE 90+'
                        WHEN diamond_score >= 80 THEN 'DIAMOND 80+'
                        WHEN diamond_score >= 70 THEN 'STRONG 70+'
                        ELSE 'STANDARD'
                    END as tier,
                    ROUND(
                        COUNT(*) FILTER (WHERE is_winner = true)::numeric / 
                        NULLIF(COUNT(*) FILTER (WHERE is_resolved = true), 0) * 100, 1
                    ) as win_rate,
                    COUNT(*) FILTER (WHERE is_resolved = true) as sample
                FROM tracking_clv_picks
                WHERE created_at > NOW() - INTERVAL '%s days'
                GROUP BY 1
                HAVING COUNT(*) FILTER (WHERE is_resolved = true) >= 10
                ORDER BY win_rate DESC
                LIMIT 1
            """, (days,))
            best = cursor.fetchone()
            if best and best['win_rate'] >= 55:
                insights.append({
                    "type": "BEST_PERFORMER",
                    "severity": "INFO",
                    "icon": "🏆",
                    "message": f"Meilleur: {best['tier']} à {best['win_rate']}% win rate ({best['sample']} paris)",
                    "action": f"Concentrer les stakes sur {best['tier']}"
                })
            
            return {
                "period_days": days,
                "insights_count": len(insights),
                "insights": insights,
                "generated_at": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Erreur insights: {e}")
        return {"error": str(e)}


# ============================================================================
# ADAPTIVE STRATEGY ENGINE V2.0 - ENDPOINTS FUTURISTES
# ============================================================================

from api.services.adaptive_strategy_engine_v2 import adaptive_engine_v2

@router.get("/command-center/strategy/v2/config")
async def get_adaptive_strategy_config_v2(
    force_refresh: bool = False,
    lookback_days: int = 30
):
    """
    🧠 CONFIGURATION STRATÉGIQUE ADAPTATIVE V2.0
    
    Retourne le diagnostic complet avec:
    - ROI-based evaluation (pas Win Rate absolu)
    - Wilson Confidence Intervals
    - Breakeven Analysis
    - Trend Detection
    - Auto-Diagnostic & Suggestions
    - Shadow Tracking status
    """
    config = adaptive_engine_v2.get_config(force_refresh=force_refresh, lookback_days=lookback_days)
    
    return {
        "version": "2.0.0",
        "generated_at": config.generated_at.isoformat(),
        "lookback_days": config.lookback_days,
        
        "system_health": {
            "status": config.system_health,
            "score": config.system_score,
            "interpretation": "Le système est en bonne santé" if config.system_score >= 60 else "Attention requise"
        },
        
        "rankings": {
            "tiers": config.tier_ranking,
            "markets": config.market_ranking
        },
        
        "thresholds": {
            "min_roi": config.min_roi_threshold,
            "min_clv": config.min_clv_threshold,
            "min_confidence": config.min_confidence_threshold
        },
        
        "tier_diagnostics": config.tier_diagnostics,
        "market_diagnostics": config.market_diagnostics,
        
        "optimal_combinations": config.optimal_combinations,
        
        "shadow_strategies": {
            "count": len(config.shadow_strategies),
            "strategies": config.shadow_strategies,
            "note": "Ces stratégies sont en paper trading - données collectées pour réintégration future"
        },
        
        "global_recommendations": config.global_recommendations
    }


@router.get("/command-center/strategy/v2/tier/{tier_name}")
async def get_tier_diagnostic(tier_name: str):
    """
    📊 DIAGNOSTIC DÉTAILLÉ D'UN TIER
    
    Analyse complète avec:
    - ROI réel vs Win Rate
    - Breakeven analysis
    - Wilson confidence interval
    - Issues identifiées
    - Suggestions d'amélioration
    """
    config = adaptive_engine_v2.get_config()
    
    # Normaliser le nom du tier
    tier_map = {
        "elite": "ELITE 90+",
        "elite90": "ELITE 90+",
        "diamond": "DIAMOND 80+",
        "diamond80": "DIAMOND 80+",
        "strong": "STRONG 70+",
        "strong70": "STRONG 70+",
        "standard": "STANDARD"
    }
    
    normalized = tier_map.get(tier_name.lower(), tier_name)
    diagnostic = config.tier_diagnostics.get(normalized)
    
    if not diagnostic:
        return {
            "error": f"Tier '{tier_name}' non trouvé",
            "available_tiers": list(config.tier_diagnostics.keys())
        }
    
    return {
        "tier": normalized,
        "diagnostic": diagnostic,
        "comparison": {
            "rank": config.tier_ranking.index(normalized) + 1 if normalized in config.tier_ranking else "N/A",
            "total_tiers": len(config.tier_ranking),
            "is_best": config.tier_ranking[0] == normalized if config.tier_ranking else False
        }
    }


@router.get("/command-center/strategy/v2/market/{market_name}")
async def get_market_diagnostic(market_name: str):
    """
    📊 DIAGNOSTIC DÉTAILLÉ D'UN MARCHÉ
    """
    config = adaptive_engine_v2.get_config()
    diagnostic = config.market_diagnostics.get(market_name)
    
    if not diagnostic:
        return {
            "error": f"Marché '{market_name}' non trouvé",
            "available_markets": list(config.market_diagnostics.keys())
        }
    
    return {
        "market": market_name,
        "diagnostic": diagnostic,
        "comparison": {
            "rank": config.market_ranking.index(market_name) + 1 if market_name in config.market_ranking else "N/A",
            "total_markets": len(config.market_ranking)
        }
    }


@router.get("/command-center/strategy/v2/evaluate")
async def evaluate_pick_v2(
    tier: str,
    market: str,
    score: float,
    odds: float = 2.0
):
    """
    🎯 ÉVALUE UN PICK AVEC LE MOTEUR V2.0
    
    Retourne:
    - Si le pick est recommandé pour pari réel
    - Le multiplicateur de stake
    - Si le pick doit être tracké (shadow)
    - La raison détaillée
    """
    accepted, reason, multiplier, shadow_track = adaptive_engine_v2.should_accept_pick_v2(
        tier, market, score, odds
    )
    
    return {
        "evaluation": {
            "tier": tier,
            "market": market,
            "score": score,
            "odds": odds
        },
        "decision": {
            "accepted_for_real_bet": accepted,
            "stake_multiplier": multiplier,
            "shadow_track": shadow_track,
            "reason": reason
        },
        "recommendation": (
            f"🏆 PARIER (stake x{multiplier:.1f})" if accepted and multiplier >= 1.0 else
            f"✅ PARIER (stake réduit x{multiplier:.1f})" if accepted else
            "👻 SHADOW TRACK UNIQUEMENT" if shadow_track else
            "❌ NE PAS SUIVRE"
        ),
        "note": "Shadow track = on enregistre le résultat sans parier pour récolter des données"
    }


@router.get("/command-center/strategy/v2/optimal-picks")
async def get_optimal_picks_v2():
    """
    🏆 PICKS OPTIMAUX DU JOUR (V2.0)
    
    Filtre et classe les picks avec le moteur adaptatif V2.
    Inclut les picks shadow pour le tracking.
    """
    try:
        with get_cursor() as cursor:
            # Récupérer les picks du jour
            cursor.execute("""
                SELECT 
                    id, home_team, away_team, market_type, prediction,
                    diamond_score, odds_taken, probability, edge_pct,
                    created_at, commence_time
                FROM tracking_clv_picks
                WHERE DATE(commence_time) >= CURRENT_DATE
                AND is_resolved = false
                ORDER BY diamond_score DESC
            """)
            
            picks = [dict(row) for row in cursor.fetchall()]
        
        config = adaptive_engine_v2.get_config()
        
        real_bets = []
        shadow_bets = []
        rejected = []
        
        for pick in picks:
            score = pick['diamond_score'] or 0
            market = pick.get('market_type', 'unknown')
            odds = float(pick.get('odds_taken', 2.0) or 2.0)
            
            # Déterminer le tier
            if score >= 90:
                tier = "ELITE 90+"
            elif score >= 80:
                tier = "DIAMOND 80+"
            elif score >= 70:
                tier = "STRONG 70+"
            else:
                tier = "STANDARD"
            
            accepted, reason, multiplier, shadow = adaptive_engine_v2.should_accept_pick_v2(
                tier, market, score, odds
            )
            
            pick_data = {
                "id": pick['id'],
                "match": f"{pick['home_team']} vs {pick['away_team']}",
                "market": market,
                "prediction": pick['prediction'],
                "score": score,
                "tier": tier,
                "odds": odds,
                "stake_multiplier": multiplier,
                "reason": reason,
                "commence_time": pick['commence_time'].isoformat() if pick['commence_time'] else None
            }
            
            if accepted:
                real_bets.append(pick_data)
            elif shadow:
                shadow_bets.append(pick_data)
            else:
                rejected.append(pick_data)
        
        # Trier les real bets par multiplicateur puis score
        real_bets.sort(key=lambda x: (x['stake_multiplier'], x['score']), reverse=True)
        
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "system_health": config.system_health,
            
            "summary": {
                "total_picks": len(picks),
                "real_bets": len(real_bets),
                "shadow_tracking": len(shadow_bets),
                "rejected": len(rejected)
            },
            
            "real_bets": {
                "count": len(real_bets),
                "description": "✅ Paris recommandés pour argent réel",
                "picks": real_bets[:15]
            },
            
            "shadow_tracking": {
                "count": len(shadow_bets),
                "description": "👻 Paper trading - On track sans parier",
                "picks": shadow_bets[:10]
            },
            
            "strategy_recommendations": config.global_recommendations
        }
        
    except Exception as e:
        logger.error(f"Erreur optimal picks V2: {e}")
        return {"error": str(e)}


@router.get("/command-center/strategy/v2/issues")
async def get_strategy_issues():
    """
    ⚠️ PROBLÈMES IDENTIFIÉS ET SOLUTIONS
    
    Liste tous les problèmes détectés avec des suggestions d'amélioration.
    """
    config = adaptive_engine_v2.get_config()
    
    all_issues = []
    all_improvements = []
    
    # Collecter depuis les tiers
    for tier, diag in config.tier_diagnostics.items():
        if diag.get('issues'):
            for issue in diag['issues']:
                all_issues.append({
                    "source": f"Tier: {tier}",
                    "issue": issue,
                    "roi": diag.get('roi_percent'),
                    "status": diag.get('status')
                })
        if diag.get('improvements'):
            for imp in diag['improvements']:
                all_improvements.append({
                    "source": f"Tier: {tier}",
                    "suggestion": imp
                })
    
    # Collecter depuis les marchés
    for market, diag in config.market_diagnostics.items():
        if diag.get('issues'):
            for issue in diag['issues']:
                all_issues.append({
                    "source": f"Marché: {market}",
                    "issue": issue,
                    "roi": diag.get('roi_percent'),
                    "status": diag.get('status')
                })
        if diag.get('improvements'):
            for imp in diag['improvements']:
                all_improvements.append({
                    "source": f"Marché: {market}",
                    "suggestion": imp
                })
    
    # Trier par sévérité (ROI)
    all_issues.sort(key=lambda x: x.get('roi', 0) or 0)
    
    return {
        "generated_at": datetime.now().isoformat(),
        
        "issues_summary": {
            "total_issues": len(all_issues),
            "critical": len([i for i in all_issues if (i.get('roi') or 0) < -10]),
            "warning": len([i for i in all_issues if -10 <= (i.get('roi') or 0) < 0]),
            "info": len([i for i in all_issues if (i.get('roi') or 0) >= 0])
        },
        
        "issues": all_issues,
        "improvements": all_improvements,
        
        "priority_actions": [
            imp for imp in all_improvements 
            if "💡" in imp.get('suggestion', '')
        ][:5]
    }


@router.get("/command-center/strategy/v2/shadow-report")
async def get_shadow_tracking_report():
    """
    👻 RAPPORT DES STRATÉGIES EN SHADOW
    
    Montre les stratégies en paper trading et leur évolution.
    Permet de détecter quand une stratégie est prête pour réintégration.
    """
    config = adaptive_engine_v2.get_config()
    
    shadow_details = []
    
    # Tiers en shadow
    for tier, diag in config.tier_diagnostics.items():
        if diag.get('is_shadow_mode'):
            shadow_details.append({
                "type": "tier",
                "name": tier,
                "roi": diag.get('roi_percent'),
                "clv": diag.get('clv_percent'),
                "trend": diag.get('trend'),
                "reason": diag.get('shadow_reason'),
                "recent_roi_7d": diag.get('recent_roi_7d'),
                "recovering": diag.get('trend') == 'improving',
                "recommendation": (
                    "🔄 RÉINTÉGRATION POSSIBLE" if diag.get('trend') == 'improving' and diag.get('recent_roi_7d', -100) > -5
                    else "⏳ CONTINUER OBSERVATION"
                )
            })
    
    # Marchés en shadow
    for market, diag in config.market_diagnostics.items():
        if diag.get('is_shadow_mode'):
            shadow_details.append({
                "type": "market",
                "name": market,
                "roi": diag.get('roi_percent'),
                "trend": diag.get('trend'),
                "reason": diag.get('shadow_reason'),
                "recent_roi_7d": diag.get('recent_roi_7d'),
                "recovering": diag.get('trend') == 'improving'
            })
    
    # Candidats à la réintégration
    reintegration_candidates = [
        s for s in shadow_details 
        if s.get('recovering') and s.get('recent_roi_7d', -100) > -5
    ]
    
    return {
        "generated_at": datetime.now().isoformat(),
        
        "shadow_count": len(shadow_details),
        "shadow_strategies": shadow_details,
        
        "reintegration": {
            "candidates_count": len(reintegration_candidates),
            "candidates": reintegration_candidates,
            "note": "Ces stratégies montrent des signes de reprise et pourraient être réintégrées"
        },
        
        "philosophy": "Le shadow tracking permet de ne jamais perdre de données précieuses. "
                     "Même les stratégies en difficulté continuent d'être observées pour "
                     "détecter leur potentielle reprise."
    }


@router.get("/command-center/strategy/v2/breakeven-analysis")
async def get_breakeven_analysis():
    """
    📊 ANALYSE BREAKEVEN COMPLÈTE
    
    Compare le Win Rate réel vs le Win Rate nécessaire pour chaque cote moyenne.
    """
    config = adaptive_engine_v2.get_config()
    
    analysis = []
    
    for tier, diag in config.tier_diagnostics.items():
        be = diag.get('breakeven', {})
        analysis.append({
            "strategy": tier,
            "type": "tier",
            "avg_odds": be.get('avg_odds'),
            "breakeven_wr": be.get('breakeven_win_rate'),
            "actual_wr": be.get('actual_win_rate'),
            "edge": be.get('edge_vs_breakeven'),
            "profitable": be.get('is_profitable_structure'),
            "verdict": (
                "✅ RENTABLE" if be.get('is_profitable_structure')
                else "❌ SOUS LE SEUIL"
            )
        })
    
    for market, diag in config.market_diagnostics.items():
        be = diag.get('breakeven', {})
        analysis.append({
            "strategy": market,
            "type": "market",
            "avg_odds": be.get('avg_odds'),
            "breakeven_wr": be.get('breakeven_win_rate'),
            "actual_wr": be.get('actual_win_rate'),
            "edge": be.get('edge_vs_breakeven'),
            "profitable": be.get('is_profitable_structure')
        })
    
    # Trier par edge
    analysis.sort(key=lambda x: x.get('edge', 0) or 0, reverse=True)
    
    profitable = [a for a in analysis if a.get('profitable')]
    unprofitable = [a for a in analysis if not a.get('profitable')]
    
    return {
        "summary": {
            "profitable_strategies": len(profitable),
            "unprofitable_strategies": len(unprofitable),
            "best_edge": analysis[0] if analysis else None
        },
        
        "profitable": profitable,
        "unprofitable": unprofitable,
        
        "insight": (
            "Le breakeven analysis montre si tu gagnes vraiment de l'argent "
            "en tenant compte des cotes moyennes. Un WR de 60% à @1.50 perd de l'argent, "
            "alors qu'un WR de 40% à @3.00 est rentable."
        )
    }
