"""
FORTRESS V3.8 - State Dataclasses pour LangGraph
================================================

Ce fichier définit TOUTES les structures de données
qui circulent entre les Nodes du graphe LangGraph.

Principe: Chaque Node reçoit un State, le modifie, et le passe au suivant.

Version: 1.0.0
Date: 24 Décembre 2025
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum


# ═══════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════

class MatchStatus(str, Enum):
    """Status du traitement d'un match."""
    PENDING = "PENDING"           # En attente
    PROCESSING = "PROCESSING"     # En cours
    COMPLETED = "COMPLETED"       # Terminé avec pick
    SKIPPED = "SKIPPED"           # Ignoré (trap, black swan, etc.)
    ERROR = "ERROR"               # Erreur technique


class SkipReason(str, Enum):
    """Raisons de skip un match."""
    TRAP_DETECTED = "TRAP_DETECTED"
    BLACK_SWAN = "BLACK_SWAN"
    LOW_LIQUIDITY = "LOW_LIQUIDITY"
    LOW_CONVERGENCE = "LOW_CONVERGENCE"
    HIGH_EXPOSURE = "HIGH_EXPOSURE"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    DATA_QUALITY = "DATA_QUALITY"
    LOSING_STREAK = "LOSING_STREAK"
    DRAWDOWN_LIMIT = "DRAWDOWN_LIMIT"


class Signal(str, Enum):
    """Signaux de trading."""
    STRONG_BUY = "STRONG_BUY"     # Edge > 5%
    BUY = "BUY"                   # Edge 2-5%
    NEUTRAL = "NEUTRAL"          # Edge < 2%
    AVOID = "AVOID"              # Contre-signal


class Confidence(str, Enum):
    """Niveaux de confiance."""
    VERY_HIGH = "VERY_HIGH"      # > 80%
    HIGH = "HIGH"                # 65-80%
    MEDIUM = "MEDIUM"            # 50-65%
    LOW = "LOW"                  # < 50%


# ═══════════════════════════════════════════════════════════════
# DATACLASSES - ENTRÉE
# ═══════════════════════════════════════════════════════════════

@dataclass
class MatchInput:
    """Données d'entrée d'un match."""
    match_id: str
    home_team: str
    away_team: str
    kickoff: datetime
    league: str
    season: str = "2024-25"
    
    # Métadonnées
    model_version: str = "v3.8"
    processing_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))


# ═══════════════════════════════════════════════════════════════
# DATACLASSES - DNA
# ═══════════════════════════════════════════════════════════════

@dataclass
class TeamDNAState:
    """État DNA d'une équipe."""
    team_name: str
    
    # DNA de base (chargé depuis JSON/DB)
    base_dna: Dict[str, Any] = field(default_factory=dict)
    
    # Ajustements runtime
    absences_impact: Dict[str, float] = field(default_factory=dict)
    coach_impact: Dict[str, float] = field(default_factory=dict)
    freshness_impact: float = 0.0
    
    # DNA final (base + ajustements)
    final_dna: Dict[str, Any] = field(default_factory=dict)
    
    # Métadonnées
    data_quality: float = 1.0  # 0-1, 1 = parfait
    confidence: Confidence = Confidence.MEDIUM
    
    def apply_adjustments(self):
        """Applique les ajustements au DNA de base."""
        self.final_dna = self.base_dna.copy()
        # Les ajustements seront appliqués par RuntimeCalculators


@dataclass 
class GoalkeeperDNAState:
    """État DNA du gardien."""
    gk_name: str
    team_name: str
    
    # Profil GK
    profile: Dict[str, Any] = field(default_factory=dict)
    panic_score: float = 0.0
    timing_profile: str = "CONSISTENT"
    
    # Exploits identifiés
    exploits: List[Dict[str, Any]] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
# DATACLASSES - FRICTION
# ═══════════════════════════════════════════════════════════════

