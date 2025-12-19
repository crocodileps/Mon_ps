"""
Mapping entre noms de ligues Mon_PS (The Odds API) et URLs Betexplorer

IMPORTANT: Betexplorer utilise /football/ (pas /soccer/)
Format URL: https://www.betexplorer.com/football/{country}/{league}/

REFACTORED: 19/12/2025
- Team name mapping déplacé vers quantum/utils/team_resolver.py
- Utilise la table team_aliases en DB (source='betexplorer')
- Évite la duplication avec le mapping central Mon_PS
"""

import sys
from pathlib import Path

# Add quantum path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from quantum.utils.team_resolver import to_betexplorer, to_canonical, normalize_team
except ImportError:
    # Fallback si le module n'est pas disponible
    def to_betexplorer(name: str) -> str:
        return name
    def to_canonical(name: str, source: str = "betexplorer") -> str:
        return name
    def normalize_team(name: str) -> str:
        return name.lower().strip()


# Mapping Mon_PS league key -> Betexplorer URL path
LEAGUE_MAPPING = {
    # England
    "soccer_epl": "/football/england/premier-league/",
    "soccer_england_efl_cup": "/football/england/league-cup/",
    "soccer_england_fa_cup": "/football/england/fa-cup/",
    "soccer_england_championship": "/football/england/championship/",
    "soccer_england_league1": "/football/england/league-one/",
    "soccer_england_league2": "/football/england/league-two/",

    # Spain
    "soccer_spain_la_liga": "/football/spain/laliga/",
    "soccer_spain_segunda_division": "/football/spain/laliga2/",

    # Italy
    "soccer_italy_serie_a": "/football/italy/serie-a/",
    "soccer_italy_serie_b": "/football/italy/serie-b/",

    # Germany
    "soccer_germany_bundesliga": "/football/germany/bundesliga/",
    "soccer_germany_bundesliga2": "/football/germany/2-bundesliga/",
    "soccer_germany_liga3": "/football/germany/3-liga/",

    # France
    "soccer_france_ligue_one": "/football/france/ligue-1/",
    "soccer_france_ligue_two": "/football/france/ligue-2/",

    # Netherlands
    "soccer_netherlands_eredivisie": "/football/netherlands/eredivisie/",

    # Portugal
    "soccer_portugal_primeira_liga": "/football/portugal/liga-portugal/",

    # Belgium
    "soccer_belgium_first_div": "/football/belgium/jupiler-pro-league/",

    # Turkey
    "soccer_turkey_super_league": "/football/turkey/super-lig/",

    # Greece
    "soccer_greece_super_league": "/football/greece/super-league/",

    # Australia
    "soccer_australia_aleague": "/football/australia/a-league/",

    # Japan
    "soccer_japan_j_league": "/football/japan/j1-league/",

    # UEFA Competitions
    "soccer_uefa_champs_league": "/football/europe/champions-league/",
    "soccer_uefa_europa_league": "/football/europe/europa-league/",
    # NOTE: URL changed from europa-conference-league to conference-league in 2024-2025
    "soccer_uefa_europa_conference_league": "/football/europe/conference-league/",

    # Additional leagues (from legacy naming)
    "Premier League": "/football/england/premier-league/",
    "Primera Division": "/football/spain/laliga/",
    "Primera División": "/football/spain/laliga/",  # With accent
    "La Liga": "/football/spain/laliga/",
    "Ligue 1": "/football/france/ligue-1/",
    "Serie A": "/football/italy/serie-a/",
    "Bundesliga": "/football/germany/bundesliga/",
    "Eredivisie": "/football/netherlands/eredivisie/",
    "A-League": "/football/australia/a-league/",
    "Jupiler Pro League": "/football/belgium/jupiler-pro-league/",
}

# Market type mapping
MARKET_MAPPING = {
    # Mon_PS market -> Betexplorer endpoint
    "1x2": "1x2",
    "home": "1x2",
    "draw": "1x2",
    "away": "1x2",
    "btts_yes": "bts",
    "btts_no": "bts",
    "btts": "bts",
    "over_15": "ou",
    "under_15": "ou",
    "over_25": "ou",
    "under_25": "ou",
    "over_35": "ou",
    "under_35": "ou",
    "over_45": "ou",
    "under_45": "ou",
    "double_chance_1x": "dc",
    "double_chance_x2": "dc",
    "double_chance_12": "dc",
    "dc_1x": "dc",
    "dc_x2": "dc",
    "dc_12": "dc",
    "draw_no_bet_home": "dnb",
    "draw_no_bet_away": "dnb",
    "dnb_home": "dnb",
    "dnb_away": "dnb",
    "asian_handicap": "ah",
}

