"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                    QUANTUM DNA VECTORS - MON_PS TRADING SYSTEM                        ║
║                                                                                       ║
║  Les 9 vecteurs DNA qui définissent l'identité unique de chaque équipe.              ║
║  Chaque équipe = 1 ADN unique. Pas de catégories génériques.                         ║
║                                                                                       ║
║  "We don't bet on TEAMS. We bet on INTERACTIONS between DNA fingerprints."           ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════════════════════
# ENUMS - Classifications
# ═══════════════════════════════════════════════════════════════════════════════════════

class Mentality(str, Enum):
    """Mentalité de l'équipe - CONSERVATIVE = +11.73u/équipe (découverte clé)"""
    CONSERVATIVE = "CONSERVATIVE"
    BALANCED = "BALANCED"
    AGGRESSIVE = "AGGRESSIVE"
    CHAMELEON = "CHAMELEON"  # S'adapte selon le contexte


class KillerInstinct(str, Enum):
    """Niveau d'instinct tueur - LOW surperforme HIGH (contre-intuitif!)"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class KeeperStatus(str, Enum):
    """Statut du gardien - LEAKY = value par régression"""
    ELITE = "ELITE"
    SOLID = "SOLID"
    AVERAGE = "AVERAGE"
    LEAKY = "LEAKY"


class Formation(str, Enum):
    """Formation tactique - 4-3-3 = +8.08u (meilleure)"""
    F_4_3_3 = "4-3-3"
    F_4_4_2 = "4-4-2"
    F_4_2_3_1 = "4-2-3-1"
    F_3_5_2 = "3-5-2"
    F_3_4_3 = "3-4-3"
    F_5_3_2 = "5-3-2"
    F_4_1_4_1 = "4-1-4-1"
    F_4_5_1 = "4-5-1"
    OTHER = "OTHER"


class PlayingStyle(str, Enum):
    """Style de jeu principal"""
    POSSESSION = "POSSESSION"
    COUNTER_ATTACK = "COUNTER_ATTACK"
    HIGH_PRESS = "HIGH_PRESS"
    LOW_BLOCK = "LOW_BLOCK"
    DIRECT_PLAY = "DIRECT_PLAY"
    BALANCED = "BALANCED"
    TRANSITIONAL = "TRANSITIONAL"


class ScoringPeriod(str, Enum):
    """Période de scoring préférée"""
    EARLY = "0-15"
    FIRST_QUARTER = "15-30"
    PRE_HALF = "30-45"
    POST_HALF = "45-60"
    THIRD_QUARTER = "60-75"
    LATE = "75-90"


class MomentumTrend(str, Enum):
    """Tendance de momentum actuelle"""
    BLAZING = "BLAZING"      # 🔥 Win streak fort
    HOT = "HOT"              # 🌡️ Bonne forme
    WARMING = "WARMING"      # 📈 En progression
    NEUTRAL = "NEUTRAL"      # ➡️ Stable
    COOLING = "COOLING"      # 📉 En baisse
    COLD = "COLD"            # ❄️ Mauvaise forme


# ═══════════════════════════════════════════════════════════════════════════════════════
# VECTEUR 1: MARKET DNA - Performance par Marché
# Impact estimé: +20% ROI
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class MarketPerformance:
    """Performance sur un marché spécifique"""
    market: str
    roi: float
    win_rate: float
    n_bets: int
    profit: float
    avg_odds: float
    confidence: str = "MEDIUM"  # LOW, MEDIUM, HIGH, VERY_HIGH
    
    @property
    def is_profitable(self) -> bool:
        return self.roi > 0 and self.n_bets >= 5
    
    @property
    def is_significant(self) -> bool:
        return self.n_bets >= 10


@dataclass
class MarketDNA:
    """
    Vecteur 1: Market DNA
    Le marché le plus rentable pour CETTE équipe spécifique.
    """
    # Stratégie optimale validée
    best_strategy: str  # Ex: "CONVERGENCE_OVER_MC", "QUANT_BEST_MARKET"
    best_strategy_roi: float
    best_strategy_wr: float
    best_strategy_n: int
    best_strategy_edge: float
    best_strategy_profit: float
    
    # Stratégie secondaire
    second_strategy: Optional[str] = None
    second_strategy_roi: Optional[float] = None
    
    # Performance par marché
    market_performances: Dict[str, MarketPerformance] = field(default_factory=dict)
    
    # Listes de marchés
    best_markets: List[str] = field(default_factory=list)  # Top 3 marchés
    blacklisted_markets: List[str] = field(default_factory=list)  # Marchés à éviter
    
    # Conditions de déclenchement
    min_odds: float = 1.50
    max_odds: float = 3.00
    min_edge: float = 5.0
    min_diamond: int = 20
    optimal_odds_range: tuple = (1.65, 2.30)
    
    # Métadonnées
    last_validated: Optional[datetime] = None
    data_window: int = 20  # Nombre de matchs dans la fenêtre
    
    def get_market_roi(self, market: str) -> Optional[float]:
        """Récupère le ROI pour un marché donné"""
        if market in self.market_performances:
            return self.market_performances[market].roi
        return None
    
    def is_market_profitable(self, market: str) -> bool:
        """Vérifie si un marché est rentable pour cette équipe"""
        perf = self.market_performances.get(market)
        return perf is not None and perf.is_profitable


# ═══════════════════════════════════════════════════════════════════════════════════════
# VECTEUR 2: CONTEXT DNA - Performance Contextuelle
# Impact estimé: +12% ROI
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class LocationPerformance:
    """Performance à domicile ou à l'extérieur"""
    strength_index: float  # 0-100
    transformation_factor: float  # Multiplicateur vs baseline
    avg_goals_scored: float
    avg_goals_conceded: float
    clean_sheet_rate: float
    btts_rate: float
    over25_rate: float
    win_rate: float
    xg_for: float
    xg_against: float
    form_last_5: str = ""  # Ex: "WWDWW"


