#!/usr/bin/env python3
"""
🧠 ML SMART QUANT 2.0 - TEAM-MARKET PROFILER
Identifie le meilleur marché pour chaque équipe
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor, Json
import pandas as pd
import numpy as np
from datetime import datetime
from collections import defaultdict
import json
import warnings
warnings.filterwarnings('ignore')

DB_CONFIG = {
    'host': os.environ.get('POSTGRES_HOST', 'localhost'),
    'port': int(os.environ.get('POSTGRES_PORT', 5432)),
    'dbname': os.environ.get('POSTGRES_DB', 'monps_db'),
    'user': os.environ.get('POSTGRES_USER', 'monps_user'),
    'password': os.environ.get('POSTGRES_PASSWORD', 'monps_secure_password_2024')
}

MARKET_GROUPS = {
    'goals_over': ['over_15', 'over15', 'over_25', 'over25', 'over_35', 'over35'],
    'goals_under': ['under_15', 'under15', 'under_25', 'under25', 'under_35', 'under35'],
    'btts_yes': ['btts_yes'],
    'btts_no': ['btts_no'],
    'home_win': ['home', 'dc_1x', 'dnb_home'],
    'away_win': ['away', 'dc_x2', 'dnb_away'],
    'draw_related': ['draw', 'dc_12']
}

MARKET_TO_GROUP = {}
for group, markets in MARKET_GROUPS.items():
    for m in markets:
        MARKET_TO_GROUP[m] = group

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def convert_to_serializable(obj):
    """Convertit numpy types en Python natifs pour JSON"""
    if isinstance(obj, (np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(i) for i in obj]
    return obj

def load_team_market_data():
    """Charge les données avec les BONNES colonnes"""
    conn = get_connection()
    
    query = """
    SELECT 
        t.home_team,
        t.away_team,
        t.market_type,
        t.is_winner,
        t.profit_loss,
        t.clv_percentage,
        t.odds_taken,
        t.diamond_score,
        t.league,
        t.created_at,
        
        -- Stats team_intelligence (home)
        ti_h.home_goals_scored_avg,
        ti_h.home_goals_conceded_avg,
        ti_h.home_btts_rate,
        ti_h.home_over25_rate,
        ti_h.home_win_rate,
        ti_h.home_clean_sheet_rate,
        
        -- Stats team_intelligence (away)
        ti_a.away_goals_scored_avg,
        ti_a.away_goals_conceded_avg,
        ti_a.away_btts_rate,
        ti_a.away_over25_rate,
        ti_a.away_win_rate,
        ti_a.away_clean_sheet_rate,
        
        -- Stats team_statistics_live
        ts_h.btts_pct as home_btts_pct_live,
        ts_h.over_25_pct as home_over25_pct_live,
        ts_a.btts_pct as away_btts_pct_live,
        ts_a.over_25_pct as away_over25_pct_live,
        
        -- Team Class
        tc_h.tier as home_tier,
        tc_a.tier as away_tier
        
    FROM tracking_clv_picks t
    LEFT JOIN team_intelligence ti_h ON t.home_team = ti_h.team_name
    LEFT JOIN team_intelligence ti_a ON t.away_team = ti_a.team_name
    LEFT JOIN team_statistics_live ts_h ON t.home_team = ts_h.team_name
    LEFT JOIN team_statistics_live ts_a ON t.away_team = ts_a.team_name
    LEFT JOIN team_class tc_h ON t.home_team = tc_h.team_name
    LEFT JOIN team_class tc_a ON t.away_team = tc_a.team_name
    WHERE t.is_winner IS NOT NULL
      AND t.home_team IS NOT NULL
      AND t.away_team IS NOT NULL
    ORDER BY t.created_at DESC
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def analyze_team_market_performance(df):
    """Analyse la performance de chaque marché pour chaque équipe"""
    
    print("\n" + "="*80)
    print("📊 ANALYSE TEAM-MARKET PERFORMANCE")
    print("="*80)
    
    team_profiles = defaultdict(lambda: defaultdict(dict))
    
    # ÉQUIPES À DOMICILE
    print("\n🏠 TOP ÉQUIPES À DOMICILE (par profit):")
    print("-" * 80)
    
    home_results = []
    for team in df['home_team'].unique():
        team_df = df[df['home_team'] == team]
        if len(team_df) < 5:
            continue
        
        market_stats = []
        for market in team_df['market_type'].unique():
            market_picks = team_df[team_df['market_type'] == market]
            if len(market_picks) < 3:
                continue
            
            wins = int(market_picks['is_winner'].sum())
            total = len(market_picks)
            win_rate = wins / total
            profit = float(market_picks['profit_loss'].sum())
            avg_clv = market_picks['clv_percentage'].mean()
            roi = profit / total if total > 0 else 0
            
            clv_score = (avg_clv + 10) / 20 if not pd.isna(avg_clv) else 0.5
            composite_score = win_rate * 40 + min(max(roi + 1, 0), 2) * 15 + clv_score * 30
            
            market_stats.append({
                'market': market,
                'market_group': MARKET_TO_GROUP.get(market, 'other'),
                'picks': int(total),
                'wins': wins,
                'win_rate': float(win_rate),
                'profit': profit,
                'roi': float(roi),
                'avg_clv': float(avg_clv) if not pd.isna(avg_clv) else 0.0,
                'composite_score': float(composite_score)
            })
        
        if not market_stats:
            continue
        
        market_stats = sorted(market_stats, key=lambda x: x['composite_score'], reverse=True)
        
        team_profiles[team]['home'] = {
            'total_picks': int(len(team_df)),
            'best_market': market_stats[0] if market_stats else None,
            'all_markets': market_stats[:5],
            'avoid_markets': [m for m in market_stats if m['win_rate'] < 0.4 and m['profit'] < -2]
        }
        
        if market_stats and market_stats[0]['profit'] > 0:
            home_results.append({
                'team': team,
                'picks': len(team_df),
                'best_market': market_stats[0]['market'],
                'win_rate': market_stats[0]['win_rate'],
                'profit': market_stats[0]['profit']
            })
    
    # Afficher top 15 par profit
    home_results = sorted(home_results, key=lambda x: x['profit'], reverse=True)[:15]
    for r in home_results:
        print(f"  🏠 {r['team']:<28}: {r['picks']:>3} picks | {r['best_market']:<12} WR={r['win_rate']*100:>5.1f}% P/L={r['profit']:>+6.2f}u")
    
    # ÉQUIPES À L'EXTÉRIEUR
    print("\n✈️ TOP ÉQUIPES À L'EXTÉRIEUR (par profit):")
    print("-" * 80)
    
    away_results = []
    for team in df['away_team'].unique():
        team_df = df[df['away_team'] == team]
        if len(team_df) < 5:
            continue
        
        market_stats = []
        for market in team_df['market_type'].unique():
            market_picks = team_df[team_df['market_type'] == market]
            if len(market_picks) < 3:
                continue
            
            wins = int(market_picks['is_winner'].sum())
            total = len(market_picks)
            win_rate = wins / total
            profit = float(market_picks['profit_loss'].sum())
            avg_clv = market_picks['clv_percentage'].mean()
            roi = profit / total if total > 0 else 0
            
            clv_score = (avg_clv + 10) / 20 if not pd.isna(avg_clv) else 0.5
            composite_score = win_rate * 40 + min(max(roi + 1, 0), 2) * 15 + clv_score * 30
            
            market_stats.append({
                'market': market,
                'market_group': MARKET_TO_GROUP.get(market, 'other'),
                'picks': int(total),
                'wins': wins,
                'win_rate': float(win_rate),
                'profit': profit,
                'roi': float(roi),
                'avg_clv': float(avg_clv) if not pd.isna(avg_clv) else 0.0,
                'composite_score': float(composite_score)
            })
        
        if not market_stats:
            continue
        
        market_stats = sorted(market_stats, key=lambda x: x['composite_score'], reverse=True)
        
        team_profiles[team]['away'] = {
            'total_picks': int(len(team_df)),
            'best_market': market_stats[0] if market_stats else None,
            'all_markets': market_stats[:5],
            'avoid_markets': [m for m in market_stats if m['win_rate'] < 0.4 and m['profit'] < -2]
        }
        
        if market_stats and market_stats[0]['profit'] > 0:
            away_results.append({
                'team': team,
                'picks': len(team_df),
                'best_market': market_stats[0]['market'],
                'win_rate': market_stats[0]['win_rate'],
                'profit': market_stats[0]['profit']
            })
    
    away_results = sorted(away_results, key=lambda x: x['profit'], reverse=True)[:15]
    for r in away_results:
        print(f"  ✈️ {r['team']:<28}: {r['picks']:>3} picks | {r['best_market']:<12} WR={r['win_rate']*100:>5.1f}% P/L={r['profit']:>+6.2f}u")
    
    return dict(team_profiles)