# Betexplorer base URL
BASE_URL = "https://www.betexplorer.com"


def normalize_team_name(team_name: str) -> str:
    """
    Normalize team name to Betexplorer format.

    UTILISE LE MAPPING CENTRAL: quantum/utils/team_resolver.py
    - Lit depuis la table team_aliases (source='betexplorer')
    - Évite la duplication de mappings

    Args:
        team_name: Team name from Mon_PS/The Odds API

    Returns:
        Normalized team name for Betexplorer matching
    """
    return to_betexplorer(team_name)


def get_betexplorer_url(league_key: str) -> str | None:
    """Alias for get_betexplorer_league_url (returns path only, not full URL)"""
    if league_key in LEAGUE_MAPPING:
        return LEAGUE_MAPPING[league_key]

    league_lower = league_key.lower()
    for key, url in LEAGUE_MAPPING.items():
        if key.lower() == league_lower:
            return url

    return None


def get_betexplorer_league_url(league_key: str) -> str | None:
    """
    Get Betexplorer URL for a Mon_PS league key.

    Args:
        league_key: Mon_PS league identifier (e.g., 'soccer_spain_la_liga')

    Returns:
        Full URL or None if not mapped
    """
    # Direct match
    if league_key in LEAGUE_MAPPING:
        return BASE_URL + LEAGUE_MAPPING[league_key]

    # Fuzzy match (lowercase)
    league_lower = league_key.lower()
    for key, url in LEAGUE_MAPPING.items():
        if key.lower() == league_lower:
            return BASE_URL + url

    return None


def get_betexplorer_market_type(market_type: str) -> str | None:
    """
    Get Betexplorer market type from Mon_PS market type.

    Args:
        market_type: Mon_PS market type (e.g., 'btts_yes', 'over_25')

    Returns:
        Betexplorer market endpoint (e.g., 'bts', 'ou') or None
    """
    market_lower = market_type.lower()

    # Direct match
    if market_lower in MARKET_MAPPING:
        return MARKET_MAPPING[market_lower]

    # Pattern matching
    if 'btts' in market_lower or 'bts' in market_lower:
        return 'bts'
    if 'over' in market_lower or 'under' in market_lower:
        return 'ou'
    if 'double_chance' in market_lower or market_lower.startswith('dc_'):
        return 'dc'
    if 'dnb' in market_lower or 'draw_no_bet' in market_lower:
        return 'dnb'
    if 'handicap' in market_lower or market_lower.startswith('ah'):
        return 'ah'
    if market_lower in ['home', 'draw', 'away', '1x2']:
        return '1x2'

    return None


def get_line_from_market(market_type: str) -> float | None:
    """
    Extract the line/total from a market type.

    Args:
        market_type: e.g., 'over_25', 'under_15'

    Returns:
        Line as float (e.g., 2.5, 1.5) or None
    """
    import re
    match = re.search(r'(\d)(\d)', market_type)
    if match:
        return float(f"{match.group(1)}.{match.group(2)}")
    return None


if __name__ == "__main__":
    print("=== League Mapping Test ===")
    test_leagues = [
        "soccer_spain_la_liga",
        "soccer_epl",
        "soccer_uefa_europa_league",
        "soccer_france_ligue_one",
        "unknown_league"
    ]
    for league in test_leagues:
        url = get_betexplorer_league_url(league)
        status = url if url else "NOT MAPPED"
        print(f"  {league} -> {status}")

    print("\n=== Market Mapping Test ===")
    test_markets = [
        "btts_yes", "over_25", "under_15", "dc_1x", "dnb_home", "home", "asian_handicap"
    ]
    for market in test_markets:
        mapped = get_betexplorer_market_type(market)
        line = get_line_from_market(market)
        print(f"  {market} -> {mapped} (line: {line})")

    print("\n=== Team Name Resolution (via central resolver) ===")
    test_teams = [
        "Manchester United",
        "Nottingham Forest",
        "Wolverhampton",
        "Leeds United",
        "Liverpool",
    ]
    for team in test_teams:
        resolved = normalize_team_name(team)
        print(f"  {team} -> {resolved}")
