#!/usr/bin/env python3
"""
🏎️ FERRARI 2.0 - Collecteur de Buteurs ÉTENDU
==============================================
Récupère jusqu'à 100 buteurs par ligue (vs 10 avant)

Source: Football-Data.org API
Filtre: Buteurs avec ≥1 but (configurable)
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
    format='%(asctime)s [%(levelname)s] %(message)s'
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

# Ligues avec limit=100
COMPETITIONS = {
    "PL": {"name": "Premier League", "country": "England"},
    "PD": {"name": "La Liga", "country": "Spain"},
    "SA": {"name": "Serie A", "country": "Italy"},
    "BL1": {"name": "Bundesliga", "country": "Germany"},
    "FL1": {"name": "Ligue 1", "country": "France"},
}

# Configuration
MAX_SCORERS_PER_LEAGUE = 100
MIN_GOALS = 1  # Minimum de buts pour inclure


class ScorerCollectorExtended:
    """Collecteur étendu de buteurs"""
    
    def __init__(self):
        self.base_url = "https://api.football-data.org/v4"
        self.headers = {"X-Auth-Token": FOOTBALL_DATA_KEY}
        
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
    
    def fetch_scorers(self, competition_code: str, limit: int = 100) -> List[Dict]:
        """Récupère les buteurs avec limit étendu"""
        
        url = f"{self.base_url}/competitions/{competition_code}/scorers"
        params = {"limit": limit}
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 429:
                logger.warning("⚠️ Rate limit - attente 60s")
                time.sleep(60)
                return self.fetch_scorers(competition_code, limit)
            
            if response.status_code != 200:
                logger.error(f"❌ Erreur {response.status_code}")
                return []
            
            data = response.json()
            scorers = data.get("scorers", [])
            competition = data.get("competition", {})
            season = data.get("season", {})
            
            # Filtrer par minimum de buts
            filtered = [s for s in scorers if s.get("goals", 0) >= MIN_GOALS]
            
            logger.info(f"✅ {competition.get('name')}: {len(filtered)} buteurs (≥{MIN_GOALS} but)")
            
            return [{
                "raw": s,
                "competition": competition,
                "season": season
            } for s in filtered]
            
        except Exception as e:
            logger.error(f"❌ Erreur: {e}")
            return []
    
    def parse_scorer(self, scorer_data: Dict) -> Dict:
        """Parse les données d'un buteur"""
        
        raw = scorer_data.get("raw", {})
        player = raw.get("player", {})
        team = raw.get("team", {})
        competition = scorer_data.get("competition", {})
        season = scorer_data.get("season", {})
        
        goals = raw.get("goals", 0) or 0
        played = raw.get("playedMatches", 0) or 0
        assists = raw.get("assists", 0) or 0
        penalties = raw.get("penalties", 0) or 0
        
        goals_per_match = round(goals / played, 3) if played > 0 else 0
        
        # Tags automatiques
        tags = []
        if goals >= 10:
            tags.append("prolific")
        if goals_per_match >= 0.7:
            tags.append("clinical")
        if penalties >= 3:
            tags.append("penalty_taker")
        if assists >= 5:
            tags.append("playmaker")
        if played >= 10 and goals >= 5:
            tags.append("consistent")
        
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
            "season_assists": assists,
            "goals_per_match": goals_per_match,
            
            "penalties_scored": penalties,
            "is_penalty_taker": penalties >= 2,
            
            "tags": tags,
            
            "source": "football-data.org",
            "fetched_at": datetime.now().isoformat()
        }
    
    def upsert_scorer(self, conn, scorer_data: Dict) -> bool:
        """Insert ou update un buteur"""
        
        cur = conn.cursor()
        
        try:
            player_name = scorer_data.get("player_name")
            if not player_name:
                return False
            
            normalized = scorer_data.get("player_name_normalized")
            
            # Goals per 90 estimation
            goals = scorer_data.get("season_goals", 0) or 0
            matches = scorer_data.get("season_matches", 0) or 0
            minutes_estimate = matches * 75
            goals_per_90 = round((goals / minutes_estimate) * 90, 3) if minutes_estimate > 0 else None
            
            # Tags en JSON
            tags = scorer_data.get("tags", [])
            
            cur.execute("""
                INSERT INTO scorer_intelligence (
                    player_name, player_name_normalized,
                    nationality, birth_date, position_primary,
                    current_team, current_team_id,
                    season, season_matches, season_goals, season_assists,
                    goals_per_match, goals_per_90,
                    is_penalty_taker, penalties_scored,
                    tags,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
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
                    tags = EXCLUDED.tags,
                    updated_at = NOW()
                RETURNING id
            """, (
                player_name,
                normalized,
                scorer_data.get("nationality"),
                scorer_data.get("birth_date"),
                scorer_data.get("position_primary"),
                scorer_data.get("current_team"),
                scorer_data.get("current_team_id"),
                scorer_data.get("season", "2025-26"),
                scorer_data.get("season_matches"),
                scorer_data.get("season_goals"),
                scorer_data.get("season_assists"),
                scorer_data.get("goals_per_match"),
                goals_per_90,
                scorer_data.get("is_penalty_taker", False),
                scorer_data.get("penalties_scored"),
                json.dumps(tags) if tags else None
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Erreur upsert {scorer_data.get('player_name')}: {e}")
            return False
        finally:
            cur.close()
    
    def collect_all(self, min_goals: int = 1):
        """Collecte étendue de tous les buteurs"""
        
        global MIN_GOALS
        MIN_GOALS = min_goals
        
        logger.info("🏎️ FERRARI SCORER COLLECTOR - MODE ÉTENDU")
        logger.info("=" * 60)
        logger.info(f"�� Ligues: {list(COMPETITIONS.keys())}")
        logger.info(f"📊 Max par ligue: {MAX_SCORERS_PER_LEAGUE}")
        logger.info(f"📊 Min buts: {min_goals}")
        logger.info("=" * 60)
        
        conn = self._get_conn()
        stats = {"total": 0, "inserted": 0, "by_league": {}}
        
        for comp_code, comp_info in COMPETITIONS.items():
            logger.info(f"\n📍 {comp_info['name']} ({comp_code})...")
            
            scorers_raw = self.fetch_scorers(comp_code, limit=MAX_SCORERS_PER_LEAGUE)
            league_count = 0
            
            for scorer_raw in scorers_raw:
                parsed = self.parse_scorer(scorer_raw)
                stats["total"] += 1
                
                if self.upsert_scorer(conn, parsed):
                    stats["inserted"] += 1
                    league_count += 1
            
            stats["by_league"][comp_info["name"]] = league_count
            time.sleep(6)  # Rate limit
        
        conn.close()
        
        # Résumé
        logger.info("\n" + "=" * 60)
        logger.info("🏆 COLLECTE ÉTENDUE TERMINÉE!")
        logger.info(f"  📊 Total buteurs: {stats['total']}")
        logger.info(f"  ✅ Insérés/MàJ: {stats['inserted']}")
        logger.info("\n  📊 Par ligue:")
        for league, count in stats["by_league"].items():
            logger.info(f"     {league}: {count}")
        logger.info("=" * 60)
        
        return stats


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Collecteur de buteurs étendu")
    parser.add_argument("--min-goals", type=int, default=1,
                        help="Minimum de buts pour inclure (défaut: 1)")
    
    args = parser.parse_args()
    
    collector = ScorerCollectorExtended()
    collector.collect_all(min_goals=args.min_goals)


if __name__ == "__main__":
    main()
