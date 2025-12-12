#!/usr/bin/env python3
"""
DEFENDER BETTING PROFILES - QUANT HEDGE FUND GRADE
Version 2.0 - Simplified CENTRAL/WIDE structure

DOUBLE CLASSIFICATION:
├── PRIMARY ROLE (2)
│   ├── CENTRAL: Central defenders (CB)
│   └── WIDE: All wide defenders (RB, LB, WB, FB)
│
└── SUB-ROLE (7)
    ├── CENTRAL: DOMINANT / BALL_PLAYING / STOPPER
    └── WIDE: ATTACKING / BALANCED / DEFENSIVE / INVERTED

Team-Centric ADN Paradigm: A defender's absence =
quantified impact on Clean Sheet, xGA, creativity from flanks
"""

import json
import logging
from pathlib import Path
from typing import Dict, Tuple, Optional
from datetime import datetime

# Configuration logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
BASE_PATH = Path("/home/Mon_ps")
DATA_PATH = BASE_PATH / "data" / "quantum_v2"
INPUT_FILE = DATA_PATH / "player_dna_unified.json"
OUTPUT_FILE = DATA_PATH / "defender_betting_profiles.json"


# ============================================================
# SUB-ROLE CONFIGURATION
# ============================================================

DEFENDER_POSITIONS = ['D', 'DF', 'D S', 'CB', 'RB', 'LB', 'FB', 'WB', 'DFMF', 'D M', 'D R', 'D L', 'D M S']

SUB_ROLE_CONFIG = {
    "CENTRAL": {
        "DOMINANT": {
            "description": "Aerial dominant defender (Van Dijk, Konaté)",
            "key_metrics": ["aerial_won", "clearances", "aerial_win_pct"],
            "thresholds": {
                "aerial_won_per_90": 3.0,
                "aerial_win_pct": 60.0,
                "clearances_per_90": 3.5
            },
            "betting_markets": ["clean_sheet", "team_to_score_header", "corners_won"],
            "absence_impact": {
                "aerial_vulnerability": "+40%",
                "set_piece_goals_conceded": "+30%",
                "clean_sheet_probability": "-25%"
            }
        },
        "BALL_PLAYING": {
            "description": "Ball-playing defender (Dias, Saliba, Stones)",
            "key_metrics": ["pass_completion", "progressive_passes", "carries_into_final_third"],
            "thresholds": {
                "pass_completion": 88.0,
                "progressive_passes_per_90": 4.0,
                "long_pass_completion": 65.0
            },
            "betting_markets": ["team_possession", "build_up_play"],
            "absence_impact": {
                "possession_loss": "-8%",
                "build_up_quality": "-20%",
                "long_ball_frequency": "+25%"
            }
        },
        "STOPPER": {
            "description": "Aggressive stopper (Araujo, Upamecano)",
            "key_metrics": ["tackles", "interceptions", "blocks", "fouls"],
            "thresholds": {
                "tackles_per_90": 2.0,
                "interceptions_per_90": 1.5,
                "blocks_per_90": 1.2
            },
            "betting_markets": ["player_card", "over_fouls", "clean_sheet"],
            "absence_impact": {
                "defensive_actions": "-25%",
                "pressing_intensity": "-15%"
            }
        }
    },
    "WIDE": {
        "ATTACKING": {
            "description": "Attacking wide defender (TAA, Robertson, Hakimi)",
            "key_metrics": ["crosses", "key_passes", "xA", "goals"],
            "thresholds": {
                "crosses_per_90": 4.0,
                "key_passes_per_90": 1.5,
                "xA_per_90": 0.10
            },
            "betting_markets": ["assists", "anytime_scorer", "team_goals", "crosses_completed"],
            "absence_impact": {
                "flank_creativity": "-40%",
                "crossing_threat": "-50%",
                "team_xG": "-15%"
            }
        },
        "BALANCED": {
            "description": "Balanced wide defender (Cancelo, Theo Hernandez)",
            "key_metrics": ["crosses", "tackles", "progressive_carries"],
            "thresholds": {
                "crosses_per_90": 2.5,
                "tackles_per_90": 1.8,
                "xA_per_90": 0.06
            },
            "betting_markets": ["team_goals", "clean_sheet", "assists"],
            "absence_impact": {
                "flank_balance": "-25%",
                "transition_play": "-20%"
            }
        },
        "DEFENSIVE": {
            "description": "Defensive wide defender (Walker, Pavard)",
            "key_metrics": ["tackles", "interceptions", "duels_won"],
            "thresholds": {
                "tackles_per_90": 2.5,
                "interceptions_per_90": 1.5,
                "crosses_per_90": 1.5
            },
            "betting_markets": ["clean_sheet", "opponent_goals_under"],
            "absence_impact": {
                "flank_defense": "-30%",
                "1v1_defense": "-35%"
            }
        },
        "INVERTED": {
            "description": "Inverted full-back (Zinchenko, Cucurella Pep-style)",
            "key_metrics": ["progressive_passes", "touches", "pass_completion"],
            "thresholds": {
                "progressive_passes_per_90": 4.0,
                "pass_completion": 88.0,
                "crosses_per_90": 1.5
            },
            "betting_markets": ["team_possession", "midfield_control"],
            "absence_impact": {
                "midfield_overload": "-25%",
                "possession_stability": "-15%"
            }
        }
    }
}


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def get_stat_value(player: Dict, stat_name: str) -> float:
    """Get a stat from various sources"""
    fbref = player.get('fbref', {})

    # Defense stats
    defense = fbref.get('defense', {})
    if stat_name in defense:
        return float(defense.get(stat_name, 0) or 0)

    # Possession stats
    possession = fbref.get('possession', {})
    if stat_name in possession:
        return float(possession.get(stat_name, 0) or 0)

    # Passing stats
    passing = fbref.get('passing', {})
    if stat_name in passing:
        return float(passing.get(stat_name, 0) or 0)

    # Chance creation
    chance = fbref.get('chance_creation', {})
    if stat_name in chance:
        return float(chance.get(stat_name, 0) or 0)

    # Aerial
    aerial = fbref.get('aerial', {})
    if stat_name in aerial:
        return float(aerial.get(stat_name, 0) or 0)

    # Discipline
    discipline = fbref.get('discipline', {})
    if stat_name in discipline:
        return float(discipline.get(stat_name, 0) or 0)

    # Derived stats
    derived = fbref.get('derived', {})
    if stat_name in derived:
        return float(derived.get(stat_name, 0) or 0)

    # Impact
    impact = player.get('impact', {}) or {}
    if stat_name in impact:
        return float(impact.get(stat_name, 0) or 0)

    # Direct stats
    if stat_name in player:
        return float(player.get(stat_name, 0) or 0)

    return 0.0


