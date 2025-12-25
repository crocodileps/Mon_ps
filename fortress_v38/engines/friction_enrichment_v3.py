#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════════════
FRICTION ENRICHMENT V3.0 - SENIOR QUANT INSTITUTIONAL GRADE
═══════════════════════════════════════════════════════════════════════════════════════

Fichier: scripts/friction_enrichment_v3.py
Version: 3.0.0
Date: 2025-12-25

OBJECTIF:
Recalculer TOUTES les valeurs friction dans quantum_friction_matrix_v3
avec des formules Alpha 15/10 basées sur les vrais DNA des équipes.

PHILOSOPHIE:
- Friction ASYMÉTRIQUE (home vs away ≠ away vs home)
- Friction par MI-TEMPS (friction_1h ≠ friction_2h)
- Granularité 2 décimales (0.00 → 100.00)
- Formules basées sur données réelles (pas de buckets)

FORMULES ALPHA 15/10:
1. STYLE_CLASH: Matrice de clash tactique
2. TEMPO_CLASH: Diesel vs Fast Starter
3. PHYSICAL_CLASH: Pressing intensity differential
4. MENTAL_CLASH: Psyche profile × Panic factor
5. CHAOS_POTENTIAL: f(panic, volatile, killer_instinct)
6. PSYCHOLOGICAL_EDGE: Home advantage × mentality

USAGE:
    cd /home/Mon_ps
    PYTHONPATH=/home/Mon_ps python3 scripts/friction_enrichment_v3.py

