#!/usr/bin/env python3
"""
🎯 SMART PLAYER BET EVALUATOR V3.0
Intègre: npxG, penalties, shot_quality, playing_time, home/away context
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import json
from dataclasses import dataclass, field
from typing import List, Dict

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

@dataclass
class PlayerBetRecommendation:
    player_name: str
    team_name: str
    market: str
    recommendation: str
    confidence: str
    score: float
    reasoning: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Stats
    goals: int = 0
    npg: int = 0
    shots: int = 0
    conversion_rate: float = 0
    shot_quality: str = ""
    goals_per_90: float = 0
    minutes_per_game: float = 0
    playing_time_profile: str = ""
    home_away_profile: str = ""
    home_away_ratio: float = 1.0
    penalty_pct: float = 0
    npxg_over: float = 0
    is_penalty_taker: bool = False


class SmartPlayerEvaluator:
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.load_data()
    
    def load_data(self):
        cur = self.conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT * FROM player_stats 
            WHERE season = '2025-2026' AND games >= 5
        """)
        self.players = {f"{r['player_name']}|{r['team_name']}": dict(r) for r in cur.fetchall()}
        
        cur.execute("""
            SELECT team_name, goal_timing_dna, scorer_dna 
            FROM quantum.team_stats_extended
            WHERE goal_timing_dna IS NOT NULL
        """)
        self.teams = {r['team_name']: {
            'goal_timing': r['goal_timing_dna'],
            'scorer': r['scorer_dna']
        } for r in cur.fetchall()}
        
        cur.close()
        print(f"📊 Loaded: {len(self.players)} players, {len(self.teams)} teams")
    
    def get_team_players(self, team_name: str) -> List[dict]:
        return [p for k, p in self.players.items() if p['team_name'] == team_name]
    
    def evaluate_anytime_scorer(self, player: dict, is_home_game: bool = None) -> PlayerBetRecommendation:
        """
        SCORING V3.0:
        - Goals volume: 15 pts
        - Shot Quality: 18 pts
        - Goals per 90: 18 pts (NEW)
        - Playing Time Profile: 12 pts (NEW)
        - Home/Away Context: 12 pts (NEW)
        - npxG performance: 10 pts
        - Penalty: 15 pts (bonus/malus)
        """
        score = 0
        reasoning = []
        warnings = []
        
        name = player['player_name']
        team = player['team_name']
        goals = player.get('goals', 0)
        npg = player.get('npg', 0)
        npxg = player.get('npxg', 0)
        shots = player.get('shots', 0)
        conversion = player.get('conversion_rate', 0) or 0
        shot_quality = player.get('shot_quality', '') or ''
        goals_per_90 = player.get('goals_per_90', 0) or 0
        minutes_per_game = player.get('minutes_per_game', 0) or 0
        playing_time_profile = player.get('playing_time_profile', '') or ''
        home_away_profile = player.get('home_away_profile', '') or ''
        home_away_ratio = player.get('home_away_ratio', 1.0) or 1.0
        penalty_pct = player.get('penalty_pct', 0) or 0
        is_penalty_taker = player.get('is_penalty_taker', False)
        
        npxg_over = (npg - npxg) if npxg else 0
        
        # ===== 1. GOALS VOLUME (15 pts) =====
        if goals >= 20:
            score += 15
            reasoning.append(f"🔥 Elite: {goals} buts")
        elif goals >= 15:
            score += 12
            reasoning.append(f"✅ Top scorer: {goals} buts")
        elif goals >= 10:
            score += 9
        elif goals >= 5:
            score += 5
        else:
            warnings.append(f"⚠️ Volume: {goals} buts")
        
        # ===== 2. SHOT QUALITY (18 pts) =====
        if shot_quality == 'ELITE_FINISHER':
            score += 18
            reasoning.append(f"🎯 Elite finisher: {conversion:.1f}%")
        elif shot_quality == 'CLINICAL':
            score += 15
            reasoning.append(f"🎯 Clinical: {conversion:.1f}%")
        elif shot_quality == 'EFFICIENT':
            score += 12
        elif shot_quality == 'OPPORTUNIST':
            score += 10
        elif shot_quality == 'AVERAGE':
            score += 6
        elif shot_quality == 'VOLUME_SHOOTER':
            score -= 12
            warnings.append(f"🚨 VOLUME: {shots}T, {conversion:.1f}%")
        elif shot_quality == 'WASTEFUL':
            score -= 15
            warnings.append(f"🚨 WASTEFUL: {conversion:.1f}%")
        elif shot_quality == 'POOR_FINISHER':
            score -= 8
            warnings.append(f"⚠️ Poor: {conversion:.1f}%")
        
        # ===== 3. GOALS PER 90 (18 pts) - CRITICAL =====
        if goals_per_90 >= 1.0:
            score += 18
            reasoning.append(f"⚡ Elite G/90: {goals_per_90:.2f}")
        elif goals_per_90 >= 0.7:
            score += 14
            reasoning.append(f"✅ High G/90: {goals_per_90:.2f}")
        elif goals_per_90 >= 0.5:
            score += 10
        elif goals_per_90 >= 0.3:
            score += 5
        elif goals_per_90 < 0.2 and goals >= 3:
            score -= 5
            warnings.append(f"⚠️ Low G/90: {goals_per_90:.2f}")
        
        # ===== 4. PLAYING TIME PROFILE (12 pts) =====
        if playing_time_profile == 'SUPER_SUB':
            score += 12
            reasoning.append(f"🔥 SUPER_SUB: {minutes_per_game:.0f}min/M")
        elif playing_time_profile == 'UNDISPUTED_STARTER':
            score += 8
            reasoning.append(f"✅ Titulaire indiscutable")
        elif playing_time_profile == 'STARTER':
            score += 6
        elif playing_time_profile == 'REGULAR':
            score += 4
        elif playing_time_profile == 'ROTATION_PLAYER':
            score += 2
            warnings.append(f"⚠️ Rotation: {minutes_per_game:.0f}min/M")
        elif playing_time_profile == 'BENCH_PLAYER':
            score -= 5
            warnings.append(f"❌ Banc: {minutes_per_game:.0f}min/M")
        
        # ===== 5. HOME/AWAY CONTEXT (12 pts) =====
        if is_home_game is not None:
            if is_home_game:
                if home_away_profile == 'HOME_SPECIALIST':
                    score += 12
                    reasoning.append(f"🏠 HOME BOOST: x{home_away_ratio:.1f}")
                elif home_away_ratio > 1.5:
                    score += 8
                else:
                    score += 4
            else:  # Away game
                if home_away_profile == 'AWAY_SPECIALIST':
                    score += 12
                    reasoning.append(f"✈️ AWAY SPECIALIST: x{home_away_ratio:.1f}")
                elif home_away_profile == 'HOME_SPECIALIST':
                    score -= 10
                    warnings.append(f"🚨 HOME team AWAY: x{home_away_ratio:.1f}")
                elif home_away_ratio > 2.0:
                    score -= 8
                    warnings.append(f"⚠️ Team weak away")
                else:
                    score += 2
        
        # ===== 6. npxG PERFORMANCE (10 pts) =====
        if npxg_over >= 5:
            score += 10
            reasoning.append(f"🔥 npxG: +{npxg_over:.1f}")
        elif npxg_over >= 2:
            score += 7
        elif npxg_over >= 0:
            score += 4
        elif npxg_over >= -2:
            score += 1
        else:
            score -= 5
            warnings.append(f"❌ Under npxG: {npxg_over:.1f}")
        
        # ===== 7. PENALTY IMPACT (15 pts) =====
        if penalty_pct >= 50:
            score -= 15
            warnings.append(f"🚨 Pen dependent: {penalty_pct:.0f}%")
        elif penalty_pct >= 35:
            score -= 8
            warnings.append(f"⚠️ High pen%: {penalty_pct:.0f}%")
        elif penalty_pct <= 15 and goals >= 5:
            score += 12
            reasoning.append(f"✅ Vrais buts: {penalty_pct:.0f}% pen")
        elif penalty_pct <= 25:
            score += 8
        
        if is_penalty_taker:
            score += 8
            reasoning.append(f"🎯 Penalty taker")
        
        # ===== RECOMMENDATION =====
        if score >= 75:
            recommendation = "STRONG_BACK"
            confidence = "HIGH"
        elif score >= 60:
            recommendation = "BACK"
            confidence = "HIGH"
        elif score >= 45:
            recommendation = "BACK"
            confidence = "MEDIUM"
        elif score >= 30:
            recommendation = "NEUTRAL"
            confidence = "LOW"
        elif score >= 10:
            recommendation = "AVOID"
            confidence = "MEDIUM"
        else:
            recommendation = "STRONG_AVOID"
            confidence = "HIGH"
        
        return PlayerBetRecommendation(
            player_name=name,
            team_name=team,
            market="ANYTIME_SCORER",
            recommendation=recommendation,
            confidence=confidence,
            score=score,
            reasoning=reasoning,
            warnings=warnings,
            goals=goals,
            npg=npg,
            shots=shots,
            conversion_rate=float(conversion),
            shot_quality=shot_quality,
            goals_per_90=float(goals_per_90),
            minutes_per_game=float(minutes_per_game),
            playing_time_profile=playing_time_profile,
            home_away_profile=home_away_profile,
            home_away_ratio=float(home_away_ratio),
            penalty_pct=float(penalty_pct),
            npxg_over=npxg_over,
            is_penalty_taker=is_penalty_taker
        )
    
    def evaluate_match(self, home_team: str, away_team: str) -> Dict:
        """Évalue avec contexte HOME/AWAY"""
        results = {
            'match': f"{home_team} vs {away_team}",
            'home_team': home_team,
            'away_team': away_team,
            'home_players': {'strong_back': [], 'back': [], 'avoid': []},
            'away_players': {'strong_back': [], 'back': [], 'avoid': []}
        }
        
        # Home team players (is_home_game=True)
        for player in self.get_team_players(home_team):
            rec = self.evaluate_anytime_scorer(player, is_home_game=True)
            if rec.recommendation == "STRONG_BACK":
                results['home_players']['strong_back'].append(rec)
            elif rec.recommendation == "BACK":
                results['home_players']['back'].append(rec)
            elif rec.recommendation in ["AVOID", "STRONG_AVOID"] and rec.goals >= 3:
                results['home_players']['avoid'].append(rec)
        
        # Away team players (is_home_game=False)
        for player in self.get_team_players(away_team):
            rec = self.evaluate_anytime_scorer(player, is_home_game=False)
            if rec.recommendation == "STRONG_BACK":
                results['away_players']['strong_back'].append(rec)
            elif rec.recommendation == "BACK":
                results['away_players']['back'].append(rec)
            elif rec.recommendation in ["AVOID", "STRONG_AVOID"] and rec.goals >= 3:
                results['away_players']['avoid'].append(rec)
        
        # Sort
        for cat in ['strong_back', 'back', 'avoid']:
            results['home_players'][cat].sort(key=lambda x: -x.score)
            results['away_players'][cat].sort(key=lambda x: -x.score)
        
        return results
    
    def print_match_analysis(self, results: Dict):
        print(f"\n{'='*80}")
        print(f"⚽ {results['match']}")
        print(f"{'='*80}")
        
        # HOME TEAM
        print(f"\n🏠 {results['home_team']} (HOME):")
        if results['home_players']['strong_back']:
            print(f"   �� STRONG BACK:")
            for rec in results['home_players']['strong_back'][:4]:
                pen = "🎯" if rec.is_penalty_taker else ""
                print(f"      {rec.player_name}: {rec.score:.0f}pts | {rec.goals}G | {rec.goals_per_90:.2f}G/90 | {rec.playing_time_profile} {pen}")
                for r in rec.reasoning[:2]:
                    print(f"         {r}")
        
        if results['home_players']['back']:
            print(f"   ✅ BACK:")
            for rec in results['home_players']['back'][:4]:
                pen = "🎯" if rec.is_penalty_taker else ""
                print(f"      • {rec.player_name}: {rec.score:.0f}pts | {rec.goals}G | {rec.goals_per_90:.2f}G/90 {pen}")
        
        if results['home_players']['avoid']:
            print(f"   ⚠️ AVOID:")
            for rec in results['home_players']['avoid'][:2]:
                warn = rec.warnings[0] if rec.warnings else ""
                print(f"      • {rec.player_name}: {warn}")
        
        # AWAY TEAM
        print(f"\n✈️ {results['away_team']} (AWAY):")
        if results['away_players']['strong_back']:
            print(f"   🔥 STRONG BACK:")
            for rec in results['away_players']['strong_back'][:4]:
                pen = "🎯" if rec.is_penalty_taker else ""
                print(f"      {rec.player_name}: {rec.score:.0f}pts | {rec.goals}G | {rec.goals_per_90:.2f}G/90 | {rec.playing_time_profile} {pen}")
                for r in rec.reasoning[:2]:
                    print(f"         {r}")
        
        if results['away_players']['back']:
            print(f"   ✅ BACK:")
            for rec in results['away_players']['back'][:4]:
                pen = "🎯" if rec.is_penalty_taker else ""
                print(f"      • {rec.player_name}: {rec.score:.0f}pts | {rec.goals}G | {rec.goals_per_90:.2f}G/90 {pen}")
        
        if results['away_players']['avoid']:
            print(f"   🚨 AVOID (Home team playing away!):")
            for rec in results['away_players']['avoid'][:3]:
                warn = rec.warnings[0] if rec.warnings else ""
                print(f"      • {rec.player_name}: {warn}")
    
    def close(self):
        self.conn.close()


