#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  PHASE 3.5a - TEAM DEFENSE DNA SCRAPER V2                                    ║
║  VERSION CORRIGÉE: Récupère les équipes directement depuis Understat         ║
║  Saison: 2025/2026                                                           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import requests
import json
import re
import time
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

SEASON = '2025'
OUTPUT_DIR = Path('/home/Mon_ps/data/defense_dna')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Ligues Understat avec leurs URLs
LEAGUES = {
    'EPL': 'EPL',
    'La_Liga': 'La_liga',
    'Bundesliga': 'Bundesliga',
    'Serie_A': 'Serie_A',
    'Ligue_1': 'Ligue_1'
}

def fetch_page(url: str) -> Optional[str]:
    """Fetch une page avec gestion d'erreurs"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=30)
        return response.text if response.status_code == 200 else None
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def extract_json_var(html: str, var_name: str) -> Optional[dict]:
    """Extrait une variable JSON du HTML Understat"""
    pattern = rf"var {var_name}\s*=\s*JSON\.parse\('(.+?)'\)"
    match = re.search(pattern, html)
    if match:
        try:
            json_str = match.group(1).encode().decode('unicode_escape')
            return json.loads(json_str)
        except:
            return None
    return None

def get_teams_from_league(league_url: str, season: str = SEASON) -> Dict[str, str]:
    """
    Récupère TOUTES les équipes d'une ligue directement depuis Understat
    Returns: {team_id: team_url_name}
    """
    url = f"https://understat.com/league/{league_url}/{season}"
    html = fetch_page(url)
    
    if not html:
        return {}
    
    teams_data = extract_json_var(html, 'teamsData')
    if not teams_data:
        return {}
    
    teams = {}
    for team_id, data in teams_data.items():
        team_name = data.get('title', '')
        # Convertir en format URL (espaces → underscores)
        url_name = team_name.replace(' ', '_')
        teams[team_id] = {
            'name': team_name,
            'url_name': url_name
        }
    
    return teams

def calculate_timing_metrics(stats: dict) -> dict:
    """Calcule les métriques de timing défensif"""
    timing = stats.get('timing', {})
    metrics = {
        'xga_0_15': 0, 'xga_16_30': 0, 'xga_31_45': 0,
        'xga_46_60': 0, 'xga_61_75': 0, 'xga_76_90': 0,
        'ga_0_15': 0, 'ga_16_30': 0, 'ga_31_45': 0,
        'ga_46_60': 0, 'ga_61_75': 0, 'ga_76_90': 0,
        'shots_ag_0_15': 0, 'shots_ag_16_30': 0, 'shots_ag_31_45': 0,
        'shots_ag_46_60': 0, 'shots_ag_61_75': 0, 'shots_ag_76_90': 0,
    }
    
    slot_mapping = {
        '1-15': '0_15', '16-30': '16_30', '31-45': '31_45',
        '46-60': '46_60', '61-75': '61_75', '76-90': '76_90'
    }
    
    for slot, suffix in slot_mapping.items():
        if slot in timing:
            against = timing[slot].get('against', {})
            metrics[f'xga_{suffix}'] = float(against.get('xG', 0))
            metrics[f'ga_{suffix}'] = int(against.get('goals', 0))
            metrics[f'shots_ag_{suffix}'] = int(against.get('shots', 0))
    
    # Agrégations
    metrics['xga_1h'] = metrics['xga_0_15'] + metrics['xga_16_30'] + metrics['xga_31_45']
    metrics['xga_2h'] = metrics['xga_46_60'] + metrics['xga_61_75'] + metrics['xga_76_90']
    metrics['xga_total_timing'] = metrics['xga_1h'] + metrics['xga_2h']
    
    metrics['ga_1h'] = metrics['ga_0_15'] + metrics['ga_16_30'] + metrics['ga_31_45']
    metrics['ga_2h'] = metrics['ga_46_60'] + metrics['ga_61_75'] + metrics['ga_76_90']
    
    # Pourcentages
    if metrics['xga_total_timing'] > 0:
        metrics['xga_1h_pct'] = metrics['xga_1h'] / metrics['xga_total_timing'] * 100
        metrics['xga_2h_pct'] = metrics['xga_2h'] / metrics['xga_total_timing'] * 100
        metrics['xga_first_15_pct'] = metrics['xga_0_15'] / metrics['xga_total_timing'] * 100
        metrics['xga_last_15_pct'] = metrics['xga_76_90'] / metrics['xga_total_timing'] * 100
    else:
        metrics['xga_1h_pct'] = 0
        metrics['xga_2h_pct'] = 0
        metrics['xga_first_15_pct'] = 0
        metrics['xga_last_15_pct'] = 0
    
    return metrics

def calculate_situation_metrics(stats: dict) -> dict:
    """Calcule les métriques par situation"""
    situations = stats.get('situation', {})
    metrics = {
        'xga_open_play': 0, 'ga_open_play': 0,
        'xga_set_piece': 0, 'ga_set_piece': 0,
        'xga_corner': 0, 'ga_corner': 0,
        'xga_free_kick': 0, 'ga_free_kick': 0,
        'xga_penalty': 0, 'ga_penalty': 0,
    }
    
    mapping = {
        'OpenPlay': 'open_play',
        'FromCorner': 'corner',
        'SetPiece': 'set_piece',
        'DirectFreekick': 'free_kick',
        'Penalty': 'penalty'
    }
    
    for sit, suffix in mapping.items():
        if sit in situations:
            against = situations[sit].get('against', {})
            metrics[f'xga_{suffix}'] = float(against.get('xG', 0))
            metrics[f'ga_{suffix}'] = int(against.get('goals', 0))
    
    # Set piece total
    metrics['xga_set_piece_total'] = metrics['xga_corner'] + metrics['xga_set_piece'] + metrics['xga_free_kick']
    metrics['ga_set_piece_total'] = metrics['ga_corner'] + metrics['ga_set_piece'] + metrics['ga_free_kick']
    
    # Pourcentage set piece
    total_xga = metrics['xga_open_play'] + metrics['xga_set_piece_total'] + metrics['xga_penalty']
    if total_xga > 0:
        metrics['set_piece_vuln_pct'] = metrics['xga_set_piece_total'] / total_xga * 100
    else:
        metrics['set_piece_vuln_pct'] = 0
    
    return metrics

def calculate_shot_zone_metrics(stats: dict) -> dict:
    """Calcule les métriques par zone de tir"""
    zones = stats.get('shotZone', {})
    metrics = {
        'xga_six_yard': 0, 'ga_six_yard': 0, 'shots_ag_six_yard': 0,
        'xga_penalty_area': 0, 'ga_penalty_area': 0, 'shots_ag_penalty_area': 0,
        'xga_outside_box': 0, 'ga_outside_box': 0, 'shots_ag_outside_box': 0,
    }
    
    mapping = {
        'shotSixYardBox': 'six_yard',
        'shotPenaltyArea': 'penalty_area',
        'shotOboxTotal': 'outside_box'
    }
    
    for zone, suffix in mapping.items():
        if zone in zones:
            against = zones[zone].get('against', {})
            metrics[f'xga_{suffix}'] = float(against.get('xG', 0))
            metrics[f'ga_{suffix}'] = int(against.get('goals', 0))
            metrics[f'shots_ag_{suffix}'] = int(against.get('shots', 0))
    
    return metrics

def calculate_game_state_metrics(stats: dict) -> dict:
    """Calcule les métriques par game state"""
    game_state = stats.get('gameState', {})
    metrics = {
        'xga_level': 0, 'ga_level': 0,
        'xga_leading_1': 0, 'ga_leading_1': 0,
        'xga_leading_2plus': 0, 'ga_leading_2plus': 0,
        'xga_losing_1': 0, 'ga_losing_1': 0,
        'xga_losing_2plus': 0, 'ga_losing_2plus': 0,
    }
    
    mapping = {
        'Goal diff 0': 'level',
        'Goal diff +1': 'leading_1',
        'Goal diff > +1': 'leading_2plus',
        'Goal diff -1': 'losing_1',
        'Goal diff < -1': 'losing_2plus'
    }
    
    for state, suffix in mapping.items():
        if state in game_state:
            against = game_state[state].get('against', {})
            metrics[f'xga_{suffix}'] = float(against.get('xG', 0))
            metrics[f'ga_{suffix}'] = int(against.get('goals', 0))
    
    return metrics

def calculate_match_metrics(matches: list) -> dict:
    """Calcule les métriques à partir des matchs"""
    metrics = {
        'matches_played': 0,
        'xga_total': 0, 'ga_total': 0,
        'xga_home': 0, 'ga_home': 0, 'matches_home': 0,
        'xga_away': 0, 'ga_away': 0, 'matches_away': 0,
        'clean_sheets': 0, 'clean_sheets_home': 0, 'clean_sheets_away': 0,
        'xga_per_90': 0, 'ga_per_90': 0, 'cs_pct': 0,
        'xga_per_90_home': 0, 'ga_per_90_home': 0, 'cs_pct_home': 0,
        'xga_per_90_away': 0, 'ga_per_90_away': 0, 'cs_pct_away': 0,
        'defense_overperform': 0,
    }
    
    for match in matches:
        if not match.get('isResult', False):
            continue
        
        side = match.get('side', '')
        goals = match.get('goals', {})
        xg = match.get('xG', {})
        
        metrics['matches_played'] += 1
        
        if side == 'h':  # Home
            ga = int(goals.get('a', 0))
            xga = float(xg.get('a', 0))
            metrics['ga_home'] += ga
            metrics['xga_home'] += xga
            metrics['matches_home'] += 1
            if ga == 0:
                metrics['clean_sheets_home'] += 1
                metrics['clean_sheets'] += 1
        else:  # Away
            ga = int(goals.get('h', 0))
            xga = float(xg.get('h', 0))
            metrics['ga_away'] += ga
            metrics['xga_away'] += xga
            metrics['matches_away'] += 1
            if ga == 0:
                metrics['clean_sheets_away'] += 1
                metrics['clean_sheets'] += 1
        
        metrics['ga_total'] += ga
        metrics['xga_total'] += xga
    
    # Per 90 metrics
    if metrics['matches_played'] > 0:
        metrics['xga_per_90'] = metrics['xga_total'] / metrics['matches_played']
        metrics['ga_per_90'] = metrics['ga_total'] / metrics['matches_played']
        metrics['cs_pct'] = metrics['clean_sheets'] / metrics['matches_played'] * 100
    
    if metrics['matches_home'] > 0:
        metrics['xga_per_90_home'] = metrics['xga_home'] / metrics['matches_home']
        metrics['ga_per_90_home'] = metrics['ga_home'] / metrics['matches_home']
        metrics['cs_pct_home'] = metrics['clean_sheets_home'] / metrics['matches_home'] * 100
    
    if metrics['matches_away'] > 0:
        metrics['xga_per_90_away'] = metrics['xga_away'] / metrics['matches_away']
        metrics['ga_per_90_away'] = metrics['ga_away'] / metrics['matches_away']
        metrics['cs_pct_away'] = metrics['clean_sheets_away'] / metrics['matches_away'] * 100
    
    # Defense over/underperformance
    metrics['defense_overperform'] = metrics['xga_total'] - metrics['ga_total']
    
    return metrics

def assign_defense_profile(xga_per_90: float, cs_pct: float) -> Tuple[str, float]:
    """Assigne un profil défensif"""
    if xga_per_90 < 1.0 and cs_pct > 40:
        return 'FORTRESS', 0.90
    elif xga_per_90 < 1.3 and cs_pct > 25:
        return 'SOLID', 0.70
    elif xga_per_90 < 1.6:
        return 'AVERAGE', 0.50
    elif xga_per_90 < 2.0:
        return 'LEAKY', 0.30
    else:
        return 'SIEVE', 0.10

def assign_timing_profile(first_15_pct: float, last_15_pct: float, 
                         xga_1h_pct: float, xga_2h_pct: float) -> str:
    """Assigne un profil de timing défensif"""
    profiles = []
    
    if first_15_pct > 22:
        profiles.append('SLOW_STARTER')
    if last_15_pct > 22:
        profiles.append('LATE_COLLAPSER')
    if xga_2h_pct > 58:
        profiles.append('SECOND_HALF_WEAK')
    if xga_1h_pct > 58:
        profiles.append('FIRST_HALF_WEAK')
    
    return '+'.join(profiles) if profiles else 'CONSISTENT'

def assign_home_away_defense_profile(xga_home: float, xga_away: float) -> str:
    """Assigne un profil home/away défensif"""
    if xga_away == 0 or xga_home == 0:
        return 'INSUFFICIENT_DATA'
    
    ratio = xga_home / xga_away
    
    if ratio < 0.7:
        return 'HOME_FORTRESS'
    elif ratio > 1.4:
        return 'AWAY_VULNERABLE'
    elif xga_away < 1.2 and xga_home > 1.8:
        return 'TRAVEL_SICK'
    elif xga_away < xga_home * 0.8:
        return 'ROAD_WARRIORS'
    else:
        return 'BALANCED_DEFENSE'

def assign_set_piece_profile(set_piece_vuln_pct: float) -> str:
    """Assigne un profil de vulnérabilité sur coups de pied arrêtés"""
    if set_piece_vuln_pct > 35:
        return 'SP_SIEVE'
    elif set_piece_vuln_pct > 25:
        return 'SP_VULNERABLE'
    elif set_piece_vuln_pct > 15:
        return 'SP_SOLID'
    else:
        return 'SP_FORTRESS'

def scrape_team_defense_dna(team_url_name: str, team_display_name: str, league: str) -> Optional[dict]:
    """Scrape toutes les données défensives d'une équipe"""
    url = f"https://understat.com/team/{team_url_name}/{SEASON}"
    html = fetch_page(url)
    
    if not html:
        return None
    
    stats = extract_json_var(html, 'statisticsData')
    matches = extract_json_var(html, 'datesData')
    
    if not stats or not matches:
        return None
    
    # Vérifier qu'on a des matchs joués
    played_matches = [m for m in matches if m.get('isResult', False)]
    if len(played_matches) < 3:
        return None  # Pas assez de données
    
    # Collecter toutes les métriques
    team_data = {
        'team_name': team_display_name,
        'team_understat': team_url_name,
        'league': league,
        'season': f"{SEASON}/{int(SEASON)+1}",
        'scraped_at': datetime.now().isoformat()
    }
    
    # Métriques de base
    match_metrics = calculate_match_metrics(matches)
    team_data.update(match_metrics)
    
    # Timing
    timing_metrics = calculate_timing_metrics(stats)
    team_data.update(timing_metrics)
    
    # Situations
    situation_metrics = calculate_situation_metrics(stats)
    team_data.update(situation_metrics)
    
    # Shot zones
    zone_metrics = calculate_shot_zone_metrics(stats)
    team_data.update(zone_metrics)
    
    # Game state
    game_state_metrics = calculate_game_state_metrics(stats)
    team_data.update(game_state_metrics)
    
    # Profils
    defense_profile, friction_base = assign_defense_profile(
        team_data['xga_per_90'], 
        team_data['cs_pct']
    )
    team_data['defense_profile'] = defense_profile
    team_data['friction_base'] = friction_base
    
    team_data['timing_profile'] = assign_timing_profile(
        team_data['xga_first_15_pct'],
        team_data['xga_last_15_pct'],
        team_data['xga_1h_pct'],
        team_data['xga_2h_pct']
    )
    
    team_data['home_away_defense_profile'] = assign_home_away_defense_profile(
        team_data['xga_per_90_home'],
        team_data['xga_per_90_away']
    )
    
    team_data['set_piece_profile'] = assign_set_piece_profile(
        team_data['set_piece_vuln_pct']
    )
    
    return team_data

