#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
BACKTEST SCIENTIFIQUE - ORCHESTRATOR V11 QUANT SNIPER
Version 2: Avec normalisation des noms d'équipes
═══════════════════════════════════════════════════════════════════════════════
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from collections import defaultdict
import re

DB_CONFIG = {
    'host': 'localhost', 'port': 5432, 'dbname': 'monps_db',
    'user': 'monps_user', 'password': 'monps_secure_password_2024'
}

# ═══════════════════════════════════════════════════════════════════════════════
# NORMALISATION DES NOMS D'ÉQUIPES
# ═══════════════════════════════════════════════════════════════════════════════

def normalize_team_name(name):
    """
    Normalise un nom d'équipe pour matching cross-tables
    'FC Barcelona' → 'barcelona'
    'Manchester City FC' → 'manchester city'
    '1. FC Heidenheim 1846' → 'heidenheim'
    """
    if not name:
        return ""
    
    # Lowercase
    n = name.lower().strip()
    
    # Supprimer les suffixes/préfixes courants
    patterns_to_remove = [
        r'\bfc\b', r'\bcf\b', r'\bafc\b', r'\bsc\b', r'\bssc\b',
        r'\bac\b', r'\bas\b', r'\brc\b', r'\brcd\b', r'\bud\b',
        r'\bcd\b', r'\bsd\b', r'\bsv\b', r'\bvfb\b', r'\bvfl\b',
        r'\brb\b', r'\btsg\b', r'\bfk\b', r'\bnk\b', r'\bsk\b',
        r'\bbsc\b', r'\bsco\b', r'\bogc\b', r'\bhsc\b',
        r'\bunited\b', r'\bcity\b', r'\bfc\b',
        r'\b1\.\s*', r'\b1909\b', r'\b1846\b', r'\b1899\b', r'\b1910\b',
        r'\b1901\b', r'\b1907\b', r'\b1913\b', r'\b05\b', r'\b04\b',
        r'\bcalcio\b', r'\bbalompié\b', r'\bfútbol\b', 
        r'\bde\b', r'\bdel\b',
    ]
    
    for pattern in patterns_to_remove:
        n = re.sub(pattern, '', n)
    
    # Nettoyer espaces multiples
    n = re.sub(r'\s+', ' ', n).strip()
    
    return n

def match_team(name, cache_dict):
    """
    Trouve une équipe dans le cache avec matching intelligent
    """
    if not name or not cache_dict:
        return None
    
    name_norm = normalize_team_name(name)
    
    # 1. Match exact normalisé
    for team, data in cache_dict.items():
        if normalize_team_name(team) == name_norm:
            return data
    
    # 2. Match partiel (le nom normalisé contient ou est contenu)
    for team, data in cache_dict.items():
        team_norm = normalize_team_name(team)
        if name_norm in team_norm or team_norm in name_norm:
            return data
    
    # 3. Match par mots-clés principaux
    name_words = set(name_norm.split())
    for team, data in cache_dict.items():
        team_words = set(normalize_team_name(team).split())
        # Au moins 1 mot en commun et pas trop de différence
        common = name_words & team_words
        if common and len(common) >= 1:
            return data
    
    return None


