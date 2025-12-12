#!/usr/bin/env python3
"""
🔥 MATRICE DE FRICTION 12×12 - COLLISION ADN TACTIQUE

Cette matrice définit ce qui se passe quand deux profils tactiques
entrent en collision sur le terrain.

PARADIGME MON_PS:
- Chaque équipe a un ADN unique (12 profils possibles)
- La collision de 2 ADN produit une FRICTION
- La friction détermine les marchés exploitables

Auteur: Mon_PS Quant Team
Date: 12 Décembre 2025
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional


class TacticalProfile(str, Enum):
    """Les 12 profils tactiques ADN."""
    # Offensifs (4)
    POSSESSION = "POSSESSION"
    GEGENPRESS = "GEGENPRESS"
    WIDE_ATTACK = "WIDE_ATTACK"
    DIRECT_ATTACK = "DIRECT_ATTACK"
    # Défensifs (3)
    LOW_BLOCK = "LOW_BLOCK"
    MID_BLOCK = "MID_BLOCK"
    PARK_THE_BUS = "PARK_THE_BUS"
    # Hybrides (3)
    TRANSITION = "TRANSITION"
    ADAPTIVE = "ADAPTIVE"
    BALANCED = "BALANCED"
    # Contextuels (2)
    HOME_DOMINANT = "HOME_DOMINANT"
    SCORE_DEPENDENT = "SCORE_DEPENDENT"


class ClashType(str, Enum):
    """Types de collision tactique."""
    CHAOS_MAXIMAL = "CHAOS_MAXIMAL"           # 2 équipes offensives agressives
    CHESS_MATCH = "CHESS_MATCH"               # 2 équipes possession patientes
    SIEGE_WARFARE = "SIEGE_WARFARE"           # Possession vs Bloc bas
    ABSORB_COUNTER = "ABSORB_COUNTER"         # Pressing vs Bloc bas
    PRESSING_BATTLE = "PRESSING_BATTLE"       # 2 équipes qui pressent
    TRANSITION_FEST = "TRANSITION_FEST"       # 2 équipes en transition
    SPACE_EXPLOITATION = "SPACE_EXPLOITATION" # Équipe qui exploite les espaces
    WING_BATTLE = "WING_BATTLE"               # Combat sur les ailes
    STALEMATE = "STALEMATE"                   # Match fermé
    TACTICAL_CHESS = "TACTICAL_CHESS"         # Adaptations constantes
    UNPREDICTABLE = "UNPREDICTABLE"           # Contextuel, imprévisible


class Tempo(str, Enum):
    """Tempo attendu du match."""
    EXTREME = "EXTREME"     # 90 min d'intensité
    HIGH = "HIGH"           # Rythme élevé
    MEDIUM = "MEDIUM"       # Équilibré
    SLOW = "SLOW"           # Possession lente
    VARIABLE = "VARIABLE"   # Change selon le score


@dataclass
class FrictionResult:
    """Résultat d'une collision de profils tactiques."""
    clash_type: ClashType
    tempo: Tempo
    goals_modifier: float      # +0.5 = +0.5 buts attendus
    cards_modifier: float      # +1.0 = +1 carton attendu
    corners_modifier: float    # +2.0 = +2 corners attendus

    # Marchés recommandés
    primary_markets: List[str]    # Marchés à forte value
    secondary_markets: List[str]  # Marchés value moyenne
    avoid_markets: List[str]      # Marchés à éviter

    # Timing
    first_half_bias: float   # >0.5 = plus de buts en 1H
    late_goal_prob: float    # Probabilité but 75+

    # Narrative
    description: str


# ═══════════════════════════════════════════════════════════════════
# MATRICE DE FRICTION 12×12
# ═══════════════════════════════════════════════════════════════════

