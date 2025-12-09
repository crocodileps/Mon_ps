"""
═══════════════════════════════════════════════════════════════════════════════
🏦 TEAM PROFILER - ADN DÉFENSIF UNIQUE
   
   Chaque équipe est une empreinte digitale unique.
   Ce module génère le profil narratif complet d'une équipe.
   
   PHILOSOPHIE:
   - Arsenal n'est pas "une équipe qui défend bien"
   - Arsenal EST: "FORTRESS HOME, vulnérable en fin de match (late_pct=46%),
     GK elite (percentile 95), défenseurs disciplinés (avg_discipline=78),
     EDGE sur Clean Sheet Home (+8%), AVOID Over 3.5"
   
   OUTPUT:
   - Profil narratif (texte)
   - DNA fingerprint (dict)
   - Marchés profitables (list avec edge %)
   - Marchés à éviter (list)
   - Friction vectors (pour matchups)
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json


class DefensiveProfile(Enum):
    """Profils défensifs possibles."""
    FORTRESS = "FORTRESS"           # CS% > 45%, resist_global > 80
    SOLID = "SOLID"                 # CS% 35-45%, resist_global 60-80
    AVERAGE = "AVERAGE"             # CS% 25-35%, resist_global 40-60
    LEAKY = "LEAKY"                 # CS% 15-25%, resist_global 20-40
    CATASTROPHIC = "CATASTROPHIC"   # CS% < 15%, resist_global < 20


class TimingProfile(Enum):
    """Profils temporels - quand l'équipe concède."""
    STARTS_STRONG = "STARTS_STRONG"         # early_pct < 25%
    CONSISTENT = "CONSISTENT"               # Équilibré
    FADES_LATE = "FADES_LATE"              # late_pct > 40%
    SLOW_STARTER = "SLOW_STARTER"          # early_pct > 40%
    SECOND_HALF_COLLAPSE = "2H_COLLAPSE"   # 2h_pct > 60%


class GoalkeeperProfile(Enum):
    """Profils gardien."""
    ELITE = "ELITE"           # percentile > 85
    ABOVE_AVERAGE = "ABOVE_AVG"  # percentile 65-85
    AVERAGE = "AVERAGE"       # percentile 35-65
    BELOW_AVERAGE = "BELOW_AVG"  # percentile 15-35
    LIABILITY = "LIABILITY"   # percentile < 15


@dataclass
class DefensiveEdge:
    """Représente un edge sur un marché spécifique."""
    market: str
    edge_pct: float
    confidence: str  # HIGH, MEDIUM, LOW
    reasoning: str
    kelly_suggested: float
    
    def __str__(self):
        return f"{self.market}: {self.edge_pct:+.1f}% ({self.confidence}) - {self.reasoning}"


