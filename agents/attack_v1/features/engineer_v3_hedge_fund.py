"""
═══════════════════════════════════════════════════════════════════════════════
🧬 ATTACK FEATURE ENGINEER V3.0 - HEDGE FUND GRADE
   DNA Offensif unique et actionable pour chaque équipe
═══════════════════════════════════════════════════════════════════════════════
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

class VolumeProfile(Enum):
    ELITE_ATTACK = "ELITE_ATTACK"      # xG/90 >= 2.5
    HIGH_VOLUME = "HIGH_VOLUME"        # xG/90 >= 2.0
    SOLID_ATTACK = "SOLID_ATTACK"      # xG/90 >= 1.5
    LOW_VOLUME = "LOW_VOLUME"          # xG/90 < 1.5

class EfficiencyProfile(Enum):
    CLINICAL = "CLINICAL"              # Overperform xG > 3
    EFFICIENT = "EFFICIENT"            # Overperform 0-3
    AVERAGE = "AVERAGE"                # -2 to 0
    WASTEFUL = "WASTEFUL"              # Underperform < -2

class TimingProfile(Enum):
    LATE_GAME_KILLER = "LATE_GAME_KILLER"  # 35%+ goals après 76'
    FAST_STARTER = "FAST_STARTER"          # 30%+ goals avant 30'
    DIESEL = "DIESEL"                       # 65%+ goals en H2
    FADES_LATE = "FADES_LATE"              # 35%- goals en H2
    CONSISTENT = "CONSISTENT"               # Équilibré

class DependencyProfile(Enum):
    MVP_DEPENDENT = "MVP_DEPENDENT"    # 40%+ sur un joueur
    TOP3_HEAVY = "TOP3_HEAVY"          # 70%+ sur top 3
    WELL_SPREAD = "WELL_SPREAD"        # Distribution équilibrée

class StyleProfile(Enum):
    HIGH_PRESS = "HIGH_PRESS"
    COUNTER_ATTACK = "COUNTER_ATTACK"
    PATIENT_BUILD = "PATIENT_BUILD"
    HYBRID = "HYBRID"

class GamestateProfile(Enum):
    COMEBACK_KING = "COMEBACK_KING"    # xG/90 >= 2.5 quand mené
    GAME_MANAGER = "GAME_MANAGER"      # xG/90 <= 1.0 quand mène
    FRONTRUNNER = "FRONTRUNNER"        # Domine quand mène
    NEUTRAL = "NEUTRAL"

@dataclass
class BettingEdge:
    market: str
    edge_pct: float
    confidence: str  # HIGH, MEDIUM, LOW
    reasoning: str

@dataclass
class AttackDNA:
    """DNA Offensif complet - Hedge Fund Grade"""
    team_name: str
    league: str
    
    # Fingerprint unique
    fingerprint_hash: str = ""
    fingerprint_tags: List[str] = field(default_factory=list)
    
    # Profiles
    volume_profile: VolumeProfile = VolumeProfile.SOLID_ATTACK
    efficiency_profile: EfficiencyProfile = EfficiencyProfile.AVERAGE
    timing_profile: TimingProfile = TimingProfile.CONSISTENT
    dependency_profile: DependencyProfile = DependencyProfile.WELL_SPREAD
    style_profile: StyleProfile = StyleProfile.HYBRID
    gamestate_profile: GamestateProfile = GamestateProfile.NEUTRAL
    
    # Core Metrics
    xg_90: float = 0.0
    goals_90: float = 0.0
    xg_overperformance: float = 0.0
    matches_played: int = 0
    
    # Timing Metrics
    late_goals_pct: float = 0.0
    early_goals_pct: float = 0.0
    h1_goals_pct: float = 0.0
    h2_goals_pct: float = 0.0
    
    # Dependency Metrics
    mvp_name: str = ""
    mvp_goals: int = 0
    mvp_share: float = 0.0
    top3_share: float = 0.0
    unique_scorers: int = 0
    
    # Gamestate Metrics
    xg_90_trailing: float = 0.0
    xg_90_leading: float = 0.0
    xg_90_drawing: float = 0.0
    
    # Style Metrics
    pressing_style: str = ""
    fast_attack_pct: float = 0.0
    counter_attack_goals: int = 0
    
    # Form
    form_last_5: str = ""
    is_hot_streak: bool = False
    is_cold_streak: bool = False
    
    # Betting Intelligence
    edges: List[BettingEdge] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    avoid_markets: List[str] = field(default_factory=list)


class AttackFeatureEngineerV3:
    """Engineer V3.0 - Génère des DNA uniques Hedge Fund Grade"""
    
    def __init__(self, loader):
        self.loader = loader
        self.dna_cache: Dict[str, AttackDNA] = {}
    
    def engineer_all(self) -> None:
        """Génère le DNA pour toutes les équipes"""
        print("="*80)
        print("🧬 ATTACK DNA ENGINEER V3.0 - HEDGE FUND GRADE")
        print("="*80)
        
        for team_name in self.loader.teams.keys():
            dna = self._generate_dna(team_name)
            if dna:
                self.dna_cache[team_name] = dna
        
        print(f"✅ DNA généré pour {len(self.dna_cache)} équipes")
    
    def get_dna(self, team_name: str) -> Optional[AttackDNA]:
        """Récupère le DNA d'une équipe"""
        return self.dna_cache.get(team_name)
    
    def _generate_dna(self, team_name: str) -> Optional[AttackDNA]:
        """Génère le DNA complet pour une équipe"""
        team = self.loader.get_team(team_name)
        ctx = self.loader.context_dna.get(team_name, {})
        
        if not team:
            return None
        
        dna = AttackDNA(
            team_name=team_name,
            league=team.league,
            matches_played=ctx.get('matches', 0)
        )
        
        tags = []
        
        # ═══════════════════════════════════════════════════════════════
        # 1. VOLUME & EFFICIENCY
        # ═══════════════════════════════════════════════════════════════
        dna.xg_90 = ctx.get('history', {}).get('xg_90', 0)
        dna.goals_90 = team.total_goals / max(ctx.get('matches', 1), 1)
        dna.xg_overperformance = ctx.get('variance', {}).get('xg_overperformance', 0)
        
        # Volume Profile
        if dna.xg_90 >= 2.5:
            dna.volume_profile = VolumeProfile.ELITE_ATTACK
            tags.append("ELITE_ATTACK")
        elif dna.xg_90 >= 2.0:
            dna.volume_profile = VolumeProfile.HIGH_VOLUME
            tags.append("HIGH_VOLUME")
        elif dna.xg_90 >= 1.5:
            dna.volume_profile = VolumeProfile.SOLID_ATTACK
        else:
            dna.volume_profile = VolumeProfile.LOW_VOLUME
            tags.append("LOW_VOLUME")
        
        # Efficiency Profile
        if dna.xg_overperformance > 3:
            dna.efficiency_profile = EfficiencyProfile.CLINICAL
            tags.append("CLINICAL")
            dna.edges.append(BettingEdge(
                market="Over Goals",
                edge_pct=10.0,
                confidence="HIGH",
                reasoning=f"Overperform xG by {dna.xg_overperformance:.1f}"
            ))
        elif dna.xg_overperformance > 0:
            dna.efficiency_profile = EfficiencyProfile.EFFICIENT
        elif dna.xg_overperformance > -3:
            dna.efficiency_profile = EfficiencyProfile.AVERAGE
        else:
            dna.efficiency_profile = EfficiencyProfile.WASTEFUL
            tags.append("WASTEFUL")
            dna.warnings.append(f"Underperform xG by {abs(dna.xg_overperformance):.1f}")
        
        # ═══════════════════════════════════════════════════════════════
        # 2. TIMING DNA
        # ═══════════════════════════════════════════════════════════════
        timing = ctx.get('context_dna', {}).get('timing', {})
        total_goals = sum(t.get('goals', 0) for t in timing.values())
        
        if total_goals > 0:
            late = timing.get('76+', {}).get('goals', 0)
            early = timing.get('1-15', {}).get('goals', 0) + timing.get('16-30', {}).get('goals', 0)
            h1 = sum(timing.get(p, {}).get('goals', 0) for p in ['1-15', '16-30', '31-45'])
            h2 = sum(timing.get(p, {}).get('goals', 0) for p in ['46-60', '61-75', '76+'])
            
            dna.late_goals_pct = late / total_goals * 100
            dna.early_goals_pct = early / total_goals * 100
            dna.h1_goals_pct = h1 / total_goals * 100
            dna.h2_goals_pct = h2 / total_goals * 100
            
            if dna.late_goals_pct >= 35:
                dna.timing_profile = TimingProfile.LATE_GAME_KILLER
                tags.append("LATE_GAME_KILLER")
                dna.edges.append(BettingEdge(
                    market="Goal 76-90",
                    edge_pct=15.0,
                    confidence="HIGH",
                    reasoning=f"{dna.late_goals_pct:.0f}% goals après 76'"
                ))
            elif dna.early_goals_pct >= 30:
                dna.timing_profile = TimingProfile.FAST_STARTER
                tags.append("FAST_STARTER")
                dna.edges.append(BettingEdge(
                    market="Goal 0-30",
                    edge_pct=12.0,
                    confidence="MEDIUM",
                    reasoning=f"{dna.early_goals_pct:.0f}% goals avant 30'"
                ))
            
            if dna.h2_goals_pct >= 65:
                tags.append("DIESEL")
            elif dna.h2_goals_pct <= 35:
                tags.append("FADES_LATE")
                dna.warnings.append("Fades in second half")
        
        # ═══════════════════════════════════════════════════════════════
        # 3. DEPENDENCY DNA
        # ═══════════════════════════════════════════════════════════════
        if team.players:
            top_scorer = max(team.players, key=lambda p: p.goals)
            top3 = sorted(team.players, key=lambda p: p.goals, reverse=True)[:3]
            
            dna.mvp_name = top_scorer.player_name
            dna.mvp_goals = top_scorer.goals
            dna.mvp_share = top_scorer.goals / max(team.total_goals, 1) * 100
            dna.top3_share = sum(p.goals for p in top3) / max(team.total_goals, 1) * 100
            dna.unique_scorers = len([p for p in team.players if p.goals > 0])
            
            if dna.mvp_share >= 40:
                dna.dependency_profile = DependencyProfile.MVP_DEPENDENT
                surname = top_scorer.player_name.split()[-1].upper()
                tags.append(f"{surname}_DEPENDENT")
                dna.warnings.append(f"Sans {top_scorer.player_name}: -40% threat")
            elif dna.top3_share >= 70:
                dna.dependency_profile = DependencyProfile.TOP3_HEAVY
            else:
                dna.dependency_profile = DependencyProfile.WELL_SPREAD
                dna.edges.append(BettingEdge(
                    market="Team Total Goals",
                    edge_pct=5.0,
                    confidence="MEDIUM",
                    reasoning="Goals from multiple sources"
                ))
        
        # ═══════════════════════════════════════════════════════════════
        # 4. STYLE DNA
        # ═══════════════════════════════════════════════════════════════
        dna.pressing_style = ctx.get('history', {}).get('pressing_style', '')
        
        if dna.pressing_style == 'HIGH_PRESS':
            dna.style_profile = StyleProfile.HIGH_PRESS
            tags.append("HIGH_PRESS")
        
        speed = team.attack_speed_data
        if speed:
            fast = speed.get('Fast', {}).get('goals', 0)
            total_speed = sum(s.get('goals', 0) for s in speed.values())
            if total_speed > 0:
                dna.fast_attack_pct = fast / total_speed * 100
                if dna.fast_attack_pct >= 20:
                    dna.style_profile = StyleProfile.COUNTER_ATTACK
                    tags.append("COUNTER_ATTACK")
                elif dna.fast_attack_pct <= 5:
                    tags.append("PATIENT_BUILD")
        
        # ═══════════════════════════════════════════════════════════════
        # 5. GAMESTATE DNA
        # ═══════════════════════════════════════════════════════════════
        gamestate = team.gamestate_data
        if gamestate:
            dna.xg_90_trailing = gamestate.get('Goal diff -1', {}).get('xG_90', 0)
            dna.xg_90_leading = gamestate.get('Goal diff +1', {}).get('xG_90', 0)
            dna.xg_90_drawing = gamestate.get('Goal diff 0', {}).get('xG_90', 0)
            
            if dna.xg_90_trailing >= 2.5:
                dna.gamestate_profile = GamestateProfile.COMEBACK_KING
                tags.append("COMEBACK_KING")
                dna.edges.append(BettingEdge(
                    market="Next Goal when trailing",
                    edge_pct=12.0,
                    confidence="HIGH",
                    reasoning=f"xG/90={dna.xg_90_trailing:.1f} when behind"
                ))
            
            if dna.xg_90_leading <= 1.0:
                tags.append("GAME_MANAGER")
        
        # ═══════════════════════════════════════════════════════════════
        # 6. FORM DNA
        # ═══════════════════════════════════════════════════════════════
        dna.form_last_5 = ctx.get('momentum_dna', {}).get('form_last_5', '')
        if dna.form_last_5:
            wins = dna.form_last_5.count('W')
            losses = dna.form_last_5.count('L')
            
            if wins >= 4:
                dna.is_hot_streak = True
                tags.append("HOT_STREAK")
            elif losses >= 3:
                dna.is_cold_streak = True
                tags.append("COLD_STREAK")
                dna.warnings.append(f"Poor form: {dna.form_last_5}")
        
        # ═══════════════════════════════════════════════════════════════
        # FINAL FINGERPRINT
        # ═══════════════════════════════════════════════════════════════
        dna.fingerprint_tags = tags
        dna.fingerprint_hash = "_".join(tags) if tags else "NEUTRAL"
        
        return dna
    
    def compare_attack(self, team_a: str, team_b: str) -> Dict:
        """Compare deux équipes offensivement"""
        dna_a = self.get_dna(team_a)
        dna_b = self.get_dna(team_b)
        
        if not dna_a or not dna_b:
            return {}
        
        comparison = {
            "team_a": team_a,
            "team_b": team_b,
            "dna_a": dna_a.fingerprint_hash,
            "dna_b": dna_b.fingerprint_hash,
            "xg_90_diff": dna_a.xg_90 - dna_b.xg_90,
            "combined_edges": [],
            "matchup_insights": []
        }
        
        # Combine edges
        comparison["combined_edges"] = dna_a.edges + dna_b.edges
        
        # Matchup insights
        if dna_a.timing_profile == TimingProfile.LATE_GAME_KILLER or dna_b.timing_profile == TimingProfile.LATE_GAME_KILLER:
            comparison["matchup_insights"].append({
                "market": "Late Goal (either team)",
                "edge": "HIGH",
                "reasoning": "At least one team is a late game killer"
            })
        
        if dna_a.xg_90 + dna_b.xg_90 >= 4.0:
            comparison["matchup_insights"].append({
                "market": "Over 2.5 Goals",
                "edge": "HIGH",
                "reasoning": f"Combined xG/90: {dna_a.xg_90 + dna_b.xg_90:.1f}"
            })
        
        return comparison


# Test
if __name__ == "__main__":
    import sys
    sys.path.insert(0, '/home/Mon_ps')
    from agents.attack_v1.data.loader import AttackDataLoader
    
    loader = AttackDataLoader()
    loader.load_all()
    
    engineer = AttackFeatureEngineerV3(loader)
    engineer.engineer_all()
    
    # Test Liverpool
    dna = engineer.get_dna('Liverpool')
    if dna:
        print(f"\n🧬 {dna.team_name}")
        print(f"   Fingerprint: {dna.fingerprint_hash}")
        print(f"   Volume: {dna.volume_profile.value}")
        print(f"   Efficiency: {dna.efficiency_profile.value}")
        print(f"   Timing: {dna.timing_profile.value}")
        print(f"   Dependency: {dna.dependency_profile.value}")
        print(f"   Edges: {[e.market for e in dna.edges]}")
