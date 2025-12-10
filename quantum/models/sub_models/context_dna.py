"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║  CONTEXT DNA - Contexte Offensif & Style de Jeu                                      ║
║  Version: 2.0                                                                        ║
║  "L'attaque d'une équipe se mesure en xG, mais se comprend en contexte."             ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

Architecture Mon_PS - Chess Engine V2.0
Créé le: 2025-12-10

Installation: /home/Mon_ps/quantum/models/sub_models/context_dna.py

Sources de données:
- /home/Mon_ps/data/quantum_v2/teams_context_dna.json
- PostgreSQL: team_statistics, match_stats
"""

from pydantic import BaseModel, Field, ConfigDict, computed_field
from typing import Optional, Dict, List
from datetime import datetime

from ..base import QuantumBaseModel, ConfidentMetric, TimingMetric
from ..enums import (
    AttackProfile,
    MomentumState,
    FormTrend,
    TimingSignature,
    DataQuality
)


# ═══════════════════════════════════════════════════════════════════════════════════════
# OFFENSIVE METRICS
# ═══════════════════════════════════════════════════════════════════════════════════════

class OffensiveMetrics(BaseModel):
    """
    Métriques offensives brutes et avancées.
    """
    
    model_config = ConfigDict(frozen=False)
    
    # Goals & xG
    goals_scored: int = Field(default=0, ge=0)
    goals_per_match: float = Field(default=0, ge=0)
    xg_total: float = Field(default=0, ge=0)
    xg_per_match: ConfidentMetric = Field(default_factory=ConfidentMetric.zero)
    
    # Conversion
    goals_minus_xg: float = Field(
        default=0,
        description="Goals - xG. Positif = surperformance, négatif = sous-performance"
    )
    conversion_rate: float = Field(
        default=0, ge=0, le=100,
        description="% de tirs cadrés convertis en buts"
    )
    
    # Shots
    shots_total: int = Field(default=0, ge=0)
    shots_per_match: float = Field(default=0, ge=0)
    shots_on_target_per_match: float = Field(default=0, ge=0)
    shot_accuracy: float = Field(default=0, ge=0, le=100)
    
    # Big chances
    big_chances_created: int = Field(default=0, ge=0)
    big_chances_missed: int = Field(default=0, ge=0)
    big_chance_conversion: float = Field(default=0, ge=0, le=100)
    
    # Timing (quand l'équipe marque)
    goals_timing: Optional[TimingMetric] = None
    xg_timing: Optional[TimingMetric] = None
    
    @computed_field
    @property
    def xg_overperformance(self) -> float:
        """
        % de surperformance par rapport à xG.
        > 0 = Finition exceptionnelle (ou chance)
        < 0 = Mauvaise finition (ou malchance)
        """
        if self.xg_total == 0:
            return 0
        return round((self.goals_scored - self.xg_total) / self.xg_total * 100, 1)
    
    @computed_field
    @property
    def clinical_rating(self) -> str:
        """
        Évaluation de l'efficacité devant le but.
        """
        if self.xg_overperformance > 15:
            return "ELITE_FINISHERS"
        elif self.xg_overperformance > 5:
            return "CLINICAL"
        elif self.xg_overperformance > -5:
            return "AVERAGE"
        elif self.xg_overperformance > -15:
            return "WASTEFUL"
        else:
            return "IMPOTENT"


# ═══════════════════════════════════════════════════════════════════════════════════════
# POSSESSION & STYLE METRICS
# ═══════════════════════════════════════════════════════════════════════════════════════

class PossessionMetrics(BaseModel):
    """
    Métriques de possession et style de jeu.
    """
    
    model_config = ConfigDict(frozen=False)
    
    # Possession
    possession_avg: float = Field(default=50, ge=0, le=100)
    possession_home: float = Field(default=50, ge=0, le=100)
    possession_away: float = Field(default=50, ge=0, le=100)
    
    # Passing
    passes_per_match: float = Field(default=0, ge=0)
    pass_accuracy: float = Field(default=0, ge=0, le=100)
    progressive_passes_per_match: float = Field(default=0, ge=0)
    
    # Ball progression
    progressive_carries_per_match: float = Field(default=0, ge=0)
    touches_in_box_per_match: float = Field(default=0, ge=0)
    
    # Tempo
    direct_speed_index: float = Field(
        default=50, ge=0, le=100,
        description="0=Possession lente, 100=Jeu direct rapide"
    )
    
    @computed_field
    @property
    def possession_dominance(self) -> str:
        """Niveau de domination de la possession."""
        if self.possession_avg >= 60:
            return "DOMINANT"
        elif self.possession_avg >= 55:
            return "CONTROLLING"
        elif self.possession_avg >= 45:
            return "BALANCED"
        elif self.possession_avg >= 40:
            return "REACTIVE"
        else:
            return "COUNTER_ATTACK"
    
    @computed_field
    @property
    def home_away_possession_diff(self) -> float:
        """Différence de possession home/away."""
        return round(self.possession_home - self.possession_away, 1)


# ═══════════════════════════════════════════════════════════════════════════════════════
# MOMENTUM & FORM
# ═══════════════════════════════════════════════════════════════════════════════════════

class MomentumMetrics(BaseModel):
    """
    État de forme et momentum actuel.
    
    CRUCIAL pour les paris:
    - Équipe ON_FIRE = cotes basses mais souvent justifiées
    - Équipe CRISIS = value potentielle si régression attendue
    """
    
    model_config = ConfigDict(frozen=False)
    
    # Form récente
    last_5_points: int = Field(default=0, ge=0, le=15)
    last_5_goals_for: int = Field(default=0, ge=0)
    last_5_goals_against: int = Field(default=0, ge=0)
    last_5_xg: float = Field(default=0, ge=0)
    last_5_xga: float = Field(default=0, ge=0)
    
    # Comparaison L5 vs L10
    last_10_points: int = Field(default=0, ge=0, le=30)
    last_10_xg: float = Field(default=0, ge=0)
    last_10_xga: float = Field(default=0, ge=0)
    
    # Séries
    unbeaten_streak: int = Field(default=0, ge=0)
    winless_streak: int = Field(default=0, ge=0)
    clean_sheet_streak: int = Field(default=0, ge=0)
    scoring_streak: int = Field(default=0, ge=0)
    
    # Résultats récents détaillés
    last_5_results: str = Field(
        default="",
        description="Format: 'WWDLW' (Win/Draw/Loss, plus récent à droite)"
    )
    
    @computed_field
    @property
    def momentum_state(self) -> MomentumState:
        """État de momentum actuel."""
        ppg_l5 = self.last_5_points / 5 if self.last_5_points else 0
        
        if self.unbeaten_streak >= 5 and ppg_l5 >= 2.4:
            return MomentumState.ON_FIRE
        elif self.unbeaten_streak >= 3 or ppg_l5 >= 2.0:
            return MomentumState.HOT
        elif self.winless_streak >= 4 or ppg_l5 <= 0.6:
            return MomentumState.CRISIS
        elif self.winless_streak >= 2 or ppg_l5 <= 1.0:
            return MomentumState.COLD
        else:
            return MomentumState.STABLE
    
    @computed_field
    @property
    def form_trend(self) -> FormTrend:
        """Tendance de forme (L5 vs L10)."""
        if self.last_10_points == 0:
            return FormTrend.STABLE
        
        ppg_l5 = self.last_5_points / 5
        ppg_l10 = self.last_10_points / 10
        
        diff = ppg_l5 - ppg_l10
        
        if diff > 0.4:
            return FormTrend.IMPROVING
        elif diff < -0.4:
            return FormTrend.DECLINING
        else:
            return FormTrend.STABLE
    
    @computed_field
    @property
    def xg_form_trend(self) -> str:
        """Tendance xG (L5 vs L10)."""
        if self.last_10_xg == 0:
            return "NO_DATA"
        
        xg_per_match_l5 = self.last_5_xg / 5
        xg_per_match_l10 = self.last_10_xg / 10
        
        diff = xg_per_match_l5 - xg_per_match_l10
        
        if diff > 0.3:
            return "XG_RISING"
        elif diff < -0.3:
            return "XG_FALLING"
        else:
            return "XG_STABLE"
    
    @computed_field
    @property
    def points_per_game_l5(self) -> float:
        """Points par match sur les 5 derniers."""
        return round(self.last_5_points / 5, 2)


# ═══════════════════════════════════════════════════════════════════════════════════════
# HOME/AWAY SPLITS
# ═══════════════════════════════════════════════════════════════════════════════════════

class HomeAwaySplits(BaseModel):
    """
    Différences de performance domicile/extérieur.
    
    CRUCIAL pour identifier:
    - Forteresses imprenables (home fortress)
    - Road warriors (fort à l'extérieur)
    - Équipes fragiles à l'extérieur (fade away)
    """
    
    model_config = ConfigDict(frozen=False)
    
    # Home stats
    home_matches: int = Field(default=0, ge=0)
    home_wins: int = Field(default=0, ge=0)
    home_draws: int = Field(default=0, ge=0)
    home_losses: int = Field(default=0, ge=0)
    home_goals_for: int = Field(default=0, ge=0)
    home_goals_against: int = Field(default=0, ge=0)
    home_xg: float = Field(default=0, ge=0)
    home_xga: float = Field(default=0, ge=0)
    home_points_per_match: float = Field(default=0, ge=0)
    
    # Away stats
    away_matches: int = Field(default=0, ge=0)
    away_wins: int = Field(default=0, ge=0)
    away_draws: int = Field(default=0, ge=0)
    away_losses: int = Field(default=0, ge=0)
    away_goals_for: int = Field(default=0, ge=0)
    away_goals_against: int = Field(default=0, ge=0)
    away_xg: float = Field(default=0, ge=0)
    away_xga: float = Field(default=0, ge=0)
    away_points_per_match: float = Field(default=0, ge=0)
    
    @computed_field
    @property
    def home_win_rate(self) -> float:
        """Taux de victoire à domicile."""
        if self.home_matches == 0:
            return 0
        return round(self.home_wins / self.home_matches * 100, 1)
    
    @computed_field
    @property
    def away_win_rate(self) -> float:
        """Taux de victoire à l'extérieur."""
        if self.away_matches == 0:
            return 0
        return round(self.away_wins / self.away_matches * 100, 1)
    
    @computed_field
    @property
    def home_advantage_index(self) -> float:
        """
        Index d'avantage domicile (0-100).
        50 = Pas de différence home/away
        > 70 = Fort avantage domicile
        < 30 = Meilleur à l'extérieur (rare)
        """
        if self.home_matches == 0 or self.away_matches == 0:
            return 50
        
        home_ppg = self.home_points_per_match
        away_ppg = self.away_points_per_match
        
        # Normaliser: différence max attendue ~1.5 PPG
        diff = home_ppg - away_ppg
        index = 50 + (diff / 1.5) * 25
        
        return round(max(0, min(100, index)), 1)
    
    @computed_field
    @property
    def home_profile(self) -> str:
        """Profil domicile."""
        rate = self.home_win_rate
        if rate >= 70:
            return "FORTRESS"
        elif rate >= 55:
            return "STRONG"
        elif rate >= 40:
            return "AVERAGE"
        elif rate >= 25:
            return "WEAK"
        else:
            return "VULNERABLE"
    
    @computed_field
    @property
    def away_profile(self) -> str:
        """Profil extérieur."""
        rate = self.away_win_rate
        if rate >= 50:
            return "ROAD_WARRIOR"
        elif rate >= 35:
            return "SOLID"
        elif rate >= 20:
            return "AVERAGE"
        elif rate >= 10:
            return "WEAK"
        else:
            return "FRAGILE"
    
    @computed_field
    @property
    def xg_home_away_diff(self) -> float:
        """Différence xG home vs away par match."""
        home_xg_pm = self.home_xg / max(1, self.home_matches)
        away_xg_pm = self.away_xg / max(1, self.away_matches)
        return round(home_xg_pm - away_xg_pm, 2)


# ═══════════════════════════════════════════════════════════════════════════════════════
# CONTEXT DNA - Classe principale
# ═══════════════════════════════════════════════════════════════════════════════════════

class ContextDNA(QuantumBaseModel):
    """
    ADN de contexte offensif et style de jeu.
    
    Agrège:
    - Métriques offensives (xG, conversion, timing)
    - Style de possession
    - Momentum et forme
    - Splits home/away
    """
    
    # Identité
    team_name: str
    team_normalized: str = ""
    league: str = ""
    season: str = "2024-2025"
    
    # Sub-components
    offensive: OffensiveMetrics = Field(default_factory=OffensiveMetrics)
    possession: PossessionMetrics = Field(default_factory=PossessionMetrics)
    momentum: MomentumMetrics = Field(default_factory=MomentumMetrics)
    home_away: HomeAwaySplits = Field(default_factory=HomeAwaySplits)
    
    # Metadata
    matches_analyzed: int = Field(default=0, ge=0)
    data_quality: DataQuality = Field(default=DataQuality.MODERATE)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    @computed_field
    @property
    def attack_profile(self) -> AttackProfile:
        """Profil offensif global."""
        xg_pm = self.offensive.xg_per_match.value
        
        if xg_pm >= 2.0:
            return AttackProfile.ELITE
        elif xg_pm >= 1.5:
            return AttackProfile.DANGEROUS
        elif xg_pm >= 1.0:
            return AttackProfile.AVERAGE
        elif xg_pm >= 0.7:
            return AttackProfile.TOOTHLESS
        else:
            return AttackProfile.IMPOTENT
    
    @computed_field
    @property
    def goals_timing_signature(self) -> TimingSignature:
        """Signature de timing des buts."""
        if self.offensive.goals_timing:
            sig = self.offensive.goals_timing.timing_signature
            # Mapper string vers enum
            mapping = {
                "DIESEL": TimingSignature.DIESEL,
                "EARLY_BIRD": TimingSignature.EARLY_BIRD,
                "CLUTCH": TimingSignature.CLUTCH,
                "FIRST_HALF_TEAM": TimingSignature.FIRST_HALF_TEAM,
                "SECOND_HALF_TEAM": TimingSignature.SECOND_HALF_TEAM,
                "BALANCED": TimingSignature.BALANCED,
            }
            return mapping.get(sig, TimingSignature.BALANCED)
        return TimingSignature.BALANCED
    
    @computed_field
    @property
    def attacking_threat_score(self) -> float:
        """
        Score de menace offensive (0-100).
        Combine: xG, conversion, big chances, momentum.
        """
        xg_component = min(40, self.offensive.xg_per_match.value * 20)
        conversion_component = self.offensive.conversion_rate * 0.3
        
        # Momentum bonus/malus
        momentum_modifier = {
            MomentumState.ON_FIRE: 10,
            MomentumState.HOT: 5,
            MomentumState.STABLE: 0,
            MomentumState.COLD: -5,
            MomentumState.CRISIS: -10,
        }.get(self.momentum.momentum_state, 0)
        
        score = xg_component + conversion_component + momentum_modifier + 20
        return round(max(0, min(100, score)), 1)
    
    @computed_field
    @property
    def style_summary(self) -> str:
        """Résumé du style de jeu."""
        possession = self.possession.possession_dominance
        tempo = "FAST" if self.possession.direct_speed_index > 60 else "SLOW" if self.possession.direct_speed_index < 40 else "MEDIUM"
        attack = self.attack_profile.value.upper()
        
        return f"{possession}_{tempo}_{attack}"
