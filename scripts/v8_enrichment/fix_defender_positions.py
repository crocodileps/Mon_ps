#!/usr/bin/env python3
"""
🔧 CORRECTION DES POSITIONS DEFENDER DNA
Le problème: Understat utilise D, D S, D L, D R, etc.
"""

import json
from pathlib import Path
from collections import defaultdict
import numpy as np

DATA_DIR = Path('/home/Mon_ps/data/defender_dna')

# Charger les données
with open(DATA_DIR / 'all_defenders_dna.json', 'r') as f:
    defenders = json.load(f)

print("=" * 80)
print("🔧 CORRECTION DES POSITIONS DEFENDER DNA")
print("=" * 80)

# 1. Analyser les positions réelles
print(f"\n📊 POSITIONS RÉELLES DANS LES DONNÉES:")
positions = defaultdict(int)
for d in defenders:
    positions[d.get('position', 'NONE')] += 1

for pos, count in sorted(positions.items(), key=lambda x: -x[1]):
    print(f"   '{pos}': {count}")

# 2. Nouvelle fonction de catégorisation
def get_position_category_v2(position: str) -> str:
    """Catégorisation corrigée pour Understat"""
    if not position:
        return 'UNKNOWN'
    
    pos = position.strip().upper()
    
    # Gardien
    if 'GK' in pos:
        return 'GK'
    
    # Understat utilise: D, D L, D R, D S, D C, etc.
    # S = Sub/Stopper, C = Central, L = Left, R = Right
    
    # Latéral Gauche
    if pos in ['D L', 'DL', 'LB', 'LWB'] or (pos.startswith('D') and ' L' in pos):
        return 'LB'
    
    # Latéral Droit  
    if pos in ['D R', 'DR', 'RB', 'RWB'] or (pos.startswith('D') and ' R' in pos):
        return 'RB'
    
    # Défenseur Central (D, D S, D C, DC, etc. - sans L ou R)
    if pos.startswith('D') and 'L' not in pos and 'R' not in pos:
        return 'CB'
    
    # Milieu défensif
    if pos in ['DMC', 'DM', 'CDM', 'M C', 'MC'] or pos.startswith('DM'):
        return 'DM'
    
    # Milieu
    if pos.startswith('M'):
        return 'MID'
    
    # Attaquant
    if pos.startswith('F') or pos.startswith('S') or pos.startswith('A'):
        return 'FWD'
    
    return 'OTHER'

# 3. Corriger toutes les positions
print(f"\n🔧 APPLICATION DES CORRECTIONS...")

for d in defenders:
    old_cat = d.get('position_category')
    new_cat = get_position_category_v2(d.get('position', ''))
    d['position_category'] = new_cat
    
    # Recalculer le defender_type
    if new_cat == 'CB':
        if d.get('impact_goals_conceded', 0) >= 0.3:
            d['defender_type'] = 'ROCK'
        elif d.get('xGChain_90', 0) >= 0.3:
            d['defender_type'] = 'BALL_PLAYING_CB'
        elif d.get('impact_goals_conceded', 0) <= -0.3:
            d['defender_type'] = 'WEAK_LINK'
        else:
            d['defender_type'] = 'STANDARD'
    elif new_cat in ['LB', 'RB']:
        if d.get('xGChain_90', 0) + d.get('xA_90', 0) >= 0.3:
            d['defender_type'] = 'PISTON'
        elif d.get('impact_goals_conceded', 0) >= 0.3:
            d['defender_type'] = 'STAY_BACK'
        elif d.get('impact_goals_conceded', 0) <= -0.3:
            d['defender_type'] = 'BOULEVARD'
        else:
            d['defender_type'] = 'BALANCED'
    
    # Corriger les tags
    tags = []
    
    # Tags défensifs
    if d.get('impact_goals_conceded', 0) >= 0.3:
        tags.append('DEFENSIVE_ANCHOR')
    elif d.get('impact_goals_conceded', 0) <= -0.3:
        tags.append('DEFENSIVE_LIABILITY')
    
    if d.get('clean_sheet_rate_with', 0) >= 40:
        tags.append('CLEAN_SHEET_MACHINE')
    
    if d.get('impact_wins', 0) >= 15:
        tags.append('WINNER')
    
    # Tags offensifs
    if new_cat == 'CB':
        if d.get('xGChain_90', 0) >= 0.25:
            tags.append('OFFENSIVE_CB')
        if d.get('goals', 0) >= 2:
            tags.append('GOAL_THREAT_CB')
    
    if new_cat in ['LB', 'RB']:
        if d.get('xA_90', 0) >= 0.08:
            tags.append('CREATIVE_FULLBACK')
        if d.get('xGChain_90', 0) >= 0.2:
            tags.append('ATTACKING_FULLBACK')
        if d.get('assists', 0) >= 2:
            tags.append('ASSIST_MACHINE')
    
    if d.get('cards_90', 0) >= 0.35:
        tags.append('CARD_MAGNET')
    
    d['tags'] = tags

