"""
Closing Synthesizer DNA-Aware - Synthese de closing odds basee sur l'ADN des equipes
====================================================================================

PHILOSOPHIE ADN-CENTRIC:
- La base Poisson donne une probabilite GENERIQUE
- Les facteurs ADN AJUSTENT cette base pour chaque equipe
- La COLLISION des deux ADN produit la probabilite finale

FORMULES SUPPORTEES:
- poisson_bivariate: Pour BTTS, Over/Under (base + ADN)
- dnb_from_1x2: Pour DNB (derive de 1X2 + ADN)
- dc_from_1x2: Pour Double Chance (derive de 1X2 + ADN)
- clean_sheet_from_poisson: Pour Clean Sheet
- timing_from_profiles: Pour Goal 0-15, 76-90
- special_from_profiles: Pour Corner Goal, Header Goal
- player_from_profiles: Pour Anytime Scorer, FGS

AUTEUR: Claude Code
DATE: 2025-12-19
VERSION: 1.0.0
"""

import math
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ===============================================================================
#                              CONFIGURATION
# ===============================================================================

# Chemin reel vers le fichier DNA (structure: data.teams.NomEquipe)
DNA_FILE_PATH = Path("/home/Mon_ps/data/quantum_v2/team_dna_unified_v2.json")
GOALSCORER_FILE_PATH = Path("/home/Mon_ps/data/goals/goalscorer_profiles_2025.json")

# Cache pour eviter de recharger les fichiers
_dna_cache: Optional[Dict] = None
_goalscorer_cache: Optional[Dict] = None


# ===============================================================================
#                              TOP TEAMS POUR TACTICAL DRAG
# ===============================================================================

TOP_TEAMS = {
    # Premier League
    "Arsenal", "Liverpool", "Manchester City", "Chelsea",
    "Manchester United", "Tottenham", "Newcastle", "Aston Villa",
    # La Liga
    "Real Madrid", "Barcelona", "Atletico Madrid", "Athletic Club",
    # Bundesliga
    "Bayern Munich", "Borussia Dortmund", "RB Leipzig", "Bayer Leverkusen",
    # Serie A
    "Inter", "Juventus", "AC Milan", "Napoli", "Atalanta",
    # Ligue 1
    "PSG", "Monaco", "Marseille",
}


# ===============================================================================
#                              CHARGEMENT DNA
# ===============================================================================

