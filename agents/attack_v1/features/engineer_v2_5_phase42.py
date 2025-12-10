"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🧬 FEATURE ENGINEER V2.5 PHASE 4.2 - TEAM-CENTRIC HEDGE FUND GRADE          ║
║                                                                              ║
║  PHILOSOPHIE MON_PS:                                                         ║
║  ═══════════════════════════════════════════════════════════════════════════ ║
║  • ÉQUIPE au centre (comme un trou noir)                                    ║
║  • Chaque équipe = 1 ADN = 1 empreinte digitale UNIQUE                      ║
║  • Les marchés sont des CONSÉQUENCES de l'ADN, pas l'inverse                ║
║                                                                              ║
║  18 DIMENSIONS ADN:                                                          ║
║  ═══════════════════════════════════════════════════════════════════════════ ║
║  Phase 1 (V2.1): 1-12 (Volume, Timing, Dependency, Style, Home/Away,        ║
║                        Efficiency, Super_Sub, Penalty, Creativity, Form,     ║
║                        NP-Clinical, Creativity Chain)                        ║
║                                                                              ║
║  Phase 2 (V2.2): 13. Creator-Finisher DNA, 14. Momentum DNA                 ║
║                                                                              ║
║  Phase 3 (V2.3): 15. First Goal Impact DNA, 16. Game State DNA              ║
║                                                                              ║
║  Phase 4.1 (V2.4): 17. External Factors DNA (Horaires)                      ║
║                                                                              ║
║  Phase 4.2 (V2.5) - NOUVEAU:                                                 ║
║  18. WEATHER DNA (Météo: RAIN, COLD, HOT)                                   ║
║      Profils: RAIN_ATTACKER, RAIN_LEAKY, COLD_VULNERABLE, HEAT_DIESEL       ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
sys.path.insert(0, '/home/Mon_ps')

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json

from agents.attack_v1.data.loader_v5_6_phase42 import (
    AttackDataLoaderV56Phase42,
    WeatherDNA
)
from agents.attack_v1.features.engineer_v2_4_phase4 import (
    FeatureEngineerV24Phase4,
    TeamAttackDNAv24
)

DATA_DIR = Path('/home/Mon_ps/data')


# ═══════════════════════════════════════════════════════════════════════════════
# TEAM ATTACK DNA V2.5 - 18 DIMENSIONS COMPLÈTES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TeamAttackDNAv25(TeamAttackDNAv24):
    """
    ADN OFFENSIF COMPLET d'une équipe - VERSION 2.5 (18 DIMENSIONS)
    
    Hérite de V2.4 (17 dimensions) et ajoute:
    • 18. WEATHER DNA
    """
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🆕 18. WEATHER DNA (PHASE 4.2)
    # Performance selon les conditions météo
    # ═══════════════════════════════════════════════════════════════════════════
    weather_profile: str = ""               # Résumé global
    
    # Rain profiles
    rain_attack_profile: str = ""           # RAIN_ATTACKER, RAIN_WEAK, RAIN_NEUTRAL
    rain_defense_profile: str = ""          # RAIN_LEAKY, RAIN_SOLID, RAIN_NEUTRAL
    rain_attack_delta: float = 0.0          # buts/match pluie - sec
    rain_defense_delta: float = 0.0         # encaissés/match pluie - sec
    rain_goals_avg: float = 0.0
    rain_conceded_avg: float = 0.0
    rain_matches: int = 0
    
    # Cold profiles
    cold_profile: str = ""                  # COLD_SPECIALIST, COLD_VULNERABLE, COLD_RESILIENT
    cold_attack_delta: float = 0.0
    cold_goals_avg: float = 0.0
    cold_matches: int = 0
    
    # Hot profiles
    hot_profile: str = ""                   # HEAT_DIESEL, HEAT_WEAK, HEAT_NEUTRAL
    hot_attack_delta: float = 0.0
    hot_goals_avg: float = 0.0
    hot_matches: int = 0
    
    # Edge
    best_weather_condition: str = ""
    worst_weather_condition: str = ""
    max_weather_edge: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE ENGINEER V2.5 PHASE 4.2 - 18 DIMENSIONS
# ═══════════════════════════════════════════════════════════════════════════════

