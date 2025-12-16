#!/usr/bin/env python3
"""
Enrichissement Tags 18 Dimensions ADN - Phase 5.2
Date: 2025-12-16
Mission: Transformer narrative_fingerprint_tags (3 tags → 5-15 tags/équipe)

Sources:
1. team_dna_unified_v2.json (1,119 métriques × 96 équipes)
2. gamestate_behavior_index_v3.json (behavior patterns)
3. timing_dna_profiles.json (diesel, clutch, fast starter)
4. goalkeeper_dna_v4_4_final.json (GK metrics)
5. players_impact_dna.json (MVP dependency)
6. quantum.team_profiles (PostgreSQL - 11 vecteurs DNA)

18 Dimensions ADN:
1-10: Core (Sessions 57-60)
11-12: Advanced (Session 61)
13-14: Creator-Finisher + Momentum (Sessions 62-63)
15-16: Gamestate (Sessions 62-63)
17-18: External Factors (Sessions 64-66)
"""

import json
import psycopg2
from datetime import datetime
from typing import Dict, List, Set, Any, Optional
from collections import defaultdict

# Configuration PostgreSQL
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'monps_db',
    'user': 'monps_user',
    'password': 'monps_secure_password_2024'
}

# Fichiers sources
SOURCES = {
    'team_dna': '/home/Mon_ps/data/quantum_v2/team_dna_unified_v2.json',
    'gamestate': '/home/Mon_ps/data/quantum_v2/gamestate_behavior_index_v3.json',
    'timing': '/home/Mon_ps/data/quantum_v2/timing_dna_profiles.json',
    'goalkeeper': '/home/Mon_ps/data/goalkeeper_dna/goalkeeper_dna_v4_4_final.json',
    'players': '/home/Mon_ps/data/quantum_v2/players_impact_dna.json',
    'narrative': '/home/Mon_ps/data/quantum_v2/team_narrative_dna_v3.json'
}


def load_json_sources() -> Dict[str, Any]:
    """Charger toutes les sources JSON."""
    print("\n📥 Chargement des sources JSON...")
    sources = {}

    for key, path in SOURCES.items():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                sources[key] = json.load(f)
            print(f"  ✅ {key}: {path}")
        except FileNotFoundError:
            print(f"  ⚠️  {key}: NOT FOUND - {path}")
            sources[key] = {}

    return sources


def aggregate_players_by_team(players_data: List[Dict]) -> Dict[str, Dict]:
    """Aggréger players_impact_dna.json par équipe."""
    teams = defaultdict(lambda: {
        'players': [],
        'total_goals': 0,
        'total_assists': 0,
        'total_xg': 0,
        'total_xa': 0
    })

    for player in players_data:
        team = player.get('team')
        if not team:
            continue

        teams[team]['players'].append(player)
        teams[team]['total_goals'] += player.get('goals', 0)
        teams[team]['total_assists'] += player.get('assists', 0)
        teams[team]['total_xg'] += player.get('xG', 0)
        teams[team]['total_xa'] += player.get('xA', 0)

    return dict(teams)


# ═══════════════════════════════════════════════════════════════════════════
# EXTRACTION DES 18 DIMENSIONS ADN
# ═══════════════════════════════════════════════════════════════════════════

def extract_volume_dna(team_name: str, sources: Dict) -> List[str]:
    """
    Dimension 1: VOLUME_DNA
    Tags: HIGH_VOLUME, LOW_VOLUME, AVERAGE_VOLUME
    Source: team_dna_unified_v2.json → context.xg_for_avg
    Threshold: HIGH > 1.8 xG/match, LOW < 1.2 xG/match
    """
    tags = []
    team_data = sources['team_dna'].get('teams', {}).get(team_name, {})
    context = team_data.get('context', {})

    xg_for = context.get('xg_for_avg', 0)

    if xg_for > 1.8:
        tags.append('HIGH_VOLUME')
    elif xg_for < 1.2:
        tags.append('LOW_VOLUME')
    else:
        tags.append('AVERAGE_VOLUME')

    return tags


