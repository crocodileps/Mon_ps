#!/usr/bin/env python3
"""
🔬 CLV ORCHESTRATOR V5 SCIENTIFIC - ANALYSE COMPLÈTE

PHILOSOPHIE:
- Collecter TOUS les picks (aucun filtrage)
- Analyser TOUS les marchés (forces ET faiblesses)
- Apprendre des erreurs pour améliorer
- Approche scientifique et professionnelle

OBJECTIF:
- Comprendre pourquoi certains marchés performent mal
- Identifier les patterns de succès/échec
- Améliorer continuellement le modèle
"""
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from datetime import datetime
from decimal import Decimal
import json
import logging
import os
import math
from typing import Dict, List, Tuple

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('V5Scientific')

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
}

# ============================================================
# CONFIGURATION SCIENTIFIQUE - TOUS MARCHÉS ANALYSÉS
# ============================================================

# Calibration initiale basée sur backtest (sera mise à jour automatiquement)
MARKET_ANALYSIS = {
    # Format: 'market': {'base_wr': WR attendu, 'volatility': risque, 'category': type}
    'home':     {'base_wr': 45, 'volatility': 'high', 'category': '1x2', 'backtest_wr': 12.5},
    'draw':     {'base_wr': 28, 'volatility': 'high', 'category': '1x2', 'backtest_wr': 25.0},
    'away':     {'base_wr': 35, 'volatility': 'high', 'category': '1x2', 'backtest_wr': 42.9},
    'dc_1x':    {'base_wr': 65, 'volatility': 'low', 'category': 'double_chance', 'backtest_wr': 50.0},
    'dc_x2':    {'base_wr': 55, 'volatility': 'medium', 'category': 'double_chance', 'backtest_wr': 37.5},
    'dc_12':    {'base_wr': 72, 'volatility': 'low', 'category': 'double_chance', 'backtest_wr': 100.0},
    'btts_yes': {'base_wr': 55, 'volatility': 'medium', 'category': 'btts', 'backtest_wr': 100.0},
    'btts_no':  {'base_wr': 45, 'volatility': 'medium', 'category': 'btts', 'backtest_wr': 50.0},
    'over_15':  {'base_wr': 75, 'volatility': 'low', 'category': 'totals', 'backtest_wr': None},
    'under_15': {'base_wr': 25, 'volatility': 'high', 'category': 'totals', 'backtest_wr': None},
    'over_25':  {'base_wr': 52, 'volatility': 'medium', 'category': 'totals', 'backtest_wr': 75.0},
    'under_25': {'base_wr': 48, 'volatility': 'medium', 'category': 'totals', 'backtest_wr': 28.6},
    'over_35':  {'base_wr': 30, 'volatility': 'high', 'category': 'totals', 'backtest_wr': None},
    'under_35': {'base_wr': 70, 'volatility': 'low', 'category': 'totals', 'backtest_wr': None},
}

# Facteurs de cotes (analyse scientifique)
ODDS_ANALYSIS = {
    (1.0, 1.3): {'reliability': 95, 'risk': 'very_low', 'typical_wr': 80},
    (1.3, 1.6): {'reliability': 85, 'risk': 'low', 'typical_wr': 70},
    (1.6, 2.0): {'reliability': 75, 'risk': 'medium', 'typical_wr': 55},
    (2.0, 2.5): {'reliability': 65, 'risk': 'medium', 'typical_wr': 45},
    (2.5, 3.0): {'reliability': 55, 'risk': 'high', 'typical_wr': 38},
    (3.0, 4.0): {'reliability': 45, 'risk': 'high', 'typical_wr': 30},
    (4.0, 6.0): {'reliability': 30, 'risk': 'very_high', 'typical_wr': 20},
    (6.0, 99):  {'reliability': 15, 'risk': 'extreme', 'typical_wr': 12},
}


