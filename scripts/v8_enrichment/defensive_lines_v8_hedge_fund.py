#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
 DEFENSIVE LINES V8.0 - HEDGE FUND GRADE 3.0
 Multi-Source Fusion Analysis
═══════════════════════════════════════════════════════════════════════════════
 
 SOURCES INTÉGRÉES:
 1. team_defense_dna_v5_1_corrected.json (96 équipes, ~120 dimensions)
 2. defender_dna_quant_v9.json (664 défenseurs, 52 dimensions)
 3. teams_context_dna.json (context_dna, momentum_dna, player_impact_dna)
 4. goalkeeper_timing_dna_v1.json (96 GK, timing vulnerabilities)
 
 DIMENSIONS D'ANALYSE (30+):
 - Foundation Metrics (xGA, GA, CS, percentiles)
 - Resistance Vector (10 dimensions: resist_*)
 - Temporal Analysis (6 périodes de 15 min)
 - GameState Response (level, leading, losing)
 - Zone Vulnerability (six_yard, penalty_area, outside_box)
 - Set Piece Analysis (corner, free_kick, penalty, open_play)
 - Goalkeeper Integration (timing, vulnerabilities, exploit_paths)
 - Defender Aggregation (top defenders impact, xGBuildup allowed)
 - Context DNA (momentum, form, history)
 - Edge Synthesis (multi-factor Kelly)
 
 Auteur: Mon_PS Quant Team
 Version: 8.0 Hedge Fund Grade 3.0
 Date: 2025-12-09
═══════════════════════════════════════════════════════════════════════════════
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict
import statistics

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DATA_PATHS = {
    'team_defense': '/home/Mon_ps/data/defense_dna/team_defense_dna_v5_1_corrected.json',
    'defenders': '/home/Mon_ps/data/defender_dna/defender_dna_quant_v9.json',
    'context_dna': '/home/Mon_ps/data/quantum_v2/teams_context_dna.json',
    'goalkeeper': '/home/Mon_ps/data/goalkeeper_dna/goalkeeper_timing_dna_v1.json',
    'team_exploit': '/home/Mon_ps/data/quantum_v2/team_exploit_profiles.json',
    'players_impact': '/home/Mon_ps/data/quantum_v2/players_impact_dna.json',
}

OUTPUT_PATH = '/home/Mon_ps/data/defender_dna/defensive_lines_v8_hedge_fund.json'

# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADERS
# ═══════════════════════════════════════════════════════════════════════════════

def load_json(path: str) -> Any:
    """Charge un fichier JSON avec gestion d'erreurs"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️ Fichier non trouvé: {path}")
        return None
    except json.JSONDecodeError as e:
        print(f"⚠️ Erreur JSON dans {path}: {e}")
        return None

def load_all_sources() -> Dict[str, Any]:
    """Charge toutes les sources de données"""
    print("═" * 70)
    print("📂 CHARGEMENT DES SOURCES DE DONNÉES")
    print("═" * 70)
    
    sources = {}
    for name, path in DATA_PATHS.items():
        data = load_json(path)
        if data:
            if isinstance(data, list):
                print(f"✅ {name}: {len(data)} éléments")
            elif isinstance(data, dict):
                print(f"✅ {name}: {len(data)} clés")
            sources[name] = data
        else:
            print(f"❌ {name}: Non chargé")
    
    return sources

# ═══════════════════════════════════════════════════════════════════════════════
# TEAM NAME NORMALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def normalize_team_name(name: str) -> str:
    """Normalise les noms d'équipes pour le matching"""
    if not name:
        return ""
    
    name = name.lower().strip()
    
    # Mappings connus
    mappings = {
        'manchester united': 'manchester united',
        'man united': 'manchester united',
        'man utd': 'manchester united',
        'manchester city': 'manchester city',
        'man city': 'manchester city',
        'tottenham hotspur': 'tottenham',
        'tottenham': 'tottenham',
        'spurs': 'tottenham',
        'wolverhampton wanderers': 'wolverhampton',
        'wolverhampton': 'wolverhampton',
        'wolves': 'wolverhampton',
        'newcastle united': 'newcastle united',
        'newcastle': 'newcastle united',
        'west ham united': 'west ham',
        'west ham': 'west ham',
        'nottingham forest': 'nottingham forest',
        "nott'm forest": 'nottingham forest',
        'brighton and hove albion': 'brighton',
        'brighton': 'brighton',
        'leicester city': 'leicester',
        'leicester': 'leicester',
        'leeds united': 'leeds',
        'leeds': 'leeds',
        'afc bournemouth': 'bournemouth',
        'bournemouth': 'bournemouth',
        'crystal palace': 'crystal palace',
        'sheffield united': 'sheffield united',
        'sheffield utd': 'sheffield united',
        'luton town': 'luton',
        'luton': 'luton',
        'paris saint-germain': 'paris saint germain',
        'paris saint germain': 'paris saint germain',
        'psg': 'paris saint germain',
        'bayern munich': 'bayern munich',
        'fc bayern münchen': 'bayern munich',
        'bayern münchen': 'bayern munich',
        'borussia dortmund': 'borussia dortmund',
        'dortmund': 'borussia dortmund',
        'bvb': 'borussia dortmund',
        'rb leipzig': 'rb leipzig',
        'rasenballsport leipzig': 'rb leipzig',
        'atletico madrid': 'atletico madrid',
        'atlético madrid': 'atletico madrid',
        'atletico de madrid': 'atletico madrid',
        'real madrid': 'real madrid',
        'barcelona': 'barcelona',
        'fc barcelona': 'barcelona',
        'inter milan': 'inter',
        'inter': 'inter',
        'internazionale': 'inter',
        'ac milan': 'ac milan',
        'milan': 'ac milan',
        'juventus': 'juventus',
        'napoli': 'napoli',
        'ssc napoli': 'napoli',
        'as roma': 'roma',
        'roma': 'roma',
        'atalanta': 'atalanta',
        'lazio': 'lazio',
        'ss lazio': 'lazio',
    }
    
    return mappings.get(name, name)

