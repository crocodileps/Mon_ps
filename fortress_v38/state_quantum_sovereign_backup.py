"""
THE QUANTUM SOVEREIGN V3.8 - STATE DEFINITIONS
Le "dossier patient" qui circule à travers tout le pipeline.
Créé le: 23 Décembre 2025
"""

from typing import TypedDict, Dict, List, Optional
from datetime import datetime
from enum import Enum


# ═══════════════════════════════════════════════════════════
# ENUMS - États possibles du système
# ═══════════════════════════════════════════════════════════

class ExecutionMode(Enum):
    """Mode d'exécution du système"""
    SHADOW = "shadow"      # Analyse + Log, pas d'exécution
    PAPER = "paper"        # Analyse + Log + Telegram (sans argent réel)
    LIVE = "live"          # Tout activé
    BACKTEST = "backtest"  # Simulation historique


class ProcessingStatus(Enum):
    """Statut de traitement pour l'idempotence"""
    STARTED = "started"
    NODE_0_DONE = "node_0_done"
    NODE_05_DONE = "node_05_done"
    NODE_1_DONE = "node_1_done"
    NODE_2A_DONE = "node_2a_done"
    NODE_2B_DONE = "node_2b_done"
    NODE_3_DONE = "node_3_done"
    NODE_4_DONE = "node_4_done"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    ERROR = "error"


class DataFreshness(Enum):
    """Fraîcheur des données ADN"""
    FRESH = "fresh"        # < 3 jours
    AGING = "aging"        # 3-7 jours
    STALE = "stale"        # > 7 jours


class DriftStatus(Enum):
    """Statut de dérive du modèle"""
    STABLE = "stable"
    MODERATE_DRIFT = "moderate_drift"
    CRITICAL_DRIFT = "critical_drift"
    INSUFFICIENT_DATA = "insufficient_data"


# ═══════════════════════════════════════════════════════════
# MATCHSTATE - Le TypedDict principal
# ═══════════════════════════════════════════════════════════

