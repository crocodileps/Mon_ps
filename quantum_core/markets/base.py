"""
QUANTUM CORE - BASE MARKET PREDICTOR
====================================
Classe abstraite pour tous les prédicteurs de marchés

FONCTIONNALITÉS:
✅ Confidence dynamique multi-facteurs
✅ Structure Prediction standardisée
✅ Interface commune pour tous les marchés
✅ Intégration DataManager + EdgeCalculator

Tous les prédicteurs spécifiques (goals, scorers, cards, etc.)
héritent de cette classe.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════

class Confidence(Enum):
    """Niveaux de confiance"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    ELITE = "ELITE"

    @classmethod
    def from_score(cls, score: float) -> "Confidence":
        """Convertit un score (0-100) en niveau de confiance"""
        if score >= 80:
            return cls.ELITE
        elif score >= 65:
            return cls.HIGH
        elif score >= 45:
            return cls.MEDIUM
        else:
            return cls.LOW


class Recommendation(Enum):
    """Types de recommandations"""
    STRONG_BET = "STRONG_BET"
    BET = "BET"
    LEAN = "LEAN"
    SKIP = "SKIP"
    AVOID = "AVOID"


# ═══════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class ConfidenceFactors:
    """Facteurs pour le calcul de confiance"""
    probability: float           # Notre probabilité (0-1)
    data_quality: float = 1.0    # Qualité des données (0-1)
    variance: float = 1.0        # Variance de l'équipe (plus haut = moins confiant)
    model_agreement: int = 1     # Nombre de modèles en accord (1-4)
    sample_size: int = 10        # Nombre de matchs dans l'historique
    is_derby: bool = False       # Derby = plus imprévisible
    key_player_missing: bool = False  # Absence majeure


@dataclass
class Prediction:
    """Résultat d'une prédiction de marché"""
    # Identifiants
    market: str
    market_category: str

    # Probabilités
    probability: float
    fair_odds: float

    # Bookmaker
    bookmaker_odds: Optional[float] = None
    edge_percentage: Optional[float] = None

    # Décision
    confidence: str = "MEDIUM"
    recommendation: str = "SKIP"
    kelly_stake: float = 0.0
    confidence_adjusted_stake: float = 0.0

    # Métadonnées
    sources: List[str] = field(default_factory=list)
    explanation: str = ""
    model_version: str = "1.0"

    # Debug
    factors: Optional[ConfidenceFactors] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return {
            "market": self.market,
            "category": self.market_category,
            "probability": round(self.probability, 4),
            "fair_odds": round(self.fair_odds, 2),
            "bookmaker_odds": self.bookmaker_odds,
            "edge": self.edge_percentage,
            "confidence": self.confidence,
            "recommendation": self.recommendation,
            "stake_kelly": self.kelly_stake,
            "stake_adjusted": self.confidence_adjusted_stake,
            "explanation": self.explanation,
            "sources": self.sources
        }


# ═══════════════════════════════════════════════════════════════════════
# BASE PREDICTOR CLASS
# ═══════════════════════════════════════════════════════════════════════

