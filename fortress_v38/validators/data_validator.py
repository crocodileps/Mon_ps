"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║  DATA VALIDATOR - THE FORTRESS V3.8                                          ║
║  Validation Hedge Fund Grade - Soft/Hard Thresholds                          ║
║  Jour 3 - Moteurs Déterministes                                              ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Principe: Garbage In = Garbage Out → On filtre à l'entrée.

Logique Soft/Hard:
- HARD: Valeurs impossibles (bug scraping) → REJETTE
- SOFT: Valeurs atypiques (outliers possibles) → WARNING + continue

Installation: /home/Mon_ps/quantum_sovereign/validators/data_validator.py
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum
import logging

logger = logging.getLogger("quantum_sovereign.validators")


class ValidationSeverity(Enum):
    """Niveau de sévérité des problèmes détectés"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Un problème de validation détecté"""
    field: str
    message: str
    severity: ValidationSeverity
    value: Any = None
    expected_range: Optional[tuple] = None


@dataclass
class ValidationResult:
    """Résultat complet de validation"""
    team_name: str
    is_valid: bool
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    info: List[ValidationIssue] = field(default_factory=list)

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    @property
    def error_messages(self) -> List[str]:
        return [e.message for e in self.errors]

    @property
    def warning_messages(self) -> List[str]:
        return [w.message for w in self.warnings]


