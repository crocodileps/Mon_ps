"""
Market Registry - Source Unique de Verite pour tous les marches Mon_PS
======================================================================

PHILOSOPHIE ADN-CENTRIC:
- Chaque marche a sa configuration de closing odds
- La synthese utilise les facteurs ADN des equipes
- Le CLV est team-specific, pas generique

AUTEUR: Claude Code
DATE: 2025-12-19
VERSION: 1.0.0
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple


# ===============================================================================
#                              ENUMS DE BASE
# ===============================================================================

class MarketCategory(Enum):
    """Categories de marches pour classification"""
    RESULT = "result"           # 1X2, DNB, DC
    GOALS = "goals"             # Over/Under, BTTS, Exact Score
    TIMING = "timing"           # HT/FT, Goal 0-15, Goal 76-90
    CORNERS = "corners"         # Corners Over/Under
    CARDS = "cards"             # Cards Over/Under
    PLAYER = "player"           # Anytime Scorer, First Goalscorer
    SPECIAL = "special"         # Corner Goal, Header Goal, Penalty
    HANDICAP = "handicap"       # Asian Handicap, European Handicap


class ClosingSource(Enum):
    """Sources de closing odds par ordre de priorite"""
    FOOTBALL_DATA_UK = "football_data_uk"   # Closing reelle 1X2, O/U, AH
    BETEXPLORER = "betexplorer"             # Closing reelle BTTS, DNB, DC
    SYNTHESIZED_DNA = "synthesized_dna"     # Calculee avec facteurs ADN
    ESTIMATED = "estimated"                  # Moyenne historique
    NONE = "none"                            # Pas de source disponible


class LiquidityTier(Enum):
    """Niveaux de liquidite marche (taxe implicite)"""
    ELITE = "elite"         # 1.0% - 1X2 top leagues
    HIGH = "high"           # 1.5% - BTTS, O/U 2.5
    MEDIUM = "medium"       # 2.0% - DNB, DC, AH
    LOW = "low"             # 2.5% - Corners, Cards
    EXOTIC = "exotic"       # 5.0% - Player props, specials


class PayoffType(Enum):
    """Type de paiement du marche"""
    BINARY = "binary"           # Win/Lose (BTTS, O/U)
    CATEGORICAL = "categorical" # Multiple outcomes (1X2, CS)
    CONTINUOUS = "continuous"   # Asian Handicap (push possible)


# ===============================================================================
#                              MARKET TYPE ENUM
# ===============================================================================

class MarketType(Enum):
    """
    Enum unifie de tous les marches Mon_PS.

    CONVENTION DE NOMMAGE:
    - Tout en minuscules avec underscores
    - Nombres sans underscore: over_25 (pas over_2_5)
    - Prefixe par categorie: ht_ pour half-time, ah_ pour asian handicap
    """

    # === RESULT (1X2 et derives) ===
    HOME_WIN = "home"
    DRAW = "draw"
    AWAY_WIN = "away"
    DNB_HOME = "dnb_home"
    DNB_AWAY = "dnb_away"
    DC_1X = "dc_1x"
    DC_X2 = "dc_x2"
    DC_12 = "dc_12"

    # === GOALS (Over/Under) ===
    OVER_05 = "over_0.5"
    OVER_15 = "over_1.5"
    OVER_25 = "over_2.5"
    OVER_35 = "over_3.5"
    OVER_45 = "over_4.5"
    UNDER_05 = "under_0.5"
    UNDER_15 = "under_1.5"
    UNDER_25 = "under_2.5"
    UNDER_35 = "under_3.5"
    UNDER_45 = "under_4.5"

    # === GOALS (BTTS) ===
    BTTS_YES = "btts_yes"
    BTTS_NO = "btts_no"
    BTTS_BOTH_HALVES_YES = "btts_both_halves_yes"
    BTTS_BOTH_HALVES_NO = "btts_both_halves_no"

    # === GOALS (Team specific) ===
    HOME_OVER_05 = "home_over_0.5"
    HOME_OVER_15 = "home_over_1.5"
    HOME_OVER_25 = "home_over_2.5"
    AWAY_OVER_05 = "away_over_0.5"
    AWAY_OVER_15 = "away_over_1.5"
    AWAY_OVER_25 = "away_over_2.5"
    HOME_CLEAN_SHEET_YES = "home_clean_sheet"
    AWAY_CLEAN_SHEET_YES = "away_clean_sheet"
    HOME_WIN_TO_NIL = "home_win_to_nil"
    AWAY_WIN_TO_NIL = "away_win_to_nil"

    # === CORRECT SCORE ===
    CS_0_0 = "cs_0_0"
    CS_1_0 = "cs_1_0"
    CS_0_1 = "cs_0_1"
    CS_1_1 = "cs_1_1"
    CS_2_0 = "cs_2_0"
    CS_0_2 = "cs_0_2"
    CS_2_1 = "cs_2_1"
    CS_1_2 = "cs_1_2"
    CS_2_2 = "cs_2_2"
    CS_3_0 = "cs_3_0"
    CS_0_3 = "cs_0_3"
    CS_3_1 = "cs_3_1"
    CS_1_3 = "cs_1_3"

    # === HALF-TIME ===
    HT_HOME_WIN = "ht_home"
    HT_DRAW = "ht_draw"
    HT_AWAY_WIN = "ht_away"
    HT_OVER_05 = "ht_over_0.5"
    HT_UNDER_05 = "ht_under_0.5"
    HT_OVER_15 = "ht_over_1.5"
    HT_BTTS_YES = "ht_btts_yes"
    HT_BTTS_NO = "ht_btts_no"

    # === HT/FT ===
    DR_1_1 = "ht_ft_1_1"
    DR_1_X = "ht_ft_1_x"
    DR_1_2 = "ht_ft_1_2"
    DR_X_1 = "ht_ft_x_1"
    DR_X_X = "ht_ft_x_x"
    DR_X_2 = "ht_ft_x_2"
    DR_2_1 = "ht_ft_2_1"
    DR_2_X = "ht_ft_2_x"
    DR_2_2 = "ht_ft_2_2"

    # === ASIAN HANDICAP ===
    AH_HOME_M05 = "ah_home_-0.5"    # Home -0.5
    AH_HOME_M10 = "ah_home_-1.0"    # Home -1.0
    AH_HOME_M15 = "ah_home_-1.5"    # Home -1.5
    AH_HOME_M20 = "ah_home_-2.0"    # Home -2.0
    AH_AWAY_P05 = "ah_away_+0.5"    # Away +0.5
    AH_AWAY_P10 = "ah_away_+1.0"    # Away +1.0
    AH_AWAY_P15 = "ah_away_+1.5"    # Away +1.5
    AH_AWAY_P20 = "ah_away_+2.0"    # Away +2.0

    # === CORNERS ===
    CORNERS_OVER_85 = "corners_over_8.5"
    CORNERS_OVER_95 = "corners_over_9.5"
    CORNERS_OVER_105 = "corners_over_10.5"
    CORNERS_OVER_115 = "corners_over_11.5"
    CORNERS_UNDER_85 = "corners_under_8.5"
    CORNERS_UNDER_95 = "corners_under_9.5"
    CORNERS_UNDER_105 = "corners_under_10.5"

    # === CARDS ===
    CARDS_OVER_25 = "cards_over_2.5"
    CARDS_OVER_35 = "cards_over_3.5"
    CARDS_OVER_45 = "cards_over_4.5"
    CARDS_OVER_55 = "cards_over_5.5"
    CARDS_UNDER_35 = "cards_under_3.5"
    CARDS_UNDER_45 = "cards_under_4.5"

    # === TIMING ===
    GOAL_0_15 = "goal_0_15"
    GOAL_16_30 = "goal_16_30"
    GOAL_31_45 = "goal_31_45"
    GOAL_46_60 = "goal_46_60"
    GOAL_61_75 = "goal_61_75"
    GOAL_76_90 = "goal_76_90"
    NO_GOAL_FIRST_HALF = "no_goal_first_half"
    FIRST_HALF_OVER_05 = "first_half_over_0.5"
    FIRST_HALF_OVER_15 = "first_half_over_1.5"
    SECOND_HALF_OVER_05 = "second_half_over_0.5"
    SECOND_HALF_OVER_15 = "second_half_over_1.5"

    # === HALF COMPARISON ===
    HOME_2H_OVER_05 = "home_2h_over_05"
    FIRST_HALF_HIGHEST = "first_half_highest"
    SECOND_HALF_HIGHEST = "second_half_highest"

    # === PLAYER PROPS ===
    ANYTIME_SCORER = "anytime_scorer"
    FIRST_GOALSCORER = "first_goalscorer"
    LAST_GOALSCORER = "last_goalscorer"
    SCORER_2PLUS = "scorer_2plus"
    SCORER_HATTRICK = "scorer_hattrick"

    # === SPECIAL ===
    CORNER_GOAL = "corner_goal"
    HEADER_GOAL = "header_goal"
    SET_PIECE_GOAL = "set_piece_goal"
    PENALTY_SCORED = "penalty_scored"
    OWN_GOAL = "own_goal"
    OUTSIDE_BOX_GOAL = "outside_box_goal"
    SHOTS_ON_TARGET_OVER = "shots_on_target_over"

    # ═══════════════════════════════════════════════════════════════
    # EXACT GOALS (5)
    # ═══════════════════════════════════════════════════════════════
    EXACTLY_0 = "exactly_0_goals"
    EXACTLY_1 = "exactly_1_goals"
    EXACTLY_2 = "exactly_2_goals"
    EXACTLY_3 = "exactly_3_goals"
    EXACTLY_4 = "exactly_4_goals"

    # ═══════════════════════════════════════════════════════════════
    # GOAL RANGES (5)
    # ═══════════════════════════════════════════════════════════════
    GOALS_0_1 = "goals_0_1"
    GOALS_2_3 = "goals_2_3"
    GOALS_4_5 = "goals_4_5"
    GOALS_5_PLUS = "goals_5_plus"
    GOALS_6_PLUS = "goals_6_plus"

    # ═══════════════════════════════════════════════════════════════
    # ODD/EVEN GOALS (2)
    # ═══════════════════════════════════════════════════════════════
    ODD_GOALS = "odd_goals"
    EVEN_GOALS = "even_goals"

    # ═══════════════════════════════════════════════════════════════
    # WIN TO NIL NO (2)
    # ═══════════════════════════════════════════════════════════════
    HOME_WIN_TO_NIL_NO = "home_win_to_nil_no"
    AWAY_WIN_TO_NIL_NO = "away_win_to_nil_no"


# ===============================================================================
#                              CONFIGURATIONS
# ===============================================================================

@dataclass
class DNAFactorConfig:
    """
    Configuration des facteurs ADN pour la synthese closing d'un marche.

    PARADIGME ADN-CENTRIC:
    - home_factors: Facteurs ADN de l'equipe a domicile (defense)
    - away_factors: Facteurs ADN de l'equipe exterieure (attaque)
    - collision_pairs: Paires de facteurs pour calculer l'interaction
    - weights: Poids de chaque facteur dans le calcul final
    """
    home_factors: List[str] = field(default_factory=list)
    away_factors: List[str] = field(default_factory=list)
    collision_pairs: List[Tuple[str, str]] = field(default_factory=list)
    weights: Dict[str, float] = field(default_factory=dict)


@dataclass
class ClosingConfig:
    """
    Configuration pour obtenir la closing odds d'un marche.

    CASCADE DE FALLBACK:
    1. primary_source: Source principale (Betexplorer, Football Data UK)
    2. fallback_sources: Sources de secours dans l'ordre
    3. synthesis_base: Formule de base pour synthese (poisson, direct)
    4. dna_factors: Facteurs ADN pour ajuster la synthese
    5. quality_by_source: Score de qualite par source (0-1)
    """
    primary_source: ClosingSource
    fallback_sources: List[ClosingSource] = field(default_factory=list)
    synthesis_base: str = "poisson_bivariate"
    synthesis_inputs: List[str] = field(default_factory=list)
    dna_factors: Optional[DNAFactorConfig] = None
    quality_by_source: Dict[ClosingSource, float] = field(default_factory=dict)

    # Colonne specifique pour Football Data UK
    football_data_column: Optional[str] = None


@dataclass
class MarketMetadata:
    """
    Metadonnees completes d'un marche.

    CONTIENT:
    - Identification: canonical_name, aliases
    - Classification: category, payoff_type
    - Closing: closing_config avec cascade et ADN
    - Liquidite: tier, tax, min_edge
    - Relations: dependencies, correlations
    """
    canonical_name: str
    aliases: List[str] = field(default_factory=list)
    category: MarketCategory = MarketCategory.RESULT
    payoff_type: PayoffType = PayoffType.BINARY

    # Configuration closing ADN-aware
    closing_config: Optional[ClosingConfig] = None

    # Liquidite
    liquidity_tier: LiquidityTier = LiquidityTier.MEDIUM
    liquidity_tax: float = 0.02
    min_edge: float = 0.03

    # Dependances et correlations
    dependencies: List[MarketType] = field(default_factory=list)
    correlations: Dict[str, float] = field(default_factory=dict)

    # Sources de donnees ADN
    dna_sources: List[str] = field(default_factory=list)


# ===============================================================================
#                              MARKET REGISTRY
# ===============================================================================

MARKET_REGISTRY: Dict[MarketType, MarketMetadata] = {

    # ===========================================================================
    #                              RESULT MARKETS
    # ===========================================================================

    MarketType.HOME_WIN: MarketMetadata(
        canonical_name="home",
        aliases=["home_win", "1", "home_victory", "h", "home", "match_result_1", "ft_1", "win_home", "result_1"],
        category=MarketCategory.RESULT,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.FOOTBALL_DATA_UK,
            fallback_sources=[ClosingSource.ESTIMATED],
            football_data_column="AvgCH",
            quality_by_source={
                ClosingSource.FOOTBALL_DATA_UK: 1.0,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.ELITE,
        liquidity_tax=0.01,
        min_edge=0.02,
        correlations={"draw": -0.40, "away": -0.60, "dc_1x": 0.70, "dc_12": 0.65, "dnb_home": 0.85},
    ),

    MarketType.DRAW: MarketMetadata(
        canonical_name="draw",
        aliases=["x", "tie", "d", "draw", "match_result_x", "ft_x", "result_x", "match_draw"],
        category=MarketCategory.RESULT,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.FOOTBALL_DATA_UK,
            fallback_sources=[ClosingSource.ESTIMATED],
            football_data_column="AvgCD",
            quality_by_source={
                ClosingSource.FOOTBALL_DATA_UK: 1.0,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.ELITE,
        liquidity_tax=0.01,
        min_edge=0.02,
        correlations={"home": -0.40, "away": -0.40, "dc_1x": 0.65, "dc_x2": 0.65, "under_2.5": 0.35},
    ),

    MarketType.AWAY_WIN: MarketMetadata(
        canonical_name="away",
        aliases=["away_win", "2", "away_victory", "a", "away", "match_result_2", "ft_2", "win_away", "result_2"],
        category=MarketCategory.RESULT,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.FOOTBALL_DATA_UK,
            fallback_sources=[ClosingSource.ESTIMATED],
            football_data_column="AvgCA",
            quality_by_source={
                ClosingSource.FOOTBALL_DATA_UK: 1.0,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.ELITE,
        liquidity_tax=0.01,
        min_edge=0.02,
        correlations={"home": -0.60, "draw": -0.40, "dc_x2": 0.70, "dc_12": 0.65, "dnb_away": 0.85},
    ),

    MarketType.DNB_HOME: MarketMetadata(
        canonical_name="dnb_home",
        aliases=["draw_no_bet_home", "dnb_1", "dnb_home", "draw_no_bet_1", "money_line_home", "ml_home"],
        category=MarketCategory.RESULT,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.BETEXPLORER,
            fallback_sources=[ClosingSource.SYNTHESIZED_DNA, ClosingSource.ESTIMATED],
            synthesis_base="dnb_from_1x2",
            synthesis_inputs=["home_closing", "draw_closing"],
            dna_factors=DNAFactorConfig(
                home_factors=["home_win_rate", "home_draw_rate"],
                away_factors=["away_loss_rate", "away_draw_rate"],
                collision_pairs=[("home_dominance", "away_resilience")],
                weights={"home_factors": 0.4, "away_factors": 0.3, "collision": 0.3}
            ),
            quality_by_source={
                ClosingSource.BETEXPLORER: 1.0,
                ClosingSource.SYNTHESIZED_DNA: 0.90,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.03,
        dependencies=[MarketType.HOME_WIN, MarketType.DRAW],
    ),

    MarketType.DNB_AWAY: MarketMetadata(
        canonical_name="dnb_away",
        aliases=["draw_no_bet_away", "dnb_2", "dnb_away", "draw_no_bet_2", "money_line_away", "ml_away"],
        category=MarketCategory.RESULT,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.BETEXPLORER,
            fallback_sources=[ClosingSource.SYNTHESIZED_DNA, ClosingSource.ESTIMATED],
            synthesis_base="dnb_from_1x2",
            synthesis_inputs=["away_closing", "draw_closing"],
            dna_factors=DNAFactorConfig(
                home_factors=["home_loss_rate", "home_draw_rate"],
                away_factors=["away_win_rate", "away_draw_rate"],
                collision_pairs=[("home_vulnerability", "away_dominance")],
                weights={"home_factors": 0.3, "away_factors": 0.4, "collision": 0.3}
            ),
            quality_by_source={
                ClosingSource.BETEXPLORER: 1.0,
                ClosingSource.SYNTHESIZED_DNA: 0.90,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.03,
        dependencies=[MarketType.AWAY_WIN, MarketType.DRAW],
    ),

    MarketType.DC_1X: MarketMetadata(
        canonical_name="dc_1x",
        aliases=["double_chance_1x", "home_or_draw", "1x", "dc1x", "dc_home_draw", "home_draw", "result_1x"],
        category=MarketCategory.RESULT,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.BETEXPLORER,
            fallback_sources=[ClosingSource.SYNTHESIZED_DNA, ClosingSource.ESTIMATED],
            synthesis_base="dc_from_1x2",
            synthesis_inputs=["home_closing", "draw_closing"],
            dna_factors=DNAFactorConfig(
                home_factors=["home_unbeaten_rate"],
                away_factors=["away_win_rate"],
                collision_pairs=[],
                weights={"home_factors": 0.5, "away_factors": 0.5}
            ),
            quality_by_source={
                ClosingSource.BETEXPLORER: 1.0,
                ClosingSource.SYNTHESIZED_DNA: 0.90,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.03,
        dependencies=[MarketType.HOME_WIN, MarketType.DRAW],
    ),

    MarketType.DC_X2: MarketMetadata(
        canonical_name="dc_x2",
        aliases=["double_chance_x2", "draw_or_away", "x2", "dcx2", "dc_draw_away", "draw_away", "result_x2"],
        category=MarketCategory.RESULT,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.BETEXPLORER,
            fallback_sources=[ClosingSource.SYNTHESIZED_DNA, ClosingSource.ESTIMATED],
            synthesis_base="dc_from_1x2",
            synthesis_inputs=["draw_closing", "away_closing"],
            dna_factors=DNAFactorConfig(
                home_factors=["home_win_rate"],
                away_factors=["away_unbeaten_rate"],
                collision_pairs=[],
                weights={"home_factors": 0.5, "away_factors": 0.5}
            ),
            quality_by_source={
                ClosingSource.BETEXPLORER: 1.0,
                ClosingSource.SYNTHESIZED_DNA: 0.90,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.03,
        dependencies=[MarketType.DRAW, MarketType.AWAY_WIN],
    ),

    MarketType.DC_12: MarketMetadata(
        canonical_name="dc_12",
        aliases=["double_chance_12", "home_or_away", "no_draw", "12", "dc12", "dc_home_away", "home_away", "result_12"],
        category=MarketCategory.RESULT,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.BETEXPLORER,
            fallback_sources=[ClosingSource.SYNTHESIZED_DNA, ClosingSource.ESTIMATED],
            synthesis_base="dc_from_1x2",
            synthesis_inputs=["home_closing", "away_closing"],
            dna_factors=DNAFactorConfig(
                home_factors=["home_draw_rate"],
                away_factors=["away_draw_rate"],
                collision_pairs=[],
                weights={"home_factors": 0.5, "away_factors": 0.5}
            ),
            quality_by_source={
                ClosingSource.BETEXPLORER: 1.0,
                ClosingSource.SYNTHESIZED_DNA: 0.90,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.03,
        dependencies=[MarketType.HOME_WIN, MarketType.AWAY_WIN],
    ),

    # ===========================================================================
    #                              GOALS MARKETS
    # ===========================================================================

    MarketType.OVER_25: MarketMetadata(
        canonical_name="over_2.5",
        aliases=["over_2_5", "over25", "o25", "over_2.5", "total_over_2.5", "match_goals_over_2.5", "totals_over_2.5", "goals_over_2.5"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.FOOTBALL_DATA_UK,
            fallback_sources=[ClosingSource.ESTIMATED],
            football_data_column="AvgC>2.5",
            quality_by_source={
                ClosingSource.FOOTBALL_DATA_UK: 1.0,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.ELITE,
        liquidity_tax=0.01,
        min_edge=0.02,
        correlations={"btts_yes": 0.65, "over_3.5": 0.75, "under_2.5": -1.0},
    ),

    MarketType.UNDER_25: MarketMetadata(
        canonical_name="under_2.5",
        aliases=["under_2_5", "under25", "u25", "under_2.5", "total_under_2.5", "match_goals_under_2.5", "totals_under_2.5", "goals_under_2.5"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.FOOTBALL_DATA_UK,
            fallback_sources=[ClosingSource.ESTIMATED],
            football_data_column="AvgC<2.5",
            quality_by_source={
                ClosingSource.FOOTBALL_DATA_UK: 1.0,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.ELITE,
        liquidity_tax=0.01,
        min_edge=0.02,
        correlations={"btts_no": 0.55, "under_3.5": 0.80, "over_2.5": -1.0},
    ),

    MarketType.BTTS_YES: MarketMetadata(
        canonical_name="btts_yes",
        aliases=["btts", "bts_yes", "both_teams_to_score", "gg", "btts_yes", "bts", "both_to_score", "goals_both_teams", "gol_gol"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.BETEXPLORER,
            fallback_sources=[ClosingSource.SYNTHESIZED_DNA, ClosingSource.ESTIMATED],
            synthesis_base="poisson_bivariate",
            synthesis_inputs=["over_25_closing", "home_closing", "away_closing", "draw_closing"],
            dna_factors=DNAFactorConfig(
                home_factors=["cs_pct_home", "resist_btts", "xga_per_90", "resist_global"],
                away_factors=["btts_tendency_away", "goals_away_avg", "fail_to_score_away_pct", "xg_away"],
                collision_pairs=[
                    ("resist_pressing", "pressing_intensity"),
                    ("resist_open_play", "open_play_goals_pct"),
                    ("defensive_compactness", "chance_creation")
                ],
                weights={
                    "home_factors": 0.30,
                    "away_factors": 0.30,
                    "collision": 0.25,
                    "base_poisson": 0.15
                }
            ),
            quality_by_source={
                ClosingSource.BETEXPLORER: 1.0,
                ClosingSource.SYNTHESIZED_DNA: 0.90,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.HIGH,
        liquidity_tax=0.015,
        min_edge=0.03,
        correlations={"over_2.5": 0.65, "btts_no": -1.0},
        dna_sources=["team_dna_unified_v2.json"],
    ),

    MarketType.BTTS_NO: MarketMetadata(
        canonical_name="btts_no",
        aliases=["bts_no", "both_teams_to_score_no", "ng", "btts_no", "no_btts", "both_to_score_no", "no_gol_gol"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.BETEXPLORER,
            fallback_sources=[ClosingSource.SYNTHESIZED_DNA, ClosingSource.ESTIMATED],
            synthesis_base="poisson_bivariate",
            synthesis_inputs=["under_25_closing", "home_closing", "away_closing", "draw_closing"],
            dna_factors=DNAFactorConfig(
                home_factors=["cs_pct_home", "resist_global", "xga_per_90"],
                away_factors=["fail_to_score_away_pct", "goals_away_avg"],
                collision_pairs=[
                    ("defensive_solidity", "attack_efficiency"),
                    ("resist_low_block", "low_block_breaking")
                ],
                weights={
                    "home_factors": 0.35,
                    "away_factors": 0.30,
                    "collision": 0.20,
                    "base_poisson": 0.15
                }
            ),
            quality_by_source={
                ClosingSource.BETEXPLORER: 1.0,
                ClosingSource.SYNTHESIZED_DNA: 0.90,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.HIGH,
        liquidity_tax=0.015,
        min_edge=0.03,
        correlations={"under_2.5": 0.55, "btts_yes": -1.0},
        dna_sources=["team_dna_unified_v2.json"],
    ),

    MarketType.HOME_CLEAN_SHEET_YES: MarketMetadata(
        canonical_name="home_clean_sheet",
        aliases=["home_cs", "home_shutout", "home_no_goals_against", "clean_sheet_home"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            synthesis_base="clean_sheet_from_poisson",
            synthesis_inputs=["home_closing", "away_closing", "draw_closing"],
            dna_factors=DNAFactorConfig(
                home_factors=["cs_pct_home", "xga_per_90", "resist_global"],
                away_factors=["goals_away_avg", "fail_to_score_away_pct", "xg_away"],
                collision_pairs=[
                    ("defensive_solidity", "attack_quality")
                ],
                weights={
                    "home_factors": 0.45,
                    "away_factors": 0.35,
                    "collision": 0.20
                }
            ),
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.85,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.04,
        dna_sources=["team_dna_unified_v2.json"],
    ),

    MarketType.AWAY_CLEAN_SHEET_YES: MarketMetadata(
        canonical_name="away_clean_sheet",
        aliases=["away_cs", "away_shutout", "away_no_goals_against", "clean_sheet_away"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            synthesis_base="clean_sheet_from_poisson",
            synthesis_inputs=["home_closing", "away_closing", "draw_closing"],
            dna_factors=DNAFactorConfig(
                home_factors=["goals_home_avg", "fail_to_score_home_pct", "xg_home"],
                away_factors=["cs_pct_away", "xga_per_90_away", "resist_global_away"],
                collision_pairs=[
                    ("attack_quality", "defensive_solidity_away")
                ],
                weights={
                    "home_factors": 0.35,
                    "away_factors": 0.45,
                    "collision": 0.20
                }
            ),
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.85,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.04,
        dna_sources=["team_dna_unified_v2.json"],
    ),

    # ===========================================================================
    #                              TIMING MARKETS
    # ===========================================================================

    MarketType.GOAL_76_90: MarketMetadata(
        canonical_name="goal_76_90",
        aliases=["late_goal", "goal_last_15"],
        category=MarketCategory.TIMING,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            synthesis_base="timing_from_profiles",
            synthesis_inputs=["over_25_closing"],
            dna_factors=DNAFactorConfig(
                home_factors=["late_goal_conceded_pct", "resist_late"],
                away_factors=["late_goal_scored_pct", "super_sub_effect", "fitness_profile"],
                collision_pairs=[
                    ("resist_late", "clutch_profile")
                ],
                weights={
                    "home_factors": 0.30,
                    "away_factors": 0.40,
                    "collision": 0.20,
                    "base_timing": 0.10
                }
            ),
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.025,
        min_edge=0.05,
        dna_sources=["team_dna_unified_v2.json"],
    ),

    MarketType.GOAL_0_15: MarketMetadata(
        canonical_name="goal_0_15",
        aliases=["early_goal", "goal_first_15"],
        category=MarketCategory.TIMING,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            synthesis_base="timing_from_profiles",
            synthesis_inputs=["over_25_closing"],
            dna_factors=DNAFactorConfig(
                home_factors=["early_goal_conceded_pct", "resist_early"],
                away_factors=["early_goal_scored_pct", "fast_starter_profile"],
                collision_pairs=[
                    ("resist_early", "pressing_intensity")
                ],
                weights={
                    "home_factors": 0.30,
                    "away_factors": 0.40,
                    "collision": 0.20,
                    "base_timing": 0.10
                }
            ),
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.025,
        min_edge=0.05,
        dna_sources=["team_dna_unified_v2.json"],
    ),

    # ===========================================================================
    #                              SPECIAL MARKETS
    # ===========================================================================

    MarketType.CORNER_GOAL: MarketMetadata(
        canonical_name="corner_goal",
        aliases=["goal_from_corner", "corner_goal_yes"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            synthesis_base="special_from_profiles",
            synthesis_inputs=["corners_over_95_closing"],
            dna_factors=DNAFactorConfig(
                home_factors=["resist_aerial", "resist_set_piece", "corner_defense_rating"],
                away_factors=["corner_goal_pct", "header_specialists", "set_piece_threat"],
                collision_pairs=[
                    ("resist_aerial", "aerial_threat"),
                    ("resist_set_piece", "set_piece_quality")
                ],
                weights={
                    "home_factors": 0.35,
                    "away_factors": 0.40,
                    "collision": 0.25
                }
            ),
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.EXOTIC,
        liquidity_tax=0.05,
        min_edge=0.08,
        dna_sources=["team_dna_unified_v2.json", "goalscorer_profiles_2025.json"],
    ),

    MarketType.HEADER_GOAL: MarketMetadata(
        canonical_name="header_goal",
        aliases=["headed_goal", "goal_via_header"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            synthesis_base="special_from_profiles",
            synthesis_inputs=["corners_over_95_closing", "over_25_closing"],
            dna_factors=DNAFactorConfig(
                home_factors=["resist_aerial", "aerial_duels_won_pct"],
                away_factors=["header_goal_pct", "header_specialists", "cross_quality"],
                collision_pairs=[
                    ("resist_aerial", "aerial_threat")
                ],
                weights={
                    "home_factors": 0.30,
                    "away_factors": 0.45,
                    "collision": 0.25
                }
            ),
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.EXOTIC,
        liquidity_tax=0.05,
        min_edge=0.08,
        dna_sources=["team_dna_unified_v2.json", "goalscorer_profiles_2025.json"],
    ),

    MarketType.PENALTY_SCORED: MarketMetadata(
        canonical_name="penalty_scored",
        aliases=["penalty", "penalty_yes"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            synthesis_base="special_from_profiles",
            synthesis_inputs=["over_25_closing"],
            dna_factors=DNAFactorConfig(
                home_factors=["penalty_conceded_pct", "fouls_in_box_pct"],
                away_factors=["penalty_won_pct", "dribbles_in_box", "penalty_takers"],
                collision_pairs=[
                    ("defensive_style", "dribbling_quality")
                ],
                weights={
                    "home_factors": 0.35,
                    "away_factors": 0.40,
                    "collision": 0.15,
                    "referee_factor": 0.10
                }
            ),
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.70,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.EXOTIC,
        liquidity_tax=0.05,
        min_edge=0.10,
        dna_sources=["team_dna_unified_v2.json", "goalscorer_profiles_2025.json"],
    ),

    # ===========================================================================
    #                              HALF COMPARISON MARKETS
    # ===========================================================================

    MarketType.HOME_2H_OVER_05: MarketMetadata(
        canonical_name="home_2h_over_05",
        aliases=["home_to_score_2h", "home_2nd_half_goal", "home_score_2h"],
        category=MarketCategory.TIMING,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.025,
        min_edge=0.03,
        correlations={"home_over_0.5": 0.60, "over_2.5": 0.40, "second_half_over_0.5": 0.50},
    ),

    MarketType.FIRST_HALF_HIGHEST: MarketMetadata(
        canonical_name="first_half_highest",
        aliases=["1h_highest_scoring", "more_goals_first_half"],
        category=MarketCategory.TIMING,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.025,
        min_edge=0.03,
        correlations={"first_half_over_1.5": 0.55, "ht_over_0.5": 0.50},
    ),

    MarketType.SECOND_HALF_HIGHEST: MarketMetadata(
        canonical_name="second_half_highest",
        aliases=["2h_highest_scoring", "more_goals_second_half"],
        category=MarketCategory.TIMING,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.025,
        min_edge=0.03,
        correlations={"second_half_over_1.5": 0.55, "second_half_over_0.5": 0.50},
    ),

    # ===========================================================================
    #                              PLAYER MARKETS
    # ===========================================================================

    MarketType.ANYTIME_SCORER: MarketMetadata(
        canonical_name="anytime_scorer",
        aliases=["anytime_goalscorer", "ats"],
        category=MarketCategory.PLAYER,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            synthesis_base="player_from_profiles",
            synthesis_inputs=["over_25_closing", "btts_yes_closing"],
            dna_factors=DNAFactorConfig(
                home_factors=["goals_conceded_avg", "resist_global"],
                away_factors=["top_scorers", "goals_per_90"],
                collision_pairs=[
                    ("defensive_weakness", "player_threat")
                ],
                weights={
                    "home_factors": 0.25,
                    "away_factors": 0.50,
                    "player_profile": 0.25
                }
            ),
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.70,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.EXOTIC,
        liquidity_tax=0.05,
        min_edge=0.08,
        dna_sources=["team_dna_unified_v2.json", "goalscorer_profiles_2025.json"],
    ),

    MarketType.FIRST_GOALSCORER: MarketMetadata(
        canonical_name="first_goalscorer",
        aliases=["fgs", "first_scorer"],
        category=MarketCategory.PLAYER,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            synthesis_base="player_from_profiles",
            synthesis_inputs=["over_25_closing", "goal_0_15_closing"],
            dna_factors=DNAFactorConfig(
                home_factors=["concede_first_pct", "resist_early"],
                away_factors=["score_first_pct", "fast_starter_profile", "first_goal_specialists"],
                collision_pairs=[
                    ("resist_early", "early_pressure")
                ],
                weights={
                    "home_factors": 0.20,
                    "away_factors": 0.40,
                    "player_profile": 0.40
                }
            ),
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.65,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.EXOTIC,
        liquidity_tax=0.08,
        min_edge=0.12,
        dna_sources=["team_dna_unified_v2.json", "goalscorer_profiles_2025.json"],
    ),

    # ===========================================================================
    #                              GOALS OVER/UNDER (COMPLET)
    # ===========================================================================

    MarketType.OVER_05: MarketMetadata(
        canonical_name="over_0.5",
        aliases=["over_0_5", "over05", "o05", "over_0.5", "total_over_0.5", "match_goals_over_0.5", "totals_over_0.5", "goals_over_0.5"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.85,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.HIGH,
        liquidity_tax=0.015,
        min_edge=0.02,
        correlations={"over_1.5": 0.95, "over_2.5": 0.85, "under_0.5": -1.0, "btts_yes": 0.75},
    ),

    MarketType.OVER_15: MarketMetadata(
        canonical_name="over_1.5",
        aliases=["over_1_5", "over15", "o15", "over_1.5", "total_over_1.5", "match_goals_over_1.5", "totals_over_1.5", "goals_over_1.5"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.85,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.ELITE,
        liquidity_tax=0.01,
        min_edge=0.02,
        correlations={"over_0.5": 0.95, "over_2.5": 0.90, "over_3.5": 0.75, "under_1.5": -1.0, "btts_yes": 0.70},
    ),

    MarketType.OVER_35: MarketMetadata(
        canonical_name="over_3.5",
        aliases=["over_3_5", "over35", "o35", "over_3.5", "total_over_3.5", "match_goals_over_3.5", "totals_over_3.5", "goals_over_3.5"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.85,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.HIGH,
        liquidity_tax=0.015,
        min_edge=0.02,
        correlations={"over_2.5": 0.95, "over_4.5": 0.85, "under_3.5": -1.0, "btts_yes": 0.55},
    ),

    MarketType.OVER_45: MarketMetadata(
        canonical_name="over_4.5",
        aliases=["over_4_5", "over45", "o45", "over_4.5", "total_over_4.5", "match_goals_over_4.5", "totals_over_4.5", "goals_over_4.5"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.85,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.025,
        correlations={"over_3.5": 0.95, "under_4.5": -1.0},
    ),

    MarketType.UNDER_05: MarketMetadata(
        canonical_name="under_0.5",
        aliases=["under_0_5", "under05", "u05", "under_0.5", "total_under_0.5", "match_goals_under_0.5", "totals_under_0.5", "goals_under_0.5"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.85,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.HIGH,
        liquidity_tax=0.015,
        min_edge=0.02,
        correlations={"under_1.5": 0.95, "over_0.5": -1.0, "btts_no": 0.99},
    ),

    MarketType.UNDER_15: MarketMetadata(
        canonical_name="under_1.5",
        aliases=["under_1_5", "under15", "u15", "under_1.5", "total_under_1.5", "match_goals_under_1.5", "totals_under_1.5", "goals_under_1.5"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.85,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.ELITE,
        liquidity_tax=0.01,
        min_edge=0.02,
        correlations={"under_0.5": 0.95, "under_2.5": 0.90, "over_1.5": -1.0, "btts_no": 0.75},
    ),

    MarketType.UNDER_35: MarketMetadata(
        canonical_name="under_3.5",
        aliases=["under_3_5", "under35", "u35", "under_3.5", "total_under_3.5", "match_goals_under_3.5", "totals_under_3.5", "goals_under_3.5"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.85,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.HIGH,
        liquidity_tax=0.015,
        min_edge=0.02,
        correlations={"under_2.5": 0.95, "under_4.5": 0.90, "over_3.5": -1.0},
    ),

    MarketType.UNDER_45: MarketMetadata(
        canonical_name="under_4.5",
        aliases=["under_4_5", "under45", "u45", "under_4.5", "total_under_4.5", "match_goals_under_4.5", "totals_under_4.5", "goals_under_4.5"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.85,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.025,
        correlations={"under_3.5": 0.95, "over_4.5": -1.0},
    ),

    # ===========================================================================
    #                              TEAM GOALS (HOME/AWAY)
    # ===========================================================================

    MarketType.HOME_OVER_05: MarketMetadata(
        canonical_name="home_over_0.5",
        aliases=["home_over_0_5", "home_o05", "home_over_0.5", "home_to_score"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.85,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.025,
        correlations={"home_over_1.5": 0.90, "btts_yes": 0.70, "home": 0.55, "away_clean_sheet": -0.95},
    ),

    MarketType.HOME_OVER_15: MarketMetadata(
        canonical_name="home_over_1.5",
        aliases=["home_over_1_5", "home_o15", "home_over_1.5"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.85,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.025,
        correlations={"home_over_0.5": 0.95, "home_over_2.5": 0.85, "home": 0.65},
    ),

    MarketType.HOME_OVER_25: MarketMetadata(
        canonical_name="home_over_2.5",
        aliases=["home_over_2_5", "home_o25", "home_over_2.5"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.85,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.025,
        min_edge=0.03,
        correlations={"home_over_1.5": 0.95, "home": 0.70, "over_2.5": 0.75},
    ),

    MarketType.AWAY_OVER_05: MarketMetadata(
        canonical_name="away_over_0.5",
        aliases=["away_over_0_5", "away_o05", "away_over_0.5", "away_to_score"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.85,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.025,
        correlations={"away_over_1.5": 0.90, "btts_yes": 0.70, "away": 0.50, "home_clean_sheet": -0.95},
    ),

    MarketType.AWAY_OVER_15: MarketMetadata(
        canonical_name="away_over_1.5",
        aliases=["away_over_1_5", "away_o15", "away_over_1.5"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.85,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.025,
        correlations={"away_over_0.5": 0.95, "away_over_2.5": 0.85, "away": 0.60},
    ),

    MarketType.AWAY_OVER_25: MarketMetadata(
        canonical_name="away_over_2.5",
        aliases=["away_over_2_5", "away_o25", "away_over_2.5"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.85,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.025,
        min_edge=0.03,
        correlations={"away_over_1.5": 0.95, "away": 0.65, "over_2.5": 0.70},
    ),

    # ===========================================================================
    #                              WIN TO NIL
    # ===========================================================================

    MarketType.HOME_WIN_TO_NIL: MarketMetadata(
        canonical_name="home_win_to_nil",
        aliases=["home_wtn", "home_to_nil", "home_clean_win"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.85,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.025,
        min_edge=0.03,
        correlations={"home": 0.85, "away_clean_sheet": -0.99, "btts_no": 0.90, "home_clean_sheet": 0.60},
    ),

    MarketType.AWAY_WIN_TO_NIL: MarketMetadata(
        canonical_name="away_win_to_nil",
        aliases=["away_wtn", "away_to_nil", "away_clean_win"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.85,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.025,
        min_edge=0.03,
        correlations={"away": 0.85, "home_clean_sheet": -0.99, "btts_no": 0.90, "away_clean_sheet": 0.60},
    ),

    # ===========================================================================
    #                              BTTS SPECIALS
    # ===========================================================================

    MarketType.BTTS_BOTH_HALVES_YES: MarketMetadata(
        canonical_name="btts_both_halves_yes",
        aliases=["btts_bh_yes", "btts_both_halves", "gg_both_halves"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.025,
        min_edge=0.035,
        correlations={"btts_yes": 0.85, "over_2.5": 0.75, "btts_both_halves_no": -1.0},
    ),

    MarketType.BTTS_BOTH_HALVES_NO: MarketMetadata(
        canonical_name="btts_both_halves_no",
        aliases=["btts_bh_no", "ng_both_halves"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.025,
        min_edge=0.035,
        correlations={"btts_no": 0.60, "btts_both_halves_yes": -1.0},
    ),

    # ===========================================================================
    #                              CORNERS MARKETS
    # ===========================================================================

    MarketType.CORNERS_OVER_85: MarketMetadata(
        canonical_name="corners_over_8.5",
        aliases=["corners_o85", "corn_over_8.5", "corners_over_8_5", "corners_over_8.5"],
        category=MarketCategory.CORNERS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.025,
        min_edge=0.03,
        correlations={"corners_over_9.5": 0.90, "corners_over_10.5": 0.75, "corners_under_8.5": -1.0},
    ),

    MarketType.CORNERS_OVER_95: MarketMetadata(
        canonical_name="corners_over_9.5",
        aliases=["corners_o95", "corn_over_9.5", "corners_over_9_5", "corners_over_9.5"],
        category=MarketCategory.CORNERS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.025,
        min_edge=0.03,
        correlations={"corners_over_8.5": 0.95, "corners_over_10.5": 0.85, "corners_under_9.5": -1.0},
    ),

    MarketType.CORNERS_OVER_105: MarketMetadata(
        canonical_name="corners_over_10.5",
        aliases=["corners_o105", "corn_over_10.5", "corners_over_10_5", "corners_over_10.5"],
        category=MarketCategory.CORNERS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.025,
        min_edge=0.03,
        correlations={"corners_over_9.5": 0.95, "corners_over_11.5": 0.85, "corners_under_10.5": -1.0},
    ),

    MarketType.CORNERS_OVER_115: MarketMetadata(
        canonical_name="corners_over_11.5",
        aliases=["corners_o115", "corn_over_11.5", "corners_over_11_5", "corners_over_11.5"],
        category=MarketCategory.CORNERS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.025,
        min_edge=0.035,
        correlations={"corners_over_10.5": 0.95},
    ),

    MarketType.CORNERS_UNDER_85: MarketMetadata(
        canonical_name="corners_under_8.5",
        aliases=["corners_u85", "corn_under_8.5", "corners_under_8_5", "corners_under_8.5"],
        category=MarketCategory.CORNERS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.025,
        min_edge=0.03,
        correlations={"corners_under_9.5": 0.90, "corners_over_8.5": -1.0},
    ),

    MarketType.CORNERS_UNDER_95: MarketMetadata(
        canonical_name="corners_under_9.5",
        aliases=["corners_u95", "corn_under_9.5", "corners_under_9_5", "corners_under_9.5"],
        category=MarketCategory.CORNERS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.025,
        min_edge=0.03,
        correlations={"corners_under_8.5": 0.95, "corners_under_10.5": 0.90, "corners_over_9.5": -1.0},
    ),

    MarketType.CORNERS_UNDER_105: MarketMetadata(
        canonical_name="corners_under_10.5",
        aliases=["corners_u105", "corn_under_10.5", "corners_under_10_5", "corners_under_10.5"],
        category=MarketCategory.CORNERS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.025,
        min_edge=0.03,
        correlations={"corners_under_9.5": 0.95, "corners_over_10.5": -1.0},
    ),

    # ===========================================================================
    #                              CARDS MARKETS
    # ===========================================================================

    MarketType.CARDS_OVER_25: MarketMetadata(
        canonical_name="cards_over_2.5",
        aliases=["cards_o25", "cards_over_2.5", "cards_over_2_5"],
        category=MarketCategory.CARDS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.025,
        min_edge=0.03,
        correlations={"cards_over_3.5": 0.90, "cards_over_4.5": 0.75},
    ),

    MarketType.CARDS_OVER_35: MarketMetadata(
        canonical_name="cards_over_3.5",
        aliases=["cards_o35", "cards_over_3.5", "cards_over_3_5"],
        category=MarketCategory.CARDS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.025,
        min_edge=0.03,
        correlations={"cards_over_2.5": 0.95, "cards_over_4.5": 0.85, "cards_under_3.5": -1.0},
    ),

    MarketType.CARDS_OVER_45: MarketMetadata(
        canonical_name="cards_over_4.5",
        aliases=["cards_o45", "cards_over_4.5", "cards_over_4_5"],
        category=MarketCategory.CARDS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.025,
        min_edge=0.03,
        correlations={"cards_over_3.5": 0.95, "cards_over_5.5": 0.85, "cards_under_4.5": -1.0},
    ),

    MarketType.CARDS_OVER_55: MarketMetadata(
        canonical_name="cards_over_5.5",
        aliases=["cards_o55", "cards_over_5.5", "cards_over_5_5"],
        category=MarketCategory.CARDS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.025,
        min_edge=0.035,
        correlations={"cards_over_4.5": 0.95},
    ),

    MarketType.CARDS_UNDER_35: MarketMetadata(
        canonical_name="cards_under_3.5",
        aliases=["cards_u35", "cards_under_3.5", "cards_under_3_5"],
        category=MarketCategory.CARDS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.025,
        min_edge=0.03,
        correlations={"cards_under_4.5": 0.90, "cards_over_3.5": -1.0},
    ),

    MarketType.CARDS_UNDER_45: MarketMetadata(
        canonical_name="cards_under_4.5",
        aliases=["cards_u45", "cards_under_4.5", "cards_under_4_5"],
        category=MarketCategory.CARDS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.025,
        min_edge=0.03,
        correlations={"cards_under_3.5": 0.95, "cards_over_4.5": -1.0},
    ),

    # ===========================================================================
    #                              HALF-TIME MARKETS
    # ===========================================================================

    MarketType.HT_HOME_WIN: MarketMetadata(
        canonical_name="ht_home",
        aliases=["ht_1", "halftime_home", "ht_home_win"],
        category=MarketCategory.TIMING,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.025,
        correlations={"home": 0.65, "ht_draw": -0.50, "ht_away": -0.60},
    ),

    MarketType.HT_DRAW: MarketMetadata(
        canonical_name="ht_draw",
        aliases=["ht_x", "halftime_draw"],
        category=MarketCategory.TIMING,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.025,
        correlations={"draw": 0.50, "ht_home": -0.50, "ht_away": -0.50, "ht_under_0.5": 0.70},
    ),

    MarketType.HT_AWAY_WIN: MarketMetadata(
        canonical_name="ht_away",
        aliases=["ht_2", "halftime_away", "ht_away_win"],
        category=MarketCategory.TIMING,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.025,
        correlations={"away": 0.60, "ht_draw": -0.50, "ht_home": -0.60},
    ),

    MarketType.HT_OVER_05: MarketMetadata(
        canonical_name="ht_over_0.5",
        aliases=["ht_o05", "halftime_over_0.5", "ht_over_0_5"],
        category=MarketCategory.TIMING,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.025,
        correlations={"over_1.5": 0.70, "btts_yes": 0.55, "ht_under_0.5": -1.0, "ht_over_1.5": 0.85},
    ),

    MarketType.HT_UNDER_05: MarketMetadata(
        canonical_name="ht_under_0.5",
        aliases=["ht_u05", "halftime_under_0.5", "ht_under_0_5", "first_half_0_goals"],
        category=MarketCategory.TIMING,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.025,
        correlations={"ht_draw": 0.70, "ht_over_0.5": -1.0},
    ),

    MarketType.HT_OVER_15: MarketMetadata(
        canonical_name="ht_over_1.5",
        aliases=["ht_o15", "halftime_over_1.5", "ht_over_1_5"],
        category=MarketCategory.TIMING,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.025,
        correlations={"ht_over_0.5": 0.95, "over_2.5": 0.65, "ht_btts_yes": 0.75},
    ),

    MarketType.HT_BTTS_YES: MarketMetadata(
        canonical_name="ht_btts_yes",
        aliases=["ht_gg", "halftime_btts", "ht_btts"],
        category=MarketCategory.TIMING,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.025,
        min_edge=0.035,
        correlations={"btts_yes": 0.70, "over_1.5": 0.60, "ht_btts_no": -1.0},
    ),

    MarketType.HT_BTTS_NO: MarketMetadata(
        canonical_name="ht_btts_no",
        aliases=["ht_ng", "halftime_btts_no"],
        category=MarketCategory.TIMING,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.025,
        min_edge=0.035,
        correlations={"btts_no": 0.55, "ht_btts_yes": -1.0},
    ),

    # ===========================================================================
    #                              HT/FT DOUBLE RESULT
    # ===========================================================================

    MarketType.DR_1_1: MarketMetadata(
        canonical_name="ht_ft_1_1",
        aliases=["htft_1_1", "halftime_fulltime_1_1", "ht_ft_home_home", "ht_ft_1_1"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.035,
        min_edge=0.04,
        correlations={"home": 0.80, "ht_home": 0.85},
    ),

    MarketType.DR_1_X: MarketMetadata(
        canonical_name="ht_ft_1_x",
        aliases=["htft_1_x", "halftime_fulltime_1_x", "ht_ft_home_draw"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.035,
        min_edge=0.04,
        correlations={"draw": 0.60, "ht_home": 0.55},
    ),

    MarketType.DR_1_2: MarketMetadata(
        canonical_name="ht_ft_1_2",
        aliases=["htft_1_2", "halftime_fulltime_1_2", "ht_ft_home_away", "ht_ft_1_2"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.70,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.EXOTIC,
        liquidity_tax=0.05,
        min_edge=0.06,
        correlations={"away": 0.50, "ht_home": 0.30},
    ),

    MarketType.DR_X_1: MarketMetadata(
        canonical_name="ht_ft_x_1",
        aliases=["htft_x_1", "halftime_fulltime_x_1", "ht_ft_draw_home"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.035,
        min_edge=0.04,
        correlations={"home": 0.55, "ht_draw": 0.60},
    ),

    MarketType.DR_X_X: MarketMetadata(
        canonical_name="ht_ft_x_x",
        aliases=["htft_x_x", "halftime_fulltime_x_x", "ht_ft_draw_draw"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.035,
        min_edge=0.04,
        correlations={"draw": 0.80, "ht_draw": 0.85, "under_2.5": 0.55},
    ),

    MarketType.DR_X_2: MarketMetadata(
        canonical_name="ht_ft_x_2",
        aliases=["htft_x_2", "halftime_fulltime_x_2", "ht_ft_draw_away"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.035,
        min_edge=0.04,
        correlations={"away": 0.55, "ht_draw": 0.60},
    ),

    MarketType.DR_2_1: MarketMetadata(
        canonical_name="ht_ft_2_1",
        aliases=["htft_2_1", "halftime_fulltime_2_1", "ht_ft_away_home", "ht_ft_2_1"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.70,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.EXOTIC,
        liquidity_tax=0.05,
        min_edge=0.06,
        correlations={"home": 0.50, "ht_away": 0.30},
    ),

    MarketType.DR_2_X: MarketMetadata(
        canonical_name="ht_ft_2_x",
        aliases=["htft_2_x", "halftime_fulltime_2_x", "ht_ft_away_draw"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.035,
        min_edge=0.04,
        correlations={"draw": 0.60, "ht_away": 0.55},
    ),

    MarketType.DR_2_2: MarketMetadata(
        canonical_name="ht_ft_2_2",
        aliases=["htft_2_2", "halftime_fulltime_2_2", "ht_ft_away_away", "ht_ft_2_2"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.035,
        min_edge=0.04,
        correlations={"away": 0.80, "ht_away": 0.85},
    ),

    # ===========================================================================
    #                              ASIAN HANDICAP
    # ===========================================================================

    MarketType.AH_HOME_M05: MarketMetadata(
        canonical_name="ah_home_-0.5",
        aliases=["ah_-0.5_home", "asian_home_m05", "ah_home_minus_05", "ah_home_-0.5"],
        category=MarketCategory.HANDICAP,
        payoff_type=PayoffType.CONTINUOUS,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.FOOTBALL_DATA_UK,
            fallback_sources=[ClosingSource.SYNTHESIZED_DNA, ClosingSource.ESTIMATED],
            football_data_column="AVBAHH",
            quality_by_source={
                ClosingSource.FOOTBALL_DATA_UK: 1.0,
                ClosingSource.SYNTHESIZED_DNA: 0.90,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.HIGH,
        liquidity_tax=0.015,
        min_edge=0.02,
        correlations={"home": 0.95, "dnb_home": 0.85, "ah_home_-1.0": 0.80},
    ),

    MarketType.AH_HOME_M10: MarketMetadata(
        canonical_name="ah_home_-1.0",
        aliases=["ah_-1.0_home", "asian_home_m10", "ah_home_minus_10", "ah_home_-1.0"],
        category=MarketCategory.HANDICAP,
        payoff_type=PayoffType.CONTINUOUS,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.85,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.HIGH,
        liquidity_tax=0.015,
        min_edge=0.02,
        correlations={"ah_home_-0.5": 0.90, "home": 0.85, "ah_home_-1.5": 0.80},
    ),

    MarketType.AH_HOME_M15: MarketMetadata(
        canonical_name="ah_home_-1.5",
        aliases=["ah_-1.5_home", "asian_home_m15", "ah_home_minus_15", "ah_home_-1.5"],
        category=MarketCategory.HANDICAP,
        payoff_type=PayoffType.CONTINUOUS,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.85,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.025,
        correlations={"ah_home_-1.0": 0.90, "home": 0.75, "ah_home_-2.0": 0.80},
    ),

    MarketType.AH_HOME_M20: MarketMetadata(
        canonical_name="ah_home_-2.0",
        aliases=["ah_-2.0_home", "asian_home_m20", "ah_home_minus_20", "ah_home_-2.0"],
        category=MarketCategory.HANDICAP,
        payoff_type=PayoffType.CONTINUOUS,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.85,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.025,
        correlations={"ah_home_-1.5": 0.90, "home": 0.65},
    ),

    MarketType.AH_AWAY_P05: MarketMetadata(
        canonical_name="ah_away_+0.5",
        aliases=["ah_+0.5_away", "asian_away_p05", "ah_away_plus_05", "ah_away_+0.5"],
        category=MarketCategory.HANDICAP,
        payoff_type=PayoffType.CONTINUOUS,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.FOOTBALL_DATA_UK,
            fallback_sources=[ClosingSource.SYNTHESIZED_DNA, ClosingSource.ESTIMATED],
            football_data_column="AVBAHA",
            quality_by_source={
                ClosingSource.FOOTBALL_DATA_UK: 1.0,
                ClosingSource.SYNTHESIZED_DNA: 0.90,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.HIGH,
        liquidity_tax=0.015,
        min_edge=0.02,
        correlations={"dc_x2": 0.95, "away": 0.70, "draw": 0.60, "ah_away_+1.0": 0.80},
    ),

    MarketType.AH_AWAY_P10: MarketMetadata(
        canonical_name="ah_away_+1.0",
        aliases=["ah_+1.0_away", "asian_away_p10", "ah_away_plus_10", "ah_away_+1.0"],
        category=MarketCategory.HANDICAP,
        payoff_type=PayoffType.CONTINUOUS,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.85,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.HIGH,
        liquidity_tax=0.015,
        min_edge=0.02,
        correlations={"ah_away_+0.5": 0.90, "dc_x2": 0.85, "ah_away_+1.5": 0.80},
    ),

    MarketType.AH_AWAY_P15: MarketMetadata(
        canonical_name="ah_away_+1.5",
        aliases=["ah_+1.5_away", "asian_away_p15", "ah_away_plus_15", "ah_away_+1.5"],
        category=MarketCategory.HANDICAP,
        payoff_type=PayoffType.CONTINUOUS,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.85,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.025,
        correlations={"ah_away_+1.0": 0.90, "ah_away_+2.0": 0.80},
    ),

    MarketType.AH_AWAY_P20: MarketMetadata(
        canonical_name="ah_away_+2.0",
        aliases=["ah_+2.0_away", "asian_away_p20", "ah_away_plus_20", "ah_away_+2.0"],
        category=MarketCategory.HANDICAP,
        payoff_type=PayoffType.CONTINUOUS,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.85,
                ClosingSource.ESTIMATED: 0.7
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.025,
        correlations={"ah_away_+1.5": 0.90},
    ),

    # ===========================================================================
    #                              CORRECT SCORE
    # ===========================================================================

    MarketType.CS_0_0: MarketMetadata(
        canonical_name="cs_0_0",
        aliases=["correct_score_0_0", "score_0_0", "0-0"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.05,
        min_edge=0.05,
        correlations={"under_0.5": 0.99, "btts_no": 0.99, "draw": 0.30},
    ),

    MarketType.CS_1_0: MarketMetadata(
        canonical_name="cs_1_0",
        aliases=["correct_score_1_0", "score_1_0", "1-0"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.05,
        min_edge=0.05,
        correlations={"home": 0.40, "under_1.5": 0.50, "btts_no": 0.50, "home_win_to_nil": 0.60},
    ),

    MarketType.CS_0_1: MarketMetadata(
        canonical_name="cs_0_1",
        aliases=["correct_score_0_1", "score_0_1", "0-1"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.05,
        min_edge=0.05,
        correlations={"away": 0.40, "under_1.5": 0.50, "btts_no": 0.50, "away_win_to_nil": 0.60},
    ),

    MarketType.CS_1_1: MarketMetadata(
        canonical_name="cs_1_1",
        aliases=["correct_score_1_1", "score_1_1", "1-1"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.05,
        min_edge=0.05,
        correlations={"btts_yes": 0.50, "draw": 0.35, "over_1.5": 0.50},
    ),

    MarketType.CS_2_0: MarketMetadata(
        canonical_name="cs_2_0",
        aliases=["correct_score_2_0", "score_2_0", "2-0"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.05,
        min_edge=0.05,
        correlations={"home": 0.50, "under_2.5": 0.50, "btts_no": 0.50, "home_win_to_nil": 0.70},
    ),

    MarketType.CS_0_2: MarketMetadata(
        canonical_name="cs_0_2",
        aliases=["correct_score_0_2", "score_0_2", "0-2"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.05,
        min_edge=0.05,
        correlations={"away": 0.50, "under_2.5": 0.50, "btts_no": 0.50, "away_win_to_nil": 0.70},
    ),

    MarketType.CS_2_1: MarketMetadata(
        canonical_name="cs_2_1",
        aliases=["correct_score_2_1", "score_2_1", "2-1"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.05,
        min_edge=0.05,
        correlations={"home": 0.45, "btts_yes": 0.50, "over_2.5": 0.50},
    ),

    MarketType.CS_1_2: MarketMetadata(
        canonical_name="cs_1_2",
        aliases=["correct_score_1_2", "score_1_2", "1-2"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.05,
        min_edge=0.05,
        correlations={"away": 0.45, "btts_yes": 0.50, "over_2.5": 0.50},
    ),

    MarketType.CS_2_2: MarketMetadata(
        canonical_name="cs_2_2",
        aliases=["correct_score_2_2", "score_2_2", "2-2"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.EXOTIC,
        liquidity_tax=0.05,
        min_edge=0.06,
        correlations={"btts_yes": 0.55, "draw": 0.40, "over_3.5": 0.50},
    ),

    MarketType.CS_3_0: MarketMetadata(
        canonical_name="cs_3_0",
        aliases=["correct_score_3_0", "score_3_0", "3-0"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.EXOTIC,
        liquidity_tax=0.05,
        min_edge=0.06,
        correlations={"home": 0.55, "over_2.5": 0.50, "btts_no": 0.50, "home_win_to_nil": 0.75},
    ),

    MarketType.CS_0_3: MarketMetadata(
        canonical_name="cs_0_3",
        aliases=["correct_score_0_3", "score_0_3", "0-3"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.EXOTIC,
        liquidity_tax=0.05,
        min_edge=0.06,
        correlations={"away": 0.55, "over_2.5": 0.50, "btts_no": 0.50, "away_win_to_nil": 0.75},
    ),

    MarketType.CS_3_1: MarketMetadata(
        canonical_name="cs_3_1",
        aliases=["correct_score_3_1", "score_3_1", "3-1"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.EXOTIC,
        liquidity_tax=0.05,
        min_edge=0.06,
        correlations={"home": 0.50, "btts_yes": 0.50, "over_3.5": 0.50},
    ),

    MarketType.CS_1_3: MarketMetadata(
        canonical_name="cs_1_3",
        aliases=["correct_score_1_3", "score_1_3", "1-3"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.EXOTIC,
        liquidity_tax=0.05,
        min_edge=0.06,
        correlations={"away": 0.50, "btts_yes": 0.50, "over_3.5": 0.50},
    ),

    # ===========================================================================
    #                              TIMING MARKETS (COMPLET)
    # ===========================================================================

    MarketType.GOAL_16_30: MarketMetadata(
        canonical_name="goal_16_30",
        aliases=["goal_16_to_30", "goal_mid_first_half"],
        category=MarketCategory.TIMING,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.025,
        min_edge=0.05,
        correlations={"over_1.5": 0.55, "goal_0_15": 0.40, "goal_31_45": 0.40},
    ),

    MarketType.GOAL_31_45: MarketMetadata(
        canonical_name="goal_31_45",
        aliases=["goal_31_to_45", "goal_end_first_half"],
        category=MarketCategory.TIMING,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.025,
        min_edge=0.05,
        correlations={"over_1.5": 0.55, "goal_16_30": 0.40, "goal_46_60": 0.35},
    ),

    MarketType.GOAL_46_60: MarketMetadata(
        canonical_name="goal_46_60",
        aliases=["goal_46_to_60", "goal_start_second_half"],
        category=MarketCategory.TIMING,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.025,
        min_edge=0.05,
        correlations={"over_1.5": 0.55, "goal_31_45": 0.35, "goal_61_75": 0.40},
    ),

    MarketType.GOAL_61_75: MarketMetadata(
        canonical_name="goal_61_75",
        aliases=["goal_61_to_75", "goal_mid_second_half"],
        category=MarketCategory.TIMING,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.025,
        min_edge=0.05,
        correlations={"over_1.5": 0.55, "goal_46_60": 0.40, "goal_76_90": 0.45},
    ),

    MarketType.NO_GOAL_FIRST_HALF: MarketMetadata(
        canonical_name="no_goal_first_half",
        aliases=["0_0_ht", "scoreless_first_half"],
        category=MarketCategory.TIMING,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.025,
        correlations={"ht_under_0.5": 0.99, "ht_draw": 0.70, "under_2.5": 0.50},
    ),

    MarketType.FIRST_HALF_OVER_05: MarketMetadata(
        canonical_name="first_half_over_0.5",
        aliases=["fh_over_05", "1h_over_0.5"],
        category=MarketCategory.TIMING,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.025,
        correlations={"ht_over_0.5": 0.99, "over_1.5": 0.70, "first_half_over_1.5": 0.85},
    ),

    MarketType.FIRST_HALF_OVER_15: MarketMetadata(
        canonical_name="first_half_over_1.5",
        aliases=["fh_over_15", "1h_over_1.5"],
        category=MarketCategory.TIMING,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.025,
        correlations={"ht_over_1.5": 0.99, "first_half_over_0.5": 0.95, "over_2.5": 0.60},
    ),

    MarketType.SECOND_HALF_OVER_05: MarketMetadata(
        canonical_name="second_half_over_0.5",
        aliases=["sh_over_05", "2h_over_0.5"],
        category=MarketCategory.TIMING,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.025,
        correlations={"over_1.5": 0.65, "second_half_over_1.5": 0.85},
    ),

    MarketType.SECOND_HALF_OVER_15: MarketMetadata(
        canonical_name="second_half_over_1.5",
        aliases=["sh_over_15", "2h_over_1.5"],
        category=MarketCategory.TIMING,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.025,
        correlations={"second_half_over_0.5": 0.95, "over_2.5": 0.55},
    ),

    # ===========================================================================
    #                              PLAYER PROPS (COMPLET)
    # ===========================================================================

    MarketType.LAST_GOALSCORER: MarketMetadata(
        canonical_name="last_goalscorer",
        aliases=["lgs", "last_scorer"],
        category=MarketCategory.PLAYER,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.65,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.EXOTIC,
        liquidity_tax=0.08,
        min_edge=0.12,
        correlations={"goal_76_90": 0.50, "anytime_scorer": 0.70},
    ),

    MarketType.SCORER_2PLUS: MarketMetadata(
        canonical_name="scorer_2plus",
        aliases=["brace", "2_goals", "scorer_2_or_more"],
        category=MarketCategory.PLAYER,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.65,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.EXOTIC,
        liquidity_tax=0.08,
        min_edge=0.12,
        correlations={"anytime_scorer": 0.85, "scorer_hattrick": 0.75},
    ),

    MarketType.SCORER_HATTRICK: MarketMetadata(
        canonical_name="scorer_hattrick",
        aliases=["hattrick", "3_goals", "scorer_3_or_more"],
        category=MarketCategory.PLAYER,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.60,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.EXOTIC,
        liquidity_tax=0.10,
        min_edge=0.15,
        correlations={"scorer_2plus": 0.90, "over_3.5": 0.60},
    ),

    # ===========================================================================
    #                              SPECIAL MARKETS (COMPLET)
    # ===========================================================================

    MarketType.SET_PIECE_GOAL: MarketMetadata(
        canonical_name="set_piece_goal",
        aliases=["set_piece", "goal_from_set_piece"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.70,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.EXOTIC,
        liquidity_tax=0.05,
        min_edge=0.08,
        correlations={"corner_goal": 0.70, "over_1.5": 0.50},
    ),

    MarketType.OWN_GOAL: MarketMetadata(
        canonical_name="own_goal",
        aliases=["og", "own_goal_yes"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.60,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.EXOTIC,
        liquidity_tax=0.08,
        min_edge=0.10,
        correlations={"over_1.5": 0.30},
    ),

    MarketType.OUTSIDE_BOX_GOAL: MarketMetadata(
        canonical_name="outside_box_goal",
        aliases=["long_range_goal", "goal_from_outside_box"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.65,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.EXOTIC,
        liquidity_tax=0.08,
        min_edge=0.10,
        correlations={"over_1.5": 0.40},
    ),

    MarketType.SHOTS_ON_TARGET_OVER: MarketMetadata(
        canonical_name="shots_on_target_over",
        aliases=["sot_over", "shots_on_target_over_9.5"],
        category=MarketCategory.SPECIAL,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.70,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.03,
        min_edge=0.04,
        correlations={"over_2.5": 0.50, "corners_over_9.5": 0.40},
    ),

    # ═══════════════════════════════════════════════════════════════
    # EXACT GOALS (5)
    # ═══════════════════════════════════════════════════════════════

    MarketType.EXACTLY_0: MarketMetadata(
        canonical_name="exactly_0_goals",
        aliases=["exact_0", "0_goals", "no_goals", "scoreless"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.03,
        min_edge=0.04,
        correlations={"under_0.5": 1.0, "under_1.5": 0.85, "btts_no": 0.90, "exactly_1_goals": -0.30},
    ),

    MarketType.EXACTLY_1: MarketMetadata(
        canonical_name="exactly_1_goals",
        aliases=["exact_1", "1_goal", "one_goal"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.03,
        min_edge=0.04,
        correlations={"under_1.5": 0.70, "under_2.5": 0.85, "exactly_0_goals": -0.30, "exactly_2_goals": -0.25},
    ),

    MarketType.EXACTLY_2: MarketMetadata(
        canonical_name="exactly_2_goals",
        aliases=["exact_2", "total_2_goals", "two_goals"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.03,
        min_edge=0.04,
        correlations={"under_2.5": 0.55, "over_1.5": 0.70, "exactly_1_goals": -0.25, "exactly_3_goals": -0.20},
    ),

    MarketType.EXACTLY_3: MarketMetadata(
        canonical_name="exactly_3_goals",
        aliases=["exact_3", "total_3_goals", "three_goals"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.03,
        min_edge=0.04,
        correlations={"over_2.5": 0.70, "under_3.5": 0.55, "exactly_2_goals": -0.20, "exactly_4_goals": -0.15},
    ),

    MarketType.EXACTLY_4: MarketMetadata(
        canonical_name="exactly_4_goals",
        aliases=["exact_4", "4_goals", "four_goals"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.03,
        min_edge=0.04,
        correlations={"over_3.5": 0.70, "under_4.5": 0.55, "exactly_3_goals": -0.15},
    ),

    # ═══════════════════════════════════════════════════════════════
    # GOAL RANGES (5)
    # ═══════════════════════════════════════════════════════════════

    MarketType.GOALS_0_1: MarketMetadata(
        canonical_name="goals_0_1",
        aliases=["0_1_goals", "zero_one_goals", "low_scoring"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.03,
        min_edge=0.04,
        correlations={"under_1.5": 1.0, "under_2.5": 0.85, "btts_no": 0.70, "goals_2_3": -0.50},
    ),

    MarketType.GOALS_2_3: MarketMetadata(
        canonical_name="goals_2_3",
        aliases=["2_3_goals", "two_three_goals", "medium_scoring"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.03,
        min_edge=0.04,
        correlations={"over_1.5": 0.80, "under_3.5": 0.60, "goals_0_1": -0.50, "goals_4_5": -0.40},
    ),

    MarketType.GOALS_4_5: MarketMetadata(
        canonical_name="goals_4_5",
        aliases=["4_5_goals", "four_five_goals", "high_scoring"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.03,
        min_edge=0.05,
        correlations={"over_3.5": 0.85, "over_2.5": 0.95, "goals_2_3": -0.40},
    ),

    MarketType.GOALS_5_PLUS: MarketMetadata(
        canonical_name="goals_5_plus",
        aliases=["5_plus_goals", "five_plus", "5+"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.70,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.04,
        min_edge=0.05,
        correlations={"over_4.5": 1.0, "over_3.5": 0.90, "goals_0_1": -0.80},
    ),

    MarketType.GOALS_6_PLUS: MarketMetadata(
        canonical_name="goals_6_plus",
        aliases=["6_plus_goals", "six_plus", "6+"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.CATEGORICAL,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.65,
                ClosingSource.ESTIMATED: 0.5
            }
        ),
        liquidity_tier=LiquidityTier.EXOTIC,
        liquidity_tax=0.05,
        min_edge=0.06,
        correlations={"over_4.5": 0.85, "goals_5_plus": 0.70, "goals_0_1": -0.90},
    ),

    # ═══════════════════════════════════════════════════════════════
    # ODD/EVEN GOALS (2)
    # ═══════════════════════════════════════════════════════════════

    MarketType.ODD_GOALS: MarketMetadata(
        canonical_name="odd_goals",
        aliases=["odd", "odd_total", "impair"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.03,
        correlations={"even_goals": -1.0, "exactly_1_goals": 0.25, "exactly_3_goals": 0.25},
    ),

    MarketType.EVEN_GOALS: MarketMetadata(
        canonical_name="even_goals",
        aliases=["even", "even_total", "pair"],
        category=MarketCategory.GOALS,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.75,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.MEDIUM,
        liquidity_tax=0.02,
        min_edge=0.03,
        correlations={"odd_goals": -1.0, "exactly_0_goals": 0.30, "exactly_2_goals": 0.25, "exactly_4_goals": 0.20},
    ),

    # ═══════════════════════════════════════════════════════════════
    # WIN TO NIL NO (2)
    # ═══════════════════════════════════════════════════════════════

    MarketType.HOME_WIN_TO_NIL_NO: MarketMetadata(
        canonical_name="home_win_to_nil_no",
        aliases=["home_wtn_no", "home_win_concede", "home_dirty_win"],
        category=MarketCategory.RESULT,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.03,
        min_edge=0.04,
        correlations={"home_win_to_nil": -0.60, "home": 0.70, "btts_yes": 0.50},
    ),

    MarketType.AWAY_WIN_TO_NIL_NO: MarketMetadata(
        canonical_name="away_win_to_nil_no",
        aliases=["away_wtn_no", "away_win_concede", "away_dirty_win"],
        category=MarketCategory.RESULT,
        payoff_type=PayoffType.BINARY,
        closing_config=ClosingConfig(
            primary_source=ClosingSource.SYNTHESIZED_DNA,
            fallback_sources=[ClosingSource.ESTIMATED],
            quality_by_source={
                ClosingSource.SYNTHESIZED_DNA: 0.80,
                ClosingSource.ESTIMATED: 0.6
            }
        ),
        liquidity_tier=LiquidityTier.LOW,
        liquidity_tax=0.03,
        min_edge=0.04,
        correlations={"away_win_to_nil": -0.60, "away": 0.70, "btts_yes": 0.50},
    ),
}


# ===============================================================================
#                              ALIAS REGISTRY
# ===============================================================================

def _build_alias_registry() -> Dict[str, MarketType]:
    """
    Construit un dictionnaire inverse: alias -> MarketType

    Permet de normaliser n'importe quelle variante vers le MarketType canonical.
    Les aliases sont normalises de la meme maniere que dans normalize_market().
    """
    import re

    def _normalize_alias(alias: str) -> str:
        """Applique la meme normalisation que normalize_market()"""
        normalized = alias.lower().strip()
        normalized = re.sub(r'_(\d)_(\d)', r'_\1\2', normalized)  # over_2_5 -> over_25
        normalized = re.sub(r'\.', '', normalized)  # over_2.5 -> over_25
        return normalized

    registry = {}
    for market_type, metadata in MARKET_REGISTRY.items():
        # Ajouter le canonical_name (deja normalise)
        registry[metadata.canonical_name] = market_type
        # Ajouter tous les aliases (normalises)
        for alias in metadata.aliases:
            normalized_alias = _normalize_alias(alias)
            registry[normalized_alias] = market_type
        # Ajouter la valeur enum elle-meme
        registry[market_type.value] = market_type
    return registry


ALIAS_REGISTRY: Dict[str, MarketType] = _build_alias_registry()


# ===============================================================================
#                              FONCTIONS UTILITAIRES
# ===============================================================================

def normalize_market(market_name: str) -> Optional[MarketType]:
    """
    Normalise n'importe quel nom de marche vers son MarketType canonical.

    Args:
        market_name: Nom du marche (any format: over_25, over_2_5, OVER25, etc.)

    Returns:
        MarketType correspondant ou None si non trouve

    Examples:
        >>> normalize_market("over_2_5")
        MarketType.OVER_25
        >>> normalize_market("btts")
        MarketType.BTTS_YES
        >>> normalize_market("both_teams_to_score")
        MarketType.BTTS_YES
    """
    import re

    # Normaliser: lowercase, remplacer tirets/espaces, puis digits
    normalized = market_name.lower().strip()
    normalized = re.sub(r'[-\s]+', '_', normalized)  # tirets/espaces -> underscores
    normalized = re.sub(r'_(\d)_(\d)', r'_\1\2', normalized)  # over_2_5 -> over_25
    normalized = re.sub(r'\.', '', normalized)  # over_2.5 -> over_25

    return ALIAS_REGISTRY.get(normalized)


def get_market_metadata(market: MarketType) -> Optional[MarketMetadata]:
    """
    Recupere les metadonnees completes d'un marche.

    Args:
        market: MarketType enum

    Returns:
        MarketMetadata ou None
    """
    return MARKET_REGISTRY.get(market)


def get_closing_config(market: MarketType) -> Optional[ClosingConfig]:
    """
    Recupere la configuration closing d'un marche.

    Args:
        market: MarketType enum

    Returns:
        ClosingConfig ou None
    """
    metadata = MARKET_REGISTRY.get(market)
    return metadata.closing_config if metadata else None


def get_markets_by_category(category: MarketCategory) -> List[MarketType]:
    """
    Recupere tous les marches d'une categorie.

    Args:
        category: MarketCategory enum

    Returns:
        Liste des MarketType de cette categorie
    """
    return [
        market_type
        for market_type, metadata in MARKET_REGISTRY.items()
        if metadata.category == category
    ]


def get_markets_by_closing_source(source: ClosingSource) -> List[MarketType]:
    """
    Recupere tous les marches utilisant une source de closing specifique.

    Args:
        source: ClosingSource enum

    Returns:
        Liste des MarketType avec cette source primaire
    """
    return [
        market_type
        for market_type, metadata in MARKET_REGISTRY.items()
        if metadata.closing_config and metadata.closing_config.primary_source == source
    ]


def get_liquidity_tax(market: MarketType) -> float:
    """
    Recupere la taxe de liquidite d'un marche.

    Args:
        market: MarketType enum

    Returns:
        Taxe de liquidite (0.01 a 0.10)
    """
    metadata = MARKET_REGISTRY.get(market)
    return metadata.liquidity_tax if metadata else 0.05


def get_min_edge(market: MarketType) -> float:
    """
    Recupere l'edge minimum requis pour un marche.

    Args:
        market: MarketType enum

    Returns:
        Edge minimum (0.02 a 0.15)
    """
    metadata = MARKET_REGISTRY.get(market)
    return metadata.min_edge if metadata else 0.05


def validate_registry() -> Dict[str, List[str]]:
    """
    Valide la coherence du registry.

    Returns:
        Dict avec 'errors' et 'warnings'
    """
    errors = []
    warnings = []

    for market_type, metadata in MARKET_REGISTRY.items():
        # Verifier que canonical_name correspond a la valeur enum
        if metadata.canonical_name != market_type.value:
            errors.append(
                f"{market_type}: canonical_name '{metadata.canonical_name}' "
                f"!= enum value '{market_type.value}'"
            )

        # Verifier closing_config existe
        if not metadata.closing_config:
            warnings.append(f"{market_type}: pas de closing_config defini")

        # Verifier dependencies existent dans le registry
        for dep in metadata.dependencies:
            if dep not in MARKET_REGISTRY:
                errors.append(f"{market_type}: dependency {dep} non trouvee dans registry")

        # Verifier quality_by_source a la source primaire
        if metadata.closing_config:
            config = metadata.closing_config
            if config.primary_source not in config.quality_by_source:
                warnings.append(
                    f"{market_type}: primary_source {config.primary_source} "
                    f"pas dans quality_by_source"
                )

    return {"errors": errors, "warnings": warnings}


# ===============================================================================
#                              EXPORT
# ===============================================================================

__all__ = [
    # Enums
    "MarketCategory",
    "MarketType",
    "ClosingSource",
    "LiquidityTier",
    "PayoffType",
    # Dataclasses
    "DNAFactorConfig",
    "ClosingConfig",
    "MarketMetadata",
    # Registry
    "MARKET_REGISTRY",
    "ALIAS_REGISTRY",
    # Functions
    "normalize_market",
    "get_market_metadata",
    "get_closing_config",
    "get_markets_by_category",
    "get_markets_by_closing_source",
    "get_liquidity_tax",
    "get_min_edge",
    "validate_registry",
]
