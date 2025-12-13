"""
DataManager V2.5 ULTIME - Quant Hedge Fund Grade
═══════════════════════════════════════════════════════════════════════════

Architecture en CASCADE avec FUSION FRANKENSTEIN:
1. PostgreSQL quantum.team_profiles (99 équipes, données temps réel)
2. JSON DNA Unified (96 équipes, données riches)
3. Imputation intelligente (moyennes de ligue)

Fonctionnalités:
- Normalisation des noms d'équipes
- Fusion multi-sources (Frankenstein Merge)
- Staleness check (fraîcheur des données)
- Data quality scoring
- Variance cross-check
- Kelly adjustment par qualité

Auteur: Mon_PS Quant Team
Version: 2.5.0
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

# Configuration logging
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

# Fichiers DNA
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
    "goalkeeper_dna": DATA_DIR / "goalkeeper_dna" / "goalkeeper_dna_v4_4_final.json",
    "team_name_mapping": QUANTUM_V2_DIR / "team_name_mapping.json",
}

# Moyennes par ligue pour imputation
LEAGUE_DEFAULTS = {
    "EPL": {
        "xg_for": 1.45, "xg_against": 1.45, "diesel_factor": 1.0,
        "over25_rate": 0.52, "btts_rate": 0.48, "clean_sheet_rate": 0.28
    },
    "La Liga": {
        "xg_for": 1.35, "xg_against": 1.35, "diesel_factor": 0.95,
        "over25_rate": 0.48, "btts_rate": 0.45, "clean_sheet_rate": 0.30
    },
    "Bundesliga": {
        "xg_for": 1.55, "xg_against": 1.55, "diesel_factor": 1.05,
        "over25_rate": 0.58, "btts_rate": 0.55, "clean_sheet_rate": 0.25
    },
    "Serie A": {
        "xg_for": 1.38, "xg_against": 1.38, "diesel_factor": 0.98,
        "over25_rate": 0.50, "btts_rate": 0.47, "clean_sheet_rate": 0.29
    },
    "Ligue 1": {
        "xg_for": 1.40, "xg_against": 1.40, "diesel_factor": 1.0,
        "over25_rate": 0.51, "btts_rate": 0.46, "clean_sheet_rate": 0.28
    },
    "DEFAULT": {
        "xg_for": 1.40, "xg_against": 1.40, "diesel_factor": 1.0,
        "over25_rate": 0.50, "btts_rate": 0.47, "clean_sheet_rate": 0.28
    }
}

# Source reliability scores
SOURCE_RELIABILITY = {
    "postgresql_quantum": 0.95,
    "json_context_dna": 0.90,
    "json_tactical": 0.85,
    "json_unified": 0.80,
    "imputed": 0.40
}

# Staleness thresholds (jours)
STALENESS_THRESHOLDS = {
    "fresh": 3,
    "acceptable": 7,
    "stale": 14,
    "obsolete": 30
}


# ═══════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class TeamData:
    """Données complètes d'une équipe - Quant Grade"""
    
    # Identité
    name: str
    canonical_name: str
    league: str = "Unknown"
    
    # xG Core (OBLIGATOIRE)
    xg_for: float = 1.40
    xg_against: float = 1.40
    xg_for_home: float = 1.50
    xg_for_away: float = 1.30
    xg_against_home: float = 1.30
    xg_against_away: float = 1.50
    
    # Rates (OBLIGATOIRE)
    over25_rate: float = 0.50
    btts_rate: float = 0.47
    clean_sheet_rate: float = 0.28
    
    # Tactical DNA
    tactical_style: str = "BALANCED"
    formation: str = "4-4-2"
    pressing_intensity: float = 0.5
    verticality: float = 0.5
    possession_avg: float = 50.0
    
    # Temporal DNA
    diesel_factor: float = 1.0  # 2H vs 1H performance
    killer_instinct: float = 0.5  # Buts 0-15 et 75-90
    clutch_factor: float = 0.5
    xg_by_period: Dict[str, float] = field(default_factory=dict)
    
    # Psyche DNA
    mentality: str = "NEUTRAL"  # PREDATOR, VOLATILE, CONSERVATIVE
    comeback_rate: float = 0.0
    panic_factor: float = 0.0
    
    # Defense DNA
    keeper_status: str = "SOLID"  # ON_FIRE, SOLID, LEAKY
    gk_save_rate: float = 0.70
    
    # Market DNA
    best_markets: List[str] = field(default_factory=list)
    avoid_markets: List[str] = field(default_factory=list)
    
    # Exploit Profiles
    vulnerabilities: List[str] = field(default_factory=list)
    exploit_paths: List[str] = field(default_factory=list)
    
    # Momentum
    form_last_5: str = "NEUTRAL"  # HOT, WARMING, NEUTRAL, COOLING, COLD
    win_streak: int = 0
    
    # Metadata Quant
    data_source: str = "unknown"
    data_sources_used: List[str] = field(default_factory=list)
    data_quality_score: float = 0.50
    last_updated: datetime = field(default_factory=datetime.now)
    is_imputed: bool = False
    imputed_fields: List[str] = field(default_factory=list)
    
    def get_adjusted_kelly_multiplier(self) -> float:
        """Multiplicateur Kelly basé sur la qualité des données"""
        base = self.data_quality_score
        
        # Pénalité si données imputées
        if self.is_imputed:
            base *= 0.7
        
        # Pénalité si données obsolètes
        days_old = (datetime.now() - self.last_updated).days
        if days_old > STALENESS_THRESHOLDS["obsolete"]:
            base *= 0.5
        elif days_old > STALENESS_THRESHOLDS["stale"]:
            base *= 0.7
        elif days_old > STALENESS_THRESHOLDS["acceptable"]:
            base *= 0.85
        
        return max(0.2, min(1.0, base))


