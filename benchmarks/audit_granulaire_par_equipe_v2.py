#!/usr/bin/env python3
"""
AUDIT GRANULAIRE PAR ÉQUIPE V2 - CORRIGÉ
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import math
import random
from datetime import datetime
from typing import Dict, Optional, Tuple, List
from collections import defaultdict
from dataclasses import dataclass, field
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

STRATEGIES = [
    'CONVERGENCE_OVER_PURE',
    'CONVERGENCE_UNDER_PURE', 
    'CONVERGENCE_OVER_MC',
    'CONVERGENCE_UNDER_MC',
    'QUANT_BEST_MARKET',
    'MONTE_CARLO_PURE',
    'TOTAL_CHAOS',
    'ADAPTIVE_ENGINE',
    'MC_V2_PURE',
]

@dataclass
class TeamProfile:
    name: str
    tendency: str
    best_market: str
    best_roi: float
    xg_for: float
    xg_against: float
    strategy_stats: Dict[str, Dict] = field(default_factory=dict)
    best_strategy: str = ""
    best_strategy_wr: float = 0
    best_strategy_roi: float = 0
    best_strategy_pnl: float = 0
    total_losses: int = 0
    unlucky_losses: int = 0
    bad_analysis_losses: int = 0
    total_matches: int = 0

class AuditGranulaireV2:
    def __init__(self):
        self.conn = None
        self.team_data = {}
        self.team_profiles: Dict[str, TeamProfile] = {}
        self.matches = []
        
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
                FROM team_market_profiles WHERE sample_size >= 3
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
                
                self.team_profiles[team] = TeamProfile(
                    name=team,
                    tendency=tendency,
                    best_market=best_market,
                    best_roi=best_roi,
                    xg_for=float(xg.get('avg_xg_for') or 1.3),
                    xg_against=float(xg.get('avg_xg_against') or 1.3),
                )
                
            cur.execute("""
                SELECT match_id, home_team, away_team, score_home, score_away
                FROM match_results 
                WHERE commence_time >= '2025-09-01' AND is_finished = true
            """)
            self.matches = cur.fetchall()
            
        print(f"✅ {len(self.team_profiles)} équipes, {len(self.matches)} matchs chargés")
        
    def find_team(self, name: str) -> Tuple[Optional[str], Optional[Dict]]:
        for t in self.team_data:
            if t.lower() in name.lower() or name.lower() in t.lower():
                return t, self.team_data[t]
        return None, None
        
    def poisson_random(self, lam: float) -> int:
        if lam <= 0:
            return 0
        L = math.exp(-lam)
        k = 0
        p = 1.0
        while p > L:
            k += 1
            p *= random.random()
        return k - 1
        
    def monte_carlo_simulate(self, home_xg_for: float, home_xg_ag: float,
                            away_xg_for: float, away_xg_ag: float, n_sims: int = 2000) -> Dict:
        HOME_ADVANTAGE = 1.12
        lambda_h = math.sqrt(home_xg_for * away_xg_ag) * HOME_ADVANTAGE
        lambda_a = math.sqrt(away_xg_for * home_xg_ag)
        
        over_25 = over_35 = btts_yes = 0
        total_goals = []
        
        for _ in range(n_sims):
            home_goals = self.poisson_random(lambda_h)
            away_goals = self.poisson_random(lambda_a)
            total = home_goals + away_goals
            total_goals.append(total)
            
            if total >= 3: over_25 += 1
            if total >= 4: over_35 += 1
            if home_goals > 0 and away_goals > 0: btts_yes += 1
                
        return {
            'over_25_prob': over_25 / n_sims,
            'over_35_prob': over_35 / n_sims,
            'under_25_prob': (n_sims - over_25) / n_sims,
            'btts_yes_prob': btts_yes / n_sims,
            'expected_goals': sum(total_goals) / n_sims,
        }
        
    def evaluate_market(self, total_goals: int, home_goals: int, away_goals: int, market: str) -> bool:
        both = home_goals > 0 and away_goals > 0
        return {
            'over_25': total_goals >= 3, 'over_35': total_goals >= 4,
            'over_15': total_goals >= 2, 'under_25': total_goals < 3,
            'under_35': total_goals < 4, 'btts_yes': both, 'btts_no': not both,
        }.get(market, False)
        
    def analyze_loss(self, market: str, xg_expected: float, mc_prob: float) -> str:
        """Si MC >= 60% et perd = malchance (le 40% s'est réalisé)"""
        if market in ['over_25', 'over_35']:
            if mc_prob >= 0.58 or xg_expected >= 2.7:
                return "UNLUCKY"
            return "BAD_ANALYSIS"
        elif market in ['under_25', 'under_35']:
            if mc_prob >= 0.52 or xg_expected <= 2.4:
                return "UNLUCKY"
            return "BAD_ANALYSIS"
        return "UNLUCKY"
        
    def apply_strategies(self, team_name: str, opponent_name: str, 
                        is_home: bool, match: dict) -> Dict[str, Dict]:
        results = {}
        
        team_key, team_data = self.find_team(team_name)
        opp_key, opp_data = self.find_team(opponent_name)
        
        if not team_data or not opp_data:
            return results
            
        if is_home:
            score_for = match['score_home'] or 0
            score_against = match['score_away'] or 0
            home_xg_for, home_xg_ag = team_data['xg_for'], team_data['xg_against']
            away_xg_for, away_xg_ag = opp_data['xg_for'], opp_data['xg_against']
        else:
            score_for = match['score_away'] or 0
            score_against = match['score_home'] or 0
            home_xg_for, home_xg_ag = opp_data['xg_for'], opp_data['xg_against']
            away_xg_for, away_xg_ag = team_data['xg_for'], team_data['xg_against']
            
        total_goals = score_for + score_against
        home_goals = match['score_home'] or 0
        away_goals = match['score_away'] or 0
        
        mc = self.monte_carlo_simulate(home_xg_for, home_xg_ag, away_xg_for, away_xg_ag)
        xg_expected = mc['expected_goals']
        
        team_tendency = team_data['tendency']
        opp_tendency = opp_data['tendency']
        convergence_over = team_tendency == "OVER" and opp_tendency == "OVER"
        convergence_under = team_tendency == "UNDER" and opp_tendency == "UNDER"
        style_clash = (team_tendency == "OVER" and opp_tendency == "UNDER") or \
                     (team_tendency == "UNDER" and opp_tendency == "OVER")
        
        # STRATÉGIE 1: CONVERGENCE_OVER_PURE
        if convergence_over and xg_expected >= 2.5:
            market = 'over_25'
            won = self.evaluate_market(total_goals, home_goals, away_goals, market)
            results['CONVERGENCE_OVER_PURE'] = {
                'bet': True, 'market': market, 'won': won, 'stake': 2.0,
                'profit': 2.0 * (MARKET_ODDS[market] - 1) if won else -2.0,
                'xg': xg_expected, 'mc_prob': mc['over_25_prob'],
                'loss_type': self.analyze_loss(market, xg_expected, mc['over_25_prob']) if not won else None
            }
        else:
            results['CONVERGENCE_OVER_PURE'] = {'bet': False}
            
        # STRATÉGIE 2: CONVERGENCE_UNDER_PURE
        if convergence_under and xg_expected <= 2.3:
            market = 'under_25'
            won = self.evaluate_market(total_goals, home_goals, away_goals, market)
            results['CONVERGENCE_UNDER_PURE'] = {
                'bet': True, 'market': market, 'won': won, 'stake': 2.0,
                'profit': 2.0 * (MARKET_ODDS[market] - 1) if won else -2.0,
                'xg': xg_expected, 'mc_prob': mc['under_25_prob'],
                'loss_type': self.analyze_loss(market, xg_expected, mc['under_25_prob']) if not won else None
            }
        else:
            results['CONVERGENCE_UNDER_PURE'] = {'bet': False}
            
        # STRATÉGIE 3: CONVERGENCE_OVER_MC
        if convergence_over and mc['over_25_prob'] >= 0.55:
            market = 'over_25'
            won = self.evaluate_market(total_goals, home_goals, away_goals, market)
            results['CONVERGENCE_OVER_MC'] = {
                'bet': True, 'market': market, 'won': won, 'stake': 2.5,
                'profit': 2.5 * (MARKET_ODDS[market] - 1) if won else -2.5,
                'xg': xg_expected, 'mc_prob': mc['over_25_prob'],
                'loss_type': self.analyze_loss(market, xg_expected, mc['over_25_prob']) if not won else None
            }
        else:
            results['CONVERGENCE_OVER_MC'] = {'bet': False}
            
        # STRATÉGIE 4: CONVERGENCE_UNDER_MC
        if convergence_under and mc['under_25_prob'] >= 0.50:
            market = 'under_25'
            won = self.evaluate_market(total_goals, home_goals, away_goals, market)
            results['CONVERGENCE_UNDER_MC'] = {
                'bet': True, 'market': market, 'won': won, 'stake': 2.0,
                'profit': 2.0 * (MARKET_ODDS[market] - 1) if won else -2.0,
                'xg': xg_expected, 'mc_prob': mc['under_25_prob'],
                'loss_type': self.analyze_loss(market, xg_expected, mc['under_25_prob']) if not won else None
            }
        else:
            results['CONVERGENCE_UNDER_MC'] = {'bet': False}
            
        # STRATÉGIE 5: QUANT_BEST_MARKET
        best_market = team_data['best_market']
        if best_market in MARKET_ODDS and team_data['best_roi'] >= 20:
            won = self.evaluate_market(total_goals, home_goals, away_goals, best_market)
            results['QUANT_BEST_MARKET'] = {
                'bet': True, 'market': best_market, 'won': won, 'stake': 2.0,
                'profit': 2.0 * (MARKET_ODDS[best_market] - 1) if won else -2.0,
                'xg': xg_expected, 'mc_prob': mc['over_25_prob'],
                'loss_type': self.analyze_loss(best_market, xg_expected, mc['over_25_prob']) if not won else None
            }
        else:
            results['QUANT_BEST_MARKET'] = {'bet': False}
            
        # STRATÉGIE 6: MONTE_CARLO_PURE
        if mc['over_25_prob'] >= 0.60:
            market = 'over_25'
            won = self.evaluate_market(total_goals, home_goals, away_goals, market)
            results['MONTE_CARLO_PURE'] = {
                'bet': True, 'market': market, 'won': won, 'stake': 2.0,
                'profit': 2.0 * (MARKET_ODDS[market] - 1) if won else -2.0,
                'xg': xg_expected, 'mc_prob': mc['over_25_prob'],
                'loss_type': self.analyze_loss(market, xg_expected, mc['over_25_prob']) if not won else None
            }
        elif mc['under_25_prob'] >= 0.55 and xg_expected <= 2.5:
            market = 'under_25'
            won = self.evaluate_market(total_goals, home_goals, away_goals, market)
            results['MONTE_CARLO_PURE'] = {
                'bet': True, 'market': market, 'won': won, 'stake': 2.0,
                'profit': 2.0 * (MARKET_ODDS[market] - 1) if won else -2.0,
                'xg': xg_expected, 'mc_prob': mc['under_25_prob'],
                'loss_type': self.analyze_loss(market, xg_expected, mc['under_25_prob']) if not won else None
            }
        else:
            results['MONTE_CARLO_PURE'] = {'bet': False}
            
        # STRATÉGIE 7: TOTAL_CHAOS
        if xg_expected >= 3.0 and mc['over_25_prob'] >= 0.65:
            market = 'over_35' if xg_expected >= 3.5 else 'over_25'
            won = self.evaluate_market(total_goals, home_goals, away_goals, market)
            results['TOTAL_CHAOS'] = {
                'bet': True, 'market': market, 'won': won, 'stake': 2.5,
                'profit': 2.5 * (MARKET_ODDS[market] - 1) if won else -2.5,
                'xg': xg_expected, 'mc_prob': mc['over_25_prob'],
                'loss_type': self.analyze_loss(market, xg_expected, mc['over_25_prob']) if not won else None
            }
        else:
            results['TOTAL_CHAOS'] = {'bet': False}
            
        # STRATÉGIE 8: ADAPTIVE_ENGINE
        if team_data['best_roi'] >= 30:
            market = team_data['best_market']
            if market in MARKET_ODDS:
                won = self.evaluate_market(total_goals, home_goals, away_goals, market)
                results['ADAPTIVE_ENGINE'] = {
                    'bet': True, 'market': market, 'won': won, 'stake': 2.0,
                    'profit': 2.0 * (MARKET_ODDS[market] - 1) if won else -2.0,
                    'xg': xg_expected, 'mc_prob': mc['over_25_prob'],
                    'loss_type': self.analyze_loss(market, xg_expected, mc['over_25_prob']) if not won else None
                }
            else:
                results['ADAPTIVE_ENGINE'] = {'bet': False}
        else:
            results['ADAPTIVE_ENGINE'] = {'bet': False}
            
        # STRATÉGIE 9: MC_V2_PURE
        if not style_clash and mc['over_25_prob'] >= 0.65:
            market = 'over_25'
            won = self.evaluate_market(total_goals, home_goals, away_goals, market)
            results['MC_V2_PURE'] = {
                'bet': True, 'market': market, 'won': won, 'stake': 2.0,
                'profit': 2.0 * (MARKET_ODDS[market] - 1) if won else -2.0,
                'xg': xg_expected, 'mc_prob': mc['over_25_prob'],
                'loss_type': self.analyze_loss(market, xg_expected, mc['over_25_prob']) if not won else None
            }
        else:
            results['MC_V2_PURE'] = {'bet': False}
            
        return results
        
    def run_audit(self):
        print("\n" + "="*100)
        print("🎯 AUDIT GRANULAIRE PAR ÉQUIPE - ANALYSE INDIVIDUELLE")
        print("="*100)
        
        for team_name, profile in self.team_profiles.items():
            for strat in STRATEGIES:
                profile.strategy_stats[strat] = {
                    'bets': 0, 'wins': 0, 'profit': 0, 'stake': 0,
                    'unlucky': 0, 'bad_analysis': 0
                }
                
            for match in self.matches:
                is_home = team_name.lower() in match['home_team'].lower() or \
                         match['home_team'].lower() in team_name.lower()
                is_away = team_name.lower() in match['away_team'].lower() or \
                         match['away_team'].lower() in team_name.lower()
                         
                if not is_home and not is_away:
                    continue
                    
                profile.total_matches += 1
                opponent = match['away_team'] if is_home else match['home_team']
                
                results = self.apply_strategies(team_name, opponent, is_home, match)
                
                for strat, res in results.items():
                    if res.get('bet', False):
                        stats = profile.strategy_stats[strat]
                        stats['bets'] += 1
                        stats['stake'] += res['stake']
                        if res['won']:
                            stats['wins'] += 1
                        else:
                            if res.get('loss_type') == 'UNLUCKY':
                                stats['unlucky'] += 1
                            else:
                                stats['bad_analysis'] += 1
                        stats['profit'] += res['profit']
                        
            best_strat = None
            best_pnl = -999
            
            for strat, stats in profile.strategy_stats.items():
                if stats['bets'] >= 3:
                    if stats['profit'] > best_pnl:
                        best_pnl = stats['profit']
                        best_strat = strat
                        
            if best_strat:
                stats = profile.strategy_stats[best_strat]
                profile.best_strategy = best_strat
                profile.best_strategy_pnl = stats['profit']
                profile.best_strategy_wr = (stats['wins'] / stats['bets'] * 100) if stats['bets'] > 0 else 0
                profile.best_strategy_roi = (stats['profit'] / stats['stake'] * 100) if stats['stake'] > 0 else 0
                profile.total_losses = stats['bets'] - stats['wins']
                profile.unlucky_losses = stats['unlucky']
                profile.bad_analysis_losses = stats['bad_analysis']
                
        print(f"✅ {len(self.team_profiles)} équipes auditées")
        
    def print_results(self):
        print("\n" + "="*120)
        print("📊 RÉSULTATS AUDIT GRANULAIRE PAR ÉQUIPE")
        print("="*120)
        
        sorted_teams = sorted(
            [p for p in self.team_profiles.values() if p.best_strategy],
            key=lambda x: x.best_strategy_pnl,
            reverse=True
        )
        
        print(f"\n{'='*140}")
        print("🏆 TOP 50 ÉQUIPES - MEILLEURE STRATÉGIE INDIVIDUELLE:")
        print(f"{'='*140}")
        print(f"\n{'#':<3} {'Équipe':<32} {'Best Strategy':<22} {'Matchs':<7} {'Paris':<7} {'WR':<8} {'ROI':<10} {'P&L':<10} {'Pertes':<7} {'Malch%':<8} {'Err%':<6}")
        print("-"*140)
        
        for i, p in enumerate(sorted_teams[:50], 1):
            stats = p.strategy_stats[p.best_strategy]
            emoji = "💎" if p.best_strategy_pnl >= 10 else "✅" if p.best_strategy_pnl > 0 else "❌"
            unlucky_pct = (p.unlucky_losses / p.total_losses * 100) if p.total_losses > 0 else 0
            bad_pct = (p.bad_analysis_losses / p.total_losses * 100) if p.total_losses > 0 else 0
            
            print(f"{emoji}{i:<2} {p.name[:31]:<32} {p.best_strategy[:21]:<22} "
                  f"{p.total_matches:<7} {stats['bets']:<7} {p.best_strategy_wr:.0f}%{'':<4} {p.best_strategy_roi:+.0f}%{'':<5} "
                  f"{p.best_strategy_pnl:+.1f}u{'':<4} {p.total_losses:<7} {unlucky_pct:.0f}%{'':<5} {bad_pct:.0f}%")
                  
        print(f"\n{'='*120}")
        print("📈 RÉPARTITION DES ÉQUIPES PAR MEILLEURE STRATÉGIE:")
        print(f"{'='*120}")
        
        strat_count = defaultdict(lambda: {'teams': 0, 'total_pnl': 0, 'total_bets': 0, 'total_wins': 0})
        for p in sorted_teams:
            if p.best_strategy:
                strat_count[p.best_strategy]['teams'] += 1
                strat_count[p.best_strategy]['total_pnl'] += p.best_strategy_pnl
                stats = p.strategy_stats[p.best_strategy]
                strat_count[p.best_strategy]['total_bets'] += stats['bets']
                strat_count[p.best_strategy]['total_wins'] += stats['wins']
                
        print(f"\n{'Stratégie':<25} {'Équipes':<10} {'Paris Tot':<12} {'WR Moy':<10} {'P&L Total':<12}")
        print("-"*75)
        
        for strat, data in sorted(strat_count.items(), key=lambda x: x[1]['total_pnl'], reverse=True):
            wr = (data['total_wins'] / data['total_bets'] * 100) if data['total_bets'] > 0 else 0
            emoji = "💎" if data['total_pnl'] > 50 else "✅" if data['total_pnl'] > 0 else "❌"
            print(f"{emoji} {strat:<23} {data['teams']:<10} {data['total_bets']:<12} {wr:.1f}%{'':<6} {data['total_pnl']:+.1f}u")
            
        print(f"\n{'='*120}")
        print("📉 ANALYSE GLOBALE DES PERTES:")
        print(f"{'='*120}")
        
        total_unlucky = sum(p.unlucky_losses for p in sorted_teams)
        total_bad = sum(p.bad_analysis_losses for p in sorted_teams)
        total_losses = total_unlucky + total_bad
        
        if total_losses > 0:
            print(f"\n   Total pertes: {total_losses}")
            print(f"   🎲 Malchance: {total_unlucky} ({total_unlucky/total_losses*100:.1f}%)")
            print(f"   ❌ Mauvaise analyse: {total_bad} ({total_bad/total_losses*100:.1f}%)")
            
        print(f"\n{'='*120}")
        print("🎯 TOP 5 ÉQUIPES PAR STRATÉGIE:")
        print(f"{'='*120}")
        
        for strat in STRATEGIES:
            teams_for_strat = [(p.name, p.strategy_stats[strat], p.total_matches) 
                              for p in self.team_profiles.values() 
                              if p.strategy_stats[strat]['bets'] >= 3]
            teams_for_strat.sort(key=lambda x: x[1]['profit'], reverse=True)
            
            if teams_for_strat:
                print(f"\n📊 {strat}:")
                for i, (name, stats, matches) in enumerate(teams_for_strat[:5], 1):
                    wr = (stats['wins'] / stats['bets'] * 100) if stats['bets'] > 0 else 0
                    print(f"   {i}. {name[:35]:<37} {matches} matchs, {stats['bets']} paris, {wr:.0f}% WR, {stats['profit']:+.1f}u")
                    
        print(f"\n{'='*120}")
        print("⚠️ ÉQUIPES À ÉVITER:")
        print(f"{'='*120}")
        
        avoid_teams = [p for p in self.team_profiles.values() 
                      if not p.best_strategy or p.best_strategy_pnl < 0]
        avoid_teams.sort(key=lambda x: x.best_strategy_pnl if x.best_strategy else -100)
        
        for p in avoid_teams[:15]:
            if p.best_strategy:
                print(f"❌ {p.name[:40]:<42} Best: {p.best_strategy}: {p.best_strategy_pnl:+.1f}u")
            else:
                print(f"❌ {p.name[:40]:<42} Pas assez de paris (< 3)")
                
        output = {'timestamp': datetime.now().isoformat(), 'teams': {}}
        for p in sorted_teams[:60]:
            output['teams'][p.name] = {
                'best_strategy': p.best_strategy,
                'wr': round(p.best_strategy_wr, 1),
                'roi': round(p.best_strategy_roi, 1),
                'pnl': round(p.best_strategy_pnl, 1),
                'matches': p.total_matches,
                'losses': p.total_losses,
                'unlucky_pct': round(p.unlucky_losses / p.total_losses * 100, 1) if p.total_losses > 0 else 0,
                'all_strategies': {
                    s: {'bets': st['bets'], 'wins': st['wins'], 'profit': round(st['profit'], 1)}
                    for s, st in p.strategy_stats.items() if st['bets'] > 0
                }
            }
            
        with open('audit_granulaire_v2_results.json', 'w') as f:
            json.dump(output, f, indent=2)
            
        print(f"\n✅ Résultats sauvegardés dans audit_granulaire_v2_results.json")

def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║     🎯 AUDIT GRANULAIRE PAR ÉQUIPE V2                                         ║
║  • Analyse INDIVIDUELLE par équipe                                            ║
║  • TOUS les matchs depuis septembre                                           ║
║  • TOUTES les stratégies testées                                             ║
║  • Meilleure stratégie PAR équipe                                            ║
║  • Analyse pertes: malchance vs erreur                                       ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    audit = AuditGranulaireV2()
    audit.connect()
    audit.load_data()
    audit.run_audit()
    audit.print_results()

if __name__ == "__main__":
    main()
