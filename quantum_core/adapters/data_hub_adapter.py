"""
DataHubAdapter - Adapter Pattern Hedge Fund Grade

PRINCIPE:
    Expose la MEME interface que DataHub (quantum/chess_engine/core/data_hub.py)
    mais utilise DataOrchestrator en interne.

AVANTAGES:
    - QuantumBrain et 6 Engines = AUCUNE modification requise
    - DataOrchestrator = Source de verite unique
    - Backward compatible
    - Testable progressivement

INTERFACE REQUISE (par les engines):
    - get_team_data(team_name) -> Dict
    - get_market_profile(team, location) -> Dict
    - get_corner_dna(team) -> Dict
    - get_card_dna(team) -> Dict
    - get_referee_data(referee) -> Dict
    - is_specialist(team, market, location) -> Optional[Dict]

Version: 1.0.0
Date: 13 Decembre 2025
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from functools import lru_cache
from dataclasses import dataclass

# Configuration path
PROJECT_ROOT = Path("/home/Mon_ps")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TeamData:
    """Structure de donnees equipe compatible avec DataHub."""
    team_name: str
    canonical_name: str = ""

    # Context DNA
    xg_for: float = 1.4
    xg_against: float = 1.2
    win_rate: float = 0.45
    draw_rate: float = 0.25
    loss_rate: float = 0.30
    home_win_rate: float = 0.50
    away_win_rate: float = 0.35

    # Tactical
    tactical_profile: str = "BALANCED"
    profile_confidence: float = 0.5
    formation: str = "4-3-3"
    pressing_intensity: float = 0.5
    possession_preference: float = 0.5

    # Market DNA
    btts_rate: float = 0.50
    over25_rate: float = 0.55
    clean_sheet_rate: float = 0.30
    failed_to_score_rate: float = 0.20

    # Corner DNA
    corners_for_avg: float = 5.0
    corners_against_avg: float = 5.0
    corner_efficiency: float = 0.03

    # Card DNA
    yellow_cards_avg: float = 1.8
    red_cards_avg: float = 0.05
    fouls_committed_avg: float = 12.0

    # Tier
    tier: str = "STANDARD"

    def to_dict(self) -> Dict:
        """Convertit en dictionnaire compatible DataHub."""
        return {
            "team_name": self.team_name,
            "canonical_name": self.canonical_name or self.team_name,

            # Context
            "xg_for": self.xg_for,
            "xg_against": self.xg_against,
            "xg": self.xg_for,  # Alias
            "win_rate": self.win_rate,
            "draw_rate": self.draw_rate,
            "loss_rate": self.loss_rate,
            "home_win_rate": self.home_win_rate,
            "away_win_rate": self.away_win_rate,

            # Tactical
            "tactical_profile": self.tactical_profile,
            "profile_confidence": self.profile_confidence,
            "formation": self.formation,
            "pressing_intensity": self.pressing_intensity,
            "possession_preference": self.possession_preference,

            # Market
            "btts_rate": self.btts_rate,
            "over25_rate": self.over25_rate,
            "clean_sheet_rate": self.clean_sheet_rate,
            "failed_to_score_rate": self.failed_to_score_rate,

            # Corner (flat)
            "corners_for_avg": self.corners_for_avg,
            "corners_against_avg": self.corners_against_avg,
            "corner_efficiency": self.corner_efficiency,

            # Card (flat)
            "yellow_cards_avg": self.yellow_cards_avg,
            "red_cards_avg": self.red_cards_avg,
            "fouls_committed_avg": self.fouls_committed_avg,

            # Tier
            "tier": self.tier,

            # DNA nested structure pour CornerEngine/CardEngine
            "dna": {
                "corner": {
                    "corners_for_avg": self.corners_for_avg,
                    "corners_against_avg": self.corners_against_avg,
                    "corner_efficiency": self.corner_efficiency,
                    "over_9_5_pct": 50,
                    "over_10_5_pct": 40,
                    "profile": "BALANCED",
                },
                "card": {
                    "yellows_for_avg": self.yellow_cards_avg,
                    "yellows_against_avg": 1.5,
                    "reds_per_game": self.red_cards_avg,
                    "over_3_5_cards_pct": 55,
                    "over_4_5_cards_pct": 40,
                    "discipline_score": 50,
                },
            },
        }


class DataHubAdapter:
    """
    Adapter qui expose l'interface DataHub mais utilise DataOrchestrator.

    Usage:
        adapter = DataHubAdapter()
        team_data = adapter.get_team_data("Liverpool")
        matchup = adapter.prepare_matchup_data("Liverpool", "Man City")
    """

    VERSION = "1.0.0"

    def __init__(self):
        """Initialise l'adapter avec lazy loading."""
        self._data_orchestrator = None
        self._classification_cache = {}
        self._stats = {
            "calls": 0,
            "cache_hits": 0,
            "fallbacks": 0
        }
        self.loaded = False
        self.data = {}  # Compatibilite DataHub
        self.market_profiles = {}
        self.team_dna = {}
        logger.info("DataHubAdapter initialise (lazy mode)")

    def _ensure_orchestrator(self):
        """Charge DataOrchestrator de maniere lazy."""
        if self._data_orchestrator is not None:
            return self._data_orchestrator

        try:
            from quantum_core.data.orchestrator import DataOrchestrator
            self._data_orchestrator = DataOrchestrator()
            logger.info("DataOrchestrator connecte via Adapter")
            return self._data_orchestrator
        except Exception as e:
            logger.warning(f"DataOrchestrator non disponible: {e}")
            return None

    def _load_classification(self) -> Dict:
        """Charge la classification V25."""
        if self._classification_cache:
            return self._classification_cache

        try:
            import json
            classif_path = PROJECT_ROOT / "data/quantum_v2/classification_results_v25.json"
            if classif_path.exists():
                with open(classif_path) as f:
                    data = json.load(f)
                    results = data.get("results", [])
                    # Convertir la liste en dict avec team comme cle
                    if isinstance(results, list):
                        self._classification_cache = {
                            item.get("team", ""): item
                            for item in results
                            if item.get("team")
                        }
                    else:
                        self._classification_cache = results
                    logger.info(f"Classification V25 chargee ({len(self._classification_cache)} equipes)")
        except Exception as e:
            logger.warning(f"Classification non disponible: {e}")

        return self._classification_cache

    def load_all(self) -> None:
        """Charge toutes les sources - compatibilite DataHub."""
        self._ensure_orchestrator()
        self._load_classification()
        self.loaded = True
        logger.info("DataHubAdapter: load_all() complete")

    # ===================================================================
    # INTERFACE DATAHUB (Compatible avec les engines existants)
    # ===================================================================

    @lru_cache(maxsize=100)
    def get_team_data(self, team_name: str) -> Dict[str, Any]:
        """
        Recupere les donnees completes d'une equipe.

        Interface compatible avec DataHub.get_team_data()
        """
        self._stats["calls"] += 1

        # Creer structure de base
        team_data = TeamData(team_name=team_name)

        # Essayer DataOrchestrator
        orchestrator = self._ensure_orchestrator()
        if orchestrator:
            try:
                dna = orchestrator.get_team_dna(team_name)
                if dna and isinstance(dna, dict):
                    # Context DNA
                    team_data.canonical_name = dna.get("team_name", team_name)
                    team_data.xg_for = float(dna.get("xg_for", dna.get("xg", 1.4)))
                    team_data.xg_against = float(dna.get("xg_against", 1.2))
                    team_data.win_rate = float(dna.get("win_rate", 0.45))
                    team_data.tier = dna.get("tier", "STANDARD")

                    # Home/Away splits
                    if "context" in dna:
                        ctx = dna["context"]
                        team_data.home_win_rate = float(ctx.get("home_win_rate", 0.50))
                        team_data.away_win_rate = float(ctx.get("away_win_rate", 0.35))

                    # Market DNA
                    if "betting" in dna:
                        betting = dna["betting"]
                        team_data.btts_rate = float(betting.get("btts_rate", 0.50))
                        team_data.over25_rate = float(betting.get("over25_rate", 0.55))
                        team_data.clean_sheet_rate = float(betting.get("clean_sheet_rate", 0.30))

                    # Corner DNA (depuis TSE)
                    if "corner_dna" in dna:
                        corner_dna = dna["corner_dna"]
                        team_data.corners_for_avg = float(corner_dna.get("corners_for_avg", 5.0))
                        team_data.corners_against_avg = float(corner_dna.get("corners_against_avg", 5.0))

                    # Card DNA (depuis TSE)
                    if "card_dna" in dna:
                        card_dna = dna["card_dna"]
                        team_data.yellow_cards_avg = float(card_dna.get("yellows_for_avg", 1.8))
                        team_data.fouls_committed_avg = float(card_dna.get("fouls_for_avg", 12.0))

                    # Tactical
                    if "tactical" in dna:
                        tactical = dna["tactical"]
                        team_data.formation = tactical.get("formation", "4-3-3")
                        team_data.pressing_intensity = float(tactical.get("pressing", 0.5))
                        team_data.possession_preference = float(tactical.get("possession", 0.5))

                    logger.debug(f"Team data from DataOrchestrator: {team_name}")

            except Exception as e:
                logger.debug(f"DataOrchestrator error for {team_name}: {e}")
                self._stats["fallbacks"] += 1

        # Enrichir avec Classification V25
        classification = self._load_classification()
        team_lower = team_name.lower()
        for team, info in classification.items():
            if team.lower() == team_lower or team_lower in team.lower():
                team_data.tactical_profile = info.get("profile", "BALANCED")
                team_data.profile_confidence = float(info.get("confidence", 0.5))
                break

        return team_data.to_dict()

    def get_market_profile(self, team_name: str, location: str = "overall") -> Dict[str, float]:
        """
        Recupere le profil marche d'une equipe.

        Interface compatible avec DataHub.get_market_profile()
        """
        team_data = self.get_team_data(team_name)

        base_profile = {
            "over25": team_data.get("over25_rate", 0.55) * 100,
            "btts": team_data.get("btts_rate", 0.50) * 100,
            "under25": (1 - team_data.get("over25_rate", 0.55)) * 100,
            "clean_sheet": team_data.get("clean_sheet_rate", 0.30) * 100,
            "fail_to_score": team_data.get("failed_to_score_rate", 0.20) * 100,
        }

        # Ajuster selon location
        if location == "home":
            base_profile["over25"] *= 1.05
            base_profile["btts"] *= 1.03
        elif location == "away":
            base_profile["over25"] *= 0.95
            base_profile["btts"] *= 0.97

        return base_profile

    def get_corner_dna(self, team_name: str) -> Dict[str, Any]:
        """
        Recupere le Corner DNA d'une equipe.

        Interface compatible avec DataHub.get_corner_dna()
        """
        team_data = self.get_team_data(team_name)

        corners_for = team_data.get("corners_for_avg", 5.0)
        corners_against = team_data.get("corners_against_avg", 5.0)

        return {
            "team_name": team_name,
            "corners_for_avg": corners_for,
            "corners_against_avg": corners_against,
            "corners_total_avg": corners_for + corners_against,
            "corner_efficiency": team_data.get("corner_efficiency", 0.03),
            "corner_conceded_danger": 0.08,
        }

    def get_card_dna(self, team_name: str) -> Dict[str, Any]:
        """
        Recupere le Card DNA d'une equipe.

        Interface compatible avec DataHub.get_card_dna()
        """
        team_data = self.get_team_data(team_name)

        return {
            "team_name": team_name,
            "yellow_cards_avg": team_data.get("yellow_cards_avg", 1.8),
            "red_cards_avg": team_data.get("red_cards_avg", 0.05),
            "fouls_committed_avg": team_data.get("fouls_committed_avg", 12.0),
            "fouls_suffered_avg": 11.0,
            "cards_total_avg": team_data.get("yellow_cards_avg", 1.8) + team_data.get("red_cards_avg", 0.05),
        }

    def get_referee_data(self, referee_name: str) -> Optional[Dict]:
        """
        Recupere les donnees d'un arbitre.

        Interface compatible avec DataHub.get_referee_data()
        Compatible avec RefereeEngine qui attend: style, cards_per90
        """
        if not referee_name:
            return None

        yellow_cards_avg = 3.5
        strictness = "MEDIUM"

        orchestrator = self._ensure_orchestrator()
        if orchestrator:
            try:
                referee = orchestrator.get_referee(referee_name)
                if referee:
                    yellow_cards_avg = float(referee.get("yellow_cards_avg", 3.5))
                    strictness = referee.get("strictness", "MEDIUM")
            except Exception as e:
                logger.debug(f"Referee data error: {e}")

        # Mapper strictness vers style pour RefereeEngine
        style_map = {
            "HIGH": "strict",
            "STRICT": "strict",
            "MEDIUM": "balanced",
            "LOW": "permissive",
            "LENIENT": "permissive",
        }
        style = style_map.get(str(strictness).upper(), "balanced")

        return {
            "referee_name": referee_name,
            # Pour RefereeEngine
            "style": style,
            "cards_per90": yellow_cards_avg,
            # Standard fields
            "yellow_cards_avg": yellow_cards_avg,
            "red_cards_avg": 0.15,
            "fouls_per_card": 3.5,
            "penalty_rate": 0.25,
            "strictness": strictness,
            "home_bias": 0.0,
            "avg_yellow_cards_per_game": yellow_cards_avg,  # Pour CardEngine
        }

    def is_specialist(self, team_name: str, market: str, location: str) -> Optional[Dict]:
        """
        Verifie si une equipe est specialiste d'un marche.

        Interface compatible avec DataHub.is_specialist()
        """
        team_data = self.get_team_data(team_name)

        # Determiner si specialiste base sur les taux
        thresholds = {
            "btts_yes": ("btts_rate", 0.60),
            "btts_no": ("btts_rate", 0.40, True),  # True = inverse
            "over_25": ("over25_rate", 0.65),
            "under_25": ("over25_rate", 0.40, True),
        }

        if market not in thresholds:
            return None

        config = thresholds[market]
        field = config[0]
        threshold = config[1]
        inverse = config[2] if len(config) > 2 else False

        value = team_data.get(field, 0.5)

        if inverse:
            is_specialist = value < threshold
        else:
            is_specialist = value > threshold

        if is_specialist:
            return {
                "team": team_name,
                "market": market,
                "location": location,
                "win_rate": value * 100 if not inverse else (1 - value) * 100,
                "confidence": 0.7,
            }

        return None

    def prepare_matchup_data(self, home: str, away: str, referee: str = None) -> Dict:
        """
        Prepare les donnees de matchup pour les engines.

        C'est LA methode cle utilisee par QuantumBrain pour alimenter les engines.
        """
        home_data = self.get_team_data(home)
        away_data = self.get_team_data(away)

        # Friction via DataOrchestrator
        friction_data = {}
        orchestrator = self._ensure_orchestrator()
        if orchestrator:
            try:
                friction = orchestrator.get_friction(home, away)
                if friction:
                    friction_data = {
                        "friction_score": friction.friction_score,
                        "predicted_goals": friction.predicted_goals,
                        "btts_prob": friction.btts_prob,
                        "over25_prob": friction.over25_prob,
                        "chaos_potential": friction.chaos_potential,
                        "primary_markets": friction.primary_markets,
                        "avoid_markets": friction.avoid_markets,
                    }
            except Exception as e:
                logger.debug(f"Friction error: {e}")

        # Referee data
        referee_data = self.get_referee_data(referee) if referee else None

        # Construire le matchup_data complet
        matchup_data = {
            "home": home_data,
            "away": away_data,
            "home_team": home_data,  # Alias pour UnifiedBrain
            "away_team": away_data,  # Alias pour UnifiedBrain
            "team_a": home_data,  # Alias pour compatibilite
            "team_b": away_data,  # Alias pour compatibilite

            # Friction
            "friction": friction_data,
            "friction_score": friction_data.get("friction_score", 50.0),
            "predicted_goals": friction_data.get("predicted_goals", 2.5),

            # Referee
            "referee": referee_data,

            # Tactical clash
            "home_profile": home_data.get("tactical_profile", "BALANCED"),
            "away_profile": away_data.get("tactical_profile", "BALANCED"),

            # Computed
            "xg_total": home_data.get("xg_for", 1.4) + away_data.get("xg_for", 1.4),
            "btts_combined": (home_data.get("btts_rate", 0.5) + away_data.get("btts_rate", 0.5)) / 2,

            # Corners
            "corners_total_expected": (
                home_data.get("corners_for_avg", 5.0) +
                away_data.get("corners_for_avg", 5.0)
            ),

            # Cards
            "cards_total_expected": (
                home_data.get("yellow_cards_avg", 1.8) +
                away_data.get("yellow_cards_avg", 1.8)
            ),

            # Meta
            "_adapter_version": self.VERSION,
        }

        return matchup_data

    # ===================================================================
    # METHODES UTILITAIRES
    # ===================================================================

    def get_stats(self) -> Dict:
        """Retourne les statistiques d'utilisation."""
        return self._stats.copy()

    def clear_cache(self):
        """Vide le cache."""
        self.get_team_data.cache_clear()
        self._classification_cache = {}
        logger.info("Cache vide")

    def health_check(self) -> Dict:
        """Verifie l'etat de sante de l'adapter."""
        orchestrator = self._ensure_orchestrator()
        classification = self._load_classification()

        return {
            "adapter_version": self.VERSION,
            "orchestrator_connected": orchestrator is not None,
            "classification_loaded": len(classification) > 0,
            "classification_teams": len(classification),
            "stats": self._stats,
        }


