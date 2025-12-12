#!/usr/bin/env python3
"""
Calcul des shooter_profiles depuis all_shots_against_2025.json
Génère timing_profile, zone_profile, shot_type_profile pour chaque tireur
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Chemins des fichiers
INPUT_FILE = '/home/Mon_ps/data/goalkeeper_dna/all_shots_against_2025.json'
OUTPUT_FILE = '/home/Mon_ps/data/quantum_v2/shooter_profiles_calculated.json'

# ============================================================================
# CONSTANTES - ZONES ET PÉRIODES
# ============================================================================

PERIODS = ['0-15', '16-30', '31-45', '46-60', '61-75', '76-90', '90+']
PERIOD_RANGES = {
    '0-15': (0, 15),
    '16-30': (16, 30),
    '31-45': (31, 45),
    '46-60': (46, 60),
    '61-75': (61, 75),
    '76-90': (76, 90),
    '90+': (90, 999)
}

# Zones X (profondeur) - X normalisé 0-1, 1 = ligne de but
ZONE_X = {
    'six_yard': 0.94,      # X > 0.94
    'inside_box': 0.83,    # X > 0.83
    'outside_box': 0.83    # X <= 0.83
}

# Zones Y (largeur) - Y normalisé 0-1, 0.5 = centre
ZONE_Y = {
    'wide_left': 0.37,     # Y < 0.37
    'central_min': 0.37,   # Y >= 0.37 et Y <= 0.63
    'central_max': 0.63,
    'wide_right': 0.63     # Y > 0.63
}

# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def get_period(minute: int) -> str:
    """Retourne la période correspondant à la minute"""
    if minute <= 15:
        return '0-15'
    elif minute <= 30:
        return '16-30'
    elif minute <= 45:
        return '31-45'
    elif minute <= 60:
        return '46-60'
    elif minute <= 75:
        return '61-75'
    elif minute <= 90:
        return '76-90'
    else:
        return '90+'


def get_zone_x(x: float) -> str:
    """Retourne la zone de profondeur"""
    if x > ZONE_X['six_yard']:
        return 'six_yard'
    elif x > ZONE_X['inside_box']:
        return 'inside_box'
    else:
        return 'outside_box'


def get_zone_y(y: float) -> str:
    """Retourne la zone de largeur"""
    if y < ZONE_Y['wide_left']:
        return 'wide_left'
    elif y > ZONE_Y['wide_right']:
        return 'wide_right'
    else:
        return 'central'


def calculate_conversion(goals: int, shots: int) -> float:
    """Calcule le taux de conversion"""
    if shots == 0:
        return 0.0
    return round((goals / shots) * 100, 1)


def calculate_xg_diff(goals: int, xg: float) -> float:
    """Calcule la différence goals - xG"""
    return round(goals - xg, 2)


def safe_float(value, default=0.0) -> float:
    """Convertit une valeur en float de manière sécurisée"""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def calculate_confidence(sample: int) -> str:
    """Calcule le niveau de confiance basé sur l'échantillon (global)"""
    if sample >= 30:
        return 'HIGH'
    elif sample >= 15:
        return 'MEDIUM'
    elif sample >= 5:
        return 'LOW'
    else:
        return 'VERY_LOW'


def get_sample_confidence(shots: int) -> str:
    """Calcule le niveau de confiance pour une période (plus granulaire)"""
    if shots < 3:
        return "VERY_LOW"
    elif shots < 5:
        return "LOW"
    elif shots < 10:
        return "MEDIUM"
    elif shots < 20:
        return "HIGH"
    else:
        return "VERY_HIGH"


# ============================================================================
# MAPPINGS STRENGTH/WEAKNESS → MARKETS (HEDGE FUND GRADE)
# ============================================================================

