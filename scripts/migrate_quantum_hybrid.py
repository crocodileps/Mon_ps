#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║           MIGRATION QUANTUM HYBRID SYSTEM V1.0                                ║
║                                                                               ║
║  Migre les 20 scénarios + 44 stratégies vers PostgreSQL                      ║
║  Source: scenarios_definitions.py + audit_quant_2.0_FINAL_GRANULAIRE.py      ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import psycopg2
from psycopg2.extras import Json
from datetime import datetime
import json

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

# ═══════════════════════════════════════════════════════════════════════════════
# LES 20 SCÉNARIOS
# ═══════════════════════════════════════════════════════════════════════════════

SCENARIOS = [
    # GROUPE A: TACTIQUES (5)
    {
        "scenario_code": "TOTAL_CHAOS",
        "scenario_name": "Total Chaos",
        "category": "TACTICAL",
        "emoji": "🌪️",
        "description": "Deux équipes à haute intensité avec défenses fragiles. Festival de buts attendu.",
        "conditions": {
            "pace_factor_combined": {">": 140},
            "xg_combined": {">": 3.2},
            "defensive_solidity_combined": {"<": 65}
        },
        "primary_markets": ["over_35", "first_half_over_15"],
        "secondary_markets": ["btts_yes"],
        "avoid_markets": ["under_25", "home_clean_sheet", "away_clean_sheet"],
        "historical_roi": 15.2,
        "historical_win_rate": 68.5,
        "min_confidence_threshold": 65
    },
    {
        "scenario_code": "THE_SIEGE",
        "scenario_name": "The Siege",
        "category": "TACTICAL",
        "emoji": "🏰",
        "description": "Une équipe domine la possession contre un bloc bas. Victoire difficile.",
        "conditions": {
            "possession_gap": {">": 18},
            "control_index_dominant": {">": 72},
            "underdog_block_low": {"==": 1}
        },
        "primary_markets": ["corners_over_105"],
        "secondary_markets": ["under_25"],
        "avoid_markets": ["over_35", "btts_yes"],
        "historical_roi": 10.5,
        "historical_win_rate": 62.0,
        "min_confidence_threshold": 60
    },
    {
        "scenario_code": "SNIPER_DUEL",
        "scenario_name": "Sniper Duel",
        "category": "TACTICAL",
        "emoji": "🔫",
        "description": "Deux équipes très létales. Chaque occasion peut finir au fond.",
        "conditions": {
            "sniper_index_home": {">": 68},
            "sniper_index_away": {">": 68},
            "shots_on_target_combined": {">": 10}
        },
        "primary_markets": ["btts_yes"],
        "secondary_markets": ["over_25"],
        "avoid_markets": ["home_clean_sheet", "away_clean_sheet", "under_15"],
        "historical_roi": 13.8,
        "historical_win_rate": 71.0,
        "min_confidence_threshold": 65
    },
    {
        "scenario_code": "ATTRITION_WAR",
        "scenario_name": "Attrition War",
        "category": "TACTICAL",
        "emoji": "💤",
        "description": "Deux équipes défensives. Match fermé attendu.",
        "conditions": {
            "defensive_solidity_combined": {">": 140},
            "xg_combined": {"<": 2.0},
            "pace_factor_combined": {"<": 90}
        },
        "primary_markets": ["under_25", "btts_no"],
        "secondary_markets": ["under_35"],
        "avoid_markets": ["over_25", "over_35", "btts_yes"],
        "historical_roi": 11.2,
        "historical_win_rate": 64.0,
        "min_confidence_threshold": 60
    },
    {
        "scenario_code": "GLASS_CANNON",
        "scenario_name": "Glass Cannon",
        "category": "TACTICAL",
        "emoji": "🃏",
        "description": "Une équipe très offensive mais fragile défensivement.",
        "conditions": {
            "attack_defense_imbalance": {">": 25},
            "xg_for_high": {">": 2.0},
            "xg_against_high": {">": 1.5}
        },
        "primary_markets": ["btts_yes", "over_25"],
        "secondary_markets": ["over_35"],
        "avoid_markets": ["clean_sheet"],
        "historical_roi": 12.5,
        "historical_win_rate": 66.0,
        "min_confidence_threshold": 62
    },
    
    # GROUPE B: TEMPORELS (4)
    {
        "scenario_code": "LATE_PUNISHMENT",
        "scenario_name": "Late Punishment",
        "category": "TEMPORAL",
        "emoji": "⏰",
        "description": "Équipe qui marque tard contre adversaire qui s'effondre en fin de match.",
        "conditions": {
            "home_late_goals_pct": {">": 35},
            "away_goals_conceded_75_90": {">": 0.4}
        },
        "primary_markets": ["goal_75_90", "home_win"],
        "secondary_markets": ["over_25"],
        "avoid_markets": [],
        "historical_roi": 14.5,
        "historical_win_rate": 67.0,
        "min_confidence_threshold": 65
    },
    {
        "scenario_code": "EXPLOSIVE_START",
        "scenario_name": "Explosive Start",
        "category": "TEMPORAL",
        "emoji": "🚀",
        "description": "Deux équipes qui démarrent fort. Buts rapides attendus.",
        "conditions": {
            "first_15_goals_combined": {">": 0.8},
            "sprinter_factor_combined": {">": 120}
        },
        "primary_markets": ["first_half_over_15", "goal_before_30"],
        "secondary_markets": ["over_25"],
        "avoid_markets": ["under_15_ht"],
        "historical_roi": 11.8,
        "historical_win_rate": 63.0,
        "min_confidence_threshold": 60
    },
    {
        "scenario_code": "DIESEL_DUEL",
        "scenario_name": "Diesel Duel",
        "category": "TEMPORAL",
        "emoji": "🐢",
        "description": "Deux équipes qui montent en puissance. Second half décisif.",
        "conditions": {
            "diesel_factor_home": {">": 0.6},
            "diesel_factor_away": {">": 0.6}
        },
        "primary_markets": ["second_half_over_15", "over_25"],
        "secondary_markets": ["goal_75_90"],
        "avoid_markets": ["first_half_over_15"],
        "historical_roi": 10.2,
        "historical_win_rate": 61.0,
        "min_confidence_threshold": 58
    },
    {
        "scenario_code": "CLUTCH_KILLER",
        "scenario_name": "Clutch Killer",
        "category": "TEMPORAL",
        "emoji": "⚡",
        "description": "Équipe avec instinct de tueur en fin de match.",
        "conditions": {
            "killer_instinct": {">": 75},
            "goals_75_90_pct": {">": 25}
        },
        "primary_markets": ["goal_75_90", "team_over_15"],
        "secondary_markets": ["over_25"],
        "avoid_markets": [],
        "historical_roi": 13.2,
        "historical_win_rate": 65.0,
        "min_confidence_threshold": 63
    },
    
    # GROUPE C: PHYSIQUES (4)
    {
        "scenario_code": "FATIGUE_COLLAPSE",
        "scenario_name": "Fatigue Collapse",
        "category": "PHYSICAL",
        "emoji": "😰",
        "description": "Équipe fatiguée (3 matchs en 7 jours) contre équipe reposée.",
        "conditions": {
            "fatigue_index_gap": {">": 30},
            "matches_last_7_days_diff": {">": 2}
        },
        "primary_markets": ["away_win", "second_half_goals"],
        "secondary_markets": ["over_25"],
        "avoid_markets": [],
        "historical_roi": 15.8,
        "historical_win_rate": 58.0,
        "min_confidence_threshold": 55
    },
    {
        "scenario_code": "PRESSING_DEATH",
        "scenario_name": "Pressing Death",
        "category": "PHYSICAL",
        "emoji": "💪",
        "description": "Équipe à pressing intense contre équipe qui ne supporte pas.",
        "conditions": {
            "pressing_intensity_home": {">": 75},
            "pressing_resistance_away": {"<": 40}
        },
        "primary_markets": ["home_win", "over_25"],
        "secondary_markets": ["home_over_15"],
        "avoid_markets": ["away_win"],
        "historical_roi": 12.1,
        "historical_win_rate": 64.0,
        "min_confidence_threshold": 62
    },
    {
        "scenario_code": "PACE_EXPLOITATION",
        "scenario_name": "Pace Exploitation",
        "category": "PHYSICAL",
        "emoji": "🏃",
        "description": "Équipe rapide contre défense lente. Contre-attaques létales.",
        "conditions": {
            "pace_differential": {">": 20},
            "counter_attack_efficiency": {">": 65}
        },
        "primary_markets": ["over_25", "btts_yes"],
        "secondary_markets": ["team_over_15"],
        "avoid_markets": ["under_25"],
        "historical_roi": 11.5,
        "historical_win_rate": 62.0,
        "min_confidence_threshold": 60
    },
    {
        "scenario_code": "BENCH_WARFARE",
        "scenario_name": "Bench Warfare",
        "category": "PHYSICAL",
        "emoji": "��",
        "description": "Banc profond vs banc faible. Impact des remplaçants décisif.",
        "conditions": {
            "bench_quality_gap": {">": 25},
            "sub_impact_differential": {">": 0.3}
        },
        "primary_markets": ["second_half_winner", "goal_75_90"],
        "secondary_markets": ["over_25"],
        "avoid_markets": [],
        "historical_roi": 9.8,
        "historical_win_rate": 59.0,
        "min_confidence_threshold": 55
    },
    
    # GROUPE D: PSYCHOLOGIQUES (4)
    {
        "scenario_code": "CONSERVATIVE_WALL",
        "scenario_name": "Conservative Wall",
        "category": "PSYCHOLOGICAL",
        "emoji": "🧊",
        "description": "Équipe qui protège son avance ou joue pour le nul.",
        "conditions": {
            "conservative_tendency": {">": 70},
            "lead_protection_rate": {">": 80}
        },
        "primary_markets": ["under_25", "btts_no"],
        "secondary_markets": ["draw"],
        "avoid_markets": ["over_35", "btts_yes"],
        "historical_roi": 10.8,
        "historical_win_rate": 63.0,
        "min_confidence_threshold": 60
    },
    {
        "scenario_code": "KILLER_INSTINCT",
        "scenario_name": "Killer Instinct",
        "category": "PSYCHOLOGICAL",
        "emoji": "🔥",
        "description": "Équipe avec mental de tueur. Finit toujours le travail.",
        "conditions": {
            "killer_instinct": {">": 80},
            "win_when_leading_ht": {">": 90}
        },
        "primary_markets": ["home_win", "team_over_15"],
        "secondary_markets": ["over_25"],
        "avoid_markets": ["draw"],
        "historical_roi": 14.2,
        "historical_win_rate": 68.0,
        "min_confidence_threshold": 65
    },
    {
        "scenario_code": "COLLAPSE_ALERT",
        "scenario_name": "Collapse Alert",
        "category": "PSYCHOLOGICAL",
        "emoji": "😱",
        "description": "Équipe qui craque sous pression. Mental fragile.",
        "conditions": {
            "panic_factor": {">": 60},
            "points_lost_from_winning": {">": 8}
        },
        "primary_markets": ["btts_yes", "draw"],
        "secondary_markets": ["over_25"],
        "avoid_markets": ["team_win"],
        "historical_roi": 11.5,
        "historical_win_rate": 60.0,
        "min_confidence_threshold": 58
    },
    {
        "scenario_code": "NOTHING_TO_LOSE",
        "scenario_name": "Nothing to Lose",
        "category": "PSYCHOLOGICAL",
        "emoji": "💎",
        "description": "Équipe reléguable libérée contre favori. Upset potentiel.",
        "conditions": {
            "relegation_battle": {"==": 1},
            "underdog_motivation": {">": 80}
        },
        "primary_markets": ["draw_no_bet_away", "over_25"],
        "secondary_markets": ["btts_yes"],
        "avoid_markets": ["home_win_handicap"],
        "historical_roi": 18.5,
        "historical_win_rate": 52.0,
        "min_confidence_threshold": 50
    },
    
    # GROUPE E: NEMESIS (3)
    {
        "scenario_code": "NEMESIS_TRAP",
        "scenario_name": "Nemesis Trap",
        "category": "NEMESIS",
        "emoji": "🎯",
        "description": "Adversaire historique. Matchup défavorable malgré les stats.",
        "conditions": {
            "h2h_dominance": {">": 70},
            "psychological_edge": {">": 60}
        },
        "primary_markets": ["h2h_favorite_win"],
        "secondary_markets": ["btts_yes"],
        "avoid_markets": ["h2h_underdog_win"],
        "historical_roi": 12.8,
        "historical_win_rate": 64.0,
        "min_confidence_threshold": 62
    },
    {
        "scenario_code": "PREY_HUNT",
        "scenario_name": "Prey Hunt",
        "category": "NEMESIS",
        "emoji": "🦅",
        "description": "Équipe qui domine toujours cet adversaire spécifique.",
        "conditions": {
            "h2h_win_rate": {">": 75},
            "h2h_goals_scored_avg": {">": 2.0}
        },
        "primary_markets": ["favorite_win", "favorite_over_15"],
        "secondary_markets": ["over_25"],
        "avoid_markets": ["underdog_win"],
        "historical_roi": 13.5,
        "historical_win_rate": 66.0,
        "min_confidence_threshold": 63
    },
    {
        "scenario_code": "AERIAL_RAID",
        "scenario_name": "Aerial Raid",
        "category": "NEMESIS",
        "emoji": "✈️",
        "description": "Équipe forte sur jeu aérien contre défense faible dans les airs.",
        "conditions": {
            "aerial_dominance": {">": 65},
            "aerial_weakness_opponent": {">": 60}
        },
        "primary_markets": ["team_to_score_header", "over_25"],
        "secondary_markets": ["corners_over"],
        "avoid_markets": [],
        "historical_roi": 10.2,
        "historical_win_rate": 61.0,
        "min_confidence_threshold": 58
    }
]

