#!/usr/bin/env python3
"""
🧠 CRON: Peuplement automatique de reality_check_results
Analyse tous les matchs terminés et sauvegarde les résultats Reality Check

Usage:
    python3 populate_reality_check_results.py

Cron recommandé: 0 8 * * * (tous les jours à 8h après résolution des matchs)
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
        logging.FileHandler('/var/log/monps/reality_check_populate.log', mode='a')
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

def get_tier(team_name: str, cursor) -> str:
    """Récupère le tier d'une équipe"""
    cursor.execute("""
        SELECT tier FROM team_class 
        WHERE LOWER(team_name) = LOWER(%s)
        LIMIT 1
    """, (team_name,))
    result = cursor.fetchone()
    return result['tier'] if result else 'C'

def get_momentum_score(team_name: str, cursor) -> int:
    """Récupère le score momentum d'une équipe"""
    cursor.execute("""
        SELECT momentum_score FROM team_momentum 
        WHERE LOWER(team_name) = LOWER(%s)
        LIMIT 1
    """, (team_name,))
    result = cursor.fetchone()
    return result['momentum_score'] if result else 50

def calculate_tier_difference(home_tier: str, away_tier: str) -> int:
    """Calcule la différence de tier"""
    tier_values = {'S': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1}
    return tier_values.get(home_tier, 2) - tier_values.get(away_tier, 2)

def calculate_class_score(home_tier: str, away_tier: str, tier_diff: int) -> int:
    """Score basé sur la différence de classe"""
    if tier_diff >= 2:
        return 80  # Forte domination attendue
    elif tier_diff == 1:
        return 65
    elif tier_diff == 0:
        return 50  # Match équilibré
    elif tier_diff == -1:
        return 35
    else:
        return 20  # Outsider

def calculate_context_score(home_momentum: int, away_momentum: int) -> int:
    """Score basé sur le momentum"""
    diff = home_momentum - away_momentum
    if diff > 30:
        return 75
    elif diff > 10:
        return 60
    elif diff > -10:
        return 50
    elif diff > -30:
        return 40
    else:
        return 25

def determine_convergence(class_score: int, context_score: int) -> str:
    """Détermine le statut de convergence"""
    if abs(class_score - context_score) <= 15:
        return 'strong_convergence'
    elif abs(class_score - context_score) <= 30:
        return 'partial_convergence'
    else:
        return 'divergence'

def generate_recommendation(reality_score: int, convergence: str) -> str:
    """Génère une recommandation"""
    if convergence == 'strong_convergence' and reality_score >= 60:
        return "✅ CONFIANCE - Analyse alignée avec les facteurs qualitatifs"
    elif convergence == 'partial_convergence':
        return "⚠️ PRUDENCE - Quelques divergences détectées"
    else:
        return "🚨 ALERTE - Divergence significative entre analyse et réalité"

def check_result_correct(system_pick: str, actual_result: str) -> bool:
    """Vérifie si le pick était correct"""
    if not actual_result or not system_pick:
        return None
    return system_pick.lower() == actual_result.lower()

def populate_reality_check():
    """Peuple reality_check_results depuis les matchs terminés"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Récupérer les matchs terminés non encore analysés
        cursor.execute("""
            SELECT mr.match_id, mr.home_team, mr.away_team, mr.commence_time,
                   mr.score_home, mr.score_away, mr.outcome
            FROM match_results mr
            LEFT JOIN reality_check_results rcr ON mr.match_id = rcr.match_id
            WHERE mr.is_finished = true
            AND rcr.id IS NULL
            ORDER BY mr.commence_time DESC
        """)
        
        matches = cursor.fetchall()
        logger.info(f"📊 {len(matches)} matchs à analyser")
        
        inserted = 0
        for match in matches:
            try:
                home_team = match['home_team']
                away_team = match['away_team']
                
                # Récupérer les données
                home_tier = get_tier(home_team, cursor)
                away_tier = get_tier(away_team, cursor)
                home_momentum = get_momentum_score(home_team, cursor)
                away_momentum = get_momentum_score(away_team, cursor)
                
                # Calculer les scores
                tier_diff = calculate_tier_difference(home_tier, away_tier)
                class_score = calculate_class_score(home_tier, away_tier, tier_diff)
                context_score = calculate_context_score(home_momentum, away_momentum)
                
                # Score global (moyenne pondérée)
                reality_score = int(0.4 * class_score + 0.3 * context_score + 0.3 * 50)
                
                # Convergence et recommandation
                convergence = determine_convergence(class_score, context_score)
                recommendation = generate_recommendation(reality_score, convergence)
                
                # Déterminer le résultat réel
                actual_result = None
                if match['score_home'] is not None and match['score_away'] is not None:
                    if match['score_home'] > match['score_away']:
                        actual_result = 'home'
                    elif match['score_home'] < match['score_away']:
                        actual_result = 'away'
                    else:
                        actual_result = 'draw'
                
                # System pick basé sur le tier
                if tier_diff >= 1:
                    system_pick = 'home'
                elif tier_diff <= -1:
                    system_pick = 'away'
                else:
                    system_pick = 'draw' if class_score < 45 else 'home'
                
                # Vérifier si correct
                is_correct = check_result_correct(system_pick, actual_result)
                
                # Warnings
                warnings = []
                if tier_diff >= 2 and actual_result == 'away':
                    warnings.append("Upset majeur - équipe faible a gagné")
                if home_momentum < 30:
                    warnings.append(f"Home team en crise (momentum: {home_momentum})")
                if away_momentum > 80:
                    warnings.append(f"Away team en excellente forme (momentum: {away_momentum})")
                
                # INSERT
                cursor.execute("""
                    INSERT INTO reality_check_results (
                        match_id, home_team, away_team, commence_time,
                        home_tier, away_tier, tier_difference,
                        class_score, star_player_score, context_score, psychological_score,
                        reality_score, system_pick, system_confidence,
                        convergence_status, warnings, final_recommendation,
                        adjusted_confidence, actual_result, reality_check_correct,
                        created_at
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        NOW()
                    )
                """, (
                    match['match_id'], home_team, away_team, match['commence_time'],
                    home_tier, away_tier, tier_diff,
                    class_score, 50, context_score, 50,  # star_player et psychological à 50 par défaut
                    reality_score, system_pick, reality_score,
                    convergence, Json(warnings), recommendation,
                    reality_score, actual_result, is_correct
                ))
                
                inserted += 1
                
            except Exception as e:
                logger.error(f"❌ Erreur match {match['match_id']}: {e}")
                continue
        
        conn.commit()
        logger.info(f"✅ {inserted} analyses Reality Check insérées")
        
        # Stats finales
        cursor.execute("SELECT COUNT(*) as total FROM reality_check_results")
        total = cursor.fetchone()['total']
        
        cursor.execute("""
            SELECT convergence_status, COUNT(*) as nb
            FROM reality_check_results
            GROUP BY convergence_status
        """)
        stats = cursor.fetchall()
        
        logger.info(f"📊 Total reality_check_results: {total}")
        for s in stats:
            logger.info(f"   - {s['convergence_status']}: {s['nb']}")
        
    except Exception as e:
        logger.error(f"❌ Erreur globale: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    logger.info("🚀 Démarrage peuplement reality_check_results")
    populate_reality_check()
    logger.info("✅ Terminé")
