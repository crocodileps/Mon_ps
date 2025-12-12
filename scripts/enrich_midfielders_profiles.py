#!/usr/bin/env python3
"""
ENRICHISSEMENT DES PROFILS MILIEUX - HEDGE FUND GRADE
Solution de contournement: utiliser les données existantes au lieu de FBRef

Sources utilisées:
1. defender_dna_quant_v9.json → 140 milieux défensifs avec données complètes
2. players_impact_dna.json → 2324 joueurs avec xG, xA, xGChain, xGBuildup
3. player_dna_unified.json → Fichier cible à enrichir
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict

# ============================================================================
# CHEMINS DES FICHIERS
# ============================================================================

DEFENDER_DNA_FILE = '/home/Mon_ps/data/defender_dna/defender_dna_quant_v9.json'
PLAYERS_IMPACT_FILE = '/home/Mon_ps/data/quantum_v2/players_impact_dna.json'
UNIFIED_FILE = '/home/Mon_ps/data/quantum_v2/player_dna_unified.json'
OUTPUT_FILE = '/home/Mon_ps/data/quantum_v2/player_dna_unified.json'

# ============================================================================
# MAPPING DES FORCES/FAIBLESSES MILIEUX
# ============================================================================

MIDFIELDER_STRENGTH_MAPPING = {
    "playmaker": {
        "markets": ["assists_market", "team_goals_over"],
        "edge_type": "indirect_positive",
        "edge_mechanism": "chance_creation_above_average",
        "description": "Crée beaucoup d'occasions (key_passes élevés)"
    },
    "chain_initiator": {
        "markets": ["team_goals_over", "btts_yes"],
        "edge_type": "indirect_positive",
        "edge_mechanism": "high_xGChain_involvement",
        "description": "Impliqué dans les chaînes de buts (xGChain élevé)"
    },
    "buildup_specialist": {
        "markets": ["possession_over", "team_goals_over"],
        "edge_type": "indirect_positive",
        "edge_mechanism": "progressive_buildup_contribution",
        "description": "Contribue fortement au buildup (xGBuildup élevé)"
    },
    "goal_threat": {
        "markets": ["anytime_scorer", "team_goals_over"],
        "edge_type": "direct_positive",
        "edge_mechanism": "midfielder_goal_threat",
        "description": "Menace offensive directe pour un milieu"
    },
    "assist_machine": {
        "markets": ["assists_market", "first_assist"],
        "edge_type": "direct_positive",
        "edge_mechanism": "high_assist_output",
        "description": "Production de passes décisives élevée"
    },
    "disciplined": {
        "markets": ["no_cards_player", "team_cards_under"],
        "edge_type": "direct_negative",
        "edge_mechanism": "low_card_risk",
        "description": "Rarement averti (cards_90 bas)"
    },
    "clutch_performer": {
        "markets": ["late_goal", "team_to_score_2h"],
        "edge_type": "indirect_positive",
        "edge_mechanism": "late_game_influence",
        "description": "Performe en fin de match (clutch élevé)"
    },
    "consistent": {
        "markets": ["team_performance", "clean_sheet"],
        "edge_type": "indirect_positive",
        "edge_mechanism": "low_volatility_stabilizer",
        "description": "Performances régulières (volatility basse)"
    },
    "leader": {
        "markets": ["team_win", "team_performance"],
        "edge_type": "indirect_positive",
        "edge_mechanism": "leadership_boost",
        "description": "Impact de leadership sur l'équipe"
    },
    "home_specialist": {
        "markets": ["home_win", "home_goals_over"],
        "edge_type": "direct_positive",
        "edge_mechanism": "home_overperformance",
        "description": "Meilleur à domicile"
    },
    "duel_winner": {
        "markets": ["team_possession", "team_performance"],
        "edge_type": "indirect_positive",
        "edge_mechanism": "duel_dominance",
        "description": "Gagne ses duels régulièrement"
    }
}

MIDFIELDER_WEAKNESS_MAPPING = {
    "card_prone": {
        "markets": ["player_card", "team_cards_over"],
        "edge_type": "direct_positive",
        "edge_mechanism": "high_card_risk",
        "description": "Risque élevé de carton (cards_90 haut)"
    },
    "inconsistent": {
        "markets": ["team_performance"],
        "edge_type": "indirect_negative",
        "edge_mechanism": "high_volatility_destabilizer",
        "description": "Performances irrégulières"
    },
    "tilt_risk": {
        "markets": ["player_card", "team_discipline"],
        "edge_type": "direct_positive",
        "edge_mechanism": "emotional_instability",
        "description": "Susceptible de perdre son calme"
    },
    "away_weakness": {
        "markets": ["away_goals_under", "away_loss"],
        "edge_type": "indirect_negative",
        "edge_mechanism": "away_underperformance",
        "description": "Moins bon à l'extérieur"
    },
    "limited_creator": {
        "markets": ["assists_market"],
        "edge_type": "direct_negative",
        "edge_mechanism": "low_chance_creation",
        "description": "Peu de création d'occasions"
    },
    "invisible_buildup": {
        "markets": ["team_goals_over"],
        "edge_type": "indirect_negative",
        "edge_mechanism": "low_buildup_contribution",
        "description": "Peu impliqué dans le jeu de construction"
    }
}

# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def normalize_name(name: str) -> str:
    """Normalise un nom pour la correspondance"""
    import unicodedata
    # Supprimer accents
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    # Lowercase et strip
    return name.lower().strip()


def calculate_confidence(sample_size: int, base: str = "MEDIUM") -> float:
    """Calcule un score de confiance"""
    base_map = {"VERY_LOW": 0.2, "LOW": 0.4, "MEDIUM": 0.6, "HIGH": 0.8, "VERY_HIGH": 0.9}
    base_score = base_map.get(base, 0.5)

    if sample_size >= 30:
        factor = 1.0
    elif sample_size >= 20:
        factor = 0.9
    elif sample_size >= 10:
        factor = 0.75
    elif sample_size >= 5:
        factor = 0.6
    else:
        factor = 0.4

    return round(min(0.95, base_score * factor), 2)


def enrich_trait(trait: str, is_strength: bool) -> dict:
    """Enrichit un trait avec les infos de marché"""
    mapping = MIDFIELDER_STRENGTH_MAPPING if is_strength else MIDFIELDER_WEAKNESS_MAPPING
    if trait in mapping:
        return {"trait": trait, **mapping[trait]}
    else:
        return {
            "trait": trait,
            "markets": ["general"],
            "edge_type": "indirect_positive" if is_strength else "indirect_negative",
            "edge_mechanism": "unclassified",
            "description": trait.replace("_", " ").title()
        }


def get_percentile(value: float, all_values: List[float]) -> int:
    """Calcule le percentile d'une valeur"""
    if not all_values or value is None:
        return 50
    sorted_vals = sorted(all_values)
    count_below = sum(1 for v in sorted_vals if v < value)
    return int(100 * count_below / len(sorted_vals))


