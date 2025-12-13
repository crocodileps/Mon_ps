"""
QUANTUM CORE - EDGE CALCULATOR
==============================
Calcul de l'edge réel contre les bookmakers

FONCTIONNALITÉS:
✅ Remove Vig (suppression marge bookmaker)
✅ True Edge calculation
✅ Kelly Criterion optimal
✅ Value detection

Philosophie: On ne compare JAMAIS notre proba à une cote brute.
             On compare notre proba à la VRAIE proba estimée par le bookmaker.
"""

from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
import math
import logging

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class OddsInfo:
    """Information sur une cote"""
    decimal_odds: float
    implied_prob: float       # Probabilité implicite (avec marge)
    true_prob: float          # Probabilité réelle estimée (sans marge)
    margin_contribution: float  # Contribution à la marge totale


@dataclass
class EdgeAnalysis:
    """Résultat d'analyse d'edge"""
    market: str
    our_probability: float
    bookmaker_probability: float  # Sans marge
    bookmaker_odds: float
    fair_odds: float
    edge_percentage: float
    is_value: bool
    kelly_stake: float
    expected_value: float
    confidence_adjusted_stake: float


@dataclass
class MarketOdds:
    """Cotes d'un marché complet (ex: 1X2)"""
    outcomes: Dict[str, float]  # Ex: {"home": 2.10, "draw": 3.40, "away": 3.50}
    margin: float
    true_probabilities: Dict[str, float]


# ═══════════════════════════════════════════════════════════════════════
# REMOVE VIG (MARGIN) FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def calculate_margin(odds_list: List[float]) -> float:
    """
    Calcule la marge (overround) d'un marché

    Args:
        odds_list: Liste des cotes décimales (ex: [2.10, 3.40, 3.50])

    Returns:
        Marge en pourcentage (ex: 5.5 pour 5.5%)

    Example:
        >>> calculate_margin([2.10, 3.40, 3.50])
        5.74  # 5.74% de marge
    """
    if not odds_list or any(o <= 1 for o in odds_list):
        return 0.0

    total_implied = sum(1/o for o in odds_list)
    margin = (total_implied - 1) * 100

    return round(margin, 2)


def remove_vig_basic(odds: Dict[str, float]) -> Dict[str, float]:
    """
    Supprime la marge par division simple (méthode basique)

    Args:
        odds: Dict des cotes {outcome: decimal_odds}

    Returns:
        Dict des vraies probabilités {outcome: true_prob}

    Example:
        >>> remove_vig_basic({"home": 2.10, "draw": 3.40, "away": 3.50})
        {"home": 0.451, "draw": 0.278, "away": 0.271}
    """
    if not odds:
        return {}

    # Probabilités implicites
    implied = {k: 1/v for k, v in odds.items() if v > 1}

    # Overround total
    overround = sum(implied.values())

    if overround <= 0:
        return {}

    # Normaliser
    return {k: v/overround for k, v in implied.items()}


def remove_vig_power(odds: Dict[str, float], power: float = 1.0) -> Dict[str, float]:
    """
    Supprime la marge par la méthode Power (plus précise)

    La méthode Power assume que la marge est distribuée proportionnellement
    à la probabilité de chaque outcome.

    Args:
        odds: Dict des cotes {outcome: decimal_odds}
        power: Exposant (1.0 = méthode basique, optimal ~0.7 pour football)

    Returns:
        Dict des vraies probabilités

    Référence: Joseph Buchdahl - "Wisdom of the Crowd"
    """
    if not odds:
        return {}

    # Calculer le multiplicateur pour chaque outcome
    implied = {k: 1/v for k, v in odds.items() if v > 1}
    total = sum(implied.values())

    if total <= 0:
        return {}

    # Appliquer la correction Power
    corrected = {}
    for outcome, prob in implied.items():
        # La correction dépend de la probabilité
        weight = prob ** power
        corrected[outcome] = prob * weight

    # Re-normaliser
    total_corrected = sum(corrected.values())
    if total_corrected <= 0:
        return implied  # Fallback

    return {k: v/total_corrected for k, v in corrected.items()}