def analyze_market_correlations(df):
    """Corrélation stats équipe → succès marché"""
    
    print("\n" + "="*80)
    print("🔬 CORRÉLATION STATS ÉQUIPE → MARCHÉ OPTIMAL")
    print("="*80)
    
    stats_cols = [
        ('home_goals_scored_avg', 'Home Goals Scored'),
        ('home_goals_conceded_avg', 'Home Goals Conceded'),
        ('home_btts_rate', 'Home BTTS Rate'),
        ('home_over25_rate', 'Home Over25 Rate'),
        ('away_goals_scored_avg', 'Away Goals Scored'),
        ('away_goals_conceded_avg', 'Away Goals Conceded'),
        ('away_btts_rate', 'Away BTTS Rate'),
        ('away_over25_rate', 'Away Over25 Rate')
    ]
    
    for market_group, markets in MARKET_GROUPS.items():
        group_df = df[df['market_type'].isin(markets)]
        if len(group_df) < 20:
            continue
        
        wins = group_df[group_df['is_winner'] == True]
        losses = group_df[group_df['is_winner'] == False]
        
        if len(wins) < 5 or len(losses) < 5:
            continue
        
        print(f"\n📊 {market_group.upper()}:")
        print("-" * 60)
        
        for col, name in stats_cols:
            if col not in group_df.columns:
                continue
            
            win_mean = wins[col].dropna().mean()
            loss_mean = losses[col].dropna().mean()
            
            if pd.isna(win_mean) or pd.isna(loss_mean):
                continue
            
            diff = win_mean - loss_mean
            if abs(diff) > 0.03:
                direction = '↑' if diff > 0 else '↓'
                sig = '**' if abs(diff) > 0.1 else '*'
                print(f"  {direction} {name:<20}: Win={win_mean:>6.2f} vs Loss={loss_mean:>6.2f} (diff={diff:>+.2f}) {sig}")

