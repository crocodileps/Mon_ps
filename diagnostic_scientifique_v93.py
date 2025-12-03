#!/usr/bin/env python3
"""
🔬 DIAGNOSTIC SCIENTIFIQUE COMPLET - POUR V9.3
"""

import psycopg2
import psycopg2.extras
import os
import json

DB_CONFIG = {
    'host': os.environ.get('POSTGRES_HOST', 'localhost'),
    'port': int(os.environ.get('POSTGRES_PORT', 5432)),
    'dbname': os.environ.get('POSTGRES_DB', 'monps_db'),
    'user': os.environ.get('POSTGRES_USER', 'monps_user'),
    'password': os.environ.get('POSTGRES_PASSWORD', 'monps_secure_password_2024')
}

def analyze_table(cur, table_name):
    print(f"\n{'═'*70}")
    print(f"📋 TABLE: {table_name}")
    print(f"{'═'*70}")
    
    cur.execute(f"""
        SELECT column_name, data_type
        FROM information_schema.columns 
        WHERE table_name = '{table_name}'
        ORDER BY ordinal_position;
    """)
    cols = cur.fetchall()
    
    if not cols:
        print(f"   ❌ Table inexistante")
        return None
    
    print(f"\n   📊 COLONNES ({len(cols)}):")
    col_names = []
    for col, dtype in cols:
        col_names.append(col)
        print(f"      • {col:<35} {dtype}")
    
    try:
        cur.execute(f"SELECT COUNT(*) FROM {table_name};")
        count = cur.fetchone()[0]
        print(f"\n   📈 LIGNES: {count}")
    except:
        count = 0
    
    if count > 0:
        print(f"\n   📝 EXEMPLE (1 ligne):")
        try:
            cur.execute(f"SELECT * FROM {table_name} LIMIT 1;")
            row = cur.fetchone()
            for j, col in enumerate(col_names):
                val = row[j] if j < len(row) else 'N/A'
                val_str = str(val)[:60] + "..." if len(str(val)) > 60 else str(val)
                print(f"      {col}: {val_str}")
        except Exception as e:
            print(f"      ❌ Erreur: {e}")
    
    return {'columns': col_names, 'count': count}

def main():
    print("="*70)
    print("🔬 DIAGNOSTIC SCIENTIFIQUE - STRUCTURES TABLES")
    print("="*70)
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    tables = [
        'team_momentum',
        'team_intelligence', 
        'team_intelligence_history',
        'team_statistics_live',
        'team_aliases',
        'team_class',
        'team_head_to_head',
        'team_mapping',
        'team_name_mapping',
        'team_search',
        'team_market_profiles',
        'tactical_matrix',
        'referee_intelligence',
        'head_to_head',
        'market_traps',
        'reality_check_results',
        'fg_sharp_money',
    ]
    
    results = {}
    for table in tables:
        result = analyze_table(cur, table)
        if result:
            results[table] = result
    
    print("\n" + "="*70)
    print("📊 RÉSUMÉ")
    print("="*70)
    for table, info in results.items():
        status = "✅" if info['count'] > 0 else "⚠️"
        print(f"   {status} {table:<35} {info['count']:>6} lignes")
    
    cur.close()
    conn.close()
    print("\n✅ Diagnostic terminé")

if __name__ == "__main__":
    main()
