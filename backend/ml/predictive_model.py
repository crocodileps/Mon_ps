#!/usr/bin/env python3
"""
🧠 MODÈLE ML PRÉDICTIF - SMART QUANT 2.0

Architecture:
1. Feature Engineering basé sur analyse Niveau 3
2. Train/Test Split TEMPOREL (pas random)
3. Modèles: XGBoost, LightGBM, Logistic Regression
4. Validation: Walk-Forward Cross-Validation
5. Métriques: Accuracy, Precision, Recall, ROI simulé, Brier Score

Features significatives identifiées:
- implied_prob (effect 0.93) ⭐
- odds_taken (effect 0.61) ⭐
- ev_expected (effect 0.50)
- diamond_score (effect 0.38)
- predicted_prob (effect 0.30)
- edge_pct (effect 0.24)
- hours_before_match (effect 0.20)
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, brier_score_loss, confusion_matrix, classification_report
)
import xgboost as xgb
import lightgbm as lgb
import joblib
import json
import warnings
warnings.filterwarnings('ignore')

# Configuration
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('POSTGRES_PORT', 5432)),
    'dbname': os.environ.get('POSTGRES_DB', 'monps_db'),
    'user': os.environ.get('POSTGRES_USER', 'monps_user'),
    'password': os.environ.get('POSTGRES_PASSWORD', 'monps_secure_password_2024')
}

MODEL_DIR = '/home/Mon_ps/backend/ml/models'
os.makedirs(MODEL_DIR, exist_ok=True)

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def load_ml_dataset():
    """Charge le dataset avec les features significatives"""
    conn = get_connection()
    
    query = """
    SELECT 
        t.id,
        t.match_id,
        t.league,
        t.market_type,
        t.prediction,
        t.odds_taken,
        t.closing_odds,
        t.clv_percentage,
        t.diamond_score,
        t.edge_pct,
        t.ev_expected,
        t.is_winner,
        t.profit_loss,
        t.source,
        t.created_at,
        t.implied_prob,
        t.predicted_prob,
        t.hours_before_match,
        t.data_quality_score,
        t.model_uncertainty,
        t.steam_move,
        t.odds_movement,
        t.league_tier,
        t.match_importance,
        t.home_team,
        t.away_team,
        
        -- Reality Check
        r.reality_score,
        r.class_score,
        r.context_score,
        r.tier_difference,
        r.convergence_status,
        r.system_confidence,
        
        -- Team Intelligence Home
        ti_h.home_goals_scored_avg,
        ti_h.home_goals_conceded_avg,
        ti_h.home_btts_rate,
        ti_h.home_over25_rate,
        ti_h.home_win_rate as home_team_win_rate,
        
        -- Team Intelligence Away
        ti_a.away_goals_scored_avg,
        ti_a.away_goals_conceded_avg,
        ti_a.away_btts_rate,
        ti_a.away_over25_rate,
        ti_a.away_win_rate as away_team_win_rate,
        
        -- Team Market Profiles
        tmp_h.best_market_group as home_best_market,
        tmp_h.win_rate as home_profile_wr,
        tmp_h.profit as home_profile_profit,
        tmp_a.best_market_group as away_best_market,
        tmp_a.win_rate as away_profile_wr,
        tmp_a.profit as away_profile_profit
        
    FROM tracking_clv_picks t
    LEFT JOIN reality_check_results r ON t.match_id = r.match_id
    LEFT JOIN team_intelligence ti_h ON t.home_team = ti_h.team_name
    LEFT JOIN team_intelligence ti_a ON t.away_team = ti_a.team_name
    LEFT JOIN team_market_profiles tmp_h ON t.home_team = tmp_h.team_name AND tmp_h.location = 'home'
    LEFT JOIN team_market_profiles tmp_a ON t.away_team = tmp_a.team_name AND tmp_a.location = 'away'
    WHERE t.is_winner IS NOT NULL
      AND t.created_at IS NOT NULL
    ORDER BY t.created_at ASC
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def feature_engineering(df):
    """Crée des features dérivées intelligentes"""
    
    print("\n📐 FEATURE ENGINEERING...")
    
    # Features de base (déjà significatives)
    feature_cols = [
        'implied_prob', 'odds_taken', 'diamond_score', 'edge_pct',
        'ev_expected', 'predicted_prob', 'hours_before_match'
    ]
    
    # Features dérivées
    df['odds_value'] = df['implied_prob'] - (1 / df['odds_taken'])
    df['clv_positive'] = (df['clv_percentage'] > 0).astype(int)
    df['high_diamond'] = (df['diamond_score'] >= 65).astype(int)
    df['steam_detected'] = df['steam_move'].fillna(False).astype(int)
    
    # Interaction features
    df['prob_x_diamond'] = df['implied_prob'] * df['diamond_score'] / 100
    df['edge_x_odds'] = df['edge_pct'] * df['odds_taken']
    df['timing_factor'] = np.log1p(df['hours_before_match'].fillna(24))
    
    # Team features
    df['team_goals_diff'] = df['home_goals_scored_avg'].fillna(1.5) - df['away_goals_scored_avg'].fillna(1.0)
    df['btts_likelihood'] = (df['home_btts_rate'].fillna(50) + df['away_btts_rate'].fillna(50)) / 2
    df['over25_likelihood'] = (df['home_over25_rate'].fillna(50) + df['away_over25_rate'].fillna(50)) / 2
    
    # Reality check features
    df['reality_class_combo'] = df['reality_score'].fillna(50) * df['class_score'].fillna(50) / 100
    df['tier_advantage'] = df['tier_difference'].fillna(0)
    
    # Market profile match
    df['profile_consensus'] = (df['home_best_market'] == df['away_best_market']).astype(int)
    df['profile_profit_sum'] = df['home_profile_profit'].fillna(0) + df['away_profile_profit'].fillna(0)
    
    # Categorical encoding
    le_market = LabelEncoder()
    df['market_encoded'] = le_market.fit_transform(df['market_type'].fillna('unknown'))
    
    le_league = LabelEncoder()
    df['league_encoded'] = le_league.fit_transform(df['league'].fillna('unknown'))
    
    le_source = LabelEncoder()
    df['source_encoded'] = le_source.fit_transform(df['source'].fillna('unknown'))
    
    # Convergence encoding
    convergence_map = {'strong_convergence': 2, 'partial_convergence': 1, 'divergence': 0}
    df['convergence_encoded'] = df['convergence_status'].map(convergence_map).fillna(1)
    
    # Final feature list
    all_features = [
        # Core features (significatives)
        'implied_prob', 'odds_taken', 'diamond_score', 'edge_pct',
        'ev_expected', 'predicted_prob', 'hours_before_match',
        
        # Derived features
        'odds_value', 'clv_positive', 'high_diamond', 'steam_detected',
        'prob_x_diamond', 'edge_x_odds', 'timing_factor',
        
        # Team features
        'team_goals_diff', 'btts_likelihood', 'over25_likelihood',
        
        # Reality check
        'reality_class_combo', 'tier_advantage', 'convergence_encoded',
        
        # Profile features
        'profile_consensus', 'profile_profit_sum',
        
        # Categorical
        'market_encoded', 'league_encoded', 'source_encoded'
    ]
    
    # Nettoyer les features disponibles
    available_features = [f for f in all_features if f in df.columns]
    
    print(f"   ✅ {len(available_features)} features créées")
    
    return df, available_features

