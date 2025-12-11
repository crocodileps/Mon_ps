"""
═══════════════════════════════════════════════════════════════════════════════
🎯 REFEREE PROFILER V1.0 - HEDGE FUND GRADE
   Analyse l'arbitre pour générer des edges sur Cards, Goals, Flow
═══════════════════════════════════════════════════════════════════════════════
"""

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class RefereeStyle(Enum):
    LAISSE_JOUER = "LAISSE_JOUER"      # Peu de fautes sifflées
    STRICT = "STRICT"                   # Beaucoup de cartons
    BALANCED = "BALANCED"               # Équilibré
    CARD_HAPPY = "CARD_HAPPY"           # Cartons faciles
    FLOW_KILLER = "FLOW_KILLER"         # Casse le rythme


class RefereeStrictness(Enum):
    LENIENT = "LENIENT"
    MODERATE = "MODERATE"
    STRICT = "STRICT"
    VERY_STRICT = "VERY_STRICT"


@dataclass
class RefereeBettingEdge:
    market: str
    prediction: str
    edge_pct: float
    confidence: str  # HIGH, MEDIUM, LOW
    reasoning: str


@dataclass 
class RefereeDNA:
    """DNA complet d'un arbitre"""
    name: str
    matches: int
    leagues: List[str]
    
    # Card Profile
    avg_cards: float
    avg_yellows: float
    avg_reds: float
    card_trigger_rate: float
    style: RefereeStyle
    strictness: RefereeStrictness
    
    # Goal Profile
    avg_goals: float
    over_35_pct: float
    over_45_pct: float
    under_25_pct: float
    
    # Flow Profile
    avg_fouls: float
    match_flow_score: float
    volatility: float
    second_half_intensity: float
    
    # Bias Profile
    home_bias: float
    home_profile: str
    big_team_bias: float
    
    # Team Interactions
    nemesis_teams: List[Dict]
    favored_teams: List[Dict]
    
    # Betting Edges
    edges: List[RefereeBettingEdge] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Fingerprint
    fingerprint: str = ""


