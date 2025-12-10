"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║  TEAM LOADER - Agrégateur Principal de tous les DNA                                  ║
║  Version: 2.0                                                                        ║
║  Architecture Mon_PS - Chess Engine V2.0                                             ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

Installation: /home/Mon_ps/quantum/loaders/team_loader.py

Usage:
    from quantum.loaders import load_team, load_all_teams
    
    # Charger une équipe
    liverpool = load_team("Liverpool")
    print(liverpool.overall_strength_score)
    print(liverpool.betting_signal)
    
    # Charger toutes les équipes d'une ligue
    premier_league = load_all_teams(league="Premier League")
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from functools import lru_cache

from .base_loader import (
    load_json,
    normalize_team_name,
    get_team_key,
    safe_float,
    safe_int,
    calculate_data_quality,
    get_global_index,
    DATA_ROOT,
    QUANTUM_DATA,
)

from .context_loader import load_context_dna, find_team_context_data
from .defense_loader import load_defense_dna, find_team_defense_data
from .goalkeeper_loader import load_goalkeeper_dna, find_team_goalkeeper_data
from .variance_loader import load_variance_dna, find_team_variance_data
from .coach_loader import load_coach_dna, find_team_coach_data

from quantum.models import (
    TeamDNA,
    TeamIdentity,
    ContextDNA,
    DefenseDNA,
    GoalkeeperDNA,
    VarianceDNA,
    ExploitProfile,
    CoachDNA,
    DataQuality,
)

logger = logging.getLogger("quantum.loaders.team")

# ═══════════════════════════════════════════════════════════════════════════════════════
# CHEMINS DES FICHIERS
# ═══════════════════════════════════════════════════════════════════════════════════════

TEAM_FILES = [
    QUANTUM_DATA / "teams_master.json",
    QUANTUM_DATA / "team_index.json",
    DATA_ROOT / "teams" / "team_registry.json",
]


# ═══════════════════════════════════════════════════════════════════════════════════════
# TEAM IDENTITY LOADER
# ═══════════════════════════════════════════════════════════════════════════════════════

def load_team_identity(team_name: str, data: Dict[str, Any] = None) -> TeamIdentity:
    """
    Charge l'identité d'une équipe.
    
    Args:
        team_name: Nom de l'équipe
        data: Données pré-chargées (optionnel)
        
    Returns:
        TeamIdentity
    """
    if data is None:
        data = {}
    
    normalized = normalize_team_name(team_name)
    
    return TeamIdentity(
        name=normalized,
        name_normalized=get_team_key(normalized),
        aliases=data.get("aliases", []),
        league=data.get("league", data.get("competition", "")),
        league_tier=data.get("league_tier", "TOP_5"),
        current_position=safe_int(data.get("position", data.get("rank", 0))),
        season=data.get("season", "2024-2025"),
        understat_id=safe_int(data.get("understat_id")) if data.get("understat_id") else None,
        fotmob_id=safe_int(data.get("fotmob_id")) if data.get("fotmob_id") else None,
        sofascore_id=safe_int(data.get("sofascore_id")) if data.get("sofascore_id") else None,
    )


# ═══════════════════════════════════════════════════════════════════════════════════════
# EXPLOIT PROFILE BUILDER
# ═══════════════════════════════════════════════════════════════════════════════════════

