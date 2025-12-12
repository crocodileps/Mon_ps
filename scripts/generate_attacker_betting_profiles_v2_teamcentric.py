#!/usr/bin/env python3
"""
BETTING PROFILES ATTAQUANTS V2 - PARADIGME ADN TEAM-CENTRIC

L'ÉQUIPE est le TROU NOIR - tout gravite autour
Un joueur N'A PAS de valeur isolée
Sa valeur betting = INTERACTION (Joueur DNA × Équipe DNA)
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import re

# ============================================================================
# FICHIERS
# ============================================================================
PLAYER_DNA_FILE = '/home/Mon_ps/data/quantum_v2/player_dna_unified.json'
TEAM_DNA_FILE = '/home/Mon_ps/data/quantum_v2/team_dna_unified_v2.json'
OUTPUT_FILE = '/home/Mon_ps/data/quantum_v2/player_dna_unified.json'

# ============================================================================
# TEAM NAME NORMALIZER
# ============================================================================
def normalize_team_name(name: str) -> str:
    """Normalise les noms d'équipes pour le matching"""
    if not name:
        return ""

    # Lowercase
    n = name.lower().strip()

    # Mappings courants
    mappings = {
        'ac milan': 'ac milan',
        'milan': 'ac milan',
        'inter milan': 'inter milan',
        'inter': 'inter milan',
        'psg': 'paris saint-germain',
        'paris saint germain': 'paris saint-germain',
        'paris sg': 'paris saint-germain',
        'man city': 'manchester city',
        'man utd': 'manchester united',
        'man united': 'manchester united',
        'spurs': 'tottenham',
        'tottenham hotspur': 'tottenham',
        'wolves': 'wolverhampton',
        'wolverhampton wanderers': 'wolverhampton',
        'atletico': 'atletico madrid',
        'atletico de madrid': 'atletico madrid',
        'real': 'real madrid',
        'barca': 'barcelona',
        'fc barcelona': 'barcelona',
        'bayern': 'bayern munich',
        'fc bayern': 'bayern munich',
        'dortmund': 'borussia dortmund',
        'bvb': 'borussia dortmund',
        'gladbach': 'borussia monchengladbach',
        'mgladbach': 'borussia monchengladbach',
        'rb leipzig': 'rb leipzig',
        'leipzig': 'rb leipzig',
        'leverkusen': 'bayer leverkusen',
        'vfb stuttgart': 'vfb stuttgart',
        'stuttgart': 'vfb stuttgart',
        'as roma': 'as roma',
        'roma': 'as roma',
        'napoli': 'napoli',
        'ssc napoli': 'napoli',
        'juve': 'juventus',
        'ol': 'lyon',
        'olympique lyonnais': 'lyon',
        'om': 'marseille',
        'olympique marseille': 'marseille',
        'asse': 'saint-etienne',
        'st etienne': 'saint-etienne',
    }

    return mappings.get(n, n)


def find_team_in_dna(player_team: str, team_dna: Dict) -> Optional[Dict]:
    """Trouve l'ADN de l'équipe du joueur"""
    if not player_team:
        return None

    player_team_norm = normalize_team_name(player_team)

    # Recherche exacte
    for team_name, team_data in team_dna.items():
        if normalize_team_name(team_name) == player_team_norm:
            return team_data

        # Check aliases
        aliases = team_data.get('meta', {}).get('aliases', [])
        for alias in aliases:
            if normalize_team_name(alias) == player_team_norm:
                return team_data

    # Recherche partielle
    for team_name, team_data in team_dna.items():
        if player_team_norm in normalize_team_name(team_name) or \
           normalize_team_name(team_name) in player_team_norm:
            return team_data

    return None


