"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║  CONVERGENCE ENGINE V5 - THE FORTRESS V3.8                                   ║
║  Moteur de Triangulation Quantum (Hedge Fund Grade)                          ║
║  Jour 3 - Moteurs Déterministes                                              ║
╚═══════════════════════════════════════════════════════════════════════════════╝

3 Améliorations Quant (validées par Mya):
1. Pénalité Sigmoïde - Falaise de risque (pas linéaire)
2. Regime Switching - Poids dynamiques selon contexte
3. Kill Switch - Veto asymétrique si expert confiant dit NON

Triangulation de 3 sources:
- Historical: ADN statistique passé
- Friction: Collision des styles (friction_matrix)
- Claude: Analyse tactique LLM (future)

Installation: /home/Mon_ps/quantum_sovereign/strategies/convergence_engine.py
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
import math
import logging

logger = logging.getLogger("quantum_sovereign.strategies")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION GLOBALE (TOUS LES PARAMÈTRES CALIBRABLES)
# ═══════════════════════════════════════════════════════════════════════════════

CONVERGENCE_CONFIG = {
    # ─────────────────────────────────────────────────────────────────────────
    # SIGMOÏDE - Contrôle la "falaise" de pénalité
    # ─────────────────────────────────────────────────────────────────────────
    "sigmoid_k": 15.0,              # Raideur (plus haut = falaise plus abrupte)
    "sigmoid_threshold": 0.20,      # Point de bascule (20% d'écart-type)

    # ─────────────────────────────────────────────────────────────────────────
    # SEUILS DE VALIDATION
    # ─────────────────────────────────────────────────────────────────────────
    "min_convergence_score": 50.0,  # Score minimum pour valider un pari

    # ─────────────────────────────────────────────────────────────────────────
    # VETO (Kill Switch)
    # ─────────────────────────────────────────────────────────────────────────
    "veto_enabled": True,           # Activer/désactiver le veto
    "veto_confidence_min": 0.80,    # Confiance min pour pouvoir vétoer
    "veto_prob_max": 0.30,          # Proba max pour déclencher veto
    "veto_consensus_min": 0.60,     # Consensus min pour que veto s'applique

    # ─────────────────────────────────────────────────────────────────────────
    # POIDS PAR RÉGIME (Regime Switching)
    # ─────────────────────────────────────────────────────────────────────────
    "regime_weights": {
        "CALM": {
            "Historical": 1.0,
            "Friction": 1.0,
            "Claude": 0.8,
        },
        "VOLATILE": {
            "Historical": 0.6,      # Stats moins fiables
            "Friction": 1.2,        # Physique compte plus
            "Claude": 1.0,
        },
        "CHAOTIC": {
            "Historical": 0.2,      # Stats quasi-ignorées
            "Friction": 1.5,        # Friction domine
            "Claude": 1.2,          # Info qualitative critique
        },
    },

    # ─────────────────────────────────────────────────────────────────────────
    # FEATURES TOGGLES (pour désactiver certaines améliorations)
    # ─────────────────────────────────────────────────────────────────────────
    "use_sigmoid_penalty": True,    # Utiliser falaise sigmoïde
    "use_regime_switching": True,   # Utiliser poids dynamiques
    "use_veto": True,               # Utiliser kill switch
}


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class MarketRegime(Enum):
    """Régime de marché pour ajuster les poids"""
    CALM = "CALM"           # Match standard, stats fiables
    VOLATILE = "VOLATILE"   # Mouvements de cotes, incertitude
    CHAOTIC = "CHAOTIC"     # Derby, météo extrême, coupe


