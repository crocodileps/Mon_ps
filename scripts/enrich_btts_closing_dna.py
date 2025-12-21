#!/usr/bin/env python3
"""
Enrichissement BTTS Closing Odds via ADN - Hedge Fund Grade
============================================================

AUTEUR: Claude Code (supervise par Mya)
DATE: 2024-12-21
VERSION: 1.0.0

DESCRIPTION:
Ce script enrichit les picks BTTS qui n'ont pas de closing_odds en utilisant
le systeme de synthese ADN de Mon_PS. Il calcule des closing odds personnalisees
basees sur la collision des ADN des deux equipes.

USAGE:
    # Mode dry-run (test sur 10 picks)
    python3 enrich_btts_closing_dna.py --dry-run --limit 10

    # Mode production (tous les picks)
    python3 enrich_btts_closing_dna.py

    # Mode production avec limite
    python3 enrich_btts_closing_dna.py --limit 100

PREREQUIS:
    - PostgreSQL accessible (monps_db)
    - Fichiers existants:
      - /home/Mon_ps/quantum/models/closing_cascade.py
      - /home/Mon_ps/quantum/models/closing_synthesizer_dna.py
      - /home/Mon_ps/quantum/models/market_registry.py
"""

import argparse
import logging
import sys
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ===============================================================================
#                              CONFIGURATION
# ===============================================================================

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}

# Ajouter le chemin pour les imports Mon_PS
sys.path.insert(0, '/home/Mon_ps')

# ===============================================================================
#                              IMPORTS MON_PS
# ===============================================================================

try:
    from quantum.models.closing_cascade import get_closing_odds, ClosingResult
    from quantum.models.market_registry import MarketType
    logger.info("Imports Mon_PS reussis")
except ImportError as e:
    logger.error(f"Erreur import Mon_PS: {e}")
    logger.error("Verifier que les fichiers existent dans /home/Mon_ps/quantum/models/")
    sys.exit(1)

# ===============================================================================
#                           FONCTIONS DATABASE
# ===============================================================================

def get_connection():
    """Cree une connexion PostgreSQL."""
    return psycopg2.connect(**DB_CONFIG)


def create_backup(conn) -> str:
    """
    Cree un backup de la table tracking_clv_picks.

    Returns:
        Nom de la table backup creee
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"tracking_clv_picks_backup_{timestamp}"

    with conn.cursor() as cur:
        # Creer la table backup
        cur.execute(f"""
            CREATE TABLE {backup_name} AS
            SELECT * FROM tracking_clv_picks
        """)

        # Verifier le nombre de lignes
        cur.execute(f"SELECT COUNT(*) FROM {backup_name}")
        count = cur.fetchone()[0]

    conn.commit()
    logger.info(f"Backup cree: {backup_name} ({count} lignes)")
    return backup_name


def get_btts_picks_without_closing(conn, limit: Optional[int] = None) -> List[Dict]:
    """
    Recupere les picks BTTS sans closing_odds avec leurs liquid_odds 1X2.

    Args:
        conn: Connexion PostgreSQL
        limit: Nombre max de picks a recuperer (None = tous)

    Returns:
        Liste de dicts avec pick info + liquid_odds agreges
    """
    query = """
    WITH liquid_odds_1x2 AS (
        SELECT
            match_id,
            AVG(home_odds) as avg_home_odds,
            AVG(draw_odds) as avg_draw_odds,
            AVG(away_odds) as avg_away_odds,
            COUNT(*) as bookmaker_count_1x2
        FROM odds_history
        WHERE home_odds IS NOT NULL
          AND draw_odds IS NOT NULL
          AND away_odds IS NOT NULL
        GROUP BY match_id
    ),
    liquid_odds_totals AS (
        SELECT
            match_id,
            AVG(over_odds) as avg_over_25,
            COUNT(*) as bookmaker_count_ou
        FROM odds_totals
        WHERE line = 2.5
          AND over_odds IS NOT NULL
        GROUP BY match_id
    )
    SELECT
        t.id,
        t.match_id,
        t.home_team,
        t.away_team,
        t.market_type,
        t.odds_taken,
        t.closing_odds,
        t.clv_percentage,
        COALESCE(l1.avg_home_odds, 2.0) as liquid_home,
        COALESCE(l1.avg_draw_odds, 3.5) as liquid_draw,
        COALESCE(l1.avg_away_odds, 2.0) as liquid_away,
        COALESCE(l2.avg_over_25, 1.90) as liquid_over_25,
        COALESCE(l1.bookmaker_count_1x2, 0) as bookmaker_count_1x2,
        COALESCE(l2.bookmaker_count_ou, 0) as bookmaker_count_ou
    FROM tracking_clv_picks t
    LEFT JOIN liquid_odds_1x2 l1 ON t.match_id = l1.match_id
    LEFT JOIN liquid_odds_totals l2 ON t.match_id = l2.match_id
    WHERE t.market_type IN ('btts_yes', 'btts_no')
      AND t.closing_odds IS NULL
    ORDER BY t.id
    """

    if limit:
        query += f" LIMIT {limit}"

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query)
        picks = cur.fetchall()

    logger.info(f"Recupere {len(picks)} picks BTTS sans closing_odds")
    return [dict(p) for p in picks]


def update_pick_closing(
    conn,
    pick_id: int,
    closing_odds: float,
    clv_percentage: float,
    dry_run: bool = False
) -> bool:
    """
    Met a jour un pick avec ses closing_odds et CLV calcules.

    Args:
        conn: Connexion PostgreSQL
        pick_id: ID du pick a mettre a jour
        closing_odds: Closing odds synthetisees
        clv_percentage: CLV calcule
        dry_run: Si True, ne fait pas l'UPDATE

    Returns:
        True si succes, False sinon
    """
    if dry_run:
        logger.debug(f"  [DRY-RUN] UPDATE pick {pick_id}: closing={closing_odds:.3f}, CLV={clv_percentage:.2f}%")
        return True

    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE tracking_clv_picks
                SET
                    closing_odds = %s,
                    clv_percentage = %s
                WHERE id = %s
            """, (closing_odds, clv_percentage, pick_id))
        return True
    except Exception as e:
        logger.error(f"  Erreur UPDATE pick {pick_id}: {e}")
        return False

