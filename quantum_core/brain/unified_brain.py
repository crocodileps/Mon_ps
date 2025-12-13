"""
UnifiedBrain V2.7 - Cerveau Unifie Hedge Fund Grade
===============================================================================

ARCHITECTURE V2.7:
    1. DataHubAdapter -> Donnees unifiees
    2. 8 Engines -> Analyses specialisees
    3. PoissonCalculator -> Over/Under pour Goals/Corners/Cards
    4. DerivedMarketsCalculator -> DC et DNB depuis 1X2
    5. CorrectScoreCalculator -> Top 10 scores exacts
    6. HalfTimeCalculator -> Marches mi-temps
    7. AsianHandicapCalculator -> 8 marches AH
    8. GoalRangeCalculator -> 4 marches Goal Range
    9. DoubleResultCalculator -> 9 marches HT/FT
    10. WinToNilCalculator -> 4 marches Win to Nil
    11. OddEvenCalculator -> 2 marches Odd/Even
    12. ExactGoalsCalculator -> 6 marches Exact Goals
    13. BttsBothHalvesCalculator -> 2 marches BTTS Both Halves
    14. ScoreInBothHalvesCalculator -> 2 marches Score Both Halves
    15. CleanSheetCalculator -> 2 marches Clean Sheet
    16. ToScoreInHalfCalculator -> 4 marches To Score in Half
    17. BayesianFusion -> Fusion probabilites
    18. EdgeCalculator -> Calcul edges avec LIQUIDITY_TAX par marche
    19. KellySizer -> Sizing optimal

93 MARCHES SUPPORTES:
    - 1X2 (3): home_win, draw, away_win
    - Double Chance (3): dc_1x, dc_x2, dc_12
    - DNB (2): dnb_home, dnb_away
    - BTTS (2): btts_yes, btts_no
    - Goals (12): over/under 0.5, 1.5, 2.5, 3.5, 4.5, 5.5
    - Corners (6): over/under 8.5, 9.5, 10.5
    - Cards (6): over/under 2.5, 3.5, 4.5
    - Correct Score (10): top 10 scores (0-0, 1-0, 0-1, 1-1, 2-0, 0-2, 2-1, 1-2, 2-2, 3-1)
    - Half-Time (6): ht_1x2, ht_over_05, ht_under_05, ht_btts
    - Asian Handicap (8): ah_-0.5, ah_-1.0, ah_-1.5, ah_-2.0 (home & away)
    - Goal Range (4): 0-1, 2-3, 4-5, 6+
    - Double Result (9): 9 combinaisons HT/FT
    - Win to Nil (4): home/away win to nil yes/no
    - Odd/Even (2): odd_goals, even_goals
    - Exact Goals (6): 0, 1, 2, 3, 4, 5+
    - BTTS Both Halves (2): yes/no
    - Score Both Halves (2): yes/no
    - Clean Sheet (2): home/away clean sheet yes
    - To Score in Half (4): home/away to score 1H/2H

Auteur: Mon_PS Quant Team
Version: 2.7.0
Date: 13 Decembre 2025
"""

import sys
import logging
import math
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

# Configuration path
PROJECT_ROOT = Path("/home/Mon_ps")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from .models import (
    MatchPrediction, MarketProbability, MarketEdge, BetRecommendation,
    EngineOutput, MarketType, Confidence, SignalStrength,
    LIQUIDITY_TAX, MIN_EDGE_BY_MARKET, MARKET_CATEGORIES
)
from .correct_score import CorrectScoreCalculator
from .half_time import HalfTimeCalculator
from .asian_handicap import AsianHandicapCalculator
from .goal_range import GoalRangeCalculator
from .double_result import DoubleResultCalculator
from .win_to_nil import WinToNilCalculator
from .odd_even import OddEvenCalculator
from .exact_goals import ExactGoalsCalculator
from .btts_both_halves import BttsBothHalvesCalculator
from .score_both_halves import ScoreInBothHalvesCalculator
from .clean_sheet import CleanSheetCalculator
from .to_score_half import ToScoreInHalfCalculator

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ===============================================================================
# POISSON CALCULATOR
# ===============================================================================

class PoissonCalculator:
    """
    Calculateur Poisson pour probabilites over/under.

    Utilise pour:
    - Goals: lambda = expected_goals
    - Corners: lambda = expected_corners
    - Cards: lambda = expected_cards
    """

    @staticmethod
    def poisson_pmf(k: int, lam: float) -> float:
        """Calcul PMF Poisson P(X = k)."""
        if lam <= 0:
            return 1.0 if k == 0 else 0.0
        return (lam ** k) * math.exp(-lam) / math.factorial(k)

    @staticmethod
    def poisson_cdf(k: int, lam: float) -> float:
        """Calcul CDF Poisson P(X <= k)."""
        if lam <= 0:
            return 1.0
        cdf = 0.0
        for i in range(k + 1):
            cdf += PoissonCalculator.poisson_pmf(i, lam)
        return min(1.0, cdf)

    @staticmethod
    def prob_over(threshold: float, lam: float) -> float:
        """P(X > threshold) = 1 - P(X <= floor(threshold))."""
        k = int(threshold)  # floor
        return 1.0 - PoissonCalculator.poisson_cdf(k, lam)

    @staticmethod
    def prob_under(threshold: float, lam: float) -> float:
        """P(X < threshold) = P(X <= floor(threshold))."""
        k = int(threshold)  # floor
        return PoissonCalculator.poisson_cdf(k, lam)

    @staticmethod
    def calculate_goals_probs(expected_goals: float) -> Dict[str, float]:
        """Calcule toutes les probabilites goals."""
        return {
            "over_05": PoissonCalculator.prob_over(0.5, expected_goals),
            "over_15": PoissonCalculator.prob_over(1.5, expected_goals),
            "over_25": PoissonCalculator.prob_over(2.5, expected_goals),
            "over_35": PoissonCalculator.prob_over(3.5, expected_goals),
            "over_45": PoissonCalculator.prob_over(4.5, expected_goals),
            "over_55": PoissonCalculator.prob_over(5.5, expected_goals),
            "under_05": PoissonCalculator.prob_under(0.5, expected_goals),
            "under_15": PoissonCalculator.prob_under(1.5, expected_goals),
            "under_25": PoissonCalculator.prob_under(2.5, expected_goals),
            "under_35": PoissonCalculator.prob_under(3.5, expected_goals),
            "under_45": PoissonCalculator.prob_under(4.5, expected_goals),
            "under_55": PoissonCalculator.prob_under(5.5, expected_goals),
        }

    @staticmethod
    def calculate_corners_probs(expected_corners: float) -> Dict[str, float]:
        """Calcule toutes les probabilites corners."""
        return {
            "over_85": PoissonCalculator.prob_over(8.5, expected_corners),
            "over_95": PoissonCalculator.prob_over(9.5, expected_corners),
            "over_105": PoissonCalculator.prob_over(10.5, expected_corners),
            "under_85": PoissonCalculator.prob_under(8.5, expected_corners),
            "under_95": PoissonCalculator.prob_under(9.5, expected_corners),
            "under_105": PoissonCalculator.prob_under(10.5, expected_corners),
        }

    @staticmethod
    def calculate_cards_probs(expected_cards: float) -> Dict[str, float]:
        """Calcule toutes les probabilites cards."""
        return {
            "over_25": PoissonCalculator.prob_over(2.5, expected_cards),
            "over_35": PoissonCalculator.prob_over(3.5, expected_cards),
            "over_45": PoissonCalculator.prob_over(4.5, expected_cards),
            "under_25": PoissonCalculator.prob_under(2.5, expected_cards),
            "under_35": PoissonCalculator.prob_under(3.5, expected_cards),
            "under_45": PoissonCalculator.prob_under(4.5, expected_cards),
        }


