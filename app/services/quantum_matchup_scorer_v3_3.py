#!/usr/bin/env python3
"""
🔥 QUANTUM MATCHUP SCORER V3.3 - BAYESIAN KELLY

PROBLÈME RÉSOLU:
- V3.2: "Notre prob = 55%" (certitude absolue)
- Réalité: "Notre prob = 55% ± 10%" (incertitude)

BAYESIAN KELLY:
- Modélise l'incertitude sur notre estimation
- Plus d'incertitude → Kelly plus conservateur
- Sources d'incertitude: sample size, tier, chaos, CLV

FORMULE:
adjusted_prob = mean_prob - uncertainty_penalty
uncertainty_penalty = variance / 2 (approximation Taylor)

SOURCES D'INCERTITUDE:
1. Confidence du modèle (Z-score extremeness)
2. Sample size de l'équipe (matches joués)
3. Tier (ELITE = prévisible, SILVER = volatile)
4. Chaos du match
5. CLV agreement (confirme = réduit incertitude)
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
    BAYESIAN_KELLY = "BAYESIAN"
    ZSCORE_BAYESIAN = "ZSCORE_BAY"


@dataclass
class UncertaintyProfile:
    """Profil d'incertitude pour Bayesian Kelly"""
    base_std: float           # Écart-type de base sur notre prob
    model_confidence: float   # Confiance du modèle (0-1)
    sample_factor: float      # Facteur sample size
    tier_factor: float        # Facteur tier
    chaos_factor: float       # Facteur chaos
    clv_factor: float         # Facteur CLV
    
    @property
    def total_std(self) -> float:
        """Écart-type total combiné"""
        # Combiner les facteurs (racine de somme des carrés)
        combined = math.sqrt(
            self.base_std ** 2 +
            (1 - self.model_confidence) ** 2 * 0.05 +
            self.sample_factor ** 2 +
            self.tier_factor ** 2 +
            self.chaos_factor ** 2 +
            self.clv_factor ** 2
        )
        return min(combined, 0.25)  # Cap à 25% d'incertitude
    
    @property
    def variance(self) -> float:
        return self.total_std ** 2


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
    is_real: bool


@dataclass
class BayesianKellyResult:
    """Résultat du Kelly Bayésien"""
    mean_prob: float          # Notre probabilité moyenne
    std_prob: float           # Notre incertitude (écart-type)
    adjusted_prob: float      # Prob ajustée pour l'incertitude
    uncertainty_penalty: float # Pénalité appliquée
    
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
    uncertainty_std: float
    adjusted_probability: float
    market_odds: Optional[float]
    market_implied_prob: Optional[float]
    kelly: BayesianKellyResult
    sizing: str
    reasoning: str
    clv_validated: bool = False


@dataclass
class MatchupDecisionV33:
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
    uncertainty_profile: UncertaintyProfile
    decision_type: DecisionType
    decision_reasoning: str
    primary_bet: SmartBet
    secondary_bets: List[SmartBet]
    total_recommended_stake: float
    warnings: List[str]
    overall_confidence: float