@dataclass
class SituationalPerformance:
    """Performance dans une situation spécifique"""
    win_rate: float
    roi: float
    avg_margin: float
    n_matches: int
    style_adjustment: Optional[str] = None
    confidence: str = "MEDIUM"


@dataclass
class ContextDNA:
    """
    Vecteur 2: Context DNA
    Comment l'équipe performe selon le contexte.
    """
    # Performance domicile/extérieur
    home: LocationPerformance
    away: LocationPerformance
    
    # Différentiel
    home_away_differential: float  # home_strength - away_strength
    home_beast: bool  # home_wr > 70% AND diff > 20
    away_fragile: bool  # away_wr < 35%
    
    # Performance situationnelle
    vs_top6: SituationalPerformance
    vs_mid_table: SituationalPerformance
    vs_bottom6: SituationalPerformance
    as_favorite: SituationalPerformance
    as_underdog: SituationalPerformance
    derby_matches: Optional[SituationalPerformance] = None
    
    # Sensibilité calendrier
    optimal_rest_days: int = 5
    fatigue_threshold_days: int = 3
    performance_drop_congestion: float = -0.15  # % drop si congestion
    european_week_penalty: float = -0.12
    post_international_break: float = -0.05
    
    # Sensibilité météo (optionnel)
    rain_performance_modifier: float = 0.0
    cold_performance_modifier: float = 0.0
    heat_performance_modifier: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════════════
# VECTEUR 3: RISK DNA - Volatilité et Gestion du Risque
# Impact estimé: +5% ROI (CRITIQUE pour money management)
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class VarianceMetrics:
    """Métriques de variance"""
    overall_variance: float  # 0-1
    offensive_variance: float
    defensive_variance: float
    result_variance: float
    goals_std_dev: float


@dataclass
class UpsetProfile:
    """Profil de surprises"""
    upset_as_favorite: float  # Taux de défaites en favori
    upset_as_underdog: float  # Taux de victoires en outsider
    upset_at_home: float
    upset_away: float
    giant_killer_index: float  # 0-100
    bottle_index: float  # 0-100 (tendance à craquer)


@dataclass
class StreakAnalysis:
    """Analyse des séries"""
    max_win_streak_season: int
    max_lose_streak_season: int
    avg_win_streak: float
    avg_lose_streak: float
    current_streak: int  # Positif = wins, négatif = losses
    current_momentum: MomentumTrend
    streak_volatility: float  # 0-1


@dataclass
class RiskDNA:
    """
    Vecteur 3: Risk DNA
    Quantifie l'imprévisibilité et ajuste les mises.
    """
    # Variance
    variance: VarianceMetrics
    
    # Prévisibilité
    result_predictability: float  # 0-1 (1 = très prévisible)
    score_predictability: float
    total_goals_predictability: float
    consistency_index: float  # 0-100
    
    # Profil de surprises
    upset_profile: UpsetProfile
    
    # Analyse des séries
    streak: StreakAnalysis
    
    # Événements rares
    five_plus_goals_rate: float  # Matchs avec 5+ buts
    zero_zero_rate: float
    red_card_rate: float
    penalty_rate: float
    
    # Recommandations de mise
    stake_modifier: float  # 0.5-1.5
    max_stake_tier: str  # TIER_1, TIER_2, TIER_3
    avoid_parlays: bool
    kelly_fraction: float  # Fraction Kelly recommandée
    reasoning: str = ""


