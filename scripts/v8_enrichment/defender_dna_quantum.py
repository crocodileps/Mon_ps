#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🧬 DEFENDER DNA QUANTUM V3.0 - NIVEAU INSTITUTIONNEL                        ║
║  Profils PERSONNALISÉS multi-dimensionnels                                   ║
║                                                                              ║
║  8 DIMENSIONS D'ANALYSE:                                                     ║
║  ├── 1. SHIELD: Impact défensif (buts concédés)                              ║
║  ├── 2. FORTRESS: Clean sheet ability                                        ║
║  ├── 3. WINNER: Impact sur les victoires                                     ║
║  ├── 4. CHAIN: Implication offensive (xGChain)                               ║
║  ├── 5. BUILDER: Construction du jeu (xGBuildup)                             ║
║  ├── 6. CREATOR: Création de chances (xA)                                    ║
║  ├── 7. DISCIPLINE: Cartons (inverse)                                        ║
║  ├── 8. RELIABILITY: Temps de jeu/Régularité                                 ║
║                                                                              ║
║  OUTPUT: Fingerprint unique + Enriched Name personnalisé                     ║
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
print("🧬 DEFENDER DNA QUANTUM V3.0")
print("   Profils PERSONNALISÉS multi-dimensionnels")
print("=" * 80)

# 1. Filtrer les défenseurs avec assez de données
print(f"\n📊 Filtrage des données significatives...")
qualified = [d for d in defenders if d.get('time', 0) >= 400 and d.get('matches_analyzed_with', 0) >= 3]
print(f"   {len(qualified)}/{len(defenders)} défenseurs qualifiés (≥400 min, ≥3 matchs analysés)")

# 2. Calculer les distributions pour chaque métrique
print(f"\n📊 Calcul des distributions...")

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

for name, values in metrics.items():
    print(f"   {name}: min={min(values):.3f}, max={max(values):.3f}, median={np.median(values):.3f}")

# 3. Fonction de calcul du profil quantum
def calculate_quantum_profile(defender: dict) -> dict:
    """Calcule le profil quantum multi-dimensionnel d'un défenseur"""
    
    # Récupérer les valeurs
    impact = defender.get('impact_goals_conceded', 0)
    cs_rate = defender.get('clean_sheet_rate_with', 0)
    win_impact = defender.get('impact_wins', 0)
    xgchain = defender.get('xGChain_90', 0)
    xgbuildup = defender.get('xGBuildup_90', 0)
    xa = defender.get('xA_90', 0)
    cards = defender.get('cards_90', 0)
    time_played = defender.get('time', 0)
    
    # Calculer les percentiles (0-100)
    shield_pct = percentileofscore(metrics['impact_goals_conceded'], impact, kind='rank')
    fortress_pct = percentileofscore(metrics['clean_sheet_rate_with'], cs_rate, kind='rank')
    winner_pct = percentileofscore(metrics['impact_wins'], win_impact, kind='rank')
    chain_pct = percentileofscore(metrics['xGChain_90'], xgchain, kind='rank')
    builder_pct = percentileofscore(metrics['xGBuildup_90'], xgbuildup, kind='rank')
    creator_pct = percentileofscore(metrics['xA_90'], xa, kind='rank')
    discipline_pct = 100 - percentileofscore(metrics['cards_90'], cards, kind='rank')  # Inversé
    reliability_pct = percentileofscore(metrics['time'], time_played, kind='rank')
    
    # Les 8 dimensions
    dimensions = {
        'SHIELD': round(shield_pct, 1),      # Impact défensif
        'FORTRESS': round(fortress_pct, 1),   # Clean sheets
        'WINNER': round(winner_pct, 1),       # Impact victoires
        'CHAIN': round(chain_pct, 1),         # Implication offensive
        'BUILDER': round(builder_pct, 1),     # Construction jeu
        'CREATOR': round(creator_pct, 1),     # Création chances
        'DISCIPLINE': round(discipline_pct, 1), # Peu de cartons
        'RELIABILITY': round(reliability_pct, 1) # Temps de jeu
    }
    
    # Scores composites
    defensive_score = (dimensions['SHIELD'] * 2 + dimensions['FORTRESS'] + dimensions['WINNER']) / 4
    offensive_score = (dimensions['CHAIN'] + dimensions['BUILDER'] + dimensions['CREATOR'] * 2) / 4
    risk_score = (dimensions['DISCIPLINE'] + dimensions['RELIABILITY']) / 2
    
    # Ratios clés
    def_off_ratio = defensive_score / (offensive_score + 0.01)  # >1 = défensif, <1 = offensif
    chain_builder_ratio = dimensions['CHAIN'] / (dimensions['BUILDER'] + 0.01)  # >1 = monte, <1 = reste
    
    return {
        'dimensions': dimensions,
        'defensive_score': round(defensive_score, 1),
        'offensive_score': round(offensive_score, 1),
        'risk_score': round(risk_score, 1),
        'overall_score': round((defensive_score + offensive_score + risk_score) / 3, 1),
        'def_off_ratio': round(def_off_ratio, 2),
        'chain_builder_ratio': round(chain_builder_ratio, 2)
    }

