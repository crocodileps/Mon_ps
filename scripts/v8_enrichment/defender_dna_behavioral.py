#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🛡️ DEFENDER DNA BEHAVIORAL V2.0                                            ║
║  Catégorisation par COMPORTEMENT (stats) plutôt que position                 ║
║                                                                              ║
║  INSIGHT: Understat ne donne pas gauche/droite                               ║
║  SOLUTION: Analyser le COMPORTEMENT pour identifier les profils              ║
║                                                                              ║
║  PROFILS COMPORTEMENTAUX:                                                    ║
║  ├── ANCHOR: Faible xGChain, haut impact défensif = DC pur                   ║
║  ├── BALL_PLAYER: Haut xGBuildup = DC relanceur                              ║
║  ├── PISTON: Haut xGChain + xA = Latéral offensif                            ║
║  ├── BALANCED: Stats moyennes = Latéral équilibré                            ║
║  └── WEAK_LINK: Impact négatif = À éviter                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import numpy as np
from pathlib import Path
from collections import defaultdict
from scipy.stats import percentileofscore

DATA_DIR = Path('/home/Mon_ps/data/defender_dna')

# Charger les données
with open(DATA_DIR / 'all_defenders_dna.json', 'r') as f:
    defenders = json.load(f)

print("=" * 80)
print("🛡️ DEFENDER DNA BEHAVIORAL V2.0")
print("   Catégorisation par COMPORTEMENT")
print("=" * 80)

# 1. Calculer les percentiles pour chaque métrique
print(f"\n📊 CALCUL DES PERCENTILES...")

# Collecter les métriques
xgchain_90_all = [d.get('xGChain_90', 0) for d in defenders if d.get('time', 0) >= 500]
xgbuildup_90_all = [d.get('xGBuildup_90', 0) for d in defenders if d.get('time', 0) >= 500]
xa_90_all = [d.get('xA_90', 0) for d in defenders if d.get('time', 0) >= 500]
impact_all = [d.get('impact_goals_conceded', 0) for d in defenders if d.get('matches_analyzed_with', 0) >= 3]
cards_90_all = [d.get('cards_90', 0) for d in defenders if d.get('time', 0) >= 500]

print(f"   xGChain/90: min={min(xgchain_90_all):.3f}, max={max(xgchain_90_all):.3f}, median={np.median(xgchain_90_all):.3f}")
print(f"   xGBuildup/90: min={min(xgbuildup_90_all):.3f}, max={max(xgbuildup_90_all):.3f}, median={np.median(xgbuildup_90_all):.3f}")
print(f"   xA/90: min={min(xa_90_all):.3f}, max={max(xa_90_all):.3f}, median={np.median(xa_90_all):.3f}")

# Seuils pour catégorisation (basés sur percentiles)
THRESHOLDS = {
    'xGChain_90_high': np.percentile(xgchain_90_all, 75),  # Top 25%
    'xGChain_90_low': np.percentile(xgchain_90_all, 25),   # Bottom 25%
    'xGBuildup_90_high': np.percentile(xgbuildup_90_all, 75),
    'xA_90_high': np.percentile(xa_90_all, 75),
    'impact_positive': 0.2,
    'impact_negative': -0.2,
}

print(f"\n📊 SEUILS DE CATÉGORISATION:")
for k, v in THRESHOLDS.items():
    print(f"   {k}: {v:.3f}")

# 2. Catégoriser chaque défenseur par comportement
print(f"\n🔧 CATÉGORISATION COMPORTEMENTALE...")

def get_behavioral_profile(defender: dict) -> dict:
    """Détermine le profil comportemental d'un défenseur"""
    
    xgc = defender.get('xGChain_90', 0)
    xgb = defender.get('xGBuildup_90', 0)
    xa = defender.get('xA_90', 0)
    impact = defender.get('impact_goals_conceded', 0)
    time_played = defender.get('time', 0)
    
    # Percentiles
    xgc_pct = percentileofscore(xgchain_90_all, xgc, kind='rank') if time_played >= 500 else 50
    xgb_pct = percentileofscore(xgbuildup_90_all, xgb, kind='rank') if time_played >= 500 else 50
    xa_pct = percentileofscore(xa_90_all, xa, kind='rank') if time_played >= 500 else 50
    
    offensive_score = (xgc_pct + xa_pct) / 2
    buildup_score = xgb_pct
    
    # Profil comportemental
    if impact <= THRESHOLDS['impact_negative']:
        profile = 'WEAK_LINK'
        description = "Impact défensif négatif - Maillon faible"
    elif offensive_score >= 70 and xa >= THRESHOLDS['xA_90_high']:
        profile = 'PISTON'
        description = "Haut output offensif - Monte beaucoup"
    elif buildup_score >= 70 and offensive_score < 50:
        profile = 'BALL_PLAYER'
        description = "Relanceur - Construit depuis l'arrière"
    elif impact >= THRESHOLDS['impact_positive'] and offensive_score < 40:
        profile = 'ANCHOR'
        description = "Pur défenseur - Stabilité"
    elif offensive_score >= 60:
        profile = 'OFFENSIVE_DEF'
        description = "Défenseur offensif"
    elif impact >= 0:
        profile = 'BALANCED'
        description = "Profil équilibré"
    else:
        profile = 'STANDARD'
        description = "Profil standard"
    
    return {
        'profile': profile,
        'description': description,
        'offensive_score': round(offensive_score, 1),
        'buildup_score': round(buildup_score, 1),
        'xGChain_percentile': round(xgc_pct, 1),
        'xA_percentile': round(xa_pct, 1),
        'xGBuildup_percentile': round(xgb_pct, 1)
    }

