#!/usr/bin/env python3
"""
Patch V10.1 -> V10.2 : Filtrage par compétition
Calcule les stats depuis match_results filtré par type de compétition
"""

with open('orchestrator_v10_quant_engine.py', 'r') as f:
    lines = f.readlines()

# Trouver où ajouter la nouvelle méthode (après _get_team_intelligence)
insert_line = None
for i, line in enumerate(lines):
    if 'def _get_team_momentum' in line:
        insert_line = i
        break

if insert_line is None:
    print("❌ Ligne d'insertion non trouvée")
    exit(1)

# Nouvelle méthode pour stats filtrées par compétition
new_method = '''
    def _get_competition_adjusted_stats(self, team_name: str, location: str, competition: str = None) -> Dict:
        """
        V10.2 - Calcule les stats depuis match_results filtré par type de compétition
        
        Args:
            team_name: Nom de l'équipe
            location: 'home' ou 'away'
            competition: Type de compétition (ex: 'Premier League', 'La Liga', 'League Cup')
        
        Returns:
            Dict avec goals_scored_avg, goals_conceded_avg ajustés
        """
        if not self.conn or not competition:
            return {}
        
        try:
            # Déterminer le type de compétition (ligue domestique vs coupe)
            competition_lower = competition.lower()
            
            # Mapping vers ligues domestiques
            domestic_leagues = {
                'premier league': ['premier league', 'epl'],
                'la liga': ['la liga', 'laliga'],
                'bundesliga': ['bundesliga'],
                'serie a': ['serie a'],
                'ligue 1': ['ligue 1'],
                'league cup': ['premier league', 'epl'],  # Utiliser stats PL pour coupes anglaises
                'fa cup': ['premier league', 'epl'],
                'carabao cup': ['premier league', 'epl'],
                'copa del rey': ['la liga'],
                'dfb pokal': ['bundesliga'],
                'coppa italia': ['serie a'],
                'coupe de france': ['ligue 1'],
            }
            
            # Trouver les ligues à utiliser
            league_filters = None
            for key, values in domestic_leagues.items():
                if key in competition_lower:
                    league_filters = values
                    break
            
            if not league_filters:
                # Par défaut, utiliser la compétition telle quelle
                league_filters = [competition_lower]
            
            # Construire la requête
            where, params = self._build_name_where(
                'home_team' if location == 'home' else 'away_team', 
                team_name
            )
            
            # Filtres de ligue
            league_conditions = " OR ".join([f"LOWER(league) LIKE %s" for _ in league_filters])
            league_params = [f"%{lf}%" for lf in league_filters]
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                if location == 'home':
                    cur.execute(f"""
                        SELECT 
                            AVG(score_home) as goals_scored_avg,
                            AVG(score_away) as goals_conceded_avg,
                            COUNT(*) as matches
                        FROM match_results
                        WHERE {where}
                          AND is_finished = TRUE
                          AND ({league_conditions})
                    """, params + league_params)
                else:
                    cur.execute(f"""
                        SELECT 
                            AVG(score_away) as goals_scored_avg,
                            AVG(score_home) as goals_conceded_avg,
                            COUNT(*) as matches
                        FROM match_results
                        WHERE {where}
                          AND is_finished = TRUE
                          AND ({league_conditions})
                    """, params + league_params)
                
                row = cur.fetchone()
                if row and row['matches'] and row['matches'] >= 3:
                    return {
                        'goals_scored_avg': float(row['goals_scored_avg']) if row['goals_scored_avg'] else None,
                        'goals_conceded_avg': float(row['goals_conceded_avg']) if row['goals_conceded_avg'] else None,
                        'matches': row['matches'],
                        'source': 'competition_filtered'
                    }
            
            return {}
            
        except Exception as e:
            logger.debug(f"Competition stats error: {e}")
            return {}

'''

# Insérer la nouvelle méthode
lines.insert(insert_line, new_method)
print(f"✅ Méthode _get_competition_adjusted_stats ajoutée (ligne {insert_line})")

# Sauvegarder
with open('orchestrator_v10_quant_engine.py', 'w') as f:
    f.writelines(lines)

print("✅ Patch V10.2 (Competition Filter) appliqué!")
print("   Nouvelle méthode: _get_competition_adjusted_stats()")
print("   Utilise match_results filtré par type de compétition")