class SignalSourceType(Enum):
    """Types de sources de signal"""
    HISTORICAL = "Historical"   # ADN statistique
    FRICTION = "Friction"       # Collision des styles
    CLAUDE = "Claude"           # Analyse LLM


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SignalSource:
    """
    Une source de signal pour la triangulation.

    Attributes:
        name: Nom de la source ("Historical", "Friction", "Claude")
        probability: Prédiction de probabilité (0.0 à 1.0)
        confidence: Niveau de confiance de la source (0.0 à 1.0)
        metadata: Données supplémentaires optionnelles
    """
    name: str
    probability: float
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validation des bornes"""
        self.probability = max(0.0, min(1.0, self.probability))
        self.confidence = max(0.0, min(1.0, self.confidence))


@dataclass
class ConvergenceResult:
    """
    Résultat du moteur de convergence.

    Attributes:
        consensus_probability: Probabilité fusionnée (0.0 à 1.0)
        convergence_score: Score de qualité du signal (0-100)
        divergence: Écart-type entre les sources
        regime_used: Régime de marché utilisé
        is_valid: True si score >= seuil minimum
        is_vetoed: True si veto activé
        veto_reason: Raison du veto si applicable
        primary_conflict: Source en conflit principal
        weights_applied: Poids effectifs appliqués
    """
    consensus_probability: float
    convergence_score: float
    divergence: float
    regime_used: str
    is_valid: bool
    is_vetoed: bool = False
    veto_reason: Optional[str] = None
    primary_conflict: Optional[str] = None
    weights_applied: Dict[str, float] = field(default_factory=dict)

    @property
    def should_bet(self) -> bool:
        """True si on devrait parier (valid ET pas veto)"""
        return self.is_valid and not self.is_vetoed

    @property
    def risk_level(self) -> str:
        """Niveau de risque basé sur le score"""
        if self.convergence_score >= 80:
            return "LOW"
        elif self.convergence_score >= 60:
            return "MEDIUM"
        elif self.convergence_score >= 40:
            return "HIGH"
        else:
            return "EXTREME"


# ═══════════════════════════════════════════════════════════════════════════════
# CONVERGENCE ENGINE V5
# ═══════════════════════════════════════════════════════════════════════════════

class ConvergenceEngine:
    """
    Moteur de Triangulation V5 (Quantum Convergence).

    Fusionne 3 sources de signal (Historical, Friction, Claude) avec:
    1. Pénalité Sigmoïde - Score s'effondre si divergence critique
    2. Regime Switching - Poids dynamiques selon contexte match
    3. Kill Switch - Veto si expert confiant dit NON

    Usage:
        engine = ConvergenceEngine()

        signals = [
            SignalSource("Historical", probability=0.65, confidence=0.90),
            SignalSource("Friction", probability=0.60, confidence=0.85),
            SignalSource("Claude", probability=0.70, confidence=0.75),
        ]

        result = engine.calculate(signals, regime=MarketRegime.CALM)

        if result.should_bet:
            print(f"BET: {result.consensus_probability:.1%}")
        else:
            print(f"SKIP: {result.veto_reason or 'Low convergence'}")
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Args:
            config: Configuration custom (override CONVERGENCE_CONFIG)
        """
        self.config = {**CONVERGENCE_CONFIG, **(config or {})}
        logger.info(
            f"ConvergenceEngine V5 initialized "
            f"(sigmoid={self.config['use_sigmoid_penalty']}, "
            f"regime={self.config['use_regime_switching']}, "
            f"veto={self.config['use_veto']})"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTHODE PRINCIPALE
    # ═══════════════════════════════════════════════════════════════════════════

    def calculate(
        self,
        signals: List[SignalSource],
        regime: MarketRegime = MarketRegime.CALM
    ) -> ConvergenceResult:
        """
        Calcule le consensus et le score de convergence.

        Args:
            signals: Liste des sources de signal
            regime: Régime de marché actuel

        Returns:
            ConvergenceResult avec probabilité, score, et validité
        """
        if not signals:
            return self._empty_result(regime)

        # 1. AJUSTER LES POIDS SELON LE RÉGIME
        if self.config["use_regime_switching"]:
            adjusted_signals, weights_applied = self._apply_regime_weights(signals, regime)
        else:
            adjusted_signals = signals
            weights_applied = {s.name: s.confidence for s in signals}

        # 2. EXTRAIRE LES VECTEURS
        probs = [s.probability for s in adjusted_signals]
        confs = [s.confidence for s in adjusted_signals]
        names = [s.name for s in adjusted_signals]

        # Safety: Si confiance totale = 0
        total_conf = sum(confs)
        if total_conf == 0:
            return self._empty_result(regime, reason="No confidence data")

        # 3. CALCULER LA MOYENNE PONDÉRÉE
        weighted_mean = sum(p * c for p, c in zip(probs, confs)) / total_conf

        # 4. CALCULER LA DIVERGENCE (Écart-type pondéré)
        variance = sum(c * (p - weighted_mean) ** 2 for p, c in zip(probs, confs)) / total_conf
        std_dev = math.sqrt(variance)

        # 5. CALCULER LE SCORE DE CONVERGENCE
        if self.config["use_sigmoid_penalty"]:
            convergence_score = self._sigmoid_score(std_dev)
        else:
            convergence_score = self._linear_score(std_dev)

        # 6. IDENTIFIER LE CONFLIT PRINCIPAL
        primary_conflict = self._identify_conflict(names, probs, confs, weighted_mean, std_dev)

        # 7. VÉRIFIER LE VETO (Kill Switch)
        is_vetoed = False
        veto_reason = None

        if self.config["use_veto"] and self.config["veto_enabled"]:
            is_vetoed, veto_reason = self._check_veto(
                names, probs, confs, weighted_mean
            )
            if is_vetoed:
                convergence_score = 0.0
                logger.warning(f"VETO ACTIVÉ: {veto_reason}")

        # 8. DÉTERMINER VALIDITÉ
        is_valid = convergence_score >= self.config["min_convergence_score"]

        result = ConvergenceResult(
            consensus_probability=round(weighted_mean, 4),
            convergence_score=round(convergence_score, 2),
            divergence=round(std_dev, 4),
            regime_used=regime.value,
            is_valid=is_valid,
            is_vetoed=is_vetoed,
            veto_reason=veto_reason,
            primary_conflict=primary_conflict,
            weights_applied=weights_applied
        )

        # Log résultat
        self._log_result(result)

        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # AMÉLIORATION #1: PÉNALITÉ SIGMOÏDE
    # ═══════════════════════════════════════════════════════════════════════════

    def _sigmoid_score(self, divergence: float) -> float:
        """
        Calcule le score avec pénalité sigmoïde (falaise).

        La fonction sigmoïde crée une "falaise":
        - divergence < threshold: Score proche de 100%
        - divergence > threshold: Score s'effondre vers 0%

        Formule: 100 * (1 / (1 + exp(k * (sigma - threshold))))

        Args:
            divergence: Écart-type entre les sources

        Returns:
            Score 0-100
        """
        k = self.config["sigmoid_k"]
        threshold = self.config["sigmoid_threshold"]

        # Sigmoïde inversée: haute quand divergence faible
        sigmoid = 1.0 / (1.0 + math.exp(k * (divergence - threshold)))

        return 100.0 * sigmoid

    def _linear_score(self, divergence: float) -> float:
        """
        Score linéaire classique (fallback si sigmoïde désactivée).

        Formule: 100 * (1 - divergence / tolerance)
        """
        tolerance = self.config["sigmoid_threshold"] * 2  # Plus permissif
        raw_score = 100.0 * (1.0 - divergence / tolerance)
        return max(0.0, min(100.0, raw_score))

    # ═══════════════════════════════════════════════════════════════════════════
    # AMÉLIORATION #2: REGIME SWITCHING
    # ═══════════════════════════════════════════════════════════════════════════

    def _apply_regime_weights(
        self,
        signals: List[SignalSource],
        regime: MarketRegime
    ) -> tuple:
        """
        Applique les multiplicateurs de poids selon le régime.

        En régime CHAOTIC, l'historique compte moins (0.2x),
        la friction compte plus (1.5x).

        Args:
            signals: Signaux originaux
            regime: Régime de marché

        Returns:
            (signaux_ajustés, poids_appliqués)
        """
        regime_weights = self.config["regime_weights"].get(
            regime.value,
            self.config["regime_weights"]["CALM"]
        )

        adjusted_signals = []
        weights_applied = {}

        for signal in signals:
            multiplier = regime_weights.get(signal.name, 1.0)
            adjusted_confidence = signal.confidence * multiplier

            adjusted_signal = SignalSource(
                name=signal.name,
                probability=signal.probability,
                confidence=adjusted_confidence,
                metadata=signal.metadata
            )
            adjusted_signals.append(adjusted_signal)
            weights_applied[signal.name] = round(adjusted_confidence, 3)

        logger.debug(f"Regime {regime.value}: weights={weights_applied}")

        return adjusted_signals, weights_applied

    # ═══════════════════════════════════════════════════════════════════════════
    # AMÉLIORATION #3: KILL SWITCH (VETO)
    # ═══════════════════════════════════════════════════════════════════════════

    def _check_veto(
        self,
        names: List[str],
        probs: List[float],
        confs: List[float],
        consensus: float
    ) -> tuple:
        """
        Vérifie si un expert confiant déclenche le veto.

        Conditions du veto:
        1. Une source a confiance > veto_confidence_min (80%)
        2. Cette source prédit proba < veto_prob_max (30%)
        3. Le consensus global est > veto_consensus_min (60%)

        = Un expert confiant dit "NON" alors que les autres disent "OUI"

        Args:
            names: Noms des sources
            probs: Probabilités prédites
            confs: Confiances
            consensus: Probabilité consensus

        Returns:
            (is_vetoed, veto_reason)
        """
        veto_conf_min = self.config["veto_confidence_min"]
        veto_prob_max = self.config["veto_prob_max"]
        veto_consensus_min = self.config["veto_consensus_min"]

        for i, name in enumerate(names):
            # Expert très confiant ET prédit NON ET consensus dit OUI
            if (confs[i] >= veto_conf_min and
                probs[i] <= veto_prob_max and
                consensus >= veto_consensus_min):

                reason = (
                    f"VETO by {name}: "
                    f"Prob={probs[i]:.1%} (conf={confs[i]:.1%}) "
                    f"vs Consensus={consensus:.1%}"
                )
                return True, reason

        return False, None

    # ═══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════════════

    def _identify_conflict(
        self,
        names: List[str],
        probs: List[float],
        confs: List[float],
        mean: float,
        std_dev: float
    ) -> Optional[str]:
        """Identifie la source la plus éloignée du consensus"""

        # Seuil pour considérer qu'il y a conflit
        if std_dev < self.config["sigmoid_threshold"] / 2:
            return None

        max_diff = 0
        conflict_source = None

        for i, name in enumerate(names):
            diff = abs(probs[i] - mean)
            if diff > max_diff:
                max_diff = diff
                conflict_source = f"{name} (diff={diff:.1%})"

        return conflict_source

    def _empty_result(
        self,
        regime: MarketRegime,
        reason: str = "No signals"
    ) -> ConvergenceResult:
        """Retourne un résultat vide/invalide"""
        return ConvergenceResult(
            consensus_probability=0.0,
            convergence_score=0.0,
            divergence=0.0,
            regime_used=regime.value,
            is_valid=False,
            is_vetoed=False,
            veto_reason=reason,
            primary_conflict=None,
            weights_applied={}
        )

    def _log_result(self, result: ConvergenceResult):
        """Log le résultat avec le bon niveau"""
        if result.is_vetoed:
            logger.warning(
                f"CONVERGENCE VETOED: {result.veto_reason} "
                f"(consensus={result.consensus_probability:.1%})"
            )
        elif not result.is_valid:
            logger.info(
                f"CONVERGENCE LOW: score={result.convergence_score:.0f} "
                f"(consensus={result.consensus_probability:.1%}, "
                f"divergence={result.divergence:.3f})"
            )
        else:
            logger.debug(
                f"CONVERGENCE OK: score={result.convergence_score:.0f} "
                f"(consensus={result.consensus_probability:.1%})"
            )

    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTHODES UTILITAIRES
    # ═══════════════════════════════════════════════════════════════════════════

    def create_historical_signal(
        self,
        win_rate: float,
        sample_size: int,
        min_sample: int = 20
    ) -> SignalSource:
        """
        Crée un signal Historical avec confiance basée sur sample size.

        Args:
            win_rate: Taux de victoire historique (0-1)
            sample_size: Nombre de matchs
            min_sample: Sample pour 100% confiance

        Returns:
            SignalSource configuré
        """
        confidence = min(1.0, sample_size / min_sample)
        return SignalSource(
            name="Historical",
            probability=win_rate,
            confidence=confidence,
            metadata={"sample_size": sample_size}
        )

    def create_friction_signal(
        self,
        friction_prob: float,
        match_quality: float = 0.85
    ) -> SignalSource:
        """
        Crée un signal Friction avec confiance standard.

        Args:
            friction_prob: Probabilité calculée par friction matrix
            match_quality: Qualité du matchup (0-1)

        Returns:
            SignalSource configuré
        """
        return SignalSource(
            name="Friction",
            probability=friction_prob,
            confidence=match_quality,
            metadata={"source": "friction_matrix_12x12"}
        )

    def create_claude_signal(
        self,
        claude_prob: float,
        confidence: float = 0.70
    ) -> SignalSource:
        """
        Crée un signal Claude (LLM) avec confiance prudente.

        Note: Claude peut halluciner, confiance par défaut 70%

        Args:
            claude_prob: Probabilité estimée par Claude
            confidence: Niveau de confiance (défaut 70%)

        Returns:
            SignalSource configuré
        """
        return SignalSource(
            name="Claude",
            probability=claude_prob,
            confidence=confidence,
            metadata={"source": "llm_tactical_analysis"}
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TEST RAPIDE
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    engine = ConvergenceEngine()

    print("\n" + "="*70)
    print("TEST 1: CONVERGENCE NORMALE (Accord)")
    print("="*70)

    signals_accord = [
        SignalSource("Historical", probability=0.65, confidence=0.90),
        SignalSource("Friction", probability=0.60, confidence=0.85),
        SignalSource("Claude", probability=0.70, confidence=0.75),
    ]

    result = engine.calculate(signals_accord, regime=MarketRegime.CALM)
    print(f"Consensus: {result.consensus_probability:.1%}")
    print(f"Score: {result.convergence_score:.0f}/100")
    print(f"Divergence: {result.divergence:.3f}")
    print(f"Valid: {result.is_valid} | Should bet: {result.should_bet}")
    print(f"Risk level: {result.risk_level}")

    print("\n" + "="*70)
    print("TEST 2: DÉSACCORD MAJEUR (Score s'effondre)")
    print("="*70)

    signals_desaccord = [
        SignalSource("Historical", probability=0.90, confidence=0.90),
        SignalSource("Friction", probability=0.85, confidence=0.85),
        SignalSource("Claude", probability=0.20, confidence=0.70),
    ]

    result = engine.calculate(signals_desaccord, regime=MarketRegime.CALM)
    print(f"Consensus: {result.consensus_probability:.1%}")
    print(f"Score: {result.convergence_score:.0f}/100 (FALAISE)")
    print(f"Divergence: {result.divergence:.3f}")
    print(f"Valid: {result.is_valid} | Conflict: {result.primary_conflict}")

    print("\n" + "="*70)
    print("TEST 3: VETO (Expert confiant dit NON)")
    print("="*70)

    signals_veto = [
        SignalSource("Historical", probability=0.90, confidence=0.90),
        SignalSource("Friction", probability=0.90, confidence=0.85),
        SignalSource("Claude", probability=0.10, confidence=0.95),  # VETO!
    ]

    result = engine.calculate(signals_veto, regime=MarketRegime.CALM)
    print(f"Consensus: {result.consensus_probability:.1%}")
    print(f"Score: {result.convergence_score:.0f}/100")
    print(f"VETOED: {result.is_vetoed}")
    print(f"Veto reason: {result.veto_reason}")
    print(f"Should bet: {result.should_bet}")

    print("\n" + "="*70)
    print("TEST 4: RÉGIME CHAOTIC (Poids ajustés)")
    print("="*70)

    signals_chaos = [
        SignalSource("Historical", probability=0.80, confidence=0.90),
        SignalSource("Friction", probability=0.50, confidence=0.85),
        SignalSource("Claude", probability=0.55, confidence=0.80),
    ]

    result_calm = engine.calculate(signals_chaos, regime=MarketRegime.CALM)
    result_chaotic = engine.calculate(signals_chaos, regime=MarketRegime.CHAOTIC)

    print(f"CALM:    Consensus={result_calm.consensus_probability:.1%}, "
          f"Weights={result_calm.weights_applied}")
    print(f"CHAOTIC: Consensus={result_chaotic.consensus_probability:.1%}, "
          f"Weights={result_chaotic.weights_applied}")
    print("(En CHAOTIC, Historical compte moins, Friction compte plus)")

    print("\n" + "="*70)
    print("TEST 5: DÉSACTIVER SIGMOÏDE (Mode linéaire)")
    print("="*70)

    engine_linear = ConvergenceEngine(config={"use_sigmoid_penalty": False})

    result_linear = engine_linear.calculate(signals_desaccord, regime=MarketRegime.CALM)
    result_sigmoid = engine.calculate(signals_desaccord, regime=MarketRegime.CALM)

    print(f"Linéaire: Score={result_linear.convergence_score:.0f}")
    print(f"Sigmoïde: Score={result_sigmoid.convergence_score:.0f}")
    print("(Sigmoïde pénalise plus durement les désaccords)")
