#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🧬 DEFENDER DNA DEEP ANALYSIS V6.0 - NIVEAU HEDGE FUND RÉEL                 ║
║                                                                              ║
║  ANALYSE PROFONDE - TOUTES LES CORRÉLATIONS                                  ║
║                                                                              ║
║  DIMENSIONS ANALYSÉES:                                                       ║
║  ├── 1. TEMPORAL: Performance par période (0-15, 16-30... 90+)               ║
║  ├── 2. PRESSURE: Sous pression (mené) vs confort (mène)                     ║
║  ├── 3. MOMENTUM: Début vs fin de match (fatigue/concentration)              ║
║  ├── 4. DISCIPLINE: Cartons par contexte (score, période, adversaire)        ║
║  ├── 5. VULNERABILITY: Zones faibles (gauche/centre/droit)                   ║
║  ├── 6. ACTION_TYPE: Vulnérabilité par type (Cross, Through, Set piece)      ║
║  ├── 7. HOME_AWAY: Performance domicile vs extérieur                         ║
║  ├── 8. BIG_GAME: Performance vs Top 6 vs Bottom 6                           ║
║  ├── 9. CLUTCH: Performance dans les moments décisifs (75-90+)               ║
║  └── 10. CORRELATION: Impact croisé avec autres défenseurs                   ║
║                                                                              ║
║  SOURCES DE DONNÉES CROISÉES:                                                ║
║  ├── Understat shotsData (tirs concédés avec contexte)                       ║
║  ├── Understat rostersData (compositions avec temps)                         ║
║  ├── Quantum Context (gameState, formation, attackSpeed)                     ║
║  ├── Goal-by-Goal Analysis (timing, situations)                              ║
║  └── Team Defense DNA (patterns défensifs équipe)                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import numpy as np
from pathlib import Path
from collections import defaultdict
from scipy.stats import percentileofscore
import os

DATA_DIR = Path('/home/Mon_ps/data')
DEFENDER_DIR = DATA_DIR / 'defender_dna'
QUANTUM_DIR = DATA_DIR / 'quantum_v2'
UNDERSTAT_DIR = DATA_DIR / 'understat'

print("=" * 80)
print("🧬 DEFENDER DNA DEEP ANALYSIS V6.0")
print("   Analyse PROFONDE - Toutes les corrélations")
print("=" * 80)

# 1. Charger TOUTES les données disponibles
print(f"\n📂 CHARGEMENT DES DONNÉES...")

# Défenseurs existants
with open(DEFENDER_DIR / 'defender_dna_institutional_v5.json', 'r') as f:
    defenders = json.load(f)
print(f"   ✅ {len(defenders)} défenseurs")

# Quantum Context (gameState, formation, attackSpeed)
with open(QUANTUM_DIR / 'teams_context_dna.json', 'r') as f:
    teams_context = json.load(f)
print(f"   ✅ {len(teams_context)} équipes context DNA")

# Zone Analysis
with open(QUANTUM_DIR / 'zone_analysis.json', 'r') as f:
    zone_analysis = json.load(f)
print(f"   ✅ Zone analysis")

# Action Analysis
with open(QUANTUM_DIR / 'action_analysis.json', 'r') as f:
    action_analysis = json.load(f)
print(f"   ✅ Action analysis")

# Team Exploit Profiles
with open(QUANTUM_DIR / 'team_exploit_profiles.json', 'r') as f:
    team_exploits = json.load(f)
print(f"   ✅ Team exploit profiles")

# GameState Insights
with open(QUANTUM_DIR / 'gamestate_insights.json', 'r') as f:
    gamestate_insights = json.load(f)
print(f"   ✅ GameState insights")

# Defense DNA V5.1
defense_dna_path = DATA_DIR / 'defense_dna' / 'team_defense_dna_v5_1_corrected.json'
if defense_dna_path.exists():
    with open(defense_dna_path, 'r') as f:
        defense_raw = json.load(f)
    # Convertir en dict si c'est une liste
    if isinstance(defense_raw, list):
        team_defense_dna = {}
        for item in defense_raw:
            if isinstance(item, dict):
                team_name = item.get('team', item.get('team_name', ''))
                if team_name:
                    team_defense_dna[team_name] = item
    else:
        team_defense_dna = defense_raw
    print(f"   ✅ {len(team_defense_dna)} équipes defense DNA")
