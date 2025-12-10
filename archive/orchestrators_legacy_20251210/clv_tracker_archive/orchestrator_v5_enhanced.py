#!/usr/bin/env python3
"""
🧠 CLV ORCHESTRATOR V5.3 ENHANCED - APPROCHE MATHÉMATIQUE PURE
═══════════════════════════════════════════════════════════════════

CORRECTIONS vs V5.2:
1. ✅ Plus de double comptage - Ajustements sur xG UNIQUEMENT
2. ✅ Multiplicateurs au lieu d'additions brutes
3. ✅ Cohérence mathématique (somme probas = 100%)
4. ✅ Erreur SQL corrigée

PHILOSOPHIE MATHÉMATIQUE:
- Ajuster les ENTRÉES (xG) pas les SORTIES (probabilités)
- Laisser Poisson faire le travail
- Multiplicateurs respectent l'échelle

Auteur: Mon_PS System
Date: 01/12/2025
"""
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from datetime import datetime
from decimal import Decimal
import json
import logging
import os
import math
from typing import Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('V5Enhanced')

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
}

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION TACTIQUE - MULTIPLICATEURS UNIQUEMENT
# ═══════════════════════════════════════════════════════════════════

# Multiplicateurs par style tactique (appliqués aux xG)
STYLE_XG_MULTIPLIERS = {
    'offensive': {'attack': 1.20, 'defense': 0.85},
    'balanced_offensive': {'attack': 1.10, 'defense': 0.92},
    'balanced': {'attack': 1.00, 'defense': 1.00},
    'balanced_defensive': {'attack': 0.92, 'defense': 1.10},
    'defensive': {'attack': 0.85, 'defense': 1.20},
}

# Profils - Multiplicateurs pour xG
PROFILE_XG_MULTIPLIERS = {
    'fortress': {'home_attack': 1.15, 'home_defense': 1.10, 'away_attack': 0.90, 'away_defense': 0.95},
    'road_warriors': {'home_attack': 1.00, 'home_defense': 1.00, 'away_attack': 1.15, 'away_defense': 1.05},
    'balanced': {'home_attack': 1.05, 'home_defense': 1.00, 'away_attack': 0.95, 'away_defense': 1.00},
    'draw_king': {'home_attack': 0.90, 'home_defense': 1.05, 'away_attack': 0.90, 'away_defense': 1.05},
}

# Analyse des cotes
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
    """Calcule toutes les probabilités via Poisson - MATHÉMATIQUEMENT PUR"""
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


