"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║  CONTEXT LOADER - Chargement des données ContextDNA                                  ║
║  Version: 2.0                                                                        ║
║  Architecture Mon_PS - Chess Engine V2.0                                             ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

Installation: /home/Mon_ps/quantum/loaders/context_loader.py

Sources JSON:
- /home/Mon_ps/data/quantum_v2/teams_context_dna.json
- /home/Mon_ps/data/understat/team_stats.json
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
    QUANTUM_DATA,
    DATA_ROOT,
)

from quantum.models import (
    ContextDNA,
    OffensiveMetrics,
    PossessionMetrics,
    MomentumMetrics,
    HomeAwaySplits,
    ConfidentMetric,
    TimingMetric,
    DataQuality,
)

logger = logging.getLogger("quantum.loaders.context")

# ═══════════════════════════════════════════════════════════════════════════════════════
# CHEMINS DES FICHIERS
# ═══════════════════════════════════════════════════════════════════════════════════════

CONTEXT_FILES = [
    QUANTUM_DATA / "teams_context_dna.json",
    DATA_ROOT / "understat" / "team_stats.json",
    DATA_ROOT / "team_context" / "context_data.json",
]


# ═══════════════════════════════════════════════════════════════════════════════════════
# PARSING HELPERS
# ═══════════════════════════════════════════════════════════════════════════════════════

def parse_timing_metric(data: Dict[str, Any], prefix: str = "") -> Optional[TimingMetric]:
    """
    Parse les données de timing depuis un dict.
    
    Args:
        data: Données brutes
        prefix: Préfixe des clés (ex: "goals_" ou "xg_")
    """
    try:
        # Chercher les clés avec différents formats
        def get_period(period_name: str) -> float:
            keys_to_try = [
                f"{prefix}{period_name}",
                f"{prefix}_{period_name}",
                period_name,
            ]
            for key in keys_to_try:
                if key in data:
                    return safe_float(data[key])
            return 0.0
        
        return TimingMetric(
            period_0_15=get_period("0_15") or get_period("first_15"),
            period_16_30=get_period("16_30") or get_period("15_30"),
            period_31_45=get_period("31_45") or get_period("30_45"),
            period_46_60=get_period("46_60") or get_period("45_60"),
            period_61_75=get_period("61_75") or get_period("60_75"),
            period_76_90=get_period("76_90") or get_period("75_90") or get_period("last_15"),
        )
    except Exception as e:
        logger.debug(f"Impossible de parser TimingMetric: {e}")
        return None


def parse_offensive_metrics(data: Dict[str, Any]) -> OffensiveMetrics:
    """Parse les métriques offensives."""
    
    # xG per match avec confidence
    matches = safe_int(data.get("matches", data.get("matches_played", 10)))
    xg_total = safe_float(data.get("xg_total", data.get("xG", 0)))
    xg_per_match_value = xg_total / max(1, matches)
    
    return OffensiveMetrics(
        goals_scored=safe_int(data.get("goals_scored", data.get("goals", data.get("scored", 0)))),
        goals_per_match=safe_float(data.get("goals_per_match", data.get("gpg", 0))),
        xg_total=xg_total,
        xg_per_match=ConfidentMetric(value=xg_per_match_value, sample_size=matches),
        goals_minus_xg=safe_float(data.get("goals_minus_xg", data.get("xgDiff", 0))),
        conversion_rate=clamp(safe_float(data.get("conversion_rate", data.get("shot_conversion", 0))), 0, 100),
        shots_total=safe_int(data.get("shots_total", data.get("shots", 0))),
        shots_per_match=safe_float(data.get("shots_per_match", data.get("spm", 0))),
        shots_on_target_per_match=safe_float(data.get("shots_on_target_per_match", data.get("sotpm", 0))),
        shot_accuracy=clamp(safe_float(data.get("shot_accuracy", 0)), 0, 100),
        big_chances_created=safe_int(data.get("big_chances_created", data.get("big_chances", 0))),
        big_chances_missed=safe_int(data.get("big_chances_missed", 0)),
        big_chance_conversion=clamp(safe_float(data.get("big_chance_conversion", 0)), 0, 100),
        goals_timing=parse_timing_metric(data.get("goals_timing", {}), "goals_"),
        xg_timing=parse_timing_metric(data.get("xg_timing", {}), "xg_"),
    )


