#!/usr/bin/env python3
"""
Migration Script: Populate api_football_name in quantum.team_name_mapping
═══════════════════════════════════════════════════════════════════════════

Détecte automatiquement le pattern de conversion pour chaque équipe:
- ADD_FC: quantum_name + " FC" (ex: Arsenal → Arsenal FC)
- EXACT: quantum_name identique (ex: AC Milan → AC Milan)
- FUZZY: Recherche partielle (ex: Bologna → Bologna FC 1909)

Auteur: Mon_PS Team
Date: 2025-12-24
Version: 1.0.0
═══════════════════════════════════════════════════════════════════════════
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from typing import Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MigrationAPIFootball")

# Configuration DB
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}


def find_api_football_name(cur, quantum_name: str) -> Tuple[Optional[str], str]:
    """
    Trouve le nom API-Football correspondant au quantum_name.

    Returns:
        (api_football_name, pattern_used)
    """
    # Pattern 1: EXACT match
    cur.execute("""
        SELECT DISTINCT home_team
        FROM match_results
        WHERE home_team = %s
        LIMIT 1
    """, (quantum_name,))
    result = cur.fetchone()
    if result:
        return result['home_team'], 'EXACT'

    # Pattern 2: ADD_FC (quantum_name + " FC")
    candidate = f"{quantum_name} FC"
    cur.execute("""
        SELECT DISTINCT home_team
        FROM match_results
        WHERE home_team = %s
        LIMIT 1
    """, (candidate,))
    result = cur.fetchone()
    if result:
        return result['home_team'], 'ADD_FC'

    # Pattern 3: PREFIX_FC ("FC " + quantum_name)
    candidate = f"FC {quantum_name}"
    cur.execute("""
        SELECT DISTINCT home_team
        FROM match_results
        WHERE home_team = %s
        LIMIT 1
    """, (candidate,))
    result = cur.fetchone()
    if result:
        return result['home_team'], 'PREFIX_FC'

    # Pattern 4: CONTAINS (recherche partielle)
    cur.execute("""
        SELECT home_team, LENGTH(home_team) as len
        FROM match_results
        WHERE home_team ILIKE %s
        GROUP BY home_team
        ORDER BY len ASC
        LIMIT 1
    """, (f"%{quantum_name}%",))
    result = cur.fetchone()
    if result:
        return result['home_team'], 'CONTAINS'

    # Pattern 5: REVERSE CONTAINS (quantum_name contient le nom)
    cur.execute("""
        SELECT home_team, LENGTH(home_team) as len
        FROM match_results
        WHERE %s ILIKE '%%' || home_team || '%%'
        GROUP BY home_team
        ORDER BY len DESC
        LIMIT 1
    """, (quantum_name,))
    result = cur.fetchone()
    if result:
        return result['home_team'], 'REVERSE_CONTAINS'

    return None, 'NO_MATCH'


def migrate():
    """Exécute la migration."""
    logger.info("="*70)
    logger.info("MIGRATION: Populate api_football_name")
    logger.info("="*70)

    conn = psycopg2.connect(**DB_CONFIG)

    stats = {
        'EXACT': 0,
        'ADD_FC': 0,
        'PREFIX_FC': 0,
        'CONTAINS': 0,
        'REVERSE_CONTAINS': 0,
        'NO_MATCH': 0,
        'total': 0
    }

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Récupérer toutes les équipes du mapping
            cur.execute("""
                SELECT quantum_name
                FROM quantum.team_name_mapping
                ORDER BY quantum_name
            """)
            teams = cur.fetchall()
            stats['total'] = len(teams)

            logger.info(f"  {len(teams)} equipes a traiter")
            logger.info("")

            for team in teams:
                quantum_name = team['quantum_name']
                api_football_name, pattern = find_api_football_name(cur, quantum_name)

                stats[pattern] += 1

                if api_football_name:
                    # Update la colonne
                    cur.execute("""
                        UPDATE quantum.team_name_mapping
                        SET api_football_name = %s
                        WHERE quantum_name = %s
                    """, (api_football_name, quantum_name))

                    logger.info(f"  {quantum_name:30} -> {api_football_name:35} [{pattern}]")
                else:
                    logger.warning(f"  {quantum_name:30} -> NO MATCH FOUND")

            conn.commit()
            logger.info("")
            logger.info("  Migration COMMIT")

    except psycopg2.Error as e:
        logger.error(f"  Erreur SQL: {e}")
        conn.rollback()

    finally:
        conn.close()

    # Rapport final
    logger.info("")
    logger.info("="*70)
    logger.info("RAPPORT MIGRATION")
    logger.info("="*70)
    logger.info(f"  Total equipes: {stats['total']}")
    logger.info(f"  EXACT: {stats['EXACT']}")
    logger.info(f"  ADD_FC: {stats['ADD_FC']}")
    logger.info(f"  PREFIX_FC: {stats['PREFIX_FC']}")
    logger.info(f"  CONTAINS: {stats['CONTAINS']}")
    logger.info(f"  REVERSE_CONTAINS: {stats['REVERSE_CONTAINS']}")
    logger.info(f"  NO_MATCH: {stats['NO_MATCH']}")
    logger.info("="*70)

    return stats


if __name__ == "__main__":
    migrate()
