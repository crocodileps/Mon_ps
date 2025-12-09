#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🧬 DEFENDER DNA QUANT V8.0 - HEDGE FUND GRADE 2.0                           ║
║                                                                              ║
║  10 DIMENSIONS D'ANALYSE INSTITUTIONNELLE:                                   ║
║                                                                              ║
║  1. PAIRE SYNERGY ANALYSIS      - Corrélation entre défenseurs               ║
║  2. MATCHUP FRICTION INDEX      - Défenseur vs type d'attaquant              ║
║  3. VOLATILITY INDEX            - Constance des performances                 ║
║  4. REGRESSION TO MEAN          - Sur/sous-performance xGA                   ║
║  5. AERIAL DOMINANCE INDEX      - Vulnérabilité aérienne                     ║
║  6. FATIGUE MODEL               - Impact minutes cumulées                    ║
║  7. CONTEXTUAL EDGE MULTIPLIER  - Ajustement dynamique                       ║
║  8. EXPECTED CARDS MODEL        - xCards probabiliste                        ║
║  9. CLUTCH PERFORMANCE INDEX    - Moments décisifs                           ║
║  10. VALUE AT RISK (VaR)        - Quantification pire scénario               ║
║                                                                              ║
║  "Du travail d'analyste en profondeur, pas en superficie"                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import numpy as np
from pathlib import Path
from collections import defaultdict
from scipy.stats import percentileofscore, norm
from datetime import datetime
import math

DATA_DIR = Path('/home/Mon_ps/data')
DEFENDER_DIR = DATA_DIR / 'defender_dna'
QUANTUM_DIR = DATA_DIR / 'quantum_v2'
GOAL_DIR = DATA_DIR / 'goal_analysis'

print("═" * 80)
print("🧬 DEFENDER DNA QUANT V8.0 - HEDGE FUND GRADE 2.0")
print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("═" * 80)

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1: CHARGEMENT COMPLET DES DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═'*80}")
print("📂 PHASE 1: CHARGEMENT DES DONNÉES")
print(f"{'═'*80}")

# Défenseurs V7
with open(DEFENDER_DIR / 'defender_dna_quant_v7.json', 'r') as f:
    defenders = json.load(f)
print(f"   ✅ {len(defenders)} défenseurs (V7)")

# Teams Context DNA
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

# Players Impact DNA
with open(QUANTUM_DIR / 'players_impact_dna.json', 'r') as f:
    players_impact = json.load(f)
print(f"   ✅ Players impact DNA")

# Goals Analysis
with open(GOAL_DIR / 'all_goals_2025.json', 'r') as f:
    all_goals = json.load(f)
print(f"   ✅ {len(all_goals)} buts analysés")

# Defense DNA V5.1
defense_dna_path = DATA_DIR / 'defense_dna' / 'team_defense_dna_v5_1_corrected.json'
with open(defense_dna_path, 'r') as f:
    defense_raw = json.load(f)
if isinstance(defense_raw, list):
    team_defense_dna = {item.get('team_name', item.get('team', '')): item for item in defense_raw if isinstance(item, dict)}
else:
    team_defense_dna = defense_raw
print(f"   ✅ {len(team_defense_dna)} équipes defense DNA")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: PRÉPARATION DES DONNÉES DE RÉFÉRENCE
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═'*80}")
print("📊 PHASE 2: PRÉPARATION DES BENCHMARKS")
print(f"{'═'*80}")

# Grouper défenseurs par équipe
defenders_by_team = defaultdict(list)
for d in defenders:
    if d.get('time', 0) >= 400:
        defenders_by_team[d.get('team', '')].append(d)

print(f"   {len(defenders_by_team)} équipes avec défenseurs qualifiés")

# Collecter métriques pour percentiles
qualified = [d for d in defenders if d.get('time', 0) >= 400]

metrics_distributions = {
    'impact': [d.get('impact_goals_conceded', 0) for d in qualified],
    'cs_rate': [d.get('clean_sheet_rate_with', 0) for d in qualified],
    'xgchain_90': [d.get('xGChain_90', 0) for d in qualified],
    'xgbuildup_90': [d.get('xGBuildup_90', 0) for d in qualified],
    'xa_90': [d.get('xA_90', 0) for d in qualified],
    'cards_90': [d.get('cards_90', 0) for d in qualified],
    'goals_conceded_per_match': [d.get('goals_conceded_per_match_with', 0) for d in qualified if d.get('goals_conceded_per_match_with')],
}

# Analyser les buts pour aerial/type
goals_by_team = defaultdict(list)
for goal in all_goals:
    # Trouver l'équipe qui a concédé
    team_against = goal.get('team_against', goal.get('h_team' if goal.get('h_a') == 'a' else 'a_team', ''))
    if team_against:
        goals_by_team[team_against].append(goal)

print(f"   {len(goals_by_team)} équipes avec buts concédés analysés")

# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS D'ANALYSE V8.0
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_paire_synergy(defender: dict, team_defenders: list) -> dict:
    """
    1. PAIRE SYNERGY ANALYSIS
    Analyse la synergie entre défenseurs qui jouent ensemble
    """
    name = defender.get('name', '')
    
    synergy_analysis = {
        'description': 'Corrélation de performance avec partenaires',
        'pairs': [],
        'best_partner': None,
        'worst_partner': None,
        'isolation_risk': False
    }
    
    # Calculer la synergie avec chaque autre défenseur
    my_impact = defender.get('impact_goals_conceded', 0)
    my_cs_rate = defender.get('clean_sheet_rate_with', 0)
    
    for other in team_defenders:
        if other.get('name') == name:
            continue
        
        other_impact = other.get('impact_goals_conceded', 0)
        other_cs_rate = other.get('clean_sheet_rate_with', 0)
        
        # Synergie = moyenne pondérée des impacts
        # Si les deux sont positifs = synergie positive
        # Si un est très négatif = synergie négative
        combined_impact = (my_impact + other_impact) / 2
        combined_cs = (my_cs_rate + other_cs_rate) / 2
        
        # Score de synergie: bonus si les deux sont bons, malus si un est mauvais
        if my_impact > 0 and other_impact > 0:
            synergy_score = combined_impact * 1.2  # Bonus synergie positive
        elif my_impact < -0.3 or other_impact < -0.3:
            synergy_score = combined_impact * 0.8  # Malus pour maillon faible
        else:
            synergy_score = combined_impact
        
        pair_data = {
            'partner': other.get('name'),
            'partner_impact': round(other_impact, 2),
            'combined_impact': round(combined_impact, 2),
            'synergy_score': round(synergy_score, 2),
            'combined_cs_rate': round(combined_cs, 1),
            'compatibility': 'EXCELLENT' if synergy_score > 0.5 else
                           'GOOD' if synergy_score > 0.2 else
                           'NEUTRAL' if synergy_score > -0.2 else
                           'POOR' if synergy_score > -0.5 else 'TOXIC'
        }
        
        synergy_analysis['pairs'].append(pair_data)
    
    # Identifier meilleur/pire partenaire
    if synergy_analysis['pairs']:
        synergy_analysis['pairs'].sort(key=lambda x: x['synergy_score'], reverse=True)
        synergy_analysis['best_partner'] = synergy_analysis['pairs'][0]
        synergy_analysis['worst_partner'] = synergy_analysis['pairs'][-1]
        
        # Risque d'isolation: si le meilleur partenaire est négatif
        if synergy_analysis['best_partner']['synergy_score'] < 0:
            synergy_analysis['isolation_risk'] = True
            synergy_analysis['isolation_description'] = "AUCUN partenaire compatible - Ligne défensive compromise"
    
    return synergy_analysis


