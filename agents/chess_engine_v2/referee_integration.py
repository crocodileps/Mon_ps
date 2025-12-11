"""
═══════════════════════════════════════════════════════════════════════════════
🎯 REFEREE INTEGRATION - HEDGE FUND GRADE
   Ajustements intelligents basés sur l'arbitre
═══════════════════════════════════════════════════════════════════════════════
"""

import json
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum


class GoalDistribution(Enum):
    NORMAL = "NORMAL"           # Distribution normale
    BIMODAL = "BIMODAL"         # Soit Under soit Over, pas de milieu
    HIGH_SCORING = "HIGH_SCORING"
    LOW_SCORING = "LOW_SCORING"


class CardProfile(Enum):
    LENIENT = "LENIENT"         # < 2.8 cards/match
    MODERATE = "MODERATE"       # 2.8 - 3.5
    STRICT = "STRICT"           # 3.5 - 4.0
    CARD_HAPPY = "CARD_HAPPY"   # > 4.0


@dataclass
class RefereeAdjustment:
    """Ajustements à appliquer basés sur l'arbitre"""
    referee_name: str
    matches: int
    confidence: str  # HIGH (100+), MEDIUM (50-99), LOW (<50)
    
    # Goal adjustments
    goal_distribution: GoalDistribution
    avoid_25_line: bool
    over_25_adjustment: float  # +/- percentage points
    over_35_boost: float
    
    # Card adjustments
    card_profile: CardProfile
    cards_over_35_edge: float
    h2_cards_multiplier: float
    
    # Team-specific edges
    team_edges: Dict[str, float]  # team -> card differential
    
    # Warnings
    warnings: List[str]


class RefereeIntegration:
    """Intègre les données referee dans les prédictions"""
    
    def __init__(self, data_path: str = "/home/Mon_ps/data/referee_dna_hedge_fund_v4.json"):
        self.referees: Dict[str, Dict] = {}
        self._load_data(data_path)
        
        # Bimodal referees (pre-calculated)
        self.bimodal_refs = {'J Moss', 'A Madley', 'A Marriner', 'M Atkinson', 'K Friend'}
    
    def _load_data(self, path: str) -> None:
        with open(path, 'r') as f:
            data = json.load(f)
        
        for ref in data:
            self.referees[ref['referee_name']] = ref
        
        print(f"✅ Referee Integration: {len(self.referees)} arbitres")
    
    def get_adjustment(self, referee_name: str) -> Optional[RefereeAdjustment]:
        """Calcule les ajustements pour un arbitre"""
        ref = self.referees.get(referee_name)
        if not ref:
            return None
        
        matches = ref.get('matches', 0)
        confidence = "HIGH" if matches >= 100 else "MEDIUM" if matches >= 50 else "LOW"
        
        # === GOAL DISTRIBUTION ===
        avg_goals = ref.get('avg_goals', 2.5)
        under_25 = ref.get('under_25_pct', 40)
        over_35 = ref.get('over_35_pct', 30)
        
        # Check bimodal
        if referee_name in self.bimodal_refs:
            goal_dist = GoalDistribution.BIMODAL
            avoid_25 = True
            over_25_adj = 0  # Don't bet on 2.5 line
            over_35_boost = 10.0  # Boost Over 3.5
        elif avg_goals >= 3.0:
            goal_dist = GoalDistribution.HIGH_SCORING
            avoid_25 = False
            over_25_adj = (avg_goals - 2.5) * 8
            over_35_boost = over_35 - 30
        elif avg_goals <= 2.2:
            goal_dist = GoalDistribution.LOW_SCORING
            avoid_25 = False
            over_25_adj = (avg_goals - 2.5) * 8
            over_35_boost = 0
        else:
            goal_dist = GoalDistribution.NORMAL
            avoid_25 = False
            over_25_adj = (avg_goals - 2.5) * 5
            over_35_boost = 0
        
        # === CARD PROFILE ===
        avg_cards = ref.get('avg_cards', 3.0)
        h2_intensity = ref.get('second_half_intensity', 1.0)
        
        if avg_cards >= 4.0:
            card_profile = CardProfile.CARD_HAPPY
            cards_edge = 15.0
        elif avg_cards >= 3.5:
            card_profile = CardProfile.STRICT
            cards_edge = 10.0
        elif avg_cards <= 2.8:
            card_profile = CardProfile.LENIENT
            cards_edge = -10.0
        else:
            card_profile = CardProfile.MODERATE
            cards_edge = 0
        
        # === TEAM-SPECIFIC EDGES ===
        team_edges = {}
        for nem in ref.get('nemesis_teams', []):
            if nem.get('matches', 0) >= 5:
                team_edges[nem['team']] = nem['diff']
        for fav in ref.get('favored_teams', []):
            if fav.get('matches', 0) >= 5:
                team_edges[fav['team']] = fav['diff']
        
        # === WARNINGS ===
        warnings = []
        if matches < 30:
            warnings.append(f"Small sample: {matches} matches")
        if ref.get('volatility', 0) >= 2.5:
            warnings.append(f"High volatility: {ref['volatility']:.1f}")
        if goal_dist == GoalDistribution.BIMODAL:
            warnings.append("BIMODAL: Avoid 2.5 line, bet extremes")
        
        return RefereeAdjustment(
            referee_name=referee_name,
            matches=matches,
            confidence=confidence,
            goal_distribution=goal_dist,
            avoid_25_line=avoid_25,
            over_25_adjustment=over_25_adj,
            over_35_boost=over_35_boost,
            card_profile=card_profile,
            cards_over_35_edge=cards_edge,
            h2_cards_multiplier=h2_intensity,
            team_edges=team_edges,
            warnings=warnings
        )
    
    def apply_to_prediction(self, base_over_25_prob: float, base_btts_prob: float,
                           referee_name: str, home_team: str, away_team: str) -> Dict:
        """
        Applique les ajustements referee aux probabilités de base
        
        Returns:
            Dict avec probabilités ajustées et edges spécifiques
        """
        adj = self.get_adjustment(referee_name)
        
        result = {
            'over_25_prob': base_over_25_prob,
            'btts_prob': base_btts_prob,
            'referee_edges': [],
            'avoid_markets': [],
            'warnings': []
        }
        
        if not adj:
            result['warnings'].append(f"Referee {referee_name} not found")
            return result
        
        # === GOAL ADJUSTMENTS ===
        if adj.goal_distribution == GoalDistribution.BIMODAL:
            result['avoid_markets'].append("Over/Under 2.5")
            result['referee_edges'].append({
                'market': 'Over 3.5 Goals',
                'edge_pct': adj.over_35_boost,
                'reasoning': f"BIMODAL referee - matches are either low or high scoring"
            })
        else:
            # Adjust Over 2.5 probability
            result['over_25_prob'] = min(95, max(20, base_over_25_prob + adj.over_25_adjustment))
        
        # === CARD EDGES ===
        if adj.card_profile in [CardProfile.STRICT, CardProfile.CARD_HAPPY]:
            result['referee_edges'].append({
                'market': 'Over 3.5 Cards',
                'edge_pct': adj.cards_over_35_edge,
                'reasoning': f"{adj.card_profile.value}: {self.referees[referee_name]['avg_cards']:.1f} cards/match"
            })
        
        # H2 Cards (universal edge)
        if adj.h2_cards_multiplier >= 1.3:
            result['referee_edges'].append({
                'market': '2nd Half Cards',
                'edge_pct': (adj.h2_cards_multiplier - 1) * 15,
                'reasoning': f"H2 intensity: {adj.h2_cards_multiplier:.2f}x"
            })
        
        # === TEAM-SPECIFIC ===
        for team in [home_team, away_team]:
            if team in adj.team_edges:
                diff = adj.team_edges[team]
                direction = "MORE" if diff > 0 else "LESS"
                result['referee_edges'].append({
                    'market': f'{team} Cards',
                    'prediction': direction,
                    'edge_pct': abs(diff) * 10,
                    'reasoning': f"Historical: {diff:+.2f} cards vs avg with this referee"
                })
        
        result['warnings'] = adj.warnings
        result['confidence'] = adj.confidence
        
        return result


