"""
CHESS ENGINE V2.0 - CONSTANTES
"""

LEAGUES = {
    "EPL": "Premier League",
    "LaLiga": "La Liga", 
    "SerieA": "Serie A",
    "Bundesliga": "Bundesliga",
    "Ligue1": "Ligue 1",
}

POSITIONS = {
    "GK": ["Goalkeeper"],
    "CB": ["Centre-Back", "Defender"],
    "FB": ["Left-Back", "Right-Back", "Wing-Back"],
    "DM": ["Defensive Midfield", "D"],
    "CM": ["Central Midfield", "M"],
    "AM": ["Attacking Midfield", "AM"],
    "W": ["Left Winger", "Right Winger", "Winger"],
    "ST": ["Centre-Forward", "Forward", "F", "S"],
}

GAME_FLOW = {
    "OPEN": "Both teams attacking - High scoring expected",
    "TIGHT": "Both teams defensive - Low scoring expected",
    "TACTICAL": "Mixed styles - Balanced",
    "CHAOTIC": "High press both sides - Unpredictable",
}

TIMING_BUCKETS = ["0-15", "16-30", "31-45", "46-60", "61-75", "76-90", "90+"]

VARIANCE_PROFILES = {
    "LUCKY": "Overperforming xG significantly",
    "UNLUCKY": "Underperforming xG significantly",
    "CLINICAL": "Converting above expected rate",
    "WASTEFUL": "Converting below expected rate",
    "NEUTRAL": "Performing as expected",
}

MARKET_CATEGORIES = {
    "1X2": ["home", "draw", "away"],
    "DOUBLE_CHANCE": ["dc_1x", "dc_x2", "dc_12"],
    "DNB": ["dnb_home", "dnb_away"],
    "OVER_UNDER": ["over_15", "under_15", "over_25", "under_25", "over_35", "under_35"],
    "BTTS": ["btts_yes", "btts_no"],
    "CORNERS": ["corners_over_85", "corners_over_95", "corners_over_105"],
    "CARDS": ["cards_over_25", "cards_over_35"],
}

SIGNAL_STRENGTH = {
    "STRONG": {"min_edge": 0.08, "min_confidence": 0.75},
    "MEDIUM": {"min_edge": 0.05, "min_confidence": 0.65},
    "WEAK": {"min_edge": 0.03, "min_confidence": 0.55},
}
