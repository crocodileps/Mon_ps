#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║            🧠 BENCHMARK QUANT SCIENTIFIQUE - TEAM MARKET PROFILER             ║
║                                                                               ║
║  Utilise les profils ML existants (team_market_profiles) pour:               ║
║  • Identifier le MEILLEUR marché par équipe                                  ║
║  • Éviter les marchés TOXIQUES (is_avoid_market)                             ║
║  • Backtester sur 712 matchs réels                                           ║
║                                                                               ║
║  Approche SCIENTIFIQUE: Data-driven, pas de bidouillage                      ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json
from collections import defaultdict

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

# Cotes moyennes par marché (réalistes)
MARKET_ODDS = {
    'over_15': 1.30,
    'over_25': 1.85,
    'over_35': 2.40,
    'under_15': 3.50,
    'under_25': 2.00,
    'under_35': 1.55,
    'btts_yes': 1.80,
    'btts_no': 2.00,
    'team_over_05': 1.15,
    'team_over_15': 1.75,
    'team_clean_sheet': 2.50,
    'team_fail_to_score': 3.00
}


class TeamMarketProfile:
    """Profil marché d'une équipe"""
    def __init__(self, data: dict):
        self.team_name = data.get('team_name', '')
        self.league = data.get('league', '')
        self.market_type = data.get('market_type', '')
        self.win_rate = float(data.get('win_rate', 0) or 0)
        self.roi = float(data.get('roi', 0) or 0)
        self.sample_size = int(data.get('sample_size', 0) or 0)
        self.is_best_market = data.get('is_best_market', False)
        self.is_avoid_market = data.get('is_avoid_market', False)
        self.confidence_score = float(data.get('confidence_score', 0) or 0)


