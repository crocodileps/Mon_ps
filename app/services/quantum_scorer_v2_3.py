#!/usr/bin/env python3
"""
🔬 QUANTUM SCORER V2.3 - TALENT BIAS CORRECTION

AMÉLIORATIONS V2.3:
- V2.2 avait r=+0.28 (faible positive)
- Problème: Pénalise trop les "Super Teams" (Bayern Paradox)
- Solution: Ajuster la pénalité LUCK basée sur le TALENT (clinical_finishers)

LOGIQUE TALENT BIAS:
- High clinical_finishers + LUCKY = Talent, pas chance → réduire pénalité
- High clinical_finishers + UNLUCKY = TRUE VALUE → garder bonus
- Low clinical_finishers + LUCKY = Vraie chance → garder pénalité
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
class QuantumVector:
    """Vecteur Quantum V2.3"""
    value_score: float
    quality_score: float
    talent_adjusted_luck: float  # NEW: Luck ajusté par talent
    regression_potential: float
    z_score: float
    verdict: str
    bet_sizing: str
    confidence: float


@dataclass
class QuantumScoreV23:
    """Score Quantum V2.3"""
    team_name: str
    tier: str
    league: str
    vector: QuantumVector
    
    # Composants
    tier_value: float
    public_value: float
    luck_value: float          # Luck brut
    talent_adjustment: float   # NEW: Ajustement talent
    historical_value: float
    keeper_value: float
    
    # Stats
    clinical_finishers: int
    league_rank: int
    league_total: int
    historical_pnl: float
    historical_wr: float
    
    # Actions
    primary_action: str
    bet_types: List[str]
    insights: List[str]


class QuantumScorerV23:
    """
    Quantum Scorer V2.3 - Avec Talent Bias Correction
    
    Le "Bayern Paradox": Ces équipes sont marquées LUCKY mais 
    c'est du TALENT (10 clinical finishers) pas de la chance.
    """
    
    # Tier Value (inchangé)
    TIER_VALUE = {
        "ELITE": 0, "GOLD": 15, "SILVER": 25, "BRONZE": 20, "EXPERIMENTAL": 10,
    }
    
    # Public teams - AJUSTÉ: pénalité moins sévère
    PUBLIC_TEAMS = {
        # Tier 1: Très surcotés
        "Barcelona": -15, "Real Madrid": -15, "Manchester City": -15,
        "Bayern Munich": -15, "Paris Saint Germain": -12,
        # Tier 2: Modérément surcotés
        "Liverpool": -10, "Chelsea": -10, "Manchester United": -10,
        "Juventus": -10, "AC Milan": -8, "Inter": -8, "Arsenal": -8,
    }
    
    # Luck base values
    LUCK_VALUE = {
        "UNLUCKY": 30,
        "NEUTRAL": 10,
        "LUCKY": -15,
    }
    
    # Keeper status
    KEEPER_VALUE = {
        "LEAKY": 20, "SOLID": 5, "ON_FIRE": -10,
    }
    
    # NEW: Seuils de talent
    TALENT_THRESHOLDS = {
        "ELITE_FINISHERS": 7,    # 7+ clinical finishers = équipe d'élite
        "GOOD_FINISHERS": 5,     # 5-6 = bons finisseurs
        "AVERAGE": 3,            # 3-4 = moyen
    }
    
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

    def _calc_tier_value(self, tier: str) -> Tuple[float, str]:
        value = self.TIER_VALUE.get(tier, 10)
        insight = f"Tier {tier}: {value:+.0f}"
        return value, insight
    
    def _calc_public_value(self, team_name: str) -> Tuple[float, str]:
        """Pénalité ajustée par équipe"""
        if team_name in self.PUBLIC_TEAMS:
            penalty = self.PUBLIC_TEAMS[team_name]
            return penalty, f"⚠️ Public team: {penalty:+.0f}"
        return 15, "✅ Non-public: +15"
    
    def _calc_talent_adjusted_luck(self, dna: Dict, team_name: str) -> Tuple[float, float, float, str]:
        """
        NOUVEAU: Ajuste la pénalité LUCK basée sur le TALENT
        
        Returns: (luck_value, talent_adjustment, regression_potential, insight)
        """
        luck = dna.get('luck_dna', {})
        roster = dna.get('roster_dna', {})
        
        profile = luck.get('luck_profile', 'NEUTRAL')
        total_luck = float(luck.get('total_luck', 0) or 0)
        finishing_luck = float(luck.get('finishing_luck', 0) or 0)
        clinical_finishers = int(roster.get('clinical_finishers', 0) or 0)
        
        # Base luck value
        base_luck = self.LUCK_VALUE.get(profile, 10)
        
        # Calcul du talent factor
        if clinical_finishers >= self.TALENT_THRESHOLDS["ELITE_FINISHERS"]:
            talent_level = "ELITE"
            talent_factor = 0.4  # Réduire 60% de la pénalité luck
        elif clinical_finishers >= self.TALENT_THRESHOLDS["GOOD_FINISHERS"]:
            talent_level = "GOOD"
            talent_factor = 0.6  # Réduire 40%
        elif clinical_finishers >= self.TALENT_THRESHOLDS["AVERAGE"]:
            talent_level = "AVERAGE"
            talent_factor = 0.85  # Réduire 15%
        else:
            talent_level = "LOW"
            talent_factor = 1.0  # Pas de réduction
        
        # Appliquer l'ajustement
        if profile == "LUCKY":
            # Pour les LUCKY: réduire la pénalité si talent élevé
            raw_penalty = -min(20, total_luck * 2)
            talent_adjustment = raw_penalty * (1 - talent_factor)
            adjusted_luck = raw_penalty * talent_factor
            regression = -total_luck * 0.5 * talent_factor  # Régression réduite
            
            if talent_level == "ELITE":
                insight = f"🎯 LUCKY mais TALENT ({clinical_finishers} finishers) → pénalité réduite"
            else:
                insight = f"⚠️ LUCKY ({total_luck:+.1f}) → risque régression"
                
        elif profile == "UNLUCKY":
            # Pour les UNLUCKY: GARDER le bonus, voire l'augmenter si talent
            raw_bonus = min(25, abs(total_luck) * 2)
            
            if talent_level in ["ELITE", "GOOD"]:
                # Équipe talentueuse + UNLUCKY = MEGA VALUE
                talent_adjustment = 10  # Bonus supplémentaire
                adjusted_luck = raw_bonus + talent_adjustment
                insight = f"🔥 UNLUCKY + TALENT ({clinical_finishers}) = MEGA VALUE"
            else:
                talent_adjustment = 0
                adjusted_luck = raw_bonus
                insight = f"🎯 UNLUCKY ({total_luck:.1f}) = VALUE"
                
            regression = abs(total_luck) * 0.7
            
        else:  # NEUTRAL
            adjusted_luck = base_luck
            talent_adjustment = 0
            regression = 0
            insight = f"ℹ️ Luck neutre ({clinical_finishers} finishers)"
            
        return adjusted_luck, talent_adjustment, regression, insight
    
    def _calc_keeper_value(self, dna: Dict) -> Tuple[float, str]:
        nemesis = dna.get('nemesis_dna', {})
        status = nemesis.get('keeper_status', 'SOLID')
        value = self.KEEPER_VALUE.get(status, 5)
        
        if status == "LEAKY":
            insight = "🎯 Gardien LEAKY = value"
        elif status == "ON_FIRE":
            insight = "⚠️ Gardien ON_FIRE = temp."
        else:
            insight = "ℹ️ Gardien stable"
        return value, insight
    
    def _calc_historical_value(self, pnl: float, win_rate: float, total_bets: int) -> Tuple[float, str]:
        if total_bets < 5:
            return 0, "ℹ️ Historique insuffisant"
        
        wr_bonus = 0
        if win_rate >= 85:
            wr_bonus = 30
        elif win_rate >= 75:
            wr_bonus = 20
        elif win_rate >= 65:
            wr_bonus = 10
        elif win_rate < 50:
            wr_bonus = -15
            
        pnl_bonus = 0
        if pnl >= 15:
            pnl_bonus = 20
        elif pnl >= 10:
            pnl_bonus = 15
        elif pnl >= 5:
            pnl_bonus = 10
        elif pnl > 0:
            pnl_bonus = 5
        elif pnl < -5:
            pnl_bonus = -15
            
        total = wr_bonus + pnl_bonus
        
        if total >= 35:
            insight = f"🔥 Historique excellent (WR:{win_rate:.0f}%, +{pnl:.1f}u)"
        elif total >= 20:
            insight = f"✅ Historique bon"
        elif total < 0:
            insight = f"⚠️ Historique faible"
        else:
            insight = f"ℹ️ Historique moyen"
            
        return total, insight
    
    def _calc_quality_score(self, dna: Dict) -> float:
        current = dna.get('current_season', {})
        xg_for = float(current.get('xg_for_avg', 1.5) or 1.5)
        xg_against = float(current.get('xg_against_avg', 1.5) or 1.5)
        ppg = float(current.get('ppg', 1.5) or 1.5)
        
        xg_score = 50 + (xg_for - xg_against) * 20
        ppg_score = ppg * 25
        
        return (xg_score * 0.6 + ppg_score * 0.4)

    def _compute_all_scores(self) -> Dict[str, Dict]:
        """Calcule les scores V2.3 pour toutes les équipes"""
        self.connect()
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT team_name, tier, total_pnl, win_rate, total_bets, quantum_dna
                FROM quantum.team_profiles
            """)
            teams = cur.fetchall()
            
        results = {}
        league_scores = {}
        
        for t in teams:
            dna = t['quantum_dna'] or {}
            tier = t['tier'] or 'SILVER'
            pnl = float(t['total_pnl'] or 0)
            wr = float(t['win_rate'] or 0)
            bets = int(t['total_bets'] or 0)
            league = dna.get('league', 'Unknown')
            clinical = int(dna.get('roster_dna', {}).get('clinical_finishers', 0) or 0)
            
            # Calculer composants
            tier_val, _ = self._calc_tier_value(tier)
            public_val, _ = self._calc_public_value(t['team_name'])
            luck_val, talent_adj, regression, _ = self._calc_talent_adjusted_luck(dna, t['team_name'])
            keeper_val, _ = self._calc_keeper_value(dna)
            hist_val, _ = self._calc_historical_value(pnl, wr, bets)
            quality = self._calc_quality_score(dna)
            
            # VALUE SCORE avec talent adjustment
            value_score = tier_val + public_val + luck_val + keeper_val + hist_val
            
            results[t['team_name']] = {
                'team': t['team_name'],
                'tier': tier,
                'league': league,
                'value_score': value_score,
                'quality_score': quality,
                'regression': regression,
                'tier_val': tier_val,
                'public_val': public_val,
                'luck_val': luck_val,
                'talent_adj': talent_adj,
                'keeper_val': keeper_val,
                'hist_val': hist_val,
                'clinical': clinical,
                'pnl': pnl,
                'wr': wr,
                'bets': bets,
            }
            
            if league not in league_scores:
                league_scores[league] = []
            league_scores[league].append((t['team_name'], value_score))
            
        # Z-Score par ligue
        for league, scores in league_scores.items():
            values = [s[1] for s in scores]
            n = len(values)
            mean = sum(values) / n if n > 0 else 0
            variance = sum((x - mean) ** 2 for x in values) / n if n > 0 else 1
            std = math.sqrt(variance) if variance > 0 else 1
            
            sorted_teams = sorted(scores, key=lambda x: x[1], reverse=True)
            
            self._league_stats[league] = {
                'mean': mean, 'std': std, 'count': n,
                'ranks': {t[0]: i+1 for i, t in enumerate(sorted_teams)},
            }
            
            for team_name, score in scores:
                results[team_name]['z_score'] = (score - mean) / std if std > 0 else 0
                results[team_name]['league_rank'] = self._league_stats[league]['ranks'][team_name]
                results[team_name]['league_total'] = n
                
        return results

    def calculate_score(self, team_name: str) -> Optional[QuantumScoreV23]:
        """Calcule le score V2.3"""
        data = self._get_team_data(team_name)
        if not data:
            return None
            
        all_scores = self._compute_all_scores()
        if team_name not in all_scores:
            return None
            
        s = all_scores[team_name]
        dna = data.get('quantum_dna', {})
        
        # Insights
        _, tier_insight = self._calc_tier_value(s['tier'])
        _, public_insight = self._calc_public_value(team_name)
        _, _, _, luck_insight = self._calc_talent_adjusted_luck(dna, team_name)
        _, keeper_insight = self._calc_keeper_value(dna)
        _, hist_insight = self._calc_historical_value(s['pnl'], s['wr'], s['bets'])
        
        # Verdict
        z = s['z_score']
        
        if z >= 2.0:
            verdict, bet_sizing = "STRONG_BUY", "MAX_BET"
            primary_action = f"🔥 MAX BET sur {team_name}"
        elif z >= 1.0:
            verdict, bet_sizing = "BUY", "NORMAL"
            primary_action = f"✅ BUY {team_name}"
        elif z >= 0.5:
            verdict, bet_sizing = "BUY", "SMALL"
            primary_action = f"👍 Small bet {team_name}"
        elif z <= -2.0:
            verdict, bet_sizing = "STRONG_SELL", "FADE"
            primary_action = f"🚫 FADE {team_name}"
        elif z <= -1.0:
            verdict, bet_sizing = "SELL", "AVOID"
            primary_action = f"⚠️ Éviter {team_name}"
        elif z <= -0.5:
            verdict, bet_sizing = "SELL", "AVOID"
            primary_action = f"⚠️ Prudence {team_name}"
        else:
            verdict, bet_sizing = "HOLD", "SKIP"
            primary_action = f"⏸️ Pas d'edge {team_name}"
        
        confidence = min(1.0, s['bets'] / 30)
        if s['wr'] >= 75:
            confidence += 0.15
        if abs(z) >= 1.5:
            confidence += 0.1
            
        bet_types = []
        if verdict in ["STRONG_BUY", "BUY"]:
            bet_types.append("TEAM_WIN")
            if s['luck_val'] > 25:
                bet_types.append("OVER goals")
        elif verdict in ["STRONG_SELL", "SELL"]:
            bet_types.append("FADE")
            
        insights = [
            f"💰 Value: {s['value_score']:.0f} | Z={z:+.2f}",
            luck_insight,
            f"🎯 Clinical Finishers: {s['clinical']}",
            hist_insight,
        ]
        
        vector = QuantumVector(
            value_score=round(s['value_score'], 1),
            quality_score=round(s['quality_score'], 1),
            talent_adjusted_luck=round(s['luck_val'], 1),
            regression_potential=round(s['regression'], 1),
            z_score=round(z, 2),
            verdict=verdict,
            bet_sizing=bet_sizing,
            confidence=round(min(1.0, confidence), 2),
        )
        
        return QuantumScoreV23(
            team_name=team_name,
            tier=s['tier'],
            league=s['league'],
            vector=vector,
            tier_value=s['tier_val'],
            public_value=s['public_val'],
            luck_value=s['luck_val'],
            talent_adjustment=s['talent_adj'],
            historical_value=s['hist_val'],
            keeper_value=s['keeper_val'],
            clinical_finishers=s['clinical'],
            league_rank=s['league_rank'],
            league_total=s['league_total'],
            historical_pnl=s['pnl'],
            historical_wr=s['wr'],
            primary_action=primary_action,
            bet_types=bet_types,
            insights=insights,
        )

    def get_all_sorted(self) -> List[Dict]:
        all_scores = self._compute_all_scores()
        results = []
        for team, s in all_scores.items():
            results.append({
                'team': team,
                'league': s['league'],
                'tier': s['tier'],
                'value_score': s['value_score'],
                'z_score': s['z_score'],
                'pnl': s['pnl'],
                'wr': s['wr'],
                'clinical': s['clinical'],
                'talent_adj': s['talent_adj'],
                'rank': f"{s['league_rank']}/{s['league_total']}",
            })
        return sorted(results, key=lambda x: x['z_score'], reverse=True)


