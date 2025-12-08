#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🎯 V8 SCRAPER UNDERSTAT - ENRICHISSEMENT COMPLET                            ║
║                                                                              ║
║  Saison: 2025 (= 2025-2026)                                                 ║
║  Données: Scores MT, Buteurs, Passeurs, Stats temporelles                   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import requests
import json
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import time

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

SEASON = "2025"  # Understat: 2025 = saison 2025-2026

# Mapping équipes Understat
TEAMS = {
    # Premier League
    "Manchester_United": "Manchester United",
    "Manchester_City": "Manchester City", 
    "Liverpool": "Liverpool",
    "Arsenal": "Arsenal",
    "Chelsea": "Chelsea",
    "Tottenham": "Tottenham",
    "Newcastle_United": "Newcastle United",
    "Aston_Villa": "Aston Villa",
    "Brighton": "Brighton",
    "West_Ham": "West Ham",
    "Fulham": "Fulham",
    "Crystal_Palace": "Crystal Palace",
    "Brentford": "Brentford",
    "Everton": "Everton",
    "Nottingham_Forest": "Nottingham Forest",
    "Wolverhampton_Wanderers": "Wolverhampton Wanderers",
    "Bournemouth": "Bournemouth",
    "Leicester": "Leicester",
    "Ipswich": "Ipswich Town",
    "Southampton": "Southampton",
    # La Liga
    "Barcelona": "Barcelona",
    "Real_Madrid": "Real Madrid",
    "Atletico_Madrid": "Atletico Madrid",
    "Athletic_Club": "Athletic Bilbao",
    "Villarreal": "Villarreal",
    "Real_Sociedad": "Real Sociedad",
    "Real_Betis": "Real Betis",
    "Sevilla": "Sevilla",
    "Valencia": "Valencia",
    "Celta_Vigo": "Celta Vigo",
    "Girona": "Girona",
    "Osasuna": "Osasuna",
    "Mallorca": "Mallorca",
    "Getafe": "Getafe",
    "Alaves": "Alaves",
    "Rayo_Vallecano": "Rayo Vallecano",
    "Las_Palmas": "Las Palmas",
    "Espanyol": "Espanyol",
    "Leganes": "Leganes",
    "Real_Valladolid": "Real Valladolid",
    # Serie A
    "Napoli": "Napoli",
    "Inter": "Inter Milan",
    "Juventus": "Juventus",
    "AC_Milan": "AC Milan",
    "Atalanta": "Atalanta",
    "Lazio": "Lazio",
    "Roma": "AS Roma",
    "Fiorentina": "Fiorentina",
    "Bologna": "Bologna",
    "Torino": "Torino",
    "Udinese": "Udinese",
    "Genoa": "Genoa",
    "Cagliari": "Cagliari",
    "Parma_Calcio_1913": "Parma",
    "Empoli": "Empoli",
    "Como": "Como",
    "Verona": "Verona",
    "Lecce": "Lecce",
    "Monza": "Monza",
    "Venezia": "Venezia",
    # Bundesliga
    "Bayern_Munich": "Bayern Munich",
    "Borussia_Dortmund": "Borussia Dortmund",
    "Bayer_Leverkusen": "Bayer Leverkusen",
    "RasenBallsport_Leipzig": "RB Leipzig",
    "Eintracht_Frankfurt": "Eintracht Frankfurt",
    "VfB_Stuttgart": "VfB Stuttgart",
    "Wolfsburg": "Wolfsburg",
    "Freiburg": "Freiburg",
    "Borussia_M.Gladbach": "Borussia M.Gladbach",
    "Werder_Bremen": "Werder Bremen",
    "Mainz_05": "Mainz 05",
    "Augsburg": "Augsburg",
    "Hoffenheim": "Hoffenheim",
    "Union_Berlin": "Union Berlin",
    "FC_Heidenheim": "Heidenheim",
    "St._Pauli": "St. Pauli",
    "Holstein_Kiel": "Holstein Kiel",
    "Bochum": "Bochum",
    # Ligue 1
    "Paris_Saint_Germain": "Paris Saint Germain",
    "Monaco": "Monaco",
    "Lille": "Lille",
    "Lyon": "Lyon",
    "Marseille": "Marseille",
    "Nice": "Nice",
    "Lens": "Lens",
    "Rennes": "Rennes",
    "Strasbourg": "Strasbourg",
    "Toulouse": "Toulouse",
    "Reims": "Reims",
    "Nantes": "Nantes",
    "Auxerre": "Auxerre",
    "Montpellier": "Montpellier",
    "Angers": "Angers",
    "Le_Havre": "Le Havre",
    "Saint-Etienne": "Saint-Etienne",
    "Brest": "Brest",
}

