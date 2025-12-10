#!/usr/bin/env python3
"""
Réparation chirurgicale du fichier orchestrator_v10_quant_engine.py
Le bloc SMART HYBRID SCORING est dupliqué 16 fois - on garde 1 seul
"""

with open('orchestrator_v10_quant_engine.py', 'r') as f:
    lines = f.readlines()

print(f"Fichier original: {len(lines)} lignes")

# Trouver la première occurrence de "SMART HYBRID SCORING 2.0"
first_smart = None
last_smart_end = None

for i, line in enumerate(lines):
    if "# SMART HYBRID SCORING 2.0" in line:
        if first_smart is None:
            first_smart = i
            print(f"Première occurrence ligne {i+1}")
        last_smart_end = i
        
# Trouver la ligne "return max(-LAYER_WEIGHTS" après les duplications
return_line = None
for i in range(last_smart_end, len(lines)):
    if "return max(-LAYER_WEIGHTS" in lines[i]:
        return_line = i
        print(f"Return trouvé ligne {i+1}")
        break

if first_smart and return_line:
    # Le bloc correct est de first_smart à first_smart+4 (5 lignes)
    # Puis on saute jusqu'à return_line
    
    print(f"\nZone corrompue: lignes {first_smart+1} à {return_line}")
    print(f"Lignes à supprimer: {return_line - first_smart - 5}")
    
    # Construire le nouveau fichier
    new_lines = []
    
    # Avant la corruption
    new_lines.extend(lines[:first_smart])
    
    # Le bloc SMART HYBRID correct (1 seule fois)
    new_lines.append("        # SMART HYBRID SCORING 2.0\n")
    new_lines.append("        # Score continu: Edge 5% = 10pts, Edge 10% = 20pts\n")
    new_lines.append("        base_score = pick.mc_edge * 200\n")
    new_lines.append("        confidence_factor = mc_result.confidence_score\n")
    new_lines.append("        \n")
    new_lines.append("        # Sweet Spot bonus (3-8% = +25%), Suspect penalty (>15% = -20%)\n")
    new_lines.append("        if 0.03 <= pick.mc_edge <= 0.08:\n")
    new_lines.append("            sweet_spot = 1.25\n")
    new_lines.append("        elif pick.mc_edge > 0.15:\n")
    new_lines.append("            sweet_spot = 0.8\n")
    new_lines.append("        else:\n")
    new_lines.append("            sweet_spot = 1.0\n")
    new_lines.append("        \n")
    new_lines.append("        score = int(base_score * confidence_factor * sweet_spot)\n")
    new_lines.append("        \n")
    
    # A partir du return
    new_lines.extend(lines[return_line:])
    
    print(f"Nouveau fichier: {len(new_lines)} lignes")
    
    # Sauvegarder
    with open('orchestrator_v10_quant_engine.py', 'w') as f:
        f.writelines(new_lines)
    
    print("\n✅ Fichier réparé!")
else:
    print("❌ Impossible de trouver les marqueurs")