def calculate_matchup_friction(defender: dict, team_context: dict) -> dict:
    """
    2. MATCHUP FRICTION INDEX
    Analyse la vulnérabilité contre différents types d'attaquants
    """
    
    # Profil défensif du joueur
    cards_90 = defender.get('cards_90', 0)
    impact = defender.get('impact_goals_conceded', 0)
    xgbuildup = defender.get('xGBuildup_90', 0)
    
    # Vulnérabilités équipe (proxy pour le défenseur)
    attack_speed = team_context.get('context_dna', {}).get('attackSpeed', {})
    
    friction_analysis = {
        'description': 'Vulnérabilité contre types d\'attaquants',
        'profiles': {},
        'critical_matchup': None,
        'safe_matchup': None
    }
    
    # Calculer friction pour chaque type d'attaquant
    
    # 1. SPEED_DEMON (rapides: Mbappé, Saka, Vinicius)
    fast_vuln = attack_speed.get('Fast', {}).get('conversion_against', 10)
    speed_friction = min(fast_vuln / 10, 3.0)  # Normalisé
    if impact < 0:  # Défenseur faible = encore plus vulnérable
        speed_friction *= 1.3
    
    friction_analysis['profiles']['SPEED_DEMON'] = {
        'friction_score': round(speed_friction, 2),
        'danger_level': 'CRITICAL' if speed_friction > 2.5 else 'HIGH' if speed_friction > 1.5 else 'MEDIUM' if speed_friction > 0.8 else 'LOW',
        'description': f"Contre attaquants rapides: {fast_vuln:.1f}% conversion",
        'examples': 'Mbappé, Saka, Vinicius Jr, Adama Traoré'
    }
    
    # 2. TECHNICAL_WIZARD (dribbleurs)
    # Les défenseurs avec beaucoup de cartons sont vulnérables aux dribbleurs
    tech_friction = cards_90 * 5 + (0.5 if impact < 0 else 0)
    
    friction_analysis['profiles']['TECHNICAL_WIZARD'] = {
        'friction_score': round(tech_friction, 2),
        'danger_level': 'CRITICAL' if tech_friction > 2.0 else 'HIGH' if tech_friction > 1.2 else 'MEDIUM' if tech_friction > 0.6 else 'LOW',
        'description': f"Contre dribbleurs: {cards_90:.2f} cartons/90 → provoque fautes",
        'card_risk_multiplier': round(1 + cards_90 * 2, 2),
        'examples': 'Vinicius Jr, Lamine Yamal, Neymar, Dembélé'
    }
    
    # 3. AERIAL_THREAT (dominants dans les airs)
    # Utiliser les zones de tir (six_yard, headers)
    aerial_friction = 1.0  # Base
    
    friction_analysis['profiles']['AERIAL_THREAT'] = {
        'friction_score': round(aerial_friction, 2),
        'danger_level': 'MEDIUM',
        'description': "Contre joueurs dominants dans les airs",
        'examples': 'Haaland, Vlahovic, Darwin Núñez, Osimhen'
    }
    
    # 4. CLINICAL_FINISHER (efficaces devant but)
    # Si CS rate faible = vulnérable aux finisseurs
    cs_rate = defender.get('clean_sheet_rate_with', 25)
    clinical_friction = max(0, (50 - cs_rate) / 20)
    
    friction_analysis['profiles']['CLINICAL_FINISHER'] = {
        'friction_score': round(clinical_friction, 2),
        'danger_level': 'CRITICAL' if clinical_friction > 2.0 else 'HIGH' if clinical_friction > 1.2 else 'MEDIUM',
        'description': f"Contre finisseurs: CS rate {cs_rate:.1f}%",
        'examples': 'Kane, Lewandowski, Salah, Son'
    }
    
    # 5. PRESSING_MONSTER (haut pressing)
    # Défenseurs avec faible xGBuildup = vulnérables au pressing
    pressing_friction = max(0, (0.25 - xgbuildup) * 8)
    
    friction_analysis['profiles']['PRESSING_MONSTER'] = {
        'friction_score': round(pressing_friction, 2),
        'danger_level': 'HIGH' if pressing_friction > 1.5 else 'MEDIUM' if pressing_friction > 0.8 else 'LOW',
        'description': f"Contre presseurs: xGBuildup {xgbuildup:.3f}/90",
        'examples': 'Darwin Núñez, Luis Díaz, Gakpo, Diogo Jota'
    }
    
    # Identifier matchups critiques et safe
    sorted_profiles = sorted(friction_analysis['profiles'].items(), 
                            key=lambda x: x[1]['friction_score'], reverse=True)
    
    friction_analysis['critical_matchup'] = {
        'type': sorted_profiles[0][0],
        'friction': sorted_profiles[0][1]['friction_score'],
        'danger': sorted_profiles[0][1]['danger_level']
    }
    
    friction_analysis['safe_matchup'] = {
        'type': sorted_profiles[-1][0],
        'friction': sorted_profiles[-1][1]['friction_score'],
        'danger': sorted_profiles[-1][1]['danger_level']
    }
    
    return friction_analysis


def calculate_volatility_index(defender: dict, team_context: dict) -> dict:
    """
    3. VOLATILITY INDEX
    Mesure la constance des performances
    """
    
    # Utiliser les données disponibles pour estimer la volatilité
    games = defender.get('games', 1)
    goals_conceded_with = defender.get('goals_conceded_with', 0)
    cs_with = defender.get('clean_sheets_with', 0)
    matches_with = defender.get('matches_analyzed_with', 1)
    
    # Moyenne de buts concédés par match
    mean_conceded = goals_conceded_with / max(matches_with, 1)
    
    # Estimation de l'écart-type basée sur le ratio CS
    # Si beaucoup de CS = faible variance, sinon haute variance
    cs_ratio = cs_with / max(matches_with, 1)
    
    # Formule: variance inversement proportionnelle au CS ratio
    # Plus de CS = moins de variance
    estimated_std = mean_conceded * (1.5 - cs_ratio)
    
    # Coefficient de variation (volatilité)
    volatility = estimated_std / max(mean_conceded, 0.5)
    
    # Utiliser aussi les données de forme de l'équipe
    momentum = team_context.get('momentum_dna', {})
    form = momentum.get('form_last_5', 'XXXXX')
    
    # Calculer la variance de la forme (W=3, D=1, L=0)
    form_values = []
    for char in form:
        if char == 'W':
            form_values.append(3)
        elif char == 'D':
            form_values.append(1)
        else:
            form_values.append(0)
    
    form_std = np.std(form_values) if form_values else 1.0
    
    # Score de volatilité combiné
    combined_volatility = (volatility * 0.6 + form_std / 1.5 * 0.4)
    
    volatility_analysis = {
        'mean_goals_conceded': round(mean_conceded, 2),
        'estimated_std': round(estimated_std, 2),
        'volatility_coefficient': round(volatility, 2),
        'form_volatility': round(form_std, 2),
        'combined_volatility': round(combined_volatility, 2),
        'profile': 'ROCK' if combined_volatility < 0.4 else
                  'RELIABLE' if combined_volatility < 0.7 else
                  'INCONSISTENT' if combined_volatility < 1.0 else 'WILDCARD',
        'description': ''
    }
    
    # Description personnalisée
    if volatility_analysis['profile'] == 'ROCK':
        volatility_analysis['description'] = f"Performance très constante (vol={combined_volatility:.2f})"
        volatility_analysis['betting_impact'] = "Edges fiables, confidence HIGH"
    elif volatility_analysis['profile'] == 'WILDCARD':
        volatility_analysis['description'] = f"Imprévisible (vol={combined_volatility:.2f}) - Capable du meilleur comme du pire"
        volatility_analysis['betting_impact'] = "Edges volatils, considérer variance dans sizing"
    else:
        volatility_analysis['description'] = f"Volatilité {volatility_analysis['profile'].lower()} (vol={combined_volatility:.2f})"
        volatility_analysis['betting_impact'] = "Edges moyennement fiables"
    
    return volatility_analysis


