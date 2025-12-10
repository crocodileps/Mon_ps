#!/usr/bin/env python3
"""
🎯 SET_PIECE AGENT V1.1 - QUANTITATIVE EDGE DETECTION
"""

import json
import logging
import math
import statistics
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_DIR = Path("/home/Mon_ps/data")
FOOTBALL_DATA_DIR = DATA_DIR / "football_data"
GOAL_ANALYSIS_DIR = DATA_DIR / "goal_analysis"

FD_TO_GOALS_MAPPING = {
    'Man City': 'Manchester City',
    'Man United': 'Manchester United',
    'Ath Bilbao': 'Athletic Club',
    'Ath Madrid': 'Atletico Madrid',
    'Leverkusen': 'Bayer Leverkusen',
    'Dortmund': 'Borussia Dortmund',
    "M'gladbach": 'Borussia Monchengladbach',
    'Paris SG': 'Paris Saint-Germain',
    'Betis': 'Real Betis',
    'Sociedad': 'Real Sociedad',
    'Valladolid': 'Real Valladolid',
    'Inter': 'Inter Milan',
    'Milan': 'AC Milan',
    'Wolves': 'Wolverhampton Wanderers',
    'Spurs': 'Tottenham',
    'Newcastle': 'Newcastle United',
    "Nott'm Forest": 'Nottingham Forest',
    'West Ham': 'West Ham United',
}

class SignalStrength(Enum):
    STRONG = "STRONG"
    MEDIUM = "MEDIUM"
    WEAK = "WEAK"
    NEUTRAL = "NEUTRAL"

class MarketType(Enum):
    OVER_CORNERS = "over_corners"
    UNDER_CORNERS = "under_corners"
    CORNER_MATCH_BET = "corner_match_bet"
    HEADER_GOAL = "header_goal"

@dataclass
class SetPieceSignal:
    market: MarketType
    team: str
    opponent: str
    direction: str
    strength: SignalStrength
    confidence: float
    edge_pct: float
    reasoning: List[str]
    metrics: Dict[str, float]

class SetPieceDataLoader:
    def __init__(self):
        self.team_stats: Dict[str, dict] = {}
        self.goals_data: List[dict] = []
        self.matches_data: List[dict] = []
        
    def load_all(self) -> bool:
        logger.info("📥 Loading SET_PIECE data sources...")
        try:
            with open(FOOTBALL_DATA_DIR / "team_stats_football_data_2526.json") as f:
                self.team_stats = json.load(f)
            logger.info(f"   ✅ {len(self.team_stats)} teams loaded")
            
            goals_file = GOAL_ANALYSIS_DIR / "all_goals_2025.json"
            if goals_file.exists():
                with open(goals_file) as f:
                    self.goals_data = json.load(f)
                logger.info(f"   ✅ {len(self.goals_data)} goals loaded")
            
            with open(FOOTBALL_DATA_DIR / "matches_all_leagues_2526.json") as f:
                self.matches_data = json.load(f)
            logger.info(f"   ✅ {len(self.matches_data)} matches loaded")
            return True
        except Exception as e:
            logger.error(f"❌ Error loading data: {e}")
            return False
    
    def _normalize_team_name(self, fd_name: str) -> str:
        return FD_TO_GOALS_MAPPING.get(fd_name, fd_name)
    
    def get_team_goals_profile(self, team_name: str) -> Dict:
        goals_name = self._normalize_team_name(team_name)
        team_goals = [g for g in self.goals_data if g.get('scoring_team') == goals_name]
        if not team_goals and goals_name != team_name:
            team_goals = [g for g in self.goals_data if g.get('scoring_team') == team_name]
        if not team_goals:
            return {'total': 0, 'header_pct': 15.0, 'corner_pct': 15.0, 'setpiece_pct': 20.0, 'mapped': False}
        total = len(team_goals)
        headers = sum(1 for g in team_goals if g.get('shot_type') == 'Head')
        from_corner = sum(1 for g in team_goals if g.get('situation') == 'FromCorner')
        set_pieces = sum(1 for g in team_goals if g.get('situation') in ['FromCorner', 'SetPiece', 'DirectFreekick'])
        return {
            'total': total,
            'header_pct': round(headers / total * 100, 1) if total > 0 else 15.0,
            'corner_pct': round(from_corner / total * 100, 1) if total > 0 else 15.0,
            'setpiece_pct': round(set_pieces / total * 100, 1) if total > 0 else 20.0,
            'mapped': True, 'goals_name': goals_name,
        }

