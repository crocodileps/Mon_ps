#!/usr/bin/env python3
"""
📊 CRON: Calcul des statistiques par ligue
Agrège les performances par ligue depuis match_results et tracking_clv_picks

Usage:
    python3 populate_fg_league_stats.py

Cron recommandé: 0 7 * * * (tous les jours à 7h)
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from datetime import datetime
import logging

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/monps/league_stats.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Configuration DB
DB_CONFIG = {
    'host': os.environ.get('POSTGRES_HOST', 'localhost'),
    'port': int(os.environ.get('POSTGRES_PORT', 5432)),
    'dbname': os.environ.get('POSTGRES_DB', 'monps_db'),
    'user': os.environ.get('POSTGRES_USER', 'monps_user'),
    'password': os.environ.get('POSTGRES_PASSWORD', 'monps_secure_password_2024')
}

def populate_league_stats():
    """Calcule et insère les stats par ligue"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Calculer les stats depuis match_results
        cursor.execute("""
            WITH league_match_stats AS (
                SELECT 
                    league,
                    COUNT(*) as total_matches,
                    ROUND(AVG(score_home + score_away)::numeric, 2) as avg_actual_goals,
                    ROUND(AVG(CASE WHEN score_home > score_away THEN 1.0 ELSE 0.0 END) * 100, 1) as home_win_pct,
                    ROUND(AVG(CASE WHEN score_home = score_away THEN 1.0 ELSE 0.0 END) * 100, 1) as draw_pct,
                    ROUND(AVG(CASE WHEN score_home + score_away > 2.5 THEN 1.0 ELSE 0.0 END) * 100, 1) as over25_pct,
                    ROUND(AVG(CASE WHEN score_home > 0 AND score_away > 0 THEN 1.0 ELSE 0.0 END) * 100, 1) as btts_pct
                FROM match_results
                WHERE is_finished = true
                AND league IS NOT NULL AND league != ''
                GROUP BY league
                HAVING COUNT(*) >= 5
            ),
            league_picks_stats AS (
                SELECT 
                    league,
                    COUNT(*) as total_predictions,
                    SUM(CASE WHEN is_winner THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN is_resolved AND NOT is_winner THEN 1 ELSE 0 END) as losses,
                    ROUND(AVG(clv_percentage)::numeric, 2) as avg_clv,
                    ROUND(SUM(profit_loss)::numeric, 2) as total_pnl
                FROM tracking_clv_picks
                WHERE league IS NOT NULL AND league != ''
                GROUP BY league
            ),
            market_performance AS (
                SELECT 
                    league,
                    market_type,
                    COUNT(*) as picks,
                    SUM(CASE WHEN is_winner THEN 1 ELSE 0 END) as wins,
                    ROUND(100.0 * SUM(CASE WHEN is_winner THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) as win_rate
                FROM tracking_clv_picks
                WHERE league IS NOT NULL AND is_resolved
                GROUP BY league, market_type
            )
            SELECT 
                lms.league,
                lms.total_matches,
                COALESCE(lps.total_predictions, 0) as total_predictions,
                COALESCE(lps.wins, 0) as wins,
                COALESCE(lps.losses, 0) as losses,
                CASE WHEN lps.total_predictions > 0 
                     THEN ROUND(100.0 * lps.wins / NULLIF(lps.wins + lps.losses, 0), 1)
                     ELSE NULL END as win_rate,
                CASE WHEN lps.total_predictions > 0 
                     THEN ROUND(100.0 * COALESCE(lps.total_pnl, 0) / (lps.total_predictions * 10), 2)
                     ELSE NULL END as roi_pct,
                lps.avg_clv,
                lms.avg_actual_goals
            FROM league_match_stats lms
            LEFT JOIN league_picks_stats lps ON lms.league = lps.league
            ORDER BY lms.total_matches DESC
        """)
        
        leagues = cursor.fetchall()
        logger.info(f"📊 {len(leagues)} ligues à traiter")
        
        # Calculer best/worst market par ligue
        cursor.execute("""
            SELECT 
                league,
                market_type,
                COUNT(*) as picks,
                SUM(CASE WHEN is_winner THEN 1 ELSE 0 END) as wins,
                ROUND(100.0 * SUM(CASE WHEN is_winner THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) as win_rate,
                ROUND(SUM(profit_loss)::numeric, 2) as pnl
            FROM tracking_clv_picks
            WHERE league IS NOT NULL AND is_resolved AND league != ''
            GROUP BY league, market_type
            HAVING COUNT(*) >= 3
            ORDER BY league, win_rate DESC
        """)
        market_perfs = cursor.fetchall()
        
        # Organiser par ligue
        market_by_league = {}
        for mp in market_perfs:
            league = mp['league']
            if league not in market_by_league:
                market_by_league[league] = []
            market_by_league[league].append(mp)
        
        # Insérer/Mettre à jour chaque ligue
        for league_data in leagues:
            league = league_data['league']
            
            # Trouver best/worst market
            markets = market_by_league.get(league, [])
            best_market = None
            best_market_roi = None
            worst_market = None
            worst_market_roi = None
            market_perf_json = {}
            
            if markets:
                # Trier par ROI
                sorted_markets = sorted(markets, key=lambda x: x['pnl'] or 0, reverse=True)
                if sorted_markets:
                    best_market = sorted_markets[0]['market_type']
                    best_market_roi = float(sorted_markets[0]['win_rate'] or 0)
                    worst_market = sorted_markets[-1]['market_type']
                    worst_market_roi = float(sorted_markets[-1]['win_rate'] or 0)
                
                for m in markets:
                    market_perf_json[m['market_type']] = {
                        'picks': m['picks'],
                        'wins': m['wins'],
                        'win_rate': float(m['win_rate'] or 0),
                        'pnl': float(m['pnl'] or 0)
                    }
            
            # Upsert
            cursor.execute("""
                INSERT INTO fg_league_stats (
                    league, total_matches, total_predictions,
                    wins, losses, win_rate, roi_pct, avg_clv,
                    market_performance, best_market, best_market_roi,
                    worst_market, worst_market_roi,
                    avg_actual_goals, last_updated
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, NOW()
                )
                ON CONFLICT (league) DO UPDATE SET
                    total_matches = EXCLUDED.total_matches,
                    total_predictions = EXCLUDED.total_predictions,
                    wins = EXCLUDED.wins,
                    losses = EXCLUDED.losses,
                    win_rate = EXCLUDED.win_rate,
                    roi_pct = EXCLUDED.roi_pct,
                    avg_clv = EXCLUDED.avg_clv,
                    market_performance = EXCLUDED.market_performance,
                    best_market = EXCLUDED.best_market,
                    best_market_roi = EXCLUDED.best_market_roi,
                    worst_market = EXCLUDED.worst_market,
                    worst_market_roi = EXCLUDED.worst_market_roi,
                    avg_actual_goals = EXCLUDED.avg_actual_goals,
                    last_updated = NOW()
            """, (
                league, league_data['total_matches'], league_data['total_predictions'],
                league_data['wins'], league_data['losses'],
                league_data['win_rate'], league_data['roi_pct'], league_data['avg_clv'],
                Json(market_perf_json) if market_perf_json else None,
                best_market, best_market_roi, worst_market, worst_market_roi,
                league_data['avg_actual_goals']
            ))
        
        conn.commit()
        
        # Vérifier contrainte unique
        cursor.execute("SELECT COUNT(*) as total FROM fg_league_stats")
        total = cursor.fetchone()['total']
        logger.info(f"✅ {total} ligues dans fg_league_stats")
        
        # Top ligues
        cursor.execute("""
            SELECT league, total_matches, win_rate, avg_clv, best_market
            FROM fg_league_stats
            ORDER BY total_matches DESC
            LIMIT 10
        """)
        top = cursor.fetchall()
        for t in top:
            logger.info(f"   {t['league']}: {t['total_matches']} matchs, WR={t['win_rate']}%, CLV={t['avg_clv']}, Best={t['best_market']}")
        
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    logger.info("🚀 Démarrage calcul stats par ligue")
    populate_league_stats()
    logger.info("✅ Terminé")
