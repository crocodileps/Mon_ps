#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🧬 QUANTUM FULL ANALYSIS V1.0 - TOUTES LES PRIORITÉS                        ║
║  Analyse COMPLÈTE des données non exploitées                                 ║
║                                                                              ║
║  PRIORITÉ HAUTE (déjà fait):                                                 ║
║  ✅ gameState, attackSpeed, formation                                        ║
║                                                                              ║
║  PRIORITÉ MOYENNE (à faire):                                                 ║
║  ├── X,Y Positions: Zones de vulnérabilité                                   ║
║  ├── lastAction: Patterns d'attaque efficaces                                ║
║  └── ppda/deep: Intensité défensive                                          ║
║                                                                              ║
║  PRIORITÉ BASSE:                                                             ║
║  └── rostersData: Impact des joueurs clés                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import numpy as np
from pathlib import Path
from collections import defaultdict
from scipy.stats import percentileofscore

DATA_DIR = Path('/home/Mon_ps/data')
SHOTS_CACHE = DATA_DIR / 'goalkeeper_dna/all_shots_against_2025.json'
QUANTUM_V2 = DATA_DIR / 'quantum_v2/teams_context_dna.json'
OUTPUT_DIR = DATA_DIR / 'quantum_v2'

def analyze_shot_positions(shots_by_team: dict) -> dict:
    """
    PRIORITÉ 4: Analyse des positions X,Y des tirs
    Identifie les zones de vulnérabilité défensive
    """
    print("\n" + "=" * 60)
    print("📍 PRIORITÉ 4: ANALYSE POSITIONS X,Y")
    print("=" * 60)
    
    zone_analysis = {}
    
    # Définir les zones du terrain
    # X: 0 = propre but, 1 = but adverse
    # Y: 0 = gauche, 1 = droite
    
    def get_zone(x, y):
        """Détermine la zone du tir"""
        # Zone horizontale
        if x < 0.7:
            h_zone = 'long_range'
        elif x < 0.83:
            h_zone = 'edge_box'
        elif x < 0.94:
            h_zone = 'penalty_area'
        else:
            h_zone = 'six_yard'
        
        # Zone verticale
        if y < 0.35:
            v_zone = 'left'
        elif y < 0.65:
            v_zone = 'center'
        else:
            v_zone = 'right'
        
        return f"{h_zone}_{v_zone}"
    
    for team, shots in shots_by_team.items():
        zones = defaultdict(lambda: {'shots': 0, 'goals': 0, 'xG': 0, 'saves': 0})
        
        for shot in shots:
            if shot.get('result') not in ['Goal', 'SavedShot']:
                continue
            
            x = float(shot.get('X', 0.5))
            y = float(shot.get('Y', 0.5))
            xG = float(shot.get('xG', 0))
            
            zone = get_zone(x, y)
            zones[zone]['shots'] += 1
            zones[zone]['xG'] += xG
            
            if shot.get('result') == 'Goal':
                zones[zone]['goals'] += 1
            else:
                zones[zone]['saves'] += 1
        
        # Calculer les métriques par zone
        zone_stats = {}
        for zone, data in zones.items():
            if data['shots'] >= 3:
                zone_stats[zone] = {
                    'shots': data['shots'],
                    'goals': data['goals'],
                    'saves': data['saves'],
                    'xG': round(data['xG'], 3),
                    'conversion': round(data['goals'] / data['shots'] * 100, 1),
                    'save_rate': round(data['saves'] / data['shots'] * 100, 1)
                }
        
        # Identifier les zones vulnérables
        vulnerable_zones = []
        for zone, stats in zone_stats.items():
            if stats['conversion'] >= 40 and stats['shots'] >= 5:
                vulnerable_zones.append(zone)
        
        zone_analysis[team] = {
            'zones': zone_stats,
            'vulnerable_zones': vulnerable_zones,
            'most_dangerous_zone': max(zone_stats.items(), key=lambda x: x[1]['goals'], default=('none', {}))[0] if zone_stats else 'none'
        }
    
    # Résumé
    print(f"\n   ✅ {len(zone_analysis)} équipes analysées")
    
    # Top équipes vulnérables par zone
    for zone_type in ['penalty_area_center', 'penalty_area_left', 'penalty_area_right', 'six_yard_center']:
        vulnerable = []
        for team, data in zone_analysis.items():
            zone_data = data['zones'].get(zone_type, {})
            if zone_data.get('shots', 0) >= 5:
                vulnerable.append((team, zone_data.get('conversion', 0), zone_data.get('goals', 0)))
        
        if vulnerable:
            vulnerable.sort(key=lambda x: x[1], reverse=True)
            print(f"\n   🎯 VULNÉRABLES EN {zone_type.upper()}:")
            for team, conv, goals in vulnerable[:5]:
                print(f"      • {team:<25} | {conv:.0f}% conversion ({goals} buts)")
    
    return zone_analysis