class RefereeProfiler:
    """Profileur d'arbitres Hedge Fund Grade"""
    
    def __init__(self, data_path: str = "/home/Mon_ps/data/referee_dna_hedge_fund_v4.json"):
        self.data_path = data_path
        self.referees: Dict[str, RefereeDNA] = {}
        self._load_data()
    
    def _load_data(self) -> None:
        """Charge les données referee"""
        print("="*80)
        print("🎯 REFEREE PROFILER V1.0 - CHARGEMENT")
        print("="*80)
        
        with open(self.data_path, 'r') as f:
            raw_data = json.load(f)
        
        for ref in raw_data:
            dna = self._build_dna(ref)
            self.referees[dna.name] = dna
        
        print(f"✅ {len(self.referees)} arbitres chargés")
    
    def _build_dna(self, ref: Dict) -> RefereeDNA:
        """Construit le DNA d'un arbitre"""
        
        # Parse style
        style_str = ref.get('style', 'BALANCED')
        try:
            style = RefereeStyle(style_str)
        except ValueError:
            style = RefereeStyle.BALANCED
        
        # Parse strictness
        strict_str = ref.get('strictness', 'MODERATE')
        try:
            strictness = RefereeStrictness(strict_str)
        except ValueError:
            strictness = RefereeStrictness.MODERATE
        
        dna = RefereeDNA(
            name=ref['referee_name'],
            matches=ref.get('matches', 0),
            leagues=ref.get('leagues', []),
            avg_cards=ref.get('avg_cards', 0),
            avg_yellows=ref.get('avg_yellows', 0),
            avg_reds=ref.get('avg_reds', 0),
            card_trigger_rate=ref.get('card_trigger_rate', 0),
            style=style,
            strictness=strictness,
            avg_goals=ref.get('avg_goals', 0),
            over_35_pct=ref.get('over_35_pct', 0),
            over_45_pct=ref.get('over_45_pct', 0),
            under_25_pct=ref.get('under_25_pct', 0),
            avg_fouls=ref.get('avg_fouls', 0),
            match_flow_score=ref.get('match_flow_score', 0),
            volatility=ref.get('volatility', 0),
            second_half_intensity=ref.get('second_half_intensity', 0),
            home_bias=ref.get('home_bias', 0),
            home_profile=ref.get('home_profile', 'NEUTRE'),
            big_team_bias=ref.get('big_team_bias', 0),
            nemesis_teams=ref.get('nemesis_teams', []),
            favored_teams=ref.get('favored_teams', [])
        )
        
        # Generate edges and fingerprint
        dna.edges = self._generate_edges(dna)
        dna.warnings = self._generate_warnings(dna)
        dna.fingerprint = self._generate_fingerprint(dna)
        
        return dna
    
    def _generate_edges(self, dna: RefereeDNA) -> List[RefereeBettingEdge]:
        """Génère les betting edges basés sur le profil"""
        edges = []
        
        # === CARD EDGES ===
        if dna.avg_cards >= 4.0:
            edges.append(RefereeBettingEdge(
                market="Over 3.5 Cards",
                prediction="OVER",
                edge_pct=15.0,
                confidence="HIGH",
                reasoning=f"Avg {dna.avg_cards:.1f} cards/match"
            ))
        elif dna.avg_cards >= 3.5:
            edges.append(RefereeBettingEdge(
                market="Over 2.5 Cards",
                prediction="OVER",
                edge_pct=10.0,
                confidence="MEDIUM",
                reasoning=f"Avg {dna.avg_cards:.1f} cards/match"
            ))
        elif dna.avg_cards <= 2.5:
            edges.append(RefereeBettingEdge(
                market="Under 3.5 Cards",
                prediction="UNDER",
                edge_pct=12.0,
                confidence="HIGH",
                reasoning=f"Only {dna.avg_cards:.1f} cards/match avg"
            ))
        
        # === GOAL EDGES ===
        if dna.over_35_pct >= 45:
            edges.append(RefereeBettingEdge(
                market="Over 2.5 Goals",
                prediction="OVER",
                edge_pct=10.0,
                confidence="MEDIUM",
                reasoning=f"{dna.over_35_pct:.0f}% of matches Over 3.5"
            ))
        
        if dna.under_25_pct >= 45:
            edges.append(RefereeBettingEdge(
                market="Under 2.5 Goals",
                prediction="UNDER",
                edge_pct=10.0,
                confidence="MEDIUM",
                reasoning=f"{dna.under_25_pct:.0f}% of matches Under 2.5"
            ))
        
        # === FLOW EDGES ===
        if dna.style == RefereeStyle.LAISSE_JOUER:
            edges.append(RefereeBettingEdge(
                market="Match Flow",
                prediction="HIGH_TEMPO",
                edge_pct=8.0,
                confidence="MEDIUM",
                reasoning="Laisse jouer style = more open play"
            ))
        
        # === HOME BIAS EDGES ===
        if dna.home_bias >= 0.3:
            edges.append(RefereeBettingEdge(
                market="Home Team",
                prediction="ADVANTAGE",
                edge_pct=8.0,
                confidence="MEDIUM",
                reasoning=f"Home bias: {dna.home_bias:+.2f}"
            ))
        elif dna.home_bias <= -0.3:
            edges.append(RefereeBettingEdge(
                market="Away Team",
                prediction="FAIR_TREATMENT",
                edge_pct=5.0,
                confidence="LOW",
                reasoning=f"No home bias: {dna.home_bias:+.2f}"
            ))
        
        # === SECOND HALF INTENSITY ===
        if dna.second_half_intensity >= 1.3:
            edges.append(RefereeBettingEdge(
                market="2nd Half Cards",
                prediction="MORE",
                edge_pct=12.0,
                confidence="HIGH",
                reasoning=f"H2 intensity: {dna.second_half_intensity:.2f}x"
            ))
        
        return edges
    
    def _generate_warnings(self, dna: RefereeDNA) -> List[str]:
        """Génère les warnings"""
        warnings = []
        
        if dna.volatility >= 2.5:
            warnings.append(f"High volatility: {dna.volatility:.1f}")
        
        if dna.matches < 20:
            warnings.append(f"Small sample: {dna.matches} matches")
        
        if dna.avg_reds >= 0.2:
            warnings.append(f"Red card risk: {dna.avg_reds:.2f}/match")
        
        return warnings
    
    def _generate_fingerprint(self, dna: RefereeDNA) -> str:
        """Génère le fingerprint unique"""
        tags = []
        
        # Strictness
        tags.append(dna.strictness.value)
        
        # Style
        tags.append(dna.style.value)
        
        # Card profile
        if dna.avg_cards >= 4.0:
            tags.append("CARD_HEAVY")
        elif dna.avg_cards <= 2.5:
            tags.append("CARD_LIGHT")
        
        # Goal profile
        if dna.avg_goals >= 3.0:
            tags.append("HIGH_SCORING")
        elif dna.avg_goals <= 2.2:
            tags.append("LOW_SCORING")
        
        # Home bias
        if dna.home_bias >= 0.3:
            tags.append("HOME_BIAS")
        
        # Second half
        if dna.second_half_intensity >= 1.3:
            tags.append("H2_STRICT")
        
        return "_".join(tags)
    
    def get_referee(self, name: str) -> Optional[RefereeDNA]:
        """Récupère le DNA d'un arbitre"""
        return self.referees.get(name)
    
    def get_referee_for_teams(self, home: str, away: str) -> List[RefereeDNA]:
        """Trouve les arbitres qui ont officié ces équipes"""
        matches = []
        for ref in self.referees.values():
            # Check nemesis/favored teams
            team_refs = [t['team'] for t in ref.nemesis_teams + ref.favored_teams]
            if home in team_refs or away in team_refs:
                matches.append(ref)
        return matches
    
    def get_team_referee_edge(self, referee: RefereeDNA, team: str) -> Optional[RefereeBettingEdge]:
        """Vérifie si l'arbitre a un biais pour/contre une équipe"""
        
        # Check nemesis (défavorable)
        for nem in referee.nemesis_teams:
            if nem['team'] == team and nem['matches'] >= 5:
                return RefereeBettingEdge(
                    market=f"{team} Cards",
                    prediction="MORE",
                    edge_pct=nem['diff'] * 10,
                    confidence="HIGH" if nem['matches'] >= 10 else "MEDIUM",
                    reasoning=f"Nemesis: +{nem['diff']:.2f} cards vs avg ({nem['matches']} matches)"
                )
        
        # Check favored (favorable)
        for fav in referee.favored_teams:
            if fav['team'] == team and fav['matches'] >= 5:
                return RefereeBettingEdge(
                    market=f"{team} Cards",
                    prediction="LESS",
                    edge_pct=abs(fav['diff']) * 10,
                    confidence="HIGH" if fav['matches'] >= 10 else "MEDIUM",
                    reasoning=f"Favored: {fav['diff']:.2f} cards vs avg ({fav['matches']} matches)"
                )
        
        return None
    
    def print_dna(self, dna: RefereeDNA) -> None:
        """Affiche le DNA d'un arbitre"""
        print(f"\n🎯 {dna.name}")
        print(f"   Fingerprint: {dna.fingerprint}")
        print(f"   Matches: {dna.matches} | Leagues: {', '.join(dna.leagues)}")
        print(f"   Cards: {dna.avg_cards:.1f}/match | Goals: {dna.avg_goals:.1f}/match")
        print(f"   Style: {dna.style.value} | Strictness: {dna.strictness.value}")
        print(f"   Home Bias: {dna.home_bias:+.2f} | H2 Intensity: {dna.second_half_intensity:.2f}x")
        
        if dna.edges:
            print(f"   🎯 Edges: {[e.market for e in dna.edges]}")
        if dna.warnings:
            print(f"   ⚠️ Warnings: {dna.warnings}")


# Test
if __name__ == "__main__":
    profiler = RefereeProfiler()
    
    # Top arbitres
    print("\n" + "="*80)
    print("📊 TOP ARBITRES PAR STYLE")
    print("="*80)
    
    # Strict refs
    strict = [r for r in profiler.referees.values() if r.avg_cards >= 3.5]
    strict.sort(key=lambda x: x.avg_cards, reverse=True)
    print("\n🟨 CARD HEAVY (3.5+ cards/match):")
    for ref in strict[:5]:
        profiler.print_dna(ref)
    
    # Lenient refs
    lenient = [r for r in profiler.referees.values() if r.avg_cards <= 2.8]
    lenient.sort(key=lambda x: x.avg_cards)
    print("\n🟢 CARD LIGHT (≤2.8 cards/match):")
    for ref in lenient[:5]:
        profiler.print_dna(ref)
