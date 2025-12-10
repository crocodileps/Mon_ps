import json
from pathlib import Path

# Charger le fichier matches (déjà sauvé)
matches_file = Path("/home/Mon_ps/data/football_data/matches_all_leagues_2526.json")
print(f"✅ Matches file exists: {matches_file.exists()}")

# Recalculer team_stats avec conversion des types
import pandas as pd

df = pd.read_json(matches_file)
print(f"📊 Loaded {len(df)} matches")

team_stats = {}
all_teams = set(df['HomeTeam'].unique()) | set(df['AwayTeam'].unique())

for team in all_teams:
    home = df[df['HomeTeam'] == team]
    away = df[df['AwayTeam'] == team]
    total = len(home) + len(away)
    
    if total == 0:
        continue
    
    stats = {
        'team_name': str(team),
        'matches_played': int(total),
        'league': str(home['league_name'].iloc[0] if len(home) > 0 else away['league_name'].iloc[0]),
        
        # Corners - CONVERT TO FLOAT
        'corners_for_avg': float(round((home['HC'].sum() + away['AC'].sum()) / total, 2)),
        'corners_against_avg': float(round((home['AC'].sum() + away['HC'].sum()) / total, 2)),
        
        # Fouls
        'fouls_committed_avg': float(round((home['HF'].sum() + away['AF'].sum()) / total, 2)),
        'fouls_suffered_avg': float(round((home['AF'].sum() + away['HF'].sum()) / total, 2)),
        
        # Shots
        'shots_for_avg': float(round((home['HS'].sum() + away['AS'].sum()) / total, 2)),
        'sot_for_avg': float(round((home['HST'].sum() + away['AST'].sum()) / total, 2)),
        
        # Cards
        'yellows_for_avg': float(round((home['HY'].sum() + away['AY'].sum()) / total, 2)),
        'reds_for_total': int(home['HR'].sum() + away['AR'].sum()),
        
        # Goals
        'goals_for_avg': float(round((home['FTHG'].sum() + away['FTAG'].sum()) / total, 2)),
        'goals_against_avg': float(round((home['FTAG'].sum() + away['FTHG'].sum()) / total, 2)),
    }
    
    # Derived
    stats['corner_dominance'] = float(round(
        (stats['corners_for_avg'] - stats['corners_against_avg']) / 
        max(stats['corners_for_avg'] + stats['corners_against_avg'], 1), 3
    ))
    stats['foul_magnet_score'] = float(round(
        stats['fouls_suffered_avg'] / max(stats['fouls_committed_avg'], 1), 2
    ))
    
    team_stats[team] = stats

print(f"✅ {len(team_stats)} teams processed")

# Save team stats
team_file = Path("/home/Mon_ps/data/football_data/team_stats_football_data_2526.json")
with open(team_file, 'w') as f:
    json.dump(team_stats, f, indent=2)
print(f"💾 Saved to {team_file}")

# Save summary
from datetime import datetime
summary = {
    'scrape_date': datetime.now().isoformat(),
    'season': '2526',
    'season_display': '2025/2026',
    'total_matches': int(len(df)),
    'leagues': df['league_name'].unique().tolist(),
    'matches_per_league': {k: int(v) for k, v in df.groupby('league_name').size().to_dict().items()},
    'teams_count': int(len(team_stats)),
}
summary_file = Path("/home/Mon_ps/data/football_data/scrape_summary_2526.json")
with open(summary_file, 'w') as f:
    json.dump(summary, f, indent=2)
print(f"📋 Summary saved to {summary_file}")

print("\n✅ FIX COMPLETE!")
