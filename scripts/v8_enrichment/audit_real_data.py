#!/usr/bin/env python3
"""
🔬 AUDIT DES DONNÉES RÉELLES DISPONIBLES
Pour construire une vraie analyse quant institutionnelle
"""

import json
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path('/home/Mon_ps/data')

print("=" * 80)
print("🔬 AUDIT COMPLET DES DONNÉES DISPONIBLES")
print("=" * 80)

# 1. Quantum V2 - Structure détaillée
print(f"\n{'='*40}")
print("📊 1. QUANTUM V2 - TEAMS CONTEXT DNA")
print(f"{'='*40}")

with open(DATA_DIR / 'quantum_v2' / 'teams_context_dna.json', 'r') as f:
    teams_context = json.load(f)

sample_team = list(teams_context.keys())[0]
sample = teams_context[sample_team]
print(f"\nÉquipe exemple: {sample_team}")
print(f"Clés disponibles: {list(sample.keys())}")

if 'context_dna' in sample:
    ctx = sample['context_dna']
    print(f"\ncontext_dna clés: {list(ctx.keys())}")
    
    if 'gameState' in ctx:
        print(f"\n  gameState clés: {list(ctx['gameState'].keys())}")
        for state, data in list(ctx['gameState'].items())[:2]:
            print(f"    {state}: {data}")
    
    if 'formation' in ctx:
        print(f"\n  formation clés: {list(ctx['formation'].keys())[:3]}")
        for form, data in list(ctx['formation'].items())[:1]:
            print(f"    {form}: {data}")
    
    if 'attackSpeed' in ctx:
        print(f"\n  attackSpeed: {ctx['attackSpeed']}")

# 2. Defense DNA V5.1
print(f"\n{'='*40}")
print("📊 2. DEFENSE DNA V5.1")
print(f"{'='*40}")

with open(DATA_DIR / 'defense_dna' / 'team_defense_dna_v5_1_corrected.json', 'r') as f:
    defense_raw = json.load(f)

if isinstance(defense_raw, list):
    defense_dict = {item.get('team', ''): item for item in defense_raw if isinstance(item, dict)}
else:
    defense_dict = defense_raw

sample_team = list(defense_dict.keys())[0]
sample = defense_dict[sample_team]
print(f"\nÉquipe exemple: {sample_team}")
print(f"Clés disponibles: {list(sample.keys())[:15]}")

# Chercher les données temporelles
for key in sample.keys():
    if 'period' in key.lower() or 'timing' in key.lower() or 'minute' in key.lower():
        print(f"\n  {key}: {sample[key]}")

# 3. Players Impact DNA
print(f"\n{'='*40}")
print("📊 3. PLAYERS IMPACT DNA")
print(f"{'='*40}")

with open(DATA_DIR / 'quantum_v2' / 'players_impact_dna.json', 'r') as f:
    players_impact = json.load(f)

print(f"Nombre de joueurs: {len(players_impact)}")
sample_player = players_impact[0] if players_impact else {}
print(f"Clés joueur: {list(sample_player.keys())}")

# Chercher un défenseur connu
gabriel = next((p for p in players_impact if 'Gabriel' in p.get('name', '') and p.get('team') == 'Arsenal'), None)
if gabriel:
    print(f"\nExemple Gabriel (Arsenal):")
    for k, v in gabriel.items():
        print(f"  {k}: {v}")

# 4. Zone Analysis
print(f"\n{'='*40}")
print("📊 4. ZONE ANALYSIS")
print(f"{'='*40}")

with open(DATA_DIR / 'quantum_v2' / 'zone_analysis.json', 'r') as f:
    zones = json.load(f)

sample_team = list(zones.keys())[0]
print(f"\nÉquipe exemple: {sample_team}")
print(f"Zones: {list(zones[sample_team].keys())[:10]}")
for zone, data in list(zones[sample_team].items())[:3]:
    print(f"  {zone}: {data}")

# 5. Action Analysis
print(f"\n{'='*40}")
print("📊 5. ACTION ANALYSIS")
print(f"{'='*40}")

with open(DATA_DIR / 'quantum_v2' / 'action_analysis.json', 'r') as f:
    actions = json.load(f)

sample_team = list(actions.keys())[0]
print(f"\nÉquipe exemple: {sample_team}")
print(f"Actions: {list(actions[sample_team].keys())}")
for action, data in list(actions[sample_team].items())[:3]:
    print(f"  {action}: {data}")

