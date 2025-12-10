"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║  TEAM DNA - Agrégateur Unifié de tous les DNA                                        ║
║  Version: 2.0                                                                        ║
║  "Une équipe est plus que la somme de ses parties. Son DNA les unifie."              ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

Architecture Mon_PS - Chess Engine V2.0
Créé le: 2025-12-10

Installation: /home/Mon_ps/quantum/models/team_dna.py

TeamDNA est le point d'entrée principal pour accéder à toutes les
informations d'une équipe. Il agrège:
- ContextDNA (attaque, possession, momentum)
- DefenseDNA (xGA, zones, pressing resistance)
- GoalkeeperDNA (arrêts, distribution, fiabilité)
- VarianceDNA (chance, régression, value)
- ExploitProfile (faiblesses, marchés, edges)
- CoachDNA (tactique, subs, réactions)
"""

from pydantic import Field, ConfigDict, computed_field, field_validator
from typing import Optional, List, Dict
from datetime import datetime

from .base import QuantumBaseModel, ConfidentMetric
from .enums import (
    Formation,
    DefenseProfile,
    AttackProfile,
    MomentumState,
    VarianceProfile,
    MatchupProfile,
    DataQuality,
    League,
)
from .coach_dna import CoachDNA

# Sub-models
from .sub_models.context_dna import ContextDNA
from .sub_models.defense_dna import DefenseDNA
from .sub_models.goalkeeper_dna import GoalkeeperDNA
from .sub_models.variance_dna import VarianceDNA
from .sub_models.exploit_profile import ExploitProfile


# ═══════════════════════════════════════════════════════════════════════════════════════
# TEAM IDENTITY
# ═══════════════════════════════════════════════════════════════════════════════════════

class TeamIdentity(QuantumBaseModel):
    """
    Identité de base d'une équipe.
    """
    
    name: str = Field(description="Nom officiel de l'équipe")
    name_normalized: str = Field(default="", description="Nom normalisé pour matching")
    
    # Aliases for matching
    aliases: List[str] = Field(
        default_factory=list,
        description="Noms alternatifs (abréviations, anciens noms)"
    )
    
    # League & Position
    league: str = Field(default="")
    league_tier: str = Field(default="TOP_5")
    current_position: int = Field(default=0, ge=0)
    
    # Season
    season: str = Field(default="2024-2025")
    
    # IDs externes
    understat_id: Optional[int] = None
    fotmob_id: Optional[int] = None
    sofascore_id: Optional[int] = None
    
    @field_validator("name_normalized", mode="before")
    @classmethod
    def auto_normalize(cls, v, info):
        if not v and "name" in info.data:
            return info.data["name"].lower().replace(" ", "_").replace("-", "_")
        return v


# ═══════════════════════════════════════════════════════════════════════════════════════
# TEAM DNA - Classe principale
# ═══════════════════════════════════════════════════════════════════════════════════════

class TeamDNA(QuantumBaseModel):
    """
    ADN complet d'une équipe - Agrégateur de tous les DNA.
    
    ═══════════════════════════════════════════════════════════════════════════════════
    USAGE:
    
    >>> liverpool = TeamDNA.load("Liverpool")
    >>> 
    >>> # Accès aux composants
    >>> liverpool.context.offensive.xg_per_match
    >>> liverpool.defense.zones.weak_side
    >>> liverpool.goalkeeper.shot_stopping.shot_stopping_tier
    >>> liverpool.variance.betting_signal
    >>> liverpool.exploit.best_markets
    >>> 
    >>> # Comparaisons
    >>> liverpool.predict_matchup(arsenal)
    >>> liverpool.calculate_edge_vs(arsenal, "BTTS_YES")
    >>> 
    >>> # Score global
    >>> liverpool.overall_strength_score
    ═══════════════════════════════════════════════════════════════════════════════════
    """
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # IDENTITY
    # ─────────────────────────────────────────────────────────────────────────────────
    
    identity: TeamIdentity
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # DNA COMPONENTS
    # ─────────────────────────────────────────────────────────────────────────────────
    
    context: Optional[ContextDNA] = None
    defense: Optional[DefenseDNA] = None
    goalkeeper: Optional[GoalkeeperDNA] = None
    variance: Optional[VarianceDNA] = None
    exploit: Optional[ExploitProfile] = None
    coach: Optional[CoachDNA] = None
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # QUICK ACCESS STATS
    # ─────────────────────────────────────────────────────────────────────────────────
    
    # Points & Position
    points: int = Field(default=0, ge=0)
    matches_played: int = Field(default=0, ge=0)
    wins: int = Field(default=0, ge=0)
    draws: int = Field(default=0, ge=0)
    losses: int = Field(default=0, ge=0)
    
    # Goals
    goals_for: int = Field(default=0, ge=0)
    goals_against: int = Field(default=0, ge=0)
    
    # xG summary
    xg_total: float = Field(default=0, ge=0)
    xga_total: float = Field(default=0, ge=0)
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # METADATA
    # ─────────────────────────────────────────────────────────────────────────────────
    
    data_quality: DataQuality = Field(default=DataQuality.MODERATE)
    data_completeness: float = Field(default=0, ge=0, le=100)
    last_match_date: Optional[datetime] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # QUICK ACCESS PROPERTIES
    # ─────────────────────────────────────────────────────────────────────────────────
    
    @property
    def name(self) -> str:
        """Raccourci vers le nom."""
        return self.identity.name
    
    @property
    def league(self) -> str:
        """Raccourci vers la ligue."""
        return self.identity.league
    
    @computed_field
    @property
    def points_per_match(self) -> float:
        """Points par match."""
        if self.matches_played == 0:
            return 0
        return round(self.points / self.matches_played, 2)
    
    @computed_field
    @property
    def goal_difference(self) -> int:
        """Différence de buts."""
        return self.goals_for - self.goals_against
    
    @computed_field
    @property
    def xg_difference(self) -> float:
        """Différence xG."""
        return round(self.xg_total - self.xga_total, 2)
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # PROFILES AGRÉGÉS
    # ─────────────────────────────────────────────────────────────────────────────────
    
    @computed_field
    @property
    def attack_profile(self) -> AttackProfile:
        """Profil offensif (délégué à ContextDNA)."""
        if self.context:
            return self.context.attack_profile
        return AttackProfile.AVERAGE
    
    @computed_field
    @property
    def defense_profile(self) -> DefenseProfile:
        """Profil défensif (délégué à DefenseDNA)."""
        if self.defense:
            return self.defense.defense_profile
        return DefenseProfile.AVERAGE
    
    @computed_field
    @property
    def momentum_state(self) -> MomentumState:
        """État de momentum (délégué à ContextDNA)."""
        if self.context:
            return self.context.momentum.momentum_state
        return MomentumState.STABLE
    
    @computed_field
    @property
    def variance_profile(self) -> VarianceProfile:
        """Profil de variance (délégué à VarianceDNA)."""
        if self.variance:
            return self.variance.overall_variance_profile
        return VarianceProfile.NEUTRAL
    
    @computed_field
    @property
    def primary_formation(self) -> Formation:
        """Formation principale (délégué à CoachDNA)."""
        if self.coach:
            return self.coach.formation_primary
        return Formation.F_4_3_3
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # SCORES AGRÉGÉS
    # ─────────────────────────────────────────────────────────────────────────────────
    
    @computed_field
    @property
    def overall_strength_score(self) -> float:
        """
        Score de force globale (0-100).
        Combine tous les DNA pour un score unifié.
        """
        components = []
        weights = []
        
        # Attack (25%)
        if self.context:
            components.append(self.context.attacking_threat_score)
            weights.append(0.25)
        
        # Defense (25%)
        if self.defense:
            components.append(self.defense.defensive_strength_score)
            weights.append(0.25)
        
        # Goalkeeper (15%)
        if self.goalkeeper:
            components.append(self.goalkeeper.overall_rating)
            weights.append(0.15)
        
        # Coach (20%)
        if self.coach:
            components.append(self.coach.coaching_score)
            weights.append(0.20)
        
        # Momentum bonus/malus (15%)
        momentum_score = {
            MomentumState.ON_FIRE: 85,
            MomentumState.HOT: 70,
            MomentumState.STABLE: 50,
            MomentumState.COLD: 35,
            MomentumState.CRISIS: 20,
        }.get(self.momentum_state, 50)
        components.append(momentum_score)
        weights.append(0.15)
        
        if not components:
            return 50.0
        
        # Normaliser les poids
        total_weight = sum(weights)
        weighted_sum = sum(c * w for c, w in zip(components, weights))
        
        return round(weighted_sum / total_weight, 1)
    
    @computed_field
    @property
    def exploitation_score(self) -> float:
        """Score d'exploitabilité (délégué à ExploitProfile)."""
        if self.exploit:
            return self.exploit.exploitation_score
        return 50.0
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # BETTING SIGNALS
    # ─────────────────────────────────────────────────────────────────────────────────
    
    @computed_field
    @property
    def betting_signal(self) -> str:
        """Signal de betting basé sur la variance."""
        if self.variance:
            return self.variance.betting_signal
        return "HOLD"
    
    @computed_field
    @property
    def best_markets(self) -> List[str]:
        """Meilleurs marchés à exploiter."""
        if self.exploit:
            return self.exploit.best_markets
        return []
    
    @computed_field
    @property
    def fade_markets(self) -> List[str]:
        """Marchés à éviter."""
        if self.exploit:
            return self.exploit.fade_markets
        return []
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # WEAKNESSES SUMMARY
    # ─────────────────────────────────────────────────────────────────────────────────
    
    @computed_field
    @property
    def all_weaknesses(self) -> List[str]:
        """Liste de toutes les faiblesses identifiées."""
        weaknesses = []
        
        # From Defense DNA
        if self.defense:
            weaknesses.extend(self.defense.exploitable_weaknesses)
        
        # From Goalkeeper DNA
        if self.goalkeeper:
            weaknesses.extend(self.goalkeeper.weaknesses)
        
        # From Exploit Profile
        if self.exploit:
            weaknesses.extend([w.weakness_type for w in self.exploit.actionable_weaknesses])
        
        # From Coach DNA
        if self.coach and self.coach.substitutions:
            if self.coach.substitutions.late_collapse_risk == "HIGH":
                weaknesses.append("LATE_COLLAPSE")
        
        return list(set(weaknesses))  # Dédupliquer
    
    @computed_field
    @property
    def all_strengths(self) -> List[str]:
        """Liste de toutes les forces identifiées."""
        strengths = []
        
        # From Goalkeeper
        if self.goalkeeper:
            strengths.extend(self.goalkeeper.strengths)
        
        # From Context
        if self.context:
            if self.context.attack_profile in [AttackProfile.ELITE, AttackProfile.DANGEROUS]:
                strengths.append("ATTACK")
        
        # From Defense
        if self.defense:
            if self.defense.defense_profile in [DefenseProfile.FORTRESS, DefenseProfile.SOLID]:
                strengths.append("DEFENSE")
        
        # From Coach
        if self.coach:
            if self.coach.tactical_fingerprint.tactical_flexibility > 70:
                strengths.append("TACTICAL_FLEXIBILITY")
            if self.coach.tactical_fingerprint.set_piece_focus > 75:
                strengths.append("SET_PIECES")
        
        return list(set(strengths))
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # METHODS
    # ─────────────────────────────────────────────────────────────────────────────────
    
    def predict_matchup(self, opponent: "TeamDNA") -> str:
        """
        Prédit le type de confrontation contre un adversaire.
        
        Args:
            opponent: TeamDNA de l'adversaire
            
        Returns:
            Type de matchup (PRESSING_WAR, CHESS_MATCH, etc.)
        """
        if self.coach and opponent.coach:
            return self.coach.predict_matchup_style(opponent.coach)
        
        # Fallback basé sur les profils
        my_attack = self.attack_profile
        opp_defense = opponent.defense_profile
        
        if my_attack in [AttackProfile.ELITE] and opp_defense in [DefenseProfile.FORTRESS]:
            return "POSSESSION_VS_BUS"
        
        return "UNKNOWN"
    
    def calculate_edge_vs(self, opponent: "TeamDNA", market: str) -> Optional[float]:
        """
        Calcule l'edge sur un marché spécifique contre un adversaire.
        
        Args:
            opponent: TeamDNA de l'adversaire
            market: Type de marché
            
        Returns:
            Edge en % ou None si pas calculable
        """
        # Si on a un exploit profile avec le marché
        if self.exploit:
            edge = self.exploit.get_edge_for_market(market)
            if edge:
                return edge.total_edge_pct
        
        return None
    
    def tactical_similarity_to(self, other: "TeamDNA") -> float:
        """
        Calcule la similarité tactique avec une autre équipe.
        Basé sur les CoachDNA.
        """
        if self.coach and other.coach:
            return self.coach.tactical_similarity(other.coach)
        return 50.0  # Neutre si pas de données
    
    @computed_field
    @property
    def quick_summary(self) -> dict:
        """Résumé rapide de l'équipe."""
        return {
            "name": self.name,
            "league": self.league,
            "position": self.identity.current_position,
            "points": self.points,
            "ppg": self.points_per_match,
            "strength_score": self.overall_strength_score,
            "attack_profile": self.attack_profile.value,
            "defense_profile": self.defense_profile.value,
            "momentum": self.momentum_state.value,
            "variance": self.variance_profile.value,
            "betting_signal": self.betting_signal,
            "weaknesses_count": len(self.all_weaknesses),
            "data_quality": self.data_quality.value,
        }
    
    def is_complete(self) -> bool:
        """Vérifie si tous les DNA sont présents."""
        return all([
            self.context is not None,
            self.defense is not None,
            self.goalkeeper is not None,
            self.variance is not None,
            self.exploit is not None,
            self.coach is not None,
        ])
    
    @computed_field
    @property
    def missing_components(self) -> List[str]:
        """Liste des composants manquants."""
        missing = []
        if not self.context:
            missing.append("context")
        if not self.defense:
            missing.append("defense")
        if not self.goalkeeper:
            missing.append("goalkeeper")
        if not self.variance:
            missing.append("variance")
        if not self.exploit:
            missing.append("exploit")
        if not self.coach:
            missing.append("coach")
        return missing
