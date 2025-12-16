"""
Golden Hour Mode - Dynamic TTL Intelligence
Institutional Grade Cache Optimization

Author: Mon_PS Quant Team
Grade: 11/10 Perfectionniste
"""

from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()


class GoldenHourConfig(BaseModel):
    """Configuration Golden Hour Mode"""
    
    # Zone 1: Ultra-Short TTL (Warm-up period)
    zone_warmup_minutes: int = 15
    zone_warmup_ttl: int = 30  # 30 seconds
    
    # Zone 2: Golden Hour (Late steam capture)
    zone_golden_hours: float = 1.0
    zone_golden_ttl: int = 60  # 1 minute
    
    # Zone 3: Active Market (High volatility)
    zone_active_hours: float = 6.0
    zone_active_ttl: int = 900  # 15 minutes
    
    # Zone 4: Pre-Match (Medium volatility)
    zone_prematch_hours: float = 24.0
    zone_prematch_ttl: int = 3600  # 1 hour
    
    # Zone 5: Standard (Low volatility)
    zone_standard_ttl: int = 21600  # 6 hours
    
    # Lineup bonus (extend TTL if lineup confirmed)
    lineup_confirmed_multiplier: float = 2.0
    lineup_confirmed_max_ttl: int = 86400  # 24h max


class GoldenHourCalculator:
    """
    Calculate dynamic TTL based on time to kickoff
    
    Institutional Grade algorithm for cache optimization
    """
    
    def __init__(self, config: Optional[GoldenHourConfig] = None):
        self.config = config or GoldenHourConfig()
        logger.info(
            "GoldenHourCalculator initialized",
            config=self.config.dict()
        )
    
    def calculate_ttl(
        self,
        kickoff_time: datetime,
        current_time: Optional[datetime] = None,
        lineup_confirmed: bool = False
    ) -> dict:
        """
        Calculate optimal TTL based on time to kickoff
        
        Args:
            kickoff_time: Match kickoff datetime (UTC)
            current_time: Current time (UTC), defaults to now()
            lineup_confirmed: Whether lineup is confirmed
            
        Returns:
            dict with ttl, zone, hours_to_kickoff, reasoning
        """
        if current_time is None:
            current_time = datetime.now(kickoff_time.tzinfo)
        
        time_delta = kickoff_time - current_time
        
        if time_delta.total_seconds() < 0:
            return {
                'ttl': 0,
                'zone': 'match_started',
                'hours_to_kickoff': 0,
                'reasoning': 'Match already started - NO_CACHE',
                'recommended_action': 'LIVE_TRACKING'
            }
        
        hours_to_kickoff = time_delta.total_seconds() / 3600
        minutes_to_kickoff = time_delta.total_seconds() / 60
        
        # Zone detection
        if minutes_to_kickoff < self.config.zone_warmup_minutes:
            base_ttl = self.config.zone_warmup_ttl
            zone = 'warmup'
            reasoning = f"Warm-up period (T-{minutes_to_kickoff:.0f}min) - Ultra-short TTL {base_ttl}s"
        elif hours_to_kickoff < self.config.zone_golden_hours:
            base_ttl = self.config.zone_golden_ttl
            zone = 'golden'
            reasoning = f"GOLDEN HOUR (T-{hours_to_kickoff:.1f}h) - Late steam capture - TTL {base_ttl}s"
        elif hours_to_kickoff < self.config.zone_active_hours:
            base_ttl = self.config.zone_active_ttl
            zone = 'active'
            reasoning = f"Active market (T-{hours_to_kickoff:.1f}h) - High volatility - TTL {base_ttl}s"
        elif hours_to_kickoff < self.config.zone_prematch_hours:
            base_ttl = self.config.zone_prematch_ttl
            zone = 'prematch'
            reasoning = f"Pre-match (T-{hours_to_kickoff:.1f}h) - Moderate volatility - TTL {base_ttl}s"
        else:
            base_ttl = self.config.zone_standard_ttl
            zone = 'standard'
            reasoning = f"Standard period (T-{hours_to_kickoff:.1f}h) - Low volatility - TTL {base_ttl}s"
        
        # Lineup bonus
        final_ttl = base_ttl
        if lineup_confirmed and zone in ['active', 'prematch', 'standard']:
            final_ttl = min(
                int(base_ttl * self.config.lineup_confirmed_multiplier),
                self.config.lineup_confirmed_max_ttl
            )
            reasoning += f" | LINEUP CONFIRMED → Extended TTL {final_ttl}s (×{self.config.lineup_confirmed_multiplier})"
        
        logger.info(
            "Golden Hour TTL calculated",
            zone=zone,
            hours_to_kickoff=hours_to_kickoff,
            base_ttl=base_ttl,
            final_ttl=final_ttl,
            lineup_confirmed=lineup_confirmed
        )
        
        return {
            'ttl': final_ttl,
            'zone': zone,
            'hours_to_kickoff': hours_to_kickoff,
            'minutes_to_kickoff': minutes_to_kickoff,
            'reasoning': reasoning,
            'lineup_bonus_applied': lineup_confirmed and final_ttl != base_ttl
        }
    
    def get_zone_distribution_stats(self) -> dict:
        """Get statistical distribution of zones for monitoring"""
        return {
            'warmup': {'volume_pct': 5, 'volatility': 'very_high', 'ttl': self.config.zone_warmup_ttl},
            'golden': {'volume_pct': 25, 'volatility': 'very_high', 'ttl': self.config.zone_golden_ttl},
            'active': {'volume_pct': 35, 'volatility': 'high', 'ttl': self.config.zone_active_ttl},
            'prematch': {'volume_pct': 25, 'volatility': 'medium', 'ttl': self.config.zone_prematch_ttl},
            'standard': {'volume_pct': 15, 'volatility': 'low', 'ttl': self.config.zone_standard_ttl}
        }
