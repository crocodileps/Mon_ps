"""
Routes API pour Agent PATRON Diamond+ V3
Endpoints pour analyse multi-marchés (1X2, BTTS, Over 2.5)
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import math
import json
from datetime import datetime

router = APIRouter(prefix="/patron-diamond", tags=["Patron Diamond V3"])

# Configuration DB
DB_CONFIG = {
    'host': 'monps_postgres',
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}


# ============================================================
# HELPERS
# ============================================================

def poisson_prob(lam: float, k: int) -> float:
    """Probabilité Poisson P(X=k)"""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def calculate_poisson(home_xg: float, away_xg: float) -> dict:
    """Calcule probabilités via Poisson"""
    max_goals = 7
    btts = over15 = over25 = over35 = 0
    home_win = draw = away_win = 0
    score_probs = {}
    
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            prob = poisson_prob(home_xg, h) * poisson_prob(away_xg, a)
            score_probs[f"{h}-{a}"] = prob
            
            if h > a: home_win += prob
            elif h == a: draw += prob
            else: away_win += prob
            
            if h > 0 and a > 0: btts += prob
            total = h + a
            if total > 1: over15 += prob
            if total > 2: over25 += prob
            if total > 3: over35 += prob
    

    # ===== NOUVEAUX MARCHÉS PHASE 1 =====
    # Under (inverse des Over)
    under15 = 1 - over15
    under25 = 1 - over25
    under35 = 1 - over35
    
    # BTTS No
    btts_no = 1 - btts
    
    # Double Chance
    dc_1x = home_win + draw
    dc_x2 = draw + away_win
    dc_12 = home_win + away_win
    
    # Draw No Bet
    total_no_draw = home_win + away_win
    dnb_home = home_win / total_no_draw if total_no_draw > 0 else 0.5
    dnb_away = away_win / total_no_draw if total_no_draw > 0 else 0.5
    # ===== FIN NOUVEAUX MARCHÉS =====
    sorted_scores = sorted(score_probs.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        'btts_prob': round(btts * 100, 1),
        'over15_prob': round(over15 * 100, 1),
        'over25_prob': round(over25 * 100, 1),
        'over35_prob': round(over35 * 100, 1),
        '1x2': {
            'home': round(home_win * 100, 1),
            'draw': round(draw * 100, 1),
            'away': round(away_win * 100, 1)
        },
        'most_likely_scores': [(s, round(p * 100, 1)) for s, p in sorted_scores],
        # NOUVEAUX MARCHÉS
        'btts_no_prob': round(btts_no * 100, 1),
        'under15_prob': round(under15 * 100, 1),
        'under25_prob': round(under25 * 100, 1),
        'under35_prob': round(under35 * 100, 1),
        'double_chance': {
            '1x': round(dc_1x * 100, 1),
            'x2': round(dc_x2 * 100, 1),
            '12': round(dc_12 * 100, 1)
        },
        'draw_no_bet': {
            'home': round(dnb_home * 100, 1),
            'away': round(dnb_away * 100, 1)
        }
    }


def safe_float(value, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except:
        return default


def get_team_stats(team_name: str) -> Optional[dict]:
    """Récupère stats équipe depuis team_statistics_live"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Essayer nom exact puis partiel
        cur.execute("""
            SELECT * FROM team_statistics_live 
            WHERE team_name = %s OR team_name ILIKE %s
            LIMIT 1
        """, (team_name, f"%{team_name.split()[0]}%"))
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        return dict(row) if row else None
    except:
        return None


