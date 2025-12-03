#!/usr/bin/env python3
"""
PHASE 2.2 - SCORER ENGINE (Team Firepower Intelligence)
Utilise les données réelles de Transfermarkt
"""

SCORER_ENGINE_CODE = '''
    def _get_scorer_intelligence(self, team_name: str, location: str = 'home') -> Optional[Dict]:
        """
        Analyse les buteurs d'une equipe pour evaluer le potentiel offensif.
        Utilise les donnees enrichies par Transfermarkt scraper.
        """
        if not self.conn:
            return None
            
        try:
            variants = self._resolve_team_name(team_name)
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                scorers = []
                for v in variants[:5]:
                    cur.execute("""
                        SELECT player_name, season_goals, COALESCE(season_assists, 0) as assists,
                               goals_per_90, is_hot_streak, is_injured, is_key_player,
                               is_penalty_taker, form_score
                        FROM scorer_intelligence 
                        WHERE LOWER(current_team) LIKE %s
                        AND season_goals > 0
                        ORDER BY season_goals DESC
                        LIMIT 10
                    """, (f'%{v.lower()}%',))
                    
                    rows = cur.fetchall()
                    if rows:
                        scorers = [dict(r) for r in rows]
                        break
                
                if not scorers:
                    return None
                
                # Calculs quantitatifs
                total_goals = sum(s.get('season_goals', 0) or 0 for s in scorers)
                total_assists = sum(s.get('assists', 0) or 0 for s in scorers)
                
                # Firepower = moyenne goals_per_90 des 3 meilleurs
                top_3_gp90 = [float(s.get('goals_per_90', 0) or 0) for s in scorers[:3]]
                firepower_score = sum(top_3_gp90) / 3 if top_3_gp90 else 0
                
                # Top scorer info
                top_scorer = scorers[0] if scorers else None
                top_scorer_goals = top_scorer.get('season_goals', 0) if top_scorer else 0
                
                # Concentration risk (dependance au top scorer)
                concentration_risk = top_scorer_goals / total_goals if total_goals > 0 else 0
                
                # Hot streaks count
                hot_scorers = sum(1 for s in scorers if s.get('is_hot_streak'))
                
                # Injured key players
                injured_key = sum(1 for s in scorers 
                                 if s.get('is_injured') and s.get('is_key_player'))
                injured_any = sum(1 for s in scorers if s.get('is_injured'))
                
                # Injury penalty sur xG
                injury_penalty = 0.0
                if injured_key > 0:
                    injury_penalty = min(0.25, injured_key * 0.12)
                elif injured_any > 2:
                    injury_penalty = 0.08
                
                # Hot streak bonus
                hot_bonus = min(0.15, hot_scorers * 0.05)
                
                # Average form score
                form_scores = [s.get('form_score', 50) or 50 for s in scorers]
                avg_form = sum(form_scores) / len(form_scores) if form_scores else 50
                
                return {
                    'firepower_score': min(1.0, firepower_score),
                    'total_team_goals': total_goals,
                    'total_assists': total_assists,
                    'top_scorer': top_scorer.get('player_name') if top_scorer else None,
                    'top_scorer_goals': top_scorer_goals,
                    'hot_scorers': hot_scorers,
                    'hot_bonus': hot_bonus,
                    'injured_key_players': injured_key,
                    'injured_any': injured_any,
                    'injury_penalty': injury_penalty,
                    'concentration_risk': concentration_risk,
                    'avg_form': avg_form,
                    'scorers_count': len(scorers)
                }
                
        except Exception as e:
            return None

'''

with open('orchestrator_v10_quant_engine.py', 'r') as f:
    content = f.read()

if '_get_scorer_intelligence' not in content:
    insert_marker = '    def _get_h2h_intelligence'
    if insert_marker in content:
        content = content.replace(insert_marker, SCORER_ENGINE_CODE + '\n' + insert_marker)
        print("Scorer Intelligence Engine ajoute")
    else:
        print("Marker non trouve")
else:
    print("Scorer Intelligence deja present")

with open('orchestrator_v10_quant_engine.py', 'w') as f:
    f.write(content)
