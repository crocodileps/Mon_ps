#!/usr/bin/env python3
"""
🔧 FIX COACH INTELLIGENCE - Calcul correct des stats
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger('CoachFix')

DB_CONFIG = {
    'host': 'postgres',
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}

def fix_all_coach_stats():
    """Recalcule correctement les stats pour tous les coaches"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Récupérer tous les coaches
    cur.execute("SELECT DISTINCT coach_name, current_team FROM coach_intelligence")
    coaches = cur.fetchall()
    
    logger.info(f"🔧 Fixing stats for {len(coaches)} coaches")
    
    fixed = 0
    for coach in coaches:
        team = coach['current_team']
        
        # Calculer les VRAIS stats (buts DE l'équipe, pas du match)
        cur.execute("""
            SELECT 
                COUNT(*) as matches,
                SUM(CASE WHEN home_team ILIKE %s THEN score_home ELSE score_away END) as goals_scored,
                SUM(CASE WHEN home_team ILIKE %s THEN score_away ELSE score_home END) as goals_conceded
            FROM match_results 
            WHERE (home_team ILIKE %s OR away_team ILIKE %s)
            AND score_home IS NOT NULL
            AND commence_time >= NOW() - INTERVAL '6 months'
        """, (f"%{team}%", f"%{team}%", f"%{team}%", f"%{team}%"))
        
        stats = cur.fetchone()
        
        if stats and stats['matches'] and stats['matches'] >= 3:
            matches = int(stats['matches'])
            gf = float(stats['goals_scored'] or 0)
            ga = float(stats['goals_conceded'] or 0)
            
            avg_gf = round(gf / matches, 2)
            avg_ga = round(ga / matches, 2)
            
            # Déterminer le style CORRECT
            # Offensif = marque beaucoup (>1.5)
            # Défensif = encaisse peu (<1.0)
            if avg_gf >= 2.0 and avg_ga <= 1.0:
                style = 'dominant_offensive'
            elif avg_gf >= 1.5:
                style = 'offensive'
            elif avg_ga <= 0.8:
                style = 'ultra_defensive'
            elif avg_ga <= 1.2:
                style = 'defensive'
            else:
                style = 'balanced'
            
            # Win rate
            cur.execute("""
                SELECT COUNT(*) as wins
                FROM match_results 
                WHERE ((home_team ILIKE %s AND score_home > score_away)
                    OR (away_team ILIKE %s AND score_away > score_home))
                AND score_home IS NOT NULL
                AND commence_time >= NOW() - INTERVAL '6 months'
            """, (f"%{team}%", f"%{team}%"))
            
            wins = cur.fetchone()['wins'] or 0
            win_rate = round(wins / matches * 100, 1)
            
            # Update
            cur.execute("""
                UPDATE coach_intelligence
                SET avg_goals_per_match = %s,
                    avg_goals_conceded_per_match = %s,
                    tactical_style = %s,
                    career_matches = %s,
                    career_win_rate = %s,
                    is_reliable = %s,
                    last_computed_at = NOW()
                WHERE coach_name = %s AND current_team = %s
            """, (avg_gf, avg_ga, style, matches, win_rate, matches >= 5, 
                  coach['coach_name'], team))
            
            logger.info(f"✅ {coach['coach_name']} ({team}): GF={avg_gf}, GA={avg_ga}, Style={style}")
            fixed += 1
    
    conn.commit()
    cur.close()
    conn.close()
    
    logger.info(f"🎉 Fixed {fixed} coaches")
    return fixed


if __name__ == "__main__":
    logger.info("🔧 COACH STATS FIX - Calcul correct")
    logger.info("="*50)
    fix_all_coach_stats()