class SetPieceFeatureEngineer:
    def __init__(self, data_loader: SetPieceDataLoader):
        self.loader = data_loader
        self.league_benchmarks = self._calculate_league_benchmarks()
    
    def _calculate_league_benchmarks(self) -> Dict[str, Dict]:
        benchmarks = {}
        for league in ['EPL', 'Bundesliga', 'Serie_A', 'La_Liga', 'Ligue_1']:
            league_teams = [s for t, s in self.loader.team_stats.items() if s.get('league') == league]
            if not league_teams: continue
            corners_for = [t['corners_for_avg'] for t in league_teams]
            corners_against = [t['corners_against_avg'] for t in league_teams]
            benchmarks[league] = {
                'corners_for_mean': statistics.mean(corners_for),
                'corners_for_std': statistics.stdev(corners_for) if len(corners_for) > 1 else 1,
                'corners_against_mean': statistics.mean(corners_against),
                'corners_against_std': statistics.stdev(corners_against) if len(corners_against) > 1 else 1,
            }
        return benchmarks
    
    def calculate_offensive_aerial_power(self, team_name: str) -> float:
        stats = self.loader.team_stats.get(team_name, {})
        goals_profile = self.loader.get_team_goals_profile(team_name)
        league = stats.get('league', 'EPL')
        benchmark = self.league_benchmarks.get(league, {'corners_for_mean': 5, 'corners_for_std': 1})
        corners_for = stats.get('corners_for_avg', 5.0)
        corners_z = (corners_for - benchmark['corners_for_mean']) / benchmark['corners_for_std']
        header_z = (goals_profile['header_pct'] - 15) / 8
        corner_z = (goals_profile['corner_pct'] - 15) / 8
        combined_z = (corners_z * 0.4) + (header_z * 0.35) + (corner_z * 0.25)
        return round(max(0, min(100, 50 + combined_z * 20)), 1)
    
    def calculate_defensive_aerial_weakness(self, team_name: str) -> float:
        stats = self.loader.team_stats.get(team_name, {})
        league = stats.get('league', 'EPL')
        benchmark = self.league_benchmarks.get(league, {'corners_against_mean': 5, 'corners_against_std': 1})
        corners_against = stats.get('corners_against_avg', 5.0)
        corners_z = (corners_against - benchmark['corners_against_mean']) / benchmark['corners_against_std']
        return round(max(0, min(100, 50 + corners_z * 20)), 1)
    
    def calculate_corner_matchup_edge(self, home_team: str, away_team: str) -> Dict:
        home_stats = self.loader.team_stats.get(home_team, {})
        away_stats = self.loader.team_stats.get(away_team, {})
        home_for = home_stats.get('corners_for_avg', 5.0)
        home_against = home_stats.get('corners_against_avg', 5.0)
        away_for = away_stats.get('corners_for_avg', 5.0)
        away_against = away_stats.get('corners_against_avg', 5.0)
        home_expected = (home_for * 1.1 + away_against) / 2
        away_expected = (away_for * 0.9 + home_against) / 2
        total_expected = home_expected + away_expected
        edges = {}
        for line in [8.5, 9.5, 10.5, 11.5]:
            prob_over = self._prob_over_poisson(total_expected, line)
            fair_odds = 1 / prob_over if prob_over > 0.01 else 50
            edges[f"over_{line}"] = {'probability': round(prob_over * 100, 1), 'fair_odds': round(fair_odds, 2)}
        return {'home_expected': round(home_expected, 2), 'away_expected': round(away_expected, 2),
                'total_expected': round(total_expected, 2), 'home_corner_edge': round(home_expected - away_expected, 2), 'edges': edges}
    
    def _prob_over_poisson(self, expected: float, line: float) -> float:
        prob_under = sum((expected ** k) * math.exp(-expected) / math.factorial(k) for k in range(int(line) + 1))
        return 1 - prob_under