@dataclass
class RefereeData:
    """Données arbitre pour prédictions cartons/fautes"""
    name: str
    avg_cards_per_match: float = 4.0
    avg_fouls_per_match: float = 24.0
    home_bias: float = 0.0
    strictness: str = "MODERATE"  # LENIENT, MODERATE, STRICT
    card_profile: str = "BALANCED"
    catalyst_type: str = "NEUTRAL"
    data_quality_score: float = 0.50


@dataclass 
class ScorerData:
    """Données buteur pour prédictions goals"""
    name: str
    team: str
    goals: int = 0
    xg: float = 0.0
    goals_per_90: float = 0.0
    shot_accuracy: float = 0.0
    penalty_taker: bool = False
    header_rate: float = 0.0
    timing_profile: str = "NEUTRAL"  # EARLY, LATE, CONSISTENT
    tier: str = "STANDARD"  # ELITE, CLINICAL, STANDARD, WASTEFUL


# ═══════════════════════════════════════════════════════════════════════════
# CONNECTION POOL POSTGRESQL
# ═══════════════════════════════════════════════════════════════════════════

class PostgresPool:
    """Thread-safe connection pool pour PostgreSQL"""
    
    _instance = None
    _pool = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_pool()
        return cls._instance
    
    def _initialize_pool(self):
        """Initialise le pool de connexions"""
        try:
            self._pool = pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=20,
                **DB_CONFIG
            )
            logger.info("PostgreSQL Pool initialise (2-20 connexions)")
        except Exception as e:
            logger.warning(f"PostgreSQL Pool non disponible: {e}")
            self._pool = None
    
    def get_connection(self):
        """Obtient une connexion du pool"""
        if self._pool:
            return self._pool.getconn()
        return None
    
    def release_connection(self, conn):
        """Libère une connexion vers le pool"""
        if self._pool and conn:
            self._pool.putconn(conn)
    
    def is_available(self) -> bool:
        """Vérifie si le pool est disponible"""
        return self._pool is not None


# ═══════════════════════════════════════════════════════════════════════════
# NAME NORMALIZER
# ═══════════════════════════════════════════════════════════════════════════

