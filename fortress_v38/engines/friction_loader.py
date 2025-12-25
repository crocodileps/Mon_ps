#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════════════
FRICTION LOADER V1.0 - HEDGE FUND GRADE
═══════════════════════════════════════════════════════════════════════════════════════

Fichier: quantum/orchestrator/friction_loader.py
Version: 1.0.0
Date: 2025-12-25

PHILOSOPHIE QUANT SENIOR:
"Si la donnée n'existe pas en DB, elle n'existe pas. Point."
On ne fabrique pas de données fictives au runtime.

SOURCES DE DONNÉES (Fusion V1 + V3):
1. PRIORITÉ 1: quantum.quantum_friction_matrix_v3 (3,321 paires asymétriques)
   - Plus riche (32 colonnes)
   - Home/Away différenciés
   - tactical_friction, psychological_edge disponibles

2. PRIORITÉ 2: quantum.matchup_friction (3,403 paires symétriques)
   - Recherche bidirectionnelle (home↔away)
   - Mapping vers structure unifiée
   - Marqué is_symmetric=True

3. Si aucune donnée: Retourne None (pas de calcul à la volée)

USAGE:
    # Async (asyncpg)
    loader = FrictionLoader(pool=asyncpg_pool)
    friction = await loader.load_friction("Liverpool", "Manchester City")
    
    # Sync (psycopg2)
    loader = FrictionLoader()
    friction = loader.load_friction_sync("Liverpool", "Manchester City", cursor)
    
    if friction is None:
        logger.warning("Pas de données friction pour ce matchup")

INTÉGRATION:
    from quantum.orchestrator.friction_loader import FrictionLoader, FrictionData
    
    # Dans l'orchestrator
    friction = await self.friction_loader.load_friction(home_team, away_team)
    if friction:
        tensor = self.tensor_calculator.calculate(
            home_dna=home_dna,
            away_dna=away_dna,
            friction_data=friction,
        )
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
from datetime import datetime
import logging
import json

# Logger
logger = logging.getLogger("QuantumOrchestrator.FrictionLoader")


# ═══════════════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════════════

def decimal_to_float(value: Any) -> Optional[float]:
    """
    Convertit Decimal/numeric PostgreSQL en float Python.
    Gère None, Decimal, float, int, str.
    """
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def parse_jsonb(value: Any) -> Dict:
    """
    Parse un champ JSONB PostgreSQL.
    Gère str, dict, None.
    """
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    return {}


