#!/usr/bin/env python3
"""
AUDIT SCIENTIFIQUE - Vérification EXACTE de toutes les colonnes
Pas d'hypothèses, que des faits !
"""

import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

print("="*80)
print("🔬 AUDIT SCIENTIFIQUE - COLONNES EXACTES DE CHAQUE TABLE")
print("="*80)

# Liste des tables à auditer
tables = [
    'team_intelligence',
    'team_class', 
    'team_momentum',
    'head_to_head',
    'tactical_matrix',
    'referee_intelligence',
    'coach_intelligence',
    'scorer_intelligence',
    'market_patterns',
    'market_traps',
    'match_results',
    'odds_history',
]

for table in tables:
    print(f"\n{'═'*80}")
    print(f"📋 TABLE: {table}")
    print(f"{'═'*80}")
    
    # Vérifier si la table existe
    cur.execute("""
        SELECT COUNT(*) FROM information_schema.tables 
        WHERE table_name = %s
    """, (table,))
    
    if cur.fetchone()[0] == 0:
        print("   ❌ TABLE N'EXISTE PAS")
        continue
    
    # Nombre de lignes
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    row_count = cur.fetchone()[0]
    print(f"   Lignes: {row_count}")
    
    # Toutes les colonnes
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = %s 
        ORDER BY ordinal_position
    """, (table,))
    
    cols = cur.fetchall()
    print(f"   Colonnes ({len(cols)}):")
    for col in cols:
        print(f"      - {col['column_name']:40} ({col['data_type']})")
    
    # Exemple de données (première ligne)
    if row_count > 0:
        cur.execute(f"SELECT * FROM {table} LIMIT 1")
        row = cur.fetchone()
        print(f"\n   Exemple de données:")
        for key in list(row.keys())[:10]:  # Premiers 10 champs
            val = row[key]
            if val is not None:
                val_str = str(val)[:50] + "..." if len(str(val)) > 50 else str(val)
                print(f"      {key}: {val_str}")

print("\n" + "="*80)
print("✅ AUDIT TERMINÉ")
print("="*80)

cur.close()
conn.close()
