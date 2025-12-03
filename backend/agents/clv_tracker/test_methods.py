#!/usr/bin/env python3
"""Test direct des méthodes"""

import sys
sys.path.insert(0, '/home/Mon_ps/backend/agents/clv_tracker')

from orchestrator_v10_quant_engine import OrchestratorV10Quant

orch = OrchestratorV10Quant()

print("="*60)
print("TEST DIRECT DES METHODES")
print("="*60)

# Test _resolve_team_name
print("\n1. _resolve_team_name('Liverpool'):")
variants = orch._resolve_team_name("Liverpool")
print(f"   {variants}")

# Test _build_name_where
print("\n2. _build_name_where('team_name', 'Liverpool'):")
where, params = orch._build_name_where('team_name', 'Liverpool')
print(f"   WHERE: {where}")
print(f"   PARAMS: {params}")

# Test direct _get_team_intelligence
print("\n3. _get_team_intelligence('Liverpool'):")
intel = orch._get_team_intelligence("Liverpool")
print(f"   Result: {intel.get('team_name') if intel else 'None'}")

# Test direct _get_team_momentum
print("\n4. _get_team_momentum('Liverpool'):")
mom = orch._get_team_momentum("Liverpool")
print(f"   Result: {mom.get('team_name') if mom else 'None'}")

# Test avec "Liverpool FC"
print("\n5. _get_team_momentum('Liverpool FC'):")
mom2 = orch._get_team_momentum("Liverpool FC")
print(f"   Result: {mom2.get('team_name') if mom2 else 'None'}")

# Test _get_team_class
print("\n6. _get_team_class('Liverpool'):")
cls = orch._get_team_class("Liverpool")
print(f"   Result: {cls.get('team_name') if cls else 'None'}")

# Test _get_referee_data
print("\n7. _get_referee_data('Michael Oliver', 'Premier League'):")
ref = orch._get_referee_data("Michael Oliver", "Premier League")
print(f"   Result: {ref.get('referee_name') if ref else 'None'}")

# Test _get_h2h_data
print("\n8. _get_h2h_data('Liverpool', 'Manchester City'):")
h2h = orch._get_h2h_data("Liverpool", "Manchester City")
print(f"   Result: {h2h.get('team_a') if h2h else 'None'} vs {h2h.get('team_b') if h2h else 'None'}")

# Test _get_tactical_match
print("\n9. _get_tactical_match('balanced', 'offensive'):")
tac = orch._get_tactical_match("balanced", "offensive")
print(f"   Result: {tac.get('btts_probability') if tac else 'None'}%")

print("\nDone")
