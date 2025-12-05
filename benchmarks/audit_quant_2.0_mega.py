#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║     🏦 AUDIT QUANT 2.0 MEGA - 28 STRATÉGIES HEDGE FUND                        ║
╚═══════════════════════════════════════════════════════════════════════════════╝
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

OVER_MARKETS = ['over_25', 'over_35', 'over_15', 'btts_yes']
UNDER_MARKETS = ['under_25', 'under_35', 'btts_no']

STRATEGIES = [
    'CONVERGENCE_OVER_PURE', 'CONVERGENCE_OVER_MC_55', 'CONVERGENCE_OVER_MC_60',
    'CONVERGENCE_UNDER_PURE', 'CONVERGENCE_UNDER_MC',
    'MC_PURE_60', 'MC_PURE_65', 'MC_PURE_70', 'MC_V2_NO_CLASH',
    'QUANT_BEST_MARKET', 'QUANT_ROI_30', 'QUANT_ROI_40', 'ADAPTIVE_ENGINE',
    'TOTAL_CHAOS', 'CHAOS_EXTREME',
    'SWEET_SPOT_60_79', 'SWEET_SPOT_CONSERVATIVE',
    'CONV_MC_COMBO', 'QUANT_MC_COMBO', 'TRIPLE_VALIDATION',
    'XG_HIGH_28', 'XG_HIGH_30', 'XG_LOW_23',
    'TEAM_WR_70', 'TEAM_WR_75', 'TEAM_WR_80',
    'SNIPER_ELITE',
]

@dataclass
class TeamProfile:
    name: str
    tendency: str
    best_market: str
    best_roi: float
    xg_for: float
    xg_against: float
    historical_wr: float = 0
    strategy_stats: Dict[str, Dict] = field(default_factory=dict)
    best_strategy: str = ""
    best_strategy_wr: float = 0
    best_strategy_roi: float = 0
    best_strategy_pnl: float = 0
    best_strategy_wins: int = 0
    best_strategy_bets: int = 0
    total_losses: int = 0
    unlucky_losses: int = 0
    bad_analysis_losses: int = 0
    total_matches: int = 0
    top3_strategies: List[Tuple[str, float]] = field(default_factory=list)