# ===============================================================================
# DERIVED MARKETS CALCULATOR
# ===============================================================================

class DerivedMarketsCalculator:
    """
    Calculateur pour marches derives (Double Chance, DNB).

    Double Chance:
        DC_1X = P(home) + P(draw)
        DC_X2 = P(draw) + P(away)
        DC_12 = P(home) + P(away)

    Draw No Bet:
        DNB_Home = P(home) / (1 - P(draw))
        DNB_Away = P(away) / (1 - P(draw))
    """

    @staticmethod
    def calculate_double_chance(home: float, draw: float, away: float) -> Dict[str, float]:
        """Calcule les probabilites Double Chance."""
        return {
            "dc_1x": home + draw,
            "dc_x2": draw + away,
            "dc_12": home + away,
        }

    @staticmethod
    def calculate_dnb(home: float, draw: float, away: float) -> Dict[str, float]:
        """Calcule les probabilites Draw No Bet."""
        no_draw_factor = 1 - draw
        if no_draw_factor <= 0:
            return {"dnb_home": 0.5, "dnb_away": 0.5}

        return {
            "dnb_home": home / no_draw_factor,
            "dnb_away": away / no_draw_factor,
        }


# ===============================================================================
# POIDS DES ENGINES (Optimises pour chaque marche)
# ===============================================================================

ENGINE_WEIGHTS = {
    # Marches 1X2 et Goals
    "1x2": {
        "matchup": 0.30,
        "pattern": 0.20,
        "coach": 0.15,
        "variance": 0.15,
        "referee": 0.10,
        "chain": 0.10,
    },
    # Marches Corners
    "corners": {
        "corner": 0.40,
        "matchup": 0.20,
        "pattern": 0.15,
        "coach": 0.10,
        "referee": 0.15,
    },
    # Marches Cards
    "cards": {
        "card": 0.35,
        "referee": 0.30,
        "matchup": 0.15,
        "pattern": 0.10,
        "coach": 0.10,
    },
    # BTTS
    "btts": {
        "matchup": 0.30,
        "pattern": 0.25,
        "coach": 0.15,
        "variance": 0.15,
        "referee": 0.15,
    },
}


# ===============================================================================
# UNIFIED BRAIN V2.7
# ===============================================================================

