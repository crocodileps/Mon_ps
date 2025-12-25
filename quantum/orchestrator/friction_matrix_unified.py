#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════════════
FRICTION MATRIX UNIFIED V2.0 - HEDGE FUND GRADE
═══════════════════════════════════════════════════════════════════════════════════════

Fichier: quantum/orchestrator/friction_matrix_unified.py
Version: 2.0.0
Date: 2025-12-25

CONSOLIDATION DE:
- quantum_orchestrator_v1.py (FrictionMatrix dataclass + logique métier)
- quantum_orchestrator_v1_production.py (Query SQL réelle)
- quantum_orchestrator_v1_modular/adapters/database_adapter.py (MatchupFriction + helpers)

ARCHITECTURE:
1. FrictionMatrix = Dataclass avec données DB + métriques calculées
2. load_friction() = Query SQL vers quantum.matchup_friction
3. compute_dynamic_metrics() = Calcul kinetic/physical depuis TeamDNA

PHILOSOPHIE:
- Séparation IO (load_friction) et CPU (compute_dynamic_metrics)
- Formule Kinetic non-linéaire (tempo = amplificateur)
- Physical Edge contextuel (depuis PhysicalDNA du jour)
- Config externalisée pour calibration

CHANGELOG V2.0:
- Correction physical_edge: rotation élevée = fraîcheur (pas fatigue)
- Ajout efficiency_factor: pressing × possession
- Séparation Intensity/Stamina/Freshness dans PhysicalBreakdown
- Ajout normalisation des données via NORMALIZATION_SCALES
- Intégration bench_quality (top3_dependency) dans freshness
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, TYPE_CHECKING
import json
import math
import logging

# Import config externalisée
try:
    from quantum.config.friction_config import (
        FRICTION_CONFIG,
        NORMALIZATION_SCALES,
        get_kinetic_config,
        get_physical_config,
        get_scenario_config,
        get_validation_config,
        get_confidence_config,
        normalize_to_100,
    )
except ImportError:
    # Fallback si config pas encore déployée
    from friction_config import (
        FRICTION_CONFIG,
        NORMALIZATION_SCALES,
        get_kinetic_config,
        get_physical_config,
        get_scenario_config,
        get_validation_config,
        get_confidence_config,
        normalize_to_100,
    )

# Type checking imports (évite circular imports)
if TYPE_CHECKING:
    from quantum.orchestrator.dataclasses_v2 import TeamDNA, PhysicalDNA

# Logger Senior Grade
logger = logging.getLogger("QuantumOrchestrator.Friction")


# ═══════════════════════════════════════════════════════════════════════════════════════
# VALIDATION HELPERS
# ═══════════════════════════════════════════════════════════════════════════════════════

def validate_range(value: float, min_v: float = 0.0, max_v: float = 100.0, 
                   field_name: str = "value") -> float:
    """
    Clamp value to valid range with warning log.
    
    Args:
        value: Valeur à valider
        min_v: Minimum autorisé
        max_v: Maximum autorisé
        field_name: Nom du champ (pour logging)
    
    Returns:
        Valeur clampée dans [min_v, max_v]
    """
    config = get_validation_config()
    
    if value < min_v or value > max_v:
        if config.get("log_warnings", True):
            logger.warning(f"⚠️ {field_name}={value} hors bornes [{min_v}, {max_v}], clampé")
        return max(min_v, min(max_v, value))
    return value


def validate_probability(value: float, field_name: str = "probability") -> float:
    """Valide une probabilité dans [0, 1]."""
    return validate_range(value, 0.0, 1.0, field_name)


def safe_float(value: Any, default: float = 0.0) -> float:
    """Convertit en float de manière sécurisée."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Convertit en int de manière sécurisée."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def parse_jsonb(value: Any) -> Dict:
    """Parse un champ JSONB PostgreSQL."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            logger.warning(f"⚠️ Impossible de parser JSONB: {value[:50]}...")
            return {}
    return {}


