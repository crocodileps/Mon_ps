"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                    QUANTUM FRICTION & CONTEXT MODELS                                  ║
║                                                                                       ║
║  Un match = COLLISION de deux ADN.                                                   ║
║  La friction tactique révèle les opportunités cachées.                               ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from datetime import datetime, date


# ═══════════════════════════════════════════════════════════════════════════════════════
# ENUMS - Classifications de Friction
# ═══════════════════════════════════════════════════════════════════════════════════════

class FrictionLevel(str, Enum):
    """Niveau de friction"""
    MINIMAL = "MINIMAL"      # < 20
    LOW = "LOW"              # 20-40
    MEDIUM = "MEDIUM"        # 40-60
    HIGH = "HIGH"            # 60-80
    EXTREME = "EXTREME"      # > 80


class DominanceType(str, Enum):
    """Type de dominance dans la friction"""
    HOME_DOMINANT = "HOME_DOMINANT"
    AWAY_DOMINANT = "AWAY_DOMINANT"
    BALANCED = "BALANCED"
    CHAOTIC = "CHAOTIC"  # Les deux se font mal


class ClashType(str, Enum):
    """Type de clash prédit"""
    OPEN_GAME = "OPEN_GAME"           # Beaucoup de buts attendus
    TIGHT_GAME = "TIGHT_GAME"         # Peu de buts attendus
    HOME_CONTROLLED = "HOME_CONTROLLED"
    AWAY_CONTROLLED = "AWAY_CONTROLLED"
    LATE_DRAMA = "LATE_DRAMA"         # Buts tardifs attendus
    EARLY_GOALS = "EARLY_GOALS"       # Buts précoces attendus
    UNPREDICTABLE = "UNPREDICTABLE"


# ═══════════════════════════════════════════════════════════════════════════════════════
# FRICTION COMPONENTS - Les 4 types de friction
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class KineticFriction:
    """
    Friction Kinétique: Dommage tactique que A peut infliger à B.
    Basé sur les axes tactiques et faiblesses.
    """
    home_to_away: float  # Dommage Home → Away (0-100)
    away_to_home: float  # Dommage Away → Home (0-100)
    
    total: float  # Somme des deux
    differential: float  # home_to_away - away_to_home
    
    # Triggers détectés
    triggers: List[str] = field(default_factory=list)
    # Ex: ["PRESSING_DEATH", "COUNTER_STAB", "AIR_RAID"]
    
    # Niveau de danger
    danger_level: FrictionLevel = FrictionLevel.MEDIUM
    
    # Dominance
    dominance: DominanceType = DominanceType.BALANCED
    
    @property
    def is_chaotic(self) -> bool:
        """Les deux équipes peuvent se faire mal"""
        return self.home_to_away > 50 and self.away_to_home > 50
    
    @property
    def is_one_sided(self) -> bool:
        """Une équipe domine clairement"""
        return abs(self.differential) > 30


@dataclass
class TemporalFriction:
    """
    Friction Temporelle: Avantage sur le timing du match.
    Basé sur diesel_factor, clutch, periods.
    """
    # Avantage par période
    first_half_advantage: str  # HOME, AWAY, NEUTRAL
    second_half_advantage: str
    
    # Avantage late game
    late_game_advantage: str  # HOME, AWAY, NEUTRAL
    late_game_score: float  # Différentiel de diesel + clutch
    
    # Prediction de timing des buts
    expected_goal_distribution: str  # EARLY, EVEN, LATE
    
    # Clash temporel
    periods_clash: List[str] = field(default_factory=list)
    # Ex: ["BOTH_STRONG_75_90", "HOME_WEAK_0_15"]
    
    # Marchés suggérés basés sur temporal
    suggested_temporal_markets: List[str] = field(default_factory=list)


@dataclass
class PsycheFriction:
    """
    Friction Psychologique: Avantage mental entre les équipes.
    Basé sur mentality, resilience, killer_instinct.
    """
    # Dominance psychologique
    psychological_dominance: str  # HOME, AWAY, NEUTRAL
    dominance_score: float  # 0-100
    
    # Facteurs contributifs
    resilience_gap: float
    killer_instinct_gap: float
    motivation_gap: float
    
    # Risques identifiés
    collapse_risk_team: Optional[str] = None  # HOME, AWAY, NEITHER
    choke_risk_team: Optional[str] = None
    
    # Avantage clutch
    clutch_advantage: str = "NEUTRAL"
    
    # Impact sur le match
    expected_psychological_impact: str = "MINIMAL"
    # MINIMAL, MODERATE, SIGNIFICANT, DECISIVE


