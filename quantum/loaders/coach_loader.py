"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║  COACH LOADER - Chargement des données CoachDNA                                      ║
║  Version: 2.0                                                                        ║
║  Architecture Mon_PS - Chess Engine V2.0                                             ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

Installation: /home/Mon_ps/quantum/loaders/coach_loader.py

Sources JSON:
- /home/Mon_ps/data/coach_dna/coach_profiles.json
- /home/Mon_ps/data/quantum_v2/tactical_data.json
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
    COACH_DATA,
    DATA_ROOT,
    QUANTUM_DATA,
)

from quantum.models import (
    CoachDNA,
    TacticalFingerprint,
    SubstitutionProfile,
    GameStateReactionProfile,
    MarketImpactProfile,
    ConfidentMetric,
    TimingMetric,
    Formation,
    GameState,
    GameStateReaction,
    PublicPerceptionBias,
    DataQuality,
)

logger = logging.getLogger("quantum.loaders.coach")

# ═══════════════════════════════════════════════════════════════════════════════════════
# CHEMINS DES FICHIERS
# ═══════════════════════════════════════════════════════════════════════════════════════

COACH_FILES = [
    COACH_DATA / "coach_profiles.json",
    COACH_DATA / "coach_dna.json",
    QUANTUM_DATA / "tactical_data.json",
    DATA_ROOT / "coaches" / "coach_data.json",
]


# ═══════════════════════════════════════════════════════════════════════════════════════
# PARSING HELPERS
# ═══════════════════════════════════════════════════════════════════════════════════════

def parse_formation(value: str) -> Formation:
    """Parse une formation depuis une string."""
    if not value:
        return Formation.F_4_3_3
    
    # Nettoyer
    cleaned = value.strip().replace(" ", "").replace("-", "_")
    if not cleaned.startswith("F_"):
        cleaned = f"F_{cleaned}"
    
    # Essayer de matcher
    try:
        return Formation(cleaned)
    except ValueError:
        # Mapping des variantes communes
        mapping = {
            "F_433": Formation.F_4_3_3,
            "F_4_3_3": Formation.F_4_3_3,
            "433": Formation.F_4_3_3,
            "F_442": Formation.F_4_4_2,
            "F_4_4_2": Formation.F_4_4_2,
            "442": Formation.F_4_4_2,
            "F_4231": Formation.F_4_2_3_1,
            "F_4_2_3_1": Formation.F_4_2_3_1,
            "4231": Formation.F_4_2_3_1,
            "F_352": Formation.F_3_5_2,
            "F_3_5_2": Formation.F_3_5_2,
            "352": Formation.F_3_5_2,
            "F_343": Formation.F_3_4_3,
            "F_3_4_3": Formation.F_3_4_3,
            "343": Formation.F_3_4_3,
        }
        return mapping.get(cleaned, Formation.F_4_3_3)


def parse_perception_bias(value: str) -> PublicPerceptionBias:
    """Parse le biais de perception publique."""
    if not value:
        return PublicPerceptionBias.NEUTRAL
    
    mapping = {
        "heavily_overrated": PublicPerceptionBias.HEAVILY_OVERRATED,
        "overrated": PublicPerceptionBias.OVERRATED,
        "slightly_overrated": PublicPerceptionBias.SLIGHTLY_OVERRATED,
        "neutral": PublicPerceptionBias.NEUTRAL,
        "slightly_underrated": PublicPerceptionBias.SLIGHTLY_UNDERRATED,
        "underrated": PublicPerceptionBias.UNDERRATED,
        "heavily_underrated": PublicPerceptionBias.HEAVILY_UNDERRATED,
    }
    
    return mapping.get(value.lower().strip(), PublicPerceptionBias.NEUTRAL)


def parse_tactical_fingerprint(data: Dict[str, Any]) -> TacticalFingerprint:
    """Parse le fingerprint tactique 13D."""
    
    tact = data.get("tactical", data.get("fingerprint", data))
    
    return TacticalFingerprint(
        verticality=clamp(safe_float(tact.get("verticality", 50)), 0, 100),
        tempo=clamp(safe_float(tact.get("tempo", 50)), 0, 100),
        width_preference=clamp(safe_float(tact.get("width_preference", tact.get("width", 50))), 0, 100),
        risk_in_buildup=clamp(safe_float(tact.get("risk_in_buildup", tact.get("buildup_risk", 50))), 0, 100),
        pressing_trigger_line=clamp(safe_float(tact.get("pressing_trigger_line", tact.get("press_line", 50))), 0, 100),
        pressing_intensity=clamp(safe_float(tact.get("pressing_intensity", tact.get("press_intensity", 50))), 0, 100),
        defensive_line_height=clamp(safe_float(tact.get("defensive_line_height", tact.get("def_line", 50))), 0, 100),
        counter_press_intensity=clamp(safe_float(tact.get("counter_press_intensity", tact.get("counter_press", 50))), 0, 100),
        set_piece_focus=clamp(safe_float(tact.get("set_piece_focus", tact.get("set_pieces", 50))), 0, 100),
        tactical_flexibility=clamp(safe_float(tact.get("tactical_flexibility", tact.get("flexibility", 50))), 0, 100),
        in_game_adjustments=clamp(safe_float(tact.get("in_game_adjustments", tact.get("adaptability", 50))), 0, 100),
        youth_trust=clamp(safe_float(tact.get("youth_trust", tact.get("youth", 50))), 0, 100),
        structure_rigidity=clamp(safe_float(tact.get("structure_rigidity", tact.get("rigidity", 50))), 0, 100),
    )