def calculate_regression_to_mean(defender: dict, team_defense: dict) -> dict:
    """
    4. REGRESSION TO MEAN ANALYSIS
    Compare buts réels vs xGA attendu
    """
    
    # Données équipe (proxy pour le défenseur)
    xga_total = team_defense.get('xga_total', 0)
    ga_total = team_defense.get('ga_total', 0)
    matches = team_defense.get('matches_played', 1)
    
    # Données individuelles
    xga_with = defender.get('xGA_with', 0)
    goals_conceded_with = defender.get('goals_conceded_with', 0)
    matches_with = defender.get('matches_analyzed_with', 1)
    
    # Calcul du delta de régression
    if xga_with > 0:
        # Utiliser données individuelles si disponibles
        delta = (goals_conceded_with - xga_with) / max(matches_with, 1)
        xga_per_match = xga_with / max(matches_with, 1)
        ga_per_match = goals_conceded_with / max(matches_with, 1)
    else:
        # Sinon utiliser données équipe
        delta = (ga_total - xga_total) / max(matches, 1)
        xga_per_match = xga_total / max(matches, 1)
        ga_per_match = ga_total / max(matches, 1)
    
    regression_analysis = {
        'xGA_per_match': round(xga_per_match, 3),
        'goals_conceded_per_match': round(ga_per_match, 3),
        'delta_per_match': round(delta, 3),
        'total_delta': round(delta * matches_with, 2),
        'status': '',
        'regression_expected': '',
        'betting_edge_adjustment': 0
    }
    
    # Interprétation
    if delta > 0.15:
        regression_analysis['status'] = 'UNLUCKY'
        regression_analysis['regression_expected'] = 'POSITIVE'
        regression_analysis['description'] = f"Malchanceux: concède {delta:.2f} buts/match de plus que xGA attendu"
        regression_analysis['betting_edge_adjustment'] = -1.5  # Réduire edge Goals Over
    elif delta < -0.15:
        regression_analysis['status'] = 'LUCKY'
        regression_analysis['regression_expected'] = 'NEGATIVE'
        regression_analysis['description'] = f"Chanceux: concède {abs(delta):.2f} buts/match de moins que xGA"
        regression_analysis['betting_edge_adjustment'] = 2.0  # Augmenter edge Goals Over
    else:
        regression_analysis['status'] = 'FAIR'
        regression_analysis['regression_expected'] = 'STABLE'
        regression_analysis['description'] = f"Performance en ligne avec xGA (delta: {delta:+.2f})"
        regression_analysis['betting_edge_adjustment'] = 0
    
    return regression_analysis


def calculate_aerial_dominance(defender: dict, team_goals: list, team_actions: dict) -> dict:
    """
    5. AERIAL DOMINANCE INDEX
    Analyse vulnérabilité aérienne
    """
    
    aerial_analysis = {
        'description': 'Vulnérabilité sur situations aériennes',
        'metrics': {},
        'vulnerability_level': 'UNKNOWN',
        'betting_edge': 0
    }
    
    if not team_goals:
        aerial_analysis['vulnerability_level'] = 'NO_DATA'
        return aerial_analysis
    
    total_goals = len(team_goals)
    
    # Compter les buts par type
    head_goals = 0
    corner_goals = 0
    cross_goals = 0
    set_piece_goals = 0
    
    for goal in team_goals:
        shot_type = goal.get('shotType', goal.get('type', '')).lower()
        situation = goal.get('situation', '').lower()
        last_action = goal.get('lastAction', '').lower()
        
        if 'head' in shot_type:
            head_goals += 1
        if 'corner' in situation or 'corner' in last_action:
            corner_goals += 1
        if 'cross' in last_action:
            cross_goals += 1
        if 'setpiece' in situation or 'set' in situation or 'free' in situation:
            set_piece_goals += 1
    
    # Calculer les ratios
    head_ratio = head_goals / max(total_goals, 1)
    corner_ratio = corner_goals / max(total_goals, 1)
    cross_ratio = cross_goals / max(total_goals, 1)
    set_piece_ratio = set_piece_goals / max(total_goals, 1)
    
    # Score aérien combiné
    aerial_vulnerability = (head_ratio * 0.4 + corner_ratio * 0.3 + cross_ratio * 0.3)
    
    aerial_analysis['metrics'] = {
        'total_goals_conceded': total_goals,
        'head_goals': head_goals,
        'head_ratio': round(head_ratio * 100, 1),
        'corner_goals': corner_goals,
        'corner_ratio': round(corner_ratio * 100, 1),
        'cross_goals': cross_goals,
        'cross_ratio': round(cross_ratio * 100, 1),
        'set_piece_goals': set_piece_goals,
        'set_piece_ratio': round(set_piece_ratio * 100, 1),
        'aerial_vulnerability_score': round(aerial_vulnerability * 100, 1)
    }
    
    # Classification
    if aerial_vulnerability > 0.35:
        aerial_analysis['vulnerability_level'] = 'CRITICAL'
        aerial_analysis['description'] = f"Très vulnérable aérien ({aerial_vulnerability*100:.0f}%): {head_goals} headers, {corner_goals} corners"
        aerial_analysis['betting_edge'] = 3.5
    elif aerial_vulnerability > 0.25:
        aerial_analysis['vulnerability_level'] = 'HIGH'
        aerial_analysis['description'] = f"Vulnérable aérien ({aerial_vulnerability*100:.0f}%)"
        aerial_analysis['betting_edge'] = 2.0
    elif aerial_vulnerability > 0.15:
        aerial_analysis['vulnerability_level'] = 'MEDIUM'
        aerial_analysis['description'] = f"Vulnérabilité aérienne moyenne ({aerial_vulnerability*100:.0f}%)"
        aerial_analysis['betting_edge'] = 0.5
    else:
        aerial_analysis['vulnerability_level'] = 'LOW'
        aerial_analysis['description'] = f"Solide aérialement ({aerial_vulnerability*100:.0f}%)"
        aerial_analysis['betting_edge'] = -1.0
    
    return aerial_analysis