# ============================================================================
# TEAM CONTEXT EXTRACTION
# ============================================================================
def extract_team_context(team_data: Dict) -> Dict:
    """Extrait le contexte d'équipe pertinent pour le betting"""
    if not team_data:
        return {}

    context = team_data.get('context', {})
    tactical = team_data.get('tactical', {})
    defense = team_data.get('defense', {})
    betting = team_data.get('betting', {})
    exploit = team_data.get('exploit', {})
    defensive_line = team_data.get('defensive_line', {})

    # Record et stats offensives
    record = context.get('record', {})
    history = context.get('history', {})

    # Timing data
    timing = context.get('context_dna', {}).get('timing', {})

    return {
        # Identité
        "team_name": team_data.get('meta', {}).get('canonical_name', 'Unknown'),
        "league": context.get('league', ''),

        # Style offensif
        "attacking_style": history.get('pressing_style', 'UNKNOWN'),
        "xg_90": history.get('xg_90', 1.0),
        "goals_scored": record.get('goals_for', 0),
        "matches": context.get('matches', 0),
        "avg_goals_scored": record.get('goals_for', 0) / max(1, context.get('matches', 1)),

        # Qualité de service (deep completions, passes dans la surface)
        "deep_90": history.get('deep_90', 5.0),
        "ppda": history.get('ppda', 15.0),  # Plus bas = plus pressing

        # Tactical
        "possession_pct": tactical.get('possession_pct', 50),
        "progressive_passes": tactical.get('progressive_passes', 0),
        "passes_penalty_area": tactical.get('passes_penalty_area', 0),

        # Friction multipliers (comment l'équipe résiste aux différents types)
        "friction_multipliers": tactical.get('friction_multipliers', {}),

        # Best markets et betting insights
        "best_markets": betting.get('best_markets', []) or defense.get('best_markets', []),
        "betting_back": betting.get('betting_insights', {}).get('back', []),
        "betting_fade": betting.get('betting_insights', {}).get('fade', []),

        # Timing exploits
        "timing_profile": defense.get('timing_profile', 'NEUTRAL'),
        "early_xg_pct": timing.get('1-15', {}).get('xG', 0) / max(1, history.get('xg', 1)) * 100,
        "late_xg_pct": timing.get('76+', {}).get('xG', 0) / max(1, history.get('xg', 1)) * 100,

        # Set pieces
        "set_piece_threat": 'HIGH' if exploit.get('action_data', {}).get('dangerous_actions', []) and \
                           any('Corner' in a or 'SetPiece' in a for a in exploit.get('action_data', {}).get('dangerous_actions', [])) \
                           else 'MEDIUM',

        # Gamestate behavior
        "gamestate_behavior": tactical.get('gamestate_behavior', 'NEUTRAL'),
        "collapses_when_leading": betting.get('gamestate_insights', {}).get('collapses_when_leading', False),
        "dangerous_when_trailing": betting.get('gamestate_insights', {}).get('dangerous_when_trailing', False),

        # Vulnerabilities pour l'adversaire
        "vulnerabilities": exploit.get('vulnerabilities', []),

        # Variance / Luck
        "xg_overperformance": context.get('variance', {}).get('xg_overperformance', 0),

        # Momentum
        "form_last_5": context.get('momentum_dna', {}).get('form_last_5', ''),
        "points_last_5": context.get('momentum_dna', {}).get('points_last_5', 0),

        # Matchup guide (friction par type de joueur adverse)
        "matchup_guide": tactical.get('matchup_guide', {}) or defense.get('matchup_guide', {}),

        # Defensive line data (pour collision profiles)
        "defensive_line": {
            "resist_global": defense.get('resist_global', 0.5),
            "resist_aerial": defense.get('resist_aerial', 0.5),
            "resist_early": defense.get('resist_early', 0.5),
            "resist_late": defense.get('resist_late', 0.5),
            "resist_set_piece": defense.get('resist_set_piece', 0.5),
            "weaknesses": defense.get('weaknesses', []),
            "strengths": defense.get('strengths', []),
        }
    }


