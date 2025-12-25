"""
Runtime Calculators - Ajustements Temps Réel Senior Quant Grade
================================================================

FORTRESS V3.8 - Phase 3 Completion
Date: 25 Décembre 2025

COMPOSANTS:
1. CoachImpact - Avec Honeymoon Factor (New Manager Bounce)
2. AbsenceImpact - Avec xG Lost et Cluster Factor
3. FatigueImpact - Avec Zones et Rotation Probability

SOURCES DE DONNÉES:
- coach_intelligence (PostgreSQL) - 108 coaches, 151 colonnes
- cache/transfermarkt/*_injuries.json - Fraîcheur quotidienne
- cache/transfermarkt/*_scorers_v2.json - Stats joueurs
- match_results (PostgreSQL) - Dates des matchs

PATTERN: Singleton + Dataclasses typées + Fuzzy Matching Cache

PRINCIPES SENIOR QUANT:
- Honeymoon Factor: Modélise le "New Manager Bounce" (exponentiel)
- Cluster Factor: Impact exponentiel si même ligne touchée
- xG Lost: Quantifie l'impact réel des absences (pas le "body count")
- Rotation Probability: Heuristique basée sur type de match
- Fuzzy Matching: Cache + Token Set + Substring pour noms joueurs
"""

import json
import logging
import math
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Database connection (lazy import pour éviter circular)
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION ET CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