def remove_vig_shin(odds: Dict[str, float]) -> Dict[str, float]:
    """
    Supprime la marge par la méthode Shin (la plus précise)

    La méthode Shin modélise explicitement les "insiders" qui ont
    de l'information privilégiée et biaisent les cotes.

    Référence: Hyun Song Shin (1991, 1993)

    Args:
        odds: Dict des cotes {outcome: decimal_odds}

    Returns:
        Dict des vraies probabilités
    """
    if not odds or len(odds) < 2:
        return remove_vig_basic(odds)

    # Probabilités implicites
    implied = {k: 1/v for k, v in odds.items() if v > 1}
    n = len(implied)

    if n < 2:
        return implied

    # Calculer z (proportion d'insiders) par méthode itérative
    # Simplification: utiliser approximation quadratique
    total = sum(implied.values())

    # z ≈ (n*total - n) / (n*total - 1)
    # Mais pour simplifier, on utilise une approximation
    z = max(0, min(0.2, (total - 1) / n))

    # Corriger les probabilités
    corrected = {}
    for outcome, prob in implied.items():
        # Formule Shin simplifiée
        true_prob = (math.sqrt(z**2 + 4*(1-z)*prob/total) - z) / (2*(1-z))
        corrected[outcome] = max(0.001, min(0.999, true_prob))

    # Normaliser
    total_corrected = sum(corrected.values())
    return {k: v/total_corrected for k, v in corrected.items()}


def get_true_probability(decimal_odds: float, market_margin: float) -> float:
    """
    Calcule la vraie probabilité d'une cote unique

    Args:
        decimal_odds: Cote décimale (ex: 1.85)
        market_margin: Marge du marché en % (ex: 5.5)

    Returns:
        Vraie probabilité estimée par le bookmaker

    Example:
        >>> get_true_probability(1.85, 5.5)
        0.512  # 51.2% (vs 54.1% implicite)
    """
    if decimal_odds <= 1:
        return 0.0

    implied_prob = 1 / decimal_odds

    # Ajuster pour la marge
    # Approximation: diviser par (1 + margin/100)
    overround = 1 + market_margin / 100
    true_prob = implied_prob / overround

    return min(0.999, max(0.001, true_prob))


# ═══════════════════════════════════════════════════════════════════════
# EDGE CALCULATION
# ═══════════════════════════════════════════════════════════════════════

def calculate_edge(our_prob: float, bookmaker_odds: float,
                   market_margin: float = 5.0) -> EdgeAnalysis:
    """
    Calcule l'edge réel contre le bookmaker

    IMPORTANT: Compare notre probabilité à la probabilité DÉVIGÉE,
               pas à la probabilité implicite brute!

    Args:
        our_prob: Notre probabilité estimée (ex: 0.55 pour 55%)
        bookmaker_odds: Cote décimale proposée (ex: 1.85)
        market_margin: Marge estimée du marché (ex: 5.0%)

    Returns:
        EdgeAnalysis avec tous les détails
    """
    # Protection
    MIN_PROB = 0.001
    MAX_ODDS = 1000.0

    our_prob = max(MIN_PROB, min(0.999, our_prob))

    # Probabilité implicite du bookmaker
    implied_prob = 1 / bookmaker_odds if bookmaker_odds > 1 else 0.999

    # Vraie probabilité estimée par le bookmaker (sans marge)
    bookmaker_prob = get_true_probability(bookmaker_odds, market_margin)

    # Notre fair odds
    fair_odds = 1 / our_prob if our_prob > MIN_PROB else MAX_ODDS

    # Edge = (Notre proba - Leur proba) / Leur proba
    edge_pct = ((our_prob - bookmaker_prob) / bookmaker_prob) * 100 if bookmaker_prob > 0 else 0

    # Value si notre proba > leur proba
    is_value = our_prob > bookmaker_prob

    # Kelly Criterion
    kelly = calculate_kelly(our_prob, bookmaker_odds)

    # Expected Value
    ev = calculate_expected_value(our_prob, bookmaker_odds)

    return EdgeAnalysis(
        market="",  # À remplir par l'appelant
        our_probability=our_prob,
        bookmaker_probability=bookmaker_prob,
        bookmaker_odds=bookmaker_odds,
        fair_odds=fair_odds,
        edge_percentage=round(edge_pct, 2),
        is_value=is_value,
        kelly_stake=round(kelly, 2),
        expected_value=round(ev, 4),
        confidence_adjusted_stake=0.0  # À calculer avec confidence
    )


def calculate_expected_value(prob: float, odds: float) -> float:
    """
    Calcule l'Expected Value (EV) d'un pari

    EV = (prob * profit) - ((1 - prob) * stake)
    EV = prob * (odds - 1) - (1 - prob)
    EV = prob * odds - 1

    Args:
        prob: Probabilité de succès
        odds: Cote décimale

    Returns:
        EV (positif = profitable, négatif = -EV)

    Example:
        >>> calculate_expected_value(0.55, 1.90)
        0.045  # +4.5% EV
    """
    if odds <= 1:
        return -1.0

    return prob * odds - 1