@dataclass
class TeamDNA:
    """ADN défensif complet d'une équipe - Empreinte digitale unique."""
    
    # Identité
    team_name: str
    league: str
    
    # Profils
    defensive_profile: DefensiveProfile
    timing_profile: TimingProfile
    gk_profile: GoalkeeperProfile
    home_away_profile: str  # HOME_FORTRESS, AWAY_WEAK, CONSISTENT, etc.
    
    # Métriques clés
    xga_90: float
    ga_90: float
    cs_pct: float
    overperform: float  # GA - xGA (négatif = meilleur que prévu)
    resist_global: int
    
    # Timing DNA
    early_pct: float
    mid_pct: float
    late_pct: float
    
    # Goalkeeper
    gk_percentile: float
    gk_save_rate: float
    gk_late_vulnerability: float  # Save rate 76-90 min
    
    # Set Pieces
    set_piece_vuln_pct: float
    corner_concede_rate: float
    
    # Defender aggregates
    def_discipline: float
    def_cards_90: float
    def_transition_vuln: float
    
    # Corners/Shots (Football-Data)
    corners_for_avg: float
    corners_against_avg: float
    corners_total_avg: float
    
    # Edges identifiés
    profitable_markets: List[DefensiveEdge] = field(default_factory=list)
    avoid_markets: List[str] = field(default_factory=list)
    
    # Narratif
    narrative: str = ""
    fingerprint_hash: str = ""
    
    def generate_narrative(self) -> str:
        """Génère le profil narratif unique de l'équipe."""
        parts = []
        
        # Ouverture avec profil global
        parts.append(f"🏰 {self.team_name} ({self.league})")
        parts.append(f"   Profil: {self.defensive_profile.value} | {self.timing_profile.value}")
        parts.append("")
        
        # Foundation
        parts.append("   📊 FOUNDATION:")
        parts.append(f"      • xGA/90: {self.xga_90:.2f} | GA/90: {self.ga_90:.2f}")
        parts.append(f"      • Clean Sheet: {self.cs_pct:.1f}%")
        
        if self.overperform > 0:
            parts.append(f"      • ⚠️ UNDERPERFORM: Concède {self.overperform:.1f} buts DE PLUS que xGA")
            parts.append(f"        → Régression positive attendue (chanceux)")
        elif self.overperform < -1:
            parts.append(f"      • ✅ OVERPERFORM: Concède {abs(self.overperform):.1f} buts DE MOINS que xGA")
            parts.append(f"        → Régression négative possible (malchanceux adversaires)")
        
        # Timing
        parts.append("")
        parts.append("   ⏱️ TIMING DNA:")
        parts.append(f"      • 0-30 min: {self.early_pct:.1f}%")
        parts.append(f"      • 30-60 min: {self.mid_pct:.1f}%")
        parts.append(f"      • 60-90 min: {self.late_pct:.1f}%")
        
        if self.late_pct > 40:
            parts.append(f"      • 🚨 VULNÉRABILITÉ FIN DE MATCH: {self.late_pct:.1f}% des buts en 60-90")
            parts.append(f"        → EDGE: Late Goal market")
        elif self.early_pct > 40:
            parts.append(f"      • 🚨 DÉMARRAGE FAIBLE: {self.early_pct:.1f}% des buts en 0-30")
            parts.append(f"        → EDGE: First Half Goal market")
        
        # Goalkeeper
        parts.append("")
        parts.append("   🧤 GOALKEEPER:")
        parts.append(f"      • Percentile: {self.gk_percentile:.0f}/100 ({self.gk_profile.value})")
        parts.append(f"      • Save Rate: {self.gk_save_rate:.1f}%")
        
        if self.gk_late_vulnerability < 65:
            parts.append(f"      • ⚠️ FAIBLE EN FIN DE MATCH: SR 76-90 = {self.gk_late_vulnerability:.1f}%")
        
        # Set Pieces
        if self.set_piece_vuln_pct > 30:
            parts.append("")
            parts.append("   🎯 SET PIECES:")
            parts.append(f"      • ⚠️ VULNÉRABLE: {self.set_piece_vuln_pct:.1f}% des buts sur SP")
        
        # Marchés profitables
        if self.profitable_markets:
            parts.append("")
            parts.append("   💰 MARCHÉS PROFITABLES:")
            for edge in self.profitable_markets:
                parts.append(f"      • {edge}")
        
        # Marchés à éviter
        if self.avoid_markets:
            parts.append("")
            parts.append("   🚫 MARCHÉS À ÉVITER:")
            for market in self.avoid_markets:
                parts.append(f"      • {market}")
        
        self.narrative = "\n".join(parts)
        return self.narrative


