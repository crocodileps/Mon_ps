"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                    QUANTUM ORCHESTRATOR V1.0 - HEDGE FUND GRADE                       ║
╠═══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                       ║
║  Architecture:                                                                        ║
║  • 6 Modèles Ensemble avec Weighted Consensus                                        ║
║  • 11 Vecteurs DNA complets                                                          ║
║  • Monte Carlo Validation (obligatoire)                                              ║
║  • CLV + Smart Conflict Resolution                                                   ║
║  • Data Snapshot pour audit/debug                                                    ║
║  • Model Performance Tracking                                                        ║
║                                                                                       ║
║  "La confiance sans validation = arrogance. L'ensemble sans tracking = ignorance."  ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

import json
import uuid
import logging
import asyncio
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod

# Import MicroStrategy Loader (12ème vecteur DNA)
try:
    from quantum.loaders.microstrategy_loader import get_microstrategy_loader, MicroStrategyDNA
    MICROSTRATEGY_AVAILABLE = True
except ImportError:
    MICROSTRATEGY_AVAILABLE = False
    MicroStrategyDNA = None

# Import HybridDNALoader + DNAConverterV2 (connexion vraies données)
try:
    from quantum.orchestrator.hybrid_dna_loader import HybridDNALoader
    from quantum.orchestrator.dna_converter_v2 import DNAConverterV2
    from quantum.orchestrator.dataclasses_v2 import TeamDNA as TeamDNAV2
    HYBRID_DNA_AVAILABLE = True
except ImportError as e:
    HYBRID_DNA_AVAILABLE = False
    HybridDNALoader = None
    DNAConverterV2 = None
    TeamDNAV2 = None
    print(f"⚠️ HybridDNA not available: {e}")

logger = logging.getLogger("QuantumOrchestrator")


# ═══════════════════════════════════════════════════════════════════════════════════════
# ENUMS & CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════════════

class ModelName(Enum):
    """Les 7 modèles de l'ensemble"""
    TEAM_STRATEGY = "team_strategy"      # Model A: +1,434.6u validé
    QUANTUM_SCORER = "quantum_scorer"     # Model B: V2.4, r=+0.53
    MATCHUP_SCORER = "matchup_scorer"     # Model C: V3.4.2, Momentum L5
    DIXON_COLES = "dixon_coles"           # Model D: Probabilités BTTS/Over
    SCENARIOS = "scenarios"               # Model E: 20 scénarios + MC filter
    DNA_FEATURES = "dna_features"         # Model F: 11 vecteurs
    MICROSTRATEGY = "microstrategy"       # Model G: 126 marchés × HOME/AWAY - 12ème vecteur DNA

class Signal(Enum):
    """Signaux possibles des modèles"""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"
    SKIP = "SKIP"

class Conviction(Enum):
    """Niveau de conviction basé sur le consensus"""
    MAXIMUM = "MAXIMUM"      # 7/7 modèles
    STRONG = "STRONG"        # 6/7 modèles
    MODERATE = "MODERATE"    # 5/7 modèles
    WEAK = "WEAK"            # <5/7 modèles (SKIP)

class MomentumTrend(Enum):
    """Trends Momentum L5"""
    BLAZING = "BLAZING"      # Win streak ×4+
    HOT = "HOT"              # Strong positive
    WARMING = "WARMING"      # Positive
    NEUTRAL = "NEUTRAL"      # Stable
    COOLING = "COOLING"      # Negative
    FREEZING = "FREEZING"    # Strong negative

class ConflictResolution(Enum):
    """Résolution des conflits Z vs Momentum"""
    FOLLOW_Z = "FOLLOW_Z"           # Z fort (>2.5)
    FOLLOW_MOMENTUM = "FOLLOW_MOM"  # BLAZING/HOT
    ALIGNED = "ALIGNED"             # Boost ×1.15
    REDUCED_Z = "REDUCED_Z"         # Conflit, réduction

class Robustness(Enum):
    """Niveaux de robustesse Monte Carlo"""
    ROCK_SOLID = "ROCK_SOLID"
    ROBUST = "ROBUST"
    UNRELIABLE = "UNRELIABLE"
    FRAGILE = "FRAGILE"

class CLVSignal(Enum):
    """Signaux CLV"""
    SWEET_SPOT = "SWEET_SPOT"  # 5-10% = +5.21u
    GOOD = "GOOD"              # 2-5%
    DANGER = "DANGER"          # >10%
    NO_SIGNAL = "NO_SIGNAL"


# ═══════════════════════════════════════════════════════════════════════════════════════
# DATA CLASSES - IMPORTÉES DEPUIS dataclasses_v2.py (168+ métriques)
# ═══════════════════════════════════════════════════════════════════════════════════════
#
# ARCHIVE: Les anciennes dataclasses locales ont été archivées dans:
#          quantum/orchestrator/archive/dataclasses_local_legacy.py
#
# Les imports ci-dessous utilisent dataclasses_v2.py qui contient:
# - 12 vecteurs DNA complets (vs 11 avant)
# - 168+ métriques uniques (vs ~60 avant)
# - MicroStrategyDNA (12ème vecteur)
#
from quantum.orchestrator.dataclasses_v2 import (
    TeamDNA,
    MarketDNA,
    ContextDNA,
    RiskDNA,
    TemporalDNA,
    NemesisDNA,
    PsycheDNA,
    SentimentDNA,
    RosterDNA,
    PhysicalDNA,
    LuckDNA,
    ChameleonDNA,
    MicroStrategyDNA,
)


# ═══════════════════════════════════════════════════════════════════════════════════════
# DATA CLASSES - MODEL VOTES & PERFORMANCE
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class ModelVote:
    """Vote d'un modèle pour un pari"""
    model_name: ModelName
    signal: Signal
    confidence: float  # 0-100
    market: Optional[str] = None
    probability: Optional[float] = None
    reasoning: str = ""
    raw_data: Dict = field(default_factory=dict)
    
    @property
    def is_positive(self) -> bool:
        return self.signal in [Signal.STRONG_BUY, Signal.BUY]
    
    @property
    def weight_multiplier(self) -> float:
        """Multiplicateur basé sur la confiance"""
        if self.confidence >= 80:
            return 1.2
        elif self.confidence >= 60:
            return 1.0
        else:
            return 0.8

@dataclass
class ModelPerformance:
    """Performance historique d'un modèle"""
    model_name: ModelName
    total_votes: int = 0
    correct_votes: int = 0
    profit_loss: float = 0.0
    
    @property
    def accuracy(self) -> float:
        return self.correct_votes / self.total_votes if self.total_votes > 0 else 0
    
    @property
    def roi(self) -> float:
        return (self.profit_loss / self.total_votes) * 100 if self.total_votes > 0 else 0
    
    def calculate_weight(self, base_weight: float = 1.0) -> float:
        """Calcule le poids dynamique basé sur la performance"""
        if self.total_votes < 10:
            return base_weight  # Pas assez de données
        
        # Normalisation par ROI
        roi_factor = 1 + (self.roi / 100) * 0.5
        roi_factor = max(0.5, min(1.5, roi_factor))  # Clamp [0.5, 1.5]
        
        return base_weight * roi_factor


# ═══════════════════════════════════════════════════════════════════════════════════════
# DATA CLASSES - FRICTION MATRIX
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class FrictionMatrix:
    """Matrice de friction entre deux équipes"""
    home_team: str
    away_team: str
    
    # 4 types de friction
    kinetic_home: float = 50.0  # Dommage home → away
    kinetic_away: float = 50.0  # Dommage away → home
    temporal_clash: float = 50.0  # Avantage timing
    psyche_dominance: float = 50.0  # Edge mental
    physical_edge: float = 50.0  # Stamina advantage
    
    # Métriques dérivées
    chaos_potential: float = 50.0
    predicted_goals: float = 2.5
    btts_probability: float = 0.5
    
    # Scénarios détectés
    triggered_scenarios: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════════════
# DATA CLASSES - VALIDATION RESULTS
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class MonteCarloResult:
    """Résultat de validation Monte Carlo"""
    enabled: bool = True
    n_simulations: int = 5000
    validation_score: float = 0.0
    success_rate: float = 0.0
    robustness: Robustness = Robustness.FRAGILE
    stress_test_passed: bool = False
    kelly_recommendation: float = 0.0
    simulation_time_ms: float = 0.0
    
    @property
    def is_valid(self) -> bool:
        return self.robustness in [Robustness.ROCK_SOLID, Robustness.ROBUST]

@dataclass
class CLVResult:
    """Résultat de validation CLV"""
    our_odds: float
    closing_odds: float
    clv_percentage: float
    signal: CLVSignal
    
    @property
    def modifier(self) -> float:
        if self.signal == CLVSignal.SWEET_SPOT:
            return 1.20
        elif self.signal == CLVSignal.GOOD:
            return 1.0
        elif self.signal == CLVSignal.DANGER:
            return 0.80
        return 1.0

@dataclass
class SmartConflictResult:
    """Résultat de résolution de conflit Z vs Momentum"""
    z_score: float
    momentum_trend: MomentumTrend
    resolution: ConflictResolution
    stake_modifier: float
    reasoning: str


# ═══════════════════════════════════════════════════════════════════════════════════════
# DATA CLASSES - SNAPSHOT & OUTPUT
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class BetSnapshot:
    """Snapshot complet pour audit/debug (Boîte Noire)"""
    snapshot_id: str
    match_id: str
    timestamp: datetime
    
    # DNA au moment T
    home_dna: Dict
    away_dna: Dict
    
    # Friction au moment T
    friction_matrix: Dict
    
    # Votes des 6 modèles
    model_votes: Dict[str, Dict]
    model_weights: Dict[str, float]
    
    # Consensus
    consensus_score: float
    consensus_count: int
    conviction: str
    
    # Validations
    monte_carlo: Dict
    clv_validation: Dict
    smart_conflict: Dict
    
    # Cotes au moment T
    odds_snapshot: Dict
    
    # Décision finale
    final_market: str
    final_odds: float
    final_stake: float
    final_probability: float
    final_edge: float
    expected_value: float
    
    # Résultat (rempli après match)
    actual_result: Optional[str] = None
    profit_loss: Optional[float] = None
    settled_at: Optional[datetime] = None
    
    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str, indent=2)

