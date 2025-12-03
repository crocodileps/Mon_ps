#!/usr/bin/env python3
"""
Patch V10.1 - Améliorer calcul xG avec défense adverse
xG = moyenne(attaque équipe, défense adverse)
"""

with open('orchestrator_v10_quant_engine.py', 'r') as f:
    content = f.read()

# Code actuel
old_xg = '''        impact = LineupImpact()
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

# Code amélioré avec défense adverse
new_xg = '''        impact = LineupImpact()
        # ═══════════════════════════════════════════════════════
        # xG V10.1 - Prend en compte ATTAQUE + DÉFENSE ADVERSE
        # xG = moyenne(attaque équipe, défense adverse)
        # ═══════════════════════════════════════════════════════
        
        # HOME xG = moyenne(home_scored, away_conceded)
        home_attack = 1.3  # default
        away_defense = 1.3  # default (buts encaissés par away)
        
        if home_intel:
            xg = home_intel.get('xg_for_avg')
            if xg is None or xg == 0:
                xg = home_intel.get('home_goals_scored_avg')
            home_attack = float(xg) if xg else 1.3
        
        if away_intel:
            # Défense adverse = buts encaissés par l'équipe away
            away_def = away_intel.get('away_goals_conceded_avg')
            if away_def:
                away_defense = float(away_def)
        
        # xG home = moyenne pondérée (attaque 60%, défense adverse 40%)
        impact.home_base_xg = (home_attack * 0.6) + (away_defense * 0.4)
        
        # AWAY xG = moyenne(away_scored, home_conceded)
        away_attack = 1.1  # default
        home_defense = 1.1  # default (buts encaissés par home)
        
        if away_intel:
            xg = away_intel.get('xg_for_avg')
            if xg is None or xg == 0:
                xg = away_intel.get('away_goals_scored_avg')
            away_attack = float(xg) if xg else 1.1
        
        if home_intel:
            # Défense home = buts encaissés par l'équipe home
            home_def = home_intel.get('home_goals_conceded_avg')
            if home_def:
                home_defense = float(home_def)
        
        # xG away = moyenne pondérée (attaque 60%, défense adverse 40%)
        impact.away_base_xg = (away_attack * 0.6) + (home_defense * 0.4)'''

if old_xg in content:
    content = content.replace(old_xg, new_xg)
    with open('orchestrator_v10_quant_engine.py', 'w') as f:
        f.write(content)
    print("✅ Patch xG avec défense adverse appliqué!")
    print("   - home_xg = 60% attaque home + 40% défense away")
    print("   - away_xg = 60% attaque away + 40% défense home")
else:
    print("❌ Pattern xG non trouvé")
    # Debug
    print("\nRecherche du pattern...")
    if "impact = LineupImpact()" in content:
        print("   'impact = LineupImpact()' trouvé")
    if "xG de base - priorité" in content:
        print("   'xG de base - priorité' trouvé")
