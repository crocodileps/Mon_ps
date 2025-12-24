"""
Calculator - EffectiveRestIndex
═══════════════════════════════════════════════════════════════════════════
Calcule le repos effectif avec ajustements Hedge Fund Grade.

Formule:
EffectiveRest = RawDays + VenueBonus - TravelPenalty + RotationBonus

Exemple:
- Arsenal a joué il y a 4 jours à l'extérieur en Champions League
- RawDays = 4
- VenueBonus = 0 (pas applicable)
- TravelPenalty = -1.0 (déplacement européen)
- RotationBonus = 0 (pas un match coupe)
- EffectiveRest = 4 + 0 - 1.0 + 0 = 3.0 jours → CRITICAL
═══════════════════════════════════════════════════════════════════════════
"""
import logging
from datetime import datetime
from typing import Tuple, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from .config import MatchContextConfig, DEFAULT_CONFIG
from .models import RestAnalysis, MatchRestComparison
from .queries import GET_LAST_MATCH_FOR_TEAM

logger = logging.getLogger("MatchContextCalculator")


class MatchContextCalculator:
    """
    Calcule l'EffectiveRestIndex pour chaque équipe.

    Usage:
        calculator = MatchContextCalculator()

        # Pour une équipe spécifique
        rest = calculator.calculate_team_rest(
            team="Arsenal",
            target_date=datetime(2025, 12, 25, 15, 0)
        )
        print(rest)  # Arsenal: 4d brut → 3.0d effectif [CRITICAL]

        # Pour un match complet
        comparison = calculator.calculate_match_rest(
            home_team="Arsenal",
            away_team="Chelsea",
            match_date=datetime(2025, 12, 25, 15, 0)
        )
        print(comparison)  # Arsenal vs Chelsea: Delta=-1.5d → AWAY advantage
    """

    def __init__(self, config: MatchContextConfig = None):
        self.config = config or DEFAULT_CONFIG
        self._conn = None

    def _get_connection(self):
        """Obtient une connexion PostgreSQL."""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(
                host=self.config.DB_HOST,
                port=self.config.DB_PORT,
                dbname=self.config.DB_NAME,
                user=self.config.DB_USER,
                password=self.config.DB_PASSWORD
            )
        return self._conn

    def _get_last_match(
        self,
        team: str,
        before_date: datetime
    ) -> Optional[dict]:
        """
        Récupère le dernier match d'une équipe avant une date.

        Returns:
            dict avec last_match_date, last_venue, last_competition
            ou None si aucun match trouvé
        """
        conn = self._get_connection()

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(GET_LAST_MATCH_FOR_TEAM, (team, before_date))
            result = cur.fetchone()

        return dict(result) if result else None

    def _calculate_venue_adjustment(
        self,
        prev_venue: str,
        prev_competition: str
    ) -> float:
        """
        Calcule l'ajustement basé sur le venue du dernier match.

        - Domicile: +0.5 jour (repos, pas de voyage)
        - Extérieur national: -0.5 jour (fatigue voyage)
        - Extérieur européen: -1.0 jour (fatigue voyage long)
        """
        if prev_venue == 'Home':
            return self.config.HOME_VENUE_BONUS

        elif prev_venue == 'Away':
            # Vérifier si c'était un déplacement européen
            if any(comp in prev_competition for comp in self.config.EUROPEAN_COMPETITIONS):
                return self.config.EUROPEAN_AWAY_PENALTY
            else:
                return self.config.AWAY_VENUE_PENALTY

        return 0.0

    def _calculate_competition_adjustment(self, prev_competition: str) -> float:
        """
        Calcule l'ajustement basé sur le type de compétition.

        - Match coupe: +1.0 jour (rotation probable de l'effectif)
        - Ligue: 0.0 jour (équipe type)
        """
        if any(comp in prev_competition for comp in self.config.CUP_COMPETITIONS):
            return self.config.CUP_ROTATION_BONUS

        return 0.0

    def _determine_status(self, effective_rest: float) -> str:
        """
        Détermine le statut de repos.

        - CRITICAL: < 3 jours (danger immédiat)
        - TIRED: 3-4 jours (fatigue)
        - NORMAL: 4-7 jours (standard)
        - FRESH: 7-10 jours (reposé)
        - RUSTY: > 10 jours (manque de rythme)
        """
        if effective_rest < self.config.CRITICAL_REST:
            return self.config.STATUS_CRITICAL
        elif effective_rest < self.config.TIRED_REST:
            return self.config.STATUS_TIRED
        elif effective_rest > self.config.RUSTY_REST:
            return self.config.STATUS_RUSTY
        elif effective_rest > self.config.OPTIMAL_REST_MAX:
            return self.config.STATUS_FRESH
        else:
            return self.config.STATUS_NORMAL

    def calculate_team_rest(
        self,
        team: str,
        target_date: datetime
    ) -> Optional[RestAnalysis]:
        """
        Calcule le repos effectif d'une équipe avant un match.

        Args:
            team: Nom de l'équipe
            target_date: Date du match cible (PAS datetime.now()!)

        Returns:
            RestAnalysis ou None si aucun match précédent trouvé
        """
        # 1. Récupérer le dernier match
        last_match = self._get_last_match(team, target_date)

        if not last_match:
            logger.warning(f"Aucun match précédent trouvé pour {team}")
            return None

        # 2. Calculer le repos brut
        last_date = last_match['last_match_date']
        if isinstance(last_date, str):
            last_date = datetime.fromisoformat(last_date)

        raw_days = (target_date - last_date).days

        # 3. Calculer les ajustements
        prev_venue = last_match['last_venue']
        prev_competition = last_match['last_competition'] or ''

        venue_adjustment = self._calculate_venue_adjustment(prev_venue, prev_competition)
        competition_adjustment = self._calculate_competition_adjustment(prev_competition)

        # 4. Calculer l'index effectif
        effective_rest = float(raw_days) + venue_adjustment + competition_adjustment

        # 5. Déterminer le statut
        status = self._determine_status(effective_rest)

        return RestAnalysis(
            team=team,
            raw_days=raw_days,
            prev_match_date=last_date,
            prev_venue=prev_venue,
            prev_competition=prev_competition,
            venue_adjustment=venue_adjustment,
            competition_adjustment=competition_adjustment,
            effective_rest_index=round(effective_rest, 1),
            status=status
        )

    def calculate_match_rest(
        self,
        home_team: str,
        away_team: str,
        match_date: datetime,
        match_id: str = None
    ) -> Optional[MatchRestComparison]:
        """
        Calcule et compare le repos des 2 équipes d'un match.

        Args:
            home_team: Équipe domicile
            away_team: Équipe extérieur
            match_date: Date du match
            match_id: ID du match (optionnel)

        Returns:
            MatchRestComparison ou None si données manquantes
        """
        # 1. Calculer le repos de chaque équipe
        home_rest = self.calculate_team_rest(home_team, match_date)
        away_rest = self.calculate_team_rest(away_team, match_date)

        if not home_rest or not away_rest:
            logger.warning(
                f"Impossible de calculer le repos pour {home_team} vs {away_team}"
            )
            return None

        # 2. Calculer le delta (positif = home plus reposé)
        delta = round(home_rest.effective_rest_index - away_rest.effective_rest_index, 1)

        # 3. Déterminer l'avantage
        if abs(delta) < self.config.DELTA_MINOR_THRESHOLD:
            advantage = "neutral"
            significance = "minor"
        elif delta > 0:
            advantage = "home"
            significance = "moderate" if delta < self.config.DELTA_MODERATE_THRESHOLD else "major"
        else:
            advantage = "away"
            significance = "moderate" if abs(delta) < self.config.DELTA_MODERATE_THRESHOLD else "major"

        return MatchRestComparison(
            match_id=match_id or f"{home_team}_{away_team}_{match_date.strftime('%Y%m%d')}",
            match_date=match_date,
            home_team=home_team,
            away_team=away_team,
            home_rest=home_rest,
            away_rest=away_rest,
            delta=delta,
            advantage=advantage,
            significance=significance
        )

    def close(self):
        """Ferme la connexion DB."""
        if self._conn and not self._conn.closed:
            self._conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# TEST STANDALONE
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    calc = MatchContextCalculator()

    # Test sur un match fictif
    from datetime import datetime

    comparison = calc.calculate_match_rest(
        home_team="Arsenal",
        away_team="Chelsea",
        match_date=datetime(2025, 12, 26, 15, 0)
    )

    if comparison:
        print("="*60)
        print("TEST MATCH CONTEXT CALCULATOR")
        print("="*60)
        print(f"Match: {comparison.home_team} vs {comparison.away_team}")
        print(f"Date: {comparison.match_date}")
        print()
        print(f"Home ({comparison.home_team}):")
        print(f"  Raw days: {comparison.home_rest.raw_days}")
        print(f"  Effective: {comparison.home_rest.effective_rest_index}")
        print(f"  Status: {comparison.home_rest.status}")
        print(f"  Returning from: {comparison.home_rest.prev_venue}")
        print()
        print(f"Away ({comparison.away_team}):")
        print(f"  Raw days: {comparison.away_rest.raw_days}")
        print(f"  Effective: {comparison.away_rest.effective_rest_index}")
        print(f"  Status: {comparison.away_rest.status}")
        print(f"  Returning from: {comparison.away_rest.prev_venue}")
        print()
        print(f"Delta: {comparison.delta:+.1f} days")
        print(f"Advantage: {comparison.advantage.upper()}")
        print(f"Significance: {comparison.significance}")
        print("="*60)
    else:
        print("Impossible de calculer - donnees manquantes")

    calc.close()
