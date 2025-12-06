#!/usr/bin/env python3
"""
🔥 QUANTUM MATCHUP SCORER V3.2 - KELLY CRITERION (SCIENTIFIC)

APPROCHE SCIENTIFIQUE:
- Kelly UNIQUEMENT avec vraies odds du marché (Pinnacle)
- Sans vraies odds → sizing par Z-score (V3.1 fallback)
- Edge = Notre prob - Market implied prob

NOTRE AVANTAGE:
- Z-Score V2.4: r = +0.5273 avec résultats
- Le marché sous-estime les équipes à fort Z-score
- On applique un "edge factor" basé sur la corrélation prouvée
"""

import math
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import psycopg2
from psycopg2.extras import RealDictCursor

import sys
sys.path.append('/home/Mon_ps/app/services')
from quantum_scorer_v2_4 import QuantumScorerV24

DB_CONFIG = {
    "host": "localhost", "port": 5432, "database": "monps_db",
    "user": "monps_user", "password": "monps_secure_password_2024"
}


class MarketType(Enum):
    MATCH_WINNER = "1X2"
    ASIAN_HANDICAP = "Asian Handicap"
    ASIAN_TOTAL = "Asian Total"
    BTTS = "BTTS"
    OVER_UNDER = "Over/Under"


class DecisionType(Enum):
    CHAOS_PLAY = "CHAOS_PLAY"
    VALUE_SECURE = "VALUE_SECURE"
    TACTICAL_LOCK = "TACTICAL_LOCK"
    SHOOTOUT = "SHOOTOUT"
    PURE_VALUE = "PURE_VALUE"
    NO_EDGE = "NO_EDGE"


class CLVSignal(Enum):
    SWEET_SPOT = "SWEET_SPOT"
    GOOD = "GOOD"
    DANGER = "DANGER"
    NO_SIGNAL = "NO_SIGNAL"


class SizingMethod(Enum):
    KELLY = "KELLY"           # Vraies odds disponibles
    ZSCORE = "ZSCORE"         # Fallback sans odds
    CLV_ADJUSTED = "CLV_ADJ"  # Ajusté par CLV


@dataclass
class CLVData:
    home_clv: float
    draw_clv: float
    away_clv: float
    hours_tracked: float
    signal: CLVSignal
    recommended_side: str


@dataclass
class MarketOdds:
    home: float
    draw: float
    away: float
    over25: Optional[float]
    under25: Optional[float]
    source: str
    is_real: bool  # True = Pinnacle, False = estimated


@dataclass
class KellyResult:
    edge_percentage: float
    raw_kelly: float
    fractional_kelly: float
    recommended_stake: float
    is_positive: bool
    method: SizingMethod
    reasoning: str


@dataclass
class SmartBet:
    market: MarketType
    selection: str
    line: Optional[float]
    our_probability: float
    market_odds: Optional[float]
    market_implied_prob: Optional[float]
    kelly: KellyResult
    sizing: str
    reasoning: str
    clv_validated: bool = False


@dataclass
class MatchupDecisionV32:
    home_team: str
    away_team: str
    home_z_score: float
    away_z_score: float
    z_edge: float
    friction_score: float
    chaos_potential: float
    home_xg: float
    away_xg: float
    total_xg: float
    clv_data: Optional[CLVData]
    market_odds: Optional[MarketOdds]
    decision_type: DecisionType
    decision_reasoning: str
    primary_bet: SmartBet
    secondary_bets: List[SmartBet]
    total_recommended_stake: float
    warnings: List[str]
    overall_confidence: float


