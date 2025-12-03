#!/usr/bin/env python3
"""Test connexion V10"""

import sys
sys.path.insert(0, '/home/Mon_ps/backend/agents/clv_tracker')

from orchestrator_v10_quant_engine import OrchestratorV10Quant

orch = OrchestratorV10Quant()

print("="*60)
print("TEST CONNEXION V10")
print("="*60)

# Vérifier état connexion
print(f"\n1. Etat connexion initial:")
print(f"   conn: {orch.conn}")
print(f"   closed: {orch.conn.closed}")
print(f"   status: {orch.conn.status}")

# Test intelligence
print(f"\n2. Après _get_team_intelligence:")
intel = orch._get_team_intelligence("Liverpool")
print(f"   Result: {intel.get('team_name') if intel else 'None'}")
print(f"   closed: {orch.conn.closed}")
print(f"   status: {orch.conn.status}")

# Test momentum
print(f"\n3. Après _get_team_momentum:")
try:
    mom = orch._get_team_momentum("Liverpool")
    print(f"   Result: {mom.get('team_name') if mom else 'None'}")
except Exception as e:
    print(f"   ERREUR: {e}")
print(f"   closed: {orch.conn.closed}")
print(f"   status: {orch.conn.status}")

# Tester si c'est un problème de transaction
print(f"\n4. Après rollback:")
try:
    orch.conn.rollback()
    print(f"   Rollback OK")
except Exception as e:
    print(f"   Rollback error: {e}")

# Retester momentum après rollback
print(f"\n5. _get_team_momentum après rollback:")
mom2 = orch._get_team_momentum("Liverpool")
print(f"   Result: {mom2.get('team_name') if mom2 else 'None'}")

print("\nDone")
