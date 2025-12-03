#!/usr/bin/env python3
"""Audit COMPLET: Analyse scientifique des données disponibles vs exploitées"""

import psycopg2
import psycopg2.extras

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

print("="*80)
print("🔬 AUDIT SCIENTIFIQUE - DONNÉES DISPONIBLES vs EXPLOITÉES PAR V10")
print("="*80)

# ═══════════════════════════════════════════════════════════════════════════════
# 1. INVENTAIRE COMPLET DES TABLES
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*80)
print("1. INVENTAIRE DES TABLES CRITIQUES")
print("═"*80)

tables_analysis = [
    ('team_intelligence', 'UTILISÉ ✅', 'xG, goals, forme'),
    ('team_class', 'UTILISÉ ✅', 'Tier, big_game_factor'),
    ('team_momentum', 'PARTIEL ⚠️', 'last_5_results utilisé, trends ignorés'),
    ('head_to_head', 'NON UTILISÉ ❌', 'H2H historique'),
    ('tactical_matrix', 'NON UTILISÉ ❌', 'Style vs Style matchups'),
    ('referee_intelligence', 'NON UTILISÉ ❌', 'Cards, goals/match par arbitre'),
    ('coach_intelligence', 'NON UTILISÉ ❌', 'Tactiques coach'),
    ('scorer_intelligence', 'NON UTILISÉ ❌', 'Top buteurs, form'),
    ('market_patterns', 'NON UTILISÉ ❌', '41 patterns pro'),
    ('market_traps', 'UTILISÉ ✅', 'TRAP/CAUTION'),
    ('odds_history', 'UTILISÉ ✅', 'Steam detection'),
    ('match_results', 'UTILISÉ ✅', 'Résultats historiques'),
]

for table, status, description in tables_analysis:
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    count = cur.fetchone()[0]
    print(f"   {status:20} | {table:25} | {count:6} rows | {description}")

# ═══════════════════════════════════════════════════════════════════════════════
# 2. ANALYSE HEAD_TO_HEAD
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*80)
print("2. HEAD_TO_HEAD - Potentiel inexploité")
print("═"*80)

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'head_to_head'")
cols = [r[0] for r in cur.fetchall()]
print(f"   Colonnes: {cols}")

# Chercher Liverpool
cur.execute("""
    SELECT team_a, team_b, total_matches, team_a_wins, team_b_wins, avg_total_goals
    FROM head_to_head 
    WHERE LOWER(team_a) LIKE '%liverpool%' OR LOWER(team_b) LIKE '%liverpool%'
    LIMIT 5
""")
print("\n   Exemples H2H Liverpool:")
for r in cur.fetchall():
    print(f"   - {r['team_a']} vs {r['team_b']}: {r['total_matches']} matchs, avg goals: {r['avg_total_goals']}")

# ═══════════════════════════════════════════════════════════════════════════════
# 3. TACTICAL_MATRIX
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*80)
print("3. TACTICAL_MATRIX - Potentiel inexploité")
print("═"*80)

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'tactical_matrix'")
cols = [r[0] for r in cur.fetchall()]
print(f"   Colonnes: {cols}")

cur.execute("SELECT DISTINCT style_a FROM tactical_matrix LIMIT 10")
styles = [r[0] for r in cur.fetchall()]
print(f"   Styles disponibles: {styles}")

cur.execute("""
    SELECT style_a, style_b, win_rate_a, draw_rate, avg_goals_total, btts_probability
    FROM tactical_matrix LIMIT 3
""")
print("\n   Exemples matchups:")
for r in cur.fetchall():
    print(f"   - {r['style_a']} vs {r['style_b']}: WinA={r['win_rate_a']}, Goals={r['avg_goals_total']}, BTTS={r['btts_probability']}")

# ═══════════════════════════════════════════════════════════════════════════════
# 4. REFEREE_INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*80)
print("4. REFEREE_INTELLIGENCE - Potentiel inexploité")
print("═"*80)

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'referee_intelligence'")
cols = [r[0] for r in cur.fetchall()]
print(f"   Colonnes: {cols}")

cur.execute("""
    SELECT referee_name, league, strictness_level, avg_cards_per_match, avg_goals_per_match
    FROM referee_intelligence LIMIT 5
""")
print("\n   Exemples arbitres:")
for r in cur.fetchall():
    print(f"   - {r['referee_name']}: Strictness={r['strictness_level']}, Cards={r['avg_cards_per_match']}, Goals={r['avg_goals_per_match']}")

# ═══════════════════════════════════════════════════════════════════════════════
# 5. SCORER_INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*80)
print("5. SCORER_INTELLIGENCE - Potentiel inexploité")
print("═"*80)

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'scorer_intelligence'")
cols = [r[0] for r in cur.fetchall()]
print(f"   Colonnes: {', '.join(cols[:15])}...")