def load_team_dna(force_reload: bool = False) -> Dict:
    """
    Charge le fichier DNA complet des equipes.

    STRUCTURE DU FICHIER:
    {
        "metadata": {...},
        "teams": {
            "Arsenal": {"defense": {...}, "tactical": {...}, "betting": {...}},
            "Liverpool": {...},
            ...
        }
    }

    Returns:
        Dict avec toutes les equipes et leur ADN (section 'teams')
    """
    global _dna_cache

    if _dna_cache is not None and not force_reload:
        return _dna_cache

    if not DNA_FILE_PATH.exists():
        logger.warning(f"DNA file not found: {DNA_FILE_PATH}")
        return {}

    try:
        with open(DNA_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extraire la section 'teams' car la structure est {metadata, teams}
        if 'teams' in data:
            _dna_cache = data['teams']
        else:
            _dna_cache = data

        logger.info(f"Loaded DNA for {len(_dna_cache)} teams")
        return _dna_cache
    except Exception as e:
        logger.error(f"Error loading DNA: {e}")
        return {}


def get_team_dna(team_name: str) -> Optional[Dict]:
    """
    Recupere l'ADN d'une equipe specifique.

    Args:
        team_name: Nom de l'equipe

    Returns:
        Dict avec l'ADN de l'equipe ou None
    """
    dna = load_team_dna()

    if not dna:
        return None

    # Recherche exacte
    if team_name in dna:
        return dna[team_name]

    # Recherche case-insensitive
    team_lower = team_name.lower()
    for name, data in dna.items():
        if name.lower() == team_lower:
            return data

    # Recherche partielle
    for name, data in dna.items():
        if team_lower in name.lower() or name.lower() in team_lower:
            return data

    logger.warning(f"Team DNA not found: {team_name}")
    return None


def get_dna_factor(dna: Dict, factor_path: str, default: float = 1.0) -> float:
    """
    Extrait un facteur specifique de l'ADN d'une equipe.

    CHEMINS SUPPORTES:
    - "cs_pct" ou "defense.cs_pct" -> cherche dans dna['defense']['cs_pct']
    - "resist_global" -> cherche dans dna['defense']['resist_xxx'] ou calcule

    Args:
        dna: Dict ADN de l'equipe (structure: {defense: {...}, tactical: {...}, ...})
        factor_path: Chemin du facteur (ex: "defense.cs_pct" ou "cs_pct")
        default: Valeur par defaut si non trouve

    Returns:
        Valeur du facteur (normalisee entre 0.5 et 1.5)
    """
    if not dna:
        return default

    # Si le chemin contient un point, naviguer directement
    if '.' in factor_path:
        parts = factor_path.split('.')
        current = dna
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part, current.get(part.lower()))
                if current is None:
                    return default
            else:
                return default
    else:
        # Chercher dans les sections principales: defense, tactical, betting, fbref
        current = None
        for section in ['defense', 'tactical', 'betting', 'fbref', 'context']:
            if section in dna and isinstance(dna[section], dict):
                if factor_path in dna[section]:
                    current = dna[section][factor_path]
                    break
                # Chercher aussi en lowercase
                if factor_path.lower() in dna[section]:
                    current = dna[section][factor_path.lower()]
                    break

        if current is None:
            # Chercher directement dans dna (niveau racine)
            current = dna.get(factor_path, dna.get(factor_path.lower()))

        if current is None:
            return default

    # Convertir en float si possible
    try:
        value = float(current)
        # Normaliser: valeurs en pourcentage (0-100) vers facteur (0.5-1.5)
        if value > 1:
            # C'est probablement un pourcentage
            value = 0.5 + (value / 100)
        return min(max(value, 0.5), 1.5)
    except (TypeError, ValueError):
        return default


def get_dna_factor_raw(dna: Dict, factor_path: str, default: float = 0.0) -> float:
    """
    Extrait une valeur ADN BRUTE sans normalisation.

    IMPORTANT: Retourne la valeur telle quelle du JSON.
    Utilisee pour les calculs BTTS ou la normalisation est faite explicitement.

    Args:
        dna: Dict ADN de l'equipe
        factor_path: Chemin du facteur (ex: "defense.cs_pct_home")
        default: Valeur par defaut si non trouve

    Returns:
        Valeur brute (ex: 71.43 pour cs_pct_home, pas 1.21)
    """
    if not dna:
        logger.warning(f"DNA is None, returning default for {factor_path}")
        return default

    # Si le chemin contient un point, naviguer directement
    if '.' in factor_path:
        parts = factor_path.split('.')
        current = dna
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part, current.get(part.lower()))
                if current is None:
                    logger.debug(f"DNA factor {factor_path} not found at {part}")
                    return default
            else:
                return default
        try:
            return float(current)
        except (TypeError, ValueError):
            return default

    # Chercher dans les sections principales
    for section in ['defense', 'tactical', 'betting', 'fbref', 'context', 'exploit']:
        if section in dna and isinstance(dna[section], dict):
            if factor_path in dna[section]:
                try:
                    return float(dna[section][factor_path])
                except (TypeError, ValueError):
                    continue
            # Chercher aussi en lowercase
            if factor_path.lower() in dna[section]:
                try:
                    return float(dna[section][factor_path.lower()])
                except (TypeError, ValueError):
                    continue

    # Chercher directement au niveau racine
    if factor_path in dna:
        try:
            return float(dna[factor_path])
        except (TypeError, ValueError):
            pass

    logger.debug(f"DNA factor {factor_path} not found, using default {default}")
    return default


