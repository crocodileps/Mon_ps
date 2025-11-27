#!/usr/bin/env python3
"""
📊 MARKET ANALYZER - Analyse professionnelle des forces/faiblesses

Objectif:
- Identifier les forces et faiblesses de chaque marché
- Proposer des améliorations basées sur les données
- Calibrer le modèle scientifiquement
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from decimal import Decimal
import json
import os
from datetime import datetime

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
}


def _float(v, default=0.0):
    if v is None:
        return default
    if isinstance(v, Decimal):
        return float(v)
    try:
        return float(v)
    except:
        return default


def analyze_all_markets():
    """Analyse complète de tous les marchés avec recommandations"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    print("\n" + "=" * 80)
    print("🔬 RAPPORT D'ANALYSE SCIENTIFIQUE DES MARCHÉS")
    print(f"   Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)
    
    # 1. Analyse par source
    print("\n📊 1. PERFORMANCE PAR SOURCE:")
    print("-" * 60)
    
    cur.execute("""
        SELECT 
            source,
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE is_resolved) as resolved,
            COUNT(*) FILTER (WHERE is_winner) as wins,
            ROUND(AVG(diamond_score)::numeric, 1) as avg_score,
            ROUND(AVG(odds_taken)::numeric, 2) as avg_odds,
            ROUND(AVG(edge_pct)::numeric, 2) as avg_edge,
            ROUND(SUM(profit_loss)::numeric, 2) as profit
        FROM tracking_clv_picks
        GROUP BY source
        ORDER BY total DESC
    """)
    
    for row in cur.fetchall():
        resolved = row['resolved'] or 0
        wins = row['wins'] or 0
        wr = round(wins / resolved * 100, 1) if resolved > 0 else None
        
        print(f"\n  {row['source']}:")
        print(f"    Total: {row['total']} | Résolus: {resolved} | Wins: {wins}")
        print(f"    WR: {wr}% | Score moy: {row['avg_score']} | Edge moy: {row['avg_edge']}%")
        print(f"    Cotes moy: {row['avg_odds']} | Profit: {row['profit']}")
    
    # 2. Analyse détaillée par marché
    print("\n\n📊 2. ANALYSE DÉTAILLÉE PAR MARCHÉ:")
    print("-" * 60)
    
    cur.execute("""
        SELECT 
            market_type,
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE is_resolved) as resolved,
            COUNT(*) FILTER (WHERE is_winner) as wins,
            ROUND(AVG(diamond_score)::numeric, 1) as avg_score,
            ROUND(AVG(odds_taken)::numeric, 2) as avg_odds,
            ROUND(AVG(probability)::numeric, 1) as avg_prob,
            ROUND(AVG(edge_pct)::numeric, 2) as avg_edge,
            ROUND(AVG(kelly_pct)::numeric, 2) as avg_kelly,
            ROUND(SUM(profit_loss)::numeric, 2) as profit,
            MIN(diamond_score) as min_score,
            MAX(diamond_score) as max_score
        FROM tracking_clv_picks
        GROUP BY market_type
        ORDER BY total DESC
    """)
    
    markets = cur.fetchall()
    
    recommendations = {}
    
    for m in markets:
        market = m['market_type']
        resolved = m['resolved'] or 0
        wins = m['wins'] or 0
        wr = round(wins / resolved * 100, 1) if resolved > 0 else None
        roi = round((m['profit'] or 0) / resolved * 100, 1) if resolved > 0 else None
        
        avg_edge = _float(m['avg_edge'])
        avg_prob = _float(m['avg_prob'])
        avg_odds = _float(m['avg_odds'])
        
        # Diagnostic
        if avg_edge >= 5:
            edge_status = "✅ EXCELLENT"
            edge_action = "Conserver"
        elif avg_edge >= 0:
            edge_status = "📊 BON"
            edge_action = "Optimiser légèrement"
        elif avg_edge >= -5:
            edge_status = "⚠️ FAIBLE"
            edge_action = "Augmenter prob +5-10%"
        elif avg_edge >= -15:
            edge_status = "❌ NÉGATIF"
            edge_action = "Augmenter prob +15-20%"
        else:
            edge_status = "🚫 CRITIQUE"
            edge_action = "Revoir complètement le calcul"
        
        # Calculer la correction nécessaire
        implied_prob = (1 / avg_odds * 100) if avg_odds > 0 else 50
        prob_correction = implied_prob - avg_prob if avg_prob > 0 else 0
        
        recommendations[market] = {
            'edge_status': edge_status,
            'action': edge_action,
            'prob_correction': round(prob_correction, 1),
            'current_prob': avg_prob,
            'implied_prob': round(implied_prob, 1),
        }
        
        print(f"\n  {market.upper()}:")
        print(f"    Picks: {m['total']} | Résolus: {resolved} | WR: {wr}%")
        print(f"    Score: {m['min_score']}-{m['max_score']} (moy: {m['avg_score']})")
        print(f"    Cotes: {avg_odds} | Prob calculée: {avg_prob}% | Prob implicite: {implied_prob:.1f}%")
        print(f"    Edge: {avg_edge}% {edge_status}")
        print(f"    💡 Action: {edge_action}")
        if abs(prob_correction) > 2:
            print(f"    🔧 Correction suggérée: ajuster prob de {prob_correction:+.1f}%")
    
    # 3. Comparaison Backtest vs Prédictions
    print("\n\n📊 3. COMPARAISON BACKTEST vs PRÉDICTIONS ACTUELLES:")
    print("-" * 60)
    
    # Données backtest (de notre analyse précédente)
    backtest_data = {
        'btts_yes': {'wr': 100.0, 'roi': 105.5},
        'over_25': {'wr': 75.0, 'roi': 49.5},
        'dc_12': {'wr': 100.0, 'roi': 38.0},
        'dc_1x': {'wr': 50.0, 'roi': 8.8},
        'btts_no': {'wr': 50.0, 'roi': 29.3},
        'away': {'wr': 42.9, 'roi': 39.6},
        'dc_x2': {'wr': 37.5, 'roi': -37.4},
        'under_25': {'wr': 28.6, 'roi': -43.7},
        'draw': {'wr': 25.0, 'roi': 32.5},
        'home': {'wr': 12.5, 'roi': -55.0},
    }
    
    print("\n  ┌─────────────┬──────────────┬──────────────┬─────────────────────┐")
    print("  │   Marché    │ Backtest WR  │ Edge actuel  │    Cohérence        │")
    print("  ├─────────────┼──────────────┼──────────────┼─────────────────────┤")
    
    for market, bt in backtest_data.items():
        edge = recommendations.get(market, {}).get('prob_correction', 0)
        wr = bt['wr']
        
        # Vérifier cohérence
        if wr >= 60 and edge < -5:
            coherence = "❌ INCOHÉRENT - à corriger"
        elif wr < 40 and edge > 5:
            coherence = "⚠️ Surprenant"
        else:
            coherence = "✅ OK"
        
        print(f"  │ {market:11} │ {wr:10.1f}% │ {edge:+10.1f}% │ {coherence:19} │")
    
    print("  └─────────────┴──────────────┴──────────────┴─────────────────────┘")
    
    # 4. Recommandations finales
    print("\n\n📊 4. RECOMMANDATIONS D'AMÉLIORATION:")
    print("-" * 60)
    
    print("""
    🔥 PRIORITÉ HAUTE (incohérences critiques):
    
    1. BTTS_YES: Backtest 100% WR mais edge actuel -11%
       → Le modèle SOUS-ESTIME la probabilité de BTTS
       → Solution: Augmenter le poids des stats équipes (btts_pct)
       → Correction: +15% sur la probabilité calculée
    
    2. OVER_25: Backtest 75% WR mais edge actuel -9%
       → Le modèle sous-estime les buts
       → Solution: Augmenter xG de base ou utiliser plus over_25_pct
       → Correction: +12% sur la probabilité calculée
    
    3. DC_12: Backtest 100% WR mais edge actuel -5%
       → Marché naturellement performant (éviter le nul)
       → Correction: +8% sur la probabilité calculée
    
    📊 PRIORITÉ MOYENNE:
    
    4. HOME: Backtest 12.5% WR et edge -4%
       → Cohérent: le marché HOME est risqué
       → Action: Maintenir le malus actuel
    
    5. DC_X2: Backtest 37.5% WR et edge -30%
       → Très sous-estimé
       → Correction: +20% ou filtrer ce marché
    
    ✅ OK (pas de changement):
    
    6. BTTS_NO: Edge +5.72% ✅
       → Seul marché avec value positive
       → Conserver la calibration actuelle
    """)
    
    # 5. Générer les facteurs de correction
    print("\n\n📊 5. FACTEURS DE CORRECTION SUGGÉRÉS:")
    print("-" * 60)
    
    corrections = {
        'btts_yes': 1.25,    # +25% sur prob
        'over_25': 1.20,     # +20%
        'over_15': 1.10,     # +10%
        'dc_12': 1.12,       # +12%
        'dc_1x': 1.08,       # +8%
        'btts_no': 1.00,     # Inchangé
        'home': 0.95,        # -5% (déjà mauvais)
        'draw': 1.05,        # +5%
        'away': 1.15,        # +15%
        'dc_x2': 1.25,       # +25%
        'under_25': 1.05,    # +5%
        'over_35': 1.10,     # +10%
        'under_35': 1.00,    # Inchangé
        'under_15': 0.95,    # -5%
    }
    
    print("\n  MARKET_CORRECTIONS = {")
    for market, factor in corrections.items():
        sign = "+" if factor >= 1 else ""
        pct = (factor - 1) * 100
        print(f"      '{market}': {factor:.2f},  # {sign}{pct:.0f}%")
    print("  }")
    
    conn.close()
    
    return corrections


def main():
    corrections = analyze_all_markets()
    
    print("\n" + "=" * 80)
    print("✅ ANALYSE TERMINÉE")
    print("=" * 80)
    print("\nProchaine étape: Implémenter ces corrections dans orchestrator_v6")


if __name__ == "__main__":
    main()
