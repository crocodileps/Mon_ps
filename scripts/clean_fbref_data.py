#!/usr/bin/env python3
"""
Nettoyage et restructuration des donnees FBRef
Extrait les champs utiles avec noms propres
"""

import json
import re
from datetime import datetime
from typing import Dict, Any

INPUT_FILE = '/home/Mon_ps/data/fbref/fbref_players_complete_2025_26.json'
OUTPUT_FILE = '/home/Mon_ps/data/fbref/fbref_players_clean_2025_26.json'

# Mapping des colonnes FBRef vers noms propres
COLUMN_MAPPING = {
    # Standard
    'Playing Time_MP': 'matches_played',
    'Playing Time_Starts': 'starts',
    'Playing Time_Min': 'minutes',
    'Playing Time_90s': 'minutes_90',
    'Performance_Gls': 'goals',
    'Performance_Ast': 'assists',
    'Performance_G+A': 'goals_assists',
    'Performance_G-PK': 'non_penalty_goals',
    'Performance_PK': 'penalty_goals',
    'Performance_PKatt': 'penalty_attempts',
    'Performance_CrdY': 'yellow_cards',
    'Performance_CrdR': 'red_cards',
    'Expected_xG': 'xG',
    'Expected_npxG': 'npxG',
    'Expected_xAG': 'xA',
    'Expected_npxG+xAG': 'npxG_xA',
    'Per 90 Minutes_Gls': 'goals_90',
    'Per 90 Minutes_Ast': 'assists_90',
    'Per 90 Minutes_G+A': 'goals_assists_90',
    'Per 90 Minutes_G-PK': 'npg_90',
    'Per 90 Minutes_G+A-PK': 'npg_a_90',
    'Per 90 Minutes_xG': 'xG_90',
    'Per 90 Minutes_xAG': 'xA_90',

    # Shooting
    'Standard_Sh': 'shots',
    'Standard_SoT': 'shots_on_target',
    'Standard_SoT%': 'shot_accuracy',
    'Standard_Sh/90': 'shots_90',
    'Standard_SoT/90': 'shots_on_target_90',
    'Standard_G/Sh': 'goals_per_shot',
    'Standard_G/SoT': 'goals_per_shot_on_target',
    'Standard_Dist': 'avg_shot_distance',
    'Standard_FK': 'free_kick_shots',
    'Standard_PK': 'penalty_kicks_made',
    'Standard_PKatt': 'penalty_kicks_attempted',
    'Expected_npxG/Sh': 'npxG_per_shot',
    'Expected_G-xG': 'goals_minus_xG',
    'Expected_np:G-xG': 'npg_minus_npxG',

    # Passing
    'Total_Cmp': 'passes_completed',
    'Total_Att': 'passes_attempted',
    'Total_Cmp%': 'pass_completion_pct',
    'Total_TotDist': 'pass_distance',
    'Total_PrgDist': 'progressive_pass_distance',
    'Short_Cmp': 'short_passes_completed',
    'Short_Att': 'short_passes_attempted',
    'Short_Cmp%': 'short_pass_completion',
    'Medium_Cmp': 'medium_passes_completed',
    'Medium_Att': 'medium_passes_attempted',
    'Medium_Cmp%': 'medium_pass_completion',
    'Long_Cmp': 'long_passes_completed',
    'Long_Att': 'long_passes_attempted',
    'Long_Cmp%': 'long_pass_completion',
    'Unnamed: 22_level_0_Ast': 'assists_passing',
    'Unnamed: 23_level_0_xAG': 'xA_passing',
    'Expected_xA': 'expected_assists',
    'Unnamed: 25_level_0_A-xAG': 'assists_minus_xA',
    'Unnamed: 26_level_0_KP': 'key_passes',
    'Unnamed: 27_level_0_1/3': 'passes_final_third',
    'Unnamed: 28_level_0_PPA': 'passes_penalty_area',
    'Unnamed: 29_level_0_CrsPA': 'crosses_penalty_area',
    'Unnamed: 30_level_0_PrgP': 'progressive_passes',

    # Pass Types
    'Pass Types_Live': 'live_ball_passes',
    'Pass Types_Dead': 'dead_ball_passes',
    'Pass Types_FK': 'free_kick_passes',
    'Pass Types_TB': 'through_balls',
    'Pass Types_Sw': 'switches',
    'Pass Types_Crs': 'crosses',
    'Pass Types_TI': 'throw_ins',
    'Pass Types_CK': 'corner_kicks',
    'Corner Kicks_In': 'corner_kicks_inswing',
    'Corner Kicks_Out': 'corner_kicks_outswing',
    'Corner Kicks_Str': 'corner_kicks_straight',
    'Outcomes_Cmp': 'passes_completed_types',
    'Outcomes_Off': 'passes_offside',
    'Outcomes_Blocks': 'passes_blocked',

    # GCA (Goal/Shot Creating Actions)
    'SCA_SCA': 'shot_creating_actions',
    'SCA_SCA90': 'shot_creating_actions_90',
    'SCA Types_PassLive': 'sca_live_pass',
    'SCA Types_PassDead': 'sca_dead_pass',
    'SCA Types_TO': 'sca_take_on',
    'SCA Types_Sh': 'sca_shot',
    'SCA Types_Fld': 'sca_foul_drawn',
    'SCA Types_Def': 'sca_defensive',
    'GCA_GCA': 'goal_creating_actions',
    'GCA_GCA90': 'goal_creating_actions_90',
    'GCA Types_PassLive': 'gca_live_pass',
    'GCA Types_PassDead': 'gca_dead_pass',
    'GCA Types_TO': 'gca_take_on',
    'GCA Types_Sh': 'gca_shot',
    'GCA Types_Fld': 'gca_foul_drawn',
    'GCA Types_Def': 'gca_defensive',

    # Defense
    'Tackles_Tkl': 'tackles',
    'Tackles_TklW': 'tackles_won',
    'Tackles_Def 3rd': 'tackles_def_third',
    'Tackles_Mid 3rd': 'tackles_mid_third',
    'Tackles_Att 3rd': 'tackles_att_third',
    'Challenges_Tkl': 'challenges_tackled',
    'Challenges_Att': 'challenges_attempted',
    'Challenges_Tkl%': 'challenge_success_rate',
    'Challenges_Lost': 'challenges_lost',
    'Blocks_Blocks': 'blocks',
    'Blocks_Sh': 'shots_blocked',
    'Blocks_Pass': 'passes_blocked_def',
    'Unnamed: 20_level_0_Int': 'interceptions',
    'Unnamed: 21_level_0_Tkl+Int': 'tackles_interceptions',
    'Unnamed: 22_level_0_Clr': 'clearances',
    'Unnamed: 23_level_0_Err': 'errors',

    # Possession
    'Touches_Touches': 'touches',
    'Touches_Def Pen': 'touches_def_pen',
    'Touches_Def 3rd': 'touches_def_third',
    'Touches_Mid 3rd': 'touches_mid_third',
    'Touches_Att 3rd': 'touches_att_third',
    'Touches_Att Pen': 'touches_att_pen',
    'Touches_Live': 'touches_live',
    'Take-Ons_Att': 'take_ons_attempted',
    'Take-Ons_Succ': 'take_ons_successful',
    'Take-Ons_Succ%': 'take_on_success_rate',
    'Take-Ons_Tkld': 'take_ons_tackled',
    'Take-Ons_Tkld%': 'take_ons_tackled_pct',
    'Carries_Carries': 'carries',
    'Carries_TotDist': 'carry_distance',
    'Carries_PrgDist': 'progressive_carry_distance',
    'Carries_PrgC': 'progressive_carries',
    'Carries_1/3': 'carries_final_third',
    'Carries_CPA': 'carries_penalty_area',
    'Carries_Mis': 'miscontrols',
    'Carries_Dis': 'dispossessed',
    'Receiving_Rec': 'passes_received',
    'Receiving_PrgR': 'progressive_passes_received',

    # Misc
    'Performance_2CrdY': 'second_yellow',
    'Performance_Fls': 'fouls_committed',
    'Performance_Fld': 'fouls_drawn',
    'Performance_Off': 'offsides',
    'Performance_Crs': 'crosses_misc',
    'Performance_Int': 'interceptions_misc',
    'Performance_TklW': 'tackles_won_misc',
    'Performance_PKwon': 'penalties_won',
    'Performance_PKcon': 'penalties_conceded',
    'Performance_OG': 'own_goals',
    'Performance_Recov': 'ball_recoveries',
    'Aerial Duels_Won': 'aerials_won',
    'Aerial Duels_Lost': 'aerials_lost',
    'Aerial Duels_Won%': 'aerial_win_rate',
}