class QuantBenchmark:
    """Benchmark Quant Scientifique"""
    
    def __init__(self):
        self.conn = None
        self.team_profiles: Dict[str, Dict[str, TeamMarketProfile]] = {}  # team -> market -> profile
        self.matches = []
        self.results = {
            'strategy_best_market': {'bets': 0, 'wins': 0, 'stake': 0, 'profit': 0, 'details': []},
            'strategy_avoid_traps': {'bets': 0, 'wins': 0, 'stake': 0, 'profit': 0, 'details': []},
            'strategy_high_confidence': {'bets': 0, 'wins': 0, 'stake': 0, 'profit': 0, 'details': []},
            'strategy_combined': {'bets': 0, 'wins': 0, 'stake': 0, 'profit': 0, 'details': []},
            'baseline_over25_all': {'bets': 0, 'wins': 0, 'stake': 0, 'profit': 0, 'details': []},
        }
        
    def connect(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connexion DB établie")
        
    def load_team_profiles(self):
        """Charge tous les profils ML des équipes"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT team_name, league, market_type, win_rate, roi, 
                       sample_size, is_best_market, is_avoid_market, confidence_score
                FROM team_market_profiles
                WHERE sample_size >= 8
                ORDER BY team_name, market_type
            """)
            rows = cur.fetchall()
            
        for row in rows:
            team = row['team_name']
            market = row['market_type']
            
            if team not in self.team_profiles:
                self.team_profiles[team] = {}
            
            self.team_profiles[team][market] = TeamMarketProfile(row)
            
        print(f"✅ {len(self.team_profiles)} équipes avec profils ML chargées")
        
        # Stats
        best_markets = sum(1 for t in self.team_profiles.values() 
                         for p in t.values() if p.is_best_market)
        avoid_markets = sum(1 for t in self.team_profiles.values() 
                          for p in t.values() if p.is_avoid_market)
        print(f"   📊 {best_markets} best_markets identifiés")
        print(f"   ⚠️ {avoid_markets} avoid_markets identifiés")
        
    def load_matches(self):
        """Charge les matchs pour backtest"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT match_id, home_team, away_team, 
                       score_home, score_away, outcome,
                       commence_time, league
                FROM match_results 
                WHERE commence_time >= '2025-09-01' 
                AND is_finished = true
                ORDER BY commence_time
            """)
            self.matches = cur.fetchall()
        print(f"✅ {len(self.matches)} matchs chargés pour backtest")
        
    def normalize_team_name(self, name: str) -> str:
        """Normalise le nom d'équipe pour matching"""
        # Mappings courants
        mappings = {
            'FC Bayern München': 'Bayern Munich',
            'FC Barcelona': 'Barcelona',
            'Real Madrid CF': 'Real Madrid',
            'Atlético de Madrid': 'Atletico Madrid',
            'Liverpool FC': 'Liverpool',
            'Manchester City FC': 'Manchester City',
            'Manchester United FC': 'Manchester United',
            'Arsenal FC': 'Arsenal',
            'Chelsea FC': 'Chelsea',
            'Tottenham Hotspur FC': 'Tottenham',
            'Newcastle United FC': 'Newcastle United',
            'Brighton & Hove Albion FC': 'Brighton',
            'Brentford FC': 'Brentford',
            'West Ham United FC': 'West Ham',
            'Aston Villa FC': 'Aston Villa',
            'Paris Saint-Germain FC': 'Paris Saint Germain',
            'Olympique de Marseille': 'Marseille',
            'Olympique Lyonnais': 'Lyon',
            'AS Monaco FC': 'Monaco',
            'SSC Napoli': 'Napoli',
            'Juventus FC': 'Juventus',
            'AC Milan': 'Milan',
            'Inter Milan': 'Inter',
            'SS Lazio': 'Lazio',
            'AS Roma': 'Roma',
            'Atalanta BC': 'Atalanta',
            'Borussia Dortmund': 'Borussia Dortmund',
            'RB Leipzig': 'RB Leipzig',
            'Bayer 04 Leverkusen': 'Bayer Leverkusen',
        }
        
        # Essayer mapping direct
        if name in mappings:
            return mappings[name]
        
        # Essayer sans suffixes courants
        for suffix in [' FC', ' CF', ' SC', ' BC', ' AFC']:
            if name.endswith(suffix):
                clean = name[:-len(suffix)]
                if clean in [t for t in self.team_profiles.keys()]:
                    return clean
                    
        return name
        
    def get_team_profile(self, team_name: str) -> Optional[Dict[str, TeamMarketProfile]]:
        """Récupère le profil d'une équipe"""
        # Essai direct
        if team_name in self.team_profiles:
            return self.team_profiles[team_name]
        
        # Essai normalisé
        normalized = self.normalize_team_name(team_name)
        if normalized in self.team_profiles:
            return self.team_profiles[normalized]
        
        # Recherche partielle
        for profile_team in self.team_profiles.keys():
            if profile_team.lower() in team_name.lower() or team_name.lower() in profile_team.lower():
                return self.team_profiles[profile_team]
                
        return None
    
    def evaluate_match_result(self, match: dict, market: str, team: str = None) -> bool:
        """Évalue si un pari sur un marché est gagnant"""
        home_score = match['score_home'] or 0
        away_score = match['score_away'] or 0
        total_goals = home_score + away_score
        both_scored = home_score > 0 and away_score > 0
        
        # Déterminer si c'est home ou away pour les marchés team_*
        is_home = team and self.normalize_team_name(match['home_team']) == self.normalize_team_name(team)
        team_goals = home_score if is_home else away_score
        team_conceded = away_score if is_home else home_score
        
        market_results = {
            'over_15': total_goals >= 2,
            'over_25': total_goals >= 3,
            'over_35': total_goals >= 4,
            'under_15': total_goals < 2,
            'under_25': total_goals < 3,
            'under_35': total_goals < 4,
            'btts_yes': both_scored,
            'btts_no': not both_scored,
            'team_over_05': team_goals >= 1,
            'team_over_15': team_goals >= 2,
            'team_clean_sheet': team_conceded == 0,
            'team_fail_to_score': team_goals == 0,
        }
        
        return market_results.get(market, False)

    # ═══════════════════════════════════════════════════════════════════════════
    # STRATÉGIE 1: BEST MARKET - Parier le meilleur marché de chaque équipe
    # ═══════════════════════════════════════════════════════════════════════════
    def strategy_best_market(self, match: dict) -> List[dict]:
        """Parie uniquement sur le best_market de chaque équipe"""
        bets = []
        
        for team_name in [match['home_team'], match['away_team']]:
            profile = self.get_team_profile(team_name)
            if not profile:
                continue
                
            # Trouver le best_market
            for market, mp in profile.items():
                if mp.is_best_market and mp.sample_size >= 10 and mp.roi >= 20:
                    odds = MARKET_ODDS.get(market, 1.85)
                    stake = 2.0 if mp.roi >= 40 else 1.5
                    
                    bets.append({
                        'team': team_name,
                        'market': market,
                        'odds': odds,
                        'stake': stake,
                        'expected_wr': mp.win_rate,
                        'expected_roi': mp.roi,
                        'reason': f"Best market: {mp.win_rate:.0f}% WR, {mp.roi:+.0f}% ROI"
                    })
                    break  # Un seul bet par équipe
                    
        return bets

    # ═══════════════════════════════════════════════════════════════════════════
    # STRATÉGIE 2: AVOID TRAPS - Parier Over 2.5 sauf si c'est un trap
    # ═══════════════════════════════════════════════════════════════════════════
    def strategy_avoid_traps(self, match: dict) -> List[dict]:
        """Over 2.5 par défaut, mais évite les équipes marquées is_avoid"""
        bets = []
        
        # Vérifier si Over 2.5 est un trap pour une des équipes
        is_trap = False
        for team_name in [match['home_team'], match['away_team']]:
            profile = self.get_team_profile(team_name)
            if profile and 'over_25' in profile:
                if profile['over_25'].is_avoid_market:
                    is_trap = True
                    break
        
        if not is_trap:
            # Vérifier ROI positif pour au moins une équipe
            has_positive = False
            for team_name in [match['home_team'], match['away_team']]:
                profile = self.get_team_profile(team_name)
                if profile and 'over_25' in profile:
                    if profile['over_25'].roi > 0:
                        has_positive = True
                        break
            
            if has_positive:
                bets.append({
                    'team': 'match',
                    'market': 'over_25',
                    'odds': 1.85,
                    'stake': 2.0,
                    'reason': "Over 2.5 - No trap detected"
                })
                
        return bets

    # ═══════════════════════════════════════════════════════════════════════════
    # STRATÉGIE 3: HIGH CONFIDENCE - Seulement si confidence_score élevé
    # ═══════════════════════════════════════════════════════════════════════════
    def strategy_high_confidence(self, match: dict) -> List[dict]:
        """Parie uniquement sur les profils haute confiance"""
        bets = []
        
        for team_name in [match['home_team'], match['away_team']]:
            profile = self.get_team_profile(team_name)
            if not profile:
                continue
                
            # Trouver le marché avec la plus haute confiance ET ROI positif
            best_conf = None
            best_market = None
            
            for market, mp in profile.items():
                if mp.confidence_score >= 50 and mp.roi >= 25 and mp.win_rate >= 65:
                    if best_conf is None or mp.confidence_score > best_conf:
                        best_conf = mp.confidence_score
                        best_market = mp
                        
            if best_market:
                odds = MARKET_ODDS.get(best_market.market_type, 1.85)
                bets.append({
                    'team': team_name,
                    'market': best_market.market_type,
                    'odds': odds,
                    'stake': 2.0,
                    'expected_wr': best_market.win_rate,
                    'reason': f"High conf: {best_market.confidence_score:.0f}, {best_market.win_rate:.0f}% WR"
                })
                
        return bets

    # ═══════════════════════════════════════════════════════════════════════════
    # STRATÉGIE 4: COMBINED - Best Market + Avoid Traps + Confidence
    # ═══════════════════════════════════════════════════════════════════════════
    def strategy_combined(self, match: dict) -> List[dict]:
        """Combine les 3 stratégies avec scoring"""
        bets = []
        candidates = []
        
        for team_name in [match['home_team'], match['away_team']]:
            profile = self.get_team_profile(team_name)
            if not profile:
                continue
                
            for market, mp in profile.items():
                # Filtres de base
                if mp.is_avoid_market:
                    continue
                if mp.sample_size < 10:
                    continue
                if mp.roi < 15:
                    continue
                if mp.win_rate < 60:
                    continue
                    
                # Scoring
                score = 0
                
                # Best market bonus (+30)
                if mp.is_best_market:
                    score += 30
                    
                # ROI bonus (jusqu'à +40)
                score += min(mp.roi, 80) / 2
                
                # Win rate bonus (jusqu'à +20)
                score += (mp.win_rate - 50) / 2.5
                
                # Confidence bonus (jusqu'à +20)
                score += mp.confidence_score / 5
                
                # Sample size bonus (jusqu'à +10)
                score += min(mp.sample_size, 20) / 2
                
                candidates.append({
                    'team': team_name,
                    'market': market,
                    'profile': mp,
                    'score': score
                })
        
        # Trier par score et prendre les meilleurs
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        for c in candidates[:2]:  # Max 2 bets par match
            mp = c['profile']
            if c['score'] >= 50:  # Seuil minimum
                odds = MARKET_ODDS.get(c['market'], 1.85)
                stake = 3.0 if c['score'] >= 70 else 2.0
                
                bets.append({
                    'team': c['team'],
                    'market': c['market'],
                    'odds': odds,
                    'stake': stake,
                    'score': c['score'],
                    'expected_wr': mp.win_rate,
                    'expected_roi': mp.roi,
                    'reason': f"Combined score: {c['score']:.0f}"
                })
                
        return bets

    # ═══════════════════════════════════════════════════════════════════════════
    # BASELINE: Over 2.5 sur tous les matchs (pour comparaison)
    # ═══════════════════════════════════════════════════════════════════════════
    def strategy_baseline(self, match: dict) -> List[dict]:
        """Baseline: Over 2.5 sur tous les matchs"""
        return [{
            'team': 'match',
            'market': 'over_25',
            'odds': 1.85,
            'stake': 2.0,
            'reason': "Baseline Over 2.5"
        }]

    def run_backtest(self):
        """Execute le backtest complet"""
        print("\n" + "="*80)
        print("🧠 BENCHMARK QUANT SCIENTIFIQUE - TEAM MARKET PROFILER")
        print("="*80)
        
        strategies = {
            'strategy_best_market': self.strategy_best_market,
            'strategy_avoid_traps': self.strategy_avoid_traps,
            'strategy_high_confidence': self.strategy_high_confidence,
            'strategy_combined': self.strategy_combined,
            'baseline_over25_all': self.strategy_baseline,
        }
        
        for match in self.matches:
            for strat_name, strat_func in strategies.items():
                bets = strat_func(match)
                
                for bet in bets:
                    self.results[strat_name]['bets'] += 1
                    self.results[strat_name]['stake'] += bet['stake']
                    
                    # Évaluer résultat
                    team = bet['team'] if bet['team'] != 'match' else match['home_team']
                    won = self.evaluate_match_result(match, bet['market'], team)
                    
                    if won:
                        self.results[strat_name]['wins'] += 1
                        profit = bet['stake'] * (bet['odds'] - 1)
                    else:
                        profit = -bet['stake']
                        
                    self.results[strat_name]['profit'] += profit
                    
        # Afficher résultats
        self.print_results()
        
    def print_results(self):
        """Affiche les résultats du benchmark"""
        print("\n" + "="*80)
        print("📊 RÉSULTATS - BENCHMARK QUANT SCIENTIFIQUE")
        print("="*80)
        
        print(f"\n{'Stratégie':<30} {'Paris':<8} {'Wins':<8} {'WR':<10} {'ROI':<12} {'P&L':<12}")
        print("-" * 80)
        
        sorted_results = sorted(
            self.results.items(),
            key=lambda x: (x[1]['profit'] / x[1]['stake'] * 100) if x[1]['stake'] > 0 else -999,
            reverse=True
        )
        
        for i, (name, data) in enumerate(sorted_results):
            if data['bets'] == 0:
                continue
                
            wr = (data['wins'] / data['bets']) * 100
            roi = (data['profit'] / data['stake']) * 100 if data['stake'] > 0 else 0
            
            emoji = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "  "
            
            name_display = name.replace('strategy_', '').replace('baseline_', 'BASELINE: ')
            print(f"{emoji} {name_display:<28} {data['bets']:<8} {data['wins']:<8} {wr:.1f}%{'':<5} {roi:+.1f}%{'':<6} {data['profit']:+.1f}u")
        
        # Comparaison avec V13
        print("\n" + "="*80)
        print("📈 COMPARAISON AVEC V13 MULTI-STRIKE (Référence)")
        print("="*80)
        print("\n🎯 V13 Multi-Strike: 76.5% WR | +53.2% ROI | +210.7u")
        
        best_strat = sorted_results[0] if sorted_results else None
        if best_strat and best_strat[1]['bets'] > 0:
            data = best_strat[1]
            wr = (data['wins'] / data['bets']) * 100
            roi = (data['profit'] / data['stake']) * 100
            
            print(f"\n🏆 Meilleure stratégie Quant: {best_strat[0]}")
            print(f"   Win Rate: {wr:.1f}% (vs 76.5% V13)")
            print(f"   ROI: {roi:+.1f}% (vs +53.2% V13)")
            print(f"   P&L: {data['profit']:+.1f}u sur {data['bets']} paris")
            
            if roi > 53.2:
                print("\n   ✅ AMÉLIORATION par rapport à V13!")
            else:
                print("\n   ⚠️ V13 reste meilleur pour l'instant")


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║            🧠 BENCHMARK QUANT SCIENTIFIQUE - TEAM MARKET PROFILER             ║
║                                                                               ║
║  Stratégies testées:                                                         ║
║  1. BEST_MARKET: Parie le meilleur marché de chaque équipe                   ║
║  2. AVOID_TRAPS: Over 2.5 sauf si is_avoid_market                            ║
║  3. HIGH_CONFIDENCE: Seulement haute confiance (≥50) + ROI≥25%               ║
║  4. COMBINED: Scoring multi-facteurs (best_market + ROI + WR + conf)         ║
║  5. BASELINE: Over 2.5 sur tous les matchs (comparaison)                     ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    benchmark = QuantBenchmark()
    benchmark.connect()
    benchmark.load_team_profiles()
    benchmark.load_matches()
    benchmark.run_backtest()
    
    # Sauvegarder
    output = {
        'timestamp': datetime.now().isoformat(),
        'matches_tested': len(benchmark.matches),
        'teams_with_profiles': len(benchmark.team_profiles),
        'results': {
            name: {
                'bets': data['bets'],
                'wins': data['wins'],
                'win_rate': round((data['wins'] / data['bets']) * 100, 1) if data['bets'] > 0 else 0,
                'roi': round((data['profit'] / data['stake']) * 100, 1) if data['stake'] > 0 else 0,
                'profit': round(data['profit'], 1)
            }
            for name, data in benchmark.results.items()
        }
    }
    
    with open('/home/Mon_ps/benchmarks/quant_benchmark_results.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print("\n✅ Résultats sauvegardés dans /home/Mon_ps/benchmarks/quant_benchmark_results.json")


if __name__ == "__main__":
    main()
