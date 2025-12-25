#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════════════
FRICTION TENSOR V1.0 - ALPHA 15/10 HEDGE FUND GRADE
═══════════════════════════════════════════════════════════════════════════════════════

Fichier: quantum/orchestrator/friction_tensor.py
Version: 1.0.0
Date: 2025-12-25

PHILOSOPHIE:
Tu ne regardes plus qui est "plus fort". Tu regardes COMMENT ils interagissent.
- Arbitre + Pressing = Destructeur de rythme (Alpha Under)
- Vitesse + Ligne Haute = Destructeur de Clean Sheet (Alpha BTTS)
- Possession + Faible xG = Destructeur de Favori (Alpha Lay)

DIMENSIONS DU TENSOR:
1. KINETIC FRICTION     - Physique + Arbitre (Rhythm Destruction)
2. VELOCITY FRICTION    - Asymétrie de vitesse (Contres létaux)
3. PSYCHOLOGICAL        - Frustration + Implosion
4. SPATIAL FRICTION     - Asphyxie Spatiale (zones bouchées)
5. STATIC BYPASS        - Set-Pieces (sortie de secours)
6. ENTROPY              - Chaos des substitutions (Live Trading)

USAGE:
    from quantum.orchestrator.friction_tensor import FrictionTensorCalculator
    
    calculator = FrictionTensorCalculator()
    tensor = calculator.calculate(
        home_dna=home_team_dna,
        away_dna=away_team_dna,
        referee=referee_dna,
        friction_matrix=friction_matrix,
        is_derby=False
    )
    
    print(tensor.expected_game_script)  # "BROKEN_RHYTHM", "END_TO_END", etc.
    for signal in tensor.trading_signals:
        print(f"{signal.action} {signal.market} @ {signal.edge}% edge")

DÉPENDANCES:
- friction_config.py (configs externalisées)
- friction_matrix_unified.py (FrictionMatrix + PhysicalBreakdown)
- referee_loader.py (RefereeDNA + calculate_rhythm_destruction)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from enum import Enum
import logging

# Import config
try:
    from .friction_config import (
        FRICTION_CONFIG,
        get_disciplinary_config,
        get_velocity_config,
        get_frustration_config,
        get_spatial_config,
        get_aerial_config,
        get_scenario_config,
        normalize_to_100,
    )
except ImportError:
    from friction_config import (
        FRICTION_CONFIG,
        get_disciplinary_config,
        get_velocity_config,
        get_frustration_config,
        get_spatial_config,
        get_aerial_config,
        get_scenario_config,
        normalize_to_100,
    )

# Import referee
try:
    from quantum.orchestrator.referee_loader import (
        RefereeDNA,
        calculate_rhythm_destruction,
        DisciplinaryResult,
    )
except ImportError:
    from referee_loader import (
        RefereeDNA,
        calculate_rhythm_destruction,
        DisciplinaryResult,
    )

# Type checking
if TYPE_CHECKING:
    from .friction_matrix_unified import FrictionMatrix
    from quantum.orchestrator.dataclasses_v2 import TeamDNA

# Logger
logger = logging.getLogger("QuantumOrchestrator.FrictionTensor")


# ═══════════════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════════════

