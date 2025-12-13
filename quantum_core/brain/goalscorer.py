"""
Goalscorer Calculator - Hedge Fund Grade
═══════════════════════════════════════════════════════════════════════════

MARCHÉS:
    - Anytime Goalscorer (joueur marque au moins 1 but)
    - First Goalscorer (joueur marque le premier but du match)
    - Last Goalscorer (joueur marque le dernier but du match)

DONNÉES:
    - goalscorer_profiles_2025.json (876 joueurs)
    - first_goalscorer_stats.json (96 équipes)

FORMULES:
    Anytime: P = 1 - e^(-λ) où λ = xG_match_joueur
    First GS: P = P(Équipe 1er) × P(Joueur | Équipe) × timing_adj
    Last GS: P = P(Match a buts) × last_goal_rate × clutch_factor

Auteur: Mon_PS Quant Team
Version: 1.0.0
Date: 13 Décembre 2025
"""

import json
import math
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from functools import lru_cache

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

DATA_DIR = Path("/home/Mon_ps/data/goals")
PROFILES_FILE = DATA_DIR / "goalscorer_profiles_2025.json"
TEAM_STATS_FILE = DATA_DIR / "first_goalscorer_stats.json"

# Liquidity Tax par marché
LIQUIDITY_TAX = {
    "anytime": 0.04,      # 4% - Marché populaire mais variance
    "first_gs": 0.06,     # 6% - Plus rare, moins liquide
    "last_gs": 0.06,      # 6% - Similaire à first
}

# Min Edge par marché
MIN_EDGE = {
    "anytime": 0.05,      # 5%
    "first_gs": 0.08,     # 8% - Plus de variance
    "last_gs": 0.08,      # 8%
}

# Minutes attendues par défaut (si pas de données)
DEFAULT_MINUTES = 75  # Titulaire standard
SUB_MINUTES = 25      # Remplaçant typique

# Timing adjustments
TIMING_ADJUSTMENTS = {
    "EARLY_BIRD": {"first": 1.3, "last": 0.7},   # +30% first, -30% last
    "CLUTCH": {"first": 0.7, "last": 1.4},       # -30% first, +40% last
    "DIESEL": {"first": 0.8, "last": 1.2},       # -20% first, +20% last
    "CONSISTENT": {"first": 1.0, "last": 1.0},   # Neutre
}


# ═══════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PlayerGoalscorerOdds:
    """Probabilités goalscorer pour un joueur."""
    player_id: str
    player_name: str
    team_name: str

    # Probabilités brutes
    anytime_prob: float = 0.0
    first_gs_prob: float = 0.0
    last_gs_prob: float = 0.0

    # Fair odds (1/prob)
    anytime_fair_odds: float = 0.0
    first_gs_fair_odds: float = 0.0
    last_gs_fair_odds: float = 0.0

    # Données utilisées
    goals_per_90: float = 0.0
    xg_per_90: float = 0.0
    minutes_expected: int = 0
    first_goal_rate: float = 0.0
    timing_profile: str = ""

    # Confidence
    confidence: float = 0.0  # Basé sur sample size


@dataclass
class MatchGoalscorerAnalysis:
    """Analyse goalscorer complète pour un match."""
    home_team: str
    away_team: str

    # Probabilités équipes
    home_score_first_prob: float = 0.0
    away_score_first_prob: float = 0.0
    no_goals_prob: float = 0.0

    # Expected goals
    expected_home_goals: float = 0.0
    expected_away_goals: float = 0.0
    expected_total_goals: float = 0.0

    # Top joueurs par marché
    anytime_rankings: List[PlayerGoalscorerOdds] = field(default_factory=list)
    first_gs_rankings: List[PlayerGoalscorerOdds] = field(default_factory=list)
    last_gs_rankings: List[PlayerGoalscorerOdds] = field(default_factory=list)

    # Stats
    players_analyzed: int = 0


