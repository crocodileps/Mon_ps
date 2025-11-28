#!/usr/bin/env python3
"""
🏎️ FERRARI 2.0 - Analyseur de Patterns de Marché
=================================================
Analyse match_results pour identifier des patterns rentables

Patterns analysés:
- Par marché (1X2, BTTS, Over/Under)
- Par ligue
- Par jour de semaine
- Par contexte (forme, H2H simulé)
"""

import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "monps_db"),
    "user": os.getenv("DB_USER", "monps_user"),
    "password": os.getenv("DB_PASSWORD", "monps_secure_password_2024"),
    "port": 5432
}


@dataclass
class Pattern:
    pattern_name: str
    pattern_code: str
    pattern_description: str
    market_type: str
    league: Optional[str]
    day_of_week: Optional[int]
    is_weekend: Optional[bool]
    conditions: Dict
    sample_size: int
    wins: int
    losses: int
    win_rate: float
    avg_odds: Optional[float]
    roi: Optional[float]
    confidence_score: int
    is_profitable: bool
    is_reliable: bool
    recommendation: str
    stake_suggestion: float


class MarketPatternAnalyzer:
    """Analyseur de patterns de marché"""
    
    def __init__(self):
        self.conn = None
        self.patterns = []
        
    def _get_conn(self):
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
        return self.conn
    
    def _calculate_recommendation(self, win_rate: float, sample_size: int, roi: float = 0) -> tuple:
        """Calcule la recommandation basée sur les stats"""
        
        # Fiabilité
        is_reliable = sample_size >= 20
        
        # Recommandation
        if not is_reliable:
            recommendation = "INSUFFICIENT_DATA"
            stake = 0.5
        elif win_rate >= 65 and roi > 10:
            recommendation = "STRONG_BET"
            stake = 2.0
        elif win_rate >= 55 and roi > 0:
            recommendation = "BET"
            stake = 1.5
        elif win_rate >= 50:
            recommendation = "CAUTION"
            stake = 1.0
        else:
            recommendation = "AVOID"
            stake = 0.5
        
        # Confidence score
        confidence = min(100, int(
            (win_rate * 0.4) +
            (min(sample_size, 100) * 0.3) +
            (max(0, min(roi, 50)) * 0.3)
        ))
        
        return recommendation, stake, confidence, is_reliable
    
    # ════════════════════════════════════════════════════════════
    # PATTERNS 1X2
    # ════════════════════════════════════════════════════════════
    
    def analyze_1x2_by_league(self):
        """Analyse 1X2 par ligue"""
        
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                league,
                COUNT(*) as total,
                SUM(CASE WHEN outcome = 'home' THEN 1 ELSE 0 END) as home_wins,
                SUM(CASE WHEN outcome = 'draw' THEN 1 ELSE 0 END) as draws,
                SUM(CASE WHEN outcome = 'away' THEN 1 ELSE 0 END) as away_wins
            FROM match_results
            WHERE is_finished = true 
              AND league IS NOT NULL 
              AND league != ''
            GROUP BY league
            HAVING COUNT(*) >= 10
        """)
        
        for row in cur.fetchall():
            league = row['league']
            total = row['total']
            
            # Pattern HOME WIN
            home_wr = round(row['home_wins'] / total * 100, 2)
            rec, stake, conf, reliable = self._calculate_recommendation(home_wr, total, home_wr - 45)
            
            self.patterns.append(Pattern(
                pattern_name=f"Home Win - {league}",
                pattern_code=f"1x2_home_{league.lower().replace(' ', '_')}",
                pattern_description=f"Paris sur victoire domicile en {league}",
                market_type="1x2",
                league=league,
                day_of_week=None,
                is_weekend=None,
                conditions={"outcome": "home"},
                sample_size=total,
                wins=row['home_wins'],
                losses=total - row['home_wins'],
                win_rate=home_wr,
                avg_odds=1.8,  # Estimation
                roi=round((home_wr * 1.8 - 100), 2),
                confidence_score=conf,
                is_profitable=home_wr > 55,
                is_reliable=reliable,
                recommendation=rec,
                stake_suggestion=stake
            ))
            
            # Pattern DRAW
            draw_wr = round(row['draws'] / total * 100, 2)
            rec, stake, conf, reliable = self._calculate_recommendation(draw_wr, total, draw_wr * 3.2 - 100)
            
            self.patterns.append(Pattern(
                pattern_name=f"Draw - {league}",
                pattern_code=f"1x2_draw_{league.lower().replace(' ', '_')}",
                pattern_description=f"Paris sur match nul en {league}",
                market_type="1x2",
                league=league,
                day_of_week=None,
                is_weekend=None,
                conditions={"outcome": "draw"},
                sample_size=total,
                wins=row['draws'],
                losses=total - row['draws'],
                win_rate=draw_wr,
                avg_odds=3.2,
                roi=round((draw_wr * 3.2 - 100), 2),
                confidence_score=conf,
                is_profitable=draw_wr > 31,
                is_reliable=reliable,
                recommendation=rec,
                stake_suggestion=stake
            ))
            
            # Pattern AWAY WIN
            away_wr = round(row['away_wins'] / total * 100, 2)
            rec, stake, conf, reliable = self._calculate_recommendation(away_wr, total, away_wr * 2.5 - 100)
            
            self.patterns.append(Pattern(
                pattern_name=f"Away Win - {league}",
                pattern_code=f"1x2_away_{league.lower().replace(' ', '_')}",
                pattern_description=f"Paris sur victoire extérieur en {league}",
                market_type="1x2",
                league=league,
                day_of_week=None,
                is_weekend=None,
                conditions={"outcome": "away"},
                sample_size=total,
                wins=row['away_wins'],
                losses=total - row['away_wins'],
                win_rate=away_wr,
                avg_odds=2.5,
                roi=round((away_wr * 2.5 - 100), 2),
                confidence_score=conf,
                is_profitable=away_wr > 40,
                is_reliable=reliable,
                recommendation=rec,
                stake_suggestion=stake
            ))
        
        cur.close()
        logger.info(f"✅ Patterns 1X2 par ligue: {len(self.patterns)}")
    
    # ════════════════════════════════════════════════════════════
    # PATTERNS BTTS
    # ════════════════════════════════════════════════════════════
    
    def analyze_btts_by_league(self):
        """Analyse BTTS par ligue"""
        
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                league,
                COUNT(*) as total,
                SUM(CASE WHEN score_home > 0 AND score_away > 0 THEN 1 ELSE 0 END) as btts_yes,
                SUM(CASE WHEN score_home = 0 OR score_away = 0 THEN 1 ELSE 0 END) as btts_no
            FROM match_results
            WHERE is_finished = true 
              AND league IS NOT NULL 
              AND league != ''
            GROUP BY league
            HAVING COUNT(*) >= 10
        """)
        
        start_count = len(self.patterns)
        
        for row in cur.fetchall():
            league = row['league']
            total = row['total']
            
            # Pattern BTTS YES
            btts_yes_wr = round(row['btts_yes'] / total * 100, 2)
            rec, stake, conf, reliable = self._calculate_recommendation(btts_yes_wr, total, btts_yes_wr * 1.85 - 100)
            
            self.patterns.append(Pattern(
                pattern_name=f"BTTS Yes - {league}",
                pattern_code=f"btts_yes_{league.lower().replace(' ', '_')}",
                pattern_description=f"Les deux équipes marquent en {league}",
                market_type="btts",
                league=league,
                day_of_week=None,
                is_weekend=None,
                conditions={"btts": True},
                sample_size=total,
                wins=row['btts_yes'],
                losses=row['btts_no'],
                win_rate=btts_yes_wr,
                avg_odds=1.85,
                roi=round((btts_yes_wr * 1.85 - 100), 2),
                confidence_score=conf,
                is_profitable=btts_yes_wr > 54,
                is_reliable=reliable,
                recommendation=rec,
                stake_suggestion=stake
            ))
            
            # Pattern BTTS NO
            btts_no_wr = round(row['btts_no'] / total * 100, 2)
            rec, stake, conf, reliable = self._calculate_recommendation(btts_no_wr, total, btts_no_wr * 1.95 - 100)
            
            self.patterns.append(Pattern(
                pattern_name=f"BTTS No - {league}",
                pattern_code=f"btts_no_{league.lower().replace(' ', '_')}",
                pattern_description=f"Au moins une équipe ne marque pas en {league}",
                market_type="btts",
                league=league,
                day_of_week=None,
                is_weekend=None,
                conditions={"btts": False},
                sample_size=total,
                wins=row['btts_no'],
                losses=row['btts_yes'],
                win_rate=btts_no_wr,
                avg_odds=1.95,
                roi=round((btts_no_wr * 1.95 - 100), 2),
                confidence_score=conf,
                is_profitable=btts_no_wr > 51,
                is_reliable=reliable,
                recommendation=rec,
                stake_suggestion=stake
            ))
        
        cur.close()
        logger.info(f"✅ Patterns BTTS par ligue: {len(self.patterns) - start_count}")
    
    # ════════════════════════════════════════════════════════════
    # PATTERNS OVER/UNDER
    # ════════════════════════════════════════════════════════════
    
    def analyze_over_under_by_league(self):
        """Analyse Over/Under 2.5 par ligue"""
        
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                league,
                COUNT(*) as total,
                SUM(CASE WHEN score_home + score_away > 2 THEN 1 ELSE 0 END) as over_25,
                SUM(CASE WHEN score_home + score_away <= 2 THEN 1 ELSE 0 END) as under_25,
                ROUND(AVG(score_home + score_away), 2) as avg_goals
            FROM match_results
            WHERE is_finished = true 
              AND league IS NOT NULL 
              AND league != ''
            GROUP BY league
            HAVING COUNT(*) >= 10
        """)
        
        start_count = len(self.patterns)
        
        for row in cur.fetchall():
            league = row['league']
            total = row['total']
            avg_goals = float(row['avg_goals'])
            
            # Pattern OVER 2.5
            over_wr = round(row['over_25'] / total * 100, 2)
            rec, stake, conf, reliable = self._calculate_recommendation(over_wr, total, over_wr * 1.9 - 100)
            
            self.patterns.append(Pattern(
                pattern_name=f"Over 2.5 - {league}",
                pattern_code=f"over25_{league.lower().replace(' ', '_')}",
                pattern_description=f"Plus de 2.5 buts en {league} (moy: {avg_goals})",
                market_type="over_under",
                league=league,
                day_of_week=None,
                is_weekend=None,
                conditions={"over": 2.5, "avg_goals": avg_goals},
                sample_size=total,
                wins=row['over_25'],
                losses=row['under_25'],
                win_rate=over_wr,
                avg_odds=1.9,
                roi=round((over_wr * 1.9 - 100), 2),
                confidence_score=conf,
                is_profitable=over_wr > 52,
                is_reliable=reliable,
                recommendation=rec,
                stake_suggestion=stake
            ))
            
            # Pattern UNDER 2.5
            under_wr = round(row['under_25'] / total * 100, 2)
            rec, stake, conf, reliable = self._calculate_recommendation(under_wr, total, under_wr * 1.9 - 100)
            
            self.patterns.append(Pattern(
                pattern_name=f"Under 2.5 - {league}",
                pattern_code=f"under25_{league.lower().replace(' ', '_')}",
                pattern_description=f"Moins de 2.5 buts en {league} (moy: {avg_goals})",
                market_type="over_under",
                league=league,
                day_of_week=None,
                is_weekend=None,
                conditions={"under": 2.5, "avg_goals": avg_goals},
                sample_size=total,
                wins=row['under_25'],
                losses=row['over_25'],
                win_rate=under_wr,
                avg_odds=1.9,
                roi=round((under_wr * 1.9 - 100), 2),
                confidence_score=conf,
                is_profitable=under_wr > 52,
                is_reliable=reliable,
                recommendation=rec,
                stake_suggestion=stake
            ))
        
        cur.close()
        logger.info(f"✅ Patterns Over/Under par ligue: {len(self.patterns) - start_count}")
    
    # ════════════════════════════════════════════════════════════
    # PATTERNS PAR JOUR
    # ════════════════════════════════════════════════════════════
    
    def analyze_by_day_of_week(self):
        """Analyse patterns par jour de semaine"""
        
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                EXTRACT(DOW FROM commence_time) as day_of_week,
                COUNT(*) as total,
                SUM(CASE WHEN outcome = 'home' THEN 1 ELSE 0 END) as home_wins,
                SUM(CASE WHEN score_home > 0 AND score_away > 0 THEN 1 ELSE 0 END) as btts_yes,
                SUM(CASE WHEN score_home + score_away > 2 THEN 1 ELSE 0 END) as over_25,
                ROUND(AVG(score_home + score_away), 2) as avg_goals
            FROM match_results
            WHERE is_finished = true
            GROUP BY EXTRACT(DOW FROM commence_time)
            HAVING COUNT(*) >= 15
        """)
        
        days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        start_count = len(self.patterns)
        
        for row in cur.fetchall():
            dow = int(row['day_of_week'])
            day_name = days[dow]
            total = row['total']
            is_weekend = dow in [0, 6]  # Dimanche=0, Samedi=6
            
            # Home win par jour
            home_wr = round(row['home_wins'] / total * 100, 2)
            rec, stake, conf, reliable = self._calculate_recommendation(home_wr, total, home_wr - 45)
            
            self.patterns.append(Pattern(
                pattern_name=f"Home Win - {day_name}",
                pattern_code=f"1x2_home_day_{dow}",
                pattern_description=f"Victoire domicile le {day_name}",
                market_type="1x2",
                league=None,
                day_of_week=dow,
                is_weekend=is_weekend,
                conditions={"outcome": "home", "day": day_name},
                sample_size=total,
                wins=row['home_wins'],
                losses=total - row['home_wins'],
                win_rate=home_wr,
                avg_odds=1.8,
                roi=round((home_wr * 1.8 - 100), 2),
                confidence_score=conf,
                is_profitable=home_wr > 55,
                is_reliable=reliable,
                recommendation=rec,
                stake_suggestion=stake
            ))
            
            # Over 2.5 par jour
            over_wr = round(row['over_25'] / total * 100, 2)
            avg_goals = float(row['avg_goals'])
            rec, stake, conf, reliable = self._calculate_recommendation(over_wr, total, over_wr * 1.9 - 100)
            
            self.patterns.append(Pattern(
                pattern_name=f"Over 2.5 - {day_name}",
                pattern_code=f"over25_day_{dow}",
                pattern_description=f"Plus de 2.5 buts le {day_name} (moy: {avg_goals})",
                market_type="over_under",
                league=None,
                day_of_week=dow,
                is_weekend=is_weekend,
                conditions={"over": 2.5, "day": day_name, "avg_goals": avg_goals},
                sample_size=total,
                wins=row['over_25'],
                losses=total - row['over_25'],
                win_rate=over_wr,
                avg_odds=1.9,
                roi=round((over_wr * 1.9 - 100), 2),
                confidence_score=conf,
                is_profitable=over_wr > 52,
                is_reliable=reliable,
                recommendation=rec,
                stake_suggestion=stake
            ))
        
        cur.close()
        logger.info(f"✅ Patterns par jour: {len(self.patterns) - start_count}")
    
    # ════════════════════════════════════════════════════════════
    # PATTERNS HIGH SCORING
    # ════════════════════════════════════════════════════════════
    
    def analyze_high_scoring_matches(self):
        """Analyse patterns pour matchs à haut score"""
        
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                league,
                COUNT(*) as total,
                SUM(CASE WHEN score_home + score_away >= 4 THEN 1 ELSE 0 END) as high_scoring,
                SUM(CASE WHEN score_home + score_away <= 1 THEN 1 ELSE 0 END) as low_scoring
            FROM match_results
            WHERE is_finished = true 
              AND league IS NOT NULL 
              AND league != ''
            GROUP BY league
            HAVING COUNT(*) >= 20
        """)
        
        start_count = len(self.patterns)
        
        for row in cur.fetchall():
            league = row['league']
            total = row['total']
            
            # Pattern HIGH SCORING (4+ goals)
            high_wr = round(row['high_scoring'] / total * 100, 2)
            rec, stake, conf, reliable = self._calculate_recommendation(high_wr, total, high_wr * 2.5 - 100)
            
            self.patterns.append(Pattern(
                pattern_name=f"High Scoring (4+) - {league}",
                pattern_code=f"high_scoring_{league.lower().replace(' ', '_')}",
                pattern_description=f"4 buts ou plus en {league}",
                market_type="over_under",
                league=league,
                day_of_week=None,
                is_weekend=None,
                conditions={"min_goals": 4},
                sample_size=total,
                wins=row['high_scoring'],
                losses=total - row['high_scoring'],
                win_rate=high_wr,
                avg_odds=2.5,
                roi=round((high_wr * 2.5 - 100), 2),
                confidence_score=conf,
                is_profitable=high_wr > 40,
                is_reliable=reliable,
                recommendation=rec,
                stake_suggestion=stake
            ))
        
        cur.close()
        logger.info(f"✅ Patterns High Scoring: {len(self.patterns) - start_count}")
    
    # ════════════════════════════════════════════════════════════
    # SAUVEGARDE
    # ════════════════════════════════════════════════════════════
    
    def save_patterns(self):
        """Sauvegarde tous les patterns en base"""
        
        conn = self._get_conn()
        cur = conn.cursor()
        
        # Nettoyer les anciens patterns
        cur.execute("DELETE FROM market_patterns")
        
        inserted = 0
        for p in self.patterns:
            try:
                cur.execute("""
                    INSERT INTO market_patterns (
                        pattern_name, pattern_code, pattern_description,
                        market_type, league, day_of_week, is_weekend,
                        conditions, sample_size, wins, losses, win_rate,
                        avg_odds, roi, confidence_score,
                        is_profitable, is_reliable, recommendation, stake_suggestion,
                        last_calculated
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                    )
                    ON CONFLICT (pattern_code) DO UPDATE SET
                        sample_size = EXCLUDED.sample_size,
                        wins = EXCLUDED.wins,
                        losses = EXCLUDED.losses,
                        win_rate = EXCLUDED.win_rate,
                        roi = EXCLUDED.roi,
                        confidence_score = EXCLUDED.confidence_score,
                        is_profitable = EXCLUDED.is_profitable,
                        is_reliable = EXCLUDED.is_reliable,
                        recommendation = EXCLUDED.recommendation,
                        last_calculated = NOW(),
                        updated_at = NOW()
                """, (
                    p.pattern_name, p.pattern_code, p.pattern_description,
                    p.market_type, p.league, p.day_of_week, p.is_weekend,
                    json.dumps(p.conditions), p.sample_size, p.wins, p.losses, p.win_rate,
                    p.avg_odds, p.roi, p.confidence_score,
                    p.is_profitable, p.is_reliable, p.recommendation, p.stake_suggestion
                ))
                inserted += 1
            except Exception as e:
                logger.error(f"❌ Erreur insert pattern {p.pattern_code}: {e}")
                conn.rollback()
        
        conn.commit()
        cur.close()
        logger.info(f"✅ {inserted} patterns sauvegardés")
        return inserted
    
    # ════════════════════════════════════════════════════════════
    # EXÉCUTION
    # ════════════════════════════════════════════════════════════
    
    def analyze_all(self):
        """Exécute toutes les analyses"""
        
        logger.info("🏎️ FERRARI MARKET PATTERN ANALYZER")
        logger.info("=" * 60)
        
        # Analyses
        self.analyze_1x2_by_league()
        self.analyze_btts_by_league()
        self.analyze_over_under_by_league()
        self.analyze_by_day_of_week()
        self.analyze_high_scoring_matches()
        
        # Sauvegarder
        inserted = self.save_patterns()
        
        # Résumé
        profitable = sum(1 for p in self.patterns if p.is_profitable)
        strong_bets = sum(1 for p in self.patterns if p.recommendation == "STRONG_BET")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("🏆 ANALYSE TERMINÉE!")
        logger.info(f"   📊 Total patterns: {len(self.patterns)}")
        logger.info(f"   💰 Profitables: {profitable}")
        logger.info(f"   🎯 Strong Bets: {strong_bets}")
        logger.info("=" * 60)
        
        return {
            "total": len(self.patterns),
            "profitable": profitable,
            "strong_bets": strong_bets,
            "inserted": inserted
        }


if __name__ == "__main__":
    analyzer = MarketPatternAnalyzer()
    analyzer.analyze_all()
