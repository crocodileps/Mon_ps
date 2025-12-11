#!/usr/bin/env python3
"""
MATCHUP ENGINE - Chess Engine V2.0
═══════════════════════════════════════════════════════════════════════════════

Analyse Team A vs Team B pour identifier les avantages exploitables.

PHILOSOPHIE:
- L'ADN de chaque équipe → confrontation → signaux de trading
- Pas de prédiction générique, mais des EDGES spécifiques au matchup

USAGE:
    from quantum.engines.matchup_engine import analyze_matchup
    
    result = analyze_matchup("Arsenal", "Liverpool", is_home=True)
    print(result.narrative)
    print(result.best_bets)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import sys
sys.path.insert(0, '/home/Mon_ps')

from quantum.loaders.unified_loader import (
    load_team, 
    UnifiedTeamDNA, 
    DefenseDNA, 
    GoalkeeperDNA,
    ExploitableMarket
)


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & DATACLASSES
# ═══════════════════════════════════════════════════════════════════════════════

class EdgeType(Enum):
    """Type d'avantage identifié"""
    TIMING = "TIMING"           # Périodes fortes/faibles
    DEFENSE = "DEFENSE"         # Qualité défensive
    GOALKEEPER = "GOALKEEPER"   # Qualité GK
    FORM = "FORM"               # Momentum
    HOME_AWAY = "HOME_AWAY"     # Avantage terrain
    LUCK = "LUCK"               # Régression attendue
    TACTICAL = "TACTICAL"       # Style de jeu
    ATTACK = "ATTACK"           # Puissance offensive


class BetAction(Enum):
    """Action recommandée"""
    STRONG_BACK = "STRONG_BACK"   # Forte conviction
    BACK = "BACK"                  # Back standard
    LEAN_BACK = "LEAN_BACK"        # Légère préférence
    SKIP = "SKIP"                  # Pas d'edge
    LEAN_FADE = "LEAN_FADE"        # Légère opposition
    FADE = "FADE"                  # Fade standard
    STRONG_FADE = "STRONG_FADE"   # Forte opposition


@dataclass
class MatchupEdge:
    """Un avantage identifié dans le matchup"""
    edge_type: EdgeType
    market: str
    action: BetAction
    team_favored: str  # Quelle équipe bénéficie
    confidence: float  # 0-100
    description: str
    data: Dict = field(default_factory=dict)
    
    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 70
    
    @property
    def emoji(self) -> str:
        if self.confidence >= 80:
            return "🔥"
        elif self.confidence >= 60:
            return "📊"
        else:
            return "📝"


@dataclass
class TimingEdge:
    """Avantage sur une période spécifique"""
    period: str  # "0-15", "76-90", etc.
    attack_strength: float  # xG de l'attaquant sur cette période
    defense_weakness: float  # xGA du défenseur sur cette période
    combined_score: float  # Score combiné
    recommendation: str