# ═══════════════════════════════════════════════════════════════════════════════
# DEFENDER AGGREGATION BY TEAM
# ═══════════════════════════════════════════════════════════════════════════════

def aggregate_defenders_by_team(defenders: List[Dict]) -> Dict[str, Dict]:
    """Agrège les statistiques des défenseurs par équipe"""
    team_defenders = defaultdict(list)
    
    for defender in defenders:
        # Trouver le nom de l'équipe dans les données
        team_name = None
        
        # Chercher dans différents champs possibles
        for field in ['team', 'team_name', 'club']:
            if field in defender and defender[field]:
                team_name = defender[field]
                break
        
        if not team_name:
            continue
            
        team_defenders[normalize_team_name(team_name)].append(defender)
    
    # Calculer les agrégats par équipe
    team_aggregates = {}
    
    for team, defs in team_defenders.items():
        if not defs:
            continue
            
        # Trier par temps de jeu (time_90)
        defs_sorted = sorted(defs, key=lambda x: x.get('time_90', 0) or 0, reverse=True)
        
        # Prendre les 4-5 principaux défenseurs
        main_defenders = defs_sorted[:5]
        
        # Agrégations
        aggregate = {
            'num_defenders': len(defs),
            'main_defenders': [d.get('name', 'Unknown') for d in main_defenders],
            
            # Impact offensif des défenseurs (dangereux sur corners)
            'total_xG': sum(d.get('xG', 0) or 0 for d in main_defenders),
            'total_xA': sum(d.get('xA', 0) or 0 for d in main_defenders),
            'avg_xGBuildup_90': statistics.mean([d.get('xGBuildup_90', 0) or 0 for d in main_defenders]) if main_defenders else 0,
            
            # Cartons (risque disciplinaire)
            'total_yellow_cards': sum(d.get('yellow_cards', 0) or 0 for d in main_defenders),
            'total_red_cards': sum(d.get('red_cards', 0) or 0 for d in main_defenders),
            'avg_cards_90': statistics.mean([d.get('cards_90', 0) or 0 for d in main_defenders]) if main_defenders else 0,
            
            # Impact défensif (with vs without)
            'avg_goals_conceded_with': statistics.mean([d.get('goals_conceded_per_match_with', 0) or 0 for d in main_defenders]) if main_defenders else 0,
            'avg_goals_conceded_without': statistics.mean([d.get('goals_conceded_per_match_without', 0) or 0 for d in main_defenders]) if main_defenders else 0,
            'avg_clean_sheet_rate_with': statistics.mean([d.get('clean_sheet_rate_with', 0) or 0 for d in main_defenders]) if main_defenders else 0,
            'avg_win_rate_with': statistics.mean([d.get('win_rate_with', 0) or 0 for d in main_defenders]) if main_defenders else 0,
        }
        
        # Calculer le delta (impact net des défenseurs)
        aggregate['defender_impact_delta'] = aggregate['avg_goals_conceded_without'] - aggregate['avg_goals_conceded_with']
        
        # Risque disciplinaire
        if aggregate['avg_cards_90'] > 0.4:
            aggregate['disciplinary_risk'] = 'HIGH'
        elif aggregate['avg_cards_90'] > 0.25:
            aggregate['disciplinary_risk'] = 'MODERATE'
        else:
            aggregate['disciplinary_risk'] = 'LOW'
        
        team_aggregates[team] = aggregate
    
    return team_aggregates

# ═══════════════════════════════════════════════════════════════════════════════
# GOALKEEPER INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

def create_goalkeeper_index(goalkeepers: List[Dict]) -> Dict[str, Dict]:
    """Crée un index des gardiens par équipe"""
    gk_index = {}
    
    for gk in goalkeepers:
        team = gk.get('team', '')
        if team:
            normalized = normalize_team_name(team)
            gk_index[normalized] = {
                'name': gk.get('goalkeeper', 'Unknown'),
                'save_rate': gk.get('save_rate', 0),
                'total_saves': gk.get('total_saves', 0),
                'total_goals': gk.get('total_goals', 0),
                'total_xG': gk.get('total_xG', 0),
                'timing': gk.get('timing', {}),
                'vulnerabilities': gk.get('vulnerabilities', []),
                'strengths': gk.get('strengths', []),
                'timing_tags': gk.get('timing_tags', []),
                'exploit_paths': gk.get('exploit_paths', []),
                'timing_fingerprint': gk.get('timing_fingerprint', ''),
                'percentiles': gk.get('percentiles', {}),
                'gk_percentile': gk.get('gk_percentile', 50),
                'profile_v31': gk.get('profile_v31', ''),
            }
            
            # Calculer over/under performance du GK
            if gk_index[normalized]['total_xG'] > 0:
                gk_index[normalized]['gk_overperform'] = gk_index[normalized]['total_xG'] - gk_index[normalized]['total_goals']
            else:
                gk_index[normalized]['gk_overperform'] = 0
    
    return gk_index

# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT DNA INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

