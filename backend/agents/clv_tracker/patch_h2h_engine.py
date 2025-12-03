#!/usr/bin/env python3
"""
PHASE 2.1 - H2H ENGINE (Head-to-Head Intelligence)
"""

H2H_CODE = '''
    def _get_h2h_intelligence(self, home_team: str, away_team: str) -> Optional[Dict]:
        """Recupere et analyse les donnees H2H entre deux equipes."""
        if not self.conn:
            return None
            
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                home_variants = self._resolve_team_name(home_team)
                away_variants = self._resolve_team_name(away_team)
                
                h2h = None
                home_is_team_a = True
                
                for hv in home_variants[:5]:
                    for av in away_variants[:5]:
                        cur.execute("""
                            SELECT * FROM head_to_head 
                            WHERE (LOWER(team_a) = %s AND LOWER(team_b) = %s)
                               OR (LOWER(team_a) = %s AND LOWER(team_b) = %s)
                            LIMIT 1
                        """, (hv.lower(), av.lower(), av.lower(), hv.lower()))
                        
                        row = cur.fetchone()
                        if row:
                            h2h = dict(row)
                            home_is_team_a = h2h['team_a'].lower() in [v.lower() for v in home_variants]
                            break
                    if h2h:
                        break
                
                if not h2h:
                    return None
                
                total_matches = h2h.get('total_matches', 0)
                
                # Confidence basee sur le nombre de matchs
                if total_matches >= 10:
                    confidence = 0.9
                elif total_matches >= 5:
                    confidence = 0.7
                elif total_matches >= 3:
                    confidence = 0.5
                else:
                    confidence = 0.3
                
                btts_rate = float(h2h.get('btts_percentage', 50) or 50) / 100
                over25_rate = float(h2h.get('over_25_percentage', 50) or 50) / 100
                
                dominance_factor = float(h2h.get('dominance_factor', 1.0) or 1.0)
                dominant_team = h2h.get('dominant_team', '')
                
                if dominance_factor >= 1.5:
                    if dominant_team and dominant_team.lower() in [v.lower() for v in home_variants]:
                        dominance = 'home'
                        psychological_edge = min(0.15, (dominance_factor - 1) * 0.1)
                    elif dominant_team and dominant_team.lower() in [v.lower() for v in away_variants]:
                        dominance = 'away'
                        psychological_edge = -min(0.15, (dominance_factor - 1) * 0.1)
                    else:
                        dominance = 'balanced'
                        psychological_edge = 0.0
                else:
                    dominance = 'balanced'
                    psychological_edge = 0.0
                
                always_goals = h2h.get('always_goals', False)
                pattern_btts_boost = 0.10 if always_goals else 0.0
                
                low_scoring = h2h.get('low_scoring', False)
                pattern_under_boost = 0.10 if low_scoring else 0.0
                
                if btts_rate > 0.70:
                    pattern_btts_boost += 0.05
                if over25_rate < 0.40:
                    pattern_under_boost += 0.05
                
                last_5_home_wins = h2h.get('last_5_team_a_wins', 0) if home_is_team_a else h2h.get('last_5_team_b_wins', 0)
                last_5_away_wins = h2h.get('last_5_team_b_wins', 0) if home_is_team_a else h2h.get('last_5_team_a_wins', 0)
                
                recent_momentum = 0.0
                if last_5_home_wins >= 4:
                    recent_momentum = 0.05
                elif last_5_away_wins >= 4:
                    recent_momentum = -0.05
                
                return {
                    'total_matches': total_matches,
                    'btts_rate': btts_rate,
                    'over25_rate': over25_rate,
                    'dominance': dominance,
                    'dominance_factor': dominance_factor,
                    'psychological_edge': psychological_edge + recent_momentum,
                    'pattern_btts_boost': pattern_btts_boost,
                    'pattern_under_boost': pattern_under_boost,
                    'always_goals': always_goals,
                    'low_scoring': low_scoring,
                    'confidence': confidence
                }
                
        except Exception as e:
            return None

'''

with open('orchestrator_v10_quant_engine.py', 'r') as f:
    content = f.read()

if '_get_h2h_intelligence' not in content:
    insert_marker = '    def _calculate_mc_score'
    if insert_marker in content:
        content = content.replace(insert_marker, H2H_CODE + '\n' + insert_marker)
        print("H2H Intelligence Engine ajoute")
    else:
        print("Marker non trouve")
else:
    print("H2H Intelligence deja present")

with open('orchestrator_v10_quant_engine.py', 'w') as f:
    f.write(content)
