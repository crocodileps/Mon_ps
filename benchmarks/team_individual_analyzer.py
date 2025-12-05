#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║          🎯 TEAM INDIVIDUAL ANALYZER - ANALYSE PAR ÉQUIPE                     ║
║                                                                               ║
║  Chaque équipe a son propre profil et sa propre stratégie optimale:          ║
║  • Bayern = Offensive → Over 2.5 / Over 3.5                                  ║
║  • Lazio = Défensive → BTTS NO / Under 2.5                                   ║
║  • Real Sociedad = Open → BTTS YES                                           ║
║                                                                               ║
║  Output: Tableau individuel par équipe avec WR, ROI, P&L, Best Market        ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Dict, List
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

# Profils d'équipe
TEAM_PROFILES = {
    'OFFENSIVE': {
        'description': 'Marque beaucoup, défense moyenne',
        'best_markets': ['over_25', 'over_35', 'btts_yes'],
        'avoid_markets': ['under_25', 'btts_no']
    },
    'DEFENSIVE': {
        'description': 'Défense solide, attaque limitée',
        'best_markets': ['under_25', 'btts_no', 'under_35'],
        'avoid_markets': ['over_35', 'btts_yes']
    },
    'OPEN_PLAY': {
        'description': 'Marque et encaisse beaucoup',
        'best_markets': ['btts_yes', 'over_25', 'over_35'],
        'avoid_markets': ['under_25', 'btts_no']
    },
    'LOW_SCORING': {
        'description': 'Peu de buts marqués et encaissés',
        'best_markets': ['under_25', 'under_35', 'btts_no'],
        'avoid_markets': ['over_25', 'over_35']
    },
    'BALANCED': {
        'description': 'Équipe équilibrée',
        'best_markets': ['over_25'],
        'avoid_markets': []
    }
}