def calculate_fatigue_model(defender: dict) -> dict:
    """
    6. FATIGUE MODEL
    Estime l'impact de la charge de matchs
    """
    
    time_played = defender.get('time', 0)
    games = defender.get('games', 0)
    
    # Minutes moyennes par match
    avg_minutes = time_played / max(games, 1)
    
    # Estimation de la charge récente (basée sur la saison)
    # On estime que les matchs sont répartis sur ~20 semaines
    matches_per_week = games / 20 if games > 0 else 0
    minutes_per_week = time_played / 20 if time_played > 0 else 0
    
    fatigue_analysis = {
        'total_minutes': time_played,
        'total_games': games,
        'avg_minutes_per_game': round(avg_minutes, 1),
        'estimated_minutes_per_week': round(minutes_per_week, 1),
        'estimated_games_per_week': round(matches_per_week, 2),
        'fatigue_risk': 'LOW',
        'fatigue_score': 0,
        'performance_impact': 0
    }
    
    # Calculer le score de fatigue
    # Plus de minutes = plus de fatigue
    # Plus de 90 min/semaine = risque
    fatigue_score = minutes_per_week / 90  # Normalisé à 1.0 = 90min/semaine
    
    if avg_minutes > 85:  # Joue presque tout le temps
        fatigue_score *= 1.2
    
    fatigue_analysis['fatigue_score'] = round(fatigue_score, 2)
    
    # Impact sur la performance (fin de match)
    if fatigue_score > 1.5:
        fatigue_analysis['fatigue_risk'] = 'HIGH'
        fatigue_analysis['performance_impact'] = -0.15
        fatigue_analysis['description'] = f"Charge élevée ({minutes_per_week:.0f} min/sem) → Risque fatigue fin de match"
        fatigue_analysis['late_game_vulnerability'] = True
    elif fatigue_score > 1.0:
        fatigue_analysis['fatigue_risk'] = 'MEDIUM'
        fatigue_analysis['performance_impact'] = -0.08
        fatigue_analysis['description'] = f"Charge modérée ({minutes_per_week:.0f} min/sem)"
        fatigue_analysis['late_game_vulnerability'] = False
    else:
        fatigue_analysis['fatigue_risk'] = 'LOW'
        fatigue_analysis['performance_impact'] = 0
        fatigue_analysis['description'] = f"Charge gérable ({minutes_per_week:.0f} min/sem)"
        fatigue_analysis['late_game_vulnerability'] = False
    
    return fatigue_analysis


def calculate_contextual_multiplier(defender: dict, team_context: dict) -> dict:
    """
    7. CONTEXTUAL EDGE MULTIPLIER
    Ajustement dynamique selon le contexte
    """
    
    momentum = team_context.get('momentum_dna', {})
    
    context_analysis = {
        'base_multiplier': 1.0,
        'factors': [],
        'final_multiplier': 1.0,
        'description': ''
    }
    
    multiplier = 1.0
    
    # Factor 1: Forme récente
    form = momentum.get('form_last_5', 'XXXXX')
    losses = form.count('L')
    wins = form.count('W')
    
    if losses >= 4:
        multiplier *= 1.35
        context_analysis['factors'].append({
            'factor': 'RELEGATION_FORM',
            'multiplier': 1.35,
            'reason': f"Forme catastrophique: {form}"
        })
    elif losses >= 3:
        multiplier *= 1.2
        context_analysis['factors'].append({
            'factor': 'POOR_FORM',
            'multiplier': 1.2,
            'reason': f"Mauvaise forme: {form}"
        })
    elif wins >= 4:
        multiplier *= 0.85
        context_analysis['factors'].append({
            'factor': 'EXCELLENT_FORM',
            'multiplier': 0.85,
            'reason': f"Excellente forme: {form}"
        })
    
    # Factor 2: Tendance
    trending = momentum.get('trending', 'STABLE')
    if trending == 'DOWN':
        multiplier *= 1.15
        context_analysis['factors'].append({
            'factor': 'TRENDING_DOWN',
            'multiplier': 1.15,
            'reason': "Tendance négative"
        })
    elif trending == 'UP':
        multiplier *= 0.9
        context_analysis['factors'].append({
            'factor': 'TRENDING_UP',
            'multiplier': 0.9,
            'reason': "Tendance positive"
        })
    
    # Factor 3: xG Overperformance (régression)
    xg_over = momentum.get('xGA_overperformance', 0)
    if xg_over < -2:  # Chanceux
        multiplier *= 1.2
        context_analysis['factors'].append({
            'factor': 'LUCKY_REGRESSION',
            'multiplier': 1.2,
            'reason': f"xGA overperf: {xg_over:.2f} → régression attendue"
        })
    elif xg_over > 2:  # Malchanceux
        multiplier *= 0.9
        context_analysis['factors'].append({
            'factor': 'UNLUCKY_REGRESSION',
            'multiplier': 0.9,
            'reason': f"xGA overperf: {xg_over:.2f} → amélioration attendue"
        })
    
    # Factor 4: Failed to score (pression offensive)
    failed_to_score = momentum.get('failed_to_score_last_5', 0)
    if failed_to_score >= 3:
        multiplier *= 1.1
        context_analysis['factors'].append({
            'factor': 'OFFENSIVE_CRISIS',
            'multiplier': 1.1,
            'reason': f"{failed_to_score} matchs sans marquer → pression défense"
        })
    
    context_analysis['final_multiplier'] = round(multiplier, 2)
    context_analysis['description'] = f"Multiplier ×{multiplier:.2f}" + \
        (f" ({len(context_analysis['factors'])} facteurs)" if context_analysis['factors'] else "")
    
    return context_analysis


def calculate_expected_cards(defender: dict, friction: dict) -> dict:
    """
    8. EXPECTED CARDS MODEL (xCards)
    Modèle probabiliste de cartons
    """
    
    cards_90 = defender.get('cards_90', 0)
    yellow = defender.get('yellow_cards', 0)
    red = defender.get('red_cards', 0)
    games = defender.get('games', 1)
    
    xCards_analysis = {
        'base_yellow_rate': round(cards_90, 3),
        'base_red_rate': round(red / max(games, 1), 4),
        'historical_yellow': yellow,
        'historical_red': red,
        'xYellow_base': round(cards_90, 3),
        'xRed_base': round(min(cards_90 * 0.08, 0.1), 4),
        'adjustments': [],
        'final_xYellow': 0,
        'final_xRed': 0,
        'probability_card_next_match': 0
    }
    
    # Base probabilities
    x_yellow = cards_90
    x_red = red / max(games, 1)
    
    # Adjustment 1: Friction avec attaquants techniques
    tech_friction = friction.get('profiles', {}).get('TECHNICAL_WIZARD', {})
    if tech_friction.get('danger_level') in ['CRITICAL', 'HIGH']:
        multiplier = tech_friction.get('card_risk_multiplier', 1.3)
        x_yellow *= multiplier
        xCards_analysis['adjustments'].append({
            'factor': 'TECHNICAL_OPPONENTS',
            'multiplier': multiplier,
            'reason': f"Vulnérable aux dribbleurs → ×{multiplier:.2f}"
        })
    
    # Adjustment 2: Historique de rouges
    if red >= 1:
        x_red *= 1.5
        x_yellow *= 1.1
        xCards_analysis['adjustments'].append({
            'factor': 'RED_CARD_HISTORY',
            'multiplier': 1.5,
            'reason': f"{red} rouge(s) cette saison → risque élevé"
        })
    
    # Adjustment 3: Impact négatif (frustration)
    impact = defender.get('impact_goals_conceded', 0)
    if impact < -0.3:
        x_yellow *= 1.15
        xCards_analysis['adjustments'].append({
            'factor': 'FRUSTRATION_FACTOR',
            'multiplier': 1.15,
            'reason': f"Maillon faible (impact {impact:.2f}) → frustration"
        })
    
    xCards_analysis['final_xYellow'] = round(x_yellow, 3)
    xCards_analysis['final_xRed'] = round(x_red, 4)
    
    # Probabilité d'au moins un carton
    p_no_card = (1 - x_yellow) * (1 - x_red)
    p_card = 1 - p_no_card
    
    xCards_analysis['probability_card_next_match'] = round(p_card * 100, 1)
    xCards_analysis['probability_yellow'] = round(x_yellow * 100, 1)
    xCards_analysis['probability_red'] = round(x_red * 100, 1)
    
    # Description
    if p_card > 0.5:
        xCards_analysis['risk_level'] = 'VERY_HIGH'
        xCards_analysis['description'] = f"P(carton)={p_card*100:.0f}% - Cible privilégiée"
        xCards_analysis['betting_edge'] = (p_card - 0.3) * 10  # Edge vs ligne de base 30%
    elif p_card > 0.35:
        xCards_analysis['risk_level'] = 'HIGH'
        xCards_analysis['description'] = f"P(carton)={p_card*100:.0f}% - Risque élevé"
        xCards_analysis['betting_edge'] = (p_card - 0.3) * 8
    elif p_card > 0.2:
        xCards_analysis['risk_level'] = 'MEDIUM'
        xCards_analysis['description'] = f"P(carton)={p_card*100:.0f}% - Risque modéré"
        xCards_analysis['betting_edge'] = 0
    else:
        xCards_analysis['risk_level'] = 'LOW'
        xCards_analysis['description'] = f"P(carton)={p_card*100:.0f}% - Jeu propre"
        xCards_analysis['betting_edge'] = -2.0
    
    return xCards_analysis


