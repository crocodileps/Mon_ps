#!/usr/bin/env python3
"""
🔥 QUANTUM MATCHUP SCORER V3.0 - Decision Matrix

AMÉLIORATIONS V3.0:
- Matrice de décision finale qui résout le conflit Value vs Friction
- Marchés intelligents: Asian Handicap, Asian Total (pas juste 1X2)
- Sizing ajusté par contexte tactique

LOGIQUE DE PRIORITÉ:
1. CHAOS > 80 → AVOID_WINNER, jouer les buts uniquement
2. VALUE forte + Friction neutre → Asian Handicap (sécuriser)
3. Friction haute + xG bas → UNDER market
4. xG > 3.5 → Asian Total Over (festival offensif)
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
    """Types de marchés disponibles"""
    MATCH_WINNER = "1X2"
    ASIAN_HANDICAP = "Asian Handicap"
    ASIAN_TOTAL = "Asian Total"
    BTTS = "BTTS"
    OVER_UNDER = "Over/Under"
    DOUBLE_CHANCE = "Double Chance"
    CARDS = "Cards Market"
    CORNERS = "Corners"


class DecisionType(Enum):
    """Types de décision"""
    CHAOS_PLAY = "CHAOS_PLAY"           # Chaos > 80: jouer buts/cartons
    VALUE_SECURE = "VALUE_SECURE"       # Value forte, friction neutre: AH
    TACTICAL_LOCK = "TACTICAL_LOCK"     # Friction haute, xG bas: Under
    SHOOTOUT = "SHOOTOUT"               # xG > 3.5: Asian Total Over
    PURE_VALUE = "PURE_VALUE"           # Conditions optimales: 1X2
    NO_EDGE = "NO_EDGE"                 # Pas de signal clair


@dataclass
class SmartBet:
    """Un pari intelligent avec market, line et sizing"""
    market: MarketType
    selection: str
    line: Optional[float]  # e.g., -0.5, 2.5, etc.
    probability: float
    sizing: str
    reasoning: str


@dataclass
class MatchupDecisionV3:
    """Décision complète V3"""
    home_team: str
    away_team: str
    
    # Z-Scores
    home_z_score: float
    away_z_score: float
    z_edge: float
    
    # Friction
    friction_score: float
    chaos_potential: float
    
    # xG Analysis
    home_xg: float
    away_xg: float
    total_xg: float
    
    # Decision
    decision_type: DecisionType
    decision_reasoning: str
    
    # Bets (ordonnés par priorité)
    primary_bet: SmartBet
    secondary_bets: List[SmartBet]
    
    # Warnings
    warnings: List[str]
    
    # Confidence
    overall_confidence: float


class QuantumMatchupScorerV3:
    """
    Matchup Scorer V3 avec Matrice de Décision Intelligente
    """
    
    # Thresholds
    CHAOS_EXTREME = 80
    CHAOS_HIGH = 70
    FRICTION_HIGH = 70
    FRICTION_NEUTRAL = 60
    XG_SHOOTOUT = 3.5
    XG_LOW = 2.5
    Z_STRONG_EDGE = 2.0
    Z_MEDIUM_EDGE = 1.0
    
    HOME_ADVANTAGE_XG = 0.25
    
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
                       style_clash_score, tempo_clash_score, mental_clash_score,
                       predicted_goals, predicted_btts_prob, predicted_over25_prob
                FROM quantum.matchup_friction
                WHERE (team_a_name = %s AND team_b_name = %s)
                   OR (team_a_name = %s AND team_b_name = %s)
                LIMIT 1
            """, (team_a, team_b, team_b, team_a))
            result = cur.fetchone()
        
        if result:
            return dict(result)
        return {'friction_score': 50.0, 'chaos_potential': 50.0}

    def _calculate_xg(self, home_dna: Dict, away_dna: Dict, friction: float) -> Tuple[float, float, float]:
        """Calcule les xG ajustés"""
        home_current = home_dna.get('quantum_dna', {}).get('current_season', {})
        away_current = away_dna.get('quantum_dna', {}).get('current_season', {})
        
        home_xg_for = float(home_current.get('xg_for_avg', 1.3) or 1.3)
        home_xg_ag = float(home_current.get('xg_against_avg', 1.3) or 1.3)
        away_xg_for = float(away_current.get('xg_for_avg', 1.3) or 1.3)
        away_xg_ag = float(away_current.get('xg_against_avg', 1.3) or 1.3)
        
        # Home xG = (home_attack + away_defense) / 2 + home advantage
        home_xg = (home_xg_for + away_xg_ag) / 2 + self.HOME_ADVANTAGE_XG
        away_xg = (away_xg_for + home_xg_ag) / 2
        
        # Friction multiplier
        friction_mult = 1 + (friction - 50) / 150
        home_xg *= friction_mult
        away_xg *= friction_mult
        
        return round(home_xg, 2), round(away_xg, 2), round(home_xg + away_xg, 2)

    def _finalize_decision(self, z_edge: float, friction: float, 
                           chaos: float, total_xg: float,
                           home_z: float, away_z: float) -> Tuple[DecisionType, str]:
        """
        🎯 MATRICE DE DÉCISION FINALE
        Résout le conflit Value vs Friction
        """
        
        # CAS 1: CHAOS EXTRÊME (Ex: Newcastle vs Chelsea avec chaos=90)
        if chaos > self.CHAOS_EXTREME:
            return DecisionType.CHAOS_PLAY, \
                "⚠️ CHAOS EXTRÊME: Ne JAMAIS parier sur le vainqueur. Marchés de buts/cartons uniquement."
        
        # CAS 2: FESTIVAL OFFENSIF (Ex: Liverpool vs City avec xG=3.68)
        if total_xg > self.XG_SHOOTOUT:
            return DecisionType.SHOOTOUT, \
                f"🔥 SHOOTOUT ({total_xg:.1f} xG): Priorité Asian Total Over. Le 1X2 est trop aléatoire."
        
        # CAS 3: VALUE FORTE MAIS FRICTION NEUTRE (Ex: Sociedad vs Real avec Z=3.08, friction=50)
        if z_edge > self.Z_STRONG_EDGE and friction < self.FRICTION_NEUTRAL:
            return DecisionType.VALUE_SECURE, \
                f"💰 VALUE FORTE (edge={z_edge:.2f}) mais tactique neutre. Sécuriser avec Asian Handicap."
        
        # CAS 4: GUERRE TACTIQUE (Friction haute + peu de buts attendus)
        if friction > self.FRICTION_HIGH and total_xg < self.XG_LOW:
            return DecisionType.TACTICAL_LOCK, \
                f"🛡️ GUERRE TACTIQUE: Friction={friction:.0f}, xG={total_xg:.1f}. Favoriser UNDER."
        
        # CAS 5: CONDITIONS OPTIMALES (Value + Friction cohérentes)
        if z_edge > self.Z_MEDIUM_EDGE and friction > self.FRICTION_NEUTRAL:
            return DecisionType.PURE_VALUE, \
                f"✅ CONDITIONS OPTIMALES: Value confirmée par la tactique. 1X2 possible."
        
        # CAS 6: CHAOS MODÉRÉ
        if chaos > self.CHAOS_HIGH:
            return DecisionType.CHAOS_PLAY, \
                "⚠️ CHAOS ÉLEVÉ: Réduire exposition au 1X2. Préférer les totaux."
        
        # CAS 7: PAS DE SIGNAL CLAIR
        if z_edge < 0.5:
            return DecisionType.NO_EDGE, \
                "❌ PAS D'EDGE: Les deux équipes sont proches. Pas de pari recommandé."
        
        # Default: Value modérée
        return DecisionType.PURE_VALUE, \
            f"📊 VALUE MODÉRÉE (edge={z_edge:.2f}). Pari possible avec sizing réduit."

    def _generate_smart_bets(self, decision: DecisionType, 
                              home: str, away: str,
                              home_z: float, away_z: float,
                              home_xg: float, away_xg: float, total_xg: float,
                              btts_prob: float, over25_prob: float,
                              friction: float, chaos: float) -> Tuple[SmartBet, List[SmartBet]]:
        """
        Génère les paris intelligents basés sur le type de décision
        """
        primary = None
        secondary = []
        
        # Déterminer le favori Z-Score
        if home_z > away_z:
            z_favorite = home
            z_underdog = away
            z_diff = home_z - away_z
        else:
            z_favorite = away
            z_underdog = home
            z_diff = away_z - home_z
        
        # === CHAOS_PLAY: Éviter le vainqueur ===
        if decision == DecisionType.CHAOS_PLAY:
            # Primary: Asian Total basé sur xG
            if total_xg > 3.0:
                line = 3.0 if total_xg > 3.5 else 2.75
                primary = SmartBet(
                    market=MarketType.ASIAN_TOTAL,
                    selection=f"Over {line}",
                    line=line,
                    probability=over25_prob,
                    sizing="SMALL",
                    reasoning="Chaos élevé = match ouvert, buts probables"
                )
            else:
                primary = SmartBet(
                    market=MarketType.BTTS,
                    selection="Yes" if btts_prob > 0.5 else "No",
                    line=None,
                    probability=btts_prob if btts_prob > 0.5 else 1-btts_prob,
                    sizing="SMALL",
                    reasoning="Chaos = difficile prédire le score exact"
                )
            
            # Secondary: Cartons (chaos = agressivité)
            if chaos > 85:
                secondary.append(SmartBet(
                    market=MarketType.CARDS,
                    selection="Over 4.5 Cards",
                    line=4.5,
                    probability=0.65,
                    sizing="SMALL",
                    reasoning="Chaos extrême = beaucoup de fautes"
                ))
        
        # === SHOOTOUT: Festival offensif ===
        elif decision == DecisionType.SHOOTOUT:
            # Primary: Asian Total Over
            line = 3.5 if total_xg > 4.0 else 3.0
            primary = SmartBet(
                market=MarketType.ASIAN_TOTAL,
                selection=f"Over {line}",
                line=line,
                probability=min(0.85, over25_prob + 0.1),
                sizing="MAX",
                reasoning=f"xG total = {total_xg:.1f}, festival offensif attendu"
            )
            
            # Secondary: BTTS
            secondary.append(SmartBet(
                market=MarketType.BTTS,
                selection="Yes",
                line=None,
                probability=btts_prob,
                sizing="NORMAL",
                reasoning="Les deux attaques sont prolifiques"
            ))
            
            # Secondary: Over 2.5 (plus safe)
            secondary.append(SmartBet(
                market=MarketType.OVER_UNDER,
                selection="Over 2.5",
                line=2.5,
                probability=over25_prob,
                sizing="NORMAL",
                reasoning="Backup si Asian Total trop risqué"
            ))
        
        # === VALUE_SECURE: Asian Handicap pour sécuriser ===
        elif decision == DecisionType.VALUE_SECURE:
            # Primary: Asian Handicap +0.5 sur le favori (Double Chance)
            ah_line = 0.0 if z_diff > 2.5 else 0.5
            primary = SmartBet(
                market=MarketType.ASIAN_HANDICAP,
                selection=f"{z_favorite} {ah_line:+.1f}",
                line=ah_line,
                probability=0.70,
                sizing="NORMAL",
                reasoning=f"Value forte sur {z_favorite} mais friction neutre → sécuriser"
            )
            
            # Secondary: Double Chance classique
            if z_favorite == home:
                secondary.append(SmartBet(
                    market=MarketType.DOUBLE_CHANCE,
                    selection="1X",
                    line=None,
                    probability=0.75,
                    sizing="NORMAL",
                    reasoning="Alternative: Double Chance domicile"
                ))
            else:
                secondary.append(SmartBet(
                    market=MarketType.DOUBLE_CHANCE,
                    selection="X2",
                    line=None,
                    probability=0.75,
                    sizing="NORMAL",
                    reasoning="Alternative: Double Chance extérieur"
                ))
        
        # === TACTICAL_LOCK: Under market ===
        elif decision == DecisionType.TACTICAL_LOCK:
            line = 2.0 if total_xg < 2.2 else 2.5
            primary = SmartBet(
                market=MarketType.OVER_UNDER,
                selection=f"Under {line}",
                line=line,
                probability=1 - over25_prob + 0.1,
                sizing="NORMAL",
                reasoning=f"Friction haute ({friction:.0f}) + xG bas ({total_xg:.1f}) = match fermé"
            )
            
            # Secondary: BTTS No
            secondary.append(SmartBet(
                market=MarketType.BTTS,
                selection="No",
                line=None,
                probability=1 - btts_prob,
                sizing="SMALL",
                reasoning="Match tactique, difficile de marquer"
            ))
        
        # === PURE_VALUE: 1X2 classique ===
        elif decision == DecisionType.PURE_VALUE:
            sizing = "MAX" if z_diff > 2.0 else "NORMAL" if z_diff > 1.0 else "SMALL"
            primary = SmartBet(
                market=MarketType.MATCH_WINNER,
                selection=z_favorite,
                line=None,
                probability=0.55 + z_diff * 0.05,
                sizing=sizing,
                reasoning=f"Value confirmée: {z_favorite} Z={max(home_z, away_z):+.2f}"
            )
            
            # Secondary: Over/BTTS si xG intéressant
            if total_xg > 2.8:
                secondary.append(SmartBet(
                    market=MarketType.OVER_UNDER,
                    selection="Over 2.5",
                    line=2.5,
                    probability=over25_prob,
                    sizing="SMALL",
                    reasoning="xG supporte aussi les buts"
                ))
        
        # === NO_EDGE: Skip ===
        else:
            primary = SmartBet(
                market=MarketType.MATCH_WINNER,
                selection="SKIP",
                line=None,
                probability=0.0,
                sizing="NONE",
                reasoning="Pas d'edge identifié, ne pas parier"
            )
        
        return primary, secondary

    def analyze_matchup(self, home_team: str, away_team: str) -> Optional[MatchupDecisionV3]:
        """
        Analyse complète V3 d'un matchup
        """
        # Get Z-Scores
        home_score = self.v24_scorer.calculate_score(home_team)
        away_score = self.v24_scorer.calculate_score(away_team)
        
        if not home_score or not away_score:
            return None
        
        home_z = home_score.vector.z_score
        away_z = away_score.vector.z_score
        z_edge = abs(home_z - away_z)
        
        # Get DNA
        home_dna = self._get_team_dna(home_team)
        away_dna = self._get_team_dna(away_team)
        
        if not home_dna or not away_dna:
            return None
        
        # Get Friction
        friction_data = self._get_friction(home_team, away_team)
        friction = float(friction_data.get('friction_score', 50) or 50)
        chaos = float(friction_data.get('chaos_potential', 50) or 50)
        btts_prob = float(friction_data.get('predicted_btts_prob', 0.5) or 0.5)
        over25_prob = float(friction_data.get('predicted_over25_prob', 0.5) or 0.5)
        
        # Calculate xG
        home_xg, away_xg, total_xg = self._calculate_xg(home_dna, away_dna, friction)
        
        # Finalize decision
        decision_type, reasoning = self._finalize_decision(
            z_edge, friction, chaos, total_xg, home_z, away_z
        )
        
        # Generate smart bets
        primary_bet, secondary_bets = self._generate_smart_bets(
            decision_type, home_team, away_team,
            home_z, away_z, home_xg, away_xg, total_xg,
            btts_prob, over25_prob, friction, chaos
        )
        
        # Warnings
        warnings = []
        if chaos > 80:
            warnings.append(f"⚠️ CHAOS EXTRÊME ({chaos:.0f}): Match imprévisible")
        if friction > 75:
            warnings.append(f"⚠️ FRICTION HAUTE ({friction:.0f}): Potentiel cartons/blessures")
        if z_edge < 0.5:
            warnings.append("⚠️ EDGE FAIBLE: Les deux équipes sont proches")
        if total_xg > 4.0:
            warnings.append(f"🔥 SHOOTOUT ATTENDU ({total_xg:.1f} xG)")
        
        # Confidence
        confidence = 0.5
        if z_edge > 1.5:
            confidence += 0.2
        if chaos < 60:
            confidence += 0.1
        if friction > 60:
            confidence += 0.05
        confidence = min(0.9, confidence)
        
        return MatchupDecisionV3(
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
            decision_type=decision_type,
            decision_reasoning=reasoning,
            primary_bet=primary_bet,
            secondary_bets=secondary_bets,
            warnings=warnings,
            overall_confidence=confidence,
        )


