#!/usr/bin/env python3
"""
🏎️ FERRARI 2.0 ULTIMATE - Peuplement team_intelligence V2
Version: SMART AVANCÉ avec VRAIES DONNÉES
Date: 28 Nov 2025

SOURCES DE DONNÉES (par priorité):
1. match_results → Vrais scores de matchs (SOURCE PRINCIPALE)
2. tracking_clv_picks → Historique de nos paris (complément)
3. Calculs intelligents → Tags et alertes automatiques

PRINCIPE: JAMAIS de données inventées - uniquement des calculs réels
"""

import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from decimal import Decimal

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/home/Mon_ps/logs/ferrari_populate_v2.log')
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
# SEUILS POUR GÉNÉRATION DE TAGS (basés sur données réelles)
# ══════════════════════════════════════════════════════════════

THRESHOLDS = {
    # Draw tendency
    "roi_nuls": {"field": "draw_rate", "operator": ">=", "value": 30},
    "peu_nuls": {"field": "draw_rate", "operator": "<=", "value": 15},
    
    # Goals tendency
    "high_scoring": {"field": "avg_goals_total", "operator": ">=", "value": 3.0},
    "low_scoring": {"field": "avg_goals_total", "operator": "<=", "value": 2.0},
    "offensif": {"field": "avg_goals_scored", "operator": ">=", "value": 2.0},
    "defensif": {"field": "avg_goals_conceded", "operator": "<=", "value": 0.8},
    
    # BTTS
    "btts_friendly": {"field": "btts_rate", "operator": ">=", "value": 60},
    "btts_killer": {"field": "btts_rate", "operator": "<=", "value": 35},
    
    # Clean sheets
    "clean_sheet_kings": {"field": "clean_sheet_rate", "operator": ">=", "value": 40},
    
    # Home/Away strength
    "fortress_home": {"field": "home_win_rate", "operator": ">=", "value": 65},
    "weak_home": {"field": "home_win_rate", "operator": "<=", "value": 30},
    "road_warriors": {"field": "away_win_rate", "operator": ">=", "value": 45},
    "weak_away": {"field": "away_win_rate", "operator": "<=", "value": 15},
}

# ══════════════════════════════════════════════════════════════
# RÈGLES D'ALERTES MARCHÉ (basées sur données réelles)
# ══════════════════════════════════════════════════════════════

MARKET_ALERT_RULES = {
    "dc_12": [
        {"field": "home_draw_rate", "operator": ">=", "threshold": 30, 
         "level": "TRAP", "reason": "Équipe fait {value:.1f}% de nuls à domicile", "alternative": "dc_1x"},
        {"field": "home_draw_rate", "operator": ">=", "threshold": 25, 
         "level": "CAUTION", "reason": "Tendance aux nuls à domicile ({value:.1f}%)", "alternative": "dc_1x"},
    ],
    "btts_yes": [
        {"field": "btts_rate", "operator": "<=", "threshold": 40, 
         "level": "TRAP", "reason": "Seulement {value:.1f}% de BTTS", "alternative": "btts_no"},
        {"field": "clean_sheet_rate", "operator": ">=", "threshold": 45, 
         "level": "CAUTION", "reason": "Clean sheet fréquent ({value:.1f}%)", "alternative": "btts_no"},
    ],
    "btts_no": [
        {"field": "btts_rate", "operator": ">=", "threshold": 65, 
         "level": "TRAP", "reason": "{value:.1f}% de matchs avec BTTS", "alternative": "btts_yes"},
    ],
    "over_25": [
        {"field": "avg_goals_total", "operator": "<=", "threshold": 2.2, 
         "level": "TRAP", "reason": "Moyenne {value:.2f} buts/match seulement", "alternative": "under_25"},
        {"field": "over_25_rate", "operator": "<=", "threshold": 40, 
         "level": "CAUTION", "reason": "Seulement {value:.1f}% de Over 2.5", "alternative": "under_25"},
    ],
    "under_25": [
        {"field": "avg_goals_total", "operator": ">=", "threshold": 3.2, 
         "level": "TRAP", "reason": "Moyenne {value:.2f} buts/match", "alternative": "over_25"},
        {"field": "over_25_rate", "operator": ">=", "threshold": 65, 
         "level": "CAUTION", "reason": "{value:.1f}% de Over 2.5", "alternative": "over_25"},
    ],
    "home": [
        {"field": "home_win_rate", "operator": "<=", "threshold": 30, 
         "level": "CAUTION", "reason": "Faible à domicile ({value:.1f}% victoires)", "alternative": "draw"},
    ],
    "away": [
        {"field": "away_win_rate", "operator": "<=", "threshold": 20, 
         "level": "TRAP", "reason": "Très faible en déplacement ({value:.1f}%)", "alternative": "draw"},
    ],
}