def calculate_clutch_performance(defender: dict, team_context: dict) -> dict:
    """
    9. CLUTCH PERFORMANCE INDEX
    Performance dans les moments décisifs
    """
    
    gamestate = team_context.get('context_dna', {}).get('gameState', {})
    momentum = team_context.get('momentum_dna', {})
    
    clutch_analysis = {
        'description': 'Performance dans moments critiques',
        'situations': {},
        'clutch_rating': 'UNKNOWN',
        'choke_risk': False,
        'betting_implications': []
    }
    
    # Analyser les situations critiques
    
    # 1. Score serré (±1 but)
    tight_situations = []
    for state in ['Goal diff 0', 'Goal diff +1', 'Goal diff -1']:
        if state in gamestate:
            data = gamestate[state]
            tight_situations.append({
                'state': state,
                'goals_against_90': data.get('goals_against_90', 0),
                'xG_against_90': data.get('xG_against_90', 0)
            })
    
    if tight_situations:
        avg_goals_tight = np.mean([s['goals_against_90'] for s in tight_situations])
        avg_xg_tight = np.mean([s['xG_against_90'] for s in tight_situations])
        
        clutch_analysis['situations']['tight_score'] = {
            'avg_goals_against_90': round(avg_goals_tight, 2),
            'avg_xG_against_90': round(avg_xg_tight, 2),
            'performance': 'CHOKES' if avg_goals_tight > 1.8 else 
                          'STRUGGLES' if avg_goals_tight > 1.3 else
                          'CLUTCH' if avg_goals_tight < 0.8 else 'NEUTRAL'
        }
    
    # 2. Quand mené (pressure)
    trailing_states = ['Goal diff -1', 'Goal diff < -1']
    trailing_data = []
    for state in trailing_states:
        if state in gamestate:
            trailing_data.append(gamestate[state])
    
    if trailing_data:
        avg_goals_trailing = np.mean([d.get('goals_against_90', 0) for d in trailing_data])
        clutch_analysis['situations']['when_trailing'] = {
            'avg_goals_against_90': round(avg_goals_trailing, 2),
            'performance': 'COLLAPSES' if avg_goals_trailing > 2.0 else
                          'STRUGGLES' if avg_goals_trailing > 1.5 else 'SOLID'
        }
    
    # 3. Protection du lead
    if 'Goal diff +1' in gamestate:
        leading_data = gamestate['Goal diff +1']
        goals_when_leading = leading_data.get('goals_against_90', 0)
        clutch_analysis['situations']['protecting_lead'] = {
            'goals_against_90': round(goals_when_leading, 2),
            'performance': 'COLLAPSES' if goals_when_leading > 2.0 else
                          'NERVOUS' if goals_when_leading > 1.3 else 'SOLID'
        }
        
        if goals_when_leading > 1.5:
            clutch_analysis['choke_risk'] = True
            clutch_analysis['betting_implications'].append({
                'market': 'COMEBACK',
                'edge': round((goals_when_leading - 1.0) * 3, 1),
                'trigger': 'Équipe adverse mène'
            })
    
    # Calculer le rating global
    performances = []
    for sit, data in clutch_analysis['situations'].items():
        perf = data.get('performance', 'NEUTRAL')
        if perf in ['CLUTCH', 'SOLID']:
            performances.append(1)
        elif perf in ['NEUTRAL']:
            performances.append(0)
        else:
            performances.append(-1)
    
    if performances:
        avg_perf = np.mean(performances)
        if avg_perf > 0.5:
            clutch_analysis['clutch_rating'] = 'CLUTCH_PERFORMER'
            clutch_analysis['description'] = "Excellent sous pression - Élève son niveau"
        elif avg_perf < -0.5:
            clutch_analysis['clutch_rating'] = 'CHOKE_ARTIST'
            clutch_analysis['description'] = "Craque sous pression - Cible dans moments clés"
            clutch_analysis['betting_implications'].append({
                'market': 'LATE_GOALS',
                'edge': 3.0,
                'trigger': 'Score serré en fin de match'
            })
        else:
            clutch_analysis['clutch_rating'] = 'NEUTRAL'
            clutch_analysis['description'] = "Performance stable quelle que soit la pression"
    
    return clutch_analysis


