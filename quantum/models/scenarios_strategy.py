"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                    QUANTUM SCENARIOS & STRATEGY OUTPUT                               ║
║                                                                                       ║
║  20 scénarios identifiés par le système.                                             ║
║  Output final: QuantumStrategy avec recommandations de paris.                        ║
║  Modifié: 2025-12-19 - Migration vers market_registry                               ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
from datetime import datetime

# === IMPORT DEPUIS MARKET_REGISTRY (Source Unique de Vérité) ===
from quantum.models.market_registry import MarketType


# ═══════════════════════════════════════════════════════════════════════════════════════
# ENUMS - Types de Scénarios et Marchés
# ═══════════════════════════════════════════════════════════════════════════════════════

class ScenarioCategory(str, Enum):
    """Catégorie de scénario"""
    TACTICAL = "TACTICAL"           # Basé sur les styles de jeu
    TEMPORAL = "TEMPORAL"           # Basé sur le timing
    PHYSICAL = "PHYSICAL"           # Basé sur la condition physique
    PSYCHOLOGICAL = "PSYCHOLOGICAL"  # Basé sur le mental
    NEMESIS = "NEMESIS"             # Basé sur les matchups historiques


class ScenarioID(str, Enum):
    """
    Les 20 Scénarios Quantum.
    Chaque scénario a des conditions spécifiques et des marchés associés.
    """
    # Groupe A: Tactiques (5)
    TOTAL_CHAOS = "TOTAL_CHAOS"           # 🌪️ Festival de buts
    THE_SIEGE = "THE_SIEGE"               # 🏰 Domination stérile
    SNIPER_DUEL = "SNIPER_DUEL"           # 🔫 Létalité maximale
    ATTRITION_WAR = "ATTRITION_WAR"       # 💤 Guerre d'usure
    GLASS_CANNON = "GLASS_CANNON"         # 🃏 Canon de verre
    
    # Groupe B: Temporels (4)
    LATE_PUNISHMENT = "LATE_PUNISHMENT"   # ⏰ Punition tardive
    EXPLOSIVE_START = "EXPLOSIVE_START"   # 🚀 Départ fulgurant
    DIESEL_DUEL = "DIESEL_DUEL"           # 🐢 Deux diesels
    CLUTCH_KILLER = "CLUTCH_KILLER"       # ⚡ Tueur des fins de match
    
    # Groupe C: Physiques (4)
    FATIGUE_COLLAPSE = "FATIGUE_COLLAPSE" # 😰 Effondrement physique
    PRESSING_DEATH = "PRESSING_DEATH"     # 💪 Mort par pressing
    PACE_EXPLOITATION = "PACE_EXPLOITATION"  # 🏃 Exploitation vitesse
    BENCH_WARFARE = "BENCH_WARFARE"       # 🪑 Guerre des bancs
    
    # Groupe D: Psychologiques (4)
    CONSERVATIVE_WALL = "CONSERVATIVE_WALL"  # 🧊 Mur conservateur
    KILLER_INSTINCT = "KILLER_INSTINCT"      # 🔥 Instinct de tueur
    COLLAPSE_ALERT = "COLLAPSE_ALERT"        # 😱 Alerte effondrement
    NOTHING_TO_LOSE = "NOTHING_TO_LOSE"      # 💎 Rien à perdre
    
    # Groupe E: Nemesis (3)
    NEMESIS_TRAP = "NEMESIS_TRAP"         # 🎯 Piège Némésis
    PREY_HUNT = "PREY_HUNT"               # 🦅 Chasse à la proie
    AERIAL_RAID = "AERIAL_RAID"           # ✈️ Raid aérien


# MarketType importé depuis quantum.models.market_registry (ligne 17)


