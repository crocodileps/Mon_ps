"""
DataOrchestrator - Point d'Entree UNIQUE pour les Donnees
═══════════════════════════════════════════════════════════════════════════

Architecture Hedge Fund Grade - Pattern Facade + Adapter

PRINCIPE FONDAMENTAL:
    Ce module REUTILISE les composants existants de quantum/
    Il NE DUPLIQUE PAS, il ORCHESTRE.

COMPOSANTS REUTILISES:
    1. quantum/models/dna_vectors.py (1106 lignes, 11 DNA Vectors)
    2. quantum/loaders/unified_loader.py (915 lignes, API JSON)
    3. PostgreSQL quantum.matchup_friction (3403 frictions pre-calculees)
    4. PostgreSQL quantum.team_profiles (99 equipes, 11 vectors)

INTERFACE:
    orchestrator = DataOrchestrator()
    team_dna = orchestrator.get_team_dna("Liverpool")
    friction = orchestrator.get_friction("Liverpool", "Man City")
    context = orchestrator.get_match_context("Liverpool", "Man City")

Auteur: Mon_PS Quant Team
Version: 1.0.0
Date: 13 Decembre 2025
"""

import sys
import logging
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION PATH - Ajouter les paths necessaires
# ═══════════════════════════════════════════════════════════════════════════

PROJECT_ROOT = Path("/home/Mon_ps")

# Ajouter PROJECT_ROOT pour pouvoir importer quantum.* et backend.*
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ═══════════════════════════════════════════════════════════════════════════
# IMPORTS DES COMPOSANTS EXISTANTS (LAZY LOADING)
# ═══════════════════════════════════════════════════════════════════════════

# Les imports sont faits en lazy pour eviter les problemes de path
DNA_VECTORS_AVAILABLE = False
UNIFIED_LOADER_AVAILABLE = False
_UnifiedLoader = None
_TeamDNA = None

def _load_unified_loader():
    """Charge UnifiedLoader de maniere lazy"""
    global UNIFIED_LOADER_AVAILABLE, _UnifiedLoader
    if _UnifiedLoader is not None:
        return _UnifiedLoader
    try:
        from quantum.loaders.unified_loader import UnifiedLoader
        _UnifiedLoader = UnifiedLoader
        UNIFIED_LOADER_AVAILABLE = True
        logging.info("UnifiedLoader charge avec succes")
        return UnifiedLoader
    except ImportError as e:
        logging.warning(f"unified_loader.py import failed: {e}")
        return None
    except Exception as e:
        logging.warning(f"unified_loader.py error: {e}")
        return None

def _load_dna_vectors():
    """Charge dna_vectors de maniere lazy"""
    global DNA_VECTORS_AVAILABLE, _TeamDNA
    if _TeamDNA is not None:
        return _TeamDNA
    try:
        from quantum.models.dna_vectors import TeamDNA
        _TeamDNA = TeamDNA
        DNA_VECTORS_AVAILABLE = True
        return TeamDNA
    except ImportError as e:
        logging.debug(f"dna_vectors.py non disponible: {e}")
        return None

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION POSTGRESQL
# ═══════════════════════════════════════════════════════════════════════════

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}


# ═══════════════════════════════════════════════════════════════════════════
# DATACLASSES RESULTATS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class FrictionResult:
    """Resultat de friction entre deux equipes (depuis PostgreSQL)"""
    team_a: str
    team_b: str
    friction_score: float = 50.0
    predicted_goals: float = 2.5
    btts_prob: float = 0.50
    over25_prob: float = 0.50
    chaos_potential: float = 50.0
    friction_vector: Dict = field(default_factory=dict)
    primary_markets: List[str] = field(default_factory=list)
    avoid_markets: List[str] = field(default_factory=list)
    data_source: str = "unknown"
    data_quality: float = 0.5


