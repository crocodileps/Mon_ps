"""
Service Match Context - Orchestration
═══════════════════════════════════════════════════════════════════════════
Service principal qui orchestre le calcul et la mise à jour de match_context.
═══════════════════════════════════════════════════════════════════════════
"""
import logging
from datetime import datetime
from typing import List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from .config import MatchContextConfig, DEFAULT_CONFIG
from .models import MatchRestComparison
from .calculator import MatchContextCalculator
from .queries import (
    GET_UPCOMING_MATCHES,
    UPDATE_MATCH_CONTEXT,
    CHECK_COLUMNS_EXIST,
    ADD_MISSING_COLUMNS
)

logger = logging.getLogger("MatchContextService")


class MatchContextService:
    """
    Service principal pour le calcul du contexte de match.

    Usage:
        service = MatchContextService()

        # Mettre à jour tous les matchs à venir
        updated = service.update_upcoming_matches()
        print(f"{updated} matchs mis à jour")

        # Calculer pour un match spécifique
        result = service.calculate_for_match(
            home_team="Arsenal",
            away_team="Chelsea",
            match_date=datetime(2025, 12, 26, 15, 0)
        )
    """

    def __init__(self, config: MatchContextConfig = None):
        self.config = config or DEFAULT_CONFIG
        self.calculator = MatchContextCalculator(config)
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

    def ensure_columns_exist(self) -> bool:
        """
        Vérifie et ajoute les colonnes manquantes dans match_context.

        Returns:
            True si les colonnes existent ou ont été ajoutées
        """
        logger.info("Verification des colonnes match_context...")

        conn = self._get_connection()

        try:
            with conn.cursor() as cur:
                # Vérifier les colonnes existantes
                cur.execute(CHECK_COLUMNS_EXIST)
                existing = {row[0] for row in cur.fetchall()}

                required = {
                    'home_raw_rest_days',
                    'away_raw_rest_days',
                    'home_effective_rest',
                    'away_effective_rest',
                    'rest_delta',
                    'home_returning_from',
                    'away_returning_from',
                    'home_rest_status',
                    'away_rest_status'
                }

                missing = required - existing

                if missing:
                    logger.info(f"  Colonnes manquantes: {missing}")
                    logger.info("  Ajout des colonnes...")
                    cur.execute(ADD_MISSING_COLUMNS)
                    conn.commit()
                    logger.info("  Colonnes ajoutees")
                else:
                    logger.info("  Toutes les colonnes existent")

                return True

        except psycopg2.Error as e:
            logger.error(f"Erreur SQL: {e}")
            conn.rollback()
            return False

    def calculate_for_match(
        self,
        home_team: str,
        away_team: str,
        match_date: datetime,
        match_id: str = None
    ) -> Optional[MatchRestComparison]:
        """
        Calcule le contexte de repos pour un match spécifique.

        Args:
            home_team: Équipe domicile
            away_team: Équipe extérieur
            match_date: Date du match
            match_id: ID du match (optionnel)

        Returns:
            MatchRestComparison ou None si échec
        """
        return self.calculator.calculate_match_rest(
            home_team=home_team,
            away_team=away_team,
            match_date=match_date,
            match_id=match_id
        )

    def update_match_in_db(self, comparison: MatchRestComparison) -> bool:
        """
        Met à jour une ligne dans match_context.

        Args:
            comparison: Résultat du calcul de repos

        Returns:
            True si mise à jour réussie
        """
        conn = self._get_connection()

        params = {
            'match_id': comparison.match_id,
            'home_raw_rest_days': comparison.home_rest.raw_days,
            'away_raw_rest_days': comparison.away_rest.raw_days,
            'home_effective_rest': comparison.home_rest.effective_rest_index,
            'away_effective_rest': comparison.away_rest.effective_rest_index,
            'rest_delta': comparison.delta,
            'home_returning_from': comparison.home_rest.prev_venue,
            'away_returning_from': comparison.away_rest.prev_venue,
            'home_rest_status': comparison.home_rest.status,
            'away_rest_status': comparison.away_rest.status,
            'days_since_last_match': min(
                comparison.home_rest.raw_days,
                comparison.away_rest.raw_days
            )
        }

        try:
            with conn.cursor() as cur:
                cur.execute(UPDATE_MATCH_CONTEXT, params)
                conn.commit()
                return cur.rowcount > 0

        except psycopg2.Error as e:
            logger.error(f"Erreur update: {e}")
            conn.rollback()
            return False

    def update_upcoming_matches(self) -> int:
        """
        Met à jour le repos pour tous les matchs à venir.

        Returns:
            Nombre de matchs mis à jour
        """
        logger.info("="*60)
        logger.info("MATCH CONTEXT SERVICE - Update Upcoming Matches")
        logger.info("="*60)

        # 1. S'assurer que les colonnes existent
        if not self.ensure_columns_exist():
            return 0

        conn = self._get_connection()
        updated_count = 0

        try:
            # 2. Récupérer les matchs à venir sans calcul de repos
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(GET_UPCOMING_MATCHES)
                matches = cur.fetchall()

            logger.info(f"{len(matches)} matchs a traiter")

            # 3. Calculer et mettre à jour chaque match
            for match in matches:
                match_id = match['match_id']
                home_team = match['home_team']
                away_team = match['away_team']
                match_date = match['commence_time']

                # Calculer
                comparison = self.calculate_for_match(
                    home_team=home_team,
                    away_team=away_team,
                    match_date=match_date,
                    match_id=match_id
                )

                if comparison:
                    # Mettre à jour
                    if self.update_match_in_db(comparison):
                        updated_count += 1
                        logger.debug(f"  {home_team} vs {away_team}")
                    else:
                        logger.warning(f"  Echec update: {home_team} vs {away_team}")
                else:
                    logger.warning(f"  Pas de donnees: {home_team} vs {away_team}")

            logger.info(f"{updated_count}/{len(matches)} matchs mis a jour")
            return updated_count

        except psycopg2.Error as e:
            logger.error(f"Erreur SQL: {e}")
            return 0

    def get_rest_analysis(
        self,
        home_team: str,
        away_team: str,
        match_date: datetime = None
    ) -> Optional[dict]:
        """
        Analyse complète du repos pour affichage.

        Returns:
            Dict avec analyse lisible
        """
        if match_date is None:
            match_date = datetime.now()

        comparison = self.calculate_for_match(
            home_team=home_team,
            away_team=away_team,
            match_date=match_date
        )

        if not comparison:
            return None

        return {
            'match': f"{home_team} vs {away_team}",
            'date': match_date.strftime('%Y-%m-%d %H:%M'),
            'home': {
                'team': home_team,
                'raw_days': comparison.home_rest.raw_days,
                'effective': comparison.home_rest.effective_rest_index,
                'status': comparison.home_rest.status,
                'returning_from': comparison.home_rest.prev_venue,
                'prev_competition': comparison.home_rest.prev_competition
            },
            'away': {
                'team': away_team,
                'raw_days': comparison.away_rest.raw_days,
                'effective': comparison.away_rest.effective_rest_index,
                'status': comparison.away_rest.status,
                'returning_from': comparison.away_rest.prev_venue,
                'prev_competition': comparison.away_rest.prev_competition
            },
            'delta': comparison.delta,
            'advantage': comparison.advantage,
            'significance': comparison.significance
        }

    def close(self):
        """Ferme les connexions."""
        self.calculator.close()
        if self._conn and not self._conn.closed:
            self._conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# STANDALONE EXECUTION
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    service = MatchContextService()

    print("="*60)
    print("TEST MATCH CONTEXT SERVICE")
    print("="*60)

    # Test d'analyse
    analysis = service.get_rest_analysis(
        home_team="Liverpool",
        away_team="Manchester City",
        match_date=datetime(2025, 12, 26, 16, 0)
    )

    if analysis:
        print(f"\n{analysis['match']} ({analysis['date']})")
        print(f"\nHome ({analysis['home']['team']}):")
        print(f"  - Raw: {analysis['home']['raw_days']} days")
        print(f"  - Effective: {analysis['home']['effective']} days")
        print(f"  - Status: {analysis['home']['status']}")
        print(f"  - Last match: {analysis['home']['returning_from']} ({analysis['home']['prev_competition']})")

        print(f"\nAway ({analysis['away']['team']}):")
        print(f"  - Raw: {analysis['away']['raw_days']} days")
        print(f"  - Effective: {analysis['away']['effective']} days")
        print(f"  - Status: {analysis['away']['status']}")
        print(f"  - Last match: {analysis['away']['returning_from']} ({analysis['away']['prev_competition']})")

        print(f"\nDelta: {analysis['delta']:+.1f} days")
        print(f"Advantage: {analysis['advantage'].upper()} ({analysis['significance']})")
    else:
        print("Donnees insuffisantes pour l'analyse")

    print("="*60)

    service.close()
