#!/usr/bin/env python3
"""
Génération des betting_profiles pour les gardiens
À partir de goalkeeper_dna_v4_4_final.json → player_dna_unified.json
"""

import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Chemins des fichiers
INPUT_FILE = '/home/Mon_ps/data/quantum_v2/player_dna_unified.json'
OUTPUT_FILE = '/home/Mon_ps/data/quantum_v2/player_dna_unified.json'

# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

def calculate_confidence(sample_size: int, base_confidence: str = "MEDIUM") -> float:
    """
    Calcule un score de confiance 0-1 basé sur sample_size et confidence level
    """
    confidence_map = {
        "VERY_LOW": 0.2,
        "LOW": 0.4,
        "MEDIUM": 0.6,
        "HIGH": 0.8
    }
    base = confidence_map.get(base_confidence, 0.5)

    # Ajustement selon sample_size
    if sample_size >= 30:
        sample_factor = 1.0
    elif sample_size >= 15:
        sample_factor = 0.85
    elif sample_size >= 10:
        sample_factor = 0.7
    elif sample_size >= 5:
        sample_factor = 0.55
    else:
        sample_factor = 0.4

    return round(min(0.95, base * sample_factor), 2)


def check_weakness_keywords(weaknesses: List[str], keywords: List[str]) -> bool:
    """Vérifie si des mots-clés sont présents dans les faiblesses"""
    weakness_text = " ".join(weaknesses).lower()
    return any(kw.lower() in weakness_text for kw in keywords)


def get_total_samples(gk_data: Dict) -> int:
    """Calcule le nombre total de tirs affrontés"""
    return gk_data.get('shots_faced', 0)


# ============================================================================
# LOGIQUE DE GÉNÉRATION DES BETTING PROFILES
# ============================================================================

