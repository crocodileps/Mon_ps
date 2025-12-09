#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  PHASE 3.5a - TEAM DEFENSE DNA SCRAPER                                       ║
║  Scrape REAL 2025/2026 data from Understat                                   ║
║  Version: 1.0                                                                ║
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

TEAMS_BY_LEAGUE = {
    'EPL': [
        'Manchester_City', 'Arsenal', 'Liverpool', 'Aston_Villa', 'Tottenham',
        'Chelsea', 'Newcastle_United', 'Manchester_United', 'West_Ham',
        'Crystal_Palace', 'Brighton', 'Bournemouth', 'Fulham', 'Wolverhampton_Wanderers',
        'Everton', 'Brentford', 'Nottingham_Forest', 'Luton', 'Burnley',
        'Sheffield_United', 'Ipswich', 'Leicester', 'Southampton'
    ],
    'La_Liga': [
        'Barcelona', 'Real_Madrid', 'Atletico_Madrid', 'Real_Sociedad', 'Real_Betis',
        'Athletic_Club', 'Villarreal', 'Valencia', 'Osasuna', 'Getafe',
        'Sevilla', 'Celta_Vigo', 'Mallorca', 'Girona', 'Rayo_Vallecano',
        'Las_Palmas', 'Alaves', 'Cadiz', 'Granada', 'Almeria',
        'Leganes', 'Valladolid', 'Espanyol'
    ],
    'Bundesliga': [
        'Bayern_Munich', 'Borussia_Dortmund', 'RasenBallsport_Leipzig', 'Bayer_Leverkusen',
        'Union_Berlin', 'Freiburg', 'Eintracht_Frankfurt', 'Wolfsburg',
        'Borussia_M.Gladbach', 'Werder_Bremen', 'Mainz_05', 'Hoffenheim',
        'Augsburg', 'VfB_Stuttgart', 'FC_Koln', 'Bochum', 'Heidenheim',
        'Darmstadt', 'Holstein_Kiel', 'St._Pauli'
    ],
    'Serie_A': [
        'Inter', 'AC_Milan', 'Napoli', 'Juventus', 'Atalanta',
        'AS_Roma', 'Lazio', 'Fiorentina', 'Bologna', 'Torino',
        'Monza', 'Udinese', 'Sassuolo', 'Empoli', 'Lecce',
        'Verona', 'Cagliari', 'Genoa', 'Frosinone', 'Salernitana',
        'Parma', 'Como', 'Venezia'
    ],
    'Ligue_1': [
        'Paris_Saint_Germain', 'Monaco', 'Marseille', 'Lille', 'Lyon',
        'Lens', 'Nice', 'Rennes', 'Strasbourg', 'Reims',
        'Toulouse', 'Montpellier', 'Nantes', 'Lorient', 'Brest',
        'Le_Havre', 'Metz', 'Clermont_Foot', 'Auxerre', 'Angers',
        'Saint-Etienne'
    ]
}

def fetch_team_page(team_name: str, season: str = SEASON) -> Optional[str]:
    url = f"https://understat.com/team/{team_name}/{season}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=30)
        return response.text if response.status_code == 200 else None
    except Exception as e:
        print(f"   ❌ Error fetching {team_name}: {e}")
        return None

def extract_json_var(html: str, var_name: str) -> Optional[dict]:
    pattern = rf"var {var_name}\s*=\s*JSON\.parse\('(.+?)'\)"
    match = re.search(pattern, html)
    if match:
        try:
            json_str = match.group(1).encode().decode('unicode_escape')
            return json.loads(json_str)
        except:
            return None
    return None

