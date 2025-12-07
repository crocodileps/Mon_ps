"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                    QUANTUM MODELS - MON_PS TRADING SYSTEM                            ║
║                                                                                       ║
║  Package contenant tous les modèles de données pour l'Agent Quantum V1.              ║
║                                                                                       ║
║  Structure:                                                                           ║
║  - dna_vectors.py: Les 9 vecteurs DNA (TeamDNA)                                      ║
║  - friction_context.py: FrictionMatrix, MatchContext, CompositeIndices              ║
║  - scenarios_strategy.py: Scénarios, Recommandations, QuantumStrategy               ║
║  - scenarios_definitions.py: Définitions des 20 scénarios                           ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

# DNA Vectors
from .dna_vectors import (
    # Enums
    Mentality,
    KillerInstinct,
    KeeperStatus,
    Formation,
    PlayingStyle,
    ScoringPeriod,
    MomentumTrend,
    
    # Vecteur 1: Market DNA
    MarketPerformance,
    MarketDNA,
    
    # Vecteur 2: Context DNA
    LocationPerformance,
    SituationalPerformance,
    ContextDNA,
    
    # Vecteur 3: Risk DNA
    VarianceMetrics,
    UpsetProfile,
    StreakAnalysis,
    RiskDNA,
    
    # Vecteur 4: Temporal DNA
    PeriodStats,
    HalfStats,
    TemporalMarketOpportunity,
    TemporalDNA,
    
    # Vecteur 5: Nemesis DNA
    TacticalAxis,
    TacticalWeakness,
    TacticalStrength,
    SpecificMatchup,
    NemesisDNA,
    
    # Vecteur 6: Psyche DNA
    GameStateBehavior,
    ClutchPerformance,
    MomentumPsychology,
    PsycheDNA,
    
    # Vecteur 7: Sentiment DNA
    ValueZone,
    CLVTrackRecord,
    SentimentDNA,
    
    # Vecteur 8: Roster DNA
    RosterDNA,
    
    # Vecteur 9: Physical DNA
    PhysicalDNA,
    
    # Vecteur 10: Luck DNA
    LuckDNA,
    
    # Vecteur 11: Chameleon DNA
    ChameleonDNA,
    
    # Current Season
    CurrentSeasonDNA,
    
    # Team DNA complet
    TeamDNA,
)

# Friction & Context
from .friction_context import (
    # Enums
    FrictionLevel,
    DominanceType,
    ClashType,
    
    # Friction Components
    KineticFriction,
    TemporalFriction,
    PsycheFriction,
    PhysicalFriction,
    
    # Friction Matrix
    FrictionMatrix,
    
    # Match Context
    TeamMatchContext,
    MatchContext,
    
    # Composite Indices
    CompositeIndices,
    MatchIndicesComparison,
    
    # Disciplinary
    DisciplinaryFriction,
    
    # H2H
    H2HMatch,
    H2HAnalysis,
    
    # Referee
    RefereeProfile,
)

# Scenarios & Strategy
from .scenarios_strategy import (
    # Enums
    ScenarioCategory,
    ScenarioID,
    MarketType,
    StakeTier,
    DecisionSource,
    
    # Scenario Definition
    ScenarioCondition,
    ScenarioMarket,
    ScenarioDefinition,
    ScenarioDetectionResult,
    
    # Market Recommendation
    MarketProbabilities,
    MarketRecommendation,
    
    # Quantum Strategy
    QuantumStrategy,
    DailyQuantumPicks,
    
    # Performance
    BetResult,
    ScenarioPerformance,
    QuantumPerformanceReport,
)

# Version
__version__ = "1.0.0"
__author__ = "Mon_PS Quant Team"

# Liste de tous les exports
__all__ = [
    # DNA Vectors
    "Mentality",
    "KillerInstinct",
    "KeeperStatus",
    "Formation",
    "PlayingStyle",
    "ScoringPeriod",
    "MomentumTrend",
    "MarketPerformance",
    "MarketDNA",
    "LocationPerformance",
    "SituationalPerformance",
    "ContextDNA",
    "VarianceMetrics",
    "UpsetProfile",
    "StreakAnalysis",
    "RiskDNA",
    "PeriodStats",
    "HalfStats",
    "TemporalMarketOpportunity",
    "TemporalDNA",
    "TacticalAxis",
    "TacticalWeakness",
    "TacticalStrength",
    "SpecificMatchup",
    "NemesisDNA",
    "GameStateBehavior",
    "ClutchPerformance",
    "MomentumPsychology",
    "PsycheDNA",
    "ValueZone",
    "CLVTrackRecord",
    "SentimentDNA",
    "RosterDNA",
    "PhysicalDNA",
    "LuckDNA",
    "ChameleonDNA",
    "CurrentSeasonDNA",
    "TeamDNA",
    
    # Friction & Context
    "FrictionLevel",
    "DominanceType",
    "ClashType",
    "KineticFriction",
    "TemporalFriction",
    "PsycheFriction",
    "PhysicalFriction",
    "FrictionMatrix",
    "TeamMatchContext",
    "MatchContext",
    "CompositeIndices",
    "MatchIndicesComparison",
    "DisciplinaryFriction",
    "H2HMatch",
    "H2HAnalysis",
    "RefereeProfile",
    
    # Scenarios & Strategy
    "ScenarioCategory",
    "ScenarioID",
    "MarketType",
    "StakeTier",
    "DecisionSource",
    "ScenarioCondition",
    "ScenarioMarket",
    "ScenarioDefinition",
    "ScenarioDetectionResult",
    "MarketProbabilities",
    "MarketRecommendation",
    "QuantumStrategy",
    "DailyQuantumPicks",
    "BetResult",
    "ScenarioPerformance",
    "QuantumPerformanceReport",
]
