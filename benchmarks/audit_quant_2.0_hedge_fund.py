#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║     🏦 AUDIT QUANT 2.0 HEDGE FUND - NIVEAU PROFESSIONNEL                      ║
║                                                                               ║
║  INTÉGRATION COMPLÈTE:                                                        ║
║  • 9 Stratégies Convergence/MC/Quant (Audit V2: +574.6u)                     ║
║  • Scoring Threshold (screenshot: 94.4% WR, Sharpe 1.72)                     ║
║  • Tactical Matrix (gegenpressing = 82% Over25)                              ║
║  • Market Patterns (Champions League +28.78% ROI)                            ║
║  • League Patterns (Bundesliga, Premier League)                              ║
║  • Day Patterns (Mercredi = best)                                            ║
║  • BTTS_NO (seul marché positif +7.5u)                                       ║
║  • Low Confidence Paradox (0-39 conf = 60.6% WR)                             ║
║  • Steam Analysis (validation mouvements)                                    ║
║                                                                               ║
║  ANALYSE PAR ÉQUIPE: Granulaire + Corrélations + Pertes                      ║
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

# ═══════════════════════════════════════════════════════════════════════════════
# 20+ STRATÉGIES QUANT 2.0
# ═══════════════════════════════════════════════════════════════════════════════
STRATEGIES = [
    # GROUPE A: Convergence (Audit V2)
    'CONVERGENCE_OVER_PURE',
    'CONVERGENCE_OVER_MC_55',
    'CONVERGENCE_OVER_MC_60',
    'CONVERGENCE_UNDER_PURE',
    
    # GROUPE B: Monte Carlo Pur
    'MC_PURE_60',
    'MC_PURE_65',
    'MC_PURE_70',
    'MC_NO_CLASH',
    
    # GROUPE C: Quant Market
    'QUANT_BEST_MARKET',
    'QUANT_ROI_30',
    'QUANT_ROI_40',
    
    # GROUPE D: Chaos/High xG
    'TOTAL_CHAOS',
    'CHAOS_EXTREME',
    
    # GROUPE E: Scoring Threshold (Screenshot)
    'SCORE_SNIPER_34',      # Score >= 34 → 100% WR zone
    'SCORE_HIGH_32',        # Score >= 32 → 92% WR zone
    'SCORE_GOOD_28',        # Score >= 28 → 81% WR zone
    
    # GROUPE F: Tactical Matrix
    'TACTICAL_GEGENPRESSING',  # Gegenpressing impliqué = 82% Over25
    'TACTICAL_ATTACKING',      # Attacking vs balanced = 83% Over25
    
    # GROUPE G: League Patterns
    'LEAGUE_CHAMPIONS',     # Champions League Over25 = +28.78% ROI
    'LEAGUE_BUNDESLIGA',    # Bundesliga Over25 = +16.22% ROI
    'LEAGUE_PREMIER',       # Premier League Over25 = +9.44% ROI
    
    # GROUPE H: Special Markets
    'BTTS_NO_PURE',         # Seul marché positif dans CLV tracking
    'UNDER_35_PURE',        # 65.4% WR dans CLV
    
    # GROUPE I: Paradox
    'LOW_CONFIDENCE_PARADOX',  # Confidence 0-39 = 60.6% WR
    
    # GROUPE J: Combos
    'COMBO_CONV_MC_SCORE',   # Convergence + MC + Score >= 28
    'COMBO_TACTICAL_LEAGUE', # Tactical match + League pattern
    'ULTIMATE_SNIPER',       # Toutes conditions réunies
]

# Styles tactiques pour tactical_matrix
GEGENPRESSING_STYLES = ['gegenpressing', 'high_press', 'pressing']
ATTACKING_STYLES = ['attacking', 'offensive', 'balanced_offensive']
DEFENSIVE_STYLES = ['defensive', 'balanced_defensive', 'counter_attack']

@dataclass
class TeamProfile:
    name: str
    tendency: str
    best_market: str
    best_roi: float
    xg_for: float
    xg_against: float
    historical_wr: float = 0
    league: str = ""
    current_style: str = ""
    home_over25_rate: float = 0
    away_over25_rate: float = 0
    goals_tendency: int = 50
    
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
    
    # Corrélations
    correlations: Dict[str, float] = field(default_factory=dict)