class UnifiedBrain:
    """
    Cerveau Unifie V2.7 - Orchestre tous les composants pour 93 marches.

    Usage:
        brain = UnifiedBrain()
        prediction = brain.analyze_match("Liverpool", "Manchester City")
    """

    VERSION = "2.7.0"

    def __init__(self):
        """Initialise le cerveau avec lazy loading."""
        self._data_hub_adapter = None
        self._engines = {}
        self._bayesian_fusion = None
        self._edge_calculator = None
        self._kelly_sizer = None
        self._initialized = False

        # Calculateurs V2.7
        self._poisson = PoissonCalculator()
        self._derived = DerivedMarketsCalculator()
        self._correct_score = CorrectScoreCalculator()
        self._half_time = HalfTimeCalculator()
        self._asian_handicap = AsianHandicapCalculator()
        self._goal_range = GoalRangeCalculator()
        self._double_result = DoubleResultCalculator()
        self._win_to_nil = WinToNilCalculator()
        self._odd_even = OddEvenCalculator()
        self._exact_goals = ExactGoalsCalculator()
        self._btts_both_halves = BttsBothHalvesCalculator()
        self._score_both_halves = ScoreInBothHalvesCalculator()
        self._clean_sheet = CleanSheetCalculator()
        self._to_score_half = ToScoreInHalfCalculator()

        self._stats = {
            "matches_analyzed": 0,
            "engines_called": 0,
            "edges_found": 0,
            "bets_recommended": 0,
            "markets_processed": 0,
        }

        logger.info("UnifiedBrain V2.7 initialise (lazy mode)")

    # ===========================================================================
    # LAZY LOADING
    # ===========================================================================

    def _ensure_initialized(self):
        """Initialisation lazy des composants."""
        if self._initialized:
            return

        # DataHubAdapter
        try:
            from quantum_core.adapters.data_hub_adapter import DataHubAdapter
            self._data_hub_adapter = DataHubAdapter()
            logger.info("DataHubAdapter connecte")
        except Exception as e:
            logger.error(f"DataHubAdapter non disponible: {e}")
            raise

        # BayesianFusion (reutilise)
        try:
            from quantum.chess_engine.probability.bayesian_fusion import BayesianFusion
            self._bayesian_fusion = BayesianFusion()
            logger.info("BayesianFusion connectee")
        except Exception as e:
            logger.warning(f"BayesianFusion non disponible: {e}")

        # EdgeCalculator (reutilise)
        try:
            from quantum.chess_engine.probability.edge_calculator import EdgeCalculator
            self._edge_calculator = EdgeCalculator()
            logger.info("EdgeCalculator connecte")
        except Exception as e:
            logger.warning(f"EdgeCalculator non disponible: {e}")

        # KellySizer (reutilise)
        try:
            from quantum.chess_engine.execution.kelly_sizer import KellySizer
            self._kelly_sizer = KellySizer()
            logger.info("KellySizer connecte")
        except Exception as e:
            logger.warning(f"KellySizer non disponible: {e}")

        self._initialized = True
        logger.info("UnifiedBrain V2.7 pret - 93 marches")

    def _load_engine(self, engine_name: str):
        """Charge un engine de maniere lazy."""
        if engine_name in self._engines:
            return self._engines[engine_name]

        engine_map = {
            "matchup": ("quantum.chess_engine.engines.matchup_engine", "MatchupEngine", True),
            "corner": ("quantum.chess_engine.engines.corner_engine", "CornerEngine", False),
            "card": ("quantum.chess_engine.engines.card_engine", "CardEngine", False),
            "coach": ("quantum.chess_engine.engines.coach_engine", "CoachEngine", True),
            "referee": ("quantum.chess_engine.engines.referee_engine", "RefereeEngine", True),
            "variance": ("quantum.chess_engine.engines.variance_engine", "VarianceEngine", True),
            "pattern": ("quantum.chess_engine.engines.pattern_engine", "PatternEngine", True),
            "chain": ("quantum.chess_engine.engines.chain_engine", "ChainEngine", True),
        }

        if engine_name not in engine_map:
            return None

        module_path, class_name, needs_hub = engine_map[engine_name]
        try:
            import importlib
            module = importlib.import_module(module_path)
            engine_class = getattr(module, class_name)

            if needs_hub:
                self._engines[engine_name] = engine_class(self._data_hub_adapter)
            else:
                self._engines[engine_name] = engine_class()

            logger.debug(f"{class_name} charge")
            return self._engines[engine_name]
        except Exception as e:
            logger.warning(f"{engine_name} non disponible: {e}")
            return None

    # ===========================================================================
    # METHODE PRINCIPALE: analyze_match
    # ===========================================================================

    def analyze_match(
        self,
        home: str,
        away: str,
        referee: str = None,
        market_odds: Dict[str, float] = None,
        bankroll: float = 1000.0
    ) -> MatchPrediction:
        """
        Analyse complete d'un match - 93 marches.

        Args:
            home: Equipe a domicile
            away: Equipe a l'exterieur
            referee: Nom de l'arbitre (optionnel)
            market_odds: Cotes du marche pour calcul d'edge
            bankroll: Bankroll pour calcul Kelly

        Returns:
            MatchPrediction avec 93 marches de probabilites et recommandations
        """
        self._ensure_initialized()
        self._stats["matches_analyzed"] += 1

        logger.info(f"Analyse V2.7: {home} vs {away}")

        # Creer le resultat
        prediction = MatchPrediction(
            home_team=home,
            away_team=away,
            prediction_timestamp=datetime.now()
        )

        # -------------------------------------------------------------------
        # ETAPE 1: Preparer les donnees via DataHubAdapter
        # -------------------------------------------------------------------
        matchup_data = self._data_hub_adapter.prepare_matchup_data(home, away, referee)

        prediction.home_profile = matchup_data.get("home_profile", "UNKNOWN")
        prediction.away_profile = matchup_data.get("away_profile", "UNKNOWN")
        prediction.expected_goals = matchup_data.get("predicted_goals", 2.5)

        # Friction data
        friction = matchup_data.get("friction", {})
        if friction:
            prediction.expected_goals = friction.get("predicted_goals", prediction.expected_goals)
            prediction.btts_prob = friction.get("btts_prob", 0.50)

        # -------------------------------------------------------------------
        # ETAPE 2: Executer tous les engines
        # -------------------------------------------------------------------
        engine_outputs = self._run_all_engines(home, away, matchup_data, referee)
        prediction.engine_outputs = engine_outputs
        prediction.engines_used = [name for name, out in engine_outputs.items() if out.success]
        prediction.engines_failed = [name for name, out in engine_outputs.items() if not out.success]

        # -------------------------------------------------------------------
        # ETAPE 3: Fusion Bayesienne des probabilites de base
        # -------------------------------------------------------------------
        base_probs = self._fuse_probabilities(engine_outputs, matchup_data)

        # Assigner 1X2
        prediction.home_win_prob = base_probs.get("home_win", 0.40)
        prediction.draw_prob = base_probs.get("draw", 0.25)
        prediction.away_win_prob = base_probs.get("away_win", 0.35)

        # BTTS
        prediction.btts_prob = base_probs.get("btts", prediction.btts_prob)
        prediction.btts_no_prob = 1 - prediction.btts_prob

        # Expected values
        prediction.expected_goals = base_probs.get("expected_goals", 2.5)
        prediction.corners_expected = base_probs.get("corners_expected", 10.0)
        prediction.cards_expected = base_probs.get("cards_expected", 4.0)

        # Expected home/away goals (estimation simple)
        prediction.expected_home_goals = prediction.expected_goals * (prediction.home_win_prob + 0.1)
        prediction.expected_away_goals = prediction.expected_goals - prediction.expected_home_goals

        # -------------------------------------------------------------------
        # ETAPE 4: Calculer Double Chance et DNB
        # -------------------------------------------------------------------
        dc_probs = self._derived.calculate_double_chance(
            prediction.home_win_prob,
            prediction.draw_prob,
            prediction.away_win_prob
        )
        prediction.dc_1x_prob = dc_probs["dc_1x"]
        prediction.dc_x2_prob = dc_probs["dc_x2"]
        prediction.dc_12_prob = dc_probs["dc_12"]

        dnb_probs = self._derived.calculate_dnb(
            prediction.home_win_prob,
            prediction.draw_prob,
            prediction.away_win_prob
        )
        prediction.dnb_home_prob = dnb_probs["dnb_home"]
        prediction.dnb_away_prob = dnb_probs["dnb_away"]

        # -------------------------------------------------------------------
        # ETAPE 5: Calculer Over/Under avec Poisson
        # -------------------------------------------------------------------
        # Goals
        goals_probs = self._poisson.calculate_goals_probs(prediction.expected_goals)
        prediction.over_05_prob = goals_probs["over_05"]
        prediction.over_15_prob = goals_probs["over_15"]
        prediction.over_25_prob = goals_probs["over_25"]
        prediction.over_35_prob = goals_probs["over_35"]
        prediction.over_45_prob = goals_probs["over_45"]
        prediction.over_55_prob = goals_probs["over_55"]
        prediction.under_05_prob = goals_probs["under_05"]
        prediction.under_15_prob = goals_probs["under_15"]
        prediction.under_25_prob = goals_probs["under_25"]
        prediction.under_35_prob = goals_probs["under_35"]
        prediction.under_45_prob = goals_probs["under_45"]
        prediction.under_55_prob = goals_probs["under_55"]

        # Corners
        corners_probs = self._poisson.calculate_corners_probs(prediction.corners_expected)
        prediction.corners_over_85_prob = corners_probs["over_85"]
        prediction.corners_over_95_prob = corners_probs["over_95"]
        prediction.corners_over_105_prob = corners_probs["over_105"]
        prediction.corners_under_85_prob = corners_probs["under_85"]
        prediction.corners_under_95_prob = corners_probs["under_95"]
        prediction.corners_under_105_prob = corners_probs["under_105"]

        # Cards
        cards_probs = self._poisson.calculate_cards_probs(prediction.cards_expected)
        prediction.cards_over_25_prob = cards_probs["over_25"]
        prediction.cards_over_35_prob = cards_probs["over_35"]
        prediction.cards_over_45_prob = cards_probs["over_45"]
        prediction.cards_under_25_prob = cards_probs["under_25"]
        prediction.cards_under_35_prob = cards_probs["under_35"]
        prediction.cards_under_45_prob = cards_probs["under_45"]

        # -------------------------------------------------------------------
        # ETAPE 5b: Calculer Correct Score (Top 10)
        # -------------------------------------------------------------------
        cs_analysis = self._correct_score.calculate(
            prediction.expected_home_goals,
            prediction.expected_away_goals
        )
        prediction.correct_score_probs = {
            pred.market_key: pred.probability
            for pred in cs_analysis.top_scores
        }
        prediction.top_scores = [pred.score_str for pred in cs_analysis.top_scores]

        # -------------------------------------------------------------------
        # ETAPE 5c: Calculer Half-Time (6 marchés)
        # -------------------------------------------------------------------
        ht_analysis = self._half_time.calculate(
            expected_goals=prediction.expected_goals,
            home_win_prob=prediction.home_win_prob,
            draw_prob=prediction.draw_prob,
            away_win_prob=prediction.away_win_prob,
            expected_home_goals=prediction.expected_home_goals,
            expected_away_goals=prediction.expected_away_goals,
            home_profile=prediction.home_profile,
            away_profile=prediction.away_profile,
            btts_prob=prediction.btts_prob
        )

        prediction.ht_home_win_prob = ht_analysis.ht_home_win_prob
        prediction.ht_draw_prob = ht_analysis.ht_draw_prob
        prediction.ht_away_win_prob = ht_analysis.ht_away_win_prob
        prediction.ht_over_05_prob = ht_analysis.ht_over_05_prob
        prediction.ht_under_05_prob = ht_analysis.ht_under_05_prob
        prediction.ht_btts_prob = ht_analysis.ht_btts_prob
        prediction.expected_ht_goals = ht_analysis.expected_ht_goals

        # -------------------------------------------------------------------
        # ETAPE 5d: Calculer Asian Handicap (8 marchés)
        # -------------------------------------------------------------------
        ah_analysis = self._asian_handicap.calculate(
            prediction.expected_home_goals,
            prediction.expected_away_goals
        )

        prediction.ah_home_m05_prob = ah_analysis.ah_home_m05_prob
        prediction.ah_away_p05_prob = ah_analysis.ah_away_p05_prob
        prediction.ah_home_m10_prob = ah_analysis.ah_home_m10_prob
        prediction.ah_away_p10_prob = ah_analysis.ah_away_p10_prob
        prediction.ah_home_m15_prob = ah_analysis.ah_home_m15_prob
        prediction.ah_away_p15_prob = ah_analysis.ah_away_p15_prob
        prediction.ah_home_m20_prob = ah_analysis.ah_home_m20_prob
        prediction.ah_away_p20_prob = ah_analysis.ah_away_p20_prob

        # -------------------------------------------------------------------
        # ETAPE 5e: Calculer Goal Range (4 marchés)
        # -------------------------------------------------------------------
        gr_analysis = self._goal_range.calculate(prediction.expected_goals)

        prediction.goals_0_1_prob = gr_analysis.goals_0_1_prob
        prediction.goals_2_3_prob = gr_analysis.goals_2_3_prob
        prediction.goals_4_5_prob = gr_analysis.goals_4_5_prob
        prediction.goals_6_plus_prob = gr_analysis.goals_6_plus_prob

        # -------------------------------------------------------------------
        # ETAPE 5f: Calculer Double Result (9 marchés)
        # -------------------------------------------------------------------
        dr_analysis = self._double_result.calculate(
            ht_home=prediction.ht_home_win_prob,
            ht_draw=prediction.ht_draw_prob,
            ht_away=prediction.ht_away_win_prob,
            ft_home=prediction.home_win_prob,
            ft_draw=prediction.draw_prob,
            ft_away=prediction.away_win_prob
        )

        prediction.dr_1_1_prob = dr_analysis.ht_home_ft_home_prob
        prediction.dr_1_x_prob = dr_analysis.ht_home_ft_draw_prob
        prediction.dr_1_2_prob = dr_analysis.ht_home_ft_away_prob
        prediction.dr_x_1_prob = dr_analysis.ht_draw_ft_home_prob
        prediction.dr_x_x_prob = dr_analysis.ht_draw_ft_draw_prob
        prediction.dr_x_2_prob = dr_analysis.ht_draw_ft_away_prob
        prediction.dr_2_1_prob = dr_analysis.ht_away_ft_home_prob
        prediction.dr_2_x_prob = dr_analysis.ht_away_ft_draw_prob
        prediction.dr_2_2_prob = dr_analysis.ht_away_ft_away_prob

        # -------------------------------------------------------------------
        # ETAPE 5g: Calculer Win to Nil (4 marchés)
        # -------------------------------------------------------------------
        wtn_analysis = self._win_to_nil.calculate(
            expected_home=prediction.expected_home_goals,
            expected_away=prediction.expected_away_goals,
            home_win_prob=prediction.home_win_prob,
            away_win_prob=prediction.away_win_prob,
            correct_score_probs=prediction.correct_score_probs
        )

        prediction.home_win_to_nil_prob = wtn_analysis.home_win_to_nil_yes
        prediction.home_win_to_nil_no_prob = wtn_analysis.home_win_to_nil_no
        prediction.away_win_to_nil_prob = wtn_analysis.away_win_to_nil_yes
        prediction.away_win_to_nil_no_prob = wtn_analysis.away_win_to_nil_no

        # -------------------------------------------------------------------
        # ETAPE 5h: Calculer Odd/Even (2 marches)
        # -------------------------------------------------------------------
        oe_analysis = self._odd_even.calculate(prediction.expected_goals)
        prediction.odd_goals_prob = oe_analysis.odd_goals_prob
        prediction.even_goals_prob = oe_analysis.even_goals_prob

        # -------------------------------------------------------------------
        # ETAPE 5i: Calculer Exact Goals (6 marches)
        # -------------------------------------------------------------------
        eg_analysis = self._exact_goals.calculate(prediction.expected_goals)
        prediction.exactly_0_goals_prob = eg_analysis.exactly_0_prob
        prediction.exactly_1_goal_prob = eg_analysis.exactly_1_prob
        prediction.exactly_2_goals_prob = eg_analysis.exactly_2_prob
        prediction.exactly_3_goals_prob = eg_analysis.exactly_3_prob
        prediction.exactly_4_goals_prob = eg_analysis.exactly_4_prob
        prediction.goals_5_plus_prob = eg_analysis.goals_5_plus_prob

        # -------------------------------------------------------------------
        # ETAPE 5j: Calculer BTTS Both Halves (2 marches)
        # -------------------------------------------------------------------
        bbh_analysis = self._btts_both_halves.calculate(
            prediction.expected_home_goals,
            prediction.expected_away_goals
        )
        prediction.btts_both_halves_yes_prob = bbh_analysis.btts_both_halves_yes
        prediction.btts_both_halves_no_prob = bbh_analysis.btts_both_halves_no

        # -------------------------------------------------------------------
        # ETAPE 5k: Calculer Score Both Halves (2 marches)
        # -------------------------------------------------------------------
        sbh_analysis = self._score_both_halves.calculate(prediction.expected_goals)
        prediction.score_both_halves_yes_prob = sbh_analysis.score_both_halves_yes
        prediction.score_both_halves_no_prob = sbh_analysis.score_both_halves_no

        # -------------------------------------------------------------------
        # ETAPE 5l: Calculer Clean Sheet (2 marches)
        # -------------------------------------------------------------------
        cs_analysis = self._clean_sheet.calculate(
            prediction.expected_home_goals,
            prediction.expected_away_goals
        )
        prediction.home_clean_sheet_yes_prob = cs_analysis.home_clean_sheet_yes
        prediction.away_clean_sheet_yes_prob = cs_analysis.away_clean_sheet_yes

        # -------------------------------------------------------------------
        # ETAPE 5m: Calculer To Score in Half (4 marches)
        # -------------------------------------------------------------------
        tsh_analysis = self._to_score_half.calculate(
            prediction.expected_home_goals,
            prediction.expected_away_goals
        )
        prediction.home_to_score_1h_prob = tsh_analysis.home_to_score_1h
        prediction.home_to_score_2h_prob = tsh_analysis.home_to_score_2h
        prediction.away_to_score_1h_prob = tsh_analysis.away_to_score_1h
        prediction.away_to_score_2h_prob = tsh_analysis.away_to_score_2h

        self._stats["markets_processed"] += 93

        # -------------------------------------------------------------------
        # ETAPE 6: Calculer les edges (si cotes fournies)
        # -------------------------------------------------------------------
        if market_odds:
            all_probabilities = self._build_all_probabilities(prediction)
            edges = self._calculate_edges(all_probabilities, market_odds)
            prediction.market_edges = edges

            positive_edges = [e for e in edges.values() if e.edge_after_liquidity > 0.01]
            self._stats["edges_found"] += len(positive_edges)

        # -------------------------------------------------------------------
        # ETAPE 7: Generer les recommandations Kelly
        # -------------------------------------------------------------------
        if market_odds and prediction.market_edges:
            recommendations = self._generate_recommendations(
                prediction.market_edges,
                bankroll
            )
            prediction.recommendations = recommendations

            # Trouver le meilleur pari
            bets_only = [r for r in recommendations if r.action == "BET"]
            if bets_only:
                prediction.best_bet = max(bets_only, key=lambda r: r.stake_percentage)
                self._stats["bets_recommended"] += 1

            # Meilleur par categorie
            prediction.best_bets_by_category = self._find_best_by_category(recommendations)

        # -------------------------------------------------------------------
        # ETAPE 8: Calculer la confiance globale
        # -------------------------------------------------------------------
        prediction.data_quality_score = self._calculate_quality(prediction)
        prediction.overall_confidence = self._get_confidence_level(prediction.data_quality_score)

        logger.info(f"Analyse V2.7 terminee: {len(prediction.engines_used)} engines, "
                   f"93 marches, qualite {prediction.data_quality_score:.1%}")

        return prediction

    # ===========================================================================
    # METHODES PRIVEES
    # ===========================================================================

    def _run_all_engines(
        self,
        home: str,
        away: str,
        matchup_data: Dict,
        referee: str = None
    ) -> Dict[str, EngineOutput]:
        """Execute tous les engines et collecte les outputs."""
        outputs = {}

        home_data = matchup_data.get("home_team", {})
        away_data = matchup_data.get("away_team", {})

        engine_configs = [
            ("matchup", "matchup"),
            ("corner", "stateless"),
            ("card", "stateless"),
            ("coach", "matchup"),
            ("referee", "referee"),
            ("variance", "matchup"),
            ("pattern", "matchup"),
            ("chain", "matchup"),
        ]

        for name, engine_type in engine_configs:
            engine = self._load_engine(name)
            if engine:
                try:
                    self._stats["engines_called"] += 1

                    if engine_type == "matchup":
                        result = engine.analyze(home, away, matchup_data)
                    elif engine_type == "stateless":
                        result = engine.analyze(home_data, away_data)
                    elif engine_type == "referee" and referee:
                        result = engine.analyze(referee, home, away)
                    elif engine_type == "referee":
                        result = {"style": "balanced", "cards_over_prob": 0.50, "goals_modifier": 0.0}
                    else:
                        result = {}

                    outputs[name] = EngineOutput(
                        engine_name=name,
                        success=True,
                        data=result if isinstance(result, dict) else {"result": result},
                        confidence=0.7,
                        weight=ENGINE_WEIGHTS.get("1x2", {}).get(name, 0.1)
                    )

                except Exception as e:
                    outputs[name] = EngineOutput(
                        engine_name=name,
                        success=False,
                        error=str(e)
                    )
            else:
                outputs[name] = EngineOutput(
                    engine_name=name,
                    success=False,
                    error="Engine not available"
                )

        return outputs

    def _fuse_probabilities(
        self,
        engine_outputs: Dict[str, EngineOutput],
        matchup_data: Dict
    ) -> Dict[str, float]:
        """Fusionne les probabilites des engines."""

        friction = matchup_data.get("friction", {})
        probs = {
            "home_win": 0.40,
            "draw": 0.25,
            "away_win": 0.35,
            "btts": friction.get("btts_prob", 0.50),
            "expected_goals": friction.get("predicted_goals", 2.5),
            "corners_expected": 10.0,
            "cards_expected": 4.0,
        }

        for name, output in engine_outputs.items():
            if not output.success:
                continue

            data = output.data

            # MatchupEngine
            if name == "matchup":
                if "home_attack_edge" in data:
                    edge = data.get("home_attack_edge", 0) - data.get("away_attack_edge", 0)
                    probs["home_win"] = max(0.15, min(0.75, 0.40 + edge * 0.5))
                    probs["away_win"] = max(0.10, min(0.70, 0.35 - edge * 0.4))
                    probs["draw"] = 1 - probs["home_win"] - probs["away_win"]

            # CornerEngine
            if name == "corner":
                if "expected_total" in data:
                    probs["corners_expected"] = float(data["expected_total"])

            # CardEngine
            if name == "card":
                if "expected_cards" in data:
                    probs["cards_expected"] = float(data["expected_cards"])

            # RefereeEngine
            if name == "referee":
                if "goals_modifier" in data:
                    modifier = float(data.get("goals_modifier", 0))
                    probs["expected_goals"] = max(1.5, min(4.5, probs["expected_goals"] + modifier * 0.3))

                if "cards_modifier" in data:
                    modifier = float(data.get("cards_modifier", 0))
                    probs["cards_expected"] = max(2.0, min(7.0, probs["cards_expected"] + modifier * 0.5))

            # VarianceEngine
            if name == "variance":
                if "regression_edge" in data:
                    reg_edge = float(data.get("regression_edge", 0))
                    probs["expected_goals"] = max(1.5, min(4.0, probs["expected_goals"] - reg_edge * 0.2))

        # Normaliser 1X2
        total = probs["home_win"] + probs["draw"] + probs["away_win"]
        if total > 0:
            probs["home_win"] /= total
            probs["draw"] /= total
            probs["away_win"] /= total

        return probs

    def _build_all_probabilities(self, prediction: MatchPrediction) -> Dict[str, float]:
        """Construit le dictionnaire complet des 93 probabilites."""
        return {
            # 1X2
            "home_win": prediction.home_win_prob,
            "draw": prediction.draw_prob,
            "away_win": prediction.away_win_prob,

            # Double Chance
            "dc_1x": prediction.dc_1x_prob,
            "dc_x2": prediction.dc_x2_prob,
            "dc_12": prediction.dc_12_prob,

            # DNB
            "dnb_home": prediction.dnb_home_prob,
            "dnb_away": prediction.dnb_away_prob,

            # BTTS
            "btts_yes": prediction.btts_prob,
            "btts_no": prediction.btts_no_prob,

            # Goals Over
            "over_0.5": prediction.over_05_prob,
            "over_1.5": prediction.over_15_prob,
            "over_2.5": prediction.over_25_prob,
            "over_3.5": prediction.over_35_prob,
            "over_4.5": prediction.over_45_prob,
            "over_5.5": prediction.over_55_prob,

            # Goals Under
            "under_0.5": prediction.under_05_prob,
            "under_1.5": prediction.under_15_prob,
            "under_2.5": prediction.under_25_prob,
            "under_3.5": prediction.under_35_prob,
            "under_4.5": prediction.under_45_prob,
            "under_5.5": prediction.under_55_prob,

            # Corners Over
            "corners_over_8.5": prediction.corners_over_85_prob,
            "corners_over_9.5": prediction.corners_over_95_prob,
            "corners_over_10.5": prediction.corners_over_105_prob,

            # Corners Under
            "corners_under_8.5": prediction.corners_under_85_prob,
            "corners_under_9.5": prediction.corners_under_95_prob,
            "corners_under_10.5": prediction.corners_under_105_prob,

            # Cards Over
            "cards_over_2.5": prediction.cards_over_25_prob,
            "cards_over_3.5": prediction.cards_over_35_prob,
            "cards_over_4.5": prediction.cards_over_45_prob,

            # Cards Under
            "cards_under_2.5": prediction.cards_under_25_prob,
            "cards_under_3.5": prediction.cards_under_35_prob,
            "cards_under_4.5": prediction.cards_under_45_prob,

            # Asian Handicap
            "ah_home_m05": prediction.ah_home_m05_prob,
            "ah_away_p05": prediction.ah_away_p05_prob,
            "ah_home_m10": prediction.ah_home_m10_prob,
            "ah_away_p10": prediction.ah_away_p10_prob,
            "ah_home_m15": prediction.ah_home_m15_prob,
            "ah_away_p15": prediction.ah_away_p15_prob,
            "ah_home_m20": prediction.ah_home_m20_prob,
            "ah_away_p20": prediction.ah_away_p20_prob,

            # Goal Range
            "goals_0_1": prediction.goals_0_1_prob,
            "goals_2_3": prediction.goals_2_3_prob,
            "goals_4_5": prediction.goals_4_5_prob,
            "goals_6_plus": prediction.goals_6_plus_prob,

            # Double Result
            "dr_1_1": prediction.dr_1_1_prob,
            "dr_1_x": prediction.dr_1_x_prob,
            "dr_1_2": prediction.dr_1_2_prob,
            "dr_x_1": prediction.dr_x_1_prob,
            "dr_x_x": prediction.dr_x_x_prob,
            "dr_x_2": prediction.dr_x_2_prob,
            "dr_2_1": prediction.dr_2_1_prob,
            "dr_2_x": prediction.dr_2_x_prob,
            "dr_2_2": prediction.dr_2_2_prob,

            # Win to Nil
            "home_win_to_nil": prediction.home_win_to_nil_prob,
            "home_win_to_nil_no": prediction.home_win_to_nil_no_prob,
            "away_win_to_nil": prediction.away_win_to_nil_prob,
            "away_win_to_nil_no": prediction.away_win_to_nil_no_prob,

            # Odd/Even
            "odd_goals": prediction.odd_goals_prob,
            "even_goals": prediction.even_goals_prob,

            # Exact Goals
            "exactly_0_goals": prediction.exactly_0_goals_prob,
            "exactly_1_goal": prediction.exactly_1_goal_prob,
            "exactly_2_goals": prediction.exactly_2_goals_prob,
            "exactly_3_goals": prediction.exactly_3_goals_prob,
            "exactly_4_goals": prediction.exactly_4_goals_prob,
            "goals_5_plus": prediction.goals_5_plus_prob,

            # BTTS Both Halves
            "btts_both_halves_yes": prediction.btts_both_halves_yes_prob,
            "btts_both_halves_no": prediction.btts_both_halves_no_prob,

            # Score Both Halves
            "score_both_halves_yes": prediction.score_both_halves_yes_prob,
            "score_both_halves_no": prediction.score_both_halves_no_prob,

            # Clean Sheet
            "home_clean_sheet_yes": prediction.home_clean_sheet_yes_prob,
            "away_clean_sheet_yes": prediction.away_clean_sheet_yes_prob,

            # To Score in Half
            "home_to_score_1h": prediction.home_to_score_1h_prob,
            "home_to_score_2h": prediction.home_to_score_2h_prob,
            "away_to_score_1h": prediction.away_to_score_1h_prob,
            "away_to_score_2h": prediction.away_to_score_2h_prob,
        }

    def _calculate_edges(
        self,
        probabilities: Dict[str, float],
        market_odds: Dict[str, float]
    ) -> Dict[str, MarketEdge]:
        """Calcule les edges pour chaque marche avec LIQUIDITY_TAX specifique."""
        edges = {}

        # Mapping flexible des noms de cotes
        odds_aliases = {
            "home_win": ["1", "home", "home_win"],
            "draw": ["X", "draw"],
            "away_win": ["2", "away", "away_win"],
            "dc_1x": ["dc_1x", "1x"],
            "dc_x2": ["dc_x2", "x2"],
            "dc_12": ["dc_12", "12"],
            "dnb_home": ["dnb_home", "dnb_1"],
            "dnb_away": ["dnb_away", "dnb_2"],
            "btts_yes": ["btts_yes", "btts"],
            "btts_no": ["btts_no"],
            "over_0.5": ["over_05", "o05"],
            "over_1.5": ["over_15", "o15"],
            "over_2.5": ["over_25", "o25"],
            "over_3.5": ["over_35", "o35"],
            "over_4.5": ["over_45", "o45"],
            "over_5.5": ["over_55", "o55"],
            "under_0.5": ["under_05", "u05"],
            "under_1.5": ["under_15", "u15"],
            "under_2.5": ["under_25", "u25"],
            "under_3.5": ["under_35", "u35"],
            "under_4.5": ["under_45", "u45"],
            "under_5.5": ["under_55", "u55"],
            "corners_over_8.5": ["corners_over_85", "co85"],
            "corners_over_9.5": ["corners_over_95", "co95"],
            "corners_over_10.5": ["corners_over_105", "co105"],
            "corners_under_8.5": ["corners_under_85", "cu85"],
            "corners_under_9.5": ["corners_under_95", "cu95"],
            "corners_under_10.5": ["corners_under_105", "cu105"],
            "cards_over_2.5": ["cards_over_25", "cao25"],
            "cards_over_3.5": ["cards_over_35", "cao35"],
            "cards_over_4.5": ["cards_over_45", "cao45"],
            "cards_under_2.5": ["cards_under_25", "cau25"],
            "cards_under_3.5": ["cards_under_35", "cau35"],
            "cards_under_4.5": ["cards_under_45", "cau45"],
        }

        for prob_name, probability in probabilities.items():
            # Trouver la cote correspondante
            odds = None
            aliases = odds_aliases.get(prob_name, [prob_name])
            for alias in aliases:
                if alias in market_odds:
                    odds = market_odds[alias]
                    break

            if odds is None:
                continue

            try:
                market_type = MarketType(prob_name)
            except ValueError:
                continue

            # Liquidity tax specifique au marche
            liquidity_tax = LIQUIDITY_TAX.get(market_type, 0.02)
            min_edge = MIN_EDGE_BY_MARKET.get(market_type, 0.03)

            # Calculer l'edge
            implied_prob = 1 / odds if odds > 0 else 0
            raw_edge = probability - implied_prob
            edge_after_vig = raw_edge - 0.01  # ~1% vig bookmaker
            edge_after_liquidity = edge_after_vig - liquidity_tax

            # Kelly (half Kelly avec cap)
            kelly = 0.0
            if edge_after_liquidity > 0 and odds > 1:
                kelly = edge_after_liquidity / (odds - 1)
                kelly = max(0, min(0.10, kelly * 0.5))  # Half Kelly, cap 10%

            # Signal strength
            if edge_after_liquidity > 0.05 and kelly > 0.03:
                signal = SignalStrength.STRONG_BET
            elif edge_after_liquidity > 0.03 and kelly > 0.01:
                signal = SignalStrength.MEDIUM_BET
            elif edge_after_liquidity > 0.01:
                signal = SignalStrength.SMALL_BET
            elif edge_after_liquidity < -0.05:
                signal = SignalStrength.FADE
            else:
                signal = SignalStrength.NO_BET

            # Verifie si l'edge atteint le seuil minimum
            meets_threshold = edge_after_liquidity >= min_edge

            edges[prob_name] = MarketEdge(
                market=market_type,
                probability=probability,
                fair_odds=1/probability if probability > 0 else 0,
                market_odds=odds,
                raw_edge=raw_edge,
                edge_after_vig=edge_after_vig,
                edge_after_liquidity=edge_after_liquidity,
                kelly_fraction=kelly,
                recommended_stake=kelly,
                signal_strength=signal,
                liquidity_tax=liquidity_tax,
                min_edge_required=min_edge,
                meets_threshold=meets_threshold
            )

        return edges

    def _generate_recommendations(
        self,
        edges: Dict[str, MarketEdge],
        bankroll: float
    ) -> List[BetRecommendation]:
        """Genere les recommandations de paris."""
        recommendations = []

        # Map pour trouver la categorie
        market_to_category = {}
        for cat_name, markets in MARKET_CATEGORIES.items():
            for market in markets:
                market_to_category[market] = cat_name

        for market_name, edge in edges.items():
            if edge.signal_strength == SignalStrength.NO_BET:
                continue

            # Determiner l'action
            if edge.signal_strength == SignalStrength.FADE:
                action = "FADE"
                stake = 0.0
            elif edge.meets_threshold and edge.edge_after_liquidity > 0.01:
                action = "BET"
                stake = edge.recommended_stake
            else:
                action = "SKIP"
                stake = 0.0

            # Raisons
            reasons = []
            if edge.edge_after_liquidity > 0.05:
                reasons.append(f"Strong edge: {edge.edge_after_liquidity:.1%}")
            elif edge.edge_after_liquidity > 0.02:
                reasons.append(f"Good edge: {edge.edge_after_liquidity:.1%}")

            if edge.kelly_fraction > 0.03:
                reasons.append(f"High Kelly: {edge.kelly_fraction:.1%}")

            if edge.meets_threshold:
                reasons.append(f"Above min threshold ({edge.min_edge_required:.1%})")

            # Warnings
            warnings = []
            if edge.kelly_fraction > 0.08:
                warnings.append("High variance - consider reduced stake")
            if edge.liquidity_tax > 0.025:
                warnings.append(f"Low liquidity market (tax: {edge.liquidity_tax:.1%})")

            # Confidence
            if edge.edge_after_liquidity > 0.05:
                confidence = Confidence.HIGH
            elif edge.edge_after_liquidity > 0.02:
                confidence = Confidence.MEDIUM
            else:
                confidence = Confidence.LOW

            # Categorie
            category = market_to_category.get(edge.market, "UNKNOWN")

            recommendations.append(BetRecommendation(
                market=edge.market,
                edge=edge,
                action=action,
                stake_percentage=stake,
                stake_units=stake * bankroll,
                reasons=reasons,
                warnings=warnings,
                confidence=confidence,
                category=category
            ))

        # Trier par stake recommande
        recommendations.sort(key=lambda r: r.stake_percentage, reverse=True)

        return recommendations

    def _find_best_by_category(
        self,
        recommendations: List[BetRecommendation]
    ) -> Dict[str, BetRecommendation]:
        """Trouve le meilleur pari par categorie."""
        best_by_cat = {}

        for rec in recommendations:
            if rec.action != "BET":
                continue

            cat = rec.category
            if cat not in best_by_cat or rec.stake_percentage > best_by_cat[cat].stake_percentage:
                best_by_cat[cat] = rec

        return best_by_cat

    def _calculate_quality(self, prediction: MatchPrediction) -> float:
        """Calcule le score de qualite global."""
        score = 0.0

        # Engines utilises (max 40%)
        engine_ratio = len(prediction.engines_used) / 8
        score += 0.4 * engine_ratio

        # Probabilites coherentes (max 30%)
        total_1x2 = prediction.home_win_prob + prediction.draw_prob + prediction.away_win_prob
        if 0.95 <= total_1x2 <= 1.05:
            score += 0.3

        # Edges trouves (max 20%)
        if prediction.market_edges:
            positive_edges = sum(1 for e in prediction.market_edges.values() if e.meets_threshold)
            score += 0.2 * min(1.0, positive_edges / 10)

        # Donnees completes (max 10%)
        if prediction.home_profile != "UNKNOWN":
            score += 0.05
        if prediction.away_profile != "UNKNOWN":
            score += 0.05

        return min(1.0, score)

    def _get_confidence_level(self, score: float) -> Confidence:
        """Convertit un score en niveau de confiance."""
        if score >= 0.8:
            return Confidence.VERY_HIGH
        elif score >= 0.65:
            return Confidence.HIGH
        elif score >= 0.5:
            return Confidence.MEDIUM
        elif score >= 0.35:
            return Confidence.LOW
        else:
            return Confidence.VERY_LOW

    # ===========================================================================
    # METHODES UTILITAIRES
    # ===========================================================================

    def get_stats(self) -> Dict:
        """Retourne les statistiques d'utilisation."""
        return self._stats.copy()

    def health_check(self) -> Dict:
        """Verifie l'etat de sante du cerveau."""
        self._ensure_initialized()

        return {
            "version": self.VERSION,
            "markets_supported": 93,
            "data_hub_adapter": self._data_hub_adapter is not None,
            "bayesian_fusion": self._bayesian_fusion is not None,
            "edge_calculator": self._edge_calculator is not None,
            "kelly_sizer": self._kelly_sizer is not None,
            "engines_loaded": len(self._engines),
            "poisson_calculator": True,
            "derived_calculator": True,
            "correct_score_calculator": True,
            "half_time_calculator": True,
            "asian_handicap_calculator": True,
            "goal_range_calculator": True,
            "double_result_calculator": True,
            "win_to_nil_calculator": True,
            "odd_even_calculator": True,
            "exact_goals_calculator": True,
            "btts_both_halves_calculator": True,
            "score_both_halves_calculator": True,
            "clean_sheet_calculator": True,
            "to_score_half_calculator": True,
            "stats": self._stats,
        }


