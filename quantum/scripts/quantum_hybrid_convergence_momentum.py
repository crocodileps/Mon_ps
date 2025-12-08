#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║          QUANTUM BACKTESTER HYBRIDE - CONVERGENCE + MOMENTUM L5                       ║
║                                                                                       ║
║  STRATÉGIE: Combiner la meilleure stratégie (CONVERGENCE_OVER_MC)                    ║
║             avec Momentum L5 comme filtre de validation                               ║
║                                                                                       ║
║  HYPOTHÈSE: Momentum L5 peut AMÉLIORER le WR et ROI de CONVERGENCE                   ║
║             en filtrant les paris quand l'équipe est en mauvaise forme               ║
║                                                                                       ║
║  COMPARAISON:                                                                         ║
║  • CONVERGENCE seul (baseline)                                                        ║
║  • CONVERGENCE + Momentum BLAZING/HOT                                                 ║
║  • CONVERGENCE + Momentum ≥ WARMING                                                   ║
║  • CONVERGENCE + Momentum Score > 60                                                  ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

import psycopg2
import psycopg2.extras
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import json

# ═══════════════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════════════

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

# Cotes moyennes
AVG_ODDS = {
    'over_25': 1.85,
    'over_35': 2.50,
    'btts_yes': 1.75,
}


# ═══════════════════════════════════════════════════════════════════════════════════════
# MOMENTUM L5 (identique à V2)
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class MomentumL5:
    """Momentum basé sur les 5 derniers matchs"""
    form_points: int = 0
    form_percentage: float = 0.0
    goal_diff: int = 0
    goals_for: int = 0
    goals_against: int = 0
    streak_type: str = "NEUTRAL"
    streak_length: int = 0
    acceleration: float = 0.0
    trend: str = "NEUTRAL"
    
    @property
    def score(self) -> float:
        """Score composite 0-100"""
        base = self.form_percentage
        
        if self.streak_type == "W":
            base += min(20, self.streak_length * 5)
        elif self.streak_type == "L":
            base -= min(20, self.streak_length * 5)
        
        base += self.acceleration * 10
        
        return max(0, min(100, base))
    
    @property
    def is_blazing(self) -> bool:
        return self.trend == "BLAZING"
    
    @property
    def is_hot(self) -> bool:
        return self.trend in ["BLAZING", "HOT"]
    
    @property
    def is_warming_plus(self) -> bool:
        return self.trend in ["BLAZING", "HOT", "WARMING"]
    
    @property
    def is_cold(self) -> bool:
        return self.trend in ["COLD", "FREEZING"]


def calculate_momentum_l5(matches: List[Dict], team_name: str) -> MomentumL5:
    """
    Calcule le momentum sur les 5 derniers matchs.
    matches doit être trié par date DESC (plus récent en premier)
    """
    momentum = MomentumL5()
    
    if len(matches) < 3:
        return momentum
    
    last_5 = matches[:5]
    results = []
    goals_for = 0
    goals_against = 0
    
    team_lower = team_name.lower()
    
    for match in last_5:
        home_lower = match['home_team'].lower()
        is_home = home_lower == team_lower
        
        hg = match['home_goals']
        ag = match['away_goals']
        
        if is_home:
            gf, ga = hg, ag
        else:
            gf, ga = ag, hg
        
        goals_for += gf
        goals_against += ga
        
        if gf > ga:
            results.append('W')
        elif gf < ga:
            results.append('L')
        else:
            results.append('D')
    
    # Form points
    for r in results:
        if r == 'W':
            momentum.form_points += 3
        elif r == 'D':
            momentum.form_points += 1
    
    max_points = len(results) * 3
    momentum.form_percentage = (momentum.form_points / max_points * 100) if max_points > 0 else 0
    momentum.goal_diff = goals_for - goals_against
    momentum.goals_for = goals_for
    momentum.goals_against = goals_against
    
    # Streak detection
    if len(results) >= 2 and results[0] == results[1]:
        momentum.streak_type = results[0]
        momentum.streak_length = 2
        if len(results) >= 3 and results[2] == results[0]:
            momentum.streak_length = 3
            if len(results) >= 4 and results[3] == results[0]:
                momentum.streak_length = 4
                if len(results) >= 5 and results[4] == results[0]:
                    momentum.streak_length = 5
    
    # Acceleration: L3 vs L4-L5
    if len(results) >= 5:
        l3_points = sum(3 if r == 'W' else 1 if r == 'D' else 0 for r in results[:3])
        l45_points = sum(3 if r == 'W' else 1 if r == 'D' else 0 for r in results[3:5])
        l3_avg = l3_points / 3
        l45_avg = l45_points / 2
        momentum.acceleration = l3_avg - l45_avg
    
    # Trend classification
    if momentum.streak_type == "W" and momentum.streak_length >= 4:
        momentum.trend = "BLAZING"
    elif momentum.streak_type == "W" and momentum.streak_length >= 3:
        momentum.trend = "HOT"
    elif momentum.form_percentage >= 70:
        momentum.trend = "WARMING"
    elif momentum.form_percentage <= 25:
        momentum.trend = "FREEZING"
    elif momentum.streak_type == "L" and momentum.streak_length >= 3:
        momentum.trend = "COLD"
    elif momentum.form_percentage <= 40:
        momentum.trend = "COOLING"
    else:
        momentum.trend = "NEUTRAL"
    
    return momentum


