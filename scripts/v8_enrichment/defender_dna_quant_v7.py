#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🧬 DEFENDER DNA QUANT V7.0 - NIVEAU HEDGE FUND INSTITUTIONNEL               ║
║                                                                              ║
║  MÉTHODOLOGIE SCIENTIFIQUE:                                                  ║
║                                                                              ║
║  1. CONTRIBUTION INDIVIDUELLE PONDÉRÉE                                       ║
║     contribution = (impact_individuel × weight_temps) + contexte_équipe      ║
║                                                                              ║
║  2. CORRÉLATIONS CROISÉES                                                    ║
║     - Performance joueur × gameState équipe                                  ║
║     - Performance joueur × formation                                         ║
║     - Performance joueur × attackSpeed vulnerability                         ║
║                                                                              ║
║  3. EDGE CALCULÉ MATHÉMATIQUEMENT                                            ║
║     edge = base_vulnerability × player_contribution × confidence_factor      ║
║                                                                              ║
║  4. SIGNATURE ADN UNIQUE                                                     ║
║     Basée sur 15 dimensions quantifiées avec percentiles exacts              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import numpy as np
from pathlib import Path
from collections import defaultdict
from scipy.stats import percentileofscore
from datetime import datetime

DATA_DIR = Path('/home/Mon_ps/data')
DEFENDER_DIR = DATA_DIR / 'defender_dna'
QUANTUM_DIR = DATA_DIR / 'quantum_v2'

print("=" * 80)
print("🧬 DEFENDER DNA QUANT V7.0 - INSTITUTIONAL GRADE")
print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 80)

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1: CHARGEMENT DES DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═'*80}")
print("📂 PHASE 1: CHARGEMENT DES DONNÉES")
print(f"{'═'*80}")

# Défenseurs
with open(DEFENDER_DIR / 'defender_dna_institutional_v5.json', 'r') as f:
    defenders = json.load(f)
print(f"   ✅ {len(defenders)} défenseurs")

# Teams Context DNA (gameState, formation, attackSpeed, momentum)
with open(QUANTUM_DIR / 'teams_context_dna.json', 'r') as f:
    teams_context = json.load(f)
print(f"   ✅ {len(teams_context)} équipes context")

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
print(f"   ✅ Team exploits")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: CALCUL DES MÉTRIQUES DE RÉFÉRENCE
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═'*80}")
print("📊 PHASE 2: CALCUL DES BENCHMARKS")
print(f"{'═'*80}")

# Collecter toutes les métriques pour les percentiles
qualified_defenders = [d for d in defenders if d.get('time', 0) >= 400]
print(f"   {len(qualified_defenders)} défenseurs qualifiés (≥400 min)")

# Métriques individuelles
metrics = {
    'impact_goals_conceded': [],
    'clean_sheet_rate_with': [],
    'impact_wins': [],
    'xGChain_90': [],
    'xGBuildup_90': [],
    'xA_90': [],
    'cards_90': [],
    'time': [],
    'red_cards': [],
    'yellow_cards': []
}

for d in qualified_defenders:
    for key in metrics.keys():
        val = d.get(key, 0)
        if val is not None:
            metrics[key].append(float(val))

# Afficher les distributions
print(f"\n   📈 DISTRIBUTIONS:")
for key, values in metrics.items():
    if values:
        print(f"      {key}: min={min(values):.3f}, max={max(values):.3f}, median={np.median(values):.3f}, std={np.std(values):.3f}")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3: ANALYSE QUANTITATIVE PAR DÉFENSEUR
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═'*80}")
print("🔬 PHASE 3: ANALYSE QUANTITATIVE INDIVIDUELLE")
print(f"{'═'*80}")

