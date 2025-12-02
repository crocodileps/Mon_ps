#!/usr/bin/env python3
"""
🛡️ STEAM VALIDATOR - Utilise le Steam comme FILTRE, pas comme déclencheur

LOGIQUE:
- Notre modèle dit "Parier HOME" + Steam sur HOME = ✅ CONFIRMÉ (+10 confiance)
- Notre modèle dit "Parier HOME" + Drift sur HOME = 🛑 BLOQUÉ (marché sait quelque chose)
- Notre modèle dit "Parier HOME" + Steam AWAY = ⚠️ ATTENTION (-30 confiance)

C'est un FILTRE DE SÉCURITÉ, pas un générateur de paris.
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger('SteamValidator')

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'monps_postgres'),
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
}

# Seuils en points de probabilité (30 = 3%)
STEAM_THRESHOLD = 30   # Mouvement significatif
DRIFT_DANGER = -30     # Signal d'alarme

def get_steam_score(match_id: str) -> dict:
    """Récupère le steam score pour un match"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        WITH odds_calc AS (
            SELECT 
                FIRST_VALUE(home_odds) OVER (PARTITION BY match_id ORDER BY collected_at) as open_home,
                FIRST_VALUE(away_odds) OVER (PARTITION BY match_id ORDER BY collected_at) as open_away,
                LAST_VALUE(home_odds) OVER (PARTITION BY match_id ORDER BY collected_at 
                    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as curr_home,
                LAST_VALUE(away_odds) OVER (PARTITION BY match_id ORDER BY collected_at 
                    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as curr_away
            FROM odds_history
            WHERE match_id = %s AND bookmaker = 'Pinnacle'
        )
        SELECT DISTINCT
            open_home, curr_home, open_away, curr_away,
            CASE WHEN open_home > 1 AND curr_home > 1 
                THEN ROUND(((1.0/curr_home - 1.0/open_home) * 1000)::numeric, 1)
                ELSE 0 END as home_steam,
            CASE WHEN open_away > 1 AND curr_away > 1 
                THEN ROUND(((1.0/curr_away - 1.0/open_away) * 1000)::numeric, 1)
                ELSE 0 END as away_steam
        FROM odds_calc
        WHERE open_home IS NOT NULL
        LIMIT 1
    """, (match_id,))
    
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    if not result:
        return {'home_steam': 0, 'away_steam': 0, 'status': 'NO_DATA'}
    
    return {
        'home_steam': float(result['home_steam'] or 0),
        'away_steam': float(result['away_steam'] or 0),
        'open_home': float(result['open_home'] or 0),
        'curr_home': float(result['curr_home'] or 0),
        'open_away': float(result['open_away'] or 0),
        'curr_away': float(result['curr_away'] or 0),
        'status': 'OK'
    }

def validate_prediction(match_id: str, prediction: str, model_confidence: int) -> dict:
    """
    Valide une prédiction avec le Steam Tracker.
    
    Args:
        match_id: ID du match
        prediction: 'home', 'away', 'draw', 'btts_yes', 'over_25', etc.
        model_confidence: Score de confiance du modèle (0-100)
    
    Returns:
        dict avec: validated, adjusted_confidence, reason, action
    """
    steam = get_steam_score(match_id)
    
    if steam['status'] == 'NO_DATA':
        return {
            'validated': True,
            'adjusted_confidence': model_confidence,
            'reason': 'Pas de données Steam',
            'action': 'PROCEED',
            'steam_data': steam
        }
    
    home_steam = steam['home_steam']
    away_steam = steam['away_steam']
    
    # Déterminer la direction du pari
    if prediction in ['home', '1', 'dc_1x']:
        our_steam = home_steam
        opposite_steam = away_steam
        our_side = 'HOME'
    elif prediction in ['away', '2', 'dc_x2']:
        our_steam = away_steam
        opposite_steam = home_steam
        our_side = 'AWAY'
    elif prediction == 'draw':
        # Pour le nul, on vérifie si les deux équipes drift (match serré)
        our_steam = -(abs(home_steam) + abs(away_steam)) / 2  # Moyenne négative = incertitude
        opposite_steam = 0
        our_side = 'DRAW'
    else:
        # Pour btts, over/under, on ne filtre pas avec steam (c'est 1X2 only)
        return {
            'validated': True,
            'adjusted_confidence': model_confidence,
            'reason': 'Marché non-1X2 - Steam non applicable',
            'action': 'PROCEED',
            'steam_data': steam
        }
    
    # === LOGIQUE DE VALIDATION ===
    
    # CAS 1: Notre pari + Steam dans MÊME direction = CONFIRMÉ
    if our_steam > STEAM_THRESHOLD:
        return {
            'validated': True,
            'adjusted_confidence': min(100, model_confidence + 10),
            'reason': f'✅ CONFIRMÉ: Marché steam {our_side} (+{our_steam/10:.1f}% proba)',
            'action': 'PROCEED_BOOSTED',
            'steam_data': steam
        }
    
    # CAS 2: Notre pari + DRIFT sur notre côté = DANGER !
    if our_steam < DRIFT_DANGER:
        return {
            'validated': False,
            'adjusted_confidence': max(0, model_confidence - 40),
            'reason': f'🛑 BLOQUÉ: Marché drift {our_side} ({our_steam/10:.1f}% proba) - Info cachée probable',
            'action': 'BLOCK',
            'steam_data': steam
        }
    
    # CAS 3: Steam sur l'OPPOSÉ = ATTENTION
    if opposite_steam > STEAM_THRESHOLD:
        return {
            'validated': True,
            'adjusted_confidence': max(0, model_confidence - 20),
            'reason': f'⚠️ ATTENTION: Marché steam OPPOSÉ (+{opposite_steam/10:.1f}% proba)',
            'action': 'PROCEED_CAUTIOUS',
            'steam_data': steam
        }
    
    # CAS 4: Marché stable = Normal
    return {
        'validated': True,
        'adjusted_confidence': model_confidence,
        'reason': f'📊 STABLE: Pas de mouvement significatif (Home:{home_steam/10:.1f}%, Away:{away_steam/10:.1f}%)',
        'action': 'PROCEED',
        'steam_data': steam
    }

def analyze_historical_validation():
    """Analyse rétroactive: qu'aurions-nous gagné avec ce filtre?"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Simuler le filtre sur les picks passés
    cur.execute("""
        WITH pick_analysis AS (
            SELECT 
                t.id,
                t.market_type,
                t.prediction,
                t.is_winner,
                t.profit_loss,
                t.odds_movement as steam_score,
                CASE 
                    WHEN t.market_type IN ('home', '1x2') AND t.prediction IN ('home', '1') THEN t.odds_movement
                    WHEN t.market_type IN ('away') AND t.prediction IN ('away', '2') THEN t.odds_movement
                    ELSE 0
                END as relevant_steam
            FROM tracking_clv_picks t
            WHERE t.is_resolved = true
              AND t.odds_movement IS NOT NULL
              AND t.market_type IN ('home', 'away', '1x2')
        )
        SELECT 
            CASE 
                WHEN relevant_steam > 30 THEN 'WOULD_BOOST (+10)'
                WHEN relevant_steam < -30 THEN 'WOULD_BLOCK'
                WHEN relevant_steam < -15 THEN 'WOULD_REDUCE (-20)'
                ELSE 'NO_CHANGE'
            END as filter_action,
            COUNT(*) as picks,
            SUM(CASE WHEN is_winner THEN 1 ELSE 0 END) as wins,
            ROUND(100.0 * SUM(CASE WHEN is_winner THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) as win_rate,
            ROUND(SUM(COALESCE(profit_loss, 0))::numeric, 2) as profit
        FROM pick_analysis
        GROUP BY filter_action
        ORDER BY profit DESC
    """)
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return results

def main():
    logger.info("=" * 70)
    logger.info("🛡️ STEAM VALIDATOR - Analyse rétroactive")
    logger.info("=" * 70)
    
    # Analyser ce qu'on aurait gagné avec le filtre
    analysis = analyze_historical_validation()
    
    logger.info("\n📊 SIMULATION DU FILTRE SUR L'HISTORIQUE:\n")
    
    total_saved = 0
    blocked_loss = 0
    
    for a in analysis:
        emoji = "✅" if float(a['profit'] or 0) > 0 else "❌"
        logger.info(f"   {emoji} {a['filter_action']}: {a['win_rate']}% WR | {a['profit']}€ | {a['picks']} picks")
        
        if a['filter_action'] == 'WOULD_BLOCK':
            blocked_loss = float(a['profit'] or 0)
    
    if blocked_loss < 0:
        logger.info(f"\n   💰 EN BLOQUANT CES PARIS: On aurait évité {abs(blocked_loss):.2f}€ de pertes!")
    
    logger.info("\n" + "=" * 70)
    logger.info("🎯 RECOMMANDATION:")
    logger.info("   Intégrer validate_prediction() dans Orchestrator/Ferrari")
    logger.info("   pour BLOQUER les paris où le marché drift contre nous.")
    logger.info("=" * 70)

if __name__ == "__main__":
    main()
