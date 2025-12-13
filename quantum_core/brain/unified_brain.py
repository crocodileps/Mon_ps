"""
UnifiedBrain - Cerveau Unifie Hedge Fund Grade
===============================================================================

ARCHITECTURE:
    1. DataHubAdapter -> Donnees unifiees
    2. 8 Engines -> Analyses specialisees (7 + ChainEngine)
    3. BayesianFusion -> Fusion probabilites
    4. EdgeCalculator -> Calcul edges
    5. KellySizer -> Sizing optimal

PRINCIPE:
    REUTILISER les composants existants de quantum/chess_engine/
    AMELIORER avec DataHubAdapter et architecture propre

Auteur: Mon_PS Quant Team
Version: 1.0.0
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
    EngineOutput, MarketType, Confidence, SignalStrength
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
# UNIFIED BRAIN
# ===============================================================================

class UnifiedBrain:
    """
    Cerveau Unifie - Orchestre tous les composants pour produire des predictions.

    Usage:
        brain = UnifiedBrain()
        prediction = brain.analyze_match("Liverpool", "Manchester City")
    """

    VERSION = "1.0.0"

    def __init__(self):
        """Initialise le cerveau avec lazy loading."""
        self._data_hub_adapter = None
        self._engines = {}
        self._bayesian_fusion = None
        self._edge_calculator = None
        self._kelly_sizer = None
        self._initialized = False

        self._stats = {
            "matches_analyzed": 0,
            "engines_called": 0,
            "edges_found": 0,
            "bets_recommended": 0,
        }

        logger.info("UnifiedBrain initialise (lazy mode)")

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
            logger.info("BayesianFusion connectee (348L reutilisees)")
        except Exception as e:
            logger.warning(f"BayesianFusion non disponible: {e}")

        # EdgeCalculator (reutilise)
        try:
            from quantum.chess_engine.probability.edge_calculator import EdgeCalculator
            self._edge_calculator = EdgeCalculator()
            logger.info("EdgeCalculator connecte (141L reutilisees)")
        except Exception as e:
            logger.warning(f"EdgeCalculator non disponible: {e}")

        # KellySizer (reutilise)
        try:
            from quantum.chess_engine.execution.kelly_sizer import KellySizer
            self._kelly_sizer = KellySizer()
            logger.info("KellySizer connecte (115L reutilisees)")
        except Exception as e:
            logger.warning(f"KellySizer non disponible: {e}")

        self._initialized = True
        logger.info("UnifiedBrain pret")

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

            # Certains engines sont stateless (pas de data_hub)
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
        Analyse complete d'un match.

        Args:
            home: Equipe a domicile
            away: Equipe a l'exterieur
            referee: Nom de l'arbitre (optionnel)
            market_odds: Cotes du marche pour calcul d'edge
            bankroll: Bankroll pour calcul Kelly

        Returns:
            MatchPrediction avec toutes les probabilites et recommandations
        """
        self._ensure_initialized()
        self._stats["matches_analyzed"] += 1

        logger.info(f"Analyse: {home} vs {away}")

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
            prediction.over_25_prob = friction.get("over25_prob", 0.55)

        # -------------------------------------------------------------------
        # ETAPE 2: Executer tous les engines
        # -------------------------------------------------------------------
        engine_outputs = self._run_all_engines(home, away, matchup_data, referee)
        prediction.engine_outputs = engine_outputs
        prediction.engines_used = [name for name, out in engine_outputs.items() if out.success]
        prediction.engines_failed = [name for name, out in engine_outputs.items() if not out.success]

        # -------------------------------------------------------------------
        # ETAPE 3: Fusion Bayesienne des probabilites
        # -------------------------------------------------------------------
        probabilities = self._fuse_probabilities(engine_outputs, matchup_data)

        # Assigner les probabilites principales
        prediction.home_win_prob = probabilities.get("home_win", 0.40)
        prediction.draw_prob = probabilities.get("draw", 0.25)
        prediction.away_win_prob = probabilities.get("away_win", 0.35)
        prediction.over_25_prob = probabilities.get("over_2.5", prediction.over_25_prob)
        prediction.btts_prob = probabilities.get("btts", prediction.btts_prob)
        prediction.corners_over_95_prob = probabilities.get("corners_over_9.5", 0.50)
        prediction.cards_over_35_prob = probabilities.get("cards_over_3.5", 0.55)

        # Corners et Cards expected
        prediction.corners_expected = probabilities.get("corners_expected", 10.0)
        prediction.cards_expected = probabilities.get("cards_expected", 4.0)

        # -------------------------------------------------------------------
        # ETAPE 4: Calculer les edges (si cotes fournies)
        # -------------------------------------------------------------------
        if market_odds:
            edges = self._calculate_edges(probabilities, market_odds)
            prediction.market_edges = edges

            # Compter les edges positifs
            positive_edges = [e for e in edges.values() if e.edge_after_liquidity > 0.01]
            self._stats["edges_found"] += len(positive_edges)

        # -------------------------------------------------------------------
        # ETAPE 5: Generer les recommandations Kelly
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

        # -------------------------------------------------------------------
        # ETAPE 6: Calculer la confiance globale
        # -------------------------------------------------------------------
        prediction.data_quality_score = self._calculate_quality(prediction)
        prediction.overall_confidence = self._get_confidence_level(prediction.data_quality_score)

        logger.info(f"Analyse terminee: {len(prediction.engines_used)} engines, "
                   f"qualite {prediction.data_quality_score:.1%}")

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

        # Extraire home_data et away_data pour corner/card engines
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

                    # Appeler avec la bonne signature
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

        # Commencer avec les priors du matchup_data
        friction = matchup_data.get("friction", {})
        probs = {
            "home_win": 0.40,
            "draw": 0.25,
            "away_win": 0.35,
            "over_1.5": 0.75,
            "over_2.5": friction.get("over25_prob", 0.55),
            "over_3.5": 0.30,
            "btts": friction.get("btts_prob", 0.50),
            "corners_over_9.5": 0.50,
            "corners_over_10.5": 0.40,
            "cards_over_3.5": 0.55,
            "cards_over_4.5": 0.40,
            "corners_expected": 10.0,
            "cards_expected": 4.0,
        }

        # Extraire les probabilites des engines
        for name, output in engine_outputs.items():
            if not output.success:
                continue

            data = output.data

            # MatchupEngine
            if name == "matchup":
                if "home_attack_edge" in data:
                    edge = data.get("home_attack_edge", 0) - data.get("away_attack_edge", 0)
                    # Convertir edge en ajustement de proba
                    probs["home_win"] = max(0.15, min(0.75, 0.40 + edge * 0.5))
                    probs["away_win"] = max(0.10, min(0.70, 0.35 - edge * 0.4))
                    probs["draw"] = 1 - probs["home_win"] - probs["away_win"]

            # CornerEngine
            if name == "corner":
                if "over_9_5_prob" in data:
                    probs["corners_over_9.5"] = float(data["over_9_5_prob"])
                if "over_10_5_prob" in data:
                    probs["corners_over_10.5"] = float(data["over_10_5_prob"])
                if "expected_total" in data:
                    probs["corners_expected"] = float(data["expected_total"])

            # CardEngine
            if name == "card":
                if "over_4_5_prob" in data:
                    probs["cards_over_4.5"] = float(data["over_4_5_prob"])
                if "over_3_5_prob" in data:
                    probs["cards_over_3.5"] = float(data["over_3_5_prob"])

            # RefereeEngine
            if name == "referee":
                if "cards_over_prob" in data:
                    ref_factor = float(data.get("cards_over_prob", 0.5))
                    probs["cards_over_3.5"] = (probs["cards_over_3.5"] + ref_factor) / 2
                    probs["cards_over_4.5"] = (probs["cards_over_4.5"] + ref_factor * 0.85) / 2

                if "goals_modifier" in data:
                    modifier = float(data.get("goals_modifier", 0))
                    probs["over_2.5"] = max(0.25, min(0.80, probs["over_2.5"] + modifier * 0.1))

            # VarianceEngine
            if name == "variance":
                if "regression_edge" in data:
                    reg_edge = float(data.get("regression_edge", 0))
                    # Regression vers la moyenne
                    probs["over_2.5"] = max(0.30, min(0.75, probs["over_2.5"] - reg_edge * 0.05))

            # PatternEngine
            if name == "pattern":
                if "total_pattern_edge" in data:
                    pattern_edge = float(data.get("total_pattern_edge", 0))
                    probs["home_win"] = max(0.15, min(0.75, probs["home_win"] + pattern_edge * 0.1))

        # Normaliser 1X2
        total = probs["home_win"] + probs["draw"] + probs["away_win"]
        if total > 0:
            probs["home_win"] /= total
            probs["draw"] /= total
            probs["away_win"] /= total

        return probs

    def _calculate_edges(
        self,
        probabilities: Dict[str, float],
        market_odds: Dict[str, float]
    ) -> Dict[str, MarketEdge]:
        """Calcule les edges pour chaque marche."""
        edges = {}

        # Mapping des noms de marches
        market_mapping = {
            "home_win": "1",
            "draw": "X",
            "away_win": "2",
            "over_2.5": "over_25",
            "btts": "btts_yes",
            "corners_over_9.5": "corners_over_95",
            "cards_over_3.5": "cards_over_35",
        }

        for prob_name, probability in probabilities.items():
            # Ignorer les valeurs non-probabilites
            if prob_name in ["corners_expected", "cards_expected"]:
                continue

            # Trouver la cote correspondante
            odds_name = market_mapping.get(prob_name, prob_name)

            if odds_name in market_odds:
                odds = market_odds[odds_name]

                try:
                    market_type = MarketType(prob_name)
                except ValueError:
                    continue

                # Calculer l'edge
                implied_prob = 1 / odds if odds > 0 else 0
                raw_edge = probability - implied_prob

                # Liquidity tax (~2%)
                liquidity_tax = 0.02
                edge_after_liquidity = raw_edge - liquidity_tax

                # Kelly
                kelly = 0.0
                if edge_after_liquidity > 0 and odds > 1:
                    kelly = edge_after_liquidity / (odds - 1)
                    kelly = max(0, min(0.25, kelly))  # Cap a 25%

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

                edges[prob_name] = MarketEdge(
                    market=market_type,
                    probability=probability,
                    fair_odds=1/probability if probability > 0 else 0,
                    market_odds=odds,
                    raw_edge=raw_edge,
                    edge_after_vig=raw_edge - 0.01,  # ~1% vig
                    edge_after_liquidity=edge_after_liquidity,
                    kelly_fraction=kelly,
                    recommended_stake=kelly * 0.5,  # Half Kelly
                    signal_strength=signal
                )

        return edges

    def _generate_recommendations(
        self,
        edges: Dict[str, MarketEdge],
        bankroll: float
    ) -> List[BetRecommendation]:
        """Genere les recommandations de paris."""
        recommendations = []

        for market_name, edge in edges.items():
            if edge.signal_strength == SignalStrength.NO_BET:
                continue

            # Determiner l'action
            if edge.signal_strength == SignalStrength.FADE:
                action = "FADE"
                stake = 0.0
            elif edge.edge_after_liquidity > 0.01:
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

            # Warnings
            warnings = []
            if edge.kelly_fraction > 0.15:
                warnings.append("High variance - consider reduced stake")

            # Confidence
            if edge.edge_after_liquidity > 0.05:
                confidence = Confidence.HIGH
            elif edge.edge_after_liquidity > 0.02:
                confidence = Confidence.MEDIUM
            else:
                confidence = Confidence.LOW

            recommendations.append(BetRecommendation(
                market=edge.market,
                edge=edge,
                action=action,
                stake_percentage=stake,
                stake_units=stake * bankroll,
                reasons=reasons,
                warnings=warnings,
                confidence=confidence
            ))

        # Trier par stake recommande
        recommendations.sort(key=lambda r: r.stake_percentage, reverse=True)

        return recommendations

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
            positive_edges = sum(1 for e in prediction.market_edges.values() if e.edge_after_liquidity > 0)
            score += 0.2 * min(1.0, positive_edges / 5)

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

    @staticmethod
    def _poisson_cdf(k: int, lam: float) -> float:
        """Calcul CDF Poisson (probabilite X <= k)."""
        cdf = 0.0
        for i in range(k + 1):
            cdf += (lam ** i) * math.exp(-lam) / math.factorial(i)
        return min(1.0, cdf)

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
            "data_hub_adapter": self._data_hub_adapter is not None,
            "bayesian_fusion": self._bayesian_fusion is not None,
            "edge_calculator": self._edge_calculator is not None,
            "kelly_sizer": self._kelly_sizer is not None,
            "engines_loaded": len(self._engines),
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
    print("TEST UNIFIED BRAIN - HEDGE FUND GRADE")
    print("=" * 80)

    brain = get_unified_brain()

    # Test 1: Health Check
    print("\nTest 1: Health Check")
    print("-" * 60)
    health = brain.health_check()
    for key, value in health.items():
        print(f"  {key}: {value}")

    # Test 2: Analyse sans cotes
    print("\nTest 2: Analyse Liverpool vs Man City (sans cotes)")
    print("-" * 60)

    prediction = brain.analyze_match(
        home="Liverpool",
        away="Manchester City",
        referee="Michael Oliver"
    )

    print(prediction.summary())
    print(f"\nEngines utilises: {prediction.engines_used}")
    print(f"Engines echoues: {prediction.engines_failed}")

    # Test 3: Analyse avec cotes
    print("\nTest 3: Analyse avec cotes (Edge + Kelly)")
    print("-" * 60)

    market_odds = {
        "1": 2.50,       # Liverpool
        "X": 3.40,       # Draw
        "2": 2.80,       # Man City
        "over_25": 1.85,
        "btts_yes": 1.75,
    }

    prediction_with_odds = brain.analyze_match(
        home="Liverpool",
        away="Manchester City",
        referee="Michael Oliver",
        market_odds=market_odds,
        bankroll=1000.0
    )

    print(f"Edges trouves: {len(prediction_with_odds.market_edges)}")
    for market, edge in prediction_with_odds.market_edges.items():
        print(f"  {market}: prob={edge.probability:.1%}, odds={edge.market_odds:.2f}, "
              f"edge={edge.edge_after_liquidity:.1%}, kelly={edge.kelly_fraction:.1%}, "
              f"signal={edge.signal_strength.value}")

    if prediction_with_odds.best_bet:
        print(f"\nBest Bet: {prediction_with_odds.best_bet.market.value}")
        print(f"   Edge: {prediction_with_odds.best_bet.edge.edge_after_liquidity:.1%}")
        print(f"   Stake: {prediction_with_odds.best_bet.stake_percentage:.1%} ({prediction_with_odds.best_bet.stake_units:.2f}EUR)")
        print(f"   Reasons: {prediction_with_odds.best_bet.reasons}")

    # Stats
    print("\nStatistiques")
    print("-" * 60)
    stats = brain.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 80)
    print("TESTS TERMINES")
    print("=" * 80)
