#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║     🏆 AUDIT QUANT 2.0 FINAL - ANALYSE GRANULAIRE PAR ÉQUIPE (V2 CORRIGÉE)                                   ║
║                                                                                                               ║
║  ✅ Basé sur tracking_clv_picks (vrais paris résolus)                                                        ║
║  ✅ 44 Stratégies × Toutes Équipes × Système TIER                                                            ║
║  ✅ team_intelligence + matches_results                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Dict, Optional, List
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
    'under_25': 2.00, 'under_35': 1.55, 'under_15': 3.50,
    'btts_yes': 1.80, 'btts_no': 2.00, 'home': 2.00, 'away': 2.50, 'draw': 3.20
}

TIER_STAKES = {
    'TIER_1_SNIPER': 4.0,
    'TIER_2_ELITE': 3.0,
    'TIER_3_GOLD': 2.5,
    'TIER_4_STANDARD': 2.0,
    'TIER_5_EXPERIMENTAL': 1.0,
}

ALL_STRATEGIES = [
    # CONVERGENCE
    'CONVERGENCE_XG_HIGH', 'CONVERGENCE_XG_MEDIUM',
    # MONTE CARLO / PROBABILITY
    'PROB_HIGH_40', 'PROB_MEDIUM_30', 'PROB_LOW_25',
    # DIAMOND SCORE
    'DIAMOND_SNIPER_30', 'DIAMOND_HIGH_25', 'DIAMOND_GOOD_20', 'DIAMOND_MEDIUM_15',
    # QUANT MARKET
    'QUANT_BEST_MARKET', 'QUANT_ROI_25', 'QUANT_ROI_30', 'QUANT_ROI_40', 'QUANT_ROI_50',
    # XG SCORING
    'XG_SNIPER_4', 'XG_HIGH_35', 'XG_GOOD_3', 'XG_MEDIUM_25',
    # TACTICAL STYLES
    'STYLE_OFFENSIVE', 'STYLE_ATTACKING', 'STYLE_BALANCED_OFFENSIVE',
    # MARKET TYPES
    'MARKET_OVER25', 'MARKET_UNDER25', 'MARKET_BTTS', 'MARKET_HOME', 'MARKET_AWAY',
    # LEAGUE PATTERNS
    'LEAGUE_TOP', 'LEAGUE_TIER1', 'LEAGUE_TIER2',
    # SPECIAL MARKETS
    'UNDER_35_PURE', 'OVER_15_SAFE', 'BTTS_NO_PURE',
    # VALUE RATING
    'VALUE_STRONG', 'VALUE_GOOD', 'VALUE_MARGINAL',
    # EDGE DETECTION
    'EDGE_POSITIVE', 'EDGE_HIGH_5', 'EDGE_MEDIUM_0',
    # COMBOS
    'COMBO_DIAMOND_XG', 'COMBO_PROB_VALUE', 'TRIPLE_VALIDATION',
    # TIERS
    'TIER_1_SNIPER', 'TIER_2_ELITE', 'TIER_3_GOLD', 'TIER_4_STANDARD',
    # ULTIMATE
    'ULTIMATE_SNIPER', 'ULTIMATE_HYBRID',
]

@dataclass
class TeamProfile:
    name: str
    current_style: str = 'balanced'
    home_over25_rate: float = 0.0
    away_over25_rate: float = 0.0
    home_btts_rate: float = 0.0
    away_btts_rate: float = 0.0
    goals_tendency: int = 50
    btts_tendency: int = 50
    home_strength: int = 50
    away_strength: int = 50
    total_matches: int = 0
    historical_wr: float = 0.0
    historical_roi: float = 0.0
    best_market: str = 'over_25'

@dataclass
class PickData:
    pick_id: int
    match_id: str
    match_name: str
    home_team: str
    away_team: str
    market_type: str
    prediction: str
    odds_taken: float
    is_resolved: bool
    is_winner: bool
    profit_loss: float
    diamond_score: int
    probability: float
    home_xg: float
    away_xg: float
    total_xg: float
    score_home: int
    score_away: int
    total_goals: int
    value_rating: str
    edge_pct: float
    source: str
    league: str