def get_resist_global_percentile(dna: Dict) -> float:
    """
    Extrait le percentile resist_global depuis betting.anti_exploits.

    Returns:
        Percentile (0-100), default 50 si non trouve
    """
    if not dna:
        return 50.0

    if 'betting' not in dna or 'anti_exploits' not in dna['betting']:
        return 50.0

    for exploit in dna['betting'].get('anti_exploits', []):
        if exploit.get('dimension') == 'global':
            return float(exploit.get('percentile', 50))

    return 50.0


# ===============================================================================
#                              NORMALISATION POUR BTTS
# ===============================================================================

def _normalize_defense_for_btts(cs_pct: float, xga_per_90: float, resist_pct: float) -> float:
    """
    Calcule le facteur defensif pour BTTS.

    LOGIQUE CORRECTE (CALIBREE):
    - cs_pct eleve (>50%) = bonne defense = REDUIT P(BTTS) = factor < 1.0
    - xga_per_90 bas (<1.0) = bonne defense = REDUIT P(BTTS) = factor < 1.0
    - resist_pct eleve (>70) = bonne defense = REDUIT P(BTTS) = factor < 1.0

    CALIBRATION:
    - Arsenal (cs=71%, xga=0.79, resist=98) -> ~0.88 (defense elite mais pas extreme)
    - Equipe moyenne (cs=33%, xga=1.2, resist=50) -> 1.00
    - Passoire (cs=15%, xga=2.0, resist=20) -> ~1.12

    Args:
        cs_pct: Clean sheet percentage (0-100), ex: 71.43 pour Arsenal
        xga_per_90: Expected goals against per 90, ex: 0.79 pour Arsenal
        resist_pct: Resist global percentile (0-100), ex: 98 pour Arsenal

    Returns:
        Facteur multiplicatif (0.85 - 1.12)
        < 1.0 = defense solide = moins de BTTS
        > 1.0 = defense faible = plus de BTTS
    """
    # Normaliser cs_pct: 33% = neutre (1.0), 70% = fort (0.95), 15% = faible (1.04)
    # Formule moins agressive: factor = 1.0 - (cs_pct - 33) / 600
    cs_factor = 1.0 - (cs_pct - 33) / 600

    # Normaliser xga_per_90: 1.2 = neutre (1.0), 0.5 = fort (0.96), 2.0 = faible (1.04)
    # Formule: factor = 0.92 + xga_per_90 / 15
    xga_factor = 0.92 + xga_per_90 / 15

    # Normaliser resist_pct: 50 = neutre (1.0), 98 = fort (0.98), 20 = faible (1.01)
    # Formule: factor = 1.0 - (resist_pct - 50) / 2500
    resist_factor = 1.0 - (resist_pct - 50) / 2500

    # Combiner avec poids: cs(45%) + xga(40%) + resist(15%)
    combined = cs_factor * 0.45 + xga_factor * 0.40 + resist_factor * 0.15

    # Borner entre 0.92 et 1.08 (impact modere)
    return min(max(combined, 0.92), 1.08)


def _normalize_attack_for_btts(goals_scored_avg: float, xg_per_90: float) -> float:
    """
    Calcule le facteur offensif pour BTTS (equipe visiteuse qui doit marquer).

    LOGIQUE:
    - goals_avg eleve = attaque forte = AUGMENTE P(BTTS) = factor > 1.0
    - xg_per_90 eleve = attaque forte = AUGMENTE P(BTTS) = factor > 1.0

    Args:
        goals_scored_avg: Moyenne buts marques par match
        xg_per_90: Expected goals per 90

    Returns:
        Facteur multiplicatif (0.85 - 1.25)
    """
    # Normaliser goals_avg: 1.5 = neutre (1.0), 2.5 = fort (1.20), 0.8 = faible (0.85)
    goals_factor = 0.7 + goals_scored_avg / 4

    # Normaliser xg: 1.5 = neutre (1.0), 2.5 = fort (1.15), 0.8 = faible (0.90)
    xg_factor = 0.7 + xg_per_90 / 5

    # Combiner
    combined = goals_factor * 0.60 + xg_factor * 0.40

    return min(max(combined, 0.85), 1.25)