def extract_position(player_data: Dict) -> str:
    """Extrait la position depuis les donnees de table"""
    for table_name in ['standard', 'defense', 'misc', 'shooting']:
        table = player_data.get(table_name, {})
        for key, value in table.items():
            if 'Pos' in key and value and isinstance(value, str):
                # Nettoyer la position
                pos = value.strip()
                if pos and pos not in ['Pos', 'Position']:
                    return pos
    return ""


def extract_nation(player_data: Dict) -> str:
    """Extrait la nationalite depuis les donnees de table"""
    for table_name in ['standard', 'defense', 'misc']:
        table = player_data.get(table_name, {})
        for key, value in table.items():
            if 'Nation' in key and value and isinstance(value, str):
                # Format: "fr FRA" -> "FRA"
                parts = value.strip().split()
                if len(parts) >= 2:
                    return parts[-1]
                return value.strip()
    return ""


def extract_age(player_data: Dict) -> int:
    """Extrait l'age depuis les donnees de table"""
    for table_name in ['standard', 'defense', 'misc']:
        table = player_data.get(table_name, {})
        for key, value in table.items():
            if 'Age' in key and value:
                try:
                    # Format: "31-095" -> 31
                    if isinstance(value, str) and '-' in value:
                        return int(value.split('-')[0])
                    return int(float(value))
                except:
                    pass
    return 0


