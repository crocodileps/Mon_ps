"""VARIANCE ENGINE - Luck Detection"""

import sys
from pathlib import Path
from typing import Dict, Any, List
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.helpers import safe_get


class VarianceEngine:
    LUCKY_THRESHOLD = 0.15
    UNLUCKY_THRESHOLD = -0.15
    
    def __init__(self, data_hub):
        self.data_hub = data_hub
    
    def analyze(self, home_team: str, away_team: str, matchup_data: Dict[str, Any]) -> Dict[str, Any]:
        home = matchup_data["team_a"]
        away = matchup_data["team_b"]
        
        home_analysis = self._analyze_team(home)
        away_analysis = self._analyze_team(away)
        
        regression_edge = home_analysis["regression_factor"] - away_analysis["regression_factor"]
        
        return {
            "home_profile": home_analysis["profile"],
            "away_profile": away_analysis["profile"],
            "home_variance": home_analysis,
            "away_variance": away_analysis,
            "regression_edge": regression_edge,
        }
    
    def _analyze_team(self, team: Dict) -> Dict:
        ctx = team.get("context", {})
        variance = ctx.get("variance", {})
        history = ctx.get("history", {})
        record = ctx.get("record", {})
        
        # xG overperformance depuis variance
        xg_overperf = variance.get("xg_overperformance", 0)
        luck_index = variance.get("luck_index", 0)
        
        # Ou calculer depuis history
        if not xg_overperf and history:
            xg = history.get("xg", 20)
            goals = record.get("goals_for", 20) if record else 20
            if xg > 0:
                xg_overperf = (goals - xg) / xg
        
        # Classifier
        if xg_overperf > self.LUCKY_THRESHOLD:
            profile = "LUCKY"
            regression_factor = -xg_overperf * 0.4
        elif xg_overperf < self.UNLUCKY_THRESHOLD:
            profile = "UNLUCKY"
            regression_factor = -xg_overperf * 0.4  # Positive car underperform
        else:
            profile = "TRUE_LEVEL"
            regression_factor = 0
        
        return {
            "xg_overperformance": xg_overperf,
            "luck_index": luck_index,
            "profile": profile,
            "regression_factor": regression_factor,
        }