def _apply_tactical_drag(
    p_btts_base: float,
    p_draw: float,
    home_team: str,
    away_team: str,
    away_attack_factor: float = 1.0
) -> Tuple[float, float]:
    """
    Ajuste P(BTTS) pour les dynamiques tactiques.

    LOGIQUE CALIBREE:
    - P(Draw) eleve = match equilibre = peut aller dans les deux sens
    - Top teams vs Top teams = tactique MAIS aussi potentiel offensif
    - Si away_attack_factor > 1.05 = equipe offensive = moins de drag

    CALIBRATION:
    - Arsenal vs Liverpool (top vs top, Liverpool offensif) -> drag ~0.97
    - Manchester City vs Burnley (top vs relegation) -> drag ~0.98
    - Equipe moyenne vs moyenne -> drag = 1.0

    Args:
        p_btts_base: Probabilite BTTS de base
        p_draw: Probabilite Draw
        home_team: Nom equipe domicile
        away_team: Nom equipe exterieure
        away_attack_factor: Facteur offensif de l'equipe visiteuse

    Returns:
        Tuple (p_btts_adjusted, tactical_drag_factor)
    """
    drag_factor = 1.0

    # Factor 1: Match serre (P(Draw) eleve)
    # MAIS si P(BTTS) base > 0.50, le match est quand meme offensif
    if p_draw > 0.30 and p_btts_base < 0.50:
        drag_factor *= 0.97  # -3% seulement si vraiment defensif

    # Factor 2: Top teams matchup
    is_top_home = home_team in TOP_TEAMS
    is_top_away = away_team in TOP_TEAMS

    if is_top_home and is_top_away:
        # Top vs top MAIS si l'attaque away est forte, moins de drag
        if away_attack_factor > 1.05:
            drag_factor *= 0.98  # -2% seulement (Liverpool est offensif)
        else:
            drag_factor *= 0.95  # -5% si away est defensif

    return p_btts_base * drag_factor, drag_factor


# ===============================================================================
#                              FORMULES DE BASE
# ===============================================================================

def odds_to_probability(odds: float, margin: float = 0.05) -> float:
    """
    Convertit une cote en probabilite (en enlevant la marge bookmaker).

    Args:
        odds: Cote decimale (ex: 2.50)
        margin: Marge bookmaker estimee (default 5%)

    Returns:
        Probabilite (0 a 1)
    """
    if odds <= 1:
        return 0.0

    raw_prob = 1 / odds
    # Ajustement pour la marge (simplification)
    adjusted_prob = raw_prob / (1 + margin)
    return min(max(adjusted_prob, 0.01), 0.99)


def probability_to_odds(prob: float, margin: float = 0.05) -> float:
    """
    Convertit une probabilite en cote (en ajoutant la marge bookmaker).

    Args:
        prob: Probabilite (0 a 1)
        margin: Marge bookmaker (default 5%)

    Returns:
        Cote decimale
    """
    if prob <= 0:
        return 100.0
    if prob >= 1:
        return 1.01

    # Ajustement pour la marge
    adjusted_prob = prob * (1 - margin / 2)
    odds = 1 / adjusted_prob
    return round(max(odds, 1.01), 2)


def extract_expected_goals(over_25_prob: float) -> float:
    """
    Extrait lambda_total (expected goals total) depuis P(Over 2.5).

    Utilise la relation Poisson:
    P(Over 2.5) = 1 - e^(-lambda) x (1 + lambda + lambda^2/2)

    Args:
        over_25_prob: Probabilite Over 2.5 (0 a 1)

    Returns:
        Lambda total (expected goals)
    """
    # Approximation polynomiale validee empiriquement
    # Pour P(Over 2.5) entre 0.30 et 0.70
    if over_25_prob <= 0.30:
        return 2.0
    elif over_25_prob >= 0.70:
        return 3.5
    else:
        # Interpolation: lambda ~ 0.8 + 3.5xP + 0.5xP^2
        return 0.8 + 3.5 * over_25_prob + 0.5 * (over_25_prob ** 2)