class SetPieceSignalGenerator:
    CORNER_OVER_THRESHOLD = 60
    CORNER_UNDER_THRESHOLD = 40
    CORNER_MATCH_EDGE_THRESHOLD = 0.8
    HEADER_EDGE_THRESHOLD = 20
    
    def __init__(self, feature_engineer: SetPieceFeatureEngineer):
        self.engineer = feature_engineer
        
    def analyze_matchup(self, home_team: str, away_team: str) -> List[SetPieceSignal]:
        signals = []
        corner_edge = self.engineer.calculate_corner_matchup_edge(home_team, away_team)
        home_oap = self.engineer.calculate_offensive_aerial_power(home_team)
        away_oap = self.engineer.calculate_offensive_aerial_power(away_team)
        home_daw = self.engineer.calculate_defensive_aerial_weakness(home_team)
        away_daw = self.engineer.calculate_defensive_aerial_weakness(away_team)
        
        over_95 = corner_edge['edges'].get('over_9.5', {})
        prob = over_95.get('probability', 50)
        if prob >= self.CORNER_OVER_THRESHOLD:
            strength = SignalStrength.STRONG if prob >= 70 else SignalStrength.MEDIUM
            signals.append(SetPieceSignal(market=MarketType.OVER_CORNERS, team=home_team, opponent=away_team,
                direction="OVER 9.5", strength=strength, confidence=prob, edge_pct=round(prob - 50, 1),
                reasoning=[f"Expected: {corner_edge['total_expected']:.1f}", f"P(Over 9.5): {prob:.1f}%"],
                metrics={'total_expected': corner_edge['total_expected'], 'probability': prob}))
        elif prob <= self.CORNER_UNDER_THRESHOLD:
            strength = SignalStrength.STRONG if prob <= 30 else SignalStrength.MEDIUM
            signals.append(SetPieceSignal(market=MarketType.UNDER_CORNERS, team=home_team, opponent=away_team,
                direction="UNDER 9.5", strength=strength, confidence=100-prob, edge_pct=round(50 - prob, 1),
                reasoning=[f"Expected: {corner_edge['total_expected']:.1f}", f"P(Under 9.5): {100-prob:.1f}%"],
                metrics={'total_expected': corner_edge['total_expected'], 'probability': 100-prob}))
        
        home_edge = corner_edge['home_corner_edge']
        if abs(home_edge) >= self.CORNER_MATCH_EDGE_THRESHOLD:
            direction = "HOME" if home_edge > 0 else "AWAY"
            strength = SignalStrength.STRONG if abs(home_edge) >= 1.5 else SignalStrength.MEDIUM
            signals.append(SetPieceSignal(market=MarketType.CORNER_MATCH_BET,
                team=home_team if home_edge > 0 else away_team, opponent=away_team if home_edge > 0 else home_team,
                direction=direction, strength=strength, confidence=round(55 + abs(home_edge) * 5, 1),
                edge_pct=round(abs(home_edge) * 5, 1),
                reasoning=[f"Home exp: {corner_edge['home_expected']:.1f}", f"Away exp: {corner_edge['away_expected']:.1f}"],
                metrics={'home_expected': corner_edge['home_expected'], 'away_expected': corner_edge['away_expected']}))
        
        home_header_edge = (home_oap - 50) + (away_daw - 50)
        away_header_edge = (away_oap - 50) + (home_daw - 50)
        if home_header_edge >= self.HEADER_EDGE_THRESHOLD:
            strength = SignalStrength.STRONG if home_header_edge >= 35 else SignalStrength.MEDIUM
            signals.append(SetPieceSignal(market=MarketType.HEADER_GOAL, team=home_team, opponent=away_team,
                direction="YES", strength=strength, confidence=round(50 + home_header_edge / 2, 1),
                edge_pct=round(home_header_edge / 3, 1),
                reasoning=[f"{home_team} OAP: {home_oap:.0f}", f"{away_team} DAW: {away_daw:.0f}"],
                metrics={'home_oap': home_oap, 'away_daw': away_daw, 'edge': home_header_edge}))
        if away_header_edge >= self.HEADER_EDGE_THRESHOLD:
            strength = SignalStrength.STRONG if away_header_edge >= 35 else SignalStrength.MEDIUM
            signals.append(SetPieceSignal(market=MarketType.HEADER_GOAL, team=away_team, opponent=home_team,
                direction="YES", strength=strength, confidence=round(50 + away_header_edge / 2, 1),
                edge_pct=round(away_header_edge / 3, 1),
                reasoning=[f"{away_team} OAP: {away_oap:.0f}", f"{home_team} DAW: {home_daw:.0f}"],
                metrics={'away_oap': away_oap, 'home_daw': home_daw, 'edge': away_header_edge}))
        return signals

