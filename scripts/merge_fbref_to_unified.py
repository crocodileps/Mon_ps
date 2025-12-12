#!/usr/bin/env python3
"""
FUSION FBREF -> PLAYER_DNA_UNIFIED
Integre les donnees FBRef dans le fichier unifie
"""

import json
import unicodedata
from datetime import datetime
from typing import Dict, Any, Optional
from collections import defaultdict

# Fichiers
FBREF_FILE = '/home/Mon_ps/data/fbref/fbref_players_clean_2025_26.json'
UNIFIED_FILE = '/home/Mon_ps/data/quantum_v2/player_dna_unified.json'
OUTPUT_FILE = '/home/Mon_ps/data/quantum_v2/player_dna_unified.json'

# ============================================================================
# NORMALISATION DES NOMS
# ============================================================================

def normalize_name(name: str) -> str:
    """Normalise un nom pour la correspondance"""
    # Supprimer accents
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    # Lowercase et strip
    return name.lower().strip()


def create_name_variants(name: str) -> list:
    """Cree des variantes d'un nom pour ameliorer le matching"""
    variants = []

    # Nettoyer le nom (enlever _team si present)
    clean_name = name.split('_')[0] if '_' in name else name

    # Version normalisee
    variants.append(normalize_name(clean_name))

    # Si nom compose (prenom nom)
    parts = clean_name.split()
    if len(parts) >= 2:
        # Nom complet
        variants.append(normalize_name(" ".join(parts)))
        # Prenom + dernier nom
        variants.append(normalize_name(parts[0] + " " + parts[-1]))
        # Juste le nom de famille
        variants.append(normalize_name(parts[-1]))
        # Premier + deuxieme (pour noms a 3 parties)
        if len(parts) >= 3:
            variants.append(normalize_name(parts[0] + " " + parts[1]))

    return list(set(v for v in variants if v))


# ============================================================================
# EXTRACTION STATS FBREF
# ============================================================================

def extract_fbref_stats(fbref_player: Dict) -> Dict:
    """Extrait les stats FBRef pertinentes pour le profil unifie"""
    stats = fbref_player.get('stats', {})

    return {
        "source": "fbref",
        "updated_at": datetime.now().isoformat(),
        "position": fbref_player.get('position', ''),
        "team": fbref_player.get('team', ''),
        "nation": fbref_player.get('nation', ''),
        "age": fbref_player.get('age', 0),

        # Stats defensives (cles pour milieux)
        "defense": {
            "tackles": stats.get('tackles', 0),
            "tackles_won": stats.get('tackles_won', 0),
            "tackles_def_third": stats.get('tackles_def_third', 0),
            "tackles_mid_third": stats.get('tackles_mid_third', 0),
            "tackles_att_third": stats.get('tackles_att_third', 0),
            "interceptions": stats.get('interceptions', 0),
            "blocks": stats.get('blocks', 0),
            "clearances": stats.get('clearances', 0),
            "errors": stats.get('errors', 0),
            "tackles_interceptions": stats.get('tackles_interceptions', 0),
        },

        # Possession et progression
        "possession": {
            "touches": stats.get('touches', 0),
            "progressive_carries": stats.get('progressive_carries', 0),
            "carries_final_third": stats.get('carries_final_third', 0),
            "carries_penalty_area": stats.get('carries_penalty_area', 0),
            "take_ons_attempted": stats.get('take_ons_attempted', 0),
            "take_ons_successful": stats.get('take_ons_successful', 0),
            "take_on_success_rate": stats.get('take_on_success_rate', 0),
            "miscontrols": stats.get('miscontrols', 0),
            "dispossessed": stats.get('dispossessed', 0),
        },

        # Passes et creation
        "passing": {
            "passes_completed": stats.get('passes_completed', 0),
            "pass_completion_pct": stats.get('pass_completion_pct', 0),
            "progressive_passes": stats.get('progressive_passes', 0),
            "key_passes": stats.get('key_passes', 0),
            "passes_final_third": stats.get('passes_final_third', 0),
            "passes_penalty_area": stats.get('passes_penalty_area', 0),
            "through_balls": stats.get('through_balls', 0),
            "crosses": stats.get('crosses', 0),
        },

        # Creation de buts/tirs
        "chance_creation": {
            "shot_creating_actions": stats.get('shot_creating_actions', 0),
            "shot_creating_actions_90": stats.get('shot_creating_actions_90', 0),
            "goal_creating_actions": stats.get('goal_creating_actions', 0),
            "goal_creating_actions_90": stats.get('goal_creating_actions_90', 0),
        },

        # Discipline (CRUCIAL pour betting)
        "discipline": {
            "yellow_cards": stats.get('yellow_cards', 0),
            "red_cards": stats.get('red_cards', 0),
            "second_yellow": stats.get('second_yellow', 0),
            "fouls_committed": stats.get('fouls_committed', 0),
            "fouls_drawn": stats.get('fouls_drawn', 0),
            "fouls_ratio": round(stats.get('fouls_committed', 0) / max(stats.get('fouls_drawn', 1), 1), 2),
        },

        # Duels aeriens
        "aerial": {
            "aerials_won": stats.get('aerials_won', 0),
            "aerials_lost": stats.get('aerials_lost', 0),
            "aerial_win_rate": stats.get('aerial_win_rate', 0),
        },

        # Recuperation
        "recovery": {
            "ball_recoveries": stats.get('ball_recoveries', 0),
            "penalties_won": stats.get('penalties_won', 0),
            "penalties_conceded": stats.get('penalties_conceded', 0),
        },

        # Tirs (si attaquant/milieu offensif)
        "shooting": {
            "shots": stats.get('shots', 0),
            "shots_on_target": stats.get('shots_on_target', 0),
            "shot_accuracy": stats.get('shot_accuracy', 0),
            "goals": stats.get('goals', 0),
            "assists": stats.get('assists', 0),
            "xG": stats.get('xG', 0),
            "xA": stats.get('xA', 0),
        },
    }