def get_odds_analysis(odds: float) -> Dict:
    """Analyse scientifique des cotes"""
    for (low, high), analysis in ODDS_ANALYSIS.items():
        if low <= odds < high:
            return analysis
    return {'reliability': 10, 'risk': 'extreme', 'typical_wr': 10}


def poisson_prob(lam: float, k: int) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    try:
        return (math.exp(-lam) * (lam ** k)) / math.factorial(k)
    except:
        return 0.0


def calculate_match_probabilities(home_xg: float, away_xg: float) -> Dict[str, float]:
    """Calcule toutes les probabilités via Poisson"""
    max_goals = 8
    matrix = {}
    for h in range(max_goals):
        for a in range(max_goals):
            matrix[(h, a)] = poisson_prob(home_xg, h) * poisson_prob(away_xg, a)
    
    home_win = sum(p for (h, a), p in matrix.items() if h > a)
    draw = sum(p for (h, a), p in matrix.items() if h == a)
    away_win = sum(p for (h, a), p in matrix.items() if h < a)
    btts_yes = sum(p for (h, a), p in matrix.items() if h > 0 and a > 0)
    over_15 = sum(p for (h, a), p in matrix.items() if h + a > 1)
    over_25 = sum(p for (h, a), p in matrix.items() if h + a > 2)
    over_35 = sum(p for (h, a), p in matrix.items() if h + a > 3)
    
    return {
        'home': home_win, 'draw': draw, 'away': away_win,
        'dc_1x': home_win + draw, 'dc_x2': draw + away_win, 'dc_12': home_win + away_win,
        'btts_yes': btts_yes, 'btts_no': 1 - btts_yes,
        'over_15': over_15, 'under_15': 1 - over_15,
        'over_25': over_25, 'under_25': 1 - over_25,
        'over_35': over_35, 'under_35': 1 - over_35,
    }