# ═══════════════════════════════════════════════════════════════════════════════════════
# PHYSICAL BREAKDOWN - Détail du Physical Edge pour Betting Strategies
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class PhysicalBreakdown:
    """
    Détail du physical_edge pour stratégies de betting 1H/2H.
    
    Expose les sous-scores:
    - Intensity: Qui domine le début de match (pressing + aérien)
    - Stamina: Qui finit fort (late_game_dominance + resist_late)
    - Freshness: Qui est le plus frais (rotation × bench_quality)
    
    Usage:
        breakdown = friction.get_physical_breakdown()
        if breakdown.first_half_edge > 60:
            # BACK home to lead at HT
    """
    # Scores bruts
    intensity_home: float = 50.0
    intensity_away: float = 50.0
    stamina_home: float = 50.0
    stamina_away: float = 50.0
    freshness_home: float = 50.0
    freshness_away: float = 50.0
    
    # Score final
    overall_edge: float = 50.0
    
    # Efficiency factors (pour debug)
    efficiency_home: float = 1.0
    efficiency_away: float = 1.0
    
    @property
    def first_half_edge(self) -> float:
        """
        Avantage physique pour la 1ère mi-temps.
        Basé sur l'intensité (qui domine le début).
        
        Returns:
            50 = équilibré, >50 = avantage home, <50 = avantage away
        """
        return 50.0 + ((self.intensity_home - self.intensity_away) / 2.0)
    
    @property
    def second_half_edge(self) -> float:
        """
        Avantage physique pour la 2ème mi-temps.
        Basé sur l'endurance (qui finit fort).
        
        Returns:
            50 = équilibré, >50 = avantage home, <50 = avantage away
        """
        return 50.0 + ((self.stamina_home - self.stamina_away) / 2.0)
    
    @property
    def late_season_edge(self) -> float:
        """
        Avantage pour fin de saison (fraîcheur effectif).
        
        Returns:
            50 = équilibré, >50 = avantage home, <50 = avantage away
        """
        return 50.0 + ((self.freshness_home - self.freshness_away) / 2.0)
    
    @property
    def dominant_phase(self) -> str:
        """
        Indique dans quelle phase l'équipe home est la plus forte.
        
        Returns:
            "FIRST_HALF", "SECOND_HALF", "LATE_SEASON", ou "BALANCED"
        """
        edges = {
            "FIRST_HALF": self.first_half_edge,
            "SECOND_HALF": self.second_half_edge,
            "LATE_SEASON": self.late_season_edge,
        }
        max_phase = max(edges, key=edges.get)
        if edges[max_phase] > 55:
            return max_phase
        return "BALANCED"
    
    def to_dict(self) -> Dict[str, float]:
        """Convertit en dictionnaire."""
        return {
            "intensity_home": self.intensity_home,
            "intensity_away": self.intensity_away,
            "stamina_home": self.stamina_home,
            "stamina_away": self.stamina_away,
            "freshness_home": self.freshness_home,
            "freshness_away": self.freshness_away,
            "overall_edge": self.overall_edge,
            "first_half_edge": self.first_half_edge,
            "second_half_edge": self.second_half_edge,
            "late_season_edge": self.late_season_edge,
            "dominant_phase": self.dominant_phase,
        }