# ═══════════════════════════════════════════════════════════════════════════
# DATA LOADER
# ═══════════════════════════════════════════════════════════════════════════

class GoalscorerDataLoader:
    """Charge et cache les données goalscorer."""

    _instance = None
    _profiles: Dict = None
    _team_stats: Dict = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self) -> bool:
        """Charge les données."""
        if self._profiles is not None:
            return True

        try:
            # Load profiles
            if PROFILES_FILE.exists():
                with open(PROFILES_FILE, 'r', encoding='utf-8') as f:
                    self._profiles = json.load(f)
                logger.info(f"Loaded {len(self._profiles)} goalscorer profiles")
            else:
                logger.warning(f"Profiles file not found: {PROFILES_FILE}")
                self._profiles = {}

            # Load team stats
            if TEAM_STATS_FILE.exists():
                with open(TEAM_STATS_FILE, 'r', encoding='utf-8') as f:
                    self._team_stats = json.load(f)
                logger.info(f"Loaded {len(self._team_stats)} team first GS stats")
            else:
                logger.warning(f"Team stats file not found: {TEAM_STATS_FILE}")
                self._team_stats = {}

            return True

        except Exception as e:
            logger.error(f"Error loading goalscorer data: {e}")
            self._profiles = {}
            self._team_stats = {}
            return False

    def get_team_players(self, team_name: str) -> List[Dict]:
        """Retourne tous les joueurs d'une équipe."""
        if self._profiles is None:
            self.load()

        players = []
        team_lower = team_name.lower()

        for player_id, profile in self._profiles.items():
            if profile.get("team_name", "").lower() == team_lower:
                profile["player_id"] = player_id
                players.append(profile)

        # Trier par total_goals desc
        players.sort(key=lambda p: p.get("total_goals", 0), reverse=True)
        return players

    def get_team_first_gs_stats(self, team_name: str) -> Optional[Dict]:
        """Retourne les stats First GS d'une équipe."""
        if self._team_stats is None:
            self.load()

        # Chercher par nom exact ou partiel
        team_lower = team_name.lower()

        for name, stats in self._team_stats.items():
            if name.lower() == team_lower or team_lower in name.lower():
                return stats

        return None

    def get_player_profile(self, player_id: str) -> Optional[Dict]:
        """Retourne le profil d'un joueur."""
        if self._profiles is None:
            self.load()
        return self._profiles.get(player_id)


# ═══════════════════════════════════════════════════════════════════════════
# CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════

