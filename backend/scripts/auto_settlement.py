"""
Script de règlement automatique des paris terminés
Utilise The Odds API pour récupérer les scores
"""
import os
import sys
import requests
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor

# Config
ODDS_API_KEY = os.getenv('ODDS_API_KEY', 'YOUR_API_KEY')
ODDS_API_BASE = 'https://api.the-odds-api.com/v4'

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'monps_db'),
    'user': os.getenv('DB_USER', 'monps_user'),
    'password': os.getenv('DB_PASSWORD', 'monps_password')
}

def get_pending_finished_matches():
    """Récupère les matchs terminés avec paris en attente"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Matchs commencés il y a plus de 3h et encore pending
    three_hours_ago = datetime.now() - timedelta(hours=3)
    
    cursor.execute("""
        SELECT DISTINCT match_id, sport, home_team, away_team, commence_time
        FROM bets 
        WHERE status = 'pending' 
        AND commence_time < %s
        ORDER BY commence_time DESC
    """, (three_hours_ago,))
    
    matches = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return matches

def get_match_scores(sport, match_id):
    """Récupère le score d'un match via The Odds API"""
    url = f"{ODDS_API_BASE}/sports/{sport}/scores/"
    params = {'apiKey': ODDS_API_KEY, 'daysFrom': 3}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            scores = response.json()
            for game in scores:
                if game['id'] == match_id and game.get('completed'):
                    return game.get('scores')
        return None
    except Exception as e:
        print(f"Erreur API scores: {e}")
        return None

def determine_outcome(scores, home_team, away_team):
    """Détermine le résultat du match (home/away/draw)"""
    if not scores or len(scores) < 2:
        return None, None
    
    home_score = None
    away_score = None
    
    for score in scores:
        if score['name'] == home_team:
            home_score = int(score['score'])
        elif score['name'] == away_team:
            away_score = int(score['score'])
    
    if home_score is None or away_score is None:
        return None, None
    
    final_score = f"{home_score}-{away_score}"
    
    if home_score > away_score:
        return 'home', final_score
    elif away_score > home_score:
        return 'away', final_score
    else:
        return 'draw', final_score

def settle_bets(match_id, actual_outcome, final_score):
    """Règle tous les paris d'un match"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Récupérer tous les paris pending de ce match
    cursor.execute("""
        SELECT id, outcome, odds, stake 
        FROM bets 
        WHERE match_id = %s AND status = 'pending'
    """, (match_id,))
    
    bets = cursor.fetchall()
    settled_count = 0
    
    for bet in bets:
        bet_won = (bet['outcome'] == actual_outcome)
        
        if bet_won:
            payout = bet['stake'] * bet['odds']
            profit = payout - bet['stake']
            result = 'won'
            status = 'won'
        else:
            payout = 0
            profit = -bet['stake']
            result = 'lost'
            status = 'lost'
        
        cursor.execute("""
            UPDATE bets 
            SET status = %s, result = %s, final_score = %s,
                payout = %s, profit = %s, settled_at = NOW(),
                settled_by = 'auto'
            WHERE id = %s
        """, (status, result, final_score, payout, profit, bet['id']))
        
        settled_count += 1
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return settled_count

def main():
    print(f"[{datetime.now()}] Démarrage du settlement automatique...")
    
    matches = get_pending_finished_matches()
    print(f"✓ {len(matches)} matchs à vérifier")
    
    total_settled = 0
    
    for match in matches:
        print(f"\n→ Vérification: {match['home_team']} vs {match['away_team']}")
        
        scores = get_match_scores(match['sport'], match['match_id'])
        
        if not scores:
            print("  ⚠ Scores non disponibles")
            continue
        
        outcome, final_score = determine_outcome(scores, match['home_team'], match['away_team'])
        
        if not outcome:
            print("  ⚠ Impossible de déterminer le résultat")
            continue
        
        print(f"  ✓ Score: {final_score} → Résultat: {outcome}")
        
        settled = settle_bets(match['match_id'], outcome, final_score)
        total_settled += settled
        
        print(f"  ✓ {settled} paris réglés")
    
    print(f"\n[{datetime.now()}] Terminé ! {total_settled} paris réglés au total")

if __name__ == '__main__':
    main()