# ═══════════════════════════════════════════════════════════════════════════════════════
# CONDITIONS CONVERGENCE
# ═══════════════════════════════════════════════════════════════════════════════════════

def check_convergence_over(home_dna: Dict, away_dna: Dict, friction: Dict) -> Tuple[bool, float]:
    """
    Vérifie les conditions CONVERGENCE_OVER_MC.
    
    Conditions:
    - xG combiné élevé (home_xg + away_xg > 2.8)
    - Friction élevée (chaos_potential > 55 OU predicted_goals > 2.5)
    - Au moins une équipe "attacking" ou "balanced-attacking"
    
    Returns:
        (qualifies, confidence)
    """
    home_xg = home_dna.get('xg_for', 1.3)
    away_xg = away_dna.get('xg_for', 1.3)
    home_xga = home_dna.get('xg_against', 1.3)
    away_xga = away_dna.get('xg_against', 1.3)
    
    total_xg = home_xg + away_xg
    total_xga = home_xga + away_xga
    
    chaos = friction.get('chaos_potential', 50)
    predicted = friction.get('predicted_goals', 2.5)
    
    home_style = home_dna.get('style', '').lower()
    away_style = away_dna.get('style', '').lower()
    
    # Conditions de base
    xg_condition = total_xg > 2.8
    friction_condition = chaos > 55 or predicted > 2.5
    style_condition = 'attack' in home_style or 'attack' in away_style
    
    if not (xg_condition and friction_condition):
        return False, 0
    
    # Calcul de la confidence
    confidence = 50
    
    # Bonus xG
    if total_xg > 3.2:
        confidence += 15
    elif total_xg > 3.0:
        confidence += 10
    elif total_xg > 2.8:
        confidence += 5
    
    # Bonus friction
    if chaos > 70:
        confidence += 15
    elif chaos > 60:
        confidence += 10
    elif chaos > 55:
        confidence += 5
    
    # Bonus predicted goals
    if predicted > 3.0:
        confidence += 10
    elif predicted > 2.7:
        confidence += 5
    
    # Bonus style
    if style_condition:
        confidence += 5
    
    # Bonus défense faible
    if total_xga > 3.0:
        confidence += 10
    
    return True, min(100, confidence)


# ═══════════════════════════════════════════════════════════════════════════════════════
# STRUCTURES DE RÉSULTATS
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class StrategyStats:
    """Stats pour une variante de stratégie"""
    name: str
    bets: int = 0
    wins: int = 0
    profit: float = 0.0
    
    @property
    def win_rate(self) -> float:
        return (self.wins / self.bets * 100) if self.bets > 0 else 0.0
    
    @property
    def roi(self) -> float:
        return (self.profit / self.bets * 100) if self.bets > 0 else 0.0


@dataclass
class BetRecord:
    """Enregistrement d'un pari"""
    match_date: datetime
    home_team: str
    away_team: str
    team_perspective: str  # L'équipe qu'on suit
    market: str
    odds: float
    confidence: float
    momentum_score: float
    momentum_trend: str
    is_winner: bool
    profit: float


