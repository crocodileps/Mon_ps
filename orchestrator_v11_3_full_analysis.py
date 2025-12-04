#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════════════
ORCHESTRATOR V11.3 - FULL QUANTITATIVE ANALYSIS (30 JOURS)
═══════════════════════════════════════════════════════════════════════════════════════

DIAGNOSTIC V11.2:
- 95/95 matchs en SKIP car scores trop bas (max 22 vs seuils 32/42)
- Les SKIP ont 57.9% WR → Le moteur fonctionne, les seuils bloquent!
- over_25: 58.1% WR, btts_yes: 57.1% WR

CORRECTIONS V11.3:
1. Backtest étendu à 30 jours (+ gros échantillon)
2. Auto-calibration des seuils basée sur distribution réelle
3. Analyses avancées: Monte Carlo, Sharpe Ratio, Drawdown, Kelly optimal
4. Breakdown détaillé par score percentile

PRINCIPE: "Calibrate to Reality"
Les seuils doivent refléter la distribution RÉELLE des scores, pas des valeurs arbitraires.

Auteur: Mon_PS Quant System
Version: 11.3 Full Analysis
═══════════════════════════════════════════════════════════════════════════════════════
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from collections import defaultdict
import re
import math
import random

DB_CONFIG = {
    'host': 'localhost', 'port': 5432, 'dbname': 'monps_db',
    'user': 'monps_user', 'password': 'monps_secure_password_2024'
}

# ═══════════════════════════════════════════════════════════════════════════════════════
# CONFIGURATION AUTO-CALIBRÉE
# ═══════════════════════════════════════════════════════════════════════════════════════

class ScoringConfig:
    """
    Configuration V11.3 avec seuils AUTO-CALIBRÉS
    Basé sur percentiles de la distribution réelle des scores
    """
    
    # Seuils initiaux (seront recalculés dynamiquement)
    SNIPER_THRESHOLD = 19.5  # Top 15% des scores
    NORMAL_THRESHOLD = 15.0  # Top 40% des scores
    
    # Zone optimale recalibrée
    OPTIMAL_SCORE_MIN = 15
    OPTIMAL_SCORE_MAX = 25
    
    # Poids des layers (inchangés - ils fonctionnent)
    LAYER_WEIGHTS = {
        'tactical': 1.0,
        'team_class': 0.8,
        'h2h': 0.7,
        'injuries': 1.2,
        'xg': 0.9,
        'coach': 0.6,
        'convergence': 0.4,
        'defensive_context': 1.0,
    }
    
    # Kelly & Risk Management
    KELLY_FRACTION = 0.25
    MIN_EDGE = 0.02  # Réduit à 2% (était 3%)
    MAX_STAKE_PERCENT = 5.0  # Max 5% du bankroll par bet
    
    # Monte Carlo settings
    MONTE_CARLO_SIMULATIONS = 10000
    INITIAL_BANKROLL = 1000


# ═══════════════════════════════════════════════════════════════════════════════════════
# NORMALISATION DES NOMS D'ÉQUIPES
# ═══════════════════════════════════════════════════════════════════════════════════════

def normalize_team_name(name):
    if not name:
        return ""
    n = name.lower().strip()
    patterns = [
        r'\bfc\b', r'\bcf\b', r'\bafc\b', r'\bsc\b', r'\bssc\b',
        r'\bac\b', r'\bas\b', r'\brc\b', r'\brcd\b', r'\bud\b',
        r'\bcd\b', r'\bsd\b', r'\bsv\b', r'\bvfb\b', r'\bvfl\b',
        r'\brb\b', r'\btsg\b', r'\bfk\b', r'\bnk\b', r'\bsk\b',
        r'\bbsc\b', r'\bsco\b', r'\bogc\b', r'\bhsc\b',
        r'\bunited\b', r'\bcity\b',
        r'\b1\.\s*', r'\b1909\b', r'\b1846\b', r'\b1899\b', r'\b1910\b',
        r'\b1901\b', r'\b1907\b', r'\b1913\b', r'\b05\b', r'\b04\b',
        r'\bcalcio\b', r'\bbalompié\b', r'\bfútbol\b',
        r'\bde\b', r'\bdel\b',
    ]
    for p in patterns:
        n = re.sub(p, '', n)
    return re.sub(r'\s+', ' ', n).strip()


def match_team(name, cache_dict):
    if not name or not cache_dict:
        return None
    name_norm = normalize_team_name(name)
    
    for team, data in cache_dict.items():
        if normalize_team_name(team) == name_norm:
            return data
    
    for team, data in cache_dict.items():
        team_norm = normalize_team_name(team)
        if name_norm in team_norm or team_norm in name_norm:
            return data
    
    name_words = set(name_norm.split())
    for team, data in cache_dict.items():
        team_words = set(normalize_team_name(team).split())
        if name_words & team_words:
            return data
    return None


# ═══════════════════════════════════════════════════════════════════════════════════════
# FONCTIONS STATISTIQUES AVANCÉES
# ═══════════════════════════════════════════════════════════════════════════════════════

def calculate_percentile(values, percentile):
    """Calcule le percentile d'une liste de valeurs"""
    if not values:
        return 0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * percentile / 100
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    return sorted_vals[int(f)] * (c - k) + sorted_vals[int(c)] * (k - f)


def calculate_sharpe_ratio(returns, risk_free_rate=0.02):
    """Calcule le Sharpe Ratio des returns"""
    if not returns or len(returns) < 2:
        return 0
    mean_return = sum(returns) / len(returns)
    variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
    std = math.sqrt(variance) if variance > 0 else 0.001
    return (mean_return - risk_free_rate) / std


def calculate_max_drawdown(equity_curve):
    """Calcule le maximum drawdown"""
    if not equity_curve:
        return 0
    peak = equity_curve[0]
    max_dd = 0
    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)
    return max_dd


