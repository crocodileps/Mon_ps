#!/usr/bin/env python3
"""
🧠 NIVEAU 3 ML - ANALYSE DES FEATURES
Objectif: Identifier les variables les plus prédictives
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import numpy as np
from datetime import datetime
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

DB_CONFIG = {
    'host': os.environ.get('POSTGRES_HOST', 'localhost'),
    'port': int(os.environ.get('POSTGRES_PORT', 5432)),
    'dbname': os.environ.get('POSTGRES_DB', 'monps_db'),
    'user': os.environ.get('POSTGRES_USER', 'monps_user'),
    'password': os.environ.get('POSTGRES_PASSWORD', 'monps_secure_password_2024')
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def load_ml_dataset():
    """Charge le dataset complet pour ML avec colonnes CORRECTES"""
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
        
        -- Reality Check features
        r.reality_score,
        r.class_score,
        r.context_score,
        r.home_tier,
        r.away_tier,
        r.tier_difference,
        r.convergence_status,
        r.system_confidence,
        r.adjusted_confidence,
        r.reality_check_correct,
        
        -- Team Intelligence features (home)
        th.current_form as home_form,
        th.current_pressing as home_pressing,
        th.current_style as home_style,
        th.home_win_rate,
        th.home_draw_rate,
        th.home_strength,
        
        -- Team Intelligence features (away)
        ta.current_form as away_form,
        ta.current_pressing as away_pressing,
        ta.current_style as away_style,
        ta.away_win_rate,
        
        -- Team Class
        tch.tier as home_tier_class,
        tch.calculated_power_index as home_power,
        tch.big_game_factor as home_big_game,
        tca.tier as away_tier_class,
        tca.calculated_power_index as away_power,
        tca.big_game_factor as away_big_game,
        
        -- Derived features
        CASE WHEN t.odds_taken < t.closing_odds THEN 1 ELSE 0 END as got_value,
        ABS(t.odds_taken - t.closing_odds) / NULLIF(t.odds_taken, 0) * 100 as line_movement_pct
        
    FROM tracking_clv_picks t
    LEFT JOIN reality_check_results r ON t.match_id = r.match_id
    LEFT JOIN team_intelligence th ON t.home_team = th.team_name
    LEFT JOIN team_intelligence ta ON t.away_team = ta.team_name
    LEFT JOIN team_class tch ON t.home_team = tch.team_name
    LEFT JOIN team_class tca ON t.away_team = tca.team_name
    WHERE t.is_winner IS NOT NULL
    ORDER BY t.created_at DESC
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def analyze_feature_importance(df):
    """Analyse l'importance de chaque feature pour prédire is_winner"""
    
    print("\n" + "="*80)
    print("📊 FEATURE IMPORTANCE ANALYSIS")
    print("="*80)
    
    numeric_features = [
        'odds_taken', 'closing_odds', 'clv_percentage', 'diamond_score',
        'edge_pct', 'ev_expected', 'reality_score', 'class_score',
        'context_score', 'system_confidence', 'adjusted_confidence',
        'tier_difference', 'home_power', 'away_power', 'home_win_rate',
        'away_win_rate', 'home_strength', 'hours_before_match',
        'data_quality_score', 'model_uncertainty', 'implied_prob',
        'predicted_prob', 'line_movement_pct', 'got_value'
    ]
    
    results = []
    
    for feature in numeric_features:
        if feature not in df.columns:
            continue
            
        wins = df[df['is_winner'] == True][feature].dropna()
        losses = df[df['is_winner'] == False][feature].dropna()
        
        if len(wins) < 5 or len(losses) < 5:
            continue
        
        win_mean = wins.mean()
        loss_mean = losses.mean()
        diff = win_mean - loss_mean
        
        t_stat, p_value = stats.ttest_ind(wins, losses, equal_var=False)
        
        pooled_std = np.sqrt((wins.std()**2 + losses.std()**2) / 2)
        cohens_d = diff / pooled_std if pooled_std > 0 else 0
        
        valid_data = df[[feature, 'is_winner']].dropna()
        correlation = valid_data[feature].corr(valid_data['is_winner'].astype(int)) if len(valid_data) > 10 else 0
        
        results.append({
            'feature': feature,
            'win_mean': round(win_mean, 4),
            'loss_mean': round(loss_mean, 4),
            'diff': round(diff, 4),
            'effect_size': round(abs(cohens_d), 3),
            'p_value': round(p_value, 4),
            'correlation': round(correlation, 4),
            'significance': '***' if p_value < 0.001 else '**' if p_value < 0.01 else '*' if p_value < 0.05 else ''
        })
    
    results_df = pd.DataFrame(results).sort_values('effect_size', ascending=False)
    
    print("\n📈 TOP FEATURES PAR EFFECT SIZE (Cohen's d):")
    print("-" * 85)
    print(f"{'Feature':<25} {'Win Mean':>12} {'Loss Mean':>12} {'Effect':>8} {'Corr':>8} {'Sig':>5}")
    print("-" * 85)
    
    for _, row in results_df.head(20).iterrows():
        print(f"{row['feature']:<25} {row['win_mean']:>12.4f} {row['loss_mean']:>12.4f} {row['effect_size']:>8.3f} {row['correlation']:>8.4f} {row['significance']:>5}")
    
    return results_df

