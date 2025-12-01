#!/usr/bin/env python3
"""
📊 COACH RECOMMENDATIONS PERFORMANCE TRACKER
=============================================
Enregistre et évalue les recommandations Coach Intelligence
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import logging
import sys

sys.path.insert(0, '/app/agents')

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger('CoachTracker')

DB_CONFIG = {
    'host': 'postgres',
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}


def get_coach_recommendation(home_team: str, away_team: str) -> dict:
    """Génère les recommandations coach pour un match"""
    try:
        from coach_impact import CoachImpactCalculator
        calc = CoachImpactCalculator()
        
        home_factors = calc.get_coach_factors(home_team)
        away_factors = calc.get_coach_factors(away_team)
        
        # xG
        result = calc.calculate_adjusted_xg(home_team, away_team, 1.5, 1.2)
        
        h_style = home_factors.get('style', 'unknown')
        a_style = away_factors.get('style', 'unknown')
        
        # Déterminer matchup et recommandations
        if 'offensive' in h_style and 'offensive' in a_style:
            matchup = 'OPEN_GAME'
            recommendations = [
                ('over_25', 'STRONG', 15),
                ('btts_yes', 'GOOD', 10)
            ]
        elif 'defensive' in h_style and 'defensive' in a_style:
            matchup = 'CLOSED_GAME'
            recommendations = [
                ('under_25', 'STRONG', 15),
                ('btts_no', 'LEAN', 5)
            ]
        elif 'offensive' in h_style and 'defensive' in a_style:
            matchup = 'HOME_SIEGE'
            recommendations = [
                ('home_win', 'LEAN', 5)
            ]
        elif 'defensive' in h_style and 'offensive' in a_style:
            matchup = 'COUNTER_ATTACK'
            recommendations = [
                ('draw', 'LEAN', 8)
            ]
        else:
            matchup = 'BALANCED'
            recommendations = []
        
        return {
            'home_coach': home_factors.get('coach'),
            'away_coach': away_factors.get('coach'),
            'matchup': matchup,
            'recommendations': recommendations,
            'home_xg': result['home_xg'],
            'away_xg': result['away_xg'],
            'total_xg': result['total_xg']
        }
    except Exception as e:
        logger.error(f"Error getting recommendation: {e}")
        return None


def record_upcoming_matches():
    """Enregistre les recommandations pour les matchs à venir"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Trouver les matchs des prochaines 24h sans recommandation
    cur.execute("""
        SELECT DISTINCT home_team, away_team, commence_time, match_id
        FROM upcoming_matches
        WHERE commence_time BETWEEN NOW() AND NOW() + INTERVAL '24 hours'
        AND match_id NOT IN (
            SELECT match_id FROM coach_recommendations_tracking WHERE match_id IS NOT NULL
        )
        LIMIT 50
    """)
    
    matches = cur.fetchall()
    logger.info(f"📋 Found {len(matches)} matches to analyze")
    
    recorded = 0
    for match in matches:
        reco = get_coach_recommendation(match['home_team'], match['away_team'])
        
        if reco and reco['recommendations']:
            for market, strength, boost in reco['recommendations']:
                try:
                    cur.execute("""
                        INSERT INTO coach_recommendations_tracking (
                            match_id, home_team, away_team,
                            home_coach, away_coach, tactical_matchup,
                            recommended_market, recommendation_strength, boost_pct,
                            predicted_home_xg, predicted_away_xg, predicted_total_xg
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (match_id, recommended_market) DO NOTHING
                    """, (
                        match['match_id'], match['home_team'], match['away_team'],
                        reco['home_coach'], reco['away_coach'], reco['matchup'],
                        market, strength, boost,
                        reco['home_xg'], reco['away_xg'], reco['total_xg']
                    ))
                    recorded += 1
                except Exception as e:
                    logger.error(f"Error recording {match['home_team']} vs {match['away_team']}: {e}")
                    conn.rollback()
    
    conn.commit()
    logger.info(f"✅ Recorded {recorded} recommendations")
    
    cur.close()
    conn.close()
    return recorded


