"""
Understat Goals Scraper - Hedge Fund Grade
═══════════════════════════════════════════════════════════════════════════

OBJECTIF:
    Scraper TOUS les buts de la saison 2024/2025 des 5 grands championnats
    avec détails complets pour First/Anytime Goalscorer markets.

DONNÉES RÉCUPÉRÉES PAR BUT:
    - player_id, player_name
    - team_id, team_name
    - match_id, date, opponent
    - minute (timing exact)
    - xG du tir
    - situation: OpenPlay, FromCorner, SetPiece, DirectFreekick, Penalty
    - shot_type: RightFoot, LeftFoot, Head
    - is_own_goal

LIGUES:
    - EPL (Premier League)
    - La_liga (La Liga)
    - Bundesliga
    - Serie_A
    - Ligue_1

Auteur: Mon_PS Quant Team
Version: 1.0.0
Date: 13 Décembre 2025
"""

import asyncio
import aiohttp
import json
import re
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

UNDERSTAT_BASE = "https://understat.com"
SEASON = "2024"  # Saison 2024/2025

LEAGUES = {
    "EPL": "Premier League",
    "La_liga": "La Liga",
    "Bundesliga": "Bundesliga",
    "Serie_A": "Serie A",
    "Ligue_1": "Ligue 1"
}

# Rate limiting respectueux
REQUEST_DELAY = 1.5  # secondes entre requêtes
MAX_RETRIES = 3

# Paths
DATA_DIR = Path("/home/Mon_ps/data/goals")
OUTPUT_FILE = DATA_DIR / "all_goals_2025_detailed.json"
PLAYERS_OUTPUT = DATA_DIR / "goalscorer_profiles_2025.json"


# ═══════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class GoalEvent:
    """Un but avec tous les détails."""
    goal_id: str
    player_id: int
    player_name: str
    team_id: int
    team_name: str
    match_id: int
    date: str
    home_team: str
    away_team: str
    is_home: bool
    opponent: str
    minute: int
    xg: float
    situation: str  # OpenPlay, FromCorner, SetPiece, DirectFreekick, Penalty
    shot_type: str  # RightFoot, LeftFoot, Head
    is_own_goal: bool
    result: str  # Score final
    league: str
    season: str = "2024/2025"

    # Calculés après
    is_first_goal: bool = False
    is_last_goal: bool = False
    goal_number_in_match: int = 0


@dataclass
class GoalscorerProfile:
    """Profil d'un buteur pour les marchés."""
    player_id: int
    player_name: str
    team_name: str
    league: str

    # Stats globales
    total_goals: int = 0
    total_xg: float = 0.0
    minutes_played: int = 0
    matches_played: int = 0

    # Goals per 90
    goals_per_90: float = 0.0
    xg_per_90: float = 0.0

    # First Goalscorer
    first_goals: int = 0
    first_goal_rate: float = 0.0

    # Last Goalscorer
    last_goals: int = 0
    last_goal_rate: float = 0.0

    # Timing distribution
    goals_0_15: int = 0
    goals_16_30: int = 0
    goals_31_45: int = 0
    goals_46_60: int = 0
    goals_61_75: int = 0
    goals_76_90: int = 0

    # Situation breakdown
    goals_open_play: int = 0
    goals_set_piece: int = 0
    goals_penalty: int = 0
    goals_header: int = 0

    # Conversion
    conversion_rate: float = 0.0
    overperformance: float = 0.0  # Goals - xG


# ═══════════════════════════════════════════════════════════════════════════
# SCRAPER CLASS
# ═══════════════════════════════════════════════════════════════════════════