class StakeTier(str, Enum):
    """Niveau de mise"""
    SNIPER = "SNIPER"      # 3.0u - Haute confiance
    NORMAL = "NORMAL"      # 1.5-2.0u - Confiance moyenne
    SMALL = "SMALL"        # 0.5-1.0u - Basse confiance
    MICRO = "MICRO"        # 0.25u - Très basse confiance
    SKIP = "SKIP"          # 0u - Ne pas parier


class DecisionSource(str, Enum):
    """Source de la décision"""
    RULE_ENGINE = "RULE_ENGINE"       # Règles seules (confiance > 75%)
    ML_ENGINE = "ML_ENGINE"           # ML seul (confiance règles < 50%)
    HYBRID = "HYBRID"                 # Combinaison (50-75%)
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"


# ═══════════════════════════════════════════════════════════════════════════════════════
# SCENARIO DEFINITION - Définition d'un scénario
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class ScenarioCondition:
    """Une condition pour déclencher un scénario"""
    description: str
    metric: str  # Ex: "pace_factor_combined", "diesel_factor_diff"
    operator: str  # >, <, >=, <=, ==, !=
    threshold: float
    
    def evaluate(self, features: Dict[str, float]) -> bool:
        """Évalue si la condition est remplie"""
        value = features.get(self.metric, 0)
        
        if self.operator == ">":
            return value > self.threshold
        elif self.operator == "<":
            return value < self.threshold
        elif self.operator == ">=":
            return value >= self.threshold
        elif self.operator == "<=":
            return value <= self.threshold
        elif self.operator == "==":
            return value == self.threshold
        elif self.operator == "!=":
            return value != self.threshold
        return False


@dataclass
class ScenarioMarket:
    """Marché recommandé pour un scénario"""
    market: MarketType
    priority: str  # PRIMARY, SECONDARY, TERTIARY
    typical_edge: float  # Edge typique pour ce marché dans ce scénario
    typical_confidence: float
    reasoning: str


@dataclass
class ScenarioDefinition:
    """
    Définition complète d'un scénario.
    
    Chaque scénario a:
    - Des conditions de déclenchement
    - Des marchés recommandés
    - Des marchés à éviter
    - Un historique de performance
    """
    id: ScenarioID
    name: str
    emoji: str
    description: str
    category: ScenarioCategory
    
    # Conditions (toutes doivent être vraies)
    conditions: List[ScenarioCondition]
    
    # Marchés
    primary_markets: List[ScenarioMarket]
    secondary_markets: List[ScenarioMarket] = field(default_factory=list)
    avoid_markets: List[MarketType] = field(default_factory=list)
    
    # Performance historique
    historical_roi: float = 0.0
    historical_win_rate: float = 0.0
    historical_n_bets: int = 0
    historical_profit: float = 0.0
    
    # Métadonnées
    min_confidence_threshold: float = 60.0
    is_active: bool = True
    
    def evaluate_conditions(self, features: Dict[str, float]) -> tuple:
        """
        Évalue toutes les conditions.
        Retourne (is_triggered, confidence, triggered_conditions)
        """
        triggered = []
        total_conditions = len(self.conditions)
        
        for condition in self.conditions:
            if condition.evaluate(features):
                triggered.append(condition.description)
        
        is_triggered = len(triggered) == total_conditions
        confidence = (len(triggered) / total_conditions * 100) if total_conditions > 0 else 0
        
        return is_triggered, confidence, triggered
    
    def get_primary_market(self) -> Optional[ScenarioMarket]:
        """Retourne le marché primaire"""
        return self.primary_markets[0] if self.primary_markets else None


