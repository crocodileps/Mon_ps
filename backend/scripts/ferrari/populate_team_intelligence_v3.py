#!/usr/bin/env python3
"""
🏎️ FERRARI 2.0 ULTIMATE - Agent Spécialisé SYSTÈME V3
Version: INTELLIGENT avec gestion complète des mappings
Date: 28 Nov 2025

PRINCIPE FONDAMENTAL:
- Utilise les noms de match_results comme SOURCE
- Convertit vers noms canoniques pour STOCKAGE
- JAMAIS de données inventées
- Minimum 3 matchs pour fiabilité

FLUX:
1. Lire équipes depuis match_results (noms originaux)
2. Calculer VRAIES stats depuis match_results
3. Convertir nom vers canonique via team_name_mapping
4. Stocker avec nom canonique dans team_intelligence
"""

import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging
from decimal import Decimal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/ferrari/ferrari_populate_v3.log')
    ]
)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "monps_db"),
    "user": os.getenv("DB_USER", "monps_user"),
    "password": os.getenv("DB_PASSWORD", "monps_secure_password_2024"),
    "port": 5432
}

# ══════════════════════════════════════════════════════════════
# SEUILS PROFESSIONNELS POUR TAGS
# ══════════════════════════════════════════════════════════════

TAG_RULES = {
    "roi_nuls": {"field": "draw_rate", "op": ">=", "val": 30},
    "peu_nuls": {"field": "draw_rate", "op": "<=", "val": 12},
    "high_scoring": {"field": "avg_goals_total", "op": ">=", "val": 3.0},
    "low_scoring": {"field": "avg_goals_total", "op": "<=", "val": 2.0},
    "offensif": {"field": "avg_goals_scored", "op": ">=", "val": 1.8},
    "defensif": {"field": "avg_goals_conceded", "op": "<=", "val": 0.9},
    "btts_friendly": {"field": "btts_rate", "op": ">=", "val": 55},
    "btts_killer": {"field": "btts_rate", "op": "<=", "val": 35},
    "clean_sheet_kings": {"field": "clean_sheet_rate", "op": ">=", "val": 35},
    "fortress_home": {"field": "home_win_rate", "op": ">=", "val": 60},
    "weak_home": {"field": "home_win_rate", "op": "<=", "val": 25},
    "road_warriors": {"field": "away_win_rate", "op": ">=", "val": 40},
    "weak_away": {"field": "away_win_rate", "op": "<=", "val": 12},
}

# ══════════════════════════════════════════════════════════════
# RÈGLES ALERTES MARCHÉ
# ══════════════════════════════════════════════════════════════

ALERT_RULES = {
    "dc_12": [
        {"field": "home_draw_rate", "op": ">=", "val": 35, "level": "TRAP", 
         "msg": "{val:.0f}% nuls domicile", "alt": "dc_1x"},
        {"field": "home_draw_rate", "op": ">=", "val": 25, "level": "CAUTION",
         "msg": "{val:.0f}% nuls domicile", "alt": "dc_1x"},
    ],
    "btts_yes": [
        {"field": "btts_rate", "op": "<=", "val": 35, "level": "TRAP",
         "msg": "Seulement {val:.0f}% BTTS", "alt": "btts_no"},
        {"field": "clean_sheet_rate", "op": ">=", "val": 40, "level": "CAUTION",
         "msg": "{val:.0f}% clean sheets", "alt": "btts_no"},
    ],
    "btts_no": [
        {"field": "btts_rate", "op": ">=", "val": 65, "level": "TRAP",
         "msg": "{val:.0f}% BTTS", "alt": "btts_yes"},
    ],
    "over_25": [
        {"field": "avg_goals_total", "op": "<=", "val": 2.0, "level": "TRAP",
         "msg": "Moyenne {val:.1f} buts", "alt": "under_25"},
        {"field": "over_25_rate", "op": "<=", "val": 35, "level": "CAUTION",
         "msg": "{val:.0f}% Over 2.5", "alt": "under_25"},
    ],
    "under_25": [
        {"field": "avg_goals_total", "op": ">=", "val": 3.5, "level": "TRAP",
         "msg": "Moyenne {val:.1f} buts", "alt": "over_25"},
    ],
    "home": [
        {"field": "home_win_rate", "op": "<=", "val": 25, "level": "CAUTION",
         "msg": "{val:.0f}% victoires dom", "alt": "dc_1x"},
    ],
    "away": [
        {"field": "away_win_rate", "op": "<=", "val": 15, "level": "TRAP",
         "msg": "{val:.0f}% victoires ext", "alt": "draw"},
    ],
}