class TeamNameNormalizer:
    """Normalise les noms d'équipes entre différentes sources"""
    
    def __init__(self):
        self.mapping = self._load_mapping()
        self.reverse_mapping = {v: k for k, v in self.mapping.items()}
        self._cache = {}
    
    def _load_mapping(self) -> Dict[str, str]:
        """Charge le mapping des noms"""
        mapping = {}
        
        # Mapping principal
        mapping_file = DNA_FILES.get("team_name_mapping")
        if mapping_file and mapping_file.exists():
            try:
                with open(mapping_file) as f:
                    mapping = json.load(f)
                logger.info(f"Mapping noms charge: {len(mapping)} entrees")
            except Exception as e:
                logger.warning(f"Erreur chargement mapping: {e}")
        
        # Ajouter des mappings courants
        default_mappings = {
            "Man City": "Manchester City",
            "Man United": "Manchester United",
            "Man Utd": "Manchester United",
            "Nott'm Forest": "Nottingham Forest",
            "Nottm Forest": "Nottingham Forest",
            "Spurs": "Tottenham",
            "Wolves": "Wolverhampton",
            "Wolverhampton Wanderers": "Wolverhampton",
            "Brighton & Hove Albion": "Brighton",
            "West Ham United": "West Ham",
            "Newcastle United": "Newcastle",
            "Leicester City": "Leicester",
            "Leeds United": "Leeds",
            "Atletico Madrid": "Atletico Madrid",
            "Atletico": "Atletico Madrid",
            "Bayern": "Bayern Munich",
            "Bayern Munchen": "Bayern Munich",
            "Borussia Dortmund": "Dortmund",
            "RB Leipzig": "RB Leipzig",
            "Bayer Leverkusen": "Leverkusen",
            "Inter Milan": "Inter",
            "AC Milan": "Milan",
            "AS Roma": "Roma",
            "Napoli": "Napoli",
            "Paris Saint-Germain": "PSG",
            "Paris Saint Germain": "PSG",
            "Olympique Lyon": "Lyon",
            "Olympique Marseille": "Marseille",
            "AS Monaco": "Monaco",
        }
        
        for k, v in default_mappings.items():
            if k not in mapping:
                mapping[k] = v
        
        return mapping
    
    def normalize(self, name: str) -> str:
        """Normalise un nom d'equipe"""
        if not name:
            return name
        
        # Cache
        if name in self._cache:
            return self._cache[name]
        
        # Mapping direct
        if name in self.mapping:
            normalized = self.mapping[name]
            self._cache[name] = normalized
            return normalized
        
        # Deja un nom canonique
        if name in self.reverse_mapping or name in self.mapping.values():
            self._cache[name] = name
            return name
        
        # Fuzzy matching en dernier recours
        best_match = self._fuzzy_match(name)
        if best_match:
            self._cache[name] = best_match
            return best_match
        
        # Pas de match, retourner tel quel
        self._cache[name] = name
        return name
    
    def _fuzzy_match(self, name: str, threshold: float = 0.8) -> Optional[str]:
        """Trouve la meilleure correspondance fuzzy"""
        best_score = 0
        best_match = None
        
        all_names = set(self.mapping.values()) | set(self.mapping.keys())
        
        for candidate in all_names:
            score = SequenceMatcher(None, name.lower(), candidate.lower()).ratio()
            if score > best_score and score >= threshold:
                best_score = score
                # Retourner le nom canonique
                best_match = self.mapping.get(candidate, candidate)
        
        if best_match:
            logger.debug(f"Fuzzy match: '{name}' -> '{best_match}' (score: {best_score:.2f})")
        
        return best_match


# ═══════════════════════════════════════════════════════════════════════════
# DATA MANAGER V2.5 ULTIME
# ═══════════════════════════════════════════════════════════════════════════

