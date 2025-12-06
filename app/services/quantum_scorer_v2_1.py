#!/usr/bin/env python3
"""
🔬 QUANTUM SCORER V2.1 - Z-SCORE PAR LIGUE
Alpha | Beta | Gamma | Z-Score (normalisation par ligue)
"""

import json
import math
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    "host": "localhost", "port": 5432, "database": "monps_db",
    "user": "monps_user", "password": "monps_secure_password_2024"
}


@dataclass
class Vector3DZ:
    """Score Vectoriel 3D + Z-Score"""
    alpha: float
    beta: float
    gamma: float
    z_score: float        # Normalisé par ligue
    verdict: str          # BUY/SELL/HOLD
    verdict_strength: str # MAX_BET / STRONG / NORMAL / FADE_ABSOLUTE
    confidence: float


@dataclass
class QuantumScoreV21:
    """Score Quantum V2.1"""
    team_name: str
    tier: str
    league: str
    vector: Vector3DZ
    
    # Stats ligue
    league_avg_gamma: float
    league_std_gamma: float
    league_rank: int
    league_total: int
    
    # Recommandations
    primary_action: str
    bet_sizing: str  # MAX_BET / NORMAL / SMALL / AVOID
    bet_types: List[str]
    insights: List[str]
    
    historical_pnl: float


