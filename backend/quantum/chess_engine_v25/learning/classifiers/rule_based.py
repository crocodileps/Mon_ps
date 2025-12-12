"""
╔══════════════════════════════════════════════════════════════════════════════════════════╗
║                    RULE-BASED CLASSIFIER                                                 ║
║                    Classification par règles expertes                                    ║
╠══════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                          ║
║  Avantages:                                                                              ║
║  - 100% explicable (on sait POURQUOI une équipe est classée ainsi)                      ║
║  - Pas besoin de données d'entraînement                                                 ║
║  - Fonctionne immédiatement                                                             ║
║  - Base de comparaison pour les modèles ML                                              ║
║                                                                                          ║
║  Auteur: Mya & Claude | Version: 1.0.0 | Date: 12 Décembre 2025                         ║
╚══════════════════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Dict, List, Tuple, Optional
from enum import Enum
from dataclasses import dataclass
import numpy as np


class TacticalProfile(Enum):
    """Les 12 profils tactiques ADN"""

    # Offensifs (4)
    POSSESSION = "POSSESSION"       # Man City, Barça - Possession 60%+, jeu patient
    GEGENPRESS = "GEGENPRESS"       # Liverpool, Dortmund - Pressing ultra-haut
    WIDE_ATTACK = "WIDE_ATTACK"     # Real Madrid - Centres, largeur maximum
    DIRECT_ATTACK = "DIRECT_ATTACK" # Leicester titre - Verticalité, passes longues

    # Défensifs (3)
    LOW_BLOCK = "LOW_BLOCK"         # Atlético Madrid - Défense basse, contre
    MID_BLOCK = "MID_BLOCK"         # Équipes milieu tableau - Équilibre
    PARK_THE_BUS = "PARK_THE_BUS"   # Mode survie - Ultra-défensif

    # Hybrides (3)
    TRANSITION = "TRANSITION"       # Tottenham Conte - Défense → Attaque rapide
    ADAPTIVE = "ADAPTIVE"           # Ancelotti - Caméléon, change selon adversaire
    BALANCED = "BALANCED"           # Équipes moyennes - Pas d'identité forte

    # Contextuels (2)
    HOME_DOMINANT = "HOME_DOMINANT" # Très différent domicile vs extérieur
    SCORE_DEPENDENT = "SCORE_DEPENDENT"  # Change selon score en cours


class ProfileFamily(Enum):
    """Familles de profils pour la matrice de friction niveau 1"""
    OFFENSIVE = "OFFENSIVE"
    DEFENSIVE = "DEFENSIVE"
    HYBRID = "HYBRID"
    CONTEXTUAL = "CONTEXTUAL"


# Mapping profil → famille
PROFILE_TO_FAMILY = {
    TacticalProfile.POSSESSION: ProfileFamily.OFFENSIVE,
    TacticalProfile.GEGENPRESS: ProfileFamily.OFFENSIVE,
    TacticalProfile.WIDE_ATTACK: ProfileFamily.OFFENSIVE,
    TacticalProfile.DIRECT_ATTACK: ProfileFamily.OFFENSIVE,

    TacticalProfile.LOW_BLOCK: ProfileFamily.DEFENSIVE,
    TacticalProfile.MID_BLOCK: ProfileFamily.DEFENSIVE,
    TacticalProfile.PARK_THE_BUS: ProfileFamily.DEFENSIVE,

    TacticalProfile.TRANSITION: ProfileFamily.HYBRID,
    TacticalProfile.ADAPTIVE: ProfileFamily.HYBRID,
    TacticalProfile.BALANCED: ProfileFamily.HYBRID,

    TacticalProfile.HOME_DOMINANT: ProfileFamily.CONTEXTUAL,
    TacticalProfile.SCORE_DEPENDENT: ProfileFamily.CONTEXTUAL,
}


@dataclass
class RuleExplanation:
    """Explication d'une règle appliquée"""
    metric: str
    value: float
    operator: str
    threshold: float
    matched: bool
    explanation: str