# ══════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ══════════════════════════════════════════════════════════════

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def to_float(value) -> Optional[float]:
    """Convertit une valeur en float, gère Decimal et None"""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def calculate_rate(count: int, total: int) -> Optional[float]:
    """Calcule un pourcentage de manière sécurisée"""
    if not total or total == 0:
        return None
    return round((count / total) * 100, 2)


def calculate_average(total: int, count: int) -> Optional[float]:
    """Calcule une moyenne de manière sécurisée"""
    if not count or count == 0:
        return None
    return round(total / count, 2)


# ══════════════════════════════════════════════════════════════
# EXTRACTION DES VRAIES STATS DEPUIS MATCH_RESULTS
# ══════════════════════════════════════════════════════════════

def get_team_stats_from_match_results(conn, team_name: str) -> Dict:
    """
    Calcule les VRAIES stats d'une équipe depuis match_results
    
    Returns:
        Dict avec toutes les stats calculées
    """
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Stats à DOMICILE
    cur.execute("""
        SELECT 
            COUNT(*) as matches_home,
            SUM(CASE WHEN score_home > score_away THEN 1 ELSE 0 END) as home_wins,
            SUM(CASE WHEN score_home = score_away THEN 1 ELSE 0 END) as home_draws,
            SUM(CASE WHEN score_home < score_away THEN 1 ELSE 0 END) as home_losses,
            SUM(score_home) as home_goals_for,
            SUM(score_away) as home_goals_against,
            SUM(CASE WHEN score_home > 0 AND score_away > 0 THEN 1 ELSE 0 END) as home_btts,
            SUM(CASE WHEN score_away = 0 THEN 1 ELSE 0 END) as home_clean_sheets,
            SUM(CASE WHEN score_home = 0 THEN 1 ELSE 0 END) as home_failed_to_score,
            SUM(CASE WHEN score_home + score_away > 2.5 THEN 1 ELSE 0 END) as home_over_25,
            SUM(CASE WHEN score_home + score_away > 1.5 THEN 1 ELSE 0 END) as home_over_15
        FROM match_results
        WHERE home_team = %s AND is_finished = true
    """, (team_name,))
    home_stats = cur.fetchone()
    
    # Stats à l'EXTÉRIEUR
    cur.execute("""
        SELECT 
            COUNT(*) as matches_away,
            SUM(CASE WHEN score_away > score_home THEN 1 ELSE 0 END) as away_wins,
            SUM(CASE WHEN score_home = score_away THEN 1 ELSE 0 END) as away_draws,
            SUM(CASE WHEN score_away < score_home THEN 1 ELSE 0 END) as away_losses,
            SUM(score_away) as away_goals_for,
            SUM(score_home) as away_goals_against,
            SUM(CASE WHEN score_home > 0 AND score_away > 0 THEN 1 ELSE 0 END) as away_btts,
            SUM(CASE WHEN score_home = 0 THEN 1 ELSE 0 END) as away_clean_sheets,
            SUM(CASE WHEN score_away = 0 THEN 1 ELSE 0 END) as away_failed_to_score,
            SUM(CASE WHEN score_home + score_away > 2.5 THEN 1 ELSE 0 END) as away_over_25
        FROM match_results
        WHERE away_team = %s AND is_finished = true
    """, (team_name,))
    away_stats = cur.fetchone()
    
    return {
        "home": dict(home_stats) if home_stats else {},
        "away": dict(away_stats) if away_stats else {}
    }


