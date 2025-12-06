#!/usr/bin/env python3
"""
🔥 QUANTUM MATCHUP SCORER - Phase 2.5

Combine:
- Z-Score V2.4 des deux équipes
- Friction matrix (3,403 pairs)
- DNA vectors pour prédictions de buts

Output:
- Prédiction du gagnant
- Recommandation OVER/UNDER
- BTTS probability
- Sizing du pari (basé sur chaos)
"""

import math
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
import psycopg2
from psycopg2.extras import RealDictCursor

# Importer V2.4
import sys
sys.path.append('/home/Mon_ps/app/services')
from quantum_scorer_v2_4 import QuantumScorerV24

DB_CONFIG = {
    "host": "localhost", "port": 5432, "database": "monps_db",
    "user": "monps_user", "password": "monps_secure_password_2024"
}


@dataclass
class MatchupPrediction:
    """Prédiction complète d'un matchup"""
    home_team: str
    away_team: str
    
    # Scores individuels
    home_z_score: float
    away_z_score: float
    home_value: float
    away_value: float
    
    # Friction analysis
    friction_score: float
    chaos_potential: float
    
    # Prédictions
    predicted_winner: str        # HOME / AWAY / DRAW
    winner_confidence: float     # 0-1
    predicted_goals: float       # Total attendu
    over25_probability: float    # 0-1
    btts_probability: float      # 0-1
    
    # Recommandations
    primary_bet: str
    secondary_bets: List[str]
    bet_sizing: str              # MAX / NORMAL / SMALL / SKIP
    avoid_reasons: List[str]
    
    # Insights
    key_factors: List[str]
    edge_magnitude: float


@dataclass
class TeamMatchupProfile:
    """Profil d'équipe pour le matchup"""
    name: str
    z_score: float
    value_score: float
    xg_for_avg: float
    xg_against_avg: float
    diesel_factor: float
    mentality: str
    keeper_status: str
    style: str
    is_home: bool


