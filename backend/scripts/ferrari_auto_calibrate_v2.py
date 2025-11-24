#!/usr/bin/env python3
"""
Ferrari Auto-Calibration System V2
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime
import numpy as np

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'postgres'),
    'port': 5432,
    'database': os.getenv('DB_NAME', 'monps_db'),
    'user': os.getenv('DB_USER', 'monps_user'),
    'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
}

def analyze_predictions():
    """Analyse les prédictions"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT confidence, edge_detected
        FROM agent_predictions
        WHERE predicted_at > NOW() - INTERVAL '7 days'
          AND confidence IS NOT NULL
          AND edge_detected IS NOT NULL
    """)
    
    predictions = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not predictions:
        return None
    
    confidences = np.array([float(p['confidence']) for p in predictions])
    edges = np.array([float(p['edge_detected']) for p in predictions])
    
    # Convertir confidence en décimal
    confidences = np.where(confidences > 1, confidences / 100, confidences)
    
    # Calculer TOUS les percentiles nécessaires
    return {
        'total': len(predictions),
        'confidence': {
            'min': float(confidences.min()),
            'max': float(confidences.max()),
            'mean': float(confidences.mean()),
            'p20': float(np.percentile(confidences, 20)),
            'p30': float(np.percentile(confidences, 30)),
            'p50': float(np.percentile(confidences, 50)),
            'p70': float(np.percentile(confidences, 70)),
            'p80': float(np.percentile(confidences, 80)),
            'p90': float(np.percentile(confidences, 90)),
        },
        'edge': {
            'min': float(edges.min()),
            'max': float(edges.max()),
            'mean': float(edges.mean()),
            'p20': float(np.percentile(edges, 20)),
            'p30': float(np.percentile(edges, 30)),
            'p50': float(np.percentile(edges, 50)),
            'p70': float(np.percentile(edges, 70)),
            'p80': float(np.percentile(edges, 80)),
            'p90': float(np.percentile(edges, 90)),
        }
    }

def calculate_thresholds(stats, profile='balanced'):
    """Calcule seuils selon profil"""
    profiles = {
        'aggressive': ('p70', 'p70', 'Top 30%'),
        'balanced': ('p80', 'p80', 'Top 20%'),
        'conservative': ('p90', 'p90', 'Top 10%'),
    }
    
    if profile not in profiles:
        profile = 'balanced'
    
    conf_key, edge_key, desc = profiles[profile]
    
    return {
        'confidence_threshold': stats['confidence'][conf_key],
        'min_spread': stats['edge'][edge_key],
        'profile': profile,
        'description': desc
    }

def recreate_variations_with_new_thresholds(stats):
    """Recrée TOUTES les variations avec nouveaux seuils"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Définir les variations avec leurs profils
    variations = [
        (1, 'Ferrari - Forme Récente', 'balanced', {'forme_recente': 1.5}),
        (2, 'Baseline (Contrôle)', 'balanced', {}),
        (3, 'Ferrari - Multi-Facteurs', 'balanced', {'forme_recente': 1.1, 'blessures_cles': 0.8}),
        (4, 'Ferrari - Conservative', 'conservative', {}),
        (5, 'Ferrari - Aggressive', 'aggressive', {}),
        (6, 'Ferrari V3 - Forme Récente', 'balanced', {'forme_recente': 1.5}),
        (7, 'Ferrari V3 - Blessures & Forme', 'balanced', {'forme_recente': 1.2, 'blessures_cles': 0.9}),
        (8, 'Ferrari V3 - Multi-Facteurs', 'balanced', {'forme_recente': 1.1, 'blessures_cles': 0.8}),
        (9, 'Ferrari V3 - Conservative', 'conservative', {}),
        (10, 'Ferrari V3 - Aggressive', 'aggressive', {}),
    ]
    
    # Supprimer toutes les variations existantes
    cursor.execute("DELETE FROM agent_b_variations WHERE id BETWEEN 1 AND 10")
    
    # Recréer avec nouveaux seuils
    for var_id, name, profile, factors in variations:
        thresholds = calculate_thresholds(stats, profile)
        
        config = {
            'seuils': {
                'confidence_threshold': thresholds['confidence_threshold'],
                'min_spread': thresholds['min_spread']
            },
            'facteurs_additionnels': factors
        }
        
        cursor.execute("""
            INSERT INTO agent_b_variations 
            (id, variation_name, description, config, status)
            VALUES (%s, %s, %s, %s, 'active')
        """, (
            var_id,
            name,
            f"Auto-calibré: {thresholds['description']}",
            psycopg2.extras.Json(config)
        ))
    
    conn.commit()
    cursor.close()
    conn.close()

def main():
    print("🤖 FERRARI AUTO-CALIBRATION V2")
    print("=" * 60)
    print()
    
    print("📊 Analyse des prédictions...")
    stats = analyze_predictions()
    
    if not stats:
        print("❌ Aucune donnée")
        return
    
    print(f"   ✅ {stats['total']} prédictions analysées")
    print()
    
    print("📈 Distribution:")
    print(f"   Confidence: {stats['confidence']['min']:.1%} - {stats['confidence']['max']:.1%}")
    print(f"   - Top 30%: ≥{stats['confidence']['p70']:.1%}")
    print(f"   - Top 20%: ≥{stats['confidence']['p80']:.1%}")
    print(f"   - Top 10%: ≥{stats['confidence']['p90']:.1%}")
    print()
    print(f"   Edge: {stats['edge']['min']:.2%} - {stats['edge']['max']:.2%}")
    print(f"   - Top 30%: ≥{stats['edge']['p70']:.2%}")
    print(f"   - Top 20%: ≥{stats['edge']['p80']:.2%}")
    print(f"   - Top 10%: ≥{stats['edge']['p90']:.2%}")
    print()
    
    print("🎯 Seuils calculés:")
    for profile in ['aggressive', 'balanced', 'conservative']:
        t = calculate_thresholds(stats, profile)
        print(f"   {profile:12s}: conf≥{t['confidence_threshold']:.1%}, edge≥{t['min_spread']:.2%}")
    print()
    
    print("💾 Recréation des variations avec nouveaux seuils...")
    recreate_variations_with_new_thresholds(stats)
    print("   ✅ 10 variations recréées")
    print()
    
    print("✅ Calibration terminée!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
