"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🎯 ATTACK DATA LOADER V3.0 - FULL QUANT INSTITUTIONNEL                      ║
║                                                                              ║
║  INTÉGRATION COMPLÈTE de toutes les métriques du dictionnaire:               ║
║  • VOLUMES LIGUE (all_goals_2025.json) - Référence paris                     ║
║  • EFFICACITÉ (goals_per_90, conversion_rate, xg_per_shot)                   ║
║  • PLAYING_TIME (SUPER_SUB, STARTER, minutes_per_game)                       ║
║  • FORM (hot_streak, cold_streak, xg_overperformance)                        ║
║  • CREATIVITY (xA, xgchain, xgbuildup, creativity_profile)                   ║
║  • PENALTY (is_penalty_taker, penalty_pct)                                   ║
║  • TIMING (DIESEL, EARLY_BIRD, clutch_pct)                                   ║
║  • HOME_AWAY (HOME_SPECIALIST, AWAY_SPECIALIST)                              ║
║  • SHOT_QUALITY (ELITE_FINISHER, CLINICAL, WASTEFUL)                         ║
║                                                                              ║
║  INSIGHT: league_ratio = performance LIGUE vs TOUTES COMP                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from collections import defaultdict
import json

DATA_DIR = Path('/home/Mon_ps/data')


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES - PROFIL JOUEUR COMPLET
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PlayerFullProfile:
    """
    Profil COMPLET d'un joueur - Toutes métriques du dictionnaire.
    Combine données LIGUE (all_goals) + TOUTES COMP (player_stats).
    """
    player_id: str = ""
    player_name: str = ""
    team: str = ""
    position: str = ""
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VOLUMES LIGUE (Référence pour paris - source: all_goals_2025.json)
    # ═══════════════════════════════════════════════════════════════════════════
    league_goals: int = 0
    league_xG: float = 0.0
    league_assists: int = 0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VOLUMES TOUTES COMP (source: player_stats)
    # ═══════════════════════════════════════════════════════════════════════════
    total_goals: int = 0
    total_assists: int = 0
    total_xG: float = 0.0
    total_xA: float = 0.0
    npg: int = 0  # Non-penalty goals
    npxG: float = 0.0
    shots: int = 0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LEAGUE RATIO (MÉTRIQUE CLÉ)
    # ═══════════════════════════════════════════════════════════════════════════
    league_ratio: float = 0.0  # league_goals / total_goals
    reliability_tag: str = ""  # LEAGUE_SPECIALIST, BALANCED, CUP_PERFORMER
    old_team: str = ""  # Équipe saison 2024/2025 (pour traçabilité transferts)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EFFICACITÉ (Calculées)
    # ═══════════════════════════════════════════════════════════════════════════
    goals_per_90: float = 0.0
    minutes_per_goal: float = 0.0
    conversion_rate: float = 0.0  # goals / shots %
    xg_per_shot: float = 0.0
    xg_overperformance: float = 0.0  # goals - xG
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SHOT QUALITY PROFILE
    # ═══════════════════════════════════════════════════════════════════════════
    shot_quality: str = ""  # ELITE_FINISHER, CLINICAL, WASTEFUL, VOLUME_SHOOTER, OPPORTUNIST
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PLAYING TIME
    # ═══════════════════════════════════════════════════════════════════════════
    minutes: int = 0
    games: int = 0
    minutes_per_game: float = 0.0
    playing_time_profile: str = ""  # UNDISPUTED_STARTER, STARTER, SUPER_SUB, ROTATION, BENCH
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TIMING DNA (source: all_goals pour LIGUE, player_stats pour enrichissement)
    # ═══════════════════════════════════════════════════════════════════════════
    # Volumes LIGUE par période
    league_goals_1h: int = 0
    league_goals_2h: int = 0
    league_goals_0_15: int = 0
    league_goals_16_30: int = 0
    league_goals_31_45: int = 0
    league_goals_46_60: int = 0
    league_goals_61_75: int = 0
    league_goals_76_90: int = 0
    league_goals_90_plus: int = 0
    
    # Pourcentages calculés
    goals_1h_pct: float = 0.0
    goals_2h_pct: float = 0.0
    clutch_pct: float = 0.0  # % buts après 75'
    first_goal_pct: float = 0.0  # % buts avant 15'
    
    timing_profile: str = ""  # DIESEL_SCORER, EARLY_BIRD, CLUTCH, BALANCED_TIMING
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STYLE DNA (source: all_goals pour LIGUE)
    # ═══════════════════════════════════════════════════════════════════════════
    league_goals_open_play: int = 0
    league_goals_corner: int = 0
    league_goals_penalty: int = 0
    league_goals_freekick: int = 0
    league_goals_right_foot: int = 0
    league_goals_left_foot: int = 0
    league_goals_header: int = 0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HOME/AWAY DNA
    # ═══════════════════════════════════════════════════════════════════════════
    league_goals_home: int = 0
    league_goals_away: int = 0
    home_away_ratio: float = 1.0
    home_away_profile: str = ""  # HOME_SPECIALIST, AWAY_SPECIALIST, BALANCED
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CREATIVITY DNA
    # ═══════════════════════════════════════════════════════════════════════════
    xgchain: float = 0.0  # Implication dans actions menant au but
    xgbuildup: float = 0.0  # Création de jeu
    key_passes: int = 0
    creativity_profile: str = ""  # ELITE_CREATOR, HIGH_CREATOR, PURE_FINISHER, LIMITED
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PENALTY DNA
    # ═══════════════════════════════════════════════════════════════════════════
    is_penalty_taker: bool = False
    penalty_goals: int = 0
    penalty_pct: float = 0.0  # % buts sur penalty
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FORM DNA (Tendance récente)
    # ═══════════════════════════════════════════════════════════════════════════
    form_goals_l5: int = 0  # Buts sur 5 derniers matchs
    form_xg_l5: float = 0.0
    hot_streak: bool = False  # goals - xG >= 5
    cold_streak: bool = False  # goals - xG <= -3
    form_trend: str = ""  # HOT_STREAK, GOOD_FORM, STABLE, POOR_FORM, COLD_STREAK
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TEAM DEPENDENCY
    # ═══════════════════════════════════════════════════════════════════════════
    team_goal_share: float = 0.0  # % des buts de l'équipe
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTHODES DE CALCUL
    # ═══════════════════════════════════════════════════════════════════════════
    
    def calculate_league_ratio(self) -> None:
        """Calcule le ratio ligue et le tag de fiabilité"""
        if self.total_goals > 0:
            self.league_ratio = self.league_goals / self.total_goals
        else:
            self.league_ratio = 1.0 if self.league_goals > 0 else 0.0
            
        if self.league_ratio >= 0.5:
            self.reliability_tag = "LEAGUE_SPECIALIST"
        elif self.league_ratio >= 0.3:
            self.reliability_tag = "BALANCED"
        else:
            self.reliability_tag = "CUP_PERFORMER"
            
    def calculate_timing_pcts(self) -> None:
        """Calcule les pourcentages timing depuis les volumes ligue"""
        total = self.league_goals or 1
        self.goals_1h_pct = (self.league_goals_1h / total) * 100
        self.goals_2h_pct = (self.league_goals_2h / total) * 100
        self.clutch_pct = ((self.league_goals_76_90 + self.league_goals_90_plus) / total) * 100
        self.first_goal_pct = (self.league_goals_0_15 / total) * 100
        
    def calculate_efficiency(self) -> None:
        """Calcule les métriques d'efficacité"""
        if self.minutes > 0:
            self.goals_per_90 = (self.total_goals / self.minutes) * 90
            if self.total_goals > 0:
                self.minutes_per_goal = self.minutes / self.total_goals
        if self.shots > 0:
            self.conversion_rate = (self.total_goals / self.shots) * 100
            self.xg_per_shot = self.total_xG / self.shots
        self.xg_overperformance = self.total_goals - self.total_xG
        
    def determine_shot_quality(self) -> None:
        """Détermine le profil shot quality"""
        conv = self.conversion_rate
        xg_shot = self.xg_per_shot
        shots_90 = (self.shots / self.minutes * 90) if self.minutes > 0 else 0
        
        if conv >= 20 and xg_shot >= 0.12:
            self.shot_quality = "ELITE_FINISHER"
        elif conv >= 18 and self.total_goals >= 10:
            self.shot_quality = "CLINICAL"
        elif shots_90 >= 3.5 and conv < 12:
            self.shot_quality = "VOLUME_SHOOTER"
        elif xg_shot >= 0.12 and conv < 10:
            self.shot_quality = "WASTEFUL"
        elif conv >= 15:
            self.shot_quality = "EFFICIENT"
        elif self.shots < 20 and conv >= 15:
            self.shot_quality = "OPPORTUNIST"
        else:
            self.shot_quality = "POOR_FINISHER"
            
    def determine_playing_time_profile(self) -> None:
        """Détermine le profil playing time"""
        mpg = self.minutes_per_game
        g90 = self.goals_per_90
        
        if mpg >= 85:
            self.playing_time_profile = "UNDISPUTED_STARTER"
        elif mpg >= 75:
            self.playing_time_profile = "STARTER"
        elif mpg >= 60:
            self.playing_time_profile = "REGULAR"
        elif mpg >= 45:
            self.playing_time_profile = "ROTATION"
        elif mpg < 45 and g90 >= 0.5:
            self.playing_time_profile = "SUPER_SUB"  # 🔥 VALUE!
        else:
            self.playing_time_profile = "BENCH"
            
    def determine_timing_profile(self) -> None:
        """Détermine le profil timing"""
        if self.goals_2h_pct >= 60:
            self.timing_profile = "DIESEL_SCORER"
        elif self.goals_1h_pct >= 55:
            self.timing_profile = "EARLY_BIRD"
        elif self.clutch_pct >= 25:
            self.timing_profile = "CLUTCH"
        elif self.first_goal_pct >= 20:
            self.timing_profile = "EARLY_KILLER"
        else:
            self.timing_profile = "BALANCED_TIMING"
            
    def determine_home_away_profile(self) -> None:
        """Détermine le profil home/away"""
        if self.league_goals_away > 0:
            self.home_away_ratio = self.league_goals_home / self.league_goals_away
        elif self.league_goals_home > 0:
            self.home_away_ratio = 10.0  # Très home
        else:
            self.home_away_ratio = 1.0
            
        if self.home_away_ratio >= 2.0:
            self.home_away_profile = "HOME_SPECIALIST"
        elif self.home_away_ratio <= 0.5:
            self.home_away_profile = "AWAY_SPECIALIST"
        else:
            self.home_away_profile = "BALANCED"
            
    def determine_creativity_profile(self) -> None:
        """Détermine le profil créativité"""
        if self.total_xA >= 10 and self.total_assists >= 8:
            self.creativity_profile = "ELITE_CREATOR"
        elif self.total_xA >= 7 and self.total_assists >= 6:
            self.creativity_profile = "HIGH_CREATOR"
        elif self.total_goals >= 12 and self.total_xA < 3 and self.total_assists < 4:
            self.creativity_profile = "PURE_FINISHER"
        elif self.total_xA >= 5 or self.total_assists >= 4:
            self.creativity_profile = "CREATIVE"
        elif self.total_xA >= 3 or self.total_assists >= 3:
            self.creativity_profile = "INVOLVED"
        else:
            self.creativity_profile = "LIMITED"
            
    def determine_form_trend(self) -> None:
        """Détermine le trend de forme"""
        diff = self.xg_overperformance
        
        if diff >= 5:
            self.form_trend = "HOT_STREAK"
            self.hot_streak = True
        elif diff >= 2:
            self.form_trend = "GOOD_FORM"
        elif diff >= -1:
            self.form_trend = "STABLE"
        elif diff >= -3:
            self.form_trend = "POOR_FORM"
        else:
            self.form_trend = "COLD_STREAK"
            self.cold_streak = True
            
    def calculate_penalty_pct(self) -> None:
        """Calcule le % de buts sur penalty"""
        if self.total_goals > 0:
            self.penalty_pct = (self.penalty_goals / self.total_goals) * 100
            
    def calculate_all(self) -> None:
        """Calcule toutes les métriques dérivées"""
        self.calculate_league_ratio()
        self.calculate_timing_pcts()
        self.calculate_efficiency()
        self.determine_shot_quality()
        self.determine_playing_time_profile()
        self.determine_timing_profile()
        self.determine_home_away_profile()
        self.determine_creativity_profile()
        self.determine_form_trend()
        self.calculate_penalty_pct()