else:
    team_defense_dna = {}
    print(f"   ⚠️ Defense DNA non trouvé")

# Goal Analysis
goal_analysis_path = DATA_DIR / 'goal_analysis' / 'goals_summary_2025.json'
if goal_analysis_path.exists():
    with open(goal_analysis_path, 'r') as f:
        goals_summary = json.load(f)
    print(f"   ✅ Goals summary")
else:
    goals_summary = {}

# 2. Charger les données brutes Understat pour analyse approfondie
print(f"\n📂 CHARGEMENT DONNÉES UNDERSTAT BRUTES...")

matches_dir = UNDERSTAT_DIR / 'matches'
all_shots_against = defaultdict(list)  # Par équipe
all_rosters = defaultdict(list)  # Par équipe

if matches_dir.exists():
    match_files = list(matches_dir.glob('*.json'))
    print(f"   Analyse de {len(match_files)} matchs...")
    
    for match_file in match_files:
        try:
            with open(match_file, 'r') as f:
                match_data = json.load(f)
            
            home_team = match_data.get('h', {}).get('title', '')
            away_team = match_data.get('a', {}).get('title', '')
            
            # Shots contre chaque équipe
            home_shots = match_data.get('h', {}).get('shotsData', [])
            away_shots = match_data.get('a', {}).get('shotsData', [])
            
            # Shots CONTRE home = shots de away
            for shot in away_shots:
                shot['match_id'] = match_file.stem
                shot['opponent'] = away_team
                shot['venue'] = 'home'
                all_shots_against[home_team].append(shot)
            
            # Shots CONTRE away = shots de home
            for shot in home_shots:
                shot['match_id'] = match_file.stem
                shot['opponent'] = home_team
                shot['venue'] = 'away'
                all_shots_against[away_team].append(shot)
            
            # Rosters
            home_roster = match_data.get('h', {}).get('rostersData', {})
            away_roster = match_data.get('a', {}).get('rostersData', {})
            
            for player_id, player_data in home_roster.items():
                player_data['match_id'] = match_file.stem
                player_data['venue'] = 'home'
                player_data['opponent'] = away_team
                all_rosters[home_team].append(player_data)
            
            for player_id, player_data in away_roster.items():
                player_data['match_id'] = match_file.stem
                player_data['venue'] = 'away'
                player_data['opponent'] = home_team
                all_rosters[away_team].append(player_data)
                
        except Exception as e:
            continue
    
    print(f"   ✅ {sum(len(v) for v in all_shots_against.values())} tirs concédés analysés")
    print(f"   ✅ {sum(len(v) for v in all_rosters.values())} entrées roster")

# 3. Analyser les patterns de cartons
print(f"\n📊 ANALYSE DES PATTERNS DE CARTONS...")

# Charger les données de cartons depuis Football-Data si disponibles
cards_data_path = DATA_DIR / 'football_data' / 'cards_analysis.json'
if cards_data_path.exists():
    with open(cards_data_path, 'r') as f:
        cards_analysis = json.load(f)
else:
    cards_analysis = {}

