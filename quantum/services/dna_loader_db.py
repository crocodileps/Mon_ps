"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                         DNA LOADER DB - SIMPLIFIED VERSION                            ║
║                                                                                       ║
║  Charge les vrais DNA depuis quantum.team_profiles et quantum.matchup_friction       ║
║  Retourne les données brutes sans conversion complexe                                 ║
║                                                                                       ║
║  Base: monps_db | User: monps_user | Host: localhost:5432                            ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass, field
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════════════
# DATABASE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class DBConfig:
    """Configuration PostgreSQL"""
    host: str = "localhost"
    port: int = 5432
    database: str = "monps_db"
    user: str = "monps_user"
    password: str = "monps_secure_password_2024"
    
    @classmethod
    def from_env(cls) -> 'DBConfig':
        """Charge la config depuis les variables d'environnement"""
        return cls(
            host=os.environ.get('POSTGRES_HOST', 'localhost'),
            port=int(os.environ.get('POSTGRES_PORT', 5432)),
            database=os.environ.get('POSTGRES_DB', 'monps_db'),
            user=os.environ.get('POSTGRES_USER', 'monps_user'),
            password=os.environ.get('POSTGRES_PASSWORD', 'monps_secure_password_2024')
        )


# ═══════════════════════════════════════════════════════════════════════════════════════
# SIMPLE TEAM DATA
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class SimpleTeamDNA:
    """Version simplifiée du DNA d'équipe pour le Rule Engine"""
    team_id: int
    team_name: str
    league: str
    tier: str
    
    # Context
    home_strength: float = 50.0
    away_strength: float = 50.0
    btts_tendency: float = 50.0
    goals_tendency: float = 50.0
    
    # Current Season
    xg_for_avg: float = 1.2
    xg_against_avg: float = 1.2
    goals_for: int = 0
    goals_against: int = 0
    matches_played: int = 0
    wins: int = 0
    points: int = 0
    ppg: float = 0.0
    
    # Psyche
    killer_instinct: float = 0.5
    panic_factor: float = 0.5
    comeback_mentality: float = 1.0
    lead_protection: float = 1.0
    
    # Temporal
    diesel_factor: float = 0.5
    fast_starter: float = 0.1
    first_half_xg_pct: float = 50.0
    goals_0_15: int = 0
    goals_76_90: int = 0
    
    # Nemesis/Tactical
    verticality: float = 5.0
    pressing_intensity: float = 10.0
    formation: str = "4-3-3"
    set_piece_threat: float = 10.0
    territorial_dominance: float = 0.5
    
    # Roster
    mvp_name: str = "Unknown"
    mvp_dependency: float = 30.0
    top3_dependency: float = 30.0
    
    # Physical
    stamina_profile: str = "MEDIUM"
    late_game_dominance: float = 30.0
    
    # Market
    best_strategy: str = "UNKNOWN"
    avg_edge: float = 0.0
    roi: float = 0.0
    
    # Luck
    luck_profile: str = "NEUTRAL"
    total_luck: float = 0.0
    
    # Raw data for advanced features
    quantum_dna: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class SimpleFriction:
    """Version simplifiée de la friction entre équipes"""
    team_a_name: str
    team_b_name: str
    friction_score: float = 50.0
    style_clash_score: float = 50.0
    tempo_clash_score: float = 50.0
    mental_clash_score: float = 50.0
    predicted_goals: float = 2.5
    predicted_btts_prob: float = 0.5
    predicted_over25_prob: float = 0.5
    chaos_potential: float = 50.0
    h2h_matches: int = 0
    h2h_avg_goals: float = 2.5


# ═══════════════════════════════════════════════════════════════════════════════════════
# DNA LOADER DATABASE
# ═══════════════════════════════════════════════════════════════════════════════════════

