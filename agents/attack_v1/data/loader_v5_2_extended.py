"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🎯 ATTACK DATA LOADER V5.2 EXTENDED - HEDGE FUND GRADE                      ║
║                                                                              ║
║  NOUVELLES DIMENSIONS V5.2:                                                  ║
║  ═══════════════════════════════════════════════════════════════════════════ ║
║  🎯 NP-CLINICAL DNA:                                                         ║
║     • np_overperformance = NPG - NPxG (vraie finition sans pénos)            ║
║     • Profils: TRUE_CLINICAL, CLINICAL, AVERAGE, WASTEFUL, PENALTY_INFLATED  ║
║     • Condition VOLUME: shots >= 10 (sinon UNPROVEN)                         ║
║                                                                              ║
║  🔗 xGCHAIN DNA:                                                             ║
║     • involvement_ratio = xGChain / (G+A) → implication cachée               ║
║     • buildup_ratio = xGBuildup / xGChain → PLAYMAKER vs BOX_CRASHER         ║
║     • Profils: BUILDUP_ARCHITECT, HIGH_INVOLVEMENT, BALANCED, FINISHER_ONLY  ║
║                                                                              ║
║  SOURCE: players_impact_dna.json + all_goals_2025.json (2025/2026 ONLY)      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from collections import defaultdict
import json

DATA_DIR = Path('/home/Mon_ps/data')


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def safe_int(v):
    """Convertit en int de façon sûre"""
    try: return int(float(v)) if v else 0
    except: return 0