# === BACKTESTING ===
if __name__ == "__main__":
    scorer = QuantumScorerV23()
    
    print("=" * 80)
    print("🔬 QUANTUM SCORER V2.3 - TALENT BIAS CORRECTION")
    print("=" * 80)
    
    # Test Bayern Paradox
    print("\n📊 TEST BAYERN PARADOX:")
    for team in ["Bayern Munich", "Barcelona", "Real Madrid", "Manchester City", "Real Sociedad"]:
        score = scorer.calculate_score(team)
        if score:
            v = score.vector
            print(f"\n   {team}:")
            print(f"      Value: {v.value_score:.0f} | Z={v.z_score:+.2f} | {v.verdict}")
            print(f"      Clinical: {score.clinical_finishers} | Luck: {score.luck_value:+.0f} | TalentAdj: {score.talent_adjustment:+.0f}")
            print(f"      P&L: {score.historical_pnl:+.1f}u | WR: {score.historical_wr:.0f}%")
    
    # Backtesting
    print("\n" + "=" * 80)
    print("🧪 BACKTESTING VALIDATION V2.3")
    print("=" * 80)
    
    all_teams = scorer.get_all_sorted()
    
    # Filter teams with bets
    teams_with_bets = [t for t in all_teams if t['pnl'] != 0 or t['wr'] > 0]
    
    buckets = {
        'Z ≥ 1.5 (BUY)': [t for t in teams_with_bets if t['z_score'] >= 1.5],
        'Z 0.5-1.5': [t for t in teams_with_bets if 0.5 <= t['z_score'] < 1.5],
        'Z -0.5 à 0.5': [t for t in teams_with_bets if -0.5 <= t['z_score'] < 0.5],
        'Z -1.5 à -0.5': [t for t in teams_with_bets if -1.5 <= t['z_score'] < -0.5],
        'Z ≤ -1.5 (FADE)': [t for t in teams_with_bets if t['z_score'] < -1.5],
    }
    
    print(f"\n{'Bucket':<25} | {'N':>3} | {'P&L Total':>10} | {'P&L/Équipe':>10} | {'WR Moy':>7}")
    print("-" * 70)
    
    for bucket_name, teams in buckets.items():
        if teams:
            n = len(teams)
            total_pnl = sum(t['pnl'] for t in teams)
            avg_pnl = total_pnl / n
            avg_wr = sum(t['wr'] for t in teams) / n
            print(f"{bucket_name:<25} | {n:>3} | {total_pnl:>+10.1f}u | {avg_pnl:>+10.2f}u | {avg_wr:>6.1f}%")
    
    # Corrélation
    z_scores = [t['z_score'] for t in teams_with_bets]
    pnls = [t['pnl'] for t in teams_with_bets]
    n = len(teams_with_bets)
    
    if n > 0:
        mean_z = sum(z_scores) / n
        mean_pnl = sum(pnls) / n
        
        numerator = sum((z_scores[i] - mean_z) * (pnls[i] - mean_pnl) for i in range(n))
        denom_z = math.sqrt(sum((z - mean_z) ** 2 for z in z_scores))
        denom_pnl = math.sqrt(sum((p - mean_pnl) ** 2 for p in pnls))
        
        correlation = numerator / (denom_z * denom_pnl) if denom_z > 0 and denom_pnl > 0 else 0
        
        print(f"\n📊 Corrélation Z-Score vs P&L: r = {correlation:+.4f}")
        
        if correlation >= 0.5:
            print("🏆 CORRÉLATION FORTE - HEDGE FUND GRADE!")
        elif correlation >= 0.4:
            print("✅ CORRÉLATION BONNE - Modèle solide!")
        elif correlation >= 0.3:
            print("✅ CORRÉLATION SIGNIFICATIVE")
        elif correlation >= 0.2:
            print("⚠️ Corrélation faible positive")
        else:
            print("❌ Corrélation insuffisante")
    
    # TOP picks
    print("\n" + "=" * 80)
    print("🔥 TOP 10 VALUE PICKS V2.3")
    print("=" * 80)
    
    for t in [x for x in all_teams if x['pnl'] != 0][:10]:
        status = "✅" if t['pnl'] > 0 else "❌"
        print(f"   {t['team']:<25} | Z={t['z_score']:+.2f} | P&L={t['pnl']:+.1f}u | WR={t['wr']:.0f}% | Clinical={t['clinical']} | {status}")
    
    # Comparaison V2.2 vs V2.3 pour les équipes problématiques
    print("\n" + "=" * 80)
    print("📊 CORRECTION BAYERN PARADOX - V2.2 vs V2.3")
    print("=" * 80)
    
    problem_teams = ["Barcelona", "Bayern Munich", "Manchester City", "Lazio"]
    for team in problem_teams:
        s = next((t for t in all_teams if t['team'] == team), None)
        if s:
            # Le Z était trop bas en V2.2, devrait être meilleur maintenant
            print(f"   {team}: Z={s['z_score']:+.2f} | Clinical={s['clinical']} | TalentAdj={s['talent_adj']:+.0f} | P&L={s['pnl']:+.1f}u")
    
    scorer.close()
