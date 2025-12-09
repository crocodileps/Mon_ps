"""
═══════════════════════════════════════════════════════════════════════════════
🏦 AGENT DÉFENSE 2.0 - CONFIGURATION
   Version: 2.0.0
   Date: 2025-12-09
═══════════════════════════════════════════════════════════════════════════════
"""

import os
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path('/home/Mon_ps')
DATA_DIR = BASE_DIR / 'data'
AGENT_DIR = BASE_DIR / 'agents' / 'defense_v2'
MODEL_DIR = BASE_DIR / 'models' / 'agent_defense_v2'

# Créer les dossiers si nécessaire
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════════════
# DATA SOURCES
# ═══════════════════════════════════════════════════════════════════════════════

DATA_SOURCES = {
    # Defense DNA (Understat)
    'defensive_lines': DATA_DIR / 'defensive_lines' / 'defensive_lines_v8_3_multi_source.json',
    'defender_dna': DATA_DIR / 'defender_dna' / 'defender_dna_quant_v9.json',
    'goalkeeper_dna': DATA_DIR / 'goalkeeper_dna' / 'goalkeeper_dna_v4_4_by_team.json',
    'goalkeeper_timing': DATA_DIR / 'goalkeeper_dna' / 'goalkeeper_timing_dna_v1.json',
    'team_defense_2025': DATA_DIR / 'defense_dna' / 'team_defense_dna_2025_fixed.json',
    
    # Quantum V2
    'zone_analysis': DATA_DIR / 'quantum_v2' / 'zone_analysis.json',
    'gamestate_insights': DATA_DIR / 'quantum_v2' / 'gamestate_insights.json',
    'team_exploit_profiles': DATA_DIR / 'quantum_v2' / 'team_exploit_profiles.json',
    'teams_context_dna': DATA_DIR / 'quantum_v2' / 'teams_context_dna.json',
    
    # Referee
    'referee_dna': DATA_DIR / 'referee_dna_hedge_fund_v4.json',
    
    # Football-Data UK (2025-26)
    'corners_dna': DATA_DIR / 'football_data_uk' / 'corners_dna_2025_26.json',
    'shots_dna': DATA_DIR / 'football_data_uk' / 'shots_dna_2025_26.json',
    'fouls_dna': DATA_DIR / 'football_data_uk' / 'fouls_dna_2025_26.json',
    'cards_team_dna': DATA_DIR / 'football_data_uk' / 'cards_team_dna_2025_26.json',
    'goals_enhanced': DATA_DIR / 'football_data_uk' / 'goals_enhanced_dna_2025_26.json',
    
    # Historical matches (for backtest)
    'matches_historical': DATA_DIR / 'football_data_uk' / 'all_seasons_combined.csv',
    
    # Team mapping
    'team_mapping': DATA_DIR / 'team_name_mapping_v2.json',
}

# ═══════════════════════════════════════════════════════════════════════════════
# LEAGUES
# ═══════════════════════════════════════════════════════════════════════════════

LEAGUES = ['EPL', 'La_Liga', 'Serie_A', 'Bundesliga', 'Ligue_1']

LEAGUE_MAPPING = {
    'EPL': 'Premier League',
    'La_Liga': 'La Liga',
    'Serie_A': 'Serie A',
    'Bundesliga': 'Bundesliga',
    'Ligue_1': 'Ligue 1',
}

# ═══════════════════════════════════════════════════════════════════════════════
# MARKETS (27 marchés)
# ═══════════════════════════════════════════════════════════════════════════════