class DataManager:
    """
    DataManager V2.5 ULTIME - Architecture Hybrid Cascade
    
    Niveaux:
    1. PostgreSQL quantum.team_profiles (temps reel, 99 equipes)
    2. JSON DNA Files (riches, 96 equipes)
    3. Imputation intelligente (moyennes de ligue)
    
    Features:
    - Frankenstein Merge (fusion multi-sources)
    - Staleness check
    - Variance cross-check
    - Data quality scoring
    """
    
    def __init__(self):
        self.db_pool = PostgresPool()
        self.normalizer = TeamNameNormalizer()
        
        # Caches
        self._team_cache: Dict[str, TeamData] = {}
        self._referee_cache: Dict[str, RefereeData] = {}
        self._json_cache: Dict[str, Any] = {}
        
        # Charger les JSON en memoire
        self._load_json_files()
        
        logger.info("DataManager V2.5 ULTIME initialise")
    
    def _load_json_files(self):
        """Charge les fichiers JSON en cache"""
        for key, path in DNA_FILES.items():
            if path.exists():
                try:
                    with open(path) as f:
                        self._json_cache[key] = json.load(f)
                    logger.debug(f"{key}: {len(self._json_cache[key])} entrees")
                except Exception as e:
                    logger.warning(f"Erreur chargement {key}: {e}")
    
    # ═══════════════════════════════════════════════════════════════════
    # METHODE PRINCIPALE: get_team_data_hybrid
    # ═══════════════════════════════════════════════════════════════════
    
    def get_team_data_hybrid(self, team_name: str) -> Optional[TeamData]:
        """
        Recupere les donnees d'une equipe avec fusion multi-sources.
        
        Cascade:
        1. PostgreSQL quantum.team_profiles
        2. JSON DNA files (fusion)
        3. Imputation intelligente
        
        Returns:
            TeamData avec toutes les donnees fusionnees
        """
        # Normaliser le nom
        canonical_name = self.normalizer.normalize(team_name)
        
        # Cache check
        if canonical_name in self._team_cache:
            cached = self._team_cache[canonical_name]
            # Verifier fraicheur du cache (30 minutes)
            if (datetime.now() - cached.last_updated).seconds < 1800:
                return cached
        
        # Initialiser TeamData vide
        team_data = TeamData(
            name=team_name,
            canonical_name=canonical_name,
            data_sources_used=[]
        )
        
        # ─────────────────────────────────────────────────────────────
        # NIVEAU 1: PostgreSQL quantum.team_profiles
        # ─────────────────────────────────────────────────────────────
        pg_data = self._get_from_postgresql(canonical_name)
        if pg_data:
            team_data = self._merge_postgresql_data(team_data, pg_data)
            team_data.data_sources_used.append("postgresql_quantum")
        
        # ─────────────────────────────────────────────────────────────
        # NIVEAU 2: JSON DNA Files (FUSION FRANKENSTEIN)
        # ─────────────────────────────────────────────────────────────
        
        # 2a. teams_context_dna.json (xG, momentum, variance)
        context_data = self._get_from_json("teams_context", canonical_name)
        if context_data:
            team_data = self._merge_context_dna(team_data, context_data)
            team_data.data_sources_used.append("json_context_dna")
        
        # 2b. fbref_tactical_profiles.json (tactical)
        tactical_data = self._get_from_json("tactical_profiles", canonical_name)
        if tactical_data:
            team_data = self._merge_tactical_dna(team_data, tactical_data)
            team_data.data_sources_used.append("json_tactical")
        
        # 2c. team_exploit_profiles.json (vulnerabilities)
        exploit_data = self._get_from_json("exploit_profiles", canonical_name)
        if exploit_data:
            team_data = self._merge_exploit_dna(team_data, exploit_data)
            team_data.data_sources_used.append("json_exploit")
        
        # 2d. gamestate_insights.json (psyche)
        gamestate_data = self._get_from_json("gamestate", canonical_name)
        if gamestate_data:
            team_data = self._merge_gamestate_dna(team_data, gamestate_data)
            team_data.data_sources_used.append("json_gamestate")
        
        # 2e. defense_dna (si existe)
        defense_data = self._get_from_json("defense_dna", canonical_name)
        if defense_data:
            team_data = self._merge_defense_dna(team_data, defense_data)
            team_data.data_sources_used.append("json_defense")
        
        # 2f. narrative_dna (fingerprints)
        narrative_data = self._get_from_json("narrative_dna", canonical_name)
        if narrative_data:
            team_data = self._merge_narrative_dna(team_data, narrative_data)
            team_data.data_sources_used.append("json_narrative")
        
        # ─────────────────────────────────────────────────────────────
        # NIVEAU 3: Imputation Intelligente
        # ─────────────────────────────────────────────────────────────
        team_data = self._apply_intelligent_imputation(team_data)
        
        # ─────────────────────────────────────────────────────────────
        # CALCUL DATA QUALITY SCORE
        # ─────────────────────────────────────────────────────────────
        team_data.data_quality_score = self._calculate_data_quality(team_data)
        team_data.data_source = team_data.data_sources_used[0] if team_data.data_sources_used else "imputed"
        team_data.last_updated = datetime.now()
        
        # Cache
        self._team_cache[canonical_name] = team_data
        
        return team_data
    
    # ═══════════════════════════════════════════════════════════════════
    # NIVEAU 1: POSTGRESQL
    # ═══════════════════════════════════════════════════════════════════
    
    def _get_from_postgresql(self, team_name: str) -> Optional[Dict]:
        """Recupere depuis quantum.team_profiles"""
        if not self.db_pool.is_available():
            return None
        
        conn = None
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT team_name, quantum_dna, tier, win_rate, total_pnl,
                       updated_at
                FROM quantum.team_profiles 
                WHERE team_name ILIKE %s OR team_name ILIKE %s
                LIMIT 1
            """, (team_name, f"%{team_name}%"))
            
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                return {
                    "team_name": row[0],
                    "quantum_dna": row[1] if isinstance(row[1], dict) else {},
                    "tier": row[2],
                    "win_rate": row[3],
                    "total_pnl": row[4],
                    "updated_at": row[5]
                }
            
        except Exception as e:
            logger.warning(f"PostgreSQL error: {e}")
        finally:
            if conn:
                self.db_pool.release_connection(conn)
        
        return None
    
    def _merge_postgresql_data(self, team_data: TeamData, pg_data: Dict) -> TeamData:
        """Fusionne les donnees PostgreSQL"""
        dna = pg_data.get("quantum_dna", {})
        
        # xG depuis context_dna ou current_season
        context = dna.get("context_dna", {})
        xg_profile = context.get("xg_profile", {})
        current = dna.get("current_season", {})
        
        if xg_profile:
            team_data.xg_for = float(xg_profile.get("xg_for_avg", team_data.xg_for))
            team_data.xg_against = float(xg_profile.get("xg_against_avg", team_data.xg_against))
        elif current:
            team_data.xg_for = float(current.get("xg_for", team_data.xg_for))
            team_data.xg_against = float(current.get("xg_against", team_data.xg_against))
        
        # Temporal DNA
        temporal = dna.get("temporal_dna", {})
        if temporal:
            team_data.diesel_factor = float(temporal.get("diesel_factor", 1.0))
            periods = temporal.get("periods", {})
            if periods:
                team_data.xg_by_period = {k: float(v) for k, v in periods.items() if isinstance(v, (int, float))}
        
        # Tactical DNA
        tactical = dna.get("tactical_dna", {})
        if tactical:
            team_data.formation = tactical.get("main_formation", team_data.formation)
            team_data.tactical_style = tactical.get("style", team_data.tactical_style)
            team_data.pressing_intensity = float(tactical.get("pressing_intensity", 0.5))
        
        # Psyche DNA
        psyche = dna.get("psyche_dna", {})
        if psyche:
            team_data.mentality = psyche.get("profile", team_data.mentality)
            team_data.killer_instinct = float(psyche.get("killer_instinct", 0.5))
        
        # Nemesis DNA
        nemesis = dna.get("nemesis_dna", {})
        if nemesis:
            team_data.keeper_status = nemesis.get("keeper_status", team_data.keeper_status)
            team_data.verticality = float(nemesis.get("verticality", 0.5))
        
        # Market DNA
        market = dna.get("market_dna", {})
        if market:
            team_data.best_markets = market.get("best_markets", [])
            team_data.avoid_markets = market.get("avoid_markets", [])
        
        # League
        team_data.league = context.get("league", dna.get("league", "Unknown"))
        
        return team_data
    
    # ═══════════════════════════════════════════════════════════════════
    # NIVEAU 2: JSON DNA FILES
    # ═══════════════════════════════════════════════════════════════════
    
    def _get_from_json(self, source_key: str, team_name: str) -> Optional[Dict]:
        """Recupere depuis un fichier JSON"""
        data = self._json_cache.get(source_key, {})
        
        if not data:
            return None
        
        # Dict avec cles = noms d'equipes
        if isinstance(data, dict):
            # Essayer plusieurs variantes
            for name_variant in [team_name, team_name.lower(), team_name.upper()]:
                if name_variant in data:
                    return data[name_variant]
            
            # Recherche case-insensitive
            for key, value in data.items():
                if key.lower() == team_name.lower():
                    return value
        
        # Liste avec objets contenant team_name
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    item_name = item.get("team_name", item.get("team", item.get("name", "")))
                    if item_name.lower() == team_name.lower():
                        return item
        
        return None
    
    def _merge_context_dna(self, team_data: TeamData, context: Dict) -> TeamData:
        """Fusionne teams_context_dna.json"""
        
        # History (xG)
        history = context.get("history", {})
        if history and team_data.xg_for == 1.40:  # Si pas deja rempli
            team_data.xg_for = float(history.get("xg", history.get("xg_90", team_data.xg_for)))
            team_data.xg_against = float(history.get("xga", history.get("xga_90", team_data.xg_against)))
        
        # Variance
        variance = context.get("variance", {})
        if variance:
            team_data.is_imputed = False  # Donnees reelles
        
        # Momentum DNA
        momentum = context.get("momentum_dna", {})
        if momentum:
            form = momentum.get("form_last_5", "")
            if "W" in str(form):
                wins = str(form).count("W")
                if wins >= 4:
                    team_data.form_last_5 = "HOT"
                elif wins >= 3:
                    team_data.form_last_5 = "WARMING"
                else:
                    team_data.form_last_5 = "NEUTRAL"
            team_data.win_streak = int(momentum.get("win_streak", 0))
        
        # Context DNA
        ctx_dna = context.get("context_dna", {})
        if ctx_dna:
            team_data.formation = ctx_dna.get("formation", team_data.formation)
        
        # Record
        record = context.get("record", {})
        if record:
            games = record.get("played", 1)
            if games > 0:
                over25_matches = record.get("over25_matches", 0)
                btts_matches = record.get("btts_matches", 0)
                if over25_matches:
                    team_data.over25_rate = over25_matches / games
                if btts_matches:
                    team_data.btts_rate = btts_matches / games
        
        return team_data
    
    def _merge_tactical_dna(self, team_data: TeamData, tactical: Dict) -> TeamData:
        """Fusionne fbref_tactical_profiles.json"""
        
        team_data.possession_avg = float(tactical.get("possession_pct", tactical.get("poss", team_data.possession_avg)))
        
        # Pressing metrics
        if "pressures" in tactical or "tackles_total" in tactical:
            pressures = float(tactical.get("pressures", 0))
            tackles = float(tactical.get("tackles_total", 0))
            team_data.pressing_intensity = min(1.0, (pressures + tackles) / 500)
        
        # Style detection
        poss = team_data.possession_avg
        if poss > 58:
            team_data.tactical_style = "POSSESSION"
        elif poss < 45:
            team_data.tactical_style = "COUNTER"
        
        # Verticality from progressive passes
        prog_passes = float(tactical.get("progressive_passes", tactical.get("prog_passes", 0)))
        if prog_passes > 600:
            team_data.verticality = 0.8
        elif prog_passes > 400:
            team_data.verticality = 0.6
        
        return team_data
    
    def _merge_exploit_dna(self, team_data: TeamData, exploit: Dict) -> TeamData:
        """Fusionne team_exploit_profiles.json"""
        
        team_data.vulnerabilities = exploit.get("vulnerabilities", [])
        team_data.exploit_paths = exploit.get("exploit_paths", [])
        team_data.best_markets = exploit.get("best_markets", team_data.best_markets)
        
        return team_data
    
    def _merge_gamestate_dna(self, team_data: TeamData, gamestate: Dict) -> TeamData:
        """Fusionne gamestate_insights.json"""
        
        # Comportement quand mene
        when_losing = gamestate.get("when_losing", gamestate.get("trailing", {}))
        if when_losing:
            comeback_rate = float(when_losing.get("comeback_rate", when_losing.get("win_rate", 0)))
            team_data.comeback_rate = comeback_rate
            if comeback_rate > 0.3:
                team_data.mentality = "PREDATOR"
        
        # Comportement quand en tete
        when_winning = gamestate.get("when_winning", gamestate.get("leading", {}))
        if when_winning:
            collapse_rate = float(when_winning.get("collapse_rate", when_winning.get("loss_rate", 0)))
            team_data.panic_factor = collapse_rate
        
        return team_data
    
    def _merge_defense_dna(self, team_data: TeamData, defense: Dict) -> TeamData:
        """Fusionne team_defense_dna_2025.json"""
        
        team_data.xg_against = float(defense.get("xga_per_90", defense.get("xga_avg", team_data.xg_against)))
        cs_pct = defense.get("cs_pct", defense.get("clean_sheet_rate", 0))
        if cs_pct:
            team_data.clean_sheet_rate = float(cs_pct) / 100 if cs_pct > 1 else float(cs_pct)
        
        # Home/Away splits
        xga_home = defense.get("xga_home", 0)
        xga_away = defense.get("xga_away", 0)
        matches_home = defense.get("matches_home", 1)
        matches_away = defense.get("matches_away", 1)
        
        if xga_home and matches_home:
            team_data.xg_against_home = float(xga_home) / float(matches_home)
        if xga_away and matches_away:
            team_data.xg_against_away = float(xga_away) / float(matches_away)
        
        return team_data
    
    def _merge_narrative_dna(self, team_data: TeamData, narrative: Dict) -> TeamData:
        """Fusionne team_narrative_dna_v3.json (fingerprints)"""
        
        # Attackers
        attackers = narrative.get("attackers", {})
        if attackers:
            dependency = float(attackers.get("dependency", 0))
            # Si forte dependance MVP, risque si absent
        
        # Defense
        defense = narrative.get("defense", {})
        if defense:
            weak_zone = defense.get("weak_zone", "")
            if weak_zone:
                team_data.vulnerabilities.append(f"WEAK_{weak_zone}")
        
        # Timing
        timing = narrative.get("timing", {})
        if timing:
            best_period = timing.get("best_period", "")
            if "2H" in str(best_period) or "76" in str(best_period):
                team_data.diesel_factor = max(team_data.diesel_factor, 1.2)
        
        return team_data
    
    # ═══════════════════════════════════════════════════════════════════
    # NIVEAU 3: IMPUTATION INTELLIGENTE
    # ═══════════════════════════════════════════════════════════════════
    
    def _apply_intelligent_imputation(self, team_data: TeamData) -> TeamData:
        """Applique des valeurs par defaut intelligentes aux champs manquants"""
        
        league = team_data.league if team_data.league != "Unknown" else "DEFAULT"
        defaults = LEAGUE_DEFAULTS.get(league, LEAGUE_DEFAULTS["DEFAULT"])
        
        # xG
        if team_data.xg_for == 1.40:
            team_data.xg_for = defaults["xg_for"]
            team_data.imputed_fields.append("xg_for")
            team_data.is_imputed = True
        
        if team_data.xg_against == 1.40:
            team_data.xg_against = defaults["xg_against"]
            team_data.imputed_fields.append("xg_against")
            team_data.is_imputed = True
        
        # Rates
        if team_data.over25_rate == 0.50:
            team_data.over25_rate = defaults["over25_rate"]
            team_data.imputed_fields.append("over25_rate")
        
        if team_data.btts_rate == 0.47:
            team_data.btts_rate = defaults["btts_rate"]
            team_data.imputed_fields.append("btts_rate")
        
        # Diesel factor
        if team_data.diesel_factor == 1.0:
            team_data.diesel_factor = defaults["diesel_factor"]
            team_data.imputed_fields.append("diesel_factor")
        
        # Home/Away splits (derivees)
        if team_data.xg_for_home == 1.50:
            team_data.xg_for_home = team_data.xg_for * 1.08  # Home advantage ~8%
            team_data.xg_for_away = team_data.xg_for * 0.92
        
        if team_data.xg_against_home == 1.30:
            team_data.xg_against_home = team_data.xg_against * 0.92
            team_data.xg_against_away = team_data.xg_against * 1.08
        
        return team_data
    
    # ═══════════════════════════════════════════════════════════════════
    # DATA QUALITY SCORING
    # ═══════════════════════════════════════════════════════════════════
    
    def _calculate_data_quality(self, team_data: TeamData) -> float:
        """Calcule un score de qualite des donnees 0.0 a 1.0"""
        
        score = 0.0
        
        # Points par source utilisee
        source_scores = {
            "postgresql_quantum": 0.30,
            "json_context_dna": 0.20,
            "json_tactical": 0.15,
            "json_exploit": 0.10,
            "json_gamestate": 0.10,
            "json_defense": 0.10,
            "json_narrative": 0.05,
        }
        
        for source in team_data.data_sources_used:
            score += source_scores.get(source, 0.05)
        
        # Penalite pour champs imputes
        imputation_penalty = len(team_data.imputed_fields) * 0.05
        score = max(0.2, score - imputation_penalty)
        
        # Cap a 1.0
        return min(1.0, score)
    
    # ═══════════════════════════════════════════════════════════════════
    # METHODES PUBLIQUES LEGACY (compatibilite)
    # ═══════════════════════════════════════════════════════════════════
    
    def get_team(self, team_name: str) -> Optional[TeamData]:
        """Alias pour get_team_data_hybrid (compatibilite)"""
        return self.get_team_data_hybrid(team_name)
    
    def get_team_xg(self, team_name: str, location: str = "overall") -> float:
        """Recupere le xG d'une equipe"""
        team = self.get_team_data_hybrid(team_name)
        if not team:
            return 1.40
        
        if location == "home":
            return team.xg_for_home
        elif location == "away":
            return team.xg_for_away
        return team.xg_for
    
    def get_team_xga(self, team_name: str, location: str = "overall") -> float:
        """Recupere le xGA d'une equipe"""
        team = self.get_team_data_hybrid(team_name)
        if not team:
            return 1.40
        
        if location == "home":
            return team.xg_against_home
        elif location == "away":
            return team.xg_against_away
        return team.xg_against
    
    def get_friction_multiplier(self, home_team: str, away_team: str) -> float:
        """Calcule le multiplicateur de friction tactique"""
        home = self.get_team_data_hybrid(home_team)
        away = self.get_team_data_hybrid(away_team)
        
        if not home or not away:
            return 1.0
        
        # Friction basee sur les styles tactiques
        friction_matrix = {
            ("POSSESSION", "COUNTER"): 1.15,
            ("COUNTER", "POSSESSION"): 1.10,
            ("POSSESSION", "POSSESSION"): 0.95,
            ("COUNTER", "COUNTER"): 1.05,
            ("BALANCED", "BALANCED"): 1.0,
        }
        
        key = (home.tactical_style, away.tactical_style)
        return friction_matrix.get(key, 1.0)
    
    def get_form_multiplier(self, team_name: str) -> float:
        """Calcule le multiplicateur de forme"""
        team = self.get_team_data_hybrid(team_name)
        if not team:
            return 1.0
        
        form_multipliers = {
            "HOT": 1.10,
            "WARMING": 1.05,
            "NEUTRAL": 1.0,
            "COOLING": 0.95,
            "COLD": 0.90
        }
        
        return form_multipliers.get(team.form_last_5, 1.0)
    
    # ═══════════════════════════════════════════════════════════════════
    # METHODES PUBLIQUES ADDITIONNELLES
    # ═══════════════════════════════════════════════════════════════════
    
    def get_referee_data(self, referee_name: str) -> Optional[RefereeData]:
        """Recupere les donnees d'un arbitre"""
        
        if referee_name in self._referee_cache:
            return self._referee_cache[referee_name]
        
        # Chercher dans le JSON
        referee_data = self._json_cache.get("referee_dna", {})
        
        ref_info = None
        if isinstance(referee_data, dict):
            ref_info = referee_data.get(referee_name)
            if not ref_info:
                # Recherche fuzzy
                for name, data in referee_data.items():
                    if referee_name.lower() in name.lower():
                        ref_info = data
                        break
        
        if ref_info:
            cards_data = ref_info.get("cards", {})
            result = RefereeData(
                name=referee_name,
                avg_cards_per_match=float(cards_data.get("avg_total", ref_info.get("avg_cards", 4.0))),
                avg_fouls_per_match=float(ref_info.get("fouls", {}).get("avg", 24.0)),
                home_bias=float(ref_info.get("bias", {}).get("home_bias", 0)),
                strictness=ref_info.get("profile", {}).get("type", "MODERATE"),
                catalyst_type=ref_info.get("catalyst", {}).get("type", "NEUTRAL"),
                data_quality_score=0.85
            )
            self._referee_cache[referee_name] = result
            return result
        
        # Valeurs par defaut
        return RefereeData(
            name=referee_name,
            data_quality_score=0.30
        )
    
    def get_scorer_data(self, player_name: str, team_name: str = None) -> Optional[ScorerData]:
        """Recupere les donnees d'un buteur"""
        
        attacker_data = self._json_cache.get("attacker_dna", [])
        
        for player in attacker_data:
            if isinstance(player, dict):
                if player.get("player", "").lower() == player_name.lower():
                    return ScorerData(
                        name=player_name,
                        team=player.get("team", team_name or "Unknown"),
                        goals=int(player.get("goals", 0)),
                        xg=float(player.get("xG", player.get("xg", 0))),
                        goals_per_90=float(player.get("goals_per_90", 0)),
                        shot_accuracy=float(player.get("shot_accuracy", 0)),
                        tier=player.get("tier", "STANDARD")
                    )
        
        return None
    
    def get_all_team_names(self) -> List[str]:
        """Retourne tous les noms d'equipes disponibles"""
        names = set()
        
        # Depuis les JSON
        for key in ["teams_context", "narrative_dna", "exploit_profiles"]:
            data = self._json_cache.get(key, {})
            if isinstance(data, dict):
                names.update(k for k in data.keys() if k not in ["metadata", "version"])
        
        return sorted(list(names))
    
    def clear_cache(self):
        """Vide les caches"""
        self._team_cache.clear()
        self._referee_cache.clear()
        logger.info("Caches vides")


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════