class OrchestratorV11Backtest:
    SNIPER_THRESHOLD = 50
    NORMAL_THRESHOLD = 35
    
    def __init__(self):
        self.conn = None
        self.cache = {}
        self._load_cache()
        self._test_matching()
    
    def _get_conn(self):
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
        return self.conn
    
    def _load_cache(self):
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT * FROM tactical_matrix")
        self.cache['tactical'] = {(r['style_a'], r['style_b']): r for r in cur.fetchall()}
        
        cur.execute("SELECT * FROM team_intelligence")
        self.cache['teams'] = {r['team_name']: r for r in cur.fetchall()}
        
        cur.execute("SELECT * FROM team_class")
        self.cache['team_class'] = {r['team_name']: r for r in cur.fetchall()}
        
        cur.execute("SELECT * FROM coach_intelligence")
        self.cache['coaches'] = {r['current_team']: r for r in cur.fetchall()}
        
        cur.execute("SELECT * FROM team_market_profiles WHERE is_best_market = true")
        self.cache['market_profiles'] = {}
        for r in cur.fetchall():
            team = r['team_name']
            if team not in self.cache['market_profiles']:
                self.cache['market_profiles'][team] = r
        
        print(f"Cache: {len(self.cache['tactical'])} tactical, {len(self.cache['teams'])} teams, {len(self.cache['team_class'])} classes, {len(self.cache['coaches'])} coaches, {len(self.cache['market_profiles'])} profiles")
    
    def _test_matching(self):
        """Test du matching sur quelques équipes"""
        test_teams = ["FC Barcelona", "Manchester City FC", "Real Madrid CF", "Liverpool FC"]
        print("\n🔍 Test matching:")
        for team in test_teams:
            tc = match_team(team, self.cache['team_class'])
            ti = match_team(team, self.cache['teams'])
            co = match_team(team, self.cache['coaches'])
            tc_ok = "✅" if tc else "❌"
            ti_ok = "✅" if ti else "❌"
            co_ok = "✅" if co else "❌"
            print(f"   {team}: class={tc_ok} intel={ti_ok} coach={co_ok}")
    
    def analyze_match(self, home: str, away: str, market: str = "over_25"):
        score = 10.0
        layers = {}
        btts_prob = 50.0
        over25_prob = 50.0
        recommended_market = market
        
        tactical = self._analyze_tactical(home, away)
        score += tactical['score']
        layers['tactical'] = tactical
        btts_prob = tactical.get('btts', 50)
        over25_prob = tactical.get('over25', 50)
        
        team_class = self._analyze_team_class(home, away)
        score += team_class['score']
        layers['team_class'] = team_class
        
        h2h = self._analyze_h2h(home, away)
        score += h2h['score']
        layers['h2h'] = h2h
        
        injuries = self._analyze_injuries(home, away)
        score += injuries['score']
        layers['injuries'] = injuries
        
        xg = self._analyze_xg(home, away)
        score += xg['score']
        layers['xg'] = xg
        
        coach = self._analyze_coach(home, away)
        score += coach['score']
        layers['coach'] = coach
        
        convergence = self._analyze_convergence(home, away)
        score += convergence['score']
        layers['convergence'] = convergence
        recommended_market = convergence.get('market', market)
        
        if score >= self.SNIPER_THRESHOLD:
            action = "SNIPER_BET"
        elif score >= self.NORMAL_THRESHOLD:
            action = "NORMAL_BET"
        else:
            action = "SKIP"
        
        return {
            'score': round(score, 1),
            'action': action,
            'recommended_market': recommended_market,
            'btts_prob': btts_prob,
            'over25_prob': over25_prob,
            'layers': layers
        }
    
    def _analyze_tactical(self, home, away):
        h_data = match_team(home, self.cache['teams'])
        a_data = match_team(away, self.cache['teams'])
        
        if h_data and a_data:
            h_style = h_data.get('current_style') or 'balanced'
            a_style = a_data.get('current_style') or 'balanced'
            
            key = (h_style, a_style)
            if key in self.cache['tactical']:
                tm = self.cache['tactical'][key]
                btts = float(tm.get('btts_probability') or 50)
                over25 = float(tm.get('over_25_probability') or 50)
                score = (btts + over25) / 10
                return {'score': min(15, score), 'btts': btts, 'over25': over25, 'reason': f"{h_style} vs {a_style}"}
            
            # Fallback: stats directes
            h_over25 = float(h_data.get('home_over25_rate') or 50)
            a_over25 = float(a_data.get('away_over25_rate') or 50)
            over25 = (h_over25 + a_over25) / 2
            h_btts = float(h_data.get('home_btts_rate') or 50)
            a_btts = float(a_data.get('away_btts_rate') or 50)
            btts = (h_btts + a_btts) / 2
            score = (btts + over25) / 10
            return {'score': min(15, score), 'btts': btts, 'over25': over25, 'reason': 'Stats directes'}
        
        return {'score': 5.0, 'btts': 50, 'over25': 50, 'reason': 'No data'}
    
    def _analyze_team_class(self, home, away):
        h_data = match_team(home, self.cache['team_class'])
        a_data = match_team(away, self.cache['team_class'])
        
        h_power = float(h_data.get('power_index') or 50) if h_data else 50
        a_power = float(a_data.get('power_index') or 50) if a_data else 50
        
        diff = abs(h_power - a_power)
        score = min(10, diff / 2)
        
        found = "2/2" if (h_data and a_data) else ("1/2" if (h_data or a_data) else "0/2")
        return {'score': score, 'h_power': h_power, 'a_power': a_power, 'reason': f"H:{h_power:.0f} A:{a_power:.0f} ({found})"}
    
    def _analyze_h2h(self, home, away):
        try:
            conn = self._get_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Normaliser pour la recherche
            h_norm = normalize_team_name(home)
            a_norm = normalize_team_name(away)
            
            cur.execute("""
                SELECT avg_total_goals, over_25_percentage, btts_percentage, total_matches,
                       team_a, team_b
                FROM head_to_head
            """)
            
            rows = cur.fetchall()
            for row in rows:
                ta_norm = normalize_team_name(row['team_a'])
                tb_norm = normalize_team_name(row['team_b'])
                
                if (h_norm in ta_norm or ta_norm in h_norm) and (a_norm in tb_norm or tb_norm in a_norm):
                    if int(row['total_matches'] or 0) >= 2:
                        over25 = float(row['over_25_percentage'] or 50)
                        score = min(8, (over25 / 100) * 8)
                        return {'score': score, 'reason': f"H2H {row['total_matches']}m O2.5:{over25:.0f}%"}
                
                if (a_norm in ta_norm or ta_norm in a_norm) and (h_norm in tb_norm or tb_norm in h_norm):
                    if int(row['total_matches'] or 0) >= 2:
                        over25 = float(row['over_25_percentage'] or 50)
                        score = min(8, (over25 / 100) * 8)
                        return {'score': score, 'reason': f"H2H {row['total_matches']}m O2.5:{over25:.0f}%"}
            
            return {'score': 1.0, 'reason': 'H2H not found'}
        except Exception as e:
            self.conn.rollback()
            return {'score': 1.0, 'reason': f'H2H err'}
    
    def _analyze_injuries(self, home, away):
        try:
            conn = self._get_conn()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT current_team, goals_per_90 FROM scorer_intelligence
                WHERE is_injured = true AND goals_per_90 > 0.5
            """)
            
            h_norm = normalize_team_name(home)
            a_norm = normalize_team_name(away)
            
            injured = 0
            for row in cur.fetchall():
                team_norm = normalize_team_name(row['current_team'])
                if h_norm in team_norm or team_norm in h_norm or a_norm in team_norm or team_norm in a_norm:
                    injured += 1
            
            return {'score': -min(8, injured * 2), 'injured': injured, 'reason': f"{injured} key blessés"}
        except Exception as e:
            self.conn.rollback()
            return {'score': 0, 'injured': 0, 'reason': 'Inj err'}
    
    def _analyze_xg(self, home, away):
        h_data = match_team(home, self.cache['teams'])
        a_data = match_team(away, self.cache['teams'])
        
        if h_data and a_data:
            h_diff = float(h_data.get('overperformance_goals') or 0)
            a_diff = float(a_data.get('overperformance_goals') or 0)
            avg = (h_diff + a_diff) / 2
            
            if avg > 0.3:
                return {'score': -2.0, 'diff': avg, 'reason': f'Overperf {avg:+.2f}'}
            elif avg < -0.3:
                return {'score': 2.0, 'diff': avg, 'reason': f'Underperf {avg:+.2f}'}
            return {'score': 0.0, 'diff': avg, 'reason': f'Neutral {avg:+.2f}'}
        
        return {'score': 0.0, 'reason': 'No xG data'}
    
    def _analyze_coach(self, home, away):
        h_coach = match_team(home, self.cache['coaches'])
        a_coach = match_team(away, self.cache['coaches'])
        
        h_over25 = float(h_coach.get('over25_rate') or 50) if h_coach else 50
        a_over25 = float(a_coach.get('over25_rate') or 50) if a_coach else 50
        
        score = 0
        reason = f"{h_over25:.0f}%/{a_over25:.0f}%"
        if h_over25 > 55 and a_over25 > 55:
            score = 2.0
            reason += " (both offensive)"
        elif h_over25 < 40 or a_over25 < 40:
            score = -1.0
            reason += " (defensive)"
        
        found = "2/2" if (h_coach and a_coach) else ("1/2" if (h_coach or a_coach) else "0/2")
        return {'score': score, 'reason': f"{reason} ({found})"}
    
    def _analyze_convergence(self, home, away):
        h_prof = match_team(home, self.cache['market_profiles'])
        a_prof = match_team(away, self.cache['market_profiles'])
        
        if h_prof and a_prof:
            h_market = h_prof.get('market_type', 'over_25')
            a_market = a_prof.get('market_type', 'over_25')
            h_conf = float(h_prof.get('confidence_score') or 0)
            a_conf = float(a_prof.get('confidence_score') or 0)
            
            if h_market == a_market and h_conf > 60 and a_conf > 60:
                return {'score': 30.0, 'market': h_market, 'reason': f"Convergence {h_market} ({h_conf:.0f}/{a_conf:.0f})"}
            elif h_conf > 70 or a_conf > 70:
                best = h_market if h_conf > a_conf else a_market
                return {'score': 10.0, 'market': best, 'reason': f"Partielle {best}"}
        
        return {'score': 0.0, 'market': 'over_25', 'reason': 'No convergence'}


def get_matches_last_7_days():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT DISTINCT ON (home_team, away_team, commence_time)
            home_team, away_team,
            score_home, score_away,
            commence_time, league
        FROM match_results
        WHERE commence_time >= NOW() - INTERVAL '7 days'
          AND is_finished = true
          AND score_home IS NOT NULL
          AND score_away IS NOT NULL
        ORDER BY home_team, away_team, commence_time, id DESC
    """)
    
    matches = cur.fetchall()
    cur.close()
    conn.close()
    return matches


