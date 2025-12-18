#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
UNDERSTAT TEAM MATCH HISTORY SCRAPER
Extrait PPDA, deep, npxG, xpts pour chaque match de chaque équipe
Source: Understat API getLeagueData.teams[].history[]
═══════════════════════════════════════════════════════════════════════════════
Créé: 2025-12-18
Auteur: Mon_PS Team
Architecture: API cachée (post 8 décembre 2025)
"""

import requests
import psycopg2
import psycopg2.extras
import time
import random
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

# Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest'
}

LEAGUES = {
    'EPL': 'Premier League',
    'La_liga': 'La Liga',
    'Bundesliga': 'Bundesliga',
    'Serie_A': 'Serie A',
    'Ligue_1': 'Ligue 1'
}

SEASON = '2025'  # Understat format (année de début)
SEASON_DISPLAY = '2025-2026'  # Notre format DB


def normalize_team_name(name: str) -> str:
    """Normalise le nom d'équipe pour matching"""
    import unicodedata
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    return name.lower().strip().replace(' ', '_')


def fetch_league_teams_data(league_key: str, session: requests.Session) -> Optional[Dict]:
    """
    Récupère les données teams depuis l'API Understat (post 8 décembre 2025)
    Inclut l'historique match-by-match avec PPDA, deep, etc.
    """
    try:
        time.sleep(random.uniform(2, 4))  # Rate limiting

        # D'abord visiter la page pour obtenir les cookies
        session.get(f"https://understat.com/league/{league_key}/{SEASON}")

        # Ensuite appeler l'API
        response = session.get(
            f"https://understat.com/getLeagueData/{league_key}/{SEASON}",
            headers={'Referer': f'https://understat.com/league/{league_key}/{SEASON}'},
            timeout=30
        )

        if response.status_code != 200:
            logger.error(f"HTTP {response.status_code} pour {league_key}")
            return None

        data = response.json()
        teams_data = data.get('teams', {})

        if not teams_data:
            logger.error(f"Pas de teams dans la réponse API pour {league_key}")
            return None

        logger.info(f"✅ {league_key}: {len(teams_data)} équipes récupérées")
        return teams_data

    except Exception as e:
        logger.error(f"Erreur fetch {league_key}: {e}")
        return None


def parse_team_history(team_data: Dict, league_display: str) -> List[Dict]:
    """
    Parse l'historique d'une équipe en records DB
    """
    records = []
    team_name = team_data.get('title', 'Unknown')
    team_id = team_data.get('id')
    history = team_data.get('history', [])

    for idx, match in enumerate(history, 1):
        try:
            # Déterminer H/A
            h_a = match.get('h_a', '').lower()
            home_away = 'H' if h_a == 'h' else 'A' if h_a == 'a' else None

            if not home_away:
                logger.warning(f"h_a invalide pour {team_name}: {h_a}")
                continue

            # Scores
            scored = int(match.get('scored', 0))
            conceded = int(match.get('missed', 0))

            # Résultat
            result_raw = match.get('result', '').lower()
            if result_raw == 'w':
                result = 'W'
            elif result_raw == 'l':
                result = 'L'
            elif result_raw == 'd':
                result = 'D'
            else:
                # Fallback: calculer depuis scores
                if scored > conceded:
                    result = 'W'
                elif scored < conceded:
                    result = 'L'
                else:
                    result = 'D'

            # PPDA parsing
            ppda = match.get('ppda', {})
            ppda_att = int(ppda.get('att', 0)) if isinstance(ppda, dict) else 0
            ppda_def = int(ppda.get('def', 1)) if isinstance(ppda, dict) else 1
            ppda_ratio = round(ppda_att / ppda_def, 4) if ppda_def > 0 else None

            ppda_allowed = match.get('ppda_allowed', {})
            ppda_allowed_att = int(ppda_allowed.get('att', 0)) if isinstance(ppda_allowed, dict) else 0
            ppda_allowed_def = int(ppda_allowed.get('def', 1)) if isinstance(ppda_allowed, dict) else 1
            ppda_allowed_ratio = round(ppda_allowed_att / ppda_allowed_def, 4) if ppda_allowed_def > 0 else None

            # Date parsing
            match_date = match.get('date', '').split(' ')[0]  # Garder seulement YYYY-MM-DD

            record = {
                'team_name': team_name,
                'team_name_normalized': normalize_team_name(team_name),
                'understat_team_id': team_id,
                'league': league_display,
                'season': SEASON_DISPLAY,
                'match_id': None,  # Pas disponible dans history API
                'match_date': match_date,
                'matchweek': idx,  # Index dans l'ordre chronologique
                'home_away': home_away,
                'opponent': None,  # Pas disponible dans history API
                'opponent_id': None,
                'result': result,
                'scored': scored,
                'conceded': conceded,
                'xg': round(float(match.get('xG', 0)), 6),
                'xga': round(float(match.get('xGA', 0)), 6),
                'npxg': round(float(match.get('npxG', 0)), 6),
                'npxga': round(float(match.get('npxGA', 0)), 6),
                'npxgd': round(float(match.get('npxGD', 0)), 6),
                'xpts': round(float(match.get('xpts', 0)), 4),
                'ppda_att': ppda_att,
                'ppda_def': ppda_def,
                'ppda_ratio': ppda_ratio,
                'ppda_allowed_att': ppda_allowed_att,
                'ppda_allowed_def': ppda_allowed_def,
                'ppda_allowed_ratio': ppda_allowed_ratio,
                'deep': int(match.get('deep', 0)),
                'deep_allowed': int(match.get('deep_allowed', 0)),
            }
            records.append(record)

        except Exception as e:
            logger.warning(f"Erreur parsing match {idx} pour {team_name}: {e}")
            continue

    return records


