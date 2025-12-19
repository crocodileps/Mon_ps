"""
Closing Cascade - Logique de fallback pour recuperation des closing odds
========================================================================

PHILOSOPHIE:
- Cascade de sources: Primaire -> Synthese ADN -> Estimation
- Chaque resultat inclut un score de qualite
- Le CLV est pondere par la qualite de la source

AUTEUR: Claude Code
DATE: 2025-12-19
VERSION: 1.0.0
"""

import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

from quantum.models.market_registry import (
    MarketType,
    ClosingSource,
    get_closing_config,
    normalize_market
)
from quantum.models.closing_synthesizer_dna import (
    synthesize_btts_closing,
    synthesize_dnb_closing,
    synthesize_dc_closing
)

logger = logging.getLogger(__name__)


# ===============================================================================
#                              RESULT DATACLASS
# ===============================================================================

@dataclass
class ClosingResult:
    """
    Resultat de la recuperation de closing odds.

    Attributes:
        odds: La closing odds (None si non trouvee)
        source: La source utilisee
        quality: Score de qualite (0.0 a 1.0)
        factors_used: Dict des facteurs utilises pour la synthese
        error: Message d'erreur si echec
    """
    odds: Optional[float] = None
    source: ClosingSource = ClosingSource.NONE
    quality: float = 0.0
    factors_used: Dict[str, Any] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.factors_used is None:
            self.factors_used = {}

    @property
    def is_valid(self) -> bool:
        """True si une closing odds valide a ete trouvee."""
        return self.odds is not None and self.odds > 1.0

    @property
    def weighted_quality(self) -> float:
        """Qualite ponderee pour calcul CLV."""
        return self.quality if self.is_valid else 0.0


# ===============================================================================
#                              SOURCES PRIMAIRES
# ===============================================================================

def try_football_data_uk(
    match_id: str,
    market: MarketType,
    column: str
) -> Optional[float]:
    """
    Essaie de recuperer la closing depuis Football Data UK.

    Args:
        match_id: ID du match
        market: Type de marche
        column: Colonne dans le CSV (ex: AvgCH, AvgC>2.5)

    Returns:
        Closing odds ou None
    """
    # TODO: Implementer la requete vers football_data_uk
    # Pour l'instant, retourne None pour forcer le fallback
    logger.debug(f"Football Data UK lookup: {match_id}, {column}")
    return None


def try_betexplorer(
    match_id: str,
    market: MarketType
) -> Optional[float]:
    """
    Essaie de recuperer la closing depuis Betexplorer (table odds_betexplorer).

    Args:
        match_id: ID du match
        market: Type de marche

    Returns:
        Closing odds ou None
    """
    # TODO: Implementer la requete vers odds_betexplorer
    # Pour l'instant, retourne None pour forcer le fallback
    logger.debug(f"Betexplorer lookup: {match_id}, {market}")
    return None


def try_estimated(market: MarketType) -> float:
    """
    Retourne une estimation basee sur les moyennes historiques.

    Args:
        market: Type de marche

    Returns:
        Closing odds estimee
    """
    # Moyennes historiques par type de marche
    HISTORICAL_AVERAGES = {
        MarketType.BTTS_YES: 1.85,
        MarketType.BTTS_NO: 1.95,
        MarketType.OVER_25: 1.90,
        MarketType.UNDER_25: 1.90,
        MarketType.HOME: 2.20,
        MarketType.DRAW: 3.40,
        MarketType.AWAY: 3.50,
        MarketType.DNB_HOME: 1.65,
        MarketType.DNB_AWAY: 2.20,
        MarketType.DC_1X: 1.35,
        MarketType.DC_X2: 1.50,
        MarketType.DC_12: 1.25,
    }

    return HISTORICAL_AVERAGES.get(market, 2.00)


# ===============================================================================
#                              CASCADE PRINCIPALE
# ===============================================================================