def safe_float(v):
    """Convertit en float de façon sûre"""
    try: return float(v) if v else 0.0
    except: return 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# PLAYER PROFILE V5.2 - EXTENDED
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PlayerFullProfile2025Extended:
    """
    Profil COMPLET joueur 2025/2026 - VERSION EXTENDED V5.2
    
    Nouvelles dimensions:
    • NP-CLINICAL DNA (finition sans pénaltys)
    • xGCHAIN DNA (implication cachée + buildup)
    """
    player_id: str = ""
    player_name: str = ""
    team: str = ""
    league: str = ""
    position: str = ""
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VOLUMES (players_impact_dna)
    # ═══════════════════════════════════════════════════════════════════════════
    goals: int = 0
    npg: int = 0  # Non-penalty goals
    xG: float = 0.0
    npxG: float = 0.0
    assists: int = 0
    xA: float = 0.0
    shots: int = 0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PLAYING TIME (players_impact_dna)
    # ═══════════════════════════════════════════════════════════════════════════
    minutes: int = 0
    games: int = 0
    minutes_per_game: float = 0.0
    playing_time_profile: str = ""
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EFFICACITÉ CLASSIQUE
    # ═══════════════════════════════════════════════════════════════════════════
    goals_per_90: float = 0.0
    xG_per_90: float = 0.0
    minutes_per_goal: float = 0.0
    conversion_rate: float = 0.0
    xG_per_shot: float = 0.0
    xG_overperformance: float = 0.0
    shot_quality: str = ""
    finishing_trend: str = ""
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🆕 NP-CLINICAL DNA (NOUVEAU V5.2)
    # La VRAIE finition sans les pénaltys
    # ═══════════════════════════════════════════════════════════════════════════
    np_goals: int = 0                    # = npg (depuis data)
    np_xG: float = 0.0                   # = npxG (depuis data)
    np_overperformance: float = 0.0      # = npg - npxG (LE SCORE CLÉ)
    penalty_goals: int = 0               # = goals - npg
    penalty_dependency: float = 0.0      # = penalty_goals / goals * 100
    np_clinical_profile: str = ""        # TRUE_CLINICAL, CLINICAL, AVERAGE, WASTEFUL, PENALTY_INFLATED, UNPROVEN
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 🆕 xGCHAIN DNA (NOUVEAU V5.2)
    # Implication cachée dans les actions offensives
    # ═══════════════════════════════════════════════════════════════════════════
    xGChain: float = 0.0                 # Total xG des actions impliquées
    xGBuildup: float = 0.0               # xG des phases de construction
    direct_contributions: int = 0         # = goals + assists
    involvement_ratio: float = 0.0        # = xGChain / direct_contributions
    buildup_ratio: float = 0.0            # = xGBuildup / xGChain
    chain_profile: str = ""               # BUILDUP_ARCHITECT, HIGH_INVOLVEMENT, BALANCED, FINISHER_ONLY
    buildup_profile: str = ""             # PLAYMAKER, CONNECTOR, BOX_CRASHER
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CREATIVITY (players_impact_dna)
    # ═══════════════════════════════════════════════════════════════════════════
    key_passes: int = 0
    xA_per_90: float = 0.0
    creativity_profile: str = ""
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PENALTY
    # ═══════════════════════════════════════════════════════════════════════════
    penalty_pct: float = 0.0
    is_penalty_taker: bool = False
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CARDS (players_impact_dna)
    # ═══════════════════════════════════════════════════════════════════════════
    yellow_cards: int = 0
    red_cards: int = 0
    cards_per_90: float = 0.0
    card_profile: str = ""
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TIMING DNA (from all_goals_2025.json)
    # ═══════════════════════════════════════════════════════════════════════════
    goals_1h: int = 0
    goals_2h: int = 0
    goals_0_15: int = 0
    goals_16_30: int = 0
    goals_31_45: int = 0
    goals_46_60: int = 0
    goals_61_75: int = 0
    goals_76_90: int = 0
    goals_90_plus: int = 0
    
    pct_1h: float = 0.0
    pct_2h: float = 0.0
    pct_clutch: float = 0.0
    pct_early: float = 0.0
    timing_profile: str = ""
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STYLE DNA (from all_goals_2025.json)
    # ═══════════════════════════════════════════════════════════════════════════
    goals_open_play: int = 0
    goals_corner: int = 0
    goals_set_piece: int = 0
    goals_right_foot: int = 0
    goals_left_foot: int = 0
    goals_header: int = 0
    
    pct_open_play: float = 0.0
    pct_header: float = 0.0
    pct_set_piece: float = 0.0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HOME/AWAY DNA (from all_goals_2025.json)
    # ═══════════════════════════════════════════════════════════════════════════
    goals_home: int = 0
    goals_away: int = 0
    pct_home: float = 0.0
    home_away_ratio: float = 1.0
    home_away_profile: str = ""
    
    # ═══════════════════════════════════════════════════════════════════════════
    # TEAM CONTEXT
    # ═══════════════════════════════════════════════════════════════════════════
    team_goals: int = 0
    team_share: float = 0.0
    dependency_tag: str = ""
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SCORES COMPOSITES MARKET-SPECIFIC
    # ═══════════════════════════════════════════════════════════════════════════
    first_goalscorer_score: float = 0.0
    last_goalscorer_score: float = 0.0
    anytime_value_score: float = 0.0
    
    def calculate_all(self) -> None:
        """Calcule toutes les métriques - VERSION EXTENDED V5.2"""
        
        # ═══════════════════════════════════════════════════════════════════════
        # PLAYING TIME PROFILE
        # ═══════════════════════════════════════════════════════════════════════
        if self.games > 0:
            self.minutes_per_game = self.minutes / self.games
            
        # SUPER_SUB = peu de minutes MAIS très efficace
        if self.minutes >= 200 and self.minutes_per_game < 50 and self.goals >= 2:
            g90 = (self.goals / self.minutes) * 90 if self.minutes > 0 else 0
            if g90 >= 0.5:
                self.playing_time_profile = "SUPER_SUB"
            elif self.minutes_per_game >= 30:
                self.playing_time_profile = "ROTATION"
            else:
                self.playing_time_profile = "BENCH"
        elif self.minutes_per_game >= 85:
            self.playing_time_profile = "UNDISPUTED_STARTER"
        elif self.minutes_per_game >= 70:
            self.playing_time_profile = "STARTER"
        elif self.minutes_per_game >= 50:
            self.playing_time_profile = "REGULAR"
        elif self.minutes_per_game >= 30:
            self.playing_time_profile = "ROTATION"
        else:
            self.playing_time_profile = "BENCH"
            
        # ═══════════════════════════════════════════════════════════════════════
        # EFFICACITÉ CLASSIQUE
        # ═══════════════════════════════════════════════════════════════════════
        if self.minutes > 0:
            self.goals_per_90 = (self.goals / self.minutes) * 90
            self.xG_per_90 = (self.xG / self.minutes) * 90
            self.xA_per_90 = (self.xA / self.minutes) * 90
            self.cards_per_90 = ((self.yellow_cards + self.red_cards) / self.minutes) * 90
        if self.goals > 0:
            self.minutes_per_goal = self.minutes / self.goals
        if self.shots > 0:
            self.conversion_rate = (self.goals / self.shots) * 100
            self.xG_per_shot = self.xG / self.shots
            
        # xG overperformance classique
        self.xG_overperformance = self.goals - self.xG
        
        if self.xG_overperformance >= 4:
            self.finishing_trend = "HOT_STREAK"
        elif self.xG_overperformance >= 2:
            self.finishing_trend = "CLINICAL"
        elif self.xG_overperformance >= -1:
            self.finishing_trend = "EXPECTED"
        elif self.xG_overperformance >= -3:
            self.finishing_trend = "COLD"
        else:
            self.finishing_trend = "WASTEFUL"
            
        # ═══════════════════════════════════════════════════════════════════════
        # 🆕 NP-CLINICAL DNA (NOUVEAU V5.2)
        # ═══════════════════════════════════════════════════════════════════════
        self._calculate_np_clinical()
        
        # ═══════════════════════════════════════════════════════════════════════
        # 🆕 xGCHAIN DNA (NOUVEAU V5.2)
        # ═══════════════════════════════════════════════════════════════════════
        self._calculate_xgchain()
        
        # ═══════════════════════════════════════════════════════════════════════
        # SHOT QUALITY PROFILE
        # ═══════════════════════════════════════════════════════════════════════
        if self.shots >= 10:
            if self.conversion_rate >= 25 and self.xG_per_shot >= 0.12:
                self.shot_quality = "ELITE_FINISHER"
            elif self.conversion_rate >= 20:
                self.shot_quality = "CLINICAL"
            elif self.conversion_rate >= 15:
                self.shot_quality = "EFFICIENT"
            elif self.shots >= 30 and self.conversion_rate < 12:
                self.shot_quality = "VOLUME_SHOOTER"
            elif self.xG_per_shot >= 0.12 and self.conversion_rate < 10:
                self.shot_quality = "WASTEFUL"
            else:
                self.shot_quality = "AVERAGE"
        else:
            self.shot_quality = "LOW_VOLUME"
            
        # ═══════════════════════════════════════════════════════════════════════
        # PENALTY
        # ═══════════════════════════════════════════════════════════════════════
        self.penalty_goals = self.goals - self.npg
        if self.goals > 0:
            self.penalty_pct = (self.penalty_goals / self.goals) * 100
        self.is_penalty_taker = self.penalty_goals >= 2
        
        # ═══════════════════════════════════════════════════════════════════════
        # CARDS PROFILE
        # ═══════════════════════════════════════════════════════════════════════
        if self.cards_per_90 >= 0.4:
            self.card_profile = "DIRTY"
        elif self.cards_per_90 >= 0.25:
            self.card_profile = "AGGRESSIVE"
        else:
            self.card_profile = "CLEAN"
            
        # ═══════════════════════════════════════════════════════════════════════
        # CREATIVITY PROFILE
        # ═══════════════════════════════════════════════════════════════════════
        if self.xA >= 4 and self.assists >= 4:
            self.creativity_profile = "ELITE_CREATOR"
        elif self.xA >= 2.5 or self.assists >= 3:
            self.creativity_profile = "HIGH_CREATOR"
        elif self.goals >= 8 and self.xA < 2 and self.assists < 3:
            self.creativity_profile = "PURE_FINISHER"
        elif self.xA >= 1.5 or self.assists >= 2:
            self.creativity_profile = "CREATIVE"
        else:
            self.creativity_profile = "LIMITED"
            
        # ═══════════════════════════════════════════════════════════════════════
        # TIMING PROFILE
        # ═══════════════════════════════════════════════════════════════════════
        if self.goals > 0:
            total = self.goals
            self.pct_1h = (self.goals_1h / total) * 100
            self.pct_2h = (self.goals_2h / total) * 100
            self.pct_clutch = ((self.goals_76_90 + self.goals_90_plus) / total) * 100
            self.pct_early = (self.goals_0_15 / total) * 100
            
            if self.pct_2h >= 60:
                self.timing_profile = "DIESEL"
            elif self.pct_1h >= 55:
                self.timing_profile = "EARLY_BIRD"
            elif self.pct_clutch >= 25:
                self.timing_profile = "CLUTCH"
            elif self.pct_early >= 20:
                self.timing_profile = "EARLY_KILLER"
            else:
                self.timing_profile = "BALANCED"
                
        # ═══════════════════════════════════════════════════════════════════════
        # STYLE PERCENTAGES
        # ═══════════════════════════════════════════════════════════════════════
        if self.goals > 0:
            total = self.goals
            self.pct_open_play = (self.goals_open_play / total) * 100
            self.pct_header = (self.goals_header / total) * 100
            self.pct_set_piece = ((self.goals_corner + self.goals_set_piece) / total) * 100
            
        # ═══════════════════════════════════════════════════════════════════════
        # HOME/AWAY PROFILE
        # ═══════════════════════════════════════════════════════════════════════
        if self.goals > 0:
            self.pct_home = (self.goals_home / self.goals) * 100
        if self.goals_away > 0:
            self.home_away_ratio = self.goals_home / self.goals_away
        elif self.goals_home > 0:
            self.home_away_ratio = 5.0
            
        if self.home_away_ratio >= 2.5:
            self.home_away_profile = "HOME_SPECIALIST"
        elif self.home_away_ratio <= 0.4:
            self.home_away_profile = "AWAY_SPECIALIST"
        else:
            self.home_away_profile = "BALANCED"
            
        # ═══════════════════════════════════════════════════════════════════════
        # TEAM DEPENDENCY
        # ═══════════════════════════════════════════════════════════════════════
        if self.team_goals > 0:
            self.team_share = (self.goals / self.team_goals) * 100
        if self.team_share >= 30:
            self.dependency_tag = "MVP"
        elif self.team_share >= 18:
            self.dependency_tag = "KEY_PLAYER"
        elif self.team_share >= 8:
            self.dependency_tag = "CONTRIBUTOR"
        else:
            self.dependency_tag = "ROTATIONAL"
            
        # ═══════════════════════════════════════════════════════════════════════
        # SCORES COMPOSITES MARKET-SPECIFIC
        # ═══════════════════════════════════════════════════════════════════════
        self._calculate_market_scores()
        
    def _calculate_np_clinical(self) -> None:
        """
        🆕 NP-CLINICAL DNA - La VRAIE finition sans pénaltys
        
        Profils:
        • TRUE_CLINICAL: np_overperf >= +3.0 ET shots >= 10
        • CLINICAL: np_overperf >= +1.5 ET shots >= 10
        • AVERAGE: -1.5 < np_overperf < +1.5
        • WASTEFUL: np_overperf <= -1.5 ET shots >= 10
        • PENALTY_INFLATED: penalty_dep >= 25% ET np_overperf < 0
        • UNPROVEN: shots < 10
        """
        # Données brutes depuis players_impact_dna
        self.np_goals = self.npg
        self.np_xG = self.npxG
        
        # Calcul du score clé
        self.np_overperformance = self.np_goals - self.np_xG
        
        # Calcul penalty dependency
        self.penalty_goals = self.goals - self.npg
        if self.goals > 0:
            self.penalty_dependency = (self.penalty_goals / self.goals) * 100
        else:
            self.penalty_dependency = 0.0
            
        # ───────────────────────────────────────────────────────────────────────
        # Classification NP-CLINICAL
        # ───────────────────────────────────────────────────────────────────────
        
        # CONDITION VOLUME: Sans assez de tirs, pas de conclusion
        if self.shots < 10:
            self.np_clinical_profile = "UNPROVEN"
            return
            
        # PENALTY_INFLATED: Dépendant aux pénos ET sous-performe en open play
        if self.penalty_dependency >= 25 and self.np_overperformance < 0:
            self.np_clinical_profile = "PENALTY_INFLATED"
            return
            
        # Classification par overperformance
        if self.np_overperformance >= 3.0:
            self.np_clinical_profile = "TRUE_CLINICAL"
        elif self.np_overperformance >= 1.5:
            self.np_clinical_profile = "CLINICAL"
        elif self.np_overperformance > -1.5:
            self.np_clinical_profile = "AVERAGE"
        else:
            self.np_clinical_profile = "WASTEFUL"
            
    def _calculate_xgchain(self) -> None:
        """
        🆕 xGCHAIN DNA - Implication cachée + Buildup profile
        
        Chain Profils:
        • BUILDUP_ARCHITECT: ratio >= 3.0 (impliqué partout, finit rien) → ASSISTS
        • HIGH_INVOLVEMENT: ratio >= 2.0 (au-delà des stats)
        • BALANCED: 1.0 <= ratio < 2.0
        • FINISHER_ONLY: ratio < 1.0 (pure finition) → GOALS si équipe domine
        
        Buildup Profils:
        • PLAYMAKER: buildup_ratio >= 0.6 (impliqué dans la construction)
        • CONNECTOR: 0.4 <= buildup_ratio < 0.6
        • BOX_CRASHER: buildup_ratio < 0.4 (présent que dans la surface)
        """
        # Calcul des contributions directes
        self.direct_contributions = self.goals + self.assists
        
        # ───────────────────────────────────────────────────────────────────────
        # Involvement Ratio
        # ───────────────────────────────────────────────────────────────────────
        if self.direct_contributions > 0:
            self.involvement_ratio = self.xGChain / self.direct_contributions
        elif self.xGChain > 0:
            # Si 0 G+A mais xGChain > 0, le joueur est très impliqué sans finir
            self.involvement_ratio = self.xGChain * 2  # Multiplicateur pour marquer l'anomalie
        else:
            self.involvement_ratio = 0.0
            
        # ───────────────────────────────────────────────────────────────────────
        # Buildup Ratio
        # ───────────────────────────────────────────────────────────────────────
        if self.xGChain > 0:
            self.buildup_ratio = self.xGBuildup / self.xGChain
        else:
            self.buildup_ratio = 0.0
            
        # ───────────────────────────────────────────────────────────────────────
        # Classification Chain Profile
        # ───────────────────────────────────────────────────────────────────────
        if self.involvement_ratio >= 3.0:
            self.chain_profile = "BUILDUP_ARCHITECT"
        elif self.involvement_ratio >= 2.0:
            self.chain_profile = "HIGH_INVOLVEMENT"
        elif self.involvement_ratio >= 1.0:
            self.chain_profile = "BALANCED"
        else:
            self.chain_profile = "FINISHER_ONLY"
            
        # ───────────────────────────────────────────────────────────────────────
        # Classification Buildup Profile
        # ───────────────────────────────────────────────────────────────────────
        if self.buildup_ratio >= 0.6:
            self.buildup_profile = "PLAYMAKER"
        elif self.buildup_ratio >= 0.4:
            self.buildup_profile = "CONNECTOR"
        else:
            self.buildup_profile = "BOX_CRASHER"
        
    def _calculate_market_scores(self) -> None:
        """Calcule les scores composites pour chaque marché"""
        
        # ───────────────────────────────────────────────────────────────────────
        # FIRST GOALSCORER SCORE
        # ───────────────────────────────────────────────────────────────────────
        score = 0.0
        
        # Timing 1H (max 40 pts)
        if self.pct_1h >= 70:
            score += 40
        elif self.pct_1h >= 60:
            score += 35
        elif self.pct_1h >= 55:
            score += 30
        elif self.pct_1h >= 50:
            score += 20
            
        # Titulaire (max 25 pts)
        if self.playing_time_profile == "UNDISPUTED_STARTER":
            score += 25
        elif self.playing_time_profile == "STARTER":
            score += 20
        elif self.playing_time_profile == "REGULAR":
            score += 10
            
        # Penalty taker bonus (max 15 pts)
        if self.is_penalty_taker:
            score += 15
            
        # Volume (max 20 pts)
        if self.goals >= 10:
            score += 20
        elif self.goals >= 7:
            score += 15
        elif self.goals >= 5:
            score += 10
        elif self.goals >= 3:
            score += 5
            
        # Early Killer bonus
        if self.pct_early >= 25:
            score += 10
            
        self.first_goalscorer_score = score
        
        # ───────────────────────────────────────────────────────────────────────
        # LAST GOALSCORER SCORE
        # ───────────────────────────────────────────────────────────────────────
        score = 0.0
        
        # Timing 2H (max 35 pts)
        if self.pct_2h >= 80:
            score += 35
        elif self.pct_2h >= 70:
            score += 30
        elif self.pct_2h >= 60:
            score += 25
        elif self.pct_2h >= 50:
            score += 15
            
        # Clutch (max 30 pts)
        if self.pct_clutch >= 50:
            score += 30
        elif self.pct_clutch >= 35:
            score += 25
        elif self.pct_clutch >= 25:
            score += 20
        elif self.pct_clutch >= 15:
            score += 10
            
        # SUPER_SUB bonus (max 25 pts)
        if self.playing_time_profile == "SUPER_SUB":
            score += 25
            if self.goals_per_90 >= 0.8:
                score += 10
            elif self.goals_per_90 >= 0.6:
                score += 5
                
        # Volume (max 15 pts)
        if self.goals >= 7:
            score += 15
        elif self.goals >= 5:
            score += 10
        elif self.goals >= 3:
            score += 5
            
        self.last_goalscorer_score = score
        
        # ───────────────────────────────────────────────────────────────────────
        # ANYTIME VALUE SCORE (Régression positive attendue)
        # Utilise NP-CLINICAL pour évaluer plus finement
        # ───────────────────────────────────────────────────────────────────────
        score = 0.0
        
        # xG élevé (max 40 pts)
        if self.xG >= 12:
            score += 40
        elif self.xG >= 9:
            score += 35
        elif self.xG >= 6:
            score += 25
        elif self.xG >= 4:
            score += 15
        elif self.xG >= 2:
            score += 5
            
        # Sous-performance NP (max 35 pts) - UTILISE NP_OVERPERFORMANCE
        if self.np_overperformance <= -4:
            score += 35
        elif self.np_overperformance <= -3:
            score += 30
        elif self.np_overperformance <= -2:
            score += 25
        elif self.np_overperformance <= -1:
            score += 15
        elif self.np_overperformance <= 0:
            score += 5
            
        # Volume shots (max 15 pts)
        if self.shots >= 40:
            score += 15
        elif self.shots >= 30:
            score += 10
        elif self.shots >= 20:
            score += 5
            
        # Malus si VRAIMENT wasteful chronique
        if self.np_clinical_profile == "WASTEFUL" and self.shots >= 20:
            score -= 15
            
        # Bonus si clinical de base (juste malchance récente)
        if self.np_clinical_profile in ["TRUE_CLINICAL", "CLINICAL"]:
            score += 10
            
        self.anytime_value_score = max(0, score)


