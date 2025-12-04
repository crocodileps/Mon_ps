#!/usr/bin/env python3
"""
TEAM MARKET PROFILER - Calculate market DNA for each team
"""

import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': 'localhost', 'port': 5432, 'dbname': 'monps_db',
    'user': 'monps_user', 'password': 'monps_secure_password_2024'
}

SEASON = '2025-2026'
MIN_SAMPLE_SIZE = 10

MARKETS = [
    'btts_yes', 'btts_no',
    'over_15', 'over_25', 'over_35',
    'under_15', 'under_25', 'under_35',
    'team_over_05', 'team_over_15',
    'team_clean_sheet', 'team_fail_to_score'
]


def calculate_market_outcome(home_goals, away_goals, market_type, is_home):
    """Détermine si un marché a gagné"""
    total_goals = home_goals + away_goals
    team_goals = home_goals if is_home else away_goals
    opponent_goals = away_goals if is_home else home_goals
    
    outcomes = {
        'btts_yes': home_goals > 0 and away_goals > 0,
        'btts_no': home_goals == 0 or away_goals == 0,
        'over_15': total_goals > 1.5,
        'over_25': total_goals > 2.5,
        'over_35': total_goals > 3.5,
        'under_15': total_goals < 1.5,
        'under_25': total_goals < 2.5,
        'under_35': total_goals < 3.5,
        'team_over_05': team_goals > 0.5,
        'team_over_15': team_goals > 1.5,
        'team_clean_sheet': opponent_goals == 0,
        'team_fail_to_score': team_goals == 0
    }
    return outcomes.get(market_type, False)


def get_estimated_odds(market_type):
    typical_odds = {
        'btts_yes': 1.75, 'btts_no': 2.00,
        'over_15': 1.30, 'over_25': 1.85, 'over_35': 2.50,
        'under_15': 3.50, 'under_25': 2.00, 'under_35': 1.50,
        'team_over_05': 1.25, 'team_over_15': 2.20,
        'team_clean_sheet': 3.00, 'team_fail_to_score': 4.50
    }
    return typical_odds.get(market_type, 2.00)


