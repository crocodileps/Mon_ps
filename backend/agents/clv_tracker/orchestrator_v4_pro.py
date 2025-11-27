#!/usr/bin/env python3
"""
🤖 ORCHESTRATEUR CLV TRACKER V4 PRO
Version professionnelle avec TOUTES les fonctionnalités avancées

📊 SOURCES DE DONNÉES:
✅ odds_history      → Cotes 1X2
✅ odds_totals       → Cotes Over/Under (1.5, 2.5, 3.5)
✅ team_statistics_live → Stats complètes (xG, BTTS%, Over%, forme)
✅ head_to_head      → Historique confrontations
✅ market_predictions → Prédictions existantes
✅ match_results     → Résolution

🎯 FONCTIONNALITÉS:
✅ 13 Marchés complets
✅ Analyse multi-facteurs
✅ TOP 3 marchés automatique
✅ Combinés intelligents (corrélation)
✅ Kelly % optimal
✅ Edge % calculé
✅ Facteurs JSONB détaillés
✅ Score de qualité des données
✅ H2H intégré
✅ Forme récente (L5)
"""
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from datetime import datetime, timedelta
from decimal import Decimal
import json
import logging
import os
import sys
import fcntl
import math
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# ============================================================
# CONFIGURATION
# ============================================================

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
}

LOG_DIR = Path('/home/Mon_ps/logs/clv_tracker')
LOCK_FILE = Path('/tmp/clv_orchestrator_v4.lock')
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / f"v4_{datetime.now().strftime('%Y%m%d')}.log")
    ]
)
logger = logging.getLogger('CLV_V4_PRO')


# ============================================================
# CONSTANTES
# ============================================================

# Les 13 marchés principaux
MARKETS = {
    # 1X2
    'home': {'category': '1x2', 'name': 'Victoire Domicile'},
    'draw': {'category': '1x2', 'name': 'Match Nul'},
    'away': {'category': '1x2', 'name': 'Victoire Extérieur'},
    # Double Chance
    'dc_1x': {'category': 'dc', 'name': 'Double Chance 1X'},
    'dc_x2': {'category': 'dc', 'name': 'Double Chance X2'},
    'dc_12': {'category': 'dc', 'name': 'Double Chance 12'},
    # BTTS
    'btts_yes': {'category': 'btts', 'name': 'Les 2 équipes marquent'},
    'btts_no': {'category': 'btts', 'name': 'Au moins 1 clean sheet'},
    # Over/Under
    'over_15': {'category': 'ou', 'name': 'Plus de 1.5 buts'},
    'over_25': {'category': 'ou', 'name': 'Plus de 2.5 buts'},
    'over_35': {'category': 'ou', 'name': 'Plus de 3.5 buts'},
    'under_25': {'category': 'ou', 'name': 'Moins de 2.5 buts'},
    'under_35': {'category': 'ou', 'name': 'Moins de 3.5 buts'},
}

# Corrélations entre marchés (pour éviter les doubles)
MARKET_CORRELATIONS = {
    ('btts_yes', 'over_25'): 0.72,
    ('btts_yes', 'over_15'): 0.65,
    ('over_25', 'over_35'): 0.85,
    ('under_25', 'under_35'): 0.80,
    ('home', 'dc_1x'): 0.90,
    ('away', 'dc_x2'): 0.90,
    ('btts_no', 'under_25'): 0.55,
}

# Poids des facteurs pour le score
FACTOR_WEIGHTS = {
    'poisson': 0.25,
    'team_stats': 0.20,
    'form': 0.15,
    'h2h': 0.10,
    'odds_value': 0.20,
    'market_efficiency': 0.10,
}


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class TeamStats:
    """Stats complètes d'une équipe"""
    name: str
    avg_scored: float = 1.3
    avg_conceded: float = 1.2
    btts_pct: float = 50.0
    over_25_pct: float = 50.0
    over_15_pct: float = 70.0
    over_35_pct: float = 30.0
    clean_sheet_pct: float = 25.0
    failed_to_score_pct: float = 20.0
    form_points: float = 1.5  # Points par match sur 5 derniers
    last5_goals_for: float = 6.0
    last5_goals_against: float = 5.0
    home_avg_scored: float = 1.5
    home_avg_conceded: float = 1.0
    away_avg_scored: float = 1.1
    away_avg_conceded: float = 1.4
    data_quality: int = 50


@dataclass 
class MatchAnalysis:
    """Analyse complète d'un match"""
    match_id: str
    home_team: str
    away_team: str
    league: str
    commence_time: datetime
    
    # Stats équipes
    home_stats: TeamStats = None
    away_stats: TeamStats = None
    
    # xG calculés
    home_xg: float = 1.3
    away_xg: float = 1.1
    total_xg: float = 2.4
    
    # Probabilités Poisson
    probabilities: Dict[str, float] = None
    
    # Cotes disponibles
    odds: Dict[str, float] = None
    
    # H2H
    h2h_matches: int = 0
    h2h_home_wins: float = 0
    h2h_btts_pct: float = 50.0
    h2h_over25_pct: float = 50.0
    
    # Picks générés
    picks: List[Dict] = None
    
    # Score qualité données
    data_quality: int = 50


@dataclass
class Pick:
    """Un pick complet"""
    market_type: str
    prediction: str
    odds: float
    probability: float
    score: int
    kelly_pct: float
    edge_pct: float
    value_rating: str
    factors: Dict
    is_top3: bool = False
    combo_eligible: bool = True


