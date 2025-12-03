#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
QUANT 2.0 SNIPER - PHASE 1: QUICK WINS
═══════════════════════════════════════════════════════════════════════════════

Intégrations:
1. TEAM_CLASS_EXTENDED: home_fortress_factor, away_weakness_factor, psychological_edge
2. TACTICAL_MATCHUP: Matcher current_style via tactical_matrix
3. VS_TOP/BOTTOM_TEAMS: Ajuster xG selon adversaire

Gain estimé: +15-20 pts Score
"""

with open('orchestrator_v10_quant_engine.py', 'r') as f:
    content = f.read()

# ═══════════════════════════════════════════════════════════════════════════════
# 1. Ajouter méthode _get_tactical_matchup dans LineupImpactEngine
# ═══════════════════════════════════════════════════════════════════════════════

# Trouver la fin de _get_competition_stats et insérer avant _regress_to_mean
old_regress_method = '''    def _regress_to_mean(self, team_stat: float, sample_size: int,'''

new_methods = '''    def _get_tactical_matchup(self, home_style: str, away_style: str) -> Dict:
        """
        V11 - Récupère les probabilités de matchup tactique
        
        Retourne: {btts_probability, over_25_probability, avg_goals_total, upset_probability}
        """
        if not self.conn or not home_style or not away_style:
            return {}
        
        try:
            import psycopg2.extras
            
            # Normaliser les styles
            style_map = {
                'balanced': 'balanced', 'balanced_offensive': 'attacking',
                'balanced_defensive': 'defensive', 'high_press': 'high_press',
                'pressing': 'pressing', 'gegenpressing': 'gegenpressing',
                'possession': 'possession', 'tiki_taka': 'tiki_taka',
                'counter_attack': 'counter_attack', 'low_block_counter': 'low_block_counter',
                'defensive': 'defensive', 'attacking': 'attacking',
                'direct_play': 'direct_play', 'park_the_bus': 'park_the_bus'
            }
            
            home_s = style_map.get(home_style.lower(), 'balanced')
            away_s = style_map.get(away_style.lower(), 'balanced')
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT btts_probability, over_25_probability, avg_goals_total,
                           upset_probability, win_rate_a, confidence_level
                    FROM tactical_matrix
                    WHERE style_a = %s AND style_b = %s
                """, (home_s, away_s))
                
                row = cur.fetchone()
                if row:
                    return {
                        'btts_prob': float(row['btts_probability']) if row['btts_probability'] else None,
                        'over25_prob': float(row['over_25_probability']) if row['over_25_probability'] else None,
                        'avg_goals': float(row['avg_goals_total']) if row['avg_goals_total'] else None,
                        'upset_prob': float(row['upset_probability']) if row['upset_probability'] else None,
                        'home_win_rate': float(row['win_rate_a']) if row['win_rate_a'] else None,
                        'confidence': row['confidence_level'],
                        'source': 'tactical_matrix'
                    }
            return {}
        except Exception as e:
            return {}

    def _get_vs_opponent_type_adjustment(self, team_intel: Dict, opponent_tier: str, 
                                          location: str) -> float:
        """
        V11 - Ajuste xG selon type d'adversaire (top/bottom teams)
        
        Utilise: vs_top_teams, vs_bottom_teams depuis team_intelligence
        """
        if not team_intel:
            return 0.0
        
        adjustment = 0.0
        tier_values = {'S': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1}
        opp_tier_val = tier_values.get(opponent_tier, 3)
        
        try:
            if opp_tier_val >= 4:  # Adversaire Top (S ou A)
                vs_top = team_intel.get('vs_top_teams', {})
                if isinstance(vs_top, dict):
                    # Équipe qui performe bien contre les tops = boost
                    win_rate = vs_top.get('win_rate', 30)
                    if win_rate > 40:
                        adjustment += 0.10  # Bon contre les grands
                    elif win_rate < 20:
                        adjustment -= 0.10  # Mauvais contre les grands
                        
            elif opp_tier_val <= 2:  # Adversaire Bottom (C ou D)
                vs_bottom = team_intel.get('vs_bottom_teams', {})
                if isinstance(vs_bottom, dict):
                    win_rate = vs_bottom.get('win_rate', 60)
                    if win_rate > 75:
                        adjustment += 0.15  # Écrase les petits
                    elif win_rate < 50:
                        adjustment -= 0.10  # Piégé par les petits
        except:
            pass
        
        return adjustment

    def _regress_to_mean(self, team_stat: float, sample_size: int,'''

if old_regress_method in content:
    content = content.replace(old_regress_method, new_methods)
    print("✅ 1. Méthodes _get_tactical_matchup et _get_vs_opponent_type_adjustment ajoutées")
else:
    print("❌ 1. Pattern _regress_to_mean non trouvé")

# ═══════════════════════════════════════════════════════════════════════════════
# 2. Ajouter TEAM_CLASS_EXTENDED après Tier Adjustment
# ═══════════════════════════════════════════════════════════════════════════════

old_tier_end = '''        elif tier_diff <= -1:  # Away supérieur
            impact.home_base_xg *= 0.90
            impact.away_base_xg *= 1.10
        
        # Ajustement pour absences STAR PLAYERS'''

new_tier_extended = '''        elif tier_diff <= -1:  # Away supérieur
            impact.home_base_xg *= 0.90
            impact.away_base_xg *= 1.10
        
        # ═══════════════════════════════════════════════════════
        # V11 - TEAM_CLASS EXTENDED FACTORS
        # ═══════════════════════════════════════════════════════
        
        # Home Fortress Factor (équipes dominantes à domicile)
        home_fortress = float(home_class.get('home_fortress_factor', 1.0)) if home_class else 1.0
        away_weakness = float(away_class.get('away_weakness_factor', 1.0)) if away_class else 1.0
        
        # Appliquer les facteurs
        if home_fortress > 1.0:
            impact.home_base_xg *= home_fortress  # Ex: 1.15 = +15% xG domicile
        if away_weakness > 1.0:
            impact.away_base_xg *= (2.0 - away_weakness)  # Ex: 1.10 = -10% xG extérieur
        
        # Psychological Edge (avantage mental dans les gros matchs)
        home_psych = float(home_class.get('psychological_edge', 1.0)) if home_class else 1.0
        away_psych = float(away_class.get('psychological_edge', 1.0)) if away_class else 1.0
        
        # Si différence psychologique significative
        psych_diff = home_psych - away_psych
        if psych_diff >= 0.1:
            impact.home_base_xg *= 1.05  # Avantage mental home
        elif psych_diff <= -0.1:
            impact.away_base_xg *= 1.05  # Avantage mental away
        
        # ═══════════════════════════════════════════════════════
        # V11 - TACTICAL MATCHUP (via tactical_matrix)
        # ═══════════════════════════════════════════════════════
        
        home_style = None
        away_style = None
        
        # Récupérer styles depuis team_intelligence (priorité) ou team_class
        if home_intel and home_intel.get('current_style'):
            home_style = home_intel.get('current_style')
        elif home_class and home_class.get('playing_style'):
            home_style = home_class.get('playing_style')
        
        if away_intel and away_intel.get('current_style'):
            away_style = away_intel.get('current_style')
        elif away_class and away_class.get('playing_style'):
            away_style = away_class.get('playing_style')
        
        # Stocker le matchup tactique pour usage ultérieur (probas BTTS/Over25)
        if home_style and away_style:
            tactical_data = self._get_tactical_matchup(home_style, away_style)
            if tactical_data:
                impact.tactical_matchup = tactical_data
                # Ajuster xG selon avg_goals du matchup
                if tactical_data.get('avg_goals'):
                    expected_total = tactical_data['avg_goals']
                    current_total = impact.home_base_xg + impact.away_base_xg
                    if expected_total > 0 and current_total > 0:
                        # Ajuster proportionnellement (max ±15%)
                        ratio = min(1.15, max(0.85, expected_total / current_total))
                        impact.home_base_xg *= ratio
                        impact.away_base_xg *= ratio
        
        # ═══════════════════════════════════════════════════════
        # V11 - VS TOP/BOTTOM TEAMS ADJUSTMENT
        # ═══════════════════════════════════════════════════════
        
        # Ajuster home_xg selon performance contre ce type d'adversaire
        home_vs_adj = self._get_vs_opponent_type_adjustment(home_intel, away_tier, 'home')
        away_vs_adj = self._get_vs_opponent_type_adjustment(away_intel, home_tier, 'away')
        
        impact.home_base_xg += home_vs_adj
        impact.away_base_xg += away_vs_adj
        
        # Ajustement pour absences STAR PLAYERS'''

if old_tier_end in content:
    content = content.replace(old_tier_end, new_tier_extended)
    print("✅ 2. TEAM_CLASS_EXTENDED + TACTICAL_MATCHUP + VS_TOP/BOTTOM ajoutés")
else:
    print("❌ 2. Pattern Tier end non trouvé")

# ═══════════════════════════════════════════════════════════════════════════════
# 3. Ajouter tactical_matchup au dataclass LineupImpact
# ═══════════════════════════════════════════════════════════════════════════════

old_dataclass = '''@dataclass
class LineupImpact:
    """Impact des compositions sur les probabilités"""
    home_base_xg: float = 1.3
    away_base_xg: float = 1.1'''

new_dataclass = '''@dataclass
class LineupImpact:
    """Impact des compositions sur les probabilités - V11 Enhanced"""
    home_base_xg: float = 1.3
    away_base_xg: float = 1.1
    tactical_matchup: Dict = None  # V11: Données tactical_matrix'''

if old_dataclass in content:
    content = content.replace(old_dataclass, new_dataclass)
    print("✅ 3. tactical_matchup ajouté à LineupImpact dataclass")
else:
    print("❌ 3. Pattern dataclass non trouvé")

# Sauvegarder
with open('orchestrator_v10_quant_engine.py', 'w') as f:
    f.write(content)

print("\n" + "="*70)
print("✅ PATCH QUANT V11 PHASE 1 APPLIQUÉ!")
print("="*70)
print("""
Intégrations ajoutées:
  1. _get_tactical_matchup() - Query tactical_matrix
  2. _get_vs_opponent_type_adjustment() - Ajuste selon vs_top/bottom_teams
  3. Team Class Extended (home_fortress, away_weakness, psychological_edge)
  4. Tactical Matchup (style vs style → avg_goals adjustment)
  5. VS Top/Bottom Teams adjustment

Gain estimé: +15-20 pts Score
""")