@dataclass
class MatchContext:
    """Contexte complet d'un match (fusion DNA + Friction)"""
    home_team: str
    away_team: str
    home_dna: Optional[Any] = None  # TeamDNA si disponible
    away_dna: Optional[Any] = None
    friction: Optional[FrictionResult] = None

    # Metriques agregees
    expected_goals: float = 2.5
    home_xg: float = 1.4
    away_xg: float = 1.1
    btts_prob: float = 0.50
    over25_prob: float = 0.50

    # Recommandations
    primary_markets: List[str] = field(default_factory=list)
    edge_markets: List[str] = field(default_factory=list)
    avoid_markets: List[str] = field(default_factory=list)

    # Quality
    data_sources_used: List[str] = field(default_factory=list)
    data_quality_score: float = 0.5


# ═══════════════════════════════════════════════════════════════════════════
# CONNECTION POOL POSTGRESQL
# ═══════════════════════════════════════════════════════════════════════════

class PostgresPool:
    """Singleton Thread-safe Connection Pool"""

    _instance = None
    _pool = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_pool()
        return cls._instance

    def _initialize_pool(self):
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
        if self._pool:
            return self._pool.getconn()
        return None

    def release_connection(self, conn):
        if self._pool and conn:
            self._pool.putconn(conn)

    def is_available(self) -> bool:
        return self._pool is not None


# ═══════════════════════════════════════════════════════════════════════════
# DATA ORCHESTRATOR - FACADE PRINCIPALE
# ═══════════════════════════════════════════════════════════════════════════

