#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║  UNIFIED TEAM LOADER - CHESS ENGINE V2.0                                              ║
║  "Chaque équipe = 1 ADN = 1 empreinte digitale unique"                                ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝

PHILOSOPHIE MON_PS:
───────────────────
1. ÉQUIPE au centre (comme un trou noir)
2. Chaque équipe = 1 ADN = 1 empreinte digitale unique
3. Les marchés sont des CONSÉQUENCES de l'ADN, pas l'inverse

USAGE:
───────
    from quantum.loaders.unified_loader import load_team, load_all_teams
    
    arsenal = load_team("Arsenal")
    print(arsenal.narrative)           # Profil narratif unique
    print(arsenal.exploitable_markets) # Marchés profitables POUR Arsenal
    print(arsenal.fingerprint)         # Empreinte digitale unique

SOURCES FUSIONNÉES:
───────────────────
- team_defense_dna_v5_1_corrected.json  → 125 métriques défensives
- teams_context_dna.json                 → Formation, PPDA, momentum
- goalkeeper_dna_v4_4_by_team.json       → Performance GK, timing
- team_dna_profiles_v2.json              → Fingerprints, profiles
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from functools import lru_cache

# ═══════════════════════════════════════════════════════════════════════════════
# PATHS
# ═══════════════════════════════════════════════════════════════════════════════

DATA_ROOT = Path("/home/Mon_ps/data")
DEFENSE_FILE = DATA_ROOT / "defense_dna" / "team_defense_dna_v5_1_corrected.json"
CONTEXT_FILE = DATA_ROOT / "quantum_v2" / "teams_context_dna.json"
GK_FILE = DATA_ROOT / "goalkeeper_dna" / "goalkeeper_dna_v4_4_by_team.json"
PROFILES_FILE = DATA_ROOT / "team_dna_profiles_v2.json"


# ═══════════════════════════════════════════════════════════════════════════════
# DATACLASSES - ADN STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TimingDNA:
    """Quand l'équipe est vulnérable/forte"""
    xga_0_15: float = 0.0
    xga_16_30: float = 0.0
    xga_31_45: float = 0.0
    xga_46_60: float = 0.0
    xga_61_75: float = 0.0
    xga_76_90: float = 0.0
    
    # Percentages
    early_pct: float = 0.0      # 0-15
    late_pct: float = 0.0       # 76-90
    first_half_pct: float = 0.0
    second_half_pct: float = 0.0
    
    # Profile
    timing_profile: str = "CONSISTENT"
    
    @property
    def weak_periods(self) -> List[str]:
        """Périodes où l'équipe concède le plus"""
        periods = [
            ("0-15", self.xga_0_15),
            ("16-30", self.xga_16_30),
            ("31-45", self.xga_31_45),
            ("46-60", self.xga_46_60),
            ("61-75", self.xga_61_75),
            ("76-90", self.xga_76_90),
        ]
        avg = sum(p[1] for p in periods) / 6
        return [p[0] for p in periods if p[1] > avg * 1.3]
    
    @property
    def strong_periods(self) -> List[str]:
        """Périodes où l'équipe résiste le mieux"""
        periods = [
            ("0-15", self.xga_0_15),
            ("16-30", self.xga_16_30),
            ("31-45", self.xga_31_45),
            ("46-60", self.xga_46_60),
            ("61-75", self.xga_61_75),
            ("76-90", self.xga_76_90),
        ]
        avg = sum(p[1] for p in periods) / 6
        return [p[0] for p in periods if p[1] < avg * 0.7]


@dataclass
class DefenseDNA:
    """Profil défensif complet"""
    xga_total: float = 0.0
    xga_per_90: float = 0.0
    goals_against: int = 0
    clean_sheet_pct: float = 0.0
    
    # Zones
    xga_box: float = 0.0
    xga_outside_box: float = 0.0
    xga_set_piece: float = 0.0
    xga_open_play: float = 0.0
    
    # Home/Away split
    home_xga_per_90: float = 0.0
    away_xga_per_90: float = 0.0
    home_cs_pct: float = 0.0
    away_cs_pct: float = 0.0
    
    # Resist metrics
    resist_late: float = 0.0
    resist_set_piece: float = 0.0
    
    # Timing
    timing: TimingDNA = field(default_factory=TimingDNA)
    
    # Profile
    defensive_profile: str = "AVERAGE"
    
    @property
    def home_away_ratio(self) -> float:
        """Ratio xGA away/home - >1.5 = HOME FORTRESS"""
        if self.home_xga_per_90 > 0:
            return self.away_xga_per_90 / self.home_xga_per_90
        return 1.0
    
    @property
    def luck_factor(self) -> float:
        """xGA - GA : positif = chanceux, négatif = malchanceux"""
        return self.xga_total - self.goals_against