def calculate_team_profiles():
    """Calcule les profils pour toutes les équipes"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Récupérer équipes
    cur.execute("""
        SELECT DISTINCT home_team as team, league FROM match_xg_stats
        UNION
        SELECT DISTINCT away_team as team, league FROM match_xg_stats
    """)
    teams = cur.fetchall()
    conn.close()
    
    logger.info(f"📊 Calcul des profils pour {len(teams)} équipes")
    profiles_created = 0
    
    for team_row in teams:
        team = team_row['team']
        league = team_row['league']
        
        # Nouvelle connexion par équipe pour éviter les transactions bloquées
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            cur.execute("""
                SELECT home_team, away_team, home_goals, away_goals, match_date
                FROM match_xg_stats
                WHERE home_team = %s OR away_team = %s
                ORDER BY match_date DESC
            """, (team, team))
            matches = cur.fetchall()
            
            if len(matches) < 3:
                conn.close()
                continue
            
            market_stats = {}
            
            for market in MARKETS:
                wins = 0
                for match in matches:
                    is_home = match['home_team'] == team
                    hg = int(match['home_goals'] or 0)
                    ag = int(match['away_goals'] or 0)
                    if calculate_market_outcome(hg, ag, market, is_home):
                        wins += 1
                
                total = len(matches)
                win_rate = (wins / total) * 100
                avg_odds = get_estimated_odds(market)
                roi = (win_rate / 100 * avg_odds - 1) * 100
                
                market_stats[market] = {
                    'matches': total, 'wins': wins,
                    'win_rate': round(win_rate, 2),
                    'avg_odds': avg_odds, 'roi': round(roi, 2),
                    'is_valid': total >= MIN_SAMPLE_SIZE
                }
            
            sorted_markets = sorted(market_stats.items(), key=lambda x: x[1]['roi'], reverse=True)
            
            for rank, (market, stats) in enumerate(sorted_markets, 1):
                is_best = rank <= 2 and stats['roi'] > 0 and stats['is_valid']
                is_avoid = rank >= len(sorted_markets) - 1 and stats['roi'] < -10 and stats['is_valid']
                confidence = min(100, stats['matches'] * 3 + abs(stats['roi']) * 0.5) if stats['is_valid'] else 0
                
                cur.execute("""
                    INSERT INTO team_market_profiles
                    (team_name, league, season, market_type, matches_played, wins, losses,
                     win_rate, avg_odds, roi, sample_size, is_statistically_valid,
                     is_best_market, is_avoid_market, confidence_score, market_rank, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (team_name, league, season, market_type) DO UPDATE SET
                        wins = EXCLUDED.wins, win_rate = EXCLUDED.win_rate, roi = EXCLUDED.roi,
                        is_best_market = EXCLUDED.is_best_market, market_rank = EXCLUDED.market_rank,
                        updated_at = NOW()
                """, (
                    team, league, SEASON, market,
                    stats['matches'], stats['wins'], stats['matches'] - stats['wins'],
                    stats['win_rate'], stats['avg_odds'], stats['roi'],
                    stats['matches'], stats['is_valid'], is_best, is_avoid, confidence, rank
                ))
                profiles_created += 1
            
            conn.commit()
        except Exception as e:
            logger.error(f"Erreur {team}: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    logger.info(f"✅ {profiles_created} profils créés")
    return profiles_created


def calculate_context_modifiers():
    """Calcule les modificateurs Home/Away"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    cur.execute("SELECT DISTINCT team_name, league FROM team_market_profiles")
    teams = cur.fetchall()
    conn.close()
    
    logger.info(f"📊 Calcul contexte pour {len(teams)} équipes")
    contexts_created = 0
    jekyll_hyde_teams = set()
    
    for team_row in teams:
        team = team_row['team_name']
        league = team_row['league']
        
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            # Baseline
            cur.execute("""
                SELECT market_type, win_rate FROM team_market_profiles 
                WHERE team_name = %s AND league = %s
            """, (team, league))
            baselines = {r['market_type']: float(r['win_rate']) for r in cur.fetchall()}
            
            # Home matches
            cur.execute("SELECT home_goals, away_goals FROM match_xg_stats WHERE home_team = %s", (team,))
            home_matches = cur.fetchall()
            
            # Away matches
            cur.execute("SELECT home_goals, away_goals FROM match_xg_stats WHERE away_team = %s", (team,))
            away_matches = cur.fetchall()
            
            for market in MARKETS:
                home_wins = sum(1 for m in home_matches if calculate_market_outcome(
                    int(m['home_goals'] or 0), int(m['away_goals'] or 0), market, True))
                away_wins = sum(1 for m in away_matches if calculate_market_outcome(
                    int(m['home_goals'] or 0), int(m['away_goals'] or 0), market, False))
                
                home_total = len(home_matches)
                away_total = len(away_matches)
                
                if home_total >= 3 and away_total >= 3:
                    home_wr = (home_wins / home_total) * 100
                    away_wr = (away_wins / away_total) * 100
                    baseline = baselines.get(market, 50)
                    is_jh = abs(home_wr - away_wr) > 20
                    
                    if is_jh:
                        jekyll_hyde_teams.add(team)
                    
                    for ctx, wr, total, wins in [('home', home_wr, home_total, home_wins), 
                                                  ('away', away_wr, away_total, away_wins)]:
                        delta = wr - baseline
                        cur.execute("""
                            INSERT INTO team_market_context
                            (team_name, league, season, context_type, market_type,
                             matches_in_context, wins_in_context, win_rate_in_context,
                             baseline_win_rate, delta_vs_baseline, sample_size,
                             is_significant, is_jekyll_hyde, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                            ON CONFLICT (team_name, league, season, context_type, market_type) DO UPDATE SET
                                win_rate_in_context = EXCLUDED.win_rate_in_context,
                                delta_vs_baseline = EXCLUDED.delta_vs_baseline,
                                is_jekyll_hyde = EXCLUDED.is_jekyll_hyde,
                                updated_at = NOW()
                        """, (
                            team, league, SEASON, ctx, market,
                            total, wins, round(wr, 2), baseline, round(delta, 2), total,
                            abs(delta) > 10 and total >= 5, is_jh
                        ))
                        contexts_created += 1
            
            conn.commit()
        except Exception as e:
            logger.error(f"Erreur context {team}: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    logger.info(f"✅ {contexts_created} contextes, {len(jekyll_hyde_teams)} Jekyll&Hyde")
    return contexts_created


def calculate_h2h_patterns():
    """Calcule les patterns H2H (fenêtre 3 ans)"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    cur.execute("""
        SELECT DISTINCT 
            LEAST(home_team, away_team) as team_a,
            GREATEST(home_team, away_team) as team_b,
            league
        FROM match_xg_stats
        GROUP BY 1, 2, league HAVING COUNT(*) >= 2
    """)
    pairs = cur.fetchall()
    conn.close()
    
    logger.info(f"📊 Calcul H2H pour {len(pairs)} paires")
    
    three_years_ago = datetime.now() - timedelta(days=3*365)
    patterns_created = 0
    strong_patterns = 0
    
    for pair in pairs:
        team_a, team_b, league = pair['team_a'], pair['team_b'], pair['league']
        
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        try:
            cur.execute("""
                SELECT home_team, away_team, home_goals, away_goals, match_date
                FROM match_xg_stats
                WHERE (home_team = %s AND away_team = %s) OR (home_team = %s AND away_team = %s)
                ORDER BY match_date DESC
            """, (team_a, team_b, team_b, team_a))
            matches = cur.fetchall()
            
            recent = [m for m in matches if m['match_date'] and m['match_date'] >= three_years_ago.date()]
            
            if len(recent) < 2:
                conn.close()
                continue
            
            for market in ['btts_yes', 'btts_no', 'over_25', 'under_25', 'over_35', 'under_35']:
                wins = sum(1 for m in recent if calculate_market_outcome(
                    int(m['home_goals'] or 0), int(m['away_goals'] or 0), market, True))
                total = len(recent)
                win_rate = (wins / total) * 100
                
                is_pattern = win_rate >= 65 and total >= 3
                
                if win_rate >= 80 and total >= 4:
                    strength, override = 'dominant', True
                elif win_rate >= 70 and total >= 3:
                    strength, override = 'strong', True
                elif win_rate >= 65:
                    strength, override = 'moderate', False
                else:
                    strength, override = 'weak', False
                
                desc = f"{market.upper()} en {wins}/{total} ({win_rate:.0f}%)" if is_pattern else None
                
                cur.execute("""
                    INSERT INTO h2h_market_patterns
                    (team_a, team_b, league, market_type, total_matches, matches_last_3_years,
                     wins, win_rate, is_pattern, pattern_strength, pattern_description,
                     override_individual_dna, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (team_a, team_b, market_type) DO UPDATE SET
                        wins = EXCLUDED.wins, win_rate = EXCLUDED.win_rate,
                        is_pattern = EXCLUDED.is_pattern, override_individual_dna = EXCLUDED.override_individual_dna,
                        updated_at = NOW()
                """, (
                    team_a, team_b, league, market, len(matches), total, wins, round(win_rate, 2),
                    is_pattern, strength, desc, override
                ))
                patterns_created += 1
                if is_pattern:
                    strong_patterns += 1
            
            conn.commit()
        except Exception as e:
            logger.error(f"Erreur H2H {team_a} vs {team_b}: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    logger.info(f"✅ {patterns_created} patterns, {strong_patterns} forts")
    return patterns_created


def main():
    print("═══════════════════════════════════════════════════════════════════")
    print("TEAM MARKET PROFILER - Calcul des ADN")
    print("═══════════════════════════════════════════════════════════════════")
    
    print("\n📊 PHASE 1: Profils de marché...")
    calculate_team_profiles()
    
    print("\n📊 PHASE 2: Contexte Home/Away...")
    calculate_context_modifiers()
    
    print("\n📊 PHASE 3: Patterns H2H...")
    calculate_h2h_patterns()
    
    # Résultats
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    print("\n" + "="*70)
    print("TOP ÉQUIPES PAR MARCHÉ")
    print("="*70)
    
    for market in ['btts_no', 'over_25', 'under_25', 'btts_yes']:
        cur.execute("""
            SELECT team_name, league, win_rate, roi
            FROM team_market_profiles
            WHERE market_type = %s AND is_statistically_valid = true
            ORDER BY roi DESC LIMIT 3
        """, (market,))
        results = cur.fetchall()
        
        print(f"\n   {market.upper()}:")
        for r in results:
            print(f"      {r['team_name']} ({r['league']}): {r['win_rate']:.0f}% win, {r['roi']:+.1f}% ROI")
    
    print("\n" + "="*70)
    print("ÉQUIPES JEKYLL & HYDE")
    print("="*70)
    cur.execute("""
        SELECT DISTINCT team_name, market_type FROM team_market_context
        WHERE is_jekyll_hyde = true LIMIT 10
    """)
    for r in cur.fetchall():
        print(f"   🎭 {r['team_name']}: {r['market_type']}")
    
    print("\n" + "="*70)
    print("PATTERNS H2H DOMINANTS")
    print("="*70)
    cur.execute("""
        SELECT team_a, team_b, market_type, win_rate, matches_last_3_years
        FROM h2h_market_patterns
        WHERE override_individual_dna = true
        ORDER BY win_rate DESC LIMIT 10
    """)
    for r in cur.fetchall():
        print(f"   {r['team_a']} vs {r['team_b']}: {r['market_type']} ({r['win_rate']:.0f}%)")
    
    conn.close()
    print("\n✅ TEAM MARKET PROFILER TERMINÉ!")


if __name__ == "__main__":
    main()
