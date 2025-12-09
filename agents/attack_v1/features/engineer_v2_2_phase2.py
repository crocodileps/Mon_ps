"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🧬 FEATURE ENGINEER V2.2 PHASE 2 - TEAM-CENTRIC HEDGE FUND GRADE            ║
║                                                                              ║
║  NOUVELLES DIMENSIONS PHASE 2:                                               ║
║  ═══════════════════════════════════════════════════════════════════════════ ║
║  🔗 13. CREATOR-FINISHER DNA:                                                ║
║     • elite_combos, strong_combos                                            ║
║     • top_creator_finisher_link (meilleur combo)                             ║
║     • combo_dependency_profile: COMBO_RELIANT, COMBO_DIVERSE, NO_COMBO       ║
║     • Edge: Parier sur "Creator Assist + Finisher Goal"                      ║
║                                                                              ║
║  ⚡ 14. MOMENTUM DNA:                                                         ║
║     • momentum_profile: BURST_SCORER, STEADY_SCORER, MIXED                   ║
║     • burst_rate, avg_time_between_goals                                     ║
║     • Edge Live: Si BURST marque → Next Goal même équipe                     ║
║                                                                              ║
║  HÉRITE DE: engineer_v2_1_advanced.py (12 dimensions)                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
sys.path.insert(0, '/home/Mon_ps')

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json

from agents.attack_v1.data.loader_v5_3_phase2 import (
    AttackDataLoaderV53Phase2,
    CreatorFinisherCombo,
    TeamMomentumDNA
)
from agents.attack_v1.features.engineer_v2_1_advanced import (
    FeatureEngineerV21Advanced,
    TeamAttackDNAv21
)

DATA_DIR = Path('/home/Mon_ps/data')


# ═══════════════════════════════════════════════════════════════════════════════
# TEAM ATTACK DNA V2.2 - AVEC PHASE 2
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TeamAttackDNAv22(TeamAttackDNAv21):
    """
    ADN OFFENSIF COMPLET d'une équipe - VERSION 2.2 PHASE 2
    
    Hérite de V2.1 (12 dimensions) et ajoute:
    • 13. CREATOR-FINISHER DNA
    • 14. MOMENTUM DNA
    """
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🆕 13. CREATOR-FINISHER DNA (PHASE 2)
    # ═══════════════════════════════════════════════════════════════════════════
    elite_combos: List[Dict] = field(default_factory=list)
    strong_combos: List[Dict] = field(default_factory=list)
    all_combos_count: int = 0
    top_combo: Dict = field(default_factory=dict)
    combo_goals_pct: float = 0.0  # % des buts via combos identifiés
    combo_dependency_profile: str = ""  # COMBO_RELIANT, COMBO_DIVERSE, NO_COMBO
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🆕 14. MOMENTUM DNA (PHASE 2)
    # ═══════════════════════════════════════════════════════════════════════════
    momentum_profile: str = ""  # BURST_SCORER, STEADY_SCORER, MIXED
    burst_rate: float = 0.0
    total_bursts: int = 0
    avg_time_between_goals: float = 0.0
    matches_with_multiple_goals: int = 0
    best_bursts: List[Dict] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE ENGINEER V2.2 PHASE 2
# ═══════════════════════════════════════════════════════════════════════════════

