#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║     🔬 UNDERSTAT SCRAPER - SAISON 2025/2026                                                                   ║
║                                                                                                               ║
║  Scrape les données xG actuelles et les stocke dans quantum_dna.current_season                               ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
"""

import requests
import re
import json
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional

DB_CONFIG = {
    "host": "localhost", "port": 5432, "database": "monps_db",
    "user": "monps_user", "password": "monps_secure_password_2024"
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Mapping complet équipes DB → Understat
TEAM_MAPPING = {
    # Premier League
    "Manchester City": "Manchester_City",
    "Manchester United": "Manchester_United",
    "Arsenal": "Arsenal",
    "Liverpool": "Liverpool",
    "Chelsea": "Chelsea",
    "Tottenham": "Tottenham",
    "Newcastle United": "Newcastle_United",
    "Brighton": "Brighton",
    "Aston Villa": "Aston_Villa",
    "West Ham": "West_Ham",
    "Brentford": "Brentford",
    "Fulham": "Fulham",
    "Crystal Palace": "Crystal_Palace",
    "Wolverhampton": "Wolverhampton_Wanderers",
    "Wolverhampton Wanderers": "Wolverhampton_Wanderers",
    "Everton": "Everton",
    "Nottingham Forest": "Nottingham_Forest",
    "Bournemouth": "Bournemouth",
    "Leicester": "Leicester",
    "Leeds": "Leeds",
    "Southampton": "Southampton",
    "Ipswich": "Ipswich",
    "Burnley": "Burnley",
    # La Liga
    "Barcelona": "Barcelona",
    "Real Madrid": "Real_Madrid",
    "Atletico Madrid": "Atletico_Madrid",
    "Athletic Bilbao": "Athletic_Club",
    "Athletic Club": "Athletic_Club",
    "Real Sociedad": "Real_Sociedad",
    "Real Betis": "Real_Betis",
    "Villarreal": "Villarreal",
    "Sevilla": "Sevilla",
    "Valencia": "Valencia",
    "Girona": "Girona",
    "Getafe": "Getafe",
    "Osasuna": "Osasuna",
    "Celta Vigo": "Celta_Vigo",
    "Mallorca": "Mallorca",
    "Las Palmas": "Las_Palmas",
    "Rayo Vallecano": "Rayo_Vallecano",
    "Alaves": "Alaves",
    "Espanyol": "Espanyol",
    "Valladolid": "Valladolid",
    "Leganes": "Leganes",
    "Real Oviedo": "Real_Oviedo",  # Promu 2025
    # Serie A
    "Inter": "Inter",
    "AC Milan": "AC_Milan",
    "Milan": "AC_Milan",
    "Juventus": "Juventus",
    "Napoli": "Napoli",
    "Lazio": "Lazio",
    "Roma": "Roma",
    "Atalanta": "Atalanta",
    "Fiorentina": "Fiorentina",
    "Bologna": "Bologna",
    "Torino": "Torino",
    "Monza": "Monza",
    "Udinese": "Udinese",
    "Empoli": "Empoli",
    "Cagliari": "Cagliari",
    "Verona": "Verona",
    "Lecce": "Lecce",
    "Genoa": "Genoa",
    "Como": "Como",
    "Parma": "Parma",
    "Parma Calcio 1913": "Parma",
    "Venezia": "Venezia",
    # Bundesliga
    "Bayern Munich": "Bayern_Munich",
    "Borussia Dortmund": "Borussia_Dortmund",
    "RB Leipzig": "RasenBallsport_Leipzig",
    "RasenBallsport Leipzig": "RasenBallsport_Leipzig",
    "Bayer Leverkusen": "Bayer_Leverkusen",
    "Eintracht Frankfurt": "Eintracht_Frankfurt",
    "Wolfsburg": "Wolfsburg",
    "Borussia M.Gladbach": "Borussia_M.Gladbach",
    "Freiburg": "Freiburg",
    "Hoffenheim": "Hoffenheim",
    "FC Cologne": "FC_Cologne",
    "Mainz 05": "Mainz_05",
    "Mainz": "Mainz_05",
    "Augsburg": "Augsburg",
    "Union Berlin": "Union_Berlin",
    "Stuttgart": "VfB_Stuttgart",
    "VfB Stuttgart": "VfB_Stuttgart",
    "Werder Bremen": "Werder_Bremen",
    "Bochum": "Bochum",
    "Heidenheim": "FC_Heidenheim",
    "FC Heidenheim": "FC_Heidenheim",
    "St. Pauli": "St._Pauli",
    "Holstein Kiel": "Holstein_Kiel",
    # Ligue 1
    "Paris Saint Germain": "Paris_Saint_Germain",
    "PSG": "Paris_Saint_Germain",
    "Marseille": "Marseille",
    "Monaco": "Monaco",
    "Lyon": "Lyon",
    "Lille": "Lille",
    "Nice": "Nice",
    "Lens": "Lens",
    "Rennes": "Rennes",
    "Montpellier": "Montpellier",
    "Toulouse": "Toulouse",
    "Strasbourg": "Strasbourg",
    "Nantes": "Nantes",
    "Reims": "Reims",
    "Le Havre": "Le_Havre",
    "Brest": "Brest",
    "Metz": "Metz",
    "Auxerre": "Auxerre",
    "Angers": "Angers",
    "St Etienne": "Saint-Etienne",
    "Paris FC": "Paris_FC",  # Promu 2025
}

SEASON = "2025"


class UnderstatScraper2025:
    """Scraper Understat pour saison 2025/2026"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.requests_count = 0
        
    def _get_data(self, url: str, variable_name: str) -> Optional[dict]:
        """Extrait une variable JSON d'une page Understat"""
        try:
            time.sleep(1.5)
            response = self.session.get(url, timeout=15)
            self.requests_count += 1
            
            if response.status_code != 200:
                return None
                
            pattern = re.compile(rf"var {variable_name}\s*=\s*JSON\.parse\('(.+?)'\)")
            match = pattern.search(response.text)
            
            if match:
                json_str = match.group(1).encode('utf-8').decode('unicode_escape')
                return json.loads(json_str)
            return None
            
        except Exception as e:
            return None
            
    def get_team_data(self, understat_name: str) -> Optional[dict]:
        """Récupère datesData pour saison 2025"""
        url = f"https://understat.com/team/{understat_name}/{SEASON}"
        return self._get_data(url, "datesData")
        
    def calculate_xg_stats(self, dates_data: list, understat_name: str) -> Optional[dict]:
        """Calcule les stats xG depuis datesData"""
        if not dates_data:
            return None
            
        finished = [m for m in dates_data if m.get('isResult')]
        if not finished:
            return None
            
        xg_for, xg_against = 0, 0
        goals_for, goals_against = 0, 0
        home_matches, away_matches = 0, 0
        wins, draws, losses = 0, 0, 0
        
        understat_clean = understat_name.replace('_', ' ').lower()
        
        for match in finished:
            home_title = match['h'].get('title', '').lower()
            is_home = understat_clean in home_title or understat_name.lower().replace('_', ' ') in home_title
            
            h_goals = int(match['goals']['h'])
            a_goals = int(match['goals']['a'])
            h_xg = float(match['xG']['h'])
            a_xg = float(match['xG']['a'])
            
            if is_home:
                xg_for += h_xg
                xg_against += a_xg
                goals_for += h_goals
                goals_against += a_goals
                home_matches += 1
                if h_goals > a_goals: wins += 1
                elif h_goals < a_goals: losses += 1
                else: draws += 1
            else:
                xg_for += a_xg
                xg_against += h_xg
                goals_for += a_goals
                goals_against += h_goals
                away_matches += 1
                if a_goals > h_goals: wins += 1
                elif a_goals < h_goals: losses += 1
                else: draws += 1
        
        n = len(finished)
        if n == 0:
            return None
            
        return {
            "season": "2025/2026",
            "matches_played": n,
            "home_matches": home_matches,
            "away_matches": away_matches,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_for": goals_for,
            "goals_against": goals_against,
            "goal_diff": goals_for - goals_against,
            "xg_for_total": round(xg_for, 2),
            "xg_against_total": round(xg_against, 2),
            "xg_for_avg": round(xg_for / n, 3),
            "xg_against_avg": round(xg_against / n, 3),
            "xg_diff_avg": round((xg_for - xg_against) / n, 3),
            "overperformance": round(goals_for - xg_for, 2),
            "defensive_overperf": round(xg_against - goals_against, 2),
            "clinical": goals_for > xg_for,
            "solid_defense": goals_against < xg_against,
            "points": wins * 3 + draws,
            "ppg": round((wins * 3 + draws) / n, 2),
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }


