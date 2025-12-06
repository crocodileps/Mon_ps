#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║     🔬 UNDERSTAT SCRAPER - 2-STEP APPROACH                                                                    ║
║                                                                                                               ║
║  Step 1: Team Page → datesData (xG par match)                                                                ║
║  Step 2: Match Page → shotsData (xG par minute) - optionnel                                                  ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
"""

import requests
import re
import json
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional
from decimal import Decimal

# DB Config
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Mapping équipes DB → Understat
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
    "Wolves": "Wolverhampton_Wanderers",
    "Everton": "Everton",
    "Nottingham Forest": "Nottingham_Forest",
    "Bournemouth": "Bournemouth",
    "Leicester": "Leicester",
    "Leeds": "Leeds",
    "Southampton": "Southampton",
    "Ipswich": "Ipswich",
    "Burnley": "Burnley",
    "Luton": "Luton",
    "Sheffield United": "Sheffield_United",
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
    "Cadiz": "Cadiz",
    "Granada": "Granada",
    "Espanyol": "Espanyol",
    "Valladolid": "Valladolid",
    "Leganes": "Leganes",
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
    "Sassuolo": "Sassuolo",
    "Empoli": "Empoli",
    "Cagliari": "Cagliari",
    "Verona": "Verona",
    "Lecce": "Lecce",
    "Genoa": "Genoa",
    "Salernitana": "Salernitana",
    "Frosinone": "Frosinone",
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
    "Stuttgart": "Stuttgart",
    "VfB Stuttgart": "VfB_Stuttgart",
    "Werder Bremen": "Werder_Bremen",
    "Bochum": "Bochum",
    "Heidenheim": "FC_Heidenheim",
    "FC Heidenheim": "FC_Heidenheim",
    "Darmstadt": "Darmstadt",
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
    "Lorient": "Lorient",
    "Metz": "Metz",
    "Clermont": "Clermont_Foot",
    "Auxerre": "Auxerre",
    "Angers": "Angers",
    "St Etienne": "Saint-Etienne",
}


class UnderstatScraper:
    """Scraper Understat avec approche 2-step"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.requests_count = 0
        
    def _get_data(self, url: str, variable_name: str) -> Optional[dict]:
        """Extrait une variable JSON d'une page Understat"""
        try:
            time.sleep(1.5)  # Rate limiting
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
            print(f"   ❌ Error: {e}")
            return None
            
    def get_team_season_data(self, team_name: str, season: str = "2024") -> Optional[dict]:
        """Récupère datesData d'une équipe (xG par match)"""
        understat_name = TEAM_MAPPING.get(team_name)
        if not understat_name:
            return None
            
        url = f"https://understat.com/team/{understat_name}/{season}"
        return self._get_data(url, "datesData")
        
    def get_match_shots(self, match_id: str) -> Optional[dict]:
        """Récupère shotsData d'un match (xG par tir avec minute)"""
        url = f"https://understat.com/match/{match_id}"
        return self._get_data(url, "shotsData")
        
    def calculate_team_xg_stats(self, dates_data: list, team_name: str) -> dict:
        """Calcule les stats xG depuis datesData"""
        if not dates_data:
            return {}
            
        finished = [m for m in dates_data if m.get('isResult')]
        if not finished:
            return {}
            
        xg_for_total = 0
        xg_against_total = 0
        goals_for_total = 0
        goals_against_total = 0
        
        # Détecter si l'équipe est home ou away dans chaque match
        for match in finished:
            is_home = team_name in match['h'].get('title', '') or \
                      TEAM_MAPPING.get(team_name, '').replace('_', ' ') in match['h'].get('title', '')
            
            if is_home:
                xg_for_total += float(match['xG']['h'])
                xg_against_total += float(match['xG']['a'])
                goals_for_total += int(match['goals']['h'])
                goals_against_total += int(match['goals']['a'])
            else:
                xg_for_total += float(match['xG']['a'])
                xg_against_total += float(match['xG']['h'])
                goals_for_total += int(match['goals']['a'])
                goals_against_total += int(match['goals']['h'])
                
        matches = len(finished)
        
        return {
            "matches": matches,
            "xg_for_total": round(xg_for_total, 2),
            "xg_against_total": round(xg_against_total, 2),
            "xg_for_avg": round(xg_for_total / matches, 3) if matches > 0 else 0,
            "xg_against_avg": round(xg_against_total / matches, 3) if matches > 0 else 0,
            "xg_diff": round(xg_for_total - xg_against_total, 2),
            "xg_diff_avg": round((xg_for_total - xg_against_total) / matches, 3) if matches > 0 else 0,
            "goals_for": goals_for_total,
            "goals_against": goals_against_total,
            "overperformance": round(goals_for_total - xg_for_total, 2),
            "underperformance_def": round(goals_against_total - xg_against_total, 2),
            "clinical": goals_for_total > xg_for_total,
            "last_5_xg": self._calculate_form_xg(finished[-5:], team_name) if len(finished) >= 5 else None
        }
        
    def _calculate_form_xg(self, matches: list, team_name: str) -> dict:
        """xG des 5 derniers matchs"""
        xg_for = 0
        xg_against = 0
        
        for match in matches:
            is_home = team_name in match['h'].get('title', '') or \
                      TEAM_MAPPING.get(team_name, '').replace('_', ' ') in match['h'].get('title', '')
            if is_home:
                xg_for += float(match['xG']['h'])
                xg_against += float(match['xG']['a'])
            else:
                xg_for += float(match['xG']['a'])
                xg_against += float(match['xG']['h'])
                
        return {
            "xg_for_avg": round(xg_for / len(matches), 3),
            "xg_against_avg": round(xg_against / len(matches), 3),
            "trend": "improving" if xg_for > xg_against else "declining"
        }
        
    def calculate_temporal_patterns(self, shots_data: dict, is_home: bool) -> dict:
        """Calcule patterns temporels depuis shotsData"""
        key = 'h' if is_home else 'a'
        shots = shots_data.get(key, [])
        
        if not shots:
            return {}
            
        periods = {
            "0-15": {"shots": 0, "xg": 0, "goals": 0},
            "16-30": {"shots": 0, "xg": 0, "goals": 0},
            "31-45": {"shots": 0, "xg": 0, "goals": 0},
            "46-60": {"shots": 0, "xg": 0, "goals": 0},
            "61-75": {"shots": 0, "xg": 0, "goals": 0},
            "76-90": {"shots": 0, "xg": 0, "goals": 0},
        }
        
        for shot in shots:
            minute = int(shot.get('minute', 0))
            xg = float(shot.get('xG', 0))
            is_goal = shot.get('result') == 'Goal'
            
            if minute <= 15: period = "0-15"
            elif minute <= 30: period = "16-30"
            elif minute <= 45: period = "31-45"
            elif minute <= 60: period = "46-60"
            elif minute <= 75: period = "61-75"
            else: period = "76-90"
            
            periods[period]["shots"] += 1
            periods[period]["xg"] += xg
            if is_goal:
                periods[period]["goals"] += 1
                
        total_xg = sum(p["xg"] for p in periods.values())
        total_goals = sum(p["goals"] for p in periods.values())
        
        return {
            "periods": periods,
            "first_half_xg_pct": round((periods["0-15"]["xg"] + periods["16-30"]["xg"] + periods["31-45"]["xg"]) / max(total_xg, 0.01) * 100, 1),
            "second_half_xg_pct": round((periods["46-60"]["xg"] + periods["61-75"]["xg"] + periods["76-90"]["xg"]) / max(total_xg, 0.01) * 100, 1),
            "late_xg_pct": round(periods["76-90"]["xg"] / max(total_xg, 0.01) * 100, 1),
            "first_half_goals_pct": round((periods["0-15"]["goals"] + periods["16-30"]["goals"] + periods["31-45"]["goals"]) / max(total_goals, 1) * 100, 1) if total_goals > 0 else 0,
            "late_goals_pct": round(periods["76-90"]["goals"] / max(total_goals, 1) * 100, 1) if total_goals > 0 else 0
        }