def get_per_90_stat(player: Dict, stat_name: str, minutes_90: float) -> float:
    """Get a stat per 90 minutes"""
    if minutes_90 <= 0:
        return 0.0

    # Check for already calculated per90 stats
    per90_name = f"{stat_name}_90"
    fbref = player.get('fbref', {})
    derived = fbref.get('derived', {})

    if per90_name in derived:
        return float(derived.get(per90_name, 0) or 0)

    # Otherwise calculate
    raw_value = get_stat_value(player, stat_name)
    return raw_value / minutes_90


def get_xA_per_90(player: Dict, minutes_90: float) -> float:
    """Get xA/90 from best available source"""
    if minutes_90 <= 0:
        return 0.0

    # 1. attacking.xA_per_90
    attacking = player.get('attacking', {})
    if attacking and attacking.get('xA_per_90'):
        val = float(attacking.get('xA_per_90', 0) or 0)
        if val > 0:
            return val

    # 2. style.metrics.xA_90
    style = player.get('style', {})
    if isinstance(style, dict):
        metrics = style.get('metrics', {})
        if metrics and metrics.get('xA_90'):
            val = float(metrics.get('xA_90', 0) or 0)
            if val > 0:
                return val

    # 3. impact.xA
    impact = player.get('impact', {}) or {}
    if impact.get('xA'):
        total_xA = float(impact.get('xA', 0) or 0)
        if total_xA > 0:
            return total_xA / minutes_90

    # 4. fbref.shooting.xA
    fbref = player.get('fbref', {})
    if fbref:
        shooting = fbref.get('shooting', {})
        if shooting and shooting.get('xA'):
            total_xA = float(shooting.get('xA', 0) or 0)
            if total_xA > 0:
                return total_xA / minutes_90

    return 0.0


# ============================================================
# DEFENDER CLASSIFICATION
# ============================================================