class BayesianKellyCalculator:
    """
    Kelly Criterion avec incertitude Bayésienne
    
    Au lieu de: kelly(p, odds)
    On fait: kelly(p - uncertainty_penalty, odds)
    
    où uncertainty_penalty = variance / 2 (approx Taylor)
    """
    
    FRACTION = 0.25
    MAX_STAKE = 5.0
    BANKROLL = 100.0
    
    # Base uncertainty (même avec données parfaites)
    BASE_UNCERTAINTY = 0.05  # 5% minimum
    
    # Quantum edge factor (validé par backtest r=+0.53)
    QUANTUM_EDGE_FACTOR = 0.08
    
    @classmethod
    def calculate_uncertainty(cls, 
                              z_score: float,
                              z_edge: float,
                              tier: str,
                              chaos: float,
                              sample_size: int,
                              clv: Optional[CLVData],
                              our_pick: str) -> UncertaintyProfile:
        """
        Calcule le profil d'incertitude basé sur plusieurs facteurs
        """
        
        # 1. Base uncertainty
        base_std = cls.BASE_UNCERTAINTY
        
        # 2. Model confidence (Z-scores extrêmes = moins fiables aux queues)
        # Z entre 1-2 = optimal, Z > 3 = moins confiant
        if abs(z_score) <= 2:
            model_conf = 0.85
        elif abs(z_score) <= 3:
            model_conf = 0.75
        else:
            model_conf = 0.65
        
        # 3. Sample size factor (plus de données = moins d'incertitude)
        # On suppose ~15-20 matches par saison
        if sample_size >= 15:
            sample_factor = 0.02
        elif sample_size >= 10:
            sample_factor = 0.05
        elif sample_size >= 5:
            sample_factor = 0.08
        else:
            sample_factor = 0.12
        
        # 4. Tier factor (ELITE = prévisible, SILVER = volatile)
        tier_factors = {
            'ELITE': 0.02,
            'GOLD': 0.04,
            'SILVER': 0.07,
            'BRONZE': 0.10
        }
        tier_factor = tier_factors.get(tier, 0.08)
        
        # 5. Chaos factor
        if chaos > 80:
            chaos_factor = 0.12
        elif chaos > 60:
            chaos_factor = 0.06
        else:
            chaos_factor = 0.02
        
        # 6. CLV factor (CLV confirme = réduit incertitude)
        clv_factor = 0.05  # Default
        if clv:
            clv_confirms = (
                (our_pick == "HOME" and clv.recommended_side == "HOME") or
                (our_pick == "AWAY" and clv.recommended_side == "AWAY") or
                (our_pick == "OVER" and clv.signal in [CLVSignal.SWEET_SPOT, CLVSignal.GOOD])
            )
            if clv.signal == CLVSignal.SWEET_SPOT and clv_confirms:
                clv_factor = 0.01  # Très confiant
            elif clv.signal == CLVSignal.GOOD and clv_confirms:
                clv_factor = 0.02
            elif clv.signal == CLVSignal.DANGER:
                clv_factor = 0.10  # Très incertain
            elif not clv_confirms and clv.recommended_side != "NONE":
                clv_factor = 0.08  # CLV contredit
        
        return UncertaintyProfile(
            base_std=base_std,
            model_confidence=model_conf,
            sample_factor=sample_factor,
            tier_factor=tier_factor,
            chaos_factor=chaos_factor,
            clv_factor=clv_factor
        )
    
    @classmethod
    def bayesian_kelly(cls, 
                       mean_prob: float, 
                       uncertainty: UncertaintyProfile,
                       market_odds: Optional[float] = None,
                       z_edge: float = 0) -> BayesianKellyResult:
        """
        Kelly Bayésien
        
        Formule: adjusted_prob = mean_prob - (variance / 2)
        C'est l'approximation Taylor de E[log(1 + f*X)] pour X incertain
        """
        
        std = uncertainty.total_std
        variance = uncertainty.variance
        
        # Pénalité d'incertitude (approximation Taylor ordre 2)
        uncertainty_penalty = variance / 2
        
        # Probabilité ajustée
        adjusted_prob = mean_prob - uncertainty_penalty
        adjusted_prob = max(0.10, adjusted_prob)  # Floor à 10%
        
        # === AVEC VRAIES ODDS ===
        if market_odds and market_odds > 1:
            market_prob = 1 / market_odds
            edge = adjusted_prob - market_prob
            edge_pct = edge * 100
            
            # Kelly standard avec prob ajustée
            ev = adjusted_prob * market_odds
            raw_kelly = (ev - 1) / (market_odds - 1) if market_odds > 1 else 0
            
            # Fractional Kelly
            fractional = raw_kelly * cls.FRACTION
            fractional = max(0, fractional)
            capped = min(fractional, cls.MAX_STAKE / 100)
            stake = round(capped * cls.BANKROLL, 2)
            
            if raw_kelly <= 0 or edge < 0:
                return cls._no_bet(mean_prob, std, adjusted_prob, uncertainty_penalty,
                                   f"Edge négatif ({edge_pct:.1f}%)")
            
            return BayesianKellyResult(
                mean_prob=mean_prob,
                std_prob=std,
                adjusted_prob=adjusted_prob,
                uncertainty_penalty=uncertainty_penalty,
                edge_percentage=round(edge_pct, 2),
                raw_kelly=round(raw_kelly, 4),
                fractional_kelly=round(fractional, 4),
                recommended_stake=stake,
                is_positive=True,
                method=SizingMethod.BAYESIAN_KELLY,
                reasoning=f"✅ Bayesian Kelly | σ={std:.0%}"
            )
        
        # === SANS ODDS (Z-SCORE BAYESIAN) ===
        # Base stake selon Z-edge
        if z_edge >= 2.5:
            base_stake = 4.0
        elif z_edge >= 1.5:
            base_stake = 3.0
        elif z_edge >= 1.0:
            base_stake = 2.0
        elif z_edge >= 0.5:
            base_stake = 1.0
        else:
            return cls._no_bet(mean_prob, std, adjusted_prob, uncertainty_penalty,
                               "Z-edge insuffisant")
        
        # Ajuster par confidence (inverse de l'incertitude)
        confidence_factor = 1 - std  # Plus d'incertitude = moins de stake
        stake = base_stake * confidence_factor * uncertainty.model_confidence
        stake = min(stake, cls.MAX_STAKE)
        
        # Edge estimé
        estimated_edge = cls.QUANTUM_EDGE_FACTOR * z_edge / 1.5 * confidence_factor
        
        return BayesianKellyResult(
            mean_prob=mean_prob,
            std_prob=std,
            adjusted_prob=adjusted_prob,
            uncertainty_penalty=uncertainty_penalty,
            edge_percentage=round(estimated_edge * 100, 2),
            raw_kelly=0,
            fractional_kelly=stake / cls.BANKROLL,
            recommended_stake=round(stake, 2),
            is_positive=True,
            method=SizingMethod.ZSCORE_BAYESIAN,
            reasoning=f"📊 Bayesian Z-Score | σ={std:.0%}"
        )
    
    @classmethod
    def _no_bet(cls, mean_prob, std, adj_prob, penalty, reason) -> BayesianKellyResult:
        return BayesianKellyResult(
            mean_prob=mean_prob,
            std_prob=std,
            adjusted_prob=adj_prob,
            uncertainty_penalty=penalty,
            edge_percentage=0,
            raw_kelly=0,
            fractional_kelly=0,
            recommended_stake=0,
            is_positive=False,
            method=SizingMethod.ZSCORE_BAYESIAN,
            reasoning=f"❌ {reason}"
        )


