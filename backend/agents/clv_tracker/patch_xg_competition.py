#!/usr/bin/env python3
"""
Patch V10.2 - Utiliser stats filtrées par compétition dans le calcul xG
"""

with open('orchestrator_v10_quant_engine.py', 'r') as f:
    content = f.read()

# Code actuel xG V10.1
old_xg = '''        impact = LineupImpact()
        
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
        
        impact.away_base_xg = (away_attack * 0.6) + (home_defense * 0.4)'''

# Nouveau code xG V10.2 avec filtrage compétition
new_xg = '''        impact = LineupImpact()
        
        # ═══════════════════════════════════════════════════════
        # xG V10.2 - ATTAQUE + DÉFENSE ADVERSE + FILTRAGE COMPÉTITION
        # ═══════════════════════════════════════════════════════
        
        competition = context.get('competition') if context else None
        
        # HOME xG = 60% attaque home + 40% défense away
        home_attack = 1.3
        away_defense = 1.3
        
        # Priorité 1: Stats filtrées par compétition (si disponibles)
        if competition and hasattr(self, 'orchestrator') and self.orchestrator:
            home_comp_stats = self.orchestrator._get_competition_adjusted_stats(home_team, 'home', competition)
            away_comp_stats = self.orchestrator._get_competition_adjusted_stats(away_team, 'away', competition)
            
            if home_comp_stats.get('goals_scored_avg'):
                home_attack = home_comp_stats['goals_scored_avg']
            if away_comp_stats.get('goals_conceded_avg'):
                away_defense = away_comp_stats['goals_conceded_avg']
        
        # Priorité 2: Stats team_intelligence (fallback)
        if home_attack == 1.3 and home_intel:
            xg = home_intel.get('xg_for_avg')
            if xg is None or xg == 0:
                xg = home_intel.get('home_goals_scored_avg')
            home_attack = float(xg) if xg else 1.3
        
        if away_defense == 1.3 and away_intel:
            away_def = away_intel.get('away_goals_conceded_avg')
            if away_def:
                away_defense = float(away_def)
        
        impact.home_base_xg = (home_attack * 0.6) + (away_defense * 0.4)
        
        # AWAY xG = 60% attaque away + 40% défense home
        away_attack = 1.1
        home_defense = 1.1
        
        # Priorité 1: Stats filtrées par compétition
        if competition and hasattr(self, 'orchestrator') and self.orchestrator:
            if away_comp_stats.get('goals_scored_avg'):
                away_attack = away_comp_stats['goals_scored_avg']
            if home_comp_stats.get('goals_conceded_avg'):
                home_defense = home_comp_stats['goals_conceded_avg']
        
        # Priorité 2: Stats team_intelligence (fallback)
        if away_attack == 1.1 and away_intel:
            xg = away_intel.get('xg_for_avg')
            if xg is None or xg == 0:
                xg = away_intel.get('away_goals_scored_avg')
            away_attack = float(xg) if xg else 1.1
        
        if home_defense == 1.1 and home_intel:
            home_def = home_intel.get('home_goals_conceded_avg')
            if home_def:
                home_defense = float(home_def)
        
        impact.away_base_xg = (away_attack * 0.6) + (home_defense * 0.4)'''

if old_xg in content:
    content = content.replace(old_xg, new_xg)
    with open('orchestrator_v10_quant_engine.py', 'w') as f:
        f.write(content)
    print("✅ Patch xG V10.2 (Competition Filter) appliqué!")
else:
    print("❌ Pattern xG V10.1 non trouvé")
    # Debug
    if "xG V10.1" in content:
        print("   'xG V10.1' trouvé mais le bloc complet ne correspond pas")
    if "impact = LineupImpact()" in content:
        print("   'impact = LineupImpact()' trouvé")