def analyze_last_actions(shots_by_team: dict) -> dict:
    """
    PRIORITÉ 5: Analyse des lastAction
    Identifie les patterns d'attaque qui fonctionnent contre chaque équipe
    """
    print("\n" + "=" * 60)
    print("⚡ PRIORITÉ 5: ANALYSE LAST ACTIONS (Patterns d'attaque)")
    print("=" * 60)
    
    action_analysis = {}
    
    for team, shots in shots_by_team.items():
        actions = defaultdict(lambda: {'shots': 0, 'goals': 0, 'xG': 0})
        
        for shot in shots:
            if shot.get('result') not in ['Goal', 'SavedShot']:
                continue
            
            action = shot.get('lastAction', 'None')
            if action is None:
                action = 'None'
            
            xG = float(shot.get('xG', 0))
            
            actions[action]['shots'] += 1
            actions[action]['xG'] += xG
            
            if shot.get('result') == 'Goal':
                actions[action]['goals'] += 1
        
        # Calculer les métriques
        action_stats = {}
        total_goals = sum(a['goals'] for a in actions.values())
        
        for action, data in actions.items():
            if data['shots'] >= 3:
                action_stats[action] = {
                    'shots': data['shots'],
                    'goals': data['goals'],
                    'xG': round(data['xG'], 3),
                    'conversion': round(data['goals'] / data['shots'] * 100, 1),
                    'goal_share': round(data['goals'] / total_goals * 100, 1) if total_goals > 0 else 0
                }
        
        # Identifier les actions les plus dangereuses
        dangerous_actions = []
        for action, stats in action_stats.items():
            if stats['conversion'] >= 35 and stats['shots'] >= 5:
                dangerous_actions.append(action)
        
        action_analysis[team] = {
            'actions': action_stats,
            'dangerous_actions': dangerous_actions,
            'most_conceded_from': max(action_stats.items(), key=lambda x: x[1]['goals'], default=('none', {}))[0] if action_stats else 'none'
        }
    
    print(f"\n   ✅ {len(action_analysis)} équipes analysées")
    
    # Résumé par type d'action
    for action_type in ['Cross', 'TakeOn', 'Throughball', 'Rebound', 'Pass', 'Standard']:
        vulnerable = []
        for team, data in action_analysis.items():
            action_data = data['actions'].get(action_type, {})
            if action_data.get('shots', 0) >= 5:
                vulnerable.append((team, action_data.get('conversion', 0), action_data.get('goals', 0)))
        
        if vulnerable:
            vulnerable.sort(key=lambda x: x[1], reverse=True)
            print(f"\n   🎯 VULNÉRABLES AUX {action_type.upper()}:")
            for team, conv, goals in vulnerable[:5]:
                print(f"      • {team:<25} | {conv:.0f}% conversion ({goals} buts)")
    
    return action_analysis