@dataclass
class QuantumPick:
    """Output final de l'orchestrateur"""
    pick_id: str
    match_id: str
    home_team: str
    away_team: str
    date: datetime
    
    # Sélection
    market: str
    selection: str
    odds: float
    probability: float
    edge: float
    stake: float
    expected_value: float
    
    # Méta
    confidence: float
    conviction: Conviction
    consensus: str  # "5/6 models agree"
    
    # Validations
    monte_carlo_score: float
    monte_carlo_robustness: str
    clv_signal: str
    smart_conflict_resolution: str
    
    # Détails
    scenarios_detected: List[str]
    dna_signals: Dict[str, str]
    model_votes_summary: Dict[str, str]
    
    # Reasoning
    reasoning: List[str]
    
    # Snapshot ID pour audit
    snapshot_id: str
    
    def to_dict(self) -> Dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════════════
# ABSTRACT BASE CLASSES - MODELS
# ═══════════════════════════════════════════════════════════════════════════════════════

class BaseModel(ABC):
    """Interface pour tous les modèles"""
    
    @property
    @abstractmethod
    def name(self) -> ModelName:
        pass
    
    @abstractmethod
    async def generate_signal(
        self,
        home_team: str,
        away_team: str,
        home_dna: TeamDNA,
        away_dna: TeamDNA,
        friction: FrictionMatrix,
        odds: Dict[str, float],
        context: Optional[Dict] = None
    ) -> ModelVote:
        pass


# ═══════════════════════════════════════════════════════════════════════════════════════
# MODEL A: TEAM STRATEGY (+1,434.6u validé)
# ═══════════════════════════════════════════════════════════════════════════════════════

class ModelTeamStrategy(BaseModel):
    """
    Model A: Stratégie optimale par équipe
    Source: quantum.team_strategies
    Validation: +1,434.6u sur 344 stratégies
    """
    
    def __init__(self, db_pool=None):
        self.db_pool = db_pool
    
    @property
    def name(self) -> ModelName:
        return ModelName.TEAM_STRATEGY
    
    async def generate_signal(
        self,
        home_team: str,
        away_team: str,
        home_dna: TeamDNA,
        away_dna: TeamDNA,
        friction: FrictionMatrix,
        odds: Dict[str, float],
        context: Optional[Dict] = None
    ) -> ModelVote:
        """Génère le signal basé sur la meilleure stratégie de chaque équipe"""
        
        # Récupérer les stratégies des deux équipes
        home_strategy = home_dna.market if home_dna.market else None
        away_strategy = away_dna.market if away_dna.market else None
        
        best_team = None
        best_strategy = None
        best_roi = -float('inf')
        best_market = None
        
        # Comparer les stratégies (adapté pour MarketDNA V2)
        # V2 utilise: roi (au lieu de best_strategy_roi)
        #            specialists booleans (au lieu de best_strategy string)
        #            exploit_markets (au lieu de best_markets)
        if home_strategy and home_strategy.roi > best_roi:
            best_roi = home_strategy.roi
            best_team = home_team
            # Dériver best_strategy depuis les booleans V2
            if home_strategy.over_specialist:
                best_strategy = "OVER_SPECIALIST"
            elif home_strategy.under_specialist:
                best_strategy = "UNDER_SPECIALIST"
            elif home_strategy.btts_yes_specialist:
                best_strategy = "BTTS_YES"
            elif home_strategy.btts_no_specialist:
                best_strategy = "BTTS_NO"
            else:
                best_strategy = "BALANCED"
            # exploit_markets est une List[Dict], extraire le premier marché
            best_market = home_strategy.exploit_markets[0].get('market') if home_strategy.exploit_markets else None

        if away_strategy and away_strategy.roi > best_roi:
            best_roi = away_strategy.roi
            best_team = away_team
            if away_strategy.over_specialist:
                best_strategy = "OVER_SPECIALIST"
            elif away_strategy.under_specialist:
                best_strategy = "UNDER_SPECIALIST"
            elif away_strategy.btts_yes_specialist:
                best_strategy = "BTTS_YES"
            elif away_strategy.btts_no_specialist:
                best_strategy = "BTTS_NO"
            else:
                best_strategy = "BALANCED"
            best_market = away_strategy.exploit_markets[0].get('market') if away_strategy.exploit_markets else None
        
        if not best_strategy:
            return ModelVote(
                model_name=self.name,
                signal=Signal.SKIP,
                confidence=0,
                reasoning="Aucune stratégie validée trouvée"
            )
        
        # Déterminer le signal basé sur le ROI
        if best_roi >= 50:
            signal = Signal.STRONG_BUY
            confidence = min(95, 70 + best_roi / 5)
        elif best_roi >= 20:
            signal = Signal.BUY
            confidence = min(85, 60 + best_roi / 3)
        elif best_roi >= 0:
            signal = Signal.HOLD
            confidence = 50
        else:
            signal = Signal.SKIP
            confidence = 30
        
        return ModelVote(
            model_name=self.name,
            signal=signal,
            confidence=confidence,
            market=best_market,
            reasoning=f"Strategy {best_strategy} for {best_team}: ROI {best_roi:.1f}%",
            raw_data={
                "team": best_team,
                "strategy": best_strategy,
                "roi": best_roi,
                "market": best_market
            }
        )


# ═══════════════════════════════════════════════════════════════════════════════════════
# MODEL B: QUANTUM SCORER V2.4 (r=+0.53)
# ═══════════════════════════════════════════════════════════════════════════════════════

class ModelQuantumScorer(BaseModel):
    """
    Model B: Z-Score Hedge Fund Grade
    Source: quantum_scorer_v2_4.py
    Validation: r=+0.53, BUY=+11.13u/team
    """
    
    # Thresholds validés
    Z_BUY_THRESHOLD = 1.5
    Z_FADE_THRESHOLD = -1.5
    
    def __init__(self, db_pool=None):
        self.db_pool = db_pool
    
    @property
    def name(self) -> ModelName:
        return ModelName.QUANTUM_SCORER
    
    def _calculate_z_score(self, dna: TeamDNA) -> float:
        """Calcule le Z-Score d'une équipe"""
        if not dna:
            return 0.0
        
        # Composants du Z-Score
        components = []
        weights = []
        
        # Psyche DNA
        if dna.psyche:
            # CONSERVATIVE = +11.73u (premium)
            mentality_score = 1.5 if dna.psyche.mentality == "CONSERVATIVE" else 0
            components.append(mentality_score)
            weights.append(0.2)
            
            # LOW killer_instinct > HIGH (contre-intuitif)
            killer_score = 1 - dna.psyche.killer_instinct
            components.append(killer_score)
            weights.append(0.15)
        
        # Luck DNA
        if dna.luck:
            # UNLUCKY = regression UP expected
            if dna.luck.regression_direction == "UP":
                luck_score = dna.luck.regression_magnitude / 100
            else:
                luck_score = -dna.luck.regression_magnitude / 100
            components.append(luck_score)
            weights.append(0.15)
        
        # Temporal DNA
        if dna.temporal:
            diesel_score = dna.temporal.diesel_factor
            components.append(diesel_score)
            weights.append(0.1)
        
        # Context DNA
        if dna.context:
            home_score = dna.context.home_strength / 100
            components.append(home_score)
            weights.append(0.1)
        
        # Tier bonus (adapté pour V2: tier_rank est un int 1-100)
        # Mapping: tier_rank >= 85 → ELITE, >= 65 → GOLD, >= 40 → SILVER, < 40 → BRONZE
        tier_rank = getattr(dna, 'tier_rank', 50)
        if tier_rank >= 85:
            tier_score = 0.3  # ELITE
        elif tier_rank >= 65:
            tier_score = 0.2  # GOLD
        elif tier_rank >= 40:
            tier_score = 0.1  # SILVER
        else:
            tier_score = 0.0  # BRONZE
        components.append(tier_score)
        weights.append(0.15)
        
        if not components:
            return 0.0
        
        # Weighted average
        total_weight = sum(weights[:len(components)])
        z_score = sum(c * w for c, w in zip(components, weights)) / total_weight
        
        # Normalisation [-3, 3]
        return max(-3, min(3, z_score * 3))
    
    async def generate_signal(
        self,
        home_team: str,
        away_team: str,
        home_dna: TeamDNA,
        away_dna: TeamDNA,
        friction: FrictionMatrix,
        odds: Dict[str, float],
        context: Optional[Dict] = None
    ) -> ModelVote:
        """Génère le signal Z-Score"""
        
        home_z = self._calculate_z_score(home_dna)
        away_z = self._calculate_z_score(away_dna)
        z_edge = home_z - away_z
        
        # Déterminer le signal
        if z_edge >= self.Z_BUY_THRESHOLD:
            signal = Signal.STRONG_BUY
            target = home_team
            confidence = min(95, 70 + z_edge * 10)
        elif z_edge >= 0.5:
            signal = Signal.BUY
            target = home_team
            confidence = 60 + z_edge * 10
        elif z_edge <= -self.Z_BUY_THRESHOLD:
            signal = Signal.STRONG_BUY
            target = away_team
            confidence = min(95, 70 + abs(z_edge) * 10)
        elif z_edge <= -0.5:
            signal = Signal.BUY
            target = away_team
            confidence = 60 + abs(z_edge) * 10
        else:
            signal = Signal.HOLD
            target = None
            confidence = 40
        
        return ModelVote(
            model_name=self.name,
            signal=signal,
            confidence=confidence,
            reasoning=f"Z-Score: Home={home_z:.2f}, Away={away_z:.2f}, Edge={z_edge:.2f}",
            raw_data={
                "home_z": home_z,
                "away_z": away_z,
                "z_edge": z_edge,
                "target": target
            }
        )


# ═══════════════════════════════════════════════════════════════════════════════════════
# MODEL C: MATCHUP SCORER V3.4.2 (Momentum L5 + Smart Conflict)
# ═══════════════════════════════════════════════════════════════════════════════════════