def calculate_full_stats(raw_stats: Dict) -> Dict:
    """
    Calcule toutes les statistiques depuis les données brutes
    
    PRINCIPE: Aucune donnée inventée - tout est calculé depuis match_results
    """
    home = raw_stats.get("home", {})
    away = raw_stats.get("away", {})
    
    # Extraire les valeurs (avec gestion des None)
    matches_home = home.get("matches_home") or 0
    matches_away = away.get("matches_away") or 0
    total_matches = matches_home + matches_away
    
    if total_matches == 0:
        return None  # Pas de données = pas de stats inventées
    
    # HOME STATS
    home_wins = home.get("home_wins") or 0
    home_draws = home.get("home_draws") or 0
    home_losses = home.get("home_losses") or 0
    home_goals_for = home.get("home_goals_for") or 0
    home_goals_against = home.get("home_goals_against") or 0
    home_btts = home.get("home_btts") or 0
    home_clean_sheets = home.get("home_clean_sheets") or 0
    home_failed_to_score = home.get("home_failed_to_score") or 0
    home_over_25 = home.get("home_over_25") or 0
    home_over_15 = home.get("home_over_15") or 0
    
    # AWAY STATS
    away_wins = away.get("away_wins") or 0
    away_draws = away.get("away_draws") or 0
    away_losses = away.get("away_losses") or 0
    away_goals_for = away.get("away_goals_for") or 0
    away_goals_against = away.get("away_goals_against") or 0
    away_btts = away.get("away_btts") or 0
    away_clean_sheets = away.get("away_clean_sheets") or 0
    away_over_25 = away.get("away_over_25") or 0
    
    # TOTAUX
    total_wins = home_wins + away_wins
    total_draws = home_draws + away_draws
    total_losses = home_losses + away_losses
    total_goals_for = home_goals_for + away_goals_for
    total_goals_against = home_goals_against + away_goals_against
    total_btts = home_btts + away_btts
    total_clean_sheets = home_clean_sheets + away_clean_sheets
    total_over_25 = home_over_25 + away_over_25
    
    # CALCULS DE TAUX (en %)
    stats = {
        # Matchs
        "matches_total": total_matches,
        "matches_home": matches_home,
        "matches_away": matches_away,
        
        # Win rates
        "win_rate": calculate_rate(total_wins, total_matches),
        "home_win_rate": calculate_rate(home_wins, matches_home),
        "away_win_rate": calculate_rate(away_wins, matches_away),
        
        # Draw rates
        "draw_rate": calculate_rate(total_draws, total_matches),
        "home_draw_rate": calculate_rate(home_draws, matches_home),
        "away_draw_rate": calculate_rate(away_draws, matches_away),
        
        # Loss rates
        "loss_rate": calculate_rate(total_losses, total_matches),
        "home_loss_rate": calculate_rate(home_losses, matches_home),
        "away_loss_rate": calculate_rate(away_losses, matches_away),
        
        # Goals
        "avg_goals_scored": calculate_average(total_goals_for, total_matches),
        "avg_goals_conceded": calculate_average(total_goals_against, total_matches),
        "avg_goals_total": calculate_average(total_goals_for + total_goals_against, total_matches),
        "home_goals_scored_avg": calculate_average(home_goals_for, matches_home),
        "home_goals_conceded_avg": calculate_average(home_goals_against, matches_home),
        "away_goals_scored_avg": calculate_average(away_goals_for, matches_away),
        "away_goals_conceded_avg": calculate_average(away_goals_against, matches_away),
        
        # BTTS
        "btts_rate": calculate_rate(total_btts, total_matches),
        "home_btts_rate": calculate_rate(home_btts, matches_home),
        "away_btts_rate": calculate_rate(away_btts, matches_away),
        
        # Clean sheets
        "clean_sheet_rate": calculate_rate(total_clean_sheets, total_matches),
        "home_clean_sheet_rate": calculate_rate(home_clean_sheets, matches_home),
        "away_clean_sheet_rate": calculate_rate(away_clean_sheets, matches_away),
        
        # Over/Under
        "over_25_rate": calculate_rate(total_over_25, total_matches),
        "home_over_25_rate": calculate_rate(home_over_25, matches_home),
        "away_over_25_rate": calculate_rate(away_over_25, matches_away),
        "home_over_15_rate": calculate_rate(home_over_15, matches_home),
    }
    
    return stats


# ══════════════════════════════════════════════════════════════
# GÉNÉRATION INTELLIGENTE DES TAGS
# ══════════════════════════════════════════════════════════════

