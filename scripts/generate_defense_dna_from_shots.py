#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  DEFENSE DNA GENERATOR FROM SHOTS                                            ║
║  Génère team_defense_dna_2025.json depuis all_shots_against_2025.json        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Paths
DATA_DIR = Path('/home/Mon_ps/data')
INPUT_FILE = DATA_DIR / 'goalkeeper_dna/all_shots_against_2025.json'
OUTPUT_FILE = DATA_DIR / 'defense_dna/team_defense_dna_2025.json'

# League mapping
LEAGUE_MAP = {
    'Premier League': 'EPL',
    'La Liga': 'La_Liga',
    'Bundesliga': 'Bundesliga',
    'Serie A': 'Serie_A',
    'Ligue 1': 'Ligue_1'
}

def get_timing_bucket(minute):
    """Convertit minute en bucket timing"""
    try:
        m = int(minute)
        if m <= 15: return '0_15'
        elif m <= 30: return '16_30'
        elif m <= 45: return '31_45'
        elif m <= 60: return '46_60'
        elif m <= 75: return '61_75'
        else: return '76_90'
    except:
        return '76_90'

def get_zone(x, y):
    """Détermine la zone du tir basé sur X, Y"""
    try:
        x = float(x)
        y = float(y)
        # X proche de 1 = près du but
        if x >= 0.94:  # Six yard box
            return 'six_yard'
        elif x >= 0.83:  # Penalty area
            return 'penalty_area'
        else:
            return 'outside_box'
    except:
        return 'penalty_area'

