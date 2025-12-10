#!/usr/bin/env python3
"""DATA AUDIT V2 - HEDGE FUND STYLE"""

import json
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional

DATA_ROOT = Path("/home/Mon_ps/data")
DEFENSE_FILE = DATA_ROOT / "defense_dna" / "team_defense_dna_v5_1_corrected.json"
CONTEXT_FILE = DATA_ROOT / "quantum_v2" / "teams_context_dna.json"
GK_FILE = DATA_ROOT / "goalkeeper_dna" / "goalkeeper_dna_v4_4_by_team.json"
PROFILES_FILE = DATA_ROOT / "team_dna_profiles_v2.json"

@dataclass
class DataError:
    team: str
    error_type: str
    description: str
    fix_suggestion: str
    severity: int = 20

@dataclass
class TradingSignal:
    team: str
    signal_type: str
    action: str
    market: str
    description: str
    confidence: str
    data_points: Dict = field(default_factory=dict)

@dataclass
class TeamAudit:
    team: str
    data_integrity_score: int = 100
    data_errors: List[DataError] = field(default_factory=list)
    trading_signals: List[TradingSignal] = field(default_factory=list)
    
    def add_error(self, error: DataError):
        self.data_errors.append(error)
        self.data_integrity_score = max(0, self.data_integrity_score - error.severity)
    
    def add_signal(self, signal: TradingSignal):
        self.trading_signals.append(signal)