# Appliquer à tous les défenseurs
for d in defenders:
    behavioral = get_behavioral_profile(d)
    d['behavioral_profile'] = behavioral['profile']
    d['behavioral_description'] = behavioral['description']
    d['offensive_score'] = behavioral['offensive_score']
    d['buildup_score'] = behavioral['buildup_score']
    d['xGChain_percentile'] = behavioral['xGChain_percentile']
    d['xA_percentile'] = behavioral['xA_percentile']

# 3. Distribution des profils
print(f"\n📊 DISTRIBUTION DES PROFILS COMPORTEMENTAUX:")
profile_counts = defaultdict(int)
for d in defenders:
    profile_counts[d.get('behavioral_profile', 'UNKNOWN')] += 1

for profile, count in sorted(profile_counts.items(), key=lambda x: -x[1]):
    pct = count / len(defenders) * 100
    bar = '█' * int(pct / 2)
    print(f"   {profile:<15}: {count:3} ({pct:5.1f}%) {bar}")

# 4. Recréer les lignes défensives avec profils comportementaux
print(f"\n🔧 RECONSTRUCTION DES LIGNES DÉFENSIVES...")

teams = defaultdict(list)
for d in defenders:
    teams[d.get('team')].append(d)

defensive_lines = {}

for team_name, team_defenders in teams.items():
    # Trier par temps de jeu
    team_defenders.sort(key=lambda x: x.get('time', 0), reverse=True)
    
    # Prendre les 4 titulaires (plus de temps)
    starters = team_defenders[:4]
    
    # Analyser les profils
    profiles = defaultdict(list)
    for d in starters:
        profiles[d.get('behavioral_profile', 'STANDARD')].append(d)
    
    # Identifier les rôles
    anchors = [d for d in starters if d.get('behavioral_profile') == 'ANCHOR']
    ball_players = [d for d in starters if d.get('behavioral_profile') == 'BALL_PLAYER']
    pistons = [d for d in starters if d.get('behavioral_profile') == 'PISTON']
    offensive_defs = [d for d in starters if d.get('behavioral_profile') == 'OFFENSIVE_DEF']
    weak_links = [d for d in starters if d.get('behavioral_profile') == 'WEAK_LINK']
    
    line_profile = {
        'team': team_name,
        'league': team_defenders[0].get('league', '') if team_defenders else '',
        
        # Composition
        'starters': [{
            'name': d['name'],
            'profile': d.get('behavioral_profile'),
            'impact': d.get('impact_goals_conceded', 0),
            'offensive_score': d.get('offensive_score', 0),
            'xGChain_90': d.get('xGChain_90', 0),
            'xA_90': d.get('xA_90', 0),
            'clean_sheet_rate': d.get('clean_sheet_rate_with', 0)
        } for d in starters],
        
        # Profil de la ligne
        'anchors_count': len(anchors),
        'ball_players_count': len(ball_players),
        'pistons_count': len(pistons),
        'offensive_defs_count': len(offensive_defs),
        'weak_links_count': len(weak_links),
        
        # Stats agrégées
        'avg_impact': round(np.mean([d.get('impact_goals_conceded', 0) for d in starters]), 2),
        'avg_offensive_score': round(np.mean([d.get('offensive_score', 0) for d in starters]), 1),
        'total_xGChain_90': round(sum(d.get('xGChain_90', 0) for d in starters), 3),
        'total_xA_90': round(sum(d.get('xA_90', 0) for d in starters), 3),
        'avg_clean_sheet_rate': round(np.mean([d.get('clean_sheet_rate_with', 0) for d in starters if d.get('clean_sheet_rate_with', 0) > 0]), 1) if any(d.get('clean_sheet_rate_with', 0) > 0 for d in starters) else 0,
        'avg_cards_90': round(np.mean([d.get('cards_90', 0) for d in starters]), 3),
        
        # Caractère de la ligne
        'line_character': '',
        'vulnerabilities': [],
        'strengths': [],
        'exploit_paths': []
    }
    
    # Déterminer le caractère de la ligne
    if len(anchors) >= 2:
        line_profile['line_character'] = 'FORTRESS'  # Très défensif
    elif len(pistons) >= 2:
        line_profile['line_character'] = 'ATTACKING'  # Offensif, vulnérable aux contres
    elif len(weak_links) >= 2:
        line_profile['line_character'] = 'FRAGILE'  # À cibler
    elif len(ball_players) >= 2:
        line_profile['line_character'] = 'POSSESSION'  # Joue depuis l'arrière
    else:
        line_profile['line_character'] = 'BALANCED'
    
    # Vulnérabilités
    if len(weak_links) >= 1:
        line_profile['vulnerabilities'].append('HAS_WEAK_LINK')
        weak_names = [d['name'] for d in weak_links]
        line_profile['exploit_paths'].append({
            'market': 'Goals Over / Anytime Scorer',
            'trigger': f"Cibler {', '.join(weak_names)}",
            'edge': 4.0 + len(weak_links)
        })
    
    if len(pistons) >= 2:
        line_profile['vulnerabilities'].append('COUNTER_VULNERABLE')
        line_profile['exploit_paths'].append({
            'market': 'Goals on counter-attack',
            'trigger': 'Équipes rapides en transition',
            'edge': 4.5
        })
    
    if line_profile['avg_impact'] <= -0.3:
        line_profile['vulnerabilities'].append('OVERALL_WEAK_DEFENSE')
    
    if line_profile['avg_cards_90'] >= 0.35:
        line_profile['vulnerabilities'].append('CARD_PRONE')
        line_profile['exploit_paths'].append({
            'market': 'Cards Over',
            'trigger': 'Attaquants techniques',
            'edge': 3.0
        })
    
    # Forces
    if len(anchors) >= 2:
        line_profile['strengths'].append('ROCK_SOLID')
    
    if line_profile['avg_clean_sheet_rate'] >= 45:
        line_profile['strengths'].append('CLEAN_SHEET_SPECIALISTS')
    
    if line_profile['avg_impact'] >= 0.5:
        line_profile['strengths'].append('HIGH_IMPACT_DEFENSE')
    
    # Score défensif global
    line_profile['defensive_rating'] = round(
        line_profile['avg_impact'] * 3 - 
        len(weak_links) * 1.5 + 
        len(anchors) * 1.0 +
        (line_profile['avg_clean_sheet_rate'] / 100),
        2
    )
    
    defensive_lines[team_name] = line_profile