class DataOrchestrator:
    """
    Facade unifiee pour acceder a TOUTES les donnees.

    REUTILISE les composants existants:
    - unified_loader.py pour les donnees JSON
    - dna_vectors.py pour les structures
    - PostgreSQL quantum.* pour les donnees temps reel

    NE DUPLIQUE RIEN.
    """

    def __init__(self):
        """Initialise l'orchestrateur avec les composants existants"""

        # Connection Pool PostgreSQL
        self.db_pool = PostgresPool()

        # Unified Loader (existant) - LAZY LOADING
        self.unified_loader = None
        logger.debug("Attempting to load UnifiedLoader...")
        UnifiedLoaderClass = _load_unified_loader()
        logger.debug(f"UnifiedLoaderClass = {UnifiedLoaderClass}")
        if UnifiedLoaderClass:
            try:
                self.unified_loader = UnifiedLoaderClass()
                teams_count = len(self.unified_loader.get_all_teams()) if self.unified_loader else 0
                logger.info(f"UnifiedLoader connecte (quantum/loaders/) - {teams_count} equipes")
            except Exception as e:
                logger.warning(f"UnifiedLoader init failed: {e}")
                import traceback
                traceback.print_exc()
        else:
            logger.warning("UnifiedLoader non disponible")

        # Caches
        self._team_cache: Dict[str, Any] = {}
        self._friction_cache: Dict[str, FrictionResult] = {}

        # Statistiques
        self._stats = {
            "team_queries": 0,
            "friction_queries": 0,
            "cache_hits": 0,
            "pg_queries": 0,
            "json_queries": 0
        }

        logger.info("DataOrchestrator initialise - Hedge Fund Grade")

    # ═══════════════════════════════════════════════════════════════════
    # METHODE 1: get_team_dna
    # ═══════════════════════════════════════════════════════════════════

    def get_team_dna(self, team_name: str) -> Optional[Any]:
        """
        Recupere le DNA complet d'une equipe depuis TOUTES les sources.

        Cascade (ordre de priorite):
        1. Cache local
        2. TSE (team_stats_extended) - corner/card/goalscorer/timing/handicap/scorer DNA
        3. V3 (team_quantum_dna_v3) - status/signature/profile_2d/exploit/clutch/luck/roi/clv
        4. UnifiedLoader (JSON) - donnees granulaires
        5. team_profiles (fallback legacy)

        Returns:
            Dict avec toutes les donnees fusionnees
        """
        self._stats["team_queries"] += 1

        # Normaliser le nom
        canonical = self._normalize_team_name(team_name)

        # Cache check
        if canonical in self._team_cache:
            self._stats["cache_hits"] += 1
            return self._team_cache[canonical]

        team_data = {}
        sources_used = []

        # SOURCE 1: TSE (team_stats_extended) - PRIORITAIRE pour DNA specialises
        tse_data = self._get_tse_data(canonical)
        if tse_data:
            # DNA specialises depuis TSE
            team_data["corner_dna"] = tse_data.get("corner_dna")
            team_data["card_dna"] = tse_data.get("card_dna")
            team_data["goalscorer_dna"] = tse_data.get("goalscorer_dna")
            team_data["goal_timing_dna"] = tse_data.get("goal_timing_dna")
            team_data["handicap_dna"] = tse_data.get("handicap_dna")
            team_data["scorer_dna"] = tse_data.get("scorer_dna")
            team_data["tse_matches_analyzed"] = tse_data.get("matches_analyzed")
            sources_used.append("tse_team_stats_extended")

        # SOURCE 2: V3 (team_quantum_dna_v3) - Metriques enrichies
        v3_data = self._get_team_from_v3(canonical)
        if v3_data:
            # Metriques V3 (prioritaires sur legacy)
            team_data["team_name"] = v3_data.get("team_name", canonical)
            team_data["tier"] = v3_data.get("tier")
            team_data["tier_rank"] = v3_data.get("tier_rank")
            team_data["win_rate"] = v3_data.get("win_rate")
            team_data["total_pnl"] = v3_data.get("total_pnl")
            team_data["roi"] = v3_data.get("roi")
            team_data["avg_clv"] = v3_data.get("avg_clv")

            # DNA V3 specifiques
            team_data["status_2025_2026"] = v3_data.get("status_2025_2026")
            team_data["signature_v3"] = v3_data.get("signature_v3")
            team_data["profile_2d"] = v3_data.get("profile_2d")
            team_data["exploit_markets"] = v3_data.get("exploit_markets")
            team_data["avoid_markets"] = v3_data.get("avoid_markets")
            team_data["optimal_scenarios"] = v3_data.get("optimal_scenarios")

            # JSONB DNA vectors
            team_data["market_dna"] = v3_data.get("market_dna")
            team_data["context_dna"] = v3_data.get("context_dna")
            team_data["temporal_dna"] = v3_data.get("temporal_dna")
            team_data["nemesis_dna"] = v3_data.get("nemesis_dna")
            team_data["psyche_dna"] = v3_data.get("psyche_dna")
            team_data["roster_dna"] = v3_data.get("roster_dna")
            team_data["physical_dna"] = v3_data.get("physical_dna")
            team_data["luck_dna"] = v3_data.get("luck_dna")
            team_data["tactical_dna"] = v3_data.get("tactical_dna")
            team_data["chameleon_dna"] = v3_data.get("chameleon_dna")
            team_data["meta_dna"] = v3_data.get("meta_dna")
            team_data["sentiment_dna"] = v3_data.get("sentiment_dna")
            team_data["clutch_dna"] = v3_data.get("clutch_dna")
            team_data["shooting_dna"] = v3_data.get("shooting_dna")
            team_data["form_analysis"] = v3_data.get("form_analysis")
            team_data["current_season"] = v3_data.get("current_season")

            # Fallback corner/card depuis V3 si TSE n'a pas fourni
            if not team_data.get("corner_dna") and v3_data.get("corner_dna"):
                team_data["corner_dna"] = v3_data.get("corner_dna")
            if not team_data.get("card_dna") and v3_data.get("card_dna"):
                team_data["card_dna"] = v3_data.get("card_dna")

            sources_used.append("v3_team_quantum_dna")

        # SOURCE 3: UnifiedLoader (JSON) - Donnees granulaires
        if self.unified_loader:
            try:
                json_data = self.unified_loader.get_team(canonical)
                if json_data:
                    # Fusionner (JSON enrichit sans ecraser)
                    for key, value in json_data.items():
                        if key not in team_data or team_data[key] is None:
                            team_data[key] = value
                    sources_used.append("unified_loader_json")
                    self._stats["json_queries"] += 1
            except Exception as e:
                logger.debug(f"UnifiedLoader error: {e}")

        # SOURCE 4: team_profiles (fallback legacy)
        if not v3_data:
            pg_data = self._get_team_from_postgresql(canonical)
            if pg_data:
                # Enrichir avec legacy si pas de V3
                for key, value in pg_data.items():
                    if key not in team_data or team_data[key] is None:
                        team_data[key] = value
                team_data["_legacy_profiles"] = True
                sources_used.append("postgresql_team_profiles")

        # Si aucune donnee, retourner None
        if not team_data:
            return None

        # Metadata
        team_data["_sources"] = sources_used
        team_data["_data_quality"] = len(sources_used) / 4.0  # 4 sources possibles

        # CONVERSION EN TeamDNA si disponible
        TeamDNAClass = _load_dna_vectors()
        if TeamDNAClass:
            try:
                team_dna = self._convert_to_team_dna(team_data, sources_used)
                self._team_cache[canonical] = team_dna
                return team_dna
            except Exception as e:
                logger.warning(f"Conversion TeamDNA failed: {e}")

        # Cacher et retourner Dict
        self._team_cache[canonical] = team_data
        return team_data

    # ═══════════════════════════════════════════════════════════════════
    # METHODE 2: get_friction
    # ═══════════════════════════════════════════════════════════════════

    def get_friction(self, team_a: str, team_b: str) -> Optional[FrictionResult]:
        """
        Recupere la friction pre-calculee entre deux equipes.

        Source: PostgreSQL quantum.matchup_friction (3403 rows)

        Returns:
            FrictionResult avec toutes les metriques
        """
        self._stats["friction_queries"] += 1

        # Normaliser les noms
        a_canonical = self._normalize_team_name(team_a)
        b_canonical = self._normalize_team_name(team_b)

        # Cache key (ordre alphabetique pour coherence)
        cache_key = f"{min(a_canonical, b_canonical)}_{max(a_canonical, b_canonical)}"

        if cache_key in self._friction_cache:
            self._stats["cache_hits"] += 1
            return self._friction_cache[cache_key]

        # Query PostgreSQL
        friction = self._get_friction_from_postgresql(a_canonical, b_canonical)

        if friction:
            self._friction_cache[cache_key] = friction
            return friction

        # Fallback: friction par defaut
        return FrictionResult(
            team_a=a_canonical,
            team_b=b_canonical,
            data_source="default",
            data_quality=0.3
        )

    # ═══════════════════════════════════════════════════════════════════
    # METHODE 3: get_match_context
    # ═══════════════════════════════════════════════════════════════════

    def get_match_context(self, home_team: str, away_team: str) -> MatchContext:
        """
        Recupere le contexte COMPLET d'un match.

        Combine:
        - DNA des deux equipes
        - Friction pre-calculee
        - Metriques agregees

        Returns:
            MatchContext avec toutes les donnees necessaires
        """
        # Recuperer les DNA
        home_dna = self.get_team_dna(home_team)
        away_dna = self.get_team_dna(away_team)

        # Recuperer la friction
        friction = self.get_friction(home_team, away_team)

        # Construire le contexte
        context = MatchContext(
            home_team=self._normalize_team_name(home_team),
            away_team=self._normalize_team_name(away_team),
            home_dna=home_dna,
            away_dna=away_dna,
            friction=friction
        )

        # Calculer les metriques agregees
        if friction:
            context.expected_goals = friction.predicted_goals
            context.btts_prob = friction.btts_prob
            context.over25_prob = friction.over25_prob
            context.primary_markets = friction.primary_markets
            context.avoid_markets = friction.avoid_markets

        # Extraire xG des DNA si disponibles
        if home_dna:
            if isinstance(home_dna, dict):
                context.home_xg = float(home_dna.get("xg_for", home_dna.get("xg", 1.4)))
            elif hasattr(home_dna, "context") and home_dna.context:
                context.home_xg = home_dna.context.xg_for

        if away_dna:
            if isinstance(away_dna, dict):
                context.away_xg = float(away_dna.get("xg_for", away_dna.get("xg", 1.1)))
            elif hasattr(away_dna, "context") and away_dna.context:
                context.away_xg = away_dna.context.xg_for

        # Sources utilisees
        context.data_sources_used = []
        if home_dna:
            context.data_sources_used.append("home_dna")
        if away_dna:
            context.data_sources_used.append("away_dna")
        if friction and friction.data_source != "default":
            context.data_sources_used.append("friction_postgresql")

        # Quality score
        context.data_quality_score = len(context.data_sources_used) / 3.0

        return context

    # ═══════════════════════════════════════════════════════════════════
    # METHODE 4: get_referee
    # ═══════════════════════════════════════════════════════════════════

    def get_referee(self, referee_name: str) -> Optional[Dict]:
        """
        Recupere les donnees d'un arbitre via UnifiedLoader.
        """
        if self.unified_loader:
            try:
                return self.unified_loader.get_referee(referee_name)
            except Exception as e:
                logger.debug(f"Referee query failed: {e}")
        return None

    # ═══════════════════════════════════════════════════════════════════
    # METHODE 5: get_player
    # ═══════════════════════════════════════════════════════════════════

    def get_player(self, player_name: str, team: str = None) -> Optional[Dict]:
        """
        Recupere les donnees d'un joueur via UnifiedLoader.
        """
        if self.unified_loader:
            try:
                return self.unified_loader.get_player(player_name, team)
            except Exception as e:
                logger.debug(f"Player query failed: {e}")
        return None

    # ═══════════════════════════════════════════════════════════════════
    # METHODES PRIVEES - PostgreSQL
    # ═══════════════════════════════════════════════════════════════════

    def _get_team_from_postgresql(self, team_name: str) -> Optional[Dict]:
        """
        Recupere une equipe depuis quantum.team_profiles (legacy fallback)
        Utilise exact match case-insensitive, puis fallback ILIKE intelligent.
        """
        if not self.db_pool.is_available():
            return None

        conn = None
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()

            # 1. Exact match case-insensitive
            cursor.execute("""
                SELECT team_name, quantum_dna, tier, win_rate, total_pnl
                FROM quantum.team_profiles
                WHERE LOWER(team_name) = LOWER(%s)
                LIMIT 1
            """, (team_name,))

            row = cursor.fetchone()

            # 2. Fallback ILIKE intelligent si exact match echoue
            if not row:
                cursor.execute("""
                    SELECT team_name, quantum_dna, tier, win_rate, total_pnl
                    FROM quantum.team_profiles
                    WHERE team_name ILIKE %s
                """, (f"%{team_name}%",))

                results = cursor.fetchall()
                if len(results) == 1:  # Un seul match = safe
                    row = results[0]
                    logger.debug(f"Profiles fallback ILIKE: {team_name} -> {row[0]}")
                elif len(results) > 1:
                    logger.debug(f"Profiles fallback ILIKE ambiguous: {team_name} -> {len(results)} matches")

            cursor.close()

            if row:
                quantum_dna = row[1] if isinstance(row[1], dict) else {}
                return {
                    "team_name": row[0],
                    "quantum_dna": quantum_dna,
                    "tier": row[2],
                    "win_rate": float(row[3]) if row[3] else 0.0,
                    "total_pnl": float(row[4]) if row[4] else 0.0,
                    **quantum_dna  # Flatten quantum_dna
                }
        except Exception as e:
            logger.warning(f"PostgreSQL team query error: {e}")
        finally:
            if conn:
                self.db_pool.release_connection(conn)

        return None

    def _get_friction_from_postgresql(self, team_a: str, team_b: str) -> Optional[FrictionResult]:
        """Recupere la friction depuis quantum.matchup_friction"""
        if not self.db_pool.is_available():
            return None

        conn = None
        try:
            conn = self.db_pool.get_connection()
            cursor = conn.cursor()

            # Essayer les deux ordres
            cursor.execute("""
                SELECT team_a_name, team_b_name, friction_score, predicted_goals,
                       predicted_btts_prob, predicted_over25_prob, chaos_potential,
                       friction_vector
                FROM quantum.matchup_friction
                WHERE (team_a_name ILIKE %s AND team_b_name ILIKE %s)
                   OR (team_a_name ILIKE %s AND team_b_name ILIKE %s)
                LIMIT 1
            """, (f"%{team_a}%", f"%{team_b}%", f"%{team_b}%", f"%{team_a}%"))

            row = cursor.fetchone()
            cursor.close()

            if row:
                return FrictionResult(
                    team_a=row[0],
                    team_b=row[1],
                    friction_score=float(row[2] or 50),
                    predicted_goals=float(row[3] or 2.5),
                    btts_prob=float(row[4] or 0.5),
                    over25_prob=float(row[5] or 0.5),
                    chaos_potential=float(row[6] or 50),
                    friction_vector=row[7] if isinstance(row[7], dict) else {},
                    data_source="postgresql_quantum",
                    data_quality=0.95
                )
        except Exception as e:
            logger.warning(f"PostgreSQL friction query error: {e}")
        finally:
            if conn:
                self.db_pool.release_connection(conn)

        return None

    def _get_team_from_v3(self, team_name: str) -> Optional[Dict]:
        """
        Charge les donnees depuis quantum.team_quantum_dna_v3
        Table enrichie: 59 colonnes, 30 JSONB
        Prioritaire sur team_profiles (plus riche)

        Strategie de recherche:
        1. Exact match (case-insensitive)
        2. Fallback ILIKE avec ORDER BY pour determinisme
        """
        if not self.db_pool.is_available():
            return None

        conn = None
        try:
            conn = self.db_pool.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1. Exact match d'abord (case-insensitive)
                cur.execute("""
                    SELECT team_name, tier, tier_rank, win_rate, total_pnl, roi, avg_clv,
                           status_2025_2026, signature_v3, profile_2d,
                           exploit_markets, avoid_markets, optimal_scenarios,
                           market_dna, context_dna, temporal_dna, nemesis_dna,
                           psyche_dna, roster_dna, physical_dna, luck_dna,
                           tactical_dna, chameleon_dna, meta_dna, sentiment_dna,
                           clutch_dna, shooting_dna, form_analysis, current_season,
                           corner_dna, card_dna
                    FROM quantum.team_quantum_dna_v3
                    WHERE LOWER(team_name) = LOWER(%s)
                    LIMIT 1
                """, (team_name,))

                row = cur.fetchone()
                if row:
                    self._stats["pg_queries"] += 1
                    return dict(row)

                # Fallback ILIKE intelligent si exact match echoue
                cur.execute("""
                    SELECT team_name, tier, tier_rank, win_rate, total_pnl, roi, avg_clv,
                           status_2025_2026, signature_v3, profile_2d,
                           exploit_markets, avoid_markets, optimal_scenarios,
                           market_dna, context_dna, temporal_dna, nemesis_dna,
                           psyche_dna, roster_dna, physical_dna, luck_dna,
                           tactical_dna, chameleon_dna, meta_dna, sentiment_dna,
                           clutch_dna, shooting_dna, form_analysis, current_season,
                           corner_dna, card_dna
                    FROM quantum.team_quantum_dna_v3
                    WHERE team_name ILIKE %s
                """, (f"%{team_name}%",))

                results = cur.fetchall()
                if len(results) == 1:  # Un seul match = safe
                    self._stats["pg_queries"] += 1
                    logger.debug(f"V3 fallback ILIKE: {team_name} -> {results[0]['team_name']}")
                    return dict(results[0])
                elif len(results) > 1:
                    logger.debug(f"V3 fallback ILIKE ambiguous: {team_name} -> {len(results)} matches")

        except Exception as e:
            logger.warning(f"V3 lookup failed for {team_name}: {e}")
        finally:
            if conn:
                self.db_pool.release_connection(conn)

        return None

    def _get_tse_name(self, quantum_name: str) -> str:
        """
        Convertit quantum_name vers tse_name via quantum.team_name_mapping
        5 equipes ont des noms differents: AC Milan→Milan, VfB Stuttgart→Stuttgart, etc.
        Utilise exact match case-insensitive pour eviter les faux positifs.
        """
        if not self.db_pool.is_available():
            return quantum_name

        conn = None
        try:
            conn = self.db_pool.get_connection()
            with conn.cursor() as cur:
                # Exact match case-insensitive
                cur.execute("""
                    SELECT tse_name FROM quantum.team_name_mapping
                    WHERE LOWER(quantum_name) = LOWER(%s)
                    LIMIT 1
                """, (quantum_name,))
                row = cur.fetchone()
                if row and row[0]:
                    return row[0]
        except Exception as e:
            logger.debug(f"TSE name mapping failed for {quantum_name}: {e}")
        finally:
            if conn:
                self.db_pool.release_connection(conn)

        return quantum_name

    def _get_tse_data(self, team_name: str) -> Optional[Dict]:
        """
        Charge corner/card/goalscorer DNA depuis quantum.team_stats_extended
        Utilise tse_name du mapping pour conversion (5 equipes differentes)
        Pattern copie de data_hub.py

        Strategie de recherche:
        1. Exact match (case-insensitive) avec tse_name converti
        """
        if not self.db_pool.is_available():
            return None

        # Convertir via mapping si necessaire
        tse_name = self._get_tse_name(team_name)

        conn = None
        try:
            conn = self.db_pool.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Exact match (case-insensitive)
                cur.execute("""
                    SELECT team_name, corner_dna, card_dna, goalscorer_dna,
                           goal_timing_dna, handicap_dna, scorer_dna, matches_analyzed
                    FROM quantum.team_stats_extended
                    WHERE LOWER(team_name) = LOWER(%s)
                    LIMIT 1
                """, (tse_name,))

                row = cur.fetchone()
                if row:
                    self._stats["pg_queries"] += 1
                    return dict(row)

                # Fallback ILIKE intelligent si exact match echoue
                cur.execute("""
                    SELECT team_name, corner_dna, card_dna, goalscorer_dna,
                           goal_timing_dna, handicap_dna, scorer_dna, matches_analyzed
                    FROM quantum.team_stats_extended
                    WHERE team_name ILIKE %s
                """, (f"%{tse_name}%",))

                results = cur.fetchall()
                if len(results) == 1:  # Un seul match = safe
                    self._stats["pg_queries"] += 1
                    logger.debug(f"TSE fallback ILIKE: {tse_name} -> {results[0]['team_name']}")
                    return dict(results[0])
                elif len(results) > 1:
                    logger.debug(f"TSE fallback ILIKE ambiguous: {tse_name} -> {len(results)} matches")

        except Exception as e:
            logger.warning(f"TSE lookup failed for {team_name} (tse_name={tse_name}): {e}")
        finally:
            if conn:
                self.db_pool.release_connection(conn)

        return None

    # ═══════════════════════════════════════════════════════════════════
    # METHODES PRIVEES - Helpers
    # ═══════════════════════════════════════════════════════════════════

    def _normalize_team_name(self, name: str) -> str:
        """Normalise un nom d'equipe"""
        if not name:
            return name

        # Mapping courant (alias → nom officiel)
        mapping = {
            "Man City": "Manchester City",
            "Man United": "Manchester United",
            "Man Utd": "Manchester United",
            "Spurs": "Tottenham",
            "Wolves": "Wolverhampton",
            "Nott'm Forest": "Nottingham Forest",
            # Alias internationaux
            "PSG": "Paris Saint Germain",
            "Barca": "Barcelona",
            "Bayern": "Bayern Munich",
            "Dortmund": "Borussia Dortmund",
            "BVB": "Borussia Dortmund",
            "Juve": "Juventus",
            "Atleti": "Atletico Madrid",
        }

        # Utiliser UnifiedLoader si disponible
        if self.unified_loader:
            try:
                canonical = self.unified_loader.get_canonical_team_name(name)
                if canonical:
                    # Correction pour aligner avec les noms TSE/V3 en base
                    # UnifiedLoader utilise des variantes qui ne matchent pas la DB
                    db_alignment = {
                        "Paris Saint-Germain": "Paris Saint Germain",
                        "Borussia Monchengladbach": "Borussia M.Gladbach",
                    }
                    return db_alignment.get(canonical, canonical)
            except:
                pass

        return mapping.get(name, name)

    def _merge_team_data(self, pg_data: Dict, json_data: Dict) -> Dict:
        """Fusionne les donnees PostgreSQL et JSON"""
        merged = {**pg_data}

        # Ajouter les champs JSON manquants
        for key, value in json_data.items():
            if key not in merged or merged[key] is None:
                merged[key] = value

        return merged

    def _convert_to_team_dna(self, data: Dict, sources: List[str]) -> Any:
        """Convertit un Dict en TeamDNA (si dna_vectors disponible)"""
        TeamDNAClass = _load_dna_vectors()
        if not TeamDNAClass:
            data["_dna_sources"] = sources
            return data

        # Pour l'instant, retourner les donnees avec metadata
        # TODO: Implementer conversion complete vers TeamDNA dataclass
        data["_dna_sources"] = sources
        return data

    # ═══════════════════════════════════════════════════════════════════
    # METHODES UTILITAIRES
    # ═══════════════════════════════════════════════════════════════════

    def get_stats(self) -> Dict:
        """Retourne les statistiques d'utilisation"""
        return self._stats.copy()

    def clear_cache(self):
        """Vide les caches"""
        self._team_cache.clear()
        self._friction_cache.clear()
        logger.info("Caches vides")

    def get_all_team_names(self) -> List[str]:
        """Retourne tous les noms d'equipes disponibles"""
        if self.unified_loader:
            try:
                teams = self.unified_loader.get_all_teams()
                return list(teams.keys()) if teams else []
            except:
                pass
        return []


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════

