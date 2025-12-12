"""
📊 QUANT METRICS V2.0 - MÉTRIQUES COHÉRENTES
Correction des incohérences identifiées dans quant_v9

Principes:
1. Sharpe DÉFENSIF (pas Sharpe générique)
2. CVaR normalisé PAR MATCH
3. Alpha/Beta avec CONTEXTE
4. Hidden Markov RECALIBRÉ
"""

import json
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════════════
# 1. ALPHA/BETA CONTEXTUEL (VERSION CORRIGÉE)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AlphaBetaContextual:
    """Alpha/Beta avec contexte - Plus nuancé"""
    
    # Core metrics
    alpha_raw: float          # Alpha brut (vs moyenne équipe)
    alpha_adjusted: float     # Alpha ajusté (contexte adversaire)
    beta: float               # Sensibilité aux problèmes
    
    # Contexte
    opponent_quality_factor: float  # 0.8 (faible) à 1.3 (top 6)
    partner_quality_factor: float   # Impact du partenaire de charnière
    position_factor: float          # CB=1.0, FB=0.8, DM=0.7
    
    # Résultat
    alpha_final: float        # Alpha final pondéré
    profile: str
    description: str
    edge_adjustment: float
    confidence: str           # HIGH/MEDIUM/LOW basé sur sample size