class ModelMatchupScorer(BaseModel):
    """
    Model C: Momentum L5 + Smart Conflict Resolution
    Source: quantum_matchup_scorer_v3_4.py
    Validation: +10% ROI improvement
    """
    
    # Stake multipliers par trend
    TREND_MULTIPLIERS = {
        MomentumTrend.BLAZING: 1.25,
        MomentumTrend.HOT: 1.15,
        MomentumTrend.WARMING: 1.0,
        MomentumTrend.NEUTRAL: 0.85,
        MomentumTrend.COOLING: 0.0,  # SKIP
        MomentumTrend.FREEZING: 0.0  # SKIP
    }
    
    def __init__(self, db_pool=None):
        self.db_pool = db_pool
    
    @property
    def name(self) -> ModelName:
        return ModelName.MATCHUP_SCORER
    
    def _calculate_momentum(self, team_name: str, context: Optional[Dict]) -> Tuple[float, MomentumTrend, int]:
        """
        Calcule le Momentum L5
        Returns: (score, trend, streak_length)
        """
        # En production, query la DB pour les 5 derniers matchs
        # Pour le template, on utilise les données du context
        
        if not context or "momentum" not in context:
            return 50.0, MomentumTrend.NEUTRAL, 0
        
        team_momentum = context.get("momentum", {}).get(team_name, {})
        
        score = team_momentum.get("score", 50.0)
        trend_str = team_momentum.get("trend", "NEUTRAL")
        streak = team_momentum.get("streak", 0)
        
        try:
            trend = MomentumTrend[trend_str]
        except KeyError:
            trend = MomentumTrend.NEUTRAL
        
        return score, trend, streak
    
    def _resolve_conflict(self, z_score: float, momentum_trend: MomentumTrend) -> SmartConflictResult:
        """
        Smart Conflict Resolution V3.4.2
        Règles:
        1. BLAZING/HOT + Z faible → FOLLOW_MOMENTUM
        2. Z > 2.5 + pas COLD → FOLLOW_Z
        3. Aligné → ALIGNED (boost ×1.15)
        4. Z favori COLD → REDUCED_Z (50%)
        """
        
        z_is_positive = z_score > 0.5
        z_is_strong = abs(z_score) > 2.5
        momentum_is_hot = momentum_trend in [MomentumTrend.BLAZING, MomentumTrend.HOT]
        momentum_is_cold = momentum_trend in [MomentumTrend.COOLING, MomentumTrend.FREEZING]
        
        # Cas 1: Alignés
        if z_is_positive and momentum_is_hot:
            return SmartConflictResult(
                z_score=z_score,
                momentum_trend=momentum_trend,
                resolution=ConflictResolution.ALIGNED,
                stake_modifier=1.15,
                reasoning="Z et Momentum alignés → Boost"
            )
        
        # Cas 2: Z favori mais COLD
        if z_is_positive and momentum_is_cold:
            return SmartConflictResult(
                z_score=z_score,
                momentum_trend=momentum_trend,
                resolution=ConflictResolution.REDUCED_Z,
                stake_modifier=0.5,
                reasoning="Z favori mais momentum COLD → Réduction 50%"
            )
        
        # Cas 3: BLAZING/HOT override Z faible
        if momentum_is_hot and not z_is_strong:
            return SmartConflictResult(
                z_score=z_score,
                momentum_trend=momentum_trend,
                resolution=ConflictResolution.FOLLOW_MOMENTUM,
                stake_modifier=self.TREND_MULTIPLIERS[momentum_trend],
                reasoning=f"Momentum {momentum_trend.value} override Z faible"
            )
        
        # Cas 4: Z fort override momentum
        if z_is_strong and not momentum_is_cold:
            return SmartConflictResult(
                z_score=z_score,
                momentum_trend=momentum_trend,
                resolution=ConflictResolution.FOLLOW_Z,
                stake_modifier=1.0,
                reasoning=f"Z fort ({z_score:.2f}) override momentum"
            )
        
        # Cas par défaut: réduction modérée
        return SmartConflictResult(
            z_score=z_score,
            momentum_trend=momentum_trend,
            resolution=ConflictResolution.REDUCED_Z,
            stake_modifier=0.85,
            reasoning="Conflit modéré → Réduction 15%"
        )
    
    async def generate_signal(
        self,
        home_team: str,
        away_team: str,
        home_dna: TeamDNA,
        away_dna: TeamDNA,
        friction: FrictionMatrix,
        odds: Dict[str, float],
        context: Optional[Dict] = None
    ) -> ModelVote:
        """Génère le signal Momentum + Conflict Resolution"""
        
        # Calculer momentum des deux équipes
        home_score, home_trend, home_streak = self._calculate_momentum(home_team, context)
        away_score, away_trend, away_streak = self._calculate_momentum(away_team, context)
        
        # Déterminer l'équipe avec le meilleur momentum
        if home_score > away_score:
            target = home_team
            best_trend = home_trend
            best_streak = home_streak
        else:
            target = away_team
            best_trend = away_trend
            best_streak = away_streak
        
        # Skip si COOLING/FREEZING
        if best_trend in [MomentumTrend.COOLING, MomentumTrend.FREEZING]:
            return ModelVote(
                model_name=self.name,
                signal=Signal.SKIP,
                confidence=30,
                reasoning=f"Momentum {best_trend.value} → SKIP",
                raw_data={
                    "home_momentum": home_score,
                    "away_momentum": away_score,
                    "best_trend": best_trend.value
                }
            )
        
        # Générer signal
        if best_trend == MomentumTrend.BLAZING:
            signal = Signal.STRONG_BUY
            confidence = 85 + min(10, best_streak)
        elif best_trend == MomentumTrend.HOT:
            signal = Signal.BUY
            confidence = 70 + min(15, best_streak * 2)
        elif best_trend == MomentumTrend.WARMING:
            signal = Signal.BUY
            confidence = 60
        else:
            signal = Signal.HOLD
            confidence = 50
        
        return ModelVote(
            model_name=self.name,
            signal=signal,
            confidence=confidence,
            reasoning=f"{target} momentum {best_trend.value} (streak: {best_streak})",
            raw_data={
                "target": target,
                "home_momentum": home_score,
                "away_momentum": away_score,
                "home_trend": home_trend.value,
                "away_trend": away_trend.value,
                "home_streak": home_streak,
                "away_streak": away_streak,
                "best_trend": best_trend.value,
                "stake_multiplier": self.TREND_MULTIPLIERS[best_trend]
            }
        )


# ═══════════════════════════════════════════════════════════════════════════════════════
# MODEL D: DIXON-COLES (Probabilités)
# ═══════════════════════════════════════════════════════════════════════════════════════

class ModelDixonColes(BaseModel):
    """
    Model D: Probabilités BTTS/Over via Dixon-Coles
    Source: orchestrator_v11_4_god_tier.py
    """
    
    def __init__(self, db_pool=None):
        self.db_pool = db_pool
    
    @property
    def name(self) -> ModelName:
        return ModelName.DIXON_COLES
    
    def _calculate_probabilities(
        self,
        home_dna: TeamDNA,
        away_dna: TeamDNA,
        friction: FrictionMatrix
    ) -> Dict[str, float]:
        """
        Calcule les probabilités via Dixon-Coles simplifié
        En production, utilise le vrai modèle DC
        """
        
        # Lambda (expected goals) basé sur DNA
        home_attack = 1.4
        away_attack = 1.2
        
        if home_dna.context:
            home_attack *= (home_dna.context.home_strength / 70)
        if away_dna.context:
            away_attack *= (away_dna.context.away_strength / 70)
        
        # Ajustement friction
        home_attack *= (1 + friction.kinetic_home / 200)
        away_attack *= (1 + friction.kinetic_away / 200)
        
        # Calcul Poisson simplifié
        expected_total = home_attack + away_attack
        
        # Probabilités des marchés
        import math
        
        def poisson_prob(k, lam):
            return (lam ** k) * math.exp(-lam) / math.factorial(k)
        
        # Over 2.5
        prob_under_25 = sum(
            poisson_prob(h, home_attack) * poisson_prob(a, away_attack)
            for h in range(3) for a in range(3) if h + a < 3
        )
        prob_over_25 = 1 - prob_under_25
        
        # BTTS
        prob_home_scores = 1 - poisson_prob(0, home_attack)
        prob_away_scores = 1 - poisson_prob(0, away_attack)
        prob_btts = prob_home_scores * prob_away_scores
        
        # Over 3.5
        prob_under_35 = sum(
            poisson_prob(h, home_attack) * poisson_prob(a, away_attack)
            for h in range(4) for a in range(4) if h + a < 4
        )
        prob_over_35 = 1 - prob_under_35
        
        return {
            "over_25": prob_over_25,
            "under_25": 1 - prob_over_25,
            "btts_yes": prob_btts,
            "btts_no": 1 - prob_btts,
            "over_35": prob_over_35,
            "under_35": 1 - prob_over_35,
            "expected_goals": expected_total
        }
    
    async def generate_signal(
        self,
        home_team: str,
        away_team: str,
        home_dna: TeamDNA,
        away_dna: TeamDNA,
        friction: FrictionMatrix,
        odds: Dict[str, float],
        context: Optional[Dict] = None
    ) -> ModelVote:
        """Génère le signal basé sur les probabilités Dixon-Coles"""
        
        probs = self._calculate_probabilities(home_dna, away_dna, friction)
        
        # Trouver le meilleur edge
        best_market = None
        best_edge = -float('inf')
        best_prob = 0
        
        market_mapping = {
            "over_25": "over_25",
            "btts_yes": "btts_yes",
            "over_35": "over_35"
        }
        
        for market_key, odds_key in market_mapping.items():
            if odds_key in odds and odds[odds_key] > 1:
                implied_prob = 1 / odds[odds_key]
                our_prob = probs[market_key]
                edge = our_prob - implied_prob
                
                if edge > best_edge:
                    best_edge = edge
                    best_market = market_key
                    best_prob = our_prob
        
        if best_edge < 0.02:  # Seuil minimum 2%
            return ModelVote(
                model_name=self.name,
                signal=Signal.HOLD,
                confidence=40,
                reasoning="Pas d'edge significatif trouvé",
                raw_data=probs
            )
        
        # Signal basé sur l'edge
        if best_edge >= 0.10:
            signal = Signal.STRONG_BUY
            confidence = min(90, 70 + best_edge * 200)
        elif best_edge >= 0.05:
            signal = Signal.BUY
            confidence = 60 + best_edge * 200
        else:
            signal = Signal.HOLD
            confidence = 50
        
        return ModelVote(
            model_name=self.name,
            signal=signal,
            confidence=confidence,
            market=best_market,
            probability=best_prob,
            reasoning=f"Dixon-Coles: {best_market} P={best_prob:.1%}, Edge={best_edge:.1%}",
            raw_data={
                **probs,
                "best_market": best_market,
                "best_edge": best_edge
            }
        )


