#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                                                                       ║
║     🧬 QUANTUM V6.0 TEAM-CENTRIC ADN ANALYSIS - HEDGE FUND GRADE                                                                      ║
║                                                                                                                                       ║
║  ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════   ║
║                                                                                                                                       ║
║  🎯 APPROCHE TEAM-CENTRIC:                                                                                                            ║
║     • Chaque équipe = Centre de l'analyse (1 équipe = 1 ADN = 1 stratégie)                                                            ║
║     • Toutes stratégies testées par équipe                                                                                            ║
║     • Top 3 stratégies identifiées                                                                                                    ║
║     • Classification des pertes par type (malchance vs erreur)                                                                        ║
║     • Marchés détaillés par équipe                                                                                                    ║
║     • Forces / Faiblesses basées sur ADN                                                                                              ║
║     • Stratégie personnalisée recommandée                                                                                             ║
║                                                                                                                                       ║
║  📊 SOURCES DE DONNÉES:                                                                                                               ║
║     • quantum.team_strategies (92 équipes, 812 bets, +561.9u)                                                                         ║
║     • quantum.team_profiles (99 équipes avec ADN complet)                                                                             ║
║     • tracking_clv_picks (détail par marché avec scores)                                                                              ║
║     • quantum.team_name_mapping (99 mappings)                                                                                         ║
║     • audit_complet_99_equipes.json (source originale)                                                                                ║
║                                                                                                                                       ║
║  🔬 PRINCIPE MYA: "1 équipe = 1 ADN = 1 stratégie personnalisée"                                                                      ║
║                                                                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import asyncpg
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import json
import argparse

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

# Couleurs ANSI
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'
    GOLD = '\033[38;5;220m'
    PURPLE = '\033[38;5;135m'
    ORANGE = '\033[38;5;214m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'

# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class StrategyResult:
    """Résultat d'une stratégie pour une équipe"""
    strategy: str
    bets: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    pnl: float = 0.0
    roi: float = 0.0
    unlucky: int = 0
    bad_analysis: int = 0


@dataclass
class MarketResult:
    """Résultat d'un marché pour une équipe"""
    market: str
    picks: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    pnl: float = 0.0
    avg_odds: float = 0.0


@dataclass
class TeamAnalysis:
    """Analyse complète d'une équipe"""
    team_name: str
    league: str = ""
    
    # Performance globale (from team_strategies)
    total_bets: int = 0
    total_wins: int = 0
    total_losses: int = 0
    global_wr: float = 0.0
    global_pnl: float = 0.0
    global_roi: float = 0.0
    unlucky_pct: float = 0.0
    bad_analysis_pct: float = 0.0
    
    # Stratégies testées
    best_strategy: str = ""
    all_strategies: List[StrategyResult] = field(default_factory=list)
    
    # Marchés détaillés (from tracking_clv_picks)
    markets: Dict[str, MarketResult] = field(default_factory=dict)
    best_market: str = ""
    worst_market: str = ""
    
    # ADN metrics
    killer_instinct: float = 0.0
    panic_factor: float = 0.0
    diesel_factor: float = 0.0
    luck: float = 0.0
    home_strength: int = 0
    away_strength: int = 0
    btts_tendency: int = 0
    set_piece_threat: float = 0.0
    style: str = ""
    
    # Forces et faiblesses
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    
    # Stratégie personnalisée recommandée
    recommended_strategy: str = ""
    recommendation_reason: str = ""
    
    # Diagnostic
    tier: str = ""
    diagnostic: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# QUANTUM V6 TEAM-CENTRIC ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