# ═══════════════════════════════════════════════════════════════════════════════════════
# VECTEUR 4: TEMPORAL DNA - Patterns par Tranche de 15min ⭐
# Impact estimé: +25% ROI - DIFFÉRENCIANT MAJEUR
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class PeriodStats:
    """Stats pour une période de 15 minutes"""
    xg: float
    goals: float
    shots: float
    big_chances: float
    intensity: str  # LOW, MEDIUM, HIGH, CLUTCH
    conversion_rate: float


@dataclass
class HalfStats:
    """Stats pour une mi-temps"""
    xg_for: float
    xg_against: float
    goals_for: float
    goals_against: float
    dominance_index: float  # 0-100


@dataclass
class TemporalMarketOpportunity:
    """Opportunité de marché temporel"""
    market: str
    selection: str
    edge: float
    confidence: str
    n_bets: int
    historical_roi: float


@dataclass
class TemporalDNA:
    """
    Vecteur 4: Temporal DNA (Chronos)
    Quand l'équipe marque et encaisse. Permet les paris temporels.
    """
    # Patterns de scoring par période
    scoring_0_15: PeriodStats
    scoring_15_30: PeriodStats
    scoring_30_45: PeriodStats
    scoring_45_60: PeriodStats
    scoring_60_75: PeriodStats
    scoring_75_90: PeriodStats
    
    # Patterns de concession par période
    conceding_0_15: PeriodStats
    conceding_15_30: PeriodStats
    conceding_30_45: PeriodStats
    conceding_45_60: PeriodStats
    conceding_60_75: PeriodStats
    conceding_75_90: PeriodStats
    
    # Analyse par mi-temps
    first_half: HalfStats
    second_half: HalfStats
    
    # Insights dérivés
    diesel_factor: float  # 0-1 (1 = finit très fort)
    sprinter_factor: float  # 0-1 (1 = commence très fort)
    clutch_factor: float  # 0-1 (capacité à scorer moments critiques)
    
    first_half_team: bool
    second_half_team: bool
    late_game_killer: bool
    early_starter: bool
    early_collapse_risk: bool
    late_collapse_risk: bool
    
    fatigue_sensitivity: float  # 0-1
    momentum_builder: bool  # Construit l'avantage progressivement
    
    # Meilleure période
    best_scoring_period: ScoringPeriod
    worst_defensive_period: ScoringPeriod
    
    # Déclin physique (PPDA par période)
    ppda_0_30: Optional[float] = None
    ppda_30_60: Optional[float] = None
    ppda_60_90: Optional[float] = None
    pressing_decay_rate: float = 0.0  # % de déclin du pressing
    intensity_sustainability: float = 0.5  # 0-1
    
    # Opportunités de marchés temporels
    best_temporal_markets: List[TemporalMarketOpportunity] = field(default_factory=list)
    avoid_temporal_markets: List[str] = field(default_factory=list)
    
    def get_period_xg(self, period: ScoringPeriod) -> float:
        """Récupère le xG pour une période donnée"""
        period_map = {
            ScoringPeriod.EARLY: self.scoring_0_15,
            ScoringPeriod.FIRST_QUARTER: self.scoring_15_30,
            ScoringPeriod.PRE_HALF: self.scoring_30_45,
            ScoringPeriod.POST_HALF: self.scoring_45_60,
            ScoringPeriod.THIRD_QUARTER: self.scoring_60_75,
            ScoringPeriod.LATE: self.scoring_75_90,
        }
        return period_map.get(period, self.scoring_75_90).xg


# ═══════════════════════════════════════════════════════════════════════════════════════
# VECTEUR 5: NEMESIS DNA - Friction Tactique ⭐⭐ GAME CHANGER
# Impact estimé: +35% ROI - LE CŒUR DU SYSTÈME
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class TacticalAxis:
    """Un axe tactique avec score et détails"""
    score: float  # 0-100
    description: str
    raw_value: Optional[float] = None


@dataclass
class TacticalWeakness:
    """Faiblesse tactique exploitable"""
    weakness_type: str  # vs_high_press, vs_aerial, vs_low_block, vs_counter, vs_pace
    vulnerability: float  # 0-1
    n_matches: int
    goals_conceded_avg: float
    trigger_condition: str  # Condition qui déclenche la faiblesse
    markets_affected: List[str] = field(default_factory=list)


@dataclass
class TacticalStrength:
    """Force tactique"""
    strength_type: str
    edge: float  # 0-1
    n_matches: int
    win_rate: float
    avg_margin: float
    exploitation: str  # Comment on exploite cette force


