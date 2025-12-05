#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║     🎲 MONTE CARLO V2 - SIMULATION CORRIGÉE + ÉVALUATION PRÉCISE              ║
║                                                                               ║
║  CORRECTIONS:                                                                 ║
║  • Vraie simulation Poisson (algorithme Knuth)                                ║
║  • Évaluation pertes basée sur probabilités MC (pas xG)                       ║
║  • Filtres CONVERGENCE intégrés                                               ║
║  • Seuils de confiance calibrés                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import math
import random
from datetime import datetime
from typing import Dict, Optional, Tuple, List
from collections import defaultdict
from dataclasses import dataclass
import json

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

MARKET_ODDS = {
    'over_25': 1.85, 'over_35': 2.40, 'over_15': 1.30,
    'under_25': 2.00, 'under_35': 1.55,
    'btts_yes': 1.80, 'btts_no': 2.00,
}

OVER_MARKETS = ['over_25', 'over_35', 'over_15', 'btts_yes', 'team_over_15']
UNDER_MARKETS = ['under_25', 'under_35', 'under_15', 'btts_no']


@dataclass
class MCResult:
    """Résultat de simulation Monte Carlo"""
    over_15_prob: float
    over_25_prob: float
    over_35_prob: float
    under_25_prob: float
    under_35_prob: float
    btts_yes_prob: float
    btts_no_prob: float
    expected_goals: float
    goals_std: float  # Écart-type
    simulations: int


@dataclass 
class BetDecision:
    team: str
    market: str
    stake: float
    mc_probability: float  # Probabilité MC du marché
    expected_goals: float
    convergence_type: str  # OVER, UNDER, NONE
    confidence: str  # HIGH, MEDIUM, LOW
    reason: str


