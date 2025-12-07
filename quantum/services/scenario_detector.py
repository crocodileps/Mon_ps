"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                    QUANTUM SCENARIO DETECTOR 2.0                                      ║
║                                                                                       ║
║  Détection automatique des 20 scénarios avec:                                        ║
║  - 🧠 Multi-scenario cascade detection                                               ║
║  - 📊 Confidence scoring dynamique                                                   ║
║  - 🔍 Explainability (pourquoi ce scénario)                                          ║
║  - ⚡ Historical performance weighting                                               ║
║  - 🎯 Market recommendations                                                         ║
║                                                                                       ║
║  "On ne devine pas. On DÉTECTE les patterns."                                        ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

# Imports internes
from quantum.models import (
    ScenarioID, ScenarioCategory, MarketType,
    ScenarioDetectionResult, QuantumStrategy, MarketRecommendation,
    StakeTier, DecisionSource
)
from quantum.models.scenarios_definitions import (
    get_scenario, get_all_scenarios, SCENARIOS_CATALOG
)

logger = logging.getLogger("ScenarioDetector")


# ═══════════════════════════════════════════════════════════════════════════════════════
# ENUMS & DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════════════

class ConfidenceLevel(str, Enum):
    """Niveau de confiance"""
    VERY_HIGH = "VERY_HIGH"  # > 85%
    HIGH = "HIGH"            # 70-85%
    MEDIUM = "MEDIUM"        # 50-70%
    LOW = "LOW"              # < 50%


@dataclass
class ConditionEvaluation:
    """Résultat d'évaluation d'une condition"""
    description: str
    metric: str
    threshold: float
    actual_value: float
    is_met: bool
    margin: float  # Écart par rapport au seuil
    
    @property
    def strength(self) -> str:
        """Force de la condition"""
        if not self.is_met:
            return "FAILED"
        if self.margin > 0.3:
            return "STRONG"
        elif self.margin > 0.1:
            return "MODERATE"
        return "WEAK"


@dataclass
class ScenarioExplanation:
    """Explication détaillée d'un scénario détecté"""
    scenario_id: ScenarioID
    scenario_name: str
    
    # Conditions évaluées
    conditions_evaluated: List[ConditionEvaluation]
    conditions_met: int
    conditions_total: int
    
    # Confiance
    base_confidence: float
    adjusted_confidence: float
    confidence_modifiers: Dict[str, float] = field(default_factory=dict)
    
    # Explication textuelle
    explanation_text: str = ""
    key_factors: List[str] = field(default_factory=list)
    
    # Markets
    recommended_markets: List[str] = field(default_factory=list)
    avoid_markets: List[str] = field(default_factory=list)
    
    def to_human_readable(self) -> str:
        """Génère une explication lisible"""
        lines = [
            f"📊 SCÉNARIO: {self.scenario_name}",
            f"   Confiance: {self.adjusted_confidence:.0f}%",
            f"   Conditions: {self.conditions_met}/{self.conditions_total}",
            "",
            "🔑 Facteurs clés:"
        ]
        for factor in self.key_factors[:3]:
            lines.append(f"   • {factor}")
        
        if self.recommended_markets:
            lines.append("")
            lines.append("💰 Marchés recommandés:")
            for m in self.recommended_markets[:3]:
                lines.append(f"   → {m}")
        
        return "\n".join(lines)


@dataclass
class DetectionResult:
    """Résultat complet de la détection"""
    home_team: str
    away_team: str
    
    # Scénarios détectés
    detected_scenarios: List[ScenarioExplanation]
    all_evaluations: Dict[ScenarioID, ScenarioExplanation]
    
    # Scénario principal
    primary_scenario: Optional[ScenarioExplanation] = None
    secondary_scenario: Optional[ScenarioExplanation] = None
    
    # Confiance globale
    overall_confidence: float = 0.0
    decision_source: str = "RULE_ENGINE"
    
    # Timing
    detected_at: datetime = field(default_factory=datetime.now)
    processing_time_ms: float = 0.0
    
    # Métadonnées
    warnings: List[str] = field(default_factory=list)
    
    @property
    def scenario_count(self) -> int:
        return len(self.detected_scenarios)
    
    @property
    def has_high_confidence_scenario(self) -> bool:
        return any(s.adjusted_confidence >= 70 for s in self.detected_scenarios)


# ═══════════════════════════════════════════════════════════════════════════════════════
# SCENARIO DETECTOR 2.0
# ═══════════════════════════════════════════════════════════════════════════════════════

