"""
Goalscorer Data Transformer - Hedge Fund Grade
═══════════════════════════════════════════════════════════════════════════

OBJECTIF:
    Fusionner Understat (buts détaillés) + FBRef (stats avancées)
    → Générer goalscorer_profiles_2025.json pour First/Anytime Goalscorer

SOURCES:
    1. all_shots_against_2025.json (Understat)
       - 1,869 buts avec minute exacte
       - Calcul is_first_goal, is_last_goal

    2. fbref_players_complete_2025_26.json (FBRef)
       - Minutes played, xG avancé, conversion rate

OUTPUT:
    - data/goals/all_goals_detailed_2025.json (tous les buts enrichis)
    - data/goals/goalscorer_profiles_2025.json (profils par joueur)
    - data/goals/first_goalscorer_stats.json (stats First GS par équipe)

Auteur: Mon_PS Quant Team
Version: 1.0.0
Date: 13 Décembre 2025
Saison: 2025/2026
"""

import json
import logging
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any
from datetime import datetime

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════════════════════════

BASE_DIR = Path("/home/Mon_ps")
DATA_DIR = BASE_DIR / "data"

# Input files
UNDERSTAT_SHOTS = DATA_DIR / "goalkeeper_dna" / "all_shots_against_2025.json"
FBREF_PLAYERS = DATA_DIR / "fbref" / "fbref_players_complete_2025_26.json"

# Output files
OUTPUT_DIR = DATA_DIR / "goals"
GOALS_OUTPUT = OUTPUT_DIR / "all_goals_detailed_2025.json"
PROFILES_OUTPUT = OUTPUT_DIR / "goalscorer_profiles_2025.json"
FIRST_GS_OUTPUT = OUTPUT_DIR / "first_goalscorer_stats.json"
SUMMARY_OUTPUT = OUTPUT_DIR / "transformation_summary.json"


# ═══════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class GoalEvent:
    """Un but avec tous les détails."""
    goal_id: str
    player_id: str
    player_name: str
    team_name: str
    opponent: str
    league: str
    match_id: str
    date: str
    minute: int
    xg: float
    situation: str  # OpenPlay, FromCorner, SetPiece, DirectFreekick, Penalty
    shot_type: str  # RightFoot, LeftFoot, Head
    is_home: bool
    home_team: str
    away_team: str

    # Calculés
    is_first_goal: bool = False
    is_last_goal: bool = False
    goal_number_in_match: int = 0

    # Période
    period: str = ""  # 0-15, 16-30, 31-45, 46-60, 61-75, 76-90


@dataclass
class GoalscorerProfile:
    """Profil complet d'un buteur."""
    player_id: str
    player_name: str
    team_name: str
    league: str

    # Stats de base
    total_goals: int = 0
    total_xg: float = 0.0
    matches_with_goal: int = 0

    # FBRef data (enrichi)
    minutes_played: int = 0
    goals_per_90: float = 0.0
    xg_per_90: float = 0.0
    shots_total: int = 0
    shots_on_target: int = 0
    conversion_rate: float = 0.0  # Goals / Shots
    overperformance: float = 0.0  # Goals - xG

    # First Goalscorer
    first_goals: int = 0
    first_goal_rate: float = 0.0
    first_goal_minutes_avg: float = 0.0

    # Last Goalscorer
    last_goals: int = 0
    last_goal_rate: float = 0.0

    # Timing distribution (% par période)
    goals_0_15: int = 0
    goals_16_30: int = 0
    goals_31_45: int = 0
    goals_46_60: int = 0
    goals_61_75: int = 0
    goals_76_90: int = 0

    pct_0_15: float = 0.0
    pct_16_30: float = 0.0
    pct_31_45: float = 0.0
    pct_46_60: float = 0.0
    pct_61_75: float = 0.0
    pct_76_90: float = 0.0

    # Timing profile
    timing_profile: str = ""  # EARLY_BIRD, DIESEL, CLUTCH, CONSISTENT

    # Situation breakdown
    goals_open_play: int = 0
    goals_set_piece: int = 0
    goals_penalty: int = 0
    goals_header: int = 0

    pct_open_play: float = 0.0
    pct_set_piece: float = 0.0
    pct_penalty: float = 0.0
    pct_header: float = 0.0

    # Brace stats
    braces: int = 0  # Matchs avec 2+ buts
    brace_rate: float = 0.0

    # Home/Away
    goals_home: int = 0
    goals_away: int = 0