class TacticalXGCalculator:
    """
    🧠 CALCULATEUR XG TACTIQUE
    
    PRINCIPE: Tous les ajustements se font sur les xG AVANT Poisson.
    Aucun ajustement post-probabilité = Cohérence mathématique garantie.
    """
    
    @staticmethod
    def calculate_tactical_xg(home_intel: Dict, away_intel: Dict) -> Dict:
        """
        Calcule les xG ajustés tactiquement.
        
        INPUTS:
        - Stats brutes des équipes
        - Styles tactiques
        - Profils (fortress, road_warriors, etc.)
        
        OUTPUTS:
        - home_xg ajusté
        - away_xg ajusté
        - Détails des ajustements
        """
        # 1. XG DE BASE (moyennes historiques)
        base_home_xg = (home_intel['home_goals_scored_avg'] + away_intel['away_goals_conceded_avg']) / 2
        base_away_xg = (away_intel['away_goals_scored_avg'] + home_intel['home_goals_conceded_avg']) / 2
        
        adjustments_log = []
        
        # 2. AJUSTEMENT STYLE TACTIQUE
        home_style = home_intel.get('current_style', 'balanced')
        away_style = away_intel.get('current_style', 'balanced')
        
        home_style_mult = STYLE_XG_MULTIPLIERS.get(home_style, STYLE_XG_MULTIPLIERS['balanced'])
        away_style_mult = STYLE_XG_MULTIPLIERS.get(away_style, STYLE_XG_MULTIPLIERS['balanced'])
        
        # Home attaque avec son style, Away défend avec son style
        home_xg = base_home_xg * home_style_mult['attack'] * (2 - away_style_mult['defense'])
        # Away attaque avec son style, Home défend avec son style
        away_xg = base_away_xg * away_style_mult['attack'] * (2 - home_style_mult['defense'])
        
        adjustments_log.append(f"Style: H={home_style}({home_style_mult['attack']}x) A={away_style}({away_style_mult['attack']}x)")
        
        # 3. AJUSTEMENT PROFIL (Fortress, Road Warriors, Draw King)
        home_profile = home_intel.get('home_profile', 'balanced')
        away_profile = away_intel.get('away_profile', 'balanced')
        
        home_profile_mult = PROFILE_XG_MULTIPLIERS.get(home_profile, PROFILE_XG_MULTIPLIERS['balanced'])
        away_profile_mult = PROFILE_XG_MULTIPLIERS.get(away_profile, PROFILE_XG_MULTIPLIERS['balanced'])
        
        home_xg *= home_profile_mult['home_attack']
        away_xg *= away_profile_mult['away_attack']
        
        adjustments_log.append(f"Profile: H={home_profile} A={away_profile}")
        
        # 4. AJUSTEMENT TENDANCES (goals_tendency, btts_tendency)
        home_goals_tendency = home_intel.get('goals_tendency', 50) / 100
        away_goals_tendency = away_intel.get('goals_tendency', 50) / 100
        
        # Si goals_tendency > 50%, légère augmentation des xG
        goals_mult = 0.8 + (home_goals_tendency + away_goals_tendency) / 2 * 0.4
        home_xg *= goals_mult
        away_xg *= goals_mult
        
        adjustments_log.append(f"Goals tendency mult: {goals_mult:.2f}")
        
        # 5. AJUSTEMENT DRAW KINGS (réduire les xG des deux côtés)
        home_draw = home_intel.get('draw_tendency', 50)
        away_draw = away_intel.get('draw_tendency', 50)
        
        if home_draw > 70 and away_draw > 70:
            # Deux Draw Kings = match fermé, réduire les xG
            draw_mult = 0.85
            home_xg *= draw_mult
            away_xg *= draw_mult
            adjustments_log.append(f"⚠️ Double Draw Kings: xG * {draw_mult}")
        elif home_draw > 80 or away_draw > 80:
            draw_mult = 0.92
            home_xg *= draw_mult
            away_xg *= draw_mult
            adjustments_log.append(f"Draw King detected: xG * {draw_mult}")
        
        # 6. DÉTECTION ASYMÉTRIE DANGEREUSE
        home_strength = home_intel.get('home_strength', 25)
        away_strength = away_intel.get('away_strength', 25)
        
        alerts = []
        
        # Away offensif vs Home défense faible
        if away_style in ['offensive', 'balanced_offensive'] and home_strength < 30:
            away_xg *= 1.15
            alerts.append({
                'type': 'AWAY_DANGER',
                'message': f"⚠️ AWAY offensif ({away_style}) vs HOME faible ({home_strength})"
            })
        
        # Home dominant
        if home_strength > 50 and away_strength < 25:
            home_xg *= 1.10
            alerts.append({
                'type': 'HOME_DOMINANT',
                'message': f"🔥 HOME dominant ({home_strength}) vs AWAY fragile ({away_strength})"
            })
        
        # Fortress vs Road Warriors
        if home_profile == 'fortress' and away_profile == 'road_warriors':
            alerts.append({
                'type': 'PROFILE_CLASH',
                'message': "🏰 FORTRESS vs 🛣️ ROAD WARRIORS"
            })
        
        # 7. LIMITER LES XG (éviter valeurs extrêmes)
        home_xg = max(0.4, min(3.5, home_xg))
        away_xg = max(0.3, min(3.0, away_xg))
        
        return {
            'home_xg': round(home_xg, 3),
            'away_xg': round(away_xg, 3),
            'base_home_xg': round(base_home_xg, 3),
            'base_away_xg': round(base_away_xg, 3),
            'adjustments': adjustments_log,
            'alerts': alerts,
            'home_style': home_style,
            'away_style': away_style,
            'home_profile': home_profile,
            'away_profile': away_profile,
        }


