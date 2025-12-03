#!/usr/bin/env python3
"""Patch Defense Crusher - Pattern exact"""

with open('orchestrator_v10_quant_engine.py', 'r') as f:
    content = f.read()

# Pattern exact du fichier
old_block = '''        impact.away_base_xg = (away_attack * 0.6) + (home_defense * 0.4)
        
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
            impact.away_base_xg *= 1.10'''

new_block = '''        impact.away_base_xg = (away_attack * 0.6) + (home_defense * 0.4)
        
        # ═══════════════════════════════════════════════════════
        # SMART QUANT 2.0 - DEFENSE CRUSHER
        # Suppression xG basée sur clean_sheet_tendency (exponentiel)
        # ═══════════════════════════════════════════════════════
        
        # Récupérer les métriques défensives
        home_cs_rate = float(home_intel.get('clean_sheet_tendency', 30)) if home_intel else 30
        away_cs_rate = float(away_intel.get('clean_sheet_tendency', 30)) if away_intel else 30
        
        # Appliquer Defense Crusher (Liverpool 78% CS -> -55% xG adverse)
        impact.away_base_xg = apply_defense_crusher(impact.away_base_xg, home_cs_rate)
        impact.home_base_xg = apply_defense_crusher(impact.home_base_xg, away_cs_rate)
        
        # ═══════════════════════════════════════════════════════
        # TIER ADJUSTMENT (allégé - Defense Crusher fait le gros)
        # ═══════════════════════════════════════════════════════
        home_tier = home_class.get('tier', 'B') if home_class else 'B'
        away_tier = away_class.get('tier', 'B') if away_class else 'B'
        tier_values = {'S': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1}
        home_tier_val = tier_values.get(home_tier, 3)
        away_tier_val = tier_values.get(away_tier, 3)
        tier_diff = home_tier_val - away_tier_val
        
        if tier_diff >= 2:  # Home très supérieur
            impact.home_base_xg *= 1.12  # Réduit (Defense Crusher gère)
            impact.away_base_xg *= 0.88
        elif tier_diff >= 1:  # Home supérieur
            impact.home_base_xg *= 1.06
            impact.away_base_xg *= 0.94
        elif tier_diff <= -2:  # Away très supérieur
            impact.home_base_xg *= 0.88
            impact.away_base_xg *= 1.12
        elif tier_diff <= -1:  # Away supérieur
            impact.home_base_xg *= 0.94
            impact.away_base_xg *= 1.06'''

if old_block in content:
    content = content.replace(old_block, new_block)
    print("✅ Defense Crusher intégré!")
else:
    # Essayer sans les lignes vides exactes
    print("Pattern non trouvé - essai alternatif...")
    
    # Chercher juste le début
    if "V10.3 - LEAGUE TIER ADJUSTMENT" in content:
        print("Le bloc existe mais avec formatage différent")
        print("Lignes trouvées:")
        for i, line in enumerate(content.split('\n')):
            if 'V10.3 - LEAGUE' in line or 'tier_diff >= 2' in line:
                print(f"   {i}: {line[:60]}")

with open('orchestrator_v10_quant_engine.py', 'w') as f:
    f.write(content)
