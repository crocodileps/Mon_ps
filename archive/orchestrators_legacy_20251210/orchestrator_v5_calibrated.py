#!/usr/bin/env python3
"""
🤖 CLV ORCHESTRATOR V5.0 - CALIBRÉ SUR DONNÉES RÉELLES
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
logger = logging.getLogger('OrchestratorV5')

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
}

# Calibration basée sur backtest réel
MARKET_CALIBRATION = {
    'btts_yes': {'bonus': 20, 'confidence': 'high'},
    'over_25': {'bonus': 15, 'confidence': 'high'},
    'over_15': {'bonus': 12, 'confidence': 'medium'},
    'dc_12': {'bonus': 10, 'confidence': 'medium'},
    'dc_1x': {'bonus': 5, 'confidence': 'medium'},
    'btts_no': {'bonus': 3, 'confidence': 'medium'},
    'away': {'bonus': 0, 'confidence': 'low'},
    'over_35': {'bonus': 0, 'confidence': 'low'},
    'draw': {'bonus': -8, 'confidence': 'low'},
    'dc_x2': {'bonus': -10, 'confidence': 'low'},
    'under_25': {'bonus': -12, 'confidence': 'low'},
    'under_35': {'bonus': -5, 'confidence': 'low'},
    'under_15': {'bonus': -15, 'confidence': 'low'},
    'home': {'bonus': -20, 'confidence': 'very_low'},
}

ODDS_PENALTY = {
    (1.0, 1.5): 1.0,
    (1.5, 2.0): 0.95,
    (2.0, 2.5): 0.90,
    (2.5, 3.0): 0.80,
    (3.0, 4.0): 0.65,
    (4.0, 5.0): 0.50,
    (5.0, 7.0): 0.35,
    (7.0, 99): 0.20,
}


def get_odds_penalty(odds: float) -> float:
    for (low, high), factor in ODDS_PENALTY.items():
        if low <= odds < high:
            return factor
    return 0.20


def poisson_prob(lam: float, k: int) -> float:
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    try:
        return (math.exp(-lam) * (lam ** k)) / math.factorial(k)
    except:
        return 0.0


def calculate_match_probabilities(home_xg: float, away_xg: float) -> Dict[str, float]:
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


def calculate_score_v5(prob: float, odds: float, market_type: str) -> Tuple[int, float, float, str]:
    """SCORING V5 - Calibré sur backtest réel"""
    if not odds or odds <= 1 or prob <= 0:
        return (0, 0, 0, '❌ INVALIDE')
    
    implied = 1 / odds
    edge = prob - implied
    edge_pct = edge * 100
    
    if edge > 0:
        kelly = min((edge / (odds - 1)) * 100, 8)
    else:
        kelly = 0
    
    # Score basé sur PROBABILITÉ (pas edge!)
    if prob >= 0.70:
        base_score = 75
    elif prob >= 0.55:
        base_score = 70
    elif prob >= 0.45:
        base_score = 65
    elif prob >= 0.35:
        base_score = 60
    elif prob >= 0.25:
        base_score = 55
    else:
        base_score = 45
    
    # Bonus edge modéré
    if edge >= 0.10:
        edge_bonus = 10
    elif edge >= 0.05:
        edge_bonus = 5
    elif edge >= 0.02:
        edge_bonus = 2
    elif edge > 0:
        edge_bonus = 0
    else:
        edge_bonus = -15
    
    # Pénalité cotes (underdogs perdent!)
    odds_factor = get_odds_penalty(odds)
    
    # Bonus marché
    market_info = MARKET_CALIBRATION.get(market_type, {'bonus': 0})
    market_bonus = market_info['bonus']
    
    # Calcul final
    raw_score = base_score + edge_bonus + market_bonus
    
    if odds >= 4.0:
        final_score = min(65, raw_score * odds_factor)
    elif odds >= 3.0:
        final_score = min(75, raw_score * odds_factor)
    else:
        final_score = raw_score * odds_factor
    
    final_score = max(20, min(85, int(final_score)))
    
    if final_score >= 75:
        rating = '🔥 EXCELLENT'
    elif final_score >= 68:
        rating = '✅ TRÈS BON'
    elif final_score >= 60:
        rating = '📊 BON'
    elif final_score >= 50:
        rating = '📈 CORRECT'
    else:
        rating = '⚠️ MARGINAL'
    
    return (final_score, round(kelly, 2), round(edge_pct, 2), rating)


class OrchestratorV5:
    def __init__(self):
        self.conn = None
        self.team_cache = {}
        self.adjustments = {}
        self.stats = {'created': 0, 'matches': 0, 'combos': 0, 'errors': 0}
    
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
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute("""
                SELECT adjustment_type, target, factor
                FROM fg_model_adjustments
                WHERE is_active = true
            """)
            for row in cur.fetchall():
                key = f"{row['adjustment_type']}_{row['target']}"
                self.adjustments[key] = self._float(row['factor'], 1.0)
            conn.commit()
            logger.info(f"📦 {len(self.adjustments)} ajustements chargés")
        except Exception as e:
            conn.rollback()
            logger.debug(f"Adjustments: {e}")
        finally:
            cur.close()
    
    def get_team_stats(self, team_name: str) -> Dict:
        if team_name in self.team_cache:
            return self.team_cache[team_name]
        
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            first_word = team_name.split()[0].lower() if team_name else ''
            cur.execute("""
                SELECT avg_goals_scored, avg_goals_conceded,
                       btts_pct, over_25_pct, over_15_pct,
                       home_avg_scored, home_avg_conceded,
                       away_avg_scored, away_avg_conceded,
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
                    'home_scored': self._float(row.get('home_avg_scored'), 1.4),
                    'home_conceded': self._float(row.get('home_avg_conceded'), 1.1),
                    'away_scored': self._float(row.get('away_avg_scored'), 1.1),
                    'away_conceded': self._float(row.get('away_avg_conceded'), 1.4),
                    'form_points': self._float(row.get('last5_form_points'), 7.5),
                    'quality': self._float(row.get('data_quality_score'), 50),
                }
            else:
                stats = self._default_stats()
            
            self.team_cache[team_name] = stats
            return stats
        except Exception as e:
            conn.rollback()
            return self._default_stats()
        finally:
            cur.close()
    
    def _default_stats(self) -> Dict:
        return {
            'avg_scored': 1.3, 'avg_conceded': 1.2,
            'btts_pct': 50, 'over_25_pct': 50,
            'home_scored': 1.4, 'home_conceded': 1.1,
            'away_scored': 1.1, 'away_conceded': 1.4,
            'form_points': 7.5, 'quality': 50,
        }
    
    def get_h2h_stats(self, home_team: str, away_team: str) -> Dict:
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            home_main = home_team.split()[0].lower() if home_team else ''
            away_main = away_team.split()[0].lower() if away_team else ''
            
            cur.execute("""
                SELECT total_matches, btts_pct, over_25_pct, avg_total_goals
                FROM team_head_to_head
                WHERE (LOWER(team_a) ILIKE %s AND LOWER(team_b) ILIKE %s)
                   OR (LOWER(team_a) ILIKE %s AND LOWER(team_b) ILIKE %s)
                LIMIT 1
            """, (f'%{home_main}%', f'%{away_main}%', f'%{away_main}%', f'%{home_main}%'))
            
            row = cur.fetchone()
            conn.commit()
            
            if row and int(row.get('total_matches') or 0) >= 3:
                return {
                    'matches': int(row['total_matches']),
                    'btts_pct': self._float(row.get('btts_pct'), 50),
                    'over_25_pct': self._float(row.get('over_25_pct'), 50),
                    'confidence': 'high' if int(row['total_matches']) >= 5 else 'medium'
                }
            return {'matches': 0, 'confidence': 'none'}
        except Exception as e:
            conn.rollback()
            return {'matches': 0, 'confidence': 'none'}
        finally:
            cur.close()
    
    def collect(self, hours_ahead: int = 48) -> Dict:
        start = datetime.now()
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        self.load_adjustments()
        
        logger.info("🚀 COLLECT V5 CALIBRÉ")
        
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
        
        logger.info(f"📋 {len(matches)} matchs trouvés")
        
        new_picks = []
        
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
                
                probs = calculate_match_probabilities(home_xg, away_xg)
                
                # Ajuster avec stats équipes
                team_btts = (home_stats['btts_pct'] + away_stats['btts_pct']) / 2
                team_over25 = (home_stats['over_25_pct'] + away_stats['over_25_pct']) / 2
                
                probs['btts_yes'] = probs['btts_yes'] * 0.5 + (team_btts / 100) * 0.5
                probs['btts_no'] = 1 - probs['btts_yes']
                probs['over_25'] = probs['over_25'] * 0.5 + (team_over25 / 100) * 0.5
                probs['under_25'] = 1 - probs['over_25']
                
                # H2H
                if h2h.get('matches', 0) >= 3:
                    h2h_w = 0.2
                    probs['btts_yes'] = probs['btts_yes'] * (1 - h2h_w) + (h2h['btts_pct'] / 100) * h2h_w
                    probs['over_25'] = probs['over_25'] * (1 - h2h_w) + (h2h['over_25_pct'] / 100) * h2h_w
                
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
                    cur2.execute("""
                        SELECT line, over_odds, under_odds
                        FROM odds_totals
                        WHERE match_id = %s
                    """, (match['match_id'],))
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
                
                # Générer picks
                match_picks = []
                for market, prob in probs.items():
                    odds = odds_map.get(market, 0)
                    if not odds or odds <= 1:
                        continue
                    
                    score, kelly, edge_pct, rating = calculate_score_v5(prob, odds, market)
                    
                    if score < 55 or edge_pct < 0:
                        continue
                    
                    market_info = MARKET_CALIBRATION.get(market, {})
                    
                    pick = {
                        'match_id': match['match_id'],
                        'home_team': match['home_team'],
                        'away_team': match['away_team'],
                        'league': '',
                        'commence_time': match['commence_time'],
                        'market_type': market,
                        'odds': odds,
                        'probability': prob * 100,
                        'score': score,
                        'kelly': kelly,
                        'edge_pct': edge_pct,
                        'rating': rating,
                        'home_xg': home_xg,
                        'away_xg': away_xg,
                        'h2h_matches': h2h.get('matches', 0),
                        'factors': {
                            'home_xg': round(home_xg, 2),
                            'away_xg': round(away_xg, 2),
                            'team_btts': round(team_btts, 1),
                            'odds_penalty': round(get_odds_penalty(odds), 2),
                            'market_bonus': market_info.get('bonus', 0),
                        }
                    }
                    match_picks.append(pick)
                
                if match_picks:
                    match_picks.sort(key=lambda x: x['score'], reverse=True)
                    for i, p in enumerate(match_picks[:3]):
                        p['is_top3'] = True
                    
                    new_picks.extend(match_picks)
                    self.stats['matches'] += 1
                    
                    top3 = [p for p in match_picks if p.get('is_top3')]
                    logger.info(f"  ✅ {match['home_team']} vs {match['away_team']}: {len(match_picks)} picks ({len(top3)} TOP)")
                
            except Exception as e:
                self.stats['errors'] += 1
                logger.debug(f"Error: {e}")
        
        cur.close()
        
        # Sauvegarder
        if new_picks:
            self._save_picks(new_picks)
        
        duration = (datetime.now() - start).total_seconds()
        logger.info(f"✅ COLLECT V5: {len(new_picks)} picks | {self.stats['matches']} matchs | {duration:.1f}s")
        
        self.stats['created'] = len(new_picks)
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
                    ON CONFLICT (match_id, market_type) 
                    DO UPDATE SET diamond_score = EXCLUDED.diamond_score,
                                  odds_taken = EXCLUDED.odds_taken,
                                  kelly_pct = EXCLUDED.kelly_pct,
                                  updated_at = NOW()
                """, (
                    pick['match_id'], pick['home_team'], pick['away_team'],
                    pick['league'], f"{pick['home_team']} vs {pick['away_team']}",
                    pick['market_type'], pick['market_type'], pick['score'],
                    pick['odds'], pick['probability'], pick['kelly'],
                    pick['edge_pct'], pick['rating'], pick['home_xg'],
                    pick['away_xg'], pick['home_xg'] + pick['away_xg'],
                    pick['h2h_matches'], pick.get('is_top3', False),
                    Json(pick.get('factors', {})), 'orchestrator_v5_calibrated',
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
    logger.info("🤖 CLV ORCHESTRATOR V5.0 - CALIBRÉ SUR BACKTEST")
    logger.info("   📊 Scoring: grosses cotes pénalisées, BTTS+, HOME-")
    logger.info("=" * 70)
    
    orch = OrchestratorV5()
    stats = orch.collect(hours_ahead=args.hours)
    orch.close()
    
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