def calculate_value_at_risk(defender: dict, volatility: dict) -> dict:
    """
    10. VALUE AT RISK (VaR)
    Quantification du pire scénario
    """
    
    mean_conceded = volatility.get('mean_goals_conceded', 1.5)
    std_conceded = volatility.get('estimated_std', 0.8)
    
    var_analysis = {
        'mean_goals_conceded': round(mean_conceded, 2),
        'std_goals_conceded': round(std_conceded, 2),
        'VaR_90': 0,  # 90% confidence
        'VaR_95': 0,  # 95% confidence
        'VaR_99': 0,  # 99% confidence
        'extreme_scenarios': {},
        'betting_implications': []
    }
    
    # Calcul VaR (distribution normale approximée)
    # VaR = mean + z_score × std
    var_analysis['VaR_90'] = round(mean_conceded + 1.28 * std_conceded, 1)
    var_analysis['VaR_95'] = round(mean_conceded + 1.65 * std_conceded, 1)
    var_analysis['VaR_99'] = round(mean_conceded + 2.33 * std_conceded, 1)
    
    # Probabilités de scénarios extrêmes (Poisson approximation)
    lambda_val = mean_conceded
    
    def poisson_prob(k, lam):
        """Probabilité de k buts avec paramètre lambda"""
        return (lam ** k) * math.exp(-lam) / math.factorial(k)
    
    # Calculer probabilités
    p_0_goals = poisson_prob(0, lambda_val)
    p_1_goals = poisson_prob(1, lambda_val)
    p_2_goals = poisson_prob(2, lambda_val)
    p_3_goals = poisson_prob(3, lambda_val)
    p_4_plus = 1 - (p_0_goals + p_1_goals + p_2_goals + p_3_goals)
    
    var_analysis['extreme_scenarios'] = {
        'P(clean_sheet)': round(p_0_goals * 100, 1),
        'P(1_goal)': round(p_1_goals * 100, 1),
        'P(2_goals)': round(p_2_goals * 100, 1),
        'P(3_goals)': round(p_3_goals * 100, 1),
        'P(4+_goals)': round(p_4_plus * 100, 1)
    }
    
    # Implications betting
    if p_4_plus > 0.15:
        var_analysis['betting_implications'].append({
            'market': 'Team To Concede 4+',
            'probability': round(p_4_plus * 100, 1),
            'edge': 'HIGH_VALUE si cote > 6.0'
        })
    
    if p_0_goals < 0.10:
        var_analysis['betting_implications'].append({
            'market': 'Both Teams To Score',
            'probability': round((1 - p_0_goals) * 100, 1),
            'edge': f"BTTS YES value (CS prob only {p_0_goals*100:.0f}%)"
        })
    
    # Description
    if var_analysis['VaR_95'] >= 4.0:
        var_analysis['risk_category'] = 'EXTREME_RISK'
        var_analysis['description'] = f"VaR95={var_analysis['VaR_95']} buts - Dans 5% des cas peut concéder 4+"
    elif var_analysis['VaR_95'] >= 3.0:
        var_analysis['risk_category'] = 'HIGH_RISK'
        var_analysis['description'] = f"VaR95={var_analysis['VaR_95']} buts - Risque de gros score"
    else:
        var_analysis['risk_category'] = 'MODERATE_RISK'
        var_analysis['description'] = f"VaR95={var_analysis['VaR_95']} buts - Risque contrôlé"
    
    return var_analysis


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3: CALCUL V8.0 COMPLET
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═'*80}")
print("🔬 PHASE 3: ANALYSE QUANT V8.0 (10 DIMENSIONS)")
print(f"{'═'*80}")

processed = 0
for d in defenders:
    if d.get('time', 0) < 400:
        continue
    
    team = d.get('team', '')
    team_context = teams_context.get(team, {})
    team_defense = team_defense_dna.get(team, {})
    team_goals = goals_by_team.get(team, [])
    team_actions = action_analysis.get(team, {})
    team_defenders = defenders_by_team.get(team, [])
    
    # Calculer les 10 dimensions
    v8_analysis = {}
    
    # 1. Paire Synergy
    v8_analysis['paire_synergy'] = calculate_paire_synergy(d, team_defenders)
    
    # 2. Matchup Friction
    v8_analysis['matchup_friction'] = calculate_matchup_friction(d, team_context)
    
    # 3. Volatility Index
    v8_analysis['volatility'] = calculate_volatility_index(d, team_context)
    
    # 4. Regression to Mean
    v8_analysis['regression'] = calculate_regression_to_mean(d, team_defense)
    
    # 5. Aerial Dominance
    v8_analysis['aerial'] = calculate_aerial_dominance(d, team_goals, team_actions)
    
    # 6. Fatigue Model
    v8_analysis['fatigue'] = calculate_fatigue_model(d)
    
    # 7. Contextual Multiplier
    v8_analysis['context'] = calculate_contextual_multiplier(d, team_context)
    
    # 8. Expected Cards
    v8_analysis['xCards'] = calculate_expected_cards(d, v8_analysis['matchup_friction'])
    
    # 9. Clutch Performance
    v8_analysis['clutch'] = calculate_clutch_performance(d, team_context)
    
    # 10. Value at Risk
    v8_analysis['var'] = calculate_value_at_risk(d, v8_analysis['volatility'])
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SYNTHÈSE V8.0: CALCUL DES EDGES ENRICHIS
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Récupérer les edges V7 et les enrichir
    v7_edges = d.get('quant_v7', {}).get('edges', {})
    v7_total_edge = d.get('quant_v7', {}).get('total_edge', 0)
    
    # Calculer les ajustements V8
    edge_adjustments = []
    
    # Adjustment 1: Regression
    reg_adj = v8_analysis['regression'].get('betting_edge_adjustment', 0)
    if reg_adj != 0:
        edge_adjustments.append(('REGRESSION', reg_adj))
    
    # Adjustment 2: Aerial
    aerial_edge = v8_analysis['aerial'].get('betting_edge', 0)
    if aerial_edge > 0:
        edge_adjustments.append(('AERIAL_VULN', aerial_edge))
    
    # Adjustment 3: xCards
    xcards_edge = v8_analysis['xCards'].get('betting_edge', 0)
    if xcards_edge > 1.5:
        edge_adjustments.append(('XCARDS', xcards_edge))
    
    # Adjustment 4: Clutch
    for impl in v8_analysis['clutch'].get('betting_implications', []):
        edge_adjustments.append((impl['market'], impl['edge']))
    
    # Adjustment 5: Context Multiplier
    context_mult = v8_analysis['context'].get('final_multiplier', 1.0)
    
    # Calculer le total edge V8
    v8_base_adjustment = sum(adj[1] for adj in edge_adjustments)
    v8_total_edge = (v7_total_edge + v8_base_adjustment) * context_mult
    
    v8_analysis['edge_synthesis'] = {
        'v7_base_edge': round(v7_total_edge, 1),
        'v8_adjustments': edge_adjustments,
        'v8_adjustment_total': round(v8_base_adjustment, 1),
        'context_multiplier': round(context_mult, 2),
        'v8_total_edge': round(v8_total_edge, 1)
    }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SIGNATURE V8.0 ENRICHIE
    # ═══════════════════════════════════════════════════════════════════════════
    
    signature_parts = []
    
    # Impact de base
    impact = d.get('impact_goals_conceded', 0)
    impact_pct = d.get('dna', {}).get('dimensions', {}).get('SHIELD', 50) if d.get('dna') else 50
    if impact_pct <= 25:
        signature_parts.append(f"MAILLON FAIBLE (P{impact_pct:.0f})")
    elif impact_pct >= 75:
        signature_parts.append(f"PILIER (P{impact_pct:.0f})")
    
    # Synergy
    if v8_analysis['paire_synergy'].get('isolation_risk'):
        signature_parts.append("ISOLÉ")
    elif v8_analysis['paire_synergy'].get('best_partner', {}).get('compatibility') == 'EXCELLENT':
        signature_parts.append(f"SYNERGIE+ {v8_analysis['paire_synergy']['best_partner']['partner'][:10]}")
    
    # Friction critique
    critical_matchup = v8_analysis['matchup_friction'].get('critical_matchup', {})
    if critical_matchup.get('danger') == 'CRITICAL':
        signature_parts.append(f"FRICTION {critical_matchup['type'][:8]}")
    
    # Volatilité
    vol_profile = v8_analysis['volatility'].get('profile', '')
    if vol_profile == 'WILDCARD':
        signature_parts.append("WILDCARD")
    elif vol_profile == 'ROCK':
        signature_parts.append("ROCK")
    
    # Régression
    reg_status = v8_analysis['regression'].get('status', '')
    if reg_status == 'LUCKY':
        signature_parts.append("CHANCEUX→RÉGRESSION")
    elif reg_status == 'UNLUCKY':
        signature_parts.append("MALCHANCEUX")
    
    # Aérien
    aerial_level = v8_analysis['aerial'].get('vulnerability_level', '')
    if aerial_level == 'CRITICAL':
        signature_parts.append("VULNÉRABLE AÉRIEN")
    
    # Clutch
    clutch_rating = v8_analysis['clutch'].get('clutch_rating', '')
    if clutch_rating == 'CHOKE_ARTIST':
        signature_parts.append("CHOKE")
    elif clutch_rating == 'CLUTCH_PERFORMER':
        signature_parts.append("CLUTCH")
    
    # xCards
    if v8_analysis['xCards'].get('risk_level') == 'VERY_HIGH':
        signature_parts.append(f"xCARD {v8_analysis['xCards']['probability_card_next_match']:.0f}%")
    
    # VaR
    if v8_analysis['var'].get('risk_category') == 'EXTREME_RISK':
        signature_parts.append(f"VaR95={v8_analysis['var']['VaR_95']}")
    
    v8_analysis['signature_v8'] = ' | '.join(signature_parts) if signature_parts else 'PROFIL STANDARD'
    
    # Fingerprint V8
    v8_analysis['fingerprint_v8'] = f"V8-E{int(v8_total_edge)}-VOL{v8_analysis['volatility']['profile'][:3]}-{v8_analysis['clutch']['clutch_rating'][:3] if v8_analysis['clutch'].get('clutch_rating') else 'NEU'}"
    
    # Assigner au défenseur
    d['quant_v8'] = v8_analysis
    
    processed += 1

