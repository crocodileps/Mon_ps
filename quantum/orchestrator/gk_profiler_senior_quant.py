"""
Goalkeeper Profiler - Senior Quant FBA Grade V2
================================================

Profilage Multi-Dimensionnel avec:
- Bayesian Smoothing (C variable par période)
- Z-Score normalization vs league baseline
- Edge pondéré par volume de tirs
- Context confidence flag

Date: 25 Décembre 2025
Author: Mon_PS Quant Team
"""

import statistics
from typing import Dict, List, Optional
from dataclasses import dataclass, field

# Import local
try:
    from quantum.orchestrator.dataclasses_v2 import GoalkeeperProfileFBA
except ImportError:
    # Fallback pour tests isolés
    GoalkeeperProfileFBA = None


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION SENIOR QUANT
# ═══════════════════════════════════════════════════════════════════════════════

# Constantes Bayésiennes (C variable par période)
BAYESIAN_CONFIDENCE = {
    "0-15": 8,    # Période courte, peu de tirs → forte régularisation
    "16-30": 5,
    "31-45": 5,
    "46-60": 5,
    "61-75": 5,
    "76-90": 5,
    "90+": 8,     # Période courte → forte régularisation
    "1H": 3,      # Agrégat, plus de volume → faible régularisation
    "2H": 3,
}

# Baseline ligue (Premier League 2024-25)
LEAGUE_BASELINE = {
    "save_rate_avg": 70.2,
    "save_rate_std": 8.5,
    "per_90_avg": -0.544,
    "per_90_std": 0.25,
}

# Seuils de classification (basés sur score global)
CLASSIFICATION_THRESHOLDS = {
    "ON_FIRE": 70,
    "SOLID": 50,
    "NORMAL": 30,
    "LEAKY": 0,
}

# Seuils de période (basés sur diff lissée vs baseline)
PERIOD_THRESHOLDS = {
    "STRONG": 10,
    "NORMAL": -10,
    "WEAK": -25,
    "CRITICAL": -100,
}

# Edge pondéré par volume
EDGE_MIN_SHOTS = 10