def analyze_team(team_name, shots, league):
    """Analyse tous les tirs contre une équipe"""
    
    # Structures de collecte
    timing = defaultdict(lambda: {'xG': 0, 'goals': 0, 'shots': 0})
    situations = defaultdict(lambda: {'xG': 0, 'goals': 0, 'shots': 0})
    zones = defaultdict(lambda: {'xG': 0, 'goals': 0, 'shots': 0})
    gamestates = defaultdict(lambda: {'xG': 0, 'goals': 0, 'shots': 0})
    
    # Home/Away tracking
    home_stats = {'xG': 0, 'goals': 0, 'matches': set()}
    away_stats = {'xG': 0, 'goals': 0, 'matches': set()}
    
    # Par match pour clean sheets
    matches = defaultdict(lambda: {'goals': 0, 'h_a': None})
    
    total_xg = 0
    total_goals = 0
    
    for shot in shots:
        xg = float(shot.get('xG', 0))
        is_goal = shot.get('result') == 'Goal'
        minute = shot.get('minute', '45')
        situation = shot.get('situation', 'OpenPlay')
        match_id = shot.get('match_id')
        h_a = shot.get('h_a')  # 'h' ou 'a' - c'est le tireur
        
        # Le tir est CONTRE notre équipe
        # Si h_a='h', c'est home qui tire, donc notre équipe est away
        # Si h_a='a', c'est away qui tire, donc notre équipe est home
        our_position = 'home' if h_a == 'a' else 'away'
        
        total_xg += xg
        if is_goal:
            total_goals += 1
        
        # Timing
        bucket = get_timing_bucket(minute)
        timing[bucket]['xG'] += xg
        timing[bucket]['shots'] += 1
        if is_goal:
            timing[bucket]['goals'] += 1
        
        # Situation
        sit_key = situation.lower().replace(' ', '_')
        situations[sit_key]['xG'] += xg
        situations[sit_key]['shots'] += 1
        if is_goal:
            situations[sit_key]['goals'] += 1
        
        # Zone
        zone = get_zone(shot.get('X', 0.9), shot.get('Y', 0.5))
        zones[zone]['xG'] += xg
        zones[zone]['shots'] += 1
        if is_goal:
            zones[zone]['goals'] += 1
        
        # Gamestate (basé sur h_goals, a_goals avant le tir - approximation)
        try:
            h_goals = int(shot.get('h_goals', 0))
            a_goals = int(shot.get('a_goals', 0))
            # Notre perspective
            if our_position == 'home':
                diff = h_goals - a_goals
            else:
                diff = a_goals - h_goals
            
            if diff == 0:
                gs_key = 'level'
            elif diff == 1:
                gs_key = 'leading_1'
            elif diff >= 2:
                gs_key = 'leading_2plus'
            elif diff == -1:
                gs_key = 'losing_1'
            else:
                gs_key = 'losing_2plus'
            
            gamestates[gs_key]['xG'] += xg
            gamestates[gs_key]['shots'] += 1
            if is_goal:
                gamestates[gs_key]['goals'] += 1
        except:
            pass
        
        # Home/Away
        if our_position == 'home':
            home_stats['xG'] += xg
            if is_goal:
                home_stats['goals'] += 1
            home_stats['matches'].add(match_id)
        else:
            away_stats['xG'] += xg
            if is_goal:
                away_stats['goals'] += 1
            away_stats['matches'].add(match_id)
        
        # Track goals per match
        if match_id:
            matches[match_id]['h_a'] = our_position
            if is_goal:
                matches[match_id]['goals'] += 1
    
    # Calculs finaux
    matches_home = len(home_stats['matches'])
    matches_away = len(away_stats['matches'])
    total_matches = matches_home + matches_away
    
    # Clean sheets
    cs_home = sum(1 for m in matches.values() if m['h_a'] == 'home' and m['goals'] == 0)
    cs_away = sum(1 for m in matches.values() if m['h_a'] == 'away' and m['goals'] == 0)
    clean_sheets = cs_home + cs_away
    
    # Construire le résultat
    result = {
        'team_name': team_name,
        'team_understat': team_name,
        'league': LEAGUE_MAP.get(league, league),
        'season': '2025/2026',
        'scraped_at': datetime.now().isoformat(),
        'matches_played': total_matches,
        
        # XGA totaux
        'xga_total': total_xg,
        'ga_total': total_goals,
        'xga_home': home_stats['xG'],
        'ga_home': home_stats['goals'],
        'matches_home': matches_home,
        'xga_away': away_stats['xG'],
        'ga_away': away_stats['goals'],
        'matches_away': matches_away,
        
        # Clean sheets
        'clean_sheets': clean_sheets,
        'clean_sheets_home': cs_home,
        'clean_sheets_away': cs_away,
        
        # Per 90
        'xga_per_90': total_xg / total_matches if total_matches > 0 else 0,
        'ga_per_90': total_goals / total_matches if total_matches > 0 else 0,
        'cs_pct': (clean_sheets / total_matches * 100) if total_matches > 0 else 0,
        'xga_per_90_home': home_stats['xG'] / matches_home if matches_home > 0 else 0,
        'ga_per_90_home': home_stats['goals'] / matches_home if matches_home > 0 else 0,
        'cs_pct_home': (cs_home / matches_home * 100) if matches_home > 0 else 0,
        'xga_per_90_away': away_stats['xG'] / matches_away if matches_away > 0 else 0,
        'ga_per_90_away': away_stats['goals'] / matches_away if matches_away > 0 else 0,
        'cs_pct_away': (cs_away / matches_away * 100) if matches_away > 0 else 0,
        
        # Overperformance
        'defense_overperform': total_xg - total_goals,
        
        # Timing
        'xga_0_15': timing['0_15']['xG'],
        'xga_16_30': timing['16_30']['xG'],
        'xga_31_45': timing['31_45']['xG'],
        'xga_46_60': timing['46_60']['xG'],
        'xga_61_75': timing['61_75']['xG'],
        'xga_76_90': timing['76_90']['xG'],
        'ga_0_15': timing['0_15']['goals'],
        'ga_16_30': timing['16_30']['goals'],
        'ga_31_45': timing['31_45']['goals'],
        'ga_46_60': timing['46_60']['goals'],
        'ga_61_75': timing['61_75']['goals'],
        'ga_76_90': timing['76_90']['goals'],
        'shots_ag_0_15': timing['0_15']['shots'],
        'shots_ag_16_30': timing['16_30']['shots'],
        'shots_ag_31_45': timing['31_45']['shots'],
        'shots_ag_46_60': timing['46_60']['shots'],
        'shots_ag_61_75': timing['61_75']['shots'],
        'shots_ag_76_90': timing['76_90']['shots'],
        
        # Timing aggregates
        'xga_1h': timing['0_15']['xG'] + timing['16_30']['xG'] + timing['31_45']['xG'],
        'xga_2h': timing['46_60']['xG'] + timing['61_75']['xG'] + timing['76_90']['xG'],
        'ga_1h': timing['0_15']['goals'] + timing['16_30']['goals'] + timing['31_45']['goals'],
        'ga_2h': timing['46_60']['goals'] + timing['61_75']['goals'] + timing['76_90']['goals'],
    }
    
    # Timing percentages
    result['xga_total_timing'] = result['xga_1h'] + result['xga_2h']
    if result['xga_total_timing'] > 0:
        result['xga_1h_pct'] = result['xga_1h'] / result['xga_total_timing'] * 100
        result['xga_2h_pct'] = result['xga_2h'] / result['xga_total_timing'] * 100
        result['xga_first_15_pct'] = timing['0_15']['xG'] / result['xga_total_timing'] * 100
        result['xga_last_15_pct'] = timing['76_90']['xG'] / result['xga_total_timing'] * 100
    else:
        result['xga_1h_pct'] = 50
        result['xga_2h_pct'] = 50
        result['xga_first_15_pct'] = 0
        result['xga_last_15_pct'] = 0
    
    # Situations
    result['xga_open_play'] = situations['openplay']['xG']
    result['ga_open_play'] = situations['openplay']['goals']
    result['xga_set_piece'] = situations['setpiece']['xG']
    result['ga_set_piece'] = situations['setpiece']['goals']
    result['xga_corner'] = situations['fromcorner']['xG']
    result['ga_corner'] = situations['fromcorner']['goals']
    result['xga_free_kick'] = situations['directfreekick']['xG']
    result['ga_free_kick'] = situations['directfreekick']['goals']
    result['xga_penalty'] = situations['penalty']['xG']
    result['ga_penalty'] = situations['penalty']['goals']
    
    result['xga_set_piece_total'] = result['xga_set_piece'] + result['xga_corner'] + result['xga_free_kick']
    result['ga_set_piece_total'] = result['ga_set_piece'] + result['ga_corner'] + result['ga_free_kick']
    result['set_piece_vuln_pct'] = (result['xga_set_piece_total'] / total_xg * 100) if total_xg > 0 else 0
    
    # Zones
    result['xga_six_yard'] = zones['six_yard']['xG']
    result['ga_six_yard'] = zones['six_yard']['goals']
    result['shots_ag_six_yard'] = zones['six_yard']['shots']
    result['xga_penalty_area'] = zones['penalty_area']['xG']
    result['ga_penalty_area'] = zones['penalty_area']['goals']
    result['shots_ag_penalty_area'] = zones['penalty_area']['shots']
    result['xga_outside_box'] = zones['outside_box']['xG']
    result['ga_outside_box'] = zones['outside_box']['goals']
    result['shots_ag_outside_box'] = zones['outside_box']['shots']
    
    # Gamestates
    result['xga_level'] = gamestates['level']['xG']
    result['ga_level'] = gamestates['level']['goals']
    result['xga_leading_1'] = gamestates['leading_1']['xG']
    result['ga_leading_1'] = gamestates['leading_1']['goals']
    result['xga_leading_2plus'] = gamestates['leading_2plus']['xG']
    result['ga_leading_2plus'] = gamestates['leading_2plus']['goals']
    result['xga_losing_1'] = gamestates['losing_1']['xG']
    result['ga_losing_1'] = gamestates['losing_1']['goals']
    result['xga_losing_2plus'] = gamestates['losing_2plus']['xG']
    result['ga_losing_2plus'] = gamestates['losing_2plus']['goals']
    
    # Profils
    result['defense_profile'] = classify_defense(result)
    result['friction_base'] = calculate_friction(result)
    result['timing_profile'] = classify_timing(result)
    result['home_away_defense_profile'] = classify_home_away(result)
    result['set_piece_profile'] = classify_set_piece(result)
    
    return result

