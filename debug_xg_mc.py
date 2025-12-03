#!/usr/bin/env python3
"""Debug: Voir les xG passés au Monte Carlo"""

import sys
sys.path.insert(0, '/home/Mon_ps/backend/agents/clv_tracker')

from orchestrator_v10_quant_engine import OrchestratorV10Quant

print("="*70)
print("DEBUG xG → MONTE CARLO")
print("="*70)

orch = OrchestratorV10Quant()

match_data = {
    'match_id': 'liv_sun_test',
    'home_team': 'Liverpool',
    'away_team': 'Sunderland',
    'competition': 'League Cup',
    'odds': {
        'btts_yes': 1.85,
        'btts_no': 1.95,
        'over_25': 1.55,
        'under_25': 2.45,
    }
}

# Récupérer le contexte manuellement
context = orch._prefetch_context('Liverpool', 'Sunderland', 'League Cup', {})

print("\n1. DONNÉES RÉCUPÉRÉES:")
print(f"   Home Intel: {context.get('home_intel', {}).get('home_goals_scored_avg')} scored, {context.get('home_intel', {}).get('home_goals_conceded_avg')} conceded")
print(f"   Away Intel: {context.get('away_intel', {}).get('away_goals_scored_avg')} scored, {context.get('away_intel', {}).get('away_goals_conceded_avg')} conceded")
print(f"   Home Class: Tier={context.get('home_class', {}).get('tier')}, Fortress={context.get('home_class', {}).get('home_fortress_factor')}")
print(f"   Away Class: Tier={context.get('away_class', {}).get('tier')}, Weakness={context.get('away_class', {}).get('away_weakness_factor')}")

# Calculer lineup impact
lineup = orch.lineup_engine.calculate_impact(
    'Liverpool', 'Sunderland',
    context.get('home_intel', {}),
    context.get('away_intel', {}),
    context.get('home_class', {}),
    context.get('away_class', {}),
    context.get('home_momentum', {}),
    context.get('away_momentum', {}),
    context
)

print("\n2. xG CALCULÉS PAR LINEUP ENGINE:")
print(f"   Home base xG: {lineup.home_base_xg:.3f}")
print(f"   Away base xG: {lineup.away_base_xg:.3f}")
print(f"   Home adjustment: {lineup.home_xg_adjustment:.3f}")
print(f"   Away adjustment: {lineup.away_xg_adjustment:.3f}")
print(f"   Home FINAL xG: {lineup.home_adjusted_xg:.3f}")
print(f"   Away FINAL xG: {lineup.away_adjusted_xg:.3f}")

# Simuler Monte Carlo
mc = orch.monte_carlo.simulate_match(
    lineup.home_adjusted_xg,
    lineup.away_adjusted_xg,
    home_style='balanced',
    away_style='balanced_offensive'
)

print("\n3. RÉSULTATS MONTE CARLO:")
print(f"   BTTS YES: {mc.btts_yes_prob*100:.1f}%")
print(f"   BTTS NO: {mc.btts_no_prob*100:.1f}%")
print(f"   OVER 2.5: {mc.over_25_prob*100:.1f}%")
print(f"   UNDER 2.5: {mc.under_25_prob*100:.1f}%")

# Calcul théorique Poisson pour comparaison
import math
def p_score(xg):
    return 1 - math.exp(-xg)

p_liv = p_score(lineup.home_adjusted_xg)
p_sun = p_score(lineup.away_adjusted_xg)
btts_poisson = p_liv * p_sun

print("\n4. VÉRIFICATION POISSON SIMPLE:")
print(f"   P(Liverpool marque) = {p_liv*100:.1f}%")
print(f"   P(Sunderland marque) = {p_sun*100:.1f}%")
print(f"   BTTS YES Poisson = {btts_poisson*100:.1f}%")
print(f"   Écart MC vs Poisson: {(mc.btts_yes_prob - btts_poisson)*100:+.1f}%")