_orchestrator_instance = None

def get_orchestrator() -> DataOrchestrator:
    """Retourne l'instance singleton du DataOrchestrator"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = DataOrchestrator()
    return _orchestrator_instance


# ═══════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 80)
    print("TEST DataOrchestrator - Hedge Fund Grade")
    print("=" * 80)

    orchestrator = get_orchestrator()

    # Test 1: Team DNA
    print("\nTest 1: get_team_dna('Liverpool')")
    print("-" * 60)
    liverpool = orchestrator.get_team_dna("Liverpool")
    if liverpool:
        if isinstance(liverpool, dict):
            print(f"  Team: {liverpool.get('team_name', 'Liverpool')}")
            print(f"  Tier: {liverpool.get('tier', 'N/A')}")
            print(f"  Win Rate: {liverpool.get('win_rate', 'N/A')}")
            print(f"  Sources: {liverpool.get('_sources', [])}")
        else:
            print(f"  Type: {type(liverpool).__name__}")
    else:
        print("  Aucune donnee")

    # Test 2: Friction
    print("\nTest 2: get_friction('Liverpool', 'Manchester City')")
    print("-" * 60)
    friction = orchestrator.get_friction("Liverpool", "Manchester City")
    if friction:
        print(f"  Teams: {friction.team_a} vs {friction.team_b}")
        print(f"  Friction Score: {friction.friction_score}")
        print(f"  Predicted Goals: {friction.predicted_goals}")
        print(f"  BTTS Prob: {friction.btts_prob:.1%}")
        print(f"  Over 2.5 Prob: {friction.over25_prob:.1%}")
        print(f"  Data Source: {friction.data_source}")
    else:
        print("  Aucune friction")

    # Test 3: Match Context
    print("\nTest 3: get_match_context('Arsenal', 'Chelsea')")
    print("-" * 60)
    context = orchestrator.get_match_context("Arsenal", "Chelsea")
    print(f"  Home: {context.home_team}")
    print(f"  Away: {context.away_team}")
    print(f"  Expected Goals: {context.expected_goals}")
    print(f"  BTTS: {context.btts_prob:.1%}")
    print(f"  Over 2.5: {context.over25_prob:.1%}")
    print(f"  Data Quality: {context.data_quality_score:.1%}")
    print(f"  Sources: {context.data_sources_used}")

    # Stats
    print("\nStatistiques")
    print("-" * 60)
    stats = orchestrator.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 80)
    print("TESTS TERMINES")
    print("=" * 80)
