"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║  REAL LOADERS V2 - Adaptés aux structures JSON réelles                               ║
║  Version: 2.1                                                                        ║
║  Corrections: Timing 76+, Defense LIST, Validation                                   ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

Installation: /home/Mon_ps/quantum/loaders/real_loaders.py
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from dataclasses import dataclass, field

# ═══════════════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════════════

DATA_ROOT = Path("/home/Mon_ps/data")
QUANTUM_V2 = DATA_ROOT / "quantum_v2"

logger = logging.getLogger("quantum.real_loaders")

# ═══════════════════════════════════════════════════════════════════════════════════════
# DATA QUALITY FLAGS
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class DataQualityFlags:
    """Flags de qualité des données."""
    timing_mismatch: bool = False
    timing_mismatch_pct: float = 0.0
    suspicious_zeros: List[str] = field(default_factory=list)
    profile_contradictions: List[str] = field(default_factory=list)
    regression_warnings: List[str] = field(default_factory=list)
    overall_score: float = 100.0
    
    def add_issue(self, severity: str, message: str):
        if severity == "CRITICAL":
            self.overall_score -= 20
        elif severity == "WARNING":
            self.overall_score -= 5
        self.overall_score = max(0, self.overall_score)


# ═══════════════════════════════════════════════════════════════════════════════════════
# TIMING NORMALIZATION (CORRECTION #1)
# ═══════════════════════════════════════════════════════════════════════════════════════

def normalize_timing_key(key: str) -> str:
    """
    Normalise les clés de timing.
    "76+" → "76_90"
    "1-15" → "0_15"
    """
    mapping = {
        "1-15": "0_15",
        "0-15": "0_15",
        "16-30": "16_30",
        "15-30": "16_30",
        "31-45": "31_45",
        "30-45": "31_45",
        "46-60": "46_60",
        "45-60": "46_60",
        "61-75": "61_75",
        "60-75": "61_75",
        "76-90": "76_90",
        "75-90": "76_90",
        "76+": "76_90",  # CORRECTION #1
    }
    return mapping.get(key, key.replace("-", "_"))


def extract_timing_from_context(timing_data: Dict) -> Dict[str, Dict]:
    """
    Extrait et normalise les données timing du context_dna.
    """
    normalized = {}
    
    for period, pdata in timing_data.items():
        norm_key = normalize_timing_key(period)
        normalized[norm_key] = {
            "shots": pdata.get("shots", 0),
            "goals": pdata.get("goals", 0),
            "xG": pdata.get("xG", 0),
            "conceded": pdata.get("conceded", 0),
            "xGA": pdata.get("xGA", 0),
        }
    
    return normalized


# ═══════════════════════════════════════════════════════════════════════════════════════
# CONTEXT DNA LOADER (Real Structure)
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class RealContextDNA:
    """Context DNA avec structure réelle."""
    team: str
    team_id: str
    league: str
    matches: int
    
    # Record
    wins: int
    draws: int
    losses: int
    points: int
    goals_for: int
    goals_against: int
    
    # xG History
    xg_total: float
    xga_total: float
    xg_90: float
    xga_90: float
    npxg: float
    npxga: float
    deep: int
    deep_90: float
    ppda: float
    pressing_style: str
    
    # Variance
    xg_overperformance: float
    xga_overperformance: float
    luck_index: float
    
    # Momentum
    form_last_5: str
    points_last_5: int
    xg_last_5: float
    xga_last_5: float
    
    # Timing (normalized)
    timing: Dict[str, Dict]
    
    # Formation stats
    formations: Dict[str, Dict]
    
    # Game state
    game_state: Dict[str, Dict]
    
    # Quality flags
    quality: DataQualityFlags = field(default_factory=DataQualityFlags)
    
    @property
    def ppg(self) -> float:
        return self.points / max(1, self.matches)
    
    @property
    def ppg_last_5(self) -> float:
        return self.points_last_5 / 5
    
    @property
    def form_delta(self) -> float:
        """Différence forme récente vs saison."""
        return self.ppg_last_5 - self.ppg
    
    @property
    def is_overperforming_offense(self) -> bool:
        return self.xg_overperformance > 2
    
    @property
    def is_overperforming_defense(self) -> bool:
        return self.xga_overperformance < -2