# ═══════════════════════════════════════════════════════════════════════════════
# LES 44 STRATÉGIES (avec groupes et paramètres enrichis)
# ═══════════════════════════════════════════════════════════════════════════════

STRATEGIES = [
    # GROUPE A: CONVERGENCE (5)
    {"code": "CONVERGENCE_OVER_PURE", "name": "Convergence Over Pure", "group": "CONVERGENCE", "family": "CONVERGENCE",
     "conditions": {"friction_over": True, "team_tendency_over": True}, "min_edge": 0.03,
     "compatible_scenarios": ["TOTAL_CHAOS", "SNIPER_DUEL", "GLASS_CANNON"],
     "quant_params": {"min_friction": 60, "min_tendency": 55}},
    {"code": "CONVERGENCE_OVER_MC_55", "name": "Convergence Over MC 55%", "group": "CONVERGENCE", "family": "CONVERGENCE",
     "conditions": {"mc_over_prob": 0.55, "friction_over": True}, "min_edge": 0.04,
     "compatible_scenarios": ["TOTAL_CHAOS", "EXPLOSIVE_START"],
     "quant_params": {"mc_threshold": 0.55, "min_simulations": 1000}},
    {"code": "CONVERGENCE_OVER_MC_60", "name": "Convergence Over MC 60%", "group": "CONVERGENCE", "family": "CONVERGENCE",
     "conditions": {"mc_over_prob": 0.60, "friction_over": True}, "min_edge": 0.05,
     "compatible_scenarios": ["TOTAL_CHAOS", "SNIPER_DUEL"],
     "quant_params": {"mc_threshold": 0.60, "min_simulations": 1000}},
    {"code": "CONVERGENCE_OVER_MC_65", "name": "Convergence Over MC 65%", "group": "CONVERGENCE", "family": "CONVERGENCE",
     "conditions": {"mc_over_prob": 0.65, "friction_over": True}, "min_edge": 0.06,
     "compatible_scenarios": ["TOTAL_CHAOS"],
     "quant_params": {"mc_threshold": 0.65, "min_simulations": 1000}},
    {"code": "CONVERGENCE_UNDER_PURE", "name": "Convergence Under Pure", "group": "CONVERGENCE", "family": "CONVERGENCE",
     "conditions": {"friction_under": True, "team_tendency_under": True}, "min_edge": 0.03,
     "compatible_scenarios": ["ATTRITION_WAR", "CONSERVATIVE_WALL"],
     "quant_params": {"min_friction": 60, "min_tendency": 55}},
    
    # GROUPE B: MONTE CARLO (5)
    {"code": "MC_PURE_55", "name": "Monte Carlo Pure 55%", "group": "MONTE_CARLO", "family": "MONTE_CARLO",
     "conditions": {"mc_best_prob": 0.55}, "min_edge": 0.03,
     "compatible_scenarios": ["TOTAL_CHAOS", "SNIPER_DUEL", "DIESEL_DUEL"],
     "quant_params": {"mc_threshold": 0.55, "min_simulations": 1000}},
    {"code": "MC_PURE_60", "name": "Monte Carlo Pure 60%", "group": "MONTE_CARLO", "family": "MONTE_CARLO",
     "conditions": {"mc_best_prob": 0.60}, "min_edge": 0.04,
     "compatible_scenarios": ["TOTAL_CHAOS", "KILLER_INSTINCT"],
     "quant_params": {"mc_threshold": 0.60, "min_simulations": 1000}},
    {"code": "MC_PURE_65", "name": "Monte Carlo Pure 65%", "group": "MONTE_CARLO", "family": "MONTE_CARLO",
     "conditions": {"mc_best_prob": 0.65}, "min_edge": 0.05,
     "compatible_scenarios": ["KILLER_INSTINCT", "PREY_HUNT"],
     "quant_params": {"mc_threshold": 0.65, "min_simulations": 1000}},
    {"code": "MC_PURE_70", "name": "Monte Carlo Pure 70%", "group": "MONTE_CARLO", "family": "MONTE_CARLO",
     "conditions": {"mc_best_prob": 0.70}, "min_edge": 0.06,
     "compatible_scenarios": ["KILLER_INSTINCT"],
     "quant_params": {"mc_threshold": 0.70, "min_simulations": 1000}},
    {"code": "MC_NO_CLASH", "name": "Monte Carlo No Clash", "group": "MONTE_CARLO", "family": "MONTE_CARLO",
     "conditions": {"mc_best_prob": 0.55, "no_style_clash": True}, "min_edge": 0.04,
     "compatible_scenarios": ["ATTRITION_WAR", "DIESEL_DUEL"],
     "quant_params": {"mc_threshold": 0.55, "clash_penalty": 0.1}},
    
    # GROUPE C: QUANT MARKET (5)
    {"code": "QUANT_BEST_MARKET", "name": "Quant Best Market", "group": "QUANT", "family": "QUANT",
     "conditions": {"use_team_best_market": True}, "min_edge": 0.02,
     "compatible_scenarios": [],
     "quant_params": {"min_historical_bets": 5, "min_historical_roi": 10}},
    {"code": "QUANT_ROI_25", "name": "Quant ROI 25%+", "group": "QUANT", "family": "QUANT",
     "conditions": {"min_historical_roi": 25}, "min_edge": 0.03,
     "compatible_scenarios": [],
     "quant_params": {"roi_threshold": 25}},
    {"code": "QUANT_ROI_30", "name": "Quant ROI 30%+", "group": "QUANT", "family": "QUANT",
     "conditions": {"min_historical_roi": 30}, "min_edge": 0.04,
     "compatible_scenarios": [],
     "quant_params": {"roi_threshold": 30}},
    {"code": "QUANT_ROI_40", "name": "Quant ROI 40%+", "group": "QUANT", "family": "QUANT",
     "conditions": {"min_historical_roi": 40}, "min_edge": 0.05,
     "compatible_scenarios": ["KILLER_INSTINCT", "PREY_HUNT"],
     "quant_params": {"roi_threshold": 40}},
    {"code": "QUANT_ROI_50", "name": "Quant ROI 50%+", "group": "QUANT", "family": "QUANT",
     "conditions": {"min_historical_roi": 50}, "min_edge": 0.06,
     "compatible_scenarios": ["KILLER_INSTINCT"],
     "quant_params": {"roi_threshold": 50}},
    
    # GROUPE D: SCORING THRESHOLD (4)
    {"code": "SCORE_SNIPER_34", "name": "Score Sniper 34+", "group": "SCORING", "family": "SCORING",
     "conditions": {"min_diamond_score": 34}, "min_edge": 0.08,
     "compatible_scenarios": ["KILLER_INSTINCT", "PREY_HUNT"],
     "quant_params": {"score_threshold": 34, "expected_wr": 82.7}},
    {"code": "SCORE_HIGH_32", "name": "Score High 32+", "group": "SCORING", "family": "SCORING",
     "conditions": {"min_diamond_score": 32}, "min_edge": 0.06,
     "compatible_scenarios": ["TOTAL_CHAOS", "KILLER_INSTINCT"],
     "quant_params": {"score_threshold": 32, "expected_wr": 74.0}},
    {"code": "SCORE_GOOD_28", "name": "Score Good 28+", "group": "SCORING", "family": "SCORING",
     "conditions": {"min_diamond_score": 28}, "min_edge": 0.04,
     "compatible_scenarios": ["TOTAL_CHAOS", "SNIPER_DUEL", "DIESEL_DUEL"],
     "quant_params": {"score_threshold": 28, "expected_wr": 72.4}},
    {"code": "SCORE_MEDIUM_25", "name": "Score Medium 25+", "group": "SCORING", "family": "SCORING",
     "conditions": {"min_diamond_score": 25}, "min_edge": 0.03,
     "compatible_scenarios": [],
     "quant_params": {"score_threshold": 25, "expected_wr": 68.0}},
    
    # GROUPE E: TACTICAL MATRIX (3)
    {"code": "TACTICAL_GEGENPRESSING", "name": "Tactical Gegenpressing", "group": "TACTICAL", "family": "TACTICAL",
     "conditions": {"style_gegenpressing": True}, "min_edge": 0.05,
     "compatible_scenarios": ["PRESSING_DEATH", "EXPLOSIVE_START"],
     "quant_params": {"over25_boost": 0.82}},
    {"code": "TACTICAL_ATTACKING", "name": "Tactical Attacking", "group": "TACTICAL", "family": "TACTICAL",
     "conditions": {"style_attacking": True}, "min_edge": 0.04,
     "compatible_scenarios": ["TOTAL_CHAOS", "GLASS_CANNON"],
     "quant_params": {"over25_boost": 0.83}},
    {"code": "TACTICAL_HIGH_SCORING", "name": "Tactical High Scoring", "group": "TACTICAL", "family": "TACTICAL",
     "conditions": {"both_high_scoring": True}, "min_edge": 0.05,
     "compatible_scenarios": ["TOTAL_CHAOS", "SNIPER_DUEL"],
     "quant_params": {"xg_combined_min": 3.0}},
    
    # GROUPE F: LEAGUE PATTERNS (5)
    {"code": "LEAGUE_CHAMPIONS", "name": "League Champions", "group": "LEAGUE", "family": "LEAGUE",
     "conditions": {"league": "champions_league"}, "min_edge": 0.04,
     "compatible_scenarios": ["TOTAL_CHAOS", "KILLER_INSTINCT"],
     "quant_params": {"over25_roi": 28.78}},
    {"code": "LEAGUE_BUNDESLIGA", "name": "League Bundesliga", "group": "LEAGUE", "family": "LEAGUE",
     "conditions": {"league": "bundesliga"}, "min_edge": 0.03,
     "compatible_scenarios": ["TOTAL_CHAOS", "EXPLOSIVE_START"],
     "quant_params": {"over25_roi": 16.22}},
    {"code": "LEAGUE_PREMIER", "name": "League Premier", "group": "LEAGUE", "family": "LEAGUE",
     "conditions": {"league": "premier_league"}, "min_edge": 0.02,
     "compatible_scenarios": [],
     "quant_params": {"over25_roi": 9.44}},
    {"code": "LEAGUE_SERIE_A", "name": "League Serie A", "group": "LEAGUE", "family": "LEAGUE",
     "conditions": {"league": "serie_a"}, "min_edge": 0.02,
     "compatible_scenarios": ["ATTRITION_WAR"],
     "quant_params": {"under25_tendency": True}},
    {"code": "LEAGUE_LIGUE_1", "name": "League Ligue 1", "group": "LEAGUE", "family": "LEAGUE",
     "conditions": {"league": "ligue_1"}, "min_edge": 0.02,
     "compatible_scenarios": [],
     "quant_params": {}},
    
    # GROUPE G: SPECIAL MARKETS (4)
    {"code": "UNDER_35_PURE", "name": "Under 3.5 Pure", "group": "SPECIAL_MARKETS", "family": "MARKET_SPECIFIC",
     "conditions": {"market": "under_35"}, "min_edge": 0.02,
     "compatible_scenarios": ["ATTRITION_WAR", "THE_SIEGE"],
     "quant_params": {"expected_wr": 73.6, "historical_pnl": 316.4}},
    {"code": "UNDER_25_SELECTIVE", "name": "Under 2.5 Selective", "group": "SPECIAL_MARKETS", "family": "MARKET_SPECIFIC",
     "conditions": {"market": "under_25", "defensive_match": True}, "min_edge": 0.03,
     "compatible_scenarios": ["ATTRITION_WAR", "CONSERVATIVE_WALL"],
     "quant_params": {}},
    {"code": "BTTS_NO_PURE", "name": "BTTS No Pure", "group": "SPECIAL_MARKETS", "family": "MARKET_SPECIFIC",
     "conditions": {"market": "btts_no"}, "min_edge": 0.02,
     "compatible_scenarios": ["ATTRITION_WAR", "CONSERVATIVE_WALL", "THE_SIEGE"],
     "quant_params": {"clv_positive": True}},
    {"code": "OVER_15_SAFE", "name": "Over 1.5 Safe", "group": "SPECIAL_MARKETS", "family": "MARKET_SPECIFIC",
     "conditions": {"market": "over_15"}, "min_edge": 0.01,
     "compatible_scenarios": ["TOTAL_CHAOS", "SNIPER_DUEL", "EXPLOSIVE_START"],
     "quant_params": {"min_xg_combined": 2.5}},
    
    # GROUPE H: PARADOX & SWEET SPOT (3)
    {"code": "LOW_CONFIDENCE_PARADOX", "name": "Low Confidence Paradox", "group": "PARADOX", "family": "PARADOX",
     "conditions": {"confidence_range": [20, 39]}, "min_edge": 0.02,
     "compatible_scenarios": ["NOTHING_TO_LOSE"],
     "quant_params": {"paradox_wr": 60.6, "contrarian": True}},
    {"code": "SWEET_SPOT_60_79", "name": "Sweet Spot 60-79%", "group": "PARADOX", "family": "PARADOX",
     "conditions": {"confidence_range": [60, 79]}, "min_edge": 0.04,
     "compatible_scenarios": [],
     "quant_params": {"optimal_confidence_zone": True}},
    {"code": "SWEET_SPOT_CONSERVATIVE", "name": "Sweet Spot Conservative", "group": "PARADOX", "family": "PARADOX",
     "conditions": {"confidence_range": [70, 85], "conservative_stake": True}, "min_edge": 0.03,
     "compatible_scenarios": ["KILLER_INSTINCT"],
     "quant_params": {"stake_reduction": 0.5}},
    
    # GROUPE I: COMBOS VALIDÉS (4)
    {"code": "COMBO_CONV_MC_SCORE", "name": "Combo Convergence+MC+Score", "group": "COMBO", "family": "COMBO",
     "conditions": {"convergence": True, "mc_prob": 0.55, "min_score": 28}, "min_edge": 0.06,
     "compatible_scenarios": ["TOTAL_CHAOS", "KILLER_INSTINCT"],
     "quant_params": {"historical_pnl": 554.4, "triple_validation": True}},
    {"code": "COMBO_TACTICAL_LEAGUE", "name": "Combo Tactical+League", "group": "COMBO", "family": "COMBO",
     "conditions": {"tactical_match": True, "league_pattern": True}, "min_edge": 0.05,
     "compatible_scenarios": ["PRESSING_DEATH"],
     "quant_params": {}},
    {"code": "TRIPLE_VALIDATION", "name": "Triple Validation", "group": "COMBO", "family": "COMBO",
     "conditions": {"friction": True, "mc_prob": 0.55, "quant_roi": 25}, "min_edge": 0.06,
     "compatible_scenarios": ["KILLER_INSTINCT", "PREY_HUNT"],
     "quant_params": {"require_all_three": True}},
    {"code": "QUANT_MC_COMBO", "name": "Quant+MC Combo", "group": "COMBO", "family": "COMBO",
     "conditions": {"quant_signal": True, "mc_confirmation": True}, "min_edge": 0.05,
     "compatible_scenarios": [],
     "quant_params": {}},
    
    # GROUPE J: SYSTÈME TIER (4)
    {"code": "TIER_1_SNIPER", "name": "Tier 1 Sniper", "group": "TIER", "family": "TIER",
     "conditions": {"tier": 1, "min_score": 34}, "min_edge": 0.08,
     "compatible_scenarios": ["KILLER_INSTINCT"],
     "quant_params": {"max_stake": 3, "kelly_fraction": 0.15}},
    {"code": "TIER_2_ELITE", "name": "Tier 2 Elite", "group": "TIER", "family": "TIER",
     "conditions": {"tier": 2, "min_score": 30}, "min_edge": 0.06,
     "compatible_scenarios": ["TOTAL_CHAOS", "PREY_HUNT"],
     "quant_params": {"max_stake": 2, "kelly_fraction": 0.20}},
    {"code": "TIER_3_GOLD", "name": "Tier 3 Gold", "group": "TIER", "family": "TIER",
     "conditions": {"tier": 3, "min_score": 25}, "min_edge": 0.04,
     "compatible_scenarios": [],
     "quant_params": {"max_stake": 1.5, "kelly_fraction": 0.25}},
    {"code": "TIER_4_STANDARD", "name": "Tier 4 Standard", "group": "TIER", "family": "TIER",
     "conditions": {"tier": 4, "min_score": 20}, "min_edge": 0.02,
     "compatible_scenarios": [],
     "quant_params": {"max_stake": 1, "kelly_fraction": 0.25}},
    
    # GROUPE K: ULTIMATE (2)
    {"code": "ULTIMATE_SNIPER", "name": "Ultimate Sniper", "group": "ULTIMATE", "family": "ULTIMATE",
     "conditions": {"all_conditions_met": True, "score": 34, "mc": 0.65, "convergence": True}, "min_edge": 0.10,
     "compatible_scenarios": ["KILLER_INSTINCT", "PREY_HUNT"],
     "quant_params": {"elite_only": True, "max_daily_bets": 2}},
    {"code": "ULTIMATE_HYBRID", "name": "Ultimate Hybrid", "group": "ULTIMATE", "family": "ULTIMATE",
     "conditions": {"hybrid_score": 80}, "min_edge": 0.08,
     "compatible_scenarios": ["TOTAL_CHAOS", "KILLER_INSTINCT"],
     "quant_params": {"combine_all_signals": True}},
]