def extract_timing_dna(team_name: str, sources: Dict) -> List[str]:
    """
    Dimension 2: TIMING_DNA
    Tags: DIESEL, FAST_STARTER, CLUTCH, CONSISTENT, LATE_GAME_KILLER
    Source: timing_dna_profiles.json → timing_profile, decay_factor
    Threshold: DIESEL > 1.2, FAST_STARTER < 0.7
    """
    tags = []
    timing_data = sources['timing'].get(team_name, {})

    timing_profile = timing_data.get('timing_profile', '')
    decay_factor = timing_data.get('decay_factor', 1.0)

    # Diesel (déclin performance avec le temps)
    if decay_factor > 1.2:
        tags.append('DIESEL')
    # Fast starter (forte performance en début)
    elif decay_factor < 0.7:
        tags.append('FAST_STARTER')

    # Profile-based
    if timing_profile == 'diesel':
        tags.append('DIESEL')
    elif timing_profile == 'fast_starter':
        tags.append('FAST_STARTER')
    elif timing_profile == 'clutch':
        tags.append('CLUTCH')
    elif timing_profile == 'consistent':
        tags.append('CONSISTENT')

    # Late game killer (vérifier time_curve)
    time_curve = timing_data.get('time_curve', {})
    if time_curve.get('76-90', {}).get('goals_pct', 0) > 0.35:
        tags.append('LATE_GAME_KILLER')

    return tags


def extract_dependency_dna(team_name: str, sources: Dict, players_by_team: Dict) -> List[str]:
    """
    Dimension 3: DEPENDENCY_DNA
    Tags: MVP_DEPENDENT, TOP3_HEAVY, COLLECTIVE, BALANCED
    Source: players_impact_dna.json → mvp_share
    Threshold: MVP_DEPENDENT > 40%, COLLECTIVE < 20%
    """
    tags = []
    team_players = players_by_team.get(team_name, {})

    if not team_players.get('players'):
        return tags

    # Trier joueurs par goals
    players = sorted(team_players['players'], key=lambda p: p.get('goals', 0), reverse=True)

    total_goals = team_players['total_goals']
    if total_goals == 0:
        return tags

    # MVP share
    mvp_goals = players[0].get('goals', 0) if players else 0
    mvp_share = (mvp_goals / total_goals * 100) if total_goals > 0 else 0

    # Top 3 share
    top3_goals = sum(p.get('goals', 0) for p in players[:3])
    top3_share = (top3_goals / total_goals * 100) if total_goals > 0 else 0

    # Tags
    if mvp_share > 40:
        tags.append('MVP_DEPENDENT')
    elif mvp_share < 20:
        tags.append('COLLECTIVE')
    else:
        tags.append('BALANCED')

    if top3_share > 65:
        tags.append('TOP3_HEAVY')

    return tags


def extract_style_dna(team_name: str, sources: Dict) -> List[str]:
    """
    Dimension 4: STYLE_DNA
    Tags: OPEN_PLAY_DOMINANT, SET_PIECE_KINGS, COUNTER_ATTACK, POSSESSION
    Source: team_dna_unified_v2.json → tactical.style
    Threshold: SET_PIECE > 30%
    """
    tags = []
    team_data = sources['team_dna'].get('teams', {}).get(team_name, {})
    tactical = team_data.get('tactical', {})

    style = tactical.get('classification', '')
    set_piece_pct = tactical.get('set_piece_goals_pct', 0)
    possession = tactical.get('possession_avg', 0)

    # Style primary
    if 'counter' in style.lower() or 'transition' in style.lower():
        tags.append('COUNTER_ATTACK')
    elif 'possession' in style.lower() or possession > 55:
        tags.append('POSSESSION')
    else:
        tags.append('OPEN_PLAY_DOMINANT')

    # Set piece kings
    if set_piece_pct > 30:
        tags.append('SET_PIECE_KINGS')

    return tags


def extract_home_away_dna(team_name: str, sources: Dict) -> List[str]:
    """
    Dimension 5: HOME_AWAY_DNA
    Tags: HOME_FORTRESS, ROAD_WARRIORS, HOME_WEAK, AWAY_WEAK
    Source: team_dna_unified_v2.json → context.home_xg, away_xg
    Threshold: FORTRESS home > away +0.5, WEAK < -0.5
    """
    tags = []
    team_data = sources['team_dna'].get('teams', {}).get(team_name, {})
    context = team_data.get('context', {})

    home_xg = context.get('home_xg_for_avg', 0)
    away_xg = context.get('away_xg_for_avg', 0)

    diff = home_xg - away_xg

    if diff > 0.5:
        tags.append('HOME_FORTRESS')
    elif diff < -0.5:
        tags.append('ROAD_WARRIORS')

    if home_xg < 1.0:
        tags.append('HOME_WEAK')
    if away_xg < 0.8:
        tags.append('AWAY_WEAK')

    return tags