def extract_context_insights(context_data: Dict, team_name: str) -> Dict:
    """Extrait les insights du context_dna pour une équipe"""
    normalized = normalize_team_name(team_name)
    
    # Chercher l'équipe dans le dict
    team_data = None
    for key in context_data.keys():
        if normalize_team_name(key) == normalized:
            team_data = context_data[key]
            break
    
    if not team_data:
        return {}
    
    insights = {
        'has_context_dna': True,
    }
    
    # Extraire context_dna
    if 'context_dna' in team_data:
        ctx = team_data['context_dna']
        insights['context_home_strength'] = ctx.get('home_strength', 0)
        insights['context_away_strength'] = ctx.get('away_strength', 0)
        insights['context_form_trend'] = ctx.get('form_trend', 'STABLE')
    
    # Extraire momentum_dna
    if 'momentum_dna' in team_data:
        mom = team_data['momentum_dna']
        insights['momentum_score'] = mom.get('momentum_score', 0)
        insights['momentum_direction'] = mom.get('direction', 'NEUTRAL')
        insights['momentum_streak'] = mom.get('streak', 0)
    
    # Extraire player_impact_dna
    if 'player_impact_dna' in team_data:
        player = team_data['player_impact_dna']
        insights['key_player_dependency'] = player.get('key_player_dependency', 0)
        insights['squad_depth_score'] = player.get('squad_depth_score', 0)
    
    return insights

# ═══════════════════════════════════════════════════════════════════════════════
# RESISTANCE VECTOR ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_resistance_vector(team: Dict) -> Dict:
    """Analyse le vecteur de résistance (10 dimensions)"""
    resistance = {
        'resist_global': team.get('resist_global', 50),
        'resist_home': team.get('resist_home', 50),
        'resist_away': team.get('resist_away', 50),
        'resist_early': team.get('resist_early', 50),
        'resist_late': team.get('resist_late', 50),
        'resist_set_piece': team.get('resist_set_piece', 50),
        'resist_open_play': team.get('resist_open_play', 50),
        'resist_aerial': team.get('resist_aerial', 50),
        'resist_longshot': team.get('resist_longshot', 50),
        'resist_chaos': team.get('resist_chaos', 50),
    }
    
    # Calculer les vulnérabilités critiques (<30)
    vulnerabilities = []
    strengths = []
    
    for key, value in resistance.items():
        if value < 30:
            vulnerabilities.append(key.replace('resist_', ''))
        elif value > 70:
            strengths.append(key.replace('resist_', ''))
    
    # Score de vulnérabilité composite
    vulnerability_score = 100 - statistics.mean(resistance.values())
    
    # Profil de résistance
    if resistance['resist_global'] >= 70:
        resist_profile = 'FORTRESS'
    elif resistance['resist_global'] >= 55:
        resist_profile = 'SOLID'
    elif resistance['resist_global'] >= 40:
        resist_profile = 'AVERAGE'
    elif resistance['resist_global'] >= 25:
        resist_profile = 'VULNERABLE'
    else:
        resist_profile = 'CRISIS'
    
    return {
        'resistance_vector': resistance,
        'critical_vulnerabilities': vulnerabilities,
        'defensive_strengths': strengths,
        'vulnerability_score': vulnerability_score,
        'resist_profile': resist_profile,
        'weakest_dimension': min(resistance, key=resistance.get),
        'strongest_dimension': max(resistance, key=resistance.get),
    }

# ═══════════════════════════════════════════════════════════════════════════════
# TEMPORAL VULNERABILITY ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_temporal_vulnerability(team: Dict) -> Dict:
    """Analyse la vulnérabilité temporelle (6 périodes de 15 min)"""
    
    # xGA par période
    xga_periods = {
        '0-15': team.get('xga_0_15', 0) or 0,
        '16-30': team.get('xga_16_30', 0) or 0,
        '31-45': team.get('xga_31_45', 0) or 0,
        '46-60': team.get('xga_46_60', 0) or 0,
        '61-75': team.get('xga_61_75', 0) or 0,
        '76-90': team.get('xga_76_90', 0) or 0,
    }
    
    # GA par période
    ga_periods = {
        '0-15': team.get('ga_0_15', 0) or 0,
        '16-30': team.get('ga_16_30', 0) or 0,
        '31-45': team.get('ga_31_45', 0) or 0,
        '46-60': team.get('ga_46_60', 0) or 0,
        '61-75': team.get('ga_61_75', 0) or 0,
        '76-90': team.get('ga_76_90', 0) or 0,
    }
    
    total_xga = sum(xga_periods.values())
    total_ga = sum(ga_periods.values())
    
    # Calculer les pourcentages
    xga_pct = {}
    if total_xga > 0:
        for period, val in xga_periods.items():
            xga_pct[period] = round(val / total_xga * 100, 1)
    else:
        xga_pct = {k: 16.7 for k in xga_periods.keys()}
    
    # Identifier les périodes critiques
    most_vulnerable_period = max(xga_pct, key=xga_pct.get) if xga_pct else '76-90'
    least_vulnerable_period = min(xga_pct, key=xga_pct.get) if xga_pct else '0-15'
    
    # Analyser les phases
    first_half_xga = xga_periods['0-15'] + xga_periods['16-30'] + xga_periods['31-45']
    second_half_xga = xga_periods['46-60'] + xga_periods['61-75'] + xga_periods['76-90']
    
    early_xga = xga_periods['0-15'] + xga_periods['16-30']
    late_xga = xga_periods['61-75'] + xga_periods['76-90']
    
    # Profils temporels
    if total_xga > 0:
        late_pct = (late_xga / total_xga) * 100
        early_pct = (early_xga / total_xga) * 100
    else:
        late_pct = 33.3
        early_pct = 33.3
    
    if late_pct > 45:
        timing_profile = 'LATE_COLLAPSER'
    elif late_pct < 25:
        timing_profile = 'STRONG_FINISHER'
    elif early_pct > 45:
        timing_profile = 'SLOW_STARTER'
    elif early_pct < 25:
        timing_profile = 'FAST_STARTER'
    else:
        timing_profile = 'BALANCED'
    
    return {
        'xga_by_period': xga_periods,
        'ga_by_period': ga_periods,
        'xga_pct_by_period': xga_pct,
        'most_vulnerable_period': most_vulnerable_period,
        'least_vulnerable_period': least_vulnerable_period,
        'first_half_xga': first_half_xga,
        'second_half_xga': second_half_xga,
        'early_game_xga': early_xga,
        'late_game_xga': late_xga,
        'late_game_pct': round(late_pct, 1),
        'early_game_pct': round(early_pct, 1),
        'timing_profile': timing_profile,
        'timing_edge': {
            'early_bet_value': '+' if early_pct > 40 else '-' if early_pct < 28 else '=',
            'late_bet_value': '+' if late_pct > 40 else '-' if late_pct < 28 else '=',
        }
    }

