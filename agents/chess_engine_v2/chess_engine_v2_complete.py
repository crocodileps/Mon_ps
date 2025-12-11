#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     CHESS ENGINE V2 - DEFENSE SHORTING                       ║
║                                                                              ║
║  Module unifié pour l'analyse quantitative des défenses et la génération    ║
║  de signaux de paris sur l'effondrement défensif.                           ║
║                                                                              ║
║  Auteur: Mya & Claude                                                        ║
║  Version: 2.0.0                                                              ║
║  Date: 2025-12-11                                                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

ARCHITECTURE:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │  COUCHE 1: DATA LOADERS                                                 │
    │  ├── load_defenders()       → Defender DNA V9                           │
    │  ├── load_attack_power()    → Team Attack Power V2                      │
    │  └── load_referee_profiles()→ Referee Catalyst Profiles                 │
    │                                                                         │
    │  COUCHE 2: CALCULATORS                                                  │
    │  ├── CollapseCalculatorV4   → Probabilité d'effondrement                │
    │  ├── CatalystEngine         → Amplification arbitrale                   │
    │  └── TimingDNAEngine        → Classification temporelle                 │
    │                                                                         │
    │  COUCHE 3: SIGNAL GENERATOR                                             │
    │  └── DefenseShortingEngine  → Orchestration complète                    │
    └─────────────────────────────────────────────────────────────────────────┘

USAGE:
    from chess_engine_v2_complete import DefenseShortingEngine
    
    engine = DefenseShortingEngine()
    analysis = engine.full_analysis(
        defending_team="West Ham",
        opponent_team="Manchester City",
        referee_name="Michael Oliver",
        is_home=True,
        is_derby=False,
        days_since_last_match=7
    )
    print(analysis)
"""

import json
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES & CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

class Config:
    """Configuration centralisée du Chess Engine V2"""
    
    # Chemins des données
    DATA_ROOT = Path("/home/Mon_ps/data")
    DEFENDER_DNA_PATH = DATA_ROOT / "defender_dna/defender_dna_quant_v9.json"
    ATTACK_POWER_PATH = DATA_ROOT / "quantum_v2/attack_power_v2.json"
    REFEREE_PROFILES_PATH = DATA_ROOT / "quantum_v2/referee_catalyst_profiles.json"
    TIMING_DNA_PATH = DATA_ROOT / "quantum_v2/timing_dna_profiles.json"
    
    # Constantes de calcul
    LEAGUE_AVG_GA = 1.37
    MAX_COLLAPSE_PROB = 0.95  # Cap à 95% (jamais 100% certain)
    MIN_COLLAPSE_PROB = 0.10
    
    # Odds par défaut pour calculs EV/Kelly
    DEFAULT_ODDS = 1.80
    
    # Plafonds par tier adverse
    TIER_LIMITS = {
        'ELITE': {'floor': 35, 'ceiling': 85},
        'STRONG': {'floor': 25, 'ceiling': 75},
        'AVERAGE': {'floor': 20, 'ceiling': 65},
        'WEAK': {'floor': 15, 'ceiling': 55},
        'RELEGATION': {'floor': 10, 'ceiling': 45}
    }
    
    # Mapping Panic Score par état Markov
    PANIC_BY_STATE = {
        'ELITE_FORM': 5, 'CLUTCH_MODE': 10, 'CONSISTENT_ROCK': 15,
        'IMPROVING': 25, 'STABLE_AVERAGE': 35, 'ADAPTING': 40,
        'FLUCTUATING': 45, 'INCONSISTENT_NEUTRAL': 50,
        'DECLINING': 60, 'PRESSURE_CRACKER': 75, 'SLUMP': 80,
        'CONFIDENCE_CRISIS': 85, 'TOTAL_COLLAPSE': 95,
        'LIABILITY_CONFIRMED': 90, 'CRISIS': 90, 'UNKNOWN': 50
    }


class Signal(Enum):
    """Signaux de trading générés par le moteur"""
    AGGRESSIVE_SHORT = "AGGRESSIVE_SHORT"
    STANDARD_SHORT = "STANDARD_SHORT"
    VALUE_BET = "VALUE_BET"
    MONITOR = "MONITOR"
    LEAN_SKIP = "LEAN_SKIP"
    SKIP = "SKIP"
    NO_DATA = "NO_DATA"


class TimingProfile(Enum):
    """Profils de timing pour les équipes"""
    EARLY_COLLAPSE = "EARLY_COLLAPSE"
    LATE_COLLAPSE = "LATE_COLLAPSE"
    STEADY_DECLINE = "STEADY_DECLINE"
    RANDOM_CHAOS = "RANDOM_CHAOS"
    NEUTRAL = "NEUTRAL"
    UNKNOWN = "UNKNOWN"


class RefereeProfile(Enum):
    """Profils d'arbitres"""
    CARD_HAPPY = "CARD_HAPPY"
    STRICT = "STRICT"
    NEUTRAL = "NEUTRAL"
    LENIENT = "LENIENT"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DefenderProfile:
    """Profil d'un défenseur"""
    name: str
    team: str
    position: str
    minutes_played: int
    alpha_league: float
    panic_score: int
    markov_state: str
    cvar_95: float
    is_pressure_cracker: bool = False
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DefenderProfile':
        """Crée un DefenderProfile depuis les données brutes"""
        quant = data.get('quant_v9', {})
        markov = quant.get('hidden_markov', {})
        cvar_data = quant.get('cvar', {})
        
        state = markov.get('current_state', 'STABLE_AVERAGE')
        
        # Calculer alpha_league
        player_ga = data.get('goals_conceded_per_match_with', 0) or Config.LEAGUE_AVG_GA
        alpha_league = (Config.LEAGUE_AVG_GA - player_ga) / Config.LEAGUE_AVG_GA
        
        return cls(
            name=data.get('player', 'Unknown'),
            team=data.get('team', ''),
            position=data.get('position', ''),
            minutes_played=data.get('time', 0),
            alpha_league=alpha_league,
            panic_score=Config.PANIC_BY_STATE.get(state, 50),
            markov_state=state,
            cvar_95=min(5.0, cvar_data.get('CVaR_95', 3.0) / 2),  # Normalisé
            is_pressure_cracker=state in ['PRESSURE_CRACKER', 'CONFIDENCE_CRISIS', 'TOTAL_COLLAPSE', 'SLUMP']
        )


