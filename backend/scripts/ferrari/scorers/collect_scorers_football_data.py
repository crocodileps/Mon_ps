#!/usr/bin/env python3
"""
🏎️ FERRARI 2.0 - Collecteur de Buteurs via Football-Data.org
=============================================================
Source: Football-Data.org API (données ACTUELLES 2025-26)

Ligues supportées:
- PL: Premier League
- PD: La Liga  
- SA: Serie A
- BL1: Bundesliga
- FL1: Ligue 1

Output: scorer_intelligence table peuplée avec vraies données
"""

import os
import sys
import json
import time
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Dict, List, Optional
import logging
import re
import unicodedata

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/home/Mon_ps/logs/ferrari_scorers.log')
    ]
)
logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════
# CONFIGURATION
# ════════════════════════════════════════════════════════════

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "monps_db"),
    "user": os.getenv("DB_USER", "monps_user"),
    "password": os.getenv("DB_PASSWORD", "monps_secure_password_2024"),
    "port": 5432
}

FOOTBALL_DATA_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "59bc1cecbdb24362b71d7301ce32da91")

# Ligues Football-Data.org
COMPETITIONS = {
    "PL": {"name": "Premier League", "country": "England"},
    "PD": {"name": "La Liga", "country": "Spain"},
    "SA": {"name": "Serie A", "country": "Italy"},
    "BL1": {"name": "Bundesliga", "country": "Germany"},
    "FL1": {"name": "Ligue 1", "country": "France"},
}

# API-Football pour données complémentaires (2023)
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY_MAIN", "8fbe542554070a5f04ae8aec40f9afba")

API_FOOTBALL_LEAGUES = {
    "Premier League": 39,
    "La Liga": 140,
    "Serie A": 135,
    "Bundesliga": 78,
    "Ligue 1": 61,
}


