#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🧬 DEFENDER DNA UNIQUE V4.0 - EMPREINTE DIGITALE                            ║
║  ZÉRO archétype générique - ADN 100% UNIQUE par défenseur                    ║
║                                                                              ║
║  PRINCIPE: Chaque défenseur a une combinaison UNIQUE de 8 dimensions         ║
║  qui crée son profil personnel - comme une empreinte digitale                ║
║                                                                              ║
║  OUTPUT:                                                                     ║
║  ├── DNA_SIGNATURE: Combinaison unique des 8 dimensions                      ║
║  ├── STRENGTHS: Dimensions >70% (forces spécifiques)                         ║
║  ├── WEAKNESSES: Dimensions <30% (faiblesses spécifiques)                    ║
║  ├── ENRICHED_NAME: Description textuelle unique                             ║
║  └── FINGERPRINT: Code alphanumérique unique                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import numpy as np
from pathlib import Path
from collections import defaultdict
from scipy.stats import percentileofscore

DATA_DIR = Path('/home/Mon_ps/data/defender_dna')

# Charger les données
with open(DATA_DIR / 'all_defenders_dna_v2.json', 'r') as f:
    defenders = json.load(f)

print("=" * 80)
print("🧬 DEFENDER DNA UNIQUE V4.0")
print("   Empreinte digitale UNIQUE par défenseur")
print("=" * 80)

# 1. Filtrer les défenseurs qualifiés
qualified = [d for d in defenders if d.get('time', 0) >= 400 and d.get('matches_analyzed_with', 0) >= 3]
print(f"\n📊 {len(qualified)}/{len(defenders)} défenseurs qualifiés")

# 2. Calculer les distributions
metrics = {
    'impact_goals_conceded': [d.get('impact_goals_conceded', 0) for d in qualified],
    'clean_sheet_rate_with': [d.get('clean_sheet_rate_with', 0) for d in qualified],
    'impact_wins': [d.get('impact_wins', 0) for d in qualified],
    'xGChain_90': [d.get('xGChain_90', 0) for d in qualified],
    'xGBuildup_90': [d.get('xGBuildup_90', 0) for d in qualified],
    'xA_90': [d.get('xA_90', 0) for d in qualified],
    'cards_90': [d.get('cards_90', 0) for d in qualified],
    'time': [d.get('time', 0) for d in qualified],
}

# 3. Labels pour chaque dimension à différents niveaux
DIMENSION_LABELS = {
    'SHIELD': {
        'name': 'Impact Défensif',
        'high': 'Roc Défensif',
        'medium_high': 'Solide',
        'medium': 'Standard',
        'medium_low': 'Passable',
        'low': 'Passoire'
    },
    'FORTRESS': {
        'name': 'Clean Sheets',
        'high': 'Imprenable',
        'medium_high': 'Fiable',
        'medium': 'Moyen',
        'medium_low': 'Perméable',
        'low': 'Troué'
    },
    'WINNER': {
        'name': 'Impact Victoires',
        'high': 'Décisif',
        'medium_high': 'Gagnant',
        'medium': 'Neutre',
        'medium_low': 'Peu d\'impact',
        'low': 'Poids Mort'
    },
    'CHAIN': {
        'name': 'Implication Offensive',
        'high': 'Omniprésent',
        'medium_high': 'Impliqué',
        'medium': 'Présent',
        'medium_low': 'Discret',
        'low': 'Absent'
    },
    'BUILDER': {
        'name': 'Construction',
        'high': 'Architecte',
        'medium_high': 'Relanceur',
        'medium': 'Classique',
        'medium_low': 'Direct',
        'low': 'Dégageur'
    },
    'CREATOR': {
        'name': 'Création',
        'high': 'Passeur Décisif',
        'medium_high': 'Créatif',
        'medium': 'Occasionnel',
        'medium_low': 'Rare',
        'low': 'Aucun'
    },
    'DISCIPLINE': {
        'name': 'Discipline',
        'high': 'Exemplaire',
        'medium_high': 'Propre',
        'medium': 'Normal',
        'medium_low': 'Rugueux',
        'low': 'Indiscipliné'
    },
    'RELIABILITY': {
        'name': 'Titularité',
        'high': 'Indispensable',
        'medium_high': 'Titulaire',
        'medium': 'Rotation',
        'medium_low': 'Remplaçant',
        'low': 'Marginal'
    }
}

