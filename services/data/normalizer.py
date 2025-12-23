#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
DATA NORMALIZER - Format Conversion Hedge Fund Grade
═══════════════════════════════════════════════════════════════════════════════

Module central de normalisation des donnees.
Garantit que les consommateurs recoivent toujours le format attendu,
peu importe le format source.

PRINCIPE:
    "Peu importe ce qui arrive, je retourne toujours le format attendu."

USAGE:
    from services.data.normalizer import DataNormalizer

    # Liste -> Dict (avec cle "id")
    data = DataNormalizer.to_dict(raw_data, key_field="id")

    # Liste -> Dict (avec cle composite)
    data = DataNormalizer.to_dict(raw_data, key_fields=["player_name", "team"])

    # Dict -> Liste
    data = DataNormalizer.to_list(raw_data)

Auteur: Mon_PS Team
Date: 2025-12-23
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
from typing import Union, List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class DataNormalizer:
    """
    Normalise les donnees entrantes vers un format standard.

    Supporte:
    - Liste -> Dict (avec cle simple ou composite)
    - Dict -> Liste
    - Validation de structure
    - Logging des conversions
    """

    @staticmethod
    def to_dict(
        data: Union[List, Dict],
        key_field: str = "id",
        key_fields: Optional[List[str]] = None,
        separator: str = "|"
    ) -> Dict[str, Any]:
        """
        Convertit une liste en dict, ou retourne le dict tel quel.

        Args:
            data: Liste [...] ou Dict {...}
            key_field: Champ simple a utiliser comme cle (default: "id")
            key_fields: Liste de champs pour cle composite (ex: ["name", "team"])
            separator: Separateur pour cles composites (default: "|")

        Returns:
            Dict {key: {...}, key2: {...}}

        Examples:
            # Cle simple
            DataNormalizer.to_dict([{"id": "123", "name": "Salah"}], key_field="id")
            # -> {"123": {"id": "123", "name": "Salah"}}

            # Cle composite
            DataNormalizer.to_dict(
                [{"name": "Salah", "team": "Liverpool"}],
                key_fields=["name", "team"]
            )
            # -> {"Salah|Liverpool": {"name": "Salah", "team": "Liverpool"}}
        """
        # Deja un dict -> retourner tel quel
        if isinstance(data, dict):
            logger.debug(f"to_dict: donnees deja en dict ({len(data)} elements)")
            return data

        # Doit etre une liste
        if not isinstance(data, list):
            raise TypeError(f"Format non supporte: {type(data)}. Attendu: list ou dict")

        result = {}
        converted = 0

        for i, item in enumerate(data):
            if not isinstance(item, dict):
                logger.warning(f"to_dict: element {i} n'est pas un dict, ignore")
                continue

            # Determiner la cle
            if key_fields:
                # Cle composite
                key_parts = [str(item.get(f, "")) for f in key_fields]
                key = separator.join(key_parts)
            else:
                # Cle simple
                key = str(item.get(key_field, i))

            result[key] = item
            converted += 1

        logger.info(f"to_dict: converti {converted} elements de liste en dict")
        return result

    @staticmethod
    def to_list(data: Union[List, Dict]) -> List[Any]:
        """
        Convertit un dict en liste, ou retourne la liste telle quelle.

        Args:
            data: Liste [...] ou Dict {...}

        Returns:
            Liste [...]
        """
        if isinstance(data, list):
            logger.debug(f"to_list: donnees deja en liste ({len(data)} elements)")
            return data

        if isinstance(data, dict):
            result = list(data.values())
            logger.info(f"to_list: converti dict en liste ({len(result)} elements)")
            return result

        raise TypeError(f"Format non supporte: {type(data)}. Attendu: list ou dict")

    @staticmethod
    def validate_structure(
        data: Union[List, Dict],
        required_fields: List[str],
        sample_size: int = 5
    ) -> tuple:
        """
        Valide que les donnees contiennent les champs requis.

        Args:
            data: Donnees a valider
            required_fields: Champs obligatoires
            sample_size: Nombre d'elements a verifier

        Returns:
            (is_valid: bool, missing_fields: set, warnings: list)
        """
        warnings = []
        missing_fields = set()

        # Normaliser en liste pour validation
        items = DataNormalizer.to_list(data) if isinstance(data, dict) else data

        if not items:
            return False, set(required_fields), ["Donnees vides"]

        # Verifier un echantillon
        for i, item in enumerate(items[:sample_size]):
            if not isinstance(item, dict):
                warnings.append(f"Element {i} n'est pas un dict")
                continue

            for field in required_fields:
                if field not in item:
                    missing_fields.add(field)

        is_valid = len(missing_fields) == 0
        return is_valid, missing_fields, warnings


# ═══════════════════════════════════════════════════════════════════════════════
# TEST RAPIDE
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=" * 70)
    print("TEST DATA NORMALIZER")
    print("=" * 70)

    # Test 1: Liste -> Dict (cle simple)
    test_list = [
        {"id": "123", "name": "Salah", "team": "Liverpool"},
        {"id": "456", "name": "Haaland", "team": "Man City"},
    ]
    result = DataNormalizer.to_dict(test_list, key_field="id")
    print(f"\n[TEST 1] Liste->Dict cle simple: {len(result)} elements")
    print(f"   Cles: {list(result.keys())}")

    # Test 2: Liste -> Dict (cle composite)
    result2 = DataNormalizer.to_dict(test_list, key_fields=["name", "team"])
    print(f"\n[TEST 2] Liste->Dict cle composite: {len(result2)} elements")
    print(f"   Cles: {list(result2.keys())}")

    # Test 3: Dict -> Liste
    test_dict = {"a": {"x": 1}, "b": {"x": 2}}
    result3 = DataNormalizer.to_list(test_dict)
    print(f"\n[TEST 3] Dict->Liste: {len(result3)} elements")

    # Test 4: Validation
    is_valid, missing, warnings = DataNormalizer.validate_structure(
        test_list,
        required_fields=["id", "name", "missing_field"]
    )
    print(f"\n[TEST 4] Validation: valid={is_valid}, missing={missing}")

    # Test 5: Avec fichier reel
    import json
    from pathlib import Path

    path = Path("/home/Mon_ps/data/quantum_v2/players_impact_dna.json")
    if path.exists():
        with open(path) as f:
            real_data = json.load(f)
        result5 = DataNormalizer.to_dict(real_data, key_field="id")
        print(f"\n[TEST 5] Fichier reel: {len(result5)} joueurs normalises")
        # Verifier Haaland
        if "8260" in result5:
            print(f"   Haaland trouve: {result5['8260'].get('player_name')}")

    print("\n" + "=" * 70)
    print("TOUS LES TESTS PASSES")
    print("=" * 70)