# ═══════════════════════════════════════════════════════════════════════════════════════
# SCENARIO DETECTION RESULT - Résultat de détection
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class ScenarioDetectionResult:
    """
    Résultat de la détection d'un scénario pour un match.
    """
    scenario_id: ScenarioID
    scenario_name: str
    category: ScenarioCategory
    
    # Détection
    is_detected: bool
    confidence: float  # 0-100
    triggered_conditions: List[str]
    missing_conditions: List[str] = field(default_factory=list)
    
    # Marchés recommandés (hérités du scénario)
    recommended_markets: List[MarketType] = field(default_factory=list)
    avoid_markets: List[MarketType] = field(default_factory=list)
    
    # Performance historique du scénario
    historical_roi: float = 0.0
    historical_wr: float = 0.0
    
    # Monte Carlo Validation
    monte_carlo_validated: Optional[bool] = None  # True si validé par MC
    monte_carlo_score: Optional[float] = None     # Score 0-100
    monte_carlo_robustness: Optional[str] = None  # ROCK_SOLID, ROBUST, etc.
    
    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 75
    
    @property
    def is_medium_confidence(self) -> bool:
        return 50 <= self.confidence < 75
    
    @property
    def is_low_confidence(self) -> bool:
        return self.confidence < 50


# ═══════════════════════════════════════════════════════════════════════════════════════
# MARKET RECOMMENDATION - Recommandation de pari
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class MarketProbabilities:
    """Probabilités calculées pour tous les marchés"""
    # Over/Under
    over_15: float = 0.0
    over_25: float = 0.0
    over_35: float = 0.0
    over_45: float = 0.0
    
    # BTTS
    btts_yes: float = 0.0
    btts_no: float = 0.0
    
    # 1X2
    home_win: float = 0.0
    draw: float = 0.0
    away_win: float = 0.0
    
    # Team Goals
    home_over_05: float = 0.0
    home_over_15: float = 0.0
    away_over_05: float = 0.0
    away_over_15: float = 0.0
    
    # Half Goals
    first_half_over_05: float = 0.0
    first_half_over_15: float = 0.0
    second_half_over_05: float = 0.0
    second_half_over_15: float = 0.0
    
    # Period Goals
    goal_0_15: float = 0.0
    goal_75_90: float = 0.0
    home_goal_2h: float = 0.0
    away_goal_2h: float = 0.0
    
    def get(self, market: str) -> float:
        """Récupère la probabilité pour un marché"""
        return getattr(self, market.replace(".", "_").replace("-", "_"), 0.0)


@dataclass
class MarketRecommendation:
    """
    Recommandation de pari sur un marché spécifique.
    """
    # Identifiants
    market: MarketType
    selection: str  # Ex: "Over 2.5", "Home Win", "BTTS Yes"
    
    # Probabilités
    calculated_probability: float  # Notre probabilité
    implied_probability: float  # Probabilité implicite des cotes
    
    # Odds et Edge
    odds: float
    bookmaker: str = "Pinnacle"
    edge: float = 0.0  # calculated_prob - implied_prob
    
    # Confiance et source
    confidence: float = 0.0  # 0-100
    decision_source: DecisionSource = DecisionSource.HYBRID
    
    # Stake
    stake_tier: StakeTier = StakeTier.NORMAL
    stake_units: float = 1.0
    kelly_fraction: float = 0.0
    
    # Reasoning
    reasoning: str = ""
    scenarios_contributing: List[str] = field(default_factory=list)
    
    # Expected Value
    expected_value: float = 0.0  # EV en units
    
    # Flags
    is_value_bet: bool = False  # Edge > 5%
    is_confident: bool = False  # Confidence > 70%
    
    @property
    def is_recommended(self) -> bool:
        """Le pari est-il recommandé?"""
        return self.is_value_bet and self.confidence >= 50
    
    def calculate_ev(self) -> float:
        """Calcule l'Expected Value"""
        win_amount = self.stake_units * (self.odds - 1)
        self.expected_value = (self.calculated_probability * win_amount) - \
                              ((1 - self.calculated_probability) * self.stake_units)
        return self.expected_value