# ============================================================================
# EXTRACTION DES DONNÉES MILIEUX
# ============================================================================

def extract_midfielder_profile_from_defender_dna(player_data: dict) -> dict:
    """
    Extrait un profil milieu depuis defender_dna (données riches)
    """
    profile = {
        "source": "defender_dna_quant_v9",
        "position": player_data.get("position", ""),
        "games": player_data.get("games", 0),
        "time_90": player_data.get("time_90", 0),

        # Offensive metrics
        "goals": player_data.get("goals", 0),
        "assists": player_data.get("assists", 0),
        "xG": player_data.get("xG", 0),
        "xA": player_data.get("xA", 0),
        "xA_90": player_data.get("xA_90", 0),
        "key_passes": player_data.get("key_passes", 0),
        "xGChain": player_data.get("xGChain", 0),
        "xGBuildup": player_data.get("xGBuildup", 0),
        "xGChain_90": player_data.get("xGChain_90", 0),
        "xGBuildup_90": player_data.get("xGBuildup_90", 0),

        # Discipline
        "yellow_cards": player_data.get("yellow_cards", 0),
        "red_cards": player_data.get("red_cards", 0),
        "cards_90": player_data.get("cards_90", 0),

        # Impact
        "impact_goals_conceded": player_data.get("impact_goals_conceded", 0),
        "impact_clean_sheets": player_data.get("impact_clean_sheets", 0),
        "impact_wins": player_data.get("impact_wins", 0),

        # Behavioral
        "behavioral_profile": player_data.get("behavioral_profile", ""),
        "tags": player_data.get("tags", []),

        # DNA
        "dna": player_data.get("dna", {}),
    }

    # Quant v8 metrics
    quant_v8 = player_data.get("quant_v8", {})
    if quant_v8:
        profile["quant_v8"] = {
            "clutch": quant_v8.get("clutch", {}),
            "volatility": quant_v8.get("volatility", {}),
            "xCards": quant_v8.get("xCards", 0),
            "matchup_friction": quant_v8.get("matchup_friction", {}),
            "paire_synergy": quant_v8.get("paire_synergy", {}),
        }

    # Quant v9 metrics
    quant_v9 = player_data.get("quant_v9", {})
    if quant_v9:
        profile["quant_v9"] = {
            "stadium": quant_v9.get("stadium", {}),
            "tilt": quant_v9.get("tilt", {}),
            "leadership": quant_v9.get("leadership", {}),
            "alpha_beta": quant_v9.get("alpha_beta", {}),
            "sharpe": quant_v9.get("sharpe", {}),
            "duel_success": quant_v9.get("duel_success", {}),
            "ball_progression": quant_v9.get("ball_progression", {}),
        }

    return profile