@dataclass
class TeamFirstGSStats:
    """Stats First Goalscorer par équipe."""
    team_name: str
    league: str

    total_matches: int = 0
    matches_scored_first: int = 0
    scored_first_rate: float = 0.0

    top_first_scorers: List[Dict] = field(default_factory=list)

    avg_first_goal_minute: float = 0.0
    first_goal_by_period: Dict[str, int] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════
# TRANSFORMER CLASS
# ═══════════════════════════════════════════════════════════════════════════

class GoalscorerTransformer:
    """Transforme les données brutes en profils buteurs."""

    def __init__(self):
        self.goals: List[GoalEvent] = []
        self.profiles: Dict[str, GoalscorerProfile] = {}
        self.team_first_gs: Dict[str, TeamFirstGSStats] = {}
        self.fbref_data: Dict[str, Dict] = {}

        self.stats = {
            "total_shots": 0,
            "total_goals": 0,
            "unique_scorers": 0,
            "matches_processed": 0,
            "first_goals": 0,
            "last_goals": 0
        }

    # ─────────────────────────────────────────────────────────────────────
    # LOAD DATA
    # ─────────────────────────────────────────────────────────────────────

    def load_understat(self) -> bool:
        """Charge les données Understat (tirs/buts)."""
        logger.info(f"Loading Understat data from {UNDERSTAT_SHOTS}")

        if not UNDERSTAT_SHOTS.exists():
            logger.error(f"File not found: {UNDERSTAT_SHOTS}")
            return False

        with open(UNDERSTAT_SHOTS, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Structure: {team_name: [shots...]}
        goals_by_match = defaultdict(list)

        for team_name, shots in data.items():
            self.stats["total_shots"] += len(shots)

            for shot in shots:
                if shot.get("result") == "Goal":
                    # Créer GoalEvent
                    minute_str = str(shot.get("minute", "0"))
                    if "+" in minute_str:
                        base, added = minute_str.split("+")
                        minute = int(base) + int(added)
                    else:
                        minute = int(float(minute_str))

                    # Déterminer période
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

                    # NOTE: team_name (dict key) = équipe qui DÉFEND (shots AGAINST)
                    # Le buteur joue pour l'AUTRE équipe
                    h_team = shot.get("h_team", "")
                    a_team = shot.get("a_team", "")

                    # Équipe du buteur (opposé de l'équipe qui défend)
                    if team_name == h_team:
                        scorer_team = a_team  # Away team scored against home
                        scorer_is_home = False
                    else:
                        scorer_team = h_team  # Home team scored against away
                        scorer_is_home = True

                    goal = GoalEvent(
                        goal_id=str(shot.get("id", "")),
                        player_id=str(shot.get("player_id", "")),
                        player_name=shot.get("player", "Unknown"),
                        team_name=scorer_team,  # Équipe du buteur
                        opponent=team_name,  # Équipe qui défendait
                        league=shot.get("league", ""),
                        match_id=str(shot.get("match_id", "")),
                        date=shot.get("date", ""),
                        minute=minute,
                        xg=float(shot.get("xG", 0)),
                        situation=shot.get("situation", "OpenPlay"),
                        shot_type=shot.get("shotType", "RightFoot"),
                        is_home=scorer_is_home,
                        home_team=h_team,
                        away_team=a_team,
                        period=period
                    )

                    self.goals.append(goal)
                    goals_by_match[goal.match_id].append(goal)

        self.stats["total_goals"] = len(self.goals)
        self.stats["matches_processed"] = len(goals_by_match)

        # Calculer first/last goal
        self._calculate_first_last_goals(goals_by_match)

        logger.info(f"  Loaded {self.stats['total_goals']} goals from {self.stats['matches_processed']} matches")
        return True

    def _calculate_first_last_goals(self, goals_by_match: Dict[str, List[GoalEvent]]):
        """Calcule is_first_goal et is_last_goal."""
        for match_id, match_goals in goals_by_match.items():
            sorted_goals = sorted(match_goals, key=lambda g: g.minute)

            for i, goal in enumerate(sorted_goals):
                goal.goal_number_in_match = i + 1
                goal.is_first_goal = (i == 0)
                goal.is_last_goal = (i == len(sorted_goals) - 1)

                if goal.is_first_goal:
                    self.stats["first_goals"] += 1
                if goal.is_last_goal:
                    self.stats["last_goals"] += 1

        logger.info(f"  First goals: {self.stats['first_goals']}, Last goals: {self.stats['last_goals']}")

    def load_fbref(self) -> bool:
        """Charge les données FBRef (stats avancées)."""
        logger.info(f"Loading FBRef data from {FBREF_PLAYERS}")

        if not FBREF_PLAYERS.exists():
            logger.error(f"File not found: {FBREF_PLAYERS}")
            return False

        with open(FBREF_PLAYERS, 'r', encoding='utf-8') as f:
            data = json.load(f)

        players = data.get("players", {})

        for player_key, player_data in players.items():
            # Extraire player_name du key ou des données
            if isinstance(player_data, dict):
                standard = player_data.get("standard", {})
                player_name = standard.get("Player", player_key)

                self.fbref_data[player_name.lower()] = {
                    "minutes": self._safe_int(standard.get("Min", 0)),
                    "goals": self._safe_int(standard.get("Gls", 0)),
                    "xg": self._safe_float(standard.get("xG", 0)),
                    "npxg": self._safe_float(standard.get("npxG", 0)),
                    "shots": self._safe_int(player_data.get("shooting", {}).get("Sh", 0)),
                    "sot": self._safe_int(player_data.get("shooting", {}).get("SoT", 0)),
                    "g_per_sh": self._safe_float(player_data.get("shooting", {}).get("G/Sh", 0)),
                    "team": standard.get("Squad", ""),
                    "league": standard.get("Comp", "")
                }

        logger.info(f"  Loaded {len(self.fbref_data)} players from FBRef")
        return True

    def _safe_int(self, val) -> int:
        try:
            if val == "" or val is None:
                return 0
            return int(float(str(val).replace(",", "")))
        except:
            return 0

    def _safe_float(self, val) -> float:
        try:
            if val == "" or val is None:
                return 0.0
            return float(str(val).replace(",", ""))
        except:
            return 0.0

    # ─────────────────────────────────────────────────────────────────────
    # BUILD PROFILES
    # ─────────────────────────────────────────────────────────────────────

    def build_profiles(self):
        """Construit les profils buteurs."""
        logger.info("Building goalscorer profiles...")

        # Grouper buts par joueur
        goals_by_player = defaultdict(list)
        for goal in self.goals:
            goals_by_player[goal.player_id].append(goal)

        # Créer profils
        for player_id, player_goals in goals_by_player.items():
            first_goal = player_goals[0]

            profile = GoalscorerProfile(
                player_id=player_id,
                player_name=first_goal.player_name,
                team_name=first_goal.team_name,
                league=first_goal.league
            )

            # Stats de base
            profile.total_goals = len(player_goals)
            profile.total_xg = sum(g.xg for g in player_goals)
            profile.matches_with_goal = len(set(g.match_id for g in player_goals))

            # First/Last goals
            profile.first_goals = sum(1 for g in player_goals if g.is_first_goal)
            profile.last_goals = sum(1 for g in player_goals if g.is_last_goal)

            if profile.total_goals > 0:
                profile.first_goal_rate = profile.first_goals / profile.total_goals
                profile.last_goal_rate = profile.last_goals / profile.total_goals

            # Minute moyenne first goal
            first_goal_minutes = [g.minute for g in player_goals if g.is_first_goal]
            if first_goal_minutes:
                profile.first_goal_minutes_avg = sum(first_goal_minutes) / len(first_goal_minutes)

            # Timing distribution
            for goal in player_goals:
                if goal.period == "0-15":
                    profile.goals_0_15 += 1
                elif goal.period == "16-30":
                    profile.goals_16_30 += 1
                elif goal.period == "31-45":
                    profile.goals_31_45 += 1
                elif goal.period == "46-60":
                    profile.goals_46_60 += 1
                elif goal.period == "61-75":
                    profile.goals_61_75 += 1
                else:
                    profile.goals_76_90 += 1

            # Percentages timing
            if profile.total_goals > 0:
                profile.pct_0_15 = profile.goals_0_15 / profile.total_goals
                profile.pct_16_30 = profile.goals_16_30 / profile.total_goals
                profile.pct_31_45 = profile.goals_31_45 / profile.total_goals
                profile.pct_46_60 = profile.goals_46_60 / profile.total_goals
                profile.pct_61_75 = profile.goals_61_75 / profile.total_goals
                profile.pct_76_90 = profile.goals_76_90 / profile.total_goals

            # Timing profile
            first_half = profile.goals_0_15 + profile.goals_16_30 + profile.goals_31_45
            second_half = profile.goals_46_60 + profile.goals_61_75 + profile.goals_76_90

            if profile.total_goals >= 3:
                if profile.pct_0_15 >= 0.3:
                    profile.timing_profile = "EARLY_BIRD"
                elif profile.pct_76_90 >= 0.3:
                    profile.timing_profile = "CLUTCH"
                elif second_half > first_half * 1.5:
                    profile.timing_profile = "DIESEL"
                else:
                    profile.timing_profile = "CONSISTENT"

            # Situation breakdown
            for goal in player_goals:
                if goal.situation == "Penalty":
                    profile.goals_penalty += 1
                elif goal.situation in ["FromCorner", "SetPiece", "DirectFreekick"]:
                    profile.goals_set_piece += 1
                else:
                    profile.goals_open_play += 1

                if goal.shot_type == "Head":
                    profile.goals_header += 1

            if profile.total_goals > 0:
                profile.pct_open_play = profile.goals_open_play / profile.total_goals
                profile.pct_set_piece = profile.goals_set_piece / profile.total_goals
                profile.pct_penalty = profile.goals_penalty / profile.total_goals
                profile.pct_header = profile.goals_header / profile.total_goals

            # Home/Away
            profile.goals_home = sum(1 for g in player_goals if g.is_home)
            profile.goals_away = profile.total_goals - profile.goals_home

            # Braces (2+ buts dans un match)
            goals_per_match = defaultdict(int)
            for goal in player_goals:
                goals_per_match[goal.match_id] += 1
            profile.braces = sum(1 for count in goals_per_match.values() if count >= 2)
            if profile.matches_with_goal > 0:
                profile.brace_rate = profile.braces / profile.matches_with_goal

            # Enrichir avec FBRef
            self._enrich_with_fbref(profile)

            self.profiles[player_id] = profile

        self.stats["unique_scorers"] = len(self.profiles)
        logger.info(f"  Built {len(self.profiles)} goalscorer profiles")

    def _enrich_with_fbref(self, profile: GoalscorerProfile):
        """Enrichit le profil avec les données FBRef."""
        # Chercher le joueur par nom (lowercase)
        player_lower = profile.player_name.lower()

        fbref = self.fbref_data.get(player_lower)
        if fbref:
            profile.minutes_played = fbref["minutes"]
            profile.shots_total = fbref["shots"]
            profile.shots_on_target = fbref["sot"]

            # Goals per 90
            if profile.minutes_played >= 90:
                profile.goals_per_90 = (profile.total_goals / profile.minutes_played) * 90
                profile.xg_per_90 = (profile.total_xg / profile.minutes_played) * 90

            # Conversion rate
            if profile.shots_total > 0:
                profile.conversion_rate = profile.total_goals / profile.shots_total

            # Overperformance
            profile.overperformance = profile.total_goals - profile.total_xg

    # ─────────────────────────────────────────────────────────────────────
    # BUILD TEAM FIRST GS STATS
    # ─────────────────────────────────────────────────────────────────────

    def build_team_stats(self):
        """Construit les stats First GS par équipe."""
        logger.info("Building team first goalscorer stats...")

        # Grouper buts par équipe et match
        team_matches = defaultdict(lambda: defaultdict(list))

        for goal in self.goals:
            team_matches[goal.team_name][goal.match_id].append(goal)

        for team_name, matches in team_matches.items():
            league = next((g.league for g in self.goals if g.team_name == team_name), "")

            stats = TeamFirstGSStats(
                team_name=team_name,
                league=league,
                total_matches=len(matches),
                first_goal_by_period={
                    "0-15": 0, "16-30": 0, "31-45": 0,
                    "46-60": 0, "61-75": 0, "76-90": 0
                }
            )

            first_scorer_count = defaultdict(int)
            first_goal_minutes = []

            for match_id, match_goals in matches.items():
                sorted_goals = sorted(match_goals, key=lambda g: g.minute)
                if sorted_goals:
                    first = sorted_goals[0]
                    if first.is_first_goal:  # Cette équipe a marqué le premier but du match
                        stats.matches_scored_first += 1
                        first_scorer_count[first.player_name] += 1
                        first_goal_minutes.append(first.minute)
                        stats.first_goal_by_period[first.period] += 1

            if stats.total_matches > 0:
                stats.scored_first_rate = stats.matches_scored_first / stats.total_matches

            if first_goal_minutes:
                stats.avg_first_goal_minute = sum(first_goal_minutes) / len(first_goal_minutes)

            # Top first scorers
            top = sorted(first_scorer_count.items(), key=lambda x: x[1], reverse=True)[:5]
            stats.top_first_scorers = [
                {"player": name, "first_goals": count, "rate": count / stats.matches_scored_first if stats.matches_scored_first > 0 else 0}
                for name, count in top
            ]

            self.team_first_gs[team_name] = stats

        logger.info(f"  Built stats for {len(self.team_first_gs)} teams")

    # ─────────────────────────────────────────────────────────────────────
    # SAVE
    # ─────────────────────────────────────────────────────────────────────

    def save_all(self):
        """Sauvegarde toutes les données."""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # 1. All goals detailed
        goals_data = [asdict(g) for g in self.goals]
        with open(GOALS_OUTPUT, 'w', encoding='utf-8') as f:
            json.dump(goals_data, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Saved {len(goals_data)} goals to {GOALS_OUTPUT}")

        # 2. Goalscorer profiles
        profiles_data = {k: asdict(v) for k, v in self.profiles.items()}
        with open(PROFILES_OUTPUT, 'w', encoding='utf-8') as f:
            json.dump(profiles_data, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Saved {len(profiles_data)} profiles to {PROFILES_OUTPUT}")

        # 3. Team first GS stats
        team_data = {k: asdict(v) for k, v in self.team_first_gs.items()}
        with open(FIRST_GS_OUTPUT, 'w', encoding='utf-8') as f:
            json.dump(team_data, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Saved {len(team_data)} team stats to {FIRST_GS_OUTPUT}")

        # 4. Summary
        top_scorers = sorted(self.profiles.values(), key=lambda p: p.total_goals, reverse=True)[:20]
        top_first = sorted(self.profiles.values(), key=lambda p: p.first_goals, reverse=True)[:10]

        summary = {
            "transformation_date": datetime.now().isoformat(),
            "season": "2025/2026",
            "sources": {
                "understat": str(UNDERSTAT_SHOTS),
                "fbref": str(FBREF_PLAYERS)
            },
            "stats": self.stats,
            "top_scorers": [
                {
                    "name": p.player_name,
                    "team": p.team_name,
                    "goals": p.total_goals,
                    "xG": round(p.total_xg, 2),
                    "goals_per_90": round(p.goals_per_90, 3),
                    "first_goals": p.first_goals,
                    "first_rate": round(p.first_goal_rate, 3)
                }
                for p in top_scorers
            ],
            "top_first_goalscorers": [
                {
                    "name": p.player_name,
                    "team": p.team_name,
                    "first_goals": p.first_goals,
                    "total_goals": p.total_goals,
                    "rate": round(p.first_goal_rate, 3),
                    "avg_minute": round(p.first_goal_minutes_avg, 1)
                }
                for p in top_first
            ]
        }

        with open(SUMMARY_OUTPUT, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Saved summary to {SUMMARY_OUTPUT}")

    # ─────────────────────────────────────────────────────────────────────
    # RUN
    # ─────────────────────────────────────────────────────────────────────

    def run(self):
        """Exécute la transformation complète."""
        logger.info("=" * 70)
        logger.info("GOALSCORER DATA TRANSFORMER - SAISON 2025/2026")
        logger.info("=" * 70)

        # Load
        if not self.load_understat():
            return False

        self.load_fbref()  # Optional enrichment

        # Build
        self.build_profiles()
        self.build_team_stats()

        # Save
        self.save_all()

        # Print summary
        logger.info("")
        logger.info("=" * 70)
        logger.info("TRANSFORMATION TERMINÉE")
        logger.info("=" * 70)
        logger.info(f"  Total buts: {self.stats['total_goals']}")
        logger.info(f"  Buteurs uniques: {self.stats['unique_scorers']}")
        logger.info(f"  First goals: {self.stats['first_goals']}")
        logger.info(f"  Matchs: {self.stats['matches_processed']}")

        return True


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    transformer = GoalscorerTransformer()
    success = transformer.run()

    if success:
        print("\n✅ Transformation réussie!")
        print(f"   Fichiers créés dans: {OUTPUT_DIR}")
    else:
        print("\n❌ Erreur de transformation")
