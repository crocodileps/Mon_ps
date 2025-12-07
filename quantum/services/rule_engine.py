"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                    QUANTUM RULE ENGINE 2.1 + MONTE CARLO                              ║
║                                                                                       ║
║  Orchestrateur principal avec validation Monte Carlo intégrée.                       ║
║                                                                                       ║
║  Pipeline:                                                                           ║
║  1. Load DNA (2 équipes)                                                             ║
║  2. Calculate Features (175+)                                                        ║
║  3. Detect Scenarios (20)                                                            ║
║  4. 🎲 Monte Carlo Validation (NEW!)                                                 ║
║  5. Generate Recommendations (filtered by MC)                                        ║
║  6. Output QuantumStrategy                                                           ║
║                                                                                       ║
║  "La confiance sans validation = arrogance. Monte Carlo = humilité scientifique"    ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import logging

# Imports internes
from quantum.models import (
    QuantumStrategy, MarketRecommendation, MarketType,
    StakeTier, DecisionSource, ScenarioID
)
from .dna_loader import QuantumDNALoader
from .feature_calculator import QuantumFeatureCalculator, MatchFeatures
from .scenario_detector import QuantumScenarioDetector, DetectionResult
from .monte_carlo import (
    MonteCarloValidator, 
    MonteCarloValidation,
    RobustnessLevel,
    StressTestResult
)

logger = logging.getLogger("QuantumRuleEngine")


# ═══════════════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class MonteCarloConfig:
    """Configuration Monte Carlo"""
    enabled: bool = True
    n_simulations: int = 5000          # Nombre de simulations
    noise_level: float = 0.15          # ±15% de bruit
    min_validation_score: float = 60.0  # Score minimum pour valider
    min_success_rate: float = 0.50      # Taux de succès minimum
    stress_test_required: bool = True   # Exiger le stress test
    use_kelly: bool = True              # Utiliser Kelly Criterion


@dataclass
class EngineConfig:
    """Configuration du Rule Engine"""
    min_confidence: float = 50.0
    min_edge: float = 5.0
    max_recommendations: int = 5
    use_historical_weighting: bool = True
    enable_cascade_detection: bool = True
    
    # Monte Carlo
    monte_carlo: MonteCarloConfig = field(default_factory=MonteCarloConfig)
    
    # Seuils de décision
    decision_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "rule_only": 75.0,      # > 75% = rules seules
        "hybrid": 50.0,         # 50-75% = hybrid
        "ml_fallback": 0.0      # < 50% = ML
    })


# ═══════════════════════════════════════════════════════════════════════════════════════
# DATA CLASSES POUR RÉSULTATS MC
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class MonteCarloSummary:
    """Résumé Monte Carlo pour un match"""
    enabled: bool
    scenarios_validated: int
    scenarios_rejected: int
    scenarios_total: int
    avg_validation_score: float
    avg_success_rate: float
    robustness_distribution: Dict[str, int]
    stress_tests_passed: int
    stress_tests_failed: int
    kelly_recommendations: Dict[str, float]
    total_simulation_time_ms: float
    
    def to_dict(self) -> Dict:
        return {
            "enabled": self.enabled,
            "scenarios_validated": self.scenarios_validated,
            "scenarios_rejected": self.scenarios_rejected,
            "scenarios_total": self.scenarios_total,
            "avg_validation_score": round(self.avg_validation_score, 1),
            "avg_success_rate": round(self.avg_success_rate * 100, 1),
            "robustness_distribution": self.robustness_distribution,
            "stress_tests": {
                "passed": self.stress_tests_passed,
                "failed": self.stress_tests_failed
            },
            "kelly_recommendations": {
                k: round(v * 100, 2) for k, v in self.kelly_recommendations.items()
            },
            "simulation_time_ms": round(self.total_simulation_time_ms, 1)
        }


# ═══════════════════════════════════════════════════════════════════════════════════════
# RULE ENGINE 2.1
# ═══════════════════════════════════════════════════════════════════════════════════════