def analyze_categorical_features(df):
    """Analyse les features catégorielles"""
    
    print("\n" + "="*80)
    print("📊 CATEGORICAL FEATURE ANALYSIS")
    print("="*80)
    
    categorical = ['league', 'market_type', 'source', 'convergence_status', 
                   'home_tier', 'away_tier', 'home_form', 'away_form',
                   'home_tier_class', 'away_tier_class', 'league_tier']
    
    for feature in categorical:
        if feature not in df.columns or df[feature].isna().all():
            continue
            
        print(f"\n🔹 {feature.upper()}:")
        print("-" * 60)
        
        grouped = df.groupby(feature).agg({
            'is_winner': ['count', 'sum', 'mean'],
            'profit_loss': 'sum',
            'clv_percentage': 'mean'
        }).round(4)
        
        grouped.columns = ['picks', 'wins', 'win_rate', 'profit', 'avg_clv']
        grouped = grouped.sort_values('win_rate', ascending=False)
        
        for idx, row in grouped.iterrows():
            if row['picks'] >= 5:
                emoji = '🏆' if row['win_rate'] >= 0.55 else '✅' if row['win_rate'] >= 0.45 else '⚠️'
                print(f"  {emoji} {str(idx):<25}: {int(row['picks']):>4} picks, WR={row['win_rate']*100:>5.1f}%, CLV={row['avg_clv']:>+6.2f}%, P/L={row['profit']:>+7.2f}u")

def find_optimal_thresholds(df):
    """Trouve les seuils optimaux pour chaque feature"""
    
    print("\n" + "="*80)
    print("🎯 OPTIMAL THRESHOLDS ANALYSIS")
    print("="*80)
    
    key_features = ['diamond_score', 'clv_percentage', 'edge_pct', 
                    'reality_score', 'odds_taken', 'system_confidence']
    
    for feature in key_features:
        if feature not in df.columns:
            continue
            
        valid_df = df[[feature, 'is_winner', 'profit_loss']].dropna()
        if len(valid_df) < 20:
            continue
            
        print(f"\n🔹 {feature.upper()}:")
        print("-" * 70)
        
        percentiles = [10, 25, 50, 75, 90]
        thresholds = np.percentile(valid_df[feature], percentiles)
        
        for pct, threshold in zip(percentiles, thresholds):
            above = valid_df[valid_df[feature] >= threshold]
            below = valid_df[valid_df[feature] < threshold]
            
            if len(above) >= 5 and len(below) >= 5:
                wr_above = above['is_winner'].mean()
                wr_below = below['is_winner'].mean()
                profit_above = above['profit_loss'].sum()
                
                emoji = '⬆️' if wr_above > wr_below else '⬇️'
                print(f"  P{pct:>2} (>={threshold:>8.2f}): {len(above):>4} picks, WR={wr_above*100:>5.1f}% {emoji} vs {wr_below*100:>5.1f}% | P/L={profit_above:>+7.2f}u")

