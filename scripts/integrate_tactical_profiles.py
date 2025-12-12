#!/usr/bin/env python3
"""
🔗 INTÉGRATION PROFILS TACTIQUES → TEAM DNA UNIFIED
Fusionne classification_results_v25.json dans team_dna_unified_v2.json

Auteur: Mon_PS Quant Team
Date: 12 Décembre 2025
"""

import json
from datetime import datetime
from pathlib import Path

# Paths
DATA_DIR = Path("data/quantum_v2")
CLASSIFICATION_FILE = DATA_DIR / "classification_results_v25.json"
UNIFIED_FILE = DATA_DIR / "team_dna_unified_v2.json"
OUTPUT_FILE = DATA_DIR / "team_dna_unified_v3.json"  # Nouvelle version
BACKUP_FILE = DATA_DIR / f"team_dna_unified_v2_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

# Mapping famille des profils
PROFILE_TO_FAMILY = {
    # Offensifs
    "POSSESSION": "OFFENSIVE",
    "GEGENPRESS": "OFFENSIVE",
    "WIDE_ATTACK": "OFFENSIVE",
    "DIRECT_ATTACK": "OFFENSIVE",
    # Défensifs
    "LOW_BLOCK": "DEFENSIVE",
    "MID_BLOCK": "DEFENSIVE",
    "PARK_THE_BUS": "DEFENSIVE",
    # Hybrides
    "TRANSITION": "HYBRID",
    "ADAPTIVE": "HYBRID",
    "BALANCED": "HYBRID",
    # Contextuels
    "HOME_DOMINANT": "CONTEXTUAL",
    "SCORE_DEPENDENT": "CONTEXTUAL"
}


def load_json(path: Path) -> dict:
    """Charge un fichier JSON."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: dict, path: Path) -> None:
    """Sauvegarde un fichier JSON."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Sauvegardé: {path}")


def integrate_tactical_profiles():
    """Intègre les profils tactiques V25 dans team_dna_unified."""

    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║     INTÉGRATION PROFILS TACTIQUES → TEAM DNA UNIFIED            ║")
    print("╚══════════════════════════════════════════════════════════════════╝")

    # 1. Charger les fichiers
    print("\n📂 Chargement des fichiers...")
    classification = load_json(CLASSIFICATION_FILE)
    unified = load_json(UNIFIED_FILE)

    # 2. Backup
    print(f"\n💾 Backup: {BACKUP_FILE}")
    save_json(unified, BACKUP_FILE)

    # 3. Extraire les résultats de classification (C'EST UNE LISTE!)
    results_list = classification.get('results', [])
    # Convertir en dict pour lookup rapide
    results = {item['team']: item for item in results_list}
    print(f"\n📊 Classification V25: {len(results)} équipes")
    print(f"   Équipes classifiées: {list(results.keys())[:5]}...")

    # 4. Intégrer dans unified
    integrated_count = 0
    missing_teams = []

    for team_name, team_data in unified['teams'].items():
        # Chercher dans classification (matching flexible)
        classification_data = None

        # Essayer le nom exact
        if team_name in results:
            classification_data = results[team_name]
        else:
            # Essayer les aliases
            aliases = team_data.get('meta', {}).get('aliases', [])
            for alias in aliases:
                if alias in results:
                    classification_data = results[alias]
                    break

            # Essayer matching partiel (contient)
            if not classification_data:
                for class_team in results.keys():
                    if class_team in team_name or team_name in class_team:
                        classification_data = results[class_team]
                        break

        if classification_data:
            # Créer la section tactical_profile
            profile = classification_data.get('profile', 'BALANCED')
            confidence = classification_data.get('confidence', 0.5)

            # Ajouter au tactical
            if 'tactical' not in team_data:
                team_data['tactical'] = {}

            team_data['tactical']['tactical_profile'] = {
                'profile': profile,
                'family': PROFILE_TO_FAMILY.get(profile, 'HYBRID'),
                'confidence': round(confidence, 3),
                'secondary_profile': classification_data.get('secondary_profile', None),
                'classified_at': classification.get('generated_at', ''),
                'engine_version': classification.get('engine_version', '2.5'),
                'explanations': classification_data.get('explanations', [])
            }

            integrated_count += 1
        else:
            missing_teams.append(team_name)

    # 5. Mettre à jour metadata
    unified['metadata']['tactical_profiles_integrated'] = True
    unified['metadata']['tactical_profiles_version'] = '2.5'
    unified['metadata']['integration_date'] = datetime.now().isoformat()
    unified['metadata']['version'] = 'v3.0'

    # 6. Sauvegarder
    save_json(unified, OUTPUT_FILE)

    # 7. Stats
    print("\n" + "═" * 60)
    print("📊 RÉSULTATS INTÉGRATION")
    print("═" * 60)
    print(f"✅ Équipes intégrées: {integrated_count}/{len(unified['teams'])}")
    print(f"⚠️  Équipes sans profil: {len(missing_teams)}")

    if missing_teams:
        print(f"\nÉquipes manquantes: {missing_teams[:10]}...")

    # 8. Vérification
    print("\n🔍 VÉRIFICATION (3 exemples)")
    print("-" * 40)
    for team in ['Liverpool', 'Manchester City', 'Atletico Madrid']:
        if team in unified['teams']:
            tp = unified['teams'][team].get('tactical', {}).get('tactical_profile', {})
            print(f"{team}: {tp.get('profile', 'N/A')} ({tp.get('confidence', 0)*100:.0f}%)")

    print("\n✅ INTÉGRATION TERMINÉE!")
    print(f"📁 Nouveau fichier: {OUTPUT_FILE}")

    return integrated_count, missing_teams


if __name__ == "__main__":
    integrate_tactical_profiles()
