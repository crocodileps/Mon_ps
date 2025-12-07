"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                    QUANTUM MONTE CARLO VALIDATOR 2.0                                  ║
║                                                                                       ║
║  Validation Hedge Fund Grade des scénarios par simulation Monte Carlo.               ║
║                                                                                       ║
║  Features:                                                                           ║
║  - 🎲 10,000+ simulations par scénario                                               ║
║  - 📊 Intervalles de confiance (95%, 99%)                                            ║
║  - 🔬 Stress testing des conditions                                                  ║
║  - 📈 Distribution des probabilités                                                  ║
║  - ⚠️ Détection des scénarios fragiles vs robustes                                   ║
║  - 🎯 Kelly Criterion optimisé par simulation                                        ║
║                                                                                       ║
║  "La confiance sans validation = de l'arrogance. Monte Carlo = humilité scientifique"║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

import random
import math
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logger = logging.getLogger("MonteCarloValidator")


# ═══════════════════════════════════════════════════════════════════════════════════════
# ENUMS & DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════════════

class RobustnessLevel(str, Enum):
    """Niveau de robustesse d'un scénario"""
    ROCK_SOLID = "ROCK_SOLID"      # > 90% des simulations OK
    ROBUST = "ROBUST"              # 75-90%
    MODERATE = "MODERATE"          # 50-75%
    FRAGILE = "FRAGILE"            # 25-50%
    UNRELIABLE = "UNRELIABLE"      # < 25%


class StressTestResult(str, Enum):
    """Résultat du stress test"""
    PASSED = "PASSED"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


@dataclass
class ConfidenceInterval:
    """Intervalle de confiance statistique"""
    mean: float
    std_dev: float
    ci_95_lower: float
    ci_95_upper: float
    ci_99_lower: float
    ci_99_upper: float
    min_value: float
    max_value: float
    median: float
    
    @property
    def ci_95_width(self) -> float:
        return self.ci_95_upper - self.ci_95_lower
    
    @property
    def is_tight(self) -> bool:
        """Intervalle serré = haute précision"""
        return self.ci_95_width < self.mean * 0.2  # < 20% de la moyenne


@dataclass
class SimulationResult:
    """Résultat d'une simulation individuelle"""
    iteration: int
    confidence: float
    conditions_met: int
    conditions_total: int
    edge: float
    expected_value: float
    noise_applied: Dict[str, float] = field(default_factory=dict)


