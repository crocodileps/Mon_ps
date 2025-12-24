"""
MatchContext Populator Service V4.1
═══════════════════════════════════════════════════════════════════════════
Alimente la table match_context depuis odds_history.

Architecture Hedge Fund Grade:
- Idempotent: Peut être lancé N fois sans créer de doublons
- Smart UPSERT: Gestion des reports de matchs (fenêtre ±3 jours)
- Traçabilité: source_id stocké pour audit

Flux:
1. Lit matchs futurs (7 jours) depuis odds_history
2. Pour chaque match:
   - Vérifie si existe déjà (même équipes, fenêtre ±3 jours)
   - SI EXISTE: Update commence_time (gestion reports)
   - SI NON: Insert avec status='PENDING'
3. Log le résumé

Auteur: Mon_PS Team
Date: 2025-12-24
Version: 4.1.0
═══════════════════════════════════════════════════════════════════════════
"""
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor

from .config import MatchContextConfig, DEFAULT_CONFIG
from .queries import (
    GET_UPCOMING_FROM_ODDS_HISTORY,
    CHECK_MATCH_EXISTS,
    INSERT_MATCH_CONTEXT,
    UPDATE_MATCH_COMMENCE_TIME
)

logger = logging.getLogger("MatchContextPopulator")


class MatchContextPopulator:
    """
    Alimente match_context depuis odds_history.

    Usage:
        populator = MatchContextPopulator()
        stats = populator.populate()
        print(f"Insérés: {stats['inserted']}, Mis à jour: {stats['updated']}")
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

    def _generate_match_id(self, home_team: str, away_team: str, commence_time: datetime) -> str:
        """
        Génère un match_id unique.

        Format: {home}_{away}_{YYYYMMDD}
        Note: On garde la date pour unicité, mais le UPSERT gère les reports.
        """
        date_str = commence_time.strftime('%Y%m%d')
        # Normaliser les noms (enlever espaces, lowercase pour consistance interne)
        home_clean = home_team.strip().replace(' ', '_')
        away_clean = away_team.strip().replace(' ', '_')
        return f"{home_clean}_{away_clean}_{date_str}"

    def _check_match_exists(
        self,
        cur,
        home_team: str,
        away_team: str,
        commence_time: datetime
    ) -> Optional[Dict]:
        """
        Vérifie si un match similaire existe déjà (fenêtre ±3 jours).

        Returns:
            Dict avec les données du match existant, ou None
        """
        cur.execute(CHECK_MATCH_EXISTS, {
            'home_team': home_team,
            'away_team': away_team,
            'commence_time': commence_time
        })
        result = cur.fetchone()
        return dict(result) if result else None

    def _insert_match(
        self,
        cur,
        match_id: str,
        source_id: str,
        home_team: str,
        away_team: str,
        commence_time: datetime
    ) -> bool:
        """
        Insère un nouveau match dans match_context.

        Returns:
            True si insertion réussie
        """
        try:
            cur.execute(INSERT_MATCH_CONTEXT, {
                'match_id': match_id,
                'source_id': source_id,
                'home_team': home_team,
                'away_team': away_team,
                'commence_time': commence_time
            })
            return True
        except psycopg2.Error as e:
            logger.warning(f"Erreur insertion {home_team} vs {away_team}: {e}")
            return False

    def _update_match(
        self,
        cur,
        existing_id: int,
        source_id: str,
        commence_time: datetime
    ) -> bool:
        """
        Met à jour un match existant (gestion des reports).

        Returns:
            True si update réussi
        """
        try:
            cur.execute(UPDATE_MATCH_COMMENCE_TIME, {
                'id': existing_id,
                'source_id': source_id,
                'commence_time': commence_time
            })
            return True
        except psycopg2.Error as e:
            logger.warning(f"Erreur update match {existing_id}: {e}")
            return False

    def get_upcoming_matches(self) -> List[Dict]:
        """
        Récupère les matchs à venir (7 jours) depuis odds_history.

        Returns:
            Liste de dicts avec source_id, home_team, away_team, commence_time, league
        """
        conn = self._get_connection()

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(GET_UPCOMING_FROM_ODDS_HISTORY)
            matches = cur.fetchall()

        logger.info(f"  {len(matches)} matchs recuperes depuis odds_history (7 jours)")
        return [dict(m) for m in matches]

    def populate(self, dry_run: bool = False) -> Dict[str, int]:
        """
        Alimente match_context depuis odds_history.

        Args:
            dry_run: Si True, ne fait pas les insertions réelles

        Returns:
            Dict avec stats: inserted, updated, skipped, errors
        """
        logger.info("="*70)
        logger.info("MATCH CONTEXT POPULATOR V4.1 - Hedge Fund Grade")
        logger.info("="*70)
        logger.info(f"Mode: {'DRY-RUN' if dry_run else 'PRODUCTION'}")
        logger.info(f"Source: odds_history")
        logger.info(f"Destination: match_context")
        logger.info(f"Horizon: 7 jours")
        logger.info("="*70)

        stats = {
            'inserted': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0,
            'total': 0
        }

        # 1. Récupérer matchs depuis odds_history
        upcoming_matches = self.get_upcoming_matches()
        stats['total'] = len(upcoming_matches)

        if not upcoming_matches:
            logger.warning("  Aucun match a venir trouve dans odds_history")
            return stats

        conn = self._get_connection()

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                for match in upcoming_matches:
                    home_team = match['home_team']
                    away_team = match['away_team']
                    commence_time = match['commence_time']
                    source_id = match['source_id']

                    # Générer match_id
                    match_id = self._generate_match_id(home_team, away_team, commence_time)

                    # Vérifier si existe déjà
                    existing = self._check_match_exists(cur, home_team, away_team, commence_time)

                    if dry_run:
                        if existing:
                            logger.debug(f"  [DRY-RUN] UPDATE: {home_team} vs {away_team}")
                            stats['updated'] += 1
                        else:
                            logger.debug(f"  [DRY-RUN] INSERT: {home_team} vs {away_team}")
                            stats['inserted'] += 1
                        continue

                    # Mode PRODUCTION
                    if existing:
                        # Match existe - vérifier si date a changé (report)
                        if existing['commence_time'] != commence_time:
                            if self._update_match(cur, existing['id'], source_id, commence_time):
                                stats['updated'] += 1
                                logger.debug(f"  Report: {home_team} vs {away_team}")
                            else:
                                stats['errors'] += 1
                        else:
                            stats['skipped'] += 1
                    else:
                        # Nouveau match - INSERT
                        if self._insert_match(cur, match_id, source_id, home_team, away_team, commence_time):
                            stats['inserted'] += 1
                            logger.debug(f"  Nouveau: {home_team} vs {away_team}")
                        else:
                            stats['errors'] += 1

                if not dry_run:
                    conn.commit()
                    logger.info("  Transaction COMMIT")

        except psycopg2.Error as e:
            logger.error(f"  Erreur SQL: {e}")
            conn.rollback()
            stats['errors'] = stats['total']

        # Rapport final
        logger.info("")
        logger.info("="*70)
        logger.info("RAPPORT POPULATOR")
        logger.info("="*70)
        logger.info(f"  Total matchs traites: {stats['total']}")
        logger.info(f"  Inseres: {stats['inserted']}")
        logger.info(f"  Mis a jour (reports): {stats['updated']}")
        logger.info(f"  Ignores (inchanges): {stats['skipped']}")
        logger.info(f"  Erreurs: {stats['errors']}")
        logger.info("="*70)

        return stats

    def close(self):
        """Ferme la connexion."""
        if self._conn and not self._conn.closed:
            self._conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# STANDALONE EXECUTION
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import argparse
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(description='Match Context Populator V4.1')
    parser.add_argument('--dry-run', action='store_true', help='Mode simulation')
    args = parser.parse_args()

    populator = MatchContextPopulator()
    stats = populator.populate(dry_run=args.dry_run)
    populator.close()

    print(f"\nResultat: {stats['inserted']} inseres, {stats['updated']} mis a jour")