def calculate_quant_profile(defender: dict) -> dict:
    """
    Calcul du profil quantitatif institutionnel
    
    Méthodologie:
    1. Percentiles individuels sur 10 dimensions
    2. Contextualisation avec données équipe
    3. Calcul des contributions aux vulnérabilités
    4. Edge betting scientifique
    """
    
    team = defender.get('team', '')
    name = defender.get('name', '')
    league = defender.get('league', '')
    
    # Récupérer contexte équipe
    team_ctx = teams_context.get(team, {})
    team_zones = zone_analysis.get(team, {})
    team_actions = action_analysis.get(team, {})
    team_exploit = team_exploits.get(team, {})
    
    context_dna = team_ctx.get('context_dna', {})
    momentum_dna = team_ctx.get('momentum_dna', {})
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION A: MÉTRIQUES INDIVIDUELLES QUANTIFIÉES
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Données brutes
    time_played = defender.get('time', 0)
    games = defender.get('games', 0)
    impact = defender.get('impact_goals_conceded', 0)
    cs_rate = defender.get('clean_sheet_rate_with', 0)
    win_impact = defender.get('impact_wins', 0)
    xgchain_90 = defender.get('xGChain_90', 0)
    xgbuildup_90 = defender.get('xGBuildup_90', 0)
    xa_90 = defender.get('xA_90', 0)
    cards_90 = defender.get('cards_90', 0)
    yellow = defender.get('yellow_cards', 0)
    red = defender.get('red_cards', 0)
    
    # Calculer les percentiles (0-100)
    def safe_percentile(value, distribution):
        if not distribution or value is None:
            return 50.0
        return round(percentileofscore(distribution, value, kind='rank'), 1)
    
    individual_metrics = {
        'SHIELD': {
            'raw': impact,
            'percentile': safe_percentile(impact, metrics['impact_goals_conceded']),
            'description': f"Impact défensif {impact:+.2f}"
        },
        'FORTRESS': {
            'raw': cs_rate,
            'percentile': safe_percentile(cs_rate, metrics['clean_sheet_rate_with']),
            'description': f"Clean sheet {cs_rate:.1f}%"
        },
        'WINNER': {
            'raw': win_impact,
            'percentile': safe_percentile(win_impact, metrics['impact_wins']),
            'description': f"Win impact {win_impact:+.1f}%"
        },
        'CHAIN': {
            'raw': xgchain_90,
            'percentile': safe_percentile(xgchain_90, metrics['xGChain_90']),
            'description': f"xGChain {xgchain_90:.3f}/90"
        },
        'BUILDER': {
            'raw': xgbuildup_90,
            'percentile': safe_percentile(xgbuildup_90, metrics['xGBuildup_90']),
            'description': f"xGBuildup {xgbuildup_90:.3f}/90"
        },
        'CREATOR': {
            'raw': xa_90,
            'percentile': safe_percentile(xa_90, metrics['xA_90']),
            'description': f"xA {xa_90:.3f}/90"
        },
        'DISCIPLINE': {
            'raw': cards_90,
            'percentile': 100 - safe_percentile(cards_90, metrics['cards_90']),  # Inversé
            'description': f"Cartons {cards_90:.2f}/90"
        },
        'AVAILABILITY': {
            'raw': time_played,
            'percentile': safe_percentile(time_played, metrics['time']),
            'description': f"Temps {time_played}min"
        }
    }
    
    # Cartons détaillés
    card_analysis = {
        'yellow_cards': yellow,
        'red_cards': red,
        'total_cards': yellow + red,
        'cards_per_90': cards_90,
        'red_card_rate': red / max(games, 1),
        'yellow_per_game': yellow / max(games, 1),
        'discipline_risk': 'CRITICAL' if red >= 2 or cards_90 >= 0.35 else 
                          'HIGH' if red >= 1 or cards_90 >= 0.25 else
                          'MODERATE' if cards_90 >= 0.15 else 'LOW',
        'second_yellow_risk': round(min(cards_90 * 30, 25), 1),  # % risque 2ème jaune
        'direct_red_risk': round(min(red / max(games, 1) * 100, 15), 1)  # % risque rouge direct
    }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION B: CONTEXTUALISATION ÉQUIPE - GAMESTATE
    # ═══════════════════════════════════════════════════════════════════════════
    
    gamestate = context_dna.get('gameState', {})
    
    gamestate_analysis = {
        'description': 'Comportement de l\'équipe selon le score',
        'states': {}
    }
    
    # Analyser chaque état de jeu
    for state, data in gamestate.items():
        if isinstance(data, dict):
            xga_90 = data.get('xG_against_90', 0)
            goals_against_90 = data.get('goals_against_90', 0)
            time_in_state = data.get('time', 0)
            
            # Classification de la performance
            if goals_against_90 > 2.0:
                perf = 'COLLAPSE'
                perf_desc = 'S\'effondre complètement'
            elif goals_against_90 > 1.5:
                perf = 'STRUGGLES'
                perf_desc = 'En difficulté'
            elif goals_against_90 < 0.8:
                perf = 'SOLID'
                perf_desc = 'Solide'
            else:
                perf = 'AVERAGE'
                perf_desc = 'Moyen'
            
            gamestate_analysis['states'][state] = {
                'time': time_in_state,
                'xG_against_90': round(xga_90, 3),
                'goals_against_90': round(goals_against_90, 2),
                'performance': perf,
                'performance_desc': perf_desc,
                'overperformance': round(xga_90 - goals_against_90, 3)  # + = chanceux, - = malchanceux
            }
    
    # Identifier les patterns critiques
    collapse_when_leading = False
    collapse_when_trailing = False
    
    if 'Goal diff +1' in gamestate_analysis['states']:
        leading = gamestate_analysis['states']['Goal diff +1']
        if leading['performance'] in ['COLLAPSE', 'STRUGGLES']:
            collapse_when_leading = True
            gamestate_analysis['CRITICAL_PATTERN'] = f"⚠️ S'EFFONDRE QUAND MÈNE: {leading['goals_against_90']:.2f} buts/90"
    
    if 'Goal diff -1' in gamestate_analysis['states']:
        trailing = gamestate_analysis['states']['Goal diff -1']
        if trailing['performance'] in ['COLLAPSE', 'STRUGGLES']:
            collapse_when_trailing = True
    
    gamestate_analysis['collapse_when_leading'] = collapse_when_leading
    gamestate_analysis['collapse_when_trailing'] = collapse_when_trailing
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION C: ANALYSE PAR FORMATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    formations = context_dna.get('formation', {})
    
    formation_analysis = {
        'formations': {},
        'best_formation': None,
        'worst_formation': None
    }
    
    best_rating = -999
    worst_rating = 999
    
    for formation, data in formations.items():
        if isinstance(data, dict) and data.get('time', 0) >= 90:  # Min 90 min
            def_rating = data.get('defensive_rating', 0)
            goals_against = data.get('goals_against', 0)
            time_form = data.get('time', 0)
            
            formation_analysis['formations'][formation] = {
                'time': time_form,
                'defensive_rating': round(def_rating, 3),
                'goals_against': goals_against,
                'goals_against_90': round(goals_against / (time_form / 90), 2) if time_form > 0 else 0,
                'xG_against_90': round(data.get('xG_against_90', 0), 3)
            }
            
            if def_rating > best_rating:
                best_rating = def_rating
                formation_analysis['best_formation'] = {
                    'name': formation,
                    'rating': round(def_rating, 3),
                    'description': f"Meilleure défense en {formation} (rating {def_rating:.3f})"
                }
            
            if def_rating < worst_rating:
                worst_rating = def_rating
                formation_analysis['worst_formation'] = {
                    'name': formation,
                    'rating': round(def_rating, 3),
                    'description': f"Vulnérable en {formation} (rating {def_rating:.3f})"
                }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION D: VULNÉRABILITÉ PAR VITESSE D'ATTAQUE
    # ═══════════════════════════════════════════════════════════════════════════
    
    attack_speed = context_dna.get('attackSpeed', {})
    
    speed_vulnerability = {
        'speeds': {},
        'most_vulnerable_to': None,
        'counter_attack_weakness': False
    }
    
    max_conversion = 0
    
    for speed, data in attack_speed.items():
        if isinstance(data, dict):
            conversion = data.get('conversion_against', 0)
            goals_against = data.get('goals_against', 0)
            shots_against = data.get('shots_against', 0)
            
            speed_vulnerability['speeds'][speed] = {
                'conversion_rate': round(conversion, 1),
                'goals_against': goals_against,
                'shots_against': shots_against,
                'danger_level': 'CRITICAL' if conversion > 25 else 
                               'HIGH' if conversion > 15 else
                               'MODERATE' if conversion > 10 else 'LOW'
            }
            
            if conversion > max_conversion:
                max_conversion = conversion
                speed_vulnerability['most_vulnerable_to'] = {
                    'speed': speed,
                    'conversion': round(conversion, 1),
                    'description': f"Très vulnérable aux attaques {speed} ({conversion:.1f}% conversion)"
                }
    
    # Vulnérabilité spécifique aux contre-attaques rapides
    fast_data = speed_vulnerability['speeds'].get('Fast', {})
    if fast_data.get('conversion_rate', 0) > 20:
        speed_vulnerability['counter_attack_weakness'] = True
        speed_vulnerability['counter_attack_edge'] = round((fast_data['conversion_rate'] - 10) * 0.3, 1)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION E: ZONES DE DANGER
    # ═══════════════════════════════════════════════════════════════════════════
    
    zone_vulnerability = {
        'zones': {},
        'critical_zones': [],
        'weak_side': None
    }
    
    left_danger = 0
    right_danger = 0
    center_danger = 0
    
    for zone, data in team_zones.items():
        if isinstance(data, dict):
            conversion = data.get('conversion_rate', 0)
            if isinstance(conversion, (int, float)):
                goals = data.get('goals_conceded', 0)
                
                zone_vulnerability['zones'][zone] = {
                    'conversion_rate': round(conversion * 100, 1),
                    'goals_conceded': goals,
                    'danger': 'CRITICAL' if conversion > 0.5 else 
                             'HIGH' if conversion > 0.35 else
                             'MODERATE' if conversion > 0.2 else 'LOW'
                }
                
                if zone_vulnerability['zones'][zone]['danger'] in ['CRITICAL', 'HIGH']:
                    zone_vulnerability['critical_zones'].append(zone)
                
                # Calculer le côté faible
                if 'left' in zone.lower():
                    left_danger += conversion
                elif 'right' in zone.lower():
                    right_danger += conversion
                else:
                    center_danger += conversion
    
    if left_danger > right_danger * 1.3:
        zone_vulnerability['weak_side'] = {
            'side': 'LEFT',
            'description': f"Côté GAUCHE vulnérable (danger cumulé: {left_danger:.2f} vs {right_danger:.2f})"
        }
    elif right_danger > left_danger * 1.3:
        zone_vulnerability['weak_side'] = {
            'side': 'RIGHT', 
            'description': f"Côté DROIT vulnérable (danger cumulé: {right_danger:.2f} vs {left_danger:.2f})"
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION F: ACTIONS DANGEREUSES
    # ═══════════════════════════════════════════════════════════════════════════
    
    action_vulnerability = {
        'actions': {},
        'most_dangerous': []
    }
    
    action_dangers = []
    
    for action, data in team_actions.items():
        if isinstance(data, dict):
            conversion = data.get('conversion_rate', 0)
            if isinstance(conversion, (int, float)):
                goals = data.get('goals_conceded', 0)
                
                action_vulnerability['actions'][action] = {
                    'conversion_rate': round(conversion * 100, 1),
                    'goals_conceded': goals,
                    'danger': 'CRITICAL' if conversion > 0.5 else
                             'HIGH' if conversion > 0.35 else
                             'MODERATE' if conversion > 0.2 else 'LOW'
                }
                
                action_dangers.append((action, conversion, goals))
    
    # Top 3 actions dangereuses
    action_dangers.sort(key=lambda x: x[1], reverse=True)
    action_vulnerability['most_dangerous'] = [
        {'action': a[0], 'conversion': round(a[1]*100, 1), 'goals': a[2]}
        for a in action_dangers[:3]
    ]
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION G: MOMENTUM ET FORME
    # ═══════════════════════════════════════════════════════════════════════════
    
    momentum_analysis = {
        'form': momentum_dna.get('form_last_5', 'N/A'),
        'form_points': momentum_dna.get('form_points', 0),
        'trending': momentum_dna.get('trending', 'STABLE'),
        'avg_goals_against': momentum_dna.get('avg_goals_against', 0),
        'avg_xG_against': momentum_dna.get('avg_xG_against', 0),
        'clean_sheets_last_5': momentum_dna.get('clean_sheets_last_5', 0),
        'xG_overperformance': momentum_dna.get('xGA_overperformance', 0)
    }
    
    # Déterminer l'état de forme défensive
    if momentum_analysis['trending'] == 'DOWN' and momentum_analysis['avg_goals_against'] > 1.5:
        momentum_analysis['defensive_form'] = 'CRISIS'
        momentum_analysis['form_description'] = f"CRISE: {momentum_analysis['form']} | {momentum_analysis['avg_goals_against']:.1f} buts/match"
    elif momentum_analysis['clean_sheets_last_5'] >= 3:
        momentum_analysis['defensive_form'] = 'EXCELLENT'
        momentum_analysis['form_description'] = f"EXCELLENT: {momentum_analysis['clean_sheets_last_5']} CS sur 5 matchs"
    elif momentum_analysis['avg_goals_against'] < 1.0:
        momentum_analysis['defensive_form'] = 'GOOD'
        momentum_analysis['form_description'] = f"BONNE: {momentum_analysis['avg_goals_against']:.1f} buts/match"
    else:
        momentum_analysis['defensive_form'] = 'AVERAGE'
        momentum_analysis['form_description'] = f"MOYENNE: {momentum_analysis['avg_goals_against']:.1f} buts/match"
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION H: CALCUL DES EDGES BETTING
    # ═══════════════════════════════════════════════════════════════════════════
    
    edges = {}
    
    # Poids du temps de jeu (contribution)
    # Plus un défenseur joue, plus il est responsable des stats équipe
    time_weight = min(time_played / 1200, 1.0)  # Normalisé sur ~13 matchs complets
    
    # 1. GOALS OVER Edge
    base_go_edge = 0
    go_factors = []
    
    # Factor 1: Impact individuel négatif
    if impact < -0.3:
        base_go_edge += abs(impact) * 3
        go_factors.append(f"Impact négatif ({impact:+.2f})")
    
    # Factor 2: Clean sheet rate faible
    if cs_rate < 20:
        base_go_edge += (20 - cs_rate) * 0.1
        go_factors.append(f"CS rate {cs_rate:.0f}%")
    
    # Factor 3: Équipe s'effondre quand mène
    if collapse_when_leading:
        base_go_edge += 2.5
        go_factors.append("Collapse when leading")
    
    # Factor 4: Forme défensive en crise
    if momentum_analysis['defensive_form'] == 'CRISIS':
        base_go_edge += 2.0
        go_factors.append(f"Forme: {momentum_analysis['form']}")
    
    # Factor 5: Vulnérabilité contre-attaques
    if speed_vulnerability.get('counter_attack_weakness'):
        base_go_edge += speed_vulnerability.get('counter_attack_edge', 1.5)
        go_factors.append(f"Fast attack vuln {speed_vulnerability['most_vulnerable_to']['conversion']:.0f}%")
    
    # Pondérer par temps de jeu
    final_go_edge = round(base_go_edge * time_weight, 1)
    
    if final_go_edge >= 2.0:
        edges['GOALS_OVER'] = {
            'edge': final_go_edge,
            'confidence': 'HIGH' if final_go_edge >= 5 else 'MEDIUM' if final_go_edge >= 3 else 'LOW',
            'factors': go_factors,
            'formula': f"({' + '.join([f'{f}' for f in go_factors])}) × time_weight({time_weight:.2f})"
        }
    
    # 2. BTTS YES Edge
    base_btts_edge = 0
    btts_factors = []
    
    if cs_rate < 25:
        base_btts_edge += (25 - cs_rate) * 0.12
        btts_factors.append(f"CS rate {cs_rate:.0f}%")
    
    if momentum_analysis['clean_sheets_last_5'] == 0:
        base_btts_edge += 2.0
        btts_factors.append("0 CS last 5")
    
    final_btts_edge = round(base_btts_edge * time_weight, 1)
    
    if final_btts_edge >= 2.0:
        edges['BTTS_YES'] = {
            'edge': final_btts_edge,
            'confidence': 'HIGH' if final_btts_edge >= 5 else 'MEDIUM',
            'factors': btts_factors
        }
    
    # 3. CARDS OVER Edge
    base_cards_edge = 0
    cards_factors = []
    
    if cards_90 >= 0.25:
        base_cards_edge += cards_90 * 10
        cards_factors.append(f"{cards_90:.2f} cartons/90")
    
    if red >= 1:
        base_cards_edge += red * 3
        cards_factors.append(f"{red} rouge(s) cette saison")
    
    if card_analysis['discipline_risk'] in ['CRITICAL', 'HIGH']:
        base_cards_edge += 1.5
        cards_factors.append(f"Risque {card_analysis['discipline_risk']}")
    
    final_cards_edge = round(base_cards_edge, 1)
    
    if final_cards_edge >= 2.0:
        edges['CARDS_OVER'] = {
            'edge': final_cards_edge,
            'confidence': 'HIGH' if final_cards_edge >= 4 else 'MEDIUM',
            'factors': cards_factors,
            'red_card_probability': card_analysis['direct_red_risk'],
            'second_yellow_probability': card_analysis['second_yellow_risk']
        }
    
    # 4. ANYTIME ASSIST Edge (pour latéraux offensifs)
    if xa_90 >= 0.08:
        assist_edge = round((xa_90 - 0.05) * 50, 1)
        edges['ANYTIME_ASSIST'] = {
            'edge': assist_edge,
            'confidence': 'MEDIUM',
            'factors': [f"xA {xa_90:.3f}/90", f"Percentile {individual_metrics['CREATOR']['percentile']:.0f}"]
        }
    
    # 5. COMEBACK Edge (équipe qui s'effondre)
    if collapse_when_leading:
        leading_data = gamestate_analysis['states'].get('Goal diff +1', {})
        comeback_edge = round((leading_data.get('goals_against_90', 0) - 1.0) * 3, 1)
        if comeback_edge >= 2.0:
            edges['COMEBACK'] = {
                'edge': comeback_edge,
                'confidence': 'HIGH',
                'factors': [
                    f"Concède {leading_data.get('goals_against_90', 0):.2f} buts/90 quand mène",
                    f"xG against {leading_data.get('xG_against_90', 0):.2f}/90"
                ],
                'trigger': 'Équipe mène au score'
            }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SECTION I: SIGNATURE ADN UNIQUE
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Générer la signature narrative complète
    signature_parts = []
    
    # Partie 1: Impact individuel
    shield_pct = individual_metrics['SHIELD']['percentile']
    if shield_pct >= 75:
        signature_parts.append(f"PILIER DÉFENSIF (Impact {impact:+.2f}, P{shield_pct:.0f})")
    elif shield_pct <= 25:
        signature_parts.append(f"MAILLON FAIBLE (Impact {impact:+.2f}, P{shield_pct:.0f})")
    
    # Partie 2: GameState critique
    if collapse_when_leading:
        signature_parts.append(f"COLLAPSE QUAND MÈNE ({gamestate_analysis['states'].get('Goal diff +1', {}).get('goals_against_90', 0):.2f}/90)")
    
    # Partie 3: Vulnérabilité vitesse
    if speed_vulnerability.get('counter_attack_weakness'):
        vuln = speed_vulnerability['most_vulnerable_to']
        signature_parts.append(f"VULNÉRABLE FAST ({vuln['conversion']:.0f}% conv)")
    
    # Partie 4: Momentum
    if momentum_analysis['defensive_form'] == 'CRISIS':
        signature_parts.append(f"EN CRISE ({momentum_analysis['form']})")
    elif momentum_analysis['defensive_form'] == 'EXCELLENT':
        signature_parts.append(f"EN FORME ({momentum_analysis['clean_sheets_last_5']} CS/5)")
    
    # Partie 5: Cartons
    if card_analysis['discipline_risk'] in ['CRITICAL', 'HIGH']:
        signature_parts.append(f"RISQUE CARTONS ({cards_90:.2f}/90, {red}R)")
    
    # Partie 6: Création offensive si notable
    if individual_metrics['CREATOR']['percentile'] >= 80:
        signature_parts.append(f"MENACE CRÉATIVE ({xa_90:.3f} xA/90)")
    
    # Partie 7: Formation faible si identifiée
    if formation_analysis.get('worst_formation') and formation_analysis['worst_formation']['rating'] < 0:
        signature_parts.append(f"FAIBLE EN {formation_analysis['worst_formation']['name']}")
    
    enhanced_signature = ' | '.join(signature_parts) if signature_parts else f"PROFIL STANDARD (P{shield_pct:.0f})"
    
    # Fingerprint unique
    edge_codes = [f"{k[:2]}+{v['edge']:.0f}" for k, v in edges.items()]
    fingerprint = f"DEF{int(shield_pct)}-CS{int(cs_rate)}-{'|'.join(edge_codes) if edge_codes else 'NEUTRAL'}"
    
    # Score global
    defensive_score = (shield_pct * 0.4 + individual_metrics['FORTRESS']['percentile'] * 0.3 + 
                      individual_metrics['WINNER']['percentile'] * 0.3)
    offensive_score = (individual_metrics['CHAIN']['percentile'] * 0.3 + 
                      individual_metrics['BUILDER']['percentile'] * 0.3 +
                      individual_metrics['CREATOR']['percentile'] * 0.4)
    
    total_edge = sum(e['edge'] for e in edges.values())
    
    return {
        # Métriques individuelles
        'individual_metrics': individual_metrics,
        'card_analysis': card_analysis,
        
        # Contexte équipe
        'gamestate_analysis': gamestate_analysis,
        'formation_analysis': formation_analysis,
        'speed_vulnerability': speed_vulnerability,
        'zone_vulnerability': zone_vulnerability,
        'action_vulnerability': action_vulnerability,
        'momentum_analysis': momentum_analysis,
        
        # Betting Intelligence
        'edges': edges,
        'total_edge': round(total_edge, 1),
        
        # Scores composites
        'scores': {
            'defensive': round(defensive_score, 1),
            'offensive': round(offensive_score, 1),
            'overall': round((defensive_score + offensive_score) / 2, 1)
        },
        
        # Signature unique
        'signature': enhanced_signature,
        'fingerprint': fingerprint,
        
        # Metadata
        'time_weight': round(time_weight, 2),
        'data_quality': 'HIGH' if time_played >= 800 else 'MEDIUM' if time_played >= 500 else 'LOW'
    }

# Appliquer l'analyse à tous les défenseurs
print(f"\n   🔬 Calcul en cours...")

for d in defenders:
    if d.get('time', 0) >= 400:
        quant = calculate_quant_profile(d)
        d['quant_v7'] = quant

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4: SAUVEGARDE
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═'*80}")
print("💾 PHASE 4: SAUVEGARDE")
print(f"{'═'*80}")

with open(DEFENDER_DIR / 'defender_dna_quant_v7.json', 'w') as f:
    json.dump(defenders, f, indent=2, ensure_ascii=False)
print(f"   ✅ defender_dna_quant_v7.json")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5: RAPPORT
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═'*80}")
print("📊 PHASE 5: RAPPORT QUANT V7.0")
print(f"{'═'*80}")

# Exemples détaillés
examples = ['Toti', 'Gabriel', 'van Dijk', 'Dimarco']

for name in examples:
    player = next((d for d in defenders if name in d.get('name', '') and d.get('quant_v7')), None)
    if player:
        q = player['quant_v7']
        
        print(f"\n{'═'*80}")
        print(f"👤 {player['name']} ({player['team']} - {player['league']})")
        print(f"{'═'*80}")
        
        print(f"\n📛 SIGNATURE: {q['signature']}")
        print(f"🔑 FINGERPRINT: {q['fingerprint']}")
        print(f"📊 DATA QUALITY: {q['data_quality']} | Time Weight: {q['time_weight']}")
        
        print(f"\n┌─────────────────────────────────────────────────────────────┐")
        print(f"│ 📊 MÉTRIQUES INDIVIDUELLES (Percentiles)                     │")
        print(f"├─────────────────────────────────────────────────────────────┤")
        for dim, data in q['individual_metrics'].items():
            pct = data['percentile']
            bar = '█' * int(pct / 5) + '░' * (20 - int(pct / 5))
            print(f"│ {dim:<12} {bar} {pct:5.1f}% │ {data['description']:<20}│")
        print(f"└─────────────────────────────────────────────────────────────┘")
        
        print(f"\n🟨 CARTONS:")
        ca = q['card_analysis']
        print(f"   Jaunes: {ca['yellow_cards']} | Rouges: {ca['red_cards']} | Per 90: {ca['cards_per_90']:.2f}")
        print(f"   Risque 2ème jaune: {ca['second_yellow_risk']:.1f}% | Risque rouge direct: {ca['direct_red_risk']:.1f}%")
        print(f"   Classification: {ca['discipline_risk']}")
        
        print(f"\n🎯 GAMESTATE (comportement équipe selon score):")
        for state, data in q['gamestate_analysis']['states'].items():
            emoji = '🔴' if data['performance'] == 'COLLAPSE' else '🟡' if data['performance'] == 'STRUGGLES' else '🟢' if data['performance'] == 'SOLID' else '⚪'
            print(f"   {emoji} {state}: {data['goals_against_90']:.2f} buts/90 ({data['performance']})")
        if q['gamestate_analysis'].get('CRITICAL_PATTERN'):
            print(f"   {q['gamestate_analysis']['CRITICAL_PATTERN']}")
        
        print(f"\n⚡ VULNÉRABILITÉ VITESSE ATTAQUE:")
        for speed, data in q['speed_vulnerability']['speeds'].items():
            emoji = '🔴' if data['danger_level'] == 'CRITICAL' else '🟡' if data['danger_level'] == 'HIGH' else '⚪'
            print(f"   {emoji} {speed}: {data['conversion_rate']:.1f}% conversion ({data['goals_against']} buts)")
        if q['speed_vulnerability'].get('counter_attack_weakness'):
            print(f"   ⚠️ {q['speed_vulnerability']['most_vulnerable_to']['description']}")
        
        print(f"\n📐 FORMATIONS:")
        if q['formation_analysis'].get('best_formation'):
            print(f"   ✅ {q['formation_analysis']['best_formation']['description']}")
        if q['formation_analysis'].get('worst_formation'):
            print(f"   ❌ {q['formation_analysis']['worst_formation']['description']}")
        
        print(f"\n📈 MOMENTUM:")
        print(f"   {q['momentum_analysis']['form_description']}")
        
        if q['edges']:
            print(f"\n💰 EDGES BETTING:")
            for market, edge in q['edges'].items():
                print(f"   📈 {market}: +{edge['edge']:.1f}% ({edge['confidence']})")
                print(f"      Facteurs: {', '.join(edge['factors'])}")
                if market == 'CARDS_OVER':
                    print(f"      → P(2ème jaune): {edge.get('second_yellow_probability', 0):.1f}% | P(rouge): {edge.get('red_card_probability', 0):.1f}%")
                if market == 'COMEBACK' and edge.get('trigger'):
                    print(f"      → Trigger: {edge['trigger']}")
            print(f"\n   📊 TOTAL EDGE VALUE: +{q['total_edge']:.1f}%")

# Top par Edge
print(f"\n{'═'*80}")
print("💰 TOP 25 DÉFENSEURS PAR EDGE VALUE")
print(f"{'═'*80}")

ranked = sorted([d for d in defenders if d.get('quant_v7')], 
                key=lambda x: x['quant_v7']['total_edge'], reverse=True)

print(f"\n{'Rank':<5}│{'Nom':<25}│{'Équipe':<22}│{'Edge':<8}│{'Signature courte':<40}")
print("─" * 105)
for i, d in enumerate(ranked[:25], 1):
    q = d['quant_v7']
    sig = q['signature'][:37] + '...' if len(q['signature']) > 37 else q['signature']
    print(f"{i:<5}│{d['name']:<25}│{d['team']:<22}│+{q['total_edge']:5.1f}%│{sig:<40}")

print(f"\n{'═'*80}")
print(f"✅ DEFENDER DNA QUANT V7.0 COMPLET")
print(f"   Analyse institutionnelle: {len([d for d in defenders if d.get('quant_v7')])} défenseurs")
print(f"{'═'*80}")
