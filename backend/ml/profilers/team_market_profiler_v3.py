#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
TEAM MARKET PROFILER V3 - UNIFIED HEDGE FUND GRADE
═══════════════════════════════════════════════════════════════════════════════

ARCHITECTURE:
    Source 1: match_xg_stats (réalité - 16+ mois)
    Source 2: tracking_clv_picks (système - évolutif)
    Output: team_market_profiles_v3 (table unifiée)

PRINCIPE:
    - Réalité = Ce qui SE PASSE (statistiques objectives)
    - Système = Ce que NOUS FAISONS (performance de nos décisions)
    - Combiné = Intelligence (réalité + feedback)

VERSION: 3.0
DATE: 2025-12-20
═══════════════════════════════════════════════════════════════════════════════
"""

import psycopg2
import psycopg2.extras
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import logging

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DB_CONFIG = {
    'host': 'monps_postgres',
    'port': 5432,
    'dbname': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}

THRESHOLDS = {
    'min_reality_matches': 3,
    'min_system_picks': 10,
    'high_confidence_picks': 50,
    'high_confidence_matches': 10,
}

WEIGHTS = {
    'high_system_data': {'reality': 0.6, 'system': 0.4},
    'medium_system_data': {'reality': 0.8, 'system': 0.2},
    'low_system_data': {'reality': 1.0, 'system': 0.0},
}

MARKETS = [
    'btts_yes', 'btts_no',
    'over_15', 'over_25', 'over_35',
    'under_15', 'under_25', 'under_35',
    'team_over_05', 'team_over_15',
    'team_clean_sheet', 'team_win'
]

ODDS_MAP = {
    'btts_yes': 1.85, 'btts_no': 1.95,
    'over_15': 1.35, 'over_25': 1.90, 'over_35': 2.50,
    'under_15': 3.20, 'under_25': 1.95, 'under_35': 1.50,
    'team_over_05': 1.40, 'team_over_15': 2.20,
    'team_clean_sheet': 2.80, 'team_win': 2.10,
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MarketStats:
    market_type: str
    matches_played: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    avg_odds: float = 1.90
    roi: float = 0.0

@dataclass
class SystemMarketStats:
    market_type: str
    picks: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    avg_clv: float = 0.0
    total_profit: float = 0.0
    avg_odds: float = 1.90

@dataclass
class TeamProfile:
    team_name: str
    league: str
    location: str
    reality_markets: List[MarketStats] = field(default_factory=list)
    system_markets: List[SystemMarketStats] = field(default_factory=list)
    reality_best_market: Optional[str] = None
    reality_avoid_market: Optional[str] = None
    system_best_market: Optional[str] = None
    system_avoid_market: Optional[str] = None
    composite_score: float = 50.0
    confidence_level: str = 'insufficient'
    recommended_action: str = 'wait'

# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def calculate_market_outcome(home_goals: int, away_goals: int, market_type: str, is_home: bool) -> bool:
    total_goals = home_goals + away_goals
    team_goals = home_goals if is_home else away_goals
    opponent_goals = away_goals if is_home else home_goals

    outcomes = {
        'btts_yes': home_goals > 0 and away_goals > 0,
        'btts_no': home_goals == 0 or away_goals == 0,
        'over_15': total_goals > 1.5,
        'over_25': total_goals > 2.5,
        'over_35': total_goals > 3.5,
        'under_15': total_goals < 1.5,
        'under_25': total_goals < 2.5,
        'under_35': total_goals < 3.5,
        'team_over_05': team_goals > 0.5,
        'team_over_15': team_goals > 1.5,
        'team_clean_sheet': opponent_goals == 0,
        'team_win': team_goals > opponent_goals,
    }
    return outcomes.get(market_type, False)

def calculate_roi(wins: int, total: int, avg_odds: float) -> float:
    if total == 0:
        return 0.0
    profit = (wins * avg_odds) - total
    return round((profit / total) * 100, 2)

def calculate_composite_score(reality_score: float, system_score: float, system_picks: int) -> Tuple[float, str]:
    if system_picks >= THRESHOLDS['high_confidence_picks']:
        weights = WEIGHTS['high_system_data']
        confidence = 'high'
    elif system_picks >= THRESHOLDS['min_system_picks']:
        weights = WEIGHTS['medium_system_data']
        confidence = 'medium'
    else:
        weights = WEIGHTS['low_system_data']
        confidence = 'low'

    composite = (reality_score * weights['reality']) + (system_score * weights['system'])
    return round(composite, 2), confidence

def determine_recommendation(composite: float, team_win_rate: float,
                            system_profit: Optional[float],
                            system_picks: int) -> str:
    """
    Détermine l'action recommandée basée sur composite score ET win_rate.

    LOGIQUE HEDGE FUND:
    - Une équipe doit avoir un bon composite ET un bon win_rate
    - On ne recommande JAMAIS de parier sur une équipe qui ne gagne pas
    - Distribution cible: ~20% bet, ~30% wait, ~50% avoid

    Args:
        composite: Score composite 0-100
        team_win_rate: Win rate du marché team_win (%)
        system_profit: Profit total système (ignoré si < 10 picks)
        system_picks: Nombre de picks système

    Returns:
        'strong_bet', 'bet', 'wait', 'avoid', 'strong_avoid'
    """

    # RÈGLE ABSOLUE: Une équipe qui ne gagne pas = AVOID
    if team_win_rate < 20:
        return 'strong_avoid'

    if team_win_rate < 30:
        return 'avoid'

    # Strong bet: Excellente équipe (top tier)
    if composite >= 75 and team_win_rate >= 55:
        # Vérifier que le système ne contredit pas (si données dispo)
        if system_picks >= 10 and system_profit is not None and system_profit < -20:
            return 'bet'  # Downgrade car système négatif
        return 'strong_bet'

    # Bet: Bonne équipe
    if composite >= 60 and team_win_rate >= 45:
        return 'bet'

    # Avoid: Équipe faible
    if composite < 40 or team_win_rate < 35:
        return 'avoid'

    # Wait: Incertain - besoin de plus de données ou équipe moyenne
    return 'wait'

def compare_reality_vs_system(reality_wr: float, system_wr: Optional[float], system_picks: int) -> str:
    if system_picks < THRESHOLDS['min_system_picks'] or system_wr is None:
        return 'insufficient_data'
    diff = system_wr - reality_wr
    if abs(diff) < 5:
        return 'aligned'
    elif diff > 5:
        return 'system_better'
    else:
        return 'system_worse'

# ═══════════════════════════════════════════════════════════════════════════════
# EXTRACTION DONNÉES RÉALITÉ
# ═══════════════════════════════════════════════════════════════════════════════

def extract_reality_data(conn) -> Dict[Tuple[str, str, str], List[MarketStats]]:
    logger.info("Extraction données RÉALITÉ (match_xg_stats)...")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT home_team, away_team, home_goals, away_goals, league
        FROM match_xg_stats
        WHERE home_goals IS NOT NULL AND away_goals IS NOT NULL
    """)
    matches = cur.fetchall()
    logger.info(f"   -> {len(matches)} matchs trouvés")

    team_data = {}

    for match in matches:
        home_team = match['home_team']
        away_team = match['away_team']
        home_goals = int(match['home_goals'])
        away_goals = int(match['away_goals'])
        league = match['league']

        # Équipe domicile
        for location in ['home', 'overall']:
            key = (home_team, league, location)
            if key not in team_data:
                team_data[key] = {m: MarketStats(market_type=m) for m in MARKETS}
            for market in MARKETS:
                is_win = calculate_market_outcome(home_goals, away_goals, market, is_home=True)
                stats = team_data[key][market]
                stats.matches_played += 1
                if is_win:
                    stats.wins += 1
                else:
                    stats.losses += 1

        # Équipe extérieur
        for location in ['away', 'overall']:
            key = (away_team, league, location)
            if key not in team_data:
                team_data[key] = {m: MarketStats(market_type=m) for m in MARKETS}
            for market in MARKETS:
                is_win = calculate_market_outcome(home_goals, away_goals, market, is_home=False)
                stats = team_data[key][market]
                stats.matches_played += 1
                if is_win:
                    stats.wins += 1
                else:
                    stats.losses += 1

    # Calculer win_rate et ROI
    for key, markets in team_data.items():
        for market_type, stats in markets.items():
            if stats.matches_played > 0:
                stats.win_rate = round((stats.wins / stats.matches_played) * 100, 2)
                stats.avg_odds = ODDS_MAP.get(market_type, 1.90)
                stats.roi = calculate_roi(stats.wins, stats.matches_played, stats.avg_odds)

    result = {key: list(markets.values()) for key, markets in team_data.items()}
    logger.info(f"   -> {len(result)} profils équipe-location créés")
    return result

