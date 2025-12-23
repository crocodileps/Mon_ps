"""
THE QUANTUM SOVEREIGN V3.8 - CHECKPOINT MANAGER
Gestion de l'idempotence - Sauvegarde/Restauration d'état.
Créé le: 24 Décembre 2025

Analogie: Comme la sauvegarde automatique dans un jeu vidéo.
Si le système crash, on reprend là où on s'était arrêté.

Table SQL utilisée: processing_checkpoints
- match_id (PK)
- current_node (dernier node complété)
- state_snapshot (JSONB)
- started_at, last_updated
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger("quantum_sovereign.checkpoint")


class CheckpointManager:
    """
    Gère les checkpoints pour l'idempotence.

    Idempotence = Si le système crash au milieu d'une analyse,
    on peut reprendre exactement là où on s'était arrêté.

    Flux:
    1. Match détecté → save_checkpoint(node=0)
    2. Node 0 terminé → save_checkpoint(node=1)
    3. Node 1 terminé → save_checkpoint(node=2)
    4. CRASH!
    5. Système redémarre → load_checkpoint() → Reprend à node 2
    """

    def __init__(self, db_connection=None):
        """
        Args:
            db_connection: Connexion PostgreSQL (None = lazy loading)
        """
        self._conn = db_connection

    @property
    def conn(self):
        """Lazy loading de la connexion DB"""
        if self._conn is None:
            self._conn = self._get_db_connection()
        return self._conn

    def _get_db_connection(self):
        """Crée une connexion à PostgreSQL"""
        import psycopg2
        from ..config import POSTGRES_CONFIG

        return psycopg2.connect(
            host=POSTGRES_CONFIG["host"],
            port=POSTGRES_CONFIG["port"],
            database=POSTGRES_CONFIG["database"],
            user=POSTGRES_CONFIG["user"],
            password=POSTGRES_CONFIG["password"]
        )

    def save_checkpoint(self, match_id: str, node_completed: int, state: Dict[str, Any]) -> bool:
        """
        Sauvegarde l'état après chaque Node complété.

        Args:
            match_id: Identifiant unique du match
            node_completed: Numéro du dernier node terminé (0, 1, 2, ...)
            state: L'état complet (MatchState) à sauvegarder

        Returns:
            True si sauvegarde réussie, False sinon
        """
        try:
            # Sérialiser le state en JSON
            state_json = self._serialize_state(state)

            query = """
            INSERT INTO processing_checkpoints
                (match_id, current_node, state_snapshot, started_at, last_updated)
            VALUES
                (%s, %s, %s, NOW(), NOW())
            ON CONFLICT (match_id) DO UPDATE SET
                current_node = EXCLUDED.current_node,
                state_snapshot = EXCLUDED.state_snapshot,
                last_updated = NOW()
            """

            with self.conn.cursor() as cur:
                cur.execute(query, (match_id, node_completed, state_json))
                self.conn.commit()

            logger.debug(f"Checkpoint saved: {match_id} @ node {node_completed}")
            return True

        except Exception as e:
            logger.error(f"Failed to save checkpoint for {match_id}: {e}")
            self.conn.rollback()
            return False

    def load_checkpoint(self, match_id: str) -> Optional[Dict[str, Any]]:
        """
        Charge un checkpoint existant.

        Args:
            match_id: Identifiant unique du match

        Returns:
            Le state sauvegardé ou None si pas de checkpoint
        """
        try:
            query = """
            SELECT current_node, state_snapshot, started_at, last_updated
            FROM processing_checkpoints
            WHERE match_id = %s
            """

            with self.conn.cursor() as cur:
                cur.execute(query, (match_id,))
                row = cur.fetchone()

            if row is None:
                logger.debug(f"No checkpoint found for {match_id}")
                return None

            current_node, state_json, started_at, last_updated = row
            state = self._deserialize_state(state_json)

            logger.info(
                f"Checkpoint loaded: {match_id} @ node {current_node} "
                f"(last updated: {last_updated})"
            )

            return {
                "current_node": current_node,
                "state": state,
                "started_at": started_at,
                "last_updated": last_updated
            }

        except Exception as e:
            logger.error(f"Failed to load checkpoint for {match_id}: {e}")
            return None

    def get_completed_node(self, match_id: str) -> int:
        """
        Retourne le dernier Node complété pour ce match.

        Args:
            match_id: Identifiant unique du match

        Returns:
            Numéro du dernier node complété, -1 si pas de checkpoint
        """
        try:
            query = """
            SELECT current_node FROM processing_checkpoints WHERE match_id = %s
            """

            with self.conn.cursor() as cur:
                cur.execute(query, (match_id,))
                row = cur.fetchone()

            if row is None:
                return -1

            return row[0]

        except Exception as e:
            logger.error(f"Failed to get completed node for {match_id}: {e}")
            return -1

    def clear_checkpoint(self, match_id: str) -> bool:
        """
        Supprime le checkpoint (traitement terminé avec succès).

        Args:
            match_id: Identifiant unique du match

        Returns:
            True si suppression réussie
        """
        try:
            query = "DELETE FROM processing_checkpoints WHERE match_id = %s"

            with self.conn.cursor() as cur:
                cur.execute(query, (match_id,))
                deleted = cur.rowcount
                self.conn.commit()

            if deleted > 0:
                logger.debug(f"Checkpoint cleared for {match_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to clear checkpoint for {match_id}: {e}")
            self.conn.rollback()
            return False

    def get_incomplete_matches(self) -> list:
        """
        Retourne la liste des matchs avec des checkpoints non terminés.
        Utile pour reprendre les analyses après un restart.

        Returns:
            Liste de dicts {match_id, current_node, last_updated}
        """
        try:
            query = """
            SELECT match_id, current_node, last_updated
            FROM processing_checkpoints
            WHERE current_node < 5
            ORDER BY last_updated DESC
            """

            with self.conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()

            result = [
                {
                    "match_id": row[0],
                    "current_node": row[1],
                    "last_updated": row[2]
                }
                for row in rows
            ]

            logger.info(f"Found {len(result)} incomplete matches")
            return result

        except Exception as e:
            logger.error(f"Failed to get incomplete matches: {e}")
            return []

    def _serialize_state(self, state: Dict[str, Any]) -> str:
        """
        Sérialise le state en JSON.
        Gère les types non-JSON (datetime, etc.)
        """
        def json_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        return json.dumps(state, default=json_serializer)

    def _deserialize_state(self, state_json: str) -> Dict[str, Any]:
        """
        Désérialise le JSON en state dict.
        """
        if isinstance(state_json, dict):
            # Déjà désérialisé par psycopg2 (JSONB)
            return state_json
        return json.loads(state_json)

    def cleanup_old_checkpoints(self, hours: int = 24) -> int:
        """
        Supprime les checkpoints plus vieux que X heures.
        Nettoyage périodique pour éviter l'accumulation.

        Args:
            hours: Âge maximum en heures

        Returns:
            Nombre de checkpoints supprimés
        """
        try:
            query = """
            DELETE FROM processing_checkpoints
            WHERE last_updated < NOW() - INTERVAL '%s hours'
            """

            with self.conn.cursor() as cur:
                cur.execute(query, (hours,))
                deleted = cur.rowcount
                self.conn.commit()

            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old checkpoints (>{hours}h)")

            return deleted

        except Exception as e:
            logger.error(f"Failed to cleanup old checkpoints: {e}")
            self.conn.rollback()
            return 0
