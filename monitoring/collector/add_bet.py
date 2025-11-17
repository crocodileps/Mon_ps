#!/usr/bin/env python3
"""
Helper pour ajouter un pari manuel dans la base de données
Usage: python3 add_bet.py
"""
import os
import psycopg2
from datetime import datetime

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'monps_db'),
    'user': os.getenv('DB_USER', 'monps_user'),
    'password': os.getenv('DB_PASSWORD')
}


def get_available_matches():
    """Récupère les matchs disponibles dans la base (kickoff futur)"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    query = """
        SELECT DISTINCT match_id, sport, home_team, away_team, commence_time
        FROM odds_history
        WHERE commence_time > NOW()
        ORDER BY commence_time ASC
        LIMIT 20
    """
    
    cursor.execute(query)
    matches = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return matches


def add_bet(match_id, match_name, sport, kickoff_time, market_type, 
            selection, line, bookmaker, odds_obtained, stake, notes=""):
    """Ajoute un pari dans la base de données"""
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    query = """
        INSERT INTO manual_bets 
        (match_id, match_name, sport, kickoff_time, market_type, 
         selection, line, bookmaker, odds_obtained, stake, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    
    cursor.execute(query, (
        match_id, match_name, sport, kickoff_time, market_type,
        selection, line, bookmaker, odds_obtained, stake, notes
    ))
    
    bet_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    
    return bet_id


def interactive_add():
    """Mode interactif pour ajouter un pari"""
    print("=" * 60)
    print("  AJOUTER UN PARI MANUEL")
    print("=" * 60)
    
    # Afficher les matchs disponibles
    print("\n📋 Matchs disponibles:")
    matches = get_available_matches()
    
    if not matches:
        print("❌ Aucun match disponible. Attends la prochaine collecte.")
        return
    
    for i, match in enumerate(matches, 1):
        match_id, sport, home, away, kickoff = match
        print(f"{i}. [{sport}] {home} vs {away}")
        print(f"   Kickoff: {kickoff}")
        print(f"   ID: {match_id[:20]}...")
        print()
    
    # Sélectionner le match
    choice = input("Numéro du match (ou 'q' pour quitter): ").strip()
    if choice.lower() == 'q':
        return
    
    try:
        match_idx = int(choice) - 1
        selected_match = matches[match_idx]
    except (ValueError, IndexError):
        print("❌ Choix invalide")
        return
    
    match_id, sport, home, away, kickoff = selected_match
    match_name = f"{home} vs {away}"
    
    print(f"\n✅ Match sélectionné: {match_name}")
    print(f"   Kickoff: {kickoff}")
    
    # Type de marché
    print("\n📊 Type de marché:")
    print("1. h2h (Home/Draw/Away)")
    print("2. totals (Over/Under)")
    market_choice = input("Choix (1 ou 2): ").strip()
    
    if market_choice == "1":
        market_type = "h2h"
        print("\nSélection:")
        print("1. Home")
        print("2. Away") 
        print("3. Draw")
        sel_choice = input("Choix: ").strip()
        selection_map = {"1": "Home", "2": "Away", "3": "Draw"}
        selection = selection_map.get(sel_choice, "Home")
        line = None
        
    elif market_choice == "2":
        market_type = "totals"
        print("\nSélection:")
        print("1. Over")
        print("2. Under")
        sel_choice = input("Choix: ").strip()
        selection = "Over" if sel_choice == "1" else "Under"
        
        line_str = input("Ligne (ex: 2.5, 3.0): ").strip()
        try:
            line = float(line_str)
        except ValueError:
            print("❌ Ligne invalide")
            return
        
        selection = f"{selection} {line}"
        
    else:
        print("❌ Choix invalide")
        return
    
    # Bookmaker
    bookmaker = input("\n🏦 Bookmaker (ex: Bet365, Winamax, Unibet): ").strip()
    if not bookmaker:
        bookmaker = "Unknown"
    
    # Cote
    odds_str = input("💰 Cote obtenue (ex: 1.95): ").strip()
    try:
        odds_obtained = float(odds_str)
        if odds_obtained <= 1:
            print("❌ La cote doit être > 1")
            return
    except ValueError:
        print("❌ Cote invalide")
        return
    
    # Mise
    stake_str = input("💵 Mise en € (ex: 50): ").strip()
    try:
        stake = float(stake_str)
        if stake <= 0:
            print("❌ La mise doit être > 0")
            return
    except ValueError:
        print("❌ Mise invalide")
        return
    
    # Notes (optionnel)
    notes = input("📝 Notes (optionnel, appuie sur Enter pour passer): ").strip()
    
    # Confirmation
    print("\n" + "=" * 60)
    print("📋 RÉCAPITULATIF DU PARI:")
    print("=" * 60)
    print(f"Match: {match_name}")
    print(f"Sport: {sport}")
    print(f"Kickoff: {kickoff}")
    print(f"Marché: {market_type}")
    print(f"Sélection: {selection}")
    if line:
        print(f"Ligne: {line}")
    print(f"Bookmaker: {bookmaker}")
    print(f"Cote: {odds_obtained}")
    print(f"Mise: {stake}€")
    if notes:
        print(f"Notes: {notes}")
    print("=" * 60)
    
    confirm = input("\n✅ Confirmer l'ajout ? (oui/non): ").strip().lower()
    
    if confirm in ["oui", "o", "yes", "y"]:
        bet_id = add_bet(
            match_id, match_name, sport, kickoff, market_type,
            selection, line, bookmaker, odds_obtained, stake, notes
        )
        print(f"\n🎉 PARI AJOUTÉ AVEC SUCCÈS !")
        print(f"   ID: {bet_id}")
        print(f"\nLe CLV sera calculé automatiquement après le kickoff.")
    else:
        print("❌ Ajout annulé")


if __name__ == '__main__':
    interactive_add()
