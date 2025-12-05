#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║            🎯 BENCHMARK INTELLIGENT - PAR LIGUE × MARCHÉ                      ║
║                                                                               ║
║  Trouve la MEILLEURE stratégie pour chaque combinaison:                      ║
║  • Ligue (Bundesliga, Premier League, Serie A, etc.)                         ║
║  • Marché (Over 2.5, BTTS, Over 3.5, 1X2)                                    ║
║                                                                               ║
║  Objectif: Stratégies PERSONNALISÉES, pas une taille unique!                 ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import sys
from datetime import datetime
from typing import Dict, List
import json

sys.path.insert(0, '/home/Mon_ps')
sys.path.insert(0, '/home/Mon_ps/backend')
sys.path.insert(0, '/home/Mon_ps/backend/agents')
sys.path.insert(0, '/home/Mon_ps/backend/agents/clv_tracker')

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

# ═══════════════════════════════════════════════════════════════════════════════
# DONNÉES DE RÉFÉRENCE PAR LIGUE (basées sur les stats réelles)
# ═══════════════════════════════════════════════════════════════════════════════
LEAGUE_PROFILES = {
    "Champions League": {
        "over25_rate": 67.8, "btts_rate": 53.3, "over35_rate": 48.9,
        "avg_goals": 3.44, "best_markets": ["over_25", "over_35"],
        "risk_level": "medium"
    },
    "Bundesliga": {
        "over25_rate": 62.5, "btts_rate": 56.7, "over35_rate": 39.2,
        "avg_goals": 3.18, "best_markets": ["over_25", "btts"],
        "risk_level": "low"
    },
    "Premier League": {
        "over25_rate": 56.9, "btts_rate": 54.2, "over35_rate": 30.7,
        "avg_goals": 2.85, "best_markets": ["over_25", "btts"],
        "risk_level": "medium"
    },
    "Ligue 1": {
        "over25_rate": 51.9, "btts_rate": 51.1, "over35_rate": 33.3,
        "avg_goals": 2.89, "best_markets": ["over_35"],
        "risk_level": "medium"
    },
    "La Liga": {
        "over25_rate": 47.9, "btts_rate": 54.2, "over35_rate": 25.4,
        "avg_goals": 2.59, "best_markets": ["btts"],
        "risk_level": "high"
    },
    "Serie A": {
        "over25_rate": 44.4, "btts_rate": 48.6, "over35_rate": 22.9,
        "avg_goals": 2.37, "best_markets": [],  # ÉVITER!
        "risk_level": "very_high"
    },
    "Primera Division": {
        "over25_rate": 50.0, "btts_rate": 61.1, "over35_rate": 38.9,
        "avg_goals": 2.72, "best_markets": ["btts", "over_35"],
        "risk_level": "medium"
    }
}