@dataclass
class MonteCarloValidation:
    """Résultat complet de la validation Monte Carlo"""
    scenario_id: str
    scenario_name: str
    
    # Paramètres de simulation
    n_simulations: int
    noise_level: float  # % de bruit ajouté
    
    # Résultats bruts
    simulations: List[SimulationResult] = field(default_factory=list)
    
    # Statistiques de confiance
    confidence_stats: Optional[ConfidenceInterval] = None
    
    # Statistiques d'edge
    edge_stats: Optional[ConfidenceInterval] = None
    
    # Statistiques EV
    ev_stats: Optional[ConfidenceInterval] = None
    
    # Robustesse
    success_rate: float = 0.0  # % de simulations avec confiance > seuil
    robustness: RobustnessLevel = RobustnessLevel.MODERATE
    
    # Stress test
    stress_test_result: StressTestResult = StressTestResult.PASSED
    stress_test_details: Dict[str, Any] = field(default_factory=dict)
    
    # Kelly optimisé
    kelly_optimal: float = 0.0
    kelly_half: float = 0.0  # Conservateur
    kelly_quarter: float = 0.0  # Très conservateur
    
    # Timing
    simulation_time_ms: float = 0.0
    validated_at: datetime = field(default_factory=datetime.now)
    
    # Verdict final
    is_validated: bool = False
    validation_score: float = 0.0  # 0-100
    warnings: List[str] = field(default_factory=list)
    
    def to_summary(self) -> str:
        """Génère un résumé lisible"""
        lines = [
            f"🎲 MONTE CARLO VALIDATION: {self.scenario_name}",
            "=" * 50,
            f"Simulations: {self.n_simulations:,}",
            f"Bruit appliqué: ±{self.noise_level*100:.0f}%",
            "",
            "📊 CONFIANCE:",
            f"   Moyenne: {self.confidence_stats.mean:.1f}%",
            f"   IC 95%: [{self.confidence_stats.ci_95_lower:.1f}%, {self.confidence_stats.ci_95_upper:.1f}%]",
            f"   Écart-type: {self.confidence_stats.std_dev:.2f}",
            "",
            "💰 EDGE:",
            f"   Moyenne: {self.edge_stats.mean*100:.2f}%",
            f"   IC 95%: [{self.edge_stats.ci_95_lower*100:.2f}%, {self.edge_stats.ci_95_upper*100:.2f}%]",
            "",
            f"🎯 Taux de succès: {self.success_rate*100:.1f}%",
            f"🛡️ Robustesse: {self.robustness.value}",
            f"🧪 Stress Test: {self.stress_test_result.value}",
            "",
            "💵 KELLY CRITERION:",
            f"   Optimal: {self.kelly_optimal*100:.2f}% du bankroll",
            f"   Demi-Kelly: {self.kelly_half*100:.2f}%",
            f"   Quart-Kelly: {self.kelly_quarter*100:.2f}%",
            "",
            f"✅ Score validation: {self.validation_score:.0f}/100",
            f"⏱️ Temps: {self.simulation_time_ms:.1f}ms",
        ]
        
        if self.warnings:
            lines.append("")
            lines.append("⚠️ WARNINGS:")
            for w in self.warnings:
                lines.append(f"   • {w}")
        
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════════════
# MONTE CARLO VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════════════