@dataclass
class SpecificMatchup:
    """Matchup spécifique contre une équipe"""
    team: str
    h2h_record: str  # Ex: "3W-1D-2L"
    reason: str
    recommended_action: str  # INCREASE, REDUCE, AVOID, CONFIDENT


@dataclass
class NemesisDNA:
    """
    Vecteur 5: Nemesis DNA (Friction Tactique)
    Identifie les faiblesses structurelles exploitables.
    """
    # Profil tactique (obligatoires)
    style_primary: PlayingStyle
    formation_typical: Formation
    
    # Identité de jeu (obligatoires)
    possession_avg: float
    direct_play_index: float  # 0-100
    tempo: str  # SLOW, MEDIUM, FAST, VARIABLE
    risk_taking: str  # LOW, MEDIUM, HIGH
    
    # 8 Axes Tactiques (obligatoires)
    verticality: TacticalAxis  # Ratio passes vers l'avant
    width_preference: TacticalAxis  # Préférence flancs vs centre
    pressing_intensity: TacticalAxis  # PPDA
    engagement_line: TacticalAxis  # Hauteur de la ligne défensive
    build_up_speed: TacticalAxis  # Vitesse de construction
    set_piece_reliance: TacticalAxis  # Dépendance coups de pied arrêtés
    transition_speed: TacticalAxis  # Vitesse de transition
    defensive_structure: TacticalAxis  # Compacité défensive
    
    # Optionnels avec defaults
    style_secondary: Optional[PlayingStyle] = None
    style_confidence: float = 0.7
    formation_variants: List[Formation] = field(default_factory=list)
    
    # Faiblesses structurelles
    weaknesses: List[TacticalWeakness] = field(default_factory=list)
    
    # Forces exploitables
    strengths: List[TacticalStrength] = field(default_factory=list)
    
    # Nemesis spécifiques (équipes problématiques)
    specific_nemesis: List[SpecificMatchup] = field(default_factory=list)
    
    # Proies spécifiques (équipes faciles)
    specific_prey: List[SpecificMatchup] = field(default_factory=list)
    
    def get_weakness_vs(self, weakness_type: str) -> Optional[TacticalWeakness]:
        """Récupère une faiblesse spécifique"""
        for w in self.weaknesses:
            if w.weakness_type == weakness_type:
                return w
        return None
    
    def has_nemesis(self, team_name: str) -> bool:
        """Vérifie si une équipe est un nemesis"""
        return any(n.team.lower() == team_name.lower() for n in self.specific_nemesis)
    
    def has_prey(self, team_name: str) -> bool:
        """Vérifie si une équipe est une proie"""
        return any(p.team.lower() == team_name.lower() for p in self.specific_prey)


# ═══════════════════════════════════════════════════════════════════════════════════════
# VECTEUR 6: PSYCHE DNA - Profil Psychologique
# Impact estimé: +15% ROI
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class GameStateBehavior:
    """Comportement dans un game state spécifique"""
    style: str  # CONTROL, ATTACK, DESPERATE_ATTACK, DEFENSIVE
    xg_change: float  # Changement de xG vs baseline
    possession_change: float
    pressing_intensity_change: float
    tactical_discipline: float  # 0-1
    risk_change: float


@dataclass
class ClutchPerformance:
    """Performance dans les moments critiques"""
    clutch_index: float  # 0-100
    last_10_min_goals: float  # Moyenne
    last_10_min_xg: float
    big_chance_conversion_late: float
    composure_under_pressure: float  # 0-100


@dataclass
class MomentumPsychology:
    """Psychologie du momentum"""
    win_after_win_rate: float
    lose_after_lose_rate: float
    bounce_back_rate: float
    momentum_sensitivity: float  # 0-1 (1 = très sensible au momentum)
    streak_dependent: bool


@dataclass
class PsycheDNA:
    """
    Vecteur 6: Psyche DNA
    Comment l'équipe réagit à l'adversité.
    """
    # Profil de résilience
    resilience_index: float  # 0-100
    comeback_rate: float  # Taux de remontée au score
    points_when_trailing_first: float  # Points moyens quand mené
    collapse_rate: float  # Taux d'effondrement
    mental_strength_tier: str  # WEAK, AVERAGE, STRONG, ELITE
    
    # Mentalité générale
    mentality: Mentality
    killer_instinct: KillerInstinct
    killer_instinct_score: float  # 0-1
    
    # Comportement par game state
    when_winning: GameStateBehavior
    when_drawing: GameStateBehavior
    when_losing: GameStateBehavior
    
    # Performance clutch
    clutch: ClutchPerformance
    
    # Gestion de la pression
    big_game_performance: float  # 0-1
    vs_top6_win_rate: float
    must_win_games_wr: float
    nothing_to_lose_wr: float
    
    # Psychologie du momentum
    momentum: MomentumPsychology
    
    # Facteur crowd
    home_crowd_boost: float
    hostile_away_impact: float
    
    # Motivation actuelle
    motivation_index: float  # 0-100
    motivation_zone: str  # TITLE_RACE, EUROPE_RACE, MID_TABLE, RELEGATION
    position_security: bool
    cup_competition_active: bool
    calculated_urgency: float  # 0-100


