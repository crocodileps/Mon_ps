"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🎯 ATTACK DATA LOADER V2.0 - QUANT INSTITUTIONNEL                           ║
║                                                                              ║
║  Architecture Dual-Source:                                                   ║
║  • VOLUMES (prédictions) → all_goals_2025.json (LIGUE seulement)             ║
║  • PROFILS (enrichissement) → player_stats (toutes comp = plus data)         ║
║  • NOUVELLE MÉTRIQUE: league_ratio = Ligue/Total (fiabilité)                 ║
║                                                                              ║
║  INSIGHT: Les paris sont sur la LIGUE → volumes LIGUE comme référence        ║
║  Salah: 4G ligue / 29G total = 14% → "CUP PERFORMER" → WARNING               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from collections import defaultdict
import json

DATA_DIR = Path('/home/Mon_ps/data')


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class GoalRecord:
    """Un but individuel (from all_goals_2025.json)"""
    id: str
    match_id: str
    date: str
    scorer: str
    scorer_id: str
    assister: str
    scoring_team: str
    conceding_team: str
    minute: int
    timing_period: str  # "0-15", "16-30", etc.
    half: str  # "1H", "2H"
    xG: float
    situation: str  # "OpenPlay", "Corner", "Penalty", "FromCorner", "SetPiece"
    shot_type: str  # "RightFoot", "LeftFoot", "Head"
    home_away: str  # "h", "a"
    X: float
    Y: float


@dataclass
class PlayerLeagueProfile:
    """Profil d'un joueur EN LIGUE (source: all_goals_2025.json)"""
    player_name: str
    team: str
    
    # VOLUMES LIGUE (référence pour paris)
    league_goals: int = 0
    league_xG: float = 0.0
    league_assists: int = 0
    
    # TIMING DNA (calculé depuis all_goals)
    goals_1h: int = 0
    goals_2h: int = 0
    goals_0_15: int = 0
    goals_16_30: int = 0
    goals_31_45: int = 0
    goals_46_60: int = 0
    goals_61_75: int = 0
    goals_76_90: int = 0
    goals_90_plus: int = 0
    
    # STYLE DNA (calculé depuis all_goals)
    goals_open_play: int = 0
    goals_corner: int = 0
    goals_penalty: int = 0
    goals_freekick: int = 0
    goals_right_foot: int = 0
    goals_left_foot: int = 0
    goals_header: int = 0
    
    # HOME/AWAY DNA
    goals_home: int = 0
    goals_away: int = 0
    
    # ENRICHISSEMENT depuis player_stats (toutes comp)
    total_goals_all_comp: int = 0  # Pour calculer league_ratio
    timing_profile: str = ""  # DIESEL_SCORER, EARLY_BIRD, etc.
    shot_quality: str = ""  # ELITE_FINISHER, CLINICAL, etc.
    home_away_profile: str = ""  # HOME_SPECIALIST, etc.
    
    # MÉTRIQUE CLÉ: league_ratio
    league_ratio: float = 0.0  # league_goals / total_goals_all_comp
    reliability_tag: str = ""  # LEAGUE_SPECIALIST, BALANCED, CUP_PERFORMER
    
    def calculate_league_ratio(self) -> None:
        """Calcule le ratio ligue et le tag de fiabilité"""
        if self.total_goals_all_comp > 0:
            self.league_ratio = self.league_goals / self.total_goals_all_comp
        else:
            self.league_ratio = 1.0 if self.league_goals > 0 else 0.0
            
        # Tag de fiabilité pour paris ligue
        if self.league_ratio >= 0.5:
            self.reliability_tag = "LEAGUE_SPECIALIST"  # ✅ Fiable pour paris ligue
        elif self.league_ratio >= 0.3:
            self.reliability_tag = "BALANCED"  # ⚠️ OK
        else:
            self.reliability_tag = "CUP_PERFORMER"  # 🚫 Warning pour paris ligue


@dataclass 
class TeamLeagueData:
    """Données offensives d'une équipe EN LIGUE"""
    team_name: str
    league: str = ""
    
    # VOLUMES LIGUE (référence pour paris)
    league_goals: int = 0
    league_xG: float = 0.0
    
    # Joueurs avec leurs profils ligue
    players: List[PlayerLeagueProfile] = field(default_factory=list)
    
    # TIMING DNA ÉQUIPE (depuis all_goals)
    goals_by_period: Dict[str, int] = field(default_factory=dict)
    goals_1h: int = 0
    goals_2h: int = 0
    
    # STYLE DNA ÉQUIPE
    goals_by_situation: Dict[str, int] = field(default_factory=dict)
    goals_by_shot_type: Dict[str, int] = field(default_factory=dict)
    
    # HOME/AWAY DNA
    goals_home: int = 0
    goals_away: int = 0
    
    # Context DNA (depuis teams_context_dna.json - Understat)
    timing_xg: Dict[str, float] = field(default_factory=dict)
    gamestate_xg: Dict[str, float] = field(default_factory=dict)
    attack_speed: Dict[str, float] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# LOADER V2
