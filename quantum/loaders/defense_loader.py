"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║  DEFENSE LOADER - Chargement des données DefenseDNA                                  ║
║  Version: 2.0                                                                        ║
║  Architecture Mon_PS - Chess Engine V2.0                                             ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

Installation: /home/Mon_ps/quantum/loaders/defense_loader.py

Sources JSON:
- /home/Mon_ps/data/defense_dna/team_defense_dna_v5_1_corrected.json
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from .base_loader import (
    load_json,
    normalize_team_name,
    get_team_key,
    safe_float,
    safe_int,
    clamp,
    calculate_data_quality,
    DEFENSE_DATA,
    DATA_ROOT,
)

from quantum.models import (
    DefenseDNA,
    DefensiveMetrics,
    ZoneVulnerability,
    PressingResistance,
    DefensiveActions,
    ConfidentMetric,
    TimingMetric,
    DataQuality,
)

logger = logging.getLogger("quantum.loaders.defense")

# ═══════════════════════════════════════════════════════════════════════════════════════
# CHEMINS DES FICHIERS
# ═══════════════════════════════════════════════════════════════════════════════════════

DEFENSE_FILES = [
    DEFENSE_DATA / "team_defense_dna_v5_1_corrected.json",
    DEFENSE_DATA / "defense_dna.json",
    DATA_ROOT / "quantum_v2" / "defense_data.json",
]


# ═══════════════════════════════════════════════════════════════════════════════════════
# PARSING HELPERS
# ═══════════════════════════════════════════════════════════════════════════════════════

def parse_timing_metric(data: Dict[str, Any], prefix: str = "") -> Optional[TimingMetric]:
    """Parse les données de timing."""
    try:
        def get_period(period_name: str) -> float:
            keys = [f"{prefix}{period_name}", f"{prefix}_{period_name}", period_name]
            for key in keys:
                if key in data:
                    return safe_float(data[key])
            return 0.0
        
        return TimingMetric(
            period_0_15=get_period("0_15"),
            period_16_30=get_period("16_30"),
            period_31_45=get_period("31_45"),
            period_46_60=get_period("46_60"),
            period_61_75=get_period("61_75"),
            period_76_90=get_period("76_90"),
        )
    except:
        return None


def parse_defensive_metrics(data: Dict[str, Any]) -> DefensiveMetrics:
    """Parse les métriques défensives core."""
    
    matches = safe_int(data.get("matches", data.get("matches_played", 10)))
    xga_total = safe_float(data.get("xga_total", data.get("xGA", data.get("xga", 0))))
    xga_per_match_value = xga_total / max(1, matches)
    
    return DefensiveMetrics(
        goals_conceded=safe_int(data.get("goals_conceded", data.get("goals_against", data.get("conceded", 0)))),
        goals_conceded_per_match=safe_float(data.get("goals_conceded_per_match", data.get("gapg", 0))),
        xga_total=xga_total,
        xga_per_match=ConfidentMetric(value=xga_per_match_value, sample_size=matches),
        goals_minus_xga=safe_float(data.get("goals_minus_xga", data.get("xgaDiff", 0))),
        clean_sheets=safe_int(data.get("clean_sheets", data.get("cs", 0))),
        clean_sheet_rate=clamp(safe_float(data.get("clean_sheet_rate", data.get("cs_rate", 0))), 0, 100),
        shots_against_total=safe_int(data.get("shots_against_total", data.get("shots_against", 0))),
        shots_against_per_match=safe_float(data.get("shots_against_per_match", 0)),
        shots_on_target_against_per_match=safe_float(data.get("shots_on_target_against_per_match", data.get("sota_pm", 0))),
        big_chances_conceded=safe_int(data.get("big_chances_conceded", 0)),
        big_chances_conceded_per_match=safe_float(data.get("big_chances_conceded_per_match", 0)),
        goals_conceded_timing=parse_timing_metric(data.get("goals_conceded_timing", {}), "conceded_"),
        xga_timing=parse_timing_metric(data.get("xga_timing", {}), "xga_"),
    )