# ============================================================================
# STYLE SYNERGY CALCULATION
# ============================================================================
def calculate_style_synergy(player_style: str, player_secondary_styles: List[str],
                           team_context: Dict) -> Tuple[float, str]:
    """
    Calcule la synergie entre le style du joueur et le style de l'équipe
    Retourne (score 0-1, explication)
    """
    if not player_style or not team_context:
        return 0.5, "No style data"

    attacking_style = team_context.get('attacking_style', 'UNKNOWN')
    possession = team_context.get('possession_pct', 50)
    deep_90 = team_context.get('deep_90', 5.0)
    xg_90 = team_context.get('xg_90', 1.0)

    synergy = 0.5
    reasons = []

    # CLINICAL dans équipe high-possession = haute synergie
    if player_style == 'CLINICAL' or 'CLINICAL' in player_secondary_styles:
        if possession > 55:
            synergy += 0.15
            reasons.append("CLINICAL + high possession")
        if xg_90 > 1.8:
            synergy += 0.1
            reasons.append("CLINICAL + high xG team")

    # POACHER dans équipe contre-attaque = haute synergie
    if player_style == 'POACHER' or 'POACHER' in player_secondary_styles:
        if attacking_style in ['HIGH_PRESS', 'GEGENPRESSING']:
            synergy += 0.15
            reasons.append("POACHER + pressing team")
        if deep_90 > 7:
            synergy += 0.1
            reasons.append("POACHER + deep completions")

    # PLAYMAKER dans équipe possession
    if player_style == 'PLAYMAKER' or 'PLAYMAKER' in player_secondary_styles:
        if possession > 55:
            synergy += 0.12
            reasons.append("PLAYMAKER + possession team")

    # VOLUME_SHOOTER dans équipe offensive
    if player_style == 'VOLUME_SHOOTER' or 'VOLUME_SHOOTER' in player_secondary_styles:
        if xg_90 > 1.8:
            synergy += 0.1
            reasons.append("VOLUME + high xG team")

    # Malus: style inadapté
    if player_style == 'POACHER' and attacking_style == 'LOW_BLOCK':
        synergy -= 0.1
        reasons.append("POACHER in LOW_BLOCK team (-)")

    if player_style == 'CLINICAL' and xg_90 < 1.2:
        synergy -= 0.15
        reasons.append("CLINICAL in low xG team (-)")

    # Cap
    synergy = max(0.1, min(1.0, synergy))

    return synergy, " | ".join(reasons) if reasons else "Average fit"


def calculate_role_importance(player_attacking: Dict, team_context: Dict) -> Tuple[str, float]:
    """
    Détermine l'importance du joueur dans l'équipe
    Retourne (role, boost)
    """
    tier = player_attacking.get('tier', 'LOW')
    goals = player_attacking.get('goals', 0)
    xG = player_attacking.get('xG', 0)
    team_goals = team_context.get('goals_scored', 1)

    # Contribution au scoring
    goal_share = goals / max(1, team_goals)

    if tier == 'ELITE' and goal_share > 0.3:
        return "PRIMARY_FINISHER", 0.15
    elif tier in ['ELITE', 'DANGEROUS'] and goal_share > 0.2:
        return "KEY_SCORER", 0.10
    elif tier in ['DANGEROUS', 'THREAT'] and goal_share > 0.1:
        return "SECONDARY_SCORER", 0.05
    elif player_attacking.get('titularity_factor', 0) > 0.8:
        return "REGULAR_STARTER", 0.02
    else:
        return "ROTATION", -0.05


def calculate_service_quality(team_context: Dict) -> float:
    """
    Calcule la qualité de service (passes vers l'attaquant)
    """
    deep_90 = team_context.get('deep_90', 5.0)
    passes_penalty = team_context.get('passes_penalty_area', 0)
    xg_90 = team_context.get('xg_90', 1.0)

    # Normalisation
    service = 0.5

    if deep_90 > 8:
        service += 0.2
    elif deep_90 > 6:
        service += 0.1
    elif deep_90 < 4:
        service -= 0.1

    if xg_90 > 2.0:
        service += 0.15
    elif xg_90 > 1.5:
        service += 0.08
    elif xg_90 < 1.0:
        service -= 0.15

    return max(0.1, min(1.0, service))


