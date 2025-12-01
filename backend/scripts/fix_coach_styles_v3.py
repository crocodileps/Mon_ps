#!/usr/bin/env python3
"""
🔧 FIX COACH STYLES V3 - Classification optimisée (seuils expert)
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

def classify_style(avg_gf: float, avg_ga: float) -> str:
    """Classification OPTIMISÉE avec seuils expert"""
    
    # GARDE-FOU 1: Équipes en difficulté (marque peu, encaisse beaucoup)
    if avg_gf < 1.0 and avg_ga > 1.4:
        return 'struggling'
    
    # GARDE-FOU 2: Équipes faibles offensivement mais solides
    if avg_gf < 1.05 and avg_ga <= 1.3:
        return 'defensive_weak'
    
    # Top tier: dominants offensifs
    if avg_gf >= 1.9 and avg_ga <= 1.1:
        return 'dominant_offensive'
    
    # Offensif mais vulnérable (BTTS/Over candidates) - SEUIL AJUSTÉ
    if avg_gf >= 1.6 and avg_ga >= 1.25:
        return 'attacking_vulnerable'
    
    # Offensif équilibré
    if avg_gf >= 1.5:
        return 'offensive'
    
    # Ultra défensif
    if avg_ga <= 0.85:
        return 'ultra_defensive'
    
    # Défensif standard
    if avg_ga <= 1.15:
        return 'defensive'
    
    return 'balanced'


def fix_all_styles():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT coach_name, current_team, avg_goals_per_match, avg_goals_conceded_per_match, tactical_style
        FROM coach_intelligence WHERE avg_goals_per_match IS NOT NULL
    """)
    
    coaches = cur.fetchall()
    logger.info(f"🔧 Reclassifying {len(coaches)} coaches with V3 thresholds")
    
    changes = []
    stats = {}

    for coach in coaches:
        gf = float(coach['avg_goals_per_match'])
        ga = float(coach['avg_goals_conceded_per_match'])
        old_style = coach['tactical_style']
        new_style = classify_style(gf, ga)
        stats[new_style] = stats.get(new_style, 0) + 1
        
        if new_style != old_style:
            cur.execute("""
                UPDATE coach_intelligence SET tactical_style = %s
                WHERE coach_name = %s AND current_team = %s
            """, (new_style, coach['coach_name'], coach['current_team']))
            changes.append({'coach': coach['coach_name'], 'team': coach['current_team'], 
                           'gf': gf, 'ga': ga, 'old': old_style, 'new': new_style})
    
    conn.commit()
    
    logger.info(f"\n📊 CHANGEMENTS ({len(changes)}):")
    for c in changes:
        logger.info(f"  {c['coach']} ({c['team']}): {c['old']} -> {c['new']} [GF {c['gf']} | GA {c['ga']}]")
    
    logger.info("\n📊 DISTRIBUTION FINALE:")
    for style, count in sorted(stats.items(), key=lambda item: item[1], reverse=True):
        logger.info(f"  {style}: {count}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    logger.info("🔧 COACH STYLES V3 - Seuils Expert")
    logger.info("="*60)
    fix_all_styles()
