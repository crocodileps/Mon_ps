#!/usr/bin/env python3
"""Patch pour corriger la récupération des xG"""

import re

# Lire le fichier
with open('orchestrator_v10_quant_engine.py', 'r') as f:
    content = f.read()

# Ancien code (à remplacer)
old_code = '''        impact = LineupImpact()
        
        # xG de base depuis team_intelligence
        impact.home_base_xg = float(home_intel.get('xg_for_avg', 1.3) or 1.3) if home_intel else 1.3
        impact.away_base_xg = float(away_intel.get('xg_for_avg', 1.1) or 1.1) if away_intel else 1.1
        
        # Si xG pas disponible, estimer depuis goals_avg
        if impact.home_base_xg == 0 and home_intel:
            impact.home_base_xg = float(home_intel.get('home_goals_scored_avg', 1.3) or 1.3)
        if impact.away_base_xg == 0 and away_intel:
            impact.away_base_xg = float(away_intel.get('away_goals_scored_avg', 1.1) or 1.1)'''

# Nouveau code (corrigé)
new_code = '''        impact = LineupImpact()
        
        # xG de base - priorité: xg_for_avg > home_goals_scored_avg > default
        if home_intel:
            xg = home_intel.get('xg_for_avg')
            if xg is None or xg == 0:
                xg = home_intel.get('home_goals_scored_avg')
            impact.home_base_xg = float(xg) if xg else 1.3
        else:
            impact.home_base_xg = 1.3
        
        if away_intel:
            xg = away_intel.get('xg_for_avg')
            if xg is None or xg == 0:
                xg = away_intel.get('away_goals_scored_avg')
            impact.away_base_xg = float(xg) if xg else 1.1
        else:
            impact.away_base_xg = 1.1'''

# Remplacer
if old_code in content:
    content = content.replace(old_code, new_code)
    with open('orchestrator_v10_quant_engine.py', 'w') as f:
        f.write(content)
    print("✅ Patch appliqué avec succès!")
else:
    print("❌ Code source non trouvé - vérification manuelle nécessaire")
    print("\nRecherche du pattern...")
    if 'xg_for_avg' in content:
        print("   xg_for_avg trouvé dans le fichier")
    if 'LineupImpact()' in content:
        print("   LineupImpact() trouvé dans le fichier")