# ═══════════════════════════════════════════════════════════════════════════════════════
# VECTEUR 7: SENTIMENT DNA - Biais de Marché
# Impact estimé: +8% ROI
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class ValueZone:
    """Zone de valeur identifiée"""
    situation: str
    avg_edge: float
    n_matches: int
    historical_roi: float


@dataclass
class CLVTrackRecord:
    """Historique de CLV"""
    avg_clv: float
    positive_clv_rate: float
    clv_by_market: Dict[str, float] = field(default_factory=dict)
    clv_trend: str = "STABLE"  # IMPROVING, STABLE, DECLINING
    clv_consistency: float = 0.5


@dataclass
class SentimentDNA:
    """
    Vecteur 7: Sentiment DNA
    Mesure si l'équipe est surcotée ou sous-cotée.
    """
    # Perception du marché (obligatoires)
    public_team: bool  # Équipe populaire
    brand_value_tier: str  # ELITE, HIGH, MEDIUM, LOW
    media_coverage: str  # VERY_HIGH, HIGH, MEDIUM, LOW
    casual_bettor_favorite: bool
    brand_premium: float  # Prime de marque dans les cotes
    
    # Track record CLV
    clv: CLVTrackRecord
    
    # Alignement avec sharp money (obligatoires)
    follows_sharp_money: float  # 0-1
    steam_move_correlation: float
    pinnacle_vs_soft_edge: float
    
    # Zones de valeur (optionnels)
    undervalued_situations: List[ValueZone] = field(default_factory=list)
    overvalued_situations: List[ValueZone] = field(default_factory=list)
    
    # Biais par marché
    undervalued_markets: List[str] = field(default_factory=list)
    overvalued_markets: List[str] = field(default_factory=list)
    
    # Opportunités contrariantes
    fade_when_heavy_favorite: bool = False
    back_when_heavy_underdog: bool = False
    optimal_contrarian_odds: tuple = (3.50, 6.00)
    contrarian_roi: float = 0.0
    contrarian_sample: int = 0
    
    # Timing optimal
    early_value_window_hours: int = 48
    early_value_edge: float = 0.0
    late_value_edge: float = 0.0
    optimal_bet_timing: str = "24-48h before kickoff"


# ═══════════════════════════════════════════════════════════════════════════════════════
# VECTEUR 8: ROSTER DNA - Composition d'Équipe
# Impact estimé: +10% ROI
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class RosterDNA:
    """
    Vecteur 8: Roster DNA
    Composition et dépendances de l'équipe.
    """
    # Dépendance MVP
    mvp_name: Optional[str] = None
    mvp_dependency: float = 0.0  # 0-1 (1 = très dépendant)
    mvp_goals_pct: float = 0.0  # % des buts marqués par le MVP
    mvp_assists_pct: float = 0.0
    performance_without_mvp: float = 0.0  # % de performance sans MVP
    
    # Impact du banc
    bench_impact: float = 5.0  # Score 0-10
    bench_goals_pct: float = 0.0  # % des buts par les remplaçants
    avg_sub_impact: float = 0.0  # Impact moyen des entrées
    late_sub_goals: float = 0.0  # Buts des subs après 70'
    
    # Profondeur d'effectif
    squad_depth_score: float = 50.0  # 0-100
    injury_resilience: float = 0.5  # 0-1
    rotation_capability: float = 0.5  # 0-1
    
    # Keeper
    keeper_status: KeeperStatus = KeeperStatus.AVERAGE
    keeper_save_rate: float = 0.70
    keeper_xg_prevented: float = 0.0  # xG sauvés vs attendus
    keeper_distribution: str = "AVERAGE"  # POOR, AVERAGE, GOOD, ELITE
    
    # Attaque
    striker_clinical: float = 0.0  # Conversion rate vs xG
    creative_hub_dependency: float = 0.0  # Dépendance au créateur
    aerial_threat_forwards: float = 50.0  # 0-100
    
    # Défense
    defense_aerial_ability: float = 50.0  # 0-100
    fullback_offensive: float = 50.0  # Contribution offensive des latéraux
    center_back_passing: float = 50.0  # Qualité de relance
    
    # Blessures actuelles (dynamique)
    current_injuries: int = 0
    key_players_injured: List[str] = field(default_factory=list)
    injury_impact_score: float = 0.0  # 0-100