# 4. Vérifier la nouvelle distribution
print(f"\n📊 NOUVELLE DISTRIBUTION PAR POSITION:")
new_pos_counts = defaultdict(int)
for d in defenders:
    new_pos_counts[d.get('position_category', 'UNKNOWN')] += 1

for pos, count in sorted(new_pos_counts.items(), key=lambda x: -x[1]):
    print(f"   {pos}: {count}")

# 5. Recréer les lignes défensives
print(f"\n🔧 RECONSTRUCTION DES LIGNES DÉFENSIVES...")

# Grouper par équipe
teams = defaultdict(list)
for d in defenders:
    teams[d.get('team')].append(d)

defensive_lines = {}

for team_name, team_defenders in teams.items():
    # Filtrer par position
    center_backs = [d for d in team_defenders if d.get('position_category') == 'CB']
    left_backs = [d for d in team_defenders if d.get('position_category') == 'LB']
    right_backs = [d for d in team_defenders if d.get('position_category') == 'RB']
    
    # Trier par temps de jeu
    center_backs.sort(key=lambda x: x.get('time', 0), reverse=True)
    left_backs.sort(key=lambda x: x.get('time', 0), reverse=True)
    right_backs.sort(key=lambda x: x.get('time', 0), reverse=True)
    
    # Titulaires
    main_cbs = center_backs[:2]
    main_lb = left_backs[:1] if left_backs else []
    main_rb = right_backs[:1] if right_backs else []
    
    line_profile = {
        'team': team_name,
        'league': team_defenders[0].get('league', '') if team_defenders else '',
        
        # La Charnière
        'charniere': {
            'players': [{'name': cb['name'], 'type': cb.get('defender_type'), 
                        'impact': cb.get('impact_goals_conceded', 0),
                        'xGBuildup_90': cb.get('xGBuildup_90', 0),
                        'clean_sheet_rate': cb.get('clean_sheet_rate_with', 0)} 
                       for cb in main_cbs],
            'count': len(main_cbs),
            'avg_impact': round(np.mean([cb.get('impact_goals_conceded', 0) for cb in main_cbs]), 2) if main_cbs else 0,
            'combined_xGBuildup_90': round(sum(cb.get('xGBuildup_90', 0) for cb in main_cbs), 3) if main_cbs else 0,
            'avg_clean_sheet_rate': round(np.mean([cb.get('clean_sheet_rate_with', 0) for cb in main_cbs]), 1) if main_cbs else 0,
        },
        
        # Latéral Gauche
        'left_flank': {
            'player': main_lb[0]['name'] if main_lb else None,
            'type': main_lb[0].get('defender_type') if main_lb else None,
            'offensive_output': round(main_lb[0].get('xA_90', 0) + main_lb[0].get('xGChain_90', 0), 3) if main_lb else 0,
            'defensive_impact': main_lb[0].get('impact_goals_conceded', 0) if main_lb else 0,
            'xA_90': main_lb[0].get('xA_90', 0) if main_lb else 0,
            'is_piston': main_lb[0].get('defender_type') == 'PISTON' if main_lb else False,
            'is_boulevard': main_lb[0].get('defender_type') == 'BOULEVARD' if main_lb else False,
        },
        
        # Latéral Droit
        'right_flank': {
            'player': main_rb[0]['name'] if main_rb else None,
            'type': main_rb[0].get('defender_type') if main_rb else None,
            'offensive_output': round(main_rb[0].get('xA_90', 0) + main_rb[0].get('xGChain_90', 0), 3) if main_rb else 0,
            'defensive_impact': main_rb[0].get('impact_goals_conceded', 0) if main_rb else 0,
            'xA_90': main_rb[0].get('xA_90', 0) if main_rb else 0,
            'is_piston': main_rb[0].get('defender_type') == 'PISTON' if main_rb else False,
            'is_boulevard': main_rb[0].get('defender_type') == 'BOULEVARD' if main_rb else False,
        },
        
        # Stats globales
        'total_cbs': len(center_backs),
        'total_fullbacks': len(left_backs) + len(right_backs),
        'avg_cards_90': round(np.mean([d.get('cards_90', 0) for d in team_defenders]), 3) if team_defenders else 0,
        
        # Vulnérabilités
        'vulnerabilities': [],
        'strengths': [],
        'exploit_paths': []
    }
    
    # Identifier vulnérabilités
    charniere_impact = line_profile['charniere']['avg_impact']
    
    if charniere_impact <= -0.3:
        line_profile['vulnerabilities'].append('WEAK_CENTRAL_DEFENSE')
        line_profile['exploit_paths'].append({
            'market': 'Goals Over / Anytime Scorer',
            'trigger': 'Attaquants axiaux, joueurs de tête',
            'edge': 4.0
        })
    
    if line_profile['left_flank']['is_boulevard']:
        line_profile['vulnerabilities'].append('LEFT_FLANK_EXPOSED')
        line_profile['exploit_paths'].append({
            'market': 'Goals from right wing',
            'trigger': 'Équipes avec bon ailier droit',
            'edge': 3.5
        })
    
    if line_profile['right_flank']['is_boulevard']:
        line_profile['vulnerabilities'].append('RIGHT_FLANK_EXPOSED')
        line_profile['exploit_paths'].append({
            'market': 'Goals from left wing',
            'trigger': 'Équipes avec bon ailier gauche', 
            'edge': 3.5
        })
    
    if line_profile['left_flank']['is_piston'] or line_profile['right_flank']['is_piston']:
        line_profile['vulnerabilities'].append('COUNTER_VULNERABLE')
        line_profile['exploit_paths'].append({
            'market': 'Goals on counter',
            'trigger': 'Équipes rapides en transition',
            'edge': 4.0
        })
    
    if line_profile['avg_cards_90'] >= 0.35:
        line_profile['vulnerabilities'].append('CARD_PRONE_DEFENSE')
    
    # Forces
    if charniere_impact >= 0.3:
        line_profile['strengths'].append('ROCK_SOLID_CENTER')
    
    if line_profile['charniere']['avg_clean_sheet_rate'] >= 45:
        line_profile['strengths'].append('CLEAN_SHEET_SPECIALISTS')
    
    # Scores
    line_profile['defensive_score'] = round(
        charniere_impact * 2 +
        line_profile['left_flank']['defensive_impact'] +
        line_profile['right_flank']['defensive_impact'],
        2
    )
    
    line_profile['offensive_contribution'] = round(
        line_profile['charniere']['combined_xGBuildup_90'] +
        line_profile['left_flank']['offensive_output'] +
        line_profile['right_flank']['offensive_output'],
        3
    )
    
    defensive_lines[team_name] = line_profile

