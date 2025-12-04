#!/usr/bin/env python3
"""
BACKTEST COMPLET ORCHESTRATOR V11.4 PURE
=========================================
Analyse détaillée sur 30-60 jours sans Smart Market.
V11.4 = GOD TIER (Dixon-Coles, Steam, Portfolio Kelly)
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
import sys

# Import V11.4 SEUL
from orchestrator_v11_4_god_tier import OrchestratorV11_4

class BacktestV11_4Pure:
    """Backtest du système V11.4 PURE sur matchs passés"""
    
    def __init__(self, days: int = 30):
        self.days = days
        self.conn = psycopg2.connect(
            host='localhost', port=5432, dbname='monps_db',
            user='monps_user', password='monps_secure_password_2024'
        )
        self.cur = self.conn.cursor(cursor_factory=RealDictCursor)
        self.orch = OrchestratorV11_4()
        
        # Résultats détaillés
        self.results = []
        self.stats = {
            'total_matches': 0,
            'analyzed': 0,
            'skipped': 0,
            'sniper_bets': 0,
            'normal_bets': 0,
            'wins': 0,
            'losses': 0,
            'push': 0,
            'total_stake': 0.0,
            'total_return': 0.0,
            'by_action': defaultdict(lambda: {'bets': 0, 'wins': 0, 'losses': 0, 'stake': 0, 'pnl': 0}),
            'by_market': defaultdict(lambda: {'bets': 0, 'wins': 0, 'losses': 0, 'stake': 0, 'pnl': 0}),
            'by_league': defaultdict(lambda: {'bets': 0, 'wins': 0, 'losses': 0, 'stake': 0, 'pnl': 0}),
            'by_score_range': defaultdict(lambda: {'bets': 0, 'wins': 0, 'losses': 0, 'stake': 0, 'pnl': 0}),
            'details': []
        }
    
    def get_recent_matches(self, limit: int = 100) -> List[Dict]:
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
        mappings = {
            'FC Barcelona': 'Barcelona',
            'Club Atlético de Madrid': 'Atlético Madrid',
            'Real Madrid CF': 'Real Madrid',
            'Athletic Club': 'Athletic Bilbao',
            'Liverpool FC': 'Liverpool',
            'Manchester City FC': 'Manchester City',
            'Manchester United FC': 'Manchester United',
            'Arsenal FC': 'Arsenal',
            'Chelsea FC': 'Chelsea',
            'AS Monaco': 'Monaco',
            'Olympique de Marseille': 'Marseille',
            'Olympique Lyonnais': 'Lyon',
            'Paris Saint-Germain FC': 'PSG',
            'FC Bayern München': 'Bayern Munich',
            'Borussia Dortmund': 'Dortmund',
            'RB Leipzig': 'RB Leipzig',
            'Bayer 04 Leverkusen': 'Leverkusen',
            'VfB Stuttgart': 'Stuttgart',
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
            'West Ham United FC': 'West Ham',
            'Everton FC': 'Everton',
            'AFC Bournemouth': 'Bournemouth',
            'Fulham FC': 'Fulham',
            'SS Lazio': 'Lazio',
            'AS Roma': 'Roma',
            'SSC Napoli': 'Napoli',
            'AC Milan': 'AC Milan',
            'FC Internazionale Milano': 'Inter',
            'Juventus FC': 'Juventus',
            'ACF Fiorentina': 'Fiorentina',
            'Atalanta BC': 'Atalanta',
            'Bologna FC 1909': 'Bologna',
            'Torino FC': 'Torino',
        }
        
        # Nettoyer
        clean = name.replace(' FC', '').replace(' CF', '').replace(' AFC', '').strip()
        return mappings.get(name, clean)
    
    def get_league_name(self, league: str) -> str:
        """Normalise le nom de la ligue"""
        if not league:
            return 'Unknown'
        mappings = {
            'Premier League': 'Premier League',
            'La Liga': 'La Liga',
            'Primera Division': 'La Liga',
            'Bundesliga': 'Bundesliga',
            'Serie A': 'Serie A',
            'Ligue 1': 'Ligue 1',
            'Champions League': 'Champions League',
        }
        return mappings.get(league, league)
    
    def evaluate_result(self, market: str, score_home: int, score_away: int) -> str:
        """Évalue si le pari est gagnant"""
        total_goals = score_home + score_away
        btts = score_home > 0 and score_away > 0
        
        # Over/Under
        if market == 'over_25' or market == 'over_2.5':
            return 'WIN' if total_goals > 2.5 else 'LOSS'
        if market == 'over_35' or market == 'over_3.5':
            return 'WIN' if total_goals > 3.5 else 'LOSS'
        if market == 'over_15' or market == 'over_1.5':
            return 'WIN' if total_goals > 1.5 else 'LOSS'
        if market == 'under_25' or market == 'under_2.5':
            return 'WIN' if total_goals < 2.5 else 'LOSS'
        if market == 'under_35' or market == 'under_3.5':
            return 'WIN' if total_goals < 3.5 else 'LOSS'
        
        # BTTS
        if market == 'btts_yes':
            return 'WIN' if btts else 'LOSS'
        if market == 'btts_no':
            return 'WIN' if not btts else 'LOSS'
        
        return 'UNKNOWN'
    
    def get_score_range(self, score: float) -> str:
        """Retourne la tranche de score"""
        if score >= 32:
            return '32+'
        elif score >= 30:
            return '30-32'
        elif score >= 28:
            return '28-30'
        elif score >= 26:
            return '26-28'
        elif score >= 24:
            return '24-26'
        elif score >= 22:
            return '22-24'
        elif score >= 20:
            return '20-22'
        else:
            return '<20'
    
    def run_backtest(self, limit: int = 100):
        """Lance le backtest complet"""
        print("=" * 100)
        print(f"🔬 BACKTEST ORCHESTRATOR V11.4 PURE - {self.days} DERNIERS JOURS")
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
            btts = "Yes" if score_h > 0 and score_a > 0 else "No"
            
            print(f"\n[{i}/{len(matches)}] {home} vs {away} ({league})")
            print(f"   Score: {score_h}-{score_a} | Total: {total} | BTTS: {btts}")
            
            try:
                # Analyser avec V11.4 PURE
                result = self.orch.analyze_match(home, away, league)
                
                if not result:
                    print(f"   ❌ Pas de données")
                    self.stats['skipped'] += 1
                    continue
                
                v11_score = result.get('score', result.get('final_score', 0))
                action = result.get('action', result.get('recommendation', 'SKIP'))
                market = result.get('market', 'over_25')
                
                # Normaliser l'action
                if action in ['SNIPER_BET', 'SNIPER']:
                    action = 'SNIPER_BET'
                elif action in ['NORMAL_BET', 'NORMAL']:
                    action = 'NORMAL_BET'
                else:
                    action = 'SKIP'
                
                score_range = self.get_score_range(v11_score)
                
                print(f"   V11.4 Score: {v11_score:.1f} | Action: {action} | Market: {market}")
                
                # Si SNIPER ou NORMAL → on parie
                if action in ['SNIPER_BET', 'NORMAL_BET']:
                    # Stake selon action
                    if action == 'SNIPER_BET':
                        stake = 3.0  # 3 unités pour SNIPER
                        self.stats['sniper_bets'] += 1
                    else:
                        stake = 2.0  # 2 unités pour NORMAL
                        self.stats['normal_bets'] += 1
                    
                    # Cote moyenne estimée
                    odds = 1.85
                    
                    # Évaluer le résultat
                    outcome = self.evaluate_result(market, score_h, score_a)
                    
                    # Calculer P&L
                    if outcome == 'WIN':
                        pnl = stake * (odds - 1)
                        self.stats['wins'] += 1
                    elif outcome == 'LOSS':
                        pnl = -stake
                        self.stats['losses'] += 1
                    else:
                        pnl = 0
                        self.stats['push'] += 1
                    
                    self.stats['total_stake'] += stake
                    self.stats['total_return'] += pnl
                    
                    # Stats détaillées
                    for key, cat in [('by_action', action), ('by_market', market), 
                                     ('by_league', league), ('by_score_range', score_range)]:
                        self.stats[key][cat]['bets'] += 1
                        self.stats[key][cat]['stake'] += stake
                        self.stats[key][cat]['pnl'] += pnl
                        if outcome == 'WIN':
                            self.stats[key][cat]['wins'] += 1
                        else:
                            self.stats[key][cat]['losses'] += 1
                    
                    # Log détail
                    icon = "✅" if outcome == 'WIN' else "❌"
                    print(f"   {icon} {action} → {market} @ {odds:.2f} → {outcome} (P&L: {pnl:+.2f}u)")
                    
                    self.stats['details'].append({
                        'match': f"{home} vs {away}",
                        'league': league,
                        'score': f"{score_h}-{score_a}",
                        'v11_score': v11_score,
                        'action': action,
                        'market': market,
                        'outcome': outcome,
                        'pnl': pnl
                    })
                    
                    self.stats['analyzed'] += 1
                else:
                    print(f"   ⏭️ SKIP (score {v11_score:.1f} < seuil)")
                    self.stats['skipped'] += 1
                    
            except Exception as e:
                print(f"   ❌ Erreur: {str(e)[:80]}")
                self.stats['skipped'] += 1
        
        self.print_detailed_summary()
    
    def print_detailed_summary(self):
        """Affiche le résumé détaillé du backtest"""
        s = self.stats
        
        print("\n" + "=" * 100)
        print("📊 RÉSUMÉ DÉTAILLÉ BACKTEST V11.4 PURE")
        print("=" * 100)
        
        # GLOBAL
        print(f"\n┌{'─'*98}┐")
        print(f"│ {'1️⃣  PERFORMANCE GLOBALE':<96} │")
        print(f"└{'─'*98}┘")
        print(f"   Matchs analysés: {s['total_matches']}")
        print(f"   Paris placés: {s['sniper_bets'] + s['normal_bets']} (SNIPER: {s['sniper_bets']}, NORMAL: {s['normal_bets']})")
        print(f"   Skip: {s['skipped']}")
        
        total_bets = s['wins'] + s['losses'] + s['push']
        if total_bets > 0:
            win_rate = s['wins'] / total_bets * 100
            roi = s['total_return'] / s['total_stake'] * 100 if s['total_stake'] > 0 else 0
            
            print(f"\n   �� RÉSULTATS:")
            print(f"   Wins: {s['wins']} | Losses: {s['losses']} | Push: {s['push']}")
            print(f"   Win Rate: {win_rate:.1f}%")
            print(f"   Total Stake: {s['total_stake']:.1f}u")
            print(f"   Total Return: {s['total_return']:+.1f}u")
            print(f"   ROI: {roi:+.1f}%")
        
        # PAR ACTION
        print(f"\n┌{'─'*98}┐")
        print(f"│ {'2️⃣  PERFORMANCE PAR ACTION':<96} │")
        print(f"└{'─'*98}┘")
        for action in ['SNIPER_BET', 'NORMAL_BET']:
            data = s['by_action'][action]
            if data['bets'] > 0:
                wr = data['wins'] / data['bets'] * 100
                roi = data['pnl'] / data['stake'] * 100 if data['stake'] > 0 else 0
                icon = "🎯" if action == 'SNIPER_BET' else "📈"
                print(f"   {icon} {action:15}: {data['wins']:2}/{data['bets']:2} ({wr:5.1f}%) | P&L: {data['pnl']:+6.1f}u | ROI: {roi:+.1f}%")
        
        # PAR TRANCHE DE SCORE
        print(f"\n┌{'─'*98}┐")
        print(f"│ {'3️⃣  PERFORMANCE PAR SCORE V11.4':<96} │")
        print(f"└{'─'*98}┘")
        for score_range in ['32+', '30-32', '28-30', '26-28', '24-26', '22-24', '20-22', '<20']:
            data = s['by_score_range'][score_range]
            if data['bets'] > 0:
                wr = data['wins'] / data['bets'] * 100
                roi = data['pnl'] / data['stake'] * 100 if data['stake'] > 0 else 0
                bar = "█" * int(wr / 5) + "░" * (20 - int(wr / 5))
                status = "✅" if wr >= 50 else "❌"
                print(f"   {status} {score_range:8}: {data['wins']:2}/{data['bets']:2} ({wr:5.1f}%) | ROI: {roi:+6.1f}% | {bar}")
        
        # PAR MARCHÉ
        print(f"\n┌{'─'*98}┐")
        print(f"│ {'4️⃣  PERFORMANCE PAR MARCHÉ':<96} │")
        print(f"└{'─'*98}┘")
        for market, data in sorted(s['by_market'].items(), key=lambda x: -x[1]['pnl']):
            if data['bets'] > 0:
                wr = data['wins'] / data['bets'] * 100
                roi = data['pnl'] / data['stake'] * 100 if data['stake'] > 0 else 0
                status = "✅" if data['pnl'] > 0 else "❌"
                print(f"   {status} {market:20}: {data['wins']:2}/{data['bets']:2} ({wr:5.1f}%) | P&L: {data['pnl']:+6.1f}u | ROI: {roi:+.1f}%")
        
        # PAR LIGUE
        print(f"\n┌{'─'*98}┐")
        print(f"│ {'5️⃣  PERFORMANCE PAR LIGUE':<96} │")
        print(f"└{'─'*98}┘")
        for league, data in sorted(s['by_league'].items(), key=lambda x: -x[1]['pnl']):
            if data['bets'] > 0:
                wr = data['wins'] / data['bets'] * 100
                roi = data['pnl'] / data['stake'] * 100 if data['stake'] > 0 else 0
                status = "✅" if data['pnl'] > 0 else "❌"
                print(f"   {status} {league:25}: {data['wins']:2}/{data['bets']:2} ({wr:5.1f}%) | P&L: {data['pnl']:+6.1f}u | ROI: {roi:+.1f}%")
        
        # DÉTAIL DES PARIS
        print(f"\n┌{'─'*98}┐")
        print(f"│ {'6️⃣  DÉTAIL DE TOUS LES PARIS':<96} │")
        print(f"└{'─'*98}┘")
        for i, bet in enumerate(s['details'], 1):
            icon = "✅" if bet['outcome'] == 'WIN' else "❌"
            print(f"   {icon} {bet['match']:40} | {bet['score']:5} | {bet['action']:12} | {bet['market']:10} | Score:{bet['v11_score']:5.1f} | {bet['pnl']:+.1f}u")
        
        # FORCES ET FAIBLESSES
        print(f"\n┌{'─'*98}┐")
        print(f"│ {'7️⃣  FORCES ET FAIBLESSES':<96} │")
        print(f"└{'─'*98}┘")
        
        # Meilleures performances
        print("\n   💪 FORCES:")
        for action in ['SNIPER_BET', 'NORMAL_BET']:
            data = s['by_action'][action]
            if data['bets'] > 0 and data['pnl'] > 0:
                wr = data['wins'] / data['bets'] * 100
                print(f"      ✅ {action}: {wr:.0f}% WR, {data['pnl']:+.1f}u")
        
        best_market = max(s['by_market'].items(), key=lambda x: x[1]['pnl']) if s['by_market'] else None
        if best_market and best_market[1]['pnl'] > 0:
            print(f"      ✅ Meilleur marché: {best_market[0]} ({best_market[1]['pnl']:+.1f}u)")
        
        best_league = max(s['by_league'].items(), key=lambda x: x[1]['pnl']) if s['by_league'] else None
        if best_league and best_league[1]['pnl'] > 0:
            print(f"      ✅ Meilleure ligue: {best_league[0]} ({best_league[1]['pnl']:+.1f}u)")
        
        # Faiblesses
        print("\n   ⚠️ FAIBLESSES:")
        worst_market = min(s['by_market'].items(), key=lambda x: x[1]['pnl']) if s['by_market'] else None
        if worst_market and worst_market[1]['pnl'] < 0:
            print(f"      ❌ Pire marché: {worst_market[0]} ({worst_market[1]['pnl']:+.1f}u)")
        
        worst_league = min(s['by_league'].items(), key=lambda x: x[1]['pnl']) if s['by_league'] else None
        if worst_league and worst_league[1]['pnl'] < 0:
            print(f"      ❌ Pire ligue: {worst_league[0]} ({worst_league[1]['pnl']:+.1f}u)")
        
        # CONCLUSION
        print(f"\n┌{'─'*98}┐")
        print(f"│ {'8️⃣  CONCLUSION':<96} │")
        print(f"└{'─'*98}┘")
        
        if total_bets > 0:
            win_rate = s['wins'] / total_bets * 100
            roi = s['total_return'] / s['total_stake'] * 100 if s['total_stake'] > 0 else 0
            
            if win_rate >= 80:
                print(f"\n   🏆 EXCELLENT! Win Rate {win_rate:.0f}%, ROI {roi:+.0f}%")
                print(f"   → V11.4 PURE est très performant!")
            elif win_rate >= 60:
                print(f"\n   ✅ BON! Win Rate {win_rate:.0f}%, ROI {roi:+.0f}%")
                print(f"   → V11.4 PURE est rentable")
            else:
                print(f"\n   ⚠️ ATTENTION! Win Rate {win_rate:.0f}%, ROI {roi:+.0f}%")
                print(f"   → Revoir les seuils")
    
    def close(self):
        self.orch.close()
        self.conn.close()


if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    
    bt = BacktestV11_4Pure(days=days)
    bt.run_backtest(limit=limit)
    bt.close()
    
    print("\n" + "=" * 100)
    print("✅ Backtest V11.4 PURE terminé!")
    print("=" * 100)