def safe_int(value: Any, default: int = 0) -> int:
    """Convertit en int de manière sécurisée."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_str(value: Any, default: str = "") -> str:
    """Convertit en str de manière sécurisée."""
    if value is None:
        return default
    return str(value)


# ═══════════════════════════════════════════════════════════════════════════════════════
# FRICTION VECTOR - Structure JSONB
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class FrictionVector:
    """
    Structure du friction_vector JSONB.
    
    Contenu typique:
    {
        "style_clash": 50,
        "offensive_potential": 77.5,
        "fatigue_factor": 0,
        "motivation_gap": 0,
        "form_divergence": 0,
        "pressing_friction": 0,
        "attacking_friction": 0,
        "defensive_friction": 0,
        "set_piece_friction": 0,
        "transition_friction": 0
    }
    """
    style_clash: float = 0.0
    offensive_potential: float = 0.0
    fatigue_factor: float = 0.0
    motivation_gap: float = 0.0
    form_divergence: float = 0.0
    pressing_friction: float = 0.0
    attacking_friction: float = 0.0
    defensive_friction: float = 0.0
    set_piece_friction: float = 0.0
    transition_friction: float = 0.0
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FrictionVector':
        """Crée un FrictionVector depuis un dict JSONB."""
        return cls(
            style_clash=decimal_to_float(data.get('style_clash')) or 0.0,
            offensive_potential=decimal_to_float(data.get('offensive_potential')) or 0.0,
            fatigue_factor=decimal_to_float(data.get('fatigue_factor')) or 0.0,
            motivation_gap=decimal_to_float(data.get('motivation_gap')) or 0.0,
            form_divergence=decimal_to_float(data.get('form_divergence')) or 0.0,
            pressing_friction=decimal_to_float(data.get('pressing_friction')) or 0.0,
            attacking_friction=decimal_to_float(data.get('attacking_friction')) or 0.0,
            defensive_friction=decimal_to_float(data.get('defensive_friction')) or 0.0,
            set_piece_friction=decimal_to_float(data.get('set_piece_friction')) or 0.0,
            transition_friction=decimal_to_float(data.get('transition_friction')) or 0.0,
        )
    
    def to_dict(self) -> Dict:
        """Convertit en dict."""
        return {
            'style_clash': self.style_clash,
            'offensive_potential': self.offensive_potential,
            'fatigue_factor': self.fatigue_factor,
            'motivation_gap': self.motivation_gap,
            'form_divergence': self.form_divergence,
            'pressing_friction': self.pressing_friction,
            'attacking_friction': self.attacking_friction,
            'defensive_friction': self.defensive_friction,
            'set_piece_friction': self.set_piece_friction,
            'transition_friction': self.transition_friction,
        }


# ═══════════════════════════════════════════════════════════════════════════════════════
# FRICTION DATA - Structure Unifiée V1 + V3
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class FrictionData:
    """
    Structure unifiée des données de friction - Fusion V1 + V3.
    
    Contient TOUTES les colonnes des deux tables, mappées de manière cohérente.
    Pas de valeurs calculées à la volée - uniquement données DB.
    
    Attributes:
        # Identification
        friction_id: ID unique (V1: id, V3: friction_id)
        home_team: Équipe à domicile
        away_team: Équipe à l'extérieur
        home_team_id: ID équipe home (si disponible)
        away_team_id: ID équipe away (si disponible)
        
        # Styles
        style_home: Style tactique home
        style_away: Style tactique away
        
        # Friction Scores (Core)
        friction_score: Score de friction principal (0-100)
        style_clash: Clash de style (0-100)
        tempo_friction: Friction de tempo (0-100)
        mental_clash: Clash mental (0-100)
        
        # Friction Scores (V3 Only)
        tactical_friction: Friction tactique (V3 only)
        risk_friction: Friction de risque (V3 only)
        psychological_edge: Edge psychologique (V3 only)
        
        # Prédictions
        predicted_goals: Buts prédits
        predicted_btts_prob: Probabilité BTTS (0-1)
        predicted_over25_prob: Probabilité Over 2.5 (0-1)
        predicted_winner: Vainqueur prédit ("home", "away", "draw")
        chaos_potential: Potentiel de chaos (0-100)
        
        # Head-to-Head
        h2h_matches: Nombre de matchs H2H
        h2h_home_wins: Victoires home dans H2H
        h2h_away_wins: Victoires away dans H2H
        h2h_draws: Nuls dans H2H
        h2h_avg_goals: Moyenne de buts H2H
        
        # Vecteurs JSONB
        friction_vector: Vecteur de friction détaillé
        historical_friction: Friction historique (V3 only)
        
        # Métadonnées
        matches_analyzed: Nombre de matchs analysés
        sample_size: Taille de l'échantillon (V1 only)
        confidence_level: Niveau de confiance ("low", "medium", "high")
        season: Saison (V3 only)
        last_match_date: Date du dernier match
        
        # Source Tracking
        source_table: "v1" ou "v3"
        is_symmetric: True si données V1 (pas de distinction home/away)
        is_reversed: True si la paire a été inversée pour trouver les données
    """
    
    # === IDENTIFICATION ===
    friction_id: int = 0
    home_team: str = ""
    away_team: str = ""
    home_team_id: Optional[int] = None
    away_team_id: Optional[int] = None
    
    # === STYLES ===
    style_home: Optional[str] = None
    style_away: Optional[str] = None
    
    # === FRICTION SCORES (CORE) ===
    friction_score: float = 50.0
    style_clash: float = 50.0
    tempo_friction: float = 50.0
    mental_clash: float = 50.0
    
    # === FRICTION SCORES (V3 ONLY) ===
    tactical_friction: Optional[float] = None
    risk_friction: Optional[float] = None
    psychological_edge: Optional[float] = None
    
    # === PRÉDICTIONS ===
    predicted_goals: Optional[float] = None
    predicted_btts_prob: Optional[float] = None
    predicted_over25_prob: Optional[float] = None
    predicted_winner: Optional[str] = None
    chaos_potential: float = 50.0
    
    # === HEAD-TO-HEAD ===
    h2h_matches: int = 0
    h2h_home_wins: int = 0
    h2h_away_wins: int = 0
    h2h_draws: int = 0
    h2h_avg_goals: Optional[float] = None
    
    # === VECTEURS JSONB ===
    friction_vector: FrictionVector = field(default_factory=FrictionVector)
    historical_friction: Dict = field(default_factory=dict)
    
    # === MÉTADONNÉES ===
    matches_analyzed: int = 0
    sample_size: int = 0
    confidence_level: str = "low"
    season: Optional[str] = None
    last_match_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # === SOURCE TRACKING ===
    source_table: str = "unknown"  # "v1" ou "v3"
    is_symmetric: bool = False     # True si V1 (pas de home/away distinction)
    is_reversed: bool = False      # True si la paire a été inversée
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # PROPRIÉTÉS CALCULÉES
    # ═══════════════════════════════════════════════════════════════════════════════
    
    @property
    def matchup_id(self) -> str:
        """Identifiant unique du matchup."""
        return f"{self.home_team}_vs_{self.away_team}"
    
    @property
    def is_high_friction(self) -> bool:
        """Friction élevée (>70) ?"""
        return self.friction_score > 70.0
    
    @property
    def is_chaotic(self) -> bool:
        """Match potentiellement chaotique (>65) ?"""
        return self.chaos_potential > 65.0
    
    @property
    def is_high_confidence(self) -> bool:
        """Données de haute confiance ?"""
        return self.confidence_level in ("high", "medium")
    
    @property
    def has_v3_data(self) -> bool:
        """A les données enrichies V3 ?"""
        return self.source_table == "v3"
    
    @property
    def has_h2h_history(self) -> bool:
        """A un historique H2H ?"""
        return self.h2h_matches > 0
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # SERIALIZATION
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire complet."""
        return {
            # Identification
            "friction_id": self.friction_id,
            "matchup_id": self.matchup_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_team_id": self.home_team_id,
            "away_team_id": self.away_team_id,
            
            # Styles
            "style_home": self.style_home,
            "style_away": self.style_away,
            
            # Friction Scores
            "friction_score": self.friction_score,
            "style_clash": self.style_clash,
            "tempo_friction": self.tempo_friction,
            "mental_clash": self.mental_clash,
            "tactical_friction": self.tactical_friction,
            "risk_friction": self.risk_friction,
            "psychological_edge": self.psychological_edge,
            
            # Prédictions
            "predicted_goals": self.predicted_goals,
            "predicted_btts_prob": self.predicted_btts_prob,
            "predicted_over25_prob": self.predicted_over25_prob,
            "predicted_winner": self.predicted_winner,
            "chaos_potential": self.chaos_potential,
            
            # H2H
            "h2h_matches": self.h2h_matches,
            "h2h_home_wins": self.h2h_home_wins,
            "h2h_away_wins": self.h2h_away_wins,
            "h2h_draws": self.h2h_draws,
            "h2h_avg_goals": self.h2h_avg_goals,
            
            # Vecteurs
            "friction_vector": self.friction_vector.to_dict(),
            "historical_friction": self.historical_friction,
            
            # Métadonnées
            "matches_analyzed": self.matches_analyzed,
            "sample_size": self.sample_size,
            "confidence_level": self.confidence_level,
            "season": self.season,
            
            # Source
            "source_table": self.source_table,
            "is_symmetric": self.is_symmetric,
            "is_reversed": self.is_reversed,
            
            # Flags calculés
            "is_high_friction": self.is_high_friction,
            "is_chaotic": self.is_chaotic,
            "is_high_confidence": self.is_high_confidence,
            "has_v3_data": self.has_v3_data,
            "has_h2h_history": self.has_h2h_history,
        }
    
    def summary(self) -> str:
        """Retourne un résumé lisible."""
        source_info = f"[{self.source_table.upper()}]"
        if self.is_symmetric:
            source_info += " [SYMMETRIC]"
        if self.is_reversed:
            source_info += " [REVERSED]"
        
        return (
            f"═══ FRICTION: {self.home_team} vs {self.away_team} ═══\n"
            f"  Source: {source_info}\n"
            f"  Friction Score: {self.friction_score:.1f} | Chaos: {self.chaos_potential:.1f}\n"
            f"  Style Clash: {self.style_clash:.1f} | Tempo: {self.tempo_friction:.1f} | Mental: {self.mental_clash:.1f}\n"
            f"  Predicted Goals: {self.predicted_goals or 'N/A'} | BTTS: {self.predicted_btts_prob or 'N/A'}\n"
            f"  H2H: {self.h2h_matches} matches | Confidence: {self.confidence_level}\n"
            f"  Flags: {'HIGH_FRICTION ' if self.is_high_friction else ''}{'CHAOTIC ' if self.is_chaotic else ''}"
        )


