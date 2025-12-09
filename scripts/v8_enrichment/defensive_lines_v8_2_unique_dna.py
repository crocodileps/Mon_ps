#!/usr/bin/env python3
"""
DEFENSIVE LINES V8.2 - UNIQUE DNA SIGNATURES (DONNÉES RÉELLES 76-90)
"""

import json
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict
import statistics
import hashlib
import os

INPUT_PATH = '/home/Mon_ps/data/defense_dna/team_defense_dna_2025_fixed.json'
OUTPUT_PATH = '/home/Mon_ps/data/defensive_lines/defensive_lines_v8_2_unique_dna.json'

def create_timing_dna(team: Dict) -> Dict:
    periods_xga = {
        '0-15': team.get('xga_0_15', 0) or 0,
        '16-30': team.get('xga_16_30', 0) or 0,
        '31-45': team.get('xga_31_45', 0) or 0,
        '46-60': team.get('xga_46_60', 0) or 0,
        '61-75': team.get('xga_61_75', 0) or 0,
        '76-90': team.get('xga_76_90', 0) or 0,
    }
    
    total_xga = sum(periods_xga.values())
    
    if total_xga > 0:
        periods_pct = {k: round(v / total_xga * 100, 1) for k, v in periods_xga.items()}
    else:
        periods_pct = {k: 16.7 for k in periods_xga.keys()}
    
    early = periods_pct['0-15'] + periods_pct['16-30']
    mid = periods_pct['31-45'] + periods_pct['46-60']
    late = periods_pct['61-75'] + periods_pct['76-90']
    first_half = periods_pct['0-15'] + periods_pct['16-30'] + periods_pct['31-45']
    second_half = periods_pct['46-60'] + periods_pct['61-75'] + periods_pct['76-90']
    
    peak_period = max(periods_pct, key=periods_pct.get)
    weakest_period = min(periods_pct, key=periods_pct.get)
    
    timing_tags = []
    
    if early > 42: timing_tags.append('EARLY_HEAVY')
    elif early > 36: timing_tags.append('EARLY_VULNERABLE')
    elif early < 28: timing_tags.append('EARLY_SOLID')
    elif early < 32: timing_tags.append('EARLY_GOOD')
    
    if late > 40: timing_tags.append('LATE_COLLAPSER')
    elif late > 35: timing_tags.append('LATE_VULNERABLE')
    elif late < 25: timing_tags.append('LATE_FORTRESS')
    elif late < 30: timing_tags.append('LATE_SOLID')
    
    if mid > 48: timing_tags.append('MID_VULNERABLE')
    elif mid < 35: timing_tags.append('MID_SOLID')
    
    if periods_pct['0-15'] > 22: timing_tags.append('KICKOFF_VULNERABLE')
    if periods_pct['76-90'] > 20: timing_tags.append('CLOSING_VULNERABLE')
    elif periods_pct['76-90'] < 12: timing_tags.append('CLOSING_SOLID')
    
    if second_half > first_half + 12: timing_tags.append('2H_COLLAPSER')
    elif first_half > second_half + 12: timing_tags.append('1H_VULNERABLE')
    
    if 'LATE_COLLAPSER' in timing_tags:
        if 'EARLY_SOLID' in timing_tags or 'EARLY_GOOD' in timing_tags:
            primary_profile = 'STARTS_STRONG_FADES'
        else:
            primary_profile = 'LATE_COLLAPSER'
    elif 'LATE_VULNERABLE' in timing_tags:
        primary_profile = 'LATE_VULNERABLE'
    elif 'EARLY_HEAVY' in timing_tags or 'EARLY_VULNERABLE' in timing_tags:
        if 'LATE_SOLID' in timing_tags or 'LATE_FORTRESS' in timing_tags:
            primary_profile = 'SLOW_STARTER_STRONG_FINISH'
        else:
            primary_profile = 'SLOW_STARTER'
    elif 'LATE_FORTRESS' in timing_tags:
        primary_profile = 'STRONG_FINISHER'
    elif 'EARLY_SOLID' in timing_tags:
        primary_profile = 'FAST_STARTER'
    elif 'MID_VULNERABLE' in timing_tags:
        primary_profile = 'MID_GAME_VULNERABLE'
    else:
        primary_profile = 'BALANCED'
    
    def quantize(val: float) -> int:
        return min(9, max(0, int(val / 11)))
    
    timing_vector = [quantize(periods_pct[p]) for p in ['0-15', '16-30', '31-45', '46-60', '61-75', '76-90']]
    timing_code = ''.join(str(v) for v in timing_vector)
    dna_hash = hashlib.md5(f"{timing_code}{peak_period}{weakest_period}{primary_profile}".encode()).hexdigest()[:6].upper()
    
    return {
        'periods_xga': periods_xga,
        'periods_pct': periods_pct,
        'early_pct': round(early, 1),
        'mid_pct': round(mid, 1),
        'late_pct': round(late, 1),
        'first_half_pct': round(first_half, 1),
        'second_half_pct': round(second_half, 1),
        'peak_period': peak_period,
        'weakest_period': weakest_period,
        'timing_tags': timing_tags,
        'primary_profile': primary_profile,
        'timing_code': timing_code,
        'dna_hash': dna_hash,
        'xga_76_90_source': team.get('xga_76_90_source', 'CALCULATED'),
    }

