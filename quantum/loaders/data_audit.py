#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║  DATA AUDIT - Détection d'incohérences Hedge Fund Style                              ║
║  Version: 1.0                                                                        ║
║  "Chercher les incohérences, pas les confirmations"                                  ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

Exécution: python3 /home/Mon_ps/quantum/loaders/data_audit.py
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# ═══════════════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════════════

DATA_ROOT = Path("/home/Mon_ps/data")
QUANTUM_V2 = DATA_ROOT / "quantum_v2"

FILES = {
    "context": QUANTUM_V2 / "teams_context_dna.json",
    "defense": DATA_ROOT / "defense_dna" / "team_defense_dna_v5_1_corrected.json",
    "goalkeeper": DATA_ROOT / "goalkeeper_dna" / "goalkeeper_dna_v4_4_by_team.json",
    "profiles": DATA_ROOT / "team_dna_profiles_v2.json",
}

# Seuils d'alerte
TOLERANCE_PCT = 5.0  # Écart acceptable en %
REGRESSION_THRESHOLD = 30.0  # % de surperformance avant alerte
MIN_SAMPLE_SIZE = 5  # Minimum pour confiance


class Severity(Enum):
    CRITICAL = "🚨 CRITICAL"
    WARNING = "⚠️ WARNING"
    INFO = "ℹ️ INFO"


@dataclass
class Issue:
    """Une incohérence détectée."""
    team: str
    category: str
    severity: Severity
    description: str
    source_a: str
    value_a: Any
    source_b: str
    value_b: Any
    delta: Optional[float] = None
    recommendation: str = ""
    
    def __str__(self):
        delta_str = f" (Δ={self.delta:+.1f}%)" if self.delta else ""
        return f"{self.severity.value} [{self.team}] {self.category}: {self.description}{delta_str}"


@dataclass 
class TeamAudit:
    """Résultat d'audit pour une équipe."""
    team: str
    issues: List[Issue] = field(default_factory=list)
    regression_signals: List[str] = field(default_factory=list)
    exploitable_edges: List[str] = field(default_factory=list)
    data_quality_score: float = 100.0
    
    @property
    def has_critical(self) -> bool:
        return any(i.severity == Severity.CRITICAL for i in self.issues)
    
    @property
    def issue_count(self) -> int:
        return len(self.issues)


# ═══════════════════════════════════════════════════════════════════════════════════════
# LOADERS
# ═══════════════════════════════════════════════════════════════════════════════════════

