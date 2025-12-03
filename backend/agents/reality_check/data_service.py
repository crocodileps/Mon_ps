#!/usr/bin/env python3
"""
📊 REALITY DATA SERVICE
========================
Service d'accès aux données Reality Check dans PostgreSQL.
Gère les requêtes vers les 9 tables Reality Check.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
import logging
from typing import Dict, Optional, List
from contextlib import contextmanager

logger = logging.getLogger('RealityDataService')

# Configuration DB (compatible Docker et Local)
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'monps_postgres'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'monps_db'),
    'user': os.getenv('DB_USER', 'monps_user'),
    'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
}


class RealityDataService:
    """
    Service d'accès aux données Reality Check.
    Gère la connexion et les requêtes vers les tables:
    - team_class
    - team_momentum
    - tactical_matrix
    - referee_intelligence
    - head_to_head
    - weather_conditions
    - match_context
    """
    
    def __init__(self, db_config: Dict = None):
        self.db_config = db_config or DB_CONFIG
        self._conn = None
    
    @contextmanager
    def get_connection(self):
        """Context manager pour connexion DB sécurisée"""
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            yield conn
        except Exception as e:
            logger.error(f"DB Connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def get_team_class(self, team_name: str) -> Optional[Dict]:
        """
        Récupère la classification d'une équipe (Tier S/A/B/C/D).
        Cherche par nom exact, puis par variants JSONB.
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Recherche par nom exact d'abord
                    cur.execute("""
                        SELECT 
                            team_name, tier, league, country,
                            historical_strength, squad_value_millions,
                            star_players, big_game_factor,
                            home_fortress_factor, away_weakness_factor,
                            psychological_edge, correction_factor,
                            coach, playing_style, calculated_power_index
                        FROM team_class 
                        WHERE LOWER(team_name) = LOWER(%s)
                        LIMIT 1
                    """, (team_name,))
                    result = cur.fetchone()
                    
                    if result:
                        return dict(result)
                    
                    # Recherche par variants JSONB
                    cur.execute("""
                        SELECT 
                            team_name, tier, league, country,
                            historical_strength, squad_value_millions,
                            star_players, big_game_factor,
                            home_fortress_factor, away_weakness_factor,
                            psychological_edge, correction_factor,
                            coach, playing_style, calculated_power_index
                        FROM team_class 
                        WHERE team_name_variants ? %s
                           OR team_name_variants ? LOWER(%s)
                           OR LOWER(team_name) LIKE LOWER(%s)
                        LIMIT 1
                    """, (team_name, team_name, f"%{team_name}%"))
                    result = cur.fetchone()
                    
                    return dict(result) if result else None
                    
        except Exception as e:
            logger.error(f"Error fetching team_class for {team_name}: {e}")
            return None
    
    def get_team_momentum(self, team_name: str) -> Optional[Dict]:
        """Récupère le momentum/forme actuelle d'une équipe"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT 
                            team_name, last_5_results, last_5_points,
                            momentum_status, momentum_score,
                            current_streak, home_streak, away_streak,
                            confidence_level, pressure_level,
                            coach_under_pressure, new_coach_bounce,
                            key_player_returning, key_player_absent,
                            absent_players, goals_scored_last_5,
                            goals_conceded_last_5, clean_sheets_last_5,
                            failed_to_score_last_5
                        FROM team_momentum 
                        WHERE LOWER(team_name) LIKE LOWER(%s)
                        LIMIT 1
                    """, (f"%{team_name}%",))
                    result = cur.fetchone()
                    return dict(result) if result else None
                    
        except Exception as e:
            logger.error(f"Error fetching team_momentum for {team_name}: {e}")
            return None
    
    def get_tactical_matchup(self, style_a: str, style_b: str) -> Optional[Dict]:
        """
        Récupère les stats d'un matchup tactique (Style A vs Style B).
        Ex: 'possession' vs 'low_block_counter'
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT 
                            style_a, style_b,
                            win_rate_a, draw_rate, win_rate_b,
                            upset_probability, btts_probability,
                            over_25_probability, under_25_probability,
                            notes
                        FROM tactical_matrix 
                        WHERE LOWER(style_a) = LOWER(%s) 
                          AND LOWER(style_b) = LOWER(%s)
                        LIMIT 1
                    """, (style_a, style_b))
                    result = cur.fetchone()
                    return dict(result) if result else None
                    
        except Exception as e:
            logger.error(f"Error fetching tactical_matchup {style_a} vs {style_b}: {e}")
            return None
    
    def get_referee_profile(self, referee_name: str) -> Optional[Dict]:
        """Récupère le profil d'un arbitre"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT 
                            referee_name, league,
                            strictness_level, avg_yellow_cards_per_game,
                            penalty_frequency, home_bias_factor,
                            under_over_tendency, avg_goals_per_game,
                            matches_officiated
                        FROM referee_intelligence 
                        WHERE LOWER(referee_name) LIKE LOWER(%s)
                        LIMIT 1
                    """, (f"%{referee_name}%",))
                    result = cur.fetchone()
                    return dict(result) if result else None
                    
        except Exception as e:
            logger.error(f"Error fetching referee_profile for {referee_name}: {e}")
            return None
    
    def get_head_to_head(self, team_a: str, team_b: str) -> Optional[Dict]:
        """Récupère l'historique des confrontations directes"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Chercher dans les deux sens
                    cur.execute("""
                        SELECT 
                            team_a, team_b, total_matches,
                            team_a_wins, team_b_wins, draws,
                            avg_total_goals, btts_percentage,
                            over_25_percentage, dominant_team,
                            dominance_factor, home_advantage_strong,
                            always_goals, low_scoring
                        FROM head_to_head 
                        WHERE (LOWER(team_a) LIKE LOWER(%s) AND LOWER(team_b) LIKE LOWER(%s))
                           OR (LOWER(team_a) LIKE LOWER(%s) AND LOWER(team_b) LIKE LOWER(%s))
                        LIMIT 1
                    """, (f"%{team_a}%", f"%{team_b}%", f"%{team_b}%", f"%{team_a}%"))
                    result = cur.fetchone()
                    return dict(result) if result else None
                    
        except Exception as e:
            logger.error(f"Error fetching H2H {team_a} vs {team_b}: {e}")
            return None
    
    def get_weather_conditions(self, home_team: str, away_team: str, match_time: str = None) -> Optional[Dict]:
        """Récupère les conditions météo pour un match"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT 
                            weather_type, temperature_celsius,
                            wind_speed_kmh, precipitation_mm,
                            pitch_condition, weather_impact_level,
                            over_under_adjustment,
                            possession_team_disadvantage,
                            physical_team_advantage,
                            recommended_adjustments
                        FROM weather_conditions 
                        WHERE LOWER(home_team) LIKE LOWER(%s)
                          AND LOWER(away_team) LIKE LOWER(%s)
                        ORDER BY created_at DESC
                        LIMIT 1
                    """, (f"%{home_team}%", f"%{away_team}%"))
                    result = cur.fetchone()
                    return dict(result) if result else None
                    
        except Exception as e:
            logger.error(f"Error fetching weather for {home_team} vs {away_team}: {e}")
            return None
    
    def get_match_context(self, home_team: str, away_team: str) -> Optional[Dict]:
        """Récupère le contexte du match (derby, enjeu, etc.)"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT 
                            match_type, stakes_level, stakes_description,
                            is_derby, derby_type, is_title_race,
                            is_relegation_battle, is_european_spot,
                            is_cup_final, is_knockout, is_revenge_match,
                            importance_score
                        FROM match_context 
                        WHERE LOWER(home_team) LIKE LOWER(%s)
                          AND LOWER(away_team) LIKE LOWER(%s)
                        ORDER BY created_at DESC
                        LIMIT 1
                    """, (f"%{home_team}%", f"%{away_team}%"))
                    result = cur.fetchone()
                    return dict(result) if result else None
                    
        except Exception as e:
            logger.error(f"Error fetching match_context for {home_team} vs {away_team}: {e}")
            return None


# ============================================================
# DEFAULTS (Fallback si données manquantes)
# ============================================================

DEFAULT_TEAM_CLASS = {
    'tier': 'C',
    'historical_strength': 50,
    'big_game_factor': 1.0,
    'home_fortress_factor': 1.0,
    'away_weakness_factor': 1.0,
    'psychological_edge': 1.0,
    'correction_factor': 0.95,
    'playing_style': 'balanced',
    'calculated_power_index': 50.0
}

DEFAULT_MOMENTUM = {
    'momentum_status': 'stable',
    'momentum_score': 50,
    'confidence_level': 50,
    'pressure_level': 50,
    'coach_under_pressure': False,
    'key_player_absent': False
}