def load_real_context(filepath: Path = None) -> Dict[str, RealContextDNA]:
    """Charge tous les Context DNA depuis le fichier réel."""
    
    if filepath is None:
        filepath = QUANTUM_V2 / "teams_context_dna.json"
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception as e:
        logger.error(f"Erreur chargement {filepath}: {e}")
        return {}
    
    results = {}
    
    for team, data in raw_data.items():
        try:
            record = data.get("record", {})
            history = data.get("history", {})
            variance = data.get("variance", {})
            momentum = data.get("momentum_dna", {})
            context_dna = data.get("context_dna", {})
            
            # Normalize timing
            timing = extract_timing_from_context(context_dna.get("timing", {}))
            
            ctx = RealContextDNA(
                team=team,
                team_id=data.get("team_id", ""),
                league=data.get("league", ""),
                matches=data.get("matches", 0),
                
                wins=record.get("wins", 0),
                draws=record.get("draws", 0),
                losses=record.get("losses", 0),
                points=record.get("points", 0),
                goals_for=record.get("goals_for", 0),
                goals_against=record.get("goals_against", 0),
                
                xg_total=history.get("xg", 0),
                xga_total=history.get("xga", 0),
                xg_90=history.get("xg_90", 0),
                xga_90=history.get("xga_90", 0),
                npxg=history.get("npxg", 0),
                npxga=history.get("npxga", 0),
                deep=history.get("deep", 0),
                deep_90=history.get("deep_90", 0),
                ppda=history.get("ppda", 0),
                pressing_style=history.get("pressing_style", "UNKNOWN"),
                
                xg_overperformance=variance.get("xg_overperformance", 0),
                xga_overperformance=variance.get("xga_overperformance", 0),
                luck_index=variance.get("luck_index", 0),
                
                form_last_5=momentum.get("form_last_5", ""),
                points_last_5=momentum.get("points_last_5", 0),
                xg_last_5=momentum.get("xg_last_5", 0),
                xga_last_5=momentum.get("xga_last_5", 0),
                
                timing=timing,
                formations=context_dna.get("formation", {}),
                game_state=context_dna.get("gameState", {}),
            )
            
            # Validate timing totals
            timing_xg_sum = sum(t.get("xG", 0) for t in timing.values())
            timing_xga_sum = sum(t.get("xGA", 0) for t in timing.values())
            
            if ctx.xg_total > 0:
                xg_diff_pct = abs((timing_xg_sum - ctx.xg_total) / ctx.xg_total) * 100
                if xg_diff_pct > 5:
                    ctx.quality.timing_mismatch = True
                    ctx.quality.timing_mismatch_pct = xg_diff_pct
                    ctx.quality.add_issue("WARNING", f"Timing xG mismatch: {xg_diff_pct:.1f}%")
            
            results[team] = ctx
            
        except Exception as e:
            logger.warning(f"Erreur parsing context {team}: {e}")
    
    logger.info(f"Chargé {len(results)} Context DNA")
    return results


