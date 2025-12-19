#!/usr/bin/env python3
"""
ENRICH CLOSING ODDS - HEDGE FUND GRADE
======================================
Enrichit tracking_clv_picks.closing_odds depuis:
1. match_steam_analysis (Pinnacle, si snapshots >= 3) - 1X2
2. odds_history (Pinnacle, dernière cote avant match) - 1X2
3. odds_totals (Pinnacle) - Over/Under
4. odds_history calcul (Pinnacle) - Double Chance (dc_1x, dc_x2, dc_12)

Formules Double Chance:
- dc_1x = 1 / (1/home + 1/draw)
- dc_x2 = 1 / (1/draw + 1/away)
- dc_12 = 1 / (1/home + 1/away)

Calcule ensuite le CLV pour chaque pick enrichi.

Usage: python3 scripts/enrich_closing_odds.py [--dry-run]
"""

import psycopg2
import psycopg2.extras
from datetime import datetime
import argparse
import sys

# Configuration DB
DB_CONFIG = {
    'host': 'localhost',
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}

# Seuils de qualité
MIN_SNAPSHOTS = 3  # Minimum snapshots pour considérer closing fiable

# Bookmakers par ordre de priorité (sharp first)
# NOTE: Betfair removed - has garbage data (1.01 odds = no liquidity)
BOOKMAKER_PRIORITY = [
    'Pinnacle',      # Most sharp
    'Marathon Bet',  # Sharp
    'Betsson',       # Good coverage
    '1xBet',         # Good coverage
]
# Minimum closing odds (reject unrealistic values)
MIN_CLOSING_ODDS = 1.10
PINNACLE_BOOKMAKER = 'Pinnacle'  # Keep for backward compat


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def log(msg, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}")


