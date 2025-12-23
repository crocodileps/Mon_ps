#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
GOALS DATA PROVIDER - Facade SQL Hedge Fund Grade
═══════════════════════════════════════════════════════════════════════════════

Remplace la lecture directe de all_goals_2025.json par des requetes SQL.
Source: quantum.goals_unified (PostgreSQL SSOT)

USAGE:
    from services.goals.data_provider import GoalsDataProvider

    provider = GoalsDataProvider()

    # Tous les buts
    goals = provider.get_all_goals()

    # Buts par joueur (pour loader_v5.py)
    salah_goals = provider.get_goals_by_player("Mohamed Salah")

    # Stats timing joueur (DIESEL, FAST_STARTER, etc.)
    timing = provider.get_player_timing_stats("Mohamed Salah")

Auteur: Mon_PS Team
Date: 2025-12-23
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Optional

try:
    from .config import DB_CONFIG
except ImportError:
    # Execution directe (python data_provider.py)
    from config import DB_CONFIG

logger = logging.getLogger(__name__)


class GoalsDataProvider:
    """
    Facade SQL pour acceder aux donnees goals.
    Remplace: with open('all_goals_2025.json') as f: goals = json.load(f)
    """

    def __init__(self):
        self._connection = None

    def _get_connection(self):
        """Connexion lazy a PostgreSQL."""
        if self._connection is None or self._connection.closed:
            self._connection = psycopg2.connect(**DB_CONFIG)
        return self._connection

    def _execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute une requete et retourne les resultats."""
        try:
            conn = self._get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Erreur SQL: {e}")
            return []

    # ═══════════════════════════════════════════════════════════════════════════
    # METHODES PRINCIPALES
    # ═══════════════════════════════════════════════════════════════════════════

    def get_all_goals(self, season: str = "2025") -> List[Dict]:
        """
        Retourne tous les buts de la saison.
        Equivalent: json.load(open('all_goals_2025.json'))
        """
        query = """
            SELECT * FROM quantum.goals_unified
            WHERE season = %s
            ORDER BY date, match_id, minute
        """
        return self._execute_query(query, (season,))

    def get_goals_by_player(self, player_name: str, season: str = "2025") -> List[Dict]:
        """
        Buts d'un joueur specifique.
        Pour: loader_v5.py enrichissement profils joueurs
        """
        query = """
            SELECT * FROM quantum.goals_unified
            WHERE player_name = %s AND season = %s
            ORDER BY date, minute
        """
        return self._execute_query(query, (player_name, season))

    def get_goals_by_team(self, team_name: str, season: str = "2025") -> List[Dict]:
        """
        Buts d'une equipe (marques par l'equipe).
        Pour: stats attaque equipe
        """
        query = """
            SELECT * FROM quantum.goals_unified
            WHERE team_name = %s AND season = %s
            ORDER BY date, minute
        """
        return self._execute_query(query, (team_name, season))

    def get_goals_against_team(self, team_name: str, season: str = "2025") -> List[Dict]:
        """
        Buts encaisses par une equipe.
        Pour: stats defense equipe
        """
        query = """
            SELECT * FROM quantum.goals_unified
            WHERE opponent = %s AND season = %s
            ORDER BY date, minute
        """
        return self._execute_query(query, (team_name, season))

    # ═══════════════════════════════════════════════════════════════════════════
    # STATS AGREGEES POUR LOADER_V5.PY
    # ═══════════════════════════════════════════════════════════════════════════

    def get_player_timing_stats(self, player_name: str, season: str = "2025") -> Dict:
        """
        Stats timing d'un joueur (pour DIESEL, FAST_STARTER, etc.)

        Retourne:
            {
                "total_goals": 15,
                "goals_0_15": 2,
                "goals_16_30": 3,
                "goals_31_45": 2,
                "goals_46_60": 3,
                "goals_61_75": 3,
                "goals_76_90": 2,
                "goals_first_half": 7,
                "goals_second_half": 8,
                "avg_minute": 52.3,
                "timing_profile": "BALANCED"  # ou DIESEL, FAST_STARTER
            }
        """
        query = """
            SELECT
                COUNT(*) as total_goals,
                SUM(CASE WHEN minute <= 15 THEN 1 ELSE 0 END) as goals_0_15,
                SUM(CASE WHEN minute > 15 AND minute <= 30 THEN 1 ELSE 0 END) as goals_16_30,
                SUM(CASE WHEN minute > 30 AND minute <= 45 THEN 1 ELSE 0 END) as goals_31_45,
                SUM(CASE WHEN minute > 45 AND minute <= 60 THEN 1 ELSE 0 END) as goals_46_60,
                SUM(CASE WHEN minute > 60 AND minute <= 75 THEN 1 ELSE 0 END) as goals_61_75,
                SUM(CASE WHEN minute > 75 THEN 1 ELSE 0 END) as goals_76_90,
                SUM(CASE WHEN half = '1H' THEN 1 ELSE 0 END) as goals_first_half,
                SUM(CASE WHEN half = '2H' THEN 1 ELSE 0 END) as goals_second_half,
                AVG(minute) as avg_minute
            FROM quantum.goals_unified
            WHERE player_name = %s AND season = %s
        """
        results = self._execute_query(query, (player_name, season))

        if not results or results[0]["total_goals"] == 0:
            return {"total_goals": 0, "timing_profile": "UNKNOWN"}

        stats = results[0]
        stats["timing_profile"] = self._calculate_timing_profile(stats)
        return stats

    def get_player_style_stats(self, player_name: str, season: str = "2025") -> Dict:
        """
        Stats style de but (pour open_play, headers, set_pieces, etc.)
        """
        query = """
            SELECT
                COUNT(*) as total_goals,
                SUM(CASE WHEN situation = 'OpenPlay' THEN 1 ELSE 0 END) as open_play,
                SUM(CASE WHEN situation = 'FromCorner' THEN 1 ELSE 0 END) as from_corner,
                SUM(CASE WHEN situation = 'SetPiece' THEN 1 ELSE 0 END) as set_piece,
                SUM(CASE WHEN situation = 'DirectFreekick' THEN 1 ELSE 0 END) as free_kick,
                SUM(CASE WHEN situation = 'Penalty' THEN 1 ELSE 0 END) as penalty,
                SUM(CASE WHEN shot_type = 'Head' THEN 1 ELSE 0 END) as headers
            FROM quantum.goals_unified
            WHERE player_name = %s AND season = %s
        """
        results = self._execute_query(query, (player_name, season))
        return results[0] if results else {"total_goals": 0}

    def get_player_home_away_stats(self, player_name: str, season: str = "2025") -> Dict:
        """
        Stats home/away (pour HOME_SPECIALIST, AWAY_SPECIALIST, etc.)
        """
        query = """
            SELECT
                COUNT(*) as total_goals,
                SUM(CASE WHEN is_home = true THEN 1 ELSE 0 END) as goals_home,
                SUM(CASE WHEN is_home = false THEN 1 ELSE 0 END) as goals_away
            FROM quantum.goals_unified
            WHERE player_name = %s AND season = %s
        """
        results = self._execute_query(query, (player_name, season))

        if not results or results[0]["total_goals"] == 0:
            return {"total_goals": 0, "home_away_profile": "UNKNOWN"}

        stats = results[0]
        stats["home_away_profile"] = self._calculate_home_away_profile(stats)
        return stats

    # ═══════════════════════════════════════════════════════════════════════════
    # HELPERS PRIVES
    # ═══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _calculate_timing_profile(stats: Dict) -> str:
        """Calcule le profil timing (DIESEL, FAST_STARTER, BALANCED)."""
        total = stats.get("total_goals", 0)
        if total == 0:
            return "UNKNOWN"

        first_half = stats.get("goals_first_half", 0)

        ratio = first_half / total if total > 0 else 0.5

        if ratio >= 0.65:
            return "FAST_STARTER"
        elif ratio <= 0.35:
            return "DIESEL"
        else:
            return "BALANCED"

    @staticmethod
    def _calculate_home_away_profile(stats: Dict) -> str:
        """Calcule le profil home/away."""
        total = stats.get("total_goals", 0)
        if total == 0:
            return "UNKNOWN"

        home = stats.get("goals_home", 0)

        ratio = home / total if total > 0 else 0.5

        if ratio >= 0.70:
            return "HOME_SPECIALIST"
        elif ratio <= 0.30:
            return "AWAY_SPECIALIST"
        else:
            return "BALANCED"

    def close(self):
        """Ferme la connexion."""
        if self._connection:
            self._connection.close()
            self._connection = None


# ═══════════════════════════════════════════════════════════════════════════════
# TEST RAPIDE
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("TEST GOALS DATA PROVIDER")
    print("=" * 70)

    provider = GoalsDataProvider()

    # Test 1: Tous les buts
    all_goals = provider.get_all_goals()
    print(f"\n[TEST 1] get_all_goals(): {len(all_goals)} buts")

    # Test 2: Top 5 equipes
    from collections import Counter
    teams = Counter(g["team_name"] for g in all_goals)
    print(f"\n[TEST 2] Top 5 equipes:")
    for team, count in teams.most_common(5):
        print(f"   - {team}: {count} buts")

    # Test 3: Buts Liverpool
    liverpool_goals = provider.get_goals_by_team("Liverpool")
    print(f"\n[TEST 3] get_goals_by_team('Liverpool'): {len(liverpool_goals)} buts")

    # Test 4: Buts encaisses par Liverpool
    against_liverpool = provider.get_goals_against_team("Liverpool")
    print(f"\n[TEST 4] get_goals_against_team('Liverpool'): {len(against_liverpool)} buts")

    # Test 5: Top buteur Liverpool et ses stats
    if liverpool_goals:
        scorers = Counter(g["player_name"] for g in liverpool_goals)
        top_scorer = scorers.most_common(1)[0][0] if scorers else None
        if top_scorer:
            print(f"\n[TEST 5] Top buteur Liverpool: {top_scorer} ({scorers[top_scorer]} buts)")

            # Stats timing
            timing = provider.get_player_timing_stats(top_scorer)
            print(f"\n[TEST 6] get_player_timing_stats('{top_scorer}'):")
            print(f"   - Total: {timing.get('total_goals', 0)} buts")
            print(f"   - Avg minute: {timing.get('avg_minute', 0):.1f}")
            print(f"   - 1H/2H: {timing.get('goals_first_half', 0)}/{timing.get('goals_second_half', 0)}")
            print(f"   - Profil: {timing.get('timing_profile', 'N/A')}")

            # Stats style
            style = provider.get_player_style_stats(top_scorer)
            print(f"\n[TEST 7] get_player_style_stats('{top_scorer}'):")
            print(f"   - Open play: {style.get('open_play', 0)}")
            print(f"   - Headers: {style.get('headers', 0)}")
            print(f"   - Penalties: {style.get('penalty', 0)}")

            # Stats home/away
            home_away = provider.get_player_home_away_stats(top_scorer)
            print(f"\n[TEST 8] get_player_home_away_stats('{top_scorer}'):")
            print(f"   - Home: {home_away.get('goals_home', 0)}")
            print(f"   - Away: {home_away.get('goals_away', 0)}")
            print(f"   - Profil: {home_away.get('home_away_profile', 'N/A')}")

    provider.close()
    print("\n" + "=" * 70)
    print("TESTS TERMINES")
    print("=" * 70)
