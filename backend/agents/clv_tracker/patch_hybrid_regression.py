#!/usr/bin/env python3
"""
Patch V10.5 - Hybrid Smart Regression
Régression pondérée par la différence de tier

Logique:
- tier_diff = 0 → C=10 (régression forte, matchs équilibrés)
- tier_diff = 1 → C=5 (régression moyenne)
- tier_diff >= 2 → C=2 (régression faible, D1 vs D2)

Cela permet:
1. Stabiliser les stats tout en préservant la supériorité de classe
2. Le Tier Boost s'applique ensuite normalement
"""

with open('orchestrator_v10_quant_engine.py', 'r') as f:
    content = f.read()

# Modifier la méthode _regress_to_mean pour accepter tier_diff
old_regress = '''    def _regress_to_mean(self, team_stat: float, sample_size: int,
                          league_avg: float = None, location: str = 'home') -> float:
        """
        V10.4 - Régression vers la moyenne de la ligue

        Formule: adjusted = (team_stat * n + league_avg * C) / (n + C)

        Args:
            team_stat: Statistique brute de l'équipe
            sample_size: Nombre de matchs analysés
            league_avg: Moyenne de la ligue (défaut: 1.3 home, 1.4 away pour scored)
            location: 'home' ou 'away'
        """
        # Constante de régression (poids de la moyenne ligue)
        C = 10  # Équivalent à 10 matchs de "prior"

        # Moyennes par défaut (top 5 ligues européennes)
        if league_avg is None:
            if location == 'home':
                league_avg = 1.55  # Moyenne buts marqués à domicile
            else:
                league_avg = 1.25  # Moyenne buts marqués à l'extérieur

        # Régression
        adjusted = (team_stat * sample_size + league_avg * C) / (sample_size + C)

        return round(adjusted, 2)'''

new_regress = '''    def _regress_to_mean(self, team_stat: float, sample_size: int,
                          league_avg: float = None, location: str = 'home',
                          tier_diff: int = 0) -> float:
        """
        V10.5 - Régression HYBRIDE vers la moyenne de la ligue
        
        Pondérée par tier_diff pour préserver les écarts D1 vs D2

        Formule: adjusted = (team_stat * n + league_avg * C) / (n + C)
        où C varie selon tier_diff

        Args:
            team_stat: Statistique brute de l'équipe
            sample_size: Nombre de matchs analysés
            league_avg: Moyenne de la ligue
            location: 'home' ou 'away'
            tier_diff: Différence de tier (0-4)
        """
        # V10.5 - Constante de régression DYNAMIQUE selon tier_diff
        if tier_diff >= 2:
            C = 2   # D1 vs D2: régression faible, préserver l'écart
        elif tier_diff == 1:
            C = 5   # Légère différence: régression moyenne
        else:
            C = 10  # Même niveau: régression forte pour stabilité

        # Moyennes par défaut (top 5 ligues européennes)
        if league_avg is None:
            if location == 'home':
                league_avg = 1.55
            else:
                league_avg = 1.25

        # Régression
        adjusted = (team_stat * sample_size + league_avg * C) / (sample_size + C)

        return round(adjusted, 2)'''

if old_regress in content:
    content = content.replace(old_regress, new_regress)
    print("✅ 1. Méthode _regress_to_mean mise à jour (tier_diff)")
else:
    print("❌ 1. Pattern _regress_to_mean non trouvé")

# Maintenant modifier les appels pour passer tier_diff
# Chercher le bloc de calcul xG avec la smart regression

old_call_home = '''            if home_comp_stats.get('goals_scored_avg'):
                if apply_regression:
                    n = home_comp_stats.get('sample_size', 5)
                    home_attack = self._regress_to_mean(
                        home_comp_stats['goals_scored_avg'], n, location='home'
                    )
                else:
                    # Pas de régression - utiliser stats brutes
                    home_attack = home_comp_stats['goals_scored_avg']
                    
            if away_comp_stats.get('goals_conceded_avg'):
                if apply_regression:
                    n = away_comp_stats.get('sample_size', 5)
                    away_defense = self._regress_to_mean(
                        away_comp_stats['goals_conceded_avg'], n, league_avg=1.35, location='away'
                    )
                else:
                    away_defense = away_comp_stats['goals_conceded_avg']'''

