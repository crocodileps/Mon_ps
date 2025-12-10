"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║  QUANTUM BASE MODELS - Socle Institutionnel                                          ║
║  Version: 2.0                                                                        ║
║  "Chaque métrique a une confiance. Chaque DNA a une version."                        ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

Architecture Mon_PS - Chess Engine V2.0
Créé le: 2025-12-10

Installation: /home/Mon_ps/quantum/models/base.py
"""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List, Dict, Any
import math


# ═══════════════════════════════════════════════════════════════════════════════════════
# QUANTUM BASE MODEL - Hérité par tous les DNA
# ═══════════════════════════════════════════════════════════════════════════════════════

class QuantumBaseModel(BaseModel):
    """
    Socle commun avec versioning et audit.
    Toutes les classes DNA héritent de celle-ci.
    
    Features:
    - Versioning automatique pour migrations futures
    - Timestamps de création/modification
    - Validation stricte des assignations
    - Robuste aux changements d'API (ignore extra fields)
    """
    
    model_config = ConfigDict(
        validate_assignment=True,   # Bloque modifications illégales après création
        extra="ignore",             # Robuste aux changements d'API (ignore champs inconnus)
        str_strip_whitespace=True,  # Nettoie les strings automatiquement
        use_enum_values=True,       # Sérialise les enums en valeurs
    )
    
    schema_version: str = "2.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def bump_updated(self) -> None:
        """Met à jour le timestamp de modification"""
        self.updated_at = datetime.utcnow()


# ═══════════════════════════════════════════════════════════════════════════════════════
# CONFIDENT METRIC - Métrique avec score de confiance
# ═══════════════════════════════════════════════════════════════════════════════════════

class ConfidentMetric(BaseModel):
    """
    Métrique avec score de confiance basé sur l'échantillon.
    
    ═══════════════════════════════════════════════════════════════════════════════════
    PRINCIPE QUANT:
    Un attack_index de 80 sur 3 matchs ≠ 80 sur 25 matchs.
    Le confidence_score pondère la fiabilité statistique.
    ═══════════════════════════════════════════════════════════════════════════════════
    
    Formule de confiance: confidence = 1 - e^(-sample_size / 15)
    
    Échelle de confiance:
    - 5 matchs  = 0.28 (faible)      → Données insuffisantes
    - 10 matchs = 0.49 (moyen)       → Tendance visible
    - 15 matchs = 0.63 (bon)         → Statistiquement significatif
    - 20 matchs = 0.74 (solide)      → Haute confiance
    - 30 matchs = 0.86 (excellent)   → Très haute confiance
    - 38 matchs = 0.92 (saison)      → Confiance maximale
    
    Usage:
    >>> metric = ConfidentMetric.create(value=2.15, sample_size=20)
    >>> print(metric)  # 2.15 (σ=74%, n=20)
    >>> print(metric.weighted_value)  # 1.59 (value * confidence)
    """
    
    model_config = ConfigDict(frozen=False)
    
    value: float
    sample_size: int = Field(ge=0)
    confidence: float = Field(ge=0, le=1)
    
    @classmethod
    def create(cls, value: float, sample_size: int) -> "ConfidentMetric":
        """
        Factory avec calcul automatique de la confiance.
        
        Args:
            value: La valeur de la métrique
            sample_size: Nombre d'observations (matchs, événements...)
            
        Returns:
            ConfidentMetric avec confiance calculée
        """
        confidence = 1 - math.exp(-sample_size / 15)
        return cls(
            value=round(value, 4),
            sample_size=sample_size,
            confidence=round(confidence, 3)
        )
    
    @classmethod
    def zero(cls) -> "ConfidentMetric":
        """Retourne une métrique nulle (pas de données)"""
        return cls(value=0.0, sample_size=0, confidence=0.0)
    
    @property
    def weighted_value(self) -> float:
        """
        Valeur pondérée par la confiance.
        Utile pour les agrégations où les métriques fiables pèsent plus.
        """
        return round(self.value * self.confidence, 4)
    
    @property
    def is_reliable(self) -> bool:
        """True si la confiance est suffisante (>= 50%)"""
        return self.confidence >= 0.5
    
    @property
    def reliability_tier(self) -> str:
        """Niveau de fiabilité en texte"""
        if self.confidence >= 0.8:
            return "EXCELLENT"
        elif self.confidence >= 0.6:
            return "GOOD"
        elif self.confidence >= 0.4:
            return "MODERATE"
        elif self.confidence >= 0.2:
            return "LOW"
        return "INSUFFICIENT"
    
    def __repr__(self) -> str:
        return f"{self.value:.2f} (σ={self.confidence:.0%}, n={self.sample_size})"
    
    def __str__(self) -> str:
        return self.__repr__()


# ═══════════════════════════════════════════════════════════════════════════════════════
# TIMING METRIC - Métrique avec breakdown par période
# ═══════════════════════════════════════════════════════════════════════════════════════

class TimingMetric(BaseModel):
    """
    Métrique avec breakdown par période de jeu (6 périodes de 15 minutes).
    
    ═══════════════════════════════════════════════════════════════════════════════════
    CRUCIAL pour les marchés timing:
    - Late Goals (75-90')
    - First Half Goals
    - Second Half Goals
    - Early Goal (0-15')
    ═══════════════════════════════════════════════════════════════════════════════════
    
    Usage:
    >>> timing = TimingMetric(total=2.5, period_0_15=0.3, period_76_90=0.8, ...)
    >>> print(timing.timing_signature)  # "DIESEL" (finit fort)
    >>> print(timing.late_game)  # 1.2 (61-90')
    """
    
    model_config = ConfigDict(frozen=False)
    
    total: float = Field(ge=0)
    period_0_15: float = Field(default=0, ge=0)
    period_16_30: float = Field(default=0, ge=0)
    period_31_45: float = Field(default=0, ge=0)   # Inclut temps additionnel 1H
    period_46_60: float = Field(default=0, ge=0)
    period_61_75: float = Field(default=0, ge=0)
    period_76_90: float = Field(default=0, ge=0)   # Inclut temps additionnel 2H
    
    @property
    def first_half(self) -> float:
        """Total 1ère mi-temps (0-45')"""
        return round(self.period_0_15 + self.period_16_30 + self.period_31_45, 3)
    
    @property
    def second_half(self) -> float:
        """Total 2ème mi-temps (46-90')"""
        return round(self.period_46_60 + self.period_61_75 + self.period_76_90, 3)
    
    @property
    def early_game(self) -> float:
        """Début de match (0-30')"""
        return round(self.period_0_15 + self.period_16_30, 3)
    
    @property
    def mid_game(self) -> float:
        """Milieu de match (31-60')"""
        return round(self.period_31_45 + self.period_46_60, 3)
    
    @property
    def late_game(self) -> float:
        """Fin de match (61-90')"""
        return round(self.period_61_75 + self.period_76_90, 3)
    
    @property
    def clutch_time(self) -> float:
        """Moments critiques (76-90' + arrêts de jeu)"""
        return round(self.period_76_90, 3)
    
    @property
    def first_half_ratio(self) -> float:
        """Ratio de la métrique en 1H (0-1)"""
        if self.total == 0:
            return 0.5
        return round(self.first_half / self.total, 3)
    
    @property
    def late_game_ratio(self) -> float:
        """Ratio de la métrique en fin de match (0-1)"""
        if self.total == 0:
            return 0.33  # Attendu si uniforme
        return round(self.late_game / self.total, 3)
    
    @property
    def timing_signature(self) -> str:
        """
        Empreinte timing - Profil temporel de l'équipe/coach.
        
        Returns:
            DIESEL: Finit fort (late_game > early_game * 1.5)
            EARLY_BIRD: Commence fort (early_game > late_game * 1.5)
            CLUTCH: Dangereux en fin de match (76-90 > 25% du total)
            FIRST_HALF_TEAM: Dominance en 1H (1H > 60% du total)
            SECOND_HALF_TEAM: Dominance en 2H (2H > 60% du total)
            BALANCED: Répartition équilibrée
        """
        if self.total == 0:
            return "NO_DATA"
        
        # Clutch time (très spécifique)
        if self.period_76_90 > self.total * 0.30:
            return "CLUTCH"
        
        # Diesel vs Early Bird
        if self.late_game > self.early_game * 1.5:
            return "DIESEL"
        elif self.early_game > self.late_game * 1.5:
            return "EARLY_BIRD"
        
        # Dominance par mi-temps
        if self.first_half > self.total * 0.60:
            return "FIRST_HALF_TEAM"
        elif self.second_half > self.total * 0.60:
            return "SECOND_HALF_TEAM"
        
        return "BALANCED"
    
    @property
    def period_distribution(self) -> Dict[str, float]:
        """Distribution en % par période"""
        if self.total == 0:
            return {f"period_{i}": 0.0 for i in range(6)}
        
        return {
            "0-15": round(self.period_0_15 / self.total * 100, 1),
            "16-30": round(self.period_16_30 / self.total * 100, 1),
            "31-45": round(self.period_31_45 / self.total * 100, 1),
            "46-60": round(self.period_46_60 / self.total * 100, 1),
            "61-75": round(self.period_61_75 / self.total * 100, 1),
            "76-90": round(self.period_76_90 / self.total * 100, 1),
        }
    
    def __repr__(self) -> str:
        return f"TimingMetric(total={self.total:.2f}, signature={self.timing_signature})"


# ═══════════════════════════════════════════════════════════════════════════════════════
# EDGE METRIC - Pour les edges de marché
# ═══════════════════════════════════════════════════════════════════════════════════════

class EdgeMetric(BaseModel):
    """
    Métrique d'edge sur un marché spécifique.
    
    Combine:
    - La valeur de l'edge (en %)
    - La confiance statistique
    - L'historique de performance
    """
    
    edge_pct: float = Field(description="Edge en % (positif = value, négatif = fade)")
    hit_rate: float = Field(ge=0, le=100, description="Taux de réussite historique")
    sample_size: int = Field(ge=0)
    roi: float = Field(description="ROI historique en %")
    
    @property
    def confidence(self) -> float:
        """Confiance basée sur l'échantillon"""
        return round(1 - math.exp(-self.sample_size / 15), 3)
    
    @property
    def edge_tier(self) -> str:
        """Classification de l'edge"""
        if self.edge_pct >= 10 and self.confidence >= 0.6:
            return "STRONG"
        elif self.edge_pct >= 5 and self.confidence >= 0.4:
            return "MODERATE"
        elif self.edge_pct >= 2:
            return "WEAK"
        elif self.edge_pct <= -5:
            return "FADE"
        return "NEUTRAL"
    
    @property
    def is_actionable(self) -> bool:
        """True si l'edge est exploitable"""
        return abs(self.edge_pct) >= 3 and self.confidence >= 0.4


# ═══════════════════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════════════

def calculate_confidence(sample_size: int, decay_factor: float = 15) -> float:
    """
    Calcule le score de confiance basé sur la taille de l'échantillon.
    
    Args:
        sample_size: Nombre d'observations
        decay_factor: Vitesse de convergence (défaut: 15 = ~63% à 15 obs)
        
    Returns:
        Confidence score entre 0 et 1
    """
    return round(1 - math.exp(-sample_size / decay_factor), 3)


def weighted_average(metrics: List[ConfidentMetric]) -> float:
    """
    Calcule la moyenne pondérée par la confiance.
    
    Args:
        metrics: Liste de ConfidentMetric
        
    Returns:
        Moyenne pondérée
    """
    if not metrics:
        return 0.0
    
    total_weight = sum(m.confidence for m in metrics)
    if total_weight == 0:
        return 0.0
    
    weighted_sum = sum(m.value * m.confidence for m in metrics)
    return round(weighted_sum / total_weight, 4)