@dataclass
class PhysicalFriction:
    """
    Friction Physique: Avantage d'endurance et de fraîcheur.
    Basé sur fatigue, pressing_decay, bench_impact.
    """
    # Avantage physique global
    physical_advantage: str  # HOME, AWAY, NEUTRAL
    physical_edge: float  # 0-100
    
    # Composants
    fatigue_gap: float  # Différentiel de fatigue (+ = Home plus frais)
    pressing_decay_gap: float
    bench_impact_gap: float
    
    # Prédiction d'effondrement
    expected_collapse_team: Optional[str] = None
    expected_collapse_minute: Optional[int] = None  # Quand l'effondrement est attendu
    
    # Late punishment potential
    late_punishment_potential_home: float = 0.0
    late_punishment_potential_away: float = 0.0
    
    # Marchés suggérés
    suggested_physical_markets: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════════════
# FRICTION MATRIX - Agrégation complète
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class FrictionMatrix:
    """
    Matrice de Friction complète entre deux équipes.
    
    "On parie sur des INTERACTIONS, pas sur des équipes."
    """
    # Identifiants
    home_team: str
    away_team: str
    home_team_id: int
    away_team_id: int
    
    # Les 4 types de friction
    kinetic: KineticFriction
    temporal: TemporalFriction
    psyche: PsycheFriction
    physical: PhysicalFriction
    
    # Score global
    total_friction: float  # 0-200 (somme des frictions)
    chaos_potential: float  # 0-100 (probabilité de match chaotique)
    
    # Clash prédit
    predicted_clash_type: ClashType
    
    # Scénarios détectés (liste des IDs)
    detected_scenarios: List[str] = field(default_factory=list)
    
    # Métadonnées
    calculated_at: datetime = field(default_factory=datetime.now)
    confidence: float = 0.7
    
    @property
    def is_high_friction(self) -> bool:
        """Match à haute friction (buts attendus)"""
        return self.total_friction > 100
    
    @property
    def is_low_friction(self) -> bool:
        """Match à basse friction (peu de buts)"""
        return self.total_friction < 60
    
    @property
    def is_chaotic(self) -> bool:
        """Match potentiellement chaotique"""
        return self.chaos_potential > 70
    
    @property
    def dominant_team(self) -> Optional[str]:
        """Équipe dominante si claire"""
        if self.kinetic.differential > 25:
            return self.home_team
        elif self.kinetic.differential < -25:
            return self.away_team
        return None
    
    def get_friction_summary(self) -> Dict[str, Any]:
        """Résumé de la friction pour affichage"""
        return {
            "total": self.total_friction,
            "chaos": self.chaos_potential,
            "kinetic_diff": self.kinetic.differential,
            "temporal_late_adv": self.temporal.late_game_advantage,
            "psyche_dom": self.psyche.psychological_dominance,
            "physical_adv": self.physical.physical_advantage,
            "clash_type": self.predicted_clash_type.value,
            "scenarios": self.detected_scenarios
        }


# ═══════════════════════════════════════════════════════════════════════════════════════
# MATCH CONTEXT - Contexte du match
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class TeamMatchContext:
    """Contexte spécifique à une équipe pour ce match"""
    # Repos et fatigue (obligatoires)
    rest_days: int
    european_week: bool
    
    # Position et enjeux (obligatoires)
    league_position: int
    points: int
    points_to_leader: int
    points_to_relegation: int
    
    # Forme (obligatoires)
    form_last_5: str  # Ex: "WWDLW"
    form_last_5_points: int
    momentum: str  # BLAZING, HOT, WARMING, NEUTRAL, COOLING, COLD
    
    # Séries (obligatoire)
    current_streak: int  # Positif = wins, négatif = losses
    
    # Optionnels avec defaults
    european_competition: Optional[str] = None  # UCL, UEL, UECL
    european_result: Optional[str] = None  # W, D, L
    home_streak: int = 0
    away_streak: int = 0
    
    # Blessures et suspensions
    injuries_count: int = 0
    key_players_out: List[str] = field(default_factory=list)
    suspensions: List[str] = field(default_factory=list)
    injury_impact: float = 0.0  # 0-100
    
    # Motivation
    motivation_zone: str = "MID_TABLE"  # TITLE, EUROPE, MID_TABLE, RELEGATION
    must_win: bool = False
    nothing_to_lose: bool = False
    
    # Historique contre cet adversaire
    h2h_wins: int = 0
    h2h_draws: int = 0
    h2h_losses: int = 0
    h2h_goals_for: int = 0
    h2h_goals_against: int = 0


