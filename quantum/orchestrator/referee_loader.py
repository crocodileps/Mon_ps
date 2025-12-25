#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════════════
REFEREE LOADER - CHARGEMENT DONNÉES ARBITRE HEDGE FUND GRADE
═══════════════════════════════════════════════════════════════════════════════════════

Fichier: quantum/orchestrator/referee_loader.py
Version: 1.0.0
Date: 2025-12-25

SOURCES DE DONNÉES:
1. PostgreSQL: referee_intelligence (24 colonnes)
2. PostgreSQL: referee_stats (16 colonnes)  
3. PostgreSQL: v_referees_over_under (vue pour Over/Under)
4. JSON: referee_dna_unified.json (données enrichies Hedge Fund Grade)

USAGE:
    loader = RefereeLoader(db_pool)
    referee = await loader.load_referee("Michael Oliver")
    
    # Ou depuis JSON
    referee = loader.load_referee_from_json("M Oliver")

POUR DISCIPLINARY FRICTION:
    destruction_score = calculate_rhythm_destruction(
        home_pressing=75.0,
        away_pressing=68.0,
        referee=referee,
        is_derby=True
    )
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import json
import logging
from pathlib import Path

# Import config
try:
    from quantum.config.friction_config import (
        FRICTION_CONFIG,
        get_disciplinary_config,
        normalize_to_100,
    )
except ImportError:
    from friction_config import (
        FRICTION_CONFIG,
        get_disciplinary_config,
        normalize_to_100,
    )

# Logger
logger = logging.getLogger("QuantumOrchestrator.Referee")


# ═══════════════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════════════

