#!/usr/bin/env python3
"""
MIDFIELDER BETTING PROFILES - QUANT HEDGE FUND GRADE
Génère les profils de paris pour milieux de terrain

Classification automatique:
- SENTINELLE (N°6): Rodri, Tchouaméni, Casemiro
- BOX_TO_BOX (N°8): Bellingham, Valverde, Barella
- MENEUR (N°10): Bruno Fernandes, De Bruyne, Pedri

Paradigme: ABSENCE_SHOCK = Impact quantifié si absent
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

# Configuration logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Chemins
INPUT_FILE = '/home/Mon_ps/data/quantum_v2/player_dna_unified.json'
OUTPUT_FILE = '/home/Mon_ps/data/quantum_v2/midfielder_betting_profiles.json'

# Seuils de classification (calibrés sur données réelles)
CLASSIFICATION_THRESHOLDS = {
    'SENTINELLE': {
        'min_tackles_per_90': 2.0,
        'min_interceptions_per_90': 0.8,
        'min_ball_recoveries_per_90': 4.0,
        'max_key_passes_per_90': 1.5,
        'max_xA_per_90': 0.15
    },
    'MENEUR': {
        'min_key_passes_per_90': 1.5,
        'min_xA_per_90': 0.15,
        'min_sca_per_90': 3.0,
        'max_tackles_per_90': 2.0
    },
    'BOX_TO_BOX': {
        # Par défaut si ni SENTINELLE ni MENEUR
        'min_progressive_carries_per_90': 1.0,
        'balanced_offensive_defensive': True
    }
}

# Mapping traits vers marchés
TRAIT_MARKET_MAPPING = {
    # Traits offensifs
    'playmaker': {
        'markets': ['team_goals_over', 'assists_market', 'first_assist'],
        'edge_type': 'indirect_positive',
        'edge_mechanism': 'chance_creation'
    },
    'creative_engine': {
        'markets': ['team_goals_over', 'btts_yes', 'over_2.5'],
        'edge_type': 'indirect_positive',
        'edge_mechanism': 'high_volume_chances'
    },
    'through_ball_specialist': {
        'markets': ['first_goal_assist', 'anytime_assist'],
        'edge_type': 'direct_positive',
        'edge_mechanism': 'key_pass_quality'
    },
    'progressive_player': {
        'markets': ['team_possession', 'team_goals_over'],
        'edge_type': 'indirect_positive',
        'edge_mechanism': 'ball_progression'
    },

    # Traits défensifs
    'ball_winner': {
        'markets': ['clean_sheet', 'under_goals', 'under_2.5'],
        'edge_type': 'indirect_positive',
        'edge_mechanism': 'defensive_contribution'
    },
    'pressing_monster': {
        'markets': ['first_goal_under_20', 'team_goals_1h'],
        'edge_type': 'indirect_positive',
        'edge_mechanism': 'high_press_recoveries'
    },
    'aerial_dominant': {
        'markets': ['corner_goals', 'set_piece_goal'],
        'edge_type': 'direct_positive',
        'edge_mechanism': 'aerial_threat'
    },

    # Traits discipline
    'discipline_risk': {
        'markets': ['player_card', 'over_cards_match'],
        'edge_type': 'direct_positive',
        'edge_mechanism': 'high_foul_rate'
    },
    'foul_magnet': {
        'markets': ['over_fouls', 'opponent_cards'],
        'edge_type': 'indirect_positive',
        'edge_mechanism': 'draws_fouls'
    }
}

# ABSENCE SHOCK par rôle
ABSENCE_SHOCK_TEMPLATES = {
    'SENTINELLE': {
        'xGA_increase_pct': 40,
        'clean_sheet_reduction_pct': 25,
        'possession_loss_pct': 10,
        'primary_markets_affected': ['clean_sheet', 'under_goals', 'btts'],
        'betting_when_absent': [
            {'action': 'LAY', 'market': 'clean_sheet', 'confidence': 'HIGH'},
            {'action': 'BACK', 'market': 'btts_yes', 'confidence': 'MEDIUM'},
            {'action': 'BACK', 'market': 'over_2.5', 'confidence': 'MEDIUM'}
        ]
    },
    'BOX_TO_BOX': {
        'xGA_increase_pct': 20,
        'xG_decrease_pct': 15,
        'possession_loss_pct': 15,
        'primary_markets_affected': ['btts', 'total_goals', 'possession'],
        'betting_when_absent': [
            {'action': 'BACK', 'market': 'btts_yes', 'confidence': 'MEDIUM'},
            {'action': 'BACK', 'market': 'over_cards', 'confidence': 'LOW'},
            {'action': 'FADE', 'market': 'team_win', 'confidence': 'LOW'}
        ]
    },
    'MENEUR': {
        'xG_decrease_pct': 30,
        'chances_created_reduction_pct': 35,
        'possession_loss_pct': 5,
        'primary_markets_affected': ['team_goals', 'over_under', 'btts'],
        'betting_when_absent': [
            {'action': 'BACK', 'market': 'under_team_goals', 'confidence': 'HIGH'},
            {'action': 'LAY', 'market': 'team_win', 'confidence': 'MEDIUM'},
            {'action': 'BACK', 'market': 'draw', 'confidence': 'LOW'}
        ]
    }
}

# Collision scenarios
COLLISION_SCENARIOS = {
    'SENTINELLE': [
        {
            'opponent_profile': 'HIGH_VERTICALITY',
            'impact': 'CRITICAL_POSITIVE',
            'reason': 'Coupe les transitions rapides adverses',
            'market_boost': ['clean_sheet', 'under_goals']
        },
        {
            'opponent_profile': 'POSSESSION_HEAVY',
            'impact': 'NEUTRAL',
            'reason': 'Bataille du milieu équilibrée'
        },
        {
            'opponent_profile': 'SET_PIECE_THREAT',
            'impact': 'POSITIVE',
            'reason': 'Protection zone centrale sur CPA'
        }
    ],
    'BOX_TO_BOX': [
        {
            'opponent_profile': 'WEAK_MIDFIELD',
            'impact': 'CRITICAL_POSITIVE',
            'reason': 'Domine le milieu, dicte le tempo',
            'market_boost': ['team_win', 'over_goals']
        },
        {
            'opponent_profile': 'HIGH_PRESS',
            'impact': 'POSITIVE',
            'reason': 'Peut porter le ballon sous pression',
            'market_boost': ['btts']
        },
        {
            'opponent_profile': 'PHYSICAL_TEAM',
            'impact': 'VARIABLE',
            'reason': 'Dépend de la protection arbitrale'
        }
    ],
    'MENEUR': [
        {
            'opponent_profile': 'LOW_BLOCK',
            'impact': 'CRITICAL_POSITIVE',
            'reason': 'Temps et espace pour créer',
            'market_boost': ['team_goals_over', 'assists']
        },
        {
            'opponent_profile': 'HIGH_PRESS',
            'impact': 'NEGATIVE',
            'reason': 'Moins de temps sur le ballon',
            'market_reduce': ['assists', 'team_goals']
        },
        {
            'opponent_profile': 'MAN_MARKING',
            'impact': 'VARIABLE',
            'reason': 'Dépend de la capacité à se démarquer'
        }
    ]
}


def load_unified_data() -> Dict:
    """Charge les données unifiées des joueurs"""
    logger.info(f"Chargement de {INPUT_FILE}...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    logger.info(f"  Chargé: {len(data.get('players', {}))} joueurs")
    return data


def get_stat_value(player: Dict, stat_name: str) -> float:
    """Récupère une stat depuis différentes sources"""
    fbref = player.get('fbref', {})

    # Stats dans defense fbref
    defense = fbref.get('defense', {})
    if stat_name in defense:
        return float(defense.get(stat_name, 0) or 0)

    # Stats dans possession fbref
    possession = fbref.get('possession', {})
    if stat_name in possession:
        return float(possession.get(stat_name, 0) or 0)

    # Stats dans passing fbref
    passing = fbref.get('passing', {})
    if stat_name in passing:
        return float(passing.get(stat_name, 0) or 0)

    # Stats dans discipline fbref
    discipline = fbref.get('discipline', {})
    if stat_name in discipline:
        return float(discipline.get(stat_name, 0) or 0)

    # Stats dans chance_creation fbref
    chance = fbref.get('chance_creation', {})
    if stat_name in chance:
        return float(chance.get(stat_name, 0) or 0)

    # Stats dans shooting fbref
    shooting = fbref.get('shooting', {})
    if stat_name in shooting:
        return float(shooting.get(stat_name, 0) or 0)

    # Stats dans recovery fbref
    recovery = fbref.get('recovery', {})
    if stat_name in recovery:
        return float(recovery.get(stat_name, 0) or 0)

    # Stats dérivées (per 90)
    derived = fbref.get('derived', {})
    if stat_name in derived:
        return float(derived.get(stat_name, 0) or 0)

    # Impact (données understat enrichies)
    impact = player.get('impact', {})
    if stat_name in impact:
        return float(impact.get(stat_name, 0) or 0)

    # Understat direct
    understat = player.get('understat', {})
    if stat_name in understat:
        return float(understat.get(stat_name, 0) or 0)

    # Stats directes fbref
    if stat_name in fbref:
        return float(fbref.get(stat_name, 0) or 0)

    # Stats directes player
    if stat_name in player:
        return float(player.get(stat_name, 0) or 0)

    return 0.0


def get_per_90_stat(player: Dict, stat_name: str, minutes_90: float) -> float:
    """Calcule une stat per 90 minutes"""
    if minutes_90 <= 0:
        return 0.0

    # Chercher la stat déjà en per90 dans derived
    per90_name = f"{stat_name}_90"
    fbref = player.get('fbref', {})
    derived = fbref.get('derived', {})

    if per90_name in derived:
        return float(derived.get(per90_name, 0) or 0)

    # Stats per90 directes dans chance_creation
    chance = fbref.get('chance_creation', {})
    if per90_name in chance:
        return float(chance.get(per90_name, 0) or 0)

    # Sinon calculer depuis la valeur brute
    raw_value = get_stat_value(player, stat_name)
    return raw_value / minutes_90


def get_xA_per_90(player: Dict, minutes_90: float) -> float:
    """
    Récupère xA/90 depuis la meilleure source disponible
    Ordre de priorité: attacking > style > impact > fbref > understat

    CORRECTION BUG: L'ancien code cherchait UNIQUEMENT dans understat.xA
    qui était ABSENT pour 74% des joueurs (dont Bruno Fernandes).
    """
    if minutes_90 <= 0:
        return 0.0

    # 1. attacking.xA_per_90 (déjà calculé per90)
    attacking = player.get('attacking', {})
    if attacking and attacking.get('xA_per_90'):
        val = float(attacking.get('xA_per_90', 0) or 0)
        if val > 0:
            return val

    # 2. style.metrics.xA_90 (déjà calculé per90)
    style = player.get('style', {})
    if isinstance(style, dict):
        metrics = style.get('metrics', {})
        if metrics and metrics.get('xA_90'):
            val = float(metrics.get('xA_90', 0) or 0)
            if val > 0:
                return val

    # 3. impact.xA (total, diviser par minutes_90)
    impact = player.get('impact', {})
    if impact and impact.get('xA'):
        total_xA = float(impact.get('xA', 0) or 0)
        if total_xA > 0:
            return total_xA / minutes_90

    # 4. fbref.shooting.xA (total, diviser par minutes_90)
    fbref = player.get('fbref', {})
    if fbref:
        shooting = fbref.get('shooting', {})
        if shooting and shooting.get('xA'):
            total_xA = float(shooting.get('xA', 0) or 0)
            if total_xA > 0:
                return total_xA / minutes_90

    # 5. understat.xA (total, diviser par minutes_90) - fallback
    understat = player.get('understat', {})
    if understat and understat.get('xA'):
        total_xA = float(understat.get('xA', 0) or 0)
        if total_xA > 0:
            return total_xA / minutes_90

    return 0.0


def classify_midfielder_role(player: Dict, minutes_90: float) -> Tuple[str, float]:
    """
    Classifie automatiquement le rôle du milieu
    Returns: (role, confidence)
    """
    # Extraire les stats clés
    tackles = get_per_90_stat(player, 'tackles', minutes_90)
    tackles_won = get_per_90_stat(player, 'tackles_won', minutes_90)
    interceptions = get_per_90_stat(player, 'interceptions', minutes_90)
    ball_recoveries = get_per_90_stat(player, 'ball_recoveries', minutes_90)
    key_passes = get_per_90_stat(player, 'key_passes', minutes_90)
    progressive_carries = get_per_90_stat(player, 'progressive_carries', minutes_90)
    progressive_passes = get_per_90_stat(player, 'progressive_passes', minutes_90)

    # xA depuis TOUTES les sources (attacking > style > impact > fbref > understat)
    xA_per_90 = get_xA_per_90(player, minutes_90)

    # SCA depuis fbref
    sca = get_per_90_stat(player, 'shot_creating_actions', minutes_90)

    # Scores pour chaque rôle
    sentinelle_score = 0
    meneur_score = 0
    box_to_box_score = 0

    # SENTINELLE scoring
    if tackles >= 2.0:
        sentinelle_score += 25
    if interceptions >= 0.8:
        sentinelle_score += 25
    if ball_recoveries >= 4.0:
        sentinelle_score += 25
    if key_passes < 1.5:
        sentinelle_score += 15
    if xA_per_90 < 0.15:
        sentinelle_score += 10

    # MENEUR scoring
    if key_passes >= 1.5:
        meneur_score += 30
    if xA_per_90 >= 0.15:
        meneur_score += 25
    if sca >= 3.0:
        meneur_score += 25
    if tackles < 2.0:
        meneur_score += 10
    if progressive_passes >= 5.0:
        meneur_score += 10

    # BOX_TO_BOX scoring (équilibré)
    if progressive_carries >= 1.0:
        box_to_box_score += 20
    if 1.0 <= tackles <= 3.0:
        box_to_box_score += 20
    if 0.5 <= key_passes <= 2.5:
        box_to_box_score += 20
    if ball_recoveries >= 3.0:
        box_to_box_score += 20
    if progressive_passes >= 3.0:
        box_to_box_score += 20

    # Déterminer le rôle
    scores = {
        'SENTINELLE': sentinelle_score,
        'BOX_TO_BOX': box_to_box_score,
        'MENEUR': meneur_score
    }

    best_role = max(scores, key=scores.get)
    max_score = scores[best_role]

    # Confidence basée sur la différence avec le 2ème
    sorted_scores = sorted(scores.values(), reverse=True)
    if sorted_scores[0] > 0:
        confidence = min(1.0, (sorted_scores[0] - sorted_scores[1]) / sorted_scores[0] + 0.5)
    else:
        confidence = 0.5

    return best_role, round(confidence, 2)


def calculate_role_metrics(player: Dict, role: str, minutes_90: float) -> Dict:
    """Calcule les métriques spécifiques au rôle"""
    metrics = {}

    if role == 'SENTINELLE':
        metrics = {
            'tackles_per_90': round(get_per_90_stat(player, 'tackles', minutes_90), 2),
            'tackles_won_per_90': round(get_per_90_stat(player, 'tackles_won', minutes_90), 2),
            'interceptions_per_90': round(get_per_90_stat(player, 'interceptions', minutes_90), 2),
            'ball_recoveries_per_90': round(get_per_90_stat(player, 'ball_recoveries', minutes_90), 2),
            'blocks_per_90': round(get_per_90_stat(player, 'blocks', minutes_90), 2),
            'clearances_per_90': round(get_per_90_stat(player, 'clearances', minutes_90), 2),
            'defensive_rating': 0  # Calculé après
        }
        # Rating défensif (0-100)
        def_score = (
            min(metrics['tackles_won_per_90'] / 3.0, 1.0) * 30 +
            min(metrics['interceptions_per_90'] / 2.0, 1.0) * 25 +
            min(metrics['ball_recoveries_per_90'] / 8.0, 1.0) * 25 +
            min(metrics['blocks_per_90'] / 2.0, 1.0) * 10 +
            min(metrics['clearances_per_90'] / 3.0, 1.0) * 10
        )
        metrics['defensive_rating'] = round(def_score, 0)

    elif role == 'MENEUR':
        metrics = {
            'xA_per_90': round(get_xA_per_90(player, minutes_90), 3),
            'key_passes_per_90': round(get_per_90_stat(player, 'key_passes', minutes_90), 2),
            'sca_per_90': round(get_per_90_stat(player, 'shot_creating_actions', minutes_90), 2),
            'gca_per_90': round(get_per_90_stat(player, 'goal_creating_actions', minutes_90), 2),
            'through_balls_per_90': round(get_per_90_stat(player, 'through_balls', minutes_90), 2),
            'progressive_passes_per_90': round(get_per_90_stat(player, 'progressive_passes', minutes_90), 2),
            'creative_rating': 0  # Calculé après
        }
        # Rating créatif (0-100)
        creative_score = (
            min(metrics['xA_per_90'] / 0.4, 1.0) * 30 +
            min(metrics['key_passes_per_90'] / 4.0, 1.0) * 25 +
            min(metrics['sca_per_90'] / 6.0, 1.0) * 20 +
            min(metrics['gca_per_90'] / 1.0, 1.0) * 15 +
            min(metrics['through_balls_per_90'] / 1.5, 1.0) * 10
        )
        metrics['creative_rating'] = round(creative_score, 0)

    else:  # BOX_TO_BOX
        metrics = {
            'progressive_carries_per_90': round(get_per_90_stat(player, 'progressive_carries', minutes_90), 2),
            'progressive_passes_per_90': round(get_per_90_stat(player, 'progressive_passes', minutes_90), 2),
            'tackles_per_90': round(get_per_90_stat(player, 'tackles', minutes_90), 2),
            'ball_recoveries_per_90': round(get_per_90_stat(player, 'ball_recoveries', minutes_90), 2),
            'key_passes_per_90': round(get_per_90_stat(player, 'key_passes', minutes_90), 2),
            'xA_per_90': round(get_xA_per_90(player, minutes_90), 3),
            'offensive_rating': 0,
            'defensive_rating': 0,
            'balance_score': 0
        }
        # Ratings
        off_score = (
            min(metrics['progressive_carries_per_90'] / 4.0, 1.0) * 35 +
            min(metrics['key_passes_per_90'] / 3.0, 1.0) * 35 +
            min(metrics['xA_per_90'] / 0.25, 1.0) * 30
        )
        def_score = (
            min(metrics['tackles_per_90'] / 3.0, 1.0) * 50 +
            min(metrics['ball_recoveries_per_90'] / 7.0, 1.0) * 50
        )
        metrics['offensive_rating'] = round(off_score, 0)
        metrics['defensive_rating'] = round(def_score, 0)
        metrics['balance_score'] = round((off_score + def_score) / 2, 0)

    return metrics


def calculate_discipline_profile(player: Dict, minutes_90: float) -> Dict:
    """Calcule le profil discipline"""
    fouls = get_stat_value(player, 'fouls_committed')
    fouls_drawn = get_stat_value(player, 'fouls_drawn')
    yellows = get_stat_value(player, 'yellow_cards')
    reds = get_stat_value(player, 'red_cards')

    fouls_per_90 = fouls / minutes_90 if minutes_90 > 0 else 0
    fouls_drawn_per_90 = fouls_drawn / minutes_90 if minutes_90 > 0 else 0
    cards_per_90 = (yellows + reds) / minutes_90 if minutes_90 > 0 else 0

    # Probabilité de carton par match
    matches = minutes_90
    card_probability = (yellows + reds) / matches if matches > 0 else 0

    # Classification risque
    if card_probability > 0.25 or fouls_per_90 > 2.0:
        risk = 'HIGH'
    elif card_probability > 0.15 or fouls_per_90 > 1.5:
        risk = 'MEDIUM'
    else:
        risk = 'LOW'

    return {
        'fouls_per_90': round(fouls_per_90, 2),
        'fouls_drawn_per_90': round(fouls_drawn_per_90, 2),
        'yellow_cards_total': int(yellows),
        'red_cards_total': int(reds),
        'cards_per_90': round(cards_per_90, 3),
        'card_probability': round(card_probability, 3),
        'discipline_risk': risk
    }


def calculate_tempo_control(player: Dict, minutes_90: float) -> Dict:
    """Calcule le contrôle du tempo"""
    prog_carries = get_per_90_stat(player, 'progressive_carries', minutes_90)
    prog_passes = get_per_90_stat(player, 'progressive_passes', minutes_90)
    touches = get_per_90_stat(player, 'touches', minutes_90)
    pass_completion = get_stat_value(player, 'pass_completion_pct')

    # Verticality index (0-1): ratio actions progressives vs total
    total_actions = prog_carries + prog_passes + touches / 10
    if total_actions > 0:
        verticality = (prog_carries + prog_passes) / total_actions
    else:
        verticality = 0.5

    # Tempo impact
    tempo_score = prog_carries * 10 + prog_passes * 5 + (pass_completion / 10)
    if tempo_score > 80:
        tempo_impact = 'CRITICAL'
    elif tempo_score > 50:
        tempo_impact = 'HIGH'
    elif tempo_score > 30:
        tempo_impact = 'MEDIUM'
    else:
        tempo_impact = 'LOW'

    return {
        'progressive_carries_per_90': round(prog_carries, 2),
        'progressive_passes_per_90': round(prog_passes, 2),
        'touches_per_90': round(touches, 1),
        'pass_completion': round(pass_completion, 1),
        'verticality_index': round(min(verticality, 1.0), 2),
        'tempo_impact': tempo_impact
    }


def calculate_absence_shock(player: Dict, role: str, role_metrics: Dict, team_stats: Dict = None) -> Dict:
    """Calcule l'impact si le joueur est absent"""
    template = ABSENCE_SHOCK_TEMPLATES.get(role, ABSENCE_SHOCK_TEMPLATES['BOX_TO_BOX'])

    # Score de dépendance basé sur le rating
    if role == 'SENTINELLE':
        rating = role_metrics.get('defensive_rating', 50)
    elif role == 'MENEUR':
        rating = role_metrics.get('creative_rating', 50)
    else:
        rating = role_metrics.get('balance_score', 50)

    # Dependency score (0-100)
    dependency_score = min(100, rating * 1.2)

    # Profile
    if dependency_score >= 80:
        profile = 'CRITICAL'
    elif dependency_score >= 60:
        profile = 'HIGH'
    elif dependency_score >= 40:
        profile = 'MEDIUM'
    else:
        profile = 'LOW'

    # Impact ajusté selon le score
    impact_multiplier = dependency_score / 100

    impact = {}
    if 'xGA_increase_pct' in template:
        impact['xGA_increase'] = f"+{int(template['xGA_increase_pct'] * impact_multiplier)}%"
    if 'xG_decrease_pct' in template:
        impact['xG_decrease'] = f"-{int(template['xG_decrease_pct'] * impact_multiplier)}%"
    if 'clean_sheet_reduction_pct' in template:
        impact['clean_sheet_probability'] = f"-{int(template['clean_sheet_reduction_pct'] * impact_multiplier)}%"
    if 'possession_loss_pct' in template:
        impact['possession_loss'] = f"-{int(template['possession_loss_pct'] * impact_multiplier)}%"
    if 'chances_created_reduction_pct' in template:
        impact['chances_reduction'] = f"-{int(template['chances_created_reduction_pct'] * impact_multiplier)}%"

    return {
        'dependency_score': round(dependency_score, 0),
        'dependency_profile': profile,
        'impact_if_absent': impact,
        'primary_markets_affected': template['primary_markets_affected'],
        'betting_when_absent': template['betting_when_absent']
    }