def parse_zone_vulnerability(data: Dict[str, Any]) -> ZoneVulnerability:
    """Parse les vulnérabilités par zone."""
    
    zones = data.get("zones", data.get("vulnerability", {}))
    
    return ZoneVulnerability(
        xga_from_left=clamp(safe_float(zones.get("xga_from_left", data.get("xga_left", 33.3))), 0, 100),
        xga_from_center=clamp(safe_float(zones.get("xga_from_center", data.get("xga_center", 33.3))), 0, 100),
        xga_from_right=clamp(safe_float(zones.get("xga_from_right", data.get("xga_right", 33.3))), 0, 100),
        xga_from_box=clamp(safe_float(zones.get("xga_from_box", data.get("xga_box", 70))), 0, 100),
        xga_from_outside_box=clamp(safe_float(zones.get("xga_from_outside_box", data.get("xga_outside", 30))), 0, 100),
        goals_from_open_play=clamp(safe_float(data.get("goals_from_open_play", data.get("open_play_pct", 60))), 0, 100),
        goals_from_set_pieces=clamp(safe_float(data.get("goals_from_set_pieces", data.get("set_piece_pct", 25))), 0, 100),
        goals_from_penalties=clamp(safe_float(data.get("goals_from_penalties", data.get("penalty_pct", 10))), 0, 100),
        goals_from_counter=clamp(safe_float(data.get("goals_from_counter", data.get("counter_pct", 15))), 0, 100),
        crosses_faced_per_match=safe_float(data.get("crosses_faced_per_match", data.get("crosses_faced", 0))),
        cross_success_against=clamp(safe_float(data.get("cross_success_against", 0)), 0, 100),
        aerial_duels_lost_per_match=safe_float(data.get("aerial_duels_lost_per_match", data.get("aerial_lost", 0))),
        headers_conceded=safe_int(data.get("headers_conceded", 0)),
    )


def parse_pressing_resistance(data: Dict[str, Any]) -> PressingResistance:
    """Parse la résistance au pressing."""
    
    pressing = data.get("pressing", data.get("pressing_resistance", {}))
    
    return PressingResistance(
        ppda_faced=safe_float(pressing.get("ppda_faced", data.get("ppda", 10))),
        turnovers_per_match=safe_float(pressing.get("turnovers_per_match", data.get("turnovers", 0))),
        turnovers_in_own_third=safe_float(pressing.get("turnovers_in_own_third", data.get("turnovers_own_third", 0))),
        build_up_success_rate=clamp(safe_float(pressing.get("build_up_success_rate", data.get("buildup_success", 0))), 0, 100),
        goals_conceded_from_turnovers=safe_int(pressing.get("goals_conceded_from_turnovers", data.get("goals_from_turnovers", 0))),
    )


def parse_defensive_actions(data: Dict[str, Any]) -> DefensiveActions:
    """Parse les actions défensives."""
    
    actions = data.get("actions", data.get("defensive_actions", {}))
    
    return DefensiveActions(
        tackles_per_match=safe_float(actions.get("tackles_per_match", data.get("tackles", 0))),
        tackles_won_rate=clamp(safe_float(actions.get("tackles_won_rate", data.get("tackles_won_pct", 0))), 0, 100),
        interceptions_per_match=safe_float(actions.get("interceptions_per_match", data.get("interceptions", 0))),
        clearances_per_match=safe_float(actions.get("clearances_per_match", data.get("clearances", 0))),
        blocks_per_match=safe_float(actions.get("blocks_per_match", data.get("blocks", 0))),
        shot_blocks_per_match=safe_float(actions.get("shot_blocks_per_match", data.get("shot_blocks", 0))),
        ground_duels_won_rate=clamp(safe_float(actions.get("ground_duels_won_rate", data.get("ground_duels_won", 0))), 0, 100),
        aerial_duels_won_rate=clamp(safe_float(actions.get("aerial_duels_won_rate", data.get("aerial_duels_won", 0))), 0, 100),
        fouls_committed_per_match=safe_float(actions.get("fouls_committed_per_match", data.get("fouls", 0))),
    )