@dataclass
class GoalkeeperDNA:
    """Profil gardien"""
    name: str = "Unknown"
    save_rate: float = 0.0
    goals_prevented: float = 0.0  # vs xGA
    
    # Difficulty
    avg_shot_difficulty: float = 0.0
    high_difficulty_sr: float = 0.0
    low_difficulty_sr: float = 0.0
    
    # Timing
    sr_first_half: float = 0.0
    sr_second_half: float = 0.0
    sr_late: float = 0.0  # 76-90
    
    # Situations
    sr_open_play: float = 0.0
    sr_set_piece: float = 0.0
    sr_penalty: float = 0.0
    
    @property
    def quality_tier(self) -> str:
        """Tier du gardien basé sur goals_prevented"""
        if self.goals_prevented > 3:
            return "ELITE"
        elif self.goals_prevented > 1:
            return "GOOD"
        elif self.goals_prevented > -1:
            return "AVERAGE"
        elif self.goals_prevented > -3:
            return "WEAK"
        else:
            return "LIABILITY"


@dataclass
class MomentumDNA:
    """Forme et momentum"""
    form_last_5: str = "-----"  # WWDLL
    points_last_5: int = 0
    ppg_season: float = 0.0
    ppg_last_5: float = 0.0
    
    # Streak
    current_streak: str = ""  # W3, L2, D1
    
    # Trend
    form_trend: str = "STABLE"  # UP, DOWN, STABLE
    
    @property
    def form_delta_pct(self) -> float:
        """% différence forme récente vs saison"""
        if self.ppg_season > 0:
            return ((self.ppg_last_5 - self.ppg_season) / self.ppg_season) * 100
        return 0.0


@dataclass 
class ContextDNA:
    """Contexte tactique"""
    formation: str = "4-3-3"
    ppda: float = 10.0  # Passes allowed per defensive action
    
    # xG
    xg_total: float = 0.0
    xg_per_90: float = 0.0
    goals_scored: int = 0
    
    # Efficiency
    conversion_rate: float = 0.0  # Goals / xG
    
    @property
    def attacking_luck(self) -> float:
        """Goals - xG : positif = clinical, négatif = wasteful"""
        return self.goals_scored - self.xg_total


@dataclass
class ExploitableMarket:
    """Un marché exploitable pour cette équipe"""
    market: str
    action: str  # BACK ou FADE
    edge_type: str  # REGRESSION, LUCK, HOME_AWAY, TIMING, FORM
    confidence: str  # HIGH, MEDIUM, LOW
    description: str
    data: Dict = field(default_factory=dict)