def generate_tags_from_stats(stats: Dict) -> List[str]:
    """
    Génère les tags basés sur les VRAIES statistiques
    """
    if not stats:
        return []
    
    tags = []
    
    for tag, rule in THRESHOLDS.items():
        field = rule["field"]
        operator = rule["operator"]
        threshold = rule["value"]
        
        value = stats.get(field)
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


# ══════════════════════════════════════════════════════════════
# GÉNÉRATION INTELLIGENTE DES ALERTES MARCHÉ
# ══════════════════════════════════════════════════════════════

def generate_market_alerts_from_stats(stats: Dict) -> Dict:
    """
    Génère les alertes de marché basées sur les VRAIES statistiques
    """
    if not stats:
        return {}
    
    alerts = {}
    
    for market, rules in MARKET_ALERT_RULES.items():
        for rule in rules:
            field = rule["field"]
            value = stats.get(field)
            
            if value is None:
                continue
            
            operator = rule["operator"]
            threshold = rule["threshold"]
            
            triggered = False
            if operator == ">=" and value >= threshold:
                triggered = True
            elif operator == "<=" and value <= threshold:
                triggered = True
            
            if triggered:
                alerts[market] = {
                    "level": rule["level"],
                    "reason": rule["reason"].format(value=value),
                    "alternative": rule.get("alternative"),
                    "trigger_value": round(value, 2),
                    "threshold": threshold
                }
                break  # Une seule alerte par marché (la plus sévère)
    
    return alerts


# ══════════════════════════════════════════════════════════════
# CALCUL DU STYLE ET DES PROFILS
# ══════════════════════════════════════════════════════════════

def determine_style(stats: Dict) -> Tuple[str, int]:
    """
    Détermine le style de jeu basé sur les stats réelles
    """
    if not stats:
        return ("unknown", 50)
    
    goals_scored = stats.get("avg_goals_scored") or 0
    goals_conceded = stats.get("avg_goals_conceded") or 0
    
    # Score de style: différence offensive vs défensive
    # Positif = offensif, Négatif = défensif
    style_diff = goals_scored - goals_conceded
    
    # Normaliser en score 0-100 (50 = équilibré)
    style_score = int(50 + (style_diff * 20))
    style_score = max(0, min(100, style_score))
    
    if style_score <= 30:
        style = "defensive"
    elif style_score <= 42:
        style = "balanced_defensive"
    elif style_score <= 58:
        style = "balanced"
    elif style_score <= 70:
        style = "balanced_offensive"
    else:
        style = "offensive"
    
    return (style, style_score)


def determine_home_profile(stats: Dict) -> str:
    """Détermine le profil à domicile"""
    if not stats:
        return "unknown"
    
    home_win_rate = stats.get("home_win_rate") or 50
    home_draw_rate = stats.get("home_draw_rate") or 20
    
    if home_win_rate >= 65:
        return "fortress"
    elif home_draw_rate >= 30:
        return "draw_king"
    elif home_win_rate <= 30:
        return "weak_home"
    else:
        return "balanced"


def determine_away_profile(stats: Dict) -> str:
    """Détermine le profil à l'extérieur"""
    if not stats:
        return "unknown"
    
    away_win_rate = stats.get("away_win_rate") or 30
    away_draw_rate = stats.get("away_draw_rate") or 30
    
    if away_win_rate >= 45:
        return "road_warriors"
    elif away_win_rate <= 15:
        return "weak_travelers"
    elif away_draw_rate >= 40:
        return "draw_specialists"
    else:
        return "balanced"


def calculate_tendencies(stats: Dict) -> Dict:
    """Calcule les scores de tendance (0-100)"""
    if not stats:
        return {}
    
    draw_rate = stats.get("draw_rate") or 25
    btts_rate = stats.get("btts_rate") or 50
    avg_goals = stats.get("avg_goals_total") or 2.5
    clean_sheet = stats.get("clean_sheet_rate") or 25
    
    return {
        "draw_tendency": min(100, int(draw_rate * 2.5)),  # 40% draw = 100
        "btts_tendency": min(100, int(btts_rate)),
        "goals_tendency": min(100, int((avg_goals / 4) * 100)),  # 4 goals = 100
        "clean_sheet_tendency": min(100, int(clean_sheet * 2)),  # 50% CS = 100
    }


# ══════════════════════════════════════════════════════════════
# RÉCUPÉRATION DU NOM CANONIQUE
# ══════════════════════════════════════════════════════════════

