#!/usr/bin/env python3
"""
🎯 CLV ORCHESTRATOR V9.1 - QUANT PRO FINAL

AMÉLIORATIONS V9.1 vs V9.0:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 🔴 FIX ML PATH    : Fallback multi-paths pour trouver le modèle
2. 🔴 DATA COVERAGE  : Indicateur de confiance (% layers actifs)
3. 🟡 ANTI DOUBLE-COUNT : ML comme multiplicateur (pas additif)
4. 🟢 PRE-FETCH SQL  : Context cache pour éviter N+1 queries
5. 🟢 FUZZY SEARCH   : Amélioration recherche équipes/arbitres
6. 🔵 AUTO-TUNING    : Structure préparée pour meta-learning

SOURCES DE DONNÉES (10):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. team_momentum       - Forme récente, streaks, absences
2. tactical_matrix     - Styles de jeu, confrontations tactiques
3. market_traps        - 196 pièges actifs (BLOCKING)
4. referee_intelligence - Tendency over/under, home bias
5. head_to_head        - Historique confrontations
6. team_head_to_head   - H2H détaillé par équipe
7. reality_check_results - Convergence analysis
8. fg_sharp_money      - Mouvements steam
9. team_market_profiles - Meilleur marché par équipe
10. team_intelligence   - Goals avg, BTTS rate, Over25 rate
"""

import psycopg2
import psycopg2.extras
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import math
import logging
import json
import os
from functools import lru_cache

# Configuration logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(message)s')
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

DB_CONFIG = {
    'host': os.environ.get('POSTGRES_HOST', 'localhost'),
    'port': int(os.environ.get('POSTGRES_PORT', 5432)),
    'dbname': os.environ.get('POSTGRES_DB', 'monps_db'),
    'user': os.environ.get('POSTGRES_USER', 'monps_user'),
    'password': os.environ.get('POSTGRES_PASSWORD', 'monps_secure_password_2024')
}

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION QUANT PRO - FROM V5 CALIBRATED (+3.99u ROI)
# ═══════════════════════════════════════════════════════════════════════════════

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

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION V7 SMART
# ═══════════════════════════════════════════════════════════════════════════════

SWEET_SPOT_CONFIG = {
    'score_ranges': {
        (0, 40): {'multiplier': 0.5, 'reason': 'Score trop faible'},
        (40, 60): {'multiplier': 0.8, 'reason': 'Score moyen'},
        (60, 80): {'multiplier': 1.2, 'reason': 'Sweet spot optimal'},
        (80, 100): {'multiplier': 0.9, 'reason': 'Score surestimé'},
    },
    'optimal_odds_range': (1.50, 2.50),
    'min_edge': 0.03,
}

STEAM_CONFIG = {
    'significant_move_pct': 3.0,
    'sharp_books': ['pinnacle', 'betfair', 'sbobet'],
    'steam_bonus': 15,
    'anti_steam_penalty': -20,
}

# ═══════════════════════════════════════════════════════════════════════════════
# LAYER WEIGHTS (V9.1 - ML RÉDUIT pour éviter double counting)
# ═══════════════════════════════════════════════════════════════════════════════

LAYER_WEIGHTS = {
    'momentum': 15,
    'tactical': 12,
    'trap': 100,         # BLOCKING
    'referee': 10,
    'h2h': 8,
    'reality': 10,
    'ml': 12,            # RÉDUIT de 20 → 12 (évite double counting)
    'profile': 12,
    'steam': 15,
    'sweet_spot': 10,
}

# ML Config (V9.1 - ML comme MULTIPLICATEUR)
ML_CONFIG = {
    'min_confidence': 0.55,
    'min_odds_profitable': 1.65,
    'roi_warning_threshold': 1.40,
    # V9.1: ML comme multiplicateur plutôt qu'additif
    'ml_multiplier_high': 1.25,    # Si ML > 70% → score × 1.25
    'ml_multiplier_medium': 1.10,  # Si ML 60-70% → score × 1.10
    'ml_multiplier_low': 0.85,     # Si ML < 50% → score × 0.85
}

# ═══════════════════════════════════════════════════════════════════════════════
# AUTO-TUNING CONFIG (V9.1 - Préparation V10)
# ═══════════════════════════════════════════════════════════════════════════════

AUTO_TUNING = {
    'enabled': False,  # Activer pour V10
    'min_samples': 50,
    'adjustment_factor': 0.1,
    'layers_to_tune': ['momentum', 'tactical', 'referee', 'h2h', 'reality'],
}

# ═══════════════════════════════════════════════════════════════════════════════
# TEAM NAME ALIASES (V9.1 - Amélioration fuzzy search)
# ═══════════════════════════════════════════════════════════════════════════════

