"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🧬 FEATURE ENGINEER V2.4 PHASE 4 - TEAM-CENTRIC HEDGE FUND GRADE            ║
║                                                                              ║
║  PHILOSOPHIE MON_PS:                                                         ║
║  ═══════════════════════════════════════════════════════════════════════════ ║
║  • ÉQUIPE au centre (comme un trou noir)                                    ║
║  • Chaque équipe = 1 ADN = 1 empreinte digitale UNIQUE                      ║
║  • Les marchés sont des CONSÉQUENCES de l'ADN, pas l'inverse                ║
║                                                                              ║
║  17 DIMENSIONS ADN:                                                          ║
║  ═══════════════════════════════════════════════════════════════════════════ ║
║  Phase 1 (V2.1): 1-12 (Volume, Timing, Dependency, Style, Home/Away,        ║
║                        Efficiency, Super_Sub, Penalty, Creativity, Form,     ║
║                        NP-Clinical, Creativity Chain)                        ║
║                                                                              ║
║  Phase 2 (V2.2): 13. Creator-Finisher DNA, 14. Momentum DNA                 ║
║                                                                              ║
║  Phase 3 (V2.3): 15. First Goal Impact DNA, 16. Game State DNA              ║
║                                                                              ║
║  Phase 4 (V2.4) - NOUVEAU:                                                   ║
║  17. EXTERNAL FACTORS DNA (Horaires: LUNCH, AFTERNOON, PRIME_TIME)          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
sys.path.insert(0, '/home/Mon_ps')

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json

from agents.attack_v1.data.loader_v5_5_phase4 import (
    AttackDataLoaderV55Phase4,
    ExternalFactorsDNA
)
from agents.attack_v1.features.engineer_v2_3_phase3 import (
    FeatureEngineerV23Phase3,
    TeamAttackDNAv23
)

DATA_DIR = Path('/home/Mon_ps/data')


# ═══════════════════════════════════════════════════════════════════════════════
# TEAM ATTACK DNA V2.4 - 17 DIMENSIONS COMPLÈTES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TeamAttackDNAv24(TeamAttackDNAv23):
    """
    ADN OFFENSIF COMPLET d'une équipe - VERSION 2.4 (17 DIMENSIONS)
    
    Hérite de V2.3 (16 dimensions) et ajoute:
    • 17. EXTERNAL FACTORS DNA
    """
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🆕 17. EXTERNAL FACTORS DNA (PHASE 4)
    # Performance selon les horaires
    # ═══════════════════════════════════════════════════════════════════════════
    schedule_profile: str = ""              # PRIME_TIME_BEAST, AFTERNOON_SPECIALIST, etc.
    
    # Moyennes par créneau
    lunch_avg: float = 0.0                  # 12h-15h
    afternoon_avg: float = 0.0              # 15h-19h
    prime_time_avg: float = 0.0             # 19h-24h
    overall_schedule_avg: float = 0.0
    
    # Deltas
    lunch_delta: float = 0.0
    afternoon_delta: float = 0.0
    prime_time_delta: float = 0.0
    
    # Best/Worst
    best_time_slot: str = ""
    worst_time_slot: str = ""
    best_slot_avg: float = 0.0
    worst_slot_avg: float = 0.0
    schedule_max_delta: float = 0.0
    
    # Détails
    lunch_matches: int = 0
    afternoon_matches: int = 0
    prime_time_matches: int = 0


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE ENGINEER V2.4 PHASE 4 - 17 DIMENSIONS
# ═══════════════════════════════════════════════════════════════════════════════

