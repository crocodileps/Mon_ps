#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
 DEFENSIVE LINES V8.1 - HEDGE FUND GRADE 3.1 IMPROVED
 Corrections: 76-90 bug fix, better thresholds, exploit_paths integration
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
}

OUTPUT_PATH = '/home/Mon_ps/data/defender_dna/defensive_lines_v8_1_improved.json'

# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADERS
# ═══════════════════════════════════════════════════════════════════════════════

def load_json(path: str) -> Any:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Erreur {path}: {e}")
        return None

def load_all_sources() -> Dict[str, Any]:
    print("═" * 70)
    print("📂 CHARGEMENT DES SOURCES")
    print("═" * 70)
    
    sources = {}
    for name, path in DATA_PATHS.items():
        data = load_json(path)
        if data:
            size = len(data) if isinstance(data, (list, dict)) else 0
            print(f"✅ {name}: {size} éléments")
            sources[name] = data
    return sources

# ═══════════════════════════════════════════════════════════════════════════════
# TEAM NAME NORMALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def normalize_team_name(name: str) -> str:
    if not name:
        return ""
    name = name.lower().strip()
    
    mappings = {
        'manchester united': 'manchester united', 'man united': 'manchester united', 'man utd': 'manchester united',
        'manchester city': 'manchester city', 'man city': 'manchester city',
        'tottenham hotspur': 'tottenham', 'tottenham': 'tottenham', 'spurs': 'tottenham',
        'wolverhampton wanderers': 'wolverhampton', 'wolverhampton': 'wolverhampton', 'wolves': 'wolverhampton',
        'newcastle united': 'newcastle united', 'newcastle': 'newcastle united',
        'west ham united': 'west ham', 'west ham': 'west ham',
        'nottingham forest': 'nottingham forest', "nott'm forest": 'nottingham forest',
        'brighton and hove albion': 'brighton', 'brighton': 'brighton',
        'leicester city': 'leicester', 'leicester': 'leicester',
        'afc bournemouth': 'bournemouth', 'bournemouth': 'bournemouth',
        'paris saint-germain': 'paris saint germain', 'paris saint germain': 'paris saint germain', 'psg': 'paris saint germain',
        'bayern munich': 'bayern munich', 'fc bayern münchen': 'bayern munich',
        'borussia dortmund': 'borussia dortmund', 'dortmund': 'borussia dortmund',
        'rb leipzig': 'rb leipzig', 'rasenballsport leipzig': 'rb leipzig',
        'atletico madrid': 'atletico madrid', 'atlético madrid': 'atletico madrid',
        'inter milan': 'inter', 'inter': 'inter', 'internazionale': 'inter',
        'ac milan': 'ac milan', 'milan': 'ac milan',
        'as roma': 'roma', 'roma': 'roma',
    }
    return mappings.get(name, name)

# ═══════════════════════════════════════════════════════════════════════════════
# GOALKEEPER INDEX
# ═══════════════════════════════════════════════════════════════════════════════

def create_goalkeeper_index(goalkeepers: List[Dict]) -> Dict[str, Dict]:
    gk_index = {}
    for gk in goalkeepers:
        team = gk.get('team', '')
        if team:
            normalized = normalize_team_name(team)
            gk_index[normalized] = {
                'name': gk.get('goalkeeper', 'Unknown'),
                'save_rate': gk.get('save_rate', 0),
                'gk_percentile': gk.get('gk_percentile', 50),
                'profile_v31': gk.get('profile_v31', ''),
                'vulnerabilities': gk.get('vulnerabilities', []),
                'exploit_paths': gk.get('exploit_paths', []),
                'timing': gk.get('timing', {}),
                'total_xG': gk.get('total_xG', 0),
                'total_goals': gk.get('total_goals', 0),
            }
            # GK overperform (positif = chanceux, négatif = malchanceux)
            gk_index[normalized]['gk_overperform'] = gk_index[normalized]['total_xG'] - gk_index[normalized]['total_goals']
    return gk_index

# ═══════════════════════════════════════════════════════════════════════════════
# DEFENDER AGGREGATION
# ═══════════════════════════════════════════════════════════════════════════════