def resolve_finished_matches():
    """Résout les recommandations avec les résultats réels"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Trouver les recommandations non résolues
    cur.execute("""
        SELECT crt.id, crt.match_id, crt.home_team, crt.away_team,
               crt.recommended_market, crt.predicted_total_xg
        FROM coach_recommendations_tracking crt
        WHERE crt.recommendation_correct IS NULL
        AND crt.created_at < NOW() - INTERVAL '3 hours'
    """)
    
    pending = cur.fetchall()
    logger.info(f"📊 Found {len(pending)} recommendations to resolve")
    
    resolved = 0
    for reco in pending:
        # Chercher le résultat
        cur.execute("""
            SELECT score_home, score_away
            FROM match_results
            WHERE (home_team ILIKE %s AND away_team ILIKE %s)
            OR match_id = %s
            LIMIT 1
        """, (f"%{reco['home_team']}%", f"%{reco['away_team']}%", reco['match_id']))
        
        result = cur.fetchone()
        
        if result and result['score_home'] is not None:
            home_goals = result['score_home']
            away_goals = result['score_away']
            total_goals = home_goals + away_goals
            
            # Évaluer la recommandation
            market = reco['recommended_market']
            correct = False
            
            if market == 'over_25':
                correct = total_goals > 2.5
            elif market == 'under_25':
                correct = total_goals < 2.5
            elif market == 'btts_yes':
                correct = home_goals > 0 and away_goals > 0
            elif market == 'btts_no':
                correct = home_goals == 0 or away_goals == 0
            elif market == 'home_win':
                correct = home_goals > away_goals
            elif market == 'draw':
                correct = home_goals == away_goals
            elif market == 'away_win':
                correct = home_goals < away_goals
            
            # Calculer précision xG
            predicted = reco['predicted_total_xg'] or 2.5
            xg_accuracy = max(0, 100 - abs(total_goals - predicted) * 20)
            
            cur.execute("""
                UPDATE coach_recommendations_tracking
                SET actual_home_goals = %s,
                    actual_away_goals = %s,
                    actual_total_goals = %s,
                    recommendation_correct = %s,
                    xg_accuracy = %s,
                    resolved_at = NOW()
                WHERE id = %s
            """, (home_goals, away_goals, total_goals, correct, xg_accuracy, reco['id']))
            
            resolved += 1
    
    conn.commit()
    logger.info(f"✅ Resolved {resolved} recommendations")
    
    cur.close()
    conn.close()
    return resolved


def print_performance_stats():
    """Affiche les statistiques de performance"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Stats globales
    cur.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN recommendation_correct THEN 1 END) as wins,
            COUNT(CASE WHEN recommendation_correct = false THEN 1 END) as losses,
            COUNT(CASE WHEN recommendation_correct IS NULL THEN 1 END) as pending,
            ROUND(AVG(xg_accuracy)::numeric, 1) as avg_xg_accuracy
        FROM coach_recommendations_tracking
    """)
    
    stats = cur.fetchone()
    
    print("\n" + "="*60)
    print("📊 COACH INTELLIGENCE PERFORMANCE STATS")
    print("="*60)
    print(f"Total recommendations: {stats['total']}")
    print(f"Wins: {stats['wins']} | Losses: {stats['losses']} | Pending: {stats['pending']}")
    
    if stats['wins'] and stats['losses']:
        win_rate = stats['wins'] / (stats['wins'] + stats['losses']) * 100
        print(f"Win Rate: {win_rate:.1f}%")
    
    print(f"Avg xG Accuracy: {stats['avg_xg_accuracy'] or 0}%")
    
    # Stats par matchup
    cur.execute("""
        SELECT 
            tactical_matchup,
            COUNT(*) as total,
            COUNT(CASE WHEN recommendation_correct THEN 1 END) as wins,
            ROUND(AVG(CASE WHEN recommendation_correct IS NOT NULL 
                THEN CASE WHEN recommendation_correct THEN 100 ELSE 0 END END)::numeric, 1) as win_rate
        FROM coach_recommendations_tracking
        WHERE recommendation_correct IS NOT NULL
        GROUP BY tactical_matchup
        ORDER BY win_rate DESC
    """)
    
    matchups = cur.fetchall()
    
    if matchups:
        print("\n📈 Performance by Matchup:")
        for m in matchups:
            print(f"  {m['tactical_matchup']}: {m['wins']}/{m['total']} ({m['win_rate']}%)")
    
    # Stats par marché
    cur.execute("""
        SELECT 
            recommended_market,
            COUNT(*) as total,
            COUNT(CASE WHEN recommendation_correct THEN 1 END) as wins,
            ROUND(AVG(CASE WHEN recommendation_correct IS NOT NULL 
                THEN CASE WHEN recommendation_correct THEN 100 ELSE 0 END END)::numeric, 1) as win_rate
        FROM coach_recommendations_tracking
        WHERE recommendation_correct IS NOT NULL
        GROUP BY recommended_market
        ORDER BY win_rate DESC
    """)
    
    markets = cur.fetchall()
    
    if markets:
        print("\n📈 Performance by Market:")
        for m in markets:
            print(f"  {m['recommended_market']}: {m['wins']}/{m['total']} ({m['win_rate']}%)")
    
    print("="*60 + "\n")
    
    cur.close()
    conn.close()


if __name__ == "__main__":
    logger.info("📊 COACH PERFORMANCE TRACKER")
    logger.info("="*50)
    
    # 1. Enregistrer les nouveaux matchs
    record_upcoming_matches()
    
    # 2. Résoudre les matchs terminés
    resolve_finished_matches()
    
    # 3. Afficher les stats
    print_performance_stats()