# ===================================================================
# SINGLETON
# ===================================================================

_adapter_instance = None

def get_data_hub_adapter() -> DataHubAdapter:
    """Retourne l'instance singleton du DataHubAdapter."""
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = DataHubAdapter()
    return _adapter_instance


# ===================================================================
# TEST
# ===================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("TEST DATAHUB ADAPTER - HEDGE FUND GRADE")
    print("=" * 80)

    adapter = get_data_hub_adapter()

    # Test 1: Health Check
    print("\n[1] Health Check")
    print("-" * 60)
    health = adapter.health_check()
    for key, value in health.items():
        print(f"  {key}: {value}")

    # Test 2: Team Data
    print("\n[2] Team Data (Liverpool)")
    print("-" * 60)
    team_data = adapter.get_team_data("Liverpool")
    important_keys = ["team_name", "xg_for", "xg_against", "win_rate", "tactical_profile", "tier"]
    for key in important_keys:
        print(f"  {key}: {team_data.get(key)}")

    # Test 3: Market Profile
    print("\n[3] Market Profile (Arsenal)")
    print("-" * 60)
    market = adapter.get_market_profile("Arsenal")
    for key, value in market.items():
        print(f"  {key}: {value:.1f}%")

    # Test 4: Corner DNA
    print("\n[4] Corner DNA (Man City)")
    print("-" * 60)
    corner = adapter.get_corner_dna("Manchester City")
    for key, value in corner.items():
        print(f"  {key}: {value}")

    # Test 5: Card DNA
    print("\n[5] Card DNA (Crystal Palace)")
    print("-" * 60)
    card = adapter.get_card_dna("Crystal Palace")
    for key, value in card.items():
        print(f"  {key}: {value}")

    # Test 6: Referee Data
    print("\n[6] Referee Data (Michael Oliver)")
    print("-" * 60)
    referee = adapter.get_referee_data("Michael Oliver")
    for key, value in referee.items():
        print(f"  {key}: {value}")

    # Test 7: Matchup Data
    print("\n[7] Matchup Data (Liverpool vs Man City)")
    print("-" * 60)
    matchup = adapter.prepare_matchup_data("Liverpool", "Manchester City", "Michael Oliver")
    print(f"  Home Profile: {matchup['home_profile']}")
    print(f"  Away Profile: {matchup['away_profile']}")
    print(f"  xG Total: {matchup['xg_total']:.2f}")
    print(f"  Predicted Goals: {matchup['predicted_goals']:.2f}")
    print(f"  BTTS Combined: {matchup['btts_combined']:.1%}")
    print(f"  Friction Score: {matchup['friction_score']:.1f}")

    # Stats
    print("\n[8] Statistiques")
    print("-" * 60)
    stats = adapter.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 80)
    print("TESTS TERMINES")
    print("=" * 80)