class QuantumRuleEngine:
    """
    Quantum Rule Engine 2.1 + Monte Carlo Validation
    
    Orchestre:
    - DNA Loading
    - Feature Calculation
    - Scenario Detection
    - 🎲 Monte Carlo Validation
    - Market Recommendation
    - Strategy Generation
    """
    
    def __init__(self, db_pool=None, config: Optional[EngineConfig] = None):
        self.config = config or EngineConfig()
        
        # Composants principaux
        self.dna_loader = QuantumDNALoader(db_pool)
        self.feature_calculator = QuantumFeatureCalculator()
        self.scenario_detector = QuantumScenarioDetector()
        
        # Monte Carlo Validator
        if self.config.monte_carlo.enabled:
            self.mc_validator = MonteCarloValidator(
                n_simulations=self.config.monte_carlo.n_simulations,
                noise_level=self.config.monte_carlo.noise_level,
                confidence_threshold=self.config.min_confidence,
                edge_threshold=self.config.min_edge / 100
            )
        else:
            self.mc_validator = None
        
        # Stats
        self._analyses_count = 0
        self._scenarios_detected_count = 0
        self._scenarios_validated_count = 0
        self._scenarios_rejected_count = 0
        
        mc_status = "✅ ENABLED" if self.config.monte_carlo.enabled else "❌ DISABLED"
        logger.info(f"Quantum Rule Engine 2.1 initialized | Monte Carlo: {mc_status}")
    
    async def analyze_match(
        self,
        home_team: str,
        away_team: str,
        context: Optional[Dict] = None,
        odds: Optional[Dict] = None
    ) -> QuantumStrategy:
        """
        Analyse complète d'un match avec validation Monte Carlo.
        
        Args:
            home_team: Nom de l'équipe à domicile
            away_team: Nom de l'équipe à l'extérieur
            context: Contexte du match (repos, européen, etc.)
            odds: Cotes disponibles pour calculer l'edge
        
        Returns:
            QuantumStrategy avec recommandations validées par Monte Carlo
        """
        start_time = datetime.now()
        self._analyses_count += 1
        
        try:
            # 1. LOAD DNA
            logger.info(f"Loading DNA for {home_team} vs {away_team}")
            home_dna, away_dna, friction = await self.dna_loader.get_match_dna(
                home_team, away_team
            )
            
            # 2. CALCULATE FEATURES
            logger.info("Calculating features...")
            features = self.feature_calculator.calculate_all_features(
                home_dna, away_dna, friction, context
            )
            
            # 3. DETECT SCENARIOS
            logger.info("Detecting scenarios...")
            detection = self.scenario_detector.detect_scenarios(
                features.features,
                home_dna,
                away_dna,
                min_confidence=self.config.min_confidence
            )
            
            self._scenarios_detected_count += len(detection.detected_scenarios)
            
            # 4. 🎲 MONTE CARLO VALIDATION
            mc_validations = {}
            mc_summary = None
            
            if self.config.monte_carlo.enabled and detection.detected_scenarios:
                logger.info(f"🎲 Running Monte Carlo validation on {len(detection.detected_scenarios)} scenarios...")
                mc_validations, mc_summary = self._run_monte_carlo_validation(
                    detection, features.features, odds or {}
                )
                
                # Filtrer les scénarios non validés
                detection = self._filter_by_monte_carlo(detection, mc_validations)
            
            # 5. GENERATE RECOMMENDATIONS
            logger.info("Generating recommendations...")
            recommendations = self._generate_recommendations(
                detection, features, odds or {}, mc_validations
            )
            
            # 6. BUILD STRATEGY
            strategy = self._build_strategy(
                home_team, away_team,
                detection, recommendations, features,
                mc_summary, mc_validations
            )
            
            # Calculer le temps de traitement
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            strategy.processing_time_ms = processing_time
            
            mc_info = f" | MC validated: {mc_summary.scenarios_validated}/{mc_summary.scenarios_total}" if mc_summary else ""
            logger.info(f"Analysis complete in {processing_time:.1f}ms - {len(detection.detected_scenarios)} scenarios{mc_info}")
            
            return strategy
            
        except Exception as e:
            logger.error(f"Error analyzing match: {e}")
            raise
    
    def _run_monte_carlo_validation(
        self,
        detection: DetectionResult,
        features: Dict[str, float],
        odds: Dict[str, float]
    ) -> Tuple[Dict[str, MonteCarloValidation], MonteCarloSummary]:
        """
        Exécute la validation Monte Carlo sur tous les scénarios détectés.
        
        Returns:
            Tuple[validations par scénario, résumé global]
        """
        validations = {}
        total_time = 0
        
        for scenario in detection.detected_scenarios:
            # Récupérer les cotes pour ce scénario
            scenario_odds = 2.0
            if scenario.recommended_markets:
                first_market = scenario.recommended_markets[0]
                scenario_odds = odds.get(first_market, 2.0)
            
            # Valider avec Monte Carlo
            validation = self.mc_validator.validate_scenario(
                scenario, features, scenario_odds
            )
            validations[scenario.scenario_id.value] = validation
            total_time += validation.simulation_time_ms
        
        # Construire le résumé
        validated = sum(1 for v in validations.values() if v.is_validated)
        rejected = len(validations) - validated
        
        self._scenarios_validated_count += validated
        self._scenarios_rejected_count += rejected
        
        # Distribution de robustesse
        robustness_dist = {}
        for v in validations.values():
            level = v.robustness.value
            robustness_dist[level] = robustness_dist.get(level, 0) + 1
        
        # Kelly moyen
        kelly_recommendations = {}
        for scenario_id, v in validations.items():
            if v.kelly_half > 0:
                kelly_recommendations[scenario_id] = v.kelly_half
        
        # Stress tests
        stress_passed = sum(
            1 for v in validations.values() 
            if v.stress_test_result in [StressTestResult.PASSED, StressTestResult.DEGRADED]
        )
        stress_failed = sum(
            1 for v in validations.values() 
            if v.stress_test_result == StressTestResult.FAILED
        )
        
        summary = MonteCarloSummary(
            enabled=True,
            scenarios_validated=validated,
            scenarios_rejected=rejected,
            scenarios_total=len(validations),
            avg_validation_score=sum(v.validation_score for v in validations.values()) / max(1, len(validations)),
            avg_success_rate=sum(v.success_rate for v in validations.values()) / max(1, len(validations)),
            robustness_distribution=robustness_dist,
            stress_tests_passed=stress_passed,
            stress_tests_failed=stress_failed,
            kelly_recommendations=kelly_recommendations,
            total_simulation_time_ms=total_time
        )
        
        return validations, summary
    
    def _filter_by_monte_carlo(
        self,
        detection: DetectionResult,
        validations: Dict[str, MonteCarloValidation]
    ) -> DetectionResult:
        """
        Filtre les scénarios selon la validation Monte Carlo.
        
        Garde uniquement les scénarios qui passent les critères MC.
        """
        mc_config = self.config.monte_carlo
        
        validated_scenarios = []
        
        for scenario in detection.detected_scenarios:
            validation = validations.get(scenario.scenario_id.value)
            
            if not validation:
                # Pas de validation = garder (sécurité)
                validated_scenarios.append(scenario)
                continue
            
            # Vérifier les critères
            passes = True
            
            # Score de validation minimum
            if validation.validation_score < mc_config.min_validation_score:
                logger.debug(f"❌ {scenario.scenario_name} rejected: validation_score {validation.validation_score:.0f} < {mc_config.min_validation_score}")
                passes = False
            
            # Taux de succès minimum
            elif validation.success_rate < mc_config.min_success_rate:
                logger.debug(f"❌ {scenario.scenario_name} rejected: success_rate {validation.success_rate*100:.0f}% < {mc_config.min_success_rate*100:.0f}%")
                passes = False
            
            # Stress test obligatoire
            elif mc_config.stress_test_required and validation.stress_test_result == StressTestResult.FAILED:
                logger.debug(f"❌ {scenario.scenario_name} rejected: stress test FAILED")
                passes = False
            
            # Robustesse minimum (pas UNRELIABLE)
            elif validation.robustness == RobustnessLevel.UNRELIABLE:
                logger.debug(f"❌ {scenario.scenario_name} rejected: robustness UNRELIABLE")
                passes = False
            
            if passes:
                logger.debug(f"✅ {scenario.scenario_name} validated: score={validation.validation_score:.0f}, robustness={validation.robustness.value}")
                validated_scenarios.append(scenario)
        
        # Reconstruire DetectionResult avec les scénarios filtrés
        # Garder les mêmes métadonnées mais avec les scénarios validés
        new_detection = DetectionResult(
            home_team=detection.home_team,
            away_team=detection.away_team,
            detected_scenarios=validated_scenarios,
            all_evaluations=detection.all_evaluations,
            primary_scenario=validated_scenarios[0] if validated_scenarios else None,
            secondary_scenario=validated_scenarios[1] if len(validated_scenarios) > 1 else None,
            overall_confidence=detection.overall_confidence
        )
        
        return new_detection
    
    def analyze_match_sync(
        self,
        home_team: str,
        away_team: str,
        context: Optional[Dict] = None,
        odds: Optional[Dict] = None
    ) -> QuantumStrategy:
        """Version synchrone de analyze_match"""
        return asyncio.run(self.analyze_match(home_team, away_team, context, odds))
    
    def _generate_recommendations(
        self,
        detection: DetectionResult,
        features: MatchFeatures,
        odds: Dict[str, float],
        mc_validations: Dict[str, MonteCarloValidation]
    ) -> List[MarketRecommendation]:
        """Génère les recommandations de paris avec ajustements MC"""
        
        recommendations = []
        
        if not detection.detected_scenarios:
            return recommendations
        
        # Parcourir les scénarios détectés (déjà filtrés par MC)
        for scenario in detection.detected_scenarios[:3]:  # Top 3 scénarios
            
            # Récupérer la validation MC
            mc_validation = mc_validations.get(scenario.scenario_id.value)
            
            # Récupérer les marchés recommandés
            for market_str in scenario.recommended_markets:
                try:
                    market = MarketType(market_str)
                except ValueError:
                    continue
                
                # Calculer la probabilité
                prob = self._calculate_probability(market, features, scenario)
                
                # Récupérer les cotes
                market_odds = odds.get(market_str, odds.get(market.value, 2.0))
                implied_prob = 1 / market_odds
                
                # Calculer l'edge
                edge = prob - implied_prob
                
                # Ajuster le stake avec Kelly MC si disponible
                if mc_validation and self.config.monte_carlo.use_kelly:
                    stake_tier, stake_units = self._calculate_stake_with_kelly(
                        edge, scenario.adjusted_confidence, mc_validation
                    )
                else:
                    stake_tier, stake_units = self._calculate_stake(
                        edge, scenario.adjusted_confidence
                    )
                
                # Créer la recommandation si edge positif
                if edge >= self.config.min_edge / 100:
                    # Ajouter info MC au reasoning
                    reasoning_parts = [
                        f"{scenario.scenario_name}: {', '.join(scenario.key_factors[:2])}"
                    ]
                    
                    if mc_validation:
                        reasoning_parts.append(
                            f"[MC: {mc_validation.robustness.value}, "
                            f"score={mc_validation.validation_score:.0f}]"
                        )
                    
                    rec = MarketRecommendation(
                        market=market,
                        selection=self._get_market_selection(market),
                        calculated_probability=prob,
                        implied_probability=implied_prob,
                        odds=market_odds,
                        edge=edge,
                        confidence=scenario.adjusted_confidence,
                        stake_tier=stake_tier,
                        stake_units=stake_units,
                        reasoning=" | ".join(reasoning_parts),
                        scenarios_contributing=[scenario.scenario_id.value]
                    )
                    recommendations.append(rec)
        
        # Trier par EV décroissante
        recommendations.sort(key=lambda r: r.expected_value, reverse=True)
        
        # Limiter le nombre
        return recommendations[:self.config.max_recommendations]
    
    def _calculate_probability(
        self,
        market: MarketType,
        features: MatchFeatures,
        scenario
    ) -> float:
        """Calcule la probabilité pour un marché"""
        
        f = features.features
        
        # Base probabilities par marché
        base_probs = {
            MarketType.OVER_15: 0.65,
            MarketType.OVER_25: 0.50,
            MarketType.OVER_35: 0.35,
            MarketType.UNDER_25: 0.50,
            MarketType.BTTS_YES: 0.50,
            MarketType.BTTS_NO: 0.50,
            MarketType.HOME_WIN: 0.45,
            MarketType.DRAW: 0.25,
            MarketType.AWAY_WIN: 0.30,
            MarketType.FIRST_HALF_OVER_15: 0.35,
            MarketType.SECOND_HALF_OVER_15: 0.40,
            MarketType.GOAL_0_15_YES: 0.30,
            MarketType.GOAL_75_90_YES: 0.35,
            MarketType.HOME_2H_OVER_05: 0.55,
            MarketType.AWAY_2H_OVER_05: 0.45,
        }
        
        base = base_probs.get(market, 0.50)
        
        # Ajustements selon les features
        adj = 0.0
        
        # Over marchés
        if "OVER" in market.value:
            adj += (f.get('chaos_potential', 50) - 50) / 200
            adj += (f.get('xg_combined', 2.5) - 2.5) / 10
            adj += (f.get('pace_combined', 100) - 100) / 500
        
        # Under marchés
        if "UNDER" in market.value:
            adj -= (f.get('chaos_potential', 50) - 50) / 200
            adj += (f.get('control_index', 50) - 50) / 200
        
        # BTTS
        if "BTTS" in market.value:
            if "YES" in market.value:
                adj += (f.get('chaos_potential', 50) - 50) / 150
                adj += (f.get('defensive_fragility', 50) - 50) / 200
            else:
                adj -= (f.get('chaos_potential', 50) - 50) / 150
        
        # Late goals
        if "75_90" in market.value or "2H" in market.value:
            adj += (f.get('diesel_factor_combined', 1.0) - 1.0) / 5
            adj += f.get('fatigue_away', 0) / 5
        
        # Early goals
        if "0_15" in market.value or "1H" in market.value:
            adj += (f.get('sprinter_factor_combined', 1.0) - 1.0) / 5
            adj += f.get('explosive_start_potential', 0) / 10
        
        # Bonus scénario
        scenario_bonus = (scenario.adjusted_confidence - 50) / 500
        
        # Calculer la probabilité finale
        prob = base + adj + scenario_bonus
        
        # Clamp entre 0.05 et 0.95
        return max(0.05, min(0.95, prob))
    
    def _calculate_stake(
        self,
        edge: float,
        confidence: float
    ) -> Tuple[StakeTier, float]:
        """Calcule le tier et le montant de mise (méthode classique)"""
        
        score = edge * 100 * (confidence / 100)
        
        if score >= 10 and confidence >= 75:
            return StakeTier.SNIPER, 3.0
        elif score >= 6 and confidence >= 60:
            return StakeTier.NORMAL, 2.0
        elif score >= 3:
            return StakeTier.SMALL, 1.0
        else:
            return StakeTier.MICRO, 0.5
    
    def _calculate_stake_with_kelly(
        self,
        edge: float,
        confidence: float,
        mc_validation: MonteCarloValidation
    ) -> Tuple[StakeTier, float]:
        """
        Calcule le tier et le montant de mise avec Kelly Criterion de Monte Carlo.
        
        Utilise le demi-Kelly pour être conservateur.
        """
        # Récupérer le Kelly recommandé (utiliser demi-Kelly)
        kelly_pct = mc_validation.kelly_half  # 0 à 0.125 (12.5% max)
        
        # Convertir en unités (1% du bankroll = 1 unité, max 3u)
        # kelly_half de 0.125 = 12.5% = 3 unités (SNIPER max)
        kelly_units = kelly_pct * 24  # Scale: 12.5% * 24 = 3 unités max
        
        # Ajuster selon la robustesse
        robustness_multiplier = {
            RobustnessLevel.ROCK_SOLID: 1.0,
            RobustnessLevel.ROBUST: 0.85,
            RobustnessLevel.MODERATE: 0.70,
            RobustnessLevel.FRAGILE: 0.50,
            RobustnessLevel.UNRELIABLE: 0.25,
        }
        
        multiplier = robustness_multiplier.get(mc_validation.robustness, 0.5)
        adjusted_units = kelly_units * multiplier
        
        # Déterminer le tier
        if adjusted_units >= 2.5 and mc_validation.robustness in [RobustnessLevel.ROCK_SOLID, RobustnessLevel.ROBUST]:
            return StakeTier.SNIPER, 3.0
        elif adjusted_units >= 1.5 and mc_validation.robustness != RobustnessLevel.UNRELIABLE:
            return StakeTier.NORMAL, 2.0
        elif adjusted_units >= 0.8:
            return StakeTier.SMALL, 1.0
        else:
            return StakeTier.MICRO, 0.5
    
    def _get_market_selection(self, market: MarketType) -> str:
        """Retourne le texte de sélection pour un marché"""
        selections = {
            MarketType.OVER_15: "Over 1.5 Goals",
            MarketType.OVER_25: "Over 2.5 Goals",
            MarketType.OVER_35: "Over 3.5 Goals",
            MarketType.UNDER_25: "Under 2.5 Goals",
            MarketType.BTTS_YES: "BTTS Yes",
            MarketType.BTTS_NO: "BTTS No",
            MarketType.HOME_WIN: "Home Win",
            MarketType.DRAW: "Draw",
            MarketType.AWAY_WIN: "Away Win",
            MarketType.FIRST_HALF_OVER_15: "1H Over 1.5",
            MarketType.SECOND_HALF_OVER_15: "2H Over 1.5",
            MarketType.GOAL_0_15_YES: "Goal 0-15'",
            MarketType.GOAL_75_90_YES: "Goal 75-90'",
            MarketType.HOME_2H_OVER_05: "Home Goal 2H",
            MarketType.AWAY_2H_OVER_05: "Away Goal 2H",
        }
        return selections.get(market, market.value)
    
    def _build_strategy(
        self,
        home_team: str,
        away_team: str,
        detection: DetectionResult,
        recommendations: List[MarketRecommendation],
        features: MatchFeatures,
        mc_summary: Optional[MonteCarloSummary],
        mc_validations: Dict[str, MonteCarloValidation]
    ) -> QuantumStrategy:
        """Construit la QuantumStrategy finale avec info MC"""
        
        # Convertir les scénarios en format attendu
        from quantum.models import ScenarioDetectionResult, ScenarioCategory
        
        detected_results = []
        for s in detection.detected_scenarios:
            # Récupérer validation MC
            mc_val = mc_validations.get(s.scenario_id.value)
            
            result = ScenarioDetectionResult(
                scenario_id=s.scenario_id,
                scenario_name=s.scenario_name,
                category=ScenarioCategory.TACTICAL,  # Simplified
                is_detected=True,
                confidence=s.adjusted_confidence,
                triggered_conditions=s.key_factors,
                recommended_markets=[MarketType(m) for m in s.recommended_markets[:3] if m in [mt.value for mt in MarketType]],
                historical_roi=self.scenario_detector.historical_performance.get(s.scenario_id, {}).get('roi', 0),
                # Ajouter info MC aux conditions
                monte_carlo_validated=mc_val.is_validated if mc_val else None,
                monte_carlo_score=mc_val.validation_score if mc_val else None,
                monte_carlo_robustness=mc_val.robustness.value if mc_val else None
            )
            detected_results.append(result)
        
        # Construire la stratégie
        strategy = QuantumStrategy(
            home_team=home_team,
            away_team=away_team,
            date=datetime.now(),
            detected_scenarios=detected_results,
            primary_scenario=detection.primary_scenario.scenario_id if detection.primary_scenario else None,
            secondary_scenario=detection.secondary_scenario.scenario_id if detection.secondary_scenario else None,
        )
        
        # Ajouter les recommandations
        for rec in recommendations:
            strategy.add_recommendation(rec)
        
        # Ajouter les marchés à éviter
        if detection.primary_scenario:
            for market in detection.primary_scenario.avoid_markets:
                reason = f"Éviter selon {detection.primary_scenario.scenario_name}"
                strategy.add_avoid_market(market, reason)
        
        # Déterminer la source de décision
        if detection.primary_scenario and detection.primary_scenario.adjusted_confidence >= 75:
            strategy.decision_source = DecisionSource.RULE_ENGINE
            strategy.rule_weight = 1.0
            strategy.ml_weight = 0.0
        elif detection.primary_scenario and detection.primary_scenario.adjusted_confidence >= 50:
            strategy.decision_source = DecisionSource.HYBRID
            conf = detection.primary_scenario.adjusted_confidence
            strategy.rule_weight = conf / 100
            strategy.ml_weight = 1 - (conf / 100)
        else:
            strategy.decision_source = DecisionSource.ML_ENGINE
            strategy.rule_weight = 0.2
            strategy.ml_weight = 0.8
        
        # Ajouter le résumé Monte Carlo
        if mc_summary:
            strategy.monte_carlo_summary = mc_summary.to_dict()
        
        # Calculer les totaux
        strategy.calculate_totals()
        strategy.confidence_overall = detection.overall_confidence
        
        return strategy
    
    # ═══════════════════════════════════════════════════════════════════════════════════
    # CONVENIENCE METHODS
    # ═══════════════════════════════════════════════════════════════════════════════════
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du moteur"""
        stats = {
            "analyses_count": self._analyses_count,
            "scenarios_detected_total": self._scenarios_detected_count,
            "avg_scenarios_per_match": self._scenarios_detected_count / max(1, self._analyses_count),
            "feature_count": self.feature_calculator.get_feature_count(),
            "scenarios_available": len(self.scenario_detector.scenarios),
        }
        
        if self.config.monte_carlo.enabled:
            stats["monte_carlo"] = {
                "enabled": True,
                "simulations_per_scenario": self.config.monte_carlo.n_simulations,
                "scenarios_validated": self._scenarios_validated_count,
                "scenarios_rejected": self._scenarios_rejected_count,
                "validation_rate": self._scenarios_validated_count / max(1, self._scenarios_validated_count + self._scenarios_rejected_count)
            }
        
        return stats
    
    def get_available_scenarios(self) -> List[Dict]:
        """Retourne la liste des scénarios disponibles"""
        from quantum.models.scenarios_definitions import get_all_scenarios
        return [
            {
                "id": s.id.value,
                "name": s.name,
                "emoji": s.emoji,
                "category": s.category.value,
                "description": s.description,
                "historical_roi": self.scenario_detector.historical_performance.get(s.id, {}).get('roi', 0),
            }
            for s in get_all_scenarios()
        ]
    
    def explain_scenario(self, scenario_id: ScenarioID) -> str:
        """Explique un scénario en détail"""
        from quantum.models.scenarios_definitions import get_scenario
        
        scenario = get_scenario(scenario_id)
        if not scenario:
            return f"Scénario {scenario_id} non trouvé"
        
        hist = self.scenario_detector.historical_performance.get(scenario_id, {})
        
        lines = [
            f"{scenario.emoji} {scenario.name}",
            "=" * 50,
            f"Catégorie: {scenario.category.value}",
            f"Description: {scenario.description}",
            "",
            "📋 Conditions:",
        ]
        
        for c in scenario.conditions:
            lines.append(f"  • {c.description}: {c.metric} {c.operator} {c.threshold}")
        
        lines.extend([
            "",
            "💰 Marchés recommandés:",
        ])
        for m in scenario.primary_markets:
            lines.append(f"  → {m.market.value} (edge typique: {m.typical_edge*100:.0f}%)")
        
        if scenario.avoid_markets:
            lines.extend([
                "",
                "❌ Marchés à éviter:",
            ])
            for m in scenario.avoid_markets:
                lines.append(f"  ✗ {m.value}")
        
        lines.extend([
            "",
            "📊 Performance historique:",
            f"  ROI: {hist.get('roi', 'N/A')}%",
            f"  Win Rate: {hist.get('wr', 'N/A')}%",
            f"  Échantillon: {hist.get('n', 'N/A')} paris",
        ])
        
        return "\n".join(lines)
    
    def set_monte_carlo_enabled(self, enabled: bool):
        """Active/désactive Monte Carlo à chaud"""
        self.config.monte_carlo.enabled = enabled
        
        if enabled and self.mc_validator is None:
            self.mc_validator = MonteCarloValidator(
                n_simulations=self.config.monte_carlo.n_simulations,
                noise_level=self.config.monte_carlo.noise_level,
                confidence_threshold=self.config.min_confidence,
                edge_threshold=self.config.min_edge / 100
            )
        
        status = "✅ ENABLED" if enabled else "❌ DISABLED"
        logger.info(f"Monte Carlo validation {status}")


# ═══════════════════════════════════════════════════════════════════════════════════════
# QUICK ACCESS FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════════════

def analyze_match_quick(
    home_team: str,
    away_team: str,
    context: Optional[Dict] = None,
    monte_carlo: bool = True
) -> QuantumStrategy:
    """
    Analyse rapide d'un match (sans connexion DB).
    
    Args:
        home_team: Équipe domicile
        away_team: Équipe extérieur
        context: Contexte optionnel
        monte_carlo: Activer Monte Carlo (default: True)
    
    Usage:
        strategy = analyze_match_quick('Barcelona', 'Real Madrid')
        print(strategy)
    """
    config = EngineConfig()
    config.monte_carlo.enabled = monte_carlo
    config.monte_carlo.n_simulations = 1000  # Réduit pour quick (vs 5000 en prod)
    config.monte_carlo.stress_test_required = False  # Pas de stress test pour quick
    
    engine = QuantumRuleEngine(config=config)
    return engine.analyze_match_sync(home_team, away_team, context)


def analyze_match_no_mc(
    home_team: str,
    away_team: str,
    context: Optional[Dict] = None
) -> QuantumStrategy:
    """
    Analyse rapide SANS Monte Carlo (plus rapide).
    """
    return analyze_match_quick(home_team, away_team, context, monte_carlo=False)