def split_expected_goals(
    lambda_total: float,
    home_prob: float,
    away_prob: float,
    home_advantage: float = 0.05
) -> Tuple[float, float]:
    """
    Repartit lambda_total entre equipe domicile et exterieur.

    Utilise les probabilites 1X2 comme proxy de la force relative.

    Args:
        lambda_total: Expected goals total
        home_prob: Probabilite victoire domicile
        away_prob: Probabilite victoire exterieur
        home_advantage: Bonus domicile (default 5%)

    Returns:
        Tuple (lambda_home, lambda_away)
    """
    # Calcul du ratio base sur sqrt des probabilites
    home_strength = math.sqrt(home_prob) if home_prob > 0 else 0.3
    away_strength = math.sqrt(away_prob) if away_prob > 0 else 0.3

    total_strength = home_strength + away_strength
    if total_strength == 0:
        return lambda_total / 2, lambda_total / 2

    home_ratio = home_strength / total_strength + home_advantage
    away_ratio = 1 - home_ratio

    lambda_home = lambda_total * home_ratio
    lambda_away = lambda_total * away_ratio

    return lambda_home, lambda_away


# ===============================================================================
#                              SYNTHESE BTTS (ADN-AWARE)
# ===============================================================================

def synthesize_btts_probability(
    over_25_closing: float,
    home_closing: float,
    away_closing: float,
    draw_closing: float,
    home_team: str,
    away_team: str
) -> Tuple[float, Dict]:
    """
    Calcule P(BTTS) synthetique avec ajustements ADN.

    METHODOLOGIE CORRIGEE:
    1. Base Poisson depuis cotes liquides
    2. Ajustement facteurs ADN equipe domicile (DEFENSE = reduit BTTS si forte)
    3. Ajustement facteurs ADN equipe exterieure (ATTAQUE = augmente BTTS si forte)
    4. Tactical Drag pour matchs top teams

    LOGIQUE CLES:
    - Arsenal cs_pct_home=71% -> home_factor ~0.75 (defense forte = moins de BTTS)
    - Liverpool xga=1.44 -> away_factor ~1.05 (defense faible = plus de BTTS)
    - Arsenal vs Liverpool -> tactical_drag ~0.85 (top vs top)

    Args:
        over_25_closing: Closing odds Over 2.5
        home_closing: Closing odds Home
        away_closing: Closing odds Away
        draw_closing: Closing odds Draw
        home_team: Nom equipe domicile
        away_team: Nom equipe exterieure

    Returns:
        Tuple (probabilite BTTS, dict des facteurs utilises)
    """
    factors_used = {
        "base_poisson": 0.0,
        "home_defense_factor": 1.0,
        "away_attack_factor": 1.0,
        "tactical_drag": 1.0,
        "final_probability": 0.0
    }

    # 1. BASE POISSON
    p_over_25 = odds_to_probability(over_25_closing)
    p_home = odds_to_probability(home_closing)
    p_away = odds_to_probability(away_closing)
    p_draw = odds_to_probability(draw_closing)

    lambda_total = extract_expected_goals(p_over_25)
    lambda_home, lambda_away = split_expected_goals(lambda_total, p_home, p_away)

    # P(BTTS) = P(Home>=1) x P(Away>=1)
    p_home_scores = 1 - math.exp(-lambda_home)
    p_away_scores = 1 - math.exp(-lambda_away)
    p_btts_base = p_home_scores * p_away_scores

    factors_used["base_poisson"] = round(p_btts_base, 4)
    factors_used["lambda_home"] = round(lambda_home, 3)
    factors_used["lambda_away"] = round(lambda_away, 3)

    # 2. FACTEURS ADN HOME (DEFENSE - protege contre BTTS)
    # Plus la defense est forte, moins P(BTTS) est elevee -> factor < 1.0
    home_dna = get_team_dna(home_team)
    home_defense_factor = 1.0

    if home_dna:
        # Extraire valeurs BRUTES (non normalisees)
        cs_pct_home = get_dna_factor_raw(home_dna, "cs_pct_home", 33.0)
        xga_per_90 = get_dna_factor_raw(home_dna, "xga_per_90", 1.2)
        resist_pct = get_resist_global_percentile(home_dna)

        # Normaliser avec la logique CORRECTE
        home_defense_factor = _normalize_defense_for_btts(cs_pct_home, xga_per_90, resist_pct)

        factors_used["home_cs_pct"] = round(cs_pct_home, 2)
        factors_used["home_xga"] = round(xga_per_90, 3)
        factors_used["home_resist_pct"] = round(resist_pct, 1)

    factors_used["home_defense_factor"] = round(home_defense_factor, 4)

    # 3. FACTEURS ADN AWAY (ATTAQUE - contribue a BTTS)
    # Plus l'attaque est forte, plus P(BTTS) est elevee -> factor > 1.0
    away_dna = get_team_dna(away_team)
    away_attack_factor = 1.0

    if away_dna:
        # Chercher les stats offensives dans les bons emplacements
        # Priority: context.history > context.record > fbref
        xg_per_90 = 1.5  # Default ligue moyenne
        goals_scored_avg = 1.5  # Default

        # 1. Essayer context.history (source preferee)
        if 'context' in away_dna and 'history' in away_dna['context']:
            history = away_dna['context']['history']
            if 'xg_90' in history:
                xg_per_90 = float(history['xg_90'])
            elif 'xg' in history:
                matches = away_dna['context'].get('matches', 15)
                xg_per_90 = float(history['xg']) / max(matches, 1)

        # 2. Essayer context.record pour les buts reels
        if 'context' in away_dna and 'record' in away_dna['context']:
            record = away_dna['context']['record']
            goals_for = record.get('goals_for', 22)
            matches = away_dna['context'].get('matches', 15)
            goals_scored_avg = goals_for / max(matches, 1)

        # 3. Fallback sur fbref si disponible
        elif 'fbref' in away_dna:
            fbref = away_dna['fbref']
            if 'GF' in fbref and 'MP' in fbref:
                goals_scored_avg = fbref['GF'] / max(fbref['MP'], 1)
            if 'xG' in fbref and 'MP' in fbref:
                xg_per_90 = fbref['xG'] / max(fbref['MP'], 1)

        away_attack_factor = _normalize_attack_for_btts(goals_scored_avg, xg_per_90)

        factors_used["away_xg_per_90"] = round(xg_per_90, 3)
        factors_used["away_goals_avg"] = round(goals_scored_avg, 2)

    factors_used["away_attack_factor"] = round(away_attack_factor, 4)

    # 4. TACTICAL DRAG (top teams = matchs tactiques = moins de buts)
    # MAIS si l'equipe visiteuse est offensive, moins de drag
    p_btts_after_dna = p_btts_base * home_defense_factor * away_attack_factor
    p_btts_dragged, tactical_drag = _apply_tactical_drag(
        p_btts_after_dna, p_draw, home_team, away_team, away_attack_factor
    )

    factors_used["tactical_drag"] = round(tactical_drag, 4)
    factors_used["is_top_matchup"] = home_team in TOP_TEAMS and away_team in TOP_TEAMS

    # 5. PROBABILITE FINALE
    # Borner entre 0.35 et 0.70 (marches BTTS reels)
    p_btts_final = min(max(p_btts_dragged, 0.35), 0.70)

    factors_used["final_probability"] = round(p_btts_final, 4)
    factors_used["p_btts_before_bounds"] = round(p_btts_dragged, 4)

    return p_btts_final, factors_used