class QuantumMatchupScorer:
    """
    Matchup Scorer combinant V2.4 + Friction Matrix
    
    Logique:
    1. Récupérer Z-Scores V2.4 des deux équipes
    2. Récupérer friction entre les deux
    3. Calculer expected goals basé sur xG
    4. Ajuster par friction (high friction = more goals)
    5. Recommander le meilleur pari
    """
    
    # Home advantage en termes de xG
    HOME_ADVANTAGE_XG = 0.25
    
    # Thresholds
    CHAOS_THRESHOLD_HIGH = 70
    FRICTION_THRESHOLD_HIGH = 65
    
    def __init__(self):
        self.conn = None
        self.v24_scorer = QuantumScorerV24()
        self._friction_cache = {}
        
    def connect(self):
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
            
    def close(self):
        if self.conn:
            self.conn.close()
        self.v24_scorer.close()

    def _get_team_dna(self, team_name: str) -> Optional[Dict]:
        """Récupère le DNA complet d'une équipe"""
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
        """Récupère la friction entre deux équipes"""
        cache_key = f"{team_a}_{team_b}"
        if cache_key in self._friction_cache:
            return self._friction_cache[cache_key]
            
        self.connect()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT friction_score, chaos_potential,
                       style_clash_score, tempo_clash_score, mental_clash_score,
                       predicted_goals, predicted_btts_prob, predicted_over25_prob,
                       predicted_winner, h2h_matches, h2h_avg_goals,
                       h2h_team_a_wins, h2h_team_b_wins, h2h_draws
                FROM quantum.matchup_friction
                WHERE (team_a_name = %s AND team_b_name = %s)
                   OR (team_a_name = %s AND team_b_name = %s)
                LIMIT 1
            """, (team_a, team_b, team_b, team_a))
            result = cur.fetchone()
            
        if result:
            self._friction_cache[cache_key] = dict(result)
            return self._friction_cache[cache_key]
        
        # Default si pas de friction trouvée
        return {
            'friction_score': 50.0,
            'chaos_potential': 50.0,
            'h2h_matches': 0,
        }

    def _build_team_profile(self, team_name: str, is_home: bool) -> Optional[TeamMatchupProfile]:
        """Construit le profil matchup d'une équipe"""
        # Score V2.4
        v24_score = self.v24_scorer.calculate_score(team_name)
        if not v24_score:
            return None
            
        # DNA
        team_data = self._get_team_dna(team_name)
        if not team_data:
            return None
            
        dna = team_data.get('quantum_dna', {})
        current = dna.get('current_season', {})
        temporal = dna.get('temporal_dna', {})
        psyche = dna.get('psyche_dna', {})
        nemesis = dna.get('nemesis_dna', {})
        
        return TeamMatchupProfile(
            name=team_name,
            z_score=v24_score.vector.z_score,
            value_score=v24_score.vector.value_score,
            xg_for_avg=float(current.get('xg_for_avg', 1.3) or 1.3),
            xg_against_avg=float(current.get('xg_against_avg', 1.3) or 1.3),
            diesel_factor=float(temporal.get('diesel_factor', 0.5) or 0.5),
            mentality=psyche.get('profile', 'BALANCED'),
            keeper_status=nemesis.get('keeper_status', 'SOLID'),
            style=nemesis.get('style', 'HYBRID'),
            is_home=is_home,
        )

    def _calculate_expected_goals(self, home: TeamMatchupProfile, away: TeamMatchupProfile, 
                                   friction: Dict) -> Tuple[float, float, float]:
        """
        Calcule les buts attendus
        Returns: (home_xg, away_xg, total_xg)
        """
        # Base: moyenne des xG for/against
        home_attack = home.xg_for_avg
        home_defense = home.xg_against_avg
        away_attack = away.xg_for_avg
        away_defense = away.xg_against_avg
        
        # Home expected = (home_attack + away_defense) / 2 + home_advantage
        home_xg = (home_attack + away_defense) / 2 + self.HOME_ADVANTAGE_XG
        
        # Away expected = (away_attack + home_defense) / 2
        away_xg = (away_attack + home_defense) / 2
        
        # Ajustement par friction (high friction = more open game = more goals)
        friction_score = float(friction.get('friction_score', 50) or 50)
        friction_multiplier = 1 + (friction_score - 50) / 100  # 50 = neutral
        
        home_xg *= friction_multiplier
        away_xg *= friction_multiplier
        
        # Ajustement keeper status
        if home.keeper_status == "LEAKY":
            away_xg *= 1.15
        elif home.keeper_status == "ON_FIRE":
            away_xg *= 0.85
            
        if away.keeper_status == "LEAKY":
            home_xg *= 1.15
        elif away.keeper_status == "ON_FIRE":
            home_xg *= 0.85
        
        total_xg = home_xg + away_xg
        
        return round(home_xg, 2), round(away_xg, 2), round(total_xg, 2)

    def _calculate_btts_prob(self, home_xg: float, away_xg: float) -> float:
        """Probabilité BTTS basée sur Poisson"""
        # P(home scores) = 1 - P(home=0) = 1 - e^(-home_xg)
        p_home_scores = 1 - math.exp(-home_xg)
        p_away_scores = 1 - math.exp(-away_xg)
        
        # BTTS = les deux marquent
        return round(p_home_scores * p_away_scores, 2)

    def _calculate_over25_prob(self, total_xg: float) -> float:
        """Probabilité Over 2.5 basée sur Poisson"""
        # P(over 2.5) = 1 - P(0) - P(1) - P(2)
        p_0 = math.exp(-total_xg)
        p_1 = total_xg * math.exp(-total_xg)
        p_2 = (total_xg ** 2 / 2) * math.exp(-total_xg)
        
        return round(1 - p_0 - p_1 - p_2, 2)

    def _predict_winner(self, home: TeamMatchupProfile, away: TeamMatchupProfile,
                        home_xg: float, away_xg: float) -> Tuple[str, float]:
        """
        Prédit le gagnant
        Returns: (winner, confidence)
        """
        # Différence de Z-Score (ajusté pour home advantage)
        z_diff = (home.z_score + 0.3) - away.z_score  # +0.3 home advantage
        
        # Différence xG
        xg_diff = home_xg - away_xg
        
        # Score combiné
        combined = z_diff * 0.6 + xg_diff * 0.4
        
        if combined > 0.5:
            winner = "HOME"
            confidence = min(0.9, 0.5 + combined * 0.15)
        elif combined < -0.5:
            winner = "AWAY"
            confidence = min(0.9, 0.5 + abs(combined) * 0.15)
        else:
            winner = "DRAW"
            confidence = 0.3 + (1 - abs(combined)) * 0.2
            
        return winner, round(confidence, 2)

    def _determine_bet_sizing(self, chaos: float, confidence: float, 
                               edge: float) -> str:
        """Détermine le sizing basé sur chaos et confidence"""
        if chaos > self.CHAOS_THRESHOLD_HIGH:
            return "SMALL"  # High chaos = réduire la stake
        
        if confidence >= 0.7 and edge > 1.0:
            return "MAX"
        elif confidence >= 0.55 and edge > 0.5:
            return "NORMAL"
        elif confidence >= 0.4:
            return "SMALL"
        else:
            return "SKIP"

    def _generate_recommendations(self, home: TeamMatchupProfile, away: TeamMatchupProfile,
                                   winner: str, over25_prob: float, btts_prob: float,
                                   friction: Dict) -> Tuple[str, List[str], List[str]]:
        """Génère les recommandations de paris"""
        primary = ""
        secondary = []
        avoid = []
        
        friction_score = float(friction.get('friction_score', 50) or 50)
        chaos = float(friction.get('chaos_potential', 50) or 50)
        
        # Primary bet basé sur le gagnant
        if winner == "HOME" and home.z_score > 0.5:
            primary = f"{home.name} WIN"
        elif winner == "AWAY" and away.z_score > 0.5:
            primary = f"{away.name} WIN"
        elif winner == "DRAW":
            primary = "DRAW ou Double Chance"
        else:
            primary = "Pas de pari 1X2 clair"
            
        # Secondary bets
        if over25_prob >= 0.60:
            secondary.append(f"OVER 2.5 ({over25_prob:.0%})")
        elif over25_prob <= 0.35:
            secondary.append(f"UNDER 2.5 ({1-over25_prob:.0%})")
            
        if btts_prob >= 0.55:
            secondary.append(f"BTTS YES ({btts_prob:.0%})")
        elif btts_prob <= 0.35:
            secondary.append(f"BTTS NO ({1-btts_prob:.0%})")
            
        # Bets basés sur diesel
        if home.diesel_factor > 0.55:
            secondary.append(f"{home.name} but 75-90'")
        if away.diesel_factor > 0.55:
            secondary.append(f"{away.name} but 75-90'")
            
        # Avoid reasons
        if chaos > self.CHAOS_THRESHOLD_HIGH:
            avoid.append(f"⚠️ Chaos élevé ({chaos:.0f}) - match imprévisible")
        if home.z_score < -1 and away.z_score < -1:
            avoid.append("⚠️ Les deux équipes en SELL - éviter")
        if friction_score > 75:
            avoid.append(f"⚠️ Friction très haute ({friction_score:.0f}) - volatil")
            
        return primary, secondary, avoid

    def predict_matchup(self, home_team: str, away_team: str) -> Optional[MatchupPrediction]:
        """
        Prédit un matchup complet
        """
        # Profils des équipes
        home = self._build_team_profile(home_team, is_home=True)
        away = self._build_team_profile(away_team, is_home=False)
        
        if not home or not away:
            return None
            
        # Friction
        friction = self._get_friction(home_team, away_team)
        friction_score = float(friction.get('friction_score', 50) or 50)
        chaos = float(friction.get('chaos_potential', 50) or 50)
        
        # Expected goals
        home_xg, away_xg, total_xg = self._calculate_expected_goals(home, away, friction)
        
        # Probabilités
        btts_prob = self._calculate_btts_prob(home_xg, away_xg)
        over25_prob = self._calculate_over25_prob(total_xg)
        
        # Winner
        winner, winner_conf = self._predict_winner(home, away, home_xg, away_xg)
        
        # Edge magnitude
        edge = abs(home.z_score - away.z_score)
        
        # Bet sizing
        bet_sizing = self._determine_bet_sizing(chaos, winner_conf, edge)
        
        # Recommendations
        primary, secondary, avoid = self._generate_recommendations(
            home, away, winner, over25_prob, btts_prob, friction
        )
        
        # Key factors
        key_factors = []
        if home.z_score > 1.0:
            key_factors.append(f"🔥 {home.name} Z=+{home.z_score:.2f} (BUY)")
        if away.z_score > 1.0:
            key_factors.append(f"🔥 {away.name} Z=+{away.z_score:.2f} (BUY)")
        if home.z_score < -1.0:
            key_factors.append(f"⚠️ {home.name} Z={home.z_score:.2f} (SELL)")
        if away.z_score < -1.0:
            key_factors.append(f"⚠️ {away.name} Z={away.z_score:.2f} (SELL)")
        if friction_score > 65:
            key_factors.append(f"🔥 Haute friction ({friction_score:.0f}) = match ouvert")
        if total_xg > 3.0:
            key_factors.append(f"⚽ High scoring expected ({total_xg:.1f} xG)")
        if btts_prob > 0.6:
            key_factors.append(f"⚽ BTTS probable ({btts_prob:.0%})")
            
        return MatchupPrediction(
            home_team=home_team,
            away_team=away_team,
            home_z_score=home.z_score,
            away_z_score=away.z_score,
            home_value=home.value_score,
            away_value=away.value_score,
            friction_score=friction_score,
            chaos_potential=chaos,
            predicted_winner=winner,
            winner_confidence=winner_conf,
            predicted_goals=total_xg,
            over25_probability=over25_prob,
            btts_probability=btts_prob,
            primary_bet=primary,
            secondary_bets=secondary,
            bet_sizing=bet_sizing,
            avoid_reasons=avoid,
            key_factors=key_factors,
            edge_magnitude=edge,
        )

    def get_best_matchups(self, matchups: List[Tuple[str, str]]) -> List[Dict]:
        """
        Analyse plusieurs matchups et retourne les meilleurs
        """
        results = []
        for home, away in matchups:
            pred = self.predict_matchup(home, away)
            if pred and pred.bet_sizing != "SKIP":
                results.append({
                    'match': f"{home} vs {away}",
                    'winner': pred.predicted_winner,
                    'confidence': pred.winner_confidence,
                    'total_xg': pred.predicted_goals,
                    'over25': pred.over25_probability,
                    'btts': pred.btts_probability,
                    'primary_bet': pred.primary_bet,
                    'sizing': pred.bet_sizing,
                    'edge': pred.edge_magnitude,
                })
        
        return sorted(results, key=lambda x: x['edge'], reverse=True)