# 4. Fonction de génération du profil personnalisé
def generate_personalized_profile(defender: dict, quantum: dict) -> dict:
    """Génère un profil personnalisé avec archétype et description"""
    
    dims = quantum['dimensions']
    def_score = quantum['defensive_score']
    off_score = quantum['offensive_score']
    
    # === ARCHÉTYPE PRINCIPAL ===
    archetype = ''
    archetype_desc = ''
    
    # Analyser les dimensions dominantes
    top_dims = sorted(dims.items(), key=lambda x: x[1], reverse=True)[:3]
    bottom_dims = sorted(dims.items(), key=lambda x: x[1])[:2]
    
    # Règles de détermination de l'archétype
    if dims['SHIELD'] >= 75 and dims['FORTRESS'] >= 60:
        archetype = 'FORTRESS_ANCHOR'
        archetype_desc = 'Pilier défensif - Roc inébranlable'
    elif dims['SHIELD'] >= 60 and dims['CHAIN'] >= 70:
        archetype = 'COMPLETE_DEFENDER'
        archetype_desc = 'Défenseur complet - Excelle des deux côtés'
    elif dims['CHAIN'] >= 80 and dims['CREATOR'] >= 70:
        archetype = 'MARAUDING_FULLBACK'
        archetype_desc = 'Latéral offensif - Monte constamment'
    elif dims['CREATOR'] >= 75 and dims['CHAIN'] >= 60:
        archetype = 'CREATIVE_FULLBACK'
        archetype_desc = 'Créateur depuis l\'arrière - Passes décisives'
    elif dims['BUILDER'] >= 75 and dims['CHAIN'] < 50:
        archetype = 'BALL_PLAYING_CB'
        archetype_desc = 'Relanceur - Construit depuis l\'arrière sans monter'
    elif dims['BUILDER'] >= 70 and dims['SHIELD'] >= 60:
        archetype = 'MODERN_CB'
        archetype_desc = 'DC moderne - Défend et relance'
    elif dims['SHIELD'] >= 60 and dims['DISCIPLINE'] < 30:
        archetype = 'AGGRESSIVE_STOPPER'
        archetype_desc = 'Stoppeur agressif - Efficace mais cartons'
    elif dims['CHAIN'] >= 70 and dims['SHIELD'] < 40:
        archetype = 'RISK_TAKER'
        archetype_desc = 'Offensif risqué - Monte mais laisse des espaces'
    elif dims['SHIELD'] < 35 and dims['FORTRESS'] < 35:
        archetype = 'LIABILITY'
        archetype_desc = 'Maillon faible - À cibler'
    elif dims['RELIABILITY'] >= 80 and 40 <= def_score <= 60:
        archetype = 'STEADY_PERFORMER'
        archetype_desc = 'Régulier - Toujours présent, sans éclat'
    elif dims['WINNER'] >= 75:
        archetype = 'CLUTCH_DEFENDER'
        archetype_desc = 'Décisif - Impact sur les victoires'
    elif off_score >= 65:
        archetype = 'OFFENSIVE_DEFENDER'
        archetype_desc = 'Offensif - Contribution offensive élevée'
    elif def_score >= 60:
        archetype = 'SOLID_DEFENDER'
        archetype_desc = 'Solide - Défenseur fiable'
    else:
        archetype = 'BALANCED'
        archetype_desc = 'Équilibré - Profil standard'
    
    # === TRAITS SPÉCIFIQUES ===
    traits = []
    
    # Traits positifs
    if dims['SHIELD'] >= 80:
        traits.append('ELITE_SHIELD')
    if dims['FORTRESS'] >= 80:
        traits.append('CLEAN_SHEET_KING')
    if dims['WINNER'] >= 80:
        traits.append('WINNER_MENTALITY')
    if dims['CHAIN'] >= 80:
        traits.append('CHAIN_MASTER')
    if dims['BUILDER'] >= 80:
        traits.append('BUILDUP_MAESTRO')
    if dims['CREATOR'] >= 80:
        traits.append('ASSIST_THREAT')
    if dims['DISCIPLINE'] >= 85:
        traits.append('DISCIPLINED')
    if dims['RELIABILITY'] >= 90:
        traits.append('IRONMAN')
    
    # Traits négatifs
    if dims['SHIELD'] <= 25:
        traits.append('DEFENSIVE_WEAKNESS')
    if dims['DISCIPLINE'] <= 25:
        traits.append('CARD_MAGNET')
    if dims['RELIABILITY'] <= 25:
        traits.append('ROTATION_PLAYER')
    if dims['FORTRESS'] <= 20:
        traits.append('LEAKY')
    
    # Traits contextuels
    if quantum['chain_builder_ratio'] >= 1.5:
        traits.append('HIGH_LINE_PLAYER')
    elif quantum['chain_builder_ratio'] <= 0.7:
        traits.append('DEEP_LYING')
    
    # === ENRICHED NAME ===
    # Format: [Archétype] [Dimension dominante] [Trait notable si applicable]
    enriched_parts = [archetype.replace('_', ' ').title()]
    
    # Ajouter dimension dominante
    top_dim = top_dims[0][0]
    if top_dims[0][1] >= 75:
        enriched_parts.append(f"({top_dim[:3]} {int(top_dims[0][1])})")
    
    # Ajouter trait notable
    if 'ELITE_SHIELD' in traits:
        enriched_parts.append("🛡️")
    if 'CHAIN_MASTER' in traits or 'MARAUDING_FULLBACK' == archetype:
        enriched_parts.append("⚡")
    if 'CARD_MAGNET' in traits:
        enriched_parts.append("🟨")
    if 'LIABILITY' == archetype:
        enriched_parts.append("⚠️")
    
    enriched_name = ' '.join(enriched_parts)
    
    # === FINGERPRINT ===
    # Format: DEF-[S][F][W]-OFF-[C][B][R]-[overall]
    fingerprint = f"DEF{int(dims['SHIELD'])}{int(dims['FORTRESS'])}{int(dims['WINNER'])}-OFF{int(dims['CHAIN'])}{int(dims['BUILDER'])}{int(dims['CREATOR'])}-{int(quantum['overall_score'])}"
    
    # === EXPLOIT ANALYSIS ===
    exploit_info = {
        'is_target': archetype in ['LIABILITY', 'RISK_TAKER'] or dims['SHIELD'] <= 35,
        'target_reason': [],
        'avoid_reason': []
    }
    
    if dims['SHIELD'] <= 35:
        exploit_info['target_reason'].append('Faible impact défensif')
    if dims['FORTRESS'] <= 30:
        exploit_info['target_reason'].append('Concède beaucoup de buts')
    if archetype == 'RISK_TAKER':
        exploit_info['target_reason'].append('Monte trop, laisse des espaces')
    if dims['DISCIPLINE'] <= 25:
        exploit_info['target_reason'].append('Cartons fréquents')
    
    if dims['SHIELD'] >= 70:
        exploit_info['avoid_reason'].append('Impact défensif très positif')
    if dims['FORTRESS'] >= 70:
        exploit_info['avoid_reason'].append('Clean sheet specialist')
    
    return {
        'archetype': archetype,
        'archetype_description': archetype_desc,
        'traits': traits,
        'enriched_name': enriched_name,
        'fingerprint': fingerprint,
        'exploit_info': exploit_info
    }

