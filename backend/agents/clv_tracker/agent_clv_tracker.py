#!/usr/bin/env python3
"""
🎯 AGENT CLV TRACKER V1.0
Agent spécialisé dans le tracking et l'analyse des prédictions

Responsabilités:
1. COLLECT: Récupérer les matchs à venir et leurs analyses
2. TRACK: Enregistrer tous les marchés dans tracking_clv_picks
3. RESOLVE: Résoudre les picks après les matchs
4. ANALYZE: Détecter les biais et suggérer des améliorations
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import requests
import json
import logging
import os

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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('AgentCLVTracker')


class AgentCLVTracker:
    """Agent spécialisé dans le tracking CLV"""
    
    def __init__(self):
        self.conn = None
        self.stats = {
            'collected': 0,
            'tracked': 0,
            'resolved': 0,
            'errors': 0
        }
    
    def get_db(self):
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
        return self.conn
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    # ============================================================
    # PHASE 1: COLLECT - Récupérer les matchs à analyser
    # ============================================================
    
    def collect_opportunities(self) -> list:
        """Récupère les opportunités de matchs à venir"""
        try:
            response = requests.get(
                f"{API_BASE}/opportunities/opportunities/",
                params={'limit': 100},
                timeout=30
            )
            if response.ok:
                data = response.json()
                opportunities = data if isinstance(data, list) else []
                logger.info(f"📋 {len(opportunities)} opportunités récupérées")
                return opportunities
            else:
                logger.error(f"Erreur API opportunities: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Erreur collect: {e}")
            return []
    
    def analyze_match(self, match_id: str) -> dict:
        """Analyse un match via patron-diamond"""
        try:
            response = requests.get(
                f"{API_BASE}/patron-diamond/analyze/{match_id}",
                timeout=30
            )
            if response.ok:
                return response.json()
            else:
                logger.warning(f"Analyse échouée pour {match_id}: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Erreur analyse {match_id}: {e}")
            return None
    
    # ============================================================
    # PHASE 2: TRACK - Enregistrer tous les marchés
    # ============================================================
    
    def track_analysis(self, analysis: dict, league: str = None) -> int:
        """
        Enregistre TOUS les marchés d'une analyse dans tracking_clv_picks
        Retourne le nombre de picks créés
        """
        if not analysis or not analysis.get('match_id'):
            return 0
        
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        match_id = analysis['match_id']
        home_team = analysis.get('home_team', '')
        away_team = analysis.get('away_team', '')
        poisson = analysis.get('poisson', {})
        
        # Données xG
        home_xg = poisson.get('home_xg', 0)
        away_xg = poisson.get('away_xg', 0)
        total_xg = poisson.get('total_xg', 0)
        
        # Collecter tous les marchés
        markets = []
        
        # BTTS
        btts = analysis.get('btts', {})
        if btts.get('score') is not None:
            markets.append({
                'key': 'btts_yes',
                'score': btts.get('score', 0),
                'odds': btts.get('odds', 0),
                'probability': btts.get('probability', 0),
                'poisson_prob': poisson.get('btts_prob', 0),
                'kelly': btts.get('kelly_pct', 0),
                'value_rating': btts.get('value_rating', ''),
                'recommendation': btts.get('recommendation', ''),
                'factors': btts.get('factors', {}),
                'prediction': 'yes'
            })
        
        # BTTS No
        btts_no = analysis.get('btts_no', {})
        if btts_no.get('score') is not None:
            markets.append({
                'key': 'btts_no',
                'score': btts_no.get('score', 0),
                'odds': btts_no.get('odds', 0),
                'probability': btts_no.get('probability', 0),
                'poisson_prob': poisson.get('btts_no_prob', 0),
                'kelly': btts_no.get('kelly_pct', 0),
                'value_rating': btts_no.get('value_rating', ''),
                'recommendation': btts_no.get('recommendation', ''),
                'factors': btts_no.get('factors', {}),
                'prediction': 'no'
            })
        
        # Over/Under
        for market_name in ['over15', 'under15', 'over25', 'under25', 'over35', 'under35']:
            market = analysis.get(market_name, {})
            if market.get('score') is not None:
                prob_key = f"{market_name.replace('over', 'over').replace('under', 'under')}_prob"
                markets.append({
                    'key': market_name,
                    'score': market.get('score', 0),
                    'odds': market.get('odds', 0),
                    'probability': market.get('probability', 0),
                    'poisson_prob': poisson.get(prob_key, 0),
                    'kelly': market.get('kelly_pct', 0),
                    'value_rating': market.get('value_rating', ''),
                    'recommendation': market.get('recommendation', ''),
                    'factors': market.get('factors', {}),
                    'prediction': 'over' if 'over' in market_name else 'under'
                })
        
        # Double Chance
        dc = analysis.get('double_chance', {})
        for dc_key in ['1x', 'x2', '12']:
            dc_market = dc.get(dc_key, {})
            if dc_market.get('score') is not None:
                dc_poisson = poisson.get('double_chance', {})
                markets.append({
                    'key': f'dc_{dc_key}',
                    'score': dc_market.get('score', 0),
                    'odds': dc_market.get('odds', 0),
                    'probability': dc_market.get('probability', 0),
                    'poisson_prob': dc_poisson.get(dc_key, 0),
                    'kelly': dc_market.get('kelly_pct', 0),
                    'value_rating': dc_market.get('value_rating', ''),
                    'recommendation': dc_market.get('recommendation', ''),
                    'factors': dc_market.get('factors', {}),
                    'prediction': dc_key
                })
        
        # Draw No Bet
        dnb = analysis.get('draw_no_bet', {})
        for dnb_key in ['home', 'away']:
            dnb_market = dnb.get(dnb_key, {})
            if dnb_market.get('score') is not None:
                dnb_poisson = poisson.get('draw_no_bet', {})
                markets.append({
                    'key': f'dnb_{dnb_key}',
                    'score': dnb_market.get('score', 0),
                    'odds': dnb_market.get('odds', 0),
                    'probability': dnb_market.get('probability', 0),
                    'poisson_prob': dnb_poisson.get(dnb_key, 0),
                    'kelly': dnb_market.get('kelly_pct', 0),
                    'value_rating': dnb_market.get('value_rating', ''),
                    'recommendation': dnb_market.get('recommendation', ''),
                    'factors': dnb_market.get('factors', {}),
                    'prediction': dnb_key
                })
        
        # Insérer tous les marchés
        created = 0
        for market in markets:
            try:
                # Vérifier si déjà tracké
                cur.execute("""
                    SELECT id FROM tracking_clv_picks 
                    WHERE match_id = %s AND market_type = %s
                """, (match_id, market['key']))
                
                if cur.fetchone():
                    continue
                
                # Insérer
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
                """, (
                    match_id, home_team, away_team, league or '',
                    f"{home_team} vs {away_team}",
                    market['key'], market['prediction'],
                    market['odds'], market['probability'],
                    market['kelly'], int(market['score']),
                    market['value_rating'], market['recommendation'],
                    json.dumps(market['factors']),
                    market['score'] >= 70,  # is_top3
                    'agent_clv_tracker',
                    home_xg, away_xg, total_xg,
                    market['poisson_prob'],
                    market['score'] / 100 if market['score'] else 0
                ))
                created += 1
                
            except Exception as e:
                logger.warning(f"Erreur insertion marché {market['key']}: {e}")
                conn.rollback()
                continue
        
        conn.commit()
        self.stats['tracked'] += created
        return created
    
    # ============================================================
    # PHASE 3: RESOLVE - Résoudre les picks terminés
    # ============================================================
    
    def resolve_picks(self) -> dict:
        """Résout les picks dont les matchs sont terminés"""
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Récupérer picks non résolus
        cur.execute("""
            SELECT id, match_id, market_type, odds_taken, stake
            FROM tracking_clv_picks
            WHERE is_resolved = false AND match_id IS NOT NULL
        """)
        pending = cur.fetchall()
        
        logger.info(f"🔄 {len(pending)} picks à résoudre")
        
        resolved = 0
        wins = 0
        losses = 0
        
        for pick in pending:
            # Chercher le résultat
            cur.execute("""
                SELECT score_home, score_away, outcome, is_finished
                FROM match_results
                WHERE match_id = %s AND is_finished = true
            """, (pick['match_id'],))
            result = cur.fetchone()
            
            if not result:
                continue
            
            home = result['score_home']
            away = result['score_away']
            outcome = result['outcome']
            total = home + away
            
            # Déterminer le résultat du pick
            market = pick['market_type']
            is_winner = None
            
            if market == 'btts_yes':
                is_winner = home > 0 and away > 0
            elif market == 'btts_no':
                is_winner = home == 0 or away == 0
            elif market == 'over15':
                is_winner = total > 1
            elif market == 'under15':
                is_winner = total < 2
            elif market == 'over25':
                is_winner = total > 2
            elif market == 'under25':
                is_winner = total < 3
            elif market == 'over35':
                is_winner = total > 3
            elif market == 'under35':
                is_winner = total < 4
            elif market == 'dc_1x':
                is_winner = outcome in ('home', 'draw')
            elif market == 'dc_x2':
                is_winner = outcome in ('draw', 'away')
            elif market == 'dc_12':
                is_winner = outcome in ('home', 'away')
            elif market == 'dnb_home':
                is_winner = outcome == 'home' if outcome != 'draw' else None
            elif market == 'dnb_away':
                is_winner = outcome == 'away' if outcome != 'draw' else None
            
            if is_winner is None:
                continue
            
            # Calculer profit/loss
            stake = float(pick['stake'] or 1)
            odds = float(pick['odds_taken'] or 1)
            profit = stake * (odds - 1) if is_winner else -stake
            
            # Mettre à jour
            cur.execute("""
                UPDATE tracking_clv_picks
                SET is_resolved = true, is_winner = %s, profit_loss = %s,
                    score_home = %s, score_away = %s, resolved_at = NOW()
                WHERE id = %s
            """, (is_winner, profit, home, away, pick['id']))
            
            resolved += 1
            if is_winner:
                wins += 1
            else:
                losses += 1
        
        conn.commit()
        self.stats['resolved'] += resolved
        
        return {
            'resolved': resolved,
            'wins': wins,
            'losses': losses,
            'win_rate': round(wins / resolved * 100, 1) if resolved > 0 else 0
        }
    
    # ============================================================
    # PHASE 4: ANALYZE - Analyser les performances
    # ============================================================
    
    def analyze_performance(self, days: int = 30) -> dict:
        """Analyse les performances des prédictions"""
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Stats globales
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE is_winner = true) as wins,
                COUNT(*) FILTER (WHERE is_winner = false) as losses,
                AVG(CASE WHEN is_winner THEN 100.0 ELSE 0 END) as win_rate,
                SUM(profit_loss) as total_profit,
                AVG(diamond_score) as avg_score
            FROM tracking_clv_picks
            WHERE is_resolved = true
            AND created_at > NOW() - INTERVAL '%s days'
        """, (days,))
        global_stats = cur.fetchone()
        
        # Stats par marché
        cur.execute("""
            SELECT 
                market_type,
                COUNT(*) as total,
                AVG(CASE WHEN is_winner THEN 100.0 ELSE 0 END) as win_rate,
                AVG(diamond_score) as avg_score,
                SUM(profit_loss) as profit
            FROM tracking_clv_picks
            WHERE is_resolved = true
            AND created_at > NOW() - INTERVAL '%s days'
            GROUP BY market_type
            HAVING COUNT(*) >= 5
            ORDER BY win_rate DESC
        """, (days,))
        by_market = cur.fetchall()
        
        # Calibration (score prédit vs réalité)
        cur.execute("""
            SELECT 
                FLOOR(diamond_score / 10) * 10 as bucket,
                COUNT(*) as total,
                AVG(CASE WHEN is_winner THEN 100.0 ELSE 0 END) as actual_rate
            FROM tracking_clv_picks
            WHERE is_resolved = true
            AND created_at > NOW() - INTERVAL '%s days'
            GROUP BY FLOOR(diamond_score / 10) * 10
            ORDER BY bucket
        """, (days,))
        calibration = cur.fetchall()
        
        return {
            'global': {
                'total': global_stats['total'] or 0,
                'wins': global_stats['wins'] or 0,
                'losses': global_stats['losses'] or 0,
                'win_rate': round(float(global_stats['win_rate'] or 0), 1),
                'profit': round(float(global_stats['total_profit'] or 0), 2),
                'avg_score': round(float(global_stats['avg_score'] or 0), 1)
            },
            'by_market': [
                {
                    'market': m['market_type'],
                    'total': m['total'],
                    'win_rate': round(float(m['win_rate'] or 0), 1),
                    'avg_score': round(float(m['avg_score'] or 0), 1),
                    'profit': round(float(m['profit'] or 0), 2)
                }
                for m in by_market
            ],
            'calibration': [
                {
                    'score_range': f"{int(c['bucket'])}-{int(c['bucket'])+10}",
                    'sample': c['total'],
                    'expected': int(c['bucket']) + 5,
                    'actual': round(float(c['actual_rate'] or 0), 1),
                    'gap': round(float(c['actual_rate'] or 0) - (int(c['bucket']) + 5), 1)
                }
                for c in calibration
            ]
        }
    
    # ============================================================
    # RUN - Exécution complète
    # ============================================================
    
    def run_collect_and_track(self):
        """Exécute la collecte et le tracking"""
        logger.info("🚀 Agent CLV Tracker - COLLECT & TRACK")
        
        opportunities = self.collect_opportunities()
        
        for opp in opportunities:
            try:
                match_id = opp.get('match_id')
                if not match_id:
                    continue
                
                analysis = self.analyze_match(match_id)
                if analysis:
                    created = self.track_analysis(analysis, opp.get('sport'))
                    if created > 0:
                        logger.info(f"  ✅ {analysis.get('home_team')} vs {analysis.get('away_team')}: {created} marchés")
                    self.stats['collected'] += 1
                    
            except Exception as e:
                logger.error(f"Erreur pour {match_id}: {e}")
                self.stats['errors'] += 1
        
        logger.info(f"📊 Résumé: {self.stats}")
        return self.stats
    
    def run_resolve(self):
        """Exécute la résolution des picks"""
        logger.info("🔄 Agent CLV Tracker - RESOLVE")
        result = self.resolve_picks()
        logger.info(f"📊 Résolus: {result['resolved']} | Wins: {result['wins']} | Win Rate: {result['win_rate']}%")
        return result
    
    def run_full(self):
        """Exécution complète: collect, track, resolve, analyze"""
        logger.info("=" * 60)
        logger.info("🎯 AGENT CLV TRACKER - EXÉCUTION COMPLÈTE")
        logger.info("=" * 60)
        
        # 1. Collect & Track
        self.run_collect_and_track()
        
        # 2. Resolve
        resolve_result = self.run_resolve()
        
        # 3. Analyze
        perf = self.analyze_performance()
        
        logger.info("\n📈 PERFORMANCE GLOBALE:")
        logger.info(f"   Total: {perf['global']['total']} | Win Rate: {perf['global']['win_rate']}%")
        logger.info(f"   Profit: {perf['global']['profit']}")
        
        self.close()
        return {
            'stats': self.stats,
            'resolve': resolve_result,
            'performance': perf
        }


if __name__ == "__main__":
    agent = AgentCLVTracker()
    agent.run_full()
