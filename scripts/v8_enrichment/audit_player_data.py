#!/usr/bin/env python3
"""
🔬 AUDIT DES DONNÉES JOUEURS SCRAPÉES
"""

import json
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path('/home/Mon_ps/data')

print("=" * 80)
print("🔬 AUDIT DES DONNÉES JOUEURS")
print("=" * 80)

# 1. Players Impact DNA
print(f"\n{'='*40}")
print("📊 PLAYERS IMPACT DNA")
print(f"{'='*40}")

with open(DATA_DIR / 'quantum_v2' / 'players_impact_dna.json', 'r') as f:
    players_impact = json.load(f)

print(f"Type: {type(players_impact)}")

if isinstance(players_impact, dict):
    print(f"Clés principales: {list(players_impact.keys())[:10]}")
    # Première équipe
    first_team = list(players_impact.keys())[0]
    print(f"\nÉquipe: {first_team}")
    print(f"Type données équipe: {type(players_impact[first_team])}")
    
    if isinstance(players_impact[first_team], list):
        print(f"Nombre joueurs: {len(players_impact[first_team])}")
        if players_impact[first_team]:
            sample = players_impact[first_team][0]
            print(f"\nClés joueur: {list(sample.keys())}")
            print(f"\nExemple joueur:")
            for k, v in sample.items():
                print(f"  {k}: {v}")
    elif isinstance(players_impact[first_team], dict):
        print(f"Clés: {list(players_impact[first_team].keys())[:10]}")

# Chercher un défenseur spécifique
print(f"\n{'='*40}")
print("🔍 RECHERCHE DÉFENSEURS CONNUS")
print(f"{'='*40}")

defenders_to_find = ['Gabriel', 'Saliba', 'Toti', 'van Dijk', 'Dimarco']

for team_name, team_data in players_impact.items():
    if isinstance(team_data, list):
        for player in team_data:
            name = player.get('name', player.get('player_name', ''))
            for defender in defenders_to_find:
                if defender.lower() in name.lower():
                    print(f"\n{'─'*60}")
                    print(f"👤 {name} ({team_name})")
                    print(f"{'─'*60}")
                    for k, v in player.items():
                        print(f"  {k}: {v}")
                    break

# 2. Vérifier les données de défenseurs existantes
print(f"\n{'='*40}")
print("📊 DEFENDER DNA EXISTANT")
print(f"{'='*40}")

with open(DATA_DIR / 'defender_dna' / 'defender_dna_institutional_v5.json', 'r') as f:
    defenders = json.load(f)

print(f"Nombre défenseurs: {len(defenders)}")

# Trouver Toti
toti = next((d for d in defenders if 'Toti' in d.get('name', '')), None)
if toti:
    print(f"\n{'─'*60}")
    print(f"👤 TOTI - DONNÉES COMPLÈTES")
    print(f"{'─'*60}")
    
    # Afficher toutes les clés de premier niveau
    print(f"\nClés disponibles: {list(toti.keys())}")
    
    # Données de base
    print(f"\n📋 DONNÉES DE BASE:")
    for k in ['name', 'team', 'league', 'position', 'time', 'games', 
              'goals', 'assists', 'yellow_cards', 'red_cards',
              'xG', 'xA', 'xGChain', 'xGBuildup']:
        if k in toti:
            print(f"  {k}: {toti[k]}")
    
    # Impact
    print(f"\n📊 IMPACT:")
    for k in ['impact_goals_conceded', 'impact_wins', 'impact_clean_sheets',
              'clean_sheet_rate_with', 'matches_analyzed_with', 'matches_analyzed_without']:
        if k in toti:
            print(f"  {k}: {toti[k]}")
    
    # Per 90
    print(f"\n⚡ PAR 90 MIN:")
    for k in ['xGChain_90', 'xGBuildup_90', 'xA_90', 'cards_90', 'goals_90']:
        if k in toti:
            print(f"  {k}: {toti[k]}")

# 3. Vérifier Teams Context pour données équipe
print(f"\n{'='*40}")
print("📊 WOLVES - DONNÉES ÉQUIPE COMPLÈTES")
print(f"{'='*40}")

with open(DATA_DIR / 'quantum_v2' / 'teams_context_dna.json', 'r') as f:
    teams_context = json.load(f)

wolves = teams_context.get('Wolverhampton Wanderers', {})
if wolves:
    print(f"\nClés: {list(wolves.keys())}")
    
    # Context DNA
    ctx = wolves.get('context_dna', {})
    print(f"\n📊 CONTEXT DNA:")
    
    # GameState
    print(f"\n  🎯 GAMESTATE (comportement selon le score):")
    for state, data in ctx.get('gameState', {}).items():
        print(f"    {state}:")
        for k, v in data.items():
            print(f"      {k}: {v}")
    
    # Formation
    print(f"\n  �� FORMATIONS:")
    for form, data in ctx.get('formation', {}).items():
        print(f"    {form}: {data}")
    
    # Attack Speed vulnerabilities
    print(f"\n  ⚡ VULNÉRABILITÉ PAR VITESSE D'ATTAQUE:")
    for speed, data in ctx.get('attackSpeed', {}).items():
        print(f"    {speed}: conversion_against={data.get('conversion_against', 0)}%")
    
    # Shot Zones
    print(f"\n  🎯 ZONES DE TIR:")
    for zone, data in list(ctx.get('shotZone', {}).items())[:5]:
        print(f"    {zone}: {data}")
    
    # Momentum DNA
    mom = wolves.get('momentum_dna', {})
    print(f"\n  📈 MOMENTUM (Forme récente):")
    for k, v in mom.items():
        print(f"    {k}: {v}")
    
    # History
    hist = wolves.get('history', {})
    if hist:
        print(f"\n  📜 HISTORIQUE MATCHS:")
        for k, v in list(hist.items())[:5]:
            print(f"    {k}: {v}")

