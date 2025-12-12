#!/usr/bin/env python3
"""
Génération des betting_profiles pour les attaquants
Fusion de attacking (attacker_dna_v2) + style (attacker_styles_v1)
→ player_dna_unified.json
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

def calculate_confidence(
    tier: str,
    sample_games: int,
    has_style: bool,
    xG_diff: float = 0,
    conversion: float = 1.0
) -> float:
    """
    Calcule un score de confiance 0-1 basé sur plusieurs facteurs
    """
    # Base par tier
    tier_base = {
        "ELITE": 0.9,
        "DANGEROUS": 0.75,
        "THREAT": 0.6,
        "AVERAGE": 0.45,
        "LOW": 0.3
    }
    base = tier_base.get(tier, 0.4)

    # Ajustement sample size (games)
    if sample_games >= 15:
        sample_factor = 1.0
    elif sample_games >= 10:
        sample_factor = 0.9
    elif sample_games >= 7:
        sample_factor = 0.8
    elif sample_games >= 5:
        sample_factor = 0.7
    else:
        sample_factor = 0.5

    # Bonus si style disponible
    style_bonus = 1.05 if has_style else 1.0

    # Bonus surperformance xG
    xG_bonus = 1.0
    if xG_diff > 3:
        xG_bonus = 1.15
    elif xG_diff > 1:
        xG_bonus = 1.1
    elif xG_diff > 0:
        xG_bonus = 1.05
    elif xG_diff < -2:
        xG_bonus = 0.85

    # Bonus conversion
    conv_bonus = 1.0
    if conversion > 1.3:
        conv_bonus = 1.1
    elif conversion > 1.1:
        conv_bonus = 1.05
    elif conversion < 0.7:
        conv_bonus = 0.9

    confidence = base * sample_factor * style_bonus * xG_bonus * conv_bonus
    return round(min(0.95, max(0.1, confidence)), 2)


def get_style_from_data(style_data: Dict) -> Optional[str]:
    """Extrait le style principal"""
    if not style_data or not isinstance(style_data, dict):
        return None
    return style_data.get('primary_style')


def get_secondary_styles(style_data: Dict) -> List[str]:
    """Extrait les styles secondaires"""
    if not style_data or not isinstance(style_data, dict):
        return []
    return style_data.get('secondary_styles', [])


def get_metrics(style_data: Dict) -> Dict:
    """Extrait les métriques de style"""
    if not style_data or not isinstance(style_data, dict):
        return {}
    return style_data.get('metrics', {})


# ============================================================================
# LOGIQUE DE GÉNÉRATION DES BETTING PROFILES
# ============================================================================

def generate_attacker_betting_profile(
    attacking: Dict,
    style: Dict,
    player_name: str
) -> Dict[str, Any]:
    """
    Génère le betting_profile complet pour un attaquant
    """
    target_markets = []
    avoid_markets = []

    # ========================================================================
    # EXTRACTION DES DONNÉES
    # ========================================================================

    # Attacking data
    tier = attacking.get('tier', 'LOW')
    goals = attacking.get('goals', 0)
    xG = attacking.get('xG', 0)
    xG_diff = attacking.get('xG_diff', 0)
    xG_per_90 = attacking.get('xG_per_90', 0)
    xA_per_90 = attacking.get('xA_per_90', 0)
    threat_score = attacking.get('threat_score', 0)
    titularity_factor = attacking.get('titularity_factor', 0)
    games = attacking.get('games', 0)
    minutes = attacking.get('minutes', 0)

    # Style data
    primary_style = get_style_from_data(style)
    secondary_styles = get_secondary_styles(style)
    all_styles = [primary_style] + secondary_styles if primary_style else []
    metrics = get_metrics(style)

    conversion = metrics.get('conversion', goals / xG if xG > 0 else 1.0)
    shots_90 = metrics.get('shots_90', 0)
    kp_90 = metrics.get('kp_90', 0)  # key passes per 90

    # Home/Away ratios
    home_goal_ratio = style.get('home_goal_ratio', 0.5) if style else 0.5
    home_xG_ratio = style.get('home_xG_ratio', 0.5) if style else 0.5

    has_style = primary_style is not None and primary_style != 'BALANCED'

    # ========================================================================
    # 1. TARGET: ANYTIME_SCORER
    # ========================================================================
    # Conditions: tier in ["ELITE", "DANGEROUS", "THREAT"]
    #            AND xG_diff >= 0 (surperformance)
    #            AND style in ["CLINICAL", "POACHER"]

    if tier in ['ELITE', 'DANGEROUS', 'THREAT']:
        reasons = [f"tier={tier}"]
        confidence_boost = 0

        # Vérifier surperformance
        if xG_diff >= 0:
            reasons.append(f"xG_diff=+{xG_diff:.2f}")
            confidence_boost += 0.05

        # Vérifier style
        clinical_poacher = any(s in all_styles for s in ['CLINICAL', 'POACHER'])
        if clinical_poacher:
            matching_styles = [s for s in ['CLINICAL', 'POACHER'] if s in all_styles]
            reasons.append(f"style={'+'.join(matching_styles)}")
            confidence_boost += 0.05

        # Calcul confiance
        conf = calculate_confidence(tier, games, has_style, xG_diff, conversion)
        conf = min(0.95, conf + confidence_boost)

        # Ajouter si conditions minimales remplies
        if xG_diff >= -0.5 or clinical_poacher or tier in ['ELITE', 'DANGEROUS']:
            target_markets.append({
                "market": "anytime_scorer",
                "confidence": round(conf, 2),
                "reason": " + ".join(reasons)
            })

    # ========================================================================
    # 2. TARGET: FIRST_SCORER
    # ========================================================================
    # Conditions: tier in ["ELITE", "DANGEROUS"]
    #            AND titularity_factor > 0.8
    #            AND conversion > 1.0

    if tier in ['ELITE', 'DANGEROUS'] and titularity_factor > 0.8:
        reasons = [f"tier={tier}", f"titularity={titularity_factor:.2f}"]

        if conversion > 1.0:
            reasons.append(f"conversion={conversion:.2f}")

        conf = calculate_confidence(tier, games, has_style, xG_diff, conversion)

        # Bonus pour conversion élevée
        if conversion > 1.2:
            conf = min(0.95, conf + 0.1)
        elif conversion > 1.0:
            conf = min(0.95, conf + 0.05)

        if conversion > 0.9:  # Même si < 1.0, si tier ELITE/DANGEROUS
            target_markets.append({
                "market": "first_scorer",
                "confidence": round(conf, 2),
                "reason": " + ".join(reasons)
            })

    # ========================================================================
    # 3. TARGET: 2+_GOALS
    # ========================================================================
    # Conditions: tier == "ELITE"
    #            AND threat_score > 1.0

    if tier == 'ELITE' and threat_score > 1.0:
        reasons = [f"tier=ELITE", f"threat_score={threat_score:.2f}"]

        if xG_per_90 > 0.8:
            reasons.append(f"xG_90={xG_per_90:.2f}")

        conf = calculate_confidence(tier, games, has_style, xG_diff, conversion)
        conf = min(0.95, conf + 0.1)  # Boost pour ce marché rare

        target_markets.append({
            "market": "2+_goals",
            "confidence": round(conf, 2),
            "reason": " + ".join(reasons)
        })

    # ========================================================================
    # 4. TARGET: ASSIST
    # ========================================================================
    # Conditions: style == "PLAYMAKER"
    #            AND xA_90 > 0.25

    if primary_style == 'PLAYMAKER' or 'PLAYMAKER' in secondary_styles:
        if xA_per_90 > 0.25:
            reasons = [f"style=PLAYMAKER", f"xA_90={xA_per_90:.2f}"]

            if kp_90 > 2:
                reasons.append(f"key_passes_90={kp_90:.1f}")

            conf = calculate_confidence(tier, games, True, 0, 1.0)
            conf = min(0.85, conf)  # Cap pour assists (plus incertains)

            target_markets.append({
                "market": "assist",
                "confidence": round(conf, 2),
                "reason": " + ".join(reasons)
            })
        elif xA_per_90 > 0.2 and kp_90 > 2.5:
            # Condition alternative: bon créateur même si xA légèrement bas
            reasons = [f"style=PLAYMAKER", f"xA_90={xA_per_90:.2f}", f"key_passes_90={kp_90:.1f}"]
            conf = calculate_confidence(tier, games, True, 0, 1.0) * 0.85

            target_markets.append({
                "market": "assist",
                "confidence": round(conf, 2),
                "reason": " + ".join(reasons)
            })

    # ========================================================================
    # 5. AVOID: ANYTIME_SCORER
    # ========================================================================
    # Conditions: tier == "LOW"
    #            AND xG_diff < -0.5 (sous-performance)

    avoid_reasons = []

    if tier == 'LOW':
        avoid_reasons.append(f"tier=LOW")

    if xG_diff < -0.5:
        avoid_reasons.append(f"xG_diff={xG_diff:.2f}")

    if conversion < 0.7 and goals >= 1:
        avoid_reasons.append(f"conversion={conversion:.2f}")

    if len(avoid_reasons) >= 2 or (tier == 'LOW' and xG_diff < -1):
        conf = 0.7 if tier == 'LOW' else 0.5
        if xG_diff < -2:
            conf += 0.1

        avoid_markets.append({
            "market": "anytime_scorer",
            "confidence": round(min(0.9, conf), 2),
            "reason": " + ".join(avoid_reasons)
        })

    # ========================================================================
    # 6. HOME_SCORER / AWAY_SCORER
    # ========================================================================
    # home_goal_ratio > 0.6 → target "home_scorer"
    # home_goal_ratio < 0.4 → avoid "home_scorer"

    if goals >= 3:  # Besoin d'un minimum de buts pour que le ratio soit significatif
        if home_goal_ratio > 0.65:
            reasons = [f"home_goal_ratio={home_goal_ratio:.2f}"]
            if home_xG_ratio > 0.55:
                reasons.append(f"home_xG_ratio={home_xG_ratio:.2f}")

            conf = calculate_confidence(tier, games, has_style, xG_diff, conversion)
            conf = min(0.8, conf * 0.9)  # Réduction car venue-specific

            target_markets.append({
                "market": "home_scorer",
                "confidence": round(conf, 2),
                "reason": " + ".join(reasons)
            })

        elif home_goal_ratio < 0.35:
            # Éviter de parier sur ce joueur à domicile
            avoid_markets.append({
                "market": "home_scorer",
                "confidence": round(0.6, 2),
                "reason": f"home_goal_ratio={home_goal_ratio:.2f} (préfère extérieur)"
            })

            # Mais peut être target pour away_scorer
            if tier in ['ELITE', 'DANGEROUS', 'THREAT']:
                target_markets.append({
                    "market": "away_scorer",
                    "confidence": round(0.6, 2),
                    "reason": f"away_preference (home_ratio={home_goal_ratio:.2f})"
                })

    # ========================================================================
    # 7. SHOTS_ON_TARGET (bonus pour VOLUME_SHOOTER)
    # ========================================================================
    if primary_style == 'VOLUME_SHOOTER' or 'VOLUME_SHOOTER' in secondary_styles:
        if shots_90 > 3:
            reasons = [f"style=VOLUME_SHOOTER", f"shots_90={shots_90:.1f}"]
            conf = calculate_confidence(tier, games, True, 0, 1.0)
            conf = min(0.75, conf * 0.9)

            target_markets.append({
                "market": "shots_on_target",
                "confidence": round(conf, 2),
                "reason": " + ".join(reasons)
            })

    # ========================================================================
    # 8. LONGSHOT_GOAL (pour LONGSHOT_SPECIALIST)
    # ========================================================================
    style_scores = style.get('style_scores', {}) if style else {}
    if style_scores.get('LONGSHOT_SPECIALIST', 0) > 0.5:
        reasons = [f"LONGSHOT_SPECIALIST score={style_scores['LONGSHOT_SPECIALIST']:.1f}"]
        conf = 0.4  # Marché très spécifique, confiance basse

        target_markets.append({
            "market": "goal_from_outside_box",
            "confidence": round(conf, 2),
            "reason": " + ".join(reasons)
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
            "tier": tier,
            "style": primary_style,
            "secondary_styles": secondary_styles,
            "xG_diff": round(xG_diff, 2),
            "conversion": round(conversion, 2) if conversion else None,
            "threat_score": round(threat_score, 2),
            "goals": goals,
            "xG_per_90": round(xG_per_90, 3),
            "xA_per_90": round(xA_per_90, 3),
            "titularity_factor": titularity_factor,
            "home_goal_ratio": round(home_goal_ratio, 2) if home_goal_ratio != 0.5 else None
        },
        "generated_at": datetime.now().isoformat()
    }

    # Nettoyer les None
    betting_profile["value_indicators"] = {
        k: v for k, v in betting_profile["value_indicators"].items()
        if v is not None
    }

    return betting_profile


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("GÉNÉRATION DES BETTING PROFILES - ATTAQUANTS")
    print("=" * 70)

    # Charger les données
    print("\n📂 Chargement de player_dna_unified.json...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    players = data['players']

    # Statistiques
    stats = {
        'total_attackers': 0,
        'with_attacking': 0,
        'with_style': 0,
        'with_both': 0,
        'profiles_generated': 0,
        'is_target': 0,
        'is_avoid': 0,
        'both_target_avoid': 0,
        'neutral': 0,
        'by_tier': defaultdict(lambda: {'total': 0, 'target': 0, 'avoid': 0}),
        'target_markets': defaultdict(int),
        'avoid_markets': defaultdict(int),
        'examples': defaultdict(list)
    }

    # Générer les betting_profiles
    print("\n🔄 Génération des betting_profiles...")

    for player_name, player_data in players.items():
        attacking = player_data.get('attacking')
        style = player_data.get('style')

        # Compter les données disponibles
        has_attacking = attacking and isinstance(attacking, dict) and attacking.get('tier')
        has_style = style and isinstance(style, dict) and style.get('primary_style')

        if has_attacking:
            stats['with_attacking'] += 1
        if has_style:
            stats['with_style'] += 1
        if has_attacking and has_style:
            stats['with_both'] += 1

        # Ne traiter que les joueurs avec données attacking
        if not has_attacking:
            continue

        stats['total_attackers'] += 1
        tier = attacking.get('tier', 'LOW')

        # Générer le betting_profile
        betting_profile = generate_attacker_betting_profile(
            attacking,
            style if has_style else {},
            player_name
        )

        # Ajouter au joueur
        if 'attacking' not in player_data:
            player_data['attacking'] = {}
        player_data['attacking']['betting_profile'] = betting_profile

        stats['profiles_generated'] += 1

        # Comptabiliser
        stats['by_tier'][tier]['total'] += 1

        if betting_profile['is_target']:
            stats['is_target'] += 1
            stats['by_tier'][tier]['target'] += 1
        if betting_profile['is_avoid']:
            stats['is_avoid'] += 1
            stats['by_tier'][tier]['avoid'] += 1
        if betting_profile['is_target'] and betting_profile['is_avoid']:
            stats['both_target_avoid'] += 1
        if not betting_profile['is_target'] and not betting_profile['is_avoid']:
            stats['neutral'] += 1

        for tm in betting_profile['target_markets']:
            stats['target_markets'][tm['market']] += 1

        for am in betting_profile['avoid_markets']:
            stats['avoid_markets'][am['market']] += 1

        # Garder des exemples par tier
        if len(stats['examples'][tier]) < 3 and betting_profile['is_target']:
            stats['examples'][tier].append({
                'name': player_name,
                'team': player_data['meta'].get('team', 'Unknown'),
                'targets': [m['market'] for m in betting_profile['target_markets']]
            })

    # Mettre à jour les metadata
    data['metadata']['betting_profiles']['attacker_stats'] = {
        'version': '1.0',
        'generated_at': datetime.now().isoformat(),
        'total': stats['total_attackers'],
        'with_profile': stats['profiles_generated'],
        'is_target': stats['is_target'],
        'is_avoid': stats['is_avoid'],
        'both': stats['both_target_avoid'],
        'neutral': stats['neutral'],
        'by_tier': dict(stats['by_tier'])
    }

    # Sauvegarder
    print("\n💾 Sauvegarde dans player_dna_unified.json...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Afficher les statistiques
    print("\n" + "=" * 70)
    print("📊 STATISTIQUES FINALES")
    print("=" * 70)

    print(f"\n⚽ ATTAQUANTS ANALYSÉS: {stats['total_attackers']}")
    print(f"   ├── Avec attacking data: {stats['with_attacking']}")
    print(f"   ├── Avec style data: {stats['with_style']}")
    print(f"   ├── Avec les deux: {stats['with_both']}")
    print(f"   ├── Profiles générés: {stats['profiles_generated']}")
    print(f"   ├── TARGET (opportunités): {stats['is_target']} ({stats['is_target']/stats['total_attackers']*100:.1f}%)")
    print(f"   ├── AVOID (à éviter): {stats['is_avoid']} ({stats['is_avoid']/stats['total_attackers']*100:.1f}%)")
    print(f"   ├── TARGET + AVOID: {stats['both_target_avoid']}")
    print(f"   └── NEUTRAL: {stats['neutral']}")

    print(f"\n📈 DISTRIBUTION PAR TIER:")
    for tier in ['ELITE', 'DANGEROUS', 'THREAT', 'AVERAGE', 'LOW']:
        t = stats['by_tier'].get(tier, {'total': 0, 'target': 0, 'avoid': 0})
        pct_target = t['target']/t['total']*100 if t['total'] > 0 else 0
        pct_avoid = t['avoid']/t['total']*100 if t['total'] > 0 else 0
        print(f"   {tier:10} │ Total: {t['total']:4} │ Target: {t['target']:3} ({pct_target:5.1f}%) │ Avoid: {t['avoid']:3} ({pct_avoid:5.1f}%)")

    print(f"\n🎯 TARGET MARKETS:")
    for market, count in sorted(stats['target_markets'].items(), key=lambda x: -x[1]):
        print(f"   ├── {market}: {count} joueurs")

    print(f"\n⛔ AVOID MARKETS:")
    for market, count in sorted(stats['avoid_markets'].items(), key=lambda x: -x[1]):
        print(f"   ├── {market}: {count} joueurs")

    print(f"\n📝 EXEMPLES PAR TIER:")
    for tier in ['ELITE', 'DANGEROUS', 'THREAT']:
        print(f"\n   {tier}:")
        for ex in stats['examples'].get(tier, []):
            print(f"      • {ex['name'].title()} ({ex['team']})")
            print(f"        Markets: {ex['targets']}")

    print("\n" + "=" * 70)
    print("✅ GÉNÉRATION TERMINÉE")
    print("=" * 70)

    return stats


if __name__ == '__main__':
    main()