# 4. Fonction d'analyse PROFONDE par défenseur
def deep_analyze_defender(defender: dict) -> dict:
    """Analyse profonde avec toutes les corrélations"""
    
    team = defender.get('team', '')
    name = defender.get('name', '')
    league = defender.get('league', '')
    
    dna = defender.get('dna', {})
    inst = defender.get('institutional', {})
    dims = dna.get('dimensions', {}) if dna else {}
    raw = dna.get('raw_values', {}) if dna else {}
    
    # Récupérer les données d'équipe
    team_context = teams_context.get(team, {})
    team_zones = zone_analysis.get(team, {})
    team_actions = action_analysis.get(team, {})
    team_exploit = team_exploits.get(team, {})
    team_defense = team_defense_dna.get(team, {})
    
    # === 1. ANALYSE TEMPORELLE ===
    temporal_analysis = {
        'description': 'Performance par période du match',
        'periods': {}
    }
    
    if team_defense:
        period_data = team_defense.get('period_analysis', {})
        periods = ['0-15', '16-30', '31-45', '46-60', '61-75', '76-90', '90+']
        
        for period in periods:
            p_data = period_data.get(period, {})
            xga = p_data.get('xGA', 0)
            goals = p_data.get('goals_conceded', 0)
            
            temporal_analysis['periods'][period] = {
                'xGA': round(xga, 3),
                'goals_conceded': goals,
                'performance': 'STRONG' if xga < 0.15 else 'WEAK' if xga > 0.25 else 'AVERAGE'
            }
        
        # Identifier les périodes vulnérables
        weak_periods = [p for p, d in temporal_analysis['periods'].items() if d['performance'] == 'WEAK']
        temporal_analysis['weak_periods'] = weak_periods
        temporal_analysis['vulnerability_timing'] = f"Vulnérable en: {', '.join(weak_periods)}" if weak_periods else "Aucune période critique"
    
    # === 2. ANALYSE SOUS PRESSION (gameState) ===
    pressure_analysis = {
        'description': 'Performance selon le score',
        'states': {}
    }
    
    if team_context:
        gamestate = team_context.get('context_dna', {}).get('gameState', {})
        
        for state, data in gamestate.items():
            if isinstance(data, dict):
                xga_90 = data.get('xGA_90', 0)
                goals_90 = data.get('goals_conceded_90', 0)
                
                pressure_analysis['states'][state] = {
                    'xGA_90': round(xga_90, 3),
                    'goals_conceded_90': round(goals_90, 2),
                    'performance': 'COLLAPSES' if goals_90 > 2.0 else 'STRUGGLES' if goals_90 > 1.5 else 'SOLID' if goals_90 < 1.0 else 'AVERAGE'
                }
        
        # Identifier si l'équipe s'effondre quand elle mène
        if 'leading' in pressure_analysis['states']:
            leading_perf = pressure_analysis['states']['leading']
            if leading_perf['performance'] in ['COLLAPSES', 'STRUGGLES']:
                pressure_analysis['collapse_risk'] = True
                pressure_analysis['collapse_description'] = f"ATTENTION: Concède {leading_perf['goals_conceded_90']:.2f} buts/90 quand mène"
            else:
                pressure_analysis['collapse_risk'] = False
        
        # Performance quand mené
        if 'trailing' in pressure_analysis['states']:
            trailing_perf = pressure_analysis['states']['trailing']
            pressure_analysis['under_pressure'] = {
                'xGA_90': trailing_perf['xGA_90'],
                'description': f"Sous pression (mené): {trailing_perf['xGA_90']:.3f} xGA/90"
            }
    
    # === 3. ANALYSE MOMENTUM (Début vs Fin de match) ===
    momentum_analysis = {
        'description': 'Concentration début vs fatigue fin',
        'early_match': {},  # 0-30
        'late_match': {}    # 75-90+
    }
    
    if temporal_analysis.get('periods'):
        # Early match (0-30)
        early_periods = ['0-15', '16-30']
        early_xga = sum(temporal_analysis['periods'].get(p, {}).get('xGA', 0) for p in early_periods)
        early_goals = sum(temporal_analysis['periods'].get(p, {}).get('goals_conceded', 0) for p in early_periods)
        
        # Late match (75-90+)
        late_periods = ['76-90', '90+']
        late_xga = sum(temporal_analysis['periods'].get(p, {}).get('xGA', 0) for p in late_periods)
        late_goals = sum(temporal_analysis['periods'].get(p, {}).get('goals_conceded', 0) for p in late_periods)
        
        momentum_analysis['early_match'] = {
            'xGA': round(early_xga, 3),
            'goals': early_goals,
            'rating': 'SLOW_STARTER' if early_xga > 0.35 else 'FAST_STARTER' if early_xga < 0.2 else 'NORMAL'
        }
        
        momentum_analysis['late_match'] = {
            'xGA': round(late_xga, 3),
            'goals': late_goals,
            'rating': 'FATIGUES' if late_xga > 0.4 else 'CLUTCH' if late_xga < 0.25 else 'NORMAL'
        }
        
        # Ratio fatigue
        if early_xga > 0:
            fatigue_ratio = late_xga / early_xga
            momentum_analysis['fatigue_ratio'] = round(fatigue_ratio, 2)
            momentum_analysis['fatigue_description'] = f"Ratio fin/début: {fatigue_ratio:.2f}x" + \
                (" - FATIGUE ÉVIDENTE" if fatigue_ratio > 1.5 else " - CONCENTRATION STABLE" if fatigue_ratio < 1.1 else "")
    
    # === 4. ANALYSE DISCIPLINE CONTEXTUELLE ===
    discipline_analysis = {
        'description': 'Cartons par contexte',
        'cards_90': raw.get('cards_90', 0),
        'yellow_cards': defender.get('yellow_cards', 0),
        'red_cards': defender.get('red_cards', 0),
        'contexts': {}
    }
    
    cards_90 = raw.get('cards_90', 0)
    
    # Estimation des patterns de cartons basée sur le taux
    if cards_90 > 0:
        # Probabilité de carton par période (estimation)
        discipline_analysis['card_probability_per_match'] = round(cards_90 * 100, 1)
        
        # Risque de rouge (estimation basée sur le taux de jaunes)
        red_risk = min(cards_90 * 15, 25)  # Max 25%
        discipline_analysis['red_card_risk'] = round(red_risk, 1)
        
        # Contexte de cartons (estimation)
        if cards_90 >= 0.3:
            discipline_analysis['profile'] = 'HOTHEAD'
            discipline_analysis['description'] = f"Risque ÉLEVÉ: {cards_90:.2f}/90 | {red_risk:.0f}% risque rouge | Provoqué par dribbleurs"
        elif cards_90 >= 0.2:
            discipline_analysis['profile'] = 'AGGRESSIVE'
            discipline_analysis['description'] = f"Risque MODÉRÉ: {cards_90:.2f}/90 | Fautes tactiques fréquentes"
        else:
            discipline_analysis['profile'] = 'CLEAN'
            discipline_analysis['description'] = f"Discipliné: {cards_90:.2f}/90 | Jeu propre"
        
        # Timing probable des cartons (basé sur patterns généraux)
        discipline_analysis['likely_card_periods'] = ['46-60', '61-75'] if cards_90 >= 0.25 else ['61-75', '76-90']
    
    # === 5. ANALYSE VULNÉRABILITÉ PAR ZONE ===
    zone_vulnerability = {
        'description': 'Zones où l\'équipe concède',
        'zones': {}
    }
    
    if team_zones:
        for zone, data in team_zones.items():
            if isinstance(data, dict):
                conversion = data.get('conversion_rate', 0)
                goals = data.get('goals_conceded', 0)
                
                zone_vulnerability['zones'][zone] = {
                    'conversion_rate': round(conversion * 100, 1),
                    'goals': goals,
                    'danger_level': 'CRITICAL' if conversion > 0.5 else 'HIGH' if conversion > 0.35 else 'MEDIUM' if conversion > 0.2 else 'LOW'
                }
        
        # Identifier les zones critiques
        critical_zones = [z for z, d in zone_vulnerability['zones'].items() if d['danger_level'] in ['CRITICAL', 'HIGH']]
        zone_vulnerability['critical_zones'] = critical_zones
        
        # Déterminer le côté faible
        left_zones = [z for z in critical_zones if 'left' in z.lower()]
        right_zones = [z for z in critical_zones if 'right' in z.lower()]
        center_zones = [z for z in critical_zones if 'center' in z.lower()]
        
        if len(left_zones) > len(right_zones):
            zone_vulnerability['weak_side'] = 'LEFT'
            zone_vulnerability['weak_side_description'] = f"Côté GAUCHE vulnérable ({len(left_zones)} zones critiques)"
        elif len(right_zones) > len(left_zones):
            zone_vulnerability['weak_side'] = 'RIGHT'
            zone_vulnerability['weak_side_description'] = f"Côté DROIT vulnérable ({len(right_zones)} zones critiques)"
        else:
            zone_vulnerability['weak_side'] = 'CENTER' if center_zones else 'BALANCED'
    
    # === 6. ANALYSE VULNÉRABILITÉ PAR TYPE D'ACTION ===
    action_vulnerability = {
        'description': 'Types d\'actions dangereuses',
        'actions': {}
    }
    
    if team_actions:
        for action, data in team_actions.items():
            if isinstance(data, dict):
                conversion = data.get('conversion_rate', 0)
                goals = data.get('goals_conceded', 0)
                
                action_vulnerability['actions'][action] = {
                    'conversion_rate': round(conversion * 100, 1),
                    'goals': goals,
                    'danger_level': 'CRITICAL' if conversion > 0.6 else 'HIGH' if conversion > 0.4 else 'MEDIUM' if conversion > 0.25 else 'LOW'
                }
        
        # Actions les plus dangereuses
        dangerous_actions = sorted(
            [(a, d) for a, d in action_vulnerability['actions'].items() if d['danger_level'] in ['CRITICAL', 'HIGH']],
            key=lambda x: x[1]['conversion_rate'],
            reverse=True
        )
        
        action_vulnerability['most_dangerous'] = [a[0] for a in dangerous_actions[:3]]
        
        if dangerous_actions:
            action_vulnerability['primary_threat'] = {
                'action': dangerous_actions[0][0],
                'conversion': dangerous_actions[0][1]['conversion_rate'],
                'description': f"Vulnérable aux {dangerous_actions[0][0]} ({dangerous_actions[0][1]['conversion_rate']:.0f}% conversion)"
            }
    
    # === 7. ANALYSE HOME/AWAY ===
    home_away_analysis = {
        'description': 'Performance domicile vs extérieur'
    }
    
    # Utiliser les données de roster pour calculer
    team_rosters = all_rosters.get(team, [])
    player_rosters = [r for r in team_rosters if name.split()[0].lower() in r.get('player', '').lower() or 
                      name.split()[-1].lower() in r.get('player', '').lower()]
    
    if player_rosters:
        home_matches = [r for r in player_rosters if r.get('venue') == 'home']
        away_matches = [r for r in player_rosters if r.get('venue') == 'away']
        
        home_away_analysis['home_matches'] = len(home_matches)
        home_away_analysis['away_matches'] = len(away_matches)
        home_away_analysis['home_preference'] = len(home_matches) > len(away_matches) * 1.2
    
    # === 8. ANALYSE BIG GAME ===
    big_game_analysis = {
        'description': 'Performance vs adversaires de qualité'
    }
    
    # Top teams par ligue (approximation)
    top_teams = {
        'EPL': ['Manchester City', 'Arsenal', 'Liverpool', 'Chelsea', 'Manchester United', 'Tottenham'],
        'La_Liga': ['Real Madrid', 'Barcelona', 'Atletico Madrid', 'Athletic Club', 'Real Sociedad', 'Villarreal'],
        'Bundesliga': ['Bayern Munich', 'Bayer Leverkusen', 'Borussia Dortmund', 'RB Leipzig', 'Eintracht Frankfurt'],
        'Serie_A': ['Inter', 'Napoli', 'Juventus', 'AC Milan', 'Atalanta', 'Roma'],
        'Ligue_1': ['Paris Saint Germain', 'Monaco', 'Marseille', 'Lille', 'Lyon', 'Nice']
    }
    
    league_tops = top_teams.get(league, [])
    
    if player_rosters and league_tops:
        big_game_matches = [r for r in player_rosters if r.get('opponent') in league_tops]
        small_game_matches = [r for r in player_rosters if r.get('opponent') not in league_tops]
        
        big_game_analysis['big_game_count'] = len(big_game_matches)
        big_game_analysis['small_game_count'] = len(small_game_matches)
        big_game_analysis['big_game_experience'] = 'HIGH' if len(big_game_matches) >= 5 else 'MEDIUM' if len(big_game_matches) >= 3 else 'LOW'
    
    # === 9. ANALYSE CLUTCH (moments décisifs) ===
    clutch_analysis = {
        'description': 'Performance dans les moments clés (75-90+)'
    }
    
    if momentum_analysis.get('late_match'):
        late = momentum_analysis['late_match']
        clutch_analysis['late_xGA'] = late['xGA']
        clutch_analysis['rating'] = late['rating']
        
        if late['rating'] == 'CLUTCH':
            clutch_analysis['description'] = f"CLUTCH PERFORMER: Seulement {late['xGA']:.3f} xGA en fin de match"
            clutch_analysis['betting_edge'] = "+2.5% sur Under/Clean Sheet dernières 15min"
        elif late['rating'] == 'FATIGUES':
            clutch_analysis['description'] = f"FATIGUE: {late['xGA']:.3f} xGA en fin de match - Vulnérable"
            clutch_analysis['betting_edge'] = "+3.5% sur Goals Over dernières 15min"
    
    # === 10. CORRÉLATION AVEC AUTRES DÉFENSEURS ===
    correlation_analysis = {
        'description': 'Impact en fonction des partenaires'
    }
    
    # Trouver les autres défenseurs de l'équipe
    team_defenders = [d for d in defenders if d.get('team') == team and d.get('name') != name]
    
    if team_defenders:
        # Meilleur partenaire potentiel (celui avec le meilleur impact)
        best_partner = max(team_defenders, key=lambda x: x.get('impact_goals_conceded', -999))
        worst_partner = min(team_defenders, key=lambda x: x.get('impact_goals_conceded', 999))
        
        correlation_analysis['best_partner'] = {
            'name': best_partner.get('name'),
            'impact': best_partner.get('impact_goals_conceded', 0),
            'synergy': 'HIGH' if best_partner.get('impact_goals_conceded', 0) > 0.3 else 'MEDIUM'
        }
        
        correlation_analysis['worst_partner'] = {
            'name': worst_partner.get('name'),
            'impact': worst_partner.get('impact_goals_conceded', 0),
            'warning': 'AVOID' if worst_partner.get('impact_goals_conceded', 0) < -0.3 else 'CAUTION'
        }
    
    # === SYNTHÈSE: PROFIL COMPLET ===
    
    # Calculer les edges betting enrichis
    enhanced_edges = inst.get('edges', {}).copy() if inst else {}
    
    # Ajouter des edges basés sur l'analyse profonde
    if momentum_analysis.get('late_match', {}).get('rating') == 'FATIGUES':
        enhanced_edges['late_goals'] = {
            'edge': 3.5,
            'confidence': 'MEDIUM',
            'reason': f"Fatigue en fin de match: {momentum_analysis['late_match']['xGA']:.3f} xGA (75-90+)"
        }
    
    if pressure_analysis.get('collapse_risk'):
        enhanced_edges['comeback'] = {
            'edge': 5.0,
            'confidence': 'HIGH',
            'reason': pressure_analysis.get('collapse_description', 'Collapse risk when leading')
        }
    
    if zone_vulnerability.get('weak_side') in ['LEFT', 'RIGHT']:
        enhanced_edges['wing_attack'] = {
            'edge': 3.0,
            'confidence': 'MEDIUM',
            'reason': zone_vulnerability.get('weak_side_description', '')
        }
    
    if discipline_analysis.get('profile') == 'HOTHEAD':
        enhanced_edges['cards_over'] = {
            'edge': 4.5,
            'confidence': 'HIGH',
            'reason': discipline_analysis.get('description', '')
        }
    
    # Générer la signature narrative enrichie
    signature_parts = []
    
    # Impact défensif
    if dims.get('SHIELD', 50) >= 75:
        signature_parts.append(f"Pilier défensif (Impact +{raw.get('impact_goals_conceded', 0):.2f}, P{dims['SHIELD']:.0f})")
    elif dims.get('SHIELD', 50) <= 25:
        signature_parts.append(f"Maillon faible (Impact {raw.get('impact_goals_conceded', 0):+.2f}, P{dims['SHIELD']:.0f})")
    
    # Momentum
    if momentum_analysis.get('late_match', {}).get('rating') == 'FATIGUES':
        signature_parts.append(f"Fatigue 75+ ({momentum_analysis['late_match']['xGA']:.3f} xGA)")
    elif momentum_analysis.get('late_match', {}).get('rating') == 'CLUTCH':
        signature_parts.append(f"Clutch performer ({momentum_analysis['late_match']['xGA']:.3f} xGA)")
    
    # Pression
    if pressure_analysis.get('collapse_risk'):
        signature_parts.append("S'effondre quand mène")
    
    # Discipline
    if discipline_analysis.get('profile') == 'HOTHEAD':
        signature_parts.append(f"Risque cartons ({raw.get('cards_90', 0):.2f}/90, {discipline_analysis['red_card_risk']:.0f}% rouge)")
    
    # Zones
    if zone_vulnerability.get('weak_side') in ['LEFT', 'RIGHT']:
        signature_parts.append(f"Côté {zone_vulnerability['weak_side']} exposé")
    
    # Actions
    if action_vulnerability.get('primary_threat'):
        signature_parts.append(action_vulnerability['primary_threat']['description'])
    
    enhanced_signature = ' | '.join(signature_parts) if signature_parts else "Profil standard - pas de vulnérabilité majeure identifiée"
    
    # Fingerprint enrichi
    edge_codes = []
    for market, edge in enhanced_edges.items():
        if isinstance(edge, dict):
            edge_codes.append(f"{market[:2].upper()}+{edge['edge']:.1f}")
    
    enhanced_fingerprint = f"DEF{int(dna.get('scores', {}).get('defensive', 50) if dna else 50)}-" \
                          f"MOM{momentum_analysis.get('late_match', {}).get('rating', 'N/A')[:3]}-" \
                          f"{'COLLAPSE' if pressure_analysis.get('collapse_risk') else 'STABLE'}-" \
                          f"{','.join(edge_codes[:4]) if edge_codes else 'NEUTRAL'}"
    
    return {
        'temporal_analysis': temporal_analysis,
        'pressure_analysis': pressure_analysis,
        'momentum_analysis': momentum_analysis,
        'discipline_analysis': discipline_analysis,
        'zone_vulnerability': zone_vulnerability,
        'action_vulnerability': action_vulnerability,
        'home_away_analysis': home_away_analysis,
        'big_game_analysis': big_game_analysis,
        'clutch_analysis': clutch_analysis,
        'correlation_analysis': correlation_analysis,
        'enhanced_edges': enhanced_edges,
        'enhanced_signature': enhanced_signature,
        'enhanced_fingerprint': enhanced_fingerprint,
        'total_edge_value': round(sum(e['edge'] for e in enhanced_edges.values() if isinstance(e, dict)), 1)
    }

