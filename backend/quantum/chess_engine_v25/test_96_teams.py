"""
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║                    TEST 96 ÉQUIPES - CHESS ENGINE V2.5                                   ║
║                    Classification des profils tactiques                                  ║
╠══════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                          ║
║  Ce script:                                                                              ║
║  1. Charge les 96 équipes depuis fbref_tactical_profiles.json                           ║
║  2. Transforme les métriques FBref → 24 features du classifier                          ║
║  3. Classifie chaque équipe avec AdaptiveProfileClassifier                              ║
║  4. Affiche et sauvegarde les résultats                                                 ║
║                                                                                          ║
║  Auteur: Mya & Claude | Date: 12 Décembre 2025                                          ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

# Ajouter le chemin pour les imports
sys.path.insert(0, str(Path(__file__).parent))

from learning import AdaptiveProfileClassifier, TacticalProfile


# ═══════════════════════════════════════════════════════════════════════════════
# TRANSFORMATION DES DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

def transform_fbref_to_features(team_data: dict) -> dict:
    """
    Transformer les données FBref vers les 24 features du classifier

    Mapping:
    - possession → possession_pct
    - ppda → estimé depuis tackles et pressing
    - verticality → passes_penalty_area / passes_final_third * 100
    - pressing_intensity → HIGH=80, MEDIUM=55, LOW=35
    - etc.
    """
    # Extraire les valeurs brutes
    possession = team_data.get('possession_pct', 50)
    tackles_total = team_data.get('tackles_total', 250)
    tackles_def = team_data.get('tackles_def_3rd', 100)
    tackles_att = team_data.get('tackles_att_3rd', 30)
    touches_def = team_data.get('touches_def_3rd', 2500)
    touches_mid = team_data.get('touches_mid_3rd', 3500)
    touches_att = team_data.get('touches_att_3rd', 2000)
    touches_total = touches_def + touches_mid + touches_att
    progressive_passes = team_data.get('progressive_passes', 500)
    passes_final_third = team_data.get('passes_final_third', 400)
    passes_penalty_area = team_data.get('passes_penalty_area', 100)
    pass_completion = team_data.get('pass_completion', 80)
    shots = team_data.get('shots', 150)
    xg = team_data.get('xg', 20)
    aerials_won = team_data.get('aerials_won', 200)
    aerials_lost = team_data.get('aerials_lost', 200)
    fouls = team_data.get('fouls', 150)

    # Pressing intensity mapping
    pressing_str = team_data.get('pressing_intensity', 'MEDIUM')
    if pressing_str == 'HIGH':
        pressing_intensity = 80
    elif pressing_str == 'VERY_HIGH':
        pressing_intensity = 90
    elif pressing_str == 'LOW':
        pressing_intensity = 35
    else:
        pressing_intensity = 55

    # Defensive style → defensive line height
    defensive_style = team_data.get('defensive_style', 'MID_BLOCK')
    if defensive_style == 'HIGH_LINE_PRESSING':
        defensive_line_height = 55
    elif defensive_style == 'HIGH_LINE':
        defensive_line_height = 50
    elif defensive_style == 'DEEP_BLOCK':
        defensive_line_height = 30
    elif defensive_style == 'VERY_DEEP_BLOCK':
        defensive_line_height = 25
    else:  # MID_BLOCK
        defensive_line_height = 42

    # Calculer les 24 features
    features = {
        # Possession & Style
        'possession': possession,

        # PPDA estimé: plus le tackle_att_pct est élevé, plus le PPDA est bas (pressing haut)
        'ppda': max(5, min(20, 15 - (tackles_att / tackles_total * 30) if tackles_total > 0 else 10)),

        # Verticality: proportion passes dans la surface
        'verticality': (passes_penalty_area / passes_final_third * 100) if passes_final_third > 0 else 25,

        # Pressing
        'pressing_intensity': pressing_intensity,

        # Crosses estimés depuis touches dans le dernier tiers
        'crosses_per_90': touches_att * 0.01 if touches_att > 0 else 15,

        # Defensive line height
        'defensive_line_height': defensive_line_height,

        # Counter attack goals estimé depuis style défensif
        'counter_attack_goals_pct': 35 if defensive_style in ['DEEP_BLOCK', 'VERY_DEEP_BLOCK'] else 15,

        # Long balls estimé
        'long_balls_pct': max(5, 25 - possession * 0.3),

        # Width index: différence entre attaque et milieu
        'width_index': ((touches_att - touches_mid) / touches_total * 100 + 50) if touches_total > 0 else 50,

        # High recoveries estimé depuis pressing
        'high_recoveries_pct': tackles_att / tackles_total * 100 if tackles_total > 0 else 15,

        # Transition speed estimé
        'transition_speed': 70 if pressing_intensity > 70 else 50,

        # Shots per 90 (assumant ~15 matchs = ~1350 minutes)
        'shots_per_90': shots / 15 if shots > 0 else 10,

        # Style variance (estimé faible pour données moyennes)
        'style_variance': 0.15,

        # Home/away difference (données pas disponibles, estimé moyen)
        'home_away_style_diff': 0.20,

        # Score dependent variance
        'score_dependent_variance': 0.20,

        # Aerial duels
        'aerial_duels_won_pct': team_data.get('aerial_win_pct', 50),

        # Sprints estimé depuis pressing
        'sprints_per_90': pressing_intensity * 1.3,

        # Pass accuracy
        'pass_accuracy': pass_completion,

        # xG per 90
        'xg_per_90': xg / 15 if xg > 0 else 1.5,

        # xGA per 90 estimé (inversement proportionnel à la défense)
        'xga_per_90': max(0.8, 2.0 - (defensive_line_height / 100)),

        # Set piece goals (estimé moyen)
        'set_piece_goals_pct': 25,

        # Goals from counter
        'goals_from_counter_pct': 30 if defensive_style in ['DEEP_BLOCK', 'VERY_DEEP_BLOCK'] else 15,

        # Progressive passes per 90
        'progressive_passes_per_90': progressive_passes / 15 if progressive_passes > 0 else 35,

        # Final third entries per 90
        'final_third_entries_per_90': passes_final_third / 15 if passes_final_third > 0 else 30,
    }

    return features


# ═══════════════════════════════════════════════════════════════════════════════
# TEST PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def run_96_teams_test():
    """Exécuter le test de classification sur les 96 équipes"""

    print("=" * 80)
    print("🏆 CHESS ENGINE V2.5 - TEST 96 ÉQUIPES")
    print("=" * 80)
    print()

    # Charger les données
    data_path = Path("/home/Mon_ps/data/quantum_v2/fbref_tactical_profiles.json")

    if not data_path.exists():
        print(f"❌ Fichier non trouvé: {data_path}")
        return

    with open(data_path, 'r') as f:
        teams_data = json.load(f)

    print(f"📊 {len(teams_data)} équipes chargées")
    print()

    # Créer le classifier
    classifier = AdaptiveProfileClassifier()

    # Résultats
    results = []
    profile_counts = Counter()
    league_profiles = defaultdict(lambda: Counter())

    # Header du tableau
    print(f"{'#':<4} {'Équipe':<25} {'Ligue':<12} {'Profil':<20} {'Conf':<8}")
    print("-" * 80)

    # Classifier chaque équipe
    for i, team_data in enumerate(teams_data, 1):
        team_name = team_data.get('team', 'Unknown')
        league = team_data.get('league', 'Unknown')

        # Transformer les features
        features = transform_fbref_to_features(team_data)

        # Classifier
        result = classifier.classify(
            team_id=team_name,
            team_metrics=features
        )

        # Stocker le résultat
        profile = result.primary_profile.value
        confidence = result.confidence

        results.append({
            'team': team_name,
            'league': league,
            'profile': profile,
            'confidence': confidence,
            'secondary_profile': result.secondary_profile.value if result.secondary_profile else None,
            'explanations': result.explanation[:2] if result.explanation else []
        })

        # Stats
        profile_counts[profile] += 1
        league_profiles[league][profile] += 1

        # Afficher
        print(f"{i:<4} {team_name:<25} {league:<12} {profile:<20} {confidence:.2f}")

    print()
    print("=" * 80)
    print("📈 STATISTIQUES")
    print("=" * 80)
    print()

    # Distribution des profils
    print("📊 Distribution des profils:")
    print("-" * 40)
    for profile, count in sorted(profile_counts.items(), key=lambda x: -x[1]):
        pct = count / len(teams_data) * 100
        bar = "█" * int(pct / 2)
        print(f"  {profile:<20} {count:>3} ({pct:>5.1f}%) {bar}")

    print()

    # Par ligue
    print("🏆 Profils par ligue:")
    print("-" * 40)
    for league in sorted(league_profiles.keys()):
        profiles = league_profiles[league]
        top_profile = max(profiles.items(), key=lambda x: x[1])
        print(f"  {league:<12} → {top_profile[0]} ({top_profile[1]} équipes)")

    print()

    # Confiance moyenne
    avg_confidence = sum(r['confidence'] for r in results) / len(results)
    high_conf = sum(1 for r in results if r['confidence'] >= 0.7)
    low_conf = sum(1 for r in results if r['confidence'] < 0.5)

    print("🎯 Confiance:")
    print("-" * 40)
    print(f"  Moyenne:     {avg_confidence:.2%}")
    print(f"  Haute (≥70%): {high_conf} équipes ({high_conf/len(results)*100:.1f}%)")
    print(f"  Basse (<50%): {low_conf} équipes ({low_conf/len(results)*100:.1f}%)")

    print()

    # Sauvegarder les résultats
    output_path = Path("/home/Mon_ps/data/quantum_v2/classification_results_v25.json")
    output = {
        'generated_at': datetime.now().isoformat(),
        'engine_version': '2.5',
        'total_teams': len(results),
        'avg_confidence': avg_confidence,
        'profile_distribution': dict(profile_counts),
        'results': results
    }

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"💾 Résultats sauvegardés: {output_path}")
    print()
    print("=" * 80)
    print("✅ TEST TERMINÉ")
    print("=" * 80)

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    run_96_teams_test()
