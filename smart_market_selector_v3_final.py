"""
SMART MARKET SELECTOR V3 FINAL - HEDGE FUND GRADE
==================================================
Features:
1. Dixon-Coles avec Rho dynamique par ligue
2. Dynamic Lambda (Attaque × Défense) avec Dampening
3. Sharpe Ratio pour classifier les paris
4. Monte Carlo validation
5. Kelly adaptatif
6. Filtre anti-anomalie (cotes > 10)

Sans filtre bookmakers - Meilleure cote disponible.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from dataclasses import dataclass
from typing import Optional, List, Dict
import math
import numpy as np

DB_CONFIG = {
    'host': 'localhost', 'port': 5432, 'dbname': 'monps_db',
    'user': 'monps_user', 'password': 'monps_secure_password_2024'
}

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTES CALIBRÉES
# ══════════════════════════════════════════════════════════════════════════════

LEAGUE_RHO = {
    'Bundesliga': -0.08, 'Premier League': -0.10, 'La Liga': -0.12,
    'Ligue 1': -0.13, 'Serie A': -0.14, 'Eredivisie': -0.07, 'default': -0.13
}

LEAGUE_AVG_GOALS = {
    'Bundesliga': 1.55, 'Premier League': 1.45, 'La Liga': 1.35,
    'Ligue 1': 1.40, 'Serie A': 1.38, 'Eredivisie': 1.60, 'default': 1.45
}

MAX_LAMBDA = 2.8
MIN_LAMBDA = 0.5
SNIPER_SHARPE = 1.5
NORMAL_SHARPE = 0.8
SPEC_SHARPE = 0.4
MIN_EDGE = 0.02
MAX_ABSOLUTE_ODDS = 10.0  # Filtrer marchés illiquides (Matchbook exchange)
PINNACLE_GAP_THRESHOLD = 0.15  # Flag si écart > 15% avec Pinnacle


# ══════════════════════════════════════════════════════════════════════════════
# DIXON-COLES
# ══════════════════════════════════════════════════════════════════════════════

class DixonColes:
    
    @staticmethod
    def tau(h, a, h_lam, a_lam, rho):
        if h == 0 and a == 0: return 1 - h_lam * a_lam * rho
        elif h == 0 and a == 1: return 1 + h_lam * rho
        elif h == 1 and a == 0: return 1 + a_lam * rho
        elif h == 1 and a == 1: return 1 - rho
        return 1.0
    
    @staticmethod
    def poisson(lam, k):
        if lam <= 0: return 1.0 if k == 0 else 0.0
        return (lam ** k) * math.exp(-lam) / math.factorial(k)
    
    @classmethod
    def matrix(cls, h_lam, a_lam, rho=-0.13):
        m = np.zeros((8, 8))
        for h in range(8):
            for a in range(8):
                m[h, a] = cls.poisson(h_lam, h) * cls.poisson(a_lam, a) * \
                          cls.tau(h, a, h_lam, a_lam, rho)
        return m / m.sum()
    
    @classmethod
    def probs(cls, h_lam, a_lam, rho=-0.13):
        m = cls.matrix(h_lam, a_lam, rho)
        p = {}
        
        p['home'] = sum(m[h, a] for h in range(8) for a in range(h))
        p['draw'] = sum(m[i, i] for i in range(8))
        p['away'] = sum(m[h, a] for h in range(8) for a in range(h+1, 8))
        
        for line in [1.5, 2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5, 4.5]:
            under = sum(m[h, a] for h in range(8) for a in range(8) if h+a < line)
            p[f'over_{line}'] = 1 - under
            p[f'under_{line}'] = under
        
        p['btts_yes'] = sum(m[h, a] for h in range(1, 8) for a in range(1, 8))
        p['btts_no'] = 1 - p['btts_yes']
        
        for ah in [-2.5, -2.0, -1.5, -1.0, -0.5, 0, 0.5, 1.0, 1.5, 2.0, 2.5]:
            covers = sum(m[h, a] for h in range(8) for a in range(8) if (h-a)+ah > 0)
            p[f'ah_home_{ah:+.1f}'] = covers
            p[f'ah_away_{-ah:+.1f}'] = 1 - covers
        
        return p


# ══════════════════════════════════════════════════════════════════════════════
# MONTE CARLO
# ══════════════════════════════════════════════════════════════════════════════

class MonteCarlo:
    
    @classmethod
    def analyze(cls, h_lam, a_lam, market, line, odds, n_sims=3000):
        edges = []
        implied = 1 / odds
        
        for _ in range(n_sims):
            sim_h = max(0.3, np.random.normal(h_lam, h_lam * 0.12))
            sim_a = max(0.3, np.random.normal(a_lam, a_lam * 0.12))
            
            h_score = np.random.poisson(sim_h)
            a_score = np.random.poisson(sim_a)
            total = h_score + a_score
            
            win = 0
            if market == 'over': win = 1 if total > line else 0
            elif market == 'under': win = 1 if total < line else 0
            elif market == 'ah_home': win = 1 if (h_score - a_score) + line > 0 else 0
            elif market == 'ah_away': win = 1 if (a_score - h_score) + line > 0 else 0
            elif market == 'btts_yes': win = 1 if h_score > 0 and a_score > 0 else 0
            elif market == 'btts_no': win = 1 if h_score == 0 or a_score == 0 else 0
            
            edges.append(win - implied)
        
        edges = np.array(edges)
        mean_edge = edges.mean()
        std_edge = edges.std()
        sharpe = mean_edge / std_edge if std_edge > 0 else 0
        
        if sharpe >= SNIPER_SHARPE and mean_edge > 0.05:
            rec = 'SNIPER'
        elif sharpe >= NORMAL_SHARPE and mean_edge > 0.03:
            rec = 'NORMAL'
        elif sharpe >= SPEC_SHARPE and mean_edge > 0.02:
            rec = 'SPECULATIVE'
        elif mean_edge > 0.05:
            rec = 'HIGH_RISK'
        else:
            rec = 'SKIP'
        
        return {
            'mean_edge': mean_edge,
            'sharpe': sharpe,
            'p5': np.percentile(edges, 5),
            'p95': np.percentile(edges, 95),
            'prob_profit': (edges > 0).mean(),
            'recommendation': rec
        }


# ══════════════════════════════════════════════════════════════════════════════
# DATA CLASS
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Recommendation:
    market: str
    line: Optional[float]
    team: Optional[str]
    odds: float
    bookmaker: str
    other_books: List[str]
    model_prob: float
    edge: float
    sharpe: float
    prob_profit: float
    recommendation: str
    kelly: float
    pinnacle_odds: Optional[float]
    pinnacle_gap: Optional[float] = None  # Écart avec prob Pinnacle
    market_divergence: bool = False  # True si écart > 15%


# ══════════════════════════════════════════════════════════════════════════════
# SMART SELECTOR
# ══════════════════════════════════════════════════════════════════════════════

class SmartMarketSelector:
    
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cur = self.conn.cursor(cursor_factory=RealDictCursor)
        self._load_profiles()
        self.mc = MonteCarlo()
    
    def _load_profiles(self):
        self.profiles = {}
        self.cur.execute("SELECT team_name, league, avg_xg_for, avg_xg_against FROM team_xg_tendencies")
        for r in self.cur.fetchall():
            self.profiles[r['team_name'].lower()] = {
                'xg_for': float(r['avg_xg_for'] or 1.3),
                'xg_against': float(r['avg_xg_against'] or 1.2),
                'league': r['league']
            }
        print(f"   📊 {len(self.profiles)} profils chargés")
    
    def get_profile(self, team):
        team_l = team.lower()
        if team_l in self.profiles: return self.profiles[team_l]
        for k, v in self.profiles.items():
            if team_l in k or k in team_l: return v
        first = team_l.split()[0]
        for k, v in self.profiles.items():
            if first in k: return v
        return None
    
    def calc_lambda(self, home, away, league=None):
        h_prof = self.get_profile(home)
        a_prof = self.get_profile(away)
        
        if not league and h_prof:
            league = h_prof.get('league', 'default')
        league = league or 'default'
        league_avg = LEAGUE_AVG_GOALS.get(league, 1.45)
        
        h_xg_for = h_prof['xg_for'] if h_prof else 1.4
        h_xg_ag = h_prof['xg_against'] if h_prof else 1.2
        a_xg_for = a_prof['xg_for'] if a_prof else 1.2
        a_xg_ag = a_prof['xg_against'] if a_prof else 1.3
        
        def dampen(r):
            if r > 1.3: return 1.3 + (r - 1.3) ** 0.5
            if r < 0.7: return 0.7 - (0.7 - r) ** 0.5
            return r
        
        h_att = dampen(h_xg_for / league_avg)
        a_def = dampen(a_xg_ag / league_avg)
        a_att = dampen(a_xg_for / league_avg)
        h_def = dampen(h_xg_ag / league_avg)
        
        h_lam = h_att * a_def * league_avg * 1.08
        a_lam = a_att * h_def * league_avg * 0.92
        
        return max(MIN_LAMBDA, min(MAX_LAMBDA, h_lam)), max(MIN_LAMBDA, min(MAX_LAMBDA, a_lam)), league
    
    def get_odds(self, home, away):
        result = {'spreads': [], 'totals': []}
        
        self.cur.execute("""
            SELECT bookmaker, team, spread_point, spread_odds
            FROM odds_spreads WHERE home_team ILIKE %s AND away_team ILIKE %s
        """, (f'%{home}%', f'%{away}%'))
        result['spreads'] = self.cur.fetchall()
        
        self.cur.execute("""
            SELECT bookmaker, line, over_odds, under_odds
            FROM odds_totals WHERE home_team ILIKE %s AND away_team ILIKE %s
        """, (f'%{home}%', f'%{away}%'))
        result['totals'] = self.cur.fetchall()
        
        return result
    
    def analyze(self, home, away, league=None, debug=False):
        """Analyse complète d'un match"""
        
        h_lam, a_lam, detected_league = self.calc_lambda(home, away, league)
        rho = LEAGUE_RHO.get(detected_league, -0.13)
        probs = DixonColes.probs(h_lam, a_lam, rho)
        all_odds = self.get_odds(home, away)
        
        # Collecter par marché unique (meilleure cote)
        markets = {}
        debug_info = []
        
        # Over/Under
        for row in all_odds['totals']:
            line = float(row['line'])
            bk = row['bookmaker']
            is_pinnacle = 'pinnacle' in bk.lower()
            
            for side, odds_key in [('over', 'over_odds'), ('under', 'under_odds')]:
                odds = float(row[odds_key])
                market_key = f'{side}_{line}'
                prob = probs.get(market_key, 0)
                
                # FILTRE ANTI-ANOMALIE: rejeter cotes > 10 (marchés illiquides)
                if prob > 0 and odds > 1.1 and odds < MAX_ABSOLUTE_ODDS:
                    if market_key not in markets:
                        markets[market_key] = {
                            'type': side, 'line': line, 'team': None, 'prob': prob,
                            'best_odds': odds, 'best_bk': bk, 'all_bks': [f"{bk}@{odds:.2f}"],
                            'pinnacle': None
                        }
                    else:
                        markets[market_key]['all_bks'].append(f"{bk}@{odds:.2f}")
                        if odds > markets[market_key]['best_odds']:
                            markets[market_key]['best_odds'] = odds
                            markets[market_key]['best_bk'] = bk
                    
                    if is_pinnacle:
                        markets[market_key]['pinnacle'] = odds
                elif odds >= MAX_ABSOLUTE_ODDS:
                    debug_info.append(f"🚫 {market_key}: Cote {odds:.2f} > 10 (illiquide)")
        
        # Asian Handicap
        for row in all_odds['spreads']:
            team = row['team']
            spread = float(row['spread_point'])
            odds = float(row['spread_odds'])
            bk = row['bookmaker']
            is_pinnacle = 'pinnacle' in bk.lower()
            
            is_home = home.lower() in team.lower()
            
            if is_home:
                market_key = f'ah_home_{spread:+.1f}'
                prob_key = f'ah_home_{spread:+.1f}'
                mc_type = 'ah_home'
            else:
                market_key = f'ah_away_{spread:+.1f}'
                prob_key = f'ah_away_{spread:+.1f}'
                mc_type = 'ah_away'
            
            prob = probs.get(prob_key, 0)
            
            # FILTRE ANTI-ANOMALIE
            if prob > 0 and odds > 1.1 and odds < MAX_ABSOLUTE_ODDS:
                if market_key not in markets:
                    markets[market_key] = {
                        'type': mc_type, 'line': spread, 'team': team, 'prob': prob,
                        'best_odds': odds, 'best_bk': bk, 'all_bks': [f"{bk}@{odds:.2f}"],
                        'pinnacle': None
                    }
                else:
                    markets[market_key]['all_bks'].append(f"{bk}@{odds:.2f}")
                    if odds > markets[market_key]['best_odds']:
                        markets[market_key]['best_odds'] = odds
                        markets[market_key]['best_bk'] = bk
                
                if is_pinnacle:
                    markets[market_key]['pinnacle'] = odds
        
        # Évaluer chaque marché
        recommendations = []
        
        for market_key, data in markets.items():
            prob = data['prob']
            odds = data['best_odds']
            implied = 1 / odds
            edge = prob - implied
            
            if edge < MIN_EDGE:
                debug_info.append(f"⚪ {market_key}: Edge {edge*100:.1f}% < 2%")
                continue
            
            mc = self.mc.analyze(h_lam, a_lam, data['type'], data['line'], odds)
            
            if mc['recommendation'] == 'SKIP':
                debug_info.append(f"⚪ {market_key}: Sharpe {mc['sharpe']:.2f} trop bas")
                continue
            
            kelly = max(0, min(0.05, edge * 0.25))
            
            # Calculer l'écart avec Pinnacle si disponible
            pinnacle_gap = None
            market_divergence = False
            if data['pinnacle']:
                pinnacle_implied = 1 / data['pinnacle']
                pinnacle_gap = prob - pinnacle_implied
                if abs(pinnacle_gap) > PINNACLE_GAP_THRESHOLD:
                    market_divergence = True
                    # Dégrader la recommandation si divergence
                    if mc['recommendation'] == 'SNIPER':
                        mc['recommendation'] = 'NORMAL'
                    elif mc['recommendation'] == 'NORMAL':
                        mc['recommendation'] = 'SPECULATIVE'
                    elif mc['recommendation'] == 'SPECULATIVE':
                        mc['recommendation'] = 'HIGH_RISK'
            
            recommendations.append(Recommendation(
                market=market_key,
                line=data['line'],
                team=data['team'],
                odds=odds,
                bookmaker=data['best_bk'],
                other_books=data['all_bks'][:5],
                model_prob=prob,
                edge=edge,
                sharpe=mc['sharpe'],
                prob_profit=mc['prob_profit'],
                recommendation=mc['recommendation'],
                kelly=kelly,
                pinnacle_odds=data['pinnacle'],
                pinnacle_gap=pinnacle_gap,
                market_divergence=market_divergence
            ))
        
        recommendations.sort(key=lambda x: (-x.sharpe, -x.edge))
        
        return {
            'home': home,
            'away': away,
            'home_lambda': h_lam,
            'away_lambda': a_lam,
            'total_xg': h_lam + a_lam,
            'league': detected_league,
            'rho': rho,
            'probabilities': probs,
            'recommendations': recommendations,
            'debug': debug_info
        }
    
    def close(self):
        self.conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# TEST
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 100)
    print("    🏆 SMART MARKET SELECTOR V3 FINAL - HEDGE FUND GRADE")
    print("    📊 Dixon-Coles + Dynamic Lambda + Sharpe + Monte Carlo")
    print("=" * 100)
    
    selector = SmartMarketSelector()
    
    matches = [
        ("Barcelona", "Atlético Madrid", "La Liga"),
        ("Bayern Munich", "Mainz", "Bundesliga"),
        ("Marseille", "Monaco", "Ligue 1"),
        ("Athletic Bilbao", "Real Madrid", "La Liga"),
    ]
    
    for home, away, league in matches:
        print("\n" + "─" * 100)
        print(f"   ⚽ {home} vs {away} ({league})")
        print("─" * 100)
        
        result = selector.analyze(home, away, league, debug=True)
        
        print(f"\n   📊 MODÈLE:")
        print(f"      λ Home: {result['home_lambda']:.2f} | λ Away: {result['away_lambda']:.2f} | Total: {result['total_xg']:.2f}")
        print(f"      Rho ({league}): {result['rho']}")
        
        p = result['probabilities']
        print(f"\n   🎲 PROBABILITÉS:")
        print(f"      1X2: {p['home']*100:.0f}% | {p['draw']*100:.0f}% | {p['away']*100:.0f}%")
        print(f"      Over 2.5: {p['over_2.5']*100:.0f}% | Over 3.5: {p['over_3.5']*100:.0f}% | BTTS: {p['btts_yes']*100:.0f}%")
        
        recs = result['recommendations']
        
        if recs:
            # Compter par type
            sniper = sum(1 for r in recs if r.recommendation == 'SNIPER')
            normal = sum(1 for r in recs if r.recommendation == 'NORMAL')
            spec = sum(1 for r in recs if r.recommendation == 'SPECULATIVE')
            high = sum(1 for r in recs if r.recommendation == 'HIGH_RISK')
            
            print(f"\n   🎯 OPPORTUNITÉS: {len(recs)} total")
            print(f"      🎯 SNIPER: {sniper} | ✅ NORMAL: {normal} | ⚡ SPEC: {spec} | ⚠️ HIGH_RISK: {high}")
            
            print(f"\n   📈 TOP RECOMMANDATIONS:")
            for i, rec in enumerate(recs[:5], 1):
                emoji = "🎯" if rec.recommendation == 'SNIPER' else "✅" if rec.recommendation == 'NORMAL' else "⚡" if rec.recommendation == 'SPECULATIVE' else "⚠️"
                pin = f" (Pinnacle: {rec.pinnacle_odds:.2f})" if rec.pinnacle_odds else ""
                
                print(f"\n   {i}. {emoji} {rec.market} @ {rec.odds:.2f} ({rec.bookmaker}){pin}")
                print(f"      Prob: {rec.model_prob*100:.0f}% | Edge: {rec.edge*100:.1f}% | Sharpe: {rec.sharpe:.2f}")
                print(f"      P(profit): {rec.prob_profit*100:.0f}% | Kelly: {rec.kelly*100:.1f}% | {rec.recommendation}")
                if rec.market_divergence:
                    print(f"      ⚠️ MARKET DIVERGENCE: Écart Pinnacle {rec.pinnacle_gap*100:+.1f}%")
        else:
            print("\n   ⚠️ Aucune opportunité trouvée")
            if result['debug']:
                print(f"\n   🔍 Debug (premiers rejets):")
                for d in result['debug'][:3]:
                    print(f"      {d}")
    
    selector.close()
    
    print("\n" + "=" * 100)
    print("    ✅ V3 FINAL - Prêt pour production")
    print("=" * 100)