═══════════════════════════════════════════════════════════════════════════════════════
"""

import json
import asyncio
import asyncpg
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import math

# Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FrictionEnrichmentV3")


# ═══════════════════════════════════════════════════════════════════════════════════════
# CONSTANTS - ALPHA 15/10
# ═══════════════════════════════════════════════════════════════════════════════════════

# Style clash matrix (asymétrique)
# Valeurs: 0.0 (pas de clash) → 1.0 (clash maximal)
STYLE_CLASH_MATRIX = {
    # Home style → Away style → Clash factor
    "offensive": {
        "offensive": 0.65,      # Les deux attaquent = match ouvert
        "defensive": 0.85,      # Attaque vs Bus = friction élevée
        "balanced": 0.55,       # Attaque vs équilibré = modéré
        "counter": 0.90,        # Attaque vs Contre = chaos (espaces)
        "possession": 0.50,     # Attaque vs Possession = contrôle
    },
    "defensive": {
        "offensive": 0.80,      # Bus vs Attaque = siège
        "defensive": 0.30,      # Bus vs Bus = 0-0 probable
        "balanced": 0.45,       # Bus vs équilibré = fermé
        "counter": 0.55,        # Bus vs Contre = attente
        "possession": 0.70,     # Bus vs Possession = frustration
    },
    "balanced": {
        "offensive": 0.60,
        "defensive": 0.50,
        "balanced": 0.50,       # Équilibré = neutre
        "counter": 0.60,
        "possession": 0.45,
    },
    "counter": {
        "offensive": 0.85,      # Contre vs Attaque = match ouvert
        "defensive": 0.60,
        "balanced": 0.55,
        "counter": 0.75,        # Contre vs Contre = chaos
        "possession": 0.80,     # Contre vs Possession = espaces
    },
    "possession": {
        "offensive": 0.55,
        "defensive": 0.75,      # Possession vs Bus = frustration
        "balanced": 0.50,
        "counter": 0.85,        # Possession vs Contre = danger
        "possession": 0.40,     # Possession vs Possession = échecs
    },
}

# Psyche clash matrix
# VOLATILE vs VOLATILE = chaos, PREDATOR vs FRAGILE = massacre
PSYCHE_CLASH_MATRIX = {
    "VOLATILE": {
        "VOLATILE": 0.95,       # Les deux paniquent = chaos
        "BALANCED": 0.60,
        "FRAGILE": 0.80,        # Volatile attaque Fragile
        "PREDATOR": 0.70,       # Volatile vs Tueur = tendu
        "RESILIENT": 0.50,
    },
    "BALANCED": {
        "VOLATILE": 0.55,
        "BALANCED": 0.45,       # Calme
        "FRAGILE": 0.50,
        "PREDATOR": 0.55,
        "RESILIENT": 0.40,
    },
    "FRAGILE": {
        "VOLATILE": 0.75,
        "BALANCED": 0.55,
        "FRAGILE": 0.65,        # Les deux peuvent craquer
        "PREDATOR": 0.90,       # Fragile vs Predator = massacre
        "RESILIENT": 0.60,
    },
    "PREDATOR": {
        "VOLATILE": 0.65,
        "BALANCED": 0.50,
        "FRAGILE": 0.85,        # Predator mange Fragile
        "PREDATOR": 0.60,       # Deux tueurs = respect mutuel
        "RESILIENT": 0.55,
    },
    "RESILIENT": {
        "VOLATILE": 0.45,
        "BALANCED": 0.35,
        "FRAGILE": 0.40,
        "PREDATOR": 0.50,
        "RESILIENT": 0.30,      # Les deux résistent = fermé
    },
}

# Match profiles basés sur la friction
MATCH_PROFILES = {
    "BOA_CONSTRICTOR": "Low friction, low chaos, one team dominates slowly",
    "CHAOS_FEST": "High friction, high chaos, unpredictable",
    "TACTICAL_CHESS": "Medium friction, low chaos, strategic battle",
    "GOAL_FEST": "High friction, medium chaos, both teams attack",
    "TRENCH_WARFARE": "Low friction, defensive stalemate",
    "EXPLOSIVE_SECOND_HALF": "Low friction_1h, high friction_2h",
    "FRONT_LOADED": "High friction_1h, low friction_2h",
    "DAVID_VS_GOLIATH": "High tier differential, upset potential",
}

# Weights for final calculation
WEIGHTS = {
    "style_clash": 0.20,
    "tempo_clash": 0.20,
    "physical_clash": 0.20,
    "mental_clash": 0.25,
    "tier_differential": 0.15,
}


# ═══════════════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class TeamDNALight:
    """Version légère du DNA pour le calcul de friction."""
    team_id: int
    team_name: str
    
    # Style
    current_style: str = "balanced"
    tier: str = "SILVER"
    tier_rank: int = 50
    
    # Temporal
    diesel_factor: float = 0.50
    fast_starter: float = 0.50
    goals_1h_avg: float = 0.5
    goals_2h_avg: float = 0.5
    
    # Physical
    pressing_intensity: float = 7.0
    stamina_profile: str = "MEDIUM"
    late_game_dominance: float = 50.0
    
    # Psyche
    psyche_profile: str = "BALANCED"
    panic_factor: float = 1.0
    killer_instinct: float = 1.0
    comeback_mentality: float = 1.0
    collapse_rate: float = 0.0
    
    # Context
    home_strength: float = 50.0
    away_strength: float = 50.0
    xg_for_avg: float = 1.2
    xg_against_avg: float = 1.2


@dataclass
class FrictionResult:
    """Résultat du calcul de friction pour une paire."""
    home_team_id: int
    away_team_id: int
    home_team_name: str
    away_team_name: str
    
    # Core friction scores (0-100, 2 décimales)
    friction_score: float = 50.0
    friction_1h: float = 50.0
    friction_2h: float = 50.0
    
    # Component scores
    style_clash: float = 50.0
    tempo_clash: float = 50.0
    mental_clash: float = 50.0
    physical_clash: float = 50.0
    
    # Derived metrics
    chaos_potential: float = 50.0
    psychological_edge: float = 0.0  # >0 = home advantage, <0 = away advantage
    
    # Predictions
    predicted_goals: float = 2.5
    predicted_btts_prob: float = 0.50
    predicted_over25_prob: float = 0.50
    
    # Match profile
    match_profile: str = "TACTICAL_CHESS"
    
    # Confidence
    confidence_level: str = "medium"


# ═══════════════════════════════════════════════════════════════════════════════════════
# FRICTION ENGINE V3.0
# ═══════════════════════════════════════════════════════════════════════════════════════

class FrictionEngineV3:
    """
    Moteur de calcul de friction Senior Quant Institutional Grade.
    
    Formules Alpha 15/10:
    - Friction asymétrique (home ≠ away)
    - Friction temporelle (1H ≠ 2H)
    - Granularité 2 décimales
    """
    
    def __init__(self):
        self.style_matrix = STYLE_CLASH_MATRIX
        self.psyche_matrix = PSYCHE_CLASH_MATRIX
        self.weights = WEIGHTS
    
    def calculate_friction(
        self,
        home_dna: TeamDNALight,
        away_dna: TeamDNALight,
    ) -> FrictionResult:
        """
        Calcule la friction complète entre deux équipes.
        
        Returns:
            FrictionResult avec toutes les métriques
        """
        # 1. STYLE CLASH
        style_clash = self._calculate_style_clash(home_dna, away_dna)
        
        # 2. TEMPO CLASH (Diesel vs Fast Starter)
        tempo_clash = self._calculate_tempo_clash(home_dna, away_dna)
        
        # 3. PHYSICAL CLASH (Pressing differential)
        physical_clash = self._calculate_physical_clash(home_dna, away_dna)
        
        # 4. MENTAL CLASH (Psyche profiles)
        mental_clash = self._calculate_mental_clash(home_dna, away_dna)
        
        # 5. TIER DIFFERENTIAL
        tier_diff = self._calculate_tier_differential(home_dna, away_dna)
        
        # 6. FRICTION TEMPORELLE (1H vs 2H)
        friction_1h, friction_2h = self._calculate_temporal_friction(home_dna, away_dna)
        
        # 7. FRICTION GLOBALE (weighted average)
        friction_score = (
            style_clash * self.weights["style_clash"] +
            tempo_clash * self.weights["tempo_clash"] +
            physical_clash * self.weights["physical_clash"] +
            mental_clash * self.weights["mental_clash"] +
            tier_diff * self.weights["tier_differential"]
        ) * 100
        
        # Clamp et round
        friction_score = round(max(0, min(100, friction_score)), 2)
        
        # 8. CHAOS POTENTIAL
        chaos_potential = self._calculate_chaos_potential(home_dna, away_dna, friction_score)
        
        # 9. PSYCHOLOGICAL EDGE
        psychological_edge = self._calculate_psychological_edge(home_dna, away_dna)
        
        # 10. PREDICTIONS
        predicted_goals = self._predict_goals(home_dna, away_dna, friction_score)
        predicted_btts = self._predict_btts(home_dna, away_dna, friction_score)
        predicted_over25 = self._predict_over25(predicted_goals)
        
        # 11. MATCH PROFILE
        match_profile = self._determine_match_profile(
            friction_score, friction_1h, friction_2h, chaos_potential, tier_diff
        )
        
        # 12. CONFIDENCE LEVEL
        confidence = self._calculate_confidence(home_dna, away_dna)
        
        return FrictionResult(
            home_team_id=home_dna.team_id,
            away_team_id=away_dna.team_id,
            home_team_name=home_dna.team_name,
            away_team_name=away_dna.team_name,
            
            friction_score=friction_score,
            friction_1h=round(friction_1h, 2),
            friction_2h=round(friction_2h, 2),
            
            style_clash=round(style_clash * 100, 2),
            tempo_clash=round(tempo_clash * 100, 2),
            mental_clash=round(mental_clash * 100, 2),
            physical_clash=round(physical_clash * 100, 2),
            
            chaos_potential=round(chaos_potential, 2),
            psychological_edge=round(psychological_edge, 2),
            
            predicted_goals=round(predicted_goals, 2),
            predicted_btts_prob=round(predicted_btts, 2),
            predicted_over25_prob=round(predicted_over25, 2),
            
            match_profile=match_profile,
            confidence_level=confidence,
        )
    
    def _calculate_style_clash(self, home: TeamDNALight, away: TeamDNALight) -> float:
        """Style clash basé sur la matrice tactique."""
        home_style = home.current_style.lower() if home.current_style else "balanced"
        away_style = away.current_style.lower() if away.current_style else "balanced"
        
        # Fallback si style inconnu
        if home_style not in self.style_matrix:
            home_style = "balanced"
        if away_style not in self.style_matrix.get(home_style, {}):
            away_style = "balanced"
        
        return self.style_matrix.get(home_style, {}).get(away_style, 0.50)
    
    def _calculate_tempo_clash(self, home: TeamDNALight, away: TeamDNALight) -> float:
        """
        Tempo clash basé sur diesel_factor differential.
        
        DIESEL vs FAST_STARTER = haute friction (rythmes opposés)
        DIESEL vs DIESEL = basse friction (même timing)
        """
        diesel_diff = abs(home.diesel_factor - away.diesel_factor)
        
        # Si les deux sont Diesel ou Fast Starter → basse friction
        # Si opposés → haute friction
        tempo_clash = diesel_diff * 1.5  # Amplifier le différentiel
        
        # Bonus si un est très Diesel et l'autre très Fast Starter
        if (home.diesel_factor > 0.65 and away.fast_starter > 0.45) or \
           (away.diesel_factor > 0.65 and home.fast_starter > 0.45):
            tempo_clash *= 1.3
        
        return min(1.0, tempo_clash)
    
    def _calculate_physical_clash(self, home: TeamDNALight, away: TeamDNALight) -> float:
        """
        Physical clash basé sur pressing intensity differential.
        
        HIGH PRESS vs LOW BLOCK = haute friction
        MEDIUM vs MEDIUM = basse friction
        """
        # Normaliser pressing (0-20 → 0-1)
        home_press = home.pressing_intensity / 20.0
        away_press = away.pressing_intensity / 20.0
        
        press_diff = abs(home_press - away_press)
        
        # Late game dominance differential
        late_diff = abs(home.late_game_dominance - away.late_game_dominance) / 100.0
        
        # Combine
        physical_clash = (press_diff * 0.7) + (late_diff * 0.3)
        
        return min(1.0, physical_clash)
    
    def _calculate_mental_clash(self, home: TeamDNALight, away: TeamDNALight) -> float:
        """
        Mental clash basé sur psyche profiles et panic factors.
        
        VOLATILE vs VOLATILE = chaos
        PREDATOR vs FRAGILE = massacre
        """
        home_psyche = home.psyche_profile.upper() if home.psyche_profile else "BALANCED"
        away_psyche = away.psyche_profile.upper() if away.psyche_profile else "BALANCED"
        
        # Fallback
        if home_psyche not in self.psyche_matrix:
            home_psyche = "BALANCED"
        if away_psyche not in self.psyche_matrix.get(home_psyche, {}):
            away_psyche = "BALANCED"
        
        base_clash = self.psyche_matrix.get(home_psyche, {}).get(away_psyche, 0.50)
        
        # Amplifier par panic factors
        panic_amplifier = (home.panic_factor + away.panic_factor) / 4.0  # Moyenne normalisée
        
        # Killer instinct differential
        killer_diff = abs(home.killer_instinct - away.killer_instinct) / 2.0
        
        mental_clash = base_clash * (1 + panic_amplifier * 0.3) + (killer_diff * 0.2)
        
        return min(1.0, mental_clash)
    
    def _calculate_tier_differential(self, home: TeamDNALight, away: TeamDNALight) -> float:
        """
        Tier differential - David vs Goliath creates friction.
        """
        tier_values = {"ELITE": 90, "GOLD": 70, "SILVER": 50, "BRONZE": 30}
        
        home_tier = tier_values.get(home.tier.upper() if home.tier else "SILVER", 50)
        away_tier = tier_values.get(away.tier.upper() if away.tier else "SILVER", 50)
        
        # Plus la différence est grande, plus il y a de friction
        tier_diff = abs(home_tier - away_tier) / 100.0
        
        # Bonus si ELITE vs BRONZE (upset potential)
        if (home.tier == "ELITE" and away.tier == "BRONZE") or \
           (away.tier == "ELITE" and home.tier == "BRONZE"):
            tier_diff *= 1.2
        
        return min(1.0, tier_diff)
    
    def _calculate_temporal_friction(
        self, 
        home: TeamDNALight, 
        away: TeamDNALight
    ) -> Tuple[float, float]:
        """
        Calcule la friction par mi-temps (Alpha 15/10).
        
        1ère MT: Si les deux sont Diesel → 0-0 probable → basse friction
        2ème MT: Panic factors s'activent → haute friction
        """
        # 1ère Mi-temps
        # Si les deux sont Diesel → match calme au début
        diesel_avg = (home.diesel_factor + away.diesel_factor) / 2
        friction_1h = (1 - diesel_avg) * 100  # Plus Diesel = moins de friction 1H
        
        # Ajustement par Fast Starter
        fast_avg = (home.fast_starter + away.fast_starter) / 2
        friction_1h = friction_1h * (1 + fast_avg * 0.3)
        
        # 2ème Mi-temps
        # Panic Factor de l'équipe dominée vs Killer Instinct de l'équipe dominante
        max_panic = max(home.panic_factor, away.panic_factor)
        max_late_dominance = max(home.late_game_dominance, away.late_game_dominance)
        
        friction_2h = (max_panic * 20) + (max_late_dominance * 0.5)
        
        # Si un est Diesel extrême → encore plus de friction en 2H
        if home.diesel_factor > 0.70 or away.diesel_factor > 0.70:
            friction_2h *= 1.2
        
        # Clamp
        friction_1h = max(0, min(100, friction_1h))
        friction_2h = max(0, min(100, friction_2h))
        
        return friction_1h, friction_2h
    
    def _calculate_chaos_potential(
        self, 
        home: TeamDNALight, 
        away: TeamDNALight,
        friction_score: float
    ) -> float:
        """
        Chaos potential = imprévisibilité du match.
        
        Facteurs: panic, volatility, collapse_rate, killer_instinct mismatch
        """
        # Base chaos from friction
        base_chaos = friction_score * 0.3
        
        # Panic amplifier
        panic_sum = home.panic_factor + away.panic_factor
        panic_chaos = panic_sum * 4
        
        # Volatility bonus
        volatile_count = 0
        if home.psyche_profile and home.psyche_profile.upper() == "VOLATILE":
            volatile_count += 1
        if away.psyche_profile and away.psyche_profile.upper() == "VOLATILE":
            volatile_count += 1
        volatility_chaos = volatile_count * 8
        
        # Collapse risk
        collapse_risk = (home.collapse_rate + away.collapse_rate) * 2
        
        # Comeback mentality adds chaos
        comeback_chaos = max(home.comeback_mentality, away.comeback_mentality) * 2
        
        chaos_potential = base_chaos + panic_chaos + volatility_chaos + collapse_risk + comeback_chaos
        
        return max(0, min(100, chaos_potential))
    
    def _calculate_psychological_edge(self, home: TeamDNALight, away: TeamDNALight) -> float:
        """
        Psychological edge: >0 = home favored, <0 = away favored
        
        Basé sur: killer_instinct, panic_factor, home/away strength
        """
        # Killer instinct differential
        killer_edge = (home.killer_instinct - away.killer_instinct) * 10
        
        # Panic factor (lower is better)
        panic_edge = (away.panic_factor - home.panic_factor) * 5
        
        # Home/Away strength
        home_edge = (home.home_strength - away.away_strength) * 0.2
        
        # Psyche profile edge
        psyche_edge = 0
        if home.psyche_profile == "PREDATOR":
            psyche_edge += 5
        if away.psyche_profile == "FRAGILE":
            psyche_edge += 5
        if home.psyche_profile == "FRAGILE":
            psyche_edge -= 5
        if away.psyche_profile == "PREDATOR":
            psyche_edge -= 5
        
        total_edge = killer_edge + panic_edge + home_edge + psyche_edge
        
        return max(-30, min(30, total_edge))
    
    def _predict_goals(
        self, 
        home: TeamDNALight, 
        away: TeamDNALight,
        friction_score: float
    ) -> float:
        """
        Prédit le nombre de buts basé sur xG et friction.
        
        Haute friction → plus de buts (match ouvert)
        Basse friction → moins de buts (fermé)
        """
        # Base xG
        home_xg = home.xg_for_avg
        away_xg = away.xg_for_avg
        
        base_goals = home_xg + away_xg
        
        # Friction multiplier (50 = neutral, >50 = more goals)
        friction_mult = 1 + (friction_score - 50) / 150
        
        # Pressing bonus (high press = more chances)
        press_bonus = (home.pressing_intensity + away.pressing_intensity) / 200
        
        # Killer instinct bonus
        killer_bonus = (home.killer_instinct + away.killer_instinct) / 10
        
        predicted = base_goals * friction_mult + press_bonus + killer_bonus
        
        return max(0.5, min(7.0, predicted))
    
    def _predict_btts(
        self, 
        home: TeamDNALight, 
        away: TeamDNALight,
        friction_score: float
    ) -> float:
        """
        Prédit la probabilité BTTS.
        """
        # Base: Si les deux ont un xG > 1.0 → BTTS probable
        home_scores_prob = 1 - math.exp(-home.xg_for_avg)
        away_scores_prob = 1 - math.exp(-away.xg_for_avg)
        
        base_btts = home_scores_prob * away_scores_prob
        
        # Friction boost (match ouvert = plus de chances pour les deux)
        friction_boost = 1 + (friction_score - 50) / 200
        
        # Panic factor boost (erreurs défensives)
        panic_boost = 1 + (home.panic_factor + away.panic_factor) / 20
        
        predicted = base_btts * friction_boost * panic_boost
        
        return max(0.1, min(0.95, predicted))
    
    def _predict_over25(self, predicted_goals: float) -> float:
        """Probabilité Over 2.5 basée sur les buts prédits (Poisson)."""
        # Approximation simple
        if predicted_goals <= 1.5:
            return 0.20
        elif predicted_goals <= 2.0:
            return 0.35
        elif predicted_goals <= 2.5:
            return 0.50
        elif predicted_goals <= 3.0:
            return 0.60
        elif predicted_goals <= 3.5:
            return 0.70
        elif predicted_goals <= 4.0:
            return 0.80
        else:
            return 0.85
    
    def _determine_match_profile(
        self,
        friction_score: float,
        friction_1h: float,
        friction_2h: float,
        chaos_potential: float,
        tier_diff: float
    ) -> str:
        """Détermine le profil du match."""
        
        # EXPLOSIVE_SECOND_HALF: friction_2h >> friction_1h
        if friction_2h > friction_1h * 1.5 and friction_2h > 60:
            return "EXPLOSIVE_SECOND_HALF"
        
        # FRONT_LOADED: friction_1h >> friction_2h
        if friction_1h > friction_2h * 1.3 and friction_1h > 50:
            return "FRONT_LOADED"
        
        # CHAOS_FEST: high chaos
        if chaos_potential > 75:
            return "CHAOS_FEST"
        
        # BOA_CONSTRICTOR: low friction, low chaos
        if friction_score < 40 and chaos_potential < 40:
            return "BOA_CONSTRICTOR"
        
        # TRENCH_WARFARE: very low friction
        if friction_score < 30:
            return "TRENCH_WARFARE"
        
        # GOAL_FEST: high friction, medium chaos
        if friction_score > 65 and chaos_potential > 50:
            return "GOAL_FEST"
        
        # DAVID_VS_GOLIATH: high tier differential
        if tier_diff > 0.5:
            return "DAVID_VS_GOLIATH"
        
        return "TACTICAL_CHESS"
    
    def _calculate_confidence(self, home: TeamDNALight, away: TeamDNALight) -> str:
        """Calcule le niveau de confiance basé sur la qualité des données."""
        # Check data completeness
        data_points = 0
        
        if home.diesel_factor != 0.50:
            data_points += 1
        if away.diesel_factor != 0.50:
            data_points += 1
        if home.pressing_intensity != 7.0:
            data_points += 1
        if away.pressing_intensity != 7.0:
            data_points += 1
        if home.panic_factor != 1.0:
            data_points += 1
        if away.panic_factor != 1.0:
            data_points += 1
        if home.killer_instinct != 1.0:
            data_points += 1
        if away.killer_instinct != 1.0:
            data_points += 1
        
        if data_points >= 6:
            return "high"
        elif data_points >= 4:
            return "medium"
        else:
            return "low"


# ═══════════════════════════════════════════════════════════════════════════════════════
# DATABASE OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════════════

async def load_all_teams(pool) -> Dict[int, TeamDNALight]:
    """Charge tous les DNA des équipes depuis la DB."""
    teams = {}
    
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                team_id,
                team_name,
                current_style,
                tier,
                tier_rank,
                temporal_dna,
                physical_dna,
                psyche_dna,
                context_dna
            FROM quantum.team_quantum_dna_v3
        """)
        
        for row in rows:
            temporal = row['temporal_dna'] or {}
            if isinstance(temporal, str): temporal = json.loads(temporal)
            physical = row['physical_dna'] or {}
            if isinstance(physical, str): physical = json.loads(physical)
            psyche = row['psyche_dna'] or {}
            if isinstance(psyche, str): psyche = json.loads(psyche)
            context = row['context_dna'] or {}
            if isinstance(context, str): context = json.loads(context)
            
            # Extract from v8_enriched if available
            v8 = temporal.get('v8_enriched', {})
            
            team = TeamDNALight(
                team_id=row['team_id'],
                team_name=row['team_name'],
                current_style=row['current_style'] or 'balanced',
                tier=row['tier'] or 'SILVER',
                tier_rank=row['tier_rank'] or 50,
                
                # Temporal
                diesel_factor=float(v8.get('diesel_factor_v8') or temporal.get('diesel_factor_v8') or temporal.get('diesel_factor') or 0.50),
                fast_starter=float(v8.get('fast_starter_v8') or temporal.get('fast_starter_v8') or temporal.get('fast_starter') or 0.50),
                goals_1h_avg=float(v8.get('goals_1h_avg') or 0.5),
                goals_2h_avg=float(v8.get('goals_2h_avg') or 0.5),
                
                # Physical
                pressing_intensity=float(physical.get('pressing_intensity') or 7.0),
                stamina_profile=physical.get('stamina_profile') or 'MEDIUM',
                late_game_dominance=float(physical.get('late_game_dominance') or 50.0),
                
                # Psyche
                psyche_profile=psyche.get('profile') or 'BALANCED',
                panic_factor=float(psyche.get('panic_factor') or 1.0),
                killer_instinct=float(psyche.get('killer_instinct') or 1.0),
                comeback_mentality=float(psyche.get('comeback_mentality') or 1.0),
                collapse_rate=float(v8.get('collapse_rate') or 0.0),
                
                # Context
                home_strength=float(context.get('home_strength') or 50.0),
                away_strength=float(context.get('away_strength') or 50.0),
                xg_for_avg=float(context.get('xg_for_avg') or 1.2),
                xg_against_avg=float(context.get('xg_against_avg') or 1.2),
            )
            
            teams[row['team_id']] = team
    
    return teams


