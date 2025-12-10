"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🧬 FEATURE ENGINEER V2.3 PHASE 3 - TEAM-CENTRIC HEDGE FUND GRADE            ║
║                                                                              ║
║  PHILOSOPHIE MON_PS:                                                         ║
║  ═══════════════════════════════════════════════════════════════════════════ ║
║  • ÉQUIPE au centre (comme un trou noir)                                    ║
║  • Chaque équipe = 1 ADN = 1 empreinte digitale UNIQUE                      ║
║  • Les marchés sont des CONSÉQUENCES de l'ADN, pas l'inverse                ║
║                                                                              ║
║  16 DIMENSIONS ADN:                                                          ║
║  ═══════════════════════════════════════════════════════════════════════════ ║
║  Phase 1 (V2.1):                                                             ║
║   1. Volume DNA          7. Super_Sub DNA      11. NP-Clinical DNA           ║
║   2. Timing DNA          8. Penalty DNA        12. Creativity Chain DNA      ║
║   3. Dependency DNA      9. Creativity DNA                                   ║
║   4. Style DNA          10. Form DNA                                         ║
║   5. Home/Away DNA                                                           ║
║   6. Efficiency DNA                                                          ║
║                                                                              ║
║  Phase 2 (V2.2):                                                             ║
║  13. Creator-Finisher DNA                                                    ║
║  14. Momentum DNA                                                            ║
║                                                                              ║
║  Phase 3 (V2.3) - NOUVEAU:                                                   ║
║  15. First Goal Impact DNA (FRONT_RUNNER, COMEBACK_KING, FRAGILE)           ║
║  16. Game State DNA (KILLER, SETTLER, COMEBACK_SPECIALIST)                   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
sys.path.insert(0, '/home/Mon_ps')

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json

from agents.attack_v1.data.loader_v5_4_phase3 import (
    AttackDataLoaderV54Phase3,
    FirstGoalImpactDNA,
    GameStateDNA
)
from agents.attack_v1.features.engineer_v2_2_phase2 import (
    FeatureEngineerV22Phase2,
    TeamAttackDNAv22
)

DATA_DIR = Path('/home/Mon_ps/data')


# ═══════════════════════════════════════════════════════════════════════════════
# TEAM ATTACK DNA V2.3 - 16 DIMENSIONS COMPLÈTES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TeamAttackDNAv23(TeamAttackDNAv22):
    """
    ADN OFFENSIF COMPLET d'une équipe - VERSION 2.3 (16 DIMENSIONS)
    
    Hérite de V2.2 (14 dimensions) et ajoute:
    • 15. FIRST GOAL IMPACT DNA
    • 16. GAME STATE DNA
    """
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🆕 15. FIRST GOAL IMPACT DNA (PHASE 3)
    # Réaction psychologique selon qui marque en premier
    # ═══════════════════════════════════════════════════════════════════════════
    first_goal_profile: str = ""              # FRONT_RUNNER, COMEBACK_KING, FRAGILE, RESILIENT
    matches_scored_first: int = 0
    matches_conceded_first: int = 0
    win_rate_scoring_first: float = 0.0
    win_rate_conceding_first: float = 0.0
    comeback_rate: float = 0.0
    collapse_rate: float = 0.0
    killer_instinct_fg: float = 0.0           # Buts après avoir ouvert le score
    comeback_examples: List[Dict] = field(default_factory=list)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🆕 16. GAME STATE DNA (PHASE 3)
    # Comportement selon le score actuel
    # ═══════════════════════════════════════════════════════════════════════════
    game_state_profile: str = ""              # KILLER, SETTLER, COMEBACK_SPECIALIST, BALANCED
    pct_goals_leading: float = 0.0
    pct_goals_trailing: float = 0.0
    pct_goals_level: float = 0.0
    goals_when_leading: int = 0
    goals_when_trailing: int = 0
    goals_when_level: int = 0
    killer_index: float = 0.0
    resilience_index: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE ENGINEER V2.3 PHASE 3 - 16 DIMENSIONS
# ═══════════════════════════════════════════════════════════════════════════════

