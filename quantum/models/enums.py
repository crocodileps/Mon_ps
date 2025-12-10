"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║  QUANTUM ENUMS - Classifications Strictes                                            ║
║  Version: 2.0                                                                        ║
║  "Pas de strings libres. Chaque valeur est contrôlée et documentée."                 ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

Architecture Mon_PS - Chess Engine V2.0
Créé le: 2025-12-10

Installation: /home/Mon_ps/quantum/models/enums.py

Pourquoi des Enums ?
- Typos impossibles (IDE autocomplete)
- Validation automatique par Pydantic
- Documentation intégrée
- Refactoring sécurisé
"""

from enum import Enum


# ═══════════════════════════════════════════════════════════════════════════════════════
# FORMATIONS TACTIQUES
# ═══════════════════════════════════════════════════════════════════════════════════════

class Formation(str, Enum):
    """
    Formations tactiques standardisées.
    Le format est défenseurs-milieux-attaquants.
    """
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # 4 DÉFENSEURS
    # ─────────────────────────────────────────────────────────────────────────────────
    F_4_4_2 = "4-4-2"
    F_4_4_2_DIAMOND = "4-4-2-diamond"
    F_4_3_3 = "4-3-3"
    F_4_2_3_1 = "4-2-3-1"
    F_4_1_4_1 = "4-1-4-1"
    F_4_5_1 = "4-5-1"
    F_4_3_2_1 = "4-3-2-1"          # Christmas tree
    F_4_4_1_1 = "4-4-1-1"
    F_4_1_2_1_2 = "4-1-2-1-2"      # Narrow diamond
    F_4_2_2_2 = "4-2-2-2"
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # 3 DÉFENSEURS
    # ─────────────────────────────────────────────────────────────────────────────────
    F_3_4_3 = "3-4-3"
    F_3_5_2 = "3-5-2"
    F_3_4_2_1 = "3-4-2-1"
    F_3_4_1_2 = "3-4-1-2"
    F_3_3_4 = "3-3-4"              # Ultra-offensif (rare)
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # 5 DÉFENSEURS (3 + 2 wingbacks)
    # ─────────────────────────────────────────────────────────────────────────────────
    F_5_3_2 = "5-3-2"
    F_5_4_1 = "5-4-1"
    F_5_2_3 = "5-2-3"
    F_5_2_2_1 = "5-2-2-1"
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # SPÉCIALES / RARES
    # ─────────────────────────────────────────────────────────────────────────────────
    F_3_2_4_1 = "3-2-4-1"          # Wingbacks hauts
    F_4_3_1_2 = "4-3-1-2"          # Narrow avec 10
    
    UNKNOWN = "unknown"


# ═══════════════════════════════════════════════════════════════════════════════════════
# PROFILS DÉFENSIFS
# ═══════════════════════════════════════════════════════════════════════════════════════

class DefenseProfile(str, Enum):
    """
    Profil défensif - Déduit automatiquement de xGA/90 et clean_sheet%.
    
    Seuils:
    - FORTRESS: xGA/90 < 0.9 AND CS% > 40%
    - SOLID: xGA/90 < 1.2 AND CS% > 30%
    - AVERAGE: xGA/90 1.2-1.5
    - LEAKY: xGA/90 1.5-2.0
    - CATASTROPHIC: xGA/90 > 2.0
    """
    FORTRESS = "fortress"           # Imprenable (ex: Chelsea 04-05)
    SOLID = "solid"                 # Fiable (ex: Arsenal 23-24)
    AVERAGE = "average"             # Dans la norme
    LEAKY = "leaky"                 # Problématique
    CATASTROPHIC = "catastrophic"   # Passoire (ex: Promoted teams)


class AttackProfile(str, Enum):
    """
    Profil offensif - Déduit automatiquement de xG/90 et conversion%.
    
    Seuils:
    - ELITE: xG/90 > 2.0
    - DANGEROUS: xG/90 1.5-2.0
    - AVERAGE: xG/90 1.0-1.5
    - TOOTHLESS: xG/90 0.7-1.0
    - IMPOTENT: xG/90 < 0.7
    """
    ELITE = "elite"                 # Machine à buts (ex: City)
    DANGEROUS = "dangerous"         # Menace constante
    AVERAGE = "average"             # Dans la norme
    TOOTHLESS = "toothless"         # Manque de finition
    IMPOTENT = "impotent"           # Incapable de marquer


# ═══════════════════════════════════════════════════════════════════════════════════════
# PROFILS DE MOMENTUM / FORME
# ═══════════════════════════════════════════════════════════════════════════════════════

class MomentumState(str, Enum):
    """
    État de forme actuel - Basé sur les 5 derniers matchs.
    
    Critères:
    - ON_FIRE: 4+ victoires consécutives
    - HOT: 3 victoires ou 4+ matchs sans défaite
    - STABLE: Forme normale (mix résultats)
    - COLD: 2+ défaites sur les 3 derniers
    - CRISIS: 4+ matchs sans victoire
    """
    ON_FIRE = "on_fire"       # Série victorieuse impressionnante
    HOT = "hot"               # En confiance
    STABLE = "stable"         # Forme normale
    COLD = "cold"             # En difficulté
    CRISIS = "crisis"         # Spirale négative


class FormTrend(str, Enum):
    """
    Tendance de forme - Comparaison L5 vs L10.
    """
    IMPROVING = "improving"         # L5 > L10 (en progression)
    STABLE = "stable"               # L5 ≈ L10
    DECLINING = "declining"         # L5 < L10 (en régression)


# ═══════════════════════════════════════════════════════════════════════════════════════
# PROFILS DE VARIANCE (CHANCE/MALCHANCE)
# ═══════════════════════════════════════════════════════════════════════════════════════

class VarianceProfile(str, Enum):
    """
    Profil chance/malchance - Déduit de (Points réels - xPts).
    
    CRUCIAL pour détecter la régression vers la moyenne:
    - Équipe "chanceuse" = regression DOWN probable
    - Équipe "malchanceuse" = regression UP probable = VALUE
    
    Seuils (sur une saison):
    - EXTREMELY_LUCKY: +8 pts ou plus
    - LUCKY: +4 à +8 pts
    - NEUTRAL: -4 à +4 pts
    - UNLUCKY: -4 à -8 pts
    - EXTREMELY_UNLUCKY: -8 pts ou moins
    """
    EXTREMELY_LUCKY = "extremely_lucky"     # Régression forte probable
    LUCKY = "lucky"                         # Surperformance légère
    NEUTRAL = "neutral"                     # Performance attendue
    UNLUCKY = "unlucky"                     # Sous-performance = VALUE
    EXTREMELY_UNLUCKY = "extremely_unlucky" # Grosse VALUE potentielle


# ═══════════════════════════════════════════════════════════════════════════════════════
# MATCHUP PROFILES (Confrontations tactiques)
# ═══════════════════════════════════════════════════════════════════════════════════════

class MatchupProfile(str, Enum):
    """
    Type de confrontation tactique - Déduit automatiquement des styles.
    
    Permet d'appliquer des filtres de marché instantanés:
    - ATTRITION_BATTLE → Under 2.5 automatique
    - CHAOS_GAME → Over 3.5 + BTTS Yes
    - PRESSING_WAR → Cards Over, BTTS probable
    """
    POSSESSION_VS_BUS = "possession_vs_bus"       # City vs Burnley (patience requise)
    PRESSING_WAR = "pressing_war"                 # Liverpool vs Arsenal (intense)
    TRANSITION_FEST = "transition_fest"           # Deux équipes verticales (open)
    ATTRITION_BATTLE = "attrition_battle"         # Deux blocs bas (under probable)
    CHESS_MATCH = "chess_match"                   # Deux tacticiens prudents
    CHAOS_GAME = "chaos_game"                     # Deux défenses fragiles (goals galore)
    DAVID_VS_GOLIATH = "david_vs_goliath"        # Grand écart de niveau
    MIRROR_MATCH = "mirror_match"                 # Styles identiques (imprévisible)
    COUNTER_VS_POSSESSION = "counter_vs_possession"  # Style opposé classique


# ═══════════════════════════════════════════════════════════════════════════════════════
# GAME STATE (État du score)
# ═══════════════════════════════════════════════════════════════════════════════════════

class GameState(str, Enum):
    """État du score pendant le match."""
    WINNING_BIG = "winning_big"     # +2 ou plus
    WINNING = "winning"             # +1
    DRAWING = "drawing"             # 0-0 ou X-X
    LOSING = "losing"               # -1
    LOSING_BIG = "losing_big"       # -2 ou moins


class GameStateReaction(str, Enum):
    """
    Réaction tactique d'un coach selon l'état du score.
    Crucial pour prédire les Late Goals et changements de dynamique.
    """
    ALL_OUT_ATTACK = "all_out_attack"       # Tous les risques, GK monte sur corners
    PUSH_FORWARD = "push_forward"           # Augmente la pression, plus de joueurs offensifs
    MAINTAIN = "maintain"                   # Garde le plan de jeu initial
    CONTROL = "control"                     # Gère le résultat, possession stérile
    PARK_THE_BUS = "park_the_bus"           # Défense totale, 10 derrière le ballon
    COUNTER_ATTACK_MODE = "counter_mode"    # Absorbe et contre (Mourinho special)


# ═══════════════════════════════════════════════════════════════════════════════════════
# TIMING SIGNATURES
# ═══════════════════════════════════════════════════════════════════════════════════════

class TimingSignature(str, Enum):
    """
    Signature temporelle d'une équipe.
    Déduit de la distribution des buts/xG par période.
    """
    DIESEL = "diesel"               # Monte en puissance, dangereux en fin de match
    EARLY_BIRD = "early_bird"       # Commence fort, s'essouffle
    CLUTCH = "clutch"               # Spécialiste des fins de match (76-90')
    FIRST_HALF_TEAM = "first_half"  # Dominance en 1ère mi-temps
    SECOND_HALF_TEAM = "second_half"# Dominance en 2ème mi-temps
    BALANCED = "balanced"           # Répartition uniforme


# ═══════════════════════════════════════════════════════════════════════════════════════
# MARCHÉS DE PARIS
# ═══════════════════════════════════════════════════════════════════════════════════════

class MarketType(str, Enum):
    """
    Types de marchés disponibles.
    Chaque équipe a des edges spécifiques sur certains marchés.
    """
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # GOALS TOTAUX
    # ─────────────────────────────────────────────────────────────────────────────────
    OVER_05 = "over_0.5"
    OVER_15 = "over_1.5"
    OVER_25 = "over_2.5"
    OVER_35 = "over_3.5"
    OVER_45 = "over_4.5"
    UNDER_05 = "under_0.5"
    UNDER_15 = "under_1.5"
    UNDER_25 = "under_2.5"
    UNDER_35 = "under_3.5"
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # BTTS (Both Teams To Score)
    # ─────────────────────────────────────────────────────────────────────────────────
    BTTS_YES = "btts_yes"
    BTTS_NO = "btts_no"
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # CLEAN SHEET
    # ─────────────────────────────────────────────────────────────────────────────────
    CLEAN_SHEET_HOME = "cs_home"
    CLEAN_SHEET_AWAY = "cs_away"
    NO_CLEAN_SHEET_HOME = "no_cs_home"
    NO_CLEAN_SHEET_AWAY = "no_cs_away"
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # TEAM GOALS
    # ─────────────────────────────────────────────────────────────────────────────────
    HOME_OVER_05 = "home_over_0.5"
    HOME_OVER_15 = "home_over_1.5"
    HOME_OVER_25 = "home_over_2.5"
    AWAY_OVER_05 = "away_over_0.5"
    AWAY_OVER_15 = "away_over_1.5"
    AWAY_OVER_25 = "away_over_2.5"
    HOME_UNDER_05 = "home_under_0.5"   # Home clean sheet pour away
    AWAY_UNDER_05 = "away_under_0.5"   # Away clean sheet pour home
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # HALF GOALS
    # ─────────────────────────────────────────────────────────────────────────────────
    FIRST_HALF_OVER_05 = "1h_over_0.5"
    FIRST_HALF_OVER_15 = "1h_over_1.5"
    FIRST_HALF_UNDER_05 = "1h_under_0.5"
    SECOND_HALF_OVER_05 = "2h_over_0.5"
    SECOND_HALF_OVER_15 = "2h_over_1.5"
    SECOND_HALF_OVER_25 = "2h_over_2.5"
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # TIMING GOALS
    # ─────────────────────────────────────────────────────────────────────────────────
    GOAL_0_15 = "goal_0_15"
    GOAL_76_90 = "goal_76_90"
    NO_GOAL_0_15 = "no_goal_0_15"
    GOAL_BOTH_HALVES = "goal_both_halves"
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # CORNERS
    # ─────────────────────────────────────────────────────────────────────────────────
    CORNERS_OVER_75 = "corners_over_7.5"
    CORNERS_OVER_85 = "corners_over_8.5"
    CORNERS_OVER_95 = "corners_over_9.5"
    CORNERS_OVER_105 = "corners_over_10.5"
    CORNERS_OVER_115 = "corners_over_11.5"
    CORNERS_OVER_125 = "corners_over_12.5"
    CORNERS_UNDER_95 = "corners_under_9.5"
    CORNERS_UNDER_105 = "corners_under_10.5"
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # CARDS
    # ─────────────────────────────────────────────────────────────────────────────────
    CARDS_OVER_25 = "cards_over_2.5"
    CARDS_OVER_35 = "cards_over_3.5"
    CARDS_OVER_45 = "cards_over_4.5"
    CARDS_OVER_55 = "cards_over_5.5"
    CARDS_UNDER_35 = "cards_under_3.5"
    CARDS_UNDER_45 = "cards_under_4.5"
    
    # ─────────────────────────────────────────────────────────────────────────────────
    # SPECIALS
    # ─────────────────────────────────────────────────────────────────────────────────
    PENALTY_YES = "penalty_yes"
    RED_CARD_YES = "red_card_yes"


class MarketCategory(str, Enum):
    """Catégorie de marché pour regroupement."""
    GOALS = "goals"
    BTTS = "btts"
    CLEAN_SHEET = "clean_sheet"
    TEAM_GOALS = "team_goals"
    HALF_GOALS = "half_goals"
    TIMING = "timing"
    CORNERS = "corners"
    CARDS = "cards"
    SPECIALS = "specials"


# ═══════════════════════════════════════════════════════════════════════════════════════
# STAKE / DÉCISION
# ═══════════════════════════════════════════════════════════════════════════════════════

class StakeSize(str, Enum):
    """
    Taille de mise selon la confiance et l'edge.
    Basé sur Kelly Criterion ajusté.
    """
    SKIP = "skip"           # Edge < 3% ou confiance < 40%
    SMALL = "small"         # 0.5-1% bankroll (edge 3-5%)
    MEDIUM = "medium"       # 1-2% bankroll (edge 5-8%)
    LARGE = "large"         # 2-3% bankroll (edge 8-12%)
    MAX = "max"             # 3-5% bankroll (edge > 12%, rare)


class DecisionConfidence(str, Enum):
    """Niveau de confiance dans la décision."""
    VERY_HIGH = "very_high"     # > 80% confidence
    HIGH = "high"               # 65-80%
    MEDIUM = "medium"           # 50-65%
    LOW = "low"                 # 35-50%
    VERY_LOW = "very_low"       # < 35%


# ═══════════════════════════════════════════════════════════════════════════════════════
# POSITIONS JOUEURS
# ═══════════════════════════════════════════════════════════════════════════════════════

class Position(str, Enum):
    """Positions des joueurs sur le terrain."""
    GK = "goalkeeper"
    CB = "center_back"
    LB = "left_back"
    RB = "right_back"
    LWB = "left_wingback"
    RWB = "right_wingback"
    DM = "defensive_mid"
    CM = "central_mid"
    AM = "attacking_mid"
    LM = "left_mid"
    RM = "right_mid"
    LW = "left_wing"
    RW = "right_wing"
    CF = "center_forward"
    ST = "striker"
    
    UNKNOWN = "unknown"


class PositionCategory(str, Enum):
    """Catégorie de position simplifiée."""
    GOALKEEPER = "goalkeeper"
    DEFENDER = "defender"
    MIDFIELDER = "midfielder"
    FORWARD = "forward"


# ═══════════════════════════════════════════════════════════════════════════════════════
# ARBITRE
# ═══════════════════════════════════════════════════════════════════════════════════════

class RefereeStrictness(str, Enum):
    """
    Niveau de sévérité de l'arbitre.
    Basé sur cartons par match.
    """
    PERMISSIVE = "permissive"   # < 3.0 cartons/match (laisse jouer)
    LENIENT = "lenient"         # 3.0-3.5 cartons/match
    MODERATE = "moderate"       # 3.5-4.5 cartons/match
    STRICT = "strict"           # 4.5-5.5 cartons/match
    CARD_HAPPY = "card_happy"   # > 5.5 cartons/match (Anthony Taylor)


class RefereeStyle(str, Enum):
    """Style d'arbitrage."""
    ADVANTAGE_PLAYER = "advantage_player"   # Laisse jouer, peu de sifflets
    BY_THE_BOOK = "by_the_book"             # Strict sur les règles
    HOME_BIAS = "home_bias"                 # Favorise légèrement le domicile
    VAR_LOVER = "var_lover"                 # Utilise beaucoup la VAR
    QUICK_WHISTLE = "quick_whistle"         # Siffle beaucoup de fautes


