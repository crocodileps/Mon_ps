"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║  GOALKEEPER DNA - Profil Gardien Complet                                             ║
║  Version: 2.0                                                                        ║
║  "Le gardien est le dernier rempart, mais ses stats racontent toute l'histoire."     ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

Architecture Mon_PS - Chess Engine V2.0
Créé le: 2025-12-10

Installation: /home/Mon_ps/quantum/models/sub_models/goalkeeper_dna.py

Sources de données:
- /home/Mon_ps/data/goalkeeper_dna/goalkeeper_dna_v4_4_by_team.json
- /home/Mon_ps/data/goalkeeper_dna/goalkeeper_dna_v2.json
"""

from pydantic import BaseModel, Field, ConfigDict, computed_field
from typing import Optional, List
from datetime import datetime

from ..base import QuantumBaseModel, ConfidentMetric
from ..enums import DataQuality


# ═══════════════════════════════════════════════════════════════════════════════════════
# SHOT STOPPING
# ═══════════════════════════════════════════════════════════════════════════════════════

class ShotStoppingMetrics(BaseModel):
    """
    Métriques d'arrêt de tirs.
    """
    
    model_config = ConfigDict(frozen=False)
    
    # Saves
    saves_total: int = Field(default=0, ge=0)
    saves_per_match: float = Field(default=0, ge=0)
    save_percentage: float = Field(default=0, ge=0, le=100)
    
    # Shots faced
    shots_faced_total: int = Field(default=0, ge=0)
    shots_on_target_faced: int = Field(default=0, ge=0)
    shots_faced_per_match: float = Field(default=0, ge=0)
    
    # PSxG (Post-Shot Expected Goals)
    psxg_total: float = Field(
        default=0, ge=0,
        description="Post-Shot xG - Qualité des tirs subis après trajectoire"
    )
    psxg_per_match: float = Field(default=0, ge=0)
    
    # Performance vs PSxG
    goals_conceded: int = Field(default=0, ge=0)
    psxg_minus_goals: float = Field(
        default=0,
        description="PSxG - Goals. Positif = surperformance (bon GK)"
    )
    
    # Reflexes / Big saves
    big_saves: int = Field(default=0, ge=0)
    big_save_rate: float = Field(default=0, ge=0, le=100)
    
    @computed_field
    @property
    def shot_stopping_rating(self) -> float:
        """
        Rating d'arrêt de tirs (-5 à +5).
        Basé sur PSxG - Goals concédés.
        
        > +3: Elite shot-stopper
        > +1: Above average
        -1 to +1: Average
        < -1: Below average
        < -3: Liability
        """
        return round(self.psxg_minus_goals, 2)
    
    @computed_field
    @property
    def shot_stopping_tier(self) -> str:
        """Niveau d'arrêt de tirs."""
        rating = self.shot_stopping_rating
        if rating > 5:
            return "ELITE"
        elif rating > 2:
            return "EXCELLENT"
        elif rating > 0:
            return "ABOVE_AVERAGE"
        elif rating > -2:
            return "AVERAGE"
        elif rating > -5:
            return "BELOW_AVERAGE"
        else:
            return "LIABILITY"


# ═══════════════════════════════════════════════════════════════════════════════════════
# DISTRIBUTION
# ═══════════════════════════════════════════════════════════════════════════════════════