class TeamProfiler:
    """
    Génère le profil ADN défensif complet d'une équipe.
    
    USAGE:
        profiler = TeamProfiler(data_loader)
        dna = profiler.profile_team('Arsenal')
        print(dna.narrative)
    """
    
    def __init__(self, data_loader):
        """
        Args:
            data_loader: Instance de DefenseDataLoader avec données chargées
        """
        self.loader = data_loader
        self.league_averages = {}
        self._compute_league_averages()
    
    def _compute_league_averages(self) -> None:
        """Calcule les moyennes par ligue pour contextualiser."""
        # Charger toutes les équipes et calculer les moyennes
        all_teams = self.loader.get_all_teams()
        
        by_league = {}
        for team in all_teams:
            data = self.loader.get_team_data(team)
            dl = data.get('defensive_lines', {})
            if not dl:
                continue
            
            league = dl.get('league', 'Unknown')
            if league not in by_league:
                by_league[league] = {'xga': [], 'cs': [], 'resist': []}
            
            foundation = dl.get('foundation', {})
            resistance = dl.get('resistance', {})
            
            by_league[league]['xga'].append(foundation.get('xga_90', 1.5))
            by_league[league]['cs'].append(foundation.get('cs_pct', 30))
            by_league[league]['resist'].append(resistance.get('resist_global', 50))
        
        for league, data in by_league.items():
            self.league_averages[league] = {
                'xga_90': np.mean(data['xga']) if data['xga'] else 1.5,
                'cs_pct': np.mean(data['cs']) if data['cs'] else 30,
                'resist_global': np.mean(data['resist']) if data['resist'] else 50,
            }
    
    def profile_team(self, team_name: str) -> TeamDNA:
        """
        Génère le profil ADN défensif complet d'une équipe.
        
        Args:
            team_name: Nom de l'équipe
        
        Returns:
            TeamDNA avec profil complet et marchés profitables
        """
        # Charger toutes les données
        data = self.loader.get_team_data(team_name)
        
        # Extraire les composants
        dl = data.get('defensive_lines', {}) or {}
        td = data.get('team_defense', {}) or {}
        gk = data.get('goalkeeper', {}) or {}
        gk_timing = data.get('gk_timing', {}) or {}
        defenders = data.get('defenders', {}) or {}
        corners = data.get('corners_dna', {}) or {}
        
        # Foundation
        foundation = dl.get('foundation', {}) or {}
        resistance = dl.get('resistance', {}) or {}
        timing = dl.get('timing_dna', {}) or {}
        
        # Métriques de base
        xga_90 = foundation.get('xga_90', 1.5)
        ga_90 = foundation.get('ga_90', 1.5)
        cs_pct = foundation.get('cs_pct', 30)
        overperform = foundation.get('overperform', 0)
        resist_global = resistance.get('resist_global', 50)
        
        # Timing
        early_pct = timing.get('early_pct', 33)
        mid_pct = timing.get('mid_pct', 33)
        late_pct = timing.get('late_pct', 33)
        
        # Goalkeeper
        gk_percentile = gk.get('gk_percentile', 50)
        gk_save_rate = gk.get('save_rate', 70)
        
        # GK late vulnerability
        by_timing = gk.get('by_timing', {}) or {}
        late_timing = by_timing.get('76-90', {}) if isinstance(by_timing, dict) else {}
        gk_late_sr = late_timing.get('save_rate', 70) if isinstance(late_timing, dict) else 70
        
        # Set pieces
        set_piece_vuln = td.get('set_piece_vuln_pct', 25)
        
        # Defenders
        def_discipline = defenders.get('avg_discipline', 50)
        def_cards = defenders.get('avg_cards_90', 0.2)
        def_transition = defenders.get('max_transition_vuln', 0)
        
        # Corners
        corners_for = corners.get('corners_for_avg', 5)
        corners_against = corners.get('corners_against_avg', 5)
        corners_total = corners.get('corners_total_avg', 10)
        
        # ═══════════════════════════════════════════════════════════════════════
        # DÉTERMINER LES PROFILS
        # ═══════════════════════════════════════════════════════════════════════
        
        # Defensive Profile
        if cs_pct > 45 and resist_global > 80:
            def_profile = DefensiveProfile.FORTRESS
        elif cs_pct > 35 and resist_global > 60:
            def_profile = DefensiveProfile.SOLID
        elif cs_pct > 25 and resist_global > 40:
            def_profile = DefensiveProfile.AVERAGE
        elif cs_pct > 15:
            def_profile = DefensiveProfile.LEAKY
        else:
            def_profile = DefensiveProfile.CATASTROPHIC
        
        # Timing Profile
        if late_pct > 40:
            timing_profile = TimingProfile.FADES_LATE
        elif early_pct > 40:
            timing_profile = TimingProfile.SLOW_STARTER
        elif early_pct < 25:
            timing_profile = TimingProfile.STARTS_STRONG
        else:
            timing_profile = TimingProfile.CONSISTENT
        
        # GK Profile
        if gk_percentile > 85:
            gk_profile = GoalkeeperProfile.ELITE
        elif gk_percentile > 65:
            gk_profile = GoalkeeperProfile.ABOVE_AVERAGE
        elif gk_percentile > 35:
            gk_profile = GoalkeeperProfile.AVERAGE
        elif gk_percentile > 15:
            gk_profile = GoalkeeperProfile.BELOW_AVERAGE
        else:
            gk_profile = GoalkeeperProfile.LIABILITY
        
        # Home/Away profile
        xga_home = td.get('xga_home', xga_90)
        xga_away = td.get('xga_away', xga_90)
        if isinstance(xga_home, (int, float)) and isinstance(xga_away, (int, float)):
            if xga_home < xga_away * 0.7:
                ha_profile = "HOME_FORTRESS"
            elif xga_away < xga_home * 0.7:
                ha_profile = "AWAY_STRONGER"
            else:
                ha_profile = "CONSISTENT"
        else:
            ha_profile = "UNKNOWN"
        
        # ═══════════════════════════════════════════════════════════════════════
        # IDENTIFIER LES EDGES
        # ═══════════════════════════════════════════════════════════════════════
        
        profitable = []
        avoid = []
        
        league = dl.get('league', 'Unknown')
        league_avg = self.league_averages.get(league, {'xga_90': 1.5, 'cs_pct': 30, 'resist_global': 50})
        
        # EDGE 1: Clean Sheet (si CS% > moyenne + 10%)
        cs_edge = cs_pct - league_avg['cs_pct']
        if cs_edge > 10:
            kelly = min(0.05, cs_edge / 100 * 0.5)
            profitable.append(DefensiveEdge(
                market="Clean Sheet",
                edge_pct=cs_edge,
                confidence="HIGH" if cs_edge > 15 else "MEDIUM",
                reasoning=f"CS%={cs_pct:.1f}% vs league avg {league_avg['cs_pct']:.1f}%",
                kelly_suggested=kelly
            ))
        elif cs_edge < -10:
            avoid.append(f"Clean Sheet (CS%={cs_pct:.1f}% < league avg)")
        
        # EDGE 2: Late Goal (si late_pct > 40%)
        if late_pct > 40:
            edge = late_pct - 33  # vs équilibré
            profitable.append(DefensiveEdge(
                market="Late Goal (76-90)",
                edge_pct=edge,
                confidence="HIGH" if late_pct > 45 else "MEDIUM",
                reasoning=f"Late vulnerability: {late_pct:.1f}% des buts concédés après 60'",
                kelly_suggested=min(0.04, edge / 100 * 0.4)
            ))
        
        # EDGE 3: Under 2.5 (si xGA < 1.0 et resist > 70)
        if xga_90 < 1.0 and resist_global > 70:
            edge = (1.5 - xga_90) * 10  # Approximation
            profitable.append(DefensiveEdge(
                market="Under 2.5 Goals",
                edge_pct=edge,
                confidence="MEDIUM",
                reasoning=f"Défense solide: xGA={xga_90:.2f}, resist={resist_global}",
                kelly_suggested=min(0.03, edge / 100 * 0.3)
            ))
        elif xga_90 > 2.0:
            avoid.append(f"Under 2.5 (xGA={xga_90:.2f} trop élevé)")
        
        # EDGE 4: GK Late Vulnerability
        if gk_late_sr < 60:
            edge = 70 - gk_late_sr  # vs save rate normal
            profitable.append(DefensiveEdge(
                market="Goal 76-90 vs this team",
                edge_pct=edge,
                confidence="MEDIUM",
                reasoning=f"GK faible en fin de match: SR 76-90 = {gk_late_sr:.1f}%",
                kelly_suggested=min(0.03, edge / 100 * 0.3)
            ))
        
        # EDGE 5: Set Piece Vulnerability
        if set_piece_vuln > 35:
            edge = set_piece_vuln - 25  # vs average 25%
            profitable.append(DefensiveEdge(
                market="Goal from Set Piece",
                edge_pct=edge,
                confidence="MEDIUM" if set_piece_vuln > 40 else "LOW",
                reasoning=f"Vulnérable sur SP: {set_piece_vuln:.1f}% des buts",
                kelly_suggested=min(0.02, edge / 100 * 0.2)
            ))
        
        # EDGE 6: Corners (si corners_total > 11)
        if corners_total > 11:
            profitable.append(DefensiveEdge(
                market="Over 10.5 Corners",
                edge_pct=(corners_total - 10) * 5,
                confidence="MEDIUM",
                reasoning=f"High corner games: {corners_total:.1f} avg",
                kelly_suggested=0.02
            ))
        elif corners_total < 9:
            avoid.append(f"Over 10.5 Corners (avg={corners_total:.1f})")
        
        # EDGE 7: Overperformance → Regression
        if overperform < -2:  # Concède beaucoup moins que xGA
            avoid.append(f"Clean Sheet long terme (regression expected, overperform={overperform:.1f})")
        elif overperform > 2:  # Concède plus que xGA
            profitable.append(DefensiveEdge(
                market="Regression Play (fewer goals)",
                edge_pct=overperform * 2,
                confidence="LOW",
                reasoning=f"Underperforming: concède {overperform:.1f} buts > xGA, regression attendue",
                kelly_suggested=0.01
            ))
        
        # ═══════════════════════════════════════════════════════════════════════
        # CRÉER LE DNA
        # ═══════════════════════════════════════════════════════════════════════
        
        dna = TeamDNA(
            team_name=team_name,
            league=league,
            defensive_profile=def_profile,
            timing_profile=timing_profile,
            gk_profile=gk_profile,
            home_away_profile=ha_profile,
            xga_90=xga_90,
            ga_90=ga_90,
            cs_pct=cs_pct,
            overperform=overperform,
            resist_global=resist_global,
            early_pct=early_pct,
            mid_pct=mid_pct,
            late_pct=late_pct,
            gk_percentile=gk_percentile,
            gk_save_rate=gk_save_rate,
            gk_late_vulnerability=gk_late_sr,
            set_piece_vuln_pct=set_piece_vuln,
            corner_concede_rate=corners_against,
            def_discipline=def_discipline,
            def_cards_90=def_cards,
            def_transition_vuln=def_transition,
            corners_for_avg=corners_for,
            corners_against_avg=corners_against,
            corners_total_avg=corners_total,
            profitable_markets=profitable,
            avoid_markets=avoid,
        )
        
        # Générer le narratif
        dna.generate_narrative()
        
        # Fingerprint hash
        dna.fingerprint_hash = f"{def_profile.value}_{timing_profile.value}_{gk_profile.value}_{ha_profile}"
        
        return dna
    
    def compare_teams(self, team_a: str, team_b: str) -> Dict[str, Any]:
        """
        Compare deux équipes et identifie les frictions.
        
        Returns:
            Dict avec edges du matchup
        """
        dna_a = self.profile_team(team_a)
        dna_b = self.profile_team(team_b)
        
        friction = {
            'team_a': team_a,
            'team_b': team_b,
            'dna_a': dna_a.fingerprint_hash,
            'dna_b': dna_b.fingerprint_hash,
            'matchup_edges': []
        }
        
        # Friction: FORTRESS vs LEAKY
        if dna_a.defensive_profile == DefensiveProfile.FORTRESS and dna_b.defensive_profile in [DefensiveProfile.LEAKY, DefensiveProfile.CATASTROPHIC]:
            friction['matchup_edges'].append({
                'market': f'{team_a} Clean Sheet',
                'edge': '+HIGH',
                'reasoning': f'{team_a} FORTRESS vs {team_b} {dna_b.defensive_profile.value}'
            })
        
        # Friction: Late vulnerability both teams
        if dna_a.late_pct > 35 and dna_b.late_pct > 35:
            friction['matchup_edges'].append({
                'market': 'Late Goal (either team)',
                'edge': '+HIGH',
                'reasoning': f'Both teams vulnerable late: {team_a}={dna_a.late_pct:.1f}%, {team_b}={dna_b.late_pct:.1f}%'
            })
        
        # Friction: High corners game
        combined_corners = dna_a.corners_total_avg + dna_b.corners_total_avg - 10
        if combined_corners > 12:
            friction['matchup_edges'].append({
                'market': 'Over 10.5 Corners',
                'edge': '+MEDIUM',
                'reasoning': f'High corner teams: combined avg = {combined_corners:.1f}'
            })
        
        return friction


# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from data.loader import DefenseDataLoader
    
    # Charger les données
    print("Chargement des données...")
    loader = DefenseDataLoader()
    loader.load_all()
    
    # Créer le profiler
    profiler = TeamProfiler(loader)
    
    # Profiler Arsenal
    print("\n" + "=" * 100)
    print("🏰 PROFIL ADN DÉFENSIF - ARSENAL")
    print("=" * 100)
    
    arsenal_dna = profiler.profile_team('Arsenal')
    print(arsenal_dna.narrative)
    
    # Profiler une équipe faible
    print("\n" + "=" * 100)
    print("🏰 PROFIL ADN DÉFENSIF - Une équipe LEAKY")
    print("=" * 100)
    
    # Trouver une équipe LEAKY ou CATASTROPHIC
    for team in ['Bochum', 'Lecce', 'Montpellier', 'Metz']:
        try:
            dna = profiler.profile_team(team)
            if dna.defensive_profile in [DefensiveProfile.LEAKY, DefensiveProfile.CATASTROPHIC]:
                print(dna.narrative)
                break
        except:
            continue
    
    # Comparer deux équipes
    print("\n" + "=" * 100)
    print("⚔️ FRICTION ANALYSIS: Arsenal vs Chelsea")
    print("=" * 100)
    
    friction = profiler.compare_teams('Arsenal', 'Chelsea')
    print(f"\n   {friction['team_a']} ({friction['dna_a']}) vs {friction['team_b']} ({friction['dna_b']})")
    print("\n   📊 MATCHUP EDGES:")
    for edge in friction['matchup_edges']:
        print(f"      • {edge['market']}: {edge['edge']} - {edge['reasoning']}")
