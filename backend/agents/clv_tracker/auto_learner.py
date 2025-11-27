#!/usr/bin/env python3
"""
🧠 AUTO-LEARNER - Système d'apprentissage automatique

Analyse les performances passées et génère des ajustements:
1. Calibration par score → ajuster si sur/sous-confiant
2. Performance par marché → coefficients par market_type
3. Performance par ligue → coefficients par league
4. Importance des facteurs → quels facteurs prédisent le mieux
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from decimal import Decimal
import json
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger('AutoLearner')

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
}


class AutoLearner:
    """Système d'auto-apprentissage pour amélioration continue"""
    
    MIN_SAMPLES = 3  # Minimum de picks pour calculer un ajustement
    
    def __init__(self):
        self.conn = None
        self.adjustments = {}
    
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
    
    # ============================================================
    # 1. CALIBRATION PAR SCORE
    # ============================================================
    
    def analyze_calibration(self, days: int = 60) -> dict:
        """
        Analyse la calibration: score prédit vs win rate réel
        
        Si score 70% mais win rate 55% → sur-confiant, ajustement = 0.79
        Si score 50% mais win rate 60% → sous-confiant, ajustement = 1.20
        """
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                FLOOR(diamond_score / 10) * 10 as score_bucket,
                COUNT(*) as total,
                AVG(diamond_score) as avg_predicted,
                AVG(CASE WHEN is_winner = true THEN 100.0 ELSE 0 END) as actual_rate,
                STDDEV(CASE WHEN is_winner = true THEN 100.0 ELSE 0 END) as std_dev
            FROM tracking_clv_picks
            WHERE is_resolved = true
            AND created_at > NOW() - INTERVAL '%s days'
            GROUP BY FLOOR(diamond_score / 10) * 10
            HAVING COUNT(*) >= %s
            ORDER BY score_bucket
        """, (days, self.MIN_SAMPLES))
        
        buckets = cur.fetchall()
        cur.close()
        conn.commit()
        
        calibration_data = []
        total_ece = 0
        total_weight = 0
        
        for b in buckets:
            predicted = self._float(b['avg_predicted'])
            actual = self._float(b['actual_rate'])
            total = int(b['total'])
            
            if predicted > 0:
                adjustment = actual / predicted
                adjustment = max(0.5, min(1.5, adjustment))  # Limiter entre 0.5 et 1.5
            else:
                adjustment = 1.0
            
            gap = predicted - actual
            ece_contrib = abs(gap) * total
            total_ece += ece_contrib
            total_weight += total
            
            calibration_data.append({
                'range': f"{int(b['score_bucket'])}-{int(b['score_bucket'])+9}",
                'predicted': round(predicted, 1),
                'actual': round(actual, 1),
                'gap': round(gap, 1),
                'adjustment': round(adjustment, 3),
                'samples': total,
                'confidence': 'high' if total >= 30 else 'medium' if total >= 15 else 'low',
                'status': '✅' if abs(gap) < 10 else '�� Sur-confiant' if gap > 0 else '📉 Sous-confiant'
            })
        
        ece = total_ece / total_weight if total_weight > 0 else 0
        
        return {
            'ece': round(ece, 2),
            'ece_status': '🎯 Excellent' if ece < 5 else '✅ Bon' if ece < 10 else '⚠️ À améliorer',
            'buckets': calibration_data,
            'recommendation': self._get_calibration_recommendation(calibration_data)
        }
    
    def _get_calibration_recommendation(self, data: list) -> str:
        over_confident = [d for d in data if d['gap'] > 10]
        under_confident = [d for d in data if d['gap'] < -10]
        
        if over_confident:
            ranges = ', '.join([d['range'] for d in over_confident])
            return f"Réduire les scores dans les ranges: {ranges}"
        elif under_confident:
            ranges = ', '.join([d['range'] for d in under_confident])
            return f"Augmenter les scores dans les ranges: {ranges}"
        return "Calibration satisfaisante"
    
    # ============================================================
    # 2. PERFORMANCE PAR MARCHÉ
    # ============================================================
    
    def analyze_by_market(self, days: int = 60) -> dict:
        """Analyse performance par type de marché"""
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                market_type,
                COUNT(*) as total,
                AVG(diamond_score) as avg_score,
                AVG(CASE WHEN is_winner = true THEN 100.0 ELSE 0 END) as win_rate,
                AVG(clv_percentage) as avg_clv,
                SUM(profit_loss) as profit,
                AVG(kelly_pct) as avg_kelly
            FROM tracking_clv_picks
            WHERE is_resolved = true
            AND created_at > NOW() - INTERVAL '%s days'
            GROUP BY market_type
            HAVING COUNT(*) >= %s
            ORDER BY AVG(CASE WHEN is_winner = true THEN 100.0 ELSE 0 END) DESC
        """, (days, self.MIN_SAMPLES))
        
        markets = cur.fetchall()
        cur.close()
        conn.commit()
        
        market_data = []
        for m in markets:
            avg_score = self._float(m['avg_score'])
            win_rate = self._float(m['win_rate'])
            
            # Calculer ajustement
            if avg_score > 0:
                adjustment = win_rate / avg_score
                adjustment = max(0.5, min(1.5, adjustment))
            else:
                adjustment = 1.0
            
            market_data.append({
                'market': m['market_type'],
                'total': int(m['total']),
                'avg_score': round(avg_score, 1),
                'win_rate': round(win_rate, 1),
                'avg_clv': round(self._float(m['avg_clv']), 2),
                'profit': round(self._float(m['profit']), 2),
                'adjustment': round(adjustment, 3),
                'status': '🔥' if win_rate >= 55 else '✅' if win_rate >= 45 else '⚠️'
            })
        
        return {
            'markets': market_data,
            'best_market': market_data[0]['market'] if market_data else None,
            'worst_market': market_data[-1]['market'] if market_data else None
        }
    
    # ============================================================
    # 3. PERFORMANCE PAR LIGUE
    # ============================================================
    
    def analyze_by_league(self, days: int = 60) -> dict:
        """Analyse performance par ligue"""
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                league,
                COUNT(*) as total,
                AVG(diamond_score) as avg_score,
                AVG(CASE WHEN is_winner = true THEN 100.0 ELSE 0 END) as win_rate,
                AVG(clv_percentage) as avg_clv,
                SUM(profit_loss) as profit
            FROM tracking_clv_picks
            WHERE is_resolved = true
            AND league IS NOT NULL AND league != ''
            AND created_at > NOW() - INTERVAL '%s days'
            GROUP BY league
            HAVING COUNT(*) >= %s
            ORDER BY AVG(CASE WHEN is_winner = true THEN 100.0 ELSE 0 END) DESC
        """, (days, self.MIN_SAMPLES))
        
        leagues = cur.fetchall()
        cur.close()
        conn.commit()
        
        league_data = []
        for l in leagues:
            avg_score = self._float(l['avg_score'])
            win_rate = self._float(l['win_rate'])
            
            if avg_score > 0:
                adjustment = win_rate / avg_score
                adjustment = max(0.5, min(1.5, adjustment))
            else:
                adjustment = 1.0
            
            league_data.append({
                'league': l['league'],
                'total': int(l['total']),
                'avg_score': round(avg_score, 1),
                'win_rate': round(win_rate, 1),
                'avg_clv': round(self._float(l['avg_clv']), 2),
                'profit': round(self._float(l['profit']), 2),
                'adjustment': round(adjustment, 3),
                'tier': 1 if win_rate >= 55 else 2 if win_rate >= 45 else 3
            })
        
        return {'leagues': league_data}
    
    # ============================================================
    # 4. ANALYSE TIMING (Edge Decay)
    # ============================================================
    
    def analyze_timing(self, days: int = 60) -> dict:
        """Analyse performance selon le timing"""
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                CASE 
                    WHEN hours_before_match > 48 THEN '48h+'
                    WHEN hours_before_match > 24 THEN '24-48h'
                    WHEN hours_before_match > 12 THEN '12-24h'
                    WHEN hours_before_match > 6 THEN '6-12h'
                    WHEN hours_before_match > 2 THEN '2-6h'
                    ELSE '<2h'
                END as timing,
                COUNT(*) as total,
                AVG(CASE WHEN is_winner = true THEN 100.0 ELSE 0 END) as win_rate,
                AVG(clv_percentage) as avg_clv
            FROM tracking_clv_picks
            WHERE is_resolved = true
            AND hours_before_match IS NOT NULL
            AND created_at > NOW() - INTERVAL '%s days'
            GROUP BY 
                CASE 
                    WHEN hours_before_match > 48 THEN '48h+'
                    WHEN hours_before_match > 24 THEN '24-48h'
                    WHEN hours_before_match > 12 THEN '12-24h'
                    WHEN hours_before_match > 6 THEN '6-12h'
                    WHEN hours_before_match > 2 THEN '2-6h'
                    ELSE '<2h'
                END
            HAVING COUNT(*) >= 5
        """, (days,))
        
        timing = cur.fetchall()
        cur.close()
        conn.commit()
        
        return {
            'timing_analysis': [
                {
                    'bucket': t['timing'],
                    'total': int(t['total']),
                    'win_rate': round(self._float(t['win_rate']), 1),
                    'avg_clv': round(self._float(t['avg_clv']), 2)
                }
                for t in timing
            ]
        }
    
    # ============================================================
    # 5. DÉTECTION BIAIS ET FAIBLESSES
    # ============================================================
    
    def detect_weaknesses(self, days: int = 60) -> list:
        """Détecte automatiquement les faiblesses du modèle"""
        weaknesses = []
        
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Marchés sous-performants
        cur.execute("""
            SELECT market_type, COUNT(*) as total,
                   AVG(CASE WHEN is_winner THEN 100.0 ELSE 0 END) as win_rate,
                   AVG(diamond_score) as avg_score
            FROM tracking_clv_picks
            WHERE is_resolved = true
            AND created_at > NOW() - INTERVAL '%s days'
            GROUP BY market_type
            HAVING COUNT(*) >= %s
            AND AVG(CASE WHEN is_winner THEN 100.0 ELSE 0 END) < 40
        """, (days, self.MIN_SAMPLES))
        
        for m in cur.fetchall():
            weaknesses.append({
                'type': 'market_underperforming',
                'severity': 'high' if self._float(m['win_rate']) < 35 else 'medium',
                'target': m['market_type'],
                'detail': f"WR: {round(self._float(m['win_rate']), 1)}% (score moyen: {round(self._float(m['avg_score']), 1)})",
                'action': f"Réduire scores de {m['market_type']} de {round((1 - self._float(m['win_rate'])/self._float(m['avg_score']))*100)}%"
            })
        
        # 2. Surconfiance (scores élevés, faible win rate)
        cur.execute("""
            SELECT COUNT(*) as total,
                   AVG(CASE WHEN is_winner THEN 100.0 ELSE 0 END) as win_rate,
                   AVG(diamond_score) as avg_score
            FROM tracking_clv_picks
            WHERE is_resolved = true
            AND diamond_score >= 75
            AND created_at > NOW() - INTERVAL '%s days'
        """, (days,))
        
        high_conf = cur.fetchone()
        if high_conf and int(high_conf['total'] or 0) >= self.MIN_SAMPLES:
            wr = self._float(high_conf['win_rate'])
            expected = self._float(high_conf['avg_score'])
            if wr < expected - 15:
                weaknesses.append({
                    'type': 'overconfidence',
                    'severity': 'high',
                    'target': 'scores >= 75',
                    'detail': f"WR: {round(wr, 1)}% au lieu de ~{round(expected, 1)}% attendu",
                    'action': "Réduire tous les scores de 10-15%"
                })
        
        # 3. CLV négatif
        cur.execute("""
            SELECT AVG(clv_percentage) as avg_clv
            FROM tracking_clv_picks
            WHERE clv_percentage IS NOT NULL
            AND created_at > NOW() - INTERVAL '%s days'
        """, (days,))
        
        clv = cur.fetchone()
        if clv and self._float(clv['avg_clv']) < -2:
            weaknesses.append({
                'type': 'negative_clv',
                'severity': 'high',
                'target': 'global',
                'detail': f"CLV moyen: {round(self._float(clv['avg_clv']), 2)}%",
                'action': "Tu prends des cotes inférieures à la closing - parier plus tôt ou chercher meilleures cotes"
            })
        
        cur.close()
        conn.commit()
        
        return weaknesses
    
    # ============================================================
    # 6. SAUVEGARDER AJUSTEMENTS
    # ============================================================
    
    def save_adjustments(self, days: int = 60):
        """Sauvegarde tous les ajustements dans la DB"""
        conn = self.get_db()
        cur = conn.cursor()
        
        logger.info("💾 Sauvegarde des ajustements...")
        
        # Créer/vérifier la table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tracking_model_adjustments (
                id SERIAL PRIMARY KEY,
                adjustment_type VARCHAR(50) NOT NULL,
                target VARCHAR(100) NOT NULL,
                adjustment_factor DECIMAL(6,4) DEFAULT 1.0,
                sample_size INTEGER,
                win_rate DECIMAL(5,2),
                avg_clv DECIMAL(6,4),
                confidence VARCHAR(20),
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(adjustment_type, target)
            )
        """)
        
        # Sauvegarder ajustements calibration
        calibration = self.analyze_calibration(days)
        for bucket in calibration['buckets']:
            cur.execute("""
                INSERT INTO tracking_model_adjustments 
                    (adjustment_type, target, adjustment_factor, sample_size, win_rate, confidence, updated_at)
                VALUES ('calibration', %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (adjustment_type, target) 
                DO UPDATE SET 
                    adjustment_factor = EXCLUDED.adjustment_factor,
                    sample_size = EXCLUDED.sample_size,
                    win_rate = EXCLUDED.win_rate,
                    confidence = EXCLUDED.confidence,
                    updated_at = NOW()
            """, (bucket['range'], bucket['adjustment'], bucket['samples'], bucket['actual'], bucket['confidence']))
        
        # Sauvegarder ajustements marché
        markets = self.analyze_by_market(days)
        for m in markets['markets']:
            cur.execute("""
                INSERT INTO tracking_model_adjustments 
                    (adjustment_type, target, adjustment_factor, sample_size, win_rate, avg_clv, updated_at)
                VALUES ('market', %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (adjustment_type, target) 
                DO UPDATE SET 
                    adjustment_factor = EXCLUDED.adjustment_factor,
                    sample_size = EXCLUDED.sample_size,
                    win_rate = EXCLUDED.win_rate,
                    avg_clv = EXCLUDED.avg_clv,
                    updated_at = NOW()
            """, (m['market'], m['adjustment'], m['total'], m['win_rate'], m['avg_clv']))
        
        # Sauvegarder ajustements ligue
        leagues = self.analyze_by_league(days)
        for l in leagues['leagues']:
            cur.execute("""
                INSERT INTO tracking_model_adjustments 
                    (adjustment_type, target, adjustment_factor, sample_size, win_rate, avg_clv, updated_at)
                VALUES ('league', %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (adjustment_type, target) 
                DO UPDATE SET 
                    adjustment_factor = EXCLUDED.adjustment_factor,
                    sample_size = EXCLUDED.sample_size,
                    win_rate = EXCLUDED.win_rate,
                    avg_clv = EXCLUDED.avg_clv,
                    updated_at = NOW()
            """, (l['league'], l['adjustment'], l['total'], l['win_rate'], l['avg_clv']))
        
        conn.commit()
        cur.close()
        
        logger.info("✅ Ajustements sauvegardés")
    
    # ============================================================
    # 7. RAPPORT COMPLET
    # ============================================================
    
    def run_full_analysis(self, days: int = 60) -> dict:
        """Exécute l'analyse complète et génère un rapport"""
        logger.info(f"🧠 Auto-Learning Analysis ({days} jours)...")
        
        calibration = self.analyze_calibration(days)
        markets = self.analyze_by_market(days)
        leagues = self.analyze_by_league(days)
        timing = self.analyze_timing(days)
        weaknesses = self.detect_weaknesses(days)
        
        # Sauvegarder
        self.save_adjustments(days)
        
        # Score de santé
        health = 100
        health -= len([w for w in weaknesses if w['severity'] == 'high']) * 15
        health -= len([w for w in weaknesses if w['severity'] == 'medium']) * 5
        health -= max(0, calibration['ece'] - 5) * 2
        health = max(0, min(100, health))
        
        return {
            'calibration': calibration,
            'markets': markets,
            'leagues': leagues,
            'timing': timing,
            'weaknesses': weaknesses,
            'health_score': health,
            'health_status': '🟢 Excellent' if health >= 80 else '🟡 Bon' if health >= 60 else '🔴 À améliorer'
        }


def main():
    learner = AutoLearner()
    
    report = learner.run_full_analysis(60)
    
    print("\n" + "=" * 60)
    print("🧠 AUTO-LEARNING REPORT")
    print("=" * 60)
    
    print(f"\n📊 CALIBRATION (ECE: {report['calibration']['ece']}% - {report['calibration']['ece_status']})")
    for b in report['calibration']['buckets'][:5]:
        print(f"   {b['range']}: {b['predicted']}% prédit → {b['actual']}% réel | adj: {b['adjustment']}")
    
    print(f"\n🎯 TOP MARCHÉS:")
    for m in report['markets']['markets'][:5]:
        print(f"   {m['status']} {m['market']}: {m['win_rate']}% WR | CLV: {m['avg_clv']}%")
    
    print(f"\n⚠️ FAIBLESSES DÉTECTÉES: {len(report['weaknesses'])}")
    for w in report['weaknesses']:
        print(f"   [{w['severity'].upper()}] {w['target']}: {w['detail']}")
        print(f"      → {w['action']}")
    
    print(f"\n💚 SANTÉ DU MODÈLE: {report['health_score']}/100 {report['health_status']}")
    print("=" * 60)
    
    learner.close()


if __name__ == "__main__":
    main()