# ═══════════════════════════════════════════════════════════════════════════════════════
# LEAGUES
# ═══════════════════════════════════════════════════════════════════════════════════════

class League(str, Enum):
    """Ligues supportées."""
    PREMIER_LEAGUE = "premier_league"
    LA_LIGA = "la_liga"
    BUNDESLIGA = "bundesliga"
    SERIE_A = "serie_a"
    LIGUE_1 = "ligue_1"
    
    # Optionnelles pour expansion future
    EREDIVISIE = "eredivisie"
    LIGA_PORTUGAL = "liga_portugal"
    CHAMPIONSHIP = "championship"


class LeagueTier(str, Enum):
    """Niveau de la ligue."""
    TOP_5 = "top_5"             # Big 5 leagues européennes
    TIER_2 = "tier_2"           # Eredivisie, Portugal, etc.
    TIER_3 = "tier_3"           # Championships, 2nde division
    LOWER = "lower"             # Ligues inférieures


# ═══════════════════════════════════════════════════════════════════════════════════════
# PERCEPTION PUBLIQUE (Pour Contrarian Edge)
# ═══════════════════════════════════════════════════════════════════════════════════════

class PublicPerceptionBias(str, Enum):
    """
    Biais de perception du public sur un coach/équipe.
    
    CRUCIAL pour identifier la VALUE:
    - OVERRATED: Le public surestime (cotes écrasées) → Éviter ou Fade
    - UNDERRATED: Le public sous-estime (value cachée) → Chercher les spots
    """
    HEAVILY_OVERRATED = "heavily_overrated"   # Guardiola, Klopp (cotes très basses)
    OVERRATED = "overrated"                   # Top coaches établis
    NEUTRAL = "neutral"                       # Perception juste
    UNDERRATED = "underrated"                 # Coaches efficaces mais ignorés
    HEAVILY_UNDERRATED = "heavily_underrated" # Moyes, Dyche (value max)