# Database connection
DB_CONFIG = {
    "host": "localhost",
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

# Chemins des fichiers JSON
BASE_PATH = Path("/home/Mon_ps")
INJURIES_PATH = BASE_PATH / "cache" / "transfermarkt"
SCORERS_PATH = BASE_PATH / "cache" / "transfermarkt"


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES COACH - HONEYMOON FACTOR
# ═══════════════════════════════════════════════════════════════════════════════

HONEYMOON_PHASES = {
    "SHOCK": (0, 14),           # Jours 0-14: Boost maximal (choc psychologique)
    "HONEYMOON": (15, 45),      # Jours 15-45: Décroissance exponentielle
    "STABILIZATION": (46, 90),  # Jours 46-90: Incertitude tactique
    "ESTABLISHED": (91, float('inf'))  # 90+: Style connu et prévisible
}

HONEYMOON_VOLATILITY = {
    "SHOCK": 1.25,        # +25% volatilité marchés (over/btts boost)
    "HONEYMOON": 1.15,    # +15% (décroissant)
    "STABILIZATION": 1.05,
    "ESTABLISHED": 1.0
}

HONEYMOON_UNCERTAINTY = {
    "SHOCK": 0.90,        # 90% incertitude tactique
    "HONEYMOON": 0.70,
    "STABILIZATION": 0.40,
    "ESTABLISHED": 0.10
}


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES ABSENCES - CLUSTER FACTOR ET POSITIONS
# ═══════════════════════════════════════════════════════════════════════════════

# Poids par position pour impact défensif
POSITION_DEFENSE_WEIGHTS = {
    "Goalkeeper": 0.40,
    "Centre-Back": 0.35,
    "Left-Back": 0.15,
    "Right-Back": 0.15,
    "Defensive Midfield": 0.25,
    "Central Midfield": 0.10,
    "Attacking Midfield": 0.05,
    "Left Winger": 0.02,
    "Right Winger": 0.02,
    "Centre-Forward": 0.02,
    "Second Striker": 0.02,
}

# Seuils Cluster Factor (effet exponentiel si même ligne touchée)
CLUSTER_THRESHOLDS = {
    "defenders": {0: 0.0, 1: 0.0, 2: 0.50, 3: 1.0},
    "midfielders": {0: 0.0, 1: 0.0, 2: 0.30, 3: 0.70},
    "attackers": {0: 0.0, 1: 0.0, 2: 0.40, 3: 0.80}
}

# Positions par ligne
DEFENDER_POSITIONS = {"Goalkeeper", "Centre-Back", "Left-Back", "Right-Back"}
MIDFIELDER_POSITIONS = {"Defensive Midfield", "Central Midfield", "Attacking Midfield"}
ATTACKER_POSITIONS = {"Left Winger", "Right Winger", "Centre-Forward", "Second Striker"}


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES FATIGUE - ZONES ET ROTATION
# ═══════════════════════════════════════════════════════════════════════════════

# Zones de fatigue (en heures depuis dernier match)
FATIGUE_ZONES = {
    "DANGER": (0, 72),          # < 3 jours: Risque blessure, -15% perf
    "RECOVERY": (72, 120),      # 3-5 jours: Récupération incomplète
    "OPTIMAL": (120, 216),      # 5-9 jours: Performance optimale
    "FRESH": (216, 336),        # 9-14 jours: Bien reposé, +5%
    "RUST": (336, float('inf')) # > 14 jours: Manque de rythme
}

# Modificateurs de performance par zone
FATIGUE_MODIFIERS = {
    "DANGER": -0.15,      # -15% performance
    "RECOVERY": -0.05,    # -5%
    "OPTIMAL": 0.0,       # Baseline
    "FRESH": +0.05,       # +5%
    "RUST": -0.08         # -8%
}

# Probabilité de rotation par type de match
MATCH_TYPE_ROTATION_PROBABILITY = {
    "DOMESTIC_CUP_EARLY": 0.75,    # FA Cup early rounds
    "LEAGUE_CUP": 0.80,            # Carabao Cup
    "FA_CUP_3RD_ROUND": 0.70,
    "EUROPA_LEAGUE_GROUP": 0.50,
    "EUROPA_CONFERENCE": 0.60,
    "CHAMPIONS_LEAGUE_GROUP": 0.25,
    "CHAMPIONS_LEAGUE_KO": 0.10,
    "PREMIER_LEAGUE": 0.15,
    "CHAMPIONSHIP": 0.20,
    "LA_LIGA": 0.15,
    "BUNDESLIGA": 0.15,
    "SERIE_A": 0.15,
    "LIGUE_1": 0.15,
    "UNKNOWN": 0.30
}


# ═══════════════════════════════════════════════════════════════════════════════
# SOURCES DONNÉES ENRICHIES (xG, position)
# ═══════════════════════════════════════════════════════════════════════════════

GOALSCORER_PROFILES_PATH = BASE_PATH / "data" / "goals" / "goalscorer_profiles_2025.json"
FBREF_PLAYERS_PATH = BASE_PATH / "data" / "fbref" / "fbref_players_complete_2025_26.json"

# Mapping positions FBRef → catégories pour Cluster Factor
FBREF_POSITION_MAPPING = {
    "GK": "Goalkeeper",
    "DF": "Centre-Back",
    "DFMF": "Defensive Midfield",
    "DFFW": "Centre-Back",  # Rare mais possible
    "MF": "Central Midfield",
    "MFDF": "Defensive Midfield",
    "MFFW": "Attacking Midfield",
    "FW": "Centre-Forward",
    "FWMF": "Right Winger",  # Forward who plays midfield
    "FWDF": "Centre-Forward",  # Rare
}


# Mapping compétitions → types
COMPETITION_TYPE_MAPPING = {
    "Premier League": "PREMIER_LEAGUE",
    "Championship": "CHAMPIONSHIP",
    "FA Cup": "FA_CUP_3RD_ROUND",
    "EFL Cup": "LEAGUE_CUP",
    "Carabao Cup": "LEAGUE_CUP",
    "League Cup": "LEAGUE_CUP",
    "UEFA Champions League": "CHAMPIONS_LEAGUE_GROUP",
    "Champions League": "CHAMPIONS_LEAGUE_GROUP",
    "UEFA Europa League": "EUROPA_LEAGUE_GROUP",
    "Europa League": "EUROPA_LEAGUE_GROUP",
    "UEFA Europa Conference League": "EUROPA_CONFERENCE",
    "La Liga": "LA_LIGA",
    "Bundesliga": "BUNDESLIGA",
    "Serie A": "SERIE_A",
    "Ligue 1": "LIGUE_1",
}


# ═══════════════════════════════════════════════════════════════════════════════
# CACHE FUZZY MATCHING
# ═══════════════════════════════════════════════════════════════════════════════

_PLAYER_ALIAS_CACHE: Dict[str, str] = {}


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _normalize_name(name: str) -> str:
    """
    Normalise un nom pour comparaison.
    - Minuscules
    - Supprime accents (é → e, ñ → n)
    - Strip whitespace
    """
    if not name:
        return ""
    normalized = unicodedata.normalize('NFD', name)
    ascii_name = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    return ascii_name.lower().strip()


def _tokenize_name(name: str) -> set:
    """
    Tokenise un nom pour Token Set Ratio.
    "Kevin De Bruyne" → {"kevin", "de", "bruyne"}
    """
    return set(_normalize_name(name).split())


def _fuzzy_match_player(
    target: str,
    candidates: List[str],
    threshold: float = 0.85
) -> Optional[str]:
    """
    Trouve le meilleur match pour un nom de joueur.

    STRATÉGIE SENIOR QUANT:
    1. Cache check (O(1) si déjà résolu)
    2. Exact match normalisé (fast path)
    3. Substring match (noms courts comme "Salah")
    4. Token Set Ratio (ordre des mots ignoré)
    5. SequenceMatcher (similarité globale)

    Args:
        target: Nom du joueur blessé (depuis injuries.json)
        candidates: Liste des joueurs connus (depuis scorers)
        threshold: Score minimum pour accepter (0.85 = 85%)

    Returns:
        Nom exact du joueur matché ou None
    """
    global _PLAYER_ALIAS_CACHE

    if not target or not candidates:
        return None

    # 0. Cache check (si déjà résolu)
    cache_key = _normalize_name(target)
    if cache_key in _PLAYER_ALIAS_CACHE:
        cached = _PLAYER_ALIAS_CACHE[cache_key]
        if cached in candidates:
            return cached

    target_clean = _normalize_name(target)
    target_tokens = _tokenize_name(target)

    best_match = None
    best_score = 0.0

    for candidate in candidates:
        cand_clean = _normalize_name(candidate)

        # 1. Exact match normalisé (Fast path)
        if target_clean == cand_clean:
            _PLAYER_ALIAS_CACHE[cache_key] = candidate
            return candidate

        score = 0.0

        # 2. Substring match (ex: "Salah" in "Mohamed Salah")
        if len(target_clean) >= 4:
            if target_clean in cand_clean:
                score = 0.92
            elif cand_clean in target_clean:
                score = 0.88

        # 3. Token Set Ratio (ordre des mots ignoré)
        if score < threshold:
            cand_tokens = _tokenize_name(candidate)
            if target_tokens and cand_tokens:
                intersection = len(target_tokens & cand_tokens)
                union = len(target_tokens | cand_tokens)
                if union > 0:
                    jaccard = intersection / union
                    if target_tokens <= cand_tokens:
                        jaccard = min(1.0, jaccard + 0.15)
                    score = max(score, jaccard)

        # 4. SequenceMatcher (fallback)
        if score < threshold:
            seq_score = SequenceMatcher(None, target_clean, cand_clean).ratio()
            score = max(score, seq_score)

        # Track best
        if score > best_score and score >= threshold:
            best_score = score
            best_match = candidate

    # Cache le résultat
    if best_match:
        _PLAYER_ALIAS_CACHE[cache_key] = best_match

    return best_match


def clear_player_cache():
    """Vide le cache (utile pour tests)."""
    global _PLAYER_ALIAS_CACHE
    _PLAYER_ALIAS_CACHE = {}


def _calculate_honeymoon_factor(tenure_days: int) -> Tuple[str, float, float]:
    """
    Calcule le Honeymoon Factor basé sur l'ancienneté du coach.

    Modèle: New Manager Bounce avec décroissance exponentielle.

    Args:
        tenure_days: Nombre de jours depuis l'arrivée du coach

    Returns:
        (phase, volatility_factor, decay_progress)
    """
    for phase, (min_days, max_days) in HONEYMOON_PHASES.items():
        if min_days <= tenure_days < max_days:
            volatility = HONEYMOON_VOLATILITY[phase]

            # Calculer le decay (progression dans la phase)
            if max_days == float('inf'):
                decay = 1.0
            else:
                phase_duration = max_days - min_days
                days_in_phase = tenure_days - min_days
                decay = days_in_phase / phase_duration

            # Décroissance exponentielle pour HONEYMOON
            if phase == "HONEYMOON":
                # De 1.25 à 1.05 de façon exponentielle
                volatility = 1.05 + (0.20 * math.exp(-3 * decay))

            return phase, volatility, decay

    return "ESTABLISHED", 1.0, 1.0


def _calculate_cluster_factor(positions_out: List[str]) -> Tuple[float, float, float]:
    """
    Calcule les Cluster Factors par ligne.

    Principe: L'impact est EXPONENTIEL si plusieurs joueurs de la même ligne
    sont absents. 1 défenseur out = gérable. 3 défenseurs out = ligne brisée.

    Args:
        positions_out: Liste des positions des joueurs absents

    Returns:
        (defensive_cluster, midfield_cluster, attack_cluster)
    """
    defenders_out = sum(1 for p in positions_out if p in DEFENDER_POSITIONS)
    midfielders_out = sum(1 for p in positions_out if p in MIDFIELDER_POSITIONS)
    attackers_out = sum(1 for p in positions_out if p in ATTACKER_POSITIONS)

    def get_cluster(count: int, thresholds: dict) -> float:
        count_capped = min(count, 3)
        return thresholds.get(count_capped, thresholds.get(3, 1.0))

    def_cluster = get_cluster(defenders_out, CLUSTER_THRESHOLDS["defenders"])
    mid_cluster = get_cluster(midfielders_out, CLUSTER_THRESHOLDS["midfielders"])
    att_cluster = get_cluster(attackers_out, CLUSTER_THRESHOLDS["attackers"])

    return def_cluster, mid_cluster, att_cluster


def _get_fatigue_zone(hours_since_match: float) -> str:
    """Détermine la zone de fatigue basée sur les heures depuis le dernier match."""
    for zone, (min_h, max_h) in FATIGUE_ZONES.items():
        if min_h <= hours_since_match < max_h:
            return zone
    return "RUST"


def _normalize_team_name(team_name: str) -> str:
    """Normalise un nom d'équipe pour matcher les fichiers."""
    name = team_name.lower().strip()
    name = name.replace(" ", "_")
    name = name.replace(".", "")
    name = name.replace("'", "")
    # Mappings spécifiques
    mappings = {
        "manchester_united": "manchester_united",
        "manchester_city": "manchester_city",
        "tottenham_hotspur": "tottenham",
        "tottenham": "tottenham",
        "wolverhampton_wanderers": "wolves",
        "wolverhampton": "wolves",
        "wolves": "wolves",
        "west_ham_united": "west_ham",
        "west_ham": "west_ham",
        "nottingham_forest": "nottingham_forest",
        "newcastle_united": "newcastle",
        "newcastle": "newcastle",
        "leicester_city": "leicester",
        "leicester": "leicester",
        "ipswich_town": "ipswich",
        "ipswich": "ipswich",
        "crystal_palace": "crystal_palace",
        "aston_villa": "aston_villa",
    }
    return mappings.get(name, name)


def _extract_fbref_position(player_data: dict) -> str:
    """
    Extrait la position depuis les données FBRef.

    La position est dans: standard['Unnamed: 3_level_0_Pos']
    Format: "FWMF", "DF", "GK", etc.
    """
    if not player_data:
        return "Unknown"

    standard = player_data.get('standard', {})
    pos_code = standard.get('Unnamed: 3_level_0_Pos', '')

    if not pos_code:
        return "Unknown"

    return FBREF_POSITION_MAPPING.get(pos_code, "Unknown")


def _extract_fbref_npxg(player_data: dict) -> float:
    """
    Extrait npxG per 90 depuis les données FBRef.

    Priorité: Per 90 Minutes_npxG > Expected_npxG / 90s
    """
    if not player_data:
        return 0.0

    standard = player_data.get('standard', {})

    # Option 1: npxG per 90 direct
    npxg_per_90 = standard.get('Per 90 Minutes_npxG', 0)
    if npxg_per_90 and npxg_per_90 > 0:
        return float(npxg_per_90)

    # Option 2: Calculer depuis total
    npxg_total = standard.get('Expected_npxG', 0)
    ninety_s = standard.get('Playing Time_90s', 0)

    if npxg_total and ninety_s and ninety_s > 0:
        return float(npxg_total) / float(ninety_s)

    return 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASS: COACH IMPACT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CoachImpact:
    """
    Impact coach Senior Quant avec Honeymoon Factor.

    Le Honeymoon Factor modélise le "New Manager Bounce":
    - SHOCK (0-14j): Boost maximal, très volatile
    - HONEYMOON (15-45j): Décroissance exponentielle
    - STABILIZATION (46-90j): Incertitude tactique
    - ESTABLISHED (90+j): Style connu et prévisible
    """

    # Identité
    coach_name: str = "Unknown"
    team_name: str = "Unknown"

    # Tenure
    tenure_days: int = 1000
    tenure_months: int = 33
    tenure_phase: str = "ESTABLISHED"

    # Honeymoon Factor (SENIOR QUANT)
    honeymoon_factor: float = 1.0
    honeymoon_decay: float = 1.0

    # Style tactique
    tactical_style: str = "balanced"
    pressing_style: str = "medium"
    tactical_flexibility: int = 50

    # Market Modifiers (depuis DB)
    market_modifiers: Dict[str, float] = field(default_factory=dict)

    # Forme actuelle
    form_trend: str = "STABLE"
    current_streak: str = ""
    recent_form_points: int = 0

    # Incertitude
    tactical_uncertainty: float = 0.1

    # Sécurité emploi
    job_security: str = "stable"
    rumored_departure: bool = False

    # Recommandation
    recommended_action: str = "NORMAL"

    # Meta
    is_valid: bool = True
    data_source: str = "coach_intelligence"
    last_updated: datetime = None

    @property
    def is_new_coach(self) -> bool:
        """Coach en poste depuis moins de 90 jours."""
        return self.tenure_days < 90

    @property
    def is_in_bounce_period(self) -> bool:
        """Coach en période de New Manager Bounce (45 premiers jours)."""
        return self.tenure_days <= 45

    @property
    def volatility_boost(self) -> float:
        """Boost de volatilité pour marchés over/btts."""
        return self.honeymoon_factor - 1.0  # Ex: 1.25 → 0.25 (+25%)

    def get_market_modifier(self, market: str) -> float:
        """Retourne le modificateur pour un marché spécifique."""
        return self.market_modifiers.get(market, 1.0)


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASS: ABSENCE IMPACT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AbsenceImpact:
    """
    Impact absences Senior Quant avec xG Lost et Cluster Factor.

    Principes:
    - xG Lost: Quantifie l'impact réel (pas le "body count")
    - Cluster Factor: Impact EXPONENTIEL si même ligne touchée
    - Key Players: Tracking des joueurs essentiels
    """

    # Identité
    team_name: str = "Unknown"

    # Comptage (Junior metric - gardé pour compatibilité)
    missing_count: int = 0

    # Joueurs absents détaillés
    missing_players: List[Dict[str, Any]] = field(default_factory=list)

    # MÉTRIQUES SENIOR QUANT
    total_xg_lost: float = 0.0
    team_xg_percentage_lost: float = 0.0

    # Key Players
    top_scorer_absent: bool = False
    top_assister_absent: bool = False
    key_defender_absent: bool = False
    goalkeeper_absent: bool = False

    # CLUSTER FACTOR
    defensive_cluster_factor: float = 0.0
    midfield_cluster_factor: float = 0.0
    attack_cluster_factor: float = 0.0

    # Breakdown par ligne
    defenders_out: int = 0
    midfielders_out: int = 0
    attackers_out: int = 0

    # Meta
    is_valid: bool = True
    data_freshness: datetime = None

    @property
    def severity_score(self) -> float:
        """Score 0-100 de l'impact des absences."""
        score = 0.0

        # Impact xG (20 points par xG perdu, max 40)
        score += min(40, self.total_xg_lost * 20)

        # Cluster défensif (exponentiel)
        if self.defensive_cluster_factor >= 1.0:
            score += 30  # Ligne brisée
        elif self.defensive_cluster_factor >= 0.5:
            score += 20
        elif self.defensive_cluster_factor > 0:
            score += 10

        # Key players
        if self.top_scorer_absent:
            score += 15
        if self.top_assister_absent:
            score += 10
        if self.goalkeeper_absent:
            score += 20
        if self.key_defender_absent:
            score += 10

        return min(100.0, score)

    @property
    def attack_impact(self) -> float:
        """Impact sur capacité offensive (-1 à 0)."""
        return -min(1.0, self.total_xg_lost / 2.0)

    @property
    def defense_impact(self) -> float:
        """Impact sur solidité défensive (-1 à 0)."""
        return -self.defensive_cluster_factor

    @property
    def market_recommendations(self) -> Dict[str, str]:
        """Recommandations marchés basées sur les absences."""
        recs = {}
        if self.defensive_cluster_factor >= 0.5:
            recs["over25"] = "VALUE"
            recs["btts"] = "VALUE"
            recs["clean_sheet"] = "FADE"
        if self.total_xg_lost > 0.5:
            recs["team_goals"] = "UNDER_VALUE"
        if self.top_scorer_absent:
            recs["anytime_scorer"] = "AVOID_TEAM"
        return recs

    @property
    def has_significant_impact(self) -> bool:
        """True si l'impact est significatif (>25/100)."""
        return self.severity_score > 25


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASS: FATIGUE IMPACT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class FatigueImpact:
    """
    Impact fatigue Senior Quant avec zones et rotation probability.

    Zones:
    - DANGER: <72h (risque blessure, -15% perf)
    - RECOVERY: 72-120h (-5%)
    - OPTIMAL: 120-216h (baseline)
    - FRESH: 216-336h (+5%)
    - RUST: >336h (-8%, manque rythme)
    """

    # Identité
    team_name: str = "Unknown"

    # Timing
    last_match_date: datetime = None
    hours_since_last_match: float = 168.0

    # Zone de fatigue
    fatigue_zone: str = "OPTIMAL"

    # Congestion
    matches_last_7_days: int = 1
    matches_last_14_days: int = 2
    matches_last_21_days: int = 3

    # Contexte dernier match
    last_match_type: str = "UNKNOWN"
    last_match_competition: str = ""
    rotation_probability: float = 0.30

    # Scores calculés
    base_fatigue_modifier: float = 0.0
    effective_fatigue_modifier: float = 0.0

    # Meta
    is_valid: bool = True
    confidence: str = "MEDIUM"

    @property
    def days_since_last_match(self) -> float:
        """Jours depuis dernier match."""
        return self.hours_since_last_match / 24.0

    @property
    def congestion_factor(self) -> float:
        """1.0 = Frais, 0.5 = Épuisé."""
        factors = {
            "DANGER": 0.60,
            "RECOVERY": 0.85,
            "OPTIMAL": 1.0,
            "FRESH": 1.05,
            "RUST": 0.90
        }
        return factors.get(self.fatigue_zone, 1.0)

    @property
    def is_congested(self) -> bool:
        """True si fatigue critique."""
        return self.fatigue_zone == "DANGER" or self.matches_last_7_days >= 3

    @property
    def is_rusty(self) -> bool:
        """True si manque de rythme."""
        return self.fatigue_zone == "RUST"

    @property
    def is_fresh(self) -> bool:
        """True si bien reposé."""
        return self.fatigue_zone == "FRESH"

    @property
    def performance_modifier(self) -> float:
        """Modificateur de performance global."""
        return self.effective_fatigue_modifier


# ═══════════════════════════════════════════════════════════════════════════════
# CLASSE PRINCIPALE: RUNTIME CALCULATORS
# ═══════════════════════════════════════════════════════════════════════════════

class RuntimeCalculators:
    """
    Singleton pour calculs runtime Senior Quant Grade.

    USAGE:
        calcs = RuntimeCalculators()
        coach = calcs.get_coach_impact("Liverpool")
        absences = calcs.get_absence_impact("Liverpool")
        fatigue = calcs.get_fatigue_impact("Liverpool")
        combined = calcs.get_combined_adjustment("Liverpool")
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if RuntimeCalculators._initialized:
            return

        self._db_conn = None
        self._coach_cache: Dict[str, CoachImpact] = {}
        self._absence_cache: Dict[str, AbsenceImpact] = {}
        self._fatigue_cache: Dict[str, FatigueImpact] = {}
        self._cache_ttl = timedelta(minutes=30)
        self._cache_timestamps: Dict[str, datetime] = {}

        # Cache données enrichies (lazy loading)
        self._goalscorer_data: Dict[str, dict] = None
        self._fbref_data: Dict[str, dict] = None

        RuntimeCalculators._initialized = True
        logger.info("RuntimeCalculators initialized (Singleton)")

    def _get_db_connection(self):
        """Lazy database connection."""
        if not HAS_PSYCOPG2:
            logger.warning("psycopg2 not available")
            return None

        if self._db_conn is None or self._db_conn.closed:
            try:
                self._db_conn = psycopg2.connect(**DB_CONFIG)
            except Exception as e:
                logger.error(f"DB connection failed: {e}")
                return None
        return self._db_conn

    def _load_enriched_data(self):
        """
        Charge les données enrichies (goalscorer + fbref) - Lazy loading.

        Sources:
        - goalscorer_profiles_2025.json: 876 joueurs avec xg_per_90, total_xg
        - fbref_players_complete_2025_26.json: 2314 joueurs avec position, npxG
        """
        # Charger goalscorer profiles (pour xG)
        if self._goalscorer_data is None:
            self._goalscorer_data = {}
            try:
                if GOALSCORER_PROFILES_PATH.exists():
                    with open(GOALSCORER_PROFILES_PATH, 'r') as f:
                        raw = json.load(f)
                        # Index par (player_name_lower, team_name_lower)
                        for player_id, player in raw.items():
                            name = player.get('player_name', '').lower()
                            team = player.get('team_name', '').lower()
                            if name:
                                self._goalscorer_data[(name, team)] = player
                                # Aussi indexer par nom seul (fallback)
                                if name not in self._goalscorer_data:
                                    self._goalscorer_data[name] = player
                    logger.info(f"Loaded {len(self._goalscorer_data)} goalscorer profiles")
            except Exception as e:
                logger.error(f"Error loading goalscorer profiles: {e}")

        # Charger FBRef data (pour position)
        if self._fbref_data is None:
            self._fbref_data = {}
            try:
                if FBREF_PLAYERS_PATH.exists():
                    with open(FBREF_PLAYERS_PATH, 'r') as f:
                        raw = json.load(f)
                        players = raw.get('players', {})
                        # Index par nom lower
                        for name, pdata in players.items():
                            name_lower = name.lower()
                            team = (pdata.get('team', '') or '').lower()
                            self._fbref_data[name_lower] = pdata
                            # Aussi avec team
                            if team:
                                self._fbref_data[(name_lower, team)] = pdata
                    logger.info(f"Loaded {len(self._fbref_data)} FBRef players")
            except Exception as e:
                logger.error(f"Error loading FBRef data: {e}")

    def _get_player_xg(self, player_name: str, team_name: str) -> float:
        """Récupère xg_per_90 pour un joueur depuis goalscorer_profiles."""
        self._load_enriched_data()

        name_lower = player_name.lower()
        team_lower = team_name.lower()

        # Essayer avec team d'abord
        player = self._goalscorer_data.get((name_lower, team_lower))
        if not player:
            # Fallback: fuzzy match sur le nom
            matched = _fuzzy_match_player(player_name,
                [k for k in self._goalscorer_data.keys() if isinstance(k, str)])
            if matched:
                player = self._goalscorer_data.get(matched.lower())

        if player:
            # Priorité: xg_per_90 > total_xg / matches
            xg_per_90 = player.get('xg_per_90', 0)
            if xg_per_90 and xg_per_90 > 0:
                return float(xg_per_90)

            total_xg = player.get('total_xg', 0)
            matches = player.get('matches_with_goal', 1) or 1
            if total_xg:
                return float(total_xg) / float(matches) * 0.5  # Estimation conservative

        return 0.0

    def _get_player_position(self, player_name: str, team_name: str) -> str:
        """Récupère la position pour un joueur depuis FBRef."""
        self._load_enriched_data()

        name_lower = player_name.lower()
        team_lower = team_name.lower()

        # Essayer match exact avec team
        player = self._fbref_data.get((name_lower, team_lower))
        if not player:
            # Essayer match exact sans team
            player = self._fbref_data.get(name_lower)
        if not player:
            # Fuzzy match
            matched = _fuzzy_match_player(player_name,
                [k for k in self._fbref_data.keys() if isinstance(k, str)])
            if matched:
                player = self._fbref_data.get(matched.lower())

        if player:
            return _extract_fbref_position(player)

        return "Unknown"

    def _is_cache_valid(self, key: str) -> bool:
        """Vérifie si le cache est encore valide."""
        if key not in self._cache_timestamps:
            return False
        return datetime.now() - self._cache_timestamps[key] < self._cache_ttl

    # ═══════════════════════════════════════════════════════════════
    # COACH IMPACT
    # ═══════════════════════════════════════════════════════════════

    def get_coach_impact(self, team_name: str) -> CoachImpact:
        """
        Calcule l'impact du coach avec Honeymoon Factor.

        Sources:
        - Table coach_intelligence (151 colonnes)
        - Table coach_team_mapping
        """
        cache_key = f"coach_{team_name}"
        if self._is_cache_valid(cache_key) and cache_key in self._coach_cache:
            return self._coach_cache[cache_key]

        conn = self._get_db_connection()
        if not conn:
            return CoachImpact(team_name=team_name, is_valid=False)

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Chercher le coach de l'équipe
                cur.execute("""
                    SELECT ci.*, ctm.contract_start
                    FROM coach_intelligence ci
                    JOIN coach_team_mapping ctm ON ci.coach_name = ctm.coach_name
                    WHERE ctm.team_name ILIKE %s
                    LIMIT 1
                """, (f"%{team_name}%",))

                row = cur.fetchone()

                if not row:
                    logger.warning(f"No coach found for {team_name}")
                    return CoachImpact(team_name=team_name, is_valid=False)

                # Calculer tenure
                tenure_start = row.get('tenure_start_date') or row.get('contract_start')
                if tenure_start:
                    tenure_days = (datetime.now().date() - tenure_start).days
                else:
                    tenure_days = row.get('tenure_months', 12) * 30

                # Calculer Honeymoon Factor
                phase, volatility, decay = _calculate_honeymoon_factor(tenure_days)

                # Market modifiers
                market_mods = {
                    "btts": 1.0 + (row.get('market_impact_btts', 0) or 0) / 100,
                    "over25": 1.0 + (row.get('market_impact_over25', 0) or 0) / 100,
                    "under25": 1.0 + (row.get('market_impact_under25', 0) or 0) / 100,
                    "draw": 1.0 + (row.get('market_impact_draw', 0) or 0) / 100,
                    "clean_sheet": 1.0 + (row.get('market_impact_clean_sheet', 0) or 0) / 100,
                }

                # Si en période bounce, boost over/btts
                if phase in ("SHOCK", "HONEYMOON"):
                    market_mods["btts"] *= volatility
                    market_mods["over25"] *= volatility

                # Recommandation
                if phase == "SHOCK":
                    action = "BOOST_VOLATILITY"
                elif phase == "HONEYMOON":
                    action = "CAUTION"
                elif row.get('job_security') == 'at_risk':
                    action = "REDUCE_STAKE"
                else:
                    action = "NORMAL"

                impact = CoachImpact(
                    coach_name=row.get('coach_name', 'Unknown'),
                    team_name=team_name,
                    tenure_days=tenure_days,
                    tenure_months=row.get('tenure_months', 0) or 0,
                    tenure_phase=phase,
                    honeymoon_factor=volatility,
                    honeymoon_decay=decay,
                    tactical_style=row.get('tactical_style', 'balanced') or 'balanced',
                    pressing_style=row.get('pressing_style', 'medium') or 'medium',
                    tactical_flexibility=row.get('tactical_flexibility', 50) or 50,
                    market_modifiers=market_mods,
                    form_trend=row.get('form_trend', 'stable') or 'stable',
                    current_streak=row.get('current_streak_type', '') or '',
                    recent_form_points=row.get('recent_form_points_5', 0) or 0,
                    tactical_uncertainty=HONEYMOON_UNCERTAINTY.get(phase, 0.1),
                    job_security=row.get('job_security', 'stable') or 'stable',
                    rumored_departure=row.get('rumored_departure', False) or False,
                    recommended_action=action,
                    is_valid=True,
                    last_updated=row.get('updated_at')
                )

                # Cache
                self._coach_cache[cache_key] = impact
                self._cache_timestamps[cache_key] = datetime.now()

                return impact

        except Exception as e:
            logger.error(f"Error getting coach impact for {team_name}: {e}")
            return CoachImpact(team_name=team_name, is_valid=False)

    # ═══════════════════════════════════════════════════════════════
    # ABSENCE IMPACT
    # ═══════════════════════════════════════════════════════════════

    def get_absence_impact(self, team_name: str) -> AbsenceImpact:
        """
        Calcule l'impact des absences avec xG Lost et Cluster Factor.

        Sources:
        - cache/transfermarkt/{team}_injuries.json
        - cache/transfermarkt/{team}_scorers_v2.json
        """
        cache_key = f"absence_{team_name}"
        if self._is_cache_valid(cache_key) and cache_key in self._absence_cache:
            return self._absence_cache[cache_key]

        team_norm = _normalize_team_name(team_name)

        # Charger les blessés
        injuries_file = INJURIES_PATH / f"{team_norm}_injuries.json"
        if not injuries_file.exists():
            logger.warning(f"No injuries file for {team_name}: {injuries_file}")
            return AbsenceImpact(team_name=team_name, is_valid=False)

        try:
            with open(injuries_file, 'r') as f:
                injuries = json.load(f)
        except Exception as e:
            logger.error(f"Error loading injuries for {team_name}: {e}")
            return AbsenceImpact(team_name=team_name, is_valid=False)

        if not injuries:
            return AbsenceImpact(team_name=team_name, missing_count=0, is_valid=True)

        # Charger les scorers pour croiser
        scorers_file = SCORERS_PATH / f"{team_norm}_scorers_v2.json"
        scorers = {}
        if scorers_file.exists():
            try:
                with open(scorers_file, 'r') as f:
                    scorers_data = json.load(f)
                    if isinstance(scorers_data, list):
                        for s in scorers_data:
                            name = s.get('name') or s.get('player_name', '')
                            if name:
                                scorers[name] = s
                    elif isinstance(scorers_data, dict):
                        scorers = scorers_data
            except Exception as e:
                logger.warning(f"Error loading scorers for {team_name}: {e}")

        # Analyser les absences avec données enrichies
        missing_players = []
        total_xg_lost = 0.0
        positions_out = []
        top_scorer_absent = False
        top_assister_absent = False
        goalkeeper_absent = False
        key_defender_absent = False

        scorer_names = list(scorers.keys())

        for injury in injuries:
            player_name = injury.get('player_name', '')
            if not player_name:
                continue

            # Récupérer position depuis FBRef
            position = self._get_player_position(player_name, team_name)
            positions_out.append(position)

            # Récupérer xG depuis goalscorer_profiles
            xg_per_90 = self._get_player_xg(player_name, team_name)
            total_xg_lost += xg_per_90 * 0.8  # Pondération titulaire estimée

            # Fallback: utiliser scorers_v2 pour goals/assists si disponible
            matched_name = _fuzzy_match_player(player_name, scorer_names) if scorer_names else None
            player_stats = scorers.get(matched_name, {}) if matched_name else {}

            goals = int(player_stats.get('goals', 0) or 0)
            assists = int(player_stats.get('assists', 0) or 0)

            # Si pas de xG mais des goals, estimer
            if xg_per_90 == 0 and goals > 0:
                matches = int(player_stats.get('matches', 1) or 1)
                xg_per_90 = (goals / matches) * 0.08  # Estimation conservative
                total_xg_lost += xg_per_90

            # Key players detection
            if goals >= 5:
                top_scorer_absent = True
            if assists >= 3:
                top_assister_absent = True
            if position == "Goalkeeper":
                goalkeeper_absent = True
            if position in ("Centre-Back", "Defensive Midfield"):
                key_defender_absent = True

            missing_players.append({
                "name": player_name,
                "matched_name": matched_name,
                "position": position,
                "xg_per_90": round(xg_per_90, 3),
                "goals": goals,
                "assists": assists
            })

        # Calculer Cluster Factors
        def_cluster, mid_cluster, att_cluster = _calculate_cluster_factor(positions_out)

        # Compter par ligne
        defenders_out = sum(1 for p in positions_out if p in DEFENDER_POSITIONS)
        midfielders_out = sum(1 for p in positions_out if p in MIDFIELDER_POSITIONS)
        attackers_out = sum(1 for p in positions_out if p in ATTACKER_POSITIONS)

        # Data freshness
        freshness = None
        if injuries and 'scraped_at' in injuries[0]:
            try:
                freshness = datetime.fromisoformat(injuries[0]['scraped_at'].replace('Z', '+00:00'))
            except:
                pass

        impact = AbsenceImpact(
            team_name=team_name,
            missing_count=len(injuries),
            missing_players=missing_players,
            total_xg_lost=round(total_xg_lost, 2),
            team_xg_percentage_lost=0.0,  # Nécessite team total xG
            top_scorer_absent=top_scorer_absent,
            top_assister_absent=top_assister_absent,
            key_defender_absent=key_defender_absent,
            goalkeeper_absent=goalkeeper_absent,
            defensive_cluster_factor=def_cluster,
            midfield_cluster_factor=mid_cluster,
            attack_cluster_factor=att_cluster,
            defenders_out=defenders_out,
            midfielders_out=midfielders_out,
            attackers_out=attackers_out,
            is_valid=True,
            data_freshness=freshness
        )

        # Cache
        self._absence_cache[cache_key] = impact
        self._cache_timestamps[cache_key] = datetime.now()

        return impact

    # ═══════════════════════════════════════════════════════════════
    # FATIGUE IMPACT
    # ═══════════════════════════════════════════════════════════════

    def get_fatigue_impact(
        self,
        team_name: str,
        match_date: datetime = None
    ) -> FatigueImpact:
        """
        Calcule l'impact de la fatigue avec zones et rotation probability.

        Sources:
        - Table match_results (commence_time)
        """
        if match_date is None:
            match_date = datetime.now()

        cache_key = f"fatigue_{team_name}_{match_date.date()}"
        if self._is_cache_valid(cache_key) and cache_key in self._fatigue_cache:
            return self._fatigue_cache[cache_key]

        conn = self._get_db_connection()
        if not conn:
            return FatigueImpact(team_name=team_name, is_valid=False)

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Dernier match
                cur.execute("""
                    SELECT commence_time, league,
                           CASE WHEN home_team ILIKE %s THEN 'home' ELSE 'away' END as side
                    FROM match_results
                    WHERE (home_team ILIKE %s OR away_team ILIKE %s)
                      AND commence_time < %s
                      AND is_finished = true
                    ORDER BY commence_time DESC
                    LIMIT 1
                """, (f"%{team_name}%", f"%{team_name}%", f"%{team_name}%", match_date))

                last_match = cur.fetchone()

                if not last_match:
                    logger.warning(f"No previous match found for {team_name}")
                    return FatigueImpact(
                        team_name=team_name,
                        fatigue_zone="OPTIMAL",
                        is_valid=True,
                        confidence="LOW"
                    )

                last_match_time = last_match['commence_time']
                hours_since = (match_date - last_match_time).total_seconds() / 3600

                # Matches dans les derniers jours
                matches_7 = 1
                matches_14 = 2
                matches_21 = 3

                for days, attr_name in [(7, 'matches_7'), (14, 'matches_14'), (21, 'matches_21')]:
                    cur.execute("""
                        SELECT COUNT(*) as count
                        FROM match_results
                        WHERE (home_team ILIKE %s OR away_team ILIKE %s)
                          AND commence_time >= %s
                          AND commence_time < %s
                          AND is_finished = true
                    """, (f"%{team_name}%", f"%{team_name}%",
                          match_date - timedelta(days=days), match_date))
                    count = cur.fetchone()['count']
                    if attr_name == 'matches_7':
                        matches_7 = count
                    elif attr_name == 'matches_14':
                        matches_14 = count
                    else:
                        matches_21 = count

                # Déterminer zone et type de match
                zone = _get_fatigue_zone(hours_since)
                competition = last_match.get('league', '')
                match_type = COMPETITION_TYPE_MAPPING.get(competition, "UNKNOWN")
                rotation_prob = MATCH_TYPE_ROTATION_PROBABILITY.get(match_type, 0.30)

                # Calculer modifiers
                base_modifier = FATIGUE_MODIFIERS.get(zone, 0.0)
                # Ajuster si rotation probable
                effective_modifier = base_modifier * (1 - rotation_prob)

                impact = FatigueImpact(
                    team_name=team_name,
                    last_match_date=last_match_time,
                    hours_since_last_match=round(hours_since, 1),
                    fatigue_zone=zone,
                    matches_last_7_days=matches_7,
                    matches_last_14_days=matches_14,
                    matches_last_21_days=matches_21,
                    last_match_type=match_type,
                    last_match_competition=competition,
                    rotation_probability=rotation_prob,
                    base_fatigue_modifier=base_modifier,
                    effective_fatigue_modifier=round(effective_modifier, 3),
                    is_valid=True,
                    confidence="HIGH" if match_type != "UNKNOWN" else "MEDIUM"
                )

                # Cache
                self._fatigue_cache[cache_key] = impact
                self._cache_timestamps[cache_key] = datetime.now()

                return impact

        except Exception as e:
            logger.error(f"Error getting fatigue impact for {team_name}: {e}")
            return FatigueImpact(team_name=team_name, is_valid=False)

    # ═══════════════════════════════════════════════════════════════
    # COMBINED ADJUSTMENT
    # ═══════════════════════════════════════════════════════════════

    def get_combined_adjustment(
        self,
        team_name: str,
        match_date: datetime = None
    ) -> Dict[str, Any]:
        """
        Retourne un ajustement combiné de tous les facteurs runtime.

        Returns:
            Dict avec:
            - coach: CoachImpact
            - absences: AbsenceImpact
            - fatigue: FatigueImpact
            - combined_modifier: float (multiplicateur global)
            - risk_level: str (LOW, MEDIUM, HIGH)
            - recommendations: List[str]
        """
        coach = self.get_coach_impact(team_name)
        absences = self.get_absence_impact(team_name)
        fatigue = self.get_fatigue_impact(team_name, match_date)

        # Calculer modificateur combiné
        combined_mod = 1.0

        # Coach honeymoon effect
        if coach.is_valid and coach.is_in_bounce_period:
            combined_mod *= coach.honeymoon_factor

        # Absences impact (négatif)
        if absences.is_valid:
            absence_penalty = 1.0 - (absences.severity_score / 200)  # Max -50%
            combined_mod *= absence_penalty

        # Fatigue impact
        if fatigue.is_valid:
            combined_mod *= (1.0 + fatigue.effective_fatigue_modifier)

        # Risk level
        risk_score = 0
        if absences.severity_score > 50:
            risk_score += 2
        elif absences.severity_score > 25:
            risk_score += 1
        if fatigue.is_congested:
            risk_score += 2
        if coach.tactical_uncertainty > 0.5:
            risk_score += 1

        if risk_score >= 4:
            risk_level = "HIGH"
        elif risk_score >= 2:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # Recommendations
        recommendations = []
        if coach.recommended_action == "BOOST_VOLATILITY":
            recommendations.append("New manager bounce: Consider Over/BTTS")
        if absences.defensive_cluster_factor >= 0.5:
            recommendations.append("Defensive crisis: Over 2.5 value")
        if absences.top_scorer_absent:
            recommendations.append("Top scorer out: Reduce team goals expectations")
        if fatigue.is_congested:
            recommendations.append("Congested schedule: Performance may drop")
        if fatigue.is_rusty:
            recommendations.append("Long rest: May lack match rhythm")

        return {
            "team_name": team_name,
            "coach": coach,
            "absences": absences,
            "fatigue": fatigue,
            "combined_modifier": round(combined_mod, 3),
            "risk_level": risk_level,
            "recommendations": recommendations,
            "is_valid": coach.is_valid and absences.is_valid and fatigue.is_valid
        }

    def clear_cache(self):
        """Vide tous les caches."""
        self._coach_cache.clear()
        self._absence_cache.clear()
        self._fatigue_cache.clear()
        self._cache_timestamps.clear()
        clear_player_cache()
        logger.info("RuntimeCalculators cache cleared")


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def get_runtime_calculators() -> RuntimeCalculators:
    """Factory function pour obtenir le singleton RuntimeCalculators."""
    return RuntimeCalculators()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST STANDALONE
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 80)
    print("TEST RUNTIME CALCULATORS - SENIOR QUANT GRADE")
    print("=" * 80)

    calcs = RuntimeCalculators()

    # Test teams
    teams = ["Liverpool", "Arsenal", "Manchester City", "Chelsea", "Tottenham"]

    for team in teams:
        print(f"\n{'─' * 40}")
        print(f"  {team}")
        print(f"{'─' * 40}")

        # Coach
        coach = calcs.get_coach_impact(team)
        print(f"\n  COACH: {coach.coach_name}")
        print(f"   Tenure: {coach.tenure_days} jours ({coach.tenure_phase})")
        print(f"   Honeymoon Factor: {coach.honeymoon_factor:.2f}")
        print(f"   Tactical Uncertainty: {coach.tactical_uncertainty:.2f}")
        print(f"   Action: {coach.recommended_action}")

        # Absences
        absences = calcs.get_absence_impact(team)
        print(f"\n  ABSENCES: {absences.missing_count} joueurs")
        print(f"   xG Lost: {absences.total_xg_lost:.2f}")
        print(f"   Severity Score: {absences.severity_score:.1f}/100")
        print(f"   Defensive Cluster: {absences.defensive_cluster_factor:.2f}")
        if absences.top_scorer_absent:
            print(f"   TOP SCORER ABSENT")

        # Fatigue
        fatigue = calcs.get_fatigue_impact(team)
        print(f"\n  FATIGUE:")
        print(f"   Zone: {fatigue.fatigue_zone}")
        print(f"   Hours since last: {fatigue.hours_since_last_match:.1f}h")
        print(f"   Matches last 7 days: {fatigue.matches_last_7_days}")
        print(f"   Rotation Probability: {fatigue.rotation_probability:.0%}")
        print(f"   Performance Modifier: {fatigue.effective_fatigue_modifier:+.1%}")

        # Combined
        combined = calcs.get_combined_adjustment(team)
        print(f"\n  COMBINED:")
        print(f"   Modifier: {combined['combined_modifier']:.3f}")
        print(f"   Risk Level: {combined['risk_level']}")
        if combined['recommendations']:
            print(f"   Recommendations:")
            for rec in combined['recommendations']:
                print(f"      - {rec}")

    print("\n" + "=" * 80)
    print("TEST TERMINE")
    print("=" * 80)