# ═══════════════════════════════════════════════════════════════════════════════════════
# VECTEUR 9: PHYSICAL DNA - Profil Physique
# Impact estimé: +12% ROI
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class PhysicalDNA:
    """
    Vecteur 9: Physical DNA
    Le foot est physique. Une équipe fatiguée ne tient pas 90 minutes.
    """
    # Pressing et intensité
    pressing_intensity: float = 50.0  # 0-100
    ppda_avg: float = 10.0  # Passes adverses par action défensive
    high_press_triggers_per_match: float = 5.0
    counter_press_success: float = 0.40
    
    # Déclin physique (CRITIQUE)
    pressing_decay: float = 0.15  # % de déclin du pressing sur 90min
    intensity_60_plus: float = 0.7  # % d'intensité après 60'
    intensity_75_plus: float = 0.5  # % d'intensité après 75'
    
    # Endurance
    distance_covered_avg: float = 110.0  # km
    sprints_per_match: float = 100.0
    high_intensity_runs: float = 50.0
    
    # Impact fatigue
    late_game_threat: str = "MEDIUM"  # LOW, MEDIUM, HIGH
    late_game_vulnerability: str = "MEDIUM"
    
    # Récupération
    optimal_rest_days: int = 5
    short_rest_penalty: float = -0.10  # % performance si repos < 4j
    congestion_tolerance: float = 0.5  # 0-1
    
    # Agilité et vitesse
    team_pace_rating: float = 50.0  # 0-100
    counter_attack_speed: float = 50.0
    defensive_recovery_speed: float = 50.0
    
    # Physicalité
    duels_won_rate: float = 0.50
    aerial_duels_won_rate: float = 0.50
    tackles_per_match: float = 15.0
    fouls_committed: float = 12.0
    fouls_won: float = 10.0


# ═══════════════════════════════════════════════════════════════════════════════════════
# VECTEUR 10: LUCK DNA - Facteur Chance
# Impact estimé: +8% ROI (régression à la moyenne)
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class LuckDNA:
    """
    Vecteur 10: Luck DNA
    Mesure la chance/malchance d'une équipe pour anticiper la régression.
    
    xPoints > Points réels = Malchance (value à venir)
    xPoints < Points réels = Chance (régression négative à venir)
    """
    # xPoints vs Points réels (obligatoires)
    xpoints: float  # Points attendus selon xG
    actual_points: float
    xpoints_delta: float  # xpoints - actual_points (+ = malchanceux)
    
    # Profil de chance (obligatoires)
    luck_profile: str  # VERY_LUCKY, LUCKY, NEUTRAL, UNLUCKY, VERY_UNLUCKY
    luck_index: float  # -100 à +100 (+ = malchanceux = value)
    
    # Composants (obligatoires)
    xg_overperformance: float  # Goals - xG (+ = surperforme)
    xga_overperformance: float  # Goals Against - xGA (+ = défense surperforme)
    
    # Conversion (obligatoires)
    big_chances_conversion: float  # % de grosses occasions converties
    big_chances_faced_conversion: float  # % de grosses occasions adverses converties
    expected_conversion: float  # Conversion attendue
    conversion_luck: float  # Différentiel
    
    # Régression attendue (obligatoires)
    regression_direction: str  # UP, DOWN, STABLE
    regression_magnitude: float  # 0-100
    
    # Clean sheets (obligatoire)
    clean_sheet_luck: float  # CS réels - CS attendus
    
    # Optionnels avec defaults
    regression_markets: List[str] = field(default_factory=list)
    penalties_for: int = 0
    penalties_against: int = 0
    penalty_luck: float = 0.0  # Différentiel vs attendu
    
    @property
    def is_due_for_regression_up(self) -> bool:
        """Régression positive attendue (malchanceux)"""
        return self.xpoints_delta > 3 and self.luck_profile in ["UNLUCKY", "VERY_UNLUCKY"]
    
    @property
    def is_due_for_regression_down(self) -> bool:
        """Régression négative attendue (chanceux)"""
        return self.xpoints_delta < -3 and self.luck_profile in ["LUCKY", "VERY_LUCKY"]


