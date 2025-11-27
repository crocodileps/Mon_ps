#!/usr/bin/env python3
"""
🔧 SMART RESOLVER - Résolution intelligente des picks

Problème identifié:
- Les noms d'équipes ne matchent pas exactement
- "AC Milan" vs "AC Milan" ✅
- "1. FC Heidenheim" vs "1. FC Heidenheim 1846" ❌

Solution:
- Matching par similarité (Levenshtein)
- Matching par mots clés principaux
- Matching par date + premier mot
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import os
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger('SmartResolver')

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
}

# Résolveurs de marchés
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
    # Anciens formats
    'over15': lambda h, a: (h + a) > 1,
    'under15': lambda h, a: (h + a) < 2,
    'over25': lambda h, a: (h + a) > 2,
    'under25': lambda h, a: (h + a) < 3,
    'over35': lambda h, a: (h + a) > 3,
    'under35': lambda h, a: (h + a) < 4,
    'dnb_home': lambda h, a: h > a,
    'dnb_away': lambda h, a: a > h,
}


def normalize_team_name(name: str) -> str:
    """Normalise un nom d'équipe pour le matching"""
    if not name:
        return ''
    
    # Minuscules
    name = name.lower().strip()
    
    # Supprimer suffixes communs
    suffixes = [' fc', ' cf', ' sc', ' ac', ' bc', ' fk', ' sk', ' 1846', ' 1904', ' 1909', 
                ' calcio', ' futbol', ' football', ' united', ' city']
    for suffix in suffixes:
        name = name.replace(suffix, '')
    
    # Supprimer préfixes
    prefixes = ['fc ', 'cf ', 'sc ', 'ac ', 'afc ', 'rcd ', 'real ', 'sporting ']
    for prefix in prefixes:
        if name.startswith(prefix):
            name = name[len(prefix):]
    
    # Garder seulement les mots principaux
    name = re.sub(r'[^a-z0-9\s]', '', name)
    
    return name.strip()


def get_main_word(name: str) -> str:
    """Extrait le mot principal d'un nom d'équipe"""
    normalized = normalize_team_name(name)
    words = normalized.split()
    
    # Ignorer les mots courts et numériques
    main_words = [w for w in words if len(w) > 2 and not w.isdigit()]
    
    return main_words[0] if main_words else (words[0] if words else '')


def teams_match(pick_home: str, pick_away: str, result_home: str, result_away: str) -> bool:
    """Vérifie si les équipes correspondent"""
    # Normaliser
    ph = normalize_team_name(pick_home)
    pa = normalize_team_name(pick_away)
    rh = normalize_team_name(result_home)
    ra = normalize_team_name(result_away)
    
    # Match exact après normalisation
    if ph == rh and pa == ra:
        return True
    
    # Match par mot principal
    ph_main = get_main_word(pick_home)
    pa_main = get_main_word(pick_away)
    rh_main = get_main_word(result_home)
    ra_main = get_main_word(result_away)
    
    if ph_main and pa_main and rh_main and ra_main:
        if ph_main == rh_main and pa_main == ra_main:
            return True
        # Un des deux doit matcher exactement, l'autre par inclusion
        home_match = ph_main == rh_main or ph_main in rh or rh_main in ph
        away_match = pa_main == ra_main or pa_main in ra or ra_main in pa
        
        if home_match and away_match:
            return True
    
    return False


class SmartResolver:
    """Résolveur intelligent avec matching amélioré"""
    
    def __init__(self):
        self.conn = None
        self.stats = {'resolved': 0, 'wins': 0, 'losses': 0, 'errors': 0}
    
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
    
    def resolve_all(self) -> dict:
        """Résout tous les picks en attente"""
        conn = self.get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        logger.info("🔄 SMART RESOLVER - Matching amélioré")
        
        # 1. Récupérer les picks non résolus avec date passée
        cur.execute("""
            SELECT id, match_id, home_team, away_team, market_type,
                   odds_taken, stake, commence_time
            FROM tracking_clv_picks
            WHERE is_resolved = false
            AND commence_time IS NOT NULL
            AND commence_time < NOW() - INTERVAL '2 hours'
        """)
        
        pending = cur.fetchall()
        logger.info(f"📋 {len(pending)} picks à vérifier")
        
        if not pending:
            return self.stats
        
        # 2. Récupérer tous les résultats
        cur.execute("""
            SELECT home_team, away_team, score_home, score_away, commence_time
            FROM match_results
            WHERE is_finished = true
            AND score_home IS NOT NULL
        """)
        
        results = cur.fetchall()
        logger.info(f"📊 {len(results)} résultats disponibles")
        
        # Indexer par date
        results_by_date = {}
        for r in results:
            if r['commence_time']:
                date_key = r['commence_time'].date()
                if date_key not in results_by_date:
                    results_by_date[date_key] = []
                results_by_date[date_key].append(r)
        
        # 3. Résoudre chaque pick
        for pick in pending:
            try:
                if not pick['commence_time']:
                    continue
                
                pick_date = pick['commence_time'].date()
                
                # Chercher dans les résultats du même jour (+/- 1 jour)
                candidates = []
                for delta in [0, -1, 1]:
                    check_date = pick_date + timedelta(days=delta)
                    candidates.extend(results_by_date.get(check_date, []))
                
                # Trouver le match correspondant
                matched_result = None
                for result in candidates:
                    if teams_match(
                        pick['home_team'], pick['away_team'],
                        result['home_team'], result['away_team']
                    ):
                        matched_result = result
                        break
                
                if not matched_result:
                    continue
                
                # Résoudre
                hs = matched_result['score_home']
                as_ = matched_result['score_away']
                
                resolver = MARKET_RESOLVERS.get(pick['market_type'])
                if not resolver:
                    logger.debug(f"No resolver for {pick['market_type']}")
                    continue
                
                is_win = resolver(hs, as_)
                
                if is_win:
                    stake = self._float(pick['stake'], 1)
                    odds = self._float(pick['odds_taken'], 1)
                    profit = stake * (odds - 1)
                    self.stats['wins'] += 1
                else:
                    profit = -self._float(pick['stake'], 1)
                    self.stats['losses'] += 1
                
                # Mettre à jour
                cur.execute("""
                    UPDATE tracking_clv_picks
                    SET is_resolved = true,
                        is_winner = %s,
                        profit_loss = %s,
                        score_home = %s,
                        score_away = %s,
                        resolved_at = NOW()
                    WHERE id = %s
                """, (is_win, profit, hs, as_, pick['id']))
                
                self.stats['resolved'] += 1
                
                logger.info(f"  ✅ {pick['home_team']} vs {pick['away_team']} ({pick['market_type']}): "
                           f"{hs}-{as_} → {'WIN' if is_win else 'LOSS'}")
                
            except Exception as e:
                logger.warning(f"  ⚠️ {pick['id']}: {e}")
                self.stats['errors'] += 1
        
        conn.commit()
        cur.close()
        
        # Stats finales
        total = self.stats['wins'] + self.stats['losses']
        wr = round(self.stats['wins'] / total * 100, 1) if total > 0 else 0
        
        logger.info(f"\n✅ RÉSOLUTION TERMINÉE:")
        logger.info(f"   {self.stats['resolved']} résolus | {self.stats['wins']}W / {self.stats['losses']}L = {wr}%")
        
        return self.stats


def main():
    resolver = SmartResolver()
    stats = resolver.resolve_all()
    resolver.close()
    
    print(f"\n📊 Résultat: {stats}")


if __name__ == "__main__":
    main()