def aggregate_defenders_by_team(defenders: List[Dict]) -> Dict[str, Dict]:
    team_defenders = defaultdict(list)
    
    for defender in defenders:
        team_name = None
        for field in ['team', 'team_name', 'club']:
            if field in defender and defender[field]:
                team_name = defender[field]
                break
        if not team_name:
            continue
        team_defenders[normalize_team_name(team_name)].append(defender)
    
    aggregates = {}
    for team, defs in team_defenders.items():
        if not defs:
            continue
        
        defs_sorted = sorted(defs, key=lambda x: x.get('time_90', 0) or 0, reverse=True)
        main_defs = defs_sorted[:5]
        
        aggregates[team] = {
            'num_defenders': len(defs),
            'main_defenders': [d.get('name', 'Unknown') for d in main_defs],
            'avg_cards_90': statistics.mean([d.get('cards_90', 0) or 0 for d in main_defs]) if main_defs else 0,
            'avg_goals_conceded_with': statistics.mean([d.get('goals_conceded_per_match_with', 0) or 0 for d in main_defs]) if main_defs else 0,
            'avg_goals_conceded_without': statistics.mean([d.get('goals_conceded_per_match_without', 0) or 0 for d in main_defs]) if main_defs else 0,
            'avg_xGBuildup_90': statistics.mean([d.get('xGBuildup_90', 0) or 0 for d in main_defs]) if main_defs else 0,
        }
        
        aggregates[team]['defender_impact_delta'] = aggregates[team]['avg_goals_conceded_without'] - aggregates[team]['avg_goals_conceded_with']
        
        if aggregates[team]['avg_cards_90'] > 0.4:
            aggregates[team]['disciplinary_risk'] = 'HIGH'
        elif aggregates[team]['avg_cards_90'] > 0.25:
            aggregates[team]['disciplinary_risk'] = 'MODERATE'
        else:
            aggregates[team]['disciplinary_risk'] = 'LOW'
    
    return aggregates

# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT DNA EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def extract_context_insights(context_data: Dict, team_name: str) -> Dict:
    normalized = normalize_team_name(team_name)
    
    for key in context_data.keys():
        if normalize_team_name(key) == normalized:
            team_data = context_data[key]
            insights = {'has_context_dna': True}
            
            if 'context_dna' in team_data:
                ctx = team_data['context_dna']
                insights['form_recent'] = ctx.get('form_recent', 0)
                insights['momentum'] = ctx.get('momentum', 0)
            
            if 'momentum_dna' in team_data:
                mom = team_data['momentum_dna']
                insights['momentum_score'] = mom.get('score', 0)
                insights['momentum_direction'] = mom.get('direction', 'NEUTRAL')
            
            return insights
    
    return {'has_context_dna': False}

# ═══════════════════════════════════════════════════════════════════════════════
# EXPLOIT PROFILES EXTRACTION  
# ═══════════════════════════════════════════════════════════════════════════════

def extract_exploit_profile(exploit_data: Dict, team_name: str) -> Dict:
    normalized = normalize_team_name(team_name)
    
    for key in exploit_data.keys():
        if normalize_team_name(key) == normalized:
            return exploit_data[key]
    
    return {}

# ═══════════════════════════════════════════════════════════════════════════════
# TEMPORAL ANALYSIS - FIXED 76-90 BUG
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_temporal_fixed(team: Dict) -> Dict:
    """Analyse temporelle avec correction du bug 76-90"""
    
    # Récupérer les périodes
    xga_periods = {
        '0-15': team.get('xga_0_15', 0) or 0,
        '16-30': team.get('xga_16_30', 0) or 0,
        '31-45': team.get('xga_31_45', 0) or 0,
        '46-60': team.get('xga_46_60', 0) or 0,
        '61-75': team.get('xga_61_75', 0) or 0,
        '76-90': team.get('xga_76_90', 0) or 0,
    }
    
    # FIX: Si 76-90 = 0 mais xga_2h existe, recalculer
    xga_2h = team.get('xga_2h', 0) or 0
    if xga_periods['76-90'] == 0 and xga_2h > 0:
        # xga_2h = xga_46_60 + xga_61_75 + xga_76_90
        calculated_76_90 = xga_2h - xga_periods['46-60'] - xga_periods['61-75']
        if calculated_76_90 > 0:
            xga_periods['76-90'] = calculated_76_90
    
    # Si toujours 0, estimer à partir de la moyenne des autres périodes
    if xga_periods['76-90'] == 0:
        other_periods = [v for k, v in xga_periods.items() if k != '76-90' and v > 0]
        if other_periods:
            xga_periods['76-90'] = statistics.mean(other_periods) * 1.1  # +10% car fin de match souvent plus vulnérable
    
    total_xga = sum(xga_periods.values())
    
    # Calculer pourcentages
    if total_xga > 0:
        xga_pct = {k: round(v / total_xga * 100, 1) for k, v in xga_periods.items()}
    else:
        xga_pct = {k: 16.7 for k in xga_periods.keys()}
    
    # Phases
    early_xga = xga_periods['0-15'] + xga_periods['16-30']
    late_xga = xga_periods['61-75'] + xga_periods['76-90']
    
    if total_xga > 0:
        late_pct = (late_xga / total_xga) * 100
        early_pct = (early_xga / total_xga) * 100
    else:
        late_pct = 33.3
        early_pct = 33.3
    
    # Profil timing CORRIGÉ
    if late_pct > 42:
        timing_profile = 'LATE_COLLAPSER'
    elif late_pct < 28:
        timing_profile = 'STRONG_FINISHER'
    elif early_pct > 42:
        timing_profile = 'SLOW_STARTER'
    elif early_pct < 28:
        timing_profile = 'FAST_STARTER'
    else:
        timing_profile = 'BALANCED'
    
    return {
        'xga_by_period': xga_periods,
        'xga_pct_by_period': xga_pct,
        'most_vulnerable_period': max(xga_pct, key=xga_pct.get),
        'least_vulnerable_period': min(xga_pct, key=xga_pct.get),
        'early_game_pct': round(early_pct, 1),
        'late_game_pct': round(late_pct, 1),
        'timing_profile': timing_profile,
        'xga_76_90_estimated': xga_periods['76-90'] != (team.get('xga_76_90', 0) or 0),
    }