# 5. Appliquer à tous les défenseurs
print(f"\n🔧 Calcul des profils quantum...")

for d in defenders:
    if d.get('time', 0) >= 400 and d.get('matches_analyzed_with', 0) >= 3:
        quantum = calculate_quantum_profile(d)
        personalized = generate_personalized_profile(d, quantum)
        
        d['quantum'] = quantum
        d['archetype'] = personalized['archetype']
        d['archetype_description'] = personalized['archetype_description']
        d['traits'] = personalized['traits']
        d['enriched_name'] = personalized['enriched_name']
        d['fingerprint'] = personalized['fingerprint']
        d['exploit_info'] = personalized['exploit_info']
    else:
        d['quantum'] = None
        d['archetype'] = 'INSUFFICIENT_DATA'
        d['enriched_name'] = 'Données insuffisantes'
        d['fingerprint'] = 'N/A'

# 6. Distribution des archétypes
print(f"\n📊 DISTRIBUTION DES ARCHÉTYPES:")
archetype_counts = defaultdict(int)
for d in defenders:
    archetype_counts[d.get('archetype', 'UNKNOWN')] += 1

for arch, count in sorted(archetype_counts.items(), key=lambda x: -x[1]):
    if arch != 'INSUFFICIENT_DATA':
        pct = count / len(qualified) * 100
        bar = '█' * int(pct / 2)
        print(f"   {arch:<22}: {count:3} ({pct:5.1f}%) {bar}")

