#!/usr/bin/env python3
"""
🏎️ FERRARI 2.0 - Script de peuplement team_intelligence
Version: ULTIMATE - Optimisation maximale
Date: 28 Nov 2025

STRATÉGIE:
1. Extraire équipes depuis nos tables (GRATUIT)
2. Calculer stats depuis tracking_clv_picks (GRATUIT)
3. Générer tags et alertes automatiquement (GRATUIT)
4. Enrichir via API-Football seulement si nécessaire
"""

import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple
import hashlib

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/home/Mon_ps/logs/ferrari_populate.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuration DB
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "monps_db"),
    "user": os.getenv("DB_USER", "monps_user"),
    "password": os.getenv("DB_PASSWORD", "monps_secure_password_2024"),
    "port": 5432
}

# ══════════════════════════════════════════════════════════════
# RÈGLES INTELLIGENTES POUR TAGS ET ALERTES
# ══════════════════════════════════════════════════════════════

TAG_RULES = {
    # Tag: (condition_field, operator, threshold)
    "roi_nuls": ("draw_tendency", ">=", 65),
    "defensif": ("goals_tendency", "<=", 35),
    "offensif": ("goals_tendency", ">=", 70),
    "btts_killer": ("btts_tendency", "<=", 35),
    "btts_friendly": ("btts_tendency", ">=", 65),
    "fortress_home": ("home_strength", ">=", 75),
    "weak_home": ("home_strength", "<=", 35),
    "road_warriors": ("away_strength", ">=", 60),
    "weak_away": ("away_strength", "<=", 30),
    "high_scoring": ("goals_tendency", ">=", 75),
    "low_scoring": ("goals_tendency", "<=", 30),
    "clean_sheet_kings": ("clean_sheet_tendency", ">=", 60),
}

MARKET_ALERT_RULES = {
    # market_type: [(condition_field, operator, threshold, alert_level, reason_template, alternative)]
    "dc_12": [
        ("home_draw_rate", ">=", 30, "TRAP", "Équipe fait {value}% de nuls à domicile", "dc_1x"),
        ("draw_tendency", ">=", 60, "CAUTION", "Tendance aux nuls élevée ({value}%)", "dc_1x"),
    ],
    "btts_yes": [
        ("btts_tendency", "<=", 35, "TRAP", "Seulement {value}% de BTTS", "btts_no"),
        ("clean_sheet_tendency", ">=", 55, "CAUTION", "Clean sheet fréquent ({value}%)", "btts_no"),
    ],
    "btts_no": [
        ("btts_tendency", ">=", 70, "TRAP", "{value}% de matchs avec BTTS", "btts_yes"),
    ],
    "over_25": [
        ("goals_tendency", "<=", 35, "TRAP", "Équipe peu offensive (score {value})", "under_25"),
    ],
    "under_25": [
        ("goals_tendency", ">=", 70, "TRAP", "Équipe très offensive (score {value})", "over_25"),
    ],
    "home": [
        ("home_strength", "<=", 35, "CAUTION", "Faible à domicile (score {value})", "draw"),
    ],
    "away": [
        ("away_strength", "<=", 30, "TRAP", "Très faible en déplacement (score {value})", "draw"),
    ],
    "draw": [
        ("draw_tendency", "<=", 25, "CAUTION", "Fait peu de nuls ({value}%)", None),
    ],
}

# ══════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ══════════════════════════════════════════════════════════════

def get_db_connection():
    """Connexion à la base de données"""
    return psycopg2.connect(**DB_CONFIG)


def normalize_team_name(name: str) -> str:
    """Normalise le nom d'équipe pour matching"""
    if not name:
        return ""
    return name.lower().strip().replace("fc ", "").replace(" fc", "").replace(".", "").replace("-", " ")


def calculate_tendency_score(rate: float, inverse: bool = False) -> int:
    """Convertit un taux en score 0-100"""
    if rate is None:
        return 50
    score = min(100, max(0, int(rate)))
    return 100 - score if inverse else score


# ══════════════════════════════════════════════════════════════
# EXTRACTION DES ÉQUIPES (GRATUIT)
# ══════════════════════════════════════════════════════════════