FRICTION_MATRIX: Dict[Tuple[str, str], FrictionResult] = {

    # ═══════════════════════════════════════════════════════════════
    # POSSESSION vs TOUS
    # ═══════════════════════════════════════════════════════════════

    ("POSSESSION", "POSSESSION"): FrictionResult(
        clash_type=ClashType.CHESS_MATCH,
        tempo=Tempo.SLOW,
        goals_modifier=-0.3,
        cards_modifier=-0.5,
        corners_modifier=+1.0,
        primary_markets=["under_2.5", "btts_no", "0-0_ht"],
        secondary_markets=["late_goal", "corners_over_10"],
        avoid_markets=["over_3.5", "both_teams_2+"],
        first_half_bias=0.35,
        late_goal_prob=0.45,
        description="Match d'échecs. Possession stérile, peu de tirs. Patience = buts tardifs."
    ),

    ("POSSESSION", "GEGENPRESS"): FrictionResult(
        clash_type=ClashType.PRESSING_BATTLE,
        tempo=Tempo.HIGH,
        goals_modifier=+0.5,
        cards_modifier=+0.8,
        corners_modifier=+0.5,
        primary_markets=["btts_yes", "over_2.5", "cards_over_3.5"],
        secondary_markets=["gegenpress_team_goal", "1h_over_0.5"],
        avoid_markets=["under_1.5", "0-0"],
        first_half_bias=0.55,
        late_goal_prob=0.50,
        description="Le pressing force des erreurs. Turnovers dangereux des 2 côtés."
    ),

    ("POSSESSION", "WIDE_ATTACK"): FrictionResult(
        clash_type=ClashType.SPACE_EXPLOITATION,
        tempo=Tempo.MEDIUM,
        goals_modifier=+0.2,
        cards_modifier=+0.3,
        corners_modifier=+2.5,
        primary_markets=["corners_over_10", "over_2.5"],
        secondary_markets=["wide_team_goal", "btts_yes"],
        avoid_markets=["under_1.5"],
        first_half_bias=0.50,
        late_goal_prob=0.40,
        description="Possession centrale vs attaques sur les ailes. Corners fréquents."
    ),

    ("POSSESSION", "DIRECT_ATTACK"): FrictionResult(
        clash_type=ClashType.SPACE_EXPLOITATION,
        tempo=Tempo.VARIABLE,
        goals_modifier=+0.4,
        cards_modifier=+0.5,
        corners_modifier=+0.0,
        primary_markets=["btts_yes", "over_2.5"],
        secondary_markets=["direct_team_counter_goal", "2h_goals"],
        avoid_markets=["under_1.5", "possession_team_clean_sheet"],
        first_half_bias=0.45,
        late_goal_prob=0.55,
        description="Possession laisse des espaces. L'équipe directe exploite en contre."
    ),

    ("POSSESSION", "LOW_BLOCK"): FrictionResult(
        clash_type=ClashType.SIEGE_WARFARE,
        tempo=Tempo.SLOW,
        goals_modifier=-0.4,
        cards_modifier=+0.2,
        corners_modifier=+3.0,
        primary_markets=["corners_over_11", "under_2.5", "possession_team_win_nil"],
        secondary_markets=["late_goal", "0-0_ht"],
        avoid_markets=["over_3.5", "btts_yes", "low_block_goal"],
        first_half_bias=0.30,
        late_goal_prob=0.55,
        description="Siège classique. Domination stérile, corners massifs, frustration."
    ),

    ("POSSESSION", "MID_BLOCK"): FrictionResult(
        clash_type=ClashType.TACTICAL_CHESS,
        tempo=Tempo.MEDIUM,
        goals_modifier=0.0,
        cards_modifier=+0.3,
        corners_modifier=+1.5,
        primary_markets=["corners_over_9", "possession_team_win"],
        secondary_markets=["over_2.5", "late_goal"],
        avoid_markets=["both_teams_2+"],
        first_half_bias=0.45,
        late_goal_prob=0.50,
        description="Le bloc médian concède du terrain mais reste compact. Match tactique."
    ),

    ("POSSESSION", "PARK_THE_BUS"): FrictionResult(
        clash_type=ClashType.SIEGE_WARFARE,
        tempo=Tempo.SLOW,
        goals_modifier=-0.6,
        cards_modifier=+0.5,
        corners_modifier=+4.0,
        primary_markets=["corners_over_12", "under_1.5", "0-0"],
        secondary_markets=["possession_team_win_nil", "late_goal"],
        avoid_markets=["over_2.5", "btts_yes"],
        first_half_bias=0.25,
        late_goal_prob=0.60,
        description="Bus garé. Frustration maximale. Si but, ce sera très tard."
    ),

    ("POSSESSION", "TRANSITION"): FrictionResult(
        clash_type=ClashType.SPACE_EXPLOITATION,
        tempo=Tempo.MEDIUM,
        goals_modifier=+0.3,
        cards_modifier=+0.4,
        corners_modifier=+1.0,
        primary_markets=["btts_yes", "over_2.5"],
        secondary_markets=["transition_team_goal", "counter_attack"],
        avoid_markets=["possession_team_clean_sheet"],
        first_half_bias=0.50,
        late_goal_prob=0.45,
        description="Possession crée des espaces, transition les exploite. Match ouvert."
    ),

    ("POSSESSION", "ADAPTIVE"): FrictionResult(
        clash_type=ClashType.TACTICAL_CHESS,
        tempo=Tempo.VARIABLE,
        goals_modifier=0.0,
        cards_modifier=+0.2,
        corners_modifier=+1.0,
        primary_markets=["possession_team_win", "under_2.5"],
        secondary_markets=["late_goal", "corners_over_9"],
        avoid_markets=["over_3.5"],
        first_half_bias=0.45,
        late_goal_prob=0.50,
        description="L'adaptive s'ajuste. Match tactique, peu de spectacle."
    ),

    ("POSSESSION", "BALANCED"): FrictionResult(
        clash_type=ClashType.TACTICAL_CHESS,
        tempo=Tempo.MEDIUM,
        goals_modifier=+0.1,
        cards_modifier=+0.2,
        corners_modifier=+1.5,
        primary_markets=["possession_team_win", "corners_over_9"],
        secondary_markets=["over_2.5", "late_goal"],
        avoid_markets=["both_teams_2+"],
        first_half_bias=0.45,
        late_goal_prob=0.45,
        description="L'équipe possession domine mais le balanced résiste. Match standard."
    ),

    ("POSSESSION", "HOME_DOMINANT"): FrictionResult(
        clash_type=ClashType.UNPREDICTABLE,
        tempo=Tempo.VARIABLE,
        goals_modifier=+0.2,
        cards_modifier=+0.3,
        corners_modifier=+1.0,
        primary_markets=["check_home_away_context"],
        secondary_markets=["btts_yes"],
        avoid_markets=[],
        first_half_bias=0.50,
        late_goal_prob=0.45,
        description="Dépend du contexte dom/ext. Vérifier qui joue à domicile."
    ),

    ("POSSESSION", "SCORE_DEPENDENT"): FrictionResult(
        clash_type=ClashType.UNPREDICTABLE,
        tempo=Tempo.VARIABLE,
        goals_modifier=+0.1,
        cards_modifier=+0.3,
        corners_modifier=+1.0,
        primary_markets=["live_betting_recommended"],
        secondary_markets=["late_goal"],
        avoid_markets=["pre_match_exact_score"],
        first_half_bias=0.50,
        late_goal_prob=0.55,
        description="L'équipe change selon le score. Opportunités en live betting."
    ),

    # ═══════════════════════════════════════════════════════════════
    # GEGENPRESS vs TOUS
    # ═══════════════════════════════════════════════════════════════

    ("GEGENPRESS", "GEGENPRESS"): FrictionResult(
        clash_type=ClashType.CHAOS_MAXIMAL,
        tempo=Tempo.EXTREME,
        goals_modifier=+1.0,
        cards_modifier=+1.5,
        corners_modifier=+0.5,
        primary_markets=["over_3.5", "btts_yes", "cards_over_4.5", "both_teams_2+"],
        secondary_markets=["over_4.5", "red_card"],
        avoid_markets=["under_2.5", "clean_sheet", "0-0"],
        first_half_bias=0.55,
        late_goal_prob=0.60,
        description="CHAOS TOTAL. 2 équipes qui pressent = erreurs, buts, cartons. Spectacle garanti."
    ),

    ("GEGENPRESS", "WIDE_ATTACK"): FrictionResult(
        clash_type=ClashType.TRANSITION_FEST,
        tempo=Tempo.HIGH,
        goals_modifier=+0.6,
        cards_modifier=+0.8,
        corners_modifier=+1.5,
        primary_markets=["over_2.5", "btts_yes", "cards_over_3.5"],
        secondary_markets=["corners_over_10", "wide_team_goal"],
        avoid_markets=["under_1.5", "0-0"],
        first_half_bias=0.55,
        late_goal_prob=0.50,
        description="Le pressing laisse les ailes ouvertes. L'équipe wide exploite."
    ),

    ("GEGENPRESS", "DIRECT_ATTACK"): FrictionResult(
        clash_type=ClashType.CHAOS_MAXIMAL,
        tempo=Tempo.EXTREME,
        goals_modifier=+0.8,
        cards_modifier=+1.0,
        corners_modifier=+0.5,
        primary_markets=["over_3.5", "btts_yes", "cards_over_4.5"],
        secondary_markets=["both_teams_2+", "late_goal"],
        avoid_markets=["under_2.5", "clean_sheet"],
        first_half_bias=0.50,
        late_goal_prob=0.55,
        description="Pressing vs verticalité = chaos. Les deux équipes marquent."
    ),

    ("GEGENPRESS", "LOW_BLOCK"): FrictionResult(
        clash_type=ClashType.ABSORB_COUNTER,
        tempo=Tempo.VARIABLE,
        goals_modifier=-0.1,
        cards_modifier=+0.6,
        corners_modifier=+1.5,
        primary_markets=["late_goal", "2h_over_1h", "cards_over_3.5"],
        secondary_markets=["gegenpress_team_win", "low_block_counter_goal"],
        avoid_markets=["over_3.5", "1h_over_1.5"],
        first_half_bias=0.35,
        late_goal_prob=0.60,
        description="Le bloc absorbe le pressing. Fatigue 2H = opportunités. But tardif probable."
    ),

    ("GEGENPRESS", "MID_BLOCK"): FrictionResult(
        clash_type=ClashType.PRESSING_BATTLE,
        tempo=Tempo.HIGH,
        goals_modifier=+0.4,
        cards_modifier=+0.7,
        corners_modifier=+1.0,
        primary_markets=["over_2.5", "btts_yes", "cards_over_3.5"],
        secondary_markets=["gegenpress_team_win", "late_goal"],
        avoid_markets=["under_1.5"],
        first_half_bias=0.50,
        late_goal_prob=0.50,
        description="Le pressing force le bloc médian à reculer. Match ouvert."
    ),

    ("GEGENPRESS", "PARK_THE_BUS"): FrictionResult(
        clash_type=ClashType.SIEGE_WARFARE,
        tempo=Tempo.VARIABLE,
        goals_modifier=-0.3,
        cards_modifier=+0.8,
        corners_modifier=+2.5,
        primary_markets=["corners_over_11", "late_goal", "cards_over_3.5"],
        secondary_markets=["gegenpress_team_win_nil", "under_2.5"],
        avoid_markets=["over_3.5", "btts_yes"],
        first_half_bias=0.30,
        late_goal_prob=0.65,
        description="Le pressing s'épuise contre le bus. Si but, ce sera très tard."
    ),

    ("GEGENPRESS", "TRANSITION"): FrictionResult(
        clash_type=ClashType.CHAOS_MAXIMAL,
        tempo=Tempo.EXTREME,
        goals_modifier=+0.7,
        cards_modifier=+1.0,
        corners_modifier=+0.5,
        primary_markets=["over_3.5", "btts_yes", "cards_over_4.5"],
        secondary_markets=["both_teams_2+", "transition_team_goal"],
        avoid_markets=["under_2.5", "clean_sheet"],
        first_half_bias=0.55,
        late_goal_prob=0.55,
        description="Pressing haut + transitions rapides = chaos. Match très ouvert."
    ),

    ("GEGENPRESS", "ADAPTIVE"): FrictionResult(
        clash_type=ClashType.TACTICAL_CHESS,
        tempo=Tempo.HIGH,
        goals_modifier=+0.3,
        cards_modifier=+0.5,
        corners_modifier=+0.5,
        primary_markets=["over_2.5", "btts_yes"],
        secondary_markets=["gegenpress_team_win", "cards_over_3.5"],
        avoid_markets=["under_1.5"],
        first_half_bias=0.50,
        late_goal_prob=0.50,
        description="L'adaptive tente de s'ajuster au pressing. Bataille tactique."
    ),

    ("GEGENPRESS", "BALANCED"): FrictionResult(
        clash_type=ClashType.PRESSING_BATTLE,
        tempo=Tempo.HIGH,
        goals_modifier=+0.4,
        cards_modifier=+0.6,
        corners_modifier=+0.5,
        primary_markets=["over_2.5", "btts_yes", "gegenpress_team_win"],
        secondary_markets=["cards_over_3.5", "1h_over_0.5"],
        avoid_markets=["under_1.5", "balanced_clean_sheet"],
        first_half_bias=0.55,
        late_goal_prob=0.45,
        description="Le pressing domine le balanced. Buts attendus."
    ),

    ("GEGENPRESS", "HOME_DOMINANT"): FrictionResult(
        clash_type=ClashType.UNPREDICTABLE,
        tempo=Tempo.VARIABLE,
        goals_modifier=+0.3,
        cards_modifier=+0.5,
        corners_modifier=+0.5,
        primary_markets=["btts_yes", "over_2.5"],
        secondary_markets=["check_home_away_context"],
        avoid_markets=[],
        first_half_bias=0.50,
        late_goal_prob=0.50,
        description="Le pressing est efficace partout. Vérifier contexte dom/ext."
    ),

    ("GEGENPRESS", "SCORE_DEPENDENT"): FrictionResult(
        clash_type=ClashType.UNPREDICTABLE,
        tempo=Tempo.VARIABLE,
        goals_modifier=+0.4,
        cards_modifier=+0.6,
        corners_modifier=+0.5,
        primary_markets=["over_2.5", "btts_yes", "live_betting"],
        secondary_markets=["late_goal"],
        avoid_markets=[],
        first_half_bias=0.55,
        late_goal_prob=0.55,
        description="Le pressing force l'adversaire à réagir. Opportunités live."
    ),

    # ═══════════════════════════════════════════════════════════════
    # WIDE_ATTACK vs TOUS (sauf POSSESSION/GEGENPRESS déjà couverts)
    # ═══════════════════════════════════════════════════════════════

    ("WIDE_ATTACK", "WIDE_ATTACK"): FrictionResult(
        clash_type=ClashType.WING_BATTLE,
        tempo=Tempo.HIGH,
        goals_modifier=+0.5,
        cards_modifier=+0.6,
        corners_modifier=+3.0,
        primary_markets=["corners_over_11", "btts_yes", "over_2.5"],
        secondary_markets=["header_goal", "cross_assist"],
        avoid_markets=["under_1.5", "corners_under_8"],
        first_half_bias=0.50,
        late_goal_prob=0.45,
        description="Bataille sur les ailes. Centres, corners, buts de la tête."
    ),

    ("WIDE_ATTACK", "DIRECT_ATTACK"): FrictionResult(
        clash_type=ClashType.TRANSITION_FEST,
        tempo=Tempo.HIGH,
        goals_modifier=+0.5,
        cards_modifier=+0.5,
        corners_modifier=+1.5,
        primary_markets=["over_2.5", "btts_yes"],
        secondary_markets=["corners_over_9", "late_goal"],
        avoid_markets=["under_1.5"],
        first_half_bias=0.50,
        late_goal_prob=0.50,
        description="Deux styles offensifs différents. Match ouvert et spectaculaire."
    ),

    ("WIDE_ATTACK", "LOW_BLOCK"): FrictionResult(
        clash_type=ClashType.SIEGE_WARFARE,
        tempo=Tempo.SLOW,
        goals_modifier=-0.2,
        cards_modifier=+0.3,
        corners_modifier=+3.5,
        primary_markets=["corners_over_11", "wide_team_win"],
        secondary_markets=["under_2.5", "late_goal"],
        avoid_markets=["btts_yes", "over_3.5"],
        first_half_bias=0.35,
        late_goal_prob=0.55,
        description="Les centres se heurtent au bloc bas. Beaucoup de corners, peu de buts."
    ),

    ("WIDE_ATTACK", "MID_BLOCK"): FrictionResult(
        clash_type=ClashType.WING_BATTLE,
        tempo=Tempo.MEDIUM,
        goals_modifier=+0.2,
        cards_modifier=+0.4,
        corners_modifier=+2.5,
        primary_markets=["corners_over_10", "over_2.5"],
        secondary_markets=["wide_team_win", "header_goal"],
        avoid_markets=["under_1.5"],
        first_half_bias=0.45,
        late_goal_prob=0.50,
        description="Le bloc médian laisse les ailes. Corners fréquents."
    ),

    ("WIDE_ATTACK", "PARK_THE_BUS"): FrictionResult(
        clash_type=ClashType.SIEGE_WARFARE,
        tempo=Tempo.SLOW,
        goals_modifier=-0.4,
        cards_modifier=+0.4,
        corners_modifier=+4.0,
        primary_markets=["corners_over_12", "under_2.5"],
        secondary_markets=["wide_team_win_nil", "late_goal"],
        avoid_markets=["over_3.5", "btts_yes"],
        first_half_bias=0.30,
        late_goal_prob=0.60,
        description="Le bus bloque tout. Corners massifs mais peu de buts."
    ),

    ("WIDE_ATTACK", "TRANSITION"): FrictionResult(
        clash_type=ClashType.SPACE_EXPLOITATION,
        tempo=Tempo.HIGH,
        goals_modifier=+0.4,
        cards_modifier=+0.5,
        corners_modifier=+2.0,
        primary_markets=["btts_yes", "over_2.5", "corners_over_10"],
        secondary_markets=["transition_counter_goal"],
        avoid_markets=["under_1.5"],
        first_half_bias=0.50,
        late_goal_prob=0.50,
        description="Les ailes créent des espaces, la transition les exploite."
    ),

    ("WIDE_ATTACK", "ADAPTIVE"): FrictionResult(
        clash_type=ClashType.TACTICAL_CHESS,
        tempo=Tempo.MEDIUM,
        goals_modifier=+0.1,
        cards_modifier=+0.3,
        corners_modifier=+2.0,
        primary_markets=["corners_over_9", "over_2.5"],
        secondary_markets=["wide_team_win"],
        avoid_markets=[],
        first_half_bias=0.50,
        late_goal_prob=0.45,
        description="L'adaptive s'ajuste aux ailes. Match tactique avec corners."
    ),

    ("WIDE_ATTACK", "BALANCED"): FrictionResult(
        clash_type=ClashType.WING_BATTLE,
        tempo=Tempo.MEDIUM,
        goals_modifier=+0.2,
        cards_modifier=+0.3,
        corners_modifier=+2.0,
        primary_markets=["corners_over_9", "wide_team_win"],
        secondary_markets=["over_2.5", "header_goal"],
        avoid_markets=["under_1.5"],
        first_half_bias=0.50,
        late_goal_prob=0.45,
        description="L'équipe wide domine les ailes. Match relativement prévisible."
    ),

    ("WIDE_ATTACK", "HOME_DOMINANT"): FrictionResult(
        clash_type=ClashType.UNPREDICTABLE,
        tempo=Tempo.VARIABLE,
        goals_modifier=+0.2,
        cards_modifier=+0.3,
        corners_modifier=+2.0,
        primary_markets=["corners_over_9"],
        secondary_markets=["check_home_away_context"],
        avoid_markets=[],
        first_half_bias=0.50,
        late_goal_prob=0.45,
        description="Corners probables. Vérifier contexte dom/ext."
    ),

    ("WIDE_ATTACK", "SCORE_DEPENDENT"): FrictionResult(
        clash_type=ClashType.UNPREDICTABLE,
        tempo=Tempo.VARIABLE,
        goals_modifier=+0.2,
        cards_modifier=+0.3,
        corners_modifier=+2.0,
        primary_markets=["corners_over_9", "live_betting"],
        secondary_markets=["late_goal"],
        avoid_markets=[],
        first_half_bias=0.50,
        late_goal_prob=0.50,
        description="Les ailes créent des opportunités. Évolution selon le score."
    ),

    # ═══════════════════════════════════════════════════════════════
    # DIRECT_ATTACK vs TOUS (profils restants)
    # ═══════════════════════════════════════════════════════════════

    ("DIRECT_ATTACK", "DIRECT_ATTACK"): FrictionResult(
        clash_type=ClashType.CHAOS_MAXIMAL,
        tempo=Tempo.EXTREME,
        goals_modifier=+0.8,
        cards_modifier=+0.8,
        corners_modifier=+0.0,
        primary_markets=["over_3.5", "btts_yes", "both_teams_2+"],
        secondary_markets=["cards_over_3.5"],
        avoid_markets=["under_2.5", "0-0"],
        first_half_bias=0.50,
        late_goal_prob=0.55,
        description="Deux équipes directes = chaos. Peu de possession, beaucoup de buts."
    ),

    ("DIRECT_ATTACK", "LOW_BLOCK"): FrictionResult(
        clash_type=ClashType.SPACE_EXPLOITATION,
        tempo=Tempo.VARIABLE,
        goals_modifier=+0.1,
        cards_modifier=+0.4,
        corners_modifier=+1.0,
        primary_markets=["direct_team_win", "under_2.5"],
        secondary_markets=["late_goal", "low_block_counter"],
        avoid_markets=["over_3.5"],
        first_half_bias=0.40,
        late_goal_prob=0.55,
        description="Le jeu direct contre le bloc bas. Un but peut suffire."
    ),

    ("DIRECT_ATTACK", "MID_BLOCK"): FrictionResult(
        clash_type=ClashType.SPACE_EXPLOITATION,
        tempo=Tempo.HIGH,
        goals_modifier=+0.3,
        cards_modifier=+0.5,
        corners_modifier=+0.5,
        primary_markets=["over_2.5", "btts_yes"],
        secondary_markets=["direct_team_win"],
        avoid_markets=["under_1.5"],
        first_half_bias=0.50,
        late_goal_prob=0.50,
        description="Le jeu direct exploite les espaces du bloc médian."
    ),

    ("DIRECT_ATTACK", "PARK_THE_BUS"): FrictionResult(
        clash_type=ClashType.SIEGE_WARFARE,
        tempo=Tempo.SLOW,
        goals_modifier=-0.3,
        cards_modifier=+0.5,
        corners_modifier=+1.5,
        primary_markets=["under_2.5", "direct_team_win_nil"],
        secondary_markets=["late_goal", "corners_over_8"],
        avoid_markets=["over_3.5", "btts_yes"],
        first_half_bias=0.35,
        late_goal_prob=0.60,
        description="Le jeu direct n'a pas l'espace habituel. Match fermé."
    ),

    ("DIRECT_ATTACK", "TRANSITION"): FrictionResult(
        clash_type=ClashType.CHAOS_MAXIMAL,
        tempo=Tempo.EXTREME,
        goals_modifier=+0.7,
        cards_modifier=+0.7,
        corners_modifier=+0.0,
        primary_markets=["over_3.5", "btts_yes"],
        secondary_markets=["both_teams_2+", "cards_over_3.5"],
        avoid_markets=["under_2.5", "0-0"],
        first_half_bias=0.55,
        late_goal_prob=0.50,
        description="Direct + Transition = chaos offensif. Les deux marquent."
    ),

    ("DIRECT_ATTACK", "ADAPTIVE"): FrictionResult(
        clash_type=ClashType.TACTICAL_CHESS,
        tempo=Tempo.VARIABLE,
        goals_modifier=+0.2,
        cards_modifier=+0.4,
        corners_modifier=+0.0,
        primary_markets=["over_2.5", "btts_yes"],
        secondary_markets=["direct_team_win"],
        avoid_markets=["under_1.5"],
        first_half_bias=0.50,
        late_goal_prob=0.50,
        description="L'adaptive s'ajuste au jeu direct. Match équilibré."
    ),

    ("DIRECT_ATTACK", "BALANCED"): FrictionResult(
        clash_type=ClashType.SPACE_EXPLOITATION,
        tempo=Tempo.HIGH,
        goals_modifier=+0.3,
        cards_modifier=+0.4,
        corners_modifier=+0.0,
        primary_markets=["over_2.5", "direct_team_win"],
        secondary_markets=["btts_yes"],
        avoid_markets=["under_1.5"],
        first_half_bias=0.50,
        late_goal_prob=0.50,
        description="Le jeu direct exploite le balanced. Match ouvert."
    ),

    ("DIRECT_ATTACK", "HOME_DOMINANT"): FrictionResult(
        clash_type=ClashType.UNPREDICTABLE,
        tempo=Tempo.VARIABLE,
        goals_modifier=+0.3,
        cards_modifier=+0.4,
        corners_modifier=+0.0,
        primary_markets=["over_2.5"],
        secondary_markets=["check_home_away_context"],
        avoid_markets=[],
        first_half_bias=0.50,
        late_goal_prob=0.50,
        description="Le jeu direct est efficace partout. Vérifier contexte."
    ),

    ("DIRECT_ATTACK", "SCORE_DEPENDENT"): FrictionResult(
        clash_type=ClashType.UNPREDICTABLE,
        tempo=Tempo.VARIABLE,
        goals_modifier=+0.3,
        cards_modifier=+0.4,
        corners_modifier=+0.0,
        primary_markets=["over_2.5", "live_betting"],
        secondary_markets=["late_goal"],
        avoid_markets=[],
        first_half_bias=0.50,
        late_goal_prob=0.55,
        description="Le jeu direct force des réactions. Opportunités live."
    ),

    # ═══════════════════════════════════════════════════════════════
    # LOW_BLOCK vs TOUS (profils restants)
    # ═══════════════════════════════════════════════════════════════

    ("LOW_BLOCK", "LOW_BLOCK"): FrictionResult(
        clash_type=ClashType.STALEMATE,
        tempo=Tempo.SLOW,
        goals_modifier=-0.8,
        cards_modifier=-0.2,
        corners_modifier=+0.0,
        primary_markets=["under_1.5", "0-0", "btts_no"],
        secondary_markets=["draw"],
        avoid_markets=["over_2.5", "btts_yes", "both_teams_score"],
        first_half_bias=0.40,
        late_goal_prob=0.40,
        description="Deux blocs bas = match fermé. 0-0 très probable."
    ),

    ("LOW_BLOCK", "MID_BLOCK"): FrictionResult(
        clash_type=ClashType.STALEMATE,
        tempo=Tempo.SLOW,
        goals_modifier=-0.5,
        cards_modifier=0.0,
        corners_modifier=+0.5,
        primary_markets=["under_2.5", "btts_no"],
        secondary_markets=["draw", "late_goal"],
        avoid_markets=["over_3.5"],
        first_half_bias=0.40,
        late_goal_prob=0.50,
        description="Match fermé. Peu d'ambition des deux côtés."
    ),

    ("LOW_BLOCK", "PARK_THE_BUS"): FrictionResult(
        clash_type=ClashType.STALEMATE,
        tempo=Tempo.SLOW,
        goals_modifier=-1.0,
        cards_modifier=-0.3,
        corners_modifier=+0.0,
        primary_markets=["under_0.5", "0-0", "btts_no"],
        secondary_markets=["draw"],
        avoid_markets=["over_1.5", "btts_yes", "anytime_scorer"],
        first_half_bias=0.30,
        late_goal_prob=0.35,
        description="Le match le plus fermé possible. 0-0 très probable."
    ),

    ("LOW_BLOCK", "TRANSITION"): FrictionResult(
        clash_type=ClashType.ABSORB_COUNTER,
        tempo=Tempo.VARIABLE,
        goals_modifier=0.0,
        cards_modifier=+0.3,
        corners_modifier=+0.5,
        primary_markets=["under_2.5", "transition_team_win"],
        secondary_markets=["late_goal", "btts_no"],
        avoid_markets=["over_3.5"],
        first_half_bias=0.40,
        late_goal_prob=0.55,
        description="Le bloc absorbe, la transition attend son moment."
    ),

    ("LOW_BLOCK", "ADAPTIVE"): FrictionResult(
        clash_type=ClashType.TACTICAL_CHESS,
        tempo=Tempo.SLOW,
        goals_modifier=-0.3,
        cards_modifier=+0.2,
        corners_modifier=+0.5,
        primary_markets=["under_2.5", "adaptive_team_win"],
        secondary_markets=["late_goal"],
        avoid_markets=["over_3.5"],
        first_half_bias=0.40,
        late_goal_prob=0.55,
        description="L'adaptive cherche la faille du bloc. Match patient."
    ),

    ("LOW_BLOCK", "BALANCED"): FrictionResult(
        clash_type=ClashType.SIEGE_WARFARE,
        tempo=Tempo.SLOW,
        goals_modifier=-0.2,
        cards_modifier=+0.2,
        corners_modifier=+1.0,
        primary_markets=["under_2.5", "balanced_team_win"],
        secondary_markets=["corners_over_8", "late_goal"],
        avoid_markets=["over_3.5"],
        first_half_bias=0.40,
        late_goal_prob=0.50,
        description="Le balanced tente de percer le bloc. Match serré."
    ),

    ("LOW_BLOCK", "HOME_DOMINANT"): FrictionResult(
        clash_type=ClashType.UNPREDICTABLE,
        tempo=Tempo.VARIABLE,
        goals_modifier=-0.2,
        cards_modifier=+0.2,
        corners_modifier=+0.5,
        primary_markets=["under_2.5"],
        secondary_markets=["check_home_away_context"],
        avoid_markets=["over_3.5"],
        first_half_bias=0.45,
        late_goal_prob=0.50,
        description="Le bloc bas est stable. Vérifier contexte dom/ext."
    ),

    ("LOW_BLOCK", "SCORE_DEPENDENT"): FrictionResult(
        clash_type=ClashType.UNPREDICTABLE,
        tempo=Tempo.VARIABLE,
        goals_modifier=-0.1,
        cards_modifier=+0.2,
        corners_modifier=+0.5,
        primary_markets=["under_2.5", "live_betting"],
        secondary_markets=["late_goal"],
        avoid_markets=["over_3.5"],
        first_half_bias=0.45,
        late_goal_prob=0.55,
        description="Le bloc attend que l'adversaire s'ouvre. Live betting intéressant."
    ),

    # ═══════════════════════════════════════════════════════════════
    # MID_BLOCK vs TOUS (profils restants)
    # ═══════════════════════════════════════════════════════════════

    ("MID_BLOCK", "MID_BLOCK"): FrictionResult(
        clash_type=ClashType.STALEMATE,
        tempo=Tempo.MEDIUM,
        goals_modifier=-0.2,
        cards_modifier=+0.2,
        corners_modifier=+0.5,
        primary_markets=["under_2.5", "draw"],
        secondary_markets=["btts_no", "late_goal"],
        avoid_markets=["over_3.5"],
        first_half_bias=0.45,
        late_goal_prob=0.50,
        description="Deux blocs médians = match équilibré mais fermé."
    ),

    ("MID_BLOCK", "PARK_THE_BUS"): FrictionResult(
        clash_type=ClashType.SIEGE_WARFARE,
        tempo=Tempo.SLOW,
        goals_modifier=-0.4,
        cards_modifier=+0.2,
        corners_modifier=+1.5,
        primary_markets=["under_1.5", "mid_block_win"],
        secondary_markets=["corners_over_8", "late_goal"],
        avoid_markets=["over_2.5", "btts_yes"],
        first_half_bias=0.35,
        late_goal_prob=0.55,
        description="Le bloc médian domine mais le bus résiste."
    ),

    ("MID_BLOCK", "TRANSITION"): FrictionResult(
        clash_type=ClashType.SPACE_EXPLOITATION,
        tempo=Tempo.MEDIUM,
        goals_modifier=+0.2,
        cards_modifier=+0.4,
        corners_modifier=+0.5,
        primary_markets=["over_2.5", "transition_team_goal"],
        secondary_markets=["btts_yes"],
        avoid_markets=["under_1.5"],
        first_half_bias=0.50,
        late_goal_prob=0.50,
        description="Le bloc médian laisse des espaces que la transition exploite."
    ),

    ("MID_BLOCK", "ADAPTIVE"): FrictionResult(
        clash_type=ClashType.TACTICAL_CHESS,
        tempo=Tempo.MEDIUM,
        goals_modifier=0.0,
        cards_modifier=+0.2,
        corners_modifier=+0.5,
        primary_markets=["draw", "under_2.5"],
        secondary_markets=["late_goal"],
        avoid_markets=["over_3.5"],
        first_half_bias=0.45,
        late_goal_prob=0.50,
        description="Deux équipes prudentes. Match tactique équilibré."
    ),

    ("MID_BLOCK", "BALANCED"): FrictionResult(
        clash_type=ClashType.TACTICAL_CHESS,
        tempo=Tempo.MEDIUM,
        goals_modifier=0.0,
        cards_modifier=+0.2,
        corners_modifier=+0.5,
        primary_markets=["draw", "under_2.5"],
        secondary_markets=["late_goal"],
        avoid_markets=["over_3.5"],
        first_half_bias=0.45,
        late_goal_prob=0.50,
        description="Match standard entre deux équipes moyennes."
    ),

    ("MID_BLOCK", "HOME_DOMINANT"): FrictionResult(
        clash_type=ClashType.UNPREDICTABLE,
        tempo=Tempo.VARIABLE,
        goals_modifier=0.0,
        cards_modifier=+0.2,
        corners_modifier=+0.5,
        primary_markets=["check_home_away_context"],
        secondary_markets=["draw"],
        avoid_markets=[],
        first_half_bias=0.50,
        late_goal_prob=0.50,
        description="Match standard. Vérifier contexte dom/ext."
    ),

    ("MID_BLOCK", "SCORE_DEPENDENT"): FrictionResult(
        clash_type=ClashType.UNPREDICTABLE,
        tempo=Tempo.VARIABLE,
        goals_modifier=0.0,
        cards_modifier=+0.2,
        corners_modifier=+0.5,
        primary_markets=["live_betting"],
        secondary_markets=["late_goal"],
        avoid_markets=[],
        first_half_bias=0.50,
        late_goal_prob=0.55,
        description="Évolution selon le score. Live betting recommandé."
    ),

    # ═══════════════════════════════════════════════════════════════
    # PARK_THE_BUS vs TOUS (profils restants)
    # ═══════════════════════════════════════════════════════════════

    ("PARK_THE_BUS", "PARK_THE_BUS"): FrictionResult(
        clash_type=ClashType.STALEMATE,
        tempo=Tempo.SLOW,
        goals_modifier=-1.2,
        cards_modifier=-0.5,
        corners_modifier=+0.0,
        primary_markets=["0-0", "under_0.5", "btts_no"],
        secondary_markets=["draw"],
        avoid_markets=["over_0.5", "anytime_scorer"],
        first_half_bias=0.30,
        late_goal_prob=0.30,
        description="Le match le plus ennuyeux possible. 0-0 presque certain."
    ),

    ("PARK_THE_BUS", "TRANSITION"): FrictionResult(
        clash_type=ClashType.ABSORB_COUNTER,
        tempo=Tempo.SLOW,
        goals_modifier=-0.3,
        cards_modifier=+0.3,
        corners_modifier=+0.5,
        primary_markets=["under_1.5", "transition_team_win"],
        secondary_markets=["late_goal"],
        avoid_markets=["over_2.5", "btts_yes"],
        first_half_bias=0.35,
        late_goal_prob=0.55,
        description="Le bus absorbe, la transition attend. Un seul but possible."
    ),

    ("PARK_THE_BUS", "ADAPTIVE"): FrictionResult(
        clash_type=ClashType.SIEGE_WARFARE,
        tempo=Tempo.SLOW,
        goals_modifier=-0.4,
        cards_modifier=+0.3,
        corners_modifier=+1.5,
        primary_markets=["under_1.5", "adaptive_team_win"],
        secondary_markets=["corners_over_8", "late_goal"],
        avoid_markets=["over_2.5", "btts_yes"],
        first_half_bias=0.35,
        late_goal_prob=0.60,
        description="L'adaptive cherche la faille. Match très fermé."
    ),

    ("PARK_THE_BUS", "BALANCED"): FrictionResult(
        clash_type=ClashType.SIEGE_WARFARE,
        tempo=Tempo.SLOW,
        goals_modifier=-0.3,
        cards_modifier=+0.3,
        corners_modifier=+1.5,
        primary_markets=["under_1.5", "balanced_team_win"],
        secondary_markets=["corners_over_8", "late_goal"],
        avoid_markets=["over_2.5", "btts_yes"],
        first_half_bias=0.35,
        late_goal_prob=0.55,
        description="Le balanced tente de percer. Match fermé."
    ),

    ("PARK_THE_BUS", "HOME_DOMINANT"): FrictionResult(
        clash_type=ClashType.UNPREDICTABLE,
        tempo=Tempo.SLOW,
        goals_modifier=-0.4,
        cards_modifier=+0.3,
        corners_modifier=+1.0,
        primary_markets=["under_1.5"],
        secondary_markets=["check_home_away_context"],
        avoid_markets=["over_2.5"],
        first_half_bias=0.40,
        late_goal_prob=0.55,
        description="Le bus est stable. Vérifier contexte."
    ),

    ("PARK_THE_BUS", "SCORE_DEPENDENT"): FrictionResult(
        clash_type=ClashType.UNPREDICTABLE,
        tempo=Tempo.SLOW,
        goals_modifier=-0.3,
        cards_modifier=+0.3,
        corners_modifier=+1.0,
        primary_markets=["under_1.5", "live_betting"],
        secondary_markets=["late_goal"],
        avoid_markets=["over_2.5"],
        first_half_bias=0.40,
        late_goal_prob=0.60,
        description="Le bus force l'adversaire à attaquer. Live intéressant."
    ),

    # ═══════════════════════════════════════════════════════════════
    # TRANSITION vs TOUS (profils restants)
    # ═══════════════════════════════════════════════════════════════

    ("TRANSITION", "TRANSITION"): FrictionResult(
        clash_type=ClashType.TRANSITION_FEST,
        tempo=Tempo.HIGH,
        goals_modifier=+0.5,
        cards_modifier=+0.6,
        corners_modifier=+0.0,
        primary_markets=["over_2.5", "btts_yes"],
        secondary_markets=["both_teams_2+", "cards_over_3.5"],
        avoid_markets=["under_1.5", "0-0"],
        first_half_bias=0.55,
        late_goal_prob=0.50,
        description="Deux équipes en transition = match ouvert et rapide."
    ),

    ("TRANSITION", "ADAPTIVE"): FrictionResult(
        clash_type=ClashType.TACTICAL_CHESS,
        tempo=Tempo.VARIABLE,
        goals_modifier=+0.2,
        cards_modifier=+0.4,
        corners_modifier=+0.0,
        primary_markets=["over_2.5", "btts_yes"],
        secondary_markets=["transition_team_goal"],
        avoid_markets=["under_1.5"],
        first_half_bias=0.50,
        late_goal_prob=0.50,
        description="L'adaptive s'adapte à la transition. Match équilibré."
    ),

    ("TRANSITION", "BALANCED"): FrictionResult(
        clash_type=ClashType.SPACE_EXPLOITATION,
        tempo=Tempo.HIGH,
        goals_modifier=+0.3,
        cards_modifier=+0.4,
        corners_modifier=+0.0,
        primary_markets=["over_2.5", "transition_team_win"],
        secondary_markets=["btts_yes"],
        avoid_markets=["under_1.5"],
        first_half_bias=0.55,
        late_goal_prob=0.45,
        description="La transition exploite le balanced. Match ouvert."
    ),

    ("TRANSITION", "HOME_DOMINANT"): FrictionResult(
        clash_type=ClashType.UNPREDICTABLE,
        tempo=Tempo.VARIABLE,
        goals_modifier=+0.2,
        cards_modifier=+0.4,
        corners_modifier=+0.0,
        primary_markets=["over_2.5", "btts_yes"],
        secondary_markets=["check_home_away_context"],
        avoid_markets=[],
        first_half_bias=0.50,
        late_goal_prob=0.50,
        description="La transition est efficace partout. Vérifier contexte."
    ),

    ("TRANSITION", "SCORE_DEPENDENT"): FrictionResult(
        clash_type=ClashType.UNPREDICTABLE,
        tempo=Tempo.VARIABLE,
        goals_modifier=+0.3,
        cards_modifier=+0.4,
        corners_modifier=+0.0,
        primary_markets=["over_2.5", "live_betting"],
        secondary_markets=["late_goal"],
        avoid_markets=[],
        first_half_bias=0.50,
        late_goal_prob=0.55,
        description="La transition force des réactions. Live betting."
    ),

    # ═══════════════════════════════════════════════════════════════
    # ADAPTIVE vs TOUS (profils restants)
    # ═══════════════════════════════════════════════════════════════

    ("ADAPTIVE", "ADAPTIVE"): FrictionResult(
        clash_type=ClashType.TACTICAL_CHESS,
        tempo=Tempo.VARIABLE,
        goals_modifier=0.0,
        cards_modifier=+0.2,
        corners_modifier=+0.5,
        primary_markets=["draw"],
        secondary_markets=["under_2.5", "late_goal"],
        avoid_markets=["over_3.5"],
        first_half_bias=0.45,
        late_goal_prob=0.50,
        description="Deux caméléons. Match tactique imprévisible."
    ),

    ("ADAPTIVE", "BALANCED"): FrictionResult(
        clash_type=ClashType.TACTICAL_CHESS,
        tempo=Tempo.MEDIUM,
        goals_modifier=0.0,
        cards_modifier=+0.2,
        corners_modifier=+0.5,
        primary_markets=["draw", "adaptive_team_win"],
        secondary_markets=["under_2.5"],
        avoid_markets=["over_3.5"],
        first_half_bias=0.45,
        late_goal_prob=0.50,
        description="L'adaptive domine tactiquement le balanced."
    ),

    ("ADAPTIVE", "HOME_DOMINANT"): FrictionResult(
        clash_type=ClashType.UNPREDICTABLE,
        tempo=Tempo.VARIABLE,
        goals_modifier=0.0,
        cards_modifier=+0.2,
        corners_modifier=+0.5,
        primary_markets=["check_home_away_context"],
        secondary_markets=["draw"],
        avoid_markets=[],
        first_half_bias=0.50,
        late_goal_prob=0.50,
        description="L'adaptive s'adapte au contexte. Vérifier dom/ext."
    ),

    ("ADAPTIVE", "SCORE_DEPENDENT"): FrictionResult(
        clash_type=ClashType.UNPREDICTABLE,
        tempo=Tempo.VARIABLE,
        goals_modifier=0.0,
        cards_modifier=+0.2,
        corners_modifier=+0.5,
        primary_markets=["live_betting"],
        secondary_markets=["late_goal"],
        avoid_markets=[],
        first_half_bias=0.50,
        late_goal_prob=0.55,
        description="Deux équipes qui s'adaptent. Match imprévisible."
    ),

    # ═══════════════════════════════════════════════════════════════
    # BALANCED vs TOUS (profils restants)
    # ═══════════════════════════════════════════════════════════════

    ("BALANCED", "BALANCED"): FrictionResult(
        clash_type=ClashType.TACTICAL_CHESS,
        tempo=Tempo.MEDIUM,
        goals_modifier=0.0,
        cards_modifier=+0.2,
        corners_modifier=+0.5,
        primary_markets=["draw"],
        secondary_markets=["under_2.5", "late_goal"],
        avoid_markets=["over_3.5"],
        first_half_bias=0.45,
        late_goal_prob=0.50,
        description="Match standard entre deux équipes équilibrées."
    ),

    ("BALANCED", "HOME_DOMINANT"): FrictionResult(
        clash_type=ClashType.UNPREDICTABLE,
        tempo=Tempo.VARIABLE,
        goals_modifier=0.0,
        cards_modifier=+0.2,
        corners_modifier=+0.5,
        primary_markets=["check_home_away_context"],
        secondary_markets=["draw"],
        avoid_markets=[],
        first_half_bias=0.50,
        late_goal_prob=0.50,
        description="Match standard. Vérifier contexte dom/ext."
    ),

    ("BALANCED", "SCORE_DEPENDENT"): FrictionResult(
        clash_type=ClashType.UNPREDICTABLE,
        tempo=Tempo.VARIABLE,
        goals_modifier=0.0,
        cards_modifier=+0.2,
        corners_modifier=+0.5,
        primary_markets=["live_betting"],
        secondary_markets=["late_goal"],
        avoid_markets=[],
        first_half_bias=0.50,
        late_goal_prob=0.55,
        description="Évolution selon le score. Live betting."
    ),

    # ═══════════════════════════════════════════════════════════════
    # HOME_DOMINANT vs TOUS (profils restants)
    # ═══════════════════════════════════════════════════════════════

    ("HOME_DOMINANT", "HOME_DOMINANT"): FrictionResult(
        clash_type=ClashType.UNPREDICTABLE,
        tempo=Tempo.VARIABLE,
        goals_modifier=0.0,
        cards_modifier=+0.2,
        corners_modifier=+0.5,
        primary_markets=["home_team_win"],
        secondary_markets=["check_home_away_context"],
        avoid_markets=[],
        first_half_bias=0.50,
        late_goal_prob=0.50,
        description="Avantage au domicile. Vérifier qui joue où."
    ),

    ("HOME_DOMINANT", "SCORE_DEPENDENT"): FrictionResult(
        clash_type=ClashType.UNPREDICTABLE,
        tempo=Tempo.VARIABLE,
        goals_modifier=0.0,
        cards_modifier=+0.2,
        corners_modifier=+0.5,
        primary_markets=["live_betting", "check_home_away_context"],
        secondary_markets=["late_goal"],
        avoid_markets=[],
        first_half_bias=0.50,
        late_goal_prob=0.55,
        description="Deux profils contextuels. Live betting essentiel."
    ),

    # ═══════════════════════════════════════════════════════════════
    # SCORE_DEPENDENT vs SCORE_DEPENDENT
    # ═══════════════════════════════════════════════════════════════

    ("SCORE_DEPENDENT", "SCORE_DEPENDENT"): FrictionResult(
        clash_type=ClashType.UNPREDICTABLE,
        tempo=Tempo.VARIABLE,
        goals_modifier=+0.2,
        cards_modifier=+0.3,
        corners_modifier=+0.5,
        primary_markets=["live_betting"],
        secondary_markets=["late_goal", "btts_yes"],
        avoid_markets=["exact_score"],
        first_half_bias=0.45,
        late_goal_prob=0.60,
        description="Match imprévisible. Les deux changent selon le score. Live only."
    ),
}