class QuantumV6TeamCentric:
    """V6 Team-Centric Analysis - 1 équipe = 1 ADN = 1 stratégie"""
    
    def __init__(self):
        self.pool = None
        self.teams: Dict[str, TeamAnalysis] = {}
        self.name_mapping: Dict[str, str] = {}  # quantum_name -> historical_name
        self.reverse_mapping: Dict[str, str] = {}  # historical_name -> quantum_name
        
    async def connect(self):
        """Connexion à la base de données"""
        self.pool = await asyncpg.create_pool(**DB_CONFIG, min_size=2, max_size=10)
        print(f"{Colors.GREEN}✅ Connexion PostgreSQL établie{Colors.END}")
        
    async def close(self):
        """Fermeture de la connexion"""
        if self.pool:
            await self.pool.close()
            print(f"{Colors.CYAN}🔌 Connexion fermée{Colors.END}")
    
    async def load_name_mapping(self):
        """Charge le mapping des noms d'équipes"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT quantum_name, historical_name 
                FROM quantum.team_name_mapping
            """)
            for row in rows:
                self.name_mapping[row['quantum_name']] = row['historical_name']
                self.reverse_mapping[row['historical_name']] = row['quantum_name']
            print(f"{Colors.CYAN}📊 {len(self.name_mapping)} mappings chargés{Colors.END}")
    
    async def load_team_strategies(self):
        """Charge les stratégies depuis quantum.team_strategies"""
        async with self.pool.acquire() as conn:
            print(f"\n{Colors.CYAN}📊 Chargement quantum.team_strategies...{Colors.END}")
            
            rows = await conn.fetch("""
                SELECT team_name, strategy_name, is_best_strategy,
                       bets, wins, losses, 
                       win_rate, profit, roi,
                       unlucky_count, bad_analysis_count, source
                FROM quantum.team_strategies
                ORDER BY team_name, profit DESC
            """)
            
            for row in rows:
                team_name = row['team_name']
                
                if team_name not in self.teams:
                    self.teams[team_name] = TeamAnalysis(team_name=team_name)
                
                team = self.teams[team_name]
                
                strat = StrategyResult(
                    strategy=row['strategy_name'],
                    bets=int(row['bets'] or 0),
                    wins=int(row['wins'] or 0),
                    losses=int(row['losses'] or 0),
                    win_rate=float(row['win_rate'] or 0),
                    pnl=float(row['profit'] or 0),
                    roi=float(row['roi'] or 0),
                    unlucky=int(row['unlucky_count'] or 0),
                    bad_analysis=int(row['bad_analysis_count'] or 0)
                )
                team.all_strategies.append(strat)
                
                if row['is_best_strategy']:
                    team.best_strategy = row['strategy_name']
                    team.total_bets = strat.bets
                    team.total_wins = strat.wins
                    team.total_losses = strat.losses
                    team.global_wr = strat.win_rate
                    team.global_pnl = strat.pnl
                    team.global_roi = strat.roi
                    
                    if strat.losses > 0:
                        team.unlucky_pct = (strat.unlucky / strat.losses * 100)
                        team.bad_analysis_pct = (strat.bad_analysis / strat.losses * 100)
            
            print(f"   → {len(self.teams)} équipes chargées")
    
    async def load_team_profiles(self):
        """Charge les profils ADN depuis quantum.team_profiles"""
        async with self.pool.acquire() as conn:
            print(f"{Colors.CYAN}📊 Chargement quantum.team_profiles (ADN)...{Colors.END}")
            
            rows = await conn.fetch("""
                SELECT team_name, quantum_dna
                FROM quantum.team_profiles
                WHERE quantum_dna IS NOT NULL
            """)
            
            for row in rows:
                team_name = row['team_name']
                
                if team_name not in self.teams:
                    self.teams[team_name] = TeamAnalysis(team_name=team_name)
                
                team = self.teams[team_name]
                adn = row['quantum_dna']
                
                if isinstance(adn, str):
                    try:
                        adn = json.loads(adn)
                    except:
                        continue
                
                # Extract ADN metrics
                psyche = adn.get('psyche_dna', {}) or {}
                temporal = adn.get('temporal_dna', {}) or {}
                luck_dna = adn.get('luck_dna', {}) or {}
                context = adn.get('context_dna', {}) or {}
                tactical = adn.get('tactical_dna', {}) or {}
                
                team.killer_instinct = float(psyche.get('killer_instinct', 0) or 0)
                team.panic_factor = float(psyche.get('panic_factor', 0) or 0)
                team.diesel_factor = float(temporal.get('diesel_factor', 0) or 0)
                team.luck = float(luck_dna.get('total_luck', 0) or 0)
                team.home_strength = int(context.get('home_strength', 0) or 0)
                team.away_strength = int(context.get('away_strength', 0) or 0)
                team.btts_tendency = int(context.get('btts_tendency', 0) or 0)
                team.set_piece_threat = float(tactical.get('set_piece_threat', 0) or 0)
                team.style = context.get('style', '') or ''
                team.league = adn.get('league', '') or ''
            
            print(f"   → {len([t for t in self.teams.values() if t.killer_instinct > 0])} profils ADN chargés")
    
    async def load_market_data(self):
        """Charge les données de marché depuis tracking_clv_picks"""
        async with self.pool.acquire() as conn:
            print(f"{Colors.CYAN}📊 Chargement tracking_clv_picks (marchés)...{Colors.END}")
            
            # Pour chaque équipe, charger ses marchés
            rows = await conn.fetch("""
                SELECT 
                    COALESCE(m1.quantum_name, home_team) as team,
                    market_type,
                    COUNT(*) as picks,
                    SUM(CASE WHEN is_winner THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN NOT is_winner THEN 1 ELSE 0 END) as losses,
                    ROUND(SUM(profit_loss)::numeric, 2) as pnl,
                    ROUND(AVG(odds_taken)::numeric, 2) as avg_odds
                FROM tracking_clv_picks t
                LEFT JOIN quantum.team_name_mapping m1 
                    ON t.home_team = m1.historical_name
                WHERE is_resolved = true
                GROUP BY COALESCE(m1.quantum_name, home_team), market_type
                
                UNION ALL
                
                SELECT 
                    COALESCE(m2.quantum_name, away_team) as team,
                    market_type,
                    COUNT(*) as picks,
                    SUM(CASE WHEN is_winner THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN NOT is_winner THEN 1 ELSE 0 END) as losses,
                    ROUND(SUM(profit_loss)::numeric, 2) as pnl,
                    ROUND(AVG(odds_taken)::numeric, 2) as avg_odds
                FROM tracking_clv_picks t
                LEFT JOIN quantum.team_name_mapping m2 
                    ON t.away_team = m2.historical_name
                WHERE is_resolved = true
                GROUP BY COALESCE(m2.quantum_name, away_team), market_type
            """)
            
            # Agréger par équipe
            market_data = defaultdict(lambda: defaultdict(lambda: {'picks': 0, 'wins': 0, 'losses': 0, 'pnl': 0, 'odds': []}))
            
            for row in rows:
                team = row['team']
                market = row['market_type']
                
                if team in self.teams:
                    market_data[team][market]['picks'] += int(row['picks'] or 0)
                    market_data[team][market]['wins'] += int(row['wins'] or 0)
                    market_data[team][market]['losses'] += int(row['losses'] or 0)
                    market_data[team][market]['pnl'] += float(row['pnl'] or 0)
                    if row['avg_odds']:
                        market_data[team][market]['odds'].append(float(row['avg_odds']))
            
            # Assigner aux équipes
            teams_with_markets = 0
            for team_name, markets in market_data.items():
                if team_name in self.teams:
                    team = self.teams[team_name]
                    for market, data in markets.items():
                        mr = MarketResult(
                            market=market,
                            picks=data['picks'],
                            wins=data['wins'],
                            losses=data['losses'],
                            pnl=data['pnl'],
                            win_rate=(data['wins'] / data['picks'] * 100) if data['picks'] > 0 else 0,
                            avg_odds=sum(data['odds']) / len(data['odds']) if data['odds'] else 0
                        )
                        team.markets[market] = mr
                    
                    if team.markets:
                        teams_with_markets += 1
                        best = max(team.markets.values(), key=lambda x: x.pnl)
                        worst = min(team.markets.values(), key=lambda x: x.pnl)
                        team.best_market = best.market
                        team.worst_market = worst.market
            
            print(f"   → {teams_with_markets} équipes avec données de marché")
    
    def analyze_team(self, team: TeamAnalysis):
        """Analyse approfondie d'une équipe et génère recommandations"""
        
        # Déterminer le tier
        if team.global_wr >= 80 and team.global_pnl >= 15:
            team.tier = "💎 ELITE"
        elif team.global_wr >= 70 and team.global_pnl >= 8:
            team.tier = "🏆 GOLD"
        elif team.global_wr >= 65 and team.global_pnl >= 3:
            team.tier = "✅ SILVER"
        elif team.global_pnl > 0:
            team.tier = "⚪ BRONZE"
        else:
            team.tier = "⚠️ WATCH"
        
        # Identifier les forces basées sur ADN
        if team.killer_instinct >= 2.0:
            team.strengths.append(f"🦈 PREDATOR: Killer Instinct={team.killer_instinct:.2f}")
        if team.panic_factor < 0.5:
            team.strengths.append(f"🧊 SANG-FROID: Panic={team.panic_factor:.2f}")
        if team.diesel_factor >= 0.55:
            team.strengths.append(f"🚂 DIESEL: Diesel Factor={team.diesel_factor:.2f}")
        if team.luck >= 5:
            team.strengths.append(f"🍀 CHANCEUX: Luck={team.luck:+.1f}")
        if team.home_strength >= 70:
            team.strengths.append(f"🏠 FORTERESSE: Home={team.home_strength}")
        if team.away_strength >= 50:
            team.strengths.append(f"🚗 ROAD WARRIOR: Away={team.away_strength}")
        if team.btts_tendency >= 70:
            team.strengths.append(f"⚽ BTTS MACHINE: BTTS={team.btts_tendency}%")
        if team.set_piece_threat >= 25:
            team.strengths.append(f"🎯 SET PIECE: {team.set_piece_threat:.1f}%")
        
        # Identifier les faiblesses
        if team.panic_factor >= 1.5:
            team.weaknesses.append(f"😰 FRAGILE: Panic={team.panic_factor:.2f}")
        if team.luck <= -5:
            team.weaknesses.append(f"😢 MALCHANCEUX: Luck={team.luck:.1f}")
        if team.home_strength > 0 and team.away_strength > 0:
            if team.home_strength - team.away_strength >= 40:
                team.weaknesses.append(f"🏚️ HOME DEPENDENT: Home={team.home_strength} vs Away={team.away_strength}")
        if team.bad_analysis_pct >= 20:
            team.weaknesses.append(f"🔴 ERREURS: Bad Analysis={team.bad_analysis_pct:.0f}%")
        
        # Identifier les marchés forces/faiblesses
        if team.best_market and team.best_market in team.markets:
            m = team.markets[team.best_market]
            if m.pnl > 2:
                team.strengths.append(f"📈 BEST MARKET: {m.market} +{m.pnl:.1f}u ({m.win_rate:.0f}% WR)")
        
        if team.worst_market and team.worst_market in team.markets:
            m = team.markets[team.worst_market]
            if m.pnl < -2:
                team.weaknesses.append(f"📉 WORST MARKET: {m.market} {m.pnl:.1f}u ({m.win_rate:.0f}% WR)")
        
        # Générer la stratégie personnalisée
        self._generate_personalized_strategy(team)
        
        # Diagnostic
        if team.unlucky_pct >= 80:
            team.diagnostic = "🍀 Pertes = MALCHANCE - Continuer avec patience"
        elif team.bad_analysis_pct >= 30:
            team.diagnostic = "🔧 Pertes = ERREURS - Revoir le modèle"
        elif team.global_pnl > 0:
            team.diagnostic = "✅ PROFITABLE - Stratégie validée"
        else:
            team.diagnostic = "⚠️ À SURVEILLER - Optimisation nécessaire"
    
    def _generate_personalized_strategy(self, team: TeamAnalysis):
        """Génère une stratégie personnalisée basée sur ADN + marchés"""
        
        # Collecter les signaux
        signals = []
        
        # Signal ADN offensif/défensif
        if 'offensive' in team.style.lower():
            signals.append('OVER')
        elif 'defensive' in team.style.lower():
            signals.append('UNDER')
        
        # Signal Killer + Luck = Over performer
        if team.killer_instinct >= 2.0 and team.luck >= 5:
            signals.append('OVER_BTTS')
        
        # Signal Diesel = 2H specialist
        if team.diesel_factor >= 0.55:
            signals.append('SECOND_HALF')
        
        # Signal Home/Away dominant
        if team.home_strength >= 80 and team.away_strength < 40:
            signals.append('HOME_ONLY')
        elif team.away_strength >= 50 and team.away_strength > team.home_strength:
            signals.append('AWAY_SPECIALIST')
        
        # Signal BTTS tendency
        if team.btts_tendency >= 70:
            signals.append('BTTS_YES')
        elif team.btts_tendency <= 40:
            signals.append('BTTS_NO')
        
        # Signal Set Piece
        if team.set_piece_threat >= 25:
            signals.append('SET_PIECE')
        
        # Vérifier avec les marchés réels
        market_signals = []
        over_markets = ['over_25', 'over_35', 'over25', 'over35', 'over_15']
        under_markets = ['under_25', 'under_35', 'under25', 'under35']
        btts_yes_markets = ['btts_yes']
        btts_no_markets = ['btts_no']
        
        over_pnl = sum(m.pnl for k, m in team.markets.items() if k in over_markets)
        under_pnl = sum(m.pnl for k, m in team.markets.items() if k in under_markets)
        btts_yes_pnl = sum(m.pnl for k, m in team.markets.items() if k in btts_yes_markets)
        btts_no_pnl = sum(m.pnl for k, m in team.markets.items() if k in btts_no_markets)
        home_pnl = team.markets.get('home', MarketResult('')).pnl
        away_pnl = team.markets.get('away', MarketResult('')).pnl
        
        if over_pnl > 2:
            market_signals.append('OVER')
        if under_pnl > 2:
            market_signals.append('UNDER')
        if btts_yes_pnl > 2:
            market_signals.append('BTTS_YES')
        if btts_no_pnl > 2:
            market_signals.append('BTTS_NO')
        if home_pnl > 2:
            market_signals.append('HOME')
        if away_pnl > 2:
            market_signals.append('AWAY')
        
        # Combiner ADN + Marchés pour la stratégie
        combined = list(set(signals) & set(market_signals)) if market_signals else signals
        
        # Générer la recommandation
        if not combined and not market_signals:
            # Pas assez de données de marché, utiliser la meilleure stratégie existante
            if team.all_strategies:
                best = max(team.all_strategies, key=lambda x: x.pnl)
                if best.pnl > 0:
                    team.recommended_strategy = best.strategy
                    team.recommendation_reason = f"Meilleure stratégie historique: +{best.pnl:.1f}u"
                else:
                    team.recommended_strategy = "ADAPTIVE_ENGINE"
                    team.recommendation_reason = "Aucune stratégie positive - mode adaptatif"
        else:
            # Créer une stratégie personnalisée
            if 'OVER' in combined and 'BTTS_YES' in combined:
                team.recommended_strategy = "OVER_BTTS_SPECIALIST"
                team.recommendation_reason = f"ADN Offensif + Marchés Over/BTTS rentables"
            elif 'UNDER' in combined and 'BTTS_NO' in combined:
                team.recommended_strategy = "UNDER_BTTS_NO_SPECIALIST"
                team.recommendation_reason = f"ADN Défensif + Marchés Under/BTTS No rentables"
            elif 'OVER' in combined or 'OVER' in market_signals:
                team.recommended_strategy = "CONVERGENCE_OVER_MC"
                team.recommendation_reason = f"Over markets: +{over_pnl:.1f}u"
            elif 'UNDER' in combined or 'UNDER' in market_signals:
                team.recommended_strategy = "CONVERGENCE_UNDER_MC"
                team.recommendation_reason = f"Under markets: +{under_pnl:.1f}u"
            elif 'HOME' in market_signals and team.home_strength >= 70:
                team.recommended_strategy = "HOME_FORTRESS"
                team.recommendation_reason = f"Home strength {team.home_strength} + home market: +{home_pnl:.1f}u"
            elif 'AWAY' in market_signals and team.away_strength >= 40:
                team.recommended_strategy = "AWAY_WARRIOR"
                team.recommendation_reason = f"Away strength {team.away_strength} + away market: +{away_pnl:.1f}u"
            elif 'BTTS_YES' in market_signals:
                team.recommended_strategy = "BTTS_SPECIALIST"
                team.recommendation_reason = f"BTTS Yes market: +{btts_yes_pnl:.1f}u"
            elif 'BTTS_NO' in market_signals:
                team.recommended_strategy = "BTTS_NO_SPECIALIST"
                team.recommendation_reason = f"BTTS No market: +{btts_no_pnl:.1f}u"
            else:
                team.recommended_strategy = "QUANT_BEST_MARKET"
                team.recommendation_reason = "Stratégie quantitative par défaut"
    
    async def run_analysis(self):
        """Exécute l'analyse complète"""
        await self.load_name_mapping()
        await self.load_team_strategies()
        await self.load_team_profiles()
        await self.load_market_data()
        
        print(f"\n{Colors.CYAN}🔬 Analyse de {len(self.teams)} équipes...{Colors.END}")
        
        for team in self.teams.values():
            self.analyze_team(team)
        
        print(f"   → {len(self.teams)} équipes analysées")
    
    def print_team_fiche(self, team_name: str):
        """Affiche la fiche complète d'une équipe"""
        if team_name not in self.teams:
            print(f"{Colors.RED}❌ Équipe '{team_name}' non trouvée{Colors.END}")
            return
        
        t = self.teams[team_name]
        
        print(f"\n{'═'*120}")
        print(f"║{Colors.BOLD}{Colors.GOLD}  🧬 FICHE ADN: {t.team_name.upper():<80}{Colors.END}║")
        print(f"{'═'*120}")
        
        # Header avec tier et diagnostic
        tier_color = Colors.GOLD if 'ELITE' in t.tier else Colors.GREEN if 'GOLD' in t.tier else Colors.YELLOW
        print(f"║ {tier_color}{t.tier}{Colors.END} │ Ligue: {t.league[:20]:<20} │ Style: {t.style[:20]:<20} │ {t.diagnostic:<30} ║")
        print(f"{'─'*120}")
        
        # Performance globale
        wr_color = Colors.GREEN if t.global_wr >= 65 else Colors.YELLOW if t.global_wr >= 55 else Colors.RED
        pnl_color = Colors.GREEN if t.global_pnl > 0 else Colors.RED
        
        print(f"║ 📊 PERFORMANCE GLOBALE{' '*95}║")
        print(f"║    Paris: {t.total_bets:<5} │ Wins: {t.total_wins:<4} │ Losses: {t.total_losses:<4} │ "
              f"WR: {wr_color}{t.global_wr:>5.1f}%{Colors.END} │ ROI: {t.global_roi:>+6.1f}% │ "
              f"P&L: {pnl_color}{t.global_pnl:>+7.1f}u{Colors.END}{' '*15}║")
        print(f"║    Malchance: {t.unlucky_pct:>5.1f}% │ Erreur Analyse: {t.bad_analysis_pct:>5.1f}%{' '*65}║")
        print(f"{'─'*120}")
        
        # ADN Metrics
        print(f"║ 🧬 MÉTRIQUES ADN{' '*101}║")
        print(f"║    Killer: {t.killer_instinct:>5.2f} │ Panic: {t.panic_factor:>5.2f} │ Diesel: {t.diesel_factor:>5.2f} │ "
              f"Luck: {t.luck:>+5.1f} │ Home: {t.home_strength:>3} │ Away: {t.away_strength:>3} │ "
              f"BTTS: {t.btts_tendency:>3}%{' '*10}║")
        print(f"{'─'*120}")
        
        # Top 3 Stratégies
        print(f"║ 🏆 STRATÉGIES TESTÉES (Top 3){' '*88}║")
        sorted_strats = sorted(t.all_strategies, key=lambda x: x.pnl, reverse=True)[:3]
        
        for i, strat in enumerate(sorted_strats, 1):
            emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
            color = Colors.GREEN if strat.pnl > 0 else Colors.RED
            is_best = " ⭐" if strat.strategy == t.best_strategy else ""
            print(f"║    {emoji} {strat.strategy:<22} │ Bets: {strat.bets:>4} │ WR: {strat.win_rate:>5.1f}% │ "
                  f"P&L: {color}{strat.pnl:>+7.1f}u{Colors.END} │ Unlucky: {strat.unlucky:>2} │ Bad: {strat.bad_analysis:>2}{is_best:<10}║")
        
        print(f"{'─'*120}")
        
        # Marchés détaillés
        if t.markets:
            print(f"║ �� MARCHÉS DÉTAILLÉS{' '*97}║")
            sorted_markets = sorted(t.markets.values(), key=lambda x: x.pnl, reverse=True)
            
            for m in sorted_markets[:8]:
                color = Colors.GREEN if m.pnl > 0 else Colors.RED if m.pnl < 0 else Colors.YELLOW
                verdict = "✅" if m.pnl > 1 else "⚠️" if m.pnl >= -1 else "❌"
                print(f"║    {verdict} {m.market:<12} │ Picks: {m.picks:>3} │ Wins: {m.wins:>3} │ "
                      f"WR: {m.win_rate:>5.1f}% │ P&L: {color}{m.pnl:>+6.1f}u{Colors.END} │ "
                      f"Odds: {m.avg_odds:>5.2f}{' '*25}║")
            
            print(f"{'─'*120}")
        
        # Forces
        print(f"║ 💪 FORCES{' '*108}║")
        for strength in t.strengths[:5]:
            print(f"║    {strength:<113}║")
        if not t.strengths:
            print(f"║    (Aucune force identifiée){' '*88}║")
        
        # Faiblesses
        print(f"║ ⚠️ FAIBLESSES{' '*104}║")
        for weakness in t.weaknesses[:5]:
            print(f"║    {weakness:<113}║")
        if not t.weaknesses:
            print(f"║    (Aucune faiblesse identifiée){' '*84}║")
        
        print(f"{'─'*120}")
        
        # Recommandation personnalisée
        print(f"║ �� STRATÉGIE PERSONNALISÉE RECOMMANDÉE{' '*79}║")
        rec_color = Colors.GREEN if t.recommended_strategy != t.best_strategy else Colors.CYAN
        change = " 🔄 CHANGEMENT" if t.recommended_strategy != t.best_strategy else " ✓ CONFIRMÉE"
        print(f"║    {rec_color}{t.recommended_strategy:<30}{Colors.END}{change:<15}║")
        print(f"║    Raison: {t.recommendation_reason:<106}║")
        
        if t.recommended_strategy != t.best_strategy and t.best_strategy:
            print(f"║    Actuelle: {t.best_strategy:<30} → Recommandée: {t.recommended_strategy:<30}{' '*25}║")
        
        print(f"{'═'*120}\n")
    
    def print_summary(self):
        """Affiche le résumé global"""
        print(f"\n{'═'*140}")
        print(f"║{Colors.BOLD}{Colors.GOLD}                                    🧬 QUANTUM V6 TEAM-CENTRIC - RÉSUMÉ ({len(self.teams)} ÉQUIPES)                                           {Colors.END}║")
        print(f"{'═'*140}")
        
        # Stats globales
        teams_with_bets = [t for t in self.teams.values() if t.total_bets > 0]
        total_bets = sum(t.total_bets for t in teams_with_bets)
        total_wins = sum(t.total_wins for t in teams_with_bets)
        total_pnl = sum(t.global_pnl for t in teams_with_bets)
        global_wr = (total_wins / total_bets * 100) if total_bets > 0 else 0
        
        profitable = sum(1 for t in teams_with_bets if t.global_pnl > 0)
        losing = len(teams_with_bets) - profitable
        
        print(f"║ 📊 {total_bets} paris │ {total_wins}W │ {global_wr:.1f}% WR │ {total_pnl:+.1f}u P&L │ {profitable} profitables / {losing} en surveillance{' '*35}║")
        print(f"{'─'*140}")
        
        # Par tier
        tiers = defaultdict(list)
        for t in teams_with_bets:
            tiers[t.tier].append(t)
        
        print(f"║ 🏆 DISTRIBUTION PAR TIER{' '*113}║")
        for tier in ['💎 ELITE', '🏆 GOLD', '✅ SILVER', '⚪ BRONZE', '⚠️ WATCH']:
            if tier in tiers:
                teams = tiers[tier]
                tier_pnl = sum(t.global_pnl for t in teams)
                tier_wr = sum(t.global_wr for t in teams) / len(teams)
                print(f"║    {tier:<12} │ {len(teams):>3} équipes │ {tier_wr:>5.1f}% WR │ {tier_pnl:>+8.1f}u P&L{' '*75}║")
        
        print(f"{'─'*140}")
        
        # Top 10 équipes
        print(f"║ 🥇 TOP 10 ÉQUIPES{' '*120}║")
        sorted_teams = sorted(teams_with_bets, key=lambda x: x.global_pnl, reverse=True)[:10]
        
        print(f"║ {'#':<3} {'Équipe':<22} {'Tier':<12} {'Bets':>5} {'WR%':>6} {'P&L':>8} {'Best Strategy':<25} {'Recommended':<25} ║")
        print(f"║ {'─'*135} ║")
        
        for i, t in enumerate(sorted_teams, 1):
            color = Colors.GREEN if t.global_pnl > 0 else Colors.RED
            change = "🔄" if t.recommended_strategy != t.best_strategy else "✓"
            print(f"║ {i:<3} {t.team_name[:21]:<22} {t.tier:<12} {t.total_bets:>5} {t.global_wr:>5.1f}% "
                  f"{color}{t.global_pnl:>+7.1f}u{Colors.END} {t.best_strategy[:24]:<25} {change}{t.recommended_strategy[:23]:<24} ║")
        
        print(f"{'─'*140}")
        
        # Équipes GENERIC à personnaliser
        generic_teams = [t for t in teams_with_bets if t.best_strategy == 'GENERIC']
        if generic_teams:
            print(f"║ 🔧 ÉQUIPES GENERIC → STRATÉGIE PERSONNALISÉE{' '*92}║")
            
            for t in sorted(generic_teams, key=lambda x: x.global_pnl):
                color = Colors.GREEN if t.global_pnl > 0 else Colors.RED
                print(f"║    {t.team_name[:20]:<22} │ P&L: {color}{t.global_pnl:>+6.1f}u{Colors.END} │ "
                      f"GENERIC → {Colors.CYAN}{t.recommended_strategy:<25}{Colors.END} │ {t.recommendation_reason[:40]:<42}║")
        
        print(f"{'═'*140}\n")
    
    def save_report(self):
        """Sauvegarde le rapport en JSON"""
        teams_with_bets = [t for t in self.teams.values() if t.total_bets > 0]
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'version': 'V6.0 Team-Centric ADN Analysis',
            'summary': {
                'total_teams': len(teams_with_bets),
                'total_bets': sum(t.total_bets for t in teams_with_bets),
                'total_pnl': round(sum(t.global_pnl for t in teams_with_bets), 2),
                'profitable_teams': sum(1 for t in teams_with_bets if t.global_pnl > 0),
                'generic_teams': sum(1 for t in teams_with_bets if t.best_strategy == 'GENERIC')
            },
            'teams': {
                t.team_name: {
                    'league': t.league,
                    'tier': t.tier,
                    'performance': {
                        'bets': t.total_bets,
                        'wins': t.total_wins,
                        'losses': t.total_losses,
                        'win_rate': round(t.global_wr, 1),
                        'pnl': round(t.global_pnl, 1),
                        'roi': round(t.global_roi, 1),
                        'unlucky_pct': round(t.unlucky_pct, 1),
                        'bad_analysis_pct': round(t.bad_analysis_pct, 1)
                    },
                    'adn': {
                        'killer_instinct': round(t.killer_instinct, 2),
                        'panic_factor': round(t.panic_factor, 2),
                        'diesel_factor': round(t.diesel_factor, 2),
                        'luck': round(t.luck, 1),
                        'home_strength': t.home_strength,
                        'away_strength': t.away_strength,
                        'btts_tendency': t.btts_tendency,
                        'style': t.style
                    },
                    'strategies': {
                        'current_best': t.best_strategy,
                        'recommended': t.recommended_strategy,
                        'recommendation_reason': t.recommendation_reason,
                        'all_tested': [
                            {
                                'name': s.strategy,
                                'bets': s.bets,
                                'wins': s.wins,
                                'win_rate': round(s.win_rate, 1),
                                'pnl': round(s.pnl, 1),
                                'unlucky': s.unlucky,
                                'bad_analysis': s.bad_analysis
                            }
                            for s in sorted(t.all_strategies, key=lambda x: x.pnl, reverse=True)
                        ]
                    },
                    'markets': {
                        m.market: {
                            'picks': m.picks,
                            'wins': m.wins,
                            'win_rate': round(m.win_rate, 1),
                            'pnl': round(m.pnl, 1)
                        }
                        for m in t.markets.values()
                    },
                    'strengths': t.strengths,
                    'weaknesses': t.weaknesses,
                    'diagnostic': t.diagnostic
                }
                for t in sorted(teams_with_bets, key=lambda x: x.global_pnl, reverse=True)
            }
        }
        
        filename = f"quantum_v6_team_centric_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"{Colors.GREEN}✅ Rapport sauvegardé: {filename}{Colors.END}")
        
        with open('quantum_v6_team_centric_latest.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"{Colors.GREEN}✅ Rapport sauvegardé: quantum_v6_team_centric_latest.json{Colors.END}")
    
    async def run(self, team_to_show: str = None, show_generic: bool = False):
        """Exécute le rapport complet"""
        await self.connect()
        await self.run_analysis()
        
        # Afficher le résumé
        self.print_summary()
        
        # Si une équipe spécifique est demandée
        if team_to_show:
            self.print_team_fiche(team_to_show)
        elif show_generic:
            # Afficher les fiches des équipes GENERIC
            generic_teams = [t for t in self.teams.values() 
                           if t.best_strategy == 'GENERIC' and t.total_bets > 0]
            for t in sorted(generic_teams, key=lambda x: x.global_pnl):
                self.print_team_fiche(t.team_name)
        else:
            # Afficher les 3 meilleures et 3 pires équipes
            teams_with_bets = [t for t in self.teams.values() if t.total_bets > 0]
            sorted_teams = sorted(teams_with_bets, key=lambda x: x.global_pnl, reverse=True)
            
            print(f"\n{Colors.CYAN}📋 TOP 3 ÉQUIPES:{Colors.END}")
            for t in sorted_teams[:3]:
                self.print_team_fiche(t.team_name)
            
            print(f"\n{Colors.CYAN}📋 3 ÉQUIPES À AMÉLIORER:{Colors.END}")
            for t in sorted_teams[-3:]:
                self.print_team_fiche(t.team_name)
        
        # Sauvegarder
        self.save_report()
        
        await self.close()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(description='Quantum V6 Team-Centric ADN Analysis')
    parser.add_argument('--team', type=str, help='Analyser une équipe spécifique')
    parser.add_argument('--generic', action='store_true', help='Afficher les équipes GENERIC')
    parser.add_argument('--all', action='store_true', help='Afficher toutes les équipes')
    args = parser.parse_args()
    
    analyzer = QuantumV6TeamCentric()
    await analyzer.run(team_to_show=args.team, show_generic=args.generic)


if __name__ == "__main__":
    asyncio.run(main())