def classify_defender_role(player: Dict, minutes_90: float) -> Tuple[str, str, float]:
    """
    Classify defender into primary role + sub-role

    SIMPLIFIED STRUCTURE:
    - CENTRAL: Central defenders (CB)
    - WIDE: All wide defenders (RB, LB, WB, FB)

    Returns: (primary_role, sub_role, confidence)
    """
    fbref = player.get('fbref', {})
    meta = player.get('meta', {})
    position = meta.get('position', '') or fbref.get('position', player.get('position', ''))
    position = str(position).upper()

    # Determine primary role based on position
    primary_role = "CENTRAL"  # Default

    # WIDE = all wide players (RB, LB, WB, etc.)
    # Wide position indicators (explicit)
    wide_indicators = ['RB', 'LB', 'R B', 'L B', 'D R', 'D L', 'WB', 'W B', 'FB']

    # Attacking defender patterns - ONLY those with "F" (Forward) indicate attacking wingbacks
    # "D F" = Defender who also plays Forward (like Hakimi)
    # "D S" = Defender/Sweeper (NOT striker) - do NOT include here
    attacking_defender_patterns = ['D F', 'F D', 'D F S', 'F D S']

    for indicator in wide_indicators:
        if indicator in position:
            primary_role = "WIDE"
            break

    # Check attacking defender patterns (Hakimi = "D F S")
    if primary_role == "CENTRAL":
        for pattern in attacking_defender_patterns:
            if pattern in position:
                primary_role = "WIDE"
                break

    # If still ambiguous position (D, DF, D S, etc.), check stats as fallback
    # "D S" could be central (Dias) or wide (Robertson) - let stats decide
    if primary_role == "CENTRAL" and position in ['D', 'DF', 'D S', 'D M S', 'D M']:
        crosses = get_per_90_stat(player, 'crosses', minutes_90)
        progressive_carries = get_per_90_stat(player, 'progressive_carries', minutes_90)

        # Lower thresholds to catch more wide players
        # Even defensive full-backs (Walker-Peters) should be WIDE not CENTRAL
        if crosses >= 1.5 or progressive_carries >= 2.0:
            primary_role = "WIDE"
        # Extra check: combo of decent carries + some crosses
        elif crosses >= 0.5 and progressive_carries >= 1.5:
            primary_role = "WIDE"

    # Classify sub-role
    sub_role, confidence = classify_sub_role(player, minutes_90, primary_role)

    return primary_role, sub_role, confidence