class QuantumScorerV21:
    """
    Quantum Scorer V2.1 - Avec Z-Score par Ligue
    
    Z-Score > +2.0 : MAX BET (anomalie statistique)
    Z-Score > +1.0 : STRONG BUY
    Z-Score > +0.5 : BUY
    Z-Score < -0.5 : SELL
    Z-Score < -1.0 : STRONG SELL
    Z-Score < -2.0 : FADE ABSOLUTE
    """
    
    ALPHA_WEIGHTS = {"xg_diff": 0.40, "tactical": 0.25, "roster": 0.15, "momentum": 0.20}
    BETA_WEIGHTS = {"historical": 0.50, "tier": 0.30, "public": 0.20}
    
    PUBLIC_TEAMS = ["Barcelona", "Real Madrid", "Manchester City", "Liverpool",
                    "Bayern Munich", "Paris Saint Germain", "Juventus", "Chelsea"]
    
    TIER_BIAS = {"ELITE": 15, "GOLD": 5, "SILVER": 0, "BRONZE": -5, "EXPERIMENTAL": -10}
    
    def __init__(self):
        self.conn = None
        self._cache = {}
        self._league_stats = {}
        
    def connect(self):
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
            
    def close(self):
        if self.conn:
            self.conn.close()

    def _get_team_data(self, team_name: str) -> Optional[Dict]:
        if team_name in self._cache:
            return self._cache[team_name]
        self.connect()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT team_name, tier, total_pnl, win_rate, total_bets, quantum_dna
                FROM quantum.team_profiles
                WHERE team_name = %s OR team_name ILIKE %s LIMIT 1
            """, (team_name, f"%{team_name}%"))
            result = cur.fetchone()
        if result:
            self._cache[team_name] = dict(result)
            return self._cache[team_name]
        return None

    def _calc_alpha(self, dna: Dict) -> float:
        """Calcul Alpha composite"""
        current = dna.get('current_season', {})
        tactical = dna.get('tactical_dna', {})
        psyche = dna.get('psyche_dna', {})
        roster = dna.get('roster_dna', {})
        
        # XG Diff
        xg_for = float(current.get('xg_for_avg', 1.5) or 1.5)
        xg_against = float(current.get('xg_against_avg', 1.5) or 1.5)
        alpha_xg = 50 + (xg_for - xg_against) * 30
        
        # Tactical
        formation = tactical.get('main_formation', '4-4-2')
        mentality = psyche.get('profile', 'BALANCED')
        form_scores = {"4-3-3": 85, "4-2-3-1": 80, "4-1-4-1": 70, "3-4-2-1": 60, "4-4-2": 55}
        ment_scores = {"CONSERVATIVE": 90, "BALANCED": 70, "VOLATILE": 50, "PREDATOR": 45, "FRAGILE": 30}
        alpha_tact = form_scores.get(formation, 55) * 0.4 + ment_scores.get(mentality, 60) * 0.6
        
        # Roster
        mvp_impact = roster.get('mvp_missing_impact', 'MODERATE')
        alpha_roster = {"CRITICAL": 30, "HIGH": 50, "MODERATE": 70}.get(mvp_impact, 60)
        
        # Momentum
        ppg = float(current.get('ppg', 1.5) or 1.5)
        alpha_mom = min(100, ppg * 33)
        
        return (alpha_xg * 0.40 + alpha_tact * 0.25 + alpha_roster * 0.15 + alpha_mom * 0.20)

    def _calc_beta(self, tier: str, pnl: float, total_bets: int, team_name: str) -> float:
        """Calcul Beta composite"""
        # Historical ROI
        roi = (pnl / total_bets) * 100 if total_bets > 0 else 0
        beta_hist = 50 + roi * 0.5
        
        # Tier bias
        beta_tier = 50 + self.TIER_BIAS.get(tier, 0)
        
        # Public team tax
        beta_public = 75 if team_name in self.PUBLIC_TEAMS else 50
        
        return (beta_hist * 0.50 + beta_tier * 0.30 + beta_public * 0.20)

    def _calc_luck_adj(self, dna: Dict) -> float:
        """Ajustement luck (Regret Aversion)"""
        luck = dna.get('luck_dna', {})
        profile = luck.get('luck_profile', 'NEUTRAL')
        total_luck = float(luck.get('total_luck', 0) or 0)
        
        if profile == "LUCKY":
            return -min(20, total_luck * 2)
        elif profile == "UNLUCKY":
            return min(25, abs(total_luck) * 2)
        return 0

    def _calc_raw_gamma(self, team_name: str) -> Optional[Tuple[float, float, float, float, str]]:
        """Calcule Gamma brut pour une équipe. Returns (alpha, beta, gamma, luck_adj, league)"""
        data = self._get_team_data(team_name)
        if not data:
            return None
            
        dna = data.get('quantum_dna', {})
        tier = data.get('tier', 'SILVER')
        pnl = float(data.get('total_pnl', 0) or 0)
        total_bets = int(data.get('total_bets', 0) or 0)
        league = dna.get('league', 'Unknown')
        
        alpha = self._calc_alpha(dna)
        beta = self._calc_beta(tier, pnl, total_bets, team_name)
        luck_adj = self._calc_luck_adj(dna)
        gamma = alpha - beta + luck_adj
        
        return (alpha, beta, gamma, luck_adj, league)

    def _compute_league_stats(self) -> Dict[str, Dict]:
        """Calcule moyenne et écart-type de Gamma par ligue"""
        self.connect()
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT team_name FROM quantum.team_profiles")
            teams = [r['team_name'] for r in cur.fetchall()]
            
        # Calculer tous les gammas
        league_gammas = {}
        for team in teams:
            result = self._calc_raw_gamma(team)
            if result:
                _, _, gamma, _, league = result
                if league not in league_gammas:
                    league_gammas[league] = []
                league_gammas[league].append((team, gamma))
                
        # Calculer stats par ligue
        stats = {}
        for league, gammas in league_gammas.items():
            values = [g[1] for g in gammas]
            n = len(values)
            if n > 1:
                mean = sum(values) / n
                variance = sum((x - mean) ** 2 for x in values) / n
                std = math.sqrt(variance) if variance > 0 else 1
            else:
                mean, std = 0, 1
                
            # Rank teams
            sorted_teams = sorted(gammas, key=lambda x: x[1], reverse=True)
            ranks = {t[0]: i+1 for i, t in enumerate(sorted_teams)}
            
            stats[league] = {
                "mean": mean,
                "std": std,
                "count": n,
                "ranks": ranks,
                "gammas": {t[0]: t[1] for t in gammas}
            }
            
        self._league_stats = stats
        return stats

    def calculate_score(self, team_name: str) -> Optional[QuantumScoreV21]:
        """Calcule le score complet avec Z-Score"""
        data = self._get_team_data(team_name)
        if not data:
            return None
            
        # Calculer stats ligue si pas fait
        if not self._league_stats:
            self._compute_league_stats()
            
        dna = data.get('quantum_dna', {})
        tier = data.get('tier', 'SILVER')
        pnl = float(data.get('total_pnl', 0) or 0)
        total_bets = int(data.get('total_bets', 0) or 0)
        league = dna.get('league', 'Unknown')
        
        # Calculs de base
        alpha = self._calc_alpha(dna)
        beta = self._calc_beta(tier, pnl, total_bets, team_name)
        luck_adj = self._calc_luck_adj(dna)
        gamma = alpha - beta + luck_adj
        
        # Z-Score par ligue
        league_stat = self._league_stats.get(league, {"mean": 0, "std": 1, "count": 1, "ranks": {}})
        z_score = (gamma - league_stat["mean"]) / league_stat["std"] if league_stat["std"] > 0 else 0
        
        # Verdict basé sur Z-Score
        if z_score >= 2.0:
            verdict = "STRONG_BUY"
            verdict_strength = "MAX_BET"
            bet_sizing = "MAX_BET"
        elif z_score >= 1.0:
            verdict = "BUY"
            verdict_strength = "STRONG"
            bet_sizing = "NORMAL"
        elif z_score >= 0.5:
            verdict = "BUY"
            verdict_strength = "NORMAL"
            bet_sizing = "SMALL"
        elif z_score <= -2.0:
            verdict = "STRONG_SELL"
            verdict_strength = "FADE_ABSOLUTE"
            bet_sizing = "AVOID"
        elif z_score <= -1.0:
            verdict = "SELL"
            verdict_strength = "STRONG"
            bet_sizing = "AVOID"
        elif z_score <= -0.5:
            verdict = "SELL"
            verdict_strength = "NORMAL"
            bet_sizing = "AVOID"
        else:
            verdict = "HOLD"
            verdict_strength = "NORMAL"
            bet_sizing = "SKIP"
            
        # Confidence
        confidence = min(1.0, total_bets / 40)
        if abs(z_score) > 2:
            confidence += 0.15
            
        # Rank dans la ligue
        league_rank = league_stat["ranks"].get(team_name, 0)
        league_total = league_stat["count"]
        
        # Actions et insights
        if verdict in ["STRONG_BUY", "BUY"]:
            primary_action = f"🔥 {verdict_strength}: Parier sur {team_name}"
            bet_types = ["TEAM_WIN", "OVER goals"]
        elif verdict in ["STRONG_SELL", "SELL"]:
            primary_action = f"🚫 {verdict_strength}: Éviter/Fade {team_name}"
            bet_types = ["FADE", "Parier contre"]
        else:
            primary_action = f"⏸️ Pas d'edge clair sur {team_name}"
            bet_types = []
            
        insights = [
            f"🧬 α={alpha:.1f} | β={beta:.1f} | γ={gamma:+.1f}",
            f"📊 Z-Score: {z_score:+.2f} ({league})",
            f"🏆 Rank {league_rank}/{league_total} dans {league}",
            f"🎯 Luck Adj: {luck_adj:+.1f}"
        ]
        
        vector = Vector3DZ(
            alpha=round(alpha, 1),
            beta=round(beta, 1),
            gamma=round(gamma, 1),
            z_score=round(z_score, 2),
            verdict=verdict,
            verdict_strength=verdict_strength,
            confidence=round(confidence, 2)
        )
        
        return QuantumScoreV21(
            team_name=team_name,
            tier=tier,
            league=league,
            vector=vector,
            league_avg_gamma=round(league_stat["mean"], 1),
            league_std_gamma=round(league_stat["std"], 1),
            league_rank=league_rank,
            league_total=league_total,
            primary_action=primary_action,
            bet_sizing=bet_sizing,
            bet_types=bet_types,
            insights=insights,
            historical_pnl=pnl,
        )

    def get_all_by_zscore(self) -> List[Dict]:
        """Toutes les équipes triées par Z-Score"""
        self.connect()
        if not self._league_stats:
            self._compute_league_stats()
            
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT team_name FROM quantum.team_profiles")
            teams = [r['team_name'] for r in cur.fetchall()]
            
        results = []
        for team in teams:
            score = self.calculate_score(team)
            if score:
                results.append({
                    "team": team,
                    "league": score.league,
                    "tier": score.tier,
                    "gamma": score.vector.gamma,
                    "z_score": score.vector.z_score,
                    "verdict": score.vector.verdict,
                    "strength": score.vector.verdict_strength,
                    "bet_sizing": score.bet_sizing,
                    "rank": f"{score.league_rank}/{score.league_total}",
                    "pnl": score.historical_pnl,
                })
        return sorted(results, key=lambda x: x['z_score'], reverse=True)

    def get_max_bets(self) -> List[Dict]:
        """Équipes avec Z-Score > 2 (anomalies)"""
        return [x for x in self.get_all_by_zscore() if x['z_score'] >= 2.0]

    def get_fade_absolute(self) -> List[Dict]:
        """Équipes avec Z-Score < -2"""
        return [x for x in self.get_all_by_zscore() if x['z_score'] <= -2.0]

    def get_league_summary(self) -> Dict:
        """Résumé par ligue"""
        if not self._league_stats:
            self._compute_league_stats()
        return {
            league: {"avg_gamma": round(s["mean"], 1), "std": round(s["std"], 1), "teams": s["count"]}
            for league, s in self._league_stats.items()
        }


# === TEST ===
if __name__ == "__main__":
    scorer = QuantumScorerV21()
    
    print("=" * 80)
    print("🔬 QUANTUM SCORER V2.1 - Z-SCORE PAR LIGUE")
    print("=" * 80)
    
    # Stats par ligue
    print("\n📊 STATS PAR LIGUE:")
    for league, stats in scorer.get_league_summary().items():
        print(f"   {league}: μ={stats['avg_gamma']:+.1f}, σ={stats['std']:.1f}, n={stats['teams']}")
    
    # Test équipes
    print("\n" + "=" * 80)
    test_teams = ["Barcelona", "Athletic Club", "Borussia Dortmund", "Lazio", "Le Havre"]
    for team in test_teams:
        score = scorer.calculate_score(team)
        if score:
            v = score.vector
            print(f"\n📊 {team} ({score.league})")
            print(f"   γ={v.gamma:+.1f} | Z={v.z_score:+.2f} | {v.verdict} ({v.verdict_strength})")
            print(f"   Rank: {score.league_rank}/{score.league_total} | Bet: {score.bet_sizing}")
    
    # MAX BETS
    print("\n" + "=" * 80)
    print("🔥 MAX BETS (Z-Score ≥ 2.0)")
    print("=" * 80)
    for s in scorer.get_max_bets()[:10]:
        print(f"   {s['team']} ({s['league']}): Z={s['z_score']:+.2f} | {s['strength']}")
    
    # FADE ABSOLUTE
    print("\n" + "=" * 80)
    print("🚫 FADE ABSOLUTE (Z-Score ≤ -2.0)")
    print("=" * 80)
    for s in scorer.get_fade_absolute()[:5]:
        print(f"   {s['team']} ({s['league']}): Z={s['z_score']:+.2f} | {s['strength']}")
    
    # TOP 15 global
    print("\n" + "=" * 80)
    print("📈 TOP 15 PAR Z-SCORE (toutes ligues)")
    print("=" * 80)
    for s in scorer.get_all_by_zscore()[:15]:
        print(f"   {s['team']:25} | {s['league']:12} | Z={s['z_score']:+.2f} | {s['verdict']:12} | {s['bet_sizing']}")
    
    scorer.close()
