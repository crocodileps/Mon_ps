#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
🧬 MICROSTRATEGY DNA REFRESHER V1.0
   Script Cron Nocturne - Exécution: 03h00 chaque nuit
   
   Mode: HYBRIDE (stocké + rafraîchi périodiquement)
   Standard: Hedge Fund Grade
═══════════════════════════════════════════════════════════════════════════════
"""

import json
import asyncio
import asyncpg
from datetime import datetime
import os
import sys
import logging

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/Mon_ps/logs/microstrategy_refresh.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DB_CONFIG = {
    'host': 'localhost',
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}

OUTPUT_PATH = '/home/Mon_ps/data/quantum_v2/microstrategy_dna.json'
BACKUP_PATH = '/home/Mon_ps/data/quantum_v2/microstrategy_dna_backup.json'

# Classification adversaires (5 grands championnats)
TOP_TEAMS = [
    # Premier League
    'manchester city', 'arsenal', 'chelsea', 'manchester united', 'tottenham', 'newcastle', 'liverpool',
    # La Liga  
    'real madrid', 'barcelona', 'atletico madrid',
    # Bundesliga
    'bayern munich', 'borussia dortmund', 'bayer leverkusen',
    # Serie A
    'inter', 'milan', 'juventus', 'napoli',
    # Ligue 1
    'paris saint-germain', 'psg', 'marseille', 'monaco'
]

# ═══════════════════════════════════════════════════════════════════════════════
# DÉFINITION DES 126 MARCHÉS
# ═══════════════════════════════════════════════════════════════════════════════

MARKETS_DEFINITION = {
    # TOTAL GOALS (12)
    'total_over_0.5': {'baseline': 0.85, 'calc': lambda m: m['total_goals'] >= 1, 'category': 'TOTAL_GOALS'},
    'total_over_1.5': {'baseline': 0.70, 'calc': lambda m: m['total_goals'] >= 2, 'category': 'TOTAL_GOALS'},
    'total_over_2.5': {'baseline': 0.50, 'calc': lambda m: m['total_goals'] >= 3, 'category': 'TOTAL_GOALS'},
    'total_over_3.5': {'baseline': 0.30, 'calc': lambda m: m['total_goals'] >= 4, 'category': 'TOTAL_GOALS'},
    'total_over_4.5': {'baseline': 0.15, 'calc': lambda m: m['total_goals'] >= 5, 'category': 'TOTAL_GOALS'},
    'total_over_5.5': {'baseline': 0.07, 'calc': lambda m: m['total_goals'] >= 6, 'category': 'TOTAL_GOALS'},
    'total_under_1.5': {'baseline': 0.30, 'calc': lambda m: m['total_goals'] <= 1, 'category': 'TOTAL_GOALS'},
    'total_under_2.5': {'baseline': 0.50, 'calc': lambda m: m['total_goals'] <= 2, 'category': 'TOTAL_GOALS'},
    'total_under_3.5': {'baseline': 0.70, 'calc': lambda m: m['total_goals'] <= 3, 'category': 'TOTAL_GOALS'},
    'total_under_4.5': {'baseline': 0.85, 'calc': lambda m: m['total_goals'] <= 4, 'category': 'TOTAL_GOALS'},
    'total_under_5.5': {'baseline': 0.93, 'calc': lambda m: m['total_goals'] <= 5, 'category': 'TOTAL_GOALS'},
    'total_under_6.5': {'baseline': 0.97, 'calc': lambda m: m['total_goals'] <= 6, 'category': 'TOTAL_GOALS'},
    
    # TEAM GOALS (8)
    'team_over_0.5': {'baseline': 0.75, 'calc': lambda m: m['team_goals'] >= 1, 'category': 'TEAM_GOALS'},
    'team_over_1.5': {'baseline': 0.50, 'calc': lambda m: m['team_goals'] >= 2, 'category': 'TEAM_GOALS'},
    'team_over_2.5': {'baseline': 0.25, 'calc': lambda m: m['team_goals'] >= 3, 'category': 'TEAM_GOALS'},
    'team_over_3.5': {'baseline': 0.10, 'calc': lambda m: m['team_goals'] >= 4, 'category': 'TEAM_GOALS'},
    'team_exact_0': {'baseline': 0.25, 'calc': lambda m: m['team_goals'] == 0, 'category': 'TEAM_GOALS'},
    'team_exact_1': {'baseline': 0.35, 'calc': lambda m: m['team_goals'] == 1, 'category': 'TEAM_GOALS'},
    'team_exact_2': {'baseline': 0.25, 'calc': lambda m: m['team_goals'] == 2, 'category': 'TEAM_GOALS'},
    'team_exact_3plus': {'baseline': 0.15, 'calc': lambda m: m['team_goals'] >= 3, 'category': 'TEAM_GOALS'},
    
    # OPPONENT GOALS (6)
    'opp_over_0.5': {'baseline': 0.70, 'calc': lambda m: m['opp_goals'] >= 1, 'category': 'OPP_GOALS'},
    'opp_over_1.5': {'baseline': 0.40, 'calc': lambda m: m['opp_goals'] >= 2, 'category': 'OPP_GOALS'},
    'opp_over_2.5': {'baseline': 0.20, 'calc': lambda m: m['opp_goals'] >= 3, 'category': 'OPP_GOALS'},
    'opp_exact_0': {'baseline': 0.30, 'calc': lambda m: m['opp_goals'] == 0, 'category': 'OPP_GOALS'},
    'opp_exact_1': {'baseline': 0.35, 'calc': lambda m: m['opp_goals'] == 1, 'category': 'OPP_GOALS'},
    'opp_exact_2plus': {'baseline': 0.35, 'calc': lambda m: m['opp_goals'] >= 2, 'category': 'OPP_GOALS'},
    
    # HALF GOALS (9)
    '1h_over_0.5': {'baseline': 0.60, 'calc': lambda m: m['ht_total'] >= 1, 'category': 'HALF_GOALS'},
    '1h_over_1.5': {'baseline': 0.35, 'calc': lambda m: m['ht_total'] >= 2, 'category': 'HALF_GOALS'},
    '1h_over_2.5': {'baseline': 0.15, 'calc': lambda m: m['ht_total'] >= 3, 'category': 'HALF_GOALS'},
    '2h_over_0.5': {'baseline': 0.70, 'calc': lambda m: m['sh_total'] >= 1, 'category': 'HALF_GOALS'},
    '2h_over_1.5': {'baseline': 0.45, 'calc': lambda m: m['sh_total'] >= 2, 'category': 'HALF_GOALS'},
    '2h_over_2.5': {'baseline': 0.20, 'calc': lambda m: m['sh_total'] >= 3, 'category': 'HALF_GOALS'},
    'most_goals_1h': {'baseline': 0.35, 'calc': lambda m: m['ht_total'] > m['sh_total'], 'category': 'HALF_GOALS'},
    'most_goals_2h': {'baseline': 0.45, 'calc': lambda m: m['sh_total'] > m['ht_total'], 'category': 'HALF_GOALS'},
    'equal_goals_halves': {'baseline': 0.20, 'calc': lambda m: m['ht_total'] == m['sh_total'], 'category': 'HALF_GOALS'},
    
    # TEAM BY HALF (4)
    'team_1h_over_0.5': {'baseline': 0.50, 'calc': lambda m: m['team_ht'] >= 1, 'category': 'TEAM_HALF'},
    'team_1h_over_1.5': {'baseline': 0.20, 'calc': lambda m: m['team_ht'] >= 2, 'category': 'TEAM_HALF'},
    'team_2h_over_0.5': {'baseline': 0.55, 'calc': lambda m: m['team_sh'] >= 1, 'category': 'TEAM_HALF'},
    'team_2h_over_1.5': {'baseline': 0.25, 'calc': lambda m: m['team_sh'] >= 2, 'category': 'TEAM_HALF'},
    
    # OPP BY HALF (4)
    'opp_1h_over_0.5': {'baseline': 0.45, 'calc': lambda m: m['opp_ht'] >= 1, 'category': 'OPP_HALF'},
    'opp_1h_over_1.5': {'baseline': 0.15, 'calc': lambda m: m['opp_ht'] >= 2, 'category': 'OPP_HALF'},
    'opp_2h_over_0.5': {'baseline': 0.50, 'calc': lambda m: m['opp_sh'] >= 1, 'category': 'OPP_HALF'},
    'opp_2h_over_1.5': {'baseline': 0.20, 'calc': lambda m: m['opp_sh'] >= 2, 'category': 'OPP_HALF'},
    
    # BTTS (8)
    'btts_yes': {'baseline': 0.55, 'calc': lambda m: m['team_goals'] >= 1 and m['opp_goals'] >= 1, 'category': 'BTTS'},
    'btts_no': {'baseline': 0.45, 'calc': lambda m: m['team_goals'] == 0 or m['opp_goals'] == 0, 'category': 'BTTS'},
    'btts_over_2.5': {'baseline': 0.40, 'calc': lambda m: m['team_goals'] >= 1 and m['opp_goals'] >= 1 and m['total_goals'] >= 3, 'category': 'BTTS'},
    'btts_under_3.5': {'baseline': 0.45, 'calc': lambda m: m['team_goals'] >= 1 and m['opp_goals'] >= 1 and m['total_goals'] <= 3, 'category': 'BTTS'},
    'btts_1h': {'baseline': 0.25, 'calc': lambda m: m['team_ht'] >= 1 and m['opp_ht'] >= 1, 'category': 'BTTS'},
    'btts_2h': {'baseline': 0.35, 'calc': lambda m: m['team_sh'] >= 1 and m['opp_sh'] >= 1, 'category': 'BTTS'},
    'btts_both_halves': {'baseline': 0.10, 'calc': lambda m: (m['team_ht'] >= 1 and m['opp_ht'] >= 1) and (m['team_sh'] >= 1 and m['opp_sh'] >= 1), 'category': 'BTTS'},
    'btts_either_half': {'baseline': 0.50, 'calc': lambda m: (m['team_ht'] >= 1 and m['opp_ht'] >= 1) or (m['team_sh'] >= 1 and m['opp_sh'] >= 1), 'category': 'BTTS'},
    
    # RESULT (3)
    'team_win': {'baseline': 0.45, 'calc': lambda m: m['team_goals'] > m['opp_goals'], 'category': 'RESULT'},
    'draw': {'baseline': 0.25, 'calc': lambda m: m['team_goals'] == m['opp_goals'], 'category': 'RESULT'},
    'opp_win': {'baseline': 0.30, 'calc': lambda m: m['team_goals'] < m['opp_goals'], 'category': 'RESULT'},
    
    # DOUBLE CHANCE (3)
    'team_or_draw': {'baseline': 0.70, 'calc': lambda m: m['team_goals'] >= m['opp_goals'], 'category': 'DOUBLE_CHANCE'},
    'opp_or_draw': {'baseline': 0.55, 'calc': lambda m: m['opp_goals'] >= m['team_goals'], 'category': 'DOUBLE_CHANCE'},
    'team_or_opp': {'baseline': 0.75, 'calc': lambda m: m['team_goals'] != m['opp_goals'], 'category': 'DOUBLE_CHANCE'},
    
    # ASIAN HANDICAP (8)
    'team_-2.0': {'baseline': 0.15, 'calc': lambda m: m['team_goals'] - m['opp_goals'] > 2, 'category': 'ASIAN_HANDICAP'},
    'team_-1.5': {'baseline': 0.25, 'calc': lambda m: m['team_goals'] - m['opp_goals'] >= 2, 'category': 'ASIAN_HANDICAP'},
    'team_-1.0': {'baseline': 0.35, 'calc': lambda m: m['team_goals'] - m['opp_goals'] > 1, 'category': 'ASIAN_HANDICAP'},
    'team_-0.5': {'baseline': 0.45, 'calc': lambda m: m['team_goals'] > m['opp_goals'], 'category': 'ASIAN_HANDICAP'},
    'opp_+0.5': {'baseline': 0.55, 'calc': lambda m: m['opp_goals'] >= m['team_goals'], 'category': 'ASIAN_HANDICAP'},
    'opp_+1.0': {'baseline': 0.65, 'calc': lambda m: m['opp_goals'] + 1 >= m['team_goals'], 'category': 'ASIAN_HANDICAP'},
    'opp_+1.5': {'baseline': 0.75, 'calc': lambda m: m['opp_goals'] + 1.5 > m['team_goals'], 'category': 'ASIAN_HANDICAP'},
    'opp_+2.0': {'baseline': 0.85, 'calc': lambda m: m['opp_goals'] + 2 >= m['team_goals'], 'category': 'ASIAN_HANDICAP'},
    
    # HT/FT (8)
    'ht_team_ft_team': {'baseline': 0.30, 'calc': lambda m: m['team_ht'] > m['opp_ht'] and m['team_goals'] > m['opp_goals'], 'category': 'HT_FT'},
    'ht_draw_ft_team': {'baseline': 0.12, 'calc': lambda m: m['team_ht'] == m['opp_ht'] and m['team_goals'] > m['opp_goals'], 'category': 'HT_FT'},
    'ht_opp_ft_team': {'baseline': 0.05, 'calc': lambda m: m['team_ht'] < m['opp_ht'] and m['team_goals'] > m['opp_goals'], 'category': 'HT_FT'},
    'ht_draw_ft_draw': {'baseline': 0.10, 'calc': lambda m: m['team_ht'] == m['opp_ht'] and m['team_goals'] == m['opp_goals'], 'category': 'HT_FT'},
    'ht_team_ft_draw': {'baseline': 0.05, 'calc': lambda m: m['team_ht'] > m['opp_ht'] and m['team_goals'] == m['opp_goals'], 'category': 'HT_FT'},
    'ht_opp_ft_opp': {'baseline': 0.15, 'calc': lambda m: m['team_ht'] < m['opp_ht'] and m['team_goals'] < m['opp_goals'], 'category': 'HT_FT'},
    'ht_opp_ft_draw': {'baseline': 0.03, 'calc': lambda m: m['team_ht'] < m['opp_ht'] and m['team_goals'] == m['opp_goals'], 'category': 'HT_FT'},
    'ht_draw_ft_opp': {'baseline': 0.08, 'calc': lambda m: m['team_ht'] == m['opp_ht'] and m['team_goals'] < m['opp_goals'], 'category': 'HT_FT'},
    
    # CLEAN SHEET (6)
    'team_cs': {'baseline': 0.30, 'calc': lambda m: m['opp_goals'] == 0, 'category': 'CLEAN_SHEET'},
    'team_no_cs': {'baseline': 0.70, 'calc': lambda m: m['opp_goals'] >= 1, 'category': 'CLEAN_SHEET'},
    'opp_cs': {'baseline': 0.25, 'calc': lambda m: m['team_goals'] == 0, 'category': 'CLEAN_SHEET'},
    'opp_no_cs': {'baseline': 0.75, 'calc': lambda m: m['team_goals'] >= 1, 'category': 'CLEAN_SHEET'},
    'both_cs': {'baseline': 0.08, 'calc': lambda m: m['total_goals'] == 0, 'category': 'CLEAN_SHEET'},
    'neither_cs': {'baseline': 0.55, 'calc': lambda m: m['team_goals'] >= 1 and m['opp_goals'] >= 1, 'category': 'CLEAN_SHEET'},
    
    # CORNERS (10)
    'corners_over_7.5': {'baseline': 0.75, 'calc': lambda m: m['total_corners'] >= 8, 'category': 'CORNERS'},
    'corners_over_8.5': {'baseline': 0.60, 'calc': lambda m: m['total_corners'] >= 9, 'category': 'CORNERS'},
    'corners_over_9.5': {'baseline': 0.50, 'calc': lambda m: m['total_corners'] >= 10, 'category': 'CORNERS'},
    'corners_over_10.5': {'baseline': 0.40, 'calc': lambda m: m['total_corners'] >= 11, 'category': 'CORNERS'},
    'corners_over_11.5': {'baseline': 0.30, 'calc': lambda m: m['total_corners'] >= 12, 'category': 'CORNERS'},
    'corners_over_12.5': {'baseline': 0.20, 'calc': lambda m: m['total_corners'] >= 13, 'category': 'CORNERS'},
    'corners_over_13.5': {'baseline': 0.10, 'calc': lambda m: m['total_corners'] >= 14, 'category': 'CORNERS'},
    'team_corners_over_4.5': {'baseline': 0.60, 'calc': lambda m: m['team_corners'] >= 5, 'category': 'CORNERS'},
    'team_corners_over_5.5': {'baseline': 0.45, 'calc': lambda m: m['team_corners'] >= 6, 'category': 'CORNERS'},
    'team_most_corners': {'baseline': 0.50, 'calc': lambda m: m['team_corners'] > m['opp_corners'], 'category': 'CORNERS'},
    
    # OPP CORNERS (3)
    'opp_corners_over_4.5': {'baseline': 0.55, 'calc': lambda m: m['opp_corners'] >= 5, 'category': 'OPP_CORNERS'},
    'opp_corners_over_5.5': {'baseline': 0.40, 'calc': lambda m: m['opp_corners'] >= 6, 'category': 'OPP_CORNERS'},
    'opp_most_corners': {'baseline': 0.45, 'calc': lambda m: m['opp_corners'] > m['team_corners'], 'category': 'OPP_CORNERS'},
    
    # CARDS (8)
    'cards_over_2.5': {'baseline': 0.70, 'calc': lambda m: m['total_cards'] >= 3, 'category': 'CARDS'},
    'cards_over_3.5': {'baseline': 0.50, 'calc': lambda m: m['total_cards'] >= 4, 'category': 'CARDS'},
    'cards_over_4.5': {'baseline': 0.35, 'calc': lambda m: m['total_cards'] >= 5, 'category': 'CARDS'},
    'cards_over_5.5': {'baseline': 0.20, 'calc': lambda m: m['total_cards'] >= 6, 'category': 'CARDS'},
    'cards_over_6.5': {'baseline': 0.10, 'calc': lambda m: m['total_cards'] >= 7, 'category': 'CARDS'},
    'team_cards_over_0.5': {'baseline': 0.80, 'calc': lambda m: m['team_cards'] >= 1, 'category': 'CARDS'},
    'team_cards_over_1.5': {'baseline': 0.50, 'calc': lambda m: m['team_cards'] >= 2, 'category': 'CARDS'},
    'team_cards_over_2.5': {'baseline': 0.25, 'calc': lambda m: m['team_cards'] >= 3, 'category': 'CARDS'},
    
    # OPP CARDS (3)
    'opp_cards_over_0.5': {'baseline': 0.80, 'calc': lambda m: m['opp_cards'] >= 1, 'category': 'OPP_CARDS'},
    'opp_cards_over_1.5': {'baseline': 0.55, 'calc': lambda m: m['opp_cards'] >= 2, 'category': 'OPP_CARDS'},
    'opp_cards_over_2.5': {'baseline': 0.30, 'calc': lambda m: m['opp_cards'] >= 3, 'category': 'OPP_CARDS'},
    
    # RED CARD (1)
    'red_card_yes': {'baseline': 0.08, 'calc': lambda m: m['red_cards'] >= 1, 'category': 'RED_CARD'},
    
    # WIN MARGINS (6)
    'team_win_1': {'baseline': 0.20, 'calc': lambda m: m['team_goals'] - m['opp_goals'] == 1, 'category': 'WIN_MARGIN'},
    'team_win_2': {'baseline': 0.12, 'calc': lambda m: m['team_goals'] - m['opp_goals'] == 2, 'category': 'WIN_MARGIN'},
    'team_win_3plus': {'baseline': 0.08, 'calc': lambda m: m['team_goals'] - m['opp_goals'] >= 3, 'category': 'WIN_MARGIN'},
    'opp_win_1': {'baseline': 0.15, 'calc': lambda m: m['opp_goals'] - m['team_goals'] == 1, 'category': 'WIN_MARGIN'},
    'opp_win_2': {'baseline': 0.08, 'calc': lambda m: m['opp_goals'] - m['team_goals'] == 2, 'category': 'WIN_MARGIN'},
    'opp_win_3plus': {'baseline': 0.05, 'calc': lambda m: m['opp_goals'] - m['team_goals'] >= 3, 'category': 'WIN_MARGIN'},
    
    # EXACT SCORES (12)
    'score_1-0': {'baseline': 0.10, 'calc': lambda m: m['team_goals'] == 1 and m['opp_goals'] == 0, 'category': 'EXACT_SCORE'},
    'score_2-0': {'baseline': 0.08, 'calc': lambda m: m['team_goals'] == 2 and m['opp_goals'] == 0, 'category': 'EXACT_SCORE'},
    'score_2-1': {'baseline': 0.10, 'calc': lambda m: m['team_goals'] == 2 and m['opp_goals'] == 1, 'category': 'EXACT_SCORE'},
    'score_3-0': {'baseline': 0.04, 'calc': lambda m: m['team_goals'] == 3 and m['opp_goals'] == 0, 'category': 'EXACT_SCORE'},
    'score_3-1': {'baseline': 0.05, 'calc': lambda m: m['team_goals'] == 3 and m['opp_goals'] == 1, 'category': 'EXACT_SCORE'},
    'score_3-2': {'baseline': 0.03, 'calc': lambda m: m['team_goals'] == 3 and m['opp_goals'] == 2, 'category': 'EXACT_SCORE'},
    'score_0-0': {'baseline': 0.08, 'calc': lambda m: m['team_goals'] == 0 and m['opp_goals'] == 0, 'category': 'EXACT_SCORE'},
    'score_1-1': {'baseline': 0.12, 'calc': lambda m: m['team_goals'] == 1 and m['opp_goals'] == 1, 'category': 'EXACT_SCORE'},
    'score_2-2': {'baseline': 0.04, 'calc': lambda m: m['team_goals'] == 2 and m['opp_goals'] == 2, 'category': 'EXACT_SCORE'},
    'score_0-1': {'baseline': 0.08, 'calc': lambda m: m['team_goals'] == 0 and m['opp_goals'] == 1, 'category': 'EXACT_SCORE'},
    'score_0-2': {'baseline': 0.05, 'calc': lambda m: m['team_goals'] == 0 and m['opp_goals'] == 2, 'category': 'EXACT_SCORE'},
    'score_1-2': {'baseline': 0.06, 'calc': lambda m: m['team_goals'] == 1 and m['opp_goals'] == 2, 'category': 'EXACT_SCORE'},
    
    # HALF WINNER (4)
    'team_wins_1h': {'baseline': 0.35, 'calc': lambda m: m['team_ht'] > m['opp_ht'], 'category': 'HALF_WINNER'},
    'team_wins_2h': {'baseline': 0.40, 'calc': lambda m: m['team_sh'] > m['opp_sh'], 'category': 'HALF_WINNER'},
    'team_wins_both_halves': {'baseline': 0.18, 'calc': lambda m: m['team_ht'] > m['opp_ht'] and m['team_sh'] > m['opp_sh'], 'category': 'HALF_WINNER'},
    'team_wins_either_half': {'baseline': 0.55, 'calc': lambda m: m['team_ht'] > m['opp_ht'] or m['team_sh'] > m['opp_sh'], 'category': 'HALF_WINNER'},
}


def categorize_opponent(team_name):
    """Catégorise un adversaire"""
    team_lower = team_name.lower()
    for t in TOP_TEAMS:
        if t in team_lower:
            return 'TOP'
    return 'OTHER'


def calculate_market(matches_list, market_def, n_matches):
    """Calcule les stats d'un marché"""
    if n_matches == 0:
        return None
    
    wins = sum(1 for m in matches_list if market_def['calc'](m))
    hit_rate = (wins / n_matches) * 100
    baseline = market_def['baseline'] * 100
    edge = hit_rate - baseline
    
    if n_matches >= 10 and abs(edge) >= 15:
        confidence = "HIGH"
    elif n_matches >= 5 and abs(edge) >= 10:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"
    
    if edge >= 20:
        signal = "STRONG_BACK"
    elif edge >= 10:
        signal = "BACK"
    elif edge <= -20:
        signal = "STRONG_FADE"
    elif edge <= -10:
        signal = "FADE"
    else:
        signal = "NEUTRAL"
    
    return {
        "wins": wins,
        "losses": n_matches - wins,
        "sample": n_matches,
        "hit_rate": round(hit_rate, 1),
        "baseline": round(baseline, 1),
        "edge": round(edge, 1),
        "confidence": confidence,
        "signal": signal
    }