def classify_sub_role(player: Dict, minutes_90: float, primary_role: str) -> Tuple[str, float]:
    """Classify sub-role based on primary role"""

    # Get key metrics
    tackles = get_per_90_stat(player, 'tackles', minutes_90)
    interceptions = get_per_90_stat(player, 'interceptions', minutes_90)
    blocks = get_per_90_stat(player, 'blocks', minutes_90)
    clearances = get_per_90_stat(player, 'clearances', minutes_90)

    # Aerial stats
    fbref = player.get('fbref', {})
    aerial = fbref.get('aerial', {})
    aerials_won = float(aerial.get('aerials_won', 0) or 0)
    aerials_lost = float(aerial.get('aerials_lost', 0) or 0)
    aerials_won_per_90 = aerials_won / minutes_90 if minutes_90 > 0 else 0

    # Offensive stats
    crosses = get_per_90_stat(player, 'crosses', minutes_90)
    key_passes = get_per_90_stat(player, 'key_passes', minutes_90)
    progressive_passes = get_per_90_stat(player, 'progressive_passes', minutes_90)
    progressive_carries = get_per_90_stat(player, 'progressive_carries', minutes_90)
    xA_per_90 = get_xA_per_90(player, minutes_90)

    # Pass completion
    passing = fbref.get('passing', {})
    pass_completion = float(passing.get('pass_completion_pct', 0) or 0)

    # Goals
    impact = player.get('impact', {}) or {}
    goals = float(impact.get('goals', 0) or 0)
    goals_per_90 = goals / minutes_90 if minutes_90 > 0 else 0

    if primary_role == "CENTRAL":
        # Scoring for CENTRAL sub-roles
        dominant_score = 0
        ball_playing_score = 0
        stopper_score = 0

        # DOMINANT: Aerial
        if aerials_won_per_90 >= 4.0:
            dominant_score += 50
        elif aerials_won_per_90 >= 3.0:
            dominant_score += 35
        elif aerials_won_per_90 >= 2.0:
            dominant_score += 20

        if clearances >= 4.5:
            dominant_score += 35
        elif clearances >= 3.0:
            dominant_score += 20
        elif clearances >= 2.0:
            dominant_score += 10

        # BALL_PLAYING: Passer
        if pass_completion >= 92:
            ball_playing_score += 45
        elif pass_completion >= 88:
            ball_playing_score += 30
        elif pass_completion >= 84:
            ball_playing_score += 15

        if progressive_passes >= 7.0:
            ball_playing_score += 45
        elif progressive_passes >= 5.0:
            ball_playing_score += 30
        elif progressive_passes >= 3.0:
            ball_playing_score += 15

        if progressive_carries >= 2.0:
            ball_playing_score += 20
        elif progressive_carries >= 1.0:
            ball_playing_score += 10

        # STOPPER: Aggressive
        if tackles >= 3.5:
            stopper_score += 45
        elif tackles >= 2.5:
            stopper_score += 30
        elif tackles >= 1.5:
            stopper_score += 15

        if interceptions >= 2.5:
            stopper_score += 40
        elif interceptions >= 1.8:
            stopper_score += 25
        elif interceptions >= 1.2:
            stopper_score += 12

        if blocks >= 2.0:
            stopper_score += 25
        elif blocks >= 1.2:
            stopper_score += 12

        scores = {"DOMINANT": dominant_score, "BALL_PLAYING": ball_playing_score, "STOPPER": stopper_score}

    else:  # WIDE
        # Scoring for WIDE sub-roles
        attacking_score = 0
        balanced_score = 0
        defensive_score = 0
        inverted_score = 0

        # ATTACKING (TAA, Robertson, Hakimi)
        # These are wingbacks who bomb forward, deliver crosses, create chances
        if crosses >= 5.5:
            attacking_score += 60
        elif crosses >= 4.0:
            attacking_score += 45
        elif crosses >= 2.8:
            attacking_score += 30  # Boosted from 20
        elif crosses >= 2.0:
            attacking_score += 15

        if key_passes >= 2.5:
            attacking_score += 50
        elif key_passes >= 1.5:
            attacking_score += 35
        elif key_passes >= 1.0:
            attacking_score += 20  # Boosted from 15

        if xA_per_90 >= 0.18:
            attacking_score += 55
        elif xA_per_90 >= 0.10:
            attacking_score += 40
        elif xA_per_90 >= 0.06:
            attacking_score += 22

        if goals_per_90 >= 0.12:
            attacking_score += 25
        elif goals_per_90 >= 0.06:
            attacking_score += 12

        # Combo bonus: High crosses + decent xA = definite attacker
        if crosses >= 2.5 and xA_per_90 >= 0.05:
            attacking_score += 25

        # DEFENSIVE (Walker, Pavard)
        if tackles >= 3.5:
            defensive_score += 45
        elif tackles >= 2.5:
            defensive_score += 30
        elif tackles >= 1.8:
            defensive_score += 15

        if interceptions >= 2.5:
            defensive_score += 40
        elif interceptions >= 1.5:
            defensive_score += 25
        elif interceptions >= 1.0:
            defensive_score += 12

        # Low offensive output = more defensive
        if crosses < 1.5:
            defensive_score += 30
        elif crosses < 2.5:
            defensive_score += 15

        if key_passes < 0.5:
            defensive_score += 25
        elif key_passes < 0.8:
            defensive_score += 12

        if xA_per_90 < 0.04:
            defensive_score += 20

        # INVERTED (Zinchenko, Cucurella)
        # Key characteristic: HIGH progressive passes BUT LOW crosses
        # They tuck into midfield rather than bombing down the wing
        if progressive_passes >= 6.0:
            inverted_score += 50
        elif progressive_passes >= 4.5:
            inverted_score += 35
        elif progressive_passes >= 3.0:
            inverted_score += 18

        if pass_completion >= 90:
            inverted_score += 35
        elif pass_completion >= 86:
            inverted_score += 20

        # Key indicator: low crosses + high progressive passes
        if crosses < 2.0 and progressive_passes >= 4.0:
            inverted_score += 40
        elif crosses < 2.5 and progressive_passes >= 3.0:
            inverted_score += 20

        # PENALTIES: High crosses = NOT inverted (they're attacking wingbacks)
        # Hakimi, TAA cross a LOT - they're not inverted
        if crosses >= 3.5:
            inverted_score -= 50  # Heavy penalty - clearly attacking
        elif crosses >= 2.5:
            inverted_score -= 30  # Moderate penalty
        elif crosses >= 2.0:
            inverted_score -= 15  # Light penalty

        # BALANCED (Cancelo, Theo)
        # Calculate balance ratio
        off_metrics = crosses + key_passes * 2 + xA_per_90 * 50
        def_metrics = tackles + interceptions * 1.5

        if off_metrics > 0 and def_metrics > 0:
            balance_ratio = min(off_metrics, def_metrics) / max(off_metrics, def_metrics)
            if balance_ratio >= 0.5:
                balanced_score += 45
            elif balance_ratio >= 0.35:
                balanced_score += 30
            elif balance_ratio >= 0.25:
                balanced_score += 15

        if 2.0 <= crosses <= 4.5:
            balanced_score += 25
        if 1.5 <= tackles <= 3.0:
            balanced_score += 25
        if 0.05 <= xA_per_90 <= 0.15:
            balanced_score += 20

        scores = {"ATTACKING": attacking_score, "BALANCED": balanced_score, "DEFENSIVE": defensive_score, "INVERTED": inverted_score}

    # Determine winner
    best_sub_role = max(scores, key=scores.get)
    max_score = scores[best_sub_role]
    total_score = sum(scores.values())

    if total_score > 0:
        confidence = min(1.0, (max_score / total_score) + 0.3)
    else:
        confidence = 0.5

    return best_sub_role, round(confidence, 2)


