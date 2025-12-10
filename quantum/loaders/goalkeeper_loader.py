"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║  GOALKEEPER LOADER - Chargement des données GoalkeeperDNA                            ║
║  Version: 2.0                                                                        ║
║  Architecture Mon_PS - Chess Engine V2.0                                             ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

Installation: /home/Mon_ps/quantum/loaders/goalkeeper_loader.py

Sources JSON:
- /home/Mon_ps/data/goalkeeper_dna/goalkeeper_dna_v4_4_by_team.json
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
    GOALKEEPER_DATA,
    DATA_ROOT,
)

from quantum.models import (
    GoalkeeperDNA,
    ShotStoppingMetrics,
    DistributionMetrics,
    SweepingMetrics,
    PenaltyProfile,
    ReliabilityMetrics,
    DataQuality,
)

logger = logging.getLogger("quantum.loaders.goalkeeper")

# ═══════════════════════════════════════════════════════════════════════════════════════
# CHEMINS DES FICHIERS
# ═══════════════════════════════════════════════════════════════════════════════════════

GOALKEEPER_FILES = [
    GOALKEEPER_DATA / "goalkeeper_dna_v4_4_by_team.json",
    GOALKEEPER_DATA / "goalkeeper_dna_v2.json",
    GOALKEEPER_DATA / "gk_stats.json",
    DATA_ROOT / "quantum_v2" / "goalkeeper_data.json",
]


# ═══════════════════════════════════════════════════════════════════════════════════════
# PARSING HELPERS
# ═══════════════════════════════════════════════════════════════════════════════════════

def parse_shot_stopping(data: Dict[str, Any]) -> ShotStoppingMetrics:
    """Parse les métriques d'arrêt de tirs."""
    
    shot_stopping = data.get("shot_stopping", data)
    
    return ShotStoppingMetrics(
        saves_total=safe_int(shot_stopping.get("saves_total", data.get("saves", 0))),
        saves_per_match=safe_float(shot_stopping.get("saves_per_match", data.get("saves_pm", 0))),
        save_percentage=clamp(safe_float(shot_stopping.get("save_percentage", data.get("save_pct", 0))), 0, 100),
        shots_faced_total=safe_int(shot_stopping.get("shots_faced_total", data.get("shots_faced", 0))),
        shots_on_target_faced=safe_int(shot_stopping.get("shots_on_target_faced", data.get("sot_faced", 0))),
        shots_faced_per_match=safe_float(shot_stopping.get("shots_faced_per_match", 0)),
        psxg_total=safe_float(shot_stopping.get("psxg_total", data.get("PSxG", data.get("psxg", 0)))),
        psxg_per_match=safe_float(shot_stopping.get("psxg_per_match", data.get("psxg_pm", 0))),
        goals_conceded=safe_int(shot_stopping.get("goals_conceded", data.get("goals_against", 0))),
        psxg_minus_goals=safe_float(shot_stopping.get("psxg_minus_goals", data.get("PSxG_diff", data.get("psxg_diff", 0)))),
        big_saves=safe_int(shot_stopping.get("big_saves", data.get("big_saves", 0))),
        big_save_rate=clamp(safe_float(shot_stopping.get("big_save_rate", 0)), 0, 100),
    )


def parse_distribution(data: Dict[str, Any]) -> DistributionMetrics:
    """Parse les métriques de distribution."""
    
    dist = data.get("distribution", data)
    
    return DistributionMetrics(
        passes_attempted=safe_int(dist.get("passes_attempted", data.get("passes", 0))),
        pass_completion=clamp(safe_float(dist.get("pass_completion", data.get("pass_pct", 0))), 0, 100),
        long_passes_attempted=safe_int(dist.get("long_passes_attempted", data.get("long_passes", 0))),
        long_pass_completion=clamp(safe_float(dist.get("long_pass_completion", data.get("long_pass_pct", 0))), 0, 100),
        launch_rate=clamp(safe_float(dist.get("launch_rate", data.get("launch_pct", 50))), 0, 100),
        goal_kick_long_rate=clamp(safe_float(dist.get("goal_kick_long_rate", data.get("gk_long_pct", 50))), 0, 100),
        progressive_passes_per_match=safe_float(dist.get("progressive_passes_per_match", data.get("prog_passes", 0))),
    )


def parse_sweeping(data: Dict[str, Any]) -> SweepingMetrics:
    """Parse les métriques de sweeping."""
    
    sweep = data.get("sweeping", data)
    
    return SweepingMetrics(
        sweeping_actions_per_match=safe_float(sweep.get("sweeping_actions_per_match", data.get("sweeper_actions", 0))),
        avg_sweeping_distance=safe_float(sweep.get("avg_sweeping_distance", data.get("sweep_distance", 0))),
        def_actions_outside_box=safe_int(sweep.get("def_actions_outside_box", data.get("actions_outside_box", 0))),
        def_actions_outside_box_per_match=safe_float(sweep.get("def_actions_outside_box_per_match", 0)),
        crosses_stopped=safe_int(sweep.get("crosses_stopped", data.get("crosses_claimed", 0))),
        crosses_stopped_rate=clamp(safe_float(sweep.get("crosses_stopped_rate", data.get("crosses_claimed_pct", 0))), 0, 100),
        crosses_claimed_per_match=safe_float(sweep.get("crosses_claimed_per_match", 0)),
        high_claims_per_match=safe_float(sweep.get("high_claims_per_match", data.get("high_claims", 0))),
        high_claim_success_rate=clamp(safe_float(sweep.get("high_claim_success_rate", 0)), 0, 100),
        punches_per_match=safe_float(sweep.get("punches_per_match", data.get("punches", 0))),
    )