def get_db():
    return psycopg2.connect(**DB_CONFIG)


def safe_div(a, b):
    """Division sécurisée"""
    if not b or b == 0:
        return None
    return round(a / b, 2)


def safe_pct(a, b):
    """Pourcentage sécurisé"""
    if not b or b == 0:
        return None
    return round((a / b) * 100, 2)


# ══════════════════════════════════════════════════════════════
# CALCUL DES VRAIES STATS
# ══════════════════════════════════════════════════════════════

def get_team_real_stats(conn, team_name: str) -> Optional[Dict]:
    """
    Calcule les VRAIES stats depuis match_results
    Recherche par nom EXACT dans match_results
    """
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Stats DOMICILE
    cur.execute("""
        SELECT 
            COUNT(*) as m,
            COALESCE(SUM(CASE WHEN score_home > score_away THEN 1 ELSE 0 END), 0) as w,
            COALESCE(SUM(CASE WHEN score_home = score_away THEN 1 ELSE 0 END), 0) as d,
            COALESCE(SUM(CASE WHEN score_home < score_away THEN 1 ELSE 0 END), 0) as l,
            COALESCE(SUM(score_home), 0) as gf,
            COALESCE(SUM(score_away), 0) as ga,
            COALESCE(SUM(CASE WHEN score_home > 0 AND score_away > 0 THEN 1 ELSE 0 END), 0) as btts,
            COALESCE(SUM(CASE WHEN score_away = 0 THEN 1 ELSE 0 END), 0) as cs,
            COALESCE(SUM(CASE WHEN score_home + score_away > 2 THEN 1 ELSE 0 END), 0) as o25
        FROM match_results
        WHERE home_team = %s AND is_finished = true
    """, (team_name,))
    h = dict(cur.fetchone())
    
    # Stats EXTÉRIEUR
    cur.execute("""
        SELECT 
            COUNT(*) as m,
            COALESCE(SUM(CASE WHEN score_away > score_home THEN 1 ELSE 0 END), 0) as w,
            COALESCE(SUM(CASE WHEN score_home = score_away THEN 1 ELSE 0 END), 0) as d,
            COALESCE(SUM(CASE WHEN score_away < score_home THEN 1 ELSE 0 END), 0) as l,
            COALESCE(SUM(score_away), 0) as gf,
            COALESCE(SUM(score_home), 0) as ga,
            COALESCE(SUM(CASE WHEN score_home > 0 AND score_away > 0 THEN 1 ELSE 0 END), 0) as btts,
            COALESCE(SUM(CASE WHEN score_home = 0 THEN 1 ELSE 0 END), 0) as cs,
            COALESCE(SUM(CASE WHEN score_home + score_away > 2 THEN 1 ELSE 0 END), 0) as o25
        FROM match_results
        WHERE away_team = %s AND is_finished = true
    """, (team_name,))
    a = dict(cur.fetchone())
    
    total_m = h['m'] + a['m']
    if total_m == 0:
        return None
    
    # Calculs globaux
    total_w = h['w'] + a['w']
    total_d = h['d'] + a['d']
    total_l = h['l'] + a['l']
    total_gf = h['gf'] + a['gf']
    total_ga = h['ga'] + a['ga']
    total_btts = h['btts'] + a['btts']
    total_cs = h['cs'] + a['cs']
    total_o25 = h['o25'] + a['o25']
    
    return {
        # Matchs
        "matches_total": total_m,
        "matches_home": h['m'],
        "matches_away": a['m'],
        
        # Globaux
        "win_rate": safe_pct(total_w, total_m),
        "draw_rate": safe_pct(total_d, total_m),
        "loss_rate": safe_pct(total_l, total_m),
        "avg_goals_scored": safe_div(total_gf, total_m),
        "avg_goals_conceded": safe_div(total_ga, total_m),
        "avg_goals_total": safe_div(total_gf + total_ga, total_m),
        "btts_rate": safe_pct(total_btts, total_m),
        "clean_sheet_rate": safe_pct(total_cs, total_m),
        "over_25_rate": safe_pct(total_o25, total_m),
        
        # Domicile
        "home_win_rate": safe_pct(h['w'], h['m']),
        "home_draw_rate": safe_pct(h['d'], h['m']),
        "home_loss_rate": safe_pct(h['l'], h['m']),
        "home_goals_scored_avg": safe_div(h['gf'], h['m']),
        "home_goals_conceded_avg": safe_div(h['ga'], h['m']),
        "home_btts_rate": safe_pct(h['btts'], h['m']),
        "home_clean_sheet_rate": safe_pct(h['cs'], h['m']),
        "home_over_25_rate": safe_pct(h['o25'], h['m']),
        
        # Extérieur
        "away_win_rate": safe_pct(a['w'], a['m']),
        "away_draw_rate": safe_pct(a['d'], a['m']),
        "away_loss_rate": safe_pct(a['l'], a['m']),
        "away_goals_scored_avg": safe_div(a['gf'], a['m']),
        "away_goals_conceded_avg": safe_div(a['ga'], a['m']),
        "away_btts_rate": safe_pct(a['btts'], a['m']),
        "away_clean_sheet_rate": safe_pct(a['cs'], a['m']),
        "away_over_25_rate": safe_pct(a['o25'], a['m']),
    }