def get_h2h_stats(team_a: str, team_b: str) -> Optional[dict]:
    """Récupère H2H"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        t1, t2 = sorted([team_a, team_b])
        cur.execute("""
            SELECT * FROM team_head_to_head 
            WHERE (team_a ILIKE %s AND team_b ILIKE %s)
               OR (team_a ILIKE %s AND team_b ILIKE %s)
            LIMIT 1
        """, (f"%{t1.split()[0]}%", f"%{t2.split()[0]}%",
              f"%{t2.split()[0]}%", f"%{t1.split()[0]}%"))
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        return dict(row) if row else None
    except:
        return None


def get_recommendation(score: float, confidence: int) -> str:
    """Génère recommandation basée sur score et confidence"""
    if score >= 75 and confidence >= 70:
        return "💎 DIAMOND PICK"
    elif score >= 65 and confidence >= 60:
        return "✅ STRONG BET"
    elif score >= 55:
        return "📈 LEAN YES"
    elif score >= 45:
        return "⏭️ SKIP"
    else:
        return "❌ AVOID"


def get_value_rating(score: float, odds: float) -> str:
    """Calcule le rating de value"""
    if not odds or odds <= 1:
        return "N/A"
    
    implied = 100 / odds
    edge = score - implied
    
    if edge >= 15:
        return "💎 DIAMOND VALUE"
    elif edge >= 10:
        return "🔥 STRONG VALUE"
    elif edge >= 5:
        return "✅ VALUE"
    elif edge >= 0:
        return "⚖️ FAIR"
    else:
        return "❌ AVOID"


def calculate_kelly(prob: float, odds: float) -> float:
    """Kelly Criterion"""
    if not odds or odds <= 1 or prob <= 0:
        return 0.0
    
    p = prob / 100
    b = odds - 1
    q = 1 - p
    
    kelly = (b * p - q) / b
    kelly *= 0.25  # Fractional Kelly
    
    return max(0, min(10, kelly * 100))


def log_prediction(match_id: str, home_team: str, away_team: str,
                   market: str, score: float, probability: float,
                   recommendation: str, confidence: str, value_rating: str,
                   kelly: float, factors: dict, reasoning: str):
    """Log prédiction pour CLV tracking"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO market_predictions 
            (match_id, home_team, away_team, market, predicted_score, 
             predicted_probability, recommendation, confidence, value_rating,
             kelly_pct, factors, reasoning)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (
            match_id, home_team, away_team, market,
            score, probability, recommendation, confidence,
            value_rating, kelly, json.dumps(factors), reasoning
        ))
        
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Log error: {e}")


# ============================================================
# ENDPOINTS
# ============================================================

