#!/usr/bin/env python3
"""Patch xG avec défense adverse - version par lignes"""

with open('orchestrator_v10_quant_engine.py', 'r') as f:
    lines = f.readlines()

# Trouver la ligne "impact = LineupImpact()" dans _build_lineup_impact
start_line = None
end_line = None

for i, line in enumerate(lines):
    if 'impact = LineupImpact()' in line and start_line is None:
        start_line = i
    if start_line and 'impact.away_base_xg = float(xg) if xg else 1.1' in line:
        end_line = i
        break

if start_line is None or end_line is None:
    print("❌ Lignes non trouvées")
    exit(1)

print(f"Trouvé: lignes {start_line+1} à {end_line+1}")

# Trouver la ligne "else: impact.away_base_xg = 1.1"
for i in range(end_line+1, min(end_line+5, len(lines))):
    if 'impact.away_base_xg = 1.1' in lines[i]:
        end_line = i
        break

print(f"Fin du bloc: ligne {end_line+1}")

# Nouveau code
new_code = '''        impact = LineupImpact()
        
        # ═══════════════════════════════════════════════════════
        # xG V10.1 - ATTAQUE + DÉFENSE ADVERSE
        # ═══════════════════════════════════════════════════════
        
        # HOME xG = 60% attaque home + 40% défense away
        home_attack = 1.3
        away_defense = 1.3
        
        if home_intel:
            xg = home_intel.get('xg_for_avg')
            if xg is None or xg == 0:
                xg = home_intel.get('home_goals_scored_avg')
            home_attack = float(xg) if xg else 1.3
        
        if away_intel:
            away_def = away_intel.get('away_goals_conceded_avg')
            if away_def:
                away_defense = float(away_def)
        
        impact.home_base_xg = (home_attack * 0.6) + (away_defense * 0.4)
        
        # AWAY xG = 60% attaque away + 40% défense home
        away_attack = 1.1
        home_defense = 1.1
        
        if away_intel:
            xg = away_intel.get('xg_for_avg')
            if xg is None or xg == 0:
                xg = away_intel.get('away_goals_scored_avg')
            away_attack = float(xg) if xg else 1.1
        
        if home_intel:
            home_def = home_intel.get('home_goals_conceded_avg')
            if home_def:
                home_defense = float(home_def)
        
        impact.away_base_xg = (away_attack * 0.6) + (home_defense * 0.4)
'''

# Remplacer les lignes
new_lines = lines[:start_line] + [new_code] + lines[end_line+1:]

with open('orchestrator_v10_quant_engine.py', 'w') as f:
    f.writelines(new_lines)

print("✅ Patch xG V10.1 appliqué!")
print("   home_xg = 60% attaque + 40% défense adverse")
print("   away_xg = 60% attaque + 40% défense adverse")