@dataclass
class FrictionState:
    """État de la friction entre deux équipes."""
    home_profile: str  # TacticalProfile enum value
    away_profile: str
    
    # Résultat friction
    friction_score: float = 50.0
    chaos_potential: float = 0.0
    clash_type: str = "NEUTRAL"
    tempo: str = "BALANCED"
    
    # Marchés recommandés/évités
    recommended_markets: List[str] = field(default_factory=list)
    avoid_markets: List[str] = field(default_factory=list)
    
    # Multiplicateurs
    goals_multiplier: float = 1.0
    btts_multiplier: float = 1.0


# ═══════════════════════════════════════════════════════════════
# DATACLASSES - QUANT ENGINE
# ═══════════════════════════════════════════════════════════════

@dataclass
class ModelVote:
    """Vote d'un modèle individuel."""
    model_name: str
    prediction: str
    probability: float
    confidence: float
    weight: float = 1.0


@dataclass
class ConsensusResult:
    """Résultat du consensus des modèles."""
    votes: List[ModelVote] = field(default_factory=list)
    
    # Consensus final
    final_prediction: str = ""
    final_probability: float = 0.0
    consensus_strength: float = 0.0  # 0-1
    
    # Détails
    agreement_ratio: float = 0.0
    dominant_model: str = ""


@dataclass
class MonteCarloResult:
    """Résultat des simulations Monte Carlo."""
    n_simulations: int = 5000
    
    # Résultats
    mean_outcome: float = 0.0
    std_outcome: float = 0.0
    confidence_interval: Tuple[float, float] = (0.0, 0.0)
    
    # Robustesse
    stability_score: float = 0.0  # 0-1
    is_robust: bool = False


@dataclass
class CLVResult:
    """Résultat du calcul CLV."""
    our_probability: float
    market_probability: float
    
    # CLV
    clv_raw: float = 0.0
    clv_adjusted: float = 0.0  # Après liquidity tax
    
    # Verdict
    has_edge: bool = False
    edge_category: str = "WEAK"  # WEAK, MEDIUM, STRONG


# ═══════════════════════════════════════════════════════════════
# DATACLASSES - SORTIE
# ═══════════════════════════════════════════════════════════════

@dataclass
class MarketPick:
    """Un pick sur un marché spécifique."""
    market_type: str
    selection: str
    
    # Probabilités
    our_probability: float
    market_probability: float
    
    # Edge
    edge_pct: float
    edge_category: str
    
    # Stake
    kelly_stake: float
    adjusted_stake: float
    stake_units: float
    
    # Méta
    confidence: Confidence = Confidence.MEDIUM
    signal: Signal = Signal.NEUTRAL


@dataclass
class PickOutput:
    """Sortie finale pour un match."""
    match_input: MatchInput
    
    # Status
    status: MatchStatus = MatchStatus.PENDING
    skip_reason: Optional[SkipReason] = None
    
    # Picks (peut être vide si skipped)
    picks: List[MarketPick] = field(default_factory=list)
    
    # Scores agrégés
    convergence_score: float = 0.0
    quality_score: float = 0.0
    
    # Narrative (optionnel, de Claude)
    narrative: str = ""
    
    # Timestamps
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    processing_time_ms: int = 0


# ═══════════════════════════════════════════════════════════════
# STATE PRINCIPAL - LANGGRAPH
# ═══════════════════════════════════════════════════════════════

