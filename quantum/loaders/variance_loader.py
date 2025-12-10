"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║  VARIANCE LOADER - Chargement des données VarianceDNA                                ║
║  Version: 2.0                                                                        ║
║  Architecture Mon_PS - Chess Engine V2.0                                             ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

Installation: /home/Mon_ps/quantum/loaders/variance_loader.py

Sources JSON:
- /home/Mon_ps/data/variance/team_variance.json
- /home/Mon_ps/data/quantum_v2/xpts_data.json
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from .base_loader import (
    load_json,
    normalize_team_name,
    get_team_key,
    safe_float,
    safe_int,
    clamp,
    calculate_data_quality,
    VARIANCE_DATA,
    DATA_ROOT,
    QUANTUM_DATA,
)

from quantum.models import (
    VarianceDNA,
    ExpectedPointsMetrics,
    GoalVarianceMetrics,
    ConversionVariance,
    CloseGamesMetrics,
    DataQuality,
)

logger = logging.getLogger("quantum.loaders.variance")

# ═══════════════════════════════════════════════════════════════════════════════════════
# CHEMINS DES FICHIERS
# ═══════════════════════════════════════════════════════════════════════════════════════

VARIANCE_FILES = [
    VARIANCE_DATA / "team_variance.json",
    QUANTUM_DATA / "xpts_data.json",
    QUANTUM_DATA / "variance_analysis.json",
    DATA_ROOT / "understat" / "team_xpts.json",
]


# ═══════════════════════════════════════════════════════════════════════════════════════
# PARSING HELPERS
# ═══════════════════════════════════════════════════════════════════════════════════════

def parse_expected_points(data: Dict[str, Any]) -> ExpectedPointsMetrics:
    """Parse les métriques de points attendus."""
    
    xpts = data.get("expected_points", data.get("xpts", data))
    
    points_actual = safe_int(xpts.get("points_actual", data.get("points", data.get("pts", 0))))
    xpts_total = safe_float(xpts.get("xpts_total", data.get("xPts", data.get("xpts", 0))))
    matches = safe_int(xpts.get("matches_played", data.get("matches", 10)))
    
    return ExpectedPointsMetrics(
        points_actual=points_actual,
        matches_played=matches,
        xpts_total=xpts_total,
        points_diff=points_actual - xpts_total,
        points_per_match=points_actual / max(1, matches),
        xpts_per_match=xpts_total / max(1, matches),
    )


def parse_goal_variance(data: Dict[str, Any]) -> GoalVarianceMetrics:
    """Parse la variance des buts."""
    
    goals = data.get("goal_variance", data.get("goals", data))
    
    goals_scored = safe_int(goals.get("goals_scored", data.get("scored", data.get("GF", 0))))
    goals_conceded = safe_int(goals.get("goals_conceded", data.get("conceded", data.get("GA", 0))))
    xg_total = safe_float(goals.get("xg_total", data.get("xG", data.get("xg", 0))))
    xga_total = safe_float(goals.get("xga_total", data.get("xGA", data.get("xga", 0))))
    
    return GoalVarianceMetrics(
        goals_scored=goals_scored,
        xg_total=xg_total,
        goals_minus_xg=goals_scored - xg_total,
        goals_conceded=goals_conceded,
        xga_total=xga_total,
        goals_minus_xga=goals_conceded - xga_total,
    )


def parse_conversion_variance(data: Dict[str, Any]) -> ConversionVariance:
    """Parse la variance de conversion."""
    
    conv = data.get("conversion", data.get("big_chances", data))
    
    return ConversionVariance(
        big_chances_scored=safe_int(conv.get("big_chances_scored", data.get("bc_scored", 0))),
        big_chances_created=safe_int(conv.get("big_chances_created", data.get("bc_created", 0))),
        big_chances_missed=safe_int(conv.get("big_chances_missed", data.get("bc_missed", 0))),
        big_chance_conversion=clamp(safe_float(conv.get("big_chance_conversion", data.get("bc_conv_rate", 0))), 0, 100),
        expected_big_chance_conversion=45.0,  # Standard ~45%
        opponent_big_chances=safe_int(conv.get("opponent_big_chances", data.get("opp_bc", 0))),
        opponent_big_chances_scored=safe_int(conv.get("opponent_big_chances_scored", data.get("opp_bc_scored", 0))),
        opponent_big_chance_conversion=clamp(safe_float(conv.get("opponent_big_chance_conversion", 0)), 0, 100),
        penalties_scored=safe_int(conv.get("penalties_scored", data.get("pk_scored", 0))),
        penalties_taken=safe_int(conv.get("penalties_taken", data.get("pk_taken", 0))),
        penalties_missed=safe_int(conv.get("penalties_missed", data.get("pk_missed", 0))),
        penalties_conceded=safe_int(conv.get("penalties_conceded", data.get("pk_conceded", 0))),
        opponent_penalties_scored=safe_int(conv.get("opponent_penalties_scored", data.get("opp_pk_scored", 0))),
    )


