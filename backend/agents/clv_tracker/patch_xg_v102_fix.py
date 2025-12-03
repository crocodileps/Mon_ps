#!/usr/bin/env python3
"""
Fix V10.2 - Utiliser self.conn directement pour le filtrage compétition
"""

with open('orchestrator_v10_quant_engine.py', 'r') as f:
    content = f.read()

# Code actuel bugué (utilise self.orchestrator qui n'existe pas)
old_block = '''        # Priorité 1: Stats filtrées par compétition (si disponibles)
        if competition and hasattr(self, 'orchestrator') and self.orchestrator:
            home_comp_stats = self.orchestrator._get_competition_adjusted_stats(home_team, 'home', competition)
            away_comp_stats = self.orchestrator._get_competition_adjusted_stats(away_team, 'away', competition)
            
            if home_comp_stats.get('goals_scored_avg'):
                home_attack = home_comp_stats['goals_scored_avg']
            if away_comp_stats.get('goals_conceded_avg'):
                away_defense = away_comp_stats['goals_conceded_avg']'''

# Nouveau code fonctionnel
new_block = '''        # Priorité 1: Stats filtrées par compétition (si disponibles)
        home_comp_stats = {}
        away_comp_stats = {}
        if competition and self.conn:
            home_comp_stats = self._get_competition_stats(home_team, 'home', competition)
            away_comp_stats = self._get_competition_stats(away_team, 'away', competition)
            
            if home_comp_stats.get('goals_scored_avg'):
                home_attack = home_comp_stats['goals_scored_avg']
            if away_comp_stats.get('goals_conceded_avg'):
                away_defense = away_comp_stats['goals_conceded_avg']'''

if old_block in content:
    content = content.replace(old_block, new_block)
    print("✅ 1. Bloc home stats corrigé")
else:
    print("❌ 1. Bloc home stats non trouvé")

# Corriger aussi le bloc away
old_away = '''        # Priorité 1: Stats filtrées par compétition
        if competition and hasattr(self, 'orchestrator') and self.orchestrator:
            if away_comp_stats.get('goals_scored_avg'):
                away_attack = away_comp_stats['goals_scored_avg']
            if home_comp_stats.get('goals_conceded_avg'):
                home_defense = home_comp_stats['goals_conceded_avg']'''

new_away = '''        # Priorité 1: Stats filtrées par compétition
        if competition and self.conn:
            if away_comp_stats.get('goals_scored_avg'):
                away_attack = away_comp_stats['goals_scored_avg']
            if home_comp_stats.get('goals_conceded_avg'):
                home_defense = home_comp_stats['goals_conceded_avg']'''

if old_away in content:
    content = content.replace(old_away, new_away)
    print("✅ 2. Bloc away stats corrigé")
else:
    print("❌ 2. Bloc away stats non trouvé")

with open('orchestrator_v10_quant_engine.py', 'w') as f:
    f.write(content)

print("\n✅ Fix V10.2 appliqué!")
