#!/usr/bin/env python3
"""
BACKTEST COMPLET ORCHESTRATOR V12.1
====================================
Analyse les 60 derniers matchs terminés pour valider le système.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sys

# Import de l'orchestrateur final
from orchestrator_v12_1_consensus import OrchestratorV12_1

class BacktestV12:
    """Backtest du système V12.1 sur matchs passés"""
    
    def __init__(self, days: int = 30):
        self.days = days
        self.conn = psycopg2.connect(
            host='localhost', port=5432, dbname='monps_db',
            user='monps_user', password='monps_secure_password_2024'
        )
        self.cur = self.conn.cursor(cursor_factory=RealDictCursor)
        self.orch = OrchestratorV12_1()
        
        # Résultats
        self.results = []
        self.stats = {
            'total_matches': 0,
            'analyzed': 0,
            'skipped': 0,
            'bets_placed': 0,
            'wins': 0,
            'losses': 0,
            'push': 0,
            'total_stake': 0,
            'total_return': 0,
            'by_consensus': {},
            'by_market': {}
        }
    
    def get_recent_matches(self, limit: int = 60) -> List[Dict]:
        """Récupère les matchs terminés récents"""
        self.cur.execute("""
            SELECT DISTINCT ON (home_team, away_team, DATE(commence_time))
                match_id, home_team, away_team, league,
                commence_time, score_home, score_away, outcome
            FROM match_results
            WHERE is_finished = TRUE
            AND commence_time >= NOW() - INTERVAL '%s days'
            AND score_home IS NOT NULL
            ORDER BY home_team, away_team, DATE(commence_time), commence_time DESC
            LIMIT %s
        """, (self.days, limit))
        
        return self.cur.fetchall()
    
    def normalize_team_name(self, name: str) -> str:
        """Normalise le nom d'équipe pour matching"""
        # Retirer suffixes courants
        name = name.replace(' FC', '').replace(' CF', '').replace(' AFC', '')
        name = name.replace('Club ', '').replace(' Club', '')
        
        # Mappings connus
        mappings = {
            'FC Barcelona': 'Barcelona',
            'Club Atlético de Madrid': 'Atlético Madrid',
            'Real Madrid CF': 'Real Madrid',
            'Athletic Club': 'Athletic Bilbao',
            'Liverpool FC': 'Liverpool',
            'Manchester City FC': 'Manchester City',
            'Arsenal FC': 'Arsenal',
            'Chelsea FC': 'Chelsea',
            'AS Monaco': 'Monaco',
            'Olympique de Marseille': 'Marseille',
            'Bayern Munich': 'Bayern Munich',
            'Wolverhampton Wanderers FC': 'Wolves',
            'Brighton & Hove Albion FC': 'Brighton',
            'Nottingham Forest FC': 'Nottingham Forest',
            'Tottenham Hotspur FC': 'Tottenham',
            'Newcastle United FC': 'Newcastle',
            'Brentford FC': 'Brentford',
            'Aston Villa FC': 'Aston Villa',
            'Crystal Palace FC': 'Crystal Palace',
            'Burnley FC': 'Burnley',
            'Leeds United FC': 'Leeds',
            'Sunderland AFC': 'Sunderland',
        }
        
        return mappings.get(name, name.replace(' FC', '').replace(' CF', '').strip())
    
    def get_league_name(self, league: str) -> str:
        """Normalise le nom de la ligue"""
        mappings = {
            'Premier League': 'Premier League',
            'La Liga': 'La Liga',
            'Primera Division': 'La Liga',
            'Bundesliga': 'Bundesliga',
            'Serie A': 'Serie A',
            'Ligue 1': 'Ligue 1',
        }
        return mappings.get(league, league)
    
    def evaluate_bet(self, rec: Dict, score_home: int, score_away: int) -> str:
        """Évalue si le pari est gagnant"""
        total_goals = score_home + score_away
        market = rec['market']
        
        # Over/Under
        if market.startswith('over_'):
            line = float(market.split('_')[1])
            if total_goals > line:
                return 'WIN'
            elif total_goals == line:
                return 'PUSH'
            else:
                return 'LOSS'
        
        if market.startswith('under_'):
            line = float(market.split('_')[1])
            if total_goals < line:
                return 'WIN'
            elif total_goals == line:
                return 'PUSH'
            else:
                return 'LOSS'
        
        # Asian Handicap Home
        if market.startswith('ah_home_'):
            line = float(market.split('_')[2])
            adjusted_home = score_home + line
            if adjusted_home > score_away:
                return 'WIN'
            elif adjusted_home == score_away:
                return 'PUSH'
            else:
                return 'LOSS'
        
        # BTTS
        if market == 'btts_yes':
            return 'WIN' if score_home > 0 and score_away > 0 else 'LOSS'
        if market == 'btts_no':
            return 'WIN' if score_home == 0 or score_away == 0 else 'LOSS'
        
        return 'UNKNOWN'
    
    def run_backtest(self, limit: int = 60):
        """Lance le backtest complet"""
        print("=" * 100)
        print(f"🔬 BACKTEST ORCHESTRATOR V12.1 - {self.days} DERNIERS JOURS")
        print("=" * 100)
        
        matches = self.get_recent_matches(limit)
        self.stats['total_matches'] = len(matches)
        
        print(f"\n📊 {len(matches)} matchs à analyser")
        print("-" * 100)
        
        for i, match in enumerate(matches, 1):
            home = self.normalize_team_name(match['home_team'])
            away = self.normalize_team_name(match['away_team'])
            league = self.get_league_name(match['league'])
            score_h = match['score_home']
            score_a = match['score_away']
            total = score_h + score_a
            
            print(f"\n[{i}/{len(matches)}] {home} vs {away} ({league})")
            print(f"   Score: {score_h}-{score_a} (Total: {total})")
            
            try:
                # Analyser avec V12.1 (sans logger CLV)
                result = self.orch.analyze_match_v12(home, away, league, log_clv=False)
                
                consensus = result['consensus']
                action = consensus['action']
                best_bet = consensus['best_bet']
                
                print(f"   Consensus: {action}")
                
                # Si pas de SKIP et best_bet existe
                if action not in ['SKIP', 'BAD_PRICE'] and best_bet:
                    market = best_bet['market']
                    odds = best_bet['odds']
                    kelly = consensus['kelly_adjusted']
                    stake_mult = consensus['stake_multiplier']
                    
                    # Évaluer le résultat
                    outcome = self.evaluate_bet(best_bet, score_h, score_a)
                    
                    # Calculer P&L
                    stake = kelly * 100  # Stake en unités
                    if outcome == 'WIN':
                        pnl = stake * (odds - 1)
                        self.stats['wins'] += 1
                    elif outcome == 'LOSS':
                        pnl = -stake
                        self.stats['losses'] += 1
                    else:  # PUSH
                        pnl = 0
                        self.stats['push'] += 1
                    
                    self.stats['bets_placed'] += 1
                    self.stats['total_stake'] += stake
                    self.stats['total_return'] += pnl
                    
                    # Stats par consensus
                    if action not in self.stats['by_consensus']:
                        self.stats['by_consensus'][action] = {'bets': 0, 'wins': 0, 'pnl': 0}
                    self.stats['by_consensus'][action]['bets'] += 1
                    if outcome == 'WIN':
                        self.stats['by_consensus'][action]['wins'] += 1
                    self.stats['by_consensus'][action]['pnl'] += pnl
                    
                    # Stats par marché
                    market_type = market.split('_')[0] + '_' + market.split('_')[1] if '_' in market else market
                    if market_type not in self.stats['by_market']:
                        self.stats['by_market'][market_type] = {'bets': 0, 'wins': 0, 'pnl': 0}
                    self.stats['by_market'][market_type]['bets'] += 1
                    if outcome == 'WIN':
                        self.stats['by_market'][market_type]['wins'] += 1
                    self.stats['by_market'][market_type]['pnl'] += pnl
                    
                    # Log
                    icon = "✅" if outcome == 'WIN' else "❌" if outcome == 'LOSS' else "➖"
                    print(f"   {icon} {market} @ {odds:.2f} → {outcome} (P&L: {pnl:+.2f}u)")
                    
                    self.results.append({
                        'match': f"{home} vs {away}",
                        'score': f"{score_h}-{score_a}",
                        'consensus': action,
                        'market': market,
                        'odds': odds,
                        'outcome': outcome,
                        'pnl': pnl
                    })
                    
                    self.stats['analyzed'] += 1
                else:
                    print(f"   ⏭️ SKIP (pas de pari)")
                    self.stats['skipped'] += 1
                    
            except Exception as e:
                print(f"   ❌ Erreur: {str(e)[:50]}")
                self.stats['skipped'] += 1
        
        self.print_summary()
    
    def print_summary(self):
        """Affiche le résumé du backtest"""
        print("\n" + "=" * 100)
        print("📊 RÉSUMÉ BACKTEST V12.1")
        print("=" * 100)
        
        s = self.stats
        
        print(f"\n📈 GLOBAL:")
        print(f"   Matchs analysés: {s['total_matches']}")
        print(f"   Paris placés: {s['bets_placed']}")
        print(f"   Skip: {s['skipped']}")
        
        if s['bets_placed'] > 0:
            win_rate = s['wins'] / s['bets_placed'] * 100
            roi = s['total_return'] / s['total_stake'] * 100 if s['total_stake'] > 0 else 0
            
            print(f"\n📊 PERFORMANCE:")
            print(f"   Wins: {s['wins']} | Losses: {s['losses']} | Push: {s['push']}")
            print(f"   Win Rate: {win_rate:.1f}%")
            print(f"   Total Stake: {s['total_stake']:.1f}u")
            print(f"   Total Return: {s['total_return']:+.1f}u")
            print(f"   ROI: {roi:+.1f}%")
        
        if s['by_consensus']:
            print(f"\n📊 PAR TYPE DE CONSENSUS:")
            for action, data in sorted(s['by_consensus'].items()):
                wr = data['wins'] / data['bets'] * 100 if data['bets'] > 0 else 0
                print(f"   {action}: {data['bets']} paris | WR: {wr:.0f}% | P&L: {data['pnl']:+.1f}u")
        
        if s['by_market']:
            print(f"\n📊 PAR MARCHÉ:")
            for market, data in sorted(s['by_market'].items()):
                wr = data['wins'] / data['bets'] * 100 if data['bets'] > 0 else 0
                print(f"   {market}: {data['bets']} paris | WR: {wr:.0f}% | P&L: {data['pnl']:+.1f}u")
        
        # Forces et faiblesses
        print("\n" + "=" * 100)
        print("💪 FORCES ET ⚠️ FAIBLESSES")
        print("=" * 100)
        
        if s['by_consensus']:
            best_consensus = max(s['by_consensus'].items(), key=lambda x: x[1]['pnl']) if s['by_consensus'] else None
            worst_consensus = min(s['by_consensus'].items(), key=lambda x: x[1]['pnl']) if s['by_consensus'] else None
            
            if best_consensus:
                print(f"\n💪 Meilleur consensus: {best_consensus[0]} (P&L: {best_consensus[1]['pnl']:+.1f}u)")
            if worst_consensus and worst_consensus[1]['pnl'] < 0:
                print(f"⚠️ Pire consensus: {worst_consensus[0]} (P&L: {worst_consensus[1]['pnl']:+.1f}u)")
        
        if s['by_market']:
            best_market = max(s['by_market'].items(), key=lambda x: x[1]['pnl']) if s['by_market'] else None
            worst_market = min(s['by_market'].items(), key=lambda x: x[1]['pnl']) if s['by_market'] else None
            
            if best_market:
                print(f"\n💪 Meilleur marché: {best_market[0]} (P&L: {best_market[1]['pnl']:+.1f}u)")
            if worst_market and worst_market[1]['pnl'] < 0:
                print(f"⚠️ Pire marché: {worst_market[0]} (P&L: {worst_market[1]['pnl']:+.1f}u)")
    
    def close(self):
        self.orch.close()
        self.conn.close()


if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    
    bt = BacktestV12(days=days)
    bt.run_backtest(limit=limit)
    bt.close()
    
    print("\n✅ Backtest terminé!")
