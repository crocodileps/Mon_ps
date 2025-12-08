"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                     QUANTUM BACKTESTER v2.0 - PAR ÉQUIPE                              ║
║                                                                                       ║
║  Méthodologie correcte:                                                               ║
║  - Pour CHAQUE équipe: récupérer TOUS ses matchs (dom + ext)                         ║
║  - Appliquer TOUS les scénarios à chaque match                                       ║
║  - Calculer WR, ROI, P&L pour CETTE équipe avec CHAQUE scénario                      ║
║  - Identifier LA MEILLEURE stratégie pour CETTE équipe                               ║
║  - Résultat: Matrice 99 équipes × N scénarios → 1 stratégie optimale par équipe      ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import logging
import json
import time
import asyncio

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════════════
# MATCH RESULT EVALUATOR
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class MatchResult:
    """Résultat d'un match pour évaluation"""
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    home_odds: float = 0.0
    draw_odds: float = 0.0
    away_odds: float = 0.0
    
    @property
    def total_goals(self) -> int:
        return self.home_goals + self.away_goals
    
    @property
    def btts(self) -> bool:
        return self.home_goals > 0 and self.away_goals > 0
    
    @property
    def over_25(self) -> bool:
        return self.total_goals > 2.5
    
    @property
    def over_35(self) -> bool:
        return self.total_goals > 3.5
    
    @property
    def under_25(self) -> bool:
        return self.total_goals < 2.5
    
    @property
    def outcome(self) -> str:
        if self.home_goals > self.away_goals:
            return 'home'
        elif self.away_goals > self.home_goals:
            return 'away'
        return 'draw'
    
    def evaluate_market(self, market: str) -> bool:
        """Évalue si un marché a gagné"""
        market_lower = market.lower()
        
        if market_lower in ['btts_yes', 'btts']:
            return self.btts
        elif market_lower == 'btts_no':
            return not self.btts
        elif market_lower in ['over_25', 'over_2.5']:
            return self.over_25
        elif market_lower in ['over_35', 'over_3.5']:
            return self.over_35
        elif market_lower in ['under_25', 'under_2.5']:
            return self.under_25
        elif market_lower == 'home':
            return self.outcome == 'home'
        elif market_lower == 'away':
            return self.outcome == 'away'
        elif market_lower == 'draw':
            return self.outcome == 'draw'
        elif market_lower in ['home_over_1.5', 'home_over_15']:
            return self.home_goals >= 2
        elif market_lower in ['away_over_1.5', 'away_over_15']:
            return self.away_goals >= 2
        elif market_lower in ['home_over_0.5']:
            return self.home_goals >= 1
        elif market_lower in ['away_over_0.5']:
            return self.away_goals >= 1
        
        return False


# ═══════════════════════════════════════════════════════════════════════════════════════
# TEAM STATS
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class TeamScenarioStats:
    """Stats d'un scénario pour une équipe"""
    bets: int = 0
    wins: int = 0
    staked: float = 0.0
    profit: float = 0.0
    
    @property
    def win_rate(self) -> float:
        return (self.wins / self.bets * 100) if self.bets > 0 else 0
    
    @property
    def roi(self) -> float:
        return (self.profit / self.staked * 100) if self.staked > 0 else 0


@dataclass
class TeamProfile:
    """Profil complet d'une équipe avec tous ses scénarios"""
    team_name: str
    tier: str = "UNKNOWN"
    style: str = "unknown"
    total_matches: int = 0
    
    # Stats par scénario: scenario_id -> TeamScenarioStats
    scenario_stats: Dict[str, TeamScenarioStats] = field(default_factory=dict)
    
    # Meilleure stratégie calculée
    best_scenario: str = ""
    best_pnl: float = 0.0
    best_wr: float = 0.0
    second_best: str = ""
    second_pnl: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════════════
# QUANTUM BACKTESTER v2.0 - PAR ÉQUIPE
# ═══════════════════════════════════════════════════════════════════════════════════════

