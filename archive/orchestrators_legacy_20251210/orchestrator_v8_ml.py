#!/usr/bin/env python3
"""
🤖 CLV ORCHESTRATOR V8.0 - ML INTEGRATED

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

NOUVEAU V8:
  ✓ ML Prediction (XGBoost 63% accuracy)
  ✓ Team Market Profiles (70 équipes)
  ✓ ROI Warning (cotes < 1.40 = ROI négatif)
  ✓ Consensus Team Profiles

ARCHITECTURE V8:
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATOR V8 PIPELINE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  📊 DATA        🧠 ML          🎯 PROFILE      ⚖️ SCORE       🎲 DECISION  │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐     ┌─────────┐    ┌─────────┐    │
│  │ Match   │──►│ XGBoost │──►│ Team    │────►│ Combine │───►│ Filter  │    │
│  │ Data    │   │ Predict │   │ Profile │     │ Scores  │    │ & Rank  │    │
│  └─────────┘   └─────────┘   └─────────┘     └─────────┘    └─────────┘    │
│       │             │              │               │              │         │
│       ▼             ▼              ▼               ▼              ▼         │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐     ┌─────────┐    ┌─────────┐    │
│  │ Poisson │   │ Conf %  │   │ Best    │     │ Reality │    │ TOP     │    │
│  │ Probs   │   │ + ROI   │   │ Market  │     │ Check   │    │ PICKS   │    │
│  └─────────┘   └─────────┘   └─────────┘     └─────────┘    └─────────┘    │
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
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

# ML imports
try:
    import joblib
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('OrchestratorV8')

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
}

MODEL_DIR = '/home/Mon_ps/backend/ml/models'

# ════════════════════════════════════════════════════════════════════════════
# CALIBRATION V5 (prouvée +3.99u)
# ════════════════════════════════════════════════════════════════════════════

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

# ════════════════════════════════════════════════════════════════════════════
# ML THRESHOLDS (optimisés sur backtest)
# ════════════════════════════════════════════════════════════════════════════

ML_CONFIG = {
    'min_confidence': 0.60,  # 60% minimum
    'min_odds_profitable': 1.70,  # Cotes min pour ROI positif
    'roi_warning_threshold': 1.40,  # Warning si < 1.40
    'ml_bonus_high': 15,  # Bonus si ML > 70%
    'ml_bonus_medium': 8,  # Bonus si ML 60-70%
    'ml_penalty_low': -10,  # Pénalité si ML < 50%
    'profile_consensus_bonus': 12,  # Bonus si consensus équipes
    'profile_match_bonus': 8,  # Bonus si marché = profil équipe
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
    
    home_win = sum(v for (h, a), v in matrix.items() if h > a)
    draw = sum(v for (h, a), v in matrix.items() if h == a)
    away_win = sum(v for (h, a), v in matrix.items() if h < a)
    btts = sum(v for (h, a), v in matrix.items() if h > 0 and a > 0)
    over_25 = sum(v for (h, a), v in matrix.items() if h + a > 2)
    over_15 = sum(v for (h, a), v in matrix.items() if h + a > 1)
    over_35 = sum(v for (h, a), v in matrix.items() if h + a > 3)
    
    return {
        'home': home_win,
        'draw': draw,
        'away': away_win,
        'btts_yes': btts,
        'btts_no': 1 - btts,
        'over_15': over_15,
        'over_25': over_25,
        'over_35': over_35,
        'under_15': 1 - over_15,
        'under_25': 1 - over_25,
        'under_35': 1 - over_35,
        'dc_1x': home_win + draw,
        'dc_x2': draw + away_win,
        'dc_12': home_win + away_win,
    }


@dataclass
class SmartPickV8:
    """Pick enrichi avec ML et Team Profile"""
    match_id: str
    home_team: str
    away_team: str
    league: str
    market_type: str
    odds: float
    predicted_prob: float
    implied_prob: float
    
    # Scores
    base_score: int = 0
    ml_score: float = 0.0
    ml_confidence: float = 0.0
    profile_score: int = 0
    final_score: int = 0
    
    # ML
    ml_prediction: str = "N/A"
    ml_should_bet: bool = False
    roi_warning: Optional[str] = None
    
    # Team Profiles
    home_profile: Optional[str] = None
    away_profile: Optional[str] = None
    profile_consensus: bool = False
    market_matches_profile: bool = False
    
    # Decision
    kelly: float = 0.0
    recommendation: str = "SKIP"
    reasons: List[str] = field(default_factory=list)


class OrchestratorV8ML:
    """
    🤖 Orchestrator V8 avec ML intégré
    
    Combine:
    - Calibration V5 (prouvée rentable)
    - Infrastructure V7 (Steam, Reality Check)
    - ML Prediction (XGBoost)
    - Team Market Profiles
    """
    
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.ml_model = None
        self.ml_scaler = None
        self.load_ml_model()
        
        self.stats = {
            'analyzed': 0,
            'ml_approved': 0,
            'profile_matched': 0,
            'consensus_found': 0,
            'roi_warnings': 0,
            'final_picks': 0
        }
    
    def load_ml_model(self):
        """Charge le modèle ML"""
        if not ML_AVAILABLE:
            logger.warning("joblib non disponible - ML désactivé")
            return
        
        try:
            model_path = f"{MODEL_DIR}/best_model.joblib"
            scaler_path = f"{MODEL_DIR}/scaler.joblib"
            
            if os.path.exists(model_path) and os.path.exists(scaler_path):
                self.ml_model = joblib.load(model_path)
                self.ml_scaler = joblib.load(scaler_path)
                logger.info("✅ Modèle ML chargé (XGBoost)")
            else:
                logger.warning("⚠️ Modèle ML non trouvé")
        except Exception as e:
            logger.error(f"Erreur chargement ML: {e}")
    
    def get_team_profile(self, team_name: str, location: str) -> Optional[Dict]:
        """Récupère le profil marché d'une équipe"""
        cur = self.conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT best_market, best_market_group, win_rate, profit, picks_count
            FROM team_market_profiles
            WHERE team_name ILIKE %s AND location = %s
        """, (f"%{team_name}%", location))
        result = cur.fetchone()
        cur.close()
        return dict(result) if result else None
    
    def get_team_intelligence(self, team_name: str) -> Dict:
        """Récupère les stats d'une équipe"""
        cur = self.conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT home_goals_scored_avg, home_btts_rate, home_over25_rate,
                   away_goals_scored_avg, away_btts_rate, away_over25_rate
            FROM team_intelligence
            WHERE team_name ILIKE %s
        """, (f"%{team_name}%",))
        result = cur.fetchone()
        cur.close()
        return dict(result) if result else {}
    
    def predict_with_ml(self, pick: SmartPickV8, ti_home: Dict, ti_away: Dict) -> Tuple[float, str, bool]:
        """
        Utilise le modèle ML pour prédire
        
        Returns:
            (confidence, prediction, should_bet)
        """
        if self.ml_model is None:
            return 0.5, "N/A", False
        
        try:
            # Préparer features (même ordre que training)
            implied_prob = 1 / pick.odds if pick.odds > 0 else 0.5
            
            features = {
                'implied_prob': implied_prob,
                'odds_taken': pick.odds,
                'diamond_score': 50,  # Default
                'edge_pct': (pick.predicted_prob - implied_prob) * 100 if pick.predicted_prob else 0,
                'ev_expected': 0,
                'predicted_prob': pick.predicted_prob or implied_prob,
                'hours_before_match': 24,
                'odds_value': (pick.predicted_prob or implied_prob) - implied_prob,
                'clv_positive': 1 if pick.predicted_prob and pick.predicted_prob > implied_prob else 0,
                'high_diamond': 0,
                'steam_detected': 0,
                'prob_x_diamond': implied_prob * 50 / 100,
                'edge_x_odds': 0,
                'timing_factor': np.log1p(24),
                'team_goals_diff': ti_home.get('home_goals_scored_avg', 1.5) - ti_away.get('away_goals_scored_avg', 1.0),
                'btts_likelihood': (ti_home.get('home_btts_rate', 50) + ti_away.get('away_btts_rate', 50)) / 2,
                'over25_likelihood': (ti_home.get('home_over25_rate', 50) + ti_away.get('away_over25_rate', 50)) / 2,
                'reality_class_combo': 50 * 50 / 100,
                'tier_advantage': 0,
                'convergence_encoded': 1,
                'profile_consensus': 1 if pick.profile_consensus else 0,
                'profile_profit_sum': 0,
                'market_encoded': 0,
                'league_encoded': 0,
                'source_encoded': 0
            }
            
            feature_order = [
                'implied_prob', 'odds_taken', 'diamond_score', 'edge_pct',
                'ev_expected', 'predicted_prob', 'hours_before_match',
                'odds_value', 'clv_positive', 'high_diamond', 'steam_detected',
                'prob_x_diamond', 'edge_x_odds', 'timing_factor',
                'team_goals_diff', 'btts_likelihood', 'over25_likelihood',
                'reality_class_combo', 'tier_advantage', 'convergence_encoded',
                'profile_consensus', 'profile_profit_sum',
                'market_encoded', 'league_encoded', 'source_encoded'
            ]
            
            X = np.array([[features[f] for f in feature_order]])
            X_scaled = self.ml_scaler.transform(X)
            
            win_proba = self.ml_model.predict_proba(X_scaled)[0][1]
            prediction = "WIN" if win_proba >= 0.5 else "LOSS"
            
            # Should bet selon seuils optimisés
            should_bet = (
                win_proba >= ML_CONFIG['min_confidence'] and
                pick.odds >= ML_CONFIG['min_odds_profitable']
            )
            
            return float(win_proba), prediction, should_bet
            
        except Exception as e:
            logger.error(f"Erreur ML prediction: {e}")
            return 0.5, "ERROR", False
    
    def calculate_score(self, pick: SmartPickV8) -> SmartPickV8:
        """
        Calcule le score final combinant tous les facteurs
        """
        self.stats['analyzed'] += 1
        
        # 1. Récupérer Team Profiles
        home_profile = self.get_team_profile(pick.home_team, 'home')
        away_profile = self.get_team_profile(pick.away_team, 'away')
        
        if home_profile:
            pick.home_profile = home_profile.get('best_market_group')
        if away_profile:
            pick.away_profile = away_profile.get('best_market_group')
        
        # 2. Vérifier consensus
        if pick.home_profile and pick.away_profile:
            pick.profile_consensus = pick.home_profile == pick.away_profile
            if pick.profile_consensus:
                self.stats['consensus_found'] += 1
        
        # 3. Vérifier si marché = profil
        market_group = self.get_market_group(pick.market_type)
        pick.market_matches_profile = (
            market_group == pick.home_profile or
            market_group == pick.away_profile
        )
        if pick.market_matches_profile:
            self.stats['profile_matched'] += 1
        
        # 4. Team Intelligence
        ti_home = self.get_team_intelligence(pick.home_team)
        ti_away = self.get_team_intelligence(pick.away_team)
        
        # 5. ML Prediction
        ml_conf, ml_pred, ml_should = self.predict_with_ml(pick, ti_home, ti_away)
        pick.ml_confidence = ml_conf
        pick.ml_prediction = ml_pred
        pick.ml_should_bet = ml_should
        
        if ml_should:
            self.stats['ml_approved'] += 1
        
        # 6. ROI Warning
        if pick.odds < ML_CONFIG['roi_warning_threshold']:
            pick.roi_warning = f"⚠️ Cotes {pick.odds:.2f} < 1.40 = ROI négatif probable"
            pick.reasons.append(pick.roi_warning)
            self.stats['roi_warnings'] += 1
        
        # ════════════════════════════════════════════════════════════════════
        # CALCUL SCORE FINAL
        # ════════════════════════════════════════════════════════════════════
        
        # A. Base score (Poisson edge)
        implied_prob = 1 / pick.odds
        edge = pick.predicted_prob - implied_prob if pick.predicted_prob else 0
        pick.base_score = int(edge * 100 * 2)  # Scale to 0-100
        
        # B. Market calibration (V5)
        market_config = MARKET_CALIBRATION.get(pick.market_type, {'bonus': 0})
        pick.base_score += market_config['bonus']
        
        # C. Odds penalty (V5)
        odds_factor = get_odds_penalty(pick.odds)
        pick.base_score = int(pick.base_score * odds_factor)
        
        # D. ML Score
        if pick.ml_confidence >= 0.70:
            pick.ml_score = ML_CONFIG['ml_bonus_high']
            pick.reasons.append(f"🧠 ML très confiant ({pick.ml_confidence*100:.1f}%)")
        elif pick.ml_confidence >= 0.60:
            pick.ml_score = ML_CONFIG['ml_bonus_medium']
            pick.reasons.append(f"🧠 ML confiant ({pick.ml_confidence*100:.1f}%)")
        elif pick.ml_confidence < 0.50:
            pick.ml_score = ML_CONFIG['ml_penalty_low']
            pick.reasons.append(f"⚠️ ML non confiant ({pick.ml_confidence*100:.1f}%)")
        
        # E. Profile Score
        if pick.profile_consensus and pick.market_matches_profile:
            pick.profile_score = ML_CONFIG['profile_consensus_bonus']
            pick.reasons.append(f"✅ CONSENSUS: {pick.home_profile}")
        elif pick.market_matches_profile:
            pick.profile_score = ML_CONFIG['profile_match_bonus']
            pick.reasons.append(f"📊 Marché = profil équipe")
        
        # F. FINAL SCORE
        pick.final_score = pick.base_score + int(pick.ml_score) + pick.profile_score
        
        # G. Kelly sizing
        if pick.final_score > 0 and pick.ml_confidence > 0.5:
            kelly_edge = pick.ml_confidence - implied_prob
            pick.kelly = min(max(kelly_edge / (pick.odds - 1) * 100, 0), 5)
        
        # H. Recommendation
        pick.recommendation = self.get_recommendation(pick)
        
        return pick
    
    def get_market_group(self, market_type: str) -> str:
        """Convertit un market_type en groupe"""
        groups = {
            'goals_over': ['over_15', 'over_25', 'over_35'],
            'goals_under': ['under_15', 'under_25', 'under_35'],
            'btts_yes': ['btts_yes'],
            'btts_no': ['btts_no'],
            'home_win': ['home', 'dc_1x'],
            'away_win': ['away', 'dc_x2'],
        }
        for group, markets in groups.items():
            if market_type in markets:
                return group
        return 'other'
    
    def get_recommendation(self, pick: SmartPickV8) -> str:
        """Génère la recommandation finale"""
        
        # STRONG BET: ML + Profile + Cotes OK
        if (pick.ml_confidence >= 0.70 and 
            pick.market_matches_profile and 
            pick.odds >= ML_CONFIG['min_odds_profitable']):
            return "🟢 STRONG BET"
        
        # BET: ML OK + Cotes OK
        if (pick.ml_confidence >= 0.60 and 
            pick.odds >= ML_CONFIG['min_odds_profitable']):
            return "🟢 BET"
        
        # VALUE: Cotes hautes + ML acceptable
        if pick.odds >= 2.0 and pick.ml_confidence >= 0.55:
            return "🟡 VALUE BET"
        
        # MODERATE
        if pick.final_score >= 50 and pick.ml_confidence >= 0.55:
            return "🟡 MODERATE"
        
        # SKIP - Cotes trop basses
        if pick.odds < ML_CONFIG['roi_warning_threshold']:
            return "⚠️ SKIP (cotes trop basses)"
        
        # SKIP - ML pas confiant
        if pick.ml_confidence < 0.50:
            return "🔴 SKIP (ML non confiant)"
        
        return "⚪ SKIP"
    
    def analyze_match(self, match_data: Dict) -> List[SmartPickV8]:
        """Analyse un match et retourne les picks potentiels"""
        
        home_team = match_data.get('home_team', '')
        away_team = match_data.get('away_team', '')
        league = match_data.get('league', '')
        match_id = match_data.get('match_id', f"{home_team}_vs_{away_team}")
        
        # Calculer probabilités Poisson
        home_xg = match_data.get('home_xg', 1.5)
        away_xg = match_data.get('away_xg', 1.2)
        probs = calculate_match_probabilities(home_xg, away_xg)
        
        picks = []
        
        for market_type, predicted_prob in probs.items():
            odds = match_data.get('odds', {}).get(market_type, 0)
            if not odds or odds < 1.1:
                continue
            
            pick = SmartPickV8(
                match_id=match_id,
                home_team=home_team,
                away_team=away_team,
                league=league,
                market_type=market_type,
                odds=odds,
                predicted_prob=predicted_prob,
                implied_prob=1/odds
            )
            
            pick = self.calculate_score(pick)
            picks.append(pick)
        
        return picks
    
    def filter_best_picks(self, picks: List[SmartPickV8], max_picks: int = 10) -> List[SmartPickV8]:
        """Filtre et classe les meilleurs picks"""
        
        # Filtrer
        valid_picks = [
            p for p in picks 
            if p.ml_should_bet or (p.final_score >= 50 and p.ml_confidence >= 0.55)
        ]
        
        # Trier par score final
        valid_picks.sort(key=lambda x: (x.final_score, x.ml_confidence), reverse=True)
        
        self.stats['final_picks'] = min(len(valid_picks), max_picks)
        
        return valid_picks[:max_picks]
    
    def print_summary(self):
        """Affiche le résumé"""
        print("\n" + "="*70)
        print("📊 ORCHESTRATOR V8 - RÉSUMÉ")
        print("="*70)
        print(f"   Picks analysés:     {self.stats['analyzed']}")
        print(f"   ML approuvés:       {self.stats['ml_approved']}")
        print(f"   Profile matched:    {self.stats['profile_matched']}")
        print(f"   Consensus trouvés:  {self.stats['consensus_found']}")
        print(f"   ROI warnings:       {self.stats['roi_warnings']}")
        print(f"   Picks finaux:       {self.stats['final_picks']}")
        print("="*70)


def main():
    """Test de l'orchestrator V8"""
    print("\n" + "="*70)
    print("🤖 ORCHESTRATOR V8 - ML INTEGRATED")
    print("="*70)
    
    orchestrator = OrchestratorV8ML()
    
    # Test avec un match exemple
    test_match = {
        'match_id': 'test_001',
        'home_team': 'Lille',
        'away_team': 'Lyon',
        'league': 'Ligue 1',
        'home_xg': 1.4,
        'away_xg': 1.3,
        'odds': {
            'home': 2.50,
            'draw': 3.20,
            'away': 2.80,
            'btts_yes': 1.75,
            'btts_no': 1.95,
            'over_25': 1.85,
            'under_25': 1.90,
        }
    }
    
    print(f"\n📌 Test: {test_match['home_team']} vs {test_match['away_team']}")
    
    picks = orchestrator.analyze_match(test_match)
    best_picks = orchestrator.filter_best_picks(picks, max_picks=5)
    
    print(f"\n🎯 TOP {len(best_picks)} PICKS:")
    print("-"*70)
    
    for i, pick in enumerate(best_picks, 1):
        print(f"\n{i}. {pick.market_type.upper()} @ {pick.odds}")
        print(f"   Final Score: {pick.final_score}")
        print(f"   ML: {pick.ml_confidence*100:.1f}% → {pick.ml_prediction}")
        print(f"   Profiles: Home={pick.home_profile}, Away={pick.away_profile}")
        print(f"   Consensus: {pick.profile_consensus}, Match: {pick.market_matches_profile}")
        print(f"   Kelly: {pick.kelly:.2f}%")
        print(f"   → {pick.recommendation}")
        if pick.reasons:
            for r in pick.reasons:
                print(f"      {r}")
    
    orchestrator.print_summary()
    
    print("\n✅ Orchestrator V8 prêt!")


if __name__ == "__main__":
    main()