def get_level_label(dimension: str, percentile: float) -> str:
    """Retourne le label approprié pour un niveau de percentile"""
    labels = DIMENSION_LABELS.get(dimension, {})
    if percentile >= 80:
        return labels.get('high', 'Elite')
    elif percentile >= 60:
        return labels.get('medium_high', 'Bon')
    elif percentile >= 40:
        return labels.get('medium', 'Moyen')
    elif percentile >= 20:
        return labels.get('medium_low', 'Faible')
    else:
        return labels.get('low', 'Très faible')

def get_level_emoji(percentile: float) -> str:
    """Emoji représentant le niveau"""
    if percentile >= 80:
        return '🟢'
    elif percentile >= 60:
        return '🟡'
    elif percentile >= 40:
        return '⚪'
    elif percentile >= 20:
        return '🟠'
    else:
        return '🔴'

# 4. Calculer l'ADN unique de chaque défenseur
def calculate_unique_dna(defender: dict) -> dict:
    """Calcule l'ADN unique d'un défenseur"""
    
    # Récupérer les valeurs brutes
    raw_values = {
        'impact': defender.get('impact_goals_conceded', 0),
        'cs_rate': defender.get('clean_sheet_rate_with', 0),
        'win_impact': defender.get('impact_wins', 0),
        'xgchain': defender.get('xGChain_90', 0),
        'xgbuildup': defender.get('xGBuildup_90', 0),
        'xa': defender.get('xA_90', 0),
        'cards': defender.get('cards_90', 0),
        'time_played': defender.get('time', 0)
    }
    
    # Calculer les percentiles (0-100)
    dimensions = {
        'SHIELD': round(percentileofscore(metrics['impact_goals_conceded'], raw_values['impact'], kind='rank'), 1),
        'FORTRESS': round(percentileofscore(metrics['clean_sheet_rate_with'], raw_values['cs_rate'], kind='rank'), 1),
        'WINNER': round(percentileofscore(metrics['impact_wins'], raw_values['win_impact'], kind='rank'), 1),
        'CHAIN': round(percentileofscore(metrics['xGChain_90'], raw_values['xgchain'], kind='rank'), 1),
        'BUILDER': round(percentileofscore(metrics['xGBuildup_90'], raw_values['xgbuildup'], kind='rank'), 1),
        'CREATOR': round(percentileofscore(metrics['xA_90'], raw_values['xa'], kind='rank'), 1),
        'DISCIPLINE': round(100 - percentileofscore(metrics['cards_90'], raw_values['cards'], kind='rank'), 1),
        'RELIABILITY': round(percentileofscore(metrics['time'], raw_values['time_played'], kind='rank'), 1)
    }
    
    # Identifier FORCES (>70%) et FAIBLESSES (<30%)
    strengths = []
    weaknesses = []
    
    for dim, val in dimensions.items():
        label = get_level_label(dim, val)
        if val >= 70:
            strengths.append({
                'dimension': dim,
                'value': val,
                'label': label,
                'description': DIMENSION_LABELS[dim]['name']
            })
        elif val <= 30:
            weaknesses.append({
                'dimension': dim,
                'value': val,
                'label': label,
                'description': DIMENSION_LABELS[dim]['name']
            })
    
    # Trier par importance
    strengths.sort(key=lambda x: x['value'], reverse=True)
    weaknesses.sort(key=lambda x: x['value'])
    
    # DNA Signature - combinaison unique
    dna_signature = '-'.join([f"{dim[:2]}{int(val)}" for dim, val in dimensions.items()])
    
    # Fingerprint court
    fingerprint = f"D{int(dimensions['SHIELD']):02d}{int(dimensions['FORTRESS']):02d}-O{int(dimensions['CHAIN']):02d}{int(dimensions['CREATOR']):02d}-R{int(dimensions['DISCIPLINE']):02d}"
    
    # Enriched Name unique basé sur les dimensions dominantes
    enriched_parts = []
    
    # Partie défensive
    if dimensions['SHIELD'] >= 70:
        enriched_parts.append(get_level_label('SHIELD', dimensions['SHIELD']))
    elif dimensions['SHIELD'] <= 30:
        enriched_parts.append(get_level_label('SHIELD', dimensions['SHIELD']))
    
    # Partie offensive
    if dimensions['CHAIN'] >= 70 or dimensions['CREATOR'] >= 70:
        if dimensions['CREATOR'] >= dimensions['CHAIN']:
            enriched_parts.append(get_level_label('CREATOR', dimensions['CREATOR']))
        else:
            enriched_parts.append(get_level_label('CHAIN', dimensions['CHAIN']))
    
    # Caractéristique unique
    if dimensions['BUILDER'] >= 75:
        enriched_parts.append(get_level_label('BUILDER', dimensions['BUILDER']))
    elif dimensions['DISCIPLINE'] <= 25:
        enriched_parts.append(get_level_label('DISCIPLINE', dimensions['DISCIPLINE']))
    elif dimensions['FORTRESS'] >= 75:
        enriched_parts.append(get_level_label('FORTRESS', dimensions['FORTRESS']))
    
    # Si pas assez de caractéristiques, ajouter la plus haute
    if len(enriched_parts) < 2:
        top_dim = max(dimensions.items(), key=lambda x: x[1])
        if top_dim[0] not in [s['dimension'] for s in strengths[:1]]:
            enriched_parts.append(get_level_label(top_dim[0], top_dim[1]))
    
    enriched_name = ' | '.join(enriched_parts) if enriched_parts else 'Profil Standard'
    
    # Ajouter les emojis des extrêmes
    emoji_suffix = ''
    if strengths:
        emoji_suffix += ' ' + get_level_emoji(strengths[0]['value'])
    if weaknesses:
        emoji_suffix += get_level_emoji(weaknesses[0]['value'])
    
    enriched_name += emoji_suffix
    
    # Scores composites
    defensive_composite = (dimensions['SHIELD'] * 2 + dimensions['FORTRESS'] + dimensions['WINNER']) / 4
    offensive_composite = (dimensions['CHAIN'] + dimensions['BUILDER'] + dimensions['CREATOR'] * 2) / 4
    reliability_composite = (dimensions['DISCIPLINE'] + dimensions['RELIABILITY']) / 2
    overall = (defensive_composite + offensive_composite + reliability_composite) / 3
    
    # Profil de risque pour le betting
    betting_profile = {
        'is_target': bool(dimensions['SHIELD'] <= 35 or dimensions['FORTRESS'] <= 30),
        'is_avoid': bool(dimensions['SHIELD'] >= 70 and dimensions['FORTRESS'] >= 60),
        'target_markets': [],
        'avoid_markets': []
    }
    
    if dimensions['SHIELD'] <= 35:
        betting_profile['target_markets'].append('Goals Over')
    if dimensions['DISCIPLINE'] <= 25:
        betting_profile['target_markets'].append('Cards Over')
    if dimensions['CHAIN'] >= 75:
        betting_profile['target_markets'].append('Anytime Assist (if fullback)')
    if dimensions['CREATOR'] >= 80:
        betting_profile['target_markets'].append('To Assist')
    
    if dimensions['SHIELD'] >= 70:
        betting_profile['avoid_markets'].append('Goals Over (si titulaire)')
    if dimensions['FORTRESS'] >= 70:
        betting_profile['avoid_markets'].append('Both Teams To Score')
    
    return {
        'dimensions': dimensions,
        'raw_values': {
            'impact_goals_conceded': float(raw_values['impact']),
            'clean_sheet_rate': float(raw_values['cs_rate']),
            'xGChain_90': float(raw_values['xgchain']),
            'xGBuildup_90': float(raw_values['xgbuildup']),
            'xA_90': float(raw_values['xa']),
            'cards_90': float(raw_values['cards'])
        },
        'strengths': strengths,
        'weaknesses': weaknesses,
        'dna_signature': dna_signature,
        'fingerprint': fingerprint,
        'enriched_name': enriched_name,
        'scores': {
            'defensive': round(defensive_composite, 1),
            'offensive': round(offensive_composite, 1),
            'reliability': round(reliability_composite, 1),
            'overall': round(overall, 1)
        },
        'betting_profile': betting_profile
    }

