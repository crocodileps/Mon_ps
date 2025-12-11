"""
═══════════════════════════════════════════════════════════════════════════════
♟️ CHESS ENGINE V2.1 - ORCHESTRATOR COMPLET
   Attack DNA + Defense DNA + Referee DNA = Full Match Analysis
═══════════════════════════════════════════════════════════════════════════════
"""

import sys
sys.path.insert(0, '/home/Mon_ps')

from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Import des agents
from agents.attack_v1.data.loader import AttackDataLoader
from agents.attack_v1.features.engineer_v3_hedge_fund import AttackFeatureEngineerV3, AttackDNA
from agents.defense_v2.data.loader import DefenseDataLoader
from agents.defense_v2.team_profiler import TeamProfiler as DefenseProfiler
from agents.chess_engine_v2.referee_integration import RefereeIntegration, GoalDistribution


@dataclass
class BettingSignal:
    market: str
    prediction: str
    probability: float
    edge_pct: float
    confidence: str  # HIGH, MEDIUM, LOW
    source: str      # ATTACK, DEFENSE, REFEREE, COMBINED
    reasoning: str


@dataclass
class MatchAnalysis:
    """Analyse complète d'un match - Hedge Fund Grade"""
    home_team: str
    away_team: str
    referee: str
    league: str
    
    # DNA Fingerprints
    home_attack_fingerprint: str = ""
    away_attack_fingerprint: str = ""
    home_defense_profile: str = ""
    away_defense_profile: str = ""
    referee_profile: str = ""
    
    # Core Predictions
    expected_home_goals: float = 0.0
    expected_away_goals: float = 0.0
    expected_total: float = 0.0
    over_25_prob: float = 50.0
    btts_prob: float = 50.0
    
    # Signals
    signals: List[BettingSignal] = field(default_factory=list)
    avoid_markets: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Best Bets
    primary_bet: Optional[BettingSignal] = None
    secondary_bet: Optional[BettingSignal] = None