def extract_midfielder_profile_from_impact(player_data: dict) -> dict:
    """
    Extrait un profil milieu depuis players_impact_dna (données basiques)
    """
    games = player_data.get("games", 0) or 1
    time_90 = (player_data.get("time", 0) or 0) / 90

    return {
        "source": "players_impact_dna",
        "position": player_data.get("position", ""),
        "games": games,
        "time_90": round(time_90, 1),

        # Offensive metrics
        "goals": player_data.get("goals", 0),
        "assists": player_data.get("assists", 0),
        "xG": player_data.get("xG", 0),
        "xA": player_data.get("xA", 0),
        "xA_90": round(player_data.get("xA", 0) / max(time_90, 1), 3),
        "key_passes": player_data.get("key_passes", 0),
        "xGChain": player_data.get("xGChain", 0),
        "xGBuildup": player_data.get("xGBuildup", 0),
        "xGChain_90": round(player_data.get("xGChain", 0) / max(time_90, 1), 3),
        "xGBuildup_90": round(player_data.get("xGBuildup", 0) / max(time_90, 1), 3),
        "shots": player_data.get("shots", 0),

        # No discipline data from impact
        "yellow_cards": None,
        "red_cards": None,
        "cards_90": None,
    }


# ============================================================================
# GÉNÉRATION DES STRENGTHS/WEAKNESSES
# ============================================================================

