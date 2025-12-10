#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║  FIX DEFENSE DNA - Correction xGA 76-90 manquant                                     ║
║  Version: 1.0                                                                        ║
║  Problème: 100% des équipes ont xga_76_90 = 0 (bug scraping)                        ║
║  Solution: Recalculer à partir de xga_total - sum(autres périodes)                  ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

Exécution: python3 /home/Mon_ps/quantum/loaders/fix_defense_dna.py
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# ═══════════════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════════════

DATA_ROOT = Path("/home/Mon_ps/data")
DEFENSE_FILE = DATA_ROOT / "defense_dna" / "team_defense_dna_v5_1_corrected.json"
OUTPUT_FILE = DATA_ROOT / "defense_dna" / "team_defense_dna_v6_fixed.json"
BACKUP_FILE = DATA_ROOT / "defense_dna" / f"team_defense_dna_v5_1_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"


def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: Any, path: Path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Sauvegardé: {path}")


def fix_defense_data(data: List[Dict]) -> List[Dict]:
    """
    Corrige les données defense_dna:
    1. Calcule xga_76_90 manquant
    2. Recalcule les profiles timing
    3. Vérifie la cohérence
    """
    
    fixed_count = 0
    profile_changes = []
    
    for team in data:
        team_name = team.get("team_name", "Unknown")
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # FIX #1: Calculer xga_76_90 manquant
        # ═══════════════════════════════════════════════════════════════════════════════
        
        xga_total = team.get("xga_total", 0) or 0
        xga_0_15 = team.get("xga_0_15", 0) or 0
        xga_16_30 = team.get("xga_16_30", 0) or 0
        xga_31_45 = team.get("xga_31_45", 0) or 0
        xga_46_60 = team.get("xga_46_60", 0) or 0
        xga_61_75 = team.get("xga_61_75", 0) or 0
        xga_76_90_old = team.get("xga_76_90", 0) or 0
        
        # Calculer la période manquante
        sum_other = xga_0_15 + xga_16_30 + xga_31_45 + xga_46_60 + xga_61_75
        xga_76_90_calculated = max(0, xga_total - sum_other)
        
        # Update si différent
        if abs(xga_76_90_calculated - xga_76_90_old) > 0.01:
            team["xga_76_90"] = round(xga_76_90_calculated, 6)
            team["xga_76_90_source"] = "CALCULATED"  # Flag pour traçabilité
            fixed_count += 1
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # FIX #2: Recalculer les métriques timing
        # ═══════════════════════════════════════════════════════════════════════════════
        
        # Late % (76-90)
        if xga_total > 0:
            late_pct = (xga_76_90_calculated / xga_total) * 100
            team["xga_late_pct"] = round(late_pct, 2)
            
            # Early % (0-15)
            early_pct = (xga_0_15 / xga_total) * 100
            team["xga_early_pct"] = round(early_pct, 2)
            
            # First half % 
            first_half = xga_0_15 + xga_16_30 + xga_31_45
            first_half_pct = (first_half / xga_total) * 100
            team["xga_1h_pct_corrected"] = round(first_half_pct, 2)
            
            # Second half %
            second_half = xga_46_60 + xga_61_75 + xga_76_90_calculated
            second_half_pct = (second_half / xga_total) * 100
            team["xga_2h_pct_corrected"] = round(second_half_pct, 2)
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # FIX #3: Recalculer timing_profile
        # ═══════════════════════════════════════════════════════════════════════════════
        
        old_profile = team.get("timing_profile", "")
        new_profile = calculate_timing_profile(team, xga_76_90_calculated)
        
        if new_profile != old_profile:
            profile_changes.append({
                "team": team_name,
                "old": old_profile,
                "new": new_profile
            })
            team["timing_profile"] = new_profile
            team["timing_profile_old"] = old_profile  # Garder l'ancien pour référence
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # FIX #4: Recalculer resist_late
        # ═══════════════════════════════════════════════════════════════════════════════
        
        matches = team.get("matches_played", 0) or 1
        xga_76_90_per_90 = xga_76_90_calculated / matches
        
        # Resist late: 100 = parfait (0 xGA late), 0 = catastrophique (0.5+ xGA late/match)
        # Benchmark: ~0.25 xGA/match en période late est "normal"
        resist_late = max(0, min(100, 100 - (xga_76_90_per_90 / 0.5) * 100))
        team["resist_late"] = round(resist_late, 1)
    
    return data, fixed_count, profile_changes


def calculate_timing_profile(team: Dict, xga_76_90: float) -> str:
    """
    Calcule le timing_profile basé sur la distribution xGA.
    """
    
    xga_total = team.get("xga_total", 0) or 1  # Éviter division par 0
    
    xga_0_15 = team.get("xga_0_15", 0) or 0
    xga_16_30 = team.get("xga_16_30", 0) or 0
    xga_31_45 = team.get("xga_31_45", 0) or 0
    xga_46_60 = team.get("xga_46_60", 0) or 0
    xga_61_75 = team.get("xga_61_75", 0) or 0
    
    # Calculer les %
    early_pct = (xga_0_15 / xga_total) * 100
    late_pct = (xga_76_90 / xga_total) * 100
    first_half = xga_0_15 + xga_16_30 + xga_31_45
    first_half_pct = (first_half / xga_total) * 100
    
    # Déterminer le profile
    profiles = []
    
    # Early vulnerability (0-15 > 20%)
    if early_pct > 22:
        profiles.append("SLOW_STARTER")
    elif early_pct < 12:
        profiles.append("STRONG_START")
    
    # Late vulnerability (76-90 > 20%)
    if late_pct > 22:
        profiles.append("FADES_LATE")
    elif late_pct < 12:
        profiles.append("FINISHES_STRONG")
    
    # First half vulnerability (>55%)
    if first_half_pct > 58:
        profiles.append("FIRST_HALF_WEAK")
    elif first_half_pct < 42:
        profiles.append("SECOND_HALF_WEAK")
    
    # Default
    if not profiles:
        profiles.append("CONSISTENT")
    
    return "+".join(profiles)