print(f"   ✅ {processed} défenseurs analysés")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4: SAUVEGARDE
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═'*80}")
print("💾 PHASE 4: SAUVEGARDE")
print(f"{'═'*80}")

with open(DEFENDER_DIR / 'defender_dna_quant_v8.json', 'w') as f:
    json.dump(defenders, f, indent=2, ensure_ascii=False)
print(f"   ✅ defender_dna_quant_v8.json")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5: RAPPORT DÉTAILLÉ
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═'*80}")
print("📊 PHASE 5: RAPPORT QUANT V8.0 - HEDGE FUND GRADE 2.0")
print(f"{'═'*80}")

# Exemples détaillés
examples = ['Toti', 'Gabriel', 'van Dijk', 'Dimarco']

for name in examples:
    player = next((d for d in defenders if name in d.get('name', '') and d.get('quant_v8')), None)
    if player:
        v8 = player['quant_v8']
        
        print(f"\n{'═'*80}")
        print(f"👤 {player['name']} ({player['team']} - {player['league']})")
        print(f"{'═'*80}")
        
        print(f"\n📛 SIGNATURE V8: {v8['signature_v8']}")
        print(f"🔑 FINGERPRINT: {v8['fingerprint_v8']}")
        
        # 1. Synergy
        print(f"\n┌─────────────────────────────────────────────────────────────────────────────┐")
        print(f"│ 1️⃣  PAIRE SYNERGY ANALYSIS                                                   │")
        print(f"├─────────────────────────────────────────────────────────────────────────────┤")
        syn = v8['paire_synergy']
        if syn.get('best_partner'):
            print(f"│ ✅ Meilleur: {syn['best_partner']['partner']:<20} (score: {syn['best_partner']['synergy_score']:+.2f}, {syn['best_partner']['compatibility']}) │")
        if syn.get('worst_partner'):
            print(f"│ ❌ Pire:     {syn['worst_partner']['partner']:<20} (score: {syn['worst_partner']['synergy_score']:+.2f}, {syn['worst_partner']['compatibility']}) │")
        if syn.get('isolation_risk'):
            print(f"│ ⚠️  {syn['isolation_description']:<67} │")
        print(f"└─────────────────────────────────────────────────────────────────────────────┘")
        
        # 2. Friction
        print(f"\n┌─────────────────────────────────────────────────────────────────────────────┐")
        print(f"│ 2️⃣  MATCHUP FRICTION INDEX                                                   │")
        print(f"├─────────────────────────────────────────────────────────────────────────────┤")
        friction = v8['matchup_friction']
        for profile, data in friction['profiles'].items():
            emoji = '🔴' if data['danger_level'] == 'CRITICAL' else '🟡' if data['danger_level'] == 'HIGH' else '⚪'
            print(f"│ {emoji} {profile:<20}: {data['danger_level']:<10} (friction: {data['friction_score']:.2f}) │")
        print(f"│ 🎯 Critical: {friction['critical_matchup']['type']:<15} | Safe: {friction['safe_matchup']['type']:<15} │")
        print(f"└─────────────────────────────────────────────────────────────────────────────┘")
        
        # 3. Volatility
        print(f"\n┌─────────────────────────────────────────────────────────────────────────────┐")
        print(f"│ 3️⃣  VOLATILITY INDEX                                                         │")
        print(f"├─────────────────────────────────────────────────────────────────────────────┤")
        vol = v8['volatility']
        profile_emoji = '🪨' if vol['profile'] == 'ROCK' else '🎰' if vol['profile'] == 'WILDCARD' else '📊'
        print(f"│ {profile_emoji} Profil: {vol['profile']:<15} | Volatilité: {vol['combined_volatility']:.2f}             │")
        print(f"│ 📈 Mean: {vol['mean_goals_conceded']:.2f} buts/match | Std: {vol['estimated_std']:.2f}                        │")
        print(f"│ �� {vol['betting_impact']:<63} │")
        print(f"└─────────────────────────────────────────────────────────────────────────────┘")
        
        # 4. Regression
        print(f"\n┌─────────────────────────────────────────────────────────────────────────────┐")
        print(f"│ 4️⃣  REGRESSION TO MEAN                                                       │")
        print(f"├─────────────────────────────────────────────────────────────────────────────┤")
        reg = v8['regression']
        status_emoji = '🍀' if reg['status'] == 'LUCKY' else '😢' if reg['status'] == 'UNLUCKY' else '⚖️'
        print(f"│ {status_emoji} Status: {reg['status']:<12} | Delta: {reg['delta_per_match']:+.3f} buts/match           │")
        print(f"│ 📊 xGA/match: {reg['xGA_per_match']:.3f} | Réels: {reg['goals_conceded_per_match']:.3f}                       │")
        print(f"│ 📈 Edge adjustment: {reg['betting_edge_adjustment']:+.1f}%                                         │")
        print(f"└─────────────────────────────────────────────────────────────────────────────┘")
        
        # 5. Aerial
        print(f"\n┌─────────────────────────────────────────────────────────────────────────────┐")
        print(f"│ 5️⃣  AERIAL DOMINANCE INDEX                                                   │")
        print(f"├─────────────────────────────────────────────────────────────────────────────┤")
        aer = v8['aerial']
        if aer['vulnerability_level'] != 'NO_DATA':
            level_emoji = '🔴' if aer['vulnerability_level'] == 'CRITICAL' else '🟡' if aer['vulnerability_level'] == 'HIGH' else '🟢'
            metrics = aer['metrics']
            print(f"│ {level_emoji} Niveau: {aer['vulnerability_level']:<12} | Score: {metrics['aerial_vulnerability_score']:.1f}%         │")
            print(f"│ 🗣️ Headers: {metrics['head_goals']} ({metrics['head_ratio']:.0f}%) | Corners: {metrics['corner_goals']} ({metrics['corner_ratio']:.0f}%) | Crosses: {metrics['cross_goals']} │")
            print(f"│ 📈 Edge: {aer['betting_edge']:+.1f}%                                                     │")
        else:
            print(f"│ ⚪ Pas de données disponibles                                               │")
        print(f"└─────────────────────────────────────────────────────────────────────────────┘")
        
        # 6. Fatigue
        print(f"\n┌─────────────────────────────────────────────────────────────────────────────┐")
        print(f"│ 6️⃣  FATIGUE MODEL                                                            │")
        print(f"├─────────────────────────────────────────────────────────────────────────────┤")
        fat = v8['fatigue']
        risk_emoji = '🔴' if fat['fatigue_risk'] == 'HIGH' else '🟡' if fat['fatigue_risk'] == 'MEDIUM' else '🟢'
        print(f"│ {risk_emoji} Risque: {fat['fatigue_risk']:<8} | Score: {fat['fatigue_score']:.2f}                          │")
        print(f"│ ⏱️ {fat['total_minutes']} min total | ~{fat['estimated_minutes_per_week']:.0f} min/semaine                      │")
        print(f"│ 📉 Impact perf: {fat['performance_impact']:+.0%}                                              │")
        print(f"└─────────────────────────────────────────────────────────────────────────────┘")
        
        # 7. Context
        print(f"\n┌─────────────────────────────────────────────────────────────────────────────┐")
        print(f"│ 7️⃣  CONTEXTUAL EDGE MULTIPLIER                                               │")
        print(f"├─────────────────────────────────────────────────────────────────────────────┤")
        ctx = v8['context']
        print(f"│ 🎯 Multiplier Final: ×{ctx['final_multiplier']:.2f}                                           │")
        for factor in ctx['factors'][:3]:
            print(f"│    • {factor['factor']:<20}: ×{factor['multiplier']:.2f} ({factor['reason'][:30]}...) │")
        print(f"└─────────────────────────────────────────────────────────────────────────────┘")
        
        # 8. xCards
        print(f"\n┌─────────────────────────────────────────────────────────────────────────────┐")
        print(f"│ 8️⃣  EXPECTED CARDS MODEL (xCards)                                            │")
        print(f"├─────────────────────────────────────────────────────────────────────────────┤")
        xc = v8['xCards']
        risk_emoji = '🔴' if xc['risk_level'] == 'VERY_HIGH' else '🟡' if xc['risk_level'] == 'HIGH' else '🟢'
        print(f"│ {risk_emoji} P(carton): {xc['probability_card_next_match']:.0f}% | P(jaune): {xc['probability_yellow']:.0f}% | P(rouge): {xc['probability_red']:.1f}% │")
        print(f"│ 📊 xYellow: {xc['final_xYellow']:.3f} | xRed: {xc['final_xRed']:.4f}                               │")
        if xc['adjustments']:
            for adj in xc['adjustments'][:2]:
                print(f"│    • {adj['factor']:<25}: {adj['reason'][:40]}... │")
        print(f"└─────────────────────────────────────────────────────────────────────────────┘")
        
        # 9. Clutch
        print(f"\n┌─────────────────────────────────────────────────────────────────────────────┐")
        print(f"│ 9️⃣  CLUTCH PERFORMANCE INDEX                                                 │")
        print(f"├─────────────────────────────────────────────────────────────────────────────┤")
        clu = v8['clutch']
        rating_emoji = '🏆' if clu['clutch_rating'] == 'CLUTCH_PERFORMER' else '😰' if clu['clutch_rating'] == 'CHOKE_ARTIST' else '⚪'
        print(f"│ {rating_emoji} Rating: {clu['clutch_rating']:<20}                                   │")
        for sit, data in clu['situations'].items():
            print(f"│    • {sit:<20}: {data.get('performance', 'N/A'):<12} ({data.get('avg_goals_against_90', data.get('goals_against_90', 0)):.2f}/90) │")
        if clu['choke_risk']:
            print(f"│ ⚠️ CHOKE RISK: Vulnérable dans les moments décisifs                         │")
        print(f"└─────────────────────────────────────────────────────────────────────────────┘")
        
        # 10. VaR
        print(f"\n┌─────────────────────────────────────────────────────────────────────────────┐")
        print(f"│ 🔟 VALUE AT RISK (VaR)                                                       │")
        print(f"├─────────────────────────────────────────────────────────────────────────────┤")
        var = v8['var']
        cat_emoji = '🔴' if var['risk_category'] == 'EXTREME_RISK' else '🟡' if var['risk_category'] == 'HIGH_RISK' else '🟢'
        print(f"│ {cat_emoji} Catégorie: {var['risk_category']:<15}                                      │")
        print(f"│ 📊 VaR90: {var['VaR_90']:.1f} | VaR95: {var['VaR_95']:.1f} | VaR99: {var['VaR_99']:.1f}                         │")
        print(f"│ 📈 Scénarios: P(CS)={var['extreme_scenarios']['P(clean_sheet)']:.0f}% | P(3+)={var['extreme_scenarios']['P(3_goals)'] + var['extreme_scenarios']['P(4+_goals)']:.0f}% | P(4+)={var['extreme_scenarios']['P(4+_goals)']:.0f}% │")
        print(f"└─────────────────────────────────────────────────────────────────────────────┘")
        
        # Synthèse Edge
        print(f"\n┌─────────────────────────────────────────────────────────────────────────────┐")
        print(f"│ �� SYNTHÈSE EDGE V8.0                                                        │")
        print(f"├─────────────────────────────────────────────────────────────────────────────┤")
        edge_syn = v8['edge_synthesis']
        print(f"│ V7 Base Edge:        {edge_syn['v7_base_edge']:+.1f}%                                        │")
        print(f"│ V8 Adjustments:      {edge_syn['v8_adjustment_total']:+.1f}%                                        │")
        for adj in edge_syn['v8_adjustments'][:3]:
            print(f"│    • {adj[0]:<20}: {adj[1]:+.1f}%                                      │")
        print(f"│ Context Multiplier:  ×{edge_syn['context_multiplier']:.2f}                                         │")
        print(f"│ ═══════════════════════════════════════════════════════════════════════════ │")
        print(f"│ 🎯 TOTAL EDGE V8:    {edge_syn['v8_total_edge']:+.1f}%                                        │")
        print(f"└─────────────────────────────────────────────────────────────────────────────┘")