# 7. Sauvegarder
print(f"\n💾 SAUVEGARDE...")
with open(DATA_DIR / 'defender_dna_quantum_v3.json', 'w') as f:
    json.dump(defenders, f, indent=2, ensure_ascii=False)
print(f"   ✅ defender_dna_quantum_v3.json ({len(defenders)} défenseurs)")

# 8. Reconstruire les lignes défensives avec les nouveaux profils
print(f"\n🔧 Reconstruction des lignes défensives...")

teams = defaultdict(list)
for d in defenders:
    if d.get('quantum'):
        teams[d.get('team')].append(d)

defensive_lines_v3 = {}

for team_name, team_defenders in teams.items():
    team_defenders.sort(key=lambda x: x.get('time', 0), reverse=True)
    starters = team_defenders[:4]
    
    # Analyser la composition
    archetypes = [d.get('archetype') for d in starters]
    targets = [d for d in starters if d.get('exploit_info', {}).get('is_target', False)]
    
    # Caractère de la ligne basé sur les archétypes
    if archetypes.count('FORTRESS_ANCHOR') + archetypes.count('SOLID_DEFENDER') >= 2:
        line_char = 'FORTRESS'
    elif archetypes.count('MARAUDING_FULLBACK') + archetypes.count('RISK_TAKER') >= 2:
        line_char = 'HIGH_RISK_HIGH_REWARD'
    elif archetypes.count('LIABILITY') >= 1 or len(targets) >= 2:
        line_char = 'EXPLOITABLE'
    elif archetypes.count('COMPLETE_DEFENDER') >= 1:
        line_char = 'ELITE'
    elif archetypes.count('BALL_PLAYING_CB') + archetypes.count('MODERN_CB') >= 2:
        line_char = 'POSSESSION'
    else:
        line_char = 'BALANCED'
    
    line = {
        'team': team_name,
        'league': team_defenders[0].get('league', ''),
        'line_character': line_char,
        
        'starters': [{
            'name': d['name'],
            'archetype': d.get('archetype'),
            'enriched_name': d.get('enriched_name'),
            'fingerprint': d.get('fingerprint'),
            'dimensions': d.get('quantum', {}).get('dimensions', {}),
            'overall_score': d.get('quantum', {}).get('overall_score', 0),
            'is_target': d.get('exploit_info', {}).get('is_target', False)
        } for d in starters],
        
        'targets': [{
            'name': d['name'],
            'reasons': d.get('exploit_info', {}).get('target_reason', [])
        } for d in targets],
        
        'avg_defensive_score': round(np.mean([d.get('quantum', {}).get('defensive_score', 50) for d in starters]), 1),
        'avg_offensive_score': round(np.mean([d.get('quantum', {}).get('offensive_score', 50) for d in starters]), 1),
        'avg_overall': round(np.mean([d.get('quantum', {}).get('overall_score', 50) for d in starters]), 1),
        
        'exploit_paths': []
    }
    
    # Générer les exploit paths
    if targets:
        target_names = [t['name'] for t in line['targets']]
        line['exploit_paths'].append({
            'market': 'Goals Over / Anytime Scorer',
            'trigger': f"Cibler: {', '.join(target_names[:2])}",
            'edge': 3.0 + len(targets) * 1.5,
            'confidence': 'HIGH' if len(targets) >= 2 else 'MEDIUM'
        })
    
    if line_char == 'HIGH_RISK_HIGH_REWARD':
        line['exploit_paths'].append({
            'market': 'Goals on Counter',
            'trigger': 'Latéraux montés = espaces derrière',
            'edge': 4.5,
            'confidence': 'HIGH'
        })
    
    defensive_lines_v3[team_name] = line