class MatchState(TypedDict, total=False):
    """
    Structure de données qui circule à travers tous les Nodes.
    Chaque Node enrichit ce "dossier patient".

    total=False signifie que tous les champs sont optionnels,
    ce qui permet de construire l'état progressivement.
    """

    # ═══════════════════════════════════════════════════════════
    # IDENTITÉ & MÉTADONNÉES
    # ═══════════════════════════════════════════════════════════
    metadata: Dict
    # Structure attendue:
    # {
    #   "match_id": str,
    #   "home_team": str,
    #   "away_team": str,
    #   "league": str,
    #   "kickoff_time": datetime,
    #   "model_version": "v3.8.0",
    #   "alpha_weights_version": str,
    #   "created_at": datetime
    # }

    processing_status: str      # ProcessingStatus.value
    execution_mode: str         # ExecutionMode.value

    # ═══════════════════════════════════════════════════════════
    # NODE 0 : MARKET SCANNER
    # ═══════════════════════════════════════════════════════════
    market_scan: Dict
    # Structure attendue:
    # {
    #   "is_liquid": bool,
    #   "is_trapped": bool,
    #   "steam_signal": Optional[Dict],
    #   "market_regime": "EFFICIENT" | "VOLATILE",
    #   "scan_timestamp": datetime
    # }

    # ═══════════════════════════════════════════════════════════
    # NODE 0.5 : NEWS SCRAPER (BLACK SWAN)
    # ═══════════════════════════════════════════════════════════
    black_swan_check: Dict
    # Structure attendue:
    # {
    #   "alert": bool,
    #   "reason": Optional[str],
    #   "source": Optional[str],
    #   "checked_at": datetime
    # }

    # ═══════════════════════════════════════════════════════════
    # NODE 1 : DATA LOADER + VALIDATOR
    # ═══════════════════════════════════════════════════════════
    base_dna: Dict
    # Structure attendue:
    # {
    #   "home": {xg_90, xga_90, cs_pct, resist_global, ...},
    #   "away": {xg_90, xga_90, cs_pct, resist_global, ...}
    # }

    data_freshness: Dict
    # Structure attendue:
    # {
    #   "home": "FRESH" | "AGING" | "STALE",
    #   "away": "FRESH" | "AGING" | "STALE",
    #   "home_last_update": datetime,
    #   "away_last_update": datetime
    # }

    data_validation: Dict
    # Structure attendue:
    # {
    #   "is_valid": bool,
    #   "errors": List[str],
    #   "warnings": List[str]
    # }

    context_data: Dict
    # Structure attendue:
    # {
    #   "coach_home": {...},
    #   "coach_away": {...},
    #   "absences_home": List[str],
    #   "absences_away": List[str],
    #   "referee": {...},
    #   "weather": Optional[Dict]
    # }

    # ═══════════════════════════════════════════════════════════
    # NODE 2a : RUNTIME CALCULATOR
    # ═══════════════════════════════════════════════════════════
    effective_dna: Dict
    # Structure attendue:
    # {
    #   "home": {xg_90_adjusted, attack_modifier, ...},
    #   "away": {xg_90_adjusted, attack_modifier, ...},
    #   "modifiers_applied": {
    #       "roster_impact": float,
    #       "coach_impact": float,
    #       "freshness_penalty": float
    #   }
    # }

    friction_matrix: Dict
    # Structure attendue:
    # {
    #   "friction_type": "CHAOS" | "SIEGE" | "STALEMATE" | ...,
    #   "goals_modifier": float,
    #   "corners_modifier": float,
    #   "cards_modifier": float,
    #   "btts_prob_modifier": float,
    #   "confidence_level": float
    # }

    # ═══════════════════════════════════════════════════════════
    # NODE 2b : TACTICAL BRAIN (CLAUDE)
    # ═══════════════════════════════════════════════════════════
    tactical_narrative: str

    chess_analysis: Dict
    # Structure attendue:
    # {
    #   "piece_malade_home": str,
    #   "piece_malade_away": str,
    #   "phase_critique": str,
    #   "sacrifice_probable": str,
    #   "recommended_markets": List[str]
    # }

    claude_cost: Dict
    # Structure attendue:
    # {
    #   "input_tokens": int,
    #   "output_tokens": int,
    #   "cost_usd": float
    # }

    # ═══════════════════════════════════════════════════════════
    # NODE 3 : QUANT ENGINE
    # ═══════════════════════════════════════════════════════════
    mc_results: Dict
    # Structure attendue:
    # {
    #   "simulations": int,
    #   "home_win_prob": float,
    #   "draw_prob": float,
    #   "away_win_prob": float,
    #   "over25_prob": float,
    #   "btts_prob": float,
    #   "volatility_penalty": float
    # }

    consensus_probs: Dict
    # Structure attendue:
    # {
    #   "model_1": {...},
    #   "model_2": {...},
    #   ...
    #   "weighted_consensus": {...}
    # }

    # ═══════════════════════════════════════════════════════════
    # NODE 4 : PORTFOLIO MANAGER
    # ═══════════════════════════════════════════════════════════
    alpha_hunter_report: Dict
    # Structure attendue:
    # {
    #   "total_markets_scanned": int,
    #   "markets_passing_strict": int,
    #   "filter_level_used": str,
    #   "top_30": List[Dict],
    #   "best_opportunity": Optional[Dict]
    # }

    convergence_result: Dict
    # Structure attendue:
    # {
    #   "consensus_value": float,
    #   "std_dev": float,
    #   "convergence_score": float,
    #   "primary_conflict": str,
    #   "volatility_penalty": float
    # }

    seasonality_adjustment: Dict
    # Structure attendue:
    # {
    #   "month": int,
    #   "season_phase": str,
    #   "confidence_penalty": float,
    #   "applied": bool
    # }

    # ═══════════════════════════════════════════════════════════
    # DÉCISION FINALE
    # ═══════════════════════════════════════════════════════════
    recommendation: Dict
    # Structure attendue:
    # {
    #   "action": "BET" | "SKIP" | "PENDING_HUMAN",
    #   "market": str,
    #   "odds": float,
    #   "probability": float,
    #   "edge": float,
    #   "stake": float,
    #   "reason": str,
    #   "confidence_final": float
    # }

    # ═══════════════════════════════════════════════════════════
    # CIRCUIT BREAKERS
    # ═══════════════════════════════════════════════════════════
    circuit_breakers: Dict
    # Structure attendue:
    # {
    #   "budget_ok": bool,
    #   "drawdown_ok": bool,
    #   "streak_ok": bool,
    #   "convergence_ok": bool,
    #   "all_passed": bool,
    #   "blocked_reason": Optional[str]
    # }

    # ═══════════════════════════════════════════════════════════
    # ERREURS & LOGS
    # ═══════════════════════════════════════════════════════════
    errors: List[Dict]
    # Structure attendue:
    # [{
    #   "node": str,
    #   "error": str,
    #   "severity": str,
    #   "timestamp": datetime
    # }]

    warnings: List[str]
    processing_time_ms: int


# ═══════════════════════════════════════════════════════════
# FACTORY FUNCTION - Crée un état initial vide
# ═══════════════════════════════════════════════════════════

def create_initial_state(
    match_id: str,
    home_team: str,
    away_team: str,
    league: str,
    kickoff_time: datetime,
    execution_mode: ExecutionMode = ExecutionMode.SHADOW
) -> MatchState:
    """
    Crée un MatchState initial avec les métadonnées de base.
    Utilisé par le Watcher quand il détecte un nouveau match.
    """
    return MatchState(
        metadata={
            "match_id": match_id,
            "home_team": home_team,
            "away_team": away_team,
            "league": league,
            "kickoff_time": kickoff_time,
            "model_version": "v3.8.0",
            "alpha_weights_version": "2024-12-23",
            "created_at": datetime.now()
        },
        processing_status=ProcessingStatus.STARTED.value,
        execution_mode=execution_mode.value,
        errors=[],
        warnings=[]
    )
