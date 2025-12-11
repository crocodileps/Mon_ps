"""MATCHUP ENGINE - Zone Analysis"""

import sys
from pathlib import Path
from typing import Dict, Any
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.helpers import safe_get


class MatchupEngine:
    def __init__(self, data_hub):
        self.data_hub = data_hub
    
    def analyze(self, home_team: str, away_team: str, matchup_data: Dict[str, Any]) -> Dict[str, Any]:
        home = matchup_data["team_a"]
        away = matchup_data["team_b"]
        
        zone_box = self._analyze_zone_box(home, away)
        zone_creation = self._analyze_zone_creation(home, away)
        zone_aerial = self._analyze_zone_aerial(home, away)
        zone_wide = self._analyze_zone_wide(home, away)
        zone_transition = self._analyze_zone_transition(home, away)
        
        home_attack_edge = (
            zone_box["home_edge"] * 0.40 +
            zone_creation["home_edge"] * 0.25 +
            zone_aerial["home_edge"] * 0.15 +
            zone_wide["home_edge"] * 0.10 +
            zone_transition["home_edge"] * 0.10
        )
        
        away_attack_edge = (
            zone_box["away_edge"] * 0.40 +
            zone_creation["away_edge"] * 0.25 +
            zone_aerial["away_edge"] * 0.15 +
            zone_wide["away_edge"] * 0.10 +
            zone_transition["away_edge"] * 0.10
        )
        
        home_scoring_prob = max(0.1, min(0.9, 0.5 + home_attack_edge))
        away_scoring_prob = max(0.1, min(0.9, 0.5 + away_attack_edge))
        
        home_xg = 1.2 + home_attack_edge * 1.5
        away_xg = 1.0 + away_attack_edge * 1.5
        
        return {
            "home_attack_edge": home_attack_edge,
            "away_attack_edge": away_attack_edge,
            "home_scoring_prob": home_scoring_prob,
            "away_scoring_prob": away_scoring_prob,
            "expected_home_xg": home_xg,
            "expected_away_xg": away_xg,
            "edge_summary": f"H:{home_attack_edge:+.2f} A:{away_attack_edge:+.2f}",
        }
    
    def _analyze_zone_box(self, home: Dict, away: Dict) -> Dict:
        # Home attack - données dans context.history
        home_ctx = home.get("context", {})
        home_history = home_ctx.get("history", {})
        home_npxg = home_history.get("npxg", 20) / 15  # Normaliser sur 15 matchs -> par match
        
        # Away defense
        away_ctx = away.get("context", {})
        away_history = away_ctx.get("history", {})
        away_xga = away_history.get("xga", 20) / 15
        
        # Edge: home attack vs away defense
        home_power = home_npxg / 1.5  # Normaliser (1.5 xG/match = elite)
        away_weakness = away_xga / 1.2  # 1.2 xGA/match = solide
        
        home_edge = (home_power - away_weakness) * 0.3
        away_edge = -home_edge * 0.7
        
        return {"home_edge": home_edge, "away_edge": away_edge}
    
    def _analyze_zone_creation(self, home: Dict, away: Dict) -> Dict:
        home_ctx = home.get("context", {})
        away_ctx = away.get("context", {})
        
        home_history = home_ctx.get("history", {})
        away_history = away_ctx.get("history", {})
        
        # Deep completions et PPDA
        home_deep = home_history.get("deep_90", 7)
        home_ppda = home_history.get("ppda", 10)
        
        away_deep = away_history.get("deep_90", 7)
        away_ppda = away_history.get("ppda", 10)
        
        # Home creation vs away pressing
        home_creation = home_deep / 8  # 8 deep/90 = elite
        away_pressing = 10 / max(away_ppda, 5)  # Lower PPDA = more pressing
        
        home_edge = (home_creation - away_pressing + 0.5) * 0.15
        
        # Away creation vs home pressing  
        away_creation = away_deep / 8
        home_pressing = 10 / max(home_ppda, 5)
        
        away_edge = (away_creation - home_pressing + 0.5) * 0.15
        
        return {"home_edge": home_edge, "away_edge": away_edge}
    
    def _analyze_zone_aerial(self, home: Dict, away: Dict) -> Dict:
        # Utiliser defense_dna si disponible
        home_def = home.get("defense", {})
        away_def = away.get("defense", {})
        
        home_aerial = home_def.get("aerial_won_pct", 50) if home_def else 50
        away_aerial = away_def.get("aerial_won_pct", 50) if away_def else 50
        
        diff = (home_aerial - away_aerial) / 100
        return {"home_edge": diff * 0.2, "away_edge": -diff * 0.2}
    
    def _analyze_zone_wide(self, home: Dict, away: Dict) -> Dict:
        # Avantage domicile léger sur les côtés
        return {"home_edge": 0.05, "away_edge": 0.02}
    
    def _analyze_zone_transition(self, home: Dict, away: Dict) -> Dict:
        home_ctx = home.get("context", {})
        away_ctx = away.get("context", {})
        
        home_history = home_ctx.get("history", {})
        away_history = away_ctx.get("history", {})
        
        # Pressing style influence les transitions
        home_style = home_history.get("pressing_style", "MEDIUM")
        away_style = away_history.get("pressing_style", "MEDIUM")
        
        style_scores = {"HIGH_PRESS": 0.1, "MEDIUM": 0.0, "LOW_BLOCK": -0.05}
        
        home_edge = style_scores.get(home_style, 0)
        away_edge = style_scores.get(away_style, 0) * 0.8  # Away désavantage
        
        return {"home_edge": home_edge, "away_edge": away_edge}