# 5. Sauvegarder
print(f"\n💾 SAUVEGARDE...")

with open(DATA_DIR / 'all_defenders_dna_v2.json', 'w') as f:
    json.dump(defenders, f, indent=2, ensure_ascii=False)
print(f"   ✅ all_defenders_dna_v2.json ({len(defenders)} défenseurs)")

with open(DATA_DIR / 'defensive_lines_v2.json', 'w') as f:
    json.dump(defensive_lines, f, indent=2, ensure_ascii=False)
print(f"   ✅ defensive_lines_v2.json ({len(defensive_lines)} lignes)")

# 6. Rapports
print(f"\n" + "=" * 80)
print("📊 RAPPORT DEFENDER DNA BEHAVIORAL V2.0")
print("=" * 80)

# Top ANCHORS (purs défenseurs)
anchors_all = [d for d in defenders if d.get('behavioral_profile') == 'ANCHOR']
anchors_sorted = sorted(anchors_all, key=lambda x: x.get('impact_goals_conceded', 0), reverse=True)

print(f"\n🏰 TOP 15 ANCHORS (Purs défenseurs - Impact positif):")
print(f"   {'Nom':<25} | {'Équipe':<20} | {'Impact':<8} | {'CS%':<6} | {'Off Score':<10}")
print("   " + "-" * 85)
for d in anchors_sorted[:15]:
    print(f"   {d['name']:<25} | {d['team']:<20} | {d['impact_goals_conceded']:+.2f} | {d.get('clean_sheet_rate_with', 0):5.1f}% | {d.get('offensive_score', 0):5.1f}")

# Top PISTONS (latéraux offensifs)
pistons_all = [d for d in defenders if d.get('behavioral_profile') == 'PISTON']
pistons_sorted = sorted(pistons_all, key=lambda x: x.get('offensive_score', 0), reverse=True)

print(f"\n⚡ TOP 15 PISTONS (Latéraux offensifs - Haut xGChain + xA):")
print(f"   {'Nom':<25} | {'Équipe':<20} | {'xGC/90':<8} | {'xA/90':<7} | {'Off Score':<10}")
print("   " + "-" * 85)
for d in pistons_sorted[:15]:
    print(f"   {d['name']:<25} | {d['team']:<20} | {d.get('xGChain_90', 0):.3f} | {d.get('xA_90', 0):.3f} | {d.get('offensive_score', 0):5.1f}")

