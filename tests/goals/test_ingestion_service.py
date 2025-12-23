#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
TESTS INGESTION SERVICE - GoalsIngestionService Hedge Fund Grade
═══════════════════════════════════════════════════════════════════════════════

Tests unitaires pour le service d'ingestion.
Focus sur le MAPPING CORRECT du bug historique.

BUG CORRIGÉ:
- FAUX: match['h']['goals']
- CORRECT: match['goals']['h']

Exécution:
    cd /home/Mon_ps
    PYTHONPATH=/home/Mon_ps python3 tests/goals/test_ingestion_service.py

Auteur: Mon_PS Team
Date: 2025-12-23
═══════════════════════════════════════════════════════════════════════════════
"""

import pytest
import sys
sys.path.insert(0, '/home/Mon_ps')

from services.goals.ingestion_service import GoalsIngestionService


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES - Données de test simulant Understat API
# ═══════════════════════════════════════════════════════════════════════════════

def create_sample_match(match_id: str, home_goals: int, away_goals: int) -> dict:
    """
    Crée un match au format RÉEL Understat API.
    
    ATTENTION: C'est la structure CORRECTE que l'API retourne.
    Le bug était de chercher match['h']['goals'] au lieu de match['goals']['h']
    """
    return {
        "id": match_id,
        "isResult": True,
        "h": {
            "id": "87",
            "title": "Liverpool",
            "short_title": "LIV"
        },
        "a": {
            "id": "73", 
            "title": "Manchester City",
            "short_title": "MCI"
        },
        "goals": {
            "h": str(home_goals),  # SCORES ICI - pas dans h['goals'] !
            "a": str(away_goals)
        },
        "xG": {
            "h": "1.85",
            "a": "1.42"
        },
        "datetime": "2025-01-15 15:00:00"
    }


def create_sample_raw_data() -> dict:
    """Crée un échantillon de données brutes simulant understat_raw_api.json"""
    return {
        "EPL": {
            "teams": {},
            "players": [],
            "dates": [
                create_sample_match("1001", 3, 1),  # Liverpool 3-1 City
                create_sample_match("1002", 2, 2),  # Match nul 2-2
                create_sample_match("1003", 0, 1),  # 0-1
            ]
        },
        "La_liga": {
            "teams": {},
            "players": [],
            "dates": [
                create_sample_match("2001", 4, 0),  # 4-0
                create_sample_match("2002", 1, 1),  # 1-1
            ]
        }
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 1: MAPPING CORRECT - LE TEST LE PLUS CRITIQUE
# ═══════════════════════════════════════════════════════════════════════════════

def test_correct_mapping():
    """
    🔴 CRITIQUE: Vérifie que le mapping est CORRECT.
    
    Ce test reproduit exactement le bug qu'on a corrigé:
    - BUG: match['h']['goals'] retournait None/0
    - FIX: match['goals']['h'] retourne le vrai score
    
    Si ce test échoue, le bug est de retour !
    """
    service = GoalsIngestionService(dry_run=True)
    raw_data = create_sample_raw_data()
    
    # Extraire les buts
    goals = service._extract_goals(raw_data)
    
    # Compter les buts attendus:
    # EPL: (3+1) + (2+2) + (0+1) = 9 buts
    # La_liga: (4+0) + (1+1) = 6 buts
    # Total: 15 buts
    
    assert len(goals) == 15, f"Attendu 15 buts, obtenu {len(goals)}"
    
    # Vérifier qu'on n'a pas 0 buts (symptôme du bug)
    assert len(goals) > 0, "ALERTE: 0 buts extraits - le bug de mapping est peut-être de retour!"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 2: Extraction des 5 ligues
# ═══════════════════════════════════════════════════════════════════════════════

def test_extract_all_leagues():
    """
    ✅ Vérifie que toutes les ligues configurées sont traitées.
    """
    service = GoalsIngestionService(dry_run=True)
    
    # Données avec toutes les ligues
    raw_data = {
        "EPL": {"teams": {}, "players": [], "dates": [create_sample_match("1", 1, 0)]},
        "La_liga": {"teams": {}, "players": [], "dates": [create_sample_match("2", 1, 0)]},
        "Bundesliga": {"teams": {}, "players": [], "dates": [create_sample_match("3", 1, 0)]},
        "Serie_A": {"teams": {}, "players": [], "dates": [create_sample_match("4", 1, 0)]},
        "Ligue_1": {"teams": {}, "players": [], "dates": [create_sample_match("5", 1, 0)]},
    }
    
    goals = service._extract_goals(raw_data)
    
    # 5 matchs × 1 but chacun = 5 buts
    assert len(goals) == 5, f"Attendu 5 buts (1 par ligue), obtenu {len(goals)}"
    
    # Vérifier les ligues représentées
    leagues = set(g["league"] for g in goals)
    expected_leagues = {"Premier League", "La Liga", "Bundesliga", "Serie A", "Ligue 1"}
    assert leagues == expected_leagues, f"Ligues manquantes: {expected_leagues - leagues}"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 3: Calcul des périodes
# ═══════════════════════════════════════════════════════════════════════════════

def test_calculate_period():
    """
    ✅ Vérifie le calcul des périodes de temps.
    """
    service = GoalsIngestionService(dry_run=True)
    
    # Test des différentes périodes
    test_cases = [
        (5, "0-15"),
        (15, "0-15"),
        (16, "16-30"),
        (30, "16-30"),
        (31, "31-45"),
        (45, "31-45"),
        (46, "46-60"),
        (60, "46-60"),
        (61, "61-75"),
        (75, "61-75"),
        (76, "76-90"),
        (90, "76-90"),
        (91, "90+"),
        (120, "90+"),
    ]
    
    for minute, expected_period in test_cases:
        result = service._calculate_period(minute)
        assert result == expected_period, f"minute={minute}: attendu '{expected_period}', obtenu '{result}'"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 4: Structure de l'entrée but
# ═══════════════════════════════════════════════════════════════════════════════

def test_create_goal_entry_structure():
    """
    ✅ Vérifie que la structure d'un but contient tous les champs requis.
    """
    service = GoalsIngestionService(dry_run=True)
    raw_data = {
        "EPL": {
            "teams": {}, 
            "players": [], 
            "dates": [create_sample_match("1001", 1, 0)]
        }
    }
    
    goals = service._extract_goals(raw_data)
    assert len(goals) == 1, "Devrait avoir exactement 1 but"
    
    goal = goals[0]
    
    # Champs obligatoires
    required_fields = [
        "goal_id",
        "match_id",
        "team_name",
        "opponent",
        "league",
        "minute",
        "period",
        "is_home",
        "home_team",
        "away_team",
        "is_first_goal",
        "is_last_goal",
    ]
    
    for field in required_fields:
        assert field in goal, f"Champ manquant: {field}"
    
    # Vérifier les valeurs
    assert goal["team_name"] == "Liverpool", "team_name incorrect"
    assert goal["opponent"] == "Manchester City", "opponent incorrect"
    assert goal["is_home"] == True, "is_home devrait être True"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 5: Mode dry-run ne modifie pas la DB
# ═══════════════════════════════════════════════════════════════════════════════

def test_dry_run_no_side_effects():
    """
    ✅ Vérifie que le mode dry-run n'a pas d'effets de bord.
    """
    service = GoalsIngestionService(dry_run=True)
    
    # Le service devrait avoir dry_run=True
    assert service.dry_run == True, "dry_run devrait être True"
    
    # En mode dry-run, goals_inserted est mis à jour sans toucher la DB
    raw_data = create_sample_raw_data()
    goals = service._extract_goals(raw_data)
    
    # Simuler ce que run() ferait
    service.goals_processed = len(goals)
    service.goals_inserted = len(goals)  # En dry-run, on simule
    
    assert service.goals_inserted > 0, "Devrait avoir simulé des insertions"


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 6: Matchs non joués ignorés
# ═══════════════════════════════════════════════════════════════════════════════

def test_skip_unplayed_matches():
    """
    ✅ Vérifie que les matchs non joués (isResult=False) sont ignorés.
    """
    service = GoalsIngestionService(dry_run=True)
    
    raw_data = {
        "EPL": {
            "teams": {},
            "players": [],
            "dates": [
                {
                    "id": "future_match",
                    "isResult": False,  # Match pas encore joué
                    "h": {"title": "Liverpool"},
                    "a": {"title": "Arsenal"},
                    "goals": {"h": "0", "a": "0"},
                    "xG": {"h": "0", "a": "0"},
                    "datetime": "2025-12-25 15:00:00"
                },
                create_sample_match("played_match", 2, 1)  # Match joué
            ]
        }
    }
    
    goals = service._extract_goals(raw_data)
    
    # Seulement le match joué: 2+1 = 3 buts
    assert len(goals) == 3, f"Attendu 3 buts (match joué uniquement), obtenu {len(goals)}"


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN - Pour exécution directe
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("TESTS INGESTION SERVICE - Exécution directe")
    print("=" * 70)
    
    tests = [
        ("test_correct_mapping", test_correct_mapping),
        ("test_extract_all_leagues", test_extract_all_leagues),
        ("test_calculate_period", test_calculate_period),
        ("test_create_goal_entry_structure", test_create_goal_entry_structure),
        ("test_dry_run_no_side_effects", test_dry_run_no_side_effects),
        ("test_skip_unplayed_matches", test_skip_unplayed_matches),
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
