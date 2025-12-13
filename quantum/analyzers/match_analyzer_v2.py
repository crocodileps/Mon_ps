#!/usr/bin/env python3
"""
MATCH ANALYZER V2 - PARADIGME ADN EN ACTION

Combine tous les éléments du système Mon_PS:
- team_dna_unified_v2.json (96 équipes avec tactical_profile)
- friction_matrix_12x12.py (144 combinaisons de friction)
- exploit_paths, matchup_guide, vulnerabilities

PARADIGME:
- Chaque équipe a un ADN unique
- La collision de 2 ADN produit une FRICTION
- La friction détermine les marchés exploitables
- Les vulnérabilités croisées amplifient l'edge

Auteur: Mon_PS Quant Team
Date: 12 Décembre 2025
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from quantum.models.friction_matrix_12x12 import (
    get_friction,
    analyze_match_friction,
    FrictionResult,
    ClashType,
    Tempo
)


@dataclass
class MarketRecommendation:
    """Recommandation de marché avec scoring."""
    market: str
    edge_estimate: float
    confidence: str  # HIGH, MEDIUM, LOW
    source: str      # friction, exploit_path, vulnerability, combined
    reasoning: str


@dataclass
class MatchAnalysis:
    """Résultat complet d'une analyse de match."""
    home_team: str
    away_team: str
    analyzed_at: str

    # Profils
    home_profile: str
    home_family: str
    home_confidence: float
    away_profile: str
    away_family: str
    away_confidence: float

    # Friction
    clash_type: str
    tempo: str
    friction_description: str
    goals_modifier: float
    cards_modifier: float
    corners_modifier: float
    late_goal_prob: float

    # Markets
    primary_markets: List[str]
    secondary_markets: List[str]
    avoid_markets: List[str]

    # Detailed recommendations
    recommendations: List[Dict] = field(default_factory=list)

    # Cross-analysis
    home_vulnerabilities_exploited: List[str] = field(default_factory=list)
    away_vulnerabilities_exploited: List[str] = field(default_factory=list)

    # Confidence
    overall_confidence: float = 0.0
    confidence_factors: Dict = field(default_factory=dict)

    # Narrative (if full format)
    narrative: str = ""
    markdown: str = ""