# ═══════════════════════════════════════════════════════════════════════════════════════
# MODEL E: 20 SCÉNARIOS (avec MC filter)
# ═══════════════════════════════════════════════════════════════════════════════════════

class ModelScenarios(BaseModel):
    """
    Model E: 20 Scénarios avec Monte Carlo Filter
    Source: quantum/services/scenario_detector.py
    Note: Seuls = -58.4u, avec MC filter = positif
    """
    
    SCENARIOS = [
        "TOTAL_CHAOS", "THE_SIEGE", "SNIPER_DUEL", "ATTRITION_WAR", "GLASS_CANNON",
        "LATE_PUNISHMENT", "EXPLOSIVE_START", "DIESEL_DUEL", "CLUTCH_KILLER",
        "FATIGUE_COLLAPSE", "PRESSING_DEATH", "PACE_EXPLOITATION", "BENCH_WARFARE",
        "CONSERVATIVE_WALL", "KILLER_INSTINCT", "COLLAPSE_ALERT", "NOTHING_TO_LOSE",
        "NEMESIS_TRAP", "PREY_HUNT", "AERIAL_RAID"
    ]
    
    def __init__(self, db_pool=None):
        self.db_pool = db_pool
    
    @property
    def name(self) -> ModelName:
        return ModelName.SCENARIOS
    
    def _detect_scenarios(
        self,
        home_dna: TeamDNA,
        away_dna: TeamDNA,
        friction: FrictionMatrix
    ) -> List[Tuple[str, float]]:
        """
        Détecte les scénarios actifs
        Returns: List of (scenario_name, confidence)
        """
        detected = []
        
        # SNIPER_DUEL: Deux équipes avec killer_instinct élevé
        if home_dna.psyche and away_dna.psyche:
            if home_dna.psyche.killer_instinct > 0.6 and away_dna.psyche.killer_instinct > 0.6:
                confidence = (home_dna.psyche.killer_instinct + away_dna.psyche.killer_instinct) / 2 * 100
                detected.append(("SNIPER_DUEL", confidence))
        
        # LATE_PUNISHMENT: diesel_factor élevé + adversaire pressing_decay
        if home_dna.temporal and away_dna.physical:
            if home_dna.temporal.diesel_factor > 0.6 and away_dna.physical.pressing_decay > 0.2:
                confidence = home_dna.temporal.diesel_factor * 100
                detected.append(("LATE_PUNISHMENT", confidence))
        
        # GLASS_CANNON: Fort en attaque, faible en défense
        if home_dna.psyche and away_dna.psyche:
            if home_dna.psyche.killer_instinct > 0.7 and home_dna.psyche.collapse_rate > 0.2:
                detected.append(("GLASS_CANNON", 70))
        
        # CONSERVATIVE_WALL: Mentality conservative
        if home_dna.psyche and home_dna.psyche.mentality == "CONSERVATIVE":
            detected.append(("CONSERVATIVE_WALL", 75))
        
        # TOTAL_CHAOS: chaos_potential élevé
        if friction.chaos_potential > 65:
            detected.append(("TOTAL_CHAOS", friction.chaos_potential))
        
        # NEMESIS_TRAP: Équipe dans nemesis_teams
        if home_dna.nemesis and away_dna.team_name in home_dna.nemesis.nemesis_teams:
            detected.append(("NEMESIS_TRAP", 80))
        
        return detected
    
    async def generate_signal(
        self,
        home_team: str,
        away_team: str,
        home_dna: TeamDNA,
        away_dna: TeamDNA,
        friction: FrictionMatrix,
        odds: Dict[str, float],
        context: Optional[Dict] = None
    ) -> ModelVote:
        """Génère le signal basé sur les scénarios détectés"""
        
        scenarios = self._detect_scenarios(home_dna, away_dna, friction)
        
        if not scenarios:
            return ModelVote(
                model_name=self.name,
                signal=Signal.HOLD,
                confidence=40,
                reasoning="Aucun scénario clair détecté",
                raw_data={"scenarios": []}
            )
        
        # Meilleur scénario
        best_scenario, best_confidence = max(scenarios, key=lambda x: x[1])
        
        # Marchés suggérés par scénario
        scenario_markets = {
            "SNIPER_DUEL": "btts_yes",
            "LATE_PUNISHMENT": "over_25",
            "GLASS_CANNON": "btts_yes",
            "CONSERVATIVE_WALL": "under_25",
            "TOTAL_CHAOS": "over_35",
            "NEMESIS_TRAP": None  # Dépend du contexte
        }
        
        market = scenario_markets.get(best_scenario)
        
        if best_confidence >= 75:
            signal = Signal.BUY
        elif best_confidence >= 60:
            signal = Signal.HOLD
        else:
            signal = Signal.HOLD
        
        return ModelVote(
            model_name=self.name,
            signal=signal,
            confidence=best_confidence,
            market=market,
            reasoning=f"Scénario {best_scenario} détecté ({best_confidence:.0f}%)",
            raw_data={
                "scenarios": scenarios,
                "best_scenario": best_scenario,
                "suggested_market": market
            }
        )


# ═══════════════════════════════════════════════════════════════════════════════════════
# MODEL F: DNA FEATURES (11 vecteurs)
# ═══════════════════════════════════════════════════════════════════════════════════════

class ModelDNAFeatures(BaseModel):
    """
    Model F: Signaux basés sur les 11 vecteurs DNA
    Exploite les insights découverts mais non utilisés
    """
    
    # Insights validés
    INSIGHTS = {
        "CONSERVATIVE_MENTALITY": {"bonus": 11.73, "market": "under_25"},
        "LOW_KILLER_INSTINCT": {"bonus": 5.0, "market": None},
        "LEAKY_KEEPER": {"bonus": 3.0, "market": "btts_yes"},
        "FORMATION_433": {"bonus": 8.08, "market": "over_25"},
        "UNLUCKY_TEAM": {"bonus": 6.0, "market": None},
        "HIGH_DIESEL_FACTOR": {"bonus": 4.0, "market": "over_25"}
    }
    
    def __init__(self, db_pool=None):
        self.db_pool = db_pool
    
    @property
    def name(self) -> ModelName:
        return ModelName.DNA_FEATURES
    
    def _extract_signals(self, dna: TeamDNA) -> List[Tuple[str, float]]:
        """Extrait les signaux des DNA"""
        signals = []
        
        if dna.psyche:
            if dna.psyche.mentality == "CONSERVATIVE":
                signals.append(("CONSERVATIVE_MENTALITY", self.INSIGHTS["CONSERVATIVE_MENTALITY"]["bonus"]))
            if dna.psyche.killer_instinct < 0.4:
                signals.append(("LOW_KILLER_INSTINCT", self.INSIGHTS["LOW_KILLER_INSTINCT"]["bonus"]))
        
        if dna.roster and dna.roster.keeper_status == "LEAKY":
            signals.append(("LEAKY_KEEPER", self.INSIGHTS["LEAKY_KEEPER"]["bonus"]))
        
        if dna.temporal and dna.temporal.diesel_factor > 0.65:
            signals.append(("HIGH_DIESEL_FACTOR", self.INSIGHTS["HIGH_DIESEL_FACTOR"]["bonus"]))
        
        if dna.luck and dna.luck.regression_direction == "UP":
            signals.append(("UNLUCKY_TEAM", self.INSIGHTS["UNLUCKY_TEAM"]["bonus"]))
        
        return signals
    
    async def generate_signal(
        self,
        home_team: str,
        away_team: str,
        home_dna: TeamDNA,
        away_dna: TeamDNA,
        friction: FrictionMatrix,
        odds: Dict[str, float],
        context: Optional[Dict] = None
    ) -> ModelVote:
        """Génère le signal basé sur les features DNA"""
        
        home_signals = self._extract_signals(home_dna)
        away_signals = self._extract_signals(away_dna)
        
        all_signals = home_signals + away_signals
        
        if not all_signals:
            return ModelVote(
                model_name=self.name,
                signal=Signal.HOLD,
                confidence=40,
                reasoning="Aucun signal DNA fort détecté",
                raw_data={}
            )
        
        # Calculer le score total
        total_bonus = sum(s[1] for s in all_signals)
        
        # Meilleur signal
        best_signal = max(all_signals, key=lambda x: x[1])
        
        if total_bonus >= 15:
            signal = Signal.STRONG_BUY
            confidence = min(90, 60 + total_bonus)
        elif total_bonus >= 8:
            signal = Signal.BUY
            confidence = 55 + total_bonus
        else:
            signal = Signal.HOLD
            confidence = 45
        
        # Marché suggéré
        market = self.INSIGHTS.get(best_signal[0], {}).get("market")
        
        return ModelVote(
            model_name=self.name,
            signal=signal,
            confidence=confidence,
            market=market,
            reasoning=f"DNA signals: {[s[0] for s in all_signals]}, Total bonus: +{total_bonus:.1f}u",
            raw_data={
                "home_signals": home_signals,
                "away_signals": away_signals,
                "total_bonus": total_bonus,
                "suggested_market": market
            }
        )


# ═══════════════════════════════════════════════════════════════════════════════════════
# WEIGHTED CONSENSUS ENGINE
# ═══════════════════════════════════════════════════════════════════════════════════════

