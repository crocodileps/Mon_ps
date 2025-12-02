#!/usr/bin/env python3
"""
🔥 MARKET STEAM TRACKER V2 - QUANT EDITION
==========================================
Améliorations:
- Calcul en probabilité implicite (pas en % cote)
- Distinction LATE/EARLY steam
- Filtre ligues majeures (liquidité)
- Score normalisé sur 100
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger('SteamTrackerV2')

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'monps_postgres'),
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
}

# Ligues avec liquidité suffisante
MAJOR_LEAGUES = [
    'soccer_epl', 'soccer_spain_la_liga', 'soccer_germany_bundesliga',
    'soccer_italy_serie_a', 'soccer_france_ligue_one',
    'soccer_uefa_champs_league', 'soccer_uefa_europa_league',
    'soccer_netherlands_eredivisie', 'soccer_portugal_primeira_liga'
]

def calculate_steam_score(opening_odds, current_odds):
    """
    Calcule la force du mouvement en points de probabilité.
    Retourne un score de -100 à +100.
    +100 = mouvement massif vers cette équipe (STEAM)
    -100 = mouvement massif contre cette équipe (DRIFT)
    """
    if not opening_odds or not current_odds or opening_odds <= 1 or current_odds <= 1:
        return 0
    
    prob_open = 1 / float(opening_odds)
    prob_curr = 1 / float(current_odds)
    
    # Différence de probabilité (ex: 50% -> 55% = +0.05)
    diff = prob_curr - prob_open
    
    # Score normalisé (100 points = changement de 10% de proba = très significatif)
    steam_score = diff * 1000
    
    return round(steam_score, 1)

def get_steam_type(hours_to_match):
    """Détermine le type de steam selon le timing"""
    if hours_to_match < 2:
        return "🔥 LATE STEAM", "Syndicate Money - TRÈS FIABLE"
    elif hours_to_match < 6:
        return "📈 PRE-MATCH", "Confirmation du marché"
    elif hours_to_match < 24:
        return "ℹ️ MARKET ADJ", "Ajustement normal"
    else:
        return "📰 EARLY STEAM", "News/Blessure probable"

def get_steam_signals_v2():
    """Calcule les signaux Steam V2 avec probabilités"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        WITH odds_evolution AS (
            SELECT 
                match_id,
                home_team,
                away_team,
                commence_time,
                sport,
                FIRST_VALUE(home_odds) OVER (PARTITION BY match_id ORDER BY collected_at) as opening_home,
                FIRST_VALUE(away_odds) OVER (PARTITION BY match_id ORDER BY collected_at) as opening_away,
                LAST_VALUE(home_odds) OVER (PARTITION BY match_id ORDER BY collected_at 
                    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as current_home,
                LAST_VALUE(away_odds) OVER (PARTITION BY match_id ORDER BY collected_at 
                    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as current_away,
                MIN(collected_at) OVER (PARTITION BY match_id) as first_seen,
                MAX(collected_at) OVER (PARTITION BY match_id) as last_update,
                COUNT(*) OVER (PARTITION BY match_id) as snapshot_count
            FROM odds_history
            WHERE bookmaker = 'Pinnacle'
              AND commence_time > NOW()
              AND sport IN %s
        )
        SELECT DISTINCT
            match_id,
            home_team,
            away_team,
            commence_time,
            sport,
            opening_home,
            current_home,
            opening_away,
            current_away,
            first_seen,
            last_update,
            snapshot_count
        FROM odds_evolution
        WHERE opening_home IS NOT NULL
          AND snapshot_count >= 3  -- Au moins 3 snapshots pour fiabilité
        ORDER BY commence_time
    """, (tuple(MAJOR_LEAGUES),))
    
    matches = cur.fetchall()
    signals = []
    
    for m in matches:
        # Calculer Steam Score (en points de proba)
        home_steam = calculate_steam_score(m['opening_home'], m['current_home'])
        away_steam = calculate_steam_score(m['opening_away'], m['current_away'])
        
        # Temps avant le match
        hours_to_match = (m['commence_time'] - datetime.now()).total_seconds() / 3600
        steam_type, steam_desc = get_steam_type(hours_to_match)
        
        # Seuil: 3 points de proba = significatif (3%)
        THRESHOLD = 30  # 30 = 3% de proba
        
        signal = {
            'match_id': m['match_id'],
            'match': f"{m['home_team']} vs {m['away_team']}",
            'commence_time': m['commence_time'],
            'hours_to_match': round(hours_to_match, 1),
            'steam_type': steam_type,
            'steam_desc': steam_desc,
            'home_steam_score': home_steam,
            'away_steam_score': away_steam,
            'snapshots': m['snapshot_count'],
            'alerts': []
        }
        
        # Analyser HOME
        if home_steam > THRESHOLD:
            prob_change = home_steam / 10
            signal['alerts'].append({
                'side': 'HOME',
                'action': 'STEAM',
                'score': home_steam,
                'message': f"🔥 STEAM HOME (+{prob_change:.1f}% proba): {m['opening_home']} → {m['current_home']}"
            })
        elif home_steam < -THRESHOLD:
            prob_change = abs(home_steam) / 10
            signal['alerts'].append({
                'side': 'HOME',
                'action': 'DRIFT',
                'score': home_steam,
                'message': f"⚠️ DRIFT HOME (-{prob_change:.1f}% proba): {m['opening_home']} → {m['current_home']}"
            })
        
        # Analyser AWAY
        if away_steam > THRESHOLD:
            prob_change = away_steam / 10
            signal['alerts'].append({
                'side': 'AWAY',
                'action': 'STEAM',
                'score': away_steam,
                'message': f"🔥 STEAM AWAY (+{prob_change:.1f}% proba): {m['opening_away']} → {m['current_away']}"
            })
        elif away_steam < -THRESHOLD:
            prob_change = abs(away_steam) / 10
            signal['alerts'].append({
                'side': 'AWAY',
                'action': 'DRIFT',
                'score': away_steam,
                'message': f"⚠️ DRIFT AWAY (-{prob_change:.1f}% proba): {m['opening_away']} → {m['current_away']}"
            })
        
        if signal['alerts']:
            signals.append(signal)
    
    cur.close()
    conn.close()
    
    # Trier par score de steam le plus fort
    signals.sort(key=lambda x: max(abs(a['score']) for a in x['alerts']), reverse=True)
    
    return signals

def update_picks_steam_score():
    """Met à jour le steam score dans tracking_clv_picks (numeric)"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Calculer le steam score pour chaque match
    cur.execute("""
        WITH odds_calc AS (
            SELECT 
                match_id,
                FIRST_VALUE(home_odds) OVER (PARTITION BY match_id ORDER BY collected_at) as opening,
                LAST_VALUE(home_odds) OVER (PARTITION BY match_id ORDER BY collected_at 
                    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as closing
            FROM odds_history
            WHERE bookmaker = 'Pinnacle'
        ),
        steam_scores AS (
            SELECT DISTINCT
                match_id,
                opening,
                closing,
                CASE 
                    WHEN opening > 1 AND closing > 1 
                    THEN ROUND(((1.0/closing - 1.0/opening) * 1000)::numeric, 1)
                    ELSE 0
                END as steam_score
            FROM odds_calc
            WHERE opening IS NOT NULL
        )
        UPDATE tracking_clv_picks t
        SET odds_movement = ss.steam_score
        FROM steam_scores ss
        WHERE t.match_id = ss.match_id
          AND (t.odds_movement IS NULL OR t.odds_movement = 0)
    """)
    
    updated = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    
    return updated

def analyze_steam_performance():
    """Analyse la corrélation Steam vs Win Rate"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT 
            CASE 
                WHEN odds_movement > 30 THEN 'STRONG STEAM (>3%)'
                WHEN odds_movement > 15 THEN 'SLIGHT STEAM (1.5-3%)'
                WHEN odds_movement < -30 THEN 'STRONG DRIFT (<-3%)'
                WHEN odds_movement < -15 THEN 'SLIGHT DRIFT (-1.5 to -3%)'
                ELSE 'STABLE'
            END as steam_category,
            COUNT(*) as picks,
            SUM(CASE WHEN is_winner THEN 1 ELSE 0 END) as wins,
            ROUND(100.0 * SUM(CASE WHEN is_winner THEN 1 ELSE 0 END) / COUNT(*), 1) as win_rate,
            ROUND(SUM(COALESCE(profit_loss, 0))::numeric, 2) as profit
        FROM tracking_clv_picks
        WHERE is_resolved = true
          AND odds_movement IS NOT NULL
          AND odds_movement != 0
        GROUP BY steam_category
        ORDER BY profit DESC
    """)
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return results