@router.get("/health")
async def patron_diamond_health():
    """Vérifie le statut du Patron Diamond V3"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM team_statistics_live")
        teams_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM team_head_to_head")
        h2h_count = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM match_results WHERE is_finished = true")
        matches_count = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return {
            "status": "operational",
            "version": "3.0.0",
            "name": "Patron Diamond+ V3",
            "features": ["Poisson Model", "BTTS", "Over 2.5", "Kelly", "Value Detection"],
            "data": {
                "teams": teams_count,
                "h2h_pairs": h2h_count,
                "matches": matches_count
            }
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/analyze/{match_id}")
async def analyze_match_diamond(
    match_id: str,
    odds_btts: float = None,
    odds_over25: float = None
):
    """
    Analyse complète d'un match avec Patron Diamond V3
    
    - Modèle Poisson pour probabilités exactes
    - Analyse BTTS et Over 2.5
    - Value Bet detection
    - Kelly Criterion
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Récupérer info match
        cur.execute("""
            SELECT DISTINCT match_id, home_team, away_team, sport, commence_time
            FROM odds_history WHERE match_id = %s LIMIT 1
        """, (match_id,))
        
        match_row = cur.fetchone()
        if not match_row:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail=f"Match {match_id} not found")
        
        home_team = match_row['home_team']
        away_team = match_row['away_team']
        
        cur.close()
        conn.close()
        
        # Récupérer stats équipes
        home_stats = get_team_stats(home_team)
        away_stats = get_team_stats(away_team)
        h2h = get_h2h_stats(home_team, away_team)
        
        # Calculer xG
        home_xg = 1.5
        away_xg = 1.2
        
        if home_stats and away_stats:
            home_scored = safe_float(home_stats.get('home_avg_scored'), 1.5)
            away_conceded = safe_float(away_stats.get('away_avg_conceded'), 1.5)
            home_xg = (home_scored + away_conceded) / 2 * 1.15
            
            away_scored = safe_float(away_stats.get('away_avg_scored'), 1.2)
            home_conceded = safe_float(home_stats.get('home_avg_conceded'), 1.2)
            away_xg = (away_scored + home_conceded) / 2 / 1.15
        
        home_xg = max(0.5, min(4.0, home_xg))
        away_xg = max(0.3, min(3.5, away_xg))
        total_xg = home_xg + away_xg
        
        # Poisson
        poisson = calculate_poisson(home_xg, away_xg)
        
        # ========== BTTS ANALYSIS ==========
        btts_factors = {'poisson': poisson['btts_prob']}
        btts_score = poisson['btts_prob'] * 0.35  # Poisson 35%
        
        if home_stats and away_stats:
            home_btts = safe_float(home_stats.get('btts_pct'), 50)
            away_btts = safe_float(away_stats.get('btts_pct'), 50)
            global_btts = (home_btts + away_btts) / 2
            btts_factors['stats_global'] = global_btts
            btts_score += global_btts * 0.25
            
            home_l5 = safe_float(home_stats.get('last5_btts_pct'), 50)
            away_l5 = safe_float(away_stats.get('last5_btts_pct'), 50)
            l5_btts = (home_l5 + away_l5) / 2
            btts_factors['form_l5'] = l5_btts
            btts_score += l5_btts * 0.15
            
            # Pénalité clean sheets
            home_cs = safe_float(home_stats.get('home_clean_sheet_pct'), 25)
            away_cs = safe_float(away_stats.get('away_clean_sheet_pct'), 20)
            cs_penalty = (home_cs + away_cs) / 8
            btts_factors['cs_penalty'] = cs_penalty
            btts_score -= cs_penalty
        else:
            btts_score += 50 * 0.40
        
        if h2h:
            h2h_btts = safe_float(h2h.get('btts_pct'), 50)
            btts_factors['h2h'] = h2h_btts
            btts_score += h2h_btts * 0.25
        else:
            btts_score += 50 * 0.25
        
        btts_score = max(0, min(100, btts_score))
        
        # Confidence BTTS
        btts_confidence = 30
        if home_stats: btts_confidence += 25
        if away_stats: btts_confidence += 25
        if h2h: btts_confidence += 20
        
        btts_recommendation = get_recommendation(btts_score, btts_confidence)
        btts_value = get_value_rating(btts_score, odds_btts) if odds_btts else "N/A"
        btts_kelly = calculate_kelly(btts_score, odds_btts) if odds_btts else 0
        
        btts_reasoning = f"BTTS {'probable' if btts_score >= 55 else 'incertain'} ({btts_score:.0f}%). "
        btts_reasoning += f"Poisson: {poisson['btts_prob']}%. "
        if home_stats:
            btts_reasoning += f"Stats: {btts_factors.get('stats_global', 50):.0f}%."
        
        # ========== OVER 2.5 ANALYSIS ==========
        over_factors = {'poisson': poisson['over25_prob'], 'xg_total': total_xg}
        over_score = poisson['over25_prob'] * 0.40  # Poisson 40%
        
        # xG factor
        xg_factor = min(100, max(0, (total_xg - 2.5) * 40 + 50))
        over_factors['xg_factor'] = xg_factor
        over_score += xg_factor * 0.20
        
        if home_stats and away_stats:
            home_over = safe_float(home_stats.get('over_25_pct'), 50)
            away_over = safe_float(away_stats.get('over_25_pct'), 50)
            global_over = (home_over + away_over) / 2
            over_factors['stats_global'] = global_over
            over_score += global_over * 0.15
            
            home_l5 = safe_float(home_stats.get('last5_over25_pct'), 50)
            away_l5 = safe_float(away_stats.get('last5_over25_pct'), 50)
            l5_over = (home_l5 + away_l5) / 2
            over_factors['form_l5'] = l5_over
            over_score += l5_over * 0.10
        else:
            over_score += 50 * 0.25
        
        if h2h:
            h2h_over = safe_float(h2h.get('over_25_pct'), 50)
            over_factors['h2h'] = h2h_over
            over_score += h2h_over * 0.15
        else:
            over_score += 50 * 0.15
        
        over_score = max(0, min(100, over_score))
        
        # Confidence Over
        over_confidence = 30
        if home_stats: over_confidence += 25
        if away_stats: over_confidence += 25
        if h2h: over_confidence += 20
        
        over_recommendation = get_recommendation(over_score, over_confidence)
        over_value = get_value_rating(over_score, odds_over25) if odds_over25 else "N/A"
        over_kelly = calculate_kelly(over_score, odds_over25) if odds_over25 else 0
        
        over_reasoning = f"Over 2.5 {'probable' if over_score >= 55 else 'incertain'} ({over_score:.0f}%). "
        over_reasoning += f"xG: {total_xg:.2f}, Poisson: {poisson['over25_prob']}%."

        # ========== BTTS NO ANALYSIS ==========
        btts_no_score = 100 - btts_score
        btts_no_recommendation = get_recommendation(btts_no_score, btts_confidence)
        btts_no_value = "N/A"  # Odds à ajouter plus tard
        btts_no_kelly = 0
        btts_no_reasoning = f"BTTS No {'probable' if btts_no_score >= 55 else 'incertain'} ({btts_no_score:.0f}%). Inverse de BTTS Yes."

        # ========== UNDER 2.5 ANALYSIS ==========
        under25_score = 100 - over_score
        under25_recommendation = get_recommendation(under25_score, over_confidence)
        under25_value = "N/A"
        under25_kelly = 0
        under25_reasoning = f"Under 2.5 {'probable' if under25_score >= 55 else 'incertain'} ({under25_score:.0f}%). xG: {total_xg:.2f}."

        # ========== DOUBLE CHANCE ANALYSIS ==========
        dc_1x_score = poisson['double_chance']['1x']
        dc_x2_score = poisson['double_chance']['x2']
        dc_12_score = poisson['double_chance']['12']
        
        dc_confidence = 40
        if home_stats: dc_confidence += 20
        if away_stats: dc_confidence += 20
        if h2h: dc_confidence += 20

        dc_1x_recommendation = get_recommendation(dc_1x_score, dc_confidence)
        dc_x2_recommendation = get_recommendation(dc_x2_score, dc_confidence)
        dc_12_recommendation = get_recommendation(dc_12_score, dc_confidence)

        # ========== DRAW NO BET ANALYSIS ==========
        dnb_home_score = poisson['draw_no_bet']['home']
        dnb_away_score = poisson['draw_no_bet']['away']
        
        dnb_home_recommendation = get_recommendation(dnb_home_score, dc_confidence)
        dnb_away_recommendation = get_recommendation(dnb_away_score, dc_confidence)

        
        # ========== PATRON SCORE ==========
        patron_score = (btts_score + over_score) / 2
        
        max_score = max(btts_score, over_score)
        if max_score >= 70:
            match_interest = "💎 DIAMOND MATCH"
        elif max_score >= 60:
            match_interest = "🔥 HIGH INTEREST"
        elif max_score >= 50:
            match_interest = "📈 MEDIUM INTEREST"
        else:
            match_interest = "📊 LOW INTEREST"
        
        # Log predictions
        log_prediction(match_id, home_team, away_team, 'btts',
                      btts_score, poisson['btts_prob'], btts_recommendation,
                      str(btts_confidence), btts_value, btts_kelly,
                      btts_factors, btts_reasoning)
        
        log_prediction(match_id, home_team, away_team, 'over25',
                      over_score, poisson['over25_prob'], over_recommendation,
                      str(over_confidence), over_value, over_kelly,
                      over_factors, over_reasoning)
        
        return {
            "match_id": match_id,
            "home_team": home_team,
            "away_team": away_team,
            
            "poisson": {
                "home_xg": round(home_xg, 2),
                "away_xg": round(away_xg, 2),
                "total_xg": round(total_xg, 2),
                "btts_prob": poisson['btts_prob'],
                "over25_prob": poisson['over25_prob'],
                "over15_prob": poisson['over15_prob'],
                "over35_prob": poisson['over35_prob'],
                "1x2": poisson['1x2'],
                "most_likely_scores": poisson['most_likely_scores'],
                "btts_no_prob": poisson['btts_no_prob'],
                "under15_prob": poisson['under15_prob'],
                "under25_prob": poisson['under25_prob'],
                "under35_prob": poisson['under35_prob'],
                "double_chance": poisson['double_chance'],
                "draw_no_bet": poisson['draw_no_bet']
            },
            
            "btts": {
                "score": round(btts_score, 1),
                "probability": poisson['btts_prob'],
                "recommendation": btts_recommendation,
                "confidence": btts_confidence,
                "value_rating": btts_value,
                "kelly_pct": round(btts_kelly, 2),
                "factors": {k: round(v, 1) if isinstance(v, float) else v 
                           for k, v in btts_factors.items()},
                "reasoning": btts_reasoning
            },
            
            "over25": {
                "score": round(over_score, 1),
                "probability": poisson['over25_prob'],
                "expected_goals": round(total_xg, 2),
                "recommendation": over_recommendation,
                "confidence": over_confidence,
                "value_rating": over_value,
                "kelly_pct": round(over_kelly, 2),
                "factors": {k: round(v, 1) if isinstance(v, float) else v 
                           for k, v in over_factors.items()},
                "reasoning": over_reasoning
            },
            "btts_no": {
                "score": round(btts_no_score, 1),
                "probability": poisson['btts_no_prob'],
                "recommendation": btts_no_recommendation,
                "confidence": btts_confidence,
                "reasoning": btts_no_reasoning
            },
            "under25": {
                "score": round(under25_score, 1),
                "probability": poisson['under25_prob'],
                "recommendation": under25_recommendation,
                "confidence": over_confidence,
                "reasoning": under25_reasoning
            },
            "double_chance": {
                "1x": {
                    "score": round(dc_1x_score, 1),
                    "recommendation": dc_1x_recommendation,
                    "confidence": dc_confidence
                },
                "x2": {
                    "score": round(dc_x2_score, 1),
                    "recommendation": dc_x2_recommendation,
                    "confidence": dc_confidence
                },
                "12": {
                    "score": round(dc_12_score, 1),
                    "recommendation": dc_12_recommendation,
                    "confidence": dc_confidence
                }
            },
            "draw_no_bet": {
                "home": {
                    "score": round(dnb_home_score, 1),
                    "recommendation": dnb_home_recommendation,
                    "confidence": dc_confidence
                },
                "away": {
                    "score": round(dnb_away_score, 1),
                    "recommendation": dnb_away_recommendation,
                    "confidence": dc_confidence
                }
            },
            
            "patron": {
                "score": round(patron_score, 1),
                "match_interest": match_interest,
                "data_quality": {
                    "home_stats": home_stats is not None,
                    "away_stats": away_stats is not None,
                    "h2h": h2h is not None
                }
            },
            
            "generated_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/predict-teams")