# Poids des dimensions (total = 100%)
DIMENSION_WEIGHTS = {
    "xg_performance": 0.25,
    "shot_stopping": 0.20,
    "timing_consistency": 0.20,
    "first_half": 0.15,
    "second_half": 0.15,
    "pressure": 0.05,
}


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTION PRINCIPALE
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_gk_profile_senior_quant(
    gk_data: Dict,
    timing_data: Dict,
    enriched_data: Dict,
    league: str = "Premier League"
) -> 'GoalkeeperProfileFBA':
    """
    Algorithme Senior Quant - Profilage Multi-Dimensionnel FBA Grade V2

    Args:
        gk_data: Données GK depuis defensive_line.goalkeeper
        timing_data: Données timing par période
        enriched_data: Données enrichies (goalkeeper_dna_enriched)
        league: Ligue pour baseline (default: Premier League)

    Returns:
        GoalkeeperProfileFBA avec scoring complet

    AMÉLIORATIONS vs V1:
    1. Bayesian Smoothing avec C variable par période
    2. Z-Score normalization vs league baseline
    3. Edge pondéré par volume de tirs
    4. Context confidence flag
    5. Sample reliability assessment
    """

    # ═══════════════════════════════════════════════════════════════
    # 0. EXTRACTION DONNÉES BRUTES
    # ═══════════════════════════════════════════════════════════════

    gk_name = gk_data.get('name', 'Unknown')
    team_name = enriched_data.get('team_name', gk_data.get('team', 'Unknown'))

    raw_overperform = float(gk_data.get('gk_overperform', 0.0))
    matches = int(gk_data.get('matches', 17))
    save_rate = float(gk_data.get('save_rate', 70.0))
    total_saves = int(gk_data.get('total_saves', 0))
    total_goals = int(gk_data.get('total_goals', 0))
    total_shots = total_saves + total_goals

    # Percentiles si disponibles
    gk_percentile = float(gk_data.get('gk_percentile', 50.0))
    percentiles = gk_data.get('percentiles', {})
    first_half_percentile = float(percentiles.get('1H_save_rate', 50.0))
    second_half_percentile = float(percentiles.get('2H_save_rate', 50.0))

    # ═══════════════════════════════════════════════════════════════
    # 1. NORMALISATION PER_90 (Z-Score vers 0-100)
    # ═══════════════════════════════════════════════════════════════

    per_90 = raw_overperform / matches if matches > 0 else 0

    z_per90 = (per_90 - LEAGUE_BASELINE["per_90_avg"]) / LEAGUE_BASELINE["per_90_std"]
    per_90_score = max(0, min(100, 50 + (z_per90 * 25)))

    # Utiliser gk_percentile si disponible et significatif
    if gk_percentile and gk_percentile != 50.0:
        per_90_score = gk_percentile

    # ═══════════════════════════════════════════════════════════════
    # 2. NORMALISATION SAVE_RATE (Z-Score vers 0-100)
    # ═══════════════════════════════════════════════════════════════

    z_sr = (save_rate - LEAGUE_BASELINE["save_rate_avg"]) / LEAGUE_BASELINE["save_rate_std"]
    save_rate_score = max(0, min(100, 50 + (z_sr * 25)))

    # ═══════════════════════════════════════════════════════════════
    # 3. TIMING ANALYSIS AVEC LISSAGE BAYÉSIEN
    # ═══════════════════════════════════════════════════════════════

    global_avg_sr = LEAGUE_BASELINE["save_rate_avg"] / 100

    period_ratings = {}
    period_details = {}
    weak_periods = []
    strong_periods = []
    smoothed_rates = []

    for period in ['0-15', '16-30', '31-45', '46-60', '61-75', '76-90', '90+']:
        p_data = timing_data.get(period, {})

        # Extraction données brutes
        raw_sr_pct = float(p_data.get('save_rate', global_avg_sr * 100))
        raw_sr = raw_sr_pct / 100
        shots = int(p_data.get('shots', p_data.get('shots_faced', 5)))
        saves = int(p_data.get('saves', int(shots * raw_sr)))
        vs_baseline = float(p_data.get('vs_baseline', 0))

        # Constante Bayésienne variable par période
        C = BAYESIAN_CONFIDENCE.get(period, 5)

        # Formule Bayésienne
        smoothed_sr = (saves + (C * global_avg_sr)) / (shots + C)
        smoothed_rates.append(smoothed_sr * 100)

        # Différentiel lissé vs baseline
        smoothed_diff = (smoothed_sr - global_avg_sr) * 100

        # Facteur de confiance basé sur volume
        confidence_factor = min(1.0, shots / EDGE_MIN_SHOTS)

        # Classification de la période
        if smoothed_diff >= PERIOD_THRESHOLDS["STRONG"]:
            rating = "STRONG"
            strong_periods.append(period)
        elif smoothed_diff >= PERIOD_THRESHOLDS["NORMAL"]:
            rating = "NORMAL"
        elif smoothed_diff >= PERIOD_THRESHOLDS["WEAK"]:
            rating = "WEAK"
            weak_periods.append(period)
        else:
            rating = "CRITICAL"
            weak_periods.append(period)

        period_ratings[period] = rating
        period_details[period] = {
            "raw_sr": round(raw_sr * 100, 1),
            "smoothed_sr": round(smoothed_sr * 100, 1),
            "smoothed_diff": round(smoothed_diff, 1),
            "shots": shots,
            "saves": saves,
            "vs_baseline_raw": vs_baseline,
            "confidence_factor": round(confidence_factor, 2),
            "bayesian_C": C
        }

    # ═══════════════════════════════════════════════════════════════
    # 4. TIMING CONSISTENCY SCORE
    # ═══════════════════════════════════════════════════════════════

    if len(smoothed_rates) > 1:
        consistency_std = statistics.stdev(smoothed_rates)
    else:
        consistency_std = 0

    timing_consistency_score = max(0, min(100, 100 - (consistency_std * 4)))

    # ═══════════════════════════════════════════════════════════════
    # 5. HALF PERFORMANCE SCORES
    # ═══════════════════════════════════════════════════════════════

    first_half_score = first_half_percentile
    second_half_score = second_half_percentile

    if first_half_percentile == 50.0:
        first_half_sr = float(timing_data.get('1H', {}).get('save_rate', 70))
        z_1h = (first_half_sr - LEAGUE_BASELINE["save_rate_avg"]) / LEAGUE_BASELINE["save_rate_std"]
        first_half_score = max(0, min(100, 50 + (z_1h * 25)))

    if second_half_percentile == 50.0:
        second_half_sr = float(timing_data.get('2H', {}).get('save_rate', 70))
        z_2h = (second_half_sr - LEAGUE_BASELINE["save_rate_avg"]) / LEAGUE_BASELINE["save_rate_std"]
        second_half_score = max(0, min(100, 50 + (z_2h * 25)))

    half_differential = first_half_percentile - second_half_percentile

    # ═══════════════════════════════════════════════════════════════
    # 6. PRESSURE SCORE
    # ═══════════════════════════════════════════════════════════════

    late_game_details = period_details.get('90+', {})
    late_game_smoothed = late_game_details.get('smoothed_sr', 50)
    pressure_score = max(0, min(100, late_game_smoothed))

    # ═══════════════════════════════════════════════════════════════
    # 7. OVERALL SCORE PONDÉRÉ
    # ═══════════════════════════════════════════════════════════════

    dimension_scores = {
        "xg_performance": round(per_90_score, 1),
        "shot_stopping": round(save_rate_score, 1),
        "timing_consistency": round(timing_consistency_score, 1),
        "first_half": round(first_half_score, 1),
        "second_half": round(second_half_score, 1),
        "pressure": round(pressure_score, 1)
    }

    overall_score = (
        per_90_score * DIMENSION_WEIGHTS["xg_performance"] +
        save_rate_score * DIMENSION_WEIGHTS["shot_stopping"] +
        timing_consistency_score * DIMENSION_WEIGHTS["timing_consistency"] +
        first_half_score * DIMENSION_WEIGHTS["first_half"] +
        second_half_score * DIMENSION_WEIGHTS["second_half"] +
        pressure_score * DIMENSION_WEIGHTS["pressure"]
    )

    # ═══════════════════════════════════════════════════════════════
    # 8. STATUS
    # ═══════════════════════════════════════════════════════════════

    if overall_score >= CLASSIFICATION_THRESHOLDS["ON_FIRE"]:
        status = "ON_FIRE"
    elif overall_score >= CLASSIFICATION_THRESHOLDS["SOLID"]:
        status = "SOLID"
    elif overall_score >= CLASSIFICATION_THRESHOLDS["NORMAL"]:
        status = "NORMAL"
    else:
        status = "LEAKY"

    # ═══════════════════════════════════════════════════════════════
    # 9. TIMING PATTERN
    # ═══════════════════════════════════════════════════════════════

    if half_differential >= 30:
        timing_pattern = "LATE_GAME_VULNERABLE"
    elif half_differential <= -30:
        timing_pattern = "EARLY_GAME_VULNERABLE"
    elif '90+' in weak_periods:
        timing_pattern = "CLUTCH_VULNERABLE"
    elif timing_consistency_score >= 70:
        timing_pattern = "CONSISTENT"
    else:
        timing_pattern = "INCONSISTENT"

    # ═══════════════════════════════════════════════════════════════
    # 10. EXPLOIT MARKETS (EDGE PONDÉRÉ)
    # ═══════════════════════════════════════════════════════════════

    exploit_markets = []

    for period in weak_periods:
        details = period_details.get(period, {})
        smoothed_diff = details.get('smoothed_diff', 0)
        shots = details.get('shots', 5)
        confidence_factor = details.get('confidence_factor', 0.5)

        raw_edge = abs(smoothed_diff) / 10
        adjusted_edge = raw_edge * confidence_factor

        if adjusted_edge >= 2.0 and confidence_factor >= 0.8:
            market_confidence = "HIGH"
        elif adjusted_edge >= 1.0 and confidence_factor >= 0.5:
            market_confidence = "MEDIUM"
        else:
            market_confidence = "LOW"

        exploit_markets.append({
            "market": f"goal_{period.replace('-', '_').replace('+', 'plus')}",
            "period": period,
            "reason": f"Vulnérable en {period} (smoothed: {details.get('smoothed_sr', 0):.1f}%)",
            "confidence": market_confidence,
            "raw_edge": round(raw_edge, 2),
            "adjusted_edge": round(adjusted_edge, 2),
            "confidence_factor": round(confidence_factor, 2),
            "shots_basis": shots
        })

    # Exploit 2H si LATE_GAME_VULNERABLE
    if timing_pattern == "LATE_GAME_VULNERABLE":
        half_edge = abs(half_differential) / 10
        exploit_markets.append({
            "market": "over_2h_goals",
            "period": "2H",
            "reason": f"2H percentile: {second_half_percentile}% (s'effondre)",
            "confidence": "HIGH" if second_half_percentile <= 20 else "MEDIUM",
            "raw_edge": round(half_edge, 2),
            "adjusted_edge": round(half_edge * 0.9, 2),
            "confidence_factor": 0.9,
            "shots_basis": total_shots // 2 if total_shots > 0 else 15
        })

    # Trier par adjusted_edge
    exploit_markets.sort(key=lambda x: x['adjusted_edge'], reverse=True)

    # ═══════════════════════════════════════════════════════════════
    # 11. BEHAVIORAL TAGS
    # ═══════════════════════════════════════════════════════════════

    behavioral_tags = []

    if timing_pattern != "CONSISTENT":
        behavioral_tags.append(timing_pattern)

    for vuln in gk_data.get('vulnerabilities', []):
        behavioral_tags.append(vuln)

    for strength in gk_data.get('strengths', []):
        behavioral_tags.append(strength)

    # ═══════════════════════════════════════════════════════════════
    # 12. SAMPLE RELIABILITY & CONTEXT CONFIDENCE
    # ═══════════════════════════════════════════════════════════════

    if total_shots >= 50:
        sample_reliability = "HIGH"
    elif total_shots >= 25:
        sample_reliability = "MEDIUM"
    else:
        sample_reliability = "LOW"

    has_psxg_per_period = 'xG_by_period' in gk_data or 'psxg_timing' in enriched_data
    context_confidence = "HIGH" if has_psxg_per_period else "MEDIUM"

    # ═══════════════════════════════════════════════════════════════
    # 13. NARRATIVE
    # ═══════════════════════════════════════════════════════════════

    status_emoji = {"ON_FIRE": "🔥", "SOLID": "✅", "NORMAL": "⚠️", "LEAKY": "🔴"}.get(status, "❓")

    top_exploit = exploit_markets[0] if exploit_markets else None
    exploit_text = f"Exploiter: {top_exploit['market']} (edge {top_exploit['adjusted_edge']})" if top_exploit else "Aucun exploit clair"

    narrative = (
        f"{status_emoji} {gk_name}: {timing_pattern} - "
        f"Score {overall_score:.1f}/100 ({status}). "
        f"1H: {first_half_percentile}% vs 2H: {second_half_percentile}%. "
        f"{exploit_text}. "
        f"[Reliability: {sample_reliability}]"
    )

    # ═══════════════════════════════════════════════════════════════
    # 14. CONSTRUCTION PROFIL FINAL
    # ═══════════════════════════════════════════════════════════════

    # Import dynamique pour éviter circular import
    from quantum.orchestrator.dataclasses_v2 import GoalkeeperProfileFBA

    return GoalkeeperProfileFBA(
        gk_name=gk_name,
        team_name=team_name,
        overall_score=round(overall_score, 1),
        dimension_scores=dimension_scores,
        status=status,
        timing_pattern=timing_pattern,
        period_ratings=period_ratings,
        period_details=period_details,
        weak_periods=weak_periods,
        strong_periods=strong_periods,
        first_half_percentile=first_half_percentile,
        second_half_percentile=second_half_percentile,
        half_differential=round(half_differential, 1),
        exploit_markets=exploit_markets,
        behavioral_tags=behavioral_tags,
        fingerprint=gk_data.get('timing_fingerprint', ''),
        narrative=narrative,
        data_quality=1.0 if sample_reliability == "HIGH" else 0.8 if sample_reliability == "MEDIUM" else 0.6,
        context_confidence=context_confidence,
        total_shots_faced=total_shots,
        sample_reliability=sample_reliability
    )


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_keeper_status_from_profile(profile: 'GoalkeeperProfileFBA') -> str:
    """Retourne le status V1 compatible depuis le profil FBA."""
    return profile.status if profile else "NORMAL"