class AuditQuant20:
    def __init__(self):
        self.conn = None
        self.team_data = {}
        self.team_profiles: Dict[str, TeamProfile] = {}
        self.matches = []
        
    def connect(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.conn.autocommit = True  # FIX: Évite le blocage de transaction
        print("✅ Connexion DB établie")
        
    def load_data(self):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # XG Tendencies
            cur.execute("SELECT * FROM team_xg_tendencies")
            xg_data = {r['team_name']: r for r in cur.fetchall()}
            
            # Market Profiles
            cur.execute("""
                SELECT team_name, market_type, roi, win_rate, is_best_market, sample_size
                FROM team_market_profiles WHERE sample_size >= 3
            """)
            mkt_data = {}
            for r in cur.fetchall():
                team = r['team_name']
                if team not in mkt_data:
                    mkt_data[team] = {'markets': {}, 'best_wr': 0}
                mkt_data[team]['markets'][r['market_type']] = {
                    'roi': float(r['roi'] or 0),
                    'wr': float(r['win_rate'] or 0),
                    'is_best': r['is_best_market'],
                    'sample': r['sample_size']
                }
                if r['is_best_market'] and float(r['win_rate'] or 0) > mkt_data[team]['best_wr']:
                    mkt_data[team]['best_wr'] = float(r['win_rate'] or 0)
                
            # Build team profiles
            for team in set(xg_data.keys()):
                xg = xg_data.get(team, {})
                markets = mkt_data.get(team, {'markets': {}, 'best_wr': 0})
                
                best_market = 'over_25'
                best_roi = 0
                for mkt, data in markets['markets'].items():
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
                    'markets': markets['markets'],
                    'best_wr': markets['best_wr']
                }
                
                self.team_profiles[team] = TeamProfile(
                    name=team,
                    tendency=tendency,
                    best_market=best_market,
                    best_roi=best_roi,
                    xg_for=float(xg.get('avg_xg_for') or 1.3),
                    xg_against=float(xg.get('avg_xg_against') or 1.3),
                    historical_wr=markets['best_wr']
                )
                
            # Matchs
            cur.execute("""
                SELECT match_id, home_team, away_team, score_home, score_away
                FROM match_results 
                WHERE commence_time >= '2024-09-01' AND is_finished = true
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
            home_xg_for, home_xg_ag = team_data['xg_for'], team_data['xg_against']
            away_xg_for, away_xg_ag = opp_data['xg_for'], opp_data['xg_against']
        else:
            home_xg_for, home_xg_ag = opp_data['xg_for'], opp_data['xg_against']
            away_xg_for, away_xg_ag = team_data['xg_for'], team_data['xg_against']
            
        total_goals = (match['score_home'] or 0) + (match['score_away'] or 0)
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
        
        def make_bet(strat_name, condition, market, stake=2.0):
            if condition:
                won = self.evaluate_market(total_goals, home_goals, away_goals, market)
                mc_prob = mc['over_25_prob'] if 'over' in market else mc['under_25_prob']
                results[strat_name] = {
                    'bet': True, 'market': market, 'won': won, 'stake': stake,
                    'profit': stake * (MARKET_ODDS.get(market, 1.85) - 1) if won else -stake,
                    'xg': xg_expected, 'mc_prob': mc_prob,
                    'loss_type': self.analyze_loss(market, xg_expected, mc_prob) if not won else None
                }
            else:
                results[strat_name] = {'bet': False}
        
        # GROUPE A: CONVERGENCE
        make_bet('CONVERGENCE_OVER_PURE', convergence_over and xg_expected >= 2.5, 'over_25', 2.0)
        make_bet('CONVERGENCE_OVER_MC_55', convergence_over and mc['over_25_prob'] >= 0.55, 'over_25', 2.5)
        make_bet('CONVERGENCE_OVER_MC_60', convergence_over and mc['over_25_prob'] >= 0.60, 'over_25', 3.0)
        make_bet('CONVERGENCE_UNDER_PURE', convergence_under and xg_expected <= 2.3, 'under_25', 2.0)
        make_bet('CONVERGENCE_UNDER_MC', convergence_under and mc['under_25_prob'] >= 0.50, 'under_25', 2.0)
        
        # GROUPE B: MONTE CARLO
        make_bet('MC_PURE_60', mc['over_25_prob'] >= 0.60, 'over_25', 2.0)
        make_bet('MC_PURE_65', mc['over_25_prob'] >= 0.65, 'over_25', 2.5)
        make_bet('MC_PURE_70', mc['over_25_prob'] >= 0.70, 'over_25', 3.0)
        make_bet('MC_V2_NO_CLASH', not style_clash and mc['over_25_prob'] >= 0.65, 'over_25', 2.5)
        
        # GROUPE C: QUANT MARKET
        best_mkt = team_data['best_market']
        if best_mkt in MARKET_ODDS:
            make_bet('QUANT_BEST_MARKET', team_data['best_roi'] >= 20, best_mkt, 2.0)
            make_bet('QUANT_ROI_30', team_data['best_roi'] >= 30, best_mkt, 2.5)
            make_bet('QUANT_ROI_40', team_data['best_roi'] >= 40, best_mkt, 3.0)
            make_bet('ADAPTIVE_ENGINE', team_data['best_roi'] >= 30, best_mkt, 2.0)
        else:
            for s in ['QUANT_BEST_MARKET', 'QUANT_ROI_30', 'QUANT_ROI_40', 'ADAPTIVE_ENGINE']:
                results[s] = {'bet': False}
        
        # GROUPE D: CHAOS
        make_bet('TOTAL_CHAOS', xg_expected >= 3.0 and mc['over_25_prob'] >= 0.65, 'over_25', 2.5)
        make_bet('CHAOS_EXTREME', xg_expected >= 3.5 and mc['over_35_prob'] >= 0.55, 'over_35', 3.0)
        
        # GROUPE E: SWEET SPOT
        sweet_score = mc['over_25_prob'] * 100
        make_bet('SWEET_SPOT_60_79', 60 <= sweet_score <= 79, 'over_25', 2.5)
        make_bet('SWEET_SPOT_CONSERVATIVE', 65 <= sweet_score <= 75 and xg_expected >= 2.6, 'over_25', 2.0)
        
        # GROUPE F: COMBOS
        make_bet('CONV_MC_COMBO', convergence_over and mc['over_25_prob'] >= 0.58 and xg_expected >= 2.6, 'over_25', 3.0)
        make_bet('QUANT_MC_COMBO', team_data['best_roi'] >= 25 and mc['over_25_prob'] >= 0.55, 'over_25', 2.5)
        make_bet('TRIPLE_VALIDATION', convergence_over and mc['over_25_prob'] >= 0.60 and xg_expected >= 2.7, 'over_25', 3.5)
        
        # GROUPE G: XG THRESHOLDS
        make_bet('XG_HIGH_28', xg_expected >= 2.8 and not style_clash, 'over_25', 2.0)
        make_bet('XG_HIGH_30', xg_expected >= 3.0 and not style_clash, 'over_25', 2.5)
        make_bet('XG_LOW_23', xg_expected <= 2.3 and not style_clash, 'under_25', 2.0)
        
        # GROUPE H: WR HISTORICAL
        team_wr = team_data.get('best_wr', 0)
        if best_mkt in MARKET_ODDS:
            make_bet('TEAM_WR_70', team_wr >= 70, best_mkt, 2.0)
            make_bet('TEAM_WR_75', team_wr >= 75, best_mkt, 2.5)
            make_bet('TEAM_WR_80', team_wr >= 80, best_mkt, 3.0)
        else:
            for s in ['TEAM_WR_70', 'TEAM_WR_75', 'TEAM_WR_80']:
                results[s] = {'bet': False}
        
        # GROUPE I: SNIPER ELITE
        sniper_cond = (
            convergence_over and 
            mc['over_25_prob'] >= 0.65 and 
            xg_expected >= 2.8 and 
            team_data['best_roi'] >= 25
        )
        make_bet('SNIPER_ELITE', sniper_cond, 'over_25', 4.0)
        
        return results
        
    def run_audit(self):
        print("\n" + "="*100)
        print("🏦 AUDIT QUANT 2.0 MEGA - 28 STRATÉGIES")
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
                        
            # Trouver les 3 meilleures stratégies
            strat_profits = [(s, stats['profit']) for s, stats in profile.strategy_stats.items() if stats['bets'] >= 1]
            strat_profits.sort(key=lambda x: x[1], reverse=True)
            profile.top3_strategies = strat_profits[:3]
            
            if strat_profits:
                best_strat, best_pnl = strat_profits[0]
                stats = profile.strategy_stats[best_strat]
                profile.best_strategy = best_strat
                profile.best_strategy_pnl = best_pnl
                profile.best_strategy_wins = stats['wins']
                profile.best_strategy_bets = stats['bets']
                profile.best_strategy_wr = (stats['wins'] / stats['bets'] * 100) if stats['bets'] > 0 else 0
                profile.best_strategy_roi = (stats['profit'] / stats['stake'] * 100) if stats['stake'] > 0 else 0
                profile.total_losses = stats['bets'] - stats['wins']
                profile.unlucky_losses = stats['unlucky']
                profile.bad_analysis_losses = stats['bad_analysis']
                
        print(f"✅ {len(self.team_profiles)} équipes auditées avec 28 stratégies")
        
    def print_results(self):
        print("\n")
        print("="*180)
        print("🏆 TABLEAU COMPLET 99 ÉQUIPES - 28 STRATÉGIES QUANT 2.0")
        print("="*180)
        
        all_teams = sorted(
            self.team_profiles.values(),
            key=lambda x: x.best_strategy_pnl if x.best_strategy else -1000,
            reverse=True
        )
        
        print(f"\n{'#':<4} {'Équipe':<30} {'Best Strategy':<25} {'M':<4} {'P':<4} {'W':<4} {'L':<3} {'WR':<7} {'ROI':<8} {'P&L':<10} {'2nd Best':<20} {'3rd Best':<20}")
        print("-"*180)
        
        total_bets = total_wins = 0
        total_pnl = 0
        
        for i, p in enumerate(all_teams, 1):
            if p.best_strategy:
                stats = p.strategy_stats[p.best_strategy]
                losses = p.total_losses
                
                if p.best_strategy_pnl >= 15:
                    emoji = "💎"
                elif p.best_strategy_pnl >= 5:
                    emoji = "✅"
                elif p.best_strategy_pnl >= 0:
                    emoji = "⚪"
                else:
                    emoji = "❌"
                
                second = f"{p.top3_strategies[1][0][:15]}({p.top3_strategies[1][1]:+.1f})" if len(p.top3_strategies) > 1 else "-"
                third = f"{p.top3_strategies[2][0][:15]}({p.top3_strategies[2][1]:+.1f})" if len(p.top3_strategies) > 2 else "-"
                
                print(f"{emoji}{i:<3} {p.name[:29]:<30} {p.best_strategy[:24]:<25} "
                      f"{p.total_matches:<4} {stats['bets']:<4} {stats['wins']:<4} {losses:<3} "
                      f"{p.best_strategy_wr:.0f}%{'':<3} {p.best_strategy_roi:+.0f}%{'':<3} "
                      f"{p.best_strategy_pnl:+.1f}u{'':<4} {second:<20} {third:<20}")
                      
                total_bets += stats['bets']
                total_wins += stats['wins']
                total_pnl += p.best_strategy_pnl
            else:
                print(f"⚠️{i:<3} {p.name[:29]:<30} {'AUCUNE':<25} {p.total_matches:<4} -    -    -   -       -        -")
        
        # Résumé
        print("-"*180)
        wr = (total_wins / total_bets * 100) if total_bets > 0 else 0
        print(f"{'TOTAL':<4} {'':<30} {'':<25} {'':<4} {total_bets:<4} {total_wins:<4} {total_bets-total_wins:<3} {wr:.0f}%{'':<3} {'':<8} {total_pnl:+.1f}u")
        
        # Classement stratégies
        print("\n" + "="*120)
        print("📈 CLASSEMENT DES 28 STRATÉGIES (par P&L total):")
        print("="*120)
        
        strat_totals = defaultdict(lambda: {'teams': 0, 'bets': 0, 'wins': 0, 'pnl': 0, 'unlucky': 0, 'bad': 0})
        for p in all_teams:
            for strat, stats in p.strategy_stats.items():
                if stats['bets'] > 0:
                    strat_totals[strat]['teams'] += 1
                    strat_totals[strat]['bets'] += stats['bets']
                    strat_totals[strat]['wins'] += stats['wins']
                    strat_totals[strat]['pnl'] += stats['profit']
                    strat_totals[strat]['unlucky'] += stats['unlucky']
                    strat_totals[strat]['bad'] += stats['bad_analysis']
        
        sorted_strats = sorted(strat_totals.items(), key=lambda x: x[1]['pnl'], reverse=True)
        
        print(f"\n{'#':<4} {'Stratégie':<28} {'Éq.':<8} {'Paris':<8} {'Wins':<8} {'WR':<8} {'P&L':<12} {'Mal%':<8} {'Verdict':<15}")
        print("-"*110)
        
        for i, (strat, data) in enumerate(sorted_strats, 1):
            wr = (data['wins'] / data['bets'] * 100) if data['bets'] > 0 else 0
            losses = data['bets'] - data['wins']
            unlucky_pct = (data['unlucky'] / losses * 100) if losses > 0 else 0
            
            if data['pnl'] >= 100:
                emoji, verdict = "💎", "EXCELLENT"
            elif data['pnl'] >= 50:
                emoji, verdict = "🏆", "TRÈS BON"
            elif data['pnl'] >= 0:
                emoji, verdict = "✅", "POSITIF"
            else:
                emoji, verdict = "❌", "À ÉVITER"
                
            print(f"{emoji}{i:<3} {strat:<28} {data['teams']:<8} {data['bets']:<8} {data['wins']:<8} {wr:.1f}%{'':<4} {data['pnl']:+.1f}u{'':<6} {unlucky_pct:.0f}%{'':<5} {verdict:<15}")
        
        # Sauvegarder
        output = {
            'timestamp': datetime.now().isoformat(),
            'strategies_count': len(STRATEGIES),
            'teams_count': len(all_teams),
            'total': {'bets': total_bets, 'wins': total_wins, 'pnl': round(total_pnl, 1)},
            'strategy_ranking': [
                {'rank': i+1, 'strategy': s, 'teams': d['teams'], 'bets': d['bets'], 
                 'wins': d['wins'], 'wr': round((d['wins']/d['bets']*100) if d['bets']>0 else 0, 1),
                 'pnl': round(d['pnl'], 1)}
                for i, (s, d) in enumerate(sorted_strats)
            ],
            'teams': [
                {'rank': i+1, 'name': p.name, 'best_strategy': p.best_strategy,
                 'matches': p.total_matches, 'bets': p.best_strategy_bets,
                 'wins': p.best_strategy_wins, 'wr': round(p.best_strategy_wr, 1),
                 'pnl': round(p.best_strategy_pnl, 1),
                 'top3': [(s, round(pnl, 1)) for s, pnl in p.top3_strategies]}
                for i, p in enumerate(all_teams) if p.best_strategy
            ]
        }
        
        with open('audit_quant_2.0_mega_results.json', 'w') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
            
        print(f"\n✅ Résultats sauvegardés dans audit_quant_2.0_mega_results.json")

def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║     🏦 AUDIT QUANT 2.0 MEGA - NIVEAU HEDGE FUND                               ║
║     28 Stratégies testées sur 99 équipes                                     ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    audit = AuditQuant20()
    audit.connect()
    audit.load_data()
    audit.run_audit()
    audit.print_results()

if __name__ == "__main__":
    main()
