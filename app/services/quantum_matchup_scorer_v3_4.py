#!/usr/bin/env python3
"""
🔥 QUANTUM MATCHUP SCORER V3.4.2 - SMART CONFLICT RESOLUTION

CORRECTIONS V3.4.2:
1. Smart Conflict: Momentum BLAZING/HOT override Z faible
2. Seuils ajustés: moins de faux EXTREME
3. Resolution: Suivre le signal le PLUS FORT, pas SKIP

Modifié: 2025-12-19 - Documenté divergence market_registry
"""

import math
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import statistics

import sys
sys.path.append('/home/Mon_ps/app/services')
from quantum_scorer_v2_4 import QuantumScorerV24

# Note: market_registry.MarketType utilise des valeurs normalisées ("home", "ah_home_m05")
# Ce fichier garde ses propres valeurs descriptives pour compatibilité ("1X2", "Asian Total")
# Migration future: aligner les valeurs avec market_registry

DB_CONFIG = {
    "host": "localhost", "port": 5432, "database": "monps_db",
    "user": "monps_user", "password": "monps_secure_password_2024"
}


class MomentumTrend(Enum):
    BLAZING = "🔥 BLAZING"
    HOT = "🌡️ HOT"
    WARMING = "📈 WARMING"
    NEUTRAL = "➡️ NEUTRAL"
    COOLING = "📉 COOLING"
    COLD = "❄️ COLD"
    FREEZING = "🥶 FREEZING"


class MarketType(Enum):
    MATCH_WINNER = "1X2"
    ASIAN_TOTAL = "Asian Total"


class DecisionType(Enum):
    CHAOS_PLAY = "CHAOS_PLAY"
    VALUE_SECURE = "VALUE_SECURE"
    SHOOTOUT = "SHOOTOUT"
    PURE_VALUE = "PURE_VALUE"
    MOMENTUM_PLAY = "MOMENTUM_PLAY"  # NEW: Momentum override Z
    NO_EDGE = "NO_EDGE"


class CLVSignal(Enum):
    SWEET_SPOT = "SWEET_SPOT"
    GOOD = "GOOD"
    DANGER = "DANGER"
    NO_SIGNAL = "NO_SIGNAL"


class ConflictResolution(Enum):
    FOLLOW_Z = "FOLLOW_Z"           # Z-Score plus fiable
    FOLLOW_MOMENTUM = "FOLLOW_MOM"  # Momentum plus fiable
    FOLLOW_BOTH = "ALIGNED"         # Pas de conflit
    REDUCED_Z = "REDUCED_Z"         # Z avec réduction
    SKIP = "SKIP"                   # Trop incertain


@dataclass
class MatchResult:
    venue: str
    opponent: str
    goals_for: int
    goals_against: int
    outcome: str
    date: datetime
    
    @property
    def points(self) -> int:
        return 3 if self.outcome == 'win' else (1 if self.outcome == 'draw' else 0)


