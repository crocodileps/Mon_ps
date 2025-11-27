#!/usr/bin/env python3
"""
🤖 ORCHESTRATEUR CLV TRACKER - VERSION HYBRIDE SMART
Mode intelligent qui optimise l'utilisation des ressources

STRATÉGIE HYBRIDE:
✅ COLLECTE: 100% locale (odds_history + team_statistics_live + Poisson)
✅ RÉSOLUTION: 100% locale (match_results déjà collecté par cron API-Football)
✅ ANALYSE: 100% locale (calculs statistiques)

⚠️ AUCUN APPEL API SUPPLÉMENTAIRE
Les APIs sont appelées par les collecteurs existants (cron séparés)
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
        logging.FileHandler(LOG_DIR / f"hybrid_{datetime.now().strftime('%Y%m%d')}.log")
    ]
)
logger = logging.getLogger('CLV_Hybrid')


# ============================================================
# CALCULS POISSON LOCAUX
# ============================================================

def poisson_prob(lam: float, k: int) -> float:
    """Probabilité Poisson P(X=k)"""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return (math.exp(-lam) * (lam ** k)) / math.factorial(k)


def calculate_probabilities(home_xg: float, away_xg: float) -> Dict:
    """Calcule toutes les probabilités via Poisson (100% local)"""
    max_goals = 6
    
    # Matrice des scores
    matrix = {}
    for h in range(max_goals):
        for a in range(max_goals):
            matrix[(h, a)] = poisson_prob(home_xg, h) * poisson_prob(away_xg, a)
    
    # Calculs
    btts_yes = sum(p for (h, a), p in matrix.items() if h > 0 and a > 0)
    over_15 = sum(p for (h, a), p in matrix.items() if h + a > 1)
    over_25 = sum(p for (h, a), p in matrix.items() if h + a > 2)
    over_35 = sum(p for (h, a), p in matrix.items() if h + a > 3)
    
    home_win = sum(p for (h, a), p in matrix.items() if h > a)
    draw = sum(p for (h, a), p in matrix.items() if h == a)
    away_win = sum(p for (h, a), p in matrix.items() if h < a)
    
    return {
        'btts_yes': btts_yes, 'btts_no': 1 - btts_yes,
        'over15': over_15, 'under15': 1 - over_15,
        'over25': over_25, 'under25': 1 - over_25,
        'over35': over_35, 'under35': 1 - over_35,
        'home': home_win, 'draw': draw, 'away': away_win,
        'dc_1x': home_win + draw, 'dc_x2': draw + away_win, 'dc_12': home_win + away_win
    }


def calculate_value(prob: float, odds: float) -> Tuple[int, float, str]:
    """Calcule score/kelly/rating"""
    if not odds or odds <= 1:
        return (0, 0, 'NO_VALUE')
    
    implied = 1 / odds
    edge = prob - implied
    
    if edge > 0:
        kelly = min((edge / (odds - 1)) * 100, 10)
    else:
        kelly = 0
    
    if edge >= 0.15:
        score, rating = min(95, int(70 + edge * 100)), '🔥 EXCELLENT'
    elif edge >= 0.10:
        score, rating = int(60 + edge * 100), '✅ GOOD'
    elif edge >= 0.05:
        score, rating = int(50 + edge * 100), '📊 FAIR'
    elif edge > 0:
        score, rating = int(40 + edge * 100), '⚠️ MARGINAL'
    else:
        score, rating = max(20, int(40 + edge * 100)), '❌ NO_VALUE'
    
    return (score, round(kelly, 2), rating)


# ============================================================
# RÉSOLVEURS
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
    'home': lambda h, a, o: h > a,
    'draw': lambda h, a, o: h == a,
    'away': lambda h, a, o: h < a,
    'dc_1x': lambda h, a, o: h >= a,
    'dc_x2': lambda h, a, o: h <= a,
    'dc_12': lambda h, a, o: h != a,
}


class CLVOrchestratorHybrid:
    """
    Orchestrateur Hybride Smart
    - Collecte: données locales + calculs Poisson
    - Résolution: match_results (collecté par cron existant)
    - ZÉRO appel API supplémentaire
    """
    
    VERSION = "2.1-HYBRID"
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.conn = None
        self.start_time = datetime.now()
        self._tracked: Set[str] = set()
        self._cache_loaded = False
        self.stats = {'db': 0, 'created': 0, 'resolved': 0, 'errors': 0}
    
    def get_db(self):
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
        return self.conn
    
    def close(self):
        if self.conn and not self.conn.closed:
            self.conn.close()
    
    def _float(self, v, d=0.0) -> float:
        if v is None: return d
        if isinstance(v, Decimal): return float(v)
        try: return float(v)
        except: return d
    
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
        except:
            logger.warning("⚠️ Instance déjà en cours")
            return False
    
    def release_lock(self):
        try:
            if hasattr(self, 'lock_file') and self.lock_file:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
                LOCK_FILE.unlink(missing_ok=True)
        except: pass
    
    # ============================================================
    # CACHE
    # ============================================================
    
    def _load_cache(self):
        if self._cache_loaded: return
        conn = self.get_db()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT match_id FROM tracking_clv_picks WHERE match_id IS NOT NULL")
        self._tracked = {r[0] for r in cur.fetchall()}
        cur.close()
        self._cache_loaded = True
        self.stats['db'] += 1
        logger.info(f"📦 Cache: {len(self._tracked)} matchs trackés")
    
    # ============================================================
    # COLLECTE HYBRIDE
    # ============================================================
    
    def get_team_xg(self, team: str) -> float:
        """Récupère xG depuis team_statistics_live (local)"""
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Chercher par nom (fuzzy)
        cur.execute("""
            SELECT goals_for_avg_overall, goals_for_avg_home, goals_for_avg_away
            FROM team_statistics_live
            WHERE LOWER(team_name) ILIKE %s
            ORDER BY last_updated DESC LIMIT 1
        """, (f'%{team.split()[0].lower()}%',))
        
        r = cur.fetchone()
        cur.close()
        self.stats['db'] += 1
        
        if r and r.get('goals_for_avg_overall'):
            return self._float(r['goals_for_avg_overall'], 1.3)
        return 1.3  # Défaut
    
    def collect(self) -> Dict:
        """
        Collecte 100% LOCALE:
        1. Récupère matchs depuis odds_history
        2. Récupère xG depuis team_statistics_live
        3. Calcule probabilités via Poisson (local)
        4. Génère les picks
        """
        start = datetime.now()
        logger.info("🚀 COLLECT HYBRIDE - 0 API externe")
        
        self._load_cache()
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Matchs dans les 48h prochaines (depuis odds_history)
        cur.execute("""
            SELECT DISTINCT ON (match_id)
                match_id, home_team, away_team, sport as league,
                commence_time, home_odds, draw_odds, away_odds
            FROM odds_history
            WHERE commence_time BETWEEN NOW() AND NOW() + INTERVAL '48 hours'
            ORDER BY match_id, collected_at DESC
        """)
        
        matches = cur.fetchall()
        cur.close()
        self.stats['db'] += 1
        
        # Filtrer déjà trackés
        new_matches = [m for m in matches if m['match_id'] not in self._tracked]
        logger.info(f"📋 {len(new_matches)} nouveaux / {len(matches)} total")
        
        if not new_matches:
            return {'created': 0, 'matches': 0}
        
        created = 0
        
        for match in new_matches:
            try:
                # 2. Récupérer xG (local)
                home_xg = self.get_team_xg(match['home_team']) * 1.1  # Home advantage
                away_xg = self.get_team_xg(match['away_team']) * 0.9
                
                # 3. Calculer probabilités Poisson (local)
                probs = calculate_probabilities(home_xg, away_xg)
                
                # 4. Générer les picks pour tous les marchés
                markets = []
                
                # 1X2 (cotes depuis odds_history)
                for mtype, odds_col in [('home', 'home_odds'), ('draw', 'draw_odds'), ('away', 'away_odds')]:
                    odds = self._float(match.get(odds_col))
                    if odds > 1:
                        score, kelly, rating = calculate_value(probs[mtype], odds)
                        markets.append((mtype, mtype, odds, probs[mtype], score, kelly, rating))
                
                # BTTS/Over/Under (estimations via implied odds)
                # On utilise les probabilités Poisson pour estimer les cotes
                for mtype, prob in [
                    ('btts_yes', probs['btts_yes']),
                    ('btts_no', probs['btts_no']),
                    ('over25', probs['over25']),
                    ('under25', probs['under25']),
                    ('over15', probs['over15']),
                    ('over35', probs['over35']),
                    ('dc_1x', probs['dc_1x']),
                    ('dc_x2', probs['dc_x2']),
                    ('dc_12', probs['dc_12']),
                ]:
                    # Estimer la cote fair (sans marge bookmaker)
                    fair_odds = 1 / prob if prob > 0.05 else 20
                    # Simuler une cote avec ~5% de marge
                    estimated_odds = fair_odds * 0.95
                    
                    if estimated_odds > 1.05:
                        score, kelly, rating = calculate_value(prob, estimated_odds)
                        # Ne garder que les value bets (score >= 50)
                        if score >= 50:
                            markets.append((mtype, mtype.split('_')[-1] if '_' in mtype else mtype, 
                                          estimated_odds, prob, score, kelly, rating))
                
                # 5. Sauvegarder
                if markets:
                    saved = self._save_picks(match, markets, home_xg, away_xg)
                    created += saved
                    if saved > 0:
                        self._tracked.add(match['match_id'])
                        logger.info(f"  ✅ {match['home_team']} vs {match['away_team']}: {saved} marchés")
                        
            except Exception as e:
                logger.warning(f"  ⚠️ {match['match_id']}: {e}")
                self.stats['errors'] += 1
        
        self.stats['created'] += created
        duration = (datetime.now() - start).total_seconds()
        logger.info(f"✅ COLLECT: {created} picks | {duration:.1f}s | 0 API")
        
        return {'created': created, 'matches': len(new_matches), 'duration': duration}
    
    def _save_picks(self, match: Dict, markets: List, home_xg: float, away_xg: float) -> int:
        """Sauvegarde les picks"""
        if self.dry_run:
            return len(markets)
        
        conn = self.get_db()
        cur = conn.cursor()
        saved = 0
        
        for mtype, pred, odds, prob, score, kelly, rating in markets:
            try:
                cur.execute("""
                    INSERT INTO tracking_clv_picks (
                        match_id, home_team, away_team, league, match_name,
                        market_type, prediction, diamond_score, odds_taken,
                        probability, kelly_pct, value_rating,
                        home_xg, away_xg, total_xg, poisson_prob,
                        is_top3, source, predicted_prob
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (match_id, market_type) DO NOTHING
                """, (
                    match['match_id'], match['home_team'], match['away_team'],
                    match.get('league', ''), f"{match['home_team']} vs {match['away_team']}",
                    mtype, pred, score, odds, prob * 100, kelly, rating,
                    home_xg, away_xg, home_xg + away_xg, prob * 100,
                    score >= 70, 'hybrid_v2', score / 100
                ))
                if cur.rowcount > 0:
                    saved += 1
            except Exception as e:
                logger.debug(f"Insert error: {e}")
        
        conn.commit()
        cur.close()
        self.stats['db'] += 1
        return saved
    
    # ============================================================
    # RÉSOLUTION (100% locale)
    # ============================================================
    
    def resolve(self) -> Dict:
        """
        Résolution 100% LOCALE:
        - Utilise match_results (collecté par cron API-Football existant)
        """
        start = datetime.now()
        logger.info("🔄 RESOLVE - Utilise match_results local")
        
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Picks non résolus avec commence_time passé (+2h marge)
        cur.execute("""
            SELECT DISTINCT 
                p.id, p.home_team, p.away_team, p.market_type, 
                p.odds_taken, p.stake, p.match_id,
                o.commence_time
            FROM tracking_clv_picks p
            JOIN odds_history o ON p.match_id = o.match_id
            WHERE p.is_resolved = false
            AND o.commence_time < NOW() - INTERVAL '2 hours'
        """)
        
        pending = cur.fetchall()
        self.stats['db'] += 1
        
        logger.info(f"📋 {len(pending)} picks à vérifier")
        
        if not pending:
            return {'resolved': 0, 'wins': 0, 'losses': 0}
        
        # Grouper par match
        matches = {}
        for p in pending:
            ct = p['commence_time']
            key = (p['home_team'].lower().strip(), p['away_team'].lower().strip(),
                   ct.date() if ct else None)
            if key not in matches:
                matches[key] = []
            matches[key].append(p)
        
        resolved = wins = losses = 0
        
        for (home, away, mdate), picks in matches.items():
            if not mdate:
                continue
            
            # Chercher résultat dans match_results
            cur.execute("""
                SELECT score_home, score_away, outcome
                FROM match_results
                WHERE is_finished = true
                AND DATE(match_date) BETWEEN %s AND %s
                AND LOWER(home_team) ILIKE %s 
                AND LOWER(away_team) ILIKE %s
                LIMIT 1
            """, (
                mdate - timedelta(days=1), mdate + timedelta(days=1),
                f'%{home.split()[0]}%', f'%{away.split()[0]}%'
            ))
            
            result = cur.fetchone()
            self.stats['db'] += 1
            
            if not result:
                continue
            
            hs, as_, oc = result['score_home'], result['score_away'], result['outcome']
            logger.info(f"  ✅ {home} vs {away}: {hs}-{as_}")
            
            for pick in picks:
                resolver = MARKET_RESOLVERS.get(pick['market_type'])
                if not resolver:
                    continue
                
                is_win = resolver(hs, as_, oc)
                
                if is_win is None:
                    profit = 0
                elif is_win:
                    stake = self._float(pick['stake'], 1)
                    odds = self._float(pick['odds_taken'], 1)
                    profit = stake * (odds - 1)
                    wins += 1
                else:
                    profit = -self._float(pick['stake'], 1)
                    losses += 1
                
                if not self.dry_run:
                    cur.execute("""
                        UPDATE tracking_clv_picks
                        SET is_resolved=true, is_winner=%s, profit_loss=%s,
                            score_home=%s, score_away=%s, resolved_at=NOW()
                        WHERE id=%s
                    """, (is_win, profit, hs, as_, pick['id']))
                
                resolved += 1
        
        if not self.dry_run:
            conn.commit()
        cur.close()
        
        self.stats['resolved'] += resolved
        wr = round(wins/(wins+losses)*100, 1) if (wins+losses) > 0 else 0
        duration = (datetime.now() - start).total_seconds()
        
        logger.info(f"✅ RESOLVE: {resolved} ({wins}W/{losses}L = {wr}%) | {duration:.1f}s")
        
        return {'resolved': resolved, 'wins': wins, 'losses': losses, 'win_rate': wr}
    
    # ============================================================
    # RAPPORT
    # ============================================================
    
    def report(self, days: int = 7) -> Dict:
        """Rapport de performance"""
        logger.info(f"📊 REPORT ({days}j)")
        
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
        
        s = cur.fetchone()
        cur.close()
        self.stats['db'] += 1
        
        resolved = int(s['resolved'] or 0)
        wins = int(s['wins'] or 0)
        profit = self._float(s['profit'])
        
        report = {
            'period': f'{days}j',
            'total': int(s['total'] or 0),
            'resolved': resolved,
            'pending': int(s['total'] or 0) - resolved,
            'wins': wins,
            'losses': int(s['losses'] or 0),
            'win_rate': round(wins/resolved*100, 1) if resolved > 0 else 0,
            'profit': round(profit, 2),
            'roi': round(profit/resolved*100, 1) if resolved > 0 else 0
        }
        
        logger.info("=" * 50)
        logger.info(f"📈 {report['total']} picks | {report['resolved']} résolus | {report['pending']} en attente")
        logger.info(f"   {report['wins']}W / {report['losses']}L = {report['win_rate']}% WR")
        logger.info(f"   Profit: {report['profit']} | ROI: {report['roi']}%")
        logger.info("=" * 50)
        
        return report
    
    # ============================================================
    # MODE SMART
    # ============================================================
    
    def should_collect(self) -> Tuple[bool, str, int]:
        """Vérifie si collecte nécessaire"""
        self._load_cache()
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT COUNT(DISTINCT match_id) as cnt
            FROM odds_history
            WHERE commence_time BETWEEN NOW() AND NOW() + INTERVAL '24 hours'
            AND match_id NOT IN (SELECT DISTINCT match_id FROM tracking_clv_picks WHERE match_id IS NOT NULL)
        """)
        
        r = cur.fetchone()
        cur.close()
        self.stats['db'] += 1
        
        cnt = r['cnt'] if r else 0
        if cnt > 0:
            return (True, f"{cnt} nouveaux matchs", cnt)
        return (False, "Aucun nouveau match", 0)
    
    def should_resolve(self) -> Tuple[bool, str, int]:
        """Vérifie si résolution nécessaire"""
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT COUNT(*) as cnt
            FROM tracking_clv_picks p
            JOIN odds_history o ON p.match_id = o.match_id
            WHERE p.is_resolved = false
            AND o.commence_time < NOW() - INTERVAL '2 hours'
        """)
        
        r = cur.fetchone()
        cur.close()
        self.stats['db'] += 1
        
        cnt = r['cnt'] if r else 0
        if cnt > 0:
            return (True, f"{cnt} picks prêts", cnt)
        return (False, "Rien à résoudre", 0)
    
    def run_smart(self) -> Dict:
        """Mode intelligent"""
        results = {'actions': []}
        
        logger.info("🧠 MODE SMART")
        
        should_c, reason_c, _ = self.should_collect()
        logger.info(f"  Collect: {should_c} ({reason_c})")
        if should_c:
            results['collect'] = self.collect()
            results['actions'].append('collect')
        
        should_r, reason_r, _ = self.should_resolve()
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
        """Point d'entrée"""
        if not self.acquire_lock():
            return {'error': 'Already running'}
        
        try:
            logger.info("=" * 60)
            logger.info(f"🤖 CLV ORCHESTRATOR HYBRID v{self.VERSION}")
            logger.info(f"   Mode: {task} | Dry-run: {self.dry_run}")
            logger.info("   ⚠️ 0 API EXTERNE - 100% données locales")
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
            logger.info(f"\n⏱️ {duration:.1f}s | DB: {self.stats['db']} | Erreurs: {self.stats['errors']}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='CLV Orchestrator Hybrid')
    parser.add_argument('task', nargs='?', default='smart',
                        choices=['collect', 'resolve', 'report', 'full', 'smart'])
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    
    orch = CLVOrchestratorHybrid(dry_run=args.dry_run)
    result = orch.run(args.task)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
