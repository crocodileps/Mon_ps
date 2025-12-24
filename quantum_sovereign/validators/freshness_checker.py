"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║  FRESHNESS CHECKER - THE FORTRESS V3.8                                       ║
║  Vérification fraîcheur des données ADN                                      ║
║  Jour 3 - Moteurs Déterministes                                              ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Seuils ajustés (football ≠ trading HFT):
- FRESH:  < 7 jours  → 0% pénalité
- AGING:  7-14 jours → -5% pénalité
- STALE:  14-21 jours → -15% pénalité
- DEAD:   > 21 jours → SKIP

Installation: /home/Mon_ps/quantum_sovereign/validators/freshness_checker.py
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from enum import Enum
import logging

logger = logging.getLogger("quantum_sovereign.validators")


class FreshnessStatus(Enum):
    """Statut de fraîcheur des données"""
    FRESH = "fresh"      # < 7 jours - Données optimales
    AGING = "aging"      # 7-14 jours - Acceptable avec warning
    STALE = "stale"      # 14-21 jours - Pénalité appliquée
    DEAD = "dead"        # > 21 jours - Données inutilisables


@dataclass
class FreshnessResult:
    """Résultat de vérification de fraîcheur"""
    team_name: str
    status: FreshnessStatus
    days_old: int
    penalty: float  # 0.0 à 0.15 (pourcentage de pénalité)
    last_updated: Optional[datetime]
    should_skip: bool  # True si données trop vieilles
    message: str

    @property
    def confidence_multiplier(self) -> float:
        """Multiplicateur de confiance (1.0 - penalty)"""
        return 1.0 - self.penalty


