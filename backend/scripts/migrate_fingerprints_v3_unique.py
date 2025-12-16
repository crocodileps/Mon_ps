#!/usr/bin/env python3
"""
Migration des fingerprints UNIQUES depuis team_narrative_dna_v3.json vers PostgreSQL
Date: 2025-12-16
Phase 5.1: Fingerprints V3 Uniques

Objectif: Remplacer fingerprints génériques par fingerprints UNIQUES
Source: /home/Mon_ps/data/quantum_v2/team_narrative_dna_v3.json (96 équipes, 100% uniques)
Cible: quantum.team_quantum_dna_v3 (99 équipes, actuellement 56.6% uniques)
"""

import json
import psycopg2
from datetime import datetime
from typing import Dict, List, Tuple

# Configuration PostgreSQL
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}

# Mapping des noms différents entre JSON et PostgreSQL
NAME_MAPPING = {
    # JSON → PostgreSQL
    "Borussia Monchengladbach": "Borussia M.Gladbach",
    "Heidenheim": "FC Heidenheim",
    "Inter Milan": "Inter",
    "Paris Saint-Germain": "Paris Saint Germain",
    "AS Roma": "Roma",
    "RB Leipzig": "RasenBallsport Leipzig",
    "Wolverhampton": "Wolverhampton Wanderers",
    "Parma": "Parma Calcio 1913",
    "Hellas Verona": "Verona",
    "Leeds United": "Leeds",
    "Athletic Bilbao": "Athletic Club"  # Au cas où
}

# Fichier JSON source
JSON_SOURCE = "/home/Mon_ps/data/quantum_v2/team_narrative_dna_v3.json"


def load_json_data() -> Dict:
    """Charger le fichier JSON source."""
    print(f"\n📥 Chargement du fichier JSON: {JSON_SOURCE}")
    with open(JSON_SOURCE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"✅ {len(data)} équipes chargées depuis JSON")
    return data


def extract_dna_tags(dna: Dict) -> List[str]:
    """
    Extraire les tags depuis le DNA pour narrative_fingerprint_tags.

    Tags extraits:
    - tactical.profile (ex: GEGENPRESS)
    - goalkeeper.status (ex: ELITE)
    - mvp.name (prénom du MVP)
    - Autres métadonnées importantes
    """
    tags = []

    # Tag tactique
    if 'tactical' in dna and 'profile' in dna['tactical']:
        tags.append(dna['tactical']['profile'])

    # Tag goalkeeper
    if 'goalkeeper' in dna:
        gk = dna['goalkeeper']
        if 'status' in gk:
            tags.append(f"GK_{gk['status']}")
        if 'name' in gk:
            # Extraire prénom du GK
            gk_name = gk['name'].split()[0]
            tags.append(f"GK_{gk_name}")

    # Tag MVP
    if 'mvp' in dna and 'name' in dna['mvp']:
        mvp_name = dna['mvp']['name'].split()[0]
        tags.append(f"MVP_{mvp_name}")

    # Tag contextes
    if 'context' in dna:
        ctx = dna['context']
        if 'best_context' in ctx:
            tags.append(f"BEST_{ctx['best_context']}")
        if 'avoid_context' in ctx:
            tags.append(f"AVOID_{ctx['avoid_context']}")

    return tags


def map_team_name(json_name: str) -> str:
    """Mapper le nom JSON vers le nom PostgreSQL si différent."""
    return NAME_MAPPING.get(json_name, json_name)


def update_fingerprints(conn, json_data: Dict) -> Tuple[int, int, List[str]]:
    """
    Mettre à jour les fingerprints et tags dans PostgreSQL.

    Returns:
        (updated_count, not_found_count, not_found_teams)
    """
    cursor = conn.cursor()

    # 1. Récupérer toutes les équipes PostgreSQL
    cursor.execute("""
        SELECT team_id, team_name
        FROM quantum.team_quantum_dna_v3
        ORDER BY team_name
    """)
    pg_teams = {row[1]: row[0] for row in cursor.fetchall()}
    print(f"\n📋 PostgreSQL: {len(pg_teams)} équipes")

    # 2. Mettre à jour chaque équipe
    updated = 0
    not_found = []

    print(f"\n🔄 Migration des fingerprints...")

    for json_name, team_data in json_data.items():
        # Extraire le fingerprint
        fingerprint = team_data.get('fingerprint', {}).get('text', '')

        # Extraire le DNA
        dna = team_data.get('dna', {})

        # Extraire les tags depuis DNA
        tags = extract_dna_tags(dna)

        # Mapper le nom
        pg_name = map_team_name(json_name)

        # Vérifier si l'équipe existe en PostgreSQL
        if pg_name not in pg_teams:
            not_found.append(json_name)
            print(f"  ⚠️  Équipe non trouvée: {json_name} (mappé: {pg_name})")
            continue

        # Mettre à jour PostgreSQL
        cursor.execute("""
            UPDATE quantum.team_quantum_dna_v3
            SET
                dna_fingerprint = %s,
                narrative_fingerprint_tags = %s,
                updated_at = NOW()
            WHERE team_name = %s
        """, (fingerprint, tags, pg_name))

        if cursor.rowcount > 0:
            updated += 1
            print(f"  ✅ {pg_name}: {fingerprint[:50]}... ({len(tags)} tags)")

    conn.commit()
    cursor.close()

    return updated, len(not_found), not_found


