#!/usr/bin/env python3
"""
Patch V10.4 - Régression vers la moyenne de la ligue
Stabilise les stats quand le sample size est faible

Formule: adjusted = (team_stat * n + league_avg * C) / (n + C)
où C = constante de régression (ex: 10 matchs)
"""

with open('orchestrator_v10_quant_engine.py', 'r') as f:
    content = f.read()

# Ajouter la méthode de régression dans LineupImpactEngine
# Chercher la fin de _get_competition_stats

old_method_end = '''            return {}
        except Exception as e:
            return {}

    def calculate_impact'''

new_method = '''            return {}
        except Exception as e:
            return {}

    def _regress_to_mean(self, team_stat: float, sample_size: int, 
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
        
        return round(adjusted, 2)

    def calculate_impact'''

if old_method_end in content:
    content = content.replace(old_method_end, new_method)
    print("✅ 1. Méthode _regress_to_mean ajoutée")
else:
    print("❌ 1. Pattern non trouvé pour _regress_to_mean")

# Maintenant modifier _get_competition_stats pour retourner aussi le sample size
old_return = '''                if row and row['n'] and row['n'] >= 3:
                    return {
                        'goals_scored_avg': float(row['scored']) if row['scored'] else None,
                        'goals_conceded_avg': float(row['conceded']) if row['conceded'] else None,
                    }'''

new_return = '''                if row and row['n'] and row['n'] >= 3:
                    return {
                        'goals_scored_avg': float(row['scored']) if row['scored'] else None,
                        'goals_conceded_avg': float(row['conceded']) if row['conceded'] else None,
                        'sample_size': row['n'],
                    }'''

if old_return in content:
    content = content.replace(old_return, new_return)
    print("✅ 2. sample_size ajouté au retour")
else:
    print("❌ 2. Pattern retour non trouvé")

# Modifier le calcul xG pour utiliser la régression
old_xg_home = '''        # Priorité 1: Stats filtrées par compétition (si disponibles)
        home_comp_stats = {}
        away_comp_stats = {}
        if competition and self.conn:
            home_comp_stats = self._get_competition_stats(home_team, 'home', competition)
            away_comp_stats = self._get_competition_stats(away_team, 'away', competition)
            
            if home_comp_stats.get('goals_scored_avg'):
                home_attack = home_comp_stats['goals_scored_avg']
            if away_comp_stats.get('goals_conceded_avg'):
                away_defense = away_comp_stats['goals_conceded_avg']'''

new_xg_home = '''        # Priorité 1: Stats filtrées par compétition (si disponibles)
        home_comp_stats = {}
        away_comp_stats = {}
        if competition and self.conn:
            home_comp_stats = self._get_competition_stats(home_team, 'home', competition)
            away_comp_stats = self._get_competition_stats(away_team, 'away', competition)
            
            if home_comp_stats.get('goals_scored_avg'):
                # V10.4 - Régression vers la moyenne si sample faible
                n = home_comp_stats.get('sample_size', 5)
                home_attack = self._regress_to_mean(
                    home_comp_stats['goals_scored_avg'], n, location='home'
                )
            if away_comp_stats.get('goals_conceded_avg'):
                n = away_comp_stats.get('sample_size', 5)
                away_defense = self._regress_to_mean(
                    away_comp_stats['goals_conceded_avg'], n, league_avg=1.35, location='away'
                )'''

if old_xg_home in content:
    content = content.replace(old_xg_home, new_xg_home)
    print("✅ 3. Régression appliquée au calcul xG home")
else:
    print("❌ 3. Pattern xG home non trouvé")

# Modifier aussi pour away
old_xg_away = '''        # Priorité 1: Stats filtrées par compétition
        if competition and self.conn:
            if away_comp_stats.get('goals_scored_avg'):
                away_attack = away_comp_stats['goals_scored_avg']
            if home_comp_stats.get('goals_conceded_avg'):
                home_defense = home_comp_stats['goals_conceded_avg']'''

new_xg_away = '''        # Priorité 1: Stats filtrées par compétition
        if competition and self.conn:
            if away_comp_stats.get('goals_scored_avg'):
                n = away_comp_stats.get('sample_size', 5)
                away_attack = self._regress_to_mean(
                    away_comp_stats['goals_scored_avg'], n, location='away'
                )
            if home_comp_stats.get('goals_conceded_avg'):
                n = home_comp_stats.get('sample_size', 5)
                home_defense = self._regress_to_mean(
                    home_comp_stats['goals_conceded_avg'], n, league_avg=1.20, location='home'
                )'''

if old_xg_away in content:
    content = content.replace(old_xg_away, new_xg_away)
    print("✅ 4. Régression appliquée au calcul xG away")
else:
    print("❌ 4. Pattern xG away non trouvé")

with open('orchestrator_v10_quant_engine.py', 'w') as f:
    f.write(content)

print("\n✅ Patch V10.4 (Régression vers la moyenne) appliqué!")