new_call_home = '''            if home_comp_stats.get('goals_scored_avg'):
                # V10.5 - Régression hybride avec tier_diff
                n = home_comp_stats.get('sample_size', 5)
                home_attack = self._regress_to_mean(
                    home_comp_stats['goals_scored_avg'], n, 
                    location='home', tier_diff=tier_diff
                )
                    
            if away_comp_stats.get('goals_conceded_avg'):
                n = away_comp_stats.get('sample_size', 5)
                away_defense = self._regress_to_mean(
                    away_comp_stats['goals_conceded_avg'], n, 
                    league_avg=1.35, location='away', tier_diff=tier_diff
                )'''

if old_call_home in content:
    content = content.replace(old_call_home, new_call_home)
    print("✅ 2. Appels HOME mis à jour avec tier_diff")
else:
    print("❌ 2. Pattern appels HOME non trouvé")

old_call_away = '''        # Priorité 1: Stats filtrées par compétition
        if competition and self.conn:
            if away_comp_stats.get('goals_scored_avg'):
                if apply_regression:
                    n = away_comp_stats.get('sample_size', 5)
                    away_attack = self._regress_to_mean(
                        away_comp_stats['goals_scored_avg'], n, location='away'
                    )
                else:
                    away_attack = away_comp_stats['goals_scored_avg']
                    
            if home_comp_stats.get('goals_conceded_avg'):
                if apply_regression:
                    n = home_comp_stats.get('sample_size', 5)
                    home_defense = self._regress_to_mean(
                        home_comp_stats['goals_conceded_avg'], n, league_avg=1.20, location='home'
                    )
                else:
                    home_defense = home_comp_stats['goals_conceded_avg']'''

new_call_away = '''        # Priorité 1: Stats filtrées par compétition
        if competition and self.conn:
            if away_comp_stats.get('goals_scored_avg'):
                # V10.5 - Régression hybride
                n = away_comp_stats.get('sample_size', 5)
                away_attack = self._regress_to_mean(
                    away_comp_stats['goals_scored_avg'], n, 
                    location='away', tier_diff=tier_diff
                )
                    
            if home_comp_stats.get('goals_conceded_avg'):
                n = home_comp_stats.get('sample_size', 5)
                home_defense = self._regress_to_mean(
                    home_comp_stats['goals_conceded_avg'], n, 
                    league_avg=1.20, location='home', tier_diff=tier_diff
                )'''

if old_call_away in content:
    content = content.replace(old_call_away, new_call_away)
    print("✅ 3. Appels AWAY mis à jour avec tier_diff")
else:
    print("❌ 3. Pattern appels AWAY non trouvé")

# Supprimer la variable apply_regression qui n'est plus utilisée
old_apply = '''        # V10.4b - Vérifier tier_diff pour décider si régression
        home_tier = home_class.get('tier', 'B') if home_class else 'B'
        away_tier = away_class.get('tier', 'B') if away_class else 'B'
        tier_values = {'S': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1}
        tier_diff = abs(tier_values.get(home_tier, 3) - tier_values.get(away_tier, 3))
        
        # Si mismatch de niveau (D1 vs D2), pas de régression
        apply_regression = tier_diff < 2'''

new_apply = '''        # V10.5 - Calcul tier_diff pour régression hybride
        home_tier = home_class.get('tier', 'B') if home_class else 'B'
        away_tier = away_class.get('tier', 'B') if away_class else 'B'
        tier_values = {'S': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1}
        tier_diff = abs(tier_values.get(home_tier, 3) - tier_values.get(away_tier, 3))'''

if old_apply in content:
    content = content.replace(old_apply, new_apply)
    print("✅ 4. Variable apply_regression supprimée")
else:
    print("❌ 4. Pattern apply_regression non trouvé")

with open('orchestrator_v10_quant_engine.py', 'w') as f:
    f.write(content)

print("\n✅ Patch V10.5 (Hybrid Smart Regression) appliqué!")
print("   - tier_diff >= 2: C=2 (faible régression)")
print("   - tier_diff = 1:  C=5 (moyenne)")
print("   - tier_diff = 0:  C=10 (forte)")
