"""
FBRef Validator - Protection anti-données corrompues
═══════════════════════════════════════════════════════════════════════════
Valide les données AVANT toute écriture en base ou fichier.
═══════════════════════════════════════════════════════════════════════════
"""
import logging
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

from .config import FBRefConfig, DEFAULT_CONFIG
from .stats_smoother import StatsSmoother

logger = logging.getLogger("FBRefValidator")


@dataclass
class ValidationResult:
    """Résultat de validation."""
    is_valid: bool
    total_players: int
    players_by_league: Dict[str, int]
    warnings: List[str]
    errors: List[str]

    def __str__(self) -> str:
        status = "✅ VALID" if self.is_valid else "❌ INVALID"
        return f"{status} | {self.total_players} players | {len(self.warnings)} warnings | {len(self.errors)} errors"


class FBRefValidator:
    """
    Validateur de données FBRef.

    Règles:
    1. Minimum 500 joueurs total (sinon REJET)
    2. Minimum 80 joueurs par ligue (sinon WARNING)
    3. Toutes les colonnes requises présentes (sinon REJET)
    4. Valeurs xG/shots dans les ranges acceptables
    """

    def __init__(self, config: FBRefConfig = None):
        self.config = config or DEFAULT_CONFIG
        self.smoother = StatsSmoother(padding_minutes=300.0)
        self._smoother_loaded = False

    def _ensure_smoother_loaded(self) -> None:
        """Charge les moyennes du smoother si pas déjà fait."""
        if not self._smoother_loaded:
            self._smoother_loaded = self.smoother.load_league_averages()

    def validate(self, players: List[Dict[str, Any]]) -> ValidationResult:
        """
        Valide une liste de joueurs.

        Args:
            players: Liste de dictionnaires joueur

        Returns:
            ValidationResult avec statut et détails
        """
        warnings = []
        errors = []

        # === CHECK 1: Nombre total de joueurs ===
        total = len(players)
        if total < self.config.MIN_PLAYERS_REQUIRED:
            errors.append(
                f"CRITICAL: Only {total} players (minimum: {self.config.MIN_PLAYERS_REQUIRED})"
            )

        # === CHECK 2: Distribution par ligue ===
        players_by_league = self._count_by_league(players)

        for league in self.config.EXPECTED_LEAGUES:
            count = players_by_league.get(league, 0)
            if count == 0:
                errors.append(f"CRITICAL: League {league} has 0 players!")
            elif count < self.config.MIN_PLAYERS_PER_LEAGUE:
                warnings.append(
                    f"WARNING: League {league} has only {count} players "
                    f"(expected >= {self.config.MIN_PLAYERS_PER_LEAGUE})"
                )

        # === CHECK 3: Colonnes requises ===
        if players:
            missing_cols = self._check_required_columns(players[0])
            if missing_cols:
                errors.append(
                    f"CRITICAL: Missing required columns: {missing_cols}"
                )

        # === CHECK 4: Valeurs aberrantes ===
        outliers = self._check_outliers(players)
        warnings.extend(outliers["warnings"])
        errors.extend(outliers["errors"])

        # === VERDICT ===
        is_valid = len(errors) == 0

        result = ValidationResult(
            is_valid=is_valid,
            total_players=total,
            players_by_league=players_by_league,
            warnings=warnings,
            errors=errors
        )

        # Log result
        if is_valid:
            logger.info(f"✅ Validation PASSED: {result}")
        else:
            logger.error(f"❌ Validation FAILED: {result}")
            for error in errors:
                logger.error(f"   {error}")

        return result

    def _count_by_league(self, players: List[Dict]) -> Dict[str, int]:
        """Compte les joueurs par ligue."""
        counts = {}
        for player in players:
            league = player.get("league", "Unknown")
            counts[league] = counts.get(league, 0) + 1
        return counts

    def _check_required_columns(self, sample_player: Dict) -> List[str]:
        """Vérifie que toutes les colonnes requises sont présentes."""
        missing = []
        for col in self.config.REQUIRED_COLUMNS:
            if col not in sample_player:
                missing.append(col)
        return missing

    def _check_outliers(self, players: List[Dict]) -> Dict[str, List[str]]:
        """Détecte les valeurs aberrantes avec lissage Bayésien."""
        warnings = []
        errors = []

        # Charger le smoother
        self._ensure_smoother_loaded()

        for player in players:
            name = player.get("player_name", player.get("player", "Unknown"))
            league = player.get("league", "EPL")
            minutes_90 = player.get("minutes_90", 0)
            minutes = float(minutes_90) * 90 if minutes_90 else 0

            # Check xG_90 avec lissage
            xg_90_raw = player.get("xg_90")
            if xg_90_raw is not None:
                try:
                    xg_90_raw = float(xg_90_raw)

                    # Calculer stat lissée
                    real_count = (xg_90_raw / 90.0) * minutes if minutes > 0 else 0
                    xg_90_smoothed = self.smoother.get_smoothed_rate(
                        real_count=real_count,
                        real_minutes=minutes,
                        metric="xg_90",
                        league=league
                    )

                    # Valider la stat LISSÉE
                    if xg_90_smoothed > self.config.XG_90_HARD_MAX:
                        errors.append(
                            f"OUTLIER: {name} has smoothed xG_90={xg_90_smoothed} "
                            f"(raw={xg_90_raw}, max: {self.config.XG_90_HARD_MAX})"
                        )
                    elif xg_90_smoothed > self.config.XG_90_SOFT_MAX:
                        warnings.append(
                            f"SUSPICIOUS: {name} has smoothed xG_90={xg_90_smoothed} "
                            f"(raw={xg_90_raw})"
                        )
                except (ValueError, TypeError):
                    pass

            # Check shots_90 avec lissage
            shots_90_raw = player.get("shots_90")
            if shots_90_raw is not None:
                try:
                    shots_90_raw = float(shots_90_raw)

                    # Calculer stat lissée
                    real_count = (shots_90_raw / 90.0) * minutes if minutes > 0 else 0
                    shots_90_smoothed = self.smoother.get_smoothed_rate(
                        real_count=real_count,
                        real_minutes=minutes,
                        metric="shots_90",
                        league=league
                    )

                    # Valider la stat LISSÉE
                    if shots_90_smoothed > self.config.SHOTS_90_HARD_MAX:
                        errors.append(
                            f"OUTLIER: {name} has smoothed shots_90={shots_90_smoothed} "
                            f"(raw={shots_90_raw}, max: {self.config.SHOTS_90_HARD_MAX})"
                        )
                    elif shots_90_smoothed > self.config.SHOTS_90_SOFT_MAX:
                        warnings.append(
                            f"SUSPICIOUS: {name} has smoothed shots_90={shots_90_smoothed} "
                            f"(raw={shots_90_raw})"
                        )
                except (ValueError, TypeError):
                    pass

        # Limiter le nombre de warnings affichés
        if len(warnings) > 10:
            warnings = warnings[:10] + [f"... and {len(warnings) - 10} more warnings"]

        return {"warnings": warnings, "errors": errors}


# === TEST ===
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Test avec données fictives
    test_players = [
        {"player": "Test", "team": "Arsenal", "league": "EPL",
         "minutes_90s": 10, "xg": 5, "xg_90": 0.5, "shots": 30, "shots_90": 3}
    ] * 100  # 100 joueurs identiques pour test

    validator = FBRefValidator()
    result = validator.validate(test_players)
    print(result)
