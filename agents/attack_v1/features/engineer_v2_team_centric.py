"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  �� FEATURE ENGINEER V2.0 - TEAM-CENTRIC HEDGE FUND GRADE                    ║
║                                                                              ║
║  PHILOSOPHIE MON_PS:                                                         ║
║  • ÉQUIPE au centre (comme un trou noir)                                    ║
║  • Chaque équipe = 1 ADN = 1 empreinte digitale UNIQUE                      ║
║  • Les marchés sont des CONSÉQUENCES de l'ADN, pas l'inverse                ║
║                                                                              ║
║  APPROCHE:                                                                   ║
║  1. Calculer l'ADN COMPLET de chaque équipe                                 ║
║  2. Identifier les EXPLOITS et FAIBLESSES uniques                           ║
║  3. Déduire les MARCHÉS PROFITABLES pour CETTE équipe                       ║
║  4. Créer un PROFIL NARRATIF unique                                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
sys.path.insert(0, '/home/Mon_ps')

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json

from agents.attack_v1.data.loader_v5_optimized import (
    AttackDataLoaderV5Optimized, 
    PlayerFullProfile2025,
    TeamProfile2025
)

DATA_DIR = Path('/home/Mon_ps/data')


@dataclass
class TeamAttackDNA:
    """
    ADN OFFENSIF COMPLET d'une équipe - Empreinte digitale unique.
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
    xG_overperformance: float = 0.0  # Goals - xG
    volume_profile: str = ""  # HIGH_SCORING, AVERAGE, LOW_SCORING
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 2. TIMING DNA - Quand l'équipe marque
    # ═══════════════════════════════════════════════════════════════════════════
    goals_1h: int = 0
    goals_2h: int = 0
    pct_1h: float = 0.0
    pct_2h: float = 0.0
    
    goals_0_15: int = 0
    goals_16_30: int = 0
    goals_31_45: int = 0
    goals_46_60: int = 0
    goals_61_75: int = 0
    goals_76_90: int = 0
    goals_90_plus: int = 0
    
    pct_early: float = 0.0   # 0-15
    pct_clutch: float = 0.0  # 76-90+
    
    timing_profile: str = ""  # EARLY_STARTERS, DIESEL, CLUTCH_TEAM, BALANCED
    peak_period: str = ""     # "61-75" par exemple
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 3. DEPENDENCY DNA - Qui fait les buts
    # ═══════════════════════════════════════════════════════════════════════════
    top_scorer: str = ""
    top_scorer_goals: int = 0
    top_scorer_share: float = 0.0
    
    top_3_scorers: List[Tuple[str, int, float]] = field(default_factory=list)
    top_3_share: float = 0.0  # % des buts par le top 3
    
    scorers_count: int = 0  # Nombre de joueurs avec 1+ but
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
    # 5. HOME/AWAY DNA - Où l'équipe performe
    # ═══════════════════════════════════════════════════════════════════════════
    goals_home: int = 0
    goals_away: int = 0
    pct_home: float = 0.0
    home_away_ratio: float = 1.0
    home_away_profile: str = ""  # FORTRESS, ROAD_WARRIORS, BALANCED
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 6. EFFICIENCY DNA - Qualité des finisseurs
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
    # 8. PENALTY DNA - Spécialistes penalties
    # ═══════════════════════════════════════════════════════════════════════════
    penalty_taker: str = ""
    penalty_goals: int = 0
    penalty_reliability: str = ""  # RELIABLE, INCONSISTENT, NO_DATA
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 9. CREATIVITY DNA - Création de jeu
    # ═══════════════════════════════════════════════════════════════════════════
    total_assists: int = 0
    total_xA: float = 0.0
    top_creator: str = ""
    top_creator_xA: float = 0.0
    elite_creators_count: int = 0
    creativity_profile: str = ""  # CREATIVE_HUB, INDIVIDUAL_BRILLIANCE, COLLECTIVE
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 10. FORM DNA - Tendance actuelle
    # ═══════════════════════════════════════════════════════════════════════════
    hot_streak_players: List[str] = field(default_factory=list)
    cold_streak_players: List[str] = field(default_factory=list)
    team_form_trend: str = ""  # RISING, STABLE, DECLINING
    value_regression_candidates: List[Tuple[str, float]] = field(default_factory=list)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PROFIL NARRATIF - Résumé unique
    # ═══════════════════════════════════════════════════════════════════════════
    narrative_profile: str = ""
    key_strengths: List[str] = field(default_factory=list)
    key_weaknesses: List[str] = field(default_factory=list)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MARCHÉS EXPLOITABLES - Conséquences de l'ADN
    # ═══════════════════════════════════════════════════════════════════════════
    profitable_markets: List[Dict] = field(default_factory=list)
    avoid_markets: List[Dict] = field(default_factory=list)


@dataclass
class MatchupAnalysis:
    """
    Analyse d'un matchup entre deux ADN d'équipes.
    """
    home_team: str = ""
    away_team: str = ""
    home_dna: TeamAttackDNA = None
    away_dna: TeamAttackDNA = None
    
    # Friction tactique
    tactical_edges: List[Dict] = field(default_factory=list)
    
    # Recommandations par marché
    market_recommendations: List[Dict] = field(default_factory=list)


class FeatureEngineerV2TeamCentric:
    """
    Feature Engineer V2 - TEAM-CENTRIC.
    
    Philosophie:
    1. L'ÉQUIPE au centre
    2. Chaque équipe = 1 ADN unique
    3. Marchés = CONSÉQUENCES de l'ADN
    """
    
    def __init__(self):
        self.loader = AttackDataLoaderV5Optimized()
        self.context_dna = {}
        self.team_attack_dna: Dict[str, TeamAttackDNA] = {}
        
    def initialize(self) -> None:
        """Initialise et calcule l'ADN de toutes les équipes"""
        print("=" * 80)
        print("🎯 FEATURE ENGINEER V2.0 - TEAM-CENTRIC HEDGE FUND GRADE")
        print("=" * 80)
        
        self.loader.load_all()
        self._load_context_dna()
        self._build_all_team_dna()
        
        print(f"\n✅ {len(self.team_attack_dna)} équipes avec ADN COMPLET")
        
    def _load_context_dna(self) -> None:
        """Charge context DNA"""
        path = DATA_DIR / 'quantum_v2/teams_context_dna.json'
        with open(path) as f:
            self.context_dna = json.load(f)
            
    def _build_all_team_dna(self) -> None:
        """Construit l'ADN de chaque équipe"""
        print("\n📊 Construction ADN par équipe...")
        
        for team_name, team in self.loader.teams.items():
            dna = self._build_team_dna(team_name, team)
            self.team_attack_dna[team_name] = dna
            
    def _build_team_dna(self, team_name: str, team: TeamProfile2025) -> TeamAttackDNA:
        """
        Construit l'ADN COMPLET d'une équipe.
        """
        dna = TeamAttackDNA(team_name=team_name, league=team.league)
        
        # Récupérer tous les joueurs de l'équipe
        players = [p for p in self.loader.players.values() if p.team == team_name]
        
        if not players:
            return dna
            
        # ═══════════════════════════════════════════════════════════════════════
        # 1. VOLUME DNA
        # ═══════════════════════════════════════════════════════════════════════
        dna.total_goals = sum(p.goals for p in players)
        dna.total_xG = sum(p.xG for p in players)
        
        # Estimer matchs joués (moyenne des titulaires)
        starters = [p for p in players if p.playing_time_profile in ['UNDISPUTED_STARTER', 'STARTER']]
        avg_games = sum(p.games for p in starters) / len(starters) if starters else 10
        
        dna.goals_per_match = dna.total_goals / avg_games if avg_games > 0 else 0
        dna.xG_per_match = dna.total_xG / avg_games if avg_games > 0 else 0
        dna.xG_overperformance = dna.total_goals - dna.total_xG
        
        if dna.goals_per_match >= 2.2:
            dna.volume_profile = "HIGH_SCORING"
        elif dna.goals_per_match >= 1.5:
            dna.volume_profile = "AVERAGE"
        else:
            dna.volume_profile = "LOW_SCORING"
            
        # ═══════════════════════════════════════════════════════════════════════
        # 2. TIMING DNA
        # ═══════════════════════════════════════════════════════════════════════
        dna.goals_1h = sum(p.goals_1h for p in players)
        dna.goals_2h = sum(p.goals_2h for p in players)
        dna.goals_0_15 = sum(p.goals_0_15 for p in players)
        dna.goals_16_30 = sum(p.goals_16_30 for p in players)
        dna.goals_31_45 = sum(p.goals_31_45 for p in players)
        dna.goals_46_60 = sum(p.goals_46_60 for p in players)
        dna.goals_61_75 = sum(p.goals_61_75 for p in players)
        dna.goals_76_90 = sum(p.goals_76_90 for p in players)
        dna.goals_90_plus = sum(p.goals_90_plus for p in players)
        
        total = dna.total_goals
        if total > 0:
            dna.pct_1h = (dna.goals_1h / total) * 100
            dna.pct_2h = (dna.goals_2h / total) * 100
            dna.pct_early = (dna.goals_0_15 / total) * 100
            dna.pct_clutch = ((dna.goals_76_90 + dna.goals_90_plus) / total) * 100
            
            # Peak period
            periods = {
                '0-15': dna.goals_0_15, '16-30': dna.goals_16_30, '31-45': dna.goals_31_45,
                '46-60': dna.goals_46_60, '61-75': dna.goals_61_75, '76-90+': dna.goals_76_90 + dna.goals_90_plus
            }
            dna.peak_period = max(periods, key=periods.get)
            
            # Timing profile
            if dna.pct_2h >= 65:
                dna.timing_profile = "DIESEL"
            elif dna.pct_1h >= 60:
                dna.timing_profile = "EARLY_STARTERS"
            elif dna.pct_clutch >= 30:
                dna.timing_profile = "CLUTCH_TEAM"
            else:
                dna.timing_profile = "BALANCED"
                
        # ═══════════════════════════════════════════════════════════════════════
        # 3. DEPENDENCY DNA
        # ═══════════════════════════════════════════════════════════════════════
        scorers = sorted([p for p in players if p.goals > 0], key=lambda x: -x.goals)
        dna.scorers_count = len(scorers)
        
        if scorers:
            dna.top_scorer = scorers[0].player_name
            dna.top_scorer_goals = scorers[0].goals
            dna.top_scorer_share = (scorers[0].goals / total * 100) if total > 0 else 0
            
            dna.top_3_scorers = [
                (p.player_name, p.goals, (p.goals / total * 100) if total > 0 else 0)
                for p in scorers[:3]
            ]
            dna.top_3_share = sum(x[2] for x in dna.top_3_scorers)
            
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
        
        if total > 0:
            dna.pct_open_play = (dna.goals_open_play / total) * 100
            dna.pct_set_piece = (dna.goals_set_piece / total) * 100
            dna.pct_penalty = (dna.goals_penalty / total) * 100
            dna.pct_header = (dna.goals_header / total) * 100
            
            if dna.pct_open_play >= 75:
                dna.style_profile = "OPEN_PLAY_DOMINANT"
            elif dna.pct_set_piece >= 25:
                dna.style_profile = "SET_PIECE_THREAT"
            elif dna.pct_header >= 20:
                dna.style_profile = "AERIAL_THREAT"
            elif dna.pct_penalty >= 20:
                dna.style_profile = "PENALTY_RELIANT"
            else:
                dna.style_profile = "BALANCED_STYLE"
                
        # ═══════════════════════════════════════════════════════════════════════
        # 5. HOME/AWAY DNA
        # ═══════════════════════════════════════════════════════════════════════
        dna.goals_home = sum(p.goals_home for p in players)
        dna.goals_away = sum(p.goals_away for p in players)
        
        if total > 0:
            dna.pct_home = (dna.goals_home / total) * 100
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
        dna.team_conversion_rate = (dna.total_goals / total_shots * 100) if total_shots > 0 else 0
        
        dna.elite_finishers_count = len([p for p in players if p.shot_quality == "ELITE_FINISHER"])
        dna.clinical_count = len([p for p in players if p.shot_quality == "CLINICAL"])
        dna.wasteful_count = len([p for p in players if p.shot_quality == "WASTEFUL"])
        
        if dna.team_conversion_rate >= 15 or dna.elite_finishers_count >= 2:
            dna.efficiency_profile = "CLINICAL_TEAM"
        elif dna.wasteful_count >= 2 or dna.team_conversion_rate < 10:
            dna.efficiency_profile = "WASTEFUL_TEAM"
        else:
            dna.efficiency_profile = "AVERAGE_EFFICIENCY"
            
        # ═══════════════════════════════════════════════════════════════════════
        # 7. SUPER_SUB DNA
        # ═══════════════════════════════════════════════════════════════════════
        super_subs = [p for p in players if p.playing_time_profile == "SUPER_SUB"]
        dna.super_subs = [p.player_name for p in super_subs]
        dna.super_sub_goals = sum(p.goals for p in super_subs)
        dna.super_sub_pct = (dna.super_sub_goals / total * 100) if total > 0 else 0
        
        if dna.super_sub_pct >= 15 or len(super_subs) >= 2:
            dna.bench_strength = "STRONG_BENCH"
        elif super_subs:
            dna.bench_strength = "AVERAGE_BENCH"
        else:
            dna.bench_strength = "WEAK_BENCH"
            
        # ═══════════════════════════════════════════════════════════════════════
        # 8. PENALTY DNA
        # ═══════════════════════════════════════════════════════════════════════
        pen_takers = [p for p in players if p.is_penalty_taker]
        if pen_takers:
            main_taker = max(pen_takers, key=lambda x: x.penalty_goals)
            dna.penalty_taker = main_taker.player_name
            dna.penalty_goals = sum(p.penalty_goals for p in pen_takers)
            dna.penalty_reliability = "RELIABLE" if main_taker.penalty_goals >= 3 else "AVERAGE"
        else:
            dna.penalty_reliability = "NO_DATA"
            
        # ═══════════════════════════════════════════════════════════════════════
        # 9. CREATIVITY DNA
        # ═══════════════════════════════════════════════════════════════════════
        dna.total_assists = sum(p.assists for p in players)
        dna.total_xA = sum(p.xA for p in players)
        
        creators = sorted(players, key=lambda x: -x.xA)
        if creators:
            dna.top_creator = creators[0].player_name
            dna.top_creator_xA = creators[0].xA
            
        dna.elite_creators_count = len([p for p in players if p.creativity_profile == "ELITE_CREATOR"])
        
        if dna.elite_creators_count >= 2:
            dna.creativity_profile = "CREATIVE_HUB"
        elif dna.elite_creators_count == 1 and creators[0].xA >= 5:
            dna.creativity_profile = "INDIVIDUAL_BRILLIANCE"
        else:
            dna.creativity_profile = "COLLECTIVE"
            
        # ═══════════════════════════════════════════════════════════════════════
        # 10. FORM DNA
        # ═══════════════════════════════════════════════════════════════════════
        dna.hot_streak_players = [p.player_name for p in players if p.finishing_trend == "HOT_STREAK"]
        dna.cold_streak_players = [p.player_name for p in players if p.finishing_trend in ["COLD", "WASTEFUL"]]
        
        # Value regression candidates (xG élevé + sous-performance)
        dna.value_regression_candidates = [
            (p.player_name, p.xG_overperformance)
            for p in players
            if p.xG >= 4 and p.xG_overperformance <= -1.5
        ]
        
        # Team form trend
        if len(dna.hot_streak_players) >= 2:
            dna.team_form_trend = "RISING"
        elif len(dna.cold_streak_players) >= 3:
            dna.team_form_trend = "DECLINING"
        else:
            dna.team_form_trend = "STABLE"
            
        # ═══════════════════════════════════════════════════════════════════════
        # PROFIL NARRATIF
        # ═══════════════════════════════════════════════════════════════════════
        self._build_narrative(dna)
        
        # ═══════════════════════════════════════════════════════════════════════
        # MARCHÉS EXPLOITABLES
        # ═══════════════════════════════════════════════════════════════════════
        self._identify_profitable_markets(dna)
        
        return dna
        
    def _build_narrative(self, dna: TeamAttackDNA) -> None:
        """Construit le profil narratif unique de l'équipe"""
        
        parts = []
        strengths = []
        weaknesses = []
        
        # Volume
        if dna.volume_profile == "HIGH_SCORING":
            parts.append(f"Machine offensive ({dna.goals_per_match:.1f} buts/match)")
            strengths.append("Puissance de feu élevée")
        elif dna.volume_profile == "LOW_SCORING":
            parts.append(f"Attaque en difficulté ({dna.goals_per_match:.1f} buts/match)")
            weaknesses.append("Manque de buts")
            
        # Timing
        if dna.timing_profile == "DIESEL":
            parts.append(f"Diesel ({dna.pct_2h:.0f}% buts en 2H)")
            strengths.append("Monte en puissance")
        elif dna.timing_profile == "EARLY_STARTERS":
            parts.append(f"Démarrage canon ({dna.pct_1h:.0f}% buts en 1H)")
            strengths.append("Marque tôt")
        elif dna.timing_profile == "CLUTCH_TEAM":
            parts.append(f"Clutch ({dna.pct_clutch:.0f}% après 75')")
            strengths.append("Décisifs en fin de match")
            
        # Dependency
        if dna.dependency_profile == "MVP_DEPENDENT":
            parts.append(f"Dépendant de {dna.top_scorer} ({dna.top_scorer_share:.0f}%)")
            weaknesses.append(f"Trop dépendant d'un joueur")
        elif dna.dependency_profile == "DISTRIBUTED":
            parts.append(f"Attaque distribuée ({dna.scorers_count} buteurs)")
            strengths.append("Menace variée")
            
        # Home/Away
        if dna.home_away_profile == "FORTRESS":
            parts.append(f"Forteresse à domicile ({dna.home_away_ratio:.1f}x)")
            strengths.append("Dominant à domicile")
            weaknesses.append("Moins dangereux à l'extérieur")
        elif dna.home_away_profile == "ROAD_WARRIORS":
            parts.append("Road Warriors (performent away)")
            strengths.append("Dangereux à l'extérieur")
            
        # Bench
        if dna.bench_strength == "STRONG_BENCH":
            parts.append(f"Banc impactant ({', '.join(dna.super_subs[:2])})")
            strengths.append("Impact des remplaçants")
            
        # Efficiency
        if dna.efficiency_profile == "CLINICAL_TEAM":
            strengths.append("Finisseurs cliniques")
        elif dna.efficiency_profile == "WASTEFUL_TEAM":
            weaknesses.append("Gaspille des occasions")
            
        # Form
        if dna.team_form_trend == "RISING":
            parts.append(f"En forme montante ({', '.join(dna.hot_streak_players[:2])} en feu)")
        elif dna.team_form_trend == "DECLINING":
            weaknesses.append("Forme déclinante")
            
        dna.narrative_profile = " | ".join(parts) if parts else "Profil standard"
        dna.key_strengths = strengths
        dna.key_weaknesses = weaknesses
        
    def _identify_profitable_markets(self, dna: TeamAttackDNA) -> None:
        """
        Identifie les marchés profitables POUR CETTE ÉQUIPE.
        C'est la clé de l'approche Team-Centric.
        """
        profitable = []
        avoid = []
        
        # ─────────────────────────────────────────────────────────────────────
        # OVER/UNDER GOALS
        # ─────────────────────────────────────────────────────────────────────
        if dna.volume_profile == "HIGH_SCORING":
            profitable.append({
                'market': 'OVER_2.5_TEAM_GOALS',
                'edge': 'HIGH',
                'reason': f'{dna.goals_per_match:.1f} buts/match',
                'context': 'HOME' if dna.home_away_profile == "FORTRESS" else 'ALL'
            })
        elif dna.volume_profile == "LOW_SCORING":
            avoid.append({
                'market': 'OVER_1.5_TEAM_GOALS',
                'reason': f'Seulement {dna.goals_per_match:.1f} buts/match'
            })
            
        # ─────────────────────────────────────────────────────────────────────
        # FIRST GOALSCORER
        # ─────────────────────────────────────────────────────────────────────
        if dna.timing_profile == "EARLY_STARTERS" and dna.pct_early >= 20:
            profitable.append({
                'market': 'FIRST_GOALSCORER',
                'edge': 'HIGH',
                'players': [s[0] for s in dna.top_3_scorers if s[1] >= 3],
                'reason': f'{dna.pct_1h:.0f}% buts en 1H, {dna.pct_early:.0f}% dans les 15 premières min'
            })
        elif dna.timing_profile == "DIESEL":
            avoid.append({
                'market': 'FIRST_GOALSCORER',
                'reason': f'Équipe DIESEL - {dna.pct_2h:.0f}% buts en 2H'
            })
            
        # ─────────────────────────────────────────────────────────────────────
        # LAST GOALSCORER
        # ─────────────────────────────────────────────────────────────────────
        if dna.timing_profile == "DIESEL" or dna.pct_clutch >= 25:
            candidates = dna.super_subs.copy() if dna.super_subs else []
            # Ajouter les titulaires DIESEL
            for name, goals, share in dna.top_3_scorers:
                if name not in candidates:
                    candidates.append(name)
            profitable.append({
                'market': 'LAST_GOALSCORER',
                'edge': 'HIGH' if dna.bench_strength == "STRONG_BENCH" else 'MEDIUM',
                'players': candidates[:5],
                'reason': f'{dna.pct_2h:.0f}% buts en 2H, {dna.pct_clutch:.0f}% clutch'
            })
            
        if dna.bench_strength == "STRONG_BENCH":
            profitable.append({
                'market': 'LAST_GOALSCORER_SUPER_SUB',
                'edge': 'HIGH',
                'players': dna.super_subs,
                'reason': f'SUPER_SUBs: {", ".join(dna.super_subs[:3])}'
            })
            
        # ─────────────────────────────────────────────────────────────────────
        # ANYTIME SCORER
        # ─────────────────────────────────────────────────────────────────────
        if dna.dependency_profile == "MVP_DEPENDENT":
            profitable.append({
                'market': 'ANYTIME_MVP',
                'edge': 'HIGH',
                'players': [dna.top_scorer],
                'reason': f'{dna.top_scorer} = {dna.top_scorer_share:.0f}% des buts'
            })
            
        if dna.value_regression_candidates:
            profitable.append({
                'market': 'ANYTIME_VALUE_REGRESSION',
                'edge': 'HIGH',
                'players': [x[0] for x in dna.value_regression_candidates],
                'reason': 'Sous-performent leur xG - régression attendue',
                'details': dna.value_regression_candidates
            })
            
        # ─────────────────────────────────────────────────────────────────────
        # SET PIECES / HEADERS
        # ─────────────────────────────────────────────────────────────────────
        if dna.style_profile == "SET_PIECE_THREAT":
            profitable.append({
                'market': 'GOAL_FROM_SET_PIECE',
                'edge': 'MEDIUM',
                'reason': f'{dna.pct_set_piece:.0f}% des buts sur coups de pied arrêtés'
            })
            
        if dna.style_profile == "AERIAL_THREAT" or dna.pct_header >= 15:
            profitable.append({
                'market': 'HEADED_GOAL',
                'edge': 'MEDIUM',
                'reason': f'{dna.pct_header:.0f}% des buts de la tête'
            })
            
        # ─────────────────────────────────────────────────────────────────────
        # HOME/AWAY SPECIFIC
        # ─────────────────────────────────────────────────────────────────────
        if dna.home_away_profile == "FORTRESS":
            profitable.append({
                'market': 'TEAM_WIN_HOME',
                'edge': 'HIGH',
                'reason': f'Ratio Home/Away: {dna.home_away_ratio:.1f}x'
            })
            avoid.append({
                'market': 'TEAM_GOALS_AWAY',
                'reason': f'Seulement {dna.goals_away} buts à l\'extérieur'
            })
        elif dna.home_away_profile == "ROAD_WARRIORS":
            profitable.append({
                'market': 'TEAM_GOALS_AWAY',
                'edge': 'MEDIUM',
                'reason': 'Performent à l\'extérieur'
            })
            
        dna.profitable_markets = profitable
        dna.avoid_markets = avoid
        
    # ═══════════════════════════════════════════════════════════════════════════
    # API PUBLIQUE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_team_dna(self, team_name: str) -> Optional[TeamAttackDNA]:
        """Récupère l'ADN d'une équipe"""
        return self.team_attack_dna.get(team_name)
        
    def print_team_dna(self, team_name: str) -> None:
        """Affiche l'ADN complet d'une équipe"""
        dna = self.get_team_dna(team_name)
        if not dna:
            print(f"❌ Équipe {team_name} non trouvée")
            return
            
        print("\n" + "=" * 80)
        print(f"🧬 ADN OFFENSIF: {dna.team_name} ({dna.league})")
        print("=" * 80)
        
        print(f"\n📝 PROFIL NARRATIF:")
        print(f"   {dna.narrative_profile}")
        
        print(f"\n💪 FORCES:")
        for s in dna.key_strengths:
            print(f"   ✅ {s}")
            
        print(f"\n⚠️ FAIBLESSES:")
        for w in dna.key_weaknesses:
            print(f"   ❌ {w}")
            
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
        
        print(f"\n📈 FORM DNA:")
        print(f"   • Hot: {', '.join(dna.hot_streak_players) if dna.hot_streak_players else 'Aucun'}")
        print(f"   • Cold: {', '.join(dna.cold_streak_players[:3]) if dna.cold_streak_players else 'Aucun'}")
        print(f"   • Trend: {dna.team_form_trend}")
        if dna.value_regression_candidates:
            print(f"   • 💎 VALUE: {[(n, f'{d:+.1f}') for n, d in dna.value_regression_candidates]}")
            
        print(f"\n" + "─" * 80)
        print(f"💰 MARCHÉS PROFITABLES POUR {dna.team_name}:")
        for m in dna.profitable_markets:
            players = f" → {', '.join(m.get('players', [])[:3])}" if m.get('players') else ""
            print(f"   ✅ {m['market']} [{m['edge']}]{players}")
            print(f"      Raison: {m['reason']}")
            
        print(f"\n🚫 MARCHÉS À ÉVITER:")
        for m in dna.avoid_markets:
            print(f"   ❌ {m['market']}")
            print(f"      Raison: {m['reason']}")
            
    def analyze_matchup(self, home_team: str, away_team: str) -> None:
        """Analyse un matchup entre deux équipes"""
        home_dna = self.get_team_dna(home_team)
        away_dna = self.get_team_dna(away_team)
        
        if not home_dna or not away_dna:
            print("❌ Équipe non trouvée")
            return
            
        print("\n" + "=" * 80)
        print(f"⚔️ MATCHUP: {home_team} (🏠) vs {away_team} (✈️)")
        print("=" * 80)
        
        # Résumé ADN
        print(f"\n🏠 {home_team}: {home_dna.narrative_profile}")
        print(f"✈️ {away_team}: {away_dna.narrative_profile}")
        
        # Friction tactique
        print(f"\n⚡ FRICTION TACTIQUE:")
        
        # Timing
        print(f"\n   ⏱️ TIMING:")
        print(f"      {home_team}: {home_dna.timing_profile} ({home_dna.pct_2h:.0f}% 2H)")
        print(f"      {away_team}: {away_dna.timing_profile} ({away_dna.pct_2h:.0f}% 2H)")
        
        if home_dna.timing_profile == "DIESEL" and away_dna.timing_profile == "DIESEL":
            print(f"      → Match DIESEL: Buts tardifs attendus ✅ OVER 0.5 2H")
        elif home_dna.timing_profile == "EARLY_STARTERS" and away_dna.timing_profile == "EARLY_STARTERS":
            print(f"      → Match explosif: Buts tôt attendus ✅ BTTS 1H")
            
        # Home/Away
        print(f"\n   🏠 HOME/AWAY:")
        if home_dna.home_away_profile == "FORTRESS":
            print(f"      {home_team} est une FORTERESSE à domicile ({home_dna.home_away_ratio:.1f}x)")
            print(f"      → ✅ BACK {home_team} scorers")
        if away_dna.home_away_profile == "ROAD_WARRIORS":
            print(f"      {away_team} performe à l'extérieur")
            print(f"      → ✅ {away_team} peut scorer")
            
        # Super Subs
        print(f"\n   🦸 SUPER_SUBS:")
        print(f"      {home_team}: {', '.join(home_dna.super_subs[:2]) if home_dna.super_subs else 'Aucun'}")
        print(f"      {away_team}: {', '.join(away_dna.super_subs[:2]) if away_dna.super_subs else 'Aucun'}")
        
        # Recommandations
        print(f"\n💰 RECOMMANDATIONS:")
        
        # Combiner les marchés profitables des deux équipes
        all_picks = []
        
        for m in home_dna.profitable_markets:
            if m['edge'] == 'HIGH':
                all_picks.append((home_team, '🏠', m))
        for m in away_dna.profitable_markets:
            if m['edge'] == 'HIGH':
                all_picks.append((away_team, '✈️', m))
                
        for team, side, m in all_picks[:8]:
            players = f" → {', '.join(m.get('players', [])[:2])}" if m.get('players') else ""
            print(f"   {side} [{team}] {m['market']}{players}")


if __name__ == '__main__':
    engineer = FeatureEngineerV2TeamCentric()
    engineer.initialize()