# === TEST ===
if __name__ == "__main__":
    scorer = QuantumMatchupScorerV3()
    
    print("=" * 80)
    print("🔥 QUANTUM MATCHUP SCORER V3.0 - DECISION MATRIX")
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
            print(f"   Z-Scores: {home} {result.home_z_score:+.2f} | {away} {result.away_z_score:+.2f} | Edge: {result.z_edge:.2f}")
            print(f"   Friction: {result.friction_score:.0f} | Chaos: {result.chaos_potential:.0f}")
            print(f"   xG: {home} {result.home_xg:.2f} | {away} {result.away_xg:.2f} | Total: {result.total_xg:.2f}")
            
            print(f"\n�� DÉCISION: {result.decision_type.value}")
            print(f"   {result.decision_reasoning}")
            
            print(f"\n💰 PRIMARY BET:")
            pb = result.primary_bet
            line_str = f" ({pb.line})" if pb.line else ""
            print(f"   {pb.market.value}: {pb.selection}{line_str}")
            print(f"   Sizing: {pb.sizing} | Prob: {pb.probability:.0%}")
            print(f"   💡 {pb.reasoning}")
            
            if result.secondary_bets:
                print(f"\n💰 SECONDARY BETS:")
                for sb in result.secondary_bets[:2]:
                    line_str = f" ({sb.line})" if sb.line else ""
                    print(f"   • {sb.market.value}: {sb.selection}{line_str} | {sb.sizing}")
            
            if result.warnings:
                print(f"\n⚠️ WARNINGS:")
                for w in result.warnings:
                    print(f"   {w}")
            
            print(f"\n📈 Confidence: {result.overall_confidence:.0%}")
    
    # Résumé comparatif V2 vs V3
    print("\n" + "=" * 80)
    print("📊 COMPARAISON V2 vs V3")
    print("=" * 80)
    print("""
| Match                    | V2 Recommandation      | V3 Recommandation           |
|--------------------------|------------------------|------------------------------|
| Real Sociedad vs Real    | MAX BET 1X2            | Asian Handicap +0.5 (NORMAL) |
| Newcastle vs Chelsea     | SMALL (chaos warning)  | AVOID 1X2, Asian Total Only  |
| Liverpool vs City        | Draw/DC + Over 2.5     | Asian Total Over 3.0 (MAX)   |
| Lazio vs Juve            | Lazio WIN (NORMAL)     | Lazio WIN (confirmé)         |
    """)
    
    scorer.close()