@dataclass
class CollapseResult:
    """Résultat du calcul de collapse"""
    collapse_prob: float
    signal: Signal
    confidence: str
    
    # Composantes
    base_score: float
    total_bonus: float
    raw_score: float
    
    # Métriques défensives
    liability: float
    crisis_count: int
    avg_panic: float
    avg_alpha: float
    
    # Métriques adverses
    opponent_tier: str
    attack_power: float
    
    # Bonuses détaillés
    bonuses: List[Tuple[str, float]]
    
    # Trading metrics
    ev: float
    edge: float
    kelly_half: float
    
    # Marchés recommandés
    markets: List[str]


@dataclass
class CatalystResult:
    """Résultat du Catalyst Engine"""
    catalyst_score: float
    chain_reaction_prob: float
    referee_profile: str
    card_impact: float
    pressure_crackers_count: int
    pressure_cracker_names: List[str]
    reasoning: List[str]
    additional_markets: List[dict]
    amplified_collapse: float


@dataclass
class TimingResult:
    """Résultat du Timing DNA Engine"""
    timing_profile: TimingProfile
    optimal_entry: str
    decay_factor: float
    time_curve: Dict[str, float]
    reasoning: str
    is_live_trap: bool
    live_trap_details: Optional[dict] = None


@dataclass
class FullAnalysis:
    """Analyse complète d'un match"""
    defending_team: str
    opponent_team: str
    referee_name: Optional[str]
    
    # Résultats des 3 moteurs
    collapse: CollapseResult
    catalyst: Optional[CatalystResult]
    timing: TimingResult
    
    # Synthèse finale
    final_collapse_prob: float
    final_signal: Signal
    recommended_action: str
    all_markets: List[dict]
    
    # Alertes
    alerts: List[str]


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADERS
# ═══════════════════════════════════════════════════════════════════════════════

class DataLoader:
    """Gestionnaire de chargement des données"""
    
    _cache: Dict[str, Any] = {}
    
    @classmethod
    def load_defenders(cls) -> Dict[str, List[DefenderProfile]]:
        """Charge et structure les données des défenseurs par équipe"""
        if 'defenders' in cls._cache:
            return cls._cache['defenders']
        
        try:
            with open(Config.DEFENDER_DNA_PATH, 'r') as f:
                raw_data = json.load(f)
        except FileNotFoundError:
            logger.warning(f"Fichier non trouvé: {Config.DEFENDER_DNA_PATH}")
            return {}
        
        defenders_by_team = {}
        for d in raw_data:
            team = d.get('team', '')
            if team not in defenders_by_team:
                defenders_by_team[team] = []
            defenders_by_team[team].append(DefenderProfile.from_dict(d))
        
        cls._cache['defenders'] = defenders_by_team
        return defenders_by_team
    
    @classmethod
    def load_attack_power(cls) -> Dict[str, dict]:
        """Charge les données Attack Power V2"""
        if 'attack_power' in cls._cache:
            return cls._cache['attack_power']
        
        try:
            with open(Config.ATTACK_POWER_PATH, 'r') as f:
                data = json.load(f)
                cls._cache['attack_power'] = data.get('teams', {})
                return cls._cache['attack_power']
        except FileNotFoundError:
            logger.warning(f"Fichier non trouvé: {Config.ATTACK_POWER_PATH}")
            return {}
    
    @classmethod
    def load_referee_profiles(cls) -> Dict[str, dict]:
        """Charge les profils d'arbitres"""
        if 'referees' in cls._cache:
            return cls._cache['referees']
        
        try:
            with open(Config.REFEREE_PROFILES_PATH, 'r') as f:
                cls._cache['referees'] = json.load(f)
                return cls._cache['referees']
        except FileNotFoundError:
            logger.warning(f"Fichier non trouvé: {Config.REFEREE_PROFILES_PATH}")
            return {}
    
    @classmethod
    def load_timing_profiles(cls) -> Dict[str, dict]:
        """Charge les profils de timing"""
        if 'timing' in cls._cache:
            return cls._cache['timing']
        
        try:
            with open(Config.TIMING_DNA_PATH, 'r') as f:
                cls._cache['timing'] = json.load(f)
                return cls._cache['timing']
        except FileNotFoundError:
            logger.warning(f"Fichier non trouvé: {Config.TIMING_DNA_PATH}")
            return {}
    
    @classmethod
    def clear_cache(cls):
        """Vide le cache"""
        cls._cache.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# COLLAPSE CALCULATOR V4
# ═══════════════════════════════════════════════════════════════════════════════

