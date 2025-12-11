"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🎯 ATTACK DATA LOADER V1.0 - HEDGE FUND GRADE                               ║
║                                                                              ║
║  Charge et unifie TOUTES les données offensives:                             ║
║  • PostgreSQL: player_stats, scorer_intelligence                             ║
║  • JSON: teams_context_dna, all_goals_2025, players_impact_dna               ║
║                                                                              ║
║  Philosophie: "Une équipe = Un ADN offensif unique"                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict


DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

DATA_DIR = Path('/home/Mon_ps/data')


@dataclass
class PlayerOffensiveProfile:
    """Profil offensif d'un joueur"""
    player_id: str
    player_name: str
    team: str
    position: str
    
    # Volume
    goals: int = 0
    assists: int = 0
    npg: int = 0  # Non-penalty goals
    shots: int = 0
    
    # Efficacité
    xg: float = 0.0
    npxg: float = 0.0
    conversion_rate: float = 0.0
    shot_quality: str = ""  # ELITE_FINISHER, CLINICAL, WASTEFUL...
    xg_overperformance: float = 0.0  # goals - xG
    
    # Timing
    timing_profile: str = ""  # DIESEL_SCORER, EARLY_BIRD, BALANCED_TIMING
    goals_1h: int = 0
    goals_2h: int = 0
    goals_0_15: int = 0
    goals_16_30: int = 0
    goals_31_45: int = 0
    goals_46_60: int = 0
    goals_61_75: int = 0
    goals_76_90: int = 0
    clutch_pct: float = 0.0
    first_goal_pct: float = 0.0
    
    # Context
    home_away_profile: str = ""  # HOME_SPECIALIST, AWAY_SPECIALIST, BALANCED
    goals_home: int = 0
    goals_away: int = 0
    home_away_ratio: float = 1.0
    
    # Involvement
    xgchain: float = 0.0  # Implication dans les actions
    xgbuildup: float = 0.0  # Création de jeu
    key_passes: int = 0
    creativity_profile: str = ""
    
    # Playing time
    minutes: int = 0
    games: int = 0
    playing_time_profile: str = ""  # STARTER, SUPER_SUB, ROTATION
    minutes_per_game: float = 0.0
    
    # Penalties
    is_penalty_taker: bool = False
    penalty_goals: int = 0
    penalty_pct: float = 0.0
    
    # Form
    form_goals_l5: int = 0
    form_xg_l5: float = 0.0
    hot_streak: bool = False
    cold_streak: bool = False
    form_trend: str = ""
    
    # Dependency
    team_goal_share: float = 0.0  # % des buts de l'équipe


@dataclass  
class TeamOffensiveData:
    """Données offensives brutes d'une équipe"""
    team_name: str
    league: str
    
    # Aggregated from players
    players: List[PlayerOffensiveProfile] = field(default_factory=list)
    
    # From teams_context_dna
    timing_data: Dict = field(default_factory=dict)  # xG par période
    gamestate_data: Dict = field(default_factory=dict)  # Performance selon score
    attack_speed_data: Dict = field(default_factory=dict)  # Verticality
    formation_data: Dict = field(default_factory=dict)
    
    # From all_goals_2025
    goals_by_period: Dict = field(default_factory=dict)
    goals_by_situation: Dict = field(default_factory=dict)  # OpenPlay, Corner, Penalty...
    goals_by_shot_type: Dict = field(default_factory=dict)  # RightFoot, LeftFoot, Head...
    
    # Aggregated stats
    total_goals: int = 0
    total_xg: float = 0.0
    goals_per_90: float = 0.0
    xg_per_90: float = 0.0
    matches_played: int = 0


