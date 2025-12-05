#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║     🔬 AUDIT COMPLET SCIENTIFIQUE PAR ÉQUIPE                                  ║
║                                                                               ║
║  Pour CHAQUE équipe, teste TOUTES les stratégies:                             ║
║  • ADCM 2.1 (Convergence Over/Under, Style Clash, etc.)                       ║
║  • Adaptive Engine                                                            ║
║  • Monte Carlo + ADCM                                                         ║
║  • Team Market Profile (QUANT)                                                ║
║                                                                               ║
║  Output:                                                                      ║
║  • Meilleure stratégie PAR ÉQUIPE                                             ║
║  • Analyse des pertes (malchance vs mauvaise analyse)                         ║
║  • Top équipes par stratégie                                                  ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
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


@dataclass
class TeamMetrics:
    team_name: str
    pace_index: float = 50.0
    control_index: float = 50.0
    lethality_index: float = 50.0
    defensive_solidity: float = 50.0
    xg_for: float = 1.3
    xg_against: float = 1.3
    best_market: str = 'over_25'
    best_market_roi: float = 0.0
    market_tendency: str = 'NEUTRAL'


@dataclass
class BetResult:
    match_id: str
    home_team: str
    away_team: str
    team_analyzed: str
    strategy: str
    scenario: str
    market: str
    stake: float
    odds: float
    won: bool
    profit: float
    expected_goals: float
    actual_goals: int
    loss_reason: str = ""  # "UNLUCKY" or "BAD_ANALYSIS" or ""


@dataclass
class TeamAudit:
    team_name: str
    league: str = ""
    
    # Par stratégie
    strategies: Dict[str, Dict] = field(default_factory=dict)
    
    # Meilleure stratégie
    best_strategy: str = ""
    best_strategy_wr: float = 0.0
    best_strategy_roi: float = 0.0
    best_strategy_profit: float = 0.0
    
    # Détail des paris
    all_bets: List[BetResult] = field(default_factory=list)
    
    # Analyse des pertes
    total_losses: int = 0
    unlucky_losses: int = 0  # xG supportait le pari
    bad_analysis_losses: int = 0  # xG ne supportait pas