def parse_possession_metrics(data: Dict[str, Any]) -> PossessionMetrics:
    """Parse les métriques de possession."""
    
    return PossessionMetrics(
        possession_avg=clamp(safe_float(data.get("possession_avg", data.get("possession", 50))), 0, 100),
        possession_home=clamp(safe_float(data.get("possession_home", data.get("possession_h", 50))), 0, 100),
        possession_away=clamp(safe_float(data.get("possession_away", data.get("possession_a", 50))), 0, 100),
        passes_per_match=safe_float(data.get("passes_per_match", data.get("passes", 0))),
        pass_accuracy=clamp(safe_float(data.get("pass_accuracy", data.get("pass_acc", 0))), 0, 100),
        progressive_passes_per_match=safe_float(data.get("progressive_passes_per_match", data.get("prog_passes", 0))),
        progressive_carries_per_match=safe_float(data.get("progressive_carries_per_match", data.get("prog_carries", 0))),
        touches_in_box_per_match=safe_float(data.get("touches_in_box_per_match", data.get("touches_box", 0))),
        direct_speed_index=clamp(safe_float(data.get("direct_speed_index", data.get("directness", 50))), 0, 100),
    )


def parse_momentum_metrics(data: Dict[str, Any]) -> MomentumMetrics:
    """Parse les métriques de momentum."""
    
    return MomentumMetrics(
        last_5_points=safe_int(data.get("last_5_points", data.get("l5_points", data.get("form_points", 0)))),
        last_5_goals_for=safe_int(data.get("last_5_goals_for", data.get("l5_gf", 0))),
        last_5_goals_against=safe_int(data.get("last_5_goals_against", data.get("l5_ga", 0))),
        last_5_xg=safe_float(data.get("last_5_xg", data.get("l5_xg", 0))),
        last_5_xga=safe_float(data.get("last_5_xga", data.get("l5_xga", 0))),
        last_10_points=safe_int(data.get("last_10_points", data.get("l10_points", 0))),
        last_10_xg=safe_float(data.get("last_10_xg", data.get("l10_xg", 0))),
        last_10_xga=safe_float(data.get("last_10_xga", data.get("l10_xga", 0))),
        unbeaten_streak=safe_int(data.get("unbeaten_streak", data.get("unbeaten", 0))),
        winless_streak=safe_int(data.get("winless_streak", data.get("winless", 0))),
        clean_sheet_streak=safe_int(data.get("clean_sheet_streak", data.get("cs_streak", 0))),
        scoring_streak=safe_int(data.get("scoring_streak", data.get("scoring", 0))),
        last_5_results=data.get("last_5_results", data.get("form", "")),
    )


def parse_home_away_splits(data: Dict[str, Any]) -> HomeAwaySplits:
    """Parse les splits home/away."""
    
    # Données home
    home_data = data.get("home", {})
    away_data = data.get("away", {})
    
    return HomeAwaySplits(
        # Home
        home_matches=safe_int(home_data.get("matches", data.get("home_matches", 0))),
        home_wins=safe_int(home_data.get("wins", data.get("home_wins", 0))),
        home_draws=safe_int(home_data.get("draws", data.get("home_draws", 0))),
        home_losses=safe_int(home_data.get("losses", data.get("home_losses", 0))),
        home_goals_for=safe_int(home_data.get("goals_for", data.get("home_gf", 0))),
        home_goals_against=safe_int(home_data.get("goals_against", data.get("home_ga", 0))),
        home_xg=safe_float(home_data.get("xg", data.get("home_xg", 0))),
        home_xga=safe_float(home_data.get("xga", data.get("home_xga", 0))),
        home_points_per_match=safe_float(home_data.get("ppg", data.get("home_ppg", 0))),
        
        # Away
        away_matches=safe_int(away_data.get("matches", data.get("away_matches", 0))),
        away_wins=safe_int(away_data.get("wins", data.get("away_wins", 0))),
        away_draws=safe_int(away_data.get("draws", data.get("away_draws", 0))),
        away_losses=safe_int(away_data.get("losses", data.get("away_losses", 0))),
        away_goals_for=safe_int(away_data.get("goals_for", data.get("away_gf", 0))),
        away_goals_against=safe_int(away_data.get("goals_against", data.get("away_ga", 0))),
        away_xg=safe_float(away_data.get("xg", data.get("away_xg", 0))),
        away_xga=safe_float(away_data.get("xga", data.get("away_xga", 0))),
        away_points_per_match=safe_float(away_data.get("ppg", data.get("away_ppg", 0))),
    )


