"""
🧠 API ML PREDICTION - SMART QUANT 2.0
Analyse TOUTES les cotes et donne une recommandation
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np
import joblib
import json
import os

router = APIRouter(prefix="/api/ml", tags=["ML Prediction"])

MODEL_DIR = '/home/Mon_ps/backend/ml/models'

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'postgres'),
    'port': 5432,
    'dbname': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}

# Cache modèle
_model = None
_scaler = None
_config = None

def get_model():
    global _model, _scaler, _config
    if _model is None:
        _model = joblib.load(f"{MODEL_DIR}/best_model.joblib")
        _scaler = joblib.load(f"{MODEL_DIR}/scaler.joblib")
        with open(f"{MODEL_DIR}/optimal_config.json") as f:
            _config = json.load(f)
    return _model, _scaler, _config

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

class PickInput(BaseModel):
    home_team: str
    away_team: str
    market_type: str
    odds: float
    implied_prob: Optional[float] = None
    diamond_score: Optional[float] = 50.0
    edge_pct: Optional[float] = 0.0
    ev_expected: Optional[float] = 0.0
    predicted_prob: Optional[float] = None
    hours_before_match: Optional[float] = 24.0

class PredictionResult(BaseModel):
    prediction: str
    confidence: float
    win_probability: float
    recommendation: str
    risk_level: str
    expected_roi_category: str
    should_bet: bool
    expected_value: float
    roi_warning: Optional[str]
    details: dict

@router.post("/predict", response_model=PredictionResult)
async def predict_pick(pick: PickInput):
    """
    🧠 Prédit si un pick va gagner - ANALYSE TOUTES LES COTES
    
    Retourne:
    - Prédiction WIN/LOSS
    - Confiance du modèle
    - Recommandation selon le profil de risque
    - Avertissement ROI si cotes trop basses
    """
    model, scaler, config = get_model()
    
    # Récupérer données équipes
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Team Intelligence Home
    cur.execute("""
        SELECT home_goals_scored_avg, home_btts_rate, home_over25_rate
        FROM team_intelligence WHERE team_name ILIKE %s
    """, (f"%{pick.home_team}%",))
    ti_home = cur.fetchone() or {}
    
    # Team Intelligence Away
    cur.execute("""
        SELECT away_goals_scored_avg, away_btts_rate, away_over25_rate
        FROM team_intelligence WHERE team_name ILIKE %s
    """, (f"%{pick.away_team}%",))
    ti_away = cur.fetchone() or {}
    
    # Team Profiles
    cur.execute("""
        SELECT best_market_group, profit FROM team_market_profiles 
        WHERE team_name ILIKE %s AND location = 'home'
    """, (f"%{pick.home_team}%",))
    profile_home = cur.fetchone() or {}
    
    cur.execute("""
        SELECT best_market_group, profit FROM team_market_profiles 
        WHERE team_name ILIKE %s AND location = 'away'
    """, (f"%{pick.away_team}%",))
    profile_away = cur.fetchone() or {}
    
    cur.close()
    conn.close()
    
    # Calculer implied_prob si non fourni
    implied_prob = pick.implied_prob or (1 / pick.odds)
    predicted_prob = pick.predicted_prob or implied_prob
    
    # Préparer les features
    features = {
        'implied_prob': implied_prob,
        'odds_taken': pick.odds,
        'diamond_score': pick.diamond_score,
        'edge_pct': pick.edge_pct,
        'ev_expected': pick.ev_expected,
        'predicted_prob': predicted_prob,
        'hours_before_match': pick.hours_before_match,
        'odds_value': implied_prob - (1 / pick.odds),
        'clv_positive': 1 if pick.edge_pct > 0 else 0,
        'high_diamond': 1 if pick.diamond_score >= 65 else 0,
        'steam_detected': 0,
        'prob_x_diamond': implied_prob * pick.diamond_score / 100,
        'edge_x_odds': pick.edge_pct * pick.odds,
        'timing_factor': np.log1p(pick.hours_before_match),
        'team_goals_diff': ti_home.get('home_goals_scored_avg', 1.5) - ti_away.get('away_goals_scored_avg', 1.0),
        'btts_likelihood': (ti_home.get('home_btts_rate', 50) + ti_away.get('away_btts_rate', 50)) / 2,
        'over25_likelihood': (ti_home.get('home_over25_rate', 50) + ti_away.get('away_over25_rate', 50)) / 2,
        'reality_class_combo': 50 * 50 / 100,
        'tier_advantage': 0,
        'convergence_encoded': 1,
        'profile_consensus': 1 if profile_home.get('best_market_group') == profile_away.get('best_market_group') else 0,
        'profile_profit_sum': (profile_home.get('profit', 0) or 0) + (profile_away.get('profit', 0) or 0),
        'market_encoded': 0,
        'league_encoded': 0,
        'source_encoded': 0
    }
    
    # Ordre des features
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
    X_scaled = scaler.transform(X)
    
    # PRÉDICTION (sur TOUTES les cotes)
    win_proba = model.predict_proba(X_scaled)[0][1]
    prediction = "WIN" if win_proba >= 0.5 else "LOSS"
    
    # Expected Value
    ev = (win_proba * (pick.odds - 1)) - ((1 - win_proba) * 1)
    
    # Déterminer le niveau de risque et la catégorie ROI
    # Basé sur l'analyse d'optimisation
    roi_warning = None
    
    if pick.odds >= 2.00:
        risk_level = "HIGH_VALUE"
        expected_roi_cat = "EXCELLENT (+45% ROI potentiel)"
    elif pick.odds >= 1.70:
        risk_level = "GOOD_VALUE"
        expected_roi_cat = "BON (+20% ROI potentiel)"
    elif pick.odds >= 1.40:
        risk_level = "MODERATE_VALUE"
        expected_roi_cat = "MODÉRÉ (+9% ROI potentiel)"
    else:
        risk_level = "LOW_VALUE"
        expected_roi_cat = "FAIBLE (ROI négatif probable)"
        roi_warning = f"⚠️ Cotes {pick.odds:.2f} trop basses. Historiquement, les cotes <1.40 avec ce modèle ont un ROI négatif même avec haute confiance."
    
    # Recommandation globale
    if win_proba >= 0.70 and pick.odds >= 1.70:
        recommendation = "🟢 STRONG BET - Haute confiance + Bonnes cotes"
        should_bet = True
    elif win_proba >= 0.65 and pick.odds >= 1.50:
        recommendation = "🟢 BET - Confiance élevée"
        should_bet = True
    elif win_proba >= 0.60 and pick.odds >= 1.70:
        recommendation = "🟡 VALUE BET - Cotes intéressantes"
        should_bet = True
    elif win_proba >= 0.60 and pick.odds >= 1.40:
        recommendation = "🟡 MODERATE - Acceptable"
        should_bet = True
    elif win_proba >= 0.55:
        if pick.odds < 1.40:
            recommendation = "⚠️ SKIP - Confiance OK mais cotes trop basses"
            should_bet = False
        else:
            recommendation = "🟡 RISKY - Confiance limite"
            should_bet = pick.odds >= 1.60
    else:
        recommendation = "🔴 NO BET - Confiance insuffisante"
        should_bet = False
    
    return PredictionResult(
        prediction=prediction,
        confidence=round(win_proba * 100, 1),
        win_probability=round(win_proba, 4),
        recommendation=recommendation,
        risk_level=risk_level,
        expected_roi_category=expected_roi_cat,
        should_bet=should_bet,
        expected_value=round(ev, 4),
        roi_warning=roi_warning,
        details={
            'odds': pick.odds,
            'diamond_score': pick.diamond_score,
            'edge_pct': pick.edge_pct,
            'team_profile_consensus': bool(features['profile_consensus']),
            'btts_likelihood': round(features['btts_likelihood'], 1),
            'over25_likelihood': round(features['over25_likelihood'], 1),
            'home_profile': profile_home.get('best_market_group', 'unknown'),
            'away_profile': profile_away.get('best_market_group', 'unknown'),
            'model_features_used': 25
        }
    )

@router.get("/config")
async def get_ml_config():
    """Retourne la configuration ML et les seuils de ROI"""
    _, _, config = get_model()
    return {
        **config,
        "roi_thresholds": {
            "odds >= 2.00": "+45% ROI (conservateur)",
            "odds >= 1.70": "+20% ROI (balanced)",
            "odds >= 1.40": "+9% ROI (aggressive)",
            "odds < 1.40": "ROI négatif probable"
        }
    }

@router.get("/health")
async def ml_health():
    """Vérifie que le modèle ML est chargé"""
    try:
        model, scaler, config = get_model()
        return {
            "status": "healthy",
            "model": "xgboost",
            "features": 25,
            "recommended_min_odds": 1.70,
            "recommended_min_confidence": 60
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