@dataclass 
class MatchupResult:
    """Résultat complet de l'analyse de matchup"""
    home_team: str
    away_team: str
    home_dna: UnifiedTeamDNA
    away_dna: UnifiedTeamDNA
    
    # Edges identifiés
    edges: List[MatchupEdge] = field(default_factory=list)
    timing_edges: List[TimingEdge] = field(default_factory=list)
    
    # Scores globaux
    home_advantage_score: float = 50.0  # 0-100, 50 = neutre
    goals_expected: float = 2.5
    
    # Meilleurs paris
    best_bets: List[MatchupEdge] = field(default_factory=list)
    
    @property
    def high_confidence_edges(self) -> List[MatchupEdge]:
        return [e for e in self.edges if e.is_high_confidence]
    
    @property
    def narrative(self) -> str:
        """Génère un résumé narratif du matchup"""
        lines = []
        lines.append(f"{'═' * 60}")
        lines.append(f"⚔️  {self.home_team} vs {self.away_team}")
        lines.append(f"{'═' * 60}")
        
        # Home advantage
        if self.home_advantage_score > 60:
            lines.append(f"🏠 Avantage {self.home_team}: {self.home_advantage_score:.0f}/100")
        elif self.home_advantage_score < 40:
            lines.append(f"✈️ Avantage {self.away_team}: {100 - self.home_advantage_score:.0f}/100")
        else:
            lines.append(f"⚖️ Match équilibré: {self.home_advantage_score:.0f}/100")
        
        lines.append(f"⚽ Goals attendus: {self.goals_expected:.1f}")
        lines.append("")
        
        # Edges par type
        if self.high_confidence_edges:
            lines.append(f"🎯 EDGES HIGH CONFIDENCE ({len(self.high_confidence_edges)}):")
            for edge in self.high_confidence_edges:
                action_str = "BACK" if "BACK" in edge.action.value else "FADE"
                lines.append(f"   {edge.emoji} {action_str} {edge.market}: {edge.description}")
        
        # Timing edges
        if self.timing_edges:
            lines.append("")
            lines.append("⏰ TIMING EDGES:")
            for te in sorted(self.timing_edges, key=lambda x: -x.combined_score)[:3]:
                lines.append(f"   {te.period}: {te.recommendation} (score: {te.combined_score:.1f})")
        
        # Best bets
        if self.best_bets:
            lines.append("")
            lines.append("💰 MEILLEURS PARIS:")
            for bet in self.best_bets[:3]:
                lines.append(f"   🔥 {bet.action.value} {bet.market} ({bet.confidence:.0f}%)")
                lines.append(f"      → {bet.description}")
        
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _analyze_defense_vs_attack(
    attacker: UnifiedTeamDNA, 
    defender: UnifiedTeamDNA,
    attacker_is_home: bool
) -> List[MatchupEdge]:
    """Analyse attaque vs défense"""
    edges = []
    
    # xG attaquant vs xGA défenseur
    attack_xg = attacker.context.xg_per_90
    defense_xga = defender.defense.xga_per_90
    
    # Ajustement home/away
    if attacker_is_home:
        # Attaquant à domicile = bonus
        attack_xg *= 1.1
        defense_xga = defender.defense.away_xga_per_90 or defense_xga
    else:
        # Attaquant à l'extérieur = malus
        attack_xg *= 0.9
        defense_xga = defender.defense.home_xga_per_90 or defense_xga
    
    expected_goals = (attack_xg + defense_xga) / 2
    
    # Edge si grande différence
    if attack_xg > defense_xga * 1.3:
        confidence = min(85, 50 + (attack_xg / defense_xga - 1) * 50)
        edges.append(MatchupEdge(
            edge_type=EdgeType.ATTACK,
            market=f"{attacker.team_name} Goals",
            action=BetAction.BACK,
            team_favored=attacker.team_name,
            confidence=confidence,
            description=f"Attaque forte ({attack_xg:.2f} xG) vs défense faible ({defense_xga:.2f} xGA)",
            data={"attack_xg": attack_xg, "defense_xga": defense_xga, "expected": expected_goals}
        ))
    elif defense_xga < attack_xg * 0.7:
        confidence = min(85, 50 + (1 - defense_xga / attack_xg) * 50)
        edges.append(MatchupEdge(
            edge_type=EdgeType.DEFENSE,
            market=f"{defender.team_name} Clean Sheet",
            action=BetAction.BACK,
            team_favored=defender.team_name,
            confidence=confidence,
            description=f"Défense solide ({defense_xga:.2f} xGA) vs attaque limitée ({attack_xg:.2f} xG)",
            data={"attack_xg": attack_xg, "defense_xga": defense_xga}
        ))
    
    return edges


def _analyze_timing_matchup(
    home: UnifiedTeamDNA,
    away: UnifiedTeamDNA
) -> List[TimingEdge]:
    """Analyse les périodes de jeu"""
    timing_edges = []
    periods = ["0-15", "16-30", "31-45", "46-60", "61-75", "76-90"]
    
    home_timing = home.defense.timing
    away_timing = away.defense.timing
    
    # Mapping période → attribut
    period_map = {
        "0-15": "xga_0_15",
        "16-30": "xga_16_30", 
        "31-45": "xga_31_45",
        "46-60": "xga_46_60",
        "61-75": "xga_61_75",
        "76-90": "xga_76_90",
    }
    
    for period in periods:
        attr = period_map[period]
        
        # Home attacking Away's defense
        away_xga_period = getattr(away_timing, attr, 0)
        home_attack_strength = home.context.xg_per_90 / 6  # Approximation par période
        
        # Away attacking Home's defense  
        home_xga_period = getattr(home_timing, attr, 0)
        away_attack_strength = away.context.xg_per_90 / 6
        
        # Score combiné pour Home scoring
        home_score = (home_attack_strength * 0.4 + away_xga_period * 0.6)
        away_score = (away_attack_strength * 0.4 + home_xga_period * 0.6)
        
        # Identifier les périodes exploitables
        if away_xga_period > away.defense.xga_per_90 / 6 * 1.3:
            timing_edges.append(TimingEdge(
                period=period,
                attack_strength=home_attack_strength,
                defense_weakness=away_xga_period,
                combined_score=home_score * 10,
                recommendation=f"BACK {home.team_name} Goal {period}"
            ))
        
        if home_xga_period > home.defense.xga_per_90 / 6 * 1.3:
            timing_edges.append(TimingEdge(
                period=period,
                attack_strength=away_attack_strength,
                defense_weakness=home_xga_period,
                combined_score=away_score * 10,
                recommendation=f"BACK {away.team_name} Goal {period}"
            ))
    
    return timing_edges


