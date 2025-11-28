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


# ════════════════════════════════════════════════════════════
# 🏎️ PATTERNS AVANCÉS V2
# ════════════════════════════════════════════════════════════

class AdvancedPatternAnalyzer(MarketPatternAnalyzer):
    """Analyseur de patterns avancés"""
    
    def analyze_combined_patterns(self):
        """Analyse patterns combinés (BTTS + Over, etc.)"""
        
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Pattern: BTTS YES + Over 2.5
        cur.execute("""
            SELECT 
                league,
                COUNT(*) as total,
                SUM(CASE WHEN score_home > 0 AND score_away > 0 
                         AND score_home + score_away > 2 THEN 1 ELSE 0 END) as btts_over25,
                ROUND(AVG(score_home + score_away), 2) as avg_goals
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
            
            # BTTS YES + Over 2.5
            combo_wr = round(row['btts_over25'] / total * 100, 2)
            # Cote combinée estimée: ~2.3
            rec, stake, conf, reliable = self._calculate_recommendation(combo_wr, total, combo_wr * 2.3 - 100)
            
            self.patterns.append(Pattern(
                pattern_name=f"BTTS + Over 2.5 - {league}",
                pattern_code=f"combo_btts_over25_{league.lower().replace(' ', '_')}",
                pattern_description=f"BTTS Oui ET Plus de 2.5 buts en {league}",
                market_type="combo",
                league=league,
                day_of_week=None,
                is_weekend=None,
                conditions={"btts": True, "over": 2.5, "combo": True},
                sample_size=total,
                wins=row['btts_over25'],
                losses=total - row['btts_over25'],
                win_rate=combo_wr,
                avg_odds=2.3,
                roi=round((combo_wr * 2.3 - 100), 2),
                confidence_score=conf,
                is_profitable=combo_wr > 43,
                is_reliable=reliable,
                recommendation=rec,
                stake_suggestion=stake
            ))
        
        # Pattern: Home Win + BTTS YES
        cur.execute("""
            SELECT 
                league,
                COUNT(*) as total,
                SUM(CASE WHEN outcome = 'home' 
                         AND score_home > 0 AND score_away > 0 THEN 1 ELSE 0 END) as home_btts
            FROM match_results
            WHERE is_finished = true 
              AND league IS NOT NULL 
              AND league != ''
            GROUP BY league
            HAVING COUNT(*) >= 20
        """)
        
        for row in cur.fetchall():
            league = row['league']
            total = row['total']
            
            combo_wr = round(row['home_btts'] / total * 100, 2)
            rec, stake, conf, reliable = self._calculate_recommendation(combo_wr, total, combo_wr * 3.5 - 100)
            
            self.patterns.append(Pattern(
                pattern_name=f"Home Win + BTTS - {league}",
                pattern_code=f"combo_home_btts_{league.lower().replace(' ', '_')}",
                pattern_description=f"Victoire domicile ET les deux marquent en {league}",
                market_type="combo",
                league=league,
                day_of_week=None,
                is_weekend=None,
                conditions={"outcome": "home", "btts": True, "combo": True},
                sample_size=total,
                wins=row['home_btts'],
                losses=total - row['home_btts'],
                win_rate=combo_wr,
                avg_odds=3.5,
                roi=round((combo_wr * 3.5 - 100), 2),
                confidence_score=conf,
                is_profitable=combo_wr > 28,
                is_reliable=reliable,
                recommendation=rec,
                stake_suggestion=stake
            ))
        
        # Pattern: Home Win + Over 1.5
        cur.execute("""
            SELECT 
                league,
                COUNT(*) as total,
                SUM(CASE WHEN outcome = 'home' 
                         AND score_home + score_away > 1 THEN 1 ELSE 0 END) as home_over15
            FROM match_results
            WHERE is_finished = true 
              AND league IS NOT NULL 
              AND league != ''
            GROUP BY league
            HAVING COUNT(*) >= 20
        """)
        
        for row in cur.fetchall():
            league = row['league']
            total = row['total']
            
            combo_wr = round(row['home_over15'] / total * 100, 2)
            rec, stake, conf, reliable = self._calculate_recommendation(combo_wr, total, combo_wr * 2.0 - 100)
            
            self.patterns.append(Pattern(
                pattern_name=f"Home Win + Over 1.5 - {league}",
                pattern_code=f"combo_home_over15_{league.lower().replace(' ', '_')}",
                pattern_description=f"Victoire domicile ET plus de 1.5 buts en {league}",
                market_type="combo",
                league=league,
                day_of_week=None,
                is_weekend=None,
                conditions={"outcome": "home", "over": 1.5, "combo": True},
                sample_size=total,
                wins=row['home_over15'],
                losses=total - row['home_over15'],
                win_rate=combo_wr,
                avg_odds=2.0,
                roi=round((combo_wr * 2.0 - 100), 2),
                confidence_score=conf,
                is_profitable=combo_wr > 50,
                is_reliable=reliable,
                recommendation=rec,
                stake_suggestion=stake
            ))
        
        cur.close()
        logger.info(f"✅ Patterns combinés: {len(self.patterns) - start_count}")
    
    def analyze_scoreline_patterns(self):
        """Analyse patterns de scores exacts fréquents"""
        
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Scores les plus fréquents par ligue
        cur.execute("""
            SELECT 
                league,
                score_home || '-' || score_away as scoreline,
                COUNT(*) as occurrences,
                (SELECT COUNT(*) FROM match_results mr2 
                 WHERE mr2.league = mr.league AND mr2.is_finished = true) as total
            FROM match_results mr
            WHERE is_finished = true 
              AND league IS NOT NULL 
              AND league != ''
            GROUP BY league, score_home, score_away
            HAVING COUNT(*) >= 5
            ORDER BY league, occurrences DESC
        """)
        
        start_count = len(self.patterns)
        seen_leagues = set()
        
        for row in cur.fetchall():
            league = row['league']
            
            # Seulement le top scoreline par ligue
            if league in seen_leagues:
                continue
            seen_leagues.add(league)
            
            scoreline = row['scoreline']
            occurrences = row['occurrences']
            total = row['total']
            
            wr = round(occurrences / total * 100, 2)
            # Cote score exact ~8-12
            rec, stake, conf, reliable = self._calculate_recommendation(wr, total, wr * 10 - 100)
            
            self.patterns.append(Pattern(
                pattern_name=f"Score {scoreline} - {league}",
                pattern_code=f"scoreline_{scoreline.replace('-', '_')}_{league.lower().replace(' ', '_')}",
                pattern_description=f"Score exact {scoreline} le plus fréquent en {league}",
                market_type="correct_score",
                league=league,
                day_of_week=None,
                is_weekend=None,
                conditions={"scoreline": scoreline},
                sample_size=total,
                wins=occurrences,
                losses=total - occurrences,
                win_rate=wr,
                avg_odds=10.0,
                roi=round((wr * 10 - 100), 2),
                confidence_score=conf,
                is_profitable=wr > 10,
                is_reliable=reliable,
                recommendation=rec,
                stake_suggestion=stake
            ))
        
        cur.close()
        logger.info(f"✅ Patterns scoreline: {len(self.patterns) - start_count}")
    
    def analyze_goal_timing_patterns(self):
        """Analyse patterns liés aux buts (équipe qui marque en premier, etc.)"""
        
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Pattern: Home team marque au moins 1
        cur.execute("""
            SELECT 
                league,
                COUNT(*) as total,
                SUM(CASE WHEN score_home > 0 THEN 1 ELSE 0 END) as home_scores,
                SUM(CASE WHEN score_home >= 2 THEN 1 ELSE 0 END) as home_scores_2plus
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
            
            # Home to score
            home_scores_wr = round(row['home_scores'] / total * 100, 2)
            rec, stake, conf, reliable = self._calculate_recommendation(home_scores_wr, total, home_scores_wr * 1.3 - 100)
            
            self.patterns.append(Pattern(
                pattern_name=f"Home to Score - {league}",
                pattern_code=f"home_to_score_{league.lower().replace(' ', '_')}",
                pattern_description=f"L'équipe à domicile marque au moins 1 but en {league}",
                market_type="team_goals",
                league=league,
                day_of_week=None,
                is_weekend=None,
                conditions={"home_goals": "1+"},
                sample_size=total,
                wins=row['home_scores'],
                losses=total - row['home_scores'],
                win_rate=home_scores_wr,
                avg_odds=1.3,
                roi=round((home_scores_wr * 1.3 - 100), 2),
                confidence_score=conf,
                is_profitable=home_scores_wr > 77,
                is_reliable=reliable,
                recommendation=rec,
                stake_suggestion=stake
            ))
            
            # Home 2+ goals
            home_2plus_wr = round(row['home_scores_2plus'] / total * 100, 2)
            rec, stake, conf, reliable = self._calculate_recommendation(home_2plus_wr, total, home_2plus_wr * 2.0 - 100)
            
            self.patterns.append(Pattern(
                pattern_name=f"Home 2+ Goals - {league}",
                pattern_code=f"home_2plus_{league.lower().replace(' ', '_')}",
                pattern_description=f"L'équipe à domicile marque 2+ buts en {league}",
                market_type="team_goals",
                league=league,
                day_of_week=None,
                is_weekend=None,
                conditions={"home_goals": "2+"},
                sample_size=total,
                wins=row['home_scores_2plus'],
                losses=total - row['home_scores_2plus'],
                win_rate=home_2plus_wr,
                avg_odds=2.0,
                roi=round((home_2plus_wr * 2.0 - 100), 2),
                confidence_score=conf,
                is_profitable=home_2plus_wr > 50,
                is_reliable=reliable,
                recommendation=rec,
                stake_suggestion=stake
            ))
        
        cur.close()
        logger.info(f"✅ Patterns team goals: {len(self.patterns) - start_count}")
    
    def analyze_clean_sheet_patterns(self):
        """Analyse patterns clean sheet"""
        
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                league,
                COUNT(*) as total,
                SUM(CASE WHEN score_away = 0 THEN 1 ELSE 0 END) as home_clean_sheet,
                SUM(CASE WHEN score_home = 0 THEN 1 ELSE 0 END) as away_clean_sheet
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
            
            # Home clean sheet
            hcs_wr = round(row['home_clean_sheet'] / total * 100, 2)
            rec, stake, conf, reliable = self._calculate_recommendation(hcs_wr, total, hcs_wr * 2.5 - 100)
            
            self.patterns.append(Pattern(
                pattern_name=f"Home Clean Sheet - {league}",
                pattern_code=f"home_cs_{league.lower().replace(' ', '_')}",
                pattern_description=f"L'équipe à domicile ne prend pas de but en {league}",
                market_type="clean_sheet",
                league=league,
                day_of_week=None,
                is_weekend=None,
                conditions={"away_goals": 0},
                sample_size=total,
                wins=row['home_clean_sheet'],
                losses=total - row['home_clean_sheet'],
                win_rate=hcs_wr,
                avg_odds=2.5,
                roi=round((hcs_wr * 2.5 - 100), 2),
                confidence_score=conf,
                is_profitable=hcs_wr > 40,
                is_reliable=reliable,
                recommendation=rec,
                stake_suggestion=stake
            ))
        
        cur.close()
        logger.info(f"✅ Patterns clean sheet: {len(self.patterns) - start_count}")
    
    def analyze_all_advanced(self):
        """Exécute toutes les analyses avancées"""
        
        logger.info("")
        logger.info("🏎️ PATTERNS AVANCÉS V2")
        logger.info("=" * 60)
        
        # Patterns de base
        self.analyze_1x2_by_league()
        self.analyze_btts_by_league()
        self.analyze_over_under_by_league()
        self.analyze_by_day_of_week()
        self.analyze_high_scoring_matches()
        
        # Patterns avancés
        self.analyze_combined_patterns()
        self.analyze_scoreline_patterns()
        self.analyze_goal_timing_patterns()
        self.analyze_clean_sheet_patterns()
        
        # Sauvegarder
        inserted = self.save_patterns()
        
        # Résumé
        profitable = sum(1 for p in self.patterns if p.is_profitable)
        strong_bets = sum(1 for p in self.patterns if p.recommendation == "STRONG_BET")
        combos = sum(1 for p in self.patterns if p.market_type == "combo")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("🏆 ANALYSE AVANCÉE TERMINÉE!")
        logger.info(f"   �� Total patterns: {len(self.patterns)}")
        logger.info(f"   🔄 Combos: {combos}")
        logger.info(f"   💰 Profitables: {profitable}")
        logger.info(f"   🎯 Strong Bets: {strong_bets}")
        logger.info("=" * 60)
        
        return {
            "total": len(self.patterns),
            "combos": combos,
            "profitable": profitable,
            "strong_bets": strong_bets,
            "inserted": inserted
        }


# Remplacer le main
if __name__ == "__main__":
    import sys
    
    if "--advanced" in sys.argv:
        analyzer = AdvancedPatternAnalyzer()
        analyzer.analyze_all_advanced()
    else:
        analyzer = MarketPatternAnalyzer()
        analyzer.analyze_all()


# ════════════════════════════════════════════════════════════
# 🏎️ PATTERNS PROFESSIONNELS V3
# ════════════════════════════════════════════════════════════

class ProPatternAnalyzer(AdvancedPatternAnalyzer):
    """Analyseur de patterns niveau professionnel"""
    
    def analyze_streak_patterns(self):
        """Analyse patterns basés sur les séries (forme récente)"""
        
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Calculer la forme des équipes sur leurs 5 derniers matchs
        # Pattern: Équipe en forme (3+ victoires sur 5) à domicile
        cur.execute("""
            WITH team_form AS (
                SELECT 
                    home_team as team,
                    commence_time,
                    CASE WHEN outcome = 'home' THEN 'W' 
                         WHEN outcome = 'draw' THEN 'D' 
                         ELSE 'L' END as result,
                    'home' as venue
                FROM match_results WHERE is_finished = true
                UNION ALL
                SELECT 
                    away_team as team,
                    commence_time,
                    CASE WHEN outcome = 'away' THEN 'W' 
                         WHEN outcome = 'draw' THEN 'D' 
                         ELSE 'L' END as result,
                    'away' as venue
                FROM match_results WHERE is_finished = true
            ),
            form_stats AS (
                SELECT 
                    team,
                    COUNT(*) as total_matches,
                    SUM(CASE WHEN result = 'W' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN result = 'D' THEN 1 ELSE 0 END) as draws,
                    SUM(CASE WHEN result = 'L' THEN 1 ELSE 0 END) as losses
                FROM team_form
                GROUP BY team
                HAVING COUNT(*) >= 5
            )
            SELECT 
                'all' as league,
                COUNT(*) as total_teams,
                AVG(wins::float / total_matches * 100) as avg_win_rate,
                SUM(CASE WHEN wins::float / total_matches > 0.5 THEN 1 ELSE 0 END) as good_form_teams,
                SUM(CASE WHEN wins::float / total_matches < 0.3 THEN 1 ELSE 0 END) as bad_form_teams
            FROM form_stats
        """)
        
        row = cur.fetchone()
        if row and row['total_teams']:
            start_count = len(self.patterns)
            
            # Pattern: Équipes en bonne forme (>50% WR)
            good_pct = round(row['good_form_teams'] / row['total_teams'] * 100, 2) if row['total_teams'] else 0
            
            self.patterns.append(Pattern(
                pattern_name="Good Form Teams (>50% WR)",
                pattern_code="form_good_teams",
                pattern_description=f"{row['good_form_teams']} équipes sur {row['total_teams']} ont >50% de victoires",
                market_type="form",
                league=None,
                day_of_week=None,
                is_weekend=None,
                conditions={"min_win_rate": 50, "type": "good_form"},
                sample_size=row['total_teams'],
                wins=row['good_form_teams'],
                losses=row['total_teams'] - row['good_form_teams'],
                win_rate=good_pct,
                avg_odds=1.5,
                roi=round((good_pct * 1.5 - 100), 2),
                confidence_score=50,
                is_profitable=good_pct > 66,
                is_reliable=row['total_teams'] >= 20,
                recommendation="INFO",
                stake_suggestion=1.0
            ))
            
            logger.info(f"✅ Patterns streak/forme: {len(self.patterns) - start_count}")
        
        cur.close()
    
    def analyze_half_patterns(self):
        """Analyse patterns première/deuxième mi-temps (simulé avec score total)"""
        
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Pattern: Matchs avec beaucoup de buts (proxy pour 2ème MT active)
        cur.execute("""
            SELECT 
                league,
                COUNT(*) as total,
                SUM(CASE WHEN score_home + score_away >= 3 THEN 1 ELSE 0 END) as high_scoring,
                SUM(CASE WHEN score_home + score_away >= 4 THEN 1 ELSE 0 END) as very_high,
                SUM(CASE WHEN score_home + score_away = 0 THEN 1 ELSE 0 END) as nil_nil
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
            
            # Pattern: 0-0 (très rare mais côté élevée ~15)
            nil_nil_wr = round(row['nil_nil'] / total * 100, 2)
            rec, stake, conf, reliable = self._calculate_recommendation(nil_nil_wr, total, nil_nil_wr * 15 - 100)
            
            self.patterns.append(Pattern(
                pattern_name=f"0-0 Draw - {league}",
                pattern_code=f"nil_nil_{league.lower().replace(' ', '_')}",
                pattern_description=f"Match 0-0 en {league}",
                market_type="correct_score",
                league=league,
                day_of_week=None,
                is_weekend=None,
                conditions={"scoreline": "0-0"},
                sample_size=total,
                wins=row['nil_nil'],
                losses=total - row['nil_nil'],
                win_rate=nil_nil_wr,
                avg_odds=15.0,
                roi=round((nil_nil_wr * 15 - 100), 2),
                confidence_score=conf,
                is_profitable=nil_nil_wr > 6.7,
                is_reliable=reliable,
                recommendation=rec,
                stake_suggestion=stake
            ))
        
        cur.close()
        logger.info(f"✅ Patterns mi-temps/score: {len(self.patterns) - start_count}")
    
    def analyze_goal_difference_patterns(self):
        """Analyse patterns basés sur l'écart de buts"""
        
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                league,
                COUNT(*) as total,
                SUM(CASE WHEN ABS(score_home - score_away) = 1 THEN 1 ELSE 0 END) as close_games,
                SUM(CASE WHEN ABS(score_home - score_away) >= 3 THEN 1 ELSE 0 END) as blowouts,
                SUM(CASE WHEN score_home - score_away >= 2 THEN 1 ELSE 0 END) as home_dominant,
                SUM(CASE WHEN score_away - score_home >= 2 THEN 1 ELSE 0 END) as away_dominant
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
            
            # Pattern: Match serré (1 but d'écart)
            close_wr = round(row['close_games'] / total * 100, 2)
            rec, stake, conf, reliable = self._calculate_recommendation(close_wr, total, close_wr * 2.2 - 100)
            
            self.patterns.append(Pattern(
                pattern_name=f"Close Game (1 goal diff) - {league}",
                pattern_code=f"close_game_{league.lower().replace(' ', '_')}",
                pattern_description=f"Match avec 1 but d'écart en {league}",
                market_type="handicap",
                league=league,
                day_of_week=None,
                is_weekend=None,
                conditions={"goal_diff": 1},
                sample_size=total,
                wins=row['close_games'],
                losses=total - row['close_games'],
                win_rate=close_wr,
                avg_odds=2.2,
                roi=round((close_wr * 2.2 - 100), 2),
                confidence_score=conf,
                is_profitable=close_wr > 45,
                is_reliable=reliable,
                recommendation=rec,
                stake_suggestion=stake
            ))
            
            # Pattern: Blowout (3+ buts d'écart)
            blowout_wr = round(row['blowouts'] / total * 100, 2)
            rec, stake, conf, reliable = self._calculate_recommendation(blowout_wr, total, blowout_wr * 4.0 - 100)
            
            self.patterns.append(Pattern(
                pattern_name=f"Blowout (3+ diff) - {league}",
                pattern_code=f"blowout_{league.lower().replace(' ', '_')}",
                pattern_description=f"Match avec 3+ buts d'écart en {league}",
                market_type="handicap",
                league=league,
                day_of_week=None,
                is_weekend=None,
                conditions={"goal_diff": "3+"},
                sample_size=total,
                wins=row['blowouts'],
                losses=total - row['blowouts'],
                win_rate=blowout_wr,
                avg_odds=4.0,
                roi=round((blowout_wr * 4.0 - 100), 2),
                confidence_score=conf,
                is_profitable=blowout_wr > 25,
                is_reliable=reliable,
                recommendation=rec,
                stake_suggestion=stake
            ))
        
        cur.close()
        logger.info(f"✅ Patterns goal difference: {len(self.patterns) - start_count}")
    
    def analyze_timing_patterns(self):
        """Analyse patterns selon l'heure du match"""
        
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                CASE 
                    WHEN EXTRACT(HOUR FROM commence_time) < 15 THEN 'early'
                    WHEN EXTRACT(HOUR FROM commence_time) < 18 THEN 'afternoon'
                    WHEN EXTRACT(HOUR FROM commence_time) < 21 THEN 'evening'
                    ELSE 'night'
                END as time_slot,
                COUNT(*) as total,
                SUM(CASE WHEN outcome = 'home' THEN 1 ELSE 0 END) as home_wins,
                SUM(CASE WHEN score_home + score_away > 2 THEN 1 ELSE 0 END) as over_25,
                ROUND(AVG(score_home + score_away), 2) as avg_goals
            FROM match_results
            WHERE is_finished = true
            GROUP BY 
                CASE 
                    WHEN EXTRACT(HOUR FROM commence_time) < 15 THEN 'early'
                    WHEN EXTRACT(HOUR FROM commence_time) < 18 THEN 'afternoon'
                    WHEN EXTRACT(HOUR FROM commence_time) < 21 THEN 'evening'
                    ELSE 'night'
                END
            HAVING COUNT(*) >= 20
        """)
        
        start_count = len(self.patterns)
        slot_names = {'early': 'Matin (<15h)', 'afternoon': 'Après-midi (15-18h)', 
                      'evening': 'Soirée (18-21h)', 'night': 'Nuit (>21h)'}
        
        for row in cur.fetchall():
            slot = row['time_slot']
            slot_name = slot_names.get(slot, slot)
            total = row['total']
            avg_goals = float(row['avg_goals'])
            
            # Over 2.5 par créneau
            over_wr = round(row['over_25'] / total * 100, 2)
            rec, stake, conf, reliable = self._calculate_recommendation(over_wr, total, over_wr * 1.9 - 100)
            
            self.patterns.append(Pattern(
                pattern_name=f"Over 2.5 - {slot_name}",
                pattern_code=f"over25_time_{slot}",
                pattern_description=f"Plus de 2.5 buts pour matchs {slot_name} (moy: {avg_goals})",
                market_type="over_under",
                league=None,
                day_of_week=None,
                is_weekend=None,
                conditions={"time_slot": slot, "over": 2.5, "avg_goals": avg_goals},
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
            
            # Home win par créneau
            home_wr = round(row['home_wins'] / total * 100, 2)
            rec, stake, conf, reliable = self._calculate_recommendation(home_wr, total, home_wr * 1.8 - 100)
            
            self.patterns.append(Pattern(
                pattern_name=f"Home Win - {slot_name}",
                pattern_code=f"home_time_{slot}",
                pattern_description=f"Victoire domicile pour matchs {slot_name}",
                market_type="1x2",
                league=None,
                day_of_week=None,
                is_weekend=None,
                conditions={"time_slot": slot, "outcome": "home"},
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
        
        cur.close()
        logger.info(f"✅ Patterns timing: {len(self.patterns) - start_count}")
    
    def analyze_winning_margin_patterns(self):
        """Analyse patterns marge de victoire"""
        
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                league,
                COUNT(*) as total,
                SUM(CASE WHEN outcome = 'home' AND score_home - score_away = 1 THEN 1 ELSE 0 END) as home_by_1,
                SUM(CASE WHEN outcome = 'home' AND score_home - score_away = 2 THEN 1 ELSE 0 END) as home_by_2,
                SUM(CASE WHEN outcome = 'away' AND score_away - score_home = 1 THEN 1 ELSE 0 END) as away_by_1
            FROM match_results
            WHERE is_finished = true 
              AND league IS NOT NULL 
              AND league != ''
            GROUP BY league
            HAVING COUNT(*) >= 30
        """)
        
        start_count = len(self.patterns)
        
        for row in cur.fetchall():
            league = row['league']
            total = row['total']
            
            # Home win by exactly 1 goal
            hb1_wr = round(row['home_by_1'] / total * 100, 2)
            rec, stake, conf, reliable = self._calculate_recommendation(hb1_wr, total, hb1_wr * 4.5 - 100)
            
            self.patterns.append(Pattern(
                pattern_name=f"Home Win by 1 - {league}",
                pattern_code=f"home_by_1_{league.lower().replace(' ', '_')}",
                pattern_description=f"Victoire domicile par 1 but exact en {league}",
                market_type="winning_margin",
                league=league,
                day_of_week=None,
                is_weekend=None,
                conditions={"outcome": "home", "margin": 1},
                sample_size=total,
                wins=row['home_by_1'],
                losses=total - row['home_by_1'],
                win_rate=hb1_wr,
                avg_odds=4.5,
                roi=round((hb1_wr * 4.5 - 100), 2),
                confidence_score=conf,
                is_profitable=hb1_wr > 22,
                is_reliable=reliable,
                recommendation=rec,
                stake_suggestion=stake
            ))
            
            # Home win by exactly 2 goals
            hb2_wr = round(row['home_by_2'] / total * 100, 2)
            rec, stake, conf, reliable = self._calculate_recommendation(hb2_wr, total, hb2_wr * 6.0 - 100)
            
            self.patterns.append(Pattern(
                pattern_name=f"Home Win by 2 - {league}",
                pattern_code=f"home_by_2_{league.lower().replace(' ', '_')}",
                pattern_description=f"Victoire domicile par 2 buts exact en {league}",
                market_type="winning_margin",
                league=league,
                day_of_week=None,
                is_weekend=None,
                conditions={"outcome": "home", "margin": 2},
                sample_size=total,
                wins=row['home_by_2'],
                losses=total - row['home_by_2'],
                win_rate=hb2_wr,
                avg_odds=6.0,
                roi=round((hb2_wr * 6.0 - 100), 2),
                confidence_score=conf,
                is_profitable=hb2_wr > 16,
                is_reliable=reliable,
                recommendation=rec,
                stake_suggestion=stake
            ))
        
        cur.close()
        logger.info(f"✅ Patterns winning margin: {len(self.patterns) - start_count}")
    
    def analyze_all_pro(self):
        """Exécute TOUTES les analyses professionnelles"""
        
        logger.info("")
        logger.info("🏎️ FERRARI PATTERN ANALYZER - MODE PRO")
        logger.info("=" * 60)
        
        # Patterns de base
        self.analyze_1x2_by_league()
        self.analyze_btts_by_league()
        self.analyze_over_under_by_league()
        self.analyze_by_day_of_week()
        self.analyze_high_scoring_matches()
        
        # Patterns avancés
        self.analyze_combined_patterns()
        self.analyze_scoreline_patterns()
        self.analyze_goal_timing_patterns()
        self.analyze_clean_sheet_patterns()
        
        # Patterns PRO
        self.analyze_streak_patterns()
        self.analyze_half_patterns()
        self.analyze_goal_difference_patterns()
        self.analyze_timing_patterns()
        self.analyze_winning_margin_patterns()
        
        # Sauvegarder
        inserted = self.save_patterns()
        
        # Résumé détaillé
        by_market = {}
        for p in self.patterns:
            mt = p.market_type
            if mt not in by_market:
                by_market[mt] = {"total": 0, "profitable": 0}
            by_market[mt]["total"] += 1
            if p.is_profitable:
                by_market[mt]["profitable"] += 1
        
        profitable = sum(1 for p in self.patterns if p.is_profitable)
        strong_bets = sum(1 for p in self.patterns if p.recommendation == "STRONG_BET")
        bets = sum(1 for p in self.patterns if p.recommendation == "BET")
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("🏆 ANALYSE PRO TERMINÉE!")
        logger.info(f"   📊 Total patterns: {len(self.patterns)}")
        logger.info(f"   💰 Profitables: {profitable}")
        logger.info(f"   🎯 Strong Bets: {strong_bets}")
        logger.info(f"   ✅ Bets: {bets}")
        logger.info("")
        logger.info("   📊 Par type de marché:")
        for mt, stats in sorted(by_market.items(), key=lambda x: x[1]['profitable'], reverse=True):
            logger.info(f"      {mt}: {stats['total']} patterns, {stats['profitable']} profitables")
        logger.info("=" * 60)
        
        return {
            "total": len(self.patterns),
            "profitable": profitable,
            "strong_bets": strong_bets,
            "bets": bets,
            "by_market": by_market,
            "inserted": inserted
        }


# Nouveau main avec option --pro
if __name__ == "__main__":
    import sys
    
    if "--pro" in sys.argv:
        analyzer = ProPatternAnalyzer()
        analyzer.analyze_all_pro()
    elif "--advanced" in sys.argv:
        analyzer = AdvancedPatternAnalyzer()
        analyzer.analyze_all_advanced()
    else:
        analyzer = MarketPatternAnalyzer()
        analyzer.analyze_all()
