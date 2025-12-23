"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🎯 ATTACK DATA LOADER V5.0 - HEDGE FUND GRADE 2025/2026                     ║
║                                                                              ║
║  FUSION COMPLÈTE de toutes les données actuelles:                            ║
║  • players_impact_dna.json (2293 joueurs - efficacité, créativité, cartons)  ║
║  • all_goals_2025.json (1844 buts - timing, style, home/away)                ║
║  • teams_context_dna.json (96 équipes - xG timing, gamestate)                ║
║                                                                              ║
║  TOUTES LES MÉTRIQUES DU DICTIONNAIRE:                                       ║
║  ✅ Efficacité (goals_per_90, conversion, xG_per_shot)                       ║
║  ✅ Playing Time (SUPER_SUB, STARTER, minutes_per_game)                      ║
║  ✅ Creativity (xA, xGChain, xGBuildup, key_passes)                          ║
║  ✅ Penalty (is_penalty_taker, penalty_pct)                                  ║
║  ✅ Cards (yellow, red, cards_per_90)                                        ║
║  ✅ Timing (DIESEL, FAST_STARTER, clutch_pct) - from all_goals               ║
║  ✅ Style (open_play, headers, set_pieces) - from all_goals                  ║
║  ✅ Home/Away (HOME_SPECIALIST, AWAY_SPECIALIST) - from all_goals            ║
║  ✅ Form (xG_overperformance, CLINICAL, WASTEFUL)                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path
from collections import defaultdict
import json

# Migration SQL - Phase 4.2
from services.goals.data_provider import GoalsDataProvider
from services.data.normalizer import DataNormalizer

DATA_DIR = Path('/home/Mon_ps/data')


def safe_int(v):
    """Convertit en int de façon sûre"""
    try: return int(float(v)) if v else 0
    except: return 0

def safe_float(v):
    """Convertit en float de façon sûre"""
    try: return float(v) if v else 0.0
    except: return 0.0