class ScorerCollectorFootballData:
    """Collecteur de buteurs via Football-Data.org"""
    
    def __init__(self):
        self.base_url = "https://api.football-data.org/v4"
        self.headers = {"X-Auth-Token": FOOTBALL_DATA_KEY}
        self.collected_scorers = {}
        
    def _get_conn(self):
        return psycopg2.connect(**DB_CONFIG)
    
    def normalize_name(self, name: str) -> str:
        """Normalise le nom pour matching"""
        if not name:
            return ""
        name = unicodedata.normalize('NFKD', name)
        name = name.encode('ASCII', 'ignore').decode('ASCII')
        name = name.lower().strip()
        name = re.sub(r'\s+(jr|sr|ii|iii)\.?$', '', name)
        return name
    
    # ════════════════════════════════════════════════════════════
    # FOOTBALL-DATA.ORG (DONNÉES 2025-26)
    # ════════════════════════════════════════════════════════════
    
    def fetch_scorers(self, competition_code: str) -> List[Dict]:
        """Récupère les buteurs depuis Football-Data.org"""
        
        url = f"{self.base_url}/competitions/{competition_code}/scorers"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 429:
                logger.warning("⚠️ Rate limit - attente 60s")
                time.sleep(60)
                return self.fetch_scorers(competition_code)
            
            if response.status_code != 200:
                logger.error(f"❌ Erreur {response.status_code}: {response.text[:200]}")
                return []
            
            data = response.json()
            
            competition = data.get("competition", {})
            season = data.get("season", {})
            scorers = data.get("scorers", [])
            
            logger.info(f"✅ {competition.get('name')}: {len(scorers)} buteurs (saison {season.get('startDate', '')[:4]})")
            
            return [{
                "raw": s,
                "competition": competition,
                "season": season
            } for s in scorers]
            
        except Exception as e:
            logger.error(f"❌ Erreur fetch {competition_code}: {e}")
            return []
    
    def parse_scorer(self, scorer_data: Dict) -> Dict:
        """Parse les données d'un buteur"""
        
        raw = scorer_data.get("raw", {})
        player = raw.get("player", {})
        team = raw.get("team", {})
        competition = scorer_data.get("competition", {})
        season = scorer_data.get("season", {})
        
        # Calculer goals per match
        goals = raw.get("goals", 0) or 0
        played = raw.get("playedMatches", 0) or 0
        goals_per_match = round(goals / played, 3) if played > 0 else 0
        
        # Penalties
        penalties = raw.get("penalties", 0) or 0
        is_penalty_taker = penalties >= 2
        
        return {
            "player_name": player.get("name"),
            "player_name_normalized": self.normalize_name(player.get("name")),
            "nationality": player.get("nationality"),
            "birth_date": player.get("dateOfBirth"),
            "position_primary": player.get("position"),
            
            "current_team": team.get("name"),
            "current_team_id": team.get("id"),
            "league": competition.get("name"),
            
            "season": f"{season.get('startDate', '')[:4]}-{season.get('endDate', '')[:4][-2:]}",
            "season_matches": played,
            "season_goals": goals,
            "season_assists": raw.get("assists"),
            "goals_per_match": goals_per_match,
            
            "penalties_scored": penalties,
            "is_penalty_taker": is_penalty_taker,
            
            "source": "football-data.org",
            "fetched_at": datetime.now().isoformat()
        }
    
    # ════════════════════════════════════════════════════════════
    # API-FOOTBALL (DONNÉES COMPLÉMENTAIRES 2023)
    # ════════════════════════════════════════════════════════════
    
    def fetch_api_football_data(self, player_name: str, league_name: str) -> Optional[Dict]:
        """Récupère données complémentaires depuis API-Football 2023"""
        
        league_id = API_FOOTBALL_LEAGUES.get(league_name)
        if not league_id:
            return None
        
        url = "https://v3.football.api-sports.io/players/topscorers"
        params = {"league": league_id, "season": 2023}
        headers = {"x-apisports-key": API_FOOTBALL_KEY}
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            data = response.json()
            
            if data.get("errors"):
                return None
            
            # Chercher le joueur par nom
            normalized_search = self.normalize_name(player_name)
            
            for p in data.get("response", []):
                player = p.get("player", {})
                if self.normalize_name(player.get("name")) == normalized_search:
                    stats = p.get("statistics", [{}])[0]
                    return {
                        "api_football_id": player.get("id"),
                        "photo_url": player.get("photo"),
                        "height_cm": self._parse_height(player.get("height")),
                        "age": player.get("age"),
                        "season_2023_goals": stats.get("goals", {}).get("total", 0),
                        "season_2023_assists": stats.get("goals", {}).get("assists", 0),
                        "penalties_taken_2023": stats.get("penalty", {}).get("taken", 0),
                        "penalties_scored_2023": stats.get("penalty", {}).get("scored", 0),
                    }
            
            return None
            
        except Exception as e:
            logger.debug(f"API-Football lookup failed: {e}")
            return None
    
    def _parse_height(self, height_str: str) -> Optional[int]:
        if not height_str:
            return None
        match = re.search(r'(\d+)', str(height_str))
        return int(match.group(1)) if match else None
    
    # ════════════════════════════════════════════════════════════
    # INSERTION DATABASE
    # ════════════════════════════════════════════════════════════
    
    def upsert_scorer(self, conn, scorer_data: Dict) -> bool:
        """Insert ou update un buteur"""
        
        cur = conn.cursor()
        
        try:
            player_name = scorer_data.get("player_name")
            if not player_name:
                return False
            
            normalized = scorer_data.get("player_name_normalized") or self.normalize_name(player_name)
            
            # Calculer goals per 90 (estimation basée sur ~80 min par match)
            goals = scorer_data.get("season_goals", 0) or 0
            matches = scorer_data.get("season_matches", 0) or 0
            minutes_estimate = matches * 80  # Estimation
            goals_per_90 = round((goals / minutes_estimate) * 90, 3) if minutes_estimate > 0 else None
            
            cur.execute("""
                INSERT INTO scorer_intelligence (
                    player_name, player_name_normalized,
                    api_football_id, photo_url, nationality, birth_date, height_cm,
                    current_team, current_team_id, position_primary,
                    season, season_matches, season_goals, season_assists,
                    goals_per_match, goals_per_90,
                    is_penalty_taker, penalties_scored,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    NOW(), NOW()
                )
                ON CONFLICT (player_name_normalized) 
                DO UPDATE SET
                    current_team = COALESCE(EXCLUDED.current_team, scorer_intelligence.current_team),
                    season = EXCLUDED.season,
                    season_matches = EXCLUDED.season_matches,
                    season_goals = EXCLUDED.season_goals,
                    season_assists = COALESCE(EXCLUDED.season_assists, scorer_intelligence.season_assists),
                    goals_per_match = EXCLUDED.goals_per_match,
                    goals_per_90 = COALESCE(EXCLUDED.goals_per_90, scorer_intelligence.goals_per_90),
                    updated_at = NOW()
                RETURNING id
            """, (
                player_name,
                normalized,
                scorer_data.get("api_football_id"),
                scorer_data.get("photo_url"),
                scorer_data.get("nationality"),
                scorer_data.get("birth_date"),
                scorer_data.get("height_cm"),
                scorer_data.get("current_team"),
                scorer_data.get("current_team_id"),
                scorer_data.get("position_primary"),
                scorer_data.get("season", "2025-26"),
                scorer_data.get("season_matches"),
                scorer_data.get("season_goals"),
                scorer_data.get("season_assists"),
                scorer_data.get("goals_per_match"),
                goals_per_90,
                scorer_data.get("is_penalty_taker", False),
                scorer_data.get("penalties_scored")
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Erreur upsert {scorer_data.get('player_name')}: {e}")
            return False
        finally:
            cur.close()
    
    # ════════════════════════════════════════════════════════════
    # EXÉCUTION PRINCIPALE
    # ════════════════════════════════════════════════════════════
    
    def collect_all(self, enrich_with_api_football: bool = False):
        """Collecte tous les buteurs des 5 grandes ligues"""
        
        logger.info("🏎️ FERRARI SCORER COLLECTOR - Football-Data.org")
        logger.info("=" * 60)
        logger.info(f"📊 Ligues: {list(COMPETITIONS.keys())}")
        logger.info(f"🔄 Enrichissement API-Football: {enrich_with_api_football}")
        logger.info("=" * 60)
        
        conn = self._get_conn()
        stats = {"total": 0, "inserted": 0, "enriched": 0}
        
        for comp_code, comp_info in COMPETITIONS.items():
            logger.info(f"\n📍 {comp_info['name']} ({comp_code})...")
            
            scorers_raw = self.fetch_scorers(comp_code)
            
            for scorer_raw in scorers_raw:
                parsed = self.parse_scorer(scorer_raw)
                stats["total"] += 1
                
                # Enrichir avec API-Football si demandé
                if enrich_with_api_football and parsed.get("player_name"):
                    api_data = self.fetch_api_football_data(
                        parsed["player_name"],
                        comp_info["name"]
                    )
                    if api_data:
                        parsed.update(api_data)
                        stats["enriched"] += 1
                        time.sleep(0.5)  # Rate limit
                
                # Insérer
                if self.upsert_scorer(conn, parsed):
                    stats["inserted"] += 1
            
            time.sleep(6)  # Respecter rate limit Football-Data.org (10 req/min)
        
        conn.close()
        
        # ═══ RÉSUMÉ ═══
        logger.info("\n" + "=" * 60)
        logger.info("🏆 COLLECTE TERMINÉE!")
        logger.info(f"  📊 Total buteurs: {stats['total']}")
        logger.info(f"  ✅ Insérés: {stats['inserted']}")
        logger.info(f"  🔄 Enrichis (API-Football): {stats['enriched']}")
        logger.info("=" * 60)
        
        return stats


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Collecteur de buteurs Football-Data.org")
    parser.add_argument("--enrich", action="store_true", 
                        help="Enrichir avec API-Football 2023")
    parser.add_argument("--league", type=str, default=None,
                        help="Collecter une seule ligue (PL, PD, SA, BL1, FL1)")
    
    args = parser.parse_args()
    
    collector = ScorerCollectorFootballData()
    
    if args.league:
        # Collecter une seule ligue
        conn = collector._get_conn()
        scorers = collector.fetch_scorers(args.league)
        for s in scorers:
            parsed = collector.parse_scorer(s)
            collector.upsert_scorer(conn, parsed)
        conn.close()
    else:
        collector.collect_all(enrich_with_api_football=args.enrich)


if __name__ == "__main__":
    main()