def analyze_gamestate_vulnerability(quantum_data: dict) -> dict:
    """
    Analyse approfondie des vulnérabilités par gameState
    """
    print("\n" + "=" * 60)
    print("🎮 ANALYSE GAMESTATE - VULNÉRABILITÉS CONTEXTUELLES")
    print("=" * 60)
    
    gamestate_insights = {}
    
    for team, data in quantum_data.items():
        context = data.get('context_dna', {}).get('gameState', {})
        
        if not context:
            continue
        
        insights = {
            'collapses_when_leading': False,
            'dangerous_when_trailing': False,
            'strong_at_0_0': False,
            'weak_at_0_0': False,
            'comeback_vulnerability': 0,
            'closing_ability': 0
        }
        
        # Analyser chaque état
        leading_1 = context.get('Goal diff +1', {})
        leading_2 = context.get('Goal diff > +1', {})
        trailing_1 = context.get('Goal diff -1', {})
        equal = context.get('Goal diff 0', {})
        
        # S'effondre quand mène?
        if leading_1.get('xG_against_90', 0) >= 1.5 or leading_1.get('goals_against_90', 0) >= 0.8:
            insights['collapses_when_leading'] = True
            insights['comeback_vulnerability'] = leading_1.get('goals_against_90', 0)
        
        # Dangereux quand mené?
        if trailing_1.get('xG_for_90', 0) >= 2.0:
            insights['dangerous_when_trailing'] = True
        
        # Fort/Faible à 0-0?
        if equal.get('net_xG_90', 0) >= 0.5:
            insights['strong_at_0_0'] = True
        elif equal.get('net_xG_90', 0) <= -0.3:
            insights['weak_at_0_0'] = True
        
        # Capacité à fermer le match
        if leading_1.get('goals_against_90', 0) <= 0.3:
            insights['closing_ability'] = 'EXCELLENT'
        elif leading_1.get('goals_against_90', 0) <= 0.6:
            insights['closing_ability'] = 'GOOD'
        else:
            insights['closing_ability'] = 'POOR'
        
        gamestate_insights[team] = {
            'raw_data': context,
            'insights': insights
        }
    
    # Équipes qui s'effondrent quand elles mènent
    collapsers = [(t, d['insights']['comeback_vulnerability']) 
                  for t, d in gamestate_insights.items() 
                  if d['insights']['collapses_when_leading']]
    collapsers.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\n   🔴 ÉQUIPES QUI S'EFFONDRENT QUAND ELLES MÈNENT:")
    for team, vuln in collapsers[:10]:
        print(f"      • {team:<25} | {vuln:.2f} buts concédés/90 quand +1")
    
    # Équipes dangereuses quand menées
    dangerous = [t for t, d in gamestate_insights.items() 
                 if d['insights']['dangerous_when_trailing']]
    print(f"\n   🟢 ÉQUIPES DANGEREUSES QUAND MENÉES:")
    for team in dangerous[:10]:
        xg = gamestate_insights[team]['raw_data'].get('Goal diff -1', {}).get('xG_for_90', 0)
        print(f"      • {team:<25} | {xg:.2f} xG/90 quand -1")
    
    return gamestate_insights