class DNALoaderDB:
    """
    Charge les DNA depuis PostgreSQL quantum.team_profiles.
    """
    
    def __init__(self, config: Optional[DBConfig] = None):
        self.config = config or DBConfig()
        self._connection = None
        self._team_cache: Dict[str, Dict] = {}
        self._friction_cache: Dict[str, Dict] = {}
        
    def _get_connection(self):
        """Obtient une connexion à la base"""
        if self._connection is None or self._connection.closed:
            self._connection = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password
            )
        return self._connection
    
    def _normalize_team_name(self, name: str) -> str:
        """Normalise le nom d'équipe pour la recherche"""
        return name.strip().lower().replace('-', ' ').replace('_', ' ')
    
    def load_team_profile_raw(self, team_name: str) -> Optional[Dict]:
        """Charge le profil complet brut d'une équipe depuis la DB"""
        normalized = self._normalize_team_name(team_name)
        
        if normalized in self._team_cache:
            return self._team_cache[normalized]
        
        conn = self._get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cur.execute("""
                SELECT * FROM quantum.team_profiles 
                WHERE LOWER(team_name) = %s 
                   OR LOWER(team_name_normalized) = %s
                LIMIT 1
            """, (normalized, normalized))
            
            row = cur.fetchone()
            
            if not row:
                cur.execute("""
                    SELECT * FROM quantum.team_profiles 
                    WHERE LOWER(team_name) LIKE %s 
                       OR LOWER(team_name_normalized) LIKE %s
                    LIMIT 1
                """, (f'%{normalized}%', f'%{normalized}%'))
                row = cur.fetchone()
            
            if row:
                profile = dict(row)
                self._team_cache[normalized] = profile
                return profile
            
            logger.warning(f"Team not found in DB: {team_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error loading team profile: {e}")
            return None
        finally:
            cur.close()
    
    def load_team_dna(self, team_name: str) -> Optional[SimpleTeamDNA]:
        """Charge et convertit en SimpleTeamDNA"""
        profile = self.load_team_profile_raw(team_name)
        if not profile:
            return None
        
        return self._convert_to_simple_dna(profile)
    
    def _convert_to_simple_dna(self, profile: Dict) -> SimpleTeamDNA:
        """Convertit un profil DB en SimpleTeamDNA"""
        qd = profile.get('quantum_dna', {}) or {}
        
        context = qd.get('context_dna', {})
        current = qd.get('current_season', {})
        psyche = qd.get('psyche_dna', {})
        temporal = qd.get('temporal_dna', {})
        nemesis = qd.get('nemesis_dna', {})
        tactical = qd.get('tactical_dna', {})
        physical = qd.get('physical_dna', {})
        roster = qd.get('roster_dna', {})
        market = qd.get('market_dna', {})
        luck = qd.get('luck_dna', {})
        
        periods = temporal.get('periods', {})
        empirical = market.get('empirical_profile', {})
        mvp = roster.get('mvp', {})
        
        return SimpleTeamDNA(
            team_id=profile.get('id', 0),
            team_name=profile['team_name'],
            league=qd.get('league', 'Unknown'),
            tier=profile.get('tier', 'SILVER'),
            home_strength=context.get('home_strength', 50),
            away_strength=context.get('away_strength', 50),
            btts_tendency=context.get('btts_tendency', 50),
            goals_tendency=context.get('goals_tendency', 50),
            xg_for_avg=current.get('xg_for_avg', 1.2),
            xg_against_avg=current.get('xg_against_avg', 1.2),
            goals_for=current.get('goals_for', 0),
            goals_against=current.get('goals_against', 0),
            matches_played=current.get('matches_played', 0),
            wins=current.get('wins', 0),
            points=current.get('points', 0),
            ppg=current.get('ppg', 0),
            killer_instinct=psyche.get('killer_instinct', 0.5),
            panic_factor=psyche.get('panic_factor', 0.5),
            comeback_mentality=psyche.get('comeback_mentality', 1.0),
            lead_protection=psyche.get('lead_protection', 1.0),
            diesel_factor=temporal.get('diesel_factor', 0.5),
            fast_starter=temporal.get('fast_starter', 0.1),
            first_half_xg_pct=temporal.get('first_half_xg_pct', 50),
            goals_0_15=periods.get('1-15', {}).get('goals', 0),
            goals_76_90=periods.get('76+', {}).get('goals', 0),
            verticality=nemesis.get('verticality', 5),
            pressing_intensity=physical.get('pressing_intensity', 10),
            formation=tactical.get('main_formation', '4-3-3'),
            set_piece_threat=tactical.get('set_piece_threat', 10),
            territorial_dominance=nemesis.get('territorial_dominance', 0.5),
            mvp_name=mvp.get('name', 'Unknown'),
            mvp_dependency=mvp.get('dependency_score', 30),
            top3_dependency=roster.get('top3_dependency', 30),
            stamina_profile=physical.get('stamina_profile', 'MEDIUM'),
            late_game_dominance=physical.get('late_game_dominance', 30),
            best_strategy=market.get('best_strategy', 'UNKNOWN'),
            avg_edge=empirical.get('avg_edge', 0),
            roi=profile.get('roi', 0) or 0,
            luck_profile=luck.get('luck_profile', 'NEUTRAL'),
            total_luck=luck.get('total_luck', 0),
            quantum_dna=qd
        )
    
    def load_friction(self, home_team: str, away_team: str) -> Optional[SimpleFriction]:
        """Charge la friction entre deux équipes"""
        conn = self._get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        home_norm = self._normalize_team_name(home_team)
        away_norm = self._normalize_team_name(away_team)
        
        cache_key = f"{home_norm}_{away_norm}"
        if cache_key in self._friction_cache:
            return self._convert_to_simple_friction(self._friction_cache[cache_key])
        
        try:
            cur.execute("""
                SELECT * FROM quantum.matchup_friction 
                WHERE (LOWER(team_a_name) LIKE %s AND LOWER(team_b_name) LIKE %s)
                   OR (LOWER(team_a_name) LIKE %s AND LOWER(team_b_name) LIKE %s)
                LIMIT 1
            """, (f'%{home_norm}%', f'%{away_norm}%', f'%{away_norm}%', f'%{home_norm}%'))
            
            row = cur.fetchone()
            
            if row:
                friction = dict(row)
                self._friction_cache[cache_key] = friction
                return self._convert_to_simple_friction(friction)
            
            logger.warning(f"Friction not found: {home_team} vs {away_team}")
            return None
            
        except Exception as e:
            logger.error(f"Error loading friction: {e}")
            return None
        finally:
            cur.close()
    
    def _convert_to_simple_friction(self, data: Dict) -> SimpleFriction:
        """Convertit les données friction en SimpleFriction"""
        return SimpleFriction(
            team_a_name=data.get('team_a_name', ''),
            team_b_name=data.get('team_b_name', ''),
            friction_score=data.get('friction_score', 50) or 50,
            style_clash_score=data.get('style_clash_score', 50) or 50,
            tempo_clash_score=data.get('tempo_clash_score', 50) or 50,
            mental_clash_score=data.get('mental_clash_score', 50) or 50,
            predicted_goals=data.get('predicted_goals', 2.5) or 2.5,
            predicted_btts_prob=data.get('predicted_btts_prob', 0.5) or 0.5,
            predicted_over25_prob=data.get('predicted_over25_prob', 0.5) or 0.5,
            chaos_potential=data.get('chaos_potential', 50) or 50,
            h2h_matches=data.get('h2h_matches', 0) or 0,
            h2h_avg_goals=data.get('h2h_avg_goals', 2.5) or 2.5,
        )
    
    def load_match_data(self, home_team: str, away_team: str) -> Tuple[Optional[SimpleTeamDNA], Optional[SimpleTeamDNA], Optional[SimpleFriction]]:
        """Charge toutes les données pour un match"""
        home_dna = self.load_team_dna(home_team)
        away_dna = self.load_team_dna(away_team)
        friction = self.load_friction(home_team, away_team)
        return home_dna, away_dna, friction
    
    def get_all_teams(self) -> List[str]:
        """Retourne la liste de toutes les équipes"""
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT team_name FROM quantum.team_profiles ORDER BY team_name")
            return [row[0] for row in cur.fetchall()]
        finally:
            cur.close()
    
    def get_teams_by_league(self, league: str) -> List[str]:
        """Retourne les équipes d'une ligue"""
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT team_name FROM quantum.team_profiles 
                WHERE quantum_dna->>'league' = %s
                ORDER BY team_name
            """, (league,))
            return [row[0] for row in cur.fetchall()]
        finally:
            cur.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de la base"""
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            stats = {}
            cur.execute("SELECT COUNT(*) FROM quantum.team_profiles")
            stats['total_teams'] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM quantum.matchup_friction")
            stats['total_frictions'] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(DISTINCT quantum_dna->>'league') FROM quantum.team_profiles")
            stats['total_leagues'] = cur.fetchone()[0]
            cur.execute("SELECT tier, COUNT(*) FROM quantum.team_profiles GROUP BY tier ORDER BY COUNT(*) DESC")
            stats['tiers'] = dict(cur.fetchall())
            return stats
        finally:
            cur.close()
    
    def close(self):
        """Ferme la connexion"""
        if self._connection and not self._connection.closed:
            self._connection.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Convenience functions
_loader_instance: Optional[DNALoaderDB] = None

def get_loader() -> DNALoaderDB:
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = DNALoaderDB()
    return _loader_instance

def load_team(team_name: str) -> Optional[SimpleTeamDNA]:
    return get_loader().load_team_dna(team_name)

def load_match(home: str, away: str) -> Tuple[Optional[SimpleTeamDNA], Optional[SimpleTeamDNA], Optional[SimpleFriction]]:
    return get_loader().load_match_data(home, away)

def get_all_teams() -> List[str]:
    return get_loader().get_all_teams()