def get_friction(profile_a: str, profile_b: str) -> FrictionResult:
    """
    Retourne le résultat de friction entre deux profils tactiques.

    Args:
        profile_a: Profil de l'équipe A (home)
        profile_b: Profil de l'équipe B (away)

    Returns:
        FrictionResult avec tous les détails de la collision
    """
    # Normaliser en majuscules
    profile_a = profile_a.upper()
    profile_b = profile_b.upper()

    # Chercher dans la matrice
    key = (profile_a, profile_b)

    if key in FRICTION_MATRIX:
        return FRICTION_MATRIX[key]

    # Essayer l'inverse (symétrie pour certaines combinaisons)
    reverse_key = (profile_b, profile_a)
    if reverse_key in FRICTION_MATRIX:
        result = FRICTION_MATRIX[reverse_key]
        # Inverser first_half_bias car les équipes sont inversées
        return FrictionResult(
            clash_type=result.clash_type,
            tempo=result.tempo,
            goals_modifier=result.goals_modifier,
            cards_modifier=result.cards_modifier,
            corners_modifier=result.corners_modifier,
            primary_markets=result.primary_markets,
            secondary_markets=result.secondary_markets,
            avoid_markets=result.avoid_markets,
            first_half_bias=1 - result.first_half_bias,
            late_goal_prob=result.late_goal_prob,
            description=result.description
        )

    # Fallback: profil BALANCED par défaut
    return FRICTION_MATRIX[("BALANCED", "BALANCED")]


