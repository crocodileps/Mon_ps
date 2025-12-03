#!/usr/bin/env python3
"""
══════════════════════════════════════════════════════════════════════════════
ANALYSE SCIENTIFIQUE - POTENTIEL DATA QUANT 2.0 SNIPER
══════════════════════════════════════════════════════════════════════════════

Objectif: Identifier les corrélations exploitables et les sources de données
          à haute valeur ajoutée pour améliorer le Score de 21 à 60+

Méthodologie:
1. Inventaire exhaustif des données disponibles
2. Analyse des corrélations statistiques
3. Identification des gaps d'exploitation
4. Recommandations priorisées par impact/effort
"""

import psycopg2
import psycopg2.extras
from collections import defaultdict

conn = psycopg2.connect(host='localhost', port=5432, dbname='monps_db', 
                        user='monps_user', password='monps_secure_password_2024')
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

print("="*90)
print("🔬 ANALYSE SCIENTIFIQUE - QUANT 2.0 SNIPER DATA ASSESSMENT")
print("="*90)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: INVENTAIRE DES DONNÉES DISPONIBLES
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*90)
print("SECTION 1: INVENTAIRE QUANTITATIF DES DONNÉES")
print("═"*90)

data_inventory = {}

tables_critical = [
    'team_intelligence', 'team_class', 'team_momentum', 'head_to_head',
    'tactical_matrix', 'referee_intelligence', 'coach_intelligence',
    'scorer_intelligence', 'market_patterns', 'market_traps',
    'match_results', 'odds_history'
]

for table in tables_critical:
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    rows = cur.fetchone()[0]
    
    cur.execute("""
        SELECT COUNT(*) FROM information_schema.columns WHERE table_name = %s
    """, (table,))
    cols = cur.fetchone()[0]
    
    data_inventory[table] = {'rows': rows, 'cols': cols, 'data_points': rows * cols}
    
print(f"\n{'Table':<25} {'Rows':>10} {'Cols':>8} {'Data Points':>15}")
print("-"*60)
total_points = 0
for table, info in sorted(data_inventory.items(), key=lambda x: -x[1]['data_points']):
    print(f"{table:<25} {info['rows']:>10,} {info['cols']:>8} {info['data_points']:>15,}")
    total_points += info['data_points']
print("-"*60)
print(f"{'TOTAL':<25} {'':<10} {'':<8} {total_points:>15,}")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: ANALYSE DES COLONNES EXPLOITABLES PAR TABLE
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*90)
print("SECTION 2: COLONNES EXPLOITABLES PAR TABLE")
print("═"*90)

# 2.1 TEAM_INTELLIGENCE - Colonnes critiques
print("\n📊 2.1 TEAM_INTELLIGENCE (83 colonnes)")
print("-"*70)

ti_columns_used = ['home_goals_scored_avg', 'away_goals_scored_avg', 'home_goals_conceded_avg', 'away_goals_conceded_avg']
ti_columns_unused_high_value = [
    'current_style', 'current_pressing', 'current_form', 'current_form_points',
    'home_btts_rate', 'home_over25_rate', 'away_btts_rate', 'away_over25_rate',
    'xg_for_avg', 'xg_against_avg', 'xg_difference',
    'first_half_goals_pct', 'second_half_goals_pct', 'late_goals_pct',
    'comeback_rate', 'vs_top_teams', 'vs_bottom_teams', 'after_europe'
]

print(f"   UTILISÉES ({len(ti_columns_used)}): {', '.join(ti_columns_used)}")
print(f"   NON UTILISÉES HAUTE VALEUR ({len(ti_columns_unused_high_value)}):")
for col in ti_columns_unused_high_value:
    cur.execute(f"SELECT COUNT(*) FROM team_intelligence WHERE {col} IS NOT NULL")
    not_null = cur.fetchone()[0]
    pct = (not_null / 675) * 100 if not_null else 0
    status = "✅" if pct > 50 else "⚠️" if pct > 20 else "❌"
    print(f"      {status} {col}: {pct:.0f}% rempli ({not_null}/675)")