# Top 25 par Edge V8
print(f"\n{'═'*80}")
print("💰 TOP 25 DÉFENSEURS PAR EDGE V8.0")
print(f"{'═'*80}")

ranked = sorted([d for d in defenders if d.get('quant_v8')], 
                key=lambda x: x['quant_v8']['edge_synthesis']['v8_total_edge'], reverse=True)

print(f"\n{'Rank':<5}│{'Nom':<25}│{'Équipe':<22}│{'EdgeV7':<8}│{'EdgeV8':<8}│{'Δ':<6}│{'Signature':<30}")
print("─" * 115)
for i, d in enumerate(ranked[:25], 1):
    v7_edge = d.get('quant_v7', {}).get('total_edge', 0)
    v8_edge = d['quant_v8']['edge_synthesis']['v8_total_edge']
    delta = v8_edge - v7_edge
    sig = d['quant_v8']['signature_v8'][:27] + '...' if len(d['quant_v8']['signature_v8']) > 27 else d['quant_v8']['signature_v8']
    print(f"{i:<5}│{d['name']:<25}│{d['team']:<22}│{v7_edge:+6.1f}%│{v8_edge:+6.1f}%│{delta:+5.1f}│{sig:<30}")

print(f"\n{'═'*80}")
print(f"✅ DEFENDER DNA QUANT V8.0 - HEDGE FUND GRADE 2.0 COMPLET")
print(f"   10 dimensions analysées | {processed} défenseurs | Edges contextuels enrichis")
print(f"{'═'*80}")