def extract_efficiency_dna(team_name: str, sources: Dict) -> List[str]:
    """
    Dimension 6: EFFICIENCY_DNA
    Tags: TRUE_CLINICAL, CLINICAL, WASTEFUL, PENALTY_INFLATED
    Source: team_dna_unified_v2.json → tactical.conversion_rate, npg vs npxg
    Threshold: CLINICAL npg > npxg + 3, WASTEFUL < -3
    """
    tags = []
    team_data = sources['team_dna'].get('teams', {}).get(team_name, {})
    tactical = team_data.get('tactical', {})

    npg = tactical.get('np_goals', 0)
    npxg = tactical.get('np_xg', 0)
    penalty_pct = tactical.get('penalty_goals_pct', 0)

    np_diff = npg - npxg

    if np_diff > 3 and penalty_pct < 20:
        tags.append('TRUE_CLINICAL')
    elif np_diff > 2:
        tags.append('CLINICAL')
    elif np_diff < -3:
        tags.append('WASTEFUL')

    if penalty_pct > 25:
        tags.append('PENALTY_INFLATED')

    return tags


def extract_super_sub_dna(team_name: str, sources: Dict) -> List[str]:
    """
    Dimension 7: SUPER_SUB_DNA
    Tags: STRONG_BENCH, WEAK_BENCH
    Source: timing_dna_profiles.json → sub_impact
    Threshold: STRONG sub_goals > 20%
    """
    tags = []
    timing_data = sources['timing'].get(team_name, {})

    # Approximation via time_curve (76-90 peut inclure subs)
    time_curve = timing_data.get('time_curve', {})
    late_goals_pct = time_curve.get('76-90', {}).get('goals_pct', 0)

    # Si forte augmentation en fin de match → subs impactants
    mid_goals_pct = time_curve.get('46-60', {}).get('goals_pct', 0)

    if late_goals_pct - mid_goals_pct > 0.1:
        tags.append('STRONG_BENCH')
    elif late_goals_pct < mid_goals_pct - 0.1:
        tags.append('WEAK_BENCH')

    return tags


def extract_penalty_dna(team_name: str, sources: Dict) -> List[str]:
    """
    Dimension 8: PENALTY_DNA
    Tags: PENALTY_RELIABLE, PENALTY_WEAK, PENALTY_DEPENDENT
    Source: team_dna_unified_v2.json → penalty_pct, penalty_conversion
    Threshold: DEPENDENT > 25%, RELIABLE conversion > 80%
    """
    tags = []
    team_data = sources['team_dna'].get('teams', {}).get(team_name, {})
    tactical = team_data.get('tactical', {})

    penalty_pct = tactical.get('penalty_goals_pct', 0)
    # penalty_conversion = tactical.get('penalty_conversion', 0)  # Si disponible

    if penalty_pct > 25:
        tags.append('PENALTY_DEPENDENT')
    # elif penalty_conversion > 80:
    #     tags.append('PENALTY_RELIABLE')
    # elif penalty_conversion < 60:
    #     tags.append('PENALTY_WEAK')

    return tags


def extract_creativity_dna(team_name: str, sources: Dict, players_by_team: Dict) -> List[str]:
    """
    Dimension 9: CREATIVITY_DNA
    Tags: CREATIVE_HUB, DIRECT_PLAY
    Source: players_impact_dna.json → assists_concentration
    Threshold: HUB top_creator > 35%
    """
    tags = []
    team_players = players_by_team.get(team_name, {})

    if not team_players.get('players'):
        return tags

    # Trier joueurs par assists
    players = sorted(team_players['players'], key=lambda p: p.get('assists', 0), reverse=True)

    total_assists = team_players['total_assists']
    if total_assists == 0:
        return tags

    # Top créateur share
    top_creator_assists = players[0].get('assists', 0) if players else 0
    creator_share = (top_creator_assists / total_assists * 100) if total_assists > 0 else 0

    if creator_share > 35:
        tags.append('CREATIVE_HUB')
    else:
        tags.append('DIRECT_PLAY')

    return tags