class MonteCarloValidator:
    """
    Validateur Monte Carlo pour les scénarios Quantum.
    
    Simule des milliers de variations pour valider la robustesse
    des détections de scénarios.
    """
    
    def __init__(
        self,
        n_simulations: int = 10000,
        noise_level: float = 0.15,
        confidence_threshold: float = 50.0,
        edge_threshold: float = 0.03,
        parallel: bool = True
    ):
        """
        Args:
            n_simulations: Nombre de simulations (10000 par défaut)
            noise_level: Niveau de bruit (15% = ±15% sur chaque feature)
            confidence_threshold: Seuil de confiance minimum
            edge_threshold: Seuil d'edge minimum (3%)
            parallel: Utiliser le parallélisme
        """
        self.n_simulations = n_simulations
        self.noise_level = noise_level
        self.confidence_threshold = confidence_threshold
        self.edge_threshold = edge_threshold
        self.parallel = parallel
        
        # Cache des validations
        self._validation_cache: Dict[str, MonteCarloValidation] = {}
    
    def validate_scenario(
        self,
        scenario_evaluation,  # ScenarioExplanation from detector
        features: Dict[str, float],
        odds: float = 2.0
    ) -> MonteCarloValidation:
        """
        Valide un scénario détecté par simulation Monte Carlo.
        
        Args:
            scenario_evaluation: Résultat de l'évaluation du scénario
            features: Features du match
            odds: Cotes du marché
        
        Returns:
            MonteCarloValidation avec statistiques complètes
        """
        start_time = datetime.now()
        
        # Exécuter les simulations
        if self.parallel and self.n_simulations >= 1000:
            simulations = self._run_parallel_simulations(
                scenario_evaluation, features, odds
            )
        else:
            simulations = self._run_simulations(
                scenario_evaluation, features, odds
            )
        
        # Calculer les statistiques
        confidence_values = [s.confidence for s in simulations]
        edge_values = [s.edge for s in simulations]
        ev_values = [s.expected_value for s in simulations]
        
        confidence_stats = self._calculate_confidence_interval(confidence_values)
        edge_stats = self._calculate_confidence_interval(edge_values)
        ev_stats = self._calculate_confidence_interval(ev_values)
        
        # Calculer le taux de succès
        successes = sum(
            1 for s in simulations 
            if s.confidence >= self.confidence_threshold 
            and s.edge >= self.edge_threshold
        )
        success_rate = successes / len(simulations)
        
        # Déterminer la robustesse
        robustness = self._determine_robustness(success_rate, confidence_stats)
        
        # Stress test
        stress_result, stress_details = self._run_stress_test(
            scenario_evaluation, features, odds
        )
        
        # Calculer Kelly optimal
        kelly_optimal, kelly_half, kelly_quarter = self._calculate_kelly(
            edge_stats.mean, confidence_stats.mean / 100, odds
        )
        
        # Score de validation final
        validation_score = self._calculate_validation_score(
            success_rate, confidence_stats, edge_stats, stress_result
        )
        
        # Warnings
        warnings = self._generate_warnings(
            success_rate, confidence_stats, edge_stats, stress_result
        )
        
        # Temps de simulation
        simulation_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return MonteCarloValidation(
            scenario_id=scenario_evaluation.scenario_id.value,
            scenario_name=scenario_evaluation.scenario_name,
            n_simulations=self.n_simulations,
            noise_level=self.noise_level,
            simulations=simulations[:100],  # Garder seulement 100 pour mémoire
            confidence_stats=confidence_stats,
            edge_stats=edge_stats,
            ev_stats=ev_stats,
            success_rate=success_rate,
            robustness=robustness,
            stress_test_result=stress_result,
            stress_test_details=stress_details,
            kelly_optimal=kelly_optimal,
            kelly_half=kelly_half,
            kelly_quarter=kelly_quarter,
            simulation_time_ms=simulation_time,
            is_validated=validation_score >= 60,
            validation_score=validation_score,
            warnings=warnings
        )
    
    def _run_simulations(
        self,
        scenario_eval,
        features: Dict[str, float],
        odds: float
    ) -> List[SimulationResult]:
        """Exécute les simulations séquentiellement"""
        
        simulations = []
        
        for i in range(self.n_simulations):
            # Ajouter du bruit aux features
            noisy_features, noise_applied = self._add_noise(features)
            
            # Recalculer la confiance avec les features bruitées
            confidence, conditions_met = self._recalculate_confidence(
                scenario_eval, noisy_features
            )
            
            # Calculer l'edge et EV
            implied_prob = 1 / odds
            calc_prob = confidence / 100 * 0.6 + 0.2  # Simplified mapping
            edge = calc_prob - implied_prob
            ev = edge * odds - (1 - calc_prob)
            
            simulations.append(SimulationResult(
                iteration=i,
                confidence=confidence,
                conditions_met=conditions_met,
                conditions_total=len(scenario_eval.conditions_evaluated),
                edge=edge,
                expected_value=ev,
                noise_applied=noise_applied
            ))
        
        return simulations
    
    def _run_parallel_simulations(
        self,
        scenario_eval,
        features: Dict[str, float],
        odds: float
    ) -> List[SimulationResult]:
        """Exécute les simulations en parallèle"""
        
        # Diviser en chunks
        n_workers = min(8, self.n_simulations // 500)
        chunk_size = self.n_simulations // n_workers
        
        all_simulations = []
        
        with ThreadPoolExecutor(max_workers=n_workers) as executor:
            futures = []
            for i in range(n_workers):
                start_idx = i * chunk_size
                end_idx = start_idx + chunk_size if i < n_workers - 1 else self.n_simulations
                
                futures.append(executor.submit(
                    self._run_simulation_chunk,
                    scenario_eval, features, odds, start_idx, end_idx
                ))
            
            for future in as_completed(futures):
                all_simulations.extend(future.result())
        
        return all_simulations
    
    def _run_simulation_chunk(
        self,
        scenario_eval,
        features: Dict[str, float],
        odds: float,
        start_idx: int,
        end_idx: int
    ) -> List[SimulationResult]:
        """Exécute un chunk de simulations"""
        
        simulations = []
        
        for i in range(start_idx, end_idx):
            noisy_features, noise_applied = self._add_noise(features)
            confidence, conditions_met = self._recalculate_confidence(
                scenario_eval, noisy_features
            )
            
            implied_prob = 1 / odds
            calc_prob = min(0.95, max(0.05, confidence / 100 * 0.6 + 0.2))
            edge = calc_prob - implied_prob
            ev = edge * odds - (1 - calc_prob)
            
            simulations.append(SimulationResult(
                iteration=i,
                confidence=confidence,
                conditions_met=conditions_met,
                conditions_total=len(scenario_eval.conditions_evaluated),
                edge=edge,
                expected_value=ev,
                noise_applied={}  # Simplifié pour les chunks
            ))
        
        return simulations
    
    def _add_noise(self, features: Dict[str, float]) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Ajoute du bruit gaussien aux features"""
        
        noisy = {}
        noise_applied = {}
        
        for key, value in features.items():
            # Bruit gaussien proportionnel
            noise_factor = random.gauss(0, self.noise_level)
            noise_applied[key] = noise_factor
            
            # Appliquer le bruit
            if value != 0:
                noisy[key] = value * (1 + noise_factor)
            else:
                noisy[key] = random.gauss(0, 0.1)
            
            # Clamp les valeurs binaires
            if key.startswith("is_") or key.endswith("_flag"):
                noisy[key] = 1 if noisy[key] > 0.5 else 0
        
        return noisy, noise_applied
    
    def _recalculate_confidence(
        self,
        scenario_eval,
        noisy_features: Dict[str, float]
    ) -> Tuple[float, int]:
        """Recalcule la confiance avec les features bruitées"""
        
        conditions_met = 0
        
        for cond in scenario_eval.conditions_evaluated:
            # Récupérer la valeur bruitée
            value = noisy_features.get(cond.metric, cond.actual_value)
            
            # Vérifier la condition
            if self._check_condition(cond.metric, value, cond.threshold):
                conditions_met += 1
        
        # Calculer la confiance
        total = len(scenario_eval.conditions_evaluated)
        if total > 0:
            base_confidence = (conditions_met / total) * 100
        else:
            base_confidence = 0
        
        # Ajouter un peu de bruit à la confiance finale
        confidence = base_confidence + random.gauss(0, 5)
        confidence = max(0, min(100, confidence))
        
        return confidence, conditions_met
    
    def _check_condition(self, metric: str, value: float, threshold: float) -> bool:
        """Vérifie si une condition est remplie"""
        # Simplified: assume > operator for most conditions
        if "under" in metric.lower() or "less" in metric.lower():
            return value < threshold
        return value > threshold
    
    def _calculate_confidence_interval(self, values: List[float]) -> ConfidenceInterval:
        """Calcule l'intervalle de confiance"""
        
        n = len(values)
        mean = statistics.mean(values)
        std_dev = statistics.stdev(values) if n > 1 else 0
        
        # Z-scores
        z_95 = 1.96
        z_99 = 2.576
        
        # Standard error
        se = std_dev / math.sqrt(n) if n > 0 else 0
        
        return ConfidenceInterval(
            mean=mean,
            std_dev=std_dev,
            ci_95_lower=mean - z_95 * se,
            ci_95_upper=mean + z_95 * se,
            ci_99_lower=mean - z_99 * se,
            ci_99_upper=mean + z_99 * se,
            min_value=min(values),
            max_value=max(values),
            median=statistics.median(values)
        )
    
    def _determine_robustness(
        self,
        success_rate: float,
        confidence_stats: ConfidenceInterval
    ) -> RobustnessLevel:
        """Détermine le niveau de robustesse"""
        
        # Combiner taux de succès et stabilité
        stability_score = 1 - (confidence_stats.std_dev / max(confidence_stats.mean, 1))
        combined_score = success_rate * 0.7 + stability_score * 0.3
        
        if combined_score >= 0.90:
            return RobustnessLevel.ROCK_SOLID
        elif combined_score >= 0.75:
            return RobustnessLevel.ROBUST
        elif combined_score >= 0.50:
            return RobustnessLevel.MODERATE
        elif combined_score >= 0.25:
            return RobustnessLevel.FRAGILE
        else:
            return RobustnessLevel.UNRELIABLE
    
    def _run_stress_test(
        self,
        scenario_eval,
        features: Dict[str, float],
        odds: float
    ) -> Tuple[StressTestResult, Dict[str, Any]]:
        """Exécute un stress test avec bruit extrême"""
        
        stress_results = []
        
        # Test avec différents niveaux de bruit
        noise_levels = [0.20, 0.30, 0.40, 0.50]
        
        for noise in noise_levels:
            original_noise = self.noise_level
            self.noise_level = noise
            
            # Petit échantillon pour stress test
            simulations = self._run_simulations(scenario_eval, features, odds)
            simulations = simulations[:500]
            
            success_count = sum(
                1 for s in simulations 
                if s.confidence >= self.confidence_threshold
            )
            success_rate = success_count / len(simulations)
            
            stress_results.append({
                "noise_level": noise,
                "success_rate": success_rate,
                "avg_confidence": statistics.mean([s.confidence for s in simulations])
            })
            
            self.noise_level = original_noise
        
        # Analyser les résultats
        degradation = stress_results[0]["success_rate"] - stress_results[-1]["success_rate"]
        
        details = {
            "stress_levels": stress_results,
            "degradation": degradation,
            "worst_case_success": stress_results[-1]["success_rate"]
        }
        
        if degradation < 0.20 and stress_results[-1]["success_rate"] > 0.50:
            return StressTestResult.PASSED, details
        elif degradation < 0.40 and stress_results[-1]["success_rate"] > 0.25:
            return StressTestResult.DEGRADED, details
        else:
            return StressTestResult.FAILED, details
    
    def _calculate_kelly(
        self,
        edge: float,
        win_prob: float,
        odds: float
    ) -> Tuple[float, float, float]:
        """Calcule le Kelly Criterion optimisé"""
        
        # Kelly = (bp - q) / b
        # b = odds - 1 (profit en cas de gain)
        # p = probabilité de gain
        # q = 1 - p
        
        b = odds - 1
        p = win_prob
        q = 1 - p
        
        if b <= 0:
            return 0, 0, 0
        
        kelly = (b * p - q) / b
        
        # Clamp entre 0 et 0.25 (jamais plus de 25% du bankroll)
        kelly_optimal = max(0, min(0.25, kelly))
        kelly_half = kelly_optimal / 2
        kelly_quarter = kelly_optimal / 4
        
        return kelly_optimal, kelly_half, kelly_quarter
    
    def _calculate_validation_score(
        self,
        success_rate: float,
        confidence_stats: ConfidenceInterval,
        edge_stats: ConfidenceInterval,
        stress_result: StressTestResult
    ) -> float:
        """Calcule un score de validation global (0-100)"""
        
        score = 0
        
        # Taux de succès (40 points max)
        score += success_rate * 40
        
        # Confiance moyenne (20 points max)
        if confidence_stats.mean >= 70:
            score += 20
        elif confidence_stats.mean >= 50:
            score += 15
        elif confidence_stats.mean >= 30:
            score += 10
        
        # Edge positif (20 points max)
        if edge_stats.ci_95_lower > 0.05:
            score += 20
        elif edge_stats.ci_95_lower > 0:
            score += 15
        elif edge_stats.mean > 0:
            score += 10
        
        # Stress test (20 points max)
        if stress_result == StressTestResult.PASSED:
            score += 20
        elif stress_result == StressTestResult.DEGRADED:
            score += 10
        
        return min(100, score)
    
    def _generate_warnings(
        self,
        success_rate: float,
        confidence_stats: ConfidenceInterval,
        edge_stats: ConfidenceInterval,
        stress_result: StressTestResult
    ) -> List[str]:
        """Génère des warnings basés sur les résultats"""
        
        warnings = []
        
        if success_rate < 0.50:
            warnings.append(f"Taux de succès bas ({success_rate*100:.0f}%): scénario fragile")
        
        if confidence_stats.std_dev > 20:
            warnings.append(f"Haute variabilité (σ={confidence_stats.std_dev:.1f}): résultats instables")
        
        if not confidence_stats.is_tight:
            warnings.append("Intervalle de confiance large: précision insuffisante")
        
        if edge_stats.ci_95_lower < 0:
            warnings.append("Edge potentiellement négatif: risque de perte")
        
        if stress_result == StressTestResult.FAILED:
            warnings.append("Stress test échoué: scénario très sensible aux variations")
        
        return warnings
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # BATCH VALIDATION
    # ═══════════════════════════════════════════════════════════════════════════════════
    
    def validate_all_scenarios(
        self,
        detection_result,  # DetectionResult from detector
        features: Dict[str, float],
        odds: Dict[str, float] = None
    ) -> Dict[str, MonteCarloValidation]:
        """Valide tous les scénarios détectés"""
        
        validations = {}
        odds = odds or {}
        
        for scenario in detection_result.detected_scenarios:
            default_odds = 2.0
            scenario_odds = odds.get(scenario.scenario_id.value, default_odds)
            
            validation = self.validate_scenario(scenario, features, scenario_odds)
            validations[scenario.scenario_id.value] = validation
        
        return validations
    
    def get_validated_recommendations(
        self,
        validations: Dict[str, MonteCarloValidation],
        min_validation_score: float = 60.0
    ) -> List[str]:
        """Retourne les scénarios validés par Monte Carlo"""
        
        validated = []
        
        for scenario_id, validation in validations.items():
            if validation.validation_score >= min_validation_score:
                validated.append(scenario_id)
        
        return validated


# ═══════════════════════════════════════════════════════════════════════════════════════
# QUICK ACCESS FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════════════

def quick_validate(
    scenario_name: str,
    confidence: float,
    edge: float,
    odds: float = 2.0,
    n_simulations: int = 5000
) -> MonteCarloValidation:
    """
    Validation rapide d'un scénario.
    
    Usage:
        validation = quick_validate("TOTAL_CHAOS", 75, 0.08)
        print(validation.to_summary())
    """
    from quantum.models import ScenarioID
    
    # Créer un mock scenario evaluation
    @dataclass
    class MockCondition:
        metric: str
        threshold: float
        actual_value: float
    
    @dataclass
    class MockEval:
        scenario_id: ScenarioID
        scenario_name: str
        adjusted_confidence: float
        conditions_evaluated: List[MockCondition]
    
    # Simuler des conditions
    mock_conditions = [
        MockCondition("pace_combined", 100, 120),
        MockCondition("chaos_potential", 60, 75),
        MockCondition("xg_combined", 2.5, 3.0),
    ]
    
    try:
        scenario_id = ScenarioID(scenario_name)
    except:
        scenario_id = ScenarioID.TOTAL_CHAOS
    
    mock_eval = MockEval(
        scenario_id=scenario_id,
        scenario_name=scenario_name,
        adjusted_confidence=confidence,
        conditions_evaluated=mock_conditions
    )
    
    # Créer des features simulées
    features = {
        "pace_combined": 120,
        "chaos_potential": 75,
        "xg_combined": 3.0,
        "confidence": confidence,
        "edge": edge,
    }
    
    validator = MonteCarloValidator(n_simulations=n_simulations)
    return validator.validate_scenario(mock_eval, features, odds)