STRENGTH_MAPPING = {
    "clutch_scorer": {
        "markets": ["last_scorer", "anytime_scorer"],
        "edge_type": "direct_positive",
        "edge_mechanism": "timing_overperformance_late",
        "description": "Sur-performe en fin de match (76-90+)"
    },
    "fast_starter": {
        "markets": ["first_scorer", "anytime_scorer"],
        "edge_type": "direct_positive",
        "edge_mechanism": "timing_overperformance_early",
        "description": "Sur-performe en début de match (0-15)"
    },
    "aerial_threat": {
        "markets": ["header_goal", "anytime_scorer"],
        "edge_type": "direct_positive",
        "edge_mechanism": "shot_type_specialty",
        "collision_boost": "vs_weak_aerial_defense",
        "description": "Dangereux de la tête (conversion >15%)"
    },
    "box_predator": {
        "markets": ["anytime_scorer"],
        "edge_type": "direct_positive",
        "edge_mechanism": "zone_specialty",
        "description": "Finisseur de surface (>80% tirs inside box)"
    },
    "long_range_threat": {
        "markets": ["anytime_scorer", "outside_box_goal"],
        "edge_type": "direct_positive",
        "edge_mechanism": "zone_specialty",
        "collision_boost": "vs_deep_block_defense",
        "description": "Dangereux de loin (conversion outside box >10%)"
    },
    "clinical_finisher": {
        "markets": ["anytime_scorer"],
        "edge_type": "direct_positive",
        "edge_mechanism": "conversion_overperformance",
        "description": "Conversion élevée (>25% ou xG_diff > +2)"
    },
    "set_piece_specialist": {
        "markets": ["anytime_scorer", "first_scorer"],
        "edge_type": "direct_positive",
        "edge_mechanism": "situation_specialty",
        "collision_boost": "vs_weak_set_piece_defense",
        "description": "Dangereux sur coups de pied arrêtés"
    },
    "second_half_specialist": {
        "markets": ["anytime_scorer"],
        "edge_type": "direct_positive",
        "edge_mechanism": "timing_pattern",
        "description": "Meilleur en 2ème mi-temps"
    },
    "first_half_specialist": {
        "markets": ["anytime_scorer", "first_scorer"],
        "edge_type": "direct_positive",
        "edge_mechanism": "timing_pattern",
        "description": "Meilleur en 1ère mi-temps"
    },
    "prolific_scorer": {
        "markets": ["anytime_scorer", "2+_goals"],
        "edge_type": "direct_positive",
        "edge_mechanism": "volume_performance",
        "description": "Volume élevé de buts (15+ buts)"
    },
    "reliable_scorer": {
        "markets": ["anytime_scorer"],
        "edge_type": "direct_positive",
        "edge_mechanism": "volume_performance",
        "description": "Volume solide de buts (10-14 buts)"
    },
    "penalty_specialist": {
        "markets": ["anytime_scorer", "penalty_scored"],
        "edge_type": "direct_positive",
        "edge_mechanism": "situation_specialty",
        "description": "Tireur de penalty fiable (>75% conversion)"
    },
    "two_footed": {
        "markets": ["anytime_scorer", "penalty_scored"],
        "edge_type": "indirect_positive",
        "edge_mechanism": "unpredictability_vs_goalkeeper",
        "collision_boost": "vs_predictable_diving_gk",
        "description": "Peut marquer des deux pieds - imprévisible pour le gardien"
    },
    "willing_shooter": {
        "markets": ["anytime_scorer", "shots_on_target"],
        "edge_type": "indirect_positive",
        "edge_mechanism": "volume_probability",
        "collision_boost": "vs_high_possession_opponent",
        "description": "Volume élevé de tirs - plus d'opportunités de marquer"
    },
    "poacher": {
        "markets": ["anytime_scorer"],
        "edge_type": "direct_positive",
        "edge_mechanism": "zone_specialty",
        "collision_boost": "vs_high_cross_team",
        "description": "Spécialiste six yards (conversion >50% zone)"
    }
}

WEAKNESS_MAPPING = {
    "slow_starter": {
        "markets": ["first_scorer"],
        "edge_type": "direct_negative",
        "edge_mechanism": "timing_underperformance_early",
        "description": "Sous-performe en début de match (0-15)"
    },
    "clutch_fader": {
        "markets": ["last_scorer"],
        "edge_type": "direct_negative",
        "edge_mechanism": "timing_underperformance_late",
        "description": "Sous-performe en fin de match (76-90+)"
    },
    "weak_header": {
        "markets": ["header_goal"],
        "edge_type": "direct_negative",
        "edge_mechanism": "shot_type_weakness",
        "description": "Mauvais de la tête (conversion <=8%)"
    },
    "wasteful": {
        "markets": ["anytime_scorer"],
        "edge_type": "direct_negative",
        "edge_mechanism": "conversion_underperformance",
        "description": "Sous-performe son xG (xG_diff < -2)"
    },
    "one_footed": {
        "markets": ["anytime_scorer"],
        "edge_type": "indirect_negative",
        "edge_mechanism": "predictability_for_goalkeeper",
        "collision_boost": "vs_analytical_goalkeeper",
        "description": "Prévisible - tire presque toujours du même pied"
    }
}


def confidence_to_float(conf: str) -> float:
    """Convertit confidence en float"""
    return {'HIGH': 0.8, 'MEDIUM': 0.6, 'LOW': 0.4, 'VERY_LOW': 0.2}.get(conf, 0.5)


# ============================================================================
# ANALYSE DES TIRS PAR JOUEUR
# ============================================================================

def collect_player_shots(data: Dict) -> Dict[str, List[Dict]]:
    """
    Collecte tous les tirs par joueur depuis la structure par équipe
    """
    player_shots = defaultdict(list)

    for team, shots in data.items():
        if not isinstance(shots, list):
            continue
        for shot in shots:
            player_name = shot.get('player')
            player_id = shot.get('player_id')
            if player_name:
                # Clé unique: player_name (on garde player_id dans le shot)
                player_shots[player_name].append(shot)

    return player_shots