def generate_midfielder_traits(profile: dict, percentiles: dict) -> tuple:
    """
    Génère les forces et faiblesses d'un milieu
    """
    strengths = []
    weaknesses = []

    games = profile.get("games", 0)
    time_90 = profile.get("time_90", 0)

    # Skip si pas assez de données
    if games < 3 or time_90 < 2:
        return [], []

    # === OFFENSIVE TRAITS ===

    # Playmaker (key_passes)
    key_passes_90 = profile.get("key_passes", 0) / max(time_90, 1)
    if key_passes_90 > 1.5:
        strengths.append("playmaker")

    # Chain initiator (xGChain_90)
    xgchain_90 = profile.get("xGChain_90", 0)
    if xgchain_90 > 0.4:
        strengths.append("chain_initiator")
    elif xgchain_90 < 0.1:
        weaknesses.append("invisible_buildup")

    # Buildup specialist (xGBuildup_90)
    xgbuildup_90 = profile.get("xGBuildup_90", 0)
    if xgbuildup_90 > 0.3:
        strengths.append("buildup_specialist")

    # Goal threat (xG pour un milieu)
    xg_90 = profile.get("xG", 0) / max(time_90, 1)
    if xg_90 > 0.15:  # Élevé pour un milieu
        strengths.append("goal_threat")

    # Assist machine
    xa_90 = profile.get("xA_90", 0)
    if xa_90 > 0.2:
        strengths.append("assist_machine")
    elif xa_90 < 0.05:
        weaknesses.append("limited_creator")

    # === DISCIPLINE TRAITS (si disponible) ===

    cards_90 = profile.get("cards_90")
    if cards_90 is not None:
        if cards_90 < 0.1:
            strengths.append("disciplined")
        elif cards_90 > 0.35:
            weaknesses.append("card_prone")

    # === QUANT TRAITS (si disponible depuis defender_dna) ===

    quant_v8 = profile.get("quant_v8", {})
    quant_v9 = profile.get("quant_v9", {})

    # Clutch
    clutch = quant_v8.get("clutch", {})
    clutch_factor = clutch.get("clutch_factor", 0) if isinstance(clutch, dict) else 0
    if clutch_factor > 10:
        strengths.append("clutch_performer")

    # Volatility
    volatility = quant_v8.get("volatility", {})
    vol_score = volatility.get("volatility_score", 50) if isinstance(volatility, dict) else 50
    if vol_score < 30:
        strengths.append("consistent")
    elif vol_score > 70:
        weaknesses.append("inconsistent")

    # Leadership
    leadership = quant_v9.get("leadership", {})
    lead_score = leadership.get("leadership_score", 0) if isinstance(leadership, dict) else 0
    if lead_score > 70:
        strengths.append("leader")

    # Tilt
    tilt = quant_v9.get("tilt", {})
    tilt_risk = tilt.get("tilt_risk", 0) if isinstance(tilt, dict) else 0
    if tilt_risk > 60:
        weaknesses.append("tilt_risk")

    # Stadium (home/away)
    stadium = quant_v9.get("stadium", {})
    if isinstance(stadium, dict):
        # home_advantage est un float représentant la différence home vs away
        home_advantage = stadium.get("home_advantage", 0)
        edge_impact = stadium.get("edge_impact", {})
        home_edge = edge_impact.get("home", 0) if isinstance(edge_impact, dict) else 0
        away_edge = edge_impact.get("away", 0) if isinstance(edge_impact, dict) else 0

        if home_advantage > 0.3 or home_edge > 0.1:
            strengths.append("home_specialist")
        if home_advantage < -0.3 or away_edge < -0.1:
            weaknesses.append("away_weakness")

    # Duel success
    duel = quant_v9.get("duel_success", {})
    if isinstance(duel, dict):
        duel_rate = duel.get("success_rate", 50)
        if duel_rate > 60:
            strengths.append("duel_winner")

    return strengths, weaknesses


# ============================================================================
# GÉNÉRATION DU BETTING PROFILE
# ============================================================================

