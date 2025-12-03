#!/usr/bin/env python3
"""
📊 CRON: Peuplement team_intelligence_history
Crée un snapshot initial et track les changements de style/form/stats

Usage:
    python3 populate_team_intelligence_history.py

Cron recommandé: 0 7 * * * (après update_momentum)
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from datetime import datetime
import logging

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/monps/team_intelligence_history.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Configuration DB
DB_CONFIG = {
    'host': os.environ.get('POSTGRES_HOST', 'localhost'),
    'port': int(os.environ.get('POSTGRES_PORT', 5432)),
    'dbname': os.environ.get('POSTGRES_DB', 'monps_db'),
    'user': os.environ.get('POSTGRES_USER', 'monps_user'),
    'password': os.environ.get('POSTGRES_PASSWORD', 'monps_secure_password_2024')
}

# Champs à tracker
TRACKED_FIELDS = [
    'current_style',
    'current_form', 
    'current_pressing',
    'home_goals_scored_avg',
    'home_goals_conceded_avg',
    'away_goals_scored_avg',
    'away_goals_conceded_avg',
    'home_win_rate',
    'away_win_rate',
    'home_btts_rate',
    'away_btts_rate',
    'home_over25_rate',
    'away_over25_rate'
]

def get_affected_markets(field: str) -> list:
    """Détermine les marchés affectés par un changement de champ"""
    if 'style' in field or 'pressing' in field:
        return ['1X2', 'BTTS', 'O/U']
    elif 'btts' in field:
        return ['BTTS']
    elif 'over' in field:
        return ['O/U']
    elif 'goals' in field:
        return ['O/U', 'BTTS', '1X2']
    elif 'win_rate' in field:
        return ['1X2']
    elif 'form' in field:
        return ['1X2', 'BTTS', 'O/U']
    return ['1X2']

def calculate_change_magnitude(old_val, new_val, field: str) -> float:
    """Calcule la magnitude du changement"""
    if old_val is None or new_val is None:
        return 0
    
    # Pour les champs texte (style, form)
    if isinstance(old_val, str) or isinstance(new_val, str):
        return 1.0 if str(old_val) != str(new_val) else 0.0
    
    # Pour les champs numériques
    try:
        old_f = float(old_val) if old_val else 0
        new_f = float(new_val) if new_val else 0
        if old_f == 0:
            return abs(new_f)
        return abs((new_f - old_f) / old_f)
    except:
        return 0

def determine_impact(magnitude: float, field: str) -> str:
    """Détermine l'impact sur les prédictions"""
    if magnitude >= 0.3:
        return 'HIGH'
    elif magnitude >= 0.15:
        return 'MEDIUM'
    elif magnitude > 0:
        return 'LOW'
    return 'NONE'

def populate_initial_snapshot():
    """Crée un snapshot initial pour toutes les équipes"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Vérifier si déjà peuplé
        cursor.execute("SELECT COUNT(*) as cnt FROM team_intelligence_history")
        existing = cursor.fetchone()['cnt']
        
        if existing > 0:
            logger.info(f"⚠️ Table déjà peuplée ({existing} entrées), passage en mode delta")
            return track_changes(conn, cursor)
        
        # Récupérer toutes les équipes avec leurs données
        cursor.execute(f"""
            SELECT id, team_name, {', '.join(TRACKED_FIELDS)}
            FROM team_intelligence
            WHERE team_name IS NOT NULL
        """)
        
        teams = cursor.fetchall()
        logger.info(f"📊 {len(teams)} équipes à snapshoter")
        
        inserted = 0
        for team in teams:
            team_id = team['id']
            team_name = team['team_name']
            
            # Créer une entrée pour chaque champ tracké
            for field in TRACKED_FIELDS:
                value = team.get(field)
                if value is not None:
                    cursor.execute("""
                        INSERT INTO team_intelligence_history (
                            team_intelligence_id, team_name, field_changed,
                            old_value, new_value, change_type,
                            change_magnitude, change_reason, trigger_event,
                            impact_on_predictions, affected_markets,
                            changed_by, change_source, algorithm_version,
                            is_validated, created_at
                        ) VALUES (
                            %s, %s, %s,
                            NULL, %s, %s,
                            %s, %s, %s,
                            %s, %s,
                            %s, %s, %s,
                            %s, NOW()
                        )
                    """, (
                        team_id, team_name, field,
                        str(value), 'initial_snapshot',
                        0, 'Initial data load', 'system_init',
                        'NONE', Json(get_affected_markets(field)),
                        'system', 'cron_populate', 'v1.0',
                        True
                    ))
                    inserted += 1
        
        conn.commit()
        logger.info(f"✅ {inserted} entrées snapshot créées")
        return inserted
        
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def track_changes(conn, cursor):
    """Track les changements depuis le dernier snapshot"""
    
    # Récupérer le dernier état connu par équipe/champ
    cursor.execute("""
        WITH latest_values AS (
            SELECT DISTINCT ON (team_intelligence_id, field_changed)
                team_intelligence_id, team_name, field_changed, new_value, created_at
            FROM team_intelligence_history
            ORDER BY team_intelligence_id, field_changed, created_at DESC
        )
        SELECT * FROM latest_values
    """)
    
    last_known = {}
    for row in cursor.fetchall():
        key = (row['team_intelligence_id'], row['field_changed'])
        last_known[key] = row['new_value']
    
    # Récupérer les valeurs actuelles
    cursor.execute(f"""
        SELECT id, team_name, {', '.join(TRACKED_FIELDS)}
        FROM team_intelligence
        WHERE team_name IS NOT NULL
    """)
    
    current_teams = cursor.fetchall()
    
    changes_detected = 0
    for team in current_teams:
        team_id = team['id']
        team_name = team['team_name']
        
        for field in TRACKED_FIELDS:
            current_value = team.get(field)
            if current_value is None:
                continue
                
            key = (team_id, field)
            old_value = last_known.get(key)
            
            # Comparer (conversion en string pour comparaison)
            current_str = str(current_value) if current_value else None
            old_str = str(old_value) if old_value else None
            
            if current_str != old_str and old_value is not None:
                # Changement détecté !
                magnitude = calculate_change_magnitude(old_value, current_value, field)
                impact = determine_impact(magnitude, field)
                
                cursor.execute("""
                    INSERT INTO team_intelligence_history (
                        team_intelligence_id, team_name, field_changed,
                        old_value, new_value, change_type,
                        change_magnitude, change_reason, trigger_event,
                        impact_on_predictions, affected_markets,
                        changed_by, change_source, algorithm_version,
                        is_validated, created_at
                    ) VALUES (
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s,
                        %s, %s, %s,
                        %s, NOW()
                    )
                """, (
                    team_id, team_name, field,
                    old_str, current_str, 'value_change',
                    magnitude, 'Automatic detection', 'cron_tracking',
                    impact, Json(get_affected_markets(field)),
                    'system', 'cron_tracking', 'v1.0',
                    False  # À valider
                ))
                changes_detected += 1
                logger.info(f"   📝 {team_name}.{field}: {old_str} → {current_str}")
    
    conn.commit()
    logger.info(f"✅ {changes_detected} changements détectés et enregistrés")
    return changes_detected

if __name__ == "__main__":
    logger.info("🚀 Démarrage peuplement team_intelligence_history")
    populate_initial_snapshot()
    logger.info("✅ Terminé")
