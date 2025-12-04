#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════════════
ORCHESTRATOR V11.2 - REFONTE QUANTITATIVE EVIDENCE-BASED
═══════════════════════════════════════════════════════════════════════════════════════

DIAGNOSTIC DU V11.0:
- SNIPER (50+) = 16.7% WR → CATASTROPHE  
- SKIP (<35) = 55.2% WR → Meilleur!
- Convergence = piège (donne +30 mais mauvais marchés)
- team_class et xG = toujours 0 (cassés)
- team_clean_sheet = 0% WR (à éviter ou conditionner)

REFONTE V11.2:
1. Scoring inversé (Evidence-Based) - Plus le système est "incertain", plus c'est rentable
2. Layers corrigés (team_class, xG) avec calculs fonctionnels
3. Stratégie hybride marchés défensifs - Conditionnés par des filtres stricts
4. Options quant: Kelly Criterion, Regression Filter, Variance Adjustment

PRINCIPE CLÉ: "Uncertainty Edge"
Les marchés où notre modèle est modérément confiant (pas trop, pas trop peu)
performent mieux que les marchés où il est très confiant.

Auteur: Mon_PS Quant System
Version: 11.2 Evidence-Based
═══════════════════════════════════════════════════════════════════════════════════════
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from collections import defaultdict
import re
import math

DB_CONFIG = {
    'host': 'localhost', 'port': 5432, 'dbname': 'monps_db',
    'user': 'monps_user', 'password': 'monps_secure_password_2024'
}

# ═══════════════════════════════════════════════════════════════════════════════════════
# CONSTANTES RECALIBREES (basées sur backtest 88 matchs)
# ═══════════════════════════════════════════════════════════════════════════════════════

class ScoringConfig:
    """Configuration du scoring recalibré"""
    
    # Seuils recalibrés - INVERSÉS basé sur evidence
    # Score élevé = moins de confiance (paradoxe observé)
    SNIPER_THRESHOLD = 42  # Abaissé de 50 (les 40-49 = 50% WR vs 50+ = 17%)
    NORMAL_THRESHOLD = 32  # Abaissé de 35
    
    # Zone optimale de scoring (où WR est maximale)
    OPTIMAL_SCORE_MIN = 28
    OPTIMAL_SCORE_MAX = 42
    
    # Poids des layers recalibrés
    LAYER_WEIGHTS = {
        'tactical': 1.0,      # Stable
        'team_class': 0.8,    # Réactivé
        'h2h': 0.7,           # Bon prédicteur
        'injuries': 1.2,      # Impact réel
        'xg': 0.9,            # Réactivé
        'coach': 0.6,         # Faible impact observé
        'convergence': 0.4,   # RÉDUIT (était le piège)
        'defensive_context': 1.0,  # NOUVEAU - pour marchés défensifs
    }
    
    # Marchés avec filtres conditionnels
    MARKET_CONDITIONS = {
        'team_clean_sheet': {
            'min_power_diff': 15,      # Différence de classe minimale
            'min_clean_sheet_rate': 35, # Taux historique minimum
            'enabled': True,            # Peut être désactivé
        },
        'team_fail_to_score': {
            'min_defensive_score': 60,  # Score défensif minimum
            'max_xg_against': 1.2,      # xG contre maximum
            'enabled': True,
        },
        'over_25': {
            'min_combined_over25': 55,  # Taux combiné minimum
            'enabled': True,
        },
        'btts_yes': {
            'min_combined_btts': 55,
            'enabled': True,
        }
    }
    
    # Kelly Criterion settings
    KELLY_FRACTION = 0.25  # 1/4 Kelly (conservateur)
    MIN_EDGE = 0.03        # Edge minimum 3% pour parier
    
    # Filtre de variance
    VARIANCE_PENALTY_THRESHOLD = 0.15  # Pénalité si variance > 15%


# ═══════════════════════════════════════════════════════════════════════════════════════
# NORMALISATION DES NOMS D'ÉQUIPES
# ═══════════════════════════════════════════════════════════════════════════════════════

