#!/usr/bin/env python3
"""
Patch V10.3 - League Tier Adjustment
Ajuste les xG quand D1 affronte D2/D3
"""

with open('orchestrator_v10_quant_engine.py', 'r') as f:
    content = f.read()

# Trouver le bloc après le calcul xG et avant les ajustements
old_block = '''        impact.away_base_xg = (away_attack * 0.6) + (home_defense * 0.4)
        
        # Ajustement pour absences STAR PLAYERS'''

new_block = '''        impact.away_base_xg = (away_attack * 0.6) + (home_defense * 0.4)
        
        # ═══════════════════════════════════════════════════════
        # V10.3 - LEAGUE TIER ADJUSTMENT
        # D1 vs D2 = boost attaque D1, malus défense D2
        # ═══════════════════════════════════════════════════════
        home_tier = home_class.get('tier', 'B') if home_class else 'B'
        away_tier = away_class.get('tier', 'B') if away_class else 'B'
        
        tier_values = {'S': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1}
        home_tier_val = tier_values.get(home_tier, 3)
        away_tier_val = tier_values.get(away_tier, 3)
        tier_diff = home_tier_val - away_tier_val
        
        if tier_diff >= 2:  # Home très supérieur (ex: Liverpool vs Sunderland)
            impact.home_base_xg *= 1.25  # +25% attaque home
            impact.away_base_xg *= 0.75  # -25% attaque away
        elif tier_diff >= 1:  # Home supérieur
            impact.home_base_xg *= 1.10  # +10% attaque home
            impact.away_base_xg *= 0.90  # -10% attaque away
        elif tier_diff <= -2:  # Away très supérieur
            impact.home_base_xg *= 0.75
            impact.away_base_xg *= 1.25
        elif tier_diff <= -1:  # Away supérieur
            impact.home_base_xg *= 0.90
            impact.away_base_xg *= 1.10
        
        # Ajustement pour absences STAR PLAYERS'''

if old_block in content:
    content = content.replace(old_block, new_block)
    with open('orchestrator_v10_quant_engine.py', 'w') as f:
        f.write(content)
    print("✅ Patch V10.3 (League Tier Adjustment) appliqué!")
else:
    print("❌ Pattern non trouvé")
