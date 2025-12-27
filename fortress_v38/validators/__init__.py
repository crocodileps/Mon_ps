"""
FORTRESS V38 - VALIDATORS
=========================

Validation des données et vérification de fraîcheur.

Modules:
- data_validator: Validation complète des entrées
- freshness_checker: Vérification de l'âge des données

Version: 1.0.0
"""

# ═══════════════════════════════════════════════════════════════
# DATA VALIDATOR
# ═══════════════════════════════════════════════════════════════

from .data_validator import (
    # Enums
    ValidationSeverity,
    # Dataclasses
    ValidationIssue,
    ValidationResult,
    # Classe principale
    DataValidator,
    # Exceptions
    DataValidationError,
)

# ═══════════════════════════════════════════════════════════════
# FRESHNESS CHECKER
# ═══════════════════════════════════════════════════════════════

from .freshness_checker import (
    # Enums
    FreshnessStatus,
    # Dataclasses
    FreshnessResult,
    # Classe principale
    FreshnessChecker,
    # Exceptions
    DataTooOldError,
)

# ═══════════════════════════════════════════════════════════════
# EXPORTS PUBLICS
# ═══════════════════════════════════════════════════════════════

__all__ = [
    # Data Validator
    "ValidationSeverity",
    "ValidationIssue",
    "ValidationResult",
    "DataValidator",
    "DataValidationError",
    # Freshness Checker
    "FreshnessStatus",
    "FreshnessResult",
    "FreshnessChecker",
    "DataTooOldError",
]

__version__ = "1.0.0"
