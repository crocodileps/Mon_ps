"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🎯 ATTACK TEAM PROFILER V1.0 - HEDGE FUND GRADE                             ║
║                                                                              ║
║  Génère un profil narratif complet + edges pour chaque équipe:               ║
║  • DNA unique par équipe                                                     ║
║  • Marchés profitables identifiés                                            ║
║  • Marchés à éviter                                                          ║
║                                                                              ║
║  Philosophie Team-Centric: "Pour CETTE équipe, quels paris sont rentables?"  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

import sys
sys.path.insert(0, '/home/Mon_ps')
from agents.attack_v1.data.loader import AttackDataLoader, TeamOffensiveData
from agents.attack_v1.features.engineer import AttackFeatureEngineer, TeamOffensiveFeatures


@dataclass
class OffensiveEdge:
    """Un edge offensif identifié"""
    market: str
    edge_pct: float
    confidence: str  # LOW, MEDIUM, HIGH
    reasoning: str
    kelly_suggested: float = 0.02


@dataclass
class TeamOffensiveDNA:
    """ADN offensif complet d'une équipe"""
    team_name: str
    league: str
    
    # Profils
    offensive_profile: str
    timing_profile: str
    dependency_profile: str
    style_profile: str
    
    # Features clés
    features: TeamOffensiveFeatures = None
    
    # Edges
    profitable_markets: List[OffensiveEdge] = field(default_factory=list)
    avoid_markets: List[str] = field(default_factory=list)
    
    # Narratif
    narrative: str = ""
    
    # Fingerprint
    fingerprint_hash: str = ""