# ═══════════════════════════════════════════════════════════════════════════════
# RESISTANCE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_resistance(team: Dict) -> Dict:
    resistance = {
        'resist_global': team.get('resist_global', 50) or 50,
        'resist_home': team.get('resist_home', 50) or 50,
        'resist_away': team.get('resist_away', 50) or 50,
        'resist_early': team.get('resist_early', 50) or 50,
        'resist_late': team.get('resist_late', 50) or 50,
        'resist_set_piece': team.get('resist_set_piece', 50) or 50,
        'resist_open_play': team.get('resist_open_play', 50) or 50,
        'resist_aerial': team.get('resist_aerial', 50) or 50,
        'resist_longshot': team.get('resist_longshot', 50) or 50,
        'resist_chaos': team.get('resist_chaos', 50) or 50,
    }
    
    # Vulnérabilités critiques (<25) et forces (>75)
    critical_vulns = [k.replace('resist_', '') for k, v in resistance.items() if v < 25]
    strengths = [k.replace('resist_', '') for k, v in resistance.items() if v > 75]
    
    # Profil
    rg = resistance['resist_global']
    if rg >= 80:
        profile = 'ELITE_FORTRESS'
    elif rg >= 65:
        profile = 'SOLID'
    elif rg >= 50:
        profile = 'AVERAGE'
    elif rg >= 35:
        profile = 'VULNERABLE'
    elif rg >= 20:
        profile = 'CRISIS'
    else:
        profile = 'CATASTROPHIC'
    
    return {
        'resistance_vector': resistance,
        'resist_profile': profile,
        'critical_vulnerabilities': critical_vulns,
        'defensive_strengths': strengths,
        'weakest_dimension': min(resistance, key=resistance.get),
        'strongest_dimension': max(resistance, key=resistance.get),
        'vulnerability_score': round(100 - statistics.mean(resistance.values()), 1),
    }

# ═══════════════════════════════════════════════════════════════════════════════
# GAMESTATE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_gamestate(team: Dict) -> Dict:
    gamestate = {
        'level': team.get('xga_level', 0) or 0,
        'leading_1': team.get('xga_leading_1', 0) or 0,
        'leading_2plus': team.get('xga_leading_2plus', 0) or 0,
        'losing_1': team.get('xga_losing_1', 0) or 0,
        'losing_2plus': team.get('xga_losing_2plus', 0) or 0,
    }
    
    total = sum(gamestate.values())
    
    if total > 0:
        leading_total = gamestate['leading_1'] + gamestate['leading_2plus']
        losing_total = gamestate['losing_1'] + gamestate['losing_2plus']
        
        leading_pct = (leading_total / total) * 100
        losing_pct = (losing_total / total) * 100
        level_pct = (gamestate['level'] / total) * 100
    else:
        leading_pct = losing_pct = level_pct = 33.3
    
    # Profil
    if leading_pct > 35:
        profile = 'CANT_HOLD_LEAD'
    elif losing_pct > 45:
        profile = 'OPENS_UP_WHEN_BEHIND'
    elif level_pct > 55:
        profile = 'LEVEL_VULNERABLE'
    else:
        profile = 'BALANCED_GAMESTATE'
    
    return {
        'gamestate_xga': gamestate,
        'leading_vulnerability_pct': round(leading_pct, 1),
        'losing_vulnerability_pct': round(losing_pct, 1),
        'level_vulnerability_pct': round(level_pct, 1),
        'gamestate_profile': profile,
    }

