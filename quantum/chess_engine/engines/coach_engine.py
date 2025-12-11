"""COACH ENGINE - Tactical Clash"""

import sys
from pathlib import Path
from typing import Dict, Any
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.helpers import safe_get


class CoachEngine:
    def __init__(self, data_hub):
        self.data_hub = data_hub
    
    def analyze(self, home_team: str, away_team: str, matchup_data: Dict[str, Any]) -> Dict[str, Any]:
        home_coach = matchup_data["team_a"].get("coach", {})
        away_coach = matchup_data["team_b"].get("coach", {})
        
        if not home_coach and not away_coach:
            return self._empty_result()
        
        # Safe get avec valeurs par défaut
        home_style = (home_coach.get("tactical_style") or "balanced").lower()
        away_style = (away_coach.get("tactical_style") or "balanced").lower()
        
        offensive_styles = ["offensive", "attacking", "possession", "high_pressing"]
        home_offensive = home_style in offensive_styles
        away_offensive = away_style in offensive_styles
        
        if home_offensive and away_offensive:
            clash_type = "OPEN_GAME"
            tactical_edge = 0.1
        elif not home_offensive and not away_offensive:
            clash_type = "TACTICAL"
            tactical_edge = 0.0
        elif home_offensive:
            clash_type = "HOME_DOMINANCE"
            tactical_edge = 0.15
        else:
            clash_type = "AWAY_COUNTER"
            tactical_edge = -0.1
        
        home_btts = home_coach.get("market_impact_btts", 0) or 0
        away_btts = away_coach.get("market_impact_btts", 0) or 0
        home_over25 = home_coach.get("market_impact_over25", 0) or 0
        away_over25 = away_coach.get("market_impact_over25", 0) or 0
        
        return {
            "tactical_clash": clash_type,
            "tactical_edge": tactical_edge,
            "pressing_clash": {"combined_intensity": 4},
            "market_impacts": {
                "btts_combined": (home_btts + away_btts) / 200,
                "over25_combined": (home_over25 + away_over25) / 200,
            }
        }
    
    def _empty_result(self) -> Dict[str, Any]:
        return {
            "tactical_clash": "UNKNOWN",
            "tactical_edge": 0,
            "pressing_clash": {"combined_intensity": 4},
            "market_impacts": {"btts_combined": 0, "over25_combined": 0}
        }