def synthesize_btts_closing(
    over_25_closing: float,
    home_closing: float,
    away_closing: float,
    draw_closing: float,
    home_team: str,
    away_team: str,
    margin: float = 0.05
) -> Tuple[float, Dict]:
    """
    Retourne la CLOSING ODDS synthetique pour BTTS Yes.

    Returns:
        Tuple (closing odds, dict des facteurs utilises)
    """
    p_btts, factors = synthesize_btts_probability(
        over_25_closing, home_closing, away_closing, draw_closing,
        home_team, away_team
    )

    closing_odds = probability_to_odds(p_btts, margin)
    factors["closing_odds"] = closing_odds

    return closing_odds, factors


# ===============================================================================
#                              SYNTHESE DNB (ADN-AWARE)
# ===============================================================================

def synthesize_dnb_closing(
    home_closing: float,
    draw_closing: float,
    home_team: str,
    away_team: str,
    for_home: bool = True,
    margin: float = 0.03
) -> Tuple[float, Dict]:
    """
    Calcule la closing DNB synthetique.

    FORMULE:
    DNB_home = 1 / (P_home / (1 - P_draw))

    Args:
        home_closing: Closing odds Home
        draw_closing: Closing odds Draw
        home_team: Nom equipe domicile
        away_team: Nom equipe exterieure
        for_home: True pour DNB Home, False pour DNB Away
        margin: Marge bookmaker

    Returns:
        Tuple (closing odds, dict des facteurs)
    """
    factors = {"base": 0.0, "dna_adjustment": 1.0}

    p_home = odds_to_probability(home_closing)
    p_draw = odds_to_probability(draw_closing)

    # DNB = repartition entre Home et Away si pas Draw
    if for_home:
        p_dnb_base = p_home / (1 - p_draw) if p_draw < 1 else 0.5
    else:
        p_away = 1 - p_home - p_draw
        p_dnb_base = p_away / (1 - p_draw) if p_draw < 1 else 0.5

    factors["base"] = round(p_dnb_base, 4)

    # Ajustement ADN
    home_dna = get_team_dna(home_team)
    away_dna = get_team_dna(away_team)

    dna_adjustment = 1.0
    if home_dna and away_dna:
        if for_home:
            home_cs = get_dna_factor(home_dna, "cs_pct_home", 1.0)
            away_ga = get_dna_factor(away_dna, "ga_away", 1.0)
            dna_adjustment = (home_cs + (1 - away_ga)) / 2
        else:
            away_cs = get_dna_factor(away_dna, "cs_pct_away", 1.0)
            home_ga = get_dna_factor(home_dna, "ga_home", 1.0)
            dna_adjustment = (away_cs + (1 - home_ga)) / 2

        dna_adjustment = min(max(dna_adjustment, 0.8), 1.2)

    factors["dna_adjustment"] = round(dna_adjustment, 4)

    p_dnb_final = p_dnb_base * dna_adjustment
    p_dnb_final = min(max(p_dnb_final, 0.10), 0.90)

    closing = probability_to_odds(p_dnb_final, margin)
    factors["closing_odds"] = closing

    return closing, factors


