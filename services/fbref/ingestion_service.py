"""
FBRef Ingestion Service - Service Principal
═══════════════════════════════════════════════════════════════════════════
Orchestre l'ingestion sécurisée des données FBRef.
═══════════════════════════════════════════════════════════════════════════
"""
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

import psycopg2
from psycopg2.extras import RealDictCursor

from .config import FBRefConfig, DEFAULT_CONFIG
from .validator import FBRefValidator, ValidationResult
from .transformer import FBRefTransformer

logger = logging.getLogger("FBRefIngestionService")


class FBRefIngestionService:
    """
    Service d'ingestion FBRef avec protection Hedge Fund Grade.

    Workflow:
    1. Charger les données brutes
    2. Valider (min 500 joueurs, toutes ligues présentes)
    3. Créer backup de l'existant
    4. Écrire les nouvelles données
    5. Exporter en format legacy si nécessaire
    """

    def __init__(self, config: FBRefConfig = None):
        self.config = config or DEFAULT_CONFIG
        self.validator = FBRefValidator(self.config)
        self.transformer = FBRefTransformer()

    def ingest_from_json(self, json_path: Path = None) -> ValidationResult:
        """
        Ingère les données depuis un fichier JSON.

        Args:
            json_path: Chemin du fichier JSON (défaut: config.CLEAN_JSON_PATH)

        Returns:
            ValidationResult
        """
        json_path = json_path or self.config.CLEAN_JSON_PATH

        logger.info(f"📂 Loading data from {json_path}")

        # === ÉTAPE 1: Charger ===
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            logger.error(f"❌ File not found: {json_path}")
            return ValidationResult(
                is_valid=False,
                total_players=0,
                players_by_league={},
                warnings=[],
                errors=[f"File not found: {json_path}"]
            )
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON: {e}")
            return ValidationResult(
                is_valid=False,
                total_players=0,
                players_by_league={},
                warnings=[],
                errors=[f"Invalid JSON: {e}"]
            )

        # Gérer différents formats (liste ou dict avec clés)
        if isinstance(data, list):
            players = data
        elif isinstance(data, dict):
            # Chercher une clé contenant les joueurs
            if "players" in data:
                players_data = data["players"]
                # Si players est un dict {nom: stats}, convertir en liste
                if isinstance(players_data, dict):
                    # Utiliser le transformer pour aplatir et normaliser
                    players = self.transformer.transform_players(players_data)
                    logger.info(f"📊 Transformed {len(players)} players")
                else:
                    players = players_data
            elif "data" in data:
                players = data["data"]
            else:
                # Peut-être dict par ligue
                players = []
                for key, value in data.items():
                    if isinstance(value, list):
                        players.extend(value)
        else:
            players = []

        logger.info(f"📊 Loaded {len(players)} players")

        # === ÉTAPE 2: Valider ===
        result = self.validator.validate(players)

        if not result.is_valid:
            logger.error("❌ Validation FAILED - Aborting ingestion")
            return result

        # === ÉTAPE 3: Backup ===
        self._create_backup()

        # === ÉTAPE 4: Sauvegarder données validées ===
        self._save_validated_data(players)

        logger.info("✅ Ingestion completed successfully")
        return result

    def _create_backup(self) -> Optional[Path]:
        """Crée un backup du fichier existant."""
        if not self.config.CLEAN_JSON_PATH.exists():
            logger.info("📁 No existing file to backup")
            return None

        # Créer répertoire backup
        self.config.BACKUP_DIR.mkdir(parents=True, exist_ok=True)

        # Nom avec timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"fbref_backup_{timestamp}.json"
        backup_path = self.config.BACKUP_DIR / backup_name

        # Copier
        shutil.copy2(self.config.CLEAN_JSON_PATH, backup_path)
        logger.info(f"💾 Backup created: {backup_path}")

        # Nettoyer vieux backups (garder 7 derniers)
        self._cleanup_old_backups()

        return backup_path

    def _cleanup_old_backups(self, keep: int = 7) -> None:
        """Supprime les vieux backups, garde les N plus récents."""
        backups = sorted(
            self.config.BACKUP_DIR.glob("fbref_backup_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        for old_backup in backups[keep:]:
            old_backup.unlink()
            logger.debug(f"🗑️ Deleted old backup: {old_backup}")

    def _save_validated_data(self, players: List[Dict[str, Any]]) -> None:
        """Sauvegarde les données validées."""
        output = {
            "metadata": {
                "version": "2.0",
                "created": datetime.now().isoformat(),
                "total_players": len(players),
                "source": "FBRefIngestionService"
            },
            "players": players
        }

        with open(self.config.CLEAN_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        logger.info(f"💾 Saved {len(players)} players to {self.config.CLEAN_JSON_PATH}")

    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du fichier actuel."""
        if not self.config.CLEAN_JSON_PATH.exists():
            return {"status": "no_data"}

        with open(self.config.CLEAN_JSON_PATH, 'r') as f:
            data = json.load(f)

        players_data = data.get("players", [])

        # Gérer format legacy (dict) vs nouveau format (list)
        if isinstance(players_data, dict):
            players = list(players_data.values())
        else:
            players = players_data

        by_league = {}
        for p in players:
            if isinstance(p, dict):
                league = p.get("league", "Unknown")
                by_league[league] = by_league.get(league, 0) + 1

        return {
            "status": "ok",
            "total_players": len(players),
            "by_league": by_league,
            "last_updated": data.get("metadata", {}).get("created")
        }

    def validate_from_db(self) -> ValidationResult:
        """
        Valide les données directement depuis PostgreSQL.

        Returns:
            ValidationResult avec statut et détails
        """
        logger.info("🔍 Validating data from PostgreSQL...")

        try:
            # Connexion à PostgreSQL
            conn = psycopg2.connect(
                host=self.config.DB_HOST,
                port=self.config.DB_PORT,
                dbname=self.config.DB_NAME,
                user=self.config.DB_USER,
                password=self.config.DB_PASSWORD
            )

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Récupérer tous les joueurs avec colonnes requises
                columns = ", ".join(self.config.REQUIRED_COLUMNS)
                query = f"""
                    SELECT {columns}
                    FROM {self.config.DB_TABLE}
                    WHERE player_name IS NOT NULL
                """
                cur.execute(query)
                players = [dict(row) for row in cur.fetchall()]

            conn.close()

            logger.info(f"📊 Loaded {len(players)} players from PostgreSQL")

            # Valider avec le validator existant
            result = self.validator.validate(players)

            return result

        except psycopg2.Error as e:
            logger.error(f"❌ Database error: {e}")
            return ValidationResult(
                is_valid=False,
                total_players=0,
                players_by_league={},
                warnings=[],
                errors=[f"Database error: {e}"]
            )


# === TEST ===
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    service = FBRefIngestionService()
    stats = service.get_stats()
    print(f"Current stats: {stats}")
