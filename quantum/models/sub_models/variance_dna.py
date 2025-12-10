"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║  VARIANCE DNA - Chance, Malchance & Régression                                       ║
║  Version: 2.0                                                                        ║
║  "La chance finit toujours par tourner. La question est: quand?"                     ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

Architecture Mon_PS - Chess Engine V2.0
Créé le: 2025-12-10

Installation: /home/Mon_ps/quantum/models/sub_models/variance_dna.py

CONCEPT CLÉ:
La variance (chance/malchance) est mesurable via xPts - Points réels.
Une équipe "chanceuse" va régresser vers le bas = FADE
Une équipe "malchanceuse" va régresser vers le haut = VALUE
"""

from pydantic import BaseModel, Field, ConfigDict, computed_field
from typing import Optional, List
from datetime import datetime

from ..base import QuantumBaseModel, ConfidentMetric
from ..enums import VarianceProfile, DataQuality


# ═══════════════════════════════════════════════════════════════════════════════════════
# EXPECTED POINTS
# ═══════════════════════════════════════════════════════════════════════════════════════

class ExpectedPointsMetrics(BaseModel):
    """
    Métriques de points attendus vs réels.
    
    FORMULE xPts:
    xPts = Σ (P(Win) * 3 + P(Draw) * 1)
    où P(Win) et P(Draw) sont calculés via simulations Monte Carlo basées sur xG.
    """
    
    model_config = ConfigDict(frozen=False)
    
    # Points réels
    points_actual: int = Field(default=0, ge=0)
    matches_played: int = Field(default=0, ge=0)
    
    # Points attendus
    xpts_total: float = Field(
        default=0, ge=0,
        description="Expected Points basés sur xG"
    )
    
    # Différence
    points_diff: float = Field(
        default=0,
        description="Points réels - xPts. Positif = chanceux"
    )
    
    # Par match
    points_per_match: float = Field(default=0, ge=0)
    xpts_per_match: float = Field(default=0, ge=0)
    
    @computed_field
    @property
    def luck_index(self) -> float:
        """
        Index de chance (-100 à +100).
        
        Formule: (points_diff / matches_played) * 50
        
        > +10: Très chanceux
        > +5: Chanceux
        -5 à +5: Normal
        < -5: Malchanceux
        < -10: Très malchanceux
        """
        if self.matches_played == 0:
            return 0
        return round((self.points_diff / self.matches_played) * 50, 1)
    
    @computed_field
    @property
    def variance_profile(self) -> VarianceProfile:
        """Classification de variance."""
        diff = self.points_diff
        
        if diff >= 8:
            return VarianceProfile.EXTREMELY_LUCKY
        elif diff >= 4:
            return VarianceProfile.LUCKY
        elif diff >= -4:
            return VarianceProfile.NEUTRAL
        elif diff >= -8:
            return VarianceProfile.UNLUCKY
        else:
            return VarianceProfile.EXTREMELY_UNLUCKY
    
    @computed_field
    @property
    def regression_direction(self) -> str:
        """Direction attendue de la régression."""
        if self.points_diff > 4:
            return "DOWN"  # Va régresser vers le bas
        elif self.points_diff < -4:
            return "UP"    # Va régresser vers le haut = VALUE
        else:
            return "STABLE"
    
    @computed_field
    @property
    def regression_magnitude(self) -> str:
        """Magnitude de la régression attendue."""
        abs_diff = abs(self.points_diff)
        if abs_diff >= 8:
            return "STRONG"
        elif abs_diff >= 4:
            return "MODERATE"
        else:
            return "WEAK"


# ═══════════════════════════════════════════════════════════════════════════════════════
# GOAL VARIANCE
# ═══════════════════════════════════════════════════════════════════════════════════════

class GoalVarianceMetrics(BaseModel):
    """
    Variance au niveau des buts (xG vs Goals réels).
    """
    
    model_config = ConfigDict(frozen=False)
    
    # Offensive
    goals_scored: int = Field(default=0, ge=0)
    xg_total: float = Field(default=0, ge=0)
    goals_minus_xg: float = Field(default=0)
    
    # Defensive
    goals_conceded: int = Field(default=0, ge=0)
    xga_total: float = Field(default=0, ge=0)
    goals_minus_xga: float = Field(default=0)
    
    @computed_field
    @property
    def offensive_luck(self) -> str:
        """Chance offensive (finition)."""
        if self.goals_minus_xg > 4:
            return "VERY_LUCKY"
        elif self.goals_minus_xg > 2:
            return "LUCKY"
        elif self.goals_minus_xg > -2:
            return "NEUTRAL"
        elif self.goals_minus_xg > -4:
            return "UNLUCKY"
        else:
            return "VERY_UNLUCKY"
    
    @computed_field
    @property
    def defensive_luck(self) -> str:
        """Chance défensive (gardien/posts/etc)."""
        # Inversé: moins de buts que xGA = chanceux
        if self.goals_minus_xga < -4:
            return "VERY_LUCKY"
        elif self.goals_minus_xga < -2:
            return "LUCKY"
        elif self.goals_minus_xga < 2:
            return "NEUTRAL"
        elif self.goals_minus_xga < 4:
            return "UNLUCKY"
        else:
            return "VERY_UNLUCKY"
    
    @computed_field
    @property
    def total_goal_variance(self) -> float:
        """
        Variance totale en buts.
        Positif = plus de buts pour, moins de buts contre que prévu
        """
        return round(self.goals_minus_xg - self.goals_minus_xga, 2)


# ═══════════════════════════════════════════════════════════════════════════════════════
# CONVERSION VARIANCE
# ═══════════════════════════════════════════════════════════════════════════════════════

class ConversionVariance(BaseModel):
    """
    Variance de conversion (big chances, penalties, etc).
    """
    
    model_config = ConfigDict(frozen=False)
    
    # Big chances
    big_chances_scored: int = Field(default=0, ge=0)
    big_chances_created: int = Field(default=0, ge=0)
    big_chances_missed: int = Field(default=0, ge=0)
    big_chance_conversion: float = Field(default=0, ge=0, le=100)
    expected_big_chance_conversion: float = Field(
        default=45, ge=0, le=100,
        description="Conversion attendue historique (~45%)"
    )
    
    # Opponent big chances
    opponent_big_chances: int = Field(default=0, ge=0)
    opponent_big_chances_scored: int = Field(default=0, ge=0)
    opponent_big_chance_conversion: float = Field(default=0, ge=0, le=100)
    
    # Penalties
    penalties_scored: int = Field(default=0, ge=0)
    penalties_taken: int = Field(default=0, ge=0)
    penalties_missed: int = Field(default=0, ge=0)
    
    penalties_conceded: int = Field(default=0, ge=0)
    opponent_penalties_scored: int = Field(default=0, ge=0)
    
    @computed_field
    @property
    def big_chance_luck(self) -> float:
        """
        Luck sur big chances (différence vs expected).
        Positif = chanceux dans la conversion
        """
        if self.big_chances_created == 0:
            return 0
        expected_scored = self.big_chances_created * (self.expected_big_chance_conversion / 100)
        return round(self.big_chances_scored - expected_scored, 1)
    
    @computed_field
    @property
    def opponent_big_chance_luck(self) -> float:
        """
        Luck sur big chances adverses.
        Négatif = adversaires ont converti moins que prévu = chanceux défensivement
        """
        if self.opponent_big_chances == 0:
            return 0
        expected = self.opponent_big_chances * 0.45  # 45% expected
        return round(self.opponent_big_chances_scored - expected, 1)
    
    @computed_field
    @property
    def penalty_variance(self) -> int:
        """
        Variance sur penalties (bilan net).
        Positif = plus de pens pour, moins contre que la moyenne
        """
        pen_for_net = self.penalties_scored - self.penalties_missed
        pen_against_net = self.opponent_penalties_scored
        return pen_for_net - pen_against_net


# ═══════════════════════════════════════════════════════════════════════════════════════
# CLOSE GAMES VARIANCE
# ═══════════════════════════════════════════════════════════════════════════════════════

class CloseGamesMetrics(BaseModel):
    """
    Performance dans les matchs serrés.
    
    CONCEPT: Les matchs serrés ont beaucoup de variance.
    Une équipe qui gagne tous ses matchs serrés 1-0 régresse.
    """
    
    model_config = ConfigDict(frozen=False)
    
    # Close games (1 but d'écart max)
    close_games_total: int = Field(default=0, ge=0)
    close_games_won: int = Field(default=0, ge=0)
    close_games_drawn: int = Field(default=0, ge=0)
    close_games_lost: int = Field(default=0, ge=0)
    
    # 1-0 / 0-1 games
    one_nil_wins: int = Field(default=0, ge=0)
    one_nil_losses: int = Field(default=0, ge=0)
    
    # Late winners/losers (but décisif après 80')
    late_winners: int = Field(default=0, ge=0)
    late_losers: int = Field(default=0, ge=0)
    
    @computed_field
    @property
    def close_game_win_rate(self) -> float:
        """Taux de victoire dans les matchs serrés."""
        if self.close_games_total == 0:
            return 50
        return round(self.close_games_won / self.close_games_total * 100, 1)
    
    @computed_field
    @property
    def close_game_luck(self) -> str:
        """
        Luck dans les matchs serrés.
        Win rate > 55% = chanceux (unsustainable)
        Win rate < 35% = malchanceux (value)
        """
        rate = self.close_game_win_rate
        if rate >= 60:
            return "VERY_LUCKY"
        elif rate >= 50:
            return "LUCKY"
        elif rate >= 40:
            return "NEUTRAL"
        elif rate >= 30:
            return "UNLUCKY"
        else:
            return "VERY_UNLUCKY"
    
    @computed_field
    @property
    def late_game_net(self) -> int:
        """Bilan net des buts décisifs tardifs."""
        return self.late_winners - self.late_losers
    
    @computed_field
    @property
    def close_game_regression_risk(self) -> str:
        """Risque de régression sur matchs serrés."""
        if self.close_game_win_rate >= 55 and self.close_games_total >= 5:
            return "HIGH"
        elif self.close_game_win_rate <= 35 and self.close_games_total >= 5:
            return "POSITIVE"  # Régression positive = value
        else:
            return "LOW"


# ═══════════════════════════════════════════════════════════════════════════════════════
# VARIANCE DNA - Classe principale
# ═══════════════════════════════════════════════════════════════════════════════════════

class VarianceDNA(QuantumBaseModel):
    """
    ADN de variance complet - Identifie chance/malchance et régression.
    
    USAGE BETTING:
    - variance_profile == UNLUCKY/EXTREMELY_UNLUCKY → VALUE (régression UP)
    - variance_profile == LUCKY/EXTREMELY_LUCKY → FADE (régression DOWN)
    """
    
    # Identité
    team_name: str
    team_normalized: str = ""
    league: str = ""
    season: str = "2024-2025"
    
    # Sub-components
    points: ExpectedPointsMetrics = Field(default_factory=ExpectedPointsMetrics)
    goals: GoalVarianceMetrics = Field(default_factory=GoalVarianceMetrics)
    conversion: ConversionVariance = Field(default_factory=ConversionVariance)
    close_games: CloseGamesMetrics = Field(default_factory=CloseGamesMetrics)
    
    # Metadata
    matches_analyzed: int = Field(default=0, ge=0)
    data_quality: DataQuality = Field(default=DataQuality.MODERATE)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    @computed_field
    @property
    def overall_variance_profile(self) -> VarianceProfile:
        """Profil de variance global."""
        return self.points.variance_profile
    
    @computed_field
    @property
    def composite_luck_score(self) -> float:
        """
        Score de chance composite (-100 à +100).
        Combine tous les facteurs de variance.
        """
        # Points luck (40%)
        points_luck = self.points.luck_index
        
        # Goal variance (30%)
        goal_luck = self.goals.total_goal_variance * 5
        
        # Close games (20%)
        close_luck = (self.close_games.close_game_win_rate - 45) * 2
        
        # Conversion (10%)
        conversion_luck = self.conversion.big_chance_luck * 5
        
        composite = (points_luck * 0.4 + goal_luck * 0.3 + 
                    close_luck * 0.2 + conversion_luck * 0.1)
        
        return round(max(-100, min(100, composite)), 1)
    
    @computed_field
    @property
    def regression_forecast(self) -> dict:
        """
        Prévision de régression.
        
        Returns:
            direction: UP/DOWN/STABLE
            confidence: 0-100
            timeframe: SHORT/MEDIUM/LONG
        """
        direction = self.points.regression_direction
        magnitude = self.points.regression_magnitude
        
        # Confidence basée sur magnitude et sample size
        confidence_base = {
            "STRONG": 75,
            "MODERATE": 55,
            "WEAK": 35,
        }.get(magnitude, 40)
        
        # Ajuster selon sample size
        if self.matches_analyzed >= 20:
            confidence_base += 15
        elif self.matches_analyzed >= 10:
            confidence_base += 5
        
        # Timeframe estimation
        if magnitude == "STRONG":
            timeframe = "SHORT"  # 3-5 matchs
        elif magnitude == "MODERATE":
            timeframe = "MEDIUM"  # 5-10 matchs
        else:
            timeframe = "LONG"  # 10+ matchs
        
        return {
            "direction": direction,
            "confidence": min(95, confidence_base),
            "timeframe": timeframe,
            "points_diff": self.points.points_diff,
        }
    
    @computed_field
    @property
    def betting_signal(self) -> str:
        """
        Signal de betting basé sur la variance.
        
        BUY: Équipe malchanceuse, value attendue
        SELL: Équipe chanceuse, fade
        HOLD: Pas de signal clair
        """
        profile = self.overall_variance_profile
        
        if profile in [VarianceProfile.EXTREMELY_UNLUCKY, VarianceProfile.UNLUCKY]:
            return "BUY"
        elif profile in [VarianceProfile.EXTREMELY_LUCKY, VarianceProfile.LUCKY]:
            return "SELL"
        else:
            return "HOLD"
    
    @computed_field
    @property
    def value_indicators(self) -> List[str]:
        """Indicateurs de value identifiés."""
        indicators = []
        
        # Points variance
        if self.points.points_diff < -4:
            indicators.append("UNDERPERFORMING_XPTS")
        
        # Offensive bad luck
        if self.goals.offensive_luck in ["UNLUCKY", "VERY_UNLUCKY"]:
            indicators.append("POOR_FINISHING_LUCK")
        
        # Defensive bad luck
        if self.goals.defensive_luck in ["UNLUCKY", "VERY_UNLUCKY"]:
            indicators.append("POOR_DEFENSIVE_LUCK")
        
        # Close games
        if self.close_games.close_game_luck in ["UNLUCKY", "VERY_UNLUCKY"]:
            indicators.append("CLOSE_GAME_BAD_LUCK")
        
        # Big chances
        if self.conversion.big_chance_luck < -2:
            indicators.append("MISSING_BIG_CHANCES")
        
        return indicators
    
    @computed_field
    @property
    def fade_indicators(self) -> List[str]:
        """Indicateurs de fade (surévaluation)."""
        indicators = []
        
        # Points variance
        if self.points.points_diff > 4:
            indicators.append("OVERPERFORMING_XPTS")
        
        # Offensive good luck
        if self.goals.offensive_luck in ["LUCKY", "VERY_LUCKY"]:
            indicators.append("GOOD_FINISHING_LUCK")
        
        # Defensive good luck
        if self.goals.defensive_luck in ["LUCKY", "VERY_LUCKY"]:
            indicators.append("GOOD_DEFENSIVE_LUCK")
        
        # Close games
        if self.close_games.close_game_luck in ["LUCKY", "VERY_LUCKY"]:
            indicators.append("CLOSE_GAME_GOOD_LUCK")
        
        # Big chances conversion
        if self.conversion.big_chance_luck > 2:
            indicators.append("OVERCONVERTING_BIG_CHANCES")
        
        return indicators
    
    @computed_field
    @property
    def market_adjustments(self) -> dict:
        """
        Ajustements suggérés pour les marchés.
        En points de probabilité.
        """
        luck = self.composite_luck_score
        
        # Base adjustment
        win_adjustment = -luck * 0.1  # Si chanceux, diminuer P(win)
        
        # Goals adjustments basés sur goal variance
        goals_luck = self.goals.total_goal_variance
        over_adjustment = -goals_luck * 2  # Si surperformance goals, diminuer Over
        
        return {
            "win_probability": round(win_adjustment, 1),
            "over_25_probability": round(over_adjustment, 1),
            "btts_probability": round(-luck * 0.05, 1),
        }