# 5. Appliquer à tous les défenseurs
print(f"\n🔧 Calcul des ADN uniques...")

unique_signatures = set()
duplicate_count = 0

for d in defenders:
    if d.get('time', 0) >= 400 and d.get('matches_analyzed_with', 0) >= 3:
        dna = calculate_unique_dna(d)
        
        # Vérifier unicité
        if dna['dna_signature'] in unique_signatures:
            duplicate_count += 1
        else:
            unique_signatures.add(dna['dna_signature'])
        
        d['dna'] = dna
    else:
        d['dna'] = None

print(f"   ✅ {len(unique_signatures)} signatures UNIQUES sur {len(qualified)} défenseurs")
print(f"   ⚠️ {duplicate_count} signatures similaires (arrondis proches)")

# 6. Vérifier la diversité des profils
print(f"\n📊 ANALYSE DE LA DIVERSITÉ:")

# Compter les combinaisons de forces
strength_combos = defaultdict(int)
for d in defenders:
    if d.get('dna'):
        combo = tuple(sorted([s['dimension'] for s in d['dna']['strengths']]))
        strength_combos[combo] += 1

print(f"   Combinaisons de forces uniques: {len(strength_combos)}")

# Compter les combinaisons de faiblesses
weakness_combos = defaultdict(int)
for d in defenders:
    if d.get('dna'):
        combo = tuple(sorted([w['dimension'] for w in d['dna']['weaknesses']]))
        weakness_combos[combo] += 1