@dataclass
class UnifiedTeamDNA:
    """
    ═══════════════════════════════════════════════════════════════════════════════
    ADN UNIQUE - L'empreinte digitale complète d'une équipe
    ═══════════════════════════════════════════════════════════════════════════════
    
    Chaque équipe a UN SEUL ADN qui définit:
    - Son identité défensive
    - Son profil gardien
    - Son momentum
    - Son contexte tactique
    - Ses marchés EXPLOITABLES (conséquence de l'ADN)
    """
    
    # Identity
    team_name: str
    league: str = ""
    
    # DNA Components
    defense: DefenseDNA = field(default_factory=DefenseDNA)
    goalkeeper: GoalkeeperDNA = field(default_factory=GoalkeeperDNA)
    momentum: MomentumDNA = field(default_factory=MomentumDNA)
    context: ContextDNA = field(default_factory=ContextDNA)
    
    # Fingerprint
    fingerprint: str = ""
    
    # Quality
    data_quality_score: int = 100
    
    # Exploitable markets (CONSEQUENCE of DNA)
    exploitable_markets: List[ExploitableMarket] = field(default_factory=list)
    
    @property
    def narrative(self) -> str:
        """
        Génère un profil narratif UNIQUE pour cette équipe.
        Chaque équipe a son histoire, ses forces, ses faiblesses.
        """
        lines = []
        lines.append(f"═══ {self.team_name.upper()} ═══")
        lines.append(f"League: {self.league}")
        lines.append(f"Fingerprint: {self.fingerprint}")
        lines.append("")
        
        # Defense narrative
        if self.defense.defensive_profile == "ELITE":
            lines.append(f"🛡️ DÉFENSE ELITE: Seulement {self.defense.xga_per_90:.2f} xGA/90")
        elif self.defense.defensive_profile == "CATASTROPHIC":
            lines.append(f"⚠️ DÉFENSE CATASTROPHIQUE: {self.defense.xga_per_90:.2f} xGA/90")
        else:
            lines.append(f"🛡️ Défense {self.defense.defensive_profile}: {self.defense.xga_per_90:.2f} xGA/90")
        
        # Home/Away
        if self.defense.home_away_ratio > 1.8:
            lines.append(f"🏠 HOME FORTRESS: {self.defense.home_away_ratio:.1f}x plus solide à domicile")
            lines.append(f"   → Home CS%: {self.defense.home_cs_pct:.0f}% vs Away: {self.defense.away_cs_pct:.0f}%")
        elif self.defense.home_away_ratio < 0.7:
            lines.append(f"✈️ ROAD WARRIOR: Meilleur à l'extérieur!")
        
        # Timing vulnerabilities
        if self.defense.timing.weak_periods:
            lines.append(f"⏰ VULNÉRABLE: {', '.join(self.defense.timing.weak_periods)} min")
        if "FADES_LATE" in self.defense.timing.timing_profile:
            lines.append(f"😰 FADE LATE: {self.defense.timing.late_pct:.0f}% des xGA après 76'")
        if "FINISHES_STRONG" in self.defense.timing.timing_profile:
            lines.append(f"💪 FINIT FORT: Seulement {self.defense.timing.late_pct:.0f}% des xGA après 76'")
        
        # Luck factor
        luck = self.defense.luck_factor
        if luck > 4:
            lines.append(f"🍀 CHANCEUX: +{luck:.1f} buts évités vs xGA (régression attendue)")
        elif luck < -4:
            lines.append(f"😢 MALCHANCEUX: {luck:.1f} buts de plus que xGA (rebond attendu)")
        
        # Goalkeeper
        lines.append(f"\n🧤 GK: {self.goalkeeper.name} ({self.goalkeeper.quality_tier})")
        lines.append(f"   Goals prevented: {self.goalkeeper.goals_prevented:+.1f}")
        if self.goalkeeper.sr_late < 60:
            lines.append(f"   ⚠️ Faible en fin de match: {self.goalkeeper.sr_late:.0f}% SR 76-90'")
        
        # Momentum
        lines.append(f"\n📈 FORME: {self.momentum.form_last_5} ({self.momentum.points_last_5} pts)")
        if self.momentum.form_delta_pct > 25:
            lines.append(f"   🔥 EN FEU: +{self.momentum.form_delta_pct:.0f}% vs moyenne saison")
        elif self.momentum.form_delta_pct < -25:
            lines.append(f"   📉 EN CHUTE: {self.momentum.form_delta_pct:.0f}% vs moyenne saison")
        
        # Context
        lines.append(f"\n⚽ ATTAQUE: {self.context.xg_per_90:.2f} xG/90, {self.context.conversion_rate:.0f}% conversion")
        if self.context.attacking_luck > 3:
            lines.append(f"   🎯 CLINICAL: +{self.context.attacking_luck:.1f} buts vs xG")
        elif self.context.attacking_luck < -3:
            lines.append(f"   😤 WASTEFUL: {self.context.attacking_luck:.1f} buts vs xG")
        
        # Exploitable markets
        if self.exploitable_markets:
            lines.append(f"\n💰 MARCHÉS EXPLOITABLES ({len(self.exploitable_markets)}):")
            for m in self.exploitable_markets[:5]:
                conf_emoji = "🔥" if m.confidence == "HIGH" else "📊"
                lines.append(f"   {conf_emoji} {m.action} {m.market}: {m.description}")
        
        return "\n".join(lines)
    
    def get_markets_for_matchup(self, opponent: 'UnifiedTeamDNA', is_home: bool) -> List[ExploitableMarket]:
        """
        Retourne les marchés exploitables POUR CE MATCH SPÉCIFIQUE
        basés sur l'interaction des deux ADN.
        """
        markets = []
        
        # Home advantage
        if is_home and self.defense.home_away_ratio > 1.5:
            markets.append(ExploitableMarket(
                market="Clean Sheet",
                action="BACK",
                edge_type="HOME_AWAY",
                confidence="HIGH" if self.defense.home_away_ratio > 2 else "MEDIUM",
                description=f"HOME FORTRESS: {self.defense.home_cs_pct:.0f}% CS à domicile",
                data={"home_cs_pct": self.defense.home_cs_pct}
            ))
        
        # Late goals
        if "FADES_LATE" in self.defense.timing.timing_profile:
            if opponent.context.xg_per_90 > 1.3:
                markets.append(ExploitableMarket(
                    market="Goal 76-90",
                    action="BACK",
                    edge_type="TIMING",
                    confidence="HIGH",
                    description=f"{self.team_name} FADES LATE vs attaque forte",
                    data={"late_pct": self.defense.timing.late_pct}
                ))
        
        # Goalkeeper weakness
        if self.goalkeeper.quality_tier in ["WEAK", "LIABILITY"]:
            markets.append(ExploitableMarket(
                market="Over Goals",
                action="BACK",
                edge_type="GOALKEEPER",
                confidence="MEDIUM",
                description=f"GK {self.goalkeeper.name} = {self.goalkeeper.quality_tier}",
                data={"goals_prevented": self.goalkeeper.goals_prevented}
            ))
        
        return markets


