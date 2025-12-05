#!/usr/bin/env python3
"""
AUDIT QUANT 2.0 FINAL - VERSION CORRIGÉE
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
    'btts_yes': 1.80, 'btts_no': 2.00,
}

TIER_STAKES = {
    'TIER_1_SNIPER': 4.0,
    'TIER_2_ELITE': 3.0,
    'TIER_3_GOLD': 2.5,
    'TIER_4_STANDARD': 2.0,
    'TIER_5_EXPERIMENTAL': 1.0,
}

ALL_STRATEGIES = [
    'CONVERGENCE_OVER_PURE', 'CONVERGENCE_OVER_MC_55', 'CONVERGENCE_OVER_MC_60',
    'CONVERGENCE_OVER_MC_65', 'CONVERGENCE_UNDER_PURE',
    'MC_PURE_55', 'MC_PURE_60', 'MC_PURE_65', 'MC_PURE_70', 'MC_NO_CLASH',
    'QUANT_BEST_MARKET', 'QUANT_ROI_25', 'QUANT_ROI_30', 'QUANT_ROI_40', 'QUANT_ROI_50',
    'SCORE_SNIPER_34', 'SCORE_HIGH_32', 'SCORE_GOOD_28', 'SCORE_MEDIUM_25',
    'TACTICAL_GEGENPRESSING', 'TACTICAL_ATTACKING', 'TACTICAL_HIGH_SCORING',
    'LEAGUE_CHAMPIONS', 'LEAGUE_BUNDESLIGA', 'LEAGUE_PREMIER', 'LEAGUE_SERIE_A', 'LEAGUE_LIGUE_1',
    'UNDER_35_PURE', 'UNDER_25_SELECTIVE', 'BTTS_NO_PURE', 'OVER_15_SAFE',
    'LOW_CONFIDENCE_PARADOX', 'SWEET_SPOT_60_79', 'SWEET_SPOT_CONSERVATIVE',
    'COMBO_CONV_MC_SCORE', 'COMBO_TACTICAL_LEAGUE', 'TRIPLE_VALIDATION', 'QUANT_MC_COMBO',
    'TIER_1_SNIPER', 'TIER_2_ELITE', 'TIER_3_GOLD', 'TIER_4_STANDARD',
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
    clean_sheet_tendency: int = 50
    xg_for_avg: float = 1.5
    xg_against_avg: float = 1.3
    home_strength: int = 50
    away_strength: int = 50
    total_matches: int = 0
    historical_wr: float = 0.0
    historical_roi: float = 0.0
    best_market: str = 'over_25'

@dataclass
class MatchData:
    match_id: int
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    total_goals: int
    match_date: datetime
    league: str = ''
    home_xg: float = 0.0
    away_xg: float = 0.0
    total_xg: float = 0.0
    mc_over25_prob: float = 0.0
    mc_over35_prob: float = 0.0
    mc_under25_prob: float = 0.0
    mc_under35_prob: float = 0.0
    mc_btts_prob: float = 0.0
    convergence_over: bool = False
    convergence_under: bool = False
    is_over25: bool = False
    is_over35: bool = False
    is_btts: bool = False

@dataclass
class BetResult:
    strategy: str
    market: str
    stake: float
    odds: float
    is_winner: bool
    profit: float
    team: str
    match_id: int
    tier: str = 'STANDARD'
    score: int = 0
    loss_type: str = ''
    xg_supported: bool = False
    mc_supported: bool = False
    convergence_supported: bool = False

@dataclass
class StrategyStats:
    name: str
    total_bets: int = 0
    wins: int = 0
    losses: int = 0
    profit: float = 0.0
    unlucky_losses: int = 0
    bad_analysis_losses: int = 0
    
    @property
    def win_rate(self) -> float:
        return (self.wins / self.total_bets * 100) if self.total_bets > 0 else 0
    
    @property
    def roi(self) -> float:
        total_staked = self.total_bets * 2.0
        return (self.profit / total_staked * 100) if total_staked > 0 else 0


class QuantAuditFinal:
    def __init__(self):
        self.conn = None
        self.team_profiles: Dict[str, TeamProfile] = {}
        self.matches: List[MatchData] = []
        self.tactical_matrix: Dict[str, Dict] = {}
        self.team_results: Dict[str, Dict[str, StrategyStats]] = defaultdict(lambda: defaultdict(lambda: StrategyStats(name='')))
        self.global_results: Dict[str, StrategyStats] = {s: StrategyStats(name=s) for s in ALL_STRATEGIES}
        self.all_bets: List[BetResult] = []
    
    def connect(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.conn.autocommit = True
        print("✅ Connexion DB établie")
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def load_team_intelligence(self):
        """Charge les profils - VERSION ADAPTÉE"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # D'abord vérifier les colonnes disponibles
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'team_intelligence'
            """)
            columns = [row['column_name'] for row in cur.fetchall()]
            print(f"   Colonnes disponibles: {columns[:10]}...")
            
            # Requête adaptée selon les colonnes existantes
            cur.execute("""
                SELECT team_name, 
                       COALESCE(current_style, 'balanced') as current_style,
                       COALESCE(home_over25_rate, 0) as home_over25_rate,
                       COALESCE(away_over25_rate, 0) as away_over25_rate,
                       COALESCE(home_btts_rate, 0) as home_btts_rate,
                       COALESCE(away_btts_rate, 0) as away_btts_rate,
                       COALESCE(goals_tendency, 50) as goals_tendency,
                       COALESCE(btts_tendency, 50) as btts_tendency,
                       COALESCE(clean_sheet_tendency, 50) as clean_sheet_tendency,
                       COALESCE(xg_for_avg, 1.5) as xg_for_avg,
                       COALESCE(xg_against_avg, 1.3) as xg_against_avg,
                       COALESCE(home_strength, 50) as home_strength,
                       COALESCE(away_strength, 50) as away_strength
                FROM team_intelligence 
                WHERE team_name IS NOT NULL
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
                    clean_sheet_tendency=int(row['clean_sheet_tendency'] or 50),
                    xg_for_avg=float(row['xg_for_avg'] or 1.5),
                    xg_against_avg=float(row['xg_against_avg'] or 1.3),
                    home_strength=int(row['home_strength'] or 50),
                    away_strength=int(row['away_strength'] or 50),
                )
                self.team_profiles[row['team_name']] = profile
            
            print(f"✅ {len(self.team_profiles)} profils d'équipes chargés")
    
    def load_tactical_matrix(self):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            try:
                cur.execute("""
                    SELECT style_a, style_b, over_25_probability, btts_probability,
                           avg_goals_total, sample_size, confidence_level
                    FROM tactical_matrix WHERE sample_size >= 10
                """)
                for row in cur.fetchall():
                    key = f"{row['style_a']}_vs_{row['style_b']}"
                    self.tactical_matrix[key] = {
                        'over25_prob': float(row['over_25_probability'] or 50),
                        'btts_prob': float(row['btts_probability'] or 50),
                        'avg_goals': float(row['avg_goals_total'] or 2.5),
                        'samples': int(row['sample_size'] or 0),
                    }
                print(f"✅ {len(self.tactical_matrix)} combinaisons tactiques chargées")
            except Exception as e:
                print(f"⚠️ Tactical matrix non disponible: {e}")
    
    def load_matches(self):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT ON (ap.match_id)
                    ap.match_id, ap.home_team, ap.away_team,
                    ap.home_goals, ap.away_goals, ap.match_date, 
                    COALESCE(ap.league, '') as league,
                    COALESCE(ap.home_xg, 0) as home_xg,
                    COALESCE(ap.away_xg, 0) as away_xg,
                    COALESCE(ap.mc_over25_prob, 0) as mc_over25_prob,
                    COALESCE(ap.mc_over35_prob, 0) as mc_over35_prob,
                    COALESCE(ap.mc_under25_prob, 0) as mc_under25_prob,
                    COALESCE(ap.mc_under35_prob, 0) as mc_under35_prob,
                    COALESCE(ap.mc_btts_prob, 0) as mc_btts_prob,
                    COALESCE(ap.convergence_over, false) as convergence_over,
                    COALESCE(ap.convergence_under, false) as convergence_under
                FROM agent_predictions ap
                WHERE ap.home_goals IS NOT NULL AND ap.away_goals IS NOT NULL
                  AND ap.match_date >= '2024-09-01'
                ORDER BY ap.match_id, ap.created_at DESC
            """)
            for row in cur.fetchall():
                total_goals = (row['home_goals'] or 0) + (row['away_goals'] or 0)
                match = MatchData(
                    match_id=row['match_id'],
                    home_team=row['home_team'],
                    away_team=row['away_team'],
                    home_goals=row['home_goals'] or 0,
                    away_goals=row['away_goals'] or 0,
                    total_goals=total_goals,
                    match_date=row['match_date'],
                    league=row['league'] or '',
                    home_xg=float(row['home_xg'] or 0),
                    away_xg=float(row['away_xg'] or 0),
                    total_xg=float(row['home_xg'] or 0) + float(row['away_xg'] or 0),
                    mc_over25_prob=float(row['mc_over25_prob'] or 0),
                    mc_over35_prob=float(row['mc_over35_prob'] or 0),
                    mc_under25_prob=float(row['mc_under25_prob'] or 0),
                    mc_under35_prob=float(row['mc_under35_prob'] or 0),
                    mc_btts_prob=float(row['mc_btts_prob'] or 0),
                    convergence_over=bool(row['convergence_over']),
                    convergence_under=bool(row['convergence_under']),
                    is_over25=total_goals >= 3,
                    is_over35=total_goals >= 4,
                    is_btts=(row['home_goals'] or 0) > 0 and (row['away_goals'] or 0) > 0,
                )
                self.matches.append(match)
            print(f"✅ {len(self.matches)} matchs chargés")
    
    def calculate_composite_score(self, match: MatchData, team: str, is_home: bool) -> int:
        score = 0
        xg = match.total_xg
        if xg >= 3.5: score += 10
        elif xg >= 3.0: score += 8
        elif xg >= 2.7: score += 6
        elif xg >= 2.5: score += 4
        elif xg >= 2.2: score += 2
        
        mc = match.mc_over25_prob
        if mc >= 70: score += 10
        elif mc >= 65: score += 8
        elif mc >= 60: score += 6
        elif mc >= 55: score += 4
        elif mc >= 50: score += 2
        
        if match.convergence_over: score += 8
        
        profile = self.team_profiles.get(team)
        if profile:
            rate = profile.home_over25_rate if is_home else profile.away_over25_rate
            if rate >= 70: score += 6
            elif rate >= 60: score += 4
            elif rate >= 50: score += 2
            
            tendency = profile.goals_tendency
            if tendency >= 75: score += 6
            elif tendency >= 65: score += 4
            elif tendency >= 55: score += 2
        
        return min(score, 40)
    
    def evaluate_strategy(self, strategy: str, match: MatchData, team: str, is_home: bool) -> Optional[BetResult]:
        profile = self.team_profiles.get(team)
        score = self.calculate_composite_score(match, team, is_home)
        
        home_profile = self.team_profiles.get(match.home_team)
        away_profile = self.team_profiles.get(match.away_team)
        home_style = home_profile.current_style if home_profile else 'balanced'
        away_style = away_profile.current_style if away_profile else 'balanced'
        tactical_key = f"{home_style}_vs_{away_style}"
        tactical = self.tactical_matrix.get(tactical_key, {})
        
        # CONVERGENCE
        if strategy == 'CONVERGENCE_OVER_PURE':
            if match.convergence_over:
                return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_4_STANDARD')
        elif strategy == 'CONVERGENCE_OVER_MC_55':
            if match.convergence_over and match.mc_over25_prob >= 55:
                return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_3_GOLD')
        elif strategy == 'CONVERGENCE_OVER_MC_60':
            if match.convergence_over and match.mc_over25_prob >= 60:
                return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_3_GOLD')
        elif strategy == 'CONVERGENCE_OVER_MC_65':
            if match.convergence_over and match.mc_over25_prob >= 65:
                return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_2_ELITE')
        elif strategy == 'CONVERGENCE_UNDER_PURE':
            if match.convergence_under:
                return self._make_bet(strategy, 'under_25', match, team, score, 'TIER_4_STANDARD', is_over=False)
        
        # MONTE CARLO
        elif strategy == 'MC_PURE_55':
            if match.mc_over25_prob >= 55:
                return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_4_STANDARD')
        elif strategy == 'MC_PURE_60':
            if match.mc_over25_prob >= 60:
                return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_4_STANDARD')
        elif strategy == 'MC_PURE_65':
            if match.mc_over25_prob >= 65:
                return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_3_GOLD')
        elif strategy == 'MC_PURE_70':
            if match.mc_over25_prob >= 70:
                return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_2_ELITE')
        elif strategy == 'MC_NO_CLASH':
            if match.mc_over25_prob >= 65 and match.mc_under25_prob < 40:
                return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_3_GOLD')
        
        # QUANT MARKET
        elif strategy == 'QUANT_BEST_MARKET':
            if profile and profile.historical_roi > 0:
                market = profile.best_market
                is_over = market in ['over_25', 'over_35', 'btts_yes']
                return self._make_bet(strategy, market, match, team, score, 'TIER_4_STANDARD', is_over=is_over)
        elif strategy == 'QUANT_ROI_25':
            if profile and profile.historical_roi >= 25:
                return self._make_bet(strategy, profile.best_market, match, team, score, 'TIER_4_STANDARD')
        elif strategy == 'QUANT_ROI_30':
            if profile and profile.historical_roi >= 30:
                return self._make_bet(strategy, profile.best_market, match, team, score, 'TIER_3_GOLD')
        elif strategy == 'QUANT_ROI_40':
            if profile and profile.historical_roi >= 40:
                return self._make_bet(strategy, profile.best_market, match, team, score, 'TIER_2_ELITE')
        elif strategy == 'QUANT_ROI_50':
            if profile and profile.historical_roi >= 50:
                return self._make_bet(strategy, profile.best_market, match, team, score, 'TIER_1_SNIPER')
        
        # SCORING THRESHOLD
        elif strategy == 'SCORE_SNIPER_34':
            if score >= 34:
                return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_1_SNIPER')
        elif strategy == 'SCORE_HIGH_32':
            if score >= 32:
                return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_2_ELITE')
        elif strategy == 'SCORE_GOOD_28':
            if score >= 28:
                return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_3_GOLD')
        elif strategy == 'SCORE_MEDIUM_25':
            if score >= 25:
                return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_4_STANDARD')
        
        # TACTICAL
        elif strategy == 'TACTICAL_GEGENPRESSING':
            if 'gegenpressing' in home_style or 'gegenpressing' in away_style:
                if tactical.get('over25_prob', 0) >= 70:
                    return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_2_ELITE')
        elif strategy == 'TACTICAL_ATTACKING':
            if 'attacking' in home_style or 'offensive' in home_style:
                if tactical.get('over25_prob', 0) >= 65:
                    return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_3_GOLD')
        elif strategy == 'TACTICAL_HIGH_SCORING':
            if tactical.get('avg_goals', 0) >= 3.5:
                return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_2_ELITE')
        
        # LEAGUE PATTERNS
        elif strategy == 'LEAGUE_CHAMPIONS':
            if 'champions' in match.league.lower() or 'uefa' in match.league.lower():
                if match.mc_over25_prob >= 55:
                    return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_2_ELITE')
        elif strategy == 'LEAGUE_BUNDESLIGA':
            if 'bundesliga' in match.league.lower():
                if match.mc_over25_prob >= 55:
                    return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_3_GOLD')
        elif strategy == 'LEAGUE_PREMIER':
            if 'premier' in match.league.lower():
                if match.mc_over25_prob >= 55:
                    return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_3_GOLD')
        elif strategy == 'LEAGUE_SERIE_A':
            if 'serie a' in match.league.lower():
                if match.mc_over25_prob >= 55:
                    return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_4_STANDARD')
        elif strategy == 'LEAGUE_LIGUE_1':
            if 'ligue 1' in match.league.lower():
                if match.mc_over25_prob >= 55:
                    return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_4_STANDARD')
        
        # SPECIAL MARKETS
        elif strategy == 'UNDER_35_PURE':
            if match.mc_under35_prob >= 55 and match.total_xg <= 3.2:
                return self._make_bet(strategy, 'under_35', match, team, score, 'TIER_4_STANDARD', is_over=False)
        elif strategy == 'UNDER_25_SELECTIVE':
            if match.mc_under25_prob >= 60 and match.total_xg <= 2.3:
                return self._make_bet(strategy, 'under_25', match, team, score, 'TIER_3_GOLD', is_over=False)
        elif strategy == 'BTTS_NO_PURE':
            if match.mc_btts_prob < 45 and (match.home_xg < 1.0 or match.away_xg < 1.0):
                return self._make_bet(strategy, 'btts_no', match, team, score, 'TIER_4_STANDARD', is_over=False)
        elif strategy == 'OVER_15_SAFE':
            if match.mc_over25_prob >= 70 or match.total_xg >= 3.0:
                return self._make_bet(strategy, 'over_15', match, team, score, 'TIER_4_STANDARD')
        
        # PARADOX & SWEET SPOT
        elif strategy == 'LOW_CONFIDENCE_PARADOX':
            if 20 <= match.mc_over25_prob <= 35:
                if match.convergence_over or match.total_xg >= 2.5:
                    return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_5_EXPERIMENTAL')
        elif strategy == 'SWEET_SPOT_60_79':
            if 60 <= match.mc_over25_prob <= 79:
                return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_4_STANDARD')
        elif strategy == 'SWEET_SPOT_CONSERVATIVE':
            if 55 <= match.mc_over25_prob <= 65 and match.convergence_over:
                return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_4_STANDARD')
        
        # COMBOS
        elif strategy == 'COMBO_CONV_MC_SCORE':
            if match.convergence_over and match.mc_over25_prob >= 60 and score >= 28:
                return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_2_ELITE')
        elif strategy == 'COMBO_TACTICAL_LEAGUE':
            tactical_ok = tactical.get('over25_prob', 0) >= 65
            league_ok = any(l in match.league.lower() for l in ['champions', 'bundesliga', 'premier'])
            if tactical_ok and league_ok:
                return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_2_ELITE')
        elif strategy == 'TRIPLE_VALIDATION':
            if match.convergence_over and match.mc_over25_prob >= 60 and match.total_xg >= 2.5:
                return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_2_ELITE')
        elif strategy == 'QUANT_MC_COMBO':
            if profile and profile.historical_roi >= 20 and match.mc_over25_prob >= 55:
                return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_3_GOLD')
        
        # TIERS
        elif strategy == 'TIER_1_SNIPER':
            if score >= 34 and match.convergence_over and match.mc_over25_prob >= 65:
                return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_1_SNIPER')
        elif strategy == 'TIER_2_ELITE':
            if 32 <= score <= 33:
                return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_2_ELITE')
            elif profile and profile.historical_roi >= 40:
                return self._make_bet(strategy, profile.best_market, match, team, score, 'TIER_2_ELITE')
        elif strategy == 'TIER_3_GOLD':
            if 28 <= score <= 31:
                return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_3_GOLD')
            elif profile and profile.historical_roi >= 30:
                return self._make_bet(strategy, profile.best_market, match, team, score, 'TIER_3_GOLD')
        elif strategy == 'TIER_4_STANDARD':
            if match.mc_over25_prob >= 60:
                return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_4_STANDARD')
            elif match.mc_under35_prob >= 55:
                return self._make_bet(strategy, 'under_35', match, team, score, 'TIER_4_STANDARD', is_over=False)
        
        # ULTIMATE
        elif strategy == 'ULTIMATE_SNIPER':
            if score >= 34 and match.convergence_over and match.mc_over25_prob >= 65 and match.total_xg >= 2.8:
                return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_1_SNIPER')
        elif strategy == 'ULTIMATE_HYBRID':
            if score >= 32 and match.mc_over25_prob >= 60:
                return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_2_ELITE')
            elif score >= 28 and match.convergence_over:
                return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_3_GOLD')
            elif profile and profile.historical_roi >= 30:
                return self._make_bet(strategy, profile.best_market, match, team, score, 'TIER_3_GOLD')
        
        return None
    
    def _make_bet(self, strategy: str, market: str, match: MatchData, 
                  team: str, score: int, tier: str, is_over: bool = True) -> BetResult:
        stake = TIER_STAKES.get(tier, 2.0)
        odds = MARKET_ODDS.get(market, 1.85)
        
        if market == 'over_25': is_winner = match.is_over25
        elif market == 'over_35': is_winner = match.is_over35
        elif market == 'over_15': is_winner = match.total_goals >= 2
        elif market == 'under_25': is_winner = not match.is_over25
        elif market == 'under_35': is_winner = match.total_goals < 4
        elif market == 'btts_yes': is_winner = match.is_btts
        elif market == 'btts_no': is_winner = not match.is_btts
        else: is_winner = match.is_over25
        
        profit = stake * (odds - 1) if is_winner else -stake
        
        xg_supported = match.total_xg >= 2.5 if is_over else match.total_xg <= 2.5
        mc_supported = match.mc_over25_prob >= 55 if is_over else match.mc_under25_prob >= 55
        convergence_supported = match.convergence_over if is_over else match.convergence_under
        
        loss_type = ''
        if not is_winner:
            support_count = sum([xg_supported, mc_supported, convergence_supported])
            loss_type = 'UNLUCKY' if support_count >= 2 else 'BAD_ANALYSIS'
        
        return BetResult(
            strategy=strategy, market=market, stake=stake, odds=odds,
            is_winner=is_winner, profit=profit, team=team, match_id=match.match_id,
            tier=tier, score=score, loss_type=loss_type,
            xg_supported=xg_supported, mc_supported=mc_supported,
            convergence_supported=convergence_supported,
        )
    
    def calculate_team_historical(self):
        team_stats = defaultdict(lambda: {'matches': 0, 'over25_wins': 0, 'under35_wins': 0})
        
        for match in self.matches:
            for team in [match.home_team, match.away_team]:
                team_stats[team]['matches'] += 1
                if match.is_over25:
                    team_stats[team]['over25_wins'] += 1
                if match.total_goals < 4:
                    team_stats[team]['under35_wins'] += 1
        
        for team, stats in team_stats.items():
            if team in self.team_profiles and stats['matches'] > 0:
                profile = self.team_profiles[team]
                profile.total_matches = stats['matches']
                
                over25_wr = stats['over25_wins'] / stats['matches']
                under35_wr = stats['under35_wins'] / stats['matches']
                
                over25_roi = (over25_wr * MARKET_ODDS['over_25'] - 1) * 100
                under35_roi = (under35_wr * MARKET_ODDS['under_35'] - 1) * 100
                
                if over25_roi > under35_roi:
                    profile.historical_wr = over25_wr * 100
                    profile.historical_roi = over25_roi
                    profile.best_market = 'over_25'
                else:
                    profile.historical_wr = under35_wr * 100
                    profile.historical_roi = under35_roi
                    profile.best_market = 'under_35'
        
        print(f"✅ Historique calculé pour {len(team_stats)} équipes")
    
    def run_audit(self):
        print("\n" + "="*100)
        print("🏆 AUDIT QUANT 2.0 FINAL - ANALYSE GRANULAIRE PAR ÉQUIPE")
        print("="*100)
        
        for match in self.matches:
            self._audit_team_match(match, match.home_team, is_home=True)
            self._audit_team_match(match, match.away_team, is_home=False)
        
        print(f"\n✅ {len(self.all_bets)} paris analysés pour {len(self.team_results)} équipes")
    
    def _audit_team_match(self, match: MatchData, team: str, is_home: bool):
        for strategy in ALL_STRATEGIES:
            result = self.evaluate_strategy(strategy, match, team, is_home)
            if result:
                if strategy not in self.team_results[team] or self.team_results[team][strategy].name == '':
                    self.team_results[team][strategy] = StrategyStats(name=strategy)
                
                stats = self.team_results[team][strategy]
                stats.total_bets += 1
                stats.profit += result.profit
                
                if result.is_winner:
                    stats.wins += 1
                else:
                    stats.losses += 1
                    if result.loss_type == 'UNLUCKY':
                        stats.unlucky_losses += 1
                    else:
                        stats.bad_analysis_losses += 1
                
                g_stats = self.global_results[strategy]
                g_stats.total_bets += 1
                g_stats.profit += result.profit
                if result.is_winner:
                    g_stats.wins += 1
                else:
                    g_stats.losses += 1
                    if result.loss_type == 'UNLUCKY':
                        g_stats.unlucky_losses += 1
                    else:
                        g_stats.bad_analysis_losses += 1
                
                self.all_bets.append(result)
    
    def print_results(self):
        self._print_global_summary()
        self._print_team_table()
        self._print_strategy_ranking()
        self._print_tier_analysis()
        self._print_loss_analysis()
        self._save_results()
    
    def _print_global_summary(self):
        print("\n" + "="*100)
        print("📊 RÉSUMÉ GLOBAL")
        print("="*100)
        
        total_bets = len(self.all_bets)
        total_wins = sum(1 for b in self.all_bets if b.is_winner)
        total_profit = sum(b.profit for b in self.all_bets)
        total_wr = (total_wins / total_bets * 100) if total_bets > 0 else 0
        
        print(f"""
   📈 Total Paris: {total_bets}
   ✅ Wins: {total_wins} ({total_wr:.1f}%)
   💰 P&L Total: {total_profit:+.1f}u
   🎯 Équipes: {len(self.team_results)}
   🧪 Stratégies: {len(ALL_STRATEGIES)}
