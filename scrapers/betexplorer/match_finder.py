"""
Module pour trouver les match_id Betexplorer depuis nos données Mon_PS
Mapping: (home_team, away_team, date) -> betexplorer_match_id

HEDGE FUND GRADE:
- Triple validation obligatoire (équipes + date)
- Seuil de similarité: 80%
- Différence de date max: 5 jours (tolérance: décalages API, fuseaux horaires, reports)
"""
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import logging
from difflib import SequenceMatcher

from anti_ban import rate_limiter, get_headers, retry_with_backoff, ScraperSession
from league_mapping import get_betexplorer_url, normalize_team_name, BASE_URL
from match_validator import validate_match, normalize_for_comparison, MIN_TEAM_SIMILARITY

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def similarity(a: str, b: str) -> float:
    """Calcule la similarité entre deux chaînes normalisées"""
    norm_a = normalize_for_comparison(a)
    norm_b = normalize_for_comparison(b)
    return SequenceMatcher(None, norm_a, norm_b).ratio()


def normalize_for_match(name: str) -> str:
    """Normalise un nom d'équipe pour le matching"""
    # D'abord appliquer le mapping connu
    name = normalize_team_name(name)
    # Puis normaliser pour la comparaison
    return normalize_for_comparison(name)


@retry_with_backoff(max_retries=3)
def get_league_matches(league_url: str, results: bool = True, session: ScraperSession = None) -> List[Dict]:
    """
    Récupère la liste des matchs d'une ligue

    Args:
        league_url: URL relative Betexplorer (ex: /football/england/premier-league/)
                    OU clé de ligue Mon_PS (ex: soccer_belgium_first_div)
        results: True pour résultats, False pour fixtures
        session: Session de scraping (optionnel)

    Returns:
        Liste de dicts avec home_team, away_team, match_id, match_url
    """
    if session:
        rl = session.rate_limiter
    else:
        rl = rate_limiter

    rl.wait()

    # Convertir clé de ligue en URL si nécessaire
    if not league_url.startswith('/football/'):
        # C'est une clé de ligue (ex: soccer_belgium_first_div)
        converted_url = get_betexplorer_url(league_url)
        if not converted_url:
            logger.error(f"Ligue non mappée: {league_url}")
            return []
        league_url = converted_url

    suffix = "results/" if results else "fixtures/"
    url = f"{BASE_URL}{league_url}{suffix}"

    logger.info(f"Fetching matches from: {url}")

    if session:
        resp = session.get(url)
    else:
        resp = requests.get(url, headers=get_headers(BASE_URL + league_url), timeout=15)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, 'lxml')
    matches = []

    # Trouver la table principale
    table = soup.find('table', {'class': 'table-main'})
    if not table:
        logger.warning(f"No table-main found at {url}")
        return matches

    # Parser chaque ligne
    for row in table.find_all('tr'):
        # Chercher le lien du match
        link = row.find('a', href=re.compile(r'/football/[^/]+/[^/]+/[^/]+-[^/]+/[a-zA-Z0-9]+/?$'))
        if not link:
            continue

        href = link['href']
        match_id = href.rstrip('/').split('/')[-1]
        match_text = link.text.strip()

        # Parser "Team1 - Team2"
        if ' - ' in match_text:
            teams = match_text.split(' - ')
            if len(teams) >= 2:
                home_team = teams[0].strip()
                away_team = teams[1].strip()

                # Chercher le score
                score_elem = row.find('td', {'class': re.compile(r'.*score.*', re.I)})
                score = score_elem.text.strip() if score_elem else None

                matches.append({
                    'match_id': match_id,
                    'match_url': href,
                    'home_team': home_team,
                    'away_team': away_team,
                    'score': score,
                })

    logger.info(f"Found {len(matches)} matches")
    return matches


@retry_with_backoff(max_retries=2)
def get_match_date_from_page(match_url: str, session: ScraperSession = None) -> Optional[datetime]:
    """
    Récupère la date d'un match depuis sa page individuelle.

    Args:
        match_url: URL relative du match (ex: /football/.../match_id/)
        session: Session de scraping

    Returns:
        datetime ou None
    """
    if session:
        rl = session.rate_limiter
    else:
        rl = rate_limiter

    rl.wait()

    url = f"{BASE_URL}{match_url}"

    if session:
        resp = session.get(url)
    else:
        resp = requests.get(url, headers=get_headers(), timeout=15)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, 'lxml')

    # Chercher data-dt dans la page
    elem = soup.find(attrs={'data-dt': True})
    if elem:
        dt_str = elem['data-dt']  # Format: "15,12,2025,21,00"
        try:
            parts = dt_str.split(',')
            if len(parts) >= 5:
                day = int(parts[0])
                month = int(parts[1])
                year = int(parts[2])
                hour = int(parts[3])
                minute = int(parts[4])
                return datetime(year, month, day, hour, minute)
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse date '{dt_str}': {e}")

    return None