def safe_float(value: Any, default: float = 0.0) -> float:
    """Convertit en float de manière sécurisée."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Convertit en int de manière sécurisée."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def normalize_referee_name(name: str) -> str:
    """
    Normalise le nom d'un arbitre pour la recherche.
    Ex: "Michael Oliver" → "m oliver", "M Oliver" → "m oliver"
    """
    if not name:
        return ""
    # Lowercase et strip
    normalized = name.lower().strip()
    # Remplacer les points (M. Oliver → m oliver)
    normalized = normalized.replace(".", " ")
    # Supprimer les doubles espaces
    while "  " in normalized:
        normalized = normalized.replace("  ", " ")
    return normalized.strip()


# ═══════════════════════════════════════════════════════════════════════════════════════
# REFEREE DNA - DATACLASS PRINCIPALE
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class TeamInteraction:
    """Interaction historique entre un arbitre et une équipe."""
    team: str
    matches: int = 0
    avg_yellows: float = 0.0
    avg_reds: float = 0.0
    avg_cards: float = 0.0
    avg_fouls: float = 0.0
    total_reds: int = 0
    win_rate: float = 0.0
    card_diff: float = 0.0  # Différence vs moyenne de l'arbitre


@dataclass
class RefereeDNA:
    """
    DNA complète d'un arbitre - Hedge Fund Grade.
    
    Consolidation des données de:
    - referee_intelligence (PostgreSQL)
    - referee_stats (PostgreSQL)
    - referee_dna_unified.json
    
    Attributes:
        name: Nom canonique de l'arbitre
        normalized_name: Nom normalisé pour recherche
        
        # Core Stats
        matches: Nombre de matchs arbitrés
        leagues: Ligues où il arbitre
        seasons: Nombre de saisons
        
        # Cards
        avg_cards: Moyenne de cartons par match
        avg_yellows: Moyenne de jaunes par match
        avg_reds: Moyenne de rouges par match
        card_impact: Impact sur les cartons vs moyenne (+/-)
        
        # Fouls
        avg_fouls: Moyenne de fautes par match
        card_per_foul: Ratio cartons/fautes (CRUCIAL pour destruction_score!)
        
        # Goals
        avg_goals: Moyenne de buts par match
        under_over_tendency: "over", "under", "neutral"
        
        # Profile
        strictness_level: 1-10 (10 = très strict)
        style: "LAISSE_JOUER", "TRIGGER_HAPPY", "NEUTRAL"
        profile: "LENIENT", "NEUTRAL", "STRICT"
        volatility: Variance dans les décisions
        home_bias: Biais vers l'équipe à domicile
        
        # Catalyst (pour trading)
        penalty_frequency: Fréquence de penaltys
        match_flow_score: Impact sur le rythme du match
        second_half_intensity: Plus de cartons en 2H?
        high_stakes_factor: Comportement en gros matchs
        
        # Thresholds (pour Over/Under cards)
        over_35_cards_pct: % matchs avec +3.5 cartons
        over_45_cards_pct: % matchs avec +4.5 cartons
        over_55_cards_pct: % matchs avec +5.5 cartons
        
        # Team Interactions
        nemesis_teams: Équipes qui prennent plus de cartons avec lui
        favored_teams: Équipes qui en prennent moins
        team_interactions: Détail des interactions équipe×arbitre
        
        # Metadata
        quality_score: Score de qualité des données (1-5)
        quality_tier: "hedge_fund_grade", "standard", "low"
        sources: Liste des sources utilisées
    """
    
    # === IDENTITÉ ===
    name: str
    normalized_name: str = ""
    
    # === CORE STATS ===
    matches: int = 0
    leagues: List[str] = field(default_factory=list)
    seasons: int = 0
    
    # === CARDS ===
    avg_cards: float = 3.5
    avg_yellows: float = 3.5
    avg_reds: float = 0.1
    card_impact: float = 0.0  # + = plus de cartons que moyenne
    
    # === FOULS ===
    avg_fouls: float = 20.0
    card_per_foul: float = 15.0  # CRUCIAL: fautes pour 1 carton
    
    # === GOALS ===
    avg_goals: float = 2.7
    under_over_tendency: str = "neutral"  # "over", "under", "neutral"
    
    # === PROFILE ===
    strictness_level: int = 5  # 1-10
    style: str = "NEUTRAL"  # "LAISSE_JOUER", "TRIGGER_HAPPY", "NEUTRAL"
    profile: str = "NEUTRAL"  # "LENIENT", "NEUTRAL", "STRICT"
    volatility: float = 2.0  # Variance
    home_bias: float = 0.0  # + = favorise home
    
    # === CATALYST ===
    penalty_frequency: float = 20.0  # % matchs avec penalty
    match_flow_score: float = 30.0  # Impact sur le rythme
    second_half_intensity: float = 1.0  # Ratio 2H/1H cartons
    high_stakes_factor: float = 1.0  # Comportement big games
    card_trigger_rate: float = 15.0  # Fautes avant de sortir carton
    
    # === THRESHOLDS ===
    over_35_cards_pct: float = 40.0  # % matchs +3.5 cartons
    over_45_cards_pct: float = 25.0  # % matchs +4.5 cartons
    over_55_cards_pct: float = 10.0  # % matchs +5.5 cartons
    
    # === TEAM INTERACTIONS ===
    nemesis_teams: List[Dict[str, Any]] = field(default_factory=list)
    favored_teams: List[Dict[str, Any]] = field(default_factory=list)
    team_interactions: List[TeamInteraction] = field(default_factory=list)
    
    # === METADATA ===
    quality_score: float = 3.0
    quality_tier: str = "standard"
    sources: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Normalise le nom après création."""
        if not self.normalized_name:
            self.normalized_name = normalize_referee_name(self.name)
        
        # Déduire le style depuis strictness si non défini
        if self.style == "NEUTRAL" and self.strictness_level:
            if self.strictness_level <= 4:
                self.style = "LAISSE_JOUER"
            elif self.strictness_level >= 7:
                self.style = "TRIGGER_HAPPY"
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # PROPRIÉTÉS CALCULÉES
    # ═══════════════════════════════════════════════════════════════════════════════
    
    @property
    def strictness_normalized(self) -> float:
        """Strictness normalisé sur 0-100."""
        return (self.strictness_level / 10.0) * 100.0
    
    @property
    def is_strict(self) -> bool:
        """Est-ce un arbitre strict ?"""
        return self.strictness_level >= 7 or self.profile == "STRICT"
    
    @property
    def is_lenient(self) -> bool:
        """Est-ce un arbitre permissif ?"""
        return self.strictness_level <= 4 or self.profile == "LENIENT"
    
    @property
    def favors_over_goals(self) -> bool:
        """Favorise-t-il les Over goals ?"""
        return self.under_over_tendency == "over" or self.avg_goals > 2.8
    
    @property
    def card_strictness_ratio(self) -> float:
        """
        Ratio de sévérité cartons vs moyenne league (15.0).
        > 1.0 = plus strict, < 1.0 = plus permissif
        """
        avg_league = 15.0  # card_per_foul moyen
        if self.card_per_foul <= 0:
            return 1.0
        # Inversé: moins de fautes par carton = plus strict
        return avg_league / self.card_per_foul
    
    def get_team_interaction(self, team_name: str) -> Optional[TeamInteraction]:
        """Récupère l'interaction avec une équipe spécifique."""
        normalized_team = team_name.lower().strip()
        for interaction in self.team_interactions:
            if interaction.team.lower().strip() == normalized_team:
                return interaction
        return None
    
    def has_history_with(self, team_name: str) -> bool:
        """Vérifie si l'arbitre a un historique avec cette équipe."""
        return self.get_team_interaction(team_name) is not None
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # SERIALIZATION
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire."""
        return {
            "name": self.name,
            "normalized_name": self.normalized_name,
            "matches": self.matches,
            "leagues": self.leagues,
            "seasons": self.seasons,
            "avg_cards": self.avg_cards,
            "avg_yellows": self.avg_yellows,
            "avg_reds": self.avg_reds,
            "card_impact": self.card_impact,
            "avg_fouls": self.avg_fouls,
            "card_per_foul": self.card_per_foul,
            "avg_goals": self.avg_goals,
            "under_over_tendency": self.under_over_tendency,
            "strictness_level": self.strictness_level,
            "style": self.style,
            "profile": self.profile,
            "volatility": self.volatility,
            "home_bias": self.home_bias,
            "penalty_frequency": self.penalty_frequency,
            "match_flow_score": self.match_flow_score,
            "second_half_intensity": self.second_half_intensity,
            "over_35_cards_pct": self.over_35_cards_pct,
            "over_45_cards_pct": self.over_45_cards_pct,
            "quality_score": self.quality_score,
            "quality_tier": self.quality_tier,
            "is_strict": self.is_strict,
            "is_lenient": self.is_lenient,
            "card_strictness_ratio": self.card_strictness_ratio,
        }
    
    def summary(self) -> str:
        """Retourne un résumé lisible."""
        return (
            f"═══ REFEREE: {self.name} ═══\n"
            f"  Matches: {self.matches} | Leagues: {', '.join(self.leagues[:2])}\n"
            f"  Style: {self.style} | Profile: {self.profile}\n"
            f"  Strictness: {self.strictness_level}/10 | Volatility: {self.volatility:.2f}\n"
            f"  Avg Cards: {self.avg_cards:.2f} | Card/Foul: {self.card_per_foul:.1f}\n"
            f"  Avg Goals: {self.avg_goals:.2f} | Tendency: {self.under_over_tendency}\n"
            f"  Home Bias: {self.home_bias:+.2f} | Penalty Freq: {self.penalty_frequency:.0f}%\n"
            f"  Quality: {self.quality_tier} ({self.quality_score:.1f}/5)"
        )


# ═══════════════════════════════════════════════════════════════════════════════════════
# REFEREE LOADER - CHARGEMENT DEPUIS DB ET JSON
# ═══════════════════════════════════════════════════════════════════════════════════════

class RefereeLoader:
    """
    Charge les données arbitre depuis PostgreSQL et JSON.
    
    Usage:
        loader = RefereeLoader(db_pool)
        
        # Depuis DB
        referee = await loader.load_referee("Michael Oliver")
        
        # Depuis JSON
        referee = loader.load_referee_from_json("M Oliver")
        
        # Avec fallback automatique
        referee = await loader.load_referee_with_fallback("Michael Oliver")
    """
    
    # Chemin vers le JSON (configurable)
    JSON_PATH = Path("/home/Mon_ps/data/quantum_v2/referee_dna_unified.json")
    
    def __init__(self, db_pool=None, json_path: Optional[Path] = None):
        """
        Args:
            db_pool: Pool de connexions asyncpg ou psycopg2
            json_path: Chemin alternatif vers referee_dna_unified.json
        """
        self.pool = db_pool
        self.json_path = json_path or self.JSON_PATH
        self._json_cache: Optional[Dict] = None
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # CHARGEMENT DEPUIS JSON
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def _load_json_data(self) -> Dict:
        """Charge et cache le fichier JSON."""
        if self._json_cache is not None:
            return self._json_cache
        
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                self._json_cache = json.load(f)
            logger.info(f"✅ Chargé {len(self._json_cache)} arbitres depuis JSON")
        except FileNotFoundError:
            logger.warning(f"⚠️ JSON non trouvé: {self.json_path}")
            self._json_cache = {}
        except json.JSONDecodeError as e:
            logger.error(f"❌ Erreur JSON: {e}")
            self._json_cache = {}
        
        return self._json_cache
    
    def load_referee_from_json(self, referee_name: str) -> Optional[RefereeDNA]:
        """
        Charge un arbitre depuis referee_dna_unified.json.
        
        Args:
            referee_name: Nom de l'arbitre (ex: "M Oliver", "Michael Oliver")
        
        Returns:
            RefereeDNA ou None si non trouvé
        """
        data = self._load_json_data()
        
        if not data:
            return None
        
        # Recherche par nom exact
        if referee_name in data:
            return self._parse_json_referee(referee_name, data[referee_name])
        
        # Recherche par nom normalisé
        normalized = normalize_referee_name(referee_name)
        for key, ref_data in data.items():
            if normalize_referee_name(key) == normalized:
                return self._parse_json_referee(key, ref_data)
            # Vérifier aussi normalized_key dans meta
            meta = ref_data.get("meta", {})
            if meta.get("normalized_key") == normalized:
                return self._parse_json_referee(key, ref_data)
        
        logger.warning(f"⚠️ Arbitre non trouvé dans JSON: {referee_name}")
        return None
    
    def _parse_json_referee(self, name: str, data: Dict) -> RefereeDNA:
        """Parse les données JSON en RefereeDNA."""
        meta = data.get("meta", {})
        core = data.get("core", {})
        cards = data.get("cards", {})
        fouls = data.get("fouls", {})
        goals = data.get("goals", {})
        profile = data.get("profile", {})
        catalyst = data.get("catalyst", {})
        thresholds = data.get("thresholds", {})
        
        # Team interactions
        team_interactions = []
        for ti in data.get("team_interactions", []):
            team_interactions.append(TeamInteraction(
                team=ti.get("team", ""),
                matches=safe_int(ti.get("matches")),
                avg_yellows=safe_float(ti.get("avg_yellows")),
                avg_reds=safe_float(ti.get("avg_reds")),
                avg_cards=safe_float(ti.get("avg_cards")),
                avg_fouls=safe_float(ti.get("avg_fouls")),
                total_reds=safe_int(ti.get("total_reds")),
                win_rate=safe_float(ti.get("win_rate")),
                card_diff=safe_float(ti.get("card_diff")),
            ))
        
        return RefereeDNA(
            name=meta.get("canonical_name", name),
            normalized_name=meta.get("normalized_key", normalize_referee_name(name)),
            
            # Core
            matches=safe_int(core.get("matches")),
            leagues=core.get("leagues", []),
            seasons=safe_int(core.get("seasons")),
            
            # Cards
            avg_cards=safe_float(cards.get("avg_total", cards.get("per_match")), 3.5),
            avg_yellows=safe_float(cards.get("avg_yellows"), 3.5),
            avg_reds=safe_float(cards.get("avg_reds"), 0.1),
            card_impact=safe_float(cards.get("impact"), 0.0),
            
            # Fouls
            avg_fouls=safe_float(fouls.get("avg"), 20.0),
            card_per_foul=safe_float(fouls.get("card_per_foul"), 15.0),
            
            # Goals
            avg_goals=safe_float(goals.get("avg"), 2.7),
            
            # Profile
            volatility=safe_float(profile.get("volatility"), 2.0),
            home_bias=safe_float(profile.get("home_bias"), 0.0),
            profile=profile.get("type", "NEUTRAL"),
            
            # Catalyst
            # card_impact déjà défini plus haut
            penalty_frequency=safe_float(catalyst.get("penalty_impact", 0.0)) * 100,
            
            # Thresholds
            over_35_cards_pct=safe_float(thresholds.get("cards_over_35"), 40.0),
            over_45_cards_pct=safe_float(thresholds.get("cards_over_45"), 25.0),
            over_55_cards_pct=safe_float(thresholds.get("cards_over_55"), 10.0),
            
            # Team Interactions
            team_interactions=team_interactions,
            
            # Metadata
            quality_score=safe_float(meta.get("quality_score"), 3.0),
            quality_tier=meta.get("quality_tier", "standard"),
            sources=meta.get("sources", []),
        )
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # CHARGEMENT DEPUIS POSTGRESQL (ASYNC)
    # ═══════════════════════════════════════════════════════════════════════════════
    
    async def load_referee(self, referee_name: str) -> Optional[RefereeDNA]:
        """
        Charge un arbitre depuis PostgreSQL (referee_intelligence + referee_stats).
        
        Args:
            referee_name: Nom de l'arbitre
        
        Returns:
            RefereeDNA ou None si non trouvé
        """
        if not self.pool:
            logger.warning("⚠️ Pas de pool DB, fallback vers JSON")
            return self.load_referee_from_json(referee_name)
        
        # Query combinée referee_intelligence + referee_stats
        query = """
            SELECT 
                ri.referee_name,
                ri.league,
                ri.strictness_level,
                ri.avg_fouls_per_game,
                ri.avg_yellow_cards_per_game,
                ri.avg_red_cards_per_game,
                ri.penalty_frequency,
                ri.home_bias_factor,
                ri.under_over_tendency,
                ri.avg_goals_per_game,
                ri.avg_stoppage_time_added,
                ri.matches_officiated,
                ri.seasons_active,
                ri.big_game_experience,
                ri.notes,
                rs.avg_fouls as rs_avg_fouls,
                rs.over_3_5_cards_pct,
                rs.over_4_5_cards_pct,
                rs.card_impact as rs_card_impact,
                rs.card_per_foul,
                rs.volatility,
                rs.profile as rs_profile,
                rs.trigger_tag
            FROM referee_intelligence ri
            LEFT JOIN referee_stats rs 
                ON LOWER(ri.referee_name) = LOWER(rs.referee_name)
            WHERE LOWER(ri.referee_name) LIKE LOWER($1)
               OR LOWER(ri.referee_name) LIKE LOWER($2)
            LIMIT 1
        """
        
        # Patterns de recherche
        pattern1 = f"%{referee_name}%"
        pattern2 = f"%{normalize_referee_name(referee_name)}%"
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, pattern1, pattern2)
                
                if not row:
                    logger.warning(f"⚠️ Arbitre non trouvé en DB: {referee_name}")
                    return None
                
                return self._parse_db_referee(row)
                
        except Exception as e:
            logger.error(f"❌ Erreur DB referee: {e}")
            return None
    
    def _parse_db_referee(self, row) -> RefereeDNA:
        """Parse une row PostgreSQL en RefereeDNA."""
        # Déterminer le style depuis les données
        strictness = safe_int(row['strictness_level'], 5)
        style = "NEUTRAL"
        if strictness <= 4:
            style = "LAISSE_JOUER"
        elif strictness >= 7:
            style = "TRIGGER_HAPPY"
        
        # Déterminer le profile
        profile = row['rs_profile'] if row['rs_profile'] else "NEUTRAL"
        
        return RefereeDNA(
            name=row['referee_name'],
            matches=safe_int(row['matches_officiated']),
            leagues=[row['league']] if row['league'] else [],
            seasons=safe_int(row['seasons_active']),
            
            avg_cards=safe_float(row['avg_yellow_cards_per_game'], 3.5),
            avg_yellows=safe_float(row['avg_yellow_cards_per_game'], 3.5),
            avg_reds=safe_float(row['avg_red_cards_per_game'], 0.1),
            card_impact=safe_float(row['rs_card_impact'], 0.0),
            
            avg_fouls=safe_float(row['avg_fouls_per_game'] or row['rs_avg_fouls'], 20.0),
            card_per_foul=safe_float(row['card_per_foul'], 15.0),
            
            avg_goals=safe_float(row['avg_goals_per_game'], 2.7),
            under_over_tendency=row['under_over_tendency'] or "neutral",
            
            strictness_level=strictness,
            style=style,
            profile=profile,
            volatility=safe_float(row['volatility'], 2.0),
            home_bias=safe_float(row['home_bias_factor'], 0.0),
            
            penalty_frequency=safe_float(row['penalty_frequency'], 20.0),
            
            over_35_cards_pct=safe_float(row['over_3_5_cards_pct'], 40.0),
            over_45_cards_pct=safe_float(row['over_4_5_cards_pct'], 25.0),
            
            quality_tier="db_sourced",
            sources=["referee_intelligence", "referee_stats"],
        )
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # CHARGEMENT SYNCHRONE (pour psycopg2)
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def load_referee_sync(self, referee_name: str, cursor) -> Optional[RefereeDNA]:
        """
        Version synchrone pour psycopg2.
        
        Args:
            referee_name: Nom de l'arbitre
            cursor: Curseur psycopg2
        
        Returns:
            RefereeDNA ou None
        """
        query = """
            SELECT 
                ri.referee_name,
                ri.league,
                ri.strictness_level,
                ri.avg_fouls_per_game,
                ri.avg_yellow_cards_per_game,
                ri.avg_red_cards_per_game,
                ri.penalty_frequency,
                ri.home_bias_factor,
                ri.under_over_tendency,
                ri.avg_goals_per_game,
                ri.matches_officiated,
                ri.seasons_active,
                rs.over_3_5_cards_pct,
                rs.over_4_5_cards_pct,
                rs.card_impact as rs_card_impact,
                rs.card_per_foul,
                rs.volatility,
                rs.profile as rs_profile
            FROM referee_intelligence ri
            LEFT JOIN referee_stats rs 
                ON LOWER(ri.referee_name) = LOWER(rs.referee_name)
            WHERE LOWER(ri.referee_name) LIKE LOWER(%s)
               OR LOWER(ri.referee_name) LIKE LOWER(%s)
            LIMIT 1
        """
        
        pattern1 = f"%{referee_name}%"
        pattern2 = f"%{normalize_referee_name(referee_name)}%"
        
        try:
            cursor.execute(query, (pattern1, pattern2))
            row = cursor.fetchone()
            
            if not row:
                logger.warning(f"⚠️ Arbitre non trouvé: {referee_name}")
                return None
            
            # Row est un tuple, mapper par index
            strictness = safe_int(row[2], 5)
            style = "NEUTRAL"
            if strictness <= 4:
                style = "LAISSE_JOUER"
            elif strictness >= 7:
                style = "TRIGGER_HAPPY"
            
            return RefereeDNA(
                name=row[0],
                leagues=[row[1]] if row[1] else [],
                strictness_level=strictness,
                avg_fouls=safe_float(row[3], 20.0),
                avg_yellows=safe_float(row[4], 3.5),
                avg_cards=safe_float(row[4], 3.5),
                avg_reds=safe_float(row[5], 0.1),
                penalty_frequency=safe_float(row[6], 20.0),
                home_bias=safe_float(row[7], 0.0),
                under_over_tendency=row[8] or "neutral",
                avg_goals=safe_float(row[9], 2.7),
                matches=safe_int(row[10]),
                seasons=safe_int(row[11]),
                over_35_cards_pct=safe_float(row[12], 40.0),
                over_45_cards_pct=safe_float(row[13], 25.0),
                card_impact=safe_float(row[14], 0.0),
                card_per_foul=safe_float(row[15], 15.0),
                volatility=safe_float(row[16], 2.0),
                profile=row[17] or "NEUTRAL",
                style=style,
                quality_tier="db_sourced",
                sources=["referee_intelligence", "referee_stats"],
            )
            
        except Exception as e:
            logger.error(f"❌ Erreur sync referee: {e}")
            return None
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # CHARGEMENT AVEC FALLBACK
    # ═══════════════════════════════════════════════════════════════════════════════
    
    async def load_referee_with_fallback(self, referee_name: str) -> RefereeDNA:
        """
        Charge un arbitre avec fallback: DB → JSON → Default.
        
        Args:
            referee_name: Nom de l'arbitre
        
        Returns:
            RefereeDNA (toujours, avec valeurs par défaut si non trouvé)
        """
        # Essayer DB d'abord
        if self.pool:
            referee = await self.load_referee(referee_name)
            if referee:
                return referee
        
        # Fallback vers JSON
        referee = self.load_referee_from_json(referee_name)
        if referee:
            return referee
        
        # Retourner un arbitre par défaut
        logger.warning(f"⚠️ Arbitre inconnu, utilisation valeurs par défaut: {referee_name}")
        return RefereeDNA(
            name=referee_name,
            quality_tier="default",
            sources=["default"],
        )
    
    def load_referee_with_fallback_sync(self, referee_name: str, cursor=None) -> RefereeDNA:
        """Version synchrone du fallback."""
        # Essayer DB d'abord
        if cursor:
            referee = self.load_referee_sync(referee_name, cursor)
            if referee:
                return referee
        
        # Fallback vers JSON
        referee = self.load_referee_from_json(referee_name)
        if referee:
            return referee
        
        # Retourner un arbitre par défaut
        logger.warning(f"⚠️ Arbitre inconnu: {referee_name}")
        return RefereeDNA(
            name=referee_name,
            quality_tier="default",
            sources=["default"],
        )


# ═══════════════════════════════════════════════════════════════════════════════════════
# DISCIPLINARY FRICTION CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class DisciplinaryResult:
    """Résultat du calcul de Disciplinary Friction."""
    destruction_score: float
    rhythm_status: str  # "BROKEN", "DISRUPTED", "FLUID"
    expected_cards: float
    expected_fouls: float
    
    # Trading Signals
    back_under_goals: bool = False
    back_over_cards: bool = False
    sell_early_goal: bool = False
    
    # Confidence
    signal_confidence: int = 50


def calculate_rhythm_destruction(
    home_pressing: float,
    away_pressing: float,
    referee: RefereeDNA,
    is_derby: bool = False,
    rivalry_intensity: float = 0.0,
) -> DisciplinaryResult:
    """
    Calcule le Rhythm Destruction Score (Alpha #1).
    
    Formule:
        destruction_score = (contact_density / 50) × ref_strictness × rivalry_mult
    
    Args:
        home_pressing: pressing_intensity de l'équipe home (échelle 0-100)
        away_pressing: pressing_intensity de l'équipe away (échelle 0-100)
        referee: RefereeDNA
        is_derby: Est-ce un derby?
        rivalry_intensity: Intensité de la rivalité (0-100)
    
    Returns:
        DisciplinaryResult avec destruction_score et trading signals
    """
    config = get_disciplinary_config()
    
    # 1. Contact Density (moyenne des deux pressings)
    contact_density = (home_pressing + away_pressing) / 2.0
    
    # 2. Referee Strictness Ratio
    # Plus le card_per_foul est bas, plus l'arbitre est strict
    avg_league_cpf = config.get("avg_league_card_per_foul", 15.0)
    ref_strictness = avg_league_cpf / max(referee.card_per_foul, 1.0)
    
    # 3. Rivalry/Derby Multiplier
    rivalry_multiplier = 1.0
    if is_derby:
        rivalry_multiplier = config.get("derby_multiplier", 1.30)
    elif rivalry_intensity > config.get("rivalry_base_threshold", 50.0):
        scale = config.get("rivalry_multiplier_scale", 100.0)
        rivalry_multiplier = 1.0 + (rivalry_intensity - 50) / scale
    
    # 4. Destruction Score
    divisor = config.get("contact_density_divisor", 50.0)
    destruction_score = (contact_density / divisor) * ref_strictness * rivalry_multiplier
    
    # 5. Déterminer le status
    broken_threshold = config.get("broken_rhythm_threshold", 1.4)
    high_cards_threshold = config.get("high_cards_threshold", 1.2)
    
    if destruction_score > broken_threshold:
        rhythm_status = "BROKEN"
    elif destruction_score > high_cards_threshold:
        rhythm_status = "DISRUPTED"
    else:
        rhythm_status = "FLUID"
    
    # 6. Prédictions
    expected_cards = destruction_score * referee.avg_cards
    expected_fouls = contact_density * 0.8  # Approximation
    
    # 7. Trading Signals
    back_under_goals = destruction_score > broken_threshold
    back_over_cards = destruction_score > high_cards_threshold
    sell_early_goal = destruction_score > broken_threshold
    
    # 8. Confidence
    confidence = 50
    if rhythm_status == "BROKEN":
        confidence = config.get("signal_under_goals_confidence", 75)
    elif rhythm_status == "DISRUPTED":
        confidence = config.get("signal_over_cards_confidence", 65)
    
    return DisciplinaryResult(
        destruction_score=destruction_score,
        rhythm_status=rhythm_status,
        expected_cards=expected_cards,
        expected_fouls=expected_fouls,
        back_under_goals=back_under_goals,
        back_over_cards=back_over_cards,
        sell_early_goal=sell_early_goal,
        signal_confidence=confidence,
    )


# ═══════════════════════════════════════════════════════════════════════════════════════
# VERSION INFO
# ═══════════════════════════════════════════════════════════════════════════════════════

REFEREE_LOADER_VERSION = "1.0.0"
REFEREE_LOADER_DATE = "2025-12-25"


# ═══════════════════════════════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 80)
    print("TEST REFEREE LOADER V1.0")
    print("=" * 80)
    
    # Test 1: Chargement depuis JSON
    print("\n📋 Test 1: Chargement depuis JSON")
    loader = RefereeLoader()
    
    # Essayer de charger M Oliver
    referee = loader.load_referee_from_json("M Oliver")
    if referee:
        print(referee.summary())
    else:
        print("⚠️ M Oliver non trouvé, test avec données simulées")
        referee = RefereeDNA(
            name="Michael Oliver",
            matches=320,
            leagues=["Premier League"],
            strictness_level=7,
            avg_cards=3.80,
            avg_fouls=22.0,
            card_per_foul=12.5,  # Strict: 12.5 fautes avant carton (vs 15 moyenne)
            avg_goals=2.95,
            under_over_tendency="over",
            penalty_frequency=28.0,
            volatility=1.79,
            home_bias=0.05,
            profile="NEUTRAL",
            style="TRIGGER_HAPPY",
        )
        print(referee.summary())
    
    # Test 2: Rhythm Destruction Score
    print("\n📋 Test 2: Rhythm Destruction Score")
    print("Scénario: Liverpool (pressing=75) vs Man City (pressing=70), Derby=False")
    
    result = calculate_rhythm_destruction(
        home_pressing=75.0,  # Liverpool high pressing
        away_pressing=70.0,  # City high pressing
        referee=referee,
        is_derby=False,
        rivalry_intensity=60.0,  # Rivalité modérée
    )
    
    print(f"  Destruction Score: {result.destruction_score:.2f}")
    print(f"  Rhythm Status: {result.rhythm_status}")
    print(f"  Expected Cards: {result.expected_cards:.1f}")
    print(f"  Trading Signals:")
    print(f"    - BACK Under Goals: {'✅' if result.back_under_goals else '❌'}")
    print(f"    - BACK Over Cards: {'✅' if result.back_over_cards else '❌'}")
    print(f"    - SELL Early Goal: {'✅' if result.sell_early_goal else '❌'}")
    print(f"  Signal Confidence: {result.signal_confidence}%")
    
    # Test 3: Derby scenario
    print("\n📋 Test 3: Derby Scenario")
    print("Scénario: Liverpool vs Everton (pressing=68), Derby=True")
    
    result_derby = calculate_rhythm_destruction(
        home_pressing=75.0,
        away_pressing=68.0,
        referee=referee,
        is_derby=True,  # DERBY!
    )
    
    print(f"  Destruction Score: {result_derby.destruction_score:.2f} (+{result_derby.destruction_score - result.destruction_score:.2f} vs non-derby)")
    print(f"  Rhythm Status: {result_derby.rhythm_status}")
    print(f"  Trading Signals:")
    print(f"    - BACK Under Goals: {'✅' if result_derby.back_under_goals else '❌'}")
    print(f"    - BACK Over Cards: {'✅' if result_derby.back_over_cards else '❌'}")
    
    print("\n✅ TEST PASSED")

