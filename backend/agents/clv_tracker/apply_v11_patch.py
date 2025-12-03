#!/usr/bin/env python3
"""Patch ciblé V10.1 - Game State + Spread"""

# Lire le fichier
with open('orchestrator_v10_quant_engine.py', 'r') as f:
    lines = f.readlines()

# ============================================================
# 1. GAME STATE - Insérer après "for minute in range(1, 91):"
# ============================================================
game_state_code = '''            # ═══════════════════════════════════════════════════════
            # GAME STATE DYNAMICS V10.1 - Ajuster xG selon score/temps
            # ═══════════════════════════════════════════════════════
            goal_diff = home_goals - away_goals
            home_gs_factor = 1.0
            away_gs_factor = 1.0
            
            if minute >= 60:  # Dernière demi-heure
                if goal_diff >= 2:
                    home_gs_factor, away_gs_factor = 0.7, 1.4  # Home défend
                elif goal_diff == 1:
                    home_gs_factor, away_gs_factor = 0.85, 1.2
                elif goal_diff == -1:
                    home_gs_factor, away_gs_factor = 1.2, 0.85
                elif goal_diff <= -2:
                    home_gs_factor, away_gs_factor = 1.4, 0.7  # Home pousse
            
            if minute >= 75:  # 15 dernières minutes = intensité max
                if goal_diff >= 1:
                    home_gs_factor, away_gs_factor = 0.6, 1.5
                elif goal_diff <= -1:
                    home_gs_factor, away_gs_factor = 1.5, 0.6
            
            # Appliquer Game State aux xG
            adj_home_xg = home_xg_per_min * home_gs_factor
            adj_away_xg = away_xg_per_min * away_gs_factor

'''

# Trouver la ligne "for minute in range(1, 91):"
inserted_gs = False
for i, line in enumerate(lines):
    if 'for minute in range(1, 91):' in line and not inserted_gs:
        # Insérer après cette ligne
        lines.insert(i + 1, game_state_code)
        inserted_gs = True
        print(f"✅ 1. Game State inséré après ligne {i+1}")
        break

if not inserted_gs:
    print("❌ 1. Ligne 'for minute in range' non trouvée")

# ============================================================
# 2. Modifier les références home_xg_per_min -> adj_home_xg
# ============================================================
# Remplacer dans le calcul de probabilité (après notre insertion)
modified = False
for i, line in enumerate(lines):
    if 'home_prob = home_xg_per_min * home_momentum' in line:
        lines[i] = line.replace('home_xg_per_min', 'adj_home_xg')
        modified = True
        print(f"✅ 2a. home_xg_per_min -> adj_home_xg (ligne {i+1})")
    if 'away_prob = away_xg_per_min * away_momentum' in line:
        lines[i] = line.replace('away_xg_per_min', 'adj_away_xg')
        print(f"✅ 2b. away_xg_per_min -> adj_away_xg (ligne {i+1})")

# ============================================================
# 3. SPREAD/LIQUIDITÉ - Modifier _detect_steam
# ============================================================
# Trouver la ligne avec le calcul de movement_pct et ajouter après
spread_code = '''
        # ═══════════════════════════════════════════════════════
        # SPREAD/LIQUIDITÉ V10.1 - Pondérer par liquidité du marché
        # ═══════════════════════════════════════════════════════
        steam_importance = 1.0
        last_record = recent[-1] if recent else {}
        h_odds = last_record.get('home_odds')
        d_odds = last_record.get('draw_odds')
        a_odds = last_record.get('away_odds')
        
        if h_odds and d_odds and a_odds:
            try:
                spread = (1/float(h_odds) + 1/float(d_odds) + 1/float(a_odds)) - 1
                if spread < 0.03:
                    steam_importance = 1.5  # Très liquide = signal fort
                elif spread < 0.05:
                    steam_importance = 1.0  # Normal
                elif spread < 0.07:
                    steam_importance = 0.7  # Peu liquide
                else:
                    steam_importance = 0.3  # Illiquide = ignorer
            except:
                pass
        
        # Ajuster le seuil par liquidité
        adjusted_threshold = self.config['steam_threshold_pct'] / steam_importance
        movement_pct_adj = abs(movement_pct) * steam_importance

'''

inserted_spread = False
for i, line in enumerate(lines):
    if "movement_pct = (last_recent - first_recent)" in line:
        # Insérer après cette ligne
        lines.insert(i + 1, spread_code)
        inserted_spread = True
        print(f"✅ 3. Spread/Liquidité inséré après ligne {i+1}")
        break

if not inserted_spread:
    print("❌ 3. Ligne movement_pct non trouvée")

# ============================================================
# 4. Modifier la condition de steam pour utiliser adjusted_threshold
# ============================================================
for i, line in enumerate(lines):
    if "if abs(movement_pct) >= self.config['steam_threshold_pct']:" in line:
        lines[i] = "        if abs(movement_pct) >= adjusted_threshold:\n"
        print(f"✅ 4. Condition steam modifiée (ligne {i+1})")
        break

# Sauvegarder
with open('orchestrator_v10_quant_engine.py', 'w') as f:
    f.writelines(lines)

print("\n✅ Patch V10.1 appliqué avec succès!")