# ═══════════════════════════════════════════════════════════════════════════════
# EXTRACTION DONNÉES SYSTÈME
# ═══════════════════════════════════════════════════════════════════════════════

def extract_system_data(conn) -> Dict[Tuple[str, str], List[SystemMarketStats]]:
    """
    Extraction données SYSTÈME (tracking_clv_picks)

    DÉSACTIVÉ TEMPORAIREMENT:
    - Données insuffisantes (6 jours seulement)
    - Schéma ne permet pas d'attribuer pick à une équipe spécifique
    - Double comptage si on utilise home_team + away_team

    TODO: Réactiver quand:
    - tracking_clv_picks a 3+ mois de données
    - Colonne target_team ajoutée pour identifier l'équipe du pick

    Returns:
        Dict vide - Pas de données système pour l'instant
    """
    logger.info("Extraction données SYSTÈME (tracking_clv_picks)...")
    logger.warning("   DÉSACTIVÉ: Données insuffisantes (6 jours) + risque double comptage")
    logger.info("   -> 0 profils système (désactivé temporairement)")
    return {}

# ═══════════════════════════════════════════════════════════════════════════════
# FUSION ET CALCUL PROFILS
# ═══════════════════════════════════════════════════════════════════════════════

def build_unified_profiles(reality_data: Dict, system_data: Dict) -> List[TeamProfile]:
    logger.info("Fusion données réalité + système...")
    profiles = []

    for (team, league, location), reality_markets in reality_data.items():
        system_key = (team, 'overall')
        system_markets = system_data.get(system_key, [])

        profile = TeamProfile(
            team_name=team,
            league=league,
            location=location,
            reality_markets=reality_markets,
            system_markets=system_markets
        )

        # Meilleur/pire marché réalité
        valid_reality = [m for m in reality_markets if m.matches_played >= THRESHOLDS['min_reality_matches']]
        if valid_reality:
            best = max(valid_reality, key=lambda x: x.roi)
            worst = min(valid_reality, key=lambda x: x.roi)
            profile.reality_best_market = best.market_type
            profile.reality_avoid_market = worst.market_type

        # Meilleur/pire marché système
        valid_system = [m for m in system_markets if m.picks >= THRESHOLDS['min_system_picks']]
        if valid_system:
            best = max(valid_system, key=lambda x: x.total_profit)
            worst = min(valid_system, key=lambda x: x.total_profit)
            profile.system_best_market = best.market_type
            profile.system_avoid_market = worst.market_type

        # ═══════════════════════════════════════════════════════════════════
        # CALCUL COMPOSITE SCORE - BASÉ SUR WIN RATE GLOBAL
        # ═══════════════════════════════════════════════════════════════════

        # Trouver le win_rate du marché team_win (victoire de l'équipe)
        team_win_market = next(
            (m for m in profile.reality_markets if m.market_type == 'team_win'),
            None
        )

        if team_win_market and team_win_market.matches_played >= THRESHOLDS['min_reality_matches']:
            team_win_rate = team_win_market.win_rate
        else:
            # Fallback: moyenne des win_rates des marchés valides
            valid_markets = [m for m in profile.reality_markets
                           if m.matches_played >= THRESHOLDS['min_reality_matches']]
            team_win_rate = (sum(m.win_rate for m in valid_markets) / len(valid_markets)) if valid_markets else 0

        # Composite score basé sur win_rate global (échelle 0-100)
        # 60%+ win rate → 75-100
        # 40-60% → 50-75
        # 20-40% → 25-50
        # 0-20% → 0-25
        if team_win_rate >= 60:
            reality_score = 75 + (team_win_rate - 60) * 0.625  # 60%→75, 100%→100
        elif team_win_rate >= 40:
            reality_score = 50 + (team_win_rate - 40) * 1.25   # 40%→50, 60%→75
        elif team_win_rate >= 20:
            reality_score = 25 + (team_win_rate - 20) * 1.25   # 20%→25, 40%→50
        else:
            reality_score = team_win_rate * 1.25               # 0%→0, 20%→25

        # Pas de données système pour l'instant
        system_score = 50  # Neutre
        total_system_picks = 0

        profile.composite_score, profile.confidence_level = calculate_composite_score(
            reality_score, system_score, total_system_picks
        )

        # ═══════════════════════════════════════════════════════════════════
        # RECOMMANDATION
        # ═══════════════════════════════════════════════════════════════════

        total_system_profit = sum(m.total_profit for m in profile.system_markets) if profile.system_markets else None
        total_system_picks = sum(m.picks for m in profile.system_markets) if profile.system_markets else 0

        profile.recommended_action = determine_recommendation(
            profile.composite_score,
            team_win_rate,
            total_system_profit,
            total_system_picks
        )

        profiles.append(profile)

    logger.info(f"   -> {len(profiles)} profils unifiés créés")
    return profiles

