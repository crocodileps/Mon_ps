#!/usr/bin/env python3
"""Audit FINAL - Toutes les colonnes exactes"""

import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

print("="*80)
print("🎯 AUDIT FINAL - DONNÉES POUR QUANT 2.0 SNIPER")
print("="*80)

# 1. REFEREE
print("\n1. REFEREE_INTELLIGENCE:")
cur.execute("""
    SELECT referee_name, league, strictness_level, avg_yellow_cards_per_game, 
           avg_goals_per_game, home_bias_factor, matches_officiated
    FROM referee_intelligence LIMIT 5
""")
for r in cur.fetchall():
    print(f"   {r['referee_name']}: Goals/match={r['avg_goals_per_game']}, Cards={r['avg_yellow_cards_per_game']}, HomeBias={r['home_bias_factor']}")

# 2. SCORER
print("\n2. SCORER_INTELLIGENCE:")
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'scorer_intelligence' LIMIT 20")
cols = [r[0] for r in cur.fetchall()]
print(f"   Colonnes: {cols}")

cur.execute("""
    SELECT player_name, team_name, goals_total, goals_home, goals_away
    FROM scorer_intelligence 
    WHERE LOWER(team_name) LIKE '%liverpool%'
    LIMIT 5
""")
for r in cur.fetchall():
    print(f"   {r['player_name']} ({r['team_name']}): {r['goals_total']} goals (H:{r['goals_home']}/A:{r['goals_away']})")

# 3. COACH
print("\n3. COACH_INTELLIGENCE:")
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'coach_intelligence'")
cols = [r[0] for r in cur.fetchall()]
print(f"   Colonnes: {cols}")

cur.execute("""
    SELECT coach_name, current_team, career_win_rate, preferred_formation, tactical_style
    FROM coach_intelligence 
    WHERE current_team IS NOT NULL LIMIT 5
""")
for r in cur.fetchall():
    print(f"   {r['coach_name']} ({r['current_team']}): WR={r['career_win_rate']}, Style={r['tactical_style']}")

# 4. MARKET_PATTERNS
print("\n4. MARKET_PATTERNS:")
cur.execute("""
    SELECT pattern_name, pattern_code, market_type, confidence_boost, min_tier_diff
    FROM market_patterns LIMIT 10
""")
for r in cur.fetchall():
    print(f"   [{r['pattern_code']}] {r['pattern_name']}: {r['market_type']}, boost={r['confidence_boost']}")

# 5. TEAM_CLASS colonnes complètes
print("\n5. TEAM_CLASS - Colonnes non exploitées:")
cur.execute("""
    SELECT team_name, tier, big_game_factor, home_fortress_factor, 
           away_weakness_factor, psychological_edge, playing_style, calculated_power_index
    FROM team_class 
    WHERE LOWER(team_name) LIKE '%liverpool%' OR LOWER(team_name) LIKE '%arsenal%'
""")
for r in cur.fetchall():
    print(f"   {r['team_name']}: Style={r['playing_style']}, HomeFort={r['home_fortress_factor']}, PsychEdge={r['psychological_edge']}, Power={r['calculated_power_index']}")

# 6. HEAD_TO_HEAD colonnes
print("\n6. HEAD_TO_HEAD - Colonnes exploitables:")
cur.execute("""
    SELECT team_a, team_b, total_matches, dominant_team, dominance_factor,
           over_25_percentage, btts_percentage, always_goals
    FROM head_to_head 
    WHERE total_matches >= 3
    LIMIT 5
""")
for r in cur.fetchall():
    print(f"   {r['team_a']} vs {r['team_b']}: {r['total_matches']} matchs, Over25={r['over_25_percentage']}%, BTTS={r['btts_percentage']}%")

print("\n" + "="*80)
print("📋 PLAN D'INTÉGRATION QUANT 2.0 SNIPER")
print("="*80)
print("""
┌─────────────────────────────────────────────────────────────────────────────┐
│ NOUVEAUX LAYERS À INTÉGRER                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ LAYER 1: H2H_LAYER (+10 pts max)                                            │
│   → Requête: head_to_head WHERE team_a/team_b LIKE %team%                   │
│   → Utilise: dominance_factor, over_25_percentage, btts_percentage          │
│   → Impact: Ajuste xG et probas BTTS/Over25                                 │
│                                                                             │
│ LAYER 2: TACTICAL_LAYER (+8 pts max)                                        │
│   → Requête: tactical_matrix WHERE style_a = home_style AND style_b = away  │
│   → Utilise: win_rate_a, btts_probability, over_25_probability              │
│   → Impact: Ajuste probas selon matchup tactique                            │
│                                                                             │
│ LAYER 3: REFEREE_LAYER (+5 pts max)                                         │
│   → Requête: referee_intelligence WHERE referee_name = match_referee        │
│   → Utilise: avg_goals_per_game, avg_yellow_cards_per_game, home_bias       │
│   → Impact: Ajuste Over/Under et Home/Away                                  │
│                                                                             │
│ LAYER 4: SCORER_LAYER (+5 pts max)                                          │
│   → Requête: scorer_intelligence WHERE team_name = home/away                │
│   → Utilise: goals_total, goals_home, goals_away, minutes_per_goal          │
│   → Impact: Boost xG si top buteurs présents                                │
│                                                                             │
│ LAYER 5: COACH_LAYER (+5 pts max)                                           │
│   → Requête: coach_intelligence WHERE current_team = team                   │
│   → Utilise: career_win_rate, tactical_style                                │
│   → Impact: Cross-check avec tactical_matrix                                │
│                                                                             │
│ LAYER 6: PATTERNS_LAYER (+7 pts max)                                        │
│   → Requête: market_patterns + match context                                │
│   → Utilise: pattern_code, confidence_boost, min_tier_diff                  │
│   → Impact: Détecte patterns spéciaux (derby, relegation, cup_upset)        │
│                                                                             │
│ LAYER 7: TEAM_CLASS_EXTENDED (+5 pts max)                                   │
│   → Colonnes: home_fortress, away_weakness, psychological_edge, power_index │
│   → Impact: Affine le Tier Adjustment                                       │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ SCORE POTENTIEL: 21 actuel + 45 nouveaux = 66 pts (STRONG BET!)             │
└─────────────────────────────────────────────────────────────────────────────┘
""")

cur.close()
conn.close()
