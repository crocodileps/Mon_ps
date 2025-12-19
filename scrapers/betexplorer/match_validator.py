"""
Validateur de match - Triple vérification obligatoire
Hedge Fund Grade: Pas de faux positifs acceptés

Règles strictes:
- Similarité équipes >= 80% (pas 60%)
- Différence de date <= 5 jours
- Les 3 checks doivent passer
"""
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Tuple, Dict, Optional
import logging
import re

logger = logging.getLogger(__name__)

# Seuils stricts - Hedge Fund Grade
MIN_TEAM_SIMILARITY = 0.80  # 80% minimum
# Tolérance 5 jours: décalages API, fuseaux horaires, matchs reportés/avancés
MAX_DATE_DIFF_DAYS = 5      # ±5 jours maximum


def normalize_for_comparison(name: str) -> str:
    """
    Normalise un nom d'équipe pour la comparaison.
    Gère les abréviations et variantes courantes.
    """
    name = name.lower().strip()

    # Expansions d'abréviations AVANT suppression
    abbreviations = {
        'man ': 'manchester ',
        'man.': 'manchester ',
        'utd': 'united',
        'man utd': 'manchester united',
        'man city': 'manchester city',
        'spurs': 'tottenham',
        'wolves': 'wolverhampton',
        'brighton': 'brighton hove albion',
        'west ham': 'west ham united',
        'newcastle': 'newcastle united',
        'psg': 'paris saint germain',
        'atl.': 'atletico',
        'atl ': 'atletico ',
        'rb ': 'red bull ',
        # Noms longs espagnols -> courts
        'club atlético de madrid': 'atletico madrid',
        'club atletico de madrid': 'atletico madrid',
        'real sociedad de fútbol': 'real sociedad',
        'real sociedad de futbol': 'real sociedad',
        'ca osasuna': 'osasuna',
        'rcd espanyol de barcelona': 'espanyol',
        # Noms longs néerlandais -> courts
        'fc twente enschede': 'twente',
    }

    for abbrev, full in abbreviations.items():
        if abbrev in name:
            name = name.replace(abbrev, full)

    # Supprimer les suffixes courants
    suffixes = [' fc', ' sc', ' cf', ' afc', ' ac', ' as', ' fk', ' sk', ' bk',
                ' rovers', ' wanderers', ' hotspur', ' albion',
                ' de fútbol', ' de futbol', ' de barcelona', ' enschede']
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)]

    # Supprimer les préfixes courants
    prefixes = ['fc ', 'sc ', 'cf ', 'afc ', 'ac ', 'as ', 'fk ', 'sk ', 'ca ', 'rcd ']
    for prefix in prefixes:
        if name.startswith(prefix):
            name = name[len(prefix):]

    # Supprimer caractères spéciaux et accents basiques
    name = re.sub(r'[^a-z0-9\s]', '', name)
    name = ' '.join(name.split())  # Normaliser espaces

    return name


def similarity(a: str, b: str) -> float:
    """Calcule similarité entre deux chaînes normalisées"""
    norm_a = normalize_for_comparison(a)
    norm_b = normalize_for_comparison(b)
    return SequenceMatcher(None, norm_a, norm_b).ratio()


def parse_date(date_input) -> Optional[datetime]:
    """Parse une date en datetime"""
    if isinstance(date_input, datetime):
        return date_input
    if isinstance(date_input, str):
        # Essayer différents formats
        for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M', '%d/%m/%Y', '%d.%m.%Y']:
            try:
                return datetime.strptime(date_input, fmt)
            except ValueError:
                continue
    return None