@dataclass
class PlayerFullProfile2025:
    """
    Profil COMPLET joueur 2025/2026 - TOUTES métriques du dictionnaire.
    """
    player_id: str = ""
    player_name: str = ""
    team: str = ""
    league: str = ""
    position: str = ""
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VOLUMES (players_impact_dna)
    # ═══════════════════════════════════════════════════════════════════════════
    goals: int = 0
    npg: int = 0  # Non-penalty goals
    xG: float = 0.0
    npxG: float = 0.0
    assists: int = 0
    xA: float = 0.0
    shots: int = 0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PLAYING TIME (players_impact_dna)
    # ═══════════════════════════════════════════════════════════════════════════
    minutes: int = 0
    games: int = 0
    minutes_per_game: float = 0.0
    playing_time_profile: str = ""  # UNDISPUTED_STARTER, STARTER, SUPER_SUB, etc.
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EFFICACITÉ (calculée)
    # ═══════════════════════════════════════════════════════════════════════════
    goals_per_90: float = 0.0
    xG_per_90: float = 0.0
    minutes_per_goal: float = 0.0
    conversion_rate: float = 0.0  # goals / shots %
    xG_per_shot: float = 0.0
    xG_overperformance: float = 0.0  # goals - xG
    shot_quality: str = ""  # ELITE_FINISHER, CLINICAL, WASTEFUL, etc.
    finishing_trend: str = ""  # CLINICAL, EXPECTED, WASTEFUL
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CREATIVITY (players_impact_dna)
    # ═══════════════════════════════════════════════════════════════════════════
    xGChain: float = 0.0
    xGBuildup: float = 0.0
    key_passes: int = 0
    xA_per_90: float = 0.0
    creativity_profile: str = ""  # ELITE_CREATOR, HIGH_CREATOR, PURE_FINISHER
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PENALTY (calculé depuis npg)
    # ═══════════════════════════════════════════════════════════════════════════
    penalty_goals: int = 0
    penalty_pct: float = 0.0
    is_penalty_taker: bool = False
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CARDS (players_impact_dna)
    # ═══════════════════════════════════════════════════════════════════════════
    yellow_cards: int = 0
    red_cards: int = 0
    cards_per_90: float = 0.0
    card_profile: str = ""  # DIRTY, AGGRESSIVE, CLEAN
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TIMING DNA (from all_goals_2025.json)
    # ═══════════════════════════════════════════════════════════════════════════
    goals_1h: int = 0
    goals_2h: int = 0
    goals_0_15: int = 0
    goals_16_30: int = 0
    goals_31_45: int = 0
    goals_46_60: int = 0
    goals_61_75: int = 0
    goals_76_90: int = 0
    goals_90_plus: int = 0
    
    pct_1h: float = 0.0
    pct_2h: float = 0.0
    pct_clutch: float = 0.0  # 76-90 + 90+
    pct_early: float = 0.0   # 0-15
    timing_profile: str = ""  # DIESEL, FAST_STARTER, CLUTCH, BALANCED
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STYLE DNA (from all_goals_2025.json)
    # ═══════════════════════════════════════════════════════════════════════════
    goals_open_play: int = 0
    goals_corner: int = 0
    goals_set_piece: int = 0
    goals_right_foot: int = 0
    goals_left_foot: int = 0
    goals_header: int = 0
    
    pct_open_play: float = 0.0
    pct_header: float = 0.0
    pct_set_piece: float = 0.0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HOME/AWAY DNA (from all_goals_2025.json)
    # ═══════════════════════════════════════════════════════════════════════════
    goals_home: int = 0
    goals_away: int = 0
    pct_home: float = 0.0
    home_away_ratio: float = 1.0
    home_away_profile: str = ""  # HOME_SPECIALIST, AWAY_SPECIALIST, BALANCED
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TEAM CONTEXT
    # ═══════════════════════════════════════════════════════════════════════════
    team_goals: int = 0
    team_share: float = 0.0
    dependency_tag: str = ""  # MVP, KEY_PLAYER, CONTRIBUTOR, ROTATIONAL
    
    def calculate_all(self) -> None:
        """Calcule toutes les métriques dérivées"""
        
        # Playing time profile
        if self.games > 0:
            self.minutes_per_game = self.minutes / self.games
            
        # SUPER_SUB = peu de minutes MAIS très efficace (priorité!)
        if self.minutes >= 200 and self.minutes_per_game < 50 and self.goals >= 2:
            # Calculer G/90 d'abord
            g90 = (self.goals / self.minutes) * 90 if self.minutes > 0 else 0
            if g90 >= 0.5:
                self.playing_time_profile = "SUPER_SUB"
            elif self.minutes_per_game >= 30:
                self.playing_time_profile = "ROTATION"
            else:
                self.playing_time_profile = "BENCH"
        elif self.minutes_per_game >= 85:
            self.playing_time_profile = "UNDISPUTED_STARTER"
        elif self.minutes_per_game >= 70:
            self.playing_time_profile = "STARTER"
        elif self.minutes_per_game >= 50:
            self.playing_time_profile = "REGULAR"
        elif self.minutes_per_game >= 30:
            self.playing_time_profile = "ROTATION"
        else:
            self.playing_time_profile = "BENCH"
            
        # Efficacité
        if self.minutes > 0:
            self.goals_per_90 = (self.goals / self.minutes) * 90
            self.xG_per_90 = (self.xG / self.minutes) * 90
            self.xA_per_90 = (self.xA / self.minutes) * 90
            self.cards_per_90 = ((self.yellow_cards + self.red_cards) / self.minutes) * 90
        if self.goals > 0:
            self.minutes_per_goal = self.minutes / self.goals
        if self.shots > 0:
            self.conversion_rate = (self.goals / self.shots) * 100
            self.xG_per_shot = self.xG / self.shots
            
        # xG performance
        self.xG_overperformance = self.goals - self.xG
        if self.xG_overperformance >= 3:
            self.finishing_trend = "HOT_STREAK"
        elif self.xG_overperformance >= 1:
            self.finishing_trend = "CLINICAL"
        elif self.xG_overperformance >= -1:
            self.finishing_trend = "EXPECTED"
        elif self.xG_overperformance >= -3:
            self.finishing_trend = "COLD"
        else:
            self.finishing_trend = "WASTEFUL"
            
        # Shot quality profile
        if self.shots >= 10:
            if self.conversion_rate >= 25 and self.xG_per_shot >= 0.12:
                self.shot_quality = "ELITE_FINISHER"
            elif self.conversion_rate >= 20:
                self.shot_quality = "CLINICAL"
            elif self.conversion_rate >= 15:
                self.shot_quality = "EFFICIENT"
            elif self.shots >= 30 and self.conversion_rate < 12:
                self.shot_quality = "VOLUME_SHOOTER"
            elif self.xG_per_shot >= 0.12 and self.conversion_rate < 12:
                self.shot_quality = "WASTEFUL"
            else:
                self.shot_quality = "AVERAGE"
        else:
            self.shot_quality = "LOW_VOLUME"
            
        # Penalty
        self.penalty_goals = self.goals - self.npg
        if self.goals > 0:
            self.penalty_pct = (self.penalty_goals / self.goals) * 100
        self.is_penalty_taker = self.penalty_goals >= 2
        
        # Cards profile
        if self.cards_per_90 >= 0.4:
            self.card_profile = "DIRTY"
        elif self.cards_per_90 >= 0.25:
            self.card_profile = "AGGRESSIVE"
        else:
            self.card_profile = "CLEAN"
            
        # Creativity profile
        if self.xA >= 4 and self.assists >= 4:
            self.creativity_profile = "ELITE_CREATOR"
        elif self.xA >= 2.5 or self.assists >= 3:
            self.creativity_profile = "HIGH_CREATOR"
        elif self.goals >= 8 and self.xA < 2 and self.assists < 3:
            self.creativity_profile = "PURE_FINISHER"
        elif self.xA >= 1.5 or self.assists >= 2:
            self.creativity_profile = "CREATIVE"
        else:
            self.creativity_profile = "LIMITED"
            
        # Timing profile (from goals data)
        if self.goals > 0:
            total = self.goals
            self.pct_1h = (self.goals_1h / total) * 100
            self.pct_2h = (self.goals_2h / total) * 100
            self.pct_clutch = ((self.goals_76_90 + self.goals_90_plus) / total) * 100
            self.pct_early = (self.goals_0_15 / total) * 100
            
            if self.pct_2h >= 65:
                self.timing_profile = "DIESEL"
            elif self.pct_1h >= 60:
                self.timing_profile = "FAST_STARTER"
            elif self.pct_clutch >= 30:
                self.timing_profile = "CLUTCH"
            elif self.pct_early >= 25:
                self.timing_profile = "EARLY_KILLER"
            else:
                self.timing_profile = "BALANCED"
                
        # Style percentages
        if self.goals > 0:
            total = self.goals
            self.pct_open_play = (self.goals_open_play / total) * 100
            self.pct_header = (self.goals_header / total) * 100
            self.pct_set_piece = ((self.goals_corner + self.goals_set_piece) / total) * 100
            
        # Home/Away profile
        if self.goals > 0:
            self.pct_home = (self.goals_home / self.goals) * 100
        if self.goals_away > 0:
            self.home_away_ratio = self.goals_home / self.goals_away
        elif self.goals_home > 0:
            self.home_away_ratio = 5.0
            
        if self.home_away_ratio >= 2.5:
            self.home_away_profile = "HOME_SPECIALIST"
        elif self.home_away_ratio <= 0.4:
            self.home_away_profile = "AWAY_SPECIALIST"
        else:
            self.home_away_profile = "BALANCED"
            
        # Team dependency
        if self.team_goals > 0:
            self.team_share = (self.goals / self.team_goals) * 100
        if self.team_share >= 30:
            self.dependency_tag = "MVP"
        elif self.team_share >= 18:
            self.dependency_tag = "KEY_PLAYER"
        elif self.team_share >= 8:
            self.dependency_tag = "CONTRIBUTOR"
        else:
            self.dependency_tag = "ROTATIONAL"


