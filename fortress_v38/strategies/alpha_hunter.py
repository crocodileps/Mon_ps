"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║  ALPHA HUNTER - THE FORTRESS V3.8                                            ║
║  Scanner de marchés avec améliorations Quant                                 ║
║  Jour 3 - Moteurs Déterministes                                              ║
╚═══════════════════════════════════════════════════════════════════════════════╝

3 Améliorations Quant (validées par Mya):
1. Lissage Bayésien - Utiliser petits échantillons intelligemment
2. Corrélation Pruning - Éliminer marchés redondants
3. Seuils Dynamiques - Adapter au régime de volatilité

Installation: /home/Mon_ps/quantum_sovereign/strategies/alpha_hunter.py
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger("quantum_sovereign.strategies")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS ET CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

class MarketRegime(Enum):
    """Régime de volatilité du marché"""
    CALM = "calm"          # Marché stable, seuils normaux
    VOLATILE = "volatile"  # Mouvements importants, seuils +50%
    CHAOTIC = "chaotic"    # Situation exceptionnelle, seuils +100%


class FilterLevel(Enum):
    """Niveaux de filtrage progressif"""
    STRICT = "strict"      # Défaut: odds 1.50-2.50, edge 3%, sample 15
    RELAXED = "relaxed"    # Fallback: odds 1.40-2.80, edge 2.5%, sample 10
    WIDE = "wide"          # Dernier recours: odds 1.30-3.00, edge 2%, sample 5


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MarketCandidate:
    """Un marché candidat identifié par l'Alpha Hunter"""
    market: str                    # Nom du marché (ex: "over_2.5")
    raw_win_rate: float           # Win rate brut (0.0 à 1.0)
    bayesian_win_rate: float      # Win rate ajusté Bayésien
    sample_size: int              # Nombre de matchs historiques
    edge: float                   # Edge calculé (prob - implied_prob)
    odds: float                   # Cote actuelle
    implied_prob: float           # Probabilité implicite (1/odds)
    score: float                  # Score final pour ranking
    confidence: float             # Niveau de confiance (0-100)
    filter_level: FilterLevel     # Niveau de filtre utilisé

    def __post_init__(self):
        """Calculs automatiques après initialisation"""
        if self.implied_prob == 0:
            self.implied_prob = 1 / self.odds if self.odds > 0 else 0


@dataclass
class AlphaHunterResult:
    """Résultat complet du scan Alpha Hunter"""
    candidates: List[MarketCandidate] = field(default_factory=list)
    pruned_candidates: List[MarketCandidate] = field(default_factory=list)
    regime: MarketRegime = MarketRegime.CALM
    filter_level_used: FilterLevel = FilterLevel.STRICT
    total_scanned: int = 0
    total_passed: int = 0
    total_after_pruning: int = 0
    scan_timestamp: datetime = field(default_factory=datetime.now)

    @property
    def best_candidate(self) -> Optional[MarketCandidate]:
        """Retourne le meilleur candidat après pruning"""
        return self.pruned_candidates[0] if self.pruned_candidates else None

    @property
    def has_opportunities(self) -> bool:
        """True si au moins une opportunité trouvée"""
        return len(self.pruned_candidates) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# ALPHA HUNTER - CLASSE PRINCIPALE
# ═══════════════════════════════════════════════════════════════════════════════