# 2.2 TEAM_CLASS - Colonnes critiques
print("\n📊 2.2 TEAM_CLASS (20 colonnes)")
print("-"*70)

tc_columns_used = ['tier', 'big_game_factor']
tc_columns_unused = ['home_fortress_factor', 'away_weakness_factor', 'psychological_edge', 
                     'playing_style', 'calculated_power_index', 'star_players']

print(f"   UTILISÉES ({len(tc_columns_used)}): {', '.join(tc_columns_used)}")
print(f"   NON UTILISÉES:")
for col in tc_columns_unused:
    cur.execute(f"SELECT COUNT(*) FROM team_class WHERE {col} IS NOT NULL")
    not_null = cur.fetchone()[0]
    pct = (not_null / 231) * 100 if not_null else 0
    status = "✅" if pct > 50 else "⚠️" if pct > 20 else "❌"
    print(f"      {status} {col}: {pct:.0f}% rempli ({not_null}/231)")

# 2.3 HEAD_TO_HEAD - Analyse qualité
print("\n📊 2.3 HEAD_TO_HEAD (20 colonnes) - NON UTILISÉ")
print("-"*70)

h2h_critical = ['dominant_team', 'dominance_factor', 'over_25_percentage', 
                'btts_percentage', 'always_goals', 'low_scoring', 'total_matches']

for col in h2h_critical:
    cur.execute(f"SELECT COUNT(*) FROM head_to_head WHERE {col} IS NOT NULL")
    not_null = cur.fetchone()[0]
    pct = (not_null / 772) * 100 if not_null else 0
    status = "✅" if pct > 50 else "⚠️" if pct > 20 else "❌"
    print(f"   {status} {col}: {pct:.0f}% rempli ({not_null}/772)")

# Distribution des matchs H2H
cur.execute("SELECT total_matches, COUNT(*) FROM head_to_head GROUP BY total_matches ORDER BY total_matches")
print("\n   Distribution matchs H2H:")
for r in cur.fetchall():
    print(f"      {r[0]} matchs: {r[1]} paires d'équipes")

# 2.4 TACTICAL_MATRIX - Analyse qualité
print("\n📊 2.4 TACTICAL_MATRIX (26 colonnes) - NON UTILISÉ")
print("-"*70)

cur.execute("SELECT DISTINCT style_a FROM tactical_matrix ORDER BY style_a")
styles = [r[0] for r in cur.fetchall()]
print(f"   Styles disponibles ({len(styles)}): {', '.join(styles)}")

tm_critical = ['win_rate_a', 'btts_probability', 'over_25_probability', 
               'avg_goals_total', 'upset_probability', 'confidence_level']

for col in tm_critical:
    cur.execute(f"SELECT COUNT(*) FROM tactical_matrix WHERE {col} IS NOT NULL")
    not_null = cur.fetchone()[0]
    pct = (not_null / 144) * 100 if not_null else 0
    status = "✅" if pct > 50 else "⚠️" if pct > 20 else "❌"
    print(f"   {status} {col}: {pct:.0f}% rempli ({not_null}/144)")

# 2.5 SCORER_INTELLIGENCE - Analyse qualité
print("\n📊 2.5 SCORER_INTELLIGENCE (153 colonnes) - NON UTILISÉ")
print("-"*70)

scorer_critical = ['anytime_scorer_prob', 'goals_per_90', 'home_goals', 'away_goals',
                   'is_hot_streak', 'form_score', 'is_injured', 'is_penalty_taker',
                   'current_team', 'season_goals']

for col in scorer_critical:
    cur.execute(f"SELECT COUNT(*) FROM scorer_intelligence WHERE {col} IS NOT NULL")
    not_null = cur.fetchone()[0]
    pct = (not_null / 499) * 100 if not_null else 0
    status = "✅" if pct > 50 else "⚠️" if pct > 20 else "❌"
    print(f"   {status} {col}: {pct:.0f}% rempli ({not_null}/499)")