# ══════════════════════════════════════════════════════════════
# GÉNÉRATION TAGS ET ALERTES
# ══════════════════════════════════════════════════════════════

def generate_tags(stats: Dict) -> List[str]:
    """Génère tags basés sur VRAIES stats"""
    if not stats:
        return []
    
    tags = []
    for tag, rule in TAG_RULES.items():
        val = stats.get(rule["field"])
        if val is None:
            continue
        
        op = rule["op"]
        threshold = rule["val"]
        
        if op == ">=" and val >= threshold:
            tags.append(tag)
        elif op == "<=" and val <= threshold:
            tags.append(tag)
    
    return tags


def generate_alerts(stats: Dict) -> Dict:
    """Génère alertes basées sur VRAIES stats"""
    if not stats:
        return {}
    
    alerts = {}
    for market, rules in ALERT_RULES.items():
        for rule in rules:
            val = stats.get(rule["field"])
            if val is None:
                continue
            
            op = rule["op"]
            threshold = rule["val"]
            triggered = False
            
            if op == ">=" and val >= threshold:
                triggered = True
            elif op == "<=" and val <= threshold:
                triggered = True
            
            if triggered:
                alerts[market] = {
                    "level": rule["level"],
                    "reason": rule["msg"].format(val=val),
                    "alternative": rule.get("alt"),
                    "value": round(val, 1),
                    "threshold": threshold
                }
                break
    
    return alerts


def calc_style(stats: Dict) -> Tuple[str, int]:
    """Calcule style depuis vraies stats"""
    if not stats:
        return ("unknown", 50)
    
    gs = stats.get("avg_goals_scored") or 1.0
    gc = stats.get("avg_goals_conceded") or 1.0
    
    diff = gs - gc
    score = int(50 + (diff * 25))
    score = max(0, min(100, score))
    
    if score <= 35:
        return ("defensive", score)
    elif score <= 45:
        return ("balanced_defensive", score)
    elif score <= 55:
        return ("balanced", score)
    elif score <= 65:
        return ("balanced_offensive", score)
    else:
        return ("offensive", score)


def calc_profile(stats: Dict, loc: str) -> str:
    """Calcule profil dom/ext"""
    if not stats:
        return "unknown"
    
    if loc == "home":
        wr = stats.get("home_win_rate") or 40
        dr = stats.get("home_draw_rate") or 25
        if wr >= 60:
            return "fortress"
        elif dr >= 35:
            return "draw_king"
        elif wr <= 25:
            return "weak_home"
        return "balanced"
    else:
        wr = stats.get("away_win_rate") or 25
        if wr >= 40:
            return "road_warriors"
        elif wr <= 12:
            return "weak_travelers"
        return "balanced"


def calc_tendencies(stats: Dict) -> Dict:
    """Calcule scores de tendance 0-100"""
    if not stats:
        return {}
    
    return {
        "draw_tendency": min(100, int((stats.get("draw_rate") or 25) * 2.5)),
        "btts_tendency": min(100, int(stats.get("btts_rate") or 50)),
        "goals_tendency": min(100, int(((stats.get("avg_goals_total") or 2.5) / 4) * 100)),
        "clean_sheet_tendency": min(100, int((stats.get("clean_sheet_rate") or 25) * 2.5)),
    }


# ══════════════════════════════════════════════════════════════
# MAPPING DES NOMS
# ══════════════════════════════════════════════════════════════

def get_canonical(conn, source_name: str) -> str:
    """Récupère nom canonique depuis mapping"""
    cur = conn.cursor()
    cur.execute("""
        SELECT canonical_name FROM team_name_mapping
        WHERE source_name = %s AND source_table = 'match_results'
    """, (source_name,))
    
    res = cur.fetchone()
    return res[0] if res else source_name