def extract_teams_from_odds(conn) -> List[Dict]:
    """Extrait toutes les équipes uniques depuis la table odds"""
    logger.info("�� Extraction des équipes depuis odds...")
    
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Récupérer équipes avec comptage de matchs
    cur.execute("""
        WITH team_matches AS (
            SELECT home_team as team_name, COUNT(*) as home_count, 0 as away_count
            FROM odds
            WHERE home_team IS NOT NULL AND home_team != ''
            GROUP BY home_team
            UNION ALL
            SELECT away_team as team_name, 0 as home_count, COUNT(*) as away_count
            FROM odds
            WHERE away_team IS NOT NULL AND away_team != ''
            GROUP BY away_team
        )
        SELECT 
            team_name,
            SUM(home_count) as home_matches,
            SUM(away_count) as away_matches,
            SUM(home_count + away_count) as total_odds
        FROM team_matches
        GROUP BY team_name
        ORDER BY total_odds DESC
    """)
    
    teams = cur.fetchall()
    logger.info(f"✅ {len(teams)} équipes extraites depuis odds")
    
    return teams


# ══════════════════════════════════════════════════════════════
# CALCUL DES STATS DEPUIS NOS DONNÉES (GRATUIT)
# ══════════════════════════════════════════════════════════════

def calculate_team_stats_from_picks(conn, team_name: str) -> Dict:
    """Calcule les stats d'une équipe depuis tracking_clv_picks"""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Stats quand l'équipe joue à domicile
    cur.execute("""
        SELECT 
            COUNT(*) as total_picks,
            COUNT(*) FILTER (WHERE is_resolved) as resolved,
            COUNT(*) FILTER (WHERE is_winner) as wins,
            COUNT(*) FILTER (WHERE is_resolved AND NOT is_winner) as losses,
            
            -- Stats par marché
            COUNT(*) FILTER (WHERE market_type = 'draw' AND is_winner) as draw_wins,
            COUNT(*) FILTER (WHERE market_type = 'draw') as draw_total,
            COUNT(*) FILTER (WHERE market_type = 'btts_yes' AND is_winner) as btts_yes_wins,
            COUNT(*) FILTER (WHERE market_type = 'btts_yes') as btts_yes_total,
            COUNT(*) FILTER (WHERE market_type = 'btts_no' AND is_winner) as btts_no_wins,
            COUNT(*) FILTER (WHERE market_type = 'btts_no') as btts_no_total,
            COUNT(*) FILTER (WHERE market_type = 'over_25' AND is_winner) as over25_wins,
            COUNT(*) FILTER (WHERE market_type = 'over_25') as over25_total,
            COUNT(*) FILTER (WHERE market_type = 'under_25' AND is_winner) as under25_wins,
            COUNT(*) FILTER (WHERE market_type = 'under_25') as under25_total,
            COUNT(*) FILTER (WHERE market_type = 'home' AND is_winner) as home_wins,
            COUNT(*) FILTER (WHERE market_type = 'home') as home_total,
            COUNT(*) FILTER (WHERE market_type IN ('dc_12', 'dc_1x', 'dc_x2')) as dc_total,
            
            -- Moyennes
            ROUND(AVG(odds_taken)::numeric, 2) as avg_odds,
            ROUND(AVG(clv_percentage)::numeric, 2) as avg_clv,
            ROUND(SUM(COALESCE(profit_loss, 0))::numeric, 2) as total_profit
            
        FROM tracking_clv_picks
        WHERE home_team = %s
    """, (team_name,))
    
    home_stats = cur.fetchone()
    
    # Stats quand l'équipe joue à l'extérieur
    cur.execute("""
        SELECT 
            COUNT(*) as total_picks,
            COUNT(*) FILTER (WHERE is_resolved) as resolved,
            COUNT(*) FILTER (WHERE is_winner) as wins,
            COUNT(*) FILTER (WHERE market_type = 'away' AND is_winner) as away_wins,
            COUNT(*) FILTER (WHERE market_type = 'away') as away_total
        FROM tracking_clv_picks
        WHERE away_team = %s
    """, (team_name,))
    
    away_stats = cur.fetchone()
    
    return {
        "home": home_stats,
        "away": away_stats
    }


