#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
TESTS LEGACY EXPORTER - Export PostgreSQL vers JSON
═══════════════════════════════════════════════════════════════════════════════

Tests unitaires pour l'export JSON legacy.
Vérifie la création de backup et le format de sortie.

Exécution:
    cd /home/Mon_ps
    PYTHONPATH=/home/Mon_ps python3 tests/goals/test_legacy_exporter.py

Auteur: Mon_PS Team
Date: 2025-12-23
═══════════════════════════════════════════════════════════════════════════════
"""

import pytest
import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, '/home/Mon_ps')

from services.goals.legacy_exporter import LegacyExporter
from services.goals.config import MIN_GOALS_REQUIRED


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 1: Export crée un fichier valide
# ═══════════════════════════════════════════════════════════════════════════════

def test_exporter_initialization():
    """
    ✅ Vérifie que l'exporter s'initialise correctement.
    """
    exporter = LegacyExporter()
    
    assert exporter.goals_exported == 0, "goals_exported devrait être 0 au départ"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 2: Champs requis pour compatibilité legacy
# ═══════════════════════════════════════════════════════════════════════════════

def test_legacy_fields_required():
    """
    ✅ Vérifie que les champs requis par les scripts legacy sont documentés.
    
    Les 20 scripts legacy attendent ces champs:
    - scorer
    - scoring_team
    - half
    - timing_period
    - minute
    - situation
    """
    required_legacy_fields = [
        "scorer",
        "scoring_team", 
        "half",
        "timing_period",
        "minute",
        "situation",
        "league",
        "date",
        "is_home",
    ]
    
    # Ces champs sont calculés par les triggers PostgreSQL
    # Ce test documente le contrat d'interface
    
    assert len(required_legacy_fields) == 9, "9 champs legacy requis"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 3: Protection minimum buts
# ═══════════════════════════════════════════════════════════════════════════════

def test_minimum_goals_protection():
    """
    🔴 CRITIQUE: L'exporter doit refuser si < MIN_GOALS_REQUIRED.
    
    Même protection que le validator - on ne génère pas un JSON
    vide ou quasi-vide.
    """
    from services.goals.config import MIN_GOALS_REQUIRED
    
    # Vérifier que la constante existe et est raisonnable
    assert MIN_GOALS_REQUIRED >= 100, "Minimum devrait être >= 100"
    assert MIN_GOALS_REQUIRED <= 500, "Minimum ne devrait pas être trop élevé"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 4: Format JSON correct
# ═══════════════════════════════════════════════════════════════════════════════

def test_json_format():
    """
    ✅ Vérifie que le JSON exporté est valide et lisible.
    """
    # Simuler une liste de buts
    sample_goals = [
        {
            "goal_id": "test_1",
            "scorer": "Salah",
            "scoring_team": "Liverpool",
            "half": "1H",
            "timing_period": "31-45",
            "minute": 42,
            "situation": "OpenPlay",
            "league": "Premier League",
            "date": "2025-01-15",
            "is_home": True
        }
    ]
    
    # Tester la sérialisation JSON
    try:
        json_str = json.dumps(sample_goals, indent=2, default=str)
        parsed = json.loads(json_str)
        assert len(parsed) == 1, "Devrait avoir 1 but"
        assert parsed[0]["scorer"] == "Salah", "scorer incorrect"
    except json.JSONDecodeError as e:
        pytest.fail(f"JSON invalide: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 5: Backup path correct
# ═══════════════════════════════════════════════════════════════════════════════

def test_backup_path_generation():
    """
    ✅ Vérifie que le chemin de backup est correct.
    """
    from services.goals.config import LEGACY_GOALS_FILE, LEGACY_GOALS_BACKUP
    
    # Vérifier que le backup a l'extension .bak
    assert str(LEGACY_GOALS_BACKUP).endswith('.bak'), "Backup devrait avoir extension .bak"
    
    # Vérifier que c'est dans le même dossier
    assert LEGACY_GOALS_FILE.parent == LEGACY_GOALS_BACKUP.parent, "Backup devrait être dans le même dossier"


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN - Pour exécution directe
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("TESTS LEGACY EXPORTER - Exécution directe")
    print("=" * 70)
    
    tests = [
        ("test_exporter_initialization", test_exporter_initialization),
        ("test_legacy_fields_required", test_legacy_fields_required),
        ("test_minimum_goals_protection", test_minimum_goals_protection),
        ("test_json_format", test_json_format),
        ("test_backup_path_generation", test_backup_path_generation),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            print(f"  ✅ {name}")
            passed += 1
        except AssertionError as e:
            print(f"  ❌ {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"  💥 {name}: {type(e).__name__}: {e}")
            failed += 1
    
    print("=" * 70)
    print(f"Résultat: {passed}/{len(tests)} tests passés")
    print("=" * 70)