class AttackDataLoader:
    """
    Charge toutes les données offensives depuis PostgreSQL et JSON.
    """
    
    def __init__(self):
        self.players: Dict[str, PlayerOffensiveProfile] = {}
        self.teams: Dict[str, TeamOffensiveData] = {}
        self.goals_data: List[Dict] = []
        self.context_dna: Dict = {}
        
    def load_all(self) -> None:
        """Charge toutes les sources de données"""
        print("=" * 80)
        print("🎯 ATTACK DATA LOADER V1.0")
        print("=" * 80)
        
        self._load_player_stats()
        self._load_context_dna()
        self._load_goals_data()
        self._aggregate_team_data()
        
        print(f"\n✅ Chargement terminé:")
        print(f"   • {len(self.players)} joueurs")
        print(f"   • {len(self.teams)} équipes")
        print(f"   • {len(self.goals_data)} buts analysés")
        
    def _load_player_stats(self) -> None:
        """Charge les stats joueurs depuis PostgreSQL"""
        print("\n📊 Chargement player_stats...")
        
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT * FROM player_stats 
                WHERE season = '2025-2026' 
                AND goals >= 1
                ORDER BY goals DESC
            """)
            
            rows = cur.fetchall()
            
            for row in rows:
                player = PlayerOffensiveProfile(
                    player_id=str(row.get('player_id', '')),
                    player_name=row.get('player_name', ''),
                    team=row.get('team_name', ''),
                    position=row.get('position', ''),
                    
                    # Volume
                    goals=row.get('goals', 0) or 0,
                    assists=row.get('assists', 0) or 0,
                    npg=row.get('npg', 0) or 0,
                    shots=row.get('shots', 0) or 0,
                    
                    # Efficacité
                    xg=float(row.get('xg', 0) or 0),
                    npxg=float(row.get('npxg', 0) or 0),
                    conversion_rate=float(row.get('conversion_rate', 0) or 0),
                    shot_quality=row.get('shot_quality', '') or '',
                    xg_overperformance=float(row.get('goals_minus_xg', 0) or 0),
                    
                    # Timing
                    timing_profile=row.get('timing_profile', '') or '',
                    goals_1h=row.get('goals_1h', 0) or 0,
                    goals_2h=row.get('goals_2h', 0) or 0,
                    goals_0_15=row.get('goals_0_15', 0) or 0,
                    goals_16_30=row.get('goals_16_30', 0) or 0,
                    goals_31_45=row.get('goals_31_45', 0) or 0,
                    goals_46_60=row.get('goals_46_60', 0) or 0,
                    goals_61_75=row.get('goals_61_75', 0) or 0,
                    goals_76_90=row.get('goals_76_90', 0) or 0,
                    clutch_pct=float(row.get('clutch_pct', 0) or 0),
                    first_goal_pct=float(row.get('first_goal_pct', 0) or 0),
                    
                    # Context
                    home_away_profile=row.get('home_away_profile', '') or '',
                    goals_home=row.get('goals_home', 0) or 0,
                    goals_away=row.get('goals_away', 0) or 0,
                    home_away_ratio=float(row.get('home_away_ratio', 1.0) or 1.0),
                    
                    # Involvement
                    xgchain=float(row.get('xgchain', 0) or 0),
                    xgbuildup=float(row.get('xgbuildup', 0) or 0),
                    key_passes=row.get('key_passes', 0) or 0,
                    creativity_profile=row.get('creativity_profile', '') or '',
                    
                    # Playing time
                    minutes=row.get('minutes', 0) or 0,
                    games=row.get('games', 0) or 0,
                    playing_time_profile=row.get('playing_time_profile', '') or '',
                    minutes_per_game=float(row.get('minutes_per_game', 0) or 0),
                    
                    # Penalties
                    is_penalty_taker=row.get('is_penalty_taker', False) or False,
                    penalty_goals=row.get('penalty_goals', 0) or 0,
                    penalty_pct=float(row.get('penalty_pct', 0) or 0),
                    
                    # Form
                    form_goals_l5=row.get('form_goals_l5', 0) or 0,
                    form_xg_l5=float(row.get('form_xg_l5', 0) or 0),
                    hot_streak=row.get('hot_streak', False) or False,
                    cold_streak=row.get('cold_streak', False) or False,
                    form_trend=row.get('form_trend', '') or '',
                )
                
                key = f"{player.player_name}|{player.team}"
                self.players[key] = player
                
            cur.close()
            conn.close()
            
            print(f"   ✅ {len(self.players)} joueurs chargés")
            
        except Exception as e:
            print(f"   ❌ Erreur PostgreSQL: {e}")
            
    def _load_context_dna(self) -> None:
        """Charge teams_context_dna.json"""
        print("\n📊 Chargement teams_context_dna...")
        
        path = DATA_DIR / 'quantum_v2/teams_context_dna.json'
        if path.exists():
            with open(path, 'r') as f:
                self.context_dna = json.load(f)
            print(f"   ✅ {len(self.context_dna)} équipes chargées")
        else:
            print(f"   ⚠️ Fichier non trouvé: {path}")
            
    def _load_goals_data(self) -> None:
        """Charge all_goals_2025.json"""
        print("\n📊 Chargement all_goals_2025...")
        
        path = DATA_DIR / 'goal_analysis/all_goals_2025.json'
        if path.exists():
            with open(path, 'r') as f:
                self.goals_data = json.load(f)
            print(f"   ✅ {len(self.goals_data)} buts chargés")
        else:
            print(f"   ⚠️ Fichier non trouvé: {path}")
            
    def _aggregate_team_data(self) -> None:
        """Agrège les données par équipe"""
        print("\n📊 Agrégation par équipe...")
        
        # Grouper les joueurs par équipe
        players_by_team = defaultdict(list)
        for player in self.players.values():
            players_by_team[player.team].append(player)
            
        # Grouper les buts par équipe
        goals_by_team = defaultdict(list)
        for goal in self.goals_data:
            team = goal.get('scoring_team', '')
            if team:
                goals_by_team[team].append(goal)
                
        # Créer TeamOffensiveData pour chaque équipe
        all_teams = set(players_by_team.keys()) | set(goals_by_team.keys()) | set(self.context_dna.keys())
        
        for team_name in all_teams:
            # Déterminer la ligue
            league = "Unknown"
            if team_name in self.context_dna:
                league = self.context_dna[team_name].get('league', 'Unknown')
            elif players_by_team[team_name]:
                # Prendre la ligue du premier joueur
                first_player = players_by_team[team_name][0]
                league = getattr(first_player, 'league', 'Unknown') if hasattr(first_player, 'league') else 'Unknown'
                
            team_data = TeamOffensiveData(
                team_name=team_name,
                league=league,
                players=players_by_team.get(team_name, []),
            )
            
            # Ajouter context_dna
            if team_name in self.context_dna:
                ctx = self.context_dna[team_name]
                
                # Raw statistics timing
                if 'raw_statistics' in ctx and 'timing' in ctx['raw_statistics']:
                    team_data.timing_data = ctx['raw_statistics']['timing']
                    
                # Context DNA
                if 'context_dna' in ctx:
                    team_data.gamestate_data = ctx['context_dna'].get('gameState', {})
                    team_data.attack_speed_data = ctx['context_dna'].get('attackSpeed', {})
                    team_data.formation_data = ctx['context_dna'].get('formation', {})

                # ====== FIX: Récupérer matches et xG depuis context_dna ======
                team_data.matches_played = ctx.get('matches', 0)
                if 'history' in ctx:
                    team_data.total_xg = ctx['history'].get('xg', 0.0)
                    team_data.xg_per_90 = ctx['history'].get('xg_90', 0.0)
                if 'record' in ctx:
                    team_data.goals_per_90 = ctx['record'].get('goals_for', 0) / max(ctx.get('matches', 1), 1)

            # Agréger les buts
            team_goals = goals_by_team.get(team_name, [])
            team_data.total_goals = len(team_goals)
            
            # Buts par période
            for goal in team_goals:
                period = goal.get('timing_period', '')
                situation = goal.get('situation', '')
                shot_type = goal.get('shot_type', '')
                xg = float(goal.get('xG', 0) or 0)
                
                team_data.total_xg += xg
                
                if period:
                    team_data.goals_by_period[period] = team_data.goals_by_period.get(period, 0) + 1
                if situation:
                    team_data.goals_by_situation[situation] = team_data.goals_by_situation.get(situation, 0) + 1
                if shot_type:
                    team_data.goals_by_shot_type[shot_type] = team_data.goals_by_shot_type.get(shot_type, 0) + 1
                    
            self.teams[team_name] = team_data
            
        print(f"   ✅ {len(self.teams)} équipes agrégées")
        
    def get_team(self, team_name: str) -> Optional[TeamOffensiveData]:
        """Récupère les données d'une équipe"""
        return self.teams.get(team_name)
        
    def get_team_players(self, team_name: str) -> List[PlayerOffensiveProfile]:
        """Récupère les joueurs d'une équipe"""
        team = self.teams.get(team_name)
        return team.players if team else []
        
    def get_top_scorers(self, team_name: str, n: int = 5) -> List[PlayerOffensiveProfile]:
        """Récupère les meilleurs buteurs d'une équipe"""
        players = self.get_team_players(team_name)
        return sorted(players, key=lambda p: p.goals, reverse=True)[:n]


# Test
if __name__ == '__main__':
    loader = AttackDataLoader()
    loader.load_all()
    
    # Test avec Liverpool
    print("\n" + "=" * 80)
    print("🔴 TEST: LIVERPOOL")
    print("=" * 80)
    
    liverpool = loader.get_team('Liverpool')
    if liverpool:
        print(f"\nÉquipe: {liverpool.team_name}")
        print(f"Ligue: {liverpool.league}")
        print(f"Joueurs: {len(liverpool.players)}")
        print(f"Buts totaux: {liverpool.total_goals}")
        print(f"xG total: {liverpool.total_xg:.2f}")
        
        print(f"\nButs par période: {liverpool.goals_by_period}")
        print(f"Buts par situation: {liverpool.goals_by_situation}")
        
        print(f"\nTiming xG (Understat):")
        for period, data in liverpool.timing_data.items():
            print(f"  {period}: xG={data.get('xG', 0):.2f}, Goals={data.get('goals', 0)}")
            
        print(f"\nTop buteurs:")
        for p in loader.get_top_scorers('Liverpool', 5):
            print(f"  • {p.player_name}: {p.goals}G ({p.timing_profile}, {p.shot_quality})")