@dataclass
class TeamFullData:
    """Données offensives complètes d'une équipe"""
    team_name: str
    league: str = ""
    
    # Volumes LIGUE
    league_goals: int = 0
    league_xG: float = 0.0
    
    # Joueurs
    players: List[PlayerFullProfile] = field(default_factory=list)
    
    # Timing DNA équipe
    goals_by_period: Dict[str, int] = field(default_factory=dict)
    goals_1h: int = 0
    goals_2h: int = 0
    
    # Style DNA équipe
    goals_by_situation: Dict[str, int] = field(default_factory=dict)
    goals_by_shot_type: Dict[str, int] = field(default_factory=dict)
    
    # Home/Away DNA
    goals_home: int = 0
    goals_away: int = 0
    
    # Context DNA (Understat)
    timing_xg: Dict[str, float] = field(default_factory=dict)
    gamestate_xg: Dict[str, float] = field(default_factory=dict)
    attack_speed: Dict[str, float] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# LOADER V3 - FULL INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

class AttackDataLoaderV3:
    """
    Loader COMPLET intégrant TOUTES les métriques du dictionnaire.
    """
    
    def __init__(self):
        self.players: Dict[str, PlayerFullProfile] = {}
        self.teams: Dict[str, TeamFullData] = {}
        self.raw_goals: List[dict] = []
        
    def load_all(self) -> None:
        """Charge toutes les sources et calcule tout"""
        print("=" * 80)
        print("🎯 ATTACK DATA LOADER V3.0 - FULL QUANT INSTITUTIONNEL")
        print("=" * 80)
        
        self._load_league_goals()
        self._load_player_stats_full()
        self._load_context_dna()
        self._aggregate_teams()
        self._calculate_all_metrics()
        
        print(f"\n✅ Chargement COMPLET terminé:")
        print(f"   • {len(self.raw_goals)} buts LIGUE analysés")
        print(f"   • {len(self.players)} joueurs avec profil COMPLET")
        print(f"   • {len(self.teams)} équipes agrégées")
        
    def _load_league_goals(self) -> None:
        """Charge all_goals_2025.json - SOURCE LIGUE"""
        print("\n📊 [1/4] Chargement all_goals_2025.json (LIGUE)...")
        
        path = DATA_DIR / 'goal_analysis/all_goals_2025.json'
        if not path.exists():
            print(f"   ⚠️ Fichier non trouvé: {path}")
            return
            
        with open(path) as f:
            self.raw_goals = json.load(f)
            
        # Créer les profils joueurs depuis les buts ligue
        for g in self.raw_goals:
            scorer = g.get('scorer', '')
            team = g.get('scoring_team', '')
            if not scorer or not team:
                continue
                
            key = f"{scorer}|{team}"
            if key not in self.players:
                self.players[key] = PlayerFullProfile(
                    player_name=scorer,
                    team=team
                )
                
            p = self.players[key]
            p.league_goals += 1
            p.league_xG += float(g.get('xG', 0))
            
            # Timing
            half = g.get('half', '')
            if half == "1H":
                p.league_goals_1h += 1
            else:
                p.league_goals_2h += 1
                
            period = g.get('timing_period', '')
            period_map = {
                "0-15": "league_goals_0_15", "16-30": "league_goals_16_30",
                "31-45": "league_goals_31_45", "46-60": "league_goals_46_60",
                "61-75": "league_goals_61_75", "76-90": "league_goals_76_90",
                "90+": "league_goals_90_plus"
            }
            if period in period_map:
                setattr(p, period_map[period], getattr(p, period_map[period]) + 1)
                
            # Style
            situation = g.get('situation', '')
            if 'Corner' in situation:
                p.league_goals_corner += 1
            elif situation == 'Penalty':
                p.league_goals_penalty += 1
            elif 'Freekick' in situation or 'SetPiece' in situation:
                p.league_goals_freekick += 1
            else:
                p.league_goals_open_play += 1
                
            shot_type = g.get('shot_type', '')
            if shot_type == 'RightFoot':
                p.league_goals_right_foot += 1
            elif shot_type == 'LeftFoot':
                p.league_goals_left_foot += 1
            elif shot_type == 'Head':
                p.league_goals_header += 1
                
            # Home/Away
            if g.get('home_away') == 'h':
                p.league_goals_home += 1
            else:
                p.league_goals_away += 1
                
        print(f"   ✅ {len(self.raw_goals)} buts, {len(self.players)} joueurs")
        
    def _load_player_stats_full(self) -> None:
        """Charge player_stats pour enrichissement COMPLET - MATCHING PAR NOM"""
        print("\n📊 [2/4] Chargement player_stats (ENRICHISSEMENT PAR NOM)...")
        
        try:
            import sys
            sys.path.insert(0, '/home/Mon_ps')
            from agents.attack_v1.data.loader import AttackDataLoader
            
            old_loader = AttackDataLoader()
            old_loader.load_all()
            
            # Créer un index par nom de joueur (sans équipe)
            player_stats_by_name = {}
            for team_name, team_data in old_loader.teams.items():
                for ps in team_data.players:
                    # Stocker par nom seulement (le dernier écrase si doublon)
                    player_stats_by_name[ps.player_name] = ps
                    
            enriched = 0
            transfers_detected = 0
            
            # Enrichir les joueurs de all_goals (saison 2025/2026)
            for key, p in self.players.items():
                # Chercher par nom seulement
                if p.player_name in player_stats_by_name:
                    ps = player_stats_by_name[p.player_name]
                    
                    # Détecter transfert
                    if ps.team != p.team:
                        transfers_detected += 1
                        
                    # Enrichir avec TOUTES les données player_stats (2024/2025)
                    # Note: équipe = celle de 2025/2026 (all_goals), profils = 2024/2025
                    p.player_id = ps.player_id
                    p.position = ps.position
                    p.old_team = ps.team  # Pour traçabilité
                    
                    # Volumes toutes comp (saison 2024/2025)
                    p.total_goals = ps.goals
                    p.total_assists = ps.assists
                    p.total_xG = ps.xg
                    p.total_xA = ps.assists  # xA ≈ assists réels (xgchain est différent)
                    p.npg = ps.npg
                    p.npxG = ps.npxg
                    p.shots = ps.shots
                    
                    # Playing time
                    p.minutes = ps.minutes
                    p.games = ps.games
                    p.minutes_per_game = ps.minutes_per_game
                    
                    # Creativity
                    p.xgchain = ps.xgchain
                    p.xgbuildup = ps.xgbuildup
                    p.key_passes = ps.key_passes
                    
                    # Penalty
                    p.is_penalty_taker = ps.is_penalty_taker
                    p.penalty_goals = ps.penalty_goals
                    
                    # Form
                    p.form_goals_l5 = ps.form_goals_l5
                    p.form_xg_l5 = ps.form_xg_l5
                    p.hot_streak = ps.hot_streak
                    p.cold_streak = ps.cold_streak
                    
                    # Team share
                    p.team_goal_share = ps.team_goal_share
                    
                    enriched += 1
                    
            print(f"   ✅ {enriched} joueurs enrichis")
            print(f"   🔄 {transfers_detected} transferts détectés (équipe différente 2024→2025)")
            
        except Exception as e:
            print(f"   ⚠️ Erreur: {e}")
            
    def _load_context_dna(self) -> None:
        """Charge teams_context_dna.json"""
        print("\n📊 [3/4] Chargement teams_context_dna.json...")
        
        path = DATA_DIR / 'quantum_v2/teams_context_dna.json'
        if not path.exists():
            return
            
        with open(path) as f:
            self.context_dna = json.load(f)
            
        print(f"   ✅ {len(self.context_dna)} équipes")
        
    def _aggregate_teams(self) -> None:
        """Agrège par équipe"""
        print("\n📊 [4/4] Agrégation par équipe...")
        
        # Grouper joueurs
        players_by_team = defaultdict(list)
        for p in self.players.values():
            players_by_team[p.team].append(p)
            
        # Grouper buts
        goals_by_team = defaultdict(list)
        for g in self.raw_goals:
            goals_by_team[g.get('scoring_team', '')].append(g)
            
        # Créer équipes
        for team_name, team_goals in goals_by_team.items():
            team = TeamFullData(team_name=team_name)
            team.players = players_by_team.get(team_name, [])
            team.league_goals = len(team_goals)
            team.league_xG = sum(float(g.get('xG', 0)) for g in team_goals)
            
            # Timing
            for g in team_goals:
                period = g.get('timing_period', '')
                team.goals_by_period[period] = team.goals_by_period.get(period, 0) + 1
                if g.get('half') == '1H':
                    team.goals_1h += 1
                else:
                    team.goals_2h += 1
                    
            # Style
            for g in team_goals:
                sit = g.get('situation', '')
                team.goals_by_situation[sit] = team.goals_by_situation.get(sit, 0) + 1
                shot = g.get('shot_type', '')
                team.goals_by_shot_type[shot] = team.goals_by_shot_type.get(shot, 0) + 1
                
            # Home/Away
            for g in team_goals:
                if g.get('home_away') == 'h':
                    team.goals_home += 1
                else:
                    team.goals_away += 1
                    
            # Context DNA
            if hasattr(self, 'context_dna') and team_name in self.context_dna:
                ctx = self.context_dna[team_name]
                team.league = ctx.get('league', '')
                if 'raw_statistics' in ctx:
                    raw = ctx['raw_statistics']
                    team.timing_xg = raw.get('timing', {})
                    team.gamestate_xg = raw.get('gameState', {})
                if 'context_dna' in ctx:
                    team.attack_speed = ctx['context_dna'].get('attackSpeed', {})
                    
            self.teams[team_name] = team
            
        print(f"   ✅ {len(self.teams)} équipes")
        
    def _calculate_all_metrics(self) -> None:
        """Calcule toutes les métriques pour tous les joueurs"""
        print("\n📊 Calcul de toutes les métriques...")
        
        super_subs = []
        cup_performers = []
        hot_streaks = []
        cold_streaks = []
        elite_finishers = []
        
        for p in self.players.values():
            p.calculate_all()
            
            # Collecter insights
            if p.playing_time_profile == "SUPER_SUB" and p.league_goals >= 2:
                super_subs.append(p)
            if p.reliability_tag == "CUP_PERFORMER" and p.league_goals >= 2:
                cup_performers.append(p)
            if p.hot_streak and p.total_goals >= 5:
                hot_streaks.append(p)
            if p.cold_streak and p.total_xG >= 5:
                cold_streaks.append(p)
            if p.shot_quality == "ELITE_FINISHER" and p.league_goals >= 3:
                elite_finishers.append(p)
                
        # Afficher insights
        print(f"\n   📊 INSIGHTS DÉTECTÉS:")
        print(f"      • {len(super_subs)} SUPER_SUB (VALUE pour Last Goalscorer)")
        print(f"      • {len(cup_performers)} CUP_PERFORMERS (⚠️ éviter pour paris ligue)")
        print(f"      • {len(hot_streaks)} HOT_STREAK (🔥 en forme)")
        print(f"      • {len(cold_streaks)} COLD_STREAK (💎 VALUE régression)")
        print(f"      • {len(elite_finishers)} ELITE_FINISHER")
        
        if super_subs:
            print(f"\n   🔥 TOP SUPER_SUB (VALUE Last Goalscorer):")
            for p in sorted(super_subs, key=lambda x: x.goals_per_90, reverse=True)[:5]:
                print(f"      {p.player_name} ({p.team}): {p.league_goals}G ligue, {p.goals_per_90:.2f} G/90, {p.minutes_per_game:.0f} min/match")
                
        if cold_streaks:
            print(f"\n   💎 COLD_STREAK avec haut xG (VALUE régression positive):")
            for p in sorted(cold_streaks, key=lambda x: x.xg_overperformance)[:5]:
                print(f"      {p.player_name} ({p.team}): {p.total_goals}G vs {p.total_xG:.1f}xG ({p.xg_overperformance:+.1f})")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # GETTERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_team(self, team_name: str) -> Optional[TeamFullData]:
        return self.teams.get(team_name)
        
    def get_player(self, name: str, team: str = None) -> Optional[PlayerFullProfile]:
        if team:
            return self.players.get(f"{name}|{team}")
        for p in self.players.values():
            if p.player_name == name:
                return p
        return None
        
    def get_top_scorers_league(self, team: str = None, n: int = 10) -> List[PlayerFullProfile]:
        """Top buteurs EN LIGUE"""
        if team:
            players = self.teams.get(team, TeamFullData(team)).players
        else:
            players = list(self.players.values())
        return sorted(players, key=lambda p: p.league_goals, reverse=True)[:n]
        
    def get_reliable_scorers(self, min_goals: int = 3) -> List[PlayerFullProfile]:
        """Buteurs FIABLES (pas CUP_PERFORMER)"""
        return [p for p in self.players.values()
                if p.league_goals >= min_goals and p.reliability_tag != "CUP_PERFORMER"]
                
    def get_super_subs(self, min_goals: int = 2) -> List[PlayerFullProfile]:
        """SUPER_SUB - VALUE pour Last Goalscorer"""
        return sorted(
            [p for p in self.players.values() 
             if p.playing_time_profile == "SUPER_SUB" and p.league_goals >= min_goals],
            key=lambda x: x.goals_per_90, reverse=True
        )
        
    def get_early_birds(self, min_goals: int = 3) -> List[PlayerFullProfile]:
        """EARLY_BIRD - VALUE pour First Goalscorer"""
        return sorted(
            [p for p in self.players.values()
             if p.timing_profile == "EARLY_BIRD" and p.league_goals >= min_goals],
            key=lambda x: x.first_goal_pct, reverse=True
        )
        
    def get_value_regression(self, min_xg: float = 5) -> List[PlayerFullProfile]:
        """COLD_STREAK avec haut xG - VALUE régression positive"""
        return sorted(
            [p for p in self.players.values()
             if p.cold_streak and p.total_xG >= min_xg],
            key=lambda x: x.xg_overperformance
        )
        
    def get_penalty_takers(self) -> List[PlayerFullProfile]:
        """Tireurs de penalty - BONUS First Goalscorer"""
        return [p for p in self.players.values() if p.is_penalty_taker]
        
    def get_elite_creators(self, min_xa: float = 5) -> List[PlayerFullProfile]:
        """ELITE_CREATOR - VALUE pour Assist market"""
        return sorted(
            [p for p in self.players.values()
             if p.creativity_profile in ["ELITE_CREATOR", "HIGH_CREATOR"] and p.total_xA >= min_xa],
            key=lambda x: x.total_xA, reverse=True
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    loader = AttackDataLoaderV3()
    loader.load_all()
