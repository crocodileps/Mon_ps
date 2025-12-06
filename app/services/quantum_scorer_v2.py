#!/usr/bin/env python3
"""
🔬 QUANTUM SCORER V2 - SCORING VECTORIEL 3D
Alpha (Force Intrinsèque) | Beta (Perception Marché) | Gamma (VALUE)
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
class Vector3D:
    """Score Vectoriel 3D"""
    alpha: float      # Force intrinsèque
    beta: float       # Perception marché
    gamma: float      # VALUE = Alpha - Beta
    verdict: str      # BUY / SELL / HOLD
    confidence: float # 0-1


@dataclass
class QuantumScoreV2:
    """Score Quantum V2 avec Vector 3D"""
    team_name: str
    tier: str
    
    # Vector 3D
    vector: Vector3D
    
    # Composants Alpha
    alpha_xg: float           # xG differential
    alpha_tactical: float     # Formation + style
    alpha_roster: float       # MVP dependency
    
    # Composants Beta
    beta_historical: float    # Performance passée (marché apprend)
    beta_public_bias: float   # Surcote populaire
    
    # Ajustements
    luck_adjustment: float    # Pénalité/Bonus luck
    regression_expected: float # Régression attendue
    
    # Recommandations
    primary_action: str
    bet_types: List[str]
    avoid: List[str]
    insights: List[str]
    
    # Métadonnées
    historical_pnl: float
    win_rate: float


class QuantumScorerV2:
    """
    Quantum Scorer V2 - Scoring Vectoriel 3D Hedge Fund Grade
    
    Alpha = Force Intrinsèque (ce que l'équipe VAUT)
    Beta = Perception Marché (ce que le marché PENSE)
    Gamma = Alpha - Beta = VALUE RÉELLE
    
    Regret Aversion: Pénalise LUCKY, Bonifie UNLUCKY
    """
    
    # === WEIGHTS ===
    ALPHA_WEIGHTS = {
        "xg_diff": 0.40,        # xG For - xG Against
        "tactical": 0.25,       # Formation + style
        "roster_depth": 0.15,   # Dépendance MVP
        "momentum": 0.20,       # Forme récente
    }
    
    BETA_WEIGHTS = {
        "historical_roi": 0.50,  # Le marché apprend du passé
        "tier_bias": 0.30,       # ELITE = surcotés
        "public_team": 0.20,     # Équipes populaires = taxe
    }
    
    # Équipes "publiques" (surcotées par le marché)
    PUBLIC_TEAMS = [
        "Barcelona", "Real Madrid", "Manchester City", "Liverpool",
        "Bayern Munich", "Paris Saint Germain", "Juventus", "Chelsea"
    ]
    
    TIER_BIAS = {
        "ELITE": 15,        # Surcotés +15
        "GOLD": 5,          # Légèrement surcotés
        "SILVER": 0,        # Fair value
        "BRONZE": -5,       # Sous-cotés
        "EXPERIMENTAL": -10 # Très sous-cotés
    }
    
    def __init__(self):
        self.conn = None
        self._cache = {}
        
    def connect(self):
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
            
    def close(self):
        if self.conn:
            self.conn.close()
            
    def get_team_data(self, team_name: str) -> Optional[Dict]:
        """Récupère données complètes équipe"""
        if team_name in self._cache:
            return self._cache[team_name]
        self.connect()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT team_name, tier, total_pnl, win_rate, total_bets, quantum_dna
                FROM quantum.team_profiles
                WHERE team_name = %s OR team_name ILIKE %s
                LIMIT 1
            """, (team_name, f"%{team_name}%"))
            result = cur.fetchone()
        if result:
            self._cache[team_name] = dict(result)
            return self._cache[team_name]
        return None

    # ═══════════════════════════════════════════════════════════════════
    # ALPHA CALCULATION (Force Intrinsèque)
    # ═══════════════════════════════════════════════════════════════════
    
    def _calc_alpha_xg(self, dna: Dict) -> Tuple[float, str]:
        """Alpha XG: Différentiel xG normalisé"""
        current = dna.get('current_season', {})
        xg_for = float(current.get('xg_for_avg', 1.5) or 1.5)
        xg_against = float(current.get('xg_against_avg', 1.5) or 1.5)
        
        # Différentiel normalisé sur échelle 0-100
        xg_diff = xg_for - xg_against
        # Range typique: -1.0 à +1.0, on normalise sur 0-100
        alpha_xg = 50 + (xg_diff * 30)  # 50 = neutre, ±30 pour extrêmes
        
        insight = f"xG Diff: {xg_diff:+.2f}/match"
        return max(0, min(100, alpha_xg)), insight
        
    def _calc_alpha_tactical(self, dna: Dict) -> Tuple[float, str]:
        """Alpha Tactical: Formation + Style"""
        tactical = dna.get('tactical_dna', {})
        psyche = dna.get('psyche_dna', {})
        
        formation = tactical.get('main_formation', '4-4-2')
        mentality = psyche.get('profile', 'BALANCED')
        
        # Formations rentables (de l'analyse Phase 1)
        formation_scores = {
            "4-3-3": 85, "4-2-3-1": 80, "4-1-4-1": 70,
            "3-4-2-1": 60, "4-4-2": 55, "3-4-3": 50, "3-5-2": 45,
        }
        
        # Mentalités rentables
        mentality_scores = {
            "CONSERVATIVE": 90, "BALANCED": 70, "VOLATILE": 50,
            "PREDATOR": 45, "FRAGILE": 30,
        }
        
        form_score = formation_scores.get(formation, 55)
        ment_score = mentality_scores.get(mentality, 60)
        
        alpha = (form_score * 0.4) + (ment_score * 0.6)
        insight = f"Formation: {formation}, Mentality: {mentality}"
        return alpha, insight
        
    def _calc_alpha_roster(self, dna: Dict) -> Tuple[float, str]:
        """Alpha Roster: Profondeur effectif (inverse de dépendance)"""
        roster = dna.get('roster_dna', {})
        
        mvp_impact = roster.get('mvp_missing_impact', 'MODERATE')
        top3_dep = float(roster.get('top3_dependency', 50) or 50)
        
        # Moins de dépendance = meilleur score
        if mvp_impact == "CRITICAL":
            base = 30
        elif mvp_impact == "HIGH":
            base = 50
        else:
            base = 70
            
        # Ajuster par top3_dependency (plus bas = mieux)
        alpha = base + (100 - top3_dep) * 0.3
        insight = f"MVP Impact: {mvp_impact}, Top3 Dep: {top3_dep:.0f}%"
        return min(100, alpha), insight
        
    def _calc_alpha_momentum(self, dna: Dict) -> Tuple[float, str]:
        """Alpha Momentum: Forme récente basée sur PPG"""
        current = dna.get('current_season', {})
        ppg = float(current.get('ppg', 1.5) or 1.5)
        matches = int(current.get('matches_played', 10) or 10)
        
        # PPG range: 0-3, normaliser sur 0-100
        alpha = min(100, ppg * 33)
        
        # Bonus/malus si beaucoup de matchs (plus fiable)
        if matches >= 12:
            confidence = "HIGH"
        elif matches >= 8:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
            
        insight = f"PPG: {ppg:.2f} ({matches}m, {confidence})"
        return alpha, insight

    # ═══════════════════════════════════════════════════════════════════
    # BETA CALCULATION (Perception Marché)
    # ═══════════════════════════════════════════════════════════════════
    
    def _calc_beta_historical(self, pnl: float, total_bets: int) -> Tuple[float, str]:
        """Beta Historical: Le marché apprend des résultats passés"""
        if total_bets == 0:
            return 50, "Pas d'historique"
            
        # ROI approximatif (1u par bet)
        roi = (pnl / total_bets) * 100 if total_bets > 0 else 0
        
        # Plus l'équipe a été profitable, plus le marché va s'ajuster
        # ROI range: -50% à +50%, normaliser sur 0-100
        beta = 50 + roi * 0.5
        
        insight = f"ROI: {roi:+.1f}% sur {total_bets} bets"
        return max(0, min(100, beta)), insight
        
    def _calc_beta_tier(self, tier: str) -> Tuple[float, str]:
        """Beta Tier: Biais de perception par tier"""
        bias = self.TIER_BIAS.get(tier, 0)
        beta = 50 + bias
        insight = f"Tier {tier}: {bias:+d} bias"
        return beta, insight
        
    def _calc_beta_public(self, team_name: str) -> Tuple[float, str]:
        """Beta Public: Taxe sur équipes populaires"""
        if team_name in self.PUBLIC_TEAMS:
            return 75, f"Public team: +25 surcote"
        return 50, "Non-public team"

    # ═══════════════════════════════════════════════════════════════════
    # LUCK ADJUSTMENT (Regret Aversion)
    # ═══════════════════════════════════════════════════════════════════
    
    def _calc_luck_adjustment(self, dna: Dict) -> Tuple[float, float, str]:
        """
        Luck Adjustment: Pénalise LUCKY, Bonifie UNLUCKY
        Returns: (adjustment, regression_expected, insight)
        """
        luck = dna.get('luck_dna', {})
        profile = luck.get('luck_profile', 'NEUTRAL')
        total_luck = float(luck.get('total_luck', 0) or 0)
        
        if profile == "LUCKY":
            # Pénalité proportionnelle à la chance
            adjustment = -min(20, total_luck * 2)
            regression = -total_luck * 0.7  # Attend régression négative
            insight = f"⚠️ LUCKY ({total_luck:+.1f}) → Pénalité {adjustment:.0f}"
            
        elif profile == "UNLUCKY":
            # Bonus proportionnel à la malchance
            adjustment = min(25, abs(total_luck) * 2)
            regression = abs(total_luck) * 0.7  # Attend régression positive
            insight = f"🎯 UNLUCKY ({total_luck:.1f}) → Bonus +{adjustment:.0f}"
            
        else:
            adjustment = 0
            regression = 0
            insight = "NEUTRAL luck"
            
        return adjustment, regression, insight

    # ═══════════════════════════════════════════════════════════════════
    # VECTOR 3D CALCULATION
    # ═══════════════════════════════════════════════════════════════════
    
    def calculate_vector_3d(self, team_name: str) -> Optional[QuantumScoreV2]:
        """Calcule le Score Vectoriel 3D complet"""
        data = self.get_team_data(team_name)
        if not data:
            return None
            
        dna = data.get('quantum_dna', {})
        tier = data.get('tier', 'SILVER')
        pnl = float(data.get('total_pnl', 0) or 0)
        win_rate = float(data.get('win_rate', 0) or 0)
        total_bets = int(data.get('total_bets', 0) or 0)
        
        insights = []
        
        # === ALPHA COMPONENTS ===
        alpha_xg, xg_insight = self._calc_alpha_xg(dna)
        alpha_tactical, tact_insight = self._calc_alpha_tactical(dna)
        alpha_roster, roster_insight = self._calc_alpha_roster(dna)
        alpha_momentum, mom_insight = self._calc_alpha_momentum(dna)
        
        # Alpha composite
        ALPHA = (
            alpha_xg * self.ALPHA_WEIGHTS['xg_diff'] +
            alpha_tactical * self.ALPHA_WEIGHTS['tactical'] +
            alpha_roster * self.ALPHA_WEIGHTS['roster_depth'] +
            alpha_momentum * self.ALPHA_WEIGHTS['momentum']
        )
        
        # === BETA COMPONENTS ===
        beta_hist, hist_insight = self._calc_beta_historical(pnl, total_bets)
        beta_tier, tier_insight = self._calc_beta_tier(tier)
        beta_public, public_insight = self._calc_beta_public(team_name)
        
        # Beta composite
        BETA = (
            beta_hist * self.BETA_WEIGHTS['historical_roi'] +
            beta_tier * self.BETA_WEIGHTS['tier_bias'] +
            beta_public * self.BETA_WEIGHTS['public_team']
        )
        
        # === LUCK ADJUSTMENT ===
        luck_adj, regression, luck_insight = self._calc_luck_adjustment(dna)
        insights.append(luck_insight)
        
        # === GAMMA (VALUE) ===
        GAMMA = ALPHA - BETA + luck_adj
        
        # === VERDICT ===
        if GAMMA > 15:
            verdict = "STRONG_BUY"
            primary_action = f"🔥 STRONG BUY sur {team_name}"
        elif GAMMA > 5:
            verdict = "BUY"
            primary_action = f"✅ BUY sur {team_name}"
        elif GAMMA < -15:
            verdict = "STRONG_SELL"
            primary_action = f"🚫 STRONG SELL - Éviter {team_name}"
        elif GAMMA < -5:
            verdict = "SELL"
            primary_action = f"⚠️ SELL - Fade {team_name}"
        else:
            verdict = "HOLD"
            primary_action = f"⏸️ HOLD - Pas d'edge clair"
            
        # === CONFIDENCE ===
        # Plus de bets = plus confiant
        confidence = min(1.0, total_bets / 40)
        # Ajuster par magnitude du gamma
        if abs(GAMMA) > 20:
            confidence += 0.1
            
        # === BET RECOMMENDATIONS ===
        bet_types = []
        avoid = []
        
        luck_profile = dna.get('luck_dna', {}).get('luck_profile', 'NEUTRAL')
        keeper = dna.get('nemesis_dna', {}).get('keeper_status', 'SOLID')
        diesel = float(dna.get('temporal_dna', {}).get('diesel_factor', 0.5) or 0.5)
        
        if verdict in ["BUY", "STRONG_BUY"]:
            bet_types.append("TEAM_WIN")
            if luck_profile == "UNLUCKY":
                bet_types.append("OVER goals (régression)")
            if diesel > 0.55:
                bet_types.append("Over 0.5 75-90'")
        else:
            avoid.append("TEAM_WIN")
            if luck_profile == "LUCKY":
                avoid.append("Parier sur cette équipe")
                bet_types.append("FADE / Parier contre")
                
        if keeper == "LEAKY":
            bet_types.append("OVER goals match")
        elif keeper == "ON_FIRE":
            bet_types.append("UNDER (court-terme)")
            
        # === INSIGHTS ===
        insights.append(f"α={ALPHA:.1f} (xG:{alpha_xg:.0f}, Tact:{alpha_tactical:.0f})")
        insights.append(f"β={BETA:.1f} (Hist:{beta_hist:.0f}, Tier:{beta_tier:.0f})")
        insights.append(f"γ={GAMMA:+.1f} → {verdict}")
        
        # === BUILD RESULT ===
        vector = Vector3D(
            alpha=round(ALPHA, 1),
            beta=round(BETA, 1),
            gamma=round(GAMMA, 1),
            verdict=verdict,
            confidence=round(confidence, 2)
        )
        
        return QuantumScoreV2(
            team_name=team_name,
            tier=tier,
            vector=vector,
            alpha_xg=round(alpha_xg, 1),
            alpha_tactical=round(alpha_tactical, 1),
            alpha_roster=round(alpha_roster, 1),
            beta_historical=round(beta_hist, 1),
            beta_public_bias=round(beta_public, 1),
            luck_adjustment=round(luck_adj, 1),
            regression_expected=round(regression, 1),
            primary_action=primary_action,
            bet_types=bet_types,
            avoid=avoid,
            insights=insights,
            historical_pnl=pnl,
            win_rate=win_rate,
        )
        
    def get_all_verdicts(self) -> List[Dict]:
        """Récupère tous les verdicts triés par Gamma"""
        self.connect()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT team_name FROM quantum.team_profiles")
            teams = [r['team_name'] for r in cur.fetchall()]
            
        results = []
        for team in teams:
            score = self.calculate_vector_3d(team)
            if score:
                results.append({
                    "team": team,
                    "tier": score.tier,
                    "alpha": score.vector.alpha,
                    "beta": score.vector.beta,
                    "gamma": score.vector.gamma,
                    "verdict": score.vector.verdict,
                    "pnl": score.historical_pnl,
                    "luck_adj": score.luck_adjustment,
                })
                
        return sorted(results, key=lambda x: x['gamma'], reverse=True)
        
    def get_buy_signals(self) -> List[Dict]:
        """Équipes avec signal BUY/STRONG_BUY"""
        all_verdicts = self.get_all_verdicts()
        return [v for v in all_verdicts if v['verdict'] in ['BUY', 'STRONG_BUY']]
        
    def get_sell_signals(self) -> List[Dict]:
        """Équipes avec signal SELL/STRONG_SELL"""
        all_verdicts = self.get_all_verdicts()
        return [v for v in all_verdicts if v['verdict'] in ['SELL', 'STRONG_SELL']]