class CollapseCalculatorV4:
    """
    Calculateur de probabilité d'effondrement défensif V4
    
    Formule:
        Base Score (20-50%) + Bonus Additifs (plafonnés)
        → Appliqué dans les limites du tier adverse
        → Capped à 95% maximum
    """
    
    def __init__(self):
        self.defenders = DataLoader.load_defenders()
        self.attack_power = DataLoader.load_attack_power()
    
    def get_team_starters(self, team: str, min_minutes: int = 500) -> List[DefenderProfile]:
        """Récupère les 5 titulaires principaux d'une équipe"""
        team_defenders = self.defenders.get(team, [])
        starters = sorted(
            [d for d in team_defenders if d.minutes_played > min_minutes],
            key=lambda x: -x.minutes_played
        )[:5]
        return starters
    
    def calculate(
        self,
        defending_team: str,
        opponent_team: str,
        is_home: bool = True,
        is_derby: bool = False,
        days_since_last_match: int = 7
    ) -> CollapseResult:
        """
        Calcule la probabilité de collapse avec nuances
        
        Args:
            defending_team: Équipe qui défend
            opponent_team: Équipe qui attaque
            is_home: Match à domicile?
            is_derby: Derby?
            days_since_last_match: Jours depuis dernier match
            
        Returns:
            CollapseResult avec tous les détails
        """
        
        # ═══════════════════════════════════════════════════════════════════
        # 1. DONNÉES
        # ═══════════════════════════════════════════════════════════════════
        
        starters = self.get_team_starters(defending_team)
        
        if not starters:
            return CollapseResult(
                collapse_prob=0.30, signal=Signal.NO_DATA, confidence='LOW',
                base_score=30, total_bonus=0, raw_score=30,
                liability=0, crisis_count=0, avg_panic=50, avg_alpha=0,
                opponent_tier='UNKNOWN', attack_power=50,
                bonuses=[], ev=0, edge=0, kelly_half=0, markets=[]
            )
        
        # Attack Power adverse
        opp_data = self.attack_power.get(opponent_team, {})
        attack_power = opp_data.get('attack_power', 50)
        opp_tier = opp_data.get('tier', 'AVERAGE')
        
        # ═══════════════════════════════════════════════════════════════════
        # 2. MÉTRIQUES DÉFENSIVES
        # ═══════════════════════════════════════════════════════════════════
        
        alphas = [d.alpha_league for d in starters]
        panics = [d.panic_score for d in starters]
        
        avg_alpha = np.mean(alphas)
        avg_panic = np.mean(panics)
        
        # Liability: 0 (parfait) à 1 (catastrophique)
        liability = max(0, min(1, -avg_alpha * 1.5))
        
        # Crisis count
        crisis_count = sum(1 for a in alphas if a < -0.3)
        
        # Base score: entre 20% et 50%
        base_score = 20 + (liability * 30)
        
        # ═══════════════════════════════════════════════════════════════════
        # 3. BONUS ADDITIFS (avec plafonds!)
        # ═══════════════════════════════════════════════════════════════════
        
        bonuses = []
        
        # --- Crisis Count Bonus (max +25%) ---
        if crisis_count >= 4:
            bonuses.append(('🚨 Crise systémique', 25))
        elif crisis_count >= 3:
            bonuses.append(('⚠️ Multiple liabilities', 18))
        elif crisis_count >= 2:
            bonuses.append(('⚠️ Paire fragile', 10))
        
        # --- Panic Bonus (max +20%) ---
        if avg_panic >= 80:
            bonuses.append(('😰 Panique extrême', 20))
        elif avg_panic >= 70:
            bonuses.append(('😟 Panique élevée', 12))
        elif avg_panic >= 60:
            bonuses.append(('😐 Tension', 5))
        
        # --- Opponent Tier Bonus (max +15% / min -15%) ---
        if opp_tier == 'ELITE':
            bonuses.append((f'⚡ vs {opponent_team} (ELITE)', 15))
        elif opp_tier == 'STRONG':
            bonuses.append((f'💪 vs {opponent_team} (STRONG)', 8))
        elif opp_tier == 'WEAK':
            bonuses.append((f'😴 vs {opponent_team} (WEAK)', -10))
        elif opp_tier == 'RELEGATION':
            bonuses.append((f'🐢 vs {opponent_team} (RELEGATION)', -15))
        
        # --- Volatility Bonus (max +10%) ---
        cvars = [d.cvar_95 for d in starters]
        max_cvar = max(cvars) if cvars else 3.0
        if max_cvar >= 4.5:
            bonuses.append(('💣 Volatilité extrême', 10))
        elif max_cvar >= 4.0:
            bonuses.append(('📊 Haute volatilité', 5))
        
        # --- Context Bonuses ---
        if not is_home:
            bonuses.append(('🏟️ Extérieur', 5))
        if is_derby:
            bonuses.append(('🔥 Derby', 5))
        if days_since_last_match < 4:
            bonuses.append(('😓 Fatigue (<4j)', 5))
        
        # ═══════════════════════════════════════════════════════════════════
        # 4. CALCUL FINAL
        # ═══════════════════════════════════════════════════════════════════
        
        total_bonus = sum(b[1] for b in bonuses)
        raw_score = base_score + total_bonus
        
        # Appliquer floor et ceiling du tier
        limits = Config.TIER_LIMITS.get(opp_tier, Config.TIER_LIMITS['AVERAGE'])
        collapse_pct = max(limits['floor'], min(limits['ceiling'], raw_score))
        
        # Convertir en probabilité et cap à 95%
        collapse_prob = min(Config.MAX_COLLAPSE_PROB, collapse_pct / 100)
        collapse_prob = max(Config.MIN_COLLAPSE_PROB, collapse_prob)
        
        # ═══════════════════════════════════════════════════════════════════
        # 5. KELLY & EV
        # ═══════════════════════════════════════════════════════════════════
        
        implied_odds = Config.DEFAULT_ODDS
        implied_prob = 1 / implied_odds
        edge = collapse_prob - implied_prob
        ev = collapse_prob * implied_odds - 1
        
        if edge > 0 and implied_odds > 1:
            kelly_full = edge / (implied_odds - 1)
            kelly_half = kelly_full / 2
        else:
            kelly_half = 0
        
        # ═══════════════════════════════════════════════════════════════════
        # 6. SIGNAL
        # ═══════════════════════════════════════════════════════════════════
        
        # Confidence
        strong_signals = sum([
            crisis_count >= 3,
            avg_panic >= 70,
            opp_tier in ['ELITE', 'STRONG'],
            max_cvar >= 4.0
        ])
        confidence = ['LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH'][min(3, strong_signals)]
        
        # Signal
        if collapse_prob >= 0.70 and ev >= 0.15 and confidence in ['HIGH', 'VERY_HIGH']:
            signal = Signal.AGGRESSIVE_SHORT
        elif collapse_prob >= 0.60 and ev >= 0.08:
            signal = Signal.STANDARD_SHORT
        elif collapse_prob >= 0.50 and ev >= 0.03:
            signal = Signal.VALUE_BET
        elif collapse_prob >= 0.40:
            signal = Signal.MONITOR
        elif collapse_prob >= 0.30:
            signal = Signal.LEAN_SKIP
        else:
            signal = Signal.SKIP
        
        # ═══════════════════════════════════════════════════════════════════
        # 7. MARCHÉS
        # ═══════════════════════════════════════════════════════════════════
        
        markets = []
        if collapse_prob >= 0.60 and opp_tier in ['ELITE', 'STRONG']:
            markets.append(f'{opponent_team} Over 2.5 Team Goals')
        if collapse_prob >= 0.50:
            markets.append(f'{opponent_team} Over 1.5 Team Goals')
        if collapse_prob >= 0.55 and opp_tier != 'RELEGATION':
            markets.append('Match Over 2.5 Goals')
        if collapse_prob >= 0.65 and crisis_count >= 3:
            markets.append('Penalty in Match')
        
        return CollapseResult(
            collapse_prob=round(collapse_prob, 3),
            signal=signal,
            confidence=confidence,
            base_score=round(base_score, 1),
            total_bonus=round(total_bonus, 1),
            raw_score=round(raw_score, 1),
            liability=round(liability, 2),
            crisis_count=crisis_count,
            avg_panic=round(avg_panic, 1),
            avg_alpha=round(avg_alpha, 3),
            opponent_tier=opp_tier,
            attack_power=round(attack_power, 1),
            bonuses=bonuses,
            ev=round(ev * 100, 1),
            edge=round(edge * 100, 1),
            kelly_half=round(kelly_half * 100, 2),
            markets=markets
        )


