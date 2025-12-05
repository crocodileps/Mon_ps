#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║       🚀 ADAPTIVE TEAM ENGINE - MOTEUR ADAPTATIF PAR ÉQUIPE                  ║
║                                                                               ║
║  Applique automatiquement la MEILLEURE stratégie selon:                      ║
║  • Profil de l'équipe (OFFENSIVE/DEFENSIVE/OPEN_PLAY/LOW_SCORING)           ║
║  • Meilleur marché historique (team_market_profiles)                         ║
║  • Équipes à éviter (blacklist)                                              ║
║                                                                               ║
║  Résultat attendu: Combiner le meilleur de chaque stratégie                  ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
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
    'over_15': 1.30, 'over_25': 1.85, 'over_35': 2.40,
    'under_15': 3.50, 'under_25': 2.00, 'under_35': 1.55,
    'btts_yes': 1.80, 'btts_no': 2.00,
}

# Configuration optimale découverte par le benchmark
OPTIMAL_CONFIG = {
    'OFFENSIVE': {
        'strategy': 'CONSERVATIVE',
        'primary_market': 'over_25',
        'secondary_market': 'over_35',
        'min_roi': 30,
        'min_wr': 65
    },
    'DEFENSIVE': {
        'strategy': 'BEST_MARKET_ONLY',
        'primary_market': 'under_25',
        'secondary_market': 'btts_no',
        'min_roi': 20,
        'min_wr': 60
    },
    'OPEN_PLAY': {
        'strategy': 'CONSERVATIVE',
        'primary_market': 'over_25',
        'secondary_market': 'btts_yes',
        'min_roi': 25,
        'min_wr': 65
    },
    'LOW_SCORING': {
        'strategy': 'QUANT_ONLY',
        'primary_market': 'btts_no',
        'secondary_market': 'under_25',
        'min_roi': 30,
        'min_wr': 65
    },
    'BALANCED': {
        'strategy': 'BEST_MARKET_ONLY',
        'primary_market': 'over_25',
        'secondary_market': None,
        'min_roi': 35,
        'min_wr': 70
    }
}

# Équipes blacklistées (ROI négatif constant)
BLACKLIST = ['Benfica', 'RB Leipzig', 'Atalanta BC', 'Elche CF']


