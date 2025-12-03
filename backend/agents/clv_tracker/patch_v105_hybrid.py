#!/usr/bin/env python3
"""
Patch V10.5 - Hybrid Smart Regression
Calcule tier_diff AVANT la régression et ajuste C dynamiquement
"""

with open('orchestrator_v10_quant_engine.py', 'r') as f:
    lines = f.readlines()

# 1. Modifier _regress_to_mean pour accepter tier_diff (ligne ~594)
for i, line in enumerate(lines):
    if "def _regress_to_mean(self, team_stat: float, sample_size: int," in line:
        # Remplacer la signature
        lines[i] = "    def _regress_to_mean(self, team_stat: float, sample_size: int,\n"
        lines[i+1] = "                          league_avg: float = None, location: str = 'home',\n"
        # Insérer le nouveau paramètre
        lines.insert(i+2, "                          tier_diff: int = 0) -> float:\n")
        # Supprimer l'ancienne ligne de fermeture
        for j in range(i+3, min(i+10, len(lines))):
            if "location: str = 'home') -> float:" in lines[j]:
                lines[j] = ""
                break
        print(f"✅ 1. Signature _regress_to_mean modifiée (ligne {i+1})")
        break

# 2. Modifier le corps de _regress_to_mean pour C dynamique
for i, line in enumerate(lines):
    if 'C = 10  # Équivalent à 10 matchs de "prior"' in line:
        lines[i] = '''        # V10.5 - C dynamique selon tier_diff
        if tier_diff >= 2:
            C = 2   # D1 vs D2: régression faible
        elif tier_diff == 1:
            C = 5   # Légère diff: régression moyenne
        else:
            C = 10  # Même niveau: régression forte
'''
        print(f"✅ 2. C dynamique ajouté (ligne {i+1})")
        break

# 3. Déplacer le calcul tier_diff AVANT la régression
# Trouver "home_attack = 1.3" et insérer tier_diff juste après
for i, line in enumerate(lines):
    if "        home_attack = 1.3" in line and "away_defense = 1.3" in lines[i+1]:
        tier_calc = '''
        # V10.5 - Calculer tier_diff AVANT régression
        home_tier = home_class.get('tier', 'B') if home_class else 'B'
        away_tier = away_class.get('tier', 'B') if away_class else 'B'
        tier_values_pre = {'S': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1}
        tier_diff_pre = abs(tier_values_pre.get(home_tier, 3) - tier_values_pre.get(away_tier, 3))

'''
        lines.insert(i+2, tier_calc)
        print(f"✅ 3. Calcul tier_diff déplacé AVANT régression (ligne {i+3})")
        break

# 4. Modifier les appels à _regress_to_mean pour passer tier_diff
modified_calls = 0
for i, line in enumerate(lines):
    if "home_attack = self._regress_to_mean(" in line:
        # Trouver la ligne de fermeture
        for j in range(i, min(i+5, len(lines))):
            if "location='home'" in lines[j] and ")" in lines[j]:
                lines[j] = lines[j].replace("location='home')", "location='home', tier_diff=tier_diff_pre)")
                modified_calls += 1
                break
    elif "away_defense = self._regress_to_mean(" in line:
        for j in range(i, min(i+5, len(lines))):
            if "location='away'" in lines[j] and ")" in lines[j]:
                lines[j] = lines[j].replace("location='away')", "location='away', tier_diff=tier_diff_pre)")
                modified_calls += 1
                break
    elif "away_attack = self._regress_to_mean(" in line:
        for j in range(i, min(i+5, len(lines))):
            if "location='away'" in lines[j] and ")" in lines[j]:
                lines[j] = lines[j].replace("location='away')", "location='away', tier_diff=tier_diff_pre)")
                modified_calls += 1
                break
    elif "home_defense = self._regress_to_mean(" in line:
        for j in range(i, min(i+5, len(lines))):
            if "location='home'" in lines[j] and ")" in lines[j]:
                lines[j] = lines[j].replace("location='home')", "location='home', tier_diff=tier_diff_pre)")
                modified_calls += 1
                break

print(f"✅ 4. {modified_calls} appels _regress_to_mean modifiés avec tier_diff")

with open('orchestrator_v10_quant_engine.py', 'w') as f:
    f.writelines(lines)

print("\n✅ Patch V10.5 (Hybrid Smart Regression) appliqué!")