@dataclass
class MatchContext:
    """
    Contexte complet du match.
    
    Barcelona vs Athletic en septembre ≠ Barcelona vs Athletic en mars.
    Un match à domicile ≠ un match à l'extérieur.
    """
    # Identifiants
    match_id: Optional[int] = None
    
    # Date et heure
    date: date = field(default_factory=date.today)
    kickoff_time: Optional[str] = None
    day_of_week: Optional[str] = None
    
    # Compétition
    league: str = ""
    league_id: Optional[int] = None
    competition_type: str = "LEAGUE"  # LEAGUE, CUP, EUROPEAN
    matchday: Optional[int] = None
    
    # Contexte des équipes
    home: Optional[TeamMatchContext] = None
    away: Optional[TeamMatchContext] = None
    
    # H2H global
    h2h_total_matches: int = 0
    h2h_avg_goals: float = 2.5
    h2h_btts_rate: float = 0.5
    h2h_over25_rate: float = 0.5
    h2h_home_win_rate: float = 0.4
    h2h_draw_rate: float = 0.2
    h2h_away_win_rate: float = 0.4
    last_h2h_result: Optional[str] = None  # Ex: "2-1 Home"
    
    # Conditions
    weather: Optional[str] = None  # CLEAR, RAIN, SNOW, EXTREME_HEAT
    temperature: Optional[float] = None
    
    # Importance du match
    importance_home: str = "NORMAL"  # LOW, NORMAL, HIGH, CRITICAL
    importance_away: str = "NORMAL"
    
    # Derby?
    is_derby: bool = False
    derby_intensity: str = "NORMAL"  # NORMAL, HIGH, EXTREME
    
    # Saison
    season_phase: str = "MID"  # EARLY, MID, LATE, FINAL
    
    # Gap de repos
    rest_days_gap: int = 0  # Positif = Home plus reposé
    
    # Gap de position
    position_gap: int = 0  # Positif = Home mieux classé
    
    @property
    def is_high_stakes(self) -> bool:
        """Match à enjeu élevé"""
        return (self.importance_home in ["HIGH", "CRITICAL"] or 
                self.importance_away in ["HIGH", "CRITICAL"])
    
    @property
    def fatigue_advantage(self) -> str:
        """Qui a l'avantage de repos"""
        if self.rest_days_gap > 1:
            return "HOME"
        elif self.rest_days_gap < -1:
            return "AWAY"
        return "NEUTRAL"
    
    @property
    def quality_advantage(self) -> str:
        """Qui a l'avantage de qualité (position)"""
        if self.position_gap > 5:
            return "HOME"
        elif self.position_gap < -5:
            return "AWAY"
        return "NEUTRAL"


# ═══════════════════════════════════════════════════════════════════════════════════════
# COMPOSITE INDICES - Les 3 indices ADCM
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class CompositeIndices:
    """
    Indices composites calculés pour une équipe.
    
    Ces indices sont notre avantage concurrentiel pour le ML.
    On n'entraîne pas sur "nombre de buts" mais sur ces métriques.
    """
    # Identifiant (obligatoire)
    team_name: str
    
    # Indices principaux (obligatoires)
    pace_factor: float  # 0-100
    control_index: float  # 0-100
    sniper_index: float  # 0-100
    
    # Indices dérivés (obligatoires)
    diesel_factor: float  # 0-1 (finit fort)
    clutch_factor: float  # 0-1 (performe dans moments critiques)
    
    # Indices de friction pré-calculés (obligatoires)
    offensive_threat: float  # 0-100
    defensive_solidity: float  # 0-100
    
    # Late game indices (obligatoires)
    late_game_threat: float  # 0-100
    late_game_vulnerability: float  # 0-100
    
    # Adaptability (obligatoire)
    chameleon_index: float  # 0-100 (capacité à changer de plan)
    
    # Optionnels avec defaults
    pace_components: Dict[str, float] = field(default_factory=dict)
    control_components: Dict[str, float] = field(default_factory=dict)
    sniper_components: Dict[str, float] = field(default_factory=dict)
    
    # Métadonnées
    calculated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def is_high_intensity(self) -> bool:
        return self.pace_factor > 70
    
    @property
    def is_possession_based(self) -> bool:
        return self.control_index > 70
    
    @property
    def is_clinical(self) -> bool:
        return self.sniper_index > 70