class MonteCarloV2:
    """Monte Carlo V2 avec simulation Poisson correcte"""
    
    def __init__(self):
        self.conn = None
        self.team_data = {}
        self.matches = []
        self.results = {
            'ALL': {'bets': 0, 'wins': 0, 'profit': 0, 'stake': 0},
            'MC_CONVERGENCE_HIGH': {'bets': 0, 'wins': 0, 'profit': 0, 'unlucky': 0, 'bad': 0},
            'MC_CONVERGENCE_MED': {'bets': 0, 'wins': 0, 'profit': 0, 'unlucky': 0, 'bad': 0},
            'MC_PURE_HIGH': {'bets': 0, 'wins': 0, 'profit': 0, 'unlucky': 0, 'bad': 0},
            'MC_PURE_MED': {'bets': 0, 'wins': 0, 'profit': 0, 'unlucky': 0, 'bad': 0},
        }
        self.team_stats = defaultdict(lambda: {'bets': 0, 'wins': 0, 'profit': 0})
        
    def connect(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connexion DB établie")
        
    def load_data(self):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM team_xg_tendencies")
            xg_data = {r['team_name']: r for r in cur.fetchall()}
            
            cur.execute("SELECT * FROM team_big_chances_tendencies")
            bc_data = {r['team_name']: r for r in cur.fetchall()}
            
            cur.execute("""
                SELECT team_name, market_type, roi, win_rate, is_best_market
                FROM team_market_profiles WHERE sample_size >= 5
            """)
            mkt_data = {}
            for r in cur.fetchall():
                team = r['team_name']
                if team not in mkt_data:
                    mkt_data[team] = {}
                mkt_data[team][r['market_type']] = {
                    'roi': float(r['roi'] or 0),
                    'wr': float(r['win_rate'] or 0),
                    'is_best': r['is_best_market']
                }
                
            for team in set(xg_data.keys()) | set(bc_data.keys()):
                xg = xg_data.get(team, {})
                bc = bc_data.get(team, {})
                markets = mkt_data.get(team, {})
                
                best_market = 'over_25'
                best_roi = 0
                for mkt, data in markets.items():
                    if data.get('is_best') and data['roi'] > best_roi:
                        best_market = mkt
                        best_roi = data['roi']
                        
                tendency = "OVER" if best_market in OVER_MARKETS else "UNDER" if best_market in UNDER_MARKETS else "NEUTRAL"
                
                self.team_data[team] = {
                    'xg_for': float(xg.get('avg_xg_for') or 1.3),
                    'xg_against': float(xg.get('avg_xg_against') or 1.3),
                    'bc_created': float(bc.get('avg_bc_created') or 1.5),
                    'bc_conceded': float(bc.get('avg_bc_conceded') or 1.5),
                    'best_market': best_market,
                    'best_roi': best_roi,
                    'tendency': tendency,
                    'markets': markets
                }
                
            cur.execute("""
                SELECT match_id, home_team, away_team, score_home, score_away
                FROM match_results 
                WHERE commence_time >= '2025-09-01' AND is_finished = true
            """)
            self.matches = cur.fetchall()
            
        print(f"✅ {len(self.team_data)} équipes, {len(self.matches)} matchs")
        
    def find_team(self, name: str) -> Tuple[Optional[str], Optional[Dict]]:
        for t in self.team_data:
            if t.lower() in name.lower() or name.lower() in t.lower():
                return t, self.team_data[t]
        return None, None
        
    def poisson_random(self, lam: float) -> int:
        """
        Génère un nombre aléatoire selon distribution Poisson
        Algorithme de Knuth (correct!)
        """
        if lam <= 0:
            return 0
        L = math.exp(-lam)
        k = 0
        p = 1.0
        while p > L:
            k += 1
            p *= random.random()
        return k - 1
        
    def monte_carlo_simulate(self, home_data: Dict, away_data: Dict, 
                            n_sims: int = 5000) -> MCResult:
        """
        Simulation Monte Carlo CORRECTE avec vraie distribution Poisson
        """
        # Calcul des lambdas (Dixon-Coles simplifié)
        HOME_ADVANTAGE = 1.12
        
        lambda_h = math.sqrt(home_data['xg_for'] * away_data['xg_against']) * HOME_ADVANTAGE
        lambda_a = math.sqrt(away_data['xg_for'] * home_data['xg_against'])
        
        # Compteurs
        over_15 = 0
        over_25 = 0
        over_35 = 0
        btts_yes = 0
        total_goals = []
        
        for _ in range(n_sims):
            # Simulation Poisson CORRECTE
            home_goals = self.poisson_random(lambda_h)
            away_goals = self.poisson_random(lambda_a)
            
            total = home_goals + away_goals
            total_goals.append(total)
            
            if total >= 2:
                over_15 += 1
            if total >= 3:
                over_25 += 1
            if total >= 4:
                over_35 += 1
            if home_goals > 0 and away_goals > 0:
                btts_yes += 1
                
        # Calcul statistiques
        avg_goals = sum(total_goals) / n_sims
        variance = sum((g - avg_goals) ** 2 for g in total_goals) / n_sims
        std_goals = math.sqrt(variance)
        
        return MCResult(
            over_15_prob=over_15 / n_sims,
            over_25_prob=over_25 / n_sims,
            over_35_prob=over_35 / n_sims,
            under_25_prob=(n_sims - over_25) / n_sims,
            under_35_prob=(n_sims - over_35) / n_sims,
            btts_yes_prob=btts_yes / n_sims,
            btts_no_prob=(n_sims - btts_yes) / n_sims,
            expected_goals=avg_goals,
            goals_std=std_goals,
            simulations=n_sims
        )
        
    def get_decision(self, home_name: str, away_name: str) -> Optional[BetDecision]:
        """
        Décision basée sur Monte Carlo + Convergence
        """
        home_key, home_data = self.find_team(home_name)
        away_key, away_data = self.find_team(away_name)
        
        if not home_data or not away_data:
            return None
            
        # Convergence check
        home_tendency = home_data['tendency']
        away_tendency = away_data['tendency']
        
        convergence_over = home_tendency == "OVER" and away_tendency == "OVER"
        convergence_under = home_tendency == "UNDER" and away_tendency == "UNDER"
        convergence_type = "OVER" if convergence_over else "UNDER" if convergence_under else "NONE"
        
        # Monte Carlo simulation
        mc = self.monte_carlo_simulate(home_data, away_data, n_sims=5000)
        
        # ═══════════════════════════════════════════════════════════════════════
        # RÈGLE 1: MC + CONVERGENCE_OVER (Double signal = HIGH confidence)
        # ═══════════════════════════════════════════════════════════════════════
        if convergence_over and mc.over_25_prob >= 0.55:
            return BetDecision(
                team=f"{home_name} vs {away_name}",
                market='over_25' if mc.over_25_prob >= mc.over_35_prob * 1.3 else 'over_35',
                stake=3.0 if mc.over_25_prob >= 0.65 else 2.5,
                mc_probability=mc.over_25_prob,
                expected_goals=mc.expected_goals,
                convergence_type="OVER",
                confidence="HIGH" if mc.over_25_prob >= 0.65 else "MEDIUM",
                reason=f"MC {mc.over_25_prob*100:.1f}% + CONVERGENCE_OVER (xG: {mc.expected_goals:.2f})"
            )
            
        # ═══════════════════════════════════════════════════════════════════════
        # RÈGLE 2: MC + CONVERGENCE_UNDER (Double signal)
        # Seuil plus strict car Under est plus risqué
        # ═══════════════════════════════════════════════════════════════════════
        if convergence_under and mc.under_25_prob >= 0.50 and mc.expected_goals <= 2.5:
            return BetDecision(
                team=f"{home_name} vs {away_name}",
                market='under_25',
                stake=2.5 if mc.under_25_prob >= 0.55 else 2.0,
                mc_probability=mc.under_25_prob,
                expected_goals=mc.expected_goals,
                convergence_type="UNDER",
                confidence="HIGH" if mc.under_25_prob >= 0.55 else "MEDIUM",
                reason=f"MC {mc.under_25_prob*100:.1f}% + CONVERGENCE_UNDER (xG: {mc.expected_goals:.2f})"
            )
            
        # ═══════════════════════════════════════════════════════════════════════
        # RÈGLE 3: MC PURE avec très haute probabilité (>= 70%)
        # Seulement si PAS de clash de styles
        # ═══════════════════════════════════════════════════════════════════════
        style_clash = (home_tendency == "OVER" and away_tendency == "UNDER") or \
                     (home_tendency == "UNDER" and away_tendency == "OVER")
                     
        if not style_clash:
            if mc.over_25_prob >= 0.70:
                return BetDecision(
                    team=f"{home_name} vs {away_name}",
                    market='over_25',
                    stake=2.0,
                    mc_probability=mc.over_25_prob,
                    expected_goals=mc.expected_goals,
                    convergence_type="NONE",
                    confidence="HIGH",
                    reason=f"MC PURE {mc.over_25_prob*100:.1f}% Over (xG: {mc.expected_goals:.2f})"
                )
                
            if mc.under_25_prob >= 0.60 and mc.expected_goals <= 2.3:
                return BetDecision(
                    team=f"{home_name} vs {away_name}",
                    market='under_25',
                    stake=2.0,
                    mc_probability=mc.under_25_prob,
                    expected_goals=mc.expected_goals,
                    convergence_type="NONE",
                    confidence="MEDIUM",
                    reason=f"MC PURE {mc.under_25_prob*100:.1f}% Under (xG: {mc.expected_goals:.2f})"
                )
                
        # SKIP si pas de signal clair
        return None
        
    def evaluate_market(self, match: dict, market: str) -> bool:
        h = match['score_home'] or 0
        a = match['score_away'] or 0
        total = h + a
        both = h > 0 and a > 0
        
        return {
            'over_25': total >= 3, 'over_35': total >= 4,
            'under_25': total < 3, 'btts_yes': both, 'btts_no': not both,
        }.get(market, False)
        
    def analyze_loss(self, decision: BetDecision, won: bool) -> str:
        """
        Analyse de la perte basée sur probabilité MC
        Si MC prédit 70% et ça perd = 30% s'est réalisé = UNLUCKY
        Si MC prédit 52% et ça perd = analyse incertaine = BAD_ANALYSIS
        """
        if won:
            return ""
            
        # Si probabilité MC >= 60%, c'est de la malchance
        if decision.mc_probability >= 0.60:
            return "UNLUCKY"
        # Si probabilité MC entre 50-60%, c'est discutable
        elif decision.mc_probability >= 0.50:
            return "BORDERLINE"
        else:
            return "BAD_ANALYSIS"
            
    def run_backtest(self):
        print("\n" + "="*100)
        print("🎲 BACKTEST MONTE CARLO V2 (SIMULATION CORRIGÉE)")
        print("="*100)
        
        for match in self.matches:
            decision = self.get_decision(match['home_team'], match['away_team'])
            
            if not decision:
                continue
                
            market = decision.market
            stake = decision.stake
            
            if market not in MARKET_ODDS:
                continue
                
            odds = MARKET_ODDS[market]
            won = self.evaluate_market(match, market)
            profit = stake * (odds - 1) if won else -stake
            
            # Catégoriser
            if decision.convergence_type != "NONE":
                cat = f"MC_CONVERGENCE_{decision.confidence}"
            else:
                cat = f"MC_PURE_{decision.confidence}"
                
            # Global
            self.results['ALL']['bets'] += 1
            self.results['ALL']['wins'] += 1 if won else 0
            self.results['ALL']['profit'] += profit
            self.results['ALL']['stake'] += stake
            
            # Par catégorie
            if cat in self.results:
                self.results[cat]['bets'] += 1
                self.results[cat]['wins'] += 1 if won else 0
                self.results[cat]['profit'] += profit
                
                if not won:
                    loss_type = self.analyze_loss(decision, won)
                    if loss_type == "UNLUCKY":
                        self.results[cat]['unlucky'] += 1
                    elif loss_type == "BAD_ANALYSIS":
                        self.results[cat]['bad'] += 1
                        
            # Par équipe
            team = decision.team
            self.team_stats[team]['bets'] += 1
            self.team_stats[team]['wins'] += 1 if won else 0
            self.team_stats[team]['profit'] += profit
            
        print(f"✅ {self.results['ALL']['bets']} paris exécutés")
        
    def print_results(self):
        print("\n" + "="*100)
        print("📊 RÉSULTATS MONTE CARLO V2")
        print("="*100)
        
        all_r = self.results['ALL']
        if all_r['bets'] > 0:
            wr = (all_r['wins'] / all_r['bets']) * 100
            roi = (all_r['profit'] / all_r['stake']) * 100
            
            print(f"\n🎲 PERFORMANCE GLOBALE MC V2:")
            print(f"   Paris: {all_r['bets']}")
            print(f"   Wins: {all_r['wins']}")
            print(f"   Win Rate: {wr:.1f}%")
            print(f"   ROI: {roi:+.1f}%")
            print(f"   P&L: {all_r['profit']:+.1f}u")
            
        # Par catégorie avec analyse des pertes
        print(f"\n{'='*100}")
        print("📈 PERFORMANCE PAR CATÉGORIE + ANALYSE DES PERTES:")
        print(f"{'='*100}")
        print(f"\n{'Catégorie':<25} {'Paris':<8} {'Wins':<8} {'WR':<10} {'P&L':<12} {'Malch.':<10} {'Err.':<8}")
        print("-"*85)
        
        for cat in ['MC_CONVERGENCE_HIGH', 'MC_CONVERGENCE_MED', 'MC_PURE_HIGH', 'MC_PURE_MED']:
            r = self.results[cat]
            if r['bets'] > 0:
                wr = (r['wins'] / r['bets']) * 100
                losses = r['bets'] - r['wins']
                unlucky_pct = (r['unlucky'] / losses * 100) if losses > 0 else 0
                bad_pct = (r['bad'] / losses * 100) if losses > 0 else 0
                emoji = "💎" if r['profit'] > 50 else "✅" if r['profit'] > 0 else "❌"
                print(f"{emoji} {cat:<23} {r['bets']:<8} {r['wins']:<8} {wr:.1f}%{'':<5} {r['profit']:+.1f}u{'':<6} {unlucky_pct:.0f}%{'':<6} {bad_pct:.0f}%")
                
        # Comparaison avec MC V1
        print(f"\n{'='*100}")
        print("🔄 COMPARAISON MC V1 vs MC V2:")
        print(f"{'='*100}")
        
        all_r = self.results['ALL']
        if all_r['bets'] > 0:
            wr = (all_r['wins'] / all_r['bets']) * 100
            roi = (all_r['profit'] / all_r['stake']) * 100
            
            print(f"\n{'Version':<25} {'Paris':<10} {'WR':<12} {'ROI':<14} {'P&L':<12}")
            print("-"*75)
            print(f"{'🎲 MC V2 (corrigé)':<25} {all_r['bets']:<10} {wr:.1f}%{'':<7} {roi:+.1f}%{'':<8} {all_r['profit']:+.1f}u")
            print(f"{'❌ MC V1 (buggé)':<25} {'995':<10} {'46.8%':<12} {'-2.9%':<14} {'-62.0u':<12}")
            print(f"{'CONVERGENCE_OVER':<25} {'366':<10} {'73.8%':<12} {'+36.5%':<14} {'+400.5u':<12}")
            print(f"{'🏆 STRATÉGIE ULTIME V1':<25} {'244':<10} {'76.6%':<12} {'+50.0%':<14} {'+337.1u':<12}")
            
        # Top équipes
        print(f"\n{'='*100}")
        print("🎯 TOP 15 ÉQUIPES MC V2:")
        print(f"{'='*100}")
        
        team_list = []
        for team, data in self.team_stats.items():
            if data['bets'] >= 2:
                team_wr = (data['wins'] / data['bets']) * 100
                team_list.append({
                    'team': team,
                    'bets': data['bets'],
                    'wins': data['wins'],
                    'wr': team_wr,
                    'profit': data['profit']
                })
                
        team_list.sort(key=lambda x: x['profit'], reverse=True)
        
        print(f"\n{'#':<3} {'Match/Équipe':<45} {'Paris':<8} {'WR':<10} {'P&L':<10}")
        print("-"*80)
        
        for i, t in enumerate(team_list[:15], 1):
            emoji = "💎" if t['profit'] >= 10 else "✅" if t['profit'] > 0 else "❌"
            print(f"{emoji}{i:<2} {t['team'][:44]:<45} {t['bets']:<8} {t['wr']:.1f}%{'':<5} {t['profit']:+.1f}u")
            
        # Save
        with open('monte_carlo_v2_results.json', 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'global': {k: round(v, 1) if isinstance(v, float) else v for k, v in all_r.items()},
                'by_category': {k: {kk: round(vv, 1) if isinstance(vv, float) else vv for kk, vv in v.items()} 
                               for k, v in self.results.items() if k != 'ALL'}
            }, f, indent=2)
            
        print("\n✅ Résultats sauvegardés")


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║     🎲 MONTE CARLO V2 - SIMULATION POISSON CORRIGÉE                           ║
║                                                                               ║
║  CORRECTIONS APPLIQUÉES:                                                      ║
║  • Algorithme Knuth pour vraie distribution Poisson                           ║
║  • 5000 simulations (vs 500 avant)                                            ║
║  • Évaluation pertes basée sur probabilité MC                                 ║
║  • Filtres CONVERGENCE intégrés                                               ║
║  • SKIP des STYLE_CLASH                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    mc = MonteCarloV2()
    mc.connect()
    mc.load_data()
    mc.run_backtest()
    mc.print_results()


if __name__ == "__main__":
    main()