def analyze_timing(shots: List[Dict]) -> Dict[str, Any]:
    """
    Analyse timing: goals par période, clutch_factor, early_threat
    """
    periods_data = {p: {'shots': 0, 'goals': 0, 'xG': 0.0} for p in PERIODS}

    for shot in shots:
        minute_raw = shot.get('minute', 0)
        try:
            minute = int(float(str(minute_raw))) if minute_raw else 0
        except (ValueError, TypeError):
            minute = 0
        result = shot.get('result', '')
        xg = safe_float(shot.get('xG', 0))

        period = get_period(minute)
        periods_data[period]['shots'] += 1
        periods_data[period]['xG'] += xg
        if result == 'Goal':
            periods_data[period]['goals'] += 1

    # Calcul des métriques par période
    periods_analysis = {}
    for period, data in periods_data.items():
        shots_count = data['shots']
        goals_count = data['goals']
        xg_total = data['xG']

        periods_analysis[period] = {
            'shots': shots_count,
            'goals': goals_count,
            'xG': round(xg_total, 2),
            'conversion': calculate_conversion(goals_count, shots_count),
            'xG_diff': calculate_xg_diff(goals_count, xg_total),
            'confidence': get_sample_confidence(shots_count)
        }

    # Calcul 1ère vs 2ème mi-temps
    first_half = sum(periods_data[p]['goals'] for p in ['0-15', '16-30', '31-45'])
    second_half = sum(periods_data[p]['goals'] for p in ['46-60', '61-75', '76-90', '90+'])
    first_half_shots = sum(periods_data[p]['shots'] for p in ['0-15', '16-30', '31-45'])
    second_half_shots = sum(periods_data[p]['shots'] for p in ['46-60', '61-75', '76-90', '90+'])

    # Clutch factor: performance 76-90+ vs moyenne
    late_goals = periods_data['76-90']['goals'] + periods_data['90+']['goals']
    late_shots = periods_data['76-90']['shots'] + periods_data['90+']['shots']
    late_xg = periods_data['76-90']['xG'] + periods_data['90+']['xG']

    total_goals = sum(d['goals'] for d in periods_data.values())
    total_shots = sum(d['shots'] for d in periods_data.values())

    avg_conversion = calculate_conversion(total_goals, total_shots)
    late_conversion = calculate_conversion(late_goals, late_shots)

    clutch_factor = round(late_conversion - avg_conversion, 1) if late_shots >= 3 else 0.0

    # Early threat: performance 0-15
    early_goals = periods_data['0-15']['goals']
    early_shots = periods_data['0-15']['shots']
    early_conversion = calculate_conversion(early_goals, early_shots)
    early_threat = round(early_conversion - avg_conversion, 1) if early_shots >= 3 else 0.0

    # Déterminer pattern
    if abs(clutch_factor) > 10:
        pattern = 'CLUTCH_PERFORMER' if clutch_factor > 0 else 'CLUTCH_FADER'
    elif abs(early_threat) > 10:
        pattern = 'FAST_STARTER' if early_threat > 0 else 'SLOW_STARTER'
    elif first_half > second_half * 1.5:
        pattern = 'FIRST_HALF_SPECIALIST'
    elif second_half > first_half * 1.5:
        pattern = 'SECOND_HALF_SPECIALIST'
    else:
        pattern = 'CONSISTENT'

    # Weakest/Strongest period
    goal_periods = [(p, d['goals']) for p, d in periods_analysis.items() if d['shots'] >= 3]
    if goal_periods:
        strongest_period = max(goal_periods, key=lambda x: x[1])[0]
        weakest_period = min(goal_periods, key=lambda x: x[1])[0]
    else:
        strongest_period = ''
        weakest_period = ''

    return {
        'periods': periods_analysis,
        'first_half_goals': first_half,
        'second_half_goals': second_half,
        'first_half_shots': first_half_shots,
        'second_half_shots': second_half_shots,
        'first_half_conversion': calculate_conversion(first_half, first_half_shots),
        'second_half_conversion': calculate_conversion(second_half, second_half_shots),
        'clutch_factor': clutch_factor,
        'early_threat': early_threat,
        'pattern': pattern,
        'strongest_period': strongest_period,
        'weakest_period': weakest_period,
        'late_goals': late_goals,
        'late_xG_diff': calculate_xg_diff(late_goals, late_xg)
    }


