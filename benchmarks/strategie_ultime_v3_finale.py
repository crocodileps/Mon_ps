#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║     🏆 STRATÉGIE ULTIME V3 - VERSION FINALE OPTIMISÉE                         ║
║                                                                               ║
║  DÉCOUVERTES INTÉGRÉES:                                                       ║
║  • MC pour ELITE/GOLD/QUANT/CHAOS (améliore qualité)                         ║
║  • CONVERGENCE SANS MC (le signal est déjà parfait)                          ║
║  • CONVERGENCE_UNDER avec filtre xG <= 2.3                                   ║
║                                                                               ║
║  Objectif: Maximiser P&L tout en gardant ROI > 45%                           ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import math
import random
from datetime import datetime
from typing import Dict, Optional, Tuple
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

# Équipes ELITE (100% WR historique sur CONVERGENCE)
CONVERGENCE_ELITE = ['Marseille', 'Brighton', 'Augsburg', 'Inter', 'Manchester City']

# Équipes GOLD (85%+ WR sur CONVERGENCE)
CONVERGENCE_GOLD = ['Newcastle United', 'Nice', 'Fulham', 'Bournemouth', 'Manchester United',
                    'Leeds', 'Barcelona', 'Brentford', 'Aston Villa', 'Sevilla']

# Équipes QUANT (meilleur ROI avec best_market spécifique)
QUANT_SPECIALISTS = ['Lazio', 'Athletic Club', 'Real Sociedad', 'Angers', 'Rayo Vallecano', 'Paris FC']

# Équipes CHAOS (performantes sur TOTAL_CHAOS)
CHAOS_SPECIALISTS = ['Brest', 'Monaco', 'Hoffenheim', 'Metz', 'Villarreal', 'Valencia']

# BLACKLIST (toutes stratégies négatives)
BLACKLIST = ['Bologna', 'Mainz 05', 'Borussia Dortmund', 'Hamburger SV']


@dataclass
class Decision:
    team: str
    market: str
    stake: float
    category: str
    expected_goals: float
    mc_prob: float
    reason: str