class DistributionMetrics(BaseModel):
    """
    Métriques de relance et distribution.
    """
    
    model_config = ConfigDict(frozen=False)
    
    # Pass stats
    passes_attempted: int = Field(default=0, ge=0)
    pass_completion: float = Field(default=0, ge=0, le=100)
    
    # Long passes
    long_passes_attempted: int = Field(default=0, ge=0)
    long_pass_completion: float = Field(default=0, ge=0, le=100)
    
    # Launch tendency
    launch_rate: float = Field(
        default=50, ge=0, le=100,
        description="% de dégagements longs vs passes courtes"
    )
    
    # Goal kicks
    goal_kick_long_rate: float = Field(default=50, ge=0, le=100)
    
    # Progressive passes
    progressive_passes_per_match: float = Field(default=0, ge=0)
    
    @computed_field
    @property
    def distribution_style(self) -> str:
        """Style de relance."""
        if self.launch_rate > 70:
            return "LONG_BALL"
        elif self.launch_rate > 50:
            return "MIXED"
        elif self.launch_rate > 30:
            return "SHORT_BUILDUP"
        else:
            return "SWEEPER_KEEPER"
    
    @computed_field
    @property
    def distribution_quality(self) -> str:
        """Qualité de la distribution."""
        if self.pass_completion > 85:
            return "EXCELLENT"
        elif self.pass_completion > 75:
            return "GOOD"
        elif self.pass_completion > 65:
            return "AVERAGE"
        else:
            return "POOR"


# ═══════════════════════════════════════════════════════════════════════════════════════
# SWEEPING & CLAIMING
# ═══════════════════════════════════════════════════════════════════════════════════════

class SweepingMetrics(BaseModel):
    """
    Métriques de jeu au pied et sorties.
    """
    
    model_config = ConfigDict(frozen=False)
    
    # Sweeping (jeu au pied hors surface)
    sweeping_actions_per_match: float = Field(default=0, ge=0)
    avg_sweeping_distance: float = Field(
        default=0, ge=0,
        description="Distance moyenne des sorties (mètres)"
    )
    
    # Defensive actions outside box
    def_actions_outside_box: int = Field(default=0, ge=0)
    def_actions_outside_box_per_match: float = Field(default=0, ge=0)
    
    # Crosses claimed
    crosses_stopped: int = Field(default=0, ge=0)
    crosses_stopped_rate: float = Field(default=0, ge=0, le=100)
    crosses_claimed_per_match: float = Field(default=0, ge=0)
    
    # High claims
    high_claims_per_match: float = Field(default=0, ge=0)
    high_claim_success_rate: float = Field(default=0, ge=0, le=100)
    
    # Punches
    punches_per_match: float = Field(default=0, ge=0)
    
    @computed_field
    @property
    def sweeping_aggressiveness(self) -> str:
        """Agressivité des sorties."""
        if self.sweeping_actions_per_match > 1.5:
            return "VERY_AGGRESSIVE"
        elif self.sweeping_actions_per_match > 1.0:
            return "AGGRESSIVE"
        elif self.sweeping_actions_per_match > 0.5:
            return "MODERATE"
        else:
            return "CONSERVATIVE"
    
    @computed_field
    @property
    def aerial_dominance(self) -> str:
        """Dominance aérienne dans la surface."""
        if self.crosses_stopped_rate > 15:
            return "DOMINANT"
        elif self.crosses_stopped_rate > 10:
            return "GOOD"
        elif self.crosses_stopped_rate > 5:
            return "AVERAGE"
        else:
            return "WEAK"


# ═══════════════════════════════════════════════════════════════════════════════════════
# PENALTY PROFILE
# ═══════════════════════════════════════════════════════════════════════════════════════

class PenaltyProfile(BaseModel):
    """
    Profil sur penalties.
    """
    
    model_config = ConfigDict(frozen=False)
    
    penalties_faced: int = Field(default=0, ge=0)
    penalties_saved: int = Field(default=0, ge=0)
    penalties_conceded: int = Field(default=0, ge=0)
    
    # Dans les tirs au but
    shootout_faced: int = Field(default=0, ge=0)
    shootout_saved: int = Field(default=0, ge=0)
    
    @computed_field
    @property
    def penalty_save_rate(self) -> float:
        """Taux d'arrêt de penalties."""
        if self.penalties_faced == 0:
            return 0
        return round(self.penalties_saved / self.penalties_faced * 100, 1)
    
    @computed_field
    @property
    def penalty_specialist(self) -> bool:
        """True si spécialiste des penalties."""
        return self.penalties_faced >= 5 and self.penalty_save_rate >= 30
    
    @computed_field
    @property
    def penalty_tier(self) -> str:
        """Niveau sur penalties."""
        rate = self.penalty_save_rate
        if rate >= 35:
            return "SPECIALIST"
        elif rate >= 25:
            return "GOOD"
        elif rate >= 15:
            return "AVERAGE"
        else:
            return "POOR"