# ============================================================================
# TEAM SYNERGY MARKETS CALCULATION
# ============================================================================
def calculate_team_synergy_markets(
    player_attacking: Dict,
    player_style: Dict,
    team_context: Dict,
    base_profile: Dict
) -> Dict:
    """
    Calcule les marchés avec boost/malus d'équipe
    """
    synergy_markets = []
    team_warnings = []

    if not team_context:
        return {"team_synergy_markets": [], "team_warnings": []}

    # Extraire données
    primary_style = player_style.get('primary_style', '') if player_style else ''
    secondary_styles = player_style.get('secondary_styles', []) if player_style else []
    all_styles = [primary_style] + secondary_styles

    tier = player_attacking.get('tier', 'LOW')
    xg_90 = team_context.get('xg_90', 1.0)
    avg_goals = team_context.get('avg_goals_scored', 1.0)
    best_markets = team_context.get('best_markets', [])
    friction = team_context.get('friction_multipliers', {})
    matchup = team_context.get('matchup_guide', {})

    # ========================================================================
    # 1. ANYTIME_SCORER avec contexte équipe
    # ========================================================================
    if tier in ['ELITE', 'DANGEROUS', 'THREAT']:
        base_conf = base_profile.get('value_indicators', {}).get('xG_diff', 0)
        base_conf = 0.7 if tier == 'ELITE' else 0.6 if tier == 'DANGEROUS' else 0.5

        team_boost = 0.0
        boost_reasons = []

        # Boost si équipe offensive
        if xg_90 > 2.0:
            team_boost += 0.15
            boost_reasons.append(f"HIGH scoring team (xG/90={xg_90:.2f})")
        elif xg_90 > 1.5:
            team_boost += 0.08
            boost_reasons.append(f"Good scoring team (xG/90={xg_90:.2f})")
        elif xg_90 < 1.2:
            team_boost -= 0.15
            boost_reasons.append(f"LOW scoring team (xG/90={xg_90:.2f})")

        # Boost si best_markets contient over_2.5 ou scorer markets
        # best_markets peut être une liste de dicts ou de strings
        def extract_market_name(m):
            if isinstance(m, dict):
                return m.get('market', '').lower()
            return str(m).lower()

        market_names = [extract_market_name(m) for m in best_markets]
        if any('over' in mn or 'btts' in mn or 'scorer' in mn for mn in market_names):
            team_boost += 0.08
            boost_reasons.append("Team favors high-scoring markets")

        # Boost CLINICAL dans matchup_guide favorable
        if 'CLINICAL' in all_styles and matchup.get('CLINICAL', {}).get('friction_multiplier', 1.0) < 0.9:
            team_boost += 0.05
            boost_reasons.append("CLINICAL style amplified by team")

        # Role boost
        role, role_boost = calculate_role_importance(player_attacking, team_context)
        team_boost += role_boost
        if role_boost > 0:
            boost_reasons.append(f"Role: {role}")

        final_conf = min(0.95, max(0.1, base_conf + team_boost))

        synergy_markets.append({
            "market": "anytime_scorer",
            "base_confidence": round(base_conf, 2),
            "team_boost": round(team_boost, 2),
            "final_confidence": round(final_conf, 2),
            "context": " | ".join(boost_reasons) if boost_reasons else "No significant team effect",
            "exploit_conditions": generate_exploit_conditions(team_context, "scorer")
        })

        # Warning si équipe faible
        if xg_90 < 1.2:
            team_warnings.append({
                "market": "anytime_scorer",
                "reason": f"LOW scoring team ({xg_90:.2f} xG/90)",
                "recommendation": "AVOID or wait for odds >3.5"
            })

    # ========================================================================
    # 2. FIRST_SCORER avec timing équipe
    # ========================================================================
    early_xg_pct = team_context.get('early_xg_pct', 15)
    timing_profile = team_context.get('timing_profile', 'NEUTRAL')

    if tier in ['ELITE', 'DANGEROUS'] and player_attacking.get('titularity_factor', 0) > 0.8:
        base_conf = 0.55
        team_boost = 0.0
        boost_reasons = []

        # Équipe qui démarre fort
        if 'EARLY' in timing_profile.upper() or early_xg_pct > 20:
            team_boost += 0.12
            boost_reasons.append(f"Team scores early ({early_xg_pct:.1f}% xG in 0-15)")
        elif early_xg_pct < 10:
            team_boost -= 0.1
            boost_reasons.append(f"Team slow starter ({early_xg_pct:.1f}% xG in 0-15)")

        final_conf = min(0.85, max(0.2, base_conf + team_boost))

        synergy_markets.append({
            "market": "first_scorer",
            "base_confidence": round(base_conf, 2),
            "team_boost": round(team_boost, 2),
            "final_confidence": round(final_conf, 2),
            "context": " | ".join(boost_reasons) if boost_reasons else "Average timing"
        })

        if early_xg_pct < 10:
            team_warnings.append({
                "market": "first_scorer",
                "reason": f"Team slow starter ({early_xg_pct:.1f}% early xG)",
                "recommendation": "AVOID or wait for odds >5.0"
            })

    # ========================================================================
    # 3. ASSIST avec contexte équipe
    # ========================================================================
    if primary_style == 'PLAYMAKER' or 'PLAYMAKER' in secondary_styles:
        xA_90 = player_attacking.get('xA_per_90', 0)
        if xA_90 > 0.2:
            base_conf = 0.5
            team_boost = 0.0
            boost_reasons = []

            # Plus de buts = plus d'assists
            if avg_goals > 2.0:
                team_boost += 0.12
                boost_reasons.append(f"High-scoring team ({avg_goals:.1f} gpg)")

            # Possession team = plus de passes
            if team_context.get('possession_pct', 50) > 55:
                team_boost += 0.08
                boost_reasons.append("Possession-heavy team")

            final_conf = min(0.80, max(0.2, base_conf + team_boost))

            synergy_markets.append({
                "market": "assist",
                "base_confidence": round(base_conf, 2),
                "team_boost": round(team_boost, 2),
                "final_confidence": round(final_conf, 2),
                "context": " | ".join(boost_reasons) if boost_reasons else "Average team fit"
            })

    return {
        "team_synergy_markets": synergy_markets,
        "team_warnings": team_warnings
    }