def evaluate_prediction(market, home_score, away_score):
    total = home_score + away_score
    results = {
        'over_25': total > 2.5,
        'over_35': total > 3.5,
        'under_25': total < 2.5,
        'btts_yes': home_score > 0 and away_score > 0,
        'btts_no': home_score == 0 or away_score == 0,
        'team_over_15': home_score > 1.5 or away_score > 1.5,
        'team_fail_to_score': home_score == 0 or away_score == 0,
        'team_clean_sheet': home_score == 0 or away_score == 0,
    }
    
    m = market.lower().replace(' ', '_')
    if m in results:
        return results[m]
    elif 'over' in m and '25' in m:
        return results['over_25']
    elif 'btts' in m:
        return results['btts_yes']
    elif 'fail' in m or 'clean' in m:
        return results['team_fail_to_score']
    return results['over_25']


def run_backtest():
    print("═" * 70)
    print("BACKTEST SCIENTIFIQUE V2 - AVEC NORMALISATION")
    print("═" * 70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    
    orch = OrchestratorV11Backtest()
    matches = get_matches_last_7_days()
    print(f"\n📊 {len(matches)} matchs uniques (7 derniers jours)\n")
    
    if not matches:
        print("❌ Aucun match")
        return
    
    stats = {
        'total': 0, 'analyzed': 0, 'errors': 0,
        'by_action': {
            'SNIPER_BET': {'total': 0, 'wins': 0, 'details': []},
            'NORMAL_BET': {'total': 0, 'wins': 0, 'details': []},
            'SKIP': {'total': 0, 'would_win': 0},
        },
        'by_score_range': defaultdict(lambda: {'total': 0, 'wins': 0}),
        'by_market': defaultdict(lambda: {'total': 0, 'wins': 0}),
        'by_league': defaultdict(lambda: {'total': 0, 'wins': 0}),
        'layer_impact': defaultdict(lambda: {'win': [], 'loss': []}),
    }
    
    for match in matches:
        stats['total'] += 1
        try:
            home = match['home_team']
            away = match['away_team']
            home_score = int(match['score_home'])
            away_score = int(match['score_away'])
            league = match.get('league') or 'Unknown'
            
            result = orch.analyze_match(home, away, "over_25")
            action = result['action']
            score = result['score']
            market = result['recommended_market']
            
            correct = evaluate_prediction(market, home_score, away_score)
            stats['analyzed'] += 1
            
            # Score range
            if score >= 50: sr = "50+"
            elif score >= 40: sr = "40-49"
            elif score >= 35: sr = "35-39"
            else: sr = "<35"
            
            stats['by_score_range'][sr]['total'] += 1
            if correct: stats['by_score_range'][sr]['wins'] += 1
            
            stats['by_action'][action]['total'] += 1
            if action == 'SKIP':
                if correct: stats['by_action'][action]['would_win'] += 1
            else:
                if correct: stats['by_action'][action]['wins'] += 1
                stats['by_action'][action]['details'].append({
                    'match': f"{home} vs {away}",
                    'real': f"{home_score}-{away_score}",
                    'goals': home_score + away_score,
                    'score': score, 'market': market, 'correct': correct,
                    'layers': {k: v.get('score', 0) for k, v in result['layers'].items()}
                })
            
            stats['by_market'][market]['total'] += 1
            if correct: stats['by_market'][market]['wins'] += 1
            
            stats['by_league'][league]['total'] += 1
            if correct: stats['by_league'][league]['wins'] += 1
            
            if action in ['SNIPER_BET', 'NORMAL_BET']:
                for layer, data in result['layers'].items():
                    key = 'win' if correct else 'loss'
                    stats['layer_impact'][layer][key].append(data.get('score', 0))
            
            status = "✅" if correct else "❌"
            print(f"{status} {home} vs {away} ({home_score}-{away_score}) | {action} ({score:.0f}) → {market}")
            
        except Exception as e:
            stats['errors'] += 1
            print(f"⚠️  Erreur: {e}")
    
    # RAPPORT
    print("\n" + "═" * 70)
    print("RAPPORT SCIENTIFIQUE V2")
    print("═" * 70)
    
    print(f"\n📊 {stats['analyzed']}/{stats['total']} analysés ({stats['errors']} erreurs)")
    
    print("\n┌─────────────────────────────────────────────────────────────────┐")
    print("│ 1️⃣  PERFORMANCE PAR ACTION                                       │")
    print("└─────────────────────────────────────────────────────────────────┘")
    for action, data in stats['by_action'].items():
        if data['total'] > 0:
            if action == 'SKIP':
                wr = data['would_win'] / data['total'] * 100
                print(f"   ⏭️  {action:12}: {data['total']:3} matchs | Aurait gagné: {data['would_win']} ({wr:.1f}%)")
            else:
                wr = data['wins'] / data['total'] * 100
                emoji = "🎯" if action == "SNIPER_BET" else "📈"
                print(f"   {emoji} {action:12}: {data['wins']:2}/{data['total']:2} ({wr:.1f}%)")
    
    print("\n┌─────────────────────────────────────────────────────────────────┐")
    print("│ 2️⃣  PERFORMANCE PAR SCORE V11                                    │")
    print("└─────────────────────────────────────────────────────────────────┘")
    for sr in ['50+', '40-49', '35-39', '<35']:
        d = stats['by_score_range'].get(sr, {'total': 0, 'wins': 0})
        if d['total'] > 0:
            wr = d['wins'] / d['total'] * 100
            bar = "█" * int(wr / 10) + "░" * (10 - int(wr / 10))
            print(f"   {sr:8}: {d['wins']:2}/{d['total']:2} ({wr:5.1f}%) {bar}")
    
    print("\n┌─────────────────────────────────────────────────────────────────┐")
    print("│ 3️⃣  PERFORMANCE PAR MARCHÉ                                       │")
    print("└─────────────────────────────────────────────────────────────────┘")
    for m, d in sorted(stats['by_market'].items(), key=lambda x: -x[1]['total']):
        if d['total'] > 0:
            wr = d['wins'] / d['total'] * 100
            print(f"   {m:20}: {d['wins']}/{d['total']} ({wr:.1f}%)")
    
    print("\n┌─────────────────────────────────────────────────────────────────┐")
    print("│ 4️⃣  PERFORMANCE PAR LIGUE (min 3 matchs)                         │")
    print("└─────────────────────────────────────────────────────────────────┘")
    for league, d in sorted(stats['by_league'].items(), key=lambda x: -x[1]['total']):
        if d['total'] >= 3:
            wr = d['wins'] / d['total'] * 100
            print(f"   {league:25}: {d['wins']}/{d['total']} ({wr:.1f}%)")
    
    print("\n┌─────────────────────────────────────────────────────────────────┐")
    print("│ 5️⃣  IMPACT DES LAYERS (bets actifs uniquement)                   │")
    print("└─────────────────────────────────────────────────────────────────┘")
    for layer, data in stats['layer_impact'].items():
        win_avg = sum(data['win']) / len(data['win']) if data['win'] else 0
        loss_avg = sum(data['loss']) / len(data['loss']) if data['loss'] else 0
        diff = win_avg - loss_avg
        ind = "📈" if diff > 1 else "📉" if diff < -1 else "➡️"
        n_win = len(data['win'])
        n_loss = len(data['loss'])
        print(f"   {layer:15}: Win={win_avg:+6.1f} ({n_win}) | Loss={loss_avg:+6.1f} ({n_loss}) | Δ={diff:+5.1f} {ind}")
    
    print("\n┌─────────────────────────────────────────────────────────────────┐")
    print("│ 6️⃣  DÉTAIL SNIPER_BET                                            │")
    print("└─────────────────────────────────────────────────────────────────┘")
    for d in stats['by_action']['SNIPER_BET']['details']:
        s = "✅" if d['correct'] else "❌"
        print(f"   {s} {d['match']} ({d['real']}) [{d['goals']}g] - {d['score']:.0f}pts → {d['market']}")
        print(f"      Layers: {d['layers']}")
    
    print("\n┌─────────────────────────────────────────────────────────────────┐")
    print("│ 7️⃣  DÉTAIL NORMAL_BET                                            │")
    print("└─────────────────────────────────────────────────────────────────┘")
    for d in stats['by_action']['NORMAL_BET']['details']:
        s = "✅" if d['correct'] else "❌"
        print(f"   {s} {d['match']} ({d['real']}) [{d['goals']}g] - {d['score']:.0f}pts → {d['market']}")
    
    # CONCLUSIONS
    print("\n" + "═" * 70)
    print("CONCLUSIONS & RECOMMANDATIONS")
    print("═" * 70)
    
    print("\n💪 FORCES:")
    for sr, d in stats['by_score_range'].items():
        if d['total'] >= 3 and d['wins'] / d['total'] >= 0.55:
            print(f"   ✅ Score {sr}: {d['wins']/d['total']*100:.0f}% WR ({d['total']} matchs)")
    
    for m, d in stats['by_market'].items():
        if d['total'] >= 3 and d['wins'] / d['total'] >= 0.55:
            print(f"   ✅ Marché {m}: {d['wins']/d['total']*100:.0f}% WR")
    
    print("\n⚠️  FAIBLESSES:")
    for sr, d in stats['by_score_range'].items():
        if d['total'] >= 3 and d['wins'] / d['total'] < 0.45:
            print(f"   ❌ Score {sr}: {d['wins']/d['total']*100:.0f}% WR")
    
    # ROI
    sniper = stats['by_action']['SNIPER_BET']
    normal = stats['by_action']['NORMAL_BET']
    print(f"\n💰 ROI THÉORIQUE (cote 1.85):")
    if sniper['total'] > 0:
        sniper_roi = (sniper['wins'] * 1.85 - sniper['total']) / sniper['total'] * 100
        print(f"   SNIPER: {sniper['wins']}/{sniper['total']} → ROI {sniper_roi:+.1f}%")
    if normal['total'] > 0:
        normal_roi = (normal['wins'] * 1.85 - normal['total']) / normal['total'] * 100
        print(f"   NORMAL: {normal['wins']}/{normal['total']} → ROI {normal_roi:+.1f}%")
    
    print("\n" + "═" * 70)

if __name__ == "__main__":
    run_backtest()