def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🎯 SMART PLAYER BET EVALUATOR V3.0 - Full Quant Integration                 ║
║  Features: Shot Quality + G/90 + Playing Time + Home/Away Context            ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    evaluator = SmartPlayerEvaluator()
    
    # Test matches avec contexte H/A
    test_matches = [
        ("Liverpool", "Manchester City"),
        ("Wolverhampton Wanderers", "Arsenal"),  # Wolves HOME (away specialist) vs Arsenal AWAY (home specialist)
        ("Bayern Munich", "Fiorentina"),  # Bayern HOME vs Fiorentina AWAY
        ("Barcelona", "Atletico Madrid"),
        ("Brentford", "Nottingham Forest"),  # 2 équipes avec super subs
    ]
    
    for home, away in test_matches:
        results = evaluator.evaluate_match(home, away)
        evaluator.print_match_analysis(results)
    
    # TOP GLOBAL (sans contexte)
    print("\n" + "="*85)
    print("📊 TOP 25 ANYTIME SCORER - GLOBAL RANKING V3.0:")
    print("="*85)
    
    all_recs = []
    for key, player in evaluator.players.items():
        if player.get('goals', 0) >= 5:
            rec = evaluator.evaluate_anytime_scorer(player, is_home_game=None)
            all_recs.append(rec)
    
    all_recs.sort(key=lambda x: -x.score)
    
    print(f"\n{'#':<3} {'Joueur':<20} {'Équipe':<16} {'Sc':<5} {'G':<4} {'G/90':<5} {'Conv%':<6} {'TimeProf':<15} {'ShotQual':<14} {'H/A'}")
    print("-"*115)
    
    for i, rec in enumerate(all_recs[:25], 1):
        pen = "🎯" if rec.is_penalty_taker else ""
        ha = "🏠" if rec.home_away_profile == 'HOME_SPECIALIST' else "✈️" if rec.home_away_profile == 'AWAY_SPECIALIST' else "⚖️"
        time_prof = rec.playing_time_profile[:14] if rec.playing_time_profile else "N/A"
        shot_qual = rec.shot_quality[:13] if rec.shot_quality else "N/A"
        print(f"{i:<3} {rec.player_name[:19]:<20} {rec.team_name[:15]:<16} {rec.score:<5.0f} {rec.goals:<4} {rec.goals_per_90:<5.2f} {rec.conversion_rate:<6.1f} {time_prof:<15} {shot_qual:<14} {ha} {pen}")
    
    # SUPER SUBS RANKING
    print("\n" + "="*85)
    print("⚡ SUPER SUBS RANKING - VALUE PICKS:")
    print("="*85)
    
    super_subs = [r for r in all_recs if r.playing_time_profile == 'SUPER_SUB']
    super_subs.sort(key=lambda x: -x.goals_per_90)
    
    print(f"\n{'Joueur':<22} {'Équipe':<18} {'G':<4} {'G/90':<6} {'Min/M':<7} {'Score':<6} {'Shot Quality'}")
    print("-"*90)
    for rec in super_subs[:12]:
        print(f"{rec.player_name[:21]:<22} {rec.team_name[:17]:<18} {rec.goals:<4} {rec.goals_per_90:<6.2f} {rec.minutes_per_game:<7.0f} {rec.score:<6.0f} {rec.shot_quality}")
    
    evaluator.close()
    print("\n✅ Evaluator V3.0 Ready!")


if __name__ == "__main__":
    main()