class SmartBenchmark:
    """Benchmark intelligent par ligue et marché"""
    
    def __init__(self):
        self.conn = None
        self.matches_by_league = {}
        self.results = {}
        
    def connect(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connexion DB établie")
        
    def load_matches_by_league(self):
        """Charge les matchs groupés par ligue"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    match_id, home_team, away_team, 
                    score_home, score_away, outcome,
                    commence_time, league, sport
                FROM match_results 
                WHERE commence_time >= '2025-09-01' 
                AND is_finished = true
                AND league IS NOT NULL AND league != ''
                ORDER BY league, commence_time
            """)
            matches = cur.fetchall()
            
        for match in matches:
            league = match['league']
            if league not in self.matches_by_league:
                self.matches_by_league[league] = []
            self.matches_by_league[league].append(match)
            
        print(f"✅ Matchs chargés par ligue:")
        for league, matches in self.matches_by_league.items():
            print(f"   {league}: {len(matches)} matchs")
        return self.matches_by_league
    
    def get_tactical_data(self, home: str, away: str) -> dict:
        """Récupère les données tactiques pour un match"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Team Intelligence Home
            cur.execute("""
                SELECT playing_style, xg_for_per_match, xg_against_per_match,
                       home_over25_rate, away_over25_rate
                FROM team_intelligence 
                WHERE team_name ILIKE %s LIMIT 1
            """, (f"%{home}%",))
            home_intel = cur.fetchone() or {}
            
            # Team Intelligence Away
            cur.execute("""
                SELECT playing_style, xg_for_per_match, xg_against_per_match,
                       home_over25_rate, away_over25_rate
                FROM team_intelligence 
                WHERE team_name ILIKE %s LIMIT 1
            """, (f"%{away}%",))
            away_intel = cur.fetchone() or {}
            
            # Tactical Matrix
            home_style = home_intel.get('playing_style', 'balanced')
            away_style = away_intel.get('playing_style', 'balanced')
            
            cur.execute("""
                SELECT over_25_probability, btts_probability, clean_sheet_probability
                FROM tactical_matrix 
                WHERE style_a = %s AND style_b = %s
                LIMIT 1
            """, (home_style, away_style))
            tactical = cur.fetchone() or {}
            
            # H2H
            cur.execute("""
                SELECT over_25_percentage, avg_total_goals, total_matches
                FROM head_to_head 
                WHERE (team_a ILIKE %s AND team_b ILIKE %s)
                OR (team_a ILIKE %s AND team_b ILIKE %s)
                LIMIT 1
            """, (f"%{home}%", f"%{away}%", f"%{away}%", f"%{home}%"))
            h2h = cur.fetchone() or {}
            
        return {
            'home_intel': dict(home_intel) if home_intel else {},
            'away_intel': dict(away_intel) if away_intel else {},
            'tactical': dict(tactical) if tactical else {},
            'h2h': dict(h2h) if h2h else {}
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # STRATÉGIES PAR MARCHÉ
    # ═══════════════════════════════════════════════════════════════════════════
    
    def evaluate_over25(self, match: dict, data: dict, league_profile: dict) -> dict:
        """Évalue Over 2.5 pour un match"""
        score = 0
        reasons = []
        
        # 1. Tactical Matrix (0-30)
        tactical_prob = data['tactical'].get('over_25_probability', 50)
        if tactical_prob >= 65:
            score += 30
            reasons.append(f"Tactical: {tactical_prob}%")
        elif tactical_prob >= 55:
            score += 20
            reasons.append(f"Tactical: {tactical_prob}%")
        elif tactical_prob >= 50:
            score += 10
            
        # 2. xG combiné (0-25)
        home_xg = data['home_intel'].get('xg_for_per_match', 1.3)
        away_xg = data['away_intel'].get('xg_for_per_match', 1.3)
        expected_goals = home_xg + away_xg
        if expected_goals >= 3.0:
            score += 25
            reasons.append(f"xG: {expected_goals:.1f}")
        elif expected_goals >= 2.7:
            score += 15
            reasons.append(f"xG: {expected_goals:.1f}")
        elif expected_goals >= 2.5:
            score += 10
            
        # 3. H2H (0-20)
        h2h_over25 = data['h2h'].get('over_25_percentage', 50)
        h2h_matches = data['h2h'].get('total_matches', 0)
        if h2h_matches >= 3 and h2h_over25 >= 70:
            score += 20
            reasons.append(f"H2H: {h2h_over25}%")
        elif h2h_matches >= 2 and h2h_over25 >= 60:
            score += 10
            
        # 4. League Profile Bonus (0-25)
        league_rate = league_profile.get('over25_rate', 50)
        if league_rate >= 60:
            score += 25
            reasons.append(f"League: {league_rate}%")
        elif league_rate >= 55:
            score += 15
        elif league_rate < 50:
            score -= 10  # Pénalité pour ligues défensives
            
        return {
            'market': 'over_25',
            'score': score,
            'confidence': min(score, 100),
            'reasons': reasons,
            'bet': score >= 60
        }
    
    def evaluate_btts(self, match: dict, data: dict, league_profile: dict) -> dict:
        """Évalue BTTS pour un match"""
        score = 0
        reasons = []
        
        # 1. Tactical Matrix (0-30)
        btts_prob = data['tactical'].get('btts_probability', 50)
        if btts_prob >= 60:
            score += 30
            reasons.append(f"Tactical BTTS: {btts_prob}%")
        elif btts_prob >= 50:
            score += 20
        elif btts_prob >= 45:
            score += 10
            
        # 2. Defensive weakness (0-25)
        home_xg_against = data['home_intel'].get('xg_against_per_match', 1.2)
        away_xg_against = data['away_intel'].get('xg_against_per_match', 1.2)
        if home_xg_against >= 1.3 and away_xg_against >= 1.3:
            score += 25
            reasons.append(f"Both leak goals")
        elif home_xg_against >= 1.2 or away_xg_against >= 1.2:
            score += 15
            
        # 3. Both teams score regularly (0-20)
        home_xg_for = data['home_intel'].get('xg_for_per_match', 1.3)
        away_xg_for = data['away_intel'].get('xg_for_per_match', 1.3)
        if home_xg_for >= 1.2 and away_xg_for >= 1.2:
            score += 20
            reasons.append(f"Both attack well")
        elif home_xg_for >= 1.0 and away_xg_for >= 1.0:
            score += 10
            
        # 4. League Profile (0-25)
        league_btts = league_profile.get('btts_rate', 50)
        if league_btts >= 55:
            score += 25
            reasons.append(f"League BTTS: {league_btts}%")
        elif league_btts >= 50:
            score += 15
        elif league_btts < 48:
            score -= 10
            
        return {
            'market': 'btts',
            'score': score,
            'confidence': min(score, 100),
            'reasons': reasons,
            'bet': score >= 55
        }
    
    def evaluate_over35(self, match: dict, data: dict, league_profile: dict) -> dict:
        """Évalue Over 3.5 pour un match"""
        score = 0
        reasons = []
        
        # Over 3.5 = plus risqué, seuils plus élevés
        
        # 1. xG très élevé requis (0-35)
        home_xg = data['home_intel'].get('xg_for_per_match', 1.3)
        away_xg = data['away_intel'].get('xg_for_per_match', 1.3)
        expected_goals = home_xg + away_xg
        if expected_goals >= 3.5:
            score += 35
            reasons.append(f"High xG: {expected_goals:.1f}")
        elif expected_goals >= 3.0:
            score += 20
            reasons.append(f"Good xG: {expected_goals:.1f}")
        elif expected_goals >= 2.8:
            score += 10
            
        # 2. Tactical très offensif (0-30)
        tactical_prob = data['tactical'].get('over_25_probability', 50)
        if tactical_prob >= 70:
            score += 30
            reasons.append(f"Very attacking: {tactical_prob}%")
        elif tactical_prob >= 60:
            score += 15
            
        # 3. League Profile crucial (0-35)
        league_over35 = league_profile.get('over35_rate', 30)
        if league_over35 >= 40:
            score += 35
            reasons.append(f"High-scoring league: {league_over35}%")
        elif league_over35 >= 35:
            score += 20
        elif league_over35 < 30:
            score -= 20  # Forte pénalité
            reasons.append(f"Low-scoring league: {league_over35}%")
            
        return {
            'market': 'over_35',
            'score': score,
            'confidence': min(score, 100),
            'reasons': reasons,
            'bet': score >= 65  # Seuil plus élevé pour O3.5
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # BENCHMARK PAR LIGUE × MARCHÉ
    # ═══════════════════════════════════════════════════════════════════════════
    
    def run_benchmark_for_league(self, league: str) -> dict:
        """Execute le benchmark pour une ligue spécifique"""
        matches = self.matches_by_league.get(league, [])
        profile = LEAGUE_PROFILES.get(league, {
            "over25_rate": 50, "btts_rate": 50, "over35_rate": 30,
            "avg_goals": 2.5, "best_markets": [], "risk_level": "unknown"
        })
        
        results = {
            'over_25': {'bets': 0, 'wins': 0, 'stake': 0, 'profit': 0},
            'btts': {'bets': 0, 'wins': 0, 'stake': 0, 'profit': 0},
            'over_35': {'bets': 0, 'wins': 0, 'stake': 0, 'profit': 0}
        }
        
        for match in matches:
            # Récupérer données
            data = self.get_tactical_data(match['home_team'], match['away_team'])
            
            # Résultats réels
            total_goals = (match['score_home'] or 0) + (match['score_away'] or 0)
            both_scored = (match['score_home'] or 0) > 0 and (match['score_away'] or 0) > 0
            
            # Évaluer Over 2.5
            o25 = self.evaluate_over25(match, data, profile)
            if o25['bet']:
                results['over_25']['bets'] += 1
                results['over_25']['stake'] += 2.0
                if total_goals >= 3:
                    results['over_25']['wins'] += 1
                    results['over_25']['profit'] += 2.0 * 0.85  # Cote ~1.85
                else:
                    results['over_25']['profit'] -= 2.0
                    
            # Évaluer BTTS
            btts = self.evaluate_btts(match, data, profile)
            if btts['bet']:
                results['btts']['bets'] += 1
                results['btts']['stake'] += 2.0
                if both_scored:
                    results['btts']['wins'] += 1
                    results['btts']['profit'] += 2.0 * 0.80  # Cote ~1.80
                else:
                    results['btts']['profit'] -= 2.0
                    
            # Évaluer Over 3.5
            o35 = self.evaluate_over35(match, data, profile)
            if o35['bet']:
                results['over_35']['bets'] += 1
                results['over_35']['stake'] += 1.0  # Moins de stake sur O3.5
                if total_goals >= 4:
                    results['over_35']['wins'] += 1
                    results['over_35']['profit'] += 1.0 * 1.40  # Cote ~2.40
                else:
                    results['over_35']['profit'] -= 1.0
                    
        return results
    
    def run_full_benchmark(self):
        """Execute le benchmark complet"""
        print("\n" + "="*80)
        print("🎯 BENCHMARK INTELLIGENT PAR LIGUE × MARCHÉ")
        print("="*80)
        
        all_results = {}
        
        for league in self.matches_by_league.keys():
            print(f"\n⏳ Analyse {league}...")
            results = self.run_benchmark_for_league(league)
            all_results[league] = results
            
            # Afficher résumé par ligue
            for market, data in results.items():
                if data['bets'] > 0:
                    wr = (data['wins'] / data['bets']) * 100
                    roi = (data['profit'] / data['stake']) * 100 if data['stake'] > 0 else 0
                    print(f"   {market.upper()}: {data['bets']} paris | {wr:.1f}% WR | {roi:+.1f}% ROI | {data['profit']:+.1f}u")
                    
        return all_results
    
    def print_recommendations(self, results: dict):
        """Affiche les recommandations finales"""
        print("\n" + "="*80)
        print("🏆 RECOMMANDATIONS - MEILLEURES COMBINAISONS LIGUE × MARCHÉ")
        print("="*80)
        
        recommendations = []
        
        for league, markets in results.items():
            for market, data in markets.items():
                if data['bets'] >= 5:  # Minimum 5 paris pour être significatif
                    wr = (data['wins'] / data['bets']) * 100
                    roi = (data['profit'] / data['stake']) * 100 if data['stake'] > 0 else 0
                    recommendations.append({
                        'league': league,
                        'market': market,
                        'bets': data['bets'],
                        'wins': data['wins'],
                        'win_rate': wr,
                        'roi': roi,
                        'profit': data['profit']
                    })
        
        # Trier par ROI
        recommendations.sort(key=lambda x: x['roi'], reverse=True)
        
        print(f"\n{'Rang':<5} {'Ligue':<20} {'Marché':<12} {'Paris':<8} {'WR':<8} {'ROI':<10} {'P&L':<10}")
        print("-" * 85)
        
        for i, rec in enumerate(recommendations[:15], 1):
            emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "✅" if rec['roi'] > 0 else "❌"
            print(f"{emoji} #{i:<2} {rec['league']:<20} {rec['market'].upper():<12} {rec['bets']:<8} {rec['win_rate']:.1f}%{'':<3} {rec['roi']:+.1f}%{'':<4} {rec['profit']:+.1f}u")
        
        # Stratégie finale recommandée
        print("\n" + "="*80)
        print("📋 STRATÉGIE PERSONNALISÉE RECOMMANDÉE")
        print("="*80)
        
        profitable = [r for r in recommendations if r['roi'] > 10 and r['win_rate'] >= 50]
        
        if profitable:
            print("\n🎯 COMBINAISONS À UTILISER:")
            for rec in profitable:
                print(f"   ✅ {rec['league']} → {rec['market'].upper()} ({rec['win_rate']:.0f}% WR, {rec['roi']:+.0f}% ROI)")
        
        # Ligues/marchés à éviter
        to_avoid = [r for r in recommendations if r['roi'] < -10]
        if to_avoid:
            print("\n⚠️ COMBINAISONS À ÉVITER:")
            for rec in to_avoid[:5]:
                print(f"   ❌ {rec['league']} → {rec['market'].upper()} ({rec['win_rate']:.0f}% WR, {rec['roi']:+.0f}% ROI)")


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║            🎯 BENCHMARK INTELLIGENT - PAR LIGUE × MARCHÉ                      ║
║                                                                               ║
║  Objectif: Trouver la MEILLEURE stratégie pour chaque contexte               ║
║  Pas de solution unique - Stratégies PERSONNALISÉES!                         ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    benchmark = SmartBenchmark()
    benchmark.connect()
    benchmark.load_matches_by_league()
    
    results = benchmark.run_full_benchmark()
    benchmark.print_recommendations(results)
    
    # Sauvegarder
    with open('/home/Mon_ps/benchmarks/smart_benchmark_results.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'results': results
        }, f, indent=2, default=str)
    
    print("\n✅ Résultats sauvegardés dans /home/Mon_ps/benchmarks/smart_benchmark_results.json")


if __name__ == "__main__":
    main()