def _analyze_goalkeeper_matchup(
    attacker: UnifiedTeamDNA,
    defender: UnifiedTeamDNA,
    attacker_name: str
) -> List[MatchupEdge]:
    """Analyse GK vs attaque"""
    edges = []
    gk = defender.goalkeeper
    
    # GK faible = opportunité
    if gk.quality_tier in ["WEAK", "LIABILITY"]:
        confidence = 75 if gk.quality_tier == "LIABILITY" else 60
        edges.append(MatchupEdge(
            edge_type=EdgeType.GOALKEEPER,
            market=f"{attacker_name} Goals Over 0.5",
            action=BetAction.BACK,
            team_favored=attacker_name,
            confidence=confidence,
            description=f"GK {gk.quality_tier}: {gk.name} ({gk.goals_prevented:+.1f} prevented)",
            data={"gk": gk.name, "tier": gk.quality_tier, "prevented": gk.goals_prevented}
        ))
        
        # GK faible en fin de match
        if gk.sr_late < 60:
            edges.append(MatchupEdge(
                edge_type=EdgeType.GOALKEEPER,
                market=f"{attacker_name} Goal 76-90",
                action=BetAction.BACK,
                team_favored=attacker_name,
                confidence=70,
                description=f"GK faible late: {gk.sr_late:.0f}% SR après 76'",
                data={"sr_late": gk.sr_late}
            ))
    
    # GK fort = protection
    elif gk.quality_tier == "ELITE":
        edges.append(MatchupEdge(
            edge_type=EdgeType.GOALKEEPER,
            market=f"{defender.team_name} Clean Sheet",
            action=BetAction.LEAN_BACK,
            team_favored=defender.team_name,
            confidence=55,
            description=f"GK ELITE: {gk.name} ({gk.goals_prevented:+.1f} prevented)",
            data={"gk": gk.name, "prevented": gk.goals_prevented}
        ))
    
    return edges


def _analyze_form_matchup(
    home: UnifiedTeamDNA,
    away: UnifiedTeamDNA
) -> List[MatchupEdge]:
    """Analyse momentum des deux équipes"""
    edges = []
    
    home_delta = home.momentum.form_delta_pct
    away_delta = away.momentum.form_delta_pct
    
    # Différence de forme significative
    form_diff = home_delta - away_delta
    
    if form_diff > 30:
        edges.append(MatchupEdge(
            edge_type=EdgeType.FORM,
            market=f"{home.team_name} Win",
            action=BetAction.BACK,
            team_favored=home.team_name,
            confidence=min(75, 50 + form_diff / 2),
            description=f"Forme: {home.team_name} +{home_delta:.0f}% vs {away.team_name} {away_delta:+.0f}%",
            data={"home_delta": home_delta, "away_delta": away_delta, "diff": form_diff}
        ))
    elif form_diff < -30:
        edges.append(MatchupEdge(
            edge_type=EdgeType.FORM,
            market=f"{away.team_name} Win/Draw",
            action=BetAction.BACK,
            team_favored=away.team_name,
            confidence=min(75, 50 + abs(form_diff) / 2),
            description=f"Forme: {away.team_name} +{away_delta:.0f}% vs {home.team_name} {home_delta:+.0f}%",
            data={"home_delta": home_delta, "away_delta": away_delta, "diff": form_diff}
        ))
    
    # Équipe en chute à domicile
    if home_delta < -25 and home.defense.home_away_ratio < 1.2:
        edges.append(MatchupEdge(
            edge_type=EdgeType.FORM,
            market=f"{home.team_name} Loss",
            action=BetAction.LEAN_BACK,
            team_favored=away.team_name,
            confidence=55,
            description=f"{home.team_name} en chute ({home_delta:+.0f}%) sans avantage domicile",
            data={"delta": home_delta, "home_ratio": home.defense.home_away_ratio}
        ))
    
    return edges