def calculate_intelligence_scores(team_stats: Dict) -> Dict:
    """Calcule les scores d'intelligence depuis les stats"""
    home = team_stats.get("home", {}) or {}
    away = team_stats.get("away", {}) or {}
    
    # Calculs sécurisés
    def safe_rate(wins, total):
        if not total or total == 0:
            return None
        return round((wins / total) * 100, 2)
    
    # Draw tendency (basé sur les wins du marché draw)
    draw_wins = (home.get("draw_wins") or 0)
    draw_total = (home.get("draw_total") or 0)
    draw_rate = safe_rate(draw_wins, draw_total) if draw_total >= 3 else None
    
    # BTTS tendency
    btts_yes_wins = (home.get("btts_yes_wins") or 0)
    btts_yes_total = (home.get("btts_yes_total") or 0)
    btts_rate = safe_rate(btts_yes_wins, btts_yes_total) if btts_yes_total >= 3 else None
    
    # Over 2.5 tendency
    over25_wins = (home.get("over25_wins") or 0)
    over25_total = (home.get("over25_total") or 0)
    over25_rate = safe_rate(over25_wins, over25_total) if over25_total >= 3 else None
    
    # Home strength (basé sur wins du marché home)
    home_wins = (home.get("home_wins") or 0)
    home_total = (home.get("home_total") or 0)
    home_win_rate = safe_rate(home_wins, home_total) if home_total >= 3 else None
    
    # Away strength
    away_wins = (away.get("away_wins") or 0)
    away_total = (away.get("away_total") or 0)
    away_win_rate = safe_rate(away_wins, away_total) if away_total >= 3 else None
    
    # Scores de tendance (0-100)
    draw_tendency = int(draw_rate) if draw_rate else 50
    btts_tendency = int(btts_rate) if btts_rate else 50
    goals_tendency = int(over25_rate) if over25_rate else 50
    home_strength = int(home_win_rate) if home_win_rate else 50
    away_strength = int(away_win_rate) if away_win_rate else 50
    
    # Clean sheet tendency (inverse de BTTS)
    clean_sheet_tendency = 100 - btts_tendency
    
    return {
        "draw_tendency": draw_tendency,
        "btts_tendency": btts_tendency,
        "goals_tendency": goals_tendency,
        "clean_sheet_tendency": clean_sheet_tendency,
        "home_strength": home_strength,
        "away_strength": away_strength,
        "home_draw_rate": draw_rate,
        "home_btts_rate": btts_rate,
        "home_over25_rate": over25_rate,
        "home_win_rate": home_win_rate,
        "away_win_rate": away_win_rate,
        "matches_analyzed": (home.get("total_picks") or 0) + (away.get("total_picks") or 0),
        "avg_clv": home.get("avg_clv"),
        "total_profit": home.get("total_profit")
    }


# ══════════════════════════════════════════════════════════════
# GÉNÉRATION AUTOMATIQUE DES TAGS ET ALERTES
# ══════════════════════════════════════════════════════════════

def generate_tags(scores: Dict) -> List[str]:
    """Génère les tags automatiquement basé sur les scores"""
    tags = []
    
    for tag, (field, operator, threshold) in TAG_RULES.items():
        value = scores.get(field)
        if value is None:
            continue
            
        if operator == ">=" and value >= threshold:
            tags.append(tag)
        elif operator == "<=" and value <= threshold:
            tags.append(tag)
        elif operator == ">" and value > threshold:
            tags.append(tag)
        elif operator == "<" and value < threshold:
            tags.append(tag)
    
    return tags


def generate_market_alerts(scores: Dict) -> Dict:
    """Génère les alertes marchés automatiquement"""
    alerts = {}
    
    for market, rules in MARKET_ALERT_RULES.items():
        for (field, operator, threshold, alert_level, reason_template, alternative) in rules:
            value = scores.get(field)
            if value is None:
                continue
            
            triggered = False
            if operator == ">=" and value >= threshold:
                triggered = True
            elif operator == "<=" and value <= threshold:
                triggered = True
            
            if triggered:
                alerts[market] = {
                    "level": alert_level,
                    "reason": reason_template.format(value=value),
                    "alternative": alternative,
                    "trigger_value": value,
                    "threshold": threshold
                }
                break  # Une seule alerte par marché
    
    return alerts


