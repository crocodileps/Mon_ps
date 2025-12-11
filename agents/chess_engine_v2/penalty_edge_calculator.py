"""
🎯 PENALTY & SET PIECE EDGE CALCULATOR
Hedge Fund Grade - Combine toutes les données pour des edges tradables

Data Sources:
- all_shots_against_2025.json (situations, zones, shot types)
- referee_dna_hedge_fund_v4.json (H2 intensity, cards)
- defender_dna (cards/90, fouls/90)
- attack DNA (penalty takers)
"""

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
from pathlib import Path

class VulnerabilityLevel(Enum):
    EXTREME = "EXTREME"      # Top 10%
    HIGH = "HIGH"            # Top 25%
    MODERATE = "MODERATE"    # Top 50%
    LOW = "LOW"              # Bottom 50%

@dataclass
class TeamDefensiveVulnerability:
    """Vulnérabilités défensives d'une équipe"""
    team: str
    league: str
    
    # Penalty vulnerability
    penalties_conceded: int = 0
    penalty_goals_conceded: int = 0
    penalty_rate: float = 0.0  # % of shots that are penalties
    penalty_vulnerability: VulnerabilityLevel = VulnerabilityLevel.LOW
    
    # Header vulnerability
    headers_faced: int = 0
    header_goals_conceded: int = 0
    header_conversion_against: float = 0.0
    header_vulnerability: VulnerabilityLevel = VulnerabilityLevel.LOW
    
    # Corner vulnerability
    corners_faced: int = 0
    corner_goals_conceded: int = 0
    corner_vulnerability: VulnerabilityLevel = VulnerabilityLevel.LOW
    
    # Zone vulnerability
    box_shots_faced: int = 0
    box_goals_conceded: int = 0
    box_conversion_against: float = 0.0
    outside_box_goals: int = 0
    
    # Set piece vulnerability
    set_piece_goals_conceded: int = 0
    
    def to_dict(self) -> dict:
        return {
            'team': self.team,
            'penalties_conceded': self.penalties_conceded,
            'penalty_vulnerability': self.penalty_vulnerability.value,
            'header_conversion_against': self.header_conversion_against,
            'header_vulnerability': self.header_vulnerability.value,
            'corner_goals_conceded': self.corner_goals_conceded,
            'corner_vulnerability': self.corner_vulnerability.value,
            'box_conversion_against': self.box_conversion_against,
        }


@dataclass
class PenaltyEdge:
    """Edge sur le marché Penalty"""
    market: str
    prediction: str
    probability: float
    edge_pct: float
    confidence: str
    reasoning: str
    timing: str = "PRE_MATCH"