def generate_exploit_conditions(team_context: Dict, market_type: str) -> List[str]:
    """Génère les conditions d'exploitation optimales"""
    conditions = []

    avg_goals = team_context.get('avg_goals_scored', 1.0)
    form = team_context.get('form_last_5', '')

    # Home advantage
    if avg_goals > 1.5:
        conditions.append("HOME matches (higher conversion)")

    # Form
    if form.count('W') >= 3:
        conditions.append(f"Current good form ({form})")

    # Timing
    timing = team_context.get('timing_profile', '')
    if 'LATE' in timing.upper():
        conditions.append("Consider late goal markets")

    return conditions if conditions else ["Standard conditions apply"]


# ============================================================================
# MAIN BETTING PROFILE GENERATION
# ============================================================================
def generate_team_centric_betting_profile(
    player_attacking: Dict,
    player_style: Dict,
    team_context: Dict,
    player_name: str
) -> Dict:
    """
    Génère le betting_profile complet avec paradigme team-centric
    """
    # Base profile (joueur isolé)
    base_profile = generate_base_profile(player_attacking, player_style)

    if not team_context:
        return {
            "base_profile": base_profile,
            "team_context": None,
            "final_betting_profile": base_profile,
            "paradigm": "isolated",
            "generated_at": datetime.now().isoformat()
        }

    # Calculate synergies
    primary_style = player_style.get('primary_style', '') if player_style else ''
    secondary_styles = player_style.get('secondary_styles', []) if player_style else []

    style_synergy, synergy_reason = calculate_style_synergy(
        primary_style, secondary_styles, team_context
    )

    role, role_boost = calculate_role_importance(player_attacking, team_context)
    service_quality = calculate_service_quality(team_context)

    # Team context object
    team_context_obj = {
        "team_name": team_context.get('team_name', 'Unknown'),
        "league": team_context.get('league', ''),
        "team_dna_fit": round(style_synergy, 2),
        "style_synergy_reason": synergy_reason,
        "role": role,
        "service_quality": round(service_quality, 2),
        "team_xg_90": team_context.get('xg_90', 0),
        "team_avg_goals": round(team_context.get('avg_goals_scored', 0), 2),
        "team_style": team_context.get('attacking_style', 'UNKNOWN'),
        "team_best_markets": team_context.get('best_markets', [])[:5]
    }

    # Calculate team synergy markets
    synergy_data = calculate_team_synergy_markets(
        player_attacking, player_style, team_context, base_profile
    )

    # Build final profile with team adjustments
    final_markets = []
    boosted = []
    nerfed = []

    for sm in synergy_data['team_synergy_markets']:
        market = {
            "market": sm['market'],
            "confidence": sm['final_confidence'],
            "confidence_breakdown": {
                "player_base": sm['base_confidence'],
                "team_synergy": sm['team_boost'],
                "role_boost": role_boost if sm['market'] == 'anytime_scorer' else 0
            },
            "exploit_conditions": sm.get('exploit_conditions', []),
            "context": sm['context']
        }
        final_markets.append(market)

        if sm['team_boost'] > 0.05:
            boosted.append(sm['market'])
        elif sm['team_boost'] < -0.05:
            nerfed.append(sm['market'])

    # Add avoid markets from base
    avoid_markets = base_profile.get('avoid_markets', [])

    # Add team warnings as avoid
    for warn in synergy_data['team_warnings']:
        avoid_markets.append({
            "market": warn['market'],
            "confidence": 0.7,
            "reason": warn['reason'],
            "recommendation": warn['recommendation']
        })

    # Final betting profile
    final_betting_profile = {
        "is_target": len(final_markets) > 0 and any(m['confidence'] > 0.5 for m in final_markets),
        "is_avoid": len(avoid_markets) > 0,
        "target_markets": final_markets,
        "avoid_markets": avoid_markets,
        "value_indicators": base_profile.get('value_indicators', {})
    }

    return {
        "base_profile": base_profile,
        "team_context": team_context_obj,
        "player_fit": {
            "style_synergy": round(style_synergy, 2),
            "role_importance": role,
            "service_quality": round(service_quality, 2)
        },
        "team_synergy_markets": synergy_data['team_synergy_markets'],
        "team_warnings": synergy_data['team_warnings'],
        "boosted_markets": boosted,
        "nerfed_markets": nerfed,
        "final_betting_profile": final_betting_profile,
        "paradigm": "team_centric",
        "generated_at": datetime.now().isoformat()
    }