def get_closing_odds(
    match_id: str,
    home_team: str,
    away_team: str,
    market: MarketType,
    liquid_odds: Optional[Dict[str, float]] = None
) -> ClosingResult:
    """
    Recupere la closing odds avec cascade de fallback.

    CASCADE:
    1. Source primaire (Football Data UK ou Betexplorer)
    2. Synthese ADN-aware (si cotes liquides disponibles)
    3. Estimation historique (dernier recours)

    Args:
        match_id: ID du match
        home_team: Nom equipe domicile
        away_team: Nom equipe exterieure
        market: Type de marche
        liquid_odds: Dict avec cotes liquides pour synthese
                     ex: {"home": 2.10, "draw": 3.50, "away": 3.40, "over_25": 1.75}

    Returns:
        ClosingResult avec odds, source, qualite
    """
    config = get_closing_config(market)

    if not config:
        return ClosingResult(
            odds=None,
            source=ClosingSource.NONE,
            quality=0.0,
            error=f"No closing config for market {market}"
        )

    # 1. ESSAYER SOURCE PRIMAIRE
    if config.primary_source == ClosingSource.FOOTBALL_DATA_UK:
        if config.football_data_column:
            odds = try_football_data_uk(match_id, market, config.football_data_column)
            if odds:
                quality = config.quality_by_source.get(ClosingSource.FOOTBALL_DATA_UK, 1.0)
                return ClosingResult(
                    odds=odds,
                    source=ClosingSource.FOOTBALL_DATA_UK,
                    quality=quality,
                    factors_used={"source": "primary", "column": config.football_data_column}
                )

    elif config.primary_source == ClosingSource.BETEXPLORER:
        odds = try_betexplorer(match_id, market)
        if odds:
            quality = config.quality_by_source.get(ClosingSource.BETEXPLORER, 1.0)
            return ClosingResult(
                odds=odds,
                source=ClosingSource.BETEXPLORER,
                quality=quality,
                factors_used={"source": "primary", "scraper": "betexplorer"}
            )

    # 2. ESSAYER SYNTHESE ADN
    if ClosingSource.SYNTHESIZED_DNA in config.fallback_sources:
        if liquid_odds and _has_required_odds(config.synthesis_inputs, liquid_odds):
            try:
                odds, factors = _synthesize_market(
                    market, home_team, away_team, liquid_odds
                )
                if odds:
                    quality = config.quality_by_source.get(ClosingSource.SYNTHESIZED_DNA, 0.85)
                    return ClosingResult(
                        odds=odds,
                        source=ClosingSource.SYNTHESIZED_DNA,
                        quality=quality,
                        factors_used=factors
                    )
            except Exception as e:
                logger.warning(f"Synthesis failed for {market}: {e}")

    # 3. ESSAYER ESTIMATION
    if ClosingSource.ESTIMATED in config.fallback_sources:
        odds = try_estimated(market)
        quality = config.quality_by_source.get(ClosingSource.ESTIMATED, 0.6)
        return ClosingResult(
            odds=odds,
            source=ClosingSource.ESTIMATED,
            quality=quality,
            factors_used={"source": "estimated", "method": "historical_average"}
        )

    # 4. ECHEC TOTAL
    return ClosingResult(
        odds=None,
        source=ClosingSource.NONE,
        quality=0.0,
        error="All sources failed"
    )


def _has_required_odds(required: list, available: dict) -> bool:
    """Verifie si toutes les cotes requises sont disponibles."""
    mapping = {
        "home_closing": "home",
        "draw_closing": "draw",
        "away_closing": "away",
        "over_25_closing": "over_25"
    }

    for req in required:
        key = mapping.get(req, req)
        if key not in available or not available[key]:
            return False
    return True