@dataclass
class MomentumL5:
    team_name: str
    matches: List[MatchResult]
    
    @property
    def n_matches(self) -> int:
        return len(self.matches)
    
    @property
    def wins(self) -> int:
        return sum(1 for m in self.matches if m.outcome == 'win')
    
    @property
    def draws(self) -> int:
        return sum(1 for m in self.matches if m.outcome == 'draw')
    
    @property
    def losses(self) -> int:
        return sum(1 for m in self.matches if m.outcome == 'loss')
    
    @property
    def points(self) -> int:
        return sum(m.points for m in self.matches)
    
    @property
    def form_percentage(self) -> float:
        if self.n_matches == 0:
            return 50.0
        return (self.points / (self.n_matches * 3)) * 100
    
    @property
    def goals_scored(self) -> int:
        return sum(m.goals_for for m in self.matches)
    
    @property
    def goals_conceded(self) -> int:
        return sum(m.goals_against for m in self.matches)
    
    @property
    def goal_diff(self) -> int:
        return self.goals_scored - self.goals_conceded
    
    @property
    def current_streak(self) -> Tuple[str, int]:
        if not self.matches:
            return ("none", 0)
        streak_type = self.matches[0].outcome
        streak_len = 1
        for m in self.matches[1:]:
            if m.outcome == streak_type:
                streak_len += 1
            else:
                break
        return (streak_type, streak_len)
    
    @property
    def l3_points(self) -> int:
        return sum(m.points for m in self.matches[:3])
    
    @property
    def momentum_acceleration(self) -> float:
        if self.n_matches < 5:
            return 0.0
        l3_avg = self.l3_points / 3
        l2_old = sum(m.points for m in self.matches[3:5]) / 2 if len(self.matches) >= 5 else l3_avg
        return round((l3_avg - l2_old) / 3 * 100, 1)
    
    @property
    def home_form(self) -> float:
        home = [m for m in self.matches if m.venue == 'HOME']
        return sum(m.points for m in home) / (len(home) * 3) * 100 if home else 50.0
    
    @property
    def away_form(self) -> float:
        away = [m for m in self.matches if m.venue == 'AWAY']
        return sum(m.points for m in away) / (len(away) * 3) * 100 if away else 50.0
    
    @property
    def momentum_score(self) -> float:
        form_score = self.form_percentage
        gd_per_match = self.goal_diff / max(self.n_matches, 1)
        goal_score = max(0, min(100, 50 + gd_per_match * 15))
        
        streak_type, streak_len = self.current_streak
        if streak_type == 'win':
            streak_score = min(100, 50 + streak_len * 12)
        elif streak_type == 'draw':
            streak_score = 45
        else:
            streak_score = max(0, 50 - streak_len * 12)
        
        accel_score = max(0, min(100, 50 + self.momentum_acceleration / 2))
        
        return round(0.35 * form_score + 0.20 * goal_score + 0.25 * streak_score + 0.20 * accel_score, 1)
    
    @property
    def trend(self) -> MomentumTrend:
        score = self.momentum_score
        accel = self.momentum_acceleration
        streak_type, streak_len = self.current_streak
        
        # BLAZING: score élevé OU win streak >= 4
        if score >= 75 or (streak_type == 'win' and streak_len >= 4):
            return MomentumTrend.BLAZING
        elif score >= 65 or (streak_type == 'win' and streak_len >= 3):
            return MomentumTrend.HOT
        elif score >= 50 and accel > 10:
            return MomentumTrend.WARMING
        elif 40 <= score < 60:
            return MomentumTrend.NEUTRAL
        elif score < 50 and accel < -10:
            return MomentumTrend.COOLING
        elif score < 35 or (streak_type == 'loss' and streak_len >= 3):
            return MomentumTrend.COLD
        elif score < 20:
            return MomentumTrend.FREEZING
        return MomentumTrend.NEUTRAL
    
    @property
    def stake_multiplier(self) -> float:
        return {
            MomentumTrend.BLAZING: 1.25,
            MomentumTrend.HOT: 1.15,
            MomentumTrend.WARMING: 1.05,
            MomentumTrend.NEUTRAL: 1.00,
            MomentumTrend.COOLING: 0.92,
            MomentumTrend.COLD: 0.80,
            MomentumTrend.FREEZING: 0.65,
        }.get(self.trend, 1.0)
    
    @property
    def is_hot(self) -> bool:
        return self.trend in [MomentumTrend.BLAZING, MomentumTrend.HOT]
    
    @property
    def is_cold(self) -> bool:
        return self.trend in [MomentumTrend.COLD, MomentumTrend.FREEZING]


@dataclass
class SmartConflictResolution:
    """Résolution intelligente des conflits Z vs Momentum"""
    z_favorite: str
    z_edge: float
    momentum_favorite: str
    momentum_edge: float
    resolution: ConflictResolution
    follow_team: str           # L'équipe à parier
    stake_multiplier: float    # Multiplicateur final
    reasoning: str
    confidence_boost: float    # Boost si aligné


@dataclass 
class CLVData:
    home_clv: float
    draw_clv: float
    away_clv: float
    hours_tracked: float
    signal: CLVSignal
    recommended_side: str


@dataclass
class BayesianKellyResult:
    mean_prob: float
    std_prob: float
    adjusted_prob: float
    edge_percentage: float
    recommended_stake: float
    is_positive: bool
    reasoning: str