# 6. Sauvegarder
print(f"\n💾 SAUVEGARDE...")

with open(DATA_DIR / 'all_defenders_dna.json', 'w') as f:
    json.dump(defenders, f, indent=2, ensure_ascii=False)
print(f"   ✅ all_defenders_dna.json ({len(defenders)} défenseurs)")

with open(DATA_DIR / 'defensive_lines.json', 'w') as f:
    json.dump(defensive_lines, f, indent=2, ensure_ascii=False)
print(f"   ✅ defensive_lines.json ({len(defensive_lines)} lignes)")

# 7. Rapport Final
print(f"\n" + "=" * 80)
print("📊 RAPPORT DEFENDER DNA CORRIGÉ")
print("=" * 80)

# Top CB par impact
cbs = [d for d in defenders if d.get('position_category') == 'CB']
cbs_sorted = sorted(cbs, key=lambda x: x.get('impact_goals_conceded', 0), reverse=True)

print(f"\n🏰 TOP 15 DÉFENSEURS CENTRAUX (Impact défensif):")
print(f"   {'Nom':<25} | {'Équipe':<20} | {'Impact':<8} | {'CS%':<6} | {'Type':<15}")
print("   " + "-" * 90)
for cb in cbs_sorted[:15]:
    print(f"   {cb['name']:<25} | {cb['team']:<20} | {cb['impact_goals_conceded']:+.2f} | {cb.get('clean_sheet_rate_with', 0):5.1f}% | {cb.get('defender_type', '?')}")

print(f"\n🔴 BOTTOM 10 CB (Maillons faibles):")
print(f"   {'Nom':<25} | {'Équipe':<20} | {'Impact':<8} | {'CS%':<6} | {'Type':<15}")
print("   " + "-" * 90)
for cb in cbs_sorted[-10:]:
    print(f"   {cb['name']:<25} | {cb['team']:<20} | {cb['impact_goals_conceded']:+.2f} | {cb.get('clean_sheet_rate_with', 0):5.1f}% | {cb.get('defender_type', '?')}")

# Top Latéraux Offensifs
fullbacks = [d for d in defenders if d.get('position_category') in ['LB', 'RB']]
fb_sorted = sorted(fullbacks, key=lambda x: x.get('xGChain_90', 0) + x.get('xA_90', 0), reverse=True)