def analyze_resistance(team: Dict) -> Dict:
    xga_90 = team.get('xga_per_90', 1.2) or 1.2
    
    if xga_90 < 0.8:
        resist_global, profile = 95, 'ELITE_FORTRESS'
    elif xga_90 < 1.0:
        resist_global, profile = 80, 'SOLID'
    elif xga_90 < 1.2:
        resist_global, profile = 65, 'ABOVE_AVERAGE'
    elif xga_90 < 1.4:
        resist_global, profile = 50, 'AVERAGE'
    elif xga_90 < 1.7:
        resist_global, profile = 35, 'VULNERABLE'
    elif xga_90 < 2.0:
        resist_global, profile = 20, 'CRISIS'
    else:
        resist_global, profile = 10, 'CATASTROPHIC'
    
    return {'profile': profile, 'resist_global': resist_global, 'xga_per_90': xga_90}

def calculate_edge(team: Dict, resistance: Dict, timing_dna: Dict) -> Dict:
    ec = {}
    
    rg = resistance['resist_global']
    if rg < 20: ec['resistance_edge'] = 8.0
    elif rg < 35: ec['resistance_edge'] = 5.0
    elif rg < 50: ec['resistance_edge'] = 2.0
    elif rg < 65: ec['resistance_edge'] = 0.0
    elif rg < 80: ec['resistance_edge'] = -3.0
    else: ec['resistance_edge'] = -6.0
    
    profile = timing_dna['primary_profile']
    if profile in ['LATE_COLLAPSER', 'STARTS_STRONG_FADES']: ec['temporal_edge'] = 3.5
    elif profile == 'LATE_VULNERABLE': ec['temporal_edge'] = 2.5
    elif profile in ['SLOW_STARTER', 'MID_GAME_VULNERABLE']: ec['temporal_edge'] = 1.5
    elif profile in ['STRONG_FINISHER', 'LATE_FORTRESS']: ec['temporal_edge'] = -2.5
    else: ec['temporal_edge'] = 0.0
    
    closing_pct = timing_dna['periods_pct']['76-90']
    if closing_pct > 20: ec['closing_bonus'] = 2.0
    elif closing_pct > 17: ec['closing_bonus'] = 1.0
    elif closing_pct < 10: ec['closing_bonus'] = -1.5
    else: ec['closing_bonus'] = 0.0
    
    overperform = team.get('defense_overperform', 0) or 0
    if overperform > 6: ec['regression_edge'] = 3.0
    elif overperform > 3: ec['regression_edge'] = 1.5
    elif overperform < -6: ec['regression_edge'] = -2.5
    elif overperform < -3: ec['regression_edge'] = -1.0
    else: ec['regression_edge'] = 0.0
    
    sp_vuln = team.get('set_piece_vuln_pct', 25) or 25
    if sp_vuln > 35: ec['set_piece_edge'] = 2.5
    elif sp_vuln > 28: ec['set_piece_edge'] = 1.0
    elif sp_vuln < 15: ec['set_piece_edge'] = -1.5
    else: ec['set_piece_edge'] = 0.0
    
    total = sum(ec.values())
    
    if total >= 15: classif, kelly_mult = 'EXTREME_VALUE', 1.0
    elif total >= 10: classif, kelly_mult = 'HIGH_VALUE', 0.75
    elif total >= 6: classif, kelly_mult = 'MODERATE_VALUE', 0.5
    elif total >= 2: classif, kelly_mult = 'SLIGHT_VALUE', 0.25
    elif total >= -2: classif, kelly_mult = 'NO_VALUE', 0.0
    else: classif, kelly_mult = 'NEGATIVE_VALUE', 0.0
    
    kelly = min(5.0, max(0.0, total * kelly_mult * 0.18))
    
    return {
        'components': ec,
        'total_edge': round(total, 2),
        'classification': classif,
        'kelly_stake': round(kelly, 2),
    }

