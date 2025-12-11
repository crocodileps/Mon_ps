"""
═══════════════════════════════════════════════════════════════════════════════
♟️ CHESS ENGINE V2.0 - ORCHESTRATOR
   Combine Attack DNA + Defense DNA + Referee DNA pour prédictions match
═══════════════════════════════════════════════════════════════════════════════
"""

import sys
sys.path.insert(0, '/home/Mon_ps')

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

# Import des agents
from agents.attack_v1.data.loader import AttackDataLoader
from agents.attack_v1.features.engineer_v3_hedge_fund import AttackFeatureEngineerV3, AttackDNA
from agents.defense_v2.data.loader import DefenseDataLoader
from agents.defense_v2.team_profiler import TeamProfiler as DefenseProfiler


@dataclass
class BettingSignal:
    market: str
    prediction: str
    confidence: float  # 0-100
    edge_pct: float
    reasoning: List[str]


@dataclass
class MatchAnalysis:
    """Analyse complète d'un match"""
    home_team: str
    away_team: str
    league: str
    
    # DNA
    home_attack_dna: Optional[AttackDNA] = None
    away_attack_dna: Optional[AttackDNA] = None
    home_defense_dna: Optional[Dict] = None
    away_defense_dna: Optional[Dict] = None
    
    # Prédictions
    expected_goals_home: float = 0.0
    expected_goals_away: float = 0.0
    expected_total: float = 0.0
    
    # Signaux
    signals: List[BettingSignal] = field(default_factory=list)
    primary_edge: Optional[str] = None
    edge_confidence: float = 0.0