# ===============================================================================
#                          LOGIQUE ENRICHISSEMENT
# ===============================================================================

def calculate_clv(odds_taken: float, closing_odds: float) -> float:
    """
    Calcule le Closing Line Value.

    Formule: CLV% = (odds_taken / closing_odds - 1) * 100

    Args:
        odds_taken: Cotes prises par le systeme
        closing_odds: Cotes de cloture (synthetisees ADN)

    Returns:
        CLV en pourcentage
    """
    if closing_odds <= 1.0:
        return 0.0
    return (float(odds_taken) / float(closing_odds) - 1) * 100


def get_market_type(market_str: str) -> MarketType:
    """
    Convertit le string market en MarketType enum.

    Args:
        market_str: 'btts_yes' ou 'btts_no'

    Returns:
        MarketType correspondant
    """
    mapping = {
        'btts_yes': MarketType.BTTS_YES,
        'btts_no': MarketType.BTTS_NO
    }
    return mapping.get(market_str, MarketType.BTTS_YES)


def enrich_single_pick(pick: Dict) -> Tuple[Optional[float], Optional[float], Optional[Dict]]:
    """
    Enrichit un seul pick BTTS avec closing_odds ADN.

    Args:
        pick: Dict avec les infos du pick

    Returns:
        Tuple (closing_odds, clv_percentage, factors_used) ou (None, None, None) si erreur
    """
    try:
        # Preparer liquid_odds
        liquid_odds = {
            'home': float(pick['liquid_home']),
            'draw': float(pick['liquid_draw']),
            'away': float(pick['liquid_away']),
            'over_25': float(pick['liquid_over_25'])
        }

        # Appeler la synthese ADN
        result: ClosingResult = get_closing_odds(
            match_id=pick['match_id'],
            home_team=pick['home_team'],
            away_team=pick['away_team'],
            market=get_market_type(pick['market_type']),
            liquid_odds=liquid_odds
        )

        if not result.is_valid:
            logger.warning(f"  Closing invalide pour {pick['home_team']} vs {pick['away_team']}: {result.error}")
            return None, None, None

        # Calculer CLV
        closing_odds = result.odds
        clv = calculate_clv(pick['odds_taken'], closing_odds)

        return closing_odds, clv, result.factors_used

    except Exception as e:
        logger.error(f"  Erreur synthese pour pick {pick['id']}: {e}")
        return None, None, None

# ===============================================================================
#                              MAIN FUNCTION
# ===============================================================================