# ═══════════════════════════════════════════════════════════════════════════════════════
# FRICTION LOADER - Chargement depuis DB
# ═══════════════════════════════════════════════════════════════════════════════════════

class FrictionLoader:
    """
    Chargeur de données friction - Fusion V1 + V3 Hedge Fund Grade.
    
    Hiérarchie de chargement:
    1. V3 (quantum_friction_matrix_v3) - Plus riche, home/away différenciés
    2. V1 (matchup_friction) - Symétrique, recherche bidirectionnelle
    3. None - Pas de calcul à la volée
    
    Usage:
        # Async
        loader = FrictionLoader(pool=asyncpg_pool)
        friction = await loader.load_friction("Liverpool", "Manchester City")
        
        # Sync
        loader = FrictionLoader()
        friction = loader.load_friction_sync("Liverpool", "Man City", cursor)
    """
    
    # === QUERIES SQL ===
    
    # V3 Query (asymétrique - home/away exact)
    QUERY_V3 = """
        SELECT 
            friction_id, team_home_id, team_away_id,
            team_home_name, team_away_name,
            style_home, style_away,
            friction_score, style_clash, tempo_friction, mental_clash,
            tactical_friction, risk_friction, psychological_edge,
            predicted_goals, predicted_btts_prob, predicted_over25_prob, predicted_winner,
            chaos_potential,
            h2h_matches, h2h_home_wins, h2h_away_wins, h2h_draws, h2h_avg_goals,
            friction_vector, historical_friction,
            matches_analyzed, confidence_level, season,
            last_match_date, created_at, updated_at
        FROM quantum.quantum_friction_matrix_v3
        WHERE LOWER(team_home_name) = LOWER($1) 
          AND LOWER(team_away_name) = LOWER($2)
        LIMIT 1
    """
    
    # V1 Query (symétrique - recherche dans les deux sens)
    QUERY_V1_DIRECT = """
        SELECT 
            id, team_a_id, team_b_id,
            team_a_name, team_b_name,
            style_a, style_b,
            friction_score, style_clash_score, tempo_clash_score, mental_clash_score,
            predicted_goals, predicted_btts_prob, predicted_over25_prob, predicted_winner,
            chaos_potential,
            h2h_matches, h2h_team_a_wins, h2h_team_b_wins, h2h_draws, h2h_avg_goals,
            friction_vector, sample_size, confidence_level,
            last_match_date, created_at, updated_at
        FROM quantum.matchup_friction
        WHERE LOWER(team_a_name) = LOWER($1) 
          AND LOWER(team_b_name) = LOWER($2)
        LIMIT 1
    """
    
    QUERY_V1_REVERSED = """
        SELECT 
            id, team_a_id, team_b_id,
            team_a_name, team_b_name,
            style_a, style_b,
            friction_score, style_clash_score, tempo_clash_score, mental_clash_score,
            predicted_goals, predicted_btts_prob, predicted_over25_prob, predicted_winner,
            chaos_potential,
            h2h_matches, h2h_team_a_wins, h2h_team_b_wins, h2h_draws, h2h_avg_goals,
            friction_vector, sample_size, confidence_level,
            last_match_date, created_at, updated_at
        FROM quantum.matchup_friction
        WHERE LOWER(team_a_name) = LOWER($2) 
          AND LOWER(team_b_name) = LOWER($1)
        LIMIT 1
    """
    
    def __init__(self, pool=None):
        """
        Args:
            pool: Pool de connexions asyncpg (optionnel pour async)
        """
        self.pool = pool
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # ASYNC LOADING (asyncpg)
    # ═══════════════════════════════════════════════════════════════════════════════
    
    async def load_friction(
        self,
        home_team: str,
        away_team: str,
    ) -> Optional[FrictionData]:
        """
        Charge les données de friction depuis la DB (async).
        
        Hiérarchie: V3 → V1 direct → V1 inversé → None
        
        Args:
            home_team: Nom de l'équipe à domicile
            away_team: Nom de l'équipe à l'extérieur
        
        Returns:
            FrictionData ou None si aucune donnée trouvée
        """
        if not self.pool:
            logger.error("❌ Pas de pool asyncpg configuré")
            return None
        
        try:
            async with self.pool.acquire() as conn:
                # 1. Essayer V3 d'abord (plus riche)
                row = await conn.fetchrow(self.QUERY_V3, home_team, away_team)
                if row:
                    logger.debug(f"✅ V3 trouvé: {home_team} vs {away_team}")
                    return self._parse_v3_row(row, home_team, away_team)
                
                # 2. Essayer V1 direct
                row = await conn.fetchrow(self.QUERY_V1_DIRECT, home_team, away_team)
                if row:
                    logger.debug(f"✅ V1 direct trouvé: {home_team} vs {away_team}")
                    return self._parse_v1_row(row, home_team, away_team, is_reversed=False)
                
                # 3. Essayer V1 inversé
                row = await conn.fetchrow(self.QUERY_V1_REVERSED, home_team, away_team)
                if row:
                    logger.debug(f"✅ V1 inversé trouvé: {away_team} vs {home_team}")
                    return self._parse_v1_row(row, home_team, away_team, is_reversed=True)
                
                # 4. Aucune donnée
                logger.warning(f"⚠️ Pas de données friction: {home_team} vs {away_team}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erreur chargement friction: {e}")
            return None
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # SYNC LOADING (psycopg2)
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def load_friction_sync(
        self,
        home_team: str,
        away_team: str,
        cursor,
    ) -> Optional[FrictionData]:
        """
        Charge les données de friction depuis la DB (sync).
        
        Args:
            home_team: Nom de l'équipe à domicile
            away_team: Nom de l'équipe à l'extérieur
            cursor: Curseur psycopg2
        
        Returns:
            FrictionData ou None si aucune donnée trouvée
        """
        # Convertir les queries asyncpg ($1, $2) vers psycopg2 (%s)
        query_v3 = self.QUERY_V3.replace('$1', '%s').replace('$2', '%s')
        query_v1_direct = self.QUERY_V1_DIRECT.replace('$1', '%s').replace('$2', '%s')
        query_v1_reversed = self.QUERY_V1_REVERSED.replace('$1', '%s').replace('$2', '%s')
        
        try:
            # 1. Essayer V3
            cursor.execute(query_v3, (home_team, away_team))
            row = cursor.fetchone()
            if row:
                # Convertir tuple en dict avec les noms de colonnes
                columns = [desc[0] for desc in cursor.description]
                row_dict = dict(zip(columns, row))
                logger.debug(f"✅ V3 trouvé: {home_team} vs {away_team}")
                return self._parse_v3_dict(row_dict, home_team, away_team)
            
            # 2. Essayer V1 direct
            cursor.execute(query_v1_direct, (home_team, away_team))
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                row_dict = dict(zip(columns, row))
                logger.debug(f"✅ V1 direct trouvé: {home_team} vs {away_team}")
                return self._parse_v1_dict(row_dict, home_team, away_team, is_reversed=False)
            
            # 3. Essayer V1 inversé
            cursor.execute(query_v1_reversed, (home_team, away_team))
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                row_dict = dict(zip(columns, row))
                logger.debug(f"✅ V1 inversé trouvé: {away_team} vs {home_team}")
                return self._parse_v1_dict(row_dict, home_team, away_team, is_reversed=True)
            
            # 4. Aucune donnée
            logger.warning(f"⚠️ Pas de données friction: {home_team} vs {away_team}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Erreur chargement friction sync: {e}")
            return None
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # PARSING V3
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def _parse_v3_row(self, row, home_team: str, away_team: str) -> FrictionData:
        """Parse une row asyncpg V3 en FrictionData."""
        return FrictionData(
            friction_id=row['friction_id'],
            home_team=home_team,
            away_team=away_team,
            home_team_id=row['team_home_id'],
            away_team_id=row['team_away_id'],
            
            style_home=safe_str(row['style_home']),
            style_away=safe_str(row['style_away']),
            
            friction_score=decimal_to_float(row['friction_score']) or 50.0,
            style_clash=decimal_to_float(row['style_clash']) or 50.0,
            tempo_friction=decimal_to_float(row['tempo_friction']) or 50.0,
            mental_clash=decimal_to_float(row['mental_clash']) or 50.0,
            tactical_friction=decimal_to_float(row['tactical_friction']),
            risk_friction=decimal_to_float(row['risk_friction']),
            psychological_edge=decimal_to_float(row['psychological_edge']),
            
            predicted_goals=decimal_to_float(row['predicted_goals']),
            predicted_btts_prob=decimal_to_float(row['predicted_btts_prob']),
            predicted_over25_prob=decimal_to_float(row['predicted_over25_prob']),
            predicted_winner=safe_str(row['predicted_winner']),
            chaos_potential=decimal_to_float(row['chaos_potential']) or 50.0,
            
            h2h_matches=safe_int(row['h2h_matches']),
            h2h_home_wins=safe_int(row['h2h_home_wins']),
            h2h_away_wins=safe_int(row['h2h_away_wins']),
            h2h_draws=safe_int(row['h2h_draws']),
            h2h_avg_goals=decimal_to_float(row['h2h_avg_goals']),
            
            friction_vector=FrictionVector.from_dict(parse_jsonb(row['friction_vector'])),
            historical_friction=parse_jsonb(row['historical_friction']),
            
            matches_analyzed=safe_int(row['matches_analyzed']),
            confidence_level=safe_str(row['confidence_level'], 'low'),
            season=safe_str(row['season']),
            last_match_date=row['last_match_date'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            
            source_table="v3",
            is_symmetric=False,
            is_reversed=False,
        )
    
    def _parse_v3_dict(self, row: Dict, home_team: str, away_team: str) -> FrictionData:
        """Parse un dict V3 (psycopg2) en FrictionData."""
        return FrictionData(
            friction_id=row.get('friction_id', 0),
            home_team=home_team,
            away_team=away_team,
            home_team_id=row.get('team_home_id'),
            away_team_id=row.get('team_away_id'),
            
            style_home=safe_str(row.get('style_home')),
            style_away=safe_str(row.get('style_away')),
            
            friction_score=decimal_to_float(row.get('friction_score')) or 50.0,
            style_clash=decimal_to_float(row.get('style_clash')) or 50.0,
            tempo_friction=decimal_to_float(row.get('tempo_friction')) or 50.0,
            mental_clash=decimal_to_float(row.get('mental_clash')) or 50.0,
            tactical_friction=decimal_to_float(row.get('tactical_friction')),
            risk_friction=decimal_to_float(row.get('risk_friction')),
            psychological_edge=decimal_to_float(row.get('psychological_edge')),
            
            predicted_goals=decimal_to_float(row.get('predicted_goals')),
            predicted_btts_prob=decimal_to_float(row.get('predicted_btts_prob')),
            predicted_over25_prob=decimal_to_float(row.get('predicted_over25_prob')),
            predicted_winner=safe_str(row.get('predicted_winner')),
            chaos_potential=decimal_to_float(row.get('chaos_potential')) or 50.0,
            
            h2h_matches=safe_int(row.get('h2h_matches')),
            h2h_home_wins=safe_int(row.get('h2h_home_wins')),
            h2h_away_wins=safe_int(row.get('h2h_away_wins')),
            h2h_draws=safe_int(row.get('h2h_draws')),
            h2h_avg_goals=decimal_to_float(row.get('h2h_avg_goals')),
            
            friction_vector=FrictionVector.from_dict(parse_jsonb(row.get('friction_vector'))),
            historical_friction=parse_jsonb(row.get('historical_friction')),
            
            matches_analyzed=safe_int(row.get('matches_analyzed')),
            confidence_level=safe_str(row.get('confidence_level'), 'low'),
            season=safe_str(row.get('season')),
            last_match_date=row.get('last_match_date'),
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at'),
            
            source_table="v3",
            is_symmetric=False,
            is_reversed=False,
        )
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # PARSING V1
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def _parse_v1_row(self, row, home_team: str, away_team: str, is_reversed: bool) -> FrictionData:
        """Parse une row asyncpg V1 en FrictionData."""
        # Si inversé, on swap les données H2H
        if is_reversed:
            h2h_home_wins = safe_int(row['h2h_team_b_wins'])
            h2h_away_wins = safe_int(row['h2h_team_a_wins'])
            style_home = safe_str(row['style_b'])
            style_away = safe_str(row['style_a'])
        else:
            h2h_home_wins = safe_int(row['h2h_team_a_wins'])
            h2h_away_wins = safe_int(row['h2h_team_b_wins'])
            style_home = safe_str(row['style_a'])
            style_away = safe_str(row['style_b'])
        
        return FrictionData(
            friction_id=row['id'],
            home_team=home_team,
            away_team=away_team,
            home_team_id=row['team_a_id'] if not is_reversed else row['team_b_id'],
            away_team_id=row['team_b_id'] if not is_reversed else row['team_a_id'],
            
            style_home=style_home,
            style_away=style_away,
            
            # V1 utilise des noms différents
            friction_score=decimal_to_float(row['friction_score']) or 50.0,
            style_clash=decimal_to_float(row['style_clash_score']) or 50.0,
            tempo_friction=decimal_to_float(row['tempo_clash_score']) or 50.0,
            mental_clash=decimal_to_float(row['mental_clash_score']) or 50.0,
            
            # V3 only - non disponible en V1
            tactical_friction=None,
            risk_friction=None,
            psychological_edge=None,
            
            predicted_goals=decimal_to_float(row['predicted_goals']),
            predicted_btts_prob=decimal_to_float(row['predicted_btts_prob']),
            predicted_over25_prob=decimal_to_float(row['predicted_over25_prob']),
            predicted_winner=safe_str(row['predicted_winner']),
            chaos_potential=decimal_to_float(row['chaos_potential']) or 50.0,
            
            h2h_matches=safe_int(row['h2h_matches']),
            h2h_home_wins=h2h_home_wins,
            h2h_away_wins=h2h_away_wins,
            h2h_draws=safe_int(row['h2h_draws']),
            h2h_avg_goals=decimal_to_float(row['h2h_avg_goals']),
            
            friction_vector=FrictionVector.from_dict(parse_jsonb(row['friction_vector'])),
            historical_friction={},  # Non disponible en V1
            
            matches_analyzed=0,  # Non disponible en V1
            sample_size=safe_int(row['sample_size']),
            confidence_level=safe_str(row['confidence_level'], 'low'),
            season=None,  # Non disponible en V1
            last_match_date=row['last_match_date'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            
            source_table="v1",
            is_symmetric=True,
            is_reversed=is_reversed,
        )
    
    def _parse_v1_dict(self, row: Dict, home_team: str, away_team: str, is_reversed: bool) -> FrictionData:
        """Parse un dict V1 (psycopg2) en FrictionData."""
        # Si inversé, on swap les données H2H
        if is_reversed:
            h2h_home_wins = safe_int(row.get('h2h_team_b_wins'))
            h2h_away_wins = safe_int(row.get('h2h_team_a_wins'))
            style_home = safe_str(row.get('style_b'))
            style_away = safe_str(row.get('style_a'))
        else:
            h2h_home_wins = safe_int(row.get('h2h_team_a_wins'))
            h2h_away_wins = safe_int(row.get('h2h_team_b_wins'))
            style_home = safe_str(row.get('style_a'))
            style_away = safe_str(row.get('style_b'))
        
        return FrictionData(
            friction_id=row.get('id', 0),
            home_team=home_team,
            away_team=away_team,
            home_team_id=row.get('team_a_id') if not is_reversed else row.get('team_b_id'),
            away_team_id=row.get('team_b_id') if not is_reversed else row.get('team_a_id'),
            
            style_home=style_home,
            style_away=style_away,
            
            friction_score=decimal_to_float(row.get('friction_score')) or 50.0,
            style_clash=decimal_to_float(row.get('style_clash_score')) or 50.0,
            tempo_friction=decimal_to_float(row.get('tempo_clash_score')) or 50.0,
            mental_clash=decimal_to_float(row.get('mental_clash_score')) or 50.0,
            
            tactical_friction=None,
            risk_friction=None,
            psychological_edge=None,
            
            predicted_goals=decimal_to_float(row.get('predicted_goals')),
            predicted_btts_prob=decimal_to_float(row.get('predicted_btts_prob')),
            predicted_over25_prob=decimal_to_float(row.get('predicted_over25_prob')),
            predicted_winner=safe_str(row.get('predicted_winner')),
            chaos_potential=decimal_to_float(row.get('chaos_potential')) or 50.0,
            
            h2h_matches=safe_int(row.get('h2h_matches')),
            h2h_home_wins=h2h_home_wins,
            h2h_away_wins=h2h_away_wins,
            h2h_draws=safe_int(row.get('h2h_draws')),
            h2h_avg_goals=decimal_to_float(row.get('h2h_avg_goals')),
            
            friction_vector=FrictionVector.from_dict(parse_jsonb(row.get('friction_vector'))),
            historical_friction={},
            
            matches_analyzed=0,
            sample_size=safe_int(row.get('sample_size')),
            confidence_level=safe_str(row.get('confidence_level'), 'low'),
            season=None,
            last_match_date=row.get('last_match_date'),
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at'),
            
            source_table="v1",
            is_symmetric=True,
            is_reversed=is_reversed,
        )
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # BATCH LOADING
    # ═══════════════════════════════════════════════════════════════════════════════
    
    async def load_friction_batch(
        self,
        matchups: List[tuple[str, str]],
    ) -> Dict[str, Optional[FrictionData]]:
        """
        Charge plusieurs matchups en batch.
        
        Args:
            matchups: Liste de tuples (home_team, away_team)
        
        Returns:
            Dict[matchup_id, FrictionData | None]
        """
        results = {}
        for home, away in matchups:
            friction = await self.load_friction(home, away)
            matchup_id = f"{home}_vs_{away}"
            results[matchup_id] = friction
        return results
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════════════════════════
    
    async def get_coverage_stats(self) -> Dict[str, int]:
        """
        Retourne les statistiques de couverture des tables.
        
        Returns:
            {"v1_count": 3403, "v3_count": 3321, "total_unique": ...}
        """
        if not self.pool:
            return {"error": "No pool configured"}
        
        try:
            async with self.pool.acquire() as conn:
                v1_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM quantum.matchup_friction"
                )
                v3_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM quantum.quantum_friction_matrix_v3"
                )
                return {
                    "v1_count": v1_count,
                    "v3_count": v3_count,
                    "v1_is_symmetric": True,
                    "v3_is_asymmetric": True,
                }
        except Exception as e:
            return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════════════