def generate_smart_rules(team_profiles):
    """Génère les règles smart"""
    
    print("\n" + "="*80)
    print("🎯 RÈGLES SMART GÉNÉRÉES")
    print("="*80)
    
    rules = []
    
    # BTTS Spécialistes
    btts_teams = []
    for team, profile in team_profiles.items():
        for loc in ['home', 'away']:
            if loc in profile and profile[loc].get('best_market'):
                best = profile[loc]['best_market']
                if best['market_group'] in ['btts_yes', 'btts_no'] and best['win_rate'] > 0.55 and best['profit'] > 0:
                    btts_teams.append({
                        'team': team, 'location': loc, 'market': best['market'],
                        'win_rate': best['win_rate'], 'profit': best['profit']
                    })
    
    if btts_teams:
        print("\n🎲 ÉQUIPES BTTS SPÉCIALISTES:")
        for t in sorted(btts_teams, key=lambda x: x['profit'], reverse=True)[:10]:
            print(f"  • {t['team']} ({t['location']}): {t['market']} → WR={t['win_rate']*100:.1f}%, P/L={t['profit']:+.2f}u")
        rules.append({'name': 'btts_specialists', 'teams': convert_to_serializable(btts_teams[:20])})
    
    # Over Spécialistes
    over_teams = []
    for team, profile in team_profiles.items():
        for loc in ['home', 'away']:
            if loc in profile and profile[loc].get('best_market'):
                best = profile[loc]['best_market']
                if best['market_group'] == 'goals_over' and best['win_rate'] > 0.55 and best['profit'] > 0:
                    over_teams.append({
                        'team': team, 'location': loc, 'market': best['market'],
                        'win_rate': best['win_rate'], 'profit': best['profit']
                    })
    
    if over_teams:
        print("\n⚽ ÉQUIPES OVER SPÉCIALISTES:")
        for t in sorted(over_teams, key=lambda x: x['profit'], reverse=True)[:10]:
            print(f"  • {t['team']} ({t['location']}): {t['market']} → WR={t['win_rate']*100:.1f}%, P/L={t['profit']:+.2f}u")
        rules.append({'name': 'over_specialists', 'teams': convert_to_serializable(over_teams[:20])})
    
    # Under Spécialistes
    under_teams = []
    for team, profile in team_profiles.items():
        for loc in ['home', 'away']:
            if loc in profile and profile[loc].get('best_market'):
                best = profile[loc]['best_market']
                if best['market_group'] == 'goals_under' and best['win_rate'] > 0.55 and best['profit'] > 0:
                    under_teams.append({
                        'team': team, 'location': loc, 'market': best['market'],
                        'win_rate': best['win_rate'], 'profit': best['profit']
                    })
    
    if under_teams:
        print("\n🛡️ ÉQUIPES UNDER SPÉCIALISTES:")
        for t in sorted(under_teams, key=lambda x: x['profit'], reverse=True)[:10]:
            print(f"  • {t['team']} ({t['location']}): {t['market']} → WR={t['win_rate']*100:.1f}%, P/L={t['profit']:+.2f}u")
        rules.append({'name': 'under_specialists', 'teams': convert_to_serializable(under_teams[:20])})
    
    # Marchés à éviter
    avoid_patterns = []
    for team, profile in team_profiles.items():
        for loc in ['home', 'away']:
            if loc in profile and profile[loc].get('avoid_markets'):
                for m in profile[loc]['avoid_markets'][:3]:
                    avoid_patterns.append({
                        'team': team, 'location': loc, 'market': m['market'],
                        'win_rate': m['win_rate'], 'loss': m['profit']
                    })
    
    if avoid_patterns:
        print("\n⚠️ MARCHÉS À ÉVITER:")
        for p in sorted(avoid_patterns, key=lambda x: x['loss'])[:10]:
            print(f"  ❌ {p['team']} ({p['location']}): ÉVITER {p['market']} → WR={p['win_rate']*100:.1f}%, P/L={p['loss']:+.2f}u")
        rules.append({'name': 'avoid_markets', 'patterns': convert_to_serializable(avoid_patterns[:30])})
    
    return rules