class KellyCalculator:
    """
    Kelly scientifique:
    - Avec vraies odds: Kelly = (p*b - 1) / (b - 1)
    - Sans vraies odds: Sizing par Z-score
    """
    
    FRACTION = 0.25
    MAX_STAKE = 5.0
    BANKROLL = 100.0
    
    # Edge factor basé sur notre corrélation r=0.53
    # Les équipes BUY (+1.5 Z) surperforment de ~10% vs market
    QUANTUM_EDGE_FACTOR = 0.08  # 8% edge sur les BUY
    
    @classmethod
    def calculate_with_real_odds(cls, our_prob: float, market_odds: float,
                                   confidence: float = 1.0, 
                                   clv_boost: float = 0.0) -> KellyResult:
        """Kelly avec vraies odds du marché"""
        
        if market_odds <= 1 or our_prob <= 0:
            return cls._no_bet("Invalid inputs")
        
        market_prob = 1 / market_odds
        adjusted_prob = our_prob * confidence
        
        # Edge = notre prob - market prob
        edge = adjusted_prob - market_prob
        edge_pct = edge * 100
        
        # Kelly formula
        ev = adjusted_prob * market_odds
        raw_kelly = (ev - 1) / (market_odds - 1) if market_odds > 1 else 0
        
        # Fractional + CLV boost
        fractional = raw_kelly * cls.FRACTION * (1 + clv_boost)
        capped = min(max(fractional, 0), cls.MAX_STAKE / 100)
        stake = round(capped * cls.BANKROLL, 2)
        
        if raw_kelly <= 0 or edge < 0:
            return cls._no_bet(f"Edge négatif ({edge_pct:.1f}%)")
        
        return KellyResult(
            edge_percentage=round(edge_pct, 2),
            raw_kelly=round(raw_kelly, 4),
            fractional_kelly=round(fractional, 4),
            recommended_stake=stake,
            is_positive=True,
            method=SizingMethod.KELLY,
            reasoning=f"✅ Kelly {fractional*100:.1f}% | Edge {edge_pct:.1f}%"
        )
    
    @classmethod
    def calculate_from_zscore(cls, z_score: float, z_edge: float,
                               confidence: float = 1.0,
                               clv_boost: float = 0.0) -> KellyResult:
        """
        Sizing basé sur Z-score quand pas d'odds réelles
        Validé par backtest: BUY (Z≥1.5) = +11.13u/équipe
        """
        
        # Base stake selon Z-edge
        if z_edge >= 2.5:
            base_stake = 4.0  # MAX
        elif z_edge >= 1.5:
            base_stake = 3.0  # NORMAL+
        elif z_edge >= 1.0:
            base_stake = 2.0  # NORMAL
        elif z_edge >= 0.5:
            base_stake = 1.0  # SMALL
        else:
            return cls._no_bet("Z-edge insuffisant")
        
        # Ajustements
        stake = base_stake * confidence * (1 + clv_boost)
        stake = min(stake, cls.MAX_STAKE)
        
        # Edge estimé basé sur backtest
        # BUY bucket: +11.13u sur 7 équipes = ~1.6u/match
        # Avec odds moyennes ~2.0, ça donne ~8% edge
        estimated_edge = cls.QUANTUM_EDGE_FACTOR * z_edge / 1.5  # Scaled
        
        return KellyResult(
            edge_percentage=round(estimated_edge * 100, 2),
            raw_kelly=0,  # N/A sans vraies odds
            fractional_kelly=stake / cls.BANKROLL,
            recommended_stake=round(stake, 2),
            is_positive=True,
            method=SizingMethod.ZSCORE,
            reasoning=f"📊 Z-Score sizing | Edge ~{estimated_edge*100:.1f}%"
        )
    
    @classmethod
    def _no_bet(cls, reason: str) -> KellyResult:
        return KellyResult(0, 0, 0, 0, False, SizingMethod.ZSCORE, f"❌ {reason}")