@dataclass
class SmartBet:
    market: MarketType
    selection: str
    line: Optional[float]
    our_probability: float
    uncertainty_std: float
    kelly: BayesianKellyResult
    sizing: str
    reasoning: str


@dataclass
class MatchupDecisionV34:
    home_team: str
    away_team: str
    home_z_score: float
    away_z_score: float
    z_edge: float
    friction_score: float
    chaos_potential: float
    total_xg: float
    home_momentum: Optional[MomentumL5]
    away_momentum: Optional[MomentumL5]
    momentum_edge: float
    conflict_resolution: SmartConflictResolution
    clv_data: Optional[CLVData]
    decision_type: DecisionType
    decision_reasoning: str
    primary_bet: SmartBet
    total_recommended_stake: float
    warnings: List[str]
    overall_confidence: float


class SmartConflictResolver:
    """
    SMART CONFLICT RESOLUTION
    
    Règles:
    1. Si Momentum = BLAZING/HOT et Z-edge < 2.0 → FOLLOW_MOMENTUM
    2. Si Z-edge > 2.5 et Momentum pas COLD → FOLLOW_Z
    3. Si les deux ALIGNED → BOOST
    4. Si Momentum COLD contre Z favorable → REDUCED_Z
    5. Sinon → FOLLOW_Z avec réduction
    """
    
    @staticmethod
    def resolve(home_team: str, away_team: str,
                home_z: float, away_z: float,
                home_mom: Optional[MomentumL5],
                away_mom: Optional[MomentumL5]) -> SmartConflictResolution:
        
        # Z-Score analysis
        z_diff = home_z - away_z
        z_favorite = home_team if z_diff > 0 else away_team
        z_underdog = away_team if z_diff > 0 else home_team
        z_edge = abs(z_diff)
        
        # Momentum analysis
        if home_mom and away_mom:
            mom_diff = home_mom.momentum_score - away_mom.momentum_score
            momentum_favorite = home_team if mom_diff > 0 else away_team
            momentum_edge = abs(mom_diff)
            
            fav_is_home = (z_favorite == home_team)
            z_fav_mom = home_mom if fav_is_home else away_mom
            z_und_mom = away_mom if fav_is_home else home_mom
        else:
            momentum_favorite = z_favorite
            momentum_edge = 0
            z_fav_mom = None
            z_und_mom = None
        
        aligned = (z_favorite == momentum_favorite)
        
        # === RESOLUTION LOGIC ===
        
        # CASE 1: ALIGNED - Both agree
        if aligned:
            boost = 1.0
            if z_fav_mom and z_fav_mom.is_hot:
                boost = 1.15  # Hot streak bonus
            return SmartConflictResolution(
                z_favorite=z_favorite,
                z_edge=z_edge,
                momentum_favorite=momentum_favorite,
                momentum_edge=momentum_edge,
                resolution=ConflictResolution.FOLLOW_BOTH,
                follow_team=z_favorite,
                stake_multiplier=boost,
                reasoning=f"✅ ALIGNÉ: Z + Momentum → {z_favorite}",
                confidence_boost=0.10
            )
        
        # CASE 2: Z underdog is BLAZING/HOT → Follow Momentum
        if z_und_mom and z_und_mom.is_hot and z_edge < 2.0:
            return SmartConflictResolution(
                z_favorite=z_favorite,
                z_edge=z_edge,
                momentum_favorite=momentum_favorite,
                momentum_edge=momentum_edge,
                resolution=ConflictResolution.FOLLOW_MOMENTUM,
                follow_team=momentum_favorite,
                stake_multiplier=z_und_mom.stake_multiplier,
                reasoning=f"🔥 MOMENTUM OVERRIDE: {momentum_favorite} {z_und_mom.trend.value}",
                confidence_boost=0.05
            )
        
        # CASE 3: Z very strong (> 2.5) → Follow Z
        if z_edge > 2.5 and (not z_fav_mom or not z_fav_mom.is_cold):
            return SmartConflictResolution(
                z_favorite=z_favorite,
                z_edge=z_edge,
                momentum_favorite=momentum_favorite,
                momentum_edge=momentum_edge,
                resolution=ConflictResolution.FOLLOW_Z,
                follow_team=z_favorite,
                stake_multiplier=0.90,  # Slight reduction
                reasoning=f"📊 Z FORT ({z_edge:.2f}): suivre {z_favorite}",
                confidence_boost=0.0
            )
        
        # CASE 4: Z favorite is COLD → Reduce heavily
        if z_fav_mom and z_fav_mom.is_cold:
            return SmartConflictResolution(
                z_favorite=z_favorite,
                z_edge=z_edge,
                momentum_favorite=momentum_favorite,
                momentum_edge=momentum_edge,
                resolution=ConflictResolution.REDUCED_Z,
                follow_team=z_favorite,
                stake_multiplier=0.50,  # Heavy reduction
                reasoning=f"❄️ Z favori {z_favorite} en COLD → réduction 50%",
                confidence_boost=-0.10
            )
        
        # CASE 5: Moderate conflict → Follow Z with reduction
        reduction = 0.75 if momentum_edge > 20 else 0.85
        return SmartConflictResolution(
            z_favorite=z_favorite,
            z_edge=z_edge,
            momentum_favorite=momentum_favorite,
            momentum_edge=momentum_edge,
            resolution=ConflictResolution.REDUCED_Z,
            follow_team=z_favorite,
            stake_multiplier=reduction,
            reasoning=f"⚠️ Conflit modéré: Z→{z_favorite} (×{reduction:.2f})",
            confidence_boost=-0.05
        )


