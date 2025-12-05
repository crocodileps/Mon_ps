#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║       🎯 TEAM STRATEGY MATRIX - MEILLEURE STRATÉGIE PAR ÉQUIPE               ║
║                                                                               ║
║  Teste 4 stratégies pour chaque équipe et identifie la meilleure:            ║
║  • QUANT_ONLY: Team Market Profile seul                                      ║
║  • HYBRID_CONSERVATIVE: V13 prioritaire + Profile fallback                   ║
║  • HYBRID_AGGRESSIVE: V13 + Profile combinés                                 ║
║  • PROFILE_ADAPTIVE: Adapté au profil (OFF/DEF/OPEN/LOW)                     ║
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

# Configuration des stratégies par profil
PROFILE_STRATEGIES = {
    'OFFENSIVE': {
        'markets': ['over_25', 'over_35', 'btts_yes'],
        'weights': {'over_25': 0.4, 'over_35': 0.35, 'btts_yes': 0.25}
    },
    'DEFENSIVE': {
        'markets': ['under_25', 'btts_no'],
        'weights': {'under_25': 0.5, 'btts_no': 0.5}
    },
    'OPEN_PLAY': {
        'markets': ['btts_yes', 'over_25', 'over_35'],
        'weights': {'btts_yes': 0.4, 'over_25': 0.35, 'over_35': 0.25}
    },
    'LOW_SCORING': {
        'markets': ['under_25', 'btts_no', 'under_35'],
        'weights': {'under_25': 0.4, 'btts_no': 0.4, 'under_35': 0.2}
    },
    'BALANCED': {
        'markets': ['over_25'],
        'weights': {'over_25': 1.0}
    }
}