@dataclass
class MatchIndicesComparison:
    """
    Comparaison des indices entre deux équipes pour un match.
    """
    home_team: str
    away_team: str
    
    # Indices Home
    home_indices: CompositeIndices
    
    # Indices Away
    away_indices: CompositeIndices
    
    # Gaps calculés
    pace_factor_gap: float  # Home - Away
    control_gap: float
    sniper_gap: float
    diesel_gap: float
    clutch_gap: float
    
    # Indices combinés
    pace_factor_combined: float  # Home + Away
    control_combined: float
    sniper_combined: float
    
    # Prédictions basées sur les gaps
    expected_total_goals: float
    expected_dominance: str  # HOME, AWAY, BALANCED
    expected_late_drama: bool
    
    @property
    def is_high_tempo_expected(self) -> bool:
        """Match à rythme élevé attendu"""
        return self.pace_factor_combined > 140
    
    @property
    def is_sniper_duel(self) -> bool:
        """Duel de snipers attendu"""
        return (self.home_indices.sniper_index > 65 and 
                self.away_indices.sniper_index > 65)
    
    @property
    def is_attrition_expected(self) -> bool:
        """Match d'usure attendu"""
        return (self.pace_factor_combined < 100 and 
                self.control_combined > 120)


# ═══════════════════════════════════════════════════════════════════════════════════════
# DISCIPLINARY FRICTION - Friction Disciplinaire
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class DisciplinaryFriction:
    """
    Friction Disciplinaire entre deux équipes.
    Pour les paris sur les cartons.
    """
    home_team: str
    away_team: str
    
    # Scores d'agressivité
    aggression_home: float  # 0-100
    aggression_away: float
    
    # Scores de provocation
    provocation_home: float  # 0-100
    provocation_away: float
    
    # Friction croisée
    # Agressivité A × Provocation B + Agressivité B × Provocation A
    disciplinary_friction: float  # 0-100
    
    # Prédictions
    expected_total_cards: float
    expected_home_cards: float
    expected_away_cards: float
    red_card_probability: float
    
    # Seuils
    volatile_match: bool  # friction > 60
    cards_market_opportunity: bool  # friction > 50
    suggested_cards_line: float
    
    # Marchés suggérés
    suggested_markets: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════════════
# H2H ANALYSIS - Analyse Head to Head
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class H2HMatch:
    """Un match historique H2H"""
    date: date
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    result: str  # H, D, A
    competition: str
    
    @property
    def total_goals(self) -> int:
        return self.home_goals + self.away_goals
    
    @property
    def btts(self) -> bool:
        return self.home_goals > 0 and self.away_goals > 0


@dataclass
class H2HAnalysis:
    """
    Analyse complète des confrontations directes.
    """
    team_a: str
    team_b: str
    
    # Stats globales
    total_matches: int
    team_a_wins: int
    draws: int
    team_b_wins: int
    
    team_a_goals: int
    team_b_goals: int
    avg_goals_per_match: float
    
    # Taux
    team_a_win_rate: float
    draw_rate: float
    team_b_win_rate: float
    btts_rate: float
    over25_rate: float
    over35_rate: float
    
    # Stats Home/Away
    team_a_home_record: str  # Ex: "3W-1D-1L"
    team_a_away_record: str
    
    # Tendances récentes (5 derniers)
    recent_trend: str  # TEAM_A_DOMINANT, TEAM_B_DOMINANT, BALANCED
    recent_avg_goals: float
    recent_btts_rate: float
    
    # Historique détaillé
    matches: List[H2HMatch] = field(default_factory=list)
    
    # Patterns identifiés
    patterns: List[str] = field(default_factory=list)
    # Ex: ["HIGH_SCORING", "TEAM_A_LATE_GOALS", "LOW_FIRST_HALF"]
    
    @property
    def is_one_sided(self) -> bool:
        """Une équipe domine historiquement"""
        return abs(self.team_a_win_rate - self.team_b_win_rate) > 0.3
    
    @property
    def dominant_team(self) -> Optional[str]:
        """Équipe dominante dans le H2H"""
        if self.team_a_win_rate > self.team_b_win_rate + 0.2:
            return self.team_a
        elif self.team_b_win_rate > self.team_a_win_rate + 0.2:
            return self.team_b
        return None
    
    @property
    def is_high_scoring_fixture(self) -> bool:
        """Confrontation historiquement à buts"""
        return self.avg_goals_per_match > 2.8


# ═══════════════════════════════════════════════════════════════════════════════════════
# REFEREE PROFILE - Profil de l'arbitre (optionnel)
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class RefereeProfile:
    """
    Profil de l'arbitre pour ajuster les prédictions.
    """
    name: str
    
    # Stats générales
    matches_refereed: int
    avg_fouls_per_match: float
    avg_yellow_cards: float
    avg_red_cards: float
    
    # Tendances
    strictness: float  # 0-100 (100 = très strict)
    home_bias: float  # 0-1 (>0.5 = favorise domicile)
    
    # Impact sur les marchés
    cards_modifier: float  # Multiplicateur pour les cartons
    penalty_rate: float  # Pénaltys par match
    
    @property
    def is_strict(self) -> bool:
        return self.strictness > 70
    
    @property
    def is_lenient(self) -> bool:
        return self.strictness < 40
