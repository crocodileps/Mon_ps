"""CHAIN ENGINE - Flow Analysis"""

import sys
from pathlib import Path
from typing import Dict, Any
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.helpers import safe_get


class ChainEngine:
    def __init__(self, data_hub):
        self.data_hub = data_hub
    
    def analyze(self, home_team: str, away_team: str, matchup_data: Dict[str, Any]) -> Dict[str, Any]:
        home = matchup_data["team_a"]
        away = matchup_data["team_b"]
        
        home_offensive = self._analyze_offensive_chain(home)
        away_offensive = self._analyze_offensive_chain(away)
        home_defensive = self._analyze_defensive_chain(home)
        away_defensive = self._analyze_defensive_chain(away)
        
        home_attack_flow = home_offensive - away_defensive * 0.8
        away_attack_flow = away_offensive - home_defensive * 0.8
        
        return {
            "home_offensive": home_offensive,
            "home_defensive": home_defensive,
            "away_offensive": away_offensive,
            "away_defensive": away_defensive,
            "home_attack_flow": home_attack_flow,
            "away_attack_flow": away_attack_flow,
            "flow_differential": home_attack_flow - away_attack_flow,
        }
    
    def _analyze_offensive_chain(self, team: Dict) -> float:
        ctx = team.get("context", {})
        history = ctx.get("history", {})
        
        # Metrics offensifs
        xg_90 = history.get("xg_90", 1.2)
        npxg = history.get("npxg", 20)
        deep_90 = history.get("deep_90", 7)
        
        # Normalize (elite = 1.0)
        xg_score = min(1.0, xg_90 / 2.0)
        deep_score = min(1.0, deep_90 / 10)
        
        chain_score = xg_score * 0.6 + deep_score * 0.4
        return min(1.0, max(0.0, chain_score))
    
    def _analyze_defensive_chain(self, team: Dict) -> float:
        ctx = team.get("context", {})
        history = ctx.get("history", {})
        defense = team.get("defense", {})
        gk = team.get("goalkeeper", {})
        
        # xGA
        xga_90 = history.get("xga_90", 1.3)
        
        # GK
        gk_perf = gk.get("gk_performance", {}) if gk else {}
        save_rate = gk_perf.get("save_rate", 70) if isinstance(gk_perf, dict) else 70
        
        # Score (lower xGA = better)
        xga_score = min(1.0, 1.5 / max(xga_90, 0.5))
        gk_score = min(1.0, save_rate / 80)
        
        chain_score = xga_score * 0.6 + gk_score * 0.4
        return min(1.0, max(0.0, chain_score))