def determine_style(scores: Dict) -> Tuple[str, int]:
    """Détermine le style de jeu et le score"""
    goals = scores.get("goals_tendency", 50)
    btts = scores.get("btts_tendency", 50)
    
    # Score de style: 0 = ultra défensif, 100 = ultra offensif
    style_score = int((goals + btts) / 2)
    
    if style_score <= 30:
        style = "defensive"
    elif style_score <= 45:
        style = "balanced_defensive"
    elif style_score <= 55:
        style = "balanced"
    elif style_score <= 70:
        style = "balanced_offensive"
    else:
        style = "offensive"
    
    return style, style_score


def determine_home_profile(scores: Dict) -> str:
    """Détermine le profil à domicile"""
    home_strength = scores.get("home_strength", 50)
    draw_tendency = scores.get("draw_tendency", 50)
    
    if home_strength >= 70:
        return "fortress"
    elif draw_tendency >= 60:
        return "draw_king"
    elif home_strength <= 35:
        return "weak_home"
    else:
        return "balanced"


def determine_away_profile(scores: Dict) -> str:
    """Détermine le profil à l'extérieur"""
    away_strength = scores.get("away_strength", 50)
    
    if away_strength >= 55:
        return "road_warriors"
    elif away_strength <= 30:
        return "weak_travelers"
    else:
        return "balanced"


# ══════════════════════════════════════════════════════════════
# INSERTION EN BASE
# ══════════════════════════════════════════════════════════════