# Vérifier les top scorers avec données complètes
cur.execute("""
    SELECT player_name, current_team, season_goals, goals_per_90, anytime_scorer_prob
    FROM scorer_intelligence 
    WHERE season_goals IS NOT NULL AND season_goals > 5
    ORDER BY season_goals DESC LIMIT 10
""")
print("\n   Top 10 buteurs avec données:")
for r in cur.fetchall():
    print(f"      {r['player_name']} ({r['current_team']}): {r['season_goals']} goals, {r['goals_per_90']} per90")

# 2.6 COACH_INTELLIGENCE - Analyse qualité  
print("\n📊 2.6 COACH_INTELLIGENCE (151 colonnes) - NON UTILISÉ")
print("-"*70)

coach_critical = ['current_team', 'career_win_rate', 'tactical_style', 
                  'over25_rate', 'btts_rate', 'clean_sheet_rate', 'formation_primary']

for col in coach_critical:
    cur.execute(f"SELECT COUNT(*) FROM coach_intelligence WHERE {col} IS NOT NULL")
    not_null = cur.fetchone()[0]
    pct = (not_null / 103) * 100 if not_null else 0
    status = "✅" if pct > 50 else "⚠️" if pct > 20 else "❌"
    print(f"   {status} {col}: {pct:.0f}% rempli ({not_null}/103)")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3: ANALYSE DES CORRÉLATIONS EXPLOITABLES
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*90)
print("SECTION 3: CORRÉLATIONS STATISTIQUES EXPLOITABLES")
print("═"*90)

# 3.1 Corrélation Style vs BTTS/Over25 dans tactical_matrix
print("\n📈 3.1 TACTICAL_MATRIX - Impact Style sur BTTS/Over25")
print("-"*70)

cur.execute("""
    SELECT style_a, style_b, 
           AVG(btts_probability) as avg_btts,
           AVG(over_25_probability) as avg_over25,
           AVG(avg_goals_total) as avg_goals,
           COUNT(*) as matchups
    FROM tactical_matrix
    WHERE btts_probability IS NOT NULL
    GROUP BY style_a, style_b
    ORDER BY avg_btts DESC
    LIMIT 10
""")
print("\n   Top 10 matchups BTTS les plus élevés:")
for r in cur.fetchall():
    print(f"   {r['style_a']:15} vs {r['style_b']:15}: BTTS={r['avg_btts']:.1f}%, Over25={r['avg_over25']:.1f}%, Goals={r['avg_goals']:.2f}")

# 3.2 Corrélation Tier vs Performance
print("\n📈 3.2 TEAM_CLASS - Impact Tier sur Performance")
print("-"*70)

cur.execute("""
    SELECT tc.tier, COUNT(*) as teams,
           AVG(ti.home_win_rate) as avg_home_wr,
           AVG(ti.home_goals_scored_avg) as avg_home_goals,
           AVG(ti.home_btts_rate) as avg_btts
    FROM team_class tc
    JOIN team_intelligence ti ON LOWER(tc.team_name) = LOWER(ti.team_name)
    WHERE tc.tier IS NOT NULL
    GROUP BY tc.tier
    ORDER BY tc.tier
""")
print(f"\n   {'Tier':<8} {'Teams':>6} {'HomeWR':>10} {'HomeGoals':>12} {'BTTS':>10}")
for r in cur.fetchall():
    print(f"   {r['tier']:<8} {r['teams']:>6} {r['avg_home_wr'] or 0:.1f}% {r['avg_home_goals'] or 0:.2f} {r['avg_btts'] or 0:.1f}%")

# 3.3 Referee Impact
print("\n📈 3.3 REFEREE_INTELLIGENCE - Impact Arbitre")
print("-"*70)