def generate_midfielder_betting_profile(profile: dict, strengths: List[dict], weaknesses: List[dict]) -> dict:
    """
    Génère le betting_profile pour un milieu
    """
    target_markets = []
    avoid_markets = []

    games = profile.get("games", 0)
    time_90 = profile.get("time_90", 0)

    # Confiance basée sur sample size
    base_confidence = "HIGH" if games >= 10 else "MEDIUM" if games >= 5 else "LOW"

    # === TARGET MARKETS ===

    for s in strengths:
        trait_name = s.get("trait") if isinstance(s, dict) else s
        trait_info = s if isinstance(s, dict) else enrich_trait(trait_name, True)

        for market in trait_info.get("markets", []):
            existing = next((t for t in target_markets if t["market"] == market), None)
            if existing:
                existing["reasons"].append(trait_name)
                existing["confidence"] = min(0.95, existing["confidence"] + 0.05)
            else:
                target_markets.append({
                    "market": market,
                    "confidence": calculate_confidence(games, base_confidence),
                    "reasons": [trait_name],
                    "edge_type": trait_info.get("edge_type", "indirect_positive")
                })

    # === AVOID MARKETS ===

    for w in weaknesses:
        trait_name = w.get("trait") if isinstance(w, dict) else w
        trait_info = w if isinstance(w, dict) else enrich_trait(trait_name, False)

        for market in trait_info.get("markets", []):
            existing = next((a for a in avoid_markets if a["market"] == market), None)
            if existing:
                existing["reasons"].append(trait_name)
            else:
                avoid_markets.append({
                    "market": market,
                    "confidence": calculate_confidence(games, base_confidence),
                    "reasons": [trait_name],
                    "edge_type": trait_info.get("edge_type", "indirect_negative")
                })

    # Consolider les raisons
    for t in target_markets:
        t["reason"] = " + ".join(t.pop("reasons"))
    for a in avoid_markets:
        a["reason"] = " + ".join(a.pop("reasons"))

    return {
        "is_target": len(target_markets) > 0,
        "is_avoid": len(avoid_markets) > 0,
        "target_markets": target_markets,
        "avoid_markets": avoid_markets,
        "value_indicators": {
            "xGChain_90": profile.get("xGChain_90", 0),
            "xGBuildup_90": profile.get("xGBuildup_90", 0),
            "xA_90": profile.get("xA_90", 0),
            "key_passes_90": profile.get("key_passes", 0) / max(profile.get("time_90", 1), 1),
            "cards_90": profile.get("cards_90"),
            "games": games,
            "source": profile.get("source", "unknown")
        },
        "generated_at": datetime.now().isoformat()
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("ENRICHISSEMENT DES PROFILS MILIEUX - HEDGE FUND GRADE")
    print("=" * 70)

    # === CHARGEMENT DES DONNÉES ===

    print("\n1. Chargement des sources de données...")

    # Defender DNA (milieux défensifs avec données riches)
    with open(DEFENDER_DNA_FILE, 'r', encoding='utf-8') as f:
        defender_data = json.load(f)

    # Filtrer les milieux
    midfielders_from_def = [p for p in defender_data if 'M' in p.get('position', '').split()]
    print(f"   - defender_dna: {len(midfielders_from_def)} milieux")

    # Index par nom normalisé
    defender_index = {normalize_name(p['name']): p for p in midfielders_from_def}

    # Players impact (tous les joueurs)
    with open(PLAYERS_IMPACT_FILE, 'r', encoding='utf-8') as f:
        impact_data = json.load(f)

    # Filtrer les milieux (positions avec M ou S mais pas F seul)
    midfielders_from_impact = [p for p in impact_data
                               if 'M' in p.get('position', '').split()
                               or p.get('position', '') in ['M S', 'M']]
    print(f"   - players_impact: {len(midfielders_from_impact)} milieux")

    # Index par nom normalisé
    impact_index = {normalize_name(p['player_name']): p for p in midfielders_from_impact}

    # Player DNA unified
    with open(UNIFIED_FILE, 'r', encoding='utf-8') as f:
        unified_data = json.load(f)

    players = unified_data.get('players', {})
    print(f"   - player_dna_unified: {len(players)} joueurs")

    # === CALCUL DES PERCENTILES ===

    print("\n2. Calcul des percentiles de référence...")

    all_xgchain = [p.get('xGChain', 0) for p in midfielders_from_impact if p.get('games', 0) >= 5]
    all_xgbuildup = [p.get('xGBuildup', 0) for p in midfielders_from_impact if p.get('games', 0) >= 5]
    all_xa = [p.get('xA', 0) for p in midfielders_from_impact if p.get('games', 0) >= 5]

    percentiles = {
        'xGChain': sorted(all_xgchain),
        'xGBuildup': sorted(all_xgbuildup),
        'xA': sorted(all_xa)
    }

    # === ENRICHISSEMENT ===

    print("\n3. Enrichissement des profils milieux...")

    stats = {
        'total_midfielders': 0,
        'enriched_from_defender': 0,
        'enriched_from_impact': 0,
        'betting_profiles_generated': 0,
        'is_target': 0,
        'is_avoid': 0,
        'strengths_count': defaultdict(int),
        'weaknesses_count': defaultdict(int),
        'target_markets_count': defaultdict(int),
        'avoid_markets_count': defaultdict(int),
    }

    # Tous les milieux uniques (union des deux sources)
    all_midfielders = set(defender_index.keys()) | set(impact_index.keys())
    stats['total_midfielders'] = len(all_midfielders)

    # Pour chaque milieu, enrichir les données
    for norm_name in all_midfielders:
        # Trouver le joueur dans unified
        # Chercher par nom similaire
        matched_key = None
        for player_key in players.keys():
            if normalize_name(player_key) == norm_name:
                matched_key = player_key
                break

        # Créer l'entrée si elle n'existe pas
        if not matched_key:
            # Récupérer le nom original
            if norm_name in defender_index:
                original_name = defender_index[norm_name]['name']
                team = defender_index[norm_name].get('team', 'Unknown')
                league = defender_index[norm_name].get('league', 'Unknown')
            else:
                original_name = impact_index[norm_name]['player_name']
                team = impact_index[norm_name].get('team', 'Unknown')
                league = impact_index[norm_name].get('league', 'Unknown')

            matched_key = original_name
            players[matched_key] = {
                'meta': {
                    'name': original_name,
                    'team': team,
                    'league': league,
                    'position': 'M'
                }
            }

        player_data = players[matched_key]

        # Extraire le profil milieu
        if norm_name in defender_index:
            # Source riche: defender_dna
            profile = extract_midfielder_profile_from_defender_dna(defender_index[norm_name])
            stats['enriched_from_defender'] += 1
        elif norm_name in impact_index:
            # Source basique: players_impact
            profile = extract_midfielder_profile_from_impact(impact_index[norm_name])
            stats['enriched_from_impact'] += 1
        else:
            continue

        # Générer strengths/weaknesses
        raw_strengths, raw_weaknesses = generate_midfielder_traits(profile, percentiles)

        # Enrichir les traits
        strengths = [enrich_trait(s, True) for s in raw_strengths]
        weaknesses = [enrich_trait(w, False) for w in raw_weaknesses]

        # Comptabiliser
        for s in strengths:
            stats['strengths_count'][s['trait']] += 1
        for w in weaknesses:
            stats['weaknesses_count'][w['trait']] += 1

        # Générer betting profile
        betting_profile = generate_midfielder_betting_profile(profile, strengths, weaknesses)

        # Ajouter au profil milieu
        profile['strengths'] = strengths
        profile['weaknesses'] = weaknesses
        profile['betting_profile'] = betting_profile

        # Ajouter au joueur
        player_data['midfielder'] = profile

        # Stats
        stats['betting_profiles_generated'] += 1
        if betting_profile['is_target']:
            stats['is_target'] += 1
        if betting_profile['is_avoid']:
            stats['is_avoid'] += 1

        for t in betting_profile['target_markets']:
            stats['target_markets_count'][t['market']] += 1
        for a in betting_profile['avoid_markets']:
            stats['avoid_markets_count'][a['market']] += 1

    # === MISE À JOUR METADATA ===

    if 'metadata' not in unified_data:
        unified_data['metadata'] = {}

    unified_data['metadata']['midfielder_profiles'] = {
        'version': '1.0',
        'generated_at': datetime.now().isoformat(),
        'sources': ['defender_dna_quant_v9', 'players_impact_dna'],
        'stats': {
            'total': stats['total_midfielders'],
            'from_defender_dna': stats['enriched_from_defender'],
            'from_players_impact': stats['enriched_from_impact'],
            'with_betting_profile': stats['betting_profiles_generated'],
            'is_target': stats['is_target'],
            'is_avoid': stats['is_avoid']
        }
    }

    # === SAUVEGARDE ===

    print("\n4. Sauvegarde...")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(unified_data, f, indent=2, ensure_ascii=False)

    # === RAPPORT FINAL ===

    print("\n" + "=" * 70)
    print("RAPPORT FINAL")
    print("=" * 70)

    print(f"\nMILIEUX ANALYSÉS: {stats['total_midfielders']}")
    print(f"   - Depuis defender_dna (données riches): {stats['enriched_from_defender']}")
    print(f"   - Depuis players_impact (données basiques): {stats['enriched_from_impact']}")

    print(f"\nBETTING PROFILES: {stats['betting_profiles_generated']}")
    print(f"   - TARGET (opportunités): {stats['is_target']} ({100*stats['is_target']/max(stats['betting_profiles_generated'],1):.1f}%)")
    print(f"   - AVOID (à éviter): {stats['is_avoid']} ({100*stats['is_avoid']/max(stats['betting_profiles_generated'],1):.1f}%)")

    print(f"\nFORCES DÉTECTÉES:")
    for trait, count in sorted(stats['strengths_count'].items(), key=lambda x: -x[1])[:10]:
        print(f"   - {trait}: {count}")

    print(f"\nFAIBLESSES DÉTECTÉES:")
    for trait, count in sorted(stats['weaknesses_count'].items(), key=lambda x: -x[1])[:10]:
        print(f"   - {trait}: {count}")

    print(f"\nTARGET MARKETS:")
    for market, count in sorted(stats['target_markets_count'].items(), key=lambda x: -x[1])[:10]:
        print(f"   - {market}: {count}")

    print(f"\nAVOID MARKETS:")
    for market, count in sorted(stats['avoid_markets_count'].items(), key=lambda x: -x[1])[:10]:
        print(f"   - {market}: {count}")

    print("\n" + "=" * 70)
    print("ENRICHISSEMENT TERMINÉ")
    print("=" * 70)

    return stats


if __name__ == '__main__':
    main()