# === TEST ===
if __name__ == "__main__":
    scorer = QuantumMatchupScorer()
    
    print("=" * 80)
    print("🔥 QUANTUM MATCHUP SCORER - Phase 2.5")
    print("=" * 80)
    
    # Test matchups
    test_matchups = [
        ("Barcelona", "Athletic Club"),
        ("Lazio", "Juventus"),
        ("Liverpool", "Manchester City"),
        ("Real Sociedad", "Real Madrid"),
        ("Newcastle United", "Chelsea"),
    ]
    
    for home, away in test_matchups:
        pred = scorer.predict_matchup(home, away)
        if pred:
            print(f"\n{'='*60}")
            print(f"⚽ {home} vs {away}")
            print(f"{'='*60}")
            print(f"   Z-Scores: {home} {pred.home_z_score:+.2f} | {away} {pred.away_z_score:+.2f}")
            print(f"   Friction: {pred.friction_score:.0f} | Chaos: {pred.chaos_potential:.0f}")
            print(f"   ")
            print(f"   🎯 WINNER: {pred.predicted_winner} ({pred.winner_confidence:.0%})")
            print(f"   ⚽ Total xG: {pred.predicted_goals:.2f}")
            print(f"   📊 Over 2.5: {pred.over25_probability:.0%} | BTTS: {pred.btts_probability:.0%}")
            print(f"   ")
            print(f"   💰 PRIMARY: {pred.primary_bet}")
            print(f"   💰 SECONDARY: {pred.secondary_bets[:2]}")
            print(f"   📏 SIZING: {pred.bet_sizing}")
            if pred.avoid_reasons:
                print(f"   ⚠️ AVOID: {pred.avoid_reasons[:2]}")
            print(f"   💡 KEY: {pred.key_factors[:3]}")
    
    # Meilleurs matchups
    print("\n" + "=" * 80)
    print("🏆 CLASSEMENT DES MATCHUPS PAR EDGE")
    print("=" * 80)
    
    best = scorer.get_best_matchups(test_matchups)
    for i, m in enumerate(best, 1):
        print(f"   {i}. {m['match']}: {m['primary_bet']} | Edge={m['edge']:.2f} | {m['sizing']}")
    
    scorer.close()