# ═══════════════════════════════════════════════════════════════════════════════
# GAMESTATE RESPONSE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_gamestate_response(team: Dict) -> Dict:
    """Analyse la réponse selon le score (level, leading, losing)"""
    
    gamestate = {
        'level': {
            'xga': team.get('xga_level', 0) or 0,
            'ga': team.get('ga_level', 0) or 0,
        },
        'leading_1': {
            'xga': team.get('xga_leading_1', 0) or 0,
            'ga': team.get('ga_leading_1', 0) or 0,
        },
        'leading_2plus': {
            'xga': team.get('xga_leading_2plus', 0) or 0,
            'ga': team.get('ga_leading_2plus', 0) or 0,
        },
        'losing_1': {
            'xga': team.get('xga_losing_1', 0) or 0,
            'ga': team.get('ga_losing_1', 0) or 0,
        },
        'losing_2plus': {
            'xga': team.get('xga_losing_2plus', 0) or 0,
            'ga': team.get('ga_losing_2plus', 0) or 0,
        },
    }
    
    # Calculer les ratios
    total_xga = sum(gs['xga'] for gs in gamestate.values())
    
    if total_xga > 0:
        gamestate_pct = {
            'level_pct': gamestate['level']['xga'] / total_xga * 100,
            'leading_pct': (gamestate['leading_1']['xga'] + gamestate['leading_2plus']['xga']) / total_xga * 100,
            'losing_pct': (gamestate['losing_1']['xga'] + gamestate['losing_2plus']['xga']) / total_xga * 100,
        }
    else:
        gamestate_pct = {'level_pct': 50, 'leading_pct': 25, 'losing_pct': 25}
    
    # Profil gamestate
    if gamestate_pct['losing_pct'] > 40:
        gamestate_profile = 'CHASES_GAME_POORLY'  # Vulnérable quand ils doivent attaquer
    elif gamestate_pct['leading_pct'] > 35:
        gamestate_profile = 'CANT_HOLD_LEAD'  # Vulnérable en protection de résultat
    elif gamestate_pct['level_pct'] > 60:
        gamestate_profile = 'LEVEL_VULNERABLE'
    else:
        gamestate_profile = 'BALANCED_GAMESTATE'
    
    # Insights betting
    insights = []
    if gamestate['leading_1']['xga'] > gamestate['level']['xga'] * 0.3:
        insights.append("Vulnérable quand mène 1-0 → Value sur égalisation")
    if gamestate['losing_2plus']['xga'] < gamestate['losing_1']['xga'] * 0.5:
        insights.append("Se ressaisit quand mené 2+ → Moins de valeur sur blow-out")
    
    return {
        'gamestate_data': gamestate,
        'gamestate_pct': gamestate_pct,
        'gamestate_profile': gamestate_profile,
        'gamestate_insights': insights,
    }

# ═══════════════════════════════════════════════════════════════════════════════
# ZONE VULNERABILITY ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_zone_vulnerability(team: Dict) -> Dict:
    """Analyse la vulnérabilité par zone (six-yard, penalty area, outside box)"""
    
    zones = {
        'six_yard': {
            'xga': team.get('xga_six_yard', 0) or 0,
            'ga': team.get('ga_six_yard', 0) or 0,
            'shots': team.get('shots_ag_six_yard', 0) or 0,
        },
        'penalty_area': {
            'xga': team.get('xga_penalty_area', 0) or 0,
            'ga': team.get('ga_penalty_area', 0) or 0,
            'shots': team.get('shots_ag_penalty_area', 0) or 0,
        },
        'outside_box': {
            'xga': team.get('xga_outside_box', 0) or 0,
            'ga': team.get('ga_outside_box', 0) or 0,
            'shots': team.get('shots_ag_outside_box', 0) or 0,
        },
    }
    
    # Calculer les conversion rates
    for zone in zones.values():
        if zone['shots'] > 0:
            zone['conversion_rate'] = zone['ga'] / zone['shots'] * 100
            zone['xg_per_shot'] = zone['xga'] / zone['shots']
        else:
            zone['conversion_rate'] = 0
            zone['xg_per_shot'] = 0
    
    # Identifier la zone la plus vulnérable
    total_xga = sum(z['xga'] for z in zones.values())
    if total_xga > 0:
        zone_pct = {name: z['xga'] / total_xga * 100 for name, z in zones.items()}
    else:
        zone_pct = {'six_yard': 33.3, 'penalty_area': 50, 'outside_box': 16.7}
    
    most_vulnerable_zone = max(zone_pct, key=zone_pct.get)
    
    # Profil de zone
    if zone_pct['six_yard'] > 35:
        zone_profile = 'CLOSE_RANGE_VULNERABLE'
    elif zone_pct['outside_box'] > 25:
        zone_profile = 'LONGSHOT_VULNERABLE'
    elif zone_pct['penalty_area'] > 60:
        zone_profile = 'BOX_VULNERABLE'
    else:
        zone_profile = 'BALANCED_ZONE'
    
    return {
        'zone_data': zones,
        'zone_pct': zone_pct,
        'most_vulnerable_zone': most_vulnerable_zone,
        'zone_profile': zone_profile,
    }