_data_manager_instance = None

def get_data_manager() -> DataManager:
    """Retourne l'instance singleton du DataManager"""
    global _data_manager_instance
    if _data_manager_instance is None:
        _data_manager_instance = DataManager()
    return _data_manager_instance


# ═══════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 80)
    print("TEST DataManager V2.5 ULTIME")
    print("=" * 80)
    
    dm = get_data_manager()
    
    # Test Liverpool
    print("\nTest: Liverpool")
    liverpool = dm.get_team_data_hybrid("Liverpool")
    if liverpool:
        print(f"  Name: {liverpool.canonical_name}")
        print(f"  League: {liverpool.league}")
        print(f"  xG For: {liverpool.xg_for:.2f}")
        print(f"  xG Against: {liverpool.xg_against:.2f}")
        print(f"  Diesel Factor: {liverpool.diesel_factor:.2f}")
        print(f"  Tactical Style: {liverpool.tactical_style}")
        print(f"  Formation: {liverpool.formation}")
        print(f"  Mentality: {liverpool.mentality}")
        print(f"  Data Quality: {liverpool.data_quality_score:.2f}")
        print(f"  Sources: {liverpool.data_sources_used}")
        print(f"  Imputed: {liverpool.imputed_fields}")
        print(f"  Kelly Multiplier: {liverpool.get_adjusted_kelly_multiplier():.2f}")
    
    # Test Man City (alias)
    print("\nTest: Man City (alias)")
    city = dm.get_team_data_hybrid("Man City")
    if city:
        print(f"  Canonical: {city.canonical_name}")
        print(f"  xG For: {city.xg_for:.2f}")
        print(f"  Data Quality: {city.data_quality_score:.2f}")
    
    # Test equipe inconnue
    print("\nTest: Equipe inconnue")
    unknown = dm.get_team_data_hybrid("Unknown FC")
    if unknown:
        print(f"  Name: {unknown.canonical_name}")
        print(f"  Is Imputed: {unknown.is_imputed}")
        print(f"  Data Quality: {unknown.data_quality_score:.2f}")
    
    # Test arbitre
    print("\nTest: Arbitre")
    ref = dm.get_referee_data("Anthony Taylor")
    if ref:
        print(f"  Name: {ref.name}")
        print(f"  Cards/Match: {ref.avg_cards_per_match:.1f}")
        print(f"  Strictness: {ref.strictness}")
    
    print("\nTests termines!")