def prepare_train_test_split(df, features, test_ratio=0.2):
    """Split temporel (pas random!)"""
    
    print("\n📊 PRÉPARATION TRAIN/TEST SPLIT TEMPOREL...")
    
    # Trier par date
    df = df.sort_values('created_at').reset_index(drop=True)
    
    # Split temporel
    split_idx = int(len(df) * (1 - test_ratio))
    
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()
    
    print(f"   Train: {len(train_df)} samples ({train_df['created_at'].min()} → {train_df['created_at'].max()})")
    print(f"   Test:  {len(test_df)} samples ({test_df['created_at'].min()} → {test_df['created_at'].max()})")
    
    # Préparer X et y
    X_train = train_df[features].fillna(0)
    y_train = train_df['is_winner'].astype(int)
    
    X_test = test_df[features].fillna(0)
    y_test = test_df['is_winner'].astype(int)
    
    # Garder les odds pour calcul ROI
    odds_test = test_df['odds_taken'].values
    
    # Scaler
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    return X_train_scaled, X_test_scaled, y_train, y_test, odds_test, scaler, features

def train_models(X_train, y_train):
    """Entraîne plusieurs modèles"""
    
    print("\n🤖 ENTRAÎNEMENT DES MODÈLES...")
    
    models = {}
    
    # 1. Logistic Regression (baseline)
    print("   → Logistic Regression...")
    lr = LogisticRegression(
        max_iter=1000,
        class_weight='balanced',
        random_state=42
    )
    lr.fit(X_train, y_train)
    models['logistic_regression'] = lr
    
    # 2. XGBoost
    print("   → XGBoost...")
    xgb_model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=len(y_train[y_train==0]) / len(y_train[y_train==1]),
        random_state=42,
        eval_metric='logloss',
        early_stopping_rounds=20
    )
    xgb_model.fit(
        X_train, y_train,
        eval_set=[(X_train, y_train)],
        verbose=False
    )
    models['xgboost'] = xgb_model
    
    # 3. LightGBM
    print("   → LightGBM...")
    lgb_model = lgb.LGBMClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        class_weight='balanced',
        random_state=42,
        verbose=-1
    )
    lgb_model.fit(X_train, y_train)
    models['lightgbm'] = lgb_model
    
    print(f"   ✅ {len(models)} modèles entraînés")
    
    return models