# ═══════════════════════════════════════════════════════════════════════════════
# SET PIECE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_set_pieces(team: Dict) -> Dict:
    """Analyse détaillée des coups de pied arrêtés"""
    
    set_pieces = {
        'corner': {
            'xga': team.get('xga_corner', 0) or 0,
            'ga': team.get('ga_corner', 0) or 0,
        },
        'free_kick': {
            'xga': team.get('xga_free_kick', 0) or 0,
            'ga': team.get('ga_free_kick', 0) or 0,
        },
        'penalty': {
            'xga': team.get('xga_penalty', 0) or 0,
            'ga': team.get('ga_penalty', 0) or 0,
        },
        'open_play': {
            'xga': team.get('xga_open_play', 0) or 0,
            'ga': team.get('ga_open_play', 0) or 0,
        },
    }
    
    total_xga = sum(sp['xga'] for sp in set_pieces.values())
    total_sp_xga = set_pieces['corner']['xga'] + set_pieces['free_kick']['xga'] + set_pieces['penalty']['xga']
    
    # Pourcentage set pieces
    if total_xga > 0:
        set_piece_pct = total_sp_xga / total_xga * 100
    else:
        set_piece_pct = 25
    
    # Profil
    if set_piece_pct > 35:
        sp_profile = 'SET_PIECE_VULNERABLE'
    elif set_piece_pct < 18:
        sp_profile = 'SET_PIECE_SOLID'
    else:
        sp_profile = 'SET_PIECE_AVERAGE'
    
    # Détail des vulnérabilités
    sp_vulnerabilities = []
    if set_pieces['corner']['xga'] > 10:
        sp_vulnerabilities.append('CORNER_VULNERABLE')
    if set_pieces['free_kick']['xga'] > 3:
        sp_vulnerabilities.append('FREEKICK_VULNERABLE')
    if set_pieces['penalty']['xga'] > 5:
        sp_vulnerabilities.append('GIVES_PENALTIES')
    
    return {
        'set_piece_data': set_pieces,
        'set_piece_pct': round(set_piece_pct, 1),
        'set_piece_profile': sp_profile,
        'set_piece_vulnerabilities': sp_vulnerabilities,
        'aerial_threat_level': 'HIGH' if set_pieces['corner']['xga'] > 12 else 'MODERATE' if set_pieces['corner']['xga'] > 8 else 'LOW',
    }

