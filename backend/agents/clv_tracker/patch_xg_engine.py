#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
PHASE 2.3 - xG INTELLIGENCE ENGINE (Understat Data)
═══════════════════════════════════════════════════════════════════════════════

Utilise les données xG historiques pour:
1. Ajuster les prédictions selon les tendances de sur/sous-performance
2. Identifier les profils de matchs (défensif/ouvert)
3. Améliorer les prédictions BTTS et Over/Under
"""

XG_ENGINE_CODE = '''
    def _get_xg_intelligence(self, team_name: str) -> Optional[Dict]:
        """
        Récupère les tendances xG d'une équipe depuis Understat.
        
        Returns:
            Dict avec:
            - avg_xg_for: xG moyen marqué
            - avg_xg_against: xG moyen concédé  
            - avg_performance: goals - xG moyen (positif = surperformance)
            - overperform_rate: % matchs où l'équipe surperforme
            - defensive_rate: % matchs défensifs (<1.5 xG total)
            - open_rate: % matchs ouverts (>4 xG total)
            - btts_xg_rate: % matchs où BTTS était attendu selon xG
            - over25_xg_rate: % matchs où Over 2.5 était attendu
            - recent_xg_for/against: forme récente (5 derniers)
            - regression_factor: ajustement pour regression à la moyenne
        """
        if not self.conn:
            return None
            
        try:
            variants = self._resolve_team_name(team_name)
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                for v in variants[:5]:
                    cur.execute("""
                        SELECT * FROM team_xg_tendencies 
                        WHERE LOWER(team_name) LIKE %s
                        ORDER BY updated_at DESC
                        LIMIT 1
                    """, (f'%{v.lower()}%',))
                    
                    row = cur.fetchone()
                    if row:
                        data = dict(row)
                        
                        # Calculer le facteur de régression
                        # Si surperformance > +0.3, on s'attend à une régression
                        avg_perf = float(data.get('avg_performance', 0) or 0)
                        if avg_perf > 0.3:
                            regression_factor = -0.15  # Réduire xG attendu
                        elif avg_perf < -0.3:
                            regression_factor = 0.15   # Augmenter xG attendu
                        else:
                            regression_factor = 0.0
                        
                        # Calculer trend récent vs moyenne
                        recent_for = float(data.get('recent_xg_for', 0) or 0)
                        avg_for = float(data.get('avg_xg_for', 0) or 0)
                        form_trend = recent_for - avg_for  # Positif = en hausse
                        
                        return {
                            'avg_xg_for': float(data.get('avg_xg_for', 1.0) or 1.0),
                            'avg_xg_against': float(data.get('avg_xg_against', 1.0) or 1.0),
                            'avg_performance': avg_perf,
                            'overperform_rate': float(data.get('overperform_rate', 50) or 50),
                            'underperform_rate': float(data.get('underperform_rate', 50) or 50),
                            'defensive_rate': float(data.get('defensive_rate', 20) or 20),
                            'open_rate': float(data.get('open_rate', 20) or 20),
                            'btts_xg_rate': float(data.get('btts_xg_rate', 50) or 50),
                            'over25_xg_rate': float(data.get('over25_xg_rate', 50) or 50),
                            'recent_xg_for': recent_for,
                            'recent_xg_against': float(data.get('recent_xg_against', 1.0) or 1.0),
                            'recent_performance': float(data.get('recent_performance', 0) or 0),
                            'regression_factor': regression_factor,
                            'form_trend': form_trend,
                            'matches_analyzed': data.get('matches_analyzed', 0)
                        }
                        
            return None
                
        except Exception as e:
            return None

    def _get_h2h_xg_history(self, home_team: str, away_team: str) -> Optional[Dict]:
        """
        Récupère l'historique xG des confrontations directes.
        """
        if not self.conn:
            return None
            
        try:
            home_variants = self._resolve_team_name(home_team)
            away_variants = self._resolve_team_name(away_team)
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                matches = []
                
                for hv in home_variants[:3]:
                    for av in away_variants[:3]:
                        cur.execute("""
                            SELECT home_xg, away_xg, total_xg, match_profile,
                                   home_goals, away_goals, btts_expected, over25_expected
                            FROM match_xg_stats
                            WHERE (LOWER(home_team) LIKE %s AND LOWER(away_team) LIKE %s)
                               OR (LOWER(home_team) LIKE %s AND LOWER(away_team) LIKE %s)
                            ORDER BY match_date DESC
                            LIMIT 5
                        """, (f'%{hv.lower()}%', f'%{av.lower()}%',
                              f'%{av.lower()}%', f'%{hv.lower()}%'))
                        
                        rows = cur.fetchall()
                        if rows:
                            matches = [dict(r) for r in rows]
                            break
                    if matches:
                        break
                
                if not matches:
                    return None
                
                # Calculer les moyennes H2H
                avg_total_xg = sum(m['total_xg'] for m in matches) / len(matches)
                btts_rate = sum(1 for m in matches if m['btts_expected']) / len(matches)
                over25_rate = sum(1 for m in matches if m['over25_expected']) / len(matches)
                
                profiles = [m['match_profile'] for m in matches]
                dominant_profile = max(set(profiles), key=profiles.count)
                
                return {
                    'matches_count': len(matches),
                    'avg_total_xg': round(avg_total_xg, 2),
                    'btts_xg_rate': round(btts_rate * 100, 1),
                    'over25_xg_rate': round(over25_rate * 100, 1),
                    'dominant_profile': dominant_profile
                }
                
        except Exception as e:
            return None

'''

with open('orchestrator_v10_quant_engine.py', 'r') as f:
    content = f.read()

if '_get_xg_intelligence' not in content:
    insert_marker = '    def _get_scorer_intelligence'
    if insert_marker in content:
        content = content.replace(insert_marker, XG_ENGINE_CODE + '\n' + insert_marker)
        print("xG Intelligence Engine ajouté!")
    else:
        print("Marker non trouvé")
else:
    print("xG Intelligence déjà présent")

with open('orchestrator_v10_quant_engine.py', 'w') as f:
    f.write(content)
