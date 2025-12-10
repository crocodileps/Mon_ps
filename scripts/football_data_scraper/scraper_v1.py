#!/usr/bin/env python3
"""
🏦 FOOTBALL-DATA.CO.UK SCRAPER - HEDGE FUND GRADE
Season: 2025/2026 (2526)
"""

import pandas as pd
import requests
from io import StringIO
from datetime import datetime
import json
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION - SAISON 2025/2026
# ═══════════════════════════════════════════════════════════════

SEASON = "2526"  # 2025-2026 ✅

@dataclass
class LeagueConfig:
    code: str
    name: str
    country: str
    our_name: str

LEAGUES = [
    LeagueConfig("E0", "Premier League", "England", "EPL"),
    LeagueConfig("D1", "Bundesliga", "Germany", "Bundesliga"),
    LeagueConfig("I1", "Serie A", "Italy", "Serie_A"),
    LeagueConfig("SP1", "La Liga", "Spain", "La_Liga"),
    LeagueConfig("F1", "Ligue 1", "France", "Ligue_1"),
]

BASE_URL = "https://www.football-data.co.uk/mmz4281/{season}/{league}.csv"

class FootballDataScraper:
    def __init__(self, output_dir: str = "/home/Mon_ps/data/football_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def fetch_league(self, league: LeagueConfig) -> Optional[pd.DataFrame]:
        url = BASE_URL.format(season=SEASON, league=league.code)
        logger.info(f"📥 Fetching {league.name} ({league.code}) - Season {SEASON}...")
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            df = pd.read_csv(StringIO(response.text))
            df['league_code'] = league.code
            df['league_name'] = league.our_name
            df['country'] = league.country
            df['season'] = SEASON
            
            logger.info(f"   ✅ {len(df)} matches loaded")
            return df
            
        except Exception as e:
            logger.error(f"   ❌ Error: {e}")
            return None
    
    def fetch_all_leagues(self) -> pd.DataFrame:
        all_data = []
        for league in LEAGUES:
            df = self.fetch_league(league)
            if df is not None:
                all_data.append(df)
        
        if all_data:
            combined = pd.concat(all_data, ignore_index=True)
            logger.info(f"📊 Total: {len(combined)} matches across {len(all_data)} leagues")
            return combined
        return pd.DataFrame()
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("🧹 Cleaning data...")
        
        df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y', errors='coerce')
        
        stat_cols = ['HS', 'AS', 'HST', 'AST', 'HF', 'AF', 'HC', 'AC', 'HY', 'AY', 'HR', 'AR']
        for col in stat_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        df = df.dropna(subset=['FTHG', 'FTAG'])
        logger.info(f"   ✅ {len(df)} matches after cleaning")
        return df
    
    def calculate_derived_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("📈 Calculating derived metrics...")
        
        # Goals
        df['total_goals'] = df['FTHG'] + df['FTAG']
        df['total_goals_ht'] = df['HTHG'] + df['HTAG']
        
        # Corners & Fouls
        df['total_corners'] = df['HC'] + df['AC']
        df['corner_diff'] = df['HC'] - df['AC']
        df['total_fouls'] = df['HF'] + df['AF']
        
        # Shots
        df['total_shots'] = df['HS'] + df['AS']
        df['total_sot'] = df['HST'] + df['AST']
        
        # Cards
        df['total_yellows'] = df['HY'] + df['AY']
        df['total_reds'] = df['HR'] + df['AR']
        df['total_cards'] = df['total_yellows'] + df['total_reds']
        
        # CLV (Pinnacle)
        if 'PSH' in df.columns and 'PSCH' in df.columns:
            df['clv_home_pinnacle'] = ((df['PSCH'] - df['PSH']) / df['PSH'] * 100).round(2)
            df['clv_away_pinnacle'] = ((df['PSCA'] - df['PSA']) / df['PSA'] * 100).round(2)
        
        if 'P>2.5' in df.columns and 'PC>2.5' in df.columns:
            df['clv_over25_pinnacle'] = ((df['PC>2.5'] - df['P>2.5']) / df['P>2.5'] * 100).round(2)
        
        # Market results
        df['btts'] = ((df['FTHG'] > 0) & (df['FTAG'] > 0)).astype(int)
        df['over_25'] = (df['total_goals'] > 2.5).astype(int)
        df['over_35'] = (df['total_goals'] > 3.5).astype(int)
        
        return df
    
    def calculate_team_aggregates(self, df: pd.DataFrame) -> Dict:
        logger.info("📊 Calculating team aggregates...")
        
        team_stats = {}
        all_teams = set(df['HomeTeam'].unique()) | set(df['AwayTeam'].unique())
        
        for team in all_teams:
            home = df[df['HomeTeam'] == team]
            away = df[df['AwayTeam'] == team]
            total = len(home) + len(away)
            
            if total == 0:
                continue
            
            stats = {
                'team_name': team,
                'matches_played': total,
                'league': home['league_name'].iloc[0] if len(home) > 0 else away['league_name'].iloc[0],
                
                # Corners
                'corners_for_avg': round((home['HC'].sum() + away['AC'].sum()) / total, 2),
                'corners_against_avg': round((home['AC'].sum() + away['HC'].sum()) / total, 2),
                
                # Fouls
                'fouls_committed_avg': round((home['HF'].sum() + away['AF'].sum()) / total, 2),
                'fouls_suffered_avg': round((home['AF'].sum() + away['HF'].sum()) / total, 2),
                
                # Shots
                'shots_for_avg': round((home['HS'].sum() + away['AS'].sum()) / total, 2),
                'sot_for_avg': round((home['HST'].sum() + away['AST'].sum()) / total, 2),
                
                # Cards
                'yellows_for_avg': round((home['HY'].sum() + away['AY'].sum()) / total, 2),
                'reds_for_total': home['HR'].sum() + away['AR'].sum(),
                
                # Goals
                'goals_for_avg': round((home['FTHG'].sum() + away['FTAG'].sum()) / total, 2),
                'goals_against_avg': round((home['FTAG'].sum() + away['FTHG'].sum()) / total, 2),
            }
            
            # Derived
            stats['corner_dominance'] = round(
                (stats['corners_for_avg'] - stats['corners_against_avg']) / 
                max(stats['corners_for_avg'] + stats['corners_against_avg'], 1), 3
            )
            stats['foul_magnet_score'] = round(
                stats['fouls_suffered_avg'] / max(stats['fouls_committed_avg'], 1), 2
            )
            
            team_stats[team] = stats
        
        logger.info(f"   ✅ {len(team_stats)} teams aggregated")
        return team_stats
    
    def save_to_json(self, df: pd.DataFrame, team_stats: Dict):
        # Matches
        matches_file = self.output_dir / f"matches_all_leagues_{SEASON}.json"
        df_json = df.copy()
        df_json['Date'] = df_json['Date'].astype(str)
        df_json.to_json(matches_file, orient='records', indent=2)
        logger.info(f"💾 Saved {len(df)} matches to {matches_file}")
        
        # Team stats
        team_file = self.output_dir / f"team_stats_football_data_{SEASON}.json"
        with open(team_file, 'w') as f:
            json.dump(team_stats, f, indent=2)
        logger.info(f"💾 Saved {len(team_stats)} team stats to {team_file}")
        
        # Summary
        summary = {
            'scrape_date': datetime.now().isoformat(),
            'season': SEASON,
            'season_display': '2025/2026',
            'total_matches': len(df),
            'leagues': df['league_name'].unique().tolist(),
            'matches_per_league': df.groupby('league_name').size().to_dict(),
            'teams_count': len(team_stats),
        }
        summary_file = self.output_dir / f"scrape_summary_{SEASON}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"📋 Summary: {summary_file}")
    
    def run(self) -> Dict:
        logger.info("=" * 60)
        logger.info(f"🏦 FOOTBALL-DATA SCRAPER - SEASON {SEASON} (2025/2026)")
        logger.info("=" * 60)
        
        df = self.fetch_all_leagues()
        if df.empty:
            logger.error("❌ No data!")
            return {}
        
        df = self.clean_data(df)
        df = self.calculate_derived_metrics(df)
        team_stats = self.calculate_team_aggregates(df)
        self.save_to_json(df, team_stats)
        
        logger.info("=" * 60)
        logger.info("✅ SCRAPING COMPLETE!")
        logger.info("=" * 60)
        
        return {'matches': len(df), 'teams': len(team_stats)}

if __name__ == "__main__":
    scraper = FootballDataScraper()
    scraper.run()