class AlphaHunter:
    """
    Scanner de marchés Hedge Fund Grade avec 3 améliorations Quant.

    Améliorations:
    1. Lissage Bayésien: Permet d'utiliser des échantillons < 15 matchs
    2. Corrélation Pruning: Élimine marchés redondants (Under2.5 + BTTSNo)
    3. Seuils Dynamiques: Adapte les seuils au régime de volatilité

    Usage:
        hunter = AlphaHunter()
        result = hunter.scan(
            team_dna={"btts_pct": 55, "over25_pct": 60, ...},
            available_odds={"over_2.5": 1.85, "btts_yes": 1.90, ...},
            regime=MarketRegime.CALM
        )

        if result.has_opportunities:
            best = result.best_candidate
            print(f"Best: {best.market} @ {best.odds} (edge={best.edge:.1%})")
    """

    # ═══════════════════════════════════════════════════════════════════════════
    # CONFIGURATION DES FILTRES
    # ═══════════════════════════════════════════════════════════════════════════

    FILTER_CONFIG = {
        FilterLevel.STRICT: {
            "odds_min": 1.50,
            "odds_max": 2.50,
            "edge_min": 0.03,      # 3%
            "sample_min": 15,
            "confidence_min": 60,
        },
        FilterLevel.RELAXED: {
            "odds_min": 1.40,
            "odds_max": 2.80,
            "edge_min": 0.025,     # 2.5%
            "sample_min": 10,
            "confidence_min": 50,
        },
        FilterLevel.WIDE: {
            "odds_min": 1.30,
            "odds_max": 3.00,
            "edge_min": 0.02,      # 2%
            "sample_min": 5,
            "confidence_min": 40,
        },
    }

    # ═══════════════════════════════════════════════════════════════════════════
    # FACTEURS DE VOLATILITÉ PAR RÉGIME
    # ═══════════════════════════════════════════════════════════════════════════

    REGIME_VOLATILITY_FACTORS = {
        MarketRegime.CALM: 0.0,      # Pas d'ajustement
        MarketRegime.VOLATILE: 0.5,  # +50% sur les seuils
        MarketRegime.CHAOTIC: 1.0,   # +100% sur les seuils
    }

    # ═══════════════════════════════════════════════════════════════════════════
    # MATRICE DE CORRÉLATION ENTRE MARCHÉS
    # ═══════════════════════════════════════════════════════════════════════════

    CORRELATION_MATRIX = {
        # Marchés buts - très corrélés
        ("under_2.5", "btts_no"): 0.85,
        ("under_2.5", "cs_0_0"): 0.90,
        ("under_2.5", "cs_1_0"): 0.75,
        ("under_2.5", "cs_0_1"): 0.75,
        ("under_2.5", "under_1.5"): 0.80,
        ("btts_no", "cs_0_0"): 0.95,
        ("btts_no", "cs_1_0"): 0.80,
        ("btts_no", "cs_0_1"): 0.80,
        ("btts_no", "under_1.5"): 0.75,

        # Marchés buts - corrélés positifs
        ("over_2.5", "btts_yes"): 0.80,
        ("over_2.5", "over_3.5"): 0.85,
        ("over_2.5", "over_1.5"): 0.70,
        ("btts_yes", "over_3.5"): 0.70,
        ("btts_yes", "over_1.5"): 0.65,

        # Marchés résultat
        ("home_win", "home_or_draw"): 0.75,
        ("away_win", "away_or_draw"): 0.75,
        ("draw", "under_2.5"): 0.60,
        ("draw", "btts_no"): 0.55,

        # Double chance
        ("home_or_draw", "under_2.5"): 0.40,
        ("away_or_draw", "under_2.5"): 0.40,
    }

    # ═══════════════════════════════════════════════════════════════════════════
    # MAPPING DNA → MARCHÉ
    # ═══════════════════════════════════════════════════════════════════════════

    DNA_TO_MARKET_MAPPING = {
        "btts_pct": "btts_yes",
        "over25_pct": "over_2.5",
        "over35_pct": "over_3.5",
        "under25_pct": "under_2.5",
        "under15_pct": "under_1.5",
        "cs_pct": "clean_sheet",
        "home_win_pct": "home_win",
        "away_win_pct": "away_win",
        "draw_pct": "draw",
    }

    # ═══════════════════════════════════════════════════════════════════════════
    # BAYESIAN PRIORS
    # ═══════════════════════════════════════════════════════════════════════════

    BAYESIAN_ALPHA = 2.0  # Prior succès
    BAYESIAN_BETA = 2.0   # Prior échecs

    def __init__(self, correlation_threshold: float = 0.70):
        """
        Args:
            correlation_threshold: Seuil de corrélation pour pruning (défaut 0.70)
        """
        self.correlation_threshold = correlation_threshold
        logger.info(f"AlphaHunter initialized (corr_threshold={correlation_threshold})")

    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTHODE PRINCIPALE - SCAN
    # ═══════════════════════════════════════════════════════════════════════════

    def scan(
        self,
        team_dna: Dict[str, Any],
        available_odds: Dict[str, float],
        historical_stats: Optional[Dict[str, Dict]] = None,
        regime: MarketRegime = MarketRegime.CALM
    ) -> AlphaHunterResult:
        """
        Scanne tous les marchés et retourne les opportunités.

        Args:
            team_dna: DNA de l'équipe avec win rates par marché
            available_odds: Cotes disponibles {market: odds}
            historical_stats: Stats historiques optionnelles {market: {wins, total}}
            regime: Régime de volatilité actuel

        Returns:
            AlphaHunterResult avec candidats triés et prunés
        """
        result = AlphaHunterResult(regime=regime)

        # 1. SCAN avec fallback progressif STRICT → RELAXED → WIDE
        for level in [FilterLevel.STRICT, FilterLevel.RELAXED, FilterLevel.WIDE]:
            candidates = self._scan_with_filter(
                team_dna=team_dna,
                available_odds=available_odds,
                historical_stats=historical_stats,
                regime=regime,
                filter_level=level
            )

            if candidates:
                result.candidates = candidates
                result.filter_level_used = level
                result.total_passed = len(candidates)
                break

        result.total_scanned = len(available_odds)

        # 2. TRIER par score (meilleur en premier)
        result.candidates.sort(key=lambda x: x.score, reverse=True)

        # 3. PRUNING des corrélations
        result.pruned_candidates = self._prune_correlated(result.candidates)
        result.total_after_pruning = len(result.pruned_candidates)

        # 4. LOG résultat
        logger.info(
            f"AlphaHunter scan: {result.total_scanned} scanned → "
            f"{result.total_passed} passed → {result.total_after_pruning} after pruning "
            f"(filter={result.filter_level_used.value}, regime={regime.value})"
        )

        return result

    def _scan_with_filter(
        self,
        team_dna: Dict[str, Any],
        available_odds: Dict[str, float],
        historical_stats: Optional[Dict[str, Dict]],
        regime: MarketRegime,
        filter_level: FilterLevel
    ) -> List[MarketCandidate]:
        """Scanne avec un niveau de filtre spécifique"""

        config = self.FILTER_CONFIG[filter_level]
        candidates = []

        # Ajuster edge_min selon régime
        effective_edge_min = self._get_dynamic_threshold(
            config["edge_min"],
            regime
        )

        for dna_key, market in self.DNA_TO_MARKET_MAPPING.items():
            # Vérifier si on a les données
            if dna_key not in team_dna:
                continue
            if market not in available_odds:
                continue

            odds = available_odds[market]

            # Filtre odds range
            if not (config["odds_min"] <= odds <= config["odds_max"]):
                continue

            # Récupérer stats
            raw_win_rate = team_dna[dna_key] / 100.0  # Convertir % en ratio

            # Stats historiques si disponibles
            if historical_stats and market in historical_stats:
                hist = historical_stats[market]
                wins = hist.get("wins", 0)
                total = hist.get("total", 0)
            else:
                # Estimer depuis win rate et sample minimum
                total = config["sample_min"]
                wins = int(raw_win_rate * total)

            # Filtre sample size (mais Bayésien permet plus petit)
            min_sample = max(5, config["sample_min"] // 2)  # Au moins 5
            if total < min_sample:
                continue

            # AMÉLIORATION #1: Lissage Bayésien
            bayesian_win_rate = self._bayesian_win_rate(wins, total)

            # Calculer edge
            implied_prob = 1 / odds
            edge = bayesian_win_rate - implied_prob

            # Filtre edge minimum (dynamique selon régime)
            if edge < effective_edge_min:
                continue

            # Calculer score et confidence
            score = self._calculate_score(edge, bayesian_win_rate, total)
            confidence = self._calculate_confidence(edge, total, filter_level)

            # Filtre confidence
            if confidence < config["confidence_min"]:
                continue

            # Créer candidat
            candidate = MarketCandidate(
                market=market,
                raw_win_rate=raw_win_rate,
                bayesian_win_rate=bayesian_win_rate,
                sample_size=total,
                edge=edge,
                odds=odds,
                implied_prob=implied_prob,
                score=score,
                confidence=confidence,
                filter_level=filter_level
            )

            candidates.append(candidate)

        return candidates

    # ═══════════════════════════════════════════════════════════════════════════
    # AMÉLIORATION #1: LISSAGE BAYÉSIEN
    # ═══════════════════════════════════════════════════════════════════════════

    def _bayesian_win_rate(self, wins: int, total: int) -> float:
        """
        Calcule la probabilité bayésienne avec shrinkage vers 50%.

        Formule: (wins + alpha) / (total + alpha + beta)

        Permet d'utiliser des échantillons plus petits (5-10 matchs)
        en les "punissant" mathématiquement vers la moyenne.

        Exemple:
        - 6 matchs, 5 victoires (83% brut)
        - Bayésien: (5+2)/(6+4) = 70% → Plus conservateur

        Args:
            wins: Nombre de succès
            total: Nombre total d'essais

        Returns:
            Probabilité ajustée (0.0 à 1.0)
        """
        return (wins + self.BAYESIAN_ALPHA) / (total + self.BAYESIAN_ALPHA + self.BAYESIAN_BETA)

    # ═══════════════════════════════════════════════════════════════════════════
    # AMÉLIORATION #2: CORRÉLATION PRUNING
    # ═══════════════════════════════════════════════════════════════════════════

    def _prune_correlated(
        self,
        candidates: List[MarketCandidate]
    ) -> List[MarketCandidate]:
        """
        Élimine les marchés trop corrélés pour diversifier le portefeuille.

        Exemple problématique AVANT pruning:
        1. Under 2.5 (edge 4.5%)
        2. BTTS No (edge 4.2%)
        3. CS 0-0 (edge 3.8%)
        → Si score = 1-1, les TROIS perdent !

        APRÈS pruning:
        1. Under 2.5 (edge 4.5%) ✓
        2. Home Win (edge 3.5%) ✓ (non corrélé)

        Args:
            candidates: Liste triée par score (meilleur en premier)

        Returns:
            Liste prunée de candidats diversifiés
        """
        if not candidates:
            return []

        pruned = [candidates[0]]  # Le meilleur passe toujours

        for candidate in candidates[1:]:
            is_correlated = False

            for selected in pruned:
                corr = self._get_correlation(selected.market, candidate.market)
                if corr >= self.correlation_threshold:
                    is_correlated = True
                    logger.debug(
                        f"Pruned {candidate.market} "
                        f"(corr={corr:.2f} with {selected.market})"
                    )
                    break

            if not is_correlated:
                pruned.append(candidate)

        return pruned

    def _get_correlation(self, market_a: str, market_b: str) -> float:
        """Retourne la corrélation entre deux marchés (0.0 si inconnue)"""
        key = (market_a.lower(), market_b.lower())
        reverse_key = (market_b.lower(), market_a.lower())

        return (
            self.CORRELATION_MATRIX.get(key) or
            self.CORRELATION_MATRIX.get(reverse_key) or
            0.0
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # AMÉLIORATION #3: SEUILS DYNAMIQUES
    # ═══════════════════════════════════════════════════════════════════════════

    def _get_dynamic_threshold(
        self,
        base_threshold: float,
        regime: MarketRegime
    ) -> float:
        """
        Calcule le seuil dynamique selon le régime de marché.

        Formule: seuil_effectif = seuil_base × (1 + facteur_volatilité)

        Exemples:
        - CALM: 3% × 1.0 = 3%
        - VOLATILE: 3% × 1.5 = 4.5%
        - CHAOTIC: 3% × 2.0 = 6%

        Args:
            base_threshold: Seuil de base (ex: 0.03 pour 3%)
            regime: Régime de marché actuel

        Returns:
            Seuil ajusté
        """
        factor = self.REGIME_VOLATILITY_FACTORS.get(regime, 0.0)
        return base_threshold * (1 + factor)

    # ═══════════════════════════════════════════════════════════════════════════
    # CALCULS AUXILIAIRES
    # ═══════════════════════════════════════════════════════════════════════════

    def _calculate_score(
        self,
        edge: float,
        win_rate: float,
        sample_size: int
    ) -> float:
        """
        Calcule un score composite pour ranking.

        Score = Edge × Win Rate × Sample Factor

        Sample Factor = min(1.0, sample_size / 20)
        → Pénalise légèrement les petits échantillons
        """
        sample_factor = min(1.0, sample_size / 20)
        return edge * win_rate * sample_factor * 100  # Normaliser

    def _calculate_confidence(
        self,
        edge: float,
        sample_size: int,
        filter_level: FilterLevel
    ) -> float:
        """
        Calcule le niveau de confiance (0-100).

        Basé sur:
        - Edge (plus c'est haut, plus confiant)
        - Sample size (plus c'est grand, plus confiant)
        - Filter level (STRICT = plus confiant)
        """
        # Base confidence from edge (edge 5% = 50 points)
        edge_confidence = min(50, edge * 1000)

        # Sample confidence (20 samples = 30 points max)
        sample_confidence = min(30, sample_size * 1.5)

        # Filter bonus
        filter_bonus = {
            FilterLevel.STRICT: 20,
            FilterLevel.RELAXED: 10,
            FilterLevel.WIDE: 0,
        }

        return edge_confidence + sample_confidence + filter_bonus[filter_level]


# ═══════════════════════════════════════════════════════════════════════════════
# TEST RAPIDE
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    hunter = AlphaHunter()

    # Simuler DNA d'une équipe
    team_dna = {
        "btts_pct": 55,      # 55% BTTS
        "over25_pct": 60,    # 60% Over 2.5
        "under25_pct": 40,   # 40% Under 2.5
        "cs_pct": 25,        # 25% Clean Sheet
        "home_win_pct": 45,
        "draw_pct": 28,
    }

    # Simuler cotes disponibles
    available_odds = {
        "btts_yes": 1.85,
        "btts_no": 1.95,
        "over_2.5": 1.90,
        "under_2.5": 1.90,
        "home_win": 2.10,
        "draw": 3.40,
        "cs_0_0": 8.50,
    }

    # Simuler historique
    historical_stats = {
        "btts_yes": {"wins": 11, "total": 20},
        "over_2.5": {"wins": 13, "total": 20},
        "under_2.5": {"wins": 7, "total": 20},
        "home_win": {"wins": 9, "total": 20},
    }

    print("\n" + "="*60)
    print("TEST ALPHA HUNTER - RÉGIME CALM")
    print("="*60)

    result = hunter.scan(
        team_dna=team_dna,
        available_odds=available_odds,
        historical_stats=historical_stats,
        regime=MarketRegime.CALM
    )

    print(f"\nScanned: {result.total_scanned}")
    print(f"Passed filter: {result.total_passed}")
    print(f"After pruning: {result.total_after_pruning}")
    print(f"Filter used: {result.filter_level_used.value}")

    print("\nCandidats APRÈS pruning:")
    for i, c in enumerate(result.pruned_candidates, 1):
        print(f"  {i}. {c.market}: odds={c.odds}, edge={c.edge:.1%}, "
              f"bayesian_wr={c.bayesian_win_rate:.1%}, score={c.score:.1f}")

    print("\n" + "="*60)
    print("TEST ALPHA HUNTER - RÉGIME VOLATILE (+50% seuils)")
    print("="*60)

    result_volatile = hunter.scan(
        team_dna=team_dna,
        available_odds=available_odds,
        historical_stats=historical_stats,
        regime=MarketRegime.VOLATILE
    )

    print(f"\nAfter pruning (VOLATILE): {result_volatile.total_after_pruning}")
    print("(Moins de candidats car seuils plus stricts)")

    print("\n" + "="*60)
    print("TEST CORRÉLATION PRUNING")
    print("="*60)

    # Forcer des marchés corrélés
    correlated_dna = {
        "btts_pct": 30,      # Faible BTTS
        "under25_pct": 70,   # Fort Under 2.5
    }
    correlated_odds = {
        "btts_no": 1.50,     # Corrélé avec Under
        "under_2.5": 1.55,   # Leader
        "cs_0_0": 7.00,      # Ultra corrélé
    }
    correlated_hist = {
        "btts_no": {"wins": 14, "total": 20},
        "under_2.5": {"wins": 15, "total": 20},
    }

    result_corr = hunter.scan(
        team_dna=correlated_dna,
        available_odds=correlated_odds,
        historical_stats=correlated_hist,
        regime=MarketRegime.CALM
    )

    print(f"\nAvant pruning: {result_corr.total_passed} candidats")
    print(f"Après pruning: {result_corr.total_after_pruning} candidats")
    print("(Les marchés corrélés sont éliminés)")