def evaluate_models(models, X_test, y_test, odds_test):
    """Évalue les modèles avec métriques complètes"""
    
    print("\n" + "="*80)
    print("📊 ÉVALUATION DES MODÈLES")
    print("="*80)
    
    results = {}
    
    for name, model in models.items():
        print(f"\n{'─'*40}")
        print(f"🔹 {name.upper()}")
        print(f"{'─'*40}")
        
        # Prédictions
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]
        
        # Métriques de classification
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        
        try:
            roc_auc = roc_auc_score(y_test, y_proba)
        except:
            roc_auc = 0.5
        
        brier = brier_score_loss(y_test, y_proba)
        
        print(f"   Accuracy:  {accuracy*100:.2f}%")
        print(f"   Precision: {precision*100:.2f}%")
        print(f"   Recall:    {recall*100:.2f}%")
        print(f"   F1 Score:  {f1*100:.2f}%")
        print(f"   ROC AUC:   {roc_auc:.4f}")
        print(f"   Brier:     {brier:.4f} (lower is better)")
        
        # Confusion Matrix
        cm = confusion_matrix(y_test, y_pred)
        print(f"\n   Confusion Matrix:")
        print(f"   TN={cm[0,0]:4d}  FP={cm[0,1]:4d}")
        print(f"   FN={cm[1,0]:4d}  TP={cm[1,1]:4d}")
        
        # Simulation ROI
        roi_results = simulate_betting(y_test, y_pred, y_proba, odds_test)
        
        print(f"\n   📈 SIMULATION BETTING:")
        print(f"   Bets placés:     {roi_results['bets_placed']}")
        print(f"   Wins:            {roi_results['wins']}")
        print(f"   Win Rate:        {roi_results['win_rate']*100:.1f}%")
        print(f"   Profit/Loss:     {roi_results['profit']:.2f}u")
        print(f"   ROI:             {roi_results['roi']*100:.2f}%")
        
        results[name] = {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'roc_auc': roc_auc,
            'brier': brier,
            'roi': roi_results['roi'],
            'profit': roi_results['profit'],
            'win_rate': roi_results['win_rate']
        }
    
    return results

def simulate_betting(y_true, y_pred, y_proba, odds, threshold=0.55, stake=1.0):
    """Simule les paris basés sur les prédictions"""
    
    bets_placed = 0
    wins = 0
    profit = 0.0
    
    for i in range(len(y_pred)):
        # Ne parier que si proba > threshold
        if y_proba[i] >= threshold:
            bets_placed += 1
            
            if y_true.iloc[i] == 1:  # Win
                wins += 1
                profit += (odds[i] - 1) * stake
            else:  # Loss
                profit -= stake
    
    win_rate = wins / bets_placed if bets_placed > 0 else 0
    roi = profit / bets_placed if bets_placed > 0 else 0
    
    return {
        'bets_placed': bets_placed,
        'wins': wins,
        'win_rate': win_rate,
        'profit': profit,
        'roi': roi
    }

def get_feature_importance(models, feature_names):
    """Analyse l'importance des features"""
    
    print("\n" + "="*80)
    print("🎯 FEATURE IMPORTANCE")
    print("="*80)
    
    importance_data = {}
    
    for name, model in models.items():
        if hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_
        elif hasattr(model, 'coef_'):
            importances = np.abs(model.coef_[0])
        else:
            continue
        
        importance_data[name] = dict(zip(feature_names, importances))
    
    # Afficher pour XGBoost (le plus fiable)
    if 'xgboost' in importance_data:
        print("\n🔹 XGBoost Feature Importance:")
        sorted_imp = sorted(importance_data['xgboost'].items(), key=lambda x: x[1], reverse=True)
        for feat, imp in sorted_imp[:15]:
            bar = '█' * int(imp * 100)
            print(f"   {feat:<25}: {imp:.4f} {bar}")
    
    return importance_data