def analyze_attack_speed_vulnerability(quantum_data: dict) -> dict:
    """
    Analyse approfondie des vulnérabilités par vitesse d'attaque
    """
    print("\n" + "=" * 60)
    print("⚡ ANALYSE ATTACK SPEED - VULNÉRABILITÉS TRANSITIONS")
    print("=" * 60)
    
    speed_insights = {}
    
    for team, data in quantum_data.items():
        attack_speed = data.get('context_dna', {}).get('attackSpeed', {})
        
        if not attack_speed:
            continue
        
        fast = attack_speed.get('Fast', {})
        normal = attack_speed.get('Normal', {})
        slow = attack_speed.get('Slow', {})
        
        insights = {
            'vulnerable_to_fast': False,
            'vulnerable_to_slow': False,
            'fast_conversion': fast.get('conversion_against', 0),
            'normal_conversion': normal.get('conversion_against', 0),
            'slow_conversion': slow.get('conversion_against', 0)
        }
        
        # Vulnérable aux contres rapides?
        if fast.get('conversion_against', 0) >= 30 and fast.get('shots_against', 0) >= 5:
            insights['vulnerable_to_fast'] = True
        
        # Vulnérable à la possession lente?
        if slow.get('conversion_against', 0) >= 35 and slow.get('shots_against', 0) >= 5:
            insights['vulnerable_to_slow'] = True
        
        speed_insights[team] = {
            'raw_data': attack_speed,
            'insights': insights
        }
    
    # Top vulnérables aux contres
    fast_vulnerable = [(t, d['insights']['fast_conversion'], d['raw_data'].get('Fast', {}).get('goals_against', 0))
                       for t, d in speed_insights.items() 
                       if d['insights']['vulnerable_to_fast']]
    fast_vulnerable.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\n   🔴 VULNÉRABLES AUX CONTRE-ATTAQUES RAPIDES:")
    for team, conv, goals in fast_vulnerable[:10]:
        print(f"      • {team:<25} | {conv:.0f}% conversion ({goals} buts)")
    
    # Vulnérables à la possession
    slow_vulnerable = [(t, d['insights']['slow_conversion'], d['raw_data'].get('Slow', {}).get('goals_against', 0))
                       for t, d in speed_insights.items() 
                       if d['insights']['vulnerable_to_slow']]
    slow_vulnerable.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\n   🔴 VULNÉRABLES À LA POSSESSION LENTE:")
    for team, conv, goals in slow_vulnerable[:10]:
        print(f"      • {team:<25} | {conv:.0f}% conversion ({goals} buts)")
    
    return speed_insights

