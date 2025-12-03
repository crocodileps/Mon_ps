#!/usr/bin/env python3
"""
🤖 CLV ORCHESTRATOR V6.0 - CORRECTIONS SCIENTIFIQUES

Basé sur l'analyse des données réelles:
- Backtest: 27 matchs, 70 picks
- Analyse: 352 picks générés
- Incohérences identifiées et corrigées

CORRECTIONS APPLIQUÉES:
┌─────────────┬──────────────┬─────────────────────────────────┐
│   Marché    │   Facteur    │   Raison                        │
├─────────────┼──────────────┼─────────────────────────────────┤
│ BTTS_YES    │ × 1.25 (+25%)│ Backtest 100% WR, edge -11%     │
│ OVER_25     │ × 1.20 (+20%)│ Backtest 75% WR, edge -9%       │
│ DC_12       │ × 1.12 (+12%)│ Backtest 100% WR, edge -5%      │
│ DC_1X       │ × 1.10 (+10%)│ Backtest 50% WR, stable         │
│ AWAY        │ × 1.15 (+15%)│ Backtest 43% WR, edge -24%      │
│ DC_X2       │ × 1.20 (+20%)│ Backtest 37.5% WR, edge -30%    │
│ OVER_15     │ × 1.10 (+10%)│ Sous-estimé                     │
│ OVER_35     │ × 1.10 (+10%)│ Sous-estimé                     │
│ BTTS_NO     │ × 1.00 (0%)  │ Seul edge positif, conserver    │
│ HOME        │ × 0.90 (-10%)│ Backtest 12.5% WR, surestimé    │
│ DRAW        │ × 1.05 (+5%) │ Légèrement sous-estimé          │
│ UNDER_25    │ × 1.05 (+5%) │ Légèrement sous-estimé          │
└─────────────┴──────────────┴─────────────────────────────────┘
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
logger = logging.getLogger('OrchestratorV6')

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
}

# ============================================================
# FACTEURS DE CORRECTION SCIENTIFIQUES (basés sur backtest)
# ============================================================

PROBABILITY_CORRECTIONS = {
    # TOP PERFORMERS - augmenter la confiance
    'btts_yes': 1.25,    # +25% - Backtest 100% WR mais edge -11%
    'over_25': 1.20,     # +20% - Backtest 75% WR mais edge -9%
    'dc_12': 1.12,       # +12% - Backtest 100% WR mais edge -5%
    'over_15': 1.10,     # +10% - Sous-estimé
    'over_35': 1.10,     # +10% - Sous-estimé
    
    # CORRECTIONS MOYENNES
    'dc_1x': 1.10,       # +10% - Stable mais sous-estimé
    'away': 1.15,        # +15% - Backtest 43% WR, edge -24%
    'dc_x2': 1.20,       # +20% - Edge très négatif -30%
    'draw': 1.05,        # +5% - Légèrement sous-estimé
    'under_25': 1.05,    # +5% - Légèrement sous-estimé
    'under_35': 1.00,    # Inchangé
    'under_15': 0.95,    # -5% - Rare
    
    # SEUL MARCHÉ OK - ne pas toucher
    'btts_no': 1.00,     # Edge +5.72% - Conserver
    
    # RÉDUIRE - surestimé dans le modèle
    'home': 0.90,        # -10% - Backtest 12.5% WR catastrophique
}

# Bonus/Malus par marché (performance historique)
MARKET_PERFORMANCE = {
    'btts_yes': {'bonus': 15, 'backtest_wr': 100.0, 'confidence': 'very_high'},
    'over_25': {'bonus': 12, 'backtest_wr': 75.0, 'confidence': 'high'},
    'dc_12': {'bonus': 10, 'backtest_wr': 100.0, 'confidence': 'very_high'},
    'dc_1x': {'bonus': 5, 'backtest_wr': 50.0, 'confidence': 'medium'},
    'btts_no': {'bonus': 8, 'backtest_wr': 50.0, 'confidence': 'medium'},
    'away': {'bonus': 3, 'backtest_wr': 42.9, 'confidence': 'medium'},
    'over_15': {'bonus': 5, 'backtest_wr': None, 'confidence': 'medium'},
    'over_35': {'bonus': 0, 'backtest_wr': None, 'confidence': 'low'},
    'draw': {'bonus': -5, 'backtest_wr': 25.0, 'confidence': 'low'},
    'dc_x2': {'bonus': -8, 'backtest_wr': 37.5, 'confidence': 'low'},
    'under_25': {'bonus': -10, 'backtest_wr': 28.6, 'confidence': 'low'},
    'under_35': {'bonus': 0, 'backtest_wr': None, 'confidence': 'medium'},
    'under_15': {'bonus': -5, 'backtest_wr': None, 'confidence': 'low'},
    'home': {'bonus': -15, 'backtest_wr': 12.5, 'confidence': 'very_low'},
}

# Analyse des cotes
ODDS_ANALYSIS = {
    (1.0, 1.5): {'reliability': 90, 'risk': 'very_low'},
    (1.5, 2.0): {'reliability': 80, 'risk': 'low'},
    (2.0, 2.5): {'reliability': 70, 'risk': 'medium'},
    (2.5, 3.0): {'reliability': 55, 'risk': 'medium_high'},
    (3.0, 4.0): {'reliability': 40, 'risk': 'high'},
    (4.0, 6.0): {'reliability': 25, 'risk': 'very_high'},
    (6.0, 99): {'reliability': 15, 'risk': 'extreme'},
}


def get_odds_info(odds: float) -> Dict:
    for (low, high), info in ODDS_ANALYSIS.items():
        if low <= odds < high:
            return info
    return {'reliability': 10, 'risk': 'extreme'}


def poisson_prob(lam: float, k: int) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    try:
        return (math.exp(-lam) * (lam ** k)) / math.factorial(k)
    except:
        return 0.0


def calculate_match_probabilities(home_xg: float, away_xg: float) -> Dict[str, float]:
    """Calcule probabilités via Poisson"""
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


def apply_correction(prob: float, market_type: str) -> float:
    """Applique le facteur de correction scientifique"""
    factor = PROBABILITY_CORRECTIONS.get(market_type, 1.0)
    corrected = prob * factor
    # Plafonner entre 0.05 et 0.95
    return max(0.05, min(0.95, corrected))


def calculate_score_v6(prob_raw: float, prob_corrected: float, odds: float, market_type: str) -> Dict:
    """
    SCORING V6 - Basé sur probabilité corrigée
    
    Retourne score, kelly, edge, rating, et analyse détaillée
    """
    result = {
        'score': 0, 'kelly': 0, 'edge_pct': 0, 'rating': '❌ INVALIDE',
        'confidence': 'none', 'risk': 'unknown', 'expected_wr': 0,
        'analysis': {}
    }
    
    if not odds or odds <= 1 or prob_corrected <= 0:
        return result
    
    implied = 1 / odds
    
    # Edge basé sur prob CORRIGÉE
    edge = prob_corrected - implied
    edge_pct = edge * 100
    
    # Kelly
    if edge > 0:
        kelly = min((edge / (odds - 1)) * 100, 10)
    else:
        kelly = 0
    
    # Info marché
    market_info = MARKET_PERFORMANCE.get(market_type, {'bonus': 0, 'backtest_wr': None})
    odds_info = get_odds_info(odds)
    
    # ============================================================
    # SCORING V6 MULTI-FACTEURS
    # ============================================================
    
    # 1. Score probabilité corrigée (35 points max)
    prob_score = prob_corrected * 35
    
    # 2. Score edge (25 points max)
    if edge >= 0.15:
        edge_score = 25
    elif edge >= 0.10:
        edge_score = 20
    elif edge >= 0.05:
        edge_score = 15
    elif edge >= 0.02:
        edge_score = 8
    elif edge > 0:
        edge_score = 3
    else:
        edge_score = max(-10, edge * 30)
    
    # 3. Score fiabilité cotes (20 points max)
    reliability_score = odds_info['reliability'] * 0.2
    
    # 4. Bonus marché historique (15 points max)
    market_bonus = market_info['bonus']
    
    # 5. Correction pour backtest connu
    backtest_wr = market_info.get('backtest_wr')
    if backtest_wr is not None:
        if backtest_wr >= 70:
            backtest_bonus = 10
        elif backtest_wr >= 50:
            backtest_bonus = 5
        elif backtest_wr >= 35:
            backtest_bonus = 0
        else:
            backtest_bonus = -5
    else:
        backtest_bonus = 0
    
    # Score total
    raw_score = prob_score + edge_score + reliability_score + market_bonus + backtest_bonus
    final_score = max(0, min(100, int(raw_score)))
    
    # WR attendu (combinaison)
    base_wr = backtest_wr if backtest_wr else 50
    implied_wr = implied * 100
    corrected_wr = prob_corrected * 100
    expected_wr = (base_wr * 0.3 + corrected_wr * 0.5 + implied_wr * 0.2)
    
    # Confiance
    if final_score >= 75 and edge >= 0.05:
        confidence = 'very_high'
    elif final_score >= 65 and edge >= 0:
        confidence = 'high'
    elif final_score >= 55:
        confidence = 'medium'
    elif final_score >= 45:
        confidence = 'low'
    else:
        confidence = 'very_low'
    
    # Rating
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
        'kelly': round(kelly, 2),
        'edge_pct': round(edge_pct, 2),
        'rating': rating,
        'confidence': confidence,
        'risk': odds_info['risk'],
        'expected_wr': round(expected_wr, 1),
        'analysis': {
            'prob_raw': round(prob_raw * 100, 1),
            'prob_corrected': round(prob_corrected * 100, 1),
            'correction_factor': PROBABILITY_CORRECTIONS.get(market_type, 1.0),
            'prob_score': round(prob_score, 1),
            'edge_score': round(edge_score, 1),
            'reliability_score': round(reliability_score, 1),
            'market_bonus': market_bonus,
            'backtest_bonus': backtest_bonus,
            'backtest_wr': backtest_wr,
        }
    }


class OrchestratorV6:
    """Orchestrateur V6 avec corrections scientifiques"""
    
    def __init__(self):
        self.conn = None
        self.team_cache = {}
        self.stats = {
            'created': 0, 'matches': 0, 'errors': 0,
            'by_market': {}, 'by_confidence': {}
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
    
    def get_team_stats(self, team_name: str) -> Dict:
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
                    last5_form_points, data_quality_score
                FROM team_statistics_live
                WHERE LOWER(team_name) ILIKE %s
                LIMIT 1
            """, (f'%{first_word}%',))
            
            row = cur.fetchone()
            conn.commit()
            
            if row:
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
                    'form_points': self._float(row.get('last5_form_points'), 7.5),
                    'quality': self._float(row.get('data_quality_score'), 50),
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
            'form_points': 7.5, 'quality': 50,
        }
    
    def get_h2h_stats(self, home_team: str, away_team: str) -> Dict:
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            home_main = home_team.split()[0].lower() if home_team else ''
            away_main = away_team.split()[0].lower() if away_team else ''
            
            cur.execute("""
                SELECT total_matches, btts_pct, over_25_pct, over_15_pct, avg_total_goals
                FROM team_head_to_head
                WHERE (LOWER(team_a) ILIKE %s AND LOWER(team_b) ILIKE %s)
                   OR (LOWER(team_a) ILIKE %s AND LOWER(team_b) ILIKE %s)
                LIMIT 1
            """, (f'%{home_main}%', f'%{away_main}%', f'%{away_main}%', f'%{home_main}%'))
            
            row = cur.fetchone()
            conn.commit()
            
            if row and int(row.get('total_matches') or 0) >= 2:
                return {
                    'matches': int(row['total_matches']),
                    'btts_pct': self._float(row.get('btts_pct'), 50),
                    'over_25_pct': self._float(row.get('over_25_pct'), 50),
                    'avg_goals': self._float(row.get('avg_total_goals'), 2.5),
                }
            return {'matches': 0}
        except:
            conn.rollback()
            return {'matches': 0}
        finally:
            cur.close()
    
    def collect(self, hours_ahead: int = 48) -> Dict:
        """Collecte avec corrections scientifiques"""
        start = datetime.now()
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        logger.info("🔬 COLLECT V6 - Corrections scientifiques appliquées")
        logger.info("   �� BTTS_YES ×1.25 | OVER_25 ×1.20 | DC_12 ×1.12 | HOME ×0.90")
        
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
                home_stats = self.get_team_stats(match['home_team'])
                away_stats = self.get_team_stats(match['away_team'])
                h2h = self.get_h2h_stats(match['home_team'], match['away_team'])
                
                # xG
                home_xg = (home_stats['home_scored'] + away_stats['away_conceded']) / 2 * 1.08
                away_xg = (away_stats['away_scored'] + home_stats['home_conceded']) / 2 * 0.92
                home_xg = max(0.5, min(3.5, home_xg))
                away_xg = max(0.3, min(3.0, away_xg))
                
                # Probabilités brutes (Poisson)
                probs_raw = calculate_match_probabilities(home_xg, away_xg)
                
                # Ajuster avec stats équipes (avant correction)
                team_btts = (home_stats['btts_pct'] + away_stats['btts_pct']) / 2
                team_over25 = (home_stats['over_25_pct'] + away_stats['over_25_pct']) / 2
                
                probs_raw['btts_yes'] = probs_raw['btts_yes'] * 0.5 + (team_btts / 100) * 0.5
                probs_raw['btts_no'] = 1 - probs_raw['btts_yes']
                probs_raw['over_25'] = probs_raw['over_25'] * 0.5 + (team_over25 / 100) * 0.5
                probs_raw['under_25'] = 1 - probs_raw['over_25']
                
                # H2H
                if h2h.get('matches', 0) >= 3:
                    w = 0.15
                    probs_raw['btts_yes'] = probs_raw['btts_yes'] * (1-w) + (h2h.get('btts_pct', 50) / 100) * w
                    probs_raw['over_25'] = probs_raw['over_25'] * (1-w) + (h2h.get('over_25_pct', 50) / 100) * w
                
                # Cotes
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
                    odds_map['btts_no'] = round(1 / max(0.1, 1 - 1/odds_map['btts_yes']), 2)
                
                # Générer picks pour TOUS les marchés
                match_picks = []
                for market, prob_raw in probs_raw.items():
                    odds = odds_map.get(market, 0)
                    if not odds or odds <= 1:
                        continue
                    
                    # APPLIQUER CORRECTION SCIENTIFIQUE
                    prob_corrected = apply_correction(prob_raw, market)
                    
                    # Scoring V6
                    scoring = calculate_score_v6(prob_raw, prob_corrected, odds, market)
                    
                    # Stats
                    if market not in self.stats['by_market']:
                        self.stats['by_market'][market] = {'count': 0, 'total_score': 0, 'total_edge': 0}
                    self.stats['by_market'][market]['count'] += 1
                    self.stats['by_market'][market]['total_score'] += scoring['score']
                    self.stats['by_market'][market]['total_edge'] += scoring['edge_pct']
                    
                    conf = scoring['confidence']
                    if conf not in self.stats['by_confidence']:
                        self.stats['by_confidence'][conf] = 0
                    self.stats['by_confidence'][conf] += 1
                    
                    pick = {
                        'match_id': match['match_id'],
                        'home_team': match['home_team'],
                        'away_team': match['away_team'],
                        'league': '',
                        'commence_time': match['commence_time'],
                        'market_type': market,
                        'odds': odds,
                        'probability': prob_corrected * 100,
                        'probability_raw': prob_raw * 100,
                        'score': scoring['score'],
                        'kelly': scoring['kelly'],
                        'edge_pct': scoring['edge_pct'],
                        'rating': scoring['rating'],
                        'confidence': scoring['confidence'],
                        'risk': scoring['risk'],
                        'expected_wr': scoring['expected_wr'],
                        'home_xg': home_xg,
                        'away_xg': away_xg,
                        'h2h_matches': h2h.get('matches', 0),
                        'factors': {
                            'correction_factor': PROBABILITY_CORRECTIONS.get(market, 1.0),
                            **scoring['analysis']
                        }
                    }
                    match_picks.append(pick)
                
                if match_picks:
                    match_picks.sort(key=lambda x: x['score'], reverse=True)
                    for i, p in enumerate(match_picks[:3]):
                        p['is_top3'] = True
                    for p in match_picks[3:]:
                        p['is_top3'] = False
                    
                    all_picks.extend(match_picks)
                    self.stats['matches'] += 1
                    
                    top = match_picks[0]
                    logger.info(f"  ✅ {match['home_team']} vs {match['away_team']}: "
                               f"{len(match_picks)} picks | TOP: {top['market_type']} ({top['score']})")
                
            except Exception as e:
                self.stats['errors'] += 1
                logger.debug(f"Error: {e}")
        
        cur.close()
        
        if all_picks:
            self._save_picks(all_picks)
        
        # Stats finales
        for market, data in self.stats['by_market'].items():
            if data['count'] > 0:
                data['avg_score'] = round(data['total_score'] / data['count'], 1)
                data['avg_edge'] = round(data['total_edge'] / data['count'], 2)
        
        duration = (datetime.now() - start).total_seconds()
        self.stats['created'] = len(all_picks)
        
        logger.info(f"\n✅ COLLECT V6: {len(all_picks)} picks | {self.stats['matches']} matchs | {duration:.1f}s")
        
        return self.stats
    
    def _save_picks(self, picks: List[Dict]):
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
                    ON CONFLICT (match_id, market_type, source) 
                    DO UPDATE SET 
                        diamond_score = EXCLUDED.diamond_score,
                        odds_taken = EXCLUDED.odds_taken,
                        probability = EXCLUDED.probability,
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
                    Json(pick.get('factors', {})), 'orchestrator_v6_corrected',
                    pick['commence_time']
                ))
            except Exception as e:
                conn.rollback()
                logger.debug(f"Save error: {e}")
        
        conn.commit()
        cur.close()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('action', nargs='?', default='collect')
    parser.add_argument('--hours', type=int, default=48)
    args = parser.parse_args()
    
    logger.info("=" * 70)
    logger.info("🤖 CLV ORCHESTRATOR V6.0 - CORRECTIONS SCIENTIFIQUES")
    logger.info("=" * 70)
    logger.info("📊 Facteurs de correction appliqués:")
    logger.info("   BTTS_YES: ×1.25 (+25%) | OVER_25: ×1.20 (+20%)")
    logger.info("   DC_12: ×1.12 (+12%)    | HOME: ×0.90 (-10%)")
    logger.info("=" * 70)
    
    orch = OrchestratorV6()
    stats = orch.collect(hours_ahead=args.hours)
    
    # Afficher stats
    print("\n📊 PICKS PAR MARCHÉ (après correction):")
    for market, data in sorted(stats['by_market'].items(), key=lambda x: x[1]['count'], reverse=True):
        print(f"   {market:12} | {data['count']:3} picks | Score: {data['avg_score']:5.1f} | Edge: {data['avg_edge']:+6.2f}%")
    
    print(f"\n📊 PAR CONFIANCE:")
    for conf, count in sorted(stats['by_confidence'].items(), key=lambda x: x[1], reverse=True):
        print(f"   {conf:12} | {count:3} picks")
    
    orch.close()
    
    print(json.dumps({'created': stats['created'], 'matches': stats['matches']}, indent=2))


if __name__ == "__main__":
    main()