def analyze_team(team: Dict) -> Dict:
    resistance = analyze_resistance(team)
    timing_dna = create_timing_dna(team)
    edge = calculate_edge(team, resistance, timing_dna)
    
    return {
        'team_name': team.get('team_name', 'Unknown'),
        'league': team.get('league', 'Unknown'),
        'foundation': {
            'matches': team.get('matches_played', 0),
            'xga_90': round(team.get('xga_per_90', 0) or 0, 3),
            'ga_90': round(team.get('ga_per_90', 0) or 0, 3),
            'cs_pct': round(team.get('cs_pct', 0) or 0, 1),
        },
        'resistance': resistance,
        'timing_dna': timing_dna,
        'edge': edge,
        'global_dna': f"{edge['classification'][:3]}|{resistance['profile'][:4]}|{timing_dna['primary_profile'][:4]}|{timing_dna['timing_code']}|E{edge['total_edge']:+.0f}",
        'timing_dna_hash': timing_dna['dna_hash'],
        'version': 'V8.2_REAL_76_90',
        'timestamp': datetime.now().isoformat(),
    }

def main():
    print("=" * 70)
    print("DEFENSIVE LINES V8.2 - DONNÉES RÉELLES 76-90")
    print("=" * 70)
    
    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        teams = json.load(f)
    
    print(f"Chargé: {len(teams)} équipes")
    
    results = []
    for team in teams:
        result = analyze_team(team)
        results.append(result)
        xga_76_90 = result['timing_dna']['periods_xga']['76-90']
        print(f"  {result['team_name']:25} | {result['edge']['total_edge']:+6.1f}% | {result['timing_dna']['primary_profile']:25} | 76-90:{xga_76_90:.2f}")
    
    results.sort(key=lambda x: x['edge']['total_edge'], reverse=True)
    
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nSauvegardé: {OUTPUT_PATH}")
    
    print("\n" + "=" * 70)
    print("TOP 10 GOALS OVER")
    print("=" * 70)
    for i, t in enumerate(results[:10], 1):
        print(f"{i:2}. {t['team_name']:25} | {t['edge']['total_edge']:+.1f}% | K:{t['edge']['kelly_stake']:.1f}% | {t['global_dna']}")
    
    print("\n" + "=" * 70)
    print("TOP 10 GOALS UNDER")
    print("=" * 70)
    for i, t in enumerate(results[-10:][::-1], 1):
        print(f"{i:2}. {t['team_name']:25} | {t['edge']['total_edge']:+.1f}% | K:{t['edge']['kelly_stake']:.1f}% | {t['global_dna']}")
    
    edges = [r['edge']['total_edge'] for r in results]
    timing_dist = defaultdict(int)
    for r in results:
        timing_dist[r['timing_dna']['primary_profile']] += 1
    
    print("\n" + "=" * 70)
    print("STATISTIQUES")
    print("=" * 70)
    print(f"Edge moyen: {statistics.mean(edges):+.1f}%")
    print(f"Min/Max: {min(edges):+.1f}% / {max(edges):+.1f}%")
    print("\nDISTRIBUTION TIMING:")
    for p, c in sorted(timing_dist.items(), key=lambda x: -x[1]):
        print(f"  {p:30}: {c:2} ({c/len(results)*100:.1f}%)")
    
    unique = len(set(r['timing_dna_hash'] for r in results))
    print(f"\nDNA UNIQUENESS: {unique}/{len(results)} ({unique/len(results)*100:.1f}%)")

if __name__ == '__main__':
    main()