class QuantumEnricher2025:
    """Enrichit quantum_dna avec données saison 2025"""
    
    def __init__(self):
        self.conn = None
        self.scraper = UnderstatScraper2025()
        self.enriched = 0
        self.failed = 0
        self.no_data = 0
        
    def connect(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        
    def close(self):
        if self.conn:
            self.conn.close()
            
    def get_teams(self) -> List[dict]:
        """Récupère toutes les équipes"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, team_name, tier, total_pnl
                FROM quantum.team_profiles
                ORDER BY total_pnl DESC
            """)
            return cur.fetchall()
            
    def enrich_team(self, team: dict) -> str:
        """Enrichit une équipe avec données 2025. Retourne status."""
        team_name = team['team_name']
        
        if team_name not in TEAM_MAPPING:
            return "no_mapping"
            
        understat_name = TEAM_MAPPING[team_name]
        dates_data = self.scraper.get_team_data(understat_name)
        
        if not dates_data:
            return "no_data"
            
        xg_stats = self.scraper.calculate_xg_stats(dates_data, understat_name)
        
        if not xg_stats or xg_stats['matches_played'] == 0:
            return "no_matches"
            
        # Stocker dans quantum_dna.current_season
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE quantum.team_profiles
                SET quantum_dna = jsonb_set(
                    quantum_dna,
                    '{current_season}',
                    %s::jsonb
                ),
                updated_at = NOW()
                WHERE id = %s
            """, (json.dumps(xg_stats), team['id']))
            
        self.conn.commit()
        return "success"
        
    def run(self):
        """Lance l'enrichissement complet"""
        print("""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║     🔬 UNDERSTAT ENRICHMENT - SAISON 2025/2026                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
        """)
        
        self.connect()
        teams = self.get_teams()
        print(f"✅ {len(teams)} équipes à enrichir\n")
        
        for team in teams:
            team_name = team['team_name']
            print(f"   📊 {team_name}...", end=" ", flush=True)
            
            status = self.enrich_team(team)
            
            if status == "success":
                self.enriched += 1
                print("✅")
            elif status == "no_mapping":
                self.failed += 1
                print("⚠️ pas de mapping")
            elif status == "no_data":
                self.no_data += 1
                print("❌ pas sur Understat 2025")
            elif status == "no_matches":
                self.no_data += 1
                print("⏳ 0 matchs joués")
            else:
                self.failed += 1
                print(f"❌ {status}")
                
            time.sleep(2)
            
        print(f"""
{'='*80}
📊 RÉSUMÉ SCRAPING SAISON 2025/2026
{'='*80}
   ✅ Enrichies: {self.enriched}
   ⏳ Pas de données 2025: {self.no_data}
   ⚠️ Pas de mapping: {self.failed}
   📡 Requêtes: {self.scraper.requests_count}
{'='*80}
        """)
        
        self.close()


if __name__ == "__main__":
    enricher = QuantumEnricher2025()
    enricher.run()
