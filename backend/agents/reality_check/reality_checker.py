#!/usr/bin/env python3
"""
🧠 REALITY CHECKER V1.0
========================

Moteur principal d'analyse Reality Check.
Calcule un score de réalité (0-100) et génère des warnings/adjustments.

Architecture:
┌─────────────────────────────────────────────────────────────────────────────┐
│                        REALITY CHECK PIPELINE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  📊 COLLECT         🔬 ANALYZE          📈 SCORE           🎯 OUTPUT        │
│  ┌─────────┐       ┌─────────┐        ┌─────────┐        ┌─────────┐       │
│  │ Team    │ ────► │ Class   │ ─────► │ Weight  │ ─────► │ Final   │       │
│  │ Data    │       │ Check   │        │ & Sum   │        │ Result  │       │
│  └─────────┘       └─────────┘        └─────────┘        └─────────┘       │
│       │                 │                  │                  │            │
│       ▼                 ▼                  ▼                  ▼            │
│  ┌─────────┐       ┌─────────┐        ┌─────────┐        ┌─────────┐       │
│  │ Momentum│       │ Tactical│        │ Apply   │        │ Warnings│       │
│  │ Weather │       │ Referee │        │ Factors │        │ Adjust  │       │
│  └─────────┘       └─────────┘        └─────────┘        └─────────┘       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

Scoring System (Total 100 points):
- Class/Tier Analysis:     25 points
- Tactical Matchup:        25 points
- Momentum/Psychology:     25 points
- Context (H2H, Weather):  25 points
"""

import logging
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field, asdict
from .data_service import RealityDataService, DEFAULT_TEAM_CLASS, DEFAULT_MOMENTUM

logger = logging.getLogger('RealityChecker')


# ============================================================
# CONFIGURATION & CONSTANTS
# ============================================================

# Tier Strength Values
TIER_STRENGTH = {
    'S': 95,  # Elite mondiale (Man City, Real Madrid, Bayern, PSG)
    'A': 82,  # Top européen (Liverpool, Arsenal, Barcelona, Inter...)
    'B': 68,  # Bon niveau (Tottenham, Roma, Monaco...)
    'C': 55,  # Milieu de tableau (Brighton, Sevilla, Freiburg...)
    'D': 40   # Bas de tableau (Southampton, Lecce, Bochum...)
}

# Correction factors par tier (appliqués à la confiance)
TIER_CORRECTION = {
    'S': 0.80,  # -20% confiance quand on parie CONTRE Tier S
    'A': 0.85,
    'B': 0.90,
    'C': 0.95,
    'D': 1.00
}

# Momentum Status Impact
MOMENTUM_IMPACT = {
    'on_fire': {'score_bonus': 15, 'confidence_mult': 1.15},
    'confident': {'score_bonus': 8, 'confidence_mult': 1.08},
    'stable': {'score_bonus': 0, 'confidence_mult': 1.0},
    'shaky': {'score_bonus': -8, 'confidence_mult': 0.92},
    'in_crisis': {'score_bonus': -15, 'confidence_mult': 0.85},
    'free_fall': {'score_bonus': -25, 'confidence_mult': 0.75}
}

# Tactical Upset Thresholds
TACTICAL_UPSET_HIGH = 35  # % above which tactical trap is detected
TACTICAL_UPSET_MEDIUM = 25


@dataclass
class RealityResult:
    """Résultat complet d'une analyse Reality Check"""
    # Scores par dimension (0-25 chacun)
    class_score: int = 0
    tactical_score: int = 0
    momentum_score: int = 0
    context_score: int = 0
    
    # Score final (0-100)
    reality_score: int = 50
    
    # Niveau de convergence avec les données statistiques
    convergence: str = 'neutral'  # full, partial, divergence, strong_divergence
    
    # Warnings détectés
    warnings: List[str] = field(default_factory=list)
    
    # Ajustements recommandés
    adjustments: Dict = field(default_factory=lambda: {
        'home_win_mult': 1.0,
        'away_win_mult': 1.0,
        'draw_mult': 1.0,
        'over_mult': 1.0,
        'under_mult': 1.0,
        'btts_mult': 1.0,
        'confidence_correction': 1.0
    })
    
    # Méta-données
    home_team: str = ''
    away_team: str = ''
    home_tier: str = 'C'
    away_tier: str = 'C'
    tier_gap: int = 0
    
    # Recommandation finale
    recommendation: str = ''
    
    def to_dict(self) -> Dict:
        return asdict(self)