# ══════════════════════════════════════════════════════════════
# INSERTION
# ══════════════════════════════════════════════════════════════

def upsert_team(conn, data: Dict) -> bool:
    """Insert/Update team_intelligence"""
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO team_intelligence (
                team_name, team_name_normalized,
                current_style, current_style_score, season_style, season_style_score,
                home_strength, home_win_rate, home_draw_rate, home_loss_rate,
                home_goals_scored_avg, home_goals_conceded_avg,
                home_btts_rate, home_over25_rate, home_clean_sheet_rate, home_profile,
                away_strength, away_win_rate, away_draw_rate, away_loss_rate,
                away_goals_scored_avg, away_goals_conceded_avg,
                away_btts_rate, away_over25_rate, away_clean_sheet_rate, away_profile,
                draw_tendency, goals_tendency, btts_tendency, clean_sheet_tendency,
                tags, market_alerts,
                matches_analyzed, is_reliable, data_quality_score, confidence_overall,
                data_sources, last_computed_at, updated_at
            ) VALUES (
                %(team_name)s, %(normalized)s,
                %(style)s, %(style_score)s, %(style)s, %(style_score)s,
                %(home_strength)s, %(home_win_rate)s, %(home_draw_rate)s, %(home_loss_rate)s,
                %(home_gf)s, %(home_ga)s,
                %(home_btts)s, %(home_o25)s, %(home_cs)s, %(home_profile)s,
                %(away_strength)s, %(away_win_rate)s, %(away_draw_rate)s, %(away_loss_rate)s,
                %(away_gf)s, %(away_ga)s,
                %(away_btts)s, %(away_o25)s, %(away_cs)s, %(away_profile)s,
                %(draw_t)s, %(goals_t)s, %(btts_t)s, %(cs_t)s,
                %(tags)s, %(alerts)s,
                %(matches)s, %(reliable)s, %(quality)s, %(confidence)s,
                %(sources)s, NOW(), NOW()
            )
            ON CONFLICT (team_name) DO UPDATE SET
                team_name_normalized = EXCLUDED.team_name_normalized,
                current_style = EXCLUDED.current_style,
                current_style_score = EXCLUDED.current_style_score,
                season_style = EXCLUDED.season_style,
                season_style_score = EXCLUDED.season_style_score,
                home_strength = EXCLUDED.home_strength,
                home_win_rate = EXCLUDED.home_win_rate,
                home_draw_rate = EXCLUDED.home_draw_rate,
                home_loss_rate = EXCLUDED.home_loss_rate,
                home_goals_scored_avg = EXCLUDED.home_goals_scored_avg,
                home_goals_conceded_avg = EXCLUDED.home_goals_conceded_avg,
                home_btts_rate = EXCLUDED.home_btts_rate,
                home_over25_rate = EXCLUDED.home_over25_rate,
                home_clean_sheet_rate = EXCLUDED.home_clean_sheet_rate,
                home_profile = EXCLUDED.home_profile,
                away_strength = EXCLUDED.away_strength,
                away_win_rate = EXCLUDED.away_win_rate,
                away_draw_rate = EXCLUDED.away_draw_rate,
                away_loss_rate = EXCLUDED.away_loss_rate,
                away_goals_scored_avg = EXCLUDED.away_goals_scored_avg,
                away_goals_conceded_avg = EXCLUDED.away_goals_conceded_avg,
                away_btts_rate = EXCLUDED.away_btts_rate,
                away_over25_rate = EXCLUDED.away_over25_rate,
                away_clean_sheet_rate = EXCLUDED.away_clean_sheet_rate,
                away_profile = EXCLUDED.away_profile,
                draw_tendency = EXCLUDED.draw_tendency,
                goals_tendency = EXCLUDED.goals_tendency,
                btts_tendency = EXCLUDED.btts_tendency,
                clean_sheet_tendency = EXCLUDED.clean_sheet_tendency,
                tags = EXCLUDED.tags,
                market_alerts = EXCLUDED.market_alerts,
                matches_analyzed = EXCLUDED.matches_analyzed,
                is_reliable = EXCLUDED.is_reliable,
                data_quality_score = EXCLUDED.data_quality_score,
                confidence_overall = EXCLUDED.confidence_overall,
                data_sources = EXCLUDED.data_sources,
                last_computed_at = NOW(),
                updated_at = NOW()
        """, data)
        return True
    except Exception as e:
        logger.error(f"❌ Insert error {data.get('team_name')}: {e}")
        return False


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def run(min_matches: int = 3):
    """
    Agent Spécialisé SYSTÈME - Peuplement INTELLIGENT
    """
    logger.info("🏎️ FERRARI V3 - Agent Spécialisé SYSTÈME")
    logger.info("=" * 60)
    logger.info(f"📊 Source: match_results (VRAIES données)")
    logger.info(f"📊 Min matchs: {min_matches}")
    logger.info("=" * 60)
    
    conn = get_db()
    cur = conn.cursor()
    
    # 1. Équipes uniques depuis match_results
    cur.execute("""
        SELECT DISTINCT team FROM (
            SELECT home_team as team FROM match_results WHERE is_finished = true
            UNION
            SELECT away_team as team FROM match_results WHERE is_finished = true
        ) t WHERE team IS NOT NULL
    """)
    teams = [r[0] for r in cur.fetchall()]
    
    logger.info(f"📊 {len(teams)} équipes dans match_results")
    
    ok = skip = err = 0
    
    for i, team in enumerate(teams):
        try:
            # 2. Stats VRAIES
            stats = get_team_real_stats(conn, team)
            
            if not stats or stats["matches_total"] < min_matches:
                skip += 1
                continue
            
            # 3. Nom canonique
            canonical = get_canonical(conn, team)
            
            # 4. Tags et alertes
            tags = generate_tags(stats)
            alerts = generate_alerts(stats)
            
            # 5. Style et profils
            style, style_score = calc_style(stats)
            home_profile = calc_profile(stats, "home")
            away_profile = calc_profile(stats, "away")
            tendencies = calc_tendencies(stats)
            
            # 6. Qualité
            m = stats["matches_total"]
            reliable = m >= min_matches
            quality = min(100, m * 7)
            confidence = min(100, m * 5)
            
            # 7. Data
            data = {
                "team_name": canonical,
                "normalized": canonical.lower().replace(" ", "_"),
                "style": style,
                "style_score": style_score,
                "home_strength": int(stats.get("home_win_rate") or 50),
                "home_win_rate": stats.get("home_win_rate"),
                "home_draw_rate": stats.get("home_draw_rate"),
                "home_loss_rate": stats.get("home_loss_rate"),
                "home_gf": stats.get("home_goals_scored_avg"),
                "home_ga": stats.get("home_goals_conceded_avg"),
                "home_btts": stats.get("home_btts_rate"),
                "home_o25": stats.get("home_over_25_rate"),
                "home_cs": stats.get("home_clean_sheet_rate"),
                "home_profile": home_profile,
                "away_strength": int(stats.get("away_win_rate") or 30),
                "away_win_rate": stats.get("away_win_rate"),
                "away_draw_rate": stats.get("away_draw_rate"),
                "away_loss_rate": stats.get("away_loss_rate"),
                "away_gf": stats.get("away_goals_scored_avg"),
                "away_ga": stats.get("away_goals_conceded_avg"),
                "away_btts": stats.get("away_btts_rate"),
                "away_o25": stats.get("away_over_25_rate"),
                "away_cs": stats.get("away_clean_sheet_rate"),
                "away_profile": away_profile,
                "draw_t": tendencies.get("draw_tendency", 50),
                "goals_t": tendencies.get("goals_tendency", 50),
                "btts_t": tendencies.get("btts_tendency", 50),
                "cs_t": tendencies.get("clean_sheet_tendency", 50),
                "tags": json.dumps(tags),
                "alerts": json.dumps(alerts),
                "matches": m,
                "reliable": reliable,
                "quality": quality,
                "confidence": confidence,
                "sources": json.dumps(["match_results"])
            }
            
            if upsert_team(conn, data):
                ok += 1
                if (i + 1) % 25 == 0:
                    logger.info(f"  ✅ {i+1}/{len(teams)}...")
                    conn.commit()
            else:
                err += 1
                
        except Exception as e:
            logger.error(f"❌ {team}: {e}")
            err += 1
    
    conn.commit()
    conn.close()
    
    logger.info("=" * 60)
    logger.info("🏆 TERMINÉ!")
    logger.info(f"  ✅ Succès: {ok}")
    logger.info(f"  ⏭️ Ignorés (<{min_matches} matchs): {skip}")
    logger.info(f"  ❌ Erreurs: {err}")
    logger.info("=" * 60)
    
    return ok


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-matches", type=int, default=3)
    args = parser.parse_args()
    run(min_matches=args.min_matches)
