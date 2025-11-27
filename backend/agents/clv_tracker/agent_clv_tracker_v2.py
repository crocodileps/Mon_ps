#!/usr/bin/env python3
"""
🎯 AGENT CLV TRACKER V2.0 - VERSION AVANCÉE
Agent intelligent de tracking et analyse des prédictions

AMÉLIORATIONS V2:
- Anti-doublons intelligent (vérifie AVANT d'appeler l'API)
- Cache des matchs déjà analysés
- Analyses statistiques avancées (calibration, edge decay, biais)
- Détection automatique des faiblesses du modèle
- Suggestions d'amélioration
- Rapport quotidien complet
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from decimal import Decimal
import requests
import json
import logging
import os
from typing import Optional, Dict, List, Tuple
from collections import defaultdict

# Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
}

API_BASE = os.getenv('API_BASE', 'http://localhost:8001')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('AgentCLVTrackerV2')


class AgentCLVTrackerV2:
    """Agent CLV Tracker V2 - Version avancée avec optimisations"""
    
    VERSION = "2.0"
    
    # Mapping des marchés pour résolution
    MARKET_RESOLVERS = {
        'btts_yes': lambda h, a, o: h > 0 and a > 0,
        'btts_no': lambda h, a, o: h == 0 or a == 0,
        'over15': lambda h, a, o: (h + a) > 1,
        'under15': lambda h, a, o: (h + a) < 2,
        'over25': lambda h, a, o: (h + a) > 2,
        'under25': lambda h, a, o: (h + a) < 3,
        'over35': lambda h, a, o: (h + a) > 3,
        'under35': lambda h, a, o: (h + a) < 4,
        'dc_1x': lambda h, a, o: o in ('home', 'draw'),
        'dc_x2': lambda h, a, o: o in ('draw', 'away'),
        'dc_12': lambda h, a, o: o in ('home', 'away'),
        'dnb_home': lambda h, a, o: o == 'home' if o != 'draw' else None,
        'dnb_away': lambda h, a, o: o == 'away' if o != 'draw' else None,
    }
    
    def __init__(self):
        self.conn = None
        self.tracked_matches = set()  # Cache des matchs déjà trackés
        self.stats = {
            'skipped_duplicates': 0,
            'new_tracks': 0,
            'resolved': 0,
            'errors': 0
        }
    
    def get_db(self):
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
        return self.conn
    
    def close(self):
        if self.conn and not self.conn.closed:
            self.conn.close()
    
    # ============================================================
    # ANTI-DOUBLONS INTELLIGENT
    # ============================================================
    
    def load_tracked_matches(self):
        """Charge en cache tous les matchs déjà trackés"""
        conn = self.get_db()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT DISTINCT match_id 
            FROM tracking_clv_picks 
            WHERE match_id IS NOT NULL
        """)
        
        self.tracked_matches = {row[0] for row in cur.fetchall()}
        logger.info(f"📦 Cache: {len(self.tracked_matches)} matchs déjà trackés")
        cur.close()
    
    def is_already_tracked(self, match_id: str) -> bool:
        """Vérifie si un match est déjà tracké (sans requête DB)"""
        return match_id in self.tracked_matches
    
    # ============================================================
    # COLLECT - Récupération intelligente
    # ============================================================
    
    def get_opportunities_to_track(self) -> List[dict]:
        """
        Récupère UNIQUEMENT les matchs non encore trackés
        Évite les appels API inutiles
        """
        try:
            response = requests.get(
                f"{API_BASE}/opportunities/opportunities/",
                params={'limit': 100},
                timeout=30
            )
            
            if not response.ok:
                logger.error(f"API opportunities error: {response.status_code}")
                return []
            
            all_opportunities = response.json()
            if not isinstance(all_opportunities, list):
                return []
            
            # Filtrer: garder uniquement les non-trackés
            new_opportunities = [
                opp for opp in all_opportunities
                if opp.get('match_id') and not self.is_already_tracked(opp['match_id'])
            ]
            
            skipped = len(all_opportunities) - len(new_opportunities)
            self.stats['skipped_duplicates'] += skipped
            
            logger.info(f"📋 {len(new_opportunities)} nouveaux matchs à tracker (/{len(all_opportunities)} total, {skipped} déjà trackés)")
            
            return new_opportunities
            
        except Exception as e:
            logger.error(f"Erreur get_opportunities: {e}")
            return []
    
    # ============================================================
    # TRACK - Enregistrement des analyses
    # ============================================================
    
    def analyze_and_track(self, match_id: str, league: str = None) -> int:
        """
        Analyse un match et enregistre tous ses marchés
        Retourne le nombre de marchés créés
        """
        try:
            # Appeler l'API d'analyse
            response = requests.get(
                f"{API_BASE}/patron-diamond/analyze/{match_id}",
                timeout=30
            )
            
            if not response.ok:
                return 0
            
            analysis = response.json()
            if not analysis or 'match_id' not in analysis:
                return 0
            
            return self._save_all_markets(analysis, league)
            
        except Exception as e:
            logger.error(f"Erreur analyze_and_track {match_id}: {e}")
            self.stats['errors'] += 1
            return 0
    
    def _save_all_markets(self, analysis: dict, league: str = None) -> int:
        """Sauvegarde tous les 13 marchés d'une analyse"""
        conn = self.get_db()
        cur = conn.cursor()
        
        match_id = analysis['match_id']
        home_team = analysis.get('home_team', '')
        away_team = analysis.get('away_team', '')
        poisson = analysis.get('poisson', {})
        
        # Extraction des données xG
        home_xg = poisson.get('home_xg', 0)
        away_xg = poisson.get('away_xg', 0)
        total_xg = poisson.get('total_xg', 0)
        
        # Collecter tous les marchés
        markets_data = self._extract_all_markets(analysis, poisson)
        
        created = 0
        for market in markets_data:
            try:
                cur.execute("""
                    INSERT INTO tracking_clv_picks (
                        match_id, home_team, away_team, league, match_name,
                        market_type, prediction, odds_taken, probability,
                        kelly_pct, diamond_score, value_rating, recommendation,
                        factors, is_top3, source,
                        home_xg, away_xg, total_xg, poisson_prob, predicted_prob
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                    ON CONFLICT DO NOTHING
                """, (
                    match_id, home_team, away_team, league or '',
                    f"{home_team} vs {away_team}",
                    market['key'], market['prediction'],
                    market['odds'], market['probability'],
                    market['kelly'], market['score'],
                    market['value_rating'], market['recommendation'],
                    json.dumps(market.get('factors', {})),
                    market['score'] >= 70,
                    'agent_clv_v2',
                    home_xg, away_xg, total_xg,
                    market['poisson_prob'],
                    market['score'] / 100 if market['score'] else 0
                ))
                
                if cur.rowcount > 0:
                    created += 1
                    
            except Exception as e:
                logger.warning(f"Erreur insert {market['key']}: {e}")
                conn.rollback()
        
        conn.commit()
        cur.close()
        
        # Ajouter au cache
        self.tracked_matches.add(match_id)
        self.stats['new_tracks'] += created
        
        return created
    
    def _extract_all_markets(self, analysis: dict, poisson: dict) -> List[dict]:
        """Extrait les 13 marchés d'une analyse"""
        markets = []
        
        # BTTS Yes
        btts = analysis.get('btts', {})
        if btts.get('score') is not None:
            markets.append({
                'key': 'btts_yes',
                'prediction': 'yes',
                'score': int(btts.get('score', 0)),
                'odds': float(btts.get('odds', 0) or 0),
                'probability': float(btts.get('probability', 0) or 0),
                'poisson_prob': float(poisson.get('btts_prob', 0) or 0),
                'kelly': float(btts.get('kelly_pct', 0) or 0),
                'value_rating': btts.get('value_rating', ''),
                'recommendation': btts.get('recommendation', ''),
                'factors': btts.get('factors', {})
            })
        
        # BTTS No
        btts_no = analysis.get('btts_no', {})
        if btts_no.get('score') is not None:
            markets.append({
                'key': 'btts_no',
                'prediction': 'no',
                'score': int(btts_no.get('score', 0)),
                'odds': float(btts_no.get('odds', 0) or 0),
                'probability': float(btts_no.get('probability', 0) or 0),
                'poisson_prob': float(poisson.get('btts_no_prob', 0) or 0),
                'kelly': float(btts_no.get('kelly_pct', 0) or 0),
                'value_rating': btts_no.get('value_rating', ''),
                'recommendation': btts_no.get('recommendation', ''),
                'factors': btts_no.get('factors', {})
            })
        
        # Over/Under markets
        for market_name in ['over15', 'under15', 'over25', 'under25', 'over35', 'under35']:
            market = analysis.get(market_name, {})
            if market.get('score') is not None:
                prob_key = f"{market_name}_prob"
                markets.append({
                    'key': market_name,
                    'prediction': 'over' if 'over' in market_name else 'under',
                    'score': int(market.get('score', 0)),
                    'odds': float(market.get('odds', 0) or 0),
                    'probability': float(market.get('probability', 0) or 0),
                    'poisson_prob': float(poisson.get(prob_key, 0) or 0),
                    'kelly': float(market.get('kelly_pct', 0) or 0),
                    'value_rating': market.get('value_rating', ''),
                    'recommendation': market.get('recommendation', ''),
                    'factors': market.get('factors', {})
                })
        
        # Double Chance
        dc = analysis.get('double_chance', {})
        dc_poisson = poisson.get('double_chance', {})
        for dc_key in ['1x', 'x2', '12']:
            dc_market = dc.get(dc_key, {})
            if dc_market.get('score') is not None:
                markets.append({
                    'key': f'dc_{dc_key}',
                    'prediction': dc_key,
                    'score': int(dc_market.get('score', 0)),
                    'odds': float(dc_market.get('odds', 0) or 0),
                    'probability': float(dc_market.get('probability', 0) or 0),
                    'poisson_prob': float(dc_poisson.get(dc_key, 0) or 0),
                    'kelly': float(dc_market.get('kelly_pct', 0) or 0),
                    'value_rating': dc_market.get('value_rating', ''),
                    'recommendation': dc_market.get('recommendation', ''),
                    'factors': dc_market.get('factors', {})
                })
        
        # Draw No Bet
        dnb = analysis.get('draw_no_bet', {})
        dnb_poisson = poisson.get('draw_no_bet', {})
        for dnb_key in ['home', 'away']:
            dnb_market = dnb.get(dnb_key, {})
            if dnb_market.get('score') is not None:
                markets.append({
                    'key': f'dnb_{dnb_key}',
                    'prediction': dnb_key,
                    'score': int(dnb_market.get('score', 0)),
                    'odds': float(dnb_market.get('odds', 0) or 0),
                    'probability': float(dnb_market.get('probability', 0) or 0),
                    'poisson_prob': float(dnb_poisson.get(dnb_key, 0) or 0),
                    'kelly': float(dnb_market.get('kelly_pct', 0) or 0),
                    'value_rating': dnb_market.get('value_rating', ''),
                    'recommendation': dnb_market.get('recommendation', ''),
                    'factors': dnb_market.get('factors', {})
                })
        
        return markets
    
    # ============================================================
    # RESOLVE - Résolution intelligente des picks
    # ============================================================
    
    def resolve_all_pending(self) -> dict:
        """Résout tous les picks en attente avec résultats disponibles"""
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Récupérer picks non résolus
        cur.execute("""
            SELECT p.id, p.match_id, p.market_type, p.odds_taken, p.stake,
                   p.diamond_score, p.predicted_prob
            FROM tracking_clv_picks p
            WHERE p.is_resolved = false 
            AND p.match_id IS NOT NULL
        """)
        pending = cur.fetchall()
        
        if not pending:
            logger.info("✅ Aucun pick à résoudre")
            return {'resolved': 0, 'wins': 0, 'losses': 0, 'pushes': 0}
        
        logger.info(f"🔄 {len(pending)} picks à résoudre")
        
        # Grouper par match_id pour optimiser les requêtes
        picks_by_match = defaultdict(list)
        for pick in pending:
            picks_by_match[pick['match_id']].append(pick)
        
        results = {'resolved': 0, 'wins': 0, 'losses': 0, 'pushes': 0}
        
        for match_id, picks in picks_by_match.items():
            # Récupérer le résultat du match
            cur.execute("""
                SELECT score_home, score_away, outcome, is_finished
                FROM match_results
                WHERE match_id = %s AND is_finished = true
            """, (match_id,))
            result = cur.fetchone()
            
            if not result:
                continue
            
            home = result['score_home']
            away = result['score_away']
            outcome = result['outcome']
            
            for pick in picks:
                market_type = pick['market_type']
                resolver = self.MARKET_RESOLVERS.get(market_type)
                
                if not resolver:
                    continue
                
                is_winner = resolver(home, away, outcome)
                
                if is_winner is None:  # Push (DNB avec nul)
                    profit = 0
                    results['pushes'] += 1
                elif is_winner:
                    stake = float(pick['stake'] or 1)
                    odds = float(pick['odds_taken'] or 1)
                    profit = stake * (odds - 1)
                    results['wins'] += 1
                else:
                    profit = -float(pick['stake'] or 1)
                    results['losses'] += 1
                
                # Mettre à jour
                cur.execute("""
                    UPDATE tracking_clv_picks
                    SET is_resolved = true, is_winner = %s, profit_loss = %s,
                        score_home = %s, score_away = %s, resolved_at = NOW()
                    WHERE id = %s
                """, (is_winner, profit, home, away, pick['id']))
                
                results['resolved'] += 1
        
        conn.commit()
        cur.close()
        self.stats['resolved'] += results['resolved']
        
        return results
    
    # ============================================================
    # ANALYSE AVANCÉE - Calibration & Performance
    # ============================================================
    
    def analyze_calibration(self, days: int = 30) -> dict:
        """
        Analyse la calibration du modèle
        Compare le score prédit vs le taux de réussite réel
        ECE = Expected Calibration Error
        """
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                FLOOR(diamond_score / 10) * 10 as bucket,
                COUNT(*) as total,
                AVG(diamond_score) as avg_predicted,
                AVG(CASE WHEN is_winner = true THEN 100.0 ELSE 0 END) as actual_rate
            FROM tracking_clv_picks
            WHERE is_resolved = true
            AND created_at > NOW() - INTERVAL '%s days'
            GROUP BY FLOOR(diamond_score / 10) * 10
            HAVING COUNT(*) >= 3
            ORDER BY bucket
        """, (days,))
        
        buckets = cur.fetchall()
        cur.close()
        
        if not buckets:
            return {'ece': 0, 'buckets': [], 'status': 'insufficient_data'}
        
        # Calculer ECE
        total_samples = sum(int(b['total']) for b in buckets)
        ece = 0
        
        calibration_data = []
        for b in buckets:
            predicted = float(b['avg_predicted'] or 0)
            actual = float(b['actual_rate'] or 0)
            gap = abs(predicted - actual)
            weight = int(b['total']) / total_samples
            ece += weight * gap
            
            calibration_data.append({
                'range': f"{int(b['bucket'])}-{int(b['bucket'])+10}%",
                'predicted': round(predicted, 1),
                'actual': round(actual, 1),
                'gap': round(gap, 1),
                'samples': int(b['total']),
                'status': 'good' if gap < 10 else 'overconfident' if predicted > actual else 'underconfident'
            })
        
        # Interprétation
        if ece < 5:
            status = "�� Excellente calibration"
        elif ece < 10:
            status = "✅ Bonne calibration"
        elif ece < 15:
            status = "⚠️ Calibration moyenne - ajustements recommandés"
        else:
            status = "❌ Mauvaise calibration - révision nécessaire"
        
        return {
            'ece': round(ece, 2),
            'status': status,
            'buckets': calibration_data,
            'recommendation': self._get_calibration_recommendation(calibration_data)
        }
    
    def _get_calibration_recommendation(self, calibration_data: list) -> str:
        """Génère des recommandations basées sur la calibration"""
        overconfident = [b for b in calibration_data if b['status'] == 'overconfident']
        underconfident = [b for b in calibration_data if b['status'] == 'underconfident']
        
        recommendations = []
        
        if overconfident:
            ranges = [b['range'] for b in overconfident]
            recommendations.append(f"Réduire les scores dans les tranches {', '.join(ranges)}")
        
        if underconfident:
            ranges = [b['range'] for b in underconfident]
            recommendations.append(f"Augmenter les scores dans les tranches {', '.join(ranges)}")
        
        if not recommendations:
            return "Modèle bien calibré, pas d'ajustement nécessaire"
        
        return "; ".join(recommendations)
    
    def analyze_by_market(self, days: int = 30) -> List[dict]:
        """Analyse les performances par type de marché"""
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                market_type,
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE is_winner = true) as wins,
                AVG(CASE WHEN is_winner = true THEN 100.0 ELSE 0 END) as win_rate,
                AVG(diamond_score) as avg_score,
                SUM(profit_loss) as total_profit,
                AVG(profit_loss) as avg_profit
            FROM tracking_clv_picks
            WHERE is_resolved = true
            AND created_at > NOW() - INTERVAL '%s days'
            GROUP BY market_type
            HAVING COUNT(*) >= 5
            ORDER BY AVG(CASE WHEN is_winner = true THEN 100.0 ELSE 0 END) DESC
        """, (days,))
        
        markets = cur.fetchall()
        cur.close()
        
        return [
            {
                'market': m['market_type'],
                'total': int(m['total']),
                'wins': int(m['wins']),
                'win_rate': round(float(m['win_rate'] or 0), 1),
                'avg_score': round(float(m['avg_score'] or 0), 1),
                'profit': round(float(m['total_profit'] or 0), 2),
                'roi': round(float(m['total_profit'] or 0) / int(m['total']) * 100, 1) if m['total'] else 0,
                'status': '🔥' if float(m['win_rate'] or 0) >= 55 else '✅' if float(m['win_rate'] or 0) >= 45 else '⚠️'
            }
            for m in markets
        ]
    
    def detect_weaknesses(self, days: int = 30) -> List[dict]:
        """Détecte les faiblesses systématiques du modèle"""
        weaknesses = []
        
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Marchés sous-performants (< 40% win rate)
        cur.execute("""
            SELECT market_type, COUNT(*) as total,
                   AVG(CASE WHEN is_winner = true THEN 100.0 ELSE 0 END) as win_rate,
                   AVG(diamond_score) as avg_score
            FROM tracking_clv_picks
            WHERE is_resolved = true AND created_at > NOW() - INTERVAL '%s days'
            GROUP BY market_type
            HAVING COUNT(*) >= 10 AND AVG(CASE WHEN is_winner = true THEN 100.0 ELSE 0 END) < 40
        """, (days,))
        
        for m in cur.fetchall():
            weaknesses.append({
                'type': 'underperforming_market',
                'severity': 'high',
                'market': m['market_type'],
                'win_rate': round(float(m['win_rate']), 1),
                'avg_score': round(float(m['avg_score']), 1),
                'samples': int(m['total']),
                'action': f"Réduire le score de {m['market_type']} de 10-15% ou exclure temporairement"
            })
        
        # 2. Overconfidence globale (score >= 70 mais win rate < 60%)
        cur.execute("""
            SELECT COUNT(*) as total,
                   AVG(CASE WHEN is_winner = true THEN 100.0 ELSE 0 END) as win_rate
            FROM tracking_clv_picks
            WHERE is_resolved = true AND diamond_score >= 70
            AND created_at > NOW() - INTERVAL '%s days'
        """, (days,))
        
        high_conf = cur.fetchone()
        if high_conf and int(high_conf['total'] or 0) >= 20:
            win_rate = float(high_conf['win_rate'] or 0)
            if win_rate < 60:
                weaknesses.append({
                    'type': 'overconfidence',
                    'severity': 'high',
                    'expected': 70,
                    'actual': round(win_rate, 1),
                    'samples': int(high_conf['total']),
                    'action': "Réduire tous les scores de 5-10% ou augmenter le seuil de confiance"
                })
        
        # 3. Leagues problématiques
        cur.execute("""
            SELECT league, COUNT(*) as total,
                   AVG(CASE WHEN is_winner = true THEN 100.0 ELSE 0 END) as win_rate
            FROM tracking_clv_picks
            WHERE is_resolved = true AND league IS NOT NULL AND league != ''
            AND created_at > NOW() - INTERVAL '%s days'
            GROUP BY league
            HAVING COUNT(*) >= 10 AND AVG(CASE WHEN is_winner = true THEN 100.0 ELSE 0 END) < 35
        """, (days,))
        
        for l in cur.fetchall():
            weaknesses.append({
                'type': 'league_weakness',
                'severity': 'medium',
                'league': l['league'],
                'win_rate': round(float(l['win_rate']), 1),
                'samples': int(l['total']),
                'action': f"Appliquer un malus de -10% pour la ligue {l['league']}"
            })
        
        cur.close()
        
        return weaknesses
    
    # ============================================================
    # RAPPORT COMPLET
    # ============================================================
    
    def generate_daily_report(self, days: int = 7) -> dict:
        """Génère un rapport complet d'analyse"""
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Stats globales
        cur.execute("""
            SELECT 
                COUNT(*) as total_picks,
                COUNT(*) FILTER (WHERE is_resolved) as resolved,
                COUNT(*) FILTER (WHERE is_winner = true) as wins,
                COUNT(*) FILTER (WHERE is_winner = false) as losses,
                SUM(profit_loss) FILTER (WHERE is_resolved) as total_profit,
                AVG(diamond_score) as avg_score
            FROM tracking_clv_picks
            WHERE created_at > NOW() - INTERVAL '%s days'
        """, (days,))
        
        global_stats = cur.fetchone()
        cur.close()
        
        resolved = int(global_stats['resolved'] or 0)
        wins = int(global_stats['wins'] or 0)
        
        report = {
            'period': f"Derniers {days} jours",
            'generated_at': datetime.now().isoformat(),
            'global': {
                'total_picks': int(global_stats['total_picks'] or 0),
                'resolved': resolved,
                'pending': int(global_stats['total_picks'] or 0) - resolved,
                'wins': wins,
                'losses': int(global_stats['losses'] or 0),
                'win_rate': round(wins / resolved * 100, 1) if resolved > 0 else 0,
                'profit': round(float(global_stats['total_profit'] or 0), 2),
                'avg_score': round(float(global_stats['avg_score'] or 0), 1)
            },
            'calibration': self.analyze_calibration(days),
            'by_market': self.analyze_by_market(days),
            'weaknesses': self.detect_weaknesses(days),
            'health_score': 0  # Calculé ci-dessous
        }
        
        # Calculer le score de santé du modèle
        health = 100
        health -= len(report['weaknesses']) * 15
        health -= max(0, report['calibration']['ece'] - 5) * 2
        if resolved > 0 and report['global']['win_rate'] < 45:
            health -= 20
        
        report['health_score'] = max(0, min(100, health))
        
        return report
    
    # ============================================================
    # EXÉCUTION
    # ============================================================
    
    def run_collect(self):
        """Phase 1: Collecte et tracking des nouveaux matchs"""
        logger.info("=" * 60)
        logger.info("🚀 AGENT CLV TRACKER V2 - COLLECT")
        logger.info("=" * 60)
        
        self.load_tracked_matches()
        
        opportunities = self.get_opportunities_to_track()
        
        for opp in opportunities:
            match_id = opp.get('match_id')
            if not match_id:
                continue
            
            created = self.analyze_and_track(match_id, opp.get('sport', ''))
            if created > 0:
                logger.info(f"  ✅ {match_id[:20]}... : {created} marchés")
        
        logger.info(f"\n📊 Résumé: {self.stats['new_tracks']} nouveaux, {self.stats['skipped_duplicates']} déjà trackés")
        
        return self.stats
    
    def run_resolve(self):
        """Phase 2: Résolution des picks terminés"""
        logger.info("=" * 60)
        logger.info("🔄 AGENT CLV TRACKER V2 - RESOLVE")
        logger.info("=" * 60)
        
        result = self.resolve_all_pending()
        
        logger.info(f"\n📊 Résolus: {result['resolved']}")
        logger.info(f"   ✅ Wins: {result['wins']}")
        logger.info(f"   ❌ Losses: {result['losses']}")
        if result['resolved'] > 0:
            wr = result['wins'] / result['resolved'] * 100
            logger.info(f"   📈 Win Rate: {wr:.1f}%")
        
        return result
    
    def run_analyze(self):
        """Phase 3: Analyse des performances"""
        logger.info("=" * 60)
        logger.info("📈 AGENT CLV TRACKER V2 - ANALYZE")
        logger.info("=" * 60)
        
        report = self.generate_daily_report()
        
        logger.info(f"\n🎯 RAPPORT ({report['period']}):")
        logger.info(f"   Total picks: {report['global']['total_picks']}")
        logger.info(f"   Résolus: {report['global']['resolved']}")
        logger.info(f"   Win Rate: {report['global']['win_rate']}%")
        logger.info(f"   Profit: {report['global']['profit']}")
        logger.info(f"\n📊 Calibration ECE: {report['calibration']['ece']}%")
        logger.info(f"   {report['calibration']['status']}")
        
        if report['weaknesses']:
            logger.info(f"\n⚠️ {len(report['weaknesses'])} faiblesses détectées:")
            for w in report['weaknesses']:
                logger.info(f"   - {w['type']}: {w.get('market', w.get('league', ''))} ({w['action']})")
        
        logger.info(f"\n💚 Score de santé du modèle: {report['health_score']}/100")
        
        return report
    
    def run_full(self):
        """Exécution complète: Collect + Resolve + Analyze"""
        logger.info("=" * 60)
        logger.info("🎯 AGENT CLV TRACKER V2 - EXÉCUTION COMPLÈTE")
        logger.info("=" * 60)
        
        # 1. Collect
        self.run_collect()
        
        # 2. Resolve
        self.run_resolve()
        
        # 3. Analyze
        report = self.run_analyze()
        
        self.close()
        
        return {
            'stats': self.stats,
            'report': report
        }


if __name__ == "__main__":
    import sys
    
    agent = AgentCLVTrackerV2()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == 'collect':
            agent.run_collect()
        elif command == 'resolve':
            agent.run_resolve()
        elif command == 'analyze':
            agent.run_analyze()
        else:
            agent.run_full()
    else:
        agent.run_full()
    
    agent.close()