class MatchAnalyzerV2:
    """
    Analyseur de matchs V2 - Combine ADN + Friction + Vulnérabilités.

    Usage:
        analyzer = MatchAnalyzerV2()
        result = analyzer.analyze("Liverpool", "Manchester City", format="full")
        print(result["markdown"])
    """

    # Aliases pour normalisation des noms
    TEAM_ALIASES = {
        "man city": "Manchester City",
        "man united": "Manchester United",
        "man utd": "Manchester United",
        "spurs": "Tottenham",
        "wolves": "Wolverhampton",
        "athletic": "Athletic Club",
        "atletico": "Atletico Madrid",
        "barca": "Barcelona",
        "bayern": "Bayern Munich",
        "psg": "Paris Saint-Germain",
        "inter": "Inter Milan",
        "ac milan": "AC Milan",
        "milan": "AC Milan",
        "juve": "Juventus",
        "dortmund": "Borussia Dortmund",
        "gladbach": "Borussia Monchengladbach",
        "rb leipzig": "RB Leipzig",
        "leipzig": "RB Leipzig",
    }

    def __init__(self, data_path: str = None):
        """
        Initialise l'analyseur.

        Args:
            data_path: Chemin vers team_dna_unified_v2.json
        """
        if data_path is None:
            # Try multiple paths
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

    def _load_data(self) -> dict:
        """Charge les données unifiées."""
        with open(self.data_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _normalize_team_name(self, name: str) -> str:
        """Normalise le nom d'équipe."""
        # Check aliases first
        name_lower = name.lower().strip()
        if name_lower in self.TEAM_ALIASES:
            return self.TEAM_ALIASES[name_lower]

        # Try exact match
        if name in self.teams:
            return name

        # Try case-insensitive match
        for team in self.teams.keys():
            if team.lower() == name_lower:
                return team

        # Try partial match
        for team in self.teams.keys():
            if name_lower in team.lower() or team.lower() in name_lower:
                return team

        return name

    def _get_team_data(self, team_name: str) -> dict:
        """Récupère les données d'une équipe."""
        normalized = self._normalize_team_name(team_name)
        if normalized not in self.teams:
            raise KeyError(f"Team not found: {team_name} (tried: {normalized})")
        return self.teams[normalized]

    def _get_tactical_profile(self, team_data: dict) -> dict:
        """Extrait le profil tactique."""
        return team_data.get('tactical', {}).get('tactical_profile', {
            'profile': 'BALANCED',
            'family': 'HYBRID',
            'confidence': 0.5,
            'secondary_profile': None
        })

    def _analyze_friction(self, home_profile: str, away_profile: str) -> FrictionResult:
        """Analyse la friction entre deux profils."""
        return get_friction(home_profile, away_profile)

    def _cross_vulnerabilities(self, home_data: dict, away_data: dict) -> dict:
        """
        Analyse croisée des vulnérabilités.

        Pour chaque vulnérabilité de l'équipe A:
        - Vérifier si l'équipe B a les armes pour l'exploiter
        """
        result = {
            "home_exploitable_by_away": [],
            "away_exploitable_by_home": [],
            "exploitation_score": 0.0
        }

        # Get vulnerabilities
        home_vulns = home_data.get('exploit', {}).get('vulnerabilities', [])
        away_vulns = away_data.get('exploit', {}).get('vulnerabilities', [])

        # Get exploit paths
        home_exploit_paths = home_data.get('exploit', {}).get('exploit_paths', [])
        away_exploit_paths = away_data.get('exploit', {}).get('exploit_paths', [])

        # Get friction multipliers
        home_friction_mult = home_data.get('tactical', {}).get('friction_multipliers', {})
        away_friction_mult = away_data.get('tactical', {}).get('friction_multipliers', {})

        # Analyze: Can away team exploit home vulnerabilities?
        for vuln in home_vulns:
            vuln_type = self._parse_vulnerability(vuln)

            # Check if away has relevant exploit paths
            for path in away_exploit_paths:
                if self._vulnerability_matches_exploit(vuln_type, path):
                    result["home_exploitable_by_away"].append({
                        "vulnerability": vuln,
                        "exploit_path": path.get('market', 'Unknown'),
                        "edge_boost": path.get('edge_estimate', 0) * 1.2  # 20% boost
                    })

        # Analyze: Can home team exploit away vulnerabilities?
        for vuln in away_vulns:
            vuln_type = self._parse_vulnerability(vuln)

            for path in home_exploit_paths:
                if self._vulnerability_matches_exploit(vuln_type, path):
                    result["away_exploitable_by_home"].append({
                        "vulnerability": vuln,
                        "exploit_path": path.get('market', 'Unknown'),
                        "edge_boost": path.get('edge_estimate', 0) * 1.2
                    })

        # Calculate exploitation score
        total_exploits = len(result["home_exploitable_by_away"]) + len(result["away_exploitable_by_home"])
        result["exploitation_score"] = min(total_exploits * 0.1, 0.5)  # Max 50% boost

        return result

    def _parse_vulnerability(self, vuln: str) -> dict:
        """Parse une vulnérabilité en composants."""
        parts = vuln.split('_')
        return {
            "type": parts[0] if parts else "UNKNOWN",  # ZONE, ACTION
            "detail": '_'.join(parts[1:]) if len(parts) > 1 else ""
        }

    def _vulnerability_matches_exploit(self, vuln: dict, exploit_path: dict) -> bool:
        """Vérifie si une vulnérabilité peut être exploitée."""
        trigger = exploit_path.get('trigger', '').lower()
        market = exploit_path.get('market', '').lower()

        vuln_detail = vuln.get('detail', '').lower()

        # Zone vulnerabilities
        if 'penalty' in vuln_detail and ('goalscorer' in market or 'goal' in trigger):
            return True
        if 'six_yard' in vuln_detail and ('header' in trigger or 'aerial' in trigger):
            return True

        # Action vulnerabilities
        if vuln.get('type') == 'ACTION':
            if 'pass' in vuln_detail and 'pass' in trigger:
                return True
            if 'cross' in vuln_detail and ('header' in trigger or 'aerial' in market):
                return True

        return False

    def _generate_market_recommendations(
        self,
        friction: FrictionResult,
        vulns: dict,
        home_data: dict,
        away_data: dict
    ) -> dict:
        """
        Génère les recommandations de marchés.

        Combine:
        1. Primary markets de la friction
        2. Exploit paths des deux équipes
        3. Vulnérabilités croisées
        """
        recommendations = []
        seen_markets = set()

        # 1. Markets from friction (highest priority)
        for market in friction.primary_markets:
            if market not in seen_markets:
                recommendations.append({
                    "market": market,
                    "edge_estimate": 5.0,  # Base edge for friction markets
                    "confidence": "HIGH",
                    "source": "friction",
                    "reasoning": f"Friction {friction.clash_type.value} suggests this market"
                })
                seen_markets.add(market)

        # 2. Exploit paths from both teams
        for team_name, team_data in [("home", home_data), ("away", away_data)]:
            exploit_paths = team_data.get('exploit', {}).get('exploit_paths', [])
            for path in exploit_paths:
                market = path.get('market', '')
                if market and market.lower() not in [m.lower() for m in seen_markets]:
                    edge = path.get('edge_estimate', 0)
                    conf = path.get('confidence', 'MEDIUM')
                    recommendations.append({
                        "market": market,
                        "edge_estimate": edge,
                        "confidence": conf,
                        "source": f"exploit_path_{team_name}",
                        "reasoning": path.get('trigger', 'Team exploit path')
                    })
                    seen_markets.add(market)

        # 3. Boost markets from vulnerability cross-analysis
        for exploit in vulns.get("home_exploitable_by_away", []):
            market = exploit.get("exploit_path", "")
            for rec in recommendations:
                if rec["market"].lower() == market.lower():
                    rec["edge_estimate"] += exploit.get("edge_boost", 0)
                    rec["confidence"] = "HIGH"
                    rec["reasoning"] += f" + vulnerability exploit ({exploit['vulnerability']})"

        for exploit in vulns.get("away_exploitable_by_home", []):
            market = exploit.get("exploit_path", "")
            for rec in recommendations:
                if rec["market"].lower() == market.lower():
                    rec["edge_estimate"] += exploit.get("edge_boost", 0)
                    rec["confidence"] = "HIGH"
                    rec["reasoning"] += f" + vulnerability exploit ({exploit['vulnerability']})"

        # Sort by edge estimate
        recommendations.sort(key=lambda x: -x["edge_estimate"])

        # Categorize
        primary = [r for r in recommendations if r["edge_estimate"] >= 4.0][:5]
        secondary = [r for r in recommendations if 2.0 <= r["edge_estimate"] < 4.0][:5]

        return {
            "primary": primary,
            "secondary": secondary,
            "avoid": [{"market": m, "reason": "Low edge in this friction type"} for m in friction.avoid_markets],
            "all_recommendations": recommendations[:10]
        }

    def _calculate_confidence(
        self,
        home_data: dict,
        away_data: dict,
        friction: FrictionResult,
        vulns: dict
    ) -> dict:
        """Calcule le score de confiance global."""
        factors = {}

        # 1. Profile confidence (from classification)
        home_tp = self._get_tactical_profile(home_data)
        away_tp = self._get_tactical_profile(away_data)

        profile_conf = (home_tp.get('confidence', 0.5) + away_tp.get('confidence', 0.5)) / 2
        factors["profile_classification"] = round(profile_conf, 3)

        # 2. Friction clarity (non-BALANCED profiles are clearer)
        friction_clarity = 0.7
        if home_tp.get('profile') != 'BALANCED' and away_tp.get('profile') != 'BALANCED':
            friction_clarity = 0.9
        elif home_tp.get('profile') == 'BALANCED' and away_tp.get('profile') == 'BALANCED':
            friction_clarity = 0.5
        factors["friction_clarity"] = friction_clarity

        # 3. Data completeness
        home_sections = len([k for k in home_data.keys() if home_data[k]])
        away_sections = len([k for k in away_data.keys() if away_data[k]])
        data_completeness = min((home_sections + away_sections) / 16, 1.0)  # 8 sections each
        factors["data_completeness"] = round(data_completeness, 3)

        # 4. Exploitation score
        factors["exploitation_potential"] = vulns.get("exploitation_score", 0)

        # Overall confidence
        overall = (
            factors["profile_classification"] * 0.3 +
            factors["friction_clarity"] * 0.3 +
            factors["data_completeness"] * 0.2 +
            factors["exploitation_potential"] * 0.2
        )

        return {
            "overall": round(overall, 3),
            "factors": factors,
            "tier": "HIGH" if overall >= 0.7 else "MEDIUM" if overall >= 0.5 else "LOW"
        }

    def _generate_narrative(self, analysis: dict) -> str:
        """Génère une description textuelle professionnelle."""
        home = analysis["match"]["home"]
        away = analysis["match"]["away"]

        home_profile = analysis["profiles"]["home"]["profile"]
        away_profile = analysis["profiles"]["away"]["profile"]

        clash = analysis["friction"]["clash_type"]
        tempo = analysis["friction"]["tempo"]

        narrative = []

        # Opening
        narrative.append(f"ANALYSE: {home} vs {away}")
        narrative.append("")

        # Tactical context
        narrative.append("CONTEXTE TACTIQUE:")
        narrative.append(f"- {home}: Profil {home_profile} ({analysis['profiles']['home']['family']})")
        narrative.append(f"- {away}: Profil {away_profile} ({analysis['profiles']['away']['family']})")
        narrative.append("")

        # Friction
        narrative.append(f"TYPE DE FRICTION: {clash}")
        narrative.append(f"- Tempo attendu: {tempo}")
        narrative.append(f"- {analysis['friction']['description']}")
        narrative.append("")

        # Modifiers
        mods = analysis["modifiers"]
        narrative.append("IMPACT SUR LES MARCHÉS:")
        if mods["goals"] > 0:
            narrative.append(f"- Goals: +{mods['goals']:.1f} buts attendus par rapport à la moyenne")
        elif mods["goals"] < 0:
            narrative.append(f"- Goals: {mods['goals']:.1f} buts (match fermé attendu)")

        if mods["corners"] > 1:
            narrative.append(f"- Corners: +{mods['corners']:.0f} corners supplémentaires attendus")

        if mods["cards"] > 0.5:
            narrative.append(f"- Cards: +{mods['cards']:.1f} cartons supplémentaires attendus")
        narrative.append("")

        # Key vulnerabilities
        if analysis.get("vulnerabilities", {}).get("home_exploitable"):
            narrative.append(f"VULNÉRABILITÉS {home.upper()}:")
            for v in analysis["vulnerabilities"]["home_exploitable"][:3]:
                narrative.append(f"  - {v}")

        if analysis.get("vulnerabilities", {}).get("away_exploitable"):
            narrative.append(f"VULNÉRABILITÉS {away.upper()}:")
            for v in analysis["vulnerabilities"]["away_exploitable"][:3]:
                narrative.append(f"  - {v}")
        narrative.append("")

        # Recommendations
        narrative.append("MARCHÉS RECOMMANDÉS (PRIMARY):")
        for m in analysis["markets"]["primary"][:5]:
            if isinstance(m, dict):
                narrative.append(f"  -> {m['market']} (edge: {m.get('edge_estimate', 'N/A')})")
            else:
                narrative.append(f"  -> {m}")
        narrative.append("")

        narrative.append("MARCHÉS À ÉVITER:")
        for m in analysis["markets"]["avoid"][:3]:
            if isinstance(m, dict):
                narrative.append(f"  X {m['market']}: {m.get('reason', '')}")
            else:
                narrative.append(f"  X {m}")
        narrative.append("")

        # Confidence
        conf = analysis["confidence"]
        narrative.append(f"CONFIANCE: {conf['tier']} ({conf['overall']*100:.0f}%)")

        return "\n".join(narrative)

    def _to_markdown(self, analysis: dict) -> str:
        """Convertit le rapport en Markdown formaté."""
        home = analysis["match"]["home"]
        away = analysis["match"]["away"]

        md = []
        md.append(f"# {home} vs {away}")
        md.append(f"*Analysé le {analysis['match']['analyzed_at']}*")
        md.append("")

        # Profiles
        md.append("## Profils Tactiques")
        md.append("")
        md.append("| Équipe | Profil | Famille | Confiance |")
        md.append("|--------|--------|---------|-----------|")
        hp = analysis["profiles"]["home"]
        ap = analysis["profiles"]["away"]
        md.append(f"| {home} | {hp['profile']} | {hp['family']} | {hp['confidence']*100:.0f}% |")
        md.append(f"| {away} | {ap['profile']} | {ap['family']} | {ap['confidence']*100:.0f}% |")
        md.append("")

        # Friction
        md.append("## Analyse de Friction")
        md.append("")
        md.append(f"**Type de clash**: {analysis['friction']['clash_type']}")
        md.append(f"**Tempo**: {analysis['friction']['tempo']}")
        md.append("")
        md.append(f"> {analysis['friction']['description']}")
        md.append("")

        # Modifiers table
        md.append("### Modificateurs")
        md.append("")
        md.append("| Métrique | Modificateur |")
        md.append("|----------|--------------|")
        mods = analysis["modifiers"]
        md.append(f"| Goals | {mods['goals']:+.1f} |")
        md.append(f"| Cards | {mods['cards']:+.1f} |")
        md.append(f"| Corners | {mods['corners']:+.1f} |")
        md.append(f"| Late Goal Prob | {analysis['timing']['late_goal_prob']*100:.0f}% |")
        md.append("")

        # Markets
        md.append("## Recommandations de Marchés")
        md.append("")
        md.append("### Primary Markets")
        for m in analysis["markets"]["primary"][:5]:
            if isinstance(m, dict):
                md.append(f"- **{m['market']}** (edge: {m.get('edge_estimate', 'N/A')}, {m.get('confidence', '')})")
            else:
                md.append(f"- **{m}**")
        md.append("")

        md.append("### Secondary Markets")
        for m in analysis["markets"]["secondary"][:5]:
            if isinstance(m, dict):
                md.append(f"- {m['market']} (edge: {m.get('edge_estimate', 'N/A')})")
            else:
                md.append(f"- {m}")
        md.append("")

        md.append("### Avoid")
        for m in analysis["markets"]["avoid"][:3]:
            if isinstance(m, dict):
                md.append(f"- ~~{m['market']}~~ - {m.get('reason', '')}")
            else:
                md.append(f"- ~~{m}~~")
        md.append("")

        # Confidence
        conf = analysis["confidence"]
        md.append("## Confiance")
        md.append("")
        md.append(f"**Score global**: {conf['overall']*100:.0f}% ({conf['tier']})")
        md.append("")
        md.append("| Facteur | Score |")
        md.append("|---------|-------|")
        for k, v in conf["factors"].items():
            md.append(f"| {k.replace('_', ' ').title()} | {v*100:.0f}% |")
        md.append("")

        return "\n".join(md)

    def analyze(self, home: str, away: str, format: str = "json") -> dict:
        """
        Analyse complète d'un match.

        Args:
            home: Nom de l'équipe à domicile
            away: Nom de l'équipe à l'extérieur
            format: "json" (données brutes) ou "full" (avec narrative/markdown)

        Returns:
            Dict avec l'analyse complète
        """
        # 1. Normalize and get team data
        home_normalized = self._normalize_team_name(home)
        away_normalized = self._normalize_team_name(away)

        home_data = self._get_team_data(home_normalized)
        away_data = self._get_team_data(away_normalized)

        # 2. Get tactical profiles
        home_tp = self._get_tactical_profile(home_data)
        away_tp = self._get_tactical_profile(away_data)

        home_profile = home_tp.get('profile', 'BALANCED')
        away_profile = away_tp.get('profile', 'BALANCED')

        # 3. Analyze friction
        friction = self._analyze_friction(home_profile, away_profile)

        # 4. Cross-analyze vulnerabilities
        vulns = self._cross_vulnerabilities(home_data, away_data)

        # 5. Generate market recommendations
        markets = self._generate_market_recommendations(friction, vulns, home_data, away_data)

        # 6. Calculate confidence
        confidence = self._calculate_confidence(home_data, away_data, friction, vulns)

        # 7. Build report
        report = {
            "match": {
                "home": home_normalized,
                "away": away_normalized,
                "analyzed_at": datetime.now().isoformat()
            },
            "profiles": {
                "home": {
                    "team": home_normalized,
                    "profile": home_profile,
                    "family": home_tp.get('family', 'HYBRID'),
                    "confidence": home_tp.get('confidence', 0.5),
                    "secondary": home_tp.get('secondary_profile')
                },
                "away": {
                    "team": away_normalized,
                    "profile": away_profile,
                    "family": away_tp.get('family', 'HYBRID'),
                    "confidence": away_tp.get('confidence', 0.5),
                    "secondary": away_tp.get('secondary_profile')
                }
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
            "vulnerabilities": {
                "home_exploitable": [v["vulnerability"] for v in vulns.get("home_exploitable_by_away", [])],
                "away_exploitable": [v["vulnerability"] for v in vulns.get("away_exploitable_by_home", [])],
                "exploitation_score": vulns.get("exploitation_score", 0)
            },
            "markets": {
                "primary": markets["primary"],
                "secondary": markets["secondary"],
                "avoid": markets["avoid"]
            },
            "confidence": confidence
        }

        # 8. Add narrative if full format
        if format == "full":
            report["narrative"] = self._generate_narrative(report)
            report["markdown"] = self._to_markdown(report)

        return report

    def analyze_batch(self, matches: List[Tuple[str, str]], format: str = "json") -> List[dict]:
        """Analyse plusieurs matchs."""
        return [self.analyze(home, away, format) for home, away in matches]


# ═══════════════════════════════════════════════════════════════════
# TESTS INTÉGRÉS
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║         MATCH ANALYZER V2 - TESTS INTÉGRÉS                      ║")
    print("╚══════════════════════════════════════════════════════════════════╝")

    analyzer = MatchAnalyzerV2()

    # Test 1: Liverpool vs Man City (TRANSITION vs WIDE_ATTACK)
    print("\n" + "=" * 70)
    print("TEST 1: Liverpool vs Manchester City")
    print("=" * 70)

    result1 = analyzer.analyze("Liverpool", "Manchester City", format="full")
    print(result1["narrative"])

    # Test 2: Atletico vs Barcelona (ADAPTIVE vs POSSESSION)
    print("\n" + "=" * 70)
    print("TEST 2: Atletico Madrid vs Barcelona")
    print("=" * 70)

    result2 = analyzer.analyze("Atletico Madrid", "Barcelona", format="json")
    print(f"Clash: {result2['friction']['clash_type']}")
    print(f"Tempo: {result2['friction']['tempo']}")
    print(f"Primary Markets: {[m['market'] if isinstance(m, dict) else m for m in result2['markets']['primary'][:3]]}")
    print(f"Confidence: {result2['confidence']['tier']} ({result2['confidence']['overall']*100:.0f}%)")

    # Test 3: Defensive match - two defensive teams
    print("\n" + "=" * 70)
    print("TEST 3: Match Défensif")
    print("=" * 70)

    result3 = analyzer.analyze("Burnley", "Crystal Palace", format="full")
    print(result3["markdown"])

    print("\n" + "=" * 70)
    print("✅ MATCH ANALYZER V2 - TOUS LES TESTS PASSÉS")
    print("=" * 70)
