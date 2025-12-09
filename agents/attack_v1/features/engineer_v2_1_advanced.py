"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🧬 FEATURE ENGINEER V2.1 ADVANCED - TEAM-CENTRIC HEDGE FUND GRADE           ║
║                                                                              ║
║  PHILOSOPHIE MON_PS:                                                         ║
║  • ÉQUIPE au centre (comme un trou noir)                                    ║
║  • Chaque équipe = 1 ADN = 1 empreinte digitale UNIQUE                      ║
║  • Les marchés sont des CONSÉQUENCES de l'ADN, pas l'inverse                ║
║                                                                              ║
║  NOUVELLES DIMENSIONS V2.1:                                                  ║
║  ═══════════════════════════════════════════════════════════════════════════ ║
║  🎯 11. NP-CLINICAL DNA:                                                     ║
║     • team_np_overperformance = somme NPG - NPxG équipe                      ║
║     • true_clinical_players, penalty_inflated_players                        ║
║     • team_np_profile: CLINICAL_TEAM, PENALTY_RELIANT, WASTEFUL_TEAM         ║
║                                                                              ║
║  🔗 12. CREATIVITY CHAIN DNA:                                                ║
║     • buildup_architects (ratio >= 3.0)                                      ║
║     • finisher_only_players (ratio < 1.0)                                    ║
║     • creative_dependency_count → Impact sur FINISHER_ONLY si absents        ║
║     • creative_dependency_profile: HIGH_DEPENDENCY, MODERATE, DISTRIBUTED    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
sys.path.insert(0, '/home/Mon_ps')

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json

from agents.attack_v1.data.loader_v5_2_extended import (
    AttackDataLoaderV52Extended,
    PlayerFullProfile2025Extended,
    TeamProfile2025Extended
)

DATA_DIR = Path('/home/Mon_ps/data')


# ═══════════════════════════════════════════════════════════════════════════════
# TEAM ATTACK DNA V2.1 - AVEC NP-CLINICAL + CREATIVITY CHAIN
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TeamAttackDNAv21:
    """
    ADN OFFENSIF COMPLET d'une équipe - VERSION 2.1 ADVANCED
    
    12 dimensions dont 2 nouvelles:
    • 11. NP-CLINICAL DNA (finition équipe sans pénos)
    • 12. CREATIVITY CHAIN DNA (dépendance créative)
    """
    team_name: str = ""
    league: str = ""

    # ═══════════════════════════════════════════════════════════════════════════
    # 1. VOLUME DNA - Puissance de feu
    # ═══════════════════════════════════════════════════════════════════════════
    total_goals: int = 0
    total_xG: float = 0.0
    goals_per_match: float = 0.0
    xG_per_match: float = 0.0
    xG_overperformance: float = 0.0
    volume_profile: str = ""  # HIGH_SCORING, AVERAGE, LOW_SCORING
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 2. TIMING DNA - Quand l'équipe marque
    # ═══════════════════════════════════════════════════════════════════════════
    goals_1h: int = 0
    goals_2h: int = 0
    pct_1h: float = 0.0
    pct_2h: float = 0.0
    pct_early: float = 0.0
    pct_clutch: float = 0.0
    goals_by_period: Dict[str, int] = field(default_factory=dict)
    timing_profile: str = ""  # EARLY_STARTERS, DIESEL, CLUTCH_TEAM, BALANCED
    peak_period: str = ""
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 3. DEPENDENCY DNA - Concentration des buts
    # ═══════════════════════════════════════════════════════════════════════════
    top_scorer: str = ""
    top_scorer_goals: int = 0
    top_scorer_share: float = 0.0
    top_3_share: float = 0.0
    scorers_count: int = 0
    dependency_profile: str = ""  # MVP_DEPENDENT, TOP3_DEPENDENT, DISTRIBUTED
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 4. STYLE DNA - Comment l'équipe marque
    # ═══════════════════════════════════════════════════════════════════════════
    goals_open_play: int = 0
    goals_set_piece: int = 0
    goals_penalty: int = 0
    goals_header: int = 0
    pct_open_play: float = 0.0
    pct_set_piece: float = 0.0
    pct_penalty: float = 0.0
    pct_header: float = 0.0
    style_profile: str = ""  # OPEN_PLAY_DOMINANT, SET_PIECE_THREAT, AERIAL_THREAT, PENALTY_RELIANT
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 5. HOME/AWAY DNA - Performances domicile/extérieur
    # ═══════════════════════════════════════════════════════════════════════════
    goals_home: int = 0
    goals_away: int = 0
    home_away_ratio: float = 1.0
    home_away_profile: str = ""  # FORTRESS, ROAD_WARRIORS, BALANCED
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 6. EFFICIENCY DNA - Qualité de finition équipe
    # ═══════════════════════════════════════════════════════════════════════════
    team_conversion_rate: float = 0.0
    elite_finishers_count: int = 0
    clinical_count: int = 0
    wasteful_count: int = 0
    efficiency_profile: str = ""  # CLINICAL_TEAM, WASTEFUL_TEAM, AVERAGE
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 7. SUPER_SUB DNA - Impact des remplaçants
    # ═══════════════════════════════════════════════════════════════════════════
    super_subs: List[str] = field(default_factory=list)
    super_sub_goals: int = 0
    super_sub_pct: float = 0.0
    bench_strength: str = ""  # STRONG_BENCH, AVERAGE_BENCH, WEAK_BENCH
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 8. PENALTY DNA - Fiabilité aux penalties
    # ═══════════════════════════════════════════════════════════════════════════
    penalty_taker: str = ""
    penalty_goals: int = 0
    penalty_reliability: str = ""  # RELIABLE, AVERAGE, NO_DATA
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 9. CREATIVITY DNA - Création de jeu
    # ═══════════════════════════════════════════════════════════════════════════
    total_assists: int = 0
    total_xA: float = 0.0
    top_creator: str = ""
    elite_creators_count: int = 0
    creativity_profile: str = ""  # CREATIVE_HUB, INDIVIDUAL_BRILLIANCE, COLLECTIVE
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 10. FORM DNA - Tendance actuelle
    # ═══════════════════════════════════════════════════════════════════════════
    hot_streak_players: List[str] = field(default_factory=list)
    cold_streak_players: List[str] = field(default_factory=list)
    value_regression_candidates: List[str] = field(default_factory=list)
    team_form_trend: str = ""  # HOT, STABLE, DECLINING
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🆕 11. NP-CLINICAL DNA (NOUVEAU V2.1)
    # La VRAIE efficacité de finition sans les pénaltys
    # ═══════════════════════════════════════════════════════════════════════════
    team_np_goals: int = 0                      # Total NPG équipe
    team_np_xG: float = 0.0                     # Total NPxG équipe
    team_np_overperformance: float = 0.0        # NPG - NPxG
    true_clinical_players: List[str] = field(default_factory=list)   # np_overperf >= +3
    clinical_players: List[str] = field(default_factory=list)        # np_overperf >= +1.5
    penalty_inflated_players: List[str] = field(default_factory=list)
    np_wasteful_players: List[str] = field(default_factory=list)
    team_np_profile: str = ""                   # CLINICAL_TEAM, PENALTY_RELIANT, WASTEFUL_TEAM, AVERAGE
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🆕 12. CREATIVITY CHAIN DNA (NOUVEAU V2.1)
    # Dépendance créative - Impact sur FINISHER_ONLY si architectes absents
    # ═══════════════════════════════════════════════════════════════════════════
    buildup_architects: List[str] = field(default_factory=list)      # ratio >= 3.0
    high_involvement_players: List[str] = field(default_factory=list) # ratio >= 2.0
    finisher_only_players: List[str] = field(default_factory=list)   # ratio < 1.0
    playmakers: List[str] = field(default_factory=list)              # buildup_ratio >= 0.6
    box_crashers: List[str] = field(default_factory=list)            # buildup_ratio < 0.4
    creative_dependency_count: int = 0          # Nombre de joueurs avec buildup >= 0.6
    creative_dependency_profile: str = ""       # HIGH_DEPENDENCY, MODERATE, DISTRIBUTED
    total_xGChain: float = 0.0
    total_xGBuildup: float = 0.0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PROFIL NARRATIF
    # ═══════════════════════════════════════════════════════════════════════════
    narrative_profile: str = ""
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MARCHÉS EXPLOITABLES
    # ═══════════════════════════════════════════════════════════════════════════
    profitable_markets: List[Dict] = field(default_factory=list)
    markets_to_avoid: List[Dict] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE ENGINEER V2.1 ADVANCED