def safe_float(value: Any, default: float = 0.0) -> float:
    """Convertit en float de manière sécurisée."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def clamp(value: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
    """Clamp une valeur entre min et max."""
    return max(min_val, min(max_val, value))


# ═══════════════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════════════

class GameScript(Enum):
    """Scripts de match prédits."""
    STANDARD = "STANDARD"
    BROKEN_RHYTHM = "BROKEN_RHYTHM"      # Haché, Cartons, Under, Late Goals
    END_TO_END = "END_TO_END"            # Ping-pong, Over, BTTS, Early Goals
    ASPHYXIATION = "ASPHYXIATION"        # Étouffé, Under, 0-0 ou 1-0
    TRENCH_WARFARE = "TRENCH_WARFARE"    # Guerre de tranchées, Under, Set-Pieces
    IMPLOSION_RISK = "IMPLOSION_RISK"    # Un favori peut craquer
    COUNTER_ATTACK = "COUNTER_ATTACK"    # Équipe exposée aux contres


class SignalAction(Enum):
    """Actions de trading."""
    BACK = "BACK"
    LAY = "LAY"
    SELL = "SELL"
    BUY = "BUY"


# ═══════════════════════════════════════════════════════════════════════════════════════
# TRADING SIGNAL
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class TradingSignal:
    """
    Signal de trading généré par le FrictionTensor.
    
    Attributes:
        action: BACK, LAY, SELL, BUY
        market: Le marché ciblé (ex: "Under 2.5", "BTTS Yes")
        edge: Avantage estimé en % (0-100)
        confidence: Confiance dans le signal (0-100)
        source: Source du signal (ex: "DISCIPLINARY", "VELOCITY")
        reasoning: Explication du signal
    """
    action: str
    market: str
    edge: float = 0.0
    confidence: int = 50
    source: str = ""
    reasoning: str = ""
    
    def __str__(self) -> str:
        return f"{self.action} {self.market} | Edge: {self.edge:.0f}% | Conf: {self.confidence}%"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "market": self.market,
            "edge": self.edge,
            "confidence": self.confidence,
            "source": self.source,
            "reasoning": self.reasoning,
        }


# ═══════════════════════════════════════════════════════════════════════════════════════
# VELOCITY MISMATCH - Rupture de Ligne (ALPHA #2)
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class VelocityMismatch:
    """
    Analyse l'asymétrie de vitesse entre deux équipes.
    
    Concept: City (High Line + Slow Recovery) vs Leicester 2016 (Vardy Verticality 95%)
    = MASSACRE ANNONCÉ sur les contres
    
    Attributes:
        home_exposure: Vulnérabilité home aux contres (0-100)
        away_exposure: Vulnérabilité away aux contres (0-100)
        is_lethal: True si une équipe est mortellement exposée
        vulnerable_team: "HOME" ou "AWAY" ou "NONE"
        counter_threat_team: Équipe qui menace en contre
    """
    home_exposure: float = 0.0
    away_exposure: float = 0.0
    is_lethal: bool = False
    vulnerable_team: str = "NONE"
    counter_threat_team: str = "NONE"
    
    @property
    def max_exposure(self) -> float:
        return max(self.home_exposure, self.away_exposure)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "home_exposure": self.home_exposure,
            "away_exposure": self.away_exposure,
            "is_lethal": self.is_lethal,
            "vulnerable_team": self.vulnerable_team,
            "counter_threat_team": self.counter_threat_team,
        }


def calculate_velocity_mismatch(
    home_dna: 'TeamDNA',
    away_dna: 'TeamDNA',
) -> VelocityMismatch:
    """
    Calcule le Velocity Mismatch (Alpha #2).
    
    Formule:
        exposure = counter_speed_adversaire × line_height
        counter_speed = verticality × (1 - patience/100)
        line_height = possession / 50 (proxy via home/away_strength)
    
    Args:
        home_dna: TeamDNA de l'équipe home
        away_dna: TeamDNA de l'équipe away
    
    Returns:
        VelocityMismatch avec expositions et flags
    """
    config = get_velocity_config()
    
    # Extraire NemesisDNA et ContextDNA
    h_nemesis = getattr(home_dna, 'nemesis', None)
    a_nemesis = getattr(away_dna, 'nemesis', None)
    h_context = getattr(home_dna, 'context', None)
    a_context = getattr(away_dna, 'context', None)
    
    # Scales pour normalisation
    vert_scale = config.get("verticality_scale", 15.0)
    pat_scale = config.get("patience_scale", 20.0)
    
    # Verticality (vitesse de transition offensive)
    h_vert_raw = safe_float(getattr(h_nemesis, 'verticality', 5.84)) if h_nemesis else 5.84
    a_vert_raw = safe_float(getattr(a_nemesis, 'verticality', 5.84)) if a_nemesis else 5.84
    
    # Normaliser vers 0-100
    h_verticality = (h_vert_raw / vert_scale) * 100.0
    a_verticality = (a_vert_raw / vert_scale) * 100.0
    
    # Patience (faible = jeu direct = contre rapide)
    h_pat_raw = safe_float(getattr(h_nemesis, 'patience', 7.38)) if h_nemesis else 7.38
    a_pat_raw = safe_float(getattr(a_nemesis, 'patience', 7.38)) if a_nemesis else 7.38
    
    # Normaliser
    h_patience = (h_pat_raw / pat_scale) * 100.0
    a_patience = (a_pat_raw / pat_scale) * 100.0
    
    # Line height (proxy: home_strength pour home, away_strength pour away)
    # Plus tu domines, plus tu montes
    h_strength = safe_float(getattr(h_context, 'home_strength', 50.0)) if h_context else 50.0
    a_strength = safe_float(getattr(a_context, 'away_strength', 50.0)) if a_context else 50.0
    
    # Counter speed = verticality × (100 - patience) / 100
    h_counter_speed = h_verticality * ((100 - h_patience) / 100.0)
    a_counter_speed = a_verticality * ((100 - a_patience) / 100.0)
    
    # Line height factor
    h_line_height = h_strength / 50.0  # >1 si dominant
    a_line_height = a_strength / 50.0
    
    # HOME EXPOSURE = Away counter speed × Home line height
    # Plus Home monte ET plus Away est rapide en contre = Plus Home est exposé
    home_exposure = a_counter_speed * h_line_height
    
    # AWAY EXPOSURE = Home counter speed × Away line height
    away_exposure = h_counter_speed * a_line_height
    
    # Clamp
    home_exposure = clamp(home_exposure, 0.0, 100.0)
    away_exposure = clamp(away_exposure, 0.0, 100.0)
    
    # Flags
    lethal_threshold = config.get("lethal_threshold", 80.0)
    is_lethal = max(home_exposure, away_exposure) > lethal_threshold
    
    vulnerable_team = "NONE"
    counter_threat_team = "NONE"
    
    if home_exposure > away_exposure and home_exposure > 50:
        vulnerable_team = "HOME"
        counter_threat_team = "AWAY"
    elif away_exposure > home_exposure and away_exposure > 50:
        vulnerable_team = "AWAY"
        counter_threat_team = "HOME"
    
    logger.debug(
        f"Velocity: Home exposure={home_exposure:.1f}, Away exposure={away_exposure:.1f}, "
        f"Lethal={is_lethal}, Vulnerable={vulnerable_team}"
    )
    
    return VelocityMismatch(
        home_exposure=home_exposure,
        away_exposure=away_exposure,
        is_lethal=is_lethal,
        vulnerable_team=vulnerable_team,
        counter_threat_team=counter_threat_team,
    )


# ═══════════════════════════════════════════════════════════════════════════════════════
# FRUSTRATION INDEX - Cocotte-Minute (ALPHA #3)
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class FrustrationIndex:
    """
    Analyse le risque de frustration/implosion d'une équipe.
    
    Concept: Domination stérile = Possession > 70% mais xG/Shot < 0.07
    = Frustration = Erreur stupide ou Contre Assassin
    
    Attributes:
        home_risk: Risque de frustration home (0-100)
        away_risk: Risque de frustration away (0-100)
        boiling_point_team: Équipe à risque de "cocotte-minute" ou "NONE"
        implosion_risk: True si une équipe risque d'imploser
    """
    home_risk: float = 0.0
    away_risk: float = 0.0
    boiling_point_team: str = "NONE"
    implosion_risk: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "home_risk": self.home_risk,
            "away_risk": self.away_risk,
            "boiling_point_team": self.boiling_point_team,
            "implosion_risk": self.implosion_risk,
        }


def calculate_frustration_index(
    home_dna: 'TeamDNA',
    away_dna: 'TeamDNA',
) -> FrustrationIndex:
    """
    Calcule le Frustration Index (Alpha #3).
    
    Prédit le risque qu'une équipe entre en mode "Cocotte-Minute".
    Utile pour LAY stratégique en pré-match.
    
    Composants:
    - Haute possession + pas clinical = frustration latente
    - xG négatif malgré possession = crée mais ne marque pas
    - Panic factor élevé = craque sous pression
    - Collapse rate = historique d'effondrements
    
    Args:
        home_dna: TeamDNA de l'équipe home
        away_dna: TeamDNA de l'équipe away
    
    Returns:
        FrustrationIndex avec risques et flags
    """
    config = get_frustration_config()
    
    def calc_team_frustration(team_dna: 'TeamDNA') -> float:
        """Calcule le risque de frustration pour une équipe."""
        context = getattr(team_dna, 'context', None)
        psyche = getattr(team_dna, 'psyche', None)
        
        risk = 0.0
        
        if context:
            # Style score comme proxy de possession
            style_score = safe_float(getattr(context, 'style_score', 50.0))
            
            # Clinical flag
            xg_profile = getattr(context, 'xg_profile', {})
            if isinstance(xg_profile, dict):
                clinical = xg_profile.get('clinical', False)
                xg_diff = safe_float(xg_profile.get('xg_diff', 0.0))
            else:
                clinical = False
                xg_diff = 0.0
            
            # Haute possession mais pas clinical
            if style_score > config.get("high_possession_threshold", 55.0) and not clinical:
                risk += config.get("possession_non_clinical_weight", 25.0)
            
            # xG négatif malgré style offensif
            if style_score > 50 and xg_diff < 0:
                risk += config.get("xg_negative_weight", 20.0)
        
        if psyche:
            # Panic factor (échelle 0.34-3.22, avg 1.38)
            panic_raw = safe_float(getattr(psyche, 'panic_factor', 1.38))
            panic_norm = (panic_raw / 5.0) * 100.0  # Normaliser vers 0-100
            
            if panic_norm > config.get("panic_factor_high_threshold", 60.0):
                risk += panic_norm * config.get("panic_factor_weight", 0.30)
            
            # Lead protection faible = risque de perdre l'avantage
            lead_prot = safe_float(getattr(psyche, 'lead_protection', 0.5))
            if lead_prot < 0.4:
                risk += 15.0
            
            # Killer instinct faible = pas de finition
            killer = safe_float(getattr(psyche, 'killer_instinct', 1.0))
            if killer < 0.8:
                risk += 10.0
        
        return clamp(risk, 0.0, 100.0)
    
    # Calculer pour chaque équipe
    home_risk = calc_team_frustration(home_dna)
    away_risk = calc_team_frustration(away_dna)
    
    # Déterminer le boiling point
    threshold = config.get("boiling_point_threshold", 70.0)
    boiling_point_team = "NONE"
    implosion_risk = False
    
    if home_risk > threshold and home_risk > away_risk:
        boiling_point_team = "HOME"
        implosion_risk = True
    elif away_risk > threshold and away_risk > home_risk:
        boiling_point_team = "AWAY"
        implosion_risk = True
    elif home_risk > threshold or away_risk > threshold:
        implosion_risk = True
    
    logger.debug(
        f"Frustration: Home={home_risk:.1f}, Away={away_risk:.1f}, "
        f"Boiling={boiling_point_team}, Implosion={implosion_risk}"
    )
    
    return FrustrationIndex(
        home_risk=home_risk,
        away_risk=away_risk,
        boiling_point_team=boiling_point_team,
        implosion_risk=implosion_risk,
    )


# ═══════════════════════════════════════════════════════════════════════════════════════
# SPATIAL FRICTION - Asphyxie Spatiale (ALPHA 2.0 #1)
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class SpatialFriction:
    """
    Analyse si les zones d'attaque sont bouchées ou libres.
    
    Concept: Si attaque passe 60% par le centre et défense est NARROW
    = Friction TOTALE = Le ballon ne passera pas
    
    Attributes:
        friction_score: Score de friction spatiale (0-100)
        attack_zone_home: Zone principale d'attaque home
        attack_zone_away: Zone principale d'attaque away
        mismatch_type: "ASPHYXIA", "BOULEVARDS", "BLOCKED_WINGS", "BALANCED"
    """
    friction_score: float = 50.0
    attack_zone_home: str = "BALANCED"
    attack_zone_away: str = "BALANCED"
    mismatch_type: str = "BALANCED"
    
    @property
    def is_blocked(self) -> bool:
        return self.friction_score > 80.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "friction_score": self.friction_score,
            "attack_zone_home": self.attack_zone_home,
            "attack_zone_away": self.attack_zone_away,
            "mismatch_type": self.mismatch_type,
            "is_blocked": self.is_blocked,
        }


def calculate_spatial_friction(
    home_dna: 'TeamDNA',
    away_dna: 'TeamDNA',
) -> SpatialFriction:
    """
    Calcule la Spatial Friction (Alpha 2.0 #1).
    
    Croise les zones d'attaque avec la structure défensive adverse.
    
    Args:
        home_dna: TeamDNA de l'équipe home
        away_dna: TeamDNA de l'équipe away
    
    Returns:
        SpatialFriction avec score et type de mismatch
    """
    config = get_spatial_config()
    
    # Extraire TacticalDNA
    h_tactical = getattr(home_dna, 'tactical', None)
    a_tactical = getattr(away_dna, 'tactical', None)
    
    # Par défaut
    h_attack_zone = "BALANCED"
    a_attack_zone = "BALANCED"
    
    # Analyser le profil tactique home
    if h_tactical:
        tactical_profile = getattr(h_tactical, 'tactical_profile', 'BALANCED')
        box_shot_ratio = safe_float(getattr(h_tactical, 'box_shot_ratio', 0.5))
        
        # Déduire la zone d'attaque depuis le profil
        if tactical_profile == "OPEN_PLAY" and box_shot_ratio > 0.6:
            h_attack_zone = "CENTER"
        elif box_shot_ratio < 0.4:
            h_attack_zone = "WINGS"
        else:
            h_attack_zone = "BALANCED"
    
    # Analyser le profil tactique away
    if a_tactical:
        tactical_profile = getattr(a_tactical, 'tactical_profile', 'BALANCED')
        box_shot_ratio = safe_float(getattr(a_tactical, 'box_shot_ratio', 0.5))
        
        if tactical_profile == "OPEN_PLAY" and box_shot_ratio > 0.6:
            a_attack_zone = "CENTER"
        elif box_shot_ratio < 0.4:
            a_attack_zone = "WINGS"
        else:
            a_attack_zone = "BALANCED"
    
    # Calculer la friction
    # Pour l'instant, utiliser une heuristique basée sur les profils
    # (À améliorer quand on aura defensive_structure dans les données)
    friction_score = 50.0
    mismatch_type = "BALANCED"
    
    # Si les deux attaquent par le centre = congestion = Under
    if h_attack_zone == "CENTER" and a_attack_zone == "CENTER":
        friction_score = 75.0
        mismatch_type = "MIDFIELD_CONGESTION"
    
    # Si un attaque par le centre contre formation compacte
    # (proxy: si l'adversaire a un faible box_shot_ratio = bloc bas)
    if h_attack_zone == "CENTER":
        a_box_ratio = safe_float(getattr(a_tactical, 'box_shot_ratio', 0.5)) if a_tactical else 0.5
        if a_box_ratio < 0.4:  # Équipe qui ne va pas dans la surface = bloc bas
            friction_score = config.get("center_vs_narrow_friction", 90.0)
            mismatch_type = "ASPHYXIA"
    
    # Si attaque par les ailes contre bloc serré = boulevards
    if h_attack_zone == "WINGS":
        a_box_ratio = safe_float(getattr(a_tactical, 'box_shot_ratio', 0.5)) if a_tactical else 0.5
        if a_box_ratio < 0.4:
            friction_score = config.get("wings_vs_narrow_friction", 10.0)
            mismatch_type = "BOULEVARDS"
    
    logger.debug(
        f"Spatial: Home attack={h_attack_zone}, Away attack={a_attack_zone}, "
        f"Friction={friction_score:.1f}, Type={mismatch_type}"
    )
    
    return SpatialFriction(
        friction_score=friction_score,
        attack_zone_home=h_attack_zone,
        attack_zone_away=a_attack_zone,
        mismatch_type=mismatch_type,
    )


# ═══════════════════════════════════════════════════════════════════════════════════════
# AERIAL MISMATCH - Set-Piece Bypass (ALPHA 2.0 #3)
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class AerialMismatch:
    """
    Analyse le différentiel aérien pour les set-pieces.
    
    Concept: Dans un match bloqué (TRENCH_WARFARE), la seule issue est
    un but sur corner/coup franc. Le mismatch aérien prédit qui.
    
    Attributes:
        home_aerial: Score aérien home (0-100)
        away_aerial: Score aérien away (0-100)
        mismatch: Différentiel absolu
        dominant_team: Équipe dominante dans les airs
        set_piece_threat: True si le mismatch est significatif
    """
    home_aerial: float = 50.0
    away_aerial: float = 50.0
    mismatch: float = 0.0
    dominant_team: str = "NONE"
    set_piece_threat: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "home_aerial": self.home_aerial,
            "away_aerial": self.away_aerial,
            "mismatch": self.mismatch,
            "dominant_team": self.dominant_team,
            "set_piece_threat": self.set_piece_threat,
        }


def calculate_aerial_mismatch(
    home_dna: 'TeamDNA',
    away_dna: 'TeamDNA',
) -> AerialMismatch:
    """
    Calcule le Aerial Mismatch (Alpha 2.0 #3).
    
    Args:
        home_dna: TeamDNA de l'équipe home
        away_dna: TeamDNA de l'équipe away
    
    Returns:
        AerialMismatch avec scores et dominance
    """
    config = get_aerial_config()
    
    # Extraire PhysicalDNA
    h_physical = getattr(home_dna, 'physical', None)
    a_physical = getattr(away_dna, 'physical', None)
    
    # Score aérien (aerial_win_pct si disponible, sinon estimer)
    h_aerial = 50.0
    a_aerial = 50.0
    
    if h_physical:
        h_aerial = safe_float(getattr(h_physical, 'aerial_win_pct', 50.0))
    
    if a_physical:
        a_aerial = safe_float(getattr(a_physical, 'aerial_win_pct', 50.0))
    
    # Mismatch
    mismatch = abs(h_aerial - a_aerial)
    
    # Dominant team
    dominant_team = "NONE"
    if h_aerial > a_aerial + 10:
        dominant_team = "HOME"
    elif a_aerial > h_aerial + 10:
        dominant_team = "AWAY"
    
    # Set piece threat
    threshold = config.get("mismatch_threshold", 25.0)
    set_piece_threat = mismatch > threshold
    
    logger.debug(
        f"Aerial: Home={h_aerial:.1f}, Away={a_aerial:.1f}, "
        f"Mismatch={mismatch:.1f}, Dominant={dominant_team}"
    )
    
    return AerialMismatch(
        home_aerial=h_aerial,
        away_aerial=a_aerial,
        mismatch=mismatch,
        dominant_team=dominant_team,
        set_piece_threat=set_piece_threat,
    )


# ═══════════════════════════════════════════════════════════════════════════════════════
# FRICTION TENSOR - DATACLASS PRINCIPALE
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class FrictionTensor:
    """
    Tenseur de Friction Multi-Dimensionnel - Alpha 15/10.
    
    Prédit non pas QUI gagne, mais COMMENT le match se déroule.
    
    "Ça va être bloqué au centre (Spatial), haché par l'arbitre (Kinetic),
    jusqu'à ce qu'un défenseur sorte (Entropic) ou qu'il y ait un corner (Static)."
    
    Dimensions:
    1. KINETIC     - Disciplinary Friction (Arbitre + Pressing)
    2. VELOCITY    - Velocity Mismatch (Contres)
    3. PSYCHOLOGICAL - Frustration Index
    4. SPATIAL     - Spatial Friction (Zones)
    5. AERIAL      - Aerial Mismatch (Set-pieces)
    """
    
    # === IDENTIFICATION ===
    home_team: str = ""
    away_team: str = ""
    referee_name: str = ""
    
    # === DIMENSION 1: KINETIC (Physique + Arbitre) ===
    disciplinary: Optional[DisciplinaryResult] = None
    kinetic_home: float = 50.0
    kinetic_away: float = 50.0
    physical_edge: float = 50.0
    
    # === DIMENSION 2: VELOCITY (Contres) ===
    velocity: Optional[VelocityMismatch] = None
    
    # === DIMENSION 3: PSYCHOLOGICAL (Frustration) ===
    frustration: Optional[FrustrationIndex] = None
    
    # === DIMENSION 4: SPATIAL (Zones) ===
    spatial: Optional[SpatialFriction] = None
    midfield_congestion: float = 50.0
    
    # === DIMENSION 5: AERIAL (Set-pieces) ===
    aerial: Optional[AerialMismatch] = None
    
    # === GAME SCRIPT ===
    primary_script: GameScript = GameScript.STANDARD
    secondary_scripts: List[GameScript] = field(default_factory=list)
    
    # === TRADING SIGNALS ===
    signals: List[TradingSignal] = field(default_factory=list)
    
    # === METADATA ===
    confidence: int = 50
    quality_tier: str = "standard"
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # PROPRIÉTÉS CALCULÉES
    # ═══════════════════════════════════════════════════════════════════════════════
    
    @property
    def expected_game_script(self) -> str:
        """Retourne le script de match principal."""
        return self.primary_script.value
    
    @property
    def trading_signals(self) -> List[TradingSignal]:
        """Retourne les signaux de trading."""
        return self.signals
    
    @property
    def is_broken_rhythm(self) -> bool:
        """Match haché prévu ?"""
        return self.primary_script == GameScript.BROKEN_RHYTHM
    
    @property
    def is_end_to_end(self) -> bool:
        """Match ouvert prévu ?"""
        return self.primary_script == GameScript.END_TO_END
    
    @property
    def has_implosion_risk(self) -> bool:
        """Risque d'implosion d'un favori ?"""
        return self.frustration.implosion_risk if self.frustration else False
    
    @property
    def has_counter_threat(self) -> bool:
        """Menace de contre létale ?"""
        return self.velocity.is_lethal if self.velocity else False
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # SERIALIZATION
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire."""
        return {
            "home_team": self.home_team,
            "away_team": self.away_team,
            "referee_name": self.referee_name,
            
            "disciplinary": {
                "destruction_score": self.disciplinary.destruction_score if self.disciplinary else 0,
                "rhythm_status": self.disciplinary.rhythm_status if self.disciplinary else "FLUID",
                "expected_cards": self.disciplinary.expected_cards if self.disciplinary else 0,
            } if self.disciplinary else None,
            
            "velocity": self.velocity.to_dict() if self.velocity else None,
            "frustration": self.frustration.to_dict() if self.frustration else None,
            "spatial": self.spatial.to_dict() if self.spatial else None,
            "aerial": self.aerial.to_dict() if self.aerial else None,
            
            "kinetic_home": self.kinetic_home,
            "kinetic_away": self.kinetic_away,
            "physical_edge": self.physical_edge,
            "midfield_congestion": self.midfield_congestion,
            
            "primary_script": self.primary_script.value,
            "secondary_scripts": [s.value for s in self.secondary_scripts],
            
            "signals": [s.to_dict() for s in self.signals],
            "confidence": self.confidence,
            "quality_tier": self.quality_tier,
        }
    
    def summary(self) -> str:
        """Retourne un résumé lisible du tensor."""
        lines = [
            f"═══ FRICTION TENSOR: {self.home_team} vs {self.away_team} ═══",
            f"  Referee: {self.referee_name}",
            f"",
            f"  📊 GAME SCRIPT: {self.primary_script.value}",
        ]
        
        if self.secondary_scripts:
            lines.append(f"     Secondary: {', '.join(s.value for s in self.secondary_scripts)}")
        
        lines.append(f"")
        
        # Disciplinary
        if self.disciplinary:
            lines.append(f"  🎴 DISCIPLINARY:")
            lines.append(f"     Destruction Score: {self.disciplinary.destruction_score:.2f}")
            lines.append(f"     Rhythm: {self.disciplinary.rhythm_status}")
            lines.append(f"     Expected Cards: {self.disciplinary.expected_cards:.1f}")
        
        # Velocity
        if self.velocity:
            lines.append(f"  ⚡ VELOCITY:")
            lines.append(f"     Home Exposure: {self.velocity.home_exposure:.1f}")
            lines.append(f"     Away Exposure: {self.velocity.away_exposure:.1f}")
            lines.append(f"     Lethal: {'⚠️ YES' if self.velocity.is_lethal else 'No'}")
        
        # Frustration
        if self.frustration:
            lines.append(f"  🔥 FRUSTRATION:")
            lines.append(f"     Home Risk: {self.frustration.home_risk:.1f}")
            lines.append(f"     Away Risk: {self.frustration.away_risk:.1f}")
            if self.frustration.implosion_risk:
                lines.append(f"     ⚠️ IMPLOSION RISK: {self.frustration.boiling_point_team}")
        
        # Spatial
        if self.spatial:
            lines.append(f"  🗺️ SPATIAL:")
            lines.append(f"     Friction: {self.spatial.friction_score:.1f}")
            lines.append(f"     Type: {self.spatial.mismatch_type}")
        
        # Trading Signals
        if self.signals:
            lines.append(f"")
            lines.append(f"  💰 TRADING SIGNALS:")
            for sig in self.signals[:5]:  # Max 5 signals affichés
                lines.append(f"     {sig}")
        
        lines.append(f"")
        lines.append(f"  Confidence: {self.confidence}% | Quality: {self.quality_tier}")
        
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════════════
# FRICTION TENSOR CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════════════════

class FrictionTensorCalculator:
    """
    Calculateur du FrictionTensor.
    
    Orchestre le calcul de toutes les dimensions et génère les signaux de trading.
    
    Usage:
        calculator = FrictionTensorCalculator()
        tensor = calculator.calculate(
            home_dna=home_team_dna,
            away_dna=away_team_dna,
            referee=referee_dna,
            friction_matrix=friction_matrix,
            is_derby=False
        )
    """
    
    def __init__(self):
        self.scenario_config = get_scenario_config()
    
    def calculate(
        self,
        home_dna: 'TeamDNA',
        away_dna: 'TeamDNA',
        referee: Optional[RefereeDNA] = None,
        friction_matrix: Optional['FrictionMatrix'] = None,
        is_derby: bool = False,
        rivalry_intensity: float = 0.0,
    ) -> FrictionTensor:
        """
        Calcule le FrictionTensor complet.
        
        Args:
            home_dna: TeamDNA de l'équipe home
            away_dna: TeamDNA de l'équipe away
            referee: RefereeDNA (optionnel, mais recommandé)
            friction_matrix: FrictionMatrix pré-calculée (optionnel)
            is_derby: Est-ce un derby?
            rivalry_intensity: Intensité de la rivalité (0-100)
        
        Returns:
            FrictionTensor avec toutes les dimensions calculées
        """
        # Créer le tensor
        tensor = FrictionTensor(
            home_team=getattr(home_dna, 'team_name', 'Home'),
            away_team=getattr(away_dna, 'team_name', 'Away'),
            referee_name=referee.name if referee else "Unknown",
        )
        
        # ═══════════════════════════════════════════════════════════════════════════
        # DIMENSION 1: DISCIPLINARY FRICTION
        # ═══════════════════════════════════════════════════════════════════════════
        if referee:
            # Extraire pressing depuis PhysicalDNA
            h_physical = getattr(home_dna, 'physical', None)
            a_physical = getattr(away_dna, 'physical', None)
            
            h_pressing_raw = safe_float(getattr(h_physical, 'pressing_intensity', 11.68)) if h_physical else 11.68
            a_pressing_raw = safe_float(getattr(a_physical, 'pressing_intensity', 11.68)) if a_physical else 11.68
            
            # Normaliser vers 0-100
            h_pressing = normalize_to_100(h_pressing_raw, "pressing_intensity")
            a_pressing = normalize_to_100(a_pressing_raw, "pressing_intensity")
            
            tensor.disciplinary = calculate_rhythm_destruction(
                home_pressing=h_pressing,
                away_pressing=a_pressing,
                referee=referee,
                is_derby=is_derby,
                rivalry_intensity=rivalry_intensity,
            )
        
        # ═══════════════════════════════════════════════════════════════════════════
        # DIMENSION 2: VELOCITY MISMATCH
        # ═══════════════════════════════════════════════════════════════════════════
        tensor.velocity = calculate_velocity_mismatch(home_dna, away_dna)
        
        # ═══════════════════════════════════════════════════════════════════════════
        # DIMENSION 3: FRUSTRATION INDEX
        # ═══════════════════════════════════════════════════════════════════════════
        tensor.frustration = calculate_frustration_index(home_dna, away_dna)
        
        # ═══════════════════════════════════════════════════════════════════════════
        # DIMENSION 4: SPATIAL FRICTION
        # ═══════════════════════════════════════════════════════════════════════════
        tensor.spatial = calculate_spatial_friction(home_dna, away_dna)
        tensor.midfield_congestion = tensor.spatial.friction_score if tensor.spatial else 50.0
        
        # ═══════════════════════════════════════════════════════════════════════════
        # DIMENSION 5: AERIAL MISMATCH
        # ═══════════════════════════════════════════════════════════════════════════
        tensor.aerial = calculate_aerial_mismatch(home_dna, away_dna)
        
        # ═══════════════════════════════════════════════════════════════════════════
        # RÉCUPÉRER DONNÉES DE FRICTION MATRIX
        # ═══════════════════════════════════════════════════════════════════════════
        if friction_matrix:
            tensor.kinetic_home = friction_matrix.kinetic_home
            tensor.kinetic_away = friction_matrix.kinetic_away
            tensor.physical_edge = friction_matrix.physical_edge
        
        # ═══════════════════════════════════════════════════════════════════════════
        # DÉTERMINER LE GAME SCRIPT
        # ═══════════════════════════════════════════════════════════════════════════
        tensor.primary_script, tensor.secondary_scripts = self._determine_game_script(tensor)
        
        # ═══════════════════════════════════════════════════════════════════════════
        # GÉNÉRER LES SIGNAUX DE TRADING
        # ═══════════════════════════════════════════════════════════════════════════
        tensor.signals = self._generate_trading_signals(tensor)
        
        # ═══════════════════════════════════════════════════════════════════════════
        # CALCULER LA CONFIANCE
        # ═══════════════════════════════════════════════════════════════════════════
        tensor.confidence = self._calculate_confidence(tensor, referee)
        tensor.quality_tier = self._determine_quality_tier(tensor, referee)
        
        return tensor
    
    def _determine_game_script(
        self,
        tensor: FrictionTensor
    ) -> tuple[GameScript, List[GameScript]]:
        """Détermine le script de match principal et secondaires."""
        scripts = []
        config = self.scenario_config
        
        # 1. BROKEN_RHYTHM (priorité haute)
        if tensor.disciplinary and tensor.disciplinary.destruction_score > config.get("broken_rhythm_threshold", 1.4):
            scripts.append(GameScript.BROKEN_RHYTHM)
        
        # 2. END_TO_END (velocity lethal)
        if tensor.velocity and tensor.velocity.is_lethal:
            scripts.append(GameScript.END_TO_END)
        
        # 3. ASPHYXIATION (spatial blocked)
        if tensor.spatial and tensor.spatial.friction_score > config.get("asphyxiation_threshold", 85.0):
            scripts.append(GameScript.ASPHYXIATION)
        
        # 4. TRENCH_WARFARE (midfield congestion)
        if tensor.midfield_congestion > config.get("trench_warfare_threshold", 80.0):
            scripts.append(GameScript.TRENCH_WARFARE)
        
        # 5. IMPLOSION_RISK
        if tensor.frustration and tensor.frustration.implosion_risk:
            scripts.append(GameScript.IMPLOSION_RISK)
        
        # 6. COUNTER_ATTACK (high exposure but not lethal)
        if tensor.velocity and tensor.velocity.max_exposure > 60 and not tensor.velocity.is_lethal:
            scripts.append(GameScript.COUNTER_ATTACK)
        
        # Déterminer primary et secondary
        if scripts:
            primary = scripts[0]
            secondary = scripts[1:] if len(scripts) > 1 else []
        else:
            primary = GameScript.STANDARD
            secondary = []
        
        return primary, secondary
    
    def _generate_trading_signals(self, tensor: FrictionTensor) -> List[TradingSignal]:
        """Génère les signaux de trading basés sur le tensor."""
        signals = []
        
        # Signaux DISCIPLINARY
        if tensor.disciplinary:
            if tensor.disciplinary.back_under_goals:
                signals.append(TradingSignal(
                    action="BACK",
                    market="Under 2.5 Goals",
                    edge=15.0,
                    confidence=tensor.disciplinary.signal_confidence,
                    source="DISCIPLINARY",
                    reasoning=f"Rhythm Destruction Score {tensor.disciplinary.destruction_score:.2f} > 1.4"
                ))
            
            if tensor.disciplinary.back_over_cards:
                signals.append(TradingSignal(
                    action="BACK",
                    market="Over 3.5 Cards",
                    edge=20.0,
                    confidence=tensor.disciplinary.signal_confidence,
                    source="DISCIPLINARY",
                    reasoning=f"High contact density + strict referee"
                ))
        
        # Signaux VELOCITY
        if tensor.velocity and tensor.velocity.is_lethal:
            counter_team = tensor.velocity.counter_threat_team
            signals.append(TradingSignal(
                action="BACK",
                market=f"{counter_team} to Score First",
                edge=22.0,
                confidence=75,
                source="VELOCITY",
                reasoning=f"Lethal counter threat, exposure={tensor.velocity.max_exposure:.0f}"
            ))
            
            vulnerable_team = tensor.velocity.vulnerable_team
            signals.append(TradingSignal(
                action="LAY",
                market=f"{vulnerable_team} Clean Sheet",
                edge=18.0,
                confidence=70,
                source="VELOCITY",
                reasoning=f"{vulnerable_team} exposed to counters"
            ))
        
        # Signaux FRUSTRATION
        if tensor.frustration and tensor.frustration.implosion_risk:
            boiling = tensor.frustration.boiling_point_team
            signals.append(TradingSignal(
                action="LAY",
                market=f"{boiling} to Win",
                edge=15.0,
                confidence=70,
                source="FRUSTRATION",
                reasoning=f"Implosion risk for {boiling}, frustration={max(tensor.frustration.home_risk, tensor.frustration.away_risk):.0f}"
            ))
        
        # Signaux SPATIAL
        if tensor.spatial and tensor.spatial.mismatch_type == "ASPHYXIA":
            signals.append(TradingSignal(
                action="BACK",
                market="Under 1.5 Goals",
                edge=20.0,
                confidence=75,
                source="SPATIAL",
                reasoning="Spatial asphyxiation - attack zones blocked"
            ))
        
        # Signaux AERIAL (en cas de TRENCH_WARFARE)
        if tensor.primary_script == GameScript.TRENCH_WARFARE and tensor.aerial and tensor.aerial.set_piece_threat:
            dominant = tensor.aerial.dominant_team
            signals.append(TradingSignal(
                action="BACK",
                market=f"Next Goal: Header ({dominant})",
                edge=25.0,
                confidence=65,
                source="AERIAL",
                reasoning=f"Trench warfare + aerial mismatch {tensor.aerial.mismatch:.0f}%"
            ))
            
            signals.append(TradingSignal(
                action="BACK",
                market="Over 9.5 Corners",
                edge=12.0,
                confidence=60,
                source="AERIAL",
                reasoning="Set-piece bypass expected in blocked game"
            ))
        
        return signals
    
    def _calculate_confidence(self, tensor: FrictionTensor, referee: Optional[RefereeDNA]) -> int:
        """Calcule la confiance globale du tensor."""
        confidence = 50
        
        # Bonus si referee présent
        if referee:
            confidence += 10
            if referee.quality_tier == "hedge_fund_grade":
                confidence += 10
        
        # Bonus si signaux concordants
        if len(tensor.signals) >= 3:
            confidence += 5
        
        # Bonus si script clair (pas STANDARD)
        if tensor.primary_script != GameScript.STANDARD:
            confidence += 10
        
        return min(confidence, 95)
    
    def _determine_quality_tier(self, tensor: FrictionTensor, referee: Optional[RefereeDNA]) -> str:
        """Détermine le niveau de qualité du tensor."""
        # Count des dimensions calculées
        dimensions = 0
        if tensor.disciplinary:
            dimensions += 1
        if tensor.velocity:
            dimensions += 1
        if tensor.frustration:
            dimensions += 1
        if tensor.spatial:
            dimensions += 1
        if tensor.aerial:
            dimensions += 1
        
        if dimensions >= 5 and referee and referee.quality_tier == "hedge_fund_grade":
            return "hedge_fund_grade"
        elif dimensions >= 4:
            return "senior_quant"
        elif dimensions >= 3:
            return "standard"
        else:
            return "basic"


# ═══════════════════════════════════════════════════════════════════════════════════════
# VERSION INFO
# ═══════════════════════════════════════════════════════════════════════════════════════

FRICTION_TENSOR_VERSION = "1.0.0"
FRICTION_TENSOR_DATE = "2025-12-25"


# ═══════════════════════════════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 80)
    print("TEST FRICTION TENSOR V1.0 - ALPHA 15/10")
    print("=" * 80)
    
    # Mock TeamDNA
    class MockNemesisDNA:
        verticality = 7.5    # Élevé = contre rapide
        patience = 5.0       # Faible = jeu direct
    
    class MockPsycheDNA:
        panic_factor = 2.5   # Élevé = tendance à craquer
        killer_instinct = 0.7
        lead_protection = 0.3
    
    class MockPhysicalDNA:
        pressing_intensity = 18.0
        aerial_win_pct = 65.0
    
    class MockContextDNA:
        home_strength = 70.0
        away_strength = 45.0
        style_score = 65.0
        xg_profile = {"clinical": False, "xg_diff": -5.0}
    
    class MockTacticalDNA:
        tactical_profile = "OPEN_PLAY"
        box_shot_ratio = 0.65
    
    class MockTeamDNA:
        team_name = "Test Team"
        nemesis = None
        psyche = None
        physical = None
        context = None
        tactical = None
    
    # Créer Home DNA (Liverpool style)
    home_dna = MockTeamDNA()
    home_dna.team_name = "Liverpool"
    home_dna.nemesis = MockNemesisDNA()
    home_dna.nemesis.verticality = 7.5
    home_dna.nemesis.patience = 5.0
    home_dna.psyche = MockPsycheDNA()
    home_dna.psyche.panic_factor = 1.5
    home_dna.physical = MockPhysicalDNA()
    home_dna.physical.pressing_intensity = 18.0
    home_dna.context = MockContextDNA()
    home_dna.context.home_strength = 70.0
    home_dna.tactical = MockTacticalDNA()
    
    # Créer Away DNA (Burnley style - bloc bas)
    away_dna = MockTeamDNA()
    away_dna.team_name = "Burnley"
    away_dna.nemesis = MockNemesisDNA()
    away_dna.nemesis.verticality = 9.0  # Très vertical en contre
    away_dna.nemesis.patience = 3.0      # Très direct
    away_dna.psyche = MockPsycheDNA()
    away_dna.psyche.panic_factor = 1.0   # Peu de panique
    away_dna.physical = MockPhysicalDNA()
    away_dna.physical.pressing_intensity = 12.0  # Pressing bas
    away_dna.physical.aerial_win_pct = 72.0      # Fort dans les airs
    away_dna.context = MockContextDNA()
    away_dna.context.away_strength = 40.0
    away_dna.tactical = MockTacticalDNA()
    away_dna.tactical.box_shot_ratio = 0.35      # Peu dans la surface = bloc bas
    
    # Créer Referee
    referee = RefereeDNA(
        name="Michael Oliver",
        matches=320,
        leagues=["Premier League"],
        strictness_level=7,
        avg_cards=3.80,
        avg_fouls=22.0,
        card_per_foul=12.5,
        avg_goals=2.95,
        style="TRIGGER_HAPPY",
    )
    
    # Calculer le tensor
    print("\n📊 Calcul du FrictionTensor...")
    calculator = FrictionTensorCalculator()
    tensor = calculator.calculate(
        home_dna=home_dna,
        away_dna=away_dna,
        referee=referee,
        is_derby=False,
        rivalry_intensity=30.0,
    )
    
    # Afficher le résultat
    print("\n" + tensor.summary())
    
    # Test des propriétés
    print("\n📋 PROPRIÉTÉS:")
    print(f"  is_broken_rhythm: {tensor.is_broken_rhythm}")
    print(f"  is_end_to_end: {tensor.is_end_to_end}")
    print(f"  has_implosion_risk: {tensor.has_implosion_risk}")
    print(f"  has_counter_threat: {tensor.has_counter_threat}")
    
    print("\n✅ TEST PASSED - FRICTION TENSOR V1.0")

