"""
THE QUANTUM SOVEREIGN V3.8 - ERROR TAXONOMY
Classification des erreurs par sévérité.
Créé le: 23 Décembre 2025
"""

from enum import Enum
from typing import Dict, Optional
from datetime import datetime


# ═══════════════════════════════════════════════════════════
# SEVERITY LEVELS
# ═══════════════════════════════════════════════════════════

class ErrorSeverity(Enum):
    """
    Classification des erreurs par niveau de gravité.
    Détermine le comportement du système face à l'erreur.
    """
    RECOVERABLE = "recoverable"    # Retry possible (network timeout)
    SKIP_MATCH = "skip_match"      # Skip ce match, continue les autres
    FATAL = "fatal"                # Stop le système + Alert


# ═══════════════════════════════════════════════════════════
# BASE EXCEPTION
# ═══════════════════════════════════════════════════════════

class MonPSError(Exception):
    """
    Exception de base pour tout le système Mon_PS.
    Toutes les exceptions custom héritent de cette classe.
    """
    severity: ErrorSeverity = ErrorSeverity.SKIP_MATCH

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        """Sérialise l'erreur pour logging/audit"""
        return {
            "error_type": self.__class__.__name__,
            "severity": self.severity.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


# ═══════════════════════════════════════════════════════════
# RECOVERABLE ERRORS (Retry automatique)
# ═══════════════════════════════════════════════════════════

class ClaudeTimeoutError(MonPSError):
    """Claude API n'a pas répondu dans le délai imparti"""
    severity = ErrorSeverity.RECOVERABLE


class ClaudeRateLimitError(MonPSError):
    """Claude API rate limit atteint"""
    severity = ErrorSeverity.RECOVERABLE


class RSSFetchError(MonPSError):
    """Échec de récupération des flux RSS"""
    severity = ErrorSeverity.RECOVERABLE


class DatabaseConnectionError(MonPSError):
    """Connexion à PostgreSQL échouée"""
    severity = ErrorSeverity.RECOVERABLE


class NetworkTimeoutError(MonPSError):
    """Timeout réseau générique"""
    severity = ErrorSeverity.RECOVERABLE


# ═══════════════════════════════════════════════════════════
# SKIP_MATCH ERRORS (Ce match uniquement)
# ═══════════════════════════════════════════════════════════

class TeamNotFoundError(MonPSError):
    """Équipe non trouvée dans la base de données"""
    severity = ErrorSeverity.SKIP_MATCH


class DataValidationError(MonPSError):
    """Données invalides (hors range, incohérentes)"""
    severity = ErrorSeverity.SKIP_MATCH


class StaleDataError(MonPSError):
    """Données trop anciennes pour être fiables"""
    severity = ErrorSeverity.SKIP_MATCH


class NoAlphaFoundError(MonPSError):
    """Aucun marché ne passe les filtres AlphaHunter"""
    severity = ErrorSeverity.SKIP_MATCH


class LowConvergenceError(MonPSError):
    """Score de convergence trop bas"""
    severity = ErrorSeverity.SKIP_MATCH


class BlackSwanDetectedError(MonPSError):
    """Événement Black Swan détecté (match annulé, etc.)"""
    severity = ErrorSeverity.SKIP_MATCH


class MarketTrapError(MonPSError):
    """Marché identifié comme piège"""
    severity = ErrorSeverity.SKIP_MATCH


class InsufficientLiquidityError(MonPSError):
    """Liquidité insuffisante sur le marché"""
    severity = ErrorSeverity.SKIP_MATCH


# ═══════════════════════════════════════════════════════════
# FATAL ERRORS (Stop système)
# ═══════════════════════════════════════════════════════════

class ModelBugError(MonPSError):
    """Bug dans le code du modèle"""
    severity = ErrorSeverity.FATAL


class ConfigurationError(MonPSError):
    """Erreur de configuration système"""
    severity = ErrorSeverity.FATAL


class DatabaseCorruptionError(MonPSError):
    """Corruption détectée dans la base de données"""
    severity = ErrorSeverity.FATAL


class CriticalDriftError(MonPSError):
    """Dérive critique du modèle détectée"""
    severity = ErrorSeverity.FATAL


class BudgetExceededError(MonPSError):
    """Budget Claude dépassé (ne devrait pas arriver)"""
    severity = ErrorSeverity.FATAL


# ═══════════════════════════════════════════════════════════
# ERROR HANDLER
# ═══════════════════════════════════════════════════════════

def handle_error(error: MonPSError, state: Dict) -> Dict:
    """
    Gestion centralisée des erreurs.

    Args:
        error: L'exception MonPSError
        state: Le MatchState actuel

    Returns:
        Le state mis à jour avec l'erreur loggée
    """
    import logging
    logger = logging.getLogger("quantum_sovereign")

    # Log l'erreur
    logger.error(
        f"[{error.severity.value.upper()}] {error.__class__.__name__}: {error.message}"
    )

    # Ajoute l'erreur au state
    if "errors" not in state:
        state["errors"] = []

    state["errors"].append(error.to_dict())

    # Action selon la sévérité
    if error.severity == ErrorSeverity.RECOVERABLE:
        # Le retry est géré par tenacity au niveau appelant
        raise error

    elif error.severity == ErrorSeverity.SKIP_MATCH:
        state["processing_status"] = "skipped"
        return state

    elif error.severity == ErrorSeverity.FATAL:
        state["processing_status"] = "error"
        # Envoyer alerte (sera implémenté dans monitoring)
        logger.critical(f"FATAL ERROR: {error.message}")
        raise SystemExit(f"Fatal error: {error.message}")

    return state


# ═══════════════════════════════════════════════════════════
# UTILITY
# ═══════════════════════════════════════════════════════════

def is_recoverable(error: Exception) -> bool:
    """Vérifie si une erreur est recoverable (pour retry)"""
    if isinstance(error, MonPSError):
        return error.severity == ErrorSeverity.RECOVERABLE
    return False