def get_canonical_name(conn, source_name: str) -> Tuple[str, bool]:
    """
    Récupère le nom canonique depuis team_name_mapping
    
    Returns:
        (canonical_name, has_odds_data)
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT canonical_name, match_method
        FROM team_name_mapping
        WHERE source_name = %s AND source_table = 'match_results'
    """, (source_name,))
    
    result = cur.fetchone()
    if result:
        canonical, method = result
        has_odds = method != 'no_odds_data'
        return (canonical, has_odds)
    
    return (source_name, False)


# ══════════════════════════════════════════════════════════════
# INSERTION EN BASE
# ══════════════════════════════════════════════════════════════

def upsert_team_intelligence(conn, team_data: Dict) -> bool:
    """Insère ou met à jour une équipe"""
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO team_intelligence (
                team_name, team_name_normalized,
                current_style, current_style_score,
                season_style, season_style_score,
                home_strength, home_win_rate, home_draw_rate, home_loss_rate,
                home_goals_scored_avg, home_goals_conceded_avg,
                home_btts_rate, home_over25_rate, home_over15_rate,
                home_clean_sheet_rate, home_profile,
                away_strength, away_win_rate, away_draw_rate, away_loss_rate,
                away_goals_scored_avg, away_goals_conceded_avg,
                away_btts_rate, away_over25_rate, away_clean_sheet_rate,
                away_profile,
                draw_tendency, goals_tendency, btts_tendency, clean_sheet_tendency,
                tags, market_alerts,
                matches_analyzed, is_reliable,
                data_quality_score, confidence_overall,
                data_sources, last_computed_at, updated_at
            ) VALUES (
                %(team_name)s, %(team_name_normalized)s,
                %(current_style)s, %(current_style_score)s,
                %(season_style)s, %(season_style_score)s,
                %(home_strength)s, %(home_win_rate)s, %(home_draw_rate)s, %(home_loss_rate)s,
                %(home_goals_scored_avg)s, %(home_goals_conceded_avg)s,
                %(home_btts_rate)s, %(home_over25_rate)s, %(home_over15_rate)s,
                %(home_clean_sheet_rate)s, %(home_profile)s,
                %(away_strength)s, %(away_win_rate)s, %(away_draw_rate)s, %(away_loss_rate)s,
                %(away_goals_scored_avg)s, %(away_goals_conceded_avg)s,
                %(away_btts_rate)s, %(away_over25_rate)s, %(away_clean_sheet_rate)s,
                %(away_profile)s,
                %(draw_tendency)s, %(goals_tendency)s, %(btts_tendency)s, %(clean_sheet_tendency)s,
                %(tags)s, %(market_alerts)s,
                %(matches_analyzed)s, %(is_reliable)s,
                %(data_quality_score)s, %(confidence_overall)s,
                %(data_sources)s, NOW(), NOW()
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
                home_over15_rate = EXCLUDED.home_over15_rate,
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
        """, team_data)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur insertion {team_data.get('team_name')}: {e}")
        return False


# ══════════════════════════════════════════════════════════════
# FONCTION PRINCIPALE
# ══════════════════════════════════════════════════════════════

def populate_from_match_results(min_matches: int = 3):
    """
    Peuple team_intelligence depuis les VRAIES données de match_results
    
    Args:
        min_matches: Minimum de matchs pour considérer fiable
    """
    logger.info("🏎️ FERRARI 2.0 V2 - Peuplement depuis VRAIES DONNÉES")
    logger.info("=" * 60)
    logger.info(f"📊 Source: match_results (vrais scores)")
    logger.info(f"📊 Seuil fiabilité: {min_matches} matchs minimum")
    logger.info("=" * 60)
    
    conn = get_db_connection()
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Récupérer toutes les équipes de match_results
        cur.execute("""
            SELECT DISTINCT home_team as team_name FROM match_results WHERE is_finished = true
            UNION
            SELECT DISTINCT away_team as team_name FROM match_results WHERE is_finished = true
        """)
        teams = [row["team_name"] for row in cur.fetchall() if row["team_name"]]
        
        logger.info(f"📊 {len(teams)} équipes trouvées dans match_results")
        
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for i, team_name in enumerate(teams):
            try:
                # 2. Récupérer le nom canonique
                canonical_name, has_odds = get_canonical_name(conn, team_name)
                
                # 3. Récupérer les stats brutes
                raw_stats = get_team_stats_from_match_results(conn, team_name)
                
                # 4. Calculer les stats complètes
                stats = calculate_full_stats(raw_stats)
                
                if not stats or stats.get("matches_total", 0) < min_matches:
                    skip_count += 1
                    continue
                
                # 5. Générer tags et alertes
                tags = generate_tags_from_stats(stats)
                market_alerts = generate_market_alerts_from_stats(stats)
                
                # 6. Déterminer style et profils
                style, style_score = determine_style(stats)
                home_profile = determine_home_profile(stats)
                away_profile = determine_away_profile(stats)
                tendencies = calculate_tendencies(stats)
                
                # 7. Calculer qualité et confiance
                matches = stats.get("matches_total", 0)
                is_reliable = matches >= min_matches
                data_quality = min(100, matches * 8)  # 12 matchs = ~100%
                confidence = min(100, matches * 6)    # 16 matchs = ~100%
                
                # 8. Préparer données
                team_data = {
                    "team_name": canonical_name,
                    "team_name_normalized": canonical_name.lower().replace(" ", "_"),
                    "current_style": style,
                    "current_style_score": style_score,
                    "season_style": style,
                    "season_style_score": style_score,
                    "home_strength": int(stats.get("home_win_rate") or 50),
                    "home_win_rate": stats.get("home_win_rate"),
                    "home_draw_rate": stats.get("home_draw_rate"),
                    "home_loss_rate": stats.get("home_loss_rate"),
                    "home_goals_scored_avg": stats.get("home_goals_scored_avg"),
                    "home_goals_conceded_avg": stats.get("home_goals_conceded_avg"),
                    "home_btts_rate": stats.get("home_btts_rate"),
                    "home_over25_rate": stats.get("home_over_25_rate"),
                    "home_over15_rate": stats.get("home_over_15_rate"),
                    "home_clean_sheet_rate": stats.get("home_clean_sheet_rate"),
                    "home_profile": home_profile,
                    "away_strength": int(stats.get("away_win_rate") or 30),
                    "away_win_rate": stats.get("away_win_rate"),
                    "away_draw_rate": stats.get("away_draw_rate"),
                    "away_loss_rate": stats.get("away_loss_rate"),
                    "away_goals_scored_avg": stats.get("away_goals_scored_avg"),
                    "away_goals_conceded_avg": stats.get("away_goals_conceded_avg"),
                    "away_btts_rate": stats.get("away_btts_rate"),
                    "away_over25_rate": stats.get("away_over_25_rate"),
                    "away_clean_sheet_rate": stats.get("away_clean_sheet_rate"),
                    "away_profile": away_profile,
                    "draw_tendency": tendencies.get("draw_tendency", 50),
                    "goals_tendency": tendencies.get("goals_tendency", 50),
                    "btts_tendency": tendencies.get("btts_tendency", 50),
                    "clean_sheet_tendency": tendencies.get("clean_sheet_tendency", 50),
                    "tags": json.dumps(tags),
                    "market_alerts": json.dumps(market_alerts),
                    "matches_analyzed": matches,
                    "is_reliable": is_reliable,
                    "data_quality_score": data_quality,
                    "confidence_overall": confidence,
                    "data_sources": json.dumps(["match_results"])
                }
                
                # 9. Insérer
                if upsert_team_intelligence(conn, team_data):
                    success_count += 1
                    if (i + 1) % 20 == 0:
                        logger.info(f"  ✅ {i + 1}/{len(teams)} équipes traitées...")
                        conn.commit()
                else:
                    error_count += 1
                    
            except Exception as e:
                logger.error(f"❌ Erreur {team_name}: {e}")
                error_count += 1
        
        # Commit final
        conn.commit()
        
        logger.info("=" * 60)
        logger.info("🏆 TERMINÉ!")
        logger.info(f"  ✅ Succès: {success_count}")
        logger.info(f"  ⏭️ Ignorés (< {min_matches} matchs): {skip_count}")
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
    
    parser = argparse.ArgumentParser(description="Peuplement team_intelligence V2 - VRAIES DONNÉES")
    parser.add_argument("--min-matches", type=int, default=3, 
                        help="Minimum de matchs pour fiabilité (défaut: 3)")
    
    args = parser.parse_args()
    
    populate_from_match_results(min_matches=args.min_matches)