def verify_uniqueness(conn) -> Tuple[int, int, float]:
    """
    Vérifier l'unicité des fingerprints après migration.

    Returns:
        (total_teams, unique_fingerprints, uniqueness_pct)
    """
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(DISTINCT dna_fingerprint) as unique_fp
        FROM quantum.team_quantum_dna_v3
    """)

    total, unique_fp = cursor.fetchone()
    uniqueness_pct = (unique_fp / total * 100) if total > 0 else 0

    cursor.close()
    return total, unique_fp, uniqueness_pct


def show_sample_fingerprints(conn, limit: int = 10):
    """Afficher quelques exemples de fingerprints migrés."""
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            team_name,
            dna_fingerprint,
            narrative_fingerprint_tags
        FROM quantum.team_quantum_dna_v3
        WHERE dna_fingerprint IS NOT NULL
        ORDER BY team_name
        LIMIT %s
    """, (limit,))

    print(f"\n📋 Exemples de fingerprints migrés:")
    for team_name, fingerprint, tags in cursor.fetchall():
        tags_str = ', '.join(tags[:5]) if tags else 'N/A'
        print(f"  {team_name:20s} → {fingerprint}")
        print(f"    Tags: {tags_str}")

    cursor.close()


def main():
    """Fonction principale de migration."""
    print("=" * 80)
    print("MIGRATION FINGERPRINTS V3 UNIQUES")
    print("=" * 80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. Charger le JSON
    json_data = load_json_data()

    # 2. Connexion PostgreSQL
    print(f"\n🔗 Connexion à PostgreSQL...")
    conn = psycopg2.connect(**DB_CONFIG)
    print("✅ Connecté")

    # 3. Vérifier l'état AVANT
    print(f"\n📊 ÉTAT AVANT MIGRATION:")
    total_before, unique_before, pct_before = verify_uniqueness(conn)
    print(f"  Total équipes: {total_before}")
    print(f"  Fingerprints uniques: {unique_before}")
    print(f"  Unicité: {pct_before:.1f}%")

    # 4. Exécuter la migration
    updated, not_found_count, not_found_teams = update_fingerprints(conn, json_data)

    # 5. Vérifier l'état APRÈS
    print(f"\n📊 ÉTAT APRÈS MIGRATION:")
    total_after, unique_after, pct_after = verify_uniqueness(conn)
    print(f"  Total équipes: {total_after}")
    print(f"  Fingerprints uniques: {unique_after}")
    print(f"  Unicité: {pct_after:.1f}%")

    # 6. Résumé
    print(f"\n" + "=" * 80)
    print(f"📊 RÉSUMÉ MIGRATION:")
    print(f"=" * 80)
    print(f"  ✅ Équipes mises à jour: {updated}/{len(json_data)} ({updated/len(json_data)*100:.1f}%)")
    print(f"  ⚠️  Équipes non trouvées: {not_found_count}")
    if not_found_teams:
        print(f"\n  Équipes manquantes:")
        for team in not_found_teams:
            mapped = map_team_name(team)
            print(f"    - {team} (mappé: {mapped})")

    print(f"\n  📈 Amélioration unicité: {pct_before:.1f}% → {pct_after:.1f}% (+{pct_after - pct_before:.1f}%)")
    print(f"  📈 Fingerprints uniques: {unique_before} → {unique_after} (+{unique_after - unique_before})")

    # 7. Exemples
    show_sample_fingerprints(conn, limit=10)

    # 8. Fermeture
    conn.close()
    print(f"\n✅ Migration terminée avec succès!")
    print("=" * 80)


if __name__ == "__main__":
    main()