def print_report(data: List[Dict], fixed_count: int, profile_changes: List[Dict]):
    """Affiche le rapport de correction."""
    
    print("\n" + "="*70)
    print("📊 RAPPORT DE CORRECTION")
    print("="*70)
    
    print(f"\n✅ Équipes corrigées: {fixed_count}/96")
    print(f"✅ Profiles modifiés: {len(profile_changes)}")
    
    # Stats sur les nouvelles valeurs xga_76_90
    xga_76_90_values = [t.get("xga_76_90", 0) for t in data]
    avg_xga_76_90 = sum(xga_76_90_values) / len(xga_76_90_values)
    max_xga_76_90 = max(xga_76_90_values)
    min_xga_76_90 = min(xga_76_90_values)
    
    print(f"\n📈 Nouvelles valeurs xGA 76-90:")
    print(f"   Moyenne: {avg_xga_76_90:.2f}")
    print(f"   Min: {min_xga_76_90:.2f}")
    print(f"   Max: {max_xga_76_90:.2f}")
    
    # Distribution late_pct
    late_pcts = [t.get("xga_late_pct", 0) for t in data]
    avg_late_pct = sum(late_pcts) / len(late_pcts)
    
    print(f"\n📈 Distribution late % (76-90):")
    print(f"   Moyenne: {avg_late_pct:.1f}%")
    
    # Top 10 équipes qui fade late
    sorted_by_late = sorted(data, key=lambda x: x.get("xga_late_pct", 0), reverse=True)[:10]
    print(f"\n🚨 TOP 10 équipes qui FADES LATE:")
    for t in sorted_by_late:
        print(f"   {t['team_name']}: {t.get('xga_late_pct', 0):.1f}% ({t.get('xga_76_90', 0):.2f} xGA)")
    
    # Profile changes
    if profile_changes:
        print(f"\n🔄 CHANGEMENTS DE PROFILE ({len(profile_changes)}):")
        for change in profile_changes[:20]:  # Top 20
            print(f"   {change['team']}: {change['old']} → {change['new']}")
    
    # Validation
    print(f"\n✅ VALIDATION:")
    
    # Check timing sum now matches total
    mismatches = []
    for t in data:
        xga_total = t.get("xga_total", 0) or 0
        timing_sum = (
            (t.get("xga_0_15", 0) or 0) +
            (t.get("xga_16_30", 0) or 0) +
            (t.get("xga_31_45", 0) or 0) +
            (t.get("xga_46_60", 0) or 0) +
            (t.get("xga_61_75", 0) or 0) +
            (t.get("xga_76_90", 0) or 0)
        )
        if xga_total > 0:
            diff_pct = abs((timing_sum - xga_total) / xga_total) * 100
            if diff_pct > 1:  # Plus de 1% d'écart
                mismatches.append((t["team_name"], diff_pct))
    
    if mismatches:
        print(f"   ⚠️ {len(mismatches)} équipes avec encore un mismatch")
        for team, pct in mismatches[:5]:
            print(f"      {team}: {pct:.1f}%")
    else:
        print(f"   ✅ Toutes les équipes: timing_sum ≈ xga_total")


def main():
    print("\n" + "🔧"*35)
    print("   FIX DEFENSE DNA - xGA 76-90")
    print("🔧"*35)
    
    # Load
    print(f"\n📂 Chargement: {DEFENSE_FILE}")
    data = load_json(DEFENSE_FILE)
    print(f"   {len(data)} équipes chargées")
    
    # Backup
    print(f"\n💾 Backup: {BACKUP_FILE}")
    save_json(data, BACKUP_FILE)
    
    # Fix
    print(f"\n🔧 Correction en cours...")
    fixed_data, fixed_count, profile_changes = fix_defense_data(data)
    
    # Report
    print_report(fixed_data, fixed_count, profile_changes)
    
    # Save
    print(f"\n💾 Sauvegarde: {OUTPUT_FILE}")
    save_json(fixed_data, OUTPUT_FILE)
    
    # Also update the original file
    print(f"\n💾 Mise à jour fichier original: {DEFENSE_FILE}")
    save_json(fixed_data, DEFENSE_FILE)
    
    print("\n" + "="*70)
    print("✅ CORRECTION TERMINÉE")
    print("="*70)
    print(f"\n📋 Prochaines étapes:")
    print(f"   1. Ré-exécuter data_audit.py pour valider")
    print(f"   2. Régénérer team_dna_profiles_v2.json avec les nouveaux profiles")
    print(f"   3. Les loaders utiliseront automatiquement les données corrigées")


if __name__ == "__main__":
    main()
