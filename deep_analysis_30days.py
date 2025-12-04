#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════════════
ANALYSE APPROFONDIE V11.3 - 30 JOURS
Objectif: Identifier TOUTES les faiblesses et opportunités d'amélioration
═══════════════════════════════════════════════════════════════════════════════════════
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from collections import defaultdict
from datetime import datetime
import sys
sys.path.insert(0, '/home/Mon_ps')
from orchestrator_v11_3_full_analysis import OrchestratorV11_3

DB_CONFIG = {
    'host': 'localhost', 'port': 5432, 'dbname': 'monps_db',
    'user': 'monps_user', 'password': 'monps_secure_password_2024'
}

def run_deep_analysis():
    print("═" * 90)
    print("    ANALYSE APPROFONDIE V11.3 - 30 JOURS")
    print("═" * 90)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    
    # Charger les matchs
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT DISTINCT ON (home_team, away_team, DATE(commence_time))
            id, home_team, away_team, score_home, score_away, 
            league, commence_time, outcome
        FROM match_results
        WHERE commence_time >= NOW() - INTERVAL '30 days'
          AND is_finished = true
          AND score_home IS NOT NULL
        ORDER BY home_team, away_team, DATE(commence_time), id DESC
    """)
    matches = cur.fetchall()
    conn.close()
    
    print(f"📥 {len(matches)} matchs chargés\n")
    
    # Initialiser l'orchestrator
    orch = OrchestratorV11_3()
    
    # Structures pour l'analyse
    all_results = []
    by_layer = defaultdict(lambda: {'wins': [], 'losses': []})
    by_league = defaultdict(lambda: {'total': 0, 'wins': 0, 'details': []})
    by_market = defaultdict(lambda: {'total': 0, 'wins': 0})
    by_score_range = defaultdict(lambda: {'total': 0, 'wins': 0, 'matches': []})
    by_day_of_week = defaultdict(lambda: {'total': 0, 'wins': 0})
    by_hour = defaultdict(lambda: {'total': 0, 'wins': 0})
    false_positives = []  # Hauts scores qui ont perdu
    false_negatives = []  # Bas scores qui ont gagné
    
    for m in matches:
        result = orch.analyze_match(m['home_team'], m['away_team'], "over_25")
        
        score = result['score']
        market = result['recommended_market']
        layer_scores = result.get('layer_scores', {})
        
        # Calculer le résultat réel
        total_goals = int(m['score_home']) + int(m['score_away'])
        h_score, a_score = int(m['score_home']), int(m['score_away'])
        
        if market == 'over_25':
            correct = total_goals > 2.5
        elif market == 'btts_yes':
            correct = h_score > 0 and a_score > 0
        elif market == 'btts_no':
            correct = h_score == 0 or a_score == 0
        elif market == 'under_25':
            correct = total_goals < 2.5
        else:
            correct = total_goals > 2.5
        
        match_data = {
            'home': m['home_team'],
            'away': m['away_team'],
            'score_v11': score,
            'market': market,
            'result': f"{m['score_home']}-{m['score_away']}",
            'correct': correct,
            'league': m['league'] or 'Unknown',
            'date': m['commence_time'],
            'layers': layer_scores,
            'over25_prob': result.get('over25_prob', 50),
            'btts_prob': result.get('btts_prob', 50),
        }
        all_results.append(match_data)
        
        # Par layer
        for layer, layer_score in layer_scores.items():
            if correct:
                by_layer[layer]['wins'].append(layer_score)
            else:
                by_layer[layer]['losses'].append(layer_score)
        
        # Par ligue
        league = m['league'] or 'Unknown'
        by_league[league]['total'] += 1
        if correct:
            by_league[league]['wins'] += 1
        by_league[league]['details'].append(match_data)
        
        # Par marché
        by_market[market]['total'] += 1
        if correct:
            by_market[market]['wins'] += 1
        
        # Par score range
        score_range = f"{int(score // 2) * 2}-{int(score // 2) * 2 + 2}"
        by_score_range[score_range]['total'] += 1
        if correct:
            by_score_range[score_range]['wins'] += 1
        by_score_range[score_range]['matches'].append(match_data)
        
        # Par jour de la semaine
        if m['commence_time']:
            dow = m['commence_time'].strftime('%A')
            by_day_of_week[dow]['total'] += 1
            if correct:
                by_day_of_week[dow]['wins'] += 1
            
            # Par heure
            hour = m['commence_time'].hour
            by_hour[hour]['total'] += 1
            if correct:
                by_hour[hour]['wins'] += 1
        
        # Faux positifs (score élevé mais perdu)
        if score >= 28 and not correct:
            false_positives.append(match_data)
        
        # Faux négatifs (score bas mais gagné)
        if score < 24 and correct:
            false_negatives.append(match_data)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # RAPPORT 1: IMPACT DES LAYERS (DÉTAILLÉ)
    # ═══════════════════════════════════════════════════════════════════════════════
    print("┌" + "─" * 88 + "┐")
    print("│ 1️⃣  IMPACT DÉTAILLÉ DES LAYERS                                                        │")
    print("└" + "─" * 88 + "┘")
    
    layer_impact = []
    for layer, data in by_layer.items():
        wins = data['wins']
        losses = data['losses']
        if wins and losses:
            avg_win = sum(wins) / len(wins)
            avg_loss = sum(losses) / len(losses)
            delta = avg_win - avg_loss
            correlation = delta / (avg_win + 0.01)  # Correlation relative
            layer_impact.append((layer, avg_win, avg_loss, delta, correlation, len(wins), len(losses)))
    
    layer_impact.sort(key=lambda x: -x[3])  # Trier par delta
    
    print(f"\n   {'Layer':<20} | {'Avg Win':>8} | {'Avg Loss':>8} | {'Delta':>7} | {'Corr':>6} | {'Wins':>5} | {'Losses':>6}")
    print("   " + "─" * 75)
    for layer, avg_win, avg_loss, delta, corr, wins, losses in layer_impact:
        indicator = "📈" if delta > 0.5 else ("➡️" if delta > 0 else "📉")
        print(f"   {indicator} {layer:<17} | {avg_win:>8.2f} | {avg_loss:>8.2f} | {delta:>+7.2f} | {corr:>6.2f} | {wins:>5} | {losses:>6}")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # RAPPORT 2: PERFORMANCE PAR LIGUE
    # ═══════════════════════════════════════════════════════════════════════════════
    print("\n┌" + "─" * 88 + "┐")
    print("│ 2️⃣  PERFORMANCE PAR LIGUE (triée par ROI)                                              │")
    print("└" + "─" * 88 + "┘\n")
    
    league_stats = []
    for league, data in by_league.items():
        if data['total'] >= 3:
            wr = data['wins'] / data['total'] * 100
            roi = (data['wins'] * 1.85 - data['total']) / data['total'] * 100
            league_stats.append((league, data['total'], data['wins'], wr, roi))
    
    league_stats.sort(key=lambda x: -x[4])  # Trier par ROI
    
    print(f"   {'Ligue':<35} | {'Total':>5} | {'Wins':>5} | {'WR':>6} | {'ROI':>8}")
    print("   " + "─" * 70)
    for league, total, wins, wr, roi in league_stats:
        indicator = "✅" if roi > 10 else ("⚠️" if roi > 0 else "❌")
        print(f"   {indicator} {league[:33]:<33} | {total:>5} | {wins:>5} | {wr:>5.1f}% | {roi:>+7.1f}%")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # RAPPORT 3: PERFORMANCE PAR MARCHÉ
    # ═══════════════════════════════════════════════════════════════════════════════
    print("\n┌" + "─" * 88 + "┐")
    print("│ 3️⃣  PERFORMANCE PAR MARCHÉ                                                             │")
    print("└" + "─" * 88 + "┘\n")
    
    for market, data in sorted(by_market.items(), key=lambda x: -x[1]['total']):
        if data['total'] >= 5:
            wr = data['wins'] / data['total'] * 100
            roi = (data['wins'] * 1.85 - data['total']) / data['total'] * 100
            indicator = "✅" if roi > 10 else ("⚠️" if roi > 0 else "❌")
            print(f"   {indicator} {market:<20} | {data['wins']:>3}/{data['total']:<3} ({wr:>5.1f}%) | ROI: {roi:>+6.1f}%")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # RAPPORT 4: PERFORMANCE PAR JOUR
    # ═══════════════════════════════════════════════════════════════════════════════
    print("\n┌" + "─" * 88 + "┐")
    print("│ 4️⃣  PERFORMANCE PAR JOUR DE LA SEMAINE                                                 │")
    print("└" + "─" * 88 + "┘\n")
    
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    for day in days_order:
        if day in by_day_of_week:
            data = by_day_of_week[day]
            if data['total'] >= 3:
                wr = data['wins'] / data['total'] * 100
                roi = (data['wins'] * 1.85 - data['total']) / data['total'] * 100
                indicator = "✅" if roi > 10 else ("⚠️" if roi > 0 else "❌")
                bar = "█" * int(wr / 5)
                print(f"   {indicator} {day:<12} | {data['wins']:>3}/{data['total']:<3} ({wr:>5.1f}%) | ROI: {roi:>+6.1f}% | {bar}")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # RAPPORT 5: FAUX POSITIFS (ANALYSE DES ÉCHECS)
    # ═══════════════════════════════════════════════════════════════════════════════
    print("\n┌" + "─" * 88 + "┐")
    print("│ 5️⃣  FAUX POSITIFS - Scores élevés (≥28) qui ont PERDU                                  │")
    print("└" + "─" * 88 + "┘\n")
    
    if false_positives:
        print(f"   ⚠️ {len(false_positives)} matchs avec score ≥28 ont perdu:\n")
        for fp in sorted(false_positives, key=lambda x: -x['score_v11']):
            print(f"   ❌ {fp['home'][:20]:20} vs {fp['away'][:20]:20} | {fp['result']}")
            print(f"      Score: {fp['score_v11']:.1f} | Market: {fp['market']} | {fp['league'][:30]}")
            print(f"      Layers: {', '.join(f'{k}:{v:.1f}' for k, v in fp['layers'].items() if v > 0)}")
            print()
    else:
        print("   ✅ Aucun faux positif - Tous les scores ≥28 ont gagné!")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # RAPPORT 6: PATTERNS DE SUCCÈS
    # ═══════════════════════════════════════════════════════════════════════════════
    print("\n┌" + "─" * 88 + "┐")
    print("│ 6️⃣  PATTERNS DE SUCCÈS - Qu'est-ce qui prédit le mieux les victoires?                  │")
    print("└" + "─" * 88 + "┘\n")
    
    # Analyser les victoires vs défaites
    wins = [r for r in all_results if r['correct']]
    losses = [r for r in all_results if not r['correct']]
    
    print(f"   Total: {len(wins)} victoires / {len(losses)} défaites ({len(wins)/len(all_results)*100:.1f}% WR)\n")
    
    # Comparer les probabilités moyennes
    avg_o25_wins = sum(r['over25_prob'] for r in wins) / len(wins) if wins else 0
    avg_o25_losses = sum(r['over25_prob'] for r in losses) / len(losses) if losses else 0
    avg_btts_wins = sum(r['btts_prob'] for r in wins) / len(wins) if wins else 0
    avg_btts_losses = sum(r['btts_prob'] for r in losses) / len(losses) if losses else 0
    
    print(f"   Over 2.5 prob moyenne:  Wins={avg_o25_wins:.1f}% | Losses={avg_o25_losses:.1f}% | Δ={avg_o25_wins-avg_o25_losses:+.1f}%")
    print(f"   BTTS prob moyenne:      Wins={avg_btts_wins:.1f}% | Losses={avg_btts_losses:.1f}% | Δ={avg_btts_wins-avg_btts_losses:+.1f}%")
    
    # Trouver les seuils optimaux
    print("\n   🎯 SEUILS OPTIMAUX (basés sur probabilités):")
    for threshold in [55, 60, 65, 70]:
        high_conf = [r for r in all_results if r['over25_prob'] >= threshold]
        if high_conf:
            wr = sum(1 for r in high_conf if r['correct']) / len(high_conf) * 100
            print(f"      O25 >= {threshold}%: {len(high_conf)} matchs → {wr:.1f}% WR")
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # RAPPORT 7: RECOMMANDATIONS
    # ═══════════════════════════════════════════════════════════════════════════════
    print("\n┌" + "─" * 88 + "┐")
    print("│ 7️⃣  RECOMMANDATIONS D'AMÉLIORATION                                                     │")
    print("└" + "─" * 88 + "┘\n")
    
    recommendations = []
    
    # Ligues à éviter
    bad_leagues = [l for l, t, w, wr, roi in league_stats if roi < -5 and t >= 5]
    if bad_leagues:
        recommendations.append(f"❌ ÉVITER ces ligues (ROI négatif): {', '.join(bad_leagues[:3])}")
    
    # Ligues à privilégier
    good_leagues = [l for l, t, w, wr, roi in league_stats if roi > 20 and t >= 5]
    if good_leagues:
        recommendations.append(f"✅ PRIVILÉGIER ces ligues (ROI > 20%): {', '.join(good_leagues[:3])}")
    
    # Layers à améliorer
    weak_layers = [l for l, aw, al, d, c, w, lo in layer_impact if d < 0.1]
    if weak_layers:
        recommendations.append(f"�� LAYERS À AMÉLIORER (faible impact): {', '.join(weak_layers)}")
    
    # Marchés à privilégier
    for market, data in by_market.items():
        if data['total'] >= 10:
            wr = data['wins'] / data['total'] * 100
            if wr > 65:
                recommendations.append(f"🎯 MARCHÉ FORT: {market} ({wr:.0f}% WR)")
    
    for rec in recommendations:
        print(f"   {rec}")
    
    print("\n" + "═" * 90)
    print("    FIN DE L'ANALYSE APPROFONDIE")
    print("═" * 90)

if __name__ == "__main__":
    run_deep_analysis()