class RealityChecker:
    """
    Moteur principal Reality Check.
    Analyse un match sous l'angle qualitatif/réalité.
    """
    
    def __init__(self, db_config: Dict = None):
        self.data_service = RealityDataService(db_config)
        logger.info("🧠 Reality Checker V1.0 initialized")
    
    def analyze_match(self, home_team: str, away_team: str, 
                      referee: str = None, match_context: Dict = None) -> RealityResult:
        """
        Analyse complète d'un match.
        
        Args:
            home_team: Nom équipe domicile
            away_team: Nom équipe extérieur
            referee: Nom arbitre (optionnel)
            match_context: Contexte additionnel (optionnel)
        
        Returns:
            RealityResult avec score, warnings et adjustments
        """
        result = RealityResult(home_team=home_team, away_team=away_team)
        
        # ═══════════════════════════════════════════════════════════════════
        # ÉTAPE 1 : COLLECTE DES DONNÉES
        # ═══════════════════════════════════════════════════════════════════
        
        home_class = self.data_service.get_team_class(home_team) or DEFAULT_TEAM_CLASS
        away_class = self.data_service.get_team_class(away_team) or DEFAULT_TEAM_CLASS
        
        home_momentum = self.data_service.get_team_momentum(home_team) or DEFAULT_MOMENTUM
        away_momentum = self.data_service.get_team_momentum(away_team) or DEFAULT_MOMENTUM
        
        h2h = self.data_service.get_head_to_head(home_team, away_team)
        weather = self.data_service.get_weather_conditions(home_team, away_team)
        
        # Tactical matchup
        home_style = home_class.get('playing_style', 'balanced')
        away_style = away_class.get('playing_style', 'balanced')
        tactical = self.data_service.get_tactical_matchup(home_style, away_style)
        
        # Referee
        referee_profile = None
        if referee:
            referee_profile = self.data_service.get_referee_profile(referee)
        
        # ═══════════════════════════════════════════════════════════════════
        # ÉTAPE 2 : ANALYSE PAR DIMENSION
        # ═══════════════════════════════════════════════════════════════════
        
        # 2.1 CLASS ANALYSIS (25 points max)
        class_result = self._analyze_class(home_class, away_class, result)
        result.class_score = class_result['score']
        result.warnings.extend(class_result['warnings'])
        result.home_tier = home_class.get('tier', 'C')
        result.away_tier = away_class.get('tier', 'C')
        result.tier_gap = class_result['tier_gap']
        
        # 2.2 TACTICAL ANALYSIS (25 points max)
        tactical_result = self._analyze_tactical(tactical, home_style, away_style, result)
        result.tactical_score = tactical_result['score']
        result.warnings.extend(tactical_result['warnings'])
        for key, val in tactical_result['adjustments'].items():
            result.adjustments[key] *= val
        
        # 2.3 MOMENTUM ANALYSIS (25 points max)
        momentum_result = self._analyze_momentum(home_momentum, away_momentum, result)
        result.momentum_score = momentum_result['score']
        result.warnings.extend(momentum_result['warnings'])
        for key, val in momentum_result['adjustments'].items():
            result.adjustments[key] *= val
        
        # 2.4 CONTEXT ANALYSIS (25 points max)
        context_result = self._analyze_context(h2h, weather, referee_profile, result)
        result.context_score = context_result['score']
        result.warnings.extend(context_result['warnings'])
        for key, val in context_result['adjustments'].items():
            result.adjustments[key] *= val
        
        # ═══════════════════════════════════════════════════════════════════
        # ÉTAPE 3 : CALCUL SCORE FINAL
        # ═══════════════════════════════════════════════════════════════════
        
        result.reality_score = (
            result.class_score + 
            result.tactical_score + 
            result.momentum_score + 
            result.context_score
        )
        
        # Déterminer convergence
        result.convergence = self._determine_convergence(result)
        
        # Générer recommandation
        result.recommendation = self._generate_recommendation(result)
        
        logger.info(f"🧠 Reality Check: {home_team} vs {away_team} = {result.reality_score}/100 [{result.convergence}]")
        
        return result
    
    def _analyze_class(self, home_class: Dict, away_class: Dict, result: RealityResult) -> Dict:
        """Analyse des classes/tiers des équipes (25 points max)"""
        score = 12  # Base neutre
        warnings = []
        
        home_tier = home_class.get('tier', 'C')
        away_tier = away_class.get('tier', 'C')
        
        home_strength = TIER_STRENGTH.get(home_tier, 55)
        away_strength = TIER_STRENGTH.get(away_tier, 55)
        
        tier_gap = home_strength - away_strength
        
        # Gros écart de classe
        if tier_gap >= 30:  # Ex: Tier S vs Tier D
            score = 22
            warnings.append(f"🏆 FORTE DOMINATION: {result.home_team} ({home_tier}) >>> {result.away_team} ({away_tier})")
            result.adjustments['home_win_mult'] *= 1.15
            result.adjustments['away_win_mult'] *= TIER_CORRECTION.get(home_tier, 0.85)
            
        elif tier_gap >= 15:  # Ex: Tier A vs Tier C
            score = 18
            warnings.append(f"⚡ AVANTAGE CLASSE: {result.home_team} ({home_tier}) > {result.away_team} ({away_tier})")
            result.adjustments['home_win_mult'] *= 1.08
            
        elif tier_gap <= -30:  # Outsider à domicile vs géant
            score = 8
            warnings.append(f"🛡️ GIANT KILLER ALERT: {result.away_team} ({away_tier}) >>> {result.home_team} ({home_tier})")
            result.adjustments['away_win_mult'] *= 1.15
            result.adjustments['home_win_mult'] *= TIER_CORRECTION.get(away_tier, 0.85)
            
        elif tier_gap <= -15:
            score = 10
            warnings.append(f"⚠️ OUTSIDER DOMICILE: {result.home_team} ({home_tier}) < {result.away_team} ({away_tier})")
            result.adjustments['away_win_mult'] *= 1.08
        
        # Big Game Factor
        home_bgf = float(home_class.get('big_game_factor', 1.0) or 1.0)
        away_bgf = float(away_class.get('big_game_factor', 1.0) or 1.0)
        
        if home_bgf > 1.1:
            score += 2
            warnings.append(f"💪 {result.home_team} performe dans les gros matchs (BGF: {home_bgf})")
        if away_bgf > 1.1:
            score += 1
            warnings.append(f"💪 {result.away_team} performe dans les gros matchs (BGF: {away_bgf})")
        
        return {'score': min(25, score), 'warnings': warnings, 'tier_gap': tier_gap}
    
    def _analyze_tactical(self, tactical: Dict, home_style: str, away_style: str, result: RealityResult) -> Dict:
        """Analyse du matchup tactique (25 points max)"""
        score = 12  # Base neutre
        warnings = []
        adjustments = {}
        
        if not tactical:
            return {'score': score, 'warnings': [], 'adjustments': {}}
        
        upset_prob = float(tactical.get('upset_probability', 25) or 25)
        btts_prob = float(tactical.get('btts_probability', 50) or 50)
        over_prob = float(tactical.get('over_25_probability', 50) or 50)
        
        # Détection piège tactique
        if upset_prob >= TACTICAL_UPSET_HIGH:
            score = 8  # Score bas = attention
            warnings.append(f"🧩 PIÈGE TACTIQUE: {away_style} contre {home_style} ({upset_prob}% upset)")
            adjustments['home_win_mult'] = 0.85
            adjustments['confidence_correction'] = 0.90
            
        elif upset_prob >= TACTICAL_UPSET_MEDIUM:
            score = 10
            warnings.append(f"⚠️ Matchup délicat: {home_style} vs {away_style}")
            adjustments['home_win_mult'] = 0.92
        
        # BTTS tendance
        if btts_prob >= 70:
            score += 3
            warnings.append(f"⚽ Matchup BTTS-friendly ({btts_prob}%)")
            adjustments['btts_mult'] = 1.10
        elif btts_prob <= 35:
            warnings.append(f"🔒 Matchup défensif probable ({btts_prob}% BTTS)")
            adjustments['btts_mult'] = 0.90
        
        # Over/Under tendance
        if over_prob >= 70:
            warnings.append(f"📈 Matchup Over-friendly ({over_prob}%)")
            adjustments['over_mult'] = 1.10
            adjustments['under_mult'] = 0.90
        elif over_prob <= 40:
            warnings.append(f"📉 Matchup Under-friendly ({100-over_prob}% Under)")
            adjustments['under_mult'] = 1.10
            adjustments['over_mult'] = 0.90
        
        return {'score': min(25, score), 'warnings': warnings, 'adjustments': adjustments}
    
    def _analyze_momentum(self, home_momentum: Dict, away_momentum: Dict, result: RealityResult) -> Dict:
        """Analyse du momentum/forme psychologique (25 points max)"""
        score = 12  # Base neutre
        warnings = []
        adjustments = {}
        
        home_status = home_momentum.get('momentum_status', 'stable')
        away_status = away_momentum.get('momentum_status', 'stable')
        
        home_impact = MOMENTUM_IMPACT.get(home_status, MOMENTUM_IMPACT['stable'])
        away_impact = MOMENTUM_IMPACT.get(away_status, MOMENTUM_IMPACT['stable'])
        
        # Home momentum
        if home_status in ['on_fire', 'confident']:
            score += home_impact['score_bonus'] // 3  # Divisé car on a 2 équipes
            warnings.append(f"🔥 {result.home_team} EN FORME ({home_status})")
            adjustments['home_win_mult'] = home_impact['confidence_mult']
            
        elif home_status in ['in_crisis', 'free_fall']:
            score += home_impact['score_bonus'] // 3  # Négatif
            warnings.append(f"📉 {result.home_team} EN CRISE ({home_status})")
            adjustments['home_win_mult'] = home_impact['confidence_mult']
        
        # Away momentum
        if away_status in ['on_fire', 'confident']:
            score -= away_impact['score_bonus'] // 3  # Inverse (danger pour domicile)
            warnings.append(f"�� {result.away_team} EN FORME ({away_status})")
            adjustments['away_win_mult'] = away_impact['confidence_mult']
            
        elif away_status in ['in_crisis', 'free_fall']:
            score -= away_impact['score_bonus'] // 3  # Inverse
            warnings.append(f"📉 {result.away_team} EN CRISE ({away_status})")
            adjustments['away_win_mult'] = away_impact['confidence_mult']
        
        # Pressure factor
        if home_momentum.get('coach_under_pressure'):
            warnings.append(f"🔴 Coach {result.home_team} sous pression")
            adjustments['home_win_mult'] = adjustments.get('home_win_mult', 1.0) * 0.95
        
        # Key player absent
        if home_momentum.get('key_player_absent'):
            warnings.append(f"🚑 {result.home_team}: Joueur clé absent")
            adjustments['home_win_mult'] = adjustments.get('home_win_mult', 1.0) * 0.90
        if away_momentum.get('key_player_absent'):
            warnings.append(f"🚑 {result.away_team}: Joueur clé absent")
            adjustments['away_win_mult'] = adjustments.get('away_win_mult', 1.0) * 0.90
        
        return {'score': max(0, min(25, score)), 'warnings': warnings, 'adjustments': adjustments}
    
    def _analyze_context(self, h2h: Dict, weather: Dict, referee: Dict, result: RealityResult) -> Dict:
        """Analyse du contexte (H2H, Météo, Arbitre) - 25 points max"""
        score = 12  # Base neutre
        warnings = []
        adjustments = {}
        
        # H2H Analysis
        if h2h:
            dominance = float(h2h.get('dominance_factor', 1.0) or 1.0)
            btts_pct = int(h2h.get('btts_percentage', 50) or 50)
            over_pct = int(h2h.get('over_25_percentage', 50) or 50)
            
            if dominance >= 1.5:
                dominant = h2h.get('dominant_team', '')
                if dominant.lower() in result.home_team.lower():
                    score += 5
                    warnings.append(f"📊 H2H: {result.home_team} domine historiquement")
                    adjustments['home_win_mult'] = adjustments.get('home_win_mult', 1.0) * 1.08
                elif dominant.lower() in result.away_team.lower():
                    score -= 3
                    warnings.append(f"📊 H2H: {result.away_team} domine historiquement")
                    adjustments['away_win_mult'] = adjustments.get('away_win_mult', 1.0) * 1.08
            
            if h2h.get('always_goals'):
                warnings.append(f"⚽ H2H: Matchs toujours avec buts (BTTS {btts_pct}%)")
                adjustments['btts_mult'] = adjustments.get('btts_mult', 1.0) * 1.10
                
            if h2h.get('low_scoring'):
                warnings.append(f"🔒 H2H: Matchs peu de buts (Over 2.5: {over_pct}%)")
                adjustments['under_mult'] = adjustments.get('under_mult', 1.0) * 1.10
        
        # Weather Analysis
        if weather:
            impact = weather.get('weather_impact_level', 'none')
            adjustment = float(weather.get('over_under_adjustment', 0) or 0)
            
            if impact in ['high', 'extreme']:
                warnings.append(f"🌧️ MÉTÉO: Impact {impact} - {weather.get('weather_type', 'unknown')}")
                if adjustment < 0:
                    adjustments['over_mult'] = adjustments.get('over_mult', 1.0) * (1 + adjustment/2)
                    adjustments['under_mult'] = adjustments.get('under_mult', 1.0) * (1 - adjustment/2)
        
        # Referee Analysis
        if referee:
            tendency = referee.get('under_over_tendency', 'neutral')
            penalty_freq = float(referee.get('penalty_frequency', 25) or 25)
            
            if tendency == 'over':
                warnings.append(f"👨‍⚖️ Arbitre {referee.get('referee_name', '')}: Tendance Over")
                adjustments['over_mult'] = adjustments.get('over_mult', 1.0) * 1.05
            elif tendency == 'under':
                warnings.append(f"👨‍⚖️ Arbitre {referee.get('referee_name', '')}: Tendance Under")
                adjustments['under_mult'] = adjustments.get('under_mult', 1.0) * 1.05
            
            if penalty_freq >= 30:
                warnings.append(f"⚠️ Arbitre penalty-friendly ({penalty_freq}%)")
        
        return {'score': max(0, min(25, score)), 'warnings': warnings, 'adjustments': adjustments}
    
    def _determine_convergence(self, result: RealityResult) -> str:
        """Détermine le niveau de convergence données vs réalité"""
        score = result.reality_score
        
        if score >= 70:
            return 'full_convergence'
        elif score >= 55:
            return 'partial_convergence'
        elif score >= 40:
            return 'divergence'
        else:
            return 'strong_divergence'
    
    def _generate_recommendation(self, result: RealityResult) -> str:
        """Génère une recommandation textuelle"""
        if result.convergence == 'full_convergence':
            return f"✅ CONVERGENCE: Données et réalité alignées. Confiance élevée."
        elif result.convergence == 'partial_convergence':
            return f"🟡 PARTIELLE: Vérifier les warnings avant de parier."
        elif result.convergence == 'divergence':
            return f"⚠️ DIVERGENCE: Les données ne reflètent pas la réalité. Prudence."
        else:
            return f"🔴 FORTE DIVERGENCE: Éviter de parier contre les fondamentaux."


# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================

def quick_check(home_team: str, away_team: str) -> Dict:
    """
    Check rapide pour intégration simple.
    
    Usage:
        from agents.reality_check import quick_check
        result = quick_check("Manchester City", "Southampton")
    """
    checker = RealityChecker()
    result = checker.analyze_match(home_team, away_team)
    return result.to_dict()
