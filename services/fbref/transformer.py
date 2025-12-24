"""
FBRef Transformer - Conversion données nested vers format plat
═══════════════════════════════════════════════════════════════════════════
Transforme les données du fichier CLEAN (nested) vers format attendu par
le validator et la base de données (flat).
═══════════════════════════════════════════════════════════════════════════

Auteur: Mon_PS Team
Date: 2025-12-24
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger("FBRefTransformer")

# Chemin du mapping de colonnes
COLUMN_MAPPING_PATH = Path("/home/Mon_ps/config/fbref_column_mapping.json")


def safe_numeric(value: Any) -> Optional[float]:
    """
    Conversion sécurisée vers numeric.
    Copie exacte de la fonction legacy pour cohérence.
    """
    if value is None or value == '' or value == '-':
        return None
    try:
        return float(str(value).replace(',', '').replace('%', ''))
    except (ValueError, TypeError):
        return None


class FBRefTransformer:
    """
    Transforme les données FBRef nested vers format plat.

    Transformations effectuées:
    1. Renommer 'name' → 'player_name'
    2. Aplatir 'stats' au niveau racine
    3. Normaliser la casse selon COLUMN_MAPPING (xG → xg)
    """

    def __init__(self, mapping_path: Path = None):
        """
        Initialise le transformer avec le mapping de colonnes.

        Args:
            mapping_path: Chemin vers le fichier de mapping JSON
        """
        self.mapping_path = mapping_path or COLUMN_MAPPING_PATH
        self.column_mapping: Dict[str, str] = {}
        self._load_mapping()

    def _load_mapping(self) -> None:
        """Charge le mapping de colonnes depuis le fichier JSON."""
        try:
            with open(self.mapping_path, 'r', encoding='utf-8') as f:
                self.column_mapping = json.load(f)
            logger.info(f"✅ Mapping loaded: {len(self.column_mapping)} columns")
        except FileNotFoundError:
            logger.error(f"❌ Mapping file not found: {self.mapping_path}")
            self.column_mapping = {}
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in mapping file: {e}")
            self.column_mapping = {}

    def transform_player(self, player_name: str, player_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transforme un joueur du format nested vers format plat.

        Args:
            player_name: Nom du joueur (clé du dict)
            player_data: Données du joueur (format nested)

        Returns:
            Dict avec données aplaties et normalisées
        """
        # Champs de base
        record = {
            'player_name': player_name,
            'team': player_data.get('team', ''),
            'league': player_data.get('league', ''),
            'position': player_data.get('position', ''),
            'nation': player_data.get('nation', ''),
            'age': player_data.get('age'),
        }

        # Récupérer les stats (nested dict)
        stats = player_data.get('stats', {})

        # Aplatir et normaliser les stats
        for json_key, value in stats.items():
            # Chercher le mapping pour cette colonne
            sql_column = self._get_mapped_column(json_key)

            # Convertir en numeric si possible
            record[sql_column] = safe_numeric(value)

        return record

    def _get_mapped_column(self, json_key: str) -> str:
        """
        Retourne le nom de colonne normalisé.

        Args:
            json_key: Nom de la colonne dans le JSON

        Returns:
            Nom normalisé (snake_case) selon le mapping
        """
        # Essayer match exact d'abord
        if json_key in self.column_mapping:
            return self.column_mapping[json_key]

        # Essayer match case-insensitive
        json_key_lower = json_key.lower()
        for key, value in self.column_mapping.items():
            if key.lower() == json_key_lower:
                return value

        # Pas de mapping trouvé, retourner la clé en snake_case
        return json_key.lower()

    def transform_players(self, players_dict: Dict[str, Dict]) -> List[Dict[str, Any]]:
        """
        Transforme un dict de joueurs en liste de dicts plats.

        Args:
            players_dict: Dict {nom_joueur: données_joueur}

        Returns:
            Liste de dicts avec données aplaties
        """
        players = []

        for player_name, player_data in players_dict.items():
            if isinstance(player_data, dict):
                transformed = self.transform_player(player_name, player_data)
                players.append(transformed)

        logger.info(f"📊 Transformed {len(players)} players")
        return players


# === TEST ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test avec données exemple
    test_data = {
        "name": "Test Player",
        "team": "Arsenal",
        "league": "EPL",
        "stats": {
            "xG": 5.0,
            "xG_90": 0.5,
            "shots": 30,
            "shots_90": 3.0
        }
    }

    transformer = FBRefTransformer()
    result = transformer.transform_player("Test Player", test_data)

    print("=== RÉSULTAT TRANSFORMATION ===")
    print(f"player_name: {result.get('player_name')}")
    print(f"team: {result.get('team')}")
    print(f"xg: {result.get('xg')}")
    print(f"xg_90: {result.get('xg_90')}")
    print(f"shots: {result.get('shots')}")
    print(f"shots_90: {result.get('shots_90')}")