class WeightedConsensusEngine:
    """
    Moteur de consensus pondéré
    Les modèles performants ont plus de poids
    """
    
    # Poids de base (avant ajustement dynamique)
    BASE_WEIGHTS = {
        ModelName.TEAM_STRATEGY: 1.25,  # +1,434.6u validé
        ModelName.QUANTUM_SCORER: 1.15,  # r=+0.53
        ModelName.MATCHUP_SCORER: 1.10,  # +10% ROI
        ModelName.DIXON_COLES: 1.0,
        ModelName.SCENARIOS: 0.85,  # Nécessite MC filter
        ModelName.DNA_FEATURES: 1.05
    }
    
    CONSENSUS_THRESHOLD = 0.60  # 60% du poids total
    
    def __init__(self, model_performances: Optional[Dict[ModelName, ModelPerformance]] = None):
        self.model_performances = model_performances or {}
    
    def get_weight(self, model_name: ModelName) -> float:
        """Récupère le poids d'un modèle (base ou dynamique)"""
        base = self.BASE_WEIGHTS.get(model_name, 1.0)
        
        if model_name in self.model_performances:
            return self.model_performances[model_name].calculate_weight(base)
        
        return base
    
    def evaluate(self, votes: List[ModelVote]) -> Tuple[bool, float, Conviction, Dict]:
        """
        Évalue le consensus pondéré
        
        Returns:
            (consensus_reached, consensus_score, conviction, details)
        """
        total_weight = 0
        positive_weight = 0
        vote_details = {}
        
        for vote in votes:
            weight = self.get_weight(vote.model_name)
            # Ajustement par confiance du vote
            adjusted_weight = weight * vote.weight_multiplier
            
            total_weight += adjusted_weight
            
            if vote.is_positive:
                positive_weight += adjusted_weight
            
            vote_details[vote.model_name.value] = {
                "signal": vote.signal.value,
                "confidence": vote.confidence,
                "weight": adjusted_weight,
                "contributed": vote.is_positive
            }
        
        consensus_score = positive_weight / total_weight if total_weight > 0 else 0
        consensus_count = sum(1 for v in votes if v.is_positive)
        
        # Déterminer la conviction
        if consensus_count == 7:
            conviction = Conviction.MAXIMUM
        elif consensus_count >= 6:
            conviction = Conviction.STRONG
        elif consensus_count >= 5:
            conviction = Conviction.MODERATE
        else:
            conviction = Conviction.WEAK
        
        consensus_reached = consensus_score >= self.CONSENSUS_THRESHOLD and consensus_count >= 5
        
        return consensus_reached, consensus_score, conviction, vote_details


# ═══════════════════════════════════════════════════════════════════════════════════════
# VALIDATORS
# ═══════════════════════════════════════════════════════════════════════════════════════

class MonteCarloValidator:
    """Validation Monte Carlo (obligatoire)"""
    
    def __init__(self, n_simulations: int = 5000, noise_level: float = 0.15):
        self.n_simulations = n_simulations
        self.noise_level = noise_level
    
    async def validate(
        self,
        probability: float,
        edge: float,
        confidence: float
    ) -> MonteCarloResult:
        """
        Valide via Monte Carlo
        """
        import time
        start = time.time()
        
        successes = 0
        scores = []
        
        for _ in range(self.n_simulations):
            # Ajouter du bruit
            noisy_prob = probability * (1 + np.random.uniform(-self.noise_level, self.noise_level))
            noisy_edge = edge * (1 + np.random.uniform(-self.noise_level, self.noise_level))
            noisy_conf = confidence * (1 + np.random.uniform(-self.noise_level, self.noise_level))
            
            # Calculer le score
            score = (noisy_prob * 40 + noisy_edge * 30 + noisy_conf * 30) / 100
            scores.append(score)
            
            if score >= 50 and noisy_edge > 0:
                successes += 1
        
        success_rate = successes / self.n_simulations
        validation_score = np.mean(scores)
        std_dev = np.std(scores)
        
        # Déterminer la robustesse
        if success_rate >= 0.80 and std_dev < 10:
            robustness = Robustness.ROCK_SOLID
        elif success_rate >= 0.65 and std_dev < 15:
            robustness = Robustness.ROBUST
        elif success_rate >= 0.50:
            robustness = Robustness.UNRELIABLE
        else:
            robustness = Robustness.FRAGILE
        
        # Kelly recommendation
        kelly = (edge * probability) / (1 - probability) if probability < 1 else 0
        kelly = max(0, min(0.25, kelly))  # Cap à 25%
        
        elapsed = (time.time() - start) * 1000
        
        return MonteCarloResult(
            enabled=True,
            n_simulations=self.n_simulations,
            validation_score=validation_score,
            success_rate=success_rate,
            robustness=robustness,
            stress_test_passed=robustness in [Robustness.ROCK_SOLID, Robustness.ROBUST],
            kelly_recommendation=kelly,
            simulation_time_ms=elapsed
        )


class CLVValidator:
    """Validation CLV (Closing Line Value)"""
    
    SWEET_SPOT_MIN = 0.05
    SWEET_SPOT_MAX = 0.10
    DANGER_THRESHOLD = 0.10
    
    def validate(self, our_odds: float, closing_odds: float) -> CLVResult:
        """
        Valide le CLV
        Sweet spot: 5-10% = +5.21u
        """
        if closing_odds <= 0:
            return CLVResult(
                our_odds=our_odds,
                closing_odds=closing_odds,
                clv_percentage=0,
                signal=CLVSignal.NO_SIGNAL
            )
        
        clv = (closing_odds - our_odds) / our_odds
        
        if self.SWEET_SPOT_MIN <= clv <= self.SWEET_SPOT_MAX:
            signal = CLVSignal.SWEET_SPOT
        elif clv > self.DANGER_THRESHOLD:
            signal = CLVSignal.DANGER
        elif clv > 0:
            signal = CLVSignal.GOOD
        else:
            signal = CLVSignal.NO_SIGNAL
        
        return CLVResult(
            our_odds=our_odds,
            closing_odds=closing_odds,
            clv_percentage=clv * 100,
            signal=signal
        )


class SmartConflictResolver:
    """Résolution des conflits Z vs Momentum"""
    
    def resolve(self, z_score: float, momentum: MomentumTrend) -> SmartConflictResult:
        """Applique les règles V3.4.2"""
        
        z_is_positive = z_score > 0.5
        z_is_strong = abs(z_score) > 2.5
        momentum_is_hot = momentum in [MomentumTrend.BLAZING, MomentumTrend.HOT]
        momentum_is_cold = momentum in [MomentumTrend.COOLING, MomentumTrend.FREEZING]
        
        if z_is_positive and momentum_is_hot:
            return SmartConflictResult(
                z_score=z_score,
                momentum_trend=momentum,
                resolution=ConflictResolution.ALIGNED,
                stake_modifier=1.15,
                reasoning="Z et Momentum alignés"
            )
        
        if z_is_positive and momentum_is_cold:
            return SmartConflictResult(
                z_score=z_score,
                momentum_trend=momentum,
                resolution=ConflictResolution.REDUCED_Z,
                stake_modifier=0.5,
                reasoning="Z favori mais momentum COLD"
            )
        
        if momentum_is_hot and not z_is_strong:
            return SmartConflictResult(
                z_score=z_score,
                momentum_trend=momentum,
                resolution=ConflictResolution.FOLLOW_MOMENTUM,
                stake_modifier=1.15 if momentum == MomentumTrend.BLAZING else 1.10,
                reasoning=f"Follow momentum {momentum.value}"
            )
        
        if z_is_strong and not momentum_is_cold:
            return SmartConflictResult(
                z_score=z_score,
                momentum_trend=momentum,
                resolution=ConflictResolution.FOLLOW_Z,
                stake_modifier=1.0,
                reasoning="Z fort override"
            )
        
        return SmartConflictResult(
            z_score=z_score,
            momentum_trend=momentum,
            resolution=ConflictResolution.REDUCED_Z,
            stake_modifier=0.85,
            reasoning="Conflit modéré"
        )


# ═══════════════════════════════════════════════════════════════════════════════════════
# RISK MANAGEMENT - BAYESIAN KELLY
# ═══════════════════════════════════════════════════════════════════════════════════════

class BayesianKellyCalculator:
    """
    Calcul du stake via Bayesian Kelly
    Inclut les modifiers DNA
    """
    
    FRACTIONAL_KELLY = 0.25  # 25% Kelly
    MAX_STAKE = 5.0
    MIN_STAKE = 0.5
    
    def calculate(
        self,
        probability: float,
        odds: float,
        confidence: float,
        dna_modifiers: Dict[str, float],
        mc_result: Optional[MonteCarloResult] = None,
        clv_result: Optional[CLVResult] = None,
        conflict_result: Optional[SmartConflictResult] = None
    ) -> float:
        """
        Calcule le stake optimal
        """
        
        # Kelly de base
        implied_prob = 1 / odds
        edge = probability - implied_prob
        
        if edge <= 0:
            return 0
        
        kelly = (edge * probability) / (implied_prob) if implied_prob > 0 else 0
        
        # Appliquer Fractional Kelly
        stake = kelly * self.FRACTIONAL_KELLY
        
        # Appliquer les modifiers
        total_modifier = 1.0
        
        # DNA modifiers
        for name, value in dna_modifiers.items():
            total_modifier *= value
        
        # MC modifier
        if mc_result and mc_result.robustness == Robustness.ROCK_SOLID:
            total_modifier *= 1.10
        elif mc_result and mc_result.robustness == Robustness.ROBUST:
            total_modifier *= 1.0
        elif mc_result:
            total_modifier *= 0.70
        
        # CLV modifier
        if clv_result:
            total_modifier *= clv_result.modifier
        
        # Conflict modifier
        if conflict_result:
            total_modifier *= conflict_result.stake_modifier
        
        # Confidence modifier
        confidence_modifier = 0.5 + (confidence / 200)  # [0.5, 1.0]
        total_modifier *= confidence_modifier
        
        # Appliquer
        stake *= total_modifier
        
        # Clamp
        stake = max(self.MIN_STAKE, min(self.MAX_STAKE, stake))
        
        # Arrondir à 0.5
        stake = round(stake * 2) / 2
        
        return stake


# ═══════════════════════════════════════════════════════════════════════════════════════
# SNAPSHOT RECORDER
# ═══════════════════════════════════════════════════════════════════════════════════════

