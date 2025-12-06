#!/usr/bin/env python3
"""
🔬 QUANTUM SCORER - PHASE 2
Transforme les 11 vecteurs DNA en scores prédictifs exploitables
"""

import json
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    "host": "localhost", "port": 5432, "database": "monps_db",
    "user": "monps_user", "password": "monps_secure_password_2024"
}


@dataclass
class QuantumScore:
    """Score Quantum pour une équipe"""
    team_name: str
    overall_score: float
    value_score: float
    confidence: float
    mentality_score: float
    temporal_score: float
    luck_score: float
    tactical_score: float
    recommended_bets: List[str]
    avoid_bets: List[str]
    insights: List[str]
    tier: str
    historical_pnl: float
    win_rate: float


@dataclass  
class MatchupPrediction:
    """Prédiction pour un matchup"""
    home_team: str
    away_team: str
    friction_score: float
    chaos_potential: float
    home_quantum_score: float
    away_quantum_score: float
    edge_team: str
    edge_magnitude: float
    primary_bet: str
    secondary_bets: List[str]
    avoid: List[str]
    confidence: float
    key_factors: List[str]


class QuantumScorer:
    """
    Moteur de scoring basé sur les 11 vecteurs DNA
    
    Corrélations clés (Phase 1 Analysis):
    - CONSERVATIVE mentality = +11.73u/équipe (BEST)
    - LOW killer_instinct (0.7-1.0) = +6.55u
    - BALANCED diesel (0.45-0.55) = +7.44u, 72.1% WR
    - LEAKY keeper = +6.95u (régression value)
    - 4-3-3 formation = +8.08u
    """
    
    WEIGHTS = {
        "mentality": 0.20,
        "killer_instinct": 0.15,
        "diesel_factor": 0.15,
        "keeper_status": 0.12,
        "luck_profile": 0.15,
        "formation": 0.08,
        "historical_pnl": 0.10,
        "chameleon": 0.05,
    }
    
    MENTALITY_SCORES = {
        "CONSERVATIVE": 100, "BALANCED": 80, "VOLATILE": 60,
        "PREDATOR": 55, "FRAGILE": 40,
    }
    
    KEEPER_SCORES = {"LEAKY": 85, "SOLID": 70, "ON_FIRE": 60}
    LUCK_SCORES = {"UNLUCKY": 90, "NEUTRAL": 60, "LUCKY": 40}
    FORMATION_SCORES = {
        "4-3-3": 100, "4-2-3-1": 95, "4-1-4-1": 85,
        "3-4-2-1": 70, "4-4-2": 65, "3-4-3": 55, "3-5-2": 50,
    }
    CHAMELEON_SCORES = {"ADAPTIVE": 80, "MODERATE": 70, "RIGID": 50}
    
    def __init__(self):
        self.conn = None
        self._team_cache = {}
        
    def connect(self):
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
            
    def close(self):
        if self.conn:
            self.conn.close()
            
    def get_team_dna(self, team_name: str) -> Optional[Dict]:
        if team_name in self._team_cache:
            return self._team_cache[team_name]
        self.connect()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT team_name, tier, total_pnl, win_rate, total_bets, quantum_dna
                FROM quantum.team_profiles
                WHERE team_name = %s OR team_name ILIKE %s
            """, (team_name, f"%{team_name}%"))
            result = cur.fetchone()
        if result:
            self._team_cache[team_name] = dict(result)
            return self._team_cache[team_name]
        return None
        
    def _calc_mentality_score(self, dna: Dict) -> Tuple[float, List[str]]:
        psyche = dna.get('psyche_dna', {})
        profile = psyche.get('profile', 'BALANCED')
        killer = float(psyche.get('killer_instinct', 1.0) or 1.0)
        base_score = self.MENTALITY_SCORES.get(profile, 60)
        insights = []
        if 0.7 <= killer <= 1.0:
            base_score += 10
            insights.append(f"✅ Killer instinct optimal ({killer:.2f})")
        elif killer > 1.5:
            base_score -= 10
            insights.append(f"⚠️ Killer instinct élevé ({killer:.2f})")
        return min(100, base_score), insights
        
    def _calc_temporal_score(self, dna: Dict) -> Tuple[float, List[str]]:
        temporal = dna.get('temporal_dna', {})
        diesel = float(temporal.get('diesel_factor', 0.5) or 0.5)
        insights = []
        if 0.45 <= diesel <= 0.55:
            score = 100
            insights.append(f"✅ Diesel équilibré ({diesel:.2f})")
        elif diesel > 0.55:
            score = 70
            insights.append(f"⚡ DIESEL - forte 2MT ({diesel:.2f})")
        else:
            score = 65
            insights.append(f"🏃 SPRINTER - forte 1MT ({diesel:.2f})")
        return score, insights
        
    def _calc_luck_score(self, dna: Dict) -> Tuple[float, List[str]]:
        luck = dna.get('luck_dna', {})
        profile = luck.get('luck_profile', 'NEUTRAL')
        total_luck = float(luck.get('total_luck', 0) or 0)
        base_score = self.LUCK_SCORES.get(profile, 60)
        insights = []
        if profile == "UNLUCKY":
            insights.append(f"🎯 UNLUCKY ({total_luck:.1f}) - VALUE!")
        elif profile == "LUCKY":
            insights.append(f"⚠️ LUCKY ({total_luck:.1f}) - risque régression")
        return base_score, insights
        
    def _calc_tactical_score(self, dna: Dict) -> Tuple[float, List[str]]:
        tactical = dna.get('tactical_dna', {})
        nemesis = dna.get('nemesis_dna', {})
        formation = tactical.get('main_formation', '4-4-2')
        keeper_status = nemesis.get('keeper_status', 'SOLID')
        formation_score = self.FORMATION_SCORES.get(formation, 60)
        keeper_score = self.KEEPER_SCORES.get(keeper_status, 70)
        combined = (formation_score * 0.4) + (keeper_score * 0.6)
        insights = []
        if formation in ['4-3-3', '4-2-3-1']:
            insights.append(f"✅ Formation rentable: {formation}")
        if keeper_status == "LEAKY":
            insights.append("🎯 Gardien LEAKY - value régression")
        return combined, insights
        
    def _generate_recommendations(self, dna: Dict) -> Tuple[List[str], List[str]]:
        recommended, avoid = [], []
        luck_profile = dna.get('luck_dna', {}).get('luck_profile', 'NEUTRAL')
        keeper_status = dna.get('nemesis_dna', {}).get('keeper_status', 'SOLID')
        diesel = float(dna.get('temporal_dna', {}).get('diesel_factor', 0.5) or 0.5)
        mentality = dna.get('psyche_dna', {}).get('profile', 'BALANCED')
        
        if luck_profile == "UNLUCKY":
            recommended.append("TEAM_WIN (value régression)")
        if keeper_status == "LEAKY":
            recommended.append("OVER goals (régression gardien)")
            avoid.append("UNDER goals")
        if diesel > 0.55:
            recommended.append("Over 0.5 buts 75-90'")
        if mentality == "CONSERVATIVE":
            recommended.append("CONFIANCE ÉLEVÉE")
        if mentality == "FRAGILE":
            avoid.append("Parier si menée")
        return recommended, avoid
        
    def score_team(self, team_name: str) -> Optional[QuantumScore]:
        team_data = self.get_team_dna(team_name)
        if not team_data:
            return None
        dna = team_data.get('quantum_dna', {})
        
        mentality_score, m_insights = self._calc_mentality_score(dna)
        temporal_score, t_insights = self._calc_temporal_score(dna)
        luck_score, l_insights = self._calc_luck_score(dna)
        tactical_score, tac_insights = self._calc_tactical_score(dna)
        
        pnl = float(team_data.get('total_pnl', 0) or 0)
        pnl_score = min(100, max(0, 50 + pnl * 2))
        
        overall = (
            mentality_score * self.WEIGHTS['mentality'] +
            temporal_score * self.WEIGHTS['diesel_factor'] +
            luck_score * self.WEIGHTS['luck_profile'] +
            tactical_score * (self.WEIGHTS['keeper_status'] + self.WEIGHTS['formation']) +
            pnl_score * self.WEIGHTS['historical_pnl']
        )
        
        luck_profile = dna.get('luck_dna', {}).get('luck_profile', 'NEUTRAL')
        keeper_status = dna.get('nemesis_dna', {}).get('keeper_status', 'SOLID')
        value_score = 50
        if luck_profile == "UNLUCKY": value_score += 25
        if keeper_status == "LEAKY": value_score += 15
        if pnl > 10: value_score += 10
        
        total_bets = team_data.get('total_bets', 0) or 0
        confidence = min(1.0, total_bets / 50)
        
        recommended, avoid = self._generate_recommendations(dna)
        all_insights = m_insights + t_insights + l_insights + tac_insights
        
        return QuantumScore(
            team_name=team_name,
            overall_score=round(overall, 1),
            value_score=round(value_score, 1),
            confidence=round(confidence, 2),
            mentality_score=round(mentality_score, 1),
            temporal_score=round(temporal_score, 1),
            luck_score=round(luck_score, 1),
            tactical_score=round(tactical_score, 1),
            recommended_bets=recommended,
            avoid_bets=avoid,
            insights=all_insights,
            tier=team_data.get('tier', 'UNKNOWN'),
            historical_pnl=pnl,
            win_rate=float(team_data.get('win_rate', 0) or 0),
        )
        
    def predict_matchup(self, home_team: str, away_team: str) -> Optional[MatchupPrediction]:
        home_score = self.score_team(home_team)
        away_score = self.score_team(away_team)
        if not home_score or not away_score:
            return None
            
        self.connect()
        friction_score, chaos_potential = 50.0, 50.0
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT friction_score, chaos_potential FROM quantum.matchup_friction
                WHERE (team_a_name = %s AND team_b_name = %s)
                   OR (team_a_name = %s AND team_b_name = %s)
            """, (home_team, away_team, away_team, home_team))
            friction = cur.fetchone()
        if friction:
            friction_score = float(friction['friction_score'] or 50)
            chaos_potential = float(friction['chaos_potential'] or 50)
            
        home_total = home_score.overall_score + 5
        away_total = away_score.overall_score
        
        if home_total > away_total + 10:
            edge_team, edge_magnitude = home_team, home_total - away_total
        elif away_total > home_total + 5:
            edge_team, edge_magnitude = away_team, away_total - home_total
        else:
            edge_team, edge_magnitude = "EVEN", abs(home_total - away_total)
            
        key_factors, secondary_bets, avoid = [], [], []
        
        if friction_score > 70:
            key_factors.append(f"🔥 Haute friction ({friction_score:.0f})")
            secondary_bets.append("OVER 2.5")
        if chaos_potential > 80:
            key_factors.append(f"⚡ Chaos élevé ({chaos_potential:.0f})")
            avoid.append("Paris haute stake")
            
        home_dna = self.get_team_dna(home_team).get('quantum_dna', {})
        away_dna = self.get_team_dna(away_team).get('quantum_dna', {})
        home_luck = home_dna.get('luck_dna', {}).get('luck_profile')
        away_luck = away_dna.get('luck_dna', {}).get('luck_profile')
        
        primary_bet = ""
        if home_luck == "UNLUCKY" and away_luck == "LUCKY":
            key_factors.append(f"🎯 {home_team} UNLUCKY vs {away_team} LUCKY")
            primary_bet = f"{home_team} WIN (value)"
        elif away_luck == "UNLUCKY" and home_luck == "LUCKY":
            key_factors.append(f"🎯 {away_team} UNLUCKY vs {home_team} LUCKY")
            primary_bet = f"{away_team} WIN/DRAW (value)"
            
        if not primary_bet:
            if edge_team != "EVEN" and edge_magnitude > 15:
                primary_bet = f"{edge_team} WIN"
            elif friction_score > 70:
                primary_bet = "OVER 2.5 buts"
            else:
                primary_bet = "Match serré"
                
        key_factors.extend(home_score.insights[:2])
        confidence = (home_score.confidence + away_score.confidence) / 2
        
        return MatchupPrediction(
            home_team=home_team, away_team=away_team,
            friction_score=friction_score, chaos_potential=chaos_potential,
            home_quantum_score=home_score.overall_score,
            away_quantum_score=away_score.overall_score,
            edge_team=edge_team, edge_magnitude=round(edge_magnitude, 1),
            primary_bet=primary_bet, secondary_bets=secondary_bets,
            avoid=avoid, confidence=round(min(1.0, max(0.1, confidence)), 2),
            key_factors=key_factors,
        )
        
    def get_value_picks(self, min_value_score: float = 60) -> List[Dict]:
        self.connect()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT team_name, tier, total_pnl,
                       quantum_dna->'luck_dna'->>'luck_profile' as luck_profile,
                       quantum_dna->'luck_dna'->>'total_luck' as total_luck,
                       quantum_dna->'nemesis_dna'->>'keeper_status' as keeper_status
                FROM quantum.team_profiles
                WHERE (quantum_dna->'luck_dna'->>'luck_profile' = 'UNLUCKY'
                       OR quantum_dna->'nemesis_dna'->>'keeper_status' = 'LEAKY')
                  AND total_pnl > 5
                ORDER BY total_pnl DESC
            """)
            results = cur.fetchall()
            
        value_picks = []
        for r in results:
            score = self.score_team(r['team_name'])
            if score and score.value_score >= min_value_score:
                value_picks.append({
                    "team_name": r['team_name'],
                    "tier": r['tier'],
                    "value_score": score.value_score,
                    "overall_score": score.overall_score,
                    "luck_profile": r['luck_profile'],
                    "keeper_status": r['keeper_status'],
                    "historical_pnl": float(r['total_pnl']),
                    "reason": "UNLUCKY" if r['luck_profile'] == "UNLUCKY" else "LEAKY_KEEPER",
                })
        return sorted(value_picks, key=lambda x: x['value_score'], reverse=True)


if __name__ == "__main__":
    scorer = QuantumScorer()
    
    print("=" * 70)
    print("🔬 QUANTUM SCORER - TEST")
    print("=" * 70)
    
    for team in ["Barcelona", "Athletic Club", "Lazio", "Wolverhampton Wanderers"]:
        score = scorer.score_team(team)
        if score:
            print(f"\n📊 {team} ({score.tier})")
            print(f"   Overall: {score.overall_score}/100 | Value: {score.value_score}")
            print(f"   P&L: +{score.historical_pnl}u | Insights: {score.insights[:2]}")
    
    print("\n" + "=" * 70)
    print("⚔️ MATCHUP: Barcelona vs Athletic Club")
    print("=" * 70)
    
    matchup = scorer.predict_matchup("Barcelona", "Athletic Club")
    if matchup:
        print(f"   Scores: {matchup.home_quantum_score} vs {matchup.away_quantum_score}")
        print(f"   Edge: {matchup.edge_team} | Primary: {matchup.primary_bet}")
        print(f"   Key: {matchup.key_factors[:3]}")
    
    print("\n" + "=" * 70)
    print("🎯 VALUE PICKS")
    print("=" * 70)
    
    for pick in scorer.get_value_picks()[:5]:
        print(f"   {pick['team_name']}: Value={pick['value_score']} | {pick['reason']}")
    
    scorer.close()