def calculate_absence_shock(player: Dict, minutes_90: float, primary_role: str, sub_role: str) -> Dict:
    """Calculate ABSENCE SHOCK impact for a defender"""

    # Get key metrics
    fbref = player.get('fbref', {})
    aerial = fbref.get('aerial', {})
    aerials_won = float(aerial.get('aerials_won', 0) or 0)
    aerials_won_per_90 = aerials_won / minutes_90 if minutes_90 > 0 else 0

    tackles = get_per_90_stat(player, 'tackles', minutes_90)
    interceptions = get_per_90_stat(player, 'interceptions', minutes_90)
    clearances = get_per_90_stat(player, 'clearances', minutes_90)
    crosses = get_per_90_stat(player, 'crosses', minutes_90)
    key_passes = get_per_90_stat(player, 'key_passes', minutes_90)
    xA_per_90 = get_xA_per_90(player, minutes_90)
    progressive_passes = get_per_90_stat(player, 'progressive_passes', minutes_90)

    # Calculate dependency score (0-100)
    dependency_score = 0

    if primary_role == "CENTRAL":
        # Defensive impact
        dependency_score += min(aerials_won_per_90 * 10, 30)
        dependency_score += min(tackles * 8, 20)
        dependency_score += min(interceptions * 10, 25)
        dependency_score += min(clearances * 5, 15)
        dependency_score += 10  # Base for starter

    else:  # WIDE
        if sub_role == "ATTACKING":
            # Offensive impact dominates
            dependency_score += min(crosses * 6, 20)
            dependency_score += min(key_passes * 12, 25)
            dependency_score += min(xA_per_90 * 250, 35)
            dependency_score += min(tackles * 3, 10)
        elif sub_role == "DEFENSIVE":
            # Defensive impact dominates
            dependency_score += min(tackles * 10, 30)
            dependency_score += min(interceptions * 12, 30)
            dependency_score += 15
        elif sub_role == "INVERTED":
            # Possession/build-up impact
            dependency_score += min(progressive_passes * 5, 25)
            dependency_score += min(tackles * 5, 15)
            dependency_score += min(interceptions * 6, 15)
            dependency_score += 15
        else:  # BALANCED
            # Mixed impact
            dependency_score += min(crosses * 5, 18)
            dependency_score += min(xA_per_90 * 150, 22)
            dependency_score += min(tackles * 6, 18)
            dependency_score += min(interceptions * 6, 15)
            dependency_score += 10

    dependency_score = min(100, max(0, dependency_score))

    # Dependency profile
    if dependency_score >= 80:
        dependency_profile = "CRITICAL"
    elif dependency_score >= 60:
        dependency_profile = "HIGH"
    elif dependency_score >= 40:
        dependency_profile = "MEDIUM"
    else:
        dependency_profile = "LOW"

    # Get impact from config
    sub_role_config = SUB_ROLE_CONFIG.get(primary_role, {}).get(sub_role, {})
    impact_if_absent = sub_role_config.get("absence_impact", {})

    # Betting actions when absent
    betting_when_absent = []

    if primary_role == "CENTRAL":
        betting_when_absent.append({
            "action": "LAY",
            "market": "clean_sheet",
            "confidence": "HIGH" if dependency_score >= 70 else "MEDIUM"
        })
        if sub_role == "DOMINANT":
            betting_when_absent.append({
                "action": "BACK",
                "market": "opponent_header_goal",
                "confidence": "MEDIUM"
            })
    else:  # WIDE
        if sub_role == "ATTACKING":
            betting_when_absent.append({
                "action": "BACK",
                "market": "under_team_goals",
                "confidence": "MEDIUM" if dependency_score >= 60 else "LOW"
            })
            betting_when_absent.append({
                "action": "LAY",
                "market": "team_win",
                "confidence": "LOW"
            })
        elif sub_role == "DEFENSIVE":
            betting_when_absent.append({
                "action": "LAY",
                "market": "clean_sheet",
                "confidence": "MEDIUM"
            })
            betting_when_absent.append({
                "action": "BACK",
                "market": "opponent_goals",
                "confidence": "LOW"
            })

    return {
        "dependency_score": round(dependency_score),
        "dependency_profile": dependency_profile,
        "impact_if_absent": impact_if_absent,
        "betting_when_absent": betting_when_absent
    }


