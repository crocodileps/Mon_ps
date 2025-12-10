#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║  TEST LOADERS - Validation avec JSON réels                                           ║
║  Version: 2.0                                                                        ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

Exécution: python3 /home/Mon_ps/quantum/loaders/test_loaders.py
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Ajouter le path
sys.path.insert(0, "/home/Mon_ps")

# ═══════════════════════════════════════════════════════════════════════════════════════
# PATHS DES FICHIERS RÉELS
# ═══════════════════════════════════════════════════════════════════════════════════════

DATA_ROOT = Path("/home/Mon_ps/data")
QUANTUM_V2 = DATA_ROOT / "quantum_v2"

FILES = {
    "context": QUANTUM_V2 / "teams_context_dna.json",
    "defense": DATA_ROOT / "defense_dna" / "team_defense_dna_v5_1_corrected.json",
    "goalkeeper": DATA_ROOT / "goalkeeper_dna" / "goalkeeper_dna_v4_4_by_team.json",
    "profiles": DATA_ROOT / "team_dna_profiles_v2.json",
}


def load_json(path: Path) -> Optional[Dict]:
    """Charge un fichier JSON."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Erreur chargement {path}: {e}")
        return None


def test_file_structure():
    """Test la structure des fichiers JSON."""
    print("\n" + "="*70)
    print("📁 TEST STRUCTURE DES FICHIERS JSON")
    print("="*70)
    
    for name, path in FILES.items():
        print(f"\n🔍 {name.upper()}: {path}")
        
        if not path.exists():
            print(f"   ❌ Fichier non trouvé!")
            continue
        
        data = load_json(path)
        if data is None:
            continue
        
        # Type
        data_type = "LIST" if isinstance(data, list) else "DICT"
        print(f"   📊 Type: {data_type}")
        
        if isinstance(data, list):
            print(f"   📊 Éléments: {len(data)}")
            if data:
                first = data[0]
                print(f"   📊 Clés premier élément: {list(first.keys())[:10]}...")
                if "team_name" in first:
                    print(f"   📊 Exemple team: {first.get('team_name')}")
        else:
            print(f"   📊 Équipes: {len(data)}")
            teams = list(data.keys())[:5]
            print(f"   📊 Exemples: {teams}")
            
            # Structure du premier
            first_team = list(data.keys())[0]
            first_data = data[first_team]
            print(f"   📊 Clés de '{first_team}': {list(first_data.keys())[:10]}...")


def test_context_loading():
    """Test le chargement des données Context."""
    print("\n" + "="*70)
    print("🎯 TEST CONTEXT DNA LOADING")
    print("="*70)
    
    data = load_json(FILES["context"])
    if not data:
        return
    
    # Test avec Arsenal
    test_team = "Arsenal"
    if test_team not in data:
        test_team = list(data.keys())[0]
    
    team_data = data[test_team]
    print(f"\n📊 Équipe test: {test_team}")
    
    # Extraire les métriques
    record = team_data.get("record", {})
    history = team_data.get("history", {})
    variance = team_data.get("variance", {})
    momentum = team_data.get("momentum_dna", {})
    context_dna = team_data.get("context_dna", {})
    
    print(f"\n   📈 RECORD:")
    print(f"      Matches: {team_data.get('matches', 0)}")
    print(f"      W/D/L: {record.get('wins', 0)}/{record.get('draws', 0)}/{record.get('losses', 0)}")
    print(f"      Points: {record.get('points', 0)}")
    print(f"      GF/GA: {record.get('goals_for', 0)}/{record.get('goals_against', 0)}")
    
    print(f"\n   📊 HISTORY (xG):")
    print(f"      xG: {history.get('xg', 0)} | xGA: {history.get('xga', 0)}")
    print(f"      xG/90: {history.get('xg_90', 0)} | xGA/90: {history.get('xga_90', 0)}")
    print(f"      PPDA: {history.get('ppda', 0)} | Style: {history.get('pressing_style', 'N/A')}")
    
    print(f"\n   🎲 VARIANCE:")
    print(f"      xG overperf: {variance.get('xg_overperformance', 0)}")
    print(f"      xGA overperf: {variance.get('xga_overperformance', 0)}")
    print(f"      Luck index: {variance.get('luck_index', 0)}")
    
    print(f"\n   🔥 MOMENTUM:")
    print(f"      Form L5: {momentum.get('form_last_5', 'N/A')}")
    print(f"      Points L5: {momentum.get('points_last_5', 0)}")
    
    # Timing
    timing = context_dna.get("timing", {})
    if timing:
        print(f"\n   ⏱️ TIMING (xG par période):")
        for period, pdata in timing.items():
            xg = pdata.get("xG", 0)
            goals = pdata.get("goals", 0)
            print(f"      {period}: xG={xg:.2f}, goals={goals}")
    
    print("\n   ✅ Context data structure OK!")


def test_defense_loading():
    """Test le chargement des données Defense."""
    print("\n" + "="*70)
    print("🛡️ TEST DEFENSE DNA LOADING")
    print("="*70)
    
    data = load_json(FILES["defense"])
    if not data:
        return
    
    # C'est une LISTE
    print(f"\n📊 Total équipes: {len(data)}")
    
    # Chercher Arsenal
    team_data = None
    for item in data:
        if item.get("team_name") == "Arsenal":
            team_data = item
            break
    
    if not team_data:
        team_data = data[0]
    
    team_name = team_data.get("team_name", "Unknown")
    print(f"\n📊 Équipe test: {team_name}")
    
    print(f"\n   🛡️ CORE DEFENSE:")
    print(f"      League: {team_data.get('league', 'N/A')}")
    print(f"      Matches: {team_data.get('matches_played', 0)}")
    print(f"      xGA total: {team_data.get('xga_total', 0):.2f}")
    print(f"      GA total: {team_data.get('ga_total', 0)}")
    print(f"      xGA/90: {team_data.get('xga_per_90', 0):.3f}")
    print(f"      Clean sheets: {team_data.get('clean_sheets', 0)} ({team_data.get('cs_pct', 0):.1f}%)")
    
    print(f"\n   🏠 HOME/AWAY:")
    print(f"      xGA home: {team_data.get('xga_home', 0):.2f} | away: {team_data.get('xga_away', 0):.2f}")
    print(f"      CS% home: {team_data.get('cs_pct_home', 0):.1f}% | away: {team_data.get('cs_pct_away', 0):.1f}%")
    
    print(f"\n   ⏱️ TIMING xGA:")
    print(f"      0-15: {team_data.get('xga_0_15', 0):.2f}")
    print(f"      16-30: {team_data.get('xga_16_30', 0):.2f}")
    print(f"      31-45: {team_data.get('xga_31_45', 0):.2f}")
    print(f"      46-60: {team_data.get('xga_46_60', 0):.2f}")
    print(f"      61-75: {team_data.get('xga_61_75', 0):.2f}")
    print(f"      76-90: {team_data.get('xga_76_90', 0):.2f}")
    
    print(f"\n   📍 ZONES:")
    print(f"      Six yard: {team_data.get('xga_six_yard', 0):.2f}")
    print(f"      Penalty area: {team_data.get('xga_penalty_area', 0):.2f}")
    print(f"      Outside box: {team_data.get('xga_outside_box', 0):.2f}")
    
    print(f"\n   🎯 SET PIECES:")
    print(f"      Open play: {team_data.get('xga_open_play', 0):.2f}")
    print(f"      Set piece: {team_data.get('xga_set_piece', 0):.2f}")
    print(f"      Corner: {team_data.get('xga_corner', 0):.2f}")
    print(f"      Vuln %: {team_data.get('set_piece_vuln_pct', 0):.1f}%")
    
    print(f"\n   📊 PROFILES:")
    print(f"      Defense: {team_data.get('defense_profile', 'N/A')}")
    print(f"      Timing: {team_data.get('timing_profile', 'N/A')}")
    print(f"      Home/Away: {team_data.get('home_away_defense_profile', 'N/A')}")
    print(f"      Set piece: {team_data.get('set_piece_profile', 'N/A')}")
    
    print(f"\n   💪 RESIST METRICS:")
    print(f"      Global: {team_data.get('resist_global', 0)}")
    print(f"      Aerial: {team_data.get('resist_aerial', 0)}")
    print(f"      Longshot: {team_data.get('resist_longshot', 0)}")
    print(f"      Open play: {team_data.get('resist_open_play', 0)}")
    
    print("\n   ✅ Defense data structure OK!")


def test_goalkeeper_loading():
    """Test le chargement des données Goalkeeper."""
    print("\n" + "="*70)
    print("🧤 TEST GOALKEEPER DNA LOADING")
    print("="*70)
    
    data = load_json(FILES["goalkeeper"])
    if not data:
        return
    
    print(f"\n📊 Total équipes: {len(data)}")
    
    # Test avec Lyon (premier dans le fichier)
    test_team = "Lyon"
    if test_team not in data:
        test_team = list(data.keys())[0]
    
    team_data = data[test_team]
    print(f"\n📊 Équipe test: {test_team}")
    
    print(f"\n   🧤 CORE:")
    print(f"      Goalkeeper: {team_data.get('goalkeeper', 'N/A')}")
    print(f"      Performance: {team_data.get('gk_performance', 0):.2f}")
    print(f"      Percentile: {team_data.get('gk_percentile', 0)}")
    print(f"      Save rate: {team_data.get('save_rate', 0):.1f}%")
    print(f"      Shots faced: {team_data.get('shots_faced', 0)}")
    print(f"      Saves: {team_data.get('saves', 0)}")
    print(f"      Goals conceded: {team_data.get('goals_conceded', 0)}")
    
    # Difficulty analysis
    diff = team_data.get("difficulty_analysis", {})
    if diff:
        print(f"\n   📊 DIFFICULTY ANALYSIS:")
        for level in ["easy", "medium", "hard", "very_hard"]:
            level_data = diff.get(level, {})
            sr = level_data.get("sr", 0)
            vs_exp = level_data.get("vs_expected", 0)
            sample = level_data.get("sample", 0)
            conf = level_data.get("confidence", "N/A")
            print(f"      {level.upper()}: SR={sr:.1f}%, vs_exp={vs_exp:+.1f}, n={sample} ({conf})")
        
        print(f"      Big save ability: {diff.get('big_save_ability', 'N/A')}")
        print(f"      Routine reliability: {diff.get('routine_reliability', 'N/A')}")
    
    # Situation analysis
    sit = team_data.get("situation_analysis", {})
    if sit:
        print(f"\n   🎯 SITUATION ANALYSIS:")
        for situation in ["open_play", "corners", "set_pieces", "penalties"]:
            sit_data = sit.get(situation, {})
            sr = sit_data.get("sr", 0)
            vs_bench = sit_data.get("vs_benchmark", 0)
            sample = sit_data.get("sample", 0)
            print(f"      {situation}: SR={sr:.1f}%, vs_bench={vs_bench:+.1f}, n={sample}")
        
        print(f"      Strongest: {sit.get('strongest', 'N/A')}")
        print(f"      Weakest: {sit.get('weakest', 'N/A')}")
    
    # Timing analysis
    timing = team_data.get("timing_analysis", {}).get("periods", {})
    if timing:
        print(f"\n   ⏱️ TIMING ANALYSIS:")
        for period, pdata in timing.items():
            sr = pdata.get("save_rate", 0)
            vs_base = pdata.get("vs_baseline", 0)
            sample = pdata.get("sample", 0)
            print(f"      {period}: SR={sr:.1f}%, vs_base={vs_base:+.1f}, n={sample}")
    
    print("\n   ✅ Goalkeeper data structure OK!")


def test_profiles_loading():
    """Test le chargement des profils fusionnés."""
    print("\n" + "="*70)
    print("📊 TEST TEAM DNA PROFILES LOADING")
    print("="*70)
    
    data = load_json(FILES["profiles"])
    if not data:
        return
    
    print(f"\n📊 Total équipes: {len(data)}")
    
    # Test avec Arsenal
    test_team = "Arsenal"
    if test_team not in data:
        test_team = list(data.keys())[0]
    
    team_data = data[test_team]
    print(f"\n📊 Équipe test: {test_team}")
    
    print(f"\n   📊 PROFILES:")
    print(f"      League: {team_data.get('league', 'N/A')}")
    print(f"      Fingerprint: {team_data.get('fingerprint', 'N/A')}")
    print(f"      Defensive: {team_data.get('defensive_profile', 'N/A')}")
    print(f"      Timing: {team_data.get('timing_profile', 'N/A')}")
    print(f"      GK: {team_data.get('gk_profile', 'N/A')}")
    print(f"      Home/Away: {team_data.get('home_away', 'N/A')}")
    
    metrics = team_data.get("metrics", {})
    if metrics:
        print(f"\n   📈 METRICS:")
        print(f"      xGA/90: {metrics.get('xga_90', 0):.3f}")
        print(f"      GA/90: {metrics.get('ga_90', 0):.3f}")
        print(f"      CS%: {metrics.get('cs_pct', 0):.1f}%")
        print(f"      Overperform: {metrics.get('overperform', 0):.2f}")
        print(f"      Resist global: {metrics.get('resist_global', 0)}")
        print(f"      Late %: {metrics.get('late_pct', 0):.1f}%")
        print(f"      GK percentile: {metrics.get('gk_percentile', 0)}")
    
    markets = team_data.get("profitable_markets", [])
    if markets:
        print(f"\n   💰 PROFITABLE MARKETS:")
        for m in markets[:3]:
            print(f"      • {m.get('market')}: +{m.get('edge_pct', 0):.1f}% ({m.get('confidence')})")
    
    avoid = team_data.get("avoid_markets", [])
    if avoid:
        print(f"\n   🚫 AVOID MARKETS:")
        for m in avoid[:3]:
            print(f"      • {m}")
    
    print("\n   ✅ Profiles data structure OK!")


def test_quantum_imports():
    """Test les imports quantum."""
    print("\n" + "="*70)
    print("🔧 TEST QUANTUM IMPORTS")
    print("="*70)
    
    try:
        from quantum.models import (
            TeamDNA, ContextDNA, DefenseDNA, GoalkeeperDNA,
            VarianceDNA, ExploitProfile, CoachDNA
        )
        print("   ✅ Models imports OK")
    except ImportError as e:
        print(f"   ❌ Models import error: {e}")
        return
    
    try:
        from quantum.loaders import (
            load_team, load_json, normalize_team_name,
            get_team_key, safe_float, safe_int
        )
        print("   ✅ Loaders imports OK")
    except ImportError as e:
        print(f"   ❌ Loaders import error: {e}")
        return
    
    # Test normalize
    tests = [
        ("man utd", "Manchester United"),
        ("spurs", "Tottenham"),
        ("psg", "PSG"),
        ("bayern", "Bayern München"),
    ]
    
    print("\n   🔄 Test normalisation:")
    for alias, expected in tests:
        result = normalize_team_name(alias)
        status = "✅" if result == expected else "⚠️"
        print(f"      {status} '{alias}' → '{result}'")


def main():
    """Exécute tous les tests."""
    print("\n" + "🚀"*35)
    print("   TEST DES LOADERS QUANTUM - JSON RÉELS")
    print("🚀"*35)
    
    test_file_structure()
    test_context_loading()
    test_defense_loading()
    test_goalkeeper_loading()
    test_profiles_loading()
    test_quantum_imports()
    
    print("\n" + "="*70)
    print("✅ TESTS TERMINÉS")
    print("="*70)
    print("\nProchaine étape: Adapter les loaders aux structures réelles")


if __name__ == "__main__":
    main()
