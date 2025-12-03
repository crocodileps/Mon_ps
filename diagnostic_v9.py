#!/usr/bin/env python3
"""
🔍 DIAGNOSTIC V9.1 - Identifier pourquoi les layers retournent 0
"""

import psycopg2
import psycopg2.extras
import os

DB_CONFIG = {
    'host': os.environ.get('POSTGRES_HOST', 'localhost'),
    'port': int(os.environ.get('POSTGRES_PORT', 5432)),
    'dbname': os.environ.get('POSTGRES_DB', 'monps_db'),
    'user': os.environ.get('POSTGRES_USER', 'monps_user'),
    'password': os.environ.get('POSTGRES_PASSWORD', 'monps_secure_password_2024')
}

def main():
    print("="*70)
    print("🔍 DIAGNOSTIC V9.1 - ANALYSE DES DONNÉES")
    print("="*70)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connexion DB OK\n")
    except Exception as e:
        print(f"❌ Erreur DB: {e}")
        return
    
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # 1. TEAM_MOMENTUM
    print("═" * 70)
    print("1. TEAM_MOMENTUM - Noms d'équipes disponibles")
    print("═" * 70)
    cur.execute("SELECT DISTINCT team_name FROM team_momentum ORDER BY team_name LIMIT 20;")
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"   • {r['team_name']}")
    else:
        print("   ❌ TABLE VIDE!")
    
    print("\n   Recherche 'Liverpool' ou 'City':")
    cur.execute("""
        SELECT team_name, momentum_score 
        FROM team_momentum 
        WHERE LOWER(team_name) LIKE '%liver%' 
           OR LOWER(team_name) LIKE '%city%'
           OR LOWER(team_name) LIKE '%manch%'
        LIMIT 5;
    """)
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"   ✅ {r['team_name']} - Score: {r['momentum_score']}")
    else:
        print("   ❌ Aucun match trouvé!")
    
    # 2. TACTICAL_MATRIX
    print("\n" + "═" * 70)
    print("2. TACTICAL_MATRIX - Styles disponibles")
    print("═" * 70)
    cur.execute("SELECT DISTINCT style_a FROM tactical_matrix UNION SELECT DISTINCT style_b FROM tactical_matrix;")
    rows = cur.fetchall()
    if rows:
        styles = [r[0] for r in rows]
        print(f"   Styles: {', '.join(styles)}")
    else:
        print("   ❌ TABLE VIDE!")
    
    print("\n   Recherche 'pressing vs possession':")
    cur.execute("""
        SELECT style_a, style_b, btts_probability, over_25_probability, sample_size
        FROM tactical_matrix
        WHERE (LOWER(style_a) IN ('pressing', 'possession') AND LOWER(style_b) IN ('pressing', 'possession'))
           OR (LOWER(style_a) = 'balanced' OR LOWER(style_b) = 'balanced')
        ORDER BY sample_size DESC
        LIMIT 5;
    """)
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"   ✅ {r['style_a']} vs {r['style_b']} - BTTS: {r['btts_probability']}%, O25: {r['over_25_probability']}%")
    else:
        print("   ❌ Aucun match trouvé!")
    
    # 3. REFEREE_INTELLIGENCE
    print("\n" + "═" * 70)
    print("3. REFEREE_INTELLIGENCE - Arbitres Premier League")
    print("═" * 70)
    cur.execute("""
        SELECT referee_name, league, avg_goals_per_game, under_over_tendency
        FROM referee_intelligence
        WHERE LOWER(league) LIKE '%premier%' OR LOWER(league) LIKE '%england%'
        LIMIT 10;
    """)
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"   ✅ {r['referee_name']} ({r['league']}) - {r['avg_goals_per_game']} buts/match, {r['under_over_tendency']}")
    else:
        print("   ❌ Aucun arbitre Premier League!")
    
    cur.execute("""
        SELECT referee_name, league FROM referee_intelligence 
        WHERE LOWER(referee_name) LIKE '%oliver%' OR LOWER(referee_name) LIKE '%taylor%'
        LIMIT 5;
    """)
    rows = cur.fetchall()
    if rows:
        print("\n   Recherche 'Oliver' ou 'Taylor':")
        for r in rows:
            print(f"   ✅ {r['referee_name']} - {r['league']}")
    else:
        print("\n   ❌ Oliver/Taylor non trouvés!")
    
    # 4. HEAD_TO_HEAD
    print("\n" + "═" * 70)
    print("4. HEAD_TO_HEAD / TEAM_HEAD_TO_HEAD")
    print("═" * 70)
    cur.execute("""
        SELECT team_a, team_b, total_matches, btts_pct, over_25_pct
        FROM team_head_to_head
        WHERE LOWER(team_a) LIKE '%liver%' OR LOWER(team_b) LIKE '%liver%'
           OR LOWER(team_a) LIKE '%city%' OR LOWER(team_b) LIKE '%city%'
        LIMIT 5;
    """)
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"   ✅ {r['team_a']} vs {r['team_b']} - {r['total_matches']} matchs, BTTS: {r['btts_pct']}%")
    else:
        print("   ❌ Aucun H2H Liverpool/City!")
        
        # Montrer ce qui existe
        cur.execute("SELECT team_a, team_b FROM team_head_to_head LIMIT 5;")
        rows = cur.fetchall()
        if rows:
            print("   Exemples existants:")
            for r in rows:
                print(f"      • {r['team_a']} vs {r['team_b']}")
    
    # 5. TEAM_INTELLIGENCE
    print("\n" + "═" * 70)
    print("5. TEAM_INTELLIGENCE")
    print("═" * 70)
    cur.execute("""
        SELECT team_name, avg_goals_scored, btts_rate, over_25_rate
        FROM team_intelligence
        WHERE LOWER(team_name) LIKE '%liver%' OR LOWER(team_name) LIKE '%city%'
        LIMIT 5;
    """)
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print(f"   ✅ {r['team_name']} - Goals: {r['avg_goals_scored']}, BTTS: {r['btts_rate']}%")
    else:
        print("   ❌ Aucune équipe trouvée!")
        cur.execute("SELECT team_name FROM team_intelligence LIMIT 10;")
        rows = cur.fetchall()
        if rows:
            print("   Exemples existants:")
            for r in rows:
                print(f"      • {r['team_name']}")
    
    # 6. ML MODEL
    print("\n" + "═" * 70)
    print("6. ML MODEL - Features attendues")
    print("═" * 70)
    try:
        import joblib
        
        # Chercher le modèle
        paths = [
            "/home/Mon_ps/ml_smart_quant/models/best_model.joblib",
            "/home/Mon_ps/backend/ml/models/best_model.joblib",
            "/home/Mon_ps/models/best_model.joblib",
        ]
        
        model = None
        scaler = None
        for p in paths:
            if os.path.exists(p):
                model = joblib.load(p)
                print(f"   ✅ Model trouvé: {p}")
                break
        
        scaler_paths = [
            "/home/Mon_ps/ml_smart_quant/models/scaler.joblib",
            "/home/Mon_ps/backend/ml/models/scaler.joblib",
            "/home/Mon_ps/models/scaler.joblib",
        ]
        for p in scaler_paths:
            if os.path.exists(p):
                scaler = joblib.load(p)
                print(f"   ✅ Scaler trouvé: {p}")
                break
        
        if scaler:
            if hasattr(scaler, 'feature_names_in_'):
                print(f"\n   Features attendues ({len(scaler.feature_names_in_)}):")
                for i, f in enumerate(scaler.feature_names_in_):
                    print(f"      {i+1}. {f}")
            if hasattr(scaler, 'n_features_in_'):
                print(f"\n   Nombre de features attendues: {scaler.n_features_in_}")
        
        if model:
            print(f"   Model type: {type(model).__name__}")
            if hasattr(model, 'n_features_in_'):
                print(f"   Model n_features: {model.n_features_in_}")
                
    except Exception as e:
        print(f"   ❌ Erreur ML: {e}")
    
    # 7. TABLES DISPONIBLES
    print("\n" + "═" * 70)
    print("7. TABLES DISPONIBLES")
    print("═" * 70)
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('team_momentum', 'tactical_matrix', 'referee_intelligence', 
                           'head_to_head', 'team_head_to_head', 'reality_check_results',
                           'fg_sharp_money', 'team_market_profiles', 'team_intelligence', 'market_traps')
        ORDER BY table_name;
    """)
    rows = cur.fetchall()
    for r in rows:
        cur.execute(f"SELECT COUNT(*) FROM {r['table_name']};")
        count = cur.fetchone()[0]
        status = "✅" if count > 0 else "❌"
        print(f"   {status} {r['table_name']}: {count} rows")
    
    cur.close()
    conn.close()
    
    print("\n" + "="*70)
    print("📋 RÉSUMÉ DU DIAGNOSTIC")
    print("="*70)
    print("""
Si les tables sont vides ou les noms ne matchent pas:
  → Les données n'ont pas été chargées correctement
  → Il faut vérifier les scripts de collecte/ETL

Si ML a un nombre de features différent:
  → Il faut adapter predict_with_ml() pour matcher
  → Ou ré-entraîner le modèle avec les bonnes features

Pour corriger:
  1. Vérifier que les scripts de collecte tournent (CRON)
  2. Vérifier les noms d'équipes dans les données source
  3. Adapter le code pour matcher les noms en DB
""")

if __name__ == "__main__":
    main()