# ═══════════════════════════════════════════════════════════════════════════════════════
# STRUCTURE TACTIQUE (Chaos vs Rigidité)
# ═══════════════════════════════════════════════════════════════════════════════════════

class StructureType(str, Enum):
    """
    Type de structure tactique.
    
    0 = FLUID (Chaos organisé, positions interchangeables)
    100 = RIGID (Structure fixe, rôles définis)
    """
    ULTRA_FLUID = "ultra_fluid"       # 0-20: Bielsa, Gasperini, Diniz
    FLUID = "fluid"                   # 20-40: Klopp, Nagelsmann
    BALANCED = "balanced"             # 40-60: Arteta, Slot
    STRUCTURED = "structured"         # 60-80: Mourinho, Ancelotti
    RIGID = "rigid"                   # 80-100: Conte, Simeone, Dyche


# ═══════════════════════════════════════════════════════════════════════════════════════
# DATA QUALITY
# ═══════════════════════════════════════════════════════════════════════════════════════

class DataQuality(str, Enum):
    """Qualité des données disponibles."""
    EXCELLENT = "excellent"     # > 90% completeness, > 30 matchs
    GOOD = "good"               # 75-90%, 20-30 matchs
    MODERATE = "moderate"       # 50-75%, 10-20 matchs
    POOR = "poor"               # 25-50%, 5-10 matchs
    INSUFFICIENT = "insufficient"# < 25%, < 5 matchs