print(f"   Combinaisons de faiblesses uniques: {len(weakness_combos)}")

# 7. Sauvegarder
print(f"\n💾 SAUVEGARDE...")

with open(DATA_DIR / 'defender_dna_unique_v4.json', 'w') as f:
    json.dump(defenders, f, indent=2, ensure_ascii=False)
print(f"   ✅ defender_dna_unique_v4.json")

# 8. Reconstruire les lignes défensives
print(f"\n🔧 Reconstruction des lignes défensives...")

teams = defaultdict(list)
for d in defenders:
    if d.get('dna'):
        teams[d.get('team')].append(d)

defensive_lines_v4 = {}

for team_name, team_defenders in teams.items():
    team_defenders.sort(key=lambda x: x.get('time', 0), reverse=True)
    starters = team_defenders[:4]
    
    # Analyser les forces/faiblesses de la ligne
    all_strengths = []
    all_weaknesses = []
    targets = []
    
    for d in starters:
        dna = d.get('dna', {})
        all_strengths.extend([s['dimension'] for s in dna.get('strengths', [])])
        all_weaknesses.extend([w['dimension'] for w in dna.get('weaknesses', [])])
        if dna.get('betting_profile', {}).get('is_target'):
            targets.append({
                'name': d['name'],
                'weaknesses': [w['label'] for w in dna.get('weaknesses', [])],
                'markets': dna.get('betting_profile', {}).get('target_markets', [])
            })
    
    # Compter les récurrences
    strength_counts = defaultdict(int)
    for s in all_strengths:
        strength_counts[s] += 1
    
    weakness_counts = defaultdict(int)
    for w in all_weaknesses:
        weakness_counts[w] += 1
    
    # Profil collectif
    collective_strengths = [dim for dim, count in strength_counts.items() if count >= 2]
    collective_weaknesses = [dim for dim, count in weakness_counts.items() if count >= 2]
    
    line = {
        'team': team_name,
        'league': team_defenders[0].get('league', ''),
        
        'starters': [{
            'name': d['name'],
            'enriched_name': d.get('dna', {}).get('enriched_name', ''),
            'fingerprint': d.get('dna', {}).get('fingerprint', ''),
            'dimensions': d.get('dna', {}).get('dimensions', {}),
            'strengths': [s['label'] for s in d.get('dna', {}).get('strengths', [])],
            'weaknesses': [w['label'] for w in d.get('dna', {}).get('weaknesses', [])],
            'overall': d.get('dna', {}).get('scores', {}).get('overall', 50)
        } for d in starters],
        
        'collective_strengths': collective_strengths,
        'collective_weaknesses': collective_weaknesses,
        'targets': targets,
        
        'avg_defensive': round(np.mean([d.get('dna', {}).get('scores', {}).get('defensive', 50) for d in starters]), 1),
        'avg_offensive': round(np.mean([d.get('dna', {}).get('scores', {}).get('offensive', 50) for d in starters]), 1),
        'avg_overall': round(np.mean([d.get('dna', {}).get('scores', {}).get('overall', 50) for d in starters]), 1),
        
        'exploit_paths': []
    }
    
    # Générer exploit paths basés sur les faiblesses collectives
    if 'SHIELD' in collective_weaknesses:
        line['exploit_paths'].append({
            'market': 'Goals Over',
            'reason': f"{weakness_counts['SHIELD']} défenseurs avec faible impact défensif",
            'edge': 4.0 + weakness_counts['SHIELD']
        })
    
    if 'DISCIPLINE' in collective_weaknesses:
        line['exploit_paths'].append({
            'market': 'Cards Over',
            'reason': f"{weakness_counts['DISCIPLINE']} défenseurs indisciplinés",
            'edge': 3.5 + weakness_counts['DISCIPLINE']
        })
    
    if targets:
        line['exploit_paths'].append({
            'market': 'Anytime Scorer',
            'reason': f"Cibler: {', '.join([t['name'] for t in targets[:2]])}",
            'edge': 3.0 + len(targets) * 1.5
        })
    
    defensive_lines_v4[team_name] = line