# Top BALL_PLAYERS (relanceurs)
bp_all = [d for d in defenders if d.get('behavioral_profile') == 'BALL_PLAYER']
bp_sorted = sorted(bp_all, key=lambda x: x.get('buildup_score', 0), reverse=True)

print(f"\n🎯 TOP 15 BALL PLAYERS (Relanceurs - Haut xGBuildup):")
print(f"   {'Nom':<25} | {'Équipe':<20} | {'xGBuildup/90':<12} | {'Buildup Score':<15}")
print("   " + "-" * 80)
for d in bp_sorted[:15]:
    print(f"   {d['name']:<25} | {d['team']:<20} | {d.get('xGBuildup_90', 0):.3f} | {d.get('buildup_score', 0):5.1f}")

# WEAK_LINKS (maillons faibles)
wl_all = [d for d in defenders if d.get('behavioral_profile') == 'WEAK_LINK']
wl_sorted = sorted(wl_all, key=lambda x: x.get('impact_goals_conceded', 0))

print(f"\n🔴 TOP 15 WEAK LINKS (Maillons faibles - À CIBLER):")
print(f"   {'Nom':<25} | {'Équipe':<20} | {'Impact':<8} | {'CS%':<6} | {'Temps':<8}")
print("   " + "-" * 85)
for d in wl_sorted[:15]:
    print(f"   {d['name']:<25} | {d['team']:<20} | {d['impact_goals_conceded']:+.2f} | {d.get('clean_sheet_rate_with', 0):5.1f}% | {d.get('time', 0):5}min")

# Lignes défensives les plus vulnérables
vul_lines = sorted(defensive_lines.items(), key=lambda x: x[1].get('defensive_rating', 0))

print(f"\n🔴 TOP 15 LIGNES DÉFENSIVES VULNÉRABLES:")
print(f"   {'Équipe':<25} | {'Rating':<8} | {'Character':<12} | {'Weak Links':<5} | Vulnérabilités")
print("   " + "-" * 100)
for team, line in vul_lines[:15]:
    vulns = ', '.join(line.get('vulnerabilities', [])[:2]) if line.get('vulnerabilities') else '-'
    print(f"   {team:<25} | {line.get('defensive_rating', 0):+.2f} | {line.get('line_character', '?'):<12} | {line.get('weak_links_count', 0):<5} | {vulns[:35]}")

# Lignes défensives les plus fortes
strong_lines = sorted(defensive_lines.items(), key=lambda x: x[1].get('defensive_rating', 0), reverse=True)

print(f"\n🟢 TOP 15 LIGNES DÉFENSIVES FORTES:")
print(f"   {'Équipe':<25} | {'Rating':<8} | {'Character':<12} | {'Anchors':<5} | Forces")
print("   " + "-" * 100)
for team, line in strong_lines[:15]:
    strengths = ', '.join(line.get('strengths', [])[:2]) if line.get('strengths') else '-'
    print(f"   {team:<25} | {line.get('defensive_rating', 0):+.2f} | {line.get('line_character', '?'):<12} | {line.get('anchors_count', 0):<5} | {strengths[:35]}")

# Exemple complet
print(f"\n" + "=" * 80)
print("📋 EXEMPLE COMPLET: Wolverhampton (Équipe vulnérable)")
print("=" * 80)

if 'Wolverhampton Wanderers' in defensive_lines:
    line = defensive_lines['Wolverhampton Wanderers']
    
    print(f"\n   🛡️ COMPOSITION ({line['line_character']}):")
    for s in line['starters']:
        print(f"      • {s['name']:<25} | {s['profile']:<15} | Impact: {s['impact']:+.2f} | Off: {s['offensive_score']:.0f}")
    
    print(f"\n   📊 STATS:")
    print(f"      → Defensive Rating: {line['defensive_rating']:+.2f}")
    print(f"      → Avg Impact: {line['avg_impact']:+.2f}")
    print(f"      → Total xGChain/90: {line['total_xGChain_90']:.3f}")
    print(f"      → Avg Clean Sheet: {line['avg_clean_sheet_rate']:.1f}%")
    
    print(f"\n   ⚠️ VULNÉRABILITÉS: {line['vulnerabilities']}")
    print(f"   🎯 EXPLOIT PATHS:")
    for exp in line['exploit_paths']:
        print(f"      • {exp['market']}: {exp['trigger']} (Edge: {exp['edge']}%)")

print(f"\n{'='*80}")
print(f"✅ DEFENDER DNA BEHAVIORAL V2.0 COMPLET")
print(f"   {len(defenders)} défenseurs | {len(defensive_lines)} lignes | 5 profils comportementaux")
print(f"{'='*80}")