# ═══════════════════════════════════════════════════════════════════════════════
# EDGE SYNTHESIS - HEDGE FUND GRADE
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_hedge_fund_edge(
    team: Dict,
    resistance: Dict,
    temporal: Dict,
    gamestate: Dict,
    zones: Dict,
    set_pieces: Dict,
    gk_data: Optional[Dict],
    defender_agg: Optional[Dict],
    context: Dict
) -> Dict:
    """Calcule l'edge multi-factoriel Hedge Fund Grade"""
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMPOSANTES DE L'EDGE
    # ═══════════════════════════════════════════════════════════════════════════
    
    edge_components = {}
    
    # 1. RESISTANCE EDGE (basé sur le vecteur de résistance)
    resist_global = resistance['resistance_vector']['resist_global']
    if resist_global < 25:
        edge_components['resistance_edge'] = 8.0
    elif resist_global < 35:
        edge_components['resistance_edge'] = 5.0
    elif resist_global < 45:
        edge_components['resistance_edge'] = 2.5
    elif resist_global < 55:
        edge_components['resistance_edge'] = 0.5
    elif resist_global < 65:
        edge_components['resistance_edge'] = -1.0
    elif resist_global < 75:
        edge_components['resistance_edge'] = -3.0
    else:
        edge_components['resistance_edge'] = -5.0
    
    # 2. TEMPORAL EDGE
    late_pct = temporal['late_game_pct']
    if late_pct > 50:
        edge_components['temporal_edge'] = 3.0
    elif late_pct > 42:
        edge_components['temporal_edge'] = 1.5
    elif late_pct < 25:
        edge_components['temporal_edge'] = -2.0
    else:
        edge_components['temporal_edge'] = 0.0
    
    # 3. GAMESTATE EDGE
    gs_profile = gamestate['gamestate_profile']
    if gs_profile == 'CANT_HOLD_LEAD':
        edge_components['gamestate_edge'] = 2.5
    elif gs_profile == 'CHASES_GAME_POORLY':
        edge_components['gamestate_edge'] = 2.0
    elif gs_profile == 'LEVEL_VULNERABLE':
        edge_components['gamestate_edge'] = 1.0
    else:
        edge_components['gamestate_edge'] = 0.0
    
    # 4. ZONE EDGE
    zone_profile = zones['zone_profile']
    if zone_profile == 'CLOSE_RANGE_VULNERABLE':
        edge_components['zone_edge'] = 2.0
    elif zone_profile == 'LONGSHOT_VULNERABLE':
        edge_components['zone_edge'] = 1.5
    else:
        edge_components['zone_edge'] = 0.0
    
    # 5. SET PIECE EDGE
    sp_pct = set_pieces['set_piece_pct']
    if sp_pct > 35:
        edge_components['set_piece_edge'] = 2.5
    elif sp_pct > 28:
        edge_components['set_piece_edge'] = 1.0
    elif sp_pct < 18:
        edge_components['set_piece_edge'] = -1.5
    else:
        edge_components['set_piece_edge'] = 0.0
    
    # 6. GOALKEEPER EDGE
    if gk_data:
        gk_pct = gk_data.get('gk_percentile', 50)
        gk_overperform = gk_data.get('gk_overperform', 0)
        
        # GK faible = edge positif
        if gk_pct < 25:
            edge_components['goalkeeper_edge'] = 3.0
        elif gk_pct < 40:
            edge_components['goalkeeper_edge'] = 1.5
        elif gk_pct > 75:
            edge_components['goalkeeper_edge'] = -2.0
        else:
            edge_components['goalkeeper_edge'] = 0.0
        
        # Régression GK
        if gk_overperform > 5:  # GK surperforme beaucoup
            edge_components['gk_regression_edge'] = 2.0
        elif gk_overperform < -5:  # GK sous-performe
            edge_components['gk_regression_edge'] = -1.5
        else:
            edge_components['gk_regression_edge'] = 0.0
    else:
        edge_components['goalkeeper_edge'] = 0.0
        edge_components['gk_regression_edge'] = 0.0
    
    # 7. DEFENDER AGGREGATE EDGE
    if defender_agg:
        # Impact des défenseurs
        delta = defender_agg.get('defender_impact_delta', 0)
        if delta < -0.3:  # Équipe pire sans ses défenseurs
            edge_components['defender_quality_edge'] = -1.5
        elif delta > 0.3:  # Défenseurs ne font pas grande différence
            edge_components['defender_quality_edge'] = 1.5
        else:
            edge_components['defender_quality_edge'] = 0.0
        
        # Risque disciplinaire
        if defender_agg.get('disciplinary_risk') == 'HIGH':
            edge_components['disciplinary_edge'] = 1.5
        else:
            edge_components['disciplinary_edge'] = 0.0
    else:
        edge_components['defender_quality_edge'] = 0.0
        edge_components['disciplinary_edge'] = 0.0
    
    # 8. CONTEXT/MOMENTUM EDGE
    if context.get('has_context_dna'):
        momentum = context.get('momentum_score', 0)
        if momentum < -3:
            edge_components['momentum_edge'] = 2.0
        elif momentum > 3:
            edge_components['momentum_edge'] = -1.5
        else:
            edge_components['momentum_edge'] = 0.0
    else:
        edge_components['momentum_edge'] = 0.0
    
    # 9. REGRESSION EDGE (xGA vs GA)
    defense_overperform = team.get('defense_overperform', 0) or 0
    if defense_overperform > 8:  # GA << xGA = Lucky
        edge_components['regression_edge'] = 3.5
    elif defense_overperform > 4:
        edge_components['regression_edge'] = 1.5
    elif defense_overperform < -8:  # GA >> xGA = Unlucky
        edge_components['regression_edge'] = -2.0
    elif defense_overperform < -4:
        edge_components['regression_edge'] = -1.0
    else:
        edge_components['regression_edge'] = 0.0
    
    # 10. PERCENTILE EDGE
    percentiles = team.get('percentiles_v5_1', {}) or team.get('percentiles', {})
    if percentiles:
        xga_pct = percentiles.get('xga_per_90', 50)
        if xga_pct < 15:
            edge_components['percentile_edge'] = 4.0
        elif xga_pct < 25:
            edge_components['percentile_edge'] = 2.0
        elif xga_pct > 85:
            edge_components['percentile_edge'] = -3.0
        elif xga_pct > 75:
            edge_components['percentile_edge'] = -1.5
        else:
            edge_components['percentile_edge'] = 0.0
    else:
        edge_components['percentile_edge'] = 0.0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TOTAL EDGE CALCULATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    total_edge = sum(edge_components.values())
    
    # Classification de l'edge
    if total_edge >= 15:
        edge_classification = 'EXTREME_VALUE'
        kelly_multiplier = 1.0
    elif total_edge >= 10:
        edge_classification = 'HIGH_VALUE'
        kelly_multiplier = 0.75
    elif total_edge >= 5:
        edge_classification = 'MODERATE_VALUE'
        kelly_multiplier = 0.5
    elif total_edge >= 2:
        edge_classification = 'SLIGHT_VALUE'
        kelly_multiplier = 0.25
    elif total_edge >= -2:
        edge_classification = 'NO_VALUE'
        kelly_multiplier = 0.0
    elif total_edge >= -5:
        edge_classification = 'NEGATIVE_VALUE'
        kelly_multiplier = 0.0
    else:
        edge_classification = 'STRONG_NEGATIVE'
        kelly_multiplier = 0.0
    
    # Kelly stake (capped at 5%)
    kelly_stake = min(5.0, max(0.0, total_edge * kelly_multiplier * 0.3))
    
    # Confidence score (0-100)
    confidence = min(100, max(0, 50 + total_edge * 3))
    
    return {
        'edge_components': edge_components,
        'total_edge': round(total_edge, 2),
        'edge_classification': edge_classification,
        'kelly_stake': round(kelly_stake, 2),
        'confidence_score': round(confidence, 1),
        'primary_edge_driver': max(edge_components, key=edge_components.get),
        'num_positive_factors': sum(1 for v in edge_components.values() if v > 0),
        'num_negative_factors': sum(1 for v in edge_components.values() if v < 0),
    }