cur.execute("""
    SELECT referee_name, avg_goals_per_game, avg_yellow_cards_per_game,
           home_bias_factor, matches_officiated
    FROM referee_intelligence
    ORDER BY avg_goals_per_game DESC
""")
print(f"\n   {'Referee':<20} {'Goals/Match':>12} {'Cards/Match':>12} {'HomeBias':>10} {'Matchs':>8}")
for r in cur.fetchall():
    print(f"   {r['referee_name']:<20} {r['avg_goals_per_game']:.2f} {r['avg_yellow_cards_per_game']:.2f} {r['home_bias_factor']:.2f} {r['matches_officiated']}")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4: GAPS D'EXPLOITATION IDENTIFIÉS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*90)
print("SECTION 4: GAPS D'EXPLOITATION - CE QUE V10 IGNORE")
print("═"*90)

gaps = [
    {
        'source': 'team_intelligence',
        'colonnes': ['current_style', 'home_btts_rate', 'home_over25_rate', 'xg_for_avg', 'vs_top_teams'],
        'impact': 'ÉLEVÉ',
        'effort': 'FAIBLE',
        'gain_score': '+8-12 pts',
        'raison': 'Données déjà présentes, juste à requêter'
    },
    {
        'source': 'team_class',
        'colonnes': ['home_fortress_factor', 'psychological_edge', 'playing_style'],
        'impact': 'MOYEN',
        'effort': 'FAIBLE', 
        'gain_score': '+5-8 pts',
        'raison': 'Enrichit le Tier Adjustment'
    },
    {
        'source': 'tactical_matrix',
        'colonnes': ['btts_probability', 'over_25_probability', 'upset_probability'],
        'impact': 'ÉLEVÉ',
        'effort': 'MOYEN',
        'gain_score': '+10-15 pts',
        'raison': 'Cross-match style_a (home) vs style_b (away)'
    },
    {
        'source': 'head_to_head',
        'colonnes': ['dominance_factor', 'over_25_percentage', 'btts_percentage'],
        'impact': 'MOYEN',
        'effort': 'MOYEN',
        'gain_score': '+5-10 pts',
        'raison': 'Historique confrontations directes'
    },
    {
        'source': 'scorer_intelligence',
        'colonnes': ['anytime_scorer_prob', 'is_hot_streak', 'is_injured'],
        'impact': 'MOYEN',
        'effort': 'ÉLEVÉ',
        'gain_score': '+5-8 pts',
        'raison': 'Nécessite matching équipe + présence joueur'
    },
    {
        'source': 'coach_intelligence',
        'colonnes': ['over25_rate', 'btts_rate', 'tactical_style'],
        'impact': 'MOYEN',
        'effort': 'MOYEN',
        'gain_score': '+3-5 pts',
        'raison': 'Enrichit analyse tactique'
    },
    {
        'source': 'referee_intelligence',
        'colonnes': ['avg_goals_per_game', 'home_bias_factor'],
        'impact': 'FAIBLE',
        'effort': 'FAIBLE',
        'gain_score': '+2-4 pts',
        'raison': 'Nécessite arbitre du match (pas toujours dispo)'
    }
]

print(f"\n{'Source':<22} {'Impact':>8} {'Effort':>8} {'Gain':>12} {'Colonnes clés'}")
print("-"*90)
for gap in gaps:
    print(f"{gap['source']:<22} {gap['impact']:>8} {gap['effort']:>8} {gap['gain_score']:>12} {', '.join(gap['colonnes'][:3])}")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5: RECOMMANDATIONS PRIORISÉES
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*90)
print("SECTION 5: RECOMMANDATIONS PRIORISÉES (Impact/Effort)")
print("═"*90)

