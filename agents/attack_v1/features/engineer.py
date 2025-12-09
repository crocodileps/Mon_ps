"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🎯 ATTACK FEATURE ENGINEER V1.0 - HEDGE FUND GRADE                          ║
║                                                                              ║
║  Calcule 40+ features offensives par équipe:                                 ║
║  • Timing DNA: diesel_factor, sprinter_factor, clutch_factor                 ║
║  • Efficiency DNA: conversion_rate, xG_overperformance                       ║
║  • Dependency DNA: mvp_share, concentration_index                            ║
║  • Style DNA: verticality, set_piece_efficiency                              ║
║                                                                              ║
║  Philosophie: "Comment cette équipe marque-t-elle?"                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np
from enum import Enum

import sys
sys.path.insert(0, '/home/Mon_ps')
from agents.attack_v1.data.loader import AttackDataLoader, TeamOffensiveData, PlayerOffensiveProfile


class OffensiveProfile(str, Enum):
    """Profil offensif de l'équipe"""
    GOAL_MACHINE = "GOAL_MACHINE"      # G/90 > 2.0
    CLINICAL = "CLINICAL"              # Conversion > 15%
    EFFICIENT = "EFFICIENT"            # xG overperformance > 10%
    WASTEFUL = "WASTEFUL"              # xG underperformance > 10%
    AVERAGE = "AVERAGE"
    STRUGGLING = "STRUGGLING"          # G/90 < 1.0


class TimingProfile(str, Enum):
    """Profil temporel offensif"""
    DIESEL = "DIESEL"                  # >55% buts en 2H
    FAST_STARTER = "FAST_STARTER"      # >55% buts en 1H
    CLUTCH = "CLUTCH"                  # >25% buts après 75'
    EARLY_KILLER = "EARLY_KILLER"      # >20% buts avant 15'
    CONSISTENT = "CONSISTENT"          # Équilibré


class DependencyProfile(str, Enum):
    """Profil de dépendance"""
    ONE_MAN_TEAM = "ONE_MAN_TEAM"      # MVP > 40% des buts
    STAR_DRIVEN = "STAR_DRIVEN"        # MVP 30-40%
    BALANCED = "BALANCED"              # MVP 20-30%
    COLLECTIVE = "COLLECTIVE"          # MVP < 20%


class StyleProfile(str, Enum):
    """Style offensif"""
    COUNTER_ATTACK = "COUNTER_ATTACK"  # Fast attacks > 25%
    POSSESSION = "POSSESSION"          # Slow attacks > 25%
    SET_PIECE_KINGS = "SET_PIECE_KINGS"  # >25% buts sur SP
    DIRECT = "DIRECT"
    HYBRID = "HYBRID"