async def refresh_microstrategy_dna():
    """Rafraîchit le fichier MicroStrategyDNA"""
    
    logger.info("=" * 80)
    logger.info("🧬 MICROSTRATEGY DNA REFRESH - DÉMARRAGE")
    logger.info("=" * 80)
    
    start_time = datetime.now()
    
    # Backup fichier existant
    if os.path.exists(OUTPUT_PATH):
        import shutil
        shutil.copy2(OUTPUT_PATH, BACKUP_PATH)
        logger.info(f"📦 Backup créé: {BACKUP_PATH}")
    
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        
        # Récupérer toutes les équipes
        teams_result = await conn.fetch("""
            SELECT DISTINCT home_team as team FROM match_stats_extended
            UNION
            SELECT DISTINCT away_team as team FROM match_stats_extended
            ORDER BY team
        """)
        all_teams = [r['team'] for r in teams_result]
        logger.info(f"📊 {len(all_teams)} équipes à traiter")
        
        # Structure finale
        microstrategy_dna = {
            "metadata": {
                "version": "1.0.0",
                "created": datetime.now().isoformat(),
                "methodology": "126_MARKETS_HEDGE_FUND_GRADE",
                "markets_count": len(MARKETS_DEFINITION),
                "teams_count": 0,
                "last_refresh": datetime.now().isoformat(),
                "refresh_type": "CRON_NIGHTLY"
            },
            "teams": {}
        }
        
        teams_processed = 0
        
        for team_name in all_teams:
            matches = await conn.fetch("""
                SELECT match_date, home_team, away_team,
                       home_goals, away_goals, ht_home_goals, ht_away_goals,
                       corners_home, corners_away,
                       yellow_cards_home, yellow_cards_away,
                       red_cards_home, red_cards_away
                FROM match_stats_extended 
                WHERE home_team = $1 OR away_team = $1
                ORDER BY match_date ASC
            """, team_name)
            
            if len(matches) < 3:
                continue
            
            home_matches = []
            away_matches = []
            
            for m in matches:
                is_home = m['home_team'] == team_name
                opponent = m['away_team'] if is_home else m['home_team']
                
                team_goals = m['home_goals'] if is_home else m['away_goals']
                opp_goals = m['away_goals'] if is_home else m['home_goals']
                team_ht = m['ht_home_goals'] if is_home else m['ht_away_goals']
                opp_ht = m['ht_away_goals'] if is_home else m['ht_home_goals']
                team_corners = m['corners_home'] if is_home else m['corners_away']
                opp_corners = m['corners_away'] if is_home else m['corners_home']
                team_cards = (m['yellow_cards_home'] or 0) if is_home else (m['yellow_cards_away'] or 0)
                opp_cards = (m['yellow_cards_away'] or 0) if is_home else (m['yellow_cards_home'] or 0)
                
                match_data = {
                    'team_goals': team_goals or 0,
                    'opp_goals': opp_goals or 0,
                    'total_goals': (m['home_goals'] or 0) + (m['away_goals'] or 0),
                    'team_ht': team_ht or 0,
                    'opp_ht': opp_ht or 0,
                    'ht_total': (m['ht_home_goals'] or 0) + (m['ht_away_goals'] or 0),
                    'team_sh': (team_goals or 0) - (team_ht or 0),
                    'opp_sh': (opp_goals or 0) - (opp_ht or 0),
                    'sh_total': ((m['home_goals'] or 0) + (m['away_goals'] or 0)) - ((m['ht_home_goals'] or 0) + (m['ht_away_goals'] or 0)),
                    'team_corners': team_corners or 0,
                    'opp_corners': opp_corners or 0,
                    'total_corners': (m['corners_home'] or 0) + (m['corners_away'] or 0),
                    'team_cards': team_cards,
                    'opp_cards': opp_cards,
                    'total_cards': team_cards + opp_cards,
                    'red_cards': (m['red_cards_home'] or 0) + (m['red_cards_away'] or 0),
                }
                
                if is_home:
                    home_matches.append(match_data)
                else:
                    away_matches.append(match_data)
            
            # Calculer tous les marchés
            home_markets = {}
            away_markets = {}
            
            for market_name, market_def in MARKETS_DEFINITION.items():
                home_result = calculate_market(home_matches, market_def, len(home_matches))
                if home_result:
                    home_markets[market_name] = home_result
                
                away_result = calculate_market(away_matches, market_def, len(away_matches))
                if away_result:
                    away_markets[market_name] = away_result
            
            # Specialists & Fades
            home_specialists = [{"market": k, **v} for k, v in home_markets.items() if v['edge'] >= 20]
            away_specialists = [{"market": k, **v} for k, v in away_markets.items() if v['edge'] >= 20]
            
            fade_home = [{"market": k, **v} for k, v in home_markets.items() if v['edge'] <= -15]
            fade_away = [{"market": k, **v} for k, v in away_markets.items() if v['edge'] <= -15]
            
            team_profile = {
                "meta": {
                    "team": team_name,
                    "sample_size": len(home_matches) + len(away_matches),
                    "home_matches": len(home_matches),
                    "away_matches": len(away_matches),
                    "last_updated": datetime.now().isoformat(),
                },
                "home_specialists": sorted(home_specialists, key=lambda x: -x['edge'])[:15],
                "away_specialists": sorted(away_specialists, key=lambda x: -x['edge'])[:15],
                "fade_markets_home": sorted(fade_home, key=lambda x: x['edge'])[:10],
                "fade_markets_away": sorted(fade_away, key=lambda x: x['edge'])[:10],
                "all_markets_home": home_markets,
                "all_markets_away": away_markets
            }
            
            microstrategy_dna["teams"][team_name] = team_profile
            teams_processed += 1
        
        await conn.close()
        
        # Mettre à jour métadonnées
        microstrategy_dna["metadata"]["teams_count"] = teams_processed
        
        # Sauvegarder
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(microstrategy_dna, f, indent=2, ensure_ascii=False, default=str)
        
        duration = (datetime.now() - start_time).total_seconds()
        file_size = os.path.getsize(OUTPUT_PATH)
        
        logger.info("=" * 80)
        logger.info("🧬 MICROSTRATEGY DNA REFRESH - TERMINÉ")
        logger.info("=" * 80)
        logger.info(f"✅ Équipes: {teams_processed}")
        logger.info(f"📊 Taille: {file_size/1024/1024:.2f} MB")
        logger.info(f"⏱️ Durée: {duration:.1f}s")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ ERREUR: {e}")
        # Restaurer backup si erreur
        if os.path.exists(BACKUP_PATH):
            import shutil
            shutil.copy2(BACKUP_PATH, OUTPUT_PATH)
            logger.info("📦 Backup restauré après erreur")
        return False


if __name__ == "__main__":
    success = asyncio.run(refresh_microstrategy_dna())
    sys.exit(0 if success else 1)