def audit_before(conn):
    """Audit état avant enrichissement"""
    log("=" * 60)
    log("AUDIT AVANT ENRICHISSEMENT")
    log("=" * 60)

    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        # État actuel
        cur.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(closing_odds) as with_closing,
                COUNT(*) - COUNT(closing_odds) as without_closing,
                COUNT(*) FILTER (WHERE clv_percentage IS NOT NULL) as with_clv
            FROM tracking_clv_picks
        """)
        row = cur.fetchone()
        log(f"Total picks: {row['total']}")
        log(f"Avec closing_odds: {row['with_closing']} ({row['with_closing']*100/row['total']:.1f}%)")
        log(f"Sans closing_odds: {row['without_closing']} ({row['without_closing']*100/row['total']:.1f}%)")
        log(f"Avec CLV calculé: {row['with_clv']}")

        # Par market_type
        cur.execute("""
            SELECT market_type, COUNT(*) as total,
                   COUNT(closing_odds) as with_closing
            FROM tracking_clv_picks
            GROUP BY market_type
            ORDER BY total DESC
        """)
        log("\nPar market_type:")
        for row in cur.fetchall():
            log(f"  {row['market_type']}: {row['total']} picks, {row['with_closing']} avec closing")

    return True


def enrich_1x2_from_steam(conn, dry_run=False):
    """Enrichir 1X2 depuis match_steam_analysis (si snapshots >= MIN_SNAPSHOTS)"""
    log("\n" + "=" * 60)
    log("ENRICHISSEMENT 1X2 DEPUIS MATCH_STEAM_ANALYSIS")
    log("=" * 60)

    query = """
        WITH enrichable AS (
            SELECT
                t.id,
                t.market_type,
                t.odds_taken,
                CASE t.market_type
                    WHEN 'home' THEN s.closing_home_odds
                    WHEN 'away' THEN s.closing_away_odds
                    WHEN 'draw' THEN s.closing_draw_odds
                END as new_closing
            FROM tracking_clv_picks t
            JOIN match_steam_analysis s ON t.match_id = s.match_id
            WHERE t.market_type IN ('home', 'draw', 'away')
              AND t.closing_odds IS NULL
              AND s.snapshots_count >= %s
        )
        SELECT COUNT(*) as enrichable_count FROM enrichable
    """

    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(query, (MIN_SNAPSHOTS,))
        count = cur.fetchone()['enrichable_count']
        log(f"Picks 1X2 enrichables (snapshots >= {MIN_SNAPSHOTS}): {count}")

        if dry_run:
            log("[DRY-RUN] Pas de modification")
            return count

        if count == 0:
            log("Rien à enrichir")
            return 0

        # UPDATE réel
        update_query = """
            UPDATE tracking_clv_picks t
            SET closing_odds = CASE t.market_type
                WHEN 'home' THEN s.closing_home_odds
                WHEN 'away' THEN s.closing_away_odds
                WHEN 'draw' THEN s.closing_draw_odds
            END,
            opening_odds = CASE t.market_type
                WHEN 'home' THEN s.opening_home_odds
                WHEN 'away' THEN s.opening_away_odds
                WHEN 'draw' THEN s.opening_draw_odds
            END
            FROM match_steam_analysis s
            WHERE t.match_id = s.match_id
              AND t.market_type IN ('home', 'draw', 'away')
              AND t.closing_odds IS NULL
              AND s.snapshots_count >= %s
        """
        cur.execute(update_query, (MIN_SNAPSHOTS,))
        updated = cur.rowcount
        conn.commit()
        log(f"Enrichi: {updated} picks 1X2 depuis steam_analysis")
        return updated


def enrich_1x2_from_history(conn, dry_run=False):
    """Enrichir 1X2 restants depuis odds_history (Pinnacle)"""
    log("\n" + "=" * 60)
    log("ENRICHISSEMENT 1X2 DEPUIS ODDS_HISTORY (PINNACLE)")
    log("=" * 60)

    # Compter enrichables
    count_query = """
        SELECT COUNT(DISTINCT t.id) as enrichable_count
        FROM tracking_clv_picks t
        JOIN odds_history o ON t.match_id = o.match_id
        WHERE t.market_type IN ('home', 'draw', 'away')
          AND t.closing_odds IS NULL
          AND o.bookmaker = %s
    """

    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(count_query, (PINNACLE_BOOKMAKER,))
        count = cur.fetchone()['enrichable_count']
        log(f"Picks 1X2 enrichables depuis Pinnacle: {count}")

        if dry_run:
            log("[DRY-RUN] Pas de modification")
            return count

        if count == 0:
            log("Rien à enrichir")
            return 0

        # UPDATE avec dernière cote Pinnacle avant le match
        update_query = """
            UPDATE tracking_clv_picks t
            SET closing_odds = sub.closing_odds
            FROM (
                SELECT DISTINCT ON (t2.id)
                    t2.id,
                    CASE t2.market_type
                        WHEN 'home' THEN o.home_odds
                        WHEN 'away' THEN o.away_odds
                        WHEN 'draw' THEN o.draw_odds
                    END as closing_odds
                FROM tracking_clv_picks t2
                JOIN odds_history o ON t2.match_id = o.match_id
                WHERE t2.market_type IN ('home', 'draw', 'away')
                  AND t2.closing_odds IS NULL
                  AND o.bookmaker = %s
                  AND o.collected_at < t2.commence_time
                ORDER BY t2.id, o.collected_at DESC
            ) sub
            WHERE t.id = sub.id
              AND sub.closing_odds IS NOT NULL
        """
        cur.execute(update_query, (PINNACLE_BOOKMAKER,))
        updated = cur.rowcount
        conn.commit()
        log(f"Enrichi: {updated} picks 1X2 depuis Pinnacle history")
        return updated


def enrich_1x2_fallback_bookmakers(conn, dry_run=False):
    """Enrichir 1X2 restants avec bookmakers alternatifs (sharp first)"""
    log("\n" + "=" * 60)
    log("ENRICHISSEMENT 1X2 - FALLBACK BOOKMAKERS")
    log("=" * 60)

    total_enriched = 0

    for bookmaker in BOOKMAKER_PRIORITY[1:]:  # Skip Pinnacle (already done)
        count_query = """
            SELECT COUNT(DISTINCT t.id) as enrichable_count
            FROM tracking_clv_picks t
            JOIN odds_history o ON t.match_id = o.match_id
            WHERE t.market_type IN ('home', 'draw', 'away')
              AND t.closing_odds IS NULL
              AND o.bookmaker = %s
        """

        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(count_query, (bookmaker,))
            count = cur.fetchone()['enrichable_count']

            if count == 0:
                continue

            log(f"  {bookmaker}: {count} picks enrichables")

            if dry_run:
                continue

            update_query = """
                UPDATE tracking_clv_picks t
                SET closing_odds = sub.closing_odds
                FROM (
                    SELECT DISTINCT ON (t2.id)
                        t2.id,
                        CASE t2.market_type
                            WHEN 'home' THEN o.home_odds
                            WHEN 'away' THEN o.away_odds
                            WHEN 'draw' THEN o.draw_odds
                        END as closing_odds
                    FROM tracking_clv_picks t2
                    JOIN odds_history o ON t2.match_id = o.match_id
                    WHERE t2.market_type IN ('home', 'draw', 'away')
                      AND t2.closing_odds IS NULL
                      AND o.bookmaker = %s
                      AND o.collected_at < t2.commence_time
                      AND CASE t2.market_type
                          WHEN 'home' THEN o.home_odds
                          WHEN 'away' THEN o.away_odds
                          WHEN 'draw' THEN o.draw_odds
                      END >= 1.10  -- Filter garbage odds
                    ORDER BY t2.id, o.collected_at DESC
                ) sub
                WHERE t.id = sub.id
                  AND sub.closing_odds IS NOT NULL
            """
            cur.execute(update_query, (bookmaker,))
            updated = cur.rowcount
            conn.commit()
            total_enriched += updated
            log(f"  Enrichi: {updated} picks depuis {bookmaker}")

    log(f"Total fallback 1X2: {total_enriched}")
    return total_enriched


def enrich_totals_fallback_bookmakers(conn, dry_run=False):
    """Enrichir O/U restants avec bookmakers alternatifs"""
    log("\n" + "=" * 60)
    log("ENRICHISSEMENT OVER/UNDER - FALLBACK BOOKMAKERS")
    log("=" * 60)

    total_enriched = 0

    for bookmaker in BOOKMAKER_PRIORITY[1:]:  # Skip Pinnacle
        count_query = """
            SELECT COUNT(DISTINCT t.id) as enrichable_count
            FROM tracking_clv_picks t
            JOIN odds_totals o ON t.match_id = o.match_id
            WHERE (t.market_type LIKE 'over%%' OR t.market_type LIKE 'under%%')
              AND t.closing_odds IS NULL
              AND o.bookmaker = %s
              AND (
                  (t.market_type LIKE '%%15' OR t.market_type LIKE '%%_15') AND o.line = 1.5
                  OR (t.market_type LIKE '%%25' OR t.market_type LIKE '%%_25') AND o.line = 2.5
                  OR (t.market_type LIKE '%%35' OR t.market_type LIKE '%%_35') AND o.line = 3.5
              )
        """

        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(count_query, (bookmaker,))
            count = cur.fetchone()['enrichable_count']

            if count == 0:
                continue

            log(f"  {bookmaker}: {count} picks enrichables")

            if dry_run:
                continue

            update_query = """
                UPDATE tracking_clv_picks t
                SET closing_odds = sub.closing_odds
                FROM (
                    SELECT DISTINCT ON (t2.id)
                        t2.id,
                        CASE
                            WHEN t2.market_type LIKE 'over%%' THEN o.over_odds
                            WHEN t2.market_type LIKE 'under%%' THEN o.under_odds
                        END as closing_odds
                    FROM tracking_clv_picks t2
                    JOIN odds_totals o ON t2.match_id = o.match_id
                    WHERE (t2.market_type LIKE 'over%%' OR t2.market_type LIKE 'under%%')
                      AND t2.closing_odds IS NULL
                      AND o.bookmaker = %s
                      AND o.collected_at < t2.commence_time
                      AND (
                          (t2.market_type LIKE '%%15' OR t2.market_type LIKE '%%_15') AND o.line = 1.5
                          OR (t2.market_type LIKE '%%25' OR t2.market_type LIKE '%%_25') AND o.line = 2.5
                          OR (t2.market_type LIKE '%%35' OR t2.market_type LIKE '%%_35') AND o.line = 3.5
                      )
                    ORDER BY t2.id, o.collected_at DESC
                ) sub
                WHERE t.id = sub.id
                  AND sub.closing_odds IS NOT NULL
            """
            cur.execute(update_query, (bookmaker,))
            updated = cur.rowcount
            conn.commit()
            total_enriched += updated
            log(f"  Enrichi: {updated} picks depuis {bookmaker}")

    log(f"Total fallback O/U: {total_enriched}")
    return total_enriched


def get_line_from_market_type(market_type):
    """Extraire la ligne (1.5, 2.5, 3.5) depuis le market_type"""
    # over_15 / under_15 / over15 / under15 -> 1.5
    # over_25 / under_25 / over25 / under25 -> 2.5
    # over_35 / under_35 / over35 / under35 -> 3.5
    if '15' in market_type or '_15' in market_type:
        return 1.5
    elif '25' in market_type or '_25' in market_type:
        return 2.5
    elif '35' in market_type or '_35' in market_type:
        return 3.5
    return None


def enrich_totals_from_history(conn, dry_run=False):
    """Enrichir Over/Under depuis odds_totals (Pinnacle) - AVEC FILTRE PAR LIGNE"""
    log("\n" + "=" * 60)
    log("ENRICHISSEMENT OVER/UNDER DEPUIS ODDS_TOTALS (PINNACLE)")
    log("=" * 60)

    # Compter enrichables PAR LIGNE
    count_query = """
        SELECT COUNT(DISTINCT t.id) as enrichable_count
        FROM tracking_clv_picks t
        JOIN odds_totals o ON t.match_id = o.match_id
        WHERE (t.market_type LIKE 'over%%' OR t.market_type LIKE 'under%%')
          AND t.closing_odds IS NULL
          AND o.bookmaker = %s
          AND (
              (t.market_type LIKE '%%15' OR t.market_type LIKE '%%_15') AND o.line = 1.5
              OR (t.market_type LIKE '%%25' OR t.market_type LIKE '%%_25') AND o.line = 2.5
              OR (t.market_type LIKE '%%35' OR t.market_type LIKE '%%_35') AND o.line = 3.5
          )
    """

    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(count_query, (PINNACLE_BOOKMAKER,))
        count = cur.fetchone()['enrichable_count']
        log(f"Picks Over/Under enrichables depuis Pinnacle (avec filtre ligne): {count}")

        if dry_run:
            log("[DRY-RUN] Pas de modification")
            return count

        if count == 0:
            log("Rien à enrichir")
            return 0

        # UPDATE avec dernière cote Pinnacle - FILTRE PAR LIGNE CORRECT
        update_query = """
            UPDATE tracking_clv_picks t
            SET closing_odds = sub.closing_odds
            FROM (
                SELECT DISTINCT ON (t2.id)
                    t2.id,
                    CASE
                        WHEN t2.market_type LIKE 'over%%' THEN o.over_odds
                        WHEN t2.market_type LIKE 'under%%' THEN o.under_odds
                    END as closing_odds
                FROM tracking_clv_picks t2
                JOIN odds_totals o ON t2.match_id = o.match_id
                WHERE (t2.market_type LIKE 'over%%' OR t2.market_type LIKE 'under%%')
                  AND t2.closing_odds IS NULL
                  AND o.bookmaker = %s
                  AND o.collected_at < t2.commence_time
                  AND (
                      (t2.market_type LIKE '%%15' OR t2.market_type LIKE '%%_15') AND o.line = 1.5
                      OR (t2.market_type LIKE '%%25' OR t2.market_type LIKE '%%_25') AND o.line = 2.5
                      OR (t2.market_type LIKE '%%35' OR t2.market_type LIKE '%%_35') AND o.line = 3.5
                  )
                ORDER BY t2.id, o.collected_at DESC
            ) sub
            WHERE t.id = sub.id
              AND sub.closing_odds IS NOT NULL
        """
        cur.execute(update_query, (PINNACLE_BOOKMAKER,))
        updated = cur.rowcount
        conn.commit()
        log(f"Enrichi: {updated} picks Over/Under depuis Pinnacle")
        return updated


def enrich_double_chance(conn, dry_run=False):
    """Enrichir Double Chance calculé depuis 1X2 (Pinnacle)"""
    log("\n" + "=" * 60)
    log("ENRICHISSEMENT DOUBLE CHANCE DEPUIS 1X2 (PINNACLE)")
    log("=" * 60)

    # dc_1x = 1 / (1/home + 1/draw)
    # dc_x2 = 1 / (1/draw + 1/away)
    # dc_12 = 1 / (1/home + 1/away)

    count_query = """
        SELECT COUNT(DISTINCT t.id) as enrichable_count
        FROM tracking_clv_picks t
        JOIN odds_history o ON t.match_id = o.match_id
        WHERE t.market_type IN ('dc_1x', 'dc_x2', 'dc_12')
          AND t.closing_odds IS NULL
          AND o.bookmaker = %s
          AND o.home_odds > 0 AND o.draw_odds > 0 AND o.away_odds > 0
    """

    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(count_query, (PINNACLE_BOOKMAKER,))
        count = cur.fetchone()['enrichable_count']
        log(f"Picks Double Chance enrichables: {count}")

        if dry_run:
            log("[DRY-RUN] Pas de modification")
            return count

        if count == 0:
            log("Rien a enrichir")
            return 0

        update_query = """
            UPDATE tracking_clv_picks t
            SET closing_odds = sub.closing_odds
            FROM (
                SELECT DISTINCT ON (t2.id)
                    t2.id,
                    CASE t2.market_type
                        WHEN 'dc_1x' THEN 1.0 / (1.0/o.home_odds + 1.0/o.draw_odds)
                        WHEN 'dc_x2' THEN 1.0 / (1.0/o.draw_odds + 1.0/o.away_odds)
                        WHEN 'dc_12' THEN 1.0 / (1.0/o.home_odds + 1.0/o.away_odds)
                    END as closing_odds
                FROM tracking_clv_picks t2
                JOIN odds_history o ON t2.match_id = o.match_id
                WHERE t2.market_type IN ('dc_1x', 'dc_x2', 'dc_12')
                  AND t2.closing_odds IS NULL
                  AND o.bookmaker = %s
                  AND o.home_odds > 0 AND o.draw_odds > 0 AND o.away_odds > 0
                  AND o.collected_at < t2.commence_time
                ORDER BY t2.id, o.collected_at DESC
            ) sub
            WHERE t.id = sub.id
              AND sub.closing_odds IS NOT NULL
        """
        cur.execute(update_query, (PINNACLE_BOOKMAKER,))
        updated = cur.rowcount
        conn.commit()
        log(f"Enrichi: {updated} picks Double Chance")
        return updated


def calculate_clv(conn, dry_run=False):
    """Calculer CLV pour tous les picks avec closing_odds"""
    log("\n" + "=" * 60)
    log("CALCUL CLV")
    log("=" * 60)

    count_query = """
        SELECT COUNT(*) as calculable
        FROM tracking_clv_picks
        WHERE closing_odds IS NOT NULL
          AND closing_odds > 0
          AND odds_taken IS NOT NULL
          AND odds_taken > 0
          AND (clv_percentage IS NULL OR clv_percentage = 0)
    """

    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(count_query)
        count = cur.fetchone()['calculable']
        log(f"Picks avec CLV calculable: {count}")

        if dry_run:
            log("[DRY-RUN] Pas de modification")
            return count

        if count == 0:
            log("Rien à calculer")
            return 0

        # UPDATE CLV
        update_query = """
            UPDATE tracking_clv_picks
            SET clv_percentage = ROUND(((odds_taken / closing_odds - 1) * 100)::numeric, 2)
            WHERE closing_odds IS NOT NULL
              AND closing_odds > 0
              AND odds_taken IS NOT NULL
              AND odds_taken > 0
              AND (clv_percentage IS NULL OR clv_percentage = 0)
        """
        cur.execute(update_query)
        updated = cur.rowcount
        conn.commit()
        log(f"CLV calculé pour: {updated} picks")
        return updated


def audit_after(conn):
    """Audit état après enrichissement"""
    log("\n" + "=" * 60)
    log("AUDIT APRES ENRICHISSEMENT")
    log("=" * 60)

    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        # État final
        cur.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(closing_odds) as with_closing,
                COUNT(*) - COUNT(closing_odds) as without_closing,
                COUNT(clv_percentage) FILTER (WHERE clv_percentage IS NOT NULL) as with_clv,
                ROUND(AVG(clv_percentage)::numeric, 2) as avg_clv,
                ROUND((COUNT(*) FILTER (WHERE clv_percentage > 0) * 100.0 /
                       NULLIF(COUNT(clv_percentage), 0))::numeric, 1) as positive_clv_rate
            FROM tracking_clv_picks
        """)
        row = cur.fetchone()
        log(f"Total picks: {row['total']}")
        log(f"Avec closing_odds: {row['with_closing']} ({row['with_closing']*100/row['total']:.1f}%)")
        log(f"Sans closing_odds: {row['without_closing']} ({row['without_closing']*100/row['total']:.1f}%)")
        log(f"Avec CLV calcule: {row['with_clv']}")
        log(f"CLV moyen: {row['avg_clv']}%")
        log(f"Positive CLV rate: {row['positive_clv_rate']}%")

        # Top équipes par CLV
        cur.execute("""
            SELECT
                COALESCE(home_team, away_team) as team,
                COUNT(*) as bets,
                ROUND(AVG(clv_percentage)::numeric, 2) as avg_clv,
                ROUND((COUNT(*) FILTER (WHERE clv_percentage > 0) * 100.0 /
                       NULLIF(COUNT(*), 0))::numeric, 1) as positive_rate
            FROM tracking_clv_picks
            WHERE clv_percentage IS NOT NULL
            GROUP BY COALESCE(home_team, away_team)
            HAVING COUNT(*) >= 5
            ORDER BY avg_clv DESC
            LIMIT 10
        """)
        log("\nTop 10 equipes par CLV:")
        for row in cur.fetchall():
            log(f"  {row['team']}: {row['bets']} bets, CLV {row['avg_clv']}%, Positive {row['positive_rate']}%")