def generate_betting_hints(player: Dict, minutes_90: float, primary_role: str, sub_role: str) -> Dict:
    """Generate betting hints for a defender"""

    boosts = []
    warnings = []

    # Get metrics
    fbref = player.get('fbref', {})
    aerial = fbref.get('aerial', {})
    aerials_won = float(aerial.get('aerials_won', 0) or 0)
    aerials_won_per_90 = aerials_won / minutes_90 if minutes_90 > 0 else 0

    tackles = get_per_90_stat(player, 'tackles', minutes_90)
    crosses = get_per_90_stat(player, 'crosses', minutes_90)
    xA_per_90 = get_xA_per_90(player, minutes_90)
    progressive_passes = get_per_90_stat(player, 'progressive_passes', minutes_90)

    # Goals
    impact = player.get('impact', {}) or {}
    goals = float(impact.get('goals', 0) or 0)
    goals_per_90 = goals / minutes_90 if minutes_90 > 0 else 0

    # Discipline
    discipline = fbref.get('discipline', {})
    fouls = float(discipline.get('fouls', 0) or 0)
    fouls_per_90 = fouls / minutes_90 if minutes_90 > 0 else 0
    cards_yellow = float(discipline.get('yellow_cards', 0) or 0)

    # Boosts by profile
    if primary_role == "CENTRAL":
        if aerials_won_per_90 >= 3.5:
            boosts.append("BACK corner goal vs weak aerial team")
            boosts.append("BACK first goal from set piece")
        if sub_role == "BALL_PLAYING":
            boosts.append("BACK team possession over")
        if sub_role == "DOMINANT":
            boosts.append("BACK clean sheet vs non-aerial team")
        if sub_role == "STOPPER":
            boosts.append("Aggressive defender - impact on duels won")

    else:  # WIDE
        if sub_role == "ATTACKING":
            if xA_per_90 >= 0.12:
                boosts.append("BACK anytime assist (high xA)")
            if crosses >= 4.5:
                boosts.append("BACK crosses completed over")
            if goals_per_90 >= 0.08:
                boosts.append("BACK anytime goalscorer (high odds value)")
            boosts.append("Flanc créatif - boost team goals over")
        elif sub_role == "DEFENSIVE":
            boosts.append("BACK clean sheet vs wingerless opponent")
            boosts.append("1v1 defensive specialist")
        elif sub_role == "INVERTED":
            boosts.append("BACK team possession over (midfield overload)")
            if progressive_passes >= 5.0:
                boosts.append("Build-up specialist - ball progression")
        else:  # BALANCED
            boosts.append("Versatile threat - both attack and defense")
            if xA_per_90 >= 0.08:
                boosts.append("BACK assists market")

    # Warnings
    if fouls_per_90 >= 1.5:
        warnings.append(f"High card risk ({fouls_per_90:.1f} fouls/90)")
    if cards_yellow >= 4:
        warnings.append(f"{int(cards_yellow)} yellow cards - suspension risk")
    if primary_role == "WIDE" and sub_role == "ATTACKING":
        warnings.append("Flank exposed defensively - BTTS risk")

    return {
        "boosts": boosts[:5],
        "warnings": warnings[:3]
    }