# ═══════════════════════════════════════════════════════════════════════════════════════
# DEFENSE DNA LOADER (Real Structure - LIST!)
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class RealDefenseDNA:
    """Defense DNA avec structure réelle."""
    team_name: str
    team_understat: str
    league: str
    season: str
    matches_played: int
    
    # Core xGA
    xga_total: float
    ga_total: int
    xga_per_90: float
    ga_per_90: float
    defense_overperform: float
    
    # Clean sheets
    clean_sheets: int
    clean_sheets_home: int
    clean_sheets_away: int
    cs_pct: float
    cs_pct_home: float
    cs_pct_away: float
    
    # Home/Away
    xga_home: float
    ga_home: int
    matches_home: int
    xga_away: float
    ga_away: int
    matches_away: int
    xga_per_90_home: float
    xga_per_90_away: float
    
    # Timing xGA
    xga_0_15: float
    xga_16_30: float
    xga_31_45: float
    xga_46_60: float
    xga_61_75: float
    xga_76_90: float
    xga_1h: float
    xga_2h: float
    
    # Timing GA
    ga_0_15: int
    ga_16_30: int
    ga_31_45: int
    ga_46_60: int
    ga_61_75: int
    ga_76_90: int
    
    # Zones
    xga_six_yard: float
    xga_penalty_area: float
    xga_outside_box: float
    
    # Set pieces
    xga_open_play: float
    xga_set_piece: float
    xga_corner: float
    xga_free_kick: float
    xga_penalty: float
    set_piece_vuln_pct: float
    
    # Game state
    xga_level: float
    xga_leading_1: float
    xga_leading_2plus: float
    xga_losing_1: float
    xga_losing_2plus: float
    
    # Profiles
    defense_profile: str
    timing_profile: str
    home_away_defense_profile: str
    set_piece_profile: str
    
    # Resist metrics
    resist_global: float
    resist_aerial: float
    resist_longshot: float
    resist_open_play: float
    resist_early: float
    resist_late: float
    resist_chaos: float
    
    # Quality
    quality: DataQualityFlags = field(default_factory=DataQualityFlags)
    
    @property
    def timing_sum(self) -> float:
        """Sum of all timing periods."""
        return (self.xga_0_15 + self.xga_16_30 + self.xga_31_45 + 
                self.xga_46_60 + self.xga_61_75 + self.xga_76_90)
    
    @property
    def timing_mismatch_pct(self) -> float:
        """% difference between timing sum and total."""
        if self.xga_total > 0:
            return ((self.timing_sum - self.xga_total) / self.xga_total) * 100
        return 0
    
    @property
    def is_home_fortress(self) -> bool:
        return self.xga_per_90_home < self.xga_per_90_away * 0.7
    
    @property
    def late_vulnerability_pct(self) -> float:
        """% of xGA in last 15 min."""
        if self.xga_total > 0:
            return (self.xga_76_90 / self.xga_total) * 100
        return 0