class GoalscorerCalculator:
    """
    Calcule les probabilités Anytime/First/Last Goalscorer.

    Utilise:
        - Profils individuels des joueurs (goals_per_90, timing, etc.)
        - Stats équipes (scored_first_rate, top_first_scorers)
        - xG du match pour ajuster les probabilités
    """

    def __init__(self):
        self.data = GoalscorerDataLoader()
        self.data.load()
        logger.info("GoalscorerCalculator initialisé")

    # ─────────────────────────────────────────────────────────────────────
    # CORE CALCULATIONS
    # ─────────────────────────────────────────────────────────────────────

    def _calc_anytime_prob(
        self,
        goals_per_90: float,
        xg_per_90: float,
        minutes_expected: int,
        team_xg_match: float,
        team_xg_season_avg: float = 1.5
    ) -> float:
        """
        Calcule P(Anytime Goalscorer).

        Formule: P = 1 - e^(-λ)
        où λ = (player_goal_rate) × (minutes/90) × (match_xg_factor)

        Args:
            goals_per_90: Buts par 90 minutes du joueur
            xg_per_90: xG par 90 minutes du joueur
            minutes_expected: Minutes attendues dans ce match
            team_xg_match: xG de l'équipe pour ce match
            team_xg_season_avg: xG moyen de l'équipe en saison
        """
        if goals_per_90 <= 0 or minutes_expected <= 0:
            return 0.0

        # Utiliser le max entre goals réels et xG (éviter sous-estimation)
        player_rate = max(goals_per_90, xg_per_90 * 0.9)  # 90% de xG comme floor

        # Ajuster par le ratio xG match vs saison
        if team_xg_season_avg > 0:
            match_factor = team_xg_match / team_xg_season_avg
            match_factor = max(0.5, min(2.0, match_factor))  # Clip entre 0.5 et 2.0
        else:
            match_factor = 1.0

        # Lambda pour Poisson
        lambda_player = (player_rate / 90) * minutes_expected * match_factor

        # P(au moins 1 but) = 1 - P(0 but) = 1 - e^(-λ)
        prob = 1 - math.exp(-lambda_player)

        return min(0.95, max(0.001, prob))  # Clip entre 0.1% et 95%

    def _calc_first_gs_prob(
        self,
        player_profile: Dict,
        team_score_first_prob: float,
        team_players: List[Dict],
        minutes_expected: int
    ) -> float:
        """
        Calcule P(First Goalscorer).

        Formule:
        P(First GS) = P(Équipe score 1er)
                    × P(Joueur | Équipe score 1er)
                    × timing_adjustment
                    × minutes_adjustment

        Args:
            player_profile: Profil du joueur
            team_score_first_prob: P(équipe marque en premier)
            team_players: Liste des joueurs de l'équipe
            minutes_expected: Minutes attendues
        """
        if not player_profile or team_score_first_prob <= 0:
            return 0.0

        # P(Joueur | Équipe score 1er) basé sur first_goal_rate historique
        first_rate = player_profile.get("first_goal_rate", 0)
        total_goals = player_profile.get("total_goals", 0)

        if first_rate <= 0 or total_goals < 2:
            # Fallback: utiliser la part des buts de l'équipe
            team_total = sum(p.get("total_goals", 0) for p in team_players)
            if team_total > 0:
                share = total_goals / team_total
                first_rate = share  # Approximation simpliste
            else:
                return 0.0

        # Timing adjustment
        timing_profile = player_profile.get("timing_profile", "CONSISTENT")
        timing_adj = TIMING_ADJUSTMENTS.get(timing_profile, {}).get("first", 1.0)

        # Minutes adjustment (moins de minutes = moins de chances)
        minutes_adj = min(1.0, minutes_expected / 90)

        # Calcul final
        prob = team_score_first_prob * first_rate * timing_adj * minutes_adj

        return min(0.50, max(0.001, prob))  # Clip (max 50% pour un seul joueur)

    def _calc_last_gs_prob(
        self,
        player_profile: Dict,
        match_has_goals_prob: float,
        team_players: List[Dict],
        minutes_expected: int
    ) -> float:
        """
        Calcule P(Last Goalscorer).

        Formule:
        P(Last GS) = P(Match a des buts)
                   × P(Joueur | buts marqués)
                   × clutch_factor (timing 76-90')

        Args:
            player_profile: Profil du joueur
            match_has_goals_prob: P(au moins 1 but dans le match)
            team_players: Liste des joueurs de l'équipe
            minutes_expected: Minutes attendues
        """
        if not player_profile or match_has_goals_prob <= 0:
            return 0.0

        # Utiliser last_goal_rate si disponible
        last_rate = player_profile.get("last_goal_rate", 0)
        total_goals = player_profile.get("total_goals", 0)

        if last_rate <= 0 or total_goals < 2:
            # Fallback: utiliser la part des buts
            team_total = sum(p.get("total_goals", 0) for p in team_players)
            if team_total > 0:
                share = total_goals / team_total
                last_rate = share
            else:
                return 0.0

        # Timing adjustment (CLUTCH players score more late goals)
        timing_profile = player_profile.get("timing_profile", "CONSISTENT")
        timing_adj = TIMING_ADJUSTMENTS.get(timing_profile, {}).get("last", 1.0)

        # Clutch factor basé sur pct_76_90
        pct_late = player_profile.get("pct_76_90", 0.15)  # Default 15%
        clutch_factor = 1.0 + (pct_late - 0.15) * 2  # Bonus si > 15%
        clutch_factor = max(0.7, min(1.5, clutch_factor))

        # Minutes adjustment
        minutes_adj = min(1.0, minutes_expected / 90)

        # Calcul final
        prob = match_has_goals_prob * last_rate * timing_adj * clutch_factor * minutes_adj * 0.5
        # × 0.5 car on partage avec l'autre équipe

        return min(0.40, max(0.001, prob))

    # ─────────────────────────────────────────────────────────────────────
    # MAIN ANALYZE
    # ─────────────────────────────────────────────────────────────────────

    def analyze_match(
        self,
        home_team: str,
        away_team: str,
        expected_home_goals: float,
        expected_away_goals: float,
        top_n: int = 10
    ) -> MatchGoalscorerAnalysis:
        """
        Analyse complète des marchés goalscorer pour un match.

        Args:
            home_team: Nom équipe domicile
            away_team: Nom équipe extérieur
            expected_home_goals: xG domicile
            expected_away_goals: xG extérieur
            top_n: Nombre de joueurs à retourner par marché

        Returns:
            MatchGoalscorerAnalysis avec rankings par marché
        """
        analysis = MatchGoalscorerAnalysis(
            home_team=home_team,
            away_team=away_team,
            expected_home_goals=expected_home_goals,
            expected_away_goals=expected_away_goals,
            expected_total_goals=expected_home_goals + expected_away_goals
        )

        # P(au moins 1 but) = 1 - P(0-0)
        p_no_goals = math.exp(-(expected_home_goals + expected_away_goals))
        analysis.no_goals_prob = p_no_goals
        match_has_goals_prob = 1 - p_no_goals

        # P(équipe score en premier)
        # Approximation: proportionnel aux xG
        total_xg = expected_home_goals + expected_away_goals
        if total_xg > 0:
            analysis.home_score_first_prob = (expected_home_goals / total_xg) * match_has_goals_prob
            analysis.away_score_first_prob = (expected_away_goals / total_xg) * match_has_goals_prob

        # Enrichir avec stats équipe si disponibles
        home_stats = self.data.get_team_first_gs_stats(home_team)
        away_stats = self.data.get_team_first_gs_stats(away_team)

        if home_stats and home_stats.get("scored_first_rate", 0) > 0:
            # Combiner notre estimation avec les données historiques (50/50)
            hist_rate = home_stats["scored_first_rate"]
            analysis.home_score_first_prob = (analysis.home_score_first_prob + hist_rate * match_has_goals_prob) / 2

        if away_stats and away_stats.get("scored_first_rate", 0) > 0:
            hist_rate = away_stats["scored_first_rate"]
            analysis.away_score_first_prob = (analysis.away_score_first_prob + hist_rate * match_has_goals_prob) / 2

        # Récupérer les joueurs
        home_players = self.data.get_team_players(home_team)
        away_players = self.data.get_team_players(away_team)

        all_player_odds = []

        # Analyser joueurs domicile
        for player in home_players[:15]:  # Top 15 buteurs
            odds = self._analyze_player(
                player=player,
                team_name=home_team,
                team_xg_match=expected_home_goals,
                team_score_first_prob=analysis.home_score_first_prob,
                team_players=home_players,
                match_has_goals_prob=match_has_goals_prob
            )
            if odds and odds.anytime_prob > 0.01:  # Au moins 1%
                all_player_odds.append(odds)

        # Analyser joueurs extérieur
        for player in away_players[:15]:
            odds = self._analyze_player(
                player=player,
                team_name=away_team,
                team_xg_match=expected_away_goals,
                team_score_first_prob=analysis.away_score_first_prob,
                team_players=away_players,
                match_has_goals_prob=match_has_goals_prob
            )
            if odds and odds.anytime_prob > 0.01:
                all_player_odds.append(odds)

        analysis.players_analyzed = len(all_player_odds)

        # Trier et assigner les rankings
        analysis.anytime_rankings = sorted(
            all_player_odds,
            key=lambda x: x.anytime_prob,
            reverse=True
        )[:top_n]

        analysis.first_gs_rankings = sorted(
            all_player_odds,
            key=lambda x: x.first_gs_prob,
            reverse=True
        )[:top_n]

        analysis.last_gs_rankings = sorted(
            all_player_odds,
            key=lambda x: x.last_gs_prob,
            reverse=True
        )[:top_n]

        logger.info(
            f"Goalscorer analysis: {home_team} vs {away_team} - "
            f"{len(all_player_odds)} players, "
            f"Home 1st: {analysis.home_score_first_prob:.1%}, "
            f"Away 1st: {analysis.away_score_first_prob:.1%}"
        )

        return analysis

    def _analyze_player(
        self,
        player: Dict,
        team_name: str,
        team_xg_match: float,
        team_score_first_prob: float,
        team_players: List[Dict],
        match_has_goals_prob: float
    ) -> Optional[PlayerGoalscorerOdds]:
        """Analyse un joueur individuel."""

        player_id = player.get("player_id", "")
        player_name = player.get("player_name", "Unknown")

        goals_per_90 = player.get("goals_per_90", 0)
        xg_per_90 = player.get("xg_per_90", 0)
        total_goals = player.get("total_goals", 0)
        total_xg = player.get("total_xg", 0)
        minutes_played = player.get("minutes_played", 0)
        matches_with_goal = player.get("matches_with_goal", 0)

        # Estimer goals_per_90 si non disponible (pas de FBRef)
        if goals_per_90 <= 0 and total_goals > 0:
            # Estimation: suppose ~70 min par match en moyenne pour buteurs
            estimated_minutes = matches_with_goal * 70 if matches_with_goal > 0 else total_goals * 90
            goals_per_90 = (total_goals / estimated_minutes) * 90 if estimated_minutes > 0 else 0
            logger.debug(f"{player_name}: estimated goals_per_90 = {goals_per_90:.3f}")

        # Estimer xg_per_90 si non disponible
        if xg_per_90 <= 0 and total_xg > 0:
            estimated_minutes = matches_with_goal * 70 if matches_with_goal > 0 else total_goals * 90
            xg_per_90 = (total_xg / estimated_minutes) * 90 if estimated_minutes > 0 else 0

        # Estimer minutes attendues
        if minutes_played >= 450:  # ~5 matchs complets
            avg_minutes = minutes_played / max(1, matches_with_goal * 1.5)
            minutes_expected = min(90, max(30, avg_minutes))
        else:
            minutes_expected = DEFAULT_MINUTES if total_goals >= 3 else SUB_MINUTES

        # Confidence basée sur sample size
        confidence = min(1.0, total_goals / 10)  # Max confidence à 10 buts

        # Skip si pas assez de données
        if total_goals < 1 and xg_per_90 < 0.1:
            return None

        # Calculer probabilités
        anytime = self._calc_anytime_prob(
            goals_per_90=goals_per_90,
            xg_per_90=xg_per_90,
            minutes_expected=int(minutes_expected),
            team_xg_match=team_xg_match
        )

        first_gs = self._calc_first_gs_prob(
            player_profile=player,
            team_score_first_prob=team_score_first_prob,
            team_players=team_players,
            minutes_expected=int(minutes_expected)
        )

        last_gs = self._calc_last_gs_prob(
            player_profile=player,
            match_has_goals_prob=match_has_goals_prob,
            team_players=team_players,
            minutes_expected=int(minutes_expected)
        )

        # Créer odds object
        odds = PlayerGoalscorerOdds(
            player_id=player_id,
            player_name=player_name,
            team_name=team_name,
            anytime_prob=anytime,
            first_gs_prob=first_gs,
            last_gs_prob=last_gs,
            anytime_fair_odds=1/anytime if anytime > 0 else 0,
            first_gs_fair_odds=1/first_gs if first_gs > 0 else 0,
            last_gs_fair_odds=1/last_gs if last_gs > 0 else 0,
            goals_per_90=goals_per_90,
            xg_per_90=xg_per_90,
            minutes_expected=int(minutes_expected),
            first_goal_rate=player.get("first_goal_rate", 0),
            timing_profile=player.get("timing_profile", ""),
            confidence=confidence
        )

        return odds


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════