@dataclass
class FortressState:
    """
    État principal qui circule entre tous les Nodes.
    
    C'est le "sac à dos" que chaque Node remplit.
    """
    
    # ─── ENTRÉE ───
    match_input: MatchInput = None
    
    # ─── NODE 0: Market Scanner ───
    market_scan_done: bool = False
    is_trap: bool = False
    liquidity_ok: bool = True
    
    # ─── NODE 0.5: News Scanner ───
    news_scan_done: bool = False
    black_swan_detected: bool = False
    news_alerts: List[str] = field(default_factory=list)
    
    # ─── NODE 1: Data Loader ───
    data_loaded: bool = False
    home_dna: Optional[TeamDNAState] = None
    away_dna: Optional[TeamDNAState] = None
    home_gk: Optional[GoalkeeperDNAState] = None
    away_gk: Optional[GoalkeeperDNAState] = None
    
    # ─── NODE 2a: Runtime Calculators ───
    runtime_done: bool = False
    friction: Optional[FrictionState] = None
    
    # ─── NODE 2b: Tactical Brain ───
    tactical_done: bool = False
    tactical_narrative: str = ""
    claude_cost_usd: float = 0.0
    
    # ─── NODE 3: Quant Engine ───
    quant_done: bool = False
    consensus: Optional[ConsensusResult] = None
    monte_carlo: Optional[MonteCarloResult] = None
    clv_results: List[CLVResult] = field(default_factory=list)
    
    # ─── NODE 4: Portfolio Manager ───
    portfolio_done: bool = False
    kelly_stakes: Dict[str, float] = field(default_factory=dict)
    exposure_check_passed: bool = True
    
    # ─── NODE 5: Auditor ───
    audit_done: bool = False
    audit_trail: Dict[str, Any] = field(default_factory=dict)
    
    # ─── SORTIE FINALE ───
    output: Optional[PickOutput] = None
    
    # ─── MÉTADONNÉES ───
    current_node: str = "START"
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def should_continue(self) -> bool:
        """Vérifie si le traitement doit continuer."""
        if self.is_trap:
            return False
        if self.black_swan_detected:
            return False
        if not self.liquidity_ok:
            return False
        if self.errors:
            return False
        return True
    
    def get_skip_reason(self) -> Optional[SkipReason]:
        """Retourne la raison du skip si applicable."""
        if self.is_trap:
            return SkipReason.TRAP_DETECTED
        if self.black_swan_detected:
            return SkipReason.BLACK_SWAN
        if not self.liquidity_ok:
            return SkipReason.LOW_LIQUIDITY
        if self.errors:
            return SkipReason.DATA_QUALITY
        return None


# ═══════════════════════════════════════════════════════════════
# FONCTIONS FACTORY
# ═══════════════════════════════════════════════════════════════

def create_initial_state(
    match_id: str,
    home_team: str,
    away_team: str,
    kickoff: datetime,
    league: str
) -> FortressState:
    """Crée un état initial pour un match."""
    match_input = MatchInput(
        match_id=match_id,
        home_team=home_team,
        away_team=away_team,
        kickoff=kickoff,
        league=league
    )
    
    return FortressState(match_input=match_input)


# ═══════════════════════════════════════════════════════════════
# POINT D'ENTRÉE TEST
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from datetime import datetime
    
    print("=" * 60)
    print("🏰 FORTRESS V3.8 - TEST STATE DATACLASSES")
    print("=" * 60)
    
    # Créer un état test
    state = create_initial_state(
        match_id="EPL_2025_LIV_ARS",
        home_team="Liverpool",
        away_team="Arsenal",
        kickoff=datetime(2025, 12, 26, 15, 0),
        league="Premier League"
    )
    
    print(f"\n📋 Match: {state.match_input.home_team} vs {state.match_input.away_team}")
    print(f"🗓️  Kickoff: {state.match_input.kickoff}")
    print(f"📊 Version: {state.match_input.model_version}")
    print(f"🔄 Current Node: {state.current_node}")
    print(f"✅ Should Continue: {state.should_continue()}")
    
    # Simuler un trap
    state.is_trap = True
    print(f"\n⚠️  After trap detection:")
    print(f"   Should Continue: {state.should_continue()}")
    print(f"   Skip Reason: {state.get_skip_reason()}")
    
    print("\n" + "=" * 60)
    print("✅ STATE DATACLASSES FONCTIONNELS")
    print("=" * 60)