# ═══════════════════════════════════════════════════════════════════════════════
# SAUVEGARDE EN BASE
# ═══════════════════════════════════════════════════════════════════════════════

def save_profiles(conn, profiles: List[TeamProfile]):
    logger.info("Sauvegarde en base de données...")
    cur = conn.cursor()
    saved = 0

    for profile in profiles:
        reality_markets_json = json.dumps([{
            'market_type': m.market_type,
            'matches_played': m.matches_played,
            'wins': m.wins,
            'losses': m.losses,
            'win_rate': m.win_rate,
            'avg_odds': m.avg_odds,
            'roi': m.roi
        } for m in profile.reality_markets if m.matches_played > 0])

        system_markets_json = json.dumps([{
            'market_type': m.market_type,
            'picks': m.picks,
            'wins': m.wins,
            'losses': m.losses,
            'win_rate': m.win_rate,
            'avg_clv': m.avg_clv,
            'total_profit': m.total_profit,
            'avg_odds': m.avg_odds
        } for m in profile.system_markets if m.picks > 0]) if profile.system_markets else '[]'

        # Calculer reality_win_rate depuis le marché team_win
        team_win_market = next(
            (m for m in profile.reality_markets if m.market_type == 'team_win'),
            None
        )
        reality_wr = team_win_market.win_rate if team_win_market else 0
        total_matches = team_win_market.matches_played if team_win_market else 0
        total_wins_team = team_win_market.wins if team_win_market else 0

        total_picks = sum(m.picks for m in profile.system_markets)
        system_wins = sum(m.wins for m in profile.system_markets)
        system_profit = sum(m.total_profit for m in profile.system_markets)
        system_wr = round((system_wins / total_picks * 100), 2) if total_picks > 0 else None
        system_avg_clv = round(sum(m.avg_clv * m.picks for m in profile.system_markets) / total_picks, 2) if total_picks > 0 else None

        insight = compare_reality_vs_system(reality_wr, system_wr, total_picks)

        reality_completeness = min(1.0, total_matches / 10)
        system_completeness = min(1.0, total_picks / 50)
        data_quality = round((reality_completeness * 0.7 + system_completeness * 0.3) * 100, 2)

        cur.execute("""
            INSERT INTO team_market_profiles_v3 (
                team_name, league, season, location,
                reality_matches_played, reality_wins, reality_win_rate,
                reality_best_market, reality_avoid_market, reality_markets_detail,
                system_picks_count, system_wins, system_win_rate,
                system_avg_clv, system_total_profit,
                system_best_market, system_avoid_market, system_markets_detail,
                composite_score, confidence_level, data_quality_score,
                recommended_action, insight_reality_vs_system,
                updated_at, reality_data_date, system_data_date
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                NOW(), CURRENT_DATE, CURRENT_DATE
            )
            ON CONFLICT (team_name, league, season, location)
            DO UPDATE SET
                reality_matches_played = EXCLUDED.reality_matches_played,
                reality_wins = EXCLUDED.reality_wins,
                reality_win_rate = EXCLUDED.reality_win_rate,
                reality_best_market = EXCLUDED.reality_best_market,
                reality_avoid_market = EXCLUDED.reality_avoid_market,
                reality_markets_detail = EXCLUDED.reality_markets_detail,
                system_picks_count = EXCLUDED.system_picks_count,
                system_wins = EXCLUDED.system_wins,
                system_win_rate = EXCLUDED.system_win_rate,
                system_avg_clv = EXCLUDED.system_avg_clv,
                system_total_profit = EXCLUDED.system_total_profit,
                system_best_market = EXCLUDED.system_best_market,
                system_avoid_market = EXCLUDED.system_avoid_market,
                system_markets_detail = EXCLUDED.system_markets_detail,
                composite_score = EXCLUDED.composite_score,
                confidence_level = EXCLUDED.confidence_level,
                data_quality_score = EXCLUDED.data_quality_score,
                recommended_action = EXCLUDED.recommended_action,
                insight_reality_vs_system = EXCLUDED.insight_reality_vs_system,
                updated_at = NOW(),
                reality_data_date = CURRENT_DATE,
                system_data_date = CURRENT_DATE
        """, (
            profile.team_name, profile.league, '2024-2025', profile.location,
            total_matches, total_wins_team, reality_wr,
            profile.reality_best_market, profile.reality_avoid_market, reality_markets_json,
            total_picks, system_wins, system_wr,
            system_avg_clv, system_profit,
            profile.system_best_market, profile.system_avoid_market, system_markets_json,
            profile.composite_score, profile.confidence_level, data_quality,
            profile.recommended_action, insight,
        ))
        saved += 1

    conn.commit()
    logger.info(f"   -> {saved} profils sauvegardés")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 80)
    print("TEAM MARKET PROFILER V3 - UNIFIED HEDGE FUND GRADE")
    print("=" * 80)

    start_time = datetime.now()

    try:
        conn = get_connection()
        reality_data = extract_reality_data(conn)
        system_data = extract_system_data(conn)
        profiles = build_unified_profiles(reality_data, system_data)
        save_profiles(conn, profiles)

        duration = (datetime.now() - start_time).total_seconds()

        print("=" * 80)
        print(f"TERMINÉ en {duration:.1f}s")
        print(f"   Profils créés: {len(profiles)}")
        print(f"   Équipes uniques: {len(set(p.team_name for p in profiles))}")
        print(f"   Avec données système: {len([p for p in profiles if p.system_markets])}")
        print("=" * 80)

        conn.close()

    except Exception as e:
        logger.error(f"ERREUR: {e}")
        raise

if __name__ == "__main__":
    main()
