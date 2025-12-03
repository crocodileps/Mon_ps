#!/usr/bin/env python3
"""
🎯 CLV ORCHESTRATOR V9.0 - QUANT PRO

ÉVOLUTION: Statisticien Amateur → Quant Professionnel

FUSION DES MEILLEURES VERSIONS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DE V5_CALIBRATED (+3.99u ROI):
  ✓ Market Calibration simple et efficace
  ✓ Odds Penalty System
  ✓ Poisson probabilities

DE V7_SMART (infrastructure):
  ✓ Steam Validator
  ✓ Reality Check
  ✓ Sweet Spot scoring
  ✓ Kelly sizing
  ✓ Auto-Learning

NOUVEAU V9 QUANT PRO:
  ✓ 6 LAYERS DE DONNÉES
  ✓ ML Prediction (XGBoost 63% accuracy)
  ✓ Team Market Profiles (70 équipes)
  ✓ ROI Warning (cotes < 1.40 = ROI négatif)

LAYERS INTÉGRÉS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LAYER 1 - MOMENTUM (team_momentum)
  ✓ Forme récente (5 derniers matchs)
  ✓ Streaks (séries en cours)
  ✓ Absences joueurs clés
  ✓ Pression coach

LAYER 2 - TACTICAL (tactical_matrix)
  ✓ Styles de jeu (possession vs counter, etc.)
  ✓ Probabilities BTTS/O25 par confrontation styles
  ✓ Upset probability

LAYER 3 - TRAPS (market_traps)
  ✓ 196 pièges actifs sur 103 équipes
  ✓ Détection automatique
  ✓ Marchés alternatifs suggérés

LAYER 4 - REFEREE (referee_intelligence)
  ✓ Tendency over/under par arbitre
  ✓ Fréquence penalties
  ✓ Sévérité (cartons)

LAYER 5 - H2H (head_to_head + team_head_to_head)
  ✓ Historique confrontations
  ✓ BTTS% et O25% historiques
  ✓ Équipe dominante

LAYER 6 - REALITY CHECK (reality_check_results)
  ✓ Convergence analysis
  ✓ Reality score
  ✓ Class score

ARCHITECTURE V9:
┌─────────────────────────────────────────────────────────────────────────────┐
│                      V9 QUANT PRO - 6 LAYERS PIPELINE                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  LAYER 1        LAYER 2        LAYER 3        LAYER 4        LAYER 5       │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐      │
│  │MOMENTUM │──►│TACTICAL │──►│  TRAP   │──►│ REFEREE │──►│   H2H   │      │
│  │ ±15pts  │   │ ±12pts  │   │ BLOCK   │   │ ±10pts  │   │ ±8pts   │      │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘      │
│       │             │              │             │              │          │
│       ▼             ▼              ▼             ▼              ▼          │
│  ┌─────────────────────────────────────────────────────────────────┐      │
│  │              LAYER 6: REALITY CHECK + ML FUSION                 │      │
│  │         Score = Σ(Layers) + ML_Score + Calibration              │      │
│  └─────────────────────────────────────────────────────────────────┘      │
│                              │                                            │
│                              ▼                                            │
│                      🎯 PICK QUANT PRO                                    │
└───────────────────────────────────────────────────────────────────────────┘
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

# Market Calibration (PROVEN: +3.99u ROI from V5)
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

# Odds Penalty (from V5 - PROVEN)
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
# CONFIGURATION FROM V7 SMART
# ═══════════════════════════════════════════════════════════════════════════════

# Sweet Spot Config (from V7)
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

# Steam Validator Thresholds (from V7)
STEAM_CONFIG = {
    'significant_move_pct': 3.0,  # Mouvement > 3% = steam
    'sharp_books': ['pinnacle', 'betfair', 'sbobet'],
    'steam_bonus': 15,
    'anti_steam_penalty': -20,
}

# ═══════════════════════════════════════════════════════════════════════════════
# LAYER WEIGHTS
# ═══════════════════════════════════════════════════════════════════════════════

LAYER_WEIGHTS = {
    'momentum': 15,      # ±15 points max
    'tactical': 12,      # ±12 points max
    'trap': 100,         # BLOCKING (si trap = skip)
    'referee': 10,       # ±10 points max
    'h2h': 8,            # ±8 points max
    'reality': 10,       # ±10 points max
    'ml': 20,            # ±20 points max
    'profile': 12,       # ±12 points max
    'steam': 15,         # ±15 points (from V7)
    'sweet_spot': 10,    # ±10 points (from V7)
}

# ML Config
ML_CONFIG = {
    'min_confidence': 0.55,
    'min_odds_profitable': 1.65,
    'roi_warning_threshold': 1.40,
    'ml_bonus_high': 20,      # Bonus if ML > 70%
    'ml_bonus_medium': 12,    # Bonus if ML 60-70%
    'ml_penalty_low': -15,    # Penalty if ML < 50%
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASS - PICK QUANT PRO
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class QuantProPick:
    """Pick avec toutes les données Quant Pro"""
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
    
    # ML
    ml_confidence: float = 0.0
    ml_prediction: str = "N/A"
    
    # Profiles
    home_profile: Optional[str] = None
    away_profile: Optional[str] = None
    profile_consensus: bool = False
    
    # Final
    base_score: int = 0
    final_score: int = 0
    kelly: float = 0.0
    edge: float = 0.0
    recommendation: str = "SKIP"
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Sweet Spot
    is_sweet_spot: bool = False
    sweet_spot_reason: str = ""
    
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
            'kelly': f"{self.kelly:.2f}%",
            'edge': f"{self.edge*100:.1f}%",
            'reasons': self.reasons,
            'warnings': self.warnings,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR V9 QUANT PRO
# ═══════════════════════════════════════════════════════════════════════════════

class OrchestratorV9Quant:
    """Orchestrateur Quant Pro avec 6 layers de données + V5/V7 features"""
    
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.conn.autocommit = True
        
        # Stats
        self.stats = {
            'analyzed': 0,
            'momentum_applied': 0,
            'tactical_applied': 0,
            'traps_blocked': 0,
            'referee_applied': 0,
            'h2h_applied': 0,
            'reality_applied': 0,
            'ml_approved': 0,
            'steam_detected': 0,
            'sweet_spots': 0,
            'final_picks': 0,
        }
        
        # Load ML model
        self.ml_model = None
        self.ml_scaler = None
        self._load_ml_model()
        
        logger.info("🎯 Orchestrator V9 Quant Pro initialisé")
    
    def _load_ml_model(self):
        """Charge le modèle ML XGBoost"""
        try:
            import joblib
            model_path = "/home/Mon_ps/ml_smart_quant/models/best_model.joblib"
            scaler_path = "/home/Mon_ps/ml_smart_quant/models/scaler.joblib"
            
            self.ml_model = joblib.load(model_path)
            self.ml_scaler = joblib.load(scaler_path)
            logger.info("✅ Modèle ML chargé (XGBoost)")
        except Exception as e:
            logger.warning(f"⚠️ ML non chargé: {e}")
            self.ml_model = None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LAYER 1: MOMENTUM
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_team_momentum(self, team_name: str) -> Optional[Dict]:
        """Récupère le momentum d'une équipe"""
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT 
                        team_name,
                        momentum_score,
                        momentum_status,
                        last_5_results,
                        current_streak,
                        goals_scored_last_5,
                        goals_conceded_last_5,
                        clean_sheets_last_5,
                        failed_to_score_last_5,
                        key_player_absent,
                        coach_under_pressure,
                        new_coach_bounce
                    FROM team_momentum
                    WHERE LOWER(team_name) LIKE LOWER(%s)
                       OR LOWER(team_name) LIKE LOWER(%s)
                    ORDER BY calculated_at DESC
                    LIMIT 1
                """, (f"%{team_name}%", f"%{team_name.replace(' ', '%')}%"))
                
                row = cur.fetchone()
                if row:
                    return dict(row)
        except Exception as e:
            logger.debug(f"Momentum error for {team_name}: {e}")
        return None
    
    def calculate_momentum_score(self, pick: QuantProPick) -> int:
        """Calcule le score momentum combiné"""
        score = 0
        
        home_mom = self.get_team_momentum(pick.home_team)
        away_mom = self.get_team_momentum(pick.away_team)
        
        pick.home_momentum = home_mom
        pick.away_momentum = away_mom
        
        if home_mom:
            mom_score = home_mom.get('momentum_score', 50) or 50
            mom_status = home_mom.get('momentum_status', 'average')
            
            # Bonus/malus basé sur le statut
            if mom_status == 'excellent' or mom_score >= 80:
                score += 8 if pick.market_type in ['home', 'dc_1x', 'dc_12'] else 3
                pick.reasons.append(f"🔥 {pick.home_team} en excellente forme")
            elif mom_status == 'poor' or mom_score <= 30:
                score -= 8 if pick.market_type in ['home', 'dc_1x', 'dc_12'] else 3
            
            # Facteurs spéciaux
            if home_mom.get('key_player_absent'):
                score -= 5
                pick.warnings.append(f"⚠️ {pick.home_team}: joueur clé absent")
            if home_mom.get('coach_under_pressure'):
                score -= 3
                pick.warnings.append(f"⚠️ {pick.home_team}: coach sous pression")
            if home_mom.get('new_coach_bounce'):
                score += 5
                pick.reasons.append(f"📈 {pick.home_team}: effet nouveau coach")
        
        if away_mom:
            mom_score = away_mom.get('momentum_score', 50) or 50
            mom_status = away_mom.get('momentum_status', 'average')
            
            if mom_status == 'excellent' or mom_score >= 80:
                score += 8 if pick.market_type in ['away', 'dc_x2', 'dc_12'] else 3
                pick.reasons.append(f"🔥 {pick.away_team} en excellente forme")
            elif mom_status == 'poor' or mom_score <= 30:
                score -= 8 if pick.market_type in ['away', 'dc_x2', 'dc_12'] else 3
            
            if away_mom.get('key_player_absent'):
                score -= 5
                pick.warnings.append(f"⚠️ {pick.away_team}: joueur clé absent")
        
        # BTTS/Over boost si les deux équipes marquent beaucoup
        if home_mom and away_mom:
            home_gf = home_mom.get('goals_scored_last_5', 0) or 0
            away_gf = away_mom.get('goals_scored_last_5', 0) or 0
            home_cs = home_mom.get('clean_sheets_last_5', 0) or 0
            away_cs = away_mom.get('clean_sheets_last_5', 0) or 0
            
            if home_gf >= 8 and away_gf >= 8:
                if pick.market_type in ['btts_yes', 'over_25', 'over_35']:
                    score += 7
                    pick.reasons.append("🔥 2 équipes offensives (8+ buts/5 matchs)")
            
            if home_cs >= 3 and away_cs >= 3:
                if pick.market_type in ['btts_no', 'under_25']:
                    score += 5
                    pick.reasons.append("🛡️ 2 équipes défensives (3+ CS/5 matchs)")
        
        if score != 0:
            self.stats['momentum_applied'] += 1
        return max(-LAYER_WEIGHTS['momentum'], min(LAYER_WEIGHTS['momentum'], score))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LAYER 2: TACTICAL MATRIX
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_tactical_match(self, home_style: str, away_style: str) -> Optional[Dict]:
        """Récupère les stats tactiques pour une confrontation de styles"""
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT 
                        style_a, style_b,
                        btts_probability,
                        over_25_probability,
                        under_25_probability,
                        upset_probability,
                        sample_size,
                        confidence_level
                    FROM tactical_matrix
                    WHERE (LOWER(style_a) = LOWER(%s) AND LOWER(style_b) = LOWER(%s))
                       OR (LOWER(style_a) = LOWER(%s) AND LOWER(style_b) = LOWER(%s))
                    ORDER BY sample_size DESC
                    LIMIT 1
                """, (home_style, away_style, away_style, home_style))
                
                row = cur.fetchone()
                if row:
                    return dict(row)
        except Exception as e:
            logger.debug(f"Tactical error: {e}")
        return None
    
    def detect_team_style(self, team_name: str) -> str:
        """Détecte le style de jeu d'une équipe"""
        team_lower = team_name.lower()
        
        # Mapping des styles par équipe (basé sur analyse tactique)
        style_map = {
            'possession': ['barcelona', 'manchester city', 'city', 'bayern', 'ajax', 'arsenal', 'brighton'],
            'counter_attack': ['atletico', 'inter', 'napoli', 'leicester', 'crystal palace', 'wolves'],
            'pressing': ['liverpool', 'dortmund', 'leipzig', 'brentford', 'tottenham', 'atalanta'],
            'gegenpressing': ['liverpool', 'rb leipzig', 'bayer leverkusen', 'leverkusen'],
            'defensive': ['juventus', 'chelsea', 'burnley', 'everton'],
            'attacking': ['real madrid', 'psg', 'paris', 'benfica', 'sporting'],
            'tiki_taka': ['barcelona', 'spain', 'betis'],
        }
        
        for style, keywords in style_map.items():
            for keyword in keywords:
                if keyword in team_lower:
                    return style
        
        return 'balanced'
    
    def calculate_tactical_score(self, pick: QuantProPick) -> int:
        """Calcule le score basé sur la matrice tactique"""
        score = 0
        
        home_style = self.detect_team_style(pick.home_team)
        away_style = self.detect_team_style(pick.away_team)
        
        tactical = self.get_tactical_match(home_style, away_style)
        pick.tactical_match = tactical
        
        if tactical and tactical.get('sample_size', 0) >= 10:
            btts_prob = float(tactical.get('btts_probability', 50) or 50)
            over25_prob = float(tactical.get('over_25_probability', 50) or 50)
            confidence = tactical.get('confidence_level', 'low')
            
            # Bonus si haute confiance
            conf_mult = 1.2 if confidence == 'high' else 1.0
            
            if pick.market_type == 'btts_yes':
                if btts_prob >= 65:
                    score += int(10 * conf_mult)
                    pick.reasons.append(f"📊 Tactique: BTTS {btts_prob:.0f}% ({home_style} vs {away_style})")
                elif btts_prob <= 40:
                    score -= 8
            elif pick.market_type == 'btts_no':
                if btts_prob <= 40:
                    score += int(8 * conf_mult)
                    pick.reasons.append(f"📊 Tactique: NO BTTS {100-btts_prob:.0f}%")
                elif btts_prob >= 65:
                    score -= 10
            elif pick.market_type in ['over_25', 'over_35']:
                if over25_prob >= 65:
                    score += int(10 * conf_mult)
                    pick.reasons.append(f"📊 Tactique: O2.5 {over25_prob:.0f}%")
                elif over25_prob <= 40:
                    score -= 8
            elif pick.market_type in ['under_25', 'under_15']:
                if over25_prob <= 40:
                    score += int(8 * conf_mult)
                    pick.reasons.append(f"📊 Tactique: U2.5 {100-over25_prob:.0f}%")
                elif over25_prob >= 65:
                    score -= 10
            
            if score != 0:
                self.stats['tactical_applied'] += 1
        
        return max(-LAYER_WEIGHTS['tactical'], min(LAYER_WEIGHTS['tactical'], score))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LAYER 3: MARKET TRAPS (BLOCKING)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def check_market_trap(self, team_name: str, market_type: str) -> Tuple[bool, str, str]:
        """Vérifie si un piège existe pour cette équipe/marché"""
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT 
                        alert_level,
                        alert_reason,
                        alternative_market,
                        confidence_score
                    FROM market_traps
                    WHERE is_active = true
                      AND LOWER(team_name) LIKE LOWER(%s)
                      AND LOWER(market_type) = LOWER(%s)
                    ORDER BY confidence_score DESC
                    LIMIT 1
                """, (f"%{team_name}%", market_type))
                
                row = cur.fetchone()
                if row and row['alert_level'] == 'TRAP':
                    return True, row['alert_reason'], row.get('alternative_market', '')
        except Exception as e:
            logger.debug(f"Trap check error: {e}")
        return False, "", ""
    
    def calculate_trap_score(self, pick: QuantProPick) -> bool:
        """Vérifie les pièges - BLOQUANT si trap détecté"""
        
        # Check home team trap
        is_trap, reason, alt = self.check_market_trap(pick.home_team, pick.market_type)
        if is_trap:
            pick.trap_detected = True
            pick.trap_reason = f"{pick.home_team}: {reason}"
            pick.trap_alternative = alt
            pick.warnings.append(f"🚨 TRAP: {pick.home_team} - {reason}")
            if alt:
                pick.warnings.append(f"💡 Alternative suggérée: {alt}")
            self.stats['traps_blocked'] += 1
            return True
        
        # Check away team trap
        is_trap, reason, alt = self.check_market_trap(pick.away_team, pick.market_type)
        if is_trap:
            pick.trap_detected = True
            pick.trap_reason = f"{pick.away_team}: {reason}"
            pick.trap_alternative = alt
            pick.warnings.append(f"🚨 TRAP: {pick.away_team} - {reason}")
            if alt:
                pick.warnings.append(f"💡 Alternative suggérée: {alt}")
            self.stats['traps_blocked'] += 1
            return True
        
        return False
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LAYER 4: REFEREE INTELLIGENCE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_referee_data(self, league: str, referee_name: str = None) -> Optional[Dict]:
        """Récupère les stats arbitre pour la ligue ou l'arbitre spécifique"""
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                if referee_name:
                    cur.execute("""
                        SELECT 
                            referee_name,
                            strictness_level,
                            penalty_frequency,
                            under_over_tendency,
                            avg_goals_per_game,
                            home_bias_factor,
                            matches_officiated
                        FROM referee_intelligence
                        WHERE LOWER(referee_name) LIKE LOWER(%s)
                        LIMIT 1
                    """, (f"%{referee_name}%",))
                else:
                    # Cherche l'arbitre le plus expérimenté de cette ligue
                    cur.execute("""
                        SELECT 
                            referee_name,
                            strictness_level,
                            penalty_frequency,
                            under_over_tendency,
                            avg_goals_per_game,
                            home_bias_factor,
                            matches_officiated
                        FROM referee_intelligence
                        WHERE LOWER(league) LIKE LOWER(%s)
                        ORDER BY matches_officiated DESC
                        LIMIT 1
                    """, (f"%{league}%",))
                
                row = cur.fetchone()
                if row:
                    return dict(row)
        except Exception as e:
            logger.debug(f"Referee error: {e}")
        return None
    
    def calculate_referee_score(self, pick: QuantProPick, referee_name: str = None) -> int:
        """Calcule le score basé sur les stats arbitre"""
        score = 0
        
        referee = self.get_referee_data(pick.league, referee_name)
        pick.referee_data = referee
        
        if referee:
            tendency = referee.get('under_over_tendency', 'neutral')
            avg_goals = float(referee.get('avg_goals_per_game', 2.5) or 2.5)
            
            if pick.market_type in ['over_25', 'over_35', 'btts_yes']:
                if tendency == 'over':
                    score += 8
                    pick.reasons.append(f"👨‍⚖️ Arbitre tendency: OVER ({avg_goals:.2f} buts/match)")
                elif tendency == 'under':
                    score -= 6
                    pick.warnings.append(f"👨‍⚖️ Arbitre tendency: UNDER")
            elif pick.market_type in ['under_25', 'under_15', 'btts_no']:
                if tendency == 'under':
                    score += 8
                    pick.reasons.append(f"👨‍⚖️ Arbitre tendency: UNDER ({avg_goals:.2f} buts/match)")
                elif tendency == 'over':
                    score -= 6
            
            # Home bias
            home_bias = float(referee.get('home_bias_factor', 1.0) or 1.0)
            if home_bias > 1.05 and pick.market_type in ['home', 'dc_1x']:
                score += 3
                pick.reasons.append(f"👨‍⚖️ Arbitre pro-domicile ({home_bias:.2f})")
            elif home_bias < 0.95 and pick.market_type in ['away', 'dc_x2']:
                score += 3
            
            if score != 0:
                self.stats['referee_applied'] += 1
        
        return max(-LAYER_WEIGHTS['referee'], min(LAYER_WEIGHTS['referee'], score))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LAYER 5: HEAD TO HEAD
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_h2h_data(self, home_team: str, away_team: str) -> Optional[Dict]:
        """Récupère l'historique des confrontations"""
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # D'abord essayer team_head_to_head (plus détaillé)
                cur.execute("""
                    SELECT 
                        team_a, team_b,
                        total_matches,
                        team_a_wins, team_b_wins, draws,
                        avg_total_goals,
                        btts_pct,
                        over_25_pct
                    FROM team_head_to_head
                    WHERE (LOWER(team_a) LIKE LOWER(%s) AND LOWER(team_b) LIKE LOWER(%s))
                       OR (LOWER(team_a) LIKE LOWER(%s) AND LOWER(team_b) LIKE LOWER(%s))
                    ORDER BY total_matches DESC
                    LIMIT 1
                """, (f"%{home_team}%", f"%{away_team}%", f"%{away_team}%", f"%{home_team}%"))
                
                row = cur.fetchone()
                if row:
                    return dict(row)
                
                # Fallback sur head_to_head
                cur.execute("""
                    SELECT 
                        team_a, team_b,
                        total_matches,
                        team_a_wins, team_b_wins, draws,
                        avg_total_goals,
                        btts_percentage as btts_pct,
                        over_25_percentage as over_25_pct
                    FROM head_to_head
                    WHERE (LOWER(team_a) LIKE LOWER(%s) AND LOWER(team_b) LIKE LOWER(%s))
                       OR (LOWER(team_a) LIKE LOWER(%s) AND LOWER(team_b) LIKE LOWER(%s))
                    LIMIT 1
                """, (f"%{home_team}%", f"%{away_team}%", f"%{away_team}%", f"%{home_team}%"))
                
                row = cur.fetchone()
                if row:
                    return dict(row)
        except Exception as e:
            logger.debug(f"H2H error: {e}")
        return None
    
    def calculate_h2h_score(self, pick: QuantProPick) -> int:
        """Calcule le score basé sur l'historique H2H"""
        score = 0
        
        h2h = self.get_h2h_data(pick.home_team, pick.away_team)
        pick.h2h_data = h2h
        
        if h2h and h2h.get('total_matches', 0) >= 3:
            btts_pct = float(h2h.get('btts_pct', 50) or 50)
            over25_pct = float(h2h.get('over_25_pct', 50) or 50)
            total_matches = h2h.get('total_matches', 0)
            
            # Bonus confiance si beaucoup de matchs
            conf_mult = 1.2 if total_matches >= 10 else 1.0
            
            if pick.market_type == 'btts_yes':
                if btts_pct >= 70:
                    score += int(8 * conf_mult)
                    pick.reasons.append(f"📜 H2H: {btts_pct:.0f}% BTTS ({total_matches} matchs)")
                elif btts_pct <= 30:
                    score -= 6
            elif pick.market_type == 'btts_no':
                if btts_pct <= 30:
                    score += int(6 * conf_mult)
                    pick.reasons.append(f"📜 H2H: {100-btts_pct:.0f}% NO BTTS")
                elif btts_pct >= 70:
                    score -= 8
            elif pick.market_type in ['over_25', 'over_35']:
                if over25_pct >= 70:
                    score += int(8 * conf_mult)
                    pick.reasons.append(f"📜 H2H: {over25_pct:.0f}% O2.5 ({total_matches} matchs)")
                elif over25_pct <= 35:
                    score -= 6
            elif pick.market_type in ['under_25', 'under_15']:
                if over25_pct <= 35:
                    score += int(6 * conf_mult)
                    pick.reasons.append(f"📜 H2H: {100-over25_pct:.0f}% U2.5")
                elif over25_pct >= 70:
                    score -= 8
            
            if score != 0:
                self.stats['h2h_applied'] += 1
        
        return max(-LAYER_WEIGHTS['h2h'], min(LAYER_WEIGHTS['h2h'], score))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LAYER 6: REALITY CHECK
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_reality_check(self, match_id: str) -> Optional[Dict]:
        """Récupère le reality check pour un match"""
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT 
                        reality_score,
                        class_score,
                        convergence_status
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
    
    def calculate_reality_score(self, pick: QuantProPick) -> int:
        """Calcule le score basé sur le reality check"""
        score = 0
        
        reality = self.get_reality_check(pick.match_id)
        pick.reality_data = reality
        
        if reality:
            convergence = reality.get('convergence_status', '')
            reality_score = int(reality.get('reality_score', 50) or 50)
            class_score = int(reality.get('class_score', 50) or 50)
            
            if convergence == 'strong_convergence':
                score += 10
                pick.reasons.append("✅ Reality Check: forte convergence")
            elif convergence == 'partial_convergence':
                score += 5
            elif convergence == 'divergence':
                score -= 8
                pick.warnings.append("⚠️ Reality Check: divergence détectée")
            
            # Bonus si scores élevés
            if reality_score >= 70 and class_score >= 70:
                score += 5
            
            if score != 0:
                self.stats['reality_applied'] += 1
        
        return max(-LAYER_WEIGHTS['reality'], min(LAYER_WEIGHTS['reality'], score))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STEAM VALIDATOR (FROM V7)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def check_steam_move(self, match_id: str, market_type: str) -> Optional[Dict]:
        """Vérifie les mouvements steam sur ce match/marché"""
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT 
                        movement_pct,
                        movement_direction,
                        is_sharp_move,
                        opening_odds,
                        current_odds
                    FROM fg_sharp_money
                    WHERE match_id = %s
                      AND LOWER(market_type) = LOWER(%s)
                    ORDER BY detected_at DESC
                    LIMIT 1
                """, (match_id, market_type))
                
                row = cur.fetchone()
                if row:
                    return dict(row)
        except Exception as e:
            logger.debug(f"Steam check error: {e}")
        return None
    
    def calculate_steam_score(self, pick: QuantProPick) -> int:
        """Calcule le score basé sur les mouvements steam"""
        score = 0
        
        steam = self.check_steam_move(pick.match_id, pick.market_type)
        pick.steam_data = steam
        
        if steam and steam.get('is_sharp_move'):
            movement_pct = abs(float(steam.get('movement_pct', 0) or 0))
            direction = steam.get('movement_direction', '')
            
            if movement_pct >= STEAM_CONFIG['significant_move_pct']:
                if direction == 'shortening':
                    # Les cotes baissent = argent sharp sur ce marché
                    score += STEAM_CONFIG['steam_bonus']
                    pick.reasons.append(f"🎯 Steam détecté: cotes en baisse ({movement_pct:.1f}%)")
                    self.stats['steam_detected'] += 1
                elif direction == 'drifting':
                    # Les cotes montent = argent sharp contre ce marché
                    score -= STEAM_CONFIG['anti_steam_penalty']
                    pick.warnings.append(f"⚠️ Anti-steam: cotes en hausse ({movement_pct:.1f}%)")
        
        return max(-LAYER_WEIGHTS['steam'], min(LAYER_WEIGHTS['steam'], score))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SWEET SPOT (FROM V7)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def calculate_sweet_spot(self, pick: QuantProPick) -> int:
        """Vérifie si le pick est dans la zone Sweet Spot"""
        score = 0
        
        # Vérifier les critères Sweet Spot
        optimal_low, optimal_high = SWEET_SPOT_CONFIG['optimal_odds_range']
        
        # Score dans range optimal (60-80) ?
        for (low, high), config in SWEET_SPOT_CONFIG['score_ranges'].items():
            if low <= pick.base_score < high:
                if config['multiplier'] > 1.0:
                    score += 10
                    pick.is_sweet_spot = True
                    pick.sweet_spot_reason = config['reason']
                    pick.reasons.append(f"🎯 Sweet Spot: {config['reason']}")
                    self.stats['sweet_spots'] += 1
                break
        
        # Cotes dans range optimal ?
        if optimal_low <= pick.odds <= optimal_high and pick.is_sweet_spot:
            score += 5
            pick.reasons.append(f"🎯 Cotes optimales ({pick.odds:.2f})")
        
        return max(-LAYER_WEIGHTS['sweet_spot'], min(LAYER_WEIGHTS['sweet_spot'], score))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ML PREDICTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_team_intelligence(self, team_name: str) -> Optional[Dict]:
        """Récupère les stats team_intelligence"""
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT 
                        home_goals_scored_avg,
                        home_goals_conceded_avg,
                        home_btts_rate,
                        home_over25_rate,
                        away_goals_scored_avg,
                        away_goals_conceded_avg,
                        away_btts_rate,
                        away_over25_rate
                    FROM team_intelligence
                    WHERE LOWER(team_name) LIKE LOWER(%s)
                    LIMIT 1
                """, (f"%{team_name}%",))
                
                row = cur.fetchone()
                if row:
                    return dict(row)
        except Exception as e:
            logger.debug(f"Team intelligence error: {e}")
        return None
    
    def predict_with_ml(self, pick: QuantProPick) -> Tuple[float, str]:
        """Prédiction ML XGBoost avec les 25 features"""
        if not self.ml_model:
            return 0.5, "NO_MODEL"
        
        try:
            import numpy as np
            import pandas as pd
            
            # Récupérer team intelligence
            ti_home = self.get_team_intelligence(pick.home_team) or {}
            ti_away = self.get_team_intelligence(pick.away_team) or {}
            
            # Calculer features
            btts_likelihood = (
                float(ti_home.get('home_btts_rate', 50) or 50) + 
                float(ti_away.get('away_btts_rate', 50) or 50)
            ) / 200
            
            over25_likelihood = (
                float(ti_home.get('home_over25_rate', 50) or 50) + 
                float(ti_away.get('away_over25_rate', 50) or 50)
            ) / 200
            
            team_goals_diff = (
                float(ti_home.get('home_goals_scored_avg', 1.3) or 1.3) - 
                float(ti_away.get('away_goals_scored_avg', 1.1) or 1.1)
            )
            
            # Features dans le même ordre que l'entraînement
            feature_names = [
                'implied_prob', 'odds_taken', 'diamond_score', 'edge_pct',
                'ev_expected', 'predicted_prob', 'hours_before_match',
                'odds_value', 'clv_positive', 'high_diamond', 'steam_detected',
                'prob_x_diamond', 'edge_x_odds', 'timing_factor',
                'team_goals_diff', 'btts_likelihood', 'over25_likelihood',
                'reality_class_combo', 'tier_advantage', 'convergence_encoded',
                'profile_consensus', 'profile_profit_sum',
                'market_encoded', 'league_encoded', 'source_encoded'
            ]
            
            features = pd.DataFrame([[
                pick.implied_prob,
                pick.odds,
                pick.base_score,
                pick.edge * 100,
                pick.edge * pick.odds - 1,
                pick.predicted_prob,
                12,  # hours_before_match (default)
                pick.odds - 1.5,
                1 if pick.edge > 0 else 0,
                1 if pick.base_score >= 60 else 0,
                1 if pick.steam_score > 0 else 0,
                pick.predicted_prob * pick.base_score,
                pick.edge * pick.odds,
                1.0,  # timing_factor
                team_goals_diff,
                btts_likelihood,
                over25_likelihood,
                0,  # reality_class_combo
                0,  # tier_advantage
                1 if pick.reality_data and pick.reality_data.get('convergence_status') == 'strong_convergence' else 0,
                1 if pick.profile_consensus else 0,
                0,  # profile_profit_sum
                0,  # market_encoded
                0,  # league_encoded
                0,  # source_encoded
            ]], columns=feature_names)
            
            features_scaled = self.ml_scaler.transform(features)
            proba = self.ml_model.predict_proba(features_scaled)[0]
            confidence = max(proba)
            prediction = "WIN" if proba[1] > 0.5 else "LOSE"
            
            return confidence, prediction
            
        except Exception as e:
            logger.debug(f"ML prediction error: {e}")
            return 0.5, "ERROR"
    
    def calculate_ml_score(self, pick: QuantProPick) -> int:
        """Calcule le score ML"""
        score = 0
        
        confidence, prediction = self.predict_with_ml(pick)
        pick.ml_confidence = confidence
        pick.ml_prediction = prediction
        
        if prediction == "WIN":
            if confidence >= 0.70:
                score += ML_CONFIG['ml_bonus_high']
                pick.reasons.append(f"🧠 ML: {confidence*100:.0f}% confiance WIN")
                self.stats['ml_approved'] += 1
            elif confidence >= 0.60:
                score += ML_CONFIG['ml_bonus_medium']
                self.stats['ml_approved'] += 1
            elif confidence >= 0.55:
                score += 5
        else:
            if confidence >= 0.65:
                score += ML_CONFIG['ml_penalty_low']
                pick.warnings.append(f"🧠 ML prédit LOSE ({confidence*100:.0f}%)")
            elif confidence >= 0.55:
                score -= 8
        
        return max(-LAYER_WEIGHTS['ml'], min(LAYER_WEIGHTS['ml'], score))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TEAM PROFILES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_team_profile(self, team_name: str, location: str = 'home') -> Optional[Dict]:
        """Récupère le profil marché d'une équipe"""
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT 
                        best_market,
                        best_market_group,
                        win_rate,
                        profit,
                        picks_count,
                        composite_score
                    FROM team_market_profiles
                    WHERE LOWER(team_name) LIKE LOWER(%s)
                      AND location = %s
                    ORDER BY picks_count DESC
                    LIMIT 1
                """, (f"%{team_name}%", location))
                
                row = cur.fetchone()
                if row:
                    return dict(row)
        except Exception as e:
            logger.debug(f"Profile error: {e}")
        return None
    
    def calculate_profile_score(self, pick: QuantProPick) -> int:
        """Calcule le score basé sur les profils d'équipes"""
        score = 0
        
        home_profile = self.get_team_profile(pick.home_team, 'home')
        away_profile = self.get_team_profile(pick.away_team, 'away')
        
        pick.home_profile = home_profile.get('best_market') if home_profile else None
        pick.away_profile = away_profile.get('best_market') if away_profile else None
        
        # Consensus
        if home_profile and away_profile:
            if home_profile.get('best_market_group') == away_profile.get('best_market_group'):
                pick.profile_consensus = True
                if home_profile.get('best_market') == pick.market_type:
                    score += 12
                    pick.reasons.append(f"🎯 Consensus profils: {home_profile.get('best_market')}")
        
        # Match individuel
        if home_profile and home_profile.get('best_market') == pick.market_type:
            wr = home_profile.get('win_rate', 0) or 0
            if wr >= 0.55:
                score += 6
                pick.reasons.append(f"📊 {pick.home_team} profil: {pick.market_type} ({wr*100:.0f}% WR)")
        
        if away_profile and away_profile.get('best_market') == pick.market_type:
            wr = away_profile.get('win_rate', 0) or 0
            if wr >= 0.55:
                score += 6
        
        return max(-LAYER_WEIGHTS['profile'], min(LAYER_WEIGHTS['profile'], score))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SCORE FINAL & RECOMMENDATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def calculate_base_score(self, pick: QuantProPick) -> int:
        """Calcule le score de base (edge + calibration + odds penalty)"""
        score = 0
        
        # Edge Poisson
        pick.edge = pick.predicted_prob - pick.implied_prob
        score += int(pick.edge * 100 * 2)
        
        # Market Calibration (from V5)
        calib = MARKET_CALIBRATION.get(pick.market_type, {'bonus': 0})
        score += calib['bonus']
        
        # Odds Penalty (from V5)
        for (low, high), factor in ODDS_PENALTY.items():
            if low <= pick.odds < high:
                score = int(score * factor)
                break
        
        return score
    
    def calculate_kelly(self, pick: QuantProPick) -> float:
        """Calcule le Kelly Criterion"""
        if pick.edge <= 0 or pick.odds <= 1:
            return 0.0
        
        kelly = (pick.edge / (pick.odds - 1)) * 100
        return min(kelly, 5.0)  # Cap à 5%
    
    def get_recommendation(self, pick: QuantProPick) -> str:
        """Génère la recommandation finale"""
        
        # TRAP = SKIP obligatoire
        if pick.trap_detected:
            return "🚫 TRAP DETECTED"
        
        # ROI Warning
        if pick.odds < ML_CONFIG['roi_warning_threshold']:
            return "⚠️ SKIP (cotes trop basses)"
        
        # Sweet Spot prioritaire
        if pick.is_sweet_spot and pick.final_score >= 70 and pick.ml_confidence >= 0.60:
            return "⭐ SWEET SPOT BET"
        
        # Score-based recommendations
        if pick.final_score >= 80 and pick.ml_confidence >= 0.65:
            return "🟢 STRONG BET"
        elif pick.final_score >= 60 and pick.ml_confidence >= 0.55:
            return "🟢 BET"
        elif pick.final_score >= 45 and pick.odds >= 2.0:
            return "🟡 VALUE BET"
        elif pick.final_score >= 35:
            return "🟡 MODERATE"
        elif pick.final_score >= 20:
            return "⚪ WATCH"
        else:
            return "🔴 SKIP"
    
    # ═══════════════════════════════════════════════════════════════════════════
    # POISSON PROBABILITIES
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
        
        # Double Chance
        probs['dc_1x'] = probs['home'] + probs['draw']
        probs['dc_x2'] = probs['draw'] + probs['away']
        probs['dc_12'] = probs['home'] + probs['away']
        
        return probs
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MAIN ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def analyze_match(self, match_data: Dict, referee_name: str = None) -> List[QuantProPick]:
        """Analyse complète d'un match avec tous les layers"""
        picks = []
        
        match_id = match_data.get('match_id', '')
        home_team = match_data.get('home_team', '')
        away_team = match_data.get('away_team', '')
        league = match_data.get('league', '')
        odds_dict = match_data.get('odds', {})
        xg_home = match_data.get('xg_home', 1.3)
        xg_away = match_data.get('xg_away', 1.1)
        
        # Calcul probabilités Poisson
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
            # 6 LAYERS + V7 FEATURES
            # ═══════════════════════════════════════════════════════════════
            
            # LAYER 1: Momentum
            pick.momentum_score = self.calculate_momentum_score(pick)
            
            # LAYER 2: Tactical
            pick.tactical_score = self.calculate_tactical_score(pick)
            
            # LAYER 3: Trap Check (BLOCKING)
            if self.calculate_trap_score(pick):
                pick.final_score = 0
                pick.recommendation = self.get_recommendation(pick)
                picks.append(pick)
                self.stats['analyzed'] += 1
                continue
            
            # LAYER 4: Referee
            pick.referee_score = self.calculate_referee_score(pick, referee_name)
            
            # LAYER 5: H2H
            pick.h2h_score = self.calculate_h2h_score(pick)
            
            # LAYER 6: Reality Check
            pick.reality_score = self.calculate_reality_score(pick)
            
            # Steam Validator (V7)
            pick.steam_score = self.calculate_steam_score(pick)
            
            # Profile Score
            pick.profile_score = self.calculate_profile_score(pick)
            
            # ML Score (après profile pour avoir consensus)
            pick.ml_score = self.calculate_ml_score(pick)
            
            # Sweet Spot (V7)
            pick.sweet_spot_score = self.calculate_sweet_spot(pick)
            
            # ═══════════════════════════════════════════════════════════════
            # FINAL SCORE
            pick.final_score = (
                pick.base_score +
                pick.momentum_score +
                pick.tactical_score +
                pick.referee_score +
                pick.h2h_score +
                pick.reality_score +
                pick.ml_score +
                pick.profile_score +
                pick.steam_score +
                pick.sweet_spot_score
            )
            
            # Kelly
            pick.kelly = self.calculate_kelly(pick)
            
            # Recommendation
            pick.recommendation = self.get_recommendation(pick)
            
            picks.append(pick)
            self.stats['analyzed'] += 1
        
        return picks
    
    def filter_best_picks(self, picks: List[QuantProPick], max_picks: int = 5) -> List[QuantProPick]:
        """Filtre et retourne les meilleurs picks"""
        # Exclure les TRAP et SKIP
        valid = [p for p in picks if not p.trap_detected and p.final_score >= 30]
        
        # Trier par score final décroissant
        valid.sort(key=lambda p: (p.is_sweet_spot, p.final_score), reverse=True)
        
        self.stats['final_picks'] = min(len(valid), max_picks)
        return valid[:max_picks]
    
    def print_summary(self):
        """Affiche le résumé des statistiques"""
        print("\n" + "="*70)
        print("📊 ORCHESTRATOR V9 QUANT PRO - RÉSUMÉ")
        print("="*70)
        for key, value in self.stats.items():
            print(f"   {key.replace('_', ' ').title():.<30} {value}")
        print("="*70)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("="*70)
    print("🎯 ORCHESTRATOR V9 - QUANT PRO")
    print("="*70)
    
    orchestrator = OrchestratorV9Quant()
    
    # Test avec un match exemple
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
    
    picks = orchestrator.analyze_match(test_match)
    best_picks = orchestrator.filter_best_picks(picks, max_picks=5)
    
    print(f"\n🎯 TOP {len(best_picks)} PICKS:")
    print("-"*70)
    
    for i, pick in enumerate(best_picks, 1):
        sweet = "⭐" if pick.is_sweet_spot else ""
        print(f"\n#{i} {pick.market_type.upper()} @ {pick.odds} {sweet}")
        print(f"   Score Final: {pick.final_score} | Edge: {pick.edge*100:.1f}%")
        print(f"   Layers: Mom={pick.momentum_score} | Tac={pick.tactical_score} | Ref={pick.referee_score} | H2H={pick.h2h_score} | RC={pick.reality_score}")
        print(f"   ML={pick.ml_score} | Prof={pick.profile_score} | Steam={pick.steam_score} | SS={pick.sweet_spot_score}")
        print(f"   ML: {pick.ml_confidence*100:.1f}% - {pick.ml_prediction}")
        print(f"   Kelly: {pick.kelly:.2f}%")
        print(f"   ➜ {pick.recommendation}")
        if pick.reasons:
            for reason in pick.reasons[:3]:
                print(f"      {reason}")
        if pick.warnings:
            for warning in pick.warnings[:2]:
                print(f"      {warning}")
    
    orchestrator.print_summary()
    print("\n✅ Orchestrator V9 Quant Pro prêt!")


if __name__ == "__main__":
    main()