def parse_close_games(data: Dict[str, Any]) -> CloseGamesMetrics:
    """Parse les métriques de matchs serrés."""
    
    close = data.get("close_games", data.get("tight_games", data))
    
    return CloseGamesMetrics(
        close_games_total=safe_int(close.get("close_games_total", data.get("close_games", 0))),
        close_games_won=safe_int(close.get("close_games_won", data.get("close_wins", 0))),
        close_games_drawn=safe_int(close.get("close_games_drawn", data.get("close_draws", 0))),
        close_games_lost=safe_int(close.get("close_games_lost", data.get("close_losses", 0))),
        one_nil_wins=safe_int(close.get("one_nil_wins", data.get("1_0_wins", 0))),
        one_nil_losses=safe_int(close.get("one_nil_losses", data.get("0_1_losses", 0))),
        late_winners=safe_int(close.get("late_winners", data.get("late_goals_scored", 0))),
        late_losers=safe_int(close.get("late_losers", data.get("late_goals_conceded", 0))),
    )


# ═══════════════════════════════════════════════════════════════════════════════════════
# LOADER PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════════════

def load_variance_dna(team_name: str, data: Dict[str, Any] = None) -> Optional[VarianceDNA]:
    """
    Charge un VarianceDNA depuis les données JSON.
    
    Args:
        team_name: Nom de l'équipe
        data: Données pré-chargées (optionnel)
        
    Returns:
        VarianceDNA ou None si échec
    """
    try:
        if data is None:
            data = find_team_variance_data(team_name)
            if data is None:
                logger.warning(f"Aucune donnée variance trouvée pour {team_name}")
                return None
        
        normalized = normalize_team_name(team_name)
        
        # Parser les composants
        points = parse_expected_points(data)
        goals = parse_goal_variance(data)
        conversion = parse_conversion_variance(data)
        close_games = parse_close_games(data)
        
        # Qualité des données
        expected_fields = ["xpts", "xg", "points", "matches"]
        quality = calculate_data_quality(data, expected_fields)
        
        return VarianceDNA(
            team_name=normalized,
            team_normalized=get_team_key(normalized),
            league=data.get("league", data.get("competition", "")),
            season=data.get("season", "2024-2025"),
            points=points,
            goals=goals,
            conversion=conversion,
            close_games=close_games,
            matches_analyzed=safe_int(data.get("matches", data.get("matches_played", 0))),
            data_quality=DataQuality(quality),
            last_updated=datetime.utcnow(),
        )
        
    except Exception as e:
        logger.error(f"Erreur chargement VarianceDNA pour {team_name}: {e}")
        return None


def find_team_variance_data(team_name: str) -> Optional[Dict[str, Any]]:
    """Cherche les données variance d'une équipe."""
    normalized = normalize_team_name(team_name)
    key = get_team_key(team_name)
    
    for filepath in VARIANCE_FILES:
        if not filepath.exists():
            continue
            
        data = load_json(filepath)
        if not data:
            continue
        
        for search_key in [normalized, key, team_name, team_name.lower()]:
            if search_key in data:
                return data[search_key]
            
            if isinstance(data, list):
                for item in data:
                    item_team = item.get("team", item.get("team_name", ""))
                    if get_team_key(item_team) == key:
                        return item
            
            if "teams" in data:
                teams = data["teams"]
                if isinstance(teams, dict) and search_key in teams:
                    return teams[search_key]
    
    return None


def load_all_variance_dna(league: str = None) -> Dict[str, VarianceDNA]:
    """Charge tous les VarianceDNA disponibles."""
    results = {}
    
    for filepath in VARIANCE_FILES:
        if not filepath.exists():
            continue
            
        data = load_json(filepath)
        if not data:
            continue
        
        teams_data = data.get("teams", data)
        
        if isinstance(teams_data, dict):
            for team_name, team_data in teams_data.items():
                if league and team_data.get("league", "") != league:
                    continue
                variance = load_variance_dna(team_name, team_data)
                if variance:
                    results[get_team_key(team_name)] = variance
                    
        elif isinstance(teams_data, list):
            for team_data in teams_data:
                team_name = team_data.get("team", team_data.get("team_name", ""))
                if not team_name:
                    continue
                if league and team_data.get("league", "") != league:
                    continue
                variance = load_variance_dna(team_name, team_data)
                if variance:
                    results[get_team_key(team_name)] = variance
    
    logger.info(f"Chargé {len(results)} VarianceDNA")
    return results