def clean_column_name(col: str) -> str:
    """Nettoie un nom de colonne FBRef"""
    # Utiliser le mapping si disponible
    if col in COLUMN_MAPPING:
        return COLUMN_MAPPING[col]

    # Sinon nettoyer manuellement
    # Enlever les prefixes Unnamed
    col = re.sub(r'Unnamed: \d+_level_\d+_', '', col)
    # Convertir en snake_case
    col = col.replace(' ', '_').replace('-', '_').lower()
    col = re.sub(r'[^\w]', '', col)
    return col


def clean_player_data(player_name: str, raw_data: Dict) -> Dict:
    """Nettoie et restructure les donnees d'un joueur"""

    cleaned = {
        "name": player_name,
        "team": raw_data.get("team", ""),
        "league": raw_data.get("league", ""),
        "position": extract_position(raw_data),
        "nation": extract_nation(raw_data),
        "age": extract_age(raw_data),
    }

    # Stats consolidees
    stats = {}

    # Parcourir chaque table
    for table_name in ['standard', 'shooting', 'passing', 'pass_types', 'gca', 'defense', 'possession', 'misc']:
        table_data = raw_data.get(table_name, {})

        for raw_col, value in table_data.items():
            # Skip colonnes inutiles
            if 'Rk' in raw_col or 'Matches' in raw_col or 'Born' in raw_col:
                continue
            if 'Nation' in raw_col or 'Age' in raw_col or 'Pos' in raw_col:
                continue
            if '90s' in raw_col and 'level_0' in raw_col:
                continue  # Skip les doublons de 90s

            # Nettoyer le nom de colonne
            clean_col = clean_column_name(raw_col)

            if clean_col and value is not None:
                # Convertir en nombre si possible
                try:
                    if isinstance(value, str):
                        value = value.replace(',', '').replace('%', '')
                        if value:
                            value = float(value)
                except:
                    pass

                # Eviter les doublons (garder la premiere valeur)
                if clean_col not in stats:
                    stats[clean_col] = value

    cleaned["stats"] = stats

    return cleaned


def main():
    print("=" * 70)
    print("NETTOYAGE DONNEES FBREF")
    print("=" * 70)

    # Charger donnees brutes
    print("\nChargement des donnees brutes...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    print(f"Joueurs bruts: {len(raw_data['players'])}")

    # Nettoyer
    print("\nNettoyage en cours...")

    cleaned_data = {
        "metadata": {
            "source": "FBRef",
            "season": "2025-26",
            "cleaned_at": datetime.now().isoformat(),
            "original_scrape": raw_data['metadata']['scraped_date'],
            "leagues": raw_data['metadata']['leagues'],
            "tables": raw_data['metadata']['tables']
        },
        "players": {}
    }

    # Stats par position
    positions = {}
    leagues = {}

    for player_name, player_data in raw_data['players'].items():
        cleaned = clean_player_data(player_name, player_data)
        cleaned_data['players'][player_name] = cleaned

        # Comptage
        pos = cleaned['position']
        if pos:
            positions[pos] = positions.get(pos, 0) + 1

        league = cleaned['league']
        leagues[league] = leagues.get(league, 0) + 1

    # Sauvegarder
    print("\nSauvegarde...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, indent=2, ensure_ascii=False)

    # Resume
    print("\n" + "=" * 70)
    print("NETTOYAGE TERMINE")
    print("=" * 70)

    print(f"\nJoueurs nettoyes: {len(cleaned_data['players'])}")

    print(f"\nPositions:")
    for pos, count in sorted(positions.items(), key=lambda x: -x[1])[:10]:
        print(f"  {pos}: {count}")

    print(f"\nPar ligue:")
    for league, count in sorted(leagues.items(), key=lambda x: -x[1]):
        print(f"  {league}: {count}")

    # Exemple
    print("\n=== EXEMPLE JOUEUR NETTOYE ===")
    for name, data in cleaned_data['players'].items():
        if 'fernandes' in name.lower() and 'bruno' in name.lower():
            print(f"\n{data['name']}")
            print(f"  Team: {data['team']}")
            print(f"  Position: {data['position']}")
            print(f"  Nation: {data['nation']}")
            print(f"  Age: {data['age']}")
            print(f"\n  Stats cles:")
            for key in ['tackles', 'interceptions', 'fouls_committed', 'yellow_cards',
                       'progressive_carries', 'key_passes', 'ball_recoveries', 'aerial_win_rate']:
                val = data['stats'].get(key)
                if val is not None:
                    print(f"    {key}: {val}")
            break

    import os
    file_size = os.path.getsize(OUTPUT_FILE) / (1024*1024)
    print(f"\nFichier: {OUTPUT_FILE}")
    print(f"Taille: {file_size:.1f} MB")


if __name__ == "__main__":
    main()