# ═══════════════════════════════════════════════════════════════════════════════════════
# LOADER PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════════════

def load_defense_dna(team_name: str, data: Dict[str, Any] = None) -> Optional[DefenseDNA]:
    """
    Charge un DefenseDNA depuis les données JSON.
    
    Args:
        team_name: Nom de l'équipe
        data: Données pré-chargées (optionnel)
        
    Returns:
        DefenseDNA ou None si échec
    """
    try:
        if data is None:
            data = find_team_defense_data(team_name)
            if data is None:
                logger.warning(f"Aucune donnée defense trouvée pour {team_name}")
                return None
        
        normalized = normalize_team_name(team_name)
        
        # Parser les composants
        core = parse_defensive_metrics(data)
        zones = parse_zone_vulnerability(data)
        pressing = parse_pressing_resistance(data)
        actions = parse_defensive_actions(data)
        
        # Qualité des données
        expected_fields = ["xga_total", "goals_conceded", "clean_sheets", "matches"]
        quality = calculate_data_quality(data, expected_fields)
        
        return DefenseDNA(
            team_name=normalized,
            team_normalized=get_team_key(normalized),
            league=data.get("league", data.get("competition", "")),
            season=data.get("season", "2024-2025"),
            core=core,
            zones=zones,
            pressing=pressing,
            actions=actions,
            xga_home=safe_float(data.get("xga_home", 0)),
            xga_away=safe_float(data.get("xga_away", 0)),
            clean_sheet_rate_home=clamp(safe_float(data.get("cs_rate_home", 0)), 0, 100),
            clean_sheet_rate_away=clamp(safe_float(data.get("cs_rate_away", 0)), 0, 100),
            matches_analyzed=safe_int(data.get("matches", data.get("matches_played", 0))),
            data_quality=DataQuality(quality),
            last_updated=datetime.utcnow(),
        )
        
    except Exception as e:
        logger.error(f"Erreur chargement DefenseDNA pour {team_name}: {e}")
        return None


def find_team_defense_data(team_name: str) -> Optional[Dict[str, Any]]:
    """Cherche les données défensives d'une équipe."""
    normalized = normalize_team_name(team_name)
    key = get_team_key(team_name)
    
    for filepath in DEFENSE_FILES:
        if not filepath.exists():
            continue
            
        data = load_json(filepath)
        if not data:
            continue
        
        # Chercher avec différentes clés
        for search_key in [normalized, key, team_name, team_name.lower()]:
            if search_key in data:
                return data[search_key]
            
            if isinstance(data, list):
                for item in data:
                    item_name = item.get("team", item.get("team_name", item.get("name", "")))
                    if get_team_key(item_name) == key:
                        return item
            
            if "teams" in data:
                teams = data["teams"]
                if isinstance(teams, dict) and search_key in teams:
                    return teams[search_key]
    
    return None


def load_all_defense_dna(league: str = None) -> Dict[str, DefenseDNA]:
    """Charge tous les DefenseDNA disponibles."""
    results = {}
    
    for filepath in DEFENSE_FILES:
        if not filepath.exists():
            continue
            
        data = load_json(filepath)
        if not data:
            continue
        
        teams_data = data.get("teams", data) if isinstance(data, dict) else data
        
        if isinstance(teams_data, dict):
            for team_name, team_data in teams_data.items():
                if league and team_data.get("league", "") != league:
                    continue
                defense = load_defense_dna(team_name, team_data)
                if defense:
                    results[get_team_key(team_name)] = defense
                    
        elif isinstance(teams_data, list):
            for team_data in teams_data:
                team_name = team_data.get("team", team_data.get("team_name", ""))
                if not team_name:
                    continue
                if league and team_data.get("league", "") != league:
                    continue
                defense = load_defense_dna(team_name, team_data)
                if defense:
                    results[get_team_key(team_name)] = defense
    
    logger.info(f"Chargé {len(results)} DefenseDNA")
    return results
