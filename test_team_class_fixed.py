#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/Mon_ps')

# Recharger le module
import importlib
import orchestrator_v11_3_full_analysis as orch_module
importlib.reload(orch_module)

from orchestrator_v11_3_full_analysis import OrchestratorV11_3

print("=" * 70)
print("    TEST LAYER TEAM_CLASS CORRIGÉ")
print("=" * 70)

orch = OrchestratorV11_3()

# Tests avec des matchs à forte différence de power
tests = [
    ("Arsenal FC", "Liverpool FC"),           # 58 vs 58 (égal)
    ("Real Madrid", "Getafe CF"),             # 99 vs ~40 (gros écart)
    ("Manchester City", "Burnley FC"),        # 99 vs ~35 (gros écart)
    ("Newcastle United FC", "Manchester City FC"),  # Match réel du backtest
]

print()
for home, away in tests:
    result = orch._analyze_team_class(home, away)
    print(f"⚽ {home[:20]:20} vs {away[:20]:20}")
    print(f"   Score: {result['score']:.2f} | {result['reason']}")
    print()

# Comparer avant/après sur le backtest
print("=" * 70)
print("    IMPACT SUR ANALYSE COMPLÈTE")
print("=" * 70)

result = orch.analyze_match("Newcastle United FC", "Manchester City FC", "over_25")
print(f"\n⚽ Newcastle vs Man City:")
print(f"   Score total: {result['score']:.1f}")
print(f"   Action: {result['action']}")
print(f"   Layers:")
for layer, score in result.get('layer_scores', {}).items():
    indicator = "📈" if score > 0.5 else "➡️"
    print(f"      {indicator} {layer}: {score:.2f}")