def parse_timing_metric(data: Dict[str, Any]) -> Optional[TimingMetric]:
    """Parse un TimingMetric depuis un dict."""
    if not data:
        return None
    
    try:
        return TimingMetric(
            period_0_15=safe_float(data.get("0_15", data.get("first_15", 0))),
            period_16_30=safe_float(data.get("16_30", data.get("15_30", 0))),
            period_31_45=safe_float(data.get("31_45", data.get("30_45", 0))),
            period_46_60=safe_float(data.get("46_60", data.get("45_60", 0))),
            period_61_75=safe_float(data.get("61_75", data.get("60_75", 0))),
            period_76_90=safe_float(data.get("76_90", data.get("75_90", data.get("last_15", 0)))),
        )
    except:
        return None


def parse_substitution_profile(data: Dict[str, Any]) -> SubstitutionProfile:
    """Parse le profil de substitutions."""
    
    subs = data.get("substitutions", data.get("subs", data))
    
    return SubstitutionProfile(
        avg_first_sub_minute=safe_float(subs.get("avg_first_sub_minute", subs.get("first_sub", 60))),
        subs_before_60=safe_float(subs.get("subs_before_60", 0)),
        subs_60_75=safe_float(subs.get("subs_60_75", 0)),
        subs_after_75=safe_float(subs.get("subs_after_75", 0)),
        avg_subs_per_match=safe_float(subs.get("avg_subs_per_match", subs.get("avg_subs", 3))),
        sub_impact_xg_change=safe_float(subs.get("sub_impact_xg_change", subs.get("sub_impact", 0))),
        sub_timing_distribution=parse_timing_metric(subs.get("timing", {})),
        bench_depth_score=clamp(safe_float(subs.get("bench_depth_score", subs.get("bench_quality", 50))), 0, 100),
    )


def parse_game_state_reaction(state: str, data: Dict[str, Any]) -> Optional[GameStateReaction]:
    """Parse une réaction par état de jeu."""
    mapping = {
        "all_out_attack": GameStateReaction.ALL_OUT_ATTACK,
        "push": GameStateReaction.PUSH,
        "maintain": GameStateReaction.MAINTAIN,
        "sit_back": GameStateReaction.SIT_BACK,
        "park_bus": GameStateReaction.PARK_BUS,
        "chaotic": GameStateReaction.CHAOTIC,
    }
    
    value = data.get(state, data.get(f"reaction_{state}", ""))
    if isinstance(value, str):
        return mapping.get(value.lower(), GameStateReaction.MAINTAIN)
    return GameStateReaction.MAINTAIN


def parse_game_state_reactions(data: Dict[str, Any]) -> GameStateReactionProfile:
    """Parse le profil de réactions par état de jeu."""
    
    reactions = data.get("reactions", data.get("game_state", data))
    
    return GameStateReactionProfile(
        reaction_winning_1=parse_game_state_reaction("winning_1", reactions),
        reaction_winning_2plus=parse_game_state_reaction("winning_2plus", reactions),
        reaction_drawing=parse_game_state_reaction("drawing", reactions),
        reaction_losing_1=parse_game_state_reaction("losing_1", reactions),
        reaction_losing_2plus=parse_game_state_reaction("losing_2plus", reactions),
        xg_when_winning=safe_float(reactions.get("xg_when_winning", reactions.get("xg_winning", 0))),
        xg_when_drawing=safe_float(reactions.get("xg_when_drawing", reactions.get("xg_drawing", 0))),
        xg_when_losing=safe_float(reactions.get("xg_when_losing", reactions.get("xg_losing", 0))),
        xga_when_winning=safe_float(reactions.get("xga_when_winning", reactions.get("xga_winning", 0))),
        xga_when_drawing=safe_float(reactions.get("xga_when_drawing", reactions.get("xga_drawing", 0))),
        xga_when_losing=safe_float(reactions.get("xga_when_losing", reactions.get("xga_losing", 0))),
    )


