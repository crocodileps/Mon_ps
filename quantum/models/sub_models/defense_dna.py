"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║  DEFENSE DNA - Profil Défensif Complet                                               ║
║  Version: 2.0                                                                        ║
║  "Une défense se lit en xGA, mais ses faiblesses sont dans les détails."             ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

Architecture Mon_PS - Chess Engine V2.0
Créé le: 2025-12-10

Installation: /home/Mon_ps/quantum/models/sub_models/defense_dna.py

Sources de données:
- /home/Mon_ps/data/defense_dna/team_defense_dna_v5_1_corrected.json
- PostgreSQL: team_statistics, shots_against
"""

from pydantic import BaseModel, Field, ConfigDict, computed_field
from typing import Optional, Dict, List
from datetime import datetime

from ..base import QuantumBaseModel, ConfidentMetric, TimingMetric
from ..enums import DefenseProfile, DataQuality


# ═══════════════════════════════════════════════════════════════════════════════════════
# CORE DEFENSIVE METRICS
# ═══════════════════════════════════════════════════════════════════════════════════════

class DefensiveMetrics(BaseModel):
    """
    Métriques défensives brutes et avancées.
    """
    
    model_config = ConfigDict(frozen=False)
    
    # Goals Against
    goals_conceded: int = Field(default=0, ge=0)
    goals_conceded_per_match: float = Field(default=0, ge=0)
    
    # xGA (Expected Goals Against)
    xga_total: float = Field(default=0, ge=0)
    xga_per_match: ConfidentMetric = Field(default_factory=ConfidentMetric.zero)
    
    # Performance vs Expected
    goals_minus_xga: float = Field(
        default=0,
        description="Goals conceded - xGA. Négatif = surperformance défensive"
    )
    
    # Clean Sheets
    clean_sheets: int = Field(default=0, ge=0)
    clean_sheet_rate: float = Field(default=0, ge=0, le=100)
    
    # Shots Against
    shots_against_total: int = Field(default=0, ge=0)
    shots_against_per_match: float = Field(default=0, ge=0)
    shots_on_target_against_per_match: float = Field(default=0, ge=0)
    
    # Big Chances Against
    big_chances_conceded: int = Field(default=0, ge=0)
    big_chances_conceded_per_match: float = Field(default=0, ge=0)
    
    # Timing
    goals_conceded_timing: Optional[TimingMetric] = None
    xga_timing: Optional[TimingMetric] = None
    
    @computed_field
    @property
    def xga_overperformance(self) -> float:
        """
        % de surperformance défensive.
        Négatif = Mieux que xGA (bonne défense ou bon GK)
        Positif = Pire que xGA (mauvaise défense)
        """
        if self.xga_total == 0:
            return 0
        return round((self.goals_conceded - self.xga_total) / self.xga_total * 100, 1)
    
    @computed_field
    @property
    def defensive_solidity_rating(self) -> str:
        """Évaluation de la solidité défensive."""
        if self.xga_overperformance < -15:
            return "ELITE_DEFENSE"
        elif self.xga_overperformance < -5:
            return "SOLID"
        elif self.xga_overperformance < 5:
            return "AVERAGE"
        elif self.xga_overperformance < 15:
            return "LEAKY"
        else:
            return "CATASTROPHIC"


# ═══════════════════════════════════════════════════════════════════════════════════════
# ZONE VULNERABILITY
# ═══════════════════════════════════════════════════════════════════════════════════════

class ZoneVulnerability(BaseModel):
    """
    Vulnérabilité par zone du terrain.
    
    CRUCIAL pour identifier:
    - Faiblesse sur les côtés (full-backs exposés)
    - Faiblesse centrale (CB lents)
    - Faiblesse aérienne
    """
    
    model_config = ConfigDict(frozen=False)
    
    # Par zone latérale (% de xGA)
    xga_from_left: float = Field(default=33.3, ge=0, le=100)
    xga_from_center: float = Field(default=33.3, ge=0, le=100)
    xga_from_right: float = Field(default=33.3, ge=0, le=100)
    
    # Par zone verticale
    xga_from_box: float = Field(default=70, ge=0, le=100)
    xga_from_outside_box: float = Field(default=30, ge=0, le=100)
    
    # Types de buts concédés (% du total)
    goals_from_open_play: float = Field(default=60, ge=0, le=100)
    goals_from_set_pieces: float = Field(default=25, ge=0, le=100)
    goals_from_penalties: float = Field(default=10, ge=0, le=100)
    goals_from_counter: float = Field(default=15, ge=0, le=100)
    
    # Crosses
    crosses_faced_per_match: float = Field(default=0, ge=0)
    cross_success_against: float = Field(default=0, ge=0, le=100)
    
    # Aerial
    aerial_duels_lost_per_match: float = Field(default=0, ge=0)
    headers_conceded: int = Field(default=0, ge=0)
    
    @computed_field
    @property
    def weak_side(self) -> str:
        """Côté le plus vulnérable."""
        if self.xga_from_left > self.xga_from_right + 10:
            return "LEFT"
        elif self.xga_from_right > self.xga_from_left + 10:
            return "RIGHT"
        else:
            return "BALANCED"
    
    @computed_field
    @property
    def set_piece_vulnerability(self) -> str:
        """Vulnérabilité sur coups de pied arrêtés."""
        if self.goals_from_set_pieces > 35:
            return "CRITICAL"
        elif self.goals_from_set_pieces > 25:
            return "HIGH"
        elif self.goals_from_set_pieces > 15:
            return "MODERATE"
        else:
            return "LOW"
    
    @computed_field
    @property
    def counter_attack_vulnerability(self) -> str:
        """Vulnérabilité aux contres."""
        if self.goals_from_counter > 25:
            return "CRITICAL"
        elif self.goals_from_counter > 18:
            return "HIGH"
        elif self.goals_from_counter > 12:
            return "MODERATE"
        else:
            return "LOW"
    
    @computed_field
    @property
    def aerial_vulnerability(self) -> str:
        """Vulnérabilité aérienne."""
        # Basé sur headers concédés et duels perdus
        if self.aerial_duels_lost_per_match > 12:
            return "CRITICAL"
        elif self.aerial_duels_lost_per_match > 9:
            return "HIGH"
        elif self.aerial_duels_lost_per_match > 6:
            return "MODERATE"
        else:
            return "LOW"
    
    @computed_field
    @property
    def primary_weakness(self) -> str:
        """Faiblesse principale identifiée."""
        weaknesses = {
            "SET_PIECES": self.goals_from_set_pieces,
            "COUNTERS": self.goals_from_counter,
            "LEFT_SIDE": self.xga_from_left,
            "RIGHT_SIDE": self.xga_from_right,
        }
        return max(weaknesses, key=weaknesses.get)


# ═══════════════════════════════════════════════════════════════════════════════════════
# PRESSING RESISTANCE
# ═══════════════════════════════════════════════════════════════════════════════════════

class PressingResistance(BaseModel):
    """
    Capacité à résister au pressing adverse.
    
    CRUCIAL pour:
    - Matchups contre équipes pressing (Liverpool, Arsenal)
    - Identifier les équipes qui craquent sous pression
    """
    
    model_config = ConfigDict(frozen=False)
    
    # PPDA (Passes Per Defensive Action) faced
    ppda_faced: float = Field(
        default=10, ge=0,
        description="PPDA subi. Bas = adversaires pressent haut, Haut = pas pressés"
    )
    
    # Turnovers
    turnovers_per_match: float = Field(default=0, ge=0)
    turnovers_in_own_third: float = Field(default=0, ge=0)
    
    # Build-up success
    build_up_success_rate: float = Field(default=0, ge=0, le=100)
    
    # Goals from turnovers
    goals_conceded_from_turnovers: int = Field(default=0, ge=0)
    
    @computed_field
    @property
    def pressing_resistance_score(self) -> float:
        """
        Score de résistance au pressing (0-100).
        Haut = Résiste bien, Bas = Cède sous pression
        """
        # Pénaliser les turnovers dans son camp
        turnover_penalty = min(30, self.turnovers_in_own_third * 3)
        
        # Bonus pour bon taux de build-up
        buildup_bonus = self.build_up_success_rate * 0.5
        
        score = 50 + buildup_bonus - turnover_penalty
        return round(max(0, min(100, score)), 1)
    
    @computed_field
    @property
    def pressing_resistance_profile(self) -> str:
        """Profil de résistance au pressing."""
        score = self.pressing_resistance_score
        if score >= 75:
            return "PRESS_RESISTANT"
        elif score >= 55:
            return "SOLID"
        elif score >= 40:
            return "AVERAGE"
        elif score >= 25:
            return "VULNERABLE"
        else:
            return "COLLAPSE_PRONE"


# ═══════════════════════════════════════════════════════════════════════════════════════
# DEFENSIVE ACTIONS
# ═══════════════════════════════════════════════════════════════════════════════════════

class DefensiveActions(BaseModel):
    """
    Actions défensives: tacles, interceptions, duels.
    """
    
    model_config = ConfigDict(frozen=False)
    
    # Tackles
    tackles_per_match: float = Field(default=0, ge=0)
    tackles_won_rate: float = Field(default=0, ge=0, le=100)
    
    # Interceptions
    interceptions_per_match: float = Field(default=0, ge=0)
    
    # Clearances
    clearances_per_match: float = Field(default=0, ge=0)
    
    # Blocks
    blocks_per_match: float = Field(default=0, ge=0)
    shot_blocks_per_match: float = Field(default=0, ge=0)
    
    # Duels
    ground_duels_won_rate: float = Field(default=0, ge=0, le=100)
    aerial_duels_won_rate: float = Field(default=0, ge=0, le=100)
    
    # Fouls
    fouls_committed_per_match: float = Field(default=0, ge=0)
    
    @computed_field
    @property
    def defensive_activity_index(self) -> float:
        """
        Index d'activité défensive (0-100).
        Haut = Défense active (beaucoup d'actions)
        Bas = Défense passive ou dominante (peu d'actions nécessaires)
        """
        actions = (
            self.tackles_per_match * 3 +
            self.interceptions_per_match * 2 +
            self.clearances_per_match +
            self.blocks_per_match * 2
        )
        # Normaliser sur 100 (moyenne ~50)
        return round(min(100, actions * 2), 1)
    
    @computed_field
    @property
    def duel_dominance(self) -> str:
        """Dominance dans les duels."""
        avg = (self.ground_duels_won_rate + self.aerial_duels_won_rate) / 2
        if avg >= 55:
            return "DOMINANT"
        elif avg >= 50:
            return "WINNING"
        elif avg >= 45:
            return "EVEN"
        else:
            return "LOSING"


# ═══════════════════════════════════════════════════════════════════════════════════════
# DEFENSE DNA - Classe principale
# ═══════════════════════════════════════════════════════════════════════════════════════

class DefenseDNA(QuantumBaseModel):
    """
    ADN défensif complet d'une équipe.
    
    Agrège:
    - Métriques défensives (xGA, CS, timing)
    - Vulnérabilités par zone
    - Résistance au pressing
    - Actions défensives
    """
    
    # Identité
    team_name: str
    team_normalized: str = ""
    league: str = ""
    season: str = "2024-2025"
    
    # Sub-components
    core: DefensiveMetrics = Field(default_factory=DefensiveMetrics)
    zones: ZoneVulnerability = Field(default_factory=ZoneVulnerability)
    pressing: PressingResistance = Field(default_factory=PressingResistance)
    actions: DefensiveActions = Field(default_factory=DefensiveActions)
    
    # Home/Away splits
    xga_home: float = Field(default=0, ge=0)
    xga_away: float = Field(default=0, ge=0)
    clean_sheet_rate_home: float = Field(default=0, ge=0, le=100)
    clean_sheet_rate_away: float = Field(default=0, ge=0, le=100)
    
    # Metadata
    matches_analyzed: int = Field(default=0, ge=0)
    data_quality: DataQuality = Field(default=DataQuality.MODERATE)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    @computed_field
    @property
    def defense_profile(self) -> DefenseProfile:
        """Profil défensif global."""
        xga_pm = self.core.xga_per_match.value
        cs_rate = self.core.clean_sheet_rate
        
        if xga_pm < 0.9 and cs_rate > 40:
            return DefenseProfile.FORTRESS
        elif xga_pm < 1.2 and cs_rate > 30:
            return DefenseProfile.SOLID
        elif xga_pm < 1.5:
            return DefenseProfile.AVERAGE
        elif xga_pm < 2.0:
            return DefenseProfile.LEAKY
        else:
            return DefenseProfile.CATASTROPHIC
    
    @computed_field
    @property
    def goals_conceded_timing_signature(self) -> str:
        """Quand l'équipe encaisse le plus."""
        if self.core.goals_conceded_timing:
            return self.core.goals_conceded_timing.timing_signature
        return "BALANCED"
    
    @computed_field
    @property
    def late_collapse_risk(self) -> str:
        """
        Risque d'effondrement en fin de match.
        Basé sur le timing des buts encaissés.
        """
        if self.core.goals_conceded_timing:
            late_ratio = self.core.goals_conceded_timing.late_game_ratio
            if late_ratio > 0.45:
                return "HIGH"
            elif late_ratio > 0.35:
                return "MEDIUM"
        return "LOW"
    
    @computed_field
    @property
    def defensive_strength_score(self) -> float:
        """
        Score de force défensive (0-100).
        Combine: xGA, clean sheets, zones, pressing resistance.
        """
        # xGA component (inversé - moins = mieux)
        xga_score = max(0, 50 - (self.core.xga_per_match.value - 1.0) * 25)
        
        # Clean sheet component
        cs_score = self.core.clean_sheet_rate * 0.5
        
        # Pressing resistance
        pressing_score = self.pressing.pressing_resistance_score * 0.3
        
        final = xga_score * 0.5 + cs_score + pressing_score
        return round(max(0, min(100, final)), 1)
    
    @computed_field
    @property
    def home_away_defensive_diff(self) -> float:
        """Différence xGA home vs away."""
        return round(self.xga_home - self.xga_away, 2)
    
    @computed_field
    @property
    def exploitable_weaknesses(self) -> List[str]:
        """Liste des faiblesses exploitables identifiées."""
        weaknesses = []
        
        # Vulnérabilités zones
        if self.zones.set_piece_vulnerability in ["CRITICAL", "HIGH"]:
            weaknesses.append("SET_PIECES")
        
        if self.zones.counter_attack_vulnerability in ["CRITICAL", "HIGH"]:
            weaknesses.append("COUNTER_ATTACKS")
        
        if self.zones.aerial_vulnerability in ["CRITICAL", "HIGH"]:
            weaknesses.append("AERIAL")
        
        if self.zones.weak_side != "BALANCED":
            weaknesses.append(f"{self.zones.weak_side}_SIDE")
        
        # Pressing
        if self.pressing.pressing_resistance_profile in ["VULNERABLE", "COLLAPSE_PRONE"]:
            weaknesses.append("HIGH_PRESS")
        
        # Late game
        if self.late_collapse_risk == "HIGH":
            weaknesses.append("LATE_GAME")
        
        return weaknesses
    
    @computed_field
    @property
    def btts_no_probability_boost(self) -> float:
        """
        Boost de probabilité pour BTTS No.
        Basé sur la solidité défensive.
        """
        if self.defense_profile == DefenseProfile.FORTRESS:
            return 12.0
        elif self.defense_profile == DefenseProfile.SOLID:
            return 6.0
        elif self.defense_profile == DefenseProfile.AVERAGE:
            return 0.0
        elif self.defense_profile == DefenseProfile.LEAKY:
            return -5.0
        else:
            return -10.0