async def update_friction_matrix(pool, results: List[FrictionResult], batch_size: int = 100):
    """Met à jour la table quantum_friction_matrix_v3 avec les nouveaux calculs."""
    
    update_query = """
        UPDATE quantum.quantum_friction_matrix_v3
        SET
            friction_score = $1,
            style_clash = $2,
            tempo_friction = $3,
            mental_clash = $4,
            tactical_friction = $5,
            psychological_edge = $6,
            chaos_potential = $7,
            confidence_level = $8,
            updated_at = NOW()
        WHERE team_home_id = $9 AND team_away_id = $10
    """
    
    async with pool.acquire() as conn:
        updated = 0
        
        for i in range(0, len(results), batch_size):
            batch = results[i:i+batch_size]
            
            for r in batch:
                try:
                    result = await conn.execute(
                        update_query,
                        r.friction_score,
                        r.style_clash,
                        r.tempo_clash,
                        r.mental_clash,
                        r.physical_clash,  # Using physical_clash for tactical_friction
                        r.psychological_edge,
                        r.chaos_potential,
                        r.confidence_level,
                        r.home_team_id,
                        r.away_team_id,
                    )
                    
                    if "UPDATE 1" in result:
                        updated += 1
                        
                except Exception as e:
                    logger.error(f"Error updating {r.home_team_name} vs {r.away_team_name}: {e}")
            
            logger.info(f"Progress: {min(i+batch_size, len(results))}/{len(results)} ({updated} updated)")
    
    return updated