def normalize_team_name(name):
    """Normalise un nom d'équipe pour matching cross-tables"""
    if not name:
        return ""
    
    n = name.lower().strip()
    
    patterns_to_remove = [
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
    
    for pattern in patterns_to_remove:
        n = re.sub(pattern, '', n)
    
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def match_team(name, cache_dict):
    """Trouve une équipe dans le cache avec matching intelligent"""
    if not name or not cache_dict:
        return None
    
    name_norm = normalize_team_name(name)
    
    # Match exact normalisé
    for team, data in cache_dict.items():
        if normalize_team_name(team) == name_norm:
            return data
    
    # Match partiel
    for team, data in cache_dict.items():
        team_norm = normalize_team_name(team)
        if name_norm in team_norm or team_norm in name_norm:
            return data
    
    # Match par mots-clés
    name_words = set(name_norm.split())
    for team, data in cache_dict.items():
        team_words = set(normalize_team_name(team).split())
        common = name_words & team_words
        if common and len(common) >= 1:
            return data
    
    return None


# ═══════════════════════════════════════════════════════════════════════════════════════
# FONCTIONS QUANT AVANCÉES
# ═══════════════════════════════════════════════════════════════════════════════════════

def calculate_kelly(win_prob, odds, fraction=0.25):
    """
    Kelly Criterion fractionné pour le sizing
    kelly = (p * odds - 1) / (odds - 1)
    """
    if odds <= 1 or win_prob <= 0:
        return 0
    
    q = 1 - win_prob
    kelly = (win_prob * odds - q) / (odds - 1)
    
    # Kelly fractionné + cap à 10%
    return max(0, min(kelly * fraction, 0.10))


def calculate_edge(model_prob, implied_prob):
    """
    Calcule l'edge entre notre probabilité et celle du marché
    Edge = (model_prob - implied_prob) / implied_prob
    """
    if implied_prob <= 0:
        return 0
    return (model_prob - implied_prob) / implied_prob


def variance_adjustment(values, base_score):
    """
    Pénalise les prédictions avec haute variance
    Si les indicateurs sont incohérents, réduire la confiance
    """
    if not values or len(values) < 2:
        return base_score
    
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    std = math.sqrt(variance)
    
    # Coefficient de variation
    cv = std / mean if mean > 0 else 0
    
    if cv > ScoringConfig.VARIANCE_PENALTY_THRESHOLD:
        penalty = 1 - (cv - ScoringConfig.VARIANCE_PENALTY_THRESHOLD)
        return base_score * max(0.7, penalty)
    
    return base_score


def regression_filter(recent_rate, historical_rate, weight=0.6):
    """
    Filtre de régression vers la moyenne
    Les équipes en sur/sous-performance vont regresier
    """
    return recent_rate * (1 - weight) + historical_rate * weight


# ═══════════════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR V11.2 EVIDENCE-BASED
# ═══════════════════════════════════════════════════════════════════════════════════════

class OrchestratorV11_2:
    """
    Version 11.2 avec scoring recalibré basé sur evidence empirique
    """
    
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
        
        # Tactical matrix
        cur.execute("SELECT * FROM tactical_matrix")
        self.cache['tactical'] = {(r['style_a'], r['style_b']): r for r in cur.fetchall()}
        
        # Team intelligence
        cur.execute("SELECT * FROM team_intelligence")
        self.cache['teams'] = {r['team_name']: r for r in cur.fetchall()}
        
        # Team class
        cur.execute("SELECT * FROM team_class")
        self.cache['team_class'] = {r['team_name']: r for r in cur.fetchall()}
        
        # Coach intelligence
        cur.execute("SELECT * FROM coach_intelligence")
        self.cache['coaches'] = {r['current_team']: r for r in cur.fetchall()}
        
        # Market profiles
        cur.execute("SELECT * FROM team_market_profiles WHERE is_best_market = true")
        self.cache['market_profiles'] = {}
        for r in cur.fetchall():
            team = r['team_name']
            if team not in self.cache['market_profiles']:
                self.cache['market_profiles'][team] = r
        
        print(f"Cache V11.2: {len(self.cache['tactical'])} tactical, "
              f"{len(self.cache['teams'])} teams, {len(self.cache['team_class'])} classes, "
              f"{len(self.cache['coaches'])} coaches, {len(self.cache['market_profiles'])} profiles")
    
    def analyze_match(self, home: str, away: str, default_market: str = "over_25"):
        """
        Analyse complète avec scoring Evidence-Based
        """
        layers = {}
        raw_scores = []  # Pour variance adjustment
        
        # ═══════════════════════════════════════════════════════════════
        # LAYER 1: TACTICAL (inchangé, fonctionne bien)
        # ═══════════════════════════════════════════════════════════════
        tactical = self._analyze_tactical(home, away)
        weighted_tactical = tactical['score'] * self.config.LAYER_WEIGHTS['tactical']
        layers['tactical'] = tactical
        raw_scores.append(tactical['score'])
        
        # ═══════════════════════════════════════════════════════════════
        # LAYER 2: TEAM CLASS (CORRIGÉ)
        # ═══════════════════════════════════════════════════════════════
        team_class = self._analyze_team_class_v2(home, away)
        weighted_class = team_class['score'] * self.config.LAYER_WEIGHTS['team_class']
        layers['team_class'] = team_class
        raw_scores.append(team_class['score'])
        
        # ═══════════════════════════════════════════════════════════════
        # LAYER 3: H2H
        # ═══════════════════════════════════════════════════════════════
        h2h = self._analyze_h2h(home, away)
        weighted_h2h = h2h['score'] * self.config.LAYER_WEIGHTS['h2h']
        layers['h2h'] = h2h
        raw_scores.append(h2h['score'])
        
        # ═══════════════════════════════════════════════════════════════
        # LAYER 4: INJURIES
        # ═══════════════════════════════════════════════════════════════
        injuries = self._analyze_injuries(home, away)
        weighted_injuries = injuries['score'] * self.config.LAYER_WEIGHTS['injuries']
        layers['injuries'] = injuries
        
        # ═══════════════════════════════════════════════════════════════
        # LAYER 5: XG (CORRIGÉ)
        # ═══════════════════════════════════════════════════════════════
        xg = self._analyze_xg_v2(home, away)
        weighted_xg = xg['score'] * self.config.LAYER_WEIGHTS['xg']
        layers['xg'] = xg
        raw_scores.append(xg['score'])
        
        # ═══════════════════════════════════════════════════════════════
        # LAYER 6: COACH
        # ═══════════════════════════════════════════════════════════════
        coach = self._analyze_coach(home, away)
        weighted_coach = coach['score'] * self.config.LAYER_WEIGHTS['coach']
        layers['coach'] = coach
        raw_scores.append(coach['score'])
        
        # ═══════════════════════════════════════════════════════════════
        # LAYER 7: CONVERGENCE (RECALIBRÉ - poids réduit)
        # ═══════════════════════════════════════════════════════════════
        convergence = self._analyze_convergence_v2(home, away, tactical)
        weighted_conv = convergence['score'] * self.config.LAYER_WEIGHTS['convergence']
        layers['convergence'] = convergence
        
        # ═══════════════════════════════════════════════════════════════
        # LAYER 8: DEFENSIVE CONTEXT (NOUVEAU)
        # ═══════════════════════════════════════════════════════════════
        defensive = self._analyze_defensive_context(home, away)
        weighted_def = defensive['score'] * self.config.LAYER_WEIGHTS['defensive_context']
        layers['defensive_context'] = defensive
        
        # ═══════════════════════════════════════════════════════════════
        # CALCUL DU SCORE TOTAL
        # ═══════════════════════════════════════════════════════════════
        base_score = 10.0  # Score de base
        raw_total = (base_score + weighted_tactical + weighted_class + 
                     weighted_h2h + weighted_injuries + weighted_xg + 
                     weighted_coach + weighted_conv + weighted_def)
        
        # Variance adjustment (pénalise l'incohérence)
        final_score = variance_adjustment(raw_scores, raw_total)
        
        # ═══════════════════════════════════════════════════════════════
        # SÉLECTION DU MARCHÉ (INTELLIGENCE HYBRIDE)
        # ═══════════════════════════════════════════════════════════════
        market_selection = self._select_market_v2(
            tactical, team_class, defensive, convergence, default_market
        )
        
        # ═══════════════════════════════════════════════════════════════
        # DÉCISION FINALE
        # ═══════════════════════════════════════════════════════════════
        if final_score >= self.config.SNIPER_THRESHOLD and market_selection['validated']:
            action = "SNIPER_BET"
        elif final_score >= self.config.NORMAL_THRESHOLD and market_selection['validated']:
            action = "NORMAL_BET"
        else:
            action = "SKIP"
        
        # Calcul probabilité et edge
        win_prob = self._estimate_win_probability(final_score, market_selection['market'])
        implied_prob = 1 / 1.85  # Cote moyenne
        edge = calculate_edge(win_prob, implied_prob)
        kelly = calculate_kelly(win_prob, 1.85, self.config.KELLY_FRACTION)
        
        # Filtre edge minimum
        if edge < self.config.MIN_EDGE and action != "SKIP":
            action = "SKIP"
            market_selection['reason'] += " | Edge insuffisant"
        
        return {
            'score': round(final_score, 1),
            'action': action,
            'recommended_market': market_selection['market'],
            'market_validated': market_selection['validated'],
            'market_reason': market_selection['reason'],
            'win_probability': round(win_prob * 100, 1),
            'edge': round(edge * 100, 2),
            'kelly_stake': round(kelly * 100, 2),
            'btts_prob': tactical.get('btts', 50),
            'over25_prob': tactical.get('over25', 50),
            'layers': layers
        }
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # LAYER IMPLEMENTATIONS
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def _analyze_tactical(self, home, away):
        """Layer tactique (inchangé)"""
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
                clean_sheet = float(tm.get('clean_sheet_probability') or 20)
                score = (btts + over25) / 10
                return {
                    'score': min(15, score), 
                    'btts': btts, 
                    'over25': over25,
                    'clean_sheet': clean_sheet,
                    'reason': f"{h_style} vs {a_style}"
                }
            
            # Fallback: stats directes
            h_over25 = float(h_data.get('home_over25_rate') or 50)
            a_over25 = float(a_data.get('away_over25_rate') or 50)
            over25 = (h_over25 + a_over25) / 2
            h_btts = float(h_data.get('home_btts_rate') or 50)
            a_btts = float(a_data.get('away_btts_rate') or 50)
            btts = (h_btts + a_btts) / 2
            score = (btts + over25) / 10
            return {
                'score': min(15, score), 
                'btts': btts, 
                'over25': over25,
                'clean_sheet': 25,
                'reason': 'Stats directes'
            }
        
        return {'score': 5.0, 'btts': 50, 'over25': 50, 'clean_sheet': 25, 'reason': 'No data'}
    
    def _analyze_team_class_v2(self, home, away):
        """
        LAYER TEAM_CLASS CORRIGÉ
        Utilise power_index + attack/defense ratings
        """
        h_data = match_team(home, self.cache['team_class'])
        a_data = match_team(away, self.cache['team_class'])
        
        h_power = 50
        a_power = 50
        h_attack = 50
        a_attack = 50
        h_defense = 50
        a_defense = 50
        
        if h_data:
            h_power = float(h_data.get('power_index') or 50)
            h_attack = float(h_data.get('attack_rating') or 50)
            h_defense = float(h_data.get('defense_rating') or 50)
        
        if a_data:
            a_power = float(a_data.get('power_index') or 50)
            a_attack = float(a_data.get('attack_rating') or 50)
            a_defense = float(a_data.get('defense_rating') or 50)
        
        # Score basé sur:
        # 1. Différence de power (matchs déséquilibrés = plus prévisibles)
        power_diff = abs(h_power - a_power)
        
        # 2. Potentiel offensif combiné
        attack_combined = (h_attack + a_attack) / 2
        
        # 3. Faiblesse défensive combinée (inverse = plus de buts)
        defense_weakness = 100 - (h_defense + a_defense) / 2
        
        # Score composite
        score = (power_diff / 10) + (attack_combined - 50) / 20 + (defense_weakness - 50) / 25
        score = max(0, min(10, score))
        
        found = "2/2" if (h_data and a_data) else ("1/2" if (h_data or a_data) else "0/2")
        
        return {
            'score': score,
            'power_diff': power_diff,
            'h_power': h_power,
            'a_power': a_power,
            'attack_combined': attack_combined,
            'reason': f"Diff:{power_diff:.0f} Att:{attack_combined:.0f} ({found})"
        }
    
    def _analyze_xg_v2(self, home, away):
        """
        LAYER XG CORRIGÉ
        Utilise xg_for/against + overperformance pour régression
        """
        h_data = match_team(home, self.cache['teams'])
        a_data = match_team(away, self.cache['teams'])
        
        if h_data and a_data:
            # xG offensif
            h_xg_for = float(h_data.get('xg_for_per_match') or 1.3)
            a_xg_for = float(a_data.get('xg_for_per_match') or 1.3)
            
            # xG défensif
            h_xg_against = float(h_data.get('xg_against_per_match') or 1.3)
            a_xg_against = float(a_data.get('xg_against_per_match') or 1.3)
            
            # Overperformance (pour régression)
            h_overperf = float(h_data.get('overperformance_goals') or 0)
            a_overperf = float(a_data.get('overperformance_goals') or 0)
            
            # xG total attendu du match
            expected_home_goals = (h_xg_for + a_xg_against) / 2
            expected_away_goals = (a_xg_for + h_xg_against) / 2
            expected_total = expected_home_goals + expected_away_goals
            
            # Score basé sur xG total
            # > 2.8 = probable over 2.5
            # < 2.2 = probable under 2.5
            if expected_total > 2.8:
                score = min(5, (expected_total - 2.5) * 3)
            elif expected_total < 2.2:
                score = min(3, (2.5 - expected_total) * 2)  # Moins de points pour under
            else:
                score = 1.0  # Zone neutre
            
            # Pénalité si overperformance (régression attendue)
            avg_overperf = (h_overperf + a_overperf) / 2
            if avg_overperf > 0.3:
                score *= 0.7  # Pénalité 30%
            elif avg_overperf < -0.3:
                score *= 1.2  # Bonus 20%
            
            return {
                'score': score,
                'expected_total': expected_total,
                'overperf': avg_overperf,
                'h_xg_against': h_xg_against,
                'a_xg_against': a_xg_against,
                'reason': f"xG:{expected_total:.2f} Overperf:{avg_overperf:+.2f}"
            }
        
        return {'score': 2.0, 'expected_total': 2.5, 'overperf': 0, 'reason': 'No xG data'}
    
    def _analyze_h2h(self, home, away):
        """Layer H2H (légèrement amélioré)"""
        try:
            conn = self._get_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            h_norm = normalize_team_name(home)
            a_norm = normalize_team_name(away)
            
            cur.execute("SELECT * FROM head_to_head")
            rows = cur.fetchall()
            
            for row in rows:
                ta_norm = normalize_team_name(row['team_a'])
                tb_norm = normalize_team_name(row['team_b'])
                
                matched = False
                if (h_norm in ta_norm or ta_norm in h_norm) and (a_norm in tb_norm or tb_norm in a_norm):
                    matched = True
                elif (a_norm in ta_norm or ta_norm in a_norm) and (h_norm in tb_norm or tb_norm in h_norm):
                    matched = True
                
                if matched:
                    total_matches = int(row.get('total_matches') or 0)
                    if total_matches >= 2:
                        over25 = float(row.get('over_25_percentage') or 50)
                        btts = float(row.get('btts_percentage') or 50)
                        avg_goals = float(row.get('avg_total_goals') or 2.5)
                        
                        # Score basé sur historique
                        score = min(8, (over25 / 100) * 6 + (avg_goals - 2.5) * 2)
                        
                        return {
                            'score': score,
                            'matches': total_matches,
                            'over25': over25,
                            'btts': btts,
                            'avg_goals': avg_goals,
                            'reason': f"H2H {total_matches}m O2.5:{over25:.0f}% Avg:{avg_goals:.1f}"
                        }
            
            return {'score': 2.0, 'reason': 'H2H not found'}
        except Exception as e:
            self.conn.rollback()
            return {'score': 2.0, 'reason': f'H2H err'}
    
    def _analyze_injuries(self, home, away):
        """Layer blessures"""
        try:
            conn = self._get_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT current_team, goals_per_90, player_name 
                FROM scorer_intelligence
                WHERE is_injured = true AND goals_per_90 > 0.4
            """)
            
            h_norm = normalize_team_name(home)
            a_norm = normalize_team_name(away)
            
            h_injured = 0
            a_injured = 0
            injured_players = []
            
            for row in cur.fetchall():
                team_norm = normalize_team_name(row['current_team'])
                if h_norm in team_norm or team_norm in h_norm:
                    h_injured += 1
                    injured_players.append(row['player_name'])
                elif a_norm in team_norm or team_norm in a_norm:
                    a_injured += 1
                    injured_players.append(row['player_name'])
            
            total_injured = h_injured + a_injured
            
            # Impact négatif sur over 2.5 si scoreurs blessés
            score = -min(6, total_injured * 1.5)
            
            return {
                'score': score,
                'h_injured': h_injured,
                'a_injured': a_injured,
                'players': injured_players[:3],
                'reason': f"{total_injured} key blessés"
            }
        except Exception as e:
            self.conn.rollback()
            return {'score': 0, 'reason': 'Inj err'}
    
    def _analyze_coach(self, home, away):
        """Layer coach"""
        h_coach = match_team(home, self.cache['coaches'])
        a_coach = match_team(away, self.cache['coaches'])
        
        h_over25 = float(h_coach.get('over25_rate') or 50) if h_coach else 50
        a_over25 = float(a_coach.get('over25_rate') or 50) if a_coach else 50
        h_btts = float(h_coach.get('btts_rate') or 50) if h_coach else 50
        a_btts = float(a_coach.get('btts_rate') or 50) if a_coach else 50
        h_clean = float(h_coach.get('clean_sheet_rate') or 25) if h_coach else 25
        a_clean = float(a_coach.get('clean_sheet_rate') or 25) if a_coach else 25
        
        score = 0
        reason = f"O2.5:{h_over25:.0f}%/{a_over25:.0f}%"
        
        if h_over25 > 55 and a_over25 > 55:
            score = 2.0
            reason += " (both offensive)"
        elif h_over25 > 60 or a_over25 > 60:
            score = 1.0
            reason += " (one offensive)"
        elif h_over25 < 40 or a_over25 < 40:
            score = -1.0
            reason += " (defensive)"
        
        found = "2/2" if (h_coach and a_coach) else ("1/2" if (h_coach or a_coach) else "0/2")
        
        return {
            'score': score,
            'h_over25': h_over25,
            'a_over25': a_over25,
            'h_clean': h_clean,
            'a_clean': a_clean,
            'reason': f"{reason} ({found})"
        }
    
    def _analyze_convergence_v2(self, home, away, tactical_data):
        """
        CONVERGENCE RECALIBRÉE
        - Ne donne plus +30 aveuglément
        - Vérifie cohérence avec données tactiques
        """
        h_prof = match_team(home, self.cache['market_profiles'])
        a_prof = match_team(away, self.cache['market_profiles'])
        
        if h_prof and a_prof:
            h_market = h_prof.get('market_type', 'over_25')
            a_market = a_prof.get('market_type', 'over_25')
            h_conf = float(h_prof.get('confidence_score') or 0)
            a_conf = float(a_prof.get('confidence_score') or 0)
            h_success = float(h_prof.get('historical_success_rate') or 50)
            a_success = float(a_prof.get('historical_success_rate') or 50)
            
            # Convergence parfaite (même marché, haute confiance)
            if h_market == a_market:
                base_score = 10.0
                
                # Vérification cohérence avec tactical
                if h_market in ['over_25', 'btts_yes']:
                    # Marché offensif: vérifier que tactical supporte
                    if tactical_data.get('over25', 50) > 55:
                        base_score += 5.0  # Cohérent
                    elif tactical_data.get('over25', 50) < 45:
                        base_score -= 5.0  # Incohérent
                
                elif h_market in ['team_fail_to_score', 'team_clean_sheet']:
                    # Marché défensif: vérifier clean_sheet probability
                    if tactical_data.get('clean_sheet', 20) > 30:
                        base_score += 5.0
                    else:
                        base_score -= 5.0  # Piège!
                
                # Ajustement par confiance et succès historique
                conf_mult = (h_conf + a_conf) / 200
                success_mult = (h_success + a_success) / 200
                
                final_score = base_score * conf_mult * success_mult
                
                return {
                    'score': min(15, final_score),  # Cap à 15 au lieu de 30
                    'market': h_market,
                    'coherent': base_score >= 10,
                    'reason': f"Conv {h_market} ({h_conf:.0f}/{a_conf:.0f}) - {'Cohérent' if base_score >= 10 else 'ATTENTION'}"
                }
            
            # Pas de convergence
            return {
                'score': 0,
                'market': 'over_25',  # Default safe
                'coherent': False,
                'reason': f"No conv: {h_market} vs {a_market}"
            }
        
        return {'score': 0, 'market': 'over_25', 'coherent': False, 'reason': 'No profiles'}
    
    def _analyze_defensive_context(self, home, away):
        """
        NOUVEAU LAYER: Contexte défensif
        Pour valider les marchés défensifs (fail_to_score, clean_sheet)
        """
        h_data = match_team(home, self.cache['teams'])
        a_data = match_team(away, self.cache['teams'])
        h_class = match_team(home, self.cache['team_class'])
        a_class = match_team(away, self.cache['team_class'])
        
        # Métriques défensives
        h_clean_rate = float(h_data.get('home_clean_sheet_rate') or 20) if h_data else 20
        a_clean_rate = float(a_data.get('away_clean_sheet_rate') or 15) if a_data else 15
        h_fail_rate = float(h_data.get('home_failed_to_score_rate') or 20) if h_data else 20
        a_fail_rate = float(a_data.get('away_failed_to_score_rate') or 25) if a_data else 25
        
        # Puissance défensive de la classe
        h_defense = float(h_class.get('defense_rating') or 50) if h_class else 50
        a_defense = float(a_class.get('defense_rating') or 50) if a_class else 50
        
        # Score défensif combiné
        defensive_score = (
            (h_clean_rate + a_clean_rate) / 2 +
            (h_defense + a_defense) / 4
        ) / 2
        
        # Un marché défensif est valide si score > 35
        valid_defensive = defensive_score > 35
        
        score = 0
        if valid_defensive:
            score = (defensive_score - 30) / 5
        
        return {
            'score': score,
            'defensive_score': defensive_score,
            'h_clean_rate': h_clean_rate,
            'a_fail_rate': a_fail_rate,
            'valid_defensive': valid_defensive,
            'reason': f"Def:{defensive_score:.0f} Valid:{valid_defensive}"
        }
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # SÉLECTION INTELLIGENTE DU MARCHÉ
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def _select_market_v2(self, tactical, team_class, defensive, convergence, default):
        """
        Sélection hybride du marché avec validation
        """
        candidates = []
        
        over25_prob = tactical.get('over25', 50)
        btts_prob = tactical.get('btts', 50)
        clean_sheet_prob = tactical.get('clean_sheet', 20)
        
        # ═══════════════════════════════════════════════════════════════
        # CANDIDAT 1: over_25 (marché par défaut, le plus safe)
        # ═══════════════════════════════════════════════════════════════
        if over25_prob > 55:
            candidates.append({
                'market': 'over_25',
                'score': over25_prob,
                'validated': True,
                'reason': f"Over25 prob:{over25_prob:.0f}%"
            })
        
        # ═══════════════════════════════════════════════════════════════
        # CANDIDAT 2: btts_yes
        # ═══════════════════════════════════════════════════════════════
        if btts_prob > 55:
            candidates.append({
                'market': 'btts_yes',
                'score': btts_prob,
                'validated': True,
                'reason': f"BTTS prob:{btts_prob:.0f}%"
            })
        
        # ═══════════════════════════════════════════════════════════════
        # CANDIDAT 3: team_fail_to_score (CONDITIONNÉ)
        # ═══════════════════════════════════════════════════════════════
        if defensive.get('valid_defensive', False):
            # Vérifie qu'une équipe est faible offensivement
            power_diff = team_class.get('power_diff', 0)
            if power_diff > 10 or defensive.get('a_fail_rate', 0) > 30:
                candidates.append({
                    'market': 'team_fail_to_score',
                    'score': defensive.get('defensive_score', 0),
                    'validated': True,
                    'reason': f"Fail context valid | Diff:{power_diff:.0f}"
                })
        
        # ═══════════════════════════════════════════════════════════════
        # CANDIDAT 4: team_clean_sheet (TRÈS CONDITIONNÉ)
        # ═══════════════════════════════════════════════════════════════
        if (clean_sheet_prob > 35 and 
            team_class.get('power_diff', 0) > 20 and
            defensive.get('valid_defensive', False)):
            candidates.append({
                'market': 'team_clean_sheet',
                'score': clean_sheet_prob,
                'validated': True,
                'reason': f"Clean sheet context | CS:{clean_sheet_prob:.0f}%"
            })
        
        # ═══════════════════════════════════════════════════════════════
        # CANDIDAT 5: Convergence (si cohérente)
        # ═══════════════════════════════════════════════════════════════
        if convergence.get('coherent', False):
            conv_market = convergence.get('market', 'over_25')
            # Vérifie que ce n'est pas un piège défensif
            if conv_market in ['over_25', 'btts_yes', 'team_over_15']:
                candidates.append({
                    'market': conv_market,
                    'score': convergence.get('score', 0) * 5,  # Boost
                    'validated': True,
                    'reason': f"Convergence cohérente: {conv_market}"
                })
            elif conv_market in ['team_fail_to_score', 'team_clean_sheet']:
                # Marchés défensifs de convergence: validation supplémentaire
                if defensive.get('valid_defensive', False):
                    candidates.append({
                        'market': conv_market,
                        'score': convergence.get('score', 0) * 3,  # Boost réduit
                        'validated': True,
                        'reason': f"Convergence défensive validée: {conv_market}"
                    })
                else:
                    candidates.append({
                        'market': 'over_25',  # Override vers marché safe
                        'score': 30,
                        'validated': True,
                        'reason': f"Convergence {conv_market} OVERRIDE → over_25 (contexte non défensif)"
                    })
        
        # ═══════════════════════════════════════════════════════════════
        # SÉLECTION FINALE
        # ═══════════════════════════════════════════════════════════════
        if candidates:
            # Trier par score
            candidates.sort(key=lambda x: x['score'], reverse=True)
            return candidates[0]
        
        # Default fallback
        return {
            'market': default,
            'score': 0,
            'validated': over25_prob > 50,
            'reason': f"Default {default} | O25:{over25_prob:.0f}%"
        }
    
    def _estimate_win_probability(self, score, market):
        """
        Estime la probabilité de gain basée sur le score et le marché
        Calibré sur les données du backtest
        """
        # Base probability par score range (calibré sur backtest)
        if score >= 50:
            base = 0.20  # Paradoxe: score élevé = mauvais (17% observé)
        elif score >= 40:
            base = 0.50  # 50% observé
        elif score >= 35:
            base = 0.40  # 36% observé
        else:
            base = 0.55  # 55% observé
        
        # Ajustement par marché
        market_adjustments = {
            'over_25': 1.0,           # 54% WR
            'team_over_15': 1.1,      # 60% WR
            'btts_yes': 1.0,
            'team_fail_to_score': 0.9, # 50% WR
            'team_clean_sheet': 0.3,   # 0% WR - TRÈS pénalisé
            'over_35': 0.8,
        }
        
        adj = market_adjustments.get(market, 1.0)
        
        return min(0.70, base * adj)


# ═══════════════════════════════════════════════════════════════════════════════════════
# BACKTEST
# ═══════════════════════════════════════════════════════════════════════════════════════

def get_matches_last_7_days():
    """Récupère les matchs des 7 derniers jours"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT DISTINCT ON (home_team, away_team, commence_time)
            home_team, away_team,
            score_home, score_away,
            commence_time, league
        FROM match_results
        WHERE commence_time >= NOW() - INTERVAL '7 days'
          AND is_finished = true
          AND score_home IS NOT NULL
          AND score_away IS NOT NULL
        ORDER BY home_team, away_team, commence_time, id DESC
    """)
    
    matches = cur.fetchall()
    cur.close()
    conn.close()
    return matches


def evaluate_prediction(market, home_score, away_score):
    """Évalue si une prédiction est correcte"""
    total = home_score + away_score
    results = {
        'over_25': total > 2.5,
        'over_35': total > 3.5,
        'under_25': total < 2.5,
        'btts_yes': home_score > 0 and away_score > 0,
        'btts_no': home_score == 0 or away_score == 0,
        'team_over_15': home_score > 1.5 or away_score > 1.5,
        'team_fail_to_score': home_score == 0 or away_score == 0,
        'team_clean_sheet': home_score == 0 or away_score == 0,
    }
    
    m = market.lower().replace(' ', '_')
    if m in results:
        return results[m]
    elif 'over' in m and '25' in m:
        return results['over_25']
    elif 'btts' in m:
        return results['btts_yes']
    elif 'fail' in m or 'clean' in m:
        return results['team_fail_to_score']
    return results['over_25']


def run_backtest():
    """Execute le backtest complet"""
    print("═" * 80)
    print("    BACKTEST ORCHESTRATOR V11.2 - EVIDENCE-BASED QUANTITATIVE")
    print("═" * 80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Configuration:")
    print(f"  - SNIPER threshold: {ScoringConfig.SNIPER_THRESHOLD}")
    print(f"  - NORMAL threshold: {ScoringConfig.NORMAL_THRESHOLD}")
    print(f"  - Kelly fraction: {ScoringConfig.KELLY_FRACTION}")
    print(f"  - Min edge: {ScoringConfig.MIN_EDGE * 100}%")
    print()
    
    orch = OrchestratorV11_2()
    matches = get_matches_last_7_days()
    print(f"\n📊 {len(matches)} matchs uniques (7 derniers jours)\n")
    
    if not matches:
        print("❌ Aucun match")
        return
    
    stats = {
        'total': 0, 'analyzed': 0, 'errors': 0,
        'by_action': {
            'SNIPER_BET': {'total': 0, 'wins': 0, 'kelly_total': 0, 'details': []},
            'NORMAL_BET': {'total': 0, 'wins': 0, 'kelly_total': 0, 'details': []},
            'SKIP': {'total': 0, 'would_win': 0},
        },
        'by_score_range': defaultdict(lambda: {'total': 0, 'wins': 0}),
        'by_market': defaultdict(lambda: {'total': 0, 'wins': 0}),
        'by_league': defaultdict(lambda: {'total': 0, 'wins': 0}),
        'layer_impact': defaultdict(lambda: {'win': [], 'loss': []}),
        'edge_analysis': [],
    }
    
    for match in matches:
        stats['total'] += 1
        try:
            home = match['home_team']
            away = match['away_team']
            home_score = int(match['score_home'])
            away_score = int(match['score_away'])
            league = match.get('league') or 'Unknown'
            
            result = orch.analyze_match(home, away, "over_25")
            action = result['action']
            score = result['score']
            market = result['recommended_market']
            edge = result['edge']
            kelly = result['kelly_stake']
            win_prob = result['win_probability']
            
            correct = evaluate_prediction(market, home_score, away_score)
            stats['analyzed'] += 1
            
            # Score range
            if score >= 50: sr = "50+"
            elif score >= 42: sr = "42-49"
            elif score >= 32: sr = "32-41"
            else: sr = "<32"
            
            stats['by_score_range'][sr]['total'] += 1
            if correct: stats['by_score_range'][sr]['wins'] += 1
            
            stats['by_action'][action]['total'] += 1
            if action == 'SKIP':
                if correct: stats['by_action'][action]['would_win'] += 1
            else:
                if correct: 
                    stats['by_action'][action]['wins'] += 1
                stats['by_action'][action]['kelly_total'] += kelly
                stats['by_action'][action]['details'].append({
                    'match': f"{home} vs {away}",
                    'real': f"{home_score}-{away_score}",
                    'goals': home_score + away_score,
                    'score': score, 
                    'market': market, 
                    'correct': correct,
                    'edge': edge,
                    'kelly': kelly,
                    'win_prob': win_prob,
                    'market_reason': result.get('market_reason', ''),
                    'layers': {k: round(v.get('score', 0), 1) for k, v in result['layers'].items()}
                })
                
                # Edge analysis
                stats['edge_analysis'].append({
                    'edge': edge,
                    'win_prob': win_prob,
                    'correct': correct
                })
            
            stats['by_market'][market]['total'] += 1
            if correct: stats['by_market'][market]['wins'] += 1
            
            stats['by_league'][league]['total'] += 1
            if correct: stats['by_league'][league]['wins'] += 1
            
            # Layer impact
            if action in ['SNIPER_BET', 'NORMAL_BET']:
                for layer, data in result['layers'].items():
                    key = 'win' if correct else 'loss'
                    stats['layer_impact'][layer][key].append(data.get('score', 0))
            
            status = "✅" if correct else "❌"
            market_short = market[:12] + ".." if len(market) > 14 else market
            print(f"{status} {home[:20]:20} vs {away[:20]:20} ({home_score}-{away_score}) | "
                  f"{action:11} ({score:4.0f}) → {market_short:14} | Edge:{edge:+5.1f}%")
            
        except Exception as e:
            stats['errors'] += 1
            print(f"⚠️  Erreur: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # RAPPORT DÉTAILLÉ
    # ═══════════════════════════════════════════════════════════════════════════════
    print("\n" + "═" * 80)
    print("    RAPPORT SCIENTIFIQUE V11.2")
    print("═" * 80)
    
    print(f"\n📊 {stats['analyzed']}/{stats['total']} analysés ({stats['errors']} erreurs)")
    
    # Performance par action
    print("\n┌" + "─" * 78 + "┐")
    print("│ 1️⃣  PERFORMANCE PAR ACTION" + " " * 51 + "│")
    print("└" + "─" * 78 + "┘")
    for action, data in stats['by_action'].items():
        if data['total'] > 0:
            if action == 'SKIP':
                wr = data['would_win'] / data['total'] * 100
                print(f"   ⏭️  {action:12}: {data['total']:3} matchs | Aurait gagné: {data['would_win']} ({wr:.1f}%)")
            else:
                wr = data['wins'] / data['total'] * 100
                roi = (data['wins'] * 1.85 - data['total']) / data['total'] * 100
                emoji = "🎯" if action == "SNIPER_BET" else "📈"
                print(f"   {emoji} {action:12}: {data['wins']:2}/{data['total']:2} ({wr:.1f}%) | ROI: {roi:+.1f}%")
    
    # Performance par score range
    print("\n┌" + "─" * 78 + "┐")
    print("│ 2️⃣  PERFORMANCE PAR SCORE V11.2" + " " * 45 + "│")
    print("└" + "─" * 78 + "┘")
    for sr in ['50+', '42-49', '32-41', '<32']:
        d = stats['by_score_range'].get(sr, {'total': 0, 'wins': 0})
        if d['total'] > 0:
            wr = d['wins'] / d['total'] * 100
            bar = "█" * int(wr / 10) + "░" * (10 - int(wr / 10))
            print(f"   {sr:8}: {d['wins']:2}/{d['total']:3} ({wr:5.1f}%) {bar}")
    
    # Performance par marché
    print("\n┌" + "─" * 78 + "┐")
    print("│ 3️⃣  PERFORMANCE PAR MARCHÉ" + " " * 51 + "│")
    print("└" + "─" * 78 + "┘")
    for m, d in sorted(stats['by_market'].items(), key=lambda x: -x[1]['total']):
        if d['total'] > 0:
            wr = d['wins'] / d['total'] * 100
            indicator = "✅" if wr > 55 else "⚠️" if wr > 45 else "❌"
            print(f"   {indicator} {m:25}: {d['wins']:2}/{d['total']:2} ({wr:.1f}%)")
    
    # Performance par ligue
    print("\n┌" + "─" * 78 + "┐")
    print("│ 4️⃣  PERFORMANCE PAR LIGUE (min 3 matchs)" + " " * 37 + "│")
    print("└" + "─" * 78 + "┘")
    for league, d in sorted(stats['by_league'].items(), key=lambda x: -x[1]['total']):
        if d['total'] >= 3:
            wr = d['wins'] / d['total'] * 100
            indicator = "✅" if wr > 55 else "⚠️" if wr > 45 else "❌"
            print(f"   {indicator} {league:30}: {d['wins']:2}/{d['total']:2} ({wr:.1f}%)")
    
    # Impact des layers
    print("\n┌" + "─" * 78 + "┐")
    print("│ 5️⃣  IMPACT DES LAYERS (bets actifs)" + " " * 41 + "│")
    print("└" + "─" * 78 + "┘")
    for layer, data in stats['layer_impact'].items():
        win_avg = sum(data['win']) / len(data['win']) if data['win'] else 0
        loss_avg = sum(data['loss']) / len(data['loss']) if data['loss'] else 0
        diff = win_avg - loss_avg
        n_win = len(data['win'])
        n_loss = len(data['loss'])
        ind = "📈" if diff > 1 else "📉" if diff < -1 else "➡️"
        print(f"   {layer:18}: Win={win_avg:+6.1f} ({n_win:2}) | Loss={loss_avg:+6.1f} ({n_loss:2}) | Δ={diff:+5.1f} {ind}")
    
    # Détail SNIPER
    print("\n┌" + "─" * 78 + "┐")
    print("│ 6️⃣  DÉTAIL SNIPER_BET" + " " * 56 + "│")
    print("└" + "─" * 78 + "┘")
    for d in stats['by_action']['SNIPER_BET']['details']:
        s = "✅" if d['correct'] else "❌"
        print(f"   {s} {d['match']}")
        print(f"      Score:{d['score']:.0f} | {d['real']} [{d['goals']}g] → {d['market']} | Edge:{d['edge']:+.1f}%")
        print(f"      Reason: {d['market_reason']}")
        print(f"      Layers: {d['layers']}")
    
    # Détail NORMAL
    print("\n┌" + "─" * 78 + "┐")
    print("│ 7️⃣  DÉTAIL NORMAL_BET" + " " * 56 + "│")
    print("└" + "─" * 78 + "┘")
    for d in stats['by_action']['NORMAL_BET']['details'][:10]:
        s = "✅" if d['correct'] else "❌"
        print(f"   {s} {d['match']} ({d['real']}) - {d['score']:.0f}pts → {d['market']} | E:{d['edge']:+.1f}%")
    
    # Edge Analysis
    print("\n┌" + "─" * 78 + "┐")
    print("│ 8️⃣  ANALYSE QUANTITATIVE (EDGE)" + " " * 45 + "│")
    print("└" + "─" * 78 + "┘")
    if stats['edge_analysis']:
        positive_edge = [e for e in stats['edge_analysis'] if e['edge'] > 0]
        if positive_edge:
            pos_correct = sum(1 for e in positive_edge if e['correct'])
            print(f"   Bets avec Edge > 0: {len(positive_edge)} | WR: {pos_correct}/{len(positive_edge)} ({pos_correct/len(positive_edge)*100:.1f}%)")
        
        high_edge = [e for e in stats['edge_analysis'] if e['edge'] > 5]
        if high_edge:
            high_correct = sum(1 for e in high_edge if e['correct'])
            print(f"   Bets avec Edge > 5%: {len(high_edge)} | WR: {high_correct}/{len(high_edge)} ({high_correct/len(high_edge)*100:.1f}%)")
    
    # CONCLUSIONS
    print("\n" + "═" * 80)
    print("    CONCLUSIONS & RECOMMANDATIONS")
    print("═" * 80)
    
    print("\n💪 FORCES:")
    for sr, d in stats['by_score_range'].items():
        if d['total'] >= 3 and d['wins'] / d['total'] >= 0.55:
            print(f"   ✅ Score {sr}: {d['wins']/d['total']*100:.0f}% WR ({d['total']} matchs)")
    
    for m, d in stats['by_market'].items():
        if d['total'] >= 3 and d['wins'] / d['total'] >= 0.55:
            print(f"   ✅ Marché {m}: {d['wins']/d['total']*100:.0f}% WR")
    
    print("\n⚠️  FAIBLESSES:")
    for sr, d in stats['by_score_range'].items():
        if d['total'] >= 3 and d['wins'] / d['total'] < 0.45:
            print(f"   ❌ Score {sr}: {d['wins']/d['total']*100:.0f}% WR")
    
    for m, d in stats['by_market'].items():
        if d['total'] >= 2 and d['wins'] / d['total'] < 0.40:
            print(f"   ❌ Marché {m}: {d['wins']/d['total']*100:.0f}% WR")
    
    # ROI Final
    print("\n💰 ROI THÉORIQUE (cote 1.85):")
    total_bets = 0
    total_wins = 0
    for action in ['SNIPER_BET', 'NORMAL_BET']:
        data = stats['by_action'][action]
        if data['total'] > 0:
            roi = (data['wins'] * 1.85 - data['total']) / data['total'] * 100
            print(f"   {action}: {data['wins']}/{data['total']} → ROI {roi:+.1f}%")
            total_bets += data['total']
            total_wins += data['wins']
    
    if total_bets > 0:
        combined_roi = (total_wins * 1.85 - total_bets) / total_bets * 100
        print(f"   ─────────────────────────────")
        print(f"   COMBINED: {total_wins}/{total_bets} → ROI {combined_roi:+.1f}%")
    
    print("\n" + "═" * 80)


if __name__ == "__main__":
    run_backtest()