# ═══════════════════════════════════════════════════════════════════════════════
# LOADER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _load_json(path: Path) -> Optional[dict]:
    """Charge un fichier JSON"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Erreur chargement {path.name}: {e}")
        return None


def _parse_defense(raw: dict, goals_against: int = 0) -> DefenseDNA:
    """Parse les données defense_dna"""
    timing = TimingDNA(
        xga_0_15=raw.get("xga_0_15", 0),
        xga_16_30=raw.get("xga_16_30", 0),
        xga_31_45=raw.get("xga_31_45", 0),
        xga_46_60=raw.get("xga_46_60", 0),
        xga_61_75=raw.get("xga_61_75", 0),
        xga_76_90=raw.get("xga_76_90", 0),
        early_pct=raw.get("xga_early_pct", 0),
        late_pct=raw.get("xga_late_pct", 0),
        first_half_pct=raw.get("first_half_pct", 50),
        second_half_pct=raw.get("second_half_pct", 50),
        timing_profile=raw.get("timing_profile", "CONSISTENT"),
    )
    
    
    return DefenseDNA(
        xga_total=raw.get("xga_total", 0),
        xga_per_90=raw.get("xga_per_90", 0),
        goals_against=goals_against if goals_against else raw.get("goals_against", 0),
        clean_sheet_pct=raw.get("clean_sheet_pct", 0),
        xga_box=raw.get("xga_box", 0),
        xga_outside_box=raw.get("xga_outside_box", 0),
        xga_set_piece=raw.get("xga_set_piece", 0),
        xga_open_play=raw.get("xga_open_play", 0),
        home_xga_per_90=raw.get("xga_per_90_home", 0),
        away_xga_per_90=raw.get("xga_per_90_away", 0),
        home_cs_pct=raw.get("cs_pct_home", 0),
        away_cs_pct=raw.get("cs_pct_away", 0),
        resist_late=raw.get("resist_late", 50),
        resist_set_piece=raw.get("resist_set_piece", 50),
        timing=timing,
        defensive_profile=raw.get("defense_profile", raw.get("defensive_profile", "AVERAGE")),
    )


def _parse_goalkeeper(raw: dict) -> GoalkeeperDNA:
    """Parse les données goalkeeper_dna"""
    difficulty = raw.get("difficulty_analysis", {})
    timing = raw.get("timing_analysis", {})
    situation = raw.get("situation_analysis", {})
    periods = timing.get("periods", {})
    
    # Calculate late SR from periods
    late_period = periods.get("76-90", {}) or periods.get("75+", {})
    sr_late = late_period.get("save_rate", 0) if isinstance(late_period, dict) else 0
    
    # First/second half
    first_half_periods = ["0-15", "16-30", "31-45"]
    second_half_periods = ["46-60", "61-75", "76-90", "75+"]
    
    sr_first = 0
    sr_second = 0
    count_first = 0
    count_second = 0
    
    for p, data in periods.items():
        if isinstance(data, dict):
            sr = data.get("save_rate", 0)
            if any(x in p for x in first_half_periods):
                sr_first += sr
                count_first += 1
            elif any(x in p for x in second_half_periods):
                sr_second += sr
                count_second += 1
    
    sr_first_half = sr_first / count_first if count_first > 0 else 0
    sr_second_half = sr_second / count_second if count_second > 0 else 0
    
    # Difficulty
    easy = difficulty.get("easy", {})
    hard = difficulty.get("hard", {})
    
    # Situations
    open_play = situation.get("open_play", {})
    corners = situation.get("corners", {})
    penalties = situation.get("penalties", {})
    
    # Goals prevented = xGA - GA (approximation via gk_performance score)
    gk_score = raw.get("gk_performance", 0)
    goals_prevented = gk_score  # gk_performance IS goals prevented  # Approximate: score 0.5 = ~2.5 goals prevented
    
    return GoalkeeperDNA(
        name=raw.get("goalkeeper", "Unknown"),
        save_rate=raw.get("save_rate", 0),
        goals_prevented=goals_prevented,
        avg_shot_difficulty=0,  # Not directly available
        high_difficulty_sr=hard.get("sr", 0) if isinstance(hard, dict) else 0,
        low_difficulty_sr=easy.get("sr", 0) if isinstance(easy, dict) else 0,
        sr_first_half=sr_first_half,
        sr_second_half=sr_second_half,
        sr_late=sr_late,
        sr_open_play=open_play.get("sr", 0) if isinstance(open_play, dict) else 0,
        sr_set_piece=corners.get("sr", 0) if isinstance(corners, dict) else 0,
        sr_penalty=penalties.get("sr", 0) if isinstance(penalties, dict) else 0,
    )


def _parse_context(raw: dict) -> Tuple[ContextDNA, MomentumDNA, str]:
    """Parse les données context_dna"""
    history = raw.get("history", {})
    record = raw.get("record", {})
    mom = raw.get("momentum_dna", {})
    ctx = raw.get("context_dna", {})
    
    # Context
    matches = record.get("matches") or 15  # Handle None
    goals = record.get("goals_for", 0)
    xg = history.get("xg", 0)
    
    context = ContextDNA(
        formation=ctx.get("formation", {}).get("primary", "4-3-3"),
        ppda=history.get("ppda", 10),
        xg_total=xg,
        xg_per_90=xg / matches if matches > 0 else 0,
        goals_scored=goals,
        conversion_rate=(goals / xg * 100) if xg > 0 else 0,
    )
    
    # Momentum
    pts_l5 = mom.get("points_last_5", 0)
    pts_season = record.get("points", 0)
    ppg_season = pts_season / matches if matches > 0 else 0
    ppg_l5 = pts_l5 / 5
    
    # Trend
    if ppg_l5 > ppg_season * 1.25:
        trend = "UP"
    elif ppg_l5 < ppg_season * 0.75:
        trend = "DOWN"
    else:
        trend = "STABLE"
    
    momentum = MomentumDNA(
        form_last_5=mom.get("form_last_5", "-----"),
        points_last_5=pts_l5,
        ppg_season=ppg_season,
        ppg_last_5=ppg_l5,
        current_streak=mom.get("current_streak", ""),
        form_trend=trend,
    )
    
    league = raw.get("league", "")
    
    return context, momentum, league


def _generate_exploitable_markets(dna: UnifiedTeamDNA) -> List[ExploitableMarket]:
    """
    Génère les marchés exploitables basés sur l'ADN de l'équipe.
    
    PHILOSOPHIE: L'ADN → Marchés (pas l'inverse!)
    """
    markets = []
    
    # 1. LUCK: Régression attendue
    if dna.defense.luck_factor > 4:
        markets.append(ExploitableMarket(
            market="Clean Sheet",
            action="FADE",
            edge_type="LUCK",
            confidence="HIGH" if dna.defense.luck_factor > 6 else "MEDIUM",
            description=f"+{dna.defense.luck_factor:.1f} buts chanceux → régression",
            data={"luck": dna.defense.luck_factor}
        ))
    elif dna.defense.luck_factor < -4:
        markets.append(ExploitableMarket(
            market="Clean Sheet",
            action="BACK",
            edge_type="LUCK",
            confidence="HIGH" if dna.defense.luck_factor < -6 else "MEDIUM",
            description=f"{dna.defense.luck_factor:.1f} buts malchanceux → rebond",
            data={"luck": dna.defense.luck_factor}
        ))
    
    # 2. HOME_AWAY: Fortress ou Road Warrior
    if dna.defense.home_away_ratio > 1.5:
        markets.append(ExploitableMarket(
            market="Clean Sheet HOME",
            action="BACK",
            edge_type="HOME_AWAY",
            confidence="HIGH" if dna.defense.home_away_ratio > 2 else "MEDIUM",
            description=f"HOME FORTRESS: {dna.defense.home_cs_pct:.0f}% CS domicile",
            data={"ratio": dna.defense.home_away_ratio, "home_cs": dna.defense.home_cs_pct}
        ))
        markets.append(ExploitableMarket(
            market="Clean Sheet AWAY",
            action="FADE",
            edge_type="HOME_AWAY",
            confidence="MEDIUM",
            description=f"Vulnérable à l'extérieur: {dna.defense.away_cs_pct:.0f}% CS",
            data={"away_cs": dna.defense.away_cs_pct}
        ))
    
    # 3. TIMING: Périodes faibles
    if "FADES_LATE" in dna.defense.timing.timing_profile:
        markets.append(ExploitableMarket(
            market="Goal 76-90",
            action="BACK",
            edge_type="TIMING",
            confidence="HIGH" if dna.defense.timing.late_pct > 25 else "MEDIUM",
            description=f"FADES LATE: {dna.defense.timing.late_pct:.0f}% xGA après 76'",
            data={"late_pct": dna.defense.timing.late_pct}
        ))
    if "SLOW_STARTER" in dna.defense.timing.timing_profile:
        markets.append(ExploitableMarket(
            market="Goal 0-15",
            action="BACK",
            edge_type="TIMING",
            confidence="MEDIUM",
            description=f"SLOW STARTER: {dna.defense.timing.early_pct:.0f}% xGA 0-15'",
            data={"early_pct": dna.defense.timing.early_pct}
        ))
    
    # 4. GOALKEEPER: Faiblesse ou force
    if dna.goalkeeper.quality_tier in ["WEAK", "LIABILITY"]:
        markets.append(ExploitableMarket(
            market="Over Goals",
            action="BACK",
            edge_type="GOALKEEPER",
            confidence="HIGH" if dna.goalkeeper.quality_tier == "LIABILITY" else "MEDIUM",
            description=f"GK {dna.goalkeeper.quality_tier}: {dna.goalkeeper.goals_prevented:+.1f} prevented",
            data={"gk": dna.goalkeeper.name, "prevented": dna.goalkeeper.goals_prevented}
        ))
    elif dna.goalkeeper.quality_tier == "ELITE":
        markets.append(ExploitableMarket(
            market="Under Goals",
            action="BACK",
            edge_type="GOALKEEPER",
            confidence="MEDIUM",
            description=f"GK ELITE: {dna.goalkeeper.goals_prevented:+.1f} goals prevented",
            data={"gk": dna.goalkeeper.name, "prevented": dna.goalkeeper.goals_prevented}
        ))
    
    # 5. FORM: Momentum
    if dna.momentum.form_delta_pct > 25:
        markets.append(ExploitableMarket(
            market="Match Result",
            action="BACK",
            edge_type="FORM",
            confidence="MEDIUM",
            description=f"EN FEU: +{dna.momentum.form_delta_pct:.0f}% vs saison",
            data={"form": dna.momentum.form_last_5, "delta": dna.momentum.form_delta_pct}
        ))
    elif dna.momentum.form_delta_pct < -25:
        markets.append(ExploitableMarket(
            market="Match Result",
            action="FADE",
            edge_type="FORM",
            confidence="MEDIUM",
            description=f"EN CHUTE: {dna.momentum.form_delta_pct:.0f}% vs saison",
            data={"form": dna.momentum.form_last_5, "delta": dna.momentum.form_delta_pct}
        ))
    
    return markets


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

# Cache global
_CACHE: Dict[str, UnifiedTeamDNA] = {}
_DATA_LOADED = False


def _load_all_data() -> Tuple[dict, dict, dict, dict]:
    """Charge toutes les sources de données"""
    defense_raw = _load_json(DEFENSE_FILE) or []
    context_raw = _load_json(CONTEXT_FILE) or {}
    gk_raw = _load_json(GK_FILE) or {}
    profiles_raw = _load_json(PROFILES_FILE) or {}
    
    # Defense is LIST, convert to dict
    defense_dict = {d["team_name"]: d for d in defense_raw} if isinstance(defense_raw, list) else defense_raw
    
    return defense_dict, context_raw, gk_raw, profiles_raw


def load_team(team_name: str) -> Optional[UnifiedTeamDNA]:
    """
    Charge l'ADN complet d'une équipe.
    
    Usage:
        arsenal = load_team("Arsenal")
        print(arsenal.narrative)
        print(arsenal.exploitable_markets)
    """
    global _CACHE, _DATA_LOADED
    
    # Check cache
    if team_name in _CACHE:
        return _CACHE[team_name]
    
    # Load all data if not loaded
    if not _DATA_LOADED:
        defense_dict, context_raw, gk_raw, profiles_raw = _load_all_data()
        _DATA_LOADED = True
        
        # Build all teams
        for name in defense_dict.keys():
            # Get goals_against from context for luck calculation
            ctx_record = context_raw.get(name, {}).get("record", {})
            goals_against = ctx_record.get("goals_against", 0)
            defense = _parse_defense(defense_dict.get(name, {}), goals_against)
            goalkeeper = _parse_goalkeeper(gk_raw.get(name, {}))
            context, momentum, league = _parse_context(context_raw.get(name, {}))
            profile = profiles_raw.get(name, {})
            
            dna = UnifiedTeamDNA(
                team_name=name,
                league=league,
                defense=defense,
                goalkeeper=goalkeeper,
                momentum=momentum,
                context=context,
                fingerprint=profile.get("fingerprint", f"{defense.defensive_profile}_{defense.timing.timing_profile}"),
                data_quality_score=100,
            )
            
            # Generate exploitable markets
            dna.exploitable_markets = _generate_exploitable_markets(dna)
            
            _CACHE[name] = dna
    
    return _CACHE.get(team_name)


def load_all_teams() -> Dict[str, UnifiedTeamDNA]:
    """
    Charge l'ADN de toutes les équipes.
    
    Usage:
        all_teams = load_all_teams()
        for name, dna in all_teams.items():
            print(f"{name}: {len(dna.exploitable_markets)} marchés exploitables")
    """
    # Force load all
    load_team("Arsenal")  # Triggers full load
    return _CACHE.copy()


def clear_cache():
    """Vide le cache"""
    global _CACHE, _DATA_LOADED
    _CACHE = {}
    _DATA_LOADED = False


def get_team(team_name: str) -> Optional[UnifiedTeamDNA]:
    """Alias pour load_team"""
    return load_team(team_name)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    
    print("\n" + "="*70)
    print("   UNIFIED TEAM LOADER - CHESS ENGINE V2.0")
    print("="*70)
    
    # Load all teams
    teams = load_all_teams()
    print(f"\n✅ {len(teams)} équipes chargées")
    
    # Stats
    total_markets = sum(len(t.exploitable_markets) for t in teams.values())
    high_conf = sum(1 for t in teams.values() for m in t.exploitable_markets if m.confidence == "HIGH")
    
    print(f"💰 {total_markets} marchés exploitables détectés")
    print(f"🔥 {high_conf} HIGH CONFIDENCE")
    
    # Single team test
    team_name = sys.argv[1] if len(sys.argv) > 1 else "Arsenal"
    team = get_team(team_name)
    
    if team:
        print("\n" + team.narrative)
    else:
        print(f"\n❌ Équipe '{team_name}' non trouvée")
        print(f"   Équipes disponibles: {list(teams.keys())[:10]}...")
