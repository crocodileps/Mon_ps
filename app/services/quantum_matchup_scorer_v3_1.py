#!/usr/bin/env python3
"""
🔥 QUANTUM MATCHUP SCORER V3.1 - CLV VALIDATED

AMÉLIORATIONS V3.1:
- Intégration CLV Validator basé sur données empiriques
- Sweet spot CLV 5-10% = MAX sizing
- CLV > 10% = réduire sizing (souvent corrections de ligne)
- CLV < 2% = pas de signal market

DÉCOUVERTES EMPIRIQUES (91 matchs):
- CLV 5-10%: +5.21u, 56% WR → BEST
- CLV 2-3%: +2.09u, 63% WR → BON
- CLV > 10%: -1.37u, 44% WR → DANGER
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
    DOUBLE_CHANCE = "Double Chance"
    CARDS = "Cards Market"


class DecisionType(Enum):
    CHAOS_PLAY = "CHAOS_PLAY"
    VALUE_SECURE = "VALUE_SECURE"
    TACTICAL_LOCK = "TACTICAL_LOCK"
    SHOOTOUT = "SHOOTOUT"
    PURE_VALUE = "PURE_VALUE"
    NO_EDGE = "NO_EDGE"


class CLVSignal(Enum):
    """Signal CLV basé sur les données empiriques"""
    SWEET_SPOT = "SWEET_SPOT"       # 5-10%: +5.21u → MAX
    GOOD = "GOOD"                   # 2-5%: +2.09u → NORMAL
    DANGER = "DANGER"               # >10%: -1.37u → SMALL
    NO_SIGNAL = "NO_SIGNAL"         # <2%: pas de signal
    CONTRARIAN = "CONTRARIAN"       # CLV négatif mais notre modèle dit BUY


@dataclass
class CLVData:
    """Données CLV pour un match"""
    home_clv: float
    draw_clv: float
    away_clv: float
    hours_tracked: float
    signal: CLVSignal
    recommended_side: str  # HOME, AWAY, DRAW, NONE
    sizing_adjustment: str  # BOOST, NORMAL, REDUCE, SKIP


@dataclass
class SmartBet:
    market: MarketType
    selection: str
    line: Optional[float]
    probability: float
    sizing: str
    reasoning: str
    clv_validated: bool = False
    clv_adjustment: str = "NONE"


@dataclass
class MatchupDecisionV31:
    """Décision V3.1 avec CLV"""
    home_team: str
    away_team: str
    
    # Z-Scores
    home_z_score: float
    away_z_score: float
    z_edge: float
    
    # Friction
    friction_score: float
    chaos_potential: float
    
    # xG
    home_xg: float
    away_xg: float
    total_xg: float
    
    # CLV NEW
    clv_data: Optional[CLVData]
    
    # Decision
    decision_type: DecisionType
    decision_reasoning: str
    
    # Bets
    primary_bet: SmartBet
    secondary_bets: List[SmartBet]
    
    # Warnings
    warnings: List[str]
    
    # Confidence (ajustée par CLV)
    overall_confidence: float
    clv_confidence_boost: float


class QuantumMatchupScorerV31:
    """
    V3.1 avec CLV Validator
    
    Le CLV (Closing Line Value) valide ou invalide nos prédictions:
    - Si notre modèle dit BUY et CLV confirme → BOOST
    - Si notre modèle dit BUY mais CLV dit DANGER → REDUCE
    - Si CLV en sweet spot (5-10%) → MAX sizing
    """
    
    # Thresholds (inchangés)
    CHAOS_EXTREME = 80
    CHAOS_HIGH = 70
    FRICTION_HIGH = 70
    FRICTION_NEUTRAL = 60
    XG_SHOOTOUT = 3.5
    XG_LOW = 2.5
    Z_STRONG_EDGE = 2.0
    Z_MEDIUM_EDGE = 1.0
    HOME_ADVANTAGE_XG = 0.25
    
    # CLV Thresholds (basés sur empirique)
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

    def _get_clv_data(self, home_team: str, away_team: str) -> Optional[CLVData]:
        """
        Récupère les données CLV depuis v_clv_from_odds
        Priorité: Pinnacle (gold standard)
        """
        self.connect()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Chercher par noms d'équipes (flexible matching)
            cur.execute("""
                SELECT 
                    home_clv, draw_clv, away_clv, hours_tracked
                FROM v_clv_from_odds
                WHERE bookmaker = 'Pinnacle'
                  AND (
                    (home_team ILIKE %s AND away_team ILIKE %s)
                    OR (home_team ILIKE %s AND away_team ILIKE %s)
                  )
                ORDER BY hours_tracked DESC
                LIMIT 1
            """, (f"%{home_team}%", f"%{away_team}%", 
                  f"%{away_team}%", f"%{home_team}%"))
            
            result = cur.fetchone()
            
        if not result:
            return None
            
        home_clv = float(result['home_clv'] or 0)
        draw_clv = float(result['draw_clv'] or 0)
        away_clv = float(result['away_clv'] or 0)
        hours = float(result['hours_tracked'] or 0)
        
        # Déterminer le signal et le side recommandé
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
        
        # Classifier le signal
        if self.CLV_SWEET_SPOT_MIN <= clv_value <= self.CLV_SWEET_SPOT_MAX:
            signal = CLVSignal.SWEET_SPOT
            sizing_adj = "BOOST"
        elif self.CLV_GOOD_MIN <= clv_value < self.CLV_SWEET_SPOT_MIN:
            signal = CLVSignal.GOOD
            sizing_adj = "NORMAL"
        elif clv_value > self.CLV_DANGER_THRESHOLD:
            signal = CLVSignal.DANGER
            sizing_adj = "REDUCE"
        else:
            signal = CLVSignal.NO_SIGNAL
            sizing_adj = "NORMAL"
            
        return CLVData(
            home_clv=home_clv,
            draw_clv=draw_clv,
            away_clv=away_clv,
            hours_tracked=hours,
            signal=signal,
            recommended_side=recommended_side,
            sizing_adjustment=sizing_adj,
        )

    def _get_team_dna(self, team_name: str) -> Optional[Dict]:
        self.connect()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT team_name, tier, quantum_dna
                FROM quantum.team_profiles
                WHERE team_name = %s OR team_name ILIKE %s
                LIMIT 1
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
                   OR (team_a_name = %s AND team_b_name = %s)
                LIMIT 1
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
        home_xg *= friction_mult
        away_xg *= friction_mult
        
        return round(home_xg, 2), round(away_xg, 2), round(home_xg + away_xg, 2)

    def _finalize_decision(self, z_edge: float, friction: float, 
                           chaos: float, total_xg: float,
                           home_z: float, away_z: float) -> Tuple[DecisionType, str]:
        """Decision Matrix (inchangé de V3.0)"""
        if chaos > self.CHAOS_EXTREME:
            return DecisionType.CHAOS_PLAY, \
                "⚠️ CHAOS EXTRÊME: Ne JAMAIS parier sur le vainqueur."
        
        if total_xg > self.XG_SHOOTOUT:
            return DecisionType.SHOOTOUT, \
                f"🔥 SHOOTOUT ({total_xg:.1f} xG): Priorité Asian Total Over."
        
        if z_edge > self.Z_STRONG_EDGE and friction < self.FRICTION_NEUTRAL:
            return DecisionType.VALUE_SECURE, \
                f"💰 VALUE FORTE mais tactique neutre. Asian Handicap."
        
        if friction > self.FRICTION_HIGH and total_xg < self.XG_LOW:
            return DecisionType.TACTICAL_LOCK, \
                f"🛡️ GUERRE TACTIQUE. Favoriser UNDER."
        
        if z_edge > self.Z_MEDIUM_EDGE and friction > self.FRICTION_NEUTRAL:
            return DecisionType.PURE_VALUE, \
                f"✅ CONDITIONS OPTIMALES. 1X2 possible."
        
        if chaos > self.CHAOS_HIGH:
            return DecisionType.CHAOS_PLAY, \
                "⚠️ CHAOS ÉLEVÉ: Préférer les totaux."
        
        if z_edge < 0.5:
            return DecisionType.NO_EDGE, \
                "❌ PAS D'EDGE identifié."
        
        return DecisionType.PURE_VALUE, \
            f"📊 VALUE MODÉRÉE (edge={z_edge:.2f})."

    def _apply_clv_to_sizing(self, base_sizing: str, clv: Optional[CLVData], 
                              our_pick: str) -> Tuple[str, bool, str]:
        """
        Ajuste le sizing basé sur CLV
        Returns: (final_sizing, clv_validated, adjustment_reason)
        """
        if not clv:
            return base_sizing, False, "NO_CLV_DATA"
        
        # Vérifier si CLV confirme notre pick
        clv_confirms = (
            (our_pick == "HOME" and clv.recommended_side == "HOME") or
            (our_pick == "AWAY" and clv.recommended_side == "AWAY") or
            (our_pick == "DRAW" and clv.recommended_side == "DRAW")
        )
        
        # Sweet spot (5-10%) + confirmation = BOOST
        if clv.signal == CLVSignal.SWEET_SPOT and clv_confirms:
            if base_sizing in ["NORMAL", "SMALL"]:
                return "MAX", True, "CLV_SWEET_SPOT_CONFIRMED"
            return base_sizing, True, "CLV_SWEET_SPOT_CONFIRMED"
        
        # Good (2-5%) + confirmation = keep or slight boost
        if clv.signal == CLVSignal.GOOD and clv_confirms:
            if base_sizing == "SMALL":
                return "NORMAL", True, "CLV_GOOD_CONFIRMED"
            return base_sizing, True, "CLV_GOOD_CONFIRMED"
        
        # DANGER (>10%) = toujours réduire
        if clv.signal == CLVSignal.DANGER:
            if base_sizing == "MAX":
                return "NORMAL", False, "CLV_DANGER_REDUCE"
            elif base_sizing == "NORMAL":
                return "SMALL", False, "CLV_DANGER_REDUCE"
            return "SKIP", False, "CLV_DANGER_SKIP"
        
        # CLV ne confirme pas mais signal existe = prudence
        if clv.recommended_side != "NONE" and not clv_confirms:
            if base_sizing == "MAX":
                return "NORMAL", False, "CLV_CONTRARIAN"
            return base_sizing, False, "CLV_CONTRARIAN"
        
        return base_sizing, False, "CLV_NO_SIGNAL"

    def _generate_smart_bets(self, decision: DecisionType,
                              home: str, away: str,
                              home_z: float, away_z: float,
                              home_xg: float, away_xg: float, total_xg: float,
                              btts_prob: float, over25_prob: float,
                              friction: float, chaos: float,
                              clv: Optional[CLVData]) -> Tuple[SmartBet, List[SmartBet]]:
        """Génère les paris avec validation CLV"""
        
        secondary = []
        
        # Déterminer le favori
        if home_z > away_z:
            z_favorite = home
            z_underdog = away
            z_diff = home_z - away_z
            our_pick = "HOME"
        else:
            z_favorite = away
            z_underdog = home
            z_diff = away_z - home_z
            our_pick = "AWAY"
        
        # Base sizing
        if z_diff > 2.0:
            base_sizing = "MAX"
        elif z_diff > 1.0:
            base_sizing = "NORMAL"
        else:
            base_sizing = "SMALL"
        
        # === CHAOS_PLAY ===
        if decision == DecisionType.CHAOS_PLAY:
            if total_xg > 3.0:
                line = 3.0 if total_xg > 3.5 else 2.75
                primary = SmartBet(
                    market=MarketType.ASIAN_TOTAL,
                    selection=f"Over {line}",
                    line=line,
                    probability=over25_prob,
                    sizing="SMALL",
                    reasoning="Chaos = buts probables"
                )
            else:
                primary = SmartBet(
                    market=MarketType.BTTS,
                    selection="Yes" if btts_prob > 0.5 else "No",
                    line=None,
                    probability=btts_prob if btts_prob > 0.5 else 1-btts_prob,
                    sizing="SMALL",
                    reasoning="Chaos = BTTS market"
                )
            return primary, secondary
        
        # === SHOOTOUT ===
        if decision == DecisionType.SHOOTOUT:
            line = 3.5 if total_xg > 4.0 else 3.0
            # CLV validation pour les totaux
            final_sizing, validated, reason = self._apply_clv_to_sizing("MAX", clv, "OVER")
            
            primary = SmartBet(
                market=MarketType.ASIAN_TOTAL,
                selection=f"Over {line}",
                line=line,
                probability=min(0.85, over25_prob + 0.1),
                sizing=final_sizing,
                reasoning=f"xG={total_xg:.1f} festival offensif",
                clv_validated=validated,
                clv_adjustment=reason,
            )
            secondary.append(SmartBet(
                market=MarketType.BTTS,
                selection="Yes",
                line=None,
                probability=btts_prob,
                sizing="NORMAL",
                reasoning="Attaques prolifiques"
            ))
            return primary, secondary
        
        # === VALUE_SECURE ===
        if decision == DecisionType.VALUE_SECURE:
            ah_line = 0.0 if z_diff > 2.5 else 0.5
            final_sizing, validated, reason = self._apply_clv_to_sizing("NORMAL", clv, our_pick)
            
            primary = SmartBet(
                market=MarketType.ASIAN_HANDICAP,
                selection=f"{z_favorite} {ah_line:+.1f}",
                line=ah_line,
                probability=0.70,
                sizing=final_sizing,
                reasoning=f"Value {z_favorite} sécurisée AH",
                clv_validated=validated,
                clv_adjustment=reason,
            )
            return primary, secondary
        
        # === TACTICAL_LOCK ===
        if decision == DecisionType.TACTICAL_LOCK:
            line = 2.0 if total_xg < 2.2 else 2.5
            primary = SmartBet(
                market=MarketType.OVER_UNDER,
                selection=f"Under {line}",
                line=line,
                probability=1 - over25_prob + 0.1,
                sizing="NORMAL",
                reasoning=f"Friction haute + xG bas = fermé"
            )
            return primary, secondary
        
        # === PURE_VALUE ===
        if decision == DecisionType.PURE_VALUE:
            final_sizing, validated, reason = self._apply_clv_to_sizing(base_sizing, clv, our_pick)
            
            primary = SmartBet(
                market=MarketType.MATCH_WINNER,
                selection=z_favorite,
                line=None,
                probability=0.55 + z_diff * 0.05,
                sizing=final_sizing,
                reasoning=f"Value: {z_favorite} Z={max(home_z, away_z):+.2f}",
                clv_validated=validated,
                clv_adjustment=reason,
            )
            
            if total_xg > 2.8:
                secondary.append(SmartBet(
                    market=MarketType.OVER_UNDER,
                    selection="Over 2.5",
                    line=2.5,
                    probability=over25_prob,
                    sizing="SMALL",
                    reasoning="xG supporte les buts"
                ))
            return primary, secondary
        
        # === NO_EDGE ===
        primary = SmartBet(
            market=MarketType.MATCH_WINNER,
            selection="SKIP",
            line=None,
            probability=0.0,
            sizing="NONE",
            reasoning="Pas d'edge identifié"
        )
        return primary, secondary

    def analyze_matchup(self, home_team: str, away_team: str) -> Optional[MatchupDecisionV31]:
        """Analyse V3.1 avec CLV"""
        
        # Z-Scores
        home_score = self.v24_scorer.calculate_score(home_team)
        away_score = self.v24_scorer.calculate_score(away_team)
        
        if not home_score or not away_score:
            return None
        
        home_z = home_score.vector.z_score
        away_z = away_score.vector.z_score
        z_edge = abs(home_z - away_z)
        
        # DNA
        home_dna = self._get_team_dna(home_team)
        away_dna = self._get_team_dna(away_team)
        
        if not home_dna or not away_dna:
            return None
        
        # Friction
        friction_data = self._get_friction(home_team, away_team)
        friction = float(friction_data.get('friction_score', 50) or 50)
        chaos = float(friction_data.get('chaos_potential', 50) or 50)
        btts_prob = float(friction_data.get('predicted_btts_prob', 0.5) or 0.5)
        over25_prob = float(friction_data.get('predicted_over25_prob', 0.5) or 0.5)
        
        # xG
        home_xg, away_xg, total_xg = self._calculate_xg(home_dna, away_dna, friction)
        
        # CLV Data (NEW)
        clv_data = self._get_clv_data(home_team, away_team)
        
        # Decision
        decision_type, reasoning = self._finalize_decision(
            z_edge, friction, chaos, total_xg, home_z, away_z
        )
        
        # Smart bets with CLV
        primary_bet, secondary_bets = self._generate_smart_bets(
            decision_type, home_team, away_team,
            home_z, away_z, home_xg, away_xg, total_xg,
            btts_prob, over25_prob, friction, chaos, clv_data
        )
        
        # Warnings
        warnings = []
        if chaos > 80:
            warnings.append(f"⚠️ CHAOS EXTRÊME ({chaos:.0f})")
        if clv_data and clv_data.signal == CLVSignal.DANGER:
            warnings.append(f"⚠️ CLV DANGER (>{self.CLV_DANGER_THRESHOLD}%): Sizing réduit")
        if clv_data and not primary_bet.clv_validated and clv_data.recommended_side != "NONE":
            warnings.append(f"⚠️ CLV CONTRARIAN: Market dit {clv_data.recommended_side}")
        
        # Confidence avec boost CLV
        confidence = 0.5
        clv_boost = 0.0
        if z_edge > 1.5:
            confidence += 0.2
        if chaos < 60:
            confidence += 0.1
        
        if clv_data:
            if clv_data.signal == CLVSignal.SWEET_SPOT and primary_bet.clv_validated:
                clv_boost = 0.15
            elif clv_data.signal == CLVSignal.GOOD and primary_bet.clv_validated:
                clv_boost = 0.10
            elif clv_data.signal == CLVSignal.DANGER:
                clv_boost = -0.10
                
        confidence = min(0.95, confidence + clv_boost)
        
        return MatchupDecisionV31(
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
            decision_type=decision_type,
            decision_reasoning=reasoning,
            primary_bet=primary_bet,
            secondary_bets=secondary_bets,
            warnings=warnings,
            overall_confidence=confidence,
            clv_confidence_boost=clv_boost,
        )


# === TEST ===
if __name__ == "__main__":
    scorer = QuantumMatchupScorerV31()
    
    print("=" * 80)
    print("🔥 QUANTUM MATCHUP SCORER V3.1 - CLV VALIDATED")
    print("=" * 80)
    
    test_matchups = [
        ("Barcelona", "Athletic Club"),
        ("Lazio", "Juventus"),
        ("Liverpool", "Manchester City"),
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
            print(f"   Z-Scores: {home} {result.home_z_score:+.2f} | {away} {result.away_z_score:+.2f}")
            print(f"   Friction: {result.friction_score:.0f} | Chaos: {result.chaos_potential:.0f}")
            print(f"   xG Total: {result.total_xg:.2f}")
            
            # CLV Section
            if result.clv_data:
                clv = result.clv_data
                print(f"\n📈 CLV ANALYSIS:")
                print(f"   Home CLV: {clv.home_clv:+.1f}% | Away CLV: {clv.away_clv:+.1f}%")
                print(f"   Signal: {clv.signal.value} | Recommended: {clv.recommended_side}")
                print(f"   Hours tracked: {clv.hours_tracked:.0f}h")
            else:
                print(f"\n📈 CLV: Pas de données")
            
            print(f"\n🎯 DÉCISION: {result.decision_type.value}")
            print(f"   {result.decision_reasoning}")
            
            print(f"\n💰 PRIMARY BET:")
            pb = result.primary_bet
            line_str = f" ({pb.line})" if pb.line else ""
            clv_tag = " ✅ CLV" if pb.clv_validated else ""
            print(f"   {pb.market.value}: {pb.selection}{line_str}")
            print(f"   Sizing: {pb.sizing}{clv_tag} | Adj: {pb.clv_adjustment}")
            print(f"   💡 {pb.reasoning}")
            
            if result.warnings:
                print(f"\n⚠️ WARNINGS:")
                for w in result.warnings:
                    print(f"   {w}")
            
            print(f"\n📈 Confidence: {result.overall_confidence:.0%} (CLV boost: {result.clv_confidence_boost:+.0%})")
    
    scorer.close()