def load_json(path: Path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None

def audit_team(team_name: str, defense: dict, context: dict, gk: dict, profile: dict) -> TeamAudit:
    audit = TeamAudit(team=team_name)
    
    # 1. ERREURS DE DONNÉES
    
    # 1.1 Timing mismatch
    if defense:
        xga_total = defense.get("xga_total", 0)
        timing_sum = sum([defense.get(f"xga_{p}", 0) for p in ["0_15","16_30","31_45","46_60","61_75","76_90"]])
        if xga_total > 0:
            mismatch = abs(timing_sum - xga_total) / xga_total * 100
            if mismatch > 5:
                audit.add_error(DataError(team_name, "TIMING_MISMATCH", 
                    f"Σ={timing_sum:.2f} ≠ total={xga_total:.2f}", "Recalculer xga_76_90", 20 if mismatch > 20 else 10))
    
    # 1.2 Zeros suspects
    if defense and defense.get("xga_total", 0) > 5:
        for p in ["0_15","16_30","31_45","46_60","61_75","76_90"]:
            if defense.get(f"xga_{p}", 0) == 0:
                audit.add_error(DataError(team_name, "SUSPICIOUS_ZERO", 
                    f"xga_{p}=0 avec total={defense.get('xga_total',0):.1f}", "Vérifier scraping", 20))
    
    # 1.3 Profile contradiction
    if defense:
        tp = defense.get("timing_profile", "")
        late = defense.get("xga_late_pct", 0)
        if "FADES_LATE" in tp and late < 15:
            audit.add_error(DataError(team_name, "PROFILE_CONTRADICTION", 
                f"FADES_LATE mais late%={late:.1f}%", "Régénérer profile", 15))
        if "FINISHES_STRONG" in tp and late > 25:
            audit.add_error(DataError(team_name, "PROFILE_CONTRADICTION", 
                f"FINISHES_STRONG mais late%={late:.1f}%", "Régénérer profile", 15))
    
    # 2. SIGNAUX DE TRADING
    
    # 2.1 Régression timing
    if context:
        for period, pdata in context.get("context_dna", {}).get("timing", {}).items():
            xg, goals = pdata.get("xG", 0), pdata.get("goals", 0)
            if xg > 1:
                diff = (goals - xg) / xg * 100
                if diff > 40:
                    audit.add_signal(TradingSignal(team_name, "REGRESSION", "FADE", f"Goals {period}",
                        f"+{diff:.0f}% surperf → régression", "HIGH" if diff > 60 else "MEDIUM"))
                elif diff < -40:
                    audit.add_signal(TradingSignal(team_name, "REGRESSION", "BACK", f"Goals {period}",
                        f"{diff:.0f}% underperf → rebond", "HIGH" if diff < -60 else "MEDIUM"))
    
    # 2.2 Luck défensive
    if context:
        xga = context.get("history", {}).get("xga", 0)
        ga = context.get("record", {}).get("goals_against", 0)
        if xga > 5:
            luck = xga - ga
            if luck > 4:
                audit.add_signal(TradingSignal(team_name, "LUCK", "FADE", "Clean Sheet",
                    f"+{luck:.1f} chanceux → CS trop courtes", "HIGH" if luck > 6 else "MEDIUM"))
            elif luck < -4:
                audit.add_signal(TradingSignal(team_name, "LUCK", "BACK", "Clean Sheet",
                    f"{luck:.1f} malchanceux → CS value", "HIGH" if luck < -6 else "MEDIUM"))
    
    # 2.3 Home/Away
    if defense:
        h, a = defense.get("home_stats", {}), defense.get("away_stats", {})
        xh, xa = h.get("xga_per_90", 0), a.get("xga_per_90", 0)
        if xh > 0 and xa > 0 and xa/xh > 1.5:
            audit.add_signal(TradingSignal(team_name, "HOME_AWAY", "BACK", "CS HOME",
                f"xGA {xh:.2f} home vs {xa:.2f} away ({xa/xh:.1f}x)", "HIGH" if xa/xh > 2 else "MEDIUM"))
    
    # 2.4 Forme
    if context:
        rec = context.get("record", {})
        ppg_s = rec.get("points", 0) / rec.get("matches", 1)
        ppg_5 = context.get("momentum_dna", {}).get("points_last_5", 0) / 5
        if ppg_s > 0:
            delta = (ppg_5 - ppg_s) / ppg_s * 100
            if delta > 25:
                audit.add_signal(TradingSignal(team_name, "FORM", "BACK", "Match",
                    f"Forme ↑ {ppg_s:.2f}→{ppg_5:.2f} (+{delta:.0f}%)", "MEDIUM"))
            elif delta < -25:
                audit.add_signal(TradingSignal(team_name, "FORM", "FADE", "Match",
                    f"Forme ↓ {ppg_s:.2f}→{ppg_5:.2f} ({delta:.0f}%)", "MEDIUM"))
    
    return audit

def print_summary(audits):
    total_err = sum(len(a.data_errors) for a in audits)
    total_sig = sum(len(a.trading_signals) for a in audits)
    perfect = sum(1 for a in audits if a.data_integrity_score == 100)
    
    print(f"""
🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍
   AUDIT HEDGE FUND V2 - RÉSUMÉ
🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍��🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍

╔═══════════════════════════════════════════════════════════════════════╗
║  📊 RÉSUMÉ GLOBAL                                                      ║
╠═══════════════════════════════════════════════════════════════════════╣
║  Équipes auditées:     {len(audits):>3}                                          ║
║  Données parfaites:    {perfect:>3}/96  ({perfect*100//len(audits)}%)  {"✅" if perfect==96 else ""}                          ║
║  Erreurs de données:   {total_err:>3}   {"✅ Aucune!" if total_err==0 else "← À corriger"}                          ║
║  Signaux de trading:   {total_sig:>3}   ← Opportunités!                         ║
╚═══════════════════════════════════════════════════════════════════════╝
""")
    
    err_teams = [a for a in audits if a.data_errors]
    if err_teams:
        print("🚨 ÉQUIPES AVEC ERREURS DE DONNÉES:\n" + "-"*70)
        for a in sorted(err_teams, key=lambda x: x.data_integrity_score):
            print(f"   • {a.team}: {a.data_integrity_score}/100")
            for e in a.data_errors:
                print(f"      ❌ {e.error_type}: {e.description}")
    else:
        print("✅ TOUTES LES DONNÉES SONT PARFAITES! (96/96)")
    
    high = [(a.team, s) for a in audits for s in a.trading_signals if s.confidence == "HIGH"]
    if high:
        print(f"\n💰 TOP SIGNAUX HIGH CONFIDENCE ({len(high)}):\n" + "-"*70)
        fades = [(t,s) for t,s in high if s.action=="FADE"][:10]
        backs = [(t,s) for t,s in high if s.action=="BACK"][:10]
        if fades:
            print("\n   🔻 FADE:")
            for t,s in fades: print(f"      • {t} - {s.market}: {s.description}")
        if backs:
            print("\n   🔼 BACK:")
            for t,s in backs: print(f"      • {t} - {s.market}: {s.description}")

def print_team(audit):
    score = audit.data_integrity_score
    emoji = "✅" if score == 100 else ("⚠️" if score >= 80 else "🔴")
    print(f"\n{'='*70}\n🔍 AUDIT: {audit.team}\n{'='*70}")
    print(f"\n{emoji} DATA INTEGRITY: {score}/100")
    
    if audit.data_errors:
        print(f"\n🚨 ERREURS ({len(audit.data_errors)}):")
        for e in audit.data_errors:
            print(f"   ❌ {e.error_type}: {e.description}\n      💡 {e.fix_suggestion}")
    else:
        print("\n✅ DONNÉES PARFAITES!")
    
    if audit.trading_signals:
        print(f"\n💰 SIGNAUX ({len(audit.trading_signals)}):")
        for s in audit.trading_signals:
            c = "🔥" if s.confidence == "HIGH" else "📊"
            print(f"   {c} {s.action} {s.market}: {s.description}")

def main():
    print("\n" + "="*70 + "\n   DATA AUDIT V2 - HEDGE FUND STYLE\n" + "="*70)
    
    defense_raw = load_json(DEFENSE_FILE)
    context = load_json(CONTEXT_FILE) or {}
    gk = load_json(GK_FILE) or {}
    profiles = load_json(PROFILES_FILE) or {}
    
    if not defense_raw: return print("❌ Erreur chargement")
    
    defense = {d["team_name"]: d for d in defense_raw}
    single = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--team" else None
    teams = [single] if single else list(defense.keys())
    
    audits = [audit_team(t, defense.get(t,{}), context.get(t,{}), gk.get(t,{}), profiles.get(t,{})) for t in teams]
    
    if single:
        print_team(audits[0])
    else:
        print_summary(audits)

if __name__ == "__main__":
    main()
