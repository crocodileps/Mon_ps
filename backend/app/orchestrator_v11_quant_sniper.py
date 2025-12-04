#!/usr/bin/env python3
"""
ORCHESTRATOR V11 - QUANT 2.0 SNIPER (CALIBRATED)
═══════════════════════════════════════════════════════════════════════════════
CORRECTIONS APPLIQUÉES (Audit Expert 2025-12-04):
1. Bonus "Elite Attack" - Pas de régression xG pour équipes power > 85
2. Convergence parfaite (+100%) = +30 pts au lieu de +20
3. Seuils ajustés: SNIPER 50, NORMAL 35
4. Poids xG réduit de 8 à 5 (moins punitif)
5. Injuries: Seuls les top scorers (goals_per_90 > 0.5) pénalisent
═══════════════════════════════════════════════════════════════════════════════
"""

import psycopg2
import psycopg2.extras
import logging
import sys
from typing import Dict, Optional
from decimal import Decimal

sys.path.insert(0, '/home/Mon_ps/backend/scripts/analytics')

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': 'localhost', 'port': 5432, 'dbname': 'monps_db',
    'user': 'monps_user', 'password': 'monps_secure_password_2024'
}

# ═══════════════════════════════════════════════════════════════════════════════
# SEUILS CALIBRÉS (Ajustés après audit expert)
# ═══════════════════════════════════════════════════════════════════════════════
SNIPER_THRESHOLD = 50      # Abaissé de 55 à 50
NORMAL_THRESHOLD = 35      # Abaissé de 40 à 35

# Poids calibrés
WEIGHTS = {
    'base': 10,
    'tactical': 15,
    'team_class': 10,
    'h2h': 8,
    'coach': 3,
    'referee': 2,
    'injuries': -8,         # Réduit de -10 à -8
    'xg': 5,                # Réduit de 8 à 5 (moins punitif)
    'convergence': 30,      # Augmenté de 25 à 30 (signal le plus fort)
}

# Seuil pour ignorer la régression xG (équipes d'élite)
ELITE_POWER_THRESHOLD = 85

# Seuil pour pénaliser une blessure (buteur significatif)
KEY_SCORER_THRESHOLD = 0.5  # goals_per_90 minimum

# Mapping styles
STYLE_MAPPING = {
    'offensive': 'attacking',
    'defensive': 'defensive', 
    'balanced': 'balanced',
    'possession': 'possession',
    'counter': 'counter_attack',
    'high_press': 'high_press',
    'gegenpressing': 'gegenpressing',
    'tiki_taka': 'tiki_taka',
    'direct': 'direct_play',
    'low_block': 'low_block_counter',
    'park_the_bus': 'park_the_bus',
    'pressing': 'pressing',
}


def to_float(val, default=0.0):
    if val is None:
        return default
    if isinstance(val, Decimal):
        return float(val)
    return float(val)