def validate_match(
    our_home: str,
    our_away: str,
    our_date: datetime,
    be_home: str,
    be_away: str,
    be_date: Optional[datetime]
) -> Tuple[bool, Dict]:
    """
    Valide qu'un match Betexplorer correspond à notre pick.
    Triple vérification obligatoire.

    Args:
        our_home: Notre équipe domicile
        our_away: Notre équipe extérieur
        our_date: Notre date de match
        be_home: Équipe domicile Betexplorer
        be_away: Équipe extérieur Betexplorer
        be_date: Date Betexplorer (peut être None)

    Returns:
        (is_valid, details_dict)
    """
    # Calculer les similarités
    home_sim = similarity(our_home, be_home)
    away_sim = similarity(our_away, be_away)

    # Calculer différence de date
    date_diff = None
    if be_date:
        our_date_only = our_date.replace(hour=0, minute=0, second=0, microsecond=0)
        be_date_only = be_date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_diff = abs((our_date_only - be_date_only).days)

    details = {
        'our_match': f"{our_home} vs {our_away} ({our_date.date()})",
        'be_match': f"{be_home} vs {be_away} ({be_date.date() if be_date else 'N/A'})",
        'home_similarity': round(home_sim, 3),
        'away_similarity': round(away_sim, 3),
        'date_diff_days': date_diff,
        'checks': {
            'home_team': home_sim >= MIN_TEAM_SIMILARITY,
            'away_team': away_sim >= MIN_TEAM_SIMILARITY,
            'date_match': date_diff is not None and date_diff <= MAX_DATE_DIFF_DAYS,
        },
        'checks_passed': 0,
        'checks_failed': [],
    }

    # Check 1: Home team
    if details['checks']['home_team']:
        details['checks_passed'] += 1
    else:
        details['checks_failed'].append(
            f"home_similarity {home_sim:.2f} < {MIN_TEAM_SIMILARITY}"
        )

    # Check 2: Away team
    if details['checks']['away_team']:
        details['checks_passed'] += 1
    else:
        details['checks_failed'].append(
            f"away_similarity {away_sim:.2f} < {MIN_TEAM_SIMILARITY}"
        )

    # Check 3: Date
    if be_date is None:
        details['checks_failed'].append("date_missing")
    elif details['checks']['date_match']:
        details['checks_passed'] += 1
    else:
        details['checks_failed'].append(
            f"date_diff {date_diff} days > {MAX_DATE_DIFF_DAYS}"
        )

    # Validation: 3/3 checks required
    is_valid = details['checks_passed'] == 3

    if not is_valid:
        logger.warning(f"Match validation FAILED: {details['our_match']}")
        logger.warning(f"  Betexplorer: {details['be_match']}")
        logger.warning(f"  Failures: {details['checks_failed']}")

    return is_valid, details


# Équipes à haut risque de confusion
HIGH_RISK_TEAMS = {
    "Real Madrid": ["Real Betis", "Real Sociedad", "Real Valladolid", "Real Oviedo"],
    "Inter": ["Inter Miami", "Internacional", "Inter Turku"],
    "Athletic": ["Atletico Madrid", "Athletic Bilbao", "Athletico Paranaense"],
    "Monaco": ["Monaco (W)", "Monaco B", "Monaco II"],
    "United": ["Manchester United", "Newcastle United", "West Ham United", "Sheffield United"],
    "City": ["Manchester City", "Leicester City", "Bristol City", "Stoke City"],
    "Sporting": ["Sporting CP", "Sporting Braga", "Sporting Gijon", "Sporting Kansas City"],
    "Nacional": ["Nacional", "Nacional Madeira", "Club Nacional"],
    "Dynamo": ["Dynamo Kiev", "Dynamo Moscow", "Dynamo Dresden", "Dynamo Zagreb"],
    "Red Star": ["Red Star Belgrade", "Red Star FC"],
}


def check_false_positive_risk(team_name: str) -> list:
    """
    Identifie les équipes à risque de faux positifs.

    Args:
        team_name: Nom de l'équipe à vérifier

    Returns:
        Liste des conflits potentiels
    """
    warnings = []
    team_lower = team_name.lower()

    for pattern, conflicts in HIGH_RISK_TEAMS.items():
        if pattern.lower() in team_lower:
            # Vérifier si c'est bien le pattern et pas un conflit
            for conflict in conflicts:
                if conflict.lower() != team_lower:
                    sim = similarity(team_name, conflict)
                    if sim >= 0.5:  # Risque si similarité >= 50%
                        warnings.append({
                            'team': team_name,
                            'conflict': conflict,
                            'similarity': round(sim, 2)
                        })

    return warnings