# ═══════════════════════════════════════════════════════════════════════════════

class AttackDataLoaderV2:
    """
    Loader Dual-Source Quant Institutionnel.
    
    Source primaire: all_goals_2025.json (LIGUE)
    Source enrichissement: player_stats, teams_context_dna
    """
    
    def __init__(self):
        self.goals: List[GoalRecord] = []
        self.players: Dict[str, PlayerLeagueProfile] = {}  # key = "name|team"
        self.teams: Dict[str, TeamLeagueData] = {}
        self.player_stats_cache: Dict[str, dict] = {}  # Enrichissement
        
    def load_all(self) -> None:
        """Charge toutes les sources"""
        print("=" * 80)
        print("🎯 ATTACK DATA LOADER V2.0 - QUANT INSTITUTIONNEL")
        print("=" * 80)
        
        self._load_league_goals()
        self._load_player_stats_enrichment()
        self._load_context_dna()
        self._aggregate_teams()
        self._calculate_ratios()
        
        print(f"\n✅ Chargement terminé:")
        print(f"   • {len(self.goals)} buts LIGUE analysés")
        print(f"   • {len(self.players)} joueurs profilés")
        print(f"   • {len(self.teams)} équipes agrégées")
        
    def _load_league_goals(self) -> None:
        """Charge all_goals_2025.json - SOURCE PRIMAIRE LIGUE"""
        print("\n📊 [SOURCE PRIMAIRE] Chargement all_goals_2025.json (LIGUE)...")
        
        path = DATA_DIR / 'goal_analysis/all_goals_2025.json'
        if not path.exists():
            print(f"   ⚠️ Fichier non trouvé: {path}")
            return
            
        with open(path) as f:
            raw_goals = json.load(f)
            
        # Parser chaque but
        for g in raw_goals:
            goal = GoalRecord(
                id=str(g.get('id', '')),
                match_id=str(g.get('match_id', '')),
                date=g.get('date', ''),
                scorer=g.get('scorer', ''),
                scorer_id=str(g.get('scorer_id', '')),
                assister=g.get('assister', ''),
                scoring_team=g.get('scoring_team', ''),
                conceding_team=g.get('conceding_team', ''),
                minute=int(g.get('minute', 0)),
                timing_period=g.get('timing_period', ''),
                half=g.get('half', ''),
                xG=float(g.get('xG', 0)),
                situation=g.get('situation', ''),
                shot_type=g.get('shot_type', ''),
                home_away=g.get('home_away', ''),
                X=float(g.get('X', 0)),
                Y=float(g.get('Y', 0))
            )
            self.goals.append(goal)
            
            # Agréger par joueur
            self._aggregate_player_goal(goal)
            
        print(f"   ✅ {len(self.goals)} buts LIGUE chargés")
        
    def _aggregate_player_goal(self, goal: GoalRecord) -> None:
        """Agrège un but dans le profil joueur"""
        key = f"{goal.scorer}|{goal.scoring_team}"
        
        if key not in self.players:
            self.players[key] = PlayerLeagueProfile(
                player_name=goal.scorer,
                team=goal.scoring_team
            )
            
        p = self.players[key]
        p.league_goals += 1
        p.league_xG += goal.xG
        
        # Timing DNA
        if goal.half == "1H":
            p.goals_1h += 1
        else:
            p.goals_2h += 1
            
        period_map = {
            "0-15": "goals_0_15", "16-30": "goals_16_30", "31-45": "goals_31_45",
            "46-60": "goals_46_60", "61-75": "goals_61_75", "76-90": "goals_76_90",
            "90+": "goals_90_plus"
        }
        attr = period_map.get(goal.timing_period)
        if attr:
            setattr(p, attr, getattr(p, attr) + 1)
            
        # Style DNA
        situation_map = {
            "OpenPlay": "goals_open_play", "FromCorner": "goals_corner",
            "Corner": "goals_corner", "Penalty": "goals_penalty",
            "SetPiece": "goals_freekick", "DirectFreekick": "goals_freekick"
        }
        attr = situation_map.get(goal.situation, "goals_open_play")
        setattr(p, attr, getattr(p, attr) + 1)
        
        shot_map = {
            "RightFoot": "goals_right_foot", "LeftFoot": "goals_left_foot",
            "Head": "goals_header"
        }
        attr = shot_map.get(goal.shot_type, "goals_right_foot")
        setattr(p, attr, getattr(p, attr) + 1)
        
        # Home/Away
        if goal.home_away == "h":
            p.goals_home += 1
        else:
            p.goals_away += 1
            
    def _load_player_stats_enrichment(self) -> None:
        """Charge player_stats pour enrichissement (profils + total_goals)"""
        print("\n📊 [ENRICHISSEMENT] Chargement player_stats (toutes comp)...")
        
        try:
            import sys
            sys.path.insert(0, '/home/Mon_ps')
            from agents.attack_v1.data.loader import AttackDataLoader
            
            old_loader = AttackDataLoader()
            old_loader.load_all()
            
            # Cacher les données pour enrichissement
            for team_name, team_data in old_loader.teams.items():
                for player in team_data.players:
                    key = f"{player.player_name}|{player.team}"
                    self.player_stats_cache[key] = {
                        'total_goals': player.goals,
                        'timing_profile': player.timing_profile,
                        'shot_quality': player.shot_quality,
                        'home_away_profile': player.home_away_profile,
                        'xg': player.xg
                    }
                    
            print(f"   ✅ {len(self.player_stats_cache)} joueurs enrichis depuis player_stats")
            
        except Exception as e:
            print(f"   ⚠️ Erreur enrichissement: {e}")
            
    def _load_context_dna(self) -> None:
        """Charge teams_context_dna.json pour xG timing/gamestate"""
        print("\n📊 [ENRICHISSEMENT] Chargement teams_context_dna.json...")
        
        path = DATA_DIR / 'quantum_v2/teams_context_dna.json'
        if not path.exists():
            print(f"   ⚠️ Fichier non trouvé: {path}")
            return
            
        with open(path) as f:
            self.context_dna = json.load(f)
            
        print(f"   ✅ {len(self.context_dna)} équipes avec context DNA")
        
    def _aggregate_teams(self) -> None:
        """Agrège les données par équipe"""
        print("\n📊 Agrégation par équipe...")
        
        # Grouper les joueurs par équipe
        players_by_team = defaultdict(list)
        for key, player in self.players.items():
            players_by_team[player.team].append(player)
            
        # Grouper les buts par équipe
        goals_by_team = defaultdict(list)
        for goal in self.goals:
            goals_by_team[goal.scoring_team].append(goal)
            
        # Créer TeamLeagueData
        for team_name, team_goals in goals_by_team.items():
            team = TeamLeagueData(team_name=team_name)
            team.players = players_by_team.get(team_name, [])
            
            # Volumes
            team.league_goals = len(team_goals)
            team.league_xG = sum(g.xG for g in team_goals)
            
            # Timing DNA
            for g in team_goals:
                period = g.timing_period
                team.goals_by_period[period] = team.goals_by_period.get(period, 0) + 1
                if g.half == "1H":
                    team.goals_1h += 1
                else:
                    team.goals_2h += 1
                    
            # Style DNA
            for g in team_goals:
                sit = g.situation
                team.goals_by_situation[sit] = team.goals_by_situation.get(sit, 0) + 1
                shot = g.shot_type
                team.goals_by_shot_type[shot] = team.goals_by_shot_type.get(shot, 0) + 1
                
            # Home/Away
            for g in team_goals:
                if g.home_away == "h":
                    team.goals_home += 1
                else:
                    team.goals_away += 1
                    
            # Enrichir avec context_dna
            if hasattr(self, 'context_dna') and team_name in self.context_dna:
                ctx = self.context_dna[team_name]
                if 'raw_statistics' in ctx:
                    raw = ctx['raw_statistics']
                    if 'timing' in raw:
                        team.timing_xg = raw['timing']
                    if 'gameState' in raw:
                        team.gamestate_xg = raw['gameState']
                if 'context_dna' in ctx:
                    if 'attackSpeed' in ctx['context_dna']:
                        team.attack_speed = ctx['context_dna']['attackSpeed']
                team.league = ctx.get('league', '')
                        
            self.teams[team_name] = team
            
        print(f"   ✅ {len(self.teams)} équipes agrégées")
        
    def _calculate_ratios(self) -> None:
        """Calcule les league_ratios pour tous les joueurs"""
        print("\n📊 Calcul des league_ratios...")
        
        enriched = 0
        cup_performers = []
        
        for key, player in self.players.items():
            # Enrichir depuis player_stats
            if key in self.player_stats_cache:
                cache = self.player_stats_cache[key]
                player.total_goals_all_comp = cache.get('total_goals', player.league_goals)
                player.timing_profile = cache.get('timing_profile', '')
                player.shot_quality = cache.get('shot_quality', '')
                player.home_away_profile = cache.get('home_away_profile', '')
                enriched += 1
            else:
                # Pas dans player_stats → assume ligue = total
                player.total_goals_all_comp = player.league_goals
                
            # Calculer ratio
            player.calculate_league_ratio()
            
            # Track cup performers (warning)
            if player.reliability_tag == "CUP_PERFORMER" and player.league_goals >= 2:
                cup_performers.append(player)
                
        print(f"   ✅ {enriched} joueurs enrichis avec player_stats")
        print(f"   ⚠️ {len(cup_performers)} CUP_PERFORMERS détectés (warning pour paris ligue)")
        
        if cup_performers[:5]:
            print("\n   🚫 TOP CUP PERFORMERS (éviter pour paris ligue):")
            for p in sorted(cup_performers, key=lambda x: x.total_goals_all_comp, reverse=True)[:5]:
                print(f"      {p.player_name} ({p.team}): {p.league_goals}G ligue / {p.total_goals_all_comp}G total = {p.league_ratio:.0%}")
                
    # ═══════════════════════════════════════════════════════════════════════════
    # GETTERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_team(self, team_name: str) -> Optional[TeamLeagueData]:
        """Récupère les données d'une équipe"""
        return self.teams.get(team_name)
        
    def get_player(self, player_name: str, team: str = None) -> Optional[PlayerLeagueProfile]:
        """Récupère un joueur"""
        if team:
            return self.players.get(f"{player_name}|{team}")
        # Chercher dans toutes les équipes
        for key, player in self.players.items():
            if player.player_name == player_name:
                return player
        return None
        
    def get_top_scorers_league(self, team_name: str = None, n: int = 10) -> List[PlayerLeagueProfile]:
        """Top buteurs EN LIGUE (fiable pour paris)"""
        if team_name:
            team = self.get_team(team_name)
            if not team:
                return []
            players = team.players
        else:
            players = list(self.players.values())
            
        return sorted(players, key=lambda p: p.league_goals, reverse=True)[:n]
        
    def get_reliable_scorers(self, team_name: str = None, min_goals: int = 3) -> List[PlayerLeagueProfile]:
        """Buteurs FIABLES pour paris ligue (exclut CUP_PERFORMERS)"""
        scorers = self.get_top_scorers_league(team_name, 50)
        return [p for p in scorers 
                if p.league_goals >= min_goals 
                and p.reliability_tag != "CUP_PERFORMER"]


# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    loader = AttackDataLoaderV2()
    loader.load_all()
    
    # Test Liverpool
    print("\n" + "=" * 80)
    print("🔴 TEST: LIVERPOOL")
    print("=" * 80)
    
    liverpool = loader.get_team('Liverpool')
    if liverpool:
        print(f"Buts LIGUE: {liverpool.league_goals}")
        print(f"xG LIGUE: {liverpool.league_xG:.2f}")
        print(f"1H/2H: {liverpool.goals_1h}/{liverpool.goals_2h}")
        print(f"Timing: {liverpool.goals_by_period}")
        
        print("\n📊 Top buteurs LIGUE Liverpool:")
        for p in loader.get_top_scorers_league('Liverpool', 5):
            print(f"  • {p.player_name}: {p.league_goals}G ligue ({p.reliability_tag})")
            if p.total_goals_all_comp != p.league_goals:
                print(f"    → {p.total_goals_all_comp}G total, ratio={p.league_ratio:.0%}")
                
    # Test Bayern
    print("\n" + "=" * 80)
    print("🔴 TEST: BAYERN MUNICH")
    print("=" * 80)
    
    bayern = loader.get_team('Bayern Munich')
    if bayern:
        print(f"Buts LIGUE: {bayern.league_goals}")
        for p in loader.get_top_scorers_league('Bayern Munich', 5):
            print(f"  • {p.player_name}: {p.league_goals}G ligue ({p.reliability_tag})")
            
    # Top buteurs fiables
    print("\n" + "=" * 80)
    print("✅ TOP 10 BUTEURS FIABLES POUR PARIS LIGUE")
    print("=" * 80)
    for p in loader.get_reliable_scorers(min_goals=5)[:10]:
        print(f"  {p.player_name} ({p.team}): {p.league_goals}G - {p.reliability_tag}")
