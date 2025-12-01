#!/usr/bin/env python3
"""
🎯 AUTO-RÉSOLUTION DES PICKS - Mon_PS V2
========================================
Collecte les scores finaux et résout automatiquement les picks.
Analyse les erreurs pour apprentissage continu.

Exécution: 3x/jour (15h, 19h, 23h)
Coût: ~15 crédits par exécution

Auteur: Mon_PS System
Date: 01/12/2025
"""
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_KEY = os.environ.get('ODDS_API_KEY', '')
BASE_URL = "https://api.the-odds-api.com/v4"

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'monps_postgres'),
    'port': int(os.environ.get('DB_PORT', 5432)),
    'database': os.environ.get('DB_NAME', 'monps_db'),
    'user': os.environ.get('DB_USER', 'monps_user'),
    'password': os.environ.get('DB_PASSWORD', 'monps_secure_password_2024')
}

SPORTS = [
    'soccer_epl', 'soccer_spain_la_liga', 'soccer_germany_bundesliga',
    'soccer_italy_serie_a', 'soccer_france_ligue_one',
    'soccer_uefa_champs_league', 'soccer_uefa_europa_league',
    'soccer_netherlands_eredivisie', 'soccer_portugal_primeira_liga',
    'soccer_belgium_first_div', 'soccer_turkey_super_league',
    'soccer_efl_champ', 'soccer_germany_bundesliga2',
    'soccer_france_ligue_two', 'soccer_italy_serie_b',
]

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def collect_scores(days_from: int = 3) -> dict:
    """Collecte les scores des matchs terminés"""
    all_scores = {}
    
    for sport in SPORTS:
        try:
            response = requests.get(
                f"{BASE_URL}/sports/{sport}/scores/",
                params={
                    'apiKey': API_KEY,
                    'daysFrom': days_from,
                    'dateFormat': 'iso'
                },
                timeout=15
            )
            
            if response.status_code != 200:
                logger.warning(f"  {sport}: Erreur {response.status_code}")
                continue
            
            remaining = response.headers.get('x-requests-remaining', '?')
            matches = response.json()
            completed = [m for m in matches if m.get('completed')]
            
            for match in completed:
                scores = match.get('scores', [])
                home_score = None
                away_score = None
                
                for s in scores:
                    if s.get('name') == match.get('home_team'):
                        home_score = int(s.get('score', 0))
                    elif s.get('name') == match.get('away_team'):
                        away_score = int(s.get('score', 0))
                
                if home_score is not None and away_score is not None:
                    all_scores[match['id']] = {
                        'home_team': match['home_team'],
                        'away_team': match['away_team'],
                        'home_score': home_score,
                        'away_score': away_score,
                        'commence_time': match.get('commence_time'),
                        'sport': sport
                    }
            
            logger.info(f"  {sport}: {len(completed)} matchs terminés (remaining: {remaining})")
            
        except Exception as e:
            logger.error(f"  {sport}: {e}")
    
    logger.info(f"📊 Total scores collectés: {len(all_scores)}")
    return all_scores