class AttackTeamProfiler:
    """
    Génère des profils offensifs complets avec edges.
    """
    
    # Moyennes de ligue pour calculer les edges
    LEAGUE_AVERAGES = {
        'EPL': {'goals_per_90': 1.45, 'xg_conversion': 1.0, 'clutch_pct': 18, 'set_piece_pct': 22},
        'La_liga': {'goals_per_90': 1.35, 'xg_conversion': 1.0, 'clutch_pct': 17, 'set_piece_pct': 24},
        'Bundesliga': {'goals_per_90': 1.60, 'xg_conversion': 1.0, 'clutch_pct': 19, 'set_piece_pct': 20},
        'Serie_A': {'goals_per_90': 1.40, 'xg_conversion': 1.0, 'clutch_pct': 18, 'set_piece_pct': 25},
        'Ligue_1': {'goals_per_90': 1.35, 'xg_conversion': 1.0, 'clutch_pct': 17, 'set_piece_pct': 23},
    }
    
    def __init__(self, loader: AttackDataLoader, engineer: AttackFeatureEngineer):
        self.loader = loader
        self.engineer = engineer
        self.profiles: Dict[str, TeamOffensiveDNA] = {}
        
    def profile_all(self) -> None:
        """Profile toutes les équipes"""
        print("=" * 80)
        print("🎯 ATTACK TEAM PROFILER V1.0")
        print("=" * 80)
        
        for team_name in self.engineer.features.keys():
            dna = self.profile_team(team_name)
            if dna and dna.features and dna.features.total_goals >= 5:
                self.profiles[team_name] = dna
                
        print(f"\n✅ {len(self.profiles)} équipes profilées")
        
    def profile_team(self, team_name: str) -> Optional[TeamOffensiveDNA]:
        """Profile une équipe spécifique"""
        features = self.engineer.get_features(team_name)
        team_data = self.loader.get_team(team_name)
        
        if not features or not team_data:
            return None
            
        dna = TeamOffensiveDNA(
            team_name=team_name,
            league=features.league,
            offensive_profile=features.offensive_profile,
            timing_profile=features.timing_profile,
            dependency_profile=features.dependency_profile,
            style_profile=features.style_profile,
            features=features,
            fingerprint_hash=features.fingerprint_hash,
        )
        
        # Identifier les edges
        self._identify_edges(dna, team_data)
        
        # Générer le narratif
        dna.narrative = self._generate_narrative(dna, team_data)
        
        return dna
        
    def _identify_edges(self, dna: TeamOffensiveDNA, team_data: TeamOffensiveData) -> None:
        """Identifie les edges offensifs"""
        f = dna.features
        league_avg = self.LEAGUE_AVERAGES.get(dna.league, self.LEAGUE_AVERAGES['EPL'])
        
        profitable = []
        avoid = []
        
        # ═══════════════════════════════════════════════════════════════════════
        # EDGE 1: Over 1.5 Team Goals (si scoring élevé)
        # ═══════════════════════════════════════════════════════════════════════
        if f.total_goals >= 15:  # Assez de données
            goals_per_match = f.total_goals / 15  # Estimation ~15 matchs
            if goals_per_match > league_avg['goals_per_90'] * 1.15:
                edge = ((goals_per_match / league_avg['goals_per_90']) - 1) * 100
                profitable.append(OffensiveEdge(
                    market=f"Over 1.5 {dna.team_name} Goals",
                    edge_pct=edge,
                    confidence="HIGH" if edge > 15 else "MEDIUM",
                    reasoning=f"G/match={goals_per_match:.2f} vs league avg {league_avg['goals_per_90']:.2f}",
                    kelly_suggested=min(0.05, edge / 100 * 0.4)
                ))
            elif goals_per_match < league_avg['goals_per_90'] * 0.85:
                avoid.append(f"Over 1.5 Team Goals (G/match={goals_per_match:.2f} < avg)")
                
        # ═══════════════════════════════════════════════════════════════════════
        # EDGE 2: 2H Team Goals (si DIESEL)
        # ═══════════════════════════════════════════════════════════════════════
        if f.timing_profile == "DIESEL" and f.goals_2h_pct > 55:
            edge = f.goals_2h_pct - 50  # vs équilibré
            profitable.append(OffensiveEdge(
                market=f"2H Over 0.5 {dna.team_name} Goals",
                edge_pct=edge,
                confidence="HIGH" if f.diesel_factor > 1.5 else "MEDIUM",
                reasoning=f"DIESEL: {f.goals_2h_pct:.0f}% buts en 2H, diesel_factor={f.diesel_factor:.2f}",
                kelly_suggested=min(0.04, edge / 100 * 0.35)
            ))
            
        # ═══════════════════════════════════════════════════════════════════════
        # EDGE 3: 1H Team Goals (si FAST_STARTER)
        # ═══════════════════════════════════════════════════════════════════════
        if f.timing_profile == "FAST_STARTER" and f.goals_1h_pct > 55:
            edge = f.goals_1h_pct - 50
            profitable.append(OffensiveEdge(
                market=f"1H Over 0.5 {dna.team_name} Goals",
                edge_pct=edge,
                confidence="HIGH" if f.sprinter_factor > 1.5 else "MEDIUM",
                reasoning=f"FAST_STARTER: {f.goals_1h_pct:.0f}% buts en 1H",
                kelly_suggested=min(0.04, edge / 100 * 0.35)
            ))
            
        # ═══════════════════════════════════════════════════════════════════════
        # EDGE 4: Late Goal (si CLUTCH)
        # ═══════════════════════════════════════════════════════════════════════
        if f.clutch_factor > league_avg['clutch_pct'] + 5:
            edge = f.clutch_factor - league_avg['clutch_pct']
            profitable.append(OffensiveEdge(
                market=f"{dna.team_name} Goal 76-90",
                edge_pct=edge,
                confidence="HIGH" if f.clutch_factor > 25 else "MEDIUM",
                reasoning=f"CLUTCH: {f.clutch_factor:.1f}% buts 76-90 vs avg {league_avg['clutch_pct']}%",
                kelly_suggested=min(0.03, edge / 100 * 0.3)
            ))
            
        # ═══════════════════════════════════════════════════════════════════════
        # EDGE 5: MVP Anytime Scorer (si ONE_MAN_TEAM ou STAR_DRIVEN)
        # ═══════════════════════════════════════════════════════════════════════
        if f.mvp_share > 30 and f.mvp_name:
            edge = f.mvp_share - 25  # vs average
            profitable.append(OffensiveEdge(
                market=f"{f.mvp_name} Anytime Scorer",
                edge_pct=edge,
                confidence="HIGH" if f.mvp_share > 40 else "MEDIUM",
                reasoning=f"MVP: {f.mvp_share:.0f}% des buts de l'équipe",
                kelly_suggested=min(0.04, edge / 100 * 0.35)
            ))
            
        # ═══════════════════════════════════════════════════════════════════════
        # EDGE 6: Set Piece Goal (si SET_PIECE_KINGS)
        # ═══════════════════════════════════════════════════════════════════════
        if f.set_piece_total_pct > league_avg['set_piece_pct'] + 5:
            edge = f.set_piece_total_pct - league_avg['set_piece_pct']
            profitable.append(OffensiveEdge(
                market=f"{dna.team_name} Set Piece Goal",
                edge_pct=edge,
                confidence="MEDIUM",
                reasoning=f"SET_PIECE: {f.set_piece_total_pct:.0f}% buts sur SP vs avg {league_avg['set_piece_pct']}%",
                kelly_suggested=min(0.03, edge / 100 * 0.25)
            ))
            
        # ═══════════════════════════════════════════════════════════════════════
        # EDGE 7: Header Goal (si header_pct élevé)
        # ═══════════════════════════════════════════════════════════════════════
        if f.header_pct > 20:  # Plus de 20% des buts de la tête
            edge = f.header_pct - 15  # vs average ~15%
            profitable.append(OffensiveEdge(
                market=f"{dna.team_name} Header Goal",
                edge_pct=edge,
                confidence="MEDIUM" if f.header_pct > 25 else "LOW",
                reasoning=f"AERIAL: {f.header_pct:.0f}% buts de la tête",
                kelly_suggested=min(0.02, edge / 100 * 0.2)
            ))
            
        # ═══════════════════════════════════════════════════════════════════════
        # EDGE 8: xG Overperformance (régression attendue)
        # ═══════════════════════════════════════════════════════════════════════
        if f.xg_overperformance > 3:  # Marque beaucoup plus que xG
            avoid.append(f"Over marchés (régression attendue, +{f.xg_overperformance:.1f} vs xG)")
        elif f.xg_overperformance < -3:  # Marque moins que xG
            profitable.append(OffensiveEdge(
                market=f"{dna.team_name} Team Goals (Regression Play)",
                edge_pct=abs(f.xg_overperformance) * 2,
                confidence="LOW",
                reasoning=f"UNDERPERFORM: {f.xg_overperformance:.1f} vs xG, régression attendue",
                kelly_suggested=0.01
            ))
            
        # ═══════════════════════════════════════════════════════════════════════
        # ÉVITER: Marchés basés sur faiblesse
        # ═══════════════════════════════════════════════════════════════════════
        if f.offensive_profile == "WASTEFUL":
            avoid.append(f"Over marchés (WASTEFUL: conversion {f.conversion_rate:.1f}%)")
            
        if f.offensive_profile == "STRUGGLING":
            avoid.append(f"Team Goals Over (STRUGGLING)")
            
        if f.dependency_profile == "ONE_MAN_TEAM" and f.mvp_name:
            avoid.append(f"First Goalscorer (trop concentré sur {f.mvp_name})")
            
        dna.profitable_markets = profitable
        dna.avoid_markets = avoid
        
    def _generate_narrative(self, dna: TeamOffensiveDNA, team_data: TeamOffensiveData) -> str:
        """Génère le narratif du profil"""
        f = dna.features
        
        # Emojis selon profil
        profile_emoji = {
            "GOAL_MACHINE": "⚽", "CLINICAL": "🎯", "EFFICIENT": "✅",
            "WASTEFUL": "❌", "AVERAGE": "➡️", "STRUGGLING": "📉"
        }
        timing_emoji = {
            "DIESEL": "🔥", "FAST_STARTER": "⚡", "CLUTCH": "🎯",
            "EARLY_KILLER": "💨", "CONSISTENT": "⚖️"
        }
        
        narrative = f"""
{'='*80}
🎯 PROFIL ADN OFFENSIF - {dna.team_name.upper()}
{'='*80}

   Profil: {profile_emoji.get(f.offensive_profile, '•')} {f.offensive_profile} | {timing_emoji.get(f.timing_profile, '•')} {f.timing_profile}
   Fingerprint: {dna.fingerprint_hash}

   📊 FOUNDATION:
      • Total: {f.total_goals} buts | xG: {f.total_xg:.1f}
      • xG Conversion: {f.xg_conversion:.2f} ({'+' if f.xg_overperformance > 0 else ''}{f.xg_overperformance:.1f} vs xG)

   ⏱️ TIMING DNA:
      • 1H: {f.goals_1h_pct:.0f}% | 2H: {f.goals_2h_pct:.0f}%
      • Diesel Factor: {f.diesel_factor:.2f}
      • 0-15: {f.goals_0_15_pct:.0f}% | 76-90: {f.goals_76_90_pct:.0f}%
      
   👤 DEPENDENCY DNA ({f.dependency_profile}):
      • MVP: {f.mvp_name} → {f.mvp_goals}G ({f.mvp_share:.0f}% des buts)
      • Top 3: {f.top3_share:.0f}%
      • Buteurs différents: {f.unique_scorers}
      
   🎨 STYLE DNA ({f.style_profile}):
      • Open Play: {f.open_play_pct:.0f}% | Set Pieces: {f.set_piece_total_pct:.0f}%
      • Headers: {f.header_pct:.0f}%
      • Verticality: {f.verticality_index:.2f}
      
   🧠 GAMESTATE DNA:
      • xG Drawing: {f.xg_when_drawing:.2f}
      • Killer Instinct: {f.killer_instinct:.2f}
      • Comeback Factor: {f.comeback_factor:.2f}
"""
        
        # Ajouter les edges
        if dna.profitable_markets:
            narrative += "\n   💰 MARCHÉS PROFITABLES:\n"
            for edge in dna.profitable_markets:
                narrative += f"      • {edge.market}: +{edge.edge_pct:.0f}% edge ({edge.confidence})\n"
                narrative += f"        → {edge.reasoning}\n"
                
        if dna.avoid_markets:
            narrative += "\n   🚫 MARCHÉS À ÉVITER:\n"
            for market in dna.avoid_markets:
                narrative += f"      • {market}\n"
                
        return narrative
        
    def get_profile(self, team_name: str) -> Optional[TeamOffensiveDNA]:
        """Récupère le profil d'une équipe"""
        return self.profiles.get(team_name)
        
    def compare_attack(self, team_a: str, team_b: str) -> Dict:
        """Compare l'attaque de deux équipes"""
        dna_a = self.get_profile(team_a)
        dna_b = self.get_profile(team_b)
        
        if not dna_a or not dna_b:
            return {}
            
        f_a = dna_a.features
        f_b = dna_b.features
        
        comparison = {
            'team_a': team_a,
            'team_b': team_b,
            'fingerprint_a': dna_a.fingerprint_hash,
            'fingerprint_b': dna_b.fingerprint_hash,
            'matchup_edges': []
        }
        
        # FRICTION: DIESEL vs défense qui s'effondre tard
        if f_a.timing_profile == "DIESEL" and f_a.clutch_factor > 20:
            comparison['matchup_edges'].append({
                'market': f'{team_a} Goal 76-90',
                'edge': '+HIGH',
                'reasoning': f'{team_a} DIESEL ({f_a.goals_2h_pct:.0f}% 2H) - late surge probable'
            })
            
        # FRICTION: ONE_MAN_TEAM - dépendance au MVP
        if f_a.dependency_profile == "ONE_MAN_TEAM":
            comparison['matchup_edges'].append({
                'market': f'{f_a.mvp_name} Anytime',
                'edge': '+HIGH',
                'reasoning': f'{team_a} dépend de {f_a.mvp_name} ({f_a.mvp_share:.0f}%)'
            })
            
        # FRICTION: Équipes offensives = Over
        combined_goals = f_a.total_goals + f_b.total_goals
        if combined_goals > 50:  # Beaucoup de buts cumulés
            comparison['matchup_edges'].append({
                'market': 'Over 2.5 Goals',
                'edge': '+MEDIUM',
                'reasoning': f'High scoring teams: {team_a}={f_a.total_goals}G, {team_b}={f_b.total_goals}G'
            })
            
        return comparison


# Test
if __name__ == '__main__':
    loader = AttackDataLoader()
    loader.load_all()
    
    engineer = AttackFeatureEngineer(loader)
    engineer.engineer_all()
    
    profiler = AttackTeamProfiler(loader, engineer)
    profiler.profile_all()
    
    # Afficher quelques profils
    for team in ['Liverpool', 'Bayern Munich', 'Paris Saint Germain', 'Barcelona']:
        dna = profiler.get_profile(team)
        if dna:
            print(dna.narrative)
            
    # Test comparison
    print("\n" + "=" * 80)
    print("⚔️ COMPARISON: Liverpool vs Arsenal")
    print("=" * 80)
    comp = profiler.compare_attack('Liverpool', 'Arsenal')
    for edge in comp.get('matchup_edges', []):
        print(f"   • {edge['market']}: {edge['edge']} - {edge['reasoning']}")