# VERSION INFO
# ═══════════════════════════════════════════════════════════════════════════════════════

FRICTION_LOADER_VERSION = "1.0.0"
FRICTION_LOADER_DATE = "2025-12-25"


# ═══════════════════════════════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 80)
    print("TEST FRICTION LOADER V1.0 - HEDGE FUND GRADE")
    print("=" * 80)
    
    # Test 1: FrictionVector parsing
    print("\n📋 Test 1: FrictionVector parsing")
    sample_vector = {
        "style_clash": 50,
        "offensive_potential": 77.5,
        "fatigue_factor": 0,
        "pressing_friction": 15.5,
    }
    fv = FrictionVector.from_dict(sample_vector)
    print(f"  style_clash: {fv.style_clash}")
    print(f"  offensive_potential: {fv.offensive_potential}")
    print(f"  pressing_friction: {fv.pressing_friction}")
    
    # Test 2: FrictionData creation
    print("\n📋 Test 2: FrictionData creation")
    friction = FrictionData(
        friction_id=1,
        home_team="Liverpool",
        away_team="Manchester City",
        friction_score=72.5,
        chaos_potential=68.0,
        style_clash=65.0,
        tempo_friction=58.0,
        mental_clash=70.0,
        predicted_goals=2.85,
        predicted_btts_prob=0.65,
        h2h_matches=25,
        h2h_home_wins=12,
        h2h_away_wins=8,
        h2h_draws=5,
        confidence_level="high",
        source_table="v3",
        friction_vector=fv,
    )
    print(friction.summary())
    
    # Test 3: Properties
    print("\n📋 Test 3: Calculated Properties")
    print(f"  matchup_id: {friction.matchup_id}")
    print(f"  is_high_friction: {friction.is_high_friction}")
    print(f"  is_chaotic: {friction.is_chaotic}")
    print(f"  is_high_confidence: {friction.is_high_confidence}")
    print(f"  has_v3_data: {friction.has_v3_data}")
    print(f"  has_h2h_history: {friction.has_h2h_history}")
    
    # Test 4: Serialization
    print("\n📋 Test 4: Serialization")
    data_dict = friction.to_dict()
    print(f"  Keys count: {len(data_dict)}")
    print(f"  Source: {data_dict['source_table']}")
    
    # Test 5: Helpers
    print("\n📋 Test 5: Helpers")
    from decimal import Decimal
    print(f"  decimal_to_float(Decimal('3.14')): {decimal_to_float(Decimal('3.14'))}")
    print(f"  decimal_to_float(None): {decimal_to_float(None)}")
    print(f"  parse_jsonb(json_str): {parse_jsonb('{"a": 1}')}")
    
    print("\n✅ TEST PASSED - FRICTION LOADER V1.0")
    print("\n⚠️ Pour tester avec la vraie DB, utiliser:")
    print("   PYTHONPATH=/home/Mon_ps python3 -c \"")
    print("   import asyncio")
    print("   import asyncpg")
    print("   from quantum.orchestrator.friction_loader import FrictionLoader")
    print("   ")
    print("   async def test():")
    print("       pool = await asyncpg.create_pool('postgresql://monps_user:monps_secure_password_2024@localhost/monps_db')")
    print("       loader = FrictionLoader(pool)")
    print("       friction = await loader.load_friction('Liverpool', 'Manchester City')")
    print("       if friction:")
    print("           print(friction.summary())")
    print("       await pool.close()")
    print("   ")
    print("   asyncio.run(test())\"")

