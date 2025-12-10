#!/usr/bin/env python3
"""
🤖 CLV ORCHESTRATOR V7.0 - SMART AUTO-LEARNING

ÉVOLUTIONS PAR RAPPORT À V6:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. FACTEURS DYNAMIQUES
   → Charge les facteurs depuis la DB (auto-learning)
   → Fallback sur facteurs statiques si pas de données

2. FILTRAGE INTELLIGENT PAR SCORE
   → Découverte: Score 60-79 = meilleur ROI
   → Score 80+ souvent surestimé (31% WR seulement)
   → Nouveau: "sweet_spot" scoring

3. FILTRAGE PAR COTES
   → Cotes < 2.5 = 60%+ WR
   → Cotes > 3.5 = <30% WR → pénaliser fortement

4. CONTEXTE MULTI-DIMENSIONNEL
   → Ajustement par league (si données suffisantes)
   → Ajustement par horaire
   → Ajustement par équipe

5. CONFIDENCE SCORING AMÉLIORÉ
   → Combine score + cotes + historique
   → Évite les faux-positifs hauts scores

ARCHITECTURE:
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATOR V7 PIPELINE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  📊 LOAD           🔬 CALC           📈 SCORE          🎯 FILTER           │
│  ┌─────────┐      ┌─────────┐       ┌─────────┐       ┌─────────┐          │
│  │ Dynamic │ ───► │ Probs   │ ────► │ Smart   │ ────► │ Sweet   │          │
│  │ Factors │      │ Poisson │       │ Score   │       │ Spot    │          │
│  └─────────┘      └─────────┘       └─────────┘       └─────────┘          │
│       │                │                 │                 │               │
│       ▼                ▼                 ▼                 ▼               │
│  ┌─────────┐      ┌─────────┐       ┌─────────┐       ┌─────────┐          │
│  │ From DB │      │ Team    │       │ Odds    │       │ TOP     │          │
│  │ or Base │      │ Stats   │       │ Penalty │       │ Picks   │          │
│  └─────────┘      └─────────┘       └─────────┘       └─────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
"""

import psycopg2
from psycopg2.extras import RealDictCursor, Json
from datetime import datetime
from decimal import Decimal
import json
import logging
import os
import math
import sys
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Coach Intelligence Integration
import sys
sys.path.append("/app/agents")
try:
    from coach_impact import CoachImpactCalculator
    COACH_IMPACT_ENABLED = True
except ImportError:
    COACH_IMPACT_ENABLED = False

# Steam Validator Integration
sys.path.append("/app/scripts")
try:
    from steam_validator import validate_prediction, get_steam_score
    STEAM_VALIDATOR_ENABLED = True
    print("✅ Steam Validator chargé")
except ImportError:
    STEAM_VALIDATOR_ENABLED = False

# Reality Check Integration
try:
    from agents.reality_check import RealityChecker
    REALITY_CHECK_ENABLED = True
    print("✅ Reality Check Module loaded")
except ImportError as e:
    REALITY_CHECK_ENABLED = False
    print(f"⚠️ Reality Check not available: {e}")
    print("⚠️ Steam Validator non disponible")
    logger.warning("CoachImpact not available - using static xG")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('OrchestratorV7')

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
}


# ============================================================
# FACTEURS DE BASE (fallback si pas de données dynamiques)
# ============================================================

BASE_FACTORS = {
    'btts_yes': 1.25,
    'over_25': 1.20,
    'dc_12': 1.12,
    'dc_1x': 1.10,
    'away': 1.15,
    'dc_x2': 1.20,
    'over_15': 1.10,
    'over_35': 1.10,
    'btts_no': 1.00,
    'home': 0.90,
    'draw': 1.05,
    'under_25': 1.05,
    'under_35': 1.00,
    'under_15': 0.95,
}

