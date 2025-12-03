#!/usr/bin/env python3
"""Ajouter la méthode _get_competition_stats à LineupImpactEngine"""

with open('orchestrator_v10_quant_engine.py', 'r') as f:
    lines = f.readlines()

# Trouver la ligne "def calculate_impact" dans LineupImpactEngine
insert_line = None
for i, line in enumerate(lines):
    if 'def calculate_impact(self, home_team: str, away_team: str,' in line:
        insert_line = i
        break

if insert_line is None:
    print("❌ Ligne d'insertion non trouvée")
    exit(1)

# Méthode à ajouter AVANT calculate_impact
method_code = '''
    def _get_competition_stats(self, team_name: str, location: str, competition: str) -> Dict:
        """Stats filtrées par compétition depuis match_results"""
        if not self.conn or not competition:
            return {}
        
        try:
            import psycopg2.extras
            
            # Mapping coupes -> ligues domestiques
            league_map = {
                'league cup': '%premier%', 'carabao': '%premier%', 'fa cup': '%premier%',
                'copa del rey': '%liga%', 'dfb pokal': '%bundesliga%',
                'coppa italia': '%serie%', 'coupe de france': '%ligue 1%',
            }
            
            comp_lower = competition.lower()
            league_filter = None
            for key, val in league_map.items():
                if key in comp_lower:
                    league_filter = val
                    break
            
            if not league_filter:
                league_filter = f"%{competition}%"
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                if location == 'home':
                    cur.execute("""
                        SELECT AVG(score_home) as scored, AVG(score_away) as conceded, COUNT(*) as n
                        FROM match_results
                        WHERE LOWER(home_team) LIKE %s AND is_finished = TRUE
                          AND LOWER(league) LIKE %s
                    """, (f"%{team_name.lower()}%", league_filter))
                else:
                    cur.execute("""
                        SELECT AVG(score_away) as scored, AVG(score_home) as conceded, COUNT(*) as n
                        FROM match_results
                        WHERE LOWER(away_team) LIKE %s AND is_finished = TRUE
                          AND LOWER(league) LIKE %s
                    """, (f"%{team_name.lower()}%", league_filter))
                
                row = cur.fetchone()
                if row and row['n'] and row['n'] >= 3:
                    return {
                        'goals_scored_avg': float(row['scored']) if row['scored'] else None,
                        'goals_conceded_avg': float(row['conceded']) if row['conceded'] else None,
                    }
            return {}
        except Exception as e:
            return {}

'''

# Insérer avant calculate_impact
lines.insert(insert_line, method_code)
print(f"✅ Méthode _get_competition_stats ajoutée (ligne {insert_line})")

with open('orchestrator_v10_quant_engine.py', 'w') as f:
    f.writelines(lines)

print("✅ Méthode ajoutée à LineupImpactEngine!")
