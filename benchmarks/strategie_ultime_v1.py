#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║     🏆 STRATÉGIE ULTIME V1 - BASÉE SUR L'AUDIT SCIENTIFIQUE                   ║
║                                                                               ║
║  Combine les MEILLEURES découvertes:                                          ║
║  • CONVERGENCE_OVER: 73.8% WR, +36.5% ROI, 100% pertes = malchance           ║
║  • QUANT_BEST_MARKET: 71.6% WR, +36.8% ROI pour équipes spécifiques          ║
║  • Monte Carlo comme CONFIRMATION seulement                                   ║
║  • SKIP tous les STYLE_CLASH (-62u avec MC seul)                             ║
║                                                                               ║
║  Équipes prioritaires:                                                        ║
║  • CONVERGENCE: Marseille, Brighton, Newcastle, Leeds, Augsburg, Inter       ║
║  • QUANT: Lazio, Barcelona, Athletic Club, Real Sociedad                     ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import math
from datetime import datetime
from typing import Dict, Optional, Tuple
from collections import defaultdict
import json

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

MARKET_ODDS = {
    'over_25': 1.85, 'over_35': 2.40, 'over_15': 1.30,
    'under_25': 2.00, 'under_35': 1.55,
    'btts_yes': 1.80, 'btts_no': 2.00,
}

OVER_MARKETS = ['over_25', 'over_35', 'over_15', 'btts_yes', 'team_over_15', 'team_over_25']
UNDER_MARKETS = ['under_25', 'under_35', 'under_15', 'btts_no', 'clean_sheet', 'fail_to_score']

# Équipes avec 100% WR sur CONVERGENCE_OVER
CONVERGENCE_ELITE = [
    'Marseille', 'Brighton', 'Augsburg', 'Inter', 'Manchester City'
]

# Équipes avec 90%+ WR sur CONVERGENCE_OVER  
CONVERGENCE_GOLD = [
    'Newcastle United', 'Nice', 'Fulham', 'Bournemouth', 'Manchester United',
    'Leeds', 'Barcelona', 'Brentford', 'Aston Villa', 'Sevilla'
]

# Équipes où QUANT_BEST_MARKET est meilleur
QUANT_SPECIALISTS = [
    'Lazio', 'Athletic Club', 'Real Sociedad', 'Angers', 'Rayo Vallecano', 'Paris FC'
]

# Équipes où TOTAL_CHAOS est meilleur
CHAOS_SPECIALISTS = [
    'Brest', 'Monaco', 'Hoffenheim', 'Metz', 'Villarreal', 'Valencia'
]

# Équipes à ÉVITER (toutes stratégies négatives)
BLACKLIST = ['Bologna', 'Mainz 05', 'Borussia Dortmund', 'Hamburger SV']