def _analyze_luck_regression(
    home: UnifiedTeamDNA,
    away: UnifiedTeamDNA
) -> List[MatchupEdge]:
    """Analyse régression attendue (luck)"""
    edges = []
    
    for team, is_home in [(home, True), (away, False)]:
        luck = team.defense.luck_factor
        
        # Très chanceux → régression négative attendue
        if luck > 5:
            edges.append(MatchupEdge(
                edge_type=EdgeType.LUCK,
                market=f"{team.team_name} Concede Goal",
                action=BetAction.BACK,
                team_favored="Opponent",
                confidence=min(80, 50 + luck * 3),
                description=f"{team.team_name} chanceux: {luck:+.1f} buts évités → régression",
                data={"luck": luck, "xga": team.defense.xga_total, "ga": team.defense.goals_against}
            ))
        
        # Très malchanceux → régression positive attendue
        elif luck < -5:
            edges.append(MatchupEdge(
                edge_type=EdgeType.LUCK,
                market=f"{team.team_name} Clean Sheet",
                action=BetAction.LEAN_BACK,
                team_favored=team.team_name,
                confidence=min(70, 50 + abs(luck) * 2),
                description=f"{team.team_name} malchanceux: {luck:+.1f} buts → rebond attendu",
                data={"luck": luck}
            ))
    
    return edges


def _analyze_home_away_profiles(
    home: UnifiedTeamDNA,
    away: UnifiedTeamDNA
) -> List[MatchupEdge]:
    """Analyse profils home/away"""
    edges = []
    
    # Home fortress
    if home.defense.home_away_ratio > 1.8:
        edges.append(MatchupEdge(
            edge_type=EdgeType.HOME_AWAY,
            market=f"{home.team_name} Clean Sheet",
            action=BetAction.BACK,
            team_favored=home.team_name,
            confidence=min(80, 50 + (home.defense.home_away_ratio - 1) * 20),
            description=f"HOME FORTRESS: {home.defense.home_away_ratio:.1f}x plus solide ({home.defense.home_cs_pct:.0f}% CS)",
            data={"ratio": home.defense.home_away_ratio, "home_cs": home.defense.home_cs_pct}
        ))
    
    # Away weakness
    if away.defense.home_away_ratio > 1.8:
        # L'équipe away est faible à l'extérieur
        edges.append(MatchupEdge(
            edge_type=EdgeType.HOME_AWAY,
            market=f"{home.team_name} Goals",
            action=BetAction.BACK,
            team_favored=home.team_name,
            confidence=min(75, 50 + (away.defense.home_away_ratio - 1) * 15),
            description=f"{away.team_name} vulnérable away: {away.defense.away_xga_per_90:.2f} xGA/90 ({away.defense.away_cs_pct:.0f}% CS)",
            data={"away_xga": away.defense.away_xga_per_90, "away_cs": away.defense.away_cs_pct}
        ))
    
    return edges


def _calculate_expected_goals(
    home: UnifiedTeamDNA,
    away: UnifiedTeamDNA
) -> float:
    """Calcule les buts attendus"""
    # Home attacking
    home_xg = home.context.xg_per_90 * 1.1  # Home bonus
    away_defense = away.defense.away_xga_per_90 or away.defense.xga_per_90
    home_expected = (home_xg + away_defense) / 2
    
    # Away attacking
    away_xg = away.context.xg_per_90 * 0.9  # Away malus
    home_defense = home.defense.home_xga_per_90 or home.defense.xga_per_90
    away_expected = (away_xg + home_defense) / 2
    
    return home_expected + away_expected