def generate_base_profile(attacking: Dict, style: Dict) -> Dict:
    """Génère le profil de base (joueur isolé)"""
    tier = attacking.get('tier', 'LOW')
    xG_diff = attacking.get('xG_diff', 0)
    goals = attacking.get('goals', 0)
    xG = attacking.get('xG', 0)
    conversion = goals / xG if xG > 0 else 1.0

    primary_style = style.get('primary_style', '') if style else ''

    target_markets = []
    avoid_markets = []

    # Base anytime_scorer
    if tier in ['ELITE', 'DANGEROUS', 'THREAT']:
        target_markets.append({
            "market": "anytime_scorer",
            "confidence": 0.7 if tier == 'ELITE' else 0.6 if tier == 'DANGEROUS' else 0.5,
            "reason": f"tier={tier}"
        })

    # Avoid if low tier + underperforming
    if tier == 'LOW' and xG_diff < -0.5:
        avoid_markets.append({
            "market": "anytime_scorer",
            "confidence": 0.7,
            "reason": f"tier=LOW + xG_diff={xG_diff:.2f}"
        })

    return {
        "is_target": len(target_markets) > 0,
        "is_avoid": len(avoid_markets) > 0,
        "target_markets": target_markets,
        "avoid_markets": avoid_markets,
        "value_indicators": {
            "tier": tier,
            "style": primary_style,
            "xG_diff": round(xG_diff, 2),
            "conversion": round(conversion, 2),
            "goals": goals
        }
    }