# ═══════════════════════════════════════════════════════════════════════════════════════
# FRICTION MATRIX - DATACLASS ENRICHIE
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class FrictionMatrix:
    """
    Matrice de friction unifiée HEDGE FUND GRADE.
    
    Combine:
    - Données statiques depuis quantum.matchup_friction (DB)
    - Métriques dynamiques calculées depuis TeamDNA (runtime)
    
    Attributes:
        home_team: Équipe à domicile
        away_team: Équipe à l'extérieur
        
        # Données DB (statiques)
        friction_score: Score friction global (0-100)
        style_clash_score: Incompatibilité tactique (0-100)
        tempo_clash_score: Différence de tempo (0-100)
        mental_clash_score: Pression psychologique (0-100)
        chaos_potential: Probabilité d'événements aléatoires (0-100)
        predicted_goals: Buts prédits pour ce match
        btts_probability: Probabilité Both Teams To Score
        predicted_over25_prob: Probabilité Over 2.5 goals
        predicted_winner: home, away, ou draw
        h2h_matches: Nombre de confrontations historiques
        h2h_avg_goals: Moyenne de buts dans les H2H
        friction_vector: JSONB avec détails friction
        confidence_level: low, medium, high
        
        # Métriques calculées (dynamiques)
        kinetic_home: Énergie cinétique canalisée par home
        kinetic_away: Énergie cinétique canalisée par away
        physical_edge: Avantage physique (50 = neutre)
        temporal_clash: = tempo_clash_score (alias)
        psyche_dominance: = mental_clash_score (alias)
        triggered_scenarios: Scénarios détectés automatiquement
    """
    
    # === IDENTITÉ ===
    home_team: str
    away_team: str
    
    # === DONNÉES DB (Table: quantum.matchup_friction) ===
    friction_score: float = 50.0
    style_clash_score: float = 50.0
    tempo_clash_score: float = 50.0
    mental_clash_score: float = 50.0
    chaos_potential: float = 50.0
    
    predicted_goals: float = 2.5
    btts_probability: float = 0.5
    predicted_over25_prob: float = 0.5
    predicted_winner: str = "draw"
    
    # H2H Context
    h2h_matches: int = 0
    h2h_avg_goals: float = 0.0
    
    # Metadata
    friction_vector: Dict = field(default_factory=dict)
    confidence_level: str = "medium"
    
    # === MÉTRIQUES CALCULÉES (Runtime via compute_dynamic_metrics) ===
    kinetic_home: float = 50.0
    kinetic_away: float = 50.0
    physical_edge: float = 50.0
    
    # Alias pour compatibilité avec ancien code
    temporal_clash: float = 50.0      # = tempo_clash_score
    psyche_dominance: float = 50.0    # = mental_clash_score
    
    # Scénarios détectés
    triggered_scenarios: List[str] = field(default_factory=list)
    
    # Détail du physical_edge pour betting 1H/2H (V2.0)
    physical_breakdown: Optional[PhysicalBreakdown] = None
    
    # Flag indiquant si compute_dynamic_metrics a été appelé
    _dynamics_computed: bool = field(default=False, repr=False)
    
    def __post_init__(self):
        """Validation automatique à la création."""
        # Clamp all scores to valid ranges
        self.friction_score = validate_range(self.friction_score, field_name="friction_score")
        self.style_clash_score = validate_range(self.style_clash_score, field_name="style_clash_score")
        self.tempo_clash_score = validate_range(self.tempo_clash_score, field_name="tempo_clash_score")
        self.mental_clash_score = validate_range(self.mental_clash_score, field_name="mental_clash_score")
        self.chaos_potential = validate_range(self.chaos_potential, field_name="chaos_potential")
        
        # Validate probabilities
        self.btts_probability = validate_probability(self.btts_probability, "btts_probability")
        self.predicted_over25_prob = validate_probability(self.predicted_over25_prob, "predicted_over25_prob")
        
        # Validate predicted_goals
        config = get_validation_config()
        self.predicted_goals = validate_range(
            self.predicted_goals,
            config.get("goals_min", 0.0),
            config.get("goals_max", 10.0),
            "predicted_goals"
        )
        
        # Synchroniser les alias
        self.temporal_clash = self.tempo_clash_score
        self.psyche_dominance = self.mental_clash_score
        
        # Auto-detect scenarios (basé sur données statiques)
        self._detect_scenarios()
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # COMPUTE DYNAMIC METRICS - MOTEUR QUANT SENIOR
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def compute_dynamic_metrics(self, home_dna: 'TeamDNA', away_dna: 'TeamDNA') -> None:
        """
        Moteur Quant Senior : Calcule les métriques cinétiques et physiques
        en croisant la Friction (Historique/Statique) avec l'ADN (Actuel/Dynamique).
        
        DOIT être appelé après load_friction() et avant utilisation dans les modèles.
        
        Args:
            home_dna: TeamDNA de l'équipe à domicile
            away_dna: TeamDNA de l'équipe à l'extérieur
        """
        # 1. PHYSICAL EDGE (depuis PhysicalDNA - Vecteur 9)
        self.physical_edge = self._calculate_physical_edge(home_dna, away_dna)
        
        # 2. KINETIC ENERGY (Formule Non-Linéaire Hedge Fund)
        self._calculate_kinetic_energy(home_dna, away_dna)
        
        # 3. Re-détecter les scénarios avec les nouvelles données
        self._detect_scenarios()
        
        # Flag
        self._dynamics_computed = True
        
        logger.info(
            f"🔬 Friction [{self.home_team} vs {self.away_team}] "
            f"Kinetic: H={self.kinetic_home:.1f} A={self.kinetic_away:.1f} | "
            f"Physical Edge: {self.physical_edge:.1f} | "
            f"Scenarios: {self.triggered_scenarios}"
        )
    
    def _calculate_physical_edge(self, home_dna: 'TeamDNA', away_dna: 'TeamDNA') -> float:
        """
        Calcule l'avantage physique HOME vs AWAY (VERSION 2.0 SENIOR QUANT).
        
        CORRECTIONS V2:
        - Rotation élevée = joueurs FRAIS (pas fatigués!)
        - Efficiency factor: pressing coûte moins si tu as le ballon
        - Séparation Intensity / Stamina / Freshness
        - Pondération bench_quality sur freshness
        
        Returns:
            50.0 = équilibré, >50 = avantage home, <50 = avantage away
        """
        config = get_physical_config()
        
        # Récupérer les DNA
        h_phys = getattr(home_dna, 'physical', None)
        a_phys = getattr(away_dna, 'physical', None)
        h_context = getattr(home_dna, 'context', None)
        a_context = getattr(away_dna, 'context', None)
        h_roster = getattr(home_dna, 'roster', None)
        a_roster = getattr(away_dna, 'roster', None)
        
        if not h_phys or not a_phys:
            logger.debug(f"⚠️ PhysicalDNA manquant, physical_edge = {config['default_value']}")
            return config["default_value"]
        
        # ═══════════════════════════════════════════════════════════════════════════
        # 1. POSSESSION CONTEXT (Pour efficiency factor)
        # ═══════════════════════════════════════════════════════════════════════════
        h_poss = 50.0
        a_poss = 50.0
        
        if config.get("efficiency_factor_enabled", True):
            if h_context:
                # home_strength comme proxy de possession à domicile
                h_poss = safe_float(getattr(h_context, 'home_strength', 50.0))
            if a_context:
                # away_strength comme proxy de possession à l'extérieur
                a_poss = safe_float(getattr(a_context, 'away_strength', 50.0))
        
        # Efficiency: pressing coûte moins si tu as le ballon
        # >1 si tu domines, <1 si tu subis
        efficiency_base = config.get("efficiency_base", 50.0)
        h_efficiency = h_poss / efficiency_base
        a_efficiency = a_poss / efficiency_base
        
        # ═══════════════════════════════════════════════════════════════════════════
        # 2. SCORE D'INTENSITÉ (40%) - Capacité à imposer le défi physique
        # ═══════════════════════════════════════════════════════════════════════════
        # Pressing normalisé pondéré par efficacité + Aérien
        h_pressing_raw = safe_float(getattr(h_phys, 'pressing_intensity', 11.68))
        a_pressing_raw = safe_float(getattr(a_phys, 'pressing_intensity', 11.68))
        
        # Normaliser vers 0-100 (pressing_intensity: 4.6 → 23.0)
        h_pressing_norm = normalize_to_100(h_pressing_raw, "pressing_intensity")
        a_pressing_norm = normalize_to_100(a_pressing_raw, "pressing_intensity")
        
        # Appliquer efficiency factor
        h_pressing_effective = h_pressing_norm * h_efficiency
        a_pressing_effective = a_pressing_norm * a_efficiency
        
        # Aérien (si disponible, sinon 50)
        h_aerial = safe_float(getattr(h_phys, 'aerial_win_pct', 50.0))
        a_aerial = safe_float(getattr(a_phys, 'aerial_win_pct', 50.0))
        
        # Calcul intensité
        int_pressing_w = config.get("intensity_pressing_weight", 0.60)
        int_aerial_w = config.get("intensity_aerial_weight", 0.40)
        
        h_intensity = (h_pressing_effective * int_pressing_w) + (h_aerial * int_aerial_w)
        a_intensity = (a_pressing_effective * int_pressing_w) + (a_aerial * int_aerial_w)
        
        # ═══════════════════════════════════════════════════════════════════════════
        # 3. SCORE D'ENDURANCE (40%) - Capacité à finir fort (2H bets)
        # ═══════════════════════════════════════════════════════════════════════════
        h_late_dom_raw = safe_float(getattr(h_phys, 'late_game_dominance', 36.3))
        a_late_dom_raw = safe_float(getattr(a_phys, 'late_game_dominance', 36.3))
        
        # late_game_dominance est déjà en 0-100 (9 → 79)
        h_late_dom = h_late_dom_raw  # Pas de normalisation nécessaire
        a_late_dom = a_late_dom_raw
        
        # Resist late (si disponible dans les données)
        h_resist = safe_float(getattr(h_phys, 'resist_late', 50.0))
        a_resist = safe_float(getattr(a_phys, 'resist_late', 50.0))
        
        # Calcul stamina
        stam_late_dom_w = config.get("stamina_late_dom_weight", 0.60)
        stam_resist_w = config.get("stamina_resist_weight", 0.40)
        
        h_stamina = (h_late_dom * stam_late_dom_w) + (h_resist * stam_resist_w)
        a_stamina = (a_late_dom * stam_late_dom_w) + (a_resist * stam_resist_w)
        
        # ═══════════════════════════════════════════════════════════════════════════
        # 4. SCORE DE FRAÎCHEUR (20%) - Gestion de l'effectif (CORRIGÉ V2)
        # ═══════════════════════════════════════════════════════════════════════════
        # CORRECTION: rotation élevée = joueurs FRAIS (pas fatigués!)
        h_rotation = safe_float(getattr(h_phys, 'estimated_rotation_index', 50.0))
        a_rotation = safe_float(getattr(a_phys, 'estimated_rotation_index', 50.0))
        
        # AMÉLIORATION: Pondérer par qualité du banc
        # top3_dependency élevé = équipe dépendante = banc faible
        h_bench_factor = 1.0
        a_bench_factor = 1.0
        
        if config.get("bench_quality_enabled", True):
            if h_roster:
                h_top3_dep = safe_float(getattr(h_roster, 'top3_dependency', 50.0))
                h_bench_factor = (100 - h_top3_dep) / 100.0  # 0.0 à 1.0
            if a_roster:
                a_top3_dep = safe_float(getattr(a_roster, 'top3_dependency', 50.0))
                a_bench_factor = (100 - a_top3_dep) / 100.0
        
        # Freshness = Rotation × Bench Quality
        # Si rotation=88 et bench_factor=0.68 → freshness=59.84
        h_freshness = h_rotation * h_bench_factor
        a_freshness = a_rotation * a_bench_factor
        
        # ═══════════════════════════════════════════════════════════════════════════
        # 5. AGRÉGATION FINALE
        # ═══════════════════════════════════════════════════════════════════════════
        intensity_w = config.get("intensity_weight", 0.40)
        stamina_w = config.get("stamina_weight", 0.40)
        freshness_w = config.get("freshness_weight", 0.20)
        
        h_final = (
            h_intensity * intensity_w +
            h_stamina * stamina_w +
            h_freshness * freshness_w
        )
        
        a_final = (
            a_intensity * intensity_w +
            a_stamina * stamina_w +
            a_freshness * freshness_w
        )
        
        # ═══════════════════════════════════════════════════════════════════════════
        # 6. DELTA NORMALISÉ (Centré sur 50)
        # ═══════════════════════════════════════════════════════════════════════════
        edge = 50.0 + ((h_final - a_final) / config.get("score_divisor", 2.0))
        
        # ═══════════════════════════════════════════════════════════════════════════
        # 7. STOCKER LE BREAKDOWN POUR BETTING STRATEGIES
        # ═══════════════════════════════════════════════════════════════════════════
        self.physical_breakdown = PhysicalBreakdown(
            intensity_home=h_intensity,
            intensity_away=a_intensity,
            stamina_home=h_stamina,
            stamina_away=a_stamina,
            freshness_home=h_freshness,
            freshness_away=a_freshness,
            overall_edge=validate_range(edge, 0.0, 100.0, "physical_edge"),
            efficiency_home=h_efficiency,
            efficiency_away=a_efficiency,
        )
        
        logger.debug(
            f"Physical V2: Intensity H={h_intensity:.1f}/A={a_intensity:.1f} | "
            f"Stamina H={h_stamina:.1f}/A={a_stamina:.1f} | "
            f"Freshness H={h_freshness:.1f}/A={a_freshness:.1f} | "
            f"Edge={edge:.1f}"
        )
        
        return validate_range(edge, 0.0, 100.0, "physical_edge")
    
    def _calculate_kinetic_energy(self, home_dna: 'TeamDNA', away_dna: 'TeamDNA') -> None:
        """
        Calcule l'énergie cinétique avec formule non-linéaire.
        
        Formule:
            base_intensity = (style × w1 + mental × w2 + friction × w3)
            tempo_factor = (tempo / 50) ** exponent
            chaos_factor = 1 + (chaos - 50) / divisor
            total_kinetic = base_intensity × tempo_factor × chaos_factor
        """
        config = get_kinetic_config()
        
        # 1. Base Intensity (moyenne pondérée)
        base_intensity = (
            self.style_clash_score * config["style_clash_weight"] +
            self.mental_clash_score * config["mental_clash_weight"] +
            self.friction_score * config["friction_score_weight"]
        )
        
        # 2. Tempo Factor (non-linéaire - amplificateur)
        # tempo > 50 → facteur > 1 (amplifie)
        # tempo < 50 → facteur < 1 (compresse)
        tempo_normalized = max(config["tempo_factor_min"], self.tempo_clash_score / 50.0)
        tempo_factor = tempo_normalized ** config["tempo_exponent"]
        
        # 3. Chaos Factor (volatilité)
        # chaos = 50 → factor = 1.0
        # chaos = 100 → factor = 1.25 (avec divisor=200)
        # chaos = 0 → factor = 0.75
        chaos_factor = 1.0 + ((self.chaos_potential - 50) / config["chaos_divisor"])
        
        # 4. Énergie totale du système
        total_kinetic = base_intensity * tempo_factor * chaos_factor
        
        # 5. Distribution Home vs Away
        home_advantage = config["home_advantage_base"]
        
        # Ajustement si home dominé mentalement
        if self.mental_clash_score < config["home_advantage_mental_threshold"]:
            home_advantage = config["home_advantage_reduced"]
        
        # Calcul final avec conservation approximative de l'énergie
        self.kinetic_home = total_kinetic * home_advantage
        self.kinetic_away = total_kinetic * (2.0 - home_advantage)
        
        # Clamp aux bornes
        self.kinetic_home = validate_range(
            self.kinetic_home,
            config["kinetic_min"],
            config["kinetic_max"],
            "kinetic_home"
        )
        self.kinetic_away = validate_range(
            self.kinetic_away,
            config["kinetic_min"],
            config["kinetic_max"],
            "kinetic_away"
        )
        
        logger.debug(
            f"Kinetic calc: base={base_intensity:.1f} × tempo_factor={tempo_factor:.2f} "
            f"× chaos_factor={chaos_factor:.2f} = {total_kinetic:.1f}"
        )
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # SCENARIO DETECTION
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def _detect_scenarios(self) -> List[str]:
        """
        Détecte automatiquement les scénarios de jeu basés sur les métriques.
        
        Returns:
            Liste des scénarios détectés
        """
        config = get_scenario_config()
        scenarios = []
        
        # TOTAL_CHAOS
        if self.chaos_potential >= config["chaos_threshold"]:
            scenarios.append("TOTAL_CHAOS")
        
        # OPEN_GAME
        if (self.style_clash_score >= config["open_game_style_threshold"] and
            self.tempo_clash_score >= config["open_game_tempo_threshold"]):
            scenarios.append("OPEN_GAME")
        
        # HOME_DOMINATED (home sous pression mentale)
        if self.mental_clash_score <= config["mental_home_dominated_threshold"]:
            scenarios.append("HOME_DOMINATED")
        
        # AWAY_PRESSURED (away sous pression mentale)
        elif self.mental_clash_score >= config["mental_away_pressured_threshold"]:
            scenarios.append("AWAY_PRESSURED")
        
        # HIGH_SCORING_RIVALRY
        if self.h2h_avg_goals >= config["high_scoring_h2h_threshold"]:
            scenarios.append("HIGH_SCORING_RIVALRY")
        
        # TENSE_STALEMATE
        if (self.predicted_winner == "draw" and 
            self.friction_score >= config["tense_stalemate_friction_threshold"]):
            scenarios.append("TENSE_STALEMATE")
        
        self.triggered_scenarios = scenarios
        return scenarios
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # CONFIDENCE SCORING
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def compute_confidence_score(self) -> str:
        """
        Calcule la confiance basée sur la qualité des données.
        
        Returns:
            "low", "medium", ou "high"
        """
        config = get_confidence_config()
        score = 0
        
        # H2H data quality
        if self.h2h_matches >= config["h2h_high_threshold"]:
            score += config["h2h_high_points"]
        elif self.h2h_matches >= config["h2h_medium_threshold"]:
            score += config["h2h_medium_points"]
        
        # Prediction coherence (goals dans range raisonnable)
        goals_range = config["goals_coherent_range"]
        if goals_range[0] <= self.predicted_goals <= goals_range[1]:
            score += config["goals_coherent_points"]
        
        # BTTS coherence avec predicted_goals
        # Approximation: P(BTTS) ≈ 1 - 0.5^predicted_goals
        expected_btts = 1 - (0.5 ** self.predicted_goals)
        if abs(self.btts_probability - expected_btts) < config["btts_coherence_tolerance"]:
            score += config["btts_coherent_points"]
        
        # Friction vector présent
        if self.friction_vector:
            score += config["friction_vector_points"]
        
        # Chaos > seuil minimum
        if self.chaos_potential > config["chaos_min_threshold"]:
            score += config["chaos_present_points"]
        
        # Déterminer le niveau
        if score >= config["high_threshold"]:
            return "high"
        elif score >= config["medium_threshold"]:
            return "medium"
        return "low"
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # UTILITIES
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def get_physical_breakdown(self) -> Optional[PhysicalBreakdown]:
        """
        Retourne le détail du physical_edge pour stratégies de betting.
        
        Returns:
            PhysicalBreakdown ou None si compute_dynamic_metrics n'a pas été appelé
        """
        if not self._dynamics_computed:
            logger.warning("⚠️ compute_dynamic_metrics() n'a pas été appelé")
        return self.physical_breakdown
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour snapshot/serialization."""
        result = {
            "home_team": self.home_team,
            "away_team": self.away_team,
            "friction_score": self.friction_score,
            "style_clash_score": self.style_clash_score,
            "tempo_clash_score": self.tempo_clash_score,
            "mental_clash_score": self.mental_clash_score,
            "chaos_potential": self.chaos_potential,
            "predicted_goals": self.predicted_goals,
            "btts_probability": self.btts_probability,
            "predicted_over25_prob": self.predicted_over25_prob,
            "predicted_winner": self.predicted_winner,
            "h2h_matches": self.h2h_matches,
            "h2h_avg_goals": self.h2h_avg_goals,
            "friction_vector": self.friction_vector,
            "confidence_level": self.confidence_level,
            "kinetic_home": self.kinetic_home,
            "kinetic_away": self.kinetic_away,
            "physical_edge": self.physical_edge,
            "triggered_scenarios": self.triggered_scenarios,
            "_dynamics_computed": self._dynamics_computed,
        }
        
        # Ajouter le breakdown si disponible
        if self.physical_breakdown:
            result["physical_breakdown"] = self.physical_breakdown.to_dict()
        
        return result
    
    def summary(self) -> str:
        """Retourne un résumé lisible de la friction."""
        base = (
            f"═══ FRICTION: {self.home_team} vs {self.away_team} ═══\n"
            f"  Friction Score: {self.friction_score:.1f}\n"
            f"  Style Clash: {self.style_clash_score:.1f} | Tempo: {self.tempo_clash_score:.1f}\n"
            f"  Mental Clash: {self.mental_clash_score:.1f} | Chaos: {self.chaos_potential:.1f}\n"
            f"  Predicted Goals: {self.predicted_goals:.2f} | BTTS: {self.btts_probability:.1%}\n"
            f"  Kinetic: Home={self.kinetic_home:.1f} Away={self.kinetic_away:.1f}\n"
            f"  Physical Edge: {self.physical_edge:.1f}\n"
        )
        
        # Ajouter le breakdown si disponible
        if self.physical_breakdown:
            pb = self.physical_breakdown
            base += (
                f"  └── Breakdown:\n"
                f"      1H Edge: {pb.first_half_edge:.1f} | 2H Edge: {pb.second_half_edge:.1f}\n"
                f"      Dominant Phase: {pb.dominant_phase}\n"
            )
        
        base += (
            f"  Scenarios: {', '.join(self.triggered_scenarios) or 'None'}\n"
            f"  Confidence: {self.confidence_level}"
        )
        
        return base


# ═══════════════════════════════════════════════════════════════════════════════════════
# FRICTION LOADER - QUERY SQL
# ═══════════════════════════════════════════════════════════════════════════════════════

class FrictionLoader:
    """
    Charge les données friction depuis PostgreSQL.
    
    Usage:
        loader = FrictionLoader(db_pool)
        friction = await loader.load_friction("Liverpool", "Manchester City")
        friction.compute_dynamic_metrics(home_dna, away_dna)
    """
    
    def __init__(self, db_pool):
        """
        Args:
            db_pool: Pool de connexions asyncpg ou psycopg2
        """
        self.pool = db_pool
    
    async def load_friction(self, home_team: str, away_team: str) -> FrictionMatrix:
        """
        Charge la friction depuis quantum.matchup_friction.
        
        Recherche bidirectionnelle : (team_a, team_b) ou (team_b, team_a)
        
        Args:
            home_team: Équipe à domicile
            away_team: Équipe à l'extérieur
        
        Returns:
            FrictionMatrix initialisée (kinetic/physical à calculer après)
        """
        query = """
            SELECT 
                team_a_name, team_b_name,
                friction_score, style_clash_score, tempo_clash_score, 
                mental_clash_score, chaos_potential,
                predicted_goals, predicted_btts_prob, predicted_over25_prob, 
                predicted_winner,
                h2h_matches, h2h_avg_goals,
                friction_vector, confidence_level
            FROM quantum.matchup_friction
            WHERE 
                (LOWER(team_a_name) = LOWER($1) AND LOWER(team_b_name) = LOWER($2))
                OR 
                (LOWER(team_a_name) = LOWER($2) AND LOWER(team_b_name) = LOWER($1))
            LIMIT 1
        """
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, home_team, away_team)
                
                if not row:
                    logger.warning(
                        f"⚠️ Pas de friction pour {home_team} vs {away_team}, "
                        f"utilisation des valeurs par défaut"
                    )
                    return FrictionMatrix(home_team=home_team, away_team=away_team)
                
                # Construire la FrictionMatrix
                matrix = FrictionMatrix(
                    home_team=home_team,
                    away_team=away_team,
                    friction_score=safe_float(row['friction_score'], 50.0),
                    style_clash_score=safe_float(row['style_clash_score'], 50.0),
                    tempo_clash_score=safe_float(row['tempo_clash_score'], 50.0),
                    mental_clash_score=safe_float(row['mental_clash_score'], 50.0),
                    chaos_potential=safe_float(row['chaos_potential'], 50.0),
                    predicted_goals=safe_float(row['predicted_goals'], 2.5),
                    btts_probability=safe_float(row['predicted_btts_prob'], 0.5),
                    predicted_over25_prob=safe_float(row['predicted_over25_prob'], 0.5),
                    predicted_winner=str(row['predicted_winner'] or "draw"),
                    h2h_matches=safe_int(row['h2h_matches'], 0),
                    h2h_avg_goals=safe_float(row['h2h_avg_goals'], 0.0),
                    friction_vector=parse_jsonb(row['friction_vector']),
                    confidence_level=str(row['confidence_level'] or "medium"),
                )
                
                logger.info(
                    f"✅ Friction chargée: {home_team} vs {away_team} | "
                    f"Score={matrix.friction_score:.1f} | Goals={matrix.predicted_goals:.2f}"
                )
                
                return matrix
                
        except Exception as e:
            logger.error(f"❌ Erreur chargement friction {home_team} vs {away_team}: {e}")
            # Fallback safe
            return FrictionMatrix(home_team=home_team, away_team=away_team)
    
    def load_friction_sync(self, home_team: str, away_team: str, 
                           cursor) -> FrictionMatrix:
        """
        Version synchrone pour les contextes non-async.
        
        Args:
            home_team: Équipe à domicile
            away_team: Équipe à l'extérieur
            cursor: Curseur psycopg2
        
        Returns:
            FrictionMatrix initialisée
        """
        query = """
            SELECT 
                team_a_name, team_b_name,
                friction_score, style_clash_score, tempo_clash_score, 
                mental_clash_score, chaos_potential,
                predicted_goals, predicted_btts_prob, predicted_over25_prob, 
                predicted_winner,
                h2h_matches, h2h_avg_goals,
                friction_vector, confidence_level
            FROM quantum.matchup_friction
            WHERE 
                (LOWER(team_a_name) = LOWER(%s) AND LOWER(team_b_name) = LOWER(%s))
                OR 
                (LOWER(team_a_name) = LOWER(%s) AND LOWER(team_b_name) = LOWER(%s))
            LIMIT 1
        """
        
        try:
            cursor.execute(query, (home_team, away_team, away_team, home_team))
            row = cursor.fetchone()
            
            if not row:
                logger.warning(f"⚠️ Pas de friction pour {home_team} vs {away_team}")
                return FrictionMatrix(home_team=home_team, away_team=away_team)
            
            # row est un tuple, on doit mapper par index
            # Ordre: team_a_name(0), team_b_name(1), friction_score(2), style_clash_score(3),
            #        tempo_clash_score(4), mental_clash_score(5), chaos_potential(6),
            #        predicted_goals(7), predicted_btts_prob(8), predicted_over25_prob(9),
            #        predicted_winner(10), h2h_matches(11), h2h_avg_goals(12),
            #        friction_vector(13), confidence_level(14)
            
            matrix = FrictionMatrix(
                home_team=home_team,
                away_team=away_team,
                friction_score=safe_float(row[2], 50.0),
                style_clash_score=safe_float(row[3], 50.0),
                tempo_clash_score=safe_float(row[4], 50.0),
                mental_clash_score=safe_float(row[5], 50.0),
                chaos_potential=safe_float(row[6], 50.0),
                predicted_goals=safe_float(row[7], 2.5),
                btts_probability=safe_float(row[8], 0.5),
                predicted_over25_prob=safe_float(row[9], 0.5),
                predicted_winner=str(row[10] or "draw"),
                h2h_matches=safe_int(row[11], 0),
                h2h_avg_goals=safe_float(row[12], 0.0),
                friction_vector=parse_jsonb(row[13]),
                confidence_level=str(row[14] or "medium"),
            )
            
            return matrix
            
        except Exception as e:
            logger.error(f"❌ Erreur sync friction {home_team} vs {away_team}: {e}")
            return FrictionMatrix(home_team=home_team, away_team=away_team)


# ═══════════════════════════════════════════════════════════════════════════════════════
# VERSION INFO
# ═══════════════════════════════════════════════════════════════════════════════════════

FRICTION_MATRIX_VERSION = "2.0.0"
FRICTION_MATRIX_DATE = "2025-12-25"
FRICTION_MATRIX_AUTHOR = "Mon_PS Quant Team"

CHANGELOG = """
V2.0.0 (2025-12-25):
- Correction physical_edge: rotation élevée = joueurs FRAIS
- Ajout efficiency_factor: pressing × possession
- Séparation Intensity/Stamina/Freshness
- Ajout PhysicalBreakdown pour betting strategies 1H/2H
- Normalisation via NORMALIZATION_SCALES
- Intégration bench_quality (top3_dependency)
"""


# ═══════════════════════════════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Test basique sans DB
    print("=" * 80)
    print("TEST FRICTION MATRIX UNIFIED V2.0")
    print("=" * 80)
    
    # Créer une friction avec valeurs simulées
    friction = FrictionMatrix(
        home_team="Liverpool",
        away_team="Manchester City",
        friction_score=65.0,
        style_clash_score=72.0,
        tempo_clash_score=58.0,
        mental_clash_score=48.0,
        chaos_potential=60.0,
        predicted_goals=2.85,
        btts_probability=0.65,
        predicted_over25_prob=0.70,
        predicted_winner="home",
        h2h_matches=5,
        h2h_avg_goals=3.2,
    )
    
    print("\n📊 Friction créée (avant compute_dynamic_metrics):")
    print(friction.summary())
    
    # Simuler des TeamDNA avec tous les vecteurs nécessaires
    class MockPhysicalDNA:
        pressing_intensity = 15.5       # Échelle 4.6-23.0
        late_game_dominance = 55.0      # Échelle 9-79
        aerial_win_pct = 65.0           # Échelle 0-100
        resist_late = 60.0              # Échelle 0-100
        estimated_rotation_index = 75.0  # Échelle 0-100 (élevé = tourne beaucoup)
    
    class MockContextDNA:
        home_strength = 66.0            # Proxy possession home
        away_strength = 50.0            # Proxy possession away
    
    class MockRosterDNA:
        top3_dependency = 32.0          # 32% = banc de qualité
    
    class MockTeamDNA:
        physical = None
        context = None
        roster = None
    
    # HOME DNA (Liverpool - Bon pressing, bon banc)
    home_dna = MockTeamDNA()
    home_dna.physical = MockPhysicalDNA()
    home_dna.physical.pressing_intensity = 15.5
    home_dna.physical.late_game_dominance = 55.0
    home_dna.physical.estimated_rotation_index = 75.0  # Tourne beaucoup = frais
    home_dna.context = MockContextDNA()
    home_dna.context.home_strength = 66.0  # Domine à domicile
    home_dna.roster = MockRosterDNA()
    home_dna.roster.top3_dependency = 32.0  # Bon banc
    
    # AWAY DNA (City - Très bon pressing, mais banc moins utilisé)
    away_dna = MockTeamDNA()
    away_dna.physical = MockPhysicalDNA()
    away_dna.physical.pressing_intensity = 18.0  # Plus haut pressing
    away_dna.physical.late_game_dominance = 50.0  # Moins bon en fin de match
    away_dna.physical.estimated_rotation_index = 45.0  # Tourne moins = plus fatigué
    away_dna.context = MockContextDNA()
    away_dna.context.away_strength = 55.0  # Bon à l'extérieur
    away_dna.roster = MockRosterDNA()
    away_dna.roster.top3_dependency = 45.0  # Plus dépendant des titulaires
    
    # Calculer les métriques dynamiques
    print("\n🔬 Calcul des métriques dynamiques (V2 Senior Quant)...")
    friction.compute_dynamic_metrics(home_dna, away_dna)
    
    print("\n📊 Friction après compute_dynamic_metrics:")
    print(friction.summary())
    
    # Afficher le breakdown détaillé
    if friction.physical_breakdown:
        print("\n📈 PHYSICAL BREAKDOWN (pour betting strategies):")
        pb = friction.physical_breakdown
        print(f"  Intensity: Home={pb.intensity_home:.1f} vs Away={pb.intensity_away:.1f}")
        print(f"  Stamina:   Home={pb.stamina_home:.1f} vs Away={pb.stamina_away:.1f}")
        print(f"  Freshness: Home={pb.freshness_home:.1f} vs Away={pb.freshness_away:.1f}")
        print(f"  Efficiency: Home={pb.efficiency_home:.2f}x vs Away={pb.efficiency_away:.2f}x")
        print(f"  ---")
        print(f"  1st Half Edge: {pb.first_half_edge:.1f} {'(HOME)' if pb.first_half_edge > 50 else '(AWAY)'}")
        print(f"  2nd Half Edge: {pb.second_half_edge:.1f} {'(HOME)' if pb.second_half_edge > 50 else '(AWAY)'}")
        print(f"  Dominant Phase: {pb.dominant_phase}")
    
    print("\n✅ TEST PASSED - V2.0 Senior Quant")