# Test
if __name__ == "__main__":
    integration = RefereeIntegration()
    
    print("\n" + "="*80)
    print("🎯 TEST: Liverpool vs Man City avec arbitre")
    print("="*80)
    
    # Test avec différents arbitres
    for ref_name in ['M Oliver', 'A Taylor', 'J Moss', 'A Madley']:
        adj = integration.get_adjustment(ref_name)
        if adj:
            print(f"\n🎯 {ref_name}:")
            print(f"   Distribution: {adj.goal_distribution.value}")
            print(f"   Cards: {adj.card_profile.value}")
            print(f"   Avoid 2.5 line: {adj.avoid_25_line}")
            print(f"   Over 3.5 boost: {adj.over_35_boost:+.1f}%")
            print(f"   H2 cards: {adj.h2_cards_multiplier:.2f}x")
            if adj.warnings:
                print(f"   ⚠️ {adj.warnings}")
    
    # Full prediction adjustment
    print("\n" + "="*80)
    print("📊 FULL ADJUSTMENT: Liverpool vs Man City")
    print("="*80)
    
    result = integration.apply_to_prediction(
        base_over_25_prob=75.0,
        base_btts_prob=65.0,
        referee_name='J Moss',
        home_team='Liverpool',
        away_team='Manchester City'
    )
    
    print(f"\nBase Over 2.5: 75% → Adjusted: {result['over_25_prob']:.0f}%")
    print(f"Referee Edges: {result['referee_edges']}")
    print(f"Avoid Markets: {result['avoid_markets']}")
    print(f"Warnings: {result['warnings']}")


# Patch: BTTS adjustment for BIMODAL referees
def adjust_btts_for_bimodal(base_btts: float, is_bimodal: bool) -> float:
    """
    Si arbitre BIMODAL, BTTS est moins fiable car:
    - 52% des matchs sont low-scoring (souvent 0-0, 1-0)
    - Dans ces matchs, BTTS NO est plus probable
    """
    if is_bimodal:
        # Réduire la confiance BTTS de 15%
        return base_btts * 0.85
    return base_btts