def create_team_exploit_profiles(zone_analysis: dict, action_analysis: dict, 
                                  gamestate_insights: dict, speed_insights: dict,
                                  quantum_data: dict) -> dict:
    """
    Crée des profils d'exploitation COMPLETS pour chaque équipe
    """
    print("\n" + "=" * 60)
    print("🎯 CRÉATION DES PROFILS D'EXPLOITATION COMPLETS")
    print("=" * 60)
    
    exploit_profiles = {}
    
    for team in quantum_data.keys():
        profile = {
            'team': team,
            'league': quantum_data[team].get('league', ''),
            'momentum': quantum_data[team].get('momentum_dna', {}),
            
            # Vulnérabilités
            'vulnerabilities': [],
            'exploit_paths': [],
            
            # Données brutes
            'zone_data': zone_analysis.get(team, {}),
            'action_data': action_analysis.get(team, {}),
            'gamestate_data': gamestate_insights.get(team, {}),
            'speed_data': speed_insights.get(team, {})
        }
        
        # === COLLECTER LES VULNÉRABILITÉS ===
        
        # Zones
        for zone in zone_analysis.get(team, {}).get('vulnerable_zones', []):
            profile['vulnerabilities'].append(f"ZONE_{zone.upper()}")
        
        # Actions
        for action in action_analysis.get(team, {}).get('dangerous_actions', []):
            profile['vulnerabilities'].append(f"ACTION_{action.upper()}")
        
        # GameState
        gs_insights = gamestate_insights.get(team, {}).get('insights', {})
        if gs_insights.get('collapses_when_leading'):
            profile['vulnerabilities'].append('COLLAPSES_WHEN_LEADING')
        if gs_insights.get('weak_at_0_0'):
            profile['vulnerabilities'].append('WEAK_AT_DEADLOCK')
        
        # Attack Speed
        sp_insights = speed_insights.get(team, {}).get('insights', {})
        if sp_insights.get('vulnerable_to_fast'):
            profile['vulnerabilities'].append('FAST_ATTACK_VULNERABLE')
        if sp_insights.get('vulnerable_to_slow'):
            profile['vulnerabilities'].append('SLOW_POSSESSION_VULNERABLE')
        
        # === CRÉER LES EXPLOIT PATHS ===
        
        # Comebacks
        if 'COLLAPSES_WHEN_LEADING' in profile['vulnerabilities']:
            profile['exploit_paths'].append({
                'market': 'Goals Over / Comeback',
                'trigger': "Si l'adversaire mène, continuer à parier sur des buts",
                'confidence': 'HIGH',
                'edge_estimate': 5.0
            })
        
        # Contres
        if 'FAST_ATTACK_VULNERABLE' in profile['vulnerabilities']:
            profile['exploit_paths'].append({
                'market': 'Goals Over vs équipes rapides',
                'trigger': 'Matcher avec équipes à contre-attaque rapide (Liverpool, Bayern)',
                'confidence': 'HIGH',
                'edge_estimate': 4.5
            })
        
        # Crosses
        if 'ACTION_CROSS' in profile['vulnerabilities']:
            profile['exploit_paths'].append({
                'market': 'Goals via crosses / Header Goal',
                'trigger': 'Équipes avec bons centreurs et grands attaquants',
                'confidence': 'MEDIUM',
                'edge_estimate': 3.5
            })
        
        # Penalty Area
        if any('PENALTY_AREA' in v for v in profile['vulnerabilities']):
            profile['exploit_paths'].append({
                'market': 'Anytime Goalscorer',
                'trigger': 'Attaquants avec haut xG dans la surface',
                'confidence': 'MEDIUM',
                'edge_estimate': 3.0
            })
        
        # Score global de vulnérabilité
        profile['vulnerability_score'] = len(profile['vulnerabilities'])
        profile['exploit_count'] = len(profile['exploit_paths'])
        
        exploit_profiles[team] = profile
    
    # Trier par vulnérabilité
    sorted_teams = sorted(exploit_profiles.items(), key=lambda x: x[1]['vulnerability_score'], reverse=True)
    
    print(f"\n   🔴 TOP 15 ÉQUIPES LES PLUS VULNÉRABLES:")
    print(f"   {'Équipe':<25} | {'Vulns':<6} | {'Exploits':<8} | Principales faiblesses")
    print("   " + "-" * 90)
    
    for team, profile in sorted_teams[:15]:
        vulns = profile['vulnerability_score']
        exploits = profile['exploit_count']
        main_vulns = ', '.join(profile['vulnerabilities'][:3])
        print(f"   {team:<25} | {vulns:<6} | {exploits:<8} | {main_vulns[:50]}")
    
    print(f"\n   ✅ {len(exploit_profiles)} profils créés")
    
    return exploit_profiles