def calculate_score_scientific(prob: float, odds: float, market_type: str, 
                               team_factor: float = 1.0, h2h_factor: float = 1.0) -> Dict:
    """
    SCORING SCIENTIFIQUE COMPLET
    
    Retourne un dictionnaire avec:
    - score: score global (0-100)
    - confidence: niveau de confiance
    - risk_level: niveau de risque
    - expected_wr: win rate attendu
    - value_edge: edge de value
    - kelly: kelly optimal
    - analysis: analyse détaillée
    """
    result = {
        'score': 0,
        'confidence': 'none',
        'risk_level': 'unknown',
        'expected_wr': 0,
        'value_edge': 0,
        'kelly': 0,
        'analysis': {}
    }
    
    if not odds or odds <= 1 or prob <= 0:
        return result
    
    implied = 1 / odds
    edge = prob - implied
    edge_pct = edge * 100
    
    # Kelly
    if edge > 0:
        kelly = min((edge / (odds - 1)) * 100, 10)
    else:
        kelly = 0
    
    # Analyse marché
    market_info = MARKET_ANALYSIS.get(market_type, {'base_wr': 50, 'volatility': 'medium'})
    odds_info = get_odds_analysis(odds)
    
    # ============================================================
    # SCORING SCIENTIFIQUE MULTI-FACTEURS
    # ============================================================
    
    # 1. Score de base selon probabilité (30 points max)
    prob_score = prob * 30
    
    # 2. Score de value/edge (25 points max)
    if edge >= 0.15:
        edge_score = 25
    elif edge >= 0.10:
        edge_score = 20
    elif edge >= 0.05:
        edge_score = 15
    elif edge >= 0.02:
        edge_score = 10
    elif edge > 0:
        edge_score = 5
    else:
        edge_score = max(-10, edge * 50)  # Pénalité si edge négatif
    
    # 3. Score de fiabilité cotes (20 points max)
    reliability_score = odds_info['reliability'] * 0.2
    
    # 4. Score historique marché (15 points max)
    backtest_wr = market_info.get('backtest_wr')
    if backtest_wr is not None:
        history_score = (backtest_wr / 100) * 15
    else:
        history_score = 7.5  # Neutre si pas de données
    
    # 5. Score facteurs équipes (10 points max)
    team_score = team_factor * 10
    
    # Score total
    raw_score = prob_score + edge_score + reliability_score + history_score + team_score
    final_score = max(0, min(100, int(raw_score)))
    
    # Calcul WR attendu (combinaison de plusieurs facteurs)
    base_wr = market_info['base_wr']
    odds_wr = odds_info['typical_wr']
    prob_wr = prob * 100
    
    # Moyenne pondérée
    expected_wr = (base_wr * 0.2 + odds_wr * 0.3 + prob_wr * 0.5)
    
    # Ajuster avec backtest si disponible
    if backtest_wr is not None:
        expected_wr = expected_wr * 0.7 + backtest_wr * 0.3
    
    # Niveau de confiance
    if final_score >= 75 and odds <= 2.0:
        confidence = 'very_high'
    elif final_score >= 65 and odds <= 3.0:
        confidence = 'high'
    elif final_score >= 55:
        confidence = 'medium'
    elif final_score >= 45:
        confidence = 'low'
    else:
        confidence = 'very_low'
    
    # Rating visuel
    if final_score >= 80:
        rating = '🔥 EXCELLENT'
    elif final_score >= 70:
        rating = '✅ TRÈS BON'
    elif final_score >= 60:
        rating = '📊 BON'
    elif final_score >= 50:
        rating = '📈 CORRECT'
    elif final_score >= 40:
        rating = '⚠️ MARGINAL'
    else:
        rating = '❌ FAIBLE'
    
    return {
        'score': final_score,
        'confidence': confidence,
        'risk_level': odds_info['risk'],
        'expected_wr': round(expected_wr, 1),
        'value_edge': round(edge_pct, 2),
        'kelly': round(kelly, 2),
        'rating': rating,
        'analysis': {
            'prob_score': round(prob_score, 1),
            'edge_score': round(edge_score, 1),
            'reliability_score': round(reliability_score, 1),
            'history_score': round(history_score, 1),
            'team_score': round(team_score, 1),
            'market_volatility': market_info['volatility'],
            'market_category': market_info['category'],
            'odds_reliability': odds_info['reliability'],
        }
    }