def generate_betting_profile(gk_data: Dict) -> Dict[str, Any]:
    """
    Génère le betting_profile complet pour un gardien
    """
    target_markets = []
    avoid_markets = []

    # Extraction des données clés
    percentile = gk_data.get('percentile', 50)
    save_rate = gk_data.get('save_rate', 70)
    shots_faced = gk_data.get('shots_faced', 0)

    difficulty = gk_data.get('difficulty_analysis', {})
    routine_reliability = difficulty.get('routine_reliability', 'AVERAGE')
    big_save_ability = difficulty.get('big_save_ability', 'AVERAGE')

    situation = gk_data.get('situation_analysis', {})
    corners_data = situation.get('corners', {})
    corners_sr = corners_data.get('sr', 65)
    corners_sample = corners_data.get('sample', 0)
    corners_confidence = corners_data.get('confidence', 'LOW')

    timing = gk_data.get('timing_analysis', {})
    first_half_sr = timing.get('first_half_sr', 70)
    second_half_sr = timing.get('second_half_sr', 70)
    clutch_factor = timing.get('clutch_factor', 0)
    pattern = timing.get('pattern', 'CONSISTENT')
    weakest_period = timing.get('weakest_period', '')
    strongest_period = timing.get('strongest_period', '')
    periods = timing.get('periods', {})

    shot_types = gk_data.get('shot_type_analysis', {})
    head_data = shot_types.get('Head', {})
    head_sr = head_data.get('sr', 60)
    head_sample = head_data.get('sample', 0)

    weaknesses = gk_data.get('weaknesses', [])
    strengths = gk_data.get('strengths', [])

    # ========================================================================
    # 1. TARGET: CLEAN_SHEET
    # ========================================================================
    # Conditions: routine_reliability in ["STRONG", "VERY_STRONG"]
    #            AND gk_percentile > 60
    #            AND big_save_ability != "WEAK"

    if (routine_reliability in ['STRONG', 'VERY_STRONG']
        and percentile > 60
        and big_save_ability != 'WEAK'):

        reasons = []
        if routine_reliability == 'VERY_STRONG':
            reasons.append(f"routine_reliability={routine_reliability}")
        else:
            reasons.append(f"routine_reliability={routine_reliability}")
        reasons.append(f"gk_percentile={percentile:.0f}")
        if big_save_ability == 'STRONG':
            reasons.append(f"big_save_ability={big_save_ability}")

        # Confidence basée sur sample_size et percentile
        easy_sample = difficulty.get('easy', {}).get('sample', 0)
        conf = calculate_confidence(easy_sample, 'HIGH' if percentile > 75 else 'MEDIUM')

        target_markets.append({
            "market": "clean_sheet",
            "confidence": conf,
            "reason": " + ".join(reasons)
        })

    # ========================================================================
    # 2. AVOID: CLEAN_SHEET
    # ========================================================================
    # Conditions: corners.sr < 65%
    #            OR weaknesses contient "headers" ou "corners"
    #            OR routine_reliability == "WEAK"

    avoid_cs_reasons = []

    if corners_sr < 65 and corners_sample >= 3:
        avoid_cs_reasons.append(f"weak_vs_corners={corners_sr:.1f}%")

    if check_weakness_keywords(weaknesses, ['header', 'headers', 'tête', 'têtes', 'airs']):
        avoid_cs_reasons.append("weak_vs_headers")

    if check_weakness_keywords(weaknesses, ['corner', 'corners']):
        avoid_cs_reasons.append("weak_vs_corners_situational")

    if routine_reliability == 'WEAK':
        avoid_cs_reasons.append(f"routine_reliability={routine_reliability}")

    if big_save_ability == 'WEAK':
        avoid_cs_reasons.append(f"big_save_ability={big_save_ability}")

    if avoid_cs_reasons:
        conf = calculate_confidence(shots_faced, corners_confidence if corners_sample >= 5 else 'LOW')
        avoid_markets.append({
            "market": "clean_sheet",
            "confidence": conf,
            "reason": " + ".join(avoid_cs_reasons)
        })

    # ========================================================================
    # 3. TARGET: BTTS_NO (Both Teams To Score = No)
    # ========================================================================
    # Conditions: first_half_sr > 75% ET second_half_sr > 75%

    if first_half_sr > 75 and second_half_sr > 75:
        conf = calculate_confidence(shots_faced, 'HIGH' if pattern == 'CONSISTENT' else 'MEDIUM')
        target_markets.append({
            "market": "btts_no",
            "confidence": conf,
            "reason": f"first_half_sr={first_half_sr:.1f}% + second_half_sr={second_half_sr:.1f}% + pattern={pattern}"
        })

    # ========================================================================
    # 4. AVOID: FIRST_HALF_CLEAN_SHEET
    # ========================================================================
    # Conditions: weakest_period in ["0-15", "16-30", "31-45"]

    early_weak_periods = ['0-15', '16-30', '31-45']
    if weakest_period in early_weak_periods:
        period_data = periods.get(weakest_period, {})
        period_sr = period_data.get('save_rate', 70)
        period_sample = period_data.get('sample', 0)
        period_conf = period_data.get('confidence', 'LOW')

        if period_sample >= 3:
            conf = calculate_confidence(period_sample, period_conf)
            avoid_markets.append({
                "market": "first_half_clean_sheet",
                "confidence": conf,
                "reason": f"weakest_period={weakest_period} (sr={period_sr:.1f}%)"
            })

    # ========================================================================
    # 5. TARGET: FIRST_HALF_CLEAN_SHEET (si très fort en 1ère mi-temps)
    # ========================================================================
    if first_half_sr > 80 and weakest_period not in early_weak_periods:
        conf = calculate_confidence(shots_faced // 2, 'MEDIUM')
        target_markets.append({
            "market": "first_half_clean_sheet",
            "confidence": conf,
            "reason": f"first_half_sr={first_half_sr:.1f}% + weakest_period={weakest_period}"
        })

    # ========================================================================
    # 6. AVOID: SECOND_HALF_CLEAN_SHEET
    # ========================================================================
    late_weak_periods = ['46-60', '61-75', '76-90']
    if weakest_period in late_weak_periods:
        period_data = periods.get(weakest_period, {})
        period_sr = period_data.get('save_rate', 70)
        period_sample = period_data.get('sample', 0)
        period_conf = period_data.get('confidence', 'LOW')

        if period_sample >= 3:
            conf = calculate_confidence(period_sample, period_conf)
            avoid_markets.append({
                "market": "second_half_clean_sheet",
                "confidence": conf,
                "reason": f"weakest_period={weakest_period} (sr={period_sr:.1f}%)"
            })

    # ========================================================================
    # 7. TARGET: HEADER_GOAL_AGAINST (si faible sur les têtes)
    # ========================================================================
    if head_sr < 50 and head_sample >= 5:
        conf = calculate_confidence(head_sample, head_data.get('confidence', 'MEDIUM'))
        target_markets.append({
            "market": "header_goal_against",
            "confidence": conf,
            "reason": f"head_sr={head_sr:.1f}% (sample={head_sample})"
        })

    # ========================================================================
    # 8. TARGET: CORNER_GOAL_AGAINST (si faible sur corners)
    # ========================================================================
    if corners_sr < 50 and corners_sample >= 4:
        conf = calculate_confidence(corners_sample, corners_confidence)
        target_markets.append({
            "market": "corner_goal_against",
            "confidence": conf,
            "reason": f"corners_sr={corners_sr:.1f}% (sample={corners_sample})"
        })

    # ========================================================================
    # 9. TARGET: LATE_GOAL_AGAINST (si clutch_factor très négatif)
    # ========================================================================
    if clutch_factor < -15:
        late_period = periods.get('76-90', {})
        late_sr = late_period.get('save_rate', 70)
        late_sample = late_period.get('sample', 0)

        if late_sample >= 5:
            conf = calculate_confidence(late_sample, late_period.get('confidence', 'MEDIUM'))
            target_markets.append({
                "market": "late_goal_against",
                "confidence": conf,
                "reason": f"clutch_factor={clutch_factor:.1f} + 76-90_sr={late_sr:.1f}%"
            })

    # ========================================================================
    # 10. TARGET: PENALTY_SAVE (si spécialiste penalties)
    # ========================================================================
    penalties_data = situation.get('penalties', {})
    pen_sr = penalties_data.get('sr', 0)
    pen_sample = penalties_data.get('sample', 0)

    if pen_sr > 30 and pen_sample >= 3:  # >30% est excellent pour penalties
        conf = calculate_confidence(pen_sample, penalties_data.get('confidence', 'LOW'))
        target_markets.append({
            "market": "penalty_save",
            "confidence": conf,
            "reason": f"penalty_sr={pen_sr:.1f}% (sample={pen_sample})"
        })

    # ========================================================================
    # CONSTRUCTION DU PROFIL FINAL
    # ========================================================================

    is_target = len(target_markets) > 0
    is_avoid = len(avoid_markets) > 0

    betting_profile = {
        "is_target": is_target,
        "is_avoid": is_avoid,
        "target_markets": target_markets,
        "avoid_markets": avoid_markets,
        "value_indicators": {
            "clutch_factor": clutch_factor,
            "consistency": pattern,
            "big_save_ability": big_save_ability,
            "routine_reliability": routine_reliability,
            "percentile": percentile,
            "save_rate": save_rate
        },
        "generated_at": datetime.now().isoformat()
    }

    return betting_profile


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("GÉNÉRATION DES BETTING PROFILES - GARDIENS")
    print("=" * 70)

    # Charger les données
    print("\n📂 Chargement de player_dna_unified.json...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    players = data['players']

    # Statistiques
    stats = {
        'total_gk': 0,
        'profiles_generated': 0,
        'is_target': 0,
        'is_avoid': 0,
        'both_target_avoid': 0,
        'neutral': 0,
        'target_markets': defaultdict(int),
        'avoid_markets': defaultdict(int),
        'examples': []
    }

    # Générer les betting_profiles pour chaque gardien
    print("\n🔄 Génération des betting_profiles...")

    for player_name, player_data in players.items():
        # Vérifier si c'est un gardien avec données
        if 'goalkeeper' not in player_data:
            continue

        gk_data = player_data.get('goalkeeper')

        # Vérifier que gk_data existe et contient des données exploitables
        if not gk_data or not isinstance(gk_data, dict):
            continue

        if not gk_data.get('percentile') and not gk_data.get('save_rate'):
            continue

        stats['total_gk'] += 1

        # Générer le betting_profile
        betting_profile = generate_betting_profile(gk_data)

        # Ajouter au joueur
        player_data['goalkeeper']['betting_profile'] = betting_profile

        stats['profiles_generated'] += 1

        # Comptabiliser
        if betting_profile['is_target']:
            stats['is_target'] += 1
        if betting_profile['is_avoid']:
            stats['is_avoid'] += 1
        if betting_profile['is_target'] and betting_profile['is_avoid']:
            stats['both_target_avoid'] += 1
        if not betting_profile['is_target'] and not betting_profile['is_avoid']:
            stats['neutral'] += 1

        for tm in betting_profile['target_markets']:
            stats['target_markets'][tm['market']] += 1

        for am in betting_profile['avoid_markets']:
            stats['avoid_markets'][am['market']] += 1

        # Garder quelques exemples
        if len(stats['examples']) < 5 and (betting_profile['is_target'] or betting_profile['is_avoid']):
            stats['examples'].append({
                'name': player_name,
                'team': player_data['meta'].get('team', 'Unknown'),
                'profile': betting_profile
            })

    # Mettre à jour les metadata
    data['metadata']['betting_profiles'] = {
        'version': '1.0',
        'generated_at': datetime.now().isoformat(),
        'goalkeeper_stats': {
            'total': stats['total_gk'],
            'with_profile': stats['profiles_generated'],
            'is_target': stats['is_target'],
            'is_avoid': stats['is_avoid'],
            'both': stats['both_target_avoid'],
            'neutral': stats['neutral']
        }
    }

    # Sauvegarder
    print("\n💾 Sauvegarde dans player_dna_unified.json...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Afficher les statistiques
    print("\n" + "=" * 70)
    print("📊 STATISTIQUES FINALES")
    print("=" * 70)

    print(f"\n🧤 GARDIENS ANALYSÉS: {stats['total_gk']}")
    print(f"   ├── Profiles générés: {stats['profiles_generated']}")
    print(f"   ├── TARGET (opportunités): {stats['is_target']} ({stats['is_target']/stats['total_gk']*100:.1f}%)")
    print(f"   ├── AVOID (à éviter): {stats['is_avoid']} ({stats['is_avoid']/stats['total_gk']*100:.1f}%)")
    print(f"   ├── TARGET + AVOID: {stats['both_target_avoid']}")
    print(f"   └── NEUTRAL: {stats['neutral']}")

    print(f"\n🎯 TARGET MARKETS (opportunités):")
    for market, count in sorted(stats['target_markets'].items(), key=lambda x: -x[1]):
        print(f"   ├── {market}: {count} gardiens")

    print(f"\n⛔ AVOID MARKETS (à éviter):")
    for market, count in sorted(stats['avoid_markets'].items(), key=lambda x: -x[1]):
        print(f"   ├── {market}: {count} gardiens")

    print(f"\n📝 EXEMPLES DE PROFILS GÉNÉRÉS:")
    for ex in stats['examples'][:3]:
        print(f"\n   {ex['name']} ({ex['team']}):")
        if ex['profile']['target_markets']:
            print(f"   🎯 Target: {[m['market'] for m in ex['profile']['target_markets']]}")
        if ex['profile']['avoid_markets']:
            print(f"   ⛔ Avoid: {[m['market'] for m in ex['profile']['avoid_markets']]}")

    print("\n" + "=" * 70)
    print("✅ GÉNÉRATION TERMINÉE")
    print("=" * 70)

    return stats


if __name__ == '__main__':
    main()