MARKETS = {
    # Goals Markets (7)
    'over_15': {'type': 'classification', 'target': 'over_15', 'description': 'Over 1.5 Goals'},
    'over_25': {'type': 'classification', 'target': 'over_25', 'description': 'Over 2.5 Goals'},
    'over_35': {'type': 'classification', 'target': 'over_35', 'description': 'Over 3.5 Goals'},
    'btts': {'type': 'classification', 'target': 'btts', 'description': 'Both Teams To Score'},
    'total_goals': {'type': 'regression', 'target': 'total_goals', 'description': 'Total Goals'},
    'clean_sheet_home': {'type': 'classification', 'target': 'cs_home', 'description': 'Home Clean Sheet'},
    'clean_sheet_away': {'type': 'classification', 'target': 'cs_away', 'description': 'Away Clean Sheet'},
    
    # Timing Markets (5)
    'first_half_over_05': {'type': 'classification', 'target': '1h_over_05', 'description': '1H Over 0.5'},
    'first_half_over_15': {'type': 'classification', 'target': '1h_over_15', 'description': '1H Over 1.5'},
    'second_half_goals': {'type': 'regression', 'target': '2h_goals', 'description': '2H Goals'},
    'late_goal': {'type': 'classification', 'target': 'late_goal', 'description': 'Goal 76-90 min'},
    'no_goal_first_half': {'type': 'classification', 'target': 'no_goal_1h', 'description': 'No Goal 1H'},
    
    # Cards Markets (4)
    'over_35_cards': {'type': 'classification', 'target': 'cards_over_35', 'description': 'Over 3.5 Cards'},
    'over_45_cards': {'type': 'classification', 'target': 'cards_over_45', 'description': 'Over 4.5 Cards'},
    'total_cards': {'type': 'regression', 'target': 'total_cards', 'description': 'Total Cards'},
    'home_cards': {'type': 'regression', 'target': 'home_cards', 'description': 'Home Team Cards'},
    
    # Corners Markets (4)
    'corners_over_85': {'type': 'classification', 'target': 'corners_over_85', 'description': 'Over 8.5 Corners'},
    'corners_over_95': {'type': 'classification', 'target': 'corners_over_95', 'description': 'Over 9.5 Corners'},
    'corners_over_105': {'type': 'classification', 'target': 'corners_over_105', 'description': 'Over 10.5 Corners'},
    'total_corners': {'type': 'regression', 'target': 'total_corners', 'description': 'Total Corners'},
    
    # Set Pieces Markets (2)
    'goal_from_set_piece': {'type': 'classification', 'target': 'sp_goal', 'description': 'Goal from Set Piece'},
    'goal_from_corner': {'type': 'classification', 'target': 'corner_goal', 'description': 'Goal from Corner'},
    
    # Advanced Quant Markets (4)
    'high_volatility': {'type': 'classification', 'target': 'high_volatility', 'description': 'High Volatility Match'},
    'regression_play': {'type': 'classification', 'target': 'regression_play', 'description': 'Regression Expected'},
    
    # Result Markets (support) (2)
    'home_win_to_nil': {'type': 'classification', 'target': 'home_wtn', 'description': 'Home Win To Nil'},
    'away_win_to_nil': {'type': 'classification', 'target': 'away_wtn', 'description': 'Away Win To Nil'},
}

# ═══════════════════════════════════════════════════════════════════════════════
# MODEL PARAMETERS
# ═══════════════════════════════════════════════════════════════════════════════

MODEL_PARAMS = {
    'random_forest': {
        'n_estimators': 200,
        'max_depth': 12,
        'min_samples_split': 10,
        'min_samples_leaf': 5,
        'random_state': 42,
        'n_jobs': -1,
    },
    'gradient_boosting': {
        'n_estimators': 150,
        'max_depth': 6,
        'learning_rate': 0.05,
        'min_samples_split': 10,
        'random_state': 42,
    },
    'xgboost': {
        'n_estimators': 200,
        'max_depth': 6,
        'learning_rate': 0.05,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'random_state': 42,
        'n_jobs': -1,
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# THRESHOLDS
# ═══════════════════════════════════════════════════════════════════════════════

THRESHOLDS = {
    'min_edge': 0.03,           # Minimum edge for bet recommendation
    'min_confidence': 0.55,     # Minimum model confidence
    'max_kelly': 0.05,          # Maximum Kelly stake
    'min_matches': 5,           # Minimum matches for team data
    'feature_importance_min': 0.005,  # Minimum feature importance to keep
    'correlation_max': 0.95,    # Maximum correlation between features
}

# ═══════════════════════════════════════════════════════════════════════════════
# CALIBRATION
# ═══════════════════════════════════════════════════════════════════════════════

CALIBRATION = {
    'method': 'isotonic',  # 'platt', 'isotonic', 'beta'
    'cv_folds': 5,
}

# ═══════════════════════════════════════════════════════════════════════════════
# VERSION
# ═══════════════════════════════════════════════════════════════════════════════

VERSION = '2.0.0'