class OrchestratorV5Scientific:
    """Orchestrateur scientifique - analyse complète tous marchés"""
    
    def __init__(self):
        self.conn = None
        self.team_cache = {}
        self.adjustments = {}
        self.stats = {
            'created': 0, 'matches': 0, 'errors': 0,
            'by_market': {}, 'by_confidence': {}, 'by_risk': {}
        }
    
    def get_db(self):
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
        return self.conn
    
    def close(self):
        if self.conn and not self.conn.closed:
            self.conn.close()
    
    def _float(self, v, default=0.0):
        if v is None:
            return default
        if isinstance(v, Decimal):
            return float(v)
        try:
            return float(v)
        except:
            return default
    
    def load_adjustments(self):
        """Charge les ajustements auto-learning"""
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute("""
                SELECT adjustment_type, target, factor
                FROM fg_model_adjustments WHERE is_active = true
            """)
            for row in cur.fetchall():
                key = f"{row['adjustment_type']}_{row['target']}"
                self.adjustments[key] = self._float(row['factor'], 1.0)
            conn.commit()
            logger.info(f"📦 {len(self.adjustments)} ajustements chargés")
        except:
            conn.rollback()
        finally:
            cur.close()
    
    def get_team_stats(self, team_name: str) -> Dict:
        """Récupère stats équipe complètes"""
        if team_name in self.team_cache:
            return self.team_cache[team_name]
        
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            first_word = team_name.split()[0].lower() if team_name else ''
            cur.execute("""
                SELECT 
                    avg_goals_scored, avg_goals_conceded,
                    btts_pct, over_25_pct, over_15_pct, over_35_pct,
                    home_avg_scored, home_avg_conceded,
                    away_avg_scored, away_avg_conceded,
                    home_btts_pct, away_btts_pct,
                    home_over25_pct, away_over25_pct,
                    last5_form_points, form,
                    clean_sheet_pct, failed_to_score_pct,
                    data_quality_score
                FROM team_statistics_live
                WHERE LOWER(team_name) ILIKE %s
                LIMIT 1
            """, (f'%{first_word}%',))
            
            row = cur.fetchone()
            conn.commit()
            
            if row:
                # Calculer un facteur de qualité équipe (0.5 à 1.5)
                form = self._float(row.get('last5_form_points'), 7.5)
                quality = self._float(row.get('data_quality_score'), 50)
                team_factor = 0.7 + (form / 15) * 0.3 + (quality / 100) * 0.3
                team_factor = max(0.5, min(1.5, team_factor))
                
                stats = {
                    'avg_scored': self._float(row.get('avg_goals_scored'), 1.3),
                    'avg_conceded': self._float(row.get('avg_goals_conceded'), 1.2),
                    'btts_pct': self._float(row.get('btts_pct'), 50),
                    'over_25_pct': self._float(row.get('over_25_pct'), 50),
                    'over_15_pct': self._float(row.get('over_15_pct'), 70),
                    'over_35_pct': self._float(row.get('over_35_pct'), 30),
                    'home_scored': self._float(row.get('home_avg_scored'), 1.4),
                    'home_conceded': self._float(row.get('home_avg_conceded'), 1.1),
                    'away_scored': self._float(row.get('away_avg_scored'), 1.1),
                    'away_conceded': self._float(row.get('away_avg_conceded'), 1.4),
                    'home_btts': self._float(row.get('home_btts_pct'), 50),
                    'away_btts': self._float(row.get('away_btts_pct'), 50),
                    'form_points': form,
                    'clean_sheet_pct': self._float(row.get('clean_sheet_pct'), 30),
                    'failed_to_score_pct': self._float(row.get('failed_to_score_pct'), 25),
                    'quality': quality,
                    'team_factor': team_factor,
                }
            else:
                stats = self._default_stats()
            
            self.team_cache[team_name] = stats
            return stats
        except:
            conn.rollback()
            return self._default_stats()
        finally:
            cur.close()
    
    def _default_stats(self) -> Dict:
        return {
            'avg_scored': 1.3, 'avg_conceded': 1.2,
            'btts_pct': 50, 'over_25_pct': 50, 'over_15_pct': 70, 'over_35_pct': 30,
            'home_scored': 1.4, 'home_conceded': 1.1,
            'away_scored': 1.1, 'away_conceded': 1.4,
            'home_btts': 50, 'away_btts': 50,
            'form_points': 7.5, 'clean_sheet_pct': 30,
            'failed_to_score_pct': 25, 'quality': 50, 'team_factor': 1.0,
        }
    
    def get_h2h_stats(self, home_team: str, away_team: str) -> Dict:
        """Récupère H2H avec facteur"""
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            home_main = home_team.split()[0].lower() if home_team else ''
            away_main = away_team.split()[0].lower() if away_team else ''
            
            cur.execute("""
                SELECT total_matches, btts_pct, over_25_pct, over_15_pct,
                       avg_total_goals, team_a_wins, team_b_wins, draws
                FROM team_head_to_head
                WHERE (LOWER(team_a) ILIKE %s AND LOWER(team_b) ILIKE %s)
                   OR (LOWER(team_a) ILIKE %s AND LOWER(team_b) ILIKE %s)
                LIMIT 1
            """, (f'%{home_main}%', f'%{away_main}%', f'%{away_main}%', f'%{home_main}%'))
            
            row = cur.fetchone()
            conn.commit()
            
            if row and int(row.get('total_matches') or 0) >= 2:
                matches = int(row['total_matches'])
                # Facteur H2H (0.8 à 1.2 selon la fiabilité)
                h2h_factor = 0.9 + min(matches / 10, 0.3)
                
                return {
                    'matches': matches,
                    'btts_pct': self._float(row.get('btts_pct'), 50),
                    'over_25_pct': self._float(row.get('over_25_pct'), 50),
                    'over_15_pct': self._float(row.get('over_15_pct'), 70),
                    'avg_goals': self._float(row.get('avg_total_goals'), 2.5),
                    'h2h_factor': h2h_factor,
                    'confidence': 'high' if matches >= 5 else 'medium' if matches >= 3 else 'low'
                }
            return {'matches': 0, 'h2h_factor': 1.0, 'confidence': 'none'}
        except:
            conn.rollback()
            return {'matches': 0, 'h2h_factor': 1.0, 'confidence': 'none'}
        finally:
            cur.close()
    
    def collect(self, hours_ahead: int = 48) -> Dict:
        """Collecte TOUS les picks - analyse scientifique complète"""
        start = datetime.now()
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        self.load_adjustments()
        
        logger.info("🔬 COLLECT SCIENTIFIC - Analyse complète tous marchés")
        
        try:
            cur.execute("""
                SELECT DISTINCT ON (o.match_id)
                    o.match_id, o.home_team, o.away_team,
                    o.commence_time, o.home_odds, o.draw_odds, o.away_odds
                FROM odds_history o
                WHERE o.commence_time BETWEEN NOW() AND NOW() + INTERVAL '%s hours'
                AND o.home_odds IS NOT NULL
                ORDER BY o.match_id, o.collected_at DESC
            """ % hours_ahead)
            
            matches = cur.fetchall()
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Query error: {e}")
            cur.close()
            return self.stats
        
        logger.info(f"📋 {len(matches)} matchs à analyser")
        
        all_picks = []
        
        for match in matches:
            try:
                # Stats équipes
                home_stats = self.get_team_stats(match['home_team'])
                away_stats = self.get_team_stats(match['away_team'])
                h2h = self.get_h2h_stats(match['home_team'], match['away_team'])
                
                # Facteurs combinés
                team_factor = (home_stats['team_factor'] + away_stats['team_factor']) / 2
                h2h_factor = h2h.get('h2h_factor', 1.0)
                
                # xG
                home_xg = (home_stats['home_scored'] + away_stats['away_conceded']) / 2 * 1.08
                away_xg = (away_stats['away_scored'] + home_stats['home_conceded']) / 2 * 0.92
                home_xg = max(0.5, min(3.5, home_xg))
                away_xg = max(0.3, min(3.0, away_xg))
                
                # Probabilités Poisson
                probs = calculate_match_probabilities(home_xg, away_xg)
                
                # Ajuster avec stats équipes
                team_btts = (home_stats['btts_pct'] + away_stats['btts_pct']) / 2
                team_over25 = (home_stats['over_25_pct'] + away_stats['over_25_pct']) / 2
                team_over15 = (home_stats.get('over_15_pct', 70) + away_stats.get('over_15_pct', 70)) / 2
                
                probs['btts_yes'] = probs['btts_yes'] * 0.5 + (team_btts / 100) * 0.5
                probs['btts_no'] = 1 - probs['btts_yes']
                probs['over_25'] = probs['over_25'] * 0.5 + (team_over25 / 100) * 0.5
                probs['under_25'] = 1 - probs['over_25']
                probs['over_15'] = probs['over_15'] * 0.5 + (team_over15 / 100) * 0.5
                probs['under_15'] = 1 - probs['over_15']
                
                # H2H adjustment
                if h2h.get('matches', 0) >= 3:
                    w = 0.2
                    probs['btts_yes'] = probs['btts_yes'] * (1-w) + (h2h.get('btts_pct', 50) / 100) * w
                    probs['over_25'] = probs['over_25'] * (1-w) + (h2h.get('over_25_pct', 50) / 100) * w
                
                # Cotes 1X2
                odds_map = {
                    'home': self._float(match.get('home_odds')),
                    'draw': self._float(match.get('draw_odds')),
                    'away': self._float(match.get('away_odds')),
                }
                
                # Double chance
                if odds_map['home'] > 1 and odds_map['draw'] > 1:
                    odds_map['dc_1x'] = round(1 / (1/odds_map['home'] + 1/odds_map['draw']), 2)
                if odds_map['draw'] > 1 and odds_map['away'] > 1:
                    odds_map['dc_x2'] = round(1 / (1/odds_map['draw'] + 1/odds_map['away']), 2)
                if odds_map['home'] > 1 and odds_map['away'] > 1:
                    odds_map['dc_12'] = round(1 / (1/odds_map['home'] + 1/odds_map['away']), 2)
                
                # Over/Under
                cur2 = conn.cursor(cursor_factory=RealDictCursor)
                try:
                    cur2.execute("SELECT line, over_odds, under_odds FROM odds_totals WHERE match_id = %s", 
                                (match['match_id'],))
                    for tot in cur2.fetchall():
                        line = self._float(tot['line'])
                        if line == 1.5:
                            odds_map['over_15'] = self._float(tot.get('over_odds'))
                            odds_map['under_15'] = self._float(tot.get('under_odds'))
                        elif line == 2.5:
                            odds_map['over_25'] = self._float(tot.get('over_odds'))
                            odds_map['under_25'] = self._float(tot.get('under_odds'))
                        elif line == 3.5:
                            odds_map['over_35'] = self._float(tot.get('over_odds'))
                            odds_map['under_35'] = self._float(tot.get('under_odds'))
                    conn.commit()
                except:
                    conn.rollback()
                finally:
                    cur2.close()
                
                # BTTS estimé
                if odds_map.get('over_25', 0) > 1 and 'btts_yes' not in odds_map:
                    odds_map['btts_yes'] = round(odds_map['over_25'] * 0.92, 2)
                    odds_map['btts_no'] = round(1 / (1 - 1/odds_map['btts_yes']), 2) if odds_map['btts_yes'] > 1 else 3.0
                
                # Générer picks pour TOUS les marchés
                match_picks = []
                for market, prob in probs.items():
                    odds = odds_map.get(market, 0)
                    if not odds or odds <= 1:
                        continue
                    
                    # Scoring scientifique complet
                    scoring = calculate_score_scientific(prob, odds, market, team_factor, h2h_factor)
                    
                    # Tracking par marché
                    if market not in self.stats['by_market']:
                        self.stats['by_market'][market] = {'count': 0, 'avg_score': 0, 'total_score': 0}
                    self.stats['by_market'][market]['count'] += 1
                    self.stats['by_market'][market]['total_score'] += scoring['score']
                    
                    # Tracking par confiance
                    conf = scoring['confidence']
                    if conf not in self.stats['by_confidence']:
                        self.stats['by_confidence'][conf] = 0
                    self.stats['by_confidence'][conf] += 1
                    
                    # Tracking par risque
                    risk = scoring['risk_level']
                    if risk not in self.stats['by_risk']:
                        self.stats['by_risk'][risk] = 0
                    self.stats['by_risk'][risk] += 1
                    
                    pick = {
                        'match_id': match['match_id'],
                        'home_team': match['home_team'],
                        'away_team': match['away_team'],
                        'league': '',
                        'commence_time': match['commence_time'],
                        'market_type': market,
                        'odds': odds,
                        'probability': prob * 100,
                        'score': scoring['score'],
                        'kelly': scoring['kelly'],
                        'edge_pct': scoring['value_edge'],
                        'rating': scoring['rating'],
                        'confidence': scoring['confidence'],
                        'risk_level': scoring['risk_level'],
                        'expected_wr': scoring['expected_wr'],
                        'home_xg': home_xg,
                        'away_xg': away_xg,
                        'h2h_matches': h2h.get('matches', 0),
                        'factors': {
                            'home_xg': round(home_xg, 2),
                            'away_xg': round(away_xg, 2),
                            'team_factor': round(team_factor, 2),
                            'h2h_factor': round(h2h_factor, 2),
                            'team_btts': round(team_btts, 1),
                            'team_over25': round(team_over25, 1),
                            **scoring['analysis']
                        }
                    }
                    match_picks.append(pick)
                
                if match_picks:
                    # Trier par score et marquer TOP 3
                    match_picks.sort(key=lambda x: x['score'], reverse=True)
                    for i, p in enumerate(match_picks[:3]):
                        p['is_top3'] = True
                    for p in match_picks[3:]:
                        p['is_top3'] = False
                    
                    all_picks.extend(match_picks)
                    self.stats['matches'] += 1
                    
                    top_score = match_picks[0]['score']
                    logger.info(f"  ✅ {match['home_team']} vs {match['away_team']}: "
                               f"{len(match_picks)} picks (TOP: {top_score})")
                
            except Exception as e:
                self.stats['errors'] += 1
                logger.debug(f"Error: {e}")
        
        cur.close()
        
        # Sauvegarder
        if all_picks:
            self._save_picks(all_picks)
        
        # Calculer moyennes
        for market, data in self.stats['by_market'].items():
            if data['count'] > 0:
                data['avg_score'] = round(data['total_score'] / data['count'], 1)
        
        duration = (datetime.now() - start).total_seconds()
        self.stats['created'] = len(all_picks)
        
        logger.info(f"\n✅ COLLECT SCIENTIFIC: {len(all_picks)} picks | {self.stats['matches']} matchs | {duration:.1f}s")
        
        return self.stats
    
    def _save_picks(self, picks: List[Dict]):
        """Sauvegarde tous les picks"""
        conn = self.get_db()
        cur = conn.cursor()
        
        for pick in picks:
            try:
                cur.execute("""
                    INSERT INTO tracking_clv_picks (
                        match_id, home_team, away_team, league, match_name,
                        market_type, prediction, diamond_score, odds_taken,
                        probability, kelly_pct, edge_pct, value_rating,
                        home_xg, away_xg, total_xg, h2h_pct,
                        is_top3, factors, source, commence_time
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (match_id, market_type) 
                    DO UPDATE SET 
                        diamond_score = EXCLUDED.diamond_score,
                        odds_taken = EXCLUDED.odds_taken,
                        kelly_pct = EXCLUDED.kelly_pct,
                        edge_pct = EXCLUDED.edge_pct,
                        factors = EXCLUDED.factors,
                        updated_at = NOW()
                """, (
                    pick['match_id'], pick['home_team'], pick['away_team'],
                    pick['league'], f"{pick['home_team']} vs {pick['away_team']}",
                    pick['market_type'], pick['market_type'], pick['score'],
                    pick['odds'], pick['probability'], pick['kelly'],
                    pick['edge_pct'], pick['rating'], pick['home_xg'],
                    pick['away_xg'], pick['home_xg'] + pick['away_xg'],
                    pick['h2h_matches'], pick.get('is_top3', False),
                    Json(pick.get('factors', {})), 'orchestrator_v5_scientific',
                    pick['commence_time']
                ))
            except Exception as e:
                conn.rollback()
                logger.debug(f"Save error: {e}")
        
        conn.commit()
        cur.close()
    
    def analyze_markets(self) -> Dict:
        """Analyse complète de tous les marchés"""
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        logger.info("\n📊 ANALYSE SCIENTIFIQUE DES MARCHÉS")
        
        cur.execute("""
            SELECT 
                market_type,
                COUNT(*) as total_picks,
                COUNT(*) FILTER (WHERE is_resolved) as resolved,
                COUNT(*) FILTER (WHERE is_winner) as wins,
                ROUND(AVG(diamond_score)::numeric, 1) as avg_score,
                ROUND(AVG(odds_taken)::numeric, 2) as avg_odds,
                ROUND(AVG(kelly_pct)::numeric, 2) as avg_kelly,
                ROUND(AVG(edge_pct)::numeric, 2) as avg_edge,
                ROUND(SUM(profit_loss)::numeric, 2) as total_profit
            FROM tracking_clv_picks
            WHERE source = 'orchestrator_v5_scientific'
            GROUP BY market_type
            ORDER BY total_picks DESC
        """)
        
        results = cur.fetchall()
        conn.commit()
        cur.close()
        
        analysis = {}
        for row in results:
            market = row['market_type']
            resolved = row['resolved'] or 0
            wins = row['wins'] or 0
            wr = round(wins / resolved * 100, 1) if resolved > 0 else None
            roi = round((row['total_profit'] or 0) / resolved * 100, 1) if resolved > 0 else None
            
            analysis[market] = {
                'total_picks': row['total_picks'],
                'resolved': resolved,
                'wins': wins,
                'win_rate': wr,
                'avg_score': float(row['avg_score'] or 0),
                'avg_odds': float(row['avg_odds'] or 0),
                'avg_kelly': float(row['avg_kelly'] or 0),
                'avg_edge': float(row['avg_edge'] or 0),
                'total_profit': float(row['total_profit'] or 0),
                'roi': roi,
                'status': self._get_market_status(wr, roi)
            }
        
        return analysis
    
    def _get_market_status(self, wr, roi):
        if wr is None:
            return '⏳ EN ATTENTE'
        if wr >= 60 and roi and roi > 5:
            return '🔥 EXCELLENT'
        if wr >= 50 and roi and roi > 0:
            return '✅ BON'
        if wr >= 45:
            return '📊 NEUTRE'
        return '⚠️ À AMÉLIORER'


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('action', nargs='?', default='collect', choices=['collect', 'analyze', 'smart'])
    parser.add_argument('--hours', type=int, default=48)
    args = parser.parse_args()
    
    logger.info("=" * 70)
    logger.info("🔬 CLV ORCHESTRATOR V5 SCIENTIFIC")
    logger.info("   �� Analyse complète - TOUS les marchés")
    logger.info("   📊 Aucun filtrage - Apprentissage scientifique")
    logger.info("=" * 70)
    
    orch = OrchestratorV5Scientific()
    
    if args.action in ['collect', 'smart']:
        stats = orch.collect(hours_ahead=args.hours)
        
        # Afficher stats par marché
        print("\n📊 PICKS PAR MARCHÉ:")
        for market, data in sorted(stats['by_market'].items(), key=lambda x: x[1]['count'], reverse=True):
            print(f"   {market:12} | {data['count']:3} picks | Score moy: {data['avg_score']}")
        
        print(f"\n📊 PAR CONFIANCE:")
        for conf, count in stats['by_confidence'].items():
            print(f"   {conf:12} | {count:3} picks")
        
        print(f"\n📊 PAR RISQUE:")
        for risk, count in stats['by_risk'].items():
            print(f"   {risk:12} | {count:3} picks")
    
    if args.action in ['analyze', 'smart']:
        analysis = orch.analyze_markets()
        
        print("\n" + "=" * 70)
        print("📊 ANALYSE DÉTAILLÉE DES MARCHÉS")
        print("=" * 70)
        
        for market, data in sorted(analysis.items(), key=lambda x: x[1]['total_picks'], reverse=True):
            print(f"\n{market.upper()}:")
            print(f"   Picks: {data['total_picks']} | Résolus: {data['resolved']}")
            print(f"   WR: {data['win_rate']}% | ROI: {data['roi']}%")
            print(f"   Score moy: {data['avg_score']} | Cotes moy: {data['avg_odds']}")
            print(f"   Status: {data['status']}")
    
    orch.close()
    
    print(json.dumps({'created': stats['created'], 'matches': stats['matches']}, indent=2))


if __name__ == "__main__":
    main()