def analyze_zones(shots: List[Dict]) -> Dict[str, Any]:
    """
    Analyse zones: inside_box, outside_box, six_yard, central, wide
    """
    zones_x = {'six_yard': {'shots': 0, 'goals': 0, 'xG': 0.0},
               'inside_box': {'shots': 0, 'goals': 0, 'xG': 0.0},
               'outside_box': {'shots': 0, 'goals': 0, 'xG': 0.0}}

    zones_y = {'central': {'shots': 0, 'goals': 0, 'xG': 0.0},
               'wide_left': {'shots': 0, 'goals': 0, 'xG': 0.0},
               'wide_right': {'shots': 0, 'goals': 0, 'xG': 0.0}}

    for shot in shots:
        x = safe_float(shot.get('X', 0))
        y = safe_float(shot.get('Y', 0))
        result = shot.get('result', '')
        xg = safe_float(shot.get('xG', 0))
        is_goal = 1 if result == 'Goal' else 0

        # Zone X
        zone_x = get_zone_x(x)
        zones_x[zone_x]['shots'] += 1
        zones_x[zone_x]['goals'] += is_goal
        zones_x[zone_x]['xG'] += xg

        # Zone Y
        zone_y = get_zone_y(y)
        zones_y[zone_y]['shots'] += 1
        zones_y[zone_y]['goals'] += is_goal
        zones_y[zone_y]['xG'] += xg

    # Calcul métriques zones X
    zones_x_analysis = {}
    for zone, data in zones_x.items():
        zones_x_analysis[zone] = {
            'shots': data['shots'],
            'goals': data['goals'],
            'xG': round(data['xG'], 2),
            'conversion': calculate_conversion(data['goals'], data['shots']),
            'xG_diff': calculate_xg_diff(data['goals'], data['xG']),
            'confidence': calculate_confidence(data['shots']),
            'pct_of_total': 0  # calculé après
        }

    total_shots = sum(d['shots'] for d in zones_x.values())
    for zone in zones_x_analysis:
        if total_shots > 0:
            zones_x_analysis[zone]['pct_of_total'] = round(
                (zones_x_analysis[zone]['shots'] / total_shots) * 100, 1
            )

    # Calcul métriques zones Y
    zones_y_analysis = {}
    for zone, data in zones_y.items():
        zones_y_analysis[zone] = {
            'shots': data['shots'],
            'goals': data['goals'],
            'xG': round(data['xG'], 2),
            'conversion': calculate_conversion(data['goals'], data['shots']),
            'xG_diff': calculate_xg_diff(data['goals'], data['xG']),
            'confidence': calculate_confidence(data['shots']),
            'pct_of_total': 0
        }

    for zone in zones_y_analysis:
        if total_shots > 0:
            zones_y_analysis[zone]['pct_of_total'] = round(
                (zones_y_analysis[zone]['shots'] / total_shots) * 100, 1
            )

    # Déterminer profil dominant
    dominant_zone_x = max(zones_x_analysis.items(),
                          key=lambda x: x[1]['goals'])[0] if total_shots > 0 else 'inside_box'
    dominant_zone_y = max(zones_y_analysis.items(),
                          key=lambda x: x[1]['goals'])[0] if total_shots > 0 else 'central'

    # Ratios
    inside_box_total = zones_x['inside_box']['shots'] + zones_x['six_yard']['shots']
    inside_box_ratio = round(inside_box_total / total_shots * 100, 1) if total_shots > 0 else 0

    return {
        'depth_zones': zones_x_analysis,
        'width_zones': zones_y_analysis,
        'dominant_depth': dominant_zone_x,
        'dominant_width': dominant_zone_y,
        'inside_box_ratio': inside_box_ratio,
        'outside_box_ratio': round(100 - inside_box_ratio, 1),
        'total_shots': total_shots
    }


def analyze_shot_types(shots: List[Dict]) -> Dict[str, Any]:
    """
    Analyse shot types: RightFoot, LeftFoot, Head
    """
    types_data = {'RightFoot': {'shots': 0, 'goals': 0, 'xG': 0.0},
                  'LeftFoot': {'shots': 0, 'goals': 0, 'xG': 0.0},
                  'Head': {'shots': 0, 'goals': 0, 'xG': 0.0},
                  'Other': {'shots': 0, 'goals': 0, 'xG': 0.0}}

    for shot in shots:
        shot_type = shot.get('shotType', 'Other')
        result = shot.get('result', '')
        xg = safe_float(shot.get('xG', 0))
        is_goal = 1 if result == 'Goal' else 0

        if shot_type not in types_data:
            shot_type = 'Other'

        types_data[shot_type]['shots'] += 1
        types_data[shot_type]['goals'] += is_goal
        types_data[shot_type]['xG'] += xg

    # Calcul métriques
    types_analysis = {}
    total_shots = sum(d['shots'] for d in types_data.values())

    for stype, data in types_data.items():
        if data['shots'] > 0:
            types_analysis[stype] = {
                'shots': data['shots'],
                'goals': data['goals'],
                'xG': round(data['xG'], 2),
                'conversion': calculate_conversion(data['goals'], data['shots']),
                'xG_diff': calculate_xg_diff(data['goals'], data['xG']),
                'confidence': calculate_confidence(data['shots']),
                'pct_of_total': round((data['shots'] / total_shots) * 100, 1) if total_shots > 0 else 0
            }

    # Pied dominant
    rf = types_data['RightFoot']['shots']
    lf = types_data['LeftFoot']['shots']

    if rf > 0 or lf > 0:
        if rf > lf * 2:
            dominant_foot = 'RIGHT_FOOTED'
        elif lf > rf * 2:
            dominant_foot = 'LEFT_FOOTED'
        else:
            dominant_foot = 'TWO_FOOTED'
    else:
        dominant_foot = 'UNKNOWN'

    # Header threat (seuils: HIGH >15%, MEDIUM >8%, LOW <=8%)
    head_data = types_data['Head']
    header_conversion = calculate_conversion(head_data['goals'], head_data['shots'])
    header_threat = 'HIGH' if header_conversion > 15 and head_data['shots'] >= 5 else \
                    'MEDIUM' if header_conversion > 8 else 'LOW'

    return {
        'by_type': types_analysis,
        'dominant_foot': dominant_foot,
        'header_threat': header_threat,
        'header_ratio': round((head_data['shots'] / total_shots * 100), 1) if total_shots > 0 else 0
    }


