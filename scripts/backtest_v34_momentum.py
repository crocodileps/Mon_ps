#!/usr/bin/env python3
"""
🔬 BACKTEST V3.4.2 - MOMENTUM L5 + SMART CONFLICT RESOLUTION
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

DB_CONFIG = {
    "host": "localhost", "port": 5432, "database": "monps_db",
    "user": "monps_user", "password": "monps_secure_password_2024"
}

@dataclass
class HistoricalMomentum:
    team_name: str
    matches_before: List[Dict]
    
    @property
    def n_matches(self) -> int:
        return len(self.matches_before)
    
    @property
    def wins(self) -> int:
        return sum(1 for m in self.matches_before if m['result'] == 'win')
    
    @property
    def draws(self) -> int:
        return sum(1 for m in self.matches_before if m['result'] == 'draw')
    
    @property
    def losses(self) -> int:
        return sum(1 for m in self.matches_before if m['result'] == 'loss')
    
    @property
    def points(self) -> int:
        pts = {'win': 3, 'draw': 1, 'loss': 0}
        return sum(pts.get(m['result'], 0) for m in self.matches_before)
    
    @property
    def form_percentage(self) -> float:
        if self.n_matches == 0:
            return 50.0
        return (self.points / (self.n_matches * 3)) * 100
    
    @property
    def current_streak(self) -> Tuple[str, int]:
        if not self.matches_before:
            return ("none", 0)
        streak_type = self.matches_before[0]['result']
        streak_len = 1
        for m in self.matches_before[1:]:
            if m['result'] == streak_type:
                streak_len += 1
            else:
                break
        return (streak_type, streak_len)
    
    @property
    def momentum_score(self) -> float:
        if self.n_matches == 0:
            return 50.0
        
        form_score = self.form_percentage
        
        streak_type, streak_len = self.current_streak
        if streak_type == 'win':
            streak_score = min(100, 50 + streak_len * 12)
        elif streak_type == 'draw':
            streak_score = 45
        else:
            streak_score = max(0, 50 - streak_len * 12)
        
        if self.n_matches >= 5:
            l3_pts = sum({'win': 3, 'draw': 1, 'loss': 0}.get(m['result'], 0) 
                        for m in self.matches_before[:3])
            l2_old = sum({'win': 3, 'draw': 1, 'loss': 0}.get(m['result'], 0) 
                        for m in self.matches_before[3:5])
            accel = ((l3_pts / 3) - (l2_old / 2)) / 3 * 100
        else:
            accel = 0
        
        accel_score = max(0, min(100, 50 + accel / 2))
        
        return round(0.40 * form_score + 0.35 * streak_score + 0.25 * accel_score, 1)
    
    @property
    def trend(self) -> str:
        score = self.momentum_score
        streak_type, streak_len = self.current_streak
        
        if score >= 75 or (streak_type == 'win' and streak_len >= 4):
            return "BLAZING"
        elif score >= 65 or (streak_type == 'win' and streak_len >= 3):
            return "HOT"
        elif score >= 50:
            return "WARMING"
        elif score >= 40:
            return "NEUTRAL"
        elif score >= 30:
            return "COOLING"
        elif streak_type == 'loss' and streak_len >= 3:
            return "FREEZING"
        else:
            return "COLD"
    
    @property
    def is_hot(self) -> bool:
        return self.trend in ["BLAZING", "HOT"]
    
    @property
    def is_cold(self) -> bool:
        return self.trend in ["COLD", "FREEZING"]


@dataclass
class BacktestResult:
    match_id: str
    date: datetime
    home_team: str
    away_team: str
    actual_outcome: str
    home_goals: int
    away_goals: int
    home_momentum: float
    away_momentum: float
    home_trend: str
    away_trend: str
    home_streak: Tuple[str, int]
    away_streak: Tuple[str, int]
    home_z: float
    away_z: float
    z_edge: float
    z_favorite: str
    momentum_favorite: str
    resolution: str
    follow_team: str
    predicted_winner: str
    stake: float
    is_correct: bool
    pnl: float


class BacktesterV34:
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.results: List[BacktestResult] = []
        self.team_stats = defaultdict(lambda: {
            'bets': 0, 'wins': 0, 'pnl': 0.0,
            'follow_mom_bets': 0, 'follow_mom_wins': 0, 'follow_mom_pnl': 0.0,
            'follow_z_bets': 0, 'follow_z_wins': 0, 'follow_z_pnl': 0.0,
            'aligned_bets': 0, 'aligned_wins': 0, 'aligned_pnl': 0.0,
        })
    
    def get_historical_momentum(self, team_name: str, before_date: datetime, n: int = 5) -> Optional[HistoricalMomentum]:
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                WITH deduped AS (
                    SELECT DISTINCT ON (DATE(commence_time), home_team, away_team)
                        CASE 
                            WHEN home_team ILIKE %s AND outcome = 'home' THEN 'win'
                            WHEN away_team ILIKE %s AND outcome = 'away' THEN 'win'
                            WHEN outcome = 'draw' THEN 'draw'
                            ELSE 'loss'
                        END as result,
                        commence_time
                    FROM match_results
                    WHERE (home_team ILIKE %s OR away_team ILIKE %s)
                      AND is_finished = true
                      AND commence_time < %s
                    ORDER BY DATE(commence_time) DESC, home_team, away_team, fetched_at DESC
                )
                SELECT * FROM deduped ORDER BY commence_time DESC LIMIT %s
            """, (f"%{team_name}%", f"%{team_name}%", f"%{team_name}%", f"%{team_name}%", before_date, n))
            rows = cur.fetchall()
        
        if not rows:
            return None
        
        matches = [{'result': r['result'], 'date': r['commence_time']} for r in rows]
        return HistoricalMomentum(team_name=team_name, matches_before=matches)
    
    def get_team_historical_wr(self, team_name: str, before_date: datetime, n: int = 20) -> float:
        """Get historical win rate for Z-score approximation - FIXED"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                WITH recent_matches AS (
                    SELECT DISTINCT ON (DATE(commence_time), home_team, away_team)
                        home_team, away_team, outcome, commence_time
                    FROM match_results
                    WHERE (home_team ILIKE %s OR away_team ILIKE %s)
                      AND is_finished = true
                      AND commence_time < %s
                    ORDER BY DATE(commence_time) DESC, home_team, away_team, fetched_at DESC
                    LIMIT %s
                )
                SELECT 
                    COUNT(*) FILTER (WHERE 
                        (home_team ILIKE %s AND outcome = 'home') OR
                        (away_team ILIKE %s AND outcome = 'away')
                    ) as wins,
                    COUNT(*) as total
                FROM recent_matches
            """, (f"%{team_name}%", f"%{team_name}%", before_date, n,
                  f"%{team_name}%", f"%{team_name}%"))
            r = cur.fetchone()
        
        if not r or r['total'] == 0:
            return 0.5
        return r['wins'] / r['total']
    
    def resolve_conflict(self, home_z: float, away_z: float, 
                         home_mom: HistoricalMomentum, away_mom: HistoricalMomentum,
                         home_team: str, away_team: str) -> Dict:
        
        z_diff = home_z - away_z
        z_favorite = home_team if z_diff > 0 else away_team
        z_edge = abs(z_diff)
        
        mom_diff = home_mom.momentum_score - away_mom.momentum_score
        momentum_favorite = home_team if mom_diff > 0 else away_team
        
        aligned = (z_favorite == momentum_favorite)
        
        z_fav_mom = home_mom if z_favorite == home_team else away_mom
        z_und_mom = away_mom if z_favorite == home_team else home_mom
        
        if aligned:
            boost = 1.15 if z_fav_mom.is_hot else 1.0
            return {
                'resolution': 'ALIGNED',
                'follow_team': z_favorite,
                'stake_mult': boost
            }
        
        if z_und_mom.is_hot and z_edge < 2.0:
            return {
                'resolution': 'FOLLOW_MOM',
                'follow_team': momentum_favorite,
                'stake_mult': 1.15
            }
        
        if z_edge > 2.5 and not z_fav_mom.is_cold:
            return {
                'resolution': 'FOLLOW_Z',
                'follow_team': z_favorite,
                'stake_mult': 0.90
            }
        
        if z_fav_mom.is_cold:
            return {
                'resolution': 'REDUCED_Z',
                'follow_team': z_favorite,
                'stake_mult': 0.50
            }
        
        return {
            'resolution': 'REDUCED_Z',
            'follow_team': z_favorite,
            'stake_mult': 0.75
        }
    
    def calculate_stake(self, z_edge: float, resolution: Dict) -> float:
        if z_edge >= 2.5:
            base = 4.0
        elif z_edge >= 1.5:
            base = 3.0
        elif z_edge >= 1.0:
            base = 2.0
        elif z_edge >= 0.5:
            base = 1.5
        else:
            base = 1.0
        
        return min(round(base * resolution['stake_mult'], 1), 5.0)
    
    def run_backtest(self, min_date: str = '2024-08-01', max_date: str = '2025-12-01'):
        print("=" * 80)
        print("🔬 BACKTEST V3.4.2 - MOMENTUM L5 + SMART CONFLICT RESOLUTION")
        print("=" * 80)
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT ON (DATE(commence_time), home_team, away_team)
                    id, home_team, away_team, outcome, 
                    score_home, score_away, commence_time
                FROM match_results
                WHERE is_finished = true
                  AND outcome IN ('home', 'draw', 'away')
                  AND commence_time BETWEEN %s AND %s
                ORDER BY DATE(commence_time), home_team, away_team, fetched_at DESC
            """, (min_date, max_date))
            matches = cur.fetchall()
        
        print(f"\n📊 Matchs à analyser: {len(matches)}")
        print(f"   Période: {min_date} → {max_date}")
        
        skipped = 0
        for i, match in enumerate(matches):
            if i % 100 == 0:
                print(f"   Processing {i}/{len(matches)}...")
            
            home = match['home_team']
            away = match['away_team']
            match_date = match['commence_time']
            outcome = match['outcome']
            
            home_mom = self.get_historical_momentum(home, match_date, 5)
            away_mom = self.get_historical_momentum(away, match_date, 5)
            
            if not home_mom or not away_mom or home_mom.n_matches < 3 or away_mom.n_matches < 3:
                skipped += 1
                continue
            
            home_wr = self.get_team_historical_wr(home, match_date, 20)
            away_wr = self.get_team_historical_wr(away, match_date, 20)
            
            home_z = (home_wr - 0.5) / 0.15
            away_z = (away_wr - 0.5) / 0.15
            z_edge = abs(home_z - away_z)
            
            resolution = self.resolve_conflict(home_z, away_z, home_mom, away_mom, home, away)
            stake = self.calculate_stake(z_edge, resolution)
            
            follow_team = resolution['follow_team']
            predicted_outcome = 'home' if follow_team == home else 'away'
            
            if outcome == 'draw':
                pnl = -stake
                is_correct = False
            elif predicted_outcome == outcome:
                pnl = stake * 0.90
                is_correct = True
            else:
                pnl = -stake
                is_correct = False
            
            result = BacktestResult(
                match_id=str(match['id']),
                date=match_date,
                home_team=home,
                away_team=away,
                actual_outcome=outcome,
                home_goals=match['score_home'] or 0,
                away_goals=match['score_away'] or 0,
                home_momentum=home_mom.momentum_score,
                away_momentum=away_mom.momentum_score,
                home_trend=home_mom.trend,
                away_trend=away_mom.trend,
                home_streak=home_mom.current_streak,
                away_streak=away_mom.current_streak,
                home_z=home_z,
                away_z=away_z,
                z_edge=z_edge,
                z_favorite=home if home_z > away_z else away,
                momentum_favorite=home if home_mom.momentum_score > away_mom.momentum_score else away,
                resolution=resolution['resolution'],
                follow_team=follow_team,
                predicted_winner=follow_team,
                stake=stake,
                is_correct=is_correct,
                pnl=pnl
            )
            
            self.results.append(result)
            
            # Stats par équipe suivie
            team = follow_team
            self.team_stats[team]['bets'] += 1
            if is_correct:
                self.team_stats[team]['wins'] += 1
            self.team_stats[team]['pnl'] += pnl
            
            res_type = resolution['resolution'].lower()
            if res_type == 'follow_mom':
                self.team_stats[team]['follow_mom_bets'] += 1
                if is_correct:
                    self.team_stats[team]['follow_mom_wins'] += 1
                self.team_stats[team]['follow_mom_pnl'] += pnl
            elif res_type == 'follow_z':
                self.team_stats[team]['follow_z_bets'] += 1
                if is_correct:
                    self.team_stats[team]['follow_z_wins'] += 1
                self.team_stats[team]['follow_z_pnl'] += pnl
            elif res_type == 'aligned':
                self.team_stats[team]['aligned_bets'] += 1
                if is_correct:
                    self.team_stats[team]['aligned_wins'] += 1
                self.team_stats[team]['aligned_pnl'] += pnl
        
        print(f"\n✅ Backtest terminé: {len(self.results)} matchs ({skipped} skipped)")
    
    def print_results(self):
        if not self.results:
            print("❌ Aucun résultat")
            return
        
        print("\n" + "=" * 80)
        print("📊 RÉSULTATS GLOBAUX V3.4.2")
        print("=" * 80)
        
        total_bets = len(self.results)
        total_wins = sum(1 for r in self.results if r.is_correct)
        total_pnl = sum(r.pnl for r in self.results)
        total_staked = sum(r.stake for r in self.results)
        
        print(f"\n📈 GLOBAL:")
        print(f"   Bets: {total_bets}")
        print(f"   Wins: {total_wins} ({100*total_wins/total_bets:.1f}%)")
        print(f"   P&L: {total_pnl:+.2f}u")
        print(f"   ROI: {100*total_pnl/total_staked:.1f}%")
        
        print(f"\n📊 PAR TYPE DE RÉSOLUTION:")
        for res_type in ['ALIGNED', 'FOLLOW_MOM', 'FOLLOW_Z', 'REDUCED_Z']:
            subset = [r for r in self.results if r.resolution == res_type]
            if subset:
                wins = sum(1 for r in subset if r.is_correct)
                pnl = sum(r.pnl for r in subset)
                staked = sum(r.stake for r in subset)
                roi = 100*pnl/staked if staked > 0 else 0
                print(f"   {res_type:12}: {len(subset):4} bets | {wins:4} wins ({100*wins/len(subset):5.1f}%) | {pnl:+8.2f}u | ROI {roi:+6.1f}%")
        
        print(f"\n🔥 PAR TREND DU FAVORI:")
        for trend in ['BLAZING', 'HOT', 'WARMING', 'NEUTRAL', 'COOLING', 'COLD']:
            subset = [r for r in self.results if 
                     (r.follow_team == r.home_team and r.home_trend == trend) or
                     (r.follow_team == r.away_team and r.away_trend == trend)]
            if subset:
                wins = sum(1 for r in subset if r.is_correct)
                pnl = sum(r.pnl for r in subset)
                staked = sum(r.stake for r in subset)
                icon = {'BLAZING': '🔥', 'HOT': '🌡️', 'WARMING': '📈', 
                       'NEUTRAL': '➡️', 'COOLING': '📉', 'COLD': '❄️'}.get(trend, '')
                roi = 100*pnl/staked if staked > 0 else 0
                print(f"   {icon} {trend:10}: {len(subset):4} bets | {wins:4} wins ({100*wins/len(subset):5.1f}%) | {pnl:+8.2f}u | ROI {roi:+6.1f}%")
        
        print(f"\n🎯 PAR WIN STREAK DU FAVORI:")
        for streak_len in range(0, 6):
            subset = [r for r in self.results if
                     ((r.follow_team == r.home_team and r.home_streak[0] == 'win' and r.home_streak[1] == streak_len) or
                      (r.follow_team == r.away_team and r.away_streak[0] == 'win' and r.away_streak[1] == streak_len))]
            if subset:
                wins = sum(1 for r in subset if r.is_correct)
                pnl = sum(r.pnl for r in subset)
                staked = sum(r.stake for r in subset)
                roi = 100*pnl/staked if staked > 0 else 0
                print(f"   WIN×{streak_len}: {len(subset):4} bets | {wins:4} wins ({100*wins/len(subset):5.1f}%) | {pnl:+8.2f}u | ROI {roi:+6.1f}%")
        
        print(f"\n🏆 TOP 15 ÉQUIPES (P&L):")
        sorted_teams = sorted(self.team_stats.items(), key=lambda x: x[1]['pnl'], reverse=True)
        for team, stats in sorted_teams[:15]:
            if stats['bets'] >= 3:
                wr = 100 * stats['wins'] / stats['bets'] if stats['bets'] > 0 else 0
                print(f"   {team:25}: {stats['bets']:3} bets | {stats['wins']:3} wins ({wr:5.1f}%) | {stats['pnl']:+8.2f}u")
        
        print(f"\n❌ BOTTOM 10 ÉQUIPES (P&L):")
        for team, stats in sorted_teams[-10:]:
            if stats['bets'] >= 3:
                wr = 100 * stats['wins'] / stats['bets'] if stats['bets'] > 0 else 0
                print(f"   {team:25}: {stats['bets']:3} bets | {stats['wins']:3} wins ({wr:5.1f}%) | {stats['pnl']:+8.2f}u")
        
        print(f"\n🔥 FOLLOW_MOM DÉTAIL:")
        mom_results = [r for r in self.results if r.resolution == 'FOLLOW_MOM']
        if mom_results:
            for trend in ['BLAZING', 'HOT']:
                subset = [r for r in mom_results if 
                         (r.follow_team == r.home_team and r.home_trend == trend) or
                         (r.follow_team == r.away_team and r.away_trend == trend)]
                if subset:
                    wins = sum(1 for r in subset if r.is_correct)
                    pnl = sum(r.pnl for r in subset)
                    print(f"   {trend}: {len(subset)} bets | {wins} wins ({100*wins/len(subset):.1f}%) | {pnl:+.2f}u")
        
        print(f"\n⚔️ CONFLITS vs ALIGNED:")
        aligned = [r for r in self.results if r.resolution == 'ALIGNED']
        conflicts = [r for r in self.results if r.resolution != 'ALIGNED']
        
        a_wins = sum(1 for r in aligned if r.is_correct)
        a_pnl = sum(r.pnl for r in aligned)
        c_wins = sum(1 for r in conflicts if r.is_correct)
        c_pnl = sum(r.pnl for r in conflicts)
        
        print(f"   ALIGNED:   {len(aligned):4} bets | {a_wins:4} wins ({100*a_wins/len(aligned) if aligned else 0:.1f}%) | {a_pnl:+.2f}u")
        print(f"   CONFLICTS: {len(conflicts):4} bets | {c_wins:4} wins ({100*c_wins/len(conflicts) if conflicts else 0:.1f}%) | {c_pnl:+.2f}u")


if __name__ == "__main__":
    bt = BacktesterV34()
    bt.run_backtest(min_date='2024-08-01', max_date='2025-12-01')
    bt.print_results()
    bt.conn.close()