def load_real_defense(filepath: Path = None) -> Dict[str, RealDefenseDNA]:
    """
    Charge tous les Defense DNA depuis le fichier réel.
    NOTE: Le fichier est une LISTE, pas un dict!
    """
    
    if filepath is None:
        filepath = DATA_ROOT / "defense_dna" / "team_defense_dna_v5_1_corrected.json"
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception as e:
        logger.error(f"Erreur chargement {filepath}: {e}")
        return {}
    
    # C'est une LISTE!
    if not isinstance(raw_data, list):
        logger.error(f"Defense data n'est pas une liste!")
        return {}
    
    results = {}
    
    for item in raw_data:
        try:
            team = item.get("team_name", "")
            if not team:
                continue
            
            defense = RealDefenseDNA(
                team_name=team,
                team_understat=item.get("team_understat", team),
                league=item.get("league", ""),
                season=item.get("season", ""),
                matches_played=item.get("matches_played", 0),
                
                xga_total=item.get("xga_total", 0),
                ga_total=item.get("ga_total", 0),
                xga_per_90=item.get("xga_per_90", 0),
                ga_per_90=item.get("ga_per_90", 0),
                defense_overperform=item.get("defense_overperform", 0),
                
                clean_sheets=item.get("clean_sheets", 0),
                clean_sheets_home=item.get("clean_sheets_home", 0),
                clean_sheets_away=item.get("clean_sheets_away", 0),
                cs_pct=item.get("cs_pct", 0),
                cs_pct_home=item.get("cs_pct_home", 0),
                cs_pct_away=item.get("cs_pct_away", 0),
                
                xga_home=item.get("xga_home", 0),
                ga_home=item.get("ga_home", 0),
                matches_home=item.get("matches_home", 0),
                xga_away=item.get("xga_away", 0),
                ga_away=item.get("ga_away", 0),
                matches_away=item.get("matches_away", 0),
                xga_per_90_home=item.get("xga_per_90_home", 0),
                xga_per_90_away=item.get("xga_per_90_away", 0),
                
                xga_0_15=item.get("xga_0_15", 0),
                xga_16_30=item.get("xga_16_30", 0),
                xga_31_45=item.get("xga_31_45", 0),
                xga_46_60=item.get("xga_46_60", 0),
                xga_61_75=item.get("xga_61_75", 0),
                xga_76_90=item.get("xga_76_90", 0),
                xga_1h=item.get("xga_1h", 0),
                xga_2h=item.get("xga_2h", 0),
                
                ga_0_15=item.get("ga_0_15", 0),
                ga_16_30=item.get("ga_16_30", 0),
                ga_31_45=item.get("ga_31_45", 0),
                ga_46_60=item.get("ga_46_60", 0),
                ga_61_75=item.get("ga_61_75", 0),
                ga_76_90=item.get("ga_76_90", 0),
                
                xga_six_yard=item.get("xga_six_yard", 0),
                xga_penalty_area=item.get("xga_penalty_area", 0),
                xga_outside_box=item.get("xga_outside_box", 0),
                
                xga_open_play=item.get("xga_open_play", 0),
                xga_set_piece=item.get("xga_set_piece", 0),
                xga_corner=item.get("xga_corner", 0),
                xga_free_kick=item.get("xga_free_kick", 0),
                xga_penalty=item.get("xga_penalty", 0),
                set_piece_vuln_pct=item.get("set_piece_vuln_pct", 0),
                
                xga_level=item.get("xga_level", 0),
                xga_leading_1=item.get("xga_leading_1", 0),
                xga_leading_2plus=item.get("xga_leading_2plus", 0),
                xga_losing_1=item.get("xga_losing_1", 0),
                xga_losing_2plus=item.get("xga_losing_2plus", 0),
                
                defense_profile=item.get("defense_profile", "UNKNOWN"),
                timing_profile=item.get("timing_profile", "UNKNOWN"),
                home_away_defense_profile=item.get("home_away_defense_profile", "UNKNOWN"),
                set_piece_profile=item.get("set_piece_profile", "UNKNOWN"),
                
                resist_global=item.get("resist_global", 0),
                resist_aerial=item.get("resist_aerial", 0),
                resist_longshot=item.get("resist_longshot", 0),
                resist_open_play=item.get("resist_open_play", 0),
                resist_early=item.get("resist_early", 0),
                resist_late=item.get("resist_late", 0),
                resist_chaos=item.get("resist_chaos", 0),
            )
            
            # VALIDATION #3: Check timing sum vs total
            mismatch = defense.timing_mismatch_pct
            if abs(mismatch) > 5:
                defense.quality.timing_mismatch = True
                defense.quality.timing_mismatch_pct = mismatch
                
                severity = "CRITICAL" if abs(mismatch) > 20 else "WARNING"
                defense.quality.add_issue(severity, f"Timing mismatch: {mismatch:.1f}%")
            
            # VALIDATION #4: Flag suspicious zeros
            if defense.xga_76_90 == 0 and defense.xga_total > 5:
                defense.quality.suspicious_zeros.append("xga_76_90")
                defense.quality.add_issue("CRITICAL", "xGA 76-90 = 0 suspicious")
            
            # Check profile contradiction
            if "FADES_LATE" in defense.timing_profile and defense.late_vulnerability_pct < 10:
                defense.quality.profile_contradictions.append(
                    f"Profile says FADES_LATE but late_pct={defense.late_vulnerability_pct:.1f}%"
                )
                defense.quality.add_issue("CRITICAL", "Profile contradiction")
            
            results[team] = defense
            
        except Exception as e:
            logger.warning(f"Erreur parsing defense: {e}")
    
    logger.info(f"Chargé {len(results)} Defense DNA")
    return results


# ═══════════════════════════════════════════════════════════════════════════════════════
# GOALKEEPER DNA LOADER
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class RealGoalkeeperDNA:
    """Goalkeeper DNA avec structure réelle."""
    team: str
    goalkeeper: str
    gk_performance: float
    gk_percentile: float
    save_rate: float
    shots_faced: int
    saves: int
    goals_conceded: int
    
    # Difficulty analysis
    easy_sr: float
    easy_vs_expected: float
    easy_sample: int
    medium_sr: float
    medium_vs_expected: float
    medium_sample: int
    hard_sr: float
    hard_vs_expected: float
    hard_sample: int
    very_hard_sr: float
    very_hard_vs_expected: float
    very_hard_sample: int
    big_save_ability: str
    routine_reliability: str
    
    # Situation analysis
    open_play_sr: float
    corners_sr: float
    set_pieces_sr: float
    penalties_sr: float
    strongest: str
    weakest: str
    
    # Timing
    timing_sr: Dict[str, float] = field(default_factory=dict)
    
    quality: DataQualityFlags = field(default_factory=DataQualityFlags)
    
    @property
    def is_elite(self) -> bool:
        return self.gk_percentile >= 75
    
    @property
    def is_liability(self) -> bool:
        return self.gk_percentile <= 25


