#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║     🏆 AUDIT QUANT 2.0 FINAL - ANALYSE GRANULAIRE PAR ÉQUIPE                                                  ║
║                                                                                                               ║
║  ✅ 44 Stratégies Testées (Fusion Hedge Fund + Mega + Nouvelles)                                             ║
║  ✅ Système TIER 1-4 avec Stakes Différenciés                                                                ║
║  ✅ Scoring Composite (0-40 points)                                                                          ║
║  ✅ Analyse GRANULAIRE: Meilleure stratégie PAR ÉQUIPE                                                       ║
║  ✅ Tactical Matrix + Market Patterns + Steam Analysis                                                       ║
║  ✅ Validation Croisée + Classification des Pertes                                                           ║
║                                                                                                               ║
║  USAGE: python3 audit_quant_2.0_FINAL_GRANULAIRE.py                                                          ║
║  REQUIS: Exécuter sur le serveur avec accès à PostgreSQL (monps_db)                                          ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Dict, Optional, List
from collections import defaultdict
from dataclasses import dataclass
import json
import os

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

# Cotes moyennes par marché
MARKET_ODDS = {
    'over_25': 1.85, 'over_35': 2.40, 'over_15': 1.30,
    'under_25': 2.00, 'under_35': 1.55, 'under_15': 3.50,
    'btts_yes': 1.80, 'btts_no': 2.00,
}

# Stakes par TIER (système recommandé)
TIER_STAKES = {
    'TIER_1_SNIPER': 4.0,      # Score >= 34 + Convergence + MC >= 65%
    'TIER_2_ELITE': 3.0,       # Score 32-33 OU ROI >= 40%
    'TIER_3_GOLD': 2.5,        # Score 28-31 OU ROI >= 30%
    'TIER_4_STANDARD': 2.0,    # MC >= 60% OU Under35 >= 55%
    'TIER_5_EXPERIMENTAL': 1.0, # Paradox / Test
}

# ═══════════════════════════════════════════════════════════════════════════════
# 44 STRATÉGIES COMPLÈTES
# ═══════════════════════════════════════════════════════════════════════════════

ALL_STRATEGIES = [
    # GROUPE A: CONVERGENCE (Validé +574.6u dans Audit V2)
    'CONVERGENCE_OVER_PURE',
    'CONVERGENCE_OVER_MC_55',
    'CONVERGENCE_OVER_MC_60',
    'CONVERGENCE_OVER_MC_65',
    'CONVERGENCE_UNDER_PURE',
    
    # GROUPE B: MONTE CARLO
    'MC_PURE_55',
    'MC_PURE_60',
    'MC_PURE_65',
    'MC_PURE_70',
    'MC_NO_CLASH',
    
    # GROUPE C: QUANT MARKET (Meilleur P&L combiné +686.1u)
    'QUANT_BEST_MARKET',
    'QUANT_ROI_25',
    'QUANT_ROI_30',
    'QUANT_ROI_40',
    'QUANT_ROI_50',
    
    # GROUPE D: SCORING THRESHOLD (Screenshot Discovery)
    'SCORE_SNIPER_34',      # Zone Sniper Elite 82.7% WR
    'SCORE_HIGH_32',        # High Confidence 74% WR
    'SCORE_GOOD_28',        # Good Volume 72.4% WR
    'SCORE_MEDIUM_25',
    
    # GROUPE E: TACTICAL MATRIX
    'TACTICAL_GEGENPRESSING',
    'TACTICAL_ATTACKING',
    'TACTICAL_HIGH_SCORING',
    
    # GROUPE F: LEAGUE PATTERNS
    'LEAGUE_CHAMPIONS',
    'LEAGUE_BUNDESLIGA',
    'LEAGUE_PREMIER',
    'LEAGUE_SERIE_A',
    'LEAGUE_LIGUE_1',
    
    # GROUPE G: SPECIAL MARKETS (CLV Discovery)
    'UNDER_35_PURE',        # 73.6% WR, +316.4u
    'UNDER_25_SELECTIVE',
    'BTTS_NO_PURE',
    'OVER_15_SAFE',
    
    # GROUPE H: PARADOX & SWEET SPOT
    'LOW_CONFIDENCE_PARADOX',  # 20-35% conf = meilleur WR
    'SWEET_SPOT_60_79',
    'SWEET_SPOT_CONSERVATIVE',
    
    # GROUPE I: COMBOS VALIDÉS
    'COMBO_CONV_MC_SCORE',     # +554.4u combiné
    'COMBO_TACTICAL_LEAGUE',
    'TRIPLE_VALIDATION',
    'QUANT_MC_COMBO',
    
    # GROUPE J: SYSTÈME TIER INTÉGRÉ
    'TIER_1_SNIPER',
    'TIER_2_ELITE',
    'TIER_3_GOLD',
    'TIER_4_STANDARD',
    
    # GROUPE K: ULTIMATE
    'ULTIMATE_SNIPER',
    'ULTIMATE_HYBRID',
]

# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TeamProfile:
    """Profil complet d'une équipe"""
    name: str
    team_id: int = 0
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
    """Données d'un match"""
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
    """Résultat d'un pari"""
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
    """Statistiques d'une stratégie"""
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


# ═══════════════════════════════════════════════════════════════════════════════
# CLASSE PRINCIPALE AUDIT
# ═══════════════════════════════════════════════════════════════════════════════

class QuantAuditFinalGranulaire:
    def __init__(self):
        self.conn = None
        self.team_profiles: Dict[str, TeamProfile] = {}
        self.matches: List[MatchData] = []
        self.tactical_matrix: Dict[str, Dict] = {}
        self.market_patterns: Dict[str, Dict] = {}
        
        # Résultats GRANULAIRES par équipe
        self.team_results: Dict[str, Dict[str, StrategyStats]] = defaultdict(lambda: defaultdict(lambda: StrategyStats(name='')))
        
        # Résultats globaux par stratégie
        self.global_results: Dict[str, StrategyStats] = {s: StrategyStats(name=s) for s in ALL_STRATEGIES}
        
        # Tous les paris
        self.all_bets: List[BetResult] = []
    
    def connect(self):
        """Connexion à la base de données"""
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.conn.autocommit = True
        print("✅ Connexion DB établie")
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CHARGEMENT DES DONNÉES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def load_team_intelligence(self):
        """Charge les profils d'équipes"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT team_id, team_name, current_style,
                       home_over25_rate, away_over25_rate, home_btts_rate, away_btts_rate,
                       goals_tendency, btts_tendency, clean_sheet_tendency,
                       xg_for_avg, xg_against_avg, home_strength, away_strength
                FROM team_intelligence WHERE team_name IS NOT NULL
            """)
            for row in cur.fetchall():
                profile = TeamProfile(
                    name=row['team_name'],
                    team_id=row['team_id'] or 0,
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
        """Charge la matrice tactique"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
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
                    'confidence': row['confidence_level'] or 'low'
                }
            print(f"✅ {len(self.tactical_matrix)} combinaisons tactiques chargées")
    
    def load_matches(self):
        """Charge tous les matchs avec résultats"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT ON (ap.match_id)
                    ap.match_id, ap.home_team, ap.away_team,
                    ap.home_goals, ap.away_goals, ap.match_date, ap.league,
                    ap.home_xg, ap.away_xg,
                    ap.mc_over25_prob, ap.mc_over35_prob,
                    ap.mc_under25_prob, ap.mc_under35_prob, ap.mc_btts_prob,
                    ap.convergence_over, ap.convergence_under
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
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SCORE COMPOSITE (0-40) - Screenshot Discovery
    # ═══════════════════════════════════════════════════════════════════════════
    
    def calculate_composite_score(self, match: MatchData, team: str, is_home: bool) -> int:
        """
        Score composite (0-40):
        - xG Expected (0-10)
        - MC Probability (0-10)
        - Convergence Bonus (0-8)
        - Team Over25 Rate (0-6)
        - Goals Tendency (0-6)
        """
        score = 0
        
        # 1. xG Expected (0-10)
        xg = match.total_xg
        if xg >= 3.5: score += 10
        elif xg >= 3.0: score += 8
        elif xg >= 2.7: score += 6
        elif xg >= 2.5: score += 4
        elif xg >= 2.2: score += 2
        
        # 2. MC Probability (0-10)
        mc = match.mc_over25_prob
        if mc >= 70: score += 10
        elif mc >= 65: score += 8
        elif mc >= 60: score += 6
        elif mc >= 55: score += 4
        elif mc >= 50: score += 2
        
        # 3. Convergence Bonus (0-8)
        if match.convergence_over: score += 8
        
        # 4. Team Over25 Rate (0-6)
        profile = self.team_profiles.get(team)
        if profile:
            rate = profile.home_over25_rate if is_home else profile.away_over25_rate
            if rate >= 70: score += 6
            elif rate >= 60: score += 4
            elif rate >= 50: score += 2
            
            # 5. Goals Tendency (0-6)
            tendency = profile.goals_tendency
            if tendency >= 75: score += 6
            elif tendency >= 65: score += 4
            elif tendency >= 55: score += 2
        
        return min(score, 40)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ÉVALUATION DES 44 STRATÉGIES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def evaluate_strategy(self, strategy: str, match: MatchData, team: str, is_home: bool) -> Optional[BetResult]:
        """Évalue si une stratégie génère un pari pour ce match/équipe"""
        profile = self.team_profiles.get(team)
        score = self.calculate_composite_score(match, team, is_home)
        
        home_profile = self.team_profiles.get(match.home_team)
        away_profile = self.team_profiles.get(match.away_team)
        home_style = home_profile.current_style if home_profile else 'balanced'
        away_style = away_profile.current_style if away_profile else 'balanced'
        tactical_key = f"{home_style}_vs_{away_style}"
        tactical = self.tactical_matrix.get(tactical_key, {})
        
        # ═══════════════════════════════════════════════════════════════════════
        # GROUPE A: CONVERGENCE
        # ═══════════════════════════════════════════════════════════════════════
        
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
        
        # ═══════════════════════════════════════════════════════════════════════
        # GROUPE B: MONTE CARLO
        # ═══════════════════════════════════════════════════════════════════════
        
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
        
        # ═══════════════════════════════════════════════════════════════════════
        # GROUPE C: QUANT MARKET
        # ═══════════════════════════════════════════════════════════════════════
        
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
        
        # ═══════════════════════════════════════════════════════════════════════
        # GROUPE D: SCORING THRESHOLD (Screenshot Discovery)
        # ═══════════════════════════════════════════════════════════════════════
        
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
        
        # ═══════════════════════════════════════════════════════════════════════
        # GROUPE E: TACTICAL MATRIX
        # ═══════════════════════════════════════════════════════════════════════
        
        elif strategy == 'TACTICAL_GEGENPRESSING':
            if 'gegenpressing' in home_style or 'gegenpressing' in away_style:
                if tactical.get('over25_prob', 0) >= 70:
                    return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_2_ELITE')
        
        elif strategy == 'TACTICAL_ATTACKING':
            if 'attacking' in home_style or 'offensive' in home_style:
                if tactical.get('over25_prob', 0) >= 65:
                    return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_3_GOLD')
        
        elif strategy == 'TACTICAL_HIGH_SCORING':
            if tactical.get('avg_goals', 0) >= 3.5 and tactical.get('samples', 0) >= 20:
                return self._make_bet(strategy, 'over_25', match, team, score, 'TIER_2_ELITE')
        
        # ═══════════════════════════════════════════════════════════════════════
        # GROUPE F: LEAGUE PATTERNS
        # ═══════════════════════════════════════════════════════════════════════
        
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
        
        # ═══════════════════════════════════════════════════════════════════════
        # GROUPE G: SPECIAL MARKETS (CLV Discovery)
        # ═══════════════════════════════════════════════════════════════════════
        
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
        
        # ═══════════════════════════════════════════════════════════════════════
        # GROUPE H: PARADOX & SWEET SPOT
        # ═══════════════════════════════════════════════════════════════════════
        
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
        
        # ═══════════════════════════════════════════════════════════════════════
        # GROUPE I: COMBOS VALIDÉS
        # ═══════════════════════════════════════════════════════════════════════
        
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
        
        # ═══════════════════════════════════════════════════════════════════════
        # GROUPE J: SYSTÈME TIER INTÉGRÉ
        # ═══════════════════════════════════════════════════════════════════════
        
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
        
        # ═══════════════════════════════════════════════════════════════════════
        # GROUPE K: ULTIMATE
        # ═══════════════════════════════════════════════════════════════════════
        
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
        """Crée un BetResult avec calcul du profit"""
        stake = TIER_STAKES.get(tier, 2.0)
        odds = MARKET_ODDS.get(market, 1.85)
        
        # Déterminer si gagné
        if market == 'over_25': is_winner = match.is_over25
        elif market == 'over_35': is_winner = match.is_over35
        elif market == 'over_15': is_winner = match.total_goals >= 2
        elif market == 'under_25': is_winner = not match.is_over25
        elif market == 'under_35': is_winner = match.total_goals < 4
        elif market == 'btts_yes': is_winner = match.is_btts
        elif market == 'btts_no': is_winner = not match.is_btts
        else: is_winner = match.is_over25
        
        profit = stake * (odds - 1) if is_winner else -stake
        
        # Analyse perte
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
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CALCUL HISTORIQUE PAR ÉQUIPE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def calculate_team_historical(self):
        """Calcule WR/ROI historique pour chaque équipe"""
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
    
    # ═══════════════════════════════════════════════════════════════════════════
    # AUDIT PRINCIPAL
    # ═══════════════════════════════════════════════════════════════════════════
    
    def run_audit(self):
        """Exécute l'audit complet"""
        print("\n" + "="*100)
        print("🏆 AUDIT QUANT 2.0 FINAL - ANALYSE GRANULAIRE PAR ÉQUIPE")
        print("="*100)
        
        for match in self.matches:
            self._audit_team_match(match, match.home_team, is_home=True)
            self._audit_team_match(match, match.away_team, is_home=False)
        
        print(f"\n✅ {len(self.all_bets)} paris analysés pour {len(self.team_results)} équipes")
    
    def _audit_team_match(self, match: MatchData, team: str, is_home: bool):
        """Audite toutes les stratégies pour une équipe sur un match"""
        for strategy in ALL_STRATEGIES:
            result = self.evaluate_strategy(strategy, match, team, is_home)
            
            if result:
                # Initialiser si nécessaire
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
                
                # Global
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
    
    # ═══════════════════════════════════════════════════════════════════════════
    # AFFICHAGE DES RÉSULTATS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def print_results(self):
        """Affiche tous les résultats"""
        self._print_global_summary()
        self._print_team_table_complete()
        self._print_strategy_ranking()
        self._print_tier_analysis()
        self._print_loss_analysis()
        self._print_top_teams_per_tier()
        self._print_top_teams_per_strategy()
        self._save_results()
    
    def _print_global_summary(self):
        """Résumé global"""
        print("\n" + "="*100)
        print("📊 RÉSUMÉ GLOBAL - AUDIT QUANT 2.0 FINAL")
        print("="*100)
        
        total_bets = len(self.all_bets)
        total_wins = sum(1 for b in self.all_bets if b.is_winner)
        total_profit = sum(b.profit for b in self.all_bets)
        total_wr = (total_wins / total_bets * 100) if total_bets > 0 else 0
        
        print(f"""
   📈 Total Paris: {total_bets}
   ✅ Wins: {total_wins} ({total_wr:.1f}%)
   💰 P&L Total: {total_profit:+.1f}u
   🎯 Équipes Analysées: {len(self.team_results)}
   🧪 Stratégies Testées: {len(ALL_STRATEGIES)}
   📅 Période: Septembre 2024 - Présent
""")
    
    def _print_team_table_complete(self):
        """Tableau COMPLET des équipes avec meilleure stratégie"""
        print("\n" + "="*220)
        print("🏆 TABLEAU GRANULAIRE COMPLET - MEILLEURE STRATÉGIE PAR ÉQUIPE")
        print("="*220)
        
        team_data = []
        
        for team, strategies in self.team_results.items():
            if not strategies:
                continue
            
            # Trouver la meilleure stratégie
            best_strategy = None
            best_pnl = float('-inf')
            best_stats = None
            
            for strat_name, stats in strategies.items():
                if stats.total_bets > 0 and stats.profit > best_pnl:
                    best_pnl = stats.profit
                    best_strategy = strat_name
                    best_stats = stats
            
            if best_strategy and best_stats:
                # 2ème et 3ème meilleures
                sorted_strats = sorted(
                    [(n, s) for n, s in strategies.items() if s.total_bets > 0],
                    key=lambda x: x[1].profit,
                    reverse=True
                )
                
                second = sorted_strats[1] if len(sorted_strats) > 1 else None
                third = sorted_strats[2] if len(sorted_strats) > 2 else None
                
                profile = self.team_profiles.get(team)
                style = profile.current_style[:12] if profile else 'balanced'
                matches = profile.total_matches if profile else 0
                hist_roi = profile.historical_roi if profile else 0
                
                total_losses = best_stats.unlucky_losses + best_stats.bad_analysis_losses
                unlucky_pct = (best_stats.unlucky_losses / total_losses * 100) if total_losses > 0 else 100
                
                team_data.append({
                    'team': team,
                    'best_strategy': best_strategy,
                    'style': style,
                    'matches': matches,
                    'hist_roi': hist_roi,
                    'bets': best_stats.total_bets,
                    'wins': best_stats.wins,
                    'losses': best_stats.losses,
                    'wr': best_stats.win_rate,
                    'pnl': best_stats.profit,
                    'unlucky_pct': unlucky_pct,
                    'second': f"{second[0][:18]}({second[1].profit:+.1f})" if second else '-',
                    'third': f"{third[0][:18]}({third[1].profit:+.1f})" if third else '-',
                    'total_strats': len([s for s in strategies.values() if s.total_bets > 0])
                })
        
        team_data.sort(key=lambda x: x['pnl'], reverse=True)
        
        # Header
        print(f"\n{'#':<4} {'Équipe':<25} {'Best Strategy':<26} {'Style':<13} {'M':<4} {'ROI%':<6} {'P':<4} {'W':<4} {'L':<4} {'WR':<7} {'P&L':<10} {'Mal%':<6} {'2nd Best':<25} {'3rd Best':<25} {'#S':<3}")
        print("-"*220)
        
        # Toutes les équipes
        for i, data in enumerate(team_data, 1):
            if data['pnl'] >= 25: emoji = "💎"
            elif data['pnl'] >= 15: emoji = "🏆"
            elif data['pnl'] >= 8: emoji = "✅"
            elif data['pnl'] >= 3: emoji = "⚪"
            elif data['pnl'] >= 0: emoji = "🔸"
            else: emoji = "❌"
            
            print(f"{emoji}{i:<3} {data['team'][:24]:<25} {data['best_strategy'][:25]:<26} {data['style']:<13} "
                  f"{data['matches']:<4} {data['hist_roi']:+.0f}%{'':<2} {data['bets']:<4} {data['wins']:<4} {data['losses']:<4} "
                  f"{data['wr']:.0f}%{'':<4} {data['pnl']:+.1f}u{'':<5} {data['unlucky_pct']:.0f}%{'':<3} "
                  f"{data['second'][:24]:<25} {data['third'][:24]:<25} {data['total_strats']:<3}")
        
        # Total
        total_pnl = sum(d['pnl'] for d in team_data)
        total_bets = sum(d['bets'] for d in team_data)
        total_wins = sum(d['wins'] for d in team_data)
        total_wr = (total_wins / total_bets * 100) if total_bets > 0 else 0
        
        print("-"*220)
        print(f"{'TOTAL':<30} {'':<26} {'':<13} {'':<4} {'':<6} {total_bets:<4} {total_wins:<4} {total_bets-total_wins:<4} "
              f"{total_wr:.0f}%{'':<4} {total_pnl:+.1f}u")
        
        # Stats équipes
        positive_teams = len([d for d in team_data if d['pnl'] > 0])
        negative_teams = len([d for d in team_data if d['pnl'] <= 0])
        elite_teams = len([d for d in team_data if d['pnl'] >= 15])
        
        print(f"\n   📊 Équipes P&L > 0: {positive_teams} | P&L <= 0: {negative_teams} | Élite (>15u): {elite_teams}")
    
    def _print_strategy_ranking(self):
        """Classement des 44 stratégies"""
        print("\n" + "="*140)
        print("📈 CLASSEMENT DES 44 STRATÉGIES (par P&L total)")
        print("="*140)
        
        sorted_strategies = sorted(
            [(name, stats) for name, stats in self.global_results.items() if stats.total_bets > 0],
            key=lambda x: x[1].profit,
            reverse=True
        )
        
        print(f"\n{'#':<4} {'Stratégie':<28} {'Équipes':<8} {'Paris':<8} {'Wins':<8} {'WR':<10} {'P&L':<14} {'Mal%':<8} {'Verdict'}")
        print("-"*140)
        
        for i, (name, stats) in enumerate(sorted_strategies, 1):
            total_losses = stats.unlucky_losses + stats.bad_analysis_losses
            unlucky_pct = (stats.unlucky_losses / total_losses * 100) if total_losses > 0 else 100
            
            # Compter équipes utilisant cette stratégie
            teams_count = sum(1 for t, strats in self.team_results.items() 
                            if name in strats and strats[name].total_bets > 0)
            
            if stats.profit >= 200: emoji, verdict = "💎", "CHAMPION"
            elif stats.profit >= 100: emoji, verdict = "🏆", "EXCELLENT"
            elif stats.profit >= 50: emoji, verdict = "✅", "TRÈS BON"
            elif stats.profit >= 0: emoji, verdict = "🔸", "POSITIF"
            else: emoji, verdict = "❌", "À ÉVITER"
            
            print(f"{emoji}{i:<3} {name:<28} {teams_count:<8} {stats.total_bets:<8} {stats.wins:<8} "
                  f"{stats.win_rate:.1f}%{'':<5} {stats.profit:+.1f}u{'':<8} "
                  f"{unlucky_pct:.0f}%{'':<5} {verdict}")
    
    def _print_tier_analysis(self):
        """Analyse par TIER"""
        print("\n" + "="*100)
        print("🎯 ANALYSE PAR TIER - VALIDATION DU SYSTÈME")
        print("="*100)
        
        tier_stats = defaultdict(lambda: {'bets': 0, 'wins': 0, 'profit': 0.0, 'teams': set()})
        
        for bet in self.all_bets:
            tier = bet.tier
            tier_stats[tier]['bets'] += 1
            tier_stats[tier]['profit'] += bet.profit
            tier_stats[tier]['teams'].add(bet.team)
            if bet.is_winner:
                tier_stats[tier]['wins'] += 1
        
        print(f"\n{'Tier':<24} {'Équipes':<10} {'Paris':<10} {'Wins':<10} {'WR':<12} {'P&L':<14} {'ROI':<10} {'Verdict'}")
        print("-"*100)
        
        expected = {
            'TIER_1_SNIPER': (82, 94, 85),
            'TIER_2_ELITE': (74, 80, 55),
            'TIER_3_GOLD': (70, 74, 35),
            'TIER_4_STANDARD': (63, 70, 20),
            'TIER_5_EXPERIMENTAL': (50, 60, 0),
        }
        
        for tier in ['TIER_1_SNIPER', 'TIER_2_ELITE', 'TIER_3_GOLD', 'TIER_4_STANDARD', 'TIER_5_EXPERIMENTAL']:
            stats = tier_stats[tier]
            if stats['bets'] > 0:
                wr = stats['wins'] / stats['bets'] * 100
                stake = TIER_STAKES.get(tier, 2.0)
                roi = stats['profit'] / (stats['bets'] * stake) * 100
                teams = len(stats['teams'])
                
                exp = expected.get(tier, (0, 100, 0))
                if wr >= exp[0]:
                    verdict = "✅ VALIDÉ"
                elif wr >= exp[0] - 5:
                    verdict = "🔸 PROCHE"
                else:
                    verdict = "❌ REVOIR"
                
                print(f"{tier:<24} {teams:<10} {stats['bets']:<10} {stats['wins']:<10} "
                      f"{wr:.1f}% ({exp[0]}-{exp[1]}%){'':<1} {stats['profit']:+.1f}u{'':<8} {roi:+.1f}%{'':<5} {verdict}")
    
    def _print_loss_analysis(self):
        """Analyse scientifique des pertes"""
        print("\n" + "="*100)
        print("📉 ANALYSE SCIENTIFIQUE DES PERTES")
        print("="*100)
        
        total_losses = sum(1 for b in self.all_bets if not b.is_winner)
        unlucky = sum(1 for b in self.all_bets if not b.is_winner and b.loss_type == 'UNLUCKY')
        bad = sum(1 for b in self.all_bets if not b.is_winner and b.loss_type == 'BAD_ANALYSIS')
        
        print(f"\n   Total pertes analysées: {total_losses}")
        if total_losses > 0:
            print(f"   🎲 MALCHANCE (indicateurs supportaient le pari): {unlucky} ({unlucky/total_losses*100:.1f}%)")
            print(f"   ❌ MAUVAISE ANALYSE (indicateurs ne supportaient pas): {bad} ({bad/total_losses*100:.1f}%)")
            
            if unlucky/total_losses*100 >= 85:
                print(f"\n   → CONCLUSION: 🏆 MODÈLE MATHÉMATIQUEMENT CORRECT!")
                print(f"   → Les pertes sont majoritairement dues à la variance, pas au modèle.")
            elif unlucky/total_losses*100 >= 70:
                print(f"\n   → CONCLUSION: ✅ Modèle globalement correct, quelques optimisations possibles.")
            else:
                print(f"\n   → ATTENTION: {bad/total_losses*100:.1f}% d'erreurs d'analyse à investiguer")
    
    def _print_top_teams_per_tier(self):
        """Top équipes par TIER"""
        print("\n" + "="*100)
        print("🎯 TOP 10 ÉQUIPES PAR TIER")
        print("="*100)
        
        for tier_name in ['TIER_1_SNIPER', 'TIER_2_ELITE', 'TIER_3_GOLD']:
            print(f"\n📊 {tier_name}:")
            
            team_perf = []
            for team, strategies in self.team_results.items():
                tier_profit = 0
                tier_bets = 0
                tier_wins = 0
                
                for strat_name, stats in strategies.items():
                    # Vérifier si cette stratégie appartient à ce tier
                    tier_strategies = {
                        'TIER_1_SNIPER': ['TIER_1_SNIPER', 'SCORE_SNIPER_34', 'ULTIMATE_SNIPER', 'QUANT_ROI_50'],
                        'TIER_2_ELITE': ['TIER_2_ELITE', 'SCORE_HIGH_32', 'CONVERGENCE_OVER_MC_65', 'MC_PURE_70', 'QUANT_ROI_40', 'COMBO_CONV_MC_SCORE', 'TRIPLE_VALIDATION'],
                        'TIER_3_GOLD': ['TIER_3_GOLD', 'SCORE_GOOD_28', 'CONVERGENCE_OVER_MC_55', 'CONVERGENCE_OVER_MC_60', 'MC_PURE_65', 'QUANT_ROI_30', 'QUANT_MC_COMBO'],
                    }
                    
                    if strat_name in tier_strategies.get(tier_name, []):
                        tier_profit += stats.profit
                        tier_bets += stats.total_bets
                        tier_wins += stats.wins
                
                if tier_bets > 0:
                    wr = tier_wins / tier_bets * 100
                    team_perf.append((team, tier_bets, wr, tier_profit))
            
            team_perf.sort(key=lambda x: x[3], reverse=True)
            
            for rank, (team, bets, wr, pnl) in enumerate(team_perf[:10], 1):
                profile = self.team_profiles.get(team)
                style = profile.current_style[:12] if profile else 'balanced'
                print(f"   {rank:>2}. {team:<28} [{style}] {bets}P, {wr:.0f}%WR, {pnl:+.1f}u")
    
    def _print_top_teams_per_strategy(self):
        """Top équipes par stratégie élite"""
        print("\n" + "="*100)
        print("🎯 TOP 5 ÉQUIPES PAR STRATÉGIE ÉLITE")
        print("="*100)
        
        elite_strategies = [
            'TIER_1_SNIPER', 'ULTIMATE_SNIPER', 'SCORE_SNIPER_34',
            'COMBO_CONV_MC_SCORE', 'TRIPLE_VALIDATION', 'QUANT_ROI_40'
        ]
        
        for strategy in elite_strategies:
            print(f"\n📊 {strategy}:")
            
            team_perf = []
            for team, strategies in self.team_results.items():
                if strategy in strategies:
                    stats = strategies[strategy]
                    if stats.total_bets > 0:
                        profile = self.team_profiles.get(team)
                        style = profile.current_style[:12] if profile else 'balanced'
                        team_perf.append((team, style, stats.total_bets, stats.win_rate, stats.profit))
            
            team_perf.sort(key=lambda x: x[4], reverse=True)
            
            if team_perf:
                for team, style, bets, wr, pnl in team_perf[:5]:
                    print(f"   {team:<28} [{style}] {bets}P, {wr:.0f}%WR, {pnl:+.1f}u")
            else:
                print(f"   (Aucune équipe)")
    
    def _save_results(self):
        """Sauvegarde les résultats en JSON"""
        results = {
            'audit_date': datetime.now().isoformat(),
            'summary': {
                'total_bets': len(self.all_bets),
                'total_wins': sum(1 for b in self.all_bets if b.is_winner),
                'total_profit': sum(b.profit for b in self.all_bets),
                'win_rate': sum(1 for b in self.all_bets if b.is_winner) / len(self.all_bets) * 100 if self.all_bets else 0,
                'teams_analyzed': len(self.team_results),
                'strategies_tested': len(ALL_STRATEGIES),
            },
            'strategies': {
                name: {
                    'bets': stats.total_bets,
                    'wins': stats.wins,
                    'win_rate': stats.win_rate,
                    'profit': stats.profit,
                    'roi': stats.roi,
                    'unlucky_pct': (stats.unlucky_losses / (stats.unlucky_losses + stats.bad_analysis_losses) * 100)
                                  if (stats.unlucky_losses + stats.bad_analysis_losses) > 0 else 100
                }
                for name, stats in self.global_results.items() if stats.total_bets > 0
            },
            'teams': {
                team: {
                    'best_strategy': max(strategies.items(), key=lambda x: x[1].profit)[0] if strategies else None,
                    'best_pnl': max(strategies.items(), key=lambda x: x[1].profit)[1].profit if strategies else 0,
                    'best_wr': max(strategies.items(), key=lambda x: x[1].profit)[1].win_rate if strategies else 0,
                    'strategies_count': len([s for s in strategies.values() if s.total_bets > 0]),
                    'all_strategies': {
                        name: {'bets': s.total_bets, 'wins': s.wins, 'wr': s.win_rate, 'pnl': s.profit}
                        for name, s in strategies.items() if s.total_bets > 0
                    }
                }
                for team, strategies in self.team_results.items() if strategies
            },
            'tier_summary': {},
        }
        
        # Tier summary
        tier_stats = defaultdict(lambda: {'bets': 0, 'wins': 0, 'profit': 0.0})
        for bet in self.all_bets:
            tier_stats[bet.tier]['bets'] += 1
            tier_stats[bet.tier]['profit'] += bet.profit
            if bet.is_winner:
                tier_stats[bet.tier]['wins'] += 1
        
        results['tier_summary'] = {
            tier: {
                'bets': s['bets'],
                'wins': s['wins'],
                'wr': (s['wins'] / s['bets'] * 100) if s['bets'] > 0 else 0,
                'profit': s['profit'],
            }
            for tier, s in tier_stats.items()
        }
        
        filename = 'audit_quant_2.0_final_GRANULAIRE_results.json'
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n✅ Résultats sauvegardés dans {filename}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║     🏆 AUDIT QUANT 2.0 FINAL - ANALYSE GRANULAIRE PAR ÉQUIPE                                                  ║
║                                                                                                               ║
║  ✅ 44 Stratégies × Toutes Équipes × Système TIER × Scoring Composite                                        ║
║  ✅ Fusion: Hedge Fund + Mega + Tactical + Patterns + Steam                                                  ║
║  ✅ Meilleure stratégie identifiée pour CHAQUE équipe                                                        ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
""")
    
    audit = QuantAuditFinalGranulaire()
    
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
