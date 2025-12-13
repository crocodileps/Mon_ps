#!/usr/bin/env python3
"""
DNA NARRATIVE GENERATOR V1.0 - HEDGE FUND GRADE
"L'empreinte digitale unique de chaque équipe"

PHILOSOPHIE MON_PS:
1. LES DONNEES dictent le profil, pas la reputation
2. Chaque equipe = 1 ADN = 1 empreinte digitale UNIQUE
3. Marches = CONSEQUENCES de l'ADN, pas l'inverse
4. Approche TEAM-CENTRIC: Pour CETTE equipe, quels marches exploitables?

Auteur: Mon_PS Quant Team
Date: 12 Decembre 2025
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import statistics

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ═══════════════════════════════════════════════════════════════════
# CONSTANTS & THRESHOLDS
# ═══════════════════════════════════════════════════════════════════

# Seuils bases sur distributions reelles (Q10, Q50, Q90)
AXIS_THRESHOLDS = {
    # OFFENSIVE
    "pressing_intensity": {"low": 40, "mid": 55, "high": 70},
    "possession_control": {"low": 45, "mid": 50, "high": 58},
    "verticality": {"low": 35, "mid": 50, "high": 65},
    "wide_play": {"low": 15, "mid": 22, "high": 30},
    "set_piece_threat": {"low": 20, "mid": 35, "high": 50},
    "clinical_finishing": {"low": 85, "mid": 100, "high": 115},

    # DEFENSIVE
    "block_depth": {"low": 30, "mid": 42, "high": 55},
    "defensive_compactness": {"low": 40, "mid": 55, "high": 70},
    "aerial_resistance": {"low": 45, "mid": 52, "high": 60},
    "transition_defense": {"low": 35, "mid": 50, "high": 65},
    "goalkeeper_reliability": {"low": 90, "mid": 100, "high": 110},

    # TEMPORAL
    "diesel_factor": {"low": 0.8, "mid": 1.0, "high": 1.3},
    "first_half_intensity": {"low": 0.4, "mid": 0.5, "high": 0.6},
    "clutch_factor": {"low": 0.15, "mid": 0.22, "high": 0.30},

    # CONTEXTUAL
    "home_dominance": {"low": 1.2, "mid": 1.6, "high": 2.2},
}

# Mapping axes -> markets
AXIS_TO_MARKETS = {
    "pressing_intensity": {
        "high": [
            {"market": "Cards Over 3.5", "direction": "FOR", "edge": 4.0},
            {"market": "BTTS Yes", "direction": "FOR", "edge": 3.5},
            {"market": "Over 2.5", "direction": "FOR", "edge": 3.0},
        ],
        "low": [
            {"market": "Under 2.5", "direction": "FOR", "edge": 3.0},
            {"market": "Cards Under 2.5", "direction": "FOR", "edge": 2.5},
        ]
    },
    "possession_control": {
        "high": [
            {"market": "Corners Over 9.5", "direction": "FOR", "edge": 4.0},
            {"market": "Team Win", "direction": "FOR", "edge": 3.0},
        ],
        "low": [
            {"market": "Counter Goals", "direction": "AGAINST", "edge": 3.5},
        ]
    },
    "diesel_factor": {
        "high": [
            {"market": "2H Over 1.5", "direction": "FOR", "edge": 5.0},
            {"market": "Goal 75-90", "direction": "FOR", "edge": 4.5},
            {"market": "Late Winner", "direction": "FOR", "edge": 4.0},
        ],
        "low": [
            {"market": "1H Over 0.5", "direction": "FOR", "edge": 3.0},
            {"market": "HT Result", "direction": "FOR", "edge": 2.5},
        ]
    },
    "first_half_intensity": {
        "high": [
            {"market": "1H Over 1.5", "direction": "FOR", "edge": 4.0},
            {"market": "First Goal 0-30", "direction": "FOR", "edge": 3.5},
        ],
        "low": [
            {"market": "0-0 HT", "direction": "FOR", "edge": 3.0},
        ]
    },
    "clutch_factor": {
        "high": [
            {"market": "Late Goal", "direction": "FOR", "edge": 5.0},
            {"market": "Goal 75+", "direction": "FOR", "edge": 4.5},
        ],
        "low": []
    },
    "block_depth": {
        "high": [
            {"market": "Under 2.5", "direction": "FOR", "edge": 3.5},
            {"market": "Clean Sheet", "direction": "FOR", "edge": 3.0},
        ],
        "low": [
            {"market": "Counter Goals", "direction": "AGAINST", "edge": 4.0},
            {"market": "Fast Transitions", "direction": "AGAINST", "edge": 3.5},
        ]
    },
    "aerial_resistance": {
        "high": [
            {"market": "Set Piece Defense", "direction": "FOR", "edge": 3.0},
        ],
        "low": [
            {"market": "Header Goal", "direction": "AGAINST", "edge": 4.5},
            {"market": "Corner Goals", "direction": "AGAINST", "edge": 4.0},
            {"market": "Set Piece Goals", "direction": "AGAINST", "edge": 3.5},
        ]
    },
    "wide_play": {
        "high": [
            {"market": "Corners Over 10.5", "direction": "FOR", "edge": 4.0},
            {"market": "Cross Assists", "direction": "FOR", "edge": 3.5},
        ],
        "low": []
    },
    "set_piece_threat": {
        "high": [
            {"market": "Set Piece Goal", "direction": "FOR", "edge": 4.5},
            {"market": "Header Goal", "direction": "FOR", "edge": 4.0},
        ],
        "low": []
    },
    "clinical_finishing": {
        "high": [
            {"market": "Team Goals Over 1.5", "direction": "FOR", "edge": 4.0},
            {"market": "Anytime Scorer", "direction": "FOR", "edge": 3.5},
        ],
        "low": [
            {"market": "Team Goals Under 0.5", "direction": "FOR", "edge": 3.0},
        ]
    },
    "home_dominance": {
        "high": [
            {"market": "Home Win", "direction": "FOR", "edge": 4.0},
            {"market": "Home Goals Over 1.5", "direction": "FOR", "edge": 3.5},
        ],
        "low": [
            {"market": "Away Points", "direction": "AGAINST", "edge": 3.0},
        ]
    },
    "goalkeeper_reliability": {
        "high": [
            {"market": "Clean Sheet", "direction": "FOR", "edge": 3.5},
            {"market": "Under 2.5", "direction": "FOR", "edge": 3.0},
        ],
        "low": [
            {"market": "Over 2.5", "direction": "AGAINST", "edge": 3.5},
            {"market": "BTTS Yes", "direction": "AGAINST", "edge": 3.0},
        ]
    },
    "defensive_compactness": {
        "high": [
            {"market": "Under 2.5", "direction": "FOR", "edge": 3.0},
        ],
        "low": [
            {"market": "Over 2.5", "direction": "AGAINST", "edge": 3.5},
        ]
    },
    "transition_defense": {
        "high": [],
        "low": [
            {"market": "Counter Goals", "direction": "AGAINST", "edge": 4.0},
        ]
    },
    "verticality": {
        "high": [
            {"market": "Fast Game", "direction": "FOR", "edge": 3.0},
            {"market": "Counter Attack Goals", "direction": "FOR", "edge": 3.5},
        ],
        "low": [
            {"market": "Slow Build-up", "direction": "FOR", "edge": 2.5},
        ]
    },
}

# Identity templates
IDENTITY_TEMPLATES = {
    "pressing_diesel": "{team} est une machine de pressing tardif - intensite maximale qui s'amplifie en 2H",
    "possession_dominant": "{team} etouffe par la possession - patience et controle du tempo",
    "counter_specialist": "{team} vit dans les transitions - bloc bas puis acceleration foudroyante",
    "aerial_powerhouse": "{team} domine dans les airs - danger constant sur coups de pied arretes",
    "clinical_assassin": "{team} est clinique - peu d'occasions mais efficacite redoutable",
    "defensive_fortress": "{team} est une forteresse defensive - compact et discipline",
    "early_starter": "{team} demarre fort - pression immediate et buts rapides",
    "late_surge": "{team} finit en force - danger maximal apres 75'",
    "home_beast": "{team} est imbattable a domicile - transformation complete",
    "balanced_chameleon": "{team} s'adapte au contexte - profil equilibre sans faiblesse majeure",
}


@dataclass
class AxisScore:
    """Score d'un axe avec metadata."""
    name: str
    score: float  # 0-100
    raw_value: float
    percentile: str  # "LOW", "MID", "HIGH", "EXTREME"
    description: str