class QuantumEnricherUnderstat:
    """Enrichit quantum_dna avec données Understat"""
    
    def __init__(self):
        self.conn = None
        self.scraper = UnderstatScraper()
        
    def connect(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        
    def close(self):
        if self.conn:
            self.conn.close()
            
    def get_teams_to_enrich(self) -> List[dict]:
        """Équipes à enrichir"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT qtp.id, qtp.team_name, qtp.team_intelligence_id,
                       ti.xg_for_avg as current_xg
                FROM quantum.team_profiles qtp
                LEFT JOIN team_intelligence ti ON qtp.team_intelligence_id = ti.id
                WHERE qtp.tier IN ('ELITE', 'GOLD', 'SILVER', 'BRONZE', 'EXPERIMENTAL')
                ORDER BY qtp.total_pnl DESC
            """)
            return cur.fetchall()
            
    def enrich_team(self, team: dict) -> bool:
        """Enrichit une équipe avec données Understat"""
        team_name = team['team_name']
        
        # Vérifier si mapping existe
        if team_name not in TEAM_MAPPING:
            return False
            
        # Récupérer datesData
        dates_data = self.scraper.get_team_season_data(team_name, "2024")
        if not dates_data:
            return False
            
        # Calculer stats xG
        xg_stats = self.scraper.calculate_team_xg_stats(dates_data, team_name)
        if not xg_stats:
            return False
            
        # Mettre à jour team_intelligence
        if team['team_intelligence_id']:
            with self.conn.cursor() as cur:
                cur.execute("""
                    UPDATE team_intelligence
                    SET xg_for_avg = %s,
                        xg_against_avg = %s,
                        xg_difference = %s,
                        overperformance_goals = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (
                    xg_stats['xg_for_avg'],
                    xg_stats['xg_against_avg'],
                    xg_stats['xg_diff_avg'],
                    xg_stats['overperformance'],
                    team['team_intelligence_id']
                ))
                
        # Mettre à jour quantum_dna
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE quantum.team_profiles
                SET quantum_dna = jsonb_set(
                    jsonb_set(
                        quantum_dna,
                        '{context_dna, xg_profile}',
                        %s::jsonb
                    ),
                    '{temporal_dna, form_xg}',
                    %s::jsonb
                ),
                updated_at = NOW()
                WHERE id = %s
            """, (
                json.dumps({
                    "xg_for_avg": xg_stats['xg_for_avg'],
                    "xg_against_avg": xg_stats['xg_against_avg'],
                    "xg_diff": xg_stats['xg_diff'],
                    "overperformance": xg_stats['overperformance'],
                    "clinical": xg_stats['clinical'],
                    "matches_analyzed": xg_stats['matches']
                }),
                json.dumps(xg_stats.get('last_5_xg', {})),
                team['id']
            ))
            
        self.conn.commit()
        return True
        
    def run(self, max_teams: int = 80):
        """Lance l'enrichissement"""
        print("""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║     🔬 UNDERSTAT ENRICHMENT - xG Data                                                                         ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
        """)
        
        self.connect()
        teams = self.get_teams_to_enrich()
        print(f"✅ {len(teams)} équipes à enrichir")
        
        enriched = 0
        for team in teams[:max_teams]:
            team_name = team['team_name']
            
            if team_name not in TEAM_MAPPING:
                print(f"   ⚠️ {team_name}: pas de mapping Understat")
                continue
                
            print(f"   📊 {team_name}...", end=" ")
            
            if self.enrich_team(team):
                enriched += 1
                print("✅")
            else:
                print("❌")
                
            time.sleep(2)  # Rate limiting
            
        print(f"\n{'='*80}")
        print(f"✅ {enriched}/{min(len(teams), max_teams)} équipes enrichies avec xG Understat")
        print(f"   Requêtes effectuées: {self.scraper.requests_count}")
        
        self.close()


if __name__ == "__main__":
    enricher = QuantumEnricherUnderstat()
    enricher.run(max_teams=99)