def create_defender_profile(name: str, player: Dict) -> Optional[Dict]:
    """Create a complete profile for a defender"""

    # Check position
    meta = player.get('meta', {})
    fbref = player.get('fbref', {})
    position = meta.get('position', '') or fbref.get('position', player.get('position', ''))

    pos_upper = str(position).upper()
    is_defender = False

    for def_pos in DEFENDER_POSITIONS:
        if position == def_pos or pos_upper == def_pos.upper():
            is_defender = True
            break

    # Also check mixed positions
    if not is_defender:
        if any(p in pos_upper for p in ['D ', ' D', 'DF', 'CB', 'RB', 'LB', 'WB', 'FB']):
            is_defender = True

    if not is_defender:
        return None

    # Minutes played
    impact = player.get('impact', {}) or {}
    time_played = float(impact.get('time', 0) or 0)
    minutes_90 = time_played / 90 if time_played > 0 else 0

    if minutes_90 == 0:
        derived = fbref.get('derived', {})
        if derived and 'tackles_90' in derived:
            defense = fbref.get('defense', {})
            tackles = float(defense.get('tackles', 0) or 0)
            tackles_90 = float(derived.get('tackles_90', 0) or 0)
            if tackles_90 > 0:
                minutes_90 = tackles / tackles_90

    # Minimum 3 matches
    if minutes_90 < 3.0:
        return None

    # Classification
    primary_role, sub_role, confidence = classify_defender_role(player, minutes_90)

    # Team info
    team = meta.get('team', '') or fbref.get('team', player.get('team', 'Unknown'))
    league = meta.get('league', '') or fbref.get('league', player.get('league', 'Unknown'))

    # Defensive metrics
    tackles = get_per_90_stat(player, 'tackles', minutes_90)
    interceptions = get_per_90_stat(player, 'interceptions', minutes_90)
    clearances = get_per_90_stat(player, 'clearances', minutes_90)
    blocks = get_per_90_stat(player, 'blocks', minutes_90)

    # Aerial
    aerial = fbref.get('aerial', {})
    aerials_won = float(aerial.get('aerials_won', 0) or 0)
    aerials_lost = float(aerial.get('aerials_lost', 0) or 0)
    aerials_won_per_90 = aerials_won / minutes_90 if minutes_90 > 0 else 0
    aerial_win_pct = aerials_won / (aerials_won + aerials_lost) * 100 if (aerials_won + aerials_lost) > 0 else 0

    # Offensive metrics
    crosses = get_per_90_stat(player, 'crosses', minutes_90)
    key_passes = get_per_90_stat(player, 'key_passes', minutes_90)
    progressive_passes = get_per_90_stat(player, 'progressive_passes', minutes_90)
    progressive_carries = get_per_90_stat(player, 'progressive_carries', minutes_90)
    xA_per_90 = get_xA_per_90(player, minutes_90)

    # Pass completion
    passing = fbref.get('passing', {})
    pass_completion = float(passing.get('pass_completion_pct', 0) or 0)

    # Discipline
    discipline = fbref.get('discipline', {})
    fouls = float(discipline.get('fouls', 0) or 0)
    fouls_per_90 = fouls / minutes_90 if minutes_90 > 0 else 0
    cards_yellow = float(discipline.get('yellow_cards', 0) or 0)
    cards_red = float(discipline.get('red_cards', 0) or 0)

    discipline_risk = "LOW"
    if fouls_per_90 >= 2.0 or cards_yellow >= 5:
        discipline_risk = "HIGH"
    elif fouls_per_90 >= 1.2 or cards_yellow >= 3:
        discipline_risk = "MEDIUM"

    # Absence shock
    absence_shock = calculate_absence_shock(player, minutes_90, primary_role, sub_role)

    # Betting hints
    betting_hints = generate_betting_hints(player, minutes_90, primary_role, sub_role)

    # Get player display name
    display_name = name.split('_')[0].replace('-', ' ').title() if '_' in name else name

    profile = {
        "meta": {
            "name": display_name,
            "team": team,
            "league": league,
            "position": position,
            "primary_role": primary_role,
            "sub_role": sub_role,
            "role_confidence": confidence,
            "minutes_90": round(minutes_90, 1)
        },
        "defensive_metrics": {
            "tackles_per_90": round(tackles, 2),
            "interceptions_per_90": round(interceptions, 2),
            "aerials_won_per_90": round(aerials_won_per_90, 2),
            "aerial_win_pct": round(aerial_win_pct, 1),
            "clearances_per_90": round(clearances, 2),
            "blocks_per_90": round(blocks, 2)
        },
        "offensive_metrics": {
            "crosses_per_90": round(crosses, 2),
            "key_passes_per_90": round(key_passes, 2),
            "progressive_passes_per_90": round(progressive_passes, 2),
            "progressive_carries_per_90": round(progressive_carries, 2),
            "xA_per_90": round(xA_per_90, 3),
            "pass_completion": round(pass_completion, 1)
        },
        "discipline_profile": {
            "fouls_per_90": round(fouls_per_90, 2),
            "cards_yellow": int(cards_yellow),
            "cards_red": int(cards_red),
            "discipline_risk": discipline_risk
        },
        "absence_shock": absence_shock,
        "betting_hints": betting_hints,
        "sub_role_config": SUB_ROLE_CONFIG.get(primary_role, {}).get(sub_role, {})
    }

    return profile


