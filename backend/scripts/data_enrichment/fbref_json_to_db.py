#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
FBREF JSON TO DATABASE V2.0 - PERFECTION 150/150 MÉTRIQUES
Extrait 2299 joueurs × 150 métriques du JSON vers PostgreSQL
═══════════════════════════════════════════════════════════════════════════════
Version: 2.0 - Dynamic Parsing (Hedge Fund Grade)
Créé: 2025-12-18
Auteur: Mon_PS Team
Source: /home/Mon_ps/data/fbref/fbref_players_clean_2025_26.json
Target: Table fbref_player_stats_full (163 colonnes) + player_stats (legacy)
Mapping: /tmp/fbref_column_mapping.json (150 métriques JSON → SQL)
"""

import json
import psycopg2
import psycopg2.extras
import logging
import unicodedata
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

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
COLUMN_MAPPING_PATH = '/tmp/fbref_column_mapping.json'
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


def load_column_mapping() -> Dict[str, str]:
    """Charge le mapping JSON → SQL depuis le fichier de configuration"""
    try:
        with open(COLUMN_MAPPING_PATH, 'r') as f:
            mapping = json.load(f)
        logger.info(f"   ✅ Mapping chargé: {len(mapping)} colonnes")
        return mapping
    except FileNotFoundError:
        logger.error(f"   ❌ Mapping non trouvé: {COLUMN_MAPPING_PATH}")
        return {}


def parse_player_dynamic(player_name: str, player_data: Dict, column_mapping: Dict) -> Dict:
    """
    Parse un joueur depuis le JSON vers un dict prêt pour insertion DB.
    Utilise le mapping dynamique pour extraire TOUTES les métriques.
    """
    stats = player_data.get('stats', {})

    # Base fields
    record = {
        'player_name': player_name,
        'player_name_normalized': normalize_name(player_name),
        'team': player_data.get('team', ''),
        'league': player_data.get('league', ''),
        'season': SEASON,
        'position': player_data.get('position', ''),
        'age': int(player_data.get('age', 0)) if player_data.get('age') else None,
        'nationality': player_data.get('nation', ''),
        'source': 'fbref',
        'scraped_at': player_data.get('scraped_at'),
    }

    # Dynamically map all 150 metrics from stats dict
    for json_key, sql_column in column_mapping.items():
        # Try exact match first
        value = stats.get(json_key)

        # If not found, try case-insensitive search for mixed case keys
        if value is None:
            # Try common variations (xG, npxG, xA, etc.)
            for key in stats.keys():
                if key.lower() == json_key.lower():
                    value = stats.get(key)
                    break

        record[sql_column] = safe_numeric(value)

    return record


def get_dynamic_columns(conn) -> List[str]:
    """Récupère la liste des colonnes disponibles dans fbref_player_stats_full"""
    cur = conn.cursor()
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'fbref_player_stats_full'
        ORDER BY ordinal_position
    """)
    columns = [row[0] for row in cur.fetchall()]
    cur.close()

    # Exclure les colonnes auto-générées
    exclude = ['id', 'inserted_at', 'updated_at']
    columns = [c for c in columns if c not in exclude]

    return columns


def insert_players_dynamic(records: list) -> int:
    """Insert/Update players dans fbref_player_stats_full avec toutes les métriques"""
    if not records:
        return 0

    conn = psycopg2.connect(**DB_CONFIG)

    # Récupérer les colonnes disponibles dans la table
    available_columns = get_dynamic_columns(conn)
    logger.info(f"   📊 Colonnes disponibles dans la table: {len(available_columns)}")

    # Filtrer les colonnes présentes dans les records
    sample_record = records[0]
    columns_to_insert = [col for col in available_columns if col in sample_record]
    logger.info(f"   📊 Colonnes à insérer: {len(columns_to_insert)}")

    # Construire dynamiquement la requête INSERT
    column_names = ', '.join(columns_to_insert)
    placeholders = ', '.join([f'%({col})s' for col in columns_to_insert])

    # Construire les clauses UPDATE
    update_clauses = ', '.join([
        f"{col} = EXCLUDED.{col}"
        for col in columns_to_insert
        if col not in ['player_name', 'team', 'league', 'season']
    ])

    insert_sql = f"""
        INSERT INTO fbref_player_stats_full ({column_names}, updated_at)
        VALUES ({placeholders}, NOW())
        ON CONFLICT (player_name, team, league, season)
        DO UPDATE SET
            {update_clauses},
            updated_at = NOW()
    """

    cur = conn.cursor()
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