with open(DATA_DIR / 'defensive_lines_unique_v4.json', 'w') as f:
    json.dump(defensive_lines_v4, f, indent=2, ensure_ascii=False)
print(f"   ✅ defensive_lines_unique_v4.json")

# 9. Rapports
print(f"\n" + "=" * 80)
print("📊 RAPPORT DEFENDER DNA UNIQUE V4.0")
print("=" * 80)

# Exemples de profils UNIQUES
print(f"\n🧬 EXEMPLES DE PROFILS UNIQUES:")

sample_players = ['Gabriel', 'Virgil van Dijk', 'William Saliba', 'Trent Alexander-Arnold', 
                  'Federico Dimarco', 'Toti', 'Ki-Jana Hoever']

for name in sample_players:
    player = next((d for d in defenders if name in d.get('name', '') and d.get('dna')), None)
    if player:
        dna = player['dna']
        dims = dna['dimensions']
        
        print(f"\n   {'─'*70}")
        print(f"   👤 {player['name']} ({player['team']})")
        print(f"   📛 {dna['enriched_name']}")
        print(f"   🔑 {dna['fingerprint']}")
        print(f"   ")
        print(f"   ┌{'─'*50}┐")
        for dim, val in dims.items():
            bar_len = int(val / 5)
            bar = '█' * bar_len + '░' * (20 - bar_len)
            emoji = get_level_emoji(val)
            label = get_level_label(dim, val)
            print(f"   │ {dim:<12} {bar} {val:5.1f}% {emoji} {label:<15}│")
        print(f"   └{'─'*50}┘")
        
        if dna['strengths']:
            print(f"   💪 FORCES: {', '.join([s['label'] for s in dna['strengths']])}")
        if dna['weaknesses']:
            print(f"   ⚠️ FAIBLESSES: {', '.join([w['label'] for w in dna['weaknesses']])}")
        
        bp = dna['betting_profile']
        if bp['target_markets']:
            print(f"   🎯 MARCHÉS À CIBLER: {', '.join(bp['target_markets'])}")
        if bp['avoid_markets']:
            print(f"   🚫 MARCHÉS À ÉVITER: {', '.join(bp['avoid_markets'])}")

# TOP défenseurs par score overall
print(f"\n" + "=" * 80)
print("🏆 TOP 20 DÉFENSEURS (Score Overall)")
print("=" * 80)

