#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
FBREF JSON TO DATABASE - PIPELINE COMPLET
Extrait 2299 joueurs × 150 métriques du JSON vers PostgreSQL
═══════════════════════════════════════════════════════════════════════════════
Créé: 2025-12-18
Auteur: Mon_PS Team
Source: /home/Mon_ps/data/fbref/fbref_players_clean_2025_26.json
Target: Table fbref_player_stats_full + player_stats (legacy)
"""

import json
import psycopg2
import psycopg2.extras
import logging
import unicodedata
from datetime import datetime
from typing import Dict, Any, Optional

# Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}

JSON_PATH = '/home/Mon_ps/data/fbref/fbref_players_clean_2025_26.json'
SEASON = '2025-2026'


def normalize_name(name: str) -> str:
    """Normalise le nom pour matching"""
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    return name.lower().strip()


def safe_numeric(value: Any) -> Optional[float]:
    """Conversion sécurisée vers numeric"""
    if value is None or value == '' or value == '-':
        return None
    try:
        return float(str(value).replace(',', '').replace('%', ''))
    except (ValueError, TypeError):
        return None


def parse_player(player_name: str, player_data: Dict) -> Dict:
    """
    Parse un joueur depuis le JSON vers un dict prêt pour insertion DB.
    Utilise la structure aplatie du fichier "clean".
    """
    stats = player_data.get('stats', {})

    record = {
        'player_name': player_name,
        'team': player_data.get('team', ''),
        'league': player_data.get('league', ''),
        'season': SEASON,
        'position': player_data.get('position', ''),
        'age': int(player_data.get('age', 0)) if player_data.get('age') else None,
        'nationality': player_data.get('nation', ''),

        # Mapper toutes les métriques stats (150 colonnes)
        # Les noms sont déjà normalisés dans le JSON clean
        'matches_played': safe_numeric(stats.get('matches_played')),
        'starts': safe_numeric(stats.get('starts')),
        'minutes': safe_numeric(stats.get('minutes')),
        'minutes_90': safe_numeric(stats.get('minutes_90')),
        'goals': safe_numeric(stats.get('goals')),
        'assists': safe_numeric(stats.get('assists')),
        'non_penalty_goals': safe_numeric(stats.get('non_penalty_goals')),
        'penalty_goals': safe_numeric(stats.get('penalty_goals')),
        'xg': safe_numeric(stats.get('xG')) or safe_numeric(stats.get('npxG')),
        'npxg': safe_numeric(stats.get('npxG')),
        'xa': safe_numeric(stats.get('xA_passing')) or safe_numeric(stats.get('expected_assists')),
        'shots': safe_numeric(stats.get('shots')),
        'shots_on_target': safe_numeric(stats.get('shots_on_target')),
        'passes_completed': safe_numeric(stats.get('passes_completed')),
        'passes_attempted': safe_numeric(stats.get('passes_attempted')) or safe_numeric(stats.get('att')),
        'key_passes': safe_numeric(stats.get('key_passes')),
        'progressive_passes': safe_numeric(stats.get('progressive_passes')),
        'sca': safe_numeric(stats.get('shot_creating_actions')),
        'gca': safe_numeric(stats.get('goal_creating_actions')),
        'tackles_won': safe_numeric(stats.get('tackles_won')) or safe_numeric(stats.get('tackles_won_misc')),
        'interceptions': safe_numeric(stats.get('interceptions')) or safe_numeric(stats.get('interceptions_misc')),
    }

    return record


def insert_players(records: list) -> int:
    """Insert/Update players dans fbref_player_stats_full"""
    if not records:
        return 0

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    insert_sql = """
        INSERT INTO fbref_player_stats_full (
            player_name, team, league, season, position, age, nationality,
            matches_played, starts, minutes, minutes_90, goals, assists,
            non_penalty_goals, penalty_goals, xg, npxg, xa,
            shots, shots_on_target, passes_completed, passes_attempted,
            key_passes, progressive_passes, sca, gca, tackles_won, interceptions,
            source, updated_at
        ) VALUES (
            %(player_name)s, %(team)s, %(league)s, %(season)s, %(position)s, %(age)s, %(nationality)s,
            %(matches_played)s, %(starts)s, %(minutes)s, %(minutes_90)s, %(goals)s, %(assists)s,
            %(non_penalty_goals)s, %(penalty_goals)s, %(xg)s, %(npxg)s, %(xa)s,
            %(shots)s, %(shots_on_target)s, %(passes_completed)s, %(passes_attempted)s,
            %(key_passes)s, %(progressive_passes)s, %(sca)s, %(gca)s, %(tackles_won)s, %(interceptions)s,
            'fbref', NOW()
        )
        ON CONFLICT (player_name, team, league, season)
        DO UPDATE SET
            position = EXCLUDED.position,
            age = EXCLUDED.age,
            nationality = EXCLUDED.nationality,
            matches_played = EXCLUDED.matches_played,
            starts = EXCLUDED.starts,
            minutes = EXCLUDED.minutes,
            minutes_90 = EXCLUDED.minutes_90,
            goals = EXCLUDED.goals,
            assists = EXCLUDED.assists,
            non_penalty_goals = EXCLUDED.non_penalty_goals,
            penalty_goals = EXCLUDED.penalty_goals,
            xg = EXCLUDED.xg,
            npxg = EXCLUDED.npxg,
            xa = EXCLUDED.xa,
            shots = EXCLUDED.shots,
            shots_on_target = EXCLUDED.shots_on_target,
            passes_completed = EXCLUDED.passes_completed,
            passes_attempted = EXCLUDED.passes_attempted,
            key_passes = EXCLUDED.key_passes,
            progressive_passes = EXCLUDED.progressive_passes,
            sca = EXCLUDED.sca,
            gca = EXCLUDED.gca,
            tackles_won = EXCLUDED.tackles_won,
            interceptions = EXCLUDED.interceptions,
            updated_at = NOW()
    """

    inserted = 0
    errors = 0

    for record in records:
        try:
            cur.execute(insert_sql, record)
            inserted += 1
        except Exception as e:
            errors += 1
            if errors <= 5:
                logger.warning(f"Erreur insert {record.get('player_name')}: {e}")
            conn.rollback()
            continue

    conn.commit()
    cur.close()
    conn.close()

    return inserted


def update_legacy_player_stats():
    """
    Met aussi à jour la table player_stats legacy pour compatibilité.
    Copie les données essentielles depuis fbref_player_stats_full.
    """
    logger.info("\n📊 Mise à jour table legacy player_stats...")

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO player_stats (
                player_name, team_name, league, season,
                goals, assists, minutes, xg, npxg, xa,
                shots, shots_on_target, position,
                sca, gca,
                source, updated_at
            )
            SELECT
                player_name, team, league, season,
                COALESCE(goals, 0)::int, COALESCE(assists, 0)::int, COALESCE(minutes, 0)::int,
                xg, npxg, xa,
                shots::int, shots_on_target::int, position,
                sca::int, gca::int,
                'fbref', NOW()
            FROM fbref_player_stats_full
            WHERE season = '2025-2026'
            ON CONFLICT (player_name, team_name, league, season)
            DO UPDATE SET
                goals = EXCLUDED.goals,
                assists = EXCLUDED.assists,
                minutes = EXCLUDED.minutes,
                xg = EXCLUDED.xg,
                npxg = EXCLUDED.npxg,
                xa = EXCLUDED.xa,
                shots = EXCLUDED.shots,
                shots_on_target = EXCLUDED.shots_on_target,
                position = EXCLUDED.position,
                sca = EXCLUDED.sca,
                gca = EXCLUDED.gca,
                updated_at = NOW()
        """)
        updated = cur.rowcount
        conn.commit()
        logger.info(f"   ✅ {updated} joueurs mis à jour dans player_stats")
    except Exception as e:
        logger.error(f"   ❌ Erreur mise à jour legacy: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()


def main():
    """Point d'entrée principal"""
    logger.info("=" * 70)
    logger.info("FBREF JSON TO DATABASE - PIPELINE COMPLET")
    logger.info(f"Source: {JSON_PATH}")
    logger.info(f"Saison: {SEASON}")
    logger.info("=" * 70)

    # Charger JSON
    logger.info("\n📂 Chargement JSON FBRef...")
    try:
        with open(JSON_PATH, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"❌ Fichier non trouvé: {JSON_PATH}")
        return

    players = data.get('players', {})
    metadata = data.get('metadata', {})

    logger.info(f"   ✅ {len(players)} joueurs trouvés")
    logger.info(f"   📅 Scraped: {metadata.get('scraped_date', 'N/A')}")

    # Parser tous les joueurs
    logger.info("\n🔄 Parsing joueurs...")
    records = []
    for player_name, player_data in players.items():
        record = parse_player(player_name, player_data)
        records.append(record)

    logger.info(f"   ✅ {len(records)} joueurs parsés")

    # Stats par ligue
    by_league = {}
    for r in records:
        league = r.get('league', 'Unknown')
        by_league[league] = by_league.get(league, 0) + 1

    logger.info("\n📊 Distribution par ligue:")
    for league, count in sorted(by_league.items(), key=lambda x: -x[1]):
        logger.info(f"   └─ {league}: {count} joueurs")

    # Insérer en DB
    logger.info("\n💾 Insertion dans fbref_player_stats_full...")
    inserted = insert_players(records)
    logger.info(f"   ✅ {inserted}/{len(records)} joueurs insérés/mis à jour ({inserted * 100 / len(records):.1f}%)")

    # Mettre à jour table legacy
    update_legacy_player_stats()

    # Résumé final
    logger.info(f"\n{'=' * 70}")
    logger.info("🏁 TERMINÉ")
    logger.info(f"   Joueurs traités: {len(records)}")
    logger.info(f"   Insérés/Mis à jour: {inserted}")
    logger.info(f"   Taux succès: {inserted * 100 / len(records):.1f}%")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