def extract_strengths_weaknesses(player: Dict, role: str) -> Tuple[List[Dict], List[Dict]]:
    """Extrait les forces et faiblesses avec mapping marchés"""
    strengths = []
    weaknesses = []

    # Traits existants dans le joueur
    existing_strengths = player.get('strengths', [])
    if isinstance(existing_strengths, list):
        for s in existing_strengths:
            if isinstance(s, dict):
                trait = s.get('trait', '')
            else:
                trait = str(s)

            if trait in TRAIT_MARKET_MAPPING:
                mapping = TRAIT_MARKET_MAPPING[trait]
                strengths.append({
                    'trait': trait,
                    'markets': mapping['markets'],
                    'edge_type': mapping['edge_type'],
                    'edge_mechanism': mapping['edge_mechanism']
                })

    # Ajouter des traits basés sur le rôle
    if role == 'SENTINELLE':
        if not any(s.get('trait') == 'ball_winner' for s in strengths):
            strengths.append({
                'trait': 'tempo_controller',
                'markets': ['team_possession', 'under_goals'],
                'edge_type': 'indirect_positive',
                'edge_mechanism': 'game_control'
            })
    elif role == 'MENEUR':
        if not any(s.get('trait') == 'playmaker' for s in strengths):
            strengths.append({
                'trait': 'chance_creator',
                'markets': ['team_goals_over', 'assists_market'],
                'edge_type': 'indirect_positive',
                'edge_mechanism': 'chance_creation'
            })

    # Weaknesses existantes
    existing_weaknesses = player.get('weaknesses', [])
    if isinstance(existing_weaknesses, list):
        for w in existing_weaknesses:
            if isinstance(w, dict):
                weaknesses.append(w)
            else:
                weaknesses.append({'trait': str(w), 'markets': [], 'edge_type': 'warning'})

    return strengths, weaknesses