class AdaptiveTeamEngine:
    """Moteur adaptatif par équipe"""
    
    def __init__(self):
        self.conn = None
        self.teams = {}
        self.ml_profiles = {}
        self.matches = []
        self.results = {'bets': 0, 'wins': 0, 'stake': 0, 'profit': 0, 'details': []}
        
    def connect(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connexion DB établie")
        
    def load_data(self):
        """Charge toutes les données nécessaires"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Team Intelligence
            cur.execute("""
                SELECT team_name, league,
                       home_goals_scored_avg, home_goals_conceded_avg,
                       away_goals_scored_avg, away_goals_conceded_avg
                FROM team_intelligence
                WHERE home_goals_scored_avg IS NOT NULL
            """)
            for row in cur.fetchall():
                team = row['team_name']
                home_scored = float(row.get('home_goals_scored_avg') or 1.2)
                home_conceded = float(row.get('home_goals_conceded_avg') or 1.2)
                away_scored = float(row.get('away_goals_scored_avg') or 1.0)
                away_conceded = float(row.get('away_goals_conceded_avg') or 1.2)
                
                avg_scored = (home_scored + away_scored) / 2
                avg_conceded = (home_conceded + away_conceded) / 2
                
                # Profil
                if avg_scored >= 1.8 and avg_conceded >= 1.3:
                    profile = 'OPEN_PLAY'
                elif avg_scored >= 1.6 and avg_conceded < 1.0:
                    profile = 'OFFENSIVE'
                elif avg_scored < 1.2 and avg_conceded < 1.0:
                    profile = 'LOW_SCORING'
                elif avg_conceded < 1.0:
                    profile = 'DEFENSIVE'
                elif avg_scored >= 1.5:
                    profile = 'OFFENSIVE'
                else:
                    profile = 'BALANCED'
                    
                self.teams[team] = {
                    'league': row.get('league') or 'Unknown',
                    'profile': profile,
                    'avg_scored': avg_scored,
                    'avg_conceded': avg_conceded
                }
                
            # ML Profiles
            cur.execute("""
                SELECT team_name, market_type, win_rate, roi, is_best_market, is_avoid_market
                FROM team_market_profiles
                WHERE sample_size >= 8
            """)
            for row in cur.fetchall():
                team = row['team_name']
                if team not in self.ml_profiles:
                    self.ml_profiles[team] = {}
                self.ml_profiles[team][row['market_type']] = {
                    'win_rate': float(row.get('win_rate') or 0),
                    'roi': float(row.get('roi') or 0),
                    'is_best': row.get('is_best_market', False),
                    'is_avoid': row.get('is_avoid_market', False)
                }
                
            # Matches
            cur.execute("""
                SELECT match_id, home_team, away_team, 
                       score_home, score_away, league, commence_time
                FROM match_results 
                WHERE commence_time >= '2025-09-01' AND is_finished = true
                ORDER BY commence_time
            """)
            self.matches = cur.fetchall()
            
        print(f"✅ {len(self.teams)} équipes, {len(self.ml_profiles)} ML profiles, {len(self.matches)} matchs")
        
    def normalize_team(self, name: str) -> str:
        mappings = {
            'FC Bayern München': 'Bayern Munich', 'FC Barcelona': 'Barcelona',
            'Real Madrid CF': 'Real Madrid', 'Liverpool FC': 'Liverpool',
        }
        if name in mappings:
            return mappings[name]
        for suffix in [' FC', ' CF', ' SC', ' BC', ' AFC']:
            if name.endswith(suffix):
                return name[:-len(suffix)].strip()
        return name
        
    def get_team_data(self, name: str):
        norm = self.normalize_team(name)
        team_data = None
        ml_data = None
        
        for t in self.teams:
            if t.lower() in name.lower() or name.lower() in t.lower() or t == norm:
                team_data = self.teams[t]
                break
        for t in self.ml_profiles:
            if t.lower() in name.lower() or name.lower() in t.lower() or t == norm:
                ml_data = self.ml_profiles[t]
                break
                
        return team_data, ml_data
        
    def evaluate_market(self, match: dict, market: str) -> bool:
        home = match['score_home'] or 0
        away = match['score_away'] or 0
        total = home + away
        both = home > 0 and away > 0
        
        return {
            'over_15': total >= 2, 'over_25': total >= 3, 'over_35': total >= 4,
            'under_15': total < 2, 'under_25': total < 3, 'under_35': total < 4,
            'btts_yes': both, 'btts_no': not both,
        }.get(market, False)
        
    def get_optimal_bet(self, team_name: str, team_data: dict, ml_data: dict) -> dict:
        """Détermine le pari optimal pour une équipe"""
        if not team_data:
            return None
            
        # Check blacklist
        norm = self.normalize_team(team_name)
        if any(b.lower() in norm.lower() for b in BLACKLIST):
            return None
            
        profile = team_data['profile']
        config = OPTIMAL_CONFIG.get(profile, OPTIMAL_CONFIG['BALANCED'])
        
        # Chercher le meilleur marché selon la stratégie
        market = None
        stake = 2.0
        reason = ""
        
        if config['strategy'] == 'CONSERVATIVE':
            # Seulement si ML confirme avec ROI >= 30% et WR >= 65%
            if ml_data:
                for m in [config['primary_market'], config['secondary_market']]:
                    if m and m in ml_data:
                        ml = ml_data[m]
                        if ml['roi'] >= config['min_roi'] and ml['win_rate'] >= config['min_wr']:
                            market = m
                            stake = 2.5
                            reason = f"CONSERVATIVE: {profile} + ML confirmed ({ml['roi']:+.0f}% ROI)"
                            break
                            
        elif config['strategy'] == 'QUANT_ONLY':
            # Utiliser le best market ML
            if ml_data:
                for m, ml in ml_data.items():
                    if ml.get('is_best') and ml['roi'] >= config['min_roi'] and m in MARKET_ODDS:
                        market = m
                        stake = 2.0
                        reason = f"QUANT_ONLY: Best ML market ({ml['roi']:+.0f}% ROI)"
                        break
                        
        elif config['strategy'] == 'BEST_MARKET_ONLY':
            # Le marché avec le meilleur ROI
            if ml_data:
                best_roi = -999
                for m, ml in ml_data.items():
                    if ml['roi'] > best_roi and ml['roi'] >= config['min_roi'] and m in MARKET_ODDS:
                        best_roi = ml['roi']
                        market = m
                        stake = 2.0
                        reason = f"BEST_MARKET: {m} ({ml['roi']:+.0f}% ROI)"
                        
        if not market:
            return None
            
        return {
            'market': market,
            'stake': stake,
            'odds': MARKET_ODDS.get(market, 1.85),
            'reason': reason,
            'profile': profile,
            'strategy': config['strategy']
        }
        
    def run_backtest(self):
        """Execute le backtest avec le moteur adaptatif"""
        print("\n" + "="*80)
        print("🚀 BACKTEST ADAPTIVE TEAM ENGINE")
        print("="*80)
        
        team_performance = defaultdict(lambda: {'bets': 0, 'wins': 0, 'profit': 0})
        
        for match in self.matches:
            for team_name in [match['home_team'], match['away_team']]:
                team_data, ml_data = self.get_team_data(team_name)
                
                bet = self.get_optimal_bet(team_name, team_data, ml_data)
                if not bet:
                    continue
                    
                self.results['bets'] += 1
                self.results['stake'] += bet['stake']
                
                won = self.evaluate_market(match, bet['market'])
                
                norm = self.normalize_team(team_name)
                team_performance[norm]['bets'] += 1
                
                if won:
                    self.results['wins'] += 1
                    profit = bet['stake'] * (bet['odds'] - 1)
                    self.results['profit'] += profit
                    team_performance[norm]['wins'] += 1
                    team_performance[norm]['profit'] += profit
                else:
                    self.results['profit'] -= bet['stake']
                    team_performance[norm]['profit'] -= bet['stake']
                    
                self.results['details'].append({
                    'team': team_name,
                    'match': f"{match['home_team']} vs {match['away_team']}",
                    'market': bet['market'],
                    'stake': bet['stake'],
                    'won': won,
                    'strategy': bet['strategy'],
                    'reason': bet['reason']
                })
                
        return team_performance
        
    def print_results(self, team_perf):
        """Affiche les résultats"""
        print("\n" + "="*80)
        print("📊 RÉSULTATS - ADAPTIVE TEAM ENGINE")
        print("="*80)
        
        wr = (self.results['wins'] / self.results['bets']) * 100 if self.results['bets'] > 0 else 0
        roi = (self.results['profit'] / self.results['stake']) * 100 if self.results['stake'] > 0 else 0
        
        print(f"\n🎯 PERFORMANCE GLOBALE:")
        print(f"   Paris: {self.results['bets']}")
        print(f"   Wins: {self.results['wins']}")
        print(f"   Win Rate: {wr:.1f}%")
        print(f"   ROI: {roi:+.1f}%")
        print(f"   P&L: {self.results['profit']:+.1f}u")
        
        print("\n" + "="*80)
        print("📈 COMPARAISON AVEC AUTRES STRATÉGIES")
        print("="*80)
        print(f"\n{'Stratégie':<25} {'Paris':<8} {'WR':<10} {'ROI':<12} {'P&L':<12}")
        print("-"*70)
        print(f"{'🚀 ADAPTIVE ENGINE':<25} {self.results['bets']:<8} {wr:.1f}%{'':<5} {roi:+.1f}%{'':<6} {self.results['profit']:+.1f}u")
        print(f"{'CONSERVATIVE':<25} {'286':<8} {'78.3%':<10} {'+45.6%':<12} {'+326.0u':<12}")
        print(f"{'QUANT_ONLY':<25} {'482':<8} {'69.7%':<10} {'+33.2%':<12} {'+320.4u':<12}")
        print(f"{'BEST_MARKET_ONLY':<25} {'1012':<8} {'67.2%':<10} {'+29.5%':<12} {'+597.7u':<12}")
        print(f"{'V13 REFERENCE':<25} {'204':<8} {'76.5%':<10} {'+53.2%':<12} {'+210.7u':<12}")
        
        # Top équipes
        print("\n" + "="*80)
        print("💎 TOP 15 ÉQUIPES - ADAPTIVE ENGINE")
        print("="*80)
        
        team_list = []
        for team, data in team_perf.items():
            if data['bets'] >= 3:
                team_wr = (data['wins'] / data['bets']) * 100
                team_roi = (data['profit'] / (data['bets'] * 2)) * 100
                team_list.append({
                    'team': team,
                    'bets': data['bets'],
                    'wins': data['wins'],
                    'wr': team_wr,
                    'roi': team_roi,
                    'profit': data['profit']
                })
                
        team_list.sort(key=lambda x: x['profit'], reverse=True)
        
        print(f"\n{'#':<3} {'Équipe':<25} {'Paris':<8} {'WR':<10} {'ROI':<12} {'P&L':<10}")
        print("-"*70)
        
        for i, t in enumerate(team_list[:15], 1):
            emoji = "💎" if t['profit'] >= 15 else "✅" if t['profit'] > 0 else "⚠️"
            print(f"{emoji}{i:<2} {t['team'][:24]:<25} {t['bets']:<8} {t['wr']:.1f}%{'':<5} {t['roi']:+.1f}%{'':<6} {t['profit']:+.1f}u")


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║       🚀 ADAPTIVE TEAM ENGINE - MOTEUR ADAPTATIF PAR ÉQUIPE                  ║
║                                                                               ║
║  Combine automatiquement:                                                    ║
║  • CONSERVATIVE pour OFFENSIVE/OPEN_PLAY (ROI≥30%, WR≥65%)                  ║
║  • QUANT_ONLY pour LOW_SCORING (best ML market)                              ║
║  • BEST_MARKET_ONLY pour DEFENSIVE/BALANCED                                  ║
║  • Blacklist les équipes à ROI négatif                                       ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    engine = AdaptiveTeamEngine()
    engine.connect()
    engine.load_data()
    team_perf = engine.run_backtest()
    engine.print_results(team_perf)
    
    # Sauvegarder
    with open('/home/Mon_ps/benchmarks/adaptive_engine_results.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'global': {
                'bets': engine.results['bets'],
                'wins': engine.results['wins'],
                'profit': round(engine.results['profit'], 1)
            }
        }, f, indent=2)
    
    print("\n✅ Résultats sauvegardés")


if __name__ == "__main__":
    main()