class FeatureEngineerV25Phase42:
    """
    Feature Engineer V2.5 PHASE 4.2 - TEAM-CENTRIC HEDGE FUND GRADE
    
    Construit l'ADN COMPLET de chaque équipe avec 18 dimensions
    
    PHILOSOPHIE: Chaque équipe = ADN UNIQUE = Empreinte digitale
    Les marchés sont des CONSÉQUENCES de l'ADN, pas l'inverse.
    """
    
    def __init__(self):
        self.loader = AttackDataLoaderV56Phase42()
        self.team_dna: Dict[str, TeamAttackDNAv25] = {}
        self.matches_played = 13  # À ajuster selon la saison
        
    def initialize(self) -> None:
        """Initialise le Feature Engineer"""
        print("=" * 80)
        print("🎯 FEATURE ENGINEER V2.5 PHASE 4.2 - 18 DIMENSIONS ADN")
        print("=" * 80)
        
        self.loader.load_all()
        self._build_all_team_dna()
        
        print(f"\n✅ {len(self.team_dna)} équipes avec ADN COMPLET V2.5 (18 dimensions)")
        
    def _build_all_team_dna(self) -> None:
        """Construit l'ADN de toutes les équipes"""
        print("\n📊 Construction ADN V2.5 par équipe...")
        
        for team_name, team in self.loader.teams.items():
            dna = self._build_team_dna(team_name)
            self.team_dna[team_name] = dna
            
    def _build_team_dna(self, team_name: str) -> TeamAttackDNAv25:
        """Construit l'ADN complet d'une équipe V2.5 (18 dimensions)"""
        
        team = self.loader.teams.get(team_name)
        if not team:
            return TeamAttackDNAv25(team_name=team_name)
            
        # Créer le DNA V2.5
        dna = TeamAttackDNAv25(team_name=team_name, league=team.league)
        
        players = team.players
        scorers = [p for p in players if p.goals > 0]
        
        # ═══════════════════════════════════════════════════════════════════════
        # DIMENSIONS 1-17 (héritées de V2.4)
        # ═══════════════════════════════════════════════════════════════════════
        self._build_v24_dimensions(dna, team, players, scorers, team_name)
        
        # ═══════════════════════════════════════════════════════════════════════
        # 🆕 DIMENSION 18: WEATHER DNA (PHASE 4.2)
        # ═══════════════════════════════════════════════════════════════════════
        self._build_weather_dna(dna, team_name)
        
        # ═══════════════════════════════════════════════════════════════════════
        # PROFIL NARRATIF FINAL + MARCHÉS
        # ═══════════════════════════════════════════════════════════════════════
        self._build_narrative_v25(dna)
        self._identify_profitable_markets_v25(dna)
        
        return dna
        
    def _build_v24_dimensions(self, dna, team, players, scorers, team_name) -> None:
        """Construit les dimensions 1-17 (héritées de V2.4)"""
        
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
            
        # ═══════════════════════════════════════════════════════════════════════
        # DIMENSION 17 (V2.4 - Phase 4.1)
        # ═══════════════════════════════════════════════════════════════════════
        
        # 17. EXTERNAL FACTORS DNA (Horaires)
        ef_dna = self.loader.get_external_factors_dna(team_name)
        if ef_dna:
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
            
    def _build_weather_dna(self, dna: TeamAttackDNAv25, team_name: str) -> None:
        """
        🆕 DIMENSION 18: WEATHER DNA
        
        Profils:
        • RAIN_ATTACKER: Marque +0.5 sous la pluie
        • RAIN_LEAKY: Encaisse +0.5 sous la pluie
        • COLD_VULNERABLE: Moins bon par temps froid
        • COLD_SPECIALIST: Meilleur par temps froid
        • HEAT_DIESEL: Meilleur par temps chaud
        """
        w_dna = self.loader.get_weather_dna(team_name)
        
        if not w_dna:
            dna.weather_profile = "NO_DATA"
            return
            
        dna.weather_profile = w_dna.weather_profile
        
        # Rain
        dna.rain_attack_profile = w_dna.rain_attack_profile
        dna.rain_defense_profile = w_dna.rain_defense_profile
        dna.rain_attack_delta = w_dna.rain_attack_delta
        dna.rain_defense_delta = w_dna.rain_defense_delta
        dna.rain_goals_avg = w_dna.rain_goals_avg
        dna.rain_conceded_avg = w_dna.rain_conceded_avg
        dna.rain_matches = w_dna.rain_matches
        
        # Cold
        dna.cold_profile = w_dna.cold_profile
        dna.cold_attack_delta = w_dna.cold_attack_delta
        dna.cold_goals_avg = w_dna.cold_goals_avg
        dna.cold_matches = w_dna.cold_matches
        
        # Hot
        dna.hot_profile = w_dna.hot_profile
        dna.hot_attack_delta = w_dna.hot_attack_delta
        dna.hot_goals_avg = w_dna.hot_goals_avg
        dna.hot_matches = w_dna.hot_matches
        
        # Edge
        dna.best_weather_condition = w_dna.best_weather_condition
        dna.worst_weather_condition = w_dna.worst_weather_condition
        dna.max_weather_edge = w_dna.max_weather_edge
        
    def _build_narrative_v25(self, dna: TeamAttackDNAv25) -> None:
        """Construit le profil narratif UNIQUE V2.5"""
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
            
        # External Factors (Horaires)
        if dna.schedule_profile == "PRIME_TIME_BEAST":
            parts.append(f"🌙 Prime Time (+{dna.prime_time_delta:.1f})")
            dna.strengths.append(f"Meilleur le soir")
        elif dna.schedule_profile == "AFTERNOON_SPECIALIST":
            parts.append(f"☀️ Afternoon (+{dna.afternoon_delta:.1f})")
            dna.strengths.append(f"Meilleur l'après-midi")
            
        # 🆕 Weather DNA
        if dna.rain_attack_profile == "RAIN_ATTACKER":
            parts.append(f"🌧️ Rain Attacker (+{dna.rain_attack_delta:.1f})")
            dna.strengths.append(f"Marque sous la pluie (+{dna.rain_attack_delta:.2f})")
        elif dna.rain_attack_profile == "RAIN_WEAK":
            dna.weaknesses.append(f"Faible sous la pluie ({dna.rain_attack_delta:.2f})")
            
        if dna.rain_defense_profile == "RAIN_LEAKY":
            dna.weaknesses.append(f"Encaisse sous la pluie (+{dna.rain_defense_delta:.2f})")
            
        if dna.cold_profile == "COLD_VULNERABLE":
            dna.weaknesses.append(f"Vulnérable au froid ({dna.cold_attack_delta:.2f})")
        elif dna.cold_profile == "COLD_SPECIALIST":
            parts.append(f"❄️ Cold Specialist (+{dna.cold_attack_delta:.1f})")
            dna.strengths.append(f"Performant par temps froid")
            
        if dna.hot_profile == "HEAT_DIESEL":
            parts.append(f"🔥 Heat Diesel (+{dna.hot_attack_delta:.1f})")
            dna.strengths.append(f"Monte en puissance par temps chaud")
            
        # NP-Clinical
        if dna.team_np_profile == "WASTEFUL_TEAM":
            dna.weaknesses.append("Gaspille des occasions")
            
        # Dependency
        if dna.dependency_profile == "MVP_DEPENDENT":
            dna.weaknesses.append(f"Dépendant de {dna.top_scorer}")
        elif dna.dependency_profile == "DISTRIBUTED":
            dna.strengths.append("Menace variée")
            
        dna.narrative_profile = " | ".join(parts) if parts else "Profil équilibré"
        
    def _identify_profitable_markets_v25(self, dna: TeamAttackDNAv25) -> None:
        """Identifie les marchés profitables V2.5 - ADN UNIQUE"""
        dna.profitable_markets = []
        dna.markets_to_avoid = []
        
        # ═══════════════════════════════════════════════════════════════════════
        # 🆕 WEATHER MARKETS (PHASE 4.2)
        # ═══════════════════════════════════════════════════════════════════════
        if dna.rain_attack_profile == "RAIN_ATTACKER":
            dna.profitable_markets.append({
                'market': 'OVER_TEAM_GOALS_RAIN',
                'confidence': 'HIGH',
                'players': None,
                'reason': f"RAIN_ATTACKER: +{dna.rain_attack_delta:.2f} buts/match sous la pluie"
            })
            
        if dna.rain_attack_profile == "RAIN_WEAK":
            dna.markets_to_avoid.append({
                'market': 'OVER_TEAM_GOALS_RAIN',
                'reason': f"RAIN_WEAK: {dna.rain_attack_delta:.2f} buts/match sous la pluie"
            })
            
        if dna.rain_defense_profile == "RAIN_LEAKY":
            dna.profitable_markets.append({
                'market': 'BACK_OPPONENT_GOALS_RAIN',
                'confidence': 'MEDIUM',
                'players': None,
                'reason': f"RAIN_LEAKY: +{dna.rain_defense_delta:.2f} encaissés sous la pluie"
            })
            
        if dna.cold_profile == "COLD_VULNERABLE":
            dna.markets_to_avoid.append({
                'market': 'OVER_TEAM_GOALS_COLD',
                'reason': f"COLD_VULNERABLE: {dna.cold_attack_delta:.2f} buts/match par temps froid"
            })
            
        if dna.cold_profile == "COLD_SPECIALIST":
            dna.profitable_markets.append({
                'market': 'OVER_TEAM_GOALS_COLD',
                'confidence': 'HIGH',
                'players': None,
                'reason': f"COLD_SPECIALIST: +{dna.cold_attack_delta:.2f} buts/match par temps froid"
            })
            
        if dna.hot_profile == "HEAT_DIESEL":
            dna.profitable_markets.append({
                'market': 'OVER_TEAM_GOALS_HOT',
                'confidence': 'MEDIUM',
                'players': None,
                'reason': f"HEAT_DIESEL: +{dna.hot_attack_delta:.2f} buts/match par temps chaud"
            })
            
        if dna.max_weather_edge >= 1.0:
            dna.profitable_markets.append({
                'market': f'WEATHER_EDGE_{dna.best_weather_condition}',
                'confidence': 'MAX_BET',
                'players': None,
                'reason': f"EDGE MAX: {dna.best_weather_condition} vs {dna.worst_weather_condition} = Δ{dna.max_weather_edge:.2f}"
            })
            
        # ═══════════════════════════════════════════════════════════════════════
        # MARCHÉS PHASE 4.1 (17)
        # ═══════════════════════════════════════════════════════════════════════
        if dna.schedule_profile == "PRIME_TIME_BEAST":
            dna.profitable_markets.append({
                'market': 'OVER_TEAM_GOALS_PRIME_TIME',
                'confidence': 'HIGH',
                'players': None,
                'reason': f"PRIME_TIME_BEAST: +{dna.prime_time_delta:.2f} buts/match le soir"
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
        # MARCHÉS PHASE 2 + 1
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
            
    # ═══════════════════════════════════════════════════════════════════════════
    # AFFICHAGE V2.5
    # ═══════════════════════════════════════════════════════════════════════════
    
    def print_team_dna(self, team_name: str) -> None:
        """Affiche l'ADN COMPLET V2.5 (18 dimensions) d'une équipe"""
        dna = self.team_dna.get(team_name)
        if not dna:
            print(f"❌ Équipe '{team_name}' non trouvée")
            return
            
        print("=" * 80)
        print(f"🧬 ADN OFFENSIF V2.5 (18 dim): {dna.team_name} ({dna.league})")
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
            
        # Résumé dimensions 1-17
        print(f"\n📊 VOLUME: {dna.total_goals}G | {dna.goals_per_match:.1f}/match | {dna.volume_profile}")
        print(f"⏱️ TIMING: 1H {dna.pct_1h:.0f}% | 2H {dna.pct_2h:.0f}% | {dna.timing_profile}")
        print(f"👤 DEPENDENCY: {dna.top_scorer} ({dna.top_scorer_share:.0f}%) | {dna.dependency_profile}")
        print(f"🎯 NP-CLINICAL: {dna.team_np_profile} ({dna.team_np_overperformance:+.1f})")
        print(f"🔗 COMBOS: {dna.combo_dependency_profile} | MOMENTUM: {dna.momentum_profile}")
        print(f"🎯 FIRST GOAL: {dna.first_goal_profile} | GAME STATE: {dna.game_state_profile}")
        print(f"🕐 SCHEDULE: {dna.schedule_profile}")
        
        # 🆕 Weather DNA
        print(f"\n🌧️ WEATHER DNA (NOUVEAU):")
        print(f"   • Profil global: {dna.weather_profile}")
        
        print(f"\n   🌧️ RAIN:")
        print(f"      Matchs pluie: {dna.rain_matches}")
        print(f"      Attaque: {dna.rain_attack_profile} (Δ {dna.rain_attack_delta:+.2f})")
        print(f"      Défense: {dna.rain_defense_profile} (Δ {dna.rain_defense_delta:+.2f})")
        
        print(f"\n   ❄️ COLD (<10°C):")
        print(f"      Matchs froid: {dna.cold_matches}")
        print(f"      Profil: {dna.cold_profile} (Δ {dna.cold_attack_delta:+.2f})")
        
        print(f"\n   🔥 HOT (>25°C):")
        print(f"      Matchs chaud: {dna.hot_matches}")
        print(f"      Profil: {dna.hot_profile} (Δ {dna.hot_attack_delta:+.2f})")
        
        print(f"\n   🎯 EDGE MÉTÉO: Best {dna.best_weather_condition} | Worst {dna.worst_weather_condition} | Δ {dna.max_weather_edge:.2f}")
        
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
            
    def analyze_matchup(self, home_team: str, away_team: str, kickoff_hour: int = None, 
                        temperature: float = None, is_rainy: bool = False) -> None:
        """Analyse matchup V2.5 avec 18 dimensions + météo"""
        home = self.team_dna.get(home_team)
        away = self.team_dna.get(away_team)
        
        if not home or not away:
            print(f"❌ Équipe(s) non trouvée(s)")
            return
            
        print("=" * 80)
        print(f"⚔️ MATCHUP V2.5: {home_team} (🏠) vs {away_team} (✈️)")
        
        conditions = []
        if kickoff_hour:
            slot = "LUNCH" if 12 <= kickoff_hour < 15 else "AFTERNOON" if 15 <= kickoff_hour < 19 else "PRIME_TIME" if 19 <= kickoff_hour < 24 else "OTHER"
            conditions.append(f"🕐 {kickoff_hour}h ({slot})")
        if temperature is not None:
            temp_cat = "❄️ COLD" if temperature < 10 else "🔥 HOT" if temperature > 25 else "🌤️ NORMAL"
            conditions.append(f"{temp_cat} ({temperature}°C)")
        if is_rainy:
            conditions.append("🌧️ RAIN")
            
        if conditions:
            print(f"🌤️ Conditions: {' | '.join(conditions)}")
        print("=" * 80)
        
        print(f"\n🏠 {home_team}: {home.narrative_profile}")
        print(f"✈️ {away_team}: {away.narrative_profile}")
        
        # 🆕 Weather clash
        print(f"\n🌧️ WEATHER CLASH:")
        print(f"   🏠 {home_team}: {home.weather_profile}")
        print(f"   ✈️ {away_team}: {away.weather_profile}")
        
        # Recommandations basées sur la météo
        print(f"\n" + "─" * 80)
        print(f"💰 RECOMMANDATIONS:")
        
        # Weather recommendations
        if is_rainy:
            if home.rain_attack_profile == "RAIN_ATTACKER":
                print(f"   🌧️ {home_team} RAIN_ATTACKER → BACK Over {home_team} Goals (+{home.rain_attack_delta:.2f})")
            if away.rain_attack_profile == "RAIN_ATTACKER":
                print(f"   🌧️ {away_team} RAIN_ATTACKER → BACK Over {away_team} Goals (+{away.rain_attack_delta:.2f})")
            if home.rain_defense_profile == "RAIN_LEAKY":
                print(f"   🌧️ {home_team} RAIN_LEAKY → BACK {away_team} Goals")
            if away.rain_defense_profile == "RAIN_LEAKY":
                print(f"   🌧️ {away_team} RAIN_LEAKY → BACK {home_team} Goals")
                
        if temperature is not None and temperature < 10:
            if home.cold_profile == "COLD_VULNERABLE":
                print(f"   ❄️ {home_team} COLD_VULNERABLE → LAY {home_team} Over")
            if away.cold_profile == "COLD_VULNERABLE":
                print(f"   ❄️ {away_team} COLD_VULNERABLE → LAY {away_team} Over")
            if home.cold_profile == "COLD_SPECIALIST":
                print(f"   ❄️ {home_team} COLD_SPECIALIST → BACK {home_team} Over")
                
        # Other recommendations
        if home.first_goal_profile == "FRONT_RUNNER":
            print(f"   🏠 Si {home_team} marque 1er → BACK {home_team} Win ({home.win_rate_scoring_first:.0f}%)")
        if away.first_goal_profile == "FRAGILE":
            print(f"   ✈️ Si {away_team} mené → LAY {away_team} (FRAGILE)")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    engineer = FeatureEngineerV25Phase42()
    engineer.initialize()
    
    # Test équipes
    for team in ["Liverpool", "Bayern Munich"]:
        engineer.print_team_dna(team)
        print("\n" + "═" * 80 + "\n")
        
    # Test matchup avec météo
    engineer.analyze_matchup("Liverpool", "Bayern Munich", kickoff_hour=20, temperature=8, is_rainy=True)