# ═══════════════════════════════════════════════════════════════════════════════
# SET PIECE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_set_pieces(team: Dict) -> Dict:
    set_pieces = {
        'corner': team.get('xga_corner', 0) or 0,
        'free_kick': team.get('xga_free_kick', 0) or 0,
        'penalty': team.get('xga_penalty', 0) or 0,
        'open_play': team.get('xga_open_play', 0) or 0,
    }
    
    total = sum(set_pieces.values())
    sp_total = set_pieces['corner'] + set_pieces['free_kick'] + set_pieces['penalty']
    
    if total > 0:
        sp_pct = (sp_total / total) * 100
    else:
        sp_pct = 25
    
    if sp_pct > 35:
        profile = 'SET_PIECE_VULNERABLE'
    elif sp_pct < 18:
        profile = 'SET_PIECE_SOLID'
    else:
        profile = 'SET_PIECE_AVERAGE'
    
    return {
        'set_piece_data': set_pieces,
        'set_piece_pct': round(sp_pct, 1),
        'set_piece_profile': profile,
        'corner_threat': 'HIGH' if set_pieces['corner'] > 12 else 'MODERATE' if set_pieces['corner'] > 7 else 'LOW',
    }

# ═══════════════════════════════════════════════════════════════════════════════
# ZONE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_zones(team: Dict) -> Dict:
    zones = {
        'six_yard': team.get('xga_six_yard', 0) or 0,
        'penalty_area': team.get('xga_penalty_area', 0) or 0,
        'outside_box': team.get('xga_outside_box', 0) or 0,
    }
    
    total = sum(zones.values())
    
    if total > 0:
        zone_pct = {k: round(v / total * 100, 1) for k, v in zones.items()}
    else:
        zone_pct = {'six_yard': 30, 'penalty_area': 55, 'outside_box': 15}
    
    if zone_pct['six_yard'] > 35:
        profile = 'CLOSE_RANGE_VULNERABLE'
    elif zone_pct['outside_box'] > 22:
        profile = 'LONGSHOT_VULNERABLE'
    else:
        profile = 'BALANCED_ZONE'
    
    return {
        'zone_data': zones,
        'zone_pct': zone_pct,
        'zone_profile': profile,
        'most_vulnerable_zone': max(zone_pct, key=zone_pct.get),
    }