class QuantumBacktesterV2:
    """
    Backtester scientifique - ANALYSE PAR ÉQUIPE
    """
    
    def __init__(self, db_config: Dict = None):
        self.db_config = db_config or {
            'host': 'localhost',
            'port': 5432,
            'database': 'monps_db',
            'user': 'monps_user',
            'password': 'monps_secure_password_2024'
        }
        self._conn = None
        
        # Profils par équipe: team_name -> TeamProfile
        self.team_profiles: Dict[str, TeamProfile] = {}
        
        # Mapping des noms
        self.name_mapping: Dict[str, str] = {}  # historical -> quantum
        self.reverse_mapping: Dict[str, str] = {}  # quantum -> historical
        
        # Import Rule Engine
        from quantum.services.rule_engine import QuantumRuleEngine, EngineConfig, MonteCarloConfig
        mc_config = MonteCarloConfig(enabled=False)
        config = EngineConfig(monte_carlo=mc_config)
        self.rule_engine = QuantumRuleEngine(config=config)
        
    def _get_conn(self):
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(**self.db_config)
        return self._conn
    
    def load_name_mappings(self):
        """Charge les mappings de noms"""
        conn = self._get_conn()
        cur = conn.cursor()
        cur.execute("SELECT quantum_name, historical_name FROM quantum.team_name_mapping")
        for row in cur.fetchall():
            self.reverse_mapping[row[0]] = row[1]  # quantum -> historical
            self.name_mapping[row[1].lower()] = row[0]  # historical -> quantum
        cur.close()
        
        # Ajouter les équipes sans mapping (nom identique)
        cur = conn.cursor()
        cur.execute("SELECT team_name, tier FROM quantum.team_profiles")
        for row in cur.fetchall():
            team_name = row[0]
            if team_name not in self.reverse_mapping:
                self.name_mapping[team_name.lower()] = team_name
            # Initialiser le profil
            self.team_profiles[team_name] = TeamProfile(
                team_name=team_name,
                tier=row[1] or "UNKNOWN"
            )
        cur.close()
    
    def get_quantum_name(self, historical_name: str) -> Optional[str]:
        """Convertit nom historique en nom Quantum"""
        # Chercher dans le mapping
        if historical_name.lower() in self.name_mapping:
            return self.name_mapping[historical_name.lower()]
        # Chercher directement
        if historical_name in self.team_profiles:
            return historical_name
        return None
    
    def load_team_matches(self, team_name: str, limit: int = None) -> List[Dict]:
        """Charge TOUS les matchs d'une équipe (dom + ext)"""
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Obtenir le nom historique
        hist_name = self.reverse_mapping.get(team_name, team_name)
        
        query = """
            SELECT 
                match_date::text as match_date,
                home_team, away_team,
                home_goals, away_goals,
                home_odds, draw_odds, away_odds,
                league, season
            FROM matches_results
            WHERE (LOWER(home_team) = LOWER(%s) OR LOWER(away_team) = LOWER(%s))
              AND home_goals IS NOT NULL
            ORDER BY match_date DESC
        """
        if limit:
            query += f" LIMIT {limit}"
        
        cur.execute(query, (hist_name, hist_name))
        matches = [dict(row) for row in cur.fetchall()]
        cur.close()
        
        return matches
    
    async def analyze_team(self, team_name: str, matches: List[Dict], verbose: bool = False):
        """Analyse tous les matchs d'une équipe et calcule les stats par scénario"""
        profile = self.team_profiles.get(team_name)
        if not profile:
            return
        
        profile.total_matches = len(matches)
        
        for match in matches:
            # Trouver les noms Quantum
            home_quantum = self.get_quantum_name(match['home_team'])
            away_quantum = self.get_quantum_name(match['away_team'])
            
            if not home_quantum or not away_quantum:
                continue
            
            # Créer le résultat du match
            result = MatchResult(
                home_team=match['home_team'],
                away_team=match['away_team'],
                home_goals=match['home_goals'],
                away_goals=match['away_goals'],
                home_odds=match.get('home_odds', 0) or 0,
                draw_odds=match.get('draw_odds', 0) or 0,
                away_odds=match.get('away_odds', 0) or 0
            )
            
            # Exécuter le Rule Engine
            try:
                strategy = await self.rule_engine.analyze_match(home_quantum, away_quantum)
            except Exception as e:
                continue
            
            if not strategy or not strategy.detected_scenarios:
                continue
            
            # Pour chaque scénario détecté
            for scenario in strategy.detected_scenarios:
                scenario_id = scenario.scenario_id.value if hasattr(scenario.scenario_id, 'value') else str(scenario.scenario_id)
                
                # Initialiser les stats si nécessaire
                if scenario_id not in profile.scenario_stats:
                    profile.scenario_stats[scenario_id] = TeamScenarioStats()
                
                stats = profile.scenario_stats[scenario_id]
                
                # Trouver les recommandations pour ce scénario
                for rec in strategy.recommendations:
                    # Vérifier si cette rec appartient à ce scénario
                    if hasattr(rec, 'scenarios_contributing') and rec.scenarios_contributing:
                        if scenario_id not in rec.scenarios_contributing:
                            continue
                    
                    market = rec.market.value if hasattr(rec.market, 'value') else str(rec.market)
                    odds = rec.odds if rec.odds > 1 else 2.0
                    stake = rec.stake_units if rec.stake_units > 0 else 1.0
                    
                    # Évaluer le pari
                    won = result.evaluate_market(market)
                    profit = (odds - 1) * stake if won else -stake
                    
                    stats.bets += 1
                    stats.staked += stake
                    stats.profit += profit
                    if won:
                        stats.wins += 1
    
    def calculate_best_strategies(self):
        """Calcule la meilleure stratégie pour chaque équipe"""
        for team_name, profile in self.team_profiles.items():
            if not profile.scenario_stats:
                continue
            
            # Trier par P&L
            sorted_scenarios = sorted(
                profile.scenario_stats.items(),
                key=lambda x: x[1].profit,
                reverse=True
            )
            
            if sorted_scenarios:
                best = sorted_scenarios[0]
                profile.best_scenario = best[0]
                profile.best_pnl = best[1].profit
                profile.best_wr = best[1].win_rate
                
                if len(sorted_scenarios) > 1:
                    second = sorted_scenarios[1]
                    profile.second_best = second[0]
                    profile.second_pnl = second[1].profit
    
    async def run_backtest(self, limit_per_team: int = None, verbose: bool = True):
        """Exécute le backtest complet pour toutes les équipes"""
        # Charger les mappings
        self.load_name_mappings()
        
        total_teams = len(self.team_profiles)
        start_time = time.time()
        
        if verbose:
            print(f"\n🔬 Analyse de {total_teams} équipes...")
        
        for i, team_name in enumerate(self.team_profiles.keys()):
            if verbose and i % 10 == 0:
                print(f"  [{i+1}/{total_teams}] {team_name}...")
            
            # Charger les matchs de l'équipe
            matches = self.load_team_matches(team_name, limit=limit_per_team)
            
            if matches:
                await self.analyze_team(team_name, matches, verbose=False)
        
        # Calculer les meilleures stratégies
        self.calculate_best_strategies()
        
        elapsed = time.time() - start_time
        if verbose:
            print(f"\n✅ Backtest terminé en {elapsed:.1f}s")
    
    def print_report(self):
        """Affiche le rapport PAR ÉQUIPE comme l'audit QUANT 2.0"""
        print("\n" + "=" * 120)
        print("🏆 QUANTUM BACKTESTER v2.0 - ANALYSE GRANULAIRE PAR ÉQUIPE")
        print("=" * 120)
        
        # Filtrer les équipes avec des données
        teams_with_data = [
            (name, profile) for name, profile in self.team_profiles.items()
            if profile.scenario_stats and profile.best_pnl != 0
        ]
        
        # Trier par P&L
        sorted_teams = sorted(teams_with_data, key=lambda x: x[1].best_pnl, reverse=True)
        
        print(f"\n✅ {len(sorted_teams)} équipes analysées avec données")
        
        # Calculer totaux
        total_pnl = sum(p.best_pnl for _, p in sorted_teams)
        positive_count = sum(1 for _, p in sorted_teams if p.best_pnl > 0)
        elite_count = sum(1 for _, p in sorted_teams if p.best_pnl >= 10)
        negative_count = sum(1 for _, p in sorted_teams if p.best_pnl < 0)
        
        print("\n" + "=" * 120)
        print(f"{'#':<4} {'Équipe':<25} {'Best Strategy':<22} {'Tier':<10} {'P':>4} {'W':>4} {'L':>4} {'WR':>6} {'P&L':>10} {'2nd Best':<20}")
        print("-" * 120)
        
        for i, (team_name, profile) in enumerate(sorted_teams[:50], 1):  # Top 50
            stats = profile.scenario_stats.get(profile.best_scenario, TeamScenarioStats())
            
            # Icône basée sur le P&L
            if profile.best_pnl >= 20:
                icon = "💎"
            elif profile.best_pnl >= 10:
                icon = "🏆"
            elif profile.best_pnl >= 5:
                icon = "✅"
            elif profile.best_pnl >= 0:
                icon = "🔸"
            else:
                icon = "❌"
            
            losses = stats.bets - stats.wins
            second_info = f"{profile.second_best}({profile.second_pnl:+.1f})" if profile.second_best else "-"
            
            print(f"{icon}{i:<3} {team_name:<25} {profile.best_scenario:<22} {profile.tier:<10} "
                  f"{stats.bets:>4} {stats.wins:>4} {losses:>4} {stats.win_rate:>5.0f}% "
                  f"{profile.best_pnl:>+9.1f}u {second_info:<20}")
        
        print("-" * 120)
        print(f"{'TOTAL':<56} {sum(p.scenario_stats.get(p.best_scenario, TeamScenarioStats()).bets for _, p in sorted_teams):>4} "
              f"{sum(p.scenario_stats.get(p.best_scenario, TeamScenarioStats()).wins for _, p in sorted_teams):>4} "
              f"     {total_pnl:>+9.1f}u")
        
        print(f"\n   📊 P&L > 0: {positive_count} | Élite (≥10u): {elite_count} | Négatif: {negative_count}")
        
        # Stats par scénario (combien d'équipes l'utilisent comme best)
        print("\n" + "=" * 80)
        print("📈 SCÉNARIOS LES PLUS PERFORMANTS (comme Best Strategy)")
        print("-" * 80)
        
        scenario_counts = defaultdict(lambda: {'count': 0, 'total_pnl': 0})
        for _, profile in sorted_teams:
            if profile.best_scenario:
                scenario_counts[profile.best_scenario]['count'] += 1
                scenario_counts[profile.best_scenario]['total_pnl'] += profile.best_pnl
        
        sorted_scenarios = sorted(scenario_counts.items(), key=lambda x: x[1]['total_pnl'], reverse=True)
        
        for scenario, data in sorted_scenarios[:15]:
            avg_pnl = data['total_pnl'] / data['count'] if data['count'] > 0 else 0
            print(f"   {scenario:<25} | {data['count']:>3} équipes | Total: {data['total_pnl']:>+8.1f}u | Avg: {avg_pnl:>+6.1f}u")
        
        print("\n" + "=" * 120)
    
    def close(self):
        if self._conn:
            self._conn.close()


# ═══════════════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════════════

async def main():
    logging.basicConfig(level=logging.WARNING)
    
    print("=" * 70)
    print("🔬 QUANTUM BACKTESTER v2.0 - PAR ÉQUIPE")
    print("=" * 70)
    
    backtester = QuantumBacktesterV2()
    
    await backtester.run_backtest(limit_per_team=50, verbose=True)
    backtester.print_report()
    backtester.close()


if __name__ == "__main__":
    asyncio.run(main())
