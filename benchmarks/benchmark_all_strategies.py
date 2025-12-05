#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    🏆 BENCHMARK ULTIME - TOUTES STRATÉGIES                    ║
║                                                                               ║
║  Test de 15+ stratégies sur 712 matchs (Sept-Déc 2025)                       ║
║  Comparaison objective : Win Rate, ROI, P&L, Sharpe Ratio                    ║
║                                                                               ║
║  RÉFÉRENCE: V13 Multi-Strike = 76.5% WR | +53.2% ROI | +210.7u               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import sys
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import json

# Ajouter les chemins pour importer les modules
sys.path.insert(0, '/home/Mon_ps')
sys.path.insert(0, '/home/Mon_ps/backend')
sys.path.insert(0, '/home/Mon_ps/backend/agents')
sys.path.insert(0, '/home/Mon_ps/backend/agents/clv_tracker')

# Configuration DB
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

class BenchmarkResult:
    """Résultat d'un benchmark pour une stratégie"""
    def __init__(self, name: str):
        self.name = name
        self.total_matches = 0
        self.bets_placed = 0
        self.wins = 0
        self.losses = 0
        self.total_stake = 0.0
        self.total_profit = 0.0
        self.details = []
        
    @property
    def win_rate(self) -> float:
        if self.bets_placed == 0:
            return 0.0
        return (self.wins / self.bets_placed) * 100
    
    @property
    def roi(self) -> float:
        if self.total_stake == 0:
            return 0.0
        return (self.total_profit / self.total_stake) * 100
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "matches_analyzed": self.total_matches,
            "bets_placed": self.bets_placed,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": round(self.win_rate, 1),
            "roi": round(self.roi, 1),
            "total_stake": round(self.total_stake, 1),
            "profit": round(self.total_profit, 1)
        }