# ═══════════════════════════════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════════════

async def main():
    """Exécution principale du script d'enrichissement."""
    
    print("=" * 80)
    print("🏛️ FRICTION ENRICHMENT V3.0 - SENIOR QUANT INSTITUTIONAL GRADE")
    print("=" * 80)
    
    # Connexion DB
    logger.info("📡 Connexion à PostgreSQL...")
    pool = await asyncpg.create_pool(
        'postgresql://monps_user:monps_secure_password_2024@localhost/monps_db'
    )
    
    # 1. Charger tous les DNA
    logger.info("📊 Chargement des DNA des équipes...")
    teams = await load_all_teams(pool)
    logger.info(f"   → {len(teams)} équipes chargées")
    
    # 2. Charger les paires existantes
    logger.info("🔗 Chargement des paires existantes...")
    async with pool.acquire() as conn:
        pairs = await conn.fetch("""
            SELECT team_home_id, team_away_id
            FROM quantum.quantum_friction_matrix_v3
        """)
    logger.info(f"   → {len(pairs)} paires à enrichir")
    
    # 3. Calculer la friction pour chaque paire
    logger.info("⚡ Calcul des frictions Alpha 15/10...")
    engine = FrictionEngineV3()
    results = []
    
    for i, pair in enumerate(pairs):
        home_id = pair['team_home_id']
        away_id = pair['team_away_id']
        
        if home_id not in teams or away_id not in teams:
            continue
        
        home_dna = teams[home_id]
        away_dna = teams[away_id]
        
        friction = engine.calculate_friction(home_dna, away_dna)
        results.append(friction)
        
        if (i + 1) % 500 == 0:
            logger.info(f"   → Calculé {i+1}/{len(pairs)} paires...")
    
    logger.info(f"   → {len(results)} calculs terminés")
    
    # 4. Afficher quelques exemples
    print("\n" + "=" * 80)
    print("📋 EXEMPLES DE RÉSULTATS")
    print("=" * 80)
    
    # Trouver des matchs intéressants
    examples = [
        ("Liverpool", "Manchester City"),
        ("Arsenal", "Chelsea"),
        ("Barcelona", "Real Madrid"),
        ("Burnley", "Manchester City"),
    ]
    
    for home_name, away_name in examples:
        for r in results:
            if r.home_team_name == home_name and r.away_team_name == away_name:
                print(f"\n{home_name} vs {away_name}:")
                print(f"  Friction: {r.friction_score:.2f} | 1H: {r.friction_1h:.2f} | 2H: {r.friction_2h:.2f}")
                print(f"  Style: {r.style_clash:.1f} | Tempo: {r.tempo_clash:.1f} | Mental: {r.mental_clash:.1f} | Physical: {r.physical_clash:.1f}")
                print(f"  Chaos: {r.chaos_potential:.2f} | Psych Edge: {r.psychological_edge:+.1f}")
                print(f"  Goals: {r.predicted_goals:.2f} | BTTS: {r.predicted_btts_prob:.0%} | Over2.5: {r.predicted_over25_prob:.0%}")
                print(f"  Profile: {r.match_profile} | Confidence: {r.confidence_level}")
                break
    
    # 5. Confirmer avant UPDATE
    print("\n" + "=" * 80)
    print("⚠️  CONFIRMATION REQUISE")
    print("=" * 80)
    print(f"Prêt à mettre à jour {len(results)} paires dans quantum_friction_matrix_v3")
    
    confirm = input("Continuer ? (yes/no): ")
    
    if confirm.lower() != 'yes':
        print("❌ Annulé.")
        await pool.close()
        return
    
    # 6. UPDATE
    logger.info("💾 Mise à jour de la base de données...")
    updated = await update_friction_matrix(pool, results)
    
    print("\n" + "=" * 80)
    print("✅ ENRICHISSEMENT TERMINÉ")
    print("=" * 80)
    print(f"  Paires mises à jour: {updated}/{len(results)}")
    
    # 7. Vérification
    async with pool.acquire() as conn:
        stats = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total,
                AVG(friction_score) as avg_friction,
                MIN(friction_score) as min_friction,
                MAX(friction_score) as max_friction,
                AVG(chaos_potential) as avg_chaos,
                AVG(predicted_goals) as avg_goals
            FROM quantum.quantum_friction_matrix_v3
        """)
    
    print(f"\n📊 STATISTIQUES POST-ENRICHISSEMENT:")
    print(f"  Total: {stats['total']}")
    print(f"  Friction: {stats['min_friction']:.2f} → {stats['max_friction']:.2f} (avg: {stats['avg_friction']:.2f})")
    print(f"  Chaos moyen: {stats['avg_chaos']:.2f}")
    print(f"  Goals moyen: {stats['avg_goals']:.2f}")
    
    await pool.close()
    print("\n✅ TERMINÉ !")


if __name__ == "__main__":
    asyncio.run(main())