class DataValidator:
    """
    Validateur de données ADN équipe - Hedge Fund Grade

    Deux niveaux de seuils:
    - HARD: Valeurs impossibles → is_valid = False (REJETTE)
    - SOFT: Valeurs atypiques → is_valid = True + warnings

    Exemple:
        xG/90 = -5.0 → HARD fail (impossible)
        xG/90 = 4.2 → SOFT warning (exceptionnel mais possible)
    """

    # ═══════════════════════════════════════════════════════════════════════════
    # SOFT THRESHOLDS - Warning mais continue (outliers possibles)
    # ═══════════════════════════════════════════════════════════════════════════
    SOFT_THRESHOLDS = {
        "xg_90": (0.5, 3.5),        # xG par 90 min
        "xga_90": (0.5, 3.0),       # xGA par 90 min
        "cs_pct": (10.0, 60.0),     # Clean Sheet %
        "possession_pct": (30.0, 70.0),  # Possession %
        "btts_pct": (20.0, 80.0),   # Both Teams To Score %
        "shots_90": (5.0, 20.0),    # Tirs par 90 min
        "shots_on_target_90": (2.0, 8.0),  # Tirs cadrés par 90 min
    }

    # ═══════════════════════════════════════════════════════════════════════════
    # HARD THRESHOLDS - Reject (bug scraping probable)
    # ═══════════════════════════════════════════════════════════════════════════
    HARD_THRESHOLDS = {
        "xg_90": (0.05, 6.0),       # Impossible < 0.05 ou > 6.0
        "xga_90": (0.05, 6.0),      # Impossible < 0.05 ou > 6.0
        "cs_pct": (0.0, 100.0),     # Pourcentage valide
        "possession_pct": (15.0, 85.0),  # Extrêmes impossibles
        "btts_pct": (0.0, 100.0),   # Pourcentage valide
        "shots_90": (0.0, 35.0),    # Max physique ~35 tirs
        "shots_on_target_90": (0.0, 15.0),  # Max réaliste
    }

    # Champs obligatoires (doit exister dans le DNA)
    REQUIRED_FIELDS = ["xg_90", "xga_90"]

    def __init__(self, strict_mode: bool = False):
        """
        Args:
            strict_mode: Si True, les warnings deviennent des errors
        """
        self.strict_mode = strict_mode
        logger.info(f"DataValidator initialized (strict_mode={strict_mode})")

    def validate_team_dna(self, team_name: str, dna: Dict[str, Any]) -> ValidationResult:
        """
        Valide le DNA complet d'une équipe.

        Args:
            team_name: Nom de l'équipe
            dna: Dictionnaire contenant les métriques ADN

        Returns:
            ValidationResult avec is_valid, errors, warnings
        """
        errors = []
        warnings = []
        info = []

        # 1. Vérifier que le DNA n'est pas vide
        if not dna:
            errors.append(ValidationIssue(
                field="dna",
                message=f"{team_name}: DNA vide ou None",
                severity=ValidationSeverity.CRITICAL,
                value=dna
            ))
            return ValidationResult(team_name=team_name, is_valid=False, errors=errors)

        # 2. Vérifier champs obligatoires
        for field in self.REQUIRED_FIELDS:
            if field not in dna or dna[field] is None:
                errors.append(ValidationIssue(
                    field=field,
                    message=f"{team_name}.{field} manquant ou None",
                    severity=ValidationSeverity.ERROR
                ))

        # 3. Vérifier les ranges (Soft + Hard)
        range_issues = self._check_ranges(team_name, dna)
        for issue in range_issues:
            if issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]:
                errors.append(issue)
            else:
                if self.strict_mode:
                    errors.append(issue)
                else:
                    warnings.append(issue)

        # 4. Vérifier cohérence inter-champs
        coherence_issues = self._check_coherence(team_name, dna)
        for issue in coherence_issues:
            if self.strict_mode:
                errors.append(issue)
            else:
                warnings.append(issue)

        # 5. Construire résultat
        is_valid = len(errors) == 0

        result = ValidationResult(
            team_name=team_name,
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            info=info
        )

        # Log le résultat
        if not is_valid:
            logger.warning(f"❌ {team_name} INVALID: {result.error_messages}")
        elif result.has_warnings:
            logger.info(f"⚠️ {team_name} VALID with warnings: {result.warning_messages}")
        else:
            logger.debug(f"✅ {team_name} VALID")

        return result

    def _check_ranges(self, team_name: str, dna: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Vérifie les ranges Soft et Hard pour chaque métrique.

        Returns:
            Liste de ValidationIssue
        """
        issues = []

        for field, (hard_min, hard_max) in self.HARD_THRESHOLDS.items():
            if field not in dna:
                continue

            value = dna[field]

            # Vérifier type
            if not isinstance(value, (int, float)):
                issues.append(ValidationIssue(
                    field=field,
                    message=f"{team_name}.{field} = {value} (pas un nombre)",
                    severity=ValidationSeverity.ERROR,
                    value=value
                ))
                continue

            # HARD threshold check (CRITICAL)
            if value < hard_min or value > hard_max:
                issues.append(ValidationIssue(
                    field=field,
                    message=f"{team_name}.{field} = {value} HORS RANGE HARD [{hard_min}, {hard_max}]",
                    severity=ValidationSeverity.CRITICAL,
                    value=value,
                    expected_range=(hard_min, hard_max)
                ))
                continue

            # SOFT threshold check (WARNING)
            if field in self.SOFT_THRESHOLDS:
                soft_min, soft_max = self.SOFT_THRESHOLDS[field]
                if value < soft_min or value > soft_max:
                    issues.append(ValidationIssue(
                        field=field,
                        message=f"{team_name}.{field} = {value} hors range SOFT [{soft_min}, {soft_max}] (outlier)",
                        severity=ValidationSeverity.WARNING,
                        value=value,
                        expected_range=(soft_min, soft_max)
                    ))

        return issues

    def _check_coherence(self, team_name: str, dna: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Vérifie la cohérence logique entre les champs.

        Règles:
        1. xG ne peut pas être > Shots (impossible de générer plus d'xG que de tirs)
        2. xG très bas + xGA très haut = possible inversion colonnes
        3. Possession très basse sans style défensif = suspect
        """
        issues = []

        # Règle 1: xG > Shots est incohérent
        xg = dna.get("xg_90", 0)
        shots = dna.get("shots_90", 0)
        if xg > 0 and shots > 0:
            if xg > shots:
                issues.append(ValidationIssue(
                    field="xg_90",
                    message=f"{team_name}: xG ({xg}) > Shots ({shots}) - Incohérent",
                    severity=ValidationSeverity.WARNING,
                    value={"xg_90": xg, "shots_90": shots}
                ))

        # Règle 2: Possible inversion xG/xGA
        xga = dna.get("xga_90", 0)
        if xg < 0.3 and xga > 2.5:
            issues.append(ValidationIssue(
                field="xg_90",
                message=f"{team_name}: xG={xg}, xGA={xga} - Possible inversion colonnes",
                severity=ValidationSeverity.WARNING,
                value={"xg_90": xg, "xga_90": xga}
            ))

        # Règle 3: Possession très basse sans style défensif
        possession = dna.get("possession_pct", 50)
        style = dna.get("tactical_style", "").upper()
        low_block_styles = ["LOW_BLOCK", "PARK_BUS", "DEFENSIVE", "COUNTER_ATTACK"]

        if possession < 35 and style not in low_block_styles:
            issues.append(ValidationIssue(
                field="possession_pct",
                message=f"{team_name}: Possession={possession}% très basse sans style défensif",
                severity=ValidationSeverity.WARNING,
                value={"possession_pct": possession, "style": style}
            ))

        return issues

    def validate_match_data(
        self,
        home_team: str,
        home_dna: Dict[str, Any],
        away_team: str,
        away_dna: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Valide les données pour un match complet (2 équipes).

        Returns:
            {
                "is_valid": bool,
                "home": ValidationResult,
                "away": ValidationResult,
                "errors": List[str],
                "warnings": List[str]
            }
        """
        home_result = self.validate_team_dna(home_team, home_dna)
        away_result = self.validate_team_dna(away_team, away_dna)

        return {
            "is_valid": home_result.is_valid and away_result.is_valid,
            "home": home_result,
            "away": away_result,
            "errors": home_result.error_messages + away_result.error_messages,
            "warnings": home_result.warning_messages + away_result.warning_messages
        }


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTION PERSONNALISÉE
# ═══════════════════════════════════════════════════════════════════════════════

class DataValidationError(Exception):
    """Exception levée quand la validation échoue"""
    def __init__(self, errors: List[str], team_name: str = None):
        self.errors = errors
        self.team_name = team_name
        message = f"Validation failed for {team_name}: {errors}" if team_name else f"Validation failed: {errors}"
        super().__init__(message)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST RAPIDE
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    validator = DataValidator()

    # Test avec données valides
    valid_dna = {
        "xg_90": 1.8,
        "xga_90": 1.2,
        "cs_pct": 35.0,
        "possession_pct": 55.0,
        "btts_pct": 52.0,
        "shots_90": 14.0
    }

    result = validator.validate_team_dna("Liverpool", valid_dna)
    print(f"\n✅ Liverpool: is_valid={result.is_valid}, warnings={len(result.warnings)}")

    # Test avec données invalides (HARD fail)
    invalid_dna = {
        "xg_90": -5.0,  # Impossible
        "xga_90": 1.2,
    }

    result = validator.validate_team_dna("BugTeam", invalid_dna)
    print(f"\n❌ BugTeam: is_valid={result.is_valid}, errors={result.error_messages}")

    # Test avec outlier (SOFT warning)
    outlier_dna = {
        "xg_90": 4.0,  # Très haut mais possible (City en forme)
        "xga_90": 0.6,
        "possession_pct": 72.0,  # Très haut
    }

    result = validator.validate_team_dna("ManCity", outlier_dna)
    print(f"\n⚠️ ManCity: is_valid={result.is_valid}, warnings={result.warning_messages}")