@dataclass
class StrategyStats:
    name: str
    total_bets: int = 0
    wins: int = 0
    losses: int = 0
    profit: float = 0.0
    unlucky_losses: int = 0
    bad_losses: int = 0
    
    @property
    def win_rate(self) -> float:
        return (self.wins / self.total_bets * 100) if self.total_bets > 0 else 0
    
    @property
    def roi(self) -> float:
        return (self.profit / self.total_bets * 100) if self.total_bets > 0 else 0


class QuantAuditFinal:
    def __init__(self):
        self.conn = None
        self.team_profiles: Dict[str, TeamProfile] = {}
        self.picks: List[PickData] = []
        self.team_results: Dict[str, Dict[str, StrategyStats]] = defaultdict(lambda: defaultdict(lambda: StrategyStats(name='')))
        self.global_results: Dict[str, StrategyStats] = {s: StrategyStats(name=s) for s in ALL_STRATEGIES}
        self.all_bets = []
    
    def connect(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.conn.autocommit = True
        print("✅ Connexion DB établie")
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def load_team_intelligence(self):
        """Charge les profils depuis team_intelligence"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT team_name, current_style, current_form,
                       home_over25_rate, away_over25_rate, home_btts_rate, away_btts_rate,
                       goals_tendency, btts_tendency, home_strength, away_strength
                FROM team_intelligence WHERE team_name IS NOT NULL
            """)
            for row in cur.fetchall():
                profile = TeamProfile(
                    name=row['team_name'],
                    current_style=row['current_style'] or 'balanced',
                    home_over25_rate=float(row['home_over25_rate'] or 0),
                    away_over25_rate=float(row['away_over25_rate'] or 0),
                    home_btts_rate=float(row['home_btts_rate'] or 0),
                    away_btts_rate=float(row['away_btts_rate'] or 0),
                    goals_tendency=int(row['goals_tendency'] or 50),
                    btts_tendency=int(row['btts_tendency'] or 50),
                    home_strength=int(row['home_strength'] or 50),
                    away_strength=int(row['away_strength'] or 50),
                )
                self.team_profiles[row['team_name']] = profile
            print(f"✅ {len(self.team_profiles)} profils d'équipes chargés")
    
    def load_picks(self):
        """Charge les paris résolus depuis tracking_clv_picks"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, match_id, match_name, home_team, away_team,
                       market_type, prediction, odds_taken,
                       is_resolved, is_winner, profit_loss,
                       diamond_score, probability,
                       home_xg, away_xg, total_xg,
                       score_home, score_away,
                       value_rating, edge_pct, source, league
                FROM tracking_clv_picks 
                WHERE is_resolved = true
                  AND home_team IS NOT NULL AND away_team IS NOT NULL
                ORDER BY created_at DESC
            """)
            for row in cur.fetchall():
                score_home = int(row['score_home'] or 0)
                score_away = int(row['score_away'] or 0)
                pick = PickData(
                    pick_id=row['id'],
                    match_id=row['match_id'] or '',
                    match_name=row['match_name'] or '',
                    home_team=row['home_team'] or '',
                    away_team=row['away_team'] or '',
                    market_type=row['market_type'] or '',
                    prediction=row['prediction'] or '',
                    odds_taken=float(row['odds_taken'] or 1.0),
                    is_resolved=bool(row['is_resolved']),
                    is_winner=bool(row['is_winner']),
                    profit_loss=float(row['profit_loss'] or 0),
                    diamond_score=int(row['diamond_score'] or 0),
                    probability=float(row['probability'] or 0),
                    home_xg=float(row['home_xg'] or 0),
                    away_xg=float(row['away_xg'] or 0),
                    total_xg=float(row['total_xg'] or 0),
                    score_home=score_home,
                    score_away=score_away,
                    total_goals=score_home + score_away,
                    value_rating=row['value_rating'] or '',
                    edge_pct=float(row['edge_pct'] or 0),
                    source=row['source'] or '',
                    league=row['league'] or '',
                )
                self.picks.append(pick)
            print(f"✅ {len(self.picks)} paris résolus chargés")
    
    def calculate_team_historical(self):
        """Calcule stats historiques par équipe"""
        team_stats = defaultdict(lambda: {'bets': 0, 'wins': 0, 'profit': 0.0})
        
        for pick in self.picks:
            for team in [pick.home_team, pick.away_team]:
                if team:
                    team_stats[team]['bets'] += 1
                    if pick.is_winner:
                        team_stats[team]['wins'] += 1
                    team_stats[team]['profit'] += pick.profit_loss
        
        for team, stats in team_stats.items():
            if team in self.team_profiles and stats['bets'] > 0:
                profile = self.team_profiles[team]
                profile.total_matches = stats['bets']
                profile.historical_wr = stats['wins'] / stats['bets'] * 100
                profile.historical_roi = stats['profit'] / stats['bets'] * 100
        
        print(f"✅ Historique calculé pour {len(team_stats)} équipes")
    
    def evaluate_strategy(self, strategy: str, pick: PickData, team: str, is_home: bool) -> bool:
        """Évalue si une stratégie s'applique à ce pick"""
        profile = self.team_profiles.get(team)
        diamond = pick.diamond_score
        xg = pick.total_xg
        prob = pick.probability
        edge = pick.edge_pct
        market = pick.market_type
        value = pick.value_rating or ''
        style = profile.current_style if profile else 'balanced'
        
        # DIAMOND SCORE
        if strategy == 'DIAMOND_SNIPER_30':
            return diamond >= 30
        elif strategy == 'DIAMOND_HIGH_25':
            return diamond >= 25
        elif strategy == 'DIAMOND_GOOD_20':
            return diamond >= 20
        elif strategy == 'DIAMOND_MEDIUM_15':
            return diamond >= 15
        
        # XG SCORING
        elif strategy == 'XG_SNIPER_4':
            return xg >= 4.0
        elif strategy == 'XG_HIGH_35':
            return xg >= 3.5
        elif strategy == 'XG_GOOD_3':
            return xg >= 3.0
        elif strategy == 'XG_MEDIUM_25':
            return xg >= 2.5
        
        # CONVERGENCE XG
        elif strategy == 'CONVERGENCE_XG_HIGH':
            return xg >= 3.0 and diamond >= 20
        elif strategy == 'CONVERGENCE_XG_MEDIUM':
            return xg >= 2.5 and diamond >= 15
        
        # PROBABILITY
        elif strategy == 'PROB_HIGH_40':
            return prob >= 40
        elif strategy == 'PROB_MEDIUM_30':
            return prob >= 30
        elif strategy == 'PROB_LOW_25':
            return prob >= 25
        
        # QUANT ROI
        elif strategy == 'QUANT_BEST_MARKET':
            return profile and profile.historical_roi > 0
        elif strategy == 'QUANT_ROI_25':
            return profile and profile.historical_roi >= 25
        elif strategy == 'QUANT_ROI_30':
            return profile and profile.historical_roi >= 30
        elif strategy == 'QUANT_ROI_40':
            return profile and profile.historical_roi >= 40
        elif strategy == 'QUANT_ROI_50':
            return profile and profile.historical_roi >= 50
        
        # MARKET TYPES
        elif strategy == 'MARKET_OVER25':
            return 'over' in market and '25' in market
        elif strategy == 'MARKET_UNDER25':
            return 'under' in market and '25' in market
        elif strategy == 'MARKET_BTTS':
            return 'btts' in market
        elif strategy == 'MARKET_HOME':
            return market == 'home'
        elif strategy == 'MARKET_AWAY':
            return market == 'away'
        
        # STYLE
        elif strategy == 'STYLE_OFFENSIVE':
            return 'offensive' in style
        elif strategy == 'STYLE_ATTACKING':
            return 'attacking' in style
        elif strategy == 'STYLE_BALANCED_OFFENSIVE':
            return style in ['balanced', 'offensive']
        
        # LEAGUE
        elif strategy == 'LEAGUE_TOP':
            return any(l in (pick.league or '').lower() for l in ['premier', 'la liga', 'bundesliga', 'serie a', 'ligue 1'])
        elif strategy == 'LEAGUE_TIER1':
            return 'champions' in (pick.league or '').lower() or 'europa' in (pick.league or '').lower()
        elif strategy == 'LEAGUE_TIER2':
            return pick.league is not None and pick.league != ''
        
        # SPECIAL MARKETS
        elif strategy == 'UNDER_35_PURE':
            return 'under' in market and xg <= 3.2
        elif strategy == 'OVER_15_SAFE':
            return 'over' in market and xg >= 2.5
        elif strategy == 'BTTS_NO_PURE':
            return market == 'btts_no'
        
        # VALUE RATING
        elif strategy == 'VALUE_STRONG':
            return '✅' in value or 'STRONG' in value.upper()
        elif strategy == 'VALUE_GOOD':
            return '⚠️' in value or 'MARGINAL' in value.upper() or 'GOOD' in value.upper()
        elif strategy == 'VALUE_MARGINAL':
            return value != '' and 'FAIBLE' not in value.upper()
        
        # EDGE
        elif strategy == 'EDGE_POSITIVE':
            return edge > 0
        elif strategy == 'EDGE_HIGH_5':
            return edge >= 5
        elif strategy == 'EDGE_MEDIUM_0':
            return edge >= 0
        
        # COMBOS
        elif strategy == 'COMBO_DIAMOND_XG':
            return diamond >= 20 and xg >= 3.0
        elif strategy == 'COMBO_PROB_VALUE':
            return prob >= 30 and edge > 0
        elif strategy == 'TRIPLE_VALIDATION':
            return diamond >= 20 and xg >= 2.5 and prob >= 25
        
        # TIERS
        elif strategy == 'TIER_1_SNIPER':
            return diamond >= 30 and xg >= 3.5 and prob >= 35
        elif strategy == 'TIER_2_ELITE':
            return diamond >= 25 and xg >= 3.0
        elif strategy == 'TIER_3_GOLD':
            return diamond >= 20 and xg >= 2.5
        elif strategy == 'TIER_4_STANDARD':
            return diamond >= 15 or xg >= 2.5
        
        # ULTIMATE
        elif strategy == 'ULTIMATE_SNIPER':
            return diamond >= 30 and xg >= 3.5 and prob >= 35 and edge > 0
        elif strategy == 'ULTIMATE_HYBRID':
            return (diamond >= 25 and xg >= 3.0) or (diamond >= 20 and prob >= 35)
        
        return False
    
    def get_tier(self, strategy: str, pick: PickData) -> str:
        """Détermine le TIER selon la stratégie"""
        if 'SNIPER' in strategy or strategy in ['DIAMOND_SNIPER_30', 'XG_SNIPER_4', 'TIER_1_SNIPER', 'ULTIMATE_SNIPER']:
            return 'TIER_1_SNIPER'
        elif 'HIGH' in strategy or 'ELITE' in strategy or strategy in ['DIAMOND_HIGH_25', 'PROB_HIGH_40', 'TIER_2_ELITE']:
            return 'TIER_2_ELITE'
        elif 'GOOD' in strategy or 'GOLD' in strategy or strategy in ['DIAMOND_GOOD_20', 'XG_GOOD_3', 'TIER_3_GOLD']:
            return 'TIER_3_GOLD'
        else:
            return 'TIER_4_STANDARD'
    
    def run_audit(self):
        """Exécute l'audit complet"""
        print("\n" + "="*100)
        print("🏆 AUDIT QUANT 2.0 FINAL - ANALYSE GRANULAIRE PAR ÉQUIPE")
        print("="*100)
        
        for pick in self.picks:
            for team, is_home in [(pick.home_team, True), (pick.away_team, False)]:
                if not team:
                    continue
                    
                for strategy in ALL_STRATEGIES:
                    if self.evaluate_strategy(strategy, pick, team, is_home):
                        tier = self.get_tier(strategy, pick)
                        stake = TIER_STAKES.get(tier, 2.0)
                        
                        profit = pick.profit_loss * stake if pick.profit_loss else (
                            stake * (pick.odds_taken - 1) if pick.is_winner else -stake
                        )
                        
                        # Team stats
                        if strategy not in self.team_results[team] or self.team_results[team][strategy].name == '':
                            self.team_results[team][strategy] = StrategyStats(name=strategy)
                        
                        stats = self.team_results[team][strategy]
                        stats.total_bets += 1
                        stats.profit += profit
                        if pick.is_winner:
                            stats.wins += 1
                        else:
                            stats.losses += 1
                            # Analyse perte
                            if pick.total_xg >= 2.5 or pick.diamond_score >= 20:
                                stats.unlucky_losses += 1
                            else:
                                stats.bad_losses += 1
                        
                        # Global stats
                        g = self.global_results[strategy]
                        g.total_bets += 1
                        g.profit += profit
                        if pick.is_winner:
                            g.wins += 1
                        else:
                            g.losses += 1
                            if pick.total_xg >= 2.5 or pick.diamond_score >= 20:
                                g.unlucky_losses += 1
                            else:
                                g.bad_losses += 1
                        
                        self.all_bets.append({
                            'team': team, 'strategy': strategy, 'tier': tier,
                            'profit': profit, 'is_winner': pick.is_winner
                        })
        
        print(f"\n✅ {len(self.all_bets)} paris analysés pour {len(self.team_results)} équipes")
    
    def print_results(self):
        self._print_summary()
        self._print_team_table()
        self._print_strategy_ranking()
        self._print_tier_analysis()
        self._print_loss_analysis()
        self._save_results()
    
    def _print_summary(self):
        print("\n" + "="*100)
        print("📊 RÉSUMÉ GLOBAL")
        print("="*100)
        
        total_bets = len(self.all_bets)
        total_wins = sum(1 for b in self.all_bets if b['is_winner'])
        total_profit = sum(b['profit'] for b in self.all_bets)
        
        print(f"""
   📈 Total Paris Analysés: {total_bets}
   ✅ Wins: {total_wins} ({total_wins/total_bets*100:.1f}% WR)
   💰 P&L Total: {total_profit:+.1f}u
   🎯 Équipes: {len(self.team_results)}
   🧪 Stratégies: {len(ALL_STRATEGIES)}
   📅 Source: tracking_clv_picks (paris résolus)
""")
    
    def _print_team_table(self):
        print("\n" + "="*200)
        print("🏆 TABLEAU GRANULAIRE - MEILLEURE STRATÉGIE PAR ÉQUIPE")
        print("="*200)
        
        team_data = []
        for team, strategies in self.team_results.items():
            if not strategies:
                continue
            
            best = max(strategies.items(), key=lambda x: x[1].profit if x[1].total_bets > 0 else float('-inf'))
            if best[1].total_bets == 0:
                continue
            
            stats = best[1]
            sorted_strats = sorted([(n, s) for n, s in strategies.items() if s.total_bets > 0], 
                                   key=lambda x: x[1].profit, reverse=True)
            second = sorted_strats[1] if len(sorted_strats) > 1 else None
            
            profile = self.team_profiles.get(team)
            style = profile.current_style[:12] if profile else 'unknown'
            
            total_losses = stats.unlucky_losses + stats.bad_losses
            unlucky_pct = (stats.unlucky_losses / total_losses * 100) if total_losses > 0 else 100
            
            team_data.append({
                'team': team, 'best_strategy': best[0], 'style': style,
                'bets': stats.total_bets, 'wins': stats.wins, 'losses': stats.losses,
                'wr': stats.win_rate, 'pnl': stats.profit, 'unlucky_pct': unlucky_pct,
                'second': f"{second[0][:18]}({second[1].profit:+.1f})" if second else '-',
                'strats': len([s for s in strategies.values() if s.total_bets > 0])
            })
        
        team_data.sort(key=lambda x: x['pnl'], reverse=True)
        
        print(f"\n{'#':<4} {'Équipe':<25} {'Best Strategy':<24} {'Style':<13} {'P':<5} {'W':<4} {'L':<4} {'WR':<8} {'P&L':<10} {'Mal%':<6} {'2nd Best':<26} {'#S'}")
        print("-"*180)
        
        for i, d in enumerate(team_data, 1):
            if d['pnl'] >= 20: emoji = "💎"
            elif d['pnl'] >= 10: emoji = "🏆"
            elif d['pnl'] >= 5: emoji = "✅"
            elif d['pnl'] >= 0: emoji = "🔸"
            else: emoji = "❌"
            
            print(f"{emoji}{i:<3} {d['team'][:24]:<25} {d['best_strategy'][:23]:<24} {d['style']:<13} "
                  f"{d['bets']:<5} {d['wins']:<4} {d['losses']:<4} {d['wr']:.0f}%{'':<4} "
                  f"{d['pnl']:+.1f}u{'':<5} {d['unlucky_pct']:.0f}%{'':<3} {d['second'][:25]:<26} {d['strats']}")
        
        total_pnl = sum(d['pnl'] for d in team_data)
        total_bets = sum(d['bets'] for d in team_data)
        total_wins = sum(d['wins'] for d in team_data)
        
        print("-"*180)
        print(f"{'TOTAL':<30} {'':<24} {'':<13} {total_bets:<5} {total_wins:<4} {total_bets-total_wins:<4} "
              f"{total_wins/total_bets*100:.0f}%{'':<4} {total_pnl:+.1f}u")
        
        positive = len([d for d in team_data if d['pnl'] > 0])
        elite = len([d for d in team_data if d['pnl'] >= 10])
        print(f"\n   📊 P&L > 0: {positive} | Élite (≥10u): {elite} | Négatif: {len(team_data)-positive}")
    
    def _print_strategy_ranking(self):
        print("\n" + "="*140)
        print("📈 CLASSEMENT DES STRATÉGIES")
        print("="*140)
        
        sorted_strats = sorted(
            [(n, s) for n, s in self.global_results.items() if s.total_bets > 0],
            key=lambda x: x[1].profit, reverse=True
        )
        
        print(f"\n{'#':<4} {'Stratégie':<26} {'Équipes':<8} {'Paris':<8} {'Wins':<8} {'WR':<10} {'P&L':<14} {'Mal%':<8} {'Verdict'}")
        print("-"*140)
        
        for i, (name, stats) in enumerate(sorted_strats, 1):
            total_losses = stats.unlucky_losses + stats.bad_losses
            unlucky_pct = (stats.unlucky_losses / total_losses * 100) if total_losses > 0 else 100
            
            teams = sum(1 for t, strats in self.team_results.items() 
                       if name in strats and strats[name].total_bets > 0)
            
            if stats.profit >= 100: emoji, verdict = "💎", "CHAMPION"
            elif stats.profit >= 50: emoji, verdict = "🏆", "EXCELLENT"
            elif stats.profit >= 20: emoji, verdict = "✅", "TRÈS BON"
            elif stats.profit >= 0: emoji, verdict = "🔸", "POSITIF"
            else: emoji, verdict = "❌", "À ÉVITER"
            
            print(f"{emoji}{i:<3} {name:<26} {teams:<8} {stats.total_bets:<8} {stats.wins:<8} "
                  f"{stats.win_rate:.1f}%{'':<5} {stats.profit:+.1f}u{'':<8} {unlucky_pct:.0f}%{'':<5} {verdict}")
    
    def _print_tier_analysis(self):
        print("\n" + "="*100)
        print("�� ANALYSE PAR TIER")
        print("="*100)
        
        tier_stats = defaultdict(lambda: {'bets': 0, 'wins': 0, 'profit': 0.0, 'teams': set()})
        for bet in self.all_bets:
            tier_stats[bet['tier']]['bets'] += 1
            tier_stats[bet['tier']]['profit'] += bet['profit']
            tier_stats[bet['tier']]['teams'].add(bet['team'])
            if bet['is_winner']:
                tier_stats[bet['tier']]['wins'] += 1
        
        print(f"\n{'Tier':<24} {'Équipes':<10} {'Paris':<10} {'Wins':<10} {'WR':<12} {'P&L':<14} {'ROI'}")
        print("-"*100)
        
        for tier in ['TIER_1_SNIPER', 'TIER_2_ELITE', 'TIER_3_GOLD', 'TIER_4_STANDARD']:
            s = tier_stats[tier]
            if s['bets'] > 0:
                wr = s['wins'] / s['bets'] * 100
                stake = TIER_STAKES.get(tier, 2.0)
                roi = s['profit'] / (s['bets'] * stake) * 100
                print(f"{tier:<24} {len(s['teams']):<10} {s['bets']:<10} {s['wins']:<10} "
                      f"{wr:.1f}%{'':<7} {s['profit']:+.1f}u{'':<8} {roi:+.1f}%")
    
    def _print_loss_analysis(self):
        print("\n" + "="*100)
        print("📉 ANALYSE DES PERTES")
        print("="*100)
        
        total_losses = sum(1 for b in self.all_bets if not b['is_winner'])
        
        unlucky = 0
        bad = 0
        for n, s in self.global_results.items():
            unlucky += s.unlucky_losses
            bad += s.bad_losses
        
        if total_losses > 0:
            print(f"\n   Total pertes: {total_losses}")
            print(f"   🎲 MALCHANCE (xG/Diamond supportaient): {unlucky} ({unlucky/(unlucky+bad)*100:.1f}%)" if (unlucky+bad) > 0 else "")
            print(f"   ❌ MAUVAISE ANALYSE: {bad} ({bad/(unlucky+bad)*100:.1f}%)" if (unlucky+bad) > 0 else "")
            
            if (unlucky+bad) > 0 and unlucky/(unlucky+bad)*100 >= 70:
                print(f"\n   → 🏆 MODÈLE GLOBALEMENT CORRECT!")
    
    def _save_results(self):
        results = {
            'date': datetime.now().isoformat(),
            'summary': {
                'total_bets': len(self.all_bets),
                'total_wins': sum(1 for b in self.all_bets if b['is_winner']),
                'total_profit': sum(b['profit'] for b in self.all_bets),
                'teams': len(self.team_results),
            },
            'strategies': {n: {'bets': s.total_bets, 'wins': s.wins, 'wr': s.win_rate, 'pnl': s.profit}
                          for n, s in self.global_results.items() if s.total_bets > 0},
            'teams': {t: {'best': max(strats.items(), key=lambda x: x[1].profit)[0],
                         'pnl': max(strats.items(), key=lambda x: x[1].profit)[1].profit}
                     for t, strats in self.team_results.items() if strats}
        }
        
        with open('audit_FINAL_V2_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n✅ Résultats sauvegardés dans audit_FINAL_V2_results.json")


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║     🏆 AUDIT QUANT 2.0 FINAL V2 - BASÉ SUR TRACKING_CLV_PICKS                                                ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
""")
    
    audit = QuantAuditFinal()
    try:
        audit.connect()
        audit.load_team_intelligence()
        audit.load_picks()
        audit.calculate_team_historical()
        audit.run_audit()
        audit.print_results()
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        audit.close()


if __name__ == "__main__":
    main()