def analyze_paradox_patterns(df):
    """Analyse les paradoxes découverts"""
    
    print("\n" + "="*80)
    print("🔄 PARADOX PATTERNS ANALYSIS")
    print("="*80)
    
    # Paradoxe diamond_score
    if 'diamond_score' in df.columns:
        print("\n🔹 PARADOXE DIAMOND SCORE:")
        print("-" * 60)
        
        ranges = [(0, 25), (25, 35), (35, 50), (50, 65), (65, 80), (80, 100)]
        for low, high in ranges:
            subset = df[(df['diamond_score'] >= low) & (df['diamond_score'] < high)]
            if len(subset) >= 5:
                wr = subset['is_winner'].mean() * 100
                profit = subset['profit_loss'].sum()
                clv = subset['clv_percentage'].mean()
                print(f"  Score {low:>2}-{high:<2}: {len(subset):>4} picks, WR={wr:>5.1f}%, P/L={profit:>+7.2f}u, CLV={clv:>+5.2f}%")
    
    # Paradoxe edge_pct
    if 'edge_pct' in df.columns:
        print("\n🔹 PARADOXE EDGE PERCENTAGE:")
        print("-" * 60)
        
        categories = [
            ('EXCELLENT (>10%)', df['edge_pct'] >= 10),
            ('GOOD (5-10%)', (df['edge_pct'] >= 5) & (df['edge_pct'] < 10)),
            ('MARGINAL (2-5%)', (df['edge_pct'] >= 2) & (df['edge_pct'] < 5)),
            ('LOW (0-2%)', (df['edge_pct'] >= 0) & (df['edge_pct'] < 2)),
            ('NEGATIVE (<0%)', df['edge_pct'] < 0)
        ]
        
        for name, mask in categories:
            subset = df[mask]
            if len(subset) >= 5:
                wr = subset['is_winner'].mean() * 100
                profit = subset['profit_loss'].sum()
                print(f"  {name:<20}: {len(subset):>4} picks, WR={wr:>5.1f}%, P/L={profit:>+7.2f}u")

def analyze_market_performance(df):
    """Analyse performance par marché"""
    
    print("\n" + "="*80)
    print("🎰 MARKET PERFORMANCE ANALYSIS")
    print("="*80)
    
    if 'market_type' not in df.columns:
        return
    
    market_perf = df.groupby('market_type').agg({
        'is_winner': ['count', 'mean'],
        'profit_loss': 'sum',
        'clv_percentage': 'mean'
    }).round(4)
    
    market_perf.columns = ['picks', 'win_rate', 'profit', 'avg_clv']
    market_perf = market_perf[market_perf['picks'] >= 10].sort_values('profit', ascending=False)
    
    print(f"\n{'Market':<25} {'Picks':>6} {'Win Rate':>10} {'Profit':>10} {'Avg CLV':>10}")
    print("-" * 65)
    
    for market, row in market_perf.iterrows():
        emoji = '🏆' if row['win_rate'] >= 0.55 else '✅' if row['win_rate'] >= 0.45 else '⚠️'
        print(f"{emoji} {market:<23} {int(row['picks']):>6} {row['win_rate']*100:>9.1f}% {row['profit']:>+9.2f}u {row['avg_clv']:>+9.2f}%")

def analyze_league_performance(df):
    """Analyse performance par ligue"""
    
    print("\n" + "="*80)
    print("🏟️ LEAGUE PERFORMANCE ANALYSIS")
    print("="*80)
    
    if 'league' not in df.columns:
        return
    
    league_perf = df.groupby('league').agg({
        'is_winner': ['count', 'mean'],
        'profit_loss': 'sum',
        'clv_percentage': 'mean'
    }).round(4)
    
    league_perf.columns = ['picks', 'win_rate', 'profit', 'avg_clv']
    league_perf = league_perf[league_perf['picks'] >= 10].sort_values('profit', ascending=False)
    
    print(f"\n{'League':<35} {'Picks':>6} {'Win Rate':>10} {'Profit':>10} {'CLV':>8}")
    print("-" * 75)
    
    for league, row in league_perf.iterrows():
        emoji = '🏆' if row['win_rate'] >= 0.55 else '✅' if row['win_rate'] >= 0.45 else '⚠️'
        league_short = str(league)[:32] + '...' if len(str(league)) > 35 else str(league)
        print(f"{emoji} {league_short:<33} {int(row['picks']):>6} {row['win_rate']*100:>9.1f}% {row['profit']:>+9.2f}u {row['avg_clv']:>+7.2f}%")