# ===============================================================================
#                              SYNTHESE DOUBLE CHANCE (ADN-AWARE)
# ===============================================================================

def synthesize_dc_closing(
    home_closing: float,
    draw_closing: float,
    away_closing: float,
    home_team: str,
    away_team: str,
    dc_type: str = "1x",  # "1x", "x2", or "12"
    margin: float = 0.03
) -> Tuple[float, Dict]:
    """
    Calcule la closing Double Chance synthetique.

    FORMULE:
    DC_1X = 1 / (P_home + P_draw)
    DC_X2 = 1 / (P_draw + P_away)
    DC_12 = 1 / (P_home + P_away)

    Returns:
        Tuple (closing odds, dict des facteurs)
    """
    factors = {"base": 0.0, "dna_adjustment": 1.0}

    p_home = odds_to_probability(home_closing)
    p_draw = odds_to_probability(draw_closing)
    p_away = odds_to_probability(away_closing)

    # Normaliser pour que somme = 1
    total = p_home + p_draw + p_away
    if total > 0:
        p_home /= total
        p_draw /= total
        p_away /= total

    # Calcul selon le type
    if dc_type == "1x":
        p_dc_base = p_home + p_draw
    elif dc_type == "x2":
        p_dc_base = p_draw + p_away
    elif dc_type == "12":
        p_dc_base = p_home + p_away
    else:
        p_dc_base = 0.5

    factors["base"] = round(p_dc_base, 4)

    # Ajustement ADN minimal pour DC (deja tres correle au 1X2)
    dna_adjustment = 1.0
    factors["dna_adjustment"] = round(dna_adjustment, 4)

    p_dc_final = p_dc_base * dna_adjustment
    p_dc_final = min(max(p_dc_final, 0.30), 0.95)

    closing = probability_to_odds(p_dc_final, margin)
    factors["closing_odds"] = closing

    return closing, factors