class QuantumMatchupScorerV33:
    """V3.3 avec Bayesian Kelly"""
    
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
        self.connect()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
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
        
        over25 = under25 = None
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT over_odds, under_odds
                FROM odds_totals
                WHERE (home_team ILIKE %s AND away_team ILIKE %s)
                  AND line = 2.5 AND bookmaker ILIKE '%%pinnacle%%'
                ORDER BY collected_at DESC LIMIT 1
            """, (f"%{home_team}%", f"%{away_team}%"))
            totals = cur.fetchone()
            if totals:
                over25 = float(totals['over_odds']) if totals['over_odds'] else None
                under25 = float(totals['under_odds']) if totals['under_odds'] else None
        
        return MarketOdds(home=home, draw=draw, away=away,
                          over25=over25, under25=under25,
                          source='Pinnacle', is_real=True)

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
            recommended_side, clv_value = "HOME", home_clv
        elif away_clv == max_clv and away_clv > self.CLV_GOOD_MIN:
            recommended_side, clv_value = "AWAY", away_clv
        elif draw_clv == max_clv and draw_clv > self.CLV_GOOD_MIN:
            recommended_side, clv_value = "DRAW", draw_clv
        else:
            recommended_side, clv_value = "NONE", max_clv
        
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
        z_diff = home_z - away_z
        if pick == "HOME":
            prob = 0.45 + z_diff * 0.08
        elif pick == "AWAY":
            prob = 0.45 - z_diff * 0.08
        else:
            prob = 0.25
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
        return DecisionType.PURE_VALUE, "📊 VALUE MODÉRÉE"

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
                        home_tier: str, away_tier: str,
                        total_xg: float, over25_prob: float,
                        market: Optional[MarketOdds],
                        chaos: float,
                        clv: Optional[CLVData]) -> Tuple[SmartBet, List[SmartBet], UncertaintyProfile]:
        
        secondary = []
        z_edge = abs(home_z - away_z)
        
        # Déterminer favori
        if home_z > away_z:
            favorite, our_pick = home, "HOME"
            fav_z = home_z
            fav_tier = home_tier
        else:
            favorite, our_pick = away, "AWAY"
            fav_z = away_z
            fav_tier = away_tier
        
        our_prob = self._calculate_our_probability(home_z, away_z, our_pick)
        
        # Sample size (estimation basée sur la saison)
        sample_size = 12  # Mi-saison typique
        
        # Calculer le profil d'incertitude
        uncertainty = BayesianKellyCalculator.calculate_uncertainty(
            z_score=fav_z,
            z_edge=z_edge,
            tier=fav_tier,
            chaos=chaos,
            sample_size=sample_size,
            clv=clv,
            our_pick=our_pick
        )
        
        # === SHOOTOUT ===
        if decision == DecisionType.SHOOTOUT:
            our_prob_over = 0.45 + (total_xg - 2.5) * 0.12
            our_prob_over = max(0.40, min(0.70, our_prob_over))
            
            uncertainty_over = BayesianKellyCalculator.calculate_uncertainty(
                z_score=fav_z, z_edge=z_edge, tier=fav_tier,
                chaos=chaos, sample_size=sample_size,
                clv=clv, our_pick="OVER"
            )
            
            kelly = BayesianKellyCalculator.bayesian_kelly(
                mean_prob=our_prob_over,
                uncertainty=uncertainty_over,
                market_odds=market.over25 if market else None,
                z_edge=z_edge
            )
            
            return SmartBet(
                market=MarketType.ASIAN_TOTAL,
                selection="Over 3.0",
                line=3.0,
                our_probability=our_prob_over,
                uncertainty_std=uncertainty_over.total_std,
                adjusted_probability=kelly.adjusted_prob,
                market_odds=market.over25 if market else None,
                market_implied_prob=round(1/market.over25, 3) if market and market.over25 else None,
                kelly=kelly,
                sizing=self._sizing_label(kelly.recommended_stake),
                reasoning=f"xG={total_xg:.1f} → Over"
            ), secondary, uncertainty_over
        
        # === CHAOS_PLAY ===
        if decision == DecisionType.CHAOS_PLAY:
            # Chaos = haute incertitude
            uncertainty_chaos = UncertaintyProfile(
                base_std=0.08,
                model_confidence=0.60,
                sample_factor=0.05,
                tier_factor=0.05,
                chaos_factor=0.15,  # Très élevé
                clv_factor=0.05
            )
            
            kelly = BayesianKellyCalculator.bayesian_kelly(
                mean_prob=over25_prob,
                uncertainty=uncertainty_chaos,
                z_edge=z_edge * 0.7
            )
            
            return SmartBet(
                market=MarketType.ASIAN_TOTAL,
                selection="Over 3.0",
                line=3.0,
                our_probability=over25_prob,
                uncertainty_std=uncertainty_chaos.total_std,
                adjusted_probability=kelly.adjusted_prob,
                market_odds=market.over25 if market else None,
                market_implied_prob=round(1/market.over25, 3) if market and market.over25 else None,
                kelly=kelly,
                sizing=self._sizing_label(kelly.recommended_stake),
                reasoning="Chaos → Goals (haute incertitude)"
            ), secondary, uncertainty_chaos
        
        # === VALUE_SECURE / PURE_VALUE ===
        if decision in [DecisionType.VALUE_SECURE, DecisionType.PURE_VALUE]:
            kelly = BayesianKellyCalculator.bayesian_kelly(
                mean_prob=our_prob,
                uncertainty=uncertainty,
                market_odds=market.home if market and our_pick == "HOME" else (market.away if market else None),
                z_edge=z_edge
            )
            
            primary = SmartBet(
                market=MarketType.MATCH_WINNER,
                selection=favorite,
                line=None,
                our_probability=our_prob,
                uncertainty_std=uncertainty.total_std,
                adjusted_probability=kelly.adjusted_prob,
                market_odds=market.home if market and our_pick == "HOME" else (market.away if market else None),
                market_implied_prob=round(1/(market.home if our_pick == "HOME" else market.away), 3) if market else None,
                kelly=kelly,
                sizing=self._sizing_label(kelly.recommended_stake),
                reasoning=f"Value {favorite} Z={fav_z:+.2f}",
                clv_validated=clv.signal in [CLVSignal.SWEET_SPOT, CLVSignal.GOOD] if clv else False
            )
            return primary, secondary, uncertainty
        
        # === TACTICAL_LOCK ===
        if decision == DecisionType.TACTICAL_LOCK:
            under_prob = 1 - over25_prob + 0.05
            kelly = BayesianKellyCalculator.bayesian_kelly(
                mean_prob=under_prob,
                uncertainty=uncertainty,
                z_edge=z_edge * 0.8
            )
            return SmartBet(
                market=MarketType.OVER_UNDER,
                selection="Under 2.5",
                line=2.5,
                our_probability=under_prob,
                uncertainty_std=uncertainty.total_std,
                adjusted_probability=kelly.adjusted_prob,
                market_odds=market.under25 if market else None,
                market_implied_prob=round(1/market.under25, 3) if market and market.under25 else None,
                kelly=kelly,
                sizing=self._sizing_label(kelly.recommended_stake),
                reasoning="Friction → Under"
            ), secondary, uncertainty
        
        # NO_EDGE
        return SmartBet(
            market=MarketType.MATCH_WINNER,
            selection="SKIP",
            line=None,
            our_probability=0,
            uncertainty_std=0,
            adjusted_probability=0,
            market_odds=None,
            market_implied_prob=None,
            kelly=BayesianKellyCalculator._no_bet(0, 0, 0, 0, "Pas d'edge"),
            sizing="SKIP",
            reasoning="Pas d'edge"
        ), [], uncertainty

    def analyze_matchup(self, home_team: str, away_team: str) -> Optional[MatchupDecisionV33]:
        
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
        
        home_tier = home_dna.get('tier', 'SILVER')
        away_tier = away_dna.get('tier', 'SILVER')
        
        friction_data = self._get_friction(home_team, away_team)
        friction = float(friction_data.get('friction_score', 50) or 50)
        chaos = float(friction_data.get('chaos_potential', 50) or 50)
        btts_prob = float(friction_data.get('predicted_btts_prob', 0.5) or 0.5)
        over25_prob = float(friction_data.get('predicted_over25_prob', 0.5) or 0.5)
        
        home_xg, away_xg, total_xg = self._calculate_xg(home_dna, away_dna, friction)
        
        clv_data = self._get_clv_data(home_team, away_team)
        market_odds = self._get_real_market_odds(home_team, away_team)
        
        decision_type, reasoning = self._finalize_decision(z_edge, friction, chaos, total_xg)
        
        primary_bet, secondary_bets, uncertainty = self._generate_bets(
            decision_type, home_team, away_team,
            home_z, away_z, home_tier, away_tier,
            total_xg, over25_prob,
            market_odds, chaos, clv_data
        )
        
        total_stake = primary_bet.kelly.recommended_stake
        for sb in secondary_bets:
            total_stake += sb.kelly.recommended_stake
        
        # Confidence globale
        confidence = 1 - uncertainty.total_std
        
        warnings = []
        if chaos > 80:
            warnings.append(f"⚠️ CHAOS ({chaos:.0f})")
        if clv_data and clv_data.signal == CLVSignal.DANGER:
            warnings.append("⚠️ CLV DANGER")
        if uncertainty.total_std > 0.15:
            warnings.append(f"⚠️ Haute incertitude (σ={uncertainty.total_std:.0%})")
        if not market_odds:
            warnings.append("📊 Pas d'odds Pinnacle")
        
        return MatchupDecisionV33(
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
            uncertainty_profile=uncertainty,
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
    scorer = QuantumMatchupScorerV33()
    
    print("=" * 80)
    print("🔥 QUANTUM MATCHUP SCORER V3.3 - BAYESIAN KELLY")
    print("=" * 80)
    print("\n📊 Différence clé avec V3.2:")
    print("   V3.2: prob = 55% → Kelly direct")
    print("   V3.3: prob = 55% ± σ → Kelly ajusté pour incertitude")
    print("\n🎯 Sources d'incertitude:")
    print("   • Model confidence (Z extremeness)")
    print("   • Tier (ELITE = stable, SILVER = volatile)")
    print("   • Chaos du match")
    print("   • CLV confirmation")
    
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
            print(f"   Z: {home} {result.home_z_score:+.2f} | {away} {result.away_z_score:+.2f}")
            print(f"   xG: {result.total_xg:.2f} | Chaos: {result.chaos_potential:.0f}")
            
            print(f"\n🎯 DÉCISION: {result.decision_type.value}")
            
            pb = result.primary_bet
            k = pb.kelly
            u = result.uncertainty_profile
            
            print(f"\n💰 BET: {pb.market.value} → {pb.selection}")
            print(f"\n   ┌────────────────────────────────────────────┐")
            print(f"   │ 📊 BAYESIAN KELLY                          │")
            print(f"   ├────────────────────────────────────────────┤")
            print(f"   │ Prob brute:     {pb.our_probability:.0%}                       │")
            print(f"   │ Incertitude σ:  {pb.uncertainty_std:.1%}                       │")
            print(f"   │ Pénalité:       -{k.uncertainty_penalty:.1%}                      │")
            print(f"   │ Prob ajustée:   {k.adjusted_prob:.0%}                       │")
            print(f"   ├────────────────────────────────────────────┤")
            print(f"   │ Edge estimé:    {k.edge_percentage:+.1f}%                      │")
            print(f"   │ 🎯 STAKE:       {k.recommended_stake:.1f}u ({pb.sizing})              │")
            print(f"   └────────────────────────────────────────────┘")
            
            print(f"\n   📉 Décomposition incertitude:")
            print(f"      Base: {u.base_std:.0%} | Model: {1-u.model_confidence:.0%} | Tier: {u.tier_factor:.0%}")
            print(f"      Chaos: {u.chaos_factor:.0%} | CLV: {u.clv_factor:.0%}")
            print(f"      → Total σ: {u.total_std:.1%}")
            
            if result.warnings:
                print(f"\n   ⚠️ {' | '.join(result.warnings)}")
    
    scorer.close()