def build_exploit_profile(
    team_name: str,
    defense: Optional[DefenseDNA] = None,
    goalkeeper: Optional[GoalkeeperDNA] = None,
    context: Optional[ContextDNA] = None,
    variance: Optional[VarianceDNA] = None,
    coach: Optional[CoachDNA] = None,
) -> Optional[ExploitProfile]:
    """
    Construit un ExploitProfile à partir des autres DNA.
    
    Note: ExploitProfile est dérivé des autres DNA, pas d'un fichier JSON séparé.
    """
    from quantum.models import (
        ExploitProfile,
        IdentifiedWeakness,
        MarketEdge,
        TimingExploits,
        SetPieceExploits,
        MatchupVulnerabilities,
    )
    
    try:
        weaknesses = []
        market_edges = {}
        
        # ─────────────────────────────────────────────────────────────────────────────
        # FAIBLESSES DÉFENSIVES
        # ─────────────────────────────────────────────────────────────────────────────
        
        if defense:
            # Set pieces
            if defense.zones.set_piece_vulnerability in ["CRITICAL", "HIGH"]:
                weaknesses.append(IdentifiedWeakness(
                    weakness_type="SET_PIECES",
                    severity=defense.zones.set_piece_vulnerability,
                    source="defense",
                    description="Vulnérable sur coups de pied arrêtés",
                    affected_markets=["CORNERS_OVER", "FIRST_GOALSCORER_DEFENDER"],
                    edge_boost_pct=8.0 if defense.zones.set_piece_vulnerability == "CRITICAL" else 5.0,
                    confidence=0.7,
                ))
            
            # Counter attacks
            if defense.zones.counter_attack_vulnerability in ["CRITICAL", "HIGH"]:
                weaknesses.append(IdentifiedWeakness(
                    weakness_type="COUNTER_ATTACKS",
                    severity=defense.zones.counter_attack_vulnerability,
                    source="defense",
                    description="Vulnérable aux contres rapides",
                    affected_markets=["BTTS_YES", "OVER_25"],
                    edge_boost_pct=6.0,
                    confidence=0.65,
                ))
            
            # Pressing
            if defense.pressing.pressing_resistance_profile in ["VULNERABLE", "COLLAPSE_PRONE"]:
                weaknesses.append(IdentifiedWeakness(
                    weakness_type="HIGH_PRESS",
                    severity="HIGH" if defense.pressing.pressing_resistance_profile == "COLLAPSE_PRONE" else "MODERATE",
                    source="defense",
                    description="Ne résiste pas au pressing haut",
                    affected_markets=["FIRST_HALF_GOALS", "BTTS_YES"],
                    edge_boost_pct=5.0,
                    confidence=0.6,
                ))
            
            # Weak side
            if defense.zones.weak_side != "BALANCED":
                weaknesses.append(IdentifiedWeakness(
                    weakness_type=f"{defense.zones.weak_side}_SIDE",
                    severity="MODERATE",
                    source="defense",
                    description=f"Côté {defense.zones.weak_side.lower()} vulnérable",
                    affected_markets=["ANYTIME_SCORER_WINGER"],
                    edge_boost_pct=4.0,
                    confidence=0.55,
                ))
        
        # ─────────────────────────────────────────────────────────────────────────────
        # FAIBLESSES GOALKEEPER
        # ─────────────────────────────────────────────────────────────────────────────
        
        if goalkeeper:
            if goalkeeper.shot_stopping.shot_stopping_tier in ["BELOW_AVERAGE", "LIABILITY"]:
                weaknesses.append(IdentifiedWeakness(
                    weakness_type="GOALKEEPER",
                    severity="HIGH" if goalkeeper.shot_stopping.shot_stopping_tier == "LIABILITY" else "MODERATE",
                    source="goalkeeper",
                    description=f"Gardien {goalkeeper.shot_stopping.shot_stopping_tier}",
                    affected_markets=["OVER_25", "BTTS_YES"],
                    edge_boost_pct=5.0,
                    confidence=0.6,
                ))
            
            if goalkeeper.sweeping.aerial_dominance == "WEAK":
                weaknesses.append(IdentifiedWeakness(
                    weakness_type="AERIAL_GK",
                    severity="MODERATE",
                    source="goalkeeper",
                    description="Gardien faible aériennement",
                    affected_markets=["CORNERS_OVER", "SET_PIECE_GOAL"],
                    edge_boost_pct=4.0,
                    confidence=0.55,
                ))
        
        # ─────────────────────────────────────────────────────────────────────────────
        # TIMING EXPLOITS
        # ─────────────────────────────────────────────────────────────────────────────
        
        timing = TimingExploits()
        
        if defense and defense.core.goals_conceded_timing:
            timing_data = defense.core.goals_conceded_timing
            
            # Late game weakness
            if timing_data.late_game_ratio > 0.35:
                timing.weak_last_15 = True
                timing.goals_conceded_last_15_pct = timing_data.late_game_ratio * 100
                
                weaknesses.append(IdentifiedWeakness(
                    weakness_type="LATE_COLLAPSE",
                    severity="HIGH" if timing_data.late_game_ratio > 0.45 else "MODERATE",
                    source="defense",
                    description="Encaisse beaucoup en fin de match",
                    affected_markets=["GOAL_76_90", "TEAM_TO_SCORE_LAST"],
                    edge_boost_pct=7.0,
                    confidence=0.65,
                ))
            
            # Early game weakness
            if timing_data.period_0_15 / max(1, sum([
                timing_data.period_0_15, timing_data.period_16_30, timing_data.period_31_45,
                timing_data.period_46_60, timing_data.period_61_75, timing_data.period_76_90
            ])) > 0.25:
                timing.weak_first_15 = True
        
        # ─────────────────────────────────────────────────────────────────────────────
        # SET PIECE EXPLOITS
        # ─────────────────────────────────────────────────────────────────────────────
        
        set_pieces = SetPieceExploits()
        
        if defense:
            set_pieces.goals_from_set_pieces_pct = defense.zones.goals_from_set_pieces
            set_pieces.aerial_duels_lost_pct = (
                100 - (defense.actions.aerial_duels_won_rate if defense.actions else 50)
            )
        
        if context:
            # Force offensive sur set pieces (approximation)
            set_pieces.set_piece_xg_per_match = context.offensive.xg_per_match.value * 0.25
        
        # ─────────────────────────────────────────────────────────────────────────────
        # MATCHUP VULNERABILITIES
        # ─────────────────────────────────────────────────────────────────────────────
        
        matchups = MatchupVulnerabilities()
        
        if defense and defense.pressing.pressing_resistance_profile in ["VULNERABLE", "COLLAPSE_PRONE"]:
            matchups.weak_vs_pressing = True
        
        if defense and defense.zones.counter_attack_vulnerability in ["CRITICAL", "HIGH"]:
            matchups.weak_vs_counter = True
        
        if defense and defense.zones.aerial_vulnerability in ["CRITICAL", "HIGH"]:
            matchups.weak_vs_aerial = True
        
        # ─────────────────────────────────────────────────────────────────────────────
        # MARKET EDGES (basés sur les faiblesses)
        # ─────────────────────────────────────────────────────────────────────────────
        
        # Over 2.5
        over_25_edge = 0.0
        if context and context.attack_profile.value in ["ELITE", "DANGEROUS"]:
            over_25_edge += 3.0
        if defense and defense.defense_profile.value in ["LEAKY", "CATASTROPHIC"]:
            over_25_edge += 4.0
        if goalkeeper and goalkeeper.shot_stopping.shot_stopping_tier in ["BELOW_AVERAGE", "LIABILITY"]:
            over_25_edge += 2.0
        
        if over_25_edge > 0:
            market_edges["OVER_25"] = MarketEdge(
                market="OVER_25",
                base_edge_pct=over_25_edge,
                total_edge_pct=over_25_edge,
                confidence=0.6,
            )
        
        # BTTS Yes
        btts_edge = 0.0
        if context and context.attack_profile.value in ["ELITE", "DANGEROUS"]:
            btts_edge += 2.0
        if defense and defense.defense_profile.value in ["LEAKY", "CATASTROPHIC"]:
            btts_edge += 3.0
        
        if btts_edge > 0:
            market_edges["BTTS_YES"] = MarketEdge(
                market="BTTS_YES",
                base_edge_pct=btts_edge,
                total_edge_pct=btts_edge,
                confidence=0.55,
            )
        
        # ─────────────────────────────────────────────────────────────────────────────
        # BUILD FINAL PROFILE
        # ─────────────────────────────────────────────────────────────────────────────
        
        critical_count = sum(1 for w in weaknesses if w.severity == "CRITICAL")
        actionable_count = sum(1 for w in weaknesses if w.is_actionable)
        
        return ExploitProfile(
            team_name=normalize_team_name(team_name),
            team_normalized=get_team_key(team_name),
            weaknesses=weaknesses,
            market_edges=market_edges,
            timing=timing,
            set_pieces=set_pieces,
            matchups=matchups,
            total_weaknesses_count=len(weaknesses),
            critical_weaknesses_count=critical_count,
            actionable_markets_count=len([e for e in market_edges.values() if e.is_bet_worthy]),
            data_quality=DataQuality.MODERATE,
            last_updated=datetime.utcnow(),
        )
        
    except Exception as e:
        logger.error(f"Erreur construction ExploitProfile pour {team_name}: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════════════
# LOADER PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════════════

def load_team(team_name: str, use_cache: bool = True) -> Optional[TeamDNA]:
    """
    Charge un TeamDNA complet en agrégeant tous les DNA.
    
    Args:
        team_name: Nom de l'équipe
        use_cache: Utiliser le cache (défaut True)
        
    Returns:
        TeamDNA complet ou None si échec
    """
    try:
        # Vérifier le cache
        if use_cache:
            index = get_global_index()
            cached = index.get_team(team_name)
            if cached:
                logger.debug(f"Cache hit pour {team_name}")
                return cached
        
        normalized = normalize_team_name(team_name)
        key = get_team_key(team_name)
        
        logger.info(f"Chargement TeamDNA pour {normalized}...")
        
        # Chercher les données de base
        base_data = find_team_base_data(team_name)
        
        # Charger chaque composant
        context = load_context_dna(team_name)
        defense = load_defense_dna(team_name)
        goalkeeper = load_goalkeeper_dna(team_name)
        variance = load_variance_dna(team_name)
        coach = load_coach_dna(team_name)
        
        # Construire ExploitProfile
        exploit = build_exploit_profile(
            team_name,
            defense=defense,
            goalkeeper=goalkeeper,
            context=context,
            variance=variance,
            coach=coach,
        )
        
        # Identity
        identity = load_team_identity(team_name, base_data or {})
        
        # Stats de base
        points = safe_int(base_data.get("points", base_data.get("pts", 0))) if base_data else 0
        matches = safe_int(base_data.get("matches", base_data.get("played", 0))) if base_data else 0
        wins = safe_int(base_data.get("wins", base_data.get("w", 0))) if base_data else 0
        draws = safe_int(base_data.get("draws", base_data.get("d", 0))) if base_data else 0
        losses = safe_int(base_data.get("losses", base_data.get("l", 0))) if base_data else 0
        gf = safe_int(base_data.get("goals_for", base_data.get("gf", base_data.get("GF", 0)))) if base_data else 0
        ga = safe_int(base_data.get("goals_against", base_data.get("ga", base_data.get("GA", 0)))) if base_data else 0
        
        # xG totaux
        xg = context.offensive.xg_total if context else 0
        xga = defense.core.xga_total if defense else 0
        
        # Calculer la qualité globale
        components_present = sum([
            1 if context else 0,
            1 if defense else 0,
            1 if goalkeeper else 0,
            1 if variance else 0,
            1 if coach else 0,
        ])
        completeness = components_present / 5 * 100
        
        if completeness >= 80:
            quality = DataQuality.HIGH
        elif completeness >= 60:
            quality = DataQuality.MODERATE
        elif completeness >= 40:
            quality = DataQuality.LOW
        else:
            quality = DataQuality.INSUFFICIENT
        
        # Construire TeamDNA
        team_dna = TeamDNA(
            identity=identity,
            context=context,
            defense=defense,
            goalkeeper=goalkeeper,
            variance=variance,
            exploit=exploit,
            coach=coach,
            points=points,
            matches_played=matches,
            wins=wins,
            draws=draws,
            losses=losses,
            goals_for=gf,
            goals_against=ga,
            xg_total=xg,
            xga_total=xga,
            data_quality=quality,
            data_completeness=completeness,
            last_updated=datetime.utcnow(),
        )
        
        # Mettre en cache
        if use_cache:
            index.register_team(normalized, team_dna)
        
        logger.info(f"✅ TeamDNA chargé: {normalized} (completeness: {completeness:.0f}%)")
        return team_dna
        
    except Exception as e:
        logger.error(f"Erreur chargement TeamDNA pour {team_name}: {e}")
        return None


def find_team_base_data(team_name: str) -> Optional[Dict[str, Any]]:
    """Cherche les données de base d'une équipe."""
    normalized = normalize_team_name(team_name)
    key = get_team_key(team_name)
    
    for filepath in TEAM_FILES:
        if not filepath.exists():
            continue
            
        data = load_json(filepath)
        if not data:
            continue
        
        for search_key in [normalized, key, team_name]:
            if search_key in data:
                return data[search_key]
    
    # Fallback: utiliser les données context/defense
    context_data = find_team_context_data(team_name)
    if context_data:
        return context_data
    
    defense_data = find_team_defense_data(team_name)
    if defense_data:
        return defense_data
    
    return None


# ═══════════════════════════════════════════════════════════════════════════════════════
# BATCH LOADERS
# ═══════════════════════════════════════════════════════════════════════════════════════

def load_all_teams(league: str = None) -> Dict[str, TeamDNA]:
    """
    Charge tous les TeamDNA disponibles.
    
    Args:
        league: Filtrer par ligue (optionnel)
        
    Returns:
        Dict[team_key, TeamDNA]
    """
    results = {}
    
    # Collecter tous les noms d'équipes
    team_names = set()
    
    # Depuis les fichiers de base
    for filepath in TEAM_FILES:
        if not filepath.exists():
            continue
            
        data = load_json(filepath)
        if not data:
            continue
        
        if isinstance(data, dict):
            for name, team_data in data.items():
                if league and team_data.get("league", "") != league:
                    continue
                team_names.add(name)
    
    # Depuis context data
    context_files = [
        QUANTUM_DATA / "teams_context_dna.json",
        DATA_ROOT / "understat" / "team_stats.json",
    ]
    
    for filepath in context_files:
        if not filepath.exists():
            continue
            
        data = load_json(filepath)
        if not data:
            continue
        
        if isinstance(data, dict):
            for name, team_data in data.items():
                if league and team_data.get("league", "") != league:
                    continue
                team_names.add(name)
    
    # Charger chaque équipe
    for name in team_names:
        team = load_team(name)
        if team:
            results[get_team_key(name)] = team
    
    logger.info(f"Chargé {len(results)} TeamDNA")
    return results


def load_teams_by_league(league: str) -> Dict[str, TeamDNA]:
    """Charge toutes les équipes d'une ligue."""
    return load_all_teams(league=league)


def preload_league(league: str) -> int:
    """
    Précharge toutes les équipes d'une ligue en cache.
    
    Returns:
        Nombre d'équipes chargées
    """
    teams = load_all_teams(league=league)
    return len(teams)


# ═══════════════════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════════════

def get_team(team_name: str) -> Optional[TeamDNA]:
    """
    Alias pour load_team avec cache par défaut.
    """
    return load_team(team_name, use_cache=True)


def list_available_teams() -> List[str]:
    """Liste tous les noms d'équipes disponibles."""
    teams = set()
    
    all_files = TEAM_FILES + [
        QUANTUM_DATA / "teams_context_dna.json",
        DATA_ROOT / "defense_dna" / "team_defense_dna_v5_1_corrected.json",
    ]
    
    for filepath in all_files:
        if not filepath.exists():
            continue
            
        data = load_json(filepath)
        if not data:
            continue
        
        if isinstance(data, dict):
            teams.update(data.keys())
    
    return sorted(teams)


def clear_cache():
    """Vide le cache global."""
    get_global_index().clear()
    logger.info("Cache vidé")
