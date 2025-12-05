#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║          🚀 STRATÉGIE HYBRIDE V13 + TEAM MARKET PROFILER                      ║
║                                                                               ║
║  Combine le meilleur des deux mondes:                                        ║
║  • V13 Multi-Strike: Sélectivité + Haut ROI (76.5% WR, +53.2% ROI)          ║
║  • Team Market Profiler: Volume + Bon profit (+739.4u)                       ║
║                                                                               ║
║  Règle: Si V13 dit BET → stake×1.5, sinon utiliser Team Profile              ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Dict, List, Optional
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
    'team_over_05': 1.15, 'team_over_15': 1.75,
    'team_clean_sheet': 2.50, 'team_fail_to_score': 3.00
}

# Seuils V13 (extraits de l'orchestrateur)
V13_ELITE_THRESHOLD = 33
V13_GOLD_THRESHOLD = 30
V13_SILVER_THRESHOLD = 27


class HybridBenchmark:
    """Benchmark Hybride V13 + Team Market Profiler"""
    
    def __init__(self):
        self.conn = None
        self.team_profiles = {}
        self.matches = []
        self.results = {
            'hybrid_conservative': {'bets': 0, 'wins': 0, 'stake': 0, 'profit': 0},
            'hybrid_aggressive': {'bets': 0, 'wins': 0, 'stake': 0, 'profit': 0},
            'hybrid_smart': {'bets': 0, 'wins': 0, 'stake': 0, 'profit': 0},
            'quant_only': {'bets': 0, 'wins': 0, 'stake': 0, 'profit': 0},
        }
        
    def connect(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connexion DB établie")
        
    def load_team_profiles(self):
        """Charge les profils ML"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT team_name, league, market_type, win_rate, roi, 
                       sample_size, is_best_market, is_avoid_market, confidence_score
                FROM team_market_profiles
                WHERE sample_size >= 8
            """)
            rows = cur.fetchall()
            
        for row in rows:
            team = row['team_name']
            market = row['market_type']
            if team not in self.team_profiles:
                self.team_profiles[team] = {}
            self.team_profiles[team][market] = row
            
        print(f"✅ {len(self.team_profiles)} équipes chargées")
        
    def load_matches(self):
        """Charge les matchs avec données tactiques"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    mr.match_id, mr.home_team, mr.away_team, 
                    mr.score_home, mr.score_away, mr.league,
                    mr.commence_time,
                    -- Home team intelligence
                    ti_h.home_over25_rate as home_o25,
                    ti_h.home_btts_rate as home_btts,
                    ti_h.goals_tendency as home_goals_tendency,
                    ti_h.btts_tendency as home_btts_tendency,
                    ti_h.current_style as home_style,
                    -- Away team intelligence  
                    ti_a.away_over25_rate as away_o25,
                    ti_a.away_btts_rate as away_btts,
                    ti_a.goals_tendency as away_goals_tendency,
                    ti_a.btts_tendency as away_btts_tendency,
                    ti_a.current_style as away_style,
                    -- Team class
                    tc_h.tier as home_tier,
                    tc_a.tier as away_tier,
                    -- Tactical matrix
                    tm.over_25_probability as tactical_o25,
                    tm.btts_probability as tactical_btts
                FROM match_results mr
                LEFT JOIN team_intelligence ti_h ON LOWER(ti_h.team_name) LIKE '%' || LOWER(SPLIT_PART(mr.home_team, ' FC', 1)) || '%'
                LEFT JOIN team_intelligence ti_a ON LOWER(ti_a.team_name) LIKE '%' || LOWER(SPLIT_PART(mr.away_team, ' FC', 1)) || '%'
                LEFT JOIN team_class tc_h ON LOWER(tc_h.team_name) LIKE '%' || LOWER(SPLIT_PART(mr.home_team, ' FC', 1)) || '%'
                LEFT JOIN team_class tc_a ON LOWER(tc_a.team_name) LIKE '%' || LOWER(SPLIT_PART(mr.away_team, ' FC', 1)) || '%'
                LEFT JOIN tactical_matrix tm ON tm.style_a = ti_h.current_style AND tm.style_b = ti_a.current_style
                WHERE mr.commence_time >= '2025-09-01' AND mr.is_finished = true
                ORDER BY mr.commence_time
            """)
            self.matches = cur.fetchall()
        print(f"✅ {len(self.matches)} matchs chargés avec données enrichies")
        
    def normalize_team(self, name: str) -> str:
        """Normalise le nom d'équipe"""
        mappings = {
            'FC Bayern München': 'Bayern Munich',
            'FC Barcelona': 'Barcelona',
            'Real Madrid CF': 'Real Madrid',
            'Liverpool FC': 'Liverpool',
            'Manchester City FC': 'Manchester City',
            'Paris Saint-Germain FC': 'Paris Saint Germain',
        }
        if name in mappings:
            return mappings[name]
        for suffix in [' FC', ' CF', ' SC', ' BC']:
            if name.endswith(suffix):
                return name[:-len(suffix)].strip()
        return name
        
    def get_profile(self, team: str) -> Optional[dict]:
        """Récupère le profil d'une équipe"""
        norm = self.normalize_team(team)
        if norm in self.team_profiles:
            return self.team_profiles[norm]
        for t in self.team_profiles:
            if t.lower() in team.lower() or team.lower() in t.lower():
                return self.team_profiles[t]
        return None

    def calculate_v13_score(self, match: dict) -> dict:
        """Simule le scoring V13 Multi-Strike"""
        score = 0
        markets = []
        
        # Layer 1: Tactical (0-8)
        tactical_o25 = float(match.get('tactical_o25') or 50)
        if tactical_o25 >= 65:
            score += 8
        elif tactical_o25 >= 55:
            score += 5
        elif tactical_o25 >= 50:
            score += 3
            
        # Layer 2: Team Class (0-6)
        # Tiers: S=0 (Super), A=1, B=2, C=3, D=4
        tier_map = {'S': 0, 'A': 1, 'B': 2, 'C': 3, 'D': 4}
        home_tier_raw = str(match.get('home_tier') or 'C')
        away_tier_raw = str(match.get('away_tier') or 'C')
        home_tier = tier_map.get(home_tier_raw, 3)
        away_tier = tier_map.get(away_tier_raw, 3)
        if home_tier <= 1 or away_tier <= 1:  # S ou A tier
            score += 6
        elif home_tier <= 2 and away_tier <= 2:  # B tier max
            score += 4
            
        # Layer 3: H2H / Style (0-5)
        home_style = match.get('home_style') or 'balanced'
        away_style = match.get('away_style') or 'balanced'
        offensive_styles = ['offensive', 'high_press', 'attacking']
        if home_style in offensive_styles or away_style in offensive_styles:
            score += 5
        elif home_style != 'defensive' and away_style != 'defensive':
            score += 3
            
        # Layer 4: Goals Tendency (0-6)
        home_goals = match.get('home_goals_tendency') or 50
        away_goals = match.get('away_goals_tendency') or 50
        avg_goals = (float(home_goals or 50) + float(away_goals or 50)) / 2
        if avg_goals >= 75:
            score += 6
        elif avg_goals >= 60:
            score += 4
            
        # Layer 5: Over25 rates (0-6)
        home_o25 = float(match.get('home_o25') or 50)
        away_o25 = float(match.get('away_o25') or 50)
        if home_o25 >= 60 and away_o25 >= 60:
            score += 6
        elif home_o25 >= 50 or away_o25 >= 50:
            score += 3
            
        # Layer 6: BTTS (0-5)
        home_btts = float(match.get('home_btts') or 50)
        away_btts = float(match.get('away_btts') or 50)
        btts_avg = (home_btts + away_btts) / 2
        if btts_avg >= 60:
            score += 5
            markets.append('btts_yes')
        elif btts_avg >= 50:
            score += 3
            
        # Layer 7: Convergence (0-4)
        if tactical_o25 >= 55 and home_o25 >= 55 and away_o25 >= 55:
            score += 4
            markets.append('over_25')
            
        # Determine markets
        if not markets:
            if score >= 25:
                markets = ['over_25']
                
        return {
            'score': score,
            'zone': 'ELITE' if score >= V13_ELITE_THRESHOLD else 'GOLD' if score >= V13_GOLD_THRESHOLD else 'SILVER' if score >= V13_SILVER_THRESHOLD else 'SKIP',
            'markets': markets
        }
        
    def get_best_team_market(self, team: str) -> Optional[dict]:
        """Trouve le meilleur marché pour une équipe"""
        profile = self.get_profile(team)
        if not profile:
            return None
            
        best = None
        for market, data in profile.items():
            if data.get('is_best_market') and float(data.get('roi', 0) or 0) >= 20:
                if best is None or float(data.get('roi', 0)) > float(best.get('roi', 0)):
                    best = data
        return best
        
    def evaluate_result(self, match: dict, market: str, team: str = None) -> bool:
        """Évalue si un pari est gagnant"""
        home = match['score_home'] or 0
        away = match['score_away'] or 0
        total = home + away
        both = home > 0 and away > 0
        
        is_home = team and self.normalize_team(match['home_team']) == self.normalize_team(team)
        team_goals = home if is_home else away
        team_conceded = away if is_home else home
        
        results = {
            'over_15': total >= 2, 'over_25': total >= 3, 'over_35': total >= 4,
            'under_15': total < 2, 'under_25': total < 3, 'under_35': total < 4,
            'btts_yes': both, 'btts_no': not both,
            'team_over_05': team_goals >= 1, 'team_over_15': team_goals >= 2,
            'team_clean_sheet': team_conceded == 0
        }
        return results.get(market, False)

    def run_benchmark(self):
        """Execute le benchmark hybride"""
        print("\n" + "="*80)
        print("🚀 BENCHMARK HYBRIDE V13 + TEAM MARKET PROFILER")
        print("="*80)
        
        for match in self.matches:
            v13 = self.calculate_v13_score(match)
            
            # ═══════════════════════════════════════════════════════════════════
            # STRATÉGIE HYBRID CONSERVATIVE
            # Si V13 ELITE/GOLD → stake×2, sinon Team Profile avec stake×1
            # ═══════════════════════════════════════════════════════════════════
            if v13['zone'] in ['ELITE', 'GOLD']:
                for market in v13['markets'][:1]:
                    stake = 3.0 if v13['zone'] == 'ELITE' else 2.0
                    won = self.evaluate_result(match, market)
                    odds = MARKET_ODDS.get(market, 1.85)
                    
                    self.results['hybrid_conservative']['bets'] += 1
                    self.results['hybrid_conservative']['stake'] += stake
                    if won:
                        self.results['hybrid_conservative']['wins'] += 1
                        self.results['hybrid_conservative']['profit'] += stake * (odds - 1)
                    else:
                        self.results['hybrid_conservative']['profit'] -= stake
            else:
                # Fallback sur Team Profile
                for team in [match['home_team'], match['away_team']]:
                    best = self.get_best_team_market(team)
                    if best and float(best.get('roi', 0) or 0) >= 30:
                        market = best['market_type']
                        stake = 1.5
                        won = self.evaluate_result(match, market, team)
                        odds = MARKET_ODDS.get(market, 1.85)
                        
                        self.results['hybrid_conservative']['bets'] += 1
                        self.results['hybrid_conservative']['stake'] += stake
                        if won:
                            self.results['hybrid_conservative']['wins'] += 1
                            self.results['hybrid_conservative']['profit'] += stake * (odds - 1)
                        else:
                            self.results['hybrid_conservative']['profit'] -= stake
                        break

            # ═══════════════════════════════════════════════════════════════════
            # STRATÉGIE HYBRID AGGRESSIVE
            # V13 ELITE/GOLD/SILVER → stake variable + Team Profile toujours
            # ═══════════════════════════════════════════════════════════════════
            if v13['zone'] != 'SKIP':
                for market in v13['markets'][:1]:
                    stake = 3.0 if v13['zone'] == 'ELITE' else 2.5 if v13['zone'] == 'GOLD' else 1.5
                    won = self.evaluate_result(match, market)
                    odds = MARKET_ODDS.get(market, 1.85)
                    
                    self.results['hybrid_aggressive']['bets'] += 1
                    self.results['hybrid_aggressive']['stake'] += stake
                    if won:
                        self.results['hybrid_aggressive']['wins'] += 1
                        self.results['hybrid_aggressive']['profit'] += stake * (odds - 1)
                    else:
                        self.results['hybrid_aggressive']['profit'] -= stake
                        
            # Toujours ajouter Team Profile
            for team in [match['home_team'], match['away_team']]:
                best = self.get_best_team_market(team)
                if best and float(best.get('roi', 0) or 0) >= 25:
                    market = best['market_type']
                    stake = 1.0
                    won = self.evaluate_result(match, market, team)
                    odds = MARKET_ODDS.get(market, 1.85)
                    
                    self.results['hybrid_aggressive']['bets'] += 1
                    self.results['hybrid_aggressive']['stake'] += stake
                    if won:
                        self.results['hybrid_aggressive']['wins'] += 1
                        self.results['hybrid_aggressive']['profit'] += stake * (odds - 1)
                    else:
                        self.results['hybrid_aggressive']['profit'] -= stake

            # ═══════════════════════════════════════════════════════════════════
            # STRATÉGIE HYBRID SMART
            # V13 + Team Profile UNIQUEMENT si les deux convergent
            # ═══════════════════════════════════════════════════════════════════
            if v13['zone'] in ['ELITE', 'GOLD']:
                # Vérifier convergence avec Team Profile
                converge = False
                for team in [match['home_team'], match['away_team']]:
                    profile = self.get_profile(team)
                    if profile:
                        for v13_market in v13['markets']:
                            if v13_market in profile:
                                p = profile[v13_market]
                                if float(p.get('roi', 0) or 0) >= 20 and float(p.get('win_rate', 0) or 0) >= 60:
                                    converge = True
                                    break
                                    
                if converge:
                    for market in v13['markets'][:1]:
                        stake = 4.0 if v13['zone'] == 'ELITE' else 3.0
                        won = self.evaluate_result(match, market)
                        odds = MARKET_ODDS.get(market, 1.85)
                        
                        self.results['hybrid_smart']['bets'] += 1
                        self.results['hybrid_smart']['stake'] += stake
                        if won:
                            self.results['hybrid_smart']['wins'] += 1
                            self.results['hybrid_smart']['profit'] += stake * (odds - 1)
                        else:
                            self.results['hybrid_smart']['profit'] -= stake

            # ═══════════════════════════════════════════════════════════════════
            # QUANT ONLY (pour comparaison)
            # ═══════════════════════════════════════════════════════════════════
            for team in [match['home_team'], match['away_team']]:
                best = self.get_best_team_market(team)
                if best and float(best.get('roi', 0) or 0) >= 25 and float(best.get('win_rate', 0) or 0) >= 65:
                    market = best['market_type']
                    stake = 2.0
                    won = self.evaluate_result(match, market, team)
                    odds = MARKET_ODDS.get(market, 1.85)
                    
                    self.results['quant_only']['bets'] += 1
                    self.results['quant_only']['stake'] += stake
                    if won:
                        self.results['quant_only']['wins'] += 1
                        self.results['quant_only']['profit'] += stake * (odds - 1)
                    else:
                        self.results['quant_only']['profit'] -= stake
                    break
                    
        self.print_results()
        
    def print_results(self):
        """Affiche les résultats"""
        print("\n" + "="*80)
        print("📊 RÉSULTATS - STRATÉGIES HYBRIDES V13 + QUANT")
        print("="*80)
        
        print(f"\n{'Stratégie':<25} {'Paris':<8} {'Wins':<8} {'WR':<10} {'ROI':<12} {'P&L':<12}")
        print("-" * 80)
        
        # Ajouter références
        all_results = list(self.results.items())
        all_results.append(('V13_REFERENCE', {'bets': 204, 'wins': 156, 'stake': 396, 'profit': 210.7}))
        
        sorted_results = sorted(
            all_results,
            key=lambda x: x[1]['profit'],
            reverse=True
        )
        
        for i, (name, data) in enumerate(sorted_results):
            if data['bets'] == 0:
                continue
            wr = (data['wins'] / data['bets']) * 100
            roi = (data['profit'] / data['stake']) * 100 if data['stake'] > 0 else 0
            
            emoji = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "  "
            ref = " ⭐" if name == 'V13_REFERENCE' else ""
            
            print(f"{emoji} {name:<23}{ref} {data['bets']:<8} {data['wins']:<8} {wr:.1f}%{'':<5} {roi:+.1f}%{'':<6} {data['profit']:+.1f}u")
            
        print("\n" + "="*80)
        print("💡 CONCLUSION")
        print("="*80)
        
        best = sorted_results[0]
        print(f"\n🏆 Meilleure stratégie: {best[0]}")
        print(f"   P&L: {best[1]['profit']:+.1f}u")
        
        v13_profit = 210.7
        improvement = best[1]['profit'] - v13_profit
        if improvement > 0:
            print(f"   ✅ +{improvement:.1f}u de plus que V13!")
        else:
            print(f"   ⚠️ {improvement:.1f}u de moins que V13")


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║          🚀 BENCHMARK HYBRIDE V13 + TEAM MARKET PROFILER                      ║
║                                                                               ║
║  Stratégies testées:                                                         ║
║  1. HYBRID_CONSERVATIVE: V13 ELITE/GOLD prioritaire, Team Profile fallback   ║
║  2. HYBRID_AGGRESSIVE: V13 + Team Profile combinés (volume max)              ║
║  3. HYBRID_SMART: Seulement si V13 ET Team Profile convergent               ║
║  4. QUANT_ONLY: Team Profile seul (comparaison)                              ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    benchmark = HybridBenchmark()
    benchmark.connect()
    benchmark.load_team_profiles()
    benchmark.load_matches()
    benchmark.run_benchmark()
    
    # Sauvegarder
    with open('/home/Mon_ps/benchmarks/hybrid_benchmark_results.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'results': {k: {**v, 'wr': round((v['wins']/v['bets'])*100, 1) if v['bets'] > 0 else 0,
                           'roi': round((v['profit']/v['stake'])*100, 1) if v['stake'] > 0 else 0}
                       for k, v in benchmark.results.items()}
        }, f, indent=2)
    
    print("\n✅ Résultats sauvegardés")


if __name__ == "__main__":
    main()
