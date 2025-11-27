#!/usr/bin/env python3
"""
🤖 ORCHESTRATEUR CLV TRACKER V3 - VERSION FINALE
Utilise les VRAIES tables existantes

SOURCES DE DONNÉES 100% LOCALES:
✅ odds_history   → Cotes 1X2 (home/draw/away)
✅ odds_totals    → Cotes Over/Under (2.5, 1.5, 3.5)
✅ team_statistics_live → Stats équipes (avg_goals_scored, btts_pct, etc.)
✅ match_results  → Résultats des matchs

⚠️ ZÉRO APPEL API - Tout est déjà collecté par les crons existants
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
from typing import Dict, List, Set, Tuple, Optional

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
        logging.FileHandler(LOG_DIR / f"v3_{datetime.now().strftime('%Y%m%d')}.log")
    ]
)
logger = logging.getLogger('CLV_V3')


# ============================================================
# CALCULS POISSON
# ============================================================

def poisson_prob(lam: float, k: int) -> float:
    """Probabilité Poisson P(X=k)"""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    try:
        return (math.exp(-lam) * (lam ** k)) / math.factorial(k)
    except:
        return 0.0


def calculate_all_probabilities(home_xg: float, away_xg: float) -> Dict[str, float]:
    """Calcule TOUTES les probabilités via Poisson"""
    max_goals = 7
    
    # Matrice des scores
    matrix = {}
    for h in range(max_goals):
        for a in range(max_goals):
            matrix[(h, a)] = poisson_prob(home_xg, h) * poisson_prob(away_xg, a)
    
    # Résultats 1X2
    home_win = sum(p for (h, a), p in matrix.items() if h > a)
    draw = sum(p for (h, a), p in matrix.items() if h == a)
    away_win = sum(p for (h, a), p in matrix.items() if h < a)
    
    # BTTS
    btts_yes = sum(p for (h, a), p in matrix.items() if h > 0 and a > 0)
    
    # Over/Under
    over_15 = sum(p for (h, a), p in matrix.items() if h + a > 1)
    over_25 = sum(p for (h, a), p in matrix.items() if h + a > 2)
    over_35 = sum(p for (h, a), p in matrix.items() if h + a > 3)
    
    return {
        # 1X2
        'home': home_win,
        'draw': draw,
        'away': away_win,
        # Double Chance
        'dc_1x': home_win + draw,
        'dc_x2': draw + away_win,
        'dc_12': home_win + away_win,
        # BTTS
        'btts_yes': btts_yes,
        'btts_no': 1 - btts_yes,
        # Over/Under
        'over_15': over_15,
        'under_15': 1 - over_15,
        'over_25': over_25,
        'under_25': 1 - over_25,
        'over_35': over_35,
        'under_35': 1 - over_35,
    }


def calculate_value_score(prob: float, odds: float) -> Tuple[int, float, str]:
    """
    Calcule le score de valeur d'un pari
    
    Args:
        prob: Probabilité estimée (0-1)
        odds: Cote du bookmaker
    
    Returns:
        (score 0-100, kelly%, rating)
    """
    if not odds or odds <= 1 or prob <= 0:
        return (0, 0, '❌ NO_VALUE')
    
    implied = 1 / odds
    edge = prob - implied
    
    # Kelly Criterion
    if edge > 0:
        kelly = min((edge / (odds - 1)) * 100, 10)  # Cap 10%
    else:
        kelly = 0
    
    # Score basé sur l'edge
    if edge >= 0.15:
        score = min(95, int(70 + edge * 100))
        rating = '🔥 EXCELLENT'
    elif edge >= 0.10:
        score = int(65 + edge * 50)
        rating = '✅ GOOD'
    elif edge >= 0.05:
        score = int(55 + edge * 50)
        rating = '📊 FAIR'
    elif edge > 0:
        score = int(45 + edge * 100)
        rating = '⚠️ MARGINAL'
    else:
        score = max(20, int(40 + edge * 100))
        rating = '❌ NO_VALUE'
    
    return (score, round(kelly, 2), rating)


# ============================================================
# RÉSOLVEURS DE MARCHÉS
# ============================================================

MARKET_RESOLVERS = {
    'home': lambda h, a: h > a,
    'draw': lambda h, a: h == a,
    'away': lambda h, a: h < a,
    'dc_1x': lambda h, a: h >= a,
    'dc_x2': lambda h, a: h <= a,
    'dc_12': lambda h, a: h != a,
    'btts_yes': lambda h, a: h > 0 and a > 0,
    'btts_no': lambda h, a: h == 0 or a == 0,
    'over_15': lambda h, a: (h + a) > 1,
    'under_15': lambda h, a: (h + a) < 2,
    'over_25': lambda h, a: (h + a) > 2,
    'under_25': lambda h, a: (h + a) < 3,
    'over_35': lambda h, a: (h + a) > 3,
    'under_35': lambda h, a: (h + a) < 4,
}


class CLVOrchestratorV3:
    """
    Orchestrateur V3 - Version Finale
    100% données locales, 0 API externe
    """
    
    VERSION = "3.0"
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.conn = None
        self.start_time = datetime.now()
        self._tracked: Set[str] = set()
        self._cache_loaded = False
        self.stats = {'db': 0, 'created': 0, 'resolved': 0, 'errors': 0}
    
    def get_db(self):
        """Connexion avec auto-reconnexion"""
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
            self.conn.autocommit = False
        return self.conn
    
    def close(self):
        if self.conn and not self.conn.closed:
            self.conn.close()
    
    def _float(self, v, default=0.0) -> float:
        if v is None:
            return default
        if isinstance(v, Decimal):
            return float(v)
        try:
            return float(v)
        except:
            return default
    
    def _rollback(self):
        """Rollback en cas d'erreur"""
        try:
            if self.conn and not self.conn.closed:
                self.conn.rollback()
        except:
            pass
    
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
        except:
            pass
    
    # ============================================================
    # CACHE
    # ============================================================
    
    def _load_cache(self):
        if self._cache_loaded:
            return
        try:
            conn = self.get_db()
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT match_id FROM tracking_clv_picks WHERE match_id IS NOT NULL")
            self._tracked = {r[0] for r in cur.fetchall()}
            cur.close()
            conn.commit()
            self._cache_loaded = True
            self.stats['db'] += 1
            logger.info(f"📦 Cache: {len(self._tracked)} matchs trackés")
        except Exception as e:
            logger.error(f"Cache error: {e}")
            self._rollback()
    
    # ============================================================
    # RÉCUPÉRATION DONNÉES LOCALES
    # ============================================================
    
    def get_team_stats(self, team_name: str) -> Dict:
        """
        Récupère les stats d'une équipe depuis team_statistics_live
        Utilise les VRAIES colonnes existantes
        """
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Recherche fuzzy par premier mot du nom
            first_word = team_name.split()[0].lower() if team_name else ''
            
            cur.execute("""
                SELECT 
                    avg_goals_scored,
                    avg_goals_conceded,
                    btts_pct,
                    over_25_pct,
                    over_15_pct,
                    over_35_pct,
                    home_avg_scored,
                    home_avg_conceded,
                    away_avg_scored,
                    away_avg_conceded,
                    home_btts_pct,
                    home_over25_pct,
                    away_btts_pct,
                    away_over25_pct,
                    last5_goals_for,
                    last5_goals_against,
                    form,
                    data_quality_score
                FROM team_statistics_live
                WHERE LOWER(team_name) ILIKE %s
                ORDER BY updated_at DESC
                LIMIT 1
            """, (f'%{first_word}%',))
            
            result = cur.fetchone()
            cur.close()
            conn.commit()
            self.stats['db'] += 1
            
            if result:
                return dict(result)
            
            # Valeurs par défaut si équipe non trouvée
            return {
                'avg_goals_scored': 1.3,
                'avg_goals_conceded': 1.2,
                'btts_pct': 50,
                'over_25_pct': 50,
            }
            
        except Exception as e:
            logger.debug(f"Stats error for {team_name}: {e}")
            self._rollback()
            return {'avg_goals_scored': 1.3, 'avg_goals_conceded': 1.2}
    
    def get_matches_to_track(self) -> List[Dict]:
        """
        Récupère les matchs à tracker depuis odds_history + odds_totals
        Combine les cotes 1X2 et Over/Under
        """
        self._load_cache()
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Matchs avec cotes 1X2 dans les 48h
            cur.execute("""
                WITH latest_1x2 AS (
                    SELECT DISTINCT ON (match_id)
                        match_id, home_team, away_team, sport as league,
                        commence_time, home_odds, draw_odds, away_odds
                    FROM odds_history
                    WHERE commence_time BETWEEN NOW() AND NOW() + INTERVAL '48 hours'
                    ORDER BY match_id, collected_at DESC
                ),
                latest_totals AS (
                    SELECT DISTINCT ON (match_id, line)
                        match_id, line, over_odds, under_odds
                    FROM odds_totals
                    WHERE commence_time BETWEEN NOW() AND NOW() + INTERVAL '48 hours'
                    AND line IN (1.5, 2.5, 3.5)
                    ORDER BY match_id, line, collected_at DESC
                ),
                totals_pivot AS (
                    SELECT 
                        match_id,
                        MAX(CASE WHEN line = 1.5 THEN over_odds END) as over_15_odds,
                        MAX(CASE WHEN line = 1.5 THEN under_odds END) as under_15_odds,
                        MAX(CASE WHEN line = 2.5 THEN over_odds END) as over_25_odds,
                        MAX(CASE WHEN line = 2.5 THEN under_odds END) as under_25_odds,
                        MAX(CASE WHEN line = 3.5 THEN over_odds END) as over_35_odds,
                        MAX(CASE WHEN line = 3.5 THEN under_odds END) as under_35_odds
                    FROM latest_totals
                    GROUP BY match_id
                )
                SELECT 
                    h.match_id, h.home_team, h.away_team, h.league, h.commence_time,
                    h.home_odds, h.draw_odds, h.away_odds,
                    t.over_15_odds, t.under_15_odds,
                    t.over_25_odds, t.under_25_odds,
                    t.over_35_odds, t.under_35_odds
                FROM latest_1x2 h
                LEFT JOIN totals_pivot t ON h.match_id = t.match_id
                ORDER BY h.commence_time
            """)
            
            matches = cur.fetchall()
            cur.close()
            conn.commit()
            self.stats['db'] += 1
            
            # Filtrer ceux déjà trackés
            new_matches = [m for m in matches if m['match_id'] not in self._tracked]
            
            logger.info(f"�� {len(new_matches)} nouveaux / {len(matches)} total")
            
            return new_matches
            
        except Exception as e:
            logger.error(f"Get matches error: {e}")
            self._rollback()
            return []
    
    # ============================================================
    # COLLECTE
    # ============================================================
    
    def collect(self) -> Dict:
        """
        Collecte 100% LOCALE
        1. Récupère matchs depuis odds_history + odds_totals
        2. Récupère stats équipes depuis team_statistics_live
        3. Calcule probabilités Poisson
        4. Génère les picks avec scores de valeur
        """
        start = datetime.now()
        logger.info("🚀 COLLECT V3 - 100% local")
        
        matches = self.get_matches_to_track()
        
        if not matches:
            logger.info("✅ Aucun nouveau match")
            return {'created': 0, 'matches': 0}
        
        created = 0
        
        for match in matches:
            try:
                # 1. Récupérer stats équipes
                home_stats = self.get_team_stats(match['home_team'])
                away_stats = self.get_team_stats(match['away_team'])
                
                # 2. Calculer xG (avec home advantage)
                home_xg = self._float(home_stats.get('avg_goals_scored'), 1.3) * 1.1
                away_xg = self._float(away_stats.get('avg_goals_scored'), 1.3) * 0.9
                
                # Ajuster avec goals concédés
                home_xg = (home_xg + self._float(away_stats.get('avg_goals_conceded'), 1.2)) / 2
                away_xg = (away_xg + self._float(home_stats.get('avg_goals_conceded'), 1.2)) / 2
                
                # 3. Calculer probabilités Poisson
                probs = calculate_all_probabilities(home_xg, away_xg)
                
                # 4. Générer les picks pour chaque marché
                picks = []
                
                # 1X2
                for mtype, odds_col in [
                    ('home', 'home_odds'),
                    ('draw', 'draw_odds'),
                    ('away', 'away_odds')
                ]:
                    odds = self._float(match.get(odds_col))
                    if odds > 1:
                        score, kelly, rating = calculate_value_score(probs[mtype], odds)
                        if score >= 45:  # Seuil minimum
                            picks.append({
                                'market_type': mtype,
                                'prediction': mtype,
                                'odds': odds,
                                'probability': probs[mtype],
                                'score': score,
                                'kelly': kelly,
                                'rating': rating
                            })
                
                # Double Chance (calculer cotes depuis 1X2)
                home_odds = self._float(match.get('home_odds'), 0)
                draw_odds = self._float(match.get('draw_odds'), 0)
                away_odds = self._float(match.get('away_odds'), 0)
                
                if home_odds > 1 and draw_odds > 1:
                    dc_1x_odds = 1 / (1/home_odds + 1/draw_odds)
                    score, kelly, rating = calculate_value_score(probs['dc_1x'], dc_1x_odds)
                    if score >= 45:
                        picks.append({
                            'market_type': 'dc_1x', 'prediction': '1X',
                            'odds': dc_1x_odds, 'probability': probs['dc_1x'],
                            'score': score, 'kelly': kelly, 'rating': rating
                        })
                
                if draw_odds > 1 and away_odds > 1:
                    dc_x2_odds = 1 / (1/draw_odds + 1/away_odds)
                    score, kelly, rating = calculate_value_score(probs['dc_x2'], dc_x2_odds)
                    if score >= 45:
                        picks.append({
                            'market_type': 'dc_x2', 'prediction': 'X2',
                            'odds': dc_x2_odds, 'probability': probs['dc_x2'],
                            'score': score, 'kelly': kelly, 'rating': rating
                        })
                
                if home_odds > 1 and away_odds > 1:
                    dc_12_odds = 1 / (1/home_odds + 1/away_odds)
                    score, kelly, rating = calculate_value_score(probs['dc_12'], dc_12_odds)
                    if score >= 45:
                        picks.append({
                            'market_type': 'dc_12', 'prediction': '12',
                            'odds': dc_12_odds, 'probability': probs['dc_12'],
                            'score': score, 'kelly': kelly, 'rating': rating
                        })
                
                # Over/Under (depuis odds_totals)
                for mtype, odds_col, prob_key in [
                    ('over_15', 'over_15_odds', 'over_15'),
                    ('under_15', 'under_15_odds', 'under_15'),
                    ('over_25', 'over_25_odds', 'over_25'),
                    ('under_25', 'under_25_odds', 'under_25'),
                    ('over_35', 'over_35_odds', 'over_35'),
                    ('under_35', 'under_35_odds', 'under_35'),
                ]:
                    odds = self._float(match.get(odds_col))
                    if odds > 1:
                        score, kelly, rating = calculate_value_score(probs[prob_key], odds)
                        if score >= 45:
                            picks.append({
                                'market_type': mtype,
                                'prediction': mtype.replace('_', ' '),
                                'odds': odds,
                                'probability': probs[prob_key],
                                'score': score,
                                'kelly': kelly,
                                'rating': rating
                            })
                
                # BTTS (estimer cotes si pas disponibles)
                btts_yes_odds = 1 / probs['btts_yes'] * 0.92 if probs['btts_yes'] > 0.1 else 0
                btts_no_odds = 1 / probs['btts_no'] * 0.92 if probs['btts_no'] > 0.1 else 0
                
                if btts_yes_odds > 1.1:
                    score, kelly, rating = calculate_value_score(probs['btts_yes'], btts_yes_odds)
                    if score >= 45:
                        picks.append({
                            'market_type': 'btts_yes', 'prediction': 'Yes',
                            'odds': btts_yes_odds, 'probability': probs['btts_yes'],
                            'score': score, 'kelly': kelly, 'rating': rating
                        })
                
                if btts_no_odds > 1.1:
                    score, kelly, rating = calculate_value_score(probs['btts_no'], btts_no_odds)
                    if score >= 45:
                        picks.append({
                            'market_type': 'btts_no', 'prediction': 'No',
                            'odds': btts_no_odds, 'probability': probs['btts_no'],
                            'score': score, 'kelly': kelly, 'rating': rating
                        })
                
                # 5. Sauvegarder
                if picks:
                    saved = self._save_picks(match, picks, home_xg, away_xg)
                    created += saved
                    if saved > 0:
                        self._tracked.add(match['match_id'])
                        logger.info(f"  ✅ {match['home_team']} vs {match['away_team']}: {saved} marchés")
                        
            except Exception as e:
                logger.warning(f"  ⚠️ {match.get('match_id', 'unknown')}: {e}")
                self.stats['errors'] += 1
                self._rollback()
        
        self.stats['created'] += created
        duration = (datetime.now() - start).total_seconds()
        logger.info(f"✅ COLLECT: {created} picks | {duration:.1f}s | 0 API")
        
        return {'created': created, 'matches': len(matches), 'duration': duration}
    
    def _save_picks(self, match: Dict, picks: List[Dict], home_xg: float, away_xg: float) -> int:
        """Sauvegarde les picks en batch"""
        if self.dry_run:
            return len(picks)
        
        conn = self.get_db()
        cur = conn.cursor()
        saved = 0
        
        for pick in picks:
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
                    match['match_id'],
                    match['home_team'],
                    match['away_team'],
                    match.get('league', ''),
                    f"{match['home_team']} vs {match['away_team']}",
                    pick['market_type'],
                    pick['prediction'],
                    pick['score'],
                    pick['odds'],
                    pick['probability'] * 100,
                    pick['kelly'],
                    pick['rating'],
                    home_xg,
                    away_xg,
                    home_xg + away_xg,
                    pick['probability'] * 100,
                    pick['score'] >= 70,
                    'orchestrator_v3',
                    pick['score'] / 100
                ))
                if cur.rowcount > 0:
                    saved += 1
            except Exception as e:
                logger.debug(f"Insert error: {e}")
                self._rollback()
        
        conn.commit()
        cur.close()
        self.stats['db'] += 1
        return saved
    
    # ============================================================
    # RÉSOLUTION
    # ============================================================
    
    def resolve(self) -> Dict:
        """
        Résolution 100% LOCALE via match_results
        """
        start = datetime.now()
        logger.info("🔄 RESOLVE V3")
        
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Picks non résolus avec match terminé
            cur.execute("""
                SELECT 
                    p.id, p.home_team, p.away_team, p.market_type,
                    p.odds_taken, p.stake, p.match_id,
                    o.commence_time
                FROM tracking_clv_picks p
                JOIN odds_history o ON p.match_id = o.match_id
                WHERE p.is_resolved = false
                AND o.commence_time < NOW() - INTERVAL '2 hours'
                GROUP BY p.id, p.home_team, p.away_team, p.market_type,
                         p.odds_taken, p.stake, p.match_id, o.commence_time
            """)
            
            pending = cur.fetchall()
            conn.commit()
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
                
                # Chercher résultat
                cur.execute("""
                    SELECT score_home, score_away
                    FROM match_results
                    WHERE is_finished = true
                    AND DATE(match_date) BETWEEN %s AND %s
                    AND LOWER(home_team) ILIKE %s
                    AND LOWER(away_team) ILIKE %s
                    LIMIT 1
                """, (
                    mdate - timedelta(days=1),
                    mdate + timedelta(days=1),
                    f'%{home.split()[0]}%',
                    f'%{away.split()[0]}%'
                ))
                
                result = cur.fetchone()
                self.stats['db'] += 1
                
                if not result:
                    continue
                
                hs, as_ = result['score_home'], result['score_away']
                logger.info(f"  ✅ {home} vs {away}: {hs}-{as_}")
                
                for pick in picks:
                    resolver = MARKET_RESOLVERS.get(pick['market_type'])
                    if not resolver:
                        continue
                    
                    is_win = resolver(hs, as_)
                    
                    if is_win:
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
            wr = round(wins / (wins + losses) * 100, 1) if (wins + losses) > 0 else 0
            duration = (datetime.now() - start).total_seconds()
            
            logger.info(f"✅ RESOLVE: {resolved} ({wins}W/{losses}L = {wr}%) | {duration:.1f}s")
            
            return {'resolved': resolved, 'wins': wins, 'losses': losses, 'win_rate': wr}
            
        except Exception as e:
            logger.error(f"Resolve error: {e}")
            self._rollback()
            return {'resolved': 0, 'wins': 0, 'losses': 0, 'error': str(e)}
    
    # ============================================================
    # RAPPORT
    # ============================================================
    
    def report(self, days: int = 7) -> Dict:
        """Rapport de performance"""
        logger.info(f"📊 REPORT ({days}j)")
        
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
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
            conn.commit()
            self.stats['db'] += 1
            
            resolved = int(s['resolved'] or 0)
            wins = int(s['wins'] or 0)
            losses = int(s['losses'] or 0)
            profit = self._float(s['profit'])
            
            report = {
                'period': f'{days}j',
                'total': int(s['total'] or 0),
                'resolved': resolved,
                'pending': int(s['total'] or 0) - resolved,
                'wins': wins,
                'losses': losses,
                'win_rate': round(wins / resolved * 100, 1) if resolved > 0 else 0,
                'profit': round(profit, 2),
                'roi': round(profit / resolved * 100, 1) if resolved > 0 else 0,
                'avg_score': round(self._float(s['avg_score']), 1)
            }
            
            logger.info("=" * 50)
            logger.info(f"📈 {report['total']} picks | {report['resolved']} résolus | {report['pending']} en attente")
            logger.info(f"   {report['wins']}W / {report['losses']}L = {report['win_rate']}% WR")
            logger.info(f"   Profit: {report['profit']} | ROI: {report['roi']}%")
            logger.info("=" * 50)
            
            return report
            
        except Exception as e:
            logger.error(f"Report error: {e}")
            self._rollback()
            return {}
    
    # ============================================================
    # MODE SMART
    # ============================================================
    
    def should_collect(self) -> Tuple[bool, str, int]:
        """Vérifie si collecte nécessaire"""
        self._load_cache()
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cur.execute("""
                SELECT COUNT(DISTINCT match_id) as cnt
                FROM odds_history
                WHERE commence_time BETWEEN NOW() AND NOW() + INTERVAL '24 hours'
                AND match_id NOT IN (
                    SELECT DISTINCT match_id FROM tracking_clv_picks WHERE match_id IS NOT NULL
                )
            """)
            
            r = cur.fetchone()
            cur.close()
            conn.commit()
            self.stats['db'] += 1
            
            cnt = r['cnt'] if r else 0
            if cnt > 0:
                return (True, f"{cnt} nouveaux matchs", cnt)
            return (False, "Aucun nouveau match", 0)
            
        except Exception as e:
            logger.error(f"Should collect error: {e}")
            self._rollback()
            return (False, str(e), 0)
    
    def should_resolve(self) -> Tuple[bool, str, int]:
        """Vérifie si résolution nécessaire"""
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cur.execute("""
                SELECT COUNT(*) as cnt
                FROM tracking_clv_picks p
                JOIN odds_history o ON p.match_id = o.match_id
                WHERE p.is_resolved = false
                AND o.commence_time < NOW() - INTERVAL '2 hours'
            """)
            
            r = cur.fetchone()
            cur.close()
            conn.commit()
            self.stats['db'] += 1
            
            cnt = r['cnt'] if r else 0
            if cnt > 0:
                return (True, f"{cnt} picks prêts", cnt)
            return (False, "Rien à résoudre", 0)
            
        except Exception as e:
            logger.error(f"Should resolve error: {e}")
            self._rollback()
            return (False, str(e), 0)
    
    def run_smart(self) -> Dict:
        """Mode intelligent"""
        results = {'actions': [], 'api_calls': 0}
        
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
            logger.info(f"🤖 CLV ORCHESTRATOR V{self.VERSION}")
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
            logger.info(f"\n⏱️ {duration:.1f}s | DB: {self.stats['db']} | Erreurs: {self.stats['errors']} | API: 0")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='CLV Orchestrator V3')
    parser.add_argument('task', nargs='?', default='smart',
                        choices=['collect', 'resolve', 'report', 'full', 'smart'])
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    
    orch = CLVOrchestratorV3(dry_run=args.dry_run)
    result = orch.run(args.task)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