class SnapshotRecorder:
    """Enregistre les snapshots pour audit/debug"""
    
    def __init__(self, db_pool=None):
        self.db_pool = db_pool
    
    def create_snapshot(
        self,
        match_id: str,
        home_dna: TeamDNA,
        away_dna: TeamDNA,
        friction: FrictionMatrix,
        votes: List[ModelVote],
        weights: Dict[str, float],
        consensus_score: float,
        consensus_count: int,
        conviction: Conviction,
        mc_result: MonteCarloResult,
        clv_result: Optional[CLVResult],
        conflict_result: Optional[SmartConflictResult],
        odds: Dict[str, float],
        final_market: str,
        final_odds: float,
        final_stake: float,
        final_probability: float,
        final_edge: float
    ) -> BetSnapshot:
        """Crée un snapshot complet"""
        
        return BetSnapshot(
            snapshot_id=str(uuid.uuid4()),
            match_id=match_id,
            timestamp=datetime.now(),
            home_dna=home_dna.to_dict(),
            away_dna=away_dna.to_dict(),
            friction_matrix=asdict(friction),
            model_votes={v.model_name.value: asdict(v) for v in votes},
            model_weights=weights,
            consensus_score=consensus_score,
            consensus_count=consensus_count,
            conviction=conviction.value,
            monte_carlo=asdict(mc_result),
            clv_validation=asdict(clv_result) if clv_result else {},
            smart_conflict=asdict(conflict_result) if conflict_result else {},
            odds_snapshot=odds,
            final_market=final_market,
            final_odds=final_odds,
            final_stake=final_stake,
            final_probability=final_probability,
            final_edge=final_edge,
            expected_value=final_stake * final_edge
        )
    
    async def save(self, snapshot: BetSnapshot) -> None:
        """Sauvegarde le snapshot en DB"""
        if not self.db_pool:
            logger.warning("No DB pool, snapshot not saved")
            return
        
        # En production: INSERT INTO quantum.bet_snapshots
        pass


# ═══════════════════════════════════════════════════════════════════════════════════════
# MODEL PERFORMANCE TRACKER
# ═══════════════════════════════════════════════════════════════════════════════════════



# ═══════════════════════════════════════════════════════════════════════════════════════
# MODEL G: MICROSTRATEGY SCORER - 12ème Vecteur DNA (126 marchés × HOME/AWAY)
# ═══════════════════════════════════════════════════════════════════════════════════════

class MicroStrategyModel(BaseModel):
    """
    Model G: MicroStrategy Scorer
    
    Utilise le 12ème vecteur DNA (MicroStrategyDNA) pour générer des signaux
    basés sur les 126 marchés × HOME/AWAY analysés par équipe.
    
    Ce modèle est SPÉCIFIQUE AU MARCHÉ - contrairement aux autres modèles
    qui donnent des signaux généraux, celui-ci répond à la question:
    "Pour CE marché spécifique, quelle est l'edge de CETTE équipe?"
    
    ROI Attendu: +15-25% (basé sur backtests internes)
    """
    
    def __init__(self, db_pool=None):
        self.db_pool = db_pool
        self.loader = get_microstrategy_loader() if MICROSTRATEGY_AVAILABLE else None
    
    @property
    def name(self) -> ModelName:
        return ModelName.MICROSTRATEGY
    
    async def generate_signal(
        self,
        home_team: str,
        away_team: str,
        market: str,
        home_dna: 'TeamDNA',
        away_dna: 'TeamDNA',
        odds: Optional[Dict] = None
    ) -> ModelVote:
        """
        Génère le signal MicroStrategy pour un marché spécifique.
        
        Combine:
        - Signal HOME de l'équipe domicile pour ce marché
        - Signal AWAY de l'équipe extérieure pour ce marché
        - Pondération 60% HOME / 40% AWAY (avantage domicile)
        """
        if not MICROSTRATEGY_AVAILABLE or not self.loader:
            return ModelVote(
                model_name=ModelName.MICROSTRATEGY,
                signal=Signal.SKIP,
                confidence=0,
                market=market,
                reasoning="MicroStrategy Loader non disponible"
            )
        
        # Récupérer les profils MicroStrategy
        home_micro = self.loader.get_team(home_team)
        away_micro = self.loader.get_team(away_team)
        
        if not home_micro and not away_micro:
            return ModelVote(
                model_name=ModelName.MICROSTRATEGY,
                signal=Signal.SKIP,
                confidence=0,
                market=market,
                reasoning=f"Aucun profil MicroStrategy pour {home_team} ou {away_team}"
            )
        
        # Obtenir les signaux pour ce marché
        home_edge = 0.0
        away_edge = 0.0
        reasoning_parts = []
        
        if home_micro:
            home_signal = home_micro.get_market_signal(market, "HOME")
            if home_signal:
                home_edge = home_signal.edge
                reasoning_parts.append(f"HOME {home_team}: {home_edge:+.1f}%")
        
        if away_micro:
            away_signal = away_micro.get_market_signal(market, "AWAY")
            if away_signal:
                away_edge = away_signal.edge
                reasoning_parts.append(f"AWAY {away_team}: {away_edge:+.1f}%")
        
        # Combinaison pondérée (60% HOME, 40% AWAY)
        combined_edge = (home_edge * 0.6) + (away_edge * 0.4)
        
        # Déterminer le signal
        if combined_edge >= 20:
            signal = Signal.STRONG_BUY
            confidence = min(95, 70 + abs(combined_edge))
        elif combined_edge >= 10:
            signal = Signal.BUY
            confidence = min(85, 60 + abs(combined_edge))
        elif combined_edge <= -20:
            signal = Signal.STRONG_SELL
            confidence = min(95, 70 + abs(combined_edge))
        elif combined_edge <= -10:
            signal = Signal.SELL
            confidence = min(85, 60 + abs(combined_edge))
        else:
            signal = Signal.HOLD
            confidence = 40
        
        # Construire le reasoning
        reasoning = f"MicroStrategy {market}: edge={combined_edge:+.1f}% | " + " | ".join(reasoning_parts)
        
        return ModelVote(
            model_name=ModelName.MICROSTRATEGY,
            signal=signal,
            confidence=confidence,
            market=market,
            probability=None,
            reasoning=reasoning,
            raw_data={
                "home_edge": home_edge,
                "away_edge": away_edge,
                "combined_edge": combined_edge,
                "home_team": home_team,
                "away_team": away_team,
                "market": market
            }
        )

class ModelPerformanceTracker:
    """Tracking des performances par modèle"""
    
    def __init__(self, db_pool=None):
        self.db_pool = db_pool
        self.performances: Dict[ModelName, ModelPerformance] = {
            name: ModelPerformance(model_name=name) for name in ModelName
        }
    
    async def record_result(
        self,
        snapshot_id: str,
        actual_result: str,
        profit_loss: float
    ) -> None:
        """Enregistre le résultat d'un pari"""
        # En production: UPDATE les votes avec was_correct
        pass
    
    def get_performance(self, model_name: ModelName) -> ModelPerformance:
        return self.performances.get(model_name, ModelPerformance(model_name=model_name))
    
    def get_all_rankings(self) -> List[ModelPerformance]:
        """Classement de tous les modèles par ROI"""
        return sorted(
            self.performances.values(),
            key=lambda x: x.roi,
            reverse=True
        )
    
    def get_recommendations(self) -> Dict[str, str]:
        """Recommandations d'amélioration"""
        recommendations = {}
        for perf in self.get_all_rankings():
            if perf.total_votes < 10:
                recommendations[perf.model_name.value] = "NEED_MORE_DATA"
            elif perf.roi < -5:
                recommendations[perf.model_name.value] = "REMOVE_OR_REBUILD"
            elif perf.roi < 0:
                recommendations[perf.model_name.value] = "REVIEW_PARAMETERS"
            elif perf.roi > 10:
                recommendations[perf.model_name.value] = "INCREASE_WEIGHT"
            else:
                recommendations[perf.model_name.value] = "KEEP"
        return recommendations


# ═══════════════════════════════════════════════════════════════════════════════════════
# MULTI-MARKET OPTIMIZER
# ═══════════════════════════════════════════════════════════════════════════════════════

class MultiMarketOptimizer:
    """Sélectionne le meilleur marché"""
    
    MARKETS = [
        "home_win", "draw", "away_win",
        "over_15", "over_25", "over_35",
        "under_15", "under_25", "under_35",
        "btts_yes", "btts_no",
        "home_over_05", "home_over_15",
        "away_over_05", "away_over_15"
    ]
    
    def optimize(
        self,
        votes: List[ModelVote],
        probabilities: Dict[str, float],
        odds: Dict[str, float],
        team_strategy_market: Optional[str] = None
    ) -> Tuple[str, float, float]:
        """
        Trouve le meilleur marché
        
        Returns:
            (market, probability, edge)
        """
        
        best_market = None
        best_edge = -float('inf')
        best_prob = 0
        
        # Collecter les marchés suggérés par les modèles
        suggested_markets = []
        for vote in votes:
            if vote.market and vote.is_positive:
                suggested_markets.append(vote.market)
        
        # Priorité au marché de team_strategy
        if team_strategy_market:
            suggested_markets.insert(0, team_strategy_market)
        
        # Évaluer chaque marché
        for market in self.MARKETS:
            if market not in odds or market not in probabilities:
                continue
            
            market_odds = odds[market]
            market_prob = probabilities.get(market, 0)
            
            if market_odds <= 1 or market_prob <= 0:
                continue
            
            implied_prob = 1 / market_odds
            edge = market_prob - implied_prob
            
            # Bonus si suggéré par les modèles
            if market in suggested_markets:
                edge *= 1.1
            
            if edge > best_edge:
                best_edge = edge
                best_market = market
                best_prob = market_prob
        
        return best_market or "over_25", best_prob, best_edge


# ═══════════════════════════════════════════════════════════════════════════════════════
# QUANTUM ORCHESTRATOR V1.0 - MAIN CLASS
# ═══════════════════════════════════════════════════════════════════════════════════════