def analyze_situations(shots: List[Dict]) -> Dict[str, Any]:
    """
    Analyse situations: OpenPlay, FromCorner, SetPiece, Penalty, DirectFreekick
    """
    situations_data = {
        'OpenPlay': {'shots': 0, 'goals': 0, 'xG': 0.0},
        'FromCorner': {'shots': 0, 'goals': 0, 'xG': 0.0},
        'SetPiece': {'shots': 0, 'goals': 0, 'xG': 0.0},
        'Penalty': {'shots': 0, 'goals': 0, 'xG': 0.0},
        'DirectFreekick': {'shots': 0, 'goals': 0, 'xG': 0.0}
    }

    for shot in shots:
        situation = shot.get('situation', 'OpenPlay')
        result = shot.get('result', '')
        xg = safe_float(shot.get('xG', 0))
        is_goal = 1 if result == 'Goal' else 0

        if situation not in situations_data:
            situation = 'OpenPlay'

        situations_data[situation]['shots'] += 1
        situations_data[situation]['goals'] += is_goal
        situations_data[situation]['xG'] += xg

    # Calcul métriques
    situations_analysis = {}
    total_shots = sum(d['shots'] for d in situations_data.values())

    for sit, data in situations_data.items():
        if data['shots'] > 0:
            situations_analysis[sit] = {
                'shots': data['shots'],
                'goals': data['goals'],
                'xG': round(data['xG'], 2),
                'conversion': calculate_conversion(data['goals'], data['shots']),
                'xG_diff': calculate_xg_diff(data['goals'], data['xG']),
                'confidence': calculate_confidence(data['shots']),
                'pct_of_total': round((data['shots'] / total_shots) * 100, 1) if total_shots > 0 else 0
            }

    # Set piece specialist?
    set_piece_shots = situations_data['FromCorner']['shots'] + situations_data['SetPiece']['shots']
    set_piece_goals = situations_data['FromCorner']['goals'] + situations_data['SetPiece']['goals']
    set_piece_specialist = set_piece_shots >= 5 and calculate_conversion(set_piece_goals, set_piece_shots) > 15

    # Penalty specialist?
    pen_data = situations_data['Penalty']
    penalty_specialist = pen_data['shots'] >= 3 and calculate_conversion(pen_data['goals'], pen_data['shots']) > 75

    return {
        'by_situation': situations_analysis,
        'set_piece_specialist': set_piece_specialist,
        'penalty_specialist': penalty_specialist,
        'open_play_ratio': round((situations_data['OpenPlay']['shots'] / total_shots * 100), 1) if total_shots > 0 else 0
    }


# ============================================================================
# GÉNÉRATION DES FORCES/FAIBLESSES ET BETTING HINTS
# ============================================================================

def enrich_trait(trait: str, is_strength: bool) -> dict:
    """Enrichit un trait avec son mapping market complet"""
    mapping = STRENGTH_MAPPING if is_strength else WEAKNESS_MAPPING
    if trait in mapping:
        return {
            "trait": trait,
            **mapping[trait]
        }
    else:
        # Trait non mappé - garder basique
        return {
            "trait": trait,
            "markets": ["anytime_scorer"],
            "edge_type": "unknown",
            "edge_mechanism": "not_mapped",
            "description": f"Trait {trait} non mappé"
        }


