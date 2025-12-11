"""REFEREE ENGINE - Officiating Analysis"""

import sys
from pathlib import Path
from typing import Dict, Any
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.helpers import safe_get


class RefereeEngine:
    def __init__(self, data_hub):
        self.data_hub = data_hub
    
    def analyze(self, referee_name: str, home_team: str, away_team: str) -> Dict[str, Any]:
        ref_data = self.data_hub.get_referee_data(referee_name)
        
        if not ref_data:
            return {"style": "unknown", "cards_over_prob": 0.50, "goals_modifier": 0.0}
        
        style = safe_get(ref_data, "style", "balanced")
        cards_per90 = safe_get(ref_data, "cards_per90", 4.0)
        
        if cards_per90 > 5.0:
            cards_over_prob = 0.65
        elif cards_per90 > 4.0:
            cards_over_prob = 0.55
        else:
            cards_over_prob = 0.45
        
        if style == "strict":
            goals_modifier = -0.15
        elif style == "permissive":
            goals_modifier = 0.10
        else:
            goals_modifier = 0.0
        
        return {
            "style": style,
            "cards_per90": cards_per90,
            "cards_over_prob": cards_over_prob,
            "goals_modifier": goals_modifier,
        }