# ═══════════════════════════════════════════════════════════════════════════════════════
# VECTEUR 11: CHAMELEON DNA - Adaptabilité
# Impact estimé: +10% ROI
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class ChameleonDNA:
    """
    Vecteur 11: Chameleon DNA
    Capacité d'adaptation tactique et mentale.
    
    Une équipe caméléon peut changer de plan de jeu selon l'adversaire.
    """
    # Adaptabilité globale (obligatoires)
    adaptability_index: float  # 0-100
    chameleon_score: float  # 0-100
    
    # Capacité de comeback (obligatoires)
    comeback_ability: float  # 0-100
    points_from_losing_positions: float
    comeback_rate: float  # % de matchs où revient au score
    
    # Flexibilité tactique (obligatoires)
    tactical_flexibility: float  # 0-100
    formations_used: int  # Nombre de formations différentes
    primary_formation: str
    
    # Adaptation au contexte (obligatoires)
    vs_stronger_adaptation: float  # 0-100 (comment joue vs meilleurs)
    vs_weaker_adaptation: float  # 0-100 (comment joue vs moins bons)
    
    # Réaction au score (obligatoires)
    style_when_leading: str  # CONTROL, DEFEND, ATTACK
    style_when_trailing: str
    style_when_drawing: str
    
    # Adaptation in-game (obligatoires)
    halftime_adjustment_success: float  # 0-100
    second_half_improvement: float  # Différentiel 2H vs 1H
    
    # Résistance aux plans adverses (obligatoires)
    anti_pressing_ability: float  # 0-100
    anti_counter_ability: float  # 0-100
    anti_low_block_ability: float  # 0-100
    
    # Optionnel
    secondary_formation: Optional[str] = None
    
    @property
    def is_true_chameleon(self) -> bool:
        """Vraie équipe caméléon"""
        return self.chameleon_score > 70 and self.tactical_flexibility > 65
    
    @property
    def is_one_dimensional(self) -> bool:
        """Équipe unidimensionnelle"""
        return self.chameleon_score < 40


# ═══════════════════════════════════════════════════════════════════════════════════════
# CURRENT SEASON DNA - État actuel de la saison
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class CurrentSeasonDNA:
    """
    Stats de la saison en cours.
    Rolling window dynamique.
    """
    # Identifiants
    season: str  # Ex: "2024-2025"
    league: str
    matches_played: int
    
    # Position et points
    position: int
    points: int
    points_per_match: float
    
    # Buts
    goals_for: int
    goals_against: int
    goal_difference: int
    goals_per_match: float
    goals_conceded_per_match: float
    
    # xG
    xg_for: float
    xg_against: float
    xg_difference: float
    xg_per_match: float
    xg_against_per_match: float
    xg_overperformance: float  # Goals - xG
    
    # Résultats
    wins: int
    draws: int
    losses: int
    win_rate: float
    
    # Forme récente
    form_last_5: str  # Ex: "WWDLW"
    form_last_5_points: int
    form_last_10_points: int
    
    # Stats détaillées
    shots_per_match: float = 0.0
    shots_on_target_per_match: float = 0.0
    possession_avg: float = 50.0
    pass_accuracy: float = 80.0
    corners_per_match: float = 5.0
    dangerous_attacks: float = 40.0
    
    # Clean sheets et BTTS
    clean_sheets: int = 0
    clean_sheet_rate: float = 0.0
    btts_rate: float = 0.50
    over25_rate: float = 0.50
    over35_rate: float = 0.25
    
    # Big chances
    big_chances_created: float = 0.0
    big_chances_missed: float = 0.0
    big_chances_faced: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════════════