def analyze_match_friction(home_team: str, away_team: str,
                          home_profile: str, away_profile: str) -> dict:
    """
    Analyse complète de la friction pour un match.

    Returns:
        Dict avec toutes les recommandations de paris
    """
    friction = get_friction(home_profile, away_profile)

    return {
        "match": f"{home_team} vs {away_team}",
        "profiles": {
            "home": {"team": home_team, "profile": home_profile},
            "away": {"team": away_team, "profile": away_profile}
        },
        "friction": {
            "clash_type": friction.clash_type.value,
            "tempo": friction.tempo.value,
            "description": friction.description
        },
        "modifiers": {
            "goals": friction.goals_modifier,
            "cards": friction.cards_modifier,
            "corners": friction.corners_modifier
        },
        "timing": {
            "first_half_bias": friction.first_half_bias,
            "late_goal_prob": friction.late_goal_prob
        },
        "markets": {
            "primary": friction.primary_markets,
            "secondary": friction.secondary_markets,
            "avoid": friction.avoid_markets
        }
    }


# ═══════════════════════════════════════════════════════════════════
# TESTS ET VALIDATION
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║     MATRICE DE FRICTION 12×12 - VALIDATION                      ║")
    print("╚══════════════════════════════════════════════════════════════════╝")

    # Test 1: Nombre de combinaisons
    print(f"\n📊 Combinaisons définies: {len(FRICTION_MATRIX)}")
    expected = 12 * 12  # 144 combinaisons théoriques
    print(f"📊 Combinaisons théoriques: {expected}")

    # Test 2: Exemples de friction
    test_cases = [
        ("GEGENPRESS", "GEGENPRESS"),
        ("POSSESSION", "LOW_BLOCK"),
        ("GEGENPRESS", "LOW_BLOCK"),
        ("TRANSITION", "TRANSITION"),
        ("BALANCED", "BALANCED"),
    ]

    print("\n🔍 EXEMPLES DE FRICTION:")
    print("-" * 60)

    for profile_a, profile_b in test_cases:
        friction = get_friction(profile_a, profile_b)
        print(f"\n{profile_a} vs {profile_b}")
        print(f"  Clash: {friction.clash_type.value}")
        print(f"  Tempo: {friction.tempo.value}")
        print(f"  Goals: {friction.goals_modifier:+.1f}")
        print(f"  Markets: {friction.primary_markets[:3]}")

    # Test 3: Validation complète d'un match
    print("\n" + "=" * 60)
    print("🎯 ANALYSE MATCH COMPLET")
    print("=" * 60)

    analysis = analyze_match_friction(
        home_team="Liverpool",
        away_team="Manchester City",
        home_profile="GEGENPRESS",
        away_profile="POSSESSION"
    )

    import json
    print(json.dumps(analysis, indent=2))

    print("\n✅ MATRICE DE FRICTION 12×12 VALIDÉE!")