# Bonus/Malus par marché (performance backtest)
MARKET_PERFORMANCE = {
    'btts_yes': {'bonus': 15, 'backtest_wr': 85.7},
    'over_25': {'bonus': 12, 'backtest_wr': 66.7},
    'dc_12': {'bonus': 10, 'backtest_wr': 100.0},
    'dc_1x': {'bonus': 5, 'backtest_wr': 57.1},
    'btts_no': {'bonus': 8, 'backtest_wr': 50.0},
    'away': {'bonus': 3, 'backtest_wr': 42.9},
    'over_15': {'bonus': 5, 'backtest_wr': None},
    'over_35': {'bonus': 0, 'backtest_wr': None},
    'draw': {'bonus': -5, 'backtest_wr': 25.0},
    'dc_x2': {'bonus': -8, 'backtest_wr': 37.5},
    'under_25': {'bonus': -10, 'backtest_wr': 28.6},
    'under_35': {'bonus': 0, 'backtest_wr': None},
    'under_15': {'bonus': -5, 'backtest_wr': None},
    'home': {'bonus': -15, 'backtest_wr': 12.5},
}

# ============================================================
# SWEET SPOT CONFIGURATION (basé sur analyse réelle)
# ============================================================

SWEET_SPOT_CONFIG = {
    # Score ranges et leur performance réelle
    'score_ranges': {
        (80, 100): {'multiplier': 0.85, 'reason': 'Score 80+ = 31% WR réel'},
        (70, 79): {'multiplier': 1.10, 'reason': 'Score 70-79 = 75% WR'},
        (60, 69): {'multiplier': 1.15, 'reason': 'Score 60-69 = 66.7% WR, best ROI'},
        (50, 59): {'multiplier': 0.80, 'reason': 'Score 50-59 = 29.4% WR'},
        (0, 49): {'multiplier': 0.60, 'reason': 'Score <50 = éviter'},
    },
    # Odds ranges et leur performance
    'odds_ranges': {
        (1.0, 1.5): {'multiplier': 1.10, 'reliability': 95},
        (1.5, 2.0): {'multiplier': 1.05, 'reliability': 85},
        (2.0, 2.5): {'multiplier': 1.00, 'reliability': 70},
        (2.5, 3.5): {'multiplier': 0.85, 'reliability': 50},
        (3.5, 5.0): {'multiplier': 0.70, 'reliability': 30},
        (5.0, 99): {'multiplier': 0.50, 'reliability': 15},
    }
}


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


@dataclass
class SmartPick:
    """Pick intelligent avec métadonnées complètes"""
    match_id: str
    home_team: str
    away_team: str
    market_type: str
    odds: float
    probability: float
    raw_score: int
    adjusted_score: int
    sweet_spot_score: int
    edge_pct: float
    kelly: float
    confidence: str
    risk_level: str
    expected_wr: float
    rating: str
    factors: Dict
    is_sweet_spot: bool
    recommendation: str