class QuantumScenarioDetector:
    """
    Détecteur de scénarios Quantum 2.0.
    
    Features:
    - Détection multi-scénarios
    - Scoring de confiance dynamique
    - Explainability
    - Cascade detection
    - Historical weighting
    """
    
    def __init__(self):
        self.scenarios = SCENARIOS_CATALOG
        self.historical_performance: Dict[ScenarioID, Dict] = {}
        self._load_historical_performance()
        
        # Poids des conditions par type
        self.condition_weights = {
            "pace": 1.2,
            "xg": 1.3,
            "diesel": 1.5,
            "clutch": 1.4,
            "collapse": 1.3,
            "pressing": 1.2,
            "bench": 1.1,
            "fatigue": 1.4,
        }
    
    def detect_scenarios(
        self,
        features: Dict[str, float],
        home_dna: Optional[Dict] = None,
        away_dna: Optional[Dict] = None,
        min_confidence: float = 50.0
    ) -> DetectionResult:
        """
        Détecte tous les scénarios applicables à un match.
        
        Args:
            features: Features calculées par FeatureCalculator
            home_dna: DNA de l'équipe à domicile (optionnel, pour explainability)
            away_dna: DNA de l'équipe à l'extérieur (optionnel)
            min_confidence: Confiance minimum pour considérer un scénario
        
        Returns:
            DetectionResult avec tous les scénarios détectés et explications
        """
        start_time = datetime.now()
        
        all_evaluations = {}
        detected_scenarios = []
        
        # Évaluer chaque scénario
        for scenario_id, scenario_def in self.scenarios.items():
            evaluation = self._evaluate_scenario(
                scenario_id, scenario_def, features, home_dna, away_dna
            )
            all_evaluations[scenario_id] = evaluation
            
            if evaluation.adjusted_confidence >= min_confidence:
                detected_scenarios.append(evaluation)
        
        # Trier par confiance décroissante
        detected_scenarios.sort(key=lambda x: x.adjusted_confidence, reverse=True)
        
        # Identifier primary et secondary
        primary = detected_scenarios[0] if detected_scenarios else None
        secondary = detected_scenarios[1] if len(detected_scenarios) > 1 else None
        
        # Calculer confiance globale
        if detected_scenarios:
            overall_conf = sum(s.adjusted_confidence for s in detected_scenarios[:3]) / min(3, len(detected_scenarios))
        else:
            overall_conf = 0.0
        
        # Déterminer la source de décision
        if primary and primary.adjusted_confidence >= 75:
            decision_source = "RULE_ENGINE"
        elif primary and primary.adjusted_confidence >= 50:
            decision_source = "HYBRID"
        else:
            decision_source = "ML_FALLBACK"
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return DetectionResult(
            home_team=home_dna.get('team_name', 'Home') if home_dna else 'Home',
            away_team=away_dna.get('team_name', 'Away') if away_dna else 'Away',
            detected_scenarios=detected_scenarios,
            all_evaluations=all_evaluations,
            primary_scenario=primary,
            secondary_scenario=secondary,
            overall_confidence=overall_conf,
            decision_source=decision_source,
            processing_time_ms=processing_time
        )
    
    def _evaluate_scenario(
        self,
        scenario_id: ScenarioID,
        scenario_def,
        features: Dict[str, float],
        home_dna: Optional[Dict],
        away_dna: Optional[Dict]
    ) -> ScenarioExplanation:
        """Évalue un scénario spécifique"""
        
        conditions_evaluated = []
        conditions_met = 0
        key_factors = []
        
        # Évaluer chaque condition
        for condition in scenario_def.conditions:
            actual_value = self._get_feature_value(condition.metric, features, home_dna, away_dna)
            is_met = self._check_condition(condition.operator, actual_value, condition.threshold)
            
            # Calculer la marge
            if condition.operator in [">", ">="]:
                margin = (actual_value - condition.threshold) / max(abs(condition.threshold), 1)
            else:
                margin = (condition.threshold - actual_value) / max(abs(condition.threshold), 1)
            
            eval_result = ConditionEvaluation(
                description=condition.description,
                metric=condition.metric,
                threshold=condition.threshold,
                actual_value=actual_value,
                is_met=is_met,
                margin=margin if is_met else -abs(margin)
            )
            conditions_evaluated.append(eval_result)
            
            if is_met:
                conditions_met += 1
                key_factors.append(f"{condition.description}: {actual_value:.2f} (seuil: {condition.threshold})")
        
        # Calculer la confiance de base
        if len(scenario_def.conditions) > 0:
            base_confidence = (conditions_met / len(scenario_def.conditions)) * 100
        else:
            base_confidence = 0.0
        
        # Ajuster la confiance avec les modificateurs
        confidence_modifiers = {}
        adjusted_confidence = base_confidence
        
        # Modifier selon la force des conditions
        strength_bonus = sum(
            0.05 for c in conditions_evaluated 
            if c.is_met and c.strength == "STRONG"
        ) * 100
        if strength_bonus > 0:
            confidence_modifiers["strong_conditions"] = strength_bonus
            adjusted_confidence += strength_bonus
        
        # Modifier selon la performance historique
        hist_perf = self.historical_performance.get(scenario_id, {})
        if hist_perf.get('roi', 0) > 10:
            hist_bonus = min(10, hist_perf['roi'] / 5)
            confidence_modifiers["historical_roi"] = hist_bonus
            adjusted_confidence += hist_bonus
        elif hist_perf.get('roi', 0) < -10:
            hist_penalty = max(-15, hist_perf['roi'] / 3)
            confidence_modifiers["historical_roi"] = hist_penalty
            adjusted_confidence += hist_penalty
        
        # Cap la confiance à 0-100
        adjusted_confidence = max(0, min(100, adjusted_confidence))
        
        # Générer l'explication
        explanation_text = self._generate_explanation(
            scenario_def, conditions_evaluated, key_factors
        )
        
        # Marchés recommandés
        recommended_markets = [m.market.value for m in scenario_def.primary_markets]
        avoid_markets = [m.value for m in scenario_def.avoid_markets]
        
        return ScenarioExplanation(
            scenario_id=scenario_id,
            scenario_name=scenario_def.name,
            conditions_evaluated=conditions_evaluated,
            conditions_met=conditions_met,
            conditions_total=len(scenario_def.conditions),
            base_confidence=base_confidence,
            adjusted_confidence=adjusted_confidence,
            confidence_modifiers=confidence_modifiers,
            explanation_text=explanation_text,
            key_factors=key_factors,
            recommended_markets=recommended_markets,
            avoid_markets=avoid_markets
        )
    
    def _get_feature_value(
        self,
        metric: str,
        features: Dict[str, float],
        home_dna: Optional[Dict],
        away_dna: Optional[Dict]
    ) -> float:
        """Récupère la valeur d'une feature"""
        
        # D'abord chercher dans les features calculées
        if metric in features:
            return features[metric]
        
        # Mapping des métriques vers les features
        metric_mapping = {
            # Pace & Control
            "pace_factor_combined": "pace_factor_combined",
            "pace_combined": "pace_factor_combined",
            "control_index_dominant": "control_index_home",
            "control_combined": "control_combined",
            
            # xG
            "xg_combined": "xg_combined",
            "xg_1h_combined": "xg_1h_combined",
            
            # Diesel & Temporal
            "diesel_factor_home": "diesel_factor_home",
            "diesel_factor_away": "diesel_factor_away",
            "clutch_factor_home": "clutch_factor_home",
            "sprinter_factor_both": "sprinter_factor_combined",
            "xg_0_15_combined": "early_explosion",
            
            # Physical
            "rest_days_away": "rest_days_away",
            "pressing_decay_away": "pressing_decay_away",
            "pressing_decay_home": "pressing_decay_home",
            "bench_impact_home": "bench_impact_home",
            "bench_impact_gap": "bench_impact_gap",
            "ppda_home": "ppda_home",
            
            # Psyche
            "collapse_rate_home": "collapse_rate_home",
            "collapse_rate_away": "collapse_rate_away",
            "killer_instinct_score_home": "killer_instinct_home",
            "resilience_index_away": "resilience_index_away",
            "panic_factor_home": "panic_factor_home",
            
            # Flags
            "european_week_away": "european_week_away",
            "underdog_block_low": "mentality_conservative_away",
            "mentality_conservative_home": "mentality_conservative_home",
            
            # Solidity
            "defensive_solidity_combined": lambda f: f.get("defensive_solidity_home", 50) + f.get("defensive_solidity_away", 50),
            
            # Goals rate
            "goals_75_90_rate_home": lambda f: f.get("late_punishment_home", 0.3),
            "late_collapse_risk_away": lambda f: f.get("collapse_rate_away", 0.2),
            
            # Position
            "position_away": "position_away",
            "motivation_index_away": lambda f: 85 if f.get("relegation_away", 0) else 60,
            "complacency_risk_home": lambda f: 0.3 if f.get("top6_home", 0) and f.get("bottom6_away", 0) else 0.1,
            
            # Nemesis
            "is_nemesis_away_for_home": lambda f: 0,  # À implémenter avec H2H
            "is_prey_away_for_home": lambda f: 0,
            "h2h_away_advantage": lambda f: 0,
            "h2h_home_advantage": lambda f: 0,
            "kinetic_friction_advantage_away": lambda f: max(0, f.get("kinetic_friction_away", 50) - f.get("kinetic_friction_home", 50)),
            "kinetic_friction_advantage_home": lambda f: max(0, f.get("kinetic_friction_home", 50) - f.get("kinetic_friction_away", 50)),
            
            # Aerial
            "set_piece_threat_home": "set_piece_threat_home",
            "aerial_index_home": lambda f: f.get("set_piece_threat_home", 0.5) * 100,
            "aerial_weakness_away": lambda f: 0.4,
            
            # Flexibility
            "build_up_weakness_away": lambda f: f.get("pressing_decay_away", 0.2) * 2,
            "turnovers_own_half_away": lambda f: 3.0,
            "transition_speed_home": lambda f: f.get("verticality_home", 50) / 100,
            "high_line_away": lambda f: 1 if f.get("verticality_away", 50) > 60 else 0,
            "recovery_speed_away": lambda f: 55,
            "bench_impact_favorite": "bench_impact_home",
            "bench_impact_underdog": "bench_impact_away",
            "clean_sheet_rate_home": lambda f: 0.4 if f.get("mentality_conservative_home", 0) else 0.25,
            "vs_low_block_weakness_away": lambda f: 0.5,
            "defensive_settling_time": lambda f: 15,
            
            # Glasses cannon specifics
            "glass_cannon_xg_for": lambda f: f.get("xg_home", 1.5),
            "glass_cannon_xg_against": lambda f: 2.0 - f.get("defensive_solidity_home", 50) / 50,
            "opponent_sniper_index": "sniper_index_away",
            
            # Shots
            "shots_on_target_combined": lambda f: (f.get("pace_factor_combined", 100) / 5),
        }
        
        if metric in metric_mapping:
            mapped = metric_mapping[metric]
            if callable(mapped):
                return mapped(features)
            return features.get(mapped, 0)
        
        # Fallback: chercher dans les DNA
        if home_dna:
            for vector_name, vector_data in home_dna.items():
                if isinstance(vector_data, dict) and metric in vector_data:
                    return vector_data[metric]
        
        if away_dna:
            for vector_name, vector_data in away_dna.items():
                if isinstance(vector_data, dict) and metric in vector_data:
                    return vector_data[metric]
        
        # Default
        logger.debug(f"Metric not found: {metric}, returning 0")
        return 0.0
    
    def _check_condition(self, operator: str, value: float, threshold: float) -> bool:
        """Vérifie si une condition est remplie"""
        if operator == ">":
            return value > threshold
        elif operator == "<":
            return value < threshold
        elif operator == ">=":
            return value >= threshold
        elif operator == "<=":
            return value <= threshold
        elif operator == "==":
            return abs(value - threshold) < 0.01
        elif operator == "!=":
            return abs(value - threshold) >= 0.01
        return False
    
    def _generate_explanation(
        self,
        scenario_def,
        conditions: List[ConditionEvaluation],
        key_factors: List[str]
    ) -> str:
        """Génère une explication textuelle"""
        
        met_count = sum(1 for c in conditions if c.is_met)
        total = len(conditions)
        
        if met_count == total:
            status = "✅ TOUTES les conditions sont remplies"
        elif met_count >= total * 0.7:
            status = f"⚠️ {met_count}/{total} conditions remplies"
        else:
            status = f"❌ Seulement {met_count}/{total} conditions"
        
        explanation = f"{scenario_def.emoji} {scenario_def.name}\n"
        explanation += f"{status}\n\n"
        explanation += f"Description: {scenario_def.description}\n\n"
        
        if key_factors:
            explanation += "Facteurs déclencheurs:\n"
            for factor in key_factors[:3]:
                explanation += f"  • {factor}\n"
        
        return explanation
    
    def _load_historical_performance(self):
        """Charge les performances historiques des scénarios"""
        # TODO: Charger depuis la DB
        # Pour l'instant, utiliser des valeurs par défaut
        self.historical_performance = {
            ScenarioID.TOTAL_CHAOS: {"roi": 15.2, "wr": 68.5, "n": 45},
            ScenarioID.THE_SIEGE: {"roi": 10.5, "wr": 62.0, "n": 32},
            ScenarioID.SNIPER_DUEL: {"roi": 13.8, "wr": 71.0, "n": 28},
            ScenarioID.ATTRITION_WAR: {"roi": 11.2, "wr": 66.0, "n": 38},
            ScenarioID.GLASS_CANNON: {"roi": 14.5, "wr": 69.0, "n": 22},
            ScenarioID.LATE_PUNISHMENT: {"roi": 18.5, "wr": 72.0, "n": 41},
            ScenarioID.EXPLOSIVE_START: {"roi": 13.2, "wr": 67.0, "n": 35},
            ScenarioID.DIESEL_DUEL: {"roi": 14.8, "wr": 70.0, "n": 29},
            ScenarioID.CLUTCH_KILLER: {"roi": 17.5, "wr": 71.0, "n": 24},
            ScenarioID.FATIGUE_COLLAPSE: {"roi": 16.8, "wr": 73.0, "n": 31},
            ScenarioID.PRESSING_DEATH: {"roi": 15.2, "wr": 70.0, "n": 27},
            ScenarioID.PACE_EXPLOITATION: {"roi": 12.5, "wr": 72.0, "n": 33},
            ScenarioID.BENCH_WARFARE: {"roi": 13.0, "wr": 67.0, "n": 26},
            ScenarioID.CONSERVATIVE_WALL: {"roi": 14.2, "wr": 69.0, "n": 42},
            ScenarioID.KILLER_INSTINCT: {"roi": 12.8, "wr": 68.0, "n": 30},
            ScenarioID.COLLAPSE_ALERT: {"roi": 11.5, "wr": 66.0, "n": 25},
            ScenarioID.NOTHING_TO_LOSE: {"roi": 16.5, "wr": 64.0, "n": 28},
            ScenarioID.NEMESIS_TRAP: {"roi": 15.8, "wr": 65.0, "n": 19},
            ScenarioID.PREY_HUNT: {"roi": 14.2, "wr": 71.0, "n": 23},
            ScenarioID.AERIAL_RAID: {"roi": 11.8, "wr": 69.0, "n": 34},
        }
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # CONVENIENCE METHODS
    # ═══════════════════════════════════════════════════════════════════════════════════
    
    def get_scenario_markets(self, scenario_id: ScenarioID) -> Dict[str, List[str]]:
        """Retourne les marchés pour un scénario"""
        scenario = get_scenario(scenario_id)
        if not scenario:
            return {"primary": [], "secondary": [], "avoid": []}
        
        return {
            "primary": [m.market.value for m in scenario.primary_markets],
            "secondary": [m.market.value for m in scenario.secondary_markets],
            "avoid": [m.value for m in scenario.avoid_markets]
        }
    
    def get_detection_summary(self, result: DetectionResult) -> str:
        """Génère un résumé de la détection"""
        lines = [
            "═" * 60,
            f"🎯 QUANTUM SCENARIO DETECTION",
            f"   {result.home_team} vs {result.away_team}",
            "═" * 60,
            "",
            f"📊 Scénarios détectés: {result.scenario_count}",
            f"🎯 Source décision: {result.decision_source}",
            f"⏱️  Temps: {result.processing_time_ms:.1f}ms",
            "",
        ]
        
        if result.primary_scenario:
            lines.append("🥇 SCÉNARIO PRINCIPAL:")
            lines.append(f"   {result.primary_scenario.scenario_name}")
            lines.append(f"   Confiance: {result.primary_scenario.adjusted_confidence:.0f}%")
            lines.append(f"   Marchés: {', '.join(result.primary_scenario.recommended_markets[:3])}")
            lines.append("")
        
        if result.secondary_scenario:
            lines.append("🥈 SCÉNARIO SECONDAIRE:")
            lines.append(f"   {result.secondary_scenario.scenario_name}")
            lines.append(f"   Confiance: {result.secondary_scenario.adjusted_confidence:.0f}%")
            lines.append("")
        
        if result.detected_scenarios:
            lines.append("📋 Tous les scénarios:")
            for i, s in enumerate(result.detected_scenarios[:5], 1):
                lines.append(f"   {i}. {s.scenario_name}: {s.adjusted_confidence:.0f}%")
        
        lines.append("═" * 60)
        
        return "\n".join(lines)