# ═══════════════════════════════════════════════════════════════════════════════

class FeatureEngineerV21Advanced:
    """
    Feature Engineer V2.1 ADVANCED - TEAM-CENTRIC
    
    Construit l'ADN COMPLET de chaque équipe avec 12 dimensions
    dont 2 nouvelles: NP-CLINICAL DNA et CREATIVITY CHAIN DNA
    """
    
    def __init__(self):
        self.loader = AttackDataLoaderV52Extended()
        self.team_dna: Dict[str, TeamAttackDNAv21] = {}
        self.matches_played = 13  # À ajuster selon la saison
        
    def initialize(self) -> None:
        """Initialise le Feature Engineer"""
        print("=" * 80)
        print("🎯 FEATURE ENGINEER V2.1 ADVANCED - TEAM-CENTRIC HEDGE FUND GRADE")
        print("=" * 80)
        
        self.loader.load_all()
        self._build_all_team_dna()
        
        print(f"\n✅ {len(self.team_dna)} équipes avec ADN COMPLET V2.1")
        
    def _build_all_team_dna(self) -> None:
        """Construit l'ADN de toutes les équipes"""
        print("\n📊 Construction ADN par équipe...")
        
        for team_name, team in self.loader.teams.items():
            dna = self._build_team_dna(team)
            self.team_dna[team_name] = dna
            
    def _build_team_dna(self, team: TeamProfile2025Extended) -> TeamAttackDNAv21:
        """Construit l'ADN complet d'une équipe"""
        dna = TeamAttackDNAv21(
            team_name=team.team_name,
            league=team.league
        )
        
        players = team.players
        scorers = [p for p in players if p.goals > 0]
        
        # ═══════════════════════════════════════════════════════════════════════
        # 1. VOLUME DNA
        # ═══════════════════════════════════════════════════════════════════════
        dna.total_goals = sum(p.goals for p in players)
        dna.total_xG = sum(p.xG for p in players)
        dna.goals_per_match = dna.total_goals / self.matches_played if self.matches_played > 0 else 0
        dna.xG_per_match = dna.total_xG / self.matches_played if self.matches_played > 0 else 0
        dna.xG_overperformance = dna.total_goals - dna.total_xG
        
        if dna.goals_per_match >= 2.2:
            dna.volume_profile = "HIGH_SCORING"
        elif dna.goals_per_match >= 1.2:
            dna.volume_profile = "AVERAGE"
        else:
            dna.volume_profile = "LOW_SCORING"
            
        # ═══════════════════════════════════════════════════════════════════════
        # 2. TIMING DNA
        # ═══════════════════════════════════════════════════════════════════════
        dna.goals_1h = sum(p.goals_1h for p in players)
        dna.goals_2h = sum(p.goals_2h for p in players)
        
        if dna.total_goals > 0:
            dna.pct_1h = (dna.goals_1h / dna.total_goals) * 100
            dna.pct_2h = (dna.goals_2h / dna.total_goals) * 100
            
        # Par période
        dna.goals_by_period = {
            '0-15': sum(p.goals_0_15 for p in players),
            '16-30': sum(p.goals_16_30 for p in players),
            '31-45': sum(p.goals_31_45 for p in players),
            '46-60': sum(p.goals_46_60 for p in players),
            '61-75': sum(p.goals_61_75 for p in players),
            '76-90': sum(p.goals_76_90 for p in players),
            '90+': sum(p.goals_90_plus for p in players)
        }
        
        clutch = dna.goals_by_period.get('76-90', 0) + dna.goals_by_period.get('90+', 0)
        early = dna.goals_by_period.get('0-15', 0)
        
        if dna.total_goals > 0:
            dna.pct_clutch = (clutch / dna.total_goals) * 100
            dna.pct_early = (early / dna.total_goals) * 100
            
        # Peak period
        if dna.goals_by_period:
            dna.peak_period = max(dna.goals_by_period, key=dna.goals_by_period.get)
            
        # Timing profile
        if dna.pct_2h >= 65:
            dna.timing_profile = "DIESEL"
        elif dna.pct_1h >= 60:
            dna.timing_profile = "EARLY_STARTERS"
        elif dna.pct_clutch >= 25:
            dna.timing_profile = "CLUTCH_TEAM"
        else:
            dna.timing_profile = "BALANCED"
            
        # ═══════════════════════════════════════════════════════════════════════
        # 3. DEPENDENCY DNA
        # ═══════════════════════════════════════════════════════════════════════
        if scorers:
            top_scorers = sorted(scorers, key=lambda p: -p.goals)[:3]
            dna.top_scorer = top_scorers[0].player_name
            dna.top_scorer_goals = top_scorers[0].goals
            dna.top_scorer_share = (dna.top_scorer_goals / dna.total_goals * 100) if dna.total_goals > 0 else 0
            dna.top_3_share = (sum(p.goals for p in top_scorers) / dna.total_goals * 100) if dna.total_goals > 0 else 0
            dna.scorers_count = len(scorers)
            
            if dna.top_scorer_share >= 40:
                dna.dependency_profile = "MVP_DEPENDENT"
            elif dna.top_3_share >= 70:
                dna.dependency_profile = "TOP3_DEPENDENT"
            else:
                dna.dependency_profile = "DISTRIBUTED"
                
        # ═══════════════════════════════════════════════════════════════════════
        # 4. STYLE DNA
        # ═══════════════════════════════════════════════════════════════════════
        dna.goals_open_play = sum(p.goals_open_play for p in players)
        dna.goals_set_piece = sum(p.goals_corner + p.goals_set_piece for p in players)
        dna.goals_penalty = sum(p.penalty_goals for p in players)
        dna.goals_header = sum(p.goals_header for p in players)
        
        if dna.total_goals > 0:
            dna.pct_open_play = (dna.goals_open_play / dna.total_goals) * 100
            dna.pct_set_piece = (dna.goals_set_piece / dna.total_goals) * 100
            dna.pct_penalty = (dna.goals_penalty / dna.total_goals) * 100
            dna.pct_header = (dna.goals_header / dna.total_goals) * 100
            
        if dna.pct_set_piece >= 25:
            dna.style_profile = "SET_PIECE_THREAT"
        elif dna.pct_header >= 20:
            dna.style_profile = "AERIAL_THREAT"
        elif dna.pct_penalty >= 15:
            dna.style_profile = "PENALTY_RELIANT"
        else:
            dna.style_profile = "OPEN_PLAY_DOMINANT"
            
        # ═══════════════════════════════════════════════════════════════════════
        # 5. HOME/AWAY DNA
        # ═══════════════════════════════════════════════════════════════════════
        dna.goals_home = sum(p.goals_home for p in players)
        dna.goals_away = sum(p.goals_away for p in players)
        
        if dna.goals_away > 0:
            dna.home_away_ratio = dna.goals_home / dna.goals_away
        elif dna.goals_home > 0:
            dna.home_away_ratio = 5.0
            
        if dna.home_away_ratio >= 2.5:
            dna.home_away_profile = "FORTRESS"
        elif dna.home_away_ratio <= 0.6:
            dna.home_away_profile = "ROAD_WARRIORS"
        else:
            dna.home_away_profile = "BALANCED"
            
        # ═══════════════════════════════════════════════════════════════════════
        # 6. EFFICIENCY DNA
        # ═══════════════════════════════════════════════════════════════════════
        total_shots = sum(p.shots for p in players)
        if total_shots > 0:
            dna.team_conversion_rate = (dna.total_goals / total_shots) * 100
            
        dna.elite_finishers_count = len([p for p in players if p.shot_quality == "ELITE_FINISHER"])
        dna.clinical_count = len([p for p in players if p.shot_quality in ["ELITE_FINISHER", "CLINICAL"]])
        dna.wasteful_count = len([p for p in players if p.shot_quality == "WASTEFUL"])
        
        if dna.elite_finishers_count >= 2 or dna.team_conversion_rate >= 15:
            dna.efficiency_profile = "CLINICAL_TEAM"
        elif dna.wasteful_count >= 3 or dna.team_conversion_rate < 10:
            dna.efficiency_profile = "WASTEFUL_TEAM"
        else:
            dna.efficiency_profile = "AVERAGE"
            
        # ═══════════════════════════════════════════════════════════════════════
        # 7. SUPER_SUB DNA
        # ═══════════════════════════════════════════════════════════════════════
        super_subs = [p for p in players if p.playing_time_profile == "SUPER_SUB" and p.goals >= 2]
        dna.super_subs = [p.player_name for p in super_subs]
        dna.super_sub_goals = sum(p.goals for p in super_subs)
        dna.super_sub_pct = (dna.super_sub_goals / dna.total_goals * 100) if dna.total_goals > 0 else 0
        
        if dna.super_sub_pct >= 15 or len(dna.super_subs) >= 2:
            dna.bench_strength = "STRONG_BENCH"
        elif dna.super_sub_pct >= 5 or len(dna.super_subs) >= 1:
            dna.bench_strength = "AVERAGE_BENCH"
        else:
            dna.bench_strength = "WEAK_BENCH"
            
        # ═══════════════════════════════════════════════════════════════════════
        # 8. PENALTY DNA
        # ═══════════════════════════════════════════════════════════════════════
        penalty_takers = [p for p in players if p.is_penalty_taker]
        if penalty_takers:
            top_taker = max(penalty_takers, key=lambda p: p.penalty_goals)
            dna.penalty_taker = top_taker.player_name
            dna.penalty_goals = top_taker.penalty_goals
            dna.penalty_reliability = "RELIABLE" if dna.penalty_goals >= 3 else "AVERAGE"
        else:
            dna.penalty_reliability = "NO_DATA"
            
        # ═══════════════════════════════════════════════════════════════════════
        # 9. CREATIVITY DNA
        # ═══════════════════════════════════════════════════════════════════════
        dna.total_assists = sum(p.assists for p in players)
        dna.total_xA = sum(p.xA for p in players)
        
        elite_creators = [p for p in players if p.creativity_profile == "ELITE_CREATOR"]
        dna.elite_creators_count = len(elite_creators)
        if elite_creators:
            dna.top_creator = max(elite_creators, key=lambda p: p.xA).player_name
            
        if dna.elite_creators_count >= 2:
            dna.creativity_profile = "CREATIVE_HUB"
        elif dna.elite_creators_count == 1:
            dna.creativity_profile = "INDIVIDUAL_BRILLIANCE"
        else:
            dna.creativity_profile = "COLLECTIVE"
            
        # ═══════════════════════════════════════════════════════════════════════
        # 10. FORM DNA
        # ═══════════════════════════════════════════════════════════════════════
        dna.hot_streak_players = [p.player_name for p in players if p.finishing_trend == "HOT_STREAK" and p.goals >= 3]
        dna.cold_streak_players = [p.player_name for p in players if p.finishing_trend in ["COLD", "WASTEFUL"] and p.goals >= 2]
        dna.value_regression_candidates = [p.player_name for p in players if p.xG >= 4 and p.xG_overperformance <= -1.5]
        
        if len(dna.hot_streak_players) >= 2:
            dna.team_form_trend = "HOT"
        elif len(dna.cold_streak_players) >= 3:
            dna.team_form_trend = "DECLINING"
        else:
            dna.team_form_trend = "STABLE"
            
        # ═══════════════════════════════════════════════════════════════════════
        # 🆕 11. NP-CLINICAL DNA (NOUVEAU V2.1)
        # ═══════════════════════════════════════════════════════════════════════
        self._calculate_np_clinical_dna(dna, players)
        
        # ═══════════════════════════════════════════════════════════════════════
        # 🆕 12. CREATIVITY CHAIN DNA (NOUVEAU V2.1)
        # ═══════════════════════════════════════════════════════════════════════
        self._calculate_creativity_chain_dna(dna, players)
        
        # ═══════════════════════════════════════════════════════════════════════
        # PROFIL NARRATIF
        # ═══════════════════════════════════════════════════════════════════════
        self._build_narrative(dna)
        
        # ═══════════════════════════════════════════════════════════════════════
        # MARCHÉS EXPLOITABLES
        # ═══════════════════════════════════════════════════════════════════════
        self._identify_profitable_markets(dna)
        
        return dna
        
    def _calculate_np_clinical_dna(self, dna: TeamAttackDNAv21, players: List[PlayerFullProfile2025Extended]) -> None:
        """
        🆕 Calcule le NP-CLINICAL DNA de l'équipe
        
        Profils:
        • CLINICAL_TEAM: team_np_overperf >= +3 OU 2+ TRUE_CLINICAL
        • PENALTY_RELIANT: pct_penalty >= 20% ET team_np_overperf < 0
        • WASTEFUL_TEAM: team_np_overperf <= -3 OU 3+ NP_WASTEFUL
        • AVERAGE: autres cas
        """
        # Totaux équipe
        dna.team_np_goals = sum(p.np_goals for p in players)
        dna.team_np_xG = sum(p.np_xG for p in players)
        dna.team_np_overperformance = dna.team_np_goals - dna.team_np_xG
        
        # Classification joueurs
        dna.true_clinical_players = [
            p.player_name for p in players 
            if p.np_clinical_profile == "TRUE_CLINICAL" and p.goals >= 3
        ]
        dna.clinical_players = [
            p.player_name for p in players 
            if p.np_clinical_profile in ["TRUE_CLINICAL", "CLINICAL"] and p.goals >= 3
        ]
        dna.penalty_inflated_players = [
            p.player_name for p in players 
            if p.np_clinical_profile == "PENALTY_INFLATED"
        ]
        dna.np_wasteful_players = [
            p.player_name for p in players 
            if p.np_clinical_profile == "WASTEFUL" and p.goals >= 2
        ]
        
        # Profil équipe
        if len(dna.true_clinical_players) >= 2 or dna.team_np_overperformance >= 3:
            dna.team_np_profile = "CLINICAL_TEAM"
        elif dna.pct_penalty >= 20 and dna.team_np_overperformance < 0:
            dna.team_np_profile = "PENALTY_RELIANT"
        elif len(dna.np_wasteful_players) >= 3 or dna.team_np_overperformance <= -3:
            dna.team_np_profile = "WASTEFUL_TEAM"
        else:
            dna.team_np_profile = "AVERAGE"
            
    def _calculate_creativity_chain_dna(self, dna: TeamAttackDNAv21, players: List[PlayerFullProfile2025Extended]) -> None:
        """
        🆕 Calcule le CREATIVITY CHAIN DNA de l'équipe
        
        Profils creative_dependency:
        • HIGH_DEPENDENCY: creative_dependency_count <= 2 (si 2+ BUILDUP_ARCHITECT absents, FINISHER_ONLY meurt)
        • MODERATE: 3-4 joueurs avec buildup >= 0.6
        • DISTRIBUTED: 5+ joueurs avec buildup >= 0.6
        """
        # xGChain et xGBuildup totaux
        dna.total_xGChain = sum(p.xGChain for p in players)
        dna.total_xGBuildup = sum(p.xGBuildup for p in players)
        
        # Classification joueurs
        dna.buildup_architects = [
            p.player_name for p in players 
            if p.chain_profile == "BUILDUP_ARCHITECT" and p.xGChain >= 3
        ]
        dna.high_involvement_players = [
            p.player_name for p in players 
            if p.chain_profile == "HIGH_INVOLVEMENT" and p.xGChain >= 2
        ]
        dna.finisher_only_players = [
            p.player_name for p in players 
            if p.chain_profile == "FINISHER_ONLY" and p.goals >= 3
        ]
        dna.playmakers = [
            p.player_name for p in players 
            if p.buildup_profile == "PLAYMAKER" and p.xGChain >= 2
        ]
        dna.box_crashers = [
            p.player_name for p in players 
            if p.buildup_profile == "BOX_CRASHER" and p.goals >= 3
        ]
        
        # Creative dependency count = joueurs clés pour la construction
        dna.creative_dependency_count = len([
            p for p in players 
            if p.buildup_ratio >= 0.6 and p.xGChain >= 2
        ])
        
        # Profil dépendance créative
        if dna.creative_dependency_count <= 2:
            dna.creative_dependency_profile = "HIGH_DEPENDENCY"
        elif dna.creative_dependency_count <= 4:
            dna.creative_dependency_profile = "MODERATE"
        else:
            dna.creative_dependency_profile = "DISTRIBUTED"
            
    def _build_narrative(self, dna: TeamAttackDNAv21) -> None:
        """Construit le profil narratif de l'équipe"""
        parts = []
        
        # Volume
        if dna.volume_profile == "HIGH_SCORING":
            parts.append(f"Machine offensive ({dna.goals_per_match:.1f} buts/match)")
            dna.strengths.append("Puissance de feu élevée")
            
        # Timing
        if dna.timing_profile == "DIESEL":
            parts.append(f"Diesel ({dna.pct_2h:.0f}% buts en 2H)")
            dna.strengths.append("Monte en puissance")
        elif dna.timing_profile == "CLUTCH_TEAM":
            parts.append(f"Clutch ({dna.pct_clutch:.0f}% après 75')")
            dna.strengths.append("Décisifs en fin de match")
        elif dna.timing_profile == "EARLY_STARTERS":
            parts.append(f"Fast Starters ({dna.pct_1h:.0f}% en 1H)")
            dna.strengths.append("Démarrage rapide")
            
        # Dependency
        if dna.dependency_profile == "MVP_DEPENDENT":
            parts.append(f"Dépendant de {dna.top_scorer} ({dna.top_scorer_share:.0f}%)")
            dna.weaknesses.append(f"Trop dépendant de {dna.top_scorer}")
        elif dna.dependency_profile == "DISTRIBUTED":
            parts.append(f"Attaque distribuée ({dna.scorers_count} buteurs)")
            dna.strengths.append("Menace variée")
            
        # Super subs
        if dna.bench_strength == "STRONG_BENCH":
            parts.append(f"Banc impactant ({', '.join(dna.super_subs)})")
            dna.strengths.append("Impact des remplaçants")
            
        # 🆕 NP-Clinical
        if dna.team_np_profile == "CLINICAL_TEAM":
            parts.append(f"Cliniques sans pénos (+{dna.team_np_overperformance:.1f})")
            dna.strengths.append("Finisseurs cliniques (sans pénos)")
        elif dna.team_np_profile == "PENALTY_RELIANT":
            parts.append(f"Dépendant aux pénos ({dna.pct_penalty:.0f}%)")
            dna.weaknesses.append("Dépendant aux penalties")
        elif dna.team_np_profile == "WASTEFUL_TEAM":
            parts.append(f"Gaspilleurs ({dna.team_np_overperformance:.1f})")
            dna.weaknesses.append("Gaspille des occasions")
            
        # 🆕 Creative dependency
        if dna.creative_dependency_profile == "HIGH_DEPENDENCY":
            if dna.buildup_architects:
                parts.append(f"Créativité dépendante ({', '.join(dna.buildup_architects[:2])})")
            dna.weaknesses.append("Créativité concentrée (vulnérable aux absences)")
        elif dna.creative_dependency_profile == "DISTRIBUTED":
            dna.strengths.append("Créativité distribuée")
            
        # Form
        if dna.team_form_trend == "HOT":
            dna.strengths.append("En forme")
        elif dna.team_form_trend == "DECLINING":
            dna.weaknesses.append("Forme déclinante")
            
        dna.narrative_profile = " | ".join(parts) if parts else "Profil équilibré"
        
    def _identify_profitable_markets(self, dna: TeamAttackDNAv21) -> None:
        """Identifie les marchés profitables et à éviter"""
        dna.profitable_markets = []
        dna.markets_to_avoid = []
        
        # ═══════════════════════════════════════════════════════════════════════
        # OVER/UNDER GOALS
        # ═══════════════════════════════════════════════════════════════════════
        if dna.volume_profile == "HIGH_SCORING":
            dna.profitable_markets.append({
                'market': 'OVER_2.5_TEAM_GOALS',
                'confidence': 'HIGH',
                'reason': f"{dna.goals_per_match:.1f} buts/match"
            })
            
        # ═══════════════════════════════════════════════════════════════════════
        # FIRST GOALSCORER
        # ═══════════════════════════════════════════════════════════════════════
        if dna.timing_profile == "EARLY_STARTERS" and dna.pct_early >= 15:
            dna.profitable_markets.append({
                'market': 'FIRST_GOALSCORER',
                'confidence': 'MEDIUM',
                'players': dna.clinical_players[:3] if dna.clinical_players else None,
                'reason': f"{dna.pct_1h:.0f}% buts en 1H"
            })
        elif dna.timing_profile == "DIESEL":
            dna.markets_to_avoid.append({
                'market': 'FIRST_GOALSCORER',
                'reason': f"Équipe DIESEL - {dna.pct_2h:.0f}% buts en 2H"
            })
            
        # ═══════════════════════════════════════════════════════════════════════
        # LAST GOALSCORER
        # ═══════════════════════════════════════════════════════════════════════
        if dna.timing_profile in ["DIESEL", "CLUTCH_TEAM"] or dna.pct_clutch >= 20:
            players = dna.super_subs.copy() if dna.super_subs else []
            # Ajouter les FINISHER_ONLY en 2H
            players.extend([p for p in dna.finisher_only_players if p not in players][:2])
            
            dna.profitable_markets.append({
                'market': 'LAST_GOALSCORER',
                'confidence': 'HIGH' if dna.bench_strength == "STRONG_BENCH" else 'MEDIUM',
                'players': players[:5] if players else None,
                'reason': f"{dna.pct_2h:.0f}% buts en 2H, {dna.pct_clutch:.0f}% clutch"
            })
            
        # Super subs spécifiquement
        if dna.bench_strength == "STRONG_BENCH":
            dna.profitable_markets.append({
                'market': 'LAST_GOALSCORER_SUPER_SUB',
                'confidence': 'HIGH',
                'players': dna.super_subs,
                'reason': f"SUPER_SUBs: {', '.join(dna.super_subs)}"
            })
            
        # ═══════════════════════════════════════════════════════════════════════
        # 🆕 ANYTIME MVP (utilise NP-Clinical)
        # ═══════════════════════════════════════════════════════════════════════
        if dna.dependency_profile == "MVP_DEPENDENT":
            # Vérifier si le MVP est TRUE_CLINICAL
            if dna.top_scorer in dna.true_clinical_players:
                confidence = "MAX_BET"
            elif dna.top_scorer in dna.clinical_players:
                confidence = "HIGH"
            elif dna.top_scorer in dna.penalty_inflated_players:
                confidence = "CAUTION"  # Dépend des pénos
            else:
                confidence = "MEDIUM"
                
            dna.profitable_markets.append({
                'market': 'ANYTIME_MVP',
                'confidence': confidence,
                'players': [dna.top_scorer],
                'reason': f"{dna.top_scorer} = {dna.top_scorer_share:.0f}% des buts"
            })
            
        # ═══════════════════════════════════════════════════════════════════════
        # 🆕 ANYTIME FINISHER_ONLY (avec creative dependency check)
        # ═══════════════════════════════════════════════════════════════════════
        if dna.finisher_only_players:
            if dna.creative_dependency_profile == "DISTRIBUTED":
                dna.profitable_markets.append({
                    'market': 'ANYTIME_FINISHER_ONLY',
                    'confidence': 'HIGH',
                    'players': dna.finisher_only_players,
                    'reason': f"FINISHER_ONLY avec créativité distribuée"
                })
            elif dna.creative_dependency_profile == "HIGH_DEPENDENCY":
                dna.markets_to_avoid.append({
                    'market': 'ANYTIME_FINISHER_ONLY',
                    'players': dna.finisher_only_players,
                    'reason': f"FINISHER_ONLY dépendant de {', '.join(dna.buildup_architects[:2])} (architectes)"
                })
                
        # ═══════════════════════════════════════════════════════════════════════
        # 🆕 PLAYER ASSISTS (utilise xGChain)
        # ═══════════════════════════════════════════════════════════════════════
        if dna.buildup_architects:
            dna.profitable_markets.append({
                'market': 'PLAYER_ASSISTS',
                'confidence': 'HIGH',
                'players': dna.buildup_architects + dna.playmakers[:2],
                'reason': f"BUILDUP_ARCHITECTS: {', '.join(dna.buildup_architects)}"
            })
            # Ces joueurs NE marquent PAS
            dna.markets_to_avoid.append({
                'market': 'ANYTIME_GOAL',
                'players': dna.buildup_architects,
                'reason': f"BUILDUP_ARCHITECTS - impliqués partout mais finissent rien"
            })
            
        # ═══════════════════════════════════════════════════════════════════════
        # VALUE REGRESSION
        # ═══════════════════════════════════════════════════════════════════════
        if dna.value_regression_candidates:
            dna.profitable_markets.append({
                'market': 'ANYTIME_VALUE_REGRESSION',
                'confidence': 'MEDIUM',
                'players': dna.value_regression_candidates,
                'reason': f"Sous-performent leur xG"
            })
            
        # ═══════════════════════════════════════════════════════════════════════
        # SET PIECES
        # ═══════════════════════════════════════════════════════════════════════
        if dna.style_profile == "SET_PIECE_THREAT":
            dna.profitable_markets.append({
                'market': 'GOAL_FROM_SET_PIECE',
                'confidence': 'HIGH',
                'reason': f"{dna.pct_set_piece:.0f}% buts sur coups de pied arrêtés"
            })
            
        # ═══════════════════════════════════════════════════════════════════════
        # 🆕 PENALTY INFLATED WARNING
        # ═══════════════════════════════════════════════════════════════════════
        if dna.penalty_inflated_players:
            dna.markets_to_avoid.append({
                'market': 'ANYTIME_GOAL',
                'players': dna.penalty_inflated_players,
                'reason': f"PENALTY_INFLATED - stats gonflées par les pénos"
            })
            
    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTHODES D'AFFICHAGE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def print_team_dna(self, team_name: str) -> None:
        """Affiche l'ADN complet d'une équipe"""
        dna = self.team_dna.get(team_name)
        if not dna:
            print(f"❌ Équipe '{team_name}' non trouvée")
            return
            
        print("=" * 80)
        print(f"🧬 ADN OFFENSIF V2.1: {dna.team_name} ({dna.league})")
        print("=" * 80)
        
        print(f"\n📝 PROFIL NARRATIF:")
        print(f"   {dna.narrative_profile}")
        
        print(f"\n💪 FORCES:")
        for s in dna.strengths:
            print(f"   ✅ {s}")
        if not dna.strengths:
            print("   Aucune identifiée")
            
        print(f"\n⚠️ FAIBLESSES:")
        for w in dna.weaknesses:
            print(f"   ❌ {w}")
        if not dna.weaknesses:
            print("   Aucune identifiée")
            
        print(f"\n📊 VOLUME DNA:")
        print(f"   • {dna.total_goals} buts | {dna.goals_per_match:.1f}/match | {dna.volume_profile}")
        print(f"   • xG: {dna.total_xG:.1f} ({dna.xG_overperformance:+.1f} vs xG)")
        
        print(f"\n⏱️ TIMING DNA:")
        print(f"   • 1H: {dna.pct_1h:.0f}% | 2H: {dna.pct_2h:.0f}% | {dna.timing_profile}")
        print(f"   • Peak: {dna.peak_period} | Early: {dna.pct_early:.0f}% | Clutch: {dna.pct_clutch:.0f}%")
        
        print(f"\n👤 DEPENDENCY DNA:")
        print(f"   • Top scorer: {dna.top_scorer} ({dna.top_scorer_goals}G, {dna.top_scorer_share:.0f}%)")
        print(f"   • Top 3: {dna.top_3_share:.0f}% | {dna.dependency_profile}")
        print(f"   • {dna.scorers_count} buteurs différents")
        
        print(f"\n🎨 STYLE DNA:")
        print(f"   • Open play: {dna.pct_open_play:.0f}% | Set pieces: {dna.pct_set_piece:.0f}%")
        print(f"   • Headers: {dna.pct_header:.0f}% | Penalties: {dna.pct_penalty:.0f}%")
        print(f"   • Profile: {dna.style_profile}")
        
        print(f"\n🏠 HOME/AWAY DNA:")
        print(f"   • Home: {dna.goals_home}G | Away: {dna.goals_away}G | Ratio: {dna.home_away_ratio:.1f}x")
        print(f"   • Profile: {dna.home_away_profile}")
        
        print(f"\n🎯 EFFICIENCY DNA:")
        print(f"   • Conversion: {dna.team_conversion_rate:.0f}%")
        print(f"   • Elite finishers: {dna.elite_finishers_count} | Clinical: {dna.clinical_count}")
        print(f"   • Profile: {dna.efficiency_profile}")
        
        print(f"\n🦸 SUPER_SUB DNA:")
        print(f"   • {', '.join(dna.super_subs) if dna.super_subs else 'Aucun'}")
        print(f"   • {dna.super_sub_goals}G ({dna.super_sub_pct:.0f}%) | {dna.bench_strength}")
        
        print(f"\n🎯 PENALTY DNA:")
        print(f"   • Tireur: {dna.penalty_taker or 'Non identifié'}")
        print(f"   • {dna.penalty_goals} penalties | {dna.penalty_reliability}")
        
        # 🆕 NP-CLINICAL DNA
        print(f"\n🎯 NP-CLINICAL DNA (NOUVEAU):")
        print(f"   • Équipe NPG: {dna.team_np_goals} | NPxG: {dna.team_np_xG:.1f}")
        print(f"   • NP Overperformance: {dna.team_np_overperformance:+.1f}")
        print(f"   • Profil: {dna.team_np_profile}")
        print(f"   • TRUE_CLINICAL: {', '.join(dna.true_clinical_players) if dna.true_clinical_players else 'Aucun'}")
        print(f"   • PENALTY_INFLATED: {', '.join(dna.penalty_inflated_players) if dna.penalty_inflated_players else 'Aucun'}")
        
        # 🆕 CREATIVITY CHAIN DNA
        print(f"\n🔗 CREATIVITY CHAIN DNA (NOUVEAU):")
        print(f"   • Total xGChain: {dna.total_xGChain:.1f} | xGBuildup: {dna.total_xGBuildup:.1f}")
        print(f"   • Dépendance créative: {dna.creative_dependency_profile} ({dna.creative_dependency_count} playmakers)")
        print(f"   • BUILDUP_ARCHITECTS: {', '.join(dna.buildup_architects) if dna.buildup_architects else 'Aucun'}")
        print(f"   • FINISHER_ONLY: {', '.join(dna.finisher_only_players) if dna.finisher_only_players else 'Aucun'}")
        print(f"   • PLAYMAKERS: {', '.join(dna.playmakers) if dna.playmakers else 'Aucun'}")
        print(f"   • BOX_CRASHERS: {', '.join(dna.box_crashers) if dna.box_crashers else 'Aucun'}")
        
        print(f"\n📈 FORM DNA:")
        print(f"   • Hot: {', '.join(dna.hot_streak_players) if dna.hot_streak_players else 'Aucun'}")
        print(f"   • Cold: {', '.join(dna.cold_streak_players) if dna.cold_streak_players else 'Aucun'}")
        print(f"   • Trend: {dna.team_form_trend}")
        
        print(f"\n" + "─" * 80)
        print(f"💰 MARCHÉS PROFITABLES POUR {dna.team_name}:")
        for m in dna.profitable_markets:
            players_str = f" → {', '.join(m['players'])}" if m.get('players') else ""
            print(f"   ✅ {m['market']} [{m['confidence']}]{players_str}")
            print(f"      Raison: {m['reason']}")
            
        print(f"\n🚫 MARCHÉS À ÉVITER:")
        for m in dna.markets_to_avoid:
            players_str = f" → {', '.join(m['players'])}" if m.get('players') else ""
            print(f"   ❌ {m['market']}{players_str}")
            print(f"      Raison: {m['reason']}")
            
    def analyze_matchup(self, home_team: str, away_team: str) -> None:
        """Analyse la friction tactique entre deux équipes"""
        home_dna = self.team_dna.get(home_team)
        away_dna = self.team_dna.get(away_team)
        
        if not home_dna or not away_dna:
            print(f"❌ Équipe(s) non trouvée(s)")
            return
            
        print("=" * 80)
        print(f"⚔️ MATCHUP V2.1: {home_team} (🏠) vs {away_team} (✈️)")
        print("=" * 80)
        
        print(f"\n🏠 {home_team}: {home_dna.narrative_profile}")
        print(f"✈️ {away_team}: {away_dna.narrative_profile}")
        
        print(f"\n⚡ FRICTION TACTIQUE:")
        
        # Timing
        print(f"\n   ⏱️ TIMING:")
        print(f"      {home_team}: {home_dna.timing_profile} ({home_dna.pct_2h:.0f}% 2H)")
        print(f"      {away_team}: {away_dna.timing_profile} ({away_dna.pct_2h:.0f}% 2H)")
        
        # 🆕 NP-Clinical
        print(f"\n   🎯 NP-CLINICAL:")
        print(f"      {home_team}: {home_dna.team_np_profile} ({home_dna.team_np_overperformance:+.1f})")
        print(f"      {away_team}: {away_dna.team_np_profile} ({away_dna.team_np_overperformance:+.1f})")
        
        # 🆕 Creative Dependency
        print(f"\n   🔗 CREATIVE DEPENDENCY:")
        print(f"      {home_team}: {home_dna.creative_dependency_profile}")
        if home_dna.finisher_only_players and home_dna.creative_dependency_profile == "HIGH_DEPENDENCY":
            print(f"         ⚠️ {', '.join(home_dna.finisher_only_players)} dépend de {', '.join(home_dna.buildup_architects[:2])}")
        print(f"      {away_team}: {away_dna.creative_dependency_profile}")
        if away_dna.finisher_only_players and away_dna.creative_dependency_profile == "HIGH_DEPENDENCY":
            print(f"         ⚠️ {', '.join(away_dna.finisher_only_players)} dépend de {', '.join(away_dna.buildup_architects[:2])}")
        
        # Super subs
        print(f"\n   🦸 SUPER_SUBS:")
        print(f"      {home_team}: {', '.join(home_dna.super_subs) if home_dna.super_subs else 'Aucun'}")
        print(f"      {away_team}: {', '.join(away_dna.super_subs) if away_dna.super_subs else 'Aucun'}")
        
        print(f"\n💰 RECOMMANDATIONS:")
        
        # Over/Under
        if home_dna.volume_profile == "HIGH_SCORING" and away_dna.volume_profile == "HIGH_SCORING":
            print(f"   ✅ OVER_3.5 GOALS - Deux machines offensives")
        elif home_dna.volume_profile == "HIGH_SCORING":
            print(f"   🏠 [{home_team}] OVER_1.5_TEAM_GOALS")
        elif away_dna.volume_profile == "HIGH_SCORING":
            print(f"   ✈️ [{away_team}] OVER_1.5_TEAM_GOALS")
            
        # MVP avec NP-Clinical check
        if home_dna.dependency_profile == "MVP_DEPENDENT":
            confidence = "MAX_BET" if home_dna.top_scorer in home_dna.true_clinical_players else "MEDIUM"
            print(f"   🏠 [{home_team}] ANYTIME_MVP [{confidence}] → {home_dna.top_scorer}")
        if away_dna.dependency_profile == "MVP_DEPENDENT":
            confidence = "MAX_BET" if away_dna.top_scorer in away_dna.true_clinical_players else "MEDIUM"
            print(f"   ✈️ [{away_team}] ANYTIME_MVP [{confidence}] → {away_dna.top_scorer}")
            
        # FINISHER_ONLY avec creative dependency check
        for team_name, dna in [(home_team, home_dna), (away_team, away_dna)]:
            if dna.finisher_only_players:
                if dna.creative_dependency_profile == "DISTRIBUTED":
                    print(f"   ✅ [{team_name}] ANYTIME → {', '.join(dna.finisher_only_players[:2])} (créativité OK)")
                elif dna.creative_dependency_profile == "HIGH_DEPENDENCY":
                    print(f"   ⚠️ [{team_name}] CHECK LINEUP - {', '.join(dna.finisher_only_players[:2])} dépend de {', '.join(dna.buildup_architects[:2])}")
            
        # Timing clash
        if home_dna.timing_profile == "DIESEL" and away_dna.timing_profile == "DIESEL":
            print(f"   ⏱️ LAST_GOALSCORER - Deux équipes DIESEL → Buts tardifs probables")


if __name__ == '__main__':
    engineer = FeatureEngineerV21Advanced()
    engineer.initialize()
    
    # Afficher l'ADN de quelques équipes
    teams = ["Liverpool", "Bayern Munich", "Barcelona", "Marseille"]
    
    for team in teams:
        engineer.print_team_dna(team)
        print("\n" + "═" * 80 + "\n")
    
    # Analyser un matchup
    engineer.analyze_matchup("Liverpool", "Manchester City")