class TeamIndividualAnalyzer:
    """Analyse individuelle par équipe"""
    
    def __init__(self):
        self.conn = None
        self.team_stats = {}  # team -> {profile, matches, results_by_market}
        self.matches = []
        
    def connect(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connexion DB établie")
        
    def load_team_intelligence(self):
        """Charge les données d'intelligence par équipe"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    team_name,
                    league,
                    home_goals_scored_avg,
                    home_goals_conceded_avg,
                    away_goals_scored_avg,
                    away_goals_conceded_avg,
                    home_over25_rate,
                    away_over25_rate,
                    home_btts_rate,
                    away_btts_rate,
                    home_clean_sheet_rate,
                    away_clean_sheet_rate,
                    goals_tendency,
                    btts_tendency,
                    clean_sheet_tendency,
                    tags,
                    market_alerts
                FROM team_intelligence
                WHERE home_goals_scored_avg IS NOT NULL
            """)
            rows = cur.fetchall()
            
        for row in rows:
            team = row['team_name']
            
            # Calculer le profil de l'équipe
            home_scored = float(row.get('home_goals_scored_avg') or 1.2)
            home_conceded = float(row.get('home_goals_conceded_avg') or 1.2)
            away_scored = float(row.get('away_goals_scored_avg') or 1.0)
            away_conceded = float(row.get('away_goals_conceded_avg') or 1.2)
            
            avg_scored = (home_scored + away_scored) / 2
            avg_conceded = (home_conceded + away_conceded) / 2
            
            # Déterminer le profil
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
                
            self.team_stats[team] = {
                'league': row.get('league', ''),
                'profile': profile,
                'avg_scored': avg_scored,
                'avg_conceded': avg_conceded,
                'home_over25': float(row.get('home_over25_rate') or 50),
                'away_over25': float(row.get('away_over25_rate') or 50),
                'home_btts': float(row.get('home_btts_rate') or 50),
                'away_btts': float(row.get('away_btts_rate') or 50),
                'clean_sheet': float(row.get('home_clean_sheet_rate') or 20),
                'tags': row.get('tags', []),
                # Résultats par marché (à remplir)
                'results': {
                    'over_25': {'bets': 0, 'wins': 0, 'stake': 0, 'profit': 0},
                    'over_35': {'bets': 0, 'wins': 0, 'stake': 0, 'profit': 0},
                    'under_25': {'bets': 0, 'wins': 0, 'stake': 0, 'profit': 0},
                    'btts_yes': {'bets': 0, 'wins': 0, 'stake': 0, 'profit': 0},
                    'btts_no': {'bets': 0, 'wins': 0, 'stake': 0, 'profit': 0},
                }
            }
            
        print(f"✅ {len(self.team_stats)} équipes avec profils chargées")
        
        # Stats par profil
        profiles_count = defaultdict(int)
        for t in self.team_stats.values():
            profiles_count[t['profile']] += 1
        print(f"   Profils: {dict(profiles_count)}")
        
    def load_matches(self):
        """Charge les matchs terminés"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT match_id, home_team, away_team, 
                       score_home, score_away, league,
                       commence_time
                FROM match_results 
                WHERE commence_time >= '2025-09-01' 
                AND is_finished = true
                ORDER BY commence_time
            """)
            self.matches = cur.fetchall()
        print(f"✅ {len(self.matches)} matchs chargés")
        
    def normalize_team(self, name: str) -> str:
        """Normalise le nom d'équipe"""
        mappings = {
            'FC Bayern München': 'Bayern Munich',
            'FC Barcelona': 'Barcelona',
            'Real Madrid CF': 'Real Madrid',
            'Liverpool FC': 'Liverpool',
            'Manchester City FC': 'Manchester City',
            'Manchester United FC': 'Manchester United',
            'Arsenal FC': 'Arsenal',
            'Chelsea FC': 'Chelsea',
            'Tottenham Hotspur FC': 'Tottenham',
            'Newcastle United FC': 'Newcastle',
            'Paris Saint-Germain FC': 'Paris Saint Germain',
            'Olympique de Marseille': 'Marseille',
            'SSC Napoli': 'Napoli',
            'Juventus FC': 'Juventus',
            'Inter Milan': 'Inter',
            'AC Milan': 'Milan',
            'SS Lazio': 'Lazio',
            'AS Roma': 'Roma',
            'Borussia Dortmund': 'Borussia Dortmund',
            'Bayer 04 Leverkusen': 'Bayer Leverkusen',
        }
        if name in mappings:
            return mappings[name]
        for suffix in [' FC', ' CF', ' SC', ' BC', ' AFC']:
            if name.endswith(suffix):
                return name[:-len(suffix)].strip()
        return name
        
    def get_team_stats(self, team: str) -> dict:
        """Récupère les stats d'une équipe"""
        norm = self.normalize_team(team)
        if norm in self.team_stats:
            return self.team_stats[norm]
        for t in self.team_stats:
            if t.lower() in team.lower() or team.lower() in t.lower():
                return self.team_stats[t]
        return None
        
    def evaluate_all_markets(self, match: dict, team: str, is_home: bool):
        """Évalue tous les marchés pour une équipe dans un match"""
        stats = self.get_team_stats(team)
        if not stats:
            return
            
        home_score = match['score_home'] or 0
        away_score = match['score_away'] or 0
        total_goals = home_score + away_score
        both_scored = home_score > 0 and away_score > 0
        
        # Résultats par marché
        results = {
            'over_25': total_goals >= 3,
            'over_35': total_goals >= 4,
            'under_25': total_goals < 3,
            'btts_yes': both_scored,
            'btts_no': not both_scored,
        }
        
        # Simuler les paris basés sur le profil
        profile_config = TEAM_PROFILES.get(stats['profile'], TEAM_PROFILES['BALANCED'])
        
        for market in results.keys():
            # Parier seulement sur les best_markets du profil
            if market in profile_config['best_markets']:
                odds = MARKET_ODDS.get(market, 1.85)
                stake = 2.0
                
                stats['results'][market]['bets'] += 1
                stats['results'][market]['stake'] += stake
                
                if results[market]:
                    stats['results'][market]['wins'] += 1
                    stats['results'][market]['profit'] += stake * (odds - 1)
                else:
                    stats['results'][market]['profit'] -= stake
                    
    def run_analysis(self):
        """Execute l'analyse individuelle"""
        print("\n" + "="*80)
        print("🎯 ANALYSE INDIVIDUELLE PAR ÉQUIPE")
        print("="*80)
        
        for match in self.matches:
            # Analyser pour l'équipe à domicile
            self.evaluate_all_markets(match, match['home_team'], is_home=True)
            # Analyser pour l'équipe à l'extérieur
            self.evaluate_all_markets(match, match['away_team'], is_home=False)
            
    def calculate_team_performance(self, team: str, stats: dict) -> dict:
        """Calcule la performance globale d'une équipe"""
        total_bets = 0
        total_wins = 0
        total_stake = 0
        total_profit = 0
        best_market = None
        best_roi = -999
        
        for market, data in stats['results'].items():
            if data['bets'] > 0:
                total_bets += data['bets']
                total_wins += data['wins']
                total_stake += data['stake']
                total_profit += data['profit']
                
                roi = (data['profit'] / data['stake']) * 100 if data['stake'] > 0 else 0
                if roi > best_roi and data['bets'] >= 3:
                    best_roi = roi
                    best_market = market
                    
        return {
            'team': team,
            'league': stats.get('league', ''),
            'profile': stats['profile'],
            'avg_scored': stats['avg_scored'],
            'avg_conceded': stats['avg_conceded'],
            'total_bets': total_bets,
            'total_wins': total_wins,
            'win_rate': (total_wins / total_bets) * 100 if total_bets > 0 else 0,
            'total_stake': total_stake,
            'total_profit': total_profit,
            'roi': (total_profit / total_stake) * 100 if total_stake > 0 else 0,
            'best_market': best_market,
            'best_market_roi': best_roi,
            'results_by_market': stats['results']
        }
        
    def print_results(self):
        """Affiche les résultats par équipe"""
        print("\n" + "="*100)
        print("📊 TABLEAU INDIVIDUEL PAR ÉQUIPE - PERFORMANCE & MEILLEUR MARCHÉ")
        print("="*100)
        
        # Calculer performance de chaque équipe
        performances = []
        for team, stats in self.team_stats.items():
            if any(stats['results'][m]['bets'] > 0 for m in stats['results']):
                perf = self.calculate_team_performance(team, stats)
                if perf['total_bets'] >= 5:  # Minimum 5 paris
                    performances.append(perf)
                    
        # Trier par ROI
        performances.sort(key=lambda x: x['roi'], reverse=True)
        
        # Top 20 équipes (pépites)
        print(f"\n🥇 TOP 20 ÉQUIPES (ROI positif) - Les PÉPITES cachées:")
        print("-"*100)
        print(f"{'#':<3} {'Équipe':<25} {'Ligue':<15} {'Profil':<12} {'Paris':<6} {'WR':<8} {'ROI':<10} {'P&L':<10} {'Best Market':<12}")
        print("-"*100)
        
        for i, p in enumerate(performances[:20], 1):
            emoji = "💎" if p['roi'] >= 30 else "🥇" if i <= 3 else "🥈" if i <= 6 else "🥉" if i <= 10 else "  "
            print(f"{emoji}{i:<2} {(p['team'] or 'Unknown')[:24]:<25} {(p['league'] or 'Unknown')[:14]:<15} {p['profile']:<12} {p['total_bets']:<6} {p['win_rate']:.1f}%{'':<3} {p['roi']:+.1f}%{'':<4} {p['total_profit']:+.1f}u{'':<4} {p['best_market'] or 'N/A':<12}")
            
        # Équipes à éviter
        print(f"\n⚠️ ÉQUIPES À ÉVITER (ROI négatif):")
        print("-"*100)
        
        negative = [p for p in performances if p['roi'] < -10]
        negative.sort(key=lambda x: x['roi'])
        
        for p in negative[:10]:
            print(f"❌  {(p['team'] or 'Unknown')[:24]:<25} {(p['league'] or 'Unknown')[:14]:<15} {p['profile']:<12} {p['total_bets']:<6} {p['win_rate']:.1f}%{'':<3} {p['roi']:+.1f}%{'':<4} {p['total_profit']:+.1f}u")
            
        # Analyse par profil
        print(f"\n📈 ANALYSE PAR PROFIL D'ÉQUIPE:")
        print("-"*60)
        
        profiles_stats = defaultdict(lambda: {'teams': 0, 'bets': 0, 'wins': 0, 'profit': 0, 'stake': 0})
        for p in performances:
            profile = p['profile']
            profiles_stats[profile]['teams'] += 1
            profiles_stats[profile]['bets'] += p['total_bets']
            profiles_stats[profile]['wins'] += p['total_wins']
            profiles_stats[profile]['profit'] += p['total_profit']
            profiles_stats[profile]['stake'] += p['total_stake']
            
        print(f"{'Profil':<15} {'Équipes':<10} {'Paris':<8} {'WR':<10} {'ROI':<12} {'P&L':<12}")
        print("-"*60)
        
        for profile, data in sorted(profiles_stats.items(), key=lambda x: x[1]['profit'], reverse=True):
            wr = (data['wins'] / data['bets']) * 100 if data['bets'] > 0 else 0
            roi = (data['profit'] / data['stake']) * 100 if data['stake'] > 0 else 0
            print(f"{profile:<15} {data['teams']:<10} {data['bets']:<8} {wr:.1f}%{'':<5} {roi:+.1f}%{'':<6} {data['profit']:+.1f}u")
            
        # Détail par équipe et marché
        print(f"\n📋 DÉTAIL PAR ÉQUIPE - TOUS LES MARCHÉS:")
        print("="*120)
        
        for p in performances[:15]:
            print(f"\n{'─'*60}")
            print(f"🏆 {p['team']} ({p['league']}) - Profil: {p['profile']}")
            print(f"   Avg Scored: {p['avg_scored']:.2f} | Avg Conceded: {p['avg_conceded']:.2f}")
            print(f"   Global: {p['total_bets']} paris | {p['win_rate']:.1f}% WR | {p['roi']:+.1f}% ROI | {p['total_profit']:+.1f}u")
            print(f"   {'Marché':<12} {'Paris':<8} {'Wins':<8} {'WR':<10} {'ROI':<12} {'P&L':<10}")
            
            for market, data in p['results_by_market'].items():
                if data['bets'] > 0:
                    wr = (data['wins'] / data['bets']) * 100
                    roi = (data['profit'] / data['stake']) * 100 if data['stake'] > 0 else 0
                    emoji = "✅" if roi > 0 else "❌"
                    print(f"   {emoji} {market:<10} {data['bets']:<8} {data['wins']:<8} {wr:.1f}%{'':<5} {roi:+.1f}%{'':<6} {data['profit']:+.1f}u")
                    
        # Résumé final
        print("\n" + "="*80)
        print("💡 CONCLUSIONS")
        print("="*80)
        
        total_profit = sum(p['total_profit'] for p in performances)
        total_bets = sum(p['total_bets'] for p in performances)
        total_wins = sum(p['total_wins'] for p in performances)
        
        print(f"\n📊 GLOBAL:")
        print(f"   {len(performances)} équipes analysées")
        print(f"   {total_bets} paris totaux")
        print(f"   {(total_wins/total_bets)*100:.1f}% Win Rate global")
        print(f"   {total_profit:+.1f}u P&L total")
        
        profitable_teams = [p for p in performances if p['roi'] > 0]
        print(f"\n💎 PÉPITES ({len(profitable_teams)} équipes rentables):")
        for p in profitable_teams[:5]:
            print(f"   • {p['team']}: {p['best_market']} → {p['roi']:+.1f}% ROI, {p['total_profit']:+.1f}u")
            
        return performances


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║          🎯 TEAM INDIVIDUAL ANALYZER - ANALYSE PAR ÉQUIPE                     ║
║                                                                               ║
║  Chaque équipe = sa propre stratégie optimale                                ║
║  • OFFENSIVE (Bayern, Barcelone) → Over 2.5, Over 3.5                        ║
║  • DEFENSIVE (Lazio, Juventus) → Under 2.5, BTTS NO                          ║
║  • OPEN_PLAY (Real Sociedad) → BTTS YES, Over 2.5                            ║
║  • LOW_SCORING → Under 2.5, Under 3.5                                        ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    analyzer = TeamIndividualAnalyzer()
    analyzer.connect()
    analyzer.load_team_intelligence()
    analyzer.load_matches()
    analyzer.run_analysis()
    performances = analyzer.print_results()
    
    # Sauvegarder
    output = {
        'timestamp': datetime.now().isoformat(),
        'teams_analyzed': len(performances),
        'performances': [
            {
                'team': p['team'],
                'league': p['league'],
                'profile': p['profile'],
                'bets': p['total_bets'],
                'wins': p['total_wins'],
                'win_rate': round(p['win_rate'], 1),
                'roi': round(p['roi'], 1),
                'profit': round(p['total_profit'], 1),
                'best_market': p['best_market'],
                'best_market_roi': round(p['best_market_roi'], 1) if p['best_market_roi'] != -999 else None
            }
            for p in performances
        ]
    }
    
    with open('/home/Mon_ps/benchmarks/team_individual_results.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print("\n✅ Résultats sauvegardés dans team_individual_results.json")


if __name__ == "__main__":
    main()