print(f"\n⚡ TOP 15 LATÉRAUX OFFENSIFS (xGChain + xA /90):")
print(f"   {'Nom':<25} | {'Équipe':<20} | {'Pos':<4} | {'xGC/90':<8} | {'xA/90':<7} | {'Type':<10}")
print("   " + "-" * 95)
for fb in fb_sorted[:15]:
    output = fb.get('xGChain_90', 0) + fb.get('xA_90', 0)
    print(f"   {fb['name']:<25} | {fb['team']:<20} | {fb['position_category']:<4} | {fb.get('xGChain_90', 0):.3f} | {fb.get('xA_90', 0):.3f} | {fb.get('defender_type', '?')}")

# Boulevards (vulnérables aux contres)
boulevards = [fb for fb in fullbacks if fb.get('defender_type') == 'BOULEVARD']
print(f"\n🚨 LATÉRAUX 'BOULEVARD' (laissent des espaces):")
print(f"   {'Nom':<25} | {'Équipe':<20} | {'Pos':<4} | {'Impact':<8}")
print("   " + "-" * 70)
for fb in boulevards[:10]:
    print(f"   {fb['name']:<25} | {fb['team']:<20} | {fb['position_category']:<4} | {fb['impact_goals_conceded']:+.2f}")

# Lignes défensives vulnérables
vulnerable_lines = sorted(defensive_lines.items(), key=lambda x: x[1].get('defensive_score', 0))

print(f"\n🔴 TOP 10 LIGNES DÉFENSIVES VULNÉRABLES:")
print(f"   {'Équipe':<25} | {'Score':<8} | {'Charnière':<30} | Vulnérabilités")
print("   " + "-" * 100)
for team, line in vulnerable_lines[:10]:
    cb_names = ', '.join([p['name'][:12] for p in line['charniere']['players'][:2]])
    vulns = ', '.join(line.get('vulnerabilities', [])[:2]) if line.get('vulnerabilities') else '-'
    print(f"   {team:<25} | {line.get('defensive_score', 0):+.2f} | {cb_names:<30} | {vulns[:40]}")

# Lignes défensives fortes
strong_lines = sorted(defensive_lines.items(), key=lambda x: x[1].get('defensive_score', 0), reverse=True)

print(f"\n�� TOP 10 LIGNES DÉFENSIVES FORTES:")
print(f"   {'Équipe':<25} | {'Score':<8} | {'Charnière':<30} | Forces")
print("   " + "-" * 100)
for team, line in strong_lines[:10]:
    cb_names = ', '.join([p['name'][:12] for p in line['charniere']['players'][:2]])
    strengths = ', '.join(line.get('strengths', [])[:2]) if line.get('strengths') else '-'
    print(f"   {team:<25} | {line.get('defensive_score', 0):+.2f} | {cb_names:<30} | {strengths[:40]}")

# Exemple complet
print(f"\n" + "=" * 80)
print("📋 EXEMPLE COMPLET: Arsenal")
print("=" * 80)

if 'Arsenal' in defensive_lines:
    line = defensive_lines['Arsenal']
    print(f"\n   🏰 LA CHARNIÈRE:")
    for cb in line['charniere']['players']:
        print(f"      • {cb['name']}: {cb['type']} | Impact: {cb['impact']:.2f} | CS: {cb['clean_sheet_rate']:.0f}%")
    print(f"      → Impact moyen: {line['charniere']['avg_impact']:.2f}")
    print(f"      → CS% moyen: {line['charniere']['avg_clean_sheet_rate']:.1f}%")
    
    print(f"\n   ⬅️ COULOIR GAUCHE:")
    lf = line['left_flank']
    print(f"      • {lf['player']}: {lf['type']}")
    print(f"      → Output offensif: {lf['offensive_output']:.3f} | Impact défensif: {lf['defensive_impact']:.2f}")
    print(f"      → Piston: {lf['is_piston']} | Boulevard: {lf['is_boulevard']}")
    
    print(f"\n   ➡️ COULOIR DROIT:")
    rf = line['right_flank']
    print(f"      • {rf['player']}: {rf['type']}")
    print(f"      → Output offensif: {rf['offensive_output']:.3f} | Impact défensif: {rf['defensive_impact']:.2f}")
    print(f"      → Piston: {rf['is_piston']} | Boulevard: {rf['is_boulevard']}")
    
    print(f"\n   📊 SCORES:")
    print(f"      → Defensive Score: {line['defensive_score']:.2f}")
    print(f"      → Offensive Contribution: {line['offensive_contribution']:.3f}")
    
    print(f"\n   ⚠️ VULNÉRABILITÉS: {line['vulnerabilities']}")
    print(f"   💪 FORCES: {line['strengths']}")

print(f"\n{'='*80}")
print(f"✅ DEFENDER DNA CORRIGÉ ET COMPLET")
print(f"   {len(cbs)} CB | {len(fullbacks)} Latéraux | {len(defensive_lines)} Lignes")
print(f"{'='*80}")
