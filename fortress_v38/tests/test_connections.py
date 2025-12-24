"""
FORTRESS V3.8 - Tests de Connexion Phase 1
==========================================

Valide que TOUS les composants sont accessibles:
1. Fichiers SDK (Python)
2. Données JSON
3. PostgreSQL
4. Imports des modules existants

Version: 1.0.0
Date: 24 Décembre 2025
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Ajouter le projet au path
PROJECT_ROOT = Path("/home/Mon_ps")
sys.path.insert(0, str(PROJECT_ROOT))

# Import config FORTRESS
from fortress_v38.config import (
    verify_paths,
    get_postgres_connection,
    POSTGRES_TABLES,
    UNIFIED_LOADER,
    TEAM_DNA_UNIFIED,
    GOALKEEPER_DNA_V44,
    DEFENSE_DNA_V51,
    FRICTION_MATRIX_12X12,
    MARKET_REGISTRY,
    FORTRESS_CONFIG
)

from fortress_v38.state import create_initial_state, FortressState


def test_config_paths() -> bool:
    """Test 1: Vérifie tous les chemins config."""
    print("\n" + "=" * 60)
    print("📁 TEST 1: CHEMINS CONFIG")
    print("=" * 60)
    
    results = verify_paths()
    all_ok = all(results.values())
    
    for name, exists in results.items():
        status = "✅" if exists else "❌"
        print(f"   {status} {name}")
    
    return all_ok


def test_postgres_connection() -> bool:
    """Test 2: Vérifie connexion PostgreSQL."""
    print("\n" + "=" * 60)
    print("🐘 TEST 2: POSTGRESQL")
    print("=" * 60)
    
    conn = get_postgres_connection()
    if not conn:
        print("   ❌ Connexion échouée")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Test basique
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"   ✅ Version: {version[:50]}...")
        
        # Compter les tables critiques
        tables_ok = 0
        tables_total = len(POSTGRES_TABLES)
        
        for name, full_table in POSTGRES_TABLES.items():
            schema, table = full_table.split(".")
            cursor.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = %s AND table_name = %s
                );
            """, (schema, table))
            exists = cursor.fetchone()[0]
            
            if exists:
                cursor.execute(f"SELECT COUNT(*) FROM {full_table};")
                count = cursor.fetchone()[0]
                print(f"   ✅ {full_table}: {count:,} rows")
                tables_ok += 1
            else:
                print(f"   ❌ {full_table}: N'EXISTE PAS")
        
        conn.close()
        print(f"\n   📊 Tables: {tables_ok}/{tables_total} OK")
        return tables_ok == tables_total
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        conn.close()
        return False


def test_json_loading() -> bool:
    """Test 3: Vérifie chargement JSON."""
    print("\n" + "=" * 60)
    print("📄 TEST 3: CHARGEMENT JSON")
    print("=" * 60)
    
    json_files = {
        "team_dna_unified": TEAM_DNA_UNIFIED,
        "goalkeeper_dna_v44": GOALKEEPER_DNA_V44,
        "defense_dna_v51": DEFENSE_DNA_V51,
    }
    
    all_ok = True
    
    for name, path in json_files.items():
        if not path.exists():
            print(f"   ❌ {name}: FICHIER MANQUANT")
            all_ok = False
            continue
        
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                count = len(data)
                print(f"   ✅ {name}: {count} entrées (list)")
            elif isinstance(data, dict):
                count = len(data.keys())
                print(f"   ✅ {name}: {count} clés (dict)")
            else:
                print(f"   ✅ {name}: chargé ({type(data).__name__})")
                
        except Exception as e:
            print(f"   ❌ {name}: {e}")
            all_ok = False
    
    return all_ok