class PenaltyEdgeCalculator:
    """
    Calcule les edges sur Penalty et Set Pieces
    en combinant toutes les données disponibles
    """
    
    def __init__(self):
        self.shots_data: Dict = {}
        self.team_vulnerabilities: Dict[str, TeamDefensiveVulnerability] = {}
        self.penalty_takers: Dict[str, int] = {}
        self.loaded = False
        
    def load_data(self):
        """Charge toutes les données nécessaires"""
        if self.loaded:
            return
            
        # Load shots data
        shots_path = Path("/home/Mon_ps/data/goalkeeper_dna/all_shots_against_2025.json")
        if shots_path.exists():
            with open(shots_path) as f:
                self.shots_data = json.load(f)
        
        self._analyze_all_teams()
        self.loaded = True
        
    def _analyze_all_teams(self):
        """Analyse toutes les équipes"""
        all_penalties = []
        team_stats = {}
        
        for team, shots in self.shots_data.items():
            if not shots:
                continue
                
            # Calculs de base
            total = len(shots)
            penalties = [s for s in shots if s.get('situation') == 'Penalty']
            headers = [s for s in shots if s.get('shotType') == 'Head']
            corners = [s for s in shots if s.get('situation') == 'FromCorner']
            box_shots = [s for s in shots if float(s.get('X', 0)) >= 0.83]
            
            # Goals
            penalty_goals = len([p for p in penalties if p.get('result') == 'Goal'])
            header_goals = len([h for h in headers if h.get('result') == 'Goal'])
            corner_goals = len([c for c in corners if c.get('result') == 'Goal'])
            box_goals = len([b for b in box_shots if b.get('result') == 'Goal'])
            outside_goals = len([s for s in shots if float(s.get('X', 0)) < 0.83 and s.get('result') == 'Goal'])
            
            # Set pieces
            set_pieces = [s for s in shots if s.get('situation') in ['FromCorner', 'SetPiece', 'DirectFreekick']]
            set_piece_goals = len([s for s in set_pieces if s.get('result') == 'Goal'])
            
            team_stats[team] = {
                'penalties_conceded': len(penalties),
                'penalty_goals': penalty_goals,
                'penalty_rate': len(penalties) / total * 100 if total else 0,
                'headers_faced': len(headers),
                'header_goals': header_goals,
                'header_conversion': header_goals / len(headers) * 100 if headers else 0,
                'corners_faced': len(corners),
                'corner_goals': corner_goals,
                'box_shots': len(box_shots),
                'box_goals': box_goals,
                'box_conversion': box_goals / len(box_shots) * 100 if box_shots else 0,
                'outside_goals': outside_goals,
                'set_piece_goals': set_piece_goals,
            }
            
            # Track penalty scorers
            for p in penalties:
                if p.get('result') == 'Goal':
                    player = p.get('player', 'Unknown')
                    self.penalty_takers[player] = self.penalty_takers.get(player, 0) + 1
        
        # Calculate percentiles and create vulnerability profiles
        penalty_counts = sorted([s['penalties_conceded'] for s in team_stats.values()], reverse=True)
        header_convs = sorted([s['header_conversion'] for s in team_stats.values()], reverse=True)
        corner_goals_list = sorted([s['corner_goals'] for s in team_stats.values()], reverse=True)
        box_convs = sorted([s['box_conversion'] for s in team_stats.values()], reverse=True)
        
        for team, stats in team_stats.items():
            vuln = TeamDefensiveVulnerability(
                team=team,
                league=self.shots_data[team][0].get('league', '') if self.shots_data[team] else '',
                penalties_conceded=stats['penalties_conceded'],
                penalty_goals_conceded=stats['penalty_goals'],
                penalty_rate=stats['penalty_rate'],
                headers_faced=stats['headers_faced'],
                header_goals_conceded=stats['header_goals'],
                header_conversion_against=stats['header_conversion'],
                corners_faced=stats['corners_faced'],
                corner_goals_conceded=stats['corner_goals'],
                box_shots_faced=stats['box_shots'],
                box_goals_conceded=stats['box_goals'],
                box_conversion_against=stats['box_conversion'],
                outside_box_goals=stats['outside_goals'],
                set_piece_goals_conceded=stats['set_piece_goals'],
            )
            
            # Set vulnerability levels based on percentiles
            pen_rank = penalty_counts.index(stats['penalties_conceded']) / len(penalty_counts) if penalty_counts else 1
            if pen_rank <= 0.10:
                vuln.penalty_vulnerability = VulnerabilityLevel.EXTREME
            elif pen_rank <= 0.25:
                vuln.penalty_vulnerability = VulnerabilityLevel.HIGH
            elif pen_rank <= 0.50:
                vuln.penalty_vulnerability = VulnerabilityLevel.MODERATE
                
            header_rank = header_convs.index(stats['header_conversion']) / len(header_convs) if header_convs else 1
            if header_rank <= 0.10:
                vuln.header_vulnerability = VulnerabilityLevel.EXTREME
            elif header_rank <= 0.25:
                vuln.header_vulnerability = VulnerabilityLevel.HIGH
            elif header_rank <= 0.50:
                vuln.header_vulnerability = VulnerabilityLevel.MODERATE
                
            corner_rank = corner_goals_list.index(stats['corner_goals']) / len(corner_goals_list) if corner_goals_list else 1
            if corner_rank <= 0.10:
                vuln.corner_vulnerability = VulnerabilityLevel.EXTREME
            elif corner_rank <= 0.25:
                vuln.corner_vulnerability = VulnerabilityLevel.HIGH
            elif corner_rank <= 0.50:
                vuln.corner_vulnerability = VulnerabilityLevel.MODERATE
            
            self.team_vulnerabilities[team] = vuln
    
    def get_team_vulnerability(self, team: str) -> Optional[TeamDefensiveVulnerability]:
        """Récupère le profil de vulnérabilité d'une équipe"""
        self.load_data()
        return self.team_vulnerabilities.get(team)
    
    def calculate_penalty_edge(
        self,
        defending_team: str,
        attacking_team: str,
        referee_h2_intensity: float = 1.0,
        attacking_penalty_taker: str = None
    ) -> List[PenaltyEdge]:
        """
        Calcule l'edge sur le marché Penalty
        
        Chain Analysis:
        1. Équipe qui concède beaucoup de penalties
        2. Arbitre avec H2 intensity élevé
        3. Attaquant qui provoque des penalties
        """
        self.load_data()
        edges = []
        
        defender_vuln = self.team_vulnerabilities.get(defending_team)
        if not defender_vuln:
            return edges
        
        base_prob = 15  # Base: 15% chance de penalty par match
        edge = 0
        reasons = []
        
        # Factor 1: Team vulnerability
        if defender_vuln.penalty_vulnerability == VulnerabilityLevel.EXTREME:
            base_prob += 10
            edge += 5
            reasons.append(f"{defending_team} TOP 10% penalty conceded")
        elif defender_vuln.penalty_vulnerability == VulnerabilityLevel.HIGH:
            base_prob += 5
            edge += 2.5
            reasons.append(f"{defending_team} TOP 25% penalty conceded")
        
        # Factor 2: Referee H2 intensity
        if referee_h2_intensity >= 1.5:
            base_prob += 5
            edge += 2
            reasons.append(f"H2 intense ({referee_h2_intensity:.2f}x) = more fouls")
        
        # Factor 3: Penalty taker quality
        if attacking_penalty_taker and attacking_penalty_taker in self.penalty_takers:
            pen_scored = self.penalty_takers[attacking_penalty_taker]
            if pen_scored >= 3:
                edge += 1.5
                reasons.append(f"{attacking_penalty_taker} = elite penalty taker ({pen_scored})")
        
        if edge >= 3:
            confidence = "HIGH" if edge >= 5 else "MEDIUM"
            edges.append(PenaltyEdge(
                market="Penalty Scored in Match",
                prediction="YES",
                probability=min(40, base_prob),
                edge_pct=edge,
                confidence=confidence,
                reasoning=" | ".join(reasons),
                timing="PRE_MATCH"
            ))
        
        return edges
    
    def calculate_header_edge(
        self,
        defending_team: str,
        attacking_has_aerial_threat: bool = False
    ) -> List[PenaltyEdge]:
        """Calcule l'edge sur les buts de la tête"""
        self.load_data()
        edges = []
        
        defender_vuln = self.team_vulnerabilities.get(defending_team)
        if not defender_vuln:
            return edges
        
        if defender_vuln.header_vulnerability in [VulnerabilityLevel.EXTREME, VulnerabilityLevel.HIGH]:
            edge = 4 if defender_vuln.header_vulnerability == VulnerabilityLevel.EXTREME else 2.5
            
            if attacking_has_aerial_threat:
                edge += 2
            
            edges.append(PenaltyEdge(
                market="Header Goal in Match",
                prediction="YES",
                probability=25 + edge * 2,
                edge_pct=edge,
                confidence="MEDIUM",
                reasoning=f"{defending_team} {defender_vuln.header_conversion_against:.0f}% header conv",
                timing="PRE_MATCH"
            ))
        
        return edges
    
    def calculate_corner_goal_edge(
        self,
        defending_team: str,
        attacking_team_corner_threat: bool = False
    ) -> List[PenaltyEdge]:
        """Calcule l'edge sur les buts de corner"""
        self.load_data()
        edges = []
        
        defender_vuln = self.team_vulnerabilities.get(defending_team)
        if not defender_vuln:
            return edges
        
        if defender_vuln.corner_vulnerability in [VulnerabilityLevel.EXTREME, VulnerabilityLevel.HIGH]:
            edge = 5 if defender_vuln.corner_vulnerability == VulnerabilityLevel.EXTREME else 3
            
            if attacking_team_corner_threat:
                edge += 2
            
            edges.append(PenaltyEdge(
                market="Goal from Corner",
                prediction="YES",
                probability=20 + edge * 2,
                edge_pct=edge,
                confidence="MEDIUM",
                reasoning=f"{defending_team} {defender_vuln.corner_goals_conceded}G from corners",
                timing="PRE_MATCH"
            ))
        
        return edges
    
    def get_all_edges(
        self,
        home_team: str,
        away_team: str,
        referee_h2_intensity: float = 1.0,
        home_penalty_taker: str = None,
        away_penalty_taker: str = None
    ) -> List[PenaltyEdge]:
        """Récupère tous les edges pour un match"""
        self.load_data()
        all_edges = []
        
        # Penalty edges (both directions)
        all_edges.extend(self.calculate_penalty_edge(
            away_team, home_team, referee_h2_intensity, home_penalty_taker
        ))
        all_edges.extend(self.calculate_penalty_edge(
            home_team, away_team, referee_h2_intensity, away_penalty_taker
        ))
        
        # Header edges
        all_edges.extend(self.calculate_header_edge(away_team))
        all_edges.extend(self.calculate_header_edge(home_team))
        
        # Corner edges
        all_edges.extend(self.calculate_corner_goal_edge(away_team))
        all_edges.extend(self.calculate_corner_goal_edge(home_team))
        
        return all_edges


