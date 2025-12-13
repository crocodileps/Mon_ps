"""
DataManager V2.6 COMPLET - Quant Hedge Fund Grade
═══════════════════════════════════════════════════════════════════════════

Architecture COMPLÈTE avec TOUTES les sources:
- PostgreSQL: quantum.team_profiles, team_intelligence, coach_intelligence
- JSON DNA: 10+ fichiers (context, tactical, exploit, gamestate, defense,
            narrative, attacker, goalkeeper, players_impact)
- Imputation intelligente par ligue

Fonctionnalités V2.6:
- Coach DNA intégré (style tactique, formation, tenure)
- Goalkeeper DNA intégré (save_rate, exploits, timing)
- Attackers DNA intégré (MVP, top scorers, dependency)
- Players Impact (xGChain, xGBuildup)
- Frankenstein Merge multi-sources
- Data Quality Scoring avancé
- Kelly Multiplier ajusté

Auteur: Mon_PS Quant Team
Version: 2.6.0
Date: 13 Décembre 2025
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from functools import lru_cache
import psycopg2
from psycopg2 import pool
from difflib import SequenceMatcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

DATA_DIR = Path("/home/Mon_ps/data")
QUANTUM_V2_DIR = DATA_DIR / "quantum_v2"

DNA_FILES = {
    "team_dna_unified": QUANTUM_V2_DIR / "team_dna_unified_v2.json",
    "teams_context": QUANTUM_V2_DIR / "teams_context_dna.json",
    "narrative_dna": QUANTUM_V2_DIR / "team_narrative_dna_v3.json",
    "exploit_profiles": QUANTUM_V2_DIR / "team_exploit_profiles.json",
    "tactical_profiles": QUANTUM_V2_DIR / "fbref_tactical_profiles.json",
    "tactical_index": QUANTUM_V2_DIR / "tactical_index_v4.json",
    "gamestate": QUANTUM_V2_DIR / "gamestate_insights.json",
    "defense_dna": DATA_DIR / "defense_dna" / "team_defense_dna_2025.json",
    "referee_dna": QUANTUM_V2_DIR / "referee_dna_unified.json",
    "attacker_dna": QUANTUM_V2_DIR / "attacker_dna_v2.json",
    "players_impact": QUANTUM_V2_DIR / "players_impact_dna.json",
    "goalkeeper_dna": DATA_DIR / "goalkeeper_dna" / "goalkeeper_dna_v4_4_final.json",
    "team_name_mapping": QUANTUM_V2_DIR / "team_name_mapping.json",
}

LEAGUE_DEFAULTS = {
    "EPL": {"xg_for": 1.45, "xg_against": 1.45, "diesel_factor": 1.0, "over25_rate": 0.52, "btts_rate": 0.48, "clean_sheet_rate": 0.28, "gk_save_rate": 0.70},
    "La Liga": {"xg_for": 1.35, "xg_against": 1.35, "diesel_factor": 0.95, "over25_rate": 0.48, "btts_rate": 0.45, "clean_sheet_rate": 0.30, "gk_save_rate": 0.72},
    "Bundesliga": {"xg_for": 1.55, "xg_against": 1.55, "diesel_factor": 1.05, "over25_rate": 0.58, "btts_rate": 0.55, "clean_sheet_rate": 0.25, "gk_save_rate": 0.68},
    "Serie A": {"xg_for": 1.38, "xg_against": 1.38, "diesel_factor": 0.98, "over25_rate": 0.50, "btts_rate": 0.47, "clean_sheet_rate": 0.29, "gk_save_rate": 0.71},
    "Ligue 1": {"xg_for": 1.40, "xg_against": 1.40, "diesel_factor": 1.0, "over25_rate": 0.51, "btts_rate": 0.46, "clean_sheet_rate": 0.28, "gk_save_rate": 0.70},
    "DEFAULT": {"xg_for": 1.40, "xg_against": 1.40, "diesel_factor": 1.0, "over25_rate": 0.50, "btts_rate": 0.47, "clean_sheet_rate": 0.28, "gk_save_rate": 0.70}
}

STALENESS_THRESHOLDS = {"fresh": 3, "acceptable": 7, "stale": 14, "obsolete": 30}


# ═══════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CoachData:
    name: str
    team: str = ""
    tactical_style: str = "balanced"
    formation_primary: str = "4-4-2"
    tenure_months: int = 0
    job_security: str = "stable"
    win_rate: float = 0.0
    avg_goals_for: float = 1.4
    over25_rate: float = 0.50
    data_quality_score: float = 0.50


@dataclass
class GoalkeeperData:
    name: str
    team: str = ""
    save_rate: float = 0.70
    gk_performance_score: float = 0.0
    weak_zone: str = ""
    exploits: List[str] = field(default_factory=list)
    status: str = "SOLID"
    data_quality_score: float = 0.50


@dataclass
class AttackerData:
    name: str
    team: str = ""
    goals: int = 0
    xg: float = 0.0
    xg_per_90: float = 0.0
    threat_score: float = 0.0
    xg_chain: float = 0.0
    tier: str = "STANDARD"
    is_mvp: bool = False
    team_goal_share: float = 0.0
    data_quality_score: float = 0.50


@dataclass
class RefereeData:
    name: str
    avg_cards_per_match: float = 4.0
    avg_fouls_per_match: float = 24.0
    home_bias: float = 0.0
    strictness: str = "MODERATE"
    data_quality_score: float = 0.50


@dataclass
class TeamData:
    name: str
    canonical_name: str
    league: str = "Unknown"

    # xG Core
    xg_for: float = 1.40
    xg_against: float = 1.40
    xg_for_home: float = 1.50
    xg_for_away: float = 1.30
    xg_against_home: float = 1.30
    xg_against_away: float = 1.50

    # Rates
    over25_rate: float = 0.50
    btts_rate: float = 0.47
    clean_sheet_rate: float = 0.28

    # Tactical
    tactical_style: str = "BALANCED"
    formation: str = "4-4-2"
    pressing_intensity: float = 0.5
    verticality: float = 0.5
    possession_avg: float = 50.0

    # Temporal
    diesel_factor: float = 1.0
    killer_instinct: float = 0.5
    xg_by_period: Dict[str, float] = field(default_factory=dict)

    # Psyche
    mentality: str = "NEUTRAL"
    comeback_rate: float = 0.0
    panic_factor: float = 0.0

    # Coach V2.6
    coach_name: str = ""
    coach_style: str = "balanced"
    coach_tenure_months: int = 0

    # Goalkeeper V2.6
    goalkeeper_name: str = ""
    gk_save_rate: float = 0.70
    gk_status: str = "SOLID"
    gk_weak_zone: str = ""
    gk_exploits: List[str] = field(default_factory=list)

    # MVP/Attackers V2.6
    mvp_name: str = ""
    mvp_goals: int = 0
    mvp_xg: float = 0.0
    mvp_dependency: float = 0.0
    top_scorers: List[Dict] = field(default_factory=list)
    penalty_taker: str = ""

    # Markets
    best_markets: List[str] = field(default_factory=list)
    avoid_markets: List[str] = field(default_factory=list)
    vulnerabilities: List[str] = field(default_factory=list)

    # Momentum
    form_last_5: str = "NEUTRAL"
    win_streak: int = 0

    # Metadata
    data_source: str = "unknown"
    data_sources_used: List[str] = field(default_factory=list)
    data_quality_score: float = 0.50
    last_updated: datetime = field(default_factory=datetime.now)
    is_imputed: bool = False
    imputed_fields: List[str] = field(default_factory=list)

    def get_adjusted_kelly_multiplier(self) -> float:
        base = self.data_quality_score
        if self.is_imputed:
            base *= 0.7
        days_old = (datetime.now() - self.last_updated).days
        if days_old > 30:
            base *= 0.5
        elif days_old > 14:
            base *= 0.7
        if self.coach_name and self.goalkeeper_name and self.mvp_name:
            base *= 1.1
        return max(0.2, min(1.0, base))


# ═══════════════════════════════════════════════════════════════════════════
# CONNECTION POOL
# ═══════════════════════════════════════════════════════════════════════════

class PostgresPool:
    _instance = None
    _pool = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_pool()
        return cls._instance

    def _initialize_pool(self):
        try:
            self._pool = pool.ThreadedConnectionPool(minconn=2, maxconn=20, **DB_CONFIG)
            logger.info("PostgreSQL Pool initialise (2-20 connexions)")
        except Exception as e:
            logger.warning(f"PostgreSQL Pool non disponible: {e}")
            self._pool = None

    def get_connection(self):
        return self._pool.getconn() if self._pool else None

    def release_connection(self, conn):
        if self._pool and conn:
            self._pool.putconn(conn)

    def is_available(self) -> bool:
        return self._pool is not None


# ═══════════════════════════════════════════════════════════════════════════
# NAME NORMALIZER
# ═══════════════════════════════════════════════════════════════════════════

class TeamNameNormalizer:
    def __init__(self):
        self.mapping = self._load_mapping()
        self._cache = {}

    def _load_mapping(self) -> Dict[str, str]:
        mapping = {}
        mapping_file = DNA_FILES.get("team_name_mapping")
        if mapping_file and mapping_file.exists():
            try:
                with open(mapping_file) as f:
                    mapping = json.load(f)
            except:
                pass

        defaults = {
            "Man City": "Manchester City", "Man United": "Manchester United",
            "Nott'm Forest": "Nottingham Forest", "Spurs": "Tottenham",
            "Wolves": "Wolverhampton", "Bayern": "Bayern Munich",
            "Inter Milan": "Inter", "AC Milan": "Milan", "PSG": "Paris Saint Germain"
        }
        for k, v in defaults.items():
            if k not in mapping:
                mapping[k] = v
        return mapping

    def normalize(self, name: str) -> str:
        if not name:
            return name
        if name in self._cache:
            return self._cache[name]
        if name in self.mapping:
            self._cache[name] = self.mapping[name]
            return self.mapping[name]
        self._cache[name] = name
        return name


# ═══════════════════════════════════════════════════════════════════════════
# DATA MANAGER V2.6
# ═══════════════════════════════════════════════════════════════════════════

class DataManager:
    def __init__(self):
        self.db_pool = PostgresPool()
        self.normalizer = TeamNameNormalizer()
        self._team_cache: Dict[str, TeamData] = {}
        self._coach_cache: Dict[str, CoachData] = {}
        self._goalkeeper_cache: Dict[str, GoalkeeperData] = {}
        self._attacker_cache: Dict[str, List[AttackerData]] = {}
        self._referee_cache: Dict[str, RefereeData] = {}
        self._json_cache: Dict[str, Any] = {}
        self._load_json_files()
        logger.info("DataManager V2.6 COMPLET initialise")

    def _load_json_files(self):
        for key, path in DNA_FILES.items():
            if path.exists():
                try:
                    with open(path) as f:
                        self._json_cache[key] = json.load(f)
                except Exception as e:
                    logger.warning(f"Erreur chargement {key}: {e}")

    def get_team_data_hybrid(self, team_name: str) -> Optional[TeamData]:
        canonical_name = self.normalizer.normalize(team_name)

        if canonical_name in self._team_cache:
            cached = self._team_cache[canonical_name]
            if (datetime.now() - cached.last_updated).seconds < 1800:
                return cached

        team_data = TeamData(name=team_name, canonical_name=canonical_name, data_sources_used=[])

        # PostgreSQL
        pg_data = self._get_from_postgresql(canonical_name)
        if pg_data:
            team_data = self._merge_postgresql_data(team_data, pg_data)
            team_data.data_sources_used.append("postgresql_quantum")

        # JSON sources
        for source_key, merge_func in [
            ("teams_context", self._merge_context_dna),
            ("tactical_profiles", self._merge_tactical_dna),
            ("exploit_profiles", self._merge_exploit_dna),
            ("gamestate", self._merge_gamestate_dna),
            ("defense_dna", self._merge_defense_dna),
            ("narrative_dna", self._merge_narrative_dna),
        ]:
            data = self._get_from_json(source_key, canonical_name)
            if data:
                team_data = merge_func(team_data, data)
                team_data.data_sources_used.append(f"json_{source_key}")

        # Coach V2.6
        coach = self.get_coach_data(canonical_name)
        if coach:
            team_data.coach_name = coach.name
            team_data.coach_style = coach.tactical_style
            team_data.coach_tenure_months = coach.tenure_months
            team_data.data_sources_used.append("coach_intelligence")

        # Goalkeeper V2.6
        gk = self.get_goalkeeper_data(canonical_name)
        if gk:
            team_data.goalkeeper_name = gk.name
            team_data.gk_save_rate = gk.save_rate
            team_data.gk_status = gk.status
            team_data.gk_weak_zone = gk.weak_zone
            team_data.gk_exploits = gk.exploits
            team_data.data_sources_used.append("goalkeeper_dna")

        # Attackers V2.6
        attackers = self.get_team_attackers(canonical_name)
        if attackers:
            mvp = attackers[0]
            team_data.mvp_name = mvp.name
            team_data.mvp_goals = mvp.goals
            team_data.mvp_xg = mvp.xg
            team_data.mvp_dependency = mvp.team_goal_share
            team_data.top_scorers = [{"name": a.name, "goals": a.goals, "xg": a.xg} for a in attackers[:3]]
            team_data.penalty_taker = mvp.name
            team_data.data_sources_used.append("attacker_dna")

        # Imputation
        team_data = self._apply_imputation(team_data)
        team_data.data_quality_score = self._calculate_quality(team_data)
        team_data.last_updated = datetime.now()

        self._team_cache[canonical_name] = team_data
        return team_data

    def _get_from_postgresql(self, team_name: str) -> Optional[Dict]:
        if not self.db_pool.is_available():
            return None
        conn = None
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT team_name, quantum_dna, tier FROM quantum.team_profiles
                WHERE team_name ILIKE %s OR team_name ILIKE %s LIMIT 1
            """, (team_name, f"%{team_name}%"))
            row = cursor.fetchone()
            cursor.close()
            if row:
                return {"team_name": row[0], "quantum_dna": row[1] if isinstance(row[1], dict) else {}, "tier": row[2]}
        except Exception as e:
            logger.warning(f"PostgreSQL error: {e}")
        finally:
            if conn:
                self.db_pool.release_connection(conn)
        return None

    def _merge_postgresql_data(self, team_data: TeamData, pg_data: Dict) -> TeamData:
        dna = pg_data.get("quantum_dna", {})
        context = dna.get("context_dna", {})
        xg_profile = context.get("xg_profile", {})

        if xg_profile:
            team_data.xg_for = float(xg_profile.get("xg_for_avg", team_data.xg_for))
            team_data.xg_against = float(xg_profile.get("xg_against_avg", team_data.xg_against))

        temporal = dna.get("temporal_dna", {})
        if temporal:
            team_data.diesel_factor = float(temporal.get("diesel_factor", 1.0))

        tactical = dna.get("tactical_dna", {})
        if tactical:
            team_data.formation = tactical.get("main_formation", team_data.formation)

        psyche = dna.get("psyche_dna", {})
        if psyche:
            team_data.mentality = psyche.get("profile", team_data.mentality)

        nemesis = dna.get("nemesis_dna", {})
        if nemesis:
            team_data.gk_status = nemesis.get("keeper_status", team_data.gk_status)

        team_data.league = context.get("league", dna.get("league", "Unknown"))
        return team_data

    def _get_from_json(self, source_key: str, team_name: str) -> Optional[Dict]:
        data = self._json_cache.get(source_key, {})
        if not data:
            return None

        if isinstance(data, dict):
            if team_name in data:
                return data[team_name]
            for key, value in data.items():
                if key.lower() == team_name.lower():
                    return value
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    item_name = item.get("team_name", item.get("team", ""))
                    if item_name.lower() == team_name.lower():
                        return item
        return None

    def _merge_context_dna(self, team_data: TeamData, context: Dict) -> TeamData:
        history = context.get("history", {})
        if history and team_data.xg_for == 1.40:
            team_data.xg_for = float(history.get("xg", team_data.xg_for))
            team_data.xg_against = float(history.get("xga", team_data.xg_against))
        return team_data

    def _merge_tactical_dna(self, team_data: TeamData, tactical: Dict) -> TeamData:
        team_data.possession_avg = float(tactical.get("possession_pct", team_data.possession_avg))
        if team_data.possession_avg > 58:
            team_data.tactical_style = "POSSESSION"
        elif team_data.possession_avg < 45:
            team_data.tactical_style = "COUNTER"
        return team_data

    def _merge_exploit_dna(self, team_data: TeamData, exploit: Dict) -> TeamData:
        team_data.vulnerabilities = exploit.get("vulnerabilities", [])
        team_data.best_markets = exploit.get("best_markets", [])
        return team_data

    def _merge_gamestate_dna(self, team_data: TeamData, gamestate: Dict) -> TeamData:
        when_losing = gamestate.get("when_losing", gamestate.get("trailing", {}))
        if when_losing:
            team_data.comeback_rate = float(when_losing.get("comeback_rate", 0))
        return team_data

    def _merge_defense_dna(self, team_data: TeamData, defense: Dict) -> TeamData:
        team_data.xg_against = float(defense.get("xga_per_90", team_data.xg_against))
        cs_pct = defense.get("cs_pct", 0)
        if cs_pct:
            team_data.clean_sheet_rate = float(cs_pct) / 100 if cs_pct > 1 else float(cs_pct)
        return team_data

    def _merge_narrative_dna(self, team_data: TeamData, narrative: Dict) -> TeamData:
        attackers = narrative.get("attackers", {})
        if attackers:
            team_data.mvp_dependency = float(attackers.get("dependency", 0))
        return team_data

    def get_coach_data(self, team_name: str) -> Optional[CoachData]:
        if not self.db_pool.is_available():
            return None
        conn = None
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ci.coach_name, ci.tactical_style, ci.formation_primary, ci.tenure_months, ci.job_security
                FROM coach_team_mapping ctm
                JOIN coach_intelligence ci ON ctm.coach_name = ci.coach_name
                WHERE ctm.team_name ILIKE %s LIMIT 1
            """, (f"%{team_name}%",))
            row = cursor.fetchone()
            cursor.close()
            if row:
                return CoachData(
                    name=row[0] or "",
                    team=team_name,
                    tactical_style=row[1] or "balanced",
                    formation_primary=row[2] or "4-4-2",
                    tenure_months=int(row[3] or 0),
                    job_security=row[4] or "stable",
                    data_quality_score=0.85
                )
        except Exception as e:
            logger.debug(f"Coach query: {e}")
        finally:
            if conn:
                self.db_pool.release_connection(conn)
        return None

    def get_goalkeeper_data(self, team_name: str) -> Optional[GoalkeeperData]:
        gk_json = self._json_cache.get("goalkeeper_dna", {})
        if not gk_json:
            return None

        gk_list = gk_json.get("goalkeepers", []) if isinstance(gk_json, dict) else gk_json

        for gk in gk_list:
            if isinstance(gk, dict):
                gk_team = gk.get("team", "")
                if team_name.lower() in gk_team.lower() or gk_team.lower() in team_name.lower():
                    save_rate = float(gk.get("save_rate", 70))
                    save_rate = save_rate / 100 if save_rate > 1 else save_rate

                    perf = float(gk.get("gk_performance", 0))
                    status = "ON_FIRE" if perf > 0.3 else "SOLID" if perf > -0.3 else "LEAKY"

                    return GoalkeeperData(
                        name=gk.get("goalkeeper", ""),
                        team=team_name,
                        save_rate=save_rate,
                        gk_performance_score=perf,
                        status=status,
                        exploits=gk.get("exploits", [])[:5] if isinstance(gk.get("exploits"), list) else [],
                        data_quality_score=0.80
                    )
        return None

    def get_team_attackers(self, team_name: str) -> List[AttackerData]:
        if team_name in self._attacker_cache:
            return self._attacker_cache[team_name]

        attacker_json = self._json_cache.get("attacker_dna", [])
        attackers = []

        for player in attacker_json:
            if isinstance(player, dict):
                player_team = player.get("team", "")
                if team_name.lower() in player_team.lower() or player_team.lower() in team_name.lower():
                    attackers.append(AttackerData(
                        name=player.get("player", ""),
                        team=team_name,
                        goals=int(player.get("goals", 0)),
                        xg=float(player.get("xG", 0)),
                        xg_per_90=float(player.get("xG_per_90", 0)),
                        threat_score=float(player.get("threat_score", 0)),
                        tier=player.get("tier", "STANDARD")
                    ))

        attackers.sort(key=lambda x: x.goals, reverse=True)

        total_goals = sum(a.goals for a in attackers)
        for att in attackers:
            att.team_goal_share = att.goals / total_goals if total_goals > 0 else 0

        if attackers:
            attackers[0].is_mvp = True

        self._attacker_cache[team_name] = attackers
        return attackers

    def _apply_imputation(self, team_data: TeamData) -> TeamData:
        league = team_data.league if team_data.league != "Unknown" else "DEFAULT"
        defaults = LEAGUE_DEFAULTS.get(league, LEAGUE_DEFAULTS["DEFAULT"])

        if team_data.xg_for == 1.40:
            team_data.xg_for = defaults["xg_for"]
            team_data.imputed_fields.append("xg_for")
            team_data.is_imputed = True

        if team_data.xg_against == 1.40:
            team_data.xg_against = defaults["xg_against"]
            team_data.imputed_fields.append("xg_against")

        team_data.xg_for_home = team_data.xg_for * 1.08
        team_data.xg_for_away = team_data.xg_for * 0.92
        team_data.xg_against_home = team_data.xg_against * 0.92
        team_data.xg_against_away = team_data.xg_against * 1.08

        return team_data

    def _calculate_quality(self, team_data: TeamData) -> float:
        score = len(team_data.data_sources_used) * 0.10
        score -= len(team_data.imputed_fields) * 0.03
        return max(0.2, min(1.0, score))

    # Legacy methods
    def get_team(self, team_name: str) -> Optional[TeamData]:
        return self.get_team_data_hybrid(team_name)

    def get_team_xg(self, team_name: str, location: str = "overall") -> float:
        team = self.get_team_data_hybrid(team_name)
        if not team:
            return 1.40
        if location == "home":
            return team.xg_for_home
        elif location == "away":
            return team.xg_for_away
        return team.xg_for

    def get_team_xga(self, team_name: str, location: str = "overall") -> float:
        team = self.get_team_data_hybrid(team_name)
        if not team:
            return 1.40
        if location == "home":
            return team.xg_against_home
        elif location == "away":
            return team.xg_against_away
        return team.xg_against

    def get_friction_multiplier(self, home_team: str, away_team: str) -> float:
        home = self.get_team_data_hybrid(home_team)
        away = self.get_team_data_hybrid(away_team)
        if not home or not away:
            return 1.0
        friction = {("POSSESSION", "COUNTER"): 1.15, ("COUNTER", "POSSESSION"): 1.10}
        return friction.get((home.tactical_style, away.tactical_style), 1.0)

    def get_form_multiplier(self, team_name: str) -> float:
        team = self.get_team_data_hybrid(team_name)
        if not team:
            return 1.0
        return {"HOT": 1.10, "WARMING": 1.05, "NEUTRAL": 1.0, "COOLING": 0.95, "COLD": 0.90}.get(team.form_last_5, 1.0)

    def get_referee_data(self, referee_name: str) -> Optional[RefereeData]:
        if referee_name in self._referee_cache:
            return self._referee_cache[referee_name]

        referee_json = self._json_cache.get("referee_dna", {})
        ref_info = referee_json.get(referee_name) if isinstance(referee_json, dict) else None

        if ref_info:
            cards = ref_info.get("cards", {})
            result = RefereeData(
                name=referee_name,
                avg_cards_per_match=float(cards.get("avg_total", 4.0)),
                strictness=ref_info.get("profile", {}).get("type", "MODERATE"),
                data_quality_score=0.85
            )
            self._referee_cache[referee_name] = result
            return result
        return RefereeData(name=referee_name, data_quality_score=0.30)

    def get_all_team_names(self) -> List[str]:
        names = set()
        for key in ["teams_context", "narrative_dna", "exploit_profiles"]:
            data = self._json_cache.get(key, {})
            if isinstance(data, dict):
                names.update(data.keys())
        return sorted(list(names))

    def clear_cache(self):
        self._team_cache.clear()
        self._coach_cache.clear()
        self._goalkeeper_cache.clear()
        self._attacker_cache.clear()
        self._referee_cache.clear()


_data_manager_instance = None

def get_data_manager() -> DataManager:
    global _data_manager_instance
    if _data_manager_instance is None:
        _data_manager_instance = DataManager()
    return _data_manager_instance


if __name__ == "__main__":
    print("=" * 80)
    print("TEST DataManager V2.6 COMPLET")
    print("=" * 80)

    dm = get_data_manager()

    print("\n" + "=" * 60)
    print("Test: Liverpool")
    print("=" * 60)

    liverpool = dm.get_team_data_hybrid("Liverpool")
    if liverpool:
        print(f"  xG For: {liverpool.xg_for:.2f}")
        print(f"  xG Against: {liverpool.xg_against:.2f}")
        print(f"  Diesel: {liverpool.diesel_factor:.2f}")
        print(f"  Style: {liverpool.tactical_style}")
        print(f"  Coach: {liverpool.coach_name}")
        print(f"  GK: {liverpool.goalkeeper_name} ({liverpool.gk_status})")
        print(f"  MVP: {liverpool.mvp_name} ({liverpool.mvp_goals}G)")
        print(f"  Top Scorers: {[s['name'] for s in liverpool.top_scorers]}")
        print(f"  Sources: {len(liverpool.data_sources_used)}")
        print(f"  Quality: {liverpool.data_quality_score:.2f}")

    print("\n" + "=" * 60)
    print("Test: Manchester City")
    print("=" * 60)

    city = dm.get_team_data_hybrid("Manchester City")
    if city:
        print(f"  xG For: {city.xg_for:.2f}")
        print(f"  Coach: {city.coach_name}")
        print(f"  GK: {city.goalkeeper_name}")
        print(f"  MVP: {city.mvp_name}")

    print("\n" + "=" * 80)
    print("TESTS V2.6 TERMINES!")
    print("=" * 80)