def save_to_db(team_profiles, rules):
    """Sauvegarde en base de données"""
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Créer table si nécessaire
    cur.execute("""
        CREATE TABLE IF NOT EXISTS team_market_profiles (
            id SERIAL PRIMARY KEY,
            team_name VARCHAR(100) NOT NULL,
            location VARCHAR(10) NOT NULL,
            best_market VARCHAR(50),
            best_market_group VARCHAR(50),
            win_rate DECIMAL(5,4),
            profit DECIMAL(10,2),
            picks_count INTEGER,
            composite_score DECIMAL(6,2),
            all_markets JSONB,
            avoid_markets JSONB,
            updated_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(team_name, location)
        )
    """)
    
    count = 0
    for team, profile in team_profiles.items():
        for location in ['home', 'away']:
            if location not in profile:
                continue
            
            loc_profile = profile[location]
            best = loc_profile.get('best_market')
            
            if not best:
                continue
            
            # Convertir pour JSON
            all_markets = convert_to_serializable(loc_profile.get('all_markets', []))
            avoid_markets = convert_to_serializable(loc_profile.get('avoid_markets', []))
            
            cur.execute("""
                INSERT INTO team_market_profiles 
                (team_name, location, best_market, best_market_group, win_rate, profit, 
                 picks_count, composite_score, all_markets, avoid_markets, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (team_name, location) 
                DO UPDATE SET
                    best_market = EXCLUDED.best_market,
                    best_market_group = EXCLUDED.best_market_group,
                    win_rate = EXCLUDED.win_rate,
                    profit = EXCLUDED.profit,
                    picks_count = EXCLUDED.picks_count,
                    composite_score = EXCLUDED.composite_score,
                    all_markets = EXCLUDED.all_markets,
                    avoid_markets = EXCLUDED.avoid_markets,
                    updated_at = NOW()
            """, (
                team,
                location,
                best['market'],
                best['market_group'],
                best['win_rate'],
                best['profit'],
                loc_profile['total_picks'],
                best['composite_score'],
                Json(all_markets),
                Json(avoid_markets)
            ))
            count += 1
    
    # Sauvegarder règles
    cur.execute("""
        CREATE TABLE IF NOT EXISTS smart_market_rules (
            id SERIAL PRIMARY KEY,
            rule_name VARCHAR(100) NOT NULL UNIQUE,
            rule_data JSONB,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    for rule in rules:
        rule_data = convert_to_serializable(rule)
        cur.execute("""
            INSERT INTO smart_market_rules (rule_name, rule_data, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (rule_name) DO UPDATE SET
                rule_data = EXCLUDED.rule_data,
                updated_at = NOW()
        """, (rule['name'], Json(rule_data)))
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"\n✅ {count} profils équipes sauvegardés")
    print(f"✅ {len(rules)} règles smart sauvegardées")

def test_recommendations(team_profiles):
    """Test de recommandation pour quelques matchs"""
    
    print("\n" + "="*80)
    print("🧪 TEST DE RECOMMANDATION")
    print("="*80)
    
    # Trouver des équipes avec profils
    teams_with_home = [t for t, p in team_profiles.items() if 'home' in p]
    teams_with_away = [t for t, p in team_profiles.items() if 'away' in p]
    
    if not teams_with_home or not teams_with_away:
        print("  Pas assez de profils pour tester")
        return
    
    # Tester 5 combinaisons aléatoires
    import random
    for _ in range(5):
        home = random.choice(teams_with_home)
        away = random.choice(teams_with_away)
        
        if home == away:
            continue
        
        print(f"\n📌 {home} vs {away}:")
        
        recommendations = []
        
        if 'home' in team_profiles.get(home, {}):
            best = team_profiles[home]['home'].get('best_market')
            if best:
                recommendations.append({
                    'source': f'{home} (home)',
                    'market': best['market'],
                    'group': best['market_group'],
                    'score': best['composite_score'],
                    'wr': best['win_rate'],
                    'profit': best['profit']
                })
        
        if 'away' in team_profiles.get(away, {}):
            best = team_profiles[away]['away'].get('best_market')
            if best:
                recommendations.append({
                    'source': f'{away} (away)',
                    'market': best['market'],
                    'group': best['market_group'],
                    'score': best['composite_score'],
                    'wr': best['win_rate'],
                    'profit': best['profit']
                })
        
        if recommendations:
            recommendations = sorted(recommendations, key=lambda x: x['score'], reverse=True)
            
            # Vérifier consensus
            if len(recommendations) >= 2 and recommendations[0]['group'] == recommendations[1]['group']:
                consensus = "✅ CONSENSUS"
            else:
                consensus = "⚠️ DIVERGENCE"
            
            print(f"   {consensus}")
            for r in recommendations:
                print(f"   └─ {r['source']}: {r['market']} (WR={r['wr']*100:.1f}%, P/L={r['profit']:+.2f}u)")

def main():
    print("\n" + "="*80)
    print("🧠 ML SMART QUANT 2.0 - TEAM-MARKET PROFILER")
    print("="*80)
    print(f"   Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    print("\n📂 Chargement des données...")
    df = load_team_market_data()
    print(f"   ✅ {len(df)} picks chargés")
    print(f"   ✅ {df['home_team'].nunique()} équipes domicile")
    print(f"   ✅ {df['away_team'].nunique()} équipes extérieur")
    print(f"   ✅ {df['market_type'].nunique()} types de marchés")
    
    team_profiles = analyze_team_market_performance(df)
    print(f"\n✅ {len(team_profiles)} équipes profilées")
    
    analyze_market_correlations(df)
    
    rules = generate_smart_rules(team_profiles)
    
    save_to_db(team_profiles, rules)
    
    test_recommendations(team_profiles)
    
    print("\n" + "="*80)
    print("📋 RÉSUMÉ")
    print("="*80)
    print(f"""
    ✅ MODÈLE CRÉÉ:
       • {len(team_profiles)} équipes profilées
       • {len(rules)} règles smart
       • Tables: team_market_profiles, smart_market_rules
       
    🎯 UTILISATION:
       1. Avant chaque match → consulter profil équipes
       2. Choisir le marché avec meilleur score
       3. Éviter marchés dans liste "avoid"
    """)
    
    print("="*80)
    print("🏁 TEAM-MARKET PROFILER TERMINÉ")
    print("="*80)

if __name__ == "__main__":
    main()