# ═══════════════════════════════════════════════════════════════════
# LAST ACTION EDGE CALCULATOR
# ═══════════════════════════════════════════════════════════════════

# Conversion rates from data
LAST_ACTION_CONVERSION = {
    'Throughball': 30.5,
    'Standard': 29.6,
    'Rebound': 19.0,
    'HeadPass': 13.0,
    'Cross': 12.3,
    'TakeOn': 10.4,
    'Chipped': 10.4,
    'BallTouch': 9.5,
    'BallRecovery': 9.0,
    'Pass': 8.6,
    'None': 8.8,
    'Aerial': 4.4,
}


def get_throughball_edge(
    attacking_team_has_pace: bool,
    defending_team_high_line: bool
) -> Optional[PenaltyEdge]:
    """
    Throughball = 30.5% conversion (HIGHEST!)
    Edge when: fast attackers + high defensive line
    """
    if attacking_team_has_pace and defending_team_high_line:
        return PenaltyEdge(
            market="Goal from Throughball",
            prediction="HIGH PROBABILITY",
            probability=35,
            edge_pct=5,
            confidence="HIGH",
            reasoning="Throughball 30.5% conv + pace + high line",
            timing="CONTEXT"
        )
    return None


if __name__ == "__main__":
    calc = PenaltyEdgeCalculator()
    calc.load_data()
    
    print("="*70)
    print("🎯 PENALTY EDGE CALCULATOR - TEST")
    print("="*70)
    
    # Test West Ham (vulnérable aux corners)
    wh_vuln = calc.get_team_vulnerability("West Ham")
    if wh_vuln:
        print(f"\nWest Ham vulnerabilities:")
        print(f"   Penalty: {wh_vuln.penalty_vulnerability.value}")
        print(f"   Header: {wh_vuln.header_vulnerability.value} ({wh_vuln.header_conversion_against:.0f}%)")
        print(f"   Corner: {wh_vuln.corner_vulnerability.value} ({wh_vuln.corner_goals_conceded}G)")
    
    # Test match
    print("\n" + "="*70)
    print("Arsenal vs West Ham (H2=1.65)")
    print("="*70)
    
    edges = calc.get_all_edges("Arsenal", "West Ham", 1.65, "Saka", "Bowen")
    for e in edges:
        print(f"\n   {e.market}")
        print(f"   → {e.prediction} @ {e.probability:.0f}%")
        print(f"   → Edge: {e.edge_pct:.1f}% ({e.confidence})")
        print(f"   → {e.reasoning}")