class FeatureEngineerV24Phase4:
    """
    Feature Engineer V2.4 PHASE 4 - TEAM-CENTRIC HEDGE FUND GRADE
    
    Construit l'ADN COMPLET de chaque équipe avec 17 dimensions
    
    PHILOSOPHIE: Chaque équipe = ADN UNIQUE = Empreinte digitale
    Les marchés sont des CONSÉQUENCES de l'ADN, pas l'inverse.
    """
    
    def __init__(self):
        self.loader = AttackDataLoaderV55Phase4()
        self.team_dna: Dict[str, TeamAttackDNAv24] = {}
        self.matches_played = 13  # À ajuster selon la saison
        
    def initialize(self) -> None:
        """Initialise le Feature Engineer"""
        print("=" * 80)
        print("🎯 FEATURE ENGINEER V2.4 PHASE 4 - 17 DIMENSIONS ADN")
        print("=" * 80)
        
        self.loader.load_all()
        self._build_all_team_dna()
        
        print(f"\n✅ {len(self.team_dna)} équipes avec ADN COMPLET V2.4 (17 dimensions)")
        
    def _build_all_team_dna(self) -> None:
        """Construit l'ADN de toutes les équipes"""
        print("\n📊 Construction ADN V2.4 par équipe...")
        
        for team_name, team in self.loader.teams.items():
            dna = self._build_team_dna(team_name)
            self.team_dna[team_name] = dna
            
    def _build_team_dna(self, team_name: str) -> TeamAttackDNAv24:
        """Construit l'ADN complet d'une équipe V2.4 (17 dimensions)"""
        
        team = self.loader.teams.get(team_name)
        if not team:
            return TeamAttackDNAv24(team_name=team_name)
            
        # Créer le DNA V2.4
        dna = TeamAttackDNAv24(team_name=team_name, league=team.league)
        
        players = team.players
        scorers = [p for p in players if p.goals > 0]
        
        # ═══════════════════════════════════════════════════════════════════════
        # DIMENSIONS 1-16 (héritées de V2.3)
        # ═══════════════════════════════════════════════════════════════════════
        self._build_v23_dimensions(dna, team, players, scorers, team_name)
        
        # ═══════════════════════════════════════════════════════════════════════
        # 🆕 DIMENSION 17: EXTERNAL FACTORS DNA (PHASE 4)
        # ═══════════════════════════════════════════════════════════════════════
        self._build_external_factors_dna(dna, team_name)
        
        # ═══════════════════════════════════════════════════════════════════════
        # PROFIL NARRATIF FINAL + MARCHÉS
        # ═══════════════════════════════════════════════════════════════════════
        self._build_narrative_v24(dna)
        self._identify_profitable_markets_v24(dna)
        
        return dna
        
    def _build_v23_dimensions(self, dna, team, players, scorers, team_name) -> None:
        """Construit les dimensions 1-16 (héritées de V2.3)"""
        
        # ═══════════════════════════════════════════════════════════════════════
        # DIMENSIONS 1-12 (V2.1 - Phase 1)
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
                
        # 4-10. Autres dimensions Phase 1
        dna.goals_open_play = sum(p.goals_open_play for p in players)
        dna.goals_penalty = sum(p.penalty_goals for p in players)
        dna.goals_home = sum(p.goals_home for p in players)
        dna.goals_away = sum(p.goals_away for p in players)
        if dna.goals_away > 0:
            dna.home_away_ratio = dna.goals_home / dna.goals_away
            
        super_subs = [p for p in players if p.playing_time_profile == "SUPER_SUB" and p.goals >= 2]
        dna.super_subs = [p.player_name for p in super_subs]
        dna.super_sub_pct = (sum(p.goals for p in super_subs) / dna.total_goals * 100) if dna.total_goals > 0 else 0
        
        if dna.super_sub_pct >= 15:
            dna.bench_strength = "STRONG_BENCH"
        else:
            dna.bench_strength = "WEAK_BENCH"
            
        # 11. NP-CLINICAL DNA
        dna.team_np_goals = sum(p.np_goals for p in players)
        dna.team_np_xG = sum(p.np_xG for p in players)
        dna.team_np_overperformance = dna.team_np_goals - dna.team_np_xG
        
        dna.true_clinical_players = [p.player_name for p in players if p.np_clinical_profile == "TRUE_CLINICAL" and p.goals >= 3]
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
        # DIMENSIONS 13-14 (V2.2 - Phase 2)
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
            
        if len(dna.elite_combos) >= 2:
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
            
        # ═══════════════════════════════════════════════════════════════════════
        # DIMENSIONS 15-16 (V2.3 - Phase 3)
        # ═══════════════════════════════════════════════════════════════════════
        
        # 15. FIRST GOAL IMPACT DNA
        fg_dna = self.loader.get_first_goal_dna(team_name)
        if fg_dna:
            dna.first_goal_profile = fg_dna.first_goal_profile
            dna.matches_scored_first = fg_dna.matches_scored_first
            dna.matches_conceded_first = fg_dna.matches_conceded_first
            dna.win_rate_scoring_first = fg_dna.win_rate_scoring_first
            dna.win_rate_conceding_first = fg_dna.win_rate_conceding_first
            dna.comeback_rate = fg_dna.comeback_rate
            dna.collapse_rate = fg_dna.collapse_rate
            
        # 16. GAME STATE DNA
        gs_dna = self.loader.get_game_state_dna(team_name)
        if gs_dna:
            dna.game_state_profile = gs_dna.game_state_profile
            dna.pct_goals_leading = gs_dna.pct_goals_leading
            dna.pct_goals_trailing = gs_dna.pct_goals_trailing
            dna.pct_goals_level = gs_dna.pct_goals_level
            dna.goals_when_leading = gs_dna.goals_when_leading
            dna.goals_when_trailing = gs_dna.goals_when_trailing
            dna.goals_when_level = gs_dna.goals_when_level
            dna.killer_index = gs_dna.killer_index
            
    def _build_external_factors_dna(self, dna: TeamAttackDNAv24, team_name: str) -> None:
        """
        🆕 DIMENSION 17: EXTERNAL FACTORS DNA
        
        Profils:
        • PRIME_TIME_BEAST: Meilleur le soir (+0.5 delta)
        • AFTERNOON_SPECIALIST: Meilleur l'après-midi
        • LUNCH_WARRIOR: Meilleur le midi
        • CONSISTENT: Stable
        """
        ef_dna = self.loader.get_external_factors_dna(team_name)
        
        if not ef_dna:
            dna.schedule_profile = "NO_DATA"
            return
            
        dna.schedule_profile = ef_dna.schedule_profile
        dna.lunch_avg = ef_dna.lunch_avg
        dna.afternoon_avg = ef_dna.afternoon_avg
        dna.prime_time_avg = ef_dna.prime_time_avg
        dna.overall_schedule_avg = ef_dna.overall_avg
        
        dna.lunch_delta = ef_dna.lunch_delta
        dna.afternoon_delta = ef_dna.afternoon_delta
        dna.prime_time_delta = ef_dna.prime_time_delta
        
        dna.best_time_slot = ef_dna.best_slot
        dna.worst_time_slot = ef_dna.worst_slot
        dna.best_slot_avg = ef_dna.best_slot_avg
        dna.worst_slot_avg = ef_dna.worst_slot_avg
        dna.schedule_max_delta = ef_dna.max_delta
        
        dna.lunch_matches = ef_dna.lunch_matches
        dna.afternoon_matches = ef_dna.afternoon_matches
        dna.prime_time_matches = ef_dna.prime_time_matches
        
    def _build_narrative_v24(self, dna: TeamAttackDNAv24) -> None:
        """Construit le profil narratif UNIQUE V2.4"""
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
            
        # First Goal Impact
        if dna.first_goal_profile == "FRONT_RUNNER":
            parts.append(f"Front Runner ({dna.win_rate_scoring_first:.0f}%)")
            dna.strengths.append("Domine après 1er but")
        elif dna.first_goal_profile == "COMEBACK_KING":
            parts.append(f"Comeback ({dna.comeback_rate:.0f}%)")
            dna.strengths.append("Revient quand mené")
        elif dna.first_goal_profile == "FRAGILE":
            dna.weaknesses.append("S'effondre quand mené")
            
        # Game State
        if dna.game_state_profile == "KILLER":
            parts.append(f"Killer ({dna.pct_goals_leading:.0f}%)")
            dna.strengths.append("Continue en menant")
        elif dna.game_state_profile == "SETTLER":
            dna.weaknesses.append("Se contente du score")
            
        # Momentum
        if dna.momentum_profile == "BURST_SCORER":
            parts.append(f"Burst ({dna.burst_rate:.0f}%)")
            dna.strengths.append("Marque en série")
            
        # 🆕 External Factors
        if dna.schedule_profile == "PRIME_TIME_BEAST":
            parts.append(f"🌙 Prime Time (+{dna.prime_time_delta:.1f})")
            dna.strengths.append(f"Meilleur le soir (+{dna.prime_time_delta:.2f}/match)")
        elif dna.schedule_profile == "AFTERNOON_SPECIALIST":
            parts.append(f"☀️ Afternoon (+{dna.afternoon_delta:.1f})")
            dna.strengths.append(f"Meilleur l'après-midi (+{dna.afternoon_delta:.2f}/match)")
        elif dna.schedule_profile == "PRIME_TIME_WEAK":
            dna.weaknesses.append(f"Faible le soir ({dna.prime_time_delta:.2f}/match)")
            
        # NP-Clinical
        if dna.team_np_profile == "WASTEFUL_TEAM":
            dna.weaknesses.append("Gaspille des occasions")
            
        # Dependency
        if dna.dependency_profile == "MVP_DEPENDENT":
            dna.weaknesses.append(f"Dépendant de {dna.top_scorer}")
        elif dna.dependency_profile == "DISTRIBUTED":
            dna.strengths.append("Menace variée")
            
        dna.narrative_profile = " | ".join(parts) if parts else "Profil équilibré"
        
    def _identify_profitable_markets_v24(self, dna: TeamAttackDNAv24) -> None:
        """Identifie les marchés profitables V2.4 - ADN UNIQUE"""
        dna.profitable_markets = []
        dna.markets_to_avoid = []
        
        # ═══════════════════════════════════════════════════════════════════════
        # 🆕 EXTERNAL FACTORS MARKETS (PHASE 4)
        # ═══════════════════════════════════════════════════════════════════════
        if dna.schedule_profile == "PRIME_TIME_BEAST":
            dna.profitable_markets.append({
                'market': 'OVER_TEAM_GOALS_PRIME_TIME',
                'confidence': 'HIGH',
                'players': None,
                'reason': f"PRIME_TIME_BEAST: +{dna.prime_time_delta:.2f} buts/match le soir"
            })
            
        if dna.schedule_profile == "AFTERNOON_SPECIALIST":
            dna.profitable_markets.append({
                'market': 'OVER_TEAM_GOALS_AFTERNOON',
                'confidence': 'HIGH',
                'players': None,
                'reason': f"AFTERNOON_SPECIALIST: +{dna.afternoon_delta:.2f} buts/match l'après-midi"
            })
            
        if dna.schedule_profile == "PRIME_TIME_WEAK" or dna.prime_time_delta <= -0.5:
            dna.markets_to_avoid.append({
                'market': 'OVER_TEAM_GOALS_PRIME_TIME',
                'reason': f"PRIME_TIME_WEAK: {dna.prime_time_delta:.2f} buts/match le soir"
            })
            
        if dna.schedule_max_delta >= 1.0:
            dna.profitable_markets.append({
                'market': f'TIMING_EDGE_{dna.best_time_slot}',
                'confidence': 'MAX_BET',
                'players': None,
                'reason': f"EDGE MAX: {dna.best_time_slot} ({dna.best_slot_avg:.2f}) vs {dna.worst_time_slot} ({dna.worst_slot_avg:.2f}) = Δ{dna.schedule_max_delta:.2f}"
            })
            
        # ═══════════════════════════════════════════════════════════════════════
        # MARCHÉS PHASE 3 (15-16)
        # ═══════════════════════════════════════════════════════════════════════
        if dna.first_goal_profile == "FRONT_RUNNER":
            dna.profitable_markets.append({
                'market': 'WIN_IF_SCORES_FIRST',
                'confidence': 'HIGH',
                'players': None,
                'reason': f"FRONT_RUNNER: {dna.win_rate_scoring_first:.0f}% win après 1er but"
            })
            
        if dna.first_goal_profile == "COMEBACK_KING":
            dna.profitable_markets.append({
                'market': 'LIVE_BACK_WHEN_TRAILING',
                'confidence': 'HIGH',
                'players': None,
                'reason': f"COMEBACK_KING: {dna.comeback_rate:.0f}% comeback"
            })
            
        if dna.first_goal_profile == "FRAGILE" or dna.win_rate_conceding_first <= 10:
            dna.markets_to_avoid.append({
                'market': 'BACK_WHEN_TRAILING',
                'reason': f"FRAGILE: Win mené = {dna.win_rate_conceding_first:.0f}%"
            })
            
        if dna.game_state_profile == "KILLER":
            dna.profitable_markets.append({
                'market': 'LIVE_OVER_WHEN_LEADING',
                'confidence': 'HIGH',
                'players': None,
                'reason': f"KILLER: {dna.pct_goals_leading:.0f}% buts en menant"
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
                    'reason': f"ELITE_COMBO: {combo['occurrences']}x"
                })
                
        if dna.momentum_profile == "BURST_SCORER":
            dna.profitable_markets.append({
                'market': 'LIVE_NEXT_GOAL',
                'confidence': 'HIGH',
                'players': None,
                'reason': f"BURST_SCORER: {dna.burst_rate:.0f}% burst"
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
                'reason': "PENALTY_INFLATED"
            })
            
    # ═══════════════════════════════════════════════════════════════════════════
    # AFFICHAGE V2.4
    # ═══════════════════════════════════════════════════════════════════════════
    
    def print_team_dna(self, team_name: str) -> None:
        """Affiche l'ADN COMPLET V2.4 (17 dimensions) d'une équipe"""
        dna = self.team_dna.get(team_name)
        if not dna:
            print(f"❌ Équipe '{team_name}' non trouvée")
            return
            
        print("=" * 80)
        print(f"🧬 ADN OFFENSIF V2.4 (17 dim): {dna.team_name} ({dna.league})")
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
            
        # Résumé dimensions 1-16
        print(f"\n📊 VOLUME: {dna.total_goals}G | {dna.goals_per_match:.1f}/match | {dna.volume_profile}")
        print(f"⏱️ TIMING: 1H {dna.pct_1h:.0f}% | 2H {dna.pct_2h:.0f}% | {dna.timing_profile}")
        print(f"👤 DEPENDENCY: {dna.top_scorer} ({dna.top_scorer_share:.0f}%) | {dna.dependency_profile}")
        print(f"🎯 NP-CLINICAL: {dna.team_np_profile} ({dna.team_np_overperformance:+.1f})")
        print(f"🔗 COMBOS: {dna.combo_dependency_profile} | MOMENTUM: {dna.momentum_profile}")
        print(f"🎯 FIRST GOAL: {dna.first_goal_profile} | GAME STATE: {dna.game_state_profile}")
        
        # 🆕 External Factors
        print(f"\n🌤️ EXTERNAL FACTORS DNA (NOUVEAU):")
        print(f"   • Profil: {dna.schedule_profile}")
        print(f"   • Moyenne globale: {dna.overall_schedule_avg:.2f} buts/match")
        print(f"\n   📊 PAR CRÉNEAU:")
        print(f"      🍽️ LUNCH (12h-15h):     {dna.lunch_avg:.2f}/match ({dna.lunch_matches} matchs) | Δ {dna.lunch_delta:+.2f}")
        print(f"      ☀️ AFTERNOON (15h-19h): {dna.afternoon_avg:.2f}/match ({dna.afternoon_matches} matchs) | Δ {dna.afternoon_delta:+.2f}")
        print(f"      🌙 PRIME_TIME (19h-24h): {dna.prime_time_avg:.2f}/match ({dna.prime_time_matches} matchs) | Δ {dna.prime_time_delta:+.2f}")
        print(f"\n   🎯 BEST: {dna.best_time_slot} ({dna.best_slot_avg:.2f}) | WORST: {dna.worst_time_slot} ({dna.worst_slot_avg:.2f}) | Δ {dna.schedule_max_delta:.2f}")
        
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
            
    def analyze_matchup(self, home_team: str, away_team: str, kickoff_hour: int = None) -> None:
        """Analyse matchup V2.4 avec 17 dimensions + horaire"""
        home = self.team_dna.get(home_team)
        away = self.team_dna.get(away_team)
        
        if not home or not away:
            print(f"❌ Équipe(s) non trouvée(s)")
            return
            
        print("=" * 80)
        print(f"⚔️ MATCHUP V2.4: {home_team} (🏠) vs {away_team} (✈️)")
        if kickoff_hour:
            slot = "LUNCH" if 12 <= kickoff_hour < 15 else "AFTERNOON" if 15 <= kickoff_hour < 19 else "PRIME_TIME" if 19 <= kickoff_hour < 24 else "OTHER"
            print(f"🕐 Horaire: {kickoff_hour}h ({slot})")
        print("=" * 80)
        
        print(f"\n🏠 {home_team}: {home.narrative_profile}")
        print(f"✈️ {away_team}: {away.narrative_profile}")
        
        # 🆕 External Factors clash
        print(f"\n🌤️ EXTERNAL FACTORS CLASH:")
        print(f"   🏠 {home_team}: {home.schedule_profile}")
        print(f"      Best: {home.best_time_slot} ({home.best_slot_avg:.2f}) | Worst: {home.worst_time_slot} ({home.worst_slot_avg:.2f})")
        print(f"   ✈️ {away_team}: {away.schedule_profile}")
        print(f"      Best: {away.best_time_slot} ({away.best_slot_avg:.2f}) | Worst: {away.worst_time_slot} ({away.worst_slot_avg:.2f})")
        
        # Si horaire fourni, analyser l'impact
        if kickoff_hour:
            slot = "LUNCH" if 12 <= kickoff_hour < 15 else "AFTERNOON" if 15 <= kickoff_hour < 19 else "PRIME_TIME"
            
            home_delta = getattr(home, f"{slot.lower()}_delta", 0)
            away_delta = getattr(away, f"{slot.lower()}_delta", 0)
            
            print(f"\n   🎯 IMPACT HORAIRE ({slot}):")
            print(f"      🏠 {home_team}: {home_delta:+.2f} buts/match à {slot}")
            print(f"      ✈️ {away_team}: {away_delta:+.2f} buts/match à {slot}")
            
            if home_delta >= 0.5:
                print(f"      ✅ AVANTAGE {home_team} à cet horaire")
            elif away_delta >= 0.5:
                print(f"      ✅ AVANTAGE {away_team} à cet horaire")
                
        # Recommandations
        print(f"\n" + "─" * 80)
        print(f"💰 RECOMMANDATIONS:")
        
        # External factors recommendations
        if kickoff_hour:
            slot = "LUNCH" if 12 <= kickoff_hour < 15 else "AFTERNOON" if 15 <= kickoff_hour < 19 else "PRIME_TIME"
            
            if home.schedule_profile == f"{slot}_BEAST" or getattr(home, f"{slot.lower()}_delta", 0) >= 0.5:
                print(f"   🌤️ {home_team} performant à {slot} → BACK Over {home_team} Goals")
            if away.schedule_profile == f"{slot}_BEAST" or getattr(away, f"{slot.lower()}_delta", 0) >= 0.5:
                print(f"   🌤️ {away_team} performant à {slot} → BACK Over {away_team} Goals")
                
        # Other recommendations from previous phases
        if home.first_goal_profile == "FRONT_RUNNER":
            print(f"   🏠 Si {home_team} marque 1er → BACK {home_team} Win ({home.win_rate_scoring_first:.0f}%)")
        if away.first_goal_profile == "FRAGILE":
            print(f"   ✈️ Si {away_team} mené → LAY {away_team} (FRAGILE)")
        if home.game_state_profile == "KILLER":
            print(f"   🏠 LIVE: Si {home_team} mène → BACK Over (KILLER)")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    engineer = FeatureEngineerV24Phase4()
    engineer.initialize()
    
    # Test équipes
    for team in ["Bayern Munich", "Liverpool", "Eintracht Frankfurt"]:
        engineer.print_team_dna(team)
        print("\n" + "═" * 80 + "\n")
        
    # Test matchup avec horaire
    engineer.analyze_matchup("Liverpool", "Bayern Munich", kickoff_hour=20)