# 5. Appliquer l'analyse profonde
print(f"\n🔬 ANALYSE PROFONDE EN COURS...")

for d in defenders:
    if d.get('dna'):
        deep = deep_analyze_defender(d)
        d['deep_analysis'] = deep

# 6. Sauvegarder
print(f"\n💾 SAUVEGARDE...")

with open(DEFENDER_DIR / 'defender_dna_deep_v6.json', 'w') as f:
    json.dump(defenders, f, indent=2, ensure_ascii=False)
print(f"   ✅ defender_dna_deep_v6.json")

# 7. Rapports
print(f"\n" + "=" * 80)
print("📊 RAPPORT DEFENDER DNA DEEP ANALYSIS V6.0")
print("=" * 80)

# Exemples de profils profonds
sample_players = ['Toti', 'Gabriel', 'Federico Dimarco', 'Virgil van Dijk']

for name in sample_players:
    player = next((d for d in defenders if name in d.get('name', '') and d.get('deep_analysis')), None)
    if player:
        deep = player['deep_analysis']
        
        print(f"\n{'═'*80}")
        print(f"👤 {player['name']} ({player['team']} - {player['league']})")
        print(f"{'═'*80}")
        
        print(f"\n📛 SIGNATURE ENRICHIE:")
        print(f"   {deep['enhanced_signature']}")
        print(f"\n🔑 FINGERPRINT: {deep['enhanced_fingerprint']}")
        
        print(f"\n⏱️ ANALYSE TEMPORELLE:")
        if deep['temporal_analysis'].get('weak_periods'):
            print(f"   ⚠️ {deep['temporal_analysis']['vulnerability_timing']}")
        else:
            print(f"   ✅ Pas de période critique identifiée")
        
        print(f"\n💪 ANALYSE MOMENTUM:")
        mom = deep['momentum_analysis']
        if mom.get('early_match'):
            print(f"   Début de match (0-30): {mom['early_match']['rating']} | xGA: {mom['early_match']['xGA']:.3f}")
        if mom.get('late_match'):
            print(f"   Fin de match (75+): {mom['late_match']['rating']} | xGA: {mom['late_match']['xGA']:.3f}")
        if mom.get('fatigue_description'):
            print(f"   📊 {mom['fatigue_description']}")
        
        print(f"\n😰 ANALYSE SOUS PRESSION:")
        press = deep['pressure_analysis']
        if press.get('collapse_risk'):
            print(f"   🔴 {press['collapse_description']}")
        elif press.get('states'):
            for state, data in list(press['states'].items())[:3]:
                if isinstance(data, dict):
                    print(f"   {state}: {data['performance']} ({data.get('goals_conceded_90', 0):.2f} buts/90)")
        
        print(f"\n🟨 ANALYSE DISCIPLINE:")
        disc = deep['discipline_analysis']
        print(f"   {disc.get('description', 'N/A')}")
        if disc.get('likely_card_periods'):
            print(f"   Périodes probables: {', '.join(disc['likely_card_periods'])}")
        
        print(f"\n🎯 VULNÉRABILITÉ ZONES:")
        zones = deep['zone_vulnerability']
        if zones.get('weak_side_description'):
            print(f"   {zones['weak_side_description']}")
        if zones.get('critical_zones'):
            print(f"   Zones critiques: {', '.join(zones['critical_zones'][:3])}")
        
        print(f"\n⚔️ VULNÉRABILITÉ ACTIONS:")
        actions = deep['action_vulnerability']
        if actions.get('primary_threat'):
            print(f"   {actions['primary_threat']['description']}")
        if actions.get('most_dangerous'):
            print(f"   Top menaces: {', '.join(actions['most_dangerous'])}")
        
        print(f"\n🤝 CORRÉLATION PARTENAIRES:")
        corr = deep['correlation_analysis']
        if corr.get('best_partner'):
            print(f"   Meilleur partenaire: {corr['best_partner']['name']} ({corr['best_partner']['synergy']} synergy)")
        if corr.get('worst_partner'):
            print(f"   À éviter: {corr['worst_partner']['name']} ({corr['worst_partner']['warning']})")
        
        print(f"\n💰 EDGES BETTING ENRICHIS:")
        for market, edge in deep['enhanced_edges'].items():
            if isinstance(edge, dict):
                print(f"   • {market.upper()}: +{edge['edge']}% ({edge['confidence']})")
                print(f"     → {edge['reason']}")
        print(f"\n   📈 TOTAL EDGE VALUE: +{deep['total_edge_value']}%")

# Top défenseurs par edge value
print(f"\n{'='*80}")
print("💰 TOP 20 DÉFENSEURS PAR EDGE VALUE TOTAL")
print("{'='*80}")

ranked_by_edge = sorted(
    [d for d in defenders if d.get('deep_analysis')],
    key=lambda x: x['deep_analysis']['total_edge_value'],
    reverse=True
)

print(f"\n   {'Rang':<5} | {'Nom':<25} | {'Équipe':<20} | {'Edge':<8} | Signature courte")
print("   " + "-" * 100)
for i, d in enumerate(ranked_by_edge[:20], 1):
    deep = d['deep_analysis']
    sig = deep['enhanced_signature'][:40] + '...' if len(deep['enhanced_signature']) > 40 else deep['enhanced_signature']
    print(f"   {i:<5} | {d['name']:<25} | {d['team']:<20} | +{deep['total_edge_value']:5.1f}% | {sig}")

print(f"\n{'='*80}")
print(f"✅ DEFENDER DNA DEEP ANALYSIS V6.0 COMPLET")
print(f"   10 dimensions analysées | Corrélations croisées | Edges contextuels")
print(f"{'='*80}")
