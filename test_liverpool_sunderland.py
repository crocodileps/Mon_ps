#!/usr/bin/env python3
"""Test V10.1 - Liverpool vs Sunderland (vrai match)"""

import sys
sys.path.insert(0, '/home/Mon_ps/backend/agents/clv_tracker')

from orchestrator_v10_quant_engine import OrchestratorV10Quant

print("="*70)
print("🏴󠁧󠁢󠁥󠁮󠁧󠁿 TEST V10.1 - LIVERPOOL vs SUNDERLAND")
print("="*70)

orch = OrchestratorV10Quant()

# Match data avec vraies cotes de la DB
match_data = {
    'match_id': 'liverpool_sunderland_real',
    'home_team': 'Liverpool',
    'away_team': 'Sunderland',
    'odds': {
        'home': 1.38,
        'draw': 5.35,
        'away': 7.90,
        'over_25': 1.55,
        'under_25': 2.45,
        'btts_yes': 1.85,
        'btts_no': 1.95,
        'over_35': 2.10,
        'under_35': 1.72
    }
}

result = orch.analyze_match(match_data)

picks = result if isinstance(result, list) else getattr(result, 'picks', [])

print(f"\nTOP {min(5, len(picks))} PICKS:")
print("-"*70)

for i, pick in enumerate(picks[:5], 1):
    ss = " SS" if getattr(pick, 'is_sweet_spot', False) else ""
    trap = " 🚫TRAP" if getattr(pick, 'is_trap', False) else ""
    print(f"\n#{i} {pick.market_type} @ {pick.odds}{ss}{trap}")
    print(f"   Score: {pick.final_score} | Coverage: {int(pick.data_coverage*100)}%")
    print(f"   MC: Prob={pick.mc_prob*100:.1f}% | Edge={pick.mc_edge*100:.1f}%")
    print(f"   Kelly: {min(pick.kelly_fraction*100, 10):.2f}%")
    print(f"   -> {pick.recommendation}")

print("\n" + "="*70)
print("📊 RÉSUMÉ")
print("="*70)
for k, v in orch.stats.items():
    print(f"   {k.replace('_', ' ').title():35} {v}")
print("="*70)
