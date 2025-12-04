#!/usr/bin/env python3
"""
BACKTEST V13 MULTI-STRIKE
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from collections import defaultdict
from orchestrator_v13_multi_strike import OrchestratorV13

class BacktestV13:
    
    def __init__(self, days=30):
        self.days = days
        self.conn = psycopg2.connect(
            host='localhost', port=5432, dbname='monps_db',
            user='monps_user', password='monps_secure_password_2024'
        )
        self.cur = self.conn.cursor(cursor_factory=RealDictCursor)
        self.v13 = OrchestratorV13()
        
        self.stats = {
            'total': 0, 'sniper': 0, 'normal': 0, 'skip': 0,
            'bets': 0, 'wins': 0, 'losses': 0,
            'stake': 0.0, 'pnl': 0.0,
            'by_market': defaultdict(lambda: {'bets': 0, 'wins': 0, 'losses': 0, 'pnl': 0}),
            'by_action': defaultdict(lambda: {'bets': 0, 'wins': 0, 'losses': 0, 'pnl': 0}),
        }
    
    def get_matches(self, limit=100):
        self.cur.execute("""
            SELECT DISTINCT ON (home_team, away_team, DATE(commence_time))
                home_team, away_team, league, score_home, score_away
            FROM match_results
            WHERE is_finished = TRUE
            AND commence_time >= NOW() - INTERVAL '%s days'
            AND score_home IS NOT NULL
            ORDER BY home_team, away_team, DATE(commence_time), commence_time DESC
            LIMIT %s
        """, (self.days, limit))
        return self.cur.fetchall()
    
    def normalize_name(self, name):
        mappings = {
            'FC Barcelona': 'Barcelona', 'Club Atlético de Madrid': 'Atlético Madrid',
            'Real Madrid CF': 'Real Madrid', 'Athletic Club': 'Athletic Bilbao',
            'Liverpool FC': 'Liverpool', 'Manchester City FC': 'Manchester City',
            'Arsenal FC': 'Arsenal', 'Chelsea FC': 'Chelsea',
            'FC Bayern München': 'Bayern Munich', 'Borussia Dortmund': 'Dortmund',
            'Bayer 04 Leverkusen': 'Leverkusen', 'AS Monaco': 'Monaco',
            'Olympique de Marseille': 'Marseille', 'Paris Saint-Germain FC': 'PSG',
            'FC Internazionale Milano': 'Inter', 'Juventus FC': 'Juventus',
            'SSC Napoli': 'Napoli', 'AS Roma': 'Roma', 'SS Lazio': 'Lazio',
            'ACF Fiorentina': 'Fiorentina', 'AC Milan': 'AC Milan',
            'Tottenham Hotspur FC': 'Tottenham', 'Newcastle United FC': 'Newcastle',
            'Aston Villa FC': 'Aston Villa', 'AFC Bournemouth': 'Bournemouth',
            'West Ham United FC': 'West Ham', 'Brighton & Hove Albion FC': 'Brighton',
            'Wolverhampton Wanderers FC': 'Wolves', 'Brentford FC': 'Brentford',
        }
        clean = name.replace(' FC', '').replace(' CF', '').replace(' AFC', '').strip()
        return mappings.get(name, clean)
    
    def get_league(self, league):
        if not league: return 'Unknown'
        return {'Primera Division': 'La Liga'}.get(league, league)
    
    def evaluate(self, market, sh, sa):
        total = sh + sa
        btts = sh > 0 and sa > 0
        if market == 'over_25': return 'WIN' if total > 2.5 else 'LOSS'
        if market == 'over_35': return 'WIN' if total > 3.5 else 'LOSS'
        if market == 'btts': return 'WIN' if btts else 'LOSS'
        return 'UNKNOWN'
    
    def run(self, limit=100):
        print("=" * 100)
        print(f"🔬 BACKTEST V13 MULTI-STRIKE - {self.days} JOURS")
        print("=" * 100)
        
        matches = self.get_matches(limit)
        self.stats['total'] = len(matches)
        print(f"\n📊 {len(matches)} matchs\n")
        
        for i, m in enumerate(matches, 1):
            home = self.normalize_name(m['home_team'])
            away = self.normalize_name(m['away_team'])
            league = self.get_league(m['league'])
            sh, sa = m['score_home'], m['score_away']
            
            result = self.v13.analyze_match(home, away, league)
            
            if not result or not result.bets:
                self.stats['skip'] += 1
                continue
            
            action = result.v11_action
            if 'SNIPER' in action: self.stats['sniper'] += 1
            elif 'NORMAL' in action: self.stats['normal'] += 1
            
            print(f"[{i}] {home} vs {away} ({sh}-{sa}) | Score={result.v11_score:.1f} {action}")
            
            for bet in result.bets:
                outcome = self.evaluate(bet.market, sh, sa)
                odds = bet.odds_estimate
                stake = bet.stake_units
                pnl = stake * (odds - 1) if outcome == 'WIN' else -stake
                
                self.stats['bets'] += 1
                self.stats['stake'] += stake
                self.stats['pnl'] += pnl
                
                if outcome == 'WIN':
                    self.stats['wins'] += 1
                    self.stats['by_market'][bet.market]['wins'] += 1
                    self.stats['by_action'][action]['wins'] += 1
                else:
                    self.stats['losses'] += 1
                    self.stats['by_market'][bet.market]['losses'] += 1
                    self.stats['by_action'][action]['losses'] += 1
                
                self.stats['by_market'][bet.market]['bets'] += 1
                self.stats['by_market'][bet.market]['pnl'] += pnl
                self.stats['by_action'][action]['bets'] += 1
                self.stats['by_action'][action]['pnl'] += pnl
                
                icon = "✅" if outcome == 'WIN' else "❌"
                print(f"    {icon} {bet.market:10} @ {odds:.2f} → {outcome} ({pnl:+.2f}u)")
        
        self.print_summary()
    
    def print_summary(self):
        s = self.stats
        print("\n" + "=" * 100)
        print("📊 RÉSUMÉ V13 MULTI-STRIKE")
        print("=" * 100)
        
        print(f"\n📈 GLOBAL:")
        print(f"   Matchs: {s['total']} | SNIPER: {s['sniper']} | NORMAL: {s['normal']} | SKIP: {s['skip']}")
        print(f"   Paris: {s['bets']} | Wins: {s['wins']} | Losses: {s['losses']}")
        
        if s['bets'] > 0:
            wr = s['wins'] / s['bets'] * 100
            roi = s['pnl'] / s['stake'] * 100 if s['stake'] > 0 else 0
            print(f"   Win Rate: {wr:.1f}% | ROI: {roi:+.1f}%")
            print(f"   Stake: {s['stake']:.1f}u | P&L: {s['pnl']:+.1f}u")
        
        print(f"\n📊 PAR MARCHÉ:")
        for market in ['over_25', 'btts', 'over_35']:
            d = s['by_market'][market]
            if d['bets'] > 0:
                wr = d['wins'] / d['bets'] * 100
                icon = "✅" if d['pnl'] > 0 else "❌"
                print(f"   {icon} {market:10}: {d['wins']}/{d['bets']} ({wr:.0f}%) | P&L: {d['pnl']:+.1f}u")
        
        print(f"\n📊 PAR ACTION:")
        for action in ['SNIPER_BET', 'NORMAL_BET']:
            d = s['by_action'][action]
            if d['bets'] > 0:
                wr = d['wins'] / d['bets'] * 100
                print(f"   {action:12}: {d['wins']}/{d['bets']} ({wr:.0f}%) | P&L: {d['pnl']:+.1f}u")


if __name__ == "__main__":
    bt = BacktestV13(days=30)
    bt.run(limit=100)
    print("\n✅ Backtest terminé!")