def generate_strengths_weaknesses(timing: Dict, zones: Dict, shot_types: Dict,
                                   situations: Dict, total_goals: int,
                                   total_shots: int, xg_diff: float) -> tuple:
    """
    Génère automatiquement les forces et faiblesses basées sur l'analyse
    Retourne des objets enrichis avec mapping market
    """
    strengths = []
    weaknesses = []

    # Timing-based (avec sample_size minimum de 5 tirs pour fiabilité)
    late_shots = timing['periods']['76-90']['shots'] + timing['periods']['90+']['shots']
    early_shots = timing['periods']['0-15']['shots']

    # Clutch: seulement si 5+ tirs tardifs
    if late_shots >= 5:
        if timing['clutch_factor'] > 10:
            strengths.append('clutch_scorer')
        elif timing['clutch_factor'] < -10:
            weaknesses.append('clutch_fader')

    # Early threat: seulement si 5+ tirs précoces
    if early_shots >= 5:
        if timing['early_threat'] > 10:
            strengths.append('fast_starter')
        elif timing['early_threat'] < -10:
            weaknesses.append('slow_starter')

    if timing['pattern'] == 'SECOND_HALF_SPECIALIST':
        strengths.append('second_half_specialist')
    elif timing['pattern'] == 'FIRST_HALF_SPECIALIST':
        strengths.append('first_half_specialist')

    # Zone-based
    if zones['depth_zones'].get('outside_box', {}).get('conversion', 0) > 10:
        strengths.append('long_range_threat')

    if zones['depth_zones'].get('six_yard', {}).get('conversion', 0) > 50:
        strengths.append('poacher')

    if zones['inside_box_ratio'] > 80:
        strengths.append('box_predator')
    elif zones['outside_box_ratio'] > 40:
        strengths.append('willing_shooter')

    # Shot type based
    if shot_types['dominant_foot'] == 'TWO_FOOTED':
        strengths.append('two_footed')
    elif shot_types['dominant_foot'] in ['RIGHT_FOOTED', 'LEFT_FOOTED']:
        # Vérifier si vraiment one_footed (>85% d'un pied)
        rf = shot_types.get('by_type', {}).get('RightFoot', {}).get('shots', 0)
        lf = shot_types.get('by_type', {}).get('LeftFoot', {}).get('shots', 0)
        total_foot = rf + lf
        if total_foot >= 10:
            max_foot = max(rf, lf)
            if max_foot / total_foot > 0.85:
                weaknesses.append('one_footed')

    if shot_types['header_threat'] == 'HIGH':
        strengths.append('aerial_threat')
    elif shot_types['header_threat'] == 'LOW' and shot_types.get('by_type', {}).get('Head', {}).get('shots', 0) >= 5:
        weaknesses.append('weak_header')

    # Situation based
    if situations['set_piece_specialist']:
        strengths.append('set_piece_specialist')

    if situations['penalty_specialist']:
        strengths.append('penalty_specialist')

    # Volume-based
    if total_goals >= 15:
        strengths.append('prolific_scorer')
    elif total_goals >= 10:
        strengths.append('reliable_scorer')

    # Conversion-based (clinical_finisher / wasteful)
    conversion = (total_goals / total_shots * 100) if total_shots > 0 else 0
    if total_shots >= 10:
        if conversion > 25 or xg_diff > 2:
            strengths.append('clinical_finisher')
        elif xg_diff < -2:
            weaknesses.append('wasteful')

    # Enrichir les traits avec les mappings
    enriched_strengths = [enrich_trait(s, True) for s in strengths]
    enriched_weaknesses = [enrich_trait(w, False) for w in weaknesses]

    return enriched_strengths, enriched_weaknesses


def has_trait(traits: List[Dict], trait_name: str) -> bool:
    """Vérifie si un trait est présent dans une liste de traits enrichis"""
    return any(t.get('trait') == trait_name for t in traits)


