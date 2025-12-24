"""
TeamNameResolver - Service de résolution centralisé
═══════════════════════════════════════════════════════════════════════════
Résout les noms d'équipes entre différentes sources avec cache en mémoire.

Sources supportées:
- quantum: Nom canonique (quantum.team_name_mapping.quantum_name)
- api_football: Nom API-Football (match_results format)
- historical: Nom Understat (historical_name)
- tse: Nom TSE (tse_name)

Auteur: Mon_PS Team
Date: 2025-12-24
Version: 1.0.0
═══════════════════════════════════════════════════════════════════════════
"""
import logging
from typing import Dict, Optional
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger("TeamNameResolver")


class TeamNameResolver:
    """
    Résolveur centralisé de noms d'équipes avec cache.

    Usage:
        resolver = TeamNameResolver()

        # Convertir vers API-Football
        api_name = resolver.to_api_football("Manchester United")
        # Returns: "Manchester United FC"

        # Convertir vers quantum
        quantum_name = resolver.to_quantum("Manchester United FC")
        # Returns: "Manchester United"
    """

    # Configuration DB par défaut
    DEFAULT_DB_CONFIG = {
        'host': 'localhost',
        'port': 5432,
        'dbname': 'monps_db',
        'user': 'monps_user',
        'password': 'monps_secure_password_2024'
    }

    def __init__(self, db_config: Dict = None):
        self.db_config = db_config or self.DEFAULT_DB_CONFIG
        self._conn = None

        # Caches bidirectionnels
        self._cache_quantum_to_api: Dict[str, str] = {}
        self._cache_api_to_quantum: Dict[str, str] = {}
        self._cache_loaded = False

    def _get_connection(self):
        """Obtient une connexion PostgreSQL."""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(**self.db_config)
        return self._conn

    def _load_cache(self):
        """Charge le mapping complet en cache."""
        if self._cache_loaded:
            return

        conn = self._get_connection()

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT quantum_name, api_football_name, historical_name, tse_name
                FROM quantum.team_name_mapping
                WHERE api_football_name IS NOT NULL
            """)
            rows = cur.fetchall()

        for row in rows:
            quantum = row['quantum_name']
            api_football = row['api_football_name']

            if quantum and api_football:
                # Cache bidirectionnel
                self._cache_quantum_to_api[quantum.lower()] = api_football
                self._cache_api_to_quantum[api_football.lower()] = quantum

                # Ajouter aussi les variantes
                self._cache_quantum_to_api[quantum] = api_football
                self._cache_api_to_quantum[api_football] = quantum

        self._cache_loaded = True
        logger.info(f"  Cache charge: {len(self._cache_quantum_to_api)} equipes")

    def to_api_football(self, team_name: str) -> str:
        """
        Convertit un nom d'équipe vers le format API-Football.

        Args:
            team_name: Nom quantum ou autre format

        Returns:
            Nom au format API-Football (ex: "Manchester United FC")
            Si non trouvé, retourne le nom original
        """
        self._load_cache()

        # Essayer exact match
        if team_name in self._cache_quantum_to_api:
            return self._cache_quantum_to_api[team_name]

        # Essayer lowercase
        if team_name.lower() in self._cache_quantum_to_api:
            return self._cache_quantum_to_api[team_name.lower()]

        # Fallback: ajouter " FC" comme pattern par défaut
        # Seulement si ça ne finit pas déjà par FC
        if not team_name.endswith(' FC'):
            candidate = f"{team_name} FC"
            # Vérifier si ce candidat existe dans match_results
            conn = self._get_connection()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 1 FROM match_results
                    WHERE home_team = %s OR away_team = %s
                    LIMIT 1
                """, (candidate, candidate))
                if cur.fetchone():
                    # Ajouter au cache pour prochaine fois
                    self._cache_quantum_to_api[team_name] = candidate
                    self._cache_quantum_to_api[team_name.lower()] = candidate
                    return candidate

        # Dernier recours: retourner original
        logger.warning(f"  Pas de mapping API-Football pour: {team_name}")
        return team_name

    def to_quantum(self, team_name: str) -> str:
        """
        Convertit un nom API-Football vers le format quantum canonique.

        Args:
            team_name: Nom au format API-Football

        Returns:
            Nom quantum canonique (ex: "Manchester United")
        """
        self._load_cache()

        # Essayer exact match
        if team_name in self._cache_api_to_quantum:
            return self._cache_api_to_quantum[team_name]

        # Essayer lowercase
        if team_name.lower() in self._cache_api_to_quantum:
            return self._cache_api_to_quantum[team_name.lower()]

        # Fallback: retirer " FC" si présent
        if team_name.endswith(' FC'):
            return team_name[:-3]

        return team_name

    def resolve(self, team_name: str, target_format: str = 'api_football') -> str:
        """
        Résout un nom d'équipe vers le format cible.

        Args:
            team_name: Nom d'équipe (n'importe quel format)
            target_format: 'api_football', 'quantum', 'historical', 'tse'

        Returns:
            Nom au format cible
        """
        if target_format == 'api_football':
            return self.to_api_football(team_name)
        elif target_format == 'quantum':
            return self.to_quantum(team_name)
        else:
            raise ValueError(f"Format inconnu: {target_format}")

    def close(self):
        """Ferme la connexion."""
        if self._conn and not self._conn.closed:
            self._conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# UTILITAIRES TIMEZONE
# ═══════════════════════════════════════════════════════════════════════════

def make_naive(dt: datetime) -> datetime:
    """
    Convertit un datetime en naive (sans timezone).

    Args:
        dt: datetime avec ou sans timezone

    Returns:
        datetime naive (sans timezone info)
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def safe_date_diff(dt1: datetime, dt2: datetime) -> int:
    """
    Calcule la différence en jours entre deux dates de manière sécurisée.
    Gère les timezones différentes automatiquement.

    Args:
        dt1: Premier datetime
        dt2: Second datetime

    Returns:
        Nombre de jours (dt1 - dt2)
    """
    naive1 = make_naive(dt1)
    naive2 = make_naive(dt2)
    return (naive1 - naive2).days