class OrchestratorV11QuantSniper:
    def __init__(self):
        self.conn = None
        self.cache = {}
        self._load_cache()
    
    def _get_conn(self):
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
        return self.conn
    
    def _normalize_style(self, style: str) -> str:
        if not style:
            return 'balanced'
        return STYLE_MAPPING.get(style.lower().strip(), style.lower().strip())
    
    def _find_team(self, team_name: str, table: str) -> Optional[str]:
        cur = self._get_conn().cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(f"SELECT team_name FROM {table} WHERE team_name = %s LIMIT 1", (team_name,))
        r = cur.fetchone()
        if r:
            return r['team_name']
        cur.execute(f"SELECT team_name FROM {table} WHERE team_name ILIKE %s LIMIT 1", (f'%{team_name}%',))
        r = cur.fetchone()
        return r['team_name'] if r else None
    
    def _get_team_power(self, team: str) -> float:
        """Récupère le power index d'une équipe"""
        t = self._find_team(team, 'team_class')
        if t and t in self.cache['team_class']:
            return to_float(self.cache['team_class'][t].get('calculated_power_index'), 50)
        return 50
    
    def _load_cache(self):
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("SELECT * FROM tactical_matrix")
        self.cache['tactical'] = {(r['style_a'], r['style_b']): r for r in cur.fetchall()}
        
        cur.execute("SELECT * FROM team_class")
        self.cache['team_class'] = {r['team_name']: r for r in cur.fetchall()}
        
        cur.execute("SELECT * FROM referee_intelligence")
        self.cache['referees'] = {r['referee_name']: r for r in cur.fetchall()}
        
        logger.info(f"Cache: {len(self.cache['tactical'])} tactical, {len(self.cache['team_class'])} teams")
    
    def get_team_intel(self, team: str) -> Optional[Dict]:
        team_found = self._find_team(team, 'team_intelligence')
        if not team_found:
            return None
        cur = self._get_conn().cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM team_intelligence WHERE team_name = %s ORDER BY updated_at DESC LIMIT 1", (team_found,))
        return cur.fetchone()
    
    def analyze_tactical(self, home: str, away: str) -> Dict:
        home_intel = self.get_team_intel(home)
        away_intel = self.get_team_intel(away)
        
        if not home_intel or not away_intel:
            return {'score': 0, 'btts': 50, 'over25': 50, 'reason': 'No team intelligence'}
        
        h_style = self._normalize_style(home_intel.get('current_style'))
        a_style = self._normalize_style(away_intel.get('current_style'))
        
        matchup = self.cache['tactical'].get((h_style, a_style))
        if not matchup:
            matchup = self.cache['tactical'].get((a_style, h_style))
        
        if matchup:
            btts = to_float(matchup.get('btts_probability'), 50)
            over25 = to_float(matchup.get('over_25_probability'), 50)
            goals = to_float(matchup.get('avg_goals_total'), 2.5)
            
            score = (abs(btts - 50) + abs(over25 - 50)) * 0.2
            if over25 > 70 or btts > 70:
                score += 5
            
            return {
                'score': min(WEIGHTS['tactical'], score),
                'btts': btts, 'over25': over25, 'goals': goals,
                'reason': f'{h_style} vs {a_style}: BTTS {btts:.0f}%, O2.5 {over25:.0f}%'
            }
        
        return {'score': 0, 'btts': 50, 'over25': 50, 'reason': f'{h_style} vs {a_style}: No matrix'}
    
    def analyze_team_class(self, home: str, away: str) -> Dict:
        h_name = self._find_team(home, 'team_class')
        a_name = self._find_team(away, 'team_class')
        
        h_class = self.cache['team_class'].get(h_name, {}) if h_name else {}
        a_class = self.cache['team_class'].get(a_name, {}) if a_name else {}
        
        if not h_class and not a_class:
            return {'score': 0, 'reason': 'No class data'}
        
        h_power = to_float(h_class.get('calculated_power_index'), 50)
        a_power = to_float(a_class.get('calculated_power_index'), 50)
        h_fortress = to_float(h_class.get('home_fortress_factor'), 1.0)
        
        diff = h_power - a_power
        score = abs(diff) * 0.15 + (h_fortress - 1.0) * 5
        
        # BONUS: Les deux équipes sont d'élite → match spectaculaire probable
        if h_power > ELITE_POWER_THRESHOLD and a_power > ELITE_POWER_THRESHOLD:
            score += 3
        
        return {
            'score': min(WEIGHTS['team_class'], score),
            'power_diff': diff,
            'h_power': h_power,
            'a_power': a_power,
            'reason': f'H:{h_power:.0f} vs A:{a_power:.0f} (Δ{diff:+.0f})'
        }
    
    def analyze_h2h(self, home: str, away: str) -> Dict:
        cur = self._get_conn().cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("""
            SELECT * FROM head_to_head 
            WHERE (team_a ILIKE %s AND team_b ILIKE %s) 
               OR (team_a ILIKE %s AND team_b ILIKE %s)
            LIMIT 1
        """, (f'%{home}%', f'%{away}%', f'%{away}%', f'%{home}%'))
        
        h2h = cur.fetchone()
        
        if not h2h or h2h.get('total_matches', 0) < 2:
            # AMÉLIORATION: Si pas de H2H, donner un petit bonus neutre au lieu de 0
            return {'score': 1, 'reason': 'H2H < 2 matchs (bonus neutre)'}
        
        over_pct = to_float(h2h.get('over_25_percentage'), 50)
        btts_pct = to_float(h2h.get('btts_percentage'), 50)
        matches = h2h['total_matches']
        
        clarity = (abs(over_pct - 50) + abs(btts_pct - 50)) * 0.12
        sample_weight = min(1.0, matches / 5)
        score = clarity * sample_weight
        
        if over_pct > 75 or over_pct < 25:
            score += 3
        if btts_pct > 75 or btts_pct < 25:
            score += 2
        
        return {
            'score': min(WEIGHTS['h2h'], score),
            'over_pct': over_pct, 'btts_pct': btts_pct,
            'reason': f'{matches} H2H: O2.5 {over_pct:.0f}%, BTTS {btts_pct:.0f}%'
        }
    
    def analyze_injuries(self, home: str, away: str) -> Dict:
        cur = self._get_conn().cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("""
            SELECT player_name, current_team, goals_per_90 
            FROM scorer_intelligence 
            WHERE (current_team ILIKE %s OR current_team ILIKE %s) 
            AND is_injured = true
            ORDER BY goals_per_90 DESC NULLS LAST
            LIMIT 10
        """, (f'%{home}%', f'%{away}%'))
        
        injured = cur.fetchall()
        
        if not injured:
            return {'score': 0, 'reason': 'No injuries'}
        
        # AMÉLIORATION: Seuls les TOP scorers (goals_per_90 > 0.5) pénalisent
        penalty = 0
        key_names = []
        for p in injured:
            g90 = to_float(p.get('goals_per_90'), 0)
            if g90 > KEY_SCORER_THRESHOLD:  # Seulement les vrais buteurs
                penalty += min(2.5, g90 * 3)
                key_names.append(p['player_name'][:12])
        
        if not key_names:
            return {'score': 0, 'reason': f'{len(injured)} blessés mineurs'}
        
        return {
            'score': -min(abs(WEIGHTS['injuries']), penalty),
            'reason': f"KEY: {', '.join(key_names[:2])}"
        }
    
    def analyze_xg(self, home: str, away: str) -> Dict:
        cur = self._get_conn().cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        cur.execute("""
            SELECT team_name, avg_xg_for, avg_performance 
            FROM team_xg_tendencies 
            WHERE team_name ILIKE %s OR team_name ILIKE %s
        """, (f'%{home}%', f'%{away}%'))
        
        data = {r['team_name']: r for r in cur.fetchall()}
        
        if not data:
            return {'score': 0, 'reason': 'No xG data'}
        
        # Récupérer les power indexes pour le bonus élite
        home_power = self._get_team_power(home)
        away_power = self._get_team_power(away)
        
        regression = 0
        reasons = []
        
        for team_name, team_data in data.items():
            luck = to_float(team_data.get('avg_performance'), 0)
            
            # AMÉLIORATION: Ignorer régression négative pour équipes d'élite
            # Les élites surperforment structurellement (Kane, Haaland, etc.)
            is_elite = (team_name.lower() in home.lower() and home_power > ELITE_POWER_THRESHOLD) or \
                       (team_name.lower() in away.lower() and away_power > ELITE_POWER_THRESHOLD)
            
            if luck > 0.3 and not is_elite:  # Overperforming non-élite
                regression -= luck * 3
                reasons.append(f"{team_name[:10]} lucky +{luck:.2f}")
            elif luck > 0.3 and is_elite:  # Overperforming élite → normal
                reasons.append(f"{team_name[:10]} elite +{luck:.2f} (OK)")
            elif luck < -0.25:  # Underperforming → regression up
                regression += abs(luck) * 4
                reasons.append(f"{team_name[:10]} unlucky {luck:.2f}")
        
        return {
            'score': max(-WEIGHTS['xg'], min(WEIGHTS['xg'], regression)),
            'reason': '; '.join(reasons) if reasons else 'Normal xG'
        }
    
    def analyze_convergence(self, home: str, away: str, market: str = None) -> Dict:
        try:
            from market_convergence_engine import MarketConvergenceEngine
            engine = MarketConvergenceEngine()
            result = engine.get_orchestrator_modifier(home, away, market)
            
            base_score = result.get('score_modifier', 0)
            
            # AMÉLIORATION: Convergence parfaite (action = STRONG_BET) → bonus max
            if result.get('convergence_action') == 'STRONG_BET':
                base_score = min(WEIGHTS['convergence'], base_score + 10)  # +10 bonus
            
            return {
                'score': base_score,
                'market': result.get('recommended_market'),
                'action': result.get('convergence_action'),
                'clash': result.get('markets_clash', False),
                'reason': result.get('reasoning', '')[:50]
            }
        except Exception as e:
            logger.warning(f"Convergence error: {e}")
            return {'score': 0, 'reason': str(e)[:30]}
    
    def analyze_match(self, home: str, away: str, market: str = 'over_25', verbose: bool = True) -> Dict:
        layers = {
            'tactical': self.analyze_tactical(home, away),
            'team_class': self.analyze_team_class(home, away),
            'h2h': self.analyze_h2h(home, away),
            'injuries': self.analyze_injuries(home, away),
            'xg': self.analyze_xg(home, away),
            'convergence': self.analyze_convergence(home, away, market)
        }
        
        total = WEIGHTS['base']
        for layer_data in layers.values():
            total += layer_data.get('score', 0)
        
        if layers['convergence'].get('clash'):
            action = 'BLOCKED'
            confidence = 20
        elif total >= SNIPER_THRESHOLD:
            action = 'SNIPER_BET'
            confidence = min(95, 55 + total * 0.7)
        elif total >= NORMAL_THRESHOLD:
            action = 'NORMAL_BET'
            confidence = min(85, 45 + total * 0.6)
        else:
            action = 'SKIP'
            confidence = max(20, 25 + total * 0.4)
        
        recommended = layers['convergence'].get('market') or market
        tactical = layers['tactical']
        
        result = {
            'home': home, 'away': away,
            'target_market': market,
            'recommended_market': recommended,
            'score': round(total, 1),
            'action': action,
            'confidence': round(confidence, 1),
            'btts_prob': tactical.get('btts', 50),
            'over25_prob': tactical.get('over25', 50),
            'layers': layers
        }
        
        if verbose:
            self._print(result)
        
        return result
    
    def _print(self, r: Dict):
        emojis = {'SNIPER_BET': '🎯', 'NORMAL_BET': '✅', 'SKIP': '❌', 'BLOCKED': '🚫'}
        colors = {'SNIPER_BET': '🔥', 'NORMAL_BET': '💚', 'SKIP': '⚪', 'BLOCKED': '🔴'}
        
        print(f"\n{'═'*65}")
        print(f"🏟️  {r['home']} vs {r['away']}")
        print(f"{'═'*65}")
        
        e = emojis.get(r['action'], '?')
        c = colors.get(r['action'], '')
        print(f"\n   {e} {c} {r['action']} | Score: {r['score']:.0f}/80 | Conf: {r['confidence']:.0f}%")
        print(f"   🎯 Marché: {r['recommended_market']}")
        print(f"   📊 BTTS: {r['btts_prob']:.0f}% | Over 2.5: {r['over25_prob']:.0f}%")
        
        print(f"\n   📈 BREAKDOWN:")
        print(f"      {'Base':14s}: +{WEIGHTS['base']:.0f}")
        for name, data in r['layers'].items():
            s = data.get('score', 0)
            reason = data.get('reason', '')[:42]
            sign = '+' if s >= 0 else ''
            print(f"      {name:14s}: {sign}{s:.1f}  → {reason}")