def audit_completeness():
    """
    Audit Hedge Fund: Vérifie que toutes les 150 métriques sont bien remplies.
    Retourne statistiques de complétude par colonne.
    """
    logger.info("\n" + "=" * 70)
    logger.info("📊 AUDIT HEDGE FUND - COMPLÉTUDE DES 150 MÉTRIQUES")
    logger.info("=" * 70)

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Récupérer toutes les colonnes métriques
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'fbref_player_stats_full'
        AND column_name NOT IN (
            'id', 'player_name', 'player_name_normalized', 'team', 'league',
            'season', 'position', 'age', 'nationality', 'source',
            'scraped_at', 'inserted_at', 'updated_at'
        )
        ORDER BY column_name
    """)
    metric_columns = [row[0] for row in cur.fetchall()]

    logger.info(f"\n📈 Colonnes métriques trouvées: {len(metric_columns)}")

    # Compter les valeurs NULL par colonne
    cur.execute("SELECT COUNT(*) FROM fbref_player_stats_full")
    total_players = cur.fetchone()[0]

    completeness_report = []
    empty_columns = []
    perfect_columns = []

    for column in metric_columns:
        cur.execute(f"""
            SELECT
                COUNT(*) as total,
                COUNT({column}) as non_null,
                COUNT(*) - COUNT({column}) as null_count
            FROM fbref_player_stats_full
        """)
        total, non_null, null_count = cur.fetchone()
        completeness_pct = (non_null / total * 100) if total > 0 else 0

        completeness_report.append({
            'column': column,
            'non_null': non_null,
            'null_count': null_count,
            'completeness_pct': completeness_pct
        })

        if completeness_pct == 0:
            empty_columns.append(column)
        elif completeness_pct == 100:
            perfect_columns.append(column)

    # Statistiques globales
    avg_completeness = sum(r['completeness_pct'] for r in completeness_report) / len(completeness_report)

    logger.info(f"\n📊 STATISTIQUES GLOBALES:")
    logger.info(f"   Total joueurs: {total_players}")
    logger.info(f"   Total métriques: {len(metric_columns)}")
    logger.info(f"   Complétude moyenne: {avg_completeness:.1f}%")
    logger.info(f"   Colonnes parfaites (100%): {len(perfect_columns)}")
    logger.info(f"   Colonnes vides (0%): {len(empty_columns)}")

    # Top 10 colonnes les mieux remplies
    logger.info(f"\n✅ TOP 10 COLONNES LES MIEUX REMPLIES:")
    top_filled = sorted(completeness_report, key=lambda x: -x['completeness_pct'])[:10]
    for i, col_data in enumerate(top_filled, 1):
        logger.info(f"   {i:2d}. {col_data['column']:30s} → {col_data['completeness_pct']:5.1f}% ({col_data['non_null']:4d}/{total_players})")

    # Colonnes vides (si présentes)
    if empty_columns:
        logger.info(f"\n⚠️  COLONNES VIDES ({len(empty_columns)}):")
        for col in empty_columns[:20]:  # Limiter à 20 pour l'affichage
            logger.info(f"   └─ {col}")

    cur.close()
    conn.close()

    logger.info("=" * 70)

    return {
        'total_metrics': len(metric_columns),
        'avg_completeness': avg_completeness,
        'perfect_columns': len(perfect_columns),
        'empty_columns': len(empty_columns)
    }


def update_legacy_player_stats():
    """
    Met à jour la table player_stats legacy pour compatibilité.
    Avec gestion robuste des contraintes manquantes.
    """
    logger.info("\n📊 Mise à jour table legacy player_stats...")

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        # La contrainte UNIQUE existante est (player_name, team_name, season)
        # On l'utilise pour l'UPSERT
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
                COALESCE(goals, 0)::int,
                COALESCE(assists, 0)::int,
                COALESCE(minutes, 0)::int,
                xg, npxg, xa,
                COALESCE(shots, 0)::int,
                COALESCE(shots_on_target, 0)::int,
                position,
                COALESCE(shot_creating_actions, 0)::int,
                COALESCE(goal_creating_actions, 0)::int,
                'fbref', NOW()
            FROM fbref_player_stats_full
            WHERE season = %s
            ON CONFLICT (player_name, team_name, season)
            DO UPDATE SET
                league = EXCLUDED.league,
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
        """, (SEASON,))
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
    logger.info("FBREF JSON TO DATABASE V2.0 - PERFECTION 150/150")
    logger.info(f"Source: {JSON_PATH}")
    logger.info(f"Saison: {SEASON}")
    logger.info("=" * 70)

    # Charger mapping colonnes
    logger.info("\n📂 Chargement mapping colonnes...")
    column_mapping = load_column_mapping()
    if not column_mapping:
        logger.error("❌ Impossible de continuer sans mapping")
        return

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

    # Parser tous les joueurs avec mapping dynamique
    logger.info("\n🔄 Parsing joueurs (150 métriques dynamiques)...")
    records = []
    for player_name, player_data in players.items():
        record = parse_player_dynamic(player_name, player_data, column_mapping)
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

    # Insérer en DB avec toutes les métriques
    logger.info("\n💾 Insertion dans fbref_player_stats_full (150 métriques)...")
    inserted = insert_players_dynamic(records)
    logger.info(f"   ✅ {inserted}/{len(records)} joueurs insérés/mis à jour ({inserted * 100 / len(records):.1f}%)")

    # Audit de complétude
    audit_results = audit_completeness()

    # Mettre à jour table legacy
    update_legacy_player_stats()

    # Résumé final
    logger.info(f"\n{'=' * 70}")
    logger.info("🏁 TERMINÉ - VERSION 2.0 PERFECTION")
    logger.info(f"   Joueurs traités: {len(records)}")
    logger.info(f"   Insérés/Mis à jour: {inserted}")
    logger.info(f"   Taux succès: {inserted * 100 / len(records):.1f}%")
    logger.info(f"   Métriques totales: {audit_results['total_metrics']}")
    logger.info(f"   Complétude moyenne: {audit_results['avg_completeness']:.1f}%")
    logger.info(f"   Colonnes parfaites: {audit_results['perfect_columns']}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