# ═══════════════════════════════════════════════════════════════════════════════════════
# QUANTUM STRATEGY - Output final du système
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class QuantumStrategy:
    """
    Stratégie Quantum complète pour un match.
    
    C'est l'OUTPUT FINAL du système Agent Quantum.
    Contient toutes les recommandations, scénarios, et analyses.
    """
    # ═══════════════════════════════════════════════════════════════════════════════════
    # IDENTIFIANTS
    # ═══════════════════════════════════════════════════════════════════════════════════
    match_id: Optional[int] = None
    home_team: str = ""
    away_team: str = ""
    league: str = ""
    date: Optional[datetime] = None
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # SCÉNARIOS DÉTECTÉS
    # ═══════════════════════════════════════════════════════════════════════════════════
    detected_scenarios: List[ScenarioDetectionResult] = field(default_factory=list)
    primary_scenario: Optional[ScenarioID] = None  # Scénario le plus confiant
    secondary_scenario: Optional[ScenarioID] = None
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # PROBABILITÉS CALCULÉES
    # ═══════════════════════════════════════════════════════════════════════════════════
    probabilities: Optional[MarketProbabilities] = None
    
    # Probabilités par source
    rule_probabilities: Optional[Dict[str, float]] = None
    ml_probabilities: Optional[Dict[str, float]] = None
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # RECOMMANDATIONS DE PARIS
    # ═══════════════════════════════════════════════════════════════════════════════════
    recommendations: List[MarketRecommendation] = field(default_factory=list)
    
    # Séparation par priorité
    primary_bets: List[MarketRecommendation] = field(default_factory=list)
    secondary_bets: List[MarketRecommendation] = field(default_factory=list)
    
    # Marchés à éviter
    avoid_markets: List[str] = field(default_factory=list)
    avoid_reasons: Dict[str, str] = field(default_factory=dict)
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # DÉCISION
    # ═══════════════════════════════════════════════════════════════════════════════════
    decision_source: DecisionSource = DecisionSource.HYBRID
    rule_weight: float = 0.5  # Poids des règles dans la décision
    ml_weight: float = 0.5    # Poids du ML dans la décision
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # EXPOSITION ET RISQUE
    # ═══════════════════════════════════════════════════════════════════════════════════
    total_exposure: float = 0.0  # Total units à risquer
    total_expected_value: float = 0.0  # EV total
    max_loss: float = 0.0
    max_win: float = 0.0
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # MÉTADONNÉES
    # ═══════════════════════════════════════════════════════════════════════════════════
    generated_at: datetime = field(default_factory=datetime.now)
    processing_time_ms: float = 0.0
    confidence_overall: float = 0.0
    
    # DNA et Friction utilisés
    home_dna_confidence: str = "MEDIUM"
    away_dna_confidence: str = "MEDIUM"
    friction_confidence: float = 0.0
    
    # Warnings et notes
    warnings: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    
    # Monte Carlo Validation Summary
    monte_carlo_summary: Optional[Dict[str, Any]] = None
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # MÉTHODES
    # ═══════════════════════════════════════════════════════════════════════════════════
    
    def add_recommendation(self, rec: MarketRecommendation):
        """Ajoute une recommandation"""
        self.recommendations.append(rec)
        
        if rec.stake_tier in [StakeTier.SNIPER, StakeTier.NORMAL]:
            self.primary_bets.append(rec)
        else:
            self.secondary_bets.append(rec)
        
        # Mise à jour exposition
        self.total_exposure += rec.stake_units
        self.total_expected_value += rec.expected_value
    
    def add_avoid_market(self, market: str, reason: str):
        """Ajoute un marché à éviter"""
        self.avoid_markets.append(market)
        self.avoid_reasons[market] = reason
    
    def calculate_totals(self):
        """Calcule les totaux d'exposition et EV"""
        self.total_exposure = sum(r.stake_units for r in self.recommendations)
        self.total_expected_value = sum(r.expected_value for r in self.recommendations)
        self.max_loss = self.total_exposure
        self.max_win = sum(r.stake_units * (r.odds - 1) for r in self.recommendations)
    
    @property
    def has_value_bets(self) -> bool:
        """Y a-t-il des paris de valeur?"""
        return any(r.is_value_bet for r in self.recommendations)
    
    @property
    def is_actionable(self) -> bool:
        """La stratégie est-elle actionnable?"""
        return len(self.primary_bets) > 0
    
    @property
    def best_bet(self) -> Optional[MarketRecommendation]:
        """Meilleur pari (plus haut edge × confidence)"""
        if not self.recommendations:
            return None
        return max(self.recommendations, key=lambda r: r.edge * r.confidence)
    
    @property
    def scenario_names(self) -> List[str]:
        """Noms des scénarios détectés"""
        return [s.scenario_name for s in self.detected_scenarios if s.is_detected]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour API/JSON"""
        return {
            "match": f"{self.home_team} vs {self.away_team}",
            "date": self.date.isoformat() if self.date else None,
            "league": self.league,
            "scenarios_detected": self.scenario_names,
            "decision_source": self.decision_source.value,
            "recommendations": [
                {
                    "market": r.market.value,
                    "selection": r.selection,
                    "odds": r.odds,
                    "probability": round(r.calculated_probability, 3),
                    "edge": round(r.edge * 100, 1),
                    "confidence": round(r.confidence, 1),
                    "stake": r.stake_units,
                    "reasoning": r.reasoning
                }
                for r in self.recommendations
            ],
            "avoid": self.avoid_markets,
            "total_exposure": round(self.total_exposure, 2),
            "expected_value": round(self.total_expected_value, 3),
            "confidence_overall": round(self.confidence_overall, 1),
            "generated_at": self.generated_at.isoformat()
        }
    
    def to_summary(self) -> str:
        """Génère un résumé textuel"""
        lines = [
            f"═══════════════════════════════════════════════════════",
            f"QUANTUM STRATEGY: {self.home_team} vs {self.away_team}",
            f"═══════════════════════════════════════════════════════",
            f"",
            f"📊 Scénarios: {', '.join(self.scenario_names) or 'Aucun détecté'}",
            f"🎯 Source: {self.decision_source.value}",
            f"",
            f"💰 RECOMMANDATIONS:",
        ]
        
        for i, rec in enumerate(self.recommendations[:5], 1):
            lines.append(
                f"  {i}. {rec.selection} @ {rec.odds:.2f}"
                f" | Edge: {rec.edge*100:.1f}% | Stake: {rec.stake_units}u"
            )
        
        if self.avoid_markets:
            lines.append(f"")
            lines.append(f"❌ ÉVITER: {', '.join(self.avoid_markets)}")
        
        lines.extend([
            f"",
            f"📈 Exposition: {self.total_exposure:.1f}u | EV: {self.total_expected_value:+.2f}u",
            f"═══════════════════════════════════════════════════════",
        ])
        
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════════════
# BATCH STRATEGY - Stratégies pour plusieurs matchs
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class DailyQuantumPicks:
    """
    Picks du jour - Agrégation de plusieurs QuantumStrategy.
    """
    date: datetime
    
    # Toutes les stratégies
    strategies: List[QuantumStrategy] = field(default_factory=list)
    
    # Filtré par edge minimum
    value_bets: List[MarketRecommendation] = field(default_factory=list)
    
    # Stats globales
    total_matches_analyzed: int = 0
    total_bets_recommended: int = 0
    total_exposure: float = 0.0
    total_expected_value: float = 0.0
    
    # Filtres appliqués
    min_edge_filter: float = 5.0
    min_confidence_filter: float = 60.0
    
    # Top picks
    top_picks: List[MarketRecommendation] = field(default_factory=list)
    
    def add_strategy(self, strategy: QuantumStrategy):
        """Ajoute une stratégie"""
        self.strategies.append(strategy)
        self.total_matches_analyzed += 1
        
        for rec in strategy.recommendations:
            if rec.edge >= self.min_edge_filter / 100 and rec.confidence >= self.min_confidence_filter:
                self.value_bets.append(rec)
                self.total_bets_recommended += 1
                self.total_exposure += rec.stake_units
                self.total_expected_value += rec.expected_value
    
    def get_top_picks(self, n: int = 5) -> List[MarketRecommendation]:
        """Retourne les N meilleurs picks"""
        sorted_bets = sorted(
            self.value_bets,
            key=lambda r: r.edge * r.confidence,
            reverse=True
        )
        self.top_picks = sorted_bets[:n]
        return self.top_picks
    
    def get_picks_by_scenario(self, scenario_id: ScenarioID) -> List[MarketRecommendation]:
        """Retourne les picks pour un scénario donné"""
        return [
            rec for rec in self.value_bets
            if scenario_id.value in rec.scenarios_contributing
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire"""
        return {
            "date": self.date.isoformat(),
            "matches_analyzed": self.total_matches_analyzed,
            "bets_recommended": self.total_bets_recommended,
            "total_exposure": round(self.total_exposure, 2),
            "total_ev": round(self.total_expected_value, 3),
            "top_picks": [
                {
                    "match": f"{rec.reasoning.split(':')[0] if ':' in rec.reasoning else 'Match'}",
                    "market": rec.market.value,
                    "selection": rec.selection,
                    "odds": rec.odds,
                    "edge": round(rec.edge * 100, 1),
                    "confidence": round(rec.confidence, 1),
                    "stake": rec.stake_units
                }
                for rec in self.get_top_picks()
            ]
        }