def generate_betting_hints(timing: Dict, zones: Dict, shot_types: Dict,
                           situations: Dict, strengths: List, weaknesses: List) -> Dict:
    """
    Génère les hints de paris basés sur l'analyse complète
    strengths/weaknesses sont maintenant des listes d'objets enrichis
    """
    boosts = []
    warnings = []

    # Anytime scorer boost
    if has_trait(strengths, 'prolific_scorer') or has_trait(strengths, 'reliable_scorer'):
        boosts.append({
            'market': 'anytime_scorer',
            'boost': 0.1,
            'reason': 'prolific_scorer' if has_trait(strengths, 'prolific_scorer') else 'reliable_scorer'
        })

    # Clinical finisher boost
    if has_trait(strengths, 'clinical_finisher'):
        boosts.append({
            'market': 'anytime_scorer',
            'boost': 0.15,
            'reason': 'clinical_finisher (conversion >25% ou xG_diff >+2)'
        })

    # First scorer boost (seulement si 5+ tirs précoces)
    early_shots = timing['periods']['0-15']['shots']
    if early_shots >= 5 and (has_trait(strengths, 'fast_starter') or timing['early_threat'] > 5):
        boosts.append({
            'market': 'first_scorer',
            'boost': 0.15,
            'reason': f"early_threat={timing['early_threat']:.1f} (n={early_shots})"
        })

    # Last scorer boost (seulement si 5+ tirs tardifs)
    late_shots = timing['periods']['76-90']['shots'] + timing['periods']['90+']['shots']
    if late_shots >= 5 and (has_trait(strengths, 'clutch_scorer') or timing['clutch_factor'] > 5):
        boosts.append({
            'market': 'last_scorer',
            'boost': 0.15,
            'reason': f"clutch_factor={timing['clutch_factor']:.1f} (n={late_shots})"
        })

    # Header goal boost
    if has_trait(strengths, 'aerial_threat'):
        header_conv = shot_types.get('by_type', {}).get('Head', {}).get('conversion', 0)
        boosts.append({
            'market': 'header_goal',
            'boost': 0.2,
            'reason': f"header_conversion={header_conv:.1f}%"
        })

    # Outside box goal boost
    if has_trait(strengths, 'long_range_threat'):
        outside_conv = zones['depth_zones'].get('outside_box', {}).get('conversion', 0)
        boosts.append({
            'market': 'outside_box_goal',
            'boost': 0.15,
            'reason': f"outside_box_conversion={outside_conv:.1f}%"
        })

    # Set piece goal boost
    if has_trait(strengths, 'set_piece_specialist'):
        boosts.append({
            'market': 'set_piece_goal',
            'boost': 0.2,
            'reason': 'set_piece_specialist'
        })

    # First half goal boost
    if timing['first_half_conversion'] > timing['second_half_conversion'] + 5:
        boosts.append({
            'market': 'first_half_goal',
            'boost': 0.1,
            'reason': f"1H_conv={timing['first_half_conversion']:.1f}% vs 2H={timing['second_half_conversion']:.1f}%"
        })

    # Warnings (avec sample_size dans reason pour transparence)
    if has_trait(weaknesses, 'slow_starter'):
        warnings.append({
            'market': 'first_scorer',
            'warning': 'slow_starter',
            'reason': f"early_threat={timing['early_threat']:.1f} (n={early_shots})"
        })

    if has_trait(weaknesses, 'clutch_fader'):
        warnings.append({
            'market': 'last_scorer',
            'warning': 'clutch_fader',
            'reason': f"clutch_factor={timing['clutch_factor']:.1f} (n={late_shots})"
        })

    if has_trait(weaknesses, 'weak_header'):
        warnings.append({
            'market': 'header_goal',
            'warning': 'weak_header',
            'reason': f"low_aerial_conversion"
        })

    if has_trait(weaknesses, 'wasteful'):
        warnings.append({
            'market': 'anytime_scorer',
            'warning': 'wasteful',
            'reason': 'xG_diff < -2 (sous-performe)'
        })

    if has_trait(weaknesses, 'one_footed'):
        warnings.append({
            'market': 'anytime_scorer',
            'warning': 'one_footed',
            'reason': '>85% tirs du même pied'
        })

    return {
        'boosts': boosts,
        'warnings': warnings
    }


# ============================================================================
# GÉNÉRATION DU PROFIL COMPLET
# ============================================================================