# ═══════════════════════════════════════════════════════════════════════════════════════
# BACKTESTER HYBRIDE
# ═══════════════════════════════════════════════════════════════════════════════════════

class HybridBacktester:
    """
    Backtester HYBRIDE: CONVERGENCE + Momentum L5
    
    Compare plusieurs variantes:
    1. CONVERGENCE seul (baseline)
    2. CONVERGENCE + Momentum BLAZING/HOT uniquement
    3. CONVERGENCE + Momentum ≥ WARMING
    4. CONVERGENCE + Momentum Score > 60
    5. CONVERGENCE + Momentum Score > 50
    6. CONVERGENCE + Anti-filter (exclure COLD/FREEZING)
    """
    
    def __init__(self):
        self.conn = None
        self.team_dna: Dict[str, Dict] = {}
        self.friction_matrix: Dict[str, Dict] = {}
        
        # Variantes à tester
        self.variants = {
            "CONVERGENCE_BASELINE": StrategyStats("CONVERGENCE (Baseline)"),
            "CONV_MOMENTUM_HOT": StrategyStats("CONV + Momentum HOT+"),
            "CONV_MOMENTUM_WARMING": StrategyStats("CONV + Momentum WARMING+"),
            "CONV_MOMENTUM_60": StrategyStats("CONV + Momentum Score>60"),
            "CONV_MOMENTUM_50": StrategyStats("CONV + Momentum Score>50"),
            "CONV_NO_COLD": StrategyStats("CONV + Exclure COLD/FREEZING"),
            "CONV_ACCELERATION_POS": StrategyStats("CONV + Acceleration>0"),
        }
        
        self.all_bets: List[BetRecord] = []
    
    def connect(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connecté à PostgreSQL")
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def load_team_dna(self):
        """Charge les DNA"""
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            cur.execute("""
                SELECT team_name, tier, quantum_dna
                FROM quantum.team_profiles
            """)
            for row in cur.fetchall():
                team = row['team_name'].lower()
                dna = row['quantum_dna'] or {}
                if isinstance(dna, str):
                    dna = json.loads(dna)
                
                self.team_dna[team] = {
                    'tier': row['tier'] or 'UNKNOWN',
                    'style': dna.get('tactical_dna', {}).get('style', 'balanced'),
                    'xg_for': dna.get('current_season', {}).get('xg', 1.5),
                    'xg_against': dna.get('current_season', {}).get('xga', 1.5),
                    'diesel_factor': dna.get('temporal_dna', {}).get('diesel_factor', 0.5),
                }
            print(f"✅ {len(self.team_dna)} équipes DNA chargées")
        finally:
            cur.close()
    
    def load_friction_matrix(self):
        """Charge la friction"""
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            cur.execute("""
                SELECT team_a_name, team_b_name, chaos_potential, 
                       style_clash_score, tempo_clash_score, predicted_goals
                FROM quantum.matchup_friction
            """)
            for row in cur.fetchall():
                key = f"{row['team_a_name'].lower()}_{row['team_b_name'].lower()}"
                self.friction_matrix[key] = {
                    'chaos_potential': row['chaos_potential'] or 50,
                    'style_clash': row['style_clash_score'] or 50,
                    'tempo_clash': row['tempo_clash_score'] or 50,
                    'predicted_goals': row['predicted_goals'] or 2.5,
                }
            print(f"✅ {len(self.friction_matrix)} paires friction chargées")
        except Exception as e:
            print(f"⚠️ Friction: {e}")
        finally:
            cur.close()
    
    def get_friction(self, home: str, away: str) -> Dict:
        key = f"{home.lower()}_{away.lower()}"
        if key in self.friction_matrix:
            return self.friction_matrix[key]
        key_rev = f"{away.lower()}_{home.lower()}"
        if key_rev in self.friction_matrix:
            return self.friction_matrix[key_rev]
        return {'chaos_potential': 50, 'style_clash': 50, 'predicted_goals': 2.5}
    
    def load_all_matches(self) -> List[Dict]:
        """Charge tous les matchs avec les deux équipes dans notre DNA"""
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            cur.execute("""
                SELECT DISTINCT ON (DATE(match_date), home_team, away_team)
                    match_date, home_team, away_team, home_goals, away_goals, league
                FROM matches_results
                WHERE home_goals IS NOT NULL
                ORDER BY DATE(match_date), home_team, away_team, match_date DESC
            """)
            
            matches = []
            for row in cur.fetchall():
                home_lower = row['home_team'].lower()
                away_lower = row['away_team'].lower()
                
                # Garder seulement si les deux équipes ont un DNA
                if home_lower in self.team_dna and away_lower in self.team_dna:
                    matches.append({
                        'date': row['match_date'],
                        'home_team': row['home_team'],
                        'away_team': row['away_team'],
                        'home_goals': row['home_goals'] or 0,
                        'away_goals': row['away_goals'] or 0,
                        'league': row['league'],
                    })
            
            # Trier par date ASC pour le calcul de momentum
            matches.sort(key=lambda x: x['date'])
            return matches
        finally:
            cur.close()
    
    def get_team_previous_matches(self, all_matches: List[Dict], team: str, 
                                   before_date: datetime, limit: int = 5) -> List[Dict]:
        """Récupère les matchs précédents d'une équipe"""
        team_lower = team.lower()
        previous = []
        
        for match in reversed(all_matches):
            if match['date'] >= before_date:
                continue
            
            home_lower = match['home_team'].lower()
            away_lower = match['away_team'].lower()
            
            if home_lower == team_lower or away_lower == team_lower:
                previous.append(match)
                if len(previous) >= limit:
                    break
        
        return previous
    
    def evaluate_bet(self, match: Dict, market: str = 'over_25') -> Tuple[bool, float]:
        """Évalue un pari Over 2.5"""
        total = match['home_goals'] + match['away_goals']
        odds = AVG_ODDS.get(market, 1.85)
        
        is_winner = total > 2.5
        profit = (odds - 1) if is_winner else -1.0
        
        return is_winner, profit
    
    def run_backtest(self):
        """Lance le backtest hybride"""
        print()
        print("=" * 100)
        print("🧬 BACKTEST HYBRIDE: CONVERGENCE + MOMENTUM L5")
        print("=" * 100)
        print()
        
        self.load_team_dna()
        self.load_friction_matrix()
        
        all_matches = self.load_all_matches()
        print(f"📊 {len(all_matches)} matchs chargés")
        print()
        
        # Pour chaque match, vérifier CONVERGENCE puis appliquer les filtres Momentum
        processed = 0
        convergence_qualified = 0
        
        for i, match in enumerate(all_matches):
            if i < 10:  # Skip les 10 premiers pour avoir du momentum
                continue
            
            home = match['home_team']
            away = match['away_team']
            home_lower = home.lower()
            away_lower = away.lower()
            
            home_dna = self.team_dna.get(home_lower, {})
            away_dna = self.team_dna.get(away_lower, {})
            friction = self.get_friction(home, away)
            
            # Vérifier CONVERGENCE
            qualifies, confidence = check_convergence_over(home_dna, away_dna, friction)
            
            if not qualifies or confidence < 65:
                continue
            
            convergence_qualified += 1
            
            # Calculer Momentum pour les deux équipes
            home_prev = self.get_team_previous_matches(all_matches, home, match['date'], 5)
            away_prev = self.get_team_previous_matches(all_matches, away, match['date'], 5)
            
            home_momentum = calculate_momentum_l5(home_prev, home)
            away_momentum = calculate_momentum_l5(away_prev, away)
            
            # Évaluer le pari
            is_winner, profit = self.evaluate_bet(match)
            
            # Enregistrer le pari
            bet = BetRecord(
                match_date=match['date'],
                home_team=home,
                away_team=away,
                team_perspective="match",
                market="over_25",
                odds=AVG_ODDS['over_25'],
                confidence=confidence,
                momentum_score=max(home_momentum.score, away_momentum.score),
                momentum_trend=home_momentum.trend if home_momentum.score > away_momentum.score else away_momentum.trend,
                is_winner=is_winner,
                profit=profit
            )
            self.all_bets.append(bet)
            
            # Mettre à jour TOUTES les variantes
            best_momentum = home_momentum if home_momentum.score > away_momentum.score else away_momentum
            
            # 1. BASELINE (tous les paris CONVERGENCE)
            self._update_stats("CONVERGENCE_BASELINE", is_winner, profit)
            
            # 2. Momentum HOT+ (BLAZING ou HOT)
            if best_momentum.is_hot:
                self._update_stats("CONV_MOMENTUM_HOT", is_winner, profit)
            
            # 3. Momentum WARMING+ (BLAZING, HOT, ou WARMING)
            if best_momentum.is_warming_plus:
                self._update_stats("CONV_MOMENTUM_WARMING", is_winner, profit)
            
            # 4. Momentum Score > 60
            if best_momentum.score > 60:
                self._update_stats("CONV_MOMENTUM_60", is_winner, profit)
            
            # 5. Momentum Score > 50
            if best_momentum.score > 50:
                self._update_stats("CONV_MOMENTUM_50", is_winner, profit)
            
            # 6. Exclure COLD/FREEZING (les deux équipes)
            if not home_momentum.is_cold and not away_momentum.is_cold:
                self._update_stats("CONV_NO_COLD", is_winner, profit)
            
            # 7. Acceleration positive
            if best_momentum.acceleration > 0:
                self._update_stats("CONV_ACCELERATION_POS", is_winner, profit)
            
            processed += 1
            if processed % 100 == 0:
                print(f"\r⏳ {processed} matchs traités...", end="", flush=True)
        
        print(f"\n\n✅ Backtest terminé: {convergence_qualified} matchs CONVERGENCE qualifiés")
    
    def _update_stats(self, variant_key: str, is_winner: bool, profit: float):
        """Met à jour les stats d'une variante"""
        stats = self.variants[variant_key]
        stats.bets += 1
        stats.profit += profit
        if is_winner:
            stats.wins += 1
    
    def print_report(self):
        """Affiche le rapport comparatif"""
        print()
        print("=" * 120)
        print("🏆 RAPPORT COMPARATIF: CONVERGENCE vs CONVERGENCE + MOMENTUM")
        print("=" * 120)
        print()
        
        # Calculer le seuil de rentabilité
        odds = AVG_ODDS['over_25']
        breakeven = 100 / odds
        
        print(f"📊 Marché: Over 2.5 | Cote moyenne: {odds} | Seuil rentabilité: {breakeven:.1f}%")
        print()
        
        print(f"{'Variante':<35} {'Bets':>7} {'Wins':>7} {'WR':>8} {'P&L':>10} {'ROI':>8} {'vs Base':>10}")
        print("-" * 95)
        
        baseline = self.variants["CONVERGENCE_BASELINE"]
        baseline_roi = baseline.roi
        
        # Trier par ROI
        sorted_variants = sorted(self.variants.items(), key=lambda x: x[1].roi, reverse=True)
        
        for key, stats in sorted_variants:
            if stats.bets == 0:
                continue
            
            delta_roi = stats.roi - baseline_roi if key != "CONVERGENCE_BASELINE" else 0
            delta_str = f"{delta_roi:+.1f}%" if delta_roi != 0 else "-"
            
            # Indicateur
            if stats.win_rate >= 60:
                icon = "🏆"
            elif stats.win_rate >= 55:
                icon = "✅"
            elif stats.win_rate >= breakeven:
                icon = "📈"
            else:
                icon = "❌"
            
            print(f"{icon} {stats.name:<33} {stats.bets:>7} {stats.wins:>7} "
                  f"{stats.win_rate:>7.1f}% {stats.profit:>+9.1f}u {stats.roi:>+7.1f}% {delta_str:>10}")
        
        print()
        print("=" * 120)
        print("📈 ANALYSE")
        print("=" * 120)
        print()
        
        # Trouver la meilleure variante
        best_variant = max(self.variants.items(), key=lambda x: x[1].roi if x[1].bets > 10 else -999)
        best_wr_variant = max(self.variants.items(), key=lambda x: x[1].win_rate if x[1].bets > 10 else -999)
        
        print(f"🎯 MEILLEUR ROI: {best_variant[1].name}")
        print(f"   • {best_variant[1].bets} bets | {best_variant[1].win_rate:.1f}% WR | {best_variant[1].profit:+.1f}u | {best_variant[1].roi:+.1f}% ROI")
        print()
        print(f"🎯 MEILLEUR WR: {best_wr_variant[1].name}")
        print(f"   • {best_wr_variant[1].bets} bets | {best_wr_variant[1].win_rate:.1f}% WR | {best_wr_variant[1].profit:+.1f}u")
        print()
        
        # Conclusion
        print("=" * 120)
        print("🧠 CONCLUSION")
        print("=" * 120)
        print()
        
        baseline_stats = self.variants["CONVERGENCE_BASELINE"]
        
        improvements = []
        for key, stats in self.variants.items():
            if key == "CONVERGENCE_BASELINE" or stats.bets < 10:
                continue
            if stats.roi > baseline_stats.roi:
                improvements.append((key, stats))
        
        if improvements:
            print("✅ Variantes qui AMÉLIORENT la baseline:")
            for key, stats in sorted(improvements, key=lambda x: x[1].roi, reverse=True):
                delta = stats.roi - baseline_stats.roi
                print(f"   • {stats.name}: +{delta:.1f}% ROI (de {baseline_stats.roi:+.1f}% à {stats.roi:+.1f}%)")
        else:
            print("❌ Aucune variante n'améliore significativement la baseline")
        
        print()
        
        # Stats par trend
        print("=" * 120)
        print("📊 BREAKDOWN PAR MOMENTUM TREND")
        print("=" * 120)
        print()
        
        trend_stats = {}
        for bet in self.all_bets:
            trend = bet.momentum_trend
            if trend not in trend_stats:
                trend_stats[trend] = {"bets": 0, "wins": 0, "profit": 0}
            trend_stats[trend]["bets"] += 1
            trend_stats[trend]["profit"] += bet.profit
            if bet.is_winner:
                trend_stats[trend]["wins"] += 1
        
        print(f"{'Momentum Trend':<15} {'Bets':>7} {'Wins':>7} {'WR':>8} {'P&L':>10} {'ROI':>8}")
        print("-" * 60)
        
        for trend, data in sorted(trend_stats.items(), key=lambda x: x[1]["profit"], reverse=True):
            wr = (data["wins"] / data["bets"] * 100) if data["bets"] > 0 else 0
            roi = (data["profit"] / data["bets"] * 100) if data["bets"] > 0 else 0
            print(f"{trend:<15} {data['bets']:>7} {data['wins']:>7} {wr:>7.1f}% {data['profit']:>+9.1f}u {roi:>+7.1f}%")
        
        print()
    
    def export_results(self, filepath: str):
        """Exporte les résultats en JSON"""
        results = {
            "generated_at": datetime.now().isoformat(),
            "market": "over_25",
            "odds": AVG_ODDS['over_25'],
            "variants": {},
            "trend_breakdown": {},
        }
        
        for key, stats in self.variants.items():
            results["variants"][key] = {
                "name": stats.name,
                "bets": stats.bets,
                "wins": stats.wins,
                "win_rate": round(stats.win_rate, 2),
                "profit": round(stats.profit, 2),
                "roi": round(stats.roi, 2),
            }
        
        # Trend breakdown
        trend_stats = {}
        for bet in self.all_bets:
            trend = bet.momentum_trend
            if trend not in trend_stats:
                trend_stats[trend] = {"bets": 0, "wins": 0, "profit": 0}
            trend_stats[trend]["bets"] += 1
            trend_stats[trend]["profit"] += bet.profit
            if bet.is_winner:
                trend_stats[trend]["wins"] += 1
        
        results["trend_breakdown"] = trend_stats
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"✅ Résultats exportés: {filepath}")


# ═══════════════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════════════

def main():
    print()
    print("╔═══════════════════════════════════════════════════════════════════════════════════════╗")
    print("║     BACKTEST HYBRIDE: CONVERGENCE_OVER_MC + MOMENTUM L5                              ║")
    print("║                                                                                       ║")
    print("║     Hypothèse: Le Momentum L5 peut améliorer le ROI de CONVERGENCE                   ║")
    print("║     en filtrant les paris quand l'équipe est en mauvaise forme                       ║")
    print("╚═══════════════════════════════════════════════════════════════════════════════════════╝")
    print()
    
    backtester = HybridBacktester()
    
    try:
        backtester.connect()
        backtester.run_backtest()
        backtester.print_report()
        
        # Export
        export_path = "/home/Mon_ps/exports/hybrid_convergence_momentum.json"
        backtester.export_results(export_path)
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
    finally:
        backtester.close()


if __name__ == "__main__":
    main()