# 6. GameState Insights
print(f"\n{'='*40}")
print("📊 6. GAMESTATE INSIGHTS")
print(f"{'='*40}")

with open(DATA_DIR / 'quantum_v2' / 'gamestate_insights.json', 'r') as f:
    gamestate = json.load(f)

print(f"Clés: {list(gamestate.keys())}")
for key in list(gamestate.keys())[:2]:
    print(f"\n{key}:")
    if isinstance(gamestate[key], list):
        for item in gamestate[key][:3]:
            print(f"  {item}")
    elif isinstance(gamestate[key], dict):
        for k, v in list(gamestate[key].items())[:3]:
            print(f"  {k}: {v}")

# 7. Team Exploit Profiles
print(f"\n{'='*40}")
print("📊 7. TEAM EXPLOIT PROFILES")
print(f"{'='*40}")

with open(DATA_DIR / 'quantum_v2' / 'team_exploit_profiles.json', 'r') as f:
    exploits = json.load(f)

# Trouver Wolverhampton
wolves = exploits.get('Wolverhampton Wanderers', {})
print(f"\nWolverhampton Wanderers:")
for k, v in wolves.items():
    if isinstance(v, (str, int, float)):
        print(f"  {k}: {v}")
    elif isinstance(v, list) and v:
        print(f"  {k}: {v[:3]}...")
    elif isinstance(v, dict):
        print(f"  {k}: {list(v.keys())[:5]}")

# 8. Defender DNA existant
print(f"\n{'='*40}")
print("📊 8. DEFENDER DNA V5 (Institutional)")
print(f"{'='*40}")

with open(DATA_DIR / 'defender_dna' / 'defender_dna_institutional_v5.json', 'r') as f:
    defenders = json.load(f)

# Trouver Toti
toti = next((d for d in defenders if 'Toti' in d.get('name', '')), None)
if toti:
    print(f"\nToti ({toti.get('team')}):")
    print(f"  Clés principales: {list(toti.keys())}")
    if toti.get('dna'):
        print(f"  DNA dimensions: {toti['dna'].get('dimensions', {})}")
        print(f"  DNA raw_values: {toti['dna'].get('raw_values', {})}")
    if toti.get('institutional'):
        print(f"  Institutional clés: {list(toti['institutional'].keys())}")

# 9. Vérifier Football-Data
print(f"\n{'='*40}")
print("📊 9. FOOTBALL-DATA (si disponible)")
print(f"{'='*40}")

fd_dir = DATA_DIR / 'football_data'
if fd_dir.exists():
    files = list(fd_dir.glob('*.csv')) + list(fd_dir.glob('*.json'))
    print(f"Fichiers: {[f.name for f in files[:10]]}")
    
    # Charger un fichier CSV si existe
    csv_files = list(fd_dir.glob('*.csv'))
    if csv_files:
        import csv
        with open(csv_files[0], 'r') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            print(f"\nColonnes CSV ({csv_files[0].name}): {headers[:20]}")
else:
    print("Pas de données Football-Data")

# 10. Résumé des données exploitables
print(f"\n{'='*80}")
print("📋 RÉSUMÉ: DONNÉES EXPLOITABLES POUR ANALYSE QUANT")
print(f"{'='*80}")

print("""
✅ DONNÉES DISPONIBLES:
   - Teams Context DNA: gameState (mené/mène), formation, attackSpeed
   - Defense DNA: xGA par situation, période, type
   - Zone Analysis: conversion par zone (left/center/right, penalty/six_yard)
   - Action Analysis: conversion par lastAction (Cross, Pass, TakeOn, etc.)
   - GameState Insights: équipes qui collapse, dangereuses quand menées
   - Players Impact: xGChain, xGBuildup, xA, goals, assists par joueur
   - Exploit Profiles: vulnérabilités identifiées par équipe

❌ DONNÉES MANQUANTES POUR ANALYSE INDIVIDUELLE:
   - Pas de stats INDIVIDUELLES par période (joueur X concède en 75-90)
   - Pas de cartons par contexte (match score, adversaire)
   - Pas de performance home/away par joueur
   - Pas de corrélation directe joueur-tirs concédés

🎯 STRATÉGIE RECOMMANDÉE:
   1. Utiliser les données ÉQUIPE comme proxy pour les défenseurs
   2. Pondérer par temps de jeu du défenseur
   3. Croiser avec les exploit profiles équipe
   4. Calculer la contribution RELATIVE du défenseur aux faiblesses équipe
""")