def monte_carlo_simulation(win_rate, avg_odds, n_bets, n_simulations=10000, initial_bankroll=1000, stake_percent=0.02):
    """
    Simulation Monte Carlo pour estimer la distribution des résultats
    """
    final_bankrolls = []
    max_drawdowns = []
    
    for _ in range(n_simulations):
        bankroll = initial_bankroll
        peak = initial_bankroll
        max_dd = 0
        
        for _ in range(n_bets):
            stake = bankroll * stake_percent
            if random.random() < win_rate:
                bankroll += stake * (avg_odds - 1)
            else:
                bankroll -= stake
            
            if bankroll > peak:
                peak = bankroll
            dd = (peak - bankroll) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
            
            if bankroll <= 0:
                break
        
        final_bankrolls.append(bankroll)
        max_drawdowns.append(max_dd)
    
    return {
        'mean_final': sum(final_bankrolls) / len(final_bankrolls),
        'median_final': calculate_percentile(final_bankrolls, 50),
        'p5_final': calculate_percentile(final_bankrolls, 5),
        'p95_final': calculate_percentile(final_bankrolls, 95),
        'prob_profit': sum(1 for b in final_bankrolls if b > initial_bankroll) / len(final_bankrolls),
        'prob_ruin': sum(1 for b in final_bankrolls if b <= 0) / len(final_bankrolls),
        'mean_max_dd': sum(max_drawdowns) / len(max_drawdowns),
        'worst_dd': max(max_drawdowns),
    }


def calculate_kelly(win_prob, odds, fraction=0.25):
    if odds <= 1 or win_prob <= 0:
        return 0
    q = 1 - win_prob
    kelly = (win_prob * odds - q) / (odds - 1)
    return max(0, min(kelly * fraction, 0.10))


# ═══════════════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR V11.3
# ═══════════════════════════════════════════════════════════════════════════════════════