class QuantumMatchupScorerV32:
    """V3.2 Scientific Kelly"""
    
    CHAOS_EXTREME = 80
    FRICTION_HIGH = 70
    FRICTION_NEUTRAL = 60
    XG_SHOOTOUT = 3.5
    XG_LOW = 2.5
    Z_STRONG_EDGE = 2.0
    Z_MEDIUM_EDGE = 1.0
    HOME_ADVANTAGE_XG = 0.25
    
    CLV_SWEET_SPOT_MIN = 5.0
    CLV_SWEET_SPOT_MAX = 10.0
    CLV_GOOD_MIN = 2.0
    CLV_DANGER_THRESHOLD = 10.0
    
    def __init__(self):
        self.conn = None
        self.v24_scorer = QuantumScorerV24()
        
    def connect(self):
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
            
    def close(self):
        if self.conn:
            self.conn.close()
        self.v24_scorer.close()

    def _get_real_market_odds(self, home_team: str, away_team: str) -> Optional[MarketOdds]:
        """Récupère les VRAIES odds Pinnacle depuis la DB"""
        self.connect()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Chercher les dernières odds Pinnacle
            cur.execute("""
                WITH latest AS (
                    SELECT match_id, MAX(created_at) as max_time
                    FROM odds
                    WHERE (home_team ILIKE %s AND away_team ILIKE %s)
                    GROUP BY match_id
                )
                SELECT o.outcome, o.odds_value, o.bookmaker
                FROM odds o
                JOIN latest l ON o.match_id = l.match_id AND o.created_at = l.max_time
                WHERE o.bookmaker ILIKE '%%pinnacle%%'
            """, (f"%{home_team}%", f"%{away_team}%"))
            
            results = cur.fetchall()
            
        if not results:
            return None
            
        home = draw = away = None
        for row in results:
            outcome = row['outcome'].lower()
            odds = float(row['odds_value'])
            if outcome == 'home':
                home = odds
            elif outcome == 'draw':
                draw = odds
            elif outcome == 'away':
                away = odds
                
        if not all([home, draw, away]):
            return None
        
        # Over/Under
        over25 = under25 = None
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT over_odds, under_odds
                FROM odds_totals
                WHERE (home_team ILIKE %s AND away_team ILIKE %s)
                  AND line = 2.5
                  AND bookmaker ILIKE '%%pinnacle%%'
                ORDER BY collected_at DESC LIMIT 1
            """, (f"%{home_team}%", f"%{away_team}%"))
            totals = cur.fetchone()
            if totals:
                over25 = float(totals['over_odds']) if totals['over_odds'] else None
                under25 = float(totals['under_odds']) if totals['under_odds'] else None
        
        return MarketOdds(
            home=home, draw=draw, away=away,
            over25=over25, under25=under25,
            source='Pinnacle', is_real=True
        )

    def _get_clv_data(self, home_team: str, away_team: str) -> Optional[CLVData]:
        self.connect()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT home_clv, draw_clv, away_clv, hours_tracked
                FROM v_clv_from_odds
                WHERE bookmaker = 'Pinnacle'
                  AND ((home_team ILIKE %s AND away_team ILIKE %s)
                    OR (home_team ILIKE %s AND away_team ILIKE %s))
                ORDER BY hours_tracked DESC LIMIT 1
            """, (f"%{home_team}%", f"%{away_team}%", 
                  f"%{away_team}%", f"%{home_team}%"))
            result = cur.fetchone()
            
        if not result:
            return None
            
        home_clv = float(result['home_clv'] or 0)
        draw_clv = float(result['draw_clv'] or 0)
        away_clv = float(result['away_clv'] or 0)
        hours = float(result['hours_tracked'] or 0)
        
        max_clv = max(home_clv, draw_clv, away_clv)
        
        if home_clv == max_clv and home_clv > self.CLV_GOOD_MIN:
            recommended_side = "HOME"
            clv_value = home_clv
        elif away_clv == max_clv and away_clv > self.CLV_GOOD_MIN:
            recommended_side = "AWAY"
            clv_value = away_clv
        elif draw_clv == max_clv and draw_clv > self.CLV_GOOD_MIN:
            recommended_side = "DRAW"
            clv_value = draw_clv
        else:
            recommended_side = "NONE"
            clv_value = max_clv
        
        if self.CLV_SWEET_SPOT_MIN <= clv_value <= self.CLV_SWEET_SPOT_MAX:
            signal = CLVSignal.SWEET_SPOT
        elif self.CLV_GOOD_MIN <= clv_value < self.CLV_SWEET_SPOT_MIN:
            signal = CLVSignal.GOOD
        elif clv_value > self.CLV_DANGER_THRESHOLD:
            signal = CLVSignal.DANGER
        else:
            signal = CLVSignal.NO_SIGNAL
            
        return CLVData(home_clv, draw_clv, away_clv, hours, signal, recommended_side)

    def _get_team_dna(self, team_name: str) -> Optional[Dict]:
        self.connect()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT team_name, tier, quantum_dna
                FROM quantum.team_profiles
                WHERE team_name = %s OR team_name ILIKE %s LIMIT 1
            """, (team_name, f"%{team_name}%"))
            result = cur.fetchone()
        return dict(result) if result else None

    def _get_friction(self, team_a: str, team_b: str) -> Dict:
        self.connect()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT friction_score, chaos_potential,
                       predicted_goals, predicted_btts_prob, predicted_over25_prob
                FROM quantum.matchup_friction
                WHERE (team_a_name = %s AND team_b_name = %s)
                   OR (team_a_name = %s AND team_b_name = %s) LIMIT 1
            """, (team_a, team_b, team_b, team_a))
            result = cur.fetchone()
        return dict(result) if result else {'friction_score': 50.0, 'chaos_potential': 50.0}

    def _calculate_xg(self, home_dna: Dict, away_dna: Dict, friction: float) -> Tuple[float, float, float]:
        home_current = home_dna.get('quantum_dna', {}).get('current_season', {})
        away_current = away_dna.get('quantum_dna', {}).get('current_season', {})
        
        home_xg_for = float(home_current.get('xg_for_avg', 1.3) or 1.3)
        home_xg_ag = float(home_current.get('xg_against_avg', 1.3) or 1.3)
        away_xg_for = float(away_current.get('xg_for_avg', 1.3) or 1.3)
        away_xg_ag = float(away_current.get('xg_against_avg', 1.3) or 1.3)
        
        home_xg = (home_xg_for + away_xg_ag) / 2 + self.HOME_ADVANTAGE_XG
        away_xg = (away_xg_for + home_xg_ag) / 2
        
        friction_mult = 1 + (friction - 50) / 150
        
        return round(home_xg * friction_mult, 2), round(away_xg * friction_mult, 2), round((home_xg + away_xg) * friction_mult, 2)

    def _calculate_our_probability(self, home_z: float, away_z: float, pick: str) -> float:
        """
        Notre probabilité basée sur Z-score
        Calibrée sur backtest: BUY teams ont ~65-70% WR
        """
        z_diff = home_z - away_z
        
        if pick == "HOME":
            # Base 45% + Z-diff adjustment
            prob = 0.45 + z_diff * 0.08
        elif pick == "AWAY":
            prob = 0.45 - z_diff * 0.08
        else:
            prob = 0.25  # Draw
            
        return max(0.20, min(0.75, prob))

    def _finalize_decision(self, z_edge: float, friction: float, 
                           chaos: float, total_xg: float) -> Tuple[DecisionType, str]:
        if chaos > self.CHAOS_EXTREME:
            return DecisionType.CHAOS_PLAY, "⚠️ CHAOS EXTRÊME"
        if total_xg > self.XG_SHOOTOUT:
            return DecisionType.SHOOTOUT, f"🔥 SHOOTOUT ({total_xg:.1f} xG)"
        if z_edge > self.Z_STRONG_EDGE and friction < self.FRICTION_NEUTRAL:
            return DecisionType.VALUE_SECURE, "💰 VALUE FORTE"
        if friction > self.FRICTION_HIGH and total_xg < self.XG_LOW:
            return DecisionType.TACTICAL_LOCK, "🛡️ GUERRE TACTIQUE"
        if z_edge > self.Z_MEDIUM_EDGE:
            return DecisionType.PURE_VALUE, "✅ PURE VALUE"
        if z_edge < 0.5:
            return DecisionType.NO_EDGE, "❌ PAS D'EDGE"
        return DecisionType.PURE_VALUE, f"📊 VALUE MODÉRÉE"

    def _get_clv_boost(self, clv: Optional[CLVData], our_pick: str) -> float:
        if not clv:
            return 0.0
        clv_confirms = (
            (our_pick == "HOME" and clv.recommended_side == "HOME") or
            (our_pick == "AWAY" and clv.recommended_side == "AWAY") or
            (our_pick == "OVER" and clv.signal in [CLVSignal.SWEET_SPOT, CLVSignal.GOOD])
        )
        if clv.signal == CLVSignal.SWEET_SPOT and clv_confirms:
            return 0.20
        elif clv.signal == CLVSignal.GOOD and clv_confirms:
            return 0.10
        elif clv.signal == CLVSignal.DANGER:
            return -0.20
        return 0.0

    def _sizing_label(self, stake: float) -> str:
        if stake >= 4.0:
            return "MAX"
        elif stake >= 2.5:
            return "NORMAL"
        elif stake >= 1.0:
            return "SMALL"
        elif stake > 0:
            return "MINI"
        return "SKIP"

    def _generate_bets(self, decision: DecisionType,
                        home: str, away: str,
                        home_z: float, away_z: float,
                        total_xg: float, over25_prob: float,
                        market: Optional[MarketOdds],
                        confidence: float,
                        clv: Optional[CLVData]) -> Tuple[SmartBet, List[SmartBet]]:
        
        secondary = []
        z_edge = abs(home_z - away_z)
        
        # Déterminer favori
        if home_z > away_z:
            favorite, our_pick = home, "HOME"
            fav_z = home_z
        else:
            favorite, our_pick = away, "AWAY"
            fav_z = away_z
        
        our_prob = self._calculate_our_probability(home_z, away_z, our_pick)
        clv_boost = self._get_clv_boost(clv, our_pick)
        
        # === DÉCISION SELON TYPE ===
        
        if decision == DecisionType.SHOOTOUT:
            our_prob_over = 0.45 + (total_xg - 2.5) * 0.12
            our_prob_over = max(0.40, min(0.70, our_prob_over))
            clv_boost = self._get_clv_boost(clv, "OVER")
            
            if market and market.is_real and market.over25:
                kelly = KellyCalculator.calculate_with_real_odds(
                    our_prob_over, market.over25, confidence, clv_boost
                )
                market_odds = market.over25
                market_impl = round(1/market.over25, 3)
            else:
                kelly = KellyCalculator.calculate_from_zscore(
                    fav_z, z_edge, confidence, clv_boost
                )
                market_odds = None
                market_impl = None
            
            return SmartBet(
                market=MarketType.ASIAN_TOTAL,
                selection="Over 3.0",
                line=3.0,
                our_probability=our_prob_over,
                market_odds=market_odds,
                market_implied_prob=market_impl,
                kelly=kelly,
                sizing=self._sizing_label(kelly.recommended_stake),
                reasoning=f"xG={total_xg:.1f} → Over",
                clv_validated=clv_boost > 0
            ), secondary
        
        if decision == DecisionType.CHAOS_PLAY:
            kelly = KellyCalculator.calculate_from_zscore(
                fav_z, z_edge * 0.7, confidence * 0.8, 0  # Réduit pour chaos
            )
            return SmartBet(
                market=MarketType.ASIAN_TOTAL,
                selection="Over 3.0",
                line=3.0,
                our_probability=over25_prob,
                market_odds=market.over25 if market else None,
                market_implied_prob=round(1/market.over25, 3) if market and market.over25 else None,
                kelly=kelly,
                sizing=self._sizing_label(kelly.recommended_stake),
                reasoning="Chaos → Goals market"
            ), secondary
        
        if decision in [DecisionType.VALUE_SECURE, DecisionType.PURE_VALUE]:
            if market and market.is_real:
                market_odds = market.home if our_pick == "HOME" else market.away
                kelly = KellyCalculator.calculate_with_real_odds(
                    our_prob, market_odds, confidence, clv_boost
                )
                market_impl = round(1/market_odds, 3)
            else:
                kelly = KellyCalculator.calculate_from_zscore(
                    fav_z, z_edge, confidence, clv_boost
                )
                market_odds = None
                market_impl = None
            
            primary = SmartBet(
                market=MarketType.MATCH_WINNER,
                selection=favorite,
                line=None,
                our_probability=our_prob,
                market_odds=market_odds,
                market_implied_prob=market_impl,
                kelly=kelly,
                sizing=self._sizing_label(kelly.recommended_stake),
                reasoning=f"Value {favorite} Z={fav_z:+.2f}",
                clv_validated=clv_boost > 0
            )
            return primary, secondary
        
        if decision == DecisionType.TACTICAL_LOCK:
            under_prob = 1 - over25_prob + 0.05
            kelly = KellyCalculator.calculate_from_zscore(
                fav_z, z_edge * 0.8, confidence * 0.85, 0
            )
            return SmartBet(
                market=MarketType.OVER_UNDER,
                selection="Under 2.5",
                line=2.5,
                our_probability=under_prob,
                market_odds=market.under25 if market else None,
                market_implied_prob=round(1/market.under25, 3) if market and market.under25 else None,
                kelly=kelly,
                sizing=self._sizing_label(kelly.recommended_stake),
                reasoning="Friction haute → Under"
            ), secondary
        
        # NO_EDGE
        return SmartBet(
            market=MarketType.MATCH_WINNER,
            selection="SKIP",
            line=None,
            our_probability=0,
            market_odds=None,
            market_implied_prob=None,
            kelly=KellyCalculator._no_bet("Pas d'edge"),
            sizing="SKIP",
            reasoning="Pas d'edge identifié"
        ), []

    def analyze_matchup(self, home_team: str, away_team: str) -> Optional[MatchupDecisionV32]:
        
        home_score = self.v24_scorer.calculate_score(home_team)
        away_score = self.v24_scorer.calculate_score(away_team)
        
        if not home_score or not away_score:
            return None
        
        home_z = home_score.vector.z_score
        away_z = away_score.vector.z_score
        z_edge = abs(home_z - away_z)
        
        home_dna = self._get_team_dna(home_team)
        away_dna = self._get_team_dna(away_team)
        
        if not home_dna or not away_dna:
            return None
        
        friction_data = self._get_friction(home_team, away_team)
        friction = float(friction_data.get('friction_score', 50) or 50)
        chaos = float(friction_data.get('chaos_potential', 50) or 50)
        btts_prob = float(friction_data.get('predicted_btts_prob', 0.5) or 0.5)
        over25_prob = float(friction_data.get('predicted_over25_prob', 0.5) or 0.5)
        
        home_xg, away_xg, total_xg = self._calculate_xg(home_dna, away_dna, friction)
        
        clv_data = self._get_clv_data(home_team, away_team)
        market_odds = self._get_real_market_odds(home_team, away_team)
        
        decision_type, reasoning = self._finalize_decision(z_edge, friction, chaos, total_xg)
        
        confidence = 0.75
        if z_edge > 1.5:
            confidence += 0.10
        if chaos < 60:
            confidence += 0.05
        if clv_data and clv_data.signal == CLVSignal.SWEET_SPOT:
            confidence += 0.10
        confidence = min(0.95, confidence)
        
        primary_bet, secondary_bets = self._generate_bets(
            decision_type, home_team, away_team,
            home_z, away_z, total_xg, over25_prob,
            market_odds, confidence, clv_data
        )
        
        total_stake = primary_bet.kelly.recommended_stake
        for sb in secondary_bets:
            total_stake += sb.kelly.recommended_stake
        
        warnings = []
        if chaos > 80:
            warnings.append(f"⚠️ CHAOS ({chaos:.0f})")
        if clv_data and clv_data.signal == CLVSignal.DANGER:
            warnings.append("⚠️ CLV DANGER")
        if not market_odds or not market_odds.is_real:
            warnings.append("📊 Sizing par Z-score (pas d'odds Pinnacle)")
        
        return MatchupDecisionV32(
            home_team=home_team,
            away_team=away_team,
            home_z_score=home_z,
            away_z_score=away_z,
            z_edge=z_edge,
            friction_score=friction,
            chaos_potential=chaos,
            home_xg=home_xg,
            away_xg=away_xg,
            total_xg=total_xg,
            clv_data=clv_data,
            market_odds=market_odds,
            decision_type=decision_type,
            decision_reasoning=reasoning,
            primary_bet=primary_bet,
            secondary_bets=secondary_bets,
            total_recommended_stake=total_stake,
            warnings=warnings,
            overall_confidence=confidence,
        )