class QuantumOrchestrator:
    """
    Orchestrateur Quantum V1.0 - Hedge Fund Grade
    
    Pipeline:
    1. Load DNA (11 vecteurs)
    2. Calculate Friction Matrix
    3. Generate Signals (6 modèles)
    4. Weighted Consensus
    5. Validation (MC + CLV + Smart Conflict)
    6. Risk Management (Bayesian Kelly)
    7. Multi-Market Optimization
    8. Snapshot Recording
    9. Output Quantum Pick
    """
    
    def __init__(self, db_pool=None):
        self.db_pool = db_pool
        
        # Models
        self.models: List[BaseModel] = [
            ModelTeamStrategy(db_pool),
            ModelQuantumScorer(db_pool),
            ModelMatchupScorer(db_pool),
            ModelDixonColes(db_pool),
            ModelScenarios(db_pool),
            ModelDNAFeatures(db_pool),
            MicroStrategyModel()  # Model G: 12ème vecteur DNA
        ]
        
        # Engines
        self.performance_tracker = ModelPerformanceTracker(db_pool)
        self.consensus_engine = WeightedConsensusEngine()
        
        # Validators
        self.mc_validator = MonteCarloValidator()
        self.clv_validator = CLVValidator()
        self.conflict_resolver = SmartConflictResolver()
        
        # Risk
        self.kelly_calculator = BayesianKellyCalculator()
        
        # Market
        self.market_optimizer = MultiMarketOptimizer()
        
        # Snapshot
        self.snapshot_recorder = SnapshotRecorder(db_pool)
        
        logger.info("Quantum Orchestrator V1.0 initialized - Hedge Fund Grade")
    
    async def load_team_dna(self, team_name: str) -> TeamDNA:
        """
        Charge les 12 vecteurs DNA d'une équipe via HybridDNALoader + DNAConverterV2

        Pipeline (V2 - simplifié):
        1. HybridDNALoader charge les données (DB + JSON fusionnés)
        2. DNAConverterV2 convertit Dict → TeamDNA V2 (retour direct!)
        3. Fallback sur template si échec

        NOTE: Plus de bridge! DNAConverterV2 retourne directement des TeamDNA V2
              qui utilisent les dataclasses importées de dataclasses_v2.py
        """
        # Essayer le vrai pipeline
        if HYBRID_DNA_AVAILABLE:
            try:
                # Charger via HybridDNALoader
                loader = HybridDNALoader()
                await loader.initialize()

                raw_data = await loader.load_team_dna(team_name)

                if raw_data and raw_data.get('merged'):
                    merged = raw_data['merged']

                    # Convertir avec DNAConverterV2 → retourne directement TeamDNA V2
                    converter = DNAConverterV2()
                    team_dna = converter.convert(merged, team_name)

                    logger.info(f"✅ Loaded REAL DNA V2 for {team_name} via HybridDNALoader (168+ metrics)")
                    return team_dna

            except Exception as e:
                logger.warning(f"⚠️ HybridDNALoader failed for {team_name}: {e}")
                logger.warning("Falling back to template data")

        # Fallback: Template data
        logger.info(f"📋 Using TEMPLATE DNA for {team_name} (no real data)")
        return self._get_template_dna(team_name)
    
    # NOTE: _bridge_dna_v2_to_local a été supprimé - Plus nécessaire depuis
    #       qu'on utilise directement les dataclasses V2 de dataclasses_v2.py
    #       ARCHIVE: quantum/orchestrator/archive/dataclasses_local_legacy.py

    def _get_template_dna(self, team_name: str) -> TeamDNA:
        """
        Template DNA de fallback - Utilise les dataclasses V2

        Retourne un TeamDNA V2 avec des valeurs neutres/par défaut.
        Ces valeurs sont utilisées quand HybridDNALoader ne trouve pas de données.
        """
        return TeamDNA(
            team_name=team_name,
            team_id=None,
            league=None,
            season=None,
            tier_rank=50,  # Milieu de classement
            style_confidence=50,
            unlucky_pct=0.0,

            # Vecteur 1: MarketDNA V2
            market=MarketDNA(
                avg_clv=0.0, avg_edge=0.0, sample_size=0,
                over_specialist=False, under_specialist=False,
                btts_no_specialist=False, btts_yes_specialist=False,
                profitable_strategies=0, total_strategies_tested=0,
                total_bets=0, total_wins=0, win_rate=50.0,
                total_pnl=0.0, roi=0.0, unlucky_losses=0,
                exploit_markets=[], avoid_markets=[]
            ),

            # Vecteur 2: ContextDNA V2
            context=ContextDNA(
                home_strength=50.0, away_strength=50.0, style_score=50,
                btts_tendency=50, draw_tendency=50, goals_tendency=50,
                xg_diff=0.0, xg_for_avg=1.2, xg_against_avg=1.2, clinical=False,
                clean_sheets_home=0, clean_sheets_away=0,
                matches_home=0, matches_away=0,
                ga_per_90_home=1.2, ga_per_90_away=1.2,
                wins=0, draws=0, losses=0, points=0,
                goals_for=0, goals_against=0
            ),

            # Vecteur 3: RiskDNA V2
            risk=RiskDNA(
                total_luck=0.0, defensive_luck=0.0, finishing_luck=0.0,
                ppg_vs_expected=0.0, panic_factor=0.1, lead_protection=0.5,
                unlucky_pct=0.0, tier_rank=50,
                avg_edge=0.0, profitable_strategies=0, total_strategies_tested=0,
                luck_index=0.0, xg_overperformance=0.0, xga_overperformance=0.0
            ),

            # Vecteur 4: TemporalDNA V2
            temporal=TemporalDNA(
                diesel_factor=0.5, fast_starter=0.5,
                diesel_factor_v8=0.5, fast_starter_v8=0.5,
                xg_momentum=0.0, late_game_threat=0.5,
                first_half_xg_pct=50.0, second_half_xg_pct=50.0,
                periods={},
                xg_1h_avg=0.6, xg_2h_avg=0.6, away_diesel=0.5,
                xga_early_pct=50.0, xga_late_pct=50.0,
                resist_early=0.5, resist_late=0.5
            ),

            # Vecteur 5: NemesisDNA V2
            nemesis=NemesisDNA(
                verticality=50.0, patience=50.0,
                fast_shots=0, slow_shots=0,
                territorial_dominance=50.0, keeper_overperformance=0.0,
                friction_multipliers={}, matchup_guide={},
                weaknesses=[], strengths=[],
                percentile_global=50, percentile_aerial=50,
                percentile_early=50, percentile_late=50,
                percentile_home=50, percentile_away=50
            ),

            # Vecteur 6: PsycheDNA V2
            psyche=PsycheDNA(
                panic_factor=0.1, killer_instinct=0.5, lead_protection=0.5,
                comeback_mentality=0.5, drawing_performance=0.0,
                ht_dominance=0.0, collapse_rate=0.1, comeback_rate=0.1,
                surrender_rate=0.1, lead_protection_v8=0.5,
                ga_leading_1=0, ga_leading_2plus=0, ga_level=0,
                ga_losing_1=0, ga_losing_2plus=0
            ),

            # Vecteur 7: SentimentDNA V2
            sentiment=SentimentDNA(
                avg_clv=0.0, avg_edge=0.0, sample_size=0,
                over_specialist=False, under_specialist=False,
                btts_no_specialist=False, btts_yes_specialist=False,
                tier_rank=50, unlucky_pct=0.0, style_confidence=50,
                goals_tendency=50, btts_tendency=50, draw_tendency=50,
                vulnerability_score=0.0
            ),

            # Vecteur 8: RosterDNA V2
            roster=RosterDNA(
                mvp_name="Unknown", mvp_xg_chain=0.0, mvp_dependency_score=0.3,
                playmaker_name="Unknown", playmaker_xg_buildup=0.0,
                total_team_xg=0.0, top3_dependency=0.3,
                clinical_finishers=0, squad_size_analyzed=0,
                goalkeeper_name="Unknown", goalkeeper_save_rate=70.0,
                keeper_overperformance=0.0
            ),

            # Vecteur 9: PhysicalDNA V2
            physical=PhysicalDNA(
                pressing_intensity=50.0, late_game_xg_avg=0.3,
                late_game_dominance=0.5, estimated_rotation_index=0.5,
                aerial_win_pct=50.0, possession_pct=50.0,
                tackles_total=0, tackles_att_3rd=0,
                tackles_mid_3rd=0, tackles_def_3rd=0,
                progressive_passes=0.0,
                resist_late=0.5, xga_late_pct=50.0,
                xga_1h_pct=50.0, xga_2h_pct=50.0
            ),

            # Vecteur 10: LuckDNA V2
            luck=LuckDNA(
                total_luck=0.0, xpoints_delta=0.0,
                defensive_luck=0.0, finishing_luck=0.0, ppg_vs_expected=0.0,
                unlucky_pct=0.0, luck_index=0.0,
                xg_overperformance=0.0, xga_overperformance=0.0,
                actual_points=0, expected_points=0.0,
                regression_direction="STABLE", regression_magnitude=0.0
            ),

            # Vecteur 11: ChameleonDNA V2
            chameleon=ChameleonDNA(
                adaptability_index=50.0, comeback_ability=0.0,
                tempo_flexibility=50.0, formation_volatility=0.3,
                lead_protection_score=0.5,
                formation_stability=0.7, box_shot_ratio=0.5,
                open_play_reliance=0.6, set_piece_threat=0.3,
                long_range_threat=0.2, main_formation="4-3-3",
                shots_per_game=10.0, sot_per_game=4.0, shot_accuracy=40.0
            ),

            # Vecteur 12: MicroStrategyDNA V2 (a des defaults)
            microstrategy=MicroStrategyDNA()
        )
    
    async def load_friction(self, home_team: str, away_team: str) -> FrictionMatrix:
        """
        Charge la friction matrix
        En production: query quantum.matchup_friction
        """
        return FrictionMatrix(
            home_team=home_team,
            away_team=away_team,
            kinetic_home=55,
            kinetic_away=48,
            temporal_clash=52,
            psyche_dominance=58,
            physical_edge=54,
            chaos_potential=62,
            predicted_goals=2.8,
            btts_probability=0.58
        )
    
    async def analyze_match(
        self,
        home_team: str,
        away_team: str,
        match_id: str,
        odds: Dict[str, float],
        context: Optional[Dict] = None
    ) -> Optional[QuantumPick]:
        """
        Analyse complète d'un match
        
        Returns:
            QuantumPick si consensus atteint, None sinon
        """
        
        logger.info(f"Analyzing: {home_team} vs {away_team}")
        
        # LAYER 0: Data Aggregation
        home_dna = await self.load_team_dna(home_team)
        away_dna = await self.load_team_dna(away_team)
        friction = await self.load_friction(home_team, away_team)
        
        # LAYER 1: Signal Generation (6 modèles)
        votes: List[ModelVote] = []
        for model in self.models:
            try:
                vote = await model.generate_signal(
                    home_team, away_team,
                    home_dna, away_dna,
                    friction, odds, context
                )
                votes.append(vote)
                logger.debug(f"Model {model.name.value}: {vote.signal.value} ({vote.confidence:.0f}%)")
            except Exception as e:
                logger.error(f"Error in model {model.name.value}: {e}")
                votes.append(ModelVote(
                    model_name=model.name,
                    signal=Signal.HOLD,
                    confidence=0,
                    reasoning=f"Error: {e}"
                ))
        
        # LAYER 2: Weighted Consensus
        consensus_reached, consensus_score, conviction, vote_details = \
            self.consensus_engine.evaluate(votes)
        
        if not consensus_reached:
            logger.info(f"No consensus: {consensus_score:.1%} < 60%")
            return None
        
        logger.info(f"Consensus reached: {consensus_score:.1%}, Conviction: {conviction.value}")
        
        # Récupérer les données des votes
        team_strategy_vote = next((v for v in votes if v.model_name == ModelName.TEAM_STRATEGY), None)
        quantum_scorer_vote = next((v for v in votes if v.model_name == ModelName.QUANTUM_SCORER), None)
        matchup_vote = next((v for v in votes if v.model_name == ModelName.MATCHUP_SCORER), None)
        dixon_vote = next((v for v in votes if v.model_name == ModelName.DIXON_COLES), None)
        
        # LAYER 3: Validation
        # Monte Carlo
        avg_confidence = np.mean([v.confidence for v in votes])
        avg_probability = dixon_vote.probability if dixon_vote and dixon_vote.probability else 0.55
        
        # Calculer l'edge estimé
        team_strategy_market = team_strategy_vote.market if team_strategy_vote else "over_25"
        market_odds = odds.get(team_strategy_market, 1.9)
        estimated_edge = avg_probability - (1 / market_odds) if market_odds > 1 else 0
        
        mc_result = await self.mc_validator.validate(
            probability=avg_probability,
            edge=estimated_edge,
            confidence=avg_confidence
        )
        
        if not mc_result.is_valid:
            logger.info(f"Monte Carlo rejected: {mc_result.robustness.value}")
            return None
        
        # CLV (si closing_odds disponible)
        closing_odds = odds.get(f"{team_strategy_market}_close", market_odds)
        clv_result = self.clv_validator.validate(market_odds, closing_odds)
        
        # Smart Conflict
        z_score = quantum_scorer_vote.raw_data.get("z_edge", 0) if quantum_scorer_vote else 0
        momentum_trend_str = matchup_vote.raw_data.get("best_trend", "NEUTRAL") if matchup_vote else "NEUTRAL"
        try:
            momentum_trend = MomentumTrend[momentum_trend_str]
        except KeyError:
            momentum_trend = MomentumTrend.NEUTRAL
        
        conflict_result = self.conflict_resolver.resolve(z_score, momentum_trend)
        
        # LAYER 4: Multi-Market Optimization
        probabilities = dixon_vote.raw_data if dixon_vote else {}
        best_market, best_prob, best_edge = self.market_optimizer.optimize(
            votes, probabilities, odds, team_strategy_market
        )
        
        final_odds = odds.get(best_market, 1.9)
        
        # LAYER 5: Risk Management (Bayesian Kelly)
        # Note: RiskDNA V2 n'a plus stake_modifier, on le calcule depuis panic_factor
        # panic_factor faible = équipe stable = modifier proche de 1.0
        # panic_factor élevé = équipe instable = modifier réduit
        risk_modifier = 1.0
        if home_dna.risk:
            panic = getattr(home_dna.risk, 'panic_factor', 0.1)
            risk_modifier = max(0.6, 1.0 - panic * 0.4)  # Range: [0.6, 1.0]
        dna_modifiers = {
            "risk": risk_modifier,
            "momentum": conflict_result.stake_modifier
        }
        
        final_stake = self.kelly_calculator.calculate(
            probability=best_prob,
            odds=final_odds,
            confidence=avg_confidence,
            dna_modifiers=dna_modifiers,
            mc_result=mc_result,
            clv_result=clv_result,
            conflict_result=conflict_result
        )
        
        final_edge = best_prob - (1 / final_odds) if final_odds > 1 else 0
        expected_value = final_stake * final_edge
        
        # LAYER 6: Snapshot Recording
        model_weights = {v.model_name.value: self.consensus_engine.get_weight(v.model_name) for v in votes}
        consensus_count = sum(1 for v in votes if v.is_positive)
        
        snapshot = self.snapshot_recorder.create_snapshot(
            match_id=match_id,
            home_dna=home_dna,
            away_dna=away_dna,
            friction=friction,
            votes=votes,
            weights=model_weights,
            consensus_score=consensus_score,
            consensus_count=consensus_count,
            conviction=conviction,
            mc_result=mc_result,
            clv_result=clv_result,
            conflict_result=conflict_result,
            odds=odds,
            final_market=best_market,
            final_odds=final_odds,
            final_stake=final_stake,
            final_probability=best_prob,
            final_edge=final_edge
        )
        
        await self.snapshot_recorder.save(snapshot)
        
        # LAYER 7: Output
        scenarios_vote = next((v for v in votes if v.model_name == ModelName.SCENARIOS), None)
        dna_vote = next((v for v in votes if v.model_name == ModelName.DNA_FEATURES), None)
        
        detected_scenarios = []
        if scenarios_vote and scenarios_vote.raw_data.get("scenarios"):
            detected_scenarios = [s[0] for s in scenarios_vote.raw_data["scenarios"]]
        
        dna_signals = {}
        if home_dna.temporal:
            dna_signals["temporal"] = f"diesel={home_dna.temporal.diesel_factor:.2f}"
        if home_dna.luck:
            total_luck = getattr(home_dna.luck, "total_luck", 0.0)
            luck_profile = "LUCKY" if total_luck > 2 else ("UNLUCKY" if total_luck < -2 else "NEUTRAL")
            regression_dir = getattr(home_dna.luck, "regression_direction", "STABLE")
            dna_signals["luck"] = f"{luck_profile} (regression {regression_dir})"
        
        pick = QuantumPick(
            pick_id=str(uuid.uuid4()),
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            date=datetime.now(),
            market=best_market,
            selection=best_market.replace("_", " ").title(),
            odds=final_odds,
            probability=best_prob,
            edge=final_edge * 100,
            stake=final_stake,
            expected_value=expected_value,
            confidence=avg_confidence,
            conviction=conviction,
            consensus=f"{consensus_count}/6 models agree",
            monte_carlo_score=mc_result.validation_score,
            monte_carlo_robustness=mc_result.robustness.value,
            clv_signal=clv_result.signal.value if clv_result else "N/A",
            smart_conflict_resolution=conflict_result.resolution.value,
            scenarios_detected=detected_scenarios,
            dna_signals=dna_signals,
            model_votes_summary={v.model_name.value: v.signal.value for v in votes},
            reasoning=[
                f"Consensus: {consensus_score:.1%} ({conviction.value})",
                f"Monte Carlo: {mc_result.robustness.value} ({mc_result.validation_score:.0f}/100)",
                f"CLV: {clv_result.signal.value}" if clv_result else "CLV: N/A",
                f"Conflict: {conflict_result.resolution.value}",
                f"Market: {best_market} @ {final_odds:.2f}",
                f"Edge: {final_edge*100:.1f}%",
                f"Stake: {final_stake:.1f}u | EV: {expected_value:.2f}u"
            ],
            snapshot_id=snapshot.snapshot_id
        )
        
        logger.info(f"Pick generated: {best_market} @ {final_odds:.2f}, Stake: {final_stake:.1f}u")
        
        return pick
    
    async def get_daily_picks(self, date: datetime = None) -> List[QuantumPick]:
        """
        Génère tous les picks pour une date
        En production: query les matchs du jour
        """
        # Template - en production, query la DB
        picks = []
        
        # Exemple de matchs
        test_matches = [
            ("Barcelona", "Athletic Club", "match_001"),
            ("Real Madrid", "Getafe", "match_002"),
            ("Liverpool", "Manchester City", "match_003")
        ]
        
        sample_odds = {
            "home_win": 1.45,
            "draw": 4.50,
            "away_win": 6.50,
            "over_25": 1.72,
            "under_25": 2.10,
            "btts_yes": 1.85,
            "btts_no": 1.95,
            "over_35": 2.40
        }
        
        for home, away, match_id in test_matches:
            pick = await self.analyze_match(home, away, match_id, sample_odds)
            if pick:
                picks.append(pick)
        
        return sorted(picks, key=lambda x: x.expected_value, reverse=True)


