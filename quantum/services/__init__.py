"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                    QUANTUM SERVICES - MON_PS TRADING SYSTEM                          ║
║                                                                                       ║
║  Services pour l'Agent Quantum V1:                                                   ║
║  - DNALoader: Chargement des 11 vecteurs DNA                                         ║
║  - FeatureCalculator: Calcul des 150+ features                                       ║
║  - ScenarioDetector: Détection des 20 scénarios                                      ║
║  - RuleEngine: Orchestrateur principal                                               ║
║  - MonteCarloValidator: Validation Hedge Fund Grade                                  ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

from .dna_loader import QuantumDNALoader, DNACache
from .feature_calculator import QuantumFeatureCalculator, MatchFeatures
from .scenario_detector import (
    QuantumScenarioDetector,
    DetectionResult,
    ScenarioExplanation,
    ConditionEvaluation,
    ConfidenceLevel
)
from .rule_engine import (
    QuantumRuleEngine,
    EngineConfig,
    analyze_match_quick
)
from .monte_carlo import (
    MonteCarloValidator,
    MonteCarloValidation,
    ConfidenceInterval,
    SimulationResult,
    RobustnessLevel,
    StressTestResult,
    quick_validate
)

__version__ = "2.1.0"
__author__ = "Mon_PS Quant Team"

__all__ = [
    # DNA Loader (simulated)
    "QuantumDNALoader",
    "DNACache",

    # Feature Calculator
    "QuantumFeatureCalculator",
    "MatchFeatures",
    
    # Scenario Detector
    "QuantumScenarioDetector",
    "DetectionResult",
    "ScenarioExplanation",
    "ConditionEvaluation",
    "ConfidenceLevel",
    
    # Rule Engine
    "QuantumRuleEngine",
    "EngineConfig",
    "analyze_match_quick",
    
    # Monte Carlo Validator
    "MonteCarloValidator",
    "MonteCarloValidation",
    "ConfidenceInterval",
    "SimulationResult",
    "RobustnessLevel",
    "StressTestResult",
    "quick_validate",
]