@dataclass
class TeamOffensiveFeatures:
    """Features offensives calculées pour une équipe"""
    team_name: str
    league: str
    
    # ═══════════════════════════════════════════════════════════════
    # FOUNDATION (Stats de base)
    # ═══════════════════════════════════════════════════════════════
    total_goals: int = 0
    total_xg: float = 0.0
    matches_played: int = 0
    goals_per_90: float = 0.0
    xg_per_90: float = 0.0
    
    # ═══════════════════════════════════════════════════════════════
    # EFFICIENCY DNA
    # ═══════════════════════════════════════════════════════════════
    conversion_rate: float = 0.0        # Goals / Shots %
    xg_conversion: float = 0.0          # Goals / xG (>1 = surperforme)
    xg_overperformance: float = 0.0     # Goals - xG
    shots_per_90: float = 0.0
    shots_on_target_pct: float = 0.0
    big_chance_conversion: float = 0.0
    
    # ═══════════════════════════════════════════════════════════════
    # TIMING DNA (Le plus important pour paris!)
    # ═══════════════════════════════════════════════════════════════
    goals_1h_pct: float = 0.0           # % buts en 1ère mi-temps
    goals_2h_pct: float = 0.0           # % buts en 2ème mi-temps
    
    # Par période de 15 min
    goals_0_15_pct: float = 0.0
    goals_16_30_pct: float = 0.0
    goals_31_45_pct: float = 0.0
    goals_46_60_pct: float = 0.0
    goals_61_75_pct: float = 0.0
    goals_76_90_pct: float = 0.0
    
    # xG par période (de Understat)
    xg_1h_pct: float = 0.0
    xg_2h_pct: float = 0.0
    xg_0_15: float = 0.0
    xg_16_30: float = 0.0
    xg_31_45: float = 0.0
    xg_46_60: float = 0.0
    xg_61_75: float = 0.0
    xg_76_plus: float = 0.0
    
    # Facteurs dérivés
    diesel_factor: float = 0.0          # 2H_pct / 1H_pct (>1.2 = diesel)
    sprinter_factor: float = 0.0        # 1H_pct / 2H_pct (>1.2 = fast starter)
    clutch_factor: float = 0.0          # % buts après 75'
    early_threat: float = 0.0           # % buts avant 15'
    
    # ═══════════════════════════════════════════════════════════════
    # DEPENDENCY DNA
    # ═══════════════════════════════════════════════════════════════
    mvp_name: str = ""
    mvp_goals: int = 0
    mvp_share: float = 0.0              # % des buts par le MVP
    top3_share: float = 0.0             # % des buts par top 3
    unique_scorers: int = 0             # Nombre de buteurs différents
    concentration_index: float = 0.0    # Herfindahl index (concentration)
    
    # ═══════════════════════════════════════════════════════════════
    # STYLE DNA
    # ═══════════════════════════════════════════════════════════════
    # Par situation de but
    open_play_pct: float = 0.0
    corner_pct: float = 0.0
    penalty_pct: float = 0.0
    freekick_pct: float = 0.0
    set_piece_total_pct: float = 0.0    # Corner + FK + Penalty
    
    # Par type de tir
    right_foot_pct: float = 0.0
    left_foot_pct: float = 0.0
    header_pct: float = 0.0
    
    # Vitesse d'attaque (de Understat)
    fast_attack_pct: float = 0.0        # Counter attacks
    normal_attack_pct: float = 0.0
    slow_attack_pct: float = 0.0        # Possession build-up
    verticality_index: float = 0.0      # Fast / (Fast + Slow)
    
    # ═══════════════════════════════════════════════════════════════
    # GAMESTATE DNA (Comment performe selon le score)
    # ═══════════════════════════════════════════════════════════════
    xg_when_drawing: float = 0.0        # xG/90 quand score = 0-0
    xg_when_leading: float = 0.0        # xG/90 quand mène
    xg_when_trailing: float = 0.0       # xG/90 quand perd
    killer_instinct: float = 0.0        # xG_leading / xG_drawing
    comeback_factor: float = 0.0        # xG_trailing / xG_drawing
    
    # ═══════════════════════════════════════════════════════════════
    # HOME/AWAY DNA
    # ═══════════════════════════════════════════════════════════════
    home_goals_pct: float = 0.0
    away_goals_pct: float = 0.0
    home_away_ratio: float = 1.0
    home_fortress: bool = False         # >65% buts à domicile
    away_threat: bool = False           # >45% buts à l'extérieur
    
    # ═══════════════════════════════════════════════════════════════
    # PROFILS CALCULÉS
    # ═══════════════════════════════════════════════════════════════
    offensive_profile: str = ""
    timing_profile: str = ""
    dependency_profile: str = ""
    style_profile: str = ""
    
    # ═══════════════════════════════════════════════════════════════
    # FINGERPRINT UNIQUE
    # ═══════════════════════════════════════════════════════════════
    fingerprint_hash: str = ""