with open(DATA_DIR / 'defensive_lines_quantum_v3.json', 'w') as f:
    json.dump(defensive_lines_v3, f, indent=2, ensure_ascii=False)
print(f"   ✅ defensive_lines_quantum_v3.json ({len(defensive_lines_v3)} lignes)")

# 9. Rapports détaillés
print(f"\n" + "=" * 80)
print("📊 RAPPORT DEFENDER DNA QUANTUM V3.0")
print("=" * 80)

# Par archétype avec exemples
archetypes_to_show = ['FORTRESS_ANCHOR', 'COMPLETE_DEFENDER', 'MARAUDING_FULLBACK', 
                      'BALL_PLAYING_CB', 'MODERN_CB', 'LIABILITY', 'RISK_TAKER']

for arch in archetypes_to_show:
    players = [d for d in defenders if d.get('archetype') == arch]
    if players:
        players.sort(key=lambda x: x.get('quantum', {}).get('overall_score', 0), reverse=True)
        print(f"\n🏷️ {arch} ({len(players)} joueurs):")
        print(f"   {'Nom':<22} | {'Équipe':<18} | {'Score':<6} | Enriched Name")
        print("   " + "-" * 85)
        for p in players[:5]:
            score = p.get('quantum', {}).get('overall_score', 0)
            print(f"   {p['name']:<22} | {p['team']:<18} | {score:5.1f} | {p.get('enriched_name', '')}")

# Lignes exploitables
print(f"\n" + "=" * 80)
print("🎯 LIGNES DÉFENSIVES EXPLOITABLES")
print("=" * 80)

exploitable = [(t, l) for t, l in defensive_lines_v3.items() if l.get('targets')]
exploitable.sort(key=lambda x: len(x[1]['targets']), reverse=True)

print(f"\n   {'Équipe':<25} | {'Character':<20} | {'Targets':<40}")
print("   " + "-" * 95)
for team, line in exploitable[:15]:
    targets = ', '.join([t['name'][:15] for t in line['targets'][:2]])
    print(f"   {team:<25} | {line['line_character']:<20} | {targets}")

# Exemple complet
print(f"\n" + "=" * 80)
print("📋 PROFIL QUANTUM COMPLET: Gabriel (Arsenal)")
print("=" * 80)

gabriel = [d for d in defenders if 'Gabriel' in d.get('name', '') and d.get('team') == 'Arsenal']
if gabriel:
    g = gabriel[0]
    q = g.get('quantum', {})
    dims = q.get('dimensions', {})
    
    print(f"\n   🧬 PROFIL QUANTUM:")
    print(f"      Archétype: {g.get('archetype')}")
    print(f"      Description: {g.get('archetype_description')}")
    print(f"      Enriched Name: {g.get('enriched_name')}")
    print(f"      Fingerprint: {g.get('fingerprint')}")
    
    print(f"\n   📊 8 DIMENSIONS (Percentiles):")
    print(f"      ┌─────────────────────────────────────────┐")
    for dim, val in dims.items():
        bar = '█' * int(val / 5) + '░' * (20 - int(val / 5))
        print(f"      │ {dim:<12}: {bar} {val:5.1f}% │")
    print(f"      └─────────────────────────────────────────┘")
    
    print(f"\n   📈 SCORES COMPOSITES:")
    print(f"      → Défensif: {q.get('defensive_score', 0):.1f}")
    print(f"      → Offensif: {q.get('offensive_score', 0):.1f}")
    print(f"      → Risque: {q.get('risk_score', 0):.1f}")
    print(f"      → Overall: {q.get('overall_score', 0):.1f}")
    
    print(f"\n   🏷️ TRAITS: {g.get('traits', [])}")
    print(f"\n   🎯 EXPLOIT INFO: {g.get('exploit_info', {})}")

print(f"\n{'='*80}")
print(f"✅ DEFENDER DNA QUANTUM V3.0 COMPLET")
print(f"   {len(qualified)} défenseurs qualifiés | {len(defensive_lines_v3)} lignes | 8 dimensions")
print(f"{'='*80}")