def _calculate_home_advantage_score(
    home: UnifiedTeamDNA,
    away: UnifiedTeamDNA
) -> float:
    """Score d'avantage domicile (0-100, 50 = neutre)"""
    score = 50.0
    
    # Home fortress bonus
    if home.defense.home_away_ratio > 1.5:
        score += (home.defense.home_away_ratio - 1) * 10
    
    # Form comparison
    form_diff = home.momentum.form_delta_pct - away.momentum.form_delta_pct
    score += form_diff / 5
    
    # Defense comparison
    defense_diff = away.defense.xga_per_90 - home.defense.xga_per_90
    score += defense_diff * 10
    
    # Attack comparison
    attack_diff = home.context.xg_per_90 - away.context.xg_per_90
    score += attack_diff * 10
    
    # GK comparison
    gk_diff = home.goalkeeper.goals_prevented - away.goalkeeper.goals_prevented
    score += gk_diff * 2
    
    return max(0, min(100, score))


def _select_best_bets(edges: List[MatchupEdge]) -> List[MatchupEdge]:
    """Sélectionne les meilleurs paris"""
    # Trier par confidence
    sorted_edges = sorted(edges, key=lambda x: -x.confidence)
    
    # Prendre les 3 meilleurs avec confidence > 60
    best = [e for e in sorted_edges if e.confidence >= 60][:3]
    
    return best


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_matchup(
    home_team: str,
    away_team: str,
    verbose: bool = False
) -> Optional[MatchupResult]:
    """
    Analyse complète d'un matchup.
    
    Args:
        home_team: Nom de l'équipe à domicile
        away_team: Nom de l'équipe à l'extérieur
        verbose: Affiche le narrative si True
    
    Returns:
        MatchupResult avec tous les edges identifiés
    
    Usage:
        result = analyze_matchup("Arsenal", "Liverpool")
        print(result.narrative)
        for bet in result.best_bets:
            print(f"{bet.action} {bet.market}: {bet.confidence}%")
    """
    # Load teams
    home = load_team(home_team)
    away = load_team(away_team)
    
    if not home:
        print(f"❌ Équipe '{home_team}' non trouvée")
        return None
    if not away:
        print(f"❌ Équipe '{away_team}' non trouvée")
        return None
    
    # Collect all edges
    edges = []
    
    # 1. Defense vs Attack (both directions)
    edges.extend(_analyze_defense_vs_attack(home, away, attacker_is_home=True))
    edges.extend(_analyze_defense_vs_attack(away, home, attacker_is_home=False))
    
    # 2. Goalkeeper analysis
    edges.extend(_analyze_goalkeeper_matchup(home, away, home.team_name))
    edges.extend(_analyze_goalkeeper_matchup(away, home, away.team_name))
    
    # 3. Form/momentum
    edges.extend(_analyze_form_matchup(home, away))
    
    # 4. Luck regression
    edges.extend(_analyze_luck_regression(home, away))
    
    # 5. Home/Away profiles
    edges.extend(_analyze_home_away_profiles(home, away))
    
    # 6. Timing analysis
    timing_edges = _analyze_timing_matchup(home, away)
    
    # Calculate scores
    expected_goals = _calculate_expected_goals(home, away)
    home_advantage = _calculate_home_advantage_score(home, away)
    
    # Select best bets
    best_bets = _select_best_bets(edges)
    
    result = MatchupResult(
        home_team=home_team,
        away_team=away_team,
        home_dna=home,
        away_dna=away,
        edges=edges,
        timing_edges=timing_edges,
        home_advantage_score=home_advantage,
        goals_expected=expected_goals,
        best_bets=best_bets
    )
    
    if verbose:
        print(result.narrative)
    
    return result


def quick_matchup(home_team: str, away_team: str) -> None:
    """Version rapide qui affiche juste le narrative"""
    result = analyze_matchup(home_team, away_team, verbose=True)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("   MATCHUP ENGINE - Chess Engine V2.0")
    print("=" * 60)
    
    if len(sys.argv) >= 3:
        home = sys.argv[1]
        away = sys.argv[2]
        result = analyze_matchup(home, away, verbose=True)
    else:
        # Demo
        print("\n🎯 DEMO: Arsenal vs Liverpool\n")
        result = analyze_matchup("Arsenal", "Liverpool", verbose=True)
        
        print("\n" + "=" * 60)
        print("\n🎯 DEMO: Eintracht Frankfurt vs Bayern Munich\n")
        result2 = analyze_matchup("Eintracht Frankfurt", "Bayern Munich", verbose=True)