def generate_betting_hints(role: str, role_metrics: Dict, discipline: Dict, strengths: List) -> Dict:
    """Génère les conseils de paris"""
    boosts = []
    warnings = []

    if role == 'SENTINELLE':
        boosts.append("BACK Clean Sheet quand titulaire vs équipe verticale")
        boosts.append("BACK Under total goals dans matchs serrés")
        if discipline['discipline_risk'] in ['MEDIUM', 'HIGH']:
            boosts.append(f"BACK Player Card (prob: {discipline['card_probability']:.0%})")
            warnings.append("Risque carton sur fautes tactiques")

    elif role == 'MENEUR':
        if role_metrics.get('creative_rating', 0) >= 70:
            boosts.append("BACK Over team goals quand titulaire")
            boosts.append("BACK Assists market si disponible")
        if role_metrics.get('xA_per_90', 0) >= 0.25:
            boosts.append("BACK First Goal Assist vs Low Block")
        warnings.append("Under team goals si ABSENT")

    else:  # BOX_TO_BOX
        if role_metrics.get('balance_score', 0) >= 60:
            boosts.append("Impact global sur le match")
        boosts.append("BACK BTTS si équipe dépendante du pressing")
        if discipline['discipline_risk'] == 'HIGH':
            boosts.append(f"BACK Player Card (prob: {discipline['card_probability']:.0%})")

    # Ajouter boosts basés sur les strengths
    for s in strengths:
        if s.get('edge_type') == 'direct_positive':
            for market in s.get('markets', [])[:2]:
                boosts.append(f"BACK {market} ({s.get('trait')})")

    return {
        'boosts': boosts[:5],  # Max 5
        'warnings': warnings[:3]  # Max 3
    }