class MomentumCalculator:
    def __init__(self, conn):
        self.conn = conn
    
    def get_team_momentum(self, team_name: str, n_matches: int = 5) -> Optional[MomentumL5]:
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                WITH deduped AS (
                    SELECT DISTINCT ON (DATE(commence_time), home_team, away_team)
                        CASE WHEN home_team ILIKE %s THEN 'HOME' ELSE 'AWAY' END as venue,
                        CASE WHEN home_team ILIKE %s THEN away_team ELSE home_team END as opponent,
                        CASE WHEN home_team ILIKE %s THEN score_home ELSE score_away END as goals_for,
                        CASE WHEN home_team ILIKE %s THEN score_away ELSE score_home END as goals_against,
                        CASE 
                            WHEN home_team ILIKE %s AND outcome = 'home' THEN 'win'
                            WHEN away_team ILIKE %s AND outcome = 'away' THEN 'win'
                            WHEN outcome = 'draw' THEN 'draw'
                            ELSE 'loss'
                        END as result,
                        commence_time
                    FROM match_results
                    WHERE (home_team ILIKE %s OR away_team ILIKE %s)
                      AND is_finished = true AND score_home IS NOT NULL
                    ORDER BY DATE(commence_time) DESC, home_team, away_team, fetched_at DESC
                )
                SELECT * FROM deduped ORDER BY commence_time DESC LIMIT %s
            """, tuple([f"%{team_name}%"] * 8) + (n_matches,))
            results = cur.fetchall()
        
        if not results:
            return None
        
        matches = [MatchResult(
            venue=r['venue'], opponent=r['opponent'],
            goals_for=r['goals_for'] or 0, goals_against=r['goals_against'] or 0,
            outcome=r['result'], date=r['commence_time']
        ) for r in results]
        
        return MomentumL5(team_name=team_name, matches=matches)


class QuantumMatchupScorerV34:
    """V3.4.2 - Smart Conflict Resolution"""
    
    CHAOS_EXTREME = 80
    XG_SHOOTOUT = 3.5
    Z_STRONG_EDGE = 2.0
    Z_MEDIUM_EDGE = 1.0
    HOME_ADVANTAGE_XG = 0.25
    
    MAX_STAKE = 5.0
    BANKROLL = 100.0
    QUANTUM_EDGE_FACTOR = 0.08
    
    def __init__(self):
        self.conn = None
        self.v24_scorer = QuantumScorerV24()
        self.momentum_calc = None
        
    def connect(self):
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
            self.momentum_calc = MomentumCalculator(self.conn)
            
    def close(self):
        if self.conn:
            self.conn.close()
        self.v24_scorer.close()

    def _get_clv_data(self, home_team: str, away_team: str) -> Optional[CLVData]:
        self.connect()
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT home_clv, draw_clv, away_clv, hours_tracked
                    FROM v_clv_from_odds WHERE bookmaker = 'Pinnacle'
                      AND ((home_team ILIKE %s AND away_team ILIKE %s)
                        OR (home_team ILIKE %s AND away_team ILIKE %s))
                    ORDER BY hours_tracked DESC LIMIT 1
                """, (f"%{home_team}%", f"%{away_team}%", f"%{away_team}%", f"%{home_team}%"))
                r = cur.fetchone()
        except:
            return None
        if not r:
            return None
        max_clv = max(float(r['home_clv'] or 0), float(r['draw_clv'] or 0), float(r['away_clv'] or 0))
        signal = CLVSignal.SWEET_SPOT if 5 <= max_clv <= 10 else (CLVSignal.DANGER if max_clv > 10 else CLVSignal.NO_SIGNAL)
        return CLVData(float(r['home_clv'] or 0), float(r['draw_clv'] or 0), float(r['away_clv'] or 0),
                       float(r['hours_tracked'] or 0), signal, "NONE")

    def _get_team_dna(self, team_name: str) -> Optional[Dict]:
        self.connect()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT team_name, tier, quantum_dna FROM quantum.team_profiles WHERE team_name ILIKE %s LIMIT 1",
                        (f"%{team_name}%",))
            r = cur.fetchone()
        return dict(r) if r else None

    def _get_friction(self, team_a: str, team_b: str) -> Dict:
        self.connect()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT friction_score, chaos_potential, predicted_over25_prob
                FROM quantum.matchup_friction
                WHERE (team_a_name = %s AND team_b_name = %s) OR (team_a_name = %s AND team_b_name = %s) LIMIT 1
            """, (team_a, team_b, team_b, team_a))
            r = cur.fetchone()
        return dict(r) if r else {'friction_score': 50.0, 'chaos_potential': 50.0}

    def _calculate_xg(self, home_dna: Dict, away_dna: Dict, friction: float) -> float:
        hc = home_dna.get('quantum_dna', {}).get('current_season', {})
        ac = away_dna.get('quantum_dna', {}).get('current_season', {})
        home_xg = (float(hc.get('xg_for_avg', 1.3) or 1.3) + float(ac.get('xg_against_avg', 1.3) or 1.3)) / 2 + self.HOME_ADVANTAGE_XG
        away_xg = (float(ac.get('xg_for_avg', 1.3) or 1.3) + float(hc.get('xg_against_avg', 1.3) or 1.3)) / 2
        return round((home_xg + away_xg) * (1 + (friction - 50) / 150), 2)

    def _calculate_probability(self, home_z: float, away_z: float, 
                                resolution: SmartConflictResolution,
                                home_mom: Optional[MomentumL5],
                                away_mom: Optional[MomentumL5]) -> float:
        
        follow_home = (resolution.follow_team == resolution.z_favorite and home_z > away_z) or \
                      (resolution.follow_team != resolution.z_favorite and home_z < away_z)
        
        z_diff = home_z - away_z
        
        if resolution.resolution == ConflictResolution.FOLLOW_MOMENTUM:
            # Probabilité basée sur momentum
            if home_mom and away_mom:
                mom_diff = (home_mom.momentum_score - away_mom.momentum_score) / 100
                base = 0.50 + mom_diff * 0.15
            else:
                base = 0.50
        else:
            # Probabilité basée sur Z-score
            base = 0.45 + z_diff * 0.08 if follow_home else 0.45 - z_diff * 0.08
        
        return max(0.25, min(0.75, base))

    def _calculate_stake(self, z_edge: float, resolution: SmartConflictResolution,
                          chaos: float, tier: str) -> Tuple[float, str]:
        
        # Base stake from Z-edge
        if z_edge >= 2.5:
            base = 4.0
        elif z_edge >= 1.5:
            base = 3.0
        elif z_edge >= 1.0:
            base = 2.0
        elif z_edge >= 0.5:
            base = 1.5
        else:
            base = 1.0
        
        # Resolution multiplier
        stake = base * resolution.stake_multiplier
        
        # Chaos penalty
        if chaos > 80:
            stake *= 0.85
        
        # Tier bonus/penalty
        tier_mult = {'ELITE': 1.10, 'GOLD': 1.05, 'SILVER': 1.00, 'BRONZE': 0.90}.get(tier, 1.0)
        stake *= tier_mult
        
        # Cap
        stake = min(max(stake, 0), self.MAX_STAKE)
        
        return round(stake, 1), self._sizing_label(stake)

    def _sizing_label(self, stake: float) -> str:
        if stake >= 4.0: return "MAX"
        elif stake >= 2.5: return "NORMAL"
        elif stake >= 1.0: return "SMALL"
        elif stake > 0: return "MINI"
        return "SKIP"

    def _finalize_decision(self, z_edge: float, chaos: float, total_xg: float,
                           resolution: SmartConflictResolution) -> Tuple[DecisionType, str]:
        
        if resolution.resolution == ConflictResolution.FOLLOW_MOMENTUM:
            return DecisionType.MOMENTUM_PLAY, resolution.reasoning
        if chaos > self.CHAOS_EXTREME:
            return DecisionType.CHAOS_PLAY, f"⚠️ CHAOS ({chaos:.0f})"
        if total_xg > self.XG_SHOOTOUT:
            return DecisionType.SHOOTOUT, f"🔥 SHOOTOUT ({total_xg:.1f} xG)"
        if z_edge > self.Z_STRONG_EDGE:
            return DecisionType.VALUE_SECURE, "💰 VALUE FORTE"
        if z_edge > self.Z_MEDIUM_EDGE:
            return DecisionType.PURE_VALUE, "✅ PURE VALUE"
        return DecisionType.PURE_VALUE, "📊 VALUE"

    def analyze_matchup(self, home_team: str, away_team: str) -> Optional[MatchupDecisionV34]:
        self.connect()
        
        home_score = self.v24_scorer.calculate_score(home_team)
        away_score = self.v24_scorer.calculate_score(away_team)
        if not home_score or not away_score:
            return None
        
        home_z, away_z = home_score.vector.z_score, away_score.vector.z_score
        z_edge = abs(home_z - away_z)
        
        home_dna = self._get_team_dna(home_team)
        away_dna = self._get_team_dna(away_team)
        if not home_dna or not away_dna:
            return None
        
        friction_data = self._get_friction(home_team, away_team)
        friction = float(friction_data.get('friction_score', 50) or 50)
        chaos = float(friction_data.get('chaos_potential', 50) or 50)
        
        total_xg = self._calculate_xg(home_dna, away_dna, friction)
        
        # Momentum
        home_mom = self.momentum_calc.get_team_momentum(home_team, 5)
        away_mom = self.momentum_calc.get_team_momentum(away_team, 5)
        
        mom_edge = (home_mom.momentum_score - away_mom.momentum_score) if home_mom and away_mom else 0
        
        # SMART CONFLICT RESOLUTION
        resolution = SmartConflictResolver.resolve(
            home_team, away_team, home_z, away_z, home_mom, away_mom
        )
        
        clv_data = self._get_clv_data(home_team, away_team)
        
        decision_type, reasoning = self._finalize_decision(z_edge, chaos, total_xg, resolution)
        
        # Override for SHOOTOUT market
        if decision_type == DecisionType.SHOOTOUT:
            selection = "Over 3.0"
            market = MarketType.ASIAN_TOTAL
        else:
            selection = resolution.follow_team
            market = MarketType.MATCH_WINNER
        
        # Probability & Stake
        prob = self._calculate_probability(home_z, away_z, resolution, home_mom, away_mom)
        fav_tier = home_dna.get('tier', 'SILVER') if resolution.follow_team == home_team else away_dna.get('tier', 'SILVER')
        stake, sizing = self._calculate_stake(z_edge, resolution, chaos, fav_tier)
        
        # Uncertainty
        uncertainty = 0.10 + (0.05 if resolution.resolution != ConflictResolution.FOLLOW_BOTH else 0)
        if chaos > 80:
            uncertainty += 0.05
        
        kelly = BayesianKellyResult(
            mean_prob=prob, std_prob=uncertainty, adjusted_prob=prob - uncertainty**2/2,
            edge_percentage=round(self.QUANTUM_EDGE_FACTOR * z_edge * resolution.stake_multiplier * 100, 1),
            recommended_stake=stake, is_positive=stake > 0,
            reasoning=resolution.reasoning
        )
        
        bet = SmartBet(
            market=market, selection=selection, line=3.0 if market == MarketType.ASIAN_TOTAL else None,
            our_probability=prob, uncertainty_std=uncertainty, kelly=kelly, sizing=sizing,
            reasoning=f"{resolution.reasoning}"
        )
        
        warnings = []
        if chaos > 80:
            warnings.append(f"⚠️ CHAOS ({chaos:.0f})")
        if clv_data and clv_data.signal == CLVSignal.DANGER:
            warnings.append("⚠️ CLV DANGER")
        if resolution.resolution != ConflictResolution.FOLLOW_BOTH:
            warnings.append(f"⚔️ {resolution.resolution.value}")
        
        confidence = 0.75 + resolution.confidence_boost
        if chaos > 80:
            confidence -= 0.10
        
        return MatchupDecisionV34(
            home_team=home_team, away_team=away_team,
            home_z_score=home_z, away_z_score=away_z, z_edge=z_edge,
            friction_score=friction, chaos_potential=chaos, total_xg=total_xg,
            home_momentum=home_mom, away_momentum=away_mom, momentum_edge=mom_edge,
            conflict_resolution=resolution, clv_data=clv_data,
            decision_type=decision_type, decision_reasoning=reasoning,
            primary_bet=bet, total_recommended_stake=stake,
            warnings=warnings, overall_confidence=min(0.95, max(0.40, confidence))
        )


if __name__ == "__main__":
    scorer = QuantumMatchupScorerV34()
    
    print("=" * 80)
    print("🔥 QUANTUM MATCHUP SCORER V3.4.2 - SMART CONFLICT RESOLUTION")
    print("=" * 80)
    print("\n📋 RÈGLES DE RÉSOLUTION:")
    print("   1. BLAZING/HOT + Z faible → FOLLOW_MOMENTUM")
    print("   2. Z > 2.5 + pas COLD → FOLLOW_Z")
    print("   3. Aligné → BOOST ×1.15")
    print("   4. Z favori COLD → réduction 50%")
    print("   5. Conflit modéré → réduction 15-25%")
    
    test_matchups = [
        ("Real Sociedad", "Real Madrid"),
        ("Lazio", "Juventus"),
        ("Barcelona", "Athletic Club"),
        ("Newcastle United", "Chelsea"),
    ]
    
    for home, away in test_matchups:
        result = scorer.analyze_matchup(home, away)
        if result:
            print(f"\n{'='*75}")
            print(f"⚽ {home} vs {away}")
            print(f"{'='*75}")
            
            print(f"\n📊 Z: {home} {result.home_z_score:+.2f} | {away} {result.away_z_score:+.2f} | Edge: {result.z_edge:.2f}")
            
            print(f"\n🔥 MOMENTUM:")
            for team, mom in [(home, result.home_momentum), (away, result.away_momentum)]:
                if mom:
                    st, sl = mom.current_streak
                    print(f"   {team}: {mom.trend.value} ({mom.momentum_score:.0f}) | "
                          f"{mom.wins}W-{mom.draws}D-{mom.losses}L | {st.upper()}×{sl} | ×{mom.stake_multiplier:.2f}")
            
            r = result.conflict_resolution
            print(f"\n⚔️ RESOLUTION: {r.resolution.value}")
            print(f"   Z → {r.z_favorite} | Mom → {r.momentum_favorite}")
            print(f"   → FOLLOW: {r.follow_team} (×{r.stake_multiplier:.2f})")
            print(f"   {r.reasoning}")
            
            print(f"\n🎯 {result.decision_type.value}")
            
            b = result.primary_bet
            print(f"\n💰 {b.market.value} → {b.selection}")
            print(f"   Prob: {b.our_probability:.0%} | Edge: {b.kelly.edge_percentage:.1f}%")
            print(f"   🎯 STAKE: {b.kelly.recommended_stake:.1f}u ({b.sizing})")
            
            if result.warnings:
                print(f"\n   ⚠️ {' | '.join(result.warnings)}")
    
    scorer.close()
