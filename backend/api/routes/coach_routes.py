"""
🧠 COACH INTELLIGENCE API ROUTES
================================
Endpoints pour accéder aux données Coach Intelligence
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Optional
import sys

sys.path.insert(0, "/app/agents")

router = APIRouter(prefix="/api/coach", tags=["Coach Intelligence"])


@router.get("/health")
async def coach_health():
    """Vérifier que Coach Intelligence est disponible"""
    try:
        from coach_impact import CoachImpactCalculator
        calc = CoachImpactCalculator()
        return {
            "status": "ok",
            "enabled": True,
            "avg_gf": round(calc.LEAGUE_AVG_GF, 2),
            "avg_ga": round(calc.LEAGUE_AVG_GA, 2)
        }
    except Exception as e:
        return {"status": "error", "enabled": False, "error": str(e)}


@router.get("/team/{team_name}")
async def get_team_coach(team_name: str):
    """Récupérer les infos coach d'une équipe"""
    try:
        from coach_impact import CoachImpactCalculator
        calc = CoachImpactCalculator()
        factors = calc.get_coach_factors(team_name)
        
        if factors.get('style') == 'unknown':
            raise HTTPException(status_code=404, detail=f"Coach non trouvé pour: {team_name}")
        
        return {
            "team": team_name,
            "coach": factors.get('coach'),
            "tactical_style": factors.get('style'),
            "attack_multiplier": round(factors.get('att', 1.0), 2),
            "defense_multiplier": round(factors.get('def', 1.0), 2),
            "is_reliable": factors.get('reliable', False),
            "insights": _generate_insights(factors)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preview/{home_team}/{away_team}")
async def get_tactical_preview(home_team: str, away_team: str):
    """
    �� Preview tactique complet pour un match
    
    Returns:
        - Infos coaches
        - Matchup tactique
        - xG ajustés
        - Recommandations marchés
    """
    try:
        from coach_impact import CoachImpactCalculator
        calc = CoachImpactCalculator()
        
        home_factors = calc.get_coach_factors(home_team)
        away_factors = calc.get_coach_factors(away_team)
        
        # Calculer xG ajustés (base 1.5 home, 1.2 away)
        base_home_xg = 1.5
        base_away_xg = 1.2
        
        result = calc.calculate_adjusted_xg(
            home_team, away_team,
            base_home_xg, base_away_xg
        )
        
        # Déterminer le matchup
        h_style = home_factors.get('style', 'unknown')
        a_style = away_factors.get('style', 'unknown')
        
        matchup = _determine_matchup(h_style, a_style)
        market_recommendations = _get_market_recommendations(matchup, result)
        
        return {
            "match": f"{home_team} vs {away_team}",
            "home_coach": {
                "name": home_factors.get('coach'),
                "style": h_style,
                "attack": round(home_factors.get('att', 1.0), 2),
                "defense": round(home_factors.get('def', 1.0), 2),
                "insights": _generate_insights(home_factors)
            },
            "away_coach": {
                "name": away_factors.get('coach'),
                "style": a_style,
                "attack": round(away_factors.get('att', 1.0), 2),
                "defense": round(away_factors.get('def', 1.0), 2),
                "insights": _generate_insights(away_factors)
            },
            "tactical_matchup": matchup,
            "expected_goals": {
                "home_xg": result['home_xg'],
                "away_xg": result['away_xg'],
                "total_xg": result['total_xg'],
                "base_comparison": {
                    "home_base": base_home_xg,
                    "away_base": base_away_xg,
                    "home_adjusted": result['home_xg'],
                    "away_adjusted": result['away_xg']
                }
            },
            "market_recommendations": market_recommendations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _determine_matchup(h_style: str, a_style: str) -> Dict:
    """Détermine le type de confrontation tactique"""
    h_off = 'offensive' in h_style
    h_def = 'defensive' in h_style
    a_off = 'offensive' in a_style
    a_def = 'defensive' in a_style
    
    if h_off and a_off:
        return {
            "type": "OPEN_GAME",
            "emoji": "🔥",
            "description": "Match ouvert - Les deux coaches offensifs",
            "expected_goals": "Élevé (3+ buts probable)"
        }
    elif h_def and a_def:
        return {
            "type": "CLOSED_GAME",
            "emoji": "🛡️",
            "description": "Match fermé - Les deux coaches défensifs",
            "expected_goals": "Faible (<2 buts probable)"
        }
    elif h_off and a_def:
        return {
            "type": "HOME_SIEGE",
            "emoji": "⚔️",
            "description": "Siège domicile - Home attaque, Away se défend",
            "expected_goals": "Modéré (2-3 buts)"
        }
    elif h_def and a_off:
        return {
            "type": "COUNTER_ATTACK",
            "emoji": "🏃",
            "description": "Contre-attaque - Home se défend, Away attaque",
            "expected_goals": "Modéré avec risque de surprise"
        }
    else:
        return {
            "type": "BALANCED",
            "emoji": "⚖️",
            "description": "Match équilibré",
            "expected_goals": "Standard (2-3 buts)"
        }


def _get_market_recommendations(matchup: Dict, xg_result: Dict) -> Dict:
    """Génère les recommandations par marché"""
    recs = {}
    matchup_type = matchup.get('type', 'BALANCED')
    total_xg = xg_result.get('total_xg', 2.5)
    
    # Over/Under
    if matchup_type == 'OPEN_GAME' or total_xg > 3.0:
        recs['over_25'] = {"recommendation": "✅ STRONG", "boost": 15, "reason": "Match ouvert + xG élevés"}
        recs['btts_yes'] = {"recommendation": "✅ GOOD", "boost": 10, "reason": "Les deux équipes marquent"}
    elif matchup_type == 'CLOSED_GAME' or total_xg < 2.2:
        recs['under_25'] = {"recommendation": "✅ STRONG", "boost": 15, "reason": "Match fermé + xG faibles"}
        recs['btts_no'] = {"recommendation": "📊 LEAN", "boost": 5, "reason": "Défenses solides"}
    
    # 1X2
    if matchup_type == 'HOME_SIEGE':
        recs['home_win'] = {"recommendation": "📊 LEAN", "boost": 5, "reason": "Domination domicile attendue"}
    elif matchup_type == 'COUNTER_ATTACK':
        recs['draw'] = {"recommendation": "📊 LEAN", "boost": 8, "reason": "Équilibre défensif possible"}
    
    return recs


def _generate_insights(factors: Dict) -> list:
    """Génère des insights basés sur les facteurs coach"""
    insights = []
    style = factors.get('style', 'unknown')
    att = factors.get('att', 1.0)
    def_mult = factors.get('def', 1.0)
    
    if 'dominant_offensive' in style:
        insights.append("🔥 Style très offensif - Favorise les Over")
    elif 'offensive' in style:
        insights.append("⚽ Style offensif - Bons pour BTTS")
    elif 'ultra_defensive' in style:
        insights.append("🧱 Ultra défensif - Favorise les Under")
    elif 'defensive' in style:
        insights.append("🛡️ Style défensif - Clean sheets fréquents")
    
    if att > 1.5:
        insights.append(f"📈 Attaque x{att:.1f} au-dessus de la moyenne")
    if def_mult < 0.7:
        insights.append(f"💪 Défense solide ({def_mult:.1f}x moins de buts)")
    elif def_mult > 1.3:
        insights.append(f"⚠️ Défense poreuse ({def_mult:.1f}x plus de buts)")
    
    return insights