# ===============================================================================
# SINGLETON
# ===============================================================================

_brain_instance = None

def get_unified_brain() -> UnifiedBrain:
    """Retourne l'instance singleton du UnifiedBrain."""
    global _brain_instance
    if _brain_instance is None:
        _brain_instance = UnifiedBrain()
    return _brain_instance


# ===============================================================================
# TEST
# ===============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("TEST UNIFIED BRAIN V2.7 - 93 MARCHES")
    print("=" * 80)

    brain = get_unified_brain()

    # Test 1: Health Check
    print("\nTest 1: Health Check")
    print("-" * 60)
    health = brain.health_check()
    for key, value in health.items():
        if key != "stats":
            print(f"  {key}: {value}")

    # Test 2: Poisson Calculator
    print("\nTest 2: Poisson Calculator")
    print("-" * 60)
    poisson = PoissonCalculator()
    goals_probs = poisson.calculate_goals_probs(2.5)
    print(f"  Expected Goals: 2.5")
    for key, value in goals_probs.items():
        print(f"    {key}: {value:.1%}")

    # Test 3: Derived Markets
    print("\nTest 3: Derived Markets Calculator")
    print("-" * 60)
    derived = DerivedMarketsCalculator()
    dc = derived.calculate_double_chance(0.40, 0.25, 0.35)
    dnb = derived.calculate_dnb(0.40, 0.25, 0.35)
    print(f"  1X2: 40% / 25% / 35%")
    print(f"  DC: 1X={dc['dc_1x']:.1%} | X2={dc['dc_x2']:.1%} | 12={dc['dc_12']:.1%}")
    print(f"  DNB: Home={dnb['dnb_home']:.1%} | Away={dnb['dnb_away']:.1%}")

    # Test 4: Analyse complete sans cotes
    print("\nTest 4: Analyse Liverpool vs Man City (sans cotes)")
    print("-" * 60)

    prediction = brain.analyze_match(
        home="Liverpool",
        away="Manchester City",
        referee="Michael Oliver"
    )

    print(prediction.summary())
    print(f"\nEngines utilises: {prediction.engines_used}")
    print(f"Engines echoues: {prediction.engines_failed}")

    # Test 5: Analyse avec cotes (toutes les 34 cotes)
    print("\nTest 5: Analyse avec cotes (Edge + Kelly)")
    print("-" * 60)

    market_odds = {
        # 1X2
        "1": 2.50,
        "X": 3.40,
        "2": 2.80,
        # Double Chance
        "dc_1x": 1.45,
        "dc_x2": 1.55,
        "dc_12": 1.35,
        # DNB
        "dnb_home": 1.85,
        "dnb_away": 2.10,
        # BTTS
        "btts_yes": 1.75,
        "btts_no": 2.00,
        # Goals
        "over_15": 1.30,
        "over_25": 1.85,
        "over_35": 2.60,
        "under_25": 2.00,
        "under_35": 1.50,
        # Corners
        "corners_over_95": 1.90,
        "corners_over_105": 2.30,
        # Cards
        "cards_over_35": 1.80,
        "cards_over_45": 2.40,
    }

    prediction_with_odds = brain.analyze_match(
        home="Liverpool",
        away="Manchester City",
        referee="Michael Oliver",
        market_odds=market_odds,
        bankroll=1000.0
    )

    print(f"\nEdges trouves: {len(prediction_with_odds.market_edges)}")
    print("\nTop 5 Edges:")
    sorted_edges = sorted(
        prediction_with_odds.market_edges.values(),
        key=lambda e: e.edge_after_liquidity,
        reverse=True
    )[:5]

    for edge in sorted_edges:
        print(f"  {edge.market.value}: prob={edge.probability:.1%}, odds={edge.market_odds:.2f}, "
              f"edge={edge.edge_after_liquidity:.1%}, kelly={edge.kelly_fraction:.1%}, "
              f"signal={edge.signal_strength.value}, meets_threshold={edge.meets_threshold}")

    if prediction_with_odds.best_bet:
        print(f"\nBest Bet: {prediction_with_odds.best_bet.market.value}")
        print(f"   Edge: {prediction_with_odds.best_bet.edge.edge_after_liquidity:.1%}")
        print(f"   Stake: {prediction_with_odds.best_bet.stake_percentage:.1%} ({prediction_with_odds.best_bet.stake_units:.2f}EUR)")
        print(f"   Reasons: {prediction_with_odds.best_bet.reasons}")

    if prediction_with_odds.best_bets_by_category:
        print("\nBest Bets by Category:")
        for cat, rec in prediction_with_odds.best_bets_by_category.items():
            print(f"  {cat}: {rec.market.value} ({rec.edge.edge_after_liquidity:.1%})")

    # Stats
    print("\nStatistiques")
    print("-" * 60)
    stats = brain.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 80)
    print("TESTS V2.7 TERMINES - 93 MARCHES")
    print("=" * 80)