def load_json(path: Path) -> Optional[Dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Erreur: {path}: {e}")
        return None


def load_all_data() -> Dict[str, Any]:
    """Charge toutes les sources de données."""
    data = {}
    
    for name, path in FILES.items():
        if path.exists():
            data[name] = load_json(path)
        else:
            print(f"⚠️ Fichier manquant: {path}")
            data[name] = None
    
    return data


# ═══════════════════════════════════════════════════════════════════════════════════════
# AUDIT FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════════════

def audit_timing_consistency(team: str, defense_data: Dict) -> List[Issue]:
    """
    Vérifie que sum(timing_periods) ≈ total.
    CORRECTION #3: assert sum(timing_periods) ≈ total
    """
    issues = []
    
    # xGA timing
    timing_sum = sum([
        defense_data.get("xga_0_15", 0) or 0,
        defense_data.get("xga_16_30", 0) or 0,
        defense_data.get("xga_31_45", 0) or 0,
        defense_data.get("xga_46_60", 0) or 0,
        defense_data.get("xga_61_75", 0) or 0,
        defense_data.get("xga_76_90", 0) or 0,
    ])
    
    xga_total = defense_data.get("xga_total", 0) or 0
    
    if xga_total > 0:
        delta_pct = ((timing_sum - xga_total) / xga_total) * 100
        
        if abs(delta_pct) > TOLERANCE_PCT:
            severity = Severity.CRITICAL if abs(delta_pct) > 20 else Severity.WARNING
            
            issues.append(Issue(
                team=team,
                category="TIMING_MISMATCH",
                severity=severity,
                description=f"Sum of timing periods ≠ xGA total",
                source_a="sum(xga_periods)",
                value_a=f"{timing_sum:.2f}",
                source_b="xga_total",
                value_b=f"{xga_total:.2f}",
                delta=delta_pct,
                recommendation="Vérifier scraping 76-90 min (peut être 76+ mal parsé)"
            ))
    
    # Check for suspicious zeros
    if defense_data.get("xga_76_90", 0) == 0 and xga_total > 5:
        issues.append(Issue(
            team=team,
            category="SUSPICIOUS_ZERO",
            severity=Severity.CRITICAL,
            description="xGA 76-90 = 0 malgré xGA total significatif",
            source_a="xga_76_90",
            value_a="0",
            source_b="xga_total",
            value_b=f"{xga_total:.2f}",
            recommendation="CORRECTION #1: Vérifier si 76+ est mappé vers 76-90"
        ))
    
    return issues


def audit_profile_vs_data(team: str, defense_data: Dict, profile_data: Dict) -> List[Issue]:
    """
    Vérifie cohérence entre profiles et données brutes.
    CORRECTION #2: Recalculer les profiles avec les vraies données
    """
    issues = []
    
    if not profile_data:
        return issues
    
    timing_profile = profile_data.get("timing_profile", "")
    
    # Check FADES_LATE vs actual late xGA
    if "FADES_LATE" in timing_profile or "LATE" in timing_profile:
        xga_76_90 = defense_data.get("xga_76_90", 0) or 0
        xga_total = defense_data.get("xga_total", 0) or 0
        
        if xga_total > 0:
            late_pct = (xga_76_90 / xga_total) * 100
            
            # Si profile dit "fades late" mais xGA late est faible/zero
            if late_pct < 10:  # Moins de 10% en fin de match
                issues.append(Issue(
                    team=team,
                    category="PROFILE_CONTRADICTION",
                    severity=Severity.CRITICAL,
                    description=f"Profile '{timing_profile}' contredit par xGA_76_90",
                    source_a="timing_profile",
                    value_a=timing_profile,
                    source_b="xga_76_90 %",
                    value_b=f"{late_pct:.1f}%",
                    recommendation="CORRECTION #2: Recalculer profile avec données corrigées"
                ))
    
    # Check defensive profile vs actual xGA
    def_profile = profile_data.get("defensive_profile", "")
    xga_90 = defense_data.get("xga_per_90", 0) or 0
    
    profile_expected_ranges = {
        "FORTRESS": (0, 0.9),
        "SOLID": (0.8, 1.2),
        "AVERAGE": (1.1, 1.5),
        "LEAKY": (1.4, 2.0),
        "CATASTROPHIC": (1.8, 99),
    }
    
    if def_profile in profile_expected_ranges:
        min_xga, max_xga = profile_expected_ranges[def_profile]
        if not (min_xga <= xga_90 <= max_xga):
            issues.append(Issue(
                team=team,
                category="PROFILE_MISMATCH",
                severity=Severity.WARNING,
                description=f"Profile '{def_profile}' ne correspond pas à xGA/90",
                source_a="defensive_profile",
                value_a=def_profile,
                source_b="xga_per_90",
                value_b=f"{xga_90:.3f}",
                recommendation=f"Expected range for {def_profile}: {min_xga}-{max_xga}"
            ))
    
    return issues


def audit_regression_signals(team: str, context_data: Dict, defense_data: Dict) -> Tuple[List[Issue], List[str]]:
    """
    Détecte les signaux de régression (sur/sous-performance non soutenable).
    """
    issues = []
    signals = []
    
    # === OFFENSIVE REGRESSION ===
    if context_data:
        timing = context_data.get("context_dna", {}).get("timing", {})
        
        for period, pdata in timing.items():
            xg = pdata.get("xG", 0) or 0
            goals = pdata.get("goals", 0) or 0
            
            if xg > 0:
                overperf_pct = ((goals - xg) / xg) * 100
                
                if overperf_pct > REGRESSION_THRESHOLD:
                    signals.append(f"FADE Goals {period}: +{overperf_pct:.0f}% overperf (xG={xg:.1f}, goals={goals})")
                    
                    if overperf_pct > 50:
                        issues.append(Issue(
                            team=team,
                            category="REGRESSION_SIGNAL",
                            severity=Severity.WARNING,
                            description=f"Surperformance non-soutenable {period}",
                            source_a="xG",
                            value_a=f"{xg:.2f}",
                            source_b="Goals réels",
                            value_b=str(goals),
                            delta=overperf_pct,
                            recommendation=f"FADE: Régression attendue période {period}"
                        ))
                
                elif overperf_pct < -REGRESSION_THRESHOLD:
                    signals.append(f"BACK Goals {period}: {overperf_pct:.0f}% underperf (chance de rebond)")
    
    # === DEFENSIVE REGRESSION ===
    if defense_data:
        xga_total = defense_data.get("xga_total", 0) or 0
        ga_total = defense_data.get("ga_total", 0) or 0
        overperf = defense_data.get("defense_overperform", 0) or 0
        
        if xga_total > 0:
            overperf_pct = (overperf / xga_total) * 100
            
            if overperf > 2:  # Concède 2+ buts de moins que xGA
                signals.append(f"FADE Clean Sheet: +{overperf:.1f} buts chanceux (régression attendue)")
                
                if overperf > 4:
                    issues.append(Issue(
                        team=team,
                        category="DEFENSIVE_LUCK",
                        severity=Severity.WARNING,
                        description=f"Surperformance défensive massive",
                        source_a="xGA",
                        value_a=f"{xga_total:.2f}",
                        source_b="GA réels",
                        value_b=str(ga_total),
                        delta=overperf_pct,
                        recommendation="FADE: Clean Sheet odds probablement trop courtes"
                    ))
            
            elif overperf < -2:  # Concède 2+ buts de plus que xGA
                signals.append(f"BACK Clean Sheet: {overperf:.1f} buts malchanceux (rebond attendu)")
    
    return issues, signals


def audit_form_vs_season(team: str, context_data: Dict) -> Tuple[List[Issue], List[str]]:
    """
    Compare forme récente vs moyenne saison.
    """
    issues = []
    edges = []
    
    if not context_data:
        return issues, edges
    
    record = context_data.get("record", {})
    momentum = context_data.get("momentum_dna", {})
    
    matches = context_data.get("matches", 0) or 0
    points = record.get("points", 0) or 0
    points_l5 = momentum.get("points_last_5", 0) or 0
    
    if matches >= 10:
        ppg_season = points / matches
        ppg_l5 = points_l5 / 5
        
        delta_ppg = ppg_l5 - ppg_season
        delta_pct = (delta_ppg / ppg_season) * 100 if ppg_season > 0 else 0
        
        if delta_pct < -20:  # Forme en baisse significative
            edges.append(f"FADE: Forme en baisse ({ppg_season:.2f} → {ppg_l5:.2f} PPG, {delta_pct:.0f}%)")
            
            issues.append(Issue(
                team=team,
                category="FORM_DECLINE",
                severity=Severity.INFO,
                description="Forme récente significativement en baisse",
                source_a="PPG saison",
                value_a=f"{ppg_season:.2f}",
                source_b="PPG L5",
                value_b=f"{ppg_l5:.2f}",
                delta=delta_pct,
                recommendation="Marché peut encore pricer la forme passée"
            ))
        
        elif delta_pct > 20:  # Forme en hausse
            edges.append(f"BACK: Forme en hausse ({ppg_season:.2f} → {ppg_l5:.2f} PPG, +{delta_pct:.0f}%)")
    
    return issues, edges


def audit_home_away_disparity(team: str, defense_data: Dict) -> List[str]:
    """
    Détecte les écarts home/away exploitables.
    """
    edges = []
    
    if not defense_data:
        return edges
    
    xga_home = defense_data.get("xga_home", 0) or 0
    xga_away = defense_data.get("xga_away", 0) or 0
    matches_home = defense_data.get("matches_home", 0) or 0
    matches_away = defense_data.get("matches_away", 0) or 0
    cs_pct_home = defense_data.get("cs_pct_home", 0) or 0
    cs_pct_away = defense_data.get("cs_pct_away", 0) or 0
    
    if matches_home >= 3 and matches_away >= 3:
        xga_90_home = xga_home / matches_home
        xga_90_away = xga_away / matches_away
        
        if xga_90_away > 0:
            ratio = xga_90_away / xga_90_home if xga_90_home > 0 else 99
            
            if ratio > 1.5:  # 50%+ plus de xGA away
                edges.append(f"HOME FORTRESS: xGA/90 home={xga_90_home:.2f} vs away={xga_90_away:.2f} (ratio {ratio:.1f}x)")
                edges.append(f"  → BACK Clean Sheet HOME (CS%={cs_pct_home:.0f}%)")
                edges.append(f"  → FADE Clean Sheet AWAY (CS%={cs_pct_away:.0f}%)")
            
            elif ratio < 0.7:  # Meilleur away
                edges.append(f"AWAY STRENGTH: xGA/90 away={xga_90_away:.2f} vs home={xga_90_home:.2f}")
    
    return edges


def audit_goalkeeper_consistency(team: str, gk_data: Dict, defense_data: Dict) -> List[Issue]:
    """
    Vérifie cohérence GK vs données défensives.
    """
    issues = []
    
    if not gk_data or not defense_data:
        return issues
    
    gk_goals_conceded = gk_data.get("goals_conceded", 0) or 0
    def_goals_conceded = defense_data.get("ga_total", 0) or 0
    
    if abs(gk_goals_conceded - def_goals_conceded) > 2:
        issues.append(Issue(
            team=team,
            category="GK_DEFENSE_MISMATCH",
            severity=Severity.WARNING,
            description="Goals conceded differ between GK and defense data",
            source_a="GK goals_conceded",
            value_a=str(gk_goals_conceded),
            source_b="Defense ga_total",
            value_b=str(def_goals_conceded),
            recommendation="Vérifier si GK a joué tous les matchs"
        ))
    
    return issues


# ═══════════════════════════════════════════════════════════════════════════════════════
# MAIN AUDIT
# ═══════════════════════════════════════════════════════════════════════════════════════

def audit_team(team: str, all_data: Dict) -> TeamAudit:
    """Audit complet d'une équipe."""
    
    audit = TeamAudit(team=team)
    
    # Get team data from each source
    context_data = all_data.get("context", {}).get(team, {}) if all_data.get("context") else {}
    
    # Defense is a LIST, need to find by team_name
    defense_data = {}
    if all_data.get("defense"):
        for item in all_data["defense"]:
            if item.get("team_name") == team:
                defense_data = item
                break
    
    gk_data = all_data.get("goalkeeper", {}).get(team, {}) if all_data.get("goalkeeper") else {}
    profile_data = all_data.get("profiles", {}).get(team, {}) if all_data.get("profiles") else {}
    
    # Run all audits
    if defense_data:
        audit.issues.extend(audit_timing_consistency(team, defense_data))
        audit.issues.extend(audit_profile_vs_data(team, defense_data, profile_data))
        audit.exploitable_edges.extend(audit_home_away_disparity(team, defense_data))
    
    if context_data:
        reg_issues, reg_signals = audit_regression_signals(team, context_data, defense_data)
        audit.issues.extend(reg_issues)
        audit.regression_signals.extend(reg_signals)
        
        form_issues, form_edges = audit_form_vs_season(team, context_data)
        audit.issues.extend(form_issues)
        audit.exploitable_edges.extend(form_edges)
    
    if gk_data and defense_data:
        audit.issues.extend(audit_goalkeeper_consistency(team, gk_data, defense_data))
    
    # Calculate data quality score
    critical_count = sum(1 for i in audit.issues if i.severity == Severity.CRITICAL)
    warning_count = sum(1 for i in audit.issues if i.severity == Severity.WARNING)
    audit.data_quality_score = max(0, 100 - (critical_count * 20) - (warning_count * 5))
    
    return audit


def run_full_audit(teams: List[str] = None) -> Dict[str, TeamAudit]:
    """Exécute l'audit sur toutes les équipes ou une liste spécifique."""
    
    print("\n" + "🔍"*35)
    print("   AUDIT HEDGE FUND - DÉTECTION D'INCOHÉRENCES")
    print("🔍"*35)
    
    all_data = load_all_data()
    
    # Get all team names
    if teams is None:
        teams = set()
        
        if all_data.get("context"):
            teams.update(all_data["context"].keys())
        
        if all_data.get("defense"):
            for item in all_data["defense"]:
                teams.add(item.get("team_name", ""))
        
        if all_data.get("profiles"):
            teams.update(all_data["profiles"].keys())
        
        teams.discard("")
        teams = sorted(teams)
    
    results = {}
    critical_teams = []
    
    for team in teams:
        audit = audit_team(team, all_data)
        results[team] = audit
        
        if audit.has_critical:
            critical_teams.append(team)
    
    return results, critical_teams


def print_audit_report(results: Dict[str, TeamAudit], critical_teams: List[str]):
    """Affiche le rapport d'audit."""
    
    print("\n" + "="*70)
    print("📊 RAPPORT D'AUDIT")
    print("="*70)
    
    # Summary
    total_issues = sum(a.issue_count for a in results.values())
    total_critical = sum(1 for a in results.values() if a.has_critical)
    
    print(f"\n📈 RÉSUMÉ:")
    print(f"   Équipes auditées: {len(results)}")
    print(f"   Issues totales: {total_issues}")
    print(f"   Équipes avec CRITICAL: {total_critical}")
    
    # Critical teams detail
    if critical_teams:
        print(f"\n🚨 ÉQUIPES AVEC PROBLÈMES CRITIQUES:")
        print("-"*70)
        
        for team in critical_teams:
            audit = results[team]
            print(f"\n🔴 {team} (Quality Score: {audit.data_quality_score:.0f}/100)")
            
            for issue in audit.issues:
                if issue.severity == Severity.CRITICAL:
                    print(f"   {issue}")
                    print(f"      → {issue.recommendation}")
    
    # Top regression signals
    print(f"\n⚠️ TOP SIGNAUX DE RÉGRESSION:")
    print("-"*70)
    
    all_signals = []
    for team, audit in results.items():
        for signal in audit.regression_signals:
            all_signals.append((team, signal))
    
    for team, signal in all_signals[:15]:
        print(f"   [{team}] {signal}")
    
    # Exploitable edges
    print(f"\n💰 EDGES EXPLOITABLES:")
    print("-"*70)
    
    all_edges = []
    for team, audit in results.items():
        for edge in audit.exploitable_edges:
            all_edges.append((team, edge))
    
    for team, edge in all_edges[:20]:
        print(f"   [{team}] {edge}")
    
    # Data quality ranking
    print(f"\n📉 PIRE QUALITÉ DE DONNÉES:")
    print("-"*70)
    
    worst = sorted(results.items(), key=lambda x: x[1].data_quality_score)[:10]
    for team, audit in worst:
        print(f"   {audit.data_quality_score:5.0f}/100 - {team} ({audit.issue_count} issues)")


def audit_single_team(team: str):
    """Audit détaillé d'une seule équipe."""
    
    all_data = load_all_data()
    audit = audit_team(team, all_data)
    
    print(f"\n{'='*70}")
    print(f"🔍 AUDIT DÉTAILLÉ: {team}")
    print(f"{'='*70}")
    
    print(f"\n📊 Data Quality Score: {audit.data_quality_score:.0f}/100")
    
    if audit.issues:
        print(f"\n🚨 ISSUES ({len(audit.issues)}):")
        for issue in audit.issues:
            print(f"\n   {issue}")
            print(f"      Source A: {issue.source_a} = {issue.value_a}")
            print(f"      Source B: {issue.source_b} = {issue.value_b}")
            if issue.recommendation:
                print(f"      💡 {issue.recommendation}")
    else:
        print(f"\n✅ Aucune issue détectée")
    
    if audit.regression_signals:
        print(f"\n⚠️ SIGNAUX RÉGRESSION:")
        for signal in audit.regression_signals:
            print(f"   • {signal}")
    
    if audit.exploitable_edges:
        print(f"\n💰 EDGES EXPLOITABLES:")
        for edge in audit.exploitable_edges:
            print(f"   • {edge}")


# ═══════════════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Audit des données Quantum")
    parser.add_argument("--team", type=str, help="Auditer une équipe spécifique")
    parser.add_argument("--top5", action="store_true", help="Auditer les top 5 leagues")
    
    args = parser.parse_args()
    
    if args.team:
        audit_single_team(args.team)
    else:
        results, critical = run_full_audit()
        print_audit_report(results, critical)
