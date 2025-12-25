#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════════════
FRICTION CONFIG V2.0 - PARAMÈTRES EXTERNALISÉS HEDGE FUND GRADE
═══════════════════════════════════════════════════════════════════════════════════════

Fichier: quantum/config/friction_config.py
Version: 2.0.0
Date: 2025-12-25

PHILOSOPHIE:
- Tous les coefficients sont EXTERNALISÉS pour calibration via backtest
- Aucun magic number dans le code métier
- Chaque paramètre est documenté avec son impact
- Échelles de normalisation basées sur données RÉELLES de la DB

USAGE:
    from quantum.config.friction_config import FRICTION_CONFIG
    tempo_exp = FRICTION_CONFIG["kinetic"]["tempo_exponent"]

CALIBRATION:
    1. Modifier les valeurs dans ce fichier
    2. Relancer le backtest
    3. Comparer les résultats
    4. Itérer jusqu'à optimum

CHANGELOG V2.0:
- Ajout des échelles de normalisation (basées sur min/max réels de la DB)
- Correction formule physical_edge (rotation = fraîcheur, pas fatigue)
- Ajout configs pour Disciplinary Friction, Velocity Mismatch, Frustration Index
- Séparation Intensity / Stamina / Freshness dans physical_edge
"""

from typing import Dict, Any

# ═══════════════════════════════════════════════════════════════════════════════════════
# ÉCHELLES DE NORMALISATION - BASÉES SUR DONNÉES RÉELLES DB
# ═══════════════════════════════════════════════════════════════════════════════════════
# Ces valeurs viennent de: SELECT MIN/MAX FROM quantum.team_quantum_dna_v3

NORMALIZATION_SCALES: Dict[str, Dict[str, float]] = {
    # NEMESIS DNA
    "verticality": {"min": 2.3, "max": 11.5, "avg": 5.84, "scale": 15.0},
    "patience": {"min": 2.4, "max": 16.5, "avg": 7.38, "scale": 20.0},
    
    # PHYSICAL DNA
    "pressing_intensity": {"min": 4.6, "max": 23.0, "avg": 11.68, "scale": 25.0},
    "late_game_dominance": {"min": 9.0, "max": 79.0, "avg": 36.3, "scale": 100.0},
    "estimated_rotation_index": {"min": 0.0, "max": 100.0, "avg": 50.0, "scale": 100.0},
    
    # PSYCHE DNA
    "panic_factor": {"min": 0.34, "max": 3.22, "avg": 1.38, "scale": 5.0},
    "killer_instinct": {"min": 0.0, "max": 3.0, "avg": 1.0, "scale": 3.0},
    "lead_protection": {"min": 0.0, "max": 1.0, "avg": 0.5, "scale": 1.0},
    "comeback_mentality": {"min": 0.0, "max": 5.0, "avg": 1.5, "scale": 5.0},
    
    # CONTEXT DNA (déjà en 0-100)
    "home_strength": {"min": 0.0, "max": 100.0, "avg": 50.0, "scale": 100.0},
    "away_strength": {"min": 0.0, "max": 100.0, "avg": 50.0, "scale": 100.0},
    
    # ROSTER DNA
    "top3_dependency": {"min": 0.0, "max": 100.0, "avg": 35.0, "scale": 100.0},
    
    # REFEREE (strictness_level from referee_intelligence)
    "strictness_level": {"min": 1.0, "max": 10.0, "avg": 6.0, "scale": 10.0},
    "card_per_foul": {"min": 10.0, "max": 25.0, "avg": 15.0, "scale": 25.0},
}


# ═══════════════════════════════════════════════════════════════════════════════════════
# FRICTION CONFIG - PARAMÈTRES CALIBRABLES
# ═══════════════════════════════════════════════════════════════════════════════════════

FRICTION_CONFIG: Dict[str, Any] = {
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # KINETIC ENERGY - Formule Non-Linéaire
    # ─────────────────────────────────────────────────────────────────────────────────
    # Formule: kinetic = base_intensity × tempo_factor × chaos_factor
    # où tempo_factor = (tempo / 50) ** tempo_exponent
    
    "kinetic": {
        # Poids pour base_intensity = (style × w1 + mental × w2 + friction × w3)
        "style_clash_weight": 0.40,      # Impact du clash de style
        "mental_clash_weight": 0.30,     # Impact du clash mental
        "friction_score_weight": 0.30,   # Impact du score friction global
        
        # Exposant tempo (non-linéaire)
        # 1.0 = linéaire, 1.2 = légèrement exponentiel, 1.5 = très exponentiel
        # Plus élevé = les matchs rapides explosent, les lents s'écrasent
        "tempo_exponent": 1.2,
        
        # Borne minimum pour tempo_factor (évite division par zéro)
        "tempo_factor_min": 0.1,
        
        # Chaos factor = 1 + (chaos - 50) / chaos_divisor
        # chaos_divisor = 200 → max ±25% impact
        # chaos_divisor = 100 → max ±50% impact
        "chaos_divisor": 200.0,
        
        # Distribution home/away
        "home_advantage_base": 1.05,     # +5% énergie canalisée par home
        "home_advantage_mental_threshold": 45,  # Si mental < seuil, home perd avantage
        "home_advantage_reduced": 0.95,  # Avantage si home dominé mentalement
        
        # Bornes de sécurité
        "kinetic_min": 0.1,
        "kinetic_max": 99.9,
    },
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # PHYSICAL EDGE V2.0 - Avantage Physique (FORMULE SENIOR QUANT)
    # ─────────────────────────────────────────────────────────────────────────────────
    # Séparation: Intensity (début match) / Stamina (fin match) / Freshness (rotation)
    # Formule: physical_edge = 50 + (h_final - a_final) / score_divisor
    
    "physical": {
        # === INTENSITY (40%) - Capacité à imposer le défi physique ===
        # Pressing pondéré par efficacité + Duels aériens
        "intensity_weight": 0.40,
        "intensity_pressing_weight": 0.60,    # Dans intensity: poids du pressing
        "intensity_aerial_weight": 0.40,       # Dans intensity: poids de l'aérien
        
        # === STAMINA (40%) - Capacité à finir fort ===
        # Late Game Dominance + Résistance défensive tardive
        "stamina_weight": 0.40,
        "stamina_late_dom_weight": 0.60,       # Dans stamina: poids late_game_dominance
        "stamina_resist_weight": 0.40,          # Dans stamina: poids resist_late
        
        # === FRESHNESS (20%) - Gestion de l'effectif ===
        # CORRECTION V2: rotation élevée = joueurs FRAIS (pas fatigués!)
        "freshness_weight": 0.20,
        "bench_quality_enabled": True,         # Pondérer rotation par qualité du banc
        
        # === EFFICIENCY FACTOR ===
        # Pressing coûte moins si tu as le ballon (possession efficiency)
        "efficiency_factor_enabled": True,
        "efficiency_base": 50.0,               # Possession de référence
        
        # === NORMALISATION ===
        "score_divisor": 2.0,
        "default_value": 50.0,
    },
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # DISCIPLINARY FRICTION - Chaos par l'Arbitre (ALPHA #1)
    # ─────────────────────────────────────────────────────────────────────────────────
    # Formule: destruction_score = (contact_density / 50) × ref_strictness × rivalry_mult
    
    "disciplinary": {
        # Contact Density = (pressing_home + pressing_away) / 2
        "contact_density_divisor": 50.0,
        
        # Referee Strictness = card_per_foul / avg_league
        "avg_league_card_per_foul": 15.0,      # Moyenne league
        
        # Derby/Rivalry Multiplier
        "derby_multiplier": 1.30,              # +30% tensions pour derbies
        "rivalry_base_threshold": 50.0,        # Rivalry > 50 → applique multiplicateur
        "rivalry_multiplier_scale": 100.0,     # Comment convertir rivalry en mult
        
        # Seuils de décision
        "broken_rhythm_threshold": 1.4,        # destruction_score > 1.4 = match haché
        "high_cards_threshold": 1.2,           # destruction_score > 1.2 = over cards
        
        # Trading signals
        "signal_under_goals_confidence": 75,
        "signal_over_cards_confidence": 80,
        "signal_late_first_goal_confidence": 70,
    },
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # VELOCITY MISMATCH - Rupture de Ligne (ALPHA #2)
    # ─────────────────────────────────────────────────────────────────────────────────
    # Formule: exposure = counter_speed × line_height
    # counter_speed = verticality × (1 - patience/100)
    # line_height = possession / 50
    
    "velocity": {
        # Seuils
        "lethal_threshold": 80.0,              # exposure > 80 = exécution
        "high_exposure_threshold": 60.0,       # exposure > 60 = risque élevé
        
        # Calcul counter_speed
        "verticality_scale": 15.0,             # Max verticality dans les données
        "patience_scale": 20.0,                # Max patience dans les données
        
        # Trading signals
        "signal_first_goal_underdog_confidence": 75,
        "signal_lay_clean_sheet_confidence": 70,
    },
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # FRUSTRATION INDEX - Cocotte-Minute (ALPHA #3)
    # ─────────────────────────────────────────────────────────────────────────────────
    # Pré-match: prédit le risque qu'une équipe implose
    
    "frustration": {
        # Seuils de possession pour domination
        "high_possession_threshold": 55.0,
        
        # Poids des composants
        "possession_non_clinical_weight": 25.0,  # Si poss > 55% et pas clinical
        "xg_negative_weight": 20.0,              # Si xG diff négatif malgré possession
        "panic_factor_weight": 0.30,             # Multiplicateur panic_factor
        "collapse_rate_weight": 0.20,            # Multiplicateur collapse_rate
        
        # Seuils
        "boiling_point_threshold": 70.0,         # frustration_risk > 70 = danger
        "panic_factor_high_threshold": 60.0,     # panic_factor normalisé > 60
        
        # Trading signals
        "signal_lay_favorite_confidence": 70,
    },
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # SPATIAL FRICTION - Asphyxie Spatiale (ALPHA 2.0 #1)
    # ─────────────────────────────────────────────────────────────────────────────────
    # Croise attack_zones avec defensive_structure
    
    "spatial": {
        # Score si attaque centre vs bloc serré
        "center_vs_narrow_friction": 90.0,     # ASPHYXIE → Under
        "wings_vs_narrow_friction": 10.0,      # BOULEVARDS → Over/Corners
        "wings_vs_wide_friction": 80.0,        # BLOQUÉ CÔTÉS → Under Corners
        
        # Seuil d'asphyxie
        "asphyxiation_threshold": 85.0,
        
        # Trading signals
        "signal_under_25_confidence": 75,
    },
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # AERIAL MISMATCH - Set-Piece Bypass (ALPHA 2.0 #3)
    # ─────────────────────────────────────────────────────────────────────────────────
    
    "aerial": {
        # Seuil de mismatch significatif
        "mismatch_threshold": 25.0,            # Différentiel > 25% = dominance
        
        # Conditions d'activation
        "trench_warfare_friction_threshold": 80.0,
        
        # Trading signals
        "signal_header_goal_confidence": 70,
        "signal_over_corners_confidence": 65,
    },
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # SCÉNARIOS AUTOMATIQUES (Game Scripts)
    # ─────────────────────────────────────────────────────────────────────────────────
    
    "scenarios": {
        # TOTAL_CHAOS: chaos_potential >= threshold
        "chaos_threshold": 70,
        
        # OPEN_GAME: style_clash >= threshold AND tempo >= threshold
        "open_game_style_threshold": 75,
        "open_game_tempo_threshold": 60,
        
        # HOME_DOMINATED / AWAY_PRESSURED: mental_clash thresholds
        "mental_home_dominated_threshold": 35,  # mental < 35 = home dominé
        "mental_away_pressured_threshold": 65,  # mental > 65 = away sous pression
        
        # HIGH_SCORING_RIVALRY: h2h_avg_goals >= threshold
        "high_scoring_h2h_threshold": 3.5,
        
        # TENSE_STALEMATE: predicted_winner == draw AND friction >= threshold
        "tense_stalemate_friction_threshold": 60,
        
        # BROKEN_RHYTHM: disciplinary_friction > threshold
        "broken_rhythm_threshold": 1.4,
        
        # END_TO_END: velocity_mismatch lethal
        "end_to_end_exposure_threshold": 80.0,
        
        # ASPHYXIATION: spatial_friction > threshold
        "asphyxiation_threshold": 85.0,
        
        # TRENCH_WARFARE: midfield_congestion > threshold
        "trench_warfare_threshold": 80.0,
        
        # IMPLOSION_RISK: frustration_risk > threshold
        "implosion_threshold": 70.0,
    },
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # VALIDATION ET BORNES
    # ─────────────────────────────────────────────────────────────────────────────────
    
    "validation": {
        # Bornes pour scores (0-100)
        "score_min": 0.0,
        "score_max": 100.0,
        
        # Bornes pour probabilités (0-1)
        "probability_min": 0.0,
        "probability_max": 1.0,
        
        # Bornes pour predicted_goals
        "goals_min": 0.0,
        "goals_max": 10.0,
        
        # Warning si valeur hors bornes
        "log_warnings": True,
    },
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # CONFIDENCE SCORING
    # ─────────────────────────────────────────────────────────────────────────────────
    
    "confidence": {
        # Points pour H2H data quality
        "h2h_high_threshold": 5,         # >= 5 matchs = high quality
        "h2h_high_points": 30,
        "h2h_medium_threshold": 2,       # >= 2 matchs = medium quality
        "h2h_medium_points": 15,
        
        # Points pour prediction coherence
        "goals_coherent_range": (1.5, 4.0),
        "goals_coherent_points": 20,
        
        # Points pour BTTS coherence
        "btts_coherence_tolerance": 0.15,
        "btts_coherent_points": 20,
        
        # Points pour friction_vector présent
        "friction_vector_points": 15,
        
        # Points pour chaos > 30
        "chaos_min_threshold": 30,
        "chaos_present_points": 15,
        
        # Seuils de niveau
        "high_threshold": 80,
        "medium_threshold": 50,
    },
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # DATABASE
    # ─────────────────────────────────────────────────────────────────────────────────
    
    "database": {
        "table": "quantum.matchup_friction",
        "timeout_seconds": 30,
        "retry_count": 3,
        "retry_delay_seconds": 1,
    },
}


# ═══════════════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════════════

def get_kinetic_config() -> Dict[str, Any]:
    """Retourne la config kinetic."""
    return FRICTION_CONFIG["kinetic"]


def get_physical_config() -> Dict[str, Any]:
    """Retourne la config physical."""
    return FRICTION_CONFIG["physical"]


def get_scenario_config() -> Dict[str, Any]:
    """Retourne la config scénarios."""
    return FRICTION_CONFIG["scenarios"]


def get_validation_config() -> Dict[str, Any]:
    """Retourne la config validation."""
    return FRICTION_CONFIG["validation"]


def get_confidence_config() -> Dict[str, Any]:
    """Retourne la config confidence."""
    return FRICTION_CONFIG["confidence"]


def get_db_config() -> Dict[str, Any]:
    """Retourne la config database."""
    return FRICTION_CONFIG["database"]


def get_disciplinary_config() -> Dict[str, Any]:
    """Retourne la config disciplinary friction."""
    return FRICTION_CONFIG["disciplinary"]


def get_velocity_config() -> Dict[str, Any]:
    """Retourne la config velocity mismatch."""
    return FRICTION_CONFIG["velocity"]


def get_frustration_config() -> Dict[str, Any]:
    """Retourne la config frustration index."""
    return FRICTION_CONFIG["frustration"]


def get_spatial_config() -> Dict[str, Any]:
    """Retourne la config spatial friction."""
    return FRICTION_CONFIG["spatial"]


def get_aerial_config() -> Dict[str, Any]:
    """Retourne la config aerial mismatch."""
    return FRICTION_CONFIG["aerial"]


# ═══════════════════════════════════════════════════════════════════════════════════════
# NORMALISATION HELPERS
# ═══════════════════════════════════════════════════════════════════════════════════════

def normalize_to_100(value: float, field_name: str) -> float:
    """
    Normalise une valeur vers l'échelle 0-100 selon les échelles réelles de la DB.
    
    Args:
        value: Valeur brute
        field_name: Nom du champ (doit exister dans NORMALIZATION_SCALES)
    
    Returns:
        Valeur normalisée entre 0 et 100
    """
    if field_name not in NORMALIZATION_SCALES:
        return value  # Pas de normalisation si échelle inconnue
    
    scale = NORMALIZATION_SCALES[field_name]["scale"]
    normalized = (value / scale) * 100.0
    
    # Clamp entre 0 et 100
    return max(0.0, min(100.0, normalized))


def denormalize_from_100(value: float, field_name: str) -> float:
    """
    Dénormalise une valeur de 0-100 vers l'échelle originale.
    
    Args:
        value: Valeur normalisée (0-100)
        field_name: Nom du champ
    
    Returns:
        Valeur dans l'échelle originale
    """
    if field_name not in NORMALIZATION_SCALES:
        return value
    
    scale = NORMALIZATION_SCALES[field_name]["scale"]
    return (value / 100.0) * scale


def get_scale_info(field_name: str) -> Dict[str, float]:
    """
    Retourne les informations d'échelle pour un champ.
    
    Args:
        field_name: Nom du champ
    
    Returns:
        Dict avec min, max, avg, scale
    """
    return NORMALIZATION_SCALES.get(field_name, {
        "min": 0.0, "max": 100.0, "avg": 50.0, "scale": 100.0
    })


# ═══════════════════════════════════════════════════════════════════════════════════════
# VERSION INFO
# ═══════════════════════════════════════════════════════════════════════════════════════

FRICTION_CONFIG_VERSION = "2.0.0"
FRICTION_CONFIG_DATE = "2025-12-25"
FRICTION_CONFIG_AUTHOR = "Mon_PS Quant Team"

CHANGELOG = """
V2.0.0 (2025-12-25):
- Ajout NORMALIZATION_SCALES basées sur données réelles DB
- Correction formule physical_edge: rotation élevée = fraîcheur (pas fatigue)
- Ajout efficiency_factor pour pressing
- Séparation Intensity/Stamina/Freshness
- Ajout configs: disciplinary, velocity, frustration, spatial, aerial
- Ajout normalize_to_100() et denormalize_from_100() helpers
- Ajout game scripts dans scenarios
"""


if __name__ == "__main__":
    # Test: Afficher la config
    import json
    print("=" * 80)
    print("FRICTION CONFIG V2.0 - HEDGE FUND GRADE")
    print("=" * 80)
    print(f"\nVersion: {FRICTION_CONFIG_VERSION}")
    print(f"Date: {FRICTION_CONFIG_DATE}")
    print(f"\nSections: {list(FRICTION_CONFIG.keys())}")
    print(f"Normalization scales: {list(NORMALIZATION_SCALES.keys())}")
    
    # Test normalisation
    print("\n--- Test Normalisation ---")
    test_cases = [
        ("verticality", 5.84),
        ("pressing_intensity", 11.68),
        ("panic_factor", 1.38),
    ]
    for field, val in test_cases:
        norm = normalize_to_100(val, field)
        denorm = denormalize_from_100(norm, field)
        print(f"{field}: {val} → normalized: {norm:.1f} → denormalized: {denorm:.2f}")

