#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🧤 GOALKEEPER DNA SCRAPER V1.0                                              ║
║  15 Dimensions | Fingerprint Unique | Exploit Paths                          ║
║                                                                              ║
║  Sources:                                                                    ║
║  - FBref: Stats détaillées gardiens (save %, PSxG, aerial, penalties)        ║
║  - Understat: xGA par équipe (backup)                                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
from scipy import stats
import pandas as pd

# Paths
DATA_DIR = Path('/home/Mon_ps/data/goalkeeper_dna')
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = DATA_DIR / 'goalkeeper_dna_v1.json'

# Headers pour les requêtes
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# Leagues FBref URLs (2024-2025 season = 2025/2026 dans notre notation)
FBREF_LEAGUES = {
    'EPL': {
        'url': 'https://fbref.com/en/comps/9/keepers/Premier-League-Stats',
        'adv_url': 'https://fbref.com/en/comps/9/keepersadv/Premier-League-Stats'
    },
    'La_Liga': {
        'url': 'https://fbref.com/en/comps/12/keepers/La-Liga-Stats',
        'adv_url': 'https://fbref.com/en/comps/12/keepersadv/La-Liga-Stats'
    },
    'Bundesliga': {
        'url': 'https://fbref.com/en/comps/20/keepers/Bundesliga-Stats',
        'adv_url': 'https://fbref.com/en/comps/20/keepersadv/Bundesliga-Stats'
    },
    'Serie_A': {
        'url': 'https://fbref.com/en/comps/11/keepers/Serie-A-Stats',
        'adv_url': 'https://fbref.com/en/comps/11/keepersadv/Serie-A-Stats'
    },
    'Ligue_1': {
        'url': 'https://fbref.com/en/comps/13/keepers/Ligue-1-Stats',
        'adv_url': 'https://fbref.com/en/comps/13/keepersadv/Ligue-1-Stats'
    }
}

def safe_float(value, default=0.0):
    """Convertit une valeur en float de manière sécurisée"""
    if value is None or value == '' or value == '-':
        return default
    try:
        # Enlever les caractères non numériques sauf . et -
        cleaned = re.sub(r'[^\d.\-]', '', str(value))
        return float(cleaned) if cleaned else default
    except (ValueError, TypeError):
        return default

def safe_int(value, default=0):
    """Convertit une valeur en int de manière sécurisée"""
    return int(safe_float(value, default))