# === TEST ===
if __name__ == "__main__":
    scorer = QuantumScorerV2()
    
    print("=" * 80)
    print("🔬 QUANTUM SCORER V2 - SCORING VECTORIEL 3D")
    print("=" * 80)
    
    # Test équipes clés
    test_teams = ["Barcelona", "Athletic Club", "Wolverhampton Wanderers", "Lazio", "Newcastle United"]
    
    for team in test_teams:
        score = scorer.calculate_vector_3d(team)
        if score:
            v = score.vector
            print(f"\n{'='*60}")
            print(f"📊 {team} ({score.tier})")
            print(f"   🧬 VECTOR 3D: α={v.alpha:.1f} | β={v.beta:.1f} | γ={v.gamma:+.1f}")
            print(f"   📈 VERDICT: {v.verdict} (conf: {v.confidence:.0%})")
            print(f"   🎯 ACTION: {score.primary_action}")
            print(f"   💡 Luck Adj: {score.luck_adjustment:+.1f} | Régression: {score.regression_expected:+.1f}")
            if score.bet_types:
                print(f"   ✅ BET: {score.bet_types[:2]}")
            if score.avoid:
                print(f"   ❌ AVOID: {score.avoid[:2]}")
    
    print("\n" + "=" * 80)
    print("🔥 TOP 10 BUY SIGNALS (Gamma > 5)")
    print("=" * 80)
    
    for s in scorer.get_buy_signals()[:10]:
        print(f"   {s['team']}: γ={s['gamma']:+.1f} | {s['verdict']} | P&L={s['pnl']:+.1f}u | LuckAdj={s['luck_adj']:+.1f}")
    
    print("\n" + "=" * 80)
    print("🚫 TOP 5 SELL SIGNALS (Gamma < -5)")
    print("=" * 80)
    
    for s in scorer.get_sell_signals()[:5]:
        print(f"   {s['team']}: γ={s['gamma']:+.1f} | {s['verdict']} | P&L={s['pnl']:+.1f}u")
    
    scorer.close()