def generate_ml_recommendations(results_df, df):
    """Génère des recommandations pour le modèle ML"""
    
    print("\n" + "="*80)
    print("💡 ML RECOMMENDATIONS")
    print("="*80)
    
    # Stats globales
    total = len(df)
    wins = df['is_winner'].sum()
    wr = wins / total * 100 if total > 0 else 0
    profit = df['profit_loss'].sum()
    clv_avg = df['clv_percentage'].mean()
    
    print(f"\n📊 STATS GLOBALES:")
    print(f"   Total picks résolus: {total}")
    print(f"   Wins: {int(wins)} ({wr:.1f}%)")
    print(f"   Profit total: {profit:+.2f}u")
    print(f"   CLV moyen: {clv_avg:+.2f}%")
    
    # Top features
    if len(results_df) > 0:
        significant = results_df[results_df['p_value'] < 0.05]
        print(f"\n🎯 FEATURES SIGNIFICATIVES (p<0.05): {len(significant)}")
        for _, row in significant.head(10).iterrows():
            direction = '↑' if row['correlation'] > 0 else '↓'
            print(f"   {direction} {row['feature']}: effect={row['effect_size']:.3f}, corr={row['correlation']:+.4f} {row['significance']}")
        
        print(f"\n⚠️ FEATURES NON-SIGNIFICATIVES:")
        non_sig = results_df[results_df['p_value'] >= 0.05]['feature'].tolist()[:5]
        for f in non_sig:
            print(f"   ❌ {f}")
    
    print("\n📋 ARCHITECTURE ML SUGGÉRÉE:")
    print("   1. XGBoost avec early stopping")
    print("   2. LightGBM pour grande échelle")
    print("   3. Logistic Regression (baseline)")
    print("   4. Neural Network (MLP)")
    
    print("\n🔧 NEXT STEPS:")
    print("   1. Feature engineering sur interactions")
    print("   2. Train/test split temporel (pas random)")
    print("   3. Cross-validation walk-forward")
    print("   4. Hyperparameter tuning")
    print("   5. Model stacking/ensemble")

def main():
    print("\n" + "="*80)
    print("🧠 NIVEAU 3 ML - SMART QUANT 2.0")
    print("   Analyse Scientifique Préliminaire")
    print("="*80)
    print(f"   Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    print("\n�� Chargement du dataset ML...")
    df = load_ml_dataset()
    print(f"   ✅ {len(df)} picks chargés")
    print(f"   ✅ Colonnes: {len(df.columns)}")
    
    if len(df) == 0:
        print("   ❌ Aucun pick résolu trouvé!")
        return
    
    wins = df['is_winner'].sum()
    print(f"   ✅ Wins: {int(wins)} / {len(df)} ({df['is_winner'].mean()*100:.1f}%)")
    
    # Analyses
    results_df = analyze_feature_importance(df)
    analyze_categorical_features(df)
    find_optimal_thresholds(df)
    analyze_paradox_patterns(df)
    analyze_market_performance(df)
    analyze_league_performance(df)
    generate_ml_recommendations(results_df, df)
    
    # Sauvegarder
    output_dir = '/home/Mon_ps/reports/ml'
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    results_df.to_csv(f'{output_dir}/feature_importance_{timestamp}.csv', index=False)
    df.to_csv(f'{output_dir}/ml_dataset_{timestamp}.csv', index=False)
    
    print(f"\n✅ Résultats sauvegardés: {output_dir}/")
    print("\n" + "="*80)
    print("🏁 ANALYSE NIVEAU 3 ML TERMINÉE")
    print("="*80)

if __name__ == "__main__":
    main()