# ============================================================
# MAIN
# ============================================================

def main():
    logger.info("=" * 70)
    logger.info("DEFENDER BETTING PROFILES V2 - CENTRAL/WIDE STRUCTURE")
    logger.info("=" * 70)

    # Load data
    logger.info(f"Loading {INPUT_FILE}...")
    with open(INPUT_FILE, 'r') as f:
        data = json.load(f)

    players = data.get('players', {})
    logger.info(f"  Loaded: {len(players)} players")

    # Generate profiles
    logger.info("\nGenerating defender profiles...")
    profiles = {}
    stats = {
        "by_primary_role": {},
        "by_sub_role": {},
        "by_league": {},
        "by_dependency": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    }

    for name, player in players.items():
        profile = create_defender_profile(name, player)
        if profile:
            profiles[name] = profile

            # Stats
            primary_role = profile['meta']['primary_role']
            sub_role = profile['meta']['sub_role']
            league = profile['meta']['league']
            dep_profile = profile['absence_shock']['dependency_profile']

            stats["by_primary_role"][primary_role] = stats["by_primary_role"].get(primary_role, 0) + 1

            full_role = f"{primary_role}_{sub_role}"
            stats["by_sub_role"][full_role] = stats["by_sub_role"].get(full_role, 0) + 1

            stats["by_league"][league] = stats["by_league"].get(league, 0) + 1
            stats["by_dependency"][dep_profile] += 1

    logger.info(f"  Generated: {len(profiles)} defender profiles")

    # Output
    output = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_defenders": len(profiles),
            "version": "2.0",
            "paradigm": "TEAM_CENTRIC_ADN_CENTRAL_WIDE"
        },
        "statistics": stats,
        "profiles": profiles
    }

    # Save
    logger.info(f"\nSaving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Total defenders: {len(profiles)}")

    logger.info("\nBy primary role:")
    for role, count in sorted(stats["by_primary_role"].items()):
        pct = count / len(profiles) * 100
        logger.info(f"  {role}: {count} ({pct:.1f}%)")

    logger.info("\nBy sub-role:")
    for role, count in sorted(stats["by_sub_role"].items(), key=lambda x: -x[1]):
        pct = count / len(profiles) * 100
        logger.info(f"  {role}: {count} ({pct:.1f}%)")

    logger.info("\nBy dependency:")
    for dep, count in stats["by_dependency"].items():
        pct = count / len(profiles) * 100 if len(profiles) > 0 else 0
        logger.info(f"  {dep}: {count} ({pct:.1f}%)")

    # Examples
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE PROFILES")
    logger.info("=" * 70)

    examples = ['van dijk', 'alexander-arnold', 'robertson', 'hakimi', 'saliba', 'dias']
    for ex_name in examples:
        for name, profile in profiles.items():
            if ex_name in name.lower():
                m = profile['meta']
                dep = profile['absence_shock']['dependency_score']
                logger.info(f"\n{m['name']} ({m['team']})")
                logger.info(f"  Role: {m['primary_role']}/{m['sub_role']} (conf: {m['role_confidence']})")
                logger.info(f"  Absence Shock: {profile['absence_shock']['dependency_profile']} ({dep})")
                if profile['betting_hints']['boosts']:
                    logger.info(f"  Boost: {profile['betting_hints']['boosts'][0]}")
                break

    logger.info("\n" + "=" * 70)
    logger.info("GENERATION COMPLETE")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