def insert_team_history(records: List[Dict]) -> int:
    """
    Insert/Update les records dans understat_team_match_history
    """
    if not records:
        return 0

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    insert_sql = """
        INSERT INTO understat_team_match_history (
            team_name, team_name_normalized, understat_team_id,
            league, season, match_id, match_date, matchweek,
            home_away, opponent, opponent_id, result, scored, conceded,
            xg, xga, npxg, npxga, npxgd, xpts,
            ppda_att, ppda_def, ppda_ratio,
            ppda_allowed_att, ppda_allowed_def, ppda_allowed_ratio,
            deep, deep_allowed,
            scraped_at, updated_at
        ) VALUES (
            %(team_name)s, %(team_name_normalized)s, %(understat_team_id)s,
            %(league)s, %(season)s, %(match_id)s, %(match_date)s, %(matchweek)s,
            %(home_away)s, %(opponent)s, %(opponent_id)s, %(result)s, %(scored)s, %(conceded)s,
            %(xg)s, %(xga)s, %(npxg)s, %(npxga)s, %(npxgd)s, %(xpts)s,
            %(ppda_att)s, %(ppda_def)s, %(ppda_ratio)s,
            %(ppda_allowed_att)s, %(ppda_allowed_def)s, %(ppda_allowed_ratio)s,
            %(deep)s, %(deep_allowed)s,
            NOW(), NOW()
        )
        ON CONFLICT (team_name, league, season, match_date, home_away)
        DO UPDATE SET
            matchweek = EXCLUDED.matchweek,
            result = EXCLUDED.result,
            scored = EXCLUDED.scored,
            conceded = EXCLUDED.conceded,
            xg = EXCLUDED.xg,
            xga = EXCLUDED.xga,
            npxg = EXCLUDED.npxg,
            npxga = EXCLUDED.npxga,
            npxgd = EXCLUDED.npxgd,
            xpts = EXCLUDED.xpts,
            ppda_att = EXCLUDED.ppda_att,
            ppda_def = EXCLUDED.ppda_def,
            ppda_ratio = EXCLUDED.ppda_ratio,
            ppda_allowed_att = EXCLUDED.ppda_allowed_att,
            ppda_allowed_def = EXCLUDED.ppda_allowed_def,
            ppda_allowed_ratio = EXCLUDED.ppda_allowed_ratio,
            deep = EXCLUDED.deep,
            deep_allowed = EXCLUDED.deep_allowed,
            updated_at = NOW()
    """

    inserted = 0
    for record in records:
        try:
            cur.execute(insert_sql, record)
            inserted += 1
        except Exception as e:
            logger.warning(f"Erreur insert {record.get('team_name')} {record.get('match_date')}: {e}")
            conn.rollback()
            continue

    conn.commit()
    cur.close()
    conn.close()

    return inserted