def main():
    parser = argparse.ArgumentParser(description='Enrichir closing_odds et calculer CLV')
    parser.add_argument('--dry-run', action='store_true', help='Simuler sans modifier')
    args = parser.parse_args()

    log("=" * 60)
    log("ENRICHISSEMENT CLOSING_ODDS - HEDGE FUND GRADE")
    log("=" * 60)
    log(f"Mode: {'DRY-RUN (simulation)' if args.dry_run else 'PRODUCTION'}")
    log(f"Bookmaker reference: {PINNACLE_BOOKMAKER}")
    log(f"Seuil qualite: snapshots >= {MIN_SNAPSHOTS}")

    conn = get_connection()

    try:
        # Audit avant
        audit_before(conn)

        # Enrichissement en 6 étapes (Pinnacle first, then fallbacks)
        total_enriched = 0

        # Étape 1-2: 1X2 Pinnacle
        total_enriched += enrich_1x2_from_steam(conn, args.dry_run)
        total_enriched += enrich_1x2_from_history(conn, args.dry_run)

        # Étape 3: 1X2 Fallback (Betfair, Marathon Bet, etc.)
        total_enriched += enrich_1x2_fallback_bookmakers(conn, args.dry_run)

        # Étape 4: O/U Pinnacle
        total_enriched += enrich_totals_from_history(conn, args.dry_run)

        # Étape 5: O/U Fallback
        total_enriched += enrich_totals_fallback_bookmakers(conn, args.dry_run)

        # Étape 6: Double Chance
        total_enriched += enrich_double_chance(conn, args.dry_run)

        # Calcul CLV
        clv_calculated = calculate_clv(conn, args.dry_run)

        # Audit après
        if not args.dry_run:
            audit_after(conn)

        # Résumé
        log("\n" + "=" * 60)
        log("RESUME")
        log("=" * 60)
        log(f"Total closing_odds enrichis: {total_enriched}")
        log(f"Total CLV calcules: {clv_calculated}")

    finally:
        conn.close()

    log("\nScript termine avec succes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