# ═══════════════════════════════════════════════════════════════════════════════
# BETTING RECOMMENDATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def generate_betting_recommendations(
    team: Dict,
    edge: Dict,
    temporal: Dict,
    gamestate: Dict,
    zones: Dict,
    set_pieces: Dict,
    gk_data: Optional[Dict]
) -> Dict:
    """Génère des recommandations de paris détaillées"""
    
    recommendations = {
        'primary_markets': [],
        'secondary_markets': [],
        'avoid_markets': [],
        'timing_plays': [],
        'conditional_plays': [],
    }
    
    total_edge = edge['total_edge']
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PRIMARY MARKETS (Goals Over/Under)
    # ═══════════════════════════════════════════════════════════════════════════
    
    if total_edge >= 10:
        recommendations['primary_markets'].append({
            'market': 'TEAM_GOALS_OVER_1.5',
            'confidence': 'HIGH',
            'edge': f"+{total_edge}%",
            'reasoning': f"Edge extrême ({edge['primary_edge_driver']})"
        })
    elif total_edge >= 5:
        recommendations['primary_markets'].append({
            'market': 'TEAM_GOALS_OVER_0.5',
            'confidence': 'MODERATE',
            'edge': f"+{total_edge}%",
            'reasoning': "Edge positif multi-facteurs"
        })
    elif total_edge <= -5:
        recommendations['primary_markets'].append({
            'market': 'TEAM_CLEAN_SHEET',
            'confidence': 'MODERATE',
            'edge': f"{total_edge}%",
            'reasoning': "Défense solide, faible edge adverse"
        })
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TIMING PLAYS
    # ═══════════════════════════════════════════════════════════════════════════
    
    if temporal['late_game_pct'] > 45:
        recommendations['timing_plays'].append({
            'market': 'GOAL_61-90_YES',
            'confidence': 'HIGH',
            'reasoning': f"Late collapser ({temporal['late_game_pct']}% xGA en fin de match)"
        })
    
    if temporal['early_game_pct'] > 40:
        recommendations['timing_plays'].append({
            'market': 'GOAL_0-30_YES',
            'confidence': 'MODERATE',
            'reasoning': f"Slow starter ({temporal['early_game_pct']}% xGA en début de match)"
        })
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SET PIECE PLAYS
    # ═══════════════════════════════════════════════════════════════════════════
    
    if set_pieces['set_piece_pct'] > 32:
        recommendations['secondary_markets'].append({
            'market': 'CORNER_GOAL_YES',
            'confidence': 'MODERATE',
            'reasoning': f"Set piece vulnerable ({set_pieces['set_piece_pct']}%)"
        })
    
    # ═══════════════════════════════════════════════════════════════════════════
    # GOALKEEPER PLAYS
    # ═══════════════════════════════════════════════════════════════════════════
    
    if gk_data and gk_data.get('gk_percentile', 50) < 30:
        recommendations['secondary_markets'].append({
            'market': 'SHOTS_ON_TARGET_OVER',
            'confidence': 'MODERATE',
            'reasoning': f"GK faible (P{gk_data['gk_percentile']})"
        })
    
    # ═══════════════════════════════════════════════════════════════════════════
    # AVOID MARKETS
    # ═══════════════════════════════════════════════════════════════════════════
    
    if total_edge < 0:
        recommendations['avoid_markets'].append({
            'market': 'GOALS_OVER',
            'reasoning': "Edge négatif - défense solide"
        })
    
    if temporal['late_game_pct'] < 25:
        recommendations['avoid_markets'].append({
            'market': 'LATE_GOAL_YES',
            'reasoning': "Strong finisher - ferme les matchs"
        })
    
    return recommendations

