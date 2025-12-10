"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║  COACH DNA - Empreinte Tactique Unique 13D                                           ║
║  Version: 2.0                                                                        ║
║  "Chaque coach a une signature tactique mesurable et comparable."                    ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

Architecture Mon_PS - Chess Engine V2.0
Créé le: 2025-12-10

Installation: /home/Mon_ps/quantum/models/coach_dna.py

Les 3 ajustements critiques intégrés:
1. structure_rigidity (13ème dimension): Chaos (Bielsa) vs Rigidité (Conte)
2. bench_depth_score: Qualité des remplaçants vs titulaires
3. public_perception_bias: Edge contrarian (surévalué/sous-évalué)
"""

from pydantic import BaseModel, Field, ConfigDict, computed_field, field_validator
from typing import Optional, List, Dict, Tuple
from datetime import datetime
import math
import hashlib

from .base import QuantumBaseModel, ConfidentMetric
from .enums import (
    Formation, 
    GameState, 
    GameStateReaction, 
    MarketType,
    PublicPerceptionBias,
    StructureType,
    DataQuality
)


# ═══════════════════════════════════════════════════════════════════════════════════════
# TACTICAL FINGERPRINT - Empreinte Tactique 13D
# ═══════════════════════════════════════════════════════════════════════════════════════

class TacticalFingerprint(BaseModel):
    """
    Empreinte tactique unique d'un coach en 13 dimensions (0-100 chacune).
    
    ═══════════════════════════════════════════════════════════════════════════════════
    PRINCIPE:
    Chaque coach a un "ADN tactique" mesurable. Deux coaches avec des fingerprints
    similaires produiront des matchs similaires. La distance dans l'espace 13D
    prédit le type de confrontation.
    ═══════════════════════════════════════════════════════════════════════════════════
    
    Dimensions:
    
    OFFENSIVE (1-4):
    1. verticality: Tiki-taka (0) → Direct/Long balls (100)
    2. tempo: Lent/Possession (0) → Rapide/Transitions (100)
    3. width_preference: Narrow/Central (0) → Wide/Wings (100)
    4. risk_in_buildup: Safe/Long (0) → Risqué/Short under pressure (100)
    
    DEFENSIVE (5-8):
    5. pressing_trigger_line: Low block (0) → High press (100)
    6. pressing_intensity: Passive (0) → Aggressive (100)
    7. defensive_line_height: Deep (0) → High (100)
    8. counter_press_intensity: Retreat (0) → Immediate gegenpressing (100)
    
    SPECIAL (9-13):
    9. set_piece_focus: Minimal (0) → Main weapon (100)
    10. tactical_flexibility: One system (0) → Chameleon (100)
    11. in_game_adjustments: Stubborn (0) → Reactive genius (100)
    12. youth_trust: Veterans only (0) → Academy promoter (100)
    13. structure_rigidity: Chaos/Fluid (0) → Rigid/Positional (100)
    
    Exemples de valeurs:
    ─────────────────────────────────────────────────────────────────────────────────
    Coach           | verticality | tempo | pressing | structure | Style dominant
    ─────────────────────────────────────────────────────────────────────────────────
    Guardiola       | 20          | 45    | 70       | 55        | Possession
    Klopp           | 55          | 78    | 75       | 40        | Gegenpressing
    Slot            | 55          | 71    | 70       | 45        | Hybrid
    Mourinho        | 60          | 35    | 30       | 75        | Low block
    Conte           | 50          | 55    | 55       | 90        | Rigid 3-5-2
    Simeone         | 65          | 40    | 35       | 85        | Attrition
    Bielsa          | 45          | 82    | 85       | 15        | Chaos pressing
    Gasperini       | 50          | 75    | 80       | 20        | Fluid 3-4-3
    Arteta          | 30          | 50    | 65       | 60        | Positional
    Dyche           | 85          | 30    | 25       | 80        | Direct/Physical
    ─────────────────────────────────────────────────────────────────────────────────
    """
    
    model_config = ConfigDict(frozen=False)
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # OFFENSIVE DIMENSIONS (1-4)
    # ─────────────────────────────────────────────────────────────────────────────────
    
    verticality: int = Field(
        ge=0, le=100,
        description="0=tiki-taka/short passes, 100=direct long balls. Guardiola=20, Dyche=85, Slot=55"
    )
    
    tempo: int = Field(
        ge=0, le=100,
        description="0=slow build-up, 100=rapid transitions. Ancelotti=40, Klopp=78, Nagelsmann=82"
    )
    
    width_preference: int = Field(
        ge=0, le=100,
        description="0=narrow/central play, 100=wide wing play. Conte=35, Guardiola=80"
    )
    
    risk_in_buildup: int = Field(
        ge=0, le=100,
        description="0=long balls from GK, 100=short passes under pressure. Allardyce=15, Arteta=82"
    )
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # DEFENSIVE DIMENSIONS (5-8)
    # ─────────────────────────────────────────────────────────────────────────────────
    
    pressing_trigger_line: int = Field(
        ge=0, le=100,
        description="0=ultra-low block, 100=ultra-high press. Simeone=35, Klopp=75, Slot=70"
    )
    
    pressing_intensity: int = Field(
        ge=0, le=100,
        description="0=passive defending, 100=aggressive gegenpressing. Mourinho=30, Slot=82, Marsch=90"
    )
    
    defensive_line_height: int = Field(
        ge=0, le=100,
        description="0=deep near GK, 100=high near midfield. Simeone=40, Arsenal=75, Bayern=80"
    )
    
    counter_press_intensity: int = Field(
        ge=0, le=100,
        description="0=organized retreat, 100=immediate counter-press. Mourinho=25, Klopp=92, Pep=85"
    )
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # SPECIAL DIMENSIONS (9-13)
    # ─────────────────────────────────────────────────────────────────────────────────
    
    set_piece_focus: int = Field(
        ge=0, le=100,
        description="0=little work on set pieces, 100=main weapon. Liverpool=45, Arsenal=78, Brentford=85"
    )
    
    tactical_flexibility: int = Field(
        ge=0, le=100,
        description="0=rigid one system, 100=chameleon multiple systems. Dyche=20, Ancelotti=85, Pep=70"
    )
    
    in_game_adjustments: int = Field(
        ge=0, le=100,
        description="0=stubborn, 100=constant effective changes. Lampard=35, Arteta=75, Ancelotti=88"
    )
    
    youth_trust: int = Field(
        ge=0, le=100,
        description="0=only veterans, 100=regularly promotes youth. Mourinho=25, Arteta=70, Slot=65"
    )
    
    structure_rigidity: int = Field(
        ge=0, le=100,
        description="""
        0=Chaos (positions fluid, man-marking, high variance → BTTS+8%, Over+5%)
        100=Rigid (fixed roles, zonal, low variance → Under+6%, CS+4%)
        
        Exemples:
        - Bielsa=15, Gasperini=20 (chaos volontaire)
        - Klopp=40, Slot=45 (semi-fluide)
        - Arteta=60, Mourinho=70 (structuré)
        - Conte=90, Simeone=85 (ultra-rigide)
        """
    )
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # COMPUTED PROPERTIES
    # ─────────────────────────────────────────────────────────────────────────────────
    
    @computed_field
    @property
    def fingerprint_vector(self) -> List[int]:
        """Vecteur 13D pour calculs de similarité."""
        return [
            self.verticality,
            self.tempo,
            self.width_preference,
            self.risk_in_buildup,
            self.pressing_trigger_line,
            self.pressing_intensity,
            self.defensive_line_height,
            self.counter_press_intensity,
            self.set_piece_focus,
            self.tactical_flexibility,
            self.in_game_adjustments,
            self.youth_trust,
            self.structure_rigidity,
        ]
    
    @computed_field
    @property
    def fingerprint_hash(self) -> str:
        """Hash unique pour comparaisons rapides."""
        vector_str = "-".join(str(v) for v in self.fingerprint_vector)
        return hashlib.md5(vector_str.encode()).hexdigest()[:12]
    
    def similarity_to(self, other: "TacticalFingerprint") -> float:
        """
        Calcule la similarité avec un autre fingerprint (0-100%).
        
        Formule: 100 * (1 - euclidean_distance / max_distance)
        Max distance = sqrt(13 * 100²) ≈ 361
        
        Args:
            other: Autre TacticalFingerprint à comparer
            
        Returns:
            Similarité en % (100 = identique, 0 = opposé total)
        """
        v1 = self.fingerprint_vector
        v2 = other.fingerprint_vector
        
        squared_diff = sum((a - b) ** 2 for a, b in zip(v1, v2))
        distance = math.sqrt(squared_diff)
        
        max_distance = math.sqrt(13 * 100 ** 2)  # ≈ 360.56
        similarity = 100 * (1 - distance / max_distance)
        
        return round(max(0, similarity), 1)
    
    def dimension_diff(self, other: "TacticalFingerprint") -> Dict[str, int]:
        """
        Retourne les différences par dimension.
        Utile pour identifier les contrastes tactiques.
        """
        dimensions = [
            "verticality", "tempo", "width_preference", "risk_in_buildup",
            "pressing_trigger_line", "pressing_intensity", "defensive_line_height",
            "counter_press_intensity", "set_piece_focus", "tactical_flexibility",
            "in_game_adjustments", "youth_trust", "structure_rigidity"
        ]
        
        return {
            dim: getattr(self, dim) - getattr(other, dim)
            for dim in dimensions
        }
    
    @computed_field
    @property
    def dominant_style(self) -> str:
        """
        Style dominant du coach.
        
        Returns:
            GEGENPRESSING: Pressing intense + tempo élevé
            POSSESSION: Low verticality + high risk in buildup
            LOW_BLOCK: Low pressing + low line height
            DIRECT: High verticality + low risk
            TRANSITION: High tempo + high counter-press
            FLUID_CHAOS: Low structure + high intensity
            RIGID_STRUCTURE: High structure + moderate pressing
            BALANCED: Pas de dominante claire
        """
        # Chaos fluide (Bielsa, Gasperini)
        if self.structure_rigidity < 30 and self.pressing_intensity > 70:
            return "FLUID_CHAOS"
        
        # Gegenpressing (Klopp, Slot)
        if self.pressing_intensity > 70 and self.counter_press_intensity > 75:
            return "GEGENPRESSING"
        
        # Possession (Guardiola)
        if self.verticality < 35 and self.risk_in_buildup > 70:
            return "POSSESSION"
        
        # Low block (Mourinho, Simeone)
        if self.pressing_trigger_line < 40 and self.defensive_line_height < 50:
            return "LOW_BLOCK"
        
        # Direct (Dyche, Allardyce)
        if self.verticality > 70 and self.risk_in_buildup < 40:
            return "DIRECT"
        
        # Transition (équipes de contre)
        if self.tempo > 70 and self.counter_press_intensity > 60:
            return "TRANSITION"
        
        # Structure rigide (Conte)
        if self.structure_rigidity > 80:
            return "RIGID_STRUCTURE"
        
        return "BALANCED"
    
    @computed_field
    @property
    def chaos_index(self) -> int:
        """
        Index de chaos tactique (0-100).
        
        Haut = Match ouvert, imprévisible, goals probables
        Bas = Match fermé, tactique, peu de goals
        
        Formule pondérée:
        - structure_rigidity inversé (x0.35)
        - tempo (x0.25)
        - pressing_intensity (x0.25)
        - risk_in_buildup (x0.15)
        """
        chaos = (
            (100 - self.structure_rigidity) * 0.35 +
            self.tempo * 0.25 +
            self.pressing_intensity * 0.25 +
            self.risk_in_buildup * 0.15
        )
        return round(chaos)
    
    @computed_field
    @property
    def predicted_match_profile(self) -> str:
        """
        Profil de match prédit basé sur le fingerprint.
        """
        chaos = self.chaos_index
        
        if chaos > 70:
            return "OPEN_HIGH_SCORING"
        elif chaos > 55:
            return "BALANCED_ACTION"
        elif chaos > 40:
            return "TACTICAL_BATTLE"
        elif chaos > 25:
            return "LOW_SCORING"
        else:
            return "DEFENSIVE_GRIND"


# ═══════════════════════════════════════════════════════════════════════════════════════
# SUBSTITUTION PROFILE
# ═══════════════════════════════════════════════════════════════════════════════════════

class SubstitutionProfile(BaseModel):
    """
    Profil de substitutions d'un coach.
    
    ═══════════════════════════════════════════════════════════════════════════════════
    INSIGHT CLÉ:
    Les patterns de substitutions révèlent:
    - La mentalité du coach (proactif vs réactif)
    - L'impact sur les Late Goals
    - La qualité du banc disponible
    ═══════════════════════════════════════════════════════════════════════════════════
    """
    
    model_config = ConfigDict(frozen=False)
    
    # Timing des changements
    first_sub_avg_minute: float = Field(
        ge=0, le=90,
        description="Minute moyenne du premier changement. <55'=proactif, >70'=réactif"
    )
    
    subs_per_match_avg: float = Field(
        ge=0, le=5,
        description="Nombre moyen de remplacements par match"
    )
    
    # Impact des remplaçants
    goals_by_subs: int = Field(
        ge=0,
        description="Buts marqués par des remplaçants (saison)"
    )
    
    assists_by_subs: int = Field(
        ge=0,
        description="Passes décisives par des remplaçants (saison)"
    )
    
    matches_analyzed: int = Field(
        ge=0,
        description="Nombre de matchs analysés pour ces stats"
    )
    
    # Type de changements
    attacking_subs_rate: float = Field(
        ge=0, le=100,
        description="% de changements offensifs (quand en difficulté)"
    )
    
    defensive_subs_rate: float = Field(
        ge=0, le=100,
        description="% de changements défensifs (quand en avance)"
    )
    
    like_for_like_rate: float = Field(
        ge=0, le=100,
        description="% de changements poste pour poste"
    )
    
    # AJUSTEMENT CRITIQUE #2: Qualité du banc
    bench_depth_score: float = Field(
        ge=0, le=100,
        description="""
        Qualité des remplaçants vs titulaires (0-100).
        
        Formule: avg(substitute_ratings) / avg(starter_ratings) * 100
        
        Exemples:
        - Man City = 85 (banc aussi fort que certains XI)
        - Liverpool = 70 (bon banc)
        - Promoted team = 30 (grosse chute de qualité)
        
        CRUCIAL: Sépare "mauvais coach" de "mauvais banc"
        - bench_depth < 50 AND first_sub > 70' = Late Collapse probable
        """
    )
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # COMPUTED PROPERTIES
    # ─────────────────────────────────────────────────────────────────────────────────
    
    @computed_field
    @property
    def sub_impact_per_match(self) -> float:
        """Impact moyen des remplaçants (G+A) par match."""
        if self.matches_analyzed == 0:
            return 0.0
        return round((self.goals_by_subs + self.assists_by_subs) / self.matches_analyzed, 2)
    
    @computed_field
    @property
    def sub_timing_profile(self) -> str:
        """
        Profil de timing des changements.
        
        Returns:
            PROACTIVE: Changements tôt (<55')
            BALANCED: Timing standard (55-65')
            CONSERVATIVE: Changements tardifs (65-75')
            LATE_REACTOR: Très tard (>75')
        """
        if self.first_sub_avg_minute < 55:
            return "PROACTIVE"
        elif self.first_sub_avg_minute < 65:
            return "BALANCED"
        elif self.first_sub_avg_minute < 75:
            return "CONSERVATIVE"
        else:
            return "LATE_REACTOR"
    
    @computed_field
    @property
    def late_collapse_risk(self) -> str:
        """
        Risque d'effondrement en fin de match.
        
        HIGH si:
        - Banc faible (bench_depth < 50) ET changements tardifs (>70')
        - OU très peu de changements (subs_per_match < 2)
        
        MEDIUM si:
        - Banc moyen (50-65) ET changements tardifs (>65')
        
        LOW sinon
        """
        if (self.bench_depth_score < 50 and self.first_sub_avg_minute > 70) or \
           (self.subs_per_match_avg < 2):
            return "HIGH"
        elif self.bench_depth_score < 65 and self.first_sub_avg_minute > 65:
            return "MEDIUM"
        else:
            return "LOW"
    
    @computed_field
    @property
    def bench_utilization_score(self) -> float:
        """
        Score d'utilisation du banc (0-100).
        Combine: timing, fréquence, et impact.
        """
        # Timing score (proactive = better)
        timing_score = max(0, 100 - (self.first_sub_avg_minute - 45) * 2)
        
        # Frequency score
        frequency_score = min(100, self.subs_per_match_avg * 25)
        
        # Impact score
        impact_score = min(100, self.sub_impact_per_match * 50)
        
        return round(timing_score * 0.3 + frequency_score * 0.3 + impact_score * 0.4, 1)


# ═══════════════════════════════════════════════════════════════════════════════════════
# GAME STATE REACTION PROFILE
# ═══════════════════════════════════════════════════════════════════════════════════════

class GameStateReactionProfile(BaseModel):
    """
    Comment le coach réagit selon l'état du score.
    
    ═══════════════════════════════════════════════════════════════════════════════════
    CRUCIAL pour:
    - Late Goals quand équipe mène (park bus vs continue pressing)
    - Comebacks quand équipe est menée (all-out attack vs pragmatic)
    - xG différentiel par game state
    ═══════════════════════════════════════════════════════════════════════════════════
    """
    
    model_config = ConfigDict(frozen=False)
    
    # Réactions par état
    when_winning: GameStateReaction = Field(
        default=GameStateReaction.CONTROL,
        description="Réaction quand mène de 1 but"
    )
    
    when_winning_big: GameStateReaction = Field(
        default=GameStateReaction.CONTROL,
        description="Réaction quand mène de 2+ buts"
    )
    
    when_drawing: GameStateReaction = Field(
        default=GameStateReaction.MAINTAIN,
        description="Réaction quand match nul"
    )
    
    when_losing: GameStateReaction = Field(
        default=GameStateReaction.PUSH_FORWARD,
        description="Réaction quand mené de 1 but"
    )
    
    when_losing_big: GameStateReaction = Field(
        default=GameStateReaction.ALL_OUT_ATTACK,
        description="Réaction quand mené de 2+ buts"
    )
    
    # Stats par game state
    xg_when_winning: float = Field(
        default=0, ge=0,
        description="xG/90 quand en avance"
    )
    
    xg_when_drawing: float = Field(
        default=0, ge=0,
        description="xG/90 quand à égalité"
    )
    
    xg_when_losing: float = Field(
        default=0, ge=0,
        description="xG/90 quand mené"
    )
    
    xga_when_winning: float = Field(
        default=0, ge=0,
        description="xGA/90 quand en avance"
    )
    
    xga_when_drawing: float = Field(
        default=0, ge=0,
        description="xGA/90 quand à égalité"
    )
    
    xga_when_losing: float = Field(
        default=0, ge=0,
        description="xGA/90 quand mené"
    )
    
    # Résultats historiques
    comeback_rate: float = Field(
        default=0, ge=0, le=100,
        description="% de matchs où l'équipe est revenue après avoir été menée"
    )
    
    collapse_rate: float = Field(
        default=0, ge=0, le=100,
        description="% de matchs où l'équipe a perdu l'avantage"
    )
    
    hold_rate: float = Field(
        default=0, ge=0, le=100,
        description="% de matchs où l'équipe a conservé l'avance"
    )
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # COMPUTED PROPERTIES
    # ─────────────────────────────────────────────────────────────────────────────────
    
    @computed_field
    @property
    def mental_strength_index(self) -> float:
        """
        Index de force mentale (0-100).
        Combine comeback_rate, hold_rate, et pénalise collapse_rate.
        """
        return round(50 + self.comeback_rate - (self.collapse_rate * 1.5), 1)
    
    @computed_field
    @property
    def attacking_mentality_when_behind(self) -> str:
        """
        Mentalité offensive quand mené.
        """
        if self.when_losing == GameStateReaction.ALL_OUT_ATTACK or \
           self.when_losing_big == GameStateReaction.ALL_OUT_ATTACK:
            return "ULTRA_AGGRESSIVE"
        elif self.when_losing == GameStateReaction.PUSH_FORWARD:
            return "AGGRESSIVE"
        elif self.when_losing == GameStateReaction.MAINTAIN:
            return "PATIENT"
        else:
            return "PASSIVE"
    
    @computed_field
    @property
    def defensive_solidity_when_ahead(self) -> str:
        """
        Solidité défensive quand en avance.
        """
        if self.when_winning == GameStateReaction.PARK_THE_BUS:
            return "FORTRESS"
        elif self.when_winning == GameStateReaction.CONTROL:
            return "SOLID"
        elif self.when_winning == GameStateReaction.MAINTAIN:
            return "BALANCED"
        else:
            return "VULNERABLE"
    
    @computed_field
    @property
    def late_drama_probability(self) -> str:
        """
        Probabilité de drama en fin de match.
        Basé sur les réactions extrêmes + variance xG.
        """
        drama_score = 0
        
        # Réactions agressives quand mené
        if self.when_losing in [GameStateReaction.ALL_OUT_ATTACK, GameStateReaction.PUSH_FORWARD]:
            drama_score += 25
        
        # Ne park pas le bus quand en avance
        if self.when_winning in [GameStateReaction.MAINTAIN, GameStateReaction.PUSH_FORWARD]:
            drama_score += 25
        
        # Taux de collapse élevé
        if self.collapse_rate > 20:
            drama_score += 30
        elif self.collapse_rate > 10:
            drama_score += 15
        
        # Taux de comeback élevé
        if self.comeback_rate > 25:
            drama_score += 20
        elif self.comeback_rate > 15:
            drama_score += 10
        
        if drama_score >= 60:
            return "HIGH"
        elif drama_score >= 35:
            return "MEDIUM"
        else:
            return "LOW"


# ═══════════════════════════════════════════════════════════════════════════════════════
# MARKET IMPACT PROFILE
# ═══════════════════════════════════════════════════════════════════════════════════════

class MarketImpactProfile(BaseModel):
    """
    Edges historiques du coach sur différents marchés.
    
    ═══════════════════════════════════════════════════════════════════════════════════
    AJUSTEMENT CRITIQUE #3: Public Perception Bias
    
    Le public surestime certains coachs (Guardiola, Klopp) → cotes écrasées
    Le public sous-estime d'autres (Moyes, Dyche) → value cachée
    
    public_perception_bias ajuste l'edge threshold:
    - OVERRATED: Need edge > 8% to bet (odds compressed)
    - UNDERRATED: Edge > 3% = actionable (hidden value)
    ═══════════════════════════════════════════════════════════════════════════════════
    """
    
    model_config = ConfigDict(frozen=False)
    
    # Edges par marché (ConfidentMetric pour inclure la confiance)
    btts_edge: Optional[ConfidentMetric] = None
    over_25_edge: Optional[ConfidentMetric] = None
    under_25_edge: Optional[ConfidentMetric] = None
    clean_sheet_edge: Optional[ConfidentMetric] = None
    first_half_goals_edge: Optional[ConfidentMetric] = None
    late_goals_edge: Optional[ConfidentMetric] = None
    corners_edge: Optional[ConfidentMetric] = None
    cards_edge: Optional[ConfidentMetric] = None
    
    # AJUSTEMENT CRITIQUE #3
    public_perception_bias: PublicPerceptionBias = Field(
        default=PublicPerceptionBias.NEUTRAL,
        description="""
        Biais de perception du public.
        
        HEAVILY_OVERRATED: Guardiola, Klopp (cotes très basses, peu de value)
        OVERRATED: Top coaches établis
        NEUTRAL: Perception juste
        UNDERRATED: Coaches efficaces mais ignorés
        HEAVILY_UNDERRATED: Moyes, Dyche (value max)
        """
    )
    
    public_bias_strength: int = Field(
        default=0, ge=-50, le=50,
        description="""
        Force du biais en points de cote implicite.
        
        +15 = Public surestime de ~15% (Guardiola)
        +8 = Légèrement surestimé
        0 = Perception juste
        -8 = Légèrement sous-estimé
        -12 = Public sous-estime de ~12% (Moyes)
        """
    )
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # COMPUTED PROPERTIES
    # ─────────────────────────────────────────────────────────────────────────────────
    
    @computed_field
    @property
    def best_market(self) -> Optional[str]:
        """Meilleur marché pour ce coach (edge le plus haut et fiable)."""
        markets = {
            "btts": self.btts_edge,
            "over_25": self.over_25_edge,
            "under_25": self.under_25_edge,
            "clean_sheet": self.clean_sheet_edge,
            "first_half_goals": self.first_half_goals_edge,
            "late_goals": self.late_goals_edge,
            "corners": self.corners_edge,
            "cards": self.cards_edge,
        }
        
        best = None
        best_weighted = -100
        
        for name, metric in markets.items():
            if metric and metric.is_reliable:
                if metric.weighted_value > best_weighted:
                    best_weighted = metric.weighted_value
                    best = name
        
        return best
    
    @computed_field
    @property
    def worst_market(self) -> Optional[str]:
        """Pire marché pour ce coach (edge le plus négatif)."""
        markets = {
            "btts": self.btts_edge,
            "over_25": self.over_25_edge,
            "under_25": self.under_25_edge,
            "clean_sheet": self.clean_sheet_edge,
            "first_half_goals": self.first_half_goals_edge,
            "late_goals": self.late_goals_edge,
            "corners": self.corners_edge,
            "cards": self.cards_edge,
        }
        
        worst = None
        worst_weighted = 100
        
        for name, metric in markets.items():
            if metric and metric.is_reliable:
                if metric.weighted_value < worst_weighted:
                    worst_weighted = metric.weighted_value
                    worst = name
        
        return worst
    
    @computed_field
    @property
    def contrarian_opportunity(self) -> str:
        """
        Identifie les opportunités contrarian.
        
        Returns:
            STRONG_BET: Coach sous-estimé avec edge
            FADE: Coach surestimé, éviter
            NEUTRAL: Pas d'avantage contrarian
        """
        if self.public_perception_bias in [
            PublicPerceptionBias.UNDERRATED,
            PublicPerceptionBias.HEAVILY_UNDERRATED
        ]:
            return "STRONG_BET"
        elif self.public_perception_bias in [
            PublicPerceptionBias.OVERRATED,
            PublicPerceptionBias.HEAVILY_OVERRATED
        ]:
            return "FADE"
        else:
            return "NEUTRAL"
    
    @computed_field
    @property
    def adjusted_edge_threshold(self) -> float:
        """
        Seuil d'edge ajusté selon le biais public.
        
        - Coach HEAVILY_OVERRATED: Need 8%+ edge (cotes écrasées)
        - Coach NEUTRAL: Need 5%+ edge
        - Coach HEAVILY_UNDERRATED: 3%+ edge suffisant (value cachée)
        """
        base_threshold = 5.0  # 5% par défaut
        
        # Ajuster selon le biais
        adjustment = self.public_bias_strength * 0.15
        
        return round(max(2.0, base_threshold + adjustment), 1)
    
    def is_bet_worthy(self, market_edge: float) -> bool:
        """
        Vérifie si l'edge est suffisant compte tenu du biais public.
        
        Args:
            market_edge: Edge calculé sur le marché (en %)
            
        Returns:
            True si l'edge dépasse le seuil ajusté
        """
        return market_edge >= self.adjusted_edge_threshold


# ═══════════════════════════════════════════════════════════════════════════════════════
# COACH DNA - Classe principale
# ═══════════════════════════════════════════════════════════════════════════════════════

class CoachDNA(QuantumBaseModel):
    """
    ADN complet d'un coach - Agrège tous les profils.
    
    ═══════════════════════════════════════════════════════════════════════════════════
    USAGE:
    
    >>> slot = CoachDNA(
    ...     name="Arne Slot",
    ...     current_team="Liverpool",
    ...     tactical_fingerprint=TacticalFingerprint(
    ...         verticality=55, tempo=71, pressing_intensity=82,
    ...         structure_rigidity=45, ...
    ...     ),
    ...     ...
    ... )
    >>> 
    >>> arteta = CoachDNA(name="Mikel Arteta", ...)
    >>> 
    >>> # Comparer les styles
    >>> slot.tactical_similarity(arteta)  # 86.6%
    >>> slot.tactical_diff(arteta)  # {'pressing_intensity': +7, 'structure': -15, ...}
    >>> 
    >>> # Prédire le type de match
    >>> slot.predict_matchup_style(arteta)  # "PRESSING_WAR"
    ═══════════════════════════════════════════════════════════════════════════════════
    """
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # IDENTITÉ
    # ─────────────────────────────────────────────────────────────────────────────────
    
    name: str = Field(description="Nom complet du coach")
    name_normalized: str = Field(default="", description="Nom normalisé pour matching")
    nationality: str = Field(default="", description="Nationalité")
    birth_year: Optional[int] = Field(default=None, ge=1940, le=2000)
    
    current_team: str = Field(description="Équipe actuelle")
    current_team_normalized: str = Field(default="", description="Équipe normalisée")
    tenure_months: int = Field(default=0, ge=0, description="Durée au poste actuel en mois")
    contract_until: Optional[int] = Field(default=None, ge=2024, le=2030)
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # CORE PROFILES
    # ─────────────────────────────────────────────────────────────────────────────────
    
    tactical_fingerprint: TacticalFingerprint
    
    formation_primary: Formation = Field(default=Formation.F_4_3_3)
    formation_secondary: Optional[Formation] = None
    formation_time_share: float = Field(
        default=100, ge=0, le=100,
        description="% du temps en formation principale"
    )
    
    substitutions: Optional[SubstitutionProfile] = None
    game_state_reactions: Optional[GameStateReactionProfile] = None
    market_impact: Optional[MarketImpactProfile] = None
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # CAREER STATS
    # ─────────────────────────────────────────────────────────────────────────────────
    
    career_matches: int = Field(default=0, ge=0)
    career_win_rate: float = Field(default=0, ge=0, le=100)
    career_draw_rate: float = Field(default=0, ge=0, le=100)
    career_goals_per_match: float = Field(default=0, ge=0)
    
    home_win_rate: float = Field(default=0, ge=0, le=100)
    away_win_rate: float = Field(default=0, ge=0, le=100)
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # METADATA
    # ─────────────────────────────────────────────────────────────────────────────────
    
    data_quality: DataQuality = Field(default=DataQuality.MODERATE)
    data_quality_score: float = Field(default=50, ge=0, le=100)
    matches_analyzed: int = Field(default=0, ge=0)
    confidence: float = Field(default=0.5, ge=0, le=1)
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # VALIDATORS
    # ─────────────────────────────────────────────────────────────────────────────────
    
    @field_validator("name_normalized", mode="before")
    @classmethod
    def auto_normalize_name(cls, v, info):
        """Auto-normalise le nom si vide."""
        if not v and "name" in info.data:
            return info.data["name"].lower().replace(" ", "_").replace("-", "_")
        return v
    
    @field_validator("current_team_normalized", mode="before")
    @classmethod
    def auto_normalize_team(cls, v, info):
        """Auto-normalise l'équipe si vide."""
        if not v and "current_team" in info.data:
            return info.data["current_team"].lower().replace(" ", "_").replace("-", "_")
        return v
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # METHODS
    # ─────────────────────────────────────────────────────────────────────────────────
    
    def tactical_similarity(self, other: "CoachDNA") -> float:
        """
        Calcule la similarité tactique avec un autre coach.
        
        Returns:
            Similarité en % (0-100)
        """
        return self.tactical_fingerprint.similarity_to(other.tactical_fingerprint)
    
    def tactical_diff(self, other: "CoachDNA") -> Dict[str, int]:
        """
        Retourne les différences tactiques avec un autre coach.
        """
        return self.tactical_fingerprint.dimension_diff(other.tactical_fingerprint)
    
    @computed_field
    @property
    def experience_tier(self) -> str:
        """
        Niveau d'expérience du coach.
        """
        if self.career_matches >= 500:
            return "ELITE"
        elif self.career_matches >= 300:
            return "EXPERIENCED"
        elif self.career_matches >= 150:
            return "ESTABLISHED"
        elif self.career_matches >= 50:
            return "DEVELOPING"
        else:
            return "ROOKIE"
    
    @computed_field
    @property
    def coaching_score(self) -> float:
        """
        Score global du coach (0-100).
        Combine: win rate, experience, tactical flexibility.
        """
        win_component = self.career_win_rate * 0.5
        
        # Experience component (diminishing returns)
        exp_normalized = min(100, self.career_matches / 5)
        exp_component = exp_normalized * 0.3
        
        # Flexibility component
        flex_component = self.tactical_fingerprint.tactical_flexibility * 0.2
        
        return round(win_component + exp_component + flex_component, 1)
    
    @computed_field
    @property
    def is_reliable_profile(self) -> bool:
        """True si le profil est statistiquement fiable."""
        return self.matches_analyzed >= 20 and self.confidence >= 0.6
    
    def predict_matchup_style(self, opponent_coach: "CoachDNA") -> str:
        """
        Prédit le style de confrontation contre un autre coach.
        
        Args:
            opponent_coach: Le coach adverse
            
        Returns:
            Type de matchup prédit (PRESSING_WAR, CHESS_MATCH, etc.)
        """
        similarity = self.tactical_similarity(opponent_coach)
        diff = self.tactical_diff(opponent_coach)
        
        my_fp = self.tactical_fingerprint
        opp_fp = opponent_coach.tactical_fingerprint
        
        # Miroir si très similaires
        if similarity > 85:
            return "MIRROR_MATCH"
        
        # Guerre de pressing si les deux pressent haut
        if my_fp.pressing_intensity > 70 and opp_fp.pressing_intensity > 70:
            return "PRESSING_WAR"
        
        # Possession vs bus
        if (my_fp.verticality < 35 and opp_fp.pressing_trigger_line < 40) or \
           (opp_fp.verticality < 35 and my_fp.pressing_trigger_line < 40):
            return "POSSESSION_VS_BUS"
        
        # Bataille d'attrition (deux blocs bas)
        if my_fp.pressing_trigger_line < 45 and opp_fp.pressing_trigger_line < 45:
            return "ATTRITION_BATTLE"
        
        # Chaos (deux structures fluides)
        if my_fp.structure_rigidity < 35 and opp_fp.structure_rigidity < 35:
            return "CHAOS_GAME"
        
        # Contre vs Possession
        if abs(diff.get("verticality", 0)) > 30 or abs(diff.get("tempo", 0)) > 30:
            return "COUNTER_VS_POSSESSION"
        
        # Échecs tactiques (deux tacticiens prudents)
        if my_fp.tactical_flexibility > 65 and opp_fp.tactical_flexibility > 65:
            return "CHESS_MATCH"
        
        # Fest de transitions (deux équipes verticales)
        if my_fp.tempo > 65 and opp_fp.tempo > 65:
            return "TRANSITION_FEST"
        
        # David vs Goliath (grande différence de niveau)
        coaching_gap = abs(self.coaching_score - opponent_coach.coaching_score)
        if coaching_gap > 25:
            return "DAVID_VS_GOLIATH"
        
        return "BALANCED_CONTEST"