def migrate_scenarios(conn):
    """Migre les 20 scénarios vers PostgreSQL"""
    print("\n📋 Migration des 20 scénarios...")
    
    with conn.cursor() as cur:
        # Vider la table existante
        cur.execute("DELETE FROM quantum.scenario_catalog")
        
        for scenario in SCENARIOS:
            cur.execute("""
                INSERT INTO quantum.scenario_catalog 
                (scenario_code, scenario_name, category, emoji, description,
                 conditions, primary_markets, secondary_markets, avoid_markets,
                 historical_roi, historical_win_rate, min_confidence_threshold, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                scenario["scenario_code"],
                scenario["scenario_name"],
                scenario["category"],
                scenario["emoji"],
                scenario["description"],
                Json(scenario["conditions"]),
                Json(scenario["primary_markets"]),
                Json(scenario["secondary_markets"]),
                Json(scenario["avoid_markets"]),
                scenario["historical_roi"],
                scenario["historical_win_rate"],
                scenario["min_confidence_threshold"],
                True
            ))
        
        conn.commit()
        print(f"   ✅ {len(SCENARIOS)} scénarios migrés")


def migrate_strategies(conn):
    """Migre les 44 stratégies vers PostgreSQL"""
    print("\n📋 Migration des 44 stratégies...")
    
    with conn.cursor() as cur:
        # Vider la table existante
        cur.execute("DELETE FROM quantum.strategy_catalog")
        
        for strategy in STRATEGIES:
            cur.execute("""
                INSERT INTO quantum.strategy_catalog 
                (strategy_code, strategy_name, strategy_family, strategy_group,
                 compatible_scenarios, min_edge, requires_conditions, quant_params,
                 kelly_fraction, max_stake_pct)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                strategy["code"],
                strategy["name"],
                strategy.get("family", "EMPIRICAL"),
                strategy.get("group", "OTHER"),
                Json(strategy.get("compatible_scenarios", [])),
                strategy.get("min_edge", 0.02),
                Json(strategy.get("conditions", {})),
                Json(strategy.get("quant_params", {})),
                strategy.get("quant_params", {}).get("kelly_fraction", 0.25),
                strategy.get("quant_params", {}).get("max_stake_pct", 100)
            ))
        
        conn.commit()
        print(f"   ✅ {len(STRATEGIES)} stratégies migrées")


