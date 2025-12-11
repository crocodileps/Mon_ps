"""
QUANTUM BRAIN V2.1 - Orchestrateur Principal
Intègre data_hub avec market_profiles
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_hub import DataHub
from engines.matchup_engine import MatchupEngine
from engines.chain_engine import ChainEngine
from engines.pattern_engine import PatternEngine
from engines.coach_engine import CoachEngine
from engines.referee_engine import RefereeEngine
from engines.variance_engine import VarianceEngine
from probability.bayesian_fusion import BayesianFusion
from probability.edge_calculator import EdgeCalculator
from execution.kelly_sizer import KellySizer
from execution.portfolio_guard import PortfolioGuard
from execution.signal_writer import SignalWriter


class QuantumBrain:
    """Cerveau quantique - Orchestre tous les moteurs d'analyse"""
    
    def __init__(self):
        print("="*70)
        print("🧠 QUANTUM BRAIN V2.0 - Initialisation")
        print("="*70)
        
        # Data Hub
        self.data_hub = DataHub()
        self.data_hub.load_all()
        
        # Engines
        self.matchup_engine = MatchupEngine()
        self.chain_engine = ChainEngine()
        self.pattern_engine = PatternEngine()
        self.coach_engine = CoachEngine()
        self.referee_engine = RefereeEngine()
        self.variance_engine = VarianceEngine()
        
        # Probability & Execution
        self.bayesian_fusion = BayesianFusion(data_hub=self.data_hub)
        self.edge_calculator = EdgeCalculator()
        self.kelly_sizer = KellySizer()
        self.portfolio_guard = PortfolioGuard()
        self.signal_writer = SignalWriter()
        
        print("\n✅ Quantum Brain pret")
    
    def analyze_match(
        self,
        home_team: str,
        away_team: str,
        league: str,
        kickoff: str,
        odds: Dict[str, Dict[str, float]],
        referee: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyse complète d'un match"""
        
        print(f"\n{'='*70}")
        print(f"⚽ ANALYSE: {home_team} vs {away_team}")
        print(f"   League: {league} | Kickoff: {kickoff}")
        print("="*70)
        
        # Récupérer les données
        home_data = self.data_hub.get_team_data(home_team)
        away_data = self.data_hub.get_team_data(away_team)
        referee_data = self.data_hub.get_referee_data(referee) if referee else None
        
        # Déterminer le tier
        home_profile = home_data.get("profile") or {}
        away_profile = away_data.get("profile") or {}
        tier = self._determine_tier(home_profile, away_profile)
        
        # Exécuter les engines
        engine_outputs = {}
        
        # Matchup Engine
        matchup_result = self.matchup_engine.analyze(home_data, away_data)
        engine_outputs["matchup"] = matchup_result
        print(f"   ✅ Matchup Engine: H:{matchup_result.get('home_attack_edge', 0):+.2f} A:{matchup_result.get('away_attack_edge', 0):+.2f}")
        
        # Chain Engine
        chain_result = self.chain_engine.analyze(home_data, away_data)
        engine_outputs["chain"] = chain_result
        print(f"   ✅ Chain Engine: OFF={chain_result.get('home_offensive', 0):.2f} vs DEF={chain_result.get('away_defensive', 0):.2f}")
        
        # Pattern Engine
        pattern_result = self.pattern_engine.analyze(home_data, away_data)
        engine_outputs["pattern"] = pattern_result
        print(f"   ✅ Pattern Engine: timing={pattern_result.get('total_pattern_edge', 0):.2f}")
        
        # Coach Engine
        coach_result = self.coach_engine.analyze(home_data, away_data)
        engine_outputs["coach"] = coach_result
        print(f"   ✅ Coach Engine: {coach_result.get('clash_type', 'N/A')}")
        
        # Referee Engine
        ref_result = self.referee_engine.analyze(referee_data) if referee_data else {}
        engine_outputs["referee"] = ref_result
        
        # Variance Engine
        variance_result = self.variance_engine.analyze(home_data, away_data)
        engine_outputs["variance"] = variance_result
        print(f"   ✅ Variance Engine: home={variance_result.get('home_profile', 'N/A')}, away={variance_result.get('away_profile', 'N/A')}")
        
        # Bayesian Fusion - AVEC data_hub pour market_profiles
        probabilities = self.bayesian_fusion.fuse(
            home_team=home_team,
            away_team=away_team,
            engine_outputs=engine_outputs,
            odds=odds,
            data_hub=self.data_hub
        )
        
        print(f"\n   📊 Probabilites fusionnees:")
        for market, probs in probabilities.items():
            print(f"      {market}: {probs}")
        
        # Edge Calculation
        edges = self.edge_calculator.calculate_all_edges(
            probabilities=probabilities,
            odds=odds,
            tier=tier
        )
        
        print(f"\n   💰 Edges detectes:")
        for market, edge_info in edges.items():
            if edge_info.get("has_edge"):
                print(f"      {market}: edge_net={edge_info['edge_net']:.3f}, selection={edge_info['selection']}")
        
        # Generate Signals
        signals = []
        for market, edge_info in edges.items():
            if edge_info.get("has_edge"):
                signal = self._create_signal(
                    home_team=home_team,
                    away_team=away_team,
                    league=league,
                    kickoff=kickoff,
                    market=market,
                    edge_info=edge_info,
                    odds=odds,
                    tier=tier,
                    probabilities=probabilities
                )
                signals.append(signal)
        
        # Portfolio Guard
        signals = self.portfolio_guard.filter_signals(signals)
        
        # Save Signals
        match_id = f"{home_team}_vs_{away_team}_{kickoff.split()[0]}"
        if signals:
            self.signal_writer.write(match_id, signals)
            print(f"\n   ✅ {len(signals)} signaux generes et sauvegardes")
        
        return {
            "match_id": match_id,
            "home_team": home_team,
            "away_team": away_team,
            "tier": tier,
            "engine_outputs": engine_outputs,
            "probabilities": probabilities,
            "edges": edges,
            "signals": signals,
            "signals_count": len(signals),
        }
    
    def _determine_tier(self, home_profile: Dict, away_profile: Dict) -> str:
        """Détermine le tier du match"""
        home_tier = home_profile.get("tier", "STANDARD")
        away_tier = away_profile.get("tier", "STANDARD")
        
        tier_order = ["ELITE", "GOLD", "SILVER", "STANDARD"]
        home_idx = tier_order.index(home_tier) if home_tier in tier_order else 3
        away_idx = tier_order.index(away_tier) if away_tier in tier_order else 3
        
        return tier_order[min(home_idx, away_idx)]
    
    def _create_signal(
        self,
        home_team: str,
        away_team: str,
        league: str,
        kickoff: str,
        market: str,
        edge_info: Dict,
        odds: Dict,
        tier: str,
        probabilities: Dict
    ) -> Dict[str, Any]:
        """Crée un signal de pari"""
        selection = edge_info["selection"]
        our_prob = edge_info["our_probability"]
        
        # Récupérer la cote
        if market == "1X2":
            odd = odds.get("1X2", {}).get(selection, 2.0)
        elif market == "over_25":
            odd = odds.get("over_25", {}).get(selection, 1.9)
        elif market == "btts":
            odd = odds.get("btts", {}).get(selection, 1.9)
        else:
            market_odds = odds.get(market, {})
            odd = market_odds.get(selection) or market_odds.get("yes", 2.0)
        
        # Kelly Sizing
        stake = self.kelly_sizer.calculate(
            edge=edge_info["edge_net"],
            odds=odd,
            confidence=our_prob,
            tier=tier
        )
        
        return {
            "match": f"{home_team} vs {away_team}",
            "league": league,
            "kickoff": kickoff,
            "market": market,
            "selection": selection,
            "odds": odd,
            "our_probability": our_prob,
            "implied_probability": edge_info["implied_probability"],
            "edge_brut": edge_info["edge_brut"],
            "edge_net": edge_info["edge_net"],
            "stake_pct": stake,
            "tier": tier,
            "timestamp": datetime.now().isoformat(),
        }
