#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║     🔬 QUANTUM ADN - ENRICHISSEMENT AVANCÉ                                                                    ║
║                                                                                                               ║
║  Sources: API-Football + Understat + Calculs dérivés                                                         ║
║  Cible: Remplir team_intelligence + quantum.team_profiles.quantum_dna                                        ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
"""

import json
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time
import os

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

# API-Football config
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "")
API_FOOTBALL_BASE = "https://v3.football.api-sports.io"

# Leagues à enrichir (ID API-Football)
TARGET_LEAGUES = {
    39: "Premier League",
    140: "La Liga", 
    135: "Serie A",
    78: "Bundesliga",
    61: "Ligue 1"
}

CURRENT_SEASON = 2025

# ═══════════════════════════════════════════════════════════════════════════════
# API-FOOTBALL CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

class APIFootballClient:
    """Client pour API-Football avec gestion de quota"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "x-apisports-key": api_key
        }
        self.requests_today = 0
        self.daily_limit = 100  # Free tier
        
    def _request(self, endpoint: str, params: dict) -> Optional[dict]:
        """Requête avec gestion d'erreurs et rate limiting"""
        if self.requests_today >= self.daily_limit:
            print(f"⚠️ Quota journalier atteint ({self.daily_limit})")
            return None
            
        url = f"{API_FOOTBALL_BASE}/{endpoint}"
        
        try:
            time.sleep(1)  # Rate limiting
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            self.requests_today += 1
            
            if response.status_code == 200:
                data = response.json()
                if data.get("errors"):
                    print(f"⚠️ API Error: {data['errors']}")
                    return None
                return data
            else:
                print(f"❌ HTTP {response.status_code}: {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"❌ Request failed: {e}")
            return None
            
    def get_team_statistics(self, team_id: int, league_id: int, season: int) -> Optional[dict]:
        """Récupère les statistiques complètes d'une équipe"""
        return self._request("teams/statistics", {
            "team": team_id,
            "league": league_id,
            "season": season
        })
        
    def get_fixtures(self, team_id: int, league_id: int, season: int, last: int = 10) -> Optional[dict]:
        """Récupère les derniers matchs d'une équipe"""
        return self._request("fixtures", {
            "team": team_id,
            "league": league_id,
            "season": season,
            "last": last
        })
        
    def get_fixtures_with_stats(self, fixture_id: int) -> Optional[dict]:
        """Récupère les stats détaillées d'un match"""
        return self._request("fixtures/statistics", {
            "fixture": fixture_id
        })


# ═══════════════════════════════════════════════════════════════════════════════
# UNDERSTAT SCRAPER (xG par minute)
# ═══════════════════════════════════════════════════════════════════════════════

class UnderstatScraper:
    """Scraper pour Understat (xG timing data)"""
    
    BASE_URL = "https://understat.com"
    
    # Mapping noms équipes -> Understat IDs
    TEAM_MAPPING = {
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
        "Barcelona": "Barcelona",
        "Real Madrid": "Real_Madrid",
        "Atletico Madrid": "Atletico_Madrid",
        "Inter": "Inter",
        "AC Milan": "Milan",
        "Juventus": "Juventus",
        "Napoli": "Napoli",
        "Lazio": "Lazio",
        "Roma": "Roma",
        "Bayern Munich": "Bayern_Munich",
        "Borussia Dortmund": "Borussia_Dortmund",
        "Paris Saint Germain": "Paris_Saint_Germain",
        "Marseille": "Marseille",
        "Lyon": "Lyon",
        "Monaco": "Monaco",
    }
    
    def get_team_shots_data(self, team_name: str, season: str = "2024") -> Optional[dict]:
        """Récupère les données de tirs avec timing"""
        understat_name = self.TEAM_MAPPING.get(team_name)
        if not understat_name:
            return None
            
        url = f"{self.BASE_URL}/team/{understat_name}/{season}"
        
        try:
            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                return None
                
            # Parse le JSON embarqué dans le HTML
            html = response.text
            
            # Chercher shotsData
            import re
            match = re.search(r"var shotsData\s*=\s*JSON\.parse\('(.+?)'\)", html)
            if match:
                json_str = match.group(1).encode().decode('unicode_escape')
                return json.loads(json_str)
                
            return None
            
        except Exception as e:
            print(f"❌ Understat error for {team_name}: {e}")
            return None
            
    def calculate_temporal_patterns(self, shots_data: dict) -> dict:
        """Calcule les patterns temporels depuis les données de tirs"""
        if not shots_data:
            return {}
            
        # Initialiser les buckets par période de 15 min
        periods = {
            "0-15": {"goals": 0, "xg": 0, "shots": 0},
            "16-30": {"goals": 0, "xg": 0, "shots": 0},
            "31-45": {"goals": 0, "xg": 0, "shots": 0},
            "46-60": {"goals": 0, "xg": 0, "shots": 0},
            "61-75": {"goals": 0, "xg": 0, "shots": 0},
            "76-90": {"goals": 0, "xg": 0, "shots": 0},
        }
        
        for shot in shots_data:
            minute = int(shot.get("minute", 0))
            xg = float(shot.get("xG", 0))
            is_goal = shot.get("result") == "Goal"
            
            # Déterminer la période
            if minute <= 15:
                period = "0-15"
            elif minute <= 30:
                period = "16-30"
            elif minute <= 45:
                period = "31-45"
            elif minute <= 60:
                period = "46-60"
            elif minute <= 75:
                period = "61-75"
            else:
                period = "76-90"
                
            periods[period]["shots"] += 1
            periods[period]["xg"] += xg
            if is_goal:
                periods[period]["goals"] += 1
                
        # Calculer les pourcentages
        total_goals = sum(p["goals"] for p in periods.values())
        total_xg = sum(p["xg"] for p in periods.values())
        
        result = {
            "goals_by_period": periods,
            "first_half_goals_pct": round((periods["0-15"]["goals"] + periods["16-30"]["goals"] + periods["31-45"]["goals"]) / max(total_goals, 1) * 100, 1),
            "second_half_goals_pct": round((periods["46-60"]["goals"] + periods["61-75"]["goals"] + periods["76-90"]["goals"]) / max(total_goals, 1) * 100, 1),
            "late_goals_pct": round(periods["76-90"]["goals"] / max(total_goals, 1) * 100, 1),
            "early_pressure_xg": round(periods["0-15"]["xg"] / max(total_xg, 1) * 100, 1),
            "total_goals": total_goals,
            "total_xg": round(total_xg, 2)
        }
        
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# CALCULATEUR DE MÉTRIQUES AVANCÉES
# ═══════════════════════════════════════════════════════════════════════════════

class AdvancedMetricsCalculator:
    """Calcule les métriques avancées pour l'ADN Quantum"""
    
    @staticmethod
    def calculate_ppda(passes_allowed_def_third: int, defensive_actions: int) -> float:
        """
        PPDA = Passes Allowed Per Defensive Action
        Plus bas = pressing plus intense
        """
        if defensive_actions == 0:
            return 15.0  # Valeur par défaut (pressing moyen)
        return round(passes_allowed_def_third / defensive_actions, 2)
        
    @staticmethod
    def calculate_intensity_score(ppda: float) -> int:
        """Score d'intensité 0-100 basé sur PPDA"""
        # PPDA < 8 = très haut pressing (score 90+)
        # PPDA > 15 = pressing bas (score < 40)
        if ppda <= 6:
            return 100
        elif ppda <= 8:
            return 90
        elif ppda <= 10:
            return 75
        elif ppda <= 12:
            return 60
        elif ppda <= 15:
            return 45
        else:
            return max(20, 100 - int(ppda * 5))
            
    @staticmethod
    def calculate_verticality(long_balls: int, total_passes: int) -> float:
        """Ratio de jeu vertical (long balls / total passes)"""
        if total_passes == 0:
            return 0.0
        return round(long_balls / total_passes * 100, 2)
        
    @staticmethod
    def calculate_width(crosses: int, total_passes: int) -> float:
        """Ratio de jeu en largeur (crosses / total passes)"""
        if total_passes == 0:
            return 0.0
        return round(crosses / total_passes * 100, 2)
        
    @staticmethod
    def calculate_xg_performance(goals: int, xg: float) -> dict:
        """Analyse de performance vs xG"""
        diff = goals - xg
        return {
            "goals": goals,
            "xg": round(xg, 2),
            "difference": round(diff, 2),
            "overperformance_pct": round(diff / max(xg, 0.1) * 100, 1),
            "clinical": diff > 0,
            "wasteful": diff < -2
        }
        
    @staticmethod
    def calculate_motivation_index(
        league_position: int,
        total_teams: int,
        points_from_target: int,
        matches_remaining: int,
        is_cup_match: bool = False,
        is_derby: bool = False,
        european_race: bool = False
    ) -> int:
        """
        Calcule l'index de motivation 0-100
        """
        base_score = 50
        
        # Position au classement
        position_pct = league_position / total_teams
        if position_pct <= 0.1:  # Top 10%
            base_score += 20
        elif position_pct <= 0.25:  # Top 25%
            base_score += 10
        elif position_pct >= 0.75:  # Bottom 25% (relegation battle)
            base_score += 25  # High motivation to survive
            
        # Proximité d'un objectif
        if abs(points_from_target) <= 3 and matches_remaining <= 10:
            base_score += 15
            
        # Contexte du match
        if is_cup_match:
            base_score += 10
        if is_derby:
            base_score += 15
        if european_race:
            base_score += 10
            
        return min(100, max(0, base_score))


# ═══════════════════════════════════════════════════════════════════════════════
# ENRICHISSEUR PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class QuantumEnricher:
    """Enrichit les données pour l'ADN Quantum"""
    
    def __init__(self):
        self.conn = None
        self.api_client = None
        self.understat = UnderstatScraper()
        self.calculator = AdvancedMetricsCalculator()
        self.enriched_count = 0
        
    def connect(self):
        """Connexion DB"""
        self.conn = psycopg2.connect(**DB_CONFIG)
        
        # Init API client si clé disponible
        if API_FOOTBALL_KEY:
            self.api_client = APIFootballClient(API_FOOTBALL_KEY)
            print("✅ API-Football client initialisé")
        else:
            print("⚠️ API_FOOTBALL_KEY non définie - utilisation données existantes uniquement")
            
    def close(self):
        if self.conn:
            self.conn.close()
            
    def get_teams_to_enrich(self) -> List[dict]:
        """Récupère les équipes à enrichir"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    qtp.id, qtp.team_name, qtp.team_intelligence_id,
                    ti.api_football_id, ti.league_id,
                    ti.xg_for_avg, ti.first_half_goals_pct
                FROM quantum.team_profiles qtp
                LEFT JOIN team_intelligence ti ON qtp.team_intelligence_id = ti.id
                WHERE qtp.tier IN ('ELITE', 'GOLD', 'SILVER')
                ORDER BY qtp.total_pnl DESC
            """)
            return cur.fetchall()
            
    def enrich_from_existing_data(self):
        """Enrichit depuis les données déjà en base (matches, odds, etc.)"""
        print("\n📊 Enrichissement depuis données existantes...")
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Calculer temporal patterns depuis les picks résolus
            cur.execute("""
                WITH team_temporal AS (
                    SELECT 
                        team,
                        COUNT(*) as total_picks,
                        AVG(CASE WHEN is_winner THEN 1.0 ELSE 0.0 END) as win_rate,
                        -- Utiliser market_type pour inférer les patterns
                        SUM(CASE WHEN market_type LIKE 'over_%' AND is_winner THEN 1 ELSE 0 END) as over_wins,
                        SUM(CASE WHEN market_type LIKE 'under_%' AND is_winner THEN 1 ELSE 0 END) as under_wins,
                        SUM(CASE WHEN market_type = 'btts_yes' AND is_winner THEN 1 ELSE 0 END) as btts_yes_wins,
                        SUM(CASE WHEN market_type = 'btts_no' AND is_winner THEN 1 ELSE 0 END) as btts_no_wins,
                        AVG(clv_percentage) as avg_clv,
                        AVG(edge_pct) as avg_edge
                    FROM (
                        SELECT home_team as team, market_type, is_winner, clv_percentage, edge_pct
                        FROM tracking_clv_picks WHERE is_resolved = true AND home_team IS NOT NULL
                        UNION ALL
                        SELECT away_team as team, market_type, is_winner, clv_percentage, edge_pct
                        FROM tracking_clv_picks WHERE is_resolved = true AND away_team IS NOT NULL
                    ) combined
                    GROUP BY team
                    HAVING COUNT(*) >= 5
                )
                SELECT * FROM team_temporal
            """)
            
            temporal_data = {row['team']: row for row in cur.fetchall()}
            print(f"   {len(temporal_data)} équipes avec données temporelles")
            
            # Enrichir les team_intelligence avec les patterns de marché
            for team_name, data in temporal_data.items():
                # Déterminer le profil de marché
                market_profile = {
                    "over_specialist": data['over_wins'] > data['under_wins'] * 1.5,
                    "under_specialist": data['under_wins'] > data['over_wins'] * 1.5,
                    "btts_yes_specialist": data['btts_yes_wins'] > data['btts_no_wins'] * 1.5,
                    "btts_no_specialist": data['btts_no_wins'] > data['btts_yes_wins'] * 1.5,
                    "avg_clv": round(data['avg_clv'] or 0, 3),
                    "avg_edge": round(data['avg_edge'] or 0, 3),
                    "sample_size": data['total_picks']
                }
                
                # Update quantum_dna
                cur.execute("""
                    UPDATE quantum.team_profiles
                    SET quantum_dna = jsonb_set(
                        quantum_dna,
                        '{market_dna, empirical_profile}',
                        %s::jsonb
                    ),
                    updated_at = NOW()
                    WHERE team_name = %s
                """, (json.dumps(market_profile, cls=DecimalEncoder), team_name))
                
            self.conn.commit()
            print(f"✅ {len(temporal_data)} profils market_dna enrichis")
            
    def enrich_from_team_intelligence(self):
        """Enrichit quantum_dna depuis team_intelligence existant"""
        print("\n📊 Enrichissement depuis team_intelligence...")
        
        with self.conn.cursor() as cur:
            # Version corrigée - home_profile est text, pas jsonb
            cur.execute("""
                UPDATE quantum.team_profiles qtp
                SET quantum_dna = jsonb_set(
                    jsonb_set(
                        jsonb_set(
                            jsonb_set(
                                jsonb_set(
                                    quantum_dna,
                                    '{context_dna, home_profile}',
                                    to_jsonb(COALESCE(ti.home_profile, 'unknown'))
                                ),
                                '{context_dna, away_profile}',
                                to_jsonb(COALESCE(ti.away_profile, 'unknown'))
                            ),
                            '{context_dna, goals_tendency}',
                            to_jsonb(COALESCE(ti.goals_tendency, 0))
                        ),
                        '{context_dna, btts_tendency}',
                        to_jsonb(COALESCE(ti.btts_tendency, 0))
                    ),
                    '{context_dna, draw_tendency}',
                    to_jsonb(COALESCE(ti.draw_tendency, 0))
                ),
                updated_at = NOW()
                FROM team_intelligence ti
                WHERE qtp.team_intelligence_id = ti.id
                AND qtp.team_intelligence_id IS NOT NULL
            """)
            
            count = cur.rowcount
            self.conn.commit()
            print(f"✅ {count} équipes enrichies depuis team_intelligence")
            
    def enrich_from_understat(self, teams: List[dict]):
        """Enrichit avec données Understat (xG timing)"""
        print("\n📊 Enrichissement depuis Understat...")
        
        enriched = 0
        for team in teams[:20]:  # Limiter pour éviter le rate limiting
            team_name = team['team_name']
            
            shots_data = self.understat.get_team_shots_data(team_name)
            if shots_data:
                temporal = self.understat.calculate_temporal_patterns(shots_data)
                
                if temporal:
                    with self.conn.cursor() as cur:
                        # Update quantum_dna avec temporal_dna
                        cur.execute("""
                            UPDATE quantum.team_profiles
                            SET quantum_dna = jsonb_set(
                                quantum_dna,
                                '{temporal_dna}',
                                %s::jsonb
                            ),
                            updated_at = NOW()
                            WHERE team_name = %s
                        """, (json.dumps(temporal, cls=DecimalEncoder), team_name))
                        
                        # Update team_intelligence si lié
                        if team['team_intelligence_id']:
                            cur.execute("""
                                UPDATE team_intelligence
                                SET first_half_goals_pct = %s,
                                    second_half_goals_pct = %s,
                                    late_goals_pct = %s,
                                    updated_at = NOW()
                                WHERE id = %s
                            """, (
                                temporal['first_half_goals_pct'],
                                temporal['second_half_goals_pct'],
                                temporal['late_goals_pct'],
                                team['team_intelligence_id']
                            ))
                            
                    self.conn.commit()
                    enriched += 1
                    print(f"   ✅ {team_name}: {temporal['total_goals']} buts, {temporal['late_goals_pct']}% late")
                    
            time.sleep(2)  # Rate limiting
            
        print(f"✅ {enriched} équipes enrichies depuis Understat")
        
    def enrich_from_api_football(self, teams: List[dict]):
        """Enrichit avec données API-Football"""
        if not self.api_client:
            print("⚠️ API-Football non disponible")
            return
            
        print("\n📊 Enrichissement depuis API-Football...")
        
        enriched = 0
        for team in teams:
            if not team['api_football_id'] or not team['league_id']:
                continue
                
            # Récupérer stats équipe
            stats = self.api_client.get_team_statistics(
                team['api_football_id'],
                team['league_id'],
                CURRENT_SEASON
            )
            
            if stats and stats.get('response'):
                data = stats['response']
                
                # Extraire métriques
                goals_for = data.get('goals', {}).get('for', {})
                goals_against = data.get('goals', {}).get('against', {})
                
                # xG si disponible
                xg_for = goals_for.get('expected', {}).get('total')
                xg_against = goals_against.get('expected', {}).get('total')
                
                if xg_for and xg_against:
                    with self.conn.cursor() as cur:
                        cur.execute("""
                            UPDATE team_intelligence
                            SET xg_for_avg = %s,
                                xg_against_avg = %s,
                                xg_difference = %s,
                                updated_at = NOW()
                            WHERE id = %s
                        """, (
                            xg_for,
                            xg_against,
                            xg_for - xg_against,
                            team['team_intelligence_id']
                        ))
                        
                    self.conn.commit()
                    enriched += 1
                    print(f"   ✅ {team['team_name']}: xG {xg_for:.1f} - {xg_against:.1f}")
                    
            if self.api_client.requests_today >= 50:  # Garder marge
                print("⚠️ Limite API proche, arrêt")
                break
                
        print(f"✅ {enriched} équipes enrichies depuis API-Football")
        
    def calculate_friction_matrix(self):
        """Calcule la matrice de friction entre équipes"""
        print("\n📊 Calcul de la matrice de friction...")
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Récupérer tous les profils avec style
            cur.execute("""
                SELECT id, team_name, current_style, 
                       quantum_dna->'context_dna'->>'home_strength' as home_strength,
                       quantum_dna->'context_dna'->>'away_strength' as away_strength
                FROM quantum.team_profiles
                WHERE current_style IS NOT NULL
            """)
            teams = cur.fetchall()
            
            if len(teams) < 2:
                print("⚠️ Pas assez d'équipes avec style pour calculer la friction")
                return
                
            # Matrice de friction par style
            STYLE_FRICTION = {
                ("offensive", "offensive"): 85,  # High-scoring potential
                ("offensive", "defensive"): 60,
                ("offensive", "balanced_offensive"): 75,
                ("offensive", "balanced_defensive"): 55,
                ("defensive", "defensive"): 30,  # Low-scoring grind
                ("defensive", "balanced_offensive"): 50,
                ("defensive", "balanced_defensive"): 35,
                ("balanced_offensive", "balanced_offensive"): 65,
                ("balanced_offensive", "balanced_defensive"): 55,
                ("balanced_defensive", "balanced_defensive"): 45,
            }
            
            inserted = 0
            for i, team_a in enumerate(teams):
                for team_b in teams[i+1:]:
                    style_a = team_a['current_style'] or 'balanced'
                    style_b = team_b['current_style'] or 'balanced'
                    
                    # Lookup friction (order doesn't matter)
                    key1 = (style_a, style_b)
                    key2 = (style_b, style_a)
                    base_friction = STYLE_FRICTION.get(key1) or STYLE_FRICTION.get(key2) or 50
                    
                    # Ajuster selon forces home/away
                    chaos_potential = base_friction
                    if base_friction >= 70:
                        chaos_potential = min(100, base_friction + 15)
                        
                    cur.execute("""
                        INSERT INTO quantum.matchup_friction (
                            team_a_id, team_a_name, style_a,
                            team_b_id, team_b_name, style_b,
                            friction_score, chaos_potential,
                            friction_vector
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (team_a_name, team_b_name) DO UPDATE SET
                            friction_score = EXCLUDED.friction_score,
                            chaos_potential = EXCLUDED.chaos_potential,
                            updated_at = NOW()
                    """, (
                        team_a['id'], team_a['team_name'], style_a,
                        team_b['id'], team_b['team_name'], style_b,
                        base_friction, chaos_potential,
                        json.dumps({
                            "style_clash": base_friction,
                            "offensive_potential": (base_friction + 100) / 2 if 'offensive' in style_a or 'offensive' in style_b else base_friction
                        })
                    ))
                    inserted += 1
                    
            self.conn.commit()
            print(f"✅ {inserted} paires de friction calculées")
            
    def print_summary(self):
        """Affiche le résumé de l'enrichissement"""
        print("\n" + "="*80)
        print("📊 RÉSUMÉ ENRICHISSEMENT QUANTUM")
        print("="*80)
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # quantum_dna remplis
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN quantum_dna->'temporal_dna' != '{}' THEN 1 ELSE 0 END) as with_temporal,
                    SUM(CASE WHEN quantum_dna->'market_dna'->'empirical_profile' IS NOT NULL THEN 1 ELSE 0 END) as with_market,
                    SUM(CASE WHEN quantum_dna->'context_dna'->'home_profile' IS NOT NULL THEN 1 ELSE 0 END) as with_context
                FROM quantum.team_profiles
            """)
            r = cur.fetchone()
            print(f"\n   Team Profiles: {r['total']} total")
            print(f"      - Avec temporal_dna: {r['with_temporal']}")
            print(f"      - Avec market_dna enrichi: {r['with_market']}")
            print(f"      - Avec context_dna complet: {r['with_context']}")
            
            # Friction matrix
            cur.execute("SELECT COUNT(*) FROM quantum.matchup_friction")
            print(f"\n   Matchup Friction: {cur.fetchone()['count']} paires")
            
            # team_intelligence enrichis
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN xg_for_avg IS NOT NULL THEN 1 ELSE 0 END) as with_xg,
                    SUM(CASE WHEN first_half_goals_pct IS NOT NULL THEN 1 ELSE 0 END) as with_temporal
                FROM team_intelligence
            """)
            r = cur.fetchone()
            print(f"\n   Team Intelligence: {r['total']} total")
            print(f"      - Avec xG: {r['with_xg']}")
            print(f"      - Avec temporels: {r['with_temporal']}")
            
        print("\n" + "="*80)


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║     🔬 QUANTUM ADN - ENRICHISSEMENT AVANCÉ                                                                    ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
    """)
    
    enricher = QuantumEnricher()
    
    try:
        enricher.connect()
        
        # 1. Récupérer équipes cibles
        teams = enricher.get_teams_to_enrich()
        print(f"✅ {len(teams)} équipes à enrichir (ELITE/GOLD/SILVER)")
        
        # 2. Enrichir depuis données existantes
        enricher.enrich_from_existing_data()
        enricher.enrich_from_team_intelligence()
        
        # 3. Enrichir depuis Understat (xG timing)
        enricher.enrich_from_understat(teams)
        
        # 4. Enrichir depuis API-Football (si dispo)
        enricher.enrich_from_api_football(teams)
        
        # 5. Calculer friction matrix
        enricher.calculate_friction_matrix()
        
        # 6. Résumé
        enricher.print_summary()
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        enricher.close()


if __name__ == "__main__":
    main()