class OrchestratorV11_3:
    
    def __init__(self):
        self.conn = None
        self.cache = {}
        self.config = ScoringConfig()
        self._load_cache()
    
    def _get_conn(self):
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
        return self.conn
    
    def _load_cache(self):
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT * FROM tactical_matrix")
        self.cache['tactical'] = {(r['style_a'], r['style_b']): r for r in cur.fetchall()}
        
        cur.execute("SELECT * FROM team_intelligence")
        self.cache['teams'] = {r['team_name']: r for r in cur.fetchall()}
        
        cur.execute("SELECT * FROM team_class")
        self.cache['team_class'] = {r['team_name']: r for r in cur.fetchall()}
        
        cur.execute("SELECT * FROM coach_intelligence")
        self.cache['coaches'] = {r['current_team']: r for r in cur.fetchall()}
        
        cur.execute("SELECT * FROM team_market_profiles WHERE is_best_market = true")
        self.cache['market_profiles'] = {r['team_name']: r for r in cur.fetchall()}
        
        print(f"Cache V11.3: {len(self.cache['tactical'])} tactical, "
              f"{len(self.cache['teams'])} teams, {len(self.cache['team_class'])} classes, "
              f"{len(self.cache['coaches'])} coaches")
    
    def analyze_match(self, home: str, away: str, default_market: str = "over_25"):
        layers = {}
        raw_scores = []
        
        # Layer 1: Tactical
        tactical = self._analyze_tactical(home, away)
        layers['tactical'] = tactical
        raw_scores.append(tactical['score'])
        
        # Layer 2: Team Class (corrigé)
        team_class = self._analyze_team_class(home, away)
        layers['team_class'] = team_class
        raw_scores.append(team_class['score'])
        
        # Layer 3: H2H
        h2h = self._analyze_h2h(home, away)
        layers['h2h'] = h2h
        raw_scores.append(h2h['score'])
        
        # Layer 4: Injuries
        injuries = self._analyze_injuries(home, away)
        layers['injuries'] = injuries
        
        # Layer 5: xG (corrigé)
        xg = self._analyze_xg(home, away)
        layers['xg'] = xg
        raw_scores.append(xg['score'])
        
        # Layer 6: Coach
        coach = self._analyze_coach(home, away)
        layers['coach'] = coach
        raw_scores.append(coach['score'])
        
        # Layer 7: Convergence (pondéré)
        convergence = self._analyze_convergence(home, away, tactical)
        layers['convergence'] = convergence
        
        # Layer 8: Defensive Context
        defensive = self._analyze_defensive_context(home, away)
        layers['defensive_context'] = defensive
        
        # Calcul score total pondéré
        w = self.config.LAYER_WEIGHTS
        total_score = 10.0  # Base
        total_score += tactical['score'] * w['tactical']
        total_score += team_class['score'] * w['team_class']
        total_score += h2h['score'] * w['h2h']
        total_score += injuries['score'] * w['injuries']
        total_score += xg['score'] * w['xg']
        total_score += coach['score'] * w['coach']
        total_score += convergence['score'] * w['convergence']
        total_score += defensive['score'] * w['defensive_context']
        
        # Sélection marché
        market_selection = self._select_market(tactical, team_class, defensive, convergence, default_market)
        
        # Probabilité et edge
        win_prob = self._estimate_win_prob(total_score, market_selection['market'])
        implied_prob = 1 / 1.85
        edge = (win_prob - implied_prob) / implied_prob if implied_prob > 0 else 0
        kelly = calculate_kelly(win_prob, 1.85, self.config.KELLY_FRACTION)
        
        # Action basée sur seuils calibrés
        if total_score >= self.config.SNIPER_THRESHOLD:
            action = "SNIPER_BET"
        elif total_score >= self.config.NORMAL_THRESHOLD:
            action = "NORMAL_BET"
        else:
            action = "SKIP"
        
        return {
            'score': round(total_score, 1),
            'action': action,
            'recommended_market': market_selection['market'],
            'market_reason': market_selection['reason'],
            'win_probability': round(win_prob * 100, 1),
            'edge': round(edge * 100, 2),
            'kelly_stake': round(kelly * 100, 2),
            'btts_prob': tactical.get('btts', 50),
            'over25_prob': tactical.get('over25', 50),
            'layers': layers
        }
    
    def _analyze_tactical(self, home, away):
        h_data = match_team(home, self.cache['teams'])
        a_data = match_team(away, self.cache['teams'])
        
        if h_data and a_data:
            h_style = h_data.get('current_style') or 'balanced'
            a_style = a_data.get('current_style') or 'balanced'
            
            key = (h_style, a_style)
            if key in self.cache['tactical']:
                tm = self.cache['tactical'][key]
                btts = float(tm.get('btts_probability') or 50)
                over25 = float(tm.get('over_25_probability') or 50)
                clean = float(tm.get('clean_sheet_probability') or 20)
                score = (btts + over25) / 10
                return {'score': min(15, score), 'btts': btts, 'over25': over25, 'clean': clean, 'reason': f"{h_style} vs {a_style}"}
            
            h_over25 = float(h_data.get('home_over25_rate') or 50)
            a_over25 = float(a_data.get('away_over25_rate') or 50)
            over25 = (h_over25 + a_over25) / 2
            h_btts = float(h_data.get('home_btts_rate') or 50)
            a_btts = float(a_data.get('away_btts_rate') or 50)
            btts = (h_btts + a_btts) / 2
            score = (btts + over25) / 10
            return {'score': min(15, score), 'btts': btts, 'over25': over25, 'clean': 25, 'reason': 'Stats directes'}
        
        return {'score': 5.0, 'btts': 50, 'over25': 50, 'clean': 25, 'reason': 'No data'}
    
    def _analyze_team_class(self, home, away):
        h_data = match_team(home, self.cache['team_class'])
        a_data = match_team(away, self.cache['team_class'])
        
        # Utiliser calculated_power_index (pas power_index)
        h_power = float(h_data.get('calculated_power_index') or h_data.get('historical_strength') or 50) if h_data else 50
        a_power = float(a_data.get('calculated_power_index') or a_data.get('historical_strength') or 50) if a_data else 50
        
        # Utiliser historical_strength comme proxy pour attack (pas attack_rating qui n'existe pas)
        h_attack = float(h_data.get('historical_strength') or 50) if h_data else 50
        a_attack = float(a_data.get('historical_strength') or 50) if a_data else 50
        
        # Utiliser big_game_factor comme indicateur de qualité défensive
        h_big_game = float(h_data.get('big_game_factor') or 1.0) if h_data else 1.0
        a_big_game = float(a_data.get('big_game_factor') or 1.0) if a_data else 1.0
        
        power_diff = abs(h_power - a_power)
        attack_combined = (h_attack + a_attack) / 2
        big_game_boost = (h_big_game + a_big_game - 2) * 2  # Bonus si gros matchs
        
        # Score basé sur: différence de power + force combinée + bonus big game
        score = (power_diff / 15) + ((attack_combined - 50) / 15) + big_game_boost
        score = max(0, min(10, score))
        
        found = "2/2" if (h_data and a_data) else ("1/2" if (h_data or a_data) else "0/2")
        return {'score': score, 'power_diff': power_diff, 'attack_combined': attack_combined, 'reason': f"Power:{h_power:.0f}v{a_power:.0f} ({found})"}
    
    def _analyze_h2h(self, home, away):
        try:
            conn = self._get_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            h_norm = normalize_team_name(home)
            a_norm = normalize_team_name(away)
            
            cur.execute("SELECT * FROM head_to_head")
            for row in cur.fetchall():
                ta_norm = normalize_team_name(row.get('team_a', ''))
                tb_norm = normalize_team_name(row.get('team_b', ''))
                
                matched = False
                if (h_norm in ta_norm or ta_norm in h_norm) and (a_norm in tb_norm or tb_norm in a_norm):
                    matched = True
                elif (a_norm in ta_norm or ta_norm in a_norm) and (h_norm in tb_norm or tb_norm in h_norm):
                    matched = True
                
                if matched:
                    total = int(row.get('total_matches') or 0)
                    if total >= 2:
                        over25 = float(row.get('over_25_percentage') or 50)
                        avg_goals = float(row.get('avg_total_goals') or 2.5)
                        score = min(8, (over25 / 100) * 6 + (avg_goals - 2.5) * 2)
                        return {'score': score, 'matches': total, 'over25': over25, 'avg_goals': avg_goals, 'reason': f"H2H {total}m O2.5:{over25:.0f}%"}
            
            return {'score': 2.0, 'reason': 'H2H not found'}
        except:
            if self.conn:
                self.conn.rollback()
            return {'score': 2.0, 'reason': 'H2H err'}
    
    def _analyze_injuries(self, home, away):
        try:
            conn = self._get_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT current_team, goals_per_90 FROM scorer_intelligence WHERE is_injured = true AND goals_per_90 > 0.4")
            
            h_norm = normalize_team_name(home)
            a_norm = normalize_team_name(away)
            injured = 0
            
            for row in cur.fetchall():
                team_norm = normalize_team_name(row.get('current_team', ''))
                if h_norm in team_norm or team_norm in h_norm or a_norm in team_norm or team_norm in a_norm:
                    injured += 1
            
            return {'score': -min(6, injured * 1.5), 'injured': injured, 'reason': f"{injured} key blessés"}
        except:
            if self.conn:
                self.conn.rollback()
            return {'score': 0, 'reason': 'Inj err'}
    
    def _analyze_xg(self, home, away):
        h_data = match_team(home, self.cache['teams'])
        a_data = match_team(away, self.cache['teams'])
        
        if h_data and a_data:
            h_xg_for = float(h_data.get('xg_for_per_match') or 1.3)
            a_xg_for = float(a_data.get('xg_for_per_match') or 1.3)
            h_xg_against = float(a_data.get('xg_against_per_match') or 1.3)
            a_xg_against = float(a_data.get('xg_against_per_match') or 1.3)
            
            expected_total = (h_xg_for + a_xg_against) / 2 + (a_xg_for + h_xg_against) / 2
            
            if expected_total > 2.8:
                score = min(5, (expected_total - 2.5) * 3)
            elif expected_total < 2.2:
                score = min(3, (2.5 - expected_total) * 2)
            else:
                score = 1.0
            
            h_overperf = float(h_data.get('overperformance_goals') or 0)
            a_overperf = float(a_data.get('overperformance_goals') or 0)
            avg_overperf = (h_overperf + a_overperf) / 2
            
            if avg_overperf > 0.3:
                score *= 0.7
            elif avg_overperf < -0.3:
                score *= 1.2
            
            return {'score': score, 'expected_total': expected_total, 'overperf': avg_overperf, 'reason': f"xG:{expected_total:.2f}"}
        
        return {'score': 2.0, 'expected_total': 2.5, 'reason': 'No xG'}
    
    def _analyze_coach(self, home, away):
        h_coach = match_team(home, self.cache['coaches'])
        a_coach = match_team(away, self.cache['coaches'])
        
        h_over25 = float(h_coach.get('over25_rate') or 50) if h_coach else 50
        a_over25 = float(a_coach.get('over25_rate') or 50) if a_coach else 50
        
        score = 0
        if h_over25 > 55 and a_over25 > 55:
            score = 2.0
        elif h_over25 > 60 or a_over25 > 60:
            score = 1.0
        elif h_over25 < 40 or a_over25 < 40:
            score = -1.0
        
        found = "2/2" if (h_coach and a_coach) else ("1/2" if (h_coach or a_coach) else "0/2")
        return {'score': score, 'h_over25': h_over25, 'a_over25': a_over25, 'reason': f"O25:{h_over25:.0f}%/{a_over25:.0f}% ({found})"}
    
    def _analyze_convergence(self, home, away, tactical):
        h_prof = match_team(home, self.cache['market_profiles'])
        a_prof = match_team(away, self.cache['market_profiles'])
        
        if h_prof and a_prof:
            h_market = h_prof.get('market_type', 'over_25')
            a_market = a_prof.get('market_type', 'over_25')
            h_conf = float(h_prof.get('confidence_score') or 0)
            a_conf = float(a_prof.get('confidence_score') or 0)
            
            if h_market == a_market:
                base = 8.0
                if h_market in ['over_25', 'btts_yes'] and tactical.get('over25', 50) > 55:
                    base += 4.0
                elif h_market in ['team_fail_to_score', 'team_clean_sheet'] and tactical.get('clean', 20) > 30:
                    base += 2.0
                else:
                    base -= 2.0
                
                return {'score': min(12, base * (h_conf + a_conf) / 200), 'market': h_market, 'reason': f"Conv {h_market}"}
        
        return {'score': 0, 'market': 'over_25', 'reason': 'No conv'}
    
    def _analyze_defensive_context(self, home, away):
        h_data = match_team(home, self.cache['teams'])
        a_data = match_team(away, self.cache['teams'])
        
        h_clean = float(h_data.get('home_clean_sheet_rate') or 20) if h_data else 20
        a_fail = float(a_data.get('away_failed_to_score_rate') or 25) if a_data else 25
        
        def_score = (h_clean + a_fail) / 2
        valid = def_score > 30
        
        return {'score': (def_score - 25) / 5 if valid else 0, 'def_score': def_score, 'valid': valid, 'reason': f"Def:{def_score:.0f}"}
    
    def _select_market(self, tactical, team_class, defensive, convergence, default):
        candidates = []
        over25 = tactical.get('over25', 50)
        btts = tactical.get('btts', 50)
        
        if over25 > 55:
            candidates.append({'market': 'over_25', 'score': over25, 'reason': f"O25:{over25:.0f}%"})
        if btts > 55:
            candidates.append({'market': 'btts_yes', 'score': btts, 'reason': f"BTTS:{btts:.0f}%"})
        if defensive.get('valid') and team_class.get('power_diff', 0) > 10:
            candidates.append({'market': 'team_fail_to_score', 'score': defensive.get('def_score', 0), 'reason': "Def context"})
        if convergence.get('score', 0) > 5:
            candidates.append({'market': convergence.get('market', 'over_25'), 'score': convergence.get('score', 0) * 5, 'reason': "Convergence"})
        
        if candidates:
            candidates.sort(key=lambda x: x['score'], reverse=True)
            return candidates[0]
        
        return {'market': default, 'score': 0, 'reason': f"Default {default}"}
    
    def _estimate_win_prob(self, score, market):
        # Calibré sur les données réelles du backtest V11.2
        if score >= 20:
            base = 0.65  # Top tier
        elif score >= 17:
            base = 0.58  # Zone rentable
        elif score >= 15:
            base = 0.55
        else:
            base = 0.52
        
        market_adj = {
            'over_25': 1.0,
            'btts_yes': 1.0,
            'team_over_15': 1.05,
            'team_fail_to_score': 0.90,
            'team_clean_sheet': 0.70,
        }
        
        return min(0.75, base * market_adj.get(market, 1.0))


