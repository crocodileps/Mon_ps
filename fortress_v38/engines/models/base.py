"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    FORTRESS V38 - PREDICTION MODELS BASE                      ║
║                    Enums, ModelVote, BaseModel ABC                            ║
║                    Version: 1.0 - Migré depuis quantum_orchestrator_v1.py     ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Source: quantum/orchestrator/quantum_orchestrator_v1.py (lignes 69-409)
Migration: 26 Décembre 2025
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Dict, Any, Optional

# TYPE_CHECKING pour éviter les imports circulaires
if TYPE_CHECKING:
    from fortress_v38.models import TeamDNA
    # FrictionMatrix = Version Hedge Fund Grade déjà migrée (PAS celle de quantum_orchestrator ligne 217)
    from fortress_v38.engines.friction_matrix_unified import FrictionMatrix


# ═══════════════════════════════════════════════════════════════════════════════
# ENUM 1: ModelName - Les 7 modèles de l'ensemble
# ═══════════════════════════════════════════════════════════════════════════════

class ModelName(Enum):
    """Les 7 modèles de l'ensemble"""
    TEAM_STRATEGY = "team_strategy"      # Model A: +1,434.6u validé
    QUANTUM_SCORER = "quantum_scorer"    # Model B: V2.4, r=+0.53
    MATCHUP_SCORER = "matchup_scorer"    # Model C: V3.4.2, Momentum L5
    DIXON_COLES = "dixon_coles"          # Model D: Probabilités BTTS/Over
    SCENARIOS = "scenarios"              # Model E: 20 scénarios + MC filter
    DNA_FEATURES = "dna_features"        # Model F: 11 vecteurs
    MICROSTRATEGY = "microstrategy"      # Model G: 126 marchés × HOME/AWAY


# ═══════════════════════════════════════════════════════════════════════════════
# ENUM 2: Signal - Signaux possibles des modèles
# ═══════════════════════════════════════════════════════════════════════════════

class Signal(Enum):
    """Signaux possibles des modèles"""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"
    SKIP = "SKIP"


# ═══════════════════════════════════════════════════════════════════════════════
# ENUM 3: Conviction - Niveau de conviction basé sur le consensus
# ═══════════════════════════════════════════════════════════════════════════════

class Conviction(Enum):
    """Niveau de conviction basé sur le consensus"""
    MAXIMUM = "MAXIMUM"      # 7/7 modèles
    STRONG = "STRONG"        # 6/7 modèles
    MODERATE = "MODERATE"    # 5/7 modèles
    WEAK = "WEAK"            # <5/7 modèles (SKIP)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUM 4: MomentumTrend - Trends Momentum L5
# ═══════════════════════════════════════════════════════════════════════════════

class MomentumTrend(Enum):
    """Trends Momentum L5"""
    BLAZING = "BLAZING"      # Win streak ×4+
    HOT = "HOT"              # Strong positive
    WARMING = "WARMING"      # Positive
    NEUTRAL = "NEUTRAL"      # Stable
    COOLING = "COOLING"      # Negative
    FREEZING = "FREEZING"    # Strong negative


# ═══════════════════════════════════════════════════════════════════════════════
# ENUM 5: ConflictResolution - Résolution des conflits Z vs Momentum
# ═══════════════════════════════════════════════════════════════════════════════

class ConflictResolution(Enum):
    """Résolution des conflits Z vs Momentum"""
    FOLLOW_Z = "FOLLOW_Z"           # Z fort (>2.5)
    FOLLOW_MOMENTUM = "FOLLOW_MOM"  # BLAZING/HOT
    ALIGNED = "ALIGNED"             # Boost ×1.15
    REDUCED_Z = "REDUCED_Z"         # Conflit, réduction


# ═══════════════════════════════════════════════════════════════════════════════
# ENUM 6: Robustness - Niveaux de robustesse Monte Carlo
# ═══════════════════════════════════════════════════════════════════════════════

class Robustness(Enum):
    """Niveaux de robustesse Monte Carlo"""
    ROCK_SOLID = "ROCK_SOLID"    # ≥80% success rate
    ROBUST = "ROBUST"            # ≥65% success rate
    UNRELIABLE = "UNRELIABLE"    # <65% success rate
    FRAGILE = "FRAGILE"          # <50% success rate


# ═══════════════════════════════════════════════════════════════════════════════
# ENUM 7: CLVSignal - Signaux CLV
# ═══════════════════════════════════════════════════════════════════════════════

class CLVSignal(Enum):
    """Signaux CLV"""
    SWEET_SPOT = "SWEET_SPOT"  # 5-10% = +5.21u
    GOOD = "GOOD"              # 2-5%
    DANGER = "DANGER"          # >10%
    NO_SIGNAL = "NO_SIGNAL"


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASS: ModelVote - Vote d'un modèle pour un pari
# ═══════════════════════════════════════════════════════════════════════════════

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
        """True si le signal est positif (BUY ou STRONG_BUY)"""
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


# ═══════════════════════════════════════════════════════════════════════════════
# ABC: BaseModel - Interface pour tous les modèles
# ═══════════════════════════════════════════════════════════════════════════════

class BaseModel(ABC):
    """
    Interface abstraite pour tous les modèles de prédiction.

    Chaque modèle doit implémenter:
    - name: Identifiant unique du modèle
    - generate_signal: Génération du signal de trading
    """

    @property
    @abstractmethod
    def name(self) -> ModelName:
        """Retourne le nom unique du modèle"""
        pass

    @abstractmethod
    async def generate_signal(
        self,
        home_team: str,
        away_team: str,
        home_dna: "TeamDNA",
        away_dna: "TeamDNA",
        friction: "FrictionMatrix",
        odds: Dict[str, float],
        context: Optional[Dict] = None
    ) -> ModelVote:
        """
        Génère un signal de trading pour un match.

        Args:
            home_team: Nom de l'équipe à domicile
            away_team: Nom de l'équipe à l'extérieur
            home_dna: ADN de l'équipe à domicile
            away_dna: ADN de l'équipe à l'extérieur
            friction: Matrice de friction entre les deux équipes
            odds: Cotes disponibles pour le match
            context: Contexte additionnel (optionnel)

        Returns:
            ModelVote avec le signal, la confiance et le raisonnement
        """
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

# Poids de base pour chaque modèle (utilisé par ConsensusEngine)
BASE_MODEL_WEIGHTS: Dict[ModelName, float] = {
    ModelName.TEAM_STRATEGY: 1.25,   # MAX - +1,434.6u validé
    ModelName.QUANTUM_SCORER: 1.15,  # r=+0.53
    ModelName.MATCHUP_SCORER: 1.10,  # +10% ROI
    ModelName.DIXON_COLES: 1.00,     # Baseline
    ModelName.SCENARIOS: 0.85,       # MIN - Nécessite MC
    ModelName.DNA_FEATURES: 1.05,    # Validé
    ModelName.MICROSTRATEGY: 1.05,   # +15-25% ROI (ajouté car manquant dans source)
}

# Version du module
BASE_VERSION = "1.0"