class FreshnessChecker:
    """
    Vérifie la fraîcheur des données ADN - Hedge Fund Grade

    Philosophie:
    - Le football n'est pas du trading haute fréquence
    - Une équipe ne change pas radicalement en 5 jours
    - Données de 10 jours restent exploitables
    - Au-delà de 21 jours = trop risqué

    Usage:
        checker = FreshnessChecker()
        result = checker.check("Liverpool", last_updated=datetime(...))

        if result.should_skip:
            raise DataTooOldError(result.message)

        adjusted_confidence = base_confidence * result.confidence_multiplier
    """

    # ═══════════════════════════════════════════════════════════════════════════
    # SEUILS DE FRAÎCHEUR (en jours)
    # ═══════════════════════════════════════════════════════════════════════════
    FRESH_THRESHOLD_DAYS = 7      # < 7 jours = FRESH
    AGING_THRESHOLD_DAYS = 14     # 7-14 jours = AGING
    STALE_THRESHOLD_DAYS = 21     # 14-21 jours = STALE
    # > 21 jours = DEAD

    # ═══════════════════════════════════════════════════════════════════════════
    # PÉNALITÉS PAR STATUT
    # ═══════════════════════════════════════════════════════════════════════════
    PENALTIES = {
        FreshnessStatus.FRESH: 0.00,   # Pas de pénalité
        FreshnessStatus.AGING: 0.05,   # -5%
        FreshnessStatus.STALE: 0.15,   # -15%
        FreshnessStatus.DEAD: 1.00,    # 100% = skip
    }

    def __init__(self, reference_time: Optional[datetime] = None):
        """
        Args:
            reference_time: Temps de référence (défaut: maintenant)
                           Utile pour les tests ou le backtesting
        """
        self.reference_time = reference_time
        logger.info("FreshnessChecker initialized")

    def _get_reference_time(self) -> datetime:
        """Retourne le temps de référence (maintenant ou injecté)"""
        return self.reference_time or datetime.now()

    def check(
        self,
        team_name: str,
        last_updated: Optional[datetime] = None,
        dna: Optional[Dict[str, Any]] = None
    ) -> FreshnessResult:
        """
        Vérifie la fraîcheur des données d'une équipe.

        Args:
            team_name: Nom de l'équipe
            last_updated: Date de dernière mise à jour (prioritaire)
            dna: Dictionnaire DNA (cherche 'last_updated' ou 'updated_at')

        Returns:
            FreshnessResult avec status, penalty, should_skip
        """
        # 1. Déterminer last_updated
        update_time = self._extract_update_time(last_updated, dna)

        if update_time is None:
            # Pas de date = on assume STALE par prudence
            logger.warning(f"⚠️ {team_name}: Pas de date de mise à jour - assumé STALE")
            return FreshnessResult(
                team_name=team_name,
                status=FreshnessStatus.STALE,
                days_old=-1,
                penalty=self.PENALTIES[FreshnessStatus.STALE],
                last_updated=None,
                should_skip=False,
                message=f"{team_name}: Date inconnue - assumé STALE (-15%)"
            )

        # 2. Calculer l'âge en jours
        reference = self._get_reference_time()
        age = reference - update_time
        days_old = age.days

        # 3. Déterminer le statut
        status = self._determine_status(days_old)
        penalty = self.PENALTIES[status]
        should_skip = (status == FreshnessStatus.DEAD)

        # 4. Construire le message
        message = self._build_message(team_name, status, days_old, penalty)

        # 5. Logger le résultat
        self._log_result(team_name, status, days_old)

        return FreshnessResult(
            team_name=team_name,
            status=status,
            days_old=days_old,
            penalty=penalty,
            last_updated=update_time,
            should_skip=should_skip,
            message=message
        )

    def _extract_update_time(
        self,
        last_updated: Optional[datetime],
        dna: Optional[Dict[str, Any]]
    ) -> Optional[datetime]:
        """Extrait la date de mise à jour depuis les sources disponibles"""

        # Priorité 1: Paramètre direct
        if last_updated is not None:
            return last_updated

        # Priorité 2: DNA dict
        if dna:
            for key in ['last_updated', 'updated_at', 'last_computed_at']:
                if key in dna:
                    value = dna[key]
                    if isinstance(value, datetime):
                        return value
                    elif isinstance(value, str):
                        try:
                            return datetime.fromisoformat(value.replace('Z', '+00:00'))
                        except ValueError:
                            continue

        return None

    def _determine_status(self, days_old: int) -> FreshnessStatus:
        """Détermine le statut basé sur l'âge en jours"""
        if days_old < self.FRESH_THRESHOLD_DAYS:
            return FreshnessStatus.FRESH
        elif days_old < self.AGING_THRESHOLD_DAYS:
            return FreshnessStatus.AGING
        elif days_old < self.STALE_THRESHOLD_DAYS:
            return FreshnessStatus.STALE
        else:
            return FreshnessStatus.DEAD

    def _build_message(
        self,
        team_name: str,
        status: FreshnessStatus,
        days_old: int,
        penalty: float
    ) -> str:
        """Construit un message descriptif"""
        if status == FreshnessStatus.FRESH:
            return f"{team_name}: Données fraîches ({days_old}j) ✅"
        elif status == FreshnessStatus.AGING:
            return f"{team_name}: Données vieillissantes ({days_old}j) - pénalité {penalty*100:.0f}%"
        elif status == FreshnessStatus.STALE:
            return f"{team_name}: Données périmées ({days_old}j) - pénalité {penalty*100:.0f}%"
        else:
            return f"{team_name}: Données MORTES ({days_old}j) - SKIP OBLIGATOIRE ❌"

    def _log_result(self, team_name: str, status: FreshnessStatus, days_old: int):
        """Log le résultat avec le bon niveau"""
        if status == FreshnessStatus.FRESH:
            logger.debug(f"✅ {team_name}: FRESH ({days_old} jours)")
        elif status == FreshnessStatus.AGING:
            logger.info(f"⚠️ {team_name}: AGING ({days_old} jours)")
        elif status == FreshnessStatus.STALE:
            logger.warning(f"🟠 {team_name}: STALE ({days_old} jours)")
        else:
            logger.error(f"❌ {team_name}: DEAD ({days_old} jours) - SKIP")

    def check_match(
        self,
        home_team: str,
        away_team: str,
        home_updated: Optional[datetime] = None,
        away_updated: Optional[datetime] = None,
        home_dna: Optional[Dict] = None,
        away_dna: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Vérifie la fraîcheur pour un match complet.

        Returns:
            {
                "should_skip": bool,
                "combined_penalty": float,
                "home": FreshnessResult,
                "away": FreshnessResult,
                "worst_status": FreshnessStatus
            }
        """
        home_result = self.check(home_team, home_updated, home_dna)
        away_result = self.check(away_team, away_updated, away_dna)

        # Skip si l'une des équipes est DEAD
        should_skip = home_result.should_skip or away_result.should_skip

        # Pénalité combinée = max des deux (on prend le pire)
        combined_penalty = max(home_result.penalty, away_result.penalty)

        # Pire statut
        status_order = [FreshnessStatus.FRESH, FreshnessStatus.AGING,
                        FreshnessStatus.STALE, FreshnessStatus.DEAD]
        home_idx = status_order.index(home_result.status)
        away_idx = status_order.index(away_result.status)
        worst_status = status_order[max(home_idx, away_idx)]

        return {
            "should_skip": should_skip,
            "combined_penalty": combined_penalty,
            "combined_multiplier": 1.0 - combined_penalty,
            "home": home_result,
            "away": away_result,
            "worst_status": worst_status
        }


# ═══════════════════════════════════════════════════════════════════════════════
# EXCEPTION PERSONNALISÉE
# ═══════════════════════════════════════════════════════════════════════════════

class DataTooOldError(Exception):
    """Exception levée quand les données sont trop vieilles (DEAD)"""
    def __init__(self, message: str, team_name: str = None, days_old: int = None):
        self.team_name = team_name
        self.days_old = days_old
        super().__init__(message)


# ═══════════════════════════════════════════════════════════════════════════════
# TEST RAPIDE
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    checker = FreshnessChecker()
    now = datetime.now()

    # Test FRESH (3 jours)
    result = checker.check("Liverpool", last_updated=now - timedelta(days=3))
    print(f"\n{result.message}")
    print(f"  → Multiplier: {result.confidence_multiplier}")

    # Test AGING (10 jours)
    result = checker.check("Arsenal", last_updated=now - timedelta(days=10))
    print(f"\n{result.message}")
    print(f"  → Multiplier: {result.confidence_multiplier}")

    # Test STALE (18 jours)
    result = checker.check("Chelsea", last_updated=now - timedelta(days=18))
    print(f"\n{result.message}")
    print(f"  → Multiplier: {result.confidence_multiplier}")

    # Test DEAD (25 jours)
    result = checker.check("Burnley", last_updated=now - timedelta(days=25))
    print(f"\n{result.message}")
    print(f"  → should_skip: {result.should_skip}")

    # Test match complet
    print("\n" + "="*60)
    print("TEST MATCH COMPLET:")
    match_result = checker.check_match(
        "Manchester City", "Manchester United",
        home_updated=now - timedelta(days=5),
        away_updated=now - timedelta(days=12)
    )
    print(f"  Combined penalty: {match_result['combined_penalty']*100:.0f}%")
    print(f"  Combined multiplier: {match_result['combined_multiplier']}")
    print(f"  Worst status: {match_result['worst_status'].value}")
    print(f"  Should skip: {match_result['should_skip']}")