async def predict_by_teams(
    home_team: str,
    away_team: str,
    odds_btts: float = None,
    odds_over25: float = None
):
    """
    Analyse directe par noms d'équipes (sans match_id)
    Utile pour les matchs à venir
    """
    # Générer un match_id temporaire
    match_id = f"direct_{home_team[:3]}_{away_team[:3]}_{datetime.now().strftime('%Y%m%d')}"
    
    # Réutiliser la logique
    home_stats = get_team_stats(home_team)
    away_stats = get_team_stats(away_team)
    h2h = get_h2h_stats(home_team, away_team)
    
    if not home_stats and not away_stats:
        raise HTTPException(status_code=404, 
                          detail=f"Teams not found: {home_team}, {away_team}")
    
    # Calculer xG
    home_xg = 1.5
    away_xg = 1.2
    
    if home_stats and away_stats:
        home_scored = safe_float(home_stats.get('home_avg_scored'), 1.5)
        away_conceded = safe_float(away_stats.get('away_avg_conceded'), 1.5)
        home_xg = (home_scored + away_conceded) / 2 * 1.15
        
        away_scored = safe_float(away_stats.get('away_avg_scored'), 1.2)
        home_conceded = safe_float(home_stats.get('home_avg_conceded'), 1.2)
        away_xg = (away_scored + home_conceded) / 2 / 1.15
    
    home_xg = max(0.5, min(4.0, home_xg))
    away_xg = max(0.3, min(3.5, away_xg))
    
    poisson = calculate_poisson(home_xg, away_xg)
    
    # BTTS Score
    btts_score = poisson['btts_prob'] * 0.35
    if home_stats and away_stats:
        global_btts = (safe_float(home_stats.get('btts_pct'), 50) + 
                      safe_float(away_stats.get('btts_pct'), 50)) / 2
        btts_score += global_btts * 0.40
    else:
        btts_score += 50 * 0.40
    
    if h2h:
        btts_score += safe_float(h2h.get('btts_pct'), 50) * 0.25
    else:
        btts_score += 50 * 0.25
    
    btts_score = max(0, min(100, btts_score))
    
    # Over Score
    over_score = poisson['over25_prob'] * 0.40
    xg_factor = min(100, max(0, (home_xg + away_xg - 2.5) * 40 + 50))
    over_score += xg_factor * 0.20
    
    if home_stats and away_stats:
        global_over = (safe_float(home_stats.get('over_25_pct'), 50) + 
                      safe_float(away_stats.get('over_25_pct'), 50)) / 2
        over_score += global_over * 0.25
    else:
        over_score += 50 * 0.25
    
    if h2h:
        over_score += safe_float(h2h.get('over_25_pct'), 50) * 0.15
    else:
        over_score += 50 * 0.15
    
    over_score = max(0, min(100, over_score))
    
    return {
        "home_team": home_team,
        "away_team": away_team,
        "poisson": {
            "home_xg": round(home_xg, 2),
            "away_xg": round(away_xg, 2),
            "total_xg": round(home_xg + away_xg, 2),
            "btts_prob": poisson['btts_prob'],
            "over25_prob": poisson['over25_prob'],
            "1x2": poisson['1x2'],
            "most_likely_scores": poisson['most_likely_scores'],
                "btts_no_prob": poisson['btts_no_prob'],
                "under15_prob": poisson['under15_prob'],
                "under25_prob": poisson['under25_prob'],
                "under35_prob": poisson['under35_prob'],
                "double_chance": poisson['double_chance'],
                "draw_no_bet": poisson['draw_no_bet'][:3]
        },
        "btts": {
            "score": round(btts_score, 1),
            "recommendation": get_recommendation(btts_score, 70),
            "value_rating": get_value_rating(btts_score, odds_btts) if odds_btts else "N/A"
        },
        "over25": {
            "score": round(over_score, 1),
            "recommendation": get_recommendation(over_score, 70),
            "value_rating": get_value_rating(over_score, odds_over25) if odds_over25 else "N/A"
        },
        "data_available": {
            "home_stats": home_stats is not None,
            "away_stats": away_stats is not None,
            "h2h": h2h is not None
        }
    }


@router.get("/top-predictions")
async def get_top_predictions(
    market: str = "all",
    min_score: float = 60,
    limit: int = 10
):
    """
    Récupère les meilleures prédictions loggées
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT * FROM market_predictions 
            WHERE predicted_score >= %s
            AND status = 'pending'
        """
        params = [min_score]
        
        if market != "all":
            query += " AND market = %s"
            params.append(market)
        
        query += " ORDER BY predicted_score DESC LIMIT %s"
        params.append(limit)
        
        cur.execute(query, params)
        results = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return {
            "count": len(results),
            "predictions": results
        }
    except Exception as e:
        return {"error": str(e)}