class TeamStrategyMatrix:
    def __init__(self):
        self.conn = None
        self.teams = {}
        self.matches = []
        
    def connect(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connexion DB établie")
        
    def load_teams(self):
        """Charge les équipes avec leurs stats"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    team_name, league,
                    home_goals_scored_avg, home_goals_conceded_avg,
                    away_goals_scored_avg, away_goals_conceded_avg,
                    home_over25_rate, away_over25_rate,
                    home_btts_rate, away_btts_rate,
                    home_clean_sheet_rate
                FROM team_intelligence
                WHERE home_goals_scored_avg IS NOT NULL
            """)
            rows = cur.fetchall()
            
        for row in rows:
            team = row['team_name']
            
            home_scored = float(row.get('home_goals_scored_avg') or 1.2)
            home_conceded = float(row.get('home_goals_conceded_avg') or 1.2)
            away_scored = float(row.get('away_goals_scored_avg') or 1.0)
            away_conceded = float(row.get('away_goals_conceded_avg') or 1.2)
            
            avg_scored = (home_scored + away_scored) / 2
            avg_conceded = (home_conceded + away_conceded) / 2
            
            # Déterminer profil
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
                'avg_conceded': avg_conceded,
                'home_o25': float(row.get('home_over25_rate') or 50),
                'away_o25': float(row.get('away_over25_rate') or 50),
                'clean_sheet': float(row.get('home_clean_sheet_rate') or 20),
                # Résultats par stratégie
                'strategies': {
                    'QUANT_ONLY': {'bets': 0, 'wins': 0, 'stake': 0, 'profit': 0},
                    'PROFILE_ADAPTIVE': {'bets': 0, 'wins': 0, 'stake': 0, 'profit': 0},
                    'BEST_MARKET_ONLY': {'bets': 0, 'wins': 0, 'stake': 0, 'profit': 0},
                    'CONSERVATIVE': {'bets': 0, 'wins': 0, 'stake': 0, 'profit': 0},
                },
                'markets': {m: {'bets': 0, 'wins': 0, 'profit': 0} for m in MARKET_ODDS.keys()}
            }
            
        print(f"✅ {len(self.teams)} équipes chargées")
        
    def load_team_market_profiles(self):
        """Charge les best markets depuis team_market_profiles"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT team_name, market_type, win_rate, roi, is_best_market, is_avoid_market
                FROM team_market_profiles
                WHERE sample_size >= 8
            """)
            rows = cur.fetchall()
            
        for row in rows:
            team = row['team_name']
            if team in self.teams:
                if 'ml_profiles' not in self.teams[team]:
                    self.teams[team]['ml_profiles'] = {}
                self.teams[team]['ml_profiles'][row['market_type']] = {
                    'win_rate': float(row.get('win_rate') or 0),
                    'roi': float(row.get('roi') or 0),
                    'is_best': row.get('is_best_market', False),
                    'is_avoid': row.get('is_avoid_market', False)
                }
                
        print(f"✅ ML Profiles chargés")
        
    def load_matches(self):
        """Charge les matchs"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT match_id, home_team, away_team, 
                       score_home, score_away, league, commence_time
                FROM match_results 
                WHERE commence_time >= '2025-09-01' AND is_finished = true
                ORDER BY commence_time
            """)
            self.matches = cur.fetchall()
        print(f"✅ {len(self.matches)} matchs chargés")
        
    def normalize_team(self, name: str) -> str:
        mappings = {
            'FC Bayern München': 'Bayern Munich', 'FC Barcelona': 'Barcelona',
            'Real Madrid CF': 'Real Madrid', 'Liverpool FC': 'Liverpool',
            'Manchester City FC': 'Manchester City', 'Paris Saint-Germain FC': 'Paris Saint Germain',
        }
        if name in mappings:
            return mappings[name]
        for suffix in [' FC', ' CF', ' SC', ' BC', ' AFC']:
            if name.endswith(suffix):
                return name[:-len(suffix)].strip()
        return name
        
    def get_team(self, name: str) -> dict:
        norm = self.normalize_team(name)
        if norm in self.teams:
            return self.teams[norm]
        for t in self.teams:
            if t.lower() in name.lower() or name.lower() in t.lower():
                return self.teams[t]
        return None
        
    def evaluate_market(self, match: dict, market: str) -> bool:
        """Évalue si un marché est gagnant"""
        home = match['score_home'] or 0
        away = match['score_away'] or 0
        total = home + away
        both = home > 0 and away > 0
        
        return {
            'over_15': total >= 2, 'over_25': total >= 3, 'over_35': total >= 4,
            'under_15': total < 2, 'under_25': total < 3, 'under_35': total < 4,
            'btts_yes': both, 'btts_no': not both,
        }.get(market, False)
        
    def run_analysis(self):
        """Analyse chaque équipe avec chaque stratégie"""
        print("\n" + "="*80)
        print("🎯 ANALYSE STRATÉGIE PAR ÉQUIPE")
        print("="*80)
        
        for match in self.matches:
            for team_name in [match['home_team'], match['away_team']]:
                team = self.get_team(team_name)
                if not team:
                    continue
                    
                profile = team['profile']
                profile_config = PROFILE_STRATEGIES.get(profile, PROFILE_STRATEGIES['BALANCED'])
                
                # Résultats réels
                results = {m: self.evaluate_market(match, m) for m in MARKET_ODDS.keys()}
                
                # ═══════════════════════════════════════════════════════════════
                # STRATÉGIE 1: QUANT_ONLY (ML Profile best market)
                # ═══════════════════════════════════════════════════════════════
                ml_profiles = team.get('ml_profiles', {})
                for market, ml in ml_profiles.items():
                    if ml.get('is_best') and ml.get('roi', 0) >= 20 and market in MARKET_ODDS:
                        odds = MARKET_ODDS[market]
                        stake = 2.0
                        team['strategies']['QUANT_ONLY']['bets'] += 1
                        team['strategies']['QUANT_ONLY']['stake'] += stake
                        if results.get(market, False):
                            team['strategies']['QUANT_ONLY']['wins'] += 1
                            team['strategies']['QUANT_ONLY']['profit'] += stake * (odds - 1)
                        else:
                            team['strategies']['QUANT_ONLY']['profit'] -= stake
                        break
                        
                # ═══════════════════════════════════════════════════════════════
                # STRATÉGIE 2: PROFILE_ADAPTIVE (basé sur le profil)
                # ═══════════════════════════════════════════════════════════════
                for market in profile_config['markets']:
                    weight = profile_config['weights'].get(market, 0.33)
                    odds = MARKET_ODDS.get(market, 1.85)
                    stake = 2.0 * weight
                    
                    team['strategies']['PROFILE_ADAPTIVE']['bets'] += 1
                    team['strategies']['PROFILE_ADAPTIVE']['stake'] += stake
                    
                    if results.get(market, False):
                        team['strategies']['PROFILE_ADAPTIVE']['wins'] += 1
                        team['strategies']['PROFILE_ADAPTIVE']['profit'] += stake * (odds - 1)
                    else:
                        team['strategies']['PROFILE_ADAPTIVE']['profit'] -= stake
                        
                    # Track market results
                    team['markets'][market]['bets'] += 1
                    if results.get(market, False):
                        team['markets'][market]['wins'] += 1
                        team['markets'][market]['profit'] += stake * (odds - 1)
                    else:
                        team['markets'][market]['profit'] -= stake
                        
                # ═══════════════════════════════════════════════════════════════
                # STRATÉGIE 3: BEST_MARKET_ONLY (le meilleur marché historique)
                # ═══════════════════════════════════════════════════════════════
                best_market = None
                best_roi = -999
                for market, ml in ml_profiles.items():
                    if ml.get('roi', 0) > best_roi and market in MARKET_ODDS:
                        best_roi = ml.get('roi', 0)
                        best_market = market
                        
                if best_market and best_roi > 0:
                    odds = MARKET_ODDS[best_market]
                    stake = 2.0
                    team['strategies']['BEST_MARKET_ONLY']['bets'] += 1
                    team['strategies']['BEST_MARKET_ONLY']['stake'] += stake
                    if results.get(best_market, False):
                        team['strategies']['BEST_MARKET_ONLY']['wins'] += 1
                        team['strategies']['BEST_MARKET_ONLY']['profit'] += stake * (odds - 1)
                    else:
                        team['strategies']['BEST_MARKET_ONLY']['profit'] -= stake
                        
                # ═══════════════════════════════════════════════════════════════
                # STRATÉGIE 4: CONSERVATIVE (seulement si ROI > 30% ET WR > 65%)
                # ═══════════════════════════════════════════════════════════════
                for market, ml in ml_profiles.items():
                    if ml.get('roi', 0) >= 30 and ml.get('win_rate', 0) >= 65 and market in MARKET_ODDS:
                        odds = MARKET_ODDS[market]
                        stake = 2.5
                        team['strategies']['CONSERVATIVE']['bets'] += 1
                        team['strategies']['CONSERVATIVE']['stake'] += stake
                        if results.get(market, False):
                            team['strategies']['CONSERVATIVE']['wins'] += 1
                            team['strategies']['CONSERVATIVE']['profit'] += stake * (odds - 1)
                        else:
                            team['strategies']['CONSERVATIVE']['profit'] -= stake
                        break
                        
    def print_results(self):
        """Affiche le tableau avec la meilleure stratégie par équipe"""
        print("\n" + "="*120)
        print("📊 MATRICE STRATÉGIE × ÉQUIPE - QUELLE STRATÉGIE POUR QUELLE ÉQUIPE?")
        print("="*120)
        
        # Calculer la meilleure stratégie pour chaque équipe
        team_results = []
        for team_name, data in self.teams.items():
            total_bets = sum(s['bets'] for s in data['strategies'].values())
            if total_bets < 5:
                continue
                
            best_strat = None
            best_roi = -999
            best_profit = -999
            
            for strat_name, strat_data in data['strategies'].items():
                if strat_data['bets'] >= 3 and strat_data['stake'] > 0:
                    roi = (strat_data['profit'] / strat_data['stake']) * 100
                    if roi > best_roi:
                        best_roi = roi
                        best_strat = strat_name
                        best_profit = strat_data['profit']
                        
            # Trouver le meilleur marché
            best_market = None
            best_market_roi = -999
            for market, mdata in data['markets'].items():
                if mdata['bets'] >= 3:
                    mroi = (mdata['profit'] / (mdata['bets'] * 2)) * 100 if mdata['bets'] > 0 else 0
                    if mroi > best_market_roi:
                        best_market_roi = mroi
                        best_market = market
                        
            team_results.append({
                'team': team_name,
                'league': data.get('league', 'Unknown'),
                'profile': data['profile'],
                'avg_scored': data['avg_scored'],
                'avg_conceded': data['avg_conceded'],
                'best_strategy': best_strat or 'N/A',
                'best_roi': best_roi,
                'best_profit': best_profit,
                'best_market': best_market or 'N/A',
                'best_market_roi': best_market_roi,
                'strategies': data['strategies']
            })
            
        # Trier par ROI
        team_results.sort(key=lambda x: x['best_roi'], reverse=True)
        
        # Header
        print(f"\n{'#':<3} {'Équipe':<22} {'Ligue':<12} {'Profil':<11} {'Best Strategy':<18} {'ROI':<9} {'P&L':<9} {'Best Market':<12} {'M-ROI':<8}")
        print("-"*120)
        
        for i, t in enumerate(team_results[:30], 1):
            emoji = "💎" if t['best_roi'] >= 40 else "🥇" if i <= 3 else "🥈" if i <= 6 else "🥉" if i <= 10 else "✅" if t['best_roi'] > 0 else "⚠️"
            
            print(f"{emoji}{i:<2} {t['team'][:21]:<22} {(t['league'] or 'Unk')[:11]:<12} {t['profile']:<11} {t['best_strategy']:<18} {t['best_roi']:+.1f}%{'':<3} {t['best_profit']:+.1f}u{'':<3} {t['best_market']:<12} {t['best_market_roi']:+.1f}%")
            
        # Équipes à éviter
        print(f"\n⚠️ ÉQUIPES À ÉVITER (ROI négatif toutes stratégies):")
        print("-"*120)
        negative = [t for t in team_results if t['best_roi'] < -10]
        negative.sort(key=lambda x: x['best_roi'])
        for t in negative[:10]:
            print(f"❌  {t['team'][:21]:<22} {(t['league'] or 'Unk')[:11]:<12} {t['profile']:<11} {t['best_strategy']:<18} {t['best_roi']:+.1f}%{'':<3} {t['best_profit']:+.1f}u")
            
        # Stats globales par stratégie
        print(f"\n📈 PERFORMANCE GLOBALE PAR STRATÉGIE:")
        print("-"*80)
        
        strat_totals = defaultdict(lambda: {'bets': 0, 'wins': 0, 'stake': 0, 'profit': 0})
        for t in team_results:
            for strat, data in t['strategies'].items():
                strat_totals[strat]['bets'] += data['bets']
                strat_totals[strat]['wins'] += data['wins']
                strat_totals[strat]['stake'] += data['stake']
                strat_totals[strat]['profit'] += data['profit']
                
        print(f"{'Stratégie':<20} {'Paris':<10} {'Wins':<10} {'WR':<10} {'ROI':<12} {'P&L':<12}")
        print("-"*80)
        
        sorted_strats = sorted(strat_totals.items(), key=lambda x: x[1]['profit'], reverse=True)
        for strat, data in sorted_strats:
            if data['bets'] > 0:
                wr = (data['wins'] / data['bets']) * 100
                roi = (data['profit'] / data['stake']) * 100 if data['stake'] > 0 else 0
                emoji = "🥇" if roi == max(s[1]['profit']/s[1]['stake']*100 if s[1]['stake'] > 0 else 0 for s in sorted_strats) else "  "
                print(f"{emoji} {strat:<18} {data['bets']:<10} {data['wins']:<10} {wr:.1f}%{'':<5} {roi:+.1f}%{'':<6} {data['profit']:+.1f}u")
                
        # Conclusion
        print("\n" + "="*80)
        print("💡 RECOMMANDATIONS FINALES")
        print("="*80)
        
        profitable = [t for t in team_results if t['best_roi'] > 20]
        print(f"\n🏆 {len(profitable)} équipes avec ROI > 20%")
        
        print("\n💎 TOP 5 PÉPITES à cibler:")
        for t in team_results[:5]:
            print(f"   • {t['team']}: {t['best_strategy']} sur {t['best_market']} → {t['best_roi']:+.1f}% ROI")
            
        print("\n🎯 STRATÉGIE RECOMMANDÉE PAR PROFIL:")
        profile_best = defaultdict(lambda: {'strat': None, 'roi': -999})
        for t in team_results:
            if t['best_roi'] > profile_best[t['profile']]['roi']:
                profile_best[t['profile']] = {'strat': t['best_strategy'], 'roi': t['best_roi'], 'market': t['best_market']}
                
        for profile, best in profile_best.items():
            print(f"   • {profile}: {best['strat']} → {best['market']}")
            
        return team_results


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║       🎯 TEAM STRATEGY MATRIX - MEILLEURE STRATÉGIE PAR ÉQUIPE               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    analyzer = TeamStrategyMatrix()
    analyzer.connect()
    analyzer.load_teams()
    analyzer.load_team_market_profiles()
    analyzer.load_matches()
    analyzer.run_analysis()
    results = analyzer.print_results()
    
    # Sauvegarder
    with open('/home/Mon_ps/benchmarks/team_strategy_matrix.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'teams': len(results),
            'results': [{k: v for k, v in t.items() if k != 'strategies'} for t in results]
        }, f, indent=2)
    
    print("\n✅ Résultats sauvegardés dans team_strategy_matrix.json")


if __name__ == "__main__":
    main()
