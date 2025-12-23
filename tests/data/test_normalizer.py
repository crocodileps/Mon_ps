#!/usr/bin/env python3
"""
Tests unitaires pour DataNormalizer
"""

import pytest
import sys
sys.path.insert(0, '/home/Mon_ps')

from services.data.normalizer import DataNormalizer


# ═══════════════════════════════════════════════════════════════════════════════
# TEST TO_DICT
# ═══════════════════════════════════════════════════════════════════════════════

def test_to_dict_from_list_simple_key():
    """Liste -> Dict avec cle simple"""
    data = [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}]
    result = DataNormalizer.to_dict(data, key_field="id")

    assert isinstance(result, dict)
    assert len(result) == 2
    assert "1" in result
    assert result["1"]["name"] == "A"


def test_to_dict_from_list_composite_key():
    """Liste -> Dict avec cle composite"""
    data = [{"name": "Salah", "team": "Liverpool"}]
    result = DataNormalizer.to_dict(data, key_fields=["name", "team"])

    assert "Salah|Liverpool" in result


def test_to_dict_from_dict_passthrough():
    """Dict -> Dict (passthrough)"""
    data = {"a": {"x": 1}}
    result = DataNormalizer.to_dict(data)

    assert result is data  # Meme objet, pas de copie


def test_to_dict_invalid_type():
    """Type invalide -> TypeError"""
    with pytest.raises(TypeError):
        DataNormalizer.to_dict("not a list or dict")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST TO_LIST
# ═══════════════════════════════════════════════════════════════════════════════

def test_to_list_from_dict():
    """Dict -> Liste"""
    data = {"a": {"x": 1}, "b": {"x": 2}}
    result = DataNormalizer.to_list(data)

    assert isinstance(result, list)
    assert len(result) == 2


def test_to_list_from_list_passthrough():
    """Liste -> Liste (passthrough)"""
    data = [1, 2, 3]
    result = DataNormalizer.to_list(data)

    assert result is data


# ═══════════════════════════════════════════════════════════════════════════════
# TEST VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def test_validate_structure_valid():
    """Validation avec tous les champs presents"""
    data = [{"id": "1", "name": "A"}]
    is_valid, missing, warnings = DataNormalizer.validate_structure(
        data, required_fields=["id", "name"]
    )

    assert is_valid is True
    assert len(missing) == 0


def test_validate_structure_missing_field():
    """Validation avec champ manquant"""
    data = [{"id": "1"}]
    is_valid, missing, warnings = DataNormalizer.validate_structure(
        data, required_fields=["id", "name"]
    )

    assert is_valid is False
    assert "name" in missing


def test_validate_structure_empty_data():
    """Validation avec donnees vides"""
    is_valid, missing, warnings = DataNormalizer.validate_structure(
        [], required_fields=["id"]
    )

    assert is_valid is False


# ═══════════════════════════════════════════════════════════════════════════════
# TEST AVEC FICHIER REEL
# ═══════════════════════════════════════════════════════════════════════════════

def test_real_file_players_impact_dna():
    """Test avec le vrai fichier players_impact_dna.json"""
    import json
    from pathlib import Path

    path = Path("/home/Mon_ps/data/quantum_v2/players_impact_dna.json")
    if not path.exists():
        pytest.skip("Fichier players_impact_dna.json non disponible")

    with open(path) as f:
        raw_data = json.load(f)

    # Doit etre une liste
    assert isinstance(raw_data, list)

    # Normaliser en dict
    normalized = DataNormalizer.to_dict(raw_data, key_field="id")

    assert isinstance(normalized, dict)
    assert len(normalized) > 2000  # ~2348 joueurs

    # Verifier Haaland (id: 8260)
    assert "8260" in normalized
    assert normalized["8260"]["player_name"] == "Erling Haaland"


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("TESTS DATA NORMALIZER")
    print("=" * 70)

    tests = [
        ("test_to_dict_from_list_simple_key", test_to_dict_from_list_simple_key),
        ("test_to_dict_from_list_composite_key", test_to_dict_from_list_composite_key),
        ("test_to_dict_from_dict_passthrough", test_to_dict_from_dict_passthrough),
        ("test_to_list_from_dict", test_to_list_from_dict),
        ("test_to_list_from_list_passthrough", test_to_list_from_list_passthrough),
        ("test_validate_structure_valid", test_validate_structure_valid),
        ("test_validate_structure_missing_field", test_validate_structure_missing_field),
        ("test_validate_structure_empty_data", test_validate_structure_empty_data),
        ("test_real_file_players_impact_dna", test_real_file_players_impact_dna),
    ]

    passed = 0
    for name, func in tests:
        try:
            func()
            print(f"  ✅ {name}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")

    print("=" * 70)
    print(f"Resultat: {passed}/{len(tests)} tests passes")
    print("=" * 70)