def get_exploit_markets_from_profile(profile: 'GoalkeeperProfileFBA') -> List[Dict]:
    """Retourne les marchés exploitables depuis le profil FBA."""
    return profile.exploit_markets if profile else []


# ═══════════════════════════════════════════════════════════════════════════════
# TEST STANDALONE
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Test avec données Alisson
    test_gk_data = {
        "name": "Alisson Becker",
        "save_rate": 60.0,
        "gk_overperform": -11.14,
        "gk_percentile": 12.0,
        "total_saves": 36,
        "total_goals": 24,
        "matches": 17,
        "percentiles": {"1H_save_rate": 61.0, "2H_save_rate": 5.0},
        "vulnerabilities": ["PERIOD_0_15_WEAK", "PERIOD_46_60_WEAK"],
        "strengths": ["PERIOD_16_30_STRONG"],
        "timing_fingerprint": "GKT-71-50-24"
    }

    test_timing_data = {
        "0-15": {"save_rate": 33.3, "vs_baseline": -35.4, "shots": 6, "saves": 2},
        "16-30": {"save_rate": 92.3, "vs_baseline": 21.5, "shots": 13, "saves": 12},
        "31-45": {"save_rate": 66.7, "vs_baseline": -1.1, "shots": 6, "saves": 4},
        "46-60": {"save_rate": 50.0, "vs_baseline": -17.4, "shots": 8, "saves": 4},
        "61-75": {"save_rate": 40.0, "vs_baseline": -29.7, "shots": 10, "saves": 4},
        "76-90": {"save_rate": 72.7, "vs_baseline": 7.4, "shots": 11, "saves": 8},
        "90+": {"save_rate": 0.0, "vs_baseline": -62.7, "shots": 2, "saves": 0},
        "1H": {"save_rate": 71.4},
        "2H": {"save_rate": 50.0}
    }

    test_enriched = {"team_name": "Liverpool"}

    profile = calculate_gk_profile_senior_quant(test_gk_data, test_timing_data, test_enriched)

    print("=" * 70)
    print("PROFIL GK SENIOR QUANT - ALISSON BECKER")
    print("=" * 70)
    print(f"Overall Score: {profile.overall_score}/100")
    print(f"Status: {profile.status}")
    print(f"Timing Pattern: {profile.timing_pattern}")
    print(f"\nDimension Scores:")
    for dim, score in profile.dimension_scores.items():
        print(f"  {dim}: {score}")
    print(f"\nWeak Periods: {profile.weak_periods}")
    print(f"Strong Periods: {profile.strong_periods}")
    print(f"\nTop Exploit Markets:")
    for exploit in profile.exploit_markets[:3]:
        print(f"  {exploit['market']}: edge={exploit['adjusted_edge']} ({exploit['confidence']})")
    print(f"\nNarrative: {profile.narrative}")
    print("=" * 70)