def resolve_tracking_picks(conn, scores: dict) -> dict:
    """
    Résout les picks dans tracking_clv_picks
    Utilise les vraies colonnes de la table
    """
    cur = conn.cursor(cursor_factory=RealDictCursor)
    stats = {'resolved': 0, 'won': 0, 'lost': 0, 'errors': []}
    
    # Récupérer les picks non résolus dont le match est passé
    cur.execute("""
        SELECT id, match_id, home_team, away_team, market_type, 
               prediction, odds_taken, stake
        FROM tracking_clv_picks
        WHERE is_resolved = false
        AND commence_time < NOW()
    """)
    
    pending_picks = cur.fetchall()
    logger.info(f"📋 {len(pending_picks)} picks en attente de résolution")
    
    for pick in pending_picks:
        # Chercher le score correspondant par équipes
        score_data = None
        for sid, sdata in scores.items():
            if (sdata['home_team'] == pick['home_team'] and 
                sdata['away_team'] == pick['away_team']):
                score_data = sdata
                break
        
        if not score_data:
            continue
        
        market = pick['market_type']
        prediction = pick['prediction']
        home_score = score_data['home_score']
        away_score = score_data['away_score']
        total_goals = home_score + away_score
        
        is_winner = None
        
        try:
            # Déterminer si le pick est gagnant selon le marché
            if market in ['1x2', 'h2h', 'home', 'Home']:
                if prediction in ['1', 'home', 'Home']:
                    is_winner = (home_score > away_score)
                elif prediction in ['X', 'draw', 'Draw']:
                    is_winner = (home_score == away_score)
                elif prediction in ['2', 'away', 'Away']:
                    is_winner = (away_score > home_score)
                    
            elif market in ['btts', 'btts_yes', 'BTTS']:
                if prediction in ['yes', 'Yes', 'BTTS_Yes']:
                    is_winner = (home_score > 0 and away_score > 0)
                else:
                    is_winner = (home_score == 0 or away_score == 0)
                    
            elif market in ['over_25', 'over25', 'Over 2.5']:
                is_winner = (total_goals > 2.5)
            elif market in ['under_25', 'under25', 'Under 2.5']:
                is_winner = (total_goals < 2.5)
            elif market in ['over_15', 'over15', 'Over 1.5']:
                is_winner = (total_goals > 1.5)
            elif market in ['over_35', 'over35', 'Over 3.5']:
                is_winner = (total_goals > 3.5)
                
            elif market in ['dc_1x', 'double_chance_1x']:
                is_winner = (home_score >= away_score)
            elif market in ['dc_x2', 'double_chance_x2']:
                is_winner = (away_score >= home_score)
            elif market in ['dc_12', 'double_chance_12']:
                is_winner = (home_score != away_score)
            
            if is_winner is not None:
                # Calculer le profit/loss
                odds = float(pick['odds_taken']) if pick['odds_taken'] else 1.0
                stake = float(pick['stake']) if pick['stake'] else 1.0
                
                if is_winner:
                    profit_loss = stake * (odds - 1)
                else:
                    profit_loss = -stake
                
                # Mettre à jour le pick
                cur.execute("""
                    UPDATE tracking_clv_picks
                    SET is_resolved = true,
                        is_winner = %s,
                        score_home = %s,
                        score_away = %s,
                        profit_loss = %s,
                        resolved_at = NOW()
                    WHERE id = %s
                """, (is_winner, home_score, away_score, profit_loss, pick['id']))
                
                stats['resolved'] += 1
                if is_winner:
                    stats['won'] += 1
                else:
                    stats['lost'] += 1
                    
                logger.info(f"  {'✅' if is_winner else '❌'} {pick['home_team']} vs {pick['away_team']} ({market}) → {home_score}-{away_score}")
                    
        except Exception as e:
            stats['errors'].append(f"Pick {pick['id']}: {e}")
            logger.error(f"  Erreur pick {pick['id']}: {e}")
    
    conn.commit()
    cur.close()
    
    logger.info(f"\n📊 Résolution terminée:")
    logger.info(f"   ✅ Résolus: {stats['resolved']}")
    logger.info(f"   🏆 Gagnés: {stats['won']}")
    logger.info(f"   ❌ Perdus: {stats['lost']}")
    if stats['resolved'] > 0:
        win_rate = (stats['won'] / stats['resolved']) * 100
        logger.info(f"   📈 Win Rate: {win_rate:.1f}%")
    
    return stats

