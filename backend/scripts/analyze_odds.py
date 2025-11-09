#!/usr/bin/env python3
"""
Script d'analyse des cotes
Identifie les opportunités (écarts entre bookmakers, CLV potentiel)
"""

import os
import psycopg2
from datetime import datetime

# Configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "monps_prod"),
    "user": os.getenv("DB_USER", "monps_user"),
    "password": os.getenv("DB_PASSWORD")
}

def connect_db():
    """Connexion à la base de données"""
    return psycopg2.connect(**DB_CONFIG)

def analyze_spreads():
    """Analyse les écarts entre bookmakers"""
    print("="*60)
    print("  ANALYSE DES ÉCARTS ENTRE BOOKMAKERS")
    print("="*60)
    
    conn = connect_db()
    cur = conn.cursor()
    
    # Requête pour trouver les écarts
    query = """
    WITH odds_by_match AS (
        SELECT 
            match_id,
            home_team,
            away_team,
            market_type,
            outcome_name,
            MIN(odds_value) as min_odd,
            MAX(odds_value) as max_odd,
            MAX(odds_value) - MIN(odds_value) as spread,
            ((MAX(odds_value) - MIN(odds_value)) / MIN(odds_value) * 100) as spread_pct,
            COUNT(DISTINCT bookmaker) as nb_bookmakers
        FROM odds
        WHERE market_type = 'h2h'
        GROUP BY match_id, home_team, away_team, market_type, outcome_name
        HAVING COUNT(DISTINCT bookmaker) >= 3
    )
    SELECT 
        home_team,
        away_team,
        outcome_name,
        min_odd,
        max_odd,
        spread,
        spread_pct,
        nb_bookmakers
    FROM odds_by_match
    WHERE spread_pct > 5  -- Écarts > 5%
    ORDER BY spread_pct DESC
    LIMIT 10;
    """
    
    cur.execute(query)
    results = cur.fetchall()
    
    if results:
        print(f"\n🎯 Top 10 des écarts (> 5%) :\n")
        for row in results:
            home, away, outcome, min_odd, max_odd, spread, spread_pct, nb_books = row
            print(f"⚽ {home} vs {away}")
            print(f"   Outcome: {outcome}")
            print(f"   Cotes: {min_odd:.2f} → {max_odd:.2f} (écart: {spread_pct:.1f}%)")
            print(f"   Bookmakers: {nb_books}")
            print()
    else:
        print("\n⚠️  Aucun écart significatif trouvé")
    
    cur.close()
    conn.close()

def top_bookmakers():
    """Identifie les bookmakers avec les meilleures cotes"""
    print("\n" + "="*60)
    print("  TOP BOOKMAKERS (MEILLEURES COTES)")
    print("="*60)
    
    conn = connect_db()
    cur = conn.cursor()
    
    query = """
    WITH ranked_odds AS (
        SELECT 
            bookmaker,
            match_id,
            outcome_name,
            odds_value,
            RANK() OVER (
                PARTITION BY match_id, outcome_name 
                ORDER BY odds_value DESC
            ) as rank
        FROM odds
        WHERE market_type = 'h2h'
    )
    SELECT 
        bookmaker,
        COUNT(*) as fois_meilleure_cote,
        ROUND(AVG(odds_value), 2) as moyenne_cotes
    FROM ranked_odds
    WHERE rank = 1
    GROUP BY bookmaker
    ORDER BY fois_meilleure_cote DESC
    LIMIT 10;
    """
    
    cur.execute(query)
    results = cur.fetchall()
    
    print(f"\n📊 Classement des bookmakers :\n")
    for i, row in enumerate(results, 1):
        bookmaker, count, avg = row
        print(f"{i:2}. {bookmaker:25} : {count:4} fois meilleure cote (avg: {avg:.2f})")
    
    cur.close()
    conn.close()

def upcoming_matches():
    """Liste les prochains matchs avec cotes"""
    print("\n" + "="*60)
    print("  PROCHAINS MATCHS")
    print("="*60)
    
    conn = connect_db()
    cur = conn.cursor()
    
    query = """
    SELECT DISTINCT
        home_team,
        away_team,
        commence_time,
        COUNT(DISTINCT bookmaker) as nb_bookmakers
    FROM odds
    WHERE commence_time > NOW()
    GROUP BY home_team, away_team, commence_time
    ORDER BY commence_time
    LIMIT 10;
    """
    
    cur.execute(query)
    results = cur.fetchall()
    
    print(f"\n📅 10 prochains matchs :\n")
    for row in results:
        home, away, time, nb_books = row
        print(f"⚽ {home:20} vs {away:20}")
        print(f"   📅 {time}  |  📚 {nb_books} bookmakers")
        print()
    
    cur.close()
    conn.close()

def main():
    """Fonction principale"""
    print("\n" + "🔍"*30)
    print("  ANALYSE DES COTES - MON_PS")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("🔍"*30 + "\n")
    
    try:
        # 1. Analyser les écarts
        analyze_spreads()
        
        # 2. Top bookmakers
        top_bookmakers()
        
        # 3. Prochains matchs
        upcoming_matches()
        
        print("\n" + "="*60)
        print("  ✅ ANALYSE TERMINÉE")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERREUR : {e}")

if __name__ == "__main__":
    main()
