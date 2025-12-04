#!/usr/bin/env python3
"""
Corrige le layer team_class pour utiliser les bonnes colonnes
"""

with open('orchestrator_v11_3_full_analysis.py', 'r') as f:
    content = f.read()

# Ancien code bugué
old_code = '''    def _analyze_team_class(self, home, away):
        h_data = match_team(home, self.cache['team_class'])
        a_data = match_team(away, self.cache['team_class'])
        
        h_power = float(h_data.get('power_index') or 50) if h_data else 50
        a_power = float(a_data.get('power_index') or 50) if a_data else 50
        h_attack = float(h_data.get('attack_rating') or 50) if h_data else 50
        a_attack = float(a_data.get('attack_rating') or 50) if a_data else 50
        h_defense = float(h_data.get('defense_rating') or 50) if h_data else 50
        a_defense = float(a_data.get('defense_rating') or 50) if a_data else 50
        
        power_diff = abs(h_power - a_power)
        attack_combined = (h_attack + a_attack) / 2
        defense_weakness = 100 - (h_defense + a_defense) / 2
        
        score = (power_diff / 10) + (attack_combined - 50) / 20 + (defense_weakness - 50) / 25
        score = max(0, min(10, score))
        
        found = "2/2" if (h_data and a_data) else ("1/2" if (h_data or a_data) else "0/2")
        return {'score': score, 'power_diff': power_diff, 'attack_combined': attack_combined, 'reason': f"Diff:{power_diff:.0f} ({found})"}'''

# Nouveau code corrigé
new_code = '''    def _analyze_team_class(self, home, away):
        h_data = match_team(home, self.cache['team_class'])
        a_data = match_team(away, self.cache['team_class'])
        
        # Utiliser calculated_power_index (pas power_index)
        h_power = float(h_data.get('calculated_power_index') or h_data.get('historical_strength') or 50) if h_data else 50
        a_power = float(a_data.get('calculated_power_index') or a_data.get('historical_strength') or 50) if a_data else 50
        
        # Utiliser historical_strength comme proxy pour attack (pas attack_rating qui n'existe pas)
        h_attack = float(h_data.get('historical_strength') or 50) if h_data else 50
        a_attack = float(a_data.get('historical_strength') or 50) if a_data else 50
        
        # Utiliser big_game_factor comme indicateur de qualité défensive
        h_big_game = float(h_data.get('big_game_factor') or 1.0) if h_data else 1.0
        a_big_game = float(a_data.get('big_game_factor') or 1.0) if a_data else 1.0
        
        power_diff = abs(h_power - a_power)
        attack_combined = (h_attack + a_attack) / 2
        big_game_boost = (h_big_game + a_big_game - 2) * 2  # Bonus si gros matchs
        
        # Score basé sur: différence de power + force combinée + bonus big game
        score = (power_diff / 15) + ((attack_combined - 50) / 15) + big_game_boost
        score = max(0, min(10, score))
        
        found = "2/2" if (h_data and a_data) else ("1/2" if (h_data or a_data) else "0/2")
        return {'score': score, 'power_diff': power_diff, 'attack_combined': attack_combined, 'reason': f"Power:{h_power:.0f}v{a_power:.0f} ({found})"}'''

if old_code in content:
    content = content.replace(old_code, new_code)
    with open('orchestrator_v11_3_full_analysis.py', 'w') as f:
        f.write(content)
    print("✅ Layer team_class corrigé!")
else:
    print("❌ Code non trouvé - vérifier manuellement")
    print("Cherchons le code actuel...")
    import subprocess
    subprocess.run(['grep', '-n', 'power_index', 'orchestrator_v11_3_full_analysis.py'])