class ChessEngineOrchestrator:
    """Orchestrateur principal du Chess Engine V2.0"""
    
    def __init__(self):
        print("="*80)
        print("♟️ CHESS ENGINE V2.0 - INITIALISATION")
        print("="*80)
        
        # Attack Agent
        print("\n🔴 Chargement Attack Agent...")
        self.attack_loader = AttackDataLoader()
        self.attack_loader.load_all()
        self.attack_engineer = AttackFeatureEngineerV3(self.attack_loader)
        self.attack_engineer.engineer_all()
        
        # Defense Agent
        print("\n🔵 Chargement Defense Agent...")
        self.defense_loader = DefenseDataLoader()
        self.defense_loader.load_all()
        self.defense_profiler = DefenseProfiler(self.defense_loader)
        
        print("\n✅ Chess Engine V2.0 prêt!")
        print(f"   • {len(self.attack_engineer.dna_cache)} équipes Attack DNA")
        print(f"   • {len(self.defense_loader.get_all_teams())} équipes Defense DNA")
    
    def analyze_match(self, home_team: str, away_team: str) -> MatchAnalysis:
        """Analyse complète d'un match"""
        analysis = MatchAnalysis(home_team=home_team, away_team=away_team, league="")
        
        # 1. RÉCUPÉRATION DES DNA
        analysis.home_attack_dna = self.attack_engineer.get_dna(home_team)
        analysis.away_attack_dna = self.attack_engineer.get_dna(away_team)
        
        home_def = self.defense_profiler.profile_team(home_team)
        away_def = self.defense_profiler.profile_team(away_team)
        
        if home_def:
            analysis.home_defense_dna = {
                'profile': home_def.defensive_profile.value if home_def.defensive_profile else 'UNKNOWN',
                'xga_90': home_def.xga_90,
                'clean_sheet_pct': home_def.cs_pct
            }
        
        if away_def:
            analysis.away_defense_dna = {
                'profile': away_def.defensive_profile.value if away_def.defensive_profile else 'UNKNOWN',
                'xga_90': away_def.xga_90,
                'clean_sheet_pct': away_def.cs_pct
            }
        
        if analysis.home_attack_dna:
            analysis.league = analysis.home_attack_dna.league
        
        # 2. CALCUL DES EXPECTED GOALS
        home_xg = analysis.home_attack_dna.xg_90 if analysis.home_attack_dna else 1.3
        away_xg = analysis.away_attack_dna.xg_90 * 0.90 if analysis.away_attack_dna else 1.0
        
        # Ajustements défense
        if analysis.away_defense_dna:
            if analysis.away_defense_dna['xga_90'] >= 1.5:
                home_xg *= 1.15
            elif analysis.away_defense_dna['xga_90'] <= 0.8:
                home_xg *= 0.85
        
        if analysis.home_defense_dna:
            if analysis.home_defense_dna['xga_90'] >= 1.5:
                away_xg *= 1.15
            elif analysis.home_defense_dna['xga_90'] <= 0.8:
                away_xg *= 0.85
        
        analysis.expected_goals_home = round(home_xg, 2)
        analysis.expected_goals_away = round(away_xg, 2)
        analysis.expected_total = round(home_xg + away_xg, 2)
        
        # 3. GÉNÉRATION DES SIGNAUX
        signals = []
        
        # OVER/UNDER
        if analysis.expected_total >= 3.0:
            confidence = min(90, 50 + (analysis.expected_total - 2.5) * 20)
            signals.append(BettingSignal(
                market="Over 2.5", prediction="OVER", confidence=confidence, edge_pct=10.0,
                reasoning=[f"Expected total: {analysis.expected_total}"]
            ))
        elif analysis.expected_total <= 2.0:
            confidence = min(90, 50 + (2.5 - analysis.expected_total) * 20)
            signals.append(BettingSignal(
                market="Under 2.5", prediction="UNDER", confidence=confidence, edge_pct=8.0,
                reasoning=[f"Expected total: {analysis.expected_total}"]
            ))
        
        # BTTS
        btts_prob = 0.5
        if analysis.home_attack_dna and analysis.away_attack_dna:
            if analysis.home_attack_dna.xg_90 >= 1.5 and analysis.away_attack_dna.xg_90 >= 1.3:
                btts_prob = 0.70
            if analysis.home_defense_dna and analysis.home_defense_dna['xga_90'] >= 1.5:
                btts_prob += 0.10
            if analysis.away_defense_dna and analysis.away_defense_dna['xga_90'] >= 1.5:
                btts_prob += 0.10
        
        if btts_prob >= 0.65:
            signals.append(BettingSignal(
                market="BTTS", prediction="YES", confidence=btts_prob * 100, edge_pct=12.0,
                reasoning=["Both teams solid attack + weak defense detected"]
            ))
        
        # TIMING EDGES from DNA
        if analysis.home_attack_dna:
            for edge in analysis.home_attack_dna.edges:
                signals.append(BettingSignal(
                    market=f"{home_team}: {edge.market}", prediction=edge.market,
                    confidence=70.0 if edge.confidence == "HIGH" else 55.0,
                    edge_pct=edge.edge_pct, reasoning=[edge.reasoning]
                ))
        
        if analysis.away_attack_dna:
            for edge in analysis.away_attack_dna.edges:
                signals.append(BettingSignal(
                    market=f"{away_team}: {edge.market}", prediction=edge.market,
                    confidence=65.0 if edge.confidence == "HIGH" else 50.0,
                    edge_pct=edge.edge_pct * 0.9, reasoning=[edge.reasoning]
                ))
        
        analysis.signals = signals
        
        if signals:
            best = max(signals, key=lambda s: s.edge_pct * s.confidence / 100)
            analysis.primary_edge = best.market
            analysis.edge_confidence = best.confidence
        
        return analysis
    
    def print_analysis(self, analysis: MatchAnalysis) -> None:
        """Affiche l'analyse"""
        print("\n" + "="*80)
        print(f"⚽ {analysis.home_team} vs {analysis.away_team} ({analysis.league})")
        print("="*80)
        
        print("\n📊 DNA")
        if analysis.home_attack_dna:
            print(f"   🏠 {analysis.home_team}: {analysis.home_attack_dna.fingerprint_hash}")
            if analysis.home_defense_dna:
                print(f"      Defense: {analysis.home_defense_dna['profile']} (xGA: {analysis.home_defense_dna['xga_90']:.2f})")
        
        if analysis.away_attack_dna:
            print(f"   ✈️ {analysis.away_team}: {analysis.away_attack_dna.fingerprint_hash}")
            if analysis.away_defense_dna:
                print(f"      Defense: {analysis.away_defense_dna['profile']} (xGA: {analysis.away_defense_dna['xga_90']:.2f})")
        
        print(f"\n📈 EXPECTED: {analysis.home_team} {analysis.expected_goals_home} - {analysis.expected_goals_away} {analysis.away_team} (Total: {analysis.expected_total})")
        
        print("\n🎯 SIGNALS")
        for s in sorted(analysis.signals, key=lambda x: x.edge_pct * x.confidence, reverse=True)[:5]:
            emoji = "��" if s.confidence >= 70 else "🟡" if s.confidence >= 55 else "🔴"
            print(f"   {emoji} {s.market}: {s.confidence:.0f}% conf, {s.edge_pct:.1f}% edge")
        
        if analysis.primary_edge:
            print(f"\n⭐ PRIMARY: {analysis.primary_edge} ({analysis.edge_confidence:.0f}%)")


if __name__ == "__main__":
    engine = ChessEngineOrchestrator()
    
    for home, away in [("Liverpool", "Manchester City"), ("Bayern Munich", "Barcelona"), ("Real Madrid", "PSG")]:
        analysis = engine.analyze_match(home, away)
        engine.print_analysis(analysis)