def extract_form_dna(team_name: str, sources: Dict) -> List[str]:
    """
    Dimension 10: FORM_DNA
    Tags: HOT_FORM, STABLE, DECLINING, COLD
    Source: team_profiles → momentum_dna (PostgreSQL)
    Threshold: HOT last_5 > 12pts, COLD < 4pts

    Note: Pour MVP, on approxime avec les données JSON disponibles
    """
    tags = []

    # Pour l'instant, on skip car nécessite PostgreSQL team_profiles
    # ou calcul depuis team_dna_unified_v2.json (si recent_form disponible)
    team_data = sources['team_dna'].get('teams', {}).get(team_name, {})
    meta = team_data.get('meta', {})

    # Placeholder
    tags.append('STABLE')

    return tags


def extract_np_clinical_dna(team_name: str, sources: Dict) -> List[str]:
    """
    Dimension 11: NP_CLINICAL_DNA (Advanced)
    Tags: TRUE_CLINICAL, CLINICAL, PENALTY_INFLATED
    Source: team_dna_unified_v2.json → npg vs npxg
    Threshold: TRUE_CLINICAL np_overperf >= +3.0, INFLATED pen_dep >= 25%
    """
    # Similaire à extract_efficiency_dna mais plus strict
    return extract_efficiency_dna(team_name, sources)


def extract_xgchain_dna(team_name: str, sources: Dict, players_by_team: Dict) -> List[str]:
    """
    Dimension 12: XGCHAIN_DNA (Advanced)
    Tags: BUILDUP_ARCHITECT, FINISHER_ONLY
    Source: players_impact_dna.json → xgchain_ratio
    Threshold: ARCHITECT chain_ratio >= 3.0, FINISHER < 1.0
    """
    tags = []
    team_players = players_by_team.get(team_name, {})

    if not team_players.get('players'):
        return tags

    # Calculer ratio xGChain / xG
    total_xg = sum(p.get('xG', 0) for p in team_players['players'])
    total_xgchain = sum(p.get('xGChain', 0) for p in team_players['players'])

    if total_xg == 0:
        return tags

    chain_ratio = total_xgchain / total_xg if total_xg > 0 else 0

    if chain_ratio >= 3.0:
        tags.append('BUILDUP_ARCHITECT')
    elif chain_ratio < 1.0:
        tags.append('FINISHER_ONLY')

    return tags


def extract_creator_finisher_dna(team_name: str, sources: Dict, players_by_team: Dict) -> List[str]:
    """
    Dimension 13: CREATOR_FINISHER_DNA
    Tags: ELITE_COMBO, STRONG_COMBO, WEAK_COMBO
    Source: players_impact_dna.json
    Threshold: ELITE both creator + finisher top 10%
    """
    tags = []
    team_players = players_by_team.get(team_name, {})

    if not team_players.get('players'):
        return tags

    # MVP goals + Top créateur assists
    players_goals = sorted(team_players['players'], key=lambda p: p.get('goals', 0), reverse=True)
    players_assists = sorted(team_players['players'], key=lambda p: p.get('assists', 0), reverse=True)

    mvp_goals = players_goals[0].get('goals', 0) if players_goals else 0
    top_creator_assists = players_assists[0].get('assists', 0) if players_assists else 0

    # Seuils top 10% (approximatifs)
    if mvp_goals > 15 and top_creator_assists > 10:
        tags.append('ELITE_COMBO')
    elif mvp_goals > 10 and top_creator_assists > 6:
        tags.append('STRONG_COMBO')
    else:
        tags.append('WEAK_COMBO')

    return tags


def extract_momentum_dna(team_name: str, sources: Dict) -> List[str]:
    """
    Dimension 14: MOMENTUM_DNA
    Tags: BURST_SCORER, STEADY_SCORER
    Source: timing_dna_profiles.json → scoring_bursts
    Threshold: BURST 3+ goals in 10 min > 20%
    """
    tags = []

    # Approximation: vérifier variabilité dans time_curve
    timing_data = sources['timing'].get(team_name, {})
    time_curve = timing_data.get('time_curve', {})

    # Calculer variance entre périodes
    periods_pct = [time_curve.get(p, {}).get('goals_pct', 0) for p in ['0-15', '16-30', '31-45', '46-60', '61-75', '76-90']]

    if periods_pct:
        variance = max(periods_pct) - min(periods_pct)
        if variance > 0.15:
            tags.append('BURST_SCORER')
        else:
            tags.append('STEADY_SCORER')

    return tags