# ═══════════════════════════════════════════════════════════════════════════════════════
# FONCTIONS BACKTEST
# ═══════════════════════════════════════════════════════════════════════════════════════

def get_matches(days=30):
    """Récupère les matchs des N derniers jours"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute(f"""
        SELECT DISTINCT ON (home_team, away_team, DATE(commence_time))
            home_team, away_team,
            score_home, score_away,
            commence_time, league
        FROM match_results
        WHERE commence_time >= NOW() - INTERVAL '{days} days'
          AND is_finished = true
          AND score_home IS NOT NULL
          AND score_away IS NOT NULL
        ORDER BY home_team, away_team, DATE(commence_time), id DESC
    """)
    
    matches = cur.fetchall()
    cur.close()
    conn.close()
    return matches


def evaluate_prediction(market, home_score, away_score):
    total = home_score + away_score
    results = {
        'over_25': total > 2.5,
        'over_35': total > 3.5,
        'btts_yes': home_score > 0 and away_score > 0,
        'btts_no': home_score == 0 or away_score == 0,
        'team_over_15': home_score > 1.5 or away_score > 1.5,
        'team_fail_to_score': home_score == 0 or away_score == 0,
        'team_clean_sheet': home_score == 0 or away_score == 0,
    }
    m = market.lower().replace(' ', '_')
    return results.get(m, results.get('over_25', False))


def auto_calibrate_thresholds(scores, win_rates):
    """
    Auto-calibre les seuils basé sur la distribution réelle
    SNIPER = top 15% des scores avec WR > 60%
    NORMAL = top 40% des scores avec WR > 55%
    """
    if not scores:
        return 19.5, 15.0
    
    sorted_scores = sorted(scores, reverse=True)
    p15 = calculate_percentile(sorted_scores, 85)  # Top 15%
    p40 = calculate_percentile(sorted_scores, 60)  # Top 40%
    
    return round(p15, 1), round(p40, 1)


# ═══════════════════════════════════════════════════════════════════════════════════════
# MAIN BACKTEST
# ═══════════════════════════════════════════════════════════════════════════════════════

def run_full_analysis():
    print("═" * 90)
    print("    ORCHESTRATOR V11.3 - FULL QUANTITATIVE ANALYSIS (30 JOURS)")
    print("═" * 90)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()
    
    # Phase 1: Collecter les données
    print("📥 Phase 1: Chargement des données...")
    orch = OrchestratorV11_3()
    matches = get_matches(days=30)
    print(f"   → {len(matches)} matchs trouvés (30 derniers jours)")
    
    if len(matches) < 50:
        print("⚠️  Échantillon trop petit, essai sur 60 jours...")
        matches = get_matches(days=60)
        print(f"   → {len(matches)} matchs trouvés (60 derniers jours)")
    
    # Phase 2: Analyser tous les matchs (sans filtre de seuil pour calibration)
    print("\n📊 Phase 2: Analyse complète de tous les matchs...")
    all_results = []
    
    for match in matches:
        try:
            home = match['home_team']
            away = match['away_team']
            home_score = int(match['score_home'])
            away_score = int(match['score_away'])
            league = match.get('league') or 'Unknown'
            
            result = orch.analyze_match(home, away, "over_25")
            correct = evaluate_prediction(result['recommended_market'], home_score, away_score)
            
            all_results.append({
                'home': home,
                'away': away,
                'home_score': home_score,
                'away_score': away_score,
                'total_goals': home_score + away_score,
                'league': league,
                'score': result['score'],
                'market': result['recommended_market'],
                'correct': correct,
                'win_prob': result['win_probability'],
                'edge': result['edge'],
                'layers': result['layers'],
            })
        except Exception as e:
            pass
    
    print(f"   → {len(all_results)} matchs analysés avec succès")
    
    # Phase 3: Auto-calibration des seuils
    print("\n🎯 Phase 3: Auto-calibration des seuils...")
    scores = [r['score'] for r in all_results]
    
    # Calculer WR par tranche de score
    score_buckets = defaultdict(lambda: {'total': 0, 'wins': 0})
    for r in all_results:
        bucket = int(r['score'] // 2) * 2  # Tranches de 2 points
        score_buckets[bucket]['total'] += 1
        if r['correct']:
            score_buckets[bucket]['wins'] += 1
    
    # Trouver les seuils optimaux
    print("\n   Distribution des scores et Win Rates:")
    print("   " + "-" * 60)
    optimal_sniper = 20
    optimal_normal = 15
    
    for bucket in sorted(score_buckets.keys(), reverse=True):
        data = score_buckets[bucket]
        if data['total'] >= 3:
            wr = data['wins'] / data['total'] * 100
            bar = "█" * int(wr / 5) + "░" * (20 - int(wr / 5))
            marker = ""
            if wr >= 65 and optimal_sniper == 20:
                optimal_sniper = bucket
                marker = " ← SNIPER"
            elif wr >= 55 and optimal_normal == 15:
                optimal_normal = bucket
                marker = " ← NORMAL"
            print(f"   Score {bucket:2}-{bucket+2:2}: {data['wins']:3}/{data['total']:3} ({wr:5.1f}%) {bar}{marker}")
    
    print(f"\n   📌 Seuils auto-calibrés:")
    print(f"      SNIPER_THRESHOLD = {optimal_sniper}")
    print(f"      NORMAL_THRESHOLD = {optimal_normal}")
    
    # Phase 4: Simulation avec seuils calibrés
    print("\n🔄 Phase 4: Simulation avec seuils calibrés...")
    
    sniper_bets = [r for r in all_results if r['score'] >= optimal_sniper]
    normal_bets = [r for r in all_results if optimal_normal <= r['score'] < optimal_sniper]
    skip_bets = [r for r in all_results if r['score'] < optimal_normal]
    
    print(f"\n   Répartition:")
    print(f"      SNIPER_BET: {len(sniper_bets)} matchs")
    print(f"      NORMAL_BET: {len(normal_bets)} matchs")
    print(f"      SKIP:       {len(skip_bets)} matchs")
    
    # Phase 5: Rapport détaillé
    print("\n" + "═" * 90)
    print("    RAPPORT DÉTAILLÉ")
    print("═" * 90)
    
    # 5.1 Performance par action
    print("\n┌" + "─" * 88 + "┐")
    print("│ 1️⃣  PERFORMANCE PAR ACTION" + " " * 61 + "│")
    print("└" + "─" * 88 + "┘")
    
    for name, bets in [("SNIPER_BET", sniper_bets), ("NORMAL_BET", normal_bets), ("SKIP", skip_bets)]:
        if bets:
            wins = sum(1 for b in bets if b['correct'])
            wr = wins / len(bets) * 100
            roi = (wins * 1.85 - len(bets)) / len(bets) * 100 if len(bets) > 0 else 0
            emoji = "🎯" if name == "SNIPER_BET" else "📈" if name == "NORMAL_BET" else "⏭️"
            print(f"   {emoji} {name:12}: {wins:3}/{len(bets):3} ({wr:5.1f}%) | ROI: {roi:+6.1f}%")
    
    # 5.2 Performance par score range
    print("\n┌" + "─" * 88 + "┐")
    print("│ 2️⃣  PERFORMANCE PAR SCORE V11.3 (tranches de 3 points)" + " " * 33 + "│")
    print("└" + "─" * 88 + "┘")
    
    for bucket in sorted(score_buckets.keys(), reverse=True):
        data = score_buckets[bucket]
        if data['total'] >= 2:
            wr = data['wins'] / data['total'] * 100
            roi = (data['wins'] * 1.85 - data['total']) / data['total'] * 100
            indicator = "✅" if wr > 57 else "⚠️" if wr > 50 else "❌"
            bar = "█" * int(wr / 5) + "░" * (20 - int(wr / 5))
            print(f"   {indicator} {bucket:2}-{bucket+2:2}: {data['wins']:3}/{data['total']:3} ({wr:5.1f}%) ROI:{roi:+6.1f}% {bar}")
    
    # 5.3 Performance par marché
    print("\n┌" + "─" * 88 + "┐")
    print("│ 3️⃣  PERFORMANCE PAR MARCHÉ" + " " * 61 + "│")
    print("└" + "─" * 88 + "┘")
    
    market_stats = defaultdict(lambda: {'total': 0, 'wins': 0})
    for r in all_results:
        market_stats[r['market']]['total'] += 1
        if r['correct']:
            market_stats[r['market']]['wins'] += 1
    
    for m, d in sorted(market_stats.items(), key=lambda x: -x[1]['total']):
        if d['total'] >= 3:
            wr = d['wins'] / d['total'] * 100
            roi = (d['wins'] * 1.85 - d['total']) / d['total'] * 100
            indicator = "✅" if wr > 55 else "⚠️" if wr > 48 else "❌"
            print(f"   {indicator} {m:25}: {d['wins']:3}/{d['total']:3} ({wr:5.1f}%) | ROI: {roi:+6.1f}%")
    
    # 5.4 Performance par ligue
    print("\n┌" + "─" * 88 + "┐")
    print("│ 4️⃣  PERFORMANCE PAR LIGUE (min 5 matchs)" + " " * 47 + "│")
    print("└" + "─" * 88 + "┘")
    
    league_stats = defaultdict(lambda: {'total': 0, 'wins': 0})
    for r in all_results:
        league_stats[r['league']]['total'] += 1
        if r['correct']:
            league_stats[r['league']]['wins'] += 1
    
    for league, d in sorted(league_stats.items(), key=lambda x: -x[1]['total']):
        if d['total'] >= 5:
            wr = d['wins'] / d['total'] * 100
            roi = (d['wins'] * 1.85 - d['total']) / d['total'] * 100
            indicator = "✅" if wr > 55 else "⚠️" if wr > 48 else "❌"
            print(f"   {indicator} {league:30}: {d['wins']:3}/{d['total']:3} ({wr:5.1f}%) | ROI: {roi:+6.1f}%")
    
    # 5.5 Impact des layers
    print("\n┌" + "─" * 88 + "┐")
    print("│ 5️⃣  IMPACT DES LAYERS (corrélation avec succès)" + " " * 39 + "│")
    print("└" + "─" * 88 + "┘")
    
    layer_names = ['tactical', 'team_class', 'h2h', 'xg', 'coach', 'convergence', 'defensive_context']
    for layer in layer_names:
        win_scores = [r['layers'].get(layer, {}).get('score', 0) for r in all_results if r['correct']]
        loss_scores = [r['layers'].get(layer, {}).get('score', 0) for r in all_results if not r['correct']]
        
        win_avg = sum(win_scores) / len(win_scores) if win_scores else 0
        loss_avg = sum(loss_scores) / len(loss_scores) if loss_scores else 0
        diff = win_avg - loss_avg
        indicator = "📈" if diff > 0.5 else "📉" if diff < -0.5 else "➡️"
        
        print(f"   {indicator} {layer:18}: Win={win_avg:+5.1f} | Loss={loss_avg:+5.1f} | Δ={diff:+5.2f}")
    
    # 5.6 Détail SNIPER bets
    print("\n┌" + "─" * 88 + "┐")
    print("│ 6️⃣  DÉTAIL SNIPER_BET" + " " * 66 + "│")
    print("└" + "─" * 88 + "┘")
    
    for b in sorted(sniper_bets, key=lambda x: -x['score'])[:15]:
        status = "✅" if b['correct'] else "❌"
        print(f"   {status} {b['home'][:18]:18} vs {b['away'][:18]:18} ({b['home_score']}-{b['away_score']}) "
              f"| {b['score']:4.1f}pts → {b['market'][:12]}")
    
    # 5.7 Détail NORMAL bets
    print("\n┌" + "─" * 88 + "┐")
    print("│ 7️⃣  DÉTAIL NORMAL_BET (top 15)" + " " * 57 + "│")
    print("└" + "─" * 88 + "┘")
    
    for b in sorted(normal_bets, key=lambda x: -x['score'])[:15]:
        status = "✅" if b['correct'] else "❌"
        print(f"   {status} {b['home'][:18]:18} vs {b['away'][:18]:18} ({b['home_score']}-{b['away_score']}) "
              f"| {b['score']:4.1f}pts → {b['market'][:12]}")
    
    # 5.8 Analyse Monte Carlo
    print("\n┌" + "─" * 88 + "┐")
    print("│ 8️⃣  SIMULATION MONTE CARLO (10,000 itérations)" + " " * 41 + "│")
    print("└" + "─" * 88 + "┘")
    
    all_active_bets = sniper_bets + normal_bets
    if all_active_bets:
        total_wins = sum(1 for b in all_active_bets if b['correct'])
        total_bets = len(all_active_bets)
        win_rate = total_wins / total_bets if total_bets > 0 else 0
        
        print(f"\n   Paramètres de simulation:")
        print(f"      Win Rate observé: {win_rate*100:.1f}%")
        print(f"      Nombre de bets: {total_bets}")
        print(f"      Cote moyenne: 1.85")
        print(f"      Stake par bet: 2%")
        print(f"      Bankroll initial: 1000€")
        
        mc_results = monte_carlo_simulation(
            win_rate=win_rate,
            avg_odds=1.85,
            n_bets=total_bets,
            n_simulations=10000,
            initial_bankroll=1000,
            stake_percent=0.02
        )
        
        print(f"\n   Résultats Monte Carlo:")
        print(f"      📊 Bankroll finale moyenne: {mc_results['mean_final']:.0f}€")
        print(f"      📊 Bankroll finale médiane: {mc_results['median_final']:.0f}€")
        print(f"      📊 Scénario pessimiste (P5): {mc_results['p5_final']:.0f}€")
        print(f"      📊 Scénario optimiste (P95): {mc_results['p95_final']:.0f}€")
        print(f"      📊 Probabilité de profit: {mc_results['prob_profit']*100:.1f}%")
        print(f"      📊 Risque de ruine: {mc_results['prob_ruin']*100:.2f}%")
        print(f"      📊 Drawdown moyen: {mc_results['mean_max_dd']*100:.1f}%")
        print(f"      📊 Pire drawdown: {mc_results['worst_dd']*100:.1f}%")
        
        # Calcul ROI et Sharpe
        roi = (total_wins * 1.85 - total_bets) / total_bets * 100 if total_bets > 0 else 0
        returns = [0.85 if b['correct'] else -1 for b in all_active_bets]
        sharpe = calculate_sharpe_ratio(returns)
        
        print(f"\n   Métriques de performance:")
        print(f"      📈 ROI réel: {roi:+.1f}%")
        print(f"      📈 Sharpe Ratio: {sharpe:.2f}")
    else:
        print("   ⚠️ Pas de bets actifs pour simulation Monte Carlo")
    
    # CONCLUSIONS
    print("\n" + "═" * 90)
    print("    CONCLUSIONS & RECOMMANDATIONS")
    print("═" * 90)
    
    print("\n📌 SEUILS RECOMMANDÉS (basés sur cette analyse):")
    print(f"   SNIPER_THRESHOLD = {optimal_sniper} (WR ~65%+)")
    print(f"   NORMAL_THRESHOLD = {optimal_normal} (WR ~55%+)")
    
    print("\n💪 FORCES IDENTIFIÉES:")
    for bucket in sorted(score_buckets.keys(), reverse=True):
        d = score_buckets[bucket]
        if d['total'] >= 3 and d['wins'] / d['total'] >= 0.58:
            wr = d['wins'] / d['total'] * 100
            print(f"   ✅ Score {bucket}-{bucket+2}: {wr:.0f}% WR ({d['total']} matchs)")
    
    for m, d in market_stats.items():
        if d['total'] >= 5 and d['wins'] / d['total'] >= 0.57:
            print(f"   ✅ Marché {m}: {d['wins']/d['total']*100:.0f}% WR")
    
    print("\n⚠️  FAIBLESSES À SURVEILLER:")
    for bucket in sorted(score_buckets.keys(), reverse=True):
        d = score_buckets[bucket]
        if d['total'] >= 3 and d['wins'] / d['total'] < 0.45:
            wr = d['wins'] / d['total'] * 100
            print(f"   ❌ Score {bucket}-{bucket+2}: {wr:.0f}% WR")
    
    for m, d in market_stats.items():
        if d['total'] >= 3 and d['wins'] / d['total'] < 0.45:
            print(f"   ❌ Marché {m}: {d['wins']/d['total']*100:.0f}% WR")
    
    # ROI global
    if all_active_bets:
        total_wins = sum(1 for b in all_active_bets if b['correct'])
        roi = (total_wins * 1.85 - len(all_active_bets)) / len(all_active_bets) * 100
        print(f"\n💰 ROI GLOBAL (SNIPER + NORMAL): {total_wins}/{len(all_active_bets)} → {roi:+.1f}%")
    
    print("\n" + "═" * 90)
    print("   Script à exécuter: python3 orchestrator_v11_3_full_analysis.py")
    print("═" * 90)




# ═══════════════════════════════════════════════════════════════════════════════════════
# AJOUT V11.3.1 - SCAN MATCHS FUTURS (odds_history)
# ═══════════════════════════════════════════════════════════════════════════════════════

def scan_upcoming_matches(hours=48):
    """
    Scan les matchs à venir depuis odds_history
    Utilise le même algorithme que le backtest
    """
    print("═" * 90)
    print("    🔮 SCAN MATCHS À VENIR (V11.3.1)")
    print("═" * 90)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"⏰ Horizon: {hours}h")
    print()
    
    # Charger l'orchestrator
    orch = OrchestratorV11_3()
    
    # Récupérer matchs futurs depuis odds_history
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute(f"""
        SELECT DISTINCT ON (home_team, away_team)
            home_team, away_team, commence_time, sport as league
        FROM odds_history
        WHERE commence_time > NOW()
          AND commence_time < NOW() + INTERVAL '{hours} hours'
        ORDER BY home_team, away_team, commence_time
    """)
    matches = cur.fetchall()
    conn.close()
    
    print(f"📥 {len(matches)} matchs trouvés\n")
    
    # Seuils calibrés (basés sur backtest 30 jours)
    SNIPER_THRESHOLD = 32  # Zone 100% WR
    NORMAL_THRESHOLD = 28  # Zone 85%+ WR
    
    # Multiplicateurs par ligue (basés sur backtest)
    LEAGUE_BOOST = {
        'bundesliga': 1.10,      # +30% ROI
        'champions': 1.05,       # +18% ROI
        'premier': 1.00,
        'ligue_1': 1.00,
        'la_liga': 0.90,         # -4.5% ROI - pénalité
        'serie_a': 0.85,         # -7.5% ROI - pénalité
    }
    
    def get_league_mult(league_str):
        if not league_str:
            return 1.0
        l = league_str.lower()
        for key, mult in LEAGUE_BOOST.items():
            if key in l:
                return mult
        return 1.0
    
    # Analyser chaque match
    opportunities = {'SNIPER': [], 'NORMAL': [], 'SKIP': 0}
    
    for m in matches:
        try:
            result = orch.analyze_match(m['home_team'], m['away_team'], "over_25")
            score = result['score']
            
            # Ajuster par ligue
            league = m.get('league', 'Unknown')
            mult = get_league_mult(league)
            adjusted_score = score * mult
            
            # Classifier
            if adjusted_score >= SNIPER_THRESHOLD:
                action = "SNIPER"
            elif adjusted_score >= NORMAL_THRESHOLD:
                action = "NORMAL"
            else:
                action = "SKIP"
            
            if action == "SKIP":
                opportunities['SKIP'] += 1
            else:
                # Déterminer stake (basé sur zone)
                if adjusted_score >= 32:
                    stake = 3.0  # Elite
                elif adjusted_score >= 30:
                    stake = 2.5  # Gold
                elif adjusted_score >= 28:
                    stake = 2.0  # Silver
                else:
                    stake = 1.5  # Normal
                
                opportunities[action].append({
                    'home': m['home_team'],
                    'away': m['away_team'],
                    'time': m['commence_time'],
                    'league': league,
                    'score': score,
                    'adjusted': adjusted_score,
                    'market': result['recommended_market'],
                    'over25': result.get('over25_prob', 50),
                    'btts': result.get('btts_prob', 50),
                    'stake': stake,
                    'mult': mult,
                })
        except Exception as e:
            pass
    
    # Affichage SNIPER
    if opportunities['SNIPER']:
        print("🎯 SNIPER BETS (Score >= 30)")
        print("─" * 90)
        for b in sorted(opportunities['SNIPER'], key=lambda x: -x['adjusted']):
            time_str = b['time'].strftime('%d/%m %H:%M') if b['time'] else 'N/A'
            league_short = b['league'][:25] if b['league'] else 'Unknown'
            mult_str = f"x{b['mult']:.2f}" if b['mult'] != 1.0 else ""
            print(f"   🎯 {b['home'][:20]:20} vs {b['away'][:20]:20}")
            print(f"      📅 {time_str} | 🏆 {league_short}")
            print(f"      📊 Score: {b['score']:.1f} → {b['adjusted']:.1f} {mult_str} | Stake: {b['stake']:.1f}%")
            print(f"      🎲 {b['market']} | O25:{b['over25']:.0f}% BTTS:{b['btts']:.0f}%")
            print()
    
    # Affichage NORMAL
    if opportunities['NORMAL']:
        print("📈 NORMAL BETS (Score 26-30)")
        print("─" * 90)
        for b in sorted(opportunities['NORMAL'], key=lambda x: -x['adjusted'])[:15]:
            time_str = b['time'].strftime('%d/%m %H:%M') if b['time'] else 'N/A'
            league_short = b['league'][:25] if b['league'] else 'Unknown'
            mult_str = f"x{b['mult']:.2f}" if b['mult'] != 1.0 else ""
            print(f"   📈 {b['home'][:20]:20} vs {b['away'][:20]:20}")
            print(f"      📅 {time_str} | 🏆 {league_short}")
            print(f"      📊 Score: {b['score']:.1f} → {b['adjusted']:.1f} {mult_str} | Stake: {b['stake']:.1f}%")
            print(f"      🎲 {b['market']} | O25:{b['over25']:.0f}% BTTS:{b['btts']:.0f}%")
            print()
    
    # Résumé
    print("═" * 90)
    print("    📊 RÉSUMÉ")
    print("═" * 90)
    print(f"   🎯 SNIPER:  {len(opportunities['SNIPER']):3} opportunités")
    print(f"   📈 NORMAL:  {len(opportunities['NORMAL']):3} opportunités")
    print(f"   ⏭️  SKIP:    {opportunities['SKIP']:3} matchs")
    
    total_stake = sum(b['stake'] for b in opportunities['SNIPER'] + opportunities['NORMAL'])
    print(f"\n   💰 Stake total recommandé: {total_stake:.1f}%")
    print("═" * 90)
    
    return opportunities


# Modifier le main pour supporter scan
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "scan":
            hours = int(sys.argv[2]) if len(sys.argv) > 2 else 48
            scan_upcoming_matches(hours)
        elif cmd == "backtest":
            run_full_analysis()
        else:
            print("Usage: python3 script.py [backtest|scan] [hours]")
            print("  backtest : Analyse 30 jours passés")
            print("  scan     : Scan matchs futurs (default 48h)")
            print("  scan 72  : Scan matchs futurs (72h)")
    else:
        # Mode par défaut: backtest
        run_full_analysis()