# ===============================================================================
#                              SYNTHESE CLEAN SHEET (ADN-AWARE)
# ===============================================================================

def synthesize_clean_sheet_probability(
    home_closing: float,
    away_closing: float,
    draw_closing: float,
    team_name: str,
    is_home: bool = True
) -> Tuple[float, Dict]:
    """
    Calcule P(Clean Sheet) pour une equipe.

    METHODOLOGIE:
    - Base: P(0 goals concedes) = e^(-lambda_opponent)
    - Ajustement ADN: cs_pct historique, xga_per_90

    Args:
        home_closing: Closing odds Home
        away_closing: Closing odds Away
        draw_closing: Closing odds Draw
        team_name: Nom de l'equipe
        is_home: True si l'equipe est a domicile

    Returns:
        Tuple (probabilite, dict des facteurs)
    """
    factors = {"base_poisson": 0.0, "dna_factor": 1.0}

    p_home = odds_to_probability(home_closing)
    p_away = odds_to_probability(away_closing)

    # Estimer lambda de l'adversaire
    # Si on defend a domicile, l'adversaire est away -> lambda_away
    # Approximation: lambda ~ 1.2 pour moyenne ligue
    if is_home:
        lambda_opponent = 1.0 + (p_away * 0.8)  # Plus away est fort, plus lambda
    else:
        lambda_opponent = 1.2 + (p_home * 0.6)  # Domicile marque plus souvent

    # Base Poisson: P(0 goals) = e^(-lambda)
    p_cs_base = math.exp(-lambda_opponent)
    factors["base_poisson"] = round(p_cs_base, 4)
    factors["lambda_opponent"] = round(lambda_opponent, 3)

    # Ajustement ADN
    team_dna = get_team_dna(team_name)
    dna_factor = 1.0

    if team_dna:
        # Utiliser cs_pct comme facteur principal
        cs_pct = 0.33  # Default: 1 CS tous les 3 matchs
        if 'defense' in team_dna:
            cs_pct = team_dna['defense'].get('cs_pct', 33.3) / 100

        # Comparer au base et ajuster
        expected_cs = p_cs_base
        if cs_pct > expected_cs:
            dna_factor = 1.0 + (cs_pct - expected_cs) * 0.5
        else:
            dna_factor = 1.0 - (expected_cs - cs_pct) * 0.3

        dna_factor = min(max(dna_factor, 0.7), 1.4)

    factors["dna_factor"] = round(dna_factor, 4)

    p_cs_final = p_cs_base * dna_factor
    p_cs_final = min(max(p_cs_final, 0.10), 0.70)

    factors["final_probability"] = round(p_cs_final, 4)

    return p_cs_final, factors


# ===============================================================================
#                              EXPORT
# ===============================================================================

__all__ = [
    # Chargement DNA
    "load_team_dna",
    "get_team_dna",
    "get_dna_factor",
    "get_dna_factor_raw",
    "get_resist_global_percentile",
    # Formules de base
    "odds_to_probability",
    "probability_to_odds",
    "extract_expected_goals",
    "split_expected_goals",
    # Synthese ADN-aware
    "synthesize_btts_probability",
    "synthesize_btts_closing",
    "synthesize_dnb_closing",
    "synthesize_dc_closing",
    "synthesize_clean_sheet_probability",
    # Top teams
    "TOP_TEAMS",
]
