#!/usr/bin/env python3
"""Test V10 sur Bilbao vs Real Madrid"""

import sys
sys.path.insert(0, '/home/Mon_ps/backend/agents/clv_tracker')

from orchestrator_v10_quant_engine import OrchestratorV10Quant

orch = OrchestratorV10Quant()

print("="*70)
print("ATHLETIC BILBAO vs REAL MADRID")
print("="*70)

match_data = {
    "match_id": "bilbao_madrid_test",
    "home_team": "Athletic Bilbao",
    "away_team": "Real Madrid",
    "league": "La Liga",
    "odds": {
        "home": 3.40,
        "draw": 3.50,
        "away": 2.10,
        "btts_yes": 1.85,
        "btts_no": 1.95,
        "over_25": 1.90,
        "under_25": 1.90,
        "over_35": 2.80,
        "under_35": 1.40,
    }
}

picks = orch.analyze_match(match_data)
best_picks = orch.filter_best_picks(picks, max_picks=5)

print(f"\nTOP {len(best_picks)} PICKS:")
print("-"*70)

for i, pick in enumerate(best_picks, 1):
    ss = "SS" if pick.sweet_spot_score > 0 else ""
    cov = "+" if pick.data_coverage >= 0.5 else "-"
    
    print(f"\n#{i} {pick.market_type.upper()} @ {pick.odds} {ss}")
    print(f"   Score: {pick.final_score} | Coverage: [{cov}] {pick.data_coverage*100:.0f}%")
    print(f"   MC: Prob={pick.mc_prob*100:.1f}% | Edge={pick.mc_edge*100:.1f}%")
    print(f"   xG: {pick.xg_adjusted_home:.2f} vs {pick.xg_adjusted_away:.2f}")
    print(f"   Kelly: {min(pick.kelly_fraction*100, 25):.2f}%")
    print(f"   -> {pick.recommendation}")
    
    # Scores individuels
    print(f"   LAYERS: MC={pick.mc_score} | Mom={pick.momentum_score} | Tac={pick.tactical_score} | Intel={pick.intelligence_score}")
    print(f"           Class={pick.class_score} | Ref={pick.referee_score} | H2H={pick.h2h_score} | SS={pick.sweet_spot_score}")

# Debug data
print("\n" + "="*70)
print("DEBUG DATA:")
print("="*70)

for team in ["Athletic Bilbao", "Real Madrid"]:
    print(f"\n{team}:")
    intel = orch._get_team_intelligence(team)
    mom = orch._get_team_momentum(team)
    cls = orch._get_team_class(team)
    
    if intel:
        print(f"  Intel: style={intel.get('current_style')}, btts={intel.get('btts_tendency')}, goals={intel.get('home_goals_scored_avg')}/{intel.get('away_goals_scored_avg')}")
    else:
        print(f"  Intel: None")
    
    if mom:
        print(f"  Momentum: {mom.get('momentum_score')}")
    else:
        print(f"  Momentum: None")
    
    if cls:
        print(f"  Class: Tier {cls.get('tier')}, style={cls.get('playing_style')}")
    else:
        print(f"  Class: None")

# Tactical
intel_home = orch._get_team_intelligence("Athletic Bilbao")
intel_away = orch._get_team_intelligence("Real Madrid")
if intel_home and intel_away:
    style_h = intel_home.get('current_style', 'balanced')
    style_a = intel_away.get('current_style', 'balanced')
    print(f"\nTactical ({style_h} vs {style_a}):")
    tac = orch._get_tactical_match(style_h, style_a)
    if tac:
        print(f"  btts={tac.get('btts_probability')}%, over25={tac.get('over_25_probability')}%")
    else:
        print(f"  None")

# H2H
print(f"\nH2H:")
h2h = orch._get_h2h_data("Athletic Bilbao", "Real Madrid")
if h2h:
    print(f"  {h2h.get('team_a')} vs {h2h.get('team_b')}: {h2h.get('total_matches')} matches, btts={h2h.get('btts_pct')}%")
else:
    print(f"  None")

print("\n" + "="*70)
orch.print_summary()