# ═══════════════════════════════════════════════════════════════════════════════
# EDGE CALCULATION V8.1 - IMPROVED THRESHOLDS
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_edge_v81(
    team: Dict,
    resistance: Dict,
    temporal: Dict,
    gamestate: Dict,
    set_pieces: Dict,
    zones: Dict,
    gk_data: Optional[Dict],
    defender_agg: Optional[Dict],
    context: Dict,
    exploit_profile: Dict
) -> Dict:
    """Edge V8.1 avec seuils améliorés et intégration exploit_paths"""
    
    edge_components = {}
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 1. RESISTANCE EDGE (principal driver) - Seuils améliorés
    # ═══════════════════════════════════════════════════════════════════════════
    rg = resistance['resistance_vector']['resist_global']
    
    if rg < 15:
        edge_components['resistance_edge'] = 10.0
    elif rg < 25:
        edge_components['resistance_edge'] = 7.0
    elif rg < 35:
        edge_components['resistance_edge'] = 4.5
    elif rg < 45:
        edge_components['resistance_edge'] = 2.0
    elif rg < 55:
        edge_components['resistance_edge'] = 0.0
    elif rg < 65:
        edge_components['resistance_edge'] = -2.0
    elif rg < 75:
        edge_components['resistance_edge'] = -4.0
    elif rg < 85:
        edge_components['resistance_edge'] = -6.0
    else:
        edge_components['resistance_edge'] = -8.0
    
    # Bonus/Malus pour vulnérabilités critiques
    num_critical = len(resistance['critical_vulnerabilities'])
    if num_critical >= 4:
        edge_components['multi_vulnerability_bonus'] = 3.0
    elif num_critical >= 2:
        edge_components['multi_vulnerability_bonus'] = 1.5
    else:
        edge_components['multi_vulnerability_bonus'] = 0.0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 2. TEMPORAL EDGE - Corrigé
    # ═══════════════════════════════════════════════════════════════════════════
    timing_profile = temporal['timing_profile']
    late_pct = temporal['late_game_pct']
    
    if timing_profile == 'LATE_COLLAPSER':
        edge_components['temporal_edge'] = 3.0
    elif timing_profile == 'SLOW_STARTER':
        edge_components['temporal_edge'] = 2.0
    elif timing_profile == 'STRONG_FINISHER':
        edge_components['temporal_edge'] = -2.0
    elif timing_profile == 'FAST_STARTER':
        edge_components['temporal_edge'] = -1.0
    else:
        edge_components['temporal_edge'] = 0.0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 3. GAMESTATE EDGE
    # ═══════════════════════════════════════════════════════════════════════════
    gs_profile = gamestate['gamestate_profile']
    
    if gs_profile == 'CANT_HOLD_LEAD':
        edge_components['gamestate_edge'] = 2.5
    elif gs_profile == 'OPENS_UP_WHEN_BEHIND':
        edge_components['gamestate_edge'] = 2.0
    elif gs_profile == 'LEVEL_VULNERABLE':
        edge_components['gamestate_edge'] = 1.0
    else:
        edge_components['gamestate_edge'] = 0.0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 4. SET PIECE EDGE
    # ═══════════════════════════════════════════════════════════════════════════
    sp_pct = set_pieces['set_piece_pct']
    
    if sp_pct > 38:
        edge_components['set_piece_edge'] = 3.0
    elif sp_pct > 30:
        edge_components['set_piece_edge'] = 1.5
    elif sp_pct < 15:
        edge_components['set_piece_edge'] = -1.5
    else:
        edge_components['set_piece_edge'] = 0.0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 5. ZONE EDGE
    # ═══════════════════════════════════════════════════════════════════════════
    zone_profile = zones['zone_profile']
    
    if zone_profile == 'CLOSE_RANGE_VULNERABLE':
        edge_components['zone_edge'] = 2.0
    elif zone_profile == 'LONGSHOT_VULNERABLE':
        edge_components['zone_edge'] = 1.5
    else:
        edge_components['zone_edge'] = 0.0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 6. GOALKEEPER EDGE - Amélioré
    # ═══════════════════════════════════════════════════════════════════════════
    if gk_data:
        gk_pct = gk_data.get('gk_percentile', 50)
        gk_overperform = gk_data.get('gk_overperform', 0)
        
        # Edge basé sur le niveau du GK
        if gk_pct < 15:
            edge_components['goalkeeper_edge'] = 4.0
        elif gk_pct < 30:
            edge_components['goalkeeper_edge'] = 2.5
        elif gk_pct < 45:
            edge_components['goalkeeper_edge'] = 1.0
        elif gk_pct > 80:
            edge_components['goalkeeper_edge'] = -3.0
        elif gk_pct > 65:
            edge_components['goalkeeper_edge'] = -1.5
        else:
            edge_components['goalkeeper_edge'] = 0.0
        
        # Régression GK
        if gk_overperform > 8:  # GK très chanceux
            edge_components['gk_regression_edge'] = 2.5
        elif gk_overperform > 4:
            edge_components['gk_regression_edge'] = 1.0
        elif gk_overperform < -8:  # GK très malchanceux
            edge_components['gk_regression_edge'] = -2.0
        elif gk_overperform < -4:
            edge_components['gk_regression_edge'] = -1.0
        else:
            edge_components['gk_regression_edge'] = 0.0
        
        # Vulnérabilités GK spécifiques
        gk_vulns = gk_data.get('vulnerabilities', [])
        if 'PERIOD_76_90_WEAK' in gk_vulns:
            edge_components['gk_timing_edge'] = 1.0
        else:
            edge_components['gk_timing_edge'] = 0.0
    else:
        edge_components['goalkeeper_edge'] = 0.0
        edge_components['gk_regression_edge'] = 0.0
        edge_components['gk_timing_edge'] = 0.0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 7. DEFENDER AGGREGATE EDGE
    # ═══════════════════════════════════════════════════════════════════════════
    if defender_agg:
        delta = defender_agg.get('defender_impact_delta', 0)
        
        if delta < -0.5:  # Défenseurs très importants
            edge_components['defender_quality_edge'] = -2.0
        elif delta > 0.5:  # Défenseurs pas importants
            edge_components['defender_quality_edge'] = 2.0
        else:
            edge_components['defender_quality_edge'] = 0.0
        
        # Risque disciplinaire
        if defender_agg.get('disciplinary_risk') == 'HIGH':
            edge_components['disciplinary_edge'] = 1.5
        elif defender_agg.get('disciplinary_risk') == 'MODERATE':
            edge_components['disciplinary_edge'] = 0.5
        else:
            edge_components['disciplinary_edge'] = 0.0
    else:
        edge_components['defender_quality_edge'] = 0.0
        edge_components['disciplinary_edge'] = 0.0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 8. REGRESSION EDGE (xGA vs GA)
    # ═══════════════════════════════════════════════════════════════════════════
    defense_overperform = team.get('defense_overperform', 0) or 0
    
    if defense_overperform > 10:
        edge_components['regression_edge'] = 4.0
    elif defense_overperform > 6:
        edge_components['regression_edge'] = 2.5
    elif defense_overperform > 3:
        edge_components['regression_edge'] = 1.0
    elif defense_overperform < -10:
        edge_components['regression_edge'] = -3.0
    elif defense_overperform < -6:
        edge_components['regression_edge'] = -2.0
    elif defense_overperform < -3:
        edge_components['regression_edge'] = -1.0
    else:
        edge_components['regression_edge'] = 0.0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 9. PERCENTILE EDGE
    # ═══════════════════════════════════════════════════════════════════════════
    percentiles = team.get('percentiles_v5_1', {}) or team.get('percentiles', {})
    if percentiles:
        xga_pct = percentiles.get('xga_per_90', 50)
        
        if xga_pct < 10:
            edge_components['percentile_edge'] = 5.0
        elif xga_pct < 20:
            edge_components['percentile_edge'] = 3.0
        elif xga_pct < 30:
            edge_components['percentile_edge'] = 1.5
        elif xga_pct > 90:
            edge_components['percentile_edge'] = -4.0
        elif xga_pct > 80:
            edge_components['percentile_edge'] = -2.5
        elif xga_pct > 70:
            edge_components['percentile_edge'] = -1.5
        else:
            edge_components['percentile_edge'] = 0.0
    else:
        edge_components['percentile_edge'] = 0.0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 10. EXPLOIT PATHS EDGE (intégration données existantes)
    # ═══════════════════════════════════════════════════════════════════════════
    exploit_paths = team.get('exploit_paths', [])
    if exploit_paths:
        num_exploits = len(exploit_paths)
        if num_exploits >= 5:
            edge_components['exploit_paths_edge'] = 2.5
        elif num_exploits >= 3:
            edge_components['exploit_paths_edge'] = 1.5
        elif num_exploits >= 1:
            edge_components['exploit_paths_edge'] = 0.5
        else:
            edge_components['exploit_paths_edge'] = 0.0
    else:
        edge_components['exploit_paths_edge'] = 0.0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 11. HOME/AWAY DIFFERENTIAL
    # ═══════════════════════════════════════════════════════════════════════════
    resist_home = resistance['resistance_vector']['resist_home']
    resist_away = resistance['resistance_vector']['resist_away']
    
    home_away_diff = resist_home - resist_away
    
    if home_away_diff > 40:  # Beaucoup plus faible à l'extérieur
        edge_components['home_away_edge'] = 2.0
    elif home_away_diff < -30:  # Plus faible à domicile (rare)
        edge_components['home_away_edge'] = 1.5
    else:
        edge_components['home_away_edge'] = 0.0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TOTAL EDGE
    # ═══════════════════════════════════════════════════════════════════════════
    total_edge = sum(edge_components.values())
    
    # Classification
    if total_edge >= 18:
        classification = 'EXTREME_VALUE'
        kelly_mult = 1.0
    elif total_edge >= 12:
        classification = 'HIGH_VALUE'
        kelly_mult = 0.75
    elif total_edge >= 7:
        classification = 'MODERATE_VALUE'
        kelly_mult = 0.5
    elif total_edge >= 3:
        classification = 'SLIGHT_VALUE'
        kelly_mult = 0.25
    elif total_edge >= -3:
        classification = 'NO_VALUE'
        kelly_mult = 0.0
    elif total_edge >= -8:
        classification = 'NEGATIVE_VALUE'
        kelly_mult = 0.0
    else:
        classification = 'STRONG_NEGATIVE'
        kelly_mult = 0.0
    
    kelly_stake = min(5.0, max(0.0, total_edge * kelly_mult * 0.25))
    confidence = min(100, max(0, 50 + total_edge * 2.5))
    
    # Top 3 drivers
    sorted_components = sorted(edge_components.items(), key=lambda x: abs(x[1]), reverse=True)
    top_drivers = [(k, v) for k, v in sorted_components[:3] if v != 0]
    
    return {
        'edge_components': edge_components,
        'total_edge': round(total_edge, 2),
        'edge_classification': classification,
        'kelly_stake': round(kelly_stake, 2),
        'confidence_score': round(confidence, 1),
        'top_3_drivers': top_drivers,
        'num_positive_factors': sum(1 for v in edge_components.values() if v > 0),
        'num_negative_factors': sum(1 for v in edge_components.values() if v < 0),
    }

