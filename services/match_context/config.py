"""
Configuration Match Context Calculator
═══════════════════════════════════════════════════════════════════════════
Tous les paramètres configurables du service.
═══════════════════════════════════════════════════════════════════════════
"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class MatchContextConfig:
    """Configuration complète du MatchContextCalculator."""

    # ═══════════════════════════════════════════════════════════════════
    # DATABASE
    # ═══════════════════════════════════════════════════════════════════
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "monps_db"
    DB_USER: str = "monps_user"
    DB_PASSWORD: str = "monps_secure_password_2024"

    # Tables
    MATCHES_TABLE: str = "match_results"  # Source des matchs passés
    CONTEXT_TABLE: str = "match_context"  # Table destination

    # ═══════════════════════════════════════════════════════════════════
    # REST THRESHOLDS (en jours)
    # ═══════════════════════════════════════════════════════════════════
    # Zone optimale de repos
    OPTIMAL_REST_MIN: int = 4    # Moins = fatigue commence
    OPTIMAL_REST_MAX: int = 7    # Plus = perte de rythme

    # Seuils critiques
    CRITICAL_REST: int = 3       # < 3 jours = CRITICAL (danger)
    TIRED_REST: int = 4          # < 4 jours = TIRED
    RUSTY_REST: int = 10         # > 10 jours = RUSTY (manque rythme)

    # ═══════════════════════════════════════════════════════════════════
    # PENALTIES & BONUSES (en jours effectifs)
    # ═══════════════════════════════════════════════════════════════════
    # Venue du dernier match
    HOME_VENUE_BONUS: float = 0.5        # Dernier match à domicile = repos
    AWAY_VENUE_PENALTY: float = -0.5     # Déplacement national = fatigue
    EUROPEAN_AWAY_PENALTY: float = -1.0  # Déplacement européen = fatigue++

    # Type de compétition
    CUP_ROTATION_BONUS: float = 1.0      # Match coupe = rotation probable

    # Intensité match (non implémenté pour V1)
    EXTRA_TIME_PENALTY: float = -1.0     # Prolongations = fatigue++

    # ═══════════════════════════════════════════════════════════════════
    # COMPETITIONS
    # ═══════════════════════════════════════════════════════════════════
    EUROPEAN_COMPETITIONS: List[str] = field(default_factory=lambda: [
        'Champions League',
        'UEFA Champions League',
        'Europa League',
        'UEFA Europa League',
        'Conference League',
        'UEFA Conference League'
    ])

    CUP_COMPETITIONS: List[str] = field(default_factory=lambda: [
        'FA Cup',
        'League Cup',
        'Carabao Cup',
        'EFL Cup',
        'Copa del Rey',
        'DFB Pokal',
        'Coppa Italia',
        'Coupe de France',
        'Coupe de la Ligue'
    ])

    LEAGUE_COMPETITIONS: List[str] = field(default_factory=lambda: [
        'Premier League',
        'EPL',
        'La Liga',
        'Bundesliga',
        'Serie A',
        'Ligue 1',
        'soccer_epl',
        'soccer_spain_la_liga',
        'soccer_germany_bundesliga',
        'soccer_italy_serie_a',
        'soccer_france_ligue_one'
    ])

    # ═══════════════════════════════════════════════════════════════════
    # REST STATUS LABELS
    # ═══════════════════════════════════════════════════════════════════
    STATUS_CRITICAL: str = "CRITICAL"
    STATUS_TIRED: str = "TIRED"
    STATUS_NORMAL: str = "NORMAL"
    STATUS_FRESH: str = "FRESH"
    STATUS_RUSTY: str = "RUSTY"

    # ═══════════════════════════════════════════════════════════════════
    # DELTA SIGNIFICANCE
    # ═══════════════════════════════════════════════════════════════════
    DELTA_MINOR_THRESHOLD: float = 1.0   # < 1 jour = négligeable
    DELTA_MODERATE_THRESHOLD: float = 2.0  # 1-2 jours = modéré
    # > 2 jours = MAJOR advantage


# Instance par défaut
DEFAULT_CONFIG = MatchContextConfig()