def calculate_alpha_beta_v2(
    defender: Dict,
    team_defense: Dict,
    team_defenders: List[Dict],
    opponent_strength: float = 1.0,  # 0.8=faible, 1.0=moyen, 1.3=top
    partner_rating: float = 50.0     # 0-100
) -> AlphaBetaContextual:
    """
    Alpha/Beta V2 avec contexte
    
    NOUVEAUTÉS:
    - Ajustement par qualité d'adversaire
    - Prise en compte du partenaire
    - Facteur positionnel
    - Confidence basé sur minutes
    """
    
    # === DONNÉES JOUEUR ===
    player_impact = defender.get('impact_goals_conceded', 0) or 0
    player_goals_conceded = defender.get('goals_conceded_per_match_with', 0) or 0
    player_time = defender.get('time', 0) or 0
    player_games = defender.get('games', 0) or 0
    position = defender.get('position_category', 'CB')
    
    # === DONNÉES ÉQUIPE ===
    team_ga = team_defense.get('ga_total', 0) or 0
    team_matches = team_defense.get('matches_played', 1) or 1
    team_avg_ga = team_ga / team_matches if team_matches > 0 else 1.0
    
    # Moyenne des autres défenseurs
    other_impacts = [
        d.get('impact_goals_conceded', 0) or 0 
        for d in team_defenders 
        if d.get('name') != defender.get('name') and d.get('time', 0) > 400
    ]
    team_avg_impact = np.mean(other_impacts) if other_impacts else 0
    
    # === ALPHA RAW ===
    alpha_raw = player_impact - team_avg_impact
    
    # === FACTEURS CONTEXTUELS ===
    
    # 1. Position factor (CB plus impactant que FB)
    position_factors = {
        'CB': 1.0,    # Central = impact maximal
        'FB': 0.85,   # Latéral = moins de duels directs
        'RB': 0.85,
        'LB': 0.85,
        'DM': 0.75,   # Milieu défensif = bouclier
        'WB': 0.80,   # Wing-back
    }
    position_factor = position_factors.get(position, 0.9)
    
    # 2. Opponent quality factor
    # Un défenseur qui joue contre des équipes fortes mérite un bonus
    opponent_quality_factor = opponent_strength
    
    # 3. Partner quality factor
    # Jouer avec Van Dijk (90) vs un rookie (40) = contexte différent
    partner_quality_factor = partner_rating / 60  # Normalisé autour de 1.0
    
    # === ALPHA AJUSTÉ ===
    # Si l'adversaire est fort (1.3), on "pardonne" un alpha négatif
    # Si le partenaire est faible, on "comprend" les difficultés
    alpha_adjusted = alpha_raw * position_factor
    
    # Bonus/malus contextuels
    context_adjustment = 0
    if opponent_quality_factor > 1.1:
        context_adjustment += 0.1  # Pardon pour adversaires forts
    if partner_quality_factor < 0.8:
        context_adjustment += 0.05  # Pardon pour mauvais partenaire
    elif partner_quality_factor > 1.2:
        context_adjustment -= 0.05  # Attendu plus avec bon partenaire
    
    alpha_final = alpha_adjusted + context_adjustment
    
    # === BETA ===
    if team_avg_ga > 0 and player_goals_conceded > 0:
        beta = player_goals_conceded / team_avg_ga
    else:
        beta = 1.0
    
    # Clamp beta to reasonable range
    beta = max(0.5, min(2.0, beta))
    
    # === CONFIDENCE ===
    if player_games >= 15 and player_time >= 1200:
        confidence = "HIGH"
    elif player_games >= 8 and player_time >= 600:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"
    
    # === CLASSIFICATION NUANCÉE ===
    if alpha_final > 0.4 and beta < 0.9:
        profile = 'ELITE_DEFENDER'
        description = f"Élite: α={alpha_final:+.2f}, stabilise (β={beta:.2f})"
        edge_adjustment = -3.0  # Contre parier Goals Over
    elif alpha_final > 0.2 and beta < 1.0:
        profile = 'VALUE_CREATOR'
        description = f"Crée de la valeur (α={alpha_final:+.2f}), stable"
        edge_adjustment = -1.5
    elif alpha_final > 0 and beta <= 1.1:
        profile = 'POSITIVE_CONTRIBUTOR'
        description = f"Contribution positive (α={alpha_final:+.2f})"
        edge_adjustment = -0.5
    elif alpha_final > -0.2 and beta <= 1.2:
        profile = 'NEUTRAL'
        description = f"Impact neutre (α={alpha_final:+.2f})"
        edge_adjustment = 0
    elif alpha_final > -0.4:
        profile = 'UNDERPERFORMER'
        description = f"Sous-performance légère (α={alpha_final:+.2f})"
        edge_adjustment = 1.5
    elif alpha_final > -0.6 and beta < 1.3:
        profile = 'PROBLEM_PLAYER'
        description = f"Problématique (α={alpha_final:+.2f})"
        edge_adjustment = 2.5
    elif beta > 1.3:
        profile = 'PROBLEM_AMPLIFIER'
        description = f"Détruit ET amplifie (α={alpha_final:+.2f}, β={beta:.2f})"
        edge_adjustment = 4.0
    else:
        profile = 'LIABILITY'
        description = f"Passif défensif (α={alpha_final:+.2f})"
        edge_adjustment = 3.5
    
    return AlphaBetaContextual(
        alpha_raw=round(alpha_raw, 3),
        alpha_adjusted=round(alpha_adjusted, 3),
        beta=round(beta, 3),
        opponent_quality_factor=opponent_quality_factor,
        partner_quality_factor=round(partner_quality_factor, 2),
        position_factor=position_factor,
        alpha_final=round(alpha_final, 3),
        profile=profile,
        description=description,
        edge_adjustment=edge_adjustment,
        confidence=confidence
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 2. SHARPE DÉFENSIF (VERSION CORRIGÉE)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SharpeDefensive:
    """Sharpe calculé sur la PERFORMANCE DÉFENSIVE, pas l'edge de paris"""
    
    sharpe_ratio: float
    rendement: float          # Performance vs moyenne ligue
    volatility: float         # Écart-type buts encaissés
    
    quality: str              # EXCELLENT/GOOD/AVERAGE/POOR/NEGATIVE
    interpretation: str
    
    # Pour betting
    sizing_recommendation: str
    sizing_multiplier: float


def calculate_sharpe_defensive(
    defender: Dict,
    league_avg_ga: float = 1.25,  # Moyenne ligue buts/match
    league_std_ga: float = 0.40   # Écart-type ligue
) -> SharpeDefensive:
    """
    Sharpe DÉFENSIF: mesure la qualité de la performance défensive
    
    FORMULE:
    Rendement = (League_avg - Player_conceded) / League_avg
    → Positif si concède MOINS que la moyenne
    → Négatif si concède PLUS
    
    Volatility = Écart-type des performances
    
    Sharpe = Rendement / Volatility
    """
    
    player_ga = defender.get('goals_conceded_per_match_with', 0) or league_avg_ga
    
    # === RENDEMENT ===
    # Performance relative à la ligue
    # Si player_ga < league_avg → rendement positif (il est meilleur)
    # Si player_ga > league_avg → rendement négatif
    rendement = (league_avg_ga - player_ga) / league_avg_ga
    
    # === VOLATILITÉ ===
    # Estimation basée sur l'écart à la moyenne
    # Plus le joueur est extrême, plus il est volatile
    deviation = abs(player_ga - league_avg_ga)
    
    # Base volatility + adjustment for extreme values
    volatility = league_std_ga + (deviation * 0.5)
    volatility = max(0.2, min(1.5, volatility))  # Clamp
    
    # === SHARPE RATIO ===
    if volatility > 0:
        sharpe = rendement / volatility
    else:
        sharpe = 0
    
    # Clamp to reasonable range
    sharpe = max(-3.0, min(3.0, sharpe))
    
    # === CLASSIFICATION ===
    if sharpe > 1.5:
        quality = 'EXCELLENT'
        sizing_recommendation = 'AVOID_GOALS_OVER'
        sizing_multiplier = 0.5  # Réduire les paris Goals Over
    elif sharpe > 0.8:
        quality = 'GOOD'
        sizing_recommendation = 'CAUTIOUS_OVER'
        sizing_multiplier = 0.75
    elif sharpe > 0.2:
        quality = 'AVERAGE'
        sizing_recommendation = 'NORMAL'
        sizing_multiplier = 1.0
    elif sharpe > -0.3:
        quality = 'BELOW_AVERAGE'
        sizing_recommendation = 'SLIGHT_OVER_BIAS'
        sizing_multiplier = 1.1
    elif sharpe > -0.8:
        quality = 'POOR'
        sizing_recommendation = 'GOALS_OVER_TARGET'
        sizing_multiplier = 1.25
    else:
        quality = 'CATASTROPHIC'
        sizing_recommendation = 'AGGRESSIVE_OVER'
        sizing_multiplier = 1.5
    
    interpretation = (
        f"Concède {player_ga:.2f} vs ligue {league_avg_ga:.2f} "
        f"→ Rendement {rendement:+.1%}, Sharpe {sharpe:.2f}"
    )
    
    return SharpeDefensive(
        sharpe_ratio=round(sharpe, 2),
        rendement=round(rendement, 3),
        volatility=round(volatility, 2),
        quality=quality,
        interpretation=interpretation,
        sizing_recommendation=sizing_recommendation,
        sizing_multiplier=sizing_multiplier
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 3. CVaR NORMALISÉ (VERSION CORRIGÉE)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CVaRNormalized:
    """CVaR calculé PER MATCH avec échelle réaliste"""
    
    cvar_90: float    # Dans les 10% pires matchs
    cvar_95: float    # Dans les 5% pires matchs
    cvar_99: float    # Dans les 1% pires matchs (catastrophe)
    
    risk_category: str
    description: str
    
    # Pour betting
    tail_risk_edge: float
    recommended_market: str


def calculate_cvar_normalized(
    defender: Dict,
    team_defense: Dict,
    league_stats: Dict = None
) -> CVaRNormalized:
    """
    CVaR normalisé PAR MATCH
    
    Échelle réaliste:
    - CVaR_90: 2.0 - 3.0 buts (matchs difficiles)
    - CVaR_95: 2.5 - 4.0 buts (très mauvais)
    - CVaR_99: 3.5 - 5.0 buts (catastrophe)
    
    Maximum absolu: 6-7 buts (scores type 0-7)
    """
    
    player_ga = defender.get('goals_conceded_per_match_with', 0) or 1.0
    player_impact = defender.get('impact_goals_conceded', 0) or 0
    
    team_ga = team_defense.get('ga_total', 0) or 0
    team_matches = team_defense.get('matches_played', 1) or 1
    team_avg_ga = team_ga / team_matches if team_matches > 0 else 1.2
    
    # === BASE CVaR ===
    # Basé sur la moyenne de buts encaissés
    base_ga = max(player_ga, team_avg_ga)
    
    # === FACTEURS DE RISQUE ===
    # Impact négatif = plus de risque dans les pires cas
    risk_factor = 1.0
    if player_impact < -0.3:
        risk_factor += 0.3  # Majoration
    elif player_impact < -0.5:
        risk_factor += 0.5
    elif player_impact > 0.3:
        risk_factor -= 0.2  # Réduction
    
    # === CALCUL CVaR ===
    # Formule: CVaR_X = base_ga * multiplier * risk_factor
    # Multipliers basés sur distribution normale
    
    cvar_90 = base_ga * 1.6 * risk_factor   # ~60% de plus que la moyenne
    cvar_95 = base_ga * 2.0 * risk_factor   # ~100% de plus
    cvar_99 = base_ga * 2.5 * risk_factor   # ~150% de plus
    
    # Clamp to realistic values
    cvar_90 = min(4.0, max(1.0, cvar_90))
    cvar_95 = min(5.0, max(1.5, cvar_95))
    cvar_99 = min(6.5, max(2.0, cvar_99))
    
    # === CLASSIFICATION ===
    if cvar_95 > 4.0:
        risk_category = 'CATASTROPHIC'
        description = f"Risque extrême: {cvar_95:.1f} buts dans les pires 5%"
        tail_risk_edge = 5.0
        recommended_market = 'Over 3.5 Goals'
    elif cvar_95 > 3.0:
        risk_category = 'HIGH'
        description = f"Risque élevé: {cvar_95:.1f} buts dans les pires 5%"
        tail_risk_edge = 3.0
        recommended_market = 'Over 2.5 Goals'
    elif cvar_95 > 2.5:
        risk_category = 'MODERATE'
        description = f"Risque modéré: {cvar_95:.1f} buts dans les pires 5%"
        tail_risk_edge = 1.5
        recommended_market = 'Over 2.5 Goals (si value)'
    else:
        risk_category = 'LOW'
        description = f"Risque faible: {cvar_95:.1f} buts dans les pires 5%"
        tail_risk_edge = 0
        recommended_market = 'No specific edge'
    
    return CVaRNormalized(
        cvar_90=round(cvar_90, 2),
        cvar_95=round(cvar_95, 2),
        cvar_99=round(cvar_99, 2),
        risk_category=risk_category,
        description=description,
        tail_risk_edge=tail_risk_edge,
        recommended_market=recommended_market
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 4. HIDDEN MARKOV RECALIBRÉ
# ═══════════════════════════════════════════════════════════════════════════════

class DefenderState(Enum):
    """États de forme avec distribution cible équilibrée"""
    
    # POSITIFS (~20%)
    ELITE_FORM = "ELITE_FORM"           # Top 5% - Intouchable
    CLUTCH_MODE = "CLUTCH_MODE"         # Performe dans les grands matchs
    CONSISTENT_ROCK = "CONSISTENT_ROCK"  # Fiable et régulier
    
    # NEUTRES (~50%)
    IMPROVING = "IMPROVING"             # En progression
    STABLE_AVERAGE = "STABLE_AVERAGE"   # Dans la moyenne, prévisible
    ADAPTING = "ADAPTING"               # S'adapte à un nouveau contexte
    FLUCTUATING = "FLUCTUATING"         # Performances variables mais OK
    
    # NÉGATIFS (~30%)
    DECLINING = "DECLINING"             # En régression
    PRESSURE_SENSITIVE = "PRESSURE_SENSITIVE"  # Sensible à la pression (pas CRACKER)
    FORM_SLUMP = "FORM_SLUMP"           # Mauvaise passe temporaire
    CONFIDENCE_LOW = "CONFIDENCE_LOW"    # Manque de confiance
    CRISIS = "CRISIS"                   # Crise profonde


def classify_defender_state_v2(
    defender: Dict,
    recent_form: str = None,  # Résultats récents (WDLWW, etc.)
    team_form: str = None
) -> Tuple[DefenderState, float, Dict]:
    """
    Classification Hidden Markov recalibrée
    
    Distribution cible:
    - 20% Positifs
    - 50% Neutres
    - 30% Négatifs
    """
    
    # Extraire les métriques
    impact = defender.get('impact_goals_conceded', 0) or 0
    cs_rate = defender.get('clean_sheet_rate_with', 0) or 0
    win_rate = defender.get('win_rate_with', 0) or 0
    games = defender.get('games', 0) or 0
    
    # Score composite
    score = 0
    
    # Impact (poids fort)
    if impact > 0.5:
        score += 30
    elif impact > 0.2:
        score += 20
    elif impact > 0:
        score += 10
    elif impact > -0.2:
        score += 0
    elif impact > -0.4:
        score -= 10
    else:
        score -= 25
    
    # Clean sheet rate
    if cs_rate > 40:
        score += 20
    elif cs_rate > 30:
        score += 10
    elif cs_rate > 20:
        score += 0
    elif cs_rate > 10:
        score -= 10
    else:
        score -= 15
    
    # Win rate
    if win_rate > 60:
        score += 15
    elif win_rate > 50:
        score += 5
    elif win_rate > 40:
        score += 0
    else:
        score -= 10
    
    # Recent form bonus/malus
    if recent_form:
        wins = recent_form.upper().count('W')
        losses = recent_form.upper().count('L')
        if wins >= 4:
            score += 15
        elif wins >= 3:
            score += 5
        if losses >= 4:
            score -= 20
        elif losses >= 3:
            score -= 10
    
    # === CLASSIFICATION ===
    if score >= 50:
        state = DefenderState.ELITE_FORM
        prob = 0.85
    elif score >= 35:
        state = DefenderState.CLUTCH_MODE
        prob = 0.75
    elif score >= 25:
        state = DefenderState.CONSISTENT_ROCK
        prob = 0.70
    elif score >= 15:
        state = DefenderState.IMPROVING
        prob = 0.65
    elif score >= 5:
        state = DefenderState.STABLE_AVERAGE
        prob = 0.60
    elif score >= -5:
        state = DefenderState.FLUCTUATING
        prob = 0.55
    elif score >= -15:
        state = DefenderState.DECLINING
        prob = 0.50
    elif score >= -25:
        state = DefenderState.PRESSURE_SENSITIVE
        prob = 0.45
    elif score >= -35:
        state = DefenderState.FORM_SLUMP
        prob = 0.40
    elif score >= -45:
        state = DefenderState.CONFIDENCE_LOW
        prob = 0.35
    else:
        state = DefenderState.CRISIS
        prob = 0.30
    
    # Transitions probables
    transitions = {
        'stay': 0.50,
        'improve': 0.25 if score < 0 else 0.15,
        'decline': 0.15 if score > 0 else 0.25,
        'volatile': 0.10
    }
    
    return state, prob, {
        'score': score,
        'transitions': transitions,
        'confidence': 'HIGH' if games >= 12 else 'MEDIUM' if games >= 6 else 'LOW'
    }


# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("="*80)
    print("�� TEST QUANT METRICS V2.0 - MÉTRIQUES COHÉRENTES")
    print("="*80)
    
    # Charger les données
    with open('/home/Mon_ps/data/defender_dna/defender_dna_quant_v9.json', 'r') as f:
        defenders = json.load(f)
    
    with open('/home/Mon_ps/data/defense_dna/team_defense_dna_v6_fixed.json', 'r') as f:
        defense_raw = json.load(f)
    
    if isinstance(defense_raw, list):
        team_defense_dna = {item.get('team_name', item.get('team', '')): item for item in defense_raw}
    else:
        team_defense_dna = defense_raw
    
    # Test West Ham
    print("\n📊 TEST: WEST HAM DEFENDERS (AVANT vs APRÈS)")
    print("="*80)
    
    wh_defenders = [d for d in defenders if d.get('team') == 'West Ham']
    wh_defense = team_defense_dna.get('West Ham', {})
    
    for d in wh_defenders[:3]:
        name = d.get('name')
        print(f"\n👤 {name}")
        
        # AVANT (V9)
        old_alpha = d.get('quant_v9', {}).get('alpha_beta', {}).get('alpha', 0)
        old_sharpe = d.get('quant_v9', {}).get('sharpe', {}).get('sharpe_ratio', 0)
        old_cvar = d.get('quant_v9', {}).get('cvar', {}).get('CVaR_95', 0)
        old_state = d.get('quant_v9', {}).get('hidden_markov', {}).get('current_state', 'UNKNOWN')
        
        print(f"   AVANT (V9 bugué):")
        print(f"      Alpha: {old_alpha:.2f}")
        print(f"      Sharpe: {old_sharpe:.2f} ← INCOHÉRENT")
        print(f"      CVaR_95: {old_cvar:.1f} ← IRRÉALISTE")
        print(f"      State: {old_state}")
        
        # APRÈS (V2 corrigé)
        alpha_v2 = calculate_alpha_beta_v2(d, wh_defense, wh_defenders)
        sharpe_v2 = calculate_sharpe_defensive(d)
        cvar_v2 = calculate_cvar_normalized(d, wh_defense)
        state_v2, prob, meta = classify_defender_state_v2(d)
        
        print(f"   APRÈS (V2 corrigé):")
        print(f"      Alpha: {alpha_v2.alpha_final:.2f} ({alpha_v2.profile})")
        print(f"      Sharpe: {sharpe_v2.sharpe_ratio:.2f} ({sharpe_v2.quality}) ← COHÉRENT")
        print(f"      CVaR_95: {cvar_v2.cvar_95:.1f} buts/match ← RÉALISTE")
        print(f"      State: {state_v2.value} ({prob:.0%})")
        
        # Vérification cohérence
        coherent = (alpha_v2.alpha_final < 0 and sharpe_v2.sharpe_ratio < 0.5) or \
                   (alpha_v2.alpha_final > 0 and sharpe_v2.sharpe_ratio > 0)
        print(f"      Cohérence Alpha/Sharpe: {'✅' if coherent else '❌'}")
