#!/usr/bin/env python3
"""
🎯 CRON: Calcul du gap entre probabilités Reality Check et cotes marché
Compare nos probabilités avec les cotes Pinnacle pour identifier la value

Usage:
    python3 populate_market_reality_gap.py

Cron recommandé: 0 9 * * * (tous les jours à 9h)
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import logging

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/monps/market_reality_gap.log', mode='a')
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

def odds_to_prob(odds: float) -> float:
    """Convertit une cote en probabilité implicite"""
    return 100.0 / float(odds) if odds and odds > 0 else 0

def prob_to_fair_odds(prob: float) -> float:
    """Convertit une probabilité en cote fair"""
    return 100.0 / float(prob) if prob and prob > 0 else 0

def calculate_kelly(prob: float, odds: float) -> float:
    """Calcule le Kelly Criterion"""
    if not prob or not odds or float(odds) <= 1:
        return 0
    q = 1 - (prob / 100)
    p = prob / 100
    b = float(odds) - 1
    kelly = (b * p - q) / b
    return max(0, min(kelly * 100, 25))  # Cap à 25%

def populate_market_reality_gap():
    """Calcule et insère le gap market/reality"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Récupérer les matchs avec Reality Check et closing odds
        cursor.execute("""
            WITH closing_odds AS (
                SELECT DISTINCT ON (match_id)
                    match_id, home_odds, draw_odds, away_odds
                FROM odds_history
                WHERE bookmaker = 'pinnacle'
                ORDER BY match_id, collected_at DESC
            )
            SELECT 
                rcr.match_id, rcr.home_team, rcr.away_team, rcr.commence_time,
                rcr.home_tier, rcr.away_tier, rcr.reality_score,
                rcr.class_score, rcr.convergence_status,
                rcr.actual_result,
                co.home_odds, co.draw_odds, co.away_odds
            FROM reality_check_results rcr
            JOIN closing_odds co ON rcr.match_id = co.match_id
            WHERE rcr.reality_score IS NOT NULL
        """)
        
        matches = cursor.fetchall()
        logger.info(f"📊 {len(matches)} matchs avec Reality Check + odds à analyser")
        
        inserted = 0
        for match in matches:
            # Calculer probabilités reality-based (basées sur tier et score)
            tier_probs = {
                'S_vs_C': {'home': 75, 'draw': 15, 'away': 10},
                'S_vs_B': {'home': 65, 'draw': 20, 'away': 15},
                'S_vs_A': {'home': 55, 'draw': 25, 'away': 20},
                'A_vs_C': {'home': 65, 'draw': 20, 'away': 15},
                'A_vs_B': {'home': 55, 'draw': 25, 'away': 20},
                'A_vs_A': {'home': 45, 'draw': 25, 'away': 30},
                'B_vs_B': {'home': 45, 'draw': 28, 'away': 27},
                'DEFAULT': {'home': 45, 'draw': 27, 'away': 28}
            }
            
            key = f"{match['home_tier']}_vs_{match['away_tier']}"
            probs = tier_probs.get(key, tier_probs['DEFAULT'])
            
            # Ajuster avec reality_score
            reality_adj = (match['reality_score'] - 50) / 100
            probs['home'] = min(90, max(10, probs['home'] + reality_adj * 10))
            
            # Pour chaque outcome (home, draw, away)
            outcomes = [
                ('1X2', 'home', probs['home'], match['home_odds']),
                ('1X2', 'draw', probs['draw'], match['draw_odds']),
                ('1X2', 'away', probs['away'], match['away_odds'])
            ]
            
            for bet_type, selection, reality_prob, market_odds in outcomes:
                if not market_odds or float(market_odds) <= 1:
                    continue
                
                market_implied = odds_to_prob(market_odds)
                fair_odds = prob_to_fair_odds(reality_prob)
                edge = reality_prob - market_implied
                
                is_value = edge > 2  # >2% edge = value bet
                
                if edge > 10:
                    value_rating = 'EXCELLENT'
                elif edge > 5:
                    value_rating = 'GOOD'
                elif edge > 2:
                    value_rating = 'MARGINAL'
                else:
                    value_rating = 'NO_VALUE'
                
                kelly = calculate_kelly(reality_prob, market_odds)
                
                # Déterminer le résultat
                bet_outcome = None
                profit_loss = None
                if match['actual_result']:
                    if match['actual_result'] == selection:
                        bet_outcome = 'WIN'
                        profit_loss = (market_odds - 1) * 10  # Base 10 unités
                    else:
                        bet_outcome = 'LOSS'
                        profit_loss = -10
                
                # Vérifier si existe déjà
                cursor.execute("""
                    SELECT id FROM market_reality_gap 
                    WHERE match_id = %s AND bet_type = %s AND bet_selection = %s
                """, (match['match_id'], bet_type, selection))
                
                if cursor.fetchone():
                    continue  # Skip si existe
                
                cursor.execute("""
                    INSERT INTO market_reality_gap (
                        match_id, home_team, away_team, commence_time,
                        bet_type, bet_selection,
                        reality_probability, reality_fair_odds, reality_confidence,
                        market_odds_closing, market_implied_prob, bookmaker,
                        value_edge_percent, is_value_bet, value_rating,
                        kelly_criterion_stake, kelly_fraction_used, suggested_stake_units,
                        bet_outcome, profit_loss,
                        reality_check_score, convergence_status,
                        created_at
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s,
                        %s, %s,
                        NOW()
                    )
                """, (
                    match['match_id'], match['home_team'], match['away_team'], match['commence_time'],
                    bet_type, selection,
                    reality_prob, fair_odds, match['reality_score'],
                    market_odds, market_implied, 'pinnacle',
                    edge, is_value, value_rating,
                    kelly, kelly / 4, kelly / 4,  # Fraction Kelly = 1/4
                    bet_outcome, profit_loss,
                    match['reality_score'], match['convergence_status']
                ))
                inserted += 1
        
        conn.commit()
        logger.info(f"✅ {inserted} entrées market_reality_gap créées")
        
        # Stats
        cursor.execute("""
            SELECT 
                value_rating,
                COUNT(*) as total,
                SUM(CASE WHEN bet_outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                ROUND(AVG(value_edge_percent)::numeric, 2) as avg_edge
            FROM market_reality_gap
            WHERE bet_outcome IS NOT NULL
            GROUP BY value_rating
            ORDER BY avg_edge DESC
        """)
        stats = cursor.fetchall()
        for s in stats:
            logger.info(f"   {s['value_rating']}: {s['total']} bets, {s['wins']} wins, avg edge {s['avg_edge']}%")
        
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    logger.info("🚀 Démarrage calcul Market Reality Gap")
    populate_market_reality_gap()
    logger.info("✅ Terminé")