# ═══════════════════════════════════════════════════════════════════════════════
# SCRAPER
# ═══════════════════════════════════════════════════════════════════════════════

class UnderstatScraperV8:
    BASE_URL = "https://understat.com"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_team_matches(self, team_understat: str) -> list:
        """Récupère tous les matchs d'une équipe avec détails"""
        url = f"{self.BASE_URL}/team/{team_understat}/{SEASON}"
        
        try:
            resp = self.session.get(url, timeout=30)
            if resp.status_code != 200:
                return []
            
            # Extraire datesData (liste des matchs)
            match = re.search(r"var datesData\s*=\s*JSON\.parse\('(.+?)'\)", resp.text)
            if match:
                return json.loads(match.group(1).encode().decode('unicode_escape'))
            return []
        except Exception as e:
            print(f"   ❌ Erreur {team_understat}: {e}")
            return []
    
    def get_match_details(self, match_id: str) -> dict:
        """Récupère les détails d'un match (tirs, buteurs, etc.)"""
        url = f"{self.BASE_URL}/match/{match_id}"
        
        try:
            resp = self.session.get(url, timeout=30)
            if resp.status_code != 200:
                return {}
            
            result = {}
            
            # Extraire shotsData
            shots_match = re.search(r"var shotsData\s*=\s*JSON\.parse\('(.+?)'\)", resp.text)
            if shots_match:
                result['shots'] = json.loads(shots_match.group(1).encode().decode('unicode_escape'))
            
            # Extraire rostersData
            rosters_match = re.search(r"var rostersData\s*=\s*JSON\.parse\('(.+?)'\)", resp.text)
            if rosters_match:
                result['rosters'] = json.loads(rosters_match.group(1).encode().decode('unicode_escape'))
            
            return result
        except Exception as e:
            print(f"   ❌ Erreur match {match_id}: {e}")
            return {}
    
    def extract_match_stats(self, shots_data: dict) -> dict:
        """Extrait toutes les stats d'un match depuis les tirs"""
        stats = {
            'ht_home': 0, 'ht_away': 0,
            'ft_home': 0, 'ft_away': 0,
            'shots_home': 0, 'shots_away': 0,
            'sot_home': 0, 'sot_away': 0,
            'xg_home': 0.0, 'xg_away': 0.0,
            'xg_1h_home': 0.0, 'xg_1h_away': 0.0,
            'xg_2h_home': 0.0, 'xg_2h_away': 0.0,
            'goals': [],  # Liste des buts avec détails
            'assists': [],  # Liste des passes D
        }
        
        for side, team_key in [('h', 'home'), ('a', 'away')]:
            for shot in shots_data.get(side, []):
                minute = int(shot.get('minute', 0))
                xg = float(shot.get('xG', 0))
                result = shot.get('result', '')
                
                # Compter tirs
                stats[f'shots_{team_key}'] += 1
                
                # Tirs cadrés
                if result in ['Goal', 'SavedShot']:
                    stats[f'sot_{team_key}'] += 1
                
                # xG par mi-temps
                if minute <= 45:
                    stats[f'xg_1h_{team_key}'] += xg
                else:
                    stats[f'xg_2h_{team_key}'] += xg
                stats[f'xg_{team_key}'] += xg
                
                # Buts
                if result == 'Goal':
                    if minute <= 45:
                        stats[f'ht_{team_key}'] += 1
                    stats[f'ft_{team_key}'] += 1
                    
                    # Détails du but
                    stats['goals'].append({
                        'player': shot.get('player'),
                        'player_id': shot.get('player_id'),
                        'minute': minute,
                        'team': side,
                        'xG': xg,
                        'situation': shot.get('situation'),
                        'shot_type': shot.get('shotType'),
                    })
                    
                    # Passe décisive
                    if shot.get('player_assisted'):
                        stats['assists'].append({
                            'player': shot.get('player_assisted'),
                            'minute': minute,
                            'team': side,
                            'to_scorer': shot.get('player'),
                        })
        
        return stats

# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════════════════════════

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def ensure_columns():
    """Ajoute les colonnes manquantes"""
    conn = get_connection()
    cur = conn.cursor()
    
    # Colonnes pour match_xg_stats
    new_cols = [
        ("match_xg_stats", "ht_home_score", "INTEGER"),
        ("match_xg_stats", "ht_away_score", "INTEGER"),
        ("match_xg_stats", "shots_home", "INTEGER"),
        ("match_xg_stats", "shots_away", "INTEGER"),
        ("match_xg_stats", "sot_home", "INTEGER"),
        ("match_xg_stats", "sot_away", "INTEGER"),
        ("match_xg_stats", "xg_1h_home", "NUMERIC(5,2)"),
        ("match_xg_stats", "xg_1h_away", "NUMERIC(5,2)"),
        ("match_xg_stats", "xg_2h_home", "NUMERIC(5,2)"),
        ("match_xg_stats", "xg_2h_away", "NUMERIC(5,2)"),
        ("match_xg_stats", "understat_match_id", "INTEGER"),
    ]
    
    for table, col, dtype in new_cols:
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {dtype};")
        except:
            pass
    
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Colonnes vérifiées/ajoutées")

def get_existing_matches():
    """Récupère les matchs déjà enrichis"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT home_team, away_team, match_date::date 
        FROM match_xg_stats 
        WHERE ht_home_score IS NOT NULL
    """)
    existing = set()
    for row in cur.fetchall():
        existing.add((row[0], row[1], str(row[2])))
    cur.close()
    conn.close()
    return existing