def load_real_goalkeeper(filepath: Path = None) -> Dict[str, RealGoalkeeperDNA]:
    """Charge tous les Goalkeeper DNA."""
    
    if filepath is None:
        filepath = DATA_ROOT / "goalkeeper_dna" / "goalkeeper_dna_v4_4_by_team.json"
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception as e:
        logger.error(f"Erreur chargement {filepath}: {e}")
        return {}
    
    results = {}
    
    for team, data in raw_data.items():
        try:
            diff = data.get("difficulty_analysis", {})
            sit = data.get("situation_analysis", {})
            timing = data.get("timing_analysis", {}).get("periods", {})
            
            gk = RealGoalkeeperDNA(
                team=team,
                goalkeeper=data.get("goalkeeper", ""),
                gk_performance=data.get("gk_performance", 0),
                gk_percentile=data.get("gk_percentile", 50),
                save_rate=data.get("save_rate", 0),
                shots_faced=data.get("shots_faced", 0),
                saves=data.get("saves", 0),
                goals_conceded=data.get("goals_conceded", 0),
                
                easy_sr=diff.get("easy", {}).get("sr", 0),
                easy_vs_expected=diff.get("easy", {}).get("vs_expected", 0),
                easy_sample=diff.get("easy", {}).get("sample", 0),
                medium_sr=diff.get("medium", {}).get("sr", 0),
                medium_vs_expected=diff.get("medium", {}).get("vs_expected", 0),
                medium_sample=diff.get("medium", {}).get("sample", 0),
                hard_sr=diff.get("hard", {}).get("sr", 0),
                hard_vs_expected=diff.get("hard", {}).get("vs_expected", 0),
                hard_sample=diff.get("hard", {}).get("sample", 0),
                very_hard_sr=diff.get("very_hard", {}).get("sr", 0),
                very_hard_vs_expected=diff.get("very_hard", {}).get("vs_expected", 0),
                very_hard_sample=diff.get("very_hard", {}).get("sample", 0),
                big_save_ability=diff.get("big_save_ability", "UNKNOWN"),
                routine_reliability=diff.get("routine_reliability", "UNKNOWN"),
                
                open_play_sr=sit.get("open_play", {}).get("sr", 0),
                corners_sr=sit.get("corners", {}).get("sr", 0),
                set_pieces_sr=sit.get("set_pieces", {}).get("sr", 0),
                penalties_sr=sit.get("penalties", {}).get("sr", 0),
                strongest=sit.get("strongest", ""),
                weakest=sit.get("weakest", ""),
                
                timing_sr={k: v.get("save_rate", 0) for k, v in timing.items()},
            )
            
            results[team] = gk
            
        except Exception as e:
            logger.warning(f"Erreur parsing goalkeeper {team}: {e}")
    
    logger.info(f"Chargé {len(results)} Goalkeeper DNA")
    return results


# ═══════════════════════════════════════════════════════════════════════════════════════
# UNIFIED TEAM LOADER
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class UnifiedTeamDNA:
    """DNA unifié d'une équipe avec toutes les sources."""
    team: str
    context: Optional[RealContextDNA] = None
    defense: Optional[RealDefenseDNA] = None
    goalkeeper: Optional[RealGoalkeeperDNA] = None
    
    # Aggregated quality
    overall_quality: float = 100.0
    issues: List[str] = field(default_factory=list)
    
    @property
    def is_complete(self) -> bool:
        return all([self.context, self.defense, self.goalkeeper])
    
    @property
    def league(self) -> str:
        if self.context:
            return self.context.league
        if self.defense:
            return self.defense.league
        return "UNKNOWN"


def load_unified_team(team: str, 
                      context_data: Dict[str, RealContextDNA] = None,
                      defense_data: Dict[str, RealDefenseDNA] = None,
                      gk_data: Dict[str, RealGoalkeeperDNA] = None) -> UnifiedTeamDNA:
    """Charge un TeamDNA unifié."""
    
    unified = UnifiedTeamDNA(team=team)
    
    if context_data and team in context_data:
        unified.context = context_data[team]
        if unified.context.quality.overall_score < 100:
            unified.issues.append(f"Context: {unified.context.quality.overall_score:.0f}/100")
    
    if defense_data and team in defense_data:
        unified.defense = defense_data[team]
        if unified.defense.quality.overall_score < 100:
            unified.issues.append(f"Defense: {unified.defense.quality.overall_score:.0f}/100")
    
    if gk_data and team in gk_data:
        unified.goalkeeper = gk_data[team]
    
    # Calculate overall quality
    scores = []
    if unified.context:
        scores.append(unified.context.quality.overall_score)
    if unified.defense:
        scores.append(unified.defense.quality.overall_score)
    if unified.goalkeeper:
        scores.append(unified.goalkeeper.quality.overall_score)
    
    if scores:
        unified.overall_quality = sum(scores) / len(scores)
    
    return unified