# TEAM DNA COMPLET - Agrégation des 9 vecteurs
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class TeamDNA:
    """
    DNA complet d'une équipe - Agrégation des 11 vecteurs.
    
    "1 Team = 1 Unique Strategy. Generic approaches are for amateurs."
    
    Les 11 vecteurs (Phase 1 Quantum):
    1. context_dna - xG 2024, style
    2. current_season - xG 2025/2026, points, ppg
    3. psyche_dna - killer_instinct, mentality_profile
    4. nemesis_dna - verticality, keeper_status
    5. temporal_dna - diesel_factor, periods
    6. tactical_dna - formation, set_piece (dans nemesis pour simplifier)
    7. roster_dna - mvp_dependency, playmaker
    8. physical_dna - stamina, pressing, rotation
    9. market_dna - empirical_profile
    10. luck_dna - xpoints_delta, luck_profile
    11. chameleon_dna - comeback_ability, adaptability
    """
    # Identifiants
    team_id: int
    team_name: str
    team_name_normalized: str  # Nom normalisé pour matching
    league: str
    country: str
    
    # Les 11 Vecteurs DNA (obligatoires en production, optionnels pour tests)
    # Vecteur 1: Context DNA
    context: Optional[ContextDNA] = None
    
    # Vecteur 2: Current Season DNA
    current_season: Optional[CurrentSeasonDNA] = None
    
    # Vecteur 3: Psyche DNA
    psyche: Optional[PsycheDNA] = None
    
    # Vecteur 4: Nemesis DNA (inclut tactical pour simplifier)
    nemesis: Optional[NemesisDNA] = None
    
    # Vecteur 5: Temporal DNA
    temporal: Optional[TemporalDNA] = None
    
    # Vecteur 6: Roster DNA
    roster: Optional[RosterDNA] = None
    
    # Vecteur 7: Physical DNA
    physical: Optional[PhysicalDNA] = None
    
    # Vecteur 8: Market DNA
    market: Optional[MarketDNA] = None
    
    # Vecteur 9: Luck DNA
    luck: Optional[LuckDNA] = None
    
    # Vecteur 10: Chameleon DNA
    chameleon: Optional[ChameleonDNA] = None
    
    # Vecteurs supplémentaires (optionnels, pour enrichissement futur)
    risk: Optional[RiskDNA] = None
    sentiment: Optional[SentimentDNA] = None
    
    # Métadonnées
    last_updated: datetime = field(default_factory=datetime.now)
    data_quality_score: float = 0.0  # 0-100
    confidence_level: str = "MEDIUM"  # LOW, MEDIUM, HIGH, ELITE
    
    # Cache des calculs
    _composite_indices: Optional[Dict[str, float]] = field(default=None, repr=False)
    
    @property
    def is_elite(self) -> bool:
        """Vérifie si l'équipe a un profil ELITE"""
        return self.confidence_level == "ELITE" and self.data_quality_score > 80
    
    @property
    def best_strategy(self) -> Optional[str]:
        """Stratégie optimale de l'équipe"""
        return self.market.best_strategy if self.market else None
    
    @property
    def is_home_beast(self) -> bool:
        """L'équipe est-elle dominante à domicile?"""
        return self.context.home_beast if self.context else False
    
    @property
    def is_diesel(self) -> bool:
        """L'équipe finit-elle fort?"""
        return self.temporal.diesel_factor > 0.65 if self.temporal else False
    
    @property
    def is_clutch(self) -> bool:
        """L'équipe est-elle performante dans les moments critiques?"""
        if not self.temporal or not self.psyche:
            return False
        clutch_temporal = self.temporal.clutch_factor > 0.7
        clutch_psyche = self.psyche.clutch and self.psyche.clutch.clutch_index > 70
        return clutch_temporal and clutch_psyche
    
    @property
    def is_high_variance(self) -> bool:
        """L'équipe est-elle imprévisible?"""
        return self.risk.variance.overall_variance > 0.7 if self.risk else False
    
    @property
    def is_public_team(self) -> bool:
        """L'équipe est-elle populaire (potentiellement surcotée)?"""
        return self.sentiment.public_team if self.sentiment else False
    
    @property
    def is_lucky(self) -> bool:
        """L'équipe surperforme-t-elle ses xG? (régression négative à venir)"""
        return self.luck.is_due_for_regression_down if self.luck else False
    
    @property
    def is_unlucky(self) -> bool:
        """L'équipe sous-performe-t-elle ses xG? (régression positive = value)"""
        return self.luck.is_due_for_regression_up if self.luck else False
    
    @property
    def is_chameleon(self) -> bool:
        """L'équipe est-elle adaptable tactiquement?"""
        return self.chameleon.is_true_chameleon if self.chameleon else False
    
    def get_weakness_vulnerability(self, weakness_type: str) -> float:
        """Récupère le niveau de vulnérabilité pour une faiblesse"""
        if not self.nemesis:
            return 0.3
        weakness = self.nemesis.get_weakness_vs(weakness_type)
        return weakness.vulnerability if weakness else 0.3
    
    def calculate_fatigue_factor(self, rest_days: int, european_week: bool) -> float:
        """Calcule le facteur de fatigue actuel"""
        if not self.physical:
            return 0.0
            
        base_fatigue = 0.0
        
        if rest_days < self.physical.optimal_rest_days:
            base_fatigue += (self.physical.optimal_rest_days - rest_days) * 0.05
        
        if european_week:
            base_fatigue += 0.15
        
        # Ajustement selon le profil physique
        base_fatigue *= (1 + self.physical.pressing_decay)
        
        return min(1.0, base_fatigue)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour serialization"""
        from dataclasses import asdict
        return asdict(self)
    
    def __repr__(self) -> str:
        strat = self.best_strategy or "N/A"
        return f"TeamDNA({self.team_name}, strategy={strat}, confidence={self.confidence_level})"