def _synthesize_market(
    market: MarketType,
    home_team: str,
    away_team: str,
    liquid_odds: Dict[str, float]
) -> tuple:
    """Dispatch vers la bonne fonction de synthese."""

    if market in [MarketType.BTTS_YES, MarketType.BTTS_NO]:
        odds, factors = synthesize_btts_closing(
            over_25_closing=liquid_odds.get("over_25", 1.90),
            home_closing=liquid_odds.get("home", 2.50),
            away_closing=liquid_odds.get("away", 3.00),
            draw_closing=liquid_odds.get("draw", 3.50),
            home_team=home_team,
            away_team=away_team
        )
        # Pour BTTS_NO, inverser la probabilite
        if market == MarketType.BTTS_NO:
            from quantum.models.closing_synthesizer_dna import (
                odds_to_probability,
                probability_to_odds
            )
            p_btts_yes = odds_to_probability(odds)
            p_btts_no = 1 - p_btts_yes
            odds = probability_to_odds(p_btts_no)
            factors["inverted_for_btts_no"] = True
        return odds, factors

    elif market in [MarketType.DNB_HOME, MarketType.DNB_AWAY]:
        return synthesize_dnb_closing(
            home_closing=liquid_odds.get("home", 2.50),
            draw_closing=liquid_odds.get("draw", 3.50),
            home_team=home_team,
            away_team=away_team,
            for_home=(market == MarketType.DNB_HOME)
        )

    elif market in [MarketType.DC_1X, MarketType.DC_X2, MarketType.DC_12]:
        dc_type = market.value.split("_")[1]  # "1x", "x2", "12"
        return synthesize_dc_closing(
            home_closing=liquid_odds.get("home", 2.50),
            draw_closing=liquid_odds.get("draw", 3.50),
            away_closing=liquid_odds.get("away", 3.00),
            home_team=home_team,
            away_team=away_team,
            dc_type=dc_type
        )

    return None, {}


# ===============================================================================
#                              CLV CALCULATION
# ===============================================================================

def calculate_clv_weighted(
    odds_taken: float,
    closing_result: ClosingResult
) -> Dict[str, float]:
    """
    Calcule le CLV pondere par la qualite de la source.

    FORMULE:
    CLV_raw = (odds_taken / closing_odds - 1) * 100
    CLV_weighted = CLV_raw * quality

    Args:
        odds_taken: La cote a laquelle on a parie
        closing_result: Resultat de get_closing_odds

    Returns:
        Dict avec clv_raw, clv_weighted, quality, source
    """
    if not closing_result.is_valid or odds_taken <= 1:
        return {
            "clv_raw": 0.0,
            "clv_weighted": 0.0,
            "quality": 0.0,
            "source": closing_result.source.value,
            "error": closing_result.error or "Invalid data"
        }

    closing_odds = closing_result.odds

    # CLV = (odds_taken / closing - 1) * 100
    clv_raw = (odds_taken / closing_odds - 1) * 100
    clv_weighted = clv_raw * closing_result.quality

    return {
        "clv_raw": round(clv_raw, 4),
        "clv_weighted": round(clv_weighted, 4),
        "quality": closing_result.quality,
        "source": closing_result.source.value,
        "closing_odds": closing_odds,
        "odds_taken": odds_taken,
        "factors": closing_result.factors_used
    }


# ===============================================================================
#                              BATCH PROCESSING
# ===============================================================================

def get_closing_odds_batch(
    matches: list,
    markets: list
) -> Dict[str, Dict[str, ClosingResult]]:
    """
    Recupere les closing odds pour plusieurs matchs et marches.

    Args:
        matches: Liste de dicts avec {match_id, home_team, away_team, liquid_odds}
        markets: Liste de MarketType

    Returns:
        Dict[match_id][market_value] = ClosingResult
    """
    results = {}

    for match in matches:
        match_id = match.get("match_id", "unknown")
        home_team = match.get("home_team", "")
        away_team = match.get("away_team", "")
        liquid_odds = match.get("liquid_odds", {})

        results[match_id] = {}

        for market in markets:
            result = get_closing_odds(
                match_id=match_id,
                home_team=home_team,
                away_team=away_team,
                market=market,
                liquid_odds=liquid_odds
            )
            results[match_id][market.value] = result

    return results


# ===============================================================================
#                              EXPORT
# ===============================================================================

__all__ = [
    "ClosingResult",
    "get_closing_odds",
    "get_closing_odds_batch",
    "calculate_clv_weighted",
]
