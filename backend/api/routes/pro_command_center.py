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
