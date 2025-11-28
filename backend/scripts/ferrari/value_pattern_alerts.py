#!/usr/bin/env python3
"""
🏎️ FERRARI VALUE ALERTS - Détection de Value Bets
==================================================
Identifie les matchs où les patterns VALUE s'appliquent

Patterns VALUE détectés:
- 0-0 Serie A: 13.39% réel vs 6.67% implicite (cote 15)
- 1-1 La Liga: 16.15% réel vs 10% implicite (cote 10)
"""

import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [VALUE] %(message)s'
)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "monps_db"),
    "user": os.getenv("DB_USER", "monps_user"),
    "password": os.getenv("DB_PASSWORD", "monps_secure_password_2024"),
    "port": 5432
}

# Patterns VALUE identifiés
VALUE_PATTERNS = [
    {
        "name": "0-0 Draw",
        "league_contains": "italy_serie_a",
        "market": "correct_score",
        "bet": "0-0",
        "real_prob": 13.39,
        "min_odds": 7.0,  # Cote min pour value (100/13.39 = 7.47)
        "target_odds": 12.0,
        "roi_expected": 100.85,
        "stake_pct": 0.5  # 0.5% du bankroll
    },
    {
        "name": "1-1 Draw",
        "league_contains": "spain_la_liga",
        "market": "correct_score",
        "bet": "1-1",
        "real_prob": 16.15,
        "min_odds": 6.0,  # 100/16.15 = 6.19
        "target_odds": 9.0,
        "roi_expected": 61.50,
        "stake_pct": 0.5
    },
    {
        "name": "Over 2.5",
        "league_contains": "champs_league",
        "market": "over_under",
        "bet": "over_2.5",
        "real_prob": 67.78,
        "min_odds": 1.45,  # 100/67.78 = 1.47
        "target_odds": 1.75,
        "roi_expected": 28.78,
        "stake_pct": 2.0  # Plus gros stake car plus fiable
    },
    {
        "name": "Over 2.5 Bundesliga",
        "league_contains": "germany_bundesliga",
        "market": "over_under",
        "bet": "over_2.5",
        "real_prob": 61.17,
        "min_odds": 1.60,
        "target_odds": 1.85,
        "roi_expected": 16.22,
        "stake_pct": 1.5
    },
    {
        "name": "Home 2+ Goals",
        "league_contains": "champs_league",
        "market": "team_goals",
        "bet": "home_2+",
        "real_prob": 58.89,
        "min_odds": 1.65,
        "target_odds": 1.95,
        "roi_expected": 17.78,
        "stake_pct": 1.5
    }
]


class ValuePatternDetector:
    """Détecte les matchs avec patterns VALUE"""
    
    def __init__(self):
        self.conn = None
        
    def _get_conn(self):
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
        return self.conn
    
    def get_upcoming_matches(self, hours_ahead: int = 48) -> list:
        """Récupère les matchs à venir"""
        
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT DISTINCT 
                home_team,
                away_team,
                sport as league,
                commence_time
            FROM odds_history
            WHERE commence_time > NOW()
              AND commence_time < NOW() + INTERVAL '%s hours'
              AND sport IS NOT NULL
            ORDER BY commence_time
        """, (hours_ahead,))
        
        matches = cur.fetchall()
        cur.close()
        
        return matches
    
    def find_value_opportunities(self, hours_ahead: int = 48) -> list:
        """Trouve les opportunités VALUE dans les matchs à venir"""
        
        matches = self.get_upcoming_matches(hours_ahead)
        opportunities = []
        
        for match in matches:
            league = match.get('league', '')
            
            for pattern in VALUE_PATTERNS:
                # Vérifier si le pattern s'applique à cette ligue
                if pattern['league_contains'].lower() in league.lower():
                    
                    opportunity = {
                        "match": f"{match['home_team']} vs {match['away_team']}",
                        "home_team": match['home_team'],
                        "away_team": match['away_team'],
                        "league": league,
                        "commence_time": match['commence_time'].isoformat() if match['commence_time'] else None,
                        "pattern_name": pattern['name'],
                        "market": pattern['market'],
                        "bet": pattern['bet'],
                        "real_probability": pattern['real_prob'],
                        "min_odds_for_value": pattern['min_odds'],
                        "target_odds": pattern['target_odds'],
                        "expected_roi": pattern['roi_expected'],
                        "suggested_stake_pct": pattern['stake_pct'],
                        "alert_type": "VALUE_BET",
                        "confidence": "HIGH" if pattern['roi_expected'] > 20 else "MEDIUM"
                    }
                    
                    opportunities.append(opportunity)
        
        return opportunities
    
    def generate_report(self, hours_ahead: int = 48) -> dict:
        """Génère un rapport des opportunités VALUE"""
        
        opportunities = self.find_value_opportunities(hours_ahead)
        
        # Grouper par match
        by_match = {}
        for opp in opportunities:
            match_key = opp['match']
            if match_key not in by_match:
                by_match[match_key] = {
                    "match": match_key,
                    "league": opp['league'],
                    "commence_time": opp['commence_time'],
                    "opportunities": []
                }
            by_match[match_key]['opportunities'].append({
                "pattern": opp['pattern_name'],
                "bet": opp['bet'],
                "real_prob": opp['real_probability'],
                "min_odds": opp['min_odds_for_value'],
                "roi": opp['expected_roi'],
                "stake": opp['suggested_stake_pct']
            })
        
        # Trier par nombre d'opportunités
        sorted_matches = sorted(by_match.values(), 
                                key=lambda x: len(x['opportunities']), 
                                reverse=True)
        
        return {
            "generated_at": datetime.now().isoformat(),
            "hours_ahead": hours_ahead,
            "total_opportunities": len(opportunities),
            "matches_with_value": len(by_match),
            "matches": sorted_matches
        }
    
    def print_alerts(self, hours_ahead: int = 48):
        """Affiche les alertes VALUE"""
        
        report = self.generate_report(hours_ahead)
        
        logger.info("=" * 60)
        logger.info("🏎️ FERRARI VALUE ALERTS")
        logger.info(f"   Période: {hours_ahead}h")
        logger.info(f"   Opportunités: {report['total_opportunities']}")
        logger.info(f"   Matchs avec VALUE: {report['matches_with_value']}")
        logger.info("=" * 60)
        
        for match in report['matches']:
            logger.info("")
            logger.info(f"⚽ {match['match']}")
            logger.info(f"   📍 {match['league']}")
            logger.info(f"   🕐 {match['commence_time']}")
            
            for opp in match['opportunities']:
                logger.info(f"   💎 {opp['pattern']} → {opp['bet']}")
                logger.info(f"      Prob réelle: {opp['real_prob']}%")
                logger.info(f"      Cote min VALUE: {opp['min_odds']}")
                logger.info(f"      ROI attendu: +{opp['roi']}%")
                logger.info(f"      Stake suggéré: {opp['stake']}% bankroll")
        
        logger.info("")
        logger.info("=" * 60)
        
        return report


def main():
    detector = ValuePatternDetector()
    detector.print_alerts(hours_ahead=72)


if __name__ == "__main__":
    main()
