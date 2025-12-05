#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║     🧪 ADCM 2.1 BACKTEST - VALIDATION SCIENTIFIQUE SUR 712 MATCHS             ║
║                                                                               ║
║  Objectif: Comparer ADCM 2.1 vs:                                              ║
║  • V13 Reference (76.5% WR, +53.2% ROI, +210.7u)                              ║
║  • Adaptive Engine (+48.3% ROI, +372.8u)                                      ║
║  • COMBINED Strategy (+32.5% ROI, +739.4u)                                    ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import math
from datetime import datetime
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict
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

OVER_MARKETS = ['over_25', 'over_35', 'over_15', 'btts_yes', 'team_over_15', 'team_over_25']
UNDER_MARKETS = ['under_25', 'under_35', 'under_15', 'btts_no', 'clean_sheet', 'fail_to_score']


class Scenario(Enum):
    TOTAL_CHAOS = "TOTAL_CHAOS"
    SIEGE = "SIEGE"
    SNIPER_DUEL = "SNIPER_DUEL"
    ATTRITION = "ATTRITION"
    GLASS_CANNON = "GLASS_CANNON"
    CONVERGENCE_OVER = "CONVERGENCE_OVER"
    CONVERGENCE_UNDER = "CONVERGENCE_UNDER"
    STYLE_CLASH = "STYLE_CLASH"
    UNCERTAIN = "UNCERTAIN"


class Action(Enum):
    SNIPER = "SNIPER"
    NORMAL = "NORMAL"
    SPECULATIVE = "SPECULATIVE"
    SKIP = "SKIP"


@dataclass
class TeamMetrics:
    team_name: str
    pace_index: float
    control_index: float
    lethality_index: float
    defensive_solidity: float
    xg_for: float
    xg_against: float
    best_market: str
    best_market_roi: float
    market_tendency: str


@dataclass
class MatchAnalysis:
    home: TeamMetrics
    away: TeamMetrics
    scenario: Scenario
    confidence: float
    expected_goals: float
    convergence: float
    conv_type: str
    primary_market: str
    primary_edge: float
    action: Action
    stake: float


