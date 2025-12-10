"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║  QUANTUM MODELS - Exports Complets V2                                                ║
║  Version: 2.0                                                                        ║
║  Architecture Mon_PS - Chess Engine V2.0                                             ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

Installation: /home/Mon_ps/quantum/models/__init__.py
(Remplacer l'ancien __init__.py par celui-ci)

Usage:
    from quantum.models import (
        # Main DNA classes
        TeamDNA,
        CoachDNA,
        ContextDNA,
        DefenseDNA,
        GoalkeeperDNA,
        VarianceDNA,
        ExploitProfile,
        
        # Base
        ConfidentMetric,
        TimingMetric,
        
        # Enums
        Formation,
        MarketType,
        ...
    )
"""

# ═══════════════════════════════════════════════════════════════════════════════════════
# BASE MODELS
# ═══════════════════════════════════════════════════════════════════════════════════════

from .base import (
    QuantumBaseModel,
    ConfidentMetric,
    TimingMetric,
    EdgeMetric,
    calculate_confidence,
    weighted_average,
)

# ═══════════════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════════════

from .enums import (
    # Formations
    Formation,
    
    # Profils
    DefenseProfile,
    AttackProfile,
    MomentumState,
    FormTrend,
    VarianceProfile,
    
    # Matchups
    MatchupProfile,
    
    # Game State
    GameState,
    GameStateReaction,
    
    # Timing
    TimingSignature,
    
    # Marchés
    MarketType,
    MarketCategory,
    
    # Stakes
    StakeSize,
    DecisionConfidence,
    
    # Positions
    Position,
    PositionCategory,
    
    # Arbitres
    RefereeStrictness,
    RefereeStyle,
    
    # Leagues
    League,
    LeagueTier,
    
    # Perception
    PublicPerceptionBias,
    StructureType,
    
    # Data Quality
    DataQuality,
)

# ═══════════════════════════════════════════════════════════════════════════════════════
# COACH DNA
# ═══════════════════════════════════════════════════════════════════════════════════════

from .coach_dna import (
    TacticalFingerprint,
    SubstitutionProfile,
    GameStateReactionProfile,
    MarketImpactProfile,
    CoachDNA,
)

# ═══════════════════════════════════════════════════════════════════════════════════════
# SUB MODELS
# ═══════════════════════════════════════════════════════════════════════════════════════

from .sub_models import (
    # Context
    OffensiveMetrics,
    PossessionMetrics,
    MomentumMetrics,
    HomeAwaySplits,
    ContextDNA,
    
    # Defense
    DefensiveMetrics,
    ZoneVulnerability,
    PressingResistance,
    DefensiveActions,
    DefenseDNA,
    
    # Goalkeeper
    ShotStoppingMetrics,
    DistributionMetrics,
    SweepingMetrics,
    PenaltyProfile,
    ReliabilityMetrics,
    GoalkeeperDNA,
    
    # Variance
    ExpectedPointsMetrics,
    GoalVarianceMetrics,
    ConversionVariance,
    CloseGamesMetrics,
    VarianceDNA,
    
    # Exploit
    IdentifiedWeakness,
    MarketEdge,
    TimingExploits,
    SetPieceExploits,
    MatchupVulnerabilities,
    ExploitProfile,
)

# ═══════════════════════════════════════════════════════════════════════════════════════
# TEAM DNA (Main aggregator)
# ═══════════════════════════════════════════════════════════════════════════════════════

from .team_dna import (
    TeamIdentity,
    TeamDNA,
)

# ═══════════════════════════════════════════════════════════════════════════════════════
# ALL EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Base
    "QuantumBaseModel",
    "ConfidentMetric",
    "TimingMetric",
    "EdgeMetric",
    "calculate_confidence",
    "weighted_average",
    
    # Enums - Formations
    "Formation",
    
    # Enums - Profils
    "DefenseProfile",
    "AttackProfile",
    "MomentumState",
    "FormTrend",
    "VarianceProfile",
    
    # Enums - Matchups
    "MatchupProfile",
    
    # Enums - Game State
    "GameState",
    "GameStateReaction",
    
    # Enums - Timing
    "TimingSignature",
    
    # Enums - Markets
    "MarketType",
    "MarketCategory",
    
    # Enums - Stakes
    "StakeSize",
    "DecisionConfidence",
    
    # Enums - Positions
    "Position",
    "PositionCategory",
    
    # Enums - Referees
    "RefereeStrictness",
    "RefereeStyle",
    
    # Enums - Leagues
    "League",
    "LeagueTier",
    
    # Enums - Perception
    "PublicPerceptionBias",
    "StructureType",
    
    # Enums - Data Quality
    "DataQuality",
    
    # Coach DNA
    "TacticalFingerprint",
    "SubstitutionProfile",
    "GameStateReactionProfile",
    "MarketImpactProfile",
    "CoachDNA",
    
    # Context DNA
    "OffensiveMetrics",
    "PossessionMetrics",
    "MomentumMetrics",
    "HomeAwaySplits",
    "ContextDNA",
    
    # Defense DNA
    "DefensiveMetrics",
    "ZoneVulnerability",
    "PressingResistance",
    "DefensiveActions",
    "DefenseDNA",
    
    # Goalkeeper DNA
    "ShotStoppingMetrics",
    "DistributionMetrics",
    "SweepingMetrics",
    "PenaltyProfile",
    "ReliabilityMetrics",
    "GoalkeeperDNA",
    
    # Variance DNA
    "ExpectedPointsMetrics",
    "GoalVarianceMetrics",
    "ConversionVariance",
    "CloseGamesMetrics",
    "VarianceDNA",
    
    # Exploit Profile
    "IdentifiedWeakness",
    "MarketEdge",
    "TimingExploits",
    "SetPieceExploits",
    "MatchupVulnerabilities",
    "ExploitProfile",
    
    # Team DNA (Main)
    "TeamIdentity",
    "TeamDNA",
]

# Version info
__version__ = "2.0"
__author__ = "Mon_PS Quantum Engine"