class ChessEngineV2:
    """
    Chess Engine V2.1 - Orchestrateur Complet
    Combine Attack + Defense + Referee pour analyse Hedge Fund Grade
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        
        if verbose:
            print("="*80)
            print("♟️ CHESS ENGINE V2.1 - INITIALISATION")
            print("="*80)
        
        # Attack Agent
        if verbose: print("\n🔴 Loading Attack Agent...")
        self.attack_loader = AttackDataLoader()
        self.attack_loader.load_all()
        self.attack_engineer = AttackFeatureEngineerV3(self.attack_loader)
        self.attack_engineer.engineer_all()
        
        # Defense Agent
        if verbose: print("\n🔵 Loading Defense Agent...")
        self.defense_loader = DefenseDataLoader()
        self.defense_loader.load_all()
        self.defense_profiler = DefenseProfiler(self.defense_loader)
        
        # Referee Agent
        if verbose: print("\n🟡 Loading Referee Agent...")
        self.referee_integration = RefereeIntegration()
        
        if verbose:
            print("\n✅ Chess Engine V2.1 Ready!")
            print(f"   • {len(self.attack_engineer.dna_cache)} teams (Attack)")
            print(f"   • {len(self.defense_loader.get_all_teams())} teams (Defense)")
            print(f"   • {len(self.referee_integration.referees)} referees")
    
    def analyze(self, home_team: str, away_team: str, referee: str = None) -> MatchAnalysis:
        """
        Analyse complète d'un match
        
        Args:
            home_team: Équipe à domicile
            away_team: Équipe à l'extérieur
            referee: Nom de l'arbitre (optionnel)
        """
        analysis = MatchAnalysis(
            home_team=home_team,
            away_team=away_team,
            referee=referee or "Unknown",
            league=""
        )
        
        signals = []
        
        # ═══════════════════════════════════════════════════════════════
        # 1. ATTACK DNA
        # ═══════════════════════════════════════════════════════════════
        home_attack = self.attack_engineer.get_dna(home_team)
        away_attack = self.attack_engineer.get_dna(away_team)
        
        if home_attack:
            analysis.home_attack_fingerprint = home_attack.fingerprint_hash
            analysis.league = home_attack.league
            analysis.expected_home_goals = home_attack.xg_90
            
            # Add attack edges
            for edge in home_attack.edges:
                signals.append(BettingSignal(
                    market=f"{home_team}: {edge.market}",
                    prediction=edge.market,
                    probability=70.0 if edge.confidence == "HIGH" else 55.0,
                    edge_pct=edge.edge_pct,
                    confidence=edge.confidence,
                    source="ATTACK",
                    reasoning=edge.reasoning
                ))
        
        if away_attack:
            analysis.away_attack_fingerprint = away_attack.fingerprint_hash
            analysis.expected_away_goals = away_attack.xg_90 * 0.90  # Away penalty
            
            for edge in away_attack.edges:
                signals.append(BettingSignal(
                    market=f"{away_team}: {edge.market}",
                    prediction=edge.market,
                    probability=65.0 if edge.confidence == "HIGH" else 50.0,
                    edge_pct=edge.edge_pct * 0.9,
                    confidence=edge.confidence,
                    source="ATTACK",
                    reasoning=edge.reasoning
                ))
        
        # ═══════════════════════════════════════════════════════════════
        # 2. DEFENSE DNA
        # ═══════════════════════════════════════════════════════════════
        home_defense = self.defense_profiler.profile_team(home_team)
        away_defense = self.defense_profiler.profile_team(away_team)
        
        if home_defense:
            analysis.home_defense_profile = home_defense.defensive_profile.value if home_defense.defensive_profile else "UNKNOWN"
            
            # Adjust away goals based on home defense PROFILE
            profile = analysis.home_defense_profile
            if profile == "FORTRESS":
                analysis.expected_away_goals *= 0.80  # -20%
            elif profile == "SOLID":
                analysis.expected_away_goals *= 0.90  # -10%
            elif profile == "LEAKY":
                analysis.expected_away_goals *= 1.15  # +15%
        if away_defense:
            analysis.away_defense_profile = away_defense.defensive_profile.value if away_defense.defensive_profile else "UNKNOWN"
            
            # Adjust home goals based on away defense PROFILE
            profile = analysis.away_defense_profile
            if profile == "FORTRESS":
                analysis.expected_home_goals *= 0.80  # -20%
            elif profile == "SOLID":
                analysis.expected_home_goals *= 0.90  # -10%
            elif profile == "LEAKY":
                analysis.expected_home_goals *= 1.15  # +15%
        # Calculate totals
        analysis.expected_total = round(analysis.expected_home_goals + analysis.expected_away_goals, 2)
        
        # Base probabilities
        analysis.over_25_prob = min(95, max(15, 50 + (analysis.expected_total - 2.5) * 15))
        
        # BTTS probability
        if home_attack and away_attack:
            if home_attack.xg_90 >= 1.5 and away_attack.xg_90 >= 1.3:
                analysis.btts_prob = 70.0
            else:
                analysis.btts_prob = 50.0
            
            # Adjust for defense leaks
            if home_defense and home_defense.xga_90 >= 1.5:
                analysis.btts_prob += 10
            if away_defense and away_defense.xga_90 >= 1.5:
                analysis.btts_prob += 10
        
        # ═══════════════════════════════════════════════════════════════
        # 3. REFEREE ADJUSTMENTS
        # ═══════════════════════════════════════════════════════════════
        if referee:
            ref_adj = self.referee_integration.apply_to_prediction(
                base_over_25_prob=analysis.over_25_prob,
                base_btts_prob=analysis.btts_prob,
                referee_name=referee,
                home_team=home_team,
                away_team=away_team
            )
            
            # Get referee profile
            ref_data = self.referee_integration.get_adjustment(referee)
            if ref_data:
                analysis.referee_profile = f"{ref_data.card_profile.value}_{ref_data.goal_distribution.value}"
                
                # Handle bimodal distribution
                if ref_data.goal_distribution == GoalDistribution.BIMODAL:
                    if "Over/Under 2.5" not in analysis.avoid_markets:
                        analysis.avoid_markets.append("Over/Under 2.5")
                    # Warning already added via ref_adj
                else:
                    analysis.over_25_prob = ref_adj['over_25_prob']
            
            # Add referee edges
            for edge in ref_adj.get('referee_edges', []):
                signals.append(BettingSignal(
                    market=edge['market'],
                    prediction=edge.get('prediction', edge['market']),
                    probability=65.0,
                    edge_pct=edge['edge_pct'],
                    confidence="MEDIUM",
                    source="REFEREE",
                    reasoning=edge['reasoning']
                ))
            
            # Deduplicate
            for m in ref_adj.get('avoid_markets', []):
                if m not in analysis.avoid_markets:
                    analysis.avoid_markets.append(m)
            for w in ref_adj.get('warnings', []):
                if w not in analysis.warnings:
                    analysis.warnings.append(w)
        
        # ═══════════════════════════════════════════════════════════════
        # 4. COMBINED SIGNALS
        # ═══════════════════════════════════════════════════════════════
        
        # Over 2.5 signal (if not avoided)
        if "Over/Under 2.5" not in analysis.avoid_markets:
            if analysis.over_25_prob >= 65:
                signals.append(BettingSignal(
                    market="Over 2.5 Goals",
                    prediction="OVER",
                    probability=analysis.over_25_prob,
                    edge_pct=(analysis.over_25_prob - 50) * 0.3,
                    confidence="HIGH" if analysis.over_25_prob >= 75 else "MEDIUM",
                    source="COMBINED",
                    reasoning=f"xG Total: {analysis.expected_total}"
                ))
            elif analysis.over_25_prob <= 35:
                signals.append(BettingSignal(
                    market="Under 2.5 Goals",
                    prediction="UNDER",
                    probability=100 - analysis.over_25_prob,
                    edge_pct=(50 - analysis.over_25_prob) * 0.3,
                    confidence="HIGH" if analysis.over_25_prob <= 25 else "MEDIUM",
                    source="COMBINED",
                    reasoning=f"xG Total: {analysis.expected_total}"
                ))
        
        # BTTS signal
        if analysis.btts_prob >= 65:
            signals.append(BettingSignal(
                market="BTTS",
                prediction="YES",
                probability=analysis.btts_prob,
                edge_pct=(analysis.btts_prob - 50) * 0.25,
                confidence="HIGH" if analysis.btts_prob >= 75 else "MEDIUM",
                source="COMBINED",
                reasoning="Both teams have scoring capability"
            ))
        
        # ═══════════════════════════════════════════════════════════════
        # 5. RANK & SELECT BEST BETS
        # ═══════════════════════════════════════════════════════════════
        
        # Filter out avoided markets
        valid_signals = [s for s in signals if s.market not in analysis.avoid_markets]
        
        # Sort by expected value (probability * edge)
        valid_signals.sort(key=lambda s: s.probability * s.edge_pct / 100, reverse=True)
        
        analysis.signals = valid_signals
        
        if valid_signals:
            analysis.primary_bet = valid_signals[0]
            if len(valid_signals) > 1:
                analysis.secondary_bet = valid_signals[1]
        
        return analysis
    
    def print_analysis(self, analysis: MatchAnalysis) -> None:
        """Affiche l'analyse formatée"""
        print("\n" + "═"*80)
        print(f"⚽ {analysis.home_team} vs {analysis.away_team}")
        print(f"   🏆 {analysis.league} | 🎯 Referee: {analysis.referee}")
        print("═"*80)
        
        # DNA Summary
        print("\n📊 DNA PROFILES")
        print(f"   🏠 {analysis.home_team}:")
        print(f"      Attack: {analysis.home_attack_fingerprint or 'N/A'}")
        print(f"      Defense: {analysis.home_defense_profile or 'N/A'}")
        print(f"   ✈️ {analysis.away_team}:")
        print(f"      Attack: {analysis.away_attack_fingerprint or 'N/A'}")
        print(f"      Defense: {analysis.away_defense_profile or 'N/A'}")
        if analysis.referee_profile:
            print(f"   🎯 Referee: {analysis.referee_profile}")
        
        # Predictions
        print(f"\n📈 EXPECTED GOALS")
        print(f"   {analysis.home_team}: {analysis.expected_home_goals:.2f}")
        print(f"   {analysis.away_team}: {analysis.expected_away_goals:.2f}")
        print(f"   Total: {analysis.expected_total:.2f}")
        print(f"   Over 2.5: {analysis.over_25_prob:.0f}% | BTTS: {analysis.btts_prob:.0f}%")
        
        # Warnings
        if analysis.warnings:
            print(f"\n⚠️ WARNINGS")
            for w in analysis.warnings:
                print(f"   • {w}")
        
        if analysis.avoid_markets:
            print(f"\n🚫 AVOID MARKETS: {analysis.avoid_markets}")
        
        # Signals
        print(f"\n🎯 BETTING SIGNALS (ranked by EV)")
        for i, s in enumerate(analysis.signals[:7], 1):
            emoji = "🟢" if s.confidence == "HIGH" else "🟡" if s.confidence == "MEDIUM" else "🔴"
            ev = s.probability * s.edge_pct / 100
            print(f"   {i}. {emoji} {s.market}")
            print(f"      {s.probability:.0f}% prob | {s.edge_pct:.1f}% edge | EV: {ev:.1f}")
            print(f"      Source: {s.source} | {s.reasoning}")
        
        # Best Bets
        if analysis.primary_bet:
            print(f"\n⭐ PRIMARY BET: {analysis.primary_bet.market}")
            print(f"   {analysis.primary_bet.probability:.0f}% @ {analysis.primary_bet.edge_pct:.1f}% edge")
        
        if analysis.secondary_bet:
            print(f"⭐ SECONDARY: {analysis.secondary_bet.market}")


# Test
if __name__ == "__main__":
    engine = ChessEngineV2()
    
    # Test matchups with referees
    matchups = [
        ("Liverpool", "Manchester City", "M Oliver"),
        ("Bayern Munich", "Barcelona", None),
        ("Arsenal", "Chelsea", "A Taylor"),
        ("Real Madrid", "Paris Saint Germain", "J Moss"),
    ]
    
    for home, away, ref in matchups:
        analysis = engine.analyze(home, away, ref)
        engine.print_analysis(analysis)