@dataclass
class TeamProfile2025:
    """Profil équipe 2025/2026"""
    team_name: str = ""
    league: str = ""
    goals: int = 0
    xG: float = 0.0
    players: List[PlayerFullProfile2025] = field(default_factory=list)
    
    # Timing DNA
    goals_1h: int = 0
    goals_2h: int = 0
    pct_2h: float = 0.0
    timing_profile: str = ""
    
    # Context DNA (from teams_context_dna)
    timing_xg: Dict = field(default_factory=dict)
    gamestate_xg: Dict = field(default_factory=dict)
    attack_speed: Dict = field(default_factory=dict)


class AttackDataLoaderV5:
    """
    Loader FINAL 2025/2026 - HEDGE FUND GRADE.
    Fusionne players_impact_dna + all_goals + teams_context_dna.
    """
    
    def __init__(self):
        self.players: Dict[str, PlayerFullProfile2025] = {}
        self.teams: Dict[str, TeamProfile2025] = {}
        
    def load_all(self) -> None:
        """Charge et fusionne toutes les sources"""
        print("=" * 80)
        print("🎯 ATTACK DATA LOADER V5.0 - HEDGE FUND GRADE 2025/2026")
        print("=" * 80)
        
        self._load_players_impact_dna()
        self._load_goals_timing_style()
        self._load_context_dna()
        self._aggregate_teams()
        self._calculate_all()
        
        print(f"\n✅ Chargement COMPLET 2025/2026:")
        print(f"   • {len(self.players)} joueurs avec profil COMPLET")
        print(f"   • {len(self.teams)} équipes")
        
    def _load_players_impact_dna(self) -> None:
        """Charge players_impact_dna.json - SOURCE PRINCIPALE"""
        print("\n📊 [1/4] Chargement players_impact_dna.json...")
        
        path = DATA_DIR / 'quantum_v2/players_impact_dna.json'
        with open(path) as f:
            raw_data = json.load(f)

        # Normalisation robuste - cle composite pour gerer les transferts
        # (31 joueurs ont le meme ID mais des equipes differentes)
        data = DataNormalizer.to_dict(raw_data, key_fields=["id", "team"])

        for pid, player in data.items():
            if not isinstance(player, dict):
                continue
                
            name = player.get('player_name', '')
            team = player.get('team', '')
            if not name or not team:
                continue
                
            key = f"{name}|{team}"
            p = PlayerFullProfile2025(
                player_id=pid,
                player_name=name,
                team=team,
                league=player.get('league', ''),
                position=player.get('position', ''),
                goals=safe_int(player.get('goals', 0)),
                npg=safe_int(player.get('npg', 0)),
                xG=safe_float(player.get('xG', 0)),
                npxG=safe_float(player.get('npxG', 0)),
                assists=safe_int(player.get('assists', 0)),
                xA=safe_float(player.get('xA', 0)),
                shots=safe_int(player.get('shots', 0)),
                minutes=safe_int(player.get('time', 0)),
                games=safe_int(player.get('games', 0)),
                xGChain=safe_float(player.get('xGChain', 0)),
                xGBuildup=safe_float(player.get('xGBuildup', 0)),
                key_passes=safe_int(player.get('key_passes', 0)),
                yellow_cards=safe_int(player.get('yellow_cards', 0)),
                red_cards=safe_int(player.get('red_cards', 0)),
            )
            self.players[key] = p
            
        print(f"   ✅ {len(self.players)} joueurs chargés")
        
    def _load_goals_timing_style(self) -> None:
        """Charge goals depuis PostgreSQL (GoalsDataProvider)"""
        print("\n📊 [2/4] Chargement goals depuis PostgreSQL (timing/style)...")

        # Migration SQL - remplace all_goals_2025.json
        provider = GoalsDataProvider()
        goals = provider.get_all_goals()
        provider.close()
            
        # Enrichir les joueurs avec timing et style
        goals_enriched = 0
        for g in goals:
            scorer = g.get('scorer', '')
            team = g.get('scoring_team', '')
            key = f"{scorer}|{team}"
            
            if key not in self.players:
                continue
                
            p = self.players[key]
            goals_enriched += 1
            
            # Timing
            half = g.get('half', '')
            if half == '1H':
                p.goals_1h += 1
            else:
                p.goals_2h += 1
                
            period = g.get('timing_period', '')
            period_map = {
                '0-15': 'goals_0_15', '16-30': 'goals_16_30', '31-45': 'goals_31_45',
                '46-60': 'goals_46_60', '61-75': 'goals_61_75', '76-90': 'goals_76_90',
                '90+': 'goals_90_plus'
            }
            if period in period_map:
                attr = period_map[period]
                setattr(p, attr, getattr(p, attr) + 1)
                
            # Style - Situation
            situation = g.get('situation', '')
            if 'Corner' in situation:
                p.goals_corner += 1
            elif 'Freekick' in situation or 'SetPiece' in situation:
                p.goals_set_piece += 1
            else:
                p.goals_open_play += 1
                
            # Style - Shot type
            shot = g.get('shot_type', '')
            if shot == 'RightFoot':
                p.goals_right_foot += 1
            elif shot == 'LeftFoot':
                p.goals_left_foot += 1
            elif shot == 'Head':
                p.goals_header += 1
                
            # Home/Away (is_home est un boolean depuis PostgreSQL)
            if g.get('is_home'):
                p.goals_home += 1
            else:
                p.goals_away += 1
                
        print(f"   ✅ {len(goals)} buts, {goals_enriched} enrichissements")
        
    def _load_context_dna(self) -> None:
        """Charge teams_context_dna.json"""
        print("\n📊 [3/4] Chargement teams_context_dna.json...")
        
        path = DATA_DIR / 'quantum_v2/teams_context_dna.json'
        with open(path) as f:
            self.context_dna = json.load(f)
            
        print(f"   ✅ {len(self.context_dna)} équipes")
        
    def _aggregate_teams(self) -> None:
        """Agrège par équipe"""
        print("\n📊 [4/4] Agrégation par équipe...")
        
        # Grouper joueurs par équipe
        players_by_team = defaultdict(list)
        for p in self.players.values():
            players_by_team[p.team].append(p)
            
        # Créer équipes
        for team_name, players in players_by_team.items():
            team = TeamProfile2025(
                team_name=team_name,
                players=players,
                goals=sum(p.goals for p in players),
                xG=sum(p.xG for p in players)
            )
            
            # Context DNA
            if team_name in self.context_dna:
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
        
    def _calculate_all(self) -> None:
        """Calcule toutes les métriques"""
        print("\n📊 Calcul des métriques...")
        
        # Team goals pour dependency
        team_goals = {t: team.goals for t, team in self.teams.items()}
        
        insights = defaultdict(list)
        
        for p in self.players.values():
            p.team_goals = team_goals.get(p.team, 0)
            p.calculate_all()
            
            # Collecter insights (min 3 buts)
            if p.goals >= 3:
                if p.timing_profile == "DIESEL":
                    insights['diesel'].append(p)
                elif p.timing_profile == "FAST_STARTER":
                    insights['fast_starter'].append(p)
                if p.pct_clutch >= 25:
                    insights['clutch'].append(p)
                if p.shot_quality == "ELITE_FINISHER":
                    insights['elite'].append(p)
                if p.finishing_trend == "WASTEFUL":
                    insights['wasteful'].append(p)
                if p.is_penalty_taker:
                    insights['penalty'].append(p)
            if p.playing_time_profile == "SUPER_SUB" and p.goals >= 2:
                insights['super_sub'].append(p)
            if p.creativity_profile == "ELITE_CREATOR":
                insights['creator'].append(p)
            if p.card_profile == "DIRTY" and p.minutes >= 500:
                insights['dirty'].append(p)
                
        # Afficher insights
        print(f"\n   📊 INSIGHTS 2025/2026:")
        print(f"      • {len(insights['diesel'])} DIESEL (2H specialists)")
        print(f"      • {len(insights['fast_starter'])} FAST_STARTER (1H specialists)")
        print(f"      • {len(insights['clutch'])} CLUTCH (25%+ après 75')")
        print(f"      • {len(insights['elite'])} ELITE_FINISHER")
        print(f"      • {len(insights['super_sub'])} SUPER_SUB")
        print(f"      • {len(insights['penalty'])} PENALTY TAKERS")
        print(f"      • {len(insights['creator'])} ELITE_CREATOR")
        print(f"      • {len(insights['wasteful'])} WASTEFUL (VALUE régression)")
        print(f"      • {len(insights['dirty'])} DIRTY PLAYERS (cartons)")
        
    # ═══════════════════════════════════════════════════════════════════════════
    # GETTERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_team(self, name: str) -> Optional[TeamProfile2025]:
        return self.teams.get(name)
        
    def get_player(self, name: str, team: str = None) -> Optional[PlayerFullProfile2025]:
        if team:
            return self.players.get(f"{name}|{team}")
        for p in self.players.values():
            if p.player_name == name:
                return p
        return None
        
    def get_top_scorers(self, team: str = None, n: int = 10) -> List[PlayerFullProfile2025]:
        if team:
            players = [p for p in self.players.values() if p.team == team]
        else:
            players = list(self.players.values())
        return sorted(players, key=lambda p: -p.goals)[:n]
        
    def get_diesel_scorers(self, min_goals: int = 3) -> List[PlayerFullProfile2025]:
        return sorted(
            [p for p in self.players.values() if p.timing_profile == "DIESEL" and p.goals >= min_goals],
            key=lambda x: -x.pct_2h
        )
        
    def get_fast_starters(self, min_goals: int = 3) -> List[PlayerFullProfile2025]:
        return sorted(
            [p for p in self.players.values() if p.timing_profile == "FAST_STARTER" and p.goals >= min_goals],
            key=lambda x: -x.pct_1h
        )
        
    def get_clutch_scorers(self, min_goals: int = 3) -> List[PlayerFullProfile2025]:
        return sorted(
            [p for p in self.players.values() if p.pct_clutch >= 25 and p.goals >= min_goals],
            key=lambda x: -x.pct_clutch
        )
        
    def get_super_subs(self, min_goals: int = 2) -> List[PlayerFullProfile2025]:
        return sorted(
            [p for p in self.players.values() if p.playing_time_profile == "SUPER_SUB" and p.goals >= min_goals],
            key=lambda x: -x.goals_per_90
        )
        
    def get_elite_finishers(self, min_goals: int = 3) -> List[PlayerFullProfile2025]:
        return sorted(
            [p for p in self.players.values() if p.shot_quality == "ELITE_FINISHER" and p.goals >= min_goals],
            key=lambda x: -x.conversion_rate
        )
        
    def get_penalty_takers(self) -> List[PlayerFullProfile2025]:
        return sorted(
            [p for p in self.players.values() if p.is_penalty_taker],
            key=lambda x: -x.penalty_goals
        )
        
    def get_elite_creators(self) -> List[PlayerFullProfile2025]:
        return sorted(
            [p for p in self.players.values() if p.creativity_profile == "ELITE_CREATOR"],
            key=lambda x: -x.xA
        )
        
    def get_value_regression(self, min_goals: int = 3) -> List[PlayerFullProfile2025]:
        return sorted(
            [p for p in self.players.values() if p.finishing_trend == "WASTEFUL" and p.goals >= min_goals],
            key=lambda x: x.xG_overperformance
        )
        
    def get_dirty_players(self, min_minutes: int = 500) -> List[PlayerFullProfile2025]:
        return sorted(
            [p for p in self.players.values() if p.card_profile == "DIRTY" and p.minutes >= min_minutes],
            key=lambda x: -x.cards_per_90
        )
        
    def get_header_specialists(self, min_goals: int = 2) -> List[PlayerFullProfile2025]:
        return sorted(
            [p for p in self.players.values() if p.goals_header >= 2 and p.goals >= min_goals],
            key=lambda x: -x.pct_header
        )


if __name__ == '__main__':
    loader = AttackDataLoaderV5()
    loader.load_all()