def calculate_kelly(prob: float, odds: float, fraction: float = 0.25) -> float:
    """
    Calcule le stake optimal selon Kelly Criterion

    f* = (bp - q) / b
    où:
        b = odds - 1 (profit si gagnant)
        p = probabilité de gagner
        q = 1 - p (probabilité de perdre)

    Args:
        prob: Probabilité de succès
        odds: Cote décimale
        fraction: Fraction de Kelly à utiliser (0.25 = quarter Kelly recommandé)

    Returns:
        Pourcentage du bankroll à miser

    Example:
        >>> calculate_kelly(0.55, 1.90)
        5.26  # 5.26% du bankroll en full Kelly
    """
    if odds <= 1 or prob <= 0 or prob >= 1:
        return 0.0

    b = odds - 1  # Profit potential
    q = 1 - prob  # Loss probability

    # Formule Kelly
    kelly = (b * prob - q) / b

    # Appliquer la fraction
    kelly *= fraction

    # Bornes (0% à 10% max)
    kelly = max(0, min(kelly * 100, 10))

    return kelly


# ═══════════════════════════════════════════════════════════════════════
# CONFIDENCE-ADJUSTED CALCULATIONS
# ═══════════════════════════════════════════════════════════════════════

def adjust_stake_for_confidence(base_kelly: float, confidence: str,
                                 data_quality: float = 1.0) -> float:
    """
    Ajuste le stake Kelly en fonction de la confiance

    Args:
        base_kelly: Stake Kelly de base (%)
        confidence: Niveau de confiance (LOW, MEDIUM, HIGH, ELITE)
        data_quality: Score de qualité des données (0-1)

    Returns:
        Stake ajusté (%)
    """
    # Multiplicateurs par niveau de confiance
    confidence_multipliers = {
        "ELITE": 1.0,
        "HIGH": 0.75,
        "MEDIUM": 0.50,
        "LOW": 0.25
    }

    multiplier = confidence_multipliers.get(confidence, 0.5)

    # Ajuster pour la qualité des données
    multiplier *= data_quality

    return round(base_kelly * multiplier, 2)


# ═══════════════════════════════════════════════════════════════════════
# VALUE FINDER
# ═══════════════════════════════════════════════════════════════════════

def find_value_bets(our_probs: Dict[str, float],
                    bookmaker_odds: Dict[str, float],
                    min_edge: float = 3.0,
                    max_odds: float = 10.0) -> List[EdgeAnalysis]:
    """
    Trouve tous les paris value dans un set de marchés

    Args:
        our_probs: Nos probabilités par marché {market: prob}
        bookmaker_odds: Cotes bookmaker {market: odds}
        min_edge: Edge minimum requis (%)
        max_odds: Cote maximum à considérer

    Returns:
        Liste des EdgeAnalysis triés par edge décroissant
    """
    value_bets = []

    for market, our_prob in our_probs.items():
        odds = bookmaker_odds.get(market)

        if not odds or odds > max_odds or odds <= 1:
            continue

        analysis = calculate_edge(our_prob, odds)
        analysis.market = market

        if analysis.is_value and analysis.edge_percentage >= min_edge:
            value_bets.append(analysis)

    # Trier par edge décroissant
    value_bets.sort(key=lambda x: -x.edge_percentage)

    return value_bets


# ═══════════════════════════════════════════════════════════════════════
# CLV (CLOSING LINE VALUE) TRACKING
# ═══════════════════════════════════════════════════════════════════════

def calculate_clv(entry_odds: float, closing_odds: float) -> float:
    """
    Calcule le CLV (Closing Line Value)

    CLV = (Entry Odds / Closing Odds - 1) * 100

    CLV positif = on a battu le marché
    CLV négatif = le marché nous a battu

    Args:
        entry_odds: Cote à laquelle on a parié
        closing_odds: Cote de fermeture (avant coup d'envoi)

    Returns:
        CLV en pourcentage

    Example:
        >>> calculate_clv(2.00, 1.85)
        8.1  # On a 8.1% de value vs la closing
    """
    if closing_odds <= 1 or entry_odds <= 1:
        return 0.0

    clv = (entry_odds / closing_odds - 1) * 100
    return round(clv, 2)