# ═══════════════════════════════════════════════════════════════════════════════
# DNA SIGNATURE GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_dna_signature(
    team: Dict,
    edge: Dict,
    resistance: Dict,
    temporal: Dict
) -> str:
    """Génère une signature DNA unique pour la ligne défensive"""
    
    components = []
    
    # Edge classification
    components.append(edge['edge_classification'][:3])
    
    # Resistance profile
    components.append(f"R{int(resistance['resistance_vector']['resist_global'])}")
    
    # Timing profile
    components.append(temporal['timing_profile'][:4])
    
    # Total edge
    edge_sign = '+' if edge['total_edge'] >= 0 else ''
    components.append(f"E{edge_sign}{int(edge['total_edge'])}")
    
    # Kelly stake
    components.append(f"K{edge['kelly_stake']:.1f}")
    
    return '|'.join(components)

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ANALYSIS FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_defensive_line(
    team: Dict,
    gk_index: Dict,
    defender_aggregates: Dict,
    context_data: Dict
) -> Dict:
    """Analyse complète d'une ligne défensive"""
    
    team_name = team.get('team_name', 'Unknown')
    normalized_name = normalize_team_name(team_name)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COLLECT ALL DATA SOURCES
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Goalkeeper data
    gk_data = gk_index.get(normalized_name, None)
    
    # Defender aggregates
    defender_agg = defender_aggregates.get(normalized_name, None)
    
    # Context DNA
    context = extract_context_insights(context_data, team_name) if context_data else {}
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RUN ALL ANALYSES
    # ═══════════════════════════════════════════════════════════════════════════
    
    resistance = analyze_resistance_vector(team)
    temporal = analyze_temporal_vulnerability(team)
    gamestate = analyze_gamestate_response(team)
    zones = analyze_zone_vulnerability(team)
    set_pieces = analyze_set_pieces(team)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CALCULATE HEDGE FUND EDGE
    # ═══════════════════════════════════════════════════════════════════════════
    
    edge = calculate_hedge_fund_edge(
        team, resistance, temporal, gamestate, zones, set_pieces,
        gk_data, defender_agg, context
    )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # GENERATE RECOMMENDATIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    recommendations = generate_betting_recommendations(
        team, edge, temporal, gamestate, zones, set_pieces, gk_data
    )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # GENERATE DNA SIGNATURE
    # ═══════════════════════════════════════════════════════════════════════════
    
    dna_signature = generate_dna_signature(team, edge, resistance, temporal)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMPILE FINAL RESULT
    # ═══════════════════════════════════════════════════════════════════════════
    
    return {
        # Identity
        'team_name': team_name,
        'league': team.get('league', 'Unknown'),
        'season': team.get('season', '2024/2025'),
        
        # Foundation metrics
        'foundation': {
            'matches_played': team.get('matches_played', 0),
            'xga_total': team.get('xga_total', 0),
            'ga_total': team.get('ga_total', 0),
            'xga_per_90': team.get('xga_per_90', 0),
            'ga_per_90': team.get('ga_per_90', 0),
            'clean_sheets': team.get('clean_sheets', 0),
            'cs_pct': team.get('cs_pct', 0),
            'defense_overperform': team.get('defense_overperform', 0),
        },
        
        # Resistance analysis
        'resistance': resistance,
        
        # Temporal analysis
        'temporal': temporal,
        
        # GameState analysis
        'gamestate': gamestate,
        
        # Zone analysis
        'zones': zones,
        
        # Set piece analysis
        'set_pieces': set_pieces,
        
        # Goalkeeper integration
        'goalkeeper': gk_data if gk_data else {'status': 'NO_DATA'},
        
        # Defender aggregate
        'defenders': defender_agg if defender_agg else {'status': 'NO_DATA'},
        
        # Context DNA
        'context': context if context else {'status': 'NO_DATA'},
        
        # Edge synthesis
        'edge': edge,
        
        # Betting recommendations
        'recommendations': recommendations,
        
        # DNA signature
        'dna_signature': dna_signature,
        
        # Existing data passthrough
        'existing_data': {
            'exploit_paths': team.get('exploit_paths', []),
            'anti_exploits': team.get('anti_exploits', []),
            'betting_insights': team.get('betting_insights', {}),
            'best_markets': team.get('best_markets', []),
            'matchup_guide': team.get('matchup_guide', {}),
            'fingerprint_code': team.get('fingerprint_code', ''),
            'dna_vector': team.get('dna_vector', []),
        },
        
        # Metadata
        'analysis_timestamp': datetime.now().isoformat(),
        'version': 'V8.0_HEDGE_FUND_GRADE_3.0',
    }

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("═" * 70)
    print("🏦 DEFENSIVE LINES V8.0 - HEDGE FUND GRADE 3.0")
    print("   Multi-Source Fusion Analysis")
    print("═" * 70)
    
    # Load all sources
    sources = load_all_sources()
    
    if 'team_defense' not in sources:
        print("❌ ERREUR: Données team_defense non disponibles")
        return
    
    team_defense = sources['team_defense']
    
    # Prepare auxiliary data
    print("\n" + "═" * 70)
    print("🔄 PRÉPARATION DES DONNÉES AUXILIAIRES")
    print("═" * 70)
    
    # Goalkeeper index
    gk_index = {}
    if 'goalkeeper' in sources and sources['goalkeeper']:
        gk_index = create_goalkeeper_index(sources['goalkeeper'])
        print(f"✅ Index gardiens: {len(gk_index)} équipes")
    
    # Defender aggregates
    defender_aggregates = {}
    if 'defenders' in sources and sources['defenders']:
        defender_aggregates = aggregate_defenders_by_team(sources['defenders'])
        print(f"✅ Agrégats défenseurs: {len(defender_aggregates)} équipes")
    
    # Context DNA
    context_data = sources.get('context_dna', {})
    if context_data:
        print(f"✅ Context DNA: {len(context_data)} équipes")
    
    # Analyze all teams
    print("\n" + "═" * 70)
    print("📊 ANALYSE DES LIGNES DÉFENSIVES")
    print("═" * 70)
    
    results = []
    
    for team in team_defense:
        team_name = team.get('team_name', 'Unknown')
        result = analyze_defensive_line(team, gk_index, defender_aggregates, context_data)
        results.append(result)
        
        # Progress
        edge = result['edge']['total_edge']
        classification = result['edge']['edge_classification']
        print(f"  {team_name:25} | Edge: {edge:+6.1f}% | {classification}")
    
    # Sort by edge
    results.sort(key=lambda x: x['edge']['total_edge'], reverse=True)
    
    # Save results
    print("\n" + "═" * 70)
    print("💾 SAUVEGARDE DES RÉSULTATS")
    print("═" * 70)
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Fichier sauvegardé: {OUTPUT_PATH}")
    print(f"   {len(results)} lignes défensives analysées")
    
    # Summary
    print("\n" + "═" * 70)
    print("📈 TOP 10 VALEURS GOALS OVER")
    print("═" * 70)
    
    for i, team in enumerate(results[:10], 1):
        print(f"{i:2}. {team['team_name']:25} | Edge: {team['edge']['total_edge']:+6.1f}% | Kelly: {team['edge']['kelly_stake']:.1f}% | {team['dna_signature']}")
    
    print("\n" + "═" * 70)
    print("📉 TOP 10 VALEURS GOALS UNDER / CLEAN SHEET")
    print("═" * 70)
    
    for i, team in enumerate(results[-10:][::-1], 1):
        print(f"{i:2}. {team['team_name']:25} | Edge: {team['edge']['total_edge']:+6.1f}% | Kelly: {team['edge']['kelly_stake']:.1f}% | {team['dna_signature']}")
    
    # Statistics
    print("\n" + "═" * 70)
    print("📊 STATISTIQUES GLOBALES")
    print("═" * 70)
    
    edges = [r['edge']['total_edge'] for r in results]
    high_value = sum(1 for e in edges if e >= 10)
    moderate_value = sum(1 for e in edges if 5 <= e < 10)
    slight_value = sum(1 for e in edges if 2 <= e < 5)
    no_value = sum(1 for e in edges if -2 <= e < 2)
    negative = sum(1 for e in edges if e < -2)
    
    print(f"Total équipes:     {len(results)}")
    print(f"Edge moyen:        {statistics.mean(edges):+.1f}%")
    print(f"Edge médian:       {statistics.median(edges):+.1f}%")
    print(f"Edge min/max:      {min(edges):+.1f}% / {max(edges):+.1f}%")
    print(f"")
    print(f"HIGH_VALUE (≥10%): {high_value} ({high_value/len(results)*100:.1f}%)")
    print(f"MODERATE (5-10%):  {moderate_value} ({moderate_value/len(results)*100:.1f}%)")
    print(f"SLIGHT (2-5%):     {slight_value} ({slight_value/len(results)*100:.1f}%)")
    print(f"NO_VALUE:          {no_value} ({no_value/len(results)*100:.1f}%)")
    print(f"NEGATIVE (<-2%):   {negative} ({negative/len(results)*100:.1f}%)")
    
    print("\n" + "═" * 70)
    print("✅ ANALYSE TERMINÉE - HEDGE FUND GRADE 3.0")
    print("═" * 70)

if __name__ == '__main__':
    main()