def create_scenario_strategy_mapping(conn):
    """Crée une vue pour le mapping scénario-stratégie"""
    print("\n�� Création de la vue scenario_strategy_mapping...")
    
    with conn.cursor() as cur:
        cur.execute("""
            CREATE OR REPLACE VIEW quantum.v_scenario_strategy_mapping AS
            SELECT 
                s.scenario_code,
                s.scenario_name,
                s.category as scenario_category,
                st.strategy_code,
                st.strategy_name,
                st.strategy_group,
                st.min_edge,
                st.quant_params
            FROM quantum.scenario_catalog s
            CROSS JOIN quantum.strategy_catalog st
            WHERE st.compatible_scenarios ? s.scenario_code
               OR jsonb_array_length(st.compatible_scenarios) = 0
            ORDER BY s.category, s.scenario_code, st.strategy_group;
        """)
        conn.commit()
        print("   ✅ Vue v_scenario_strategy_mapping créée")


def print_summary(conn):
    """Affiche le résumé de la migration"""
    print("\n" + "="*70)
    print("📊 RÉSUMÉ DE LA MIGRATION")
    print("="*70)
    
    with conn.cursor() as cur:
        # Scénarios
        cur.execute("SELECT category, COUNT(*) FROM quantum.scenario_catalog GROUP BY category ORDER BY category")
        print("\n🎯 SCÉNARIOS par catégorie:")
        for row in cur.fetchall():
            print(f"   {row[0]}: {row[1]}")
        
        # Stratégies
        cur.execute("SELECT strategy_group, COUNT(*) FROM quantum.strategy_catalog GROUP BY strategy_group ORDER BY strategy_group")
        print("\n📈 STRATÉGIES par groupe:")
        for row in cur.fetchall():
            print(f"   {row[0]}: {row[1]}")
        
        # Totaux
        cur.execute("SELECT COUNT(*) FROM quantum.scenario_catalog")
        scenarios_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM quantum.strategy_catalog")
        strategies_count = cur.fetchone()[0]
        
        print(f"\n✅ TOTAL: {scenarios_count} scénarios + {strategies_count} stratégies = {scenarios_count + strategies_count} éléments")


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║           MIGRATION QUANTUM HYBRID SYSTEM V1.0                                ║
║                                                                               ║
║  20 Scénarios + 44 Stratégies → PostgreSQL                                   ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    conn = psycopg2.connect(**DB_CONFIG)
    
    try:
        migrate_scenarios(conn)
        migrate_strategies(conn)
        create_scenario_strategy_mapping(conn)
        print_summary(conn)
        
        print("\n✅ Migration terminée avec succès!")
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