@dataclass
class Force:
    """Une force distinctive de l'equipe."""
    trait: str
    score: float
    description: str
    markets: List[Dict]


@dataclass
class Faiblesse:
    """Une faiblesse exploitable."""
    trait: str
    score: float
    description: str
    exploitation: List[Dict]


@dataclass
class DNAProfile:
    """Profil DNA complet d'une equipe."""
    team: str
    league: str
    generated_at: str

    # Core
    identity: str
    axes: Dict[str, AxisScore]

    # Analysis
    forces: List[Force]
    faiblesses: List[Faiblesse]

    # Markets
    markets_for: List[Dict]
    markets_against: List[Dict]

    # Narrative
    narrative: str
    summary: str


class DNANarrativeGenerator:
    """
    Generateur de profils narratifs DNA.

    Transforme les donnees brutes en profils uniques avec:
    - 15 axes continus (0-100)
    - Forces et faiblesses distinctives
    - Marches exploitables FOR et AGAINST
    - Narrative unique style Quant
    """

    def __init__(self, data_path: str = None):
        """Initialize avec le chemin vers team_dna_unified."""
        if data_path is None:
            possible_paths = [
                Path("data/quantum_v2/team_dna_unified_v2.json"),
                Path("/home/Mon_ps/data/quantum_v2/team_dna_unified_v2.json"),
            ]
            for p in possible_paths:
                if p.exists():
                    data_path = str(p)
                    break

        self.data_path = data_path
        self.data = self._load_data()
        self.teams = self.data.get("teams", {})

        # Calculate league averages for percentile scoring
        self._calculate_league_averages()

    def _load_data(self) -> dict:
        """Charge les donnees DNA unifiees."""
        with open(self.data_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _calculate_league_averages(self):
        """Calcule les moyennes par ligue pour le scoring."""
        self.league_stats = {}

        metrics_to_track = [
            "possession_pct", "aerial_win_pct", "pressing_intensity"
        ]

        for team_name, team_data in self.teams.items():
            league = team_data.get('context', {}).get('league') or \
                     team_data.get('tactical', {}).get('league') or 'Unknown'

            if league not in self.league_stats:
                self.league_stats[league] = {m: [] for m in metrics_to_track}

            tactical = team_data.get('tactical', {})
            for metric in metrics_to_track:
                val = tactical.get(metric)
                if val is not None:
                    try:
                        self.league_stats[league][metric].append(float(val))
                    except (ValueError, TypeError):
                        pass

    def _safe_float(self, value, default: float = 0.0) -> float:
        """Convertit en float de maniere securisee."""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def _normalize_to_100(self, value: float, low: float, high: float) -> float:
        """Normalise une valeur sur une echelle 0-100."""
        if high == low:
            return 50.0
        normalized = (value - low) / (high - low) * 100
        return max(0, min(100, normalized))

    def _get_percentile(self, score: float) -> str:
        """Determine le percentile basee sur le score 0-100."""
        if score >= 80:
            return "EXTREME_HIGH"
        elif score >= 65:
            return "HIGH"
        elif score >= 35:
            return "MID"
        elif score >= 20:
            return "LOW"
        else:
            return "EXTREME_LOW"

    def _calculate_axes(self, team_data: dict) -> Dict[str, AxisScore]:
        """Calcule les 15 axes continus depuis les donnees brutes."""
        axes = {}

        tactical = team_data.get('tactical', {})
        defense = team_data.get('defense', {})
        fbref = team_data.get('fbref', {})
        betting = team_data.get('betting', {})
        def_line = team_data.get('defensive_line', {})
        context = team_data.get('context', {})
        history = context.get('history', {})
        defense_percentiles = defense.get('percentiles', {})

        # ═══════════════════════════════════════════════════════════════
        # OFFENSIVE AXES (6)
        # ═══════════════════════════════════════════════════════════════

        # 1. PRESSING_INTENSITY
        # Source: context.history.ppda (lower = more aggressive pressing)
        # Also check tactical.pressing_intensity for textual value
        ppda = self._safe_float(history.get('ppda'), 0)
        pressing_style = history.get('pressing_style', tactical.get('pressing_intensity', ''))

        if ppda > 0:
            # PPDA: 6-8 = HIGH press, 10-12 = MID, 14+ = LOW
            # Invert: lower PPDA = higher pressing intensity
            pressing_score = self._normalize_to_100(ppda, 16, 6)  # Inverted!
        elif isinstance(pressing_style, str):
            pressing_map = {"HIGH_PRESS": 80, "HIGH": 75, "MEDIUM": 50, "MID": 50, "LOW": 25}
            pressing_score = pressing_map.get(pressing_style.upper(), 50)
        else:
            pressing_score = 50

        axes["pressing_intensity"] = AxisScore(
            name="pressing_intensity",
            score=pressing_score,
            raw_value=ppda if ppda > 0 else pressing_score,
            percentile=self._get_percentile(pressing_score),
            description="Intensite du pressing et recuperation haute"
        )

        # 2. POSSESSION_CONTROL
        poss_raw = self._safe_float(tactical.get('possession_pct') or fbref.get('possession'), 50)
        poss_score = self._normalize_to_100(poss_raw, 35, 70)
        axes["possession_control"] = AxisScore(
            name="possession_control",
            score=poss_score,
            raw_value=poss_raw,
            percentile=self._get_percentile(poss_score),
            description="Controle de la possession et patience"
        )

        # 3. VERTICALITY
        # Source: tactical.progressive_passes or attacking speed profile
        prog_passes = self._safe_float(tactical.get('progressive_passes'), 0)
        attack_speed = context.get('context_dna', {}).get('attackSpeed', {})
        fast_pct = self._safe_float(attack_speed.get('Fast', 0), 0)

        if prog_passes > 0:
            # Progressive passes: 400-500 = low, 600-700 = mid, 800+ = high
            vert_score = self._normalize_to_100(prog_passes, 400, 900)
        elif fast_pct > 0:
            vert_score = self._normalize_to_100(fast_pct, 10, 40)
        else:
            # Fallback to defensive style
            def_style = tactical.get('defensive_style', '')
            vert_map = {"HIGH_BLOCK": 70, "MID_BLOCK": 50, "DEEP_BLOCK": 30}
            vert_score = vert_map.get(str(def_style).upper(), 50)

        axes["verticality"] = AxisScore(
            name="verticality",
            score=vert_score,
            raw_value=prog_passes if prog_passes > 0 else vert_score,
            percentile=self._get_percentile(vert_score),
            description="Jeu vertical et passes progressives"
        )

        # 4. WIDE_PLAY
        # Source: fbref.passes_penalty_area ou crosses
        passes_pa = self._safe_float(fbref.get('passes_penalty_area'), 0)
        touches_att = self._safe_float(fbref.get('touches_att_3rd'), 0)

        if passes_pa > 0 and touches_att > 0:
            # Ratio passes in penalty area / touches attacking third
            wide_ratio = passes_pa / touches_att * 100 if touches_att > 0 else 5
            wide_score = self._normalize_to_100(wide_ratio, 3, 10)
        else:
            wide_score = 50  # Default

        axes["wide_play"] = AxisScore(
            name="wide_play",
            score=wide_score,
            raw_value=passes_pa,
            percentile=self._get_percentile(wide_score),
            description="Jeu sur les ailes et centres"
        )

        # 5. SET_PIECE_THREAT
        aerial_raw = self._safe_float(tactical.get('aerial_win_pct'), 50)
        sp_score = self._normalize_to_100(aerial_raw, 40, 65)
        axes["set_piece_threat"] = AxisScore(
            name="set_piece_threat",
            score=sp_score,
            raw_value=aerial_raw,
            percentile=self._get_percentile(sp_score),
            description="Danger sur coups de pied arretes"
        )

        # 6. CLINICAL_FINISHING
        # Source: fbref goals/xg or context.history xg data
        # Goals / xG ratio - above 100 = clinical, below 100 = wasteful
        xg_total = self._safe_float(history.get('xg') or fbref.get('xg'), 0)
        goals_total = self._safe_float(fbref.get('goals') or context.get('record', {}).get('goals_for'), 0)

        if xg_total > 0 and goals_total > 0:
            clinical_raw = (goals_total / xg_total) * 100
            clinical_score = self._normalize_to_100(clinical_raw, 70, 130)
        else:
            # Fallback: use variance data
            xg_overperf = self._safe_float(context.get('variance', {}).get('xg_overperformance'), 0)
            # xg_overperformance: negative = underperforming, positive = overperforming
            clinical_score = self._normalize_to_100(xg_overperf, -5, 5)
            clinical_raw = xg_overperf

        axes["clinical_finishing"] = AxisScore(
            name="clinical_finishing",
            score=clinical_score,
            raw_value=clinical_raw,
            percentile=self._get_percentile(clinical_score),
            description="Efficacite devant le but (goals/xG)"
        )

        # ═══════════════════════════════════════════════════════════════
        # DEFENSIVE AXES (5)
        # ═══════════════════════════════════════════════════════════════

        # 7. BLOCK_DEPTH
        def_line_height = 45  # Default mid-block
        def_style = tactical.get('defensive_style', '')
        if 'DEEP' in str(def_style).upper():
            def_line_height = 30
        elif 'HIGH' in str(def_style).upper():
            def_line_height = 60
        block_score = self._normalize_to_100(def_line_height, 20, 65)
        axes["block_depth"] = AxisScore(
            name="block_depth",
            score=block_score,
            raw_value=def_line_height,
            percentile=self._get_percentile(block_score),
            description="Hauteur du bloc defensif (bas=30, haut=60)"
        )

        # 8. DEFENSIVE_COMPACTNESS
        tackle_def = self._safe_float(tactical.get('tackle_def_pct'), 40)
        compact_score = self._normalize_to_100(tackle_def, 25, 60)
        axes["defensive_compactness"] = AxisScore(
            name="defensive_compactness",
            score=compact_score,
            raw_value=tackle_def,
            percentile=self._get_percentile(compact_score),
            description="Compacite et tacles defensifs"
        )

        # 9. AERIAL_RESISTANCE
        aerial_def = self._safe_float(tactical.get('aerial_win_pct'), 50)
        aerial_score = self._normalize_to_100(aerial_def, 40, 65)
        axes["aerial_resistance"] = AxisScore(
            name="aerial_resistance",
            score=aerial_score,
            raw_value=aerial_def,
            percentile=self._get_percentile(aerial_score),
            description="Resistance aerienne defensive"
        )

        # 10. TRANSITION_DEFENSE
        # Source: defense.percentiles.open_play (higher = better defense vs open play)
        open_play_resist = self._safe_float(defense_percentiles.get('open_play'), 50)
        # Also consider pressing score - high press = better transition defense
        if pressing_score > 70:
            trans_score = min(100, open_play_resist + 15)
        elif pressing_score < 30:
            trans_score = max(0, open_play_resist - 15)
        else:
            trans_score = open_play_resist

        axes["transition_defense"] = AxisScore(
            name="transition_defense",
            score=trans_score,
            raw_value=open_play_resist,
            percentile=self._get_percentile(trans_score),
            description="Defense en transition et contre-pressing"
        )

        # 11. GOALKEEPER_RELIABILITY
        # Source: defensive_line.goalkeeper.gk_percentile ou defense overperformance
        gk_data = def_line.get('goalkeeper', {})
        gk_percentile = self._safe_float(gk_data.get('gk_percentile'), 0)
        gk_overperform = self._safe_float(gk_data.get('gk_overperform'), 0)

        if gk_percentile > 0:
            # gk_percentile is already 0-100
            gk_score = gk_percentile
        elif gk_overperform != 0:
            # gk_overperform: negative = underperforming, positive = overperforming
            # Map -20 to +20 range to 0-100
            gk_score = self._normalize_to_100(gk_overperform, -20, 20)
        else:
            # Fallback: use xGA/GA ratio
            xga = self._safe_float(defense.get('xga_total'), 1)
            ga = self._safe_float(defense.get('ga_total'), 1)
            gk_raw = (xga / ga * 100) if ga > 0 else 100
            gk_score = self._normalize_to_100(gk_raw, 80, 120)

        axes["goalkeeper_reliability"] = AxisScore(
            name="goalkeeper_reliability",
            score=gk_score,
            raw_value=gk_percentile if gk_percentile > 0 else gk_overperform,
            percentile=self._get_percentile(gk_score),
            description="Fiabilite du gardien"
        )

        # ═══════════════════════════════════════════════════════════════
        # TEMPORAL AXES (3)
        # ═══════════════════════════════════════════════════════════════

        # 12. DIESEL_FACTOR (2H vs 1H goals)
        # Source: defense.percentiles.late_prop (how well they defend late = inverse)
        # OR defensive_line.temporal.timing_profile
        late_prop = self._safe_float(defense_percentiles.get('late_prop', defense_percentiles.get('late')), 50)
        timing_profile = def_line.get('temporal', {}).get('timing_profile', '')

        # late_prop is DEFENSIVE (resist late goals), we want OFFENSIVE diesel
        # High late_prop = hard to score late against = they defend well late
        # For diesel (offensive), we need context.history or goals scored patterns
        xga_late_pct = self._safe_float(defense.get('xga_late_pct'), 0)

        if xga_late_pct > 0:
            # Use xGA late percentage - higher = they concede more late = they're vulnerable
            # But we want diesel = scoring late, not conceding
            diesel_score = 100 - xga_late_pct  # Invert: if they concede late, they might also score late
        elif 'STRONG_FINISH' in str(timing_profile).upper():
            diesel_score = 75
        elif 'FADES' in str(timing_profile).upper():
            diesel_score = 30
        else:
            diesel_score = late_prop

        axes["diesel_factor"] = AxisScore(
            name="diesel_factor",
            score=diesel_score,
            raw_value=late_prop,
            percentile=self._get_percentile(diesel_score),
            description="Ratio buts 2H/1H (diesel = fort en 2H)"
        )

        # 13. FIRST_HALF_INTENSITY
        # Source: defense.percentiles.early_prop or early
        early_prop = self._safe_float(defense_percentiles.get('early_prop', defense_percentiles.get('early')), 50)
        xga_early_pct = self._safe_float(defense.get('xga_early_pct'), 0)

        if xga_early_pct > 0:
            # xga_early_pct: how much of their xGA is in first 15 min
            fh_score = self._normalize_to_100(xga_early_pct, 10, 30)
        else:
            # early_prop is defensive (resist early goals)
            # Low early_prop = vulnerable early = opponents score early against them
            fh_score = 100 - early_prop  # Invert for offensive meaning

        axes["first_half_intensity"] = AxisScore(
            name="first_half_intensity",
            score=fh_score,
            raw_value=early_prop,
            percentile=self._get_percentile(fh_score),
            description="Part des buts en 1H"
        )

        # 14. CLUTCH_FACTOR (75-90 goals)
        # Source: defense.percentiles.late_prop or gamestate_behavior
        gamestate_behavior = tactical.get('gamestate_behavior', '')
        late_pct = self._safe_float(defense_percentiles.get('late_prop', defense_percentiles.get('late')), 50)

        if 'COMEBACK' in str(gamestate_behavior).upper():
            clutch_score = 75
        elif 'COLLAPSES' in str(gamestate_behavior).upper():
            clutch_score = 30
        else:
            # Use late_prop - high = hard to score late against = they're clutch defensively
            # But for offensive clutch, we want something else
            clutch_score = late_pct

        axes["clutch_factor"] = AxisScore(
            name="clutch_factor",
            score=clutch_score,
            raw_value=late_pct,
            percentile=self._get_percentile(clutch_score),
            description="Capacite a marquer apres 75'"
        )

        # ═══════════════════════════════════════════════════════════════
        # CONTEXTUAL AXES (1)
        # ═══════════════════════════════════════════════════════════════

        # 15. HOME_DOMINANCE
        # Source: defense.percentiles.home vs away
        home_resist = self._safe_float(defense_percentiles.get('home'), 50)
        away_resist = self._safe_float(defense_percentiles.get('away'), 50)

        # home_resist = how well they defend at home (higher = better)
        # For home dominance, compare home vs away performance
        if home_resist > 0 and away_resist > 0:
            # Ratio of home resistance to away resistance
            home_ratio = home_resist / away_resist if away_resist > 0 else 1.5
            home_score = self._normalize_to_100(home_ratio, 0.7, 2.0)
        else:
            # Fallback to simple home percentile
            home_score = home_resist

        axes["home_dominance"] = AxisScore(
            name="home_dominance",
            score=home_score,
            raw_value=home_resist,
            percentile=self._get_percentile(home_score),
            description="Dominance a domicile vs exterieur"
        )

        return axes

    def _extract_forces(self, axes: Dict[str, AxisScore]) -> List[Force]:
        """Identifie les forces distinctives (axes > 65)."""
        forces = []

        for name, axis in axes.items():
            if axis.score >= 65:
                markets = AXIS_TO_MARKETS.get(name, {}).get("high", [])
                forces.append(Force(
                    trait=name,
                    score=axis.score,
                    description=f"{axis.description} - Score: {axis.score:.0f}/100",
                    markets=markets
                ))

        # Sort by score descending
        forces.sort(key=lambda x: x.score, reverse=True)
        return forces[:5]  # Top 5 forces

    def _extract_faiblesses(self, axes: Dict[str, AxisScore]) -> List[Faiblesse]:
        """Identifie les faiblesses exploitables (axes < 35)."""
        faiblesses = []

        for name, axis in axes.items():
            if axis.score <= 35:
                exploitation = AXIS_TO_MARKETS.get(name, {}).get("low", [])
                faiblesses.append(Faiblesse(
                    trait=name,
                    score=axis.score,
                    description=f"{axis.description} - Score: {axis.score:.0f}/100",
                    exploitation=exploitation
                ))

        # Sort by score ascending (lowest = biggest weakness)
        faiblesses.sort(key=lambda x: x.score)
        return faiblesses[:5]  # Top 5 weaknesses

    def _derive_identity(self, team: str, axes: Dict[str, AxisScore],
                        forces: List[Force], faiblesses: List[Faiblesse]) -> str:
        """Genere l'identite narrative unique."""
        # Find dominant traits
        top_forces = [f.trait for f in forces[:2]] if forces else []

        # Determine identity template
        if "diesel_factor" in top_forces and "pressing_intensity" in top_forces:
            template = IDENTITY_TEMPLATES["pressing_diesel"]
        elif "possession_control" in top_forces:
            template = IDENTITY_TEMPLATES["possession_dominant"]
        elif "block_depth" in [f.trait for f in faiblesses] and faiblesses[0].score < 30:
            template = IDENTITY_TEMPLATES["counter_specialist"]
        elif "aerial_resistance" in top_forces or "set_piece_threat" in top_forces:
            template = IDENTITY_TEMPLATES["aerial_powerhouse"]
        elif "clinical_finishing" in top_forces:
            template = IDENTITY_TEMPLATES["clinical_assassin"]
        elif "defensive_compactness" in top_forces:
            template = IDENTITY_TEMPLATES["defensive_fortress"]
        elif "first_half_intensity" in top_forces:
            template = IDENTITY_TEMPLATES["early_starter"]
        elif "clutch_factor" in top_forces:
            template = IDENTITY_TEMPLATES["late_surge"]
        elif "home_dominance" in top_forces:
            template = IDENTITY_TEMPLATES["home_beast"]
        else:
            template = IDENTITY_TEMPLATES["balanced_chameleon"]

        return template.format(team=team)

    def _derive_markets(self, axes: Dict[str, AxisScore],
                       forces: List[Force],
                       faiblesses: List[Faiblesse]) -> Tuple[List[Dict], List[Dict]]:
        """Derive les marches exploitables FOR et AGAINST."""
        markets_for = []
        markets_against = []

        # From forces (FOR markets)
        for force in forces:
            for market in force.markets:
                market_entry = {
                    "market": market["market"],
                    "edge": market["edge"] * (force.score / 70),  # Scale by score
                    "confidence": "HIGH" if force.score >= 75 else "MEDIUM",
                    "source": f"{force.trait} ({force.score:.0f})"
                }
                if market["direction"] == "FOR":
                    markets_for.append(market_entry)
                else:
                    markets_against.append(market_entry)

        # From faiblesses (AGAINST markets)
        for faiblesse in faiblesses:
            for market in faiblesse.exploitation:
                market_entry = {
                    "market": market["market"],
                    "edge": market["edge"] * ((100 - faiblesse.score) / 70),
                    "confidence": "HIGH" if faiblesse.score <= 25 else "MEDIUM",
                    "source": f"{faiblesse.trait} ({faiblesse.score:.0f})"
                }
                if market["direction"] == "AGAINST":
                    markets_against.append(market_entry)
                else:
                    markets_for.append(market_entry)

        # Sort by edge
        markets_for.sort(key=lambda x: -x["edge"])
        markets_against.sort(key=lambda x: -x["edge"])

        return markets_for[:8], markets_against[:8]

    def _generate_narrative(self, team: str, identity: str,
                           forces: List[Force],
                           faiblesses: List[Faiblesse],
                           markets_for: List[Dict],
                           markets_against: List[Dict]) -> str:
        """Genere le texte narratif complet."""
        lines = []

        # Identity
        lines.append(f"## {team}")
        lines.append("")
        lines.append(f"**Identite**: {identity}")
        lines.append("")

        # Forces
        if forces:
            lines.append("### Forces Distinctives")
            for f in forces[:3]:
                lines.append(f"- **{f.trait.replace('_', ' ').title()}** ({f.score:.0f}/100)")
                if f.markets:
                    mkts = ", ".join([m["market"] for m in f.markets[:2]])
                    lines.append(f"  → Marches: {mkts}")
            lines.append("")

        # Faiblesses
        if faiblesses:
            lines.append("### Faiblesses Exploitables")
            for f in faiblesses[:3]:
                lines.append(f"- **{f.trait.replace('_', ' ').title()}** ({f.score:.0f}/100)")
                if f.exploitation:
                    mkts = ", ".join([m["market"] for m in f.exploitation[:2]])
                    lines.append(f"  → Exploitation: {mkts}")
            lines.append("")

        # Market summary
        lines.append("### Recommandations Marches")
        lines.append("")
        lines.append("**Parier POUR cette equipe:**")
        for m in markets_for[:3]:
            lines.append(f"- {m['market']} (edge: {m['edge']:.1f})")
        lines.append("")
        lines.append("**Parier CONTRE cette equipe:**")
        for m in markets_against[:3]:
            lines.append(f"- {m['market']} (edge: {m['edge']:.1f})")

        return "\n".join(lines)

    def _generate_summary(self, identity: str, forces: List[Force],
                         faiblesses: List[Faiblesse]) -> str:
        """Genere un resume court."""
        force_str = ", ".join([f.trait.replace('_', ' ') for f in forces[:2]]) if forces else "equilibre"
        faiblesse_str = faiblesses[0].trait.replace('_', ' ') if faiblesses else "aucune majeure"

        return f"Forces: {force_str}. Faiblesse: {faiblesse_str}."

    def generate_profile(self, team: str) -> dict:
        """Genere le profil narratif complet pour une equipe."""
        # Normalize team name
        team_data = None
        team_key = None

        for key in self.teams.keys():
            if key.lower() == team.lower() or team.lower() in key.lower():
                team_data = self.teams[key]
                team_key = key
                break

        if team_data is None:
            raise KeyError(f"Team not found: {team}")

        # Get league
        league = team_data.get('context', {}).get('league') or \
                 team_data.get('tactical', {}).get('league') or 'Unknown'

        # Calculate axes
        axes = self._calculate_axes(team_data)

        # Extract forces and faiblesses
        forces = self._extract_forces(axes)
        faiblesses = self._extract_faiblesses(axes)

        # Derive identity
        identity = self._derive_identity(team_key, axes, forces, faiblesses)

        # Derive markets
        markets_for, markets_against = self._derive_markets(axes, forces, faiblesses)

        # Generate narrative
        narrative = self._generate_narrative(
            team_key, identity, forces, faiblesses, markets_for, markets_against
        )

        # Generate summary
        summary = self._generate_summary(identity, forces, faiblesses)

        return {
            "team": team_key,
            "league": league,
            "generated_at": datetime.now().isoformat(),
            "identity": identity,
            "summary": summary,
            "axes": {
                name: {
                    "score": axis.score,
                    "raw_value": axis.raw_value,
                    "percentile": axis.percentile,
                    "description": axis.description
                }
                for name, axis in axes.items()
            },
            "forces": [
                {
                    "trait": f.trait,
                    "score": f.score,
                    "description": f.description,
                    "markets": f.markets
                }
                for f in forces
            ],
            "faiblesses": [
                {
                    "trait": f.trait,
                    "score": f.score,
                    "description": f.description,
                    "exploitation": f.exploitation
                }
                for f in faiblesses
            ],
            "markets_for": markets_for,
            "markets_against": markets_against,
            "narrative": narrative
        }

    def generate_all_profiles(self) -> dict:
        """Genere les profils pour toutes les equipes."""
        profiles = {}
        errors = []

        for team in self.teams.keys():
            try:
                profiles[team] = self.generate_profile(team)
            except Exception as e:
                errors.append({"team": team, "error": str(e)})

        return {
            "generated_at": datetime.now().isoformat(),
            "count": len(profiles),
            "profiles": profiles,
            "errors": errors if errors else None
        }


# ═══════════════════════════════════════════════════════════════════
# TESTS INTEGRES
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("DNA NARRATIVE GENERATOR V1.0 - TESTS")
    print("=" * 70)

    gen = DNANarrativeGenerator()

    # Test 5 equipes avec profils DIFFERENTS
    teams = ["Liverpool", "Manchester City", "Atletico Madrid", "Burnley", "Brighton"]

    for team in teams:
        try:
            profile = gen.generate_profile(team)

            print(f"\n{'=' * 60}")
            print(f"  {team}")
            print(f"{'=' * 60}")
            print(f"  Identity: {profile['identity']}")
            print(f"  Summary: {profile['summary']}")

            print(f"\n  Top 3 Axes:")
            sorted_axes = sorted(profile['axes'].items(), key=lambda x: -x[1]['score'])
            for name, data in sorted_axes[:3]:
                print(f"    {name}: {data['score']:.0f}/100 ({data['percentile']})")

            if profile['forces']:
                print(f"\n  Forces:")
                for f in profile['forces'][:2]:
                    print(f"    - {f['trait']}: {f['score']:.0f}")

            if profile['faiblesses']:
                print(f"\n  Faiblesses:")
                for f in profile['faiblesses'][:2]:
                    print(f"    - {f['trait']}: {f['score']:.0f}")

            print(f"\n  Markets FOR: {[m['market'] for m in profile['markets_for'][:2]]}")
            print(f"  Markets AGAINST: {[m['market'] for m in profile['markets_against'][:2]]}")

        except Exception as e:
            print(f"\n  {team}: ERROR - {e}")

    print("\n" + "=" * 70)
    print("TESTS TERMINES")
    print("=" * 70)