print("""
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ PRIORITÉ 1: QUICK WINS (Impact ÉLEVÉ, Effort FAIBLE)                                 │
├──────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│ 1.1 EXPLOITER team_intelligence COMPLET                                              │
│     Colonnes: current_style, home_btts_rate, home_over25_rate, xg_for_avg            │
│     → Gain: +8-12 pts Score                                                          │
│     → Implémentation: Ajouter requêtes dans calculate_impact()                       │
│                                                                                      │
│ 1.2 ENRICHIR team_class                                                              │
│     Colonnes: home_fortress_factor, away_weakness_factor, psychological_edge         │
│     → Gain: +5-8 pts Score                                                           │
│     → Implémentation: Multiplier xG par ces facteurs                                 │
│                                                                                      │
├──────────────────────────────────────────────────────────────────────────────────────┤
│ PRIORITÉ 2: HIGH VALUE (Impact ÉLEVÉ, Effort MOYEN)                                  │
├──────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│ 2.1 INTÉGRER tactical_matrix                                                         │
│     → Matcher playing_style (home) vs playing_style (away)                           │
│     → Récupérer btts_probability, over_25_probability, upset_probability             │
│     → Gain: +10-15 pts Score                                                         │
│                                                                                      │
│ 2.2 INTÉGRER head_to_head                                                            │
│     → Chercher paire (team_a, team_b) ou (team_b, team_a)                            │
│     → Utiliser dominance_factor, over_25_percentage, btts_percentage                 │
│     → Gain: +5-10 pts Score                                                          │
│                                                                                      │
├──────────────────────────────────────────────────────────────────────────────────────┤
│ PRIORITÉ 3: NICE TO HAVE (Impact MOYEN, Effort MOYEN/ÉLEVÉ)                          │
├──────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│ 3.1 scorer_intelligence - Si joueur clé absent/présent                               │
│ 3.2 coach_intelligence - Style tactique du coach                                     │
│ 3.3 referee_intelligence - Si arbitre connu                                          │
│                                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────┘

SCORE POTENTIEL APRÈS INTÉGRATION COMPLÈTE:
   Actuel:    21 pts (4 sources exploitées)
   Priorité 1: +15 pts → 36 pts
   Priorité 2: +20 pts → 56 pts  
   Priorité 3: +10 pts → 66 pts (STRONG BET niveau)
""")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6: VÉRIFICATION QUALITÉ DES DONNÉES CRITIQUES
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*90)
print("SECTION 6: VÉRIFICATION QUALITÉ - DONNÉES OBSOLÈTES/MANQUANTES")
print("═"*90)

# 6.1 Vérifier fraîcheur des données
print("\n🕐 6.1 FRAÎCHEUR DES DONNÉES")
print("-"*70)

freshness_queries = [
    ("team_intelligence", "updated_at"),
    ("team_class", "updated_at"),
    ("team_momentum", "calculated_at"),
    ("head_to_head", "updated_at"),
    ("scorer_intelligence", "updated_at"),
    ("coach_intelligence", "updated_at"),
]

for table, col in freshness_queries:
    try:
        cur.execute(f"SELECT MAX({col}), MIN({col}) FROM {table}")
        r = cur.fetchone()
        print(f"   {table:<25}: Dernier update {r[0]}, Plus ancien {r[1]}")
    except:
        print(f"   {table:<25}: Colonne {col} non trouvée")

# 6.2 Vérifier cohérence Liverpool/Sunderland
print("\n🔍 6.2 COHÉRENCE DONNÉES LIVERPOOL vs SUNDERLAND")
print("-"*70)

for team in ['Liverpool', 'Sunderland']:
    print(f"\n   {team}:")
    
    # team_intelligence
    cur.execute("""
        SELECT current_style, home_btts_rate, home_over25_rate, xg_for_avg
        FROM team_intelligence WHERE LOWER(team_name) LIKE %s
    """, (f"%{team.lower()}%",))
    r = cur.fetchone()
    if r:
        print(f"      TI: Style={r['current_style']}, BTTS={r['home_btts_rate']}%, Over25={r['home_over25_rate']}%, xG={r['xg_for_avg']}")
    
    # team_class
    cur.execute("""
        SELECT playing_style, home_fortress_factor, psychological_edge
        FROM team_class WHERE LOWER(team_name) LIKE %s
    """, (f"%{team.lower()}%",))
    r = cur.fetchone()
    if r:
        print(f"      TC: Style={r['playing_style']}, HomeFort={r['home_fortress_factor']}, PsychEdge={r['psychological_edge']}")

print("\n" + "="*90)
print("✅ ANALYSE SCIENTIFIQUE TERMINÉE")
print("="*90)

cur.close()
conn.close()