class ComprehensiveAudit:
    """Audit complet par équipe"""
    
    STRATEGIES = [
        'CONVERGENCE_OVER',
        'CONVERGENCE_UNDER', 
        'TOTAL_CHAOS',
        'ADCM_SNIPER',
        'ADCM_NORMAL',
        'ADAPTIVE_ENGINE',
        'QUANT_BEST_MARKET',
        'MONTE_CARLO_ADCM'
    ]
    
    def __init__(self):
        self.conn = None
        self.team_data = {}
        self.market_profiles = {}
        self.matches = []
        self.team_audits: Dict[str, TeamAudit] = {}
        
    def connect(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connexion DB établie")
        
    def load_data(self):
        """Charge toutes les données"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # XG Tendencies
            cur.execute("SELECT * FROM team_xg_tendencies")
            xg_data = {r['team_name']: r for r in cur.fetchall()}
            
            # Big Chances
            cur.execute("SELECT * FROM team_big_chances_tendencies")
            bc_data = {r['team_name']: r for r in cur.fetchall()}
            
            # Market Profiles (tous les marchés, pas juste best)
            cur.execute("""
                SELECT team_name, market_type, roi, win_rate, sample_size, is_best_market
                FROM team_market_profiles
                WHERE sample_size >= 5
            """)
            for r in cur.fetchall():
                team = r['team_name']
                if team not in self.market_profiles:
                    self.market_profiles[team] = {}
                self.market_profiles[team][r['market_type']] = {
                    'roi': float(r['roi'] or 0),
                    'wr': float(r['win_rate'] or 0),
                    'sample': r['sample_size'],
                    'is_best': r['is_best_market']
                }
                
            # Merge team data
            for team in set(xg_data.keys()) | set(bc_data.keys()):
                xg = xg_data.get(team, {})
                bc = bc_data.get(team, {})
                
                # Find best market
                best_market = 'over_25'
                best_roi = 0
                if team in self.market_profiles:
                    for mkt, data in self.market_profiles[team].items():
                        if data.get('is_best') and data['roi'] > best_roi:
                            best_market = mkt
                            best_roi = data['roi']
                            
                self.team_data[team] = {
                    'xg': xg,
                    'bc': bc,
                    'best_market': best_market,
                    'best_roi': best_roi,
                    'league': xg.get('league', 'Unknown')
                }
                
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
        
        xg_for = float(xg.get('avg_xg_for') or 1.3)
        xg_against = float(xg.get('avg_xg_against') or 1.3)
        bc_created = float(bc.get('avg_bc_created') or 1.5)
        bc_conceded = float(bc.get('avg_bc_conceded') or 1.5)
        bc_conversion = float(bc.get('bc_conversion_rate') or 45)
        shot_quality = float(bc.get('avg_shot_quality') or 0.12)
        open_rate = float(xg.get('open_rate') or 50)
        defensive_rate = float(xg.get('defensive_rate') or 50)
        
        pace = min(100, ((xg_for / 1.3) * 30) + ((bc_created / 1.5) * 20))
        control = (open_rate * 0.7) + ((100 - defensive_rate) * 0.3)
        lethality = min(100, (bc_conversion / 70) * 50 + (shot_quality / 0.20) * 50)
        defense = max(0, 100 - ((xg_against / 1.3) * 25) - ((bc_conceded / 1.5) * 25))
        
        best_market = data['best_market']
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
            best_market_roi=data['best_roi'],
            market_tendency=tendency
        )
        
    def evaluate_market(self, match: dict, market: str) -> bool:
        """Évalue si un marché a gagné"""
        h = match['score_home'] or 0
        a = match['score_away'] or 0
        total = h + a
        both = h > 0 and a > 0
        
        return {
            'over_25': total >= 3, 'over_35': total >= 4, 'over_15': total >= 2,
            'under_25': total < 3, 'under_35': total < 4, 'under_15': total < 2,
            'btts_yes': both, 'btts_no': not both,
        }.get(market, False)
        
    def calculate_expected_goals(self, home: TeamMetrics, away: TeamMetrics) -> float:
        """Calcule xG attendu"""
        lambda_h = math.sqrt(home.xg_for * away.xg_against) * 1.12
        lambda_a = math.sqrt(away.xg_for * home.xg_against)
        return lambda_h + lambda_a
        
    def monte_carlo_simulation(self, home: TeamMetrics, away: TeamMetrics, n_sims: int = 1000) -> Dict:
        """Simulation Monte Carlo pour le match"""
        import random
        
        lambda_h = math.sqrt(home.xg_for * away.xg_against) * 1.12
        lambda_a = math.sqrt(away.xg_for * home.xg_against)
        
        over25_count = 0
        over35_count = 0
        under25_count = 0
        btts_count = 0
        
        for _ in range(n_sims):
            # Poisson simulation
            home_goals = 0
            away_goals = 0
            
            # Simple Poisson approximation
            p_h = math.exp(-lambda_h)
            p_a = math.exp(-lambda_a)
            
            for k in range(10):
                if random.random() < (lambda_h ** k * math.exp(-lambda_h) / math.factorial(k)):
                    home_goals = k
                    break
            for k in range(10):
                if random.random() < (lambda_a ** k * math.exp(-lambda_a) / math.factorial(k)):
                    away_goals = k
                    break
                    
            total = home_goals + away_goals
            if total >= 3:
                over25_count += 1
            if total >= 4:
                over35_count += 1
            if total < 3:
                under25_count += 1
            if home_goals > 0 and away_goals > 0:
                btts_count += 1
                
        return {
            'over_25_prob': over25_count / n_sims,
            'over_35_prob': over35_count / n_sims,
            'under_25_prob': under25_count / n_sims,
            'btts_yes_prob': btts_count / n_sims,
            'expected_goals': lambda_h + lambda_a
        }
        
    def analyze_loss_reason(self, bet: BetResult) -> str:
        """Analyse pourquoi un pari a été perdu"""
        if bet.won:
            return ""
            
        # Si le marché était Over et xG > 2.8 mais moins de 3 buts = UNLUCKY
        if bet.market == 'over_25':
            if bet.expected_goals >= 2.8 and bet.actual_goals < 3:
                return "UNLUCKY"  # xG supportait, variance négative
            else:
                return "BAD_ANALYSIS"  # xG ne supportait pas vraiment
                
        elif bet.market == 'under_25':
            if bet.expected_goals <= 2.4 and bet.actual_goals >= 3:
                return "UNLUCKY"
            else:
                return "BAD_ANALYSIS"
                
        elif bet.market == 'btts_yes':
            if bet.expected_goals >= 2.5:
                return "UNLUCKY"
            else:
                return "BAD_ANALYSIS"
                
        elif bet.market == 'btts_no':
            if bet.expected_goals <= 2.3:
                return "UNLUCKY"
            else:
                return "BAD_ANALYSIS"
                
        return "UNKNOWN"
        
    def get_strategy_decision(self, home: TeamMetrics, away: TeamMetrics, 
                              team: TeamMetrics, strategy: str) -> Optional[Tuple[str, float, str]]:
        """
        Pour une équipe et une stratégie, retourne (market, stake, scenario)
        """
        expected = self.calculate_expected_goals(home, away)
        
        home_over = home.market_tendency == "OVER"
        away_over = away.market_tendency == "OVER"
        home_under = home.market_tendency == "UNDER"
        away_under = away.market_tendency == "UNDER"
        
        convergence_over = home_over and away_over
        convergence_under = home_under and away_under
        style_clash = (home_over and away_under) or (home_under and away_over)
        
        total_pace = home.pace_index + away.pace_index
        avg_defense = (home.defensive_solidity + away.defensive_solidity) / 2
        
        if strategy == 'CONVERGENCE_OVER':
            if convergence_over and expected >= 2.5:
                return ('over_25', 3.0, 'CONVERGENCE_OVER')
            return None
            
        elif strategy == 'CONVERGENCE_UNDER':
            if convergence_under and expected <= 2.7:
                return ('under_25', 3.0, 'CONVERGENCE_UNDER')
            return None
            
        elif strategy == 'TOTAL_CHAOS':
            if total_pace > 100 and avg_defense < 50 and expected > 3.2:
                return ('over_35' if expected > 3.5 else 'over_25', 2.5, 'TOTAL_CHAOS')
            return None
            
        elif strategy == 'ADCM_SNIPER':
            # SNIPER = Convergence + High confidence
            if convergence_over and expected >= 2.8:
                return ('over_25', 3.0, 'ADCM_SNIPER')
            if convergence_under and expected <= 2.3:
                return ('under_25', 3.0, 'ADCM_SNIPER')
            return None
            
        elif strategy == 'ADCM_NORMAL':
            # NORMAL = Convergence avec moins de confiance
            if convergence_over and expected >= 2.5:
                return ('over_25', 2.0, 'ADCM_NORMAL')
            if convergence_under and expected <= 2.7:
                return ('under_25', 2.0, 'ADCM_NORMAL')
            if home.lethality_index > 55 and away.lethality_index > 55:
                return ('btts_yes', 2.0, 'SNIPER_DUEL')
            return None
            
        elif strategy == 'ADAPTIVE_ENGINE':
            # Suit le best_market de l'équipe si ROI >= 20%
            if team.best_market_roi >= 20:
                if team.best_market in MARKET_ODDS:
                    return (team.best_market, 2.0, 'ADAPTIVE')
            return None
            
        elif strategy == 'QUANT_BEST_MARKET':
            # Suit le best_market de l'équipe si ROI >= 30% ET WR >= 65%
            team_name = team.team_name
            if team_name in self.market_profiles:
                for mkt, data in self.market_profiles[team_name].items():
                    if data.get('is_best') and data['roi'] >= 30 and data['wr'] >= 65:
                        if mkt in MARKET_ODDS:
                            return (mkt, 2.5, 'QUANT')
            return None
            
        elif strategy == 'MONTE_CARLO_ADCM':
            # Monte Carlo + ADCM combiné
            mc = self.monte_carlo_simulation(home, away, 500)
            
            # Si convergence + MC confirme
            if convergence_over and mc['over_25_prob'] >= 0.60:
                return ('over_25', 3.0, 'MC_CONVERGENCE_OVER')
            if convergence_under and mc['under_25_prob'] >= 0.55:
                return ('under_25', 3.0, 'MC_CONVERGENCE_UNDER')
            # MC seul si très fort signal
            if mc['over_25_prob'] >= 0.70:
                return ('over_25', 2.0, 'MC_HIGH_PROB')
            if mc['under_25_prob'] >= 0.65:
                return ('under_25', 2.0, 'MC_HIGH_PROB')
            return None
            
        return None
        
    def run_audit(self):
        """Exécute l'audit complet par équipe"""
        print("\n" + "="*100)
        print("🔬 AUDIT COMPLET PAR ÉQUIPE - TOUTES STRATÉGIES")
        print("="*100)
        
        # Initialiser les audits pour chaque équipe
        for team_name, data in self.team_data.items():
            self.team_audits[team_name] = TeamAudit(
                team_name=team_name,
                league=data.get('league', 'Unknown'),
                strategies={s: {'bets': 0, 'wins': 0, 'profit': 0, 'stake': 0} for s in self.STRATEGIES}
            )
            
        match_count = 0
        
        for match in self.matches:
            home_metrics = self.get_team_metrics(match['home_team'])
            away_metrics = self.get_team_metrics(match['away_team'])
            
            if not home_metrics or not away_metrics:
                continue
                
            match_count += 1
            actual_goals = (match['score_home'] or 0) + (match['score_away'] or 0)
            expected_goals = self.calculate_expected_goals(home_metrics, away_metrics)
            
            # Tester chaque équipe du match avec chaque stratégie
            for team_metrics, team_name in [(home_metrics, home_metrics.team_name), 
                                             (away_metrics, away_metrics.team_name)]:
                
                if team_name not in self.team_audits:
                    continue
                    
                audit = self.team_audits[team_name]
                
                for strategy in self.STRATEGIES:
                    decision = self.get_strategy_decision(home_metrics, away_metrics, team_metrics, strategy)
                    
                    if not decision:
                        continue
                        
                    market, stake, scenario = decision
                    odds = MARKET_ODDS.get(market, 1.85)
                    won = self.evaluate_market(match, market)
                    profit = stake * (odds - 1) if won else -stake
                    
                    # Enregistrer
                    audit.strategies[strategy]['bets'] += 1
                    audit.strategies[strategy]['wins'] += 1 if won else 0
                    audit.strategies[strategy]['profit'] += profit
                    audit.strategies[strategy]['stake'] += stake
                    
                    # Créer le détail du pari
                    bet = BetResult(
                        match_id=match['match_id'],
                        home_team=match['home_team'],
                        away_team=match['away_team'],
                        team_analyzed=team_name,
                        strategy=strategy,
                        scenario=scenario,
                        market=market,
                        stake=stake,
                        odds=odds,
                        won=won,
                        profit=profit,
                        expected_goals=expected_goals,
                        actual_goals=actual_goals
                    )
                    
                    if not won:
                        bet.loss_reason = self.analyze_loss_reason(bet)
                        audit.total_losses += 1
                        if bet.loss_reason == "UNLUCKY":
                            audit.unlucky_losses += 1
                        elif bet.loss_reason == "BAD_ANALYSIS":
                            audit.bad_analysis_losses += 1
                            
                    audit.all_bets.append(bet)
                    
        # Déterminer la meilleure stratégie pour chaque équipe
        for team_name, audit in self.team_audits.items():
            best_roi = -999
            best_strategy = ""
            
            for strategy, stats in audit.strategies.items():
                if stats['bets'] >= 3:  # Minimum 3 paris
                    roi = (stats['profit'] / stats['stake']) * 100 if stats['stake'] > 0 else 0
                    if roi > best_roi:
                        best_roi = roi
                        best_strategy = strategy
                        
            if best_strategy:
                audit.best_strategy = best_strategy
                stats = audit.strategies[best_strategy]
                audit.best_strategy_wr = (stats['wins'] / stats['bets']) * 100 if stats['bets'] > 0 else 0
                audit.best_strategy_roi = best_roi
                audit.best_strategy_profit = stats['profit']
                
        print(f"✅ {match_count} matchs analysés")
        print(f"✅ {len(self.team_audits)} équipes auditées")
        
    def print_results(self):
        """Affiche les résultats détaillés"""
        
        # ═══════════════════════════════════════════════════════════════════════
        # 1. TOP ÉQUIPES PAR STRATÉGIE
        # ═══════════════════════════════════════════════════════════════════════
        print("\n" + "="*120)
        print("🏆 TOP 10 ÉQUIPES PAR STRATÉGIE")
        print("="*120)
        
        for strategy in self.STRATEGIES:
            teams_for_strategy = []
            for team_name, audit in self.team_audits.items():
                stats = audit.strategies[strategy]
                if stats['bets'] >= 3:
                    wr = (stats['wins'] / stats['bets']) * 100
                    roi = (stats['profit'] / stats['stake']) * 100 if stats['stake'] > 0 else 0
                    teams_for_strategy.append({
                        'team': team_name,
                        'bets': stats['bets'],
                        'wins': stats['wins'],
                        'wr': wr,
                        'roi': roi,
                        'profit': stats['profit']
                    })
                    
            if teams_for_strategy:
                teams_for_strategy.sort(key=lambda x: x['profit'], reverse=True)
                
                print(f"\n📊 {strategy}:")
                print(f"{'#':<3} {'Équipe':<25} {'Paris':<8} {'Wins':<8} {'WR':<10} {'ROI':<12} {'P&L':<10}")
                print("-"*80)
                
                for i, t in enumerate(teams_for_strategy[:10], 1):
                    emoji = "💎" if t['profit'] >= 20 else "✅" if t['profit'] > 0 else "❌"
                    print(f"{emoji}{i:<2} {t['team'][:24]:<25} {t['bets']:<8} {t['wins']:<8} {t['wr']:.1f}%{'':<5} {t['roi']:+.1f}%{'':<6} {t['profit']:+.1f}u")
                    
        # ═══════════════════════════════════════════════════════════════════════
        # 2. MEILLEURE STRATÉGIE PAR ÉQUIPE
        # ═══════════════════════════════════════════════════════════════════════
        print("\n" + "="*120)
        print("🎯 MEILLEURE STRATÉGIE PAR ÉQUIPE (Top 30)")
        print("="*120)
        
        team_list = []
        for team_name, audit in self.team_audits.items():
            if audit.best_strategy and audit.best_strategy_profit > 0:
                team_list.append({
                    'team': team_name,
                    'league': audit.league,
                    'strategy': audit.best_strategy,
                    'wr': audit.best_strategy_wr,
                    'roi': audit.best_strategy_roi,
                    'profit': audit.best_strategy_profit,
                    'losses': audit.total_losses,
                    'unlucky': audit.unlucky_losses,
                    'bad': audit.bad_analysis_losses
                })
                
        team_list.sort(key=lambda x: x['profit'], reverse=True)
        
        print(f"\n{'#':<3} {'Équipe':<22} {'Ligue':<15} {'Best Strategy':<20} {'WR':<10} {'ROI':<12} {'P&L':<10} {'Pertes':<8} {'Malch.':<8} {'Err.':<6}")
        print("-"*130)
        
        for i, t in enumerate(team_list[:30], 1):
            emoji = "💎" if t['profit'] >= 30 else "✅" if t['profit'] >= 10 else "⚠️"
            print(f"{emoji}{i:<2} {t['team'][:21]:<22} {t['league'][:14]:<15} {t['strategy'][:19]:<20} {t['wr']:.1f}%{'':<5} {t['roi']:+.1f}%{'':<6} {t['profit']:+.1f}u{'':<4} {t['losses']:<8} {t['unlucky']:<8} {t['bad']:<6}")
            
        # ═══════════════════════════════════════════════════════════════════════
        # 3. ÉQUIPES À ÉVITER
        # ═══════════════════════════════════════════════════════════════════════
        print("\n" + "="*120)
        print("⚠️ ÉQUIPES À ÉVITER (Toutes stratégies négatives)")
        print("="*120)
        
        avoid_teams = []
        for team_name, audit in self.team_audits.items():
            all_negative = True
            total_bets = 0
            total_profit = 0
            
            for strategy, stats in audit.strategies.items():
                if stats['bets'] > 0:
                    total_bets += stats['bets']
                    total_profit += stats['profit']
                    if stats['profit'] > 0:
                        all_negative = False
                        
            if all_negative and total_bets >= 5:
                avoid_teams.append({
                    'team': team_name,
                    'bets': total_bets,
                    'profit': total_profit,
                    'bad_analyses': audit.bad_analysis_losses
                })
                
        avoid_teams.sort(key=lambda x: x['profit'])
        
        print(f"\n{'Équipe':<30} {'Paris':<10} {'P&L':<12} {'Mauvaises Analyses':<20}")
        print("-"*75)
        
        for t in avoid_teams[:15]:
            print(f"❌ {t['team'][:28]:<30} {t['bets']:<10} {t['profit']:+.1f}u{'':<6} {t['bad_analyses']:<20}")
            
        # ═══════════════════════════════════════════════════════════════════════
        # 4. ANALYSE DES PERTES
        # ═══════════════════════════════════════════════════════════════════════
        print("\n" + "="*120)
        print("📉 ANALYSE DES PERTES - MALCHANCE vs MAUVAISE ANALYSE")
        print("="*120)
        
        total_losses = 0
        total_unlucky = 0
        total_bad = 0
        
        for audit in self.team_audits.values():
            total_losses += audit.total_losses
            total_unlucky += audit.unlucky_losses
            total_bad += audit.bad_analysis_losses
            
        if total_losses > 0:
            print(f"\n📊 GLOBAL:")
            print(f"   Total pertes: {total_losses}")
            print(f"   🎲 Malchance (xG supportait): {total_unlucky} ({total_unlucky/total_losses*100:.1f}%)")
            print(f"   ❌ Mauvaise analyse: {total_bad} ({total_bad/total_losses*100:.1f}%)")
            
        # Par stratégie
        print(f"\n�� PAR STRATÉGIE:")
        print(f"{'Stratégie':<25} {'Pertes':<10} {'Malchance':<12} {'%':<8} {'Mauvaise':<12} {'%':<8}")
        print("-"*80)
        
        for strategy in self.STRATEGIES:
            strat_losses = 0
            strat_unlucky = 0
            strat_bad = 0
            
            for audit in self.team_audits.values():
                for bet in audit.all_bets:
                    if bet.strategy == strategy and not bet.won:
                        strat_losses += 1
                        if bet.loss_reason == "UNLUCKY":
                            strat_unlucky += 1
                        elif bet.loss_reason == "BAD_ANALYSIS":
                            strat_bad += 1
                            
            if strat_losses > 0:
                unlucky_pct = strat_unlucky / strat_losses * 100
                bad_pct = strat_bad / strat_losses * 100
                print(f"{strategy:<25} {strat_losses:<10} {strat_unlucky:<12} {unlucky_pct:.1f}%{'':<3} {strat_bad:<12} {bad_pct:.1f}%")
                
        # ═══════════════════════════════════════════════════════════════════════
        # 5. SYNTHÈSE GLOBALE PAR STRATÉGIE
        # ═══════════════════════════════════════════════════════════════════════
        print("\n" + "="*120)
        print("📈 SYNTHÈSE GLOBALE PAR STRATÉGIE")
        print("="*120)
        
        strategy_totals = {s: {'bets': 0, 'wins': 0, 'profit': 0, 'stake': 0} for s in self.STRATEGIES}
        
        for audit in self.team_audits.values():
            for strategy, stats in audit.strategies.items():
                strategy_totals[strategy]['bets'] += stats['bets']
                strategy_totals[strategy]['wins'] += stats['wins']
                strategy_totals[strategy]['profit'] += stats['profit']
                strategy_totals[strategy]['stake'] += stats['stake']
                
        print(f"\n{'Stratégie':<25} {'Paris':<10} {'Wins':<10} {'WR':<12} {'ROI':<14} {'P&L':<12}")
        print("-"*90)
        
        sorted_strategies = sorted(strategy_totals.items(), key=lambda x: x[1]['profit'], reverse=True)
        
        for strategy, stats in sorted_strategies:
            if stats['bets'] > 0:
                wr = (stats['wins'] / stats['bets']) * 100
                roi = (stats['profit'] / stats['stake']) * 100 if stats['stake'] > 0 else 0
                emoji = "🏆" if stats == sorted_strategies[0][1] else "💎" if stats['profit'] > 100 else "✅" if stats['profit'] > 0 else "❌"
                print(f"{emoji} {strategy:<23} {stats['bets']:<10} {stats['wins']:<10} {wr:.1f}%{'':<7} {roi:+.1f}%{'':<8} {stats['profit']:+.1f}u")
                
        # ═══════════════════════════════════════════════════════════════════════
        # 6. RECOMMANDATIONS FINALES
        # ═══════════════════════════════════════════════════════════════════════
        print("\n" + "="*120)
        print("💡 RECOMMANDATIONS FINALES")
        print("="*120)
        
        # Compter équipes par meilleure stratégie
        strategy_count = defaultdict(int)
        for audit in self.team_audits.values():
            if audit.best_strategy:
                strategy_count[audit.best_strategy] += 1
                
        print(f"\n📊 Répartition des équipes par meilleure stratégie:")
        for strategy, count in sorted(strategy_count.items(), key=lambda x: x[1], reverse=True):
            print(f"   {strategy}: {count} équipes")
            
        # Save to JSON
        output = {
            'timestamp': datetime.now().isoformat(),
            'teams': {}
        }
        
        for team_name, audit in self.team_audits.items():
            if audit.best_strategy:
                output['teams'][team_name] = {
                    'league': audit.league,
                    'best_strategy': audit.best_strategy,
                    'wr': round(audit.best_strategy_wr, 1),
                    'roi': round(audit.best_strategy_roi, 1),
                    'profit': round(audit.best_strategy_profit, 1),
                    'total_losses': audit.total_losses,
                    'unlucky_losses': audit.unlucky_losses,
                    'bad_analysis_losses': audit.bad_analysis_losses,
                    'all_strategies': {
                        s: {
                            'bets': v['bets'],
                            'wins': v['wins'],
                            'profit': round(v['profit'], 1)
                        } for s, v in audit.strategies.items() if v['bets'] > 0
                    }
                }
                
        with open('audit_complet_par_equipe.json', 'w') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
            
        print("\n✅ Résultats sauvegardés dans audit_complet_par_equipe.json")


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║     🔬 AUDIT COMPLET SCIENTIFIQUE PAR ÉQUIPE                                  ║
║                                                                               ║
║  Test de TOUTES les stratégies sur CHAQUE équipe:                             ║
║  • CONVERGENCE_OVER / CONVERGENCE_UNDER                                       ║
║  • TOTAL_CHAOS                                                                ║
║  • ADCM_SNIPER / ADCM_NORMAL                                                  ║
║  • ADAPTIVE_ENGINE                                                            ║
║  • QUANT_BEST_MARKET                                                          ║
║  • MONTE_CARLO_ADCM (nouveau!)                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    audit = ComprehensiveAudit()
    audit.connect()
    audit.load_data()
    audit.run_audit()
    audit.print_results()


if __name__ == "__main__":
    main()