_calculator_instance = None

def get_goalscorer_calculator() -> GoalscorerCalculator:
    """Retourne l'instance singleton."""
    global _calculator_instance
    if _calculator_instance is None:
        _calculator_instance = GoalscorerCalculator()
    return _calculator_instance


# ═══════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    calc = get_goalscorer_calculator()

    print("=" * 70)
    print("TEST: Liverpool vs Manchester City")
    print("=" * 70)

    analysis = calc.analyze_match(
        home_team="Liverpool",
        away_team="Manchester City",
        expected_home_goals=1.8,
        expected_away_goals=2.0,
        top_n=5
    )

    print(f"\nMATCH INFO:")
    print(f"   xG: {analysis.expected_home_goals:.2f} - {analysis.expected_away_goals:.2f}")
    print(f"   Home scores first: {analysis.home_score_first_prob:.1%}")
    print(f"   Away scores first: {analysis.away_score_first_prob:.1%}")
    print(f"   No goals (0-0): {analysis.no_goals_prob:.1%}")
    print(f"   Players analyzed: {analysis.players_analyzed}")

    print(f"\nANYTIME GOALSCORER (Top 5):")
    for i, p in enumerate(analysis.anytime_rankings[:5], 1):
        print(f"   {i}. {p.player_name:20s} ({p.team_name:15s}) - "
              f"{p.anytime_prob:5.1%} (Fair: {p.anytime_fair_odds:5.1f})")

    print(f"\nFIRST GOALSCORER (Top 5):")
    for i, p in enumerate(analysis.first_gs_rankings[:5], 1):
        print(f"   {i}. {p.player_name:20s} ({p.team_name:15s}) - "
              f"{p.first_gs_prob:5.1%} (Fair: {p.first_gs_fair_odds:5.1f})")

    print(f"\nLAST GOALSCORER (Top 5):")
    for i, p in enumerate(analysis.last_gs_rankings[:5], 1):
        print(f"   {i}. {p.player_name:20s} ({p.team_name:15s}) - "
              f"{p.last_gs_prob:5.1%} (Fair: {p.last_gs_fair_odds:5.1f})")

    # Test avec un autre match
    print("\n" + "=" * 70)
    print("TEST: Bayern Munich vs Dortmund")
    print("=" * 70)

    analysis2 = calc.analyze_match(
        home_team="Bayern Munich",
        away_team="Borussia Dortmund",
        expected_home_goals=2.5,
        expected_away_goals=1.3,
        top_n=5
    )

    print(f"\nANYTIME GOALSCORER (Top 5):")
    for i, p in enumerate(analysis2.anytime_rankings[:5], 1):
        print(f"   {i}. {p.player_name:20s} ({p.team_name:15s}) - "
              f"{p.anytime_prob:5.1%} (Fair: {p.anytime_fair_odds:5.1f})")

    print(f"\nFIRST GOALSCORER (Top 5):")
    for i, p in enumerate(analysis2.first_gs_rankings[:5], 1):
        print(f"   {i}. {p.player_name:20s} ({p.team_name:15s}) - "
              f"{p.first_gs_prob:5.1%} (Fair: {p.first_gs_fair_odds:5.1f})")