def calculate_timing_metrics(stats: dict) -> dict:
    timing = stats.get('timing', {})
    metrics = {
        'xga_0_15': 0, 'xga_16_30': 0, 'xga_31_45': 0,
        'xga_46_60': 0, 'xga_61_75': 0, 'xga_76_90': 0,
        'ga_0_15': 0, 'ga_16_30': 0, 'ga_31_45': 0,
        'ga_46_60': 0, 'ga_61_75': 0, 'ga_76_90': 0,
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
    
    metrics['xga_1h'] = metrics['xga_0_15'] + metrics['xga_16_30'] + metrics['xga_31_45']
    metrics['xga_2h'] = metrics['xga_46_60'] + metrics['xga_61_75'] + metrics['xga_76_90']
    metrics['xga_total_timing'] = metrics['xga_1h'] + metrics['xga_2h']
    
    if metrics['xga_total_timing'] > 0:
        metrics['xga_1h_pct'] = metrics['xga_1h'] / metrics['xga_total_timing'] * 100
        metrics['xga_2h_pct'] = metrics['xga_2h'] / metrics['xga_total_timing'] * 100
        metrics['xga_first_15_pct'] = metrics['xga_0_15'] / metrics['xga_total_timing'] * 100
        metrics['xga_last_15_pct'] = metrics['xga_76_90'] / metrics['xga_total_timing'] * 100
    else:
        metrics['xga_1h_pct'] = metrics['xga_2h_pct'] = 0
        metrics['xga_first_15_pct'] = metrics['xga_last_15_pct'] = 0
    return metrics

def calculate_situation_metrics(stats: dict) -> dict:
    situations = stats.get('situation', {})
    metrics = {
        'xga_open_play': 0, 'ga_open_play': 0,
        'xga_set_piece': 0, 'ga_set_piece': 0,
        'xga_corner': 0, 'ga_corner': 0,
        'xga_free_kick': 0, 'ga_free_kick': 0,
        'xga_penalty': 0, 'ga_penalty': 0,
    }
    mapping = {
        'OpenPlay': 'open_play', 'FromCorner': 'corner',
        'SetPiece': 'set_piece', 'DirectFreekick': 'free_kick', 'Penalty': 'penalty'
    }
    for sit, suffix in mapping.items():
        if sit in situations:
            against = situations[sit].get('against', {})
            metrics[f'xga_{suffix}'] = float(against.get('xG', 0))
            metrics[f'ga_{suffix}'] = int(against.get('goals', 0))
    
    metrics['xga_set_piece_total'] = metrics['xga_corner'] + metrics['xga_set_piece'] + metrics['xga_free_kick']
    total_xga = metrics['xga_open_play'] + metrics['xga_set_piece_total'] + metrics['xga_penalty']
    metrics['set_piece_vuln_pct'] = metrics['xga_set_piece_total'] / total_xga * 100 if total_xga > 0 else 0
    return metrics

def calculate_match_metrics(matches: list) -> dict:
    metrics = {
        'matches_played': 0, 'xga_total': 0, 'ga_total': 0,
        'xga_home': 0, 'ga_home': 0, 'matches_home': 0,
        'xga_away': 0, 'ga_away': 0, 'matches_away': 0,
        'clean_sheets': 0, 'clean_sheets_home': 0, 'clean_sheets_away': 0,
    }
    for match in matches:
        if not match.get('isResult', False):
            continue
        side = match.get('side', '')
        goals = match.get('goals', {})
        xg = match.get('xG', {})
        metrics['matches_played'] += 1
        
        if side == 'h':
            ga = int(goals.get('a', 0))
            xga = float(xg.get('a', 0))
            metrics['ga_home'] += ga
            metrics['xga_home'] += xga
            metrics['matches_home'] += 1
            if ga == 0:
                metrics['clean_sheets_home'] += 1
                metrics['clean_sheets'] += 1
        else:
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
    
    if metrics['matches_played'] > 0:
        metrics['xga_per_90'] = metrics['xga_total'] / metrics['matches_played']
        metrics['ga_per_90'] = metrics['ga_total'] / metrics['matches_played']
        metrics['cs_pct'] = metrics['clean_sheets'] / metrics['matches_played'] * 100
    if metrics['matches_home'] > 0:
        metrics['xga_per_90_home'] = metrics['xga_home'] / metrics['matches_home']
        metrics['cs_pct_home'] = metrics['clean_sheets_home'] / metrics['matches_home'] * 100
    if metrics['matches_away'] > 0:
        metrics['xga_per_90_away'] = metrics['xga_away'] / metrics['matches_away']
        metrics['cs_pct_away'] = metrics['clean_sheets_away'] / metrics['matches_away'] * 100
    
    metrics['defense_overperform'] = metrics['xga_total'] - metrics['ga_total']
    return metrics

def assign_defense_profile(xga_per_90: float, cs_pct: float) -> Tuple[str, float]:
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

def assign_set_piece_profile(set_piece_vuln_pct: float) -> str:
    if set_piece_vuln_pct > 35:
        return 'SP_SIEVE'
    elif set_piece_vuln_pct > 25:
        return 'SP_VULNERABLE'
    elif set_piece_vuln_pct > 15:
        return 'SP_SOLID'
    else:
        return 'SP_FORTRESS'

def scrape_team_defense_dna(team_name: str, league: str) -> Optional[dict]:
    html = fetch_team_page(team_name, SEASON)
    if not html:
        return None
    
    stats = extract_json_var(html, 'statisticsData')
    matches = extract_json_var(html, 'datesData')
    if not stats or not matches:
        return None
    
    team_data = {
        'team_name': team_name.replace('_', ' '),
        'team_understat': team_name,
        'league': league,
        'season': f"{SEASON}/{int(SEASON)+1}",
        'scraped_at': datetime.now().isoformat()
    }
    
    team_data.update(calculate_match_metrics(matches))
    team_data.update(calculate_timing_metrics(stats))
    team_data.update(calculate_situation_metrics(stats))
    
    defense_profile, friction_base = assign_defense_profile(
        team_data.get('xga_per_90', 0), team_data.get('cs_pct', 0)
    )
    team_data['defense_profile'] = defense_profile
    team_data['friction_base'] = friction_base
    team_data['timing_profile'] = assign_timing_profile(
        team_data.get('xga_first_15_pct', 0), team_data.get('xga_last_15_pct', 0),
        team_data.get('xga_1h_pct', 50), team_data.get('xga_2h_pct', 50)
    )
    team_data['set_piece_profile'] = assign_set_piece_profile(team_data.get('set_piece_vuln_pct', 0))
    
    return team_data

def main():
    print("=" * 70)
    print("🔬 PHASE 3.5a - TEAM DEFENSE DNA SCRAPER")
    print(f"📅 Season: {SEASON}/{int(SEASON)+1}")
    print("=" * 70)
    
    all_teams_data = []
    
    for league, teams in TEAMS_BY_LEAGUE.items():
        print(f"\n📊 {league} ({len(teams)} teams)")
        for team in teams:
            print(f"   🔍 {team}...", end=' ')
            team_data = scrape_team_defense_dna(team, league)
            if team_data:
                all_teams_data.append(team_data)
                print(f"✅ {team_data['defense_profile']} | {team_data['timing_profile']}")
            else:
                print("❌ FAILED")
            time.sleep(0.5)
    
    if all_teams_data:
        json_path = OUTPUT_DIR / f'team_defense_dna_{SEASON}.json'
        with open(json_path, 'w') as f:
            json.dump(all_teams_data, f, indent=2)
        print(f"\n✅ Saved: {json_path}")
        
        csv_path = OUTPUT_DIR / f'team_defense_dna_{SEASON}.csv'
        fieldnames = sorted(set(k for d in all_teams_data for k in d.keys()))
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_teams_data)
        print(f"✅ Saved: {csv_path}")
    
    print(f"\n📊 RÉSUMÉ: {len(all_teams_data)} équipes scrapées")

if __name__ == "__main__":
    main()