def analyze_performance(conn) -> dict:
    """Analyse les performances pour apprentissage"""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Stats par marché (30 derniers jours)
    cur.execute("""
        SELECT 
            market_type,
            COUNT(*) as total,
            SUM(CASE WHEN is_winner THEN 1 ELSE 0 END) as wins,
            ROUND(AVG(CASE WHEN is_winner THEN 1.0 ELSE 0.0 END) * 100, 1) as win_rate,
            ROUND(SUM(COALESCE(profit_loss, 0))::numeric, 2) as total_profit,
            ROUND(AVG(odds_taken)::numeric, 2) as avg_odds
        FROM tracking_clv_picks
        WHERE is_resolved = true
        AND resolved_at > NOW() - INTERVAL '30 days'
        GROUP BY market_type
        ORDER BY total_profit DESC
    """)
    market_stats = cur.fetchall()
    
    # Stats par Diamond Score
    cur.execute("""
        SELECT 
            CASE 
                WHEN diamond_score >= 90 THEN '90+ ELITE'
                WHEN diamond_score >= 80 THEN '80+ DIAMOND'
                WHEN diamond_score >= 70 THEN '70+ STRONG'
                WHEN diamond_score >= 60 THEN '60+ GOOD'
                ELSE '< 60'
            END as tier,
            COUNT(*) as total,
            ROUND(AVG(CASE WHEN is_winner THEN 1.0 ELSE 0.0 END) * 100, 1) as win_rate,
            ROUND(SUM(COALESCE(profit_loss, 0))::numeric, 2) as profit
        FROM tracking_clv_picks
        WHERE is_resolved = true
        AND diamond_score IS NOT NULL
        AND resolved_at > NOW() - INTERVAL '30 days'
        GROUP BY tier
        ORDER BY profit DESC
    """)
    tier_stats = cur.fetchall()
    
    # Dernières défaites pour analyse
    cur.execute("""
        SELECT home_team, away_team, market_type, prediction,
               odds_taken, diamond_score, score_home, score_away,
               resolved_at::date as date
        FROM tracking_clv_picks
        WHERE is_resolved = true AND is_winner = false
        AND resolved_at > NOW() - INTERVAL '7 days'
        ORDER BY resolved_at DESC
        LIMIT 10
    """)
    recent_losses = cur.fetchall()
    
    cur.close()
    
    # Afficher le rapport
    logger.info("\n" + "=" * 60)
    logger.info("📊 RAPPORT D'APPRENTISSAGE")
    logger.info("=" * 60)
    
    if market_stats:
        logger.info("\n�� PERFORMANCE PAR MARCHÉ (30 jours):")
        for m in market_stats:
            emoji = "✅" if float(m['total_profit'] or 0) > 0 else "❌"
            logger.info(f"  {emoji} {m['market_type']}: {m['win_rate']}% WR | {m['total_profit']}€ | {m['total']} picks")
    
    if tier_stats:
        logger.info("\n💎 PERFORMANCE PAR DIAMOND SCORE:")
        for t in tier_stats:
            emoji = "✅" if float(t['profit'] or 0) > 0 else "❌"
            logger.info(f"  {emoji} {t['tier']}: {t['win_rate']}% WR | {t['profit']}€ | {t['total']} picks")
    
    if recent_losses:
        logger.info(f"\n⚠️ DERNIÈRES DÉFAITES À ANALYSER:")
        for loss in recent_losses[:5]:
            logger.info(f"  • {loss['home_team']} vs {loss['away_team']}")
            logger.info(f"    {loss['market_type']}/{loss['prediction']} → Score: {loss['score_home']}-{loss['score_away']}")
    
    return {'market_stats': market_stats, 'tier_stats': tier_stats}

def main():
    if not API_KEY:
        logger.error("❌ ODDS_API_KEY manquante!")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("🎯 AUTO-RÉSOLUTION DES PICKS - Mon_PS")
    logger.info(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    logger.info("=" * 60)
    
    # 1. Collecter les scores
    logger.info("\n📥 COLLECTE DES SCORES...")
    scores = collect_scores(days_from=3)
    
    if not scores:
        logger.warning("⚠️ Aucun score collecté")
        return
    
    # 2. Résoudre les picks
    conn = get_db_connection()
    logger.info("\n🔄 RÉSOLUTION DES PICKS...")
    stats = resolve_tracking_picks(conn, scores)
    
    # 3. Analyser les performances
    if stats['resolved'] > 0:
        analyze_performance(conn)
    
    conn.close()
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ AUTO-RÉSOLUTION TERMINÉE")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