def classify_defense(stats):
    """Classifie le profil défensif"""
    xga_90 = stats['xga_per_90']
    overperform = stats['defense_overperform']
    
    if xga_90 < 1.0 and overperform > 2:
        return 'FORTRESS'
    elif xga_90 < 1.2:
        return 'SOLID'
    elif xga_90 < 1.5:
        return 'AVERAGE'
    else:
        return 'LEAKY'

def calculate_friction(stats):
    """Calcule le coefficient de friction défensif"""
    xga_90 = stats['xga_per_90']
    if xga_90 < 0.8:
        return 0.95
    elif xga_90 < 1.0:
        return 0.9
    elif xga_90 < 1.3:
        return 0.85
    elif xga_90 < 1.6:
        return 0.8
    else:
        return 0.75

def classify_timing(stats):
    """Classifie le profil timing"""
    profiles = []
    
    if stats['xga_first_15_pct'] > 20:
        profiles.append('SLOW_STARTER')
    if stats['xga_last_15_pct'] > 20:
        profiles.append('LATE_COLLAPSER')
    if stats['xga_1h_pct'] > 60:
        profiles.append('FIRST_HALF_WEAK')
    if stats['xga_2h_pct'] > 60:
        profiles.append('SECOND_HALF_WEAK')
    
    return '+'.join(profiles) if profiles else 'BALANCED'