# ============================================================================
# CALCUL DES METRIQUES DERIVEES
# ============================================================================

def calculate_derived_metrics(fbref_stats: Dict, minutes_90: float) -> Dict:
    """Calcule des metriques par 90 minutes et ratios"""
    if minutes_90 < 1:
        minutes_90 = 1  # Eviter division par zero

    derived = {}

    # Defense per 90
    defense = fbref_stats.get('defense', {})
    derived['tackles_90'] = round(defense.get('tackles', 0) / minutes_90, 2)
    derived['interceptions_90'] = round(defense.get('interceptions', 0) / minutes_90, 2)
    derived['tackles_interceptions_90'] = round(defense.get('tackles_interceptions', 0) / minutes_90, 2)

    # Discipline per 90
    discipline = fbref_stats.get('discipline', {})
    derived['fouls_90'] = round(discipline.get('fouls_committed', 0) / minutes_90, 2)
    derived['cards_90'] = round((discipline.get('yellow_cards', 0) + discipline.get('red_cards', 0)) / minutes_90, 3)

    # Possession per 90
    possession = fbref_stats.get('possession', {})
    derived['progressive_carries_90'] = round(possession.get('progressive_carries', 0) / minutes_90, 2)
    derived['touches_90'] = round(possession.get('touches', 0) / minutes_90, 1)

    # Passing per 90
    passing = fbref_stats.get('passing', {})
    derived['key_passes_90'] = round(passing.get('key_passes', 0) / minutes_90, 2)
    derived['progressive_passes_90'] = round(passing.get('progressive_passes', 0) / minutes_90, 2)

    # Recovery per 90
    recovery = fbref_stats.get('recovery', {})
    derived['ball_recoveries_90'] = round(recovery.get('ball_recoveries', 0) / minutes_90, 2)

    return derived


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("FUSION FBREF -> PLAYER_DNA_UNIFIED")
    print("=" * 70)

    # Charger FBRef
    print("\n1. Chargement FBRef...")
    with open(FBREF_FILE, 'r', encoding='utf-8') as f:
        fbref_data = json.load(f)
    print(f"   Joueurs FBRef: {len(fbref_data['players'])}")

    # Creer index par nom normalise
    fbref_index = {}
    for name, data in fbref_data['players'].items():
        for variant in create_name_variants(name):
            if variant not in fbref_index:
                fbref_index[variant] = (name, data)

    # Charger unified
    print("\n2. Chargement player_dna_unified...")
    with open(UNIFIED_FILE, 'r', encoding='utf-8') as f:
        unified_data = json.load(f)
    print(f"   Joueurs unified: {len(unified_data['players'])}")

    # Stats
    stats = {
        'matched': 0,
        'not_matched': 0,
        'new_players': 0,
        'positions': defaultdict(int),
    }

    # Matcher et fusionner
    print("\n3. Fusion en cours...")

    matched_fbref = set()

    for player_name, player_data in unified_data['players'].items():
        # Chercher dans FBRef
        variants = create_name_variants(player_name)
        match = None

        for variant in variants:
            if variant in fbref_index:
                match = fbref_index[variant]
                break

        if match:
            fbref_name, fbref_player = match
            matched_fbref.add(fbref_name)

            # Extraire stats FBRef
            fbref_stats = extract_fbref_stats(fbref_player)

            # Calculer metriques derivees
            minutes_90 = fbref_player.get('stats', {}).get('minutes_90', 1) or 1
            derived = calculate_derived_metrics(fbref_stats, minutes_90)
            fbref_stats['derived'] = derived

            # Ajouter au joueur
            player_data['fbref'] = fbref_stats

            # Marquer data_completeness (joueur existant + FBRef = full)
            player_data['has_fbref'] = True
            if 'data_completeness' not in player_data:
                player_data['data_completeness'] = 'full'

            stats['matched'] += 1
            stats['positions'][fbref_stats['position']] += 1
        else:
            stats['not_matched'] += 1

    # Ajouter joueurs FBRef non matches comme nouveaux
    print("\n4. Ajout nouveaux joueurs FBRef...")

    for fbref_name, fbref_player in fbref_data['players'].items():
        if fbref_name not in matched_fbref:
            # Nouveau joueur (FBRef only = partial)
            fbref_stats = extract_fbref_stats(fbref_player)
            minutes_90 = fbref_player.get('stats', {}).get('minutes_90', 1) or 1
            derived = calculate_derived_metrics(fbref_stats, minutes_90)
            fbref_stats['derived'] = derived

            # Creer entree avec tracking completeness
            unified_data['players'][fbref_name] = {
                'meta': {
                    'name': fbref_name,
                    'team': fbref_player.get('team', ''),
                    'league': fbref_player.get('league', ''),
                    'position': fbref_player.get('position', ''),
                },
                'fbref': fbref_stats,
                # HEDGE FUND GRADE: tracking data completeness
                'source': 'fbref_2025_26',
                'data_completeness': 'partial',
                'has_fbref': True,
                'missing_sources': ['understat', 'sofascore'],
                'needs_enrichment': True,
                'created_at': datetime.now().isoformat()
            }

            stats['new_players'] += 1
            stats['positions'][fbref_stats['position']] += 1

    # Mettre a jour metadata
    if 'metadata' not in unified_data:
        unified_data['metadata'] = {}

    unified_data['metadata']['fbref_merge'] = {
        'merged_at': datetime.now().isoformat(),
        'fbref_source': FBREF_FILE,
        'stats': {
            'matched': stats['matched'],
            'not_matched': stats['not_matched'],
            'new_players': stats['new_players'],
            'total_with_fbref': stats['matched'] + stats['new_players'],
            'partial_players': stats['new_players'],  # FBRef-only need enrichment
            'full_players': stats['matched']  # Matched with existing = full
        }
    }

    # Sauvegarder
    print("\n5. Sauvegarde...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(unified_data, f, indent=2, ensure_ascii=False)

    # Resume
    print("\n" + "=" * 70)
    print("FUSION TERMINEE")
    print("=" * 70)

    print(f"\nResultats:")
    print(f"   Joueurs matches: {stats['matched']}")
    print(f"   Non matches: {stats['not_matched']}")
    print(f"   Nouveaux joueurs: {stats['new_players']}")
    print(f"   Total avec FBRef: {stats['matched'] + stats['new_players']}")

    print(f"\nPositions fusionnees:")
    for pos, count in sorted(stats['positions'].items(), key=lambda x: -x[1])[:8]:
        print(f"   {pos}: {count}")

    print(f"\nFichier: {OUTPUT_FILE}")

    import os
    file_size = os.path.getsize(OUTPUT_FILE) / (1024*1024)
    print(f"Taille: {file_size:.1f} MB")


if __name__ == "__main__":
    main()