# ═══════════════════════════════════════════════════════════════════════════════════════
# LOADER PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════════════

def load_context_dna(team_name: str, data: Dict[str, Any] = None) -> Optional[ContextDNA]:
    """
    Charge un ContextDNA depuis les données JSON.
    
    Args:
        team_name: Nom de l'équipe
        data: Données pré-chargées (optionnel, sinon cherche dans les fichiers)
        
    Returns:
        ContextDNA ou None si échec
    """
    try:
        # Si pas de données fournies, chercher dans les fichiers
        if data is None:
            data = find_team_context_data(team_name)
            if data is None:
                logger.warning(f"Aucune donnée context trouvée pour {team_name}")
                return None
        
        # Normaliser le nom
        normalized = normalize_team_name(team_name)
        
        # Parser les composants
        offensive = parse_offensive_metrics(data.get("offensive", data))
        possession = parse_possession_metrics(data.get("possession", data))
        momentum = parse_momentum_metrics(data.get("momentum", data.get("form", {})))
        home_away = parse_home_away_splits(data)
        
        # Calculer la qualité des données
        expected_fields = ["xg_total", "goals_scored", "possession", "matches"]
        quality = calculate_data_quality(data, expected_fields)
        
        return ContextDNA(
            team_name=normalized,
            team_normalized=get_team_key(normalized),
            league=data.get("league", data.get("competition", "")),
            season=data.get("season", "2024-2025"),
            offensive=offensive,
            possession=possession,
            momentum=momentum,
            home_away=home_away,
            matches_analyzed=safe_int(data.get("matches", data.get("matches_played", 0))),
            data_quality=DataQuality(quality),
            last_updated=datetime.utcnow(),
        )
        
    except Exception as e:
        logger.error(f"Erreur chargement ContextDNA pour {team_name}: {e}")
        return None


def find_team_context_data(team_name: str) -> Optional[Dict[str, Any]]:
    """
    Cherche les données d'une équipe dans les fichiers JSON.
    
    Args:
        team_name: Nom de l'équipe
        
    Returns:
        Données brutes ou None
    """
    normalized = normalize_team_name(team_name)
    key = get_team_key(team_name)
    
    for filepath in CONTEXT_FILES:
        if not filepath.exists():
            continue
            
        data = load_json(filepath)
        if not data:
            continue
        
        # Chercher l'équipe avec différentes clés
        for search_key in [normalized, key, team_name, team_name.lower()]:
            if search_key in data:
                return data[search_key]
            
            # Chercher dans une liste
            if isinstance(data, list):
                for item in data:
                    item_name = item.get("team", item.get("team_name", item.get("name", "")))
                    if get_team_key(item_name) == key or item_name.lower() == team_name.lower():
                        return item
            
            # Chercher dans teams
            if "teams" in data:
                teams = data["teams"]
                if isinstance(teams, dict) and search_key in teams:
                    return teams[search_key]
                elif isinstance(teams, list):
                    for item in teams:
                        item_name = item.get("team", item.get("team_name", item.get("name", "")))
                        if get_team_key(item_name) == key:
                            return item
    
    return None


def load_all_context_dna(league: str = None) -> Dict[str, ContextDNA]:
    """
    Charge tous les ContextDNA disponibles.
    
    Args:
        league: Filtrer par ligue (optionnel)
        
    Returns:
        Dict[team_key, ContextDNA]
    """
    results = {}
    
    for filepath in CONTEXT_FILES:
        if not filepath.exists():
            continue
            
        data = load_json(filepath)
        if not data:
            continue
        
        # Gérer différents formats
        teams_data = data.get("teams", data) if isinstance(data, dict) else data
        
        if isinstance(teams_data, dict):
            for team_name, team_data in teams_data.items():
                if league and team_data.get("league", "") != league:
                    continue
                    
                context = load_context_dna(team_name, team_data)
                if context:
                    results[get_team_key(team_name)] = context
                    
        elif isinstance(teams_data, list):
            for team_data in teams_data:
                team_name = team_data.get("team", team_data.get("team_name", ""))
                if not team_name:
                    continue
                    
                if league and team_data.get("league", "") != league:
                    continue
                    
                context = load_context_dna(team_name, team_data)
                if context:
                    results[get_team_key(team_name)] = context
    
    logger.info(f"Chargé {len(results)} ContextDNA")
    return results