""")
    
    def _print_team_table(self):
        print("\n" + "="*200)
        print("🏆 TABLEAU GRANULAIRE - MEILLEURE STRATÉGIE PAR ÉQUIPE")
        print("="*200)
        
        team_data = []
        for team, strategies in self.team_results.items():
            if not strategies:
                continue
            
            best_strategy = None
            best_pnl = float('-inf')
            best_stats = None
            
            for strat_name, stats in strategies.items():
                if stats.total_bets > 0 and stats.profit > best_pnl:
                    best_pnl = stats.profit
                    best_strategy = strat_name
                    best_stats = stats
            
            if best_strategy and best_stats:
                sorted_strats = sorted(
                    [(n, s) for n, s in strategies.items() if s.total_bets > 0],
                    key=lambda x: x[1].profit, reverse=True
                )
                second = sorted_strats[1] if len(sorted_strats) > 1 else None
                
                profile = self.team_profiles.get(team)
                style = profile.current_style[:12] if profile else 'balanced'
                matches = profile.total_matches if profile else 0
                
                total_losses = best_stats.unlucky_losses + best_stats.bad_analysis_losses
                unlucky_pct = (best_stats.unlucky_losses / total_losses * 100) if total_losses > 0 else 100
                
                team_data.append({
                    'team': team, 'best_strategy': best_strategy, 'style': style,
                    'matches': matches, 'bets': best_stats.total_bets, 'wins': best_stats.wins,
                    'losses': best_stats.losses, 'wr': best_stats.win_rate, 
                    'pnl': best_stats.profit, 'unlucky_pct': unlucky_pct,
                    'second': f"{second[0][:20]}({second[1].profit:+.1f})" if second else '-',
                    'total_strats': len([s for s in strategies.values() if s.total_bets > 0])
                })
        
        team_data.sort(key=lambda x: x['pnl'], reverse=True)
        
        print(f"\n{'#':<4} {'Équipe':<25} {'Best Strategy':<26} {'Style':<13} {'M':<4} {'P':<4} {'W':<4} {'L':<4} {'WR':<7} {'P&L':<10} {'Mal%':<6} {'2nd Best':<28} {'#S':<3}")
        print("-"*200)
        
        for i, data in enumerate(team_data, 1):
            if data['pnl'] >= 25: emoji = "💎"
            elif data['pnl'] >= 15: emoji = "🏆"
            elif data['pnl'] >= 8: emoji = "✅"
            elif data['pnl'] >= 3: emoji = "⚪"
            elif data['pnl'] >= 0: emoji = "🔸"
            else: emoji = "❌"
            
            print(f"{emoji}{i:<3} {data['team'][:24]:<25} {data['best_strategy'][:25]:<26} {data['style']:<13} "
                  f"{data['matches']:<4} {data['bets']:<4} {data['wins']:<4} {data['losses']:<4} "
                  f"{data['wr']:.0f}%{'':<4} {data['pnl']:+.1f}u{'':<5} {data['unlucky_pct']:.0f}%{'':<3} "
                  f"{data['second'][:27]:<28} {data['total_strats']:<3}")
        
        total_pnl = sum(d['pnl'] for d in team_data)
        total_bets = sum(d['bets'] for d in team_data)
        total_wins = sum(d['wins'] for d in team_data)
        total_wr = (total_wins / total_bets * 100) if total_bets > 0 else 0
        
        print("-"*200)
        print(f"{'TOTAL':<30} {'':<26} {'':<13} {'':<4} {total_bets:<4} {total_wins:<4} {total_bets-total_wins:<4} "
              f"{total_wr:.0f}%{'':<4} {total_pnl:+.1f}u")
        
        positive = len([d for d in team_data if d['pnl'] > 0])
        negative = len([d for d in team_data if d['pnl'] <= 0])
        elite = len([d for d in team_data if d['pnl'] >= 15])
        print(f"\n   📊 P&L > 0: {positive} | P&L <= 0: {negative} | Élite (>15u): {elite}")
    
    def _print_strategy_ranking(self):
        print("\n" + "="*140)
        print("📈 CLASSEMENT DES 44 STRATÉGIES")
        print("="*140)
        
        sorted_strategies = sorted(
            [(name, stats) for name, stats in self.global_results.items() if stats.total_bets > 0],
            key=lambda x: x[1].profit, reverse=True
        )
        
        print(f"\n{'#':<4} {'Stratégie':<28} {'Éq':<6} {'Paris':<8} {'Wins':<8} {'WR':<10} {'P&L':<14} {'Mal%':<8} {'Verdict'}")
        print("-"*140)
        
        for i, (name, stats) in enumerate(sorted_strategies, 1):
            total_losses = stats.unlucky_losses + stats.bad_analysis_losses
            unlucky_pct = (stats.unlucky_losses / total_losses * 100) if total_losses > 0 else 100
            
            teams_count = sum(1 for t, strats in self.team_results.items() 
                            if name in strats and strats[name].total_bets > 0)
            
            if stats.profit >= 200: emoji, verdict = "💎", "CHAMPION"
            elif stats.profit >= 100: emoji, verdict = "🏆", "EXCELLENT"
            elif stats.profit >= 50: emoji, verdict = "✅", "TRÈS BON"
            elif stats.profit >= 0: emoji, verdict = "🔸", "POSITIF"
            else: emoji, verdict = "❌", "À ÉVITER"
            
            print(f"{emoji}{i:<3} {name:<28} {teams_count:<6} {stats.total_bets:<8} {stats.wins:<8} "
                  f"{stats.win_rate:.1f}%{'':<5} {stats.profit:+.1f}u{'':<8} "
                  f"{unlucky_pct:.0f}%{'':<5} {verdict}")
    
    def _print_tier_analysis(self):
        print("\n" + "="*100)
        print("🎯 ANALYSE PAR TIER")
        print("="*100)
        
        tier_stats = defaultdict(lambda: {'bets': 0, 'wins': 0, 'profit': 0.0, 'teams': set()})
        
        for bet in self.all_bets:
            tier_stats[bet.tier]['bets'] += 1
            tier_stats[bet.tier]['profit'] += bet.profit
            tier_stats[bet.tier]['teams'].add(bet.team)
            if bet.is_winner:
                tier_stats[bet.tier]['wins'] += 1
        
        print(f"\n{'Tier':<24} {'Équipes':<10} {'Paris':<10} {'Wins':<10} {'WR':<12} {'P&L':<14} {'ROI'}")
        print("-"*100)
        
        for tier in ['TIER_1_SNIPER', 'TIER_2_ELITE', 'TIER_3_GOLD', 'TIER_4_STANDARD', 'TIER_5_EXPERIMENTAL']:
            stats = tier_stats[tier]
            if stats['bets'] > 0:
                wr = stats['wins'] / stats['bets'] * 100
                stake = TIER_STAKES.get(tier, 2.0)
                roi = stats['profit'] / (stats['bets'] * stake) * 100
                teams = len(stats['teams'])
                print(f"{tier:<24} {teams:<10} {stats['bets']:<10} {stats['wins']:<10} "
                      f"{wr:.1f}%{'':<7} {stats['profit']:+.1f}u{'':<8} {roi:+.1f}%")
    
    def _print_loss_analysis(self):
        print("\n" + "="*100)
        print("📉 ANALYSE DES PERTES")
        print("="*100)
        
        total_losses = sum(1 for b in self.all_bets if not b.is_winner)
        unlucky = sum(1 for b in self.all_bets if not b.is_winner and b.loss_type == 'UNLUCKY')
        bad = sum(1 for b in self.all_bets if not b.is_winner and b.loss_type == 'BAD_ANALYSIS')
        
        if total_losses > 0:
            print(f"\n   Total pertes: {total_losses}")
            print(f"   🎲 MALCHANCE: {unlucky} ({unlucky/total_losses*100:.1f}%)")
            print(f"   ❌ MAUVAISE ANALYSE: {bad} ({bad/total_losses*100:.1f}%)")
            
            if unlucky/total_losses*100 >= 85:
                print(f"\n   → 🏆 MODÈLE MATHÉMATIQUEMENT CORRECT!")
    
    def _save_results(self):
        results = {
            'audit_date': datetime.now().isoformat(),
            'summary': {
                'total_bets': len(self.all_bets),
                'total_wins': sum(1 for b in self.all_bets if b.is_winner),
                'total_profit': sum(b.profit for b in self.all_bets),
                'teams': len(self.team_results),
            },
            'strategies': {
                name: {'bets': s.total_bets, 'wins': s.wins, 'wr': s.win_rate, 'pnl': s.profit}
                for name, s in self.global_results.items() if s.total_bets > 0
            },
            'teams': {
                team: {
                    'best': max(strats.items(), key=lambda x: x[1].profit)[0] if strats else None,
                    'pnl': max(strats.items(), key=lambda x: x[1].profit)[1].profit if strats else 0,
                }
                for team, strats in self.team_results.items() if strats
            }
        }
        
        with open('audit_FINAL_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n✅ Résultats sauvegardés dans audit_FINAL_results.json")


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║     🏆 AUDIT QUANT 2.0 FINAL - VERSION CORRIGÉE                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
""")
    
    audit = QuantAuditFinal()
    try:
        audit.connect()
        audit.load_team_intelligence()
        audit.load_tactical_matrix()
        audit.load_matches()
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