# ═══════════════════════════════════════════════════════════════════════════════════════
# PERFORMANCE TRACKING - Suivi des performances
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class BetResult:
    """Résultat d'un pari"""
    recommendation_id: str
    match_id: int
    market: MarketType
    selection: str
    odds: float
    stake: float
    
    # Résultat
    result: str  # WIN, LOSS, VOID, PUSH
    profit_loss: float
    
    # Contexte
    scenario_used: Optional[ScenarioID] = None
    decision_source: DecisionSource = DecisionSource.HYBRID
    confidence_at_bet: float = 0.0
    edge_at_bet: float = 0.0
    
    # Timestamps
    placed_at: Optional[datetime] = None
    settled_at: Optional[datetime] = None


@dataclass
class ScenarioPerformance:
    """Performance d'un scénario"""
    scenario_id: ScenarioID
    
    # Stats
    total_bets: int = 0
    wins: int = 0
    losses: int = 0
    voids: int = 0
    
    win_rate: float = 0.0
    roi: float = 0.0
    profit: float = 0.0
    
    # Par marché
    performance_by_market: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Trend
    recent_form: str = ""  # Ex: "WWLWW"
    is_hot: bool = False
    is_cold: bool = False


@dataclass
class QuantumPerformanceReport:
    """Rapport de performance global du système"""
    # Période
    start_date: datetime
    end_date: datetime
    
    # Stats globales
    total_bets: int = 0
    total_wins: int = 0
    total_losses: int = 0
    
    win_rate: float = 0.0
    roi: float = 0.0
    total_profit: float = 0.0
    total_staked: float = 0.0
    
    # Performance par scénario
    scenarios_performance: Dict[ScenarioID, ScenarioPerformance] = field(default_factory=dict)
    
    # Performance par marché
    markets_performance: Dict[MarketType, Dict[str, float]] = field(default_factory=dict)
    
    # Performance par source de décision
    rule_engine_roi: float = 0.0
    ml_engine_roi: float = 0.0
    hybrid_roi: float = 0.0
    
    # Best/Worst
    best_scenario: Optional[ScenarioID] = None
    worst_scenario: Optional[ScenarioID] = None
    best_market: Optional[MarketType] = None
    worst_market: Optional[MarketType] = None
    
    # Trends
    monthly_roi: Dict[str, float] = field(default_factory=dict)
    weekly_roi: Dict[str, float] = field(default_factory=dict)