class FeatureEngineerV22Phase2:
    """
    Feature Engineer V2.2 PHASE 2 - TEAM-CENTRIC
    
    Construit l'ADN COMPLET de chaque équipe avec 14 dimensions
    dont 2 nouvelles Phase 2: CREATOR-FINISHER DNA et MOMENTUM DNA
    """
    
    def __init__(self):
        self.loader = AttackDataLoaderV53Phase2()
        self.team_dna: Dict[str, TeamAttackDNAv22] = {}
        self.matches_played = 13  # À ajuster selon la saison
        
    def initialize(self) -> None:
        """Initialise le Feature Engineer"""
        print("=" * 80)
        print("🎯 FEATURE ENGINEER V2.2 PHASE 2 - TEAM-CENTRIC HEDGE FUND GRADE")
        print("=" * 80)
        
        self.loader.load_all()
        self._build_all_team_dna()
        
        print(f"\n✅ {len(self.team_dna)} équipes avec ADN COMPLET V2.2 (14 dimensions)")
        
    def _build_all_team_dna(self) -> None:
        """Construit l'ADN de toutes les équipes"""
        print("\n📊 Construction ADN V2.2 par équipe...")
        
        for team_name, team in self.loader.teams.items():
            dna = self._build_team_dna(team_name)
            self.team_dna[team_name] = dna
            
    def _build_team_dna(self, team_name: str) -> TeamAttackDNAv22:
        """Construit l'ADN complet d'une équipe V2.2"""
        
        team = self.loader.teams.get(team_name)
        if not team:
            return TeamAttackDNAv22(team_name=team_name)
            
        # Créer le DNA V2.2
        dna = TeamAttackDNAv22(team_name=team_name, league=team.league)
        
        players = team.players
        scorers = [p for p in players if p.goals > 0]
        
        # ═══════════════════════════════════════════════════════════════════════
        # DIMENSIONS 1-12 (héritées de V2.1)
        # ═══════════════════════════════════════════════════════════════════════
        self._build_v21_dimensions(dna, team, players, scorers)
        
        # ═══════════════════════════════════════════════════════════════════════
        # 🆕 DIMENSION 13: CREATOR-FINISHER DNA (PHASE 2)
        # ═══════════════════════════════════════════════════════════════════════
        self._build_creator_finisher_dna(dna, team_name)
        
        # ═══════════════════════════════════════════════════════════════════════
        # 🆕 DIMENSION 14: MOMENTUM DNA (PHASE 2)
        # ═══════════════════════════════════════════════════════════════════════
        self._build_momentum_dna(dna, team_name)
        
        # ═══════════════════════════════════════════════════════════════════════
        # PROFIL NARRATIF + MARCHÉS
        # ═══════════════════════════════════════════════════════════════════════
        self._build_narrative_v22(dna)
        self._identify_profitable_markets_v22(dna)
        
        return dna
        
    def _build_v21_dimensions(self, dna: TeamAttackDNAv22, team, players, scorers) -> None:
        """Construit les dimensions 1-12 (héritées de V2.1)"""
        
        # 1. VOLUME DNA
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
            
        # 2. TIMING DNA
        dna.goals_1h = sum(p.goals_1h for p in players)
        dna.goals_2h = sum(p.goals_2h for p in players)
        
        if dna.total_goals > 0:
            dna.pct_1h = (dna.goals_1h / dna.total_goals) * 100
            dna.pct_2h = (dna.goals_2h / dna.total_goals) * 100
            
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
            
        if dna.goals_by_period:
            dna.peak_period = max(dna.goals_by_period, key=dna.goals_by_period.get)
            
        if dna.pct_2h >= 65:
            dna.timing_profile = "DIESEL"
        elif dna.pct_1h >= 60:
            dna.timing_profile = "EARLY_STARTERS"
        elif dna.pct_clutch >= 25:
            dna.timing_profile = "CLUTCH_TEAM"
        else:
            dna.timing_profile = "BALANCED"
            
        # 3. DEPENDENCY DNA
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
                
        # 4. STYLE DNA
        dna.goals_open_play = sum(p.goals_open_play for p in players)
        dna.goals_set_piece = sum(p.goals_corner + p.goals_set_piece for p in players)
        dna.goals_penalty = sum(p.penalty_goals for p in players)
        dna.goals_header = sum(p.goals_header for p in players)
        
        if dna.total_goals > 0:
            dna.pct_open_play = (dna.goals_open_play / dna.total_goals) * 100
            dna.pct_set_piece = (dna.goals_set_piece / dna.total_goals) * 100
            dna.pct_penalty = (dna.goals_penalty / dna.total_goals) * 100
            dna.pct_header = (dna.goals_header / dna.total_goals) * 100
            
        # 5. HOME/AWAY DNA
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
            
        # 6. EFFICIENCY DNA
        total_shots = sum(p.shots for p in players)
        if total_shots > 0:
            dna.team_conversion_rate = (dna.total_goals / total_shots) * 100
            
        dna.elite_finishers_count = len([p for p in players if p.shot_quality == "ELITE_FINISHER"])
        dna.clinical_count = len([p for p in players if p.shot_quality in ["ELITE_FINISHER", "CLINICAL"]])
        
        # 7. SUPER_SUB DNA
        super_subs = [p for p in players if p.playing_time_profile == "SUPER_SUB" and p.goals >= 2]
        dna.super_subs = [p.player_name for p in super_subs]
        dna.super_sub_goals = sum(p.goals for p in super_subs)
        dna.super_sub_pct = (dna.super_sub_goals / dna.total_goals * 100) if dna.total_goals > 0 else 0
        
        if dna.super_sub_pct >= 15:
            dna.bench_strength = "STRONG_BENCH"
        elif dna.super_sub_pct >= 5:
            dna.bench_strength = "AVERAGE_BENCH"
        else:
            dna.bench_strength = "WEAK_BENCH"
            
        # 8. PENALTY DNA
        penalty_takers = [p for p in players if p.is_penalty_taker]
        if penalty_takers:
            top_taker = max(penalty_takers, key=lambda p: p.penalty_goals)
            dna.penalty_taker = top_taker.player_name
            dna.penalty_goals = top_taker.penalty_goals
            dna.penalty_reliability = "RELIABLE" if dna.penalty_goals >= 3 else "AVERAGE"
        else:
            dna.penalty_reliability = "NO_DATA"
            
        # 9. CREATIVITY DNA
        dna.total_assists = sum(p.assists for p in players)
        dna.total_xA = sum(p.xA for p in players)
        
        elite_creators = [p for p in players if p.creativity_profile == "ELITE_CREATOR"]
        dna.elite_creators_count = len(elite_creators)
        if elite_creators:
            dna.top_creator = max(elite_creators, key=lambda p: p.xA).player_name
            
        # 10. FORM DNA
        dna.hot_streak_players = [p.player_name for p in players if p.finishing_trend == "HOT_STREAK" and p.goals >= 3]
        dna.cold_streak_players = [p.player_name for p in players if p.finishing_trend in ["COLD", "WASTEFUL"] and p.goals >= 2]
        dna.value_regression_candidates = [p.player_name for p in players if p.xG >= 4 and p.xG_overperformance <= -1.5]
        
        # 11. NP-CLINICAL DNA
        dna.team_np_goals = sum(p.np_goals for p in players)
        dna.team_np_xG = sum(p.np_xG for p in players)
        dna.team_np_overperformance = dna.team_np_goals - dna.team_np_xG
        
        dna.true_clinical_players = [p.player_name for p in players if p.np_clinical_profile == "TRUE_CLINICAL" and p.goals >= 3]
        dna.clinical_players = [p.player_name for p in players if p.np_clinical_profile in ["TRUE_CLINICAL", "CLINICAL"] and p.goals >= 3]
        dna.penalty_inflated_players = [p.player_name for p in players if p.np_clinical_profile == "PENALTY_INFLATED"]
        dna.np_wasteful_players = [p.player_name for p in players if p.np_clinical_profile == "WASTEFUL" and p.goals >= 2]
        
        if len(dna.true_clinical_players) >= 2 or dna.team_np_overperformance >= 3:
            dna.team_np_profile = "CLINICAL_TEAM"
        elif dna.pct_penalty >= 20 and dna.team_np_overperformance < 0:
            dna.team_np_profile = "PENALTY_RELIANT"
        elif len(dna.np_wasteful_players) >= 3 or dna.team_np_overperformance <= -3:
            dna.team_np_profile = "WASTEFUL_TEAM"
        else:
            dna.team_np_profile = "AVERAGE"
            
        # 12. CREATIVITY CHAIN DNA
        dna.total_xGChain = sum(p.xGChain for p in players)
        dna.total_xGBuildup = sum(p.xGBuildup for p in players)
        
        dna.buildup_architects = [p.player_name for p in players if p.chain_profile == "BUILDUP_ARCHITECT" and p.xGChain >= 3]
        dna.high_involvement_players = [p.player_name for p in players if p.chain_profile == "HIGH_INVOLVEMENT" and p.xGChain >= 2]
        dna.finisher_only_players = [p.player_name for p in players if p.chain_profile == "FINISHER_ONLY" and p.goals >= 3]
        dna.playmakers = [p.player_name for p in players if p.buildup_profile == "PLAYMAKER" and p.xGChain >= 2]
        dna.box_crashers = [p.player_name for p in players if p.buildup_profile == "BOX_CRASHER" and p.goals >= 3]
        
        dna.creative_dependency_count = len([p for p in players if p.buildup_ratio >= 0.6 and p.xGChain >= 2])
        
        if dna.creative_dependency_count <= 2:
            dna.creative_dependency_profile = "HIGH_DEPENDENCY"
        elif dna.creative_dependency_count <= 4:
            dna.creative_dependency_profile = "MODERATE"
        else:
            dna.creative_dependency_profile = "DISTRIBUTED"
            
    def _build_creator_finisher_dna(self, dna: TeamAttackDNAv22, team_name: str) -> None:
        """
        🆕 DIMENSION 13: CREATOR-FINISHER DNA
        
        Profils:
        • COMBO_RELIANT: 50%+ des buts via combos récurrents
        • COMBO_DIVERSE: Plusieurs combos, pas de dépendance
        • NO_COMBO: Peu de combos identifiés
        """
        combos = self.loader.get_team_combos(team_name, min_occurrences=2)
        
        dna.all_combos_count = len(combos)
        
        # Elite et Strong combos
        dna.elite_combos = [
            {'creator': c.creator, 'finisher': c.finisher, 'occurrences': c.occurrences, 'score': c.combo_score}
            for c in combos if c.combo_profile == "ELITE_COMBO"
        ]
        dna.strong_combos = [
            {'creator': c.creator, 'finisher': c.finisher, 'occurrences': c.occurrences, 'score': c.combo_score}
            for c in combos if c.combo_profile in ["ELITE_COMBO", "STRONG_COMBO"]
        ]
        
        # Top combo
        if combos:
            top = combos[0]
            dna.top_combo = {
                'creator': top.creator,
                'finisher': top.finisher,
                'occurrences': top.occurrences,
                'avg_xG': top.avg_xG,
                'score': top.combo_score,
                'profile': top.combo_profile
            }
            
        # % des buts via combos
        combo_goals = sum(c.occurrences for c in combos)
        if dna.total_goals > 0:
            dna.combo_goals_pct = (combo_goals / dna.total_goals) * 100
            
        # Classification
        if len(dna.elite_combos) >= 2 or dna.combo_goals_pct >= 50:
            dna.combo_dependency_profile = "COMBO_RELIANT"
        elif len(dna.strong_combos) >= 3 or dna.combo_goals_pct >= 30:
            dna.combo_dependency_profile = "COMBO_DIVERSE"
        else:
            dna.combo_dependency_profile = "NO_COMBO"
            
    def _build_momentum_dna(self, dna: TeamAttackDNAv22, team_name: str) -> None:
        """
        🆕 DIMENSION 14: MOMENTUM DNA
        
        Profils:
        • BURST_SCORER: burst_rate >= 60% (marque en série)
        • MIXED: 30-60%
        • STEADY_SCORER: < 30% (espace les buts)
        """
        momentum = self.loader.get_team_momentum(team_name)
        
        if not momentum:
            dna.momentum_profile = "NO_DATA"
            return
            
        dna.momentum_profile = momentum.momentum_profile
        dna.burst_rate = momentum.burst_rate
        dna.total_bursts = momentum.total_bursts
        dna.avg_time_between_goals = momentum.avg_time_between_goals
        dna.matches_with_multiple_goals = momentum.matches_with_multiple_goals
        dna.best_bursts = momentum.best_bursts[:3]
        
    def _build_narrative_v22(self, dna: TeamAttackDNAv22) -> None:
        """Construit le profil narratif V2.2"""
        parts = []
        dna.strengths = []
        dna.weaknesses = []
        
        # Volume
        if dna.volume_profile == "HIGH_SCORING":
            parts.append(f"Machine offensive ({dna.goals_per_match:.1f}/match)")
            dna.strengths.append("Puissance de feu élevée")
            
        # Timing
        if dna.timing_profile == "DIESEL":
            parts.append(f"Diesel ({dna.pct_2h:.0f}% 2H)")
            dna.strengths.append("Monte en puissance")
        elif dna.timing_profile == "CLUTCH_TEAM":
            parts.append(f"Clutch ({dna.pct_clutch:.0f}% après 75')")
            dna.strengths.append("Décisifs en fin de match")
            
        # Dependency
        if dna.dependency_profile == "MVP_DEPENDENT":
            parts.append(f"Dépendant de {dna.top_scorer}")
            dna.weaknesses.append(f"Trop dépendant de {dna.top_scorer}")
        elif dna.dependency_profile == "DISTRIBUTED":
            dna.strengths.append("Menace variée")
            
        # 🆕 Creator-Finisher
        if dna.combo_dependency_profile == "COMBO_RELIANT" and dna.top_combo:
            parts.append(f"Combo: {dna.top_combo['creator']}→{dna.top_combo['finisher']}")
            dna.strengths.append(f"Combo identifié ({dna.combo_goals_pct:.0f}% des buts)")
            
        # 🆕 Momentum
        if dna.momentum_profile == "BURST_SCORER":
            parts.append(f"BURST ({dna.burst_rate:.0f}%)")
            dna.strengths.append("Marque en série (BURST)")
        elif dna.momentum_profile == "STEADY_SCORER":
            parts.append(f"Steady ({dna.avg_time_between_goals:.0f}min)")
            
        # NP-Clinical
        if dna.team_np_profile == "CLINICAL_TEAM":
            dna.strengths.append("Finisseurs cliniques")
        elif dna.team_np_profile == "WASTEFUL_TEAM":
            dna.weaknesses.append("Gaspille des occasions")
            
        dna.narrative_profile = " | ".join(parts) if parts else "Profil équilibré"
        
    def _identify_profitable_markets_v22(self, dna: TeamAttackDNAv22) -> None:
        """Identifie les marchés profitables V2.2"""
        dna.profitable_markets = []
        dna.markets_to_avoid = []
        
        # ═══════════════════════════════════════════════════════════════════════
        # 🆕 COMBO BETS (PHASE 2)
        # ═══════════════════════════════════════════════════════════════════════
        if dna.elite_combos:
            for combo in dna.elite_combos[:2]:
                dna.profitable_markets.append({
                    'market': 'COMBO_BET',
                    'confidence': 'HIGH',
                    'players': [f"{combo['creator']} Assist + {combo['finisher']} Goal"],
                    'reason': f"ELITE_COMBO: {combo['occurrences']}x cette saison"
                })
                
        if dna.strong_combos and not dna.elite_combos:
            for combo in dna.strong_combos[:2]:
                dna.profitable_markets.append({
                    'market': 'COMBO_BET',
                    'confidence': 'MEDIUM',
                    'players': [f"{combo['creator']} Assist + {combo['finisher']} Goal"],
                    'reason': f"STRONG_COMBO: {combo['occurrences']}x cette saison"
                })
                
        # ═══════════════════════════════════════════════════════════════════════
        # 🆕 LIVE BETTING MOMENTUM (PHASE 2)
        # ═══════════════════════════════════════════════════════════════════════
        if dna.momentum_profile == "BURST_SCORER":
            dna.profitable_markets.append({
                'market': 'LIVE_NEXT_GOAL',
                'confidence': 'HIGH',
                'players': None,
                'reason': f"BURST_SCORER: {dna.burst_rate:.0f}% burst rate → Si marque, parier Next Goal"
            })
            dna.profitable_markets.append({
                'market': 'LIVE_OVER_GOALS',
                'confidence': 'MEDIUM',
                'players': None,
                'reason': f"BURST_SCORER: Probabilité de 2+ buts rapides élevée"
            })
            
        elif dna.momentum_profile == "STEADY_SCORER":
            dna.markets_to_avoid.append({
                'market': 'LIVE_NEXT_GOAL_IMMEDIATE',
                'reason': f"STEADY_SCORER: Écart moyen {dna.avg_time_between_goals:.0f} min entre buts"
            })
            
        # ═══════════════════════════════════════════════════════════════════════
        # MARCHÉS EXISTANTS (V2.1)
        # ═══════════════════════════════════════════════════════════════════════
        
        # Volume
        if dna.volume_profile == "HIGH_SCORING":
            dna.profitable_markets.append({
                'market': 'OVER_2.5_TEAM_GOALS',
                'confidence': 'HIGH',
                'players': None,
                'reason': f"{dna.goals_per_match:.1f} buts/match"
            })
            
        # Timing
        if dna.timing_profile == "DIESEL":
            dna.markets_to_avoid.append({
                'market': 'FIRST_GOALSCORER',
                'reason': f"DIESEL: {dna.pct_2h:.0f}% buts en 2H"
            })
            dna.profitable_markets.append({
                'market': 'LAST_GOALSCORER',
                'confidence': 'HIGH',
                'players': dna.super_subs[:3] if dna.super_subs else None,
                'reason': f"DIESEL: {dna.pct_2h:.0f}% buts en 2H"
            })
            
        # MVP
        if dna.dependency_profile == "MVP_DEPENDENT":
            confidence = "MAX_BET" if dna.top_scorer in dna.true_clinical_players else "HIGH"
            dna.profitable_markets.append({
                'market': 'ANYTIME_MVP',
                'confidence': confidence,
                'players': [dna.top_scorer],
                'reason': f"{dna.top_scorer_share:.0f}% des buts"
            })
            
        # FINISHER_ONLY
        if dna.finisher_only_players and dna.creative_dependency_profile == "DISTRIBUTED":
            dna.profitable_markets.append({
                'market': 'ANYTIME_FINISHER_ONLY',
                'confidence': 'HIGH',
                'players': dna.finisher_only_players[:2],
                'reason': "FINISHER_ONLY + Créativité distribuée"
            })
            
        # PENALTY_INFLATED warning
        if dna.penalty_inflated_players:
            dna.markets_to_avoid.append({
                'market': 'ANYTIME_GOAL',
                'players': dna.penalty_inflated_players,
                'reason': "PENALTY_INFLATED - Stats gonflées"
            })
            
    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTHODES D'AFFICHAGE V2.2
    # ═══════════════════════════════════════════════════════════════════════════
    
    def print_team_dna(self, team_name: str) -> None:
        """Affiche l'ADN complet V2.2 d'une équipe"""
        dna = self.team_dna.get(team_name)
        if not dna:
            print(f"❌ Équipe '{team_name}' non trouvée")
            return
            
        print("=" * 80)
        print(f"🧬 ADN OFFENSIF V2.2 (14 dim): {dna.team_name} ({dna.league})")
        print("=" * 80)
        
        print(f"\n📝 PROFIL NARRATIF:")
        print(f"   {dna.narrative_profile}")
        
        print(f"\n💪 FORCES:")
        for s in dna.strengths:
            print(f"   ✅ {s}")
            
        print(f"\n⚠️ FAIBLESSES:")
        for w in dna.weaknesses:
            print(f"   ❌ {w}")
            
        print(f"\n📊 VOLUME: {dna.total_goals}G | {dna.goals_per_match:.1f}/match | {dna.volume_profile}")
        print(f"⏱️ TIMING: 1H {dna.pct_1h:.0f}% | 2H {dna.pct_2h:.0f}% | {dna.timing_profile}")
        print(f"👤 DEPENDENCY: {dna.top_scorer} ({dna.top_scorer_share:.0f}%) | {dna.dependency_profile}")
        
        # 🆕 NP-CLINICAL
        print(f"\n🎯 NP-CLINICAL: {dna.team_np_profile} ({dna.team_np_overperformance:+.1f})")
        if dna.true_clinical_players:
            print(f"   TRUE_CLINICAL: {', '.join(dna.true_clinical_players)}")
        if dna.penalty_inflated_players:
            print(f"   ⚠️ PENALTY_INFLATED: {', '.join(dna.penalty_inflated_players)}")
            
        # 🆕 CREATIVITY CHAIN
        print(f"\n🔗 CREATIVITY CHAIN: {dna.creative_dependency_profile} ({dna.creative_dependency_count} playmakers)")
        if dna.finisher_only_players:
            print(f"   FINISHER_ONLY: {', '.join(dna.finisher_only_players)}")
            
        # 🆕 CREATOR-FINISHER DNA (PHASE 2)
        print(f"\n🔗 CREATOR-FINISHER DNA (PHASE 2):")
        print(f"   • Profil: {dna.combo_dependency_profile}")
        print(f"   • Combos identifiés: {dna.all_combos_count}")
        print(f"   • % buts via combos: {dna.combo_goals_pct:.0f}%")
        if dna.top_combo:
            print(f"   • TOP COMBO: {dna.top_combo['creator']} → {dna.top_combo['finisher']}")
            print(f"     {dna.top_combo['occurrences']}x | xG moy: {dna.top_combo['avg_xG']:.2f} | {dna.top_combo['profile']}")
        if dna.elite_combos:
            print(f"   • ELITE COMBOS:")
            for c in dna.elite_combos[:3]:
                print(f"     └─ {c['creator']} → {c['finisher']} ({c['occurrences']}x)")
                
        # 🆕 MOMENTUM DNA (PHASE 2)
        print(f"\n⚡ MOMENTUM DNA (PHASE 2):")
        print(f"   • Profil: {dna.momentum_profile}")
        print(f"   • Burst Rate: {dna.burst_rate:.0f}%")
        print(f"   • Total Bursts: {dna.total_bursts}")
        print(f"   • Écart moyen: {dna.avg_time_between_goals:.0f} min")
        if dna.best_bursts:
            print(f"   • MEILLEURS BURSTS:")
            for b in dna.best_bursts:
                print(f"     └─ {b['burst']} ({b['gap']} min) vs {b['opponent']}")
                
        # MARCHÉS
        print(f"\n" + "─" * 80)
        print(f"💰 MARCHÉS PROFITABLES:")
        for m in dna.profitable_markets:
            players_str = f" → {', '.join(m['players'])}" if m.get('players') else ""
            print(f"   ✅ {m['market']} [{m['confidence']}]{players_str}")
            print(f"      {m['reason']}")
            
        print(f"\n🚫 MARCHÉS À ÉVITER:")
        for m in dna.markets_to_avoid:
            players_str = f" → {', '.join(m.get('players', []))}" if m.get('players') else ""
            print(f"   ❌ {m['market']}{players_str}")
            print(f"      {m['reason']}")
            
    def analyze_matchup(self, home_team: str, away_team: str) -> None:
        """Analyse matchup V2.2 avec Phase 2"""
        home = self.team_dna.get(home_team)
        away = self.team_dna.get(away_team)
        
        if not home or not away:
            print(f"❌ Équipe(s) non trouvée(s)")
            return
            
        print("=" * 80)
        print(f"⚔️ MATCHUP V2.2: {home_team} (🏠) vs {away_team} (✈️)")
        print("=" * 80)
        
        print(f"\n🏠 {home_team}: {home.narrative_profile}")
        print(f"✈️ {away_team}: {away.narrative_profile}")
        
        # 🆕 COMBOS
        print(f"\n🔗 CREATOR-FINISHER COMBOS:")
        if home.top_combo:
            print(f"   🏠 {home.top_combo['creator']} → {home.top_combo['finisher']} ({home.top_combo['occurrences']}x)")
        if away.top_combo:
            print(f"   ✈️ {away.top_combo['creator']} → {away.top_combo['finisher']} ({away.top_combo['occurrences']}x)")
            
        # 🆕 MOMENTUM
        print(f"\n⚡ MOMENTUM:")
        print(f"   🏠 {home_team}: {home.momentum_profile} (burst {home.burst_rate:.0f}%)")
        print(f"   ✈️ {away_team}: {away.momentum_profile} (burst {away.burst_rate:.0f}%)")
        
        # RECOMMANDATIONS
        print(f"\n" + "─" * 80)
        print(f"💰 RECOMMANDATIONS:")
        
        # Combo bets
        if home.elite_combos:
            c = home.elite_combos[0]
            print(f"   🏠 COMBO BET: {c['creator']} Assist + {c['finisher']} Goal")
        if away.elite_combos:
            c = away.elite_combos[0]
            print(f"   ✈️ COMBO BET: {c['creator']} Assist + {c['finisher']} Goal")
            
        # Live betting momentum
        if home.momentum_profile == "BURST_SCORER":
            print(f"   ⚡ LIVE: Si {home_team} marque → BACK Next Goal {home_team}")
        if away.momentum_profile == "BURST_SCORER":
            print(f"   ⚡ LIVE: Si {away_team} marque → BACK Next Goal {away_team}")
            
        # Clash momentum
        if home.momentum_profile == "BURST_SCORER" and away.momentum_profile == "BURST_SCORER":
            print(f"   🔥 BOTH BURST_SCORER → BACK Over 3.5 Goals (match ouvert)")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    engineer = FeatureEngineerV22Phase2()
    engineer.initialize()
    
    # Test équipes
    for team in ["Liverpool", "Bayern Munich", "Manchester City"]:
        engineer.print_team_dna(team)
        print("\n" + "═" * 80 + "\n")
        
    # Test matchup
    engineer.analyze_matchup("Liverpool", "Manchester City")