class AuditQuant20HedgeFund:
    def __init__(self):
        self.conn = None
        self.team_data = {}
        self.team_profiles: Dict[str, TeamProfile] = {}
        self.matches = []
        self.tactical_matrix = {}
        self.team_intelligence = {}
        self.steam_data = {}
        self.market_patterns = {}
        
    def connect(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connexion DB établie")
        
    def load_data(self):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # ═══════════════════════════════════════════════════════════════
            # 1. XG Tendencies
            # ═══════════════════════════════════════════════════════════════
            cur.execute("SELECT * FROM team_xg_tendencies")
            xg_data = {r['team_name']: r for r in cur.fetchall()}
            
            # ═══════════════════════════════════════════════════════════════
            # 2. Market Profiles
            # ═══════════════════════════════════════════════════════════════
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
            
            # ═══════════════════════════════════════════════════════════════
            # 3. Team Intelligence (styles, tendances)
            # ═══════════════════════════════════════════════════════════════
            cur.execute("""
                SELECT team_name, current_style, league, 
                       home_over25_rate, away_over25_rate, 
                       home_btts_rate, away_btts_rate,
                       goals_tendency, btts_tendency,
                       xg_for_avg, xg_against_avg
                FROM team_intelligence
            """)
            for r in cur.fetchall():
                self.team_intelligence[r['team_name']] = {
                    'style': r['current_style'] or 'balanced',
                    'league': r['league'] or '',
                    'home_over25': float(r['home_over25_rate'] or 50),
                    'away_over25': float(r['away_over25_rate'] or 50),
                    'home_btts': float(r['home_btts_rate'] or 50),
                    'away_btts': float(r['away_btts_rate'] or 50),
                    'goals_tendency': int(r['goals_tendency'] or 50),
                    'xg_for': float(r['xg_for_avg'] or 1.3),
                    'xg_against': float(r['xg_against_avg'] or 1.3),
                }
            print(f"✅ {len(self.team_intelligence)} team_intelligence chargés")
            
            # ═══════════════════════════════════════════════════════════════
            # 4. Tactical Matrix
            # ═══════════════════════════════════════════════════════════════
            cur.execute("""
                SELECT style_a, style_b, over_25_probability, btts_probability,
                       avg_goals_total, sample_size, confidence_level
                FROM tactical_matrix
                WHERE sample_size >= 10
            """)
            for r in cur.fetchall():
                key = f"{r['style_a']}_{r['style_b']}"
                self.tactical_matrix[key] = {
                    'over25': float(r['over_25_probability'] or 50),
                    'btts': float(r['btts_probability'] or 50),
                    'avg_goals': float(r['avg_goals_total'] or 2.5),
                    'samples': r['sample_size'],
                    'confidence': r['confidence_level']
                }
            print(f"✅ {len(self.tactical_matrix)} tactical_matrix chargés")
            
            # ═══════════════════════════════════════════════════════════════
            # 5. Market Patterns
            # ═══════════════════════════════════════════════════════════════
            cur.execute("""
                SELECT pattern_code, market_type, win_rate, roi, 
                       sample_size, is_profitable, recommendation
                FROM market_patterns
                WHERE is_reliable = true AND sample_size >= 20
            """)
            for r in cur.fetchall():
                self.market_patterns[r['pattern_code']] = {
                    'market': r['market_type'],
                    'wr': float(r['win_rate'] or 50),
                    'roi': float(r['roi'] or 0),
                    'profitable': r['is_profitable'],
                    'recommendation': r['recommendation']
                }
            print(f"✅ {len(self.market_patterns)} market_patterns chargés")
            
            # ═══════════════════════════════════════════════════════════════
            # 6. Steam Analysis
            # ═══════════════════════════════════════════════════════════════
            cur.execute("""
                SELECT match_id, steam_direction, steam_magnitude, 
                       prob_shift_total, classification
                FROM match_steam_analysis
                WHERE steam_direction IS NOT NULL
            """)
            for r in cur.fetchall():
                self.steam_data[r['match_id']] = {
                    'direction': r['steam_direction'],
                    'magnitude': r['steam_magnitude'],
                    'shift': float(r['prob_shift_total'] or 0),
                    'classification': r['classification']
                }
            print(f"✅ {len(self.steam_data)} steam_analysis chargés")
            
            # ═══════════════════════════════════════════════════════════════
            # 7. Build Team Profiles
            # ═══════════════════════════════════════════════════════════════
            for team in set(xg_data.keys()) | set(self.team_intelligence.keys()):
                xg = xg_data.get(team, {})
                ti = self.team_intelligence.get(team, {})
                markets = mkt_data.get(team, {'markets': {}, 'best_wr': 0})
                
                best_market = 'over_25'
                best_roi = 0
                for mkt, data in markets['markets'].items():
                    if data.get('is_best') and data['roi'] > best_roi:
                        best_market = mkt
                        best_roi = data['roi']
                        
                tendency = "OVER" if best_market in OVER_MARKETS else "UNDER" if best_market in UNDER_MARKETS else "NEUTRAL"
                
                self.team_data[team] = {
                    'xg_for': float(xg.get('avg_xg_for') or ti.get('xg_for', 1.3)),
                    'xg_against': float(xg.get('avg_xg_against') or ti.get('xg_against', 1.3)),
                    'best_market': best_market,
                    'best_roi': best_roi,
                    'tendency': tendency,
                    'markets': markets['markets'],
                    'best_wr': markets['best_wr'],
                    'style': ti.get('style', 'balanced'),
                    'league': ti.get('league', ''),
                    'home_over25': ti.get('home_over25', 50),
                    'away_over25': ti.get('away_over25', 50),
                    'goals_tendency': ti.get('goals_tendency', 50),
                }
                
                self.team_profiles[team] = TeamProfile(
                    name=team,
                    tendency=tendency,
                    best_market=best_market,
                    best_roi=best_roi,
                    xg_for=float(xg.get('avg_xg_for') or ti.get('xg_for', 1.3)),
                    xg_against=float(xg.get('avg_xg_against') or ti.get('xg_against', 1.3)),
                    historical_wr=markets['best_wr'],
                    league=ti.get('league', ''),
                    current_style=ti.get('style', 'balanced'),
                    home_over25_rate=ti.get('home_over25', 50),
                    away_over25_rate=ti.get('away_over25', 50),
                    goals_tendency=ti.get('goals_tendency', 50),
                )
                
            # ═══════════════════════════════════════════════════════════════
            # 8. Matchs
            # ═══════════════════════════════════════════════════════════════
            cur.execute("""
                SELECT match_id, home_team, away_team, score_home, score_away, league
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
        
        over_25 = over_35 = btts_yes = under_25 = under_35 = 0
        total_goals = []
        
        for _ in range(n_sims):
            home_goals = self.poisson_random(lambda_h)
            away_goals = self.poisson_random(lambda_a)
            total = home_goals + away_goals
            total_goals.append(total)
            
            if total >= 3: over_25 += 1
            if total >= 4: over_35 += 1
            if total < 3: under_25 += 1
            if total < 4: under_35 += 1
            if home_goals > 0 and away_goals > 0: btts_yes += 1
                
        return {
            'over_25_prob': over_25 / n_sims,
            'over_35_prob': over_35 / n_sims,
            'under_25_prob': under_25 / n_sims,
            'under_35_prob': under_35 / n_sims,
            'btts_yes_prob': btts_yes / n_sims,
            'btts_no_prob': (n_sims - btts_yes) / n_sims,
            'expected_goals': sum(total_goals) / n_sims,
            'lambda_home': lambda_h,
            'lambda_away': lambda_a,
        }
        
    def calculate_score(self, team_data: Dict, opp_data: Dict, mc: Dict, 
                       is_home: bool, match: dict) -> float:
        """
        Calcule le score composite (0-40) basé sur le screenshot
        Score >= 34: 100% WR zone
        Score >= 32: 92% WR zone
        Score >= 28: 81% WR zone
        """
        score = 0
        
        # Factor 1: xG Expected (0-10 points)
        xg = mc['expected_goals']
        if xg >= 3.0:
            score += 10
        elif xg >= 2.8:
            score += 8
        elif xg >= 2.6:
            score += 6
        elif xg >= 2.4:
            score += 4
        else:
            score += 2
            
        # Factor 2: MC Probability (0-10 points)
        mc_prob = mc['over_25_prob']
        if mc_prob >= 0.70:
            score += 10
        elif mc_prob >= 0.65:
            score += 8
        elif mc_prob >= 0.60:
            score += 6
        elif mc_prob >= 0.55:
            score += 4
        else:
            score += 2
            
        # Factor 3: Convergence (0-8 points)
        if team_data['tendency'] == "OVER" and opp_data['tendency'] == "OVER":
            score += 8
        elif team_data['tendency'] == opp_data['tendency']:
            score += 4
        elif (team_data['tendency'] == "OVER" and opp_data['tendency'] == "UNDER") or \
             (team_data['tendency'] == "UNDER" and opp_data['tendency'] == "OVER"):
            score += 0  # Style clash = malus
        else:
            score += 2
            
        # Factor 4: Team Over25 Rate (0-6 points)
        team_over25 = team_data.get('home_over25', 50) if is_home else team_data.get('away_over25', 50)
        opp_over25 = opp_data.get('away_over25', 50) if is_home else opp_data.get('home_over25', 50)
        avg_over25 = (team_over25 + opp_over25) / 2
        
        if avg_over25 >= 65:
            score += 6
        elif avg_over25 >= 55:
            score += 4
        elif avg_over25 >= 45:
            score += 2
        else:
            score += 0
            
        # Factor 5: Goals Tendency (0-6 points)
        avg_goals_tendency = (team_data.get('goals_tendency', 50) + opp_data.get('goals_tendency', 50)) / 2
        if avg_goals_tendency >= 75:
            score += 6
        elif avg_goals_tendency >= 65:
            score += 4
        elif avg_goals_tendency >= 55:
            score += 2
        else:
            score += 0
            
        return score
        
    def get_tactical_matchup(self, style_a: str, style_b: str) -> Dict:
        """Récupère les stats du tactical matrix"""
        key = f"{style_a}_{style_b}"
        if key in self.tactical_matrix:
            return self.tactical_matrix[key]
        key_reverse = f"{style_b}_{style_a}"
        if key_reverse in self.tactical_matrix:
            return self.tactical_matrix[key_reverse]
        return {'over25': 50, 'btts': 50, 'avg_goals': 2.5, 'samples': 0, 'confidence': 'low'}
        
    def is_gegenpressing_match(self, style_a: str, style_b: str) -> bool:
        """Vérifie si c'est un match gegenpressing (82% Over25)"""
        return style_a in GEGENPRESSING_STYLES or style_b in GEGENPRESSING_STYLES
        
    def evaluate_market(self, total_goals: int, home_goals: int, away_goals: int, market: str) -> bool:
        both = home_goals > 0 and away_goals > 0
        return {
            'over_25': total_goals >= 3, 'over_35': total_goals >= 4,
            'over_15': total_goals >= 2, 'under_25': total_goals < 3,
            'under_35': total_goals < 4, 'btts_yes': both, 'btts_no': not both,
        }.get(market, False)
        
    def analyze_loss(self, market: str, xg_expected: float, mc_prob: float, score: float) -> str:
        """
        Analyse scientifique des pertes:
        - UNLUCKY: xG/MC/Score supportaient le pari (variance)
        - BAD_ANALYSIS: xG/MC/Score ne supportaient pas le pari (erreur)
        """
        if market in ['over_25', 'over_35', 'btts_yes']:
            if mc_prob >= 0.58 or xg_expected >= 2.7 or score >= 28:
                return "UNLUCKY"
            return "BAD_ANALYSIS"
        elif market in ['under_25', 'under_35', 'btts_no']:
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
            
        # Setup
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
        
        # Calcul du Score Composite
        score = self.calculate_score(team_data, opp_data, mc, is_home, match)
        
        # Tendances
        team_tendency = team_data['tendency']
        opp_tendency = opp_data['tendency']
        convergence_over = team_tendency == "OVER" and opp_tendency == "OVER"
        convergence_under = team_tendency == "UNDER" and opp_tendency == "UNDER"
        style_clash = (team_tendency == "OVER" and opp_tendency == "UNDER") or \
                     (team_tendency == "UNDER" and opp_tendency == "OVER")
        
        # Styles tactiques
        team_style = team_data.get('style', 'balanced')
        opp_style = opp_data.get('style', 'balanced')
        is_gegenpressing = self.is_gegenpressing_match(team_style, opp_style)
        tactical = self.get_tactical_matchup(team_style, opp_style)
        
        # League
        league = match.get('league', '') or team_data.get('league', '')
        is_champions = 'champion' in league.lower() if league else False
        is_bundesliga = 'bundesliga' in league.lower() if league else False
        is_premier = 'premier' in league.lower() if league else False
        
        # ═══════════════════════════════════════════════════════════════════════
        # Helper function
        # ═══════════════════════════════════════════════════════════════════════
        def make_bet(strat_name, condition, market, stake=2.0):
            if condition:
                won = self.evaluate_market(total_goals, home_goals, away_goals, market)
                mc_prob = mc.get(f'{market}_prob', mc['over_25_prob'])
                results[strat_name] = {
                    'bet': True, 'market': market, 'won': won, 'stake': stake,
                    'profit': stake * (MARKET_ODDS.get(market, 1.85) - 1) if won else -stake,
                    'xg': xg_expected, 'mc_prob': mc_prob, 'score': score,
                    'loss_type': self.analyze_loss(market, xg_expected, mc_prob, score) if not won else None
                }
            else:
                results[strat_name] = {'bet': False}
        
        # ═══════════════════════════════════════════════════════════════════════
        # GROUPE A: CONVERGENCE (Audit V2)
        # ═══════════════════════════════════════════════════════════════════════
        make_bet('CONVERGENCE_OVER_PURE', convergence_over and xg_expected >= 2.5, 'over_25', 2.0)
        make_bet('CONVERGENCE_OVER_MC_55', convergence_over and mc['over_25_prob'] >= 0.55, 'over_25', 2.5)
        make_bet('CONVERGENCE_OVER_MC_60', convergence_over and mc['over_25_prob'] >= 0.60, 'over_25', 3.0)
        make_bet('CONVERGENCE_UNDER_PURE', convergence_under and xg_expected <= 2.3, 'under_25', 2.0)
        
        # ═══════════════════════════════════════════════════════════════════════
        # GROUPE B: MONTE CARLO PUR
        # ═══════════════════════════════════════════════════════════════════════
        make_bet('MC_PURE_60', mc['over_25_prob'] >= 0.60, 'over_25', 2.0)
        make_bet('MC_PURE_65', mc['over_25_prob'] >= 0.65, 'over_25', 2.5)
        make_bet('MC_PURE_70', mc['over_25_prob'] >= 0.70, 'over_25', 3.0)
        make_bet('MC_NO_CLASH', not style_clash and mc['over_25_prob'] >= 0.65, 'over_25', 2.5)
        
        # ═══════════════════════════════════════════════════════════════════════
        # GROUPE C: QUANT MARKET
        # ═══════════════════════════════════════════════════════════════════════
        best_mkt = team_data['best_market']
        if best_mkt in MARKET_ODDS:
            make_bet('QUANT_BEST_MARKET', team_data['best_roi'] >= 20, best_mkt, 2.0)
            make_bet('QUANT_ROI_30', team_data['best_roi'] >= 30, best_mkt, 2.5)
            make_bet('QUANT_ROI_40', team_data['best_roi'] >= 40, best_mkt, 3.0)
        else:
            for s in ['QUANT_BEST_MARKET', 'QUANT_ROI_30', 'QUANT_ROI_40']:
                results[s] = {'bet': False}
        
        # ═══════════════════════════════════════════════════════════════════════
        # GROUPE D: CHAOS
        # ═══════════════════════════════════════════════════════════════════════
        make_bet('TOTAL_CHAOS', xg_expected >= 3.0 and mc['over_25_prob'] >= 0.65, 'over_25', 2.5)
        make_bet('CHAOS_EXTREME', xg_expected >= 3.5 and mc['over_35_prob'] >= 0.55, 'over_35', 3.0)
        
        # ═══════════════════════════════════════════════════════════════════════
        # GROUPE E: SCORING THRESHOLD (Screenshot - NOUVEAU!)
        # ═══════════════════════════════════════════════════════════════════════
        make_bet('SCORE_SNIPER_34', score >= 34, 'over_25', 4.0)    # 100% WR zone
        make_bet('SCORE_HIGH_32', score >= 32, 'over_25', 3.0)      # 92% WR zone
        make_bet('SCORE_GOOD_28', score >= 28, 'over_25', 2.5)      # 81% WR zone
        
        # ═══════════════════════════════════════════════════════════════════════
        # GROUPE F: TACTICAL MATRIX (NOUVEAU!)
        # ═══════════════════════════════════════════════════════════════════════
        make_bet('TACTICAL_GEGENPRESSING', is_gegenpressing and tactical['over25'] >= 70, 'over_25', 2.5)
        make_bet('TACTICAL_ATTACKING', tactical['over25'] >= 75 and tactical['samples'] >= 20, 'over_25', 2.5)
        
        # ═══════════════════════════════════════════════════════════════════════
        # GROUPE G: LEAGUE PATTERNS (NOUVEAU!)
        # ═══════════════════════════════════════════════════════════════════════
        make_bet('LEAGUE_CHAMPIONS', is_champions and mc['over_25_prob'] >= 0.55, 'over_25', 3.0)
        make_bet('LEAGUE_BUNDESLIGA', is_bundesliga and mc['over_25_prob'] >= 0.55, 'over_25', 2.5)
        make_bet('LEAGUE_PREMIER', is_premier and mc['over_25_prob'] >= 0.55, 'over_25', 2.0)
        
        # ═══════════════════════════════════════════════════════════════════════
        # GROUPE H: SPECIAL MARKETS (NOUVEAU!)
        # ═══════════════════════════════════════════════════════════════════════
        make_bet('BTTS_NO_PURE', mc['btts_no_prob'] >= 0.52 and xg_expected <= 2.6, 'btts_no', 2.0)
        make_bet('UNDER_35_PURE', mc['under_35_prob'] >= 0.55 and xg_expected <= 3.2, 'under_35', 2.0)
        
        # ═══════════════════════════════════════════════════════════════════════
        # GROUPE I: PARADOX (NOUVEAU!)
        # ═══════════════════════════════════════════════════════════════════════
        # Low confidence (25-39%) = 60.6% WR dans les données
        low_conf_score = score >= 20 and score <= 28  # Zone paradoxale
        make_bet('LOW_CONFIDENCE_PARADOX', low_conf_score and mc['over_25_prob'] >= 0.50, 'over_25', 2.0)
        
        # ═══════════════════════════════════════════════════════════════════════
        # GROUPE J: COMBOS ULTIMES (NOUVEAU!)
        # ═══════════════════════════════════════════════════════════════════════
        combo_conv_mc = convergence_over and mc['over_25_prob'] >= 0.58 and score >= 28
        make_bet('COMBO_CONV_MC_SCORE', combo_conv_mc, 'over_25', 3.5)
        
        combo_tactical = (is_gegenpressing or tactical['over25'] >= 70) and is_bundesliga
        make_bet('COMBO_TACTICAL_LEAGUE', combo_tactical and mc['over_25_prob'] >= 0.55, 'over_25', 3.0)
        
        # ULTIMATE SNIPER: Toutes les conditions top
        ultimate = (
            score >= 32 and 
            convergence_over and 
            mc['over_25_prob'] >= 0.65 and 
            xg_expected >= 2.8 and
            team_data['best_roi'] >= 25
        )
        make_bet('ULTIMATE_SNIPER', ultimate, 'over_25', 5.0)
        
        return results
        
    def run_audit(self):
        print("\n" + "="*100)
        print("🏦 AUDIT QUANT 2.0 HEDGE FUND - ANALYSE GRANULAIRE")
        print("="*100)
        
        for team_name, profile in self.team_profiles.items():
            for strat in STRATEGIES:
                profile.strategy_stats[strat] = {
                    'bets': 0, 'wins': 0, 'profit': 0, 'stake': 0,
                    'unlucky': 0, 'bad_analysis': 0, 'scores': []
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
                        stats['scores'].append(res.get('score', 0))
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
                
            # Calculer corrélations entre stratégies
            for s1 in STRATEGIES[:5]:  # Top 5 stratégies pour corrélation
                for s2 in STRATEGIES[:5]:
                    if s1 != s2:
                        s1_bets = profile.strategy_stats[s1]['bets']
                        s2_bets = profile.strategy_stats[s2]['bets']
                        if s1_bets > 0 and s2_bets > 0:
                            # Corrélation simplifiée basée sur overlap
                            overlap = min(s1_bets, s2_bets) / max(s1_bets, s2_bets)
                            profile.correlations[f"{s1}_vs_{s2}"] = overlap
                
        print(f"✅ {len(self.team_profiles)} équipes auditées avec {len(STRATEGIES)} stratégies")
        
    def print_results(self):
        print("\n")
        print("="*200)
        print("🏆 TABLEAU COMPLET 99 ÉQUIPES - AUDIT QUANT 2.0 HEDGE FUND")
        print("="*200)
        
        all_teams = sorted(
            self.team_profiles.values(),
            key=lambda x: x.best_strategy_pnl if x.best_strategy else -1000,
            reverse=True
        )
        
        print(f"\n{'#':<4} {'Équipe':<28} {'Best Strategy':<25} {'Style':<12} {'M':<4} {'P':<4} {'W':<4} {'L':<3} {'WR':<7} {'ROI':<8} {'P&L':<10} {'Mal%':<6} {'Err%':<6} {'2nd Best':<22}")
        print("-"*200)
        
        total_bets = 0
        total_wins = 0
        total_pnl = 0
        total_unlucky = 0
        total_bad = 0
        
        for i, p in enumerate(all_teams, 1):
            if p.best_strategy:
                stats = p.strategy_stats[p.best_strategy]
                losses = p.total_losses
                unlucky_pct = (p.unlucky_losses / losses * 100) if losses > 0 else 0
                bad_pct = (p.bad_analysis_losses / losses * 100) if losses > 0 else 0
                
                if p.best_strategy_pnl >= 15:
                    emoji = "💎"
                elif p.best_strategy_pnl >= 5:
                    emoji = "✅"
                elif p.best_strategy_pnl >= 0:
                    emoji = "⚪"
                else:
                    emoji = "❌"
                
                second = f"{p.top3_strategies[1][0][:18]}({p.top3_strategies[1][1]:+.1f})" if len(p.top3_strategies) > 1 else "-"
                
                print(f"{emoji}{i:<3} {p.name[:27]:<28} {p.best_strategy[:24]:<25} {p.current_style[:11]:<12} "
                      f"{p.total_matches:<4} {stats['bets']:<4} {stats['wins']:<4} {losses:<3} "
                      f"{p.best_strategy_wr:.0f}%{'':<3} {p.best_strategy_roi:+.0f}%{'':<3} "
                      f"{p.best_strategy_pnl:+.1f}u{'':<4} {unlucky_pct:.0f}%{'':<3} {bad_pct:.0f}%{'':<3} {second:<22}")
                
                total_bets += stats['bets']
                total_wins += stats['wins']
                total_pnl += p.best_strategy_pnl
                total_unlucky += p.unlucky_losses
                total_bad += p.bad_analysis_losses
            else:
                print(f"⚠️{i:<3} {p.name[:27]:<28} {'AUCUNE':<25} {p.current_style[:11]:<12} {p.total_matches:<4} {'-':<4} {'-':<4} {'-':<3} {'-':<7} {'-':<8} {'-':<10}")
        
        # Résumé
        print("-"*200)
        total_losses = total_bets - total_wins
        wr = (total_wins / total_bets * 100) if total_bets > 0 else 0
        unlucky_total = (total_unlucky / total_losses * 100) if total_losses > 0 else 0
        bad_total = (total_bad / total_losses * 100) if total_losses > 0 else 0
        
        print(f"{'TOTAL':<4} {'':<28} {'':<25} {'':<12} {'':<4} {total_bets:<4} {total_wins:<4} {total_losses:<3} "
              f"{wr:.0f}%{'':<3} {'':<8} {total_pnl:+.1f}u{'':<4} {unlucky_total:.0f}%{'':<3} {bad_total:.0f}%")
        
        # ═══════════════════════════════════════════════════════════════════════
        # CLASSEMENT DES STRATÉGIES
        # ═══════════════════════════════════════════════════════════════════════
        print("\n" + "="*140)
        print("📈 CLASSEMENT DES 27 STRATÉGIES (par P&L total):")
        print("="*140)
        
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
        
        print(f"\n{'#':<4} {'Stratégie':<28} {'Éq.':<6} {'Paris':<8} {'Wins':<8} {'WR':<8} {'P&L':<12} {'Mal%':<8} {'Err%':<8} {'Source':<15}")
        print("-"*140)
        
        for i, (strat, data) in enumerate(sorted_strats, 1):
            wr = (data['wins'] / data['bets'] * 100) if data['bets'] > 0 else 0
            losses = data['bets'] - data['wins']
            unlucky_pct = (data['unlucky'] / losses * 100) if losses > 0 else 0
            bad_pct = (data['bad'] / losses * 100) if losses > 0 else 0
            
            if data['pnl'] >= 100:
                emoji = "💎"
                verdict = "EXCELLENT"
            elif data['pnl'] >= 50:
                emoji = "🏆"
                verdict = "TRÈS BON"
            elif data['pnl'] >= 0:
                emoji = "✅"
                verdict = "POSITIF"
            else:
                emoji = "❌"
                verdict = "NÉGATIF"
            
            # Identifier la source
            if 'CONVERGENCE' in strat:
                source = "Audit V2"
            elif 'MC' in strat:
                source = "Monte Carlo"
            elif 'QUANT' in strat:
                source = "Quant Market"
            elif 'SCORE' in strat:
                source = "Screenshot MC"
            elif 'TACTICAL' in strat:
                source = "Tactical Matrix"
            elif 'LEAGUE' in strat:
                source = "Market Pattern"
            elif 'BTTS' in strat or 'UNDER' in strat:
                source = "CLV Discovery"
            elif 'PARADOX' in strat:
                source = "Agent Paradox"
            elif 'COMBO' in strat or 'ULTIMATE' in strat:
                source = "Combo Strategy"
            else:
                source = "Chaos"
                
            print(f"{emoji}{i:<3} {strat:<28} {data['teams']:<6} {data['bets']:<8} {data['wins']:<8} {wr:.1f}%{'':<4} {data['pnl']:+.1f}u{'':<6} {unlucky_pct:.0f}%{'':<5} {bad_pct:.0f}%{'':<5} {source:<15}")
        
        # ═══════════════════════════════════════════════════════════════════════
        # ANALYSE PERTES DÉTAILLÉE
        # ═══════════════════════════════════════════════════════════════════════
        print("\n" + "="*100)
        print("📉 ANALYSE SCIENTIFIQUE DES PERTES:")
        print("="*100)
        
        total_all_unlucky = sum(d['unlucky'] for d in strat_totals.values())
        total_all_bad = sum(d['bad'] for d in strat_totals.values())
        total_all_losses = total_all_unlucky + total_all_bad
        
        if total_all_losses > 0:
            print(f"\n   Total pertes analysées: {total_all_losses}")
            print(f"   🎲 MALCHANCE (xG/MC/Score supportait): {total_all_unlucky} ({total_all_unlucky/total_all_losses*100:.1f}%)")
            print(f"   ❌ MAUVAISE ANALYSE: {total_all_bad} ({total_all_bad/total_all_losses*100:.1f}%)")
            print(f"\n   → CONCLUSION: {'MODÈLE CORRECT!' if total_all_unlucky/total_all_losses > 0.7 else 'AJUSTEMENTS NÉCESSAIRES'}")
        
        # ═══════════════════════════════════════════════════════════════════════
        # TOP 5 ÉQUIPES PAR STRATÉGIE
        # ═══════════════════════════════════════════════════════════════════════
        print("\n" + "="*100)
        print("🎯 TOP 5 ÉQUIPES PAR STRATÉGIE (sélection):")
        print("="*100)
        
        key_strategies = ['CONVERGENCE_OVER_MC_55', 'QUANT_BEST_MARKET', 'SCORE_HIGH_32', 
                         'TACTICAL_GEGENPRESSING', 'COMBO_CONV_MC_SCORE', 'ULTIMATE_SNIPER']
        
        for strat in key_strategies:
            teams_for_strat = [(p.name, p.strategy_stats[strat], p.total_matches, p.current_style) 
                              for p in self.team_profiles.values() 
                              if p.strategy_stats.get(strat, {}).get('bets', 0) >= 2]
            teams_for_strat.sort(key=lambda x: x[1]['profit'], reverse=True)
            
            if teams_for_strat:
                print(f"\n📊 {strat}:")
                for i, (name, stats, matches, style) in enumerate(teams_for_strat[:5], 1):
                    wr = (stats['wins'] / stats['bets'] * 100) if stats['bets'] > 0 else 0
                    print(f"   {i}. {name[:35]:<37} [{style[:10]}] {matches}M, {stats['bets']}P, {wr:.0f}%WR, {stats['profit']:+.1f}u")
        
        # ═══════════════════════════════════════════════════════════════════════
        # SAUVEGARDER
        # ═══════════════════════════════════════════════════════════════════════
        output = {
            'timestamp': datetime.now().isoformat(),
            'strategies_count': len(STRATEGIES),
            'teams_count': len(all_teams),
            'total_summary': {
                'bets': total_bets,
                'wins': total_wins,
                'pnl': round(total_pnl, 1),
                'wr': round(wr, 1),
                'unlucky_pct': round(unlucky_total, 1),
                'bad_analysis_pct': round(bad_total, 1)
            },
            'strategy_ranking': [
                {'rank': i+1, 'strategy': s, 'teams': d['teams'], 'bets': d['bets'], 
                 'wins': d['wins'], 'wr': round((d['wins']/d['bets']*100) if d['bets']>0 else 0, 1),
                 'pnl': round(d['pnl'], 1),
                 'unlucky_pct': round((d['unlucky']/(d['bets']-d['wins'])*100) if d['bets']>d['wins'] else 0, 1),
                 'bad_pct': round((d['bad']/(d['bets']-d['wins'])*100) if d['bets']>d['wins'] else 0, 1)}
                for i, (s, d) in enumerate(sorted_strats)
            ],
            'teams': [
                {
                    'rank': i+1, 'name': p.name, 'best_strategy': p.best_strategy,
                    'style': p.current_style, 'league': p.league,
                    'matches': p.total_matches, 'bets': p.best_strategy_bets,
                    'wins': p.best_strategy_wins, 'wr': round(p.best_strategy_wr, 1),
                    'roi': round(p.best_strategy_roi, 1), 'pnl': round(p.best_strategy_pnl, 1),
                    'unlucky_pct': round((p.unlucky_losses/p.total_losses*100) if p.total_losses > 0 else 0, 1),
                    'bad_pct': round((p.bad_analysis_losses/p.total_losses*100) if p.total_losses > 0 else 0, 1),
                    'top3': [(s, round(pnl, 1)) for s, pnl in p.top3_strategies]
                }
                for i, p in enumerate(all_teams) if p.best_strategy
            ]
        }
        
        with open('audit_quant_2.0_hedge_fund_results.json', 'w') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
            
        print(f"\n✅ Résultats sauvegardés dans audit_quant_2.0_hedge_fund_results.json")

def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║     🏦 AUDIT QUANT 2.0 HEDGE FUND - NIVEAU PROFESSIONNEL                      ║
║                                                                               ║
║  27 Stratégies intégrées:                                                    ║
║  • Convergence/MC/Quant (Audit V2: +574.6u)                                  ║
║  • Scoring Threshold (Screenshot: 94.4% WR)                                  ║
║  • Tactical Matrix (Gegenpressing = 82% Over25)                              ║
║  • League Patterns (Champions +28.78% ROI)                                   ║
║  • Special Markets (BTTS_NO seul positif)                                    ║
║  • Paradox (Low Conf = High WR)                                              ║
║  • Combos Ultimes                                                            ║
║                                                                               ║
║  ANALYSE GRANULAIRE: 99 équipes × 27 stratégies + Pertes                     ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    audit = AuditQuant20HedgeFund()
    audit.connect()
    audit.load_data()
    audit.run_audit()
    audit.print_results()

if __name__ == "__main__":
    main()