def test():
    orch = OrchestratorV11QuantSniper()
    
    print("═"*65)
    print("TEST ORCHESTRATOR V11 QUANT SNIPER (CALIBRATED)")
    print("═"*65)
    print(f"Seuils: SNIPER={SNIPER_THRESHOLD}, NORMAL={NORMAL_THRESHOLD}")
    print(f"Weights: convergence={WEIGHTS['convergence']}, xg={WEIGHTS['xg']}")
    
    matches = [
        ('Liverpool', 'Arsenal', 'over_25'),
        ('Bayern Munich', 'Barcelona', 'btts_yes'),
        ('Real Madrid', 'Barcelona', 'over_25'),
        ('Inter', 'AC Milan', 'btts_yes'),
        ('Manchester City', 'Chelsea', 'over_25'),
    ]
    
    results = []
    for h, a, m in matches:
        results.append(orch.analyze_match(h, a, m))
    
    print("\n" + "═"*65)
    print("RÉSUMÉ")
    print("═"*65)
    
    sniper = sum(1 for r in results if r['action'] == 'SNIPER_BET')
    normal = sum(1 for r in results if r['action'] == 'NORMAL_BET')
    skip = sum(1 for r in results if r['action'] == 'SKIP')
    
    for r in results:
        e = {'SNIPER_BET': '🎯', 'NORMAL_BET': '✅', 'SKIP': '❌', 'BLOCKED': '🚫'}.get(r['action'], '?')
        print(f"   {e} {r['home']:17s} vs {r['away']:17s} → {r['action']:11s} ({r['score']:.0f}pts) {r['recommended_market']}")
    
    print(f"\n   📊 Stats: {sniper} SNIPER, {normal} NORMAL, {skip} SKIP")


if __name__ == "__main__":
    test()