def main():
    logger.info("=" * 70)
    logger.info("🔥 MARKET STEAM TRACKER V2 - QUANT EDITION")
    logger.info("=" * 70)
    
    # 1. Afficher les signaux actuels
    signals = get_steam_signals_v2()
    
    logger.info(f"\n📊 {len(signals)} matchs avec mouvements significatifs (≥3% proba):\n")
    
    for s in signals[:12]:
        logger.info(f"⚽ {s['match']} ({s['hours_to_match']}h avant)")
        logger.info(f"   {s['steam_type']} - {s['steam_desc']}")
        logger.info(f"   📸 {s['snapshots']} snapshots analysés")
        for alert in s['alerts']:
            logger.info(f"   {alert['message']}")
        logger.info("")
    
    # 2. Mettre à jour les picks historiques
    logger.info(f"{'='*70}")
    logger.info("📝 Mise à jour des picks historiques (steam score numérique)...")
    updated = update_picks_steam_score()
    logger.info(f"✅ {updated} picks mis à jour")
    
    # 3. Analyser la performance Steam vs Win Rate
    logger.info(f"\n{'='*70}")
    logger.info("📈 ANALYSE PERFORMANCE STEAM:")
    perf = analyze_steam_performance()
    
    if perf:
        for p in perf:
            emoji = "✅" if float(p['profit'] or 0) > 0 else "❌"
            logger.info(f"   {emoji} {p['steam_category']}: {p['win_rate']}% WR | {p['profit']}€ | {p['picks']} picks")
    else:
        logger.info("   Pas encore assez de données avec steam score")
    
    logger.info("=" * 70)

if __name__ == "__main__":
    main()