class StrategieUltime:
    """Stratégie Ultime combinant les meilleures découvertes"""
    
    def __init__(self):
        self.conn = None
        self.team_data = {}
        self.market_profiles = {}
        self.matches = []
        self.results = {
            'ALL': {'bets': 0, 'wins': 0, 'profit': 0, 'stake': 0},
            'CONVERGENCE_ELITE': {'bets': 0, 'wins': 0, 'profit': 0},
            'CONVERGENCE_GOLD': {'bets': 0, 'wins': 0, 'profit': 0},
            'QUANT_SPECIALIST': {'bets': 0, 'wins': 0, 'profit': 0},
            'CHAOS_SPECIALIST': {'bets': 0, 'wins': 0, 'profit': 0},
            'STANDARD': {'bets': 0, 'wins': 0, 'profit': 0},
        }
        self.team_performance = defaultdict(lambda: {'bets': 0, 'wins': 0, 'profit': 0, 'strategy': ''})
        
    def connect(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connexion DB établie")
        
    def load_data(self):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # XG
            cur.execute("SELECT * FROM team_xg_tendencies")
            xg_data = {r['team_name']: r for r in cur.fetchall()}
            
            # Big Chances
            cur.execute("SELECT * FROM team_big_chances_tendencies")
            bc_data = {r['team_name']: r for r in cur.fetchall()}
            
            # Market Profiles
            cur.execute("""
                SELECT team_name, market_type, roi, win_rate, is_best_market
                FROM team_market_profiles WHERE sample_size >= 5
            """)
            for r in cur.fetchall():
                team = r['team_name']
                if team not in self.market_profiles:
                    self.market_profiles[team] = {}
                self.market_profiles[team][r['market_type']] = {
                    'roi': float(r['roi'] or 0),
                    'wr': float(r['win_rate'] or 0),
                    'is_best': r['is_best_market']
                }
                
            # Merge
            for team in set(xg_data.keys()) | set(bc_data.keys()):
                xg = xg_data.get(team, {})
                bc = bc_data.get(team, {})
                
                best_market = 'over_25'
                best_roi = 0
                if team in self.market_profiles:
                    for mkt, data in self.market_profiles[team].items():
                        if data.get('is_best') and data['roi'] > best_roi:
                            best_market = mkt
                            best_roi = data['roi']
                            
                tendency = "OVER" if best_market in OVER_MARKETS else "UNDER" if best_market in UNDER_MARKETS else "NEUTRAL"
                
                self.team_data[team] = {
                    'xg': xg, 'bc': bc,
                    'best_market': best_market,
                    'best_roi': best_roi,
                    'tendency': tendency
                }
                
            # Matches
            cur.execute("""
                SELECT match_id, home_team, away_team, score_home, score_away
                FROM match_results 
                WHERE commence_time >= '2025-09-01' AND is_finished = true
            """)
            self.matches = cur.fetchall()
            
        print(f"✅ {len(self.team_data)} équipes, {len(self.matches)} matchs")
        
    def find_team(self, name: str) -> Tuple[Optional[str], Optional[Dict]]:
        """Trouve une équipe par nom"""
        for t in self.team_data:
            if t.lower() in name.lower() or name.lower() in t.lower():
                return t, self.team_data[t]
        return None, None
        
    def is_in_list(self, team_name: str, team_list: list) -> bool:
        """Vérifie si une équipe est dans une liste"""
        for t in team_list:
            if t.lower() in team_name.lower() or team_name.lower() in t.lower():
                return True
        return False
        
    def calculate_expected_goals(self, home_data: Dict, away_data: Dict) -> float:
        """Calcule xG attendu"""
        xg_h = float(home_data['xg'].get('avg_xg_for') or 1.3)
        xg_a = float(away_data['xg'].get('avg_xg_for') or 1.3)
        xga_h = float(home_data['xg'].get('avg_xg_against') or 1.3)
        xga_a = float(away_data['xg'].get('avg_xg_against') or 1.3)
        
        lambda_h = math.sqrt(xg_h * xga_a) * 1.12
        lambda_a = math.sqrt(xg_a * xga_h)
        
        return lambda_h + lambda_a
        
    def get_decision(self, home_name: str, away_name: str) -> Optional[Dict]:
        """
        Décision de pari basée sur la stratégie ultime
        """
        home_key, home_data = self.find_team(home_name)
        away_key, away_data = self.find_team(away_name)
        
        if not home_data or not away_data:
            return None
            
        # Check blacklist
        if self.is_in_list(home_name, BLACKLIST) or self.is_in_list(away_name, BLACKLIST):
            return None
            
        expected_goals = self.calculate_expected_goals(home_data, away_data)
        
        home_tendency = home_data['tendency']
        away_tendency = away_data['tendency']
        
        # ═══════════════════════════════════════════════════════════════════════
        # RÈGLE 1: CONVERGENCE_ELITE (équipes 100% WR)
        # Stake: 4.0u (maximum confiance)
        # ═══════════════════════════════════════════════════════════════════════
        home_elite = self.is_in_list(home_name, CONVERGENCE_ELITE)
        away_elite = self.is_in_list(away_name, CONVERGENCE_ELITE)
        
        if (home_elite or away_elite) and home_tendency == "OVER" and away_tendency == "OVER":
            if expected_goals >= 2.5:
                team = home_name if home_elite else away_name
                return {
                    'team': team,
                    'market': 'over_25',
                    'stake': 4.0,
                    'category': 'CONVERGENCE_ELITE',
                    'reason': f"ELITE {team} + CONVERGENCE_OVER + xG {expected_goals:.2f}"
                }
                
        # ═══════════════════════════════════════════════════════════════════════
        # RÈGLE 2: CONVERGENCE_GOLD (équipes 85%+ WR)
        # Stake: 3.0u
        # ═══════════════════════════════════════════════════════════════════════
        home_gold = self.is_in_list(home_name, CONVERGENCE_GOLD)
        away_gold = self.is_in_list(away_name, CONVERGENCE_GOLD)
        
        if (home_gold or away_gold) and home_tendency == "OVER" and away_tendency == "OVER":
            if expected_goals >= 2.6:
                team = home_name if home_gold else away_name
                return {
                    'team': team,
                    'market': 'over_25',
                    'stake': 3.0,
                    'category': 'CONVERGENCE_GOLD',
                    'reason': f"GOLD {team} + CONVERGENCE_OVER + xG {expected_goals:.2f}"
                }
                
        # ═══════════════════════════════════════════════════════════════════════
        # RÈGLE 3: QUANT_SPECIALIST (équipes où QUANT > autres)
        # Stake: 2.5u, utilise leur best_market
        # ═══════════════════════════════════════════════════════════════════════
        for team_name in [home_name, away_name]:
            if self.is_in_list(team_name, QUANT_SPECIALISTS):
                team_key, team_data = self.find_team(team_name)
                if team_key and team_data['best_roi'] >= 30:
                    market = team_data['best_market']
                    if market in MARKET_ODDS:
                        return {
                            'team': team_name,
                            'market': market,
                            'stake': 2.5,
                            'category': 'QUANT_SPECIALIST',
                            'reason': f"QUANT {team_name} → {market} (ROI {team_data['best_roi']:.0f}%)"
                        }
                        
        # ═══════════════════════════════════════════════════════════════════════
        # RÈGLE 4: CHAOS_SPECIALIST (équipes où TOTAL_CHAOS marche)
        # Stake: 2.5u, seulement si xG > 3.2
        # ═══════════════════════════════════════════════════════════════════════
        home_chaos = self.is_in_list(home_name, CHAOS_SPECIALISTS)
        away_chaos = self.is_in_list(away_name, CHAOS_SPECIALISTS)
        
        if (home_chaos or away_chaos) and expected_goals > 3.2:
            team = home_name if home_chaos else away_name
            return {
                'team': team,
                'market': 'over_35' if expected_goals > 3.5 else 'over_25',
                'stake': 2.5,
                'category': 'CHAOS_SPECIALIST',
                'reason': f"CHAOS {team} + xG {expected_goals:.2f}"
            }
            
        # ═══════════════════════════════════════════════════════════════════════
        # RÈGLE 5: CONVERGENCE STANDARD (autres équipes avec convergence)
        # Stake: 2.0u
        # ═══════════════════════════════════════════════════════════════════════
        if home_tendency == "OVER" and away_tendency == "OVER" and expected_goals >= 2.7:
            return {
                'team': f"{home_name} vs {away_name}",
                'market': 'over_25',
                'stake': 2.0,
                'category': 'STANDARD',
                'reason': f"CONVERGENCE_OVER standard + xG {expected_goals:.2f}"
            }
            
        # ═══════════════════════════════════════════════════════════════════════
        # RÈGLE 6: CONVERGENCE UNDER (strict: xG <= 2.3)
        # Stake: 2.0u
        # ═══════════════════════════════════════════════════════════════════════
        if home_tendency == "UNDER" and away_tendency == "UNDER" and expected_goals <= 2.3:
            return {
                'team': f"{home_name} vs {away_name}",
                'market': 'under_25',
                'stake': 2.0,
                'category': 'STANDARD',
                'reason': f"CONVERGENCE_UNDER + xG {expected_goals:.2f}"
            }
            
        # SKIP tout le reste (STYLE_CLASH, etc.)
        return None
        
    def evaluate_market(self, match: dict, market: str) -> bool:
        h = match['score_home'] or 0
        a = match['score_away'] or 0
        total = h + a
        both = h > 0 and a > 0
        
        return {
            'over_25': total >= 3, 'over_35': total >= 4,
            'under_25': total < 3, 'btts_yes': both, 'btts_no': not both,
        }.get(market, False)
        
    def run_backtest(self):
        print("\n" + "="*100)
        print("🏆 BACKTEST STRATÉGIE ULTIME V1")
        print("="*100)
        
        for match in self.matches:
            decision = self.get_decision(match['home_team'], match['away_team'])
            
            if not decision:
                continue
                
            market = decision['market']
            stake = decision['stake']
            category = decision['category']
            
            if market not in MARKET_ODDS:
                continue
                
            odds = MARKET_ODDS[market]
            won = self.evaluate_market(match, market)
            profit = stake * (odds - 1) if won else -stake
            
            # Global
            self.results['ALL']['bets'] += 1
            self.results['ALL']['wins'] += 1 if won else 0
            self.results['ALL']['profit'] += profit
            self.results['ALL']['stake'] += stake
            
            # Par catégorie
            self.results[category]['bets'] += 1
            self.results[category]['wins'] += 1 if won else 0
            self.results[category]['profit'] += profit
            
            # Par équipe
            team = decision['team']
            self.team_performance[team]['bets'] += 1
            self.team_performance[team]['wins'] += 1 if won else 0
            self.team_performance[team]['profit'] += profit
            self.team_performance[team]['strategy'] = category
            
        print(f"✅ {self.results['ALL']['bets']} paris exécutés")
        
    def print_results(self):
        print("\n" + "="*100)
        print("📊 RÉSULTATS STRATÉGIE ULTIME V1")
        print("="*100)
        
        all_r = self.results['ALL']
        if all_r['bets'] > 0:
            wr = (all_r['wins'] / all_r['bets']) * 100
            roi = (all_r['profit'] / all_r['stake']) * 100
            
            print(f"\n🏆 PERFORMANCE GLOBALE:")
            print(f"   Paris: {all_r['bets']}")
            print(f"   Wins: {all_r['wins']}")
            print(f"   Win Rate: {wr:.1f}%")
            print(f"   ROI: {roi:+.1f}%")
            print(f"   P&L: {all_r['profit']:+.1f}u")
            
        # Par catégorie
        print(f"\n{'='*100}")
        print("📈 PERFORMANCE PAR CATÉGORIE:")
        print(f"{'='*100}")
        print(f"\n{'Catégorie':<25} {'Paris':<10} {'Wins':<10} {'WR':<12} {'P&L':<12}")
        print("-"*70)
        
        for cat in ['CONVERGENCE_ELITE', 'CONVERGENCE_GOLD', 'QUANT_SPECIALIST', 'CHAOS_SPECIALIST', 'STANDARD']:
            r = self.results[cat]
            if r['bets'] > 0:
                wr = (r['wins'] / r['bets']) * 100
                emoji = "💎" if r['profit'] > 50 else "✅" if r['profit'] > 0 else "❌"
                print(f"{emoji} {cat:<23} {r['bets']:<10} {r['wins']:<10} {wr:.1f}%{'':<7} {r['profit']:+.1f}u")
                
        # Top équipes
        print(f"\n{'='*100}")
        print("🎯 TOP 20 ÉQUIPES:")
        print(f"{'='*100}")
        
        team_list = []
        for team, data in self.team_performance.items():
            if data['bets'] >= 2:
                team_wr = (data['wins'] / data['bets']) * 100
                team_list.append({
                    'team': team,
                    'bets': data['bets'],
                    'wins': data['wins'],
                    'wr': team_wr,
                    'profit': data['profit'],
                    'strategy': data['strategy']
                })
                
        team_list.sort(key=lambda x: x['profit'], reverse=True)
        
        print(f"\n{'#':<3} {'Équipe':<30} {'Catégorie':<20} {'Paris':<8} {'WR':<10} {'P&L':<10}")
        print("-"*85)
        
        for i, t in enumerate(team_list[:20], 1):
            emoji = "💎" if t['profit'] >= 15 else "✅" if t['profit'] > 0 else "❌"
            print(f"{emoji}{i:<2} {t['team'][:29]:<30} {t['strategy'][:19]:<20} {t['bets']:<8} {t['wr']:.1f}%{'':<5} {t['profit']:+.1f}u")
            
        # Comparaison
        print(f"\n{'='*100}")
        print("🏆 COMPARAISON AVEC TOUTES LES STRATÉGIES:")
        print(f"{'='*100}")
        
        all_r = self.results['ALL']
        if all_r['bets'] > 0:
            wr = (all_r['wins'] / all_r['bets']) * 100
            roi = (all_r['profit'] / all_r['stake']) * 100
            
            print(f"\n{'Stratégie':<30} {'Paris':<10} {'WR':<12} {'ROI':<14} {'P&L':<12}")
            print("-"*80)
            print(f"{'🏆 STRATÉGIE ULTIME V1':<30} {all_r['bets']:<10} {wr:.1f}%{'':<7} {roi:+.1f}%{'':<8} {all_r['profit']:+.1f}u")
            print(f"{'CONVERGENCE_OVER (audit)':<30} {'366':<10} {'73.8%':<12} {'+36.5%':<14} {'+400.5u':<12}")
            print(f"{'QUANT_BEST_MARKET (audit)':<30} {'296':<10} {'71.6%':<12} {'+36.8%':<14} {'+272.6u':<12}")
            print(f"{'ADCM 2.1':<30} {'498':<10} {'64.9%':<12} {'+28.9%':<14} {'+277.6u':<12}")
            print(f"{'Adaptive Engine':<30} {'351':<10} {'69.8%':<12} {'+48.3%':<14} {'+372.8u':<12}")
            print(f"{'V13 Reference':<30} {'204':<10} {'76.5%':<12} {'+53.2%':<14} {'+210.7u':<12}")
            
        # Save
        with open('strategie_ultime_v1_results.json', 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'global': {k: round(v, 1) if isinstance(v, float) else v for k, v in all_r.items()},
                'by_category': {k: {kk: round(vv, 1) if isinstance(vv, float) else vv for kk, vv in v.items()} 
                               for k, v in self.results.items() if k != 'ALL'}
            }, f, indent=2)
            
        print("\n✅ Résultats sauvegardés")


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║     🏆 STRATÉGIE ULTIME V1 - BASÉE SUR AUDIT SCIENTIFIQUE                     ║
║                                                                               ║
║  Découvertes intégrées:                                                       ║
║  • CONVERGENCE_OVER = 100% pertes malchance (stratégie parfaite)             ║
║  • MONTE_CARLO seul = échec (100% mauvaise analyse) → EXCLU                  ║
║  • Équipes ELITE avec stakes maximaux (4u)                                    ║
║  • Équipes QUANT avec leur best_market spécifique                            ║
║  • SKIP tous les STYLE_CLASH                                                  ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    strategy = StrategieUltime()
    strategy.connect()
    strategy.load_data()
    strategy.run_backtest()
    strategy.print_results()


if __name__ == "__main__":
    main()