class OrchestratorV7Smart:
    """
    Orchestrateur V7 avec Auto-Learning intégré
    
    Caractéristiques:
    - Facteurs dynamiques depuis DB
    - Sweet spot filtering (score 60-79)
    - Pénalité grosses cotes
    - Confidence multi-dimensionnelle
    """
    
    def __init__(self):
        self.conn = None
        
        # Reality Check Engine
        self.reality_checker = None
        if REALITY_CHECK_ENABLED:
            try:
                self.reality_checker = RealityChecker(DB_CONFIG)
                logger.info("🧠 Reality Check Engine initialized")
            except Exception as e:
                logger.warning(f"Reality Check init failed: {e}")
        self.team_cache = {}
        self.dynamic_factors = {}
        self.stats = {
            'created': 0, 'matches': 0, 'errors': 0,
            'sweet_spot_picks': 0, 'filtered_out': 0,
            'by_market': {}, 'by_confidence': {}
        }
    
    def get_db(self):
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
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
    
    # ================================================================
    # 1. CHARGEMENT FACTEURS DYNAMIQUES
    # ================================================================
    
    def load_dynamic_factors(self) -> Dict[str, float]:
        """Charge les facteurs depuis la DB (auto-learning)"""
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        factors = BASE_FACTORS.copy()
        
        try:
            cur.execute("""
                SELECT target, factor 
                FROM fg_model_adjustments 
                WHERE adjustment_type = 'market_factor' 
                AND is_active = true
            """)
            
            for row in cur.fetchall():
                market = row['target']
                factor = self._float(row['factor'], 1.0)
                factors[market] = factor
                logger.info(f"   📦 {market}: {factor:.2f} (dynamique)")
            
            conn.commit()
        except:
            conn.rollback()
            logger.info("   ℹ️ Utilisation des facteurs de base")
        finally:
            cur.close()
        
        self.dynamic_factors = factors
        return factors
    
    # ================================================================
    # 2. SWEET SPOT SCORING
    # ================================================================
    
    def calculate_sweet_spot_score(self, raw_score: int, odds: float, market_type: str) -> Tuple[int, bool, str]:
        """
        Calcule le score "sweet spot" optimisé
        
        Logique:
        1. Ajuster selon la tranche de score (60-79 = bonus)
        2. Ajuster selon les cotes (< 2.5 = bonus)
        3. Déterminer si dans le sweet spot
        """
        # 1. Multiplicateur de score
        score_mult = 1.0
        score_reason = ""
        for (low, high), config in SWEET_SPOT_CONFIG['score_ranges'].items():
            if low <= raw_score < high:
                score_mult = config['multiplier']
                score_reason = config['reason']
                break
        
        # 2. Multiplicateur de cotes
        odds_mult = 1.0
        for (low, high), config in SWEET_SPOT_CONFIG['odds_ranges'].items():
            if low <= odds < high:
                odds_mult = config['multiplier']
                break
        
        # 3. Bonus marché
        market_info = MARKET_PERFORMANCE.get(market_type, {'bonus': 0})
        market_bonus = market_info['bonus']
        
        # 4. Calculer le score final
        adjusted = raw_score * score_mult * odds_mult + market_bonus
        sweet_spot_score = max(0, min(100, int(adjusted)))
        
        # 5. Déterminer si dans le sweet spot
        is_sweet_spot = (
            60 <= raw_score <= 79 and 
            odds <= 2.5 and 
            sweet_spot_score >= 55
        )
        
        # 6. Recommandation
        if is_sweet_spot and sweet_spot_score >= 70:
            recommendation = "🔥 FORTEMENT RECOMMANDÉ"
        elif is_sweet_spot:
            recommendation = "✅ RECOMMANDÉ"
        elif sweet_spot_score >= 65:
            recommendation = "📊 INTÉRESSANT"
        elif sweet_spot_score >= 50:
            recommendation = "📈 À SURVEILLER"
        else:
            recommendation = "⚠️ PRUDENCE"
        
        return sweet_spot_score, is_sweet_spot, recommendation
    
    def calculate_smart_score(self, prob_raw: float, prob_corrected: float, 
                              odds: float, market_type: str) -> Dict:
        """
        Scoring intelligent V7
        
        Retourne le score complet avec sweet spot analysis
        """
        if not odds or odds <= 1 or prob_corrected <= 0:
            return {'score': 0, 'sweet_score': 0, 'is_sweet_spot': False}
        
        implied = 1 / odds
        edge = prob_corrected - implied
        edge_pct = edge * 100
        
        # Kelly
        kelly = min((edge / (odds - 1)) * 100, 10) if edge > 0 else 0
        
        # Info marché
        market_info = MARKET_PERFORMANCE.get(market_type, {'bonus': 0, 'backtest_wr': 50})
        
        # ============================================================
        # SCORING V7
        # ============================================================
        
        # 1. Score probabilité (35 points max)
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
        reliability = 90 - (odds - 1) * 20
        reliability = max(20, min(95, reliability))
        reliability_score = reliability * 0.2
        
        # 4. Bonus marché (15 points max)
        market_bonus = market_info['bonus']
        
        # Score RAW
        raw_score = max(0, min(100, int(prob_score + edge_score + reliability_score + market_bonus)))
        
        # Sweet spot transformation
        sweet_score, is_sweet_spot, recommendation = self.calculate_sweet_spot_score(
            raw_score, odds, market_type
        )
        
        # WR attendu (basé sur backtest + probabilité)
        backtest_wr = market_info.get('backtest_wr', 50)
        if backtest_wr:
            expected_wr = backtest_wr * 0.4 + prob_corrected * 100 * 0.6
        else:
            expected_wr = prob_corrected * 100
        
        # Confiance
        if is_sweet_spot and sweet_score >= 70:
            confidence = 'very_high'
        elif sweet_score >= 65 and odds <= 2.0:
            confidence = 'high'
        elif sweet_score >= 55:
            confidence = 'medium'
        elif sweet_score >= 45:
            confidence = 'low'
        else:
            confidence = 'very_low'
        
        # Risk level
        if odds < 1.5:
            risk = 'very_low'
        elif odds < 2.0:
            risk = 'low'
        elif odds < 2.5:
            risk = 'medium'
        elif odds < 3.5:
            risk = 'high'
        else:
            risk = 'very_high'
        
        # Rating
        if sweet_score >= 80:
            rating = '🔥 EXCELLENT'
        elif sweet_score >= 70:
            rating = '✅ TRÈS BON'
        elif sweet_score >= 60:
            rating = '📊 BON'
        elif sweet_score >= 50:
            rating = '📈 CORRECT'
        elif sweet_score >= 40:
            rating = '⚠️ MARGINAL'
        else:
            rating = '❌ FAIBLE'
        
        return {
            'raw_score': raw_score,
            'sweet_score': sweet_score,
            'is_sweet_spot': is_sweet_spot,
            'recommendation': recommendation,
            'edge_pct': round(edge_pct, 2),
            'kelly': round(kelly, 2),
            'confidence': confidence,
            'risk': risk,
            'expected_wr': round(expected_wr, 1),
            'rating': rating,
            'analysis': {
                'prob_score': round(prob_score, 1),
                'edge_score': round(edge_score, 1),
                'reliability_score': round(reliability_score, 1),
                'market_bonus': market_bonus,
            }
        }
    
    # ================================================================
    # 3. STATS ÉQUIPES
    # ================================================================
    

    def apply_reality_check(self, home_team: str, away_team: str, 
                            raw_score: int, market: str, direction: str) -> dict:
        """
        Applique le filtre Reality Check sur un pick.
        
        Args:
            home_team: Équipe domicile
            away_team: Équipe extérieur
            raw_score: Score V7 original (0-100)
            market: Type de marché (h2h, totals, etc.)
            direction: Direction du pari (home, away, over, under, etc.)
        
        Returns:
            Dict avec score ajusté, warnings et multiplicateur
        """
        if not self.reality_checker:
            return {
                'adjusted_score': raw_score,
                'warnings': [],
                'confidence_mult': 1.0,
                'reality_score': 50,
                'convergence': 'unknown'
            }
        
        try:
            # Analyse Reality Check
            reality = self.reality_checker.analyze_match(home_team, away_team)
            
            # Récupérer le multiplicateur approprié selon la direction
            mult_map = {
                'home': 'home_win_mult',
                'away': 'away_win_mult', 
                'draw': 'draw_mult',
                'over': 'over_mult',
                'under': 'under_mult',
                'btts_yes': 'btts_mult',
                'btts_no': 'btts_mult'
            }
            mult_key = mult_map.get(direction, 'confidence_correction')
            confidence_mult = reality.adjustments.get(mult_key, 1.0)
            
            # Ajuster le score
            adjusted_score = raw_score
            
            # Bonus/Malus selon convergence
            if reality.convergence == 'full_convergence':
                adjusted_score = min(100, int(raw_score * 1.05))  # +5%
            elif reality.convergence == 'divergence':
                adjusted_score = int(raw_score * 0.90)  # -10%
            elif reality.convergence == 'strong_divergence':
                adjusted_score = int(raw_score * 0.80)  # -20%
                logger.warning(f"⚠️ STRONG DIVERGENCE: {home_team} vs {away_team}")
            
            # Appliquer le multiplicateur de confiance
            adjusted_score = int(adjusted_score * confidence_mult)
            adjusted_score = max(0, min(100, adjusted_score))
            
            return {
                'adjusted_score': adjusted_score,
                'original_score': raw_score,
                'warnings': reality.warnings,
                'confidence_mult': round(confidence_mult, 3),
                'reality_score': reality.reality_score,
                'convergence': reality.convergence,
                'tier_gap': reality.tier_gap,
                'home_tier': reality.home_tier,
                'away_tier': reality.away_tier
            }
            
        except Exception as e:
            logger.error(f"Reality Check error for {home_team} vs {away_team}: {e}")
            return {
                'adjusted_score': raw_score,
                'warnings': [f"Reality Check failed: {str(e)}"],
                'confidence_mult': 1.0,
                'reality_score': 50,
                'convergence': 'error'
            }


    def validate_with_steam(self, match_id: str, market: str, confidence: str, sweet_score: float) -> dict:
        """
        🛡️ Valide un pick avec le Steam Validator (Shadow Mode)
        
        Returns:
            dict avec validated, action, reason, adjusted_confidence, steam_data
        """
        if not STEAM_VALIDATOR_ENABLED:
            return {'validated': True, 'action': 'PROCEED', 'reason': 'Steam Validator désactivé'}
        
        try:
            # Convertir market en direction (home, away, draw)
            market_to_direction = {
                'home': 'home',
                'dc_1x': 'home',
                'dc_12': 'home',
                'away': 'away',
                'dc_x2': 'away',
                'draw': 'draw',
                'btts_yes': None,
                'btts_no': None,
                'over_15': None,
                'over_25': None,
                'over_35': None,
                'under_15': None,
                'under_25': None,
                'under_35': None,
            }
            
            direction = market_to_direction.get(market)
            
            # Si marché neutre (BTTS, Over/Under), pas de validation Steam
            if direction is None:
                return {'validated': True, 'action': 'PROCEED', 'reason': 'Marché non-directionnel'}
            
            # Convertir confidence en score numérique
            confidence_map = {'very_high': 85, 'high': 75, 'medium': 60, 'low': 45, 'very_low': 30}
            confidence_score = confidence_map.get(confidence, 50)
            
            # Appeler le Steam Validator
            result = validate_prediction(match_id, direction, confidence_score)
            
            return result
            
        except Exception as e:
            logger.warning(f"⚠️ Erreur Steam Validator: {e}")
            return {'validated': True, 'action': 'PROCEED', 'reason': f'Erreur: {e}'}

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
        except:
            conn.rollback()
            return self._default_stats()
        finally:
            cur.close()
    
    def _default_stats(self) -> Dict:
        return {
            'avg_scored': 1.3, 'avg_conceded': 1.2,
            'btts_pct': 50, 'over_25_pct': 50, 'over_15_pct': 70,
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
            
            if row and int(row.get('total_matches') or 0) >= 2:
                return {
                    'matches': int(row['total_matches']),
                    'btts_pct': self._float(row.get('btts_pct'), 50),
                    'over_25_pct': self._float(row.get('over_25_pct'), 50),
                }
            return {'matches': 0}
        except:
            conn.rollback()
            return {'matches': 0}
        finally:
            cur.close()
    
    # ================================================================
    # 4. COLLECTE PRINCIPALE
    # ================================================================
    
    def collect(self, hours_ahead: int = 48, sweet_spot_only: bool = False) -> Dict:
        """
        Collecte avec scoring intelligent V7
        
        Args:
            hours_ahead: Heures à regarder
            sweet_spot_only: Si True, ne garde que les picks "sweet spot"
        """
        start = datetime.now()
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Charger les facteurs dynamiques
        logger.info("📦 CHARGEMENT FACTEURS DYNAMIQUES...")
        factors = self.load_dynamic_factors()
        
        logger.info("�� COLLECT V7 SMART - Sweet Spot Analysis")
        logger.info(f"   Mode: {'Sweet Spot Only' if sweet_spot_only else 'Tous les picks'}")
        
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
        sweet_spot_picks = []
        
        for match in matches:
            try:
                home_stats = self.get_team_stats(match['home_team'])
                away_stats = self.get_team_stats(match['away_team'])
                h2h = self.get_h2h_stats(match['home_team'], match['away_team'])
                
                # xG avec Coach Intelligence
                base_home_xg = (home_stats["home_scored"] + away_stats["away_conceded"]) / 2
                base_away_xg = (away_stats["away_scored"] + home_stats["home_conceded"]) / 2
                
                if COACH_IMPACT_ENABLED:
                    try:
                        coach_calc = CoachImpactCalculator(self.conn)
                        coach_result = coach_calc.calculate_adjusted_xg(
                            match["home_team"], match["away_team"],
                            base_home_xg, base_away_xg
                        )
                        home_xg = coach_result["home_xg"]
                        away_xg = coach_result["away_xg"]
                        
                        # Log si ajustement significatif
                        hc = coach_result["home_coach"]
                        ac = coach_result["away_coach"]
                        if hc["style"] != "unknown" or ac["style"] != "unknown":
                            logger.info(f"🧠 COACH: {match['home_team']}({hc['style']}) vs {match['away_team']}({ac['style']}) | xG: {base_home_xg:.1f}->{home_xg:.1f} vs {base_away_xg:.1f}->{away_xg:.1f}")
                    except Exception as e:
                        logger.warning(f"Coach impact error: {e}")
                        home_xg = base_home_xg * 1.08
                        away_xg = base_away_xg * 0.92
                        home_xg = max(0.5, min(3.5, home_xg))
                        away_xg = max(0.3, min(3.0, away_xg))
                else:
                    home_xg = base_home_xg * 1.08
                    away_xg = base_away_xg * 0.92
                    home_xg = max(0.5, min(3.5, home_xg))
                    away_xg = max(0.3, min(3.0, away_xg))
                
                # Probabilités brutes (Poisson)
                probs_raw = calculate_match_probabilities(home_xg, away_xg)
                
                # Ajuster avec stats équipes
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
                
                # Générer picks
                match_picks = []
                for market, prob_raw in probs_raw.items():
                    odds = odds_map.get(market, 0)
                    if not odds or odds <= 1:
                        continue
                    
                    # Appliquer facteur dynamique
                    factor = factors.get(market, 1.0)
                    prob_corrected = min(0.95, max(0.05, prob_raw * factor))
                    
                    # Scoring V7 Smart
                    scoring = self.calculate_smart_score(prob_raw, prob_corrected, odds, market)

                    # ═══════════════════════════════════════════════════════════
                    # 🛡️ STEAM VALIDATOR - MODE OBSERVATION (Shadow Mode)
                    # Ne bloque pas, mais log et enrichit le pick pour analyse
                    # ═══════════════════════════════════════════════════════════
                    steam_result = self.validate_with_steam(
                        match['match_id'], 
                        market, 
                        scoring['confidence'], 
                        scoring['sweet_score']
                    )
                    
                    steam_action = steam_result.get('action', 'PROCEED')
                    steam_reason = steam_result.get('reason', 'N/A')
                    
                    # Tracker les actions Steam
                    if 'steam_actions' not in self.stats:
                        self.stats['steam_actions'] = {'BLOCK': 0, 'REDUCE': 0, 'BOOST': 0, 'PROCEED': 0}
                    self.stats['steam_actions'][steam_action] = self.stats['steam_actions'].get(steam_action, 0) + 1
                    
                    # Logging selon l'action
                    if steam_action == 'BLOCK':
                        logger.warning(f"  🛑 STEAM WOULD_BLOCK: {match['home_team']} vs {match['away_team']} - {market} | {steam_reason}")
                    elif steam_action == 'REDUCE':
                        logger.info(f"  📉 STEAM REDUCE: {match['home_team']} vs {match['away_team']} - {market} | {steam_reason}")
                    elif steam_action == 'BOOST':
                        logger.info(f"  📈 STEAM BOOST: {match['home_team']} vs {match['away_team']} - {market} | {steam_reason}")
                    # ═══════════════════════════════════════════════════════════

                    
                    # Stats
                    if market not in self.stats['by_market']:
                        self.stats['by_market'][market] = {'count': 0, 'sweet_spot': 0, 'total_score': 0}
                    self.stats['by_market'][market]['count'] += 1
                    self.stats['by_market'][market]['total_score'] += scoring['sweet_score']
                    if scoring['is_sweet_spot']:
                        self.stats['by_market'][market]['sweet_spot'] += 1
                    
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
                        'raw_score': scoring['raw_score'],
                        'score': scoring['sweet_score'],  # Score principal = sweet_score
                        'kelly': scoring['kelly'],
                        'edge_pct': scoring['edge_pct'],
                        'rating': scoring['rating'],
                        'confidence': scoring['confidence'],
                        'risk': scoring['risk'],
                        'expected_wr': scoring['expected_wr'],
                        'home_xg': home_xg,
                        'away_xg': away_xg,
                        'is_sweet_spot': scoring['is_sweet_spot'],
                        'recommendation': scoring['recommendation'],
                        'h2h_matches': h2h.get('matches', 0),
                        'factors': {
                            'correction_factor': factor,
                            'is_sweet_spot': scoring['is_sweet_spot'],
                            **scoring['analysis']
                        },
                        'steam_validation': {
                            'action': steam_action,
                            'reason': steam_reason,
                            'validated': steam_result.get('validated', True),
                            'adjusted_confidence': steam_result.get('adjusted_confidence'),
                            'steam_data': steam_result.get('steam_data', {})
                        }
                    }
                    
                    # Filtrer si mode sweet_spot_only
                    if sweet_spot_only and not scoring['is_sweet_spot']:
                        self.stats['filtered_out'] += 1
                        continue
                    
                    match_picks.append(pick)
                    
                    if scoring['is_sweet_spot']:
                        sweet_spot_picks.append(pick)
                
                if match_picks:
                    match_picks.sort(key=lambda x: x['score'], reverse=True)
                    for i, p in enumerate(match_picks[:3]):
                        p['is_top3'] = True
                    for p in match_picks[3:]:
                        p['is_top3'] = False
                    
                    all_picks.extend(match_picks)
                    self.stats['matches'] += 1
                    
                    top = match_picks[0]
                    sweet_count = sum(1 for p in match_picks if p.get('is_sweet_spot'))
                    sweet_tag = f" | 🎯 {sweet_count} sweet" if sweet_count > 0 else ""
                    logger.info(f"  ✅ {match['home_team']} vs {match['away_team']}: "
                               f"{len(match_picks)} picks | TOP: {top['market_type']} ({top['score']}){sweet_tag}")
                
            except Exception as e:
                self.stats['errors'] += 1
                logger.debug(f"Error: {e}")
        
        cur.close()
        
        if all_picks:
            self._save_picks(all_picks)
        
        self.stats['created'] = len(all_picks)
        self.stats['sweet_spot_picks'] = len(sweet_spot_picks)
        
        duration = (datetime.now() - start).total_seconds()
        
        logger.info(f"\n✅ COLLECT V7: {len(all_picks)} picks | {len(sweet_spot_picks)} sweet spot | {self.stats['matches']} matchs | {duration:.1f}s")
        
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
                    Json(pick.get('factors', {})), 'orchestrator_v7_smart',
                    pick['commence_time']
                ))
            except Exception as e:
                conn.rollback()
                logger.debug(f"Save error: {e}")
        
        conn.commit()
        cur.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Orchestrator V7 Smart')
    parser.add_argument('--hours', type=int, default=48, help='Heures à regarder')
    parser.add_argument('--sweet-spot', action='store_true', help='Seulement les picks sweet spot')
    args = parser.parse_args()
    
    logger.info("=" * 70)
    logger.info("🤖 CLV ORCHESTRATOR V7.0 - SMART AUTO-LEARNING")
    logger.info("=" * 70)
    logger.info("📊 Features:")
    logger.info("   • Facteurs dynamiques (auto-learning)")
    logger.info("   • Sweet spot scoring (60-79 = best ROI)")
    logger.info("   • Pénalité grosses cotes (>2.5)")
    logger.info("=" * 70)
    
    orch = OrchestratorV7Smart()
    stats = orch.collect(hours_ahead=args.hours, sweet_spot_only=args.sweet_spot)
    
    # Afficher stats
    print(f"\n📊 STATISTIQUES V7:")
    print(f"   Total picks: {stats['created']}")
    print(f"   Sweet spot picks: {stats['sweet_spot_picks']} ({stats['sweet_spot_picks']/max(1,stats['created'])*100:.1f}%)")
    print(f"   Matchs analysés: {stats['matches']}")
    
    print("\n📊 PAR MARCHÉ:")
    for market, data in sorted(stats['by_market'].items(), key=lambda x: x[1]['count'], reverse=True):
        avg = data['total_score'] / data['count'] if data['count'] > 0 else 0
        print(f"   {market:12} | {data['count']:3} picks | {data['sweet_spot']:2} sweet | Score: {avg:5.1f}")
    
    print(f"\n📊 PAR CONFIANCE:")
    for conf, count in sorted(stats['by_confidence'].items(), key=lambda x: x[1], reverse=True):
        print(f"   {conf:12} | {count:3} picks")
    
    orch.close()
    
    print(json.dumps({'created': stats['created'], 'sweet_spot': stats['sweet_spot_picks']}, indent=2))


if __name__ == "__main__":
    main()