def generate_midfielder_profile(name: str, player: Dict) -> Optional[Dict]:
    """Génère le profil complet d'un milieu"""

    # Vérifier position
    meta = player.get('meta', {})
    position = meta.get('position', '')
    if not position:
        fbref = player.get('fbref', {})
        position = fbref.get('position', player.get('position', ''))

    # Filtrer les milieux - positions valides
    # M, MF, M S, MFFW, DFMF, MFDF, D M S, F M S, D M, F M
    midfielder_positions = ['M', 'MF', 'M S', 'MFFW', 'DFMF', 'MFDF', 'D M S', 'F M S', 'D M', 'F M', 'CM', 'DM', 'AM', 'CDM', 'CAM']
    pos_upper = str(position).upper()

    is_midfielder = False
    for mf_pos in midfielder_positions:
        if position == mf_pos or pos_upper == mf_pos:
            is_midfielder = True
            break

    if not is_midfielder:
        return None

    # Minutes jouées - depuis impact.time (understat enriched)
    impact = player.get('impact', {}) or {}
    time_played = float(impact.get('time', 0) or 0)
    minutes_90 = time_played / 90 if time_played > 0 else 0

    # Si pas dans impact, essayer fbref derived (stats per90 existent)
    if minutes_90 == 0:
        fbref = player.get('fbref', {})
        derived = fbref.get('derived', {})
        # Si derived existe avec des stats per90, on a au moins des données
        if derived and 'tackles_90' in derived:
            # Estimer minutes_90 depuis les stats brutes / per90
            defense = fbref.get('defense', {})
            tackles = float(defense.get('tackles', 0) or 0)
            tackles_90 = float(derived.get('tackles_90', 0) or 0)
            if tackles_90 > 0:
                minutes_90 = tackles / tackles_90

    # Minimum 3 matchs (270 minutes = 3.0 x 90)
    if minutes_90 < 3.0:
        return None

    # Classification du rôle
    role, role_confidence = classify_midfielder_role(player, minutes_90)

    # Métriques par rôle
    role_metrics = calculate_role_metrics(player, role, minutes_90)

    # Discipline
    discipline = calculate_discipline_profile(player, minutes_90)

    # Tempo control
    tempo = calculate_tempo_control(player, minutes_90)

    # Absence shock
    absence_shock = calculate_absence_shock(player, role, role_metrics)

    # Strengths/Weaknesses
    strengths, weaknesses = extract_strengths_weaknesses(player, role)

    # Collision scenarios
    collisions = COLLISION_SCENARIOS.get(role, [])

    # Betting hints
    betting_hints = generate_betting_hints(role, role_metrics, discipline, strengths)

    # Team context
    team = meta.get('team', '')
    if not team:
        team = fbref.get('team', player.get('team', 'Unknown'))
    league = meta.get('league', '')
    if not league:
        league = fbref.get('league', player.get('league', 'Unknown'))

    return {
        'meta': {
            'name': name,
            'team': team,
            'league': league,
            'position': position,
            'role': role,
            'role_confidence': role_confidence,
            'minutes_90': round(minutes_90, 1)
        },
        'role_metrics': {role: role_metrics},
        'tempo_control': tempo,
        'discipline_profile': discipline,
        'absence_shock': absence_shock,
        'strengths': strengths,
        'weaknesses': weaknesses,
        'collision_scenarios': collisions,
        'betting_hints': betting_hints,
        'team_context': {
            'team': team,
            'league': league,
            'is_key_player': absence_shock['dependency_profile'] in ['CRITICAL', 'HIGH'],
            'replacement_risk': 'HIGH' if absence_shock['dependency_score'] >= 70 else 'MEDIUM'
        }
    }


