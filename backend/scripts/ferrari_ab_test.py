#!/usr/bin/env python3
"""
Script de test A/B Ferrari
Compare la baseline avec toutes les variations Ferrari
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime

# Configuration DB
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'postgres'),
    'port': 5432,
    'database': os.getenv('DB_NAME', 'monps_db'),
    'user': os.getenv('DB_USER', 'monps_user'),
    'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
}

def get_current_predictions():
    """Récupère les prédictions récentes"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT 
            match_id,
            agent_name,
            predicted_outcome,
            confidence,
            edge_detected,
            kelly_fraction,
            predicted_at
        FROM agent_predictions
        WHERE predicted_at > NOW() - INTERVAL '24 hours'
        ORDER BY predicted_at DESC
    """)
    
    predictions = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return predictions

def test_variations_on_predictions(predictions):
    """Teste toutes les variations sur les prédictions"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
        SELECT id, variation_name, config, status
        FROM agent_b_variations
        WHERE status = 'active'
        ORDER BY id
    """)
    variations = cursor.fetchall()
    
    results = {
        'baseline': {'count': 0, 'predictions': []},
        'variations': {}
    }
    
    baseline_id = 2  # ID de la baseline
    
    for var in variations:
        var_id = var['id']
        var_name = var['variation_name']
        config = var['config']
        
        # Convertir les seuils en float (ils sont stockés comme strings dans JSON)
        min_confidence = float(config.get('seuils', {}).get('confidence_threshold', 0.7))
        min_spread = float(config.get('seuils', {}).get('min_spread', 2.0))
        
        # Filtrer les prédictions
        filtered = []
        for pred in predictions:
            # Convertir confidence (stockée en pourcentage: 65.00 = 65%)
            confidence = float(pred['confidence']) if pred['confidence'] else 0
            if confidence > 1:  # Si c'est un pourcentage
                confidence = confidence / 100  # Convertir en décimal
            
            # Edge en décimal (0.03 = 3%)
            edge = float(pred['edge_detected']) if pred['edge_detected'] else 0
            
            # Vérifier les seuils
            if confidence >= min_confidence and edge >= min_spread:
                filtered.append(pred)
        
        if var_id == baseline_id:
            results['baseline'] = {
                'count': len(filtered),
                'predictions': filtered[:5]
            }
        else:
            results['variations'][var_name] = {
                'id': var_id,
                'count': len(filtered),
                'config': config
            }
    
    cursor.close()
    conn.close()
    
    return results, variations

def main():
    print("🏎️  FERRARI A/B TEST")
    print("=" * 60)
    print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Récupérer les prédictions
    print("📊 Collecte des prédictions récentes (24h)...")
    predictions = get_current_predictions()
    print(f"   ✅ {len(predictions)} prédictions trouvées")
    print()
    
    if not predictions:
        print("⚠️  Aucune prédiction disponible pour le test")
        return
    
    # Tester les variations
    print("🧪 Test des variations...")
    results, variations = test_variations_on_predictions(predictions)
    print(f"   ✅ {len(variations)} variations testées")
    print()
    
    # Afficher les résultats
    print("📈 RÉSULTATS DU TEST")
    print("=" * 60)
    print()
    
    baseline_count = results['baseline']['count']
    print(f"📊 Baseline: {baseline_count} signaux")
    print()
    
    ferrari_counts = []
    print("🏎️  Variations Ferrari:")
    for var_name, data in sorted(results['variations'].items()):
        count = data['count']
        ferrari_counts.append(count)
        delta = count - baseline_count
        delta_pct = (delta / baseline_count * 100) if baseline_count > 0 else 0
        
        symbol = "📈" if delta > 0 else "📉" if delta < 0 else "➡️ "
        print(f"   {symbol} {var_name:35s}: {count:3d} signaux ({delta:+3d}, {delta_pct:+6.1f}%)")
    
    print()
    
    if ferrari_counts:
        ferrari_total = sum(ferrari_counts)
        ferrari_avg = ferrari_total / len(ferrari_counts)
        
        print(f"🏎️  Ferrari Total: {ferrari_total} signaux")
        print(f"🏎️  Ferrari Moyenne: {ferrari_avg:.1f} signaux")
        print(f"📊 Baseline: {baseline_count} signaux")
        
        if baseline_count > 0:
            improvement = ((ferrari_avg - baseline_count) / baseline_count) * 100
            print(f"📈 Amélioration moyenne: {improvement:+.1f}%")
    
    print()
    print("✅ SUCCÈS - Test A/B terminé")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