def test_unified_loader() -> bool:
    """Test 4: Vérifie UnifiedLoader."""
    print("\n" + "=" * 60)
    print("🔄 TEST 4: UNIFIED LOADER")
    print("=" * 60)
    
    try:
        from quantum.loaders.unified_loader import UnifiedLoader
        
        loader = UnifiedLoader()
        stats = loader.get_stats()
        
        print(f"   ✅ UnifiedLoader initialisé")
        print(f"   📊 Équipes: {stats.get('teams_count', 'N/A')}")
        print(f"   📊 Joueurs: {stats.get('players_count', 'N/A')}")
        print(f"   📊 Arbitres: {stats.get('referees_count', 'N/A')}")
        
        # Test get_team
        liverpool = loader.get_team("Liverpool")
        if liverpool:
            print(f"   ✅ get_team('Liverpool'): OK")
        else:
            print(f"   ⚠️  get_team('Liverpool'): None (pas critique)")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return False


def test_friction_matrix() -> bool:
    """Test 5: Vérifie Friction Matrix."""
    print("\n" + "=" * 60)
    print("⚡ TEST 5: FRICTION MATRIX 12×12")
    print("=" * 60)
    
    try:
        from quantum.models.friction_matrix_12x12 import get_friction
        
        # Test une friction
        result = get_friction("GEGENPRESS", "LOW_BLOCK")
        
        print(f"   ✅ get_friction() fonctionne")
        print(f"   📊 GEGENPRESS vs LOW_BLOCK:")
        print(f"      • Clash Type: {result.clash_type}")
        print(f"      • Tempo: {result.tempo}")
        print(f"      • Goals Modifier: {result.goals_modifier:+.1f}")
        print(f"      • Late Goal Prob: {result.late_goal_prob:.0%}")
        print(f"      • Primary Markets: {result.primary_markets[:2]}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return False

def test_market_registry() -> bool:
    """Test 6: Vérifie Market Registry."""
    print("\n" + "=" * 60)
    print("📈 TEST 6: MARKET REGISTRY")
    print("=" * 60)
    
    try:
        from quantum.models.market_registry import (
            MarketType, 
            normalize_market,
            get_market_metadata
        )
        
        # Compter les marchés
        market_count = len(list(MarketType))
        print(f"   ✅ MarketType: {market_count} marchés")
        
        # Test normalisation
        normalized = normalize_market("over 2.5 goals")
        if normalized:
            print(f"   ✅ normalize_market('over 2.5 goals'): {normalized.name}")
        else:
            print(f"   ⚠️  normalize_market: None")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return False


def test_state_dataclasses() -> bool:
    """Test 7: Vérifie State Dataclasses."""
    print("\n" + "=" * 60)
    print("🎯 TEST 7: STATE DATACLASSES")
    print("=" * 60)
    
    try:
        state = create_initial_state(
            match_id="TEST_001",
            home_team="Liverpool",
            away_team="Arsenal",
            kickoff=datetime.now(),
            league="Premier League"
        )
        
        print(f"   ✅ FortressState créé")
        print(f"   📊 Match: {state.match_input.home_team} vs {state.match_input.away_team}")
        print(f"   📊 Should Continue: {state.should_continue()}")
        print(f"   📊 Current Node: {state.current_node}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return False


def run_all_tests():
    """Exécute tous les tests Phase 1."""
    print("\n" + "=" * 60)
    print("🏰 FORTRESS V3.8 - VALIDATION PHASE 1")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    tests = [
        ("CONFIG PATHS", test_config_paths),
        ("POSTGRESQL", test_postgres_connection),
        ("JSON LOADING", test_json_loading),
        ("UNIFIED LOADER", test_unified_loader),
        ("FRICTION MATRIX", test_friction_matrix),
        ("MARKET REGISTRY", test_market_registry),
        ("STATE DATACLASSES", test_state_dataclasses),
    ]
    
    results = {}
    
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n❌ ERREUR CRITIQUE dans {name}: {e}")
            results[name] = False
    
    # Résumé final
    print("\n" + "=" * 60)
    print("📋 RÉSUMÉ PHASE 1")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"   {status} - {name}")
    
    print(f"\n   📊 Score: {passed}/{total} tests passés")
    
    if passed == total:
        print("\n" + "=" * 60)
        print("🎉 PHASE 1 VALIDÉE - PRÊT POUR PHASE 2!")
        print("=" * 60)
        return True
    else:
        print("\n" + "=" * 60)
        print("⚠️  PHASE 1 INCOMPLÈTE - Corriger les erreurs")
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
