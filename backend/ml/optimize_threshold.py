#!/usr/bin/env python3
"""
🎯 OPTIMISATION DU THRESHOLD
Trouve le meilleur seuil de confiance pour maximiser le ROI
"""

import os
import psycopg2
import pandas as pd
import numpy as np
import joblib
from datetime import datetime

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': 5432,
    'dbname': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}

MODEL_DIR = '/home/Mon_ps/backend/ml/models'

def load_test_data():
    """Charge les données de test"""
    conn = psycopg2.connect(**DB_CONFIG)
    
    query = """
    SELECT 
        t.odds_taken, t.is_winner, t.implied_prob, t.diamond_score,
        t.edge_pct, t.ev_expected, t.predicted_prob, t.hours_before_match,
        t.market_type, t.league, t.source, t.clv_percentage,
        t.steam_move, t.created_at,
        r.reality_score, r.class_score, r.convergence_status, r.tier_difference,
        ti_h.home_goals_scored_avg, ti_h.home_btts_rate, ti_h.home_over25_rate,
        ti_a.away_goals_scored_avg, ti_a.away_btts_rate, ti_a.away_over25_rate,
        tmp_h.best_market_group as home_best_market, tmp_h.profit as home_profile_profit,
        tmp_a.best_market_group as away_best_market, tmp_a.profit as away_profile_profit
    FROM tracking_clv_picks t
    LEFT JOIN reality_check_results r ON t.match_id = r.match_id
    LEFT JOIN team_intelligence ti_h ON t.home_team = ti_h.team_name
    LEFT JOIN team_intelligence ti_a ON t.away_team = ti_a.team_name
    LEFT JOIN team_market_profiles tmp_h ON t.home_team = tmp_h.team_name AND tmp_h.location = 'home'
    LEFT JOIN team_market_profiles tmp_a ON t.away_team = tmp_a.team_name AND tmp_a.location = 'away'
    WHERE t.is_winner IS NOT NULL
    ORDER BY t.created_at ASC
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def prepare_features(df):
    """Prépare les features comme dans le modèle principal"""
    from sklearn.preprocessing import LabelEncoder
    
    # Features dérivées
    df['odds_value'] = df['implied_prob'].fillna(0.5) - (1 / df['odds_taken'].replace(0, 1))
    df['clv_positive'] = (df['clv_percentage'].fillna(0) > 0).astype(int)
    df['high_diamond'] = (df['diamond_score'].fillna(0) >= 65).astype(int)
    df['steam_detected'] = df['steam_move'].fillna(False).astype(int)
    df['prob_x_diamond'] = df['implied_prob'].fillna(0.5) * df['diamond_score'].fillna(50) / 100
    df['edge_x_odds'] = df['edge_pct'].fillna(0) * df['odds_taken'].fillna(2)
    df['timing_factor'] = np.log1p(df['hours_before_match'].fillna(24))
    df['team_goals_diff'] = df['home_goals_scored_avg'].fillna(1.5) - df['away_goals_scored_avg'].fillna(1.0)
    df['btts_likelihood'] = (df['home_btts_rate'].fillna(50) + df['away_btts_rate'].fillna(50)) / 2
    df['over25_likelihood'] = (df['home_over25_rate'].fillna(50) + df['away_over25_rate'].fillna(50)) / 2
    df['reality_class_combo'] = df['reality_score'].fillna(50) * df['class_score'].fillna(50) / 100
    df['tier_advantage'] = df['tier_difference'].fillna(0)
    df['profile_consensus'] = (df['home_best_market'] == df['away_best_market']).astype(int)
    df['profile_profit_sum'] = df['home_profile_profit'].fillna(0) + df['away_profile_profit'].fillna(0)
    
    # Encodings
    le_market = LabelEncoder()
    df['market_encoded'] = le_market.fit_transform(df['market_type'].fillna('unknown'))
    le_league = LabelEncoder()
    df['league_encoded'] = le_league.fit_transform(df['league'].fillna('unknown'))
    le_source = LabelEncoder()
    df['source_encoded'] = le_source.fit_transform(df['source'].fillna('unknown'))
    
    convergence_map = {'strong_convergence': 2, 'partial_convergence': 1, 'divergence': 0}
    df['convergence_encoded'] = df['convergence_status'].map(convergence_map).fillna(1)
    
    return df

def simulate_with_filters(y_true, y_proba, odds, threshold, min_odds=1.0, max_odds=10.0):
    """Simule avec filtres de cotes"""
    bets = wins = profit = 0
    
    for i in range(len(y_proba)):
        if y_proba[i] >= threshold and min_odds <= odds[i] <= max_odds:
            bets += 1
            if y_true.iloc[i] == 1:
                wins += 1
                profit += (odds[i] - 1)
            else:
                profit -= 1
    
    wr = wins / bets if bets > 0 else 0
    roi = profit / bets if bets > 0 else 0
    return {'bets': bets, 'wins': wins, 'wr': wr, 'profit': profit, 'roi': roi}

def main():
    print("\n" + "="*80)
    print("🎯 OPTIMISATION DU THRESHOLD")
    print("="*80)
    
    # Charger données et modèle
    print("\n📂 Chargement...")
    df = load_test_data()
    df = prepare_features(df)
    
    model = joblib.load(f"{MODEL_DIR}/best_model.joblib")
    scaler = joblib.load(f"{MODEL_DIR}/scaler.joblib")
    
    # Features
    feature_cols = [
        'implied_prob', 'odds_taken', 'diamond_score', 'edge_pct',
        'ev_expected', 'predicted_prob', 'hours_before_match',
        'odds_value', 'clv_positive', 'high_diamond', 'steam_detected',
        'prob_x_diamond', 'edge_x_odds', 'timing_factor',
        'team_goals_diff', 'btts_likelihood', 'over25_likelihood',
        'reality_class_combo', 'tier_advantage', 'convergence_encoded',
        'profile_consensus', 'profile_profit_sum',
        'market_encoded', 'league_encoded', 'source_encoded'
    ]
    
    # Split temporel
    split_idx = int(len(df) * 0.8)
    test_df = df.iloc[split_idx:].copy()
    
    X_test = test_df[feature_cols].fillna(0)
    X_test_scaled = scaler.transform(X_test)
    
    y_test = test_df['is_winner'].astype(int)
    odds_test = test_df['odds_taken'].values
    
    y_proba = model.predict_proba(X_test_scaled)[:, 1]
    
    print(f"   ✅ {len(test_df)} picks de test")
    
    # Test différents thresholds
    print("\n" + "="*80)
    print("📊 TEST DES THRESHOLDS (sans filtre cotes)")
    print("="*80)
    print(f"\n{'Threshold':>10} {'Bets':>8} {'Wins':>8} {'WR':>8} {'Profit':>10} {'ROI':>10}")
    print("-"*60)
    
    best_roi = -999
    best_threshold = 0.5
    
    for thresh in [0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]:
        result = simulate_with_filters(y_test, y_proba, odds_test, thresh)
        print(f"{thresh:>10.2f} {result['bets']:>8} {result['wins']:>8} {result['wr']*100:>7.1f}% {result['profit']:>+10.2f} {result['roi']*100:>+9.2f}%")
        
        if result['roi'] > best_roi and result['bets'] >= 20:
            best_roi = result['roi']
            best_threshold = thresh
    
    # Test avec filtres de cotes
    print("\n" + "="*80)
    print("📊 TEST AVEC FILTRE COTES MINIMALES")
    print("="*80)
    print(f"\n{'MinOdds':>8} {'Thresh':>8} {'Bets':>8} {'WR':>8} {'Profit':>10} {'ROI':>10}")
    print("-"*60)
    
    best_combo = {'roi': -999}
    
    for min_odds in [1.30, 1.40, 1.50, 1.60, 1.70, 1.80, 2.00]:
        for thresh in [0.55, 0.60, 0.65, 0.70]:
            result = simulate_with_filters(y_test, y_proba, odds_test, thresh, min_odds=min_odds)
            if result['bets'] >= 15:
                print(f"{min_odds:>8.2f} {thresh:>8.2f} {result['bets']:>8} {result['wr']*100:>7.1f}% {result['profit']:>+10.2f} {result['roi']*100:>+9.2f}%")
                
                if result['roi'] > best_combo['roi']:
                    best_combo = {'min_odds': min_odds, 'thresh': thresh, **result}
    
    # Test avec Diamond Score minimum
    print("\n" + "="*80)
    print("📊 TEST AVEC FILTRE DIAMOND SCORE")
    print("="*80)
    print(f"\n{'MinDiam':>8} {'Thresh':>8} {'Bets':>8} {'WR':>8} {'Profit':>10} {'ROI':>10}")
    print("-"*60)
    
    diamond_scores = test_df['diamond_score'].values
    
    for min_diamond in [50, 55, 60, 65, 70]:
        for thresh in [0.55, 0.60, 0.65]:
            bets = wins = profit = 0
            for i in range(len(y_proba)):
                if y_proba[i] >= thresh and diamond_scores[i] >= min_diamond:
                    bets += 1
                    if y_test.iloc[i] == 1:
                        wins += 1
                        profit += (odds_test[i] - 1)
                    else:
                        profit -= 1
            
            if bets >= 10:
                wr = wins / bets
                roi = profit / bets
                print(f"{min_diamond:>8} {thresh:>8.2f} {bets:>8} {wr*100:>7.1f}% {profit:>+10.2f} {roi*100:>+9.2f}%")
    
    # Résumé
    print("\n" + "="*80)
    print("🏆 MEILLEURE CONFIGURATION TROUVÉE")
    print("="*80)
    
    if best_combo['roi'] > -999:
        print(f"\n   Cotes min: {best_combo.get('min_odds', 'N/A')}")
        print(f"   Threshold: {best_combo.get('thresh', best_threshold)}")
        print(f"   Bets:      {best_combo['bets']}")
        print(f"   Win Rate:  {best_combo['wr']*100:.1f}%")
        print(f"   Profit:    {best_combo['profit']:+.2f}u")
        print(f"   ROI:       {best_combo['roi']*100:+.2f}%")
    else:
        print(f"\n   Threshold optimal: {best_threshold}")
        print(f"   ROI: {best_roi*100:+.2f}%")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()