def enrich_opponent_and_flags():
    """
    Post-processing: Enrichir opponent/match_id et flaguer PPDA extrêmes.
    Appelé après insertion pour maintenir données complètes.
    """
    logger.info("\n📊 Enrichissement post-insertion...")

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        # 1. Enrichir opponent et match_id via jointure
        cur.execute("""
            UPDATE understat_team_match_history h
            SET
                match_id = m.id,
                opponent = CASE
                    WHEN h.home_away = 'H' THEN m.away_team
                    ELSE m.home_team
                END,
                updated_at = NOW()
            FROM match_xg_stats m
            WHERE DATE(h.match_date) = DATE(m.match_date)
              AND h.league = m.league
              AND (h.team_name = m.home_team OR h.team_name = m.away_team)
              AND h.opponent IS NULL
        """)
        enriched_opponent = cur.rowcount
        logger.info(f"   ✅ {enriched_opponent} records enrichis (opponent/match_id)")

        # 2. Flaguer matchs extrêmes (PPDA > 30)
        cur.execute("""
            UPDATE understat_team_match_history
            SET is_extreme_match = TRUE, updated_at = NOW()
            WHERE ppda_ratio > 30 AND (is_extreme_match IS NULL OR is_extreme_match = FALSE)
        """)
        flagged_extreme = cur.rowcount
        logger.info(f"   ⚠️  {flagged_extreme} matchs flagués comme extrêmes (PPDA > 30)")

        # 3. Catégoriser pressing
        cur.execute("""
            UPDATE understat_team_match_history
            SET pressing_category = CASE
                WHEN ppda_ratio < 5 THEN 'ultra_high'
                WHEN ppda_ratio < 10 THEN 'high'
                WHEN ppda_ratio < 15 THEN 'normal'
                WHEN ppda_ratio < 20 THEN 'low'
                ELSE 'very_low'
            END,
            updated_at = NOW()
            WHERE pressing_category IS NULL
        """)
        categorized = cur.rowcount
        logger.info(f"   📊 {categorized} records catégorisés (pressing)")

        conn.commit()
        logger.info("   ✅ Enrichissement terminé")

    except Exception as e:
        logger.error(f"   ❌ Erreur enrichissement: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()


def main():
    """Point d'entrée principal"""
    logger.info("=" * 70)
    logger.info("UNDERSTAT TEAM MATCH HISTORY SCRAPER (API VERSION)")
    logger.info(f"Saison: {SEASON_DISPLAY}")
    logger.info("=" * 70)

    total_inserted = 0
    total_matches = 0

    # Créer une session partagée pour réutiliser les cookies
    session = requests.Session()
    session.headers.update(HEADERS)

    for league_key, league_display in LEAGUES.items():
        logger.info(f"\n{'─' * 50}")
        logger.info(f"📊 Processing {league_display}...")

        teams_data = fetch_league_teams_data(league_key, session)
        if not teams_data:
            logger.warning(f"⚠️  Aucune donnée pour {league_display}")
            continue

        league_records = []
        for team_id, team_data in teams_data.items():
            records = parse_team_history(team_data, league_display)
            league_records.extend(records)
            total_matches += len(records)
            logger.info(f"  └─ {team_data.get('title')}: {len(records)} matchs")

        inserted = insert_team_history(league_records)
        total_inserted += inserted
        logger.info(f"✅ {league_display}: {inserted}/{len(league_records)} records insérés/mis à jour")

    # POST-PROCESSING: Enrichir données
    enrich_opponent_and_flags()

    logger.info(f"\n{'=' * 70}")
    logger.info(f"🏁 TERMINÉ")
    logger.info(f"   Total matchs parsés: {total_matches}")
    logger.info(f"   Total records DB: {total_inserted}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