ranked = sorted([d for d in defenders if d.get('dna')], 
                key=lambda x: x['dna']['scores']['overall'], reverse=True)

print(f"\n   {'Rang':<5} | {'Nom':<25} | {'Équipe':<20} | {'Score':<6} | Enriched Name")
print("   " + "-" * 100)
for i, d in enumerate(ranked[:20], 1):
    dna = d['dna']
    print(f"   {i:<5} | {d['name']:<25} | {d['team']:<20} | {dna['scores']['overall']:5.1f} | {dna['enriched_name'][:35]}")

# BOTTOM défenseurs (cibles)
print(f"\n" + "=" * 80)
print("�� BOTTOM 20 DÉFENSEURS (Cibles à exploiter)")
print("=" * 80)

print(f"\n   {'Rang':<5} | {'Nom':<25} | {'Équipe':<20} | {'Score':<6} | Faiblesses")
print("   " + "-" * 100)
for i, d in enumerate(ranked[-20:], 1):
    dna = d['dna']
    weaknesses = ', '.join([w['label'] for w in dna['weaknesses'][:2]]) if dna['weaknesses'] else '-'
    print(f"   {i:<5} | {d['name']:<25} | {d['team']:<20} | {dna['scores']['overall']:5.1f} | {weaknesses[:30]}")

# Lignes les plus vulnérables
print(f"\n" + "=" * 80)
print("🔴 TOP 15 LIGNES DÉFENSIVES VULNÉRABLES")
print("=" * 80)

vulnerable_lines = sorted(defensive_lines_v4.items(), key=lambda x: x[1].get('avg_defensive', 50))

print(f"\n   {'Équipe':<25} | {'Def':<5} | {'Targets':<3} | Faiblesses Collectives")
print("   " + "-" * 80)
for team, line in vulnerable_lines[:15]:
    targets_count = len(line.get('targets', []))
    weaknesses = ', '.join(line.get('collective_weaknesses', [])[:3]) if line.get('collective_weaknesses') else '-'
    print(f"   {team:<25} | {line['avg_defensive']:5.1f} | {targets_count:<3} | {weaknesses}")

# Exemple ligne complète
print(f"\n" + "=" * 80)
print("📋 EXEMPLE LIGNE COMPLÈTE: Wolverhampton")
print("=" * 80)

if 'Wolverhampton Wanderers' in defensive_lines_v4:
    line = defensive_lines_v4['Wolverhampton Wanderers']
    
    print(f"\n   🏟️ {line['team']} ({line['league']})")
    print(f"\n   📊 SCORES: Défensif {line['avg_defensive']:.1f} | Offensif {line['avg_offensive']:.1f} | Overall {line['avg_overall']:.1f}")
    
    print(f"\n   🛡️ TITULAIRES:")
    for s in line['starters']:
        print(f"      • {s['name']:<25} | {s['enriched_name']}")
        print(f"        Score: {s['overall']:.1f} | Forces: {', '.join(s['strengths'][:2]) if s['strengths'] else '-'} | Faiblesses: {', '.join(s['weaknesses'][:2]) if s['weaknesses'] else '-'}")
    
    if line['collective_weaknesses']:
        print(f"\n   ⚠️ FAIBLESSES COLLECTIVES: {', '.join(line['collective_weaknesses'])}")
    
    if line['targets']:
        print(f"\n   🎯 CIBLES:")
        for t in line['targets']:
            print(f"      • {t['name']}: {', '.join(t['weaknesses'][:2])}")
            print(f"        → Marchés: {', '.join(t['markets'][:3])}")
    
    if line['exploit_paths']:
        print(f"\n   💰 EXPLOIT PATHS:")
        for ep in line['exploit_paths']:
            print(f"      • {ep['market']}: {ep['reason']} (Edge: {ep['edge']:.1f}%)")

print(f"\n{'='*80}")
print(f"✅ DEFENDER DNA UNIQUE V4.0 COMPLET")
print(f"   {len(unique_signatures)} signatures UNIQUES")
print(f"   {len(strength_combos)} combinaisons de forces")
print(f"   {len(weakness_combos)} combinaisons de faiblesses")
print(f"{'='*80}")