# ============================================================================
# MAIN
# ============================================================================
def main():
    print("=" * 70)
    print("GÉNÉRATION BETTING PROFILES V2 - PARADIGME TEAM-CENTRIC")
    print("=" * 70)

    # Charger les données
    print("\n📂 Chargement des données...")
    with open(PLAYER_DNA_FILE, 'r', encoding='utf-8') as f:
        player_data = json.load(f)

    with open(TEAM_DNA_FILE, 'r', encoding='utf-8') as f:
        team_data = json.load(f)

    players = player_data['players']
    teams = team_data['teams']

    print(f"   Joueurs: {len(players)}")
    print(f"   Équipes: {len(teams)}")

    # Stats
    stats = {
        'total': 0,
        'with_team': 0,
        'without_team': 0,
        'target': 0,
        'avoid': 0,
        'by_tier': defaultdict(lambda: {'total': 0, 'boosted': 0, 'nerfed': 0}),
        'by_team_effect': defaultdict(list),
        'synergy_scores': [],
        'top_synergy': [],
        'low_scoring_teams': [],
        'high_scoring_teams': []
    }

    # Process
    print("\n🔄 Génération des betting_profiles team-centric...")

    for player_name, pdata in players.items():
        attacking = pdata.get('attacking')
        style = pdata.get('style')

        if not attacking or not isinstance(attacking, dict) or not attacking.get('tier'):
            continue

        stats['total'] += 1
        tier = attacking.get('tier', 'LOW')
        stats['by_tier'][tier]['total'] += 1

        # Find team DNA
        player_team = pdata.get('meta', {}).get('team', '')
        team_dna = find_team_in_dna(player_team, teams)

        if team_dna:
            stats['with_team'] += 1
            team_context = extract_team_context(team_dna)
        else:
            stats['without_team'] += 1
            team_context = None

        # Generate profile
        betting_profile = generate_team_centric_betting_profile(
            attacking,
            style if style and isinstance(style, dict) else {},
            team_context,
            player_name
        )

        # Store
        pdata['attacking']['betting_profile'] = betting_profile

        # Stats
        if betting_profile['final_betting_profile']['is_target']:
            stats['target'] += 1
        if betting_profile['final_betting_profile']['is_avoid']:
            stats['avoid'] += 1

        # Track boosted/nerfed
        if betting_profile.get('boosted_markets'):
            stats['by_tier'][tier]['boosted'] += 1
        if betting_profile.get('nerfed_markets'):
            stats['by_tier'][tier]['nerfed'] += 1

        # Track synergy
        if team_context:
            synergy = betting_profile.get('player_fit', {}).get('style_synergy', 0.5)
            team_name = team_context.get('team_name', 'Unknown')
            stats['synergy_scores'].append({
                'player': player_name,
                'team': team_name,
                'synergy': synergy,
                'tier': tier,
                'role': betting_profile.get('player_fit', {}).get('role_importance', ''),
                'xg_90': team_context.get('xg_90', 0)
            })

            # Track team effects
            stats['by_team_effect'][team_name].append({
                'player': player_name,
                'synergy': synergy,
                'tier': tier
            })

    # Calculate top/bottom teams
    team_avg_synergy = {}
    for team, players_list in stats['by_team_effect'].items():
        if len(players_list) >= 2:
            avg_syn = sum(p['synergy'] for p in players_list) / len(players_list)
            team_avg_synergy[team] = {
                'avg_synergy': avg_syn,
                'num_players': len(players_list),
                'players': players_list
            }

    # Update metadata
    player_data['metadata']['betting_profiles']['attacker_stats_v2'] = {
        'version': '2.0_team_centric',
        'generated_at': datetime.now().isoformat(),
        'total': stats['total'],
        'with_team_context': stats['with_team'],
        'without_team_context': stats['without_team'],
        'is_target': stats['target'],
        'is_avoid': stats['avoid'],
        'by_tier': {k: dict(v) for k, v in stats['by_tier'].items()}
    }

    # Save
    print("\n💾 Sauvegarde...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(player_data, f, indent=2, ensure_ascii=False)

    # Display stats
    print("\n" + "=" * 70)
    print("📊 STATISTIQUES TEAM-CENTRIC")
    print("=" * 70)

    print(f"\n⚽ ATTAQUANTS ANALYSÉS: {stats['total']}")
    print(f"   ├── Avec contexte équipe: {stats['with_team']} ({stats['with_team']/stats['total']*100:.1f}%)")
    print(f"   ├── Sans contexte équipe: {stats['without_team']}")
    print(f"   ├── TARGET: {stats['target']} ({stats['target']/stats['total']*100:.1f}%)")
    print(f"   └── AVOID: {stats['avoid']} ({stats['avoid']/stats['total']*100:.1f}%)")

    print(f"\n📈 PAR TIER (Boosted/Nerfed par équipe):")
    for tier in ['ELITE', 'DANGEROUS', 'THREAT', 'AVERAGE', 'LOW']:
        t = stats['by_tier'].get(tier, {'total': 0, 'boosted': 0, 'nerfed': 0})
        if t['total'] > 0:
            boost_pct = t['boosted']/t['total']*100
            nerf_pct = t['nerfed']/t['total']*100
            print(f"   {tier:10} │ {t['total']:4} │ Boosted: {t['boosted']:3} ({boost_pct:5.1f}%) │ Nerfed: {t['nerfed']:3} ({nerf_pct:5.1f}%)")

    # Top synergy players
    print(f"\n🔥 TOP 15 SYNERGIE JOUEUR × ÉQUIPE:")
    sorted_synergy = sorted(stats['synergy_scores'], key=lambda x: -x['synergy'])
    for p in sorted_synergy[:15]:
        print(f"   {p['player'].title()[:30]:30} │ {p['team']:20} │ Syn: {p['synergy']:.2f} │ {p['tier']} │ xG/90: {p['xg_90']:.2f}")

    # Teams with best effects
    print(f"\n🏟️ ÉQUIPES OÙ LES ATTAQUANTS ONT LE PLUS DE VALUE:")
    sorted_teams = sorted(team_avg_synergy.items(), key=lambda x: -x[1]['avg_synergy'])
    for team, data in sorted_teams[:10]:
        print(f"   {team:25} │ Avg Synergy: {data['avg_synergy']:.2f} │ {data['num_players']} attackers")

    # Teams where attackers are nerfed
    print(f"\n⚠️ ÉQUIPES OÙ MÊME LES BONS ATTAQUANTS SONT AVOID:")
    for team, data in sorted_teams[-10:]:
        print(f"   {team:25} │ Avg Synergy: {data['avg_synergy']:.2f} │ {data['num_players']} attackers")

    print("\n" + "=" * 70)
    print("✅ GÉNÉRATION TEAM-CENTRIC TERMINÉE")
    print("=" * 70)

    return stats


if __name__ == '__main__':
    main()
