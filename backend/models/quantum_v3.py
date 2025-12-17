"""
TeamQuantumDnaV3 ORM Model - Hedge Fund Grade Alpha
====================================================

SQLAlchemy 2.0 ORM model for quantum.team_quantum_dna_v3 table.
MAPPING EXACT des 60 colonnes de la table PostgreSQL.

Architecture Option D+:
- Typed JSONB columns via Pydantic schemas
- Hybrid properties for SQL queries on JSON fields
- Computed properties for derived metrics
- Query helpers for common patterns

Usage:
    from models.quantum_v3 import TeamQuantumDnaV3
    
    # Get team by name
    liverpool = TeamQuantumDnaV3.get_by_name(session, "Liverpool")
    print(liverpool.narrative_fingerprint_tags)
"""

from datetime import datetime
from typing import Optional, List, Any, TYPE_CHECKING, ClassVar
from functools import cached_property

from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, Boolean,
    func, text, cast,
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, Session

from models.base import Base, TimestampMixin
from schemas.enums import Tier, League, GKStatus, GamestateType, BestStrategy

# Import DNA Schemas for Option D+ (typed properties)
from schemas.dna import (
    TacticalDNA,
    MarketDNA,
    GamestateDNA,
    MomentumDNA,
    GoalkeeperDNA,
    TimingDNA,
    PsycheDNA,
    LuckDNA,
    ContextDNA,
    HomeAwayDNA,
    FormDNA,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class TeamQuantumDnaV3(Base):
    """
    ORM Model for quantum.team_quantum_dna_v3 table.
    
    MAPPING EXACT des 60 colonnes PostgreSQL:
    - 28 colonnes scalaires (TEXT, FLOAT, INTEGER, TIMESTAMP)
    - 31 colonnes JSONB (vecteurs ADN)
    - 1 colonne ARRAY (narrative_fingerprint_tags)
    """
    
    __tablename__ = "team_quantum_dna_v3"
    __table_args__ = {"schema": "quantum"}
    
    # ══════════════════════════════════════════════════════════════════════
    # PRIMARY KEY & IDENTIFIERS (Colonnes exactes DB)
    # ══════════════════════════════════════════════════════════════════════
    
    team_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    team_name_normalized: Mapped[Optional[str]] = mapped_column(String(100))
    league: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    
    # ══════════════════════════════════════════════════════════════════════
    # CLASSIFICATION & TIER (Colonnes exactes DB)
    # ══════════════════════════════════════════════════════════════════════
    
    tier: Mapped[Optional[str]] = mapped_column(String(20))
    tier_rank: Mapped[Optional[int]] = mapped_column(Integer)
    current_style: Mapped[Optional[str]] = mapped_column(String(50))
    best_strategy: Mapped[Optional[str]] = mapped_column(String(50))
    
    # ══════════════════════════════════════════════════════════════════════
    # PERFORMANCE METRICS - Scalaires (Colonnes exactes DB)
    # ══════════════════════════════════════════════════════════════════════
    
    total_matches: Mapped[Optional[int]] = mapped_column(Integer)
    total_bets: Mapped[Optional[int]] = mapped_column(Integer)
    total_wins: Mapped[Optional[int]] = mapped_column(Integer)
    total_losses: Mapped[Optional[int]] = mapped_column(Integer)
    win_rate: Mapped[Optional[float]] = mapped_column(Float)
    roi: Mapped[Optional[float]] = mapped_column(Float)
    total_pnl: Mapped[Optional[float]] = mapped_column(Float)
    avg_clv: Mapped[Optional[float]] = mapped_column(Float)
    
    # Loss analysis
    unlucky_losses: Mapped[Optional[int]] = mapped_column(Integer)
    bad_analysis_losses: Mapped[Optional[int]] = mapped_column(Integer)
    unlucky_pct: Mapped[Optional[float]] = mapped_column(Float)
    
    # Season & timestamps
    season: Mapped[Optional[str]] = mapped_column(String(20))
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_audit_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # ══════════════════════════════════════════════════════════════════════
    # NARRATIVE FINGERPRINT TAGS (ARRAY - Colonne exacte DB)
    # ══════════════════════════════════════════════════════════════════════
    
    narrative_fingerprint_tags: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(Text), 
        nullable=True,
        comment="DNA tags: GEGENPRESS, GK_ELITE, COMEBACK_KING, etc."
    )
    
    # ══════════════════════════════════════════════════════════════════════
    # DNA VECTORS - JSONB (31 colonnes exactes DB)
    # ══════════════════════════════════════════════════════════════════════
    
    # Core DNA vectors
    market_dna: Mapped[Optional[dict]] = mapped_column(JSONB)
    context_dna: Mapped[Optional[dict]] = mapped_column(JSONB)
    temporal_dna: Mapped[Optional[dict]] = mapped_column(JSONB)
    nemesis_dna: Mapped[Optional[dict]] = mapped_column(JSONB)
    psyche_dna: Mapped[Optional[dict]] = mapped_column(JSONB)
    roster_dna: Mapped[Optional[dict]] = mapped_column(JSONB)
    physical_dna: Mapped[Optional[dict]] = mapped_column(JSONB)
    luck_dna: Mapped[Optional[dict]] = mapped_column(JSONB)
    tactical_dna: Mapped[Optional[dict]] = mapped_column(JSONB)
    chameleon_dna: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Extended DNA vectors
    meta_dna: Mapped[Optional[dict]] = mapped_column(JSONB)
    sentiment_dna: Mapped[Optional[dict]] = mapped_column(JSONB)
    clutch_dna: Mapped[Optional[dict]] = mapped_column(JSONB)
    shooting_dna: Mapped[Optional[dict]] = mapped_column(JSONB)
    card_dna: Mapped[Optional[dict]] = mapped_column(JSONB)
    corner_dna: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Analysis & profiles
    form_analysis: Mapped[Optional[dict]] = mapped_column(JSONB)
    current_season: Mapped[Optional[dict]] = mapped_column(JSONB)
    status_2025_2026: Mapped[Optional[dict]] = mapped_column(JSONB)
    profile_2d: Mapped[Optional[dict]] = mapped_column(JSONB)
    signature_v3: Mapped[Optional[dict]] = mapped_column(JSONB)
    advanced_profile_v8: Mapped[Optional[dict]] = mapped_column(JSONB)
    friction_signatures: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Narrative profiles
    narrative_tactical_profile: Mapped[Optional[dict]] = mapped_column(JSONB)
    narrative_mvp: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Strategy & markets
    exploit_markets: Mapped[Optional[dict]] = mapped_column(JSONB)
    avoid_markets: Mapped[Optional[dict]] = mapped_column(JSONB)
    optimal_scenarios: Mapped[Optional[dict]] = mapped_column(JSONB)
    optimal_strategies: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Legacy
    quantum_dna_legacy: Mapped[Optional[dict]] = mapped_column(JSONB)
    betting_identity: Mapped[Optional[dict]] = mapped_column(JSONB)

    # ══════════════════════════════════════════════════════════════════════
    # OPTION D+: TYPED DNA PROPERTIES (avec lazy parsing)
    # ══════════════════════════════════════════════════════════════════════

    @property
    def tactical_dna_typed(self) -> Optional[TacticalDNA]:
        """
        Tactical DNA avec validation Pydantic (Option D+).

        Returns:
            TacticalDNA object avec autocomplétion IDE

        Usage:
            team.tactical_dna_typed.possession_pct  # float
            team.tactical_dna_typed.pressing_intensity  # str
        """
        if not hasattr(self, '_tactical_dna_parsed'):
            self._tactical_dna_parsed = None
        if self._tactical_dna_parsed is None and self.tactical_dna:
            self._tactical_dna_parsed = TacticalDNA.from_dict(self.tactical_dna)
        return self._tactical_dna_parsed

    @property
    def market_dna_typed(self) -> Optional[MarketDNA]:
        """Market DNA avec validation Pydantic."""
        if not hasattr(self, '_market_dna_parsed'):
            self._market_dna_parsed = None
        if self._market_dna_parsed is None and self.market_dna:
            self._market_dna_parsed = MarketDNA.from_dict(self.market_dna)
        return self._market_dna_parsed

    @property
    def psyche_dna_typed(self) -> Optional[PsycheDNA]:
        """Psyche DNA avec validation Pydantic."""
        if not hasattr(self, '_psyche_dna_parsed'):
            self._psyche_dna_parsed = None
        if self._psyche_dna_parsed is None and self.psyche_dna:
            self._psyche_dna_parsed = PsycheDNA.from_dict(self.psyche_dna)
        return self._psyche_dna_parsed

    @property
    def luck_dna_typed(self) -> Optional[LuckDNA]:
        """Luck DNA avec validation Pydantic."""
        if not hasattr(self, '_luck_dna_parsed'):
            self._luck_dna_parsed = None
        if self._luck_dna_parsed is None and self.luck_dna:
            self._luck_dna_parsed = LuckDNA.from_dict(self.luck_dna)
        return self._luck_dna_parsed

    @property
    def context_dna_typed(self) -> Optional[ContextDNA]:
        """Context DNA avec validation Pydantic."""
        if not hasattr(self, '_context_dna_parsed'):
            self._context_dna_parsed = None
        if self._context_dna_parsed is None and self.context_dna:
            self._context_dna_parsed = ContextDNA.from_dict(self.context_dna)
        return self._context_dna_parsed

    # ══════════════════════════════════════════════════════════════════════
    # COMPUTED PROPERTIES (Métriques dérivées)
    # ══════════════════════════════════════════════════════════════════════
    
    @property
    def tier_enum(self) -> Optional[Tier]:
        """Tier as enum (type-safe)."""
        if self.tier:
            try:
                return Tier(self.tier)
            except ValueError:
                return Tier.UNKNOWN
        return None

    @property
    def league_enum(self) -> Optional[League]:
        """League as enum (type-safe)."""
        if self.league:
            try:
                return League(self.league)
            except ValueError:
                return None
        return None

    @property
    def is_elite(self) -> bool:
        """True if team is ELITE tier with win_rate > 55%."""
        return (
            self.tier == Tier.ELITE.value and 
            self.win_rate is not None and 
            self.win_rate > 55
        )
    
    @property
    def gk_status(self) -> str:
        """Extract GK_ tag from narrative tags."""
        for tag in (self.narrative_fingerprint_tags or []):
            if tag.startswith("GK_"):
                return tag
        return "GK_UNKNOWN"
    
    @property
    def gamestate_type(self) -> str:
        """Extract gamestate tag (COMEBACK_KING, etc.)."""
        gamestate_tags = {"COMEBACK_KING", "COLLAPSE_LEADER", "NEUTRAL", "FRONTRUNNER"}
        for tag in (self.narrative_fingerprint_tags or []):
            if tag in gamestate_tags:
                return tag
        return "NEUTRAL"
    
    @property
    def tactical_style_tag(self) -> Optional[str]:
        """Extract tactical style tag (GEGENPRESS, etc.)."""
        style_tags = {"GEGENPRESS", "POSSESSION", "LOW_BLOCK", "BALANCED", "TRANSITION"}
        for tag in (self.narrative_fingerprint_tags or []):
            if tag in style_tags:
                return tag
        return None
    
    @property
    def tag_count(self) -> int:
        """Number of narrative fingerprint tags."""
        return len(self.narrative_fingerprint_tags or [])
    
    @property
    def quality_score(self) -> float:
        """
        Computed quality score (0-100).
        
        Formula:
        - Win rate: 40% weight
        - ROI: 30% weight (capped at 50)
        - Tag count: 30% weight (5 = max bonus)
        """
        score = 0.0
        
        # Win rate component (40%)
        if self.win_rate:
            score += min(self.win_rate, 100) * 0.4
        
        # ROI component (30%)
        if self.roi:
            capped_roi = max(min(self.roi, 50), -50)
            score += (capped_roi + 50) * 0.3
        
        # Tag count component (30%)
        tag_bonus = min(self.tag_count, 5) * 6
        score += tag_bonus
        
        return round(score, 2)
    
    # ══════════════════════════════════════════════════════════════════════
    # TAG HELPERS
    # ══════════════════════════════════════════════════════════════════════
    
    def has_tag(self, tag: str) -> bool:
        """Check if team has a specific tag."""
        return tag in (self.narrative_fingerprint_tags or [])
    
    def has_any_tag(self, tags: List[str]) -> bool:
        """Check if team has any of the specified tags."""
        team_tags = set(self.narrative_fingerprint_tags or [])
        return bool(team_tags.intersection(tags))
    
    def has_all_tags(self, tags: List[str]) -> bool:
        """Check if team has all specified tags."""
        team_tags = set(self.narrative_fingerprint_tags or [])
        return all(tag in team_tags for tag in tags)
    
    def get_tags_by_prefix(self, prefix: str) -> List[str]:
        """Get all tags starting with prefix (e.g., 'GK_')."""
        return [
            tag for tag in (self.narrative_fingerprint_tags or [])
            if tag.startswith(prefix)
        ]
    
    # ══════════════════════════════════════════════════════════════════════
    # QUERY CLASS METHODS
    # ══════════════════════════════════════════════════════════════════════
    
    @classmethod
    def get_by_name(cls, session: Session, name: str) -> Optional["TeamQuantumDnaV3"]:
        """Get team by name (case-insensitive)."""
        return session.query(cls).filter(
            func.lower(cls.team_name) == name.lower()
        ).first()
    
    @classmethod
    def get_by_tags(
        cls, 
        session: Session, 
        tags: List[str], 
        match_all: bool = True
    ) -> List["TeamQuantumDnaV3"]:
        """Get teams by tags."""
        query = session.query(cls)
        
        if match_all:
            for tag in tags:
                query = query.filter(cls.narrative_fingerprint_tags.contains([tag]))
        else:
            query = query.filter(cls.narrative_fingerprint_tags.overlap(tags))
        
        return query.all()
    
    @classmethod
    def get_by_league(cls, session: Session, league: str) -> List["TeamQuantumDnaV3"]:
        """Get all teams in a league."""
        return session.query(cls).filter(cls.league == league).all()
    
    @classmethod
    def get_elite_teams(
        cls, 
        session: Session, 
        league: Optional[str] = None
    ) -> List["TeamQuantumDnaV3"]:
        """Get all ELITE tier teams."""
        query = session.query(cls).filter(cls.tier == Tier.ELITE.value)
        if league:
            query = query.filter(cls.league == league)
        return query.all()
    
    @classmethod
    def get_all(cls, session: Session) -> List["TeamQuantumDnaV3"]:
        """Get all teams."""
        return session.query(cls).all()
    
    @classmethod
    def count(cls, session: Session) -> int:
        """Count total teams."""
        return session.query(func.count(cls.team_id)).scalar() or 0

    @classmethod
    def count_by_league(cls, session: Session) -> dict:
        """
        Count teams per league.

        Returns:
            Dict[str, int] - League name to team count
            Example: {'Premier League': 20, 'La Liga': 20, ...}
        """
        results = session.query(
            cls.league,
            func.count(cls.team_id)
        ).group_by(cls.league).all()
        return {league: count for league, count in results if league}

    # ══════════════════════════════════════════════════════════════════════
    # SERIALIZATION
    # ══════════════════════════════════════════════════════════════════════
    
    def to_dict(self, include_dna: bool = False) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "team_id": self.team_id,
            "team_name": self.team_name,
            "league": self.league,
            "tier": self.tier,
            "current_style": self.current_style,
            "best_strategy": self.best_strategy,
            "total_matches": self.total_matches,
            "total_bets": self.total_bets,
            "win_rate": self.win_rate,
            "roi": self.roi,
            "total_pnl": self.total_pnl,
            "avg_clv": self.avg_clv,
            "tags": self.narrative_fingerprint_tags,
            "tag_count": self.tag_count,
            "quality_score": self.quality_score,
            "gk_status": self.gk_status,
            "gamestate_type": self.gamestate_type,
            "tactical_style": self.tactical_style_tag,
            "is_elite": self.is_elite,
        }
        
        if include_dna:
            result["tactical_dna"] = self.tactical_dna
            result["market_dna"] = self.market_dna
            result["psyche_dna"] = self.psyche_dna
            result["luck_dna"] = self.luck_dna
            result["context_dna"] = self.context_dna
        
        return result
    
    def to_summary(self) -> dict[str, Any]:
        """Short summary for lists and previews."""
        return {
            "team_id": self.team_id,
            "team_name": self.team_name,
            "league": self.league,
            "tier": self.tier,
            "tags": self.narrative_fingerprint_tags,
            "win_rate": self.win_rate,
        }
    
    # ══════════════════════════════════════════════════════════════════════
    # REPR & STR
    # ══════════════════════════════════════════════════════════════════════
    
    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        wr = f"WR:{self.win_rate:.1f}%" if self.win_rate else "WR:N/A"
        return (
            f"<TeamQuantumDnaV3 "
            f"id={self.team_id} "
            f"'{self.team_name}' "
            f"[{self.league}] "
            f"[{self.tier}] "
            f"{wr} "
            f"Tags:{self.tag_count}>"
        )
    
    def __str__(self) -> str:
        """Human-readable string."""
        tags_preview = ", ".join((self.narrative_fingerprint_tags or [])[:3])
        return f"{self.team_name} ({self.league}) - {tags_preview}"