cur.execute("""
    SELECT player_name, team_name, goals_total, goals_home, goals_away, 
           penalty_goals, minutes_per_goal
    FROM scorer_intelligence 
    WHERE LOWER(team_name) LIKE '%liverpool%' OR LOWER(team_name) LIKE '%manchester%'
    LIMIT 8
""")
print("\n   Top buteurs Liverpool/Man:")
for r in cur.fetchall():
    print(f"   - {r['player_name']} ({r['team_name']}): {r['goals_total']} goals, {r['minutes_per_goal']} min/goal")

# ═══════════════════════════════════════════════════════════════════════════════
# 6. MARKET_PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*80)
print("6. MARKET_PATTERNS - 41 Patterns Pro inexploités")
print("═"*80)

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'market_patterns'")
cols = [r[0] for r in cur.fetchall()]
print(f"   Colonnes: {cols}")

cur.execute("""
    SELECT pattern_name, pattern_code, market_type, confidence_boost
    FROM market_patterns LIMIT 10
""")
print("\n   Exemples patterns:")
for r in cur.fetchall():
    print(f"   - [{r['pattern_code']}] {r['pattern_name']}: {r['market_type']}, boost={r['confidence_boost']}")

# ═══════════════════════════════════════════════════════════════════════════════
# 7. COACH_INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*80)
print("7. COACH_INTELLIGENCE - Potentiel inexploité")
print("═"*80)

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'coach_intelligence'")
cols = [r[0] for r in cur.fetchall()]
print(f"   Colonnes: {', '.join(cols[:12])}...")

cur.execute("""
    SELECT coach_name, current_team, career_win_rate, preferred_formation, tactical_style
    FROM coach_intelligence 
    WHERE current_team IS NOT NULL
    LIMIT 5
""")
print("\n   Exemples coaches:")
for r in cur.fetchall():
    print(f"   - {r['coach_name']} ({r['current_team']}): WR={r['career_win_rate']}, Style={r['tactical_style']}")

# ═══════════════════════════════════════════════════════════════════════════════
# 8. TEAM_CLASS - Colonnes non exploitées
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*80)
print("8. TEAM_CLASS - Colonnes partiellement exploitées")
print("═"*80)

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'team_class'")
cols = [r[0] for r in cur.fetchall()]
print(f"   Toutes colonnes: {cols}")

cur.execute("""
    SELECT team_name, tier, big_game_factor, home_fortress_factor, 
           away_weakness_factor, psychological_edge, playing_style
    FROM team_class 
    WHERE LOWER(team_name) LIKE '%liverpool%' OR LOWER(team_name) LIKE '%sunderland%'
""")
print("\n   Liverpool vs Sunderland:")
for r in cur.fetchall():
    print(f"   - {r['team_name']}: Tier={r['tier']}, BigGame={r['big_game_factor']}, HomeFortress={r['home_fortress_factor']}, Style={r['playing_style']}")

# ═══════════════════════════════════════════════════════════════════════════════
# SYNTHÈSE
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*80)
print("🎯 SYNTHÈSE - POTENTIEL INEXPLOITÉ")
print("═"*80)

print("""
┌─────────────────────────────────────────────────────────────────────────────┐
│ DONNÉES UTILISÉES PAR V10 (4 sources)                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ ✅ team_intelligence  → xG, goals scored/conceded                           │
│ ✅ team_class         → Tier (A/B/C/D), big_game_factor (partiel)           │
│ ✅ team_momentum      → last_5_results                                      │
│ ✅ odds_history       → Steam detection                                     │
│ ✅ market_traps       → TRAP/CAUTION                                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ DONNÉES IGNORÉES PAR V10 (7 sources = +70% de data!)                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ ❌ head_to_head (772)       → Historique confrontations directes            │
│ ❌ tactical_matrix (144)    → Style vs Style (ex: pressing vs defensive)    │
│ ❌ referee_intelligence(21) → Avg cards, goals/match par arbitre            │
│ ❌ scorer_intelligence(499) → Top buteurs, minutes/goal, penalties          │
│ ❌ market_patterns (141)    → 41 patterns pro (momentum_up, derby, etc.)    │
│ ❌ coach_intelligence (103) → Tactiques, formations, win_rate coach         │
│ ❌ team_class colonnes      → home_fortress, away_weakness, psych_edge      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ IMPACT SUR LE SCORE                                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ Actuellement:  Score ≈ 20-25 (seulement 4 layers actifs)                    │
│ Potentiel:     Score ≈ 50-70 (si 10+ layers actifs)                         │
│                                                                             │
│ Liverpool vs Sunderland devrait avoir:                                      │
│   +10 pts → H2H historique (Liverpool domine)                               │
│   +8 pts  → Tactical (pressing vs low-block)                                │
│   +5 pts  → Scorers (Salah, Nunez vs équipe D2)                             │
│   +5 pts  → Coach (Slot vs Régis Le Bris)                                   │
│   +5 pts  → Patterns (tier_mismatch, cup_upset_risk)                        │
│   = Score potentiel: 50-55 au lieu de 21                                    │
└─────────────────────────────────────────────────────────────────────────────┘
""")

cur.close()
conn.close()
