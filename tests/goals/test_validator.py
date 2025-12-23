#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
TESTS VALIDATOR - GoalsValidator Hedge Fund Grade
═══════════════════════════════════════════════════════════════════════════════

Tests unitaires pour la validation des données de buts.
Vérifie que le système refuse les données corrompues et accepte les bonnes.

Exécution:
    cd /home/Mon_ps
    PYTHONPATH=/home/Mon_ps pytest tests/goals/test_validator.py -v

Auteur: Mon_PS Team
Date: 2025-12-23
═══════════════════════════════════════════════════════════════════════════════
"""

import pytest
import sys
sys.path.insert(0, '/home/Mon_ps')

from services.goals.validator import GoalsValidator
from services.goals.config import MIN_GOALS_REQUIRED


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES - Données de test
# ═══════════════════════════════════════════════════════════════════════════════

def create_valid_goal(index: int = 1) -> dict:
    """Crée un but valide pour les tests."""
    return {
        "goal_id": f"test_{index}",
        "match_id": f"match_{index}",
        "team_name": "Liverpool",
        "opponent": "Manchester City",
        "league": "Premier League",
        "minute": 45,
        "period": "31-45",
        "player_name": "Salah",
        "is_home": True,
        "xg": 0.35
    }


def create_goals_list(count: int) -> list:
    """Crée une liste de buts valides."""
    return [create_valid_goal(i) for i in range(count)]


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 1: Rejette liste vide
# ═══════════════════════════════════════════════════════════════════════════════

def test_reject_empty_list():
    """
    🔴 CRITIQUE: Une liste vide doit être rejetée.
    
    C'est exactement le bug qu'on a corrigé - le JSON était vidé
    et personne ne l'a détecté.
    """
    validator = GoalsValidator()
    
    is_valid, message = validator.validate([])
    
    assert is_valid == False, "Liste vide devrait être rejetée"
    assert "vide" in message.lower(), "Message devrait mentionner 'vide'"
    assert len(validator.errors) > 0, "Devrait avoir au moins une erreur"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 2: Rejette si moins de 100 buts
# ═══════════════════════════════════════════════════════════════════════════════

def test_reject_below_minimum():
    """
    🔴 CRITIQUE: Moins de MIN_GOALS_REQUIRED (100) buts = données corrompues.
    
    Protection contre un scraping partiel ou échoué.
    """
    validator = GoalsValidator(min_goals=100)
    goals = create_goals_list(50)  # Seulement 50 buts
    
    is_valid, message = validator.validate(goals)
    
    assert is_valid == False, "50 buts < 100 minimum devrait être rejeté"
    assert "50" in message, "Message devrait mentionner le nombre de buts"
    assert "100" in message, "Message devrait mentionner le minimum"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 3: Accepte données valides
# ═══════════════════════════════════════════════════════════════════════════════

def test_accept_valid_data():
    """
    ✅ NORMAL: 150 buts valides doivent être acceptés.
    """
    validator = GoalsValidator(min_goals=100)
    goals = create_goals_list(150)
    
    is_valid, message = validator.validate(goals)
    
    assert is_valid == True, "150 buts valides devraient être acceptés"
    assert "150" in message, "Message devrait mentionner le nombre de buts"
    assert len(validator.errors) == 0, "Pas d'erreur attendue"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 4: Détecte champs manquants
# ═══════════════════════════════════════════════════════════════════════════════

def test_detect_missing_fields():
    """
    🟡 WARNING: Champs obligatoires manquants = warnings (pas rejet).
    
    On accepte quand même si le nombre de buts est suffisant,
    mais on log des warnings pour investigation.
    """
    validator = GoalsValidator(min_goals=100)
    
    # Créer 150 buts dont certains avec champs manquants
    goals = create_goals_list(150)
    
    # Corrompre quelques buts (enlever match_id)
    for i in range(10):
        del goals[i]["match_id"]
    
    is_valid, message = validator.validate(goals)
    
    # Devrait quand même être valide (< 10% manquants)
    assert is_valid == True, "Devrait être accepté malgré quelques champs manquants"
    assert len(validator.warnings) > 0, "Devrait avoir des warnings"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 5: Détecte minutes invalides
# ═══════════════════════════════════════════════════════════════════════════════

def test_detect_invalid_minutes():
    """
    🟡 WARNING: minute > 120 ou < 0 = warning.
    
    Les minutes de football vont de 0 à ~120 (prolongations).
    Une minute de 200 indique des données corrompues.
    """
    validator = GoalsValidator(min_goals=100)
    
    goals = create_goals_list(150)
    
    # Corrompre quelques minutes
    goals[0]["minute"] = 200  # Invalide
    goals[1]["minute"] = -5   # Invalide
    goals[2]["minute"] = 90   # Valide (limite)
    
    is_valid, message = validator.validate(goals)
    
    # Devrait quand même être valide
    assert is_valid == True, "Devrait être accepté"
    # Le validator compte les minutes invalides dans les warnings
    assert len(validator.warnings) > 0, "Devrait avoir des warnings pour minutes invalides"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 6: Cas limite - exactement 100 buts
# ═══════════════════════════════════════════════════════════════════════════════

def test_accept_edge_case_100():
    """
    ✅ EDGE CASE: Exactement 100 buts = accepté (>=, pas >).
    
    Test de la condition limite.
    """
    validator = GoalsValidator(min_goals=100)
    goals = create_goals_list(100)  # Exactement 100
    
    is_valid, message = validator.validate(goals)
    
    assert is_valid == True, "Exactement 100 buts devrait être accepté"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 7: Cas limite - 99 buts (juste en dessous)
# ═══════════════════════════════════════════════════════════════════════════════

def test_reject_edge_case_99():
    """
    🔴 EDGE CASE: 99 buts = rejeté (< 100).
    
    Test de la condition limite.
    """
    validator = GoalsValidator(min_goals=100)
    goals = create_goals_list(99)  # Juste en dessous
    
    is_valid, message = validator.validate(goals)
    
    assert is_valid == False, "99 buts devrait être rejeté"


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN - Pour exécution directe
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("TESTS VALIDATOR - Exécution directe")
    print("=" * 70)
    
    # Exécuter les tests manuellement
    tests = [
        ("test_reject_empty_list", test_reject_empty_list),
        ("test_reject_below_minimum", test_reject_below_minimum),
        ("test_accept_valid_data", test_accept_valid_data),
        ("test_detect_missing_fields", test_detect_missing_fields),
        ("test_detect_invalid_minutes", test_detect_invalid_minutes),
        ("test_accept_edge_case_100", test_accept_edge_case_100),
        ("test_reject_edge_case_99", test_reject_edge_case_99),
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
            print(f"  💥 {name}: {e}")
            failed += 1
    
    print("=" * 70)
    print(f"Résultat: {passed}/{len(tests)} tests passés")
    print("=" * 70)