def find_betexplorer_match_id(
    home_team: str,
    away_team: str,
    match_date: datetime,
    league: str,
    session: ScraperSession = None,
    validate_date: bool = True
) -> Optional[str]:
    """
    Trouve le match_id Betexplorer pour un match Mon_PS.
    Triple validation: équipes (80%+) + date (±1 jour).

    Args:
        home_team: Nom équipe domicile (Mon_PS)
        away_team: Nom équipe extérieur (Mon_PS)
        match_date: Date du match
        league: Clé ligue Mon_PS
        session: Session de scraping
        validate_date: Si True, récupère et valide la date (plus lent mais plus sûr)

    Returns:
        match_id Betexplorer ou None
    """
    # Obtenir URL Betexplorer
    league_url = get_betexplorer_url(league)
    if not league_url:
        logger.warning(f"Ligue non mappée: {league}")
        return None

    # Déterminer si c'est un résultat ou fixture
    is_past = match_date < datetime.now()

    # Récupérer matchs
    matches = get_league_matches(league_url, results=is_past, session=session)

    # Normaliser les noms pour la recherche
    home_normalized = normalize_team_name(home_team)
    away_normalized = normalize_team_name(away_team)

    # Chercher les matchs candidats (vérifie aussi les matchs inversés home/away)
    candidates = []

    for m in matches:
        if 'home_team' not in m or 'away_team' not in m:
            continue

        # Calculer score de similarité - ordre normal
        sim_home = similarity(home_normalized, m['home_team'])
        sim_away = similarity(away_normalized, m['away_team'])
        avg_score = (sim_home + sim_away) / 2

        # Calculer score de similarité - ordre INVERSÉ (match retour)
        sim_home_rev = similarity(home_normalized, m['away_team'])
        sim_away_rev = similarity(away_normalized, m['home_team'])
        avg_score_rev = (sim_home_rev + sim_away_rev) / 2

        # Garder le meilleur score
        if avg_score_rev > avg_score:
            # Match inversé est meilleur - on marque pour validation
            best_score = avg_score_rev
            is_reversed = True
        else:
            best_score = avg_score
            is_reversed = False

        # Pré-filtre: au moins 50% de similarité moyenne
        if best_score >= 0.5:
            candidates.append({
                **m,
                'sim_home': sim_home_rev if is_reversed else sim_home,
                'sim_away': sim_away_rev if is_reversed else sim_away,
                'avg_score': best_score,
                'is_reversed': is_reversed,
            })

    # Trier par score décroissant
    candidates.sort(key=lambda x: x['avg_score'], reverse=True)

    # Valider le meilleur candidat avec triple check
    for candidate in candidates[:3]:  # Vérifier les 3 meilleurs
        if validate_date:
            # Récupérer la date depuis la page du match
            be_date = get_match_date_from_page(candidate['match_url'], session)
        else:
            be_date = None

        # Pour matchs inversés, on compare notre home avec leur away et vice versa
        is_reversed = candidate.get('is_reversed', False)
        if is_reversed:
            be_home_compare = candidate['away_team']
            be_away_compare = candidate['home_team']
        else:
            be_home_compare = candidate['home_team']
            be_away_compare = candidate['away_team']

        # Validation triple - utiliser les noms CONVERTIS pour la comparaison
        is_valid, details = validate_match(
            home_normalized, away_normalized, match_date,
            be_home_compare, be_away_compare, be_date
        )

        if is_valid:
            reversed_note = " (reversed)" if is_reversed else ""
            logger.info(
                f"Match VALIDATED{reversed_note}: {home_team} vs {away_team} -> {candidate['match_id']} "
                f"(home:{details['home_similarity']:.2f}, away:{details['away_similarity']:.2f}, "
                f"date_diff:{details['date_diff_days']}d)"
            )
            return candidate['match_id']
        else:
            # Si la date n'est pas validée mais les équipes sont bonnes à 80%+
            if (details['checks']['home_team'] and details['checks']['away_team']
                    and not validate_date):
                logger.info(
                    f"Match found (no date validation): {home_team} vs {away_team} -> {candidate['match_id']}"
                )
                return candidate['match_id']

            logger.debug(
                f"Candidate rejected: {candidate['home_team']} vs {candidate['away_team']} - "
                f"{details['checks_failed']}"
            )

    logger.warning(f"Match not found: {home_team} vs {away_team} ({match_date.date()})")
    return None