def classify_home_away(stats):
    """Classifie le profil home/away"""
    home_xga = stats['xga_per_90_home']
    away_xga = stats['xga_per_90_away']
    
    if home_xga < 0.8 and stats['cs_pct_home'] > 50:
        return 'HOME_FORTRESS'
    elif away_xga < 1.0:
        return 'ROAD_WARRIOR'
    elif home_xga < away_xga * 0.7:
        return 'HOME_DEPENDENT'
    else:
        return 'CONSISTENT'

def classify_set_piece(stats):
    """Classifie la vulnérabilité sur coups de pied arrêtés"""
    sp_pct = stats['set_piece_vuln_pct']
    
    if sp_pct > 35:
        return 'SP_VERY_VULNERABLE'
    elif sp_pct > 25:
        return 'SP_VULNERABLE'
    elif sp_pct < 15:
        return 'SP_STRONG'
    else:
        return 'SP_AVERAGE'

def main():
    print("🧬 DEFENSE DNA GENERATOR")
    print("=" * 60)
    print(f"   Input: {INPUT_FILE}")
    print(f"   Output: {OUTPUT_FILE}")
    print()
    
    # Charger les shots
    with open(INPUT_FILE) as f:
        all_shots = json.load(f)
    
    print(f"📥 Chargé: {len(all_shots)} équipes")
    
    # Générer le DNA pour chaque équipe
    results = []
    
    for team_name, shots in all_shots.items():
        if not shots:
            continue
        
        # Déterminer la league depuis le premier shot
        league = shots[0].get('league', 'Unknown')
        
        team_dna = analyze_team(team_name, shots, league)
        results.append(team_dna)
    
    # Trier par league puis par nom
    results.sort(key=lambda x: (x['league'], x['team_name']))
    
    # Sauvegarder
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Généré: {len(results)} équipes")
    print(f"   Fichier: {OUTPUT_FILE}")
    
    # Stats
    print("\n📊 Résumé par league:")
    leagues = defaultdict(int)
    for r in results:
        leagues[r['league']] += 1
    for league, count in sorted(leagues.items()):
        print(f"   {league}: {count} équipes")
    
    # Sample
    sample = next((r for r in results if r['team_name'] == 'Liverpool'), results[0])
    print(f"\n📋 Sample - {sample['team_name']}:")
    print(f"   xGA/90: {sample['xga_per_90']:.2f}")
    print(f"   GA/90: {sample['ga_per_90']:.2f}")
    print(f"   CS%: {sample['cs_pct']:.1f}%")
    print(f"   Profile: {sample['defense_profile']}")
    print(f"   Timing: {sample['timing_profile']}")

if __name__ == '__main__':
    main()