def generate_shooter_profile(player_name: str, shots: List[Dict]) -> Dict[str, Any]:
    """
    Génère le profil complet pour un tireur
    """
    # Extraire player_id (prendre le premier non-null)
    player_id = None
    for shot in shots:
        if shot.get('player_id'):
            player_id = shot['player_id']
            break

    # Extraire équipes (peut jouer pour plusieurs)
    teams = set()
    leagues = set()
    for shot in shots:
        if shot.get('h_team'):
            teams.add(shot['h_team'])
        if shot.get('a_team'):
            teams.add(shot['a_team'])
        if shot.get('league'):
            leagues.add(shot['league'])

    # Statistiques globales
    total_shots = len(shots)
    total_goals = sum(1 for s in shots if s.get('result') == 'Goal')
    total_xg = sum(safe_float(s.get('xG', 0)) for s in shots)

    # Analyses détaillées
    timing = analyze_timing(shots)
    zones = analyze_zones(shots)
    shot_types = analyze_shot_types(shots)
    situations = analyze_situations(shots)

    # Calcul xG_diff pour generate_strengths_weaknesses
    xg_diff = calculate_xg_diff(total_goals, total_xg)

    # Forces et faiblesses (enrichies avec mapping market)
    strengths, weaknesses = generate_strengths_weaknesses(
        timing, zones, shot_types, situations, total_goals, total_shots, xg_diff
    )

    # Betting hints
    betting_hints = generate_betting_hints(
        timing, zones, shot_types, situations, strengths, weaknesses
    )

    return {
        'player_id': player_id,
        'teams': list(teams),
        'leagues': list(leagues),
        'summary': {
            'total_shots': total_shots,
            'total_goals': total_goals,
            'total_xG': round(total_xg, 2),
            'conversion': calculate_conversion(total_goals, total_shots),
            'xG_diff': xg_diff,
            'confidence': calculate_confidence(total_shots)
        },
        'timing_analysis': timing,
        'zone_analysis': zones,
        'shot_type_analysis': shot_types,
        'situation_analysis': situations,
        'strengths': strengths,
        'weaknesses': weaknesses,
        'betting_hints': betting_hints,
        'generated_at': datetime.now().isoformat()
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("CALCUL DES SHOOTER PROFILES DEPUIS ALL_SHOTS_AGAINST")
    print("=" * 70)

    # Charger les données
    print("\n📂 Chargement de all_shots_against_2025.json...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Collecter les tirs par joueur
    print("🔄 Collection des tirs par joueur...")
    player_shots = collect_player_shots(data)

    print(f"   → {len(player_shots)} joueurs uniques trouvés")

    # Statistiques
    stats = {
        'total_players': len(player_shots),
        'profiles_generated': 0,
        'with_goals': 0,
        'with_5plus_shots': 0,
        'with_10plus_shots': 0,
        'total_shots_processed': 0,
        'total_goals': 0,
        'strengths_count': defaultdict(int),
        'weaknesses_count': defaultdict(int),
        'top_scorers': [],
        'top_converters': []
    }

    # Générer les profils
    print("\n🔄 Génération des shooter profiles...")

    shooters = {}

    for player_name, shots in player_shots.items():
        # Filtrer: minimum 3 tirs pour être inclus
        if len(shots) < 3:
            continue

        profile = generate_shooter_profile(player_name, shots)
        shooters[player_name] = profile

        stats['profiles_generated'] += 1
        stats['total_shots_processed'] += profile['summary']['total_shots']
        stats['total_goals'] += profile['summary']['total_goals']

        if profile['summary']['total_goals'] > 0:
            stats['with_goals'] += 1
        if profile['summary']['total_shots'] >= 5:
            stats['with_5plus_shots'] += 1
        if profile['summary']['total_shots'] >= 10:
            stats['with_10plus_shots'] += 1

        for s in profile['strengths']:
            trait = s.get('trait') if isinstance(s, dict) else s
            stats['strengths_count'][trait] += 1
        for w in profile['weaknesses']:
            trait = w.get('trait') if isinstance(w, dict) else w
            stats['weaknesses_count'][trait] += 1

        # Top scorers
        stats['top_scorers'].append({
            'name': player_name,
            'goals': profile['summary']['total_goals'],
            'shots': profile['summary']['total_shots'],
            'conversion': profile['summary']['conversion']
        })

    # Trier top scorers
    stats['top_scorers'] = sorted(stats['top_scorers'], key=lambda x: -x['goals'])[:20]

    # Top converters (min 10 shots)
    stats['top_converters'] = sorted(
        [s for s in stats['top_scorers'] if s['shots'] >= 10],
        key=lambda x: -x['conversion']
    )[:10]

    # Construire output
    output = {
        'metadata': {
            'source': 'all_shots_against_2025.json',
            'generated_at': datetime.now().isoformat(),
            'total_shooters': stats['profiles_generated'],
            'total_shots': stats['total_shots_processed'],
            'total_goals': stats['total_goals'],
            'min_shots_threshold': 3
        },
        'shooters': shooters
    }

    # Sauvegarder
    print(f"\n💾 Sauvegarde dans {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Afficher statistiques
    print("\n" + "=" * 70)
    print("📊 STATISTIQUES FINALES")
    print("=" * 70)

    print(f"\n🎯 SHOOTERS ANALYSÉS: {stats['profiles_generated']}")
    print(f"   ├── Avec buts: {stats['with_goals']} ({stats['with_goals']/stats['profiles_generated']*100:.1f}%)")
    print(f"   ├── 5+ tirs: {stats['with_5plus_shots']} ({stats['with_5plus_shots']/stats['profiles_generated']*100:.1f}%)")
    print(f"   └── 10+ tirs: {stats['with_10plus_shots']} ({stats['with_10plus_shots']/stats['profiles_generated']*100:.1f}%)")

    print(f"\n⚽ VOLUME TOTAL:")
    print(f"   ├── Tirs traités: {stats['total_shots_processed']}")
    print(f"   └── Buts: {stats['total_goals']}")

    print(f"\n💪 FORCES DÉTECTÉES:")
    for strength, count in sorted(stats['strengths_count'].items(), key=lambda x: -x[1])[:10]:
        print(f"   ├── {strength}: {count} joueurs")

    print(f"\n⚠️  FAIBLESSES DÉTECTÉES:")
    for weakness, count in sorted(stats['weaknesses_count'].items(), key=lambda x: -x[1])[:10]:
        print(f"   ├── {weakness}: {count} joueurs")

    print(f"\n🏆 TOP 10 BUTEURS:")
    for i, scorer in enumerate(stats['top_scorers'][:10], 1):
        print(f"   {i:2}. {scorer['name']}: {scorer['goals']} buts ({scorer['shots']} tirs, {scorer['conversion']:.1f}%)")

    print(f"\n🎯 TOP 5 CONVERTISSEURS (min 10 tirs):")
    for i, conv in enumerate(stats['top_converters'][:5], 1):
        print(f"   {i}. {conv['name']}: {conv['conversion']:.1f}% ({conv['goals']}/{conv['shots']})")

    print("\n" + "=" * 70)
    print("✅ GÉNÉRATION TERMINÉE")
    print("=" * 70)

    return stats


if __name__ == '__main__':
    main()