def parse_market_impact(data: Dict[str, Any]) -> MarketImpactProfile:
    """Parse le profil d'impact marché."""
    
    market = data.get("market_impact", data.get("markets", data))
    
    # Parser les edges par marché
    edges = {}
    if "edges" in market:
        for market_name, edge_data in market["edges"].items():
            if isinstance(edge_data, dict):
                edges[market_name] = ConfidentMetric(
                    value=safe_float(edge_data.get("value", edge_data.get("edge", 0))),
                    sample_size=safe_int(edge_data.get("sample_size", edge_data.get("n", 10))),
                )
            else:
                edges[market_name] = ConfidentMetric(value=safe_float(edge_data), sample_size=10)
    
    return MarketImpactProfile(
        over_25_edge=edges.get("over_25", ConfidentMetric.zero()),
        under_25_edge=edges.get("under_25", ConfidentMetric.zero()),
        btts_yes_edge=edges.get("btts_yes", ConfidentMetric.zero()),
        btts_no_edge=edges.get("btts_no", ConfidentMetric.zero()),
        first_half_goals_edge=edges.get("first_half_goals", ConfidentMetric.zero()),
        second_half_goals_edge=edges.get("second_half_goals", ConfidentMetric.zero()),
        corners_over_edge=edges.get("corners_over", ConfidentMetric.zero()),
        cards_over_edge=edges.get("cards_over", ConfidentMetric.zero()),
        public_perception_bias=parse_perception_bias(market.get("perception_bias", market.get("bias", "neutral"))),
    )


# ═══════════════════════════════════════════════════════════════════════════════════════
# LOADER PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════════════

def load_coach_dna(team_name: str, data: Dict[str, Any] = None) -> Optional[CoachDNA]:
    """
    Charge un CoachDNA depuis les données JSON.
    
    Args:
        team_name: Nom de l'équipe
        data: Données pré-chargées (optionnel)
        
    Returns:
        CoachDNA ou None si échec
    """
    try:
        if data is None:
            data = find_team_coach_data(team_name)
            if data is None:
                logger.warning(f"Aucune donnée coach trouvée pour {team_name}")
                return None
        
        normalized = normalize_team_name(team_name)
        
        # Parser les composants
        fingerprint = parse_tactical_fingerprint(data)
        substitutions = parse_substitution_profile(data)
        reactions = parse_game_state_reactions(data)
        market_impact = parse_market_impact(data)
        
        # Formation
        formation = parse_formation(data.get("formation", data.get("formation_primary", "")))
        formation_alt = parse_formation(data.get("formation_secondary", data.get("formation_alt", "")))
        
        # Qualité des données
        expected_fields = ["formation", "tactical", "matches"]
        quality = calculate_data_quality(data, expected_fields)
        
        return CoachDNA(
            coach_name=data.get("coach_name", data.get("manager", data.get("name", ""))),
            coach_normalized=get_team_key(data.get("coach_name", "")),
            team_name=normalized,
            team_normalized=get_team_key(normalized),
            nationality=data.get("nationality", ""),
            formation_primary=formation,
            formation_secondary=formation_alt,
            tactical_fingerprint=fingerprint,
            substitutions=substitutions,
            game_state_reactions=reactions,
            market_impact=market_impact,
            tenure_start=data.get("tenure_start", ""),
            matches_managed=safe_int(data.get("matches_managed", data.get("matches", 0))),
            data_quality=DataQuality(quality),
            last_updated=datetime.utcnow(),
        )
        
    except Exception as e:
        logger.error(f"Erreur chargement CoachDNA pour {team_name}: {e}")
        return None


def find_team_coach_data(team_name: str) -> Optional[Dict[str, Any]]:
    """Cherche les données coach d'une équipe."""
    normalized = normalize_team_name(team_name)
    key = get_team_key(team_name)
    
    for filepath in COACH_FILES:
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
            
            if "coaches" in data:
                coaches = data["coaches"]
                if isinstance(coaches, dict) and search_key in coaches:
                    return coaches[search_key]
    
    return None


def load_all_coach_dna(league: str = None) -> Dict[str, CoachDNA]:
    """Charge tous les CoachDNA disponibles."""
    results = {}
    
    for filepath in COACH_FILES:
        if not filepath.exists():
            continue
            
        data = load_json(filepath)
        if not data:
            continue
        
        teams_data = data.get("teams", data.get("coaches", data))
        
        if isinstance(teams_data, dict):
            for team_name, team_data in teams_data.items():
                if league and team_data.get("league", "") != league:
                    continue
                coach = load_coach_dna(team_name, team_data)
                if coach:
                    results[get_team_key(team_name)] = coach
                    
        elif isinstance(teams_data, list):
            for team_data in teams_data:
                team_name = team_data.get("team", team_data.get("team_name", ""))
                if not team_name:
                    continue
                if league and team_data.get("league", "") != league:
                    continue
                coach = load_coach_dna(team_name, team_data)
                if coach:
                    results[get_team_key(team_name)] = coach
    
    logger.info(f"Chargé {len(results)} CoachDNA")
    return results
