#!/usr/bin/env python3
"""
🤖 ORCHESTRATEUR CLV TRACKER - VERSION 100% LOCALE
Utilise UNIQUEMENT les données déjà collectées dans la DB

⚠️ AUCUNE API EXTERNE APPELÉE:
✅ Lit odds_history (données The Odds API déjà collectées)
✅ Lit team_statistics_live (données API-Football déjà collectées)
✅ Calculs Poisson locaux
✅ Zéro coût API supplémentaire
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from decimal import Decimal
import json
import logging
import os
import sys
import fcntl
import math
from pathlib import Path
from typing import Optional, Dict, List, Set, Tuple
from dataclasses import dataclass
from enum import Enum

# ============================================================
# CONFIGURATION
# ============================================================

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
}

LOG_DIR = Path('/home/Mon_ps/logs/clv_tracker')
LOCK_FILE = Path('/tmp/clv_orchestrator.lock')

LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / f"orchestrator_{datetime.now().strftime('%Y%m%d')}.log")
    ]
)
logger = logging.getLogger('CLV_Local')


# ============================================================
# CALCULS POISSON LOCAUX
# ============================================================

def poisson_prob(lam: float, k: int) -> float:
    """Probabilité Poisson P(X=k) avec lambda=lam"""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (math.exp(-lam) * (lam ** k)) / math.factorial(k)

def calculate_match_probabilities(home_xg: float, away_xg: float) -> Dict:
    """
    Calcule toutes les probabilités d'un match basé sur les xG
    100% LOCAL - aucune API externe
    """
    total_xg = home_xg + away_xg
    
    # Matrice des scores (0-5 buts chaque équipe)
    max_goals = 6
    score_matrix = {}
    for h in range(max_goals):
        for a in range(max_goals):
            score_matrix[(h, a)] = poisson_prob(home_xg, h) * poisson_prob(away_xg, a)
    
    # Calculer les probabilités
    btts_yes = sum(p for (h, a), p in score_matrix.items() if h > 0 and a > 0)
    btts_no = 1 - btts_yes
    
    over_15 = sum(p for (h, a), p in score_matrix.items() if h + a > 1)
    over_25 = sum(p for (h, a), p in score_matrix.items() if h + a > 2)
    over_35 = sum(p for (h, a), p in score_matrix.items() if h + a > 3)
    
    home_win = sum(p for (h, a), p in score_matrix.items() if h > a)
    draw = sum(p for (h, a), p in score_matrix.items() if h == a)
    away_win = sum(p for (h, a), p in score_matrix.items() if h < a)
    
    return {
        'home_xg': home_xg,
        'away_xg': away_xg,
        'total_xg': total_xg,
        'btts_yes': round(btts_yes * 100, 1),
        'btts_no': round(btts_no * 100, 1),
        'over_15': round(over_15 * 100, 1),
        'under_15': round((1 - over_15) * 100, 1),
        'over_25': round(over_25 * 100, 1),
        'under_25': round((1 - over_25) * 100, 1),
        'over_35': round(over_35 * 100, 1),
        'under_35': round((1 - over_35) * 100, 1),
        'home_win': round(home_win * 100, 1),
        'draw': round(draw * 100, 1),
        'away_win': round(away_win * 100, 1),
        'dc_1x': round((home_win + draw) * 100, 1),
        'dc_x2': round((draw + away_win) * 100, 1),
        'dc_12': round((home_win + away_win) * 100, 1),
    }

def calculate_value_score(poisson_prob: float, odds: float) -> Tuple[int, float, str]:
    """
    Calcule le score de valeur d'un pari
    Returns: (score 0-100, kelly%, value_rating)
    """
    if not odds or odds <= 1:
        return (0, 0, 'NO_VALUE')
    
    implied_prob = 1 / odds * 100
    edge = poisson_prob - implied_prob
    
    # Kelly Criterion
    if edge > 0:
        kelly = (edge / 100) / (odds - 1) * 100
        kelly = min(kelly, 10)  # Cap à 10%
    else:
        kelly = 0
    
    # Score basé sur l'edge
    if edge >= 15:
        score = min(95, 70 + edge)
        rating = '🔥 EXCELLENT'
    elif edge >= 10:
        score = 60 + edge
        rating = '✅ GOOD'
    elif edge >= 5:
        score = 50 + edge
        rating = '📊 FAIR'
    elif edge > 0:
        score = 40 + edge
        rating = '⚠️ MARGINAL'
    else:
        score = max(20, 40 + edge)
        rating = '❌ NO_VALUE'
    
    return (int(score), round(kelly, 2), rating)


# ============================================================
# RÉSOLVEURS DE MARCHÉS
# ============================================================

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


class CLVOrchestratorLocal:
    """
    Orchestrateur 100% LOCAL
    - Lit uniquement depuis la DB (données déjà collectées)
    - Calculs Poisson locaux
    - Zéro appel API externe
    """
    
    VERSION = "2.0-LOCAL"
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.conn = None
        self.start_time = datetime.now()
        
        self._tracked_matches: Set[str] = set()
        self._cache_loaded = False
        
        self.stats = {
            'db_queries': 0,
            'picks_created': 0,
            'picks_resolved': 0,
            'errors': 0,
            'api_calls': 0  # Doit toujours être 0!
        }
    
    def get_db(self):
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
        return self.conn
    
    def close(self):
        if self.conn and not self.conn.closed:
            self.conn.close()
    
    def _safe_float(self, value, default: float = 0.0) -> float:
        if value is None:
            return default
        if isinstance(value, Decimal):
            return float(value)
        try:
            return float(value)
        except:
            return default
    
    # ============================================================
    # LOCK
    # ============================================================
    
    def acquire_lock(self) -> bool:
        try:
            self.lock_file = open(LOCK_FILE, 'w')
            fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_file.write(f"{os.getpid()}\n{datetime.now().isoformat()}")
            self.lock_file.flush()
            return True
        except (IOError, OSError):
            logger.warning("⚠️ Une autre instance est déjà en cours")
            return False
    
    def release_lock(self):
        try:
            if hasattr(self, 'lock_file') and self.lock_file:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
                LOCK_FILE.unlink(missing_ok=True)
        except:
            pass
    
    # ============================================================
    # CACHE
    # ============================================================
    
    def _load_cache(self):
        if self._cache_loaded:
            return
        
        conn = self.get_db()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT match_id FROM tracking_clv_picks WHERE match_id IS NOT NULL")
        self._tracked_matches = {row[0] for row in cur.fetchall()}
        cur.close()
        self._cache_loaded = True
        self.stats['db_queries'] += 1
        
        logger.info(f"📦 Cache: {len(self._tracked_matches)} matchs déjà trackés")
    
    # ============================================================
    # COLLECTE 100% LOCALE
    # ============================================================
    
    def get_matches_from_db(self) -> List[Dict]:
        """
        Récupère les matchs à tracker depuis odds_history
        ⚠️ 100% LOCAL - lit uniquement la DB
        """
        self._load_cache()
        
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Matchs dans les prochaines 48h avec cotes disponibles
        cur.execute("""
            SELECT DISTINCT ON (o.match_id)
                o.match_id,
                o.home_team,
                o.away_team,
                o.sport_title as league,
                o.commence_time,
                o.btts as btts_odds,
                o.over_25 as over25_odds,
                o.under_25 as under25_odds,
                o.over_15 as over15_odds,
                o.over_35 as over35_odds
            FROM odds_history o
            WHERE o.commence_time BETWEEN NOW() AND NOW() + INTERVAL '48 hours'
            AND o.match_id IS NOT NULL
            AND o.btts IS NOT NULL
            ORDER BY o.match_id, o.collected_at DESC
        """)
        
        matches = cur.fetchall()
        cur.close()
        self.stats['db_queries'] += 1
        
        # Filtrer ceux déjà trackés
        new_matches = [m for m in matches if m['match_id'] not in self._tracked_matches]
        
        logger.info(f"📋 {len(new_matches)} nouveaux / {len(matches)} total dans odds_history")
        
        return new_matches
    
    def get_team_xg(self, team_name: str) -> float:
        """
        Récupère le xG moyen d'une équipe depuis team_statistics_live
        ⚠️ 100% LOCAL - lit uniquement la DB
        """
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Chercher les stats de l'équipe
        cur.execute("""
            SELECT 
                goals_for_avg_overall,
                goals_for_avg_home,
                goals_for_avg_away
            FROM team_statistics_live
            WHERE LOWER(team_name) ILIKE %s
            ORDER BY last_updated DESC
            LIMIT 1
        """, (f'%{team_name.split()[0].lower()}%',))
        
        result = cur.fetchone()
        cur.close()
        self.stats['db_queries'] += 1
        
        if result:
            return self._safe_float(result['goals_for_avg_overall'], 1.3)
        
        return 1.3  # Valeur par défaut
    
    def analyze_match_locally(self, match: Dict) -> Dict:
        """
        Analyse un match 100% localement
        - Récupère xG depuis la DB
        - Calcule probabilités Poisson
        - Génère scores de valeur
        """
        home_team = match['home_team']
        away_team = match['away_team']
        
        # Récupérer xG depuis la DB
        home_xg = self.get_team_xg(home_team)
        away_xg = self.get_team_xg(away_team)
        
        # Ajustement home advantage
        home_xg *= 1.1
        away_xg *= 0.9
        
        # Calculs Poisson
        probs = calculate_match_probabilities(home_xg, away_xg)
        
        # Générer les marchés avec scores
        markets = []
        
        # BTTS
        if match.get('btts_odds'):
            score, kelly, rating = calculate_value_score(probs['btts_yes'], self._safe_float(match['btts_odds']))
            markets.append({
                'market_type': 'btts_yes',
                'prediction': 'yes',
                'odds': self._safe_float(match['btts_odds']),
                'poisson_prob': probs['btts_yes'],
                'score': score,
                'kelly': kelly,
                'rating': rating
            })
            
            # BTTS No (inverse)
            btts_no_odds = 1 / (1 - 1/self._safe_float(match['btts_odds'])) if match['btts_odds'] else 0
            if btts_no_odds > 1:
                score, kelly, rating = calculate_value_score(probs['btts_no'], btts_no_odds)
                markets.append({
                    'market_type': 'btts_no',
                    'prediction': 'no',
                    'odds': btts_no_odds,
                    'poisson_prob': probs['btts_no'],
                    'score': score,
                    'kelly': kelly,
                    'rating': rating
                })
        
        # Over/Under
        for market_key, odds_key, prob_key in [
            ('over15', 'over15_odds', 'over_15'),
            ('over25', 'over25_odds', 'over_25'),
            ('under25', 'under25_odds', 'under_25'),
            ('over35', 'over35_odds', 'over_35'),
        ]:
            odds = self._safe_float(match.get(odds_key))
            if odds > 1:
                prob = probs.get(prob_key, 50)
                score, kelly, rating = calculate_value_score(prob, odds)
                markets.append({
                    'market_type': market_key,
                    'prediction': 'over' if 'over' in market_key else 'under',
                    'odds': odds,
                    'poisson_prob': prob,
                    'score': score,
                    'kelly': kelly,
                    'rating': rating
                })
        
        return {
            'match_id': match['match_id'],
            'home_team': home_team,
            'away_team': away_team,
            'league': match.get('league', ''),
            'commence_time': match.get('commence_time'),
            'home_xg': home_xg,
            'away_xg': away_xg,
            'total_xg': home_xg + away_xg,
            'markets': markets
        }
    
    def collect(self) -> Dict:
        """
        Collecte 100% LOCALE
        - Lit odds_history
        - Lit team_statistics_live
        - Calculs Poisson locaux
        - ZÉRO appel API externe
        """
        start = datetime.now()
        logger.info("🚀 COLLECT LOCAL - Démarrage (0 API externe)")
        
        matches = self.get_matches_from_db()
        
        if not matches:
            logger.info("✅ Aucun nouveau match à tracker")
            return {'created': 0, 'matches': 0}
        
        created = 0
        
        for match in matches:
            try:
                # Analyse 100% locale
                analysis = self.analyze_match_locally(match)
                
                # Sauvegarder les picks
                picks_saved = self._save_picks(analysis)
                created += picks_saved
                
                if picks_saved > 0:
                    self._tracked_matches.add(match['match_id'])
                    logger.info(f"  ✅ {match['home_team']} vs {match['away_team']}: {picks_saved} marchés")
                    
            except Exception as e:
                logger.warning(f"  ⚠️ Erreur {match['match_id']}: {e}")
                self.stats['errors'] += 1
        
        self.stats['picks_created'] += created
        duration = (datetime.now() - start).total_seconds()
        
        logger.info(f"✅ COLLECT terminé: {created} picks | {duration:.1f}s | 0 API externe")
        
        return {'created': created, 'matches': len(matches), 'duration': duration}
    
    def _save_picks(self, analysis: Dict) -> int:
        """Sauvegarde les picks dans la DB"""
        if self.dry_run:
            return len(analysis.get('markets', []))
        
        conn = self.get_db()
        cur = conn.cursor()
        
        created = 0
        match_id = analysis['match_id']
        
        for market in analysis.get('markets', []):
            try:
                cur.execute("""
                    INSERT INTO tracking_clv_picks (
                        match_id, home_team, away_team, league, match_name,
                        market_type, prediction, diamond_score, odds_taken,
                        probability, kelly_pct, value_rating,
                        home_xg, away_xg, total_xg, poisson_prob,
                        is_top3, source, predicted_prob
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (match_id, market_type) DO NOTHING
                """, (
                    match_id,
                    analysis['home_team'],
                    analysis['away_team'],
                    analysis['league'],
                    f"{analysis['home_team']} vs {analysis['away_team']}",
                    market['market_type'],
                    market['prediction'],
                    market['score'],
                    market['odds'],
                    market['poisson_prob'],
                    market['kelly'],
                    market['rating'],
                    analysis['home_xg'],
                    analysis['away_xg'],
                    analysis['total_xg'],
                    market['poisson_prob'],
                    market['score'] >= 70,
                    'orchestrator_local_v2',
                    market['score'] / 100
                ))
                
                if cur.rowcount > 0:
                    created += 1
                    
            except Exception as e:
                logger.debug(f"Insert error: {e}")
        
        conn.commit()
        cur.close()
        self.stats['db_queries'] += 1
        
        return created
    
    # ============================================================
    # RÉSOLUTION
    # ============================================================
    
    def resolve(self) -> Dict:
        """Résout les picks terminés (100% local)"""
        start = datetime.now()
        logger.info("🔄 RESOLVE - Démarrage")
        
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        now = datetime.now()
        margin = timedelta(hours=2)
        
        # Picks avec match terminé (via odds_history.commence_time)
        cur.execute("""
            SELECT DISTINCT 
                p.id, p.home_team, p.away_team, p.market_type, 
                p.odds_taken, p.stake, p.match_id,
                o.commence_time
            FROM tracking_clv_picks p
            JOIN odds_history o ON p.match_id = o.match_id
            WHERE p.is_resolved = false
            AND o.commence_time < %s
        """, (now - margin,))
        
        pending = cur.fetchall()
        self.stats['db_queries'] += 1
        
        logger.info(f"📋 {len(pending)} picks avec match terminé")
        
        if not pending:
            return {'resolved': 0, 'wins': 0, 'losses': 0}
        
        # Grouper par match
        matches = {}
        for p in pending:
            key = (p['home_team'].lower().strip(), p['away_team'].lower().strip(),
                   p['commence_time'].date() if p['commence_time'] else None)
            if key not in matches:
                matches[key] = []
            matches[key].append(p)
        
        resolved = 0
        wins = 0
        losses = 0
        
        for (home, away, match_date), picks in matches.items():
            if not match_date:
                continue
            
            # Chercher le résultat
            cur.execute("""
                SELECT score_home, score_away, outcome
                FROM match_results
                WHERE is_finished = true
                AND DATE(match_date) BETWEEN %s AND %s
                AND (LOWER(home_team) ILIKE %s AND LOWER(away_team) ILIKE %s)
                LIMIT 1
            """, (
                match_date - timedelta(days=1),
                match_date + timedelta(days=1),
                f'%{home.split()[0]}%',
                f'%{away.split()[0]}%'
            ))
            
            result = cur.fetchone()
            self.stats['db_queries'] += 1
            
            if not result:
                continue
            
            h_score = result['score_home']
            a_score = result['score_away']
            outcome = result['outcome']
            
            logger.info(f"  ✅ {home} vs {away}: {h_score}-{a_score}")
            
            for pick in picks:
                resolver = MARKET_RESOLVERS.get(pick['market_type'])
                if not resolver:
                    continue
                
                is_winner = resolver(h_score, a_score, outcome)
                
                if is_winner is None:
                    profit = 0
                elif is_winner:
                    stake = self._safe_float(pick['stake'], 1)
                    odds = self._safe_float(pick['odds_taken'], 1)
                    profit = stake * (odds - 1)
                    wins += 1
                else:
                    profit = -self._safe_float(pick['stake'], 1)
                    losses += 1
                
                if not self.dry_run:
                    cur.execute("""
                        UPDATE tracking_clv_picks
                        SET is_resolved = true, is_winner = %s, profit_loss = %s,
                            score_home = %s, score_away = %s, resolved_at = NOW()
                        WHERE id = %s
                    """, (is_winner, profit, h_score, a_score, pick['id']))
                
                resolved += 1
        
        if not self.dry_run:
            conn.commit()
        
        cur.close()
        self.stats['picks_resolved'] += resolved
        
        duration = (datetime.now() - start).total_seconds()
        win_rate = round(wins / (wins + losses) * 100, 1) if (wins + losses) > 0 else 0
        
        logger.info(f"✅ RESOLVE terminé: {resolved} ({wins}W/{losses}L = {win_rate}%) | {duration:.1f}s")
        
        return {'resolved': resolved, 'wins': wins, 'losses': losses, 'win_rate': win_rate}
    
    # ============================================================
    # RAPPORT
    # ============================================================
    
    def report(self, days: int = 7) -> Dict:
        """Génère un rapport"""
        logger.info(f"📊 REPORT ({days} jours)")
        
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE is_resolved) as resolved,
                COUNT(*) FILTER (WHERE is_winner = true) as wins,
                COUNT(*) FILTER (WHERE is_winner = false) as losses,
                SUM(profit_loss) FILTER (WHERE is_resolved) as profit,
                AVG(diamond_score) as avg_score
            FROM tracking_clv_picks
            WHERE created_at > NOW() - INTERVAL '%s days'
        """, (days,))
        
        stats = cur.fetchone()
        cur.close()
        self.stats['db_queries'] += 1
        
        resolved = int(stats['resolved'] or 0)
        wins = int(stats['wins'] or 0)
        profit = self._safe_float(stats['profit'])
        
        report = {
            'period': f'{days} jours',
            'total': int(stats['total'] or 0),
            'resolved': resolved,
            'wins': wins,
            'losses': int(stats['losses'] or 0),
            'win_rate': round(wins / resolved * 100, 1) if resolved > 0 else 0,
            'profit': round(profit, 2),
            'roi': round(profit / resolved * 100, 1) if resolved > 0 else 0
        }
        
        logger.info("=" * 50)
        logger.info(f"📈 Total: {report['total']} | Résolus: {report['resolved']}")
        logger.info(f"   W/L: {report['wins']}/{report['losses']} | WR: {report['win_rate']}%")
        logger.info(f"   Profit: {report['profit']} | ROI: {report['roi']}%")
        logger.info("=" * 50)
        
        return report
    
    # ============================================================
    # MODE SMART
    # ============================================================
    
    def should_collect(self) -> Tuple[bool, str, int]:
        """Vérifie si collecte nécessaire"""
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT COUNT(DISTINCT o.match_id) as count
            FROM odds_history o
            LEFT JOIN tracking_clv_picks p ON o.match_id = p.match_id
            WHERE o.commence_time BETWEEN NOW() AND NOW() + INTERVAL '24 hours'
            AND p.match_id IS NULL
            AND o.btts IS NOT NULL
        """)
        
        result = cur.fetchone()
        cur.close()
        self.stats['db_queries'] += 1
        
        count = result['count'] if result else 0
        
        if count > 0:
            return (True, f"{count} nouveaux matchs dans odds_history", count)
        return (False, "Aucun nouveau match", 0)
    
    def should_resolve(self) -> Tuple[bool, str, int]:
        """Vérifie si résolution nécessaire"""
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT COUNT(*) as count
            FROM tracking_clv_picks p
            JOIN odds_history o ON p.match_id = o.match_id
            WHERE p.is_resolved = false
            AND o.commence_time < NOW() - INTERVAL '2 hours'
        """)
        
        result = cur.fetchone()
        cur.close()
        self.stats['db_queries'] += 1
        
        count = result['count'] if result else 0
        
        if count > 0:
            return (True, f"{count} picks prêts", count)
        return (False, "Aucun pick à résoudre", 0)
    
    def run_smart(self) -> Dict:
        """Mode intelligent: fait uniquement ce qui est nécessaire"""
        results = {'actions': []}
        
        logger.info("🧠 MODE SMART - Analyse...")
        
        should_c, reason_c, count_c = self.should_collect()
        logger.info(f"  Collect: {should_c} ({reason_c})")
        
        if should_c:
            results['collect'] = self.collect()
            results['actions'].append('collect')
        
        should_r, reason_r, count_r = self.should_resolve()
        logger.info(f"  Resolve: {should_r} ({reason_r})")
        
        if should_r:
            results['resolve'] = self.resolve()
            results['actions'].append('resolve')
        
        if not results['actions']:
            logger.info("✅ Rien à faire")
            results['actions'].append('none')
        
        return results
    
    # ============================================================
    # EXÉCUTION
    # ============================================================
    
    def run(self, task: str = 'smart') -> Dict:
        """Point d'entrée principal"""
        
        if not self.acquire_lock():
            return {'error': 'Already running'}
        
        try:
            logger.info("=" * 60)
            logger.info(f"🤖 CLV ORCHESTRATOR LOCAL v{self.VERSION}")
            logger.info(f"   Mode: {task} | Dry-run: {self.dry_run}")
            logger.info(f"   ⚠️ 0 API EXTERNE - 100% données locales")
            logger.info("=" * 60)
            
            if task == 'collect':
                return self.collect()
            elif task == 'resolve':
                return self.resolve()
            elif task == 'report':
                return self.report()
            elif task == 'full':
                return {
                    'collect': self.collect(),
                    'resolve': self.resolve(),
                    'report': self.report()
                }
            else:
                return self.run_smart()
                
        finally:
            self.release_lock()
            self.close()
            
            duration = (datetime.now() - self.start_time).total_seconds()
            logger.info(f"\n⏱️ Durée: {duration:.1f}s | DB queries: {self.stats['db_queries']} | API calls: {self.stats['api_calls']} (doit être 0!)")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='CLV Orchestrator 100% Local')
    parser.add_argument('task', nargs='?', default='smart',
                        choices=['collect', 'resolve', 'report', 'full', 'smart'])
    parser.add_argument('--dry-run', action='store_true')
    
    args = parser.parse_args()
    
    orchestrator = CLVOrchestratorLocal(dry_run=args.dry_run)
    result = orchestrator.run(args.task)
    
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