class RuleBasedClassifier:
    """
    Classification par règles expertes
    Explicable et prévisible - la base de l'ensemble
    """

    # Prototypes de référence pour chaque profil
    PROTOTYPES = {
        TacticalProfile.POSSESSION: {
            "possession": 62, "ppda": 14, "verticality": 35,
            "passes_per_90": 550, "pass_accuracy": 88
        },
        TacticalProfile.GEGENPRESS: {
            "possession": 52, "ppda": 6, "pressing_intensity": 85,
            "high_recoveries_pct": 35, "sprints_per_90": 130
        },
        TacticalProfile.WIDE_ATTACK: {
            "possession": 55, "crosses_per_90": 22, "width_index": 70,
            "final_third_entries_per_90": 45
        },
        TacticalProfile.DIRECT_ATTACK: {
            "possession": 42, "verticality": 75, "long_balls_pct": 18,
            "aerial_duels_per_90": 45
        },
        TacticalProfile.LOW_BLOCK: {
            "possession": 38, "defensive_line_height": 30,
            "pressing_intensity": 35, "counter_attack_goals_pct": 30
        },
        TacticalProfile.MID_BLOCK: {
            "possession": 47, "defensive_line_height": 42,
            "pressing_intensity": 55
        },
        TacticalProfile.PARK_THE_BUS: {
            "possession": 32, "shots_per_90": 7,
            "defensive_line_height": 25, "pressing_intensity": 25
        },
        TacticalProfile.TRANSITION: {
            "possession": 45, "counter_attack_goals_pct": 28,
            "transition_speed": 70, "verticality": 60
        },
        TacticalProfile.ADAPTIVE: {
            "style_variance": 0.35, "tactical_flexibility": 0.7
        },
        TacticalProfile.BALANCED: {
            "possession": 50, "style_variance": 0.15,
            "defensive_line_height": 45
        },
        TacticalProfile.HOME_DOMINANT: {
            "home_away_style_diff": 0.45, "home_win_rate": 0.65,
            "away_win_rate": 0.30
        },
        TacticalProfile.SCORE_DEPENDENT: {
            "score_dependent_variance": 0.40, "late_goals_pct": 0.25
        }
    }

    # Règles de classification (metric, operator, threshold)
    PROFILE_RULES = {
        TacticalProfile.POSSESSION: {
            'possession': ('>', 58),
            'ppda': ('>', 12),
            'verticality': ('<', 45),
            'pass_accuracy': ('>', 85)
        },
        TacticalProfile.GEGENPRESS: {
            'ppda': ('<', 8),
            'pressing_intensity': ('>', 75),
            'high_recoveries_pct': ('>', 30)
        },
        TacticalProfile.WIDE_ATTACK: {
            'crosses_per_90': ('>', 18),
            'width_index': ('>', 60),
            'possession': ('between', (48, 60))
        },
        TacticalProfile.DIRECT_ATTACK: {
            'verticality': ('>', 70),
            'possession': ('<', 48),
            'long_balls_pct': ('>', 15)
        },
        TacticalProfile.LOW_BLOCK: {
            'possession': ('<', 42),
            'defensive_line_height': ('<', 35),
            'pressing_intensity': ('<', 40)
        },
        TacticalProfile.MID_BLOCK: {
            'possession': ('between', (42, 52)),
            'defensive_line_height': ('between', (35, 50)),
            'pressing_intensity': ('between', (40, 65))
        },
        TacticalProfile.PARK_THE_BUS: {
            'possession': ('<', 35),
            'shots_per_90': ('<', 8),
            'defensive_line_height': ('<', 30)
        },
        TacticalProfile.TRANSITION: {
            'counter_attack_goals_pct': ('>', 25),
            'transition_speed': ('>', 65),
            'verticality': ('>', 55)
        },
        TacticalProfile.ADAPTIVE: {
            'style_variance': ('>', 0.30),
            'tactical_flexibility': ('>', 0.5)
        },
        TacticalProfile.BALANCED: {
            'possession': ('between', (46, 54)),
            'style_variance': ('<', 0.20)
        },
        TacticalProfile.HOME_DOMINANT: {
            'home_away_style_diff': ('>', 0.40)
        },
        TacticalProfile.SCORE_DEPENDENT: {
            'score_dependent_variance': ('>', 0.35)
        }
    }

    def __init__(self):
        self.classification_history = []

    def predict(self, features: Dict[str, float]) -> Tuple[TacticalProfile, float, List[str]]:
        """
        Classifier une équipe avec explications

        Args:
            features: Dict des métriques de l'équipe

        Returns:
            Tuple (profil, confidence, explications)
        """
        scores = {}
        all_explanations = {}

        for profile, rules in self.PROFILE_RULES.items():
            score = 0
            matched_rules = []
            total_rules = len(rules)

            for metric, (operator, threshold) in rules.items():
                value = features.get(metric, 0)
                matched = False
                explanation = ""

                if operator == '>':
                    matched = value > threshold
                    explanation = f"{metric}={value:.1f} > {threshold}"
                elif operator == '<':
                    matched = value < threshold
                    explanation = f"{metric}={value:.1f} < {threshold}"
                elif operator == 'between':
                    low, high = threshold
                    matched = low <= value <= high
                    explanation = f"{low} ≤ {metric}={value:.1f} ≤ {high}"
                elif operator == '>=':
                    matched = value >= threshold
                    explanation = f"{metric}={value:.1f} ≥ {threshold}"
                elif operator == '<=':
                    matched = value <= threshold
                    explanation = f"{metric}={value:.1f} ≤ {threshold}"

                if matched:
                    score += 1
                    matched_rules.append(f"✓ {explanation}")
                else:
                    matched_rules.append(f"✗ {explanation}")

            scores[profile] = score / total_rules if total_rules > 0 else 0
            all_explanations[profile] = matched_rules

        # Meilleur profil
        best_profile = max(scores, key=scores.get)
        confidence = scores[best_profile]

        # Obtenir le second meilleur pour comparaison
        sorted_profiles = sorted(scores.items(), key=lambda x: -x[1])
        if len(sorted_profiles) > 1:
            gap = sorted_profiles[0][1] - sorted_profiles[1][1]
            # Ajuster la confiance selon l'écart
            if gap > 0.3:
                confidence = min(0.95, confidence + 0.1)
            elif gap < 0.1:
                confidence = max(0.3, confidence - 0.1)

        explanations = all_explanations[best_profile]

        return best_profile, confidence, explanations

    def predict_proba(self, features: Dict[str, float]) -> Dict[TacticalProfile, float]:
        """
        Retourne les probabilités normalisées pour chaque profil

        Args:
            features: Dict des métriques de l'équipe

        Returns:
            Dict profil → probabilité
        """
        scores = {}

        for profile, rules in self.PROFILE_RULES.items():
            score = 0
            total_rules = len(rules)

            for metric, (operator, threshold) in rules.items():
                value = features.get(metric, 0)

                if operator == '>':
                    score += 1 if value > threshold else 0
                elif operator == '<':
                    score += 1 if value < threshold else 0
                elif operator == 'between':
                    low, high = threshold
                    score += 1 if low <= value <= high else 0
                elif operator == '>=':
                    score += 1 if value >= threshold else 0
                elif operator == '<=':
                    score += 1 if value <= threshold else 0

            scores[profile] = score / total_rules if total_rules > 0 else 0

        # Normaliser pour que la somme = 1
        total = sum(scores.values()) + 0.001
        return {p: s / total for p, s in scores.items()}

    def calculate_distance_to_prototype(self, features: Dict[str, float],
                                        profile: TacticalProfile) -> float:
        """
        Calcule la distance euclidienne au prototype du profil
        Plus petite = plus proche du profil idéal

        Args:
            features: Métriques de l'équipe
            profile: Profil cible

        Returns:
            Distance normalisée (0-1)
        """
        prototype = self.PROTOTYPES.get(profile, {})
        if not prototype:
            return 1.0

        distances = []
        for metric, proto_value in prototype.items():
            actual_value = features.get(metric, proto_value)

            # Normaliser par la valeur du prototype
            if proto_value != 0:
                normalized_diff = abs(actual_value - proto_value) / abs(proto_value)
            else:
                normalized_diff = abs(actual_value)

            distances.append(normalized_diff)

        # Distance euclidienne normalisée
        if distances:
            return min(1.0, np.sqrt(np.mean([d**2 for d in distances])))
        return 1.0

    def get_family(self, profile: TacticalProfile) -> ProfileFamily:
        """Retourne la famille d'un profil"""
        return PROFILE_TO_FAMILY.get(profile, ProfileFamily.HYBRID)

    def explain_classification(self, features: Dict[str, float]) -> Dict:
        """
        Explication détaillée de la classification

        Args:
            features: Métriques de l'équipe

        Returns:
            Dict avec profil, score, distance au prototype, règles matchées
        """
        profile, confidence, explanations = self.predict(features)
        distance = self.calculate_distance_to_prototype(features, profile)
        proba = self.predict_proba(features)

        # Top 3 profils
        sorted_proba = sorted(proba.items(), key=lambda x: -x[1])[:3]

        return {
            "primary_profile": profile,
            "confidence": confidence,
            "distance_to_prototype": distance,
            "family": self.get_family(profile),
            "matched_rules": [e for e in explanations if e.startswith("✓")],
            "unmatched_rules": [e for e in explanations if e.startswith("✗")],
            "top_3_candidates": [
                {"profile": p.value, "score": s} for p, s in sorted_proba
            ],
            "is_clear_classification": confidence > 0.7 and distance < 0.5
        }


# Export pour utilisation externe
__all__ = [
    "RuleBasedClassifier",
    "TacticalProfile",
    "ProfileFamily",
    "PROFILE_TO_FAMILY"
]