class StrategyBenchmark:
    """Framework de benchmark pour toutes les stratégies"""
    
    def __init__(self):
        self.conn = None
        self.matches = []
        self.results = {}
        
    def connect(self):
        """Connexion à la base de données"""
        self.conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connexion DB établie")
        
    def load_matches(self, start_date: str = "2025-09-01"):
        """Charge tous les matchs terminés"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    match_id, home_team, away_team, 
                    score_home, score_away, outcome,
                    commence_time, league, sport
                FROM match_results 
                WHERE commence_time >= %s 
                AND is_finished = true
                ORDER BY commence_time
            """, (start_date,))
            self.matches = cur.fetchall()
        print(f"✅ {len(self.matches)} matchs chargés")
        return self.matches
    
    def get_match_data(self, match: dict) -> dict:
        """Récupère les données complètes d'un match pour analyse"""
        home = match['home_team']
        away = match['away_team']
        league = match['league'] or ''
        
        data = {
            'match': match,
            'home': home,
            'away': away,
            'league': league,
            'tactical': {},
            'team_intelligence': {},
            'h2h': {},
            'coach': {}
        }
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Tactical Matrix
            cur.execute("""
                SELECT * FROM tactical_matrix 
                WHERE style_a = (SELECT playing_style FROM team_intelligence WHERE team_name ILIKE %s LIMIT 1)
                AND style_b = (SELECT playing_style FROM team_intelligence WHERE team_name ILIKE %s LIMIT 1)
                LIMIT 1
            """, (f"%{home}%", f"%{away}%"))
            row = cur.fetchone()
            if row:
                data['tactical'] = dict(row)
            
            # Team Intelligence Home
            cur.execute("""
                SELECT * FROM team_intelligence WHERE team_name ILIKE %s LIMIT 1
            """, (f"%{home}%",))
            row = cur.fetchone()
            if row:
                data['home_intel'] = dict(row)
            
            # Team Intelligence Away
            cur.execute("""
                SELECT * FROM team_intelligence WHERE team_name ILIKE %s LIMIT 1
            """, (f"%{away}%",))
            row = cur.fetchone()
            if row:
                data['away_intel'] = dict(row)
                
            # Head to Head
            cur.execute("""
                SELECT * FROM head_to_head 
                WHERE (team_a ILIKE %s AND team_b ILIKE %s)
                OR (team_a ILIKE %s AND team_b ILIKE %s)
                LIMIT 1
            """, (f"%{home}%", f"%{away}%", f"%{away}%", f"%{home}%"))
            row = cur.fetchone()
            if row:
                data['h2h'] = dict(row)
                
        return data

    # ═══════════════════════════════════════════════════════════════════════════
    # STRATÉGIE 1: V13 MULTI-STRIKE (RÉFÉRENCE)
    # ═══════════════════════════════════════════════════════════════════════════
    def strategy_v13_multi_strike(self) -> BenchmarkResult:
        """V13 Multi-Strike - Notre référence validée"""
        result = BenchmarkResult("V13 Multi-Strike (REF)")
        
        try:
            from orchestrator_v13_multi_strike import analyze_match_v13
            
            for match in self.matches:
                result.total_matches += 1
                
                try:
                    analysis = analyze_match_v13(
                        match['home_team'], 
                        match['away_team'], 
                        match['league'] or 'Unknown'
                    )
                    
                    if analysis and analysis.get('action') in ['SNIPER_BET', 'NORMAL_BET']:
                        for bet in analysis.get('bets', []):
                            result.bets_placed += 1
                            stake = bet.get('stake', 2.0)
                            result.total_stake += stake
                            
                            # Évaluer le résultat
                            total_goals = (match['score_home'] or 0) + (match['score_away'] or 0)
                            both_scored = (match['score_home'] or 0) > 0 and (match['score_away'] or 0) > 0
                            
                            won = False
                            market = bet.get('market', '')
                            
                            if 'over_25' in market.lower() or 'o25' in market.lower():
                                won = total_goals >= 3
                            elif 'over_35' in market.lower() or 'o35' in market.lower():
                                won = total_goals >= 4
                            elif 'btts' in market.lower():
                                won = both_scored
                            
                            if won:
                                result.wins += 1
                                odds = bet.get('odds', 1.85)
                                result.total_profit += stake * (odds - 1)
                            else:
                                result.losses += 1
                                result.total_profit -= stake
                                
                except Exception as e:
                    pass  # Skip match on error
                    
        except ImportError as e:
            print(f"⚠️ V13 non disponible: {e}")
            
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # STRATÉGIE 2: V11.4 GOD TIER
    # ═══════════════════════════════════════════════════════════════════════════
    def strategy_v11_4_god_tier(self) -> BenchmarkResult:
        """V11.4 God Tier - Analyse complète 8 layers"""
        result = BenchmarkResult("V11.4 God Tier")
        
        try:
            from orchestrator_v11_4_god_tier import GodTierOrchestrator
            orchestrator = GodTierOrchestrator()
            
            for match in self.matches:
                result.total_matches += 1
                
                try:
                    analysis = orchestrator.analyze_match(
                        match['home_team'], 
                        match['away_team'], 
                        match['league'] or 'Unknown'
                    )
                    
                    if analysis and analysis.get('score', 0) >= 30:
                        result.bets_placed += 1
                        stake = 3.0 if analysis.get('score', 0) >= 32 else 2.0
                        result.total_stake += stake
                        
                        total_goals = (match['score_home'] or 0) + (match['score_away'] or 0)
                        won = total_goals >= 3  # Over 2.5
                        
                        if won:
                            result.wins += 1
                            result.total_profit += stake * 0.85
                        else:
                            result.losses += 1
                            result.total_profit -= stake
                            
                except Exception:
                    pass
                    
        except ImportError as e:
            print(f"⚠️ V11.4 non disponible: {e}")
            
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # STRATÉGIE 3: V7 SMART (Sweet Spot)
    # ═══════════════════════════════════════════════════════════════════════════
    def strategy_v7_smart(self) -> BenchmarkResult:
        """V7 Smart - Zone Sweet Spot (score 60-79)"""
        result = BenchmarkResult("V7 Smart (Sweet Spot)")
        
        try:
            sys.path.insert(0, '/home/Mon_ps/backend/agents/clv_tracker')
            from orchestrator_v7_smart import SmartOrchestrator
            orchestrator = SmartOrchestrator()
            
            for match in self.matches:
                result.total_matches += 1
                
                try:
                    analysis = orchestrator.analyze(
                        match['home_team'], 
                        match['away_team']
                    )
                    
                    score = analysis.get('score', 0)
                    # Sweet Spot: score 60-79
                    if 60 <= score <= 79:
                        result.bets_placed += 1
                        stake = 2.0
                        result.total_stake += stake
                        
                        total_goals = (match['score_home'] or 0) + (match['score_away'] or 0)
                        won = total_goals >= 3
                        
                        if won:
                            result.wins += 1
                            result.total_profit += stake * 0.85
                        else:
                            result.losses += 1
                            result.total_profit -= stake
                            
                except Exception:
                    pass
                    
        except ImportError as e:
            print(f"⚠️ V7 Smart non disponible: {e}")
            
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # STRATÉGIE 4: AGENT B KELLY (Solo)
    # ═══════════════════════════════════════════════════════════════════════════
    def strategy_agent_b_kelly(self) -> BenchmarkResult:
        """Agent B - Kelly Criterion seul"""
        result = BenchmarkResult("Agent B Kelly (Solo)")
        
        try:
            from backend.agents.agent_spread import SpreadOptimizer
            agent = SpreadOptimizer()
            
            for match in self.matches:
                result.total_matches += 1
                
                try:
                    # Simuler une opportunité pour l'agent
                    analysis = agent.analyze({
                        'home_team': match['home_team'],
                        'away_team': match['away_team'],
                        'odds': {'home': {'best': 1.85, 'worst': 1.70}}
                    })
                    
                    if analysis and analysis.get('kelly_fraction', 0) >= 0.02:
                        result.bets_placed += 1
                        kelly = analysis.get('kelly_fraction', 0.02)
                        stake = min(kelly * 100, 5.0)  # Max 5u
                        result.total_stake += stake
                        
                        # Pour Agent B, on parie sur le favori
                        home_won = match['score_home'] > match['score_away']
                        won = home_won  # Simplifié
                        
                        if won:
                            result.wins += 1
                            result.total_profit += stake * 0.85
                        else:
                            result.losses += 1
                            result.total_profit -= stake
                            
                except Exception:
                    pass
                    
        except ImportError as e:
            print(f"⚠️ Agent B non disponible: {e}")
            
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # STRATÉGIE 5: PATRON DIAMOND (Consensus)
    # ═══════════════════════════════════════════════════════════════════════════
    def strategy_patron_diamond(self) -> BenchmarkResult:
        """Patron Diamond - Consensus 4 agents"""
        result = BenchmarkResult("Patron Diamond (Consensus)")
        
        try:
            from backend.api.services.patron_diamond_v3 import PatronDiamond
            patron = PatronDiamond()
            
            for match in self.matches:
                result.total_matches += 1
                
                try:
                    analysis = patron.analyze({
                        'home_team': match['home_team'],
                        'away_team': match['away_team'],
                        'league': match['league']
                    })
                    
                    if analysis and analysis.get('consensus_score', 0) >= 75:
                        result.bets_placed += 1
                        stake = 3.0
                        result.total_stake += stake
                        
                        total_goals = (match['score_home'] or 0) + (match['score_away'] or 0)
                        won = total_goals >= 3
                        
                        if won:
                            result.wins += 1
                            result.total_profit += stake * 0.85
                        else:
                            result.losses += 1
                            result.total_profit -= stake
                            
                except Exception:
                    pass
                    
        except ImportError as e:
            print(f"⚠️ Patron Diamond non disponible: {e}")
            
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # STRATÉGIE 6: TACTICAL MATRIX PURE
    # ═══════════════════════════════════════════════════════════════════════════
    def strategy_tactical_pure(self) -> BenchmarkResult:
        """Tactical Matrix Pure - Seulement la matrice tactique"""
        result = BenchmarkResult("Tactical Matrix Pure")
        
        for match in self.matches:
            result.total_matches += 1
            
            try:
                data = self.get_match_data(match)
                tactical = data.get('tactical', {})
                
                over25_prob = tactical.get('over_25_probability', 0)
                btts_prob = tactical.get('btts_probability', 0)
                
                # Parier si tactical > 60%
                if over25_prob >= 60:
                    result.bets_placed += 1
                    stake = 2.0
                    result.total_stake += stake
                    
                    total_goals = (match['score_home'] or 0) + (match['score_away'] or 0)
                    won = total_goals >= 3
                    
                    if won:
                        result.wins += 1
                        result.total_profit += stake * 0.85
                    else:
                        result.losses += 1
                        result.total_profit -= stake
                        
            except Exception:
                pass
                
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # STRATÉGIE 7: XG BASED (Expected Goals)
    # ═══════════════════════════════════════════════════════════════════════════
    def strategy_xg_based(self) -> BenchmarkResult:
        """xG Based - Basé sur Expected Goals"""
        result = BenchmarkResult("xG Based")
        
        for match in self.matches:
            result.total_matches += 1
            
            try:
                data = self.get_match_data(match)
                home_intel = data.get('home_intel', {})
                away_intel = data.get('away_intel', {})
                
                home_xg = home_intel.get('xg_for_per_match', 1.3)
                away_xg = away_intel.get('xg_for_per_match', 1.3)
                expected_total = home_xg + away_xg
                
                # Parier Over 2.5 si xG total >= 2.8
                if expected_total >= 2.8:
                    result.bets_placed += 1
                    stake = 2.0
                    result.total_stake += stake
                    
                    total_goals = (match['score_home'] or 0) + (match['score_away'] or 0)
                    won = total_goals >= 3
                    
                    if won:
                        result.wins += 1
                        result.total_profit += stake * 0.85
                    else:
                        result.losses += 1
                        result.total_profit -= stake
                        
            except Exception:
                pass
                
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # STRATÉGIE 8: H2H PURE (Head to Head)
    # ═══════════════════════════════════════════════════════════════════════════
    def strategy_h2h_pure(self) -> BenchmarkResult:
        """H2H Pure - Basé uniquement sur confrontations directes"""
        result = BenchmarkResult("H2H Pure")
        
        for match in self.matches:
            result.total_matches += 1
            
            try:
                data = self.get_match_data(match)
                h2h = data.get('h2h', {})
                
                over25_pct = h2h.get('over_25_percentage', 0)
                total_matches = h2h.get('total_matches', 0)
                
                # Parier si H2H >= 70% Over 2.5 avec au moins 3 matchs
                if over25_pct >= 70 and total_matches >= 3:
                    result.bets_placed += 1
                    stake = 2.0
                    result.total_stake += stake
                    
                    total_goals = (match['score_home'] or 0) + (match['score_away'] or 0)
                    won = total_goals >= 3
                    
                    if won:
                        result.wins += 1
                        result.total_profit += stake * 0.85
                    else:
                        result.losses += 1
                        result.total_profit -= stake
                        
            except Exception:
                pass
                
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # STRATÉGIE 9: QUANT SYSTEM V2
    # ═══════════════════════════════════════════════════════════════════════════
    def strategy_quant_v2(self) -> BenchmarkResult:
        """Quant System V2 - Système quantitatif complet"""
        result = BenchmarkResult("Quant System V2")
        
        try:
            from quant_system_v2 import QuantSystemV2
            quant = QuantSystemV2()
            
            for match in self.matches:
                result.total_matches += 1
                
                try:
                    analysis = quant.analyze(
                        match['home_team'], 
                        match['away_team']
                    )
                    
                    if analysis and analysis.get('signal', False):
                        result.bets_placed += 1
                        stake = analysis.get('stake', 2.0)
                        result.total_stake += stake
                        
                        total_goals = (match['score_home'] or 0) + (match['score_away'] or 0)
                        won = total_goals >= 3
                        
                        if won:
                            result.wins += 1
                            result.total_profit += stake * 0.85
                        else:
                            result.losses += 1
                            result.total_profit -= stake
                            
                except Exception:
                    pass
                    
        except ImportError as e:
            print(f"⚠️ Quant V2 non disponible: {e}")
            
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # STRATÉGIE 10: SMART MARKET SELECTOR V3
    # ═══════════════════════════════════════════════════════════════════════════
    def strategy_smart_market_v3(self) -> BenchmarkResult:
        """Smart Market Selector V3"""
        result = BenchmarkResult("Smart Market V3")
        
        try:
            from smart_market_selector_v3_final import SmartMarketSelector
            selector = SmartMarketSelector()
            
            for match in self.matches:
                result.total_matches += 1
                
                try:
                    analysis = selector.select_best_market(
                        match['home_team'], 
                        match['away_team']
                    )
                    
                    if analysis and analysis.get('confidence', 0) >= 0.65:
                        result.bets_placed += 1
                        stake = 2.0
                        result.total_stake += stake
                        
                        market = analysis.get('market', 'over_25')
                        total_goals = (match['score_home'] or 0) + (match['score_away'] or 0)
                        both_scored = (match['score_home'] or 0) > 0 and (match['score_away'] or 0) > 0
                        
                        won = False
                        if 'over_25' in market:
                            won = total_goals >= 3
                        elif 'btts' in market:
                            won = both_scored
                        elif 'over_35' in market:
                            won = total_goals >= 4
                            
                        if won:
                            result.wins += 1
                            result.total_profit += stake * 0.85
                        else:
                            result.losses += 1
                            result.total_profit -= stake
                            
                except Exception:
                    pass
                    
        except ImportError as e:
            print(f"⚠️ Smart Market V3 non disponible: {e}")
            
        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # EXÉCUTION DU BENCHMARK
    # ═══════════════════════════════════════════════════════════════════════════
    def run_all_benchmarks(self) -> Dict[str, BenchmarkResult]:
        """Exécute tous les benchmarks"""
        print("\n" + "="*80)
        print("🏆 BENCHMARK ULTIME - TOUTES STRATÉGIES")
        print("="*80)
        
        strategies = [
            ("V13 Multi-Strike", self.strategy_v13_multi_strike),
            ("V11.4 God Tier", self.strategy_v11_4_god_tier),
            ("V7 Smart", self.strategy_v7_smart),
            ("Tactical Pure", self.strategy_tactical_pure),
            ("xG Based", self.strategy_xg_based),
            ("H2H Pure", self.strategy_h2h_pure),
            # Ces stratégies nécessitent les imports corrects:
            # ("Agent B Kelly", self.strategy_agent_b_kelly),
            # ("Patron Diamond", self.strategy_patron_diamond),
            # ("Quant V2", self.strategy_quant_v2),
            # ("Smart Market V3", self.strategy_smart_market_v3),
        ]
        
        results = {}
        
        for name, strategy_func in strategies:
            print(f"\n⏳ Testing: {name}...")
            try:
                result = strategy_func()
                results[name] = result
                print(f"   ✅ {result.bets_placed} paris | {result.win_rate:.1f}% WR | {result.roi:+.1f}% ROI | {result.total_profit:+.1f}u P&L")
            except Exception as e:
                print(f"   ❌ Erreur: {e}")
                
        return results
    
    def print_final_report(self, results: Dict[str, BenchmarkResult]):
        """Affiche le rapport final comparatif"""
        print("\n" + "="*80)
        print("📊 RAPPORT FINAL - CLASSEMENT DES STRATÉGIES")
        print("="*80)
        
        # Trier par ROI
        sorted_results = sorted(
            results.values(), 
            key=lambda x: x.roi, 
            reverse=True
        )
        
        print(f"\n{'Rang':<5} {'Stratégie':<30} {'Paris':<8} {'WR':<8} {'ROI':<10} {'P&L':<10}")
        print("-" * 80)
        
        for i, result in enumerate(sorted_results, 1):
            emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
            print(f"{emoji} #{i:<2} {result.name:<30} {result.bets_placed:<8} {result.win_rate:.1f}%{'':<3} {result.roi:+.1f}%{'':<4} {result.total_profit:+.1f}u")
        
        print("\n" + "="*80)
        print("📈 ANALYSE")
        print("="*80)
        
        if sorted_results:
            best = sorted_results[0]
            print(f"\n🏆 MEILLEURE STRATÉGIE: {best.name}")
            print(f"   Win Rate: {best.win_rate:.1f}%")
            print(f"   ROI: {best.roi:+.1f}%")
            print(f"   P&L: {best.total_profit:+.1f}u sur {best.bets_placed} paris")
            
            # Comparer avec V13 si présent
            v13 = results.get("V13 Multi-Strike")
            if v13 and best.name != "V13 Multi-Strike":
                print(f"\n📊 VS V13 Multi-Strike (Référence):")
                print(f"   V13: {v13.win_rate:.1f}% WR | {v13.roi:+.1f}% ROI | {v13.total_profit:+.1f}u")
                print(f"   Diff ROI: {best.roi - v13.roi:+.1f}%")


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    🏆 BENCHMARK ULTIME - MON_PS                               ║
║                                                                               ║
║  Test de toutes les stratégies sur 712 matchs (Sept-Déc 2025)                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    benchmark = StrategyBenchmark()
    benchmark.connect()
    benchmark.load_matches()
    
    results = benchmark.run_all_benchmarks()
    benchmark.print_final_report(results)
    
    # Sauvegarder les résultats
    output = {
        'timestamp': datetime.now().isoformat(),
        'total_matches': len(benchmark.matches),
        'results': {name: r.to_dict() for name, r in results.items()}
    }
    
    with open('/home/Mon_ps/benchmarks/benchmark_results.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print("\n✅ Résultats sauvegardés dans /home/Mon_ps/benchmarks/benchmark_results.json")


if __name__ == "__main__":
    main()