def main():
    """Scrape toutes les équipes de toutes les ligues"""
    print("=" * 70)
    print("🔬 PHASE 3.5a - TEAM DEFENSE DNA SCRAPER V2")
    print(f"📅 Season: {SEASON}/{int(SEASON)+1}")
    print("📊 Méthode: Récupération automatique des équipes depuis Understat")
    print("=" * 70)
    
    all_teams_data = []
    stats = {'success': 0, 'failed': 0, 'insufficient_data': 0, 'by_league': {}}
    
    for league_name, league_url in LEAGUES.items():
        print(f"\n{'='*70}")
        print(f"📊 {league_name}")
        print(f"{'='*70}")
        
        # Récupérer la liste des équipes depuis Understat
        print(f"   🔍 Récupération des équipes depuis Understat...")
        teams = get_teams_from_league(league_url, SEASON)
        
        if not teams:
            print(f"   ❌ Impossible de récupérer les équipes pour {league_name}")
            continue
        
        print(f"   ✅ {len(teams)} équipes trouvées")
        print("-" * 50)
        
        stats['by_league'][league_name] = {'success': 0, 'failed': 0, 'insufficient_data': 0, 'teams': []}
        
        for team_id, team_info in sorted(teams.items(), key=lambda x: x[1]['name']):
            team_url = team_info['url_name']
            team_name = team_info['name']
            
            print(f"   🔍 {team_name}...", end=' ', flush=True)
            
            team_data = scrape_team_defense_dna(team_url, team_name, league_name)
            
            if team_data:
                if team_data['matches_played'] >= 3:
                    all_teams_data.append(team_data)
                    profile = team_data['defense_profile']
                    timing = team_data['timing_profile']
                    matches = team_data['matches_played']
                    print(f"✅ {profile} | {timing} | {matches} matchs")
                    stats['success'] += 1
                    stats['by_league'][league_name]['success'] += 1
                    stats['by_league'][league_name]['teams'].append(team_name)
                else:
                    print(f"⚠️ Insufficient data ({team_data['matches_played']} matchs)")
                    stats['insufficient_data'] += 1
                    stats['by_league'][league_name]['insufficient_data'] += 1
            else:
                print("❌ FAILED")
                stats['failed'] += 1
                stats['by_league'][league_name]['failed'] += 1
            
            time.sleep(0.3)  # Rate limiting
    
    # Save to CSV and JSON
    if all_teams_data:
        # JSON
        json_path = OUTPUT_DIR / f'team_defense_dna_{SEASON}.json'
        with open(json_path, 'w') as f:
            json.dump(all_teams_data, f, indent=2)
        print(f"\n✅ Saved to: {json_path}")
        
        # CSV
        csv_path = OUTPUT_DIR / f'team_defense_dna_{SEASON}.csv'
        all_keys = set()
        for data in all_teams_data:
            all_keys.update(data.keys())
        fieldnames = sorted(all_keys)
        
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_teams_data)
        print(f"✅ Saved to: {csv_path}")
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ FINAL")
    print("=" * 70)
    print(f"   ✅ Success: {stats['success']}")
    print(f"   ⚠️ Insufficient data: {stats['insufficient_data']}")
    print(f"   ❌ Failed: {stats['failed']}")
    print(f"   📊 Total équipes avec données: {len(all_teams_data)}")
    
    print("\n📊 PAR LIGUE:")
    for league, league_stats in stats['by_league'].items():
        total = league_stats['success'] + league_stats['failed'] + league_stats['insufficient_data']
        print(f"   {league}: {league_stats['success']}/{total} équipes")
    
    # Profile distribution
    if all_teams_data:
        print("\n📊 DISTRIBUTION DES PROFILS DÉFENSIFS:")
        profiles = {}
        for team in all_teams_data:
            profile = team['defense_profile']
            profiles[profile] = profiles.get(profile, 0) + 1
        
        for profile in ['FORTRESS', 'SOLID', 'AVERAGE', 'LEAKY', 'SIEVE']:
            count = profiles.get(profile, 0)
            pct = count / len(all_teams_data) * 100 if all_teams_data else 0
            print(f"   {profile:12}: {count:3} ({pct:.1f}%)")
        
        print("\n📊 DISTRIBUTION DES PROFILS TIMING:")
        timing_profiles = {}
        for team in all_teams_data:
            profile = team['timing_profile']
            timing_profiles[profile] = timing_profiles.get(profile, 0) + 1
        
        for profile, count in sorted(timing_profiles.items(), key=lambda x: -x[1]):
            print(f"   {profile:30}: {count}")
    
    # Validation finale
    print("\n" + "=" * 70)
    print("✅ VALIDATION PHASE 3.5a")
    print("=" * 70)
    if stats['failed'] == 0:
        print("   🎯 100% de succès - Aucune erreur!")
    else:
        print(f"   ⚠️ {stats['failed']} équipes en échec (probablement pas en {SEASON}/{int(SEASON)+1})")
    
    print(f"   📊 {len(all_teams_data)} équipes avec données complètes")
    print(f"   📊 Colonnes par équipe: {len(all_keys) if all_teams_data else 0}")

if __name__ == "__main__":
    main()