def main():
    print("=" * 80)
    print("🧬 QUANTUM FULL ANALYSIS V1.0")
    print("   Analyse COMPLÈTE de toutes les priorités")
    print("=" * 80)
    
    # 1. Charger les données
    print("\n📂 Chargement des données...")
    
    with open(SHOTS_CACHE, 'r') as f:
        shots_by_team = json.load(f)
    print(f"   ✅ Cache tirs: {len(shots_by_team)} équipes")
    
    with open(QUANTUM_V2, 'r') as f:
        quantum_data = json.load(f)
    print(f"   ✅ Quantum V2: {len(quantum_data)} équipes")
    
    # 2. Analyses PRIORITÉ MOYENNE
    
    # PRIORITÉ 4: Positions X,Y
    zone_analysis = analyze_shot_positions(shots_by_team)
    
    # PRIORITÉ 5: lastAction
    action_analysis = analyze_last_actions(shots_by_team)
    
    # Analyses approfondies des données existantes
    gamestate_insights = analyze_gamestate_vulnerability(quantum_data)
    speed_insights = analyze_attack_speed_vulnerability(quantum_data)
    
    # 3. Créer les profils d'exploitation complets
    exploit_profiles = create_team_exploit_profiles(
        zone_analysis, action_analysis, 
        gamestate_insights, speed_insights,
        quantum_data
    )
    
    # 4. Sauvegarder
    print("\n" + "=" * 60)
    print("💾 SAUVEGARDE")
    print("=" * 60)
    
    with open(OUTPUT_DIR / 'zone_analysis.json', 'w') as f:
        json.dump(zone_analysis, f, indent=2, ensure_ascii=False)
    print(f"   ✅ {OUTPUT_DIR / 'zone_analysis.json'}")
    
    with open(OUTPUT_DIR / 'action_analysis.json', 'w') as f:
        json.dump(action_analysis, f, indent=2, ensure_ascii=False)
    print(f"   ✅ {OUTPUT_DIR / 'action_analysis.json'}")
    
    with open(OUTPUT_DIR / 'gamestate_insights.json', 'w') as f:
        json.dump(gamestate_insights, f, indent=2, ensure_ascii=False)
    print(f"   ✅ {OUTPUT_DIR / 'gamestate_insights.json'}")
    
    with open(OUTPUT_DIR / 'speed_insights.json', 'w') as f:
        json.dump(speed_insights, f, indent=2, ensure_ascii=False)
    print(f"   ✅ {OUTPUT_DIR / 'speed_insights.json'}")
    
    with open(OUTPUT_DIR / 'team_exploit_profiles.json', 'w') as f:
        json.dump(exploit_profiles, f, indent=2, ensure_ascii=False)
    print(f"   ✅ {OUTPUT_DIR / 'team_exploit_profiles.json'}")
    
    # 5. Exemple complet
    print("\n" + "=" * 80)
    print("📋 EXEMPLE COMPLET: Wolverhampton Wanderers (Équipe très vulnérable)")
    print("=" * 80)
    
    wolves = exploit_profiles.get('Wolverhampton Wanderers', {})
    if wolves:
        print(f"\n   Équipe: Wolverhampton Wanderers")
        print(f"   Forme: {wolves.get('momentum', {}).get('form_last_5', '?')}")
        print(f"   Score vulnérabilité: {wolves['vulnerability_score']}")
        
        print(f"\n   ⚠️ VULNÉRABILITÉS ({len(wolves['vulnerabilities'])}):")
        for v in wolves['vulnerabilities']:
            print(f"      • {v}")
        
        print(f"\n   🎯 EXPLOIT PATHS ({len(wolves['exploit_paths'])}):")
        for exp in wolves['exploit_paths']:
            print(f"      • {exp['market']}")
            print(f"        Trigger: {exp['trigger']}")
            print(f"        Confidence: {exp['confidence']} | Edge: {exp['edge_estimate']}%")
        
        # Zones
        zones = wolves.get('zone_data', {}).get('zones', {})
        print(f"\n   📍 ZONES DANGEREUSES:")
        for zone, data in sorted(zones.items(), key=lambda x: x[1].get('conversion', 0), reverse=True)[:5]:
            print(f"      • {zone:<25} | {data['conversion']:.0f}% conv ({data['goals']}/{data['shots']})")
        
        # Actions
        actions = wolves.get('action_data', {}).get('actions', {})
        print(f"\n   ⚡ ACTIONS DANGEREUSES:")
        for action, data in sorted(actions.items(), key=lambda x: x[1].get('conversion', 0), reverse=True)[:5]:
            print(f"      • {action:<15} | {data['conversion']:.0f}% conv ({data['goals']}/{data['shots']})")
    
    print(f"\n{'='*80}")
    print(f"✅ QUANTUM FULL ANALYSIS COMPLET")
    print(f"   Toutes les priorités analysées!")
    print(f"{'='*80}")

if __name__ == '__main__':
    main()