def main():
    """Point d'entree principal du script."""

    # Parser arguments
    parser = argparse.ArgumentParser(
        description='Enrichir les picks BTTS avec closing_odds ADN'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simuler sans modifier la DB'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Nombre max de picks a traiter (defaut: 10 en dry-run, tous sinon)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Afficher les details de chaque pick'
    )
    args = parser.parse_args()

    # Ajuster limit par defaut
    if args.dry_run and args.limit is None:
        args.limit = 10
        logger.info("Mode DRY-RUN: limite automatique a 10 picks")

    logger.info("=" * 70)
    logger.info("    ENRICHISSEMENT BTTS CLOSING ODDS - HEDGE FUND GRADE")
    logger.info("=" * 70)
    logger.info(f"Mode: {'DRY-RUN (simulation)' if args.dry_run else 'PRODUCTION'}")
    logger.info(f"Limite: {args.limit if args.limit else 'Aucune (tous les picks)'}")
    logger.info("")

    # Connexion DB
    try:
        conn = get_connection()
        logger.info("Connexion PostgreSQL etablie")
    except Exception as e:
        logger.error(f"Erreur connexion DB: {e}")
        sys.exit(1)

    try:
        # ETAPE 1: Backup (sauf dry-run)
        if not args.dry_run:
            logger.info("")
            logger.info("ETAPE 1: Creation backup...")
            backup_name = create_backup(conn)
        else:
            logger.info("")
            logger.info("ETAPE 1: Backup SKIPPE (dry-run)")

        # ETAPE 2: Recuperer les picks
        logger.info("")
        logger.info("ETAPE 2: Recuperation des picks BTTS...")
        picks = get_btts_picks_without_closing(conn, args.limit)

        if not picks:
            logger.info("Aucun pick BTTS a enrichir!")
            return

        # ETAPE 3: Enrichissement
        logger.info("")
        logger.info("ETAPE 3: Enrichissement ADN...")
        logger.info("")

        stats = {
            'total': len(picks),
            'success': 0,
            'errors': 0,
            'clv_sum': 0.0,
            'clv_positive': 0,
            'clv_negative': 0
        }

        for i, pick in enumerate(picks, 1):
            # Log progression
            match_str = f"{pick['home_team']} vs {pick['away_team']}"
            logger.info(f"[{i}/{stats['total']}] {match_str} - {pick['market_type']}")

            # Enrichir
            closing_odds, clv, factors = enrich_single_pick(pick)

            if closing_odds is None:
                stats['errors'] += 1
                continue

            # Log resultat
            if args.verbose or args.dry_run:
                logger.info(f"  odds_taken: {pick['odds_taken']:.2f} -> closing: {closing_odds:.3f}")
                logger.info(f"  CLV: {clv:+.2f}%")
                if factors:
                    home_def = factors.get('home_defense_factor', 'N/A')
                    away_atk = factors.get('away_attack_factor', 'N/A')
                    if isinstance(home_def, (int, float)):
                        logger.info(f"  ADN: defense={home_def:.3f}, attack={away_atk:.3f}")

            # Update DB
            if update_pick_closing(conn, pick['id'], closing_odds, clv, args.dry_run):
                stats['success'] += 1
                stats['clv_sum'] += clv
                if clv > 0:
                    stats['clv_positive'] += 1
                else:
                    stats['clv_negative'] += 1
            else:
                stats['errors'] += 1

        # Commit si pas dry-run
        if not args.dry_run:
            conn.commit()
            logger.info("")
            logger.info("Modifications committees")

        # ETAPE 4: Resume
        logger.info("")
        logger.info("=" * 70)
        logger.info("                         RESUME FINAL")
        logger.info("=" * 70)
        logger.info(f"  Total picks traites:     {stats['total']}")
        logger.info(f"  Enrichis avec succes:    {stats['success']}")
        logger.info(f"  Erreurs:                 {stats['errors']}")
        logger.info("")
        if stats['success'] > 0:
            avg_clv = stats['clv_sum'] / stats['success']
            logger.info(f"  CLV moyen:               {avg_clv:+.2f}%")
            logger.info(f"  CLV positif:             {stats['clv_positive']} picks")
            logger.info(f"  CLV negatif:             {stats['clv_negative']} picks")
        logger.info("=" * 70)

        if args.dry_run:
            logger.info("")
            logger.info("MODE DRY-RUN: Aucune modification effectuee")
            logger.info("    Pour appliquer: python3 enrich_btts_closing_dna.py")

    finally:
        conn.close()
        logger.info("")
        logger.info("Connexion fermee")


if __name__ == '__main__':
    main()