class StrategieUltimeV3:
    """Stratégie Ultime V3 - Version Finale Optimisée"""
    
    def __init__(self):
        self.conn = None
        self.team_data = {}
        self.matches = []
        self.results = {
            'ALL': {'bets': 0, 'wins': 0, 'profit': 0, 'stake': 0},
            'ELITE_MC': {'bets': 0, 'wins': 0, 'profit': 0},
            'GOLD_MC': {'bets': 0, 'wins': 0, 'profit': 0},
            'QUANT_MC': {'bets': 0, 'wins': 0, 'profit': 0},
            'CHAOS_MC': {'bets': 0, 'wins': 0, 'profit': 0},
            'CONVERGENCE_PURE': {'bets': 0, 'wins': 0, 'profit': 0},
            'CONVERGENCE_UNDER': {'bets': 0, 'wins': 0, 'profit': 0},
        }
        self.team_stats = defaultdict(lambda: {'bets': 0, 'wins': 0, 'profit': 0, 'cat': ''})
        
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
        
    def is_in_list(self, team_name: str, team_list: list) -> bool:
        for t in team_list:
            if t.lower() in team_name.lower() or team_name.lower() in t.lower():
                return True
        return False
        
    def poisson_random(self, lam: float) -> int:
        """Algorithme Knuth pour vraie distribution Poisson"""
        if lam <= 0:
            return 0
        L = math.exp(-lam)
        k = 0
        p = 1.0
        while p > L:
            k += 1
            p *= random.random()
        return k - 1
        
    def monte_carlo_simulate(self, home_data: Dict, away_data: Dict, n_sims: int = 3000) -> Dict:
        """Simulation Monte Carlo avec vraie Poisson"""
        HOME_ADVANTAGE = 1.12
        lambda_h = math.sqrt(home_data['xg_for'] * away_data['xg_against']) * HOME_ADVANTAGE
        lambda_a = math.sqrt(away_data['xg_for'] * home_data['xg_against'])
        
        over_25 = 0
        over_35 = 0
        btts_yes = 0
        total_goals = []
        
        for _ in range(n_sims):
            home_goals = self.poisson_random(lambda_h)
            away_goals = self.poisson_random(lambda_a)
            total = home_goals + away_goals
            total_goals.append(total)
            
            if total >= 3:
                over_25 += 1
            if total >= 4:
                over_35 += 1
            if home_goals > 0 and away_goals > 0:
                btts_yes += 1
                
        return {
            'over_25_prob': over_25 / n_sims,
            'over_35_prob': over_35 / n_sims,
            'under_25_prob': (n_sims - over_25) / n_sims,
            'btts_yes_prob': btts_yes / n_sims,
            'expected_goals': sum(total_goals) / n_sims
        }
        
    def calculate_expected_goals(self, home_data: Dict, away_data: Dict) -> float:
        """Calcul xG attendu avec avantage domicile"""
        HOME_ADVANTAGE = 1.12
        lambda_h = math.sqrt(home_data['xg_for'] * away_data['xg_against']) * HOME_ADVANTAGE
        lambda_a = math.sqrt(away_data['xg_for'] * home_data['xg_against'])
        return lambda_h + lambda_a
        
    def get_decision(self, home_name: str, away_name: str) -> Optional[Decision]:
        """Décision hybride: MC pour specialists, CONVERGENCE pure pour standard"""
        home_key, home_data = self.find_team(home_name)
        away_key, away_data = self.find_team(away_name)
        
        if not home_data or not away_data:
            return None
            
        # Blacklist check
        if self.is_in_list(home_name, BLACKLIST) or self.is_in_list(away_name, BLACKLIST):
            return None
            
        # Convergence check
        home_tendency = home_data['tendency']
        away_tendency = away_data['tendency']
        convergence_over = home_tendency == "OVER" and away_tendency == "OVER"
        convergence_under = home_tendency == "UNDER" and away_tendency == "UNDER"
        style_clash = (home_tendency == "OVER" and away_tendency == "UNDER") or \
                     (home_tendency == "UNDER" and away_tendency == "OVER")
                     
        # Skip style clash (signal contradictoire)
        if style_clash:
            return None
            
        expected_goals = self.calculate_expected_goals(home_data, away_data)
        
        # Monte Carlo pour les specialists
        mc = self.monte_carlo_simulate(home_data, away_data)
        
        # ═══════════════════════════════════════════════════════════════════════
        # RÈGLE 1: ELITE + CONVERGENCE + MC >= 55%
        # Stake: 4.0u (maximum confiance)
        # ═══════════════════════════════════════════════════════════════════════
        home_elite = self.is_in_list(home_name, CONVERGENCE_ELITE)
        away_elite = self.is_in_list(away_name, CONVERGENCE_ELITE)
        
        if (home_elite or away_elite) and convergence_over and mc['over_25_prob'] >= 0.55:
            team = home_name if home_elite else away_name
            return Decision(
                team=team, market='over_25', stake=4.0, category='ELITE_MC',
                expected_goals=expected_goals, mc_prob=mc['over_25_prob'],
                reason=f"ELITE {team} + CONVERGENCE + MC {mc['over_25_prob']*100:.0f}%"
            )
            
        # ═══════════════════════════════════════════════════════════════════════
        # RÈGLE 2: GOLD + CONVERGENCE + MC >= 55%
        # Stake: 3.0u
        # ═══════════════════════════════════════════════════════════════════════
        home_gold = self.is_in_list(home_name, CONVERGENCE_GOLD)
        away_gold = self.is_in_list(away_name, CONVERGENCE_GOLD)
        
        if (home_gold or away_gold) and convergence_over and mc['over_25_prob'] >= 0.55:
            team = home_name if home_gold else away_name
            return Decision(
                team=team, market='over_25', stake=3.0, category='GOLD_MC',
                expected_goals=expected_goals, mc_prob=mc['over_25_prob'],
                reason=f"GOLD {team} + CONVERGENCE + MC {mc['over_25_prob']*100:.0f}%"
            )
            
        # ═══════════════════════════════════════════════════════════════════════
        # RÈGLE 3: QUANT_SPECIALIST + MC confirme leur best_market
        # Stake: 2.5u
        # ═══════════════════════════════════════════════════════════════════════
        for team_name in [home_name, away_name]:
            if self.is_in_list(team_name, QUANT_SPECIALISTS):
                team_key, team_data = self.find_team(team_name)
                if not team_key or team_data['best_roi'] < 30:
                    continue
                    
                best_market = team_data['best_market']
                mc_confirms = False
                
                if best_market == 'over_25' and mc['over_25_prob'] >= 0.55:
                    mc_confirms = True
                elif best_market == 'under_25' and mc['under_25_prob'] >= 0.50:
                    mc_confirms = True
                elif best_market == 'btts_no' and mc['btts_yes_prob'] <= 0.50:
                    mc_confirms = True
                elif best_market == 'btts_yes' and mc['btts_yes_prob'] >= 0.55:
                    mc_confirms = True
                    
                if mc_confirms and best_market in MARKET_ODDS:
                    return Decision(
                        team=team_name, market=best_market, stake=2.5, category='QUANT_MC',
                        expected_goals=expected_goals, mc_prob=mc['over_25_prob'],
                        reason=f"QUANT {team_name} → {best_market} + MC confirme"
                    )
                    
        # ═══════════════════════════════════════════════════════════════════════
        # RÈGLE 4: CHAOS_SPECIALIST + MC >= 60%
        # Stake: 2.5u
        # ═══════════════════════════════════════════════════════════════════════
        home_chaos = self.is_in_list(home_name, CHAOS_SPECIALISTS)
        away_chaos = self.is_in_list(away_name, CHAOS_SPECIALISTS)
        
        if (home_chaos or away_chaos) and mc['over_25_prob'] >= 0.60:
            team = home_name if home_chaos else away_name
            market = 'over_35' if mc['over_35_prob'] >= 0.45 else 'over_25'
            return Decision(
                team=team, market=market, stake=2.5, category='CHAOS_MC',
                expected_goals=expected_goals, mc_prob=mc['over_25_prob'],
                reason=f"CHAOS {team} + MC {mc['over_25_prob']*100:.0f}%"
            )
            
        # ═══════════════════════════════════════════════════════════════════════
        # RÈGLE 5: CONVERGENCE_OVER PURE (SANS MC!) - xG >= 2.5 suffit
        # Stake: 2.0u
        # C'est ici qu'on récupère les 80 matchs perdus dans V2!
        # ═══════════════════════════════════════════════════════════════════════
        if convergence_over and expected_goals >= 2.5:
            return Decision(
                team=f"{home_name} vs {away_name}",
                market='over_25', stake=2.0, category='CONVERGENCE_PURE',
                expected_goals=expected_goals, mc_prob=mc['over_25_prob'],
                reason=f"CONVERGENCE_OVER PURE (xG: {expected_goals:.2f})"
            )
            
        # ═══════════════════════════════════════════════════════════════════════
        # RÈGLE 6: CONVERGENCE_UNDER avec filtre xG <= 2.3
        # Stake: 2.0u
        # ═══════════════════════════════════════════════════════════════════════
        if convergence_under and expected_goals <= 2.3:
            return Decision(
                team=f"{home_name} vs {away_name}",
                market='under_25', stake=2.0, category='CONVERGENCE_UNDER',
                expected_goals=expected_goals, mc_prob=mc['under_25_prob'],
                reason=f"CONVERGENCE_UNDER (xG: {expected_goals:.2f})"
            )
            
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
        
    def run_backtest(self):
        print("\n" + "="*100)
        print("🏆 BACKTEST STRATÉGIE ULTIME V3 FINALE")
        print("="*100)
        
        for match in self.matches:
            decision = self.get_decision(match['home_team'], match['away_team'])
            
            if not decision:
                continue
                
            market = decision.market
            stake = decision.stake
            category = decision.category
            
            if market not in MARKET_ODDS:
                continue
                
            odds = MARKET_ODDS[market]
            won = self.evaluate_market(match, market)
            profit = stake * (odds - 1) if won else -stake
            
            # Global
            self.results['ALL']['bets'] += 1
            self.results['ALL']['wins'] += 1 if won else 0
            self.results['ALL']['profit'] += profit
            self.results['ALL']['stake'] += stake
            
            # Par catégorie
            if category in self.results:
                self.results[category]['bets'] += 1
                self.results[category]['wins'] += 1 if won else 0
                self.results[category]['profit'] += profit
                
            # Par équipe
            self.team_stats[decision.team]['bets'] += 1
            self.team_stats[decision.team]['wins'] += 1 if won else 0
            self.team_stats[decision.team]['profit'] += profit
            self.team_stats[decision.team]['cat'] = category
            
        print(f"✅ {self.results['ALL']['bets']} paris exécutés")
        
    def print_results(self):
        print("\n" + "="*100)
        print("📊 RÉSULTATS STRATÉGIE ULTIME V3 FINALE")
        print("="*100)
        
        all_r = self.results['ALL']
        if all_r['bets'] > 0:
            wr = (all_r['wins'] / all_r['bets']) * 100
            roi = (all_r['profit'] / all_r['stake']) * 100
            
            print(f"\n🏆 PERFORMANCE GLOBALE V3:")
            print(f"   Paris: {all_r['bets']}")
            print(f"   Wins: {all_r['wins']}")
            print(f"   Win Rate: {wr:.1f}%")
            print(f"   ROI: {roi:+.1f}%")
            print(f"   P&L: {all_r['profit']:+.1f}u")
            
        # Par catégorie
        print(f"\n{'='*100}")
        print("📈 PERFORMANCE PAR CATÉGORIE:")
        print(f"{'='*100}")
        print(f"\n{'Catégorie':<22} {'Paris':<10} {'Wins':<10} {'WR':<12} {'P&L':<12}")
        print("-"*70)
        
        for cat in ['ELITE_MC', 'GOLD_MC', 'QUANT_MC', 'CHAOS_MC', 'CONVERGENCE_PURE', 'CONVERGENCE_UNDER']:
            r = self.results[cat]
            if r['bets'] > 0:
                wr = (r['wins'] / r['bets']) * 100
                emoji = "💎" if r['profit'] > 40 else "✅" if r['profit'] > 0 else "❌"
                print(f"{emoji} {cat:<20} {r['bets']:<10} {r['wins']:<10} {wr:.1f}%{'':<7} {r['profit']:+.1f}u")
                
        # Top équipes
        print(f"\n{'='*100}")
        print("🎯 TOP 25 ÉQUIPES:")
        print(f"{'='*100}")
        
        team_list = []
        for team, data in self.team_stats.items():
            if data['bets'] >= 2:
                team_wr = (data['wins'] / data['bets']) * 100
                team_list.append({
                    'team': team,
                    'bets': data['bets'],
                    'wr': team_wr,
                    'profit': data['profit'],
                    'cat': data['cat']
                })
                
        team_list.sort(key=lambda x: x['profit'], reverse=True)
        
        print(f"\n{'#':<3} {'Équipe':<40} {'Cat':<18} {'Paris':<8} {'WR':<10} {'P&L':<10}")
        print("-"*95)
        
        for i, t in enumerate(team_list[:25], 1):
            emoji = "💎" if t['profit'] >= 15 else "✅" if t['profit'] > 0 else "❌"
            print(f"{emoji}{i:<2} {t['team'][:39]:<40} {t['cat'][:17]:<18} {t['bets']:<8} {t['wr']:.1f}%{'':<5} {t['profit']:+.1f}u")
            
        # Comparaison finale
        print(f"\n{'='*100}")
        print("🏆 COMPARAISON FINALE - TOUTES STRATÉGIES:")
        print(f"{'='*100}")
        
        all_r = self.results['ALL']
        if all_r['bets'] > 0:
            wr = (all_r['wins'] / all_r['bets']) * 100
            roi = (all_r['profit'] / all_r['stake']) * 100
            
            print(f"\n{'Stratégie':<30} {'Paris':<10} {'WR':<12} {'ROI':<14} {'P&L':<12}")
            print("-"*80)
            print(f"{'🏆 STRATÉGIE ULTIME V3':<30} {all_r['bets']:<10} {wr:.1f}%{'':<7} {roi:+.1f}%{'':<8} {all_r['profit']:+.1f}u")
            print(f"{'STRATÉGIE ULTIME V2':<30} {'164':<10} {'75.0%':<12} {'+47.7%':<14} {'+224.0u':<12}")
            print(f"{'STRATÉGIE ULTIME V1':<30} {'244':<10} {'76.6%':<12} {'+50.0%':<14} {'+337.1u':<12}")
            print(f"{'CONVERGENCE_OVER (audit)':<30} {'366':<10} {'73.8%':<12} {'+36.5%':<14} {'+400.5u':<12}")
            print(f"{'Adaptive Engine':<30} {'351':<10} {'69.8%':<12} {'+48.3%':<14} {'+372.8u':<12}")
            print(f"{'V13 Reference':<30} {'204':<10} {'76.5%':<12} {'+53.2%':<14} {'+210.7u':<12}")
            
        # Save results
        with open('strategie_ultime_v3_results.json', 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'global': {k: round(v, 1) if isinstance(v, float) else v for k, v in all_r.items()},
                'by_category': {k: {kk: round(vv, 1) if isinstance(vv, float) else vv for kk, vv in v.items()} 
                               for k, v in self.results.items() if k != 'ALL'}
            }, f, indent=2)
            
        print("\n✅ Résultats sauvegardés dans strategie_ultime_v3_results.json")


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║     🏆 STRATÉGIE ULTIME V3 - VERSION FINALE OPTIMISÉE                         ║
║                                                                               ║
║  CORRECTIONS V2 → V3:                                                         ║
║  • CONVERGENCE_PURE sans MC (récupère les 80 matchs perdus)                  ║
║  • MC seulement pour ELITE/GOLD/QUANT/CHAOS                                  ║
║  • Seuils MC abaissés à 55% (vs 58-60% dans V2)                              ║
║                                                                               ║
║  Objectif: P&L > 350u avec ROI > 45%                                         ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    strategy = StrategieUltimeV3()
    strategy.connect()
    strategy.load_data()
    strategy.run_backtest()
    strategy.print_results()


if __name__ == "__main__":
    main()