class AttackFeatureEngineer:
    """
    Calcule les features offensives pour chaque équipe.
    """
    
    def __init__(self, loader: AttackDataLoader):
        self.loader = loader
        self.features: Dict[str, TeamOffensiveFeatures] = {}
        
    def engineer_all(self) -> None:
        """Calcule les features pour toutes les équipes"""
        print("=" * 80)
        print("🎯 ATTACK FEATURE ENGINEER V1.0")
        print("=" * 80)
        
        for team_name, team_data in self.loader.teams.items():
            features = self._engineer_team(team_data)
            self.features[team_name] = features
            
        print(f"\n✅ Features calculées pour {len(self.features)} équipes")
        
    def _engineer_team(self, team: TeamOffensiveData) -> TeamOffensiveFeatures:
        """Calcule les features pour une équipe"""
        
        features = TeamOffensiveFeatures(
            team_name=team.team_name,
            league=team.league,
            total_goals=team.total_goals,
            total_xg=team.total_xg,
        )
        
        # Skip si pas assez de données
        if team.total_goals < 5:
            return features
            
        # ═══════════════════════════════════════════════════════════════
        # TIMING DNA
        # ═══════════════════════════════════════════════════════════════
        self._calc_timing_features(features, team)
        
        # ═══════════════════════════════════════════════════════════════
        # DEPENDENCY DNA
        # ═══════════════════════════════════════════════════════════════
        self._calc_dependency_features(features, team)
        
        # ═══════════════════════════════════════════════════════════════
        # STYLE DNA
        # ═══════════════════════════════════════════════════════════════
        self._calc_style_features(features, team)
        
        # ═══════════════════════════════════════════════════════════════
        # GAMESTATE DNA
        # ═══════════════════════════════════════════════════════════════
        self._calc_gamestate_features(features, team)
        
        # ═══════════════════════════════════════════════════════════════
        # EFFICIENCY DNA (depuis Understat timing)
        # ═══════════════════════════════════════════════════════════════
        self._calc_efficiency_features(features, team)
        
        # ═══════════════════════════════════════════════════════════════
        # PROFILS
        # ═══════════════════════════════════════════════════════════════
        self._calc_profiles(features)
        
        # Fingerprint
        features.fingerprint_hash = f"{features.offensive_profile}_{features.timing_profile}_{features.dependency_profile}_{features.style_profile}"
        
        return features
        
    def _calc_timing_features(self, features: TeamOffensiveFeatures, team: TeamOffensiveData) -> None:
        """Calcule les features de timing"""
        total = team.total_goals or 1
        
        # Depuis goals_by_period (all_goals_2025.json)
        g_0_15 = team.goals_by_period.get('0-15', 0)
        g_16_30 = team.goals_by_period.get('16-30', 0)
        g_31_45 = team.goals_by_period.get('31-45', 0)
        g_46_60 = team.goals_by_period.get('46-60', 0)
        g_61_75 = team.goals_by_period.get('61-75', 0)
        g_76_90 = team.goals_by_period.get('76-90', 0)
        g_90_plus = team.goals_by_period.get('90+', 0)
        
        goals_1h = g_0_15 + g_16_30 + g_31_45
        goals_2h = g_46_60 + g_61_75 + g_76_90 + g_90_plus
        
        features.goals_0_15_pct = (g_0_15 / total) * 100
        features.goals_16_30_pct = (g_16_30 / total) * 100
        features.goals_31_45_pct = (g_31_45 / total) * 100
        features.goals_46_60_pct = (g_46_60 / total) * 100
        features.goals_61_75_pct = (g_61_75 / total) * 100
        features.goals_76_90_pct = ((g_76_90 + g_90_plus) / total) * 100
        
        features.goals_1h_pct = (goals_1h / total) * 100
        features.goals_2h_pct = (goals_2h / total) * 100
        
        # Facteurs dérivés
        features.diesel_factor = features.goals_2h_pct / features.goals_1h_pct if features.goals_1h_pct > 0 else 1.0
        features.sprinter_factor = features.goals_1h_pct / features.goals_2h_pct if features.goals_2h_pct > 0 else 1.0
        features.clutch_factor = features.goals_76_90_pct
        features.early_threat = features.goals_0_15_pct
        
        # Depuis Understat timing (xG par période)
        if team.timing_data:
            total_xg = sum(float(p.get('xG', 0)) for p in team.timing_data.values())
            if total_xg > 0:
                features.xg_0_15 = float(team.timing_data.get('1-15', {}).get('xG', 0))
                features.xg_16_30 = float(team.timing_data.get('16-30', {}).get('xG', 0))
                features.xg_31_45 = float(team.timing_data.get('31-45', {}).get('xG', 0))
                features.xg_46_60 = float(team.timing_data.get('46-60', {}).get('xG', 0))
                features.xg_61_75 = float(team.timing_data.get('61-75', {}).get('xG', 0))
                features.xg_76_plus = float(team.timing_data.get('76+', {}).get('xG', 0))
                
                xg_1h = features.xg_0_15 + features.xg_16_30 + features.xg_31_45
                xg_2h = features.xg_46_60 + features.xg_61_75 + features.xg_76_plus
                
                features.xg_1h_pct = (xg_1h / total_xg) * 100
                features.xg_2h_pct = (xg_2h / total_xg) * 100
                
    def _calc_dependency_features(self, features: TeamOffensiveFeatures, team: TeamOffensiveData) -> None:
        """Calcule les features de dépendance"""
        if not team.players:
            return
            
        # Trier par buts
        sorted_players = sorted(team.players, key=lambda p: p.goals, reverse=True)
        
        # MVP
        if sorted_players:
            mvp = sorted_players[0]
            features.mvp_name = mvp.player_name
            features.mvp_goals = mvp.goals
            features.mvp_share = (mvp.goals / team.total_goals * 100) if team.total_goals > 0 else 0
            
        # Top 3
        top3_goals = sum(p.goals for p in sorted_players[:3])
        features.top3_share = (top3_goals / team.total_goals * 100) if team.total_goals > 0 else 0
        
        # Unique scorers
        features.unique_scorers = len([p for p in team.players if p.goals > 0])
        
        # Concentration Index (Herfindahl)
        if team.total_goals > 0:
            shares = [(p.goals / team.total_goals) ** 2 for p in team.players if p.goals > 0]
            features.concentration_index = sum(shares) * 100  # 100 = un seul buteur
            
    def _calc_style_features(self, features: TeamOffensiveFeatures, team: TeamOffensiveData) -> None:
        """Calcule les features de style"""
        total = team.total_goals or 1
        
        # Par situation
        features.open_play_pct = (team.goals_by_situation.get('OpenPlay', 0) / total) * 100
        features.corner_pct = (team.goals_by_situation.get('FromCorner', 0) / total) * 100
        features.penalty_pct = (team.goals_by_situation.get('Penalty', 0) / total) * 100
        features.freekick_pct = (team.goals_by_situation.get('DirectFreekick', 0) / total) * 100
        features.set_piece_total_pct = features.corner_pct + features.freekick_pct + features.penalty_pct + \
                                        (team.goals_by_situation.get('SetPiece', 0) / total) * 100
        
        # Par type de tir
        features.right_foot_pct = (team.goals_by_shot_type.get('RightFoot', 0) / total) * 100
        features.left_foot_pct = (team.goals_by_shot_type.get('LeftFoot', 0) / total) * 100
        features.header_pct = (team.goals_by_shot_type.get('Head', 0) / total) * 100
        
        # Vitesse d'attaque (depuis Understat)
        if team.attack_speed_data:
            fast = team.attack_speed_data.get('Fast', {}).get('goals_for', 0)
            normal = team.attack_speed_data.get('Normal', {}).get('goals_for', 0)
            slow = team.attack_speed_data.get('Slow', {}).get('goals_for', 0)
            standard = team.attack_speed_data.get('Standard', {}).get('goals_for', 0)
            
            total_speed = fast + normal + slow + standard
            if total_speed > 0:
                features.fast_attack_pct = (fast / total_speed) * 100
                features.normal_attack_pct = ((normal + standard) / total_speed) * 100
                features.slow_attack_pct = (slow / total_speed) * 100
                features.verticality_index = fast / (fast + slow) if (fast + slow) > 0 else 0.5
                
    def _calc_gamestate_features(self, features: TeamOffensiveFeatures, team: TeamOffensiveData) -> None:
        """Calcule les features de gamestate"""
        if not team.gamestate_data:
            return
            
        # xG par état du score
        drawing = team.gamestate_data.get('Goal diff 0', {})
        leading_1 = team.gamestate_data.get('Goal diff +1', {})
        leading_big = team.gamestate_data.get('Goal diff > +1', {})
        trailing_1 = team.gamestate_data.get('Goal diff -1', {})
        trailing_big = team.gamestate_data.get('Goal diff < -1', {})
        
        features.xg_when_drawing = float(drawing.get('xG_for_90', 0))
        features.xg_when_leading = (float(leading_1.get('xG_for_90', 0)) + float(leading_big.get('xG_for_90', 0))) / 2
        features.xg_when_trailing = (float(trailing_1.get('xG_for_90', 0)) + float(trailing_big.get('xG_for_90', 0))) / 2
        
        # Killer instinct et comeback
        if features.xg_when_drawing > 0:
            features.killer_instinct = features.xg_when_leading / features.xg_when_drawing
            features.comeback_factor = features.xg_when_trailing / features.xg_when_drawing
            
    def _calc_efficiency_features(self, features: TeamOffensiveFeatures, team: TeamOffensiveData) -> None:
        """Calcule les features d'efficacité"""
        # xG conversion
        if team.total_xg > 0:
            features.xg_conversion = team.total_goals / team.total_xg
            features.xg_overperformance = team.total_goals - team.total_xg
            
        # Shots (agrégés depuis Understat timing)
        if team.timing_data:
            total_shots = sum(int(p.get('shots', 0)) for p in team.timing_data.values())
            if total_shots > 0:
                features.conversion_rate = (team.total_goals / total_shots) * 100
                features.shots_per_90 = total_shots / (team.matches_played or 15)  # Estimation
                
    def _calc_profiles(self, features: TeamOffensiveFeatures) -> None:
        """Détermine les profils"""
        
        # Offensive Profile
        if features.goals_per_90 >= 2.0:
            features.offensive_profile = OffensiveProfile.GOAL_MACHINE.value
        elif features.xg_conversion >= 1.1:
            features.offensive_profile = OffensiveProfile.CLINICAL.value
        elif features.xg_conversion >= 1.0:
            features.offensive_profile = OffensiveProfile.EFFICIENT.value
        elif features.xg_conversion < 0.9:
            features.offensive_profile = OffensiveProfile.WASTEFUL.value
        elif features.goals_per_90 < 1.0:
            features.offensive_profile = OffensiveProfile.STRUGGLING.value
        else:
            features.offensive_profile = OffensiveProfile.AVERAGE.value
            
        # Timing Profile
        if features.goals_2h_pct > 55:
            features.timing_profile = TimingProfile.DIESEL.value
        elif features.goals_1h_pct > 55:
            features.timing_profile = TimingProfile.FAST_STARTER.value
        elif features.clutch_factor > 25:
            features.timing_profile = TimingProfile.CLUTCH.value
        elif features.early_threat > 20:
            features.timing_profile = TimingProfile.EARLY_KILLER.value
        else:
            features.timing_profile = TimingProfile.CONSISTENT.value
            
        # Dependency Profile
        if features.mvp_share > 40:
            features.dependency_profile = DependencyProfile.ONE_MAN_TEAM.value
        elif features.mvp_share > 30:
            features.dependency_profile = DependencyProfile.STAR_DRIVEN.value
        elif features.mvp_share > 20:
            features.dependency_profile = DependencyProfile.BALANCED.value
        else:
            features.dependency_profile = DependencyProfile.COLLECTIVE.value
            
        # Style Profile
        if features.fast_attack_pct > 25:
            features.style_profile = StyleProfile.COUNTER_ATTACK.value
        elif features.slow_attack_pct > 25:
            features.style_profile = StyleProfile.POSSESSION.value
        elif features.set_piece_total_pct > 25:
            features.style_profile = StyleProfile.SET_PIECE_KINGS.value
        elif features.verticality_index > 0.6:
            features.style_profile = StyleProfile.DIRECT.value
        else:
            features.style_profile = StyleProfile.HYBRID.value
            
    def get_features(self, team_name: str) -> Optional[TeamOffensiveFeatures]:
        """Récupère les features d'une équipe"""
        return self.features.get(team_name)