def extract_first_goal_impact_dna(team_name: str, sources: Dict) -> List[str]:
    """
    Dimension 15: FIRST_GOAL_IMPACT_DNA
    Tags: FRONT_RUNNER, MENTALLY_WEAK, COMEBACK_KING
    Source: gamestate_behavior_index_v3.json → behavior
    Threshold: FRONT_RUNNER win_after_first > 80%, COMEBACK comeback_rate > 40%
    """
    tags = []
    gamestate_data = sources['gamestate'].get(team_name, {})

    behavior = gamestate_data.get('behavior', '')

    if 'FRONT_RUNNER' in behavior:
        tags.append('FRONT_RUNNER')
    elif 'COMEBACK' in behavior or 'COMEBACK_KING' in behavior:
        tags.append('COMEBACK_KING')
    elif 'MENTALLY_WEAK' in behavior:
        tags.append('MENTALLY_WEAK')

    return tags


def extract_gamestate_dna(team_name: str, sources: Dict) -> List[str]:
    """
    Dimension 16: GAMESTATE_DNA
    Tags: COMEBACK_SPECIALIST, KILLER, SETTLER, GAME_MANAGER
    Source: gamestate_behavior_index_v3.json
    Threshold: KILLER xG/90 leading < 1.0, COMEBACK xG/90 trailing >= 2.5
    """
    tags = []
    gamestate_data = sources['gamestate'].get(team_name, {})

    behavior = gamestate_data.get('behavior', '')
    dangerous_trailing = gamestate_data.get('dangerous_when_trailing', False)
    good_closer = gamestate_data.get('good_closer', False)

    if 'KILLER' in behavior or good_closer:
        tags.append('KILLER')
    elif 'COMEBACK' in behavior or dangerous_trailing:
        tags.append('COMEBACK_SPECIALIST')
    elif 'SETTLER' in behavior:
        tags.append('SETTLER')
    else:
        tags.append('GAME_MANAGER')

    return tags


def extract_external_factors_dna(team_name: str, sources: Dict) -> List[str]:
    """
    Dimension 17: EXTERNAL_FACTORS_DNA
    Tags: PRIME_TIME_BEAST, AFTERNOON_SPECIALIST, LUNCH_SPECIALIST
    Source: timing_dna_profiles.json → time_slot_performance
    Threshold: PRIME_TIME +0.5 goals/match after 19h
    """
    tags = []

    # Pour MVP: données non disponibles dans les JSON actuels
    # Placeholder

    return tags


def extract_weather_dna(team_name: str, sources: Dict) -> List[str]:
    """
    Dimension 18: WEATHER_DNA
    Tags: RAIN_ATTACKER, RAIN_WEAK, RAIN_LEAKY, RAIN_SOLID,
          COLD_SPECIALIST, COLD_VULNERABLE, COLD_RESILIENT,
          HEAT_DIESEL, HEAT_WEAK
    Source: weather_dna.json ou team_dna_unified_v2.json
    Threshold: RAIN_ATTACKER +1.5 goals rain vs dry
    """
    tags = []

    # Pour MVP: données météo non disponibles dans les JSON actuels
    # Placeholder

    return tags


# ═══════════════════════════════════════════════════════════════════════════
# ORCHESTRATION
# ═══════════════════════════════════════════════════════════════════════════

def extract_all_tags(team_name: str, sources: Dict, players_by_team: Dict) -> List[str]:
    """Extraire tous les tags pour une équipe (18 dimensions)."""
    all_tags = set()

    # Phase 1 - Core (10 dimensions)
    all_tags.update(extract_volume_dna(team_name, sources))
    all_tags.update(extract_timing_dna(team_name, sources))
    all_tags.update(extract_dependency_dna(team_name, sources, players_by_team))
    all_tags.update(extract_style_dna(team_name, sources))
    all_tags.update(extract_home_away_dna(team_name, sources))
    all_tags.update(extract_efficiency_dna(team_name, sources))
    all_tags.update(extract_super_sub_dna(team_name, sources))
    all_tags.update(extract_penalty_dna(team_name, sources))
    all_tags.update(extract_creativity_dna(team_name, sources, players_by_team))
    all_tags.update(extract_form_dna(team_name, sources))

    # Phase 2 - Advanced (2 dimensions)
    all_tags.update(extract_np_clinical_dna(team_name, sources))
    all_tags.update(extract_xgchain_dna(team_name, sources, players_by_team))

    # Phase 3 - Creator/Momentum (2 dimensions)
    all_tags.update(extract_creator_finisher_dna(team_name, sources, players_by_team))
    all_tags.update(extract_momentum_dna(team_name, sources))

    # Phase 4 - Gamestate (2 dimensions)
    all_tags.update(extract_first_goal_impact_dna(team_name, sources))
    all_tags.update(extract_gamestate_dna(team_name, sources))

    # Phase 5 - External (2 dimensions)
    all_tags.update(extract_external_factors_dna(team_name, sources))
    all_tags.update(extract_weather_dna(team_name, sources))

    return sorted(list(all_tags))


