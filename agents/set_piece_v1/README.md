# 🎯 SET_PIECE Agent V1

## Overview
Agent quantitatif spécialisé dans la détection d'edges sur les marchés coups de pied arrêtés.

## Markets Covered
- **Corners**: Over/Under, Corner Match Bet, First Corner
- **Headers**: Goal from header, Anytime GS (defenders)
- **Set Pieces**: Team to score from set piece

## Data Sources
- `matches_all_leagues_2526.json` - 694 matches with HC/AC
- `team_stats_football_data_2526.json` - 96 teams aggregated stats
- `all_goals_2025.json` - 1,844 goals with situations

## Key Metrics
- **Offensive Aerial Power (OAP)**: 0-100 score combining corners_for, header_goals%, corner_goals%
- **Defensive Aerial Weakness (DAW)**: 0-100 vulnerability to aerial threats
- **Corner Matchup Edge**: Expected corners per team with Poisson probability

## Usage
```python
from agents.set_piece_v1 import SetPieceAgent

agent = SetPieceAgent()
result = agent.analyze("Liverpool", "Man City")

for signal in result['recommendations']:
    print(signal)
```

## Version History
- V1.0 (2025-12-10): Initial release