# ═══════════════════════════════════════════════════════════════════════════════
# DNA SIGNATURE
# ═══════════════════════════════════════════════════════════════════════════════

def generate_signature(team_name: str, edge: Dict, resistance: Dict, temporal: Dict, gk_data: Optional[Dict]) -> str:
    parts = []
    
    # Classification (3 chars)
    parts.append(edge['edge_classification'][:3])
    
    # Resist profile
    parts.append(resistance['resist_profile'][:4])
    
    # Timing
    parts.append(temporal['timing_profile'][:4])
    
    # GK
    if gk_data:
        gk_pct = gk_data.get('gk_percentile', 50)
        if gk_pct < 30:
            parts.append('GK-')
        elif gk_pct > 70:
            parts.append('GK+')
        else:
            parts.append('GK=')
    else:
        parts.append('GK?')
    
    # Edge
    edge_val = edge['total_edge']
    parts.append(f"E{edge_val:+.0f}")
    
    return '|'.join(parts)

# ═══════════════════════════════════════════════════════════════════════════════
# BETTING RECOMMENDATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def generate_recommendations(edge: Dict, temporal: Dict, gk_data: Optional[Dict], set_pieces: Dict) -> Dict:
    recs = {
        'goals_over': [],
        'goals_under': [],
        'timing': [],
        'avoid': [],
    }
    
    total_edge = edge['total_edge']
    
    if total_edge >= 12:
        recs['goals_over'].append({'market': 'Team Goals O1.5', 'confidence': 'HIGH', 'edge': f"+{total_edge:.1f}%"})
    elif total_edge >= 7:
        recs['goals_over'].append({'market': 'Team Goals O0.5', 'confidence': 'MODERATE', 'edge': f"+{total_edge:.1f}%"})
    elif total_edge <= -8:
        recs['goals_under'].append({'market': 'Team Clean Sheet', 'confidence': 'HIGH', 'edge': f"{total_edge:.1f}%"})
    elif total_edge <= -5:
        recs['goals_under'].append({'market': 'Team Goals U1.5', 'confidence': 'MODERATE', 'edge': f"{total_edge:.1f}%"})
    
    # Timing
    if temporal['timing_profile'] == 'LATE_COLLAPSER':
        recs['timing'].append({'market': 'Goal 61-90', 'confidence': 'HIGH', 'reason': f"Late collapser ({temporal['late_game_pct']:.1f}%)"})
    elif temporal['timing_profile'] == 'SLOW_STARTER':
        recs['timing'].append({'market': 'Goal 0-30', 'confidence': 'MODERATE', 'reason': f"Slow starter ({temporal['early_game_pct']:.1f}%)"})
    
    # GK timing
    if gk_data and 'PERIOD_76_90_WEAK' in gk_data.get('vulnerabilities', []):
        recs['timing'].append({'market': 'Last Goalscorer', 'confidence': 'HIGH', 'reason': 'GK vulnérable fin de match'})
    
    return recs

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_team(team: Dict, gk_index: Dict, defender_agg: Dict, context_data: Dict, exploit_data: Dict) -> Dict:
    team_name = team.get('team_name', 'Unknown')
    normalized = normalize_team_name(team_name)
    
    # Get auxiliary data
    gk_data = gk_index.get(normalized)
    def_agg = defender_agg.get(normalized)
    context = extract_context_insights(context_data, team_name) if context_data else {}
    exploit = extract_exploit_profile(exploit_data, team_name) if exploit_data else {}
    
    # Run analyses
    resistance = analyze_resistance(team)
    temporal = analyze_temporal_fixed(team)
    gamestate = analyze_gamestate(team)
    set_pieces = analyze_set_pieces(team)
    zones = analyze_zones(team)
    
    # Calculate edge
    edge = calculate_edge_v81(team, resistance, temporal, gamestate, set_pieces, zones, gk_data, def_agg, context, exploit)
    
    # Generate recommendations
    recommendations = generate_recommendations(edge, temporal, gk_data, set_pieces)
    
    # Generate signature
    signature = generate_signature(team_name, edge, resistance, temporal, gk_data)
    
    return {
        'team_name': team_name,
        'league': team.get('league', 'Unknown'),
        'season': team.get('season', '2025/2026'),
        
        'foundation': {
            'matches_played': team.get('matches_played', 0),
            'xga_per_90': round(team.get('xga_per_90', 0) or 0, 3),
            'ga_per_90': round(team.get('ga_per_90', 0) or 0, 3),
            'cs_pct': round(team.get('cs_pct', 0) or 0, 1),
            'defense_overperform': round(team.get('defense_overperform', 0) or 0, 2),
        },
        
        'resistance': resistance,
        'temporal': temporal,
        'gamestate': gamestate,
        'set_pieces': set_pieces,
        'zones': zones,
        
        'goalkeeper': gk_data if gk_data else {'status': 'NO_DATA'},
        'defenders': def_agg if def_agg else {'status': 'NO_DATA'},
        
        'edge': edge,
        'recommendations': recommendations,
        'dna_signature': signature,
        
        'existing_exploits': team.get('exploit_paths', []),
        'existing_betting_insights': team.get('betting_insights', {}),
        
        'analysis_version': 'V8.1_HEDGE_FUND_GRADE_3.1',
        'timestamp': datetime.now().isoformat(),
    }

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("═" * 70)
    print("🏦 DEFENSIVE LINES V8.1 - HEDGE FUND GRADE 3.1 IMPROVED")
    print("═" * 70)
    
    sources = load_all_sources()
    
    if 'team_defense' not in sources:
        print("❌ ERREUR: team_defense non disponible")
        return
    
    team_defense = sources['team_defense']
    
    # Prepare indexes
    print("\n" + "═" * 70)
    print("🔄 PRÉPARATION")
    print("═" * 70)
    
    gk_index = create_goalkeeper_index(sources.get('goalkeeper', [])) if sources.get('goalkeeper') else {}
    print(f"✅ GK Index: {len(gk_index)} équipes")
    
    defender_agg = aggregate_defenders_by_team(sources.get('defenders', [])) if sources.get('defenders') else {}
    print(f"✅ Defender Agg: {len(defender_agg)} équipes")
    
    context_data = sources.get('context_dna', {})
    exploit_data = sources.get('team_exploit', {})
    
    # Analyze
    print("\n" + "═" * 70)
    print("📊 ANALYSE")
    print("═" * 70)
    
    results = []
    for team in team_defense:
        result = analyze_team(team, gk_index, defender_agg, context_data, exploit_data)
        results.append(result)
        
        edge = result['edge']['total_edge']
        classif = result['edge']['edge_classification']
        timing = result['temporal']['timing_profile']
        print(f"  {result['team_name']:25} | Edge: {edge:+6.1f}% | {classif:15} | {timing}")
    
    # Sort
    results.sort(key=lambda x: x['edge']['total_edge'], reverse=True)
    
    # Save
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Sauvegardé: {OUTPUT_PATH}")
    
    # Summary
    print("\n" + "═" * 70)
    print("📈 TOP 10 GOALS OVER VALUE")
    print("═" * 70)
    for i, t in enumerate(results[:10], 1):
        print(f"{i:2}. {t['team_name']:25} | {t['edge']['total_edge']:+6.1f}% | Kelly: {t['edge']['kelly_stake']:.1f}% | {t['dna_signature']}")
    
    print("\n" + "═" * 70)
    print("📉 TOP 10 GOALS UNDER / CS VALUE")
    print("═" * 70)
    for i, t in enumerate(results[-10:][::-1], 1):
        print(f"{i:2}. {t['team_name']:25} | {t['edge']['total_edge']:+6.1f}% | Kelly: {t['edge']['kelly_stake']:.1f}% | {t['dna_signature']}")
    
    # Stats
    edges = [r['edge']['total_edge'] for r in results]
    print("\n" + "═" * 70)
    print("📊 STATISTIQUES")
    print("═" * 70)
    print(f"Total: {len(results)} équipes")
    print(f"Edge moyen: {statistics.mean(edges):+.1f}%")
    print(f"Edge médian: {statistics.median(edges):+.1f}%")
    print(f"Min/Max: {min(edges):+.1f}% / {max(edges):+.1f}%")
    
    extreme = sum(1 for e in edges if e >= 18)
    high = sum(1 for e in edges if 12 <= e < 18)
    moderate = sum(1 for e in edges if 7 <= e < 12)
    slight = sum(1 for e in edges if 3 <= e < 7)
    no_val = sum(1 for e in edges if -3 <= e < 3)
    negative = sum(1 for e in edges if e < -3)
    
    print(f"\nEXTREME_VALUE (≥18%): {extreme} ({extreme/len(results)*100:.1f}%)")
    print(f"HIGH_VALUE (12-18%): {high} ({high/len(results)*100:.1f}%)")
    print(f"MODERATE (7-12%): {moderate} ({moderate/len(results)*100:.1f}%)")
    print(f"SLIGHT (3-7%): {slight} ({slight/len(results)*100:.1f}%)")
    print(f"NO_VALUE (-3 to 3%): {no_val} ({no_val/len(results)*100:.1f}%)")
    print(f"NEGATIVE (<-3%): {negative} ({negative/len(results)*100:.1f}%)")
    
    # Timing distribution
    timing_dist = defaultdict(int)
    for r in results:
        timing_dist[r['temporal']['timing_profile']] += 1
    
    print("\n📊 DISTRIBUTION TIMING PROFILES:")
    for profile, count in sorted(timing_dist.items(), key=lambda x: -x[1]):
        print(f"  {profile:20}: {count} ({count/len(results)*100:.1f}%)")
    
    print("\n" + "═" * 70)
    print("✅ ANALYSE V8.1 TERMINÉE")
    print("═" * 70)

if __name__ == '__main__':
    main()