# === TEST ===
if __name__ == "__main__":
    scorer = QuantumMatchupScorerV32()
    
    print("=" * 80)
    print("🔥 QUANTUM MATCHUP SCORER V3.2 - SCIENTIFIC KELLY")
    print("=" * 80)
    print("\nLogique:")
    print("• Avec vraies odds Pinnacle → Kelly Criterion")
    print("• Sans odds → Sizing par Z-score (validé: r=+0.53)")
    print("• CLV boost: Sweet spot +20%, Danger -20%")
    
    test_matchups = [
        ("Barcelona", "Athletic Club"),
        ("Lazio", "Juventus"),
        ("Real Sociedad", "Real Madrid"),
        ("Newcastle United", "Chelsea"),
    ]
    
    for home, away in test_matchups:
        result = scorer.analyze_matchup(home, away)
        if result:
            print(f"\n{'='*70}")
            print(f"⚽ {home} vs {away}")
            print(f"{'='*70}")
            
            print(f"\n📊 ANALYSE:")
            print(f"   Z: {home} {result.home_z_score:+.2f} | {away} {result.away_z_score:+.2f} | Edge: {result.z_edge:.2f}")
            print(f"   xG: {result.total_xg:.2f} | Chaos: {result.chaos_potential:.0f}")
            
            if result.market_odds:
                m = result.market_odds
                tag = "✅ REAL" if m.is_real else "📊 EST"
                print(f"\n📈 MARKET ({m.source} {tag}):")
                print(f"   1X2: {m.home:.2f} / {m.draw:.2f} / {m.away:.2f}")
            
            print(f"\n🎯 DÉCISION: {result.decision_type.value}")
            print(f"   {result.decision_reasoning}")
            
            pb = result.primary_bet
            print(f"\n💰 BET: {pb.market.value} → {pb.selection}")
            print(f"   Notre prob: {pb.our_probability:.0%}")
            if pb.market_odds:
                print(f"   Market: {pb.market_odds:.2f} (impl: {pb.market_implied_prob:.0%})")
            
            k = pb.kelly
            print(f"\n   ┌────────────────────────────────────────┐")
            print(f"   │ {k.method.value} SIZING                          │")
            print(f"   │ Edge estimé: {k.edge_percentage:+.1f}%                     │")
            print(f"   │ 🎯 STAKE: {k.recommended_stake:.1f}u ({pb.sizing})               │")
            print(f"   │ {k.reasoning:<38} │")
            print(f"   └────────────────────────────────────────┘")
            
            if result.warnings:
                print(f"\n   ⚠️ {' | '.join(result.warnings)}")
    
    scorer.close()
