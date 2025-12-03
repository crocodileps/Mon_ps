#!/usr/bin/env python3
"""Test V10 - Debug du context"""

import sys
sys.path.insert(0, '/home/Mon_ps/backend/agents/clv_tracker')

from orchestrator_v10_quant_engine import OrchestratorV10Quant

orch = OrchestratorV10Quant()

home = "Liverpool"
away = "Manchester City"
mid = "test"
league = "Premier League"
ref = "Michael Oliver"

print("="*70)
print("DEBUG CONTEXT V10")
print("="*70)

# Utiliser le bon nom de méthode
ctx = orch._prefetch_context(home, away, mid, league, ref)

print("\nCONTEXT RECUPÉRÉ:")
for key, value in ctx.items():
    if value is None:
        print(f"  X {key}: None")
    elif isinstance(value, dict):
        preview = {k: v for k, v in list(value.items())[:3]}
        print(f"  OK {key}: {preview}...")
    elif isinstance(value, list):
        print(f"  {'OK' if value else 'X'} {key}: {len(value)} items")
    else:
        print(f"  OK {key}: {value}")

print("\nDETAIL MOMENTUM:")
home_mom = ctx.get("home_momentum")
away_mom = ctx.get("away_momentum")
print(f"  Home: {home_mom.get('team_name') if home_mom else 'None'} = {home_mom.get('momentum_score') if home_mom else 'N/A'}")
print(f"  Away: {away_mom.get('team_name') if away_mom else 'None'} = {away_mom.get('momentum_score') if away_mom else 'N/A'}")

print("\nDETAIL REFEREE:")
ref_data = ctx.get("referee")
if ref_data:
    print(f"  {ref_data.get('referee_name')}: {ref_data.get('avg_goals_per_game')} goals, {ref_data.get('under_over_tendency')}")
else:
    print(f"  None")

print("\nDETAIL H2H:")
h2h = ctx.get("h2h")
if h2h:
    print(f"  {h2h.get('team_a')} vs {h2h.get('team_b')}: BTTS={h2h.get('btts_pct')}%")
else:
    print(f"  None")

print("\nDone")