# Test
if __name__ == '__main__':
    loader = AttackDataLoader()
    loader.load_all()
    
    engineer = AttackFeatureEngineer(loader)
    engineer.engineer_all()
    
    # Test Liverpool
    print("\n" + "=" * 80)
    print("🔴 FEATURES LIVERPOOL")
    print("=" * 80)
    
    f = engineer.get_features('Liverpool')
    if f:
        print(f"\n�� PROFILS:")
        print(f"   Offensive: {f.offensive_profile}")
        print(f"   Timing: {f.timing_profile}")
        print(f"   Dependency: {f.dependency_profile}")
        print(f"   Style: {f.style_profile}")
        
        print(f"\n⏱️ TIMING DNA:")
        print(f"   1H: {f.goals_1h_pct:.1f}% | 2H: {f.goals_2h_pct:.1f}%")
        print(f"   Diesel Factor: {f.diesel_factor:.2f}")
        print(f"   Clutch (76-90): {f.clutch_factor:.1f}%")
        
        print(f"\n👤 DEPENDENCY DNA:")
        print(f"   MVP: {f.mvp_name} ({f.mvp_goals}G, {f.mvp_share:.1f}%)")
        print(f"   Top 3: {f.top3_share:.1f}%")
        print(f"   Buteurs différents: {f.unique_scorers}")
        
        print(f"\n🎯 STYLE DNA:")
        print(f"   Open Play: {f.open_play_pct:.1f}%")
        print(f"   Set Pieces: {f.set_piece_total_pct:.1f}%")
        print(f"   Headers: {f.header_pct:.1f}%")
        
        print(f"\n🧠 GAMESTATE DNA:")
        print(f"   xG Drawing: {f.xg_when_drawing:.2f}")
        print(f"   Killer Instinct: {f.killer_instinct:.2f}")
        print(f"   Comeback Factor: {f.comeback_factor:.2f}")
        
        print(f"\n🔑 FINGERPRINT: {f.fingerprint_hash}")
