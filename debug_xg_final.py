#!/usr/bin/env python3
"""Debug final avec les bons noms de clés"""

import sys
sys.path.insert(0, '/home/Mon_ps/backend/agents/clv_tracker')

from orchestrator_v10_quant_engine import OrchestratorV10Quant

print("="*70)
print("DEBUG xG FINAL")
print("="*70)

orch = OrchestratorV10Quant()

# Récupérer le contexte avec les bons paramètres
context = orch._prefetch_context('Liverpool', 'Sunderland', 'liv_sun', 'League Cup', None)

print("\n1. DONNÉES RÉCUPÉRÉES (bons noms):")
home_intel = context.get('home_intelligence')  # CORRECT!
away_intel = context.get('away_intelligence')  # CORRECT!

print(f"   Home Intelligence présent: {bool(home_intel)}")
if home_intel:
    print(f"      scored={home_intel.get('home_goals_scored_avg')}, conceded={home_intel.get('home_goals_conceded_avg')}")

print(f"   Away Intelligence présent: {bool(away_intel)}")
if away_intel:
    print(f"      scored={away_intel.get('away_goals_scored_avg')}, conceded={away_intel.get('away_goals_conceded_avg')}")

print(f"\n   Home Class: Tier={context.get('home_class', {}).get('tier')}")
print(f"   Away Class: Tier={context.get('away_class', {}).get('tier')}")

# Calculer lineup impact
lineup = orch.lineup_engine.calculate_impact(
    'Liverpool', 'Sunderland',
    home_intel,
    away_intel,
    context.get('home_class', {}),
    context.get('away_class', {}),
    context.get('home_momentum', {}),
    context.get('away_momentum', {}),
    {'competition': 'League Cup'}
)

print("\n2. xG CALCULÉS:")
print(f"   Liverpool xG: {lineup.home_adjusted_xg:.3f}")
print(f"   Sunderland xG: {lineup.away_adjusted_xg:.3f}")
print(f"   Total xG: {lineup.home_adjusted_xg + lineup.away_adjusted_xg:.3f}")

# Monte Carlo
mc = orch.monte_carlo.simulate_match(
    lineup.home_adjusted_xg,
    lineup.away_adjusted_xg,
    home_style=context.get('home_style', 'balanced'),
    away_style=context.get('away_style', 'balanced')
)

print("\n3. MONTE CARLO:")
print(f"   BTTS: {mc.btts_prob*100:.1f}%")
print(f"   OVER 2.5: {mc.over_25_prob*100:.1f}%")

# Calcul Poisson pour comparaison
import math
def p_score(xg):
    return 1 - math.exp(-xg)

p_liv = p_score(lineup.home_adjusted_xg)
p_sun = p_score(lineup.away_adjusted_xg)
btts_poisson = p_liv * p_sun

print("\n4. VERIFICATION POISSON:")
print(f"   P(Liverpool marque) = {p_liv*100:.1f}%")
print(f"   P(Sunderland marque) = {p_sun*100:.1f}%") 
print(f"   BTTS Poisson = {btts_poisson*100:.1f}%")
print(f"   Écart MC-Poisson: {(mc.btts_prob - btts_poisson)*100:+.1f}%")