# ============================================================
# CALCULS MATHÉMATIQUES
# ============================================================

def poisson_prob(lam: float, k: int) -> float:
    """Probabilité Poisson P(X=k)"""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    try:
        return (math.exp(-lam) * (lam ** k)) / math.factorial(k)
    except:
        return 0.0


def calculate_all_probabilities(home_xg: float, away_xg: float) -> Dict[str, float]:
    """Calcule TOUTES les probabilités via Poisson"""
    max_goals = 8
    
    # Matrice des scores
    matrix = {}
    for h in range(max_goals):
        for a in range(max_goals):
            matrix[(h, a)] = poisson_prob(home_xg, h) * poisson_prob(away_xg, a)
    
    # 1X2
    home_win = sum(p for (h, a), p in matrix.items() if h > a)
    draw = sum(p for (h, a), p in matrix.items() if h == a)
    away_win = sum(p for (h, a), p in matrix.items() if h < a)
    
    # BTTS
    btts_yes = sum(p for (h, a), p in matrix.items() if h > 0 and a > 0)
    
    # Over/Under
    over_15 = sum(p for (h, a), p in matrix.items() if h + a > 1)
    over_25 = sum(p for (h, a), p in matrix.items() if h + a > 2)
    over_35 = sum(p for (h, a), p in matrix.items() if h + a > 3)
    
    # Scores exacts (pour analyse)
    exact_00 = matrix.get((0, 0), 0)
    exact_11 = matrix.get((1, 1), 0)
    exact_22 = matrix.get((2, 2), 0)
    
    return {
        # 1X2
        'home': home_win,
        'draw': draw,
        'away': away_win,
        # Double Chance
        'dc_1x': home_win + draw,
        'dc_x2': draw + away_win,
        'dc_12': home_win + away_win,
        # BTTS
        'btts_yes': btts_yes,
        'btts_no': 1 - btts_yes,
        # Over/Under
        'over_15': over_15,
        'under_15': 1 - over_15,
        'over_25': over_25,
        'under_25': 1 - over_25,
        'over_35': over_35,
        'under_35': 1 - over_35,
        # Meta
        'expected_goals': home_xg + away_xg,
        'goal_diff': abs(home_xg - away_xg),
    }


def calculate_value_metrics(prob: float, odds: float) -> Tuple[int, float, float, str]:
    """
    Calcule score, kelly, edge et rating
    
    Returns: (score, kelly_pct, edge_pct, rating)
    """
    if not odds or odds <= 1 or prob <= 0:
        return (0, 0, 0, '❌ NO_VALUE')
    
    implied = 1 / odds
    edge = prob - implied
    edge_pct = edge * 100
    
    # Kelly Criterion (fractional)
    if edge > 0:
        kelly = (edge / (odds - 1)) * 100
        kelly = min(kelly, 10)  # Cap à 10%
    else:
        kelly = 0
    
    # Score composite
    if edge >= 0.15:
        base_score = 85
        rating = '🔥 EXCELLENT'
    elif edge >= 0.10:
        base_score = 75
        rating = '✅ TRÈS BON'
    elif edge >= 0.05:
        base_score = 65
        rating = '📊 BON'
    elif edge >= 0.02:
        base_score = 55
        rating = '�� CORRECT'
    elif edge > 0:
        base_score = 45
        rating = '⚠️ MARGINAL'
    else:
        base_score = max(20, 40 + int(edge * 100))
        rating = '❌ NO_VALUE'
    
    # Ajuster selon les odds (prime aux underdogs value)
    if odds >= 3.0 and edge > 0:
        base_score += 5
    elif odds >= 5.0 and edge > 0:
        base_score += 8
    
    score = min(99, base_score + int(edge * 50))
    
    return (score, round(kelly, 2), round(edge_pct, 2), rating)


def calculate_combo_score(picks: List[Dict]) -> Tuple[float, float, str]:
    """
    Calcule le score d'un combiné en tenant compte des corrélations
    
    Returns: (combined_prob, combined_odds, recommendation)
    """
    if len(picks) < 2:
        return (0, 0, 'NOT_COMBO')
    
    # Vérifier corrélations
    markets = [p['market_type'] for p in picks]
    correlation_penalty = 0
    
    for (m1, m2), corr in MARKET_CORRELATIONS.items():
        if m1 in markets and m2 in markets:
            correlation_penalty += corr * 0.1  # Pénalité proportionnelle
    
    # Probabilité combinée (avec ajustement corrélation)
    combined_prob = 1.0
    combined_odds = 1.0
    
    for pick in picks:
        combined_prob *= pick['probability']
        combined_odds *= pick['odds']
    
    # Ajuster pour corrélation
    combined_prob *= (1 + correlation_penalty * 0.5)  # Les corrélés ont plus de chances ensemble
    
    # Edge du combiné
    implied = 1 / combined_odds if combined_odds > 0 else 0
    combo_edge = combined_prob - implied
    
    if combo_edge > 0.05:
        rec = '🔥 EXCELLENT COMBO'
    elif combo_edge > 0:
        rec = '✅ COMBO VALIDE'
    else:
        rec = '⚠️ COMBO RISQUÉ'
    
    return (round(combined_prob, 4), round(combined_odds, 2), rec)


# ============================================================
# RÉSOLVEURS DE MARCHÉS
# ============================================================