TEAM_ALIASES = {
    # Premier League
    'manchester city': ['man city', 'city', 'mcfc', 'manchester c'],
    'manchester united': ['man utd', 'man united', 'mufc', 'manchester u'],
    'liverpool': ['lfc', 'the reds'],
    'arsenal': ['afc', 'the gunners'],
    'chelsea': ['cfc', 'the blues'],
    'tottenham': ['spurs', 'tottenham hotspur', 'thfc'],
    'newcastle': ['newcastle united', 'nufc', 'the magpies'],
    'aston villa': ['villa', 'avfc'],
    'west ham': ['west ham united', 'the hammers', 'whufc'],
    'brighton': ['brighton hove albion', 'bhafc', 'seagulls'],
    # La Liga
    'real madrid': ['madrid', 'real', 'rmcf', 'los blancos'],
    'barcelona': ['barca', 'fcb', 'barça'],
    'atletico madrid': ['atletico', 'atleti', 'atm'],
    # Bundesliga
    'bayern munich': ['bayern', 'fcb munich', 'fc bayern'],
    'borussia dortmund': ['dortmund', 'bvb'],
    'rb leipzig': ['leipzig', 'rbl'],
    'bayer leverkusen': ['leverkusen', 'bayer 04'],
    # Serie A
    'inter milan': ['inter', 'internazionale'],
    'ac milan': ['milan', 'rossoneri'],
    'juventus': ['juve', 'the old lady'],
    # Ligue 1
    'paris saint-germain': ['psg', 'paris'],
    'olympique marseille': ['marseille', 'om'],
    'olympique lyon': ['lyon', 'ol'],
    'as monaco': ['monaco'],
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASS - PICK QUANT PRO (V9.1)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class QuantProPick:
    """Pick avec toutes les données Quant Pro V9.1"""
    match_id: str
    home_team: str
    away_team: str
    league: str
    market_type: str
    odds: float
    predicted_prob: float
    implied_prob: float
    
    # Layer Scores
    momentum_score: int = 0
    tactical_score: int = 0
    trap_detected: bool = False
    trap_reason: str = ""
    trap_alternative: str = ""
    referee_score: int = 0
    h2h_score: int = 0
    reality_score: int = 0
    ml_score: int = 0
    profile_score: int = 0
    steam_score: int = 0
    sweet_spot_score: int = 0
    
    # Layer Details
    home_momentum: Optional[Dict] = None
    away_momentum: Optional[Dict] = None
    tactical_match: Optional[Dict] = None
    referee_data: Optional[Dict] = None
    h2h_data: Optional[Dict] = None
    reality_data: Optional[Dict] = None
    steam_data: Optional[Dict] = None
    
    # ML (V9.1 - Multiplicateur)
    ml_confidence: float = 0.0
    ml_prediction: str = "N/A"
    ml_multiplier: float = 1.0  # NOUVEAU V9.1
    
    # Profiles
    home_profile: Optional[str] = None
    away_profile: Optional[str] = None
    profile_consensus: bool = False
    
    # Final
    base_score: int = 0
    layer_score: int = 0       # NOUVEAU V9.1 - Score avant ML
    final_score: int = 0
    kelly: float = 0.0
    edge: float = 0.0
    recommendation: str = "SKIP"
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Sweet Spot
    is_sweet_spot: bool = False
    sweet_spot_reason: str = ""
    
    # Data Coverage (V9.1 - Indicateur confiance)
    data_coverage: float = 0.0
    layers_active: int = 0
    
    def to_dict(self) -> Dict:
        return {
            'match': f"{self.home_team} vs {self.away_team}",
            'league': self.league,
            'market': self.market_type,
            'odds': self.odds,
            'final_score': self.final_score,
            'recommendation': self.recommendation,
            'is_sweet_spot': self.is_sweet_spot,
            'layers': {
                'momentum': self.momentum_score,
                'tactical': self.tactical_score,
                'trap': 'BLOCKED' if self.trap_detected else 'OK',
                'referee': self.referee_score,
                'h2h': self.h2h_score,
                'reality': self.reality_score,
                'ml': self.ml_score,
                'profile': self.profile_score,
                'steam': self.steam_score,
                'sweet_spot': self.sweet_spot_score,
            },
            'ml_confidence': f"{self.ml_confidence*100:.1f}%",
            'ml_multiplier': f"×{self.ml_multiplier:.2f}",
            'kelly': f"{self.kelly:.2f}%",
            'edge': f"{self.edge*100:.1f}%",
            'data_coverage': f"{self.data_coverage*100:.0f}%",
            'layers_active': f"{self.layers_active}/6",
            'reasons': self.reasons,
            'warnings': self.warnings,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR V9.1 QUANT PRO FINAL
# ═══════════════════════════════════════════════════════════════════════════════

class OrchestratorV9Quant:
    """Orchestrator V9.1 Quant Pro - Version Finale Optimisée"""
    
    def __init__(self):
        """Initialisation avec connection DB et cache"""
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            logger.info("✅ Connexion DB établie")
        except Exception as e:
            logger.error(f"❌ Erreur DB: {e}")
            self.conn = None
        
        # Stats
        self.stats = {
            'analyzed': 0,
            'momentum_applied': 0,
            'tactical_applied': 0,
            'traps_blocked': 0,
            'referee_applied': 0,
            'h2h_applied': 0,
            'reality_applied': 0,
            'ml_applied': 0,
            'steam_detected': 0,
            'sweet_spots': 0,
            'high_data_coverage': 0,
            'low_data_coverage': 0,
            'final_picks': 0,
        }
        
        # ML Model
        self.ml_model = None
        self.ml_scaler = None
        self._load_ml_model()
        
        # Context Cache (V9.1 - Pre-fetch)
        self._context_cache = {}
        
        logger.info("🎯 Orchestrator V9.1 Quant Pro FINAL initialisé")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ML MODEL LOADING (V9.1 - Multi-path fallback)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _load_ml_model(self):
        """Charge le modèle ML avec fallback sur plusieurs paths"""
        try:
            import joblib
            
            model_paths = [
                "/home/Mon_ps/ml_smart_quant/models/best_model.joblib",
                "/home/Mon_ps/ml_smart_quant/models/best_moddel.joblib",
                "/home/Mon_ps/backend/ml/models/best_model.joblib",
                "/home/Mon_ps/models/best_model.joblib",
                "./models/best_model.joblib",
            ]
            
            scaler_paths = [
                "/home/Mon_ps/ml_smart_quant/models/scaler.joblib",
                "/home/Mon_ps/backend/ml/models/scaler.joblib",
                "/home/Mon_ps/models/scaler.joblib",
                "./models/scaler.joblib",
            ]
            
            for path in model_paths:
                if os.path.exists(path):
                    self.ml_model = joblib.load(path)
                    logger.info(f"✅ ML chargé: {path}")
                    break
            
            for path in scaler_paths:
                if os.path.exists(path):
                    self.ml_scaler = joblib.load(path)
                    logger.info(f"✅ Scaler chargé: {path}")
                    break
            
            if not self.ml_model:
                logger.warning("⚠️ ML non trouvé - Le système fonctionne sans ML")
                
        except Exception as e:
            logger.warning(f"⚠️ ML error: {e}")
            self.ml_model = None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FUZZY TEAM SEARCH (V9.1 - Amélioration recherche)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _normalize_team_name(self, team_name: str) -> List[str]:
        """Retourne toutes les variantes possibles d'un nom d'équipe"""
        name_lower = team_name.lower().strip()
        variants = [name_lower, team_name]
        
        # Chercher dans les aliases
        for canonical, aliases in TEAM_ALIASES.items():
            if name_lower == canonical or name_lower in aliases:
                variants.extend([canonical] + aliases)
                break
            for alias in aliases:
                if alias in name_lower or name_lower in alias:
                    variants.extend([canonical] + aliases)
                    break
        
        return list(set(variants))
    
    def _build_fuzzy_where(self, column: str, team_name: str) -> Tuple[str, List[str]]:
        """Construit une clause WHERE fuzzy pour une équipe"""
        variants = self._normalize_team_name(team_name)
        placeholders = ' OR '.join([f"LOWER({column}) LIKE %s" for _ in variants])
        params = [f"%{v}%" for v in variants]
        return f"({placeholders})", params
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PRE-FETCH CONTEXT (V9.1 - Évite N+1 queries)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _prefetch_match_context(self, home_team: str, away_team: str, 
                                 match_id: str, league: str, referee_name: str = None) -> Dict:
        """Pré-charge toutes les données du match en une fois"""
        cache_key = f"{home_team}_{away_team}_{match_id}"
        
        if cache_key in self._context_cache:
            return self._context_cache[cache_key]
        
        context = {
            'home_momentum': self.get_team_momentum(home_team),
            'away_momentum': self.get_team_momentum(away_team),
            'home_style': self.detect_team_style(home_team),
            'away_style': self.detect_team_style(away_team),
            'tactical': None,
            'referee': self._get_referee_with_fallback(league, referee_name),
            'h2h': self.get_h2h_data(home_team, away_team),
            'reality': self.get_reality_check(match_id),
            'home_profile': self.get_team_profile(home_team, 'home'),
            'away_profile': self.get_team_profile(away_team, 'away'),
            'home_intel': self.get_team_intelligence(home_team),
            'away_intel': self.get_team_intelligence(away_team),
            'steam_data': {},
        }
        
        # Tactical matrix (après styles)
        context['tactical'] = self.get_tactical_match(
            context['home_style'], context['away_style']
        )
        
        self._context_cache[cache_key] = context
        return context
    
    def clear_cache(self):
        """Vide le cache (à appeler entre les sessions)"""
        self._context_cache = {}
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LAYER 1: MOMENTUM
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_team_momentum(self, team_name: str) -> Optional[Dict]:
        """Récupère le momentum d'une équipe avec fuzzy search"""
        if not self.conn:
            return None
        
        try:
            variants = self._normalize_team_name(team_name)
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Construire la requête fuzzy
                where_clauses = ' OR '.join(['LOWER(team_name) LIKE %s' for _ in variants])
                params = [f"%{v}%" for v in variants]
                
                cur.execute(f"""
                    SELECT 
                        team_name, momentum_score, momentum_status,
                        last_5_results, current_streak,
                        goals_scored_last_5, goals_conceded_last_5,
                        clean_sheets_last_5, failed_to_score_last_5,
                        key_player_absent, coach_under_pressure, new_coach_bounce
                    FROM team_momentum
                    WHERE {where_clauses}
                    ORDER BY updated_at DESC
                    LIMIT 1
                """, params)
                
                row = cur.fetchone()
                if row:
                    return dict(row)
        except Exception as e:
            logger.debug(f"Momentum error: {e}")
        return None
    
    def calculate_momentum_score(self, pick: QuantProPick, context: Dict) -> int:
        """Calcule le score basé sur le momentum (utilise context)"""
        score = 0
        
        home_mom = context.get('home_momentum')
        away_mom = context.get('away_momentum')
        
        pick.home_momentum = home_mom
        pick.away_momentum = away_mom
        
        # Analyse momentum domicile
        if home_mom:
            mom_score = int(home_mom.get('momentum_score', 50) or 50)
            if mom_score >= 80:
                score += 8
                pick.reasons.append(f"🔥 {pick.home_team} en excellente forme")
            elif mom_score <= 30:
                score -= 5
                pick.warnings.append(f"⚠️ {pick.home_team} en mauvaise forme")
            
            if home_mom.get('key_player_absent'):
                score -= 5
                pick.warnings.append(f"🚑 Joueur clé absent ({pick.home_team})")
            if home_mom.get('coach_under_pressure'):
                score -= 3
            if home_mom.get('new_coach_bounce'):
                score += 5
        
        # Analyse momentum extérieur
        if away_mom:
            mom_score = int(away_mom.get('momentum_score', 50) or 50)
            if mom_score >= 80:
                score += 5
                pick.reasons.append(f"🔥 {pick.away_team} en excellente forme")
            elif mom_score <= 30:
                score -= 3
            
            if away_mom.get('key_player_absent'):
                score -= 4
                pick.warnings.append(f"🚑 Joueur clé absent ({pick.away_team})")
        
        # Bonus BTTS/Over si 2 équipes offensives
        if home_mom and away_mom:
            home_goals = int(home_mom.get('goals_scored_last_5', 0) or 0)
            away_goals = int(away_mom.get('goals_scored_last_5', 0) or 0)
            if home_goals >= 8 and away_goals >= 8:
                if pick.market_type in ['btts_yes', 'over_25', 'over_35']:
                    score += 7
                    pick.reasons.append("🔥 2 équipes offensives (8+ buts/5 matchs)")
        
        if score != 0:
            self.stats['momentum_applied'] += 1
        
        return max(-LAYER_WEIGHTS['momentum'], min(LAYER_WEIGHTS['momentum'], score))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LAYER 2: TACTICAL
    # ═══════════════════════════════════════════════════════════════════════════
    
    def detect_team_style(self, team_name: str) -> str:
        """Détecte le style de jeu d'une équipe"""
        team_lower = team_name.lower()
        
        style_map = {
            'possession': ['barcelona', 'manchester city', 'city', 'bayern', 'ajax', 'arsenal', 'brighton', 'napoli'],
            'counter_attack': ['atletico', 'inter', 'leicester', 'crystal palace', 'wolves', 'real madrid'],
            'pressing': ['liverpool', 'tottenham', 'atalanta', 'athletic bilbao', 'brentford'],
            'gegenpressing': ['liverpool', 'rb leipzig', 'bayer leverkusen', 'leverkusen', 'dortmund'],
            'defensive': ['juventus', 'chelsea', 'burnley', 'everton', 'getafe'],
            'attacking': ['psg', 'paris', 'benfica', 'sporting', 'monaco'],
        }
        
        for style, keywords in style_map.items():
            for keyword in keywords:
                if keyword in team_lower:
                    return style
        
        return 'balanced'
    
    def get_tactical_match(self, home_style: str, away_style: str) -> Optional[Dict]:
        """Récupère les données tactiques pour une confrontation de styles"""
        if not self.conn:
            return None
        
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT 
                        style_a, style_b,
                        btts_probability, over_25_probability,
                        under_25_probability, upset_probability,
                        sample_size, confidence_level
                    FROM tactical_matrix
                    WHERE (LOWER(style_a) = LOWER(%s) AND LOWER(style_b) = LOWER(%s))
                       OR (LOWER(style_a) = LOWER(%s) AND LOWER(style_b) = LOWER(%s))
                    ORDER BY sample_size DESC
                    LIMIT 1
                """, (home_style, away_style, away_style, home_style))
                
                row = cur.fetchone()
                if row:
                    return dict(row)
                
                # Fallback: chercher avec 'balanced'
                cur.execute("""
                    SELECT 
                        style_a, style_b,
                        btts_probability, over_25_probability,
                        under_25_probability, upset_probability,
                        sample_size, confidence_level
                    FROM tactical_matrix
                    WHERE LOWER(style_a) = 'balanced' OR LOWER(style_b) = 'balanced'
                    ORDER BY sample_size DESC
                    LIMIT 1
                """)
                row = cur.fetchone()
                if row:
                    return dict(row)
                    
        except Exception as e:
            logger.debug(f"Tactical error: {e}")
        return None
    
    def calculate_tactical_score(self, pick: QuantProPick, context: Dict) -> int:
        """Calcule le score basé sur la matrice tactique"""
        score = 0
        
        tactical = context.get('tactical')
        pick.tactical_match = tactical
        
        if tactical and tactical.get('sample_size', 0) >= 5:  # Réduit de 10 à 5
            btts_prob = float(tactical.get('btts_probability', 50) or 50)
            over25_prob = float(tactical.get('over_25_probability', 50) or 50)
            confidence = tactical.get('confidence_level', 'low')
            
            conf_mult = 1.2 if confidence == 'high' else 1.0
            
            if pick.market_type == 'btts_yes':
                if btts_prob >= 60:  # Réduit de 65 à 60
                    score += int(10 * conf_mult)
                    pick.reasons.append(f"📊 Tactique: BTTS {btts_prob:.0f}%")
                elif btts_prob <= 40:
                    score -= 8
            elif pick.market_type == 'btts_no':
                if btts_prob <= 40:
                    score += int(8 * conf_mult)
                elif btts_prob >= 60:
                    score -= 10
            elif pick.market_type in ['over_25', 'over_35']:
                if over25_prob >= 60:
                    score += int(10 * conf_mult)
                    pick.reasons.append(f"📊 Tactique: O2.5 {over25_prob:.0f}%")
                elif over25_prob <= 40:
                    score -= 8
            elif pick.market_type in ['under_25', 'under_15']:
                if over25_prob <= 40:
                    score += int(8 * conf_mult)
                elif over25_prob >= 60:
                    score -= 10
            
            if score != 0:
                self.stats['tactical_applied'] += 1
        
        return max(-LAYER_WEIGHTS['tactical'], min(LAYER_WEIGHTS['tactical'], score))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LAYER 3: TRAPS (BLOCKING)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def check_market_trap(self, team: str, market: str) -> Optional[Dict]:
        """Vérifie si un piège existe pour cette équipe/marché"""
        if not self.conn:
            return None
        
        try:
            variants = self._normalize_team_name(team)
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                where_clauses = ' OR '.join(['LOWER(team_name) LIKE %s' for _ in variants])
                params = [f"%{v}%" for v in variants]
                params.append(market)
                
                cur.execute(f"""
                    SELECT 
                        team_name, market_type,
                        alert_level, trap_reason,
                        alternative_market, supporting_stats
                    FROM market_traps
                    WHERE ({where_clauses})
                      AND market_type = %s
                      AND alert_level = 'TRAP'
                    LIMIT 1
                """, params)
                
                row = cur.fetchone()
                if row:
                    return dict(row)
        except Exception as e:
            logger.debug(f"Trap check error: {e}")
        return None
    
    def calculate_trap_score(self, pick: QuantProPick) -> bool:
        """Vérifie les pièges - Retourne True si TRAP détecté"""
        
        # Vérifier home team
        home_trap = self.check_market_trap(pick.home_team, pick.market_type)
        if home_trap:
            pick.trap_detected = True
            pick.trap_reason = home_trap.get('trap_reason', 'Trap détecté')
            pick.trap_alternative = home_trap.get('alternative_market', '')
            pick.warnings.append(f"🚫 TRAP: {pick.home_team} - {pick.trap_reason}")
            self.stats['traps_blocked'] += 1
            return True
        
        # Vérifier away team
        away_trap = self.check_market_trap(pick.away_team, pick.market_type)
        if away_trap:
            pick.trap_detected = True
            pick.trap_reason = away_trap.get('trap_reason', 'Trap détecté')
            pick.trap_alternative = away_trap.get('alternative_market', '')
            pick.warnings.append(f"🚫 TRAP: {pick.away_team} - {pick.trap_reason}")
            self.stats['traps_blocked'] += 1
            return True
        
        return False
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LAYER 4: REFEREE (V9.1 - Avec fallback par ligue)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_referee_data(self, league: str, referee_name: str = None) -> Optional[Dict]:
        """Récupère les données arbitre"""
        if not self.conn:
            return None
        
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                if referee_name:
                    cur.execute("""
                        SELECT 
                            referee_name, league, total_matches,
                            avg_goals_per_game, under_over_tendency,
                            avg_penalties_per_game, avg_cards_per_game,
                            home_bias_factor
                        FROM referee_intelligence
                        WHERE LOWER(referee_name) LIKE LOWER(%s)
                        ORDER BY total_matches DESC
                        LIMIT 1
                    """, (f"%{referee_name}%",))
                else:
                    cur.execute("""
                        SELECT 
                            referee_name, league, total_matches,
                            avg_goals_per_game, under_over_tendency,
                            avg_penalties_per_game, avg_cards_per_game,
                            home_bias_factor
                        FROM referee_intelligence
                        WHERE LOWER(league) LIKE LOWER(%s)
                        ORDER BY total_matches DESC
                        LIMIT 1
                    """, (f"%{league}%",))
                
                row = cur.fetchone()
                if row:
                    return dict(row)
        except Exception as e:
            logger.debug(f"Referee error: {e}")
        return None
    
    def _get_referee_with_fallback(self, league: str, referee_name: str = None) -> Optional[Dict]:
        """Récupère arbitre avec fallback sur moyenne ligue"""
        ref_data = self.get_referee_data(league, referee_name)
        
        if not ref_data and self.conn:
            # Fallback: moyenne de la ligue
            try:
                with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute("""
                        SELECT 
                            'League Average' as referee_name,
                            %s as league,
                            SUM(total_matches) as total_matches,
                            AVG(avg_goals_per_game) as avg_goals_per_game,
                            'neutral' as under_over_tendency,
                            AVG(avg_penalties_per_game) as avg_penalties_per_game,
                            AVG(avg_cards_per_game) as avg_cards_per_game,
                            1.0 as home_bias_factor
                        FROM referee_intelligence
                        WHERE LOWER(league) LIKE LOWER(%s)
                    """, (league, f"%{league}%"))
                    
                    row = cur.fetchone()
                    if row and row['total_matches']:
                        return dict(row)
            except Exception as e:
                logger.debug(f"Referee fallback error: {e}")
        
        return ref_data
    
    def calculate_referee_score(self, pick: QuantProPick, context: Dict) -> int:
        """Calcule le score basé sur les stats arbitre"""
        score = 0
        
        referee = context.get('referee')
        pick.referee_data = referee
        
        if referee:
            tendency = referee.get('under_over_tendency', 'neutral')
            avg_goals = float(referee.get('avg_goals_per_game', 2.5) or 2.5)
            
            if pick.market_type in ['over_25', 'over_35', 'btts_yes']:
                if tendency == 'over' or avg_goals >= 2.8:
                    score += 8
                    pick.reasons.append(f"👨‍⚖️ Arbitre: {avg_goals:.2f} buts/match")
                elif tendency == 'under' or avg_goals <= 2.2:
                    score -= 6
            elif pick.market_type in ['under_25', 'under_15', 'btts_no']:
                if tendency == 'under' or avg_goals <= 2.2:
                    score += 8
                    pick.reasons.append(f"👨‍⚖️ Arbitre tendency: UNDER")
                elif tendency == 'over' or avg_goals >= 2.8:
                    score -= 6
            
            # Home bias
            home_bias = float(referee.get('home_bias_factor', 1.0) or 1.0)
            if home_bias > 1.05 and pick.market_type in ['home', 'dc_1x']:
                score += 3
                pick.reasons.append(f"👨‍⚖️ Arbitre pro-domicile ({home_bias:.2f})")
            
            if score != 0:
                self.stats['referee_applied'] += 1
        
        return max(-LAYER_WEIGHTS['referee'], min(LAYER_WEIGHTS['referee'], score))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LAYER 5: HEAD TO HEAD (V9.1 - Fuzzy search amélioré)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_h2h_data(self, home_team: str, away_team: str) -> Optional[Dict]:
        """Récupère l'historique des confrontations avec fuzzy search"""
        if not self.conn:
            return None
        
        try:
            home_variants = self._normalize_team_name(home_team)
            away_variants = self._normalize_team_name(away_team)
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Essayer team_head_to_head d'abord
                for hv in home_variants[:3]:
                    for av in away_variants[:3]:
                        cur.execute("""
                            SELECT 
                                team_a, team_b, total_matches,
                                team_a_wins, team_b_wins, draws,
                                avg_total_goals, btts_pct, over_25_pct
                            FROM team_head_to_head
                            WHERE (LOWER(team_a) LIKE %s AND LOWER(team_b) LIKE %s)
                               OR (LOWER(team_a) LIKE %s AND LOWER(team_b) LIKE %s)
                            ORDER BY total_matches DESC
                            LIMIT 1
                        """, (f"%{hv}%", f"%{av}%", f"%{av}%", f"%{hv}%"))
                        
                        row = cur.fetchone()
                        if row:
                            return dict(row)
                
                # Fallback sur head_to_head générique
                for hv in home_variants[:3]:
                    for av in away_variants[:3]:
                        cur.execute("""
                            SELECT 
                                team_a, team_b, total_matches,
                                avg_total_goals, btts_pct, over_25_pct
                            FROM head_to_head
                            WHERE (LOWER(team_a) LIKE %s AND LOWER(team_b) LIKE %s)
                               OR (LOWER(team_a) LIKE %s AND LOWER(team_b) LIKE %s)
                            LIMIT 1
                        """, (f"%{hv}%", f"%{av}%", f"%{av}%", f"%{hv}%"))
                        
                        row = cur.fetchone()
                        if row:
                            return dict(row)
                            
        except Exception as e:
            logger.debug(f"H2H error: {e}")
        return None
    
    def calculate_h2h_score(self, pick: QuantProPick, context: Dict) -> int:
        """Calcule le score basé sur le H2H"""
        score = 0
        
        h2h = context.get('h2h')
        pick.h2h_data = h2h
        
        if h2h:
            total_matches = int(h2h.get('total_matches', 0) or 0)
            btts_pct = float(h2h.get('btts_pct', 50) or 50)
            over25_pct = float(h2h.get('over_25_pct', 50) or 50)
            
            # Multiplicateur si beaucoup de matchs
            conf_mult = 1.2 if total_matches >= 10 else 1.0
            
            if pick.market_type == 'btts_yes':
                if btts_pct >= 65:
                    score += int(8 * conf_mult)
                    pick.reasons.append(f"📜 H2H: BTTS {btts_pct:.0f}% ({total_matches} matchs)")
                elif btts_pct <= 35:
                    score -= 6
            elif pick.market_type == 'btts_no':
                if btts_pct <= 35:
                    score += int(6 * conf_mult)
                elif btts_pct >= 65:
                    score -= 8
            elif pick.market_type in ['over_25', 'over_35']:
                if over25_pct >= 65:
                    score += int(8 * conf_mult)
                    pick.reasons.append(f"📜 H2H: O2.5 {over25_pct:.0f}%")
                elif over25_pct <= 35:
                    score -= 6
            elif pick.market_type in ['under_25', 'under_15']:
                if over25_pct <= 35:
                    score += int(6 * conf_mult)
                elif over25_pct >= 65:
                    score -= 8
            
            if score != 0:
                self.stats['h2h_applied'] += 1
        
        return max(-LAYER_WEIGHTS['h2h'], min(LAYER_WEIGHTS['h2h'], score))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LAYER 6: REALITY CHECK
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_reality_check(self, match_id: str) -> Optional[Dict]:
        """Récupère le reality check d'un match"""
        if not self.conn or not match_id:
            return None
        
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT 
                        match_id, reality_score, class_score, convergence_status
                    FROM reality_check_results
                    WHERE match_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (match_id,))
                
                row = cur.fetchone()
                if row:
                    return dict(row)
        except Exception as e:
            logger.debug(f"Reality check error: {e}")
        return None
    
    def calculate_reality_score(self, pick: QuantProPick, context: Dict) -> int:
        """Calcule le score basé sur le reality check"""
        score = 0
        
        reality = context.get('reality')
        pick.reality_data = reality
        
        if reality:
            convergence = reality.get('convergence_status', '')
            
            if convergence == 'strong_convergence':
                score += 10
                pick.reasons.append("✅ Reality Check: forte convergence")
            elif convergence == 'partial_convergence':
                score += 5
            elif convergence == 'divergence':
                score -= 8
                pick.warnings.append("⚠️ Reality Check: divergence détectée")
            
            if score != 0:
                self.stats['reality_applied'] += 1
        
        return max(-LAYER_WEIGHTS['reality'], min(LAYER_WEIGHTS['reality'], score))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STEAM VALIDATOR (V7)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def check_steam_move(self, match_id: str, market_type: str) -> Optional[Dict]:
        """Vérifie les mouvements steam pour un match/marché"""
        if not self.conn or not match_id:
            return None
        
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT 
                        market_type, move_direction, move_percentage,
                        is_sharp_money, bookmaker
                    FROM fg_sharp_money
                    WHERE match_id = %s AND market_type = %s
                    ORDER BY detected_at DESC
                    LIMIT 1
                """, (match_id, market_type))
                
                row = cur.fetchone()
                if row:
                    return dict(row)
        except Exception as e:
            logger.debug(f"Steam error: {e}")
        return None
    
    def calculate_steam_score(self, pick: QuantProPick, context: Dict) -> int:
        """Calcule le score basé sur les mouvements steam"""
        score = 0
        
        steam = self.check_steam_move(pick.match_id, pick.market_type)
        pick.steam_data = steam
        
        if steam:
            direction = steam.get('move_direction', '')
            move_pct = float(steam.get('move_percentage', 0) or 0)
            is_sharp = steam.get('is_sharp_money', False)
            
            if move_pct >= STEAM_CONFIG['significant_move_pct']:
                if direction == 'shortening':
                    score += STEAM_CONFIG['steam_bonus']
                    pick.reasons.append(f"💨 Steam: cotes en baisse ({move_pct:.1f}%)")
                    self.stats['steam_detected'] += 1
                elif direction == 'drifting':
                    score += STEAM_CONFIG['anti_steam_penalty']
                    pick.warnings.append(f"⚠️ Anti-steam: cotes en hausse ({move_pct:.1f}%)")
        
        return max(-LAYER_WEIGHTS['steam'], min(LAYER_WEIGHTS['steam'], score))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SWEET SPOT (V7)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def calculate_sweet_spot(self, pick: QuantProPick) -> int:
        """Calcule le bonus sweet spot"""
        score = 0
        
        # Vérifier si dans le sweet spot
        if 60 <= pick.layer_score <= 80:
            score += 10
            pick.is_sweet_spot = True
            pick.sweet_spot_reason = "Score dans la zone optimale 60-80"
            self.stats['sweet_spots'] += 1
        
        # Bonus odds optimales
        min_odds, max_odds = SWEET_SPOT_CONFIG['optimal_odds_range']
        if min_odds <= pick.odds <= max_odds:
            score += 5
            if pick.is_sweet_spot:
                pick.sweet_spot_reason += " + Cotes optimales"
        
        return score
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TEAM PROFILES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_team_profile(self, team: str, location: str) -> Optional[Dict]:
        """Récupère le profil marché d'une équipe"""
        if not self.conn:
            return None
        
        try:
            variants = self._normalize_team_name(team)
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                for v in variants[:3]:
                    cur.execute("""
                        SELECT 
                            team_name, location, best_market_type,
                            market_group, win_rate, total_bets, roi
                        FROM team_market_profiles
                        WHERE LOWER(team_name) LIKE %s AND location = %s
                        LIMIT 1
                    """, (f"%{v}%", location))
                    
                    row = cur.fetchone()
                    if row:
                        return dict(row)
        except Exception as e:
            logger.debug(f"Profile error: {e}")
        return None
    
    def get_team_intelligence(self, team: str) -> Optional[Dict]:
        """Récupère l'intelligence équipe"""
        if not self.conn:
            return None
        
        try:
            variants = self._normalize_team_name(team)
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                for v in variants[:3]:
                    cur.execute("""
                        SELECT 
                            team_name, avg_goals_scored, avg_goals_conceded,
                            btts_rate, over_25_rate, clean_sheet_rate
                        FROM team_intelligence
                        WHERE LOWER(team_name) LIKE %s
                        LIMIT 1
                    """, (f"%{v}%",))
                    
                    row = cur.fetchone()
                    if row:
                        return dict(row)
        except Exception as e:
            logger.debug(f"Intel error: {e}")
        return None
    
    def calculate_profile_score(self, pick: QuantProPick, context: Dict) -> int:
        """Calcule le score basé sur les profils équipes"""
        score = 0
        
        home_prof = context.get('home_profile')
        away_prof = context.get('away_profile')
        
        if home_prof:
            pick.home_profile = home_prof.get('best_market_type')
        if away_prof:
            pick.away_profile = away_prof.get('best_market_type')
        
        # Consensus (les 2 équipes ont le même meilleur marché)
        if home_prof and away_prof:
            home_group = home_prof.get('market_group', '')
            away_group = away_prof.get('market_group', '')
            
            market_to_group = {
                'btts_yes': 'btts', 'btts_no': 'btts',
                'over_25': 'goals', 'over_35': 'goals',
                'under_25': 'goals', 'under_15': 'goals',
            }
            
            pick_group = market_to_group.get(pick.market_type, pick.market_type)
            
            if home_group == pick_group and away_group == pick_group:
                score += 12
                pick.profile_consensus = True
                pick.reasons.append(f"🎯 Consensus profil: {pick_group.upper()}")
            elif home_group == pick_group or away_group == pick_group:
                score += 6
        
        return max(-LAYER_WEIGHTS['profile'], min(LAYER_WEIGHTS['profile'], score))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ML PREDICTION (V9.1 - Multiplicateur au lieu d'additif)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def predict_with_ml(self, pick: QuantProPick, context: Dict) -> Tuple[float, str]:
        """Prédit avec le modèle ML - Retourne (confidence, prediction)"""
        if not self.ml_model:
            return 0.5, "NO_MODEL"
        
        try:
            import numpy as np
            
            # Features
            home_intel = context.get('home_intel') or {}
            away_intel = context.get('away_intel') or {}
            
            features = [
                pick.implied_prob,
                pick.odds,
                pick.base_score / 100,
                pick.edge,
                float(home_intel.get('btts_rate', 50) or 50) / 100,
                float(away_intel.get('btts_rate', 50) or 50) / 100,
                float(home_intel.get('over_25_rate', 50) or 50) / 100,
                float(away_intel.get('over_25_rate', 50) or 50) / 100,
                float(home_intel.get('avg_goals_scored', 1.3) or 1.3),
                float(away_intel.get('avg_goals_scored', 1.1) or 1.1),
                float(home_intel.get('avg_goals_conceded', 1.2) or 1.2),
                float(away_intel.get('avg_goals_conceded', 1.3) or 1.3),
                pick.momentum_score / LAYER_WEIGHTS['momentum'],
                pick.tactical_score / LAYER_WEIGHTS['tactical'],
                pick.h2h_score / LAYER_WEIGHTS['h2h'],
                1.0 if pick.profile_consensus else 0.0,
            ]
            
            X = np.array(features).reshape(1, -1)
            
            if self.ml_scaler:
                X = self.ml_scaler.transform(X)
            
            proba = self.ml_model.predict_proba(X)[0]
            confidence = max(proba)
            prediction = "WIN" if proba[1] >= 0.5 else "LOSE"
            
            return confidence, prediction
            
        except Exception as e:
            logger.debug(f"ML prediction error: {e}")
            return 0.5, "ERROR"
    
    def calculate_ml_score(self, pick: QuantProPick, context: Dict) -> Tuple[int, float]:
        """
        V9.1: Calcule le score ML ET le multiplicateur
        Retourne (ml_score, ml_multiplier)
        """
        confidence, prediction = self.predict_with_ml(pick, context)
        
        pick.ml_confidence = confidence
        pick.ml_prediction = prediction
        
        score = 0
        multiplier = 1.0
        
        if prediction == "WIN":
            if confidence >= 0.70:
                score = LAYER_WEIGHTS['ml']
                multiplier = ML_CONFIG['ml_multiplier_high']
                self.stats['ml_applied'] += 1
            elif confidence >= 0.60:
                score = int(LAYER_WEIGHTS['ml'] * 0.6)
                multiplier = ML_CONFIG['ml_multiplier_medium']
                self.stats['ml_applied'] += 1
        elif prediction == "LOSE" and confidence >= 0.65:
            score = -int(LAYER_WEIGHTS['ml'] * 0.75)
            multiplier = ML_CONFIG['ml_multiplier_low']
        
        pick.ml_multiplier = multiplier
        return score, multiplier
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DATA COVERAGE (V9.1)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def calculate_data_coverage(self, pick: QuantProPick) -> Tuple[float, int]:
        """Calcule le % de données disponibles"""
        layers_active = 0
        
        if pick.momentum_score != 0 or pick.home_momentum or pick.away_momentum:
            layers_active += 1
        if pick.tactical_score != 0 or pick.tactical_match:
            layers_active += 1
        if pick.referee_score != 0 or pick.referee_data:
            layers_active += 1
        if pick.h2h_score != 0 or pick.h2h_data:
            layers_active += 1
        if pick.reality_score != 0 or pick.reality_data:
            layers_active += 1
        if self.ml_model and pick.ml_confidence > 0.5:
            layers_active += 1
        
        coverage = layers_active / 6.0
        return coverage, layers_active
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BASE SCORE & KELLY
    # ═══════════════════════════════════════════════════════════════════════════
    
    def calculate_base_score(self, pick: QuantProPick) -> int:
        """Calcule le score de base (V5 calibration)"""
        edge = pick.predicted_prob - pick.implied_prob
        pick.edge = edge
        
        # Score basé sur l'edge
        score = int(edge * 200)
        
        # Market calibration bonus
        market_config = MARKET_CALIBRATION.get(pick.market_type, {'bonus': 0})
        score += market_config['bonus']
        
        # Odds penalty
        for (low, high), multiplier in ODDS_PENALTY.items():
            if low <= pick.odds < high:
                score = int(score * multiplier)
                break
        
        return score
    
    def calculate_kelly(self, pick: QuantProPick) -> float:
        """Calcule le Kelly sizing"""
        if pick.edge <= 0 or pick.odds <= 1:
            return 0.0
        
        kelly = (pick.edge / (pick.odds - 1)) * 100
        return min(kelly, 5.0)  # Cap à 5%
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RECOMMENDATION (V9.1 - Avec data coverage)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_recommendation(self, pick: QuantProPick) -> str:
        """Génère la recommandation finale"""
        
        if pick.trap_detected:
            return "🚫 TRAP DETECTED"
        
        if pick.odds < ML_CONFIG['roi_warning_threshold']:
            return "⚠️ SKIP (cotes < 1.40)"
        
        # Low data warning
        low_data = pick.data_coverage < 0.33
        suffix = " (Low Data)" if low_data else ""
        
        if low_data and pick.final_score >= 50:
            pick.warnings.append(f"⚠️ Confiance réduite ({pick.layers_active}/6 layers)")
        
        # Sweet spot
        if pick.is_sweet_spot and pick.final_score >= 70:
            if pick.data_coverage >= 0.5:
                return "⭐ SWEET SPOT BET"
            return f"⭐ SWEET SPOT{suffix}"
        
        # Score-based
        if pick.final_score >= 80 and pick.ml_confidence >= 0.60 and pick.data_coverage >= 0.5:
            return "🟢 STRONG BET"
        elif pick.final_score >= 80:
            return f"🟢 STRONG{suffix}"
        elif pick.final_score >= 60 and pick.ml_confidence >= 0.55:
            return f"🟢 BET{suffix}"
        elif pick.final_score >= 45 and pick.odds >= 2.0:
            return f"🟡 VALUE BET{suffix}"
        elif pick.final_score >= 35:
            return f"🟡 MODERATE{suffix}"
        elif pick.final_score >= 20:
            return "⚪ WATCH"
        else:
            return "🔴 SKIP"
    
    # ═══════════════════════════════════════════════════════════════════════════
    # POISSON
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _calculate_poisson_probs(self, xg_home: float, xg_away: float) -> Dict[str, float]:
        """Calcule les probabilités Poisson"""
        def poisson(k, lam):
            return (lam ** k) * math.exp(-lam) / math.factorial(k)
        
        probs = {
            'home': 0, 'draw': 0, 'away': 0,
            'btts_yes': 0, 'btts_no': 0,
            'over_15': 0, 'under_15': 0,
            'over_25': 0, 'under_25': 0,
            'over_35': 0, 'under_35': 0,
        }
        
        for h in range(8):
            for a in range(8):
                p = poisson(h, xg_home) * poisson(a, xg_away)
                
                if h > a:
                    probs['home'] += p
                elif h == a:
                    probs['draw'] += p
                else:
                    probs['away'] += p
                
                if h > 0 and a > 0:
                    probs['btts_yes'] += p
                else:
                    probs['btts_no'] += p
                
                total = h + a
                if total > 1.5:
                    probs['over_15'] += p
                else:
                    probs['under_15'] += p
                if total > 2.5:
                    probs['over_25'] += p
                else:
                    probs['under_25'] += p
                if total > 3.5:
                    probs['over_35'] += p
                else:
                    probs['under_35'] += p
        
        probs['dc_1x'] = probs['home'] + probs['draw']
        probs['dc_x2'] = probs['draw'] + probs['away']
        probs['dc_12'] = probs['home'] + probs['away']
        
        return probs
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MAIN ANALYSIS (V9.1 - Optimisé avec Pre-fetch)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def analyze_match(self, match_data: Dict, referee_name: str = None) -> List[QuantProPick]:
        """Analyse complète d'un match avec Pre-fetch context"""
        picks = []
        
        match_id = match_data.get('match_id', '')
        home_team = match_data.get('home_team', '')
        away_team = match_data.get('away_team', '')
        league = match_data.get('league', '')
        odds_dict = match_data.get('odds', {})
        xg_home = match_data.get('xg_home', 1.3)
        xg_away = match_data.get('xg_away', 1.1)
        
        # V9.1: Pre-fetch context (1 fois par match au lieu de N fois par marché)
        context = self._prefetch_match_context(home_team, away_team, match_id, league, referee_name)
        
        # Poisson
        probs = self._calculate_poisson_probs(xg_home, xg_away)
        
        # Analyser chaque marché
        for market_type, odds in odds_dict.items():
            if odds <= 1.0 or odds > 15:
                continue
            
            implied_prob = 1 / odds
            predicted_prob = probs.get(market_type, implied_prob)
            
            pick = QuantProPick(
                match_id=match_id,
                home_team=home_team,
                away_team=away_team,
                league=league,
                market_type=market_type,
                odds=odds,
                predicted_prob=predicted_prob,
                implied_prob=implied_prob,
            )
            
            # Base score
            pick.base_score = self.calculate_base_score(pick)
            
            # ═══════════════════════════════════════════════════════════════
            # 6 LAYERS (utilisant context pré-fetché)
            # ═══════════════════════════════════════════════════════════════
            
            pick.momentum_score = self.calculate_momentum_score(pick, context)
            pick.tactical_score = self.calculate_tactical_score(pick, context)
            
            # TRAP Check
            if self.calculate_trap_score(pick):
                pick.final_score = 0
                pick.recommendation = self.get_recommendation(pick)
                picks.append(pick)
                self.stats['analyzed'] += 1
                continue
            
            pick.referee_score = self.calculate_referee_score(pick, context)
            pick.h2h_score = self.calculate_h2h_score(pick, context)
            pick.reality_score = self.calculate_reality_score(pick, context)
            pick.steam_score = self.calculate_steam_score(pick, context)
            pick.profile_score = self.calculate_profile_score(pick, context)
            
            # ═══════════════════════════════════════════════════════════════
            # V9.1: LAYER SCORE (avant ML)
            # ═══════════════════════════════════════════════════════════════
            
            pick.layer_score = (
                pick.base_score +
                pick.momentum_score +
                pick.tactical_score +
                pick.referee_score +
                pick.h2h_score +
                pick.reality_score +
                pick.profile_score +
                pick.steam_score
            )
            
            # Sweet spot (basé sur layer_score)
            pick.sweet_spot_score = self.calculate_sweet_spot(pick)
            pick.layer_score += pick.sweet_spot_score
            
            # ═══════════════════════════════════════════════════════════════
            # V9.1: ML comme MULTIPLICATEUR (évite double counting)
            # ═══════════════════════════════════════════════════════════════
            
            pick.ml_score, pick.ml_multiplier = self.calculate_ml_score(pick, context)
            
            # Final score = layer_score × ml_multiplier + ml_bonus
            pick.final_score = int(pick.layer_score * pick.ml_multiplier) + pick.ml_score
            
            # Data coverage
            pick.data_coverage, pick.layers_active = self.calculate_data_coverage(pick)
            
            if pick.data_coverage >= 0.5:
                self.stats['high_data_coverage'] += 1
            elif pick.data_coverage < 0.33:
                self.stats['low_data_coverage'] += 1
            
            # Kelly
            pick.kelly = self.calculate_kelly(pick)
            
            # Recommendation
            pick.recommendation = self.get_recommendation(pick)
            
            picks.append(pick)
            self.stats['analyzed'] += 1
        
        return picks
    
    def filter_best_picks(self, picks: List[QuantProPick], max_picks: int = 5) -> List[QuantProPick]:
        """Filtre et retourne les meilleurs picks"""
        valid = [p for p in picks if not p.trap_detected and p.final_score >= 30]
        valid.sort(key=lambda p: (p.is_sweet_spot, p.data_coverage, p.final_score), reverse=True)
        
        self.stats['final_picks'] = min(len(valid), max_picks)
        return valid[:max_picks]
    
    def print_summary(self):
        """Affiche le résumé des stats"""
        print("\n" + "="*70)
        print("📊 ORCHESTRATOR V9.1 QUANT PRO FINAL - RÉSUMÉ")
        print("="*70)
        for key, value in self.stats.items():
            print(f"   {key.replace('_', ' ').title():.<30} {value}")
        print("="*70)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("="*70)
    print("🎯 ORCHESTRATOR V9.1 - QUANT PRO FINAL")
    print("="*70)
    print("Améliorations V9.1:")
    print("  ✅ ML Path Fallback")
    print("  ✅ Data Coverage Indicator")
    print("  ✅ ML as Multiplier (anti double-counting)")
    print("  ✅ Pre-fetch SQL Context")
    print("  ✅ Fuzzy Team Search")
    print("="*70)
    
    orchestrator = OrchestratorV9Quant()
    
    # Test match
    test_match = {
        'match_id': 'test_123',
        'home_team': 'Liverpool',
        'away_team': 'Manchester City',
        'league': 'Premier League',
        'xg_home': 1.6,
        'xg_away': 1.8,
        'odds': {
            'home': 2.80,
            'draw': 3.40,
            'away': 2.50,
            'btts_yes': 1.65,
            'btts_no': 2.10,
            'over_25': 1.70,
            'under_25': 2.05,
            'over_35': 2.40,
            'under_35': 1.55,
        }
    }
    
    print(f"\n📌 Test: {test_match['home_team']} vs {test_match['away_team']}")
    print("-"*70)
    
    picks = orchestrator.analyze_match(test_match, referee_name="Michael Oliver")
    best_picks = orchestrator.filter_best_picks(picks, max_picks=5)
    
    print(f"\n🎯 TOP {len(best_picks)} PICKS:")
    print("-"*70)
    
    for i, pick in enumerate(best_picks, 1):
        sweet = "⭐" if pick.is_sweet_spot else ""
        data_ind = "🟢" if pick.data_coverage >= 0.5 else "🟡" if pick.data_coverage >= 0.33 else "🔴"
        
        print(f"\n#{i} {pick.market_type.upper()} @ {pick.odds} {sweet}")
        print(f"   Score Final: {pick.final_score} | Layer: {pick.layer_score} | Edge: {pick.edge*100:.1f}%")
        print(f"   📊 Data Coverage: {data_ind} {pick.data_coverage*100:.0f}% ({pick.layers_active}/6 layers)")
        print(f"   Layers: Mom={pick.momentum_score} | Tac={pick.tactical_score} | Ref={pick.referee_score} | H2H={pick.h2h_score} | RC={pick.reality_score}")
        print(f"   Profile={pick.profile_score} | Steam={pick.steam_score} | SS={pick.sweet_spot_score}")
        print(f"   🤖 ML: {pick.ml_confidence*100:.1f}% {pick.ml_prediction} (×{pick.ml_multiplier:.2f})")
        print(f"   Kelly: {pick.kelly:.2f}%")
        print(f"   ➜ {pick.recommendation}")
        if pick.reasons:
            for reason in pick.reasons[:3]:
                print(f"      {reason}")
        if pick.warnings:
            for warning in pick.warnings[:2]:
                print(f"      {warning}")
    
    orchestrator.print_summary()
    print("\n✅ Orchestrator V9.1 Quant Pro FINAL prêt!")


if __name__ == "__main__":
    main()