# 4. Zone et Action Analysis pour Wolves
print(f"\n{'='*40}")
print("📊 WOLVES - ZONE & ACTION ANALYSIS")
print(f"{'='*40}")

with open(DATA_DIR / 'quantum_v2' / 'zone_analysis.json', 'r') as f:
    zones = json.load(f)

wolves_zones = zones.get('Wolverhampton Wanderers', {})
print(f"\n🎯 ZONES VULNÉRABLES:")
# Trier par conversion
sorted_zones = sorted(wolves_zones.items(), key=lambda x: x[1].get('conversion_rate', 0) if isinstance(x[1], dict) else 0, reverse=True)
for zone, data in sorted_zones[:10]:
    if isinstance(data, dict):
        print(f"  {zone}: {data.get('conversion_rate', 0)*100:.1f}% conversion | {data.get('goals_conceded', 0)} buts")

with open(DATA_DIR / 'quantum_v2' / 'action_analysis.json', 'r') as f:
    actions = json.load(f)

wolves_actions = actions.get('Wolverhampton Wanderers', {})
print(f"\n⚔️ ACTIONS DANGEREUSES:")
sorted_actions = sorted(wolves_actions.items(), key=lambda x: x[1].get('conversion_rate', 0) if isinstance(x[1], dict) else 0, reverse=True)
for action, data in sorted_actions[:10]:
    if isinstance(data, dict):
        print(f"  {action}: {data.get('conversion_rate', 0)*100:.1f}% conversion | {data.get('goals_conceded', 0)} buts")

# 5. Goal Analysis - Timing des buts
print(f"\n{'='*40}")
print("📊 GOAL ANALYSIS - TIMING")  
print(f"{'='*40}")

with open(DATA_DIR / 'goal_analysis' / 'all_goals_2025.json', 'r') as f:
    all_goals = json.load(f)

print(f"Type: {type(all_goals)}")
if isinstance(all_goals, list):
    print(f"Nombre de buts: {len(all_goals)}")
    if all_goals:
        print(f"\nClés d'un but: {list(all_goals[0].keys())}")
        print(f"\nExemple but:")
        for k, v in all_goals[0].items():
            print(f"  {k}: {v}")
        
        # Buts contre Wolves
        wolves_goals = [g for g in all_goals if 'Wolverhampton' in str(g.get('team_against', g.get('h_team', ''))) or 
                       'Wolves' in str(g.get('team_against', g.get('h_team', '')))]
        print(f"\n🐺 Buts contre Wolves: {len(wolves_goals)}")

# 6. Defense DNA V5.1 - Structure détaillée  
print(f"\n{'='*40}")
print("📊 DEFENSE DNA V5.1 - WOLVES")
print(f"{'='*40}")

with open(DATA_DIR / 'defense_dna' / 'team_defense_dna_v5_1_corrected.json', 'r') as f:
    defense_raw = json.load(f)

if isinstance(defense_raw, list):
    wolves_def = next((d for d in defense_raw if 'Wolverhampton' in d.get('team_name', d.get('team', ''))), None)
else:
    wolves_def = defense_raw.get('Wolverhampton Wanderers', {})

if wolves_def:
    print(f"\nClés disponibles ({len(wolves_def.keys())} clés):")
    for k in sorted(wolves_def.keys()):
        v = wolves_def[k]
        if isinstance(v, (int, float, str)):
            print(f"  {k}: {v}")
        elif isinstance(v, dict):
            print(f"  {k}: {list(v.keys())[:5]}...")
        elif isinstance(v, list):
            print(f"  {k}: [{len(v)} items]")

print(f"\n{'='*80}")
print("📋 RÉSUMÉ DES DONNÉES DISPONIBLES PAR JOUEUR")
print(f"{'='*80}")
print("""
✅ DONNÉES INDIVIDUELLES JOUEUR:
   - name, team, league, position
   - time (minutes jouées)
   - goals, assists, xG, xA
   - xGChain (implication dans les buts)
   - xGBuildup (construction du jeu)
   - yellow_cards, red_cards
   - impact_goals_conceded (WITH vs WITHOUT)
   - impact_wins, impact_clean_sheets
   - clean_sheet_rate_with
   - matches_analyzed_with/without

✅ DONNÉES ÉQUIPE (pour contexte):
   - gameState: performance mené/égalité/mène
   - formation: stats par système tactique
   - attackSpeed: vulnérabilité contre-attaques
   - shotZone: zones dangereuses
   - momentum_dna: forme récente
   - zone_analysis: conversion par zone
   - action_analysis: conversion par type d'action

🎯 POUR ADN UNIQUE PAR DÉFENSEUR:
   1. Croiser stats individuelles avec contexte équipe
   2. Calculer la CONTRIBUTION du défenseur aux faiblesses
   3. Identifier les patterns spécifiques (gameState, zones)
   4. Créer un profil vraiment personnalisé
""")