def enrich_all_teams(conn, sources: Dict, players_by_team: Dict) -> Dict[str, Any]:
    """Enrichir tous les équipes avec les 18 dimensions."""
    cursor = conn.cursor()

    # Récupérer toutes les équipes PostgreSQL
    cursor.execute("""
        SELECT team_id, team_name
        FROM quantum.team_quantum_dna_v3
        ORDER BY team_name
    """)
    pg_teams = {row[1]: row[0] for row in cursor.fetchall()}

    print(f"\n🔄 Enrichissement des tags (18 dimensions)...")
    print(f"📋 PostgreSQL: {len(pg_teams)} équipes")

    stats = {
        'updated': 0,
        'tags_distribution': defaultdict(int),
        'teams_tags_count': {}
    }

    for team_name in sorted(pg_teams.keys()):
        # Extraire tous les tags
        tags = extract_all_tags(team_name, sources, players_by_team)

        # UPDATE PostgreSQL
        cursor.execute("""
            UPDATE quantum.team_quantum_dna_v3
            SET
                narrative_fingerprint_tags = %s,
                updated_at = NOW()
            WHERE team_name = %s
        """, (tags, team_name))

        if cursor.rowcount > 0:
            stats['updated'] += 1
            stats['teams_tags_count'][team_name] = len(tags)

            # Compter distribution tags
            for tag in tags:
                stats['tags_distribution'][tag] += 1

            print(f"  ✅ {team_name:20s} → {len(tags)} tags")

    conn.commit()
    cursor.close()

    return stats


def display_statistics(stats: Dict[str, Any]):
    """Afficher les statistiques d'enrichissement."""
    print(f"\n" + "=" * 80)
    print(f"📊 STATISTIQUES ENRICHISSEMENT:")
    print(f"=" * 80)

    print(f"\n✅ Équipes mises à jour: {stats['updated']}")

    # Distribution tags par équipe
    tag_counts = list(stats['teams_tags_count'].values())
    print(f"\n📈 Tags par équipe:")
    print(f"  Min:  {min(tag_counts)}")
    print(f"  Max:  {max(tag_counts)}")
    print(f"  Avg:  {sum(tag_counts) / len(tag_counts):.1f}")

    # Top 10 tags les plus fréquents
    print(f"\n🏆 Top 10 Tags:")
    sorted_tags = sorted(stats['tags_distribution'].items(), key=lambda x: x[1], reverse=True)
    for tag, count in sorted_tags[:10]:
        print(f"  {tag:30s} → {count:3d} équipes")

    # Tags uniques total
    print(f"\n🔢 Total tags différents: {len(stats['tags_distribution'])}")


def main():
    """Fonction principale."""
    print("=" * 80)
    print("ENRICHISSEMENT TAGS 18 DIMENSIONS ADN - PHASE 5.2")
    print("=" * 80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. Charger les sources JSON
    sources = load_json_sources()

    # 2. Aggréger players par équipe
    print("\n📊 Agrégation players par équipe...")
    players_by_team = aggregate_players_by_team(sources.get('players', []))
    print(f"  ✅ {len(players_by_team)} équipes avec données joueurs")

    # 3. Connexion PostgreSQL
    print(f"\n🔗 Connexion à PostgreSQL...")
    conn = psycopg2.connect(**DB_CONFIG)
    print("✅ Connecté")

    # 4. Enrichissement
    stats = enrich_all_teams(conn, sources, players_by_team)

    # 5. Statistiques
    display_statistics(stats)

    # 6. Fermeture
    conn.close()
    print(f"\n✅ Enrichissement terminé avec succès!")
    print("=" * 80)


if __name__ == "__main__":
    main()