class SetPieceAgent:
    VERSION = "1.1"
    
    def __init__(self):
        logger.info(f"🎯 Initializing SET_PIECE Agent V{self.VERSION}")
        self.data_loader = SetPieceDataLoader()
        self.data_loaded = self.data_loader.load_all()
        if self.data_loaded:
            self.feature_engineer = SetPieceFeatureEngineer(self.data_loader)
            self.signal_generator = SetPieceSignalGenerator(self.feature_engineer)
            logger.info("✅ SET_PIECE Agent ready")
    
    def analyze(self, home_team: str, away_team: str) -> Dict:
        if not self.data_loaded: return {'error': 'Data not loaded'}
        logger.info(f"📊 Analyzing: {home_team} vs {away_team}")
        signals = self.signal_generator.analyze_matchup(home_team, away_team)
        corner_analysis = self.feature_engineer.calculate_corner_matchup_edge(home_team, away_team)
        home_profile = {
            'offensive_aerial_power': self.feature_engineer.calculate_offensive_aerial_power(home_team),
            'defensive_aerial_weakness': self.feature_engineer.calculate_defensive_aerial_weakness(home_team),
            'goals_profile': self.data_loader.get_team_goals_profile(home_team),
            'stats': self.data_loader.team_stats.get(home_team, {}),
        }
        away_profile = {
            'offensive_aerial_power': self.feature_engineer.calculate_offensive_aerial_power(away_team),
            'defensive_aerial_weakness': self.feature_engineer.calculate_defensive_aerial_weakness(away_team),
            'goals_profile': self.data_loader.get_team_goals_profile(away_team),
            'stats': self.data_loader.team_stats.get(away_team, {}),
        }
        recommendations = []
        for s in signals:
            emoji = "🔥" if s.strength == SignalStrength.STRONG else "📊"
            recommendations.append(f"{emoji} {s.market.value}: {s.direction} ({s.team}) - {s.confidence:.0f}% conf, +{s.edge_pct:.1f}% edge")
        if not recommendations: recommendations.append("⚪ No significant SET_PIECE edges detected")
        return {
            'matchup': f"{home_team} vs {away_team}", 'agent': f"SET_PIECE V{self.VERSION}",
            'signals': [{'market': s.market.value, 'team': s.team, 'direction': s.direction, 
                        'strength': s.strength.value, 'confidence': s.confidence, 'edge_pct': s.edge_pct,
                        'reasoning': s.reasoning, 'metrics': s.metrics} for s in signals],
            'signals_count': {'total': len(signals), 'strong': sum(1 for s in signals if s.strength == SignalStrength.STRONG)},
            'team_profiles': {'home': home_profile, 'away': away_profile},
            'corner_analysis': corner_analysis, 'recommendations': recommendations,
        }

def main():
    print("=" * 60)
    print("🎯 SET_PIECE AGENT V1.1 - TEST")
    print("=" * 60)
    agent = SetPieceAgent()
    if not agent.data_loaded: print("❌ Failed to load data!"); return
    
    print("\n📊 Test 1: Liverpool vs Man City")
    result = agent.analyze("Liverpool", "Man City")
    print(f"\n📈 Corner Analysis: Expected total: {result['corner_analysis']['total_expected']}")
    print(f"🎯 Signals ({result['signals_count']['total']}):")
    for rec in result['recommendations']: print(f"   {rec}")
    print(f"📊 Liverpool OAP: {result['team_profiles']['home']['offensive_aerial_power']}/100, Goals: {result['team_profiles']['home']['goals_profile']}")
    print(f"📊 Man City OAP: {result['team_profiles']['away']['offensive_aerial_power']}/100, Goals: {result['team_profiles']['away']['goals_profile']}")
    
    print("\n" + "=" * 60)
    print("📊 Test 2: Arsenal vs Bournemouth")
    result2 = agent.analyze("Arsenal", "Bournemouth")
    print(f"🎯 Signals ({result2['signals_count']['total']}):")
    for rec in result2['recommendations']: print(f"   {rec}")
    print(f"📊 Arsenal OAP: {result2['team_profiles']['home']['offensive_aerial_power']}/100, Goals: {result2['team_profiles']['home']['goals_profile']}")
    
    output_file = Path("/home/Mon_ps/agents/set_piece_v1/test_output.json")
    with open(output_file, 'w') as f: json.dump({'test1': result, 'test2': result2}, f, indent=2, default=str)
    print(f"\n💾 Saved to {output_file}")

if __name__ == "__main__":
    main()