class FeatureEngineerV23Phase3:
    """
    Feature Engineer V2.3 PHASE 3 - TEAM-CENTRIC HEDGE FUND GRADE
    
    Construit l'ADN COMPLET de chaque équipe avec 16 dimensions
    
    PHILOSOPHIE: Chaque équipe = ADN UNIQUE = Empreinte digitale
    Les marchés sont des CONSÉQUENCES de l'ADN, pas l'inverse.
    """
    
    def __init__(self):
        self.loader = AttackDataLoaderV54Phase3()
        self.team_dna: Dict[str, TeamAttackDNAv23] = {}
        self.matches_played = 13  # À ajuster selon la saison
        
    def initialize(self) -> None:
        """Initialise le Feature Engineer"""
        print("=" * 80)
        print("🎯 FEATURE ENGINEER V2.3 PHASE 3 - 16 DIMENSIONS ADN")
        print("=" * 80)
        
        self.loader.load_all()
        self._build_all_team_dna()
        
        print(f"\n✅ {len(self.team_dna)} équipes avec ADN COMPLET V2.3 (16 dimensions)")
        
    def _build_all_team_dna(self) -> None:
        """Construit l'ADN de toutes les équipes"""
        print("\n📊 Construction ADN V2.3 par équipe...")
        
        for team_name, team in self.loader.teams.items():
            dna = self._build_team_dna(team_name)
            self.team_dna[team_name] = dna
            
    def _build_team_dna(self, team_name: str) -> TeamAttackDNAv23:
        """Construit l'ADN complet d'une équipe V2.3 (16 dimensions)"""
        
        team = self.loader.teams.get(team_name)
        if not team:
            return TeamAttackDNAv23(team_name=team_name)
            
        # Créer le DNA V2.3
        dna = TeamAttackDNAv23(team_name=team_name, league=team.league)
        
        players = team.players
        scorers = [p for p in players if p.goals > 0]
        
        # ═══════════════════════════════════════════════════════════════════════
        # DIMENSIONS 1-14 (héritées de V2.2)
        # ═══════════════════════════════════════════════════════════════════════
        self._build_v22_dimensions(dna, team, players, scorers, team_name)
        
        # ═══════════════════════════════════════════════════════════════════════
        # 🆕 DIMENSION 15: FIRST GOAL IMPACT DNA (PHASE 3)
        # ═══════════════════════════════════════════════════════════════════════
        self._build_first_goal_impact_dna(dna, team_name)
        
        # ═══════════════════════════════════════════════════════════════════════
        # 🆕 DIMENSION 16: GAME STATE DNA (PHASE 3)
        # ═══════════════════════════════════════════════════════════════════════
        self._build_game_state_dna(dna, team_name)
        
        # ═══════════════════════════════════════════════════════════════════════
        # PROFIL NARRATIF FINAL + MARCHÉS
        # ═══════════════════════════════════════════════════════════════════════
        self._build_narrative_v23(dna)
        self._identify_profitable_markets_v23(dna)
        
        return dna
        
    def _build_v22_dimensions(self, dna, team, players, scorers, team_name) -> None:
        """Construit les dimensions 1-14 (héritées de V2.2)"""
        
        # ═══════════════════════════════════════════════════════════════════════
        # DIMENSIONS 1-12 (V2.1)
        # ═══════════════════════════════════════════════════════════════════════
        
        # 1. VOLUME DNA
        dna.total_goals = sum(p.goals for p in players)
        dna.total_xG = sum(p.xG for p in players)
        dna.goals_per_match = dna.total_goals / self.matches_played if self.matches_played > 0 else 0
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
            '76-90': sum(p.goals_76_90 for p in players),
            '90+': sum(p.goals_90_plus for p in players)
        }
        
        clutch = dna.goals_by_period.get('76-90', 0) + dna.goals_by_period.get('90+', 0)
        if dna.total_goals > 0:
            dna.pct_clutch = (clutch / dna.total_goals) * 100
            
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
                
        # 4-6. Style, Home/Away, Efficiency DNA
        dna.goals_open_play = sum(p.goals_open_play for p in players)
        dna.goals_set_piece = sum(p.goals_corner + p.goals_set_piece for p in players)
        dna.goals_penalty = sum(p.penalty_goals for p in players)
        dna.goals_header = sum(p.goals_header for p in players)
        
        dna.goals_home = sum(p.goals_home for p in players)
        dna.goals_away = sum(p.goals_away for p in players)
        if dna.goals_away > 0:
            dna.home_away_ratio = dna.goals_home / dna.goals_away
            
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
            
        # 8-10. Penalty, Creativity, Form DNA
        penalty_takers = [p for p in players if p.is_penalty_taker]
        if penalty_takers:
            dna.penalty_taker = max(penalty_takers, key=lambda p: p.penalty_goals).player_name
            
        dna.total_assists = sum(p.assists for p in players)
        dna.total_xA = sum(p.xA for p in players)
        
        dna.hot_streak_players = [p.player_name for p in players if p.finishing_trend == "HOT_STREAK"]
        dna.value_regression_candidates = [p.player_name for p in players if p.xG >= 4 and p.xG_overperformance <= -1.5]
        
        # 11. NP-CLINICAL DNA
        dna.team_np_goals = sum(p.np_goals for p in players)
        dna.team_np_xG = sum(p.np_xG for p in players)
        dna.team_np_overperformance = dna.team_np_goals - dna.team_np_xG
        
        dna.true_clinical_players = [p.player_name for p in players if p.np_clinical_profile == "TRUE_CLINICAL" and p.goals >= 3]
        dna.clinical_players = [p.player_name for p in players if p.np_clinical_profile in ["TRUE_CLINICAL", "CLINICAL"] and p.goals >= 3]
        dna.penalty_inflated_players = [p.player_name for p in players if p.np_clinical_profile == "PENALTY_INFLATED"]
        
        if len(dna.true_clinical_players) >= 2 or dna.team_np_overperformance >= 3:
            dna.team_np_profile = "CLINICAL_TEAM"
        elif dna.team_np_overperformance <= -3:
            dna.team_np_profile = "WASTEFUL_TEAM"
        else:
            dna.team_np_profile = "AVERAGE"
            
        # 12. CREATIVITY CHAIN DNA
        dna.buildup_architects = [p.player_name for p in players if p.chain_profile == "BUILDUP_ARCHITECT" and p.xGChain >= 3]
        dna.finisher_only_players = [p.player_name for p in players if p.chain_profile == "FINISHER_ONLY" and p.goals >= 3]
        dna.playmakers = [p.player_name for p in players if p.buildup_profile == "PLAYMAKER" and p.xGChain >= 2]
        
        dna.creative_dependency_count = len([p for p in players if p.buildup_ratio >= 0.6 and p.xGChain >= 2])
        if dna.creative_dependency_count <= 2:
            dna.creative_dependency_profile = "HIGH_DEPENDENCY"
        elif dna.creative_dependency_count <= 4:
            dna.creative_dependency_profile = "MODERATE"
        else:
            dna.creative_dependency_profile = "DISTRIBUTED"
            
        # ═══════════════════════════════════════════════════════════════════════
        # DIMENSIONS 13-14 (V2.2 - PHASE 2)
        # ═══════════════════════════════════════════════════════════════════════
        
        # 13. CREATOR-FINISHER DNA
        combos = self.loader.get_team_combos(team_name, min_occurrences=2)
        dna.all_combos_count = len(combos)
        
        dna.elite_combos = [
            {'creator': c.creator, 'finisher': c.finisher, 'occurrences': c.occurrences}
            for c in combos if c.combo_profile == "ELITE_COMBO"
        ]
        dna.strong_combos = [
            {'creator': c.creator, 'finisher': c.finisher, 'occurrences': c.occurrences}
            for c in combos if c.combo_profile in ["ELITE_COMBO", "STRONG_COMBO"]
        ]
        
        if combos:
            top = combos[0]
            dna.top_combo = {
                'creator': top.creator,
                'finisher': top.finisher,
                'occurrences': top.occurrences,
                'profile': top.combo_profile
            }
            
        combo_goals = sum(c.occurrences for c in combos)
        if dna.total_goals > 0:
            dna.combo_goals_pct = (combo_goals / dna.total_goals) * 100
            
        if len(dna.elite_combos) >= 2 or dna.combo_goals_pct >= 50:
            dna.combo_dependency_profile = "COMBO_RELIANT"
        elif len(dna.strong_combos) >= 3:
            dna.combo_dependency_profile = "COMBO_DIVERSE"
        else:
            dna.combo_dependency_profile = "NO_COMBO"
            
        # 14. MOMENTUM DNA
        momentum = self.loader.get_team_momentum(team_name)
        if momentum:
            dna.momentum_profile = momentum.momentum_profile
            dna.burst_rate = momentum.burst_rate
            dna.total_bursts = momentum.total_bursts
            dna.avg_time_between_goals = momentum.avg_time_between_goals
            dna.best_bursts = momentum.best_bursts[:3]
            
    def _build_first_goal_impact_dna(self, dna: TeamAttackDNAv23, team_name: str) -> None:
        """
        🆕 DIMENSION 15: FIRST GOAL IMPACT DNA
        
        Profils:
        • FRONT_RUNNER: Domine quand marque en premier (win_rate >= 80%)
        • COMEBACK_KING: Revient souvent quand mené (comeback_rate >= 40%)
        • FRAGILE: S'effondre quand mené
        • RESILIENT: Stable
        """
        fg_dna = self.loader.get_first_goal_dna(team_name)
        
        if not fg_dna:
            dna.first_goal_profile = "NO_DATA"
            return
            
        dna.first_goal_profile = fg_dna.first_goal_profile
        dna.matches_scored_first = fg_dna.matches_scored_first
        dna.matches_conceded_first = fg_dna.matches_conceded_first
        dna.win_rate_scoring_first = fg_dna.win_rate_scoring_first
        dna.win_rate_conceding_first = fg_dna.win_rate_conceding_first
        dna.comeback_rate = fg_dna.comeback_rate
        dna.collapse_rate = fg_dna.collapse_rate
        dna.killer_instinct_fg = fg_dna.killer_instinct
        dna.comeback_examples = fg_dna.comeback_matches[:3]
        
    def _build_game_state_dna(self, dna: TeamAttackDNAv23, team_name: str) -> None:
        """
        🆕 DIMENSION 16: GAME STATE DNA
        
        Profils:
        • KILLER: Continue à marquer quand mène
        • SETTLER: Se contente du score
        • COMEBACK_SPECIALIST: Marque beaucoup quand mené
        • BALANCED
        """
        gs_dna = self.loader.get_game_state_dna(team_name)
        
        if not gs_dna:
            dna.game_state_profile = "NO_DATA"
            return
            
        dna.game_state_profile = gs_dna.game_state_profile
        dna.pct_goals_leading = gs_dna.pct_goals_leading
        dna.pct_goals_trailing = gs_dna.pct_goals_trailing
        dna.pct_goals_level = gs_dna.pct_goals_level
        dna.goals_when_leading = gs_dna.goals_when_leading
        dna.goals_when_trailing = gs_dna.goals_when_trailing
        dna.goals_when_level = gs_dna.goals_when_level
        dna.killer_index = gs_dna.killer_index
        dna.resilience_index = gs_dna.resilience_index
        
    def _build_narrative_v23(self, dna: TeamAttackDNAv23) -> None:
        """Construit le profil narratif UNIQUE V2.3"""
        parts = []
        dna.strengths = []
        dna.weaknesses = []
        
        # Volume
        if dna.volume_profile == "HIGH_SCORING":
            parts.append(f"Machine ({dna.goals_per_match:.1f}/match)")
            dna.strengths.append("Puissance de feu")
            
        # Timing
        if dna.timing_profile == "DIESEL":
            parts.append(f"Diesel ({dna.pct_2h:.0f}% 2H)")
            dna.strengths.append("Monte en puissance")
        elif dna.timing_profile == "CLUTCH_TEAM":
            parts.append(f"Clutch ({dna.pct_clutch:.0f}%)")
            dna.strengths.append("Décisifs")
            
        # 🆕 First Goal Impact
        if dna.first_goal_profile == "FRONT_RUNNER":
            parts.append(f"Front Runner ({dna.win_rate_scoring_first:.0f}%)")
            dna.strengths.append("Domine après avoir marqué")
        elif dna.first_goal_profile == "COMEBACK_KING":
            parts.append(f"Comeback King ({dna.comeback_rate:.0f}%)")
            dna.strengths.append("Revient quand mené")
        elif dna.first_goal_profile == "FRAGILE":
            parts.append("Fragile")
            dna.weaknesses.append("S'effondre quand mené")
            
        # 🆕 Game State
        if dna.game_state_profile == "KILLER":
            parts.append(f"Killer ({dna.pct_goals_leading:.0f}% en menant)")
            dna.strengths.append("Continue en menant")
        elif dna.game_state_profile == "SETTLER":
            parts.append("Settler")
            dna.weaknesses.append("Se contente du score")
            
        # Momentum
        if dna.momentum_profile == "BURST_SCORER":
            parts.append(f"Burst ({dna.burst_rate:.0f}%)")
            dna.strengths.append("Marque en série")
        elif dna.momentum_profile == "STEADY_SCORER":
            parts.append(f"Steady ({dna.avg_time_between_goals:.0f}min)")
            
        # NP-Clinical
        if dna.team_np_profile == "WASTEFUL_TEAM":
            dna.weaknesses.append("Gaspille des occasions")
            
        # Dependency
        if dna.dependency_profile == "MVP_DEPENDENT":
            dna.weaknesses.append(f"Dépendant de {dna.top_scorer}")
        elif dna.dependency_profile == "DISTRIBUTED":
            dna.strengths.append("Menace variée")
            
        dna.narrative_profile = " | ".join(parts) if parts else "Profil équilibré"
        
    def _identify_profitable_markets_v23(self, dna: TeamAttackDNAv23) -> None:
        """Identifie les marchés profitables V2.3 - ADN UNIQUE"""
        dna.profitable_markets = []
        dna.markets_to_avoid = []
        
        # ═══════════════════════════════════════════════════════════════════════
        # 🆕 FIRST GOAL IMPACT MARKETS (PHASE 3)
        # ═══════════════════════════════════════════════════════════════════════
        if dna.first_goal_profile == "FRONT_RUNNER":
            dna.profitable_markets.append({
                'market': 'WIN_IF_SCORES_FIRST',
                'confidence': 'HIGH',
                'players': None,
                'reason': f"FRONT_RUNNER: {dna.win_rate_scoring_first:.0f}% win rate après 1er but"
            })
            
        if dna.first_goal_profile == "COMEBACK_KING":
            dna.profitable_markets.append({
                'market': 'LIVE_BACK_WHEN_TRAILING',
                'confidence': 'HIGH',
                'players': None,
                'reason': f"COMEBACK_KING: {dna.comeback_rate:.0f}% comeback rate"
            })
            
        if dna.first_goal_profile == "FRAGILE":
            dna.markets_to_avoid.append({
                'market': 'BACK_WHEN_TRAILING',
                'reason': f"FRAGILE: Win rate mené = {dna.win_rate_conceding_first:.0f}%"
            })
            dna.profitable_markets.append({
                'market': 'LAY_WHEN_OPPONENT_TRAILS',
                'confidence': 'MEDIUM',
                'players': None,
                'reason': f"FRAGILE contre: S'effondre quand mené"
            })
            
        # ═══════════════════════════════════════════════════════════════════════
        # 🆕 GAME STATE MARKETS (PHASE 3)
        # ═══════════════════════════════════════════════════════════════════════
        if dna.game_state_profile == "KILLER":
            dna.profitable_markets.append({
                'market': 'LIVE_OVER_WHEN_LEADING',
                'confidence': 'HIGH',
                'players': None,
                'reason': f"KILLER: {dna.pct_goals_leading:.0f}% buts en menant, Killer Index {dna.killer_index:.1f}"
            })
            
        if dna.game_state_profile == "SETTLER":
            dna.markets_to_avoid.append({
                'market': 'OVER_WHEN_LEADING',
                'reason': f"SETTLER: Seulement {dna.pct_goals_leading:.0f}% buts en menant"
            })
            dna.profitable_markets.append({
                'market': 'LIVE_UNDER_WHEN_LEADING',
                'confidence': 'MEDIUM',
                'players': None,
                'reason': f"SETTLER: Se contente du score"
            })
            
        if dna.game_state_profile == "COMEBACK_SPECIALIST":
            dna.profitable_markets.append({
                'market': 'LIVE_BACK_WHEN_TRAILING',
                'confidence': 'HIGH',
                'players': None,
                'reason': f"COMEBACK_SPECIALIST: {dna.pct_goals_trailing:.0f}% buts quand mené"
            })
            
        # ═══════════════════════════════════════════════════════════════════════
        # MARCHÉS PHASE 2 (13-14)
        # ═══════════════════════════════════════════════════════════════════════
        if dna.elite_combos:
            for combo in dna.elite_combos[:2]:
                dna.profitable_markets.append({
                    'market': 'COMBO_BET',
                    'confidence': 'HIGH',
                    'players': [f"{combo['creator']} Assist + {combo['finisher']} Goal"],
                    'reason': f"ELITE_COMBO: {combo['occurrences']}x cette saison"
                })
                
        if dna.momentum_profile == "BURST_SCORER":
            dna.profitable_markets.append({
                'market': 'LIVE_NEXT_GOAL',
                'confidence': 'HIGH',
                'players': None,
                'reason': f"BURST_SCORER: {dna.burst_rate:.0f}% burst rate"
            })
            
        # ═══════════════════════════════════════════════════════════════════════
        # MARCHÉS PHASE 1 (1-12)
        # ═══════════════════════════════════════════════════════════════════════
        if dna.timing_profile == "DIESEL":
            dna.markets_to_avoid.append({
                'market': 'FIRST_GOALSCORER',
                'reason': f"DIESEL: {dna.pct_2h:.0f}% buts en 2H"
            })
            dna.profitable_markets.append({
                'market': 'LAST_GOALSCORER',
                'confidence': 'HIGH',
                'players': dna.super_subs[:2] if dna.super_subs else None,
                'reason': f"DIESEL: {dna.pct_2h:.0f}% buts en 2H"
            })
            
        if dna.dependency_profile == "MVP_DEPENDENT":
            conf = "MAX_BET" if dna.top_scorer in dna.true_clinical_players else "HIGH"
            dna.profitable_markets.append({
                'market': 'ANYTIME_MVP',
                'confidence': conf,
                'players': [dna.top_scorer],
                'reason': f"{dna.top_scorer_share:.0f}% des buts"
            })
            
        if dna.penalty_inflated_players:
            dna.markets_to_avoid.append({
                'market': 'ANYTIME_GOAL',
                'players': dna.penalty_inflated_players,
                'reason': "PENALTY_INFLATED - Stats gonflées"
            })
            
    # ═══════════════════════════════════════════════════════════════════════════
    # AFFICHAGE V2.3
    # ═══════════════════════════════════════════════════════════════════════════
    
    def print_team_dna(self, team_name: str) -> None:
        """Affiche l'ADN COMPLET V2.3 (16 dimensions) d'une équipe"""
        dna = self.team_dna.get(team_name)
        if not dna:
            print(f"❌ Équipe '{team_name}' non trouvée")
            return
            
        print("=" * 80)
        print(f"🧬 ADN OFFENSIF V2.3 (16 dim): {dna.team_name} ({dna.league})")
        print("=" * 80)
        
        print(f"\n📝 PROFIL NARRATIF UNIQUE:")
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
            
        # Dimensions 1-6
        print(f"\n📊 VOLUME: {dna.total_goals}G | {dna.goals_per_match:.1f}/match | {dna.volume_profile}")
        print(f"⏱️ TIMING: 1H {dna.pct_1h:.0f}% | 2H {dna.pct_2h:.0f}% | {dna.timing_profile}")
        print(f"👤 DEPENDENCY: {dna.top_scorer} ({dna.top_scorer_share:.0f}%) | {dna.dependency_profile}")
        
        # 11-12: NP-Clinical + Chain
        print(f"\n🎯 NP-CLINICAL: {dna.team_np_profile} ({dna.team_np_overperformance:+.1f})")
        print(f"🔗 CREATIVITY: {dna.creative_dependency_profile} ({dna.creative_dependency_count} playmakers)")
        
        # 13-14: Phase 2
        print(f"\n🔗 COMBOS: {dna.combo_dependency_profile}")
        if dna.top_combo:
            print(f"   TOP: {dna.top_combo.get('creator', '')} → {dna.top_combo.get('finisher', '')} ({dna.top_combo.get('occurrences', 0)}x)")
        print(f"⚡ MOMENTUM: {dna.momentum_profile} (burst {dna.burst_rate:.0f}%)")
        
        # 🆕 15-16: Phase 3
        print(f"\n🎯 FIRST GOAL IMPACT (NOUVEAU):")
        print(f"   • Profil: {dna.first_goal_profile}")
        print(f"   • Si marque 1er ({dna.matches_scored_first} matchs): Win {dna.win_rate_scoring_first:.0f}%")
        print(f"   • Si encaisse 1er ({dna.matches_conceded_first} matchs): Win {dna.win_rate_conceding_first:.0f}%")
        print(f"   • Comeback Rate: {dna.comeback_rate:.0f}%")
        print(f"   • Collapse Rate: {dna.collapse_rate:.0f}%")
        
        print(f"\n🔥 GAME STATE (NOUVEAU):")
        print(f"   • Profil: {dna.game_state_profile}")
        print(f"   • Buts en menant: {dna.goals_when_leading} ({dna.pct_goals_leading:.0f}%)")
        print(f"   • Buts quand mené: {dna.goals_when_trailing} ({dna.pct_goals_trailing:.0f}%)")
        print(f"   • Buts à égalité: {dna.goals_when_level} ({dna.pct_goals_level:.0f}%)")
        print(f"   • Killer Index: {dna.killer_index:.2f}")
        
        # Marchés
        print(f"\n" + "─" * 80)
        print(f"💰 MARCHÉS PROFITABLES POUR {dna.team_name}:")
        for m in dna.profitable_markets:
            players_str = f" → {', '.join(m.get('players', []))}" if m.get('players') else ""
            print(f"   ✅ {m['market']} [{m['confidence']}]{players_str}")
            print(f"      {m['reason']}")
            
        print(f"\n🚫 MARCHÉS À ÉVITER:")
        for m in dna.markets_to_avoid:
            players_str = f" → {', '.join(m.get('players', []))}" if m.get('players') else ""
            print(f"   ❌ {m['market']}{players_str}")
            print(f"      {m.get('reason', '')}")
            
    def analyze_matchup(self, home_team: str, away_team: str) -> None:
        """Analyse matchup V2.3 avec 16 dimensions"""
        home = self.team_dna.get(home_team)
        away = self.team_dna.get(away_team)
        
        if not home or not away:
            print(f"❌ Équipe(s) non trouvée(s)")
            return
            
        print("=" * 80)
        print(f"⚔️ MATCHUP V2.3: {home_team} (🏠) vs {away_team} (✈️)")
        print("=" * 80)
        
        print(f"\n🏠 {home_team}: {home.narrative_profile}")
        print(f"✈️ {away_team}: {away.narrative_profile}")
        
        # First Goal Impact clash
        print(f"\n🎯 FIRST GOAL IMPACT CLASH:")
        print(f"   🏠 {home_team}: {home.first_goal_profile} (Win 1er: {home.win_rate_scoring_first:.0f}%, Comeback: {home.comeback_rate:.0f}%)")
        print(f"   ✈️ {away_team}: {away.first_goal_profile} (Win 1er: {away.win_rate_scoring_first:.0f}%, Comeback: {away.comeback_rate:.0f}%)")
        
        # Game State clash
        print(f"\n🔥 GAME STATE CLASH:")
        print(f"   🏠 {home_team}: {home.game_state_profile} (Killer: {home.killer_index:.1f})")
        print(f"   ✈️ {away_team}: {away.game_state_profile} (Killer: {away.killer_index:.1f})")
        
        # Momentum
        print(f"\n⚡ MOMENTUM:")
        print(f"   🏠 {home_team}: {home.momentum_profile} (burst {home.burst_rate:.0f}%)")
        print(f"   ✈️ {away_team}: {away.momentum_profile} (burst {away.burst_rate:.0f}%)")
        
        # Recommandations
        print(f"\n" + "─" * 80)
        print(f"💰 RECOMMANDATIONS:")
        
        # First Goal scenarios
        if home.first_goal_profile == "FRONT_RUNNER":
            print(f"   🏠 Si {home_team} marque 1er → BACK {home_team} Win ({home.win_rate_scoring_first:.0f}%)")
        if away.first_goal_profile == "FRAGILE":
            print(f"   ✈️ Si {away_team} mené → LAY {away_team} (FRAGILE)")
            
        if home.first_goal_profile == "COMEBACK_KING":
            print(f"   🏠 Si {home_team} mené → BACK {home_team} (Comeback {home.comeback_rate:.0f}%)")
            
        # Game State scenarios
        if home.game_state_profile == "KILLER":
            print(f"   🏠 LIVE: Si {home_team} mène → BACK Over (KILLER)")
        if away.game_state_profile == "SETTLER":
            print(f"   ✈️ LIVE: Si {away_team} mène → LAY Over (SETTLER)")
            
        # Momentum
        if home.momentum_profile == "BURST_SCORER" and away.momentum_profile == "BURST_SCORER":
            print(f"   🔥 BOTH BURST → BACK Over 3.5 (match ouvert)")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    engineer = FeatureEngineerV23Phase3()
    engineer.initialize()
    
    # Test équipes
    for team in ["Liverpool", "Bayern Munich", "Real Madrid"]:
        engineer.print_team_dna(team)
        print("\n" + "═" * 80 + "\n")
        
    # Test matchup
    engineer.analyze_matchup("Liverpool", "Real Madrid")