class MarketPredictor(ABC):
    """
    Classe de base abstraite pour tous les prédicteurs de marchés

    Chaque marché (over_25, btts, scorer, etc.) doit hériter de cette classe
    et implémenter les méthodes abstraites.

    Usage:
        class Over25Predictor(MarketPredictor):
            market_name = "over_25"
            market_category = "GOALS"

            def calculate_probability(self, context) -> float:
                # Logique spécifique
                return 0.65

            def get_required_data(self) -> List[str]:
                return ["team_dna", "narrative_dna"]
    """

    # À définir dans les classes enfants
    market_name: str = ""
    market_category: str = ""
    model_version: str = "1.0"

    # Constantes
    MIN_PROBABILITY = 0.001
    MAX_PROBABILITY = 0.999
    MAX_FAIR_ODDS = 1000.0

    def __init__(self, data_manager=None):
        """
        Args:
            data_manager: Instance de DataManager (injecté)
        """
        from ..data.manager import get_data_manager
        self.data = data_manager or get_data_manager()

    @abstractmethod
    def calculate_probability(self, home_team: str, away_team: str,
                               **kwargs) -> float:
        """
        Calcule la probabilité du marché

        Chaque classe enfant implémente sa propre logique.

        Args:
            home_team: Nom de l'équipe à domicile
            away_team: Nom de l'équipe à l'extérieur
            **kwargs: Arguments additionnels (referee, etc.)

        Returns:
            Probabilité entre 0 et 1
        """
        pass

    @abstractmethod
    def get_required_data(self) -> List[str]:
        """
        Liste des sources de données requises

        Returns:
            Liste des noms de sources (ex: ["team_dna", "scorer_intelligence"])
        """
        pass

    def predict(self, home_team: str, away_team: str,
                bookmaker_odds: float = None,
                market_margin: float = 5.0,
                **kwargs) -> Prediction:
        """
        Méthode principale de prédiction (NE PAS OVERRIDE)

        Flow:
        1. Calcule la probabilité
        2. Calcule la confiance
        3. Calcule l'edge si cote fournie
        4. Génère la recommandation
        5. Retourne Prediction complète

        Args:
            home_team: Équipe à domicile
            away_team: Équipe à l'extérieur
            bookmaker_odds: Cote du bookmaker (optionnel)
            market_margin: Marge estimée du marché (%)
            **kwargs: Arguments additionnels

        Returns:
            Prediction avec tous les détails
        """
        # 1. Calculer la probabilité
        prob = self.calculate_probability(home_team, away_team, **kwargs)
        prob = max(self.MIN_PROBABILITY, min(self.MAX_PROBABILITY, prob))

        # 2. Calculer fair odds (avec protection division par zéro)
        fair_odds = 1 / prob if prob > self.MIN_PROBABILITY else self.MAX_FAIR_ODDS
        fair_odds = min(fair_odds, self.MAX_FAIR_ODDS)

        # 3. Calculer la confiance
        factors = self._build_confidence_factors(home_team, away_team, prob, **kwargs)
        confidence = self._calculate_confidence(factors)

        # 4. Calculer l'edge si cote fournie
        edge = None
        kelly = 0.0
        adjusted_stake = 0.0
        recommendation = Recommendation.SKIP.value

        if bookmaker_odds and bookmaker_odds > 1:
            from ..edge.calculator import calculate_edge, adjust_stake_for_confidence

            edge_analysis = calculate_edge(prob, bookmaker_odds, market_margin)
            edge = edge_analysis.edge_percentage
            kelly = edge_analysis.kelly_stake

            # Ajuster le stake avec la confiance
            data_quality = factors.data_quality
            adjusted_stake = adjust_stake_for_confidence(
                kelly, confidence.value, data_quality
            )

            # Générer la recommandation
            recommendation = self._generate_recommendation(
                edge, confidence, adjusted_stake
            ).value

        # 5. Générer l'explication
        explanation = self._generate_explanation(
            home_team, away_team, prob, edge, confidence
        )

        return Prediction(
            market=self.market_name,
            market_category=self.market_category,
            probability=prob,
            fair_odds=fair_odds,
            bookmaker_odds=bookmaker_odds,
            edge_percentage=edge,
            confidence=confidence.value,
            recommendation=recommendation,
            kelly_stake=kelly,
            confidence_adjusted_stake=adjusted_stake,
            sources=self.get_required_data(),
            explanation=explanation,
            model_version=self.model_version,
            factors=factors
        )

    def _build_confidence_factors(self, home_team: str, away_team: str,
                                   prob: float, **kwargs) -> ConfidenceFactors:
        """Construit les facteurs de confiance"""
        # Qualité des données
        home_quality = self.data.get_data_quality(home_team)
        away_quality = self.data.get_data_quality(away_team)
        data_quality = (home_quality + away_quality) / 2

        # Variance
        home_var = self.data.get_team_variance(home_team)
        away_var = self.data.get_team_variance(away_team)
        variance = (home_var + away_var) / 2

        # Sample size
        home_team_data = self.data.get_team(home_team)
        away_team_data = self.data.get_team(away_team)

        sample_size = 10  # Default
        if home_team_data and away_team_data:
            sample_size = min(home_team_data.games_played, away_team_data.games_played)

        return ConfidenceFactors(
            probability=prob,
            data_quality=data_quality,
            variance=variance,
            model_agreement=kwargs.get('model_agreement', 1),
            sample_size=sample_size,
            is_derby=kwargs.get('is_derby', False),
            key_player_missing=kwargs.get('key_player_missing', False)
        )

    def _calculate_confidence(self, factors: ConfidenceFactors) -> Confidence:
        """
        Calcule le niveau de confiance multi-facteurs

        Score = f(Probabilité, DataQuality, Variance, Consensus, SampleSize)

        Args:
            factors: ConfidenceFactors

        Returns:
            Confidence level
        """
        score = 0.0

        # 1. Probabilité (35% du score)
        # Plus la proba est éloignée de 50%, plus on est confiant
        prob_distance = abs(factors.probability - 0.5)
        if prob_distance > 0.25:
            score += 35
        elif prob_distance > 0.15:
            score += 25
        elif prob_distance > 0.10:
            score += 15
        else:
            score += 5

        # 2. Qualité des données (25% du score)
        score += factors.data_quality * 25

        # 3. Variance inverse (20% du score)
        # Variance basse = équipe prévisible = confiance haute
        if factors.variance <= 1.0:
            score += 20
        elif factors.variance <= 1.5:
            score += 15
        elif factors.variance <= 2.0:
            score += 10
        else:
            score += 5

        # 4. Sample size (10% du score)
        if factors.sample_size >= 15:
            score += 10
        elif factors.sample_size >= 10:
            score += 7
        elif factors.sample_size >= 5:
            score += 4
        else:
            score += 2

        # 5. Model agreement (10% du score)
        score += min(factors.model_agreement * 2.5, 10)

        # Pénalités
        if factors.is_derby:
            score -= 10  # Derbies sont imprévisibles

        if factors.key_player_missing:
            score -= 5  # Incertitude sur l'impact

        return Confidence.from_score(score)

    def _generate_recommendation(self, edge: float, confidence: Confidence,
                                  stake: float) -> Recommendation:
        """Génère la recommandation de pari"""
        if edge is None:
            return Recommendation.SKIP

        if edge < 0:
            return Recommendation.AVOID

        if edge >= 10 and confidence in [Confidence.HIGH, Confidence.ELITE]:
            return Recommendation.STRONG_BET

        if edge >= 5 and confidence != Confidence.LOW:
            return Recommendation.BET

        if edge >= 3:
            return Recommendation.LEAN

        return Recommendation.SKIP

    def _generate_explanation(self, home: str, away: str, prob: float,
                               edge: float, confidence: Confidence) -> str:
        """Génère une explication textuelle"""
        edge_str = f", Edge: {edge:.1f}%" if edge else ""
        return (f"{self.market_name}: {home} vs {away} → "
                f"{prob*100:.1f}% (Confidence: {confidence.value}{edge_str})")
