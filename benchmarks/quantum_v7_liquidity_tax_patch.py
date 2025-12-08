#!/usr/bin/env python3
"""
QUANTUM V7.1 - LIQUIDITY TAX PATCH
Filtre les paris sur équipes élites avec cotes écrasées
"""

import asyncio
import asyncpg
import json

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

class LiquidityTaxValidator:
    """Validateur de paris avec règle Liquidity Tax"""
    
    def __init__(self):
        self.elite_teams = []
        self.min_odds_elite = 1.50
        self.min_edge_multiplier = 2.0
        self.max_stake_pct = 50
        self.base_edge = 2.0  # Edge minimum de base (2%)
        
    async def load_rules(self):
        """Charge les règles depuis la DB"""
        pool = await asyncpg.create_pool(**DB_CONFIG)
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT rule_value 
                FROM quantum.betting_rules 
                WHERE rule_name = 'LIQUIDITY_TAX'
            """)
            if row:
                rules = json.loads(row['rule_value']) if isinstance(row['rule_value'], str) else row['rule_value']
                self.elite_teams = rules.get('elite_teams', [])
                self.min_odds_elite = float(rules.get('min_odds_elite', 1.50))
                self.min_edge_multiplier = float(rules.get('min_edge_multiplier', 2.0))
                self.max_stake_pct = int(rules.get('max_stake_pct', 50))
                print(f"✅ LIQUIDITY_TAX chargé: {len(self.elite_teams)} équipes élites")
        await pool.close()
    
    def validate_bet(self, team: str, odds: float, edge: float, stake_pct: float = 100) -> dict:
        """
        Valide un pari avec la règle Liquidity Tax
        
        Returns:
            dict: {
                'valid': bool,
                'reason': str,
                'adjusted_stake': float,
                'warnings': list
            }
        """
        result = {
            'valid': True,
            'reason': 'OK',
            'adjusted_stake': stake_pct,
            'warnings': [],
            'is_elite': False
        }
        
        # Vérifier si équipe élite
        if team in self.elite_teams:
            result['is_elite'] = True
            result['warnings'].append(f"⚠️ ELITE TEAM: {team}")
            
            # Règle 1: Cote minimum
            if odds < self.min_odds_elite:
                result['valid'] = False
                result['reason'] = f"❌ LIQUIDITY_TAX: Cote {odds:.2f} < min {self.min_odds_elite} pour équipe élite"
                return result
            
            # Règle 2: Edge requis doublé
            required_edge = self.base_edge * self.min_edge_multiplier
            if edge < required_edge:
                result['valid'] = False
                result['reason'] = f"❌ LIQUIDITY_TAX: Edge {edge:.1f}% < requis {required_edge:.1f}% pour équipe élite"
                return result
            
            # Règle 3: Stake réduit
            result['adjusted_stake'] = min(stake_pct, self.max_stake_pct)
            if result['adjusted_stake'] < stake_pct:
                result['warnings'].append(f"⚠️ Stake réduit: {stake_pct}% → {result['adjusted_stake']}%")
        
        return result
    
    def analyze_historical(self, team: str, markets: dict) -> dict:
        """Analyse l'historique d'une équipe avec Liquidity Tax"""
        analysis = {
            'team': team,
            'is_elite': team in self.elite_teams,
            'total_bets': 0,
            'blocked_bets': 0,
            'potential_savings': 0.0,
            'valid_bets': [],
            'blocked_details': []
        }
        
        if not analysis['is_elite']:
            return analysis
        
        for market, data in markets.items():
            if not isinstance(data, dict):
                continue
                
            picks = data.get('picks', 0)
            pnl = data.get('pnl', 0)
            avg_odds = data.get('avg_odds', 0)
            
            analysis['total_bets'] += picks
            
            # Simuler la validation
            if avg_odds < self.min_odds_elite:
                analysis['blocked_bets'] += picks
                analysis['potential_savings'] += abs(pnl) if pnl < 0 else 0
                analysis['blocked_details'].append({
                    'market': market,
                    'picks': picks,
                    'odds': avg_odds,
                    'pnl': pnl,
                    'reason': f"Cote {avg_odds:.2f} < {self.min_odds_elite}"
                })
            else:
                analysis['valid_bets'].append({
                    'market': market,
                    'picks': picks,
                    'odds': avg_odds,
                    'pnl': pnl
                })
        
        return analysis


async def test_liquidity_tax():
    """Test de la règle Liquidity Tax sur les données historiques"""
    validator = LiquidityTaxValidator()
    await validator.load_rules()
    
    print("\n" + "="*80)
    print("🏦 TEST LIQUIDITY TAX - ANALYSE RÉTROSPECTIVE")
    print("="*80)
    
    # Charger les données V7
    try:
        with open('quantum_v7_smart_quant_latest.json', 'r') as f:
            v7_data = json.load(f)
    except FileNotFoundError:
        print("❌ Fichier V7 non trouvé")
        return
    
    teams = v7_data.get('teams', {})
    
    total_savings = 0
    total_blocked = 0
    
    print(f"\n📊 Équipes élites dans les données: {len(validator.elite_teams)}")
    print("-"*80)
    
    for team_name in validator.elite_teams:
        if team_name not in teams:
            continue
            
        team_data = teams[team_name]
        markets = team_data.get('markets', {})
        
        analysis = validator.analyze_historical(team_name, markets)
        
        if analysis['blocked_bets'] > 0:
            pnl = team_data.get('performance', {}).get('pnl', 0)
            
            print(f"\n🏆 {team_name}")
            print(f"   P&L actuel: {pnl:+.1f}u")
            print(f"   Paris bloqués: {analysis['blocked_bets']}/{analysis['total_bets']}")
            print(f"   Économies potentielles: +{analysis['potential_savings']:.1f}u")
            
            for blocked in analysis['blocked_details']:
                print(f"      ❌ {blocked['market']}: {blocked['picks']} paris @ {blocked['odds']:.2f} = {blocked['pnl']:+.1f}u")
            
            for valid in analysis['valid_bets'][:3]:
                print(f"      ✅ {valid['market']}: {valid['picks']} paris @ {valid['odds']:.2f} = {valid['pnl']:+.1f}u")
            
            total_savings += analysis['potential_savings']
            total_blocked += analysis['blocked_bets']
    
    print("\n" + "="*80)
    print(f"📊 RÉSUMÉ LIQUIDITY TAX")
    print(f"   Paris bloqués total: {total_blocked}")
    print(f"   Économies potentielles: +{total_savings:.1f}u")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_liquidity_tax())