# ═══════════════════════════════════════════════════════════════════════════════════════
# ERRORS & RELIABILITY
# ═══════════════════════════════════════════════════════════════════════════════════════

class ReliabilityMetrics(BaseModel):
    """
    Métriques de fiabilité et erreurs.
    """
    
    model_config = ConfigDict(frozen=False)
    
    # Errors
    errors_leading_to_goal: int = Field(default=0, ge=0)
    errors_leading_to_shot: int = Field(default=0, ge=0)
    
    # Consistency
    clean_sheets: int = Field(default=0, ge=0)
    clean_sheet_rate: float = Field(default=0, ge=0, le=100)
    
    # Conceding patterns
    goals_conceded_from_inside_box: float = Field(default=0, ge=0, le=100)
    goals_conceded_from_outside_box: float = Field(default=0, ge=0, le=100)
    
    @computed_field
    @property
    def error_rate(self) -> str:
        """Taux d'erreurs."""
        total_errors = self.errors_leading_to_goal + self.errors_leading_to_shot
        if total_errors == 0:
            return "FLAWLESS"
        elif total_errors <= 2:
            return "LOW"
        elif total_errors <= 4:
            return "MODERATE"
        else:
            return "HIGH"
    
    @computed_field
    @property
    def reliability_score(self) -> float:
        """Score de fiabilité (0-100)."""
        # Base sur clean sheets
        cs_component = self.clean_sheet_rate
        
        # Pénalité pour erreurs
        error_penalty = (self.errors_leading_to_goal * 10 + 
                        self.errors_leading_to_shot * 3)
        
        score = cs_component - error_penalty
        return round(max(0, min(100, score)), 1)


# ═══════════════════════════════════════════════════════════════════════════════════════
# GOALKEEPER DNA - Classe principale
# ═══════════════════════════════════════════════════════════════════════════════════════

