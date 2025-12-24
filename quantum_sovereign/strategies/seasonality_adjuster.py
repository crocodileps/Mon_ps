"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║  SEASONALITY ADJUSTER V4 ULTIMATE - THE FORTRESS V3.8                        ║
║  Ajustements saisonniers Hedge Fund Grade                                    ║
║  Jour 3 - Moteurs Déterministes (DERNIER FICHIER)                           ║
╚═══════════════════════════════════════════════════════════════════════════════╝

5 Améliorations intégrées:
1. Coach Stability: Racine carrée (récompense vite 1ère saison)
2. Rest Delta: Gradient 4 zones (CRITICAL → GREEN)
3. VACATION: -15% boost (beach mode = piège)
4. SURVIVAL: +12% boost + 1.25 volatility (combat chaotique)
5. Agrégation: Dampening (stabilité atténue fatigue)

Installation: /home/Mon_ps/quantum_sovereign/strategies/seasonality_adjuster.py
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple
from enum import Enum
import math
import logging

logger = logging.getLogger("quantum_sovereign.strategies")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION GLOBALE
# ═══════════════════════════════════════════════════════════════════════════════

SEASONALITY_CONFIG = {
    # Coach Stability
    "coach_stability_max_months": 36,      # 3 ans = stabilité max
    "coach_stability_dampening": 0.3,      # Stabilité réduit impact repos de 30% max

    # Rest Delta
    "rest_max_advantage": 0.05,            # Cap ±5%
    "rest_zones": {
        "CRITICAL": {"max_days": 2, "factor": 0.025},   # 2.5%/jour
        "RED": {"max_days": 4, "factor": 0.020},        # 2.0%/jour
        "ORANGE": {"max_days": 5, "factor": 0.010},     # 1.0%/jour
        "GREEN": {"max_days": 999, "factor": 0.005},    # 0.5%/jour
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# MOTIVATION MATRIX (avec VOLATILITY)
# ═══════════════════════════════════════════════════════════════════════════════

class MotivationZone(Enum):
    """Zones de motivation selon classement/enjeu"""
    GLORY = "GLORY"           # Course au titre
    EUROPE = "EUROPE"         # Qualification européenne
    MID_TABLE = "MID_TABLE"   # Rien à jouer
    SURVIVAL = "SURVIVAL"     # Lutte relégation
    VACATION = "VACATION"     # Saison finie mathématiquement


MOTIVATION_MATRIX = {
    # Zone: fatigue_multiplier, boost, volatility, description
    MotivationZone.GLORY: {
        "fatigue": 0.80,      # -20% impact fatigue
        "boost": 0.10,        # +10% performance
        "volatility": 0.90,   # -10% variance (concentré)
        "description": "Course au titre - Maximum focus"
    },
    MotivationZone.EUROPE: {
        "fatigue": 0.90,      # -10% impact fatigue
        "boost": 0.05,        # +5% performance
        "volatility": 1.00,   # Baseline
        "description": "Qualification européenne - Motivé"
    },
    MotivationZone.MID_TABLE: {
        "fatigue": 1.00,      # Baseline
        "boost": 0.00,        # Neutre
        "volatility": 1.00,   # Baseline
        "description": "Rien à jouer - Standard"
    },
    MotivationZone.SURVIVAL: {
        "fatigue": 0.70,      # -30% impact fatigue (adrénaline)
        "boost": 0.12,        # +12% (réduit car discipline ↓)
        "volatility": 1.25,   # +25% variance (imprévisible)
        "description": "Lutte relégation - Combat chaotique"
    },
    MotivationZone.VACATION: {
        "fatigue": 1.30,      # +30% impact fatigue
        "boost": -0.15,       # -15% performance (beach mode)
        "volatility": 1.15,   # +15% variance (rotation)
        "description": "Saison finie - Piège à parieurs"
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RestZoneInfo:
    """Information sur la zone de repos"""
    zone_name: str
    factor: float
    min_rest_days: int
    delta_days: int


@dataclass
class TeamSeasonalityFactors:
    """Facteurs saisonniers pour une équipe"""
    team_name: str
    coach_stability: float          # 0.0 à 1.0
    coach_tenure_months: int
    rest_days: int
    motivation_zone: str
    motivation_boost: float
    motivation_volatility: float
    fatigue_multiplier: float


@dataclass
class SeasonalityResult:
    """Résultat complet de l'ajustement saisonnier"""
    home_adjustment: float          # Ajustement final home
    away_adjustment: float          # Ajustement final away
    home_factors: TeamSeasonalityFactors
    away_factors: TeamSeasonalityFactors
    rest_zone: RestZoneInfo
    home_confidence_multiplier: float
    away_confidence_multiplier: float
    warnings: list = field(default_factory=list)

    @property
    def combined_volatility(self) -> float:
        """Volatilité combinée du match"""
        return (self.home_factors.motivation_volatility +
                self.away_factors.motivation_volatility) / 2

    @property
    def is_high_risk(self) -> bool:
        """True si match à haute volatilité"""
        return self.combined_volatility > 1.10


# ═══════════════════════════════════════════════════════════════════════════════
# SEASONALITY ADJUSTER V4 ULTIMATE
# ═══════════════════════════════════════════════════════════════════════════════

class SeasonalityAdjuster:
    """
    Ajusteur saisonnier V4 ULTIMATE - Hedge Fund Grade.

    5 améliorations intégrées:
    1. Coach Stability (Racine carrée)
    2. Rest Delta (Gradient 4 zones)
    3. VACATION boost renforcé (-15%)
    4. SURVIVAL avec volatility (+25%)
    5. Agrégation avec dampening correct

    Usage:
        adjuster = SeasonalityAdjuster()

        result = adjuster.calculate(
            home_coach_tenure=113,      # Guardiola
            away_coach_tenure=8,        # Nouveau coach
            home_rest_days=6,
            away_rest_days=3,
            home_motivation="GLORY",
            away_motivation="SURVIVAL"
        )

        print(f"Home adj: {result.home_adjustment:+.1%}")
        print(f"Away adj: {result.away_adjustment:+.1%}")
        print(f"High risk: {result.is_high_risk}")
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Args:
            config: Configuration custom (override SEASONALITY_CONFIG)
        """
        self.config = {**SEASONALITY_CONFIG, **(config or {})}
        logger.info("SeasonalityAdjuster V4 ULTIMATE initialized")

    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTHODE PRINCIPALE
    # ═══════════════════════════════════════════════════════════════════════════

    def calculate(
        self,
        home_coach_tenure: int,
        away_coach_tenure: int,
        home_rest_days: int,
        away_rest_days: int,
        home_motivation: str,
        away_motivation: str,
        home_team: str = "Home",
        away_team: str = "Away"
    ) -> SeasonalityResult:
        """
        Calcule les ajustements saisonniers pour un match.

        Args:
            home_coach_tenure: Ancienneté coach domicile (mois)
            away_coach_tenure: Ancienneté coach extérieur (mois)
            home_rest_days: Jours depuis dernier match (home)
            away_rest_days: Jours depuis dernier match (away)
            home_motivation: Zone motivation ("GLORY", "EUROPE", etc.)
            away_motivation: Zone motivation
            home_team: Nom équipe (pour logs)
            away_team: Nom équipe (pour logs)

        Returns:
            SeasonalityResult avec ajustements et détails
        """
        warnings = []

        # 1. COACH STABILITY (Racine carrée)
        home_stability = self._coach_stability_index(home_coach_tenure)
        away_stability = self._coach_stability_index(away_coach_tenure)

        # 2. REST DELTA (Gradient 4 zones)
        rest_info = self._calculate_rest_delta(home_rest_days, away_rest_days)

        # 3. MOTIVATION (avec volatility)
        home_motiv = self._get_motivation_factors(home_motivation)
        away_motiv = self._get_motivation_factors(away_motivation)

        # Warning si VACATION ou SURVIVAL
        if home_motivation == "VACATION":
            warnings.append(f"{home_team} en VACATION - Beach mode risk")
        if away_motivation == "VACATION":
            warnings.append(f"{away_team} en VACATION - Beach mode risk")
        if home_motivation == "SURVIVAL":
            warnings.append(f"{home_team} en SURVIVAL - Match chaotique")
        if away_motivation == "SURVIVAL":
            warnings.append(f"{away_team} en SURVIVAL - Match chaotique")

        # 4. AGRÉGATION avec dampening
        home_adj, home_conf = self._aggregate_adjustment(
            rest_adj=rest_info["home_adj"],
            motivation_boost=home_motiv["boost"],
            coach_stability=home_stability,
            motivation_volatility=home_motiv["volatility"]
        )

        away_adj, away_conf = self._aggregate_adjustment(
            rest_adj=rest_info["away_adj"],
            motivation_boost=away_motiv["boost"],
            coach_stability=away_stability,
            motivation_volatility=away_motiv["volatility"]
        )

        # 5. CONSTRUIRE RÉSULTAT
        home_factors = TeamSeasonalityFactors(
            team_name=home_team,
            coach_stability=home_stability,
            coach_tenure_months=home_coach_tenure,
            rest_days=home_rest_days,
            motivation_zone=home_motivation,
            motivation_boost=home_motiv["boost"],
            motivation_volatility=home_motiv["volatility"],
            fatigue_multiplier=home_motiv["fatigue"]
        )

        away_factors = TeamSeasonalityFactors(
            team_name=away_team,
            coach_stability=away_stability,
            coach_tenure_months=away_coach_tenure,
            rest_days=away_rest_days,
            motivation_zone=away_motivation,
            motivation_boost=away_motiv["boost"],
            motivation_volatility=away_motiv["volatility"],
            fatigue_multiplier=away_motiv["fatigue"]
        )

        rest_zone_info = RestZoneInfo(
            zone_name=rest_info["zone"],
            factor=rest_info["factor_used"],
            min_rest_days=min(home_rest_days, away_rest_days),
            delta_days=rest_info["delta_days"]
        )

        result = SeasonalityResult(
            home_adjustment=home_adj,
            away_adjustment=away_adj,
            home_factors=home_factors,
            away_factors=away_factors,
            rest_zone=rest_zone_info,
            home_confidence_multiplier=home_conf,
            away_confidence_multiplier=away_conf,
            warnings=warnings
        )

        # Log
        self._log_result(result)

        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # AMÉLIORATION #1: COACH STABILITY (Racine carrée)
    # ═══════════════════════════════════════════════════════════════════════════

    def _coach_stability_index(self, tenure_months: int) -> float:
        """
        Calcule l'indice de stabilité du coach avec racine carrée.

        Racine carrée récompense plus vite la première saison:
        - 9 mois (1 saison) → 0.50 (vs 0.25 linéaire)
        - 18 mois → 0.71
        - 36 mois → 1.00 (max)

        Args:
            tenure_months: Ancienneté en mois

        Returns:
            Indice 0.0 à 1.0
        """
        max_months = self.config["coach_stability_max_months"]

        if tenure_months <= 0:
            return 0.0

        # Racine carrée pour progression rapide au début
        index = math.sqrt(tenure_months / max_months)

        return min(1.0, index)

    # ═══════════════════════════════════════════════════════════════════════════
    # AMÉLIORATION #2: REST DELTA (Gradient 4 zones)
    # ═══════════════════════════════════════════════════════════════════════════

    def _calculate_rest_delta(
        self,
        home_rest: int,
        away_rest: int
    ) -> Dict[str, Any]:
        """
        Calcule l'avantage/désavantage de repos avec gradient 4 zones.

        Zones:
        - CRITICAL (≤2j): 2.5%/jour - Match tous les 3 jours
        - RED (3-4j): 2.0%/jour - Zone dangereuse
        - ORANGE (5j): 1.0%/jour - Transition
        - GREEN (>5j): 0.5%/jour - Les deux frais

        Args:
            home_rest: Jours de repos home
            away_rest: Jours de repos away

        Returns:
            Dict avec ajustements et info zone
        """
        delta = home_rest - away_rest
        min_rest = min(home_rest, away_rest)

        # Déterminer zone et facteur
        zone, factor = self._get_rest_zone(min_rest)

        # Calculer avantage
        raw_advantage = delta * factor

        # Cap symétrique
        max_adv = self.config["rest_max_advantage"]
        home_adj = max(-max_adv, min(max_adv, raw_advantage))
        away_adj = -home_adj

        return {
            "home_adj": round(home_adj, 4),
            "away_adj": round(away_adj, 4),
            "zone": zone,
            "factor_used": factor,
            "delta_days": delta,
            "min_rest": min_rest
        }

    def _get_rest_zone(self, min_rest_days: int) -> Tuple[str, float]:
        """Retourne (zone_name, factor) selon le nombre de jours min"""
        zones = self.config["rest_zones"]

        for zone_name in ["CRITICAL", "RED", "ORANGE", "GREEN"]:
            zone_config = zones[zone_name]
            if min_rest_days <= zone_config["max_days"]:
                return zone_name, zone_config["factor"]

        return "GREEN", zones["GREEN"]["factor"]

    # ═══════════════════════════════════════════════════════════════════════════
    # AMÉLIORATION #3 & #4: MOTIVATION MATRIX
    # ═══════════════════════════════════════════════════════════════════════════

    def _get_motivation_factors(self, zone: str) -> Dict[str, Any]:
        """
        Retourne les facteurs de motivation pour une zone.

        Inclut:
        - fatigue: Multiplicateur d'impact fatigue
        - boost: Bonus/malus performance
        - volatility: Facteur d'incertitude
        """
        # Convertir string en enum si nécessaire
        try:
            zone_enum = MotivationZone(zone)
        except ValueError:
            logger.warning(f"Zone motivation inconnue: {zone}, using MID_TABLE")
            zone_enum = MotivationZone.MID_TABLE

        return MOTIVATION_MATRIX.get(zone_enum, MOTIVATION_MATRIX[MotivationZone.MID_TABLE])

    # ═══════════════════════════════════════════════════════════════════════════
    # AMÉLIORATION #5: AGRÉGATION AVEC DAMPENING
    # ═══════════════════════════════════════════════════════════════════════════

    def _aggregate_adjustment(
        self,
        rest_adj: float,
        motivation_boost: float,
        coach_stability: float,
        motivation_volatility: float
    ) -> Tuple[float, float]:
        """
        Agrège les facteurs avec dampening correct.

        Logique:
        - Stabilité ATTÉNUE l'impact du repos (coach stable = équipe moins affectée)
        - Boost motivation reste INTÉGRAL (intrinsèque à l'équipe)
        - Volatility affecte la confiance

        Formule:
        adjustment = (rest × dampening) + motivation_boost
        dampening = 1.0 - (stability × 0.3)

        Args:
            rest_adj: Ajustement repos (-0.05 à +0.05)
            motivation_boost: Boost motivation (-0.15 à +0.12)
            coach_stability: Indice stabilité (0-1)
            motivation_volatility: Facteur volatilité (0.9-1.25)

        Returns:
            (adjustment, confidence_multiplier)
        """
        dampening_factor = self.config["coach_stability_dampening"]

        # Dampening: stabilité réduit impact repos
        dampening = 1.0 - (coach_stability * dampening_factor)

        # Repos ajusté
        rest_dampened = rest_adj * dampening

        # Final = repos dampened + boost motivation
        final_adjustment = rest_dampened + motivation_boost

        # Confidence basée sur volatility inverse
        confidence_multiplier = 1.0 / motivation_volatility

        return round(final_adjustment, 4), round(confidence_multiplier, 3)

    # ═══════════════════════════════════════════════════════════════════════════
    # LOGGING
    # ═══════════════════════════════════════════════════════════════════════════

    def _log_result(self, result: SeasonalityResult):
        """Log le résultat avec le bon niveau"""
        home = result.home_factors
        away = result.away_factors

        log_msg = (
            f"Seasonality: {home.team_name} ({home.motivation_zone}) "
            f"vs {away.team_name} ({away.motivation_zone}) | "
            f"Rest zone: {result.rest_zone.zone_name} | "
            f"Adj: {result.home_adjustment:+.1%} vs {result.away_adjustment:+.1%}"
        )

        if result.is_high_risk:
            logger.warning(f"HIGH RISK MATCH: {log_msg}")
        elif result.warnings:
            logger.info(f"{log_msg}")
        else:
            logger.debug(f"{log_msg}")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST RAPIDE
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    adjuster = SeasonalityAdjuster()

    print("\n" + "="*70)
    print("TEST 1: GUARDIOLA (113 mois) vs NOUVEAU COACH (4 mois)")
    print("="*70)

    result = adjuster.calculate(
        home_coach_tenure=113,
        away_coach_tenure=4,
        home_rest_days=6,
        away_rest_days=3,
        home_motivation="GLORY",
        away_motivation="EUROPE",
        home_team="Man City",
        away_team="Newcastle"
    )

    print(f"\nMan City (GLORY):")
    print(f"  - Coach stability: {result.home_factors.coach_stability:.2f}")
    print(f"  - Motivation boost: {result.home_factors.motivation_boost:+.1%}")
    print(f"  - Final adjustment: {result.home_adjustment:+.1%}")

    print(f"\nNewcastle (EUROPE):")
    print(f"  - Coach stability: {result.away_factors.coach_stability:.2f}")
    print(f"  - Motivation boost: {result.away_factors.motivation_boost:+.1%}")
    print(f"  - Final adjustment: {result.away_adjustment:+.1%}")

    print(f"\nRest zone: {result.rest_zone.zone_name} (factor={result.rest_zone.factor})")

    print("\n" + "="*70)
    print("TEST 2: SURVIVAL vs VACATION (Match piège)")
    print("="*70)

    result = adjuster.calculate(
        home_coach_tenure=24,
        away_coach_tenure=36,
        home_rest_days=3,
        away_rest_days=7,
        home_motivation="SURVIVAL",
        away_motivation="VACATION",
        home_team="Southampton",
        away_team="Brighton"
    )

    print(f"\nSouthampton (SURVIVAL):")
    print(f"  - Motivation boost: {result.home_factors.motivation_boost:+.1%}")
    print(f"  - Volatility: {result.home_factors.motivation_volatility}")
    print(f"  - Final adjustment: {result.home_adjustment:+.1%}")

    print(f"\nBrighton (VACATION):")
    print(f"  - Motivation boost: {result.away_factors.motivation_boost:+.1%}")
    print(f"  - Volatility: {result.away_factors.motivation_volatility}")
    print(f"  - Final adjustment: {result.away_adjustment:+.1%}")

    print(f"\nHigh risk match: {result.is_high_risk}")
    print(f"Combined volatility: {result.combined_volatility:.2f}")
    if result.warnings:
        print(f"Warnings: {result.warnings}")

    print("\n" + "="*70)
    print("TEST 3: ZONE CRITIQUE (2j vs 5j)")
    print("="*70)

    result = adjuster.calculate(
        home_coach_tenure=18,
        away_coach_tenure=18,
        home_rest_days=2,
        away_rest_days=5,
        home_motivation="MID_TABLE",
        away_motivation="MID_TABLE",
        home_team="Everton",
        away_team="Crystal Palace"
    )

    print(f"\nRest zone: {result.rest_zone.zone_name}")
    print(f"Factor: {result.rest_zone.factor} (CRITICAL = 2.5%/jour)")
    print(f"Delta: {result.rest_zone.delta_days} jours")
    print(f"Everton (2j repos): {result.home_adjustment:+.1%}")
    print(f"Crystal Palace (5j repos): {result.away_adjustment:+.1%}")

    print("\n" + "="*70)
    print("TEST 4: TOUS LES COACHS STABILITY")
    print("="*70)

    test_tenures = [0, 4, 9, 18, 36, 72, 113, 168, 219]
    print("\nTenure (mois) -> Stability Index (racine carrée)")
    for tenure in test_tenures:
        stability = adjuster._coach_stability_index(tenure)
        linear = min(1.0, tenure / 36)
        print(f"  {tenure:3d} mois -> {stability:.2f} (linéaire serait {linear:.2f})")
