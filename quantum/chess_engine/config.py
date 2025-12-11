"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    CHESS ENGINE V2.0 - CONFIGURATION                          ║
║                                                                               ║
║  Philosophie: "100x cote 1.60 > 100x cote 3.00 perdante"                     ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# PATHS - SOURCES DE DONNEES
# ═══════════════════════════════════════════════════════════════════════════════

BASE_PATH = Path("/home/Mon_ps")
DATA_PATH = BASE_PATH / "data"

PATHS = {
    "goalkeeper_dna": DATA_PATH / "goalkeeper_dna/goalkeeper_dna_v4_4_by_team.json",
    "defense_dna": DATA_PATH / "defense_dna/team_defense_dna_v5_1_corrected.json",
    "teams_context_dna": DATA_PATH / "quantum_v2/teams_context_dna.json",
    "all_goals": DATA_PATH / "goal_analysis/all_goals_2025.json",
    "players_impact": DATA_PATH / "quantum_v2/players_impact_dna.json",
    "referee_dna": DATA_PATH / "referee_dna_hedge_fund_v4.json",
    "team_exploits": DATA_PATH / "quantum_v2/team_exploit_profiles.json",
    "matches": DATA_PATH / "football_data/matches_all_leagues_2526.json",
    "defender_dna": DATA_PATH / "defender_dna/defender_dna_quant_v9.json",
    "signals_output": BASE_PATH / "outputs/chess_engine_signals",
    "backtest_output": BASE_PATH / "outputs/chess_engine_backtest",
}

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

# ═══════════════════════════════════════════════════════════════════════════════
# TIERS D'EQUIPES (Liquidite)
# ═══════════════════════════════════════════════════════════════════════════════

TEAM_TIERS = {
    "ELITE": ["Manchester City", "Liverpool", "Arsenal", "Real Madrid", "Barcelona", 
              "Bayern Munich", "Paris Saint Germain", "Inter", "Juventus"],
    "GOLD": ["Chelsea", "Manchester United", "Tottenham", "Newcastle United", 
             "Atletico Madrid", "Borussia Dortmund", "AC Milan", "Napoli", 
             "Marseille", "Lyon", "RB Leipzig", "Bayer Leverkusen"],
}

# ═══════════════════════════════════════════════════════════════════════════════
# MIN_EDGE ADAPTATIF PAR MARCHE + TIER
# ═══════════════════════════════════════════════════════════════════════════════

MIN_EDGE_BY_MARKET = {
    "home": 0.025, "away": 0.025, "draw": 0.030,
    "over_25": 0.025, "under_25": 0.025,
    "btts_yes": 0.030, "btts_no": 0.030,
    "dc_1x": 0.035, "dc_x2": 0.035, "dc_12": 0.035,
    "dnb_home": 0.035, "dnb_away": 0.035,
    "over_15": 0.040, "over_35": 0.040,
    "under_15": 0.040, "under_35": 0.040,
    "corners_over": 0.080, "corners_under": 0.080,
    "cards_over": 0.080, "cards_under": 0.080,
    "correct_score": 0.120,
}

TIER_EDGE_MULTIPLIER = {
    "ELITE": 1.0, "GOLD": 1.1, "SILVER": 1.2, "STANDARD": 1.3,
}

# ═══════════════════════════════════════════════════════════════════════════════
# POIDS BAYESIENS PAR MARCHE
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_ENGINE_WEIGHTS = {
    "matchup": 0.35, "chain": 0.20, "coach": 0.15,
    "pattern": 0.15, "referee": 0.05, "variance": 0.10,
}

MARKET_WEIGHTS = {
    "1X2": {"matchup": 0.40, "chain": 0.20, "coach": 0.15, "pattern": 0.15, "referee": 0.05, "variance": 0.05},
    "OVER_UNDER": {"matchup": 0.30, "chain": 0.25, "coach": 0.15, "pattern": 0.15, "referee": 0.05, "variance": 0.10},
    "BTTS": {"matchup": 0.35, "chain": 0.30, "coach": 0.10, "pattern": 0.10, "referee": 0.05, "variance": 0.10},
    "CORNERS": {"matchup": 0.25, "chain": 0.15, "coach": 0.20, "pattern": 0.20, "referee": 0.10, "variance": 0.10},
    "CARDS": {"matchup": 0.15, "chain": 0.10, "coach": 0.15, "pattern": 0.20, "referee": 0.30, "variance": 0.10},
}

# ═══════════════════════════════════════════════════════════════════════════════
# KELLY SIZING
# ═══════════════════════════════════════════════════════════════════════════════

KELLY_CONFIG = {
    "base_fraction": 0.25,
    "max_stake_pct": 0.05,
    "confidence_thresholds": {"strong": 0.80, "medium": 0.70, "normal": 0.60, "weak": 0.50},
    "odds_safety": {
        "very_safe": (1.0, 1.70),
        "safe": (1.70, 2.00),
        "normal": (2.00, 2.50),
        "risky": (2.50, 10.0),
    }
}

PORTFOLIO_CONFIG = {
    "max_exposure_per_match": 0.05,
    "max_correlated_bets": 3,
}

BACKTEST_CONFIG = {
    "initial_bankroll": 1000,
    "date_range": ("2024-08-01", "2025-12-10"),
    "min_matches_for_calibration": 50,
}

SUPPORTED_MARKETS = [
    "home", "draw", "away", "dc_1x", "dc_x2", "dc_12", "dnb_home", "dnb_away",
    "over_15", "under_15", "over_25", "under_25", "over_35", "under_35",
    "btts_yes", "btts_no", "corners_over_85", "corners_over_95",
    "cards_over_25", "cards_over_35",
]

# ═══════════════════════════════════════════════════════════════════════════════
# LIQUIDITY TAX (taxes de liquidite par marche et tier)
# ═══════════════════════════════════════════════════════════════════════════════

LIQUIDITY_TAX = {
    "market": {
        "1X2": 0.010,        # 1% tax - tres liquide
        "over_25": 0.010,
        "btts": 0.015,
        "corners": 0.030,    # 3% tax - moins liquide
        "cards": 0.030,
        "correct_score": 0.050,
    },
    "tier": {
        "ELITE": 0.005,      # 0.5% - meilleure liquidite
        "GOLD": 0.010,
        "SILVER": 0.015,
        "STANDARD": 0.020,   # 2% - moins de liquidite
    }
}