class GoalkeeperDNA(QuantumBaseModel):
    """
    ADN complet du gardien d'une équipe.
    
    Note: Représente le gardien ACTUEL/PRINCIPAL de l'équipe,
    pas l'historique de tous les gardiens.
    """
    
    # Identité équipe
    team_name: str
    team_normalized: str = ""
    
    # Identité gardien
    goalkeeper_name: str = ""
    goalkeeper_normalized: str = ""
    age: Optional[int] = Field(default=None, ge=16, le=45)
    
    # Sub-components
    shot_stopping: ShotStoppingMetrics = Field(default_factory=ShotStoppingMetrics)
    distribution: DistributionMetrics = Field(default_factory=DistributionMetrics)
    sweeping: SweepingMetrics = Field(default_factory=SweepingMetrics)
    penalties: PenaltyProfile = Field(default_factory=PenaltyProfile)
    reliability: ReliabilityMetrics = Field(default_factory=ReliabilityMetrics)
    
    # Career context
    matches_this_season: int = Field(default=0, ge=0)
    minutes_played: int = Field(default=0, ge=0)
    
    # Metadata
    data_quality: DataQuality = Field(default=DataQuality.MODERATE)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    @computed_field
    @property
    def overall_rating(self) -> float:
        """
        Rating global du gardien (0-100).
        Combine tous les aspects.
        """
        # Shot stopping (40%)
        ss_rating = self.shot_stopping.shot_stopping_rating
        ss_normalized = max(0, min(100, 50 + ss_rating * 10))
        
        # Distribution (15%)
        dist_score = self.distribution.pass_completion * 0.8
        
        # Sweeping (15%)
        sweep_score = min(100, self.sweeping.sweeping_actions_per_match * 50 + 
                         self.sweeping.crosses_stopped_rate * 3)
        
        # Reliability (30%)
        rel_score = self.reliability.reliability_score
        
        overall = (ss_normalized * 0.4 + dist_score * 0.15 + 
                  sweep_score * 0.15 + rel_score * 0.3)
        
        return round(max(0, min(100, overall)), 1)
    
    @computed_field
    @property
    def goalkeeper_tier(self) -> str:
        """Classification du gardien."""
        rating = self.overall_rating
        if rating >= 80:
            return "ELITE"
        elif rating >= 70:
            return "TOP"
        elif rating >= 60:
            return "GOOD"
        elif rating >= 50:
            return "AVERAGE"
        elif rating >= 40:
            return "BELOW_AVERAGE"
        else:
            return "WEAK"
    
    @computed_field
    @property
    def style_profile(self) -> str:
        """Profil de style du gardien."""
        dist_style = self.distribution.distribution_style
        sweep_style = self.sweeping.sweeping_aggressiveness
        
        if dist_style == "SWEEPER_KEEPER" and sweep_style in ["AGGRESSIVE", "VERY_AGGRESSIVE"]:
            return "MODERN_SWEEPER"
        elif dist_style == "LONG_BALL":
            return "TRADITIONAL"
        elif self.shot_stopping.shot_stopping_tier in ["ELITE", "EXCELLENT"]:
            return "SHOT_STOPPER"
        else:
            return "BALANCED"
    
    @computed_field
    @property
    def clean_sheet_probability_modifier(self) -> float:
        """
        Modificateur de probabilité de clean sheet.
        Basé sur le rating et la fiabilité.
        
        > 0: Augmente la probabilité
        < 0: Diminue la probabilité
        """
        base_modifier = (self.overall_rating - 50) / 10  # -5 à +5
        
        # Bonus pour les spécialistes
        if self.shot_stopping.shot_stopping_tier == "ELITE":
            base_modifier += 2
        elif self.shot_stopping.shot_stopping_tier == "LIABILITY":
            base_modifier -= 3
        
        return round(base_modifier, 1)
    
    @computed_field
    @property
    def market_impact_summary(self) -> dict:
        """Résumé de l'impact sur les marchés."""
        return {
            "clean_sheet_modifier": self.clean_sheet_probability_modifier,
            "penalty_specialist": self.penalties.penalty_specialist,
            "shot_stopping_tier": self.shot_stopping.shot_stopping_tier,
            "reliability": self.reliability.error_rate,
            "style": self.style_profile,
        }
    
    @computed_field
    @property
    def strengths(self) -> List[str]:
        """Points forts identifiés."""
        strengths = []
        
        if self.shot_stopping.shot_stopping_tier in ["ELITE", "EXCELLENT"]:
            strengths.append("SHOT_STOPPING")
        
        if self.distribution.distribution_quality in ["EXCELLENT", "GOOD"]:
            strengths.append("DISTRIBUTION")
        
        if self.sweeping.sweeping_aggressiveness in ["AGGRESSIVE", "VERY_AGGRESSIVE"]:
            strengths.append("SWEEPING")
        
        if self.sweeping.aerial_dominance == "DOMINANT":
            strengths.append("AERIAL")
        
        if self.penalties.penalty_specialist:
            strengths.append("PENALTIES")
        
        if self.reliability.error_rate == "FLAWLESS":
            strengths.append("RELIABILITY")
        
        return strengths
    
    @computed_field
    @property
    def weaknesses(self) -> List[str]:
        """Points faibles identifiés."""
        weaknesses = []
        
        if self.shot_stopping.shot_stopping_tier in ["BELOW_AVERAGE", "LIABILITY"]:
            weaknesses.append("SHOT_STOPPING")
        
        if self.distribution.distribution_quality == "POOR":
            weaknesses.append("DISTRIBUTION")
        
        if self.sweeping.aerial_dominance == "WEAK":
            weaknesses.append("AERIAL")
        
        if self.reliability.error_rate == "HIGH":
            weaknesses.append("ERRORS")
        
        return weaknesses