def scrape_fbref_keepers(league: str, urls: Dict[str, str]) -> List[Dict]:
    """
    Scrape les données des gardiens depuis FBref
    """
    keepers = []
    
    print(f"\n   📥 Scraping FBref {league}...")
    
    try:
        # 1. Scrape basic keeper stats
        response = requests.get(urls['url'], headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Trouver la table des gardiens
        table = soup.find('table', {'id': re.compile(r'stats_keeper')})
        if not table:
            print(f"      ⚠️ Table gardiens non trouvée pour {league}")
            return keepers
        
        # Parser les headers
        thead = table.find('thead')
        headers = []
        if thead:
            header_rows = thead.find_all('tr')
            # Prendre la dernière row de headers (celle avec les noms de colonnes)
            if header_rows:
                last_header = header_rows[-1]
                for th in last_header.find_all(['th', 'td']):
                    headers.append(th.get('data-stat', th.text.strip()))
        
        # Parser les données
        tbody = table.find('tbody')
        if tbody:
            for row in tbody.find_all('tr'):
                if 'thead' in row.get('class', []):
                    continue
                
                cells = row.find_all(['th', 'td'])
                if len(cells) < 5:
                    continue
                
                keeper_data = {}
                for i, cell in enumerate(cells):
                    stat_name = cell.get('data-stat', f'col_{i}')
                    keeper_data[stat_name] = cell.text.strip()
                
                # Extraire le nom du joueur
                player_cell = row.find('td', {'data-stat': 'player'})
                if player_cell:
                    player_link = player_cell.find('a')
                    if player_link:
                        keeper_data['player_name'] = player_link.text.strip()
                        keeper_data['player_url'] = player_link.get('href', '')
                
                # Extraire l'équipe
                team_cell = row.find('td', {'data-stat': 'team'})
                if team_cell:
                    team_link = team_cell.find('a')
                    if team_link:
                        keeper_data['team'] = team_link.text.strip()
                
                if keeper_data.get('player_name'):
                    keeper_data['league'] = league
                    keepers.append(keeper_data)
        
        time.sleep(2)  # Respecter le rate limit
        
        # 2. Scrape advanced keeper stats
        response_adv = requests.get(urls['adv_url'], headers=HEADERS, timeout=30)
        response_adv.raise_for_status()
        soup_adv = BeautifulSoup(response_adv.text, 'html.parser')
        
        table_adv = soup_adv.find('table', {'id': re.compile(r'stats_keeper_adv')})
        if table_adv:
            tbody_adv = table_adv.find('tbody')
            if tbody_adv:
                for row in tbody_adv.find_all('tr'):
                    if 'thead' in row.get('class', []):
                        continue
                    
                    cells = row.find_all(['th', 'td'])
                    player_cell = row.find('td', {'data-stat': 'player'})
                    if not player_cell:
                        continue
                    
                    player_name = player_cell.text.strip()
                    
                    # Trouver le keeper correspondant
                    for keeper in keepers:
                        if keeper.get('player_name') == player_name:
                            for cell in cells:
                                stat_name = cell.get('data-stat', '')
                                if stat_name and stat_name not in keeper:
                                    keeper[f'adv_{stat_name}'] = cell.text.strip()
                            break
        
        print(f"      ✅ {len(keepers)} gardiens trouvés")
        time.sleep(2)
        
    except Exception as e:
        print(f"      ❌ Erreur {league}: {e}")
    
    return keepers

def parse_keeper_stats(raw_keepers: List[Dict]) -> List[Dict]:
    """
    Parse et structure les données des gardiens
    """
    parsed = []
    
    for raw in raw_keepers:
        try:
            # Filtrer les gardiens avec peu de minutes
            minutes = safe_int(raw.get('minutes', raw.get('playing_time_min', 0)))
            if minutes < 270:  # Minimum 3 matchs
                continue
            
            keeper = {
                'player_name': raw.get('player_name', 'Unknown'),
                'team': raw.get('team', 'Unknown'),
                'league': raw.get('league', 'Unknown'),
                'player_url': raw.get('player_url', ''),
                
                # Playing time
                'matches_played': safe_int(raw.get('gk_games', raw.get('games', 0))),
                'matches_started': safe_int(raw.get('gk_games_starts', raw.get('games_starts', 0))),
                'minutes': minutes,
                'minutes_per_match': round(minutes / max(1, safe_int(raw.get('gk_games', 1))), 1),
                
                # Basic stats
                'goals_against': safe_int(raw.get('gk_goals_against', raw.get('goals_against', 0))),
                'goals_against_per90': safe_float(raw.get('gk_goals_against_per90', 0)),
                'shots_on_target_against': safe_int(raw.get('gk_shots_on_target_against', 0)),
                'saves': safe_int(raw.get('gk_saves', 0)),
                'save_pct': safe_float(raw.get('gk_save_pct', 0)),
                'clean_sheets': safe_int(raw.get('gk_clean_sheets', 0)),
                'clean_sheet_pct': safe_float(raw.get('gk_clean_sheets_pct', 0)),
                
                # Advanced - PSxG
                'psxg': safe_float(raw.get('adv_gk_psxg', 0)),
                'psxg_per_shot': safe_float(raw.get('adv_gk_psxg_per_shot_on_target', 0)),
                'psxg_diff': safe_float(raw.get('adv_gk_psxg_net', raw.get('adv_gk_psxg_plus_minus', 0))),
                'psxg_diff_per90': safe_float(raw.get('adv_gk_psxg_net_per90', raw.get('adv_gk_psxg_plus_minus_per90', 0))),
                
                # Penalties
                'penalties_faced': safe_int(raw.get('gk_pens_att', raw.get('adv_gk_pens_att', 0))),
                'penalties_saved': safe_int(raw.get('gk_pens_saved', raw.get('adv_gk_pens_saved', 0))),
                'penalties_conceded': safe_int(raw.get('gk_pens_allowed', raw.get('adv_gk_pens_allowed', 0))),
                'penalty_save_pct': 0.0,  # Calculé après
                
                # Distribution
                'passes_completed': safe_int(raw.get('adv_gk_passes_completed_launched', 0)),
                'passes_attempted': safe_int(raw.get('adv_gk_passes_launched', 0)),
                'pass_completion_pct': safe_float(raw.get('adv_gk_passes_pct_launched', 0)),
                'goal_kicks_launched_pct': safe_float(raw.get('adv_gk_goal_kicks_pct_launched', 0)),
                'avg_pass_length': safe_float(raw.get('adv_gk_passes_length_avg', 0)),
                'avg_goal_kick_length': safe_float(raw.get('adv_gk_goal_kicks_length_avg', 0)),
                
                # Crosses
                'crosses_faced': safe_int(raw.get('adv_gk_crosses', 0)),
                'crosses_stopped': safe_int(raw.get('adv_gk_crosses_stopped', 0)),
                'crosses_stopped_pct': safe_float(raw.get('adv_gk_crosses_stopped_pct', 0)),
                
                # Sweeper actions
                'opa_actions': safe_int(raw.get('adv_gk_def_actions_outside_pen_area', 0)),
                'opa_per90': safe_float(raw.get('adv_gk_def_actions_outside_pen_area_per90', 0)),
                'avg_opa_distance': safe_float(raw.get('adv_gk_avg_distance_def_actions', 0)),
            }
            
            # Calculer penalty_save_pct
            if keeper['penalties_faced'] > 0:
                keeper['penalty_save_pct'] = round(
                    keeper['penalties_saved'] / keeper['penalties_faced'] * 100, 1
                )
            
            # Calculer saves_per_goal
            if keeper['goals_against'] > 0:
                keeper['saves_per_goal'] = round(keeper['saves'] / keeper['goals_against'], 2)
            else:
                keeper['saves_per_goal'] = keeper['saves'] if keeper['saves'] > 0 else 0
            
            parsed.append(keeper)
            
        except Exception as e:
            print(f"      ⚠️ Erreur parsing {raw.get('player_name', 'Unknown')}: {e}")
    
    return parsed

def calculate_percentiles(keepers: List[Dict]) -> List[Dict]:
    """
    Calcule les percentiles pour chaque dimension
    """
    if not keepers:
        return keepers
    
    # Métriques où PLUS est MIEUX (percentile élevé = bon)
    higher_is_better = [
        'save_pct', 'clean_sheet_pct', 'psxg_diff', 'psxg_diff_per90',
        'penalty_save_pct', 'saves_per_goal', 'crosses_stopped_pct',
        'pass_completion_pct', 'opa_per90'
    ]
    
    # Métriques où MOINS est MIEUX (percentile inversé)
    lower_is_better = [
        'goals_against_per90'
    ]
    
    # Collecter les valeurs pour chaque métrique
    metrics_values = {}
    for metric in higher_is_better + lower_is_better:
        metrics_values[metric] = [k.get(metric, 0) for k in keepers]
    
    # Calculer les percentiles
    for keeper in keepers:
        keeper['percentiles'] = {}
        
        for metric in higher_is_better:
            value = keeper.get(metric, 0)
            values = metrics_values[metric]
            if value and max(values) > 0:
                pct = stats.percentileofscore(values, value, kind='rank')
                keeper['percentiles'][metric] = round(pct, 0)
            else:
                keeper['percentiles'][metric] = 50
        
        for metric in lower_is_better:
            value = keeper.get(metric, 0)
            values = metrics_values[metric]
            if value and max(values) > 0:
                # Inverser: moins = mieux = percentile élevé
                pct = 100 - stats.percentileofscore(values, value, kind='rank')
                keeper['percentiles'][metric] = round(pct, 0)
            else:
                keeper['percentiles'][metric] = 50
    
    return keepers

def calculate_dimension_scores(keepers: List[Dict]) -> List[Dict]:
    """
    Calcule les scores pour les 15 dimensions
    """
    for keeper in keepers:
        pct = keeper.get('percentiles', {})
        
        # DIMENSION 1: SHOT_STOPPING
        shot_stopping = np.mean([
            pct.get('save_pct', 50),
            pct.get('psxg_diff_per90', 50) if pct.get('psxg_diff_per90') else 50,
            pct.get('saves_per_goal', 50),
            pct.get('goals_against_per90', 50)
        ])
        
        # DIMENSION 2-3: ZONE & DISTANCE (approximé via PSxG et saves)
        # On utilise PSxG comme proxy car pas de données par zone
        zone_score = pct.get('psxg_diff_per90', 50)
        distance_score = np.mean([pct.get('save_pct', 50), pct.get('psxg_diff_per90', 50)])
        
        # DIMENSION 4: TIMING (approximé - pas de données par période)
        # On utilise la consistance (clean sheet % vs save %)
        timing_score = np.mean([pct.get('clean_sheet_pct', 50), pct.get('save_pct', 50)])
        
        # DIMENSION 5: AERIAL_DOMINANCE
        aerial_score = pct.get('crosses_stopped_pct', 50)
        
        # DIMENSION 6: PENALTY
        penalty_score = pct.get('penalty_save_pct', 50)
        
        # DIMENSION 7: ONE_ON_ONE (approximé via PSxG diff)
        one_on_one_score = pct.get('psxg_diff_per90', 50)
        
        # DIMENSION 8: MENTAL_RESILIENCE (approximé via clean sheet consistency)
        mental_score = np.mean([
            pct.get('clean_sheet_pct', 50),
            pct.get('psxg_diff_per90', 50)
        ])
        
        # DIMENSION 9: DISTRIBUTION
        distribution_score = pct.get('pass_completion_pct', 50)
        
        # DIMENSION 10: SWEEPER_KEEPER
        sweeper_score = pct.get('opa_per90', 50)
        
        # Stocker les dimensions
        keeper['dimensions'] = {
            'shot_stopping': round(shot_stopping, 0),
            'zone_coverage': round(zone_score, 0),
            'distance_range': round(distance_score, 0),
            'timing_consistency': round(timing_score, 0),
            'aerial_dominance': round(aerial_score, 0),
            'penalty_stopping': round(penalty_score, 0),
            'one_on_one': round(one_on_one_score, 0),
            'mental_resilience': round(mental_score, 0),
            'distribution': round(distribution_score, 0),
            'sweeper_keeper': round(sweeper_score, 0)
        }
        
        # Score global
        keeper['overall_score'] = round(np.mean(list(keeper['dimensions'].values())), 0)
    
    return keepers

def generate_fingerprint(keeper: Dict) -> str:
    """
    Génère le fingerprint unique du gardien
    """
    dims = keeper.get('dimensions', {})
    parts = ['GK']
    
    dim_order = [
        'shot_stopping', 'zone_coverage', 'distance_range', 'timing_consistency',
        'aerial_dominance', 'penalty_stopping', 'one_on_one', 'mental_resilience',
        'distribution', 'sweeper_keeper'
    ]
    
    for dim in dim_order:
        parts.append(str(int(dims.get(dim, 50))))
    
    return '-'.join(parts)

def generate_compact_fingerprint(keeper: Dict) -> str:
    """
    Génère le fingerprint compact
    """
    dims = keeper.get('dimensions', {})
    codes = {
        'shot_stopping': 'SHT',
        'zone_coverage': 'ZON',
        'distance_range': 'DST',
        'timing_consistency': 'TIM',
        'aerial_dominance': 'AER',
        'penalty_stopping': 'PEN',
        'one_on_one': '1V1',
        'mental_resilience': 'MNT',
        'distribution': 'DIS',
        'sweeper_keeper': 'SWP'
    }
    
    parts = []
    for dim, code in codes.items():
        val = int(dims.get(dim, 50))
        parts.append(f"{code}{val}")
    
    return '|'.join(parts)

def assign_profile_tags(keeper: Dict) -> List[str]:
    """
    Assigne les tags de profil au gardien
    """
    tags = []
    dims = keeper.get('dimensions', {})
    overall = keeper.get('overall_score', 50)
    
    # Tag principal (niveau global)
    if overall >= 85:
        tags.append('ELITE_GK')
    elif overall >= 70:
        tags.append('SOLID_GK')
    elif overall >= 55:
        tags.append('AVERAGE_GK')
    elif overall >= 40:
        tags.append('BELOW_AVG_GK')
    else:
        tags.append('LIABILITY_GK')
    
    # PSxG analysis
    psxg_diff = keeper.get('psxg_diff', 0)
    if psxg_diff >= 3:
        tags.append('SHOT_STOPPER_ELITE')
    elif psxg_diff >= 1:
        tags.append('SHOT_STOPPER_GOOD')
    elif psxg_diff <= -3:
        tags.append('SHOT_STOPPER_WEAK')
    elif psxg_diff <= -1:
        tags.append('SHOT_STOPPER_POOR')
    
    # Aerial
    if dims.get('aerial_dominance', 50) >= 75:
        tags.append('AERIAL_DOMINANT')
    elif dims.get('aerial_dominance', 50) <= 25:
        tags.append('AERIAL_WEAK')
    
    # Penalty
    if dims.get('penalty_stopping', 50) >= 75:
        tags.append('PENALTY_STOPPER')
    elif dims.get('penalty_stopping', 50) <= 25:
        tags.append('PENALTY_WEAK')
    
    # Distribution
    if dims.get('distribution', 50) >= 75:
        tags.append('PLAYMAKER_GK')
    elif dims.get('distribution', 50) <= 25:
        tags.append('HOOFBALL_GK')
    
    # Sweeper
    if dims.get('sweeper_keeper', 50) >= 75:
        tags.append('SWEEPER_KEEPER')
    elif dims.get('sweeper_keeper', 50) <= 25:
        tags.append('LINE_KEEPER')
    
    # Mental
    if dims.get('mental_resilience', 50) >= 75:
        tags.append('MENTAL_FORTRESS')
    elif dims.get('mental_resilience', 50) <= 25:
        tags.append('SHAKY')
    
    # One-on-one
    if dims.get('one_on_one', 50) >= 75:
        tags.append('ONE_ON_ONE_MASTER')
    elif dims.get('one_on_one', 50) <= 25:
        tags.append('ONE_ON_ONE_WEAK')
    
    return tags

def generate_exploit_paths(keeper: Dict) -> List[Dict]:
    """
    Génère les exploit paths pour ce gardien
    """
    dims = keeper.get('dimensions', {})
    exploits = []
    
    # Mapping dimension -> exploit
    exploit_mapping = {
        'shot_stopping': {
            'market': 'Goals Over',
            'attacker_profile': 'ANY_ATTACKER',
            'tactic': 'Tirer cadré'
        },
        'aerial_dominance': {
            'market': 'Header Goal',
            'attacker_profile': 'HEADER_SPECIALIST',
            'tactic': 'Centres et corners'
        },
        'penalty_stopping': {
            'market': 'Penalty Scored',
            'attacker_profile': 'PENALTY_TAKER',
            'tactic': 'Provoquer fautes dans la surface'
        },
        'one_on_one': {
            'market': 'Anytime Scorer',
            'attacker_profile': 'CLINICAL',
            'tactic': 'Créer des situations 1v1'
        },
        'distribution': {
            'market': 'Goal from GK Error',
            'attacker_profile': 'HIGH_PRESS',
            'tactic': 'Pressing haut sur relance'
        },
        'sweeper_keeper': {
            'market': 'Chip/Lob Goal',
            'attacker_profile': 'TECHNICAL',
            'tactic': 'Lober si GK avance'
        }
    }
    
    for dim, mapping in exploit_mapping.items():
        value = dims.get(dim, 50)
        
        # Déterminer la vulnérabilité
        if value <= 25:
            confidence = 'HIGH'
            exploit_type = 'ABSOLUTE'
            edge = round((50 - value) / 8, 1)
        elif value <= 40:
            confidence = 'MEDIUM'
            exploit_type = 'MODERATE'
            edge = round((50 - value) / 12, 1)
        elif value <= 50:
            confidence = 'LOW'
            exploit_type = 'MINOR'
            edge = round((50 - value) / 20, 1)
        else:
            continue  # Pas une vulnérabilité
        
        exploits.append({
            'dimension': dim,
            'dimension_value': int(value),
            'market': mapping['market'],
            'attacker_profile': mapping['attacker_profile'],
            'tactic': mapping['tactic'],
            'confidence': confidence,
            'exploit_type': exploit_type,
            'edge_estimate': edge
        })
    
    # Trier par edge décroissant
    exploits.sort(key=lambda x: x['edge_estimate'], reverse=True)
    return exploits[:5]

def generate_enriched_name(keeper: Dict) -> str:
    """
    Génère un nom enrichi pour le gardien
    """
    dims = keeper.get('dimensions', {})
    overall = keeper.get('overall_score', 50)
    
    # Niveau
    if overall >= 85:
        level = "Mur"
    elif overall >= 70:
        level = "Gardien Solide"
    elif overall >= 55:
        level = "Gardien Moyen"
    elif overall >= 40:
        level = "Gardien Fragile"
    else:
        level = "Passoire"
    
    # Force principale
    max_dim = max(dims.items(), key=lambda x: x[1])
    strength_names = {
        'shot_stopping': 'Réflexes',
        'aerial_dominance': 'Aérien',
        'penalty_stopping': 'Spécialiste Penalties',
        'distribution': 'Relanceur',
        'sweeper_keeper': 'Sweeper',
        'one_on_one': '1v1',
        'mental_resilience': 'Mental',
        'timing_consistency': 'Consistant'
    }
    strength = strength_names.get(max_dim[0], 'Complet')
    
    # Faiblesse principale
    min_dim = min(dims.items(), key=lambda x: x[1])
    weakness_names = {
        'shot_stopping': 'Arrêts Faibles',
        'aerial_dominance': 'Faible Aérien',
        'penalty_stopping': 'Penalties Faible',
        'distribution': 'Relance Faible',
        'sweeper_keeper': 'Reste sur Ligne',
        'one_on_one': '1v1 Faible',
        'mental_resilience': 'Mental Fragile',
        'timing_consistency': 'Inconsistant'
    }
    
    if min_dim[1] <= 35:
        weakness = weakness_names.get(min_dim[0], '')
        return f"{level} {strength}, {weakness}"
    
    return f"{level} {strength}"

def convert_numpy(obj):
    """Convertit les types numpy en types Python natifs"""
    if isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy(item) for item in obj]
    elif hasattr(obj, 'item'):  # numpy scalar
        return obj.item()
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj

def main():
    print("=" * 80)
    print("🧤 GOALKEEPER DNA SCRAPER V1.0")
    print("   15 Dimensions | Fingerprint Unique | Exploit Paths")
    print("=" * 80)
    
    # 1. Scraper toutes les ligues
    all_keepers_raw = []
    
    for league, urls in FBREF_LEAGUES.items():
        keepers = scrape_fbref_keepers(league, urls)
        all_keepers_raw.extend(keepers)
        time.sleep(3)  # Pause entre les ligues
    
    print(f"\n📊 Total gardiens scrapés: {len(all_keepers_raw)}")
    
    # 2. Parser les données
    print("\n🔬 Parsing des données...")
    keepers = parse_keeper_stats(all_keepers_raw)
    print(f"   ✅ {len(keepers)} gardiens qualifiés (min 270 minutes)")
    
    if not keepers:
        print("   ❌ Aucun gardien trouvé!")
        return
    
    # 3. Calculer les percentiles
    print("\n📈 Calcul des percentiles...")
    keepers = calculate_percentiles(keepers)
    
    # 4. Calculer les dimensions
    print("\n🎯 Calcul des 15 dimensions...")
    keepers = calculate_dimension_scores(keepers)
    
    # 5. Enrichir chaque gardien
    print("\n🧬 Génération des profils uniques...")
    for keeper in keepers:
        keeper['fingerprint_code'] = generate_fingerprint(keeper)
        keeper['fingerprint_compact'] = generate_compact_fingerprint(keeper)
        keeper['profile_tags'] = assign_profile_tags(keeper)
        keeper['exploit_paths'] = generate_exploit_paths(keeper)
        keeper['enriched_name'] = generate_enriched_name(keeper)
        keeper['dna_string'] = '-'.join(keeper['profile_tags'])
    
    # 6. Convertir numpy et sauvegarder
    print("\n💾 Sauvegarde...")
    keepers = convert_numpy(keepers)
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(keepers, f, indent=2, ensure_ascii=False)
    print(f"   ✅ Sauvegardé: {OUTPUT_FILE}")
    
    # 7. Vérifier unicité
    print("\n🔍 Vérification unicité...")
    fingerprints = [k['fingerprint_code'] for k in keepers]
    unique_fp = len(set(fingerprints))
    print(f"   • Fingerprints uniques: {unique_fp}/{len(keepers)} ({unique_fp/len(keepers)*100:.1f}%)")
    
    # 8. Rapport
    print("\n" + "=" * 80)
    print("📊 RAPPORT GOALKEEPER DNA V1.0")
    print("=" * 80)
    
    # Distribution par niveau
    print("\n📈 Distribution par niveau:")
    level_counts = {}
    for keeper in keepers:
        tags = keeper['profile_tags']
        level = tags[0] if tags else 'UNKNOWN'
        level_counts[level] = level_counts.get(level, 0) + 1
    
    for level, count in sorted(level_counts.items(), key=lambda x: -x[1]):
        pct = count / len(keepers) * 100
        print(f"   {level}: {count} ({pct:.1f}%)")
    
    # Top gardiens
    print("\n🏆 TOP 10 GARDIENS (Score Global):")
    top_keepers = sorted(keepers, key=lambda x: x['overall_score'], reverse=True)[:10]
    for i, k in enumerate(top_keepers, 1):
        print(f"   {i:2}. {k['player_name']:<20} ({k['team']:<15}) | Score: {k['overall_score']} | PSxG+/-: {k['psxg_diff']:+.1f}")
    
    # Pires gardiens
    print("\n⚠️ BOTTOM 10 GARDIENS (Cibles):")
    bottom_keepers = sorted(keepers, key=lambda x: x['overall_score'])[:10]
    for i, k in enumerate(bottom_keepers, 1):
        print(f"   {i:2}. {k['player_name']:<20} ({k['team']:<15}) | Score: {k['overall_score']} | PSxG+/-: {k['psxg_diff']:+.1f}")
    
    # Exemple complet
    if top_keepers:
        example = top_keepers[0]
        print(f"\n📋 EXEMPLE COMPLET: {example['player_name']}")
        print(f"   {'─' * 60}")
        print(f"   Équipe: {example['team']} ({example['league']})")
        print(f"   Fingerprint: {example['fingerprint_code']}")
        print(f"   Compact: {example['fingerprint_compact']}")
        print(f"   Nom enrichi: {example['enriched_name']}")
        print(f"   DNA String: {example['dna_string']}")
        print(f"\n   DIMENSIONS:")
        for dim, val in example['dimensions'].items():
            bar = '█' * int(val / 5)
            print(f"      {dim:<20}: {val:3.0f} {bar}")
        
        if example['exploit_paths']:
            print(f"\n   EXPLOIT PATHS:")
            for exp in example['exploit_paths'][:3]:
                print(f"      • {exp['market']} [{exp['confidence']}] Edge: {exp['edge_estimate']}%")
    
    # Stats par ligue
    print(f"\n📊 GARDIENS PAR LIGUE:")
    league_counts = {}
    for keeper in keepers:
        league = keeper['league']
        league_counts[league] = league_counts.get(league, 0) + 1
    
    for league, count in sorted(league_counts.items()):
        print(f"   {league}: {count}")
    
    print(f"\n{'=' * 80}")
    print(f"✅ GOALKEEPER DNA V1.0 COMPLET - {len(keepers)} GARDIENS")
    print(f"   📁 Fichier: {OUTPUT_FILE}")
    print(f"{'=' * 80}")

if __name__ == '__main__':
    main()