def find_match_with_details(
    home_team: str,
    away_team: str,
    match_date: datetime,
    league: str,
    session: ScraperSession = None
) -> Tuple[Optional[str], Dict]:
    """
    Trouve le match_id avec détails de validation complets.

    Returns:
        (match_id, details_dict) ou (None, error_dict)
    """
    # Obtenir URL Betexplorer
    league_url = get_betexplorer_url(league)
    if not league_url:
        return None, {'error': f"Ligue non mappée: {league}"}

    is_past = match_date < datetime.now()
    matches = get_league_matches(league_url, results=is_past, session=session)

    home_normalized = normalize_team_name(home_team)
    away_normalized = normalize_team_name(away_team)

    # Trouver le meilleur candidat (vérifie aussi matchs inversés)
    best_candidate = None
    best_score = 0

    for m in matches:
        if 'home_team' not in m or 'away_team' not in m:
            continue

        # Score normal
        sim_home = similarity(home_normalized, m['home_team'])
        sim_away = similarity(away_normalized, m['away_team'])
        avg_score = (sim_home + sim_away) / 2

        # Score inversé
        sim_home_rev = similarity(home_normalized, m['away_team'])
        sim_away_rev = similarity(away_normalized, m['home_team'])
        avg_score_rev = (sim_home_rev + sim_away_rev) / 2

        if avg_score_rev > avg_score:
            best_this = avg_score_rev
            is_reversed = True
        else:
            best_this = avg_score
            is_reversed = False

        if best_this > best_score:
            best_score = best_this
            best_candidate = {
                **m,
                'sim_home': sim_home_rev if is_reversed else sim_home,
                'sim_away': sim_away_rev if is_reversed else sim_away,
                'is_reversed': is_reversed,
            }

    if not best_candidate:
        return None, {'error': 'No candidates found'}

    # Récupérer la date
    be_date = get_match_date_from_page(best_candidate['match_url'], session)

    # Pour matchs inversés, comparer les bonnes équipes
    is_reversed = best_candidate.get('is_reversed', False)
    if is_reversed:
        be_home_compare = best_candidate['away_team']
        be_away_compare = best_candidate['home_team']
    else:
        be_home_compare = best_candidate['home_team']
        be_away_compare = best_candidate['away_team']

    # Validation - utiliser les noms CONVERTIS
    is_valid, details = validate_match(
        home_normalized, away_normalized, match_date,
        be_home_compare, be_away_compare, be_date
    )

    details['match_id'] = best_candidate['match_id']
    details['match_url'] = best_candidate['match_url']
    details['betexplorer_date'] = be_date
    details['is_reversed'] = is_reversed

    if is_valid:
        return best_candidate['match_id'], details
    else:
        return None, details


if __name__ == "__main__":
    print("=== Match Finder Test - Hedge Fund Grade ===\n")

    # Test similarité avec normalisation
    print("1. Similarity tests (with normalization):")
    test_pairs = [
        ("Liverpool", "Liverpool FC"),
        ("Manchester United", "Manchester Utd"),
        ("Manchester City", "Man City"),
        ("Tottenham Hotspur", "Tottenham"),
        ("Wolverhampton Wanderers", "Wolves"),
        ("Real Betis", "Betis"),
        ("Hellas Verona", "Verona"),
    ]
    for a, b in test_pairs:
        sim = similarity(a, b)
        status = "✅" if sim >= MIN_TEAM_SIMILARITY else "❌"
        print(f"   {status} {a} vs {b}: {sim:.2f}")

    # Test normalisation
    print("\n2. Team normalization:")
    test_teams = [
        "Manchester United",
        "RCD Espanyol de Barcelona",
        "Western Sydney Wanderers",
        "Hellas Verona",
        "FC Twente Enschede",
    ]
    for team in test_teams:
        normalized = normalize_team_name(team)
        print(f"   {team} -> {normalized}")

    print(f"\n3. Validation threshold: {MIN_TEAM_SIMILARITY}")
    print("\n=== Test Complete ===")
