"""PATTERN ENGINE - Temporal Analysis"""

import sys
from pathlib import Path
from typing import Dict, Any, List
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.helpers import safe_get


class PatternEngine:
    def __init__(self, data_hub):
        self.data_hub = data_hub
    
    def analyze(self, home_team: str, away_team: str, matchup_data: Dict[str, Any]) -> Dict[str, Any]:
        home = matchup_data["team_a"]
        away = matchup_data["team_b"]
        
        home_timing = self._analyze_timing(home)
        away_timing = self._analyze_timing(away)
        home_momentum = self._analyze_momentum(home)
        away_momentum = self._analyze_momentum(away)
        
        timing_edge = (home_timing["late_game_power"] - away_timing["late_game_power"]) * 0.15
        momentum_edge = (home_momentum["form_score"] - away_momentum["form_score"]) * 0.2
        
        return {
            "home_timing": home_timing,
            "away_timing": away_timing,
            "home_momentum": home_momentum,
            "away_momentum": away_momentum,
            "timing_edge": timing_edge,
            "momentum_edge": momentum_edge,
            "total_pattern_edge": timing_edge + momentum_edge,
        }
    
    def _analyze_timing(self, team: Dict) -> Dict:
        ctx = team.get("context", {})
        context_dna = ctx.get("context_dna", {})
        timing = context_dna.get("timing", {})
        
        # Buts par période
        late_data = timing.get("76+", {})
        early_data = timing.get("1-15", {})
        
        late_goals = late_data.get("goals", 3)
        late_xg = late_data.get("xG", 5)
        early_goals = early_data.get("goals", 2)
        
        total_goals = sum(t.get("goals", 0) for t in timing.values()) if timing else 10
        
        late_pct = late_goals / max(total_goals, 1)
        
        if late_pct > 0.35:
            profile = "LATE_SURGE"
            late_game_power = 0.7
        elif late_pct < 0.15:
            profile = "FAST_STARTER"
            late_game_power = 0.3
        else:
            profile = "BALANCED"
            late_game_power = 0.5
        
        return {
            "late_game_power": late_game_power,
            "late_pct": late_pct,
            "profile": profile,
        }
    
    def _analyze_momentum(self, team: Dict) -> Dict:
        ctx = team.get("context", {})
        momentum_dna = ctx.get("momentum_dna", {})
        
        form_last_5 = momentum_dna.get("form_last_5", "WWDLL")
        points_last_5 = momentum_dna.get("points_last_5", 7)
        xg_last_5 = momentum_dna.get("xg_last_5", 6)
        
        # Form score basé sur les points (max 15)
        form_score = min(1.0, points_last_5 / 12)
        
        return {
            "form_last_5": form_last_5,
            "points_last_5": points_last_5,
            "form_score": form_score,
        }