def insert_team_intelligence(conn, team_data: Dict) -> bool:
    """Insère ou met à jour une équipe dans team_intelligence"""
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO team_intelligence (
                team_name,
                team_name_normalized,
                current_style,
                current_style_score,
                season_style,
                season_style_score,
                home_strength,
                home_draw_rate,
                home_btts_rate,
                home_over25_rate,
                home_win_rate,
                home_profile,
                away_strength,
                away_win_rate,
                away_profile,
                draw_tendency,
                goals_tendency,
                btts_tendency,
                clean_sheet_tendency,
                tags,
                market_alerts,
                matches_analyzed,
                is_reliable,
                data_quality_score,
                confidence_overall,
                data_sources,
                last_computed_at,
                updated_at
            ) VALUES (
                %(team_name)s,
                %(team_name_normalized)s,
                %(current_style)s,
                %(current_style_score)s,
                %(season_style)s,
                %(season_style_score)s,
                %(home_strength)s,
                %(home_draw_rate)s,
                %(home_btts_rate)s,
                %(home_over25_rate)s,
                %(home_win_rate)s,
                %(home_profile)s,
                %(away_strength)s,
                %(away_win_rate)s,
                %(away_profile)s,
                %(draw_tendency)s,
                %(goals_tendency)s,
                %(btts_tendency)s,
                %(clean_sheet_tendency)s,
                %(tags)s,
                %(market_alerts)s,
                %(matches_analyzed)s,
                %(is_reliable)s,
                %(data_quality_score)s,
                %(confidence_overall)s,
                %(data_sources)s,
                NOW(),
                NOW()
            )
            ON CONFLICT (team_name) DO UPDATE SET
                team_name_normalized = EXCLUDED.team_name_normalized,
                current_style = EXCLUDED.current_style,
                current_style_score = EXCLUDED.current_style_score,
                season_style = EXCLUDED.season_style,
                season_style_score = EXCLUDED.season_style_score,
                home_strength = EXCLUDED.home_strength,
                home_draw_rate = EXCLUDED.home_draw_rate,
                home_btts_rate = EXCLUDED.home_btts_rate,
                home_over25_rate = EXCLUDED.home_over25_rate,
                home_win_rate = EXCLUDED.home_win_rate,
                home_profile = EXCLUDED.home_profile,
                away_strength = EXCLUDED.away_strength,
                away_win_rate = EXCLUDED.away_win_rate,
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
        """, team_data)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur insertion {team_data.get('team_name')}: {e}")
        return False


# ══════════════════════════════════════════════════════════════
# FONCTION PRINCIPALE
# ══════════════════════════════════════════════════════════════

def populate_team_intelligence(limit: int = None, min_picks: int = 5):
    """
    Peuple la table team_intelligence depuis nos données
    
    Args:
        limit: Nombre max d'équipes à traiter (None = toutes)
        min_picks: Minimum de picks pour considérer fiable
    """
    logger.info("🏎️ FERRARI 2.0 - Peuplement team_intelligence")
    logger.info("=" * 60)
    
    conn = get_db_connection()
    
    try:
        # 1. Extraire les équipes
        teams = extract_teams_from_odds(conn)
        
        if limit:
            teams = teams[:limit]
        
        logger.info(f"📊 Traitement de {len(teams)} équipes...")
        
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for i, team in enumerate(teams):
            team_name = team["team_name"]
            
            try:
                # 2. Calculer stats depuis nos picks
                team_stats = calculate_team_stats_from_picks(conn, team_name)
                
                # 3. Calculer scores d'intelligence
                scores = calculate_intelligence_scores(team_stats)
                
                # 4. Générer tags et alertes
                tags = generate_tags(scores)
                market_alerts = generate_market_alerts(scores)
                
                # 5. Déterminer style et profils
                style, style_score = determine_style(scores)
                home_profile = determine_home_profile(scores)
                away_profile = determine_away_profile(scores)
                
                # 6. Calculer qualité et confiance
                matches = scores.get("matches_analyzed", 0)
                is_reliable = matches >= min_picks
                data_quality = min(100, matches * 5)  # 20 matchs = 100%
                confidence = min(100, matches * 4)    # 25 matchs = 100%
                
                # 7. Préparer données pour insertion
                team_data = {
                    "team_name": team_name,
                    "team_name_normalized": normalize_team_name(team_name),
                    "current_style": style,
                    "current_style_score": style_score,
                    "season_style": style,
                    "season_style_score": style_score,
                    "home_strength": scores.get("home_strength", 50),
                    "home_draw_rate": scores.get("home_draw_rate"),
                    "home_btts_rate": scores.get("home_btts_rate"),
                    "home_over25_rate": scores.get("home_over25_rate"),
                    "home_win_rate": scores.get("home_win_rate"),
                    "home_profile": home_profile,
                    "away_strength": scores.get("away_strength", 50),
                    "away_win_rate": scores.get("away_win_rate"),
                    "away_profile": away_profile,
                    "draw_tendency": scores.get("draw_tendency", 50),
                    "goals_tendency": scores.get("goals_tendency", 50),
                    "btts_tendency": scores.get("btts_tendency", 50),
                    "clean_sheet_tendency": scores.get("clean_sheet_tendency", 50),
                    "tags": json.dumps(tags),
                    "market_alerts": json.dumps(market_alerts),
                    "matches_analyzed": matches,
                    "is_reliable": is_reliable,
                    "data_quality_score": data_quality,
                    "confidence_overall": confidence,
                    "data_sources": json.dumps(["tracking_clv_picks", "odds"])
                }
                
                # 8. Insérer
                if insert_team_intelligence(conn, team_data):
                    success_count += 1
                    if (i + 1) % 50 == 0:
                        logger.info(f"  ✅ {i + 1}/{len(teams)} équipes traitées...")
                        conn.commit()
                else:
                    error_count += 1
                    
            except Exception as e:
                logger.error(f"❌ Erreur pour {team_name}: {e}")
                error_count += 1
        
        # Commit final
        conn.commit()
        
        logger.info("=" * 60)
        logger.info(f"🏆 TERMINÉ!")
        logger.info(f"  ✅ Succès: {success_count}")
        logger.info(f"  ⏭️ Ignorés: {skip_count}")
        logger.info(f"  ❌ Erreurs: {error_count}")
        logger.info("=" * 60)
        
        return success_count
        
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        conn.rollback()
        raise
        
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
# POINT D'ENTRÉE
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Peuplement team_intelligence FERRARI 2.0")
    parser.add_argument("--limit", type=int, help="Nombre max d'équipes")
    parser.add_argument("--min-picks", type=int, default=5, help="Minimum de picks pour fiabilité")
    
    args = parser.parse_args()
    
    populate_team_intelligence(limit=args.limit, min_picks=args.min_picks)
