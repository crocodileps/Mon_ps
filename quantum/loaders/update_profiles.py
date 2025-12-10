#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║  UPDATE PROFILES - Synchronise team_dna_profiles avec defense_dna corrigé            ║
║  Version: 1.0                                                                        ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

Exécution: python3 /home/Mon_ps/quantum/loaders/update_profiles.py
"""

import json
from pathlib import Path
from datetime import datetime

DATA_ROOT = Path("/home/Mon_ps/data")
DEFENSE_FILE = DATA_ROOT / "defense_dna" / "team_defense_dna_v5_1_corrected.json"
PROFILES_FILE = DATA_ROOT / "team_dna_profiles_v2.json"
BACKUP_FILE = DATA_ROOT / f"team_dna_profiles_v2_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, path: Path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Sauvegardé: {path}")


def main():
    print("\n" + "🔄"*35)
    print("   UPDATE PROFILES - Synchronisation")
    print("🔄"*35)
    
    # Load
    print(f"\n📂 Chargement defense_dna corrigé...")
    defense_data = load_json(DEFENSE_FILE)
    
    # Create lookup by team_name
    defense_by_team = {d["team_name"]: d for d in defense_data}
    
    print(f"📂 Chargement profiles...")
    profiles = load_json(PROFILES_FILE)
    
    # Backup
    save_json(profiles, BACKUP_FILE)
    
    # Update
    updated = 0
    changes = []
    
    for team_name, profile in profiles.items():
        defense = defense_by_team.get(team_name)
        
        if not defense:
            continue
        
        # Update timing_profile
        old_timing = profile.get("timing_profile", "")
        new_timing = defense.get("timing_profile", "")
        
        if old_timing != new_timing and new_timing:
            profile["timing_profile"] = new_timing
            changes.append(f"{team_name}: {old_timing} → {new_timing}")
            updated += 1
        
        # Update metrics
        if "metrics" in profile:
            profile["metrics"]["resist_late"] = defense.get("resist_late", 0)
            profile["metrics"]["xga_late_pct"] = defense.get("xga_late_pct", 0)
        
        # Update fingerprint (defensive_timing_gk_homeaway)
        def_profile = profile.get("defensive_profile", "UNKNOWN")
        gk_profile = profile.get("gk_profile", "UNKNOWN")
        home_away = profile.get("home_away", "UNKNOWN")
        
        new_fingerprint = f"{def_profile}_{new_timing}_{gk_profile}_{home_away}"
        profile["fingerprint"] = new_fingerprint
    
    # Report
    print(f"\n📊 RAPPORT:")
    print(f"   Profiles mis à jour: {updated}")
    
    if changes:
        print(f"\n🔄 CHANGEMENTS:")
        for c in changes[:30]:
            print(f"   {c}")
        if len(changes) > 30:
            print(f"   ... et {len(changes) - 30} autres")
    
    # Save
    save_json(profiles, PROFILES_FILE)
    
    # Verify Genoa specifically
    genoa = profiles.get("Genoa", {})
    genoa_def = defense_by_team.get("Genoa", {})
    
    print(f"\n🔍 VÉRIFICATION GENOA:")
    print(f"   Profile timing: {genoa.get('timing_profile')}")
    print(f"   Defense timing: {genoa_def.get('timing_profile')}")
    print(f"   xGA late %: {genoa_def.get('xga_late_pct', 0):.1f}%")
    print(f"   xGA 76-90: {genoa_def.get('xga_76_90', 0):.2f}")
    
    print("\n✅ MISE À JOUR TERMINÉE")


if __name__ == "__main__":
    main()
