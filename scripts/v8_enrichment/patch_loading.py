#!/usr/bin/env python3
"""Patch le script pour corriger le chargement"""

import re

with open('defender_dna_deep_analysis.py', 'r') as f:
    content = f.read()

# Remplacer la section de chargement defense_dna
old_pattern = r"# Defense DNA V5\.1\ndefense_dna_path = DATA_DIR / 'defense_dna' / 'team_defense_dna_v5_1_corrected\.json'\nif defense_dna_path\.exists\(\):\n    with open\(defense_dna_path, 'r'\) as f:\n        team_defense_dna = json\.load\(f\)\n    print\(f\"   ✅ \{len\(team_defense_dna\)\} équipes defense DNA\"\)\nelse:\n    team_defense_dna = \{\}\n    print\(f\"   ⚠️ Defense DNA non trouvé\"\)"

new_section = """# Defense DNA V5.1
defense_dna_path = DATA_DIR / 'defense_dna' / 'team_defense_dna_v5_1_corrected.json'
if defense_dna_path.exists():
    with open(defense_dna_path, 'r') as f:
        defense_raw = json.load(f)
    # Convertir en dict si c'est une liste
    if isinstance(defense_raw, list):
        team_defense_dna = {}
        for item in defense_raw:
            if isinstance(item, dict):
                team_name = item.get('team', item.get('team_name', ''))
                if team_name:
                    team_defense_dna[team_name] = item
    else:
        team_defense_dna = defense_raw
    print(f"   ✅ {len(team_defense_dna)} équipes defense DNA")
else:
    team_defense_dna = {}
    print(f"   ⚠️ Defense DNA non trouvé")"""

# Simple replacement
content = content.replace(
    """# Defense DNA V5.1
defense_dna_path = DATA_DIR / 'defense_dna' / 'team_defense_dna_v5_1_corrected.json'
if defense_dna_path.exists():
    with open(defense_dna_path, 'r') as f:
        team_defense_dna = json.load(f)
    print(f"   ✅ {len(team_defense_dna)} équipes defense DNA")
else:
    team_defense_dna = {}
    print(f"   ⚠️ Defense DNA non trouvé")""",
    new_section
)

with open('defender_dna_deep_analysis.py', 'w') as f:
    f.write(content)

print("✅ Patch appliqué")
