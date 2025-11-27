#!/usr/bin/env python3
"""
📊 CLV CALCULATOR - Calcul automatique du Closing Line Value

Le CLV est LE MEILLEUR indicateur de succès long-terme:
- CLV > 0% = tu bats le marché
- CLV > 2% = excellent
- CLV > 5% = niveau professionnel

CLV = (odds_taken / closing_odds - 1) * 100

Exemple:
- Tu prends 2.10 sur Over 2.5
- La ligne close à 1.90
- CLV = (2.10 / 1.90 - 1) * 100 = +10.5% 🔥
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger('CLV_Calculator')

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
}


class CLVCalculator:
    """Calcule et met à jour le CLV pour tous les picks"""
    
    def __init__(self):
        self.conn = None
        self.stats = {'updated': 0, 'errors': 0}
    
    def get_db(self):
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
        return self.conn
    
    def close(self):
        if self.conn and not self.conn.closed:
            self.conn.close()
    
    def _float(self, v, default=0.0):
        if v is None:
            return default
        if isinstance(v, Decimal):
            return float(v)
        try:
            return float(v)
        except:
            return default
    
    def get_closing_odds_1x2(self, match_id: str, market_type: str) -> float:
        """Récupère la closing odds pour marchés 1X2"""
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Mapper market_type vers colonne
        col_map = {
            'home': 'home_odds',
            'draw': 'draw_odds', 
            'away': 'away_odds'
        }
        
        col = col_map.get(market_type)
        if not col:
            return 0
        
        # Dernière cote avant le match (Pinnacle = sharp)
        cur.execute(f"""
            SELECT {col} as closing_odds
            FROM odds_history
            WHERE match_id = %s
            AND {col} IS NOT NULL
            AND bookmaker ILIKE '%pinnacle%'
            ORDER BY collected_at DESC
            LIMIT 1
        """, (match_id,))
        
        result = cur.fetchone()
        
        if not result:
            # Fallback: moyenne des dernières cotes
            cur.execute(f"""
                SELECT AVG({col}) as closing_odds
                FROM (
                    SELECT {col}
                    FROM odds_history
                    WHERE match_id = %s AND {col} IS NOT NULL
                    ORDER BY collected_at DESC
                    LIMIT 5
                ) sub
            """, (match_id,))
            result = cur.fetchone()
        
        cur.close()
        conn.commit()
        
        return self._float(result['closing_odds']) if result else 0
    
    def get_closing_odds_totals(self, match_id: str, market_type: str) -> float:
        """Récupère la closing odds pour Over/Under"""
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Extraire la ligne
        line_map = {
            'over_15': 1.5, 'under_15': 1.5,
            'over_25': 2.5, 'under_25': 2.5,
            'over_35': 3.5, 'under_35': 3.5,
        }
        
        line = line_map.get(market_type)
        if not line:
            return 0
        
        is_over = 'over' in market_type
        col = 'over_odds' if is_over else 'under_odds'
        
        # Dernière cote (Pinnacle prioritaire)
        cur.execute(f"""
            SELECT {col} as closing_odds
            FROM odds_totals
            WHERE match_id = %s AND line = %s
            AND bookmaker ILIKE '%pinnacle%'
            ORDER BY collected_at DESC
            LIMIT 1
        """, (match_id, line))
        
        result = cur.fetchone()
        
        if not result:
            cur.execute(f"""
                SELECT AVG({col}) as closing_odds
                FROM (
                    SELECT {col}
                    FROM odds_totals
                    WHERE match_id = %s AND line = %s AND {col} IS NOT NULL
                    ORDER BY collected_at DESC
                    LIMIT 5
                ) sub
            """, (match_id, line))
            result = cur.fetchone()
        
        cur.close()
        conn.commit()
        
        return self._float(result['closing_odds']) if result else 0
    
    def calculate_clv(self, odds_taken: float, closing_odds: float) -> float:
        """
        CLV = (odds_taken / closing_odds - 1) * 100
        
        Positif = tu as pris une meilleure cote que la closing
        Négatif = tu as pris une moins bonne cote
        """
        if not closing_odds or closing_odds <= 0 or not odds_taken:
            return 0
        return (odds_taken / closing_odds - 1) * 100
    
    def update_all_clv(self) -> dict:
        """Met à jour le CLV pour tous les picks résolus"""
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        logger.info("🔄 Calcul CLV pour tous les picks...")
        
        # Picks avec match terminé (commence_time passé)
        cur.execute("""
            SELECT id, match_id, market_type, odds_taken
            FROM tracking_clv_picks
            WHERE odds_taken > 0
            AND (clv_percentage IS NULL OR closing_odds IS NULL)
            AND commence_time < NOW() - INTERVAL '2 hours'
        """)
        
        picks = cur.fetchall()
        logger.info(f"📋 {len(picks)} picks à calculer")
        
        updated = 0
        total_clv = 0
        
        for pick in picks:
            try:
                market = pick['market_type']
                
                # Récupérer closing odds selon le type de marché
                if market in ('home', 'draw', 'away'):
                    closing = self.get_closing_odds_1x2(pick['match_id'], market)
                elif 'over' in market or 'under' in market:
                    closing = self.get_closing_odds_totals(pick['match_id'], market)
                else:
                    # Double chance et autres: estimer
                    closing = 0
                
                if closing > 0:
                    clv = self.calculate_clv(self._float(pick['odds_taken']), closing)
                    
                    # Calculer odds_movement
                    movement = closing - self._float(pick['odds_taken'])
                    
                    cur.execute("""
                        UPDATE tracking_clv_picks
                        SET closing_odds = %s, 
                            clv_percentage = %s,
                            odds_movement = %s
                        WHERE id = %s
                    """, (closing, round(clv, 4), round(movement, 4), pick['id']))
                    
                    updated += 1
                    total_clv += clv
                    
            except Exception as e:
                logger.debug(f"CLV error for {pick['id']}: {e}")
                self.stats['errors'] += 1
        
        conn.commit()
        cur.close()
        
        avg_clv = total_clv / updated if updated > 0 else 0
        
        self.stats['updated'] = updated
        
        logger.info(f"✅ CLV calculé: {updated} picks | Avg CLV: {avg_clv:.2f}%")
        
        return {
            'updated': updated,
            'avg_clv': round(avg_clv, 2),
            'status': '🔥 Excellent' if avg_clv > 2 else '✅ Bon' if avg_clv > 0 else '⚠️ Négatif'
        }
    
    def get_clv_report(self, days: int = 30) -> dict:
        """Génère un rapport CLV complet"""
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Stats globales
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE clv_percentage IS NOT NULL) as with_clv,
                AVG(clv_percentage) as avg_clv,
                AVG(clv_percentage) FILTER (WHERE is_winner = true) as clv_winners,
                AVG(clv_percentage) FILTER (WHERE is_winner = false) as clv_losers,
                COUNT(*) FILTER (WHERE clv_percentage > 0) as positive_clv,
                COUNT(*) FILTER (WHERE clv_percentage > 2) as excellent_clv,
                COUNT(*) FILTER (WHERE clv_percentage > 5) as pro_clv
            FROM tracking_clv_picks
            WHERE created_at > NOW() - INTERVAL '%s days'
            AND is_resolved = true
        """, (days,))
        
        stats = cur.fetchone()
        
        # CLV par marché
        cur.execute("""
            SELECT 
                market_type,
                COUNT(*) as total,
                AVG(clv_percentage) as avg_clv,
                AVG(CASE WHEN is_winner THEN 100.0 ELSE 0 END) as win_rate
            FROM tracking_clv_picks
            WHERE clv_percentage IS NOT NULL
            AND created_at > NOW() - INTERVAL '%s days'
            GROUP BY market_type
            HAVING COUNT(*) >= 5
            ORDER BY AVG(clv_percentage) DESC
        """, (days,))
        
        by_market = cur.fetchall()
        
        # CLV par range de score
        cur.execute("""
            SELECT 
                CASE 
                    WHEN diamond_score >= 80 THEN '80+'
                    WHEN diamond_score >= 70 THEN '70-79'
                    WHEN diamond_score >= 60 THEN '60-69'
                    ELSE '<60'
                END as score_range,
                COUNT(*) as total,
                AVG(clv_percentage) as avg_clv,
                AVG(CASE WHEN is_winner THEN 100.0 ELSE 0 END) as win_rate
            FROM tracking_clv_picks
            WHERE clv_percentage IS NOT NULL
            AND created_at > NOW() - INTERVAL '%s days'
            GROUP BY 
                CASE 
                    WHEN diamond_score >= 80 THEN '80+'
                    WHEN diamond_score >= 70 THEN '70-79'
                    WHEN diamond_score >= 60 THEN '60-69'
                    ELSE '<60'
                END
            ORDER BY score_range DESC
        """, (days,))
        
        by_score = cur.fetchall()
        
        cur.close()
        
        total = int(stats['total'] or 0)
        with_clv = int(stats['with_clv'] or 0)
        positive = int(stats['positive_clv'] or 0)
        
        return {
            'period': f'{days} jours',
            'total_resolved': total,
            'with_clv': with_clv,
            'avg_clv': round(self._float(stats['avg_clv']), 2),
            'clv_winners': round(self._float(stats['clv_winners']), 2),
            'clv_losers': round(self._float(stats['clv_losers']), 2),
            'edge_indicator': round(self._float(stats['clv_winners']) - self._float(stats['clv_losers']), 2),
            'positive_clv_pct': round(positive / with_clv * 100, 1) if with_clv > 0 else 0,
            'excellent_clv': int(stats['excellent_clv'] or 0),
            'pro_level_clv': int(stats['pro_clv'] or 0),
            'by_market': [dict(m) for m in by_market],
            'by_score': [dict(s) for s in by_score]
        }


def main():
    calc = CLVCalculator()
    
    # Mettre à jour tous les CLV
    result = calc.update_all_clv()
    print(f"\n📊 CLV Update: {result}")
    
    # Générer rapport
    report = calc.get_clv_report()
    print(f"\n📈 CLV Report:")
    print(f"   Avg CLV: {report['avg_clv']}%")
    print(f"   Positive CLV: {report['positive_clv_pct']}%")
    print(f"   CLV Winners vs Losers: {report['clv_winners']}% vs {report['clv_losers']}%")
    print(f"   Edge Indicator: {report['edge_indicator']}%")
    
    calc.close()


if __name__ == "__main__":
    main()