def load_all_teams() -> Dict[str, UnifiedTeamDNA]:
    """Charge toutes les équipes avec données unifiées."""
    
    context_data = load_real_context()
    defense_data = load_real_defense()
    gk_data = load_real_goalkeeper()
    
    # Get all team names
    all_teams = set()
    all_teams.update(context_data.keys())
    all_teams.update(defense_data.keys())
    all_teams.update(gk_data.keys())
    
    results = {}
    for team in sorted(all_teams):
        results[team] = load_unified_team(team, context_data, defense_data, gk_data)
    
    logger.info(f"Chargé {len(results)} équipes unifiées")
    return results


# ═══════════════════════════════════════════════════════════════════════════════════════
# QUICK ACCESS FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════════════

# Cache global
_cache: Dict[str, Any] = {}


def get_team(team: str) -> Optional[UnifiedTeamDNA]:
    """Récupère une équipe (avec cache)."""
    
    if "all_teams" not in _cache:
        _cache["all_teams"] = load_all_teams()
    
    return _cache["all_teams"].get(team)


def get_defense(team: str) -> Optional[RealDefenseDNA]:
    """Récupère les données défensives d'une équipe."""
    
    if "defense" not in _cache:
        _cache["defense"] = load_real_defense()
    
    return _cache["defense"].get(team)


def get_context(team: str) -> Optional[RealContextDNA]:
    """Récupère les données context d'une équipe."""
    
    if "context" not in _cache:
        _cache["context"] = load_real_context()
    
    return _cache["context"].get(team)


def get_goalkeeper(team: str) -> Optional[RealGoalkeeperDNA]:
    """Récupère les données GK d'une équipe."""
    
    if "goalkeeper" not in _cache:
        _cache["goalkeeper"] = load_real_goalkeeper()
    
    return _cache["goalkeeper"].get(team)


def clear_cache():
    """Vide le cache."""
    _cache.clear()


# ═══════════════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n🔧 Test Real Loaders V2\n")
    
    # Test defense (LIST format)
    print("Loading Defense DNA...")
    defense = load_real_defense()
    print(f"  ✅ {len(defense)} équipes chargées")
    
    if "Arsenal" in defense:
        ars = defense["Arsenal"]
        print(f"\n  Arsenal:")
        print(f"    xGA total: {ars.xga_total:.2f}")
        print(f"    Timing sum: {ars.timing_sum:.2f}")
        print(f"    Mismatch: {ars.timing_mismatch_pct:.1f}%")
        print(f"    Quality: {ars.quality.overall_score:.0f}/100")
        if ars.quality.suspicious_zeros:
            print(f"    ⚠️ Zeros suspects: {ars.quality.suspicious_zeros}")
    
    # Test context
    print("\nLoading Context DNA...")
    context = load_real_context()
    print(f"  ✅ {len(context)} équipes chargées")
    
    if "Arsenal" in context:
        ars = context["Arsenal"]
        print(f"\n  Arsenal:")
        print(f"    xG: {ars.xg_total:.2f} | xGA: {ars.xga_total:.2f}")
        print(f"    Form: {ars.form_last_5} ({ars.points_last_5} pts)")
        print(f"    PPG delta: {ars.form_delta:+.2f}")
    
    # Test goalkeeper
    print("\nLoading Goalkeeper DNA...")
    gk = load_real_goalkeeper()
    print(f"  ✅ {len(gk)} équipes chargées")
    
    # Test unified
    print("\nLoading Unified Teams...")
    teams = load_all_teams()
    
    # Stats
    complete = sum(1 for t in teams.values() if t.is_complete)
    low_quality = sum(1 for t in teams.values() if t.overall_quality < 80)
    
    print(f"  ✅ {len(teams)} équipes")
    print(f"  ✅ {complete} complètes")
    print(f"  ⚠️ {low_quality} avec qualité < 80")
    
    print("\n✅ Test terminé!")