class UnderstatGoalsScraper:
    """Scraper Understat pour tous les buts."""

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.all_goals: List[GoalEvent] = []
        self.matches_processed: set = set()
        self.stats = {
            "leagues_scraped": 0,
            "matches_scraped": 0,
            "goals_found": 0,
            "errors": 0
        }

    async def __aenter__(self):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        self.session = aiohttp.ClientSession(headers=headers)
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    # ─────────────────────────────────────────────────────────────────────
    # FETCH HTML
    # ─────────────────────────────────────────────────────────────────────

    async def fetch_page(self, url: str) -> Optional[str]:
        """Fetch une page avec retry."""
        for attempt in range(MAX_RETRIES):
            try:
                async with self.session.get(url, timeout=30) as response:
                    if response.status == 200:
                        return await response.text()
                    elif response.status == 429:  # Rate limited
                        wait = (attempt + 1) * 5
                        logger.warning(f"Rate limited, waiting {wait}s...")
                        await asyncio.sleep(wait)
                    else:
                        logger.error(f"HTTP {response.status} for {url}")
            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
                await asyncio.sleep(2)

        self.stats["errors"] += 1
        return None

    # ─────────────────────────────────────────────────────────────────────
    # PARSE UNDERSTAT DATA
    # ─────────────────────────────────────────────────────────────────────

    def extract_json_var(self, html: str, var_name: str) -> Optional[Any]:
        """Extrait une variable JSON du HTML Understat."""
        # Pattern: var datesData = JSON.parse('...')
        pattern = rf"var {var_name}\s*=\s*JSON\.parse\('(.+?)'\)"
        match = re.search(pattern, html)

        if match:
            json_str = match.group(1)
            # Decode unicode escapes
            json_str = json_str.encode().decode('unicode_escape')
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for {var_name}: {e}")
        return None

    # ─────────────────────────────────────────────────────────────────────
    # SCRAPE LEAGUE MATCHES
    # ─────────────────────────────────────────────────────────────────────

    async def scrape_league(self, league_code: str) -> List[Dict]:
        """Scrape tous les matchs d'une ligue."""
        url = f"{UNDERSTAT_BASE}/league/{league_code}/{SEASON}"
        logger.info(f"Scraping {LEAGUES[league_code]} ({league_code})...")

        html = await self.fetch_page(url)
        if not html:
            return []

        # Extraire datesData (liste des matchs)
        matches_data = self.extract_json_var(html, "datesData")
        if not matches_data:
            logger.error(f"No datesData found for {league_code}")
            return []

        logger.info(f"  Found {len(matches_data)} matches in {league_code}")
        return matches_data

    # ─────────────────────────────────────────────────────────────────────
    # SCRAPE MATCH DETAILS (SHOTS/GOALS)
    # ─────────────────────────────────────────────────────────────────────

    async def scrape_match(self, match_id: int, league: str) -> List[GoalEvent]:
        """Scrape les détails d'un match (tous les tirs/buts)."""
        if match_id in self.matches_processed:
            return []

        url = f"{UNDERSTAT_BASE}/match/{match_id}"
        html = await self.fetch_page(url)

        if not html:
            return []

        self.matches_processed.add(match_id)
        await asyncio.sleep(REQUEST_DELAY)  # Rate limiting

        # Extraire shotsData
        shots_data = self.extract_json_var(html, "shotsData")
        if not shots_data:
            return []

        # Extraire match info
        match_info = self.extract_json_var(html, "match_info") or {}

        goals = []
        home_shots = shots_data.get("h", [])
        away_shots = shots_data.get("a", [])

        # Parser les tirs qui sont des buts
        for shot in home_shots + away_shots:
            if shot.get("result") == "Goal":
                goal = self._parse_goal(shot, match_info, league, is_home=(shot in home_shots))
                if goal:
                    goals.append(goal)

        return goals

    def _parse_goal(self, shot: Dict, match_info: Dict, league: str, is_home: bool) -> Optional[GoalEvent]:
        """Parse un tir en GoalEvent."""
        try:
            home_team = match_info.get("h", {}).get("title", "Unknown")
            away_team = match_info.get("a", {}).get("title", "Unknown")

            team_name = home_team if is_home else away_team
            opponent = away_team if is_home else home_team

            # Extraire la minute (format "45+2" possible)
            minute_str = str(shot.get("minute", "0"))
            if "+" in minute_str:
                base, added = minute_str.split("+")
                minute = int(base) + int(added)
            else:
                minute = int(minute_str)

            goal = GoalEvent(
                goal_id=f"{shot.get('id', '')}",
                player_id=int(shot.get("player_id", 0)),
                player_name=shot.get("player", "Unknown"),
                team_id=int(shot.get("team_id", 0) if shot.get("team_id") else 0),
                team_name=team_name,
                match_id=int(shot.get("match_id", 0)),
                date=match_info.get("date", ""),
                home_team=home_team,
                away_team=away_team,
                is_home=is_home,
                opponent=opponent,
                minute=minute,
                xg=float(shot.get("xG", 0)),
                situation=shot.get("situation", "OpenPlay"),
                shot_type=shot.get("shotType", "RightFoot"),
                is_own_goal=shot.get("result") == "OwnGoal",
                result=f"{match_info.get('h', {}).get('goals', 0)}-{match_info.get('a', {}).get('goals', 0)}",
                league=league
            )
            return goal

        except Exception as e:
            logger.error(f"Error parsing goal: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────
    # CALCULATE FIRST/LAST GOAL FLAGS
    # ─────────────────────────────────────────────────────────────────────

    def calculate_goal_positions(self):
        """Calcule is_first_goal et is_last_goal pour chaque but."""
        # Grouper par match
        goals_by_match = defaultdict(list)
        for goal in self.all_goals:
            goals_by_match[goal.match_id].append(goal)

        # Pour chaque match, trier par minute et marquer
        for match_id, goals in goals_by_match.items():
            sorted_goals = sorted(goals, key=lambda g: g.minute)

            for i, goal in enumerate(sorted_goals):
                goal.goal_number_in_match = i + 1
                goal.is_first_goal = (i == 0)
                goal.is_last_goal = (i == len(sorted_goals) - 1)

        logger.info(f"Calculated positions for {len(goals_by_match)} matches")

    # ─────────────────────────────────────────────────────────────────────
    # BUILD GOALSCORER PROFILES
    # ─────────────────────────────────────────────────────────────────────

    def build_profiles(self) -> Dict[int, GoalscorerProfile]:
        """Construit les profils buteurs à partir des buts."""
        profiles: Dict[int, GoalscorerProfile] = {}

        for goal in self.all_goals:
            if goal.is_own_goal:
                continue

            player_id = goal.player_id

            if player_id not in profiles:
                profiles[player_id] = GoalscorerProfile(
                    player_id=player_id,
                    player_name=goal.player_name,
                    team_name=goal.team_name,
                    league=goal.league
                )

            p = profiles[player_id]
            p.total_goals += 1
            p.total_xg += goal.xg

            # First/Last
            if goal.is_first_goal:
                p.first_goals += 1
            if goal.is_last_goal:
                p.last_goals += 1

            # Timing
            if goal.minute <= 15:
                p.goals_0_15 += 1
            elif goal.minute <= 30:
                p.goals_16_30 += 1
            elif goal.minute <= 45:
                p.goals_31_45 += 1
            elif goal.minute <= 60:
                p.goals_46_60 += 1
            elif goal.minute <= 75:
                p.goals_61_75 += 1
            else:
                p.goals_76_90 += 1

            # Situation
            if goal.situation in ["OpenPlay"]:
                p.goals_open_play += 1
            elif goal.situation in ["FromCorner", "SetPiece", "DirectFreekick"]:
                p.goals_set_piece += 1
            elif goal.situation == "Penalty":
                p.goals_penalty += 1

            if goal.shot_type == "Head":
                p.goals_header += 1

        # Calculer les rates
        for p in profiles.values():
            if p.total_goals > 0:
                p.first_goal_rate = p.first_goals / p.total_goals
                p.last_goal_rate = p.last_goals / p.total_goals
                p.overperformance = p.total_goals - p.total_xg

        logger.info(f"Built {len(profiles)} goalscorer profiles")
        return profiles

    # ─────────────────────────────────────────────────────────────────────
    # MAIN SCRAPE
    # ─────────────────────────────────────────────────────────────────────

    async def scrape_all(self):
        """Scrape toutes les ligues."""
        logger.info("=" * 70)
        logger.info("UNDERSTAT GOALS SCRAPER - SAISON 2024/2025")
        logger.info("=" * 70)

        for league_code, league_name in LEAGUES.items():
            logger.info(f"\n{'─' * 50}")
            logger.info(f"📊 {league_name}")
            logger.info(f"{'─' * 50}")

            # Get all matches
            matches = await self.scrape_league(league_code)

            # Scrape each match for goals
            for i, match in enumerate(matches):
                match_id = match.get("id")
                if not match_id:
                    continue

                if match.get("isResult"):  # Match terminé
                    goals = await self.scrape_match(int(match_id), league_code)
                    self.all_goals.extend(goals)
                    self.stats["goals_found"] += len(goals)

                    if (i + 1) % 20 == 0:
                        logger.info(f"  Progress: {i+1}/{len(matches)} matches, {self.stats['goals_found']} goals")

            self.stats["leagues_scraped"] += 1
            self.stats["matches_scraped"] += len([m for m in matches if m.get("isResult")])

        # Calculate first/last goal
        self.calculate_goal_positions()

        logger.info("\n" + "=" * 70)
        logger.info("SCRAPING TERMINÉ")
        logger.info("=" * 70)
        logger.info(f"  Ligues: {self.stats['leagues_scraped']}")
        logger.info(f"  Matchs: {self.stats['matches_scraped']}")
        logger.info(f"  Buts: {self.stats['goals_found']}")
        logger.info(f"  Erreurs: {self.stats['errors']}")

    # ─────────────────────────────────────────────────────────────────────
    # SAVE DATA
    # ─────────────────────────────────────────────────────────────────────

    def save_data(self):
        """Sauvegarde les données."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Save all goals
        goals_data = [asdict(g) for g in self.all_goals]
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(goals_data, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Saved {len(goals_data)} goals to {OUTPUT_FILE}")

        # Build and save profiles
        profiles = self.build_profiles()
        profiles_data = {str(k): asdict(v) for k, v in profiles.items()}
        with open(PLAYERS_OUTPUT, "w", encoding="utf-8") as f:
            json.dump(profiles_data, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Saved {len(profiles_data)} profiles to {PLAYERS_OUTPUT}")

        # Summary stats
        summary = {
            "scrape_date": datetime.now().isoformat(),
            "season": "2024/2025",
            "leagues": list(LEAGUES.keys()),
            "total_goals": len(self.all_goals),
            "unique_scorers": len(profiles),
            "first_goals_total": sum(1 for g in self.all_goals if g.is_first_goal),
            "goals_by_league": {},
            "top_scorers": []
        }

        # Goals by league
        for league in LEAGUES:
            summary["goals_by_league"][league] = len([g for g in self.all_goals if g.league == league])

        # Top scorers
        top = sorted(profiles.values(), key=lambda p: p.total_goals, reverse=True)[:20]
        summary["top_scorers"] = [
            {"name": p.player_name, "team": p.team_name, "goals": p.total_goals,
             "xG": round(p.total_xg, 2), "first_goals": p.first_goals}
            for p in top
        ]

        summary_file = DATA_DIR / "scrape_summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Saved summary to {summary_file}")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

async def main():
    async with UnderstatGoalsScraper() as scraper:
        await scraper.scrape_all()
        scraper.save_data()


if __name__ == "__main__":
    print("=" * 70)
    print("🔬 UNDERSTAT GOALS SCRAPER - HEDGE FUND GRADE")
    print("=" * 70)
    print()

    asyncio.run(main())

    print()
    print("=" * 70)
    print("✅ SCRAPING TERMINÉ")
    print("=" * 70)