# ═══════════════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════════════

async def main():
    """Test de l'orchestrateur"""
    
    logging.basicConfig(level=logging.INFO)
    
    orchestrator = QuantumOrchestrator()
    
    # Test sur un match
    odds = {
        "home_win": 1.45,
        "draw": 4.50,
        "away_win": 6.50,
        "over_25": 1.72,
        "under_25": 2.10,
        "btts_yes": 1.85,
        "btts_no": 1.95,
        "over_35": 2.40
    }
    
    context = {
        "momentum": {
            "Barcelona": {"score": 78, "trend": "HOT", "streak": 3},
            "Athletic Club": {"score": 52, "trend": "NEUTRAL", "streak": 0}
        }
    }
    
    pick = await orchestrator.analyze_match(
        home_team="Barcelona",
        away_team="Athletic Club",
        match_id="test_001",
        odds=odds,
        context=context
    )
    
    if pick:
        print("\n" + "="*80)
        print("QUANTUM PICK GENERATED")
        print("="*80)
        print(f"Match: {pick.home_team} vs {pick.away_team}")
        print(f"Market: {pick.market}")
        print(f"Odds: {pick.odds:.2f}")
        print(f"Probability: {pick.probability:.1%}")
        print(f"Edge: {pick.edge:.1f}%")
        print(f"Stake: {pick.stake:.1f}u")
        print(f"Expected Value: {pick.expected_value:.2f}u")
        print(f"Confidence: {pick.confidence:.0f}%")
        print(f"Conviction: {pick.conviction.value}")
        print(f"Consensus: {pick.consensus}")
        print(f"Monte Carlo: {pick.monte_carlo_robustness} ({pick.monte_carlo_score:.0f}/100)")
        print(f"Scenarios: {pick.scenarios_detected}")
        print("\nReasoning:")
        for r in pick.reasoning:
            print(f"  • {r}")
        print(f"\nSnapshot ID: {pick.snapshot_id}")
    else:
        print("No pick generated (no consensus)")


if __name__ == "__main__":
    asyncio.run(main())