def main():
    """Fonction principale"""
    logger.info("=" * 70)
    logger.info("GÉNÉRATION BETTING PROFILES MILIEUX - QUANT HEDGE FUND")
    logger.info("=" * 70)

    # 1. Charger les données
    data = load_unified_data()
    players = data.get('players', {})

    # 2. Générer les profils
    logger.info("\nGénération des profils milieux...")

    profiles = {}
    stats = {
        'total_processed': 0,
        'total_midfielders': 0,
        'by_role': defaultdict(int),
        'by_league': defaultdict(int),
        'by_dependency': defaultdict(int)
    }

    for name, player in players.items():
        stats['total_processed'] += 1

        profile = generate_midfielder_profile(name, player)
        if profile:
            profiles[name] = profile
            stats['total_midfielders'] += 1
            stats['by_role'][profile['meta']['role']] += 1
            stats['by_league'][profile['meta']['league']] += 1
            stats['by_dependency'][profile['absence_shock']['dependency_profile']] += 1

    # 3. Créer le fichier de sortie
    output = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'source': 'player_dna_unified.json',
            'total_midfielders': stats['total_midfielders'],
            'version': '1.0',
            'paradigm': 'TEAM_CENTRIC_ADN'
        },
        'statistics': {
            'by_role': dict(stats['by_role']),
            'by_league': dict(stats['by_league']),
            'by_dependency': dict(stats['by_dependency'])
        },
        'profiles': profiles
    }

    # 4. Sauvegarder
    logger.info(f"\nSauvegarde vers {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # 5. Afficher les résultats
    logger.info("\n" + "=" * 70)
    logger.info("RÉSULTATS")
    logger.info("=" * 70)
    logger.info(f"\nTotal milieux profilés: {stats['total_midfielders']}")

    logger.info("\nPar rôle:")
    for role, count in sorted(stats['by_role'].items()):
        logger.info(f"   {role}: {count}")

    logger.info("\nPar ligue:")
    for league, count in sorted(stats['by_league'].items(), key=lambda x: -x[1])[:10]:
        logger.info(f"   {league}: {count}")

    logger.info("\nPar niveau de dépendance:")
    for dep, count in sorted(stats['by_dependency'].items()):
        logger.info(f"   {dep}: {count}")

    # 6. Exemples
    logger.info("\n" + "=" * 70)
    logger.info("EXEMPLES DE PROFILS")
    logger.info("=" * 70)

    examples = ['Bruno Fernandes', 'Rodri', 'Jude Bellingham', 'Pedri', 'Casemiro']
    for ex_name in examples:
        for name, profile in profiles.items():
            if ex_name.lower() in name.lower():
                logger.info(f"\n{profile['meta']['name']} ({profile['meta']['team']})")
                logger.info(f"   Rôle: {profile['meta']['role']} (conf: {profile['meta']['role_confidence']})")
                logger.info(f"   Absence Shock: {profile['absence_shock']['dependency_profile']} ({profile['absence_shock']['dependency_score']})")
                if profile['betting_hints']['boosts']:
                    logger.info(f"   Boosts: {profile['betting_hints']['boosts'][0]}")
                break

    logger.info("\n" + "=" * 70)
    logger.info(f"FICHIER CRÉÉ: {OUTPUT_FILE}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