# ═══════════════════════════════════════════════════════════════════════════════
# TEAM PROFILE V5.2
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TeamProfile2025Extended:
    """Profil équipe 2025/2026 - VERSION EXTENDED"""
    team_name: str = ""
    league: str = ""
    goals: int = 0
    xG: float = 0.0
    players: List[PlayerFullProfile2025Extended] = field(default_factory=list)
    
    # Timing DNA
    goals_1h: int = 0
    goals_2h: int = 0
    pct_2h: float = 0.0
    timing_profile: str = ""
    
    # Context DNA
    timing_xg: Dict = field(default_factory=dict)
    gamestate_xg: Dict = field(default_factory=dict)
    attack_speed: Dict = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# LOADER V5.2 EXTENDED
# ═══════════════════════════════════════════════════════════════════════════════

class AttackDataLoaderV52Extended:
    """
    Loader V5.2 EXTENDED - HEDGE FUND GRADE
    
    Nouvelles fonctionnalités:
    • NP-CLINICAL DNA (finition sans pénaltys)
    • xGCHAIN DNA (implication cachée)
    • Getters spécialisés pour betting
    """
    
    def __init__(self):
        self.players: Dict[str, PlayerFullProfile2025Extended] = {}
        self.teams: Dict[str, TeamProfile2025Extended] = {}
        self.context_dna = {}
        
    def load_all(self) -> None:
        """Charge et fusionne toutes les sources"""
        print("=" * 80)
        print("🎯 ATTACK DATA LOADER V5.2 EXTENDED - HEDGE FUND GRADE")
        print("=" * 80)
        
        self._load_players_impact_dna()
        self._load_goals_timing_style()
        self._load_context_dna()
        self._aggregate_teams()
        self._calculate_all()
        
        print(f"\n✅ Chargement COMPLET 2025/2026:")
        print(f"   • {len(self.players)} joueurs avec profil EXTENDED")
        print(f"   • {len(self.teams)} équipes")
        
    def _load_players_impact_dna(self) -> None:
        """Charge players_impact_dna.json - AVEC npg, npxG, xGChain, xGBuildup"""
        print("\n📊 [1/4] Chargement players_impact_dna.json...")
        
        path = DATA_DIR / 'quantum_v2/players_impact_dna.json'
        with open(path) as f:
            data = json.load(f)
            
        for pid, player in data.items():
            if not isinstance(player, dict):
                continue
                
            name = player.get('player_name', '')
            team = player.get('team_title', '')
            if not name or not team:
                continue
                
            key = f"{name}|{team}"
            p = PlayerFullProfile2025Extended(
                player_id=pid,
                player_name=name,
                team=team,
                league=player.get('league', ''),
                position=player.get('position', ''),
                # Volumes
                goals=safe_int(player.get('goals', 0)),
                npg=safe_int(player.get('npg', 0)),
                xG=safe_float(player.get('xG', 0)),
                npxG=safe_float(player.get('npxG', 0)),
                assists=safe_int(player.get('assists', 0)),
                xA=safe_float(player.get('xA', 0)),
                shots=safe_int(player.get('shots', 0)),
                # Playing time
                minutes=safe_int(player.get('time', 0)),
                games=safe_int(player.get('games', 0)),
                # xGChain DNA (NOUVEAU)
                xGChain=safe_float(player.get('xGChain', 0)),
                xGBuildup=safe_float(player.get('xGBuildup', 0)),
                # Creativity
                key_passes=safe_int(player.get('key_passes', 0)),
                # Cards
                yellow_cards=safe_int(player.get('yellow_cards', 0)),
                red_cards=safe_int(player.get('red_cards', 0)),
            )
            self.players[key] = p
            
        print(f"   ✅ {len(self.players)} joueurs chargés")
        
    def _load_goals_timing_style(self) -> None:
        """Charge all_goals_2025.json pour timing et style"""
        print("\n📊 [2/4] Chargement all_goals_2025.json...")
        
        path = DATA_DIR / 'goal_analysis/all_goals_2025.json'
        with open(path) as f:
            goals = json.load(f)
            
        goals_enriched = 0
        for g in goals:
            scorer = g.get('scorer', '')
            team = g.get('scoring_team', '')
            key = f"{scorer}|{team}"
            
            if key not in self.players:
                continue
                
            p = self.players[key]
            goals_enriched += 1
            
            # Timing
            half = g.get('half', '')
            if half == '1H':
                p.goals_1h += 1
            else:
                p.goals_2h += 1
                
            period = g.get('timing_period', '')
            period_map = {
                '0-15': 'goals_0_15', '16-30': 'goals_16_30', '31-45': 'goals_31_45',
                '46-60': 'goals_46_60', '61-75': 'goals_61_75', '76-90': 'goals_76_90',
                '90+': 'goals_90_plus'
            }
            if period in period_map:
                attr = period_map[period]
                setattr(p, attr, getattr(p, attr) + 1)
                
            # Style
            situation = g.get('situation', '')
            if 'Corner' in situation:
                p.goals_corner += 1
            elif 'Freekick' in situation or 'SetPiece' in situation:
                p.goals_set_piece += 1
            else:
                p.goals_open_play += 1
                
            shot = g.get('shot_type', '')
            if shot == 'RightFoot':
                p.goals_right_foot += 1
            elif shot == 'LeftFoot':
                p.goals_left_foot += 1
            elif shot == 'Head':
                p.goals_header += 1
                
            # Home/Away
            if g.get('home_away') == 'h':
                p.goals_home += 1
            else:
                p.goals_away += 1
                
        print(f"   ✅ {len(goals)} buts, {goals_enriched} enrichissements")
        
    def _load_context_dna(self) -> None:
        """Charge teams_context_dna.json"""
        print("\n📊 [3/4] Chargement teams_context_dna.json...")
        
        path = DATA_DIR / 'quantum_v2/teams_context_dna.json'
        with open(path) as f:
            self.context_dna = json.load(f)
            
        print(f"   ✅ {len(self.context_dna)} équipes")
        
    def _aggregate_teams(self) -> None:
        """Agrège par équipe"""
        print("\n📊 [4/4] Agrégation par équipe...")
        
        players_by_team = defaultdict(list)
        for p in self.players.values():
            players_by_team[p.team].append(p)
            
        for team_name, players in players_by_team.items():
            team = TeamProfile2025Extended(
                team_name=team_name,
                players=players,
                goals=sum(p.goals for p in players),
                xG=sum(p.xG for p in players)
            )
            
            if team_name in self.context_dna:
                ctx = self.context_dna[team_name]
                team.league = ctx.get('league', '')
                if 'raw_statistics' in ctx:
                    raw = ctx['raw_statistics']
                    team.timing_xg = raw.get('timing', {})
                    team.gamestate_xg = raw.get('gameState', {})
                if 'context_dna' in ctx:
                    team.attack_speed = ctx['context_dna'].get('attackSpeed', {})
                    
            self.teams[team_name] = team
            
        print(f"   ✅ {len(self.teams)} équipes")
        
    def _calculate_all(self) -> None:
        """Calcule toutes les métriques"""
        print("\n📊 Calcul des métriques EXTENDED V5.2...")
        
        team_goals = {t: team.goals for t, team in self.teams.items()}
        
        insights = defaultdict(list)
        
        for p in self.players.values():
            p.team_goals = team_goals.get(p.team, 0)
            p.calculate_all()
            
            # ═══════════════════════════════════════════════════════════════════
            # COLLECTER INSIGHTS NP-CLINICAL
            # ═══════════════════════════════════════════════════════════════════
            if p.np_clinical_profile == "TRUE_CLINICAL" and p.goals >= 3:
                insights['true_clinical'].append(p)
            if p.np_clinical_profile == "CLINICAL" and p.goals >= 3:
                insights['clinical'].append(p)
            if p.np_clinical_profile == "PENALTY_INFLATED":
                insights['penalty_inflated'].append(p)
            if p.np_clinical_profile == "WASTEFUL" and p.goals >= 3:
                insights['np_wasteful'].append(p)
                
            # ═══════════════════════════════════════════════════════════════════
            # COLLECTER INSIGHTS xGCHAIN
            # ═══════════════════════════════════════════════════════════════════
            if p.chain_profile == "BUILDUP_ARCHITECT" and p.xGChain >= 3:
                insights['buildup_architect'].append(p)
            if p.chain_profile == "FINISHER_ONLY" and p.goals >= 3:
                insights['finisher_only'].append(p)
            if p.buildup_profile == "PLAYMAKER" and p.xGChain >= 2:
                insights['playmaker'].append(p)
            if p.buildup_profile == "BOX_CRASHER" and p.goals >= 3:
                insights['box_crasher'].append(p)
                
            # ═══════════════════════════════════════════════════════════════════
            # AUTRES INSIGHTS
            # ═══════════════════════════════════════════════════════════════════
            if p.goals >= 3:
                if p.timing_profile == "DIESEL":
                    insights['diesel'].append(p)
                elif p.timing_profile == "EARLY_BIRD":
                    insights['early_bird'].append(p)
                if p.pct_clutch >= 25:
                    insights['clutch'].append(p)
                if p.shot_quality == "ELITE_FINISHER":
                    insights['elite'].append(p)
                if p.finishing_trend == "HOT_STREAK":
                    insights['hot_streak'].append(p)
                if p.is_penalty_taker:
                    insights['penalty'].append(p)
                if p.xG >= 6 and p.xG_overperformance <= -2:
                    insights['value_regression'].append(p)
            if p.playing_time_profile == "SUPER_SUB" and p.goals >= 2:
                insights['super_sub'].append(p)
            if p.creativity_profile == "ELITE_CREATOR":
                insights['creator'].append(p)
            if p.first_goalscorer_score >= 60 and p.goals >= 3:
                insights['first_gs_candidates'].append(p)
            if p.last_goalscorer_score >= 60 and p.goals >= 3:
                insights['last_gs_candidates'].append(p)
                
        # ═══════════════════════════════════════════════════════════════════════
        # AFFICHER INSIGHTS
        # ═══════════════════════════════════════════════════════════════════════
        print(f"\n   📊 INSIGHTS V5.2 EXTENDED 2025/2026:")
        print(f"\n   🎯 NP-CLINICAL DNA:")
        print(f"      • {len(insights['true_clinical'])} TRUE_CLINICAL (np_overperf >= +3.0)")
        print(f"      • {len(insights['clinical'])} CLINICAL (np_overperf >= +1.5)")
        print(f"      • {len(insights['penalty_inflated'])} PENALTY_INFLATED (⚠️ dep >= 25%)")
        print(f"      • {len(insights['np_wasteful'])} NP_WASTEFUL (np_overperf <= -1.5)")
        
        print(f"\n   🔗 xGCHAIN DNA:")
        print(f"      • {len(insights['buildup_architect'])} BUILDUP_ARCHITECT (ratio >= 3.0)")
        print(f"      • {len(insights['finisher_only'])} FINISHER_ONLY (ratio < 1.0)")
        print(f"      • {len(insights['playmaker'])} PLAYMAKER (buildup >= 0.6)")
        print(f"      • {len(insights['box_crasher'])} BOX_CRASHER (buildup < 0.4)")
        
        print(f"\n   ⏱️ TIMING DNA:")
        print(f"      • {len(insights['early_bird'])} EARLY_BIRD (55%+ 1H)")
        print(f"      • {len(insights['diesel'])} DIESEL (60%+ 2H)")
        print(f"      • {len(insights['clutch'])} CLUTCH (25%+ après 75')")
        print(f"      • {len(insights['super_sub'])} SUPER_SUB")
        
        print(f"\n   📈 FORM DNA:")
        print(f"      • {len(insights['hot_streak'])} HOT_STREAK (+4 xG)")
        print(f"      • {len(insights['value_regression'])} VALUE REGRESSION")
        
        print(f"\n   🎯 MARKET CANDIDATES:")
        print(f"      • {len(insights['first_gs_candidates'])} FIRST GOALSCORER (score >= 60)")
        print(f"      • {len(insights['last_gs_candidates'])} LAST GOALSCORER (score >= 60)")
        print(f"      • {len(insights['penalty'])} PENALTY TAKERS")
        print(f"      • {len(insights['elite'])} ELITE_FINISHER")
        print(f"      • {len(insights['creator'])} ELITE_CREATOR")
        
    # ═══════════════════════════════════════════════════════════════════════════
    # GETTERS BASIQUES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_team(self, name: str) -> Optional[TeamProfile2025Extended]:
        return self.teams.get(name)
        
    def get_player(self, name: str, team: str = None) -> Optional[PlayerFullProfile2025Extended]:
        if team:
            return self.players.get(f"{name}|{team}")
        for p in self.players.values():
            if p.player_name == name:
                return p
        return None
        
    def get_top_scorers(self, team: str = None, n: int = 10) -> List[PlayerFullProfile2025Extended]:
        if team:
            players = [p for p in self.players.values() if p.team == team]
        else:
            players = list(self.players.values())
        return sorted(players, key=lambda p: -p.goals)[:n]
        
    # ═══════════════════════════════════════════════════════════════════════════
    # 🆕 GETTERS NP-CLINICAL
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_true_clinical_finishers(self, min_goals: int = 3) -> List[PlayerFullProfile2025Extended]:
        """TRUE_CLINICAL: np_overperf >= +3.0 ET shots >= 10 → MAX BET Anytime"""
        return sorted(
            [p for p in self.players.values() 
             if p.np_clinical_profile == "TRUE_CLINICAL" and p.goals >= min_goals],
            key=lambda x: -x.np_overperformance
        )
        
    def get_clinical_finishers(self, min_goals: int = 3) -> List[PlayerFullProfile2025Extended]:
        """CLINICAL: np_overperf >= +1.5 ET shots >= 10 → BACK Anytime"""
        return sorted(
            [p for p in self.players.values() 
             if p.np_clinical_profile in ["TRUE_CLINICAL", "CLINICAL"] and p.goals >= min_goals],
            key=lambda x: -x.np_overperformance
        )
        
    def get_penalty_inflated_players(self) -> List[PlayerFullProfile2025Extended]:
        """PENALTY_INFLATED: dep >= 25% ET np_overperf < 0 → ⚠️ AVOID si pas péno"""
        return sorted(
            [p for p in self.players.values() 
             if p.np_clinical_profile == "PENALTY_INFLATED"],
            key=lambda x: -x.penalty_dependency
        )
        
    def get_np_wasteful_players(self, min_goals: int = 2) -> List[PlayerFullProfile2025Extended]:
        """NP_WASTEFUL: np_overperf <= -1.5 → VALUE si pas chronique"""
        return sorted(
            [p for p in self.players.values() 
             if p.np_clinical_profile == "WASTEFUL" and p.goals >= min_goals],
            key=lambda x: x.np_overperformance
        )
        
    # ═══════════════════════════════════════════════════════════════════════════
    # 🆕 GETTERS xGCHAIN
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_buildup_architects(self, min_xgchain: float = 3.0) -> List[PlayerFullProfile2025Extended]:
        """BUILDUP_ARCHITECT: ratio >= 3.0 → ASSISTS, pas GOALS"""
        return sorted(
            [p for p in self.players.values() 
             if p.chain_profile == "BUILDUP_ARCHITECT" and p.xGChain >= min_xgchain],
            key=lambda x: -x.involvement_ratio
        )
        
    def get_finisher_only_players(self, min_goals: int = 3) -> List[PlayerFullProfile2025Extended]:
        """FINISHER_ONLY: ratio < 1.0 → GOALS si équipe domine, sinon SKIP"""
        return sorted(
            [p for p in self.players.values() 
             if p.chain_profile == "FINISHER_ONLY" and p.goals >= min_goals],
            key=lambda x: -x.goals
        )
        
    def get_playmakers(self, min_xgchain: float = 2.0) -> List[PlayerFullProfile2025Extended]:
        """PLAYMAKER: buildup_ratio >= 0.6 → Parier sur Passes/Assists"""
        return sorted(
            [p for p in self.players.values() 
             if p.buildup_profile == "PLAYMAKER" and p.xGChain >= min_xgchain],
            key=lambda x: -x.buildup_ratio
        )
        
    def get_box_crashers(self, min_goals: int = 3) -> List[PlayerFullProfile2025Extended]:
        """BOX_CRASHER: buildup_ratio < 0.4 → Présent que dans la surface"""
        return sorted(
            [p for p in self.players.values() 
             if p.buildup_profile == "BOX_CRASHER" and p.goals >= min_goals],
            key=lambda x: -x.goals
        )
        
    # ═══════════════════════════════════════════════════════════════════════════
    # GETTERS MARKET-SPECIFIC
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_first_goalscorer_candidates(self, team: str = None, min_goals: int = 3) -> List[Tuple[PlayerFullProfile2025Extended, float]]:
        """Candidats First Goalscorer avec score composite"""
        if team:
            players = [p for p in self.players.values() if p.team == team and p.goals >= min_goals]
        else:
            players = [p for p in self.players.values() if p.goals >= min_goals]
            
        return sorted(
            [(p, p.first_goalscorer_score) for p in players if p.first_goalscorer_score > 0],
            key=lambda x: -x[1]
        )
        
    def get_last_goalscorer_candidates(self, team: str = None, min_goals: int = 2) -> List[Tuple[PlayerFullProfile2025Extended, float]]:
        """Candidats Last Goalscorer avec score composite"""
        if team:
            players = [p for p in self.players.values() if p.team == team and p.goals >= min_goals]
        else:
            players = [p for p in self.players.values() if p.goals >= min_goals]
            
        return sorted(
            [(p, p.last_goalscorer_score) for p in players if p.last_goalscorer_score > 0],
            key=lambda x: -x[1]
        )
        
    def get_anytime_value_bets(self, min_xg: float = 5.0) -> List[Tuple[PlayerFullProfile2025Extended, float]]:
        """VALUE BETS: Joueurs sous-performant leur xG"""
        candidates = [
            p for p in self.players.values()
            if p.xG >= min_xg and p.np_overperformance <= -1
        ]
        
        return sorted(
            [(p, p.anytime_value_score) for p in candidates if p.anytime_value_score > 0],
            key=lambda x: -x[1]
        )
        
    # ═══════════════════════════════════════════════════════════════════════════
    # AUTRES GETTERS
    # ═══════════════════════════════════════════════════════════════════════════
        
    def get_hot_streak_players(self, min_goals: int = 3) -> List[PlayerFullProfile2025Extended]:
        return sorted(
            [p for p in self.players.values() 
             if p.finishing_trend == "HOT_STREAK" and p.goals >= min_goals],
            key=lambda x: -x.xG_overperformance
        )
        
    def get_early_birds(self, min_goals: int = 3) -> List[PlayerFullProfile2025Extended]:
        return sorted(
            [p for p in self.players.values() 
             if p.timing_profile == "EARLY_BIRD" and p.goals >= min_goals],
            key=lambda x: -x.pct_1h
        )
        
    def get_diesel_scorers(self, min_goals: int = 3) -> List[PlayerFullProfile2025Extended]:
        return sorted(
            [p for p in self.players.values() 
             if p.timing_profile == "DIESEL" and p.goals >= min_goals],
            key=lambda x: -x.pct_2h
        )
        
    def get_clutch_scorers(self, min_goals: int = 3) -> List[PlayerFullProfile2025Extended]:
        return sorted(
            [p for p in self.players.values() 
             if p.pct_clutch >= 25 and p.goals >= min_goals],
            key=lambda x: -x.pct_clutch
        )
        
    def get_super_subs(self, min_goals: int = 2) -> List[PlayerFullProfile2025Extended]:
        return sorted(
            [p for p in self.players.values() 
             if p.playing_time_profile == "SUPER_SUB" and p.goals >= min_goals],
            key=lambda x: -x.goals_per_90
        )
        
    def get_penalty_takers(self) -> List[PlayerFullProfile2025Extended]:
        return sorted(
            [p for p in self.players.values() if p.is_penalty_taker],
            key=lambda x: -x.penalty_goals
        )
        
    def get_elite_finishers(self, min_goals: int = 3) -> List[PlayerFullProfile2025Extended]:
        return sorted(
            [p for p in self.players.values() 
             if p.shot_quality == "ELITE_FINISHER" and p.goals >= min_goals],
            key=lambda x: -x.conversion_rate
        )
        
    def get_elite_creators(self) -> List[PlayerFullProfile2025Extended]:
        return sorted(
            [p for p in self.players.values() 
             if p.creativity_profile == "ELITE_CREATOR"],
            key=lambda x: -x.xA
        )
        
    def get_header_specialists(self, min_headers: int = 2) -> List[PlayerFullProfile2025Extended]:
        return sorted(
            [p for p in self.players.values() 
             if p.goals_header >= min_headers],
            key=lambda x: -x.pct_header
        )


if __name__ == '__main__':
    loader = AttackDataLoaderV52Extended()
    loader.load_all()