class ADCMBacktest:
    """ADCM 2.1 Backtest Engine"""
    
    def __init__(self):
        self.conn = None
        self.team_data = {}
        self.matches = []
        self.results = {
            'SNIPER': {'bets': 0, 'wins': 0, 'profit': 0, 'by_scenario': defaultdict(lambda: {'bets': 0, 'wins': 0, 'profit': 0})},
            'NORMAL': {'bets': 0, 'wins': 0, 'profit': 0, 'by_scenario': defaultdict(lambda: {'bets': 0, 'wins': 0, 'profit': 0})},
            'SPECULATIVE': {'bets': 0, 'wins': 0, 'profit': 0, 'by_scenario': defaultdict(lambda: {'bets': 0, 'wins': 0, 'profit': 0})},
            'ALL': {'bets': 0, 'wins': 0, 'profit': 0, 'stake': 0}
        }
        self.scenario_stats = defaultdict(lambda: {'bets': 0, 'wins': 0, 'profit': 0})
        
    def connect(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connexion DB établie")
        
    def load_data(self):
        """Charge équipes et matchs"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # XG
            cur.execute("SELECT * FROM team_xg_tendencies")
            xg_data = {r['team_name']: r for r in cur.fetchall()}
            
            # Big Chances
            cur.execute("SELECT * FROM team_big_chances_tendencies")
            bc_data = {r['team_name']: r for r in cur.fetchall()}
            
            # Market Profiles
            cur.execute("""
                SELECT team_name, market_type, roi, win_rate 
                FROM team_market_profiles 
                WHERE is_best_market = true AND sample_size >= 8
            """)
            mkt_data = {r['team_name']: {'best_market': r['market_type'], 'roi': float(r['roi'] or 0)} for r in cur.fetchall()}
            
            # Merge
            for team in set(xg_data.keys()) | set(bc_data.keys()):
                xg = xg_data.get(team, {})
                bc = bc_data.get(team, {})
                mkt = mkt_data.get(team, {'best_market': 'over_25', 'roi': 0})
                self.team_data[team] = {'xg': xg, 'bc': bc, 'market': mkt}
                
            # Matches
            cur.execute("""
                SELECT match_id, home_team, away_team, score_home, score_away, league, commence_time
                FROM match_results 
                WHERE commence_time >= '2025-09-01' AND is_finished = true
                ORDER BY commence_time
            """)
            self.matches = cur.fetchall()
            
        print(f"✅ {len(self.team_data)} équipes, {len(self.matches)} matchs chargés")
        
    def get_team_metrics(self, name: str) -> Optional[TeamMetrics]:
        """Calcule les métriques pour une équipe"""
        data = None
        team_key = name
        
        for t in self.team_data:
            if t.lower() in name.lower() or name.lower() in t.lower():
                data = self.team_data[t]
                team_key = t
                break
                
        if not data:
            return None
            
        xg = data['xg']
        bc = data['bc']
        mkt = data['market']
        
        xg_for = float(xg.get('avg_xg_for') or 1.3)
        xg_against = float(xg.get('avg_xg_against') or 1.3)
        bc_created = float(bc.get('avg_bc_created') or 1.5)
        bc_conversion = float(bc.get('bc_conversion_rate') or 45)
        shot_quality = float(bc.get('avg_shot_quality') or 0.12)
        bc_conceded = float(bc.get('avg_bc_conceded') or 1.5)
        open_rate = float(xg.get('open_rate') or 50)
        defensive_rate = float(xg.get('defensive_rate') or 50)
        
        # Indices calibrés
        pace = min(100, ((xg_for / 1.3) * 30) + ((bc_created / 1.5) * 20))
        control = (open_rate * 0.7) + ((100 - defensive_rate) * 0.3)
        lethality = min(100, (bc_conversion / 70) * 50 + (shot_quality / 0.20) * 50)
        defense = max(0, 100 - ((xg_against / 1.3) * 25) - ((bc_conceded / 1.5) * 25))
        
        best_market = mkt['best_market']
        tendency = "OVER" if best_market in OVER_MARKETS else "UNDER" if best_market in UNDER_MARKETS else "NEUTRAL"
        
        return TeamMetrics(
            team_name=team_key,
            pace_index=pace,
            control_index=control,
            lethality_index=lethality,
            defensive_solidity=defense,
            xg_for=xg_for,
            xg_against=xg_against,
            best_market=best_market,
            best_market_roi=mkt['roi'],
            market_tendency=tendency
        )
        
    def analyze_match(self, home_name: str, away_name: str) -> Optional[MatchAnalysis]:
        """Analyse ADCM complète"""
        home = self.get_team_metrics(home_name)
        away = self.get_team_metrics(away_name)
        
        if not home or not away:
            return None
            
        # Expected goals (Dixon-Coles simplifié)
        lambda_h = math.sqrt(home.xg_for * away.xg_against) * 1.12
        lambda_a = math.sqrt(away.xg_for * home.xg_against)
        expected = lambda_h + lambda_a
        
        # Convergence
        if home.market_tendency == "OVER" and away.market_tendency == "OVER":
            conv, conv_type = 1.0, "OVER"
        elif home.market_tendency == "UNDER" and away.market_tendency == "UNDER":
            conv, conv_type = 1.0, "UNDER"
        elif (home.market_tendency == "OVER" and away.market_tendency == "UNDER") or \
             (home.market_tendency == "UNDER" and away.market_tendency == "OVER"):
            conv, conv_type = -0.5, "CLASH"
        else:
            conv, conv_type = 0.0, "NEUTRAL"
            
        # Scenario classification (priorité CONVERGENCE)
        total_pace = home.pace_index + away.pace_index
        avg_defense = (home.defensive_solidity + away.defensive_solidity) / 2
        control_diff = abs(home.control_index - away.control_index)
        
        scenario = Scenario.UNCERTAIN
        confidence = 40
        
        # PRIORITÉ 1: CONVERGENCE
        if conv > 0.5:
            if conv_type == "OVER":
                scenario = Scenario.CONVERGENCE_OVER
                confidence = min(95, 70 + (expected - 2.5) * 15) if expected >= 2.6 else 55
            elif conv_type == "UNDER":
                scenario = Scenario.CONVERGENCE_UNDER
                confidence = min(95, 70 + (2.7 - expected) * 20) if expected <= 2.6 else 50
                
        # PRIORITÉ 2: TOTAL CHAOS
        elif total_pace > 100 and avg_defense < 50 and expected > 3.2:
            scenario = Scenario.TOTAL_CHAOS
            confidence = min(95, 65 + (expected - 3.0) * 10)
            
        # PRIORITÉ 3: STYLE CLASH
        elif conv < 0:
            scenario = Scenario.STYLE_CLASH
            confidence = 55 if abs(home.pace_index - away.pace_index) > 15 else 45
            
        # PRIORITÉ 4: SIEGE
        elif control_diff > 20:
            scenario = Scenario.SIEGE
            confidence = min(85, 55 + control_diff * 0.8)
            
        # PRIORITÉ 5: SNIPER DUEL
        elif home.lethality_index > 55 and away.lethality_index > 55:
            scenario = Scenario.SNIPER_DUEL
            confidence = 65
            
        # PRIORITÉ 6: ATTRITION
        elif total_pace < 70 and expected < 2.3:
            scenario = Scenario.ATTRITION
            confidence = 60
            
        # Recommendations
        primary = 'over_25'
        edge = 10
        
        if scenario == Scenario.CONVERGENCE_OVER:
            primary = 'over_25'
            edge = min(30, 15 + (expected - 2.5) * 10)
        elif scenario == Scenario.CONVERGENCE_UNDER:
            primary = 'under_25'
            edge = min(30, 15 + (2.7 - expected) * 12)
        elif scenario == Scenario.TOTAL_CHAOS:
            primary = 'over_35' if expected > 3.5 else 'over_25'
            edge = min(25, (expected - 2.5) * 12)
        elif scenario == Scenario.STYLE_CLASH:
            leader = home if home.best_market_roi > away.best_market_roi else away
            primary = leader.best_market if leader.best_market in MARKET_ODDS else 'over_25'
            edge = 8
        elif scenario == Scenario.SIEGE:
            dominant = home if home.control_index > away.control_index else away
            primary = 'over_25' if dominant.market_tendency == "OVER" else 'under_25'
            edge = 12
        elif scenario == Scenario.SNIPER_DUEL:
            primary = 'btts_yes'
            edge = 18
        elif scenario == Scenario.ATTRITION:
            primary = 'under_25'
            edge = 15
            
        # Action
        if scenario in [Scenario.CONVERGENCE_OVER, Scenario.CONVERGENCE_UNDER] and confidence >= 70 and edge >= 18:
            action, stake = Action.SNIPER, 3.0
        elif scenario == Scenario.TOTAL_CHAOS and confidence >= 65:
            action, stake = Action.SNIPER, 2.5
        elif scenario == Scenario.STYLE_CLASH:
            action, stake = Action.SPECULATIVE, 1.0
        elif confidence >= 60 and edge >= 12:
            action, stake = Action.NORMAL, 2.0
        elif confidence < 50 or edge < 8:
            action, stake = Action.SKIP, 0
        else:
            action, stake = Action.NORMAL, 1.5
            
        return MatchAnalysis(
            home=home, away=away,
            scenario=scenario, confidence=confidence,
            expected_goals=expected, convergence=conv, conv_type=conv_type,
            primary_market=primary, primary_edge=edge,
            action=action, stake=stake
        )
        
    def evaluate_bet(self, match: dict, market: str) -> bool:
        """Évalue si le pari a gagné"""
        h = match['score_home'] or 0
        a = match['score_away'] or 0
        total = h + a
        both = h > 0 and a > 0
        
        return {
            'over_15': total >= 2, 'over_25': total >= 3, 'over_35': total >= 4,
            'under_15': total < 2, 'under_25': total < 3, 'under_35': total < 4,
            'btts_yes': both, 'btts_no': not both,
        }.get(market, False)
        
    def run_backtest(self):
        """Execute le backtest complet"""
        print("\n" + "="*90)
        print("�� BACKTEST ADCM 2.1 SUR 712 MATCHS")
        print("="*90)
        
        analyzed = 0
        
        for match in self.matches:
            analysis = self.analyze_match(match['home_team'], match['away_team'])
            
            if not analysis or analysis.action == Action.SKIP:
                continue
                
            analyzed += 1
            market = analysis.primary_market
            
            if market not in MARKET_ODDS:
                continue
                
            stake = analysis.stake
            odds = MARKET_ODDS[market]
            won = self.evaluate_bet(match, market)
            
            profit = stake * (odds - 1) if won else -stake
            
            # Record results
            action_key = analysis.action.value
            scenario_key = analysis.scenario.value
            
            self.results[action_key]['bets'] += 1
            self.results[action_key]['wins'] += 1 if won else 0
            self.results[action_key]['profit'] += profit
            self.results[action_key]['by_scenario'][scenario_key]['bets'] += 1
            self.results[action_key]['by_scenario'][scenario_key]['wins'] += 1 if won else 0
            self.results[action_key]['by_scenario'][scenario_key]['profit'] += profit
            
            self.results['ALL']['bets'] += 1
            self.results['ALL']['wins'] += 1 if won else 0
            self.results['ALL']['profit'] += profit
            self.results['ALL']['stake'] += stake
            
            self.scenario_stats[scenario_key]['bets'] += 1
            self.scenario_stats[scenario_key]['wins'] += 1 if won else 0
            self.scenario_stats[scenario_key]['profit'] += profit
            
        print(f"✅ {analyzed} matchs analysés (excl. SKIP)")
        
    def print_results(self):
        """Affiche les résultats"""
        print("\n" + "="*90)
        print("📊 RÉSULTATS BACKTEST ADCM 2.1")
        print("="*90)
        
        # Global
        all_r = self.results['ALL']
        if all_r['bets'] > 0:
            wr = (all_r['wins'] / all_r['bets']) * 100
            roi = (all_r['profit'] / all_r['stake']) * 100 if all_r['stake'] > 0 else 0
            
            print(f"\n🎯 PERFORMANCE GLOBALE ADCM 2.1:")
            print(f"   Paris: {all_r['bets']}")
            print(f"   Wins: {all_r['wins']}")
            print(f"   Win Rate: {wr:.1f}%")
            print(f"   ROI: {roi:+.1f}%")
            print(f"   P&L: {all_r['profit']:+.1f}u")
            
        # Par Action
        print(f"\n{'='*90}")
        print("📈 PERFORMANCE PAR TYPE D'ACTION:")
        print(f"{'='*90}")
        print(f"\n{'Action':<15} {'Paris':<8} {'Wins':<8} {'WR':<10} {'ROI':<12} {'P&L':<12}")
        print("-"*70)
        
        for action in ['SNIPER', 'NORMAL', 'SPECULATIVE']:
            r = self.results[action]
            if r['bets'] > 0:
                wr = (r['wins'] / r['bets']) * 100
                avg_stake = 3.0 if action == 'SNIPER' else 2.0 if action == 'NORMAL' else 1.0
                roi = (r['profit'] / (r['bets'] * avg_stake)) * 100
                emoji = "🎯" if action == "SNIPER" else "✅" if action == "NORMAL" else "⚠️"
                print(f"{emoji} {action:<13} {r['bets']:<8} {r['wins']:<8} {wr:.1f}%{'':<5} {roi:+.1f}%{'':<6} {r['profit']:+.1f}u")
                
        # Par Scenario
        print(f"\n{'='*90}")
        print("📊 PERFORMANCE PAR SCÉNARIO:")
        print(f"{'='*90}")
        print(f"\n{'Scenario':<25} {'Paris':<8} {'Wins':<8} {'WR':<10} {'P&L':<12}")
        print("-"*70)
        
        sorted_scenarios = sorted(self.scenario_stats.items(), key=lambda x: x[1]['profit'], reverse=True)
        
        for scenario, stats in sorted_scenarios:
            if stats['bets'] > 0:
                wr = (stats['wins'] / stats['bets']) * 100
                emoji = "💎" if stats['profit'] > 20 else "✅" if stats['profit'] > 0 else "❌"
                print(f"{emoji} {scenario:<23} {stats['bets']:<8} {stats['wins']:<8} {wr:.1f}%{'':<5} {stats['profit']:+.1f}u")
                
        # Comparaison
        print(f"\n{'='*90}")
        print("�� COMPARAISON AVEC AUTRES STRATÉGIES:")
        print(f"{'='*90}")
        
        all_r = self.results['ALL']
        if all_r['bets'] > 0:
            wr = (all_r['wins'] / all_r['bets']) * 100
            roi = (all_r['profit'] / all_r['stake']) * 100
            
            print(f"\n{'Stratégie':<25} {'Paris':<10} {'WR':<12} {'ROI':<14} {'P&L':<12}")
            print("-"*75)
            print(f"{'🧠 ADCM 2.1':<25} {all_r['bets']:<10} {wr:.1f}%{'':<7} {roi:+.1f}%{'':<8} {all_r['profit']:+.1f}u")
            print(f"{'🚀 Adaptive Engine':<25} {'351':<10} {'69.8%':<12} {'+48.3%':<14} {'+372.8u':<12}")
            print(f"{'⭐ V13 Reference':<25} {'204':<10} {'76.5%':<12} {'+53.2%':<14} {'+210.7u':<12}")
            print(f"{'📊 COMBINED':<25} {'867':<10} {'68.9%':<12} {'+32.5%':<14} {'+739.4u':<12}")
            
        # Save results
        with open('adcm_backtest_results.json', 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'global': {
                    'bets': all_r['bets'],
                    'wins': all_r['wins'],
                    'profit': round(all_r['profit'], 1),
                    'stake': round(all_r['stake'], 1)
                },
                'by_action': {k: {'bets': v['bets'], 'wins': v['wins'], 'profit': round(v['profit'], 1)} 
                             for k, v in self.results.items() if k != 'ALL'},
                'by_scenario': {k: {'bets': v['bets'], 'wins': v['wins'], 'profit': round(v['profit'], 1)} 
                               for k, v in self.scenario_stats.items()}
            }, f, indent=2)
            
        print("\n✅ Résultats sauvegardés dans adcm_backtest_results.json")


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║     🧪 ADCM 2.1 BACKTEST - VALIDATION SCIENTIFIQUE                            ║
║                                                                               ║
║  Test sur 712 matchs Sept-Déc 2025                                            ║
║  Comparaison avec V13, Adaptive Engine, COMBINED                              ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    backtest = ADCMBacktest()
    backtest.connect()
    backtest.load_data()
    backtest.run_backtest()
    backtest.print_results()


if __name__ == "__main__":
    main()