class OrchestratorV5Enhanced:
    """
    🧠 ORCHESTRATEUR V5.3 ENHANCED
    
    PRINCIPE MATHÉMATIQUE:
    - Ajuster les xG (entrées)
    - Laisser Poisson calculer (modèle)
    - Ne JAMAIS toucher aux probabilités (sorties)
    """
    
    def __init__(self):
        self.conn = None
        self.team_cache = {}
        self.stats = {
            'created': 0, 'matches': 0, 'errors': 0,
            'by_market': {}, 'by_matchup': {}, 'by_alert': {}
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
    
    def get_team_intelligence(self, team_name: str) -> Dict:
        """Récupère les données COMPLÈTES de team_intelligence"""
        if team_name in self.team_cache:
            return self.team_cache[team_name]
        
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            first_word = team_name.split()[0].lower() if team_name else ''
            
            cur.execute("""
                SELECT
                    team_name, league, league_tier,
                    current_style, current_pressing, current_form,
                    home_strength, away_strength,
                    home_profile, away_profile,
                    draw_tendency, goals_tendency, btts_tendency,
                    home_win_rate, home_draw_rate,
                    home_goals_scored_avg, home_goals_conceded_avg,
                    home_btts_rate, home_over25_rate,
                    home_clean_sheet_rate, home_failed_to_score_rate,
                    away_win_rate, away_draw_rate,
                    away_goals_scored_avg, away_goals_conceded_avg,
                    away_btts_rate, away_over25_rate,
                    away_clean_sheet_rate, away_failed_to_score_rate
                FROM team_intelligence
                WHERE LOWER(team_name) ILIKE %s
                   OR LOWER(team_name_normalized) ILIKE %s
                LIMIT 1
            """, (f'%{first_word}%', f'%{first_word}%'))
            
            row = cur.fetchone()
            conn.commit()
            
            if row:
                stats = {
                    'team_name': row.get('team_name'),
                    'league': row.get('league', ''),
                    'league_tier': row.get('league_tier', 1),
                    'current_style': row.get('current_style', 'balanced'),
                    'current_pressing': row.get('current_pressing', 'medium'),
                    'current_form': row.get('current_form', 'neutral'),
                    'home_strength': self._float(row.get('home_strength'), 25),
                    'away_strength': self._float(row.get('away_strength'), 25),
                    'home_profile': row.get('home_profile', 'balanced'),
                    'away_profile': row.get('away_profile', 'balanced'),
                    'draw_tendency': self._float(row.get('draw_tendency'), 50),
                    'goals_tendency': self._float(row.get('goals_tendency'), 50),
                    'btts_tendency': self._float(row.get('btts_tendency'), 50),
                    'home_win_rate': self._float(row.get('home_win_rate'), 40),
                    'home_draw_rate': self._float(row.get('home_draw_rate'), 30),
                    'home_goals_scored_avg': self._float(row.get('home_goals_scored_avg'), 1.3),
                    'home_goals_conceded_avg': self._float(row.get('home_goals_conceded_avg'), 1.1),
                    'home_btts_rate': self._float(row.get('home_btts_rate'), 50),
                    'home_over25_rate': self._float(row.get('home_over25_rate'), 50),
                    'home_clean_sheet_rate': self._float(row.get('home_clean_sheet_rate'), 30),
                    'away_win_rate': self._float(row.get('away_win_rate'), 30),
                    'away_draw_rate': self._float(row.get('away_draw_rate'), 30),
                    'away_goals_scored_avg': self._float(row.get('away_goals_scored_avg'), 1.0),
                    'away_goals_conceded_avg': self._float(row.get('away_goals_conceded_avg'), 1.4),
                    'away_btts_rate': self._float(row.get('away_btts_rate'), 50),
                    'away_over25_rate': self._float(row.get('away_over25_rate'), 50),
                    'away_clean_sheet_rate': self._float(row.get('away_clean_sheet_rate'), 25),
                }
            else:
                stats = self._default_intelligence()
            
            self.team_cache[team_name] = stats
            return stats
            
        except Exception as e:
            conn.rollback()
            logger.debug(f"Error: {e}")
            return self._default_intelligence()
        finally:
            cur.close()
    
    def _default_intelligence(self) -> Dict:
        return {
            'team_name': 'Unknown', 'league': '', 'league_tier': 2,
            'current_style': 'balanced', 'current_pressing': 'medium', 'current_form': 'neutral',
            'home_strength': 25, 'away_strength': 25,
            'home_profile': 'balanced', 'away_profile': 'balanced',
            'draw_tendency': 50, 'goals_tendency': 50, 'btts_tendency': 50,
            'home_win_rate': 40, 'home_draw_rate': 30,
            'home_goals_scored_avg': 1.3, 'home_goals_conceded_avg': 1.1,
            'home_btts_rate': 50, 'home_over25_rate': 50, 'home_clean_sheet_rate': 30,
            'away_win_rate': 30, 'away_draw_rate': 30,
            'away_goals_scored_avg': 1.0, 'away_goals_conceded_avg': 1.4,
            'away_btts_rate': 50, 'away_over25_rate': 50, 'away_clean_sheet_rate': 25,
        }
    
    def calculate_score(self, prob: float, odds: float, market_type: str) -> Dict:
        """Scoring SIMPLE basé sur probabilité et cotes"""
        if not odds or odds <= 1 or prob <= 0:
            return {'score': 0, 'confidence': 'none', 'rating': '❌ INVALIDE'}
        
        implied = 1 / odds
        edge = prob - implied
        edge_pct = edge * 100
        
        kelly = min((edge / (odds - 1)) * 100, 10) if edge > 0 else 0
        odds_info = get_odds_analysis(odds)
        
        # Score basé sur probabilité (40 pts) + edge (30 pts) + fiabilité (30 pts)
        prob_score = prob * 40
        edge_score = max(-15, min(30, edge_pct * 2))
        reliability_score = odds_info['reliability'] * 0.3
        
        final_score = max(0, min(100, int(prob_score + edge_score + reliability_score)))
        
        if final_score >= 75:
            confidence, rating = 'very_high', '🔥 EXCELLENT'
        elif final_score >= 65:
            confidence, rating = 'high', '✅ TRÈS BON'
        elif final_score >= 55:
            confidence, rating = 'medium', '📊 BON'
        elif final_score >= 45:
            confidence, rating = 'low', '📈 CORRECT'
        else:
            confidence, rating = 'very_low', '⚠️ MARGINAL'
        
        return {
            'score': final_score,
            'confidence': confidence,
            'risk_level': odds_info['risk'],
            'value_edge': round(edge_pct, 2),
            'kelly': round(kelly, 2),
            'rating': rating,
        }
    
    def collect(self, hours_ahead: int = 48) -> Dict:
        """🧠 COLLECTE V5.3 - Ajustements sur xG uniquement"""
        start = datetime.now()
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        logger.info("�� COLLECT V5.3 ENHANCED - Approche Mathématique Pure")
        
        try:
            # CORRIGÉ: Pas de o.league (n'existe pas dans odds_history)
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
                # 🧠 INTELLIGENCE TACTIQUE
                home_intel = self.get_team_intelligence(match['home_team'])
                away_intel = self.get_team_intelligence(match['away_team'])
                
                # 🎯 CALCUL XG TACTIQUE (TOUT se passe ici)
                xg_result = TacticalXGCalculator.calculate_tactical_xg(home_intel, away_intel)
                
                home_xg = xg_result['home_xg']
                away_xg = xg_result['away_xg']
                alerts = xg_result['alerts']
                
                # Log alertes importantes
                for alert in alerts:
                    logger.info(f"  {alert['message']} - {match['home_team']} vs {match['away_team']}")
                    alert_type = alert['type']
                    if alert_type not in self.stats['by_alert']:
                        self.stats['by_alert'][alert_type] = 0
                    self.stats['by_alert'][alert_type] += 1
                
                # 📊 PROBABILITÉS POISSON (mathématiquement pures)
                probs = calculate_match_probabilities(home_xg, away_xg)
                
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
                
                # Totals
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
                
                # Générer picks (PAS d'ajustement sur probs!)
                match_picks = []
                for market, prob in probs.items():
                    odds = odds_map.get(market, 0)
                    if not odds or odds <= 1:
                        continue
                    
                    scoring = self.calculate_score(prob, odds, market)
                    
                    if market not in self.stats['by_market']:
                        self.stats['by_market'][market] = {'count': 0, 'total_score': 0}
                    self.stats['by_market'][market]['count'] += 1
                    self.stats['by_market'][market]['total_score'] += scoring['score']
                    
                    pick = {
                        'match_id': match['match_id'],
                        'home_team': match['home_team'],
                        'away_team': match['away_team'],
                        'league': home_intel.get('league', ''),
                        'commence_time': match['commence_time'],
                        'market_type': market,
                        'odds': odds,
                        'probability': round(prob * 100, 2),
                        'score': scoring['score'],
                        'kelly': scoring['kelly'],
                        'edge_pct': scoring['value_edge'],
                        'rating': scoring['rating'],
                        'confidence': scoring['confidence'],
                        'risk_level': scoring['risk_level'],
                        'home_xg': home_xg,
                        'away_xg': away_xg,
                        'factors': {
                            'home_xg': home_xg,
                            'away_xg': away_xg,
                            'base_home_xg': xg_result['base_home_xg'],
                            'base_away_xg': xg_result['base_away_xg'],
                            'home_style': xg_result['home_style'],
                            'away_style': xg_result['away_style'],
                            'home_profile': xg_result['home_profile'],
                            'away_profile': xg_result['away_profile'],
                            'adjustments': xg_result['adjustments'],
                            'alerts': [a['message'] for a in alerts],
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
                               f"xG={home_xg:.2f}-{away_xg:.2f} | TOP: {top['market_type']}={top['score']}")
            
            except Exception as e:
                self.stats['errors'] += 1
                logger.debug(f"Error: {e}")
        
        cur.close()
        
        if all_picks:
            self._save_picks(all_picks)
        
        duration = (datetime.now() - start).total_seconds()
        self.stats['created'] = len(all_picks)
        
        logger.info(f"\n✅ V5.3 ENHANCED: {len(all_picks)} picks | {self.stats['matches']} matchs | {duration:.1f}s")
        
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
                        home_xg, away_xg, total_xg,
                        is_top3, factors, source, commence_time
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (match_id, market_type, source)
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
                    pick.get('is_top3', False), Json(pick.get('factors', {})),
                    'v5_enhanced', pick['commence_time']
                ))
            except Exception as e:
                conn.rollback()
                logger.debug(f"Save error: {e}")
        
        conn.commit()
        cur.close()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--hours', type=int, default=48)
    args = parser.parse_args()
    
    logger.info("=" * 70)
    logger.info("🧠 CLV ORCHESTRATOR V5.3 ENHANCED")
    logger.info("   📊 Approche Mathématique Pure")
    logger.info("   🎯 Ajustements sur xG uniquement (pas de double comptage)")
    logger.info("=" * 70)
    
    orch = OrchestratorV5Enhanced()
    stats = orch.collect(hours_ahead=args.hours)
    
    print("\n📊 PICKS PAR MARCHÉ:")
    for market, data in sorted(stats['by_market'].items(), key=lambda x: x[1]['count'], reverse=True):
        avg = data['total_score'] / data['count'] if data['count'] > 0 else 0
        print(f"   {market:12} | {data['count']:3} picks | Score moy: {avg:.1f}")
    
    print("\n⚠️ ALERTES DÉTECTÉES:")
    for alert_type, count in stats['by_alert'].items():
        print(f"   {alert_type:20} | {count:3} matchs")
    
    orch.close()
    
    print(json.dumps({'created': stats['created'], 'matches': stats['matches']}, indent=2))


if __name__ == "__main__":
    main()