def validate_match_strict(
    our_home: str,
    our_away: str,
    our_date: datetime,
    be_home: str,
    be_away: str,
    be_date: Optional[datetime]
) -> Tuple[bool, Dict]:
    """
    Validation stricte avec vérification des risques de faux positifs.
    """
    # Validation de base
    is_valid, details = validate_match(
        our_home, our_away, our_date,
        be_home, be_away, be_date
    )

    # Vérifier les risques de faux positifs
    home_risks = check_false_positive_risk(our_home)
    away_risks = check_false_positive_risk(our_away)

    if home_risks or away_risks:
        details['false_positive_risks'] = {
            'home': home_risks,
            'away': away_risks
        }

        # Si risque élevé, exiger une similarité plus haute
        if home_risks:
            for risk in home_risks:
                if risk['conflict'].lower() == be_home.lower():
                    is_valid = False
                    details['checks_failed'].append(
                        f"HIGH_RISK: {our_home} could be confused with {risk['conflict']}"
                    )

        if away_risks:
            for risk in away_risks:
                if risk['conflict'].lower() == be_away.lower():
                    is_valid = False
                    details['checks_failed'].append(
                        f"HIGH_RISK: {our_away} could be confused with {risk['conflict']}"
                    )

    return is_valid, details


if __name__ == "__main__":
    print("=== Test Match Validator - Hedge Fund Grade ===\n")

    # Test 1: Match valide
    print("Test 1: Match valide (Liverpool vs Man City)")
    valid, details = validate_match(
        "Liverpool", "Manchester City", datetime(2025, 12, 15),
        "Liverpool", "Man City", datetime(2025, 12, 15)
    )
    print(f"  Valid: {valid}")
    print(f"  Home sim: {details['home_similarity']:.2f}")
    print(f"  Away sim: {details['away_similarity']:.2f}")
    print(f"  Date diff: {details['date_diff_days']} days\n")

    # Test 2: Mauvaise date (match aller vs retour)
    print("Test 2: Mauvaise date (4 mois d'écart)")
    valid, details = validate_match(
        "Liverpool", "Manchester City", datetime(2025, 12, 15),
        "Liverpool", "Man City", datetime(2025, 8, 20)
    )
    print(f"  Valid: {valid}")
    print(f"  Failures: {details['checks_failed']}\n")

    # Test 3: Real Madrid vs Real Betis (faux positif)
    print("Test 3: Real Madrid vs Real Betis (faux positif potentiel)")
    valid, details = validate_match(
        "Real Madrid", "Barcelona", datetime(2025, 12, 15),
        "Real Betis", "Barcelona", datetime(2025, 12, 15)
    )
    print(f"  Valid: {valid}")
    print(f"  Home similarity: {details['home_similarity']:.2f}")
    print(f"  Failures: {details['checks_failed']}\n")

    # Test 4: Équipes avec similarité limite
    print("Test 4: Manchester United vs Man Utd (abbreviation)")
    valid, details = validate_match(
        "Manchester United", "Arsenal", datetime(2025, 12, 15),
        "Manchester Utd", "Arsenal", datetime(2025, 12, 15)
    )
    print(f"  Valid: {valid}")
    print(f"  Home similarity: {details['home_similarity']:.2f}\n")

    # Test 5: Check risques faux positifs
    print("Test 5: Check risques faux positifs")
    for team in ["Real Madrid", "Inter", "Monaco", "Liverpool", "Athletic Bilbao"]:
        risks = check_false_positive_risk(team)
        if risks:
            print(f"  ⚠️ {team}: {len(risks)} risques")
            for r in risks[:2]:
                print(f"      - {r['conflict']} (sim: {r['similarity']})")
        else:
            print(f"  ✅ {team}: Pas de risque")

    print("\n=== Seuils configurés ===")
    print(f"  MIN_TEAM_SIMILARITY: {MIN_TEAM_SIMILARITY}")
    print(f"  MAX_DATE_DIFF_DAYS: {MAX_DATE_DIFF_DAYS}")