# ═══════════════════════════════════════════════════════════════════════════════
# CATALYST ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class CatalystEngine:
    """
    Moteur d'analyse du catalyseur arbitral V2
    
    L'arbitre est "l'étincelle" qui peut:
    - AMPLIFIER: CARD_HAPPY/STRICT + défense fragile = Carton → Panique → Effondrement
    - RÉDUIRE: LENIENT protège la défense fragile = Moins de pression → Collapse réduit
    """
    
    def __init__(self):
        self.referee_profiles = DataLoader.load_referee_profiles()
        self.defenders = DataLoader.load_defenders()
    
    def calculate(
        self,
        defending_team: str,
        referee_name: str,
        collapse_prob: float
    ) -> CatalystResult:
        """
        Calcule l'amplification/réduction due à l'arbitre
        
        AMÉLIORATION V2:
        - CARD_HAPPY/STRICT = Amplification (+5 à +15%)
        - LENIENT = Réduction (-5 à -10%) + Marchés inversés
        
        Args:
            defending_team: Équipe qui défend
            referee_name: Nom de l'arbitre
            collapse_prob: Probabilité de collapse de base
            
        Returns:
            CatalystResult avec détails
        """
        
        # Profil arbitre
        ref_profile = self.referee_profiles.get(referee_name, {})
        card_impact = ref_profile.get('card_impact', 0)
        penalty_impact = ref_profile.get('penalty_impact', 0)
        ref_type = ref_profile.get('profile', 'NEUTRAL')
        
        # Pressure crackers dans la défense
        team_defenders = self.defenders.get(defending_team, [])
        starters = sorted(
            [d for d in team_defenders if d.minutes_played > 500],
            key=lambda x: -x.minutes_played
        )[:5]
        
        pressure_crackers = [d for d in starters if d.is_pressure_cracker]
        
        # ═══════════════════════════════════════════════════════════════════
        # CATALYST SCORE (peut être POSITIF ou NÉGATIF)
        # ═══════════════════════════════════════════════════════════════════
        
        catalyst_base = 0
        reasoning = []
        
        # CARD_HAPPY = Forte amplification
        if ref_type == 'CARD_HAPPY' and len(pressure_crackers) >= 2:
            catalyst_base = 0.35
            reasoning.append(f"🔥 Arbitre CARD_HAPPY ({referee_name}) + {len(pressure_crackers)} PRESSURE_CRACKERS")
        elif ref_type == 'CARD_HAPPY':
            catalyst_base = 0.20
            reasoning.append(f"🔥 Arbitre CARD_HAPPY ({referee_name})")
        
        # STRICT = Amplification modérée
        elif ref_type == 'STRICT' and len(pressure_crackers) >= 2:
            catalyst_base = 0.20
            reasoning.append(f"⚡ Arbitre STRICT ({referee_name}) + défense fragile")
        elif ref_type == 'STRICT':
            catalyst_base = 0.10
            reasoning.append(f"⚡ Arbitre STRICT ({referee_name})")
        
        # LENIENT = Réduction (NOUVEAU!)
        elif ref_type == 'LENIENT' and len(pressure_crackers) >= 2:
            catalyst_base = -0.15  # NÉGATIF = réduit le collapse
            reasoning.append(f"🛡️ Arbitre LENIENT ({referee_name}) protège la défense fragile")
        elif ref_type == 'LENIENT':
            catalyst_base = -0.10
            reasoning.append(f"🟢 Arbitre LENIENT ({referee_name}) = moins de pression")
        
        # NEUTRAL avec pressure crackers
        elif len(pressure_crackers) >= 3:
            catalyst_base = 0.10
            reasoning.append(f"⚠️ {len(pressure_crackers)} PRESSURE_CRACKERS, arbitre neutre")
        elif len(pressure_crackers) >= 2:
            catalyst_base = 0.05
            reasoning.append(f"⚠️ Défense fragile, arbitre neutre")
        
        # Penalty Impact bonus/malus
        if penalty_impact > 0.05 and collapse_prob > 0.6:
            catalyst_base += 0.08
            reasoning.append(f"📍 Arbitre généreux en penalties")
        elif penalty_impact < -0.03 and ref_type == 'LENIENT':
            catalyst_base -= 0.05
            reasoning.append(f"📍 Arbitre avare en penalties")
        
        # Synergie collapse × catalyst
        if collapse_prob > 0.7:
            synergy_mult = 1.3
        elif collapse_prob > 0.5:
            synergy_mult = 1.1
        else:
            synergy_mult = 0.9
        
        # Catalyst final (peut être négatif!)
        catalyst_final = catalyst_base * synergy_mult
        catalyst_final = max(-0.25, min(0.5, catalyst_final))  # Bornes: -25% à +50%
        
        # ═══════════════════════════════════════════════════════════════════
        # CHAIN REACTION
        # ═══════════════════════════════════════════════════════════════════
        
        if ref_type == 'CARD_HAPPY':
            card_trigger_prob = 0.35
        elif ref_type == 'STRICT':
            card_trigger_prob = 0.25
        elif ref_type == 'LENIENT':
            card_trigger_prob = 0.08  # Très bas
        else:
            card_trigger_prob = 0.15
        
        card_trigger_prob *= (1 + len(pressure_crackers) * 0.1)
        chain_reaction_prob = collapse_prob * card_trigger_prob * synergy_mult
        chain_reaction_prob = min(0.4, chain_reaction_prob)
        
        # ═══════════════════════════════════════════════════════════════════
        # MARCHÉS ADDITIONNELS (selon profil arbitre)
        # ═══════════════════════════════════════════════════════════════════
        
        additional_markets = []
        
        if ref_type in ['CARD_HAPPY', 'STRICT']:
            # ─── Marchés pour arbitre SÉVÈRE ───
            
            # Penalty
            if catalyst_final > 0.15 and collapse_prob > 0.6:
                additional_markets.append({
                    'market': 'Penalty Awarded: YES',
                    'confidence': 'HIGH' if ref_type == 'CARD_HAPPY' else 'MEDIUM',
                    'edge_boost': '+3-5%'
                })
            
            # Cards Over
            if len(pressure_crackers) >= 1:
                cards_line = 3 + max(0, int(card_impact))
                additional_markets.append({
                    'market': f'Cards Over {cards_line}.5',
                    'confidence': 'HIGH' if ref_type == 'CARD_HAPPY' else 'MEDIUM',
                    'edge_boost': '+4-6%'
                })
            
            # Red Card
            if chain_reaction_prob > 0.20 and collapse_prob > 0.65:
                additional_markets.append({
                    'market': 'Red Card in Match: YES',
                    'confidence': 'MEDIUM',
                    'edge_boost': '+2-4%'
                })
            
            # Joueurs spécifiques à cartonner
            for pc in pressure_crackers[:2]:
                additional_markets.append({
                    'market': f"{pc.name} to be Carded",
                    'confidence': 'MEDIUM' if ref_type == 'STRICT' else 'HIGH',
                    'edge_boost': '+5-8%'
                })
        
        elif ref_type == 'LENIENT':
            # ─── Marchés INVERSÉS pour arbitre PERMISSIF ───
            
            # Cards Under
            cards_line = 3 + int(card_impact)  # Sera négatif, donc < 3
            cards_under_line = max(2, min(3, cards_line))
            additional_markets.append({
                'market': f'Cards Under {cards_under_line}.5',
                'confidence': 'HIGH',
                'edge_boost': '+4-6%'
            })
            
            # No Red Card
            additional_markets.append({
                'market': 'No Red Card in Match',
                'confidence': 'HIGH',
                'edge_boost': '+3-5%'
            })
            
            # No Penalty (si collapse pas trop haut)
            if collapse_prob < 0.75:
                additional_markets.append({
                    'market': 'No Penalty in Match',
                    'confidence': 'MEDIUM',
                    'edge_boost': '+2-4%'
                })
            
            # Both Teams Score possible (moins de fautes = plus de jeu)
            if collapse_prob > 0.5:
                additional_markets.append({
                    'market': 'Both Teams to Score: YES',
                    'confidence': 'LOW',
                    'edge_boost': '+1-3%'
                })
        
        else:
            # ─── NEUTRAL: marchés de base si forte probabilité ───
            if collapse_prob > 0.7 and len(pressure_crackers) >= 2:
                additional_markets.append({
                    'market': 'Cards Over 3.5',
                    'confidence': 'LOW',
                    'edge_boost': '+2-3%'
                })
        
        # Amplified collapse (PEUT ÊTRE RÉDUIT si catalyst négatif!)
        amplified = collapse_prob * (1 + catalyst_final)
        amplified = max(Config.MIN_COLLAPSE_PROB, min(Config.MAX_COLLAPSE_PROB, amplified))
        
        return CatalystResult(
            catalyst_score=round(catalyst_final, 3),
            chain_reaction_prob=round(chain_reaction_prob, 3),
            referee_profile=ref_type,
            card_impact=card_impact,
            pressure_crackers_count=len(pressure_crackers),
            pressure_cracker_names=[pc.name for pc in pressure_crackers],
            reasoning=reasoning,
            additional_markets=additional_markets,
            amplified_collapse=round(amplified, 3)
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TIMING DNA ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class TimingDNAEngine:
    """
    Moteur d'analyse temporelle pour le Time-Decay Arbitrage
    
    Classifie les équipes selon leur pattern d'effondrement:
    - EARLY_COLLAPSE: Parier pré-match
    - LATE_COLLAPSE: Attendre 2ème mi-temps (Live Trap)
    - STEADY_DECLINE: Flexible
    """
    
    def __init__(self):
        self.defenders = DataLoader.load_defenders()
        self.timing_profiles = DataLoader.load_timing_profiles()
        self.attack_power = DataLoader.load_attack_power()
    
    def analyze(self, team: str) -> TimingResult:
        """
        Analyse le Timing DNA d'une équipe
        
        Args:
            team: Nom de l'équipe
            
        Returns:
            TimingResult avec classification
        """
        
        # Check cache
        cached = self.timing_profiles.get(team)
        if cached:
            profile = TimingProfile(cached.get('timing_profile', 'NEUTRAL'))
            return TimingResult(
                timing_profile=profile,
                optimal_entry=cached.get('optimal_entry', 'PRE_MATCH'),
                decay_factor=cached.get('decay_factor', 1.0),
                time_curve=cached.get('time_curve', {}),
                reasoning=cached.get('reasoning', ''),
                is_live_trap=(profile == TimingProfile.LATE_COLLAPSE)
            )
        
        # Calculer si pas en cache
        team_defenders = self.defenders.get(team, [])
        starters = sorted(
            [d for d in team_defenders if d.minutes_played > 500],
            key=lambda x: -x.minutes_played
        )[:5]
        
        if not starters:
            return TimingResult(
                timing_profile=TimingProfile.UNKNOWN,
                optimal_entry='PRE_MATCH',
                decay_factor=1.0,
                time_curve={},
                reasoning='Données insuffisantes',
                is_live_trap=False
            )
        
        panics = [d.panic_score for d in starters]
        cvars = [d.cvar_95 for d in starters]
        
        avg_panic = np.mean(panics)
        panic_std = np.std(panics)
        max_cvar = max(cvars)
        
        pressure_crackers = sum(1 for d in starters if d.is_pressure_cracker)
        total_collapse = sum(1 for d in starters if d.markov_state in ['TOTAL_COLLAPSE', 'LIABILITY_CONFIRMED'])
        
        # Déterminer le profil
        if total_collapse >= 2 or (max_cvar >= 4.5 and avg_panic >= 80):
            profile = TimingProfile.EARLY_COLLAPSE
            optimal_entry = 'PRE_MATCH'
            decay_factor = 0.9
            reasoning = "Défense trop fragile, s'effondre rapidement"
            time_curve = {'0-30': 1.3, '30-45': 1.1, '45-60': 1.0, '60-75': 0.9, '75-90': 0.85}
            
        elif pressure_crackers >= 2 and 60 <= avg_panic <= 85:
            profile = TimingProfile.LATE_COLLAPSE
            optimal_entry = '2ND_HALF'
            decay_factor = 1.4
            reasoning = "Mental fragile, tient en 1ère MT mais craque à la fatigue"
            time_curve = {'0-30': 0.7, '30-45': 0.85, '45-60': 1.0, '60-75': 1.2, '75-90': 1.4}
            
        elif avg_panic >= 70 and panic_std < 15:
            profile = TimingProfile.STEADY_DECLINE
            optimal_entry = 'ANY'
            decay_factor = 1.0
            reasoning = "Déclin régulier, timing moins critique"
            time_curve = {'0-30': 0.9, '30-45': 0.95, '45-60': 1.0, '60-75': 1.05, '75-90': 1.1}
            
        elif panic_std > 25:
            profile = TimingProfile.RANDOM_CHAOS
            optimal_entry = 'AVOID_TIMING'
            decay_factor = 1.0
            reasoning = "Trop imprévisible pour timing strategy"
            time_curve = {'0-30': 1.0, '30-45': 1.0, '45-60': 1.0, '60-75': 1.0, '75-90': 1.0}
            
        else:
            profile = TimingProfile.NEUTRAL
            optimal_entry = 'PRE_MATCH'
            decay_factor = 1.0
            reasoning = "Pas de pattern timing détecté"
            time_curve = {'0-30': 1.0, '30-45': 1.0, '45-60': 1.0, '60-75': 1.0, '75-90': 1.0}
        
        return TimingResult(
            timing_profile=profile,
            optimal_entry=optimal_entry,
            decay_factor=decay_factor,
            time_curve=time_curve,
            reasoning=reasoning,
            is_live_trap=(profile == TimingProfile.LATE_COLLAPSE)
        )
    
    def calculate_live_trap(
        self,
        defending_team: str,
        opponent_team: str,
        pre_match_collapse: float,
        pre_match_odds: float = 1.80
    ) -> TimingResult:
        """
        Calcule le potentiel de Live Trap
        
        Args:
            defending_team: Équipe qui défend
            opponent_team: Adversaire
            pre_match_collapse: Probabilité de collapse pré-match
            pre_match_odds: Cotes pré-match
            
        Returns:
            TimingResult avec détails live trap
        """
        
        timing = self.analyze(defending_team)
        
        if timing.timing_profile != TimingProfile.LATE_COLLAPSE:
            timing.live_trap_details = {
                'recommendation': 'Parier PRE_MATCH (pas de live trap)'
            }
            return timing
        
        # Calculer les probabilités ajustées (CAPPED à 95%)
        adjusted_60 = min(Config.MAX_COLLAPSE_PROB, pre_match_collapse * timing.time_curve.get('60-75', 1.0))
        adjusted_75 = min(Config.MAX_COLLAPSE_PROB, pre_match_collapse * timing.time_curve.get('75-90', 1.0))
        
        # Estimation des cotes si score serré
        estimated_ht_odds = pre_match_odds * 1.25
        estimated_60_odds = pre_match_odds * 1.40
        
        implied_prob_ht = 1 / estimated_ht_odds
        implied_prob_60 = 1 / estimated_60_odds
        
        edge_at_ht = adjusted_60 - implied_prob_ht
        edge_at_60 = adjusted_75 - implied_prob_60
        
        if edge_at_60 > edge_at_ht:
            optimal_live_entry = '60-65 min'
            target_odds = estimated_60_odds
            expected_edge = edge_at_60
        else:
            optimal_live_entry = 'Mi-temps'
            target_odds = estimated_ht_odds
            expected_edge = edge_at_ht
        
        pre_match_edge = pre_match_collapse - (1 / pre_match_odds)
        arbitrage_gain = expected_edge - pre_match_edge
        
        timing.live_trap_details = {
            'pre_match': {
                'collapse_prob': round(pre_match_collapse, 2),
                'odds': pre_match_odds,
                'edge': round(pre_match_edge * 100, 1)
            },
            'live_opportunity': {
                'optimal_entry': optimal_live_entry,
                'target_odds': round(target_odds, 2),
                'adjusted_collapse_prob': round(adjusted_75, 2),
                'expected_edge': round(expected_edge * 100, 1)
            },
            'arbitrage_gain': f"+{arbitrage_gain * 100:.0f}% edge vs pré-match",
            'conditions': [
                "Score serré (0-0, 0-1, 1-1)",
                f"Pas d'expulsion pour {opponent_team}",
                f"{defending_team} montre des signes de fatigue",
                f"Cote atteint ~{target_odds:.2f} ou plus"
            ],
            'alert': f"⚠️ LIVE TRAP: Attendre {optimal_live_entry} si score serré. Edge: +{expected_edge*100:.0f}%"
        }
        
        return timing


# ═══════════════════════════════════════════════════════════════════════════════
# DEFENSE SHORTING ENGINE (ORCHESTRATEUR PRINCIPAL)
# ═══════════════════════════════════════════════════════════════════════════════

class DefenseShortingEngine:
    """
    Moteur principal de Defense Shorting
    
    Orchestre les 3 sous-moteurs:
    1. CollapseCalculatorV4 - Probabilité d'effondrement
    2. CatalystEngine - Amplification arbitrale
    3. TimingDNAEngine - Optimisation temporelle
    """
    
    def __init__(self):
        self.collapse_calc = CollapseCalculatorV4()
        self.catalyst_engine = CatalystEngine()
        self.timing_engine = TimingDNAEngine()
    
    def full_analysis(
        self,
        defending_team: str,
        opponent_team: str,
        referee_name: Optional[str] = None,
        is_home: bool = True,
        is_derby: bool = False,
        days_since_last_match: int = 7,
        pre_match_odds: float = 1.80
    ) -> FullAnalysis:
        """
        Analyse complète d'un match
        
        Args:
            defending_team: Équipe qui défend
            opponent_team: Adversaire
            referee_name: Arbitre (optionnel)
            is_home: Match à domicile?
            is_derby: Derby?
            days_since_last_match: Jours depuis dernier match
            pre_match_odds: Cotes pré-match
            
        Returns:
            FullAnalysis avec tous les détails
        """
        
        alerts = []
        
        # ═══════════════════════════════════════════════════════════════════
        # 1. COLLAPSE V4
        # ═══════════════════════════════════════════════════════════════════
        
        collapse = self.collapse_calc.calculate(
            defending_team, opponent_team, is_home, is_derby, days_since_last_match
        )
        
        # ═══════════════════════════════════════════════════════════════════
        # 2. CATALYST ENGINE (si arbitre fourni)
        # ═══════════════════════════════════════════════════════════════════
        
        catalyst = None
        if referee_name:
            catalyst = self.catalyst_engine.calculate(
                defending_team, referee_name, collapse.collapse_prob
            )
            if catalyst.catalyst_score > 0.2:
                alerts.append(f"⚡ CATALYST: {catalyst.reasoning[0] if catalyst.reasoning else 'Arbitre amplifie le risque'}")
        
        # ═══════════════════════════════════════════════════════════════════
        # 3. TIMING DNA
        # ═══════════════════════════════════════════════════════════════════
        
        timing = self.timing_engine.calculate_live_trap(
            defending_team, opponent_team, collapse.collapse_prob, pre_match_odds
        )
        
        if timing.is_live_trap:
            alerts.append(f"⏱️ LIVE TRAP: Attendre 2ème MT pour meilleur edge")
        
        # ═══════════════════════════════════════════════════════════════════
        # 4. SYNTHÈSE FINALE
        # ═══════════════════════════════════════════════════════════════════
        
        # Final collapse prob (avec catalyst si applicable)
        if catalyst and (catalyst.catalyst_score > 0.10 or catalyst.catalyst_score < -0.05):
            final_collapse = catalyst.amplified_collapse
        else:
            final_collapse = collapse.collapse_prob
        
        # Cap final
        final_collapse = min(Config.MAX_COLLAPSE_PROB, final_collapse)
        
        # Signal final
        if final_collapse >= 0.75:
            final_signal = Signal.AGGRESSIVE_SHORT
        elif final_collapse >= 0.60:
            final_signal = Signal.STANDARD_SHORT
        elif final_collapse >= 0.50:
            final_signal = Signal.VALUE_BET
        elif final_collapse >= 0.40:
            final_signal = Signal.MONITOR
        else:
            final_signal = Signal.SKIP
        
        # Recommended action
        if timing.is_live_trap and final_signal in [Signal.AGGRESSIVE_SHORT, Signal.STANDARD_SHORT]:
            recommended_action = f"LIVE_BET: Attendre {timing.optimal_entry} si score serré"
        elif final_signal in [Signal.AGGRESSIVE_SHORT, Signal.STANDARD_SHORT]:
            recommended_action = "PRE_MATCH: Parier maintenant"
        elif final_signal == Signal.VALUE_BET:
            recommended_action = "SELECTIVE: Chercher meilleures cotes"
        elif final_signal == Signal.MONITOR:
            recommended_action = "WATCH: Surveiller les conditions"
        else:
            recommended_action = "SKIP: Pas de valeur"
        
        # Tous les marchés
        all_markets = []
        for m in collapse.markets:
            all_markets.append({'market': m, 'source': 'Collapse V4', 'confidence': collapse.confidence})
        if catalyst:
            for m in catalyst.additional_markets:
                all_markets.append({**m, 'source': 'Catalyst Engine'})
        
        # ═══════════════════════════════════════════════════════════════════
        # 5. RECALCULER EV/EDGE/KELLY avec final_collapse
        # ═══════════════════════════════════════════════════════════════════
        
        implied_odds = pre_match_odds
        implied_prob = 1 / implied_odds
        final_edge = final_collapse - implied_prob
        final_ev = final_collapse * implied_odds - 1
        
        if final_edge > 0 and implied_odds > 1:
            final_kelly_full = final_edge / (implied_odds - 1)
            final_kelly_half = final_kelly_full / 2
        else:
            final_kelly_half = 0
        
        # Mettre à jour les valeurs dans collapse pour l'affichage
        collapse.ev = round(final_ev * 100, 1)
        collapse.edge = round(final_edge * 100, 1)
        collapse.kelly_half = round(final_kelly_half * 100, 2)
        
        return FullAnalysis(
            defending_team=defending_team,
            opponent_team=opponent_team,
            referee_name=referee_name,
            collapse=collapse,
            catalyst=catalyst,
            timing=timing,
            final_collapse_prob=round(final_collapse, 3),
            final_signal=final_signal,
            recommended_action=recommended_action,
            all_markets=all_markets,
            alerts=alerts
        )
    
    def quick_scan(self, defending_team: str, opponent_team: str) -> dict:
        """
        Scan rapide sans arbitre ni détails
        
        Returns:
            Dict avec collapse_prob, signal, tier
        """
        collapse = self.collapse_calc.calculate(defending_team, opponent_team)
        return {
            'defending_team': defending_team,
            'opponent_team': opponent_team,
            'collapse_prob': collapse.collapse_prob,
            'signal': collapse.signal.value,
            'confidence': collapse.confidence,
            'opponent_tier': collapse.opponent_tier,
            'ev': collapse.ev,
            'edge': collapse.edge
        }
    
    def batch_analysis(self, matches: List[Tuple[str, str]]) -> List[dict]:
        """
        Analyse batch de plusieurs matchs
        
        Args:
            matches: Liste de tuples (defending_team, opponent_team)
            
        Returns:
            Liste de quick_scan results triés par edge
        """
        results = []
        for def_team, opp_team in matches:
            try:
                result = self.quick_scan(def_team, opp_team)
                results.append(result)
            except Exception as e:
                logger.error(f"Erreur analyse {def_team} vs {opp_team}: {e}")
        
        # Trier par edge décroissant
        results.sort(key=lambda x: -x.get('edge', 0))
        return results


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def format_analysis(analysis: FullAnalysis) -> str:
    """Formate une analyse complète pour affichage"""
    
    lines = []
    lines.append("=" * 70)
    lines.append(f"{'🔴' if 'SHORT' in analysis.final_signal.value else '🟡'} {analysis.defending_team} vs {analysis.opponent_team}")
    lines.append("=" * 70)
    
    lines.append(f"\n📊 COLLAPSE: {analysis.final_collapse_prob:.0%} | Signal: {analysis.final_signal.value}")
    lines.append(f"📈 EV: {analysis.collapse.ev:+.1f}% | Edge: {analysis.collapse.edge:+.1f}%")
    lines.append(f"💰 Kelly: {analysis.collapse.kelly_half:.2f}%")
    
    lines.append(f"\n🎯 ACTION: {analysis.recommended_action}")
    
    if analysis.alerts:
        lines.append(f"\n⚠️ ALERTES:")
        for alert in analysis.alerts:
            lines.append(f"   {alert}")
    
    if analysis.all_markets:
        lines.append(f"\n📍 MARCHÉS RECOMMANDÉS:")
        for m in analysis.all_markets[:5]:
            lines.append(f"   • {m['market']} ({m.get('confidence', 'N/A')})")
    
    lines.append("\n" + "-" * 70)
    lines.append(f"Détails: Liability={analysis.collapse.liability:.0%}, Crisis={analysis.collapse.crisis_count}/5")
    lines.append(f"         Panic={analysis.collapse.avg_panic:.0f}, Tier={analysis.collapse.opponent_tier}")
    
    if analysis.timing.is_live_trap and analysis.timing.live_trap_details:
        ltd = analysis.timing.live_trap_details
        lines.append(f"\n⏱️ LIVE TRAP:")
        lines.append(f"   {ltd.get('alert', '')}")
    
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN / CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Point d'entrée CLI"""
    
    print("=" * 70)
    print("🏁 CHESS ENGINE V2 - DEFENSE SHORTING")
    print("=" * 70)
    
    engine = DefenseShortingEngine()
    
    # Tests
    test_matches = [
        ("West Ham", "Manchester City", "Michael Oliver"),
        ("West Ham", "Arsenal", None),
        ("FC Heidenheim", "Bayern Munich", None),
        ("Wolverhampton Wanderers", "Liverpool", None),
    ]
    
    for def_team, opp_team, referee in test_matches:
        analysis = engine.full_analysis(
            defending_team=def_team,
            opponent_team=opp_team,
            referee_name=referee
        )
        print(format_analysis(analysis))
        print()


if __name__ == "__main__":
    main()
