#!/usr/bin/env python3
"""
Enrichissement ADN équipes promues 2024-2025
Date: 2025-12-16
Mission: Générer fingerprints V3 et tags pour Ipswich, Leicester, Southampton

Approche:
- Basé sur profils historiques connus + données Championship
- Tag spécial: PROMOTED_2024_25 pour tracking
- Fingerprints V3 format avec métriques estimées
"""

import psycopg2
from datetime import datetime

# Configuration PostgreSQL
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}

# Profils équipes promues (basés sur style historique + Championship 2023-24)
PROMOTED_TEAMS = {
    'Ipswich': {
        'fingerprint': 'IPS_TRAN_P14.0_PS48_D0.75_M-UNK0_G-CHR68',
        'tags': [
            'PROMOTED_2024_25',
            'TRANSITION',
            'AVERAGE_VOLUME',
            'BALANCED',
            'OPEN_PLAY_DOMINANT',
            'STEADY_SCORER',
            'DIRECT_PLAY',
            'DATA_PENDING',
            'CHAMPIONSHIP_WINNER'
        ],
        'tactical': 'TRANSITION',
        'reasoning': 'Ipswich - Champions Championship 2023-24. Style transition, équilibrés.'
    },
    'Leicester': {
        'fingerprint': 'LEI_POSS_P12.5_PS52_D0.82_M-JAM12_G-HER71',
        'tags': [
            'PROMOTED_2024_25',
            'POSSESSION',
            'AVERAGE_VOLUME',
            'BALANCED',
            'OPEN_PLAY_DOMINANT',
            'STEADY_SCORER',
            'CREATIVE_HUB',
            'DATA_PENDING',
            'EX_PREMIER_LEAGUE',
            'MVP_DEPENDENT'
        ],
        'tactical': 'POSSESSION',
        'reasoning': 'Leicester - Ex Premier League, style possession, dépendance Jamie Vardy.'
    },
    'Southampton': {
        'fingerprint': 'SOU_BALA_P13.8_PS50_D0.71_M-CHE6_G-BAZ69',
        'tags': [
            'PROMOTED_2024_25',
            'BALANCED',
            'AVERAGE_VOLUME',
            'BALANCED',
            'OPEN_PLAY_DOMINANT',
            'STEADY_SCORER',
            'DIRECT_PLAY',
            'DATA_PENDING',
            'PLAYOFF_WINNER'
        ],
        'tactical': 'BALANCED',
        'reasoning': 'Southampton - Vainqueurs playoffs Championship 2023-24. Style équilibré.'
    }
}


def update_promoted_teams(conn):
    """Mettre à jour les fingerprints et tags pour les 3 promus."""
    cursor = conn.cursor()

    print("\n🔄 Enrichissement équipes promues...")

    for team_name, data in PROMOTED_TEAMS.items():
        fingerprint = data['fingerprint']
        tags = data['tags']
        reasoning = data['reasoning']

        print(f"\n📝 {team_name}:")
        print(f"   Fingerprint: {fingerprint}")
        print(f"   Tags: {len(tags)} tags")
        print(f"   Reasoning: {reasoning}")

        # UPDATE PostgreSQL
        cursor.execute("""
            UPDATE quantum.team_quantum_dna_v3
            SET
                dna_fingerprint = %s,
                narrative_fingerprint_tags = %s,
                updated_at = NOW()
            WHERE team_name = %s
        """, (fingerprint, tags, team_name))

        if cursor.rowcount > 0:
            print(f"   ✅ Mis à jour")
        else:
            print(f"   ⚠️  Équipe non trouvée en DB")

    conn.commit()
    cursor.close()


def verify_promoted_teams(conn):
    """Vérifier l'état des équipes promues."""
    cursor = conn.cursor()

    print("\n📊 VÉRIFICATION ÉQUIPES PROMUES:")
    print("=" * 80)

    cursor.execute("""
        SELECT
            team_name,
            dna_fingerprint,
            narrative_fingerprint_tags,
            array_length(narrative_fingerprint_tags, 1) as tag_count
        FROM quantum.team_quantum_dna_v3
        WHERE team_name IN ('Ipswich', 'Leicester', 'Southampton')
        ORDER BY team_name
    """)

    for row in cursor.fetchall():
        team_name, fingerprint, tags, tag_count = row
        print(f"\n{team_name}:")
        print(f"  Fingerprint: {fingerprint}")
        print(f"  Tags ({tag_count}): {', '.join(tags[:5])}...")

    cursor.close()


def main():
    """Fonction principale."""
    print("=" * 80)
    print("ENRICHISSEMENT ÉQUIPES PROMUES 2024-2025")
    print("=" * 80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Connexion PostgreSQL
    print(f"\n🔗 Connexion à PostgreSQL...")
    conn = psycopg2.connect(**DB_CONFIG)
    print("✅ Connecté")

    # Enrichissement
    update_promoted_teams(conn)

    # Vérification
    verify_promoted_teams(conn)

    # Fermeture
    conn.close()
    print(f"\n✅ Enrichissement promus terminé!")
    print("=" * 80)


if __name__ == "__main__":
    main()
