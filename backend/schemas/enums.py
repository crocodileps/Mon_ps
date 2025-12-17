"""
Mon_PS Enums - Hedge Fund Grade Alpha
=====================================

Type-safe enumerations for all constant values.
NEVER use magic strings - always use these enums.

Usage:
    from backend.schemas.enums import Tier, TacticalStyle

    team.tier = Tier.ELITE  # ✅ Correct
    team.tier = "ELITE"     # ❌ Avoid (not type-safe)
"""

from enum import Enum


class Tier(str, Enum):
    """Team tier classification based on historical performance."""
    ELITE = "ELITE"
    GOOD = "GOOD"
    MID = "MID"
    WEAK = "WEAK"
    UNKNOWN = "UNKNOWN"


class League(str, Enum):
    """Supported leagues (Top 5 European)."""
    PREMIER_LEAGUE = "Premier League"
    LA_LIGA = "La Liga"
    BUNDESLIGA = "Bundesliga"
    SERIE_A = "Serie A"
    LIGUE_1 = "Ligue 1"


class TacticalStyle(str, Enum):
    """Primary tactical approach of a team."""
    GEGENPRESS = "GEGENPRESS"
    POSSESSION = "POSSESSION"
    LOW_BLOCK = "LOW_BLOCK"
    BALANCED = "BALANCED"
    TRANSITION = "TRANSITION"
    COUNTER_ATTACK = "COUNTER_ATTACK"
    DIRECT = "DIRECT"
    TIKI_TAKA = "TIKI_TAKA"


class PressingIntensity(str, Enum):
    """Pressing intensity level."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class BlockHeight(str, Enum):
    """Defensive block height."""
    HIGH = "HIGH"
    MID = "MID"
    LOW = "LOW"


class GamestateType(str, Enum):
    """Team behavior based on game state."""
    COMEBACK_KING = "COMEBACK_KING"      # Strong when losing
    COLLAPSE_LEADER = "COLLAPSE_LEADER"  # Weak when leading
    NEUTRAL = "NEUTRAL"                  # Consistent regardless of state
    FRONTRUNNER = "FRONTRUNNER"          # Strong when leading
    SLOW_STARTER = "SLOW_STARTER"        # Weak in first half


class MomentumLevel(str, Enum):
    """Current momentum based on last 5 matches."""
    BLAZING = "BLAZING"    # 5W or 4W1D
    HOT = "HOT"            # 4W or 3W2D
    WARMING = "WARMING"    # 3W or 2W2D1L
    NEUTRAL = "NEUTRAL"    # Mixed results
    COOLING = "COOLING"    # 1W or 2D2L1W
    COLD = "COLD"          # 0-1W, mostly L
    FREEZING = "FREEZING"  # 5L or 4L1D


class GKStatus(str, Enum):
    """Goalkeeper performance classification."""
    GK_ELITE = "GK_ELITE"      # Save rate > 75% (P75)
    GK_SOLID = "GK_SOLID"      # Save rate 65-75% (P25-P75)
    GK_LEAKY = "GK_LEAKY"      # Save rate < 65% (P25)
    GK_UNKNOWN = "GK_UNKNOWN"  # No data


class TeamDependency(str, Enum):
    """Team dependency on key players."""
    COLLECTIVE = "COLLECTIVE"      # No single player dependency
    MVP_DEPENDENT = "MVP_DEPENDENT"  # Heavily relies on 1-2 players


class BestStrategy(str, Enum):
    """Best betting strategy for a team."""
    MONTE_CARLO_PURE = "MONTE_CARLO_PURE"
    VALUE_HUNTER = "VALUE_HUNTER"
    CLV_CHASER = "CLV_CHASER"
    CONTRARIAN = "CONTRARIAN"
    MOMENTUM_RIDER = "MOMENTUM_RIDER"
    UNKNOWN = "UNKNOWN"