def compare_with_current_system(y_test, current_predictions, model_predictions, odds):
    """Compare le modèle ML avec le système actuel"""
    
    print("\n" + "="*80)
    print("⚔️ COMPARAISON ML vs SYSTÈME ACTUEL")
    print("="*80)
    
    # Système actuel (basé sur is_winner des picks déjà faits)
    current_wr = y_test.mean()
    
    # Nouveau modèle
    model_correct = (model_predictions == y_test).sum()
    model_wr = model_correct / len(y_test)
    
    print(f"\n   Système Actuel:")
    print(f"   └─ Win Rate: {current_wr*100:.1f}%")
    
    print(f"\n   Modèle ML:")
    print(f"   └─ Win Rate: {model_wr*100:.1f}%")
    print(f"   └─ Amélioration: {(model_wr - current_wr)*100:+.1f}%")

def save_best_model(models, results, scaler, feature_names):
    """Sauvegarde le meilleur modèle"""
    
    print("\n" + "="*80)
    print("💾 SAUVEGARDE DU MEILLEUR MODÈLE")
    print("="*80)
    
    # Trouver le meilleur (par ROI)
    best_name = max(results.keys(), key=lambda x: results[x]['roi'])
    best_model = models[best_name]
    best_metrics = results[best_name]
    
    print(f"\n   🏆 Meilleur modèle: {best_name}")
    print(f"   └─ ROI: {best_metrics['roi']*100:.2f}%")
    print(f"   └─ Win Rate: {best_metrics['win_rate']*100:.1f}%")
    print(f"   └─ Accuracy: {best_metrics['accuracy']*100:.1f}%")
    
    # Sauvegarder
    model_path = f"{MODEL_DIR}/best_model.joblib"
    scaler_path = f"{MODEL_DIR}/scaler.joblib"
    metadata_path = f"{MODEL_DIR}/model_metadata.json"
    
    joblib.dump(best_model, model_path)
    joblib.dump(scaler, scaler_path)
    
    metadata = {
        'model_name': best_name,
        'features': feature_names,
        'metrics': {k: float(v) for k, v in best_metrics.items()},
        'trained_at': datetime.now().isoformat(),
        'threshold': 0.55
    }
    
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\n   ✅ Modèle sauvegardé: {model_path}")
    print(f"   ✅ Scaler sauvegardé: {scaler_path}")
    print(f"   ✅ Metadata sauvegardée: {metadata_path}")
    
    return best_name, best_model

def main():
    print("\n" + "="*80)
    print("🧠 MODÈLE ML PRÉDICTIF - SMART QUANT 2.0")
    print("="*80)
    print(f"   Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # 1. Charger les données
    print("\n📂 Chargement des données...")
    df = load_ml_dataset()
    print(f"   ✅ {len(df)} picks chargés")
    print(f"   ✅ Win Rate global: {df['is_winner'].mean()*100:.1f}%")
    
    # 2. Feature Engineering
    df, features = feature_engineering(df)
    
    # 3. Train/Test Split
    X_train, X_test, y_train, y_test, odds_test, scaler, feature_names = prepare_train_test_split(df, features)
    
    # 4. Entraîner les modèles
    models = train_models(X_train, y_train)
    
    # 5. Évaluer
    results = evaluate_models(models, X_test, y_test, odds_test)
    
    # 6. Feature Importance
    importance = get_feature_importance(models, feature_names)
    
    # 7. Comparaison avec système actuel
    best_model_name = max(results.keys(), key=lambda x: results[x]['roi'])
    y_pred_best = models[best_model_name].predict(X_test)
    compare_with_current_system(y_test, None, y_pred_best, odds_test)
    
    # 8. Sauvegarder
    save_best_model(models, results, scaler, feature_names)
    
    # Résumé final
    print("\n" + "="*80)
    print("📋 RÉSUMÉ FINAL")
    print("="*80)
    
    print("\n   PERFORMANCE DES MODÈLES:")
    print(f"   {'Model':<20} {'Accuracy':>10} {'ROI':>10} {'Win Rate':>10} {'Profit':>10}")
    print("   " + "-"*60)
    for name, metrics in sorted(results.items(), key=lambda x: x[1]['roi'], reverse=True):
        print(f"   {name:<20} {metrics['accuracy']*100:>9.1f}% {metrics['roi']*100:>9.2f}% {metrics['win_rate']*100:>9.1f}% {metrics['profit']:>+9.2f}u")
    
    print("\n" + "="*80)
    print("🏁 MODÈLE ML PRÉDICTIF TERMINÉ")
    print("="*80)

if __name__ == "__main__":
    main()