MARKET_RESOLVERS = {
    'home': lambda h, a: h > a,
    'draw': lambda h, a: h == a,
    'away': lambda h, a: h < a,
    'dc_1x': lambda h, a: h >= a,
    'dc_x2': lambda h, a: h <= a,
    'dc_12': lambda h, a: h != a,
    'btts_yes': lambda h, a: h > 0 and a > 0,
    'btts_no': lambda h, a: h == 0 or a == 0,
    'over_15': lambda h, a: (h + a) > 1,
    'under_15': lambda h, a: (h + a) < 2,
    'over_25': lambda h, a: (h + a) > 2,
    'under_25': lambda h, a: (h + a) < 3,
    'over_35': lambda h, a: (h + a) > 3,
    'under_35': lambda h, a: (h + a) < 4,
}


# ============================================================
# ORCHESTRATEUR V4 PRO
# ============================================================

class CLVOrchestratorV4Pro:
    """
    Orchestrateur V4 PRO - Version complète avec toutes les fonctionnalités
    """
    
    VERSION = "4.0-PRO"
    MIN_SCORE = 45  # Score minimum pour un pick
    TOP3_COUNT = 3  # Nombre de TOP picks par match
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.conn = None
        self.start_time = datetime.now()
        self._tracked: Set[str] = set()
        self._team_cache: Dict[str, TeamStats] = {}
        self._adjustments: Dict[str, float] = {}
        self.stats = {'db': 0, 'created': 0, 'resolved': 0, 'combos': 0, 'errors': 0}
    
    def get_db(self):
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
            self.conn.autocommit = False
        return self.conn
    
    def close(self):
        if self.conn and not self.conn.closed:
            self.conn.close()
    
    def _float(self, v, default=0.0) -> float:
        if v is None:
            return default
        if isinstance(v, Decimal):
            return float(v)
        try:
            return float(v)
        except:
            return default
    
    def _rollback(self):
        try:
            if self.conn and not self.conn.closed:
                self.conn.rollback()
        except:
            pass
    
    # ============================================================
    # LOCK
    # ============================================================
    
    def acquire_lock(self) -> bool:
        try:
            self.lock_file = open(LOCK_FILE, 'w')
            fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_file.write(f"{os.getpid()}\n{datetime.now().isoformat()}")
            self.lock_file.flush()
            return True
        except:
            logger.warning("⚠️ Instance déjà en cours")
            return False
    
    def release_lock(self):
        try:
            if hasattr(self, 'lock_file') and self.lock_file:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
                LOCK_FILE.unlink(missing_ok=True)
        except:
            pass
    
    # ============================================================
    # CHARGEMENT DONNÉES
    # ============================================================
    
    def load_adjustments(self):
        """Charge les ajustements du auto-learner"""
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cur.execute("""
                SELECT adjustment_type, target, adjustment_factor
                FROM tracking_model_adjustments
                WHERE updated_at > NOW() - INTERVAL '7 days'
            """)
            
            for row in cur.fetchall():
                key = f"{row['adjustment_type']}_{row['target']}"
                self._adjustments[key] = self._float(row['adjustment_factor'], 1.0)
            
            cur.close()
            conn.commit()
            self.stats['db'] += 1
            logger.info(f"📦 {len(self._adjustments)} ajustements chargés")
        except:
            self._rollback()
    
    def load_tracked(self):
        """Charge les matchs déjà trackés"""
        conn = self.get_db()
        cur = conn.cursor()
        
        try:
            cur.execute("SELECT DISTINCT match_id FROM tracking_clv_picks WHERE match_id IS NOT NULL")
            self._tracked = {r[0] for r in cur.fetchall()}
            cur.close()
            conn.commit()
            self.stats['db'] += 1
        except:
            self._rollback()
    
    def get_team_stats(self, team_name: str, is_home: bool = True) -> TeamStats:
        """Récupère les stats complètes d'une équipe"""
        cache_key = f"{team_name}_{is_home}"
        if cache_key in self._team_cache:
            return self._team_cache[cache_key]
        
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            first_word = team_name.split()[0].lower() if team_name else ''
            
            cur.execute("""
                SELECT 
                    team_name,
                    avg_goals_scored, avg_goals_conceded,
                    btts_pct, over_25_pct, over_15_pct, over_35_pct,
                    clean_sheet_pct, failed_to_score_pct,
                    home_avg_scored, home_avg_conceded,
                    away_avg_scored, away_avg_conceded,
                    last5_goals_for, last5_goals_against,
                    last5_form_points, form,
                    data_quality_score
                FROM team_statistics_live
                WHERE LOWER(team_name) ILIKE %s
                ORDER BY updated_at DESC
                LIMIT 1
            """, (f'%{first_word}%',))
            
            row = cur.fetchone()
            cur.close()
            conn.commit()
            self.stats['db'] += 1
            
            if row:
                # Utiliser stats home/away selon le contexte
                if is_home:
                    avg_scored = self._float(row.get('home_avg_scored') or row.get('avg_goals_scored'), 1.3)
                    avg_conceded = self._float(row.get('home_avg_conceded') or row.get('avg_goals_conceded'), 1.2)
                else:
                    avg_scored = self._float(row.get('away_avg_scored') or row.get('avg_goals_scored'), 1.1)
                    avg_conceded = self._float(row.get('away_avg_conceded') or row.get('avg_goals_conceded'), 1.3)
                
                stats = TeamStats(
                    name=row['team_name'],
                    avg_scored=avg_scored,
                    avg_conceded=avg_conceded,
                    btts_pct=self._float(row.get('btts_pct'), 50),
                    over_25_pct=self._float(row.get('over_25_pct'), 50),
                    over_15_pct=self._float(row.get('over_15_pct'), 70),
                    over_35_pct=self._float(row.get('over_35_pct'), 30),
                    clean_sheet_pct=self._float(row.get('clean_sheet_pct'), 25),
                    failed_to_score_pct=self._float(row.get('failed_to_score_pct'), 20),
                    form_points=self._float(row.get('last5_form_points'), 7.5) / 5,
                    last5_goals_for=self._float(row.get('last5_goals_for'), 6),
                    last5_goals_against=self._float(row.get('last5_goals_against'), 5),
                    home_avg_scored=self._float(row.get('home_avg_scored'), 1.5),
                    home_avg_conceded=self._float(row.get('home_avg_conceded'), 1.0),
                    away_avg_scored=self._float(row.get('away_avg_scored'), 1.1),
                    away_avg_conceded=self._float(row.get('away_avg_conceded'), 1.4),
                    data_quality=int(row.get('data_quality_score') or 50)
                )
            else:
                stats = TeamStats(name=team_name)
            
            self._team_cache[cache_key] = stats
            return stats
            
        except Exception as e:
            logger.debug(f"Stats error for {team_name}: {e}")
            self._rollback()
            return TeamStats(name=team_name)
    
    def get_h2h_stats(self, home_team: str, away_team: str) -> Dict:
        """Récupère les stats H2H"""
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Essayer team_head_to_head
            cur.execute("""
                SELECT 
                    matches_played, home_wins, away_wins, draws,
                    btts_pct, over_25_pct, over_15_pct,
                    last3_btts
                FROM team_head_to_head
                WHERE (LOWER(home_team) ILIKE %s AND LOWER(away_team) ILIKE %s)
                   OR (LOWER(home_team) ILIKE %s AND LOWER(away_team) ILIKE %s)
                LIMIT 1
            """, (
                f'%{home_team.split()[0].lower()}%',
                f'%{away_team.split()[0].lower()}%',
                f'%{away_team.split()[0].lower()}%',
                f'%{home_team.split()[0].lower()}%'
            ))
            
            row = cur.fetchone()
            cur.close()
            conn.commit()
            self.stats['db'] += 1
            
            if row and int(row.get('matches_played') or 0) > 0:
                return {
                    'matches': int(row['matches_played']),
                    'home_win_pct': self._float(row.get('home_wins'), 0) / int(row['matches_played']) * 100,
                    'btts_pct': self._float(row.get('btts_pct'), 50),
                    'over25_pct': self._float(row.get('over_25_pct'), 50),
                    'confidence': 'high' if int(row['matches_played']) >= 5 else 'medium'
                }
            
            return {'matches': 0, 'confidence': 'none'}
            
        except:
            self._rollback()
            return {'matches': 0, 'confidence': 'none'}
    
    # ============================================================
    # ANALYSE MATCH
    # ============================================================
    
    def analyze_match(self, match: Dict) -> MatchAnalysis:
        """Analyse complète d'un match"""
        
        # Stats équipes
        home_stats = self.get_team_stats(match['home_team'], is_home=True)
        away_stats = self.get_team_stats(match['away_team'], is_home=False)
        
        # H2H
        h2h = self.get_h2h_stats(match['home_team'], match['away_team'])
        
        # Calculer xG avec plusieurs facteurs
        # Base: moyenne buts marqués ajustée par buts encaissés adversaire
        home_xg = (home_stats.avg_scored + away_stats.avg_conceded) / 2
        away_xg = (away_stats.avg_scored + home_stats.avg_conceded) / 2
        
        # Ajuster avec forme récente
        home_form_factor = home_stats.form_points / 1.5  # Normaliser autour de 1
        away_form_factor = away_stats.form_points / 1.5
        
        home_xg *= (0.8 + 0.2 * home_form_factor)
        away_xg *= (0.8 + 0.2 * away_form_factor)
        
        # Home advantage (~10%)
        home_xg *= 1.08
        away_xg *= 0.92
        
        # Limiter aux valeurs raisonnables
        home_xg = max(0.5, min(3.5, home_xg))
        away_xg = max(0.3, min(3.0, away_xg))
        
        # Probabilités Poisson
        probabilities = calculate_all_probabilities(home_xg, away_xg)
        
        # Qualité des données
        data_quality = (home_stats.data_quality + away_stats.data_quality) // 2
        if h2h['matches'] >= 3:
            data_quality += 10
        
        analysis = MatchAnalysis(
            match_id=match['match_id'],
            home_team=match['home_team'],
            away_team=match['away_team'],
            league=match.get('league', ''),
            commence_time=match['commence_time'],
            home_stats=home_stats,
            away_stats=away_stats,
            home_xg=round(home_xg, 2),
            away_xg=round(away_xg, 2),
            total_xg=round(home_xg + away_xg, 2),
            probabilities=probabilities,
            odds=match.get('odds', {}),
            h2h_matches=h2h.get('matches', 0),
            h2h_btts_pct=h2h.get('btts_pct', 50),
            h2h_over25_pct=h2h.get('over25_pct', 50),
            data_quality=min(100, data_quality)
        )
        
        return analysis
    
    # ============================================================
    # GÉNÉRATION PICKS
    # ============================================================
    
    def generate_picks(self, analysis: MatchAnalysis, odds: Dict) -> List[Dict]:
        """Génère les picks pour un match analysé"""
        picks = []
        
        for market_type, market_info in MARKETS.items():
            # Obtenir la cote
            odds_value = self._float(odds.get(market_type) or odds.get(f"{market_type}_odds"))
            
            if odds_value <= 1:
                continue
            
            # Probabilité de base (Poisson)
            base_prob = analysis.probabilities.get(market_type, 0)
            
            if base_prob <= 0.05:
                continue
            
            # Ajuster avec stats équipes
            adjusted_prob = self.adjust_probability(
                base_prob, 
                market_type, 
                analysis
            )
            
            # Appliquer ajustements auto-learner
            market_adj = self._adjustments.get(f"market_{market_type}", 1.0)
            league_adj = self._adjustments.get(f"league_{analysis.league}", 1.0)
            adjusted_prob *= market_adj * league_adj
            
            # Limiter
            adjusted_prob = max(0.05, min(0.95, adjusted_prob))
            
            # Calculer métriques
            score, kelly, edge_pct, rating = calculate_value_metrics(adjusted_prob, odds_value)
            
            # Filtrer par score minimum
            if score < self.MIN_SCORE:
                continue
            
            # Construire les facteurs
            factors = self.build_factors(analysis, market_type, base_prob, adjusted_prob)
            
            pick = {
                'market_type': market_type,
                'prediction': market_info['name'],
                'category': market_info['category'],
                'odds': odds_value,
                'probability': adjusted_prob,
                'score': score,
                'kelly_pct': kelly,
                'edge_pct': edge_pct,
                'value_rating': rating,
                'factors': factors,
                'is_top3': False,
                'combo_eligible': True
            }
            
            picks.append(pick)
        
        # Marquer TOP 3
        if picks:
            picks.sort(key=lambda x: x['score'], reverse=True)
            for i, pick in enumerate(picks[:self.TOP3_COUNT]):
                pick['is_top3'] = True
        
        return picks
    
    def adjust_probability(self, base_prob: float, market_type: str, analysis: MatchAnalysis) -> float:
        """Ajuste la probabilité avec les stats équipes"""
        adjusted = base_prob
        
        home_stats = analysis.home_stats
        away_stats = analysis.away_stats
        
        # BTTS
        if market_type == 'btts_yes':
            team_btts = (home_stats.btts_pct + away_stats.btts_pct) / 2 / 100
            adjusted = (base_prob * 0.6 + team_btts * 0.4)
            
            # H2H bonus
            if analysis.h2h_matches >= 3:
                h2h_btts = analysis.h2h_btts_pct / 100
                adjusted = adjusted * 0.8 + h2h_btts * 0.2
        
        elif market_type == 'btts_no':
            cs_rate = (home_stats.clean_sheet_pct + away_stats.failed_to_score_pct) / 2 / 100
            adjusted = (base_prob * 0.6 + cs_rate * 0.4)
        
        # Over/Under
        elif 'over_25' in market_type:
            team_over = (home_stats.over_25_pct + away_stats.over_25_pct) / 2 / 100
            adjusted = (base_prob * 0.6 + team_over * 0.4)
            
            if analysis.h2h_matches >= 3:
                adjusted = adjusted * 0.8 + analysis.h2h_over25_pct / 100 * 0.2
        
        elif 'over_35' in market_type:
            team_over = (home_stats.over_35_pct + away_stats.over_35_pct) / 2 / 100
            adjusted = (base_prob * 0.5 + team_over * 0.5)
        
        elif 'over_15' in market_type:
            team_over = (home_stats.over_15_pct + away_stats.over_15_pct) / 2 / 100
            adjusted = (base_prob * 0.5 + team_over * 0.5)
        
        # 1X2 - ajuster avec forme
        elif market_type == 'home':
            form_boost = (home_stats.form_points - 1.5) * 0.05
            adjusted += form_boost
        
        elif market_type == 'away':
            form_boost = (away_stats.form_points - 1.5) * 0.05
            adjusted += form_boost
        
        return adjusted
    
    def build_factors(self, analysis: MatchAnalysis, market_type: str, base_prob: float, adjusted_prob: float) -> Dict:
        """Construit le dictionnaire des facteurs explicatifs"""
        return {
            'poisson_base': round(base_prob * 100, 1),
            'adjusted': round(adjusted_prob * 100, 1),
            'home_xg': analysis.home_xg,
            'away_xg': analysis.away_xg,
            'total_xg': analysis.total_xg,
            'home_form': round(analysis.home_stats.form_points, 2),
            'away_form': round(analysis.away_stats.form_points, 2),
            'home_btts_pct': analysis.home_stats.btts_pct,
            'away_btts_pct': analysis.away_stats.btts_pct,
            'h2h_matches': analysis.h2h_matches,
            'h2h_btts': analysis.h2h_btts_pct,
            'h2h_over25': analysis.h2h_over25_pct,
            'data_quality': analysis.data_quality,
            'market_category': MARKETS.get(market_type, {}).get('category', 'other')
        }
    
    # ============================================================
    # COMBINÉS INTELLIGENTS
    # ============================================================
    
    def generate_combos(self, all_picks: List[Dict]) -> List[Dict]:
        """Génère des combinés intelligents basés sur les corrélations"""
        combos = []
        
        # Grouper par match
        by_match = {}
        for pick in all_picks:
            mid = pick.get('match_id')
            if mid not in by_match:
                by_match[mid] = []
            by_match[mid].append(pick)
        
        # Combinés intra-match (BTTS + Over par exemple)
        for match_id, picks in by_match.items():
            if len(picks) < 2:
                continue
            
            # TOP picks du match
            top_picks = [p for p in picks if p.get('is_top3')]
            
            for i, p1 in enumerate(top_picks):
                for p2 in top_picks[i+1:]:
                    # Vérifier corrélation
                    pair = (p1['market_type'], p2['market_type'])
                    rev_pair = (p2['market_type'], p1['market_type'])
                    
                    corr = MARKET_CORRELATIONS.get(pair, MARKET_CORRELATIONS.get(rev_pair, 0))
                    
                    # Si peu corrélés ou corrélation favorable
                    if corr < 0.6:
                        combo_prob, combo_odds, rec = calculate_combo_score([p1, p2])
                        
                        if combo_odds >= 2.0 and combo_prob >= 0.3:
                            combos.append({
                                'type': 'intra_match',
                                'match_id': match_id,
                                'picks': [p1['market_type'], p2['market_type']],
                                'combined_odds': combo_odds,
                                'combined_prob': combo_prob,
                                'recommendation': rec,
                                'correlation': corr
                            })
        
        return combos[:5]  # Top 5 combos
    
    # ============================================================
    # COLLECTE PRINCIPALE
    # ============================================================
    
    def get_matches_to_track(self) -> List[Dict]:
        """Récupère les matchs avec toutes leurs cotes"""
        self.load_tracked()
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cur.execute("""
                WITH latest_1x2 AS (
                    SELECT DISTINCT ON (match_id)
                        match_id, home_team, away_team, sport as league,
                        commence_time, home_odds, draw_odds, away_odds
                    FROM odds_history
                    WHERE commence_time BETWEEN NOW() AND NOW() + INTERVAL '72 hours'
                    ORDER BY match_id, collected_at DESC
                ),
                latest_totals AS (
                    SELECT DISTINCT ON (match_id, line)
                        match_id, line, over_odds, under_odds
                    FROM odds_totals
                    WHERE commence_time BETWEEN NOW() AND NOW() + INTERVAL '72 hours'
                    AND line IN (1.5, 2.5, 3.5)
                    ORDER BY match_id, line, collected_at DESC
                ),
                totals_pivot AS (
                    SELECT 
                        match_id,
                        MAX(CASE WHEN line = 1.5 THEN over_odds END) as over_15_odds,
                        MAX(CASE WHEN line = 1.5 THEN under_odds END) as under_15_odds,
                        MAX(CASE WHEN line = 2.5 THEN over_odds END) as over_25_odds,
                        MAX(CASE WHEN line = 2.5 THEN under_odds END) as under_25_odds,
                        MAX(CASE WHEN line = 3.5 THEN over_odds END) as over_35_odds,
                        MAX(CASE WHEN line = 3.5 THEN under_odds END) as under_35_odds
                    FROM latest_totals
                    GROUP BY match_id
                )
                SELECT 
                    h.match_id, h.home_team, h.away_team, h.league, h.commence_time,
                    h.home_odds, h.draw_odds, h.away_odds,
                    t.over_15_odds, t.under_15_odds,
                    t.over_25_odds, t.under_25_odds,
                    t.over_35_odds, t.under_35_odds
                FROM latest_1x2 h
                LEFT JOIN totals_pivot t ON h.match_id = t.match_id
                ORDER BY h.commence_time
            """)
            
            matches = cur.fetchall()
            cur.close()
            conn.commit()
            self.stats['db'] += 1
            
            new_matches = [m for m in matches if m['match_id'] not in self._tracked]
            logger.info(f"📋 {len(new_matches)} nouveaux / {len(matches)} total")
            
            return new_matches
            
        except Exception as e:
            logger.error(f"Get matches error: {e}")
            self._rollback()
            return []
    
    def collect(self) -> Dict:
        """Collecte PRO avec toutes les fonctionnalités"""
        start = datetime.now()
        logger.info("🚀 COLLECT V4 PRO - Analyse multi-facteurs")
        
        self.load_adjustments()
        matches = self.get_matches_to_track()
        
        if not matches:
            logger.info("✅ Aucun nouveau match")
            return {'created': 0, 'matches': 0, 'combos': 0}
        
        all_picks = []
        created = 0
        
        for match in matches:
            try:
                # Construire dict odds
                odds = {
                    'home': self._float(match.get('home_odds')),
                    'draw': self._float(match.get('draw_odds')),
                    'away': self._float(match.get('away_odds')),
                    'over_15': self._float(match.get('over_15_odds')),
                    'under_15': self._float(match.get('under_15_odds')),
                    'over_25': self._float(match.get('over_25_odds')),
                    'under_25': self._float(match.get('under_25_odds')),
                    'over_35': self._float(match.get('over_35_odds')),
                    'under_35': self._float(match.get('under_35_odds')),
                }
                
                # Calculer Double Chance
                if odds['home'] > 1 and odds['draw'] > 1:
                    odds['dc_1x'] = round(1 / (1/odds['home'] + 1/odds['draw']), 2)
                if odds['draw'] > 1 and odds['away'] > 1:
                    odds['dc_x2'] = round(1 / (1/odds['draw'] + 1/odds['away']), 2)
                if odds['home'] > 1 and odds['away'] > 1:
                    odds['dc_12'] = round(1 / (1/odds['home'] + 1/odds['away']), 2)
                
                # Calculer BTTS (estimation depuis over/under)
                if odds.get('over_25', 0) > 1:
                    # Approximation: BTTS corrélé avec Over 2.5
                    odds['btts_yes'] = round(odds['over_25'] * 0.95, 2)
                    odds['btts_no'] = round(1 / (1 - 1/odds['btts_yes']), 2) if odds['btts_yes'] > 1 else 0
                
                match['odds'] = odds
                
                # Analyse complète
                analysis = self.analyze_match(match)
                
                # Générer picks
                picks = self.generate_picks(analysis, odds)
                
                if picks:
                    # Ajouter match_id aux picks
                    for p in picks:
                        p['match_id'] = match['match_id']
                    
                    all_picks.extend(picks)
                    
                    # Sauvegarder
                    saved = self._save_picks(match, picks, analysis)
                    created += saved
                    
                    if saved > 0:
                        self._tracked.add(match['match_id'])
                        top3 = [p for p in picks if p['is_top3']]
                        logger.info(f"  ✅ {match['home_team']} vs {match['away_team']}: {saved} picks ({len(top3)} TOP)")
                        
            except Exception as e:
                logger.warning(f"  ⚠️ {match.get('match_id', 'unknown')}: {e}")
                self.stats['errors'] += 1
                self._rollback()
        
        # Générer combinés
        combos = self.generate_combos(all_picks)
        if combos:
            self._save_combos(combos)
            self.stats['combos'] = len(combos)
            logger.info(f"🎰 {len(combos)} combinés intelligents générés")
        
        self.stats['created'] += created
        duration = (datetime.now() - start).total_seconds()
        
        logger.info(f"✅ COLLECT: {created} picks | {len(combos)} combos | {duration:.1f}s")
        
        return {
            'created': created, 
            'matches': len(matches), 
            'combos': len(combos),
            'duration': duration
        }
    
    def _save_picks(self, match: Dict, picks: List[Dict], analysis: MatchAnalysis) -> int:
        """Sauvegarde les picks avec toutes les données"""
        if self.dry_run:
            return len(picks)
        
        conn = self.get_db()
        cur = conn.cursor()
        saved = 0
        
        for pick in picks:
            try:
                cur.execute("""
                    INSERT INTO tracking_clv_picks (
                        match_id, home_team, away_team, league, match_name,
                        market_type, prediction, diamond_score, odds_taken,
                        probability, kelly_pct, edge_pct, value_rating,
                        home_xg, away_xg, total_xg, poisson_prob,
                        home_form_l5, away_form_l5, h2h_pct,
                        is_top3, source, predicted_prob, factors,
                        data_quality_score, league_tier,
                        implied_prob, ev_expected
                    ) VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                    )
                    ON CONFLICT (match_id, market_type) DO UPDATE SET
                        diamond_score = EXCLUDED.diamond_score,
                        odds_taken = EXCLUDED.odds_taken,
                        probability = EXCLUDED.probability,
                        kelly_pct = EXCLUDED.kelly_pct,
                        edge_pct = EXCLUDED.edge_pct,
                        factors = EXCLUDED.factors,
                        updated_at = NOW()
                """, (
                    match['match_id'],
                    match['home_team'],
                    match['away_team'],
                    match.get('league', ''),
                    f"{match['home_team']} vs {match['away_team']}",
                    pick['market_type'],
                    pick['prediction'],
                    pick['score'],
                    pick['odds'],
                    pick['probability'] * 100,
                    pick['kelly_pct'],
                    pick['edge_pct'],
                    pick['value_rating'],
                    analysis.home_xg,
                    analysis.away_xg,
                    analysis.total_xg,
                    pick['factors']['poisson_base'],
                    analysis.home_stats.form_points,
                    analysis.away_stats.form_points,
                    analysis.h2h_btts_pct if analysis.h2h_matches > 0 else None,
                    pick['is_top3'],
                    'orchestrator_v4_pro',
                    pick['score'] / 100,
                    Json(pick['factors']),
                    analysis.data_quality,
                    1 if 'premier' in match.get('league', '').lower() or 'liga' in match.get('league', '').lower() else 2,
                    1 / pick['odds'] if pick['odds'] > 0 else 0,
                    pick['edge_pct'] * pick['odds'] / 100
                ))
                saved += 1
            except Exception as e:
                logger.debug(f"Insert error: {e}")
        
        conn.commit()
        cur.close()
        self.stats['db'] += 1
        return saved
    
    def _save_combos(self, combos: List[Dict]):
        """Sauvegarde les combinés"""
        if self.dry_run or not combos:
            return
        
        conn = self.get_db()
        cur = conn.cursor()
        
        try:
            for combo in combos:
                cur.execute("""
                    INSERT INTO fg_combo_tracking (
                        combo_type, match_ids, markets, 
                        combined_odds, combined_prob, recommendation,
                        created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT DO NOTHING
                """, (
                    combo['type'],
                    [combo.get('match_id', '')],
                    combo['picks'],
                    combo['combined_odds'],
                    combo['combined_prob'],
                    combo['recommendation']
                ))
            
            conn.commit()
        except Exception as e:
            logger.debug(f"Combo save error: {e}")
            self._rollback()
        finally:
            cur.close()
    
    # ============================================================
    # RESOLVE (même que V3)
    # ============================================================
    
    def resolve(self) -> Dict:
        """Résolution 100% locale via match_results"""
        start = datetime.now()
        logger.info("🔄 RESOLVE V4 PRO")
        
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cur.execute("""
                SELECT 
                    p.id, p.home_team, p.away_team, p.market_type,
                    p.odds_taken, p.stake, p.match_id,
                    o.commence_time
                FROM tracking_clv_picks p
                JOIN odds_history o ON p.match_id = o.match_id
                WHERE p.is_resolved = false
                AND o.commence_time < NOW() - INTERVAL '2 hours'
                GROUP BY p.id, p.home_team, p.away_team, p.market_type,
                         p.odds_taken, p.stake, p.match_id, o.commence_time
            """)
            
            pending = cur.fetchall()
            conn.commit()
            self.stats['db'] += 1
            
            logger.info(f"📋 {len(pending)} picks à vérifier")
            
            if not pending:
                return {'resolved': 0, 'wins': 0, 'losses': 0}
            
            # ... (même logique de résolution que V3)
            resolved = wins = losses = 0
            
            # Grouper par match
            matches = {}
            for p in pending:
                ct = p['commence_time']
                key = (p['home_team'].lower().strip(), p['away_team'].lower().strip(),
                       ct.date() if ct else None)
                if key not in matches:
                    matches[key] = []
                matches[key].append(p)
            
            for (home, away, mdate), picks in matches.items():
                if not mdate:
                    continue
                
                cur.execute("""
                    SELECT score_home, score_away
                    FROM match_results
                    WHERE is_finished = true
                    AND DATE(commence_time) BETWEEN %s AND %s
                    AND LOWER(home_team) ILIKE %s
                    AND LOWER(away_team) ILIKE %s
                    LIMIT 1
                """, (
                    mdate - timedelta(days=1),
                    mdate + timedelta(days=1),
                    f'%{home.split()[0]}%',
                    f'%{away.split()[0]}%'
                ))
                
                result = cur.fetchone()
                self.stats['db'] += 1
                
                if not result:
                    continue
                
                hs, as_ = result['score_home'], result['score_away']
                logger.info(f"  ✅ {home} vs {away}: {hs}-{as_}")
                
                for pick in picks:
                    resolver = MARKET_RESOLVERS.get(pick['market_type'])
                    if not resolver:
                        continue
                    
                    is_win = resolver(hs, as_)
                    
                    if is_win:
                        stake = self._float(pick['stake'], 1)
                        odds = self._float(pick['odds_taken'], 1)
                        profit = stake * (odds - 1)
                        wins += 1
                    else:
                        profit = -self._float(pick['stake'], 1)
                        losses += 1
                    
                    if not self.dry_run:
                        cur.execute("""
                            UPDATE tracking_clv_picks
                            SET is_resolved=true, is_winner=%s, profit_loss=%s,
                                score_home=%s, score_away=%s, resolved_at=NOW()
                            WHERE id=%s
                        """, (is_win, profit, hs, as_, pick['id']))
                    
                    resolved += 1
            
            if not self.dry_run:
                conn.commit()
            cur.close()
            
            self.stats['resolved'] += resolved
            wr = round(wins / (wins + losses) * 100, 1) if (wins + losses) > 0 else 0
            duration = (datetime.now() - start).total_seconds()
            
            logger.info(f"✅ RESOLVE: {resolved} ({wins}W/{losses}L = {wr}%) | {duration:.1f}s")
            
            return {'resolved': resolved, 'wins': wins, 'losses': losses, 'win_rate': wr}
            
        except Exception as e:
            logger.error(f"Resolve error: {e}")
            self._rollback()
            return {'resolved': 0, 'wins': 0, 'losses': 0, 'error': str(e)}
    
    # ============================================================
    # SMART MODE
    # ============================================================
    
    def run_smart(self) -> Dict:
        """Mode intelligent"""
        results = {'actions': [], 'api_calls': 0}
        
        logger.info("🧠 MODE SMART V4 PRO")
        
        # Toujours collecter (mise à jour des cotes)
        results['collect'] = self.collect()
        results['actions'].append('collect')
        
        # Résoudre si nécessaire
        results['resolve'] = self.resolve()
        if results['resolve'].get('resolved', 0) > 0:
            results['actions'].append('resolve')
        
        return results
    
    # ============================================================
    # EXÉCUTION
    # ============================================================
    
    def run(self, task: str = 'smart') -> Dict:
        """Point d'entrée"""
        if not self.acquire_lock():
            return {'error': 'Already running'}
        
        try:
            logger.info("=" * 70)
            logger.info(f"🤖 CLV ORCHESTRATOR V{self.VERSION}")
            logger.info(f"   Mode: {task} | Dry-run: {self.dry_run}")
            logger.info("   📊 13 Marchés | TOP 3 | Combinés | Kelly | Edge | H2H")
            logger.info("=" * 70)
            
            if task == 'collect':
                return self.collect()
            elif task == 'resolve':
                return self.resolve()
            else:
                return self.run_smart()
                
        finally:
            self.release_lock()
            self.close()
            duration = (datetime.now() - self.start_time).total_seconds()
            logger.info(f"\n⏱️ {duration:.1f}s | DB: {self.stats['db']} | Erreurs: {self.stats['errors']}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='CLV Orchestrator V4 PRO')
    parser.add_argument('task', nargs='?', default='smart',
                        choices=['collect', 'resolve', 'smart'])
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    
    orch = CLVOrchestratorV4Pro(dry_run=args.dry_run)
    result = orch.run(args.task)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