def update_match_stats(home_team: str, away_team: str, match_date: str, stats: dict, match_id: str):
    """Met à jour un match avec les nouvelles stats"""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            UPDATE match_xg_stats SET
                ht_home_score = %s,
                ht_away_score = %s,
                shots_home = %s,
                shots_away = %s,
                sot_home = %s,
                sot_away = %s,
                xg_1h_home = %s,
                xg_1h_away = %s,
                xg_2h_home = %s,
                xg_2h_away = %s,
                understat_match_id = %s
            WHERE home_team = %s AND away_team = %s 
            AND match_date = %s
        """, (
            stats['ht_home'], stats['ht_away'],
            stats['shots_home'], stats['shots_away'],
            stats['sot_home'], stats['sot_away'],
            stats['xg_1h_home'], stats['xg_1h_away'],
            stats['xg_2h_home'], stats['xg_2h_away'],
            match_id,
            home_team, away_team, match_date
        ))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        print(f"   ❌ Update error: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def save_match_events(match_date: str, home_team: str, away_team: str, stats: dict, match_id: str):
    """Sauvegarde les événements (buts, assists)"""
    conn = get_connection()
    cur = conn.cursor()
    
    for goal in stats['goals']:
        try:
            cur.execute("""
                INSERT INTO match_events 
                (match_id, fixture_id, minute, event_type, team, player, player_id, detail, created_at)
                VALUES (%s, %s, %s, 'Goal', %s, %s, %s, %s, NOW())
                ON CONFLICT DO NOTHING
            """, (
                match_id, match_id, goal['minute'],
                home_team if goal['team'] == 'h' else away_team,
                goal['player'], goal['player_id'],
                json.dumps({'xG': goal['xG'], 'situation': goal['situation'], 'shot_type': goal['shot_type']})
            ))
        except Exception as e:
            pass
    
    conn.commit()
    cur.close()
    conn.close()

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🎯 V8 SCRAPER UNDERSTAT - ENRICHISSEMENT COMPLET                            ║
║     Saison 2025-2026 | Scores MT, xG temporel, Buteurs                       ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # 1. Préparer DB
    ensure_columns()
    
    # 2. Récupérer matchs déjà enrichis
    existing = get_existing_matches()
    print(f"📊 {len(existing)} matchs déjà enrichis avec scores MT")
    
    # 3. Scraper
    scraper = UnderstatScraperV8()
    
    total_updated = 0
    total_skipped = 0
    teams_processed = 0
    
    for team_understat, team_db in TEAMS.items():
        teams_processed += 1
        print(f"\n[{teams_processed}/{len(TEAMS)}] 🏟️ {team_db}...")
        
        # Récupérer matchs de l'équipe
        matches = scraper.get_team_matches(team_understat)
        
        if not matches:
            print(f"   ⚠️ Aucun match trouvé")
            continue
        
        # Filtrer matchs terminés (isResult=True)
        finished = [m for m in matches if m.get('isResult')]
        print(f"   📊 {len(finished)} matchs terminés")
        
        for match in finished:  # Limiter pour test
            match_id = match.get('id')
            match_date = match.get('datetime', '')[:10]
            
            # Déterminer home/away
            if match.get('side') == 'h':
                home_team = team_db
                away_team = match.get('a', {}).get('title', 'Unknown')
            else:
                home_team = match.get('h', {}).get('title', 'Unknown')
                away_team = team_db
            
            # Vérifier si déjà enrichi
            if (home_team, away_team, match_date) in existing:
                total_skipped += 1
                continue
            
            # Récupérer détails du match
            time.sleep(0.5)  # Rate limiting
            details = scraper.get_match_details(match_id)
            
            if details.get('shots'):
                stats = scraper.extract_match_stats(details['shots'])
                
                # Mettre à jour match_xg_stats
                if update_match_stats(home_team, away_team, match_date, stats, match_id):
                    print(f"   ✅ {home_team} vs {away_team}: MT {stats['ht_home']}-{stats['ht_away']}")
                    total_updated += 1
                    existing.add((home_team, away_team, match_date))
                    
                    # Sauvegarder les événements
                    save_match_events(match_date, home_team, away_team, stats, match_id)
        
        # Pause entre équipes
        time.sleep(1)
    
    # Résumé
    print(f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  📊 RÉSUMÉ SCRAPING V8                                                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Équipes traitées:   {teams_processed:4d}                                                    ║
║  Matchs mis à jour:  {total_updated:4d}                                                    ║
║  Matchs ignorés:     {total_skipped:4d}                                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)

if __name__ == "__main__":
    main()

# ÉQUIPES PROMUES 2025-2026 (à ajouter au mapping)
TEAMS_PROMOTED = {
    # Serie A
    "Pisa": "Pisa",
    "Sassuolo": "Sassuolo", 
    "Cremonese": "Cremonese",
    # La Liga
    "Levante": "Levante",
    "Elche": "Elche",
    "Real_Oviedo": "Real Oviedo",
    # Bundesliga
    "FC_Cologne": "FC Cologne",
    "Hamburger_SV": "Hamburger SV",
    # Premier League
    "Burnley": "Burnley",
    "Leeds": "Leeds",
    "Sunderland": "Sunderland",
}