def parse_penalties(data: Dict[str, Any]) -> PenaltyProfile:
    """Parse le profil penalties."""
    
    pen = data.get("penalties", data)
    
    return PenaltyProfile(
        penalties_faced=safe_int(pen.get("penalties_faced", data.get("pk_faced", 0))),
        penalties_saved=safe_int(pen.get("penalties_saved", data.get("pk_saved", 0))),
        penalties_conceded=safe_int(pen.get("penalties_conceded", data.get("pk_conceded", 0))),
        shootout_faced=safe_int(pen.get("shootout_faced", 0)),
        shootout_saved=safe_int(pen.get("shootout_saved", 0)),
    )


def parse_reliability(data: Dict[str, Any]) -> ReliabilityMetrics:
    """Parse les métriques de fiabilité."""
    
    rel = data.get("reliability", data)
    
    return ReliabilityMetrics(
        errors_leading_to_goal=safe_int(rel.get("errors_leading_to_goal", data.get("errors_goal", 0))),
        errors_leading_to_shot=safe_int(rel.get("errors_leading_to_shot", data.get("errors_shot", 0))),
        clean_sheets=safe_int(rel.get("clean_sheets", data.get("cs", 0))),
        clean_sheet_rate=clamp(safe_float(rel.get("clean_sheet_rate", data.get("cs_rate", 0))), 0, 100),
        goals_conceded_from_inside_box=clamp(safe_float(rel.get("goals_conceded_from_inside_box", 0)), 0, 100),
        goals_conceded_from_outside_box=clamp(safe_float(rel.get("goals_conceded_from_outside_box", 0)), 0, 100),
    )


# ═══════════════════════════════════════════════════════════════════════════════════════
# LOADER PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════════════

def load_goalkeeper_dna(team_name: str, data: Dict[str, Any] = None) -> Optional[GoalkeeperDNA]:
    """
    Charge un GoalkeeperDNA depuis les données JSON.
    
    Args:
        team_name: Nom de l'équipe
        data: Données pré-chargées (optionnel)
        
    Returns:
        GoalkeeperDNA ou None si échec
    """
    try:
        if data is None:
            data = find_team_goalkeeper_data(team_name)
            if data is None:
                logger.warning(f"Aucune donnée goalkeeper trouvée pour {team_name}")
                return None
        
        normalized = normalize_team_name(team_name)
        
        # Parser les composants
        shot_stopping = parse_shot_stopping(data)
        distribution = parse_distribution(data)
        sweeping = parse_sweeping(data)
        penalties = parse_penalties(data)
        reliability = parse_reliability(data)
        
        # Qualité des données
        expected_fields = ["saves", "psxg", "clean_sheets", "matches"]
        quality = calculate_data_quality(data, expected_fields)
        
        return GoalkeeperDNA(
            team_name=normalized,
            team_normalized=get_team_key(normalized),
            goalkeeper_name=data.get("goalkeeper_name", data.get("gk_name", data.get("name", ""))),
            goalkeeper_normalized=get_team_key(data.get("goalkeeper_name", "")),
            age=safe_int(data.get("age")) if data.get("age") else None,
            shot_stopping=shot_stopping,
            distribution=distribution,
            sweeping=sweeping,
            penalties=penalties,
            reliability=reliability,
            matches_this_season=safe_int(data.get("matches", data.get("matches_played", 0))),
            minutes_played=safe_int(data.get("minutes_played", data.get("minutes", 0))),
            data_quality=DataQuality(quality),
            last_updated=datetime.utcnow(),
        )
        
    except Exception as e:
        logger.error(f"Erreur chargement GoalkeeperDNA pour {team_name}: {e}")
        return None


def find_team_goalkeeper_data(team_name: str) -> Optional[Dict[str, Any]]:
    """Cherche les données goalkeeper d'une équipe."""
    normalized = normalize_team_name(team_name)
    key = get_team_key(team_name)
    
    for filepath in GOALKEEPER_FILES:
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
            
            if "goalkeepers" in data:
                gks = data["goalkeepers"]
                if isinstance(gks, dict) and search_key in gks:
                    return gks[search_key]
    
    return None


def load_all_goalkeeper_dna(league: str = None) -> Dict[str, GoalkeeperDNA]:
    """Charge tous les GoalkeeperDNA disponibles."""
    results = {}
    
    for filepath in GOALKEEPER_FILES:
        if not filepath.exists():
            continue
            
        data = load_json(filepath)
        if not data:
            continue
        
        teams_data = data.get("teams", data.get("goalkeepers", data))
        
        if isinstance(teams_data, dict):
            for team_name, team_data in teams_data.items():
                if league and team_data.get("league", "") != league:
                    continue
                gk = load_goalkeeper_dna(team_name, team_data)
                if gk:
                    results[get_team_key(team_name)] = gk
                    
        elif isinstance(teams_data, list):
            for team_data in teams_data:
                team_name = team_data.get("team", team_data.get("team_name", ""))
                if not team_name:
                    continue
                if league and team_data.get("league", "") != league:
                    continue
                gk = load_goalkeeper_dna(team_name, team_data)
                if gk:
                    results[get_team_key(team_name)] = gk
    
    logger.info(f"Chargé {len(results)} GoalkeeperDNA")
    return results
