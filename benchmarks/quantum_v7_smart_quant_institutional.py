#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                                                                       ║
║     🧬 QUANTUM V7.0 SMART QUANT INSTITUTIONAL - HEDGE FUND GRADE                                                                      ║
║                                                                                                                                       ║
║  ══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════   ║
║                                                                                                                                       ║
║  🎯 PHILOSOPHIE V7:                                                                                                                   ║
║     • 1 équipe = 1 ADN UNIQUE = 1 stratégie SUR MESURE                                                                                ║
║     • Pas de stratégies prédéfinies - PERSONNALISATION TOTALE                                                                         ║
║     • 15 vecteurs ADN analysés en profondeur                                                                                          ║
║     • 22 marchés testés par équipe                                                                                                    ║
║     • Classification des pertes : MALCHANCE vs ERREUR                                                                                 ║
║     • Identification des PÉPITES (marchés négatifs globalement mais positifs pour l'équipe)                                           ║
║                                                                                                                                       ║
║  📊 SOURCES DE DONNÉES:                                                                                                               ║
║     • quantum.team_profiles (99 équipes, 15 vecteurs ADN)                                                                             ║
║     • quantum.team_strategies (historique stratégies)                                                                                 ║
║     • tracking_clv_picks (22 marchés, détails paris)                                                                                  ║
║     • quantum.market_performance (performance par marché)                                                                             ║
║     • audit_complet_99_equipes.json (référence +574.5u)                                                                               ║
║                                                                                                                                       ║
║  🔬 PRINCIPE MYA: "Un ADN parfait ne suffit pas - il faut la BONNE STRATÉGIE PERSONNALISÉE"                                           ║
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
from pathlib import Path

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

# 22 marchés disponibles
ALL_MARKETS = [
    'home', 'away', 'draw',
    'dc_12', 'dc_1x', 'dc_x2',
    'over_15', 'over_25', 'over_35',
    'under_15', 'under_25', 'under_35',
    'btts_yes', 'btts_no',
    'dnb_home', 'dnb_away'
]

# Normalisation des marchés
MARKET_NORMALIZE = {
    'over15': 'over_15', 'over25': 'over_25', 'over35': 'over_35',
    'under15': 'under_15', 'under25': 'under_25', 'under35': 'under_35'
}

# 15 vecteurs ADN
ADN_VECTORS = [
    'psyche_dna', 'temporal_dna', 'luck_dna', 'context_dna', 'tactical_dna',
    'physical_dna', 'roster_dna', 'chameleon_dna', 'market_dna', 'sentiment_dna',
    'nemesis_dna', 'friction_signatures', 'meta_dna', 'current_season', 'league'
]

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
    MAGENTA = '\033[35m'


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MarketPerformance:
    """Performance d'un marché pour une équipe"""
    market: str
    picks: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    pnl: float = 0.0
    avg_odds: float = 0.0
    # Classification des pertes
    loss_malchance: int = 0      # Manque 1 but, variance
    loss_erreur_legere: int = 0  # Manque 2 buts
    loss_erreur_modele: int = 0  # Prédiction incorrecte
    loss_erreur_grave: int = 0   # Erreur fondamentale
    # Détails
    is_pepite: bool = False      # Marché négatif global mais positif pour cette équipe
    global_pnl: float = 0.0      # P&L global de ce marché (toutes équipes)


@dataclass
class ADNProfile:
    """Profil ADN complet d'une équipe"""
    # Psyche DNA
    killer_instinct: float = 0.0
    panic_factor: float = 0.0
    mental_strength: float = 0.0
    
    # Temporal DNA
    diesel_factor: float = 0.0
    first_half_dominance: float = 0.0
    second_half_dominance: float = 0.0
    
    # Luck DNA
    total_luck: float = 0.0
    xg_overperformance: float = 0.0
    
    # Context DNA
    home_strength: int = 0
    away_strength: int = 0
    btts_tendency: int = 0
    style: str = ""
    
    # Tactical DNA
    set_piece_threat: float = 0.0
    counter_attack: float = 0.0
    possession_style: float = 0.0
    verticality: float = 0.0
    
    # Physical DNA
    intensity: float = 0.0
    stamina: float = 0.0
    
    # Market DNA
    best_market: str = ""
    worst_market: str = ""
    
    # Meta
    league: str = ""
    tier: str = ""


@dataclass
class LossClassification:
    """Classification détaillée des pertes"""
    total_losses: int = 0
    malchance: int = 0           # Variance normale (manque 1 but)
    erreur_legere: int = 0       # Proche (manque 2 buts)
    erreur_modele: int = 0       # Prédiction incorrecte
    erreur_grave: int = 0        # Erreur fondamentale
    
    @property
    def malchance_pct(self) -> float:
        return (self.malchance / self.total_losses * 100) if self.total_losses > 0 else 0
    
    @property
    def erreur_pct(self) -> float:
        return ((self.erreur_legere + self.erreur_modele + self.erreur_grave) / self.total_losses * 100) if self.total_losses > 0 else 0


@dataclass
class PersonalizedStrategy:
    """Stratégie personnalisée générée pour une équipe"""
    name: str                    # Nom unique de la stratégie
    markets_focus: List[str]     # Marchés à privilégier
    markets_avoid: List[str]     # Marchés à éviter
    conditions: Dict[str, Any]   # Conditions d'application
    reasoning: str               # Explication de la stratégie
    expected_wr: float = 0.0     # WR attendu basé sur historique
    expected_roi: float = 0.0    # ROI attendu


@dataclass 
class TeamV7Analysis:
    """Analyse V7 complète d'une équipe"""
    team_name: str
    
    # Performance globale
    total_bets: int = 0
    total_wins: int = 0
    total_losses: int = 0
    global_wr: float = 0.0
    global_pnl: float = 0.0
    global_roi: float = 0.0
    
    # ADN complet
    adn: ADNProfile = field(default_factory=ADNProfile)
    adn_raw: Dict = field(default_factory=dict)
    
    # Performance par marché (22 marchés)
    markets: Dict[str, MarketPerformance] = field(default_factory=dict)
    
    # Top 3 marchés
    top_markets: List[str] = field(default_factory=list)
    worst_markets: List[str] = field(default_factory=list)
    pepites: List[str] = field(default_factory=list)  # Marchés pépites
    
    # Classification des pertes
    loss_classification: LossClassification = field(default_factory=LossClassification)
    
    # Stratégie personnalisée générée
    custom_strategy: PersonalizedStrategy = None
    
    # Forces et faiblesses
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    
    # Diagnostic
    tier: str = ""
    diagnostic: str = ""
    recommendation: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# QUANTUM V7 SMART QUANT INSTITUTIONAL
# ═══════════════════════════════════════════════════════════════════════════════

class QuantumV7SmartQuant:
    """V7 Smart Quant Institutional - Stratégies personnalisées par équipe"""
    
    def __init__(self):
        self.pool = None
        self.teams: Dict[str, TeamV7Analysis] = {}
        self.global_market_pnl: Dict[str, float] = {}  # P&L global par marché
        self.audit_data: Dict[str, Any] = {}
        
    async def connect(self):
        """Connexion à la base de données"""
        self.pool = await asyncpg.create_pool(**DB_CONFIG, min_size=2, max_size=10)
        print(f"{Colors.GREEN}✅ Connexion PostgreSQL établie{Colors.END}")
        
    async def close(self):
        """Fermeture de la connexion"""
        if self.pool:
            await self.pool.close()
            print(f"{Colors.CYAN}🔌 Connexion fermée{Colors.END}")
    
    def load_audit_data(self):
        """Charge les données de l'audit 99 équipes"""
        audit_path = Path("/home/Mon_ps/benchmarks/audit_complet_99_equipes.json")
        if audit_path.exists():
            with open(audit_path, 'r') as f:
                data = json.load(f)
                teams_list = data.get('teams', [])
                for team in teams_list:
                    self.audit_data[team['name']] = team
            print(f"{Colors.CYAN}📊 Audit chargé: {len(self.audit_data)} équipes{Colors.END}")
    
    async def load_global_market_performance(self):
        """Charge la performance globale par marché (toutes équipes)"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    COALESCE(mn.normalized_name, market_type) as market,
                    COUNT(*) as picks,
                    ROUND(SUM(profit_loss)::numeric, 2) as pnl
                FROM tracking_clv_picks t
                LEFT JOIN quantum.market_normalization mn ON t.market_type = mn.raw_name
                WHERE is_resolved = true
                GROUP BY COALESCE(mn.normalized_name, market_type)
            """)
            for row in rows:
                self.global_market_pnl[row['market']] = float(row['pnl'] or 0)
            print(f"{Colors.CYAN}📊 Performance globale marchés: {len(self.global_market_pnl)} marchés{Colors.END}")
    
    async def load_team_profiles(self):
        """Charge les profils ADN complets"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT team_name, quantum_dna
                FROM quantum.team_profiles
                WHERE quantum_dna IS NOT NULL
            """)
            
            for row in rows:
                team_name = row['team_name']
                if team_name not in self.teams:
                    self.teams[team_name] = TeamV7Analysis(team_name=team_name)
                
                team = self.teams[team_name]
                adn_raw = row['quantum_dna']
                
                if isinstance(adn_raw, str):
                    try:
                        adn_raw = json.loads(adn_raw)
                    except:
                        continue
                
                team.adn_raw = adn_raw
                team.adn = self._extract_adn_profile(adn_raw)
            
            print(f"{Colors.CYAN}📊 Profils ADN chargés: {len(self.teams)} équipes{Colors.END}")
    
    def _extract_adn_profile(self, adn_raw: Dict) -> ADNProfile:
        """Extrait un profil ADN structuré depuis le JSON brut"""
        profile = ADNProfile()
        
        # Psyche DNA
        psyche = adn_raw.get('psyche_dna', {}) or {}
        profile.killer_instinct = float(psyche.get('killer_instinct', 0) or 0)
        profile.panic_factor = float(psyche.get('panic_factor', 0) or 0)
        profile.mental_strength = float(psyche.get('mental_strength', 0) or 0)
        
        # Temporal DNA
        temporal = adn_raw.get('temporal_dna', {}) or {}
        profile.diesel_factor = float(temporal.get('diesel_factor', 0) or 0)
        profile.first_half_dominance = float(temporal.get('first_half_dominance', 0) or 0)
        profile.second_half_dominance = float(temporal.get('second_half_dominance', 0) or 0)
        
        # Luck DNA
        luck = adn_raw.get('luck_dna', {}) or {}
        profile.total_luck = float(luck.get('total_luck', 0) or 0)
        profile.xg_overperformance = float(luck.get('xg_overperformance', 0) or 0)
        
        # Context DNA
        context = adn_raw.get('context_dna', {}) or {}
        profile.home_strength = int(context.get('home_strength', 0) or 0)
        profile.away_strength = int(context.get('away_strength', 0) or 0)
        profile.btts_tendency = int(context.get('btts_tendency', 0) or 0)
        profile.style = context.get('style', '') or ''
        
        # Tactical DNA
        tactical = adn_raw.get('tactical_dna', {}) or {}
        profile.set_piece_threat = float(tactical.get('set_piece_threat', 0) or 0)
        profile.counter_attack = float(tactical.get('counter_attack', 0) or 0)
        profile.possession_style = float(tactical.get('possession_style', 0) or 0)
        profile.verticality = float(tactical.get('verticality', 0) or 0)
        
        # Physical DNA
        physical = adn_raw.get('physical_dna', {}) or {}
        profile.intensity = float(physical.get('intensity', 0) or 0)
        profile.stamina = float(physical.get('stamina', 0) or 0)
        
        # League
        profile.league = adn_raw.get('league', '') or ''
        
        return profile
    
    async def load_team_strategies(self):
        """Charge les stratégies depuis quantum.team_strategies"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT team_name, strategy_name, is_best_strategy,
                       bets, wins, losses, win_rate, profit, roi,
                       unlucky_count, bad_analysis_count, source
                FROM quantum.team_strategies
                WHERE is_best_strategy = true
            """)
            
            for row in rows:
                team_name = row['team_name']
                if team_name not in self.teams:
                    self.teams[team_name] = TeamV7Analysis(team_name=team_name)
                
                team = self.teams[team_name]
                team.total_bets = int(row['bets'] or 0)
                team.total_wins = int(row['wins'] or 0)
                team.total_losses = int(row['losses'] or 0)
                team.global_wr = float(row['win_rate'] or 0)
                team.global_pnl = float(row['profit'] or 0)
                team.global_roi = float(row['roi'] or 0)
                
                # Classification des pertes depuis la DB
                team.loss_classification.total_losses = team.total_losses
                team.loss_classification.malchance = int(row['unlucky_count'] or 0)
                team.loss_classification.erreur_modele = int(row['bad_analysis_count'] or 0)
            
            print(f"{Colors.CYAN}📊 Stratégies chargées: {len([t for t in self.teams.values() if t.total_bets > 0])} équipes avec paris{Colors.END}")
    
    async def load_market_performance(self):
        """Charge la performance par marché pour chaque équipe"""
        async with self.pool.acquire() as conn:
            # Récupérer les données par équipe et marché
            rows = await conn.fetch("""
                WITH team_markets AS (
                    SELECT 
                        COALESCE(m.quantum_name, t.home_team) as team_name,
                        COALESCE(mn.normalized_name, t.market_type) as market,
                        t.is_winner,
                        t.profit_loss,
                        t.odds_taken,
                        t.score_home,
                        t.score_away
                    FROM tracking_clv_picks t
                    LEFT JOIN quantum.team_name_mapping m ON t.home_team = m.historical_name
                    LEFT JOIN quantum.market_normalization mn ON t.market_type = mn.raw_name
                    WHERE t.is_resolved = true
                    
                    UNION ALL
                    
                    SELECT 
                        COALESCE(m.quantum_name, t.away_team) as team_name,
                        COALESCE(mn.normalized_name, t.market_type) as market,
                        t.is_winner,
                        t.profit_loss,
                        t.odds_taken,
                        t.score_home,
                        t.score_away
                    FROM tracking_clv_picks t
                    LEFT JOIN quantum.team_name_mapping m ON t.away_team = m.historical_name
                    LEFT JOIN quantum.market_normalization mn ON t.market_type = mn.raw_name
                    WHERE t.is_resolved = true
                )
                SELECT 
                    team_name,
                    market,
                    COUNT(*) as picks,
                    SUM(CASE WHEN is_winner THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN NOT is_winner THEN 1 ELSE 0 END) as losses,
                    ROUND(SUM(profit_loss)::numeric, 2) as pnl,
                    ROUND(AVG(odds_taken)::numeric, 2) as avg_odds
                FROM team_markets
                WHERE team_name IS NOT NULL
                GROUP BY team_name, market
            """)
            
            for row in rows:
                team_name = row['team_name']
                market = row['market']
                
                if team_name in self.teams:
                    team = self.teams[team_name]
                    
                    mp = MarketPerformance(
                        market=market,
                        picks=int(row['picks'] or 0),
                        wins=int(row['wins'] or 0),
                        losses=int(row['losses'] or 0),
                        pnl=float(row['pnl'] or 0),
                        avg_odds=float(row['avg_odds'] or 0)
                    )
                    mp.win_rate = (mp.wins / mp.picks * 100) if mp.picks > 0 else 0
                    
                    # Marquer comme pépite si positif pour l'équipe mais négatif globalement
                    global_pnl = self.global_market_pnl.get(market, 0)
                    mp.global_pnl = global_pnl
                    if mp.pnl > 2 and global_pnl < 0:
                        mp.is_pepite = True
                    
                    team.markets[market] = mp
            
            # Identifier top/worst/pepites pour chaque équipe
            for team in self.teams.values():
                if team.markets:
                    sorted_markets = sorted(team.markets.values(), key=lambda x: x.pnl, reverse=True)
                    team.top_markets = [m.market for m in sorted_markets[:3] if m.pnl > 0]
                    team.worst_markets = [m.market for m in sorted_markets[-3:] if m.pnl < 0]
                    team.pepites = [m.market for m in team.markets.values() if m.is_pepite]
            
            teams_with_markets = len([t for t in self.teams.values() if t.markets])
            print(f"{Colors.CYAN}📊 Marchés par équipe: {teams_with_markets} équipes{Colors.END}")
    
    def generate_personalized_strategy(self, team: TeamV7Analysis) -> PersonalizedStrategy:
        """Génère une stratégie PERSONNALISÉE basée sur l'ADN + marchés de l'équipe"""
        
        adn = team.adn
        markets = team.markets
        
        # Collecter les signaux ADN
        adn_signals = []
        
        # Signal Killer Instinct
        if adn.killer_instinct >= 2.0:
            adn_signals.append(('PREDATOR', 'Killer élevé'))
        elif adn.killer_instinct <= 0.5:
            adn_signals.append(('VULNERABLE', 'Killer faible'))
        
        # Signal Panic
        if adn.panic_factor < 0.5:
            adn_signals.append(('SANG_FROID', 'Panic bas'))
        elif adn.panic_factor >= 1.5:
            adn_signals.append(('FRAGILE', 'Panic élevé'))
        
        # Signal Diesel
        if adn.diesel_factor >= 0.55:
            adn_signals.append(('DIESEL', '2H specialist'))
        
        # Signal Luck
        if adn.total_luck >= 5:
            adn_signals.append(('CHANCEUX', f'Luck +{adn.total_luck:.1f}'))
        elif adn.total_luck <= -5:
            adn_signals.append(('MALCHANCEUX', f'Luck {adn.total_luck:.1f}'))
        
        # Signal Home/Away
        if adn.home_strength >= 80:
            adn_signals.append(('FORTERESSE', f'Home {adn.home_strength}'))
        if adn.away_strength >= 50:
            adn_signals.append(('ROAD_WARRIOR', f'Away {adn.away_strength}'))
        if adn.home_strength > 0 and adn.away_strength > 0:
            if adn.home_strength - adn.away_strength >= 40:
                adn_signals.append(('HOME_DEPENDENT', f'H{adn.home_strength}/A{adn.away_strength}'))
        
        # Signal BTTS
        if adn.btts_tendency >= 70:
            adn_signals.append(('BTTS_HIGH', f'BTTS {adn.btts_tendency}%'))
        elif adn.btts_tendency <= 40:
            adn_signals.append(('BTTS_LOW', f'BTTS {adn.btts_tendency}%'))
        
        # Signal Style
        if 'offensive' in adn.style.lower():
            adn_signals.append(('OFFENSIVE', adn.style))
        elif 'defensive' in adn.style.lower():
            adn_signals.append(('DEFENSIVE', adn.style))
        
        # Collecter les signaux MARCHÉ (basés sur données réelles)
        market_signals = []
        markets_focus = []
        markets_avoid = []
        
        for market, mp in markets.items():
            if mp.picks >= 3:  # Minimum 3 paris pour être significatif
                if mp.pnl > 2:
                    market_signals.append((market, 'PROFITABLE', mp.pnl, mp.win_rate))
                    markets_focus.append(market)
                elif mp.pnl < -2:
                    market_signals.append((market, 'PERDANT', mp.pnl, mp.win_rate))
                    markets_avoid.append(market)
        
        # Identifier les patterns marché
        over_pnl = sum(mp.pnl for m, mp in markets.items() if 'over' in m)
        under_pnl = sum(mp.pnl for m, mp in markets.items() if 'under' in m)
        btts_yes_pnl = markets.get('btts_yes', MarketPerformance('')).pnl
        btts_no_pnl = markets.get('btts_no', MarketPerformance('')).pnl
        home_pnl = markets.get('home', MarketPerformance('')).pnl
        away_pnl = markets.get('away', MarketPerformance('')).pnl
        
        # Construire le nom de la stratégie personnalisée
        strategy_components = []
        conditions = {}
        reasoning_parts = []
        
        # Priorité 1: Marchés gagnants (données réelles)
        if over_pnl > 3:
            strategy_components.append('OVER')
            conditions['over_focus'] = True
            reasoning_parts.append(f"Over markets: +{over_pnl:.1f}u")
        
        if under_pnl > 3:
            strategy_components.append('UNDER')
            conditions['under_focus'] = True
            reasoning_parts.append(f"Under markets: +{under_pnl:.1f}u")
        
        if btts_yes_pnl > 2:
            strategy_components.append('BTTS_YES')
            conditions['btts_yes'] = True
            reasoning_parts.append(f"BTTS Yes: +{btts_yes_pnl:.1f}u")
        
        if btts_no_pnl > 2:
            strategy_components.append('BTTS_NO')
            conditions['btts_no'] = True
            reasoning_parts.append(f"BTTS No: +{btts_no_pnl:.1f}u")
        
        if home_pnl > 2 and adn.home_strength >= 70:
            strategy_components.append('HOME')
            conditions['home_only'] = True
            reasoning_parts.append(f"Home: +{home_pnl:.1f}u (strength {adn.home_strength})")
        
        if away_pnl > 2 and adn.away_strength >= 50:
            strategy_components.append('AWAY')
            conditions['away_specialist'] = True
            reasoning_parts.append(f"Away: +{away_pnl:.1f}u (strength {adn.away_strength})")
        
        # Priorité 2: Signaux ADN pour affiner
        for signal, desc in adn_signals:
            if signal == 'PREDATOR' and 'OVER' not in strategy_components:
                strategy_components.append('PREDATOR')
                reasoning_parts.append(f"ADN: {desc}")
            elif signal == 'DIESEL':
                conditions['second_half'] = True
                reasoning_parts.append(f"ADN: {desc}")
            elif signal == 'FORTERESSE' and 'HOME' not in strategy_components:
                strategy_components.append('HOME')
                reasoning_parts.append(f"ADN: {desc}")
        
        # Construire le nom final
        if not strategy_components:
            # Fallback: utiliser les meilleurs marchés disponibles
            if team.top_markets:
                strategy_components = [m.upper().replace('_', '') for m in team.top_markets[:2]]
                reasoning_parts.append(f"Top markets: {', '.join(team.top_markets[:2])}")
            else:
                strategy_components = ['ADAPTIVE']
                reasoning_parts.append("Pas assez de données - mode adaptatif")
        
        strategy_name = f"{team.team_name.upper().replace(' ', '_')}_" + "_".join(strategy_components[:3])
        
        # Calculer WR et ROI attendus
        expected_wr = 0
        expected_roi = 0
        if markets_focus:
            focus_markets = [markets[m] for m in markets_focus if m in markets]
            if focus_markets:
                total_picks = sum(mp.picks for mp in focus_markets)
                total_wins = sum(mp.wins for mp in focus_markets)
                total_pnl = sum(mp.pnl for mp in focus_markets)
                expected_wr = (total_wins / total_picks * 100) if total_picks > 0 else 0
                expected_roi = (total_pnl / total_picks * 100) if total_picks > 0 else 0
        
        return PersonalizedStrategy(
            name=strategy_name,
            markets_focus=markets_focus,
            markets_avoid=markets_avoid,
            conditions=conditions,
            reasoning=" | ".join(reasoning_parts) if reasoning_parts else "Stratégie adaptative",
            expected_wr=expected_wr,
            expected_roi=expected_roi
        )
    
    def analyze_team(self, team: TeamV7Analysis):
        """Analyse approfondie d'une équipe"""
        
        # Générer la stratégie personnalisée
        team.custom_strategy = self.generate_personalized_strategy(team)
        
        # Déterminer le tier
        if team.global_wr >= 80 and team.global_pnl >= 15:
            team.tier = "💎 ELITE"
        elif team.global_wr >= 70 and team.global_pnl >= 8:
            team.tier = "🏆 GOLD"
        elif team.global_wr >= 65 and team.global_pnl >= 3:
            team.tier = "✅ SILVER"
        elif team.global_pnl > 0:
            team.tier = "⚪ BRONZE"
        elif team.total_bets == 0:
            team.tier = "🆕 NEW"
        else:
            team.tier = "⚠️ WATCH"
        
        # Identifier les forces
        adn = team.adn
        
        if adn.killer_instinct >= 2.0:
            team.strengths.append(f"🦈 PREDATOR (Killer={adn.killer_instinct:.2f})")
        if adn.panic_factor < 0.5:
            team.strengths.append(f"🧊 SANG-FROID (Panic={adn.panic_factor:.2f})")
        if adn.diesel_factor >= 0.55:
            team.strengths.append(f"🚂 DIESEL ({adn.diesel_factor:.2f})")
        if adn.total_luck >= 5:
            team.strengths.append(f"🍀 CHANCEUX (Luck={adn.total_luck:+.1f})")
        if adn.home_strength >= 70:
            team.strengths.append(f"🏠 FORTERESSE (Home={adn.home_strength})")
        if adn.away_strength >= 50:
            team.strengths.append(f"🚗 ROAD WARRIOR (Away={adn.away_strength})")
        if adn.btts_tendency >= 70:
            team.strengths.append(f"⚽ BTTS MACHINE ({adn.btts_tendency}%)")
        if adn.set_piece_threat >= 25:
            team.strengths.append(f"🎯 SET PIECE ({adn.set_piece_threat:.1f}%)")
        
        # Forces basées sur marchés
        for market in team.top_markets[:2]:
            if market in team.markets:
                mp = team.markets[market]
                team.strengths.append(f"📈 {market.upper()}: +{mp.pnl:.1f}u ({mp.win_rate:.0f}% WR)")
        
        # Pépites
        for market in team.pepites[:2]:
            if market in team.markets:
                mp = team.markets[market]
                team.strengths.append(f"💎 PÉPITE {market.upper()}: +{mp.pnl:.1f}u (global: {mp.global_pnl:.1f}u)")
        
        # Identifier les faiblesses
        if adn.panic_factor >= 1.5:
            team.weaknesses.append(f"😰 FRAGILE (Panic={adn.panic_factor:.2f})")
        if adn.total_luck <= -5:
            team.weaknesses.append(f"😢 MALCHANCEUX (Luck={adn.total_luck:.1f})")
        if adn.home_strength > 0 and adn.away_strength > 0:
            if adn.home_strength - adn.away_strength >= 40:
                team.weaknesses.append(f"🏚️ HOME DEPENDENT (H{adn.home_strength}/A{adn.away_strength})")
        
        # Faiblesses basées sur marchés
        for market in team.worst_markets[:2]:
            if market in team.markets:
                mp = team.markets[market]
                if mp.pnl < -2:
                    team.weaknesses.append(f"📉 {market.upper()}: {mp.pnl:.1f}u ({mp.win_rate:.0f}% WR)")
        
        # Faiblesses basées sur classification pertes
        if team.loss_classification.erreur_pct >= 40:
            team.weaknesses.append(f"🔴 ERREURS MODÈLE ({team.loss_classification.erreur_pct:.0f}%)")
        
        # Diagnostic
        if team.loss_classification.malchance_pct >= 80:
            team.diagnostic = "🍀 Pertes = VARIANCE - Continuer"
        elif team.loss_classification.erreur_pct >= 40:
            team.diagnostic = "🔧 Pertes = ERREURS - Ajuster modèle"
        elif team.global_pnl > 0:
            team.diagnostic = "✅ PROFITABLE - Stratégie validée"
        elif team.total_bets == 0:
            team.diagnostic = "🆕 Nouvelle équipe - Observer"
        else:
            team.diagnostic = "⚠️ À SURVEILLER - Optimisation requise"
        
        # Recommandation
        if team.custom_strategy:
            team.recommendation = f"Appliquer: {team.custom_strategy.name}"
    
    async def run_analysis(self):
        """Exécute l'analyse V7 complète"""
        self.load_audit_data()
        await self.load_global_market_performance()
        await self.load_team_profiles()
        await self.load_team_strategies()
        await self.load_market_performance()
        
        print(f"\n{Colors.CYAN}🔬 Analyse V7 de {len(self.teams)} équipes...{Colors.END}")
        
        for team in self.teams.values():
            self.analyze_team(team)
        
        print(f"   → {len(self.teams)} équipes analysées avec stratégies personnalisées")
    
    def print_team_fiche(self, team_name: str):
        """Affiche la fiche V7 complète d'une équipe"""
        if team_name not in self.teams:
            print(f"{Colors.RED}❌ Équipe '{team_name}' non trouvée{Colors.END}")
            return
        
        t = self.teams[team_name]
        adn = t.adn
        
        print(f"\n{'═'*130}")
        print(f"║{Colors.BOLD}{Colors.GOLD}  🧬 QUANTUM V7 FICHE ADN: {t.team_name.upper():<85}{Colors.END}║")
        print(f"{'═'*130}")
        
        # Header
        tier_color = Colors.GOLD if 'ELITE' in t.tier else Colors.GREEN if 'GOLD' in t.tier else Colors.YELLOW if 'SILVER' in t.tier else Colors.WHITE
        print(f"║ {tier_color}{t.tier:<12}{Colors.END} │ Ligue: {adn.league[:15]:<15} │ Style: {adn.style[:20]:<20} │ {t.diagnostic:<40} ║")
        print(f"{'─'*130}")
        
        # Performance globale
        wr_color = Colors.GREEN if t.global_wr >= 65 else Colors.YELLOW if t.global_wr >= 55 else Colors.RED
        pnl_color = Colors.GREEN if t.global_pnl > 0 else Colors.RED
        
        print(f"║ {Colors.CYAN}📊 PERFORMANCE GLOBALE{Colors.END}{' '*105}║")
        print(f"║    Paris: {t.total_bets:<5} │ Wins: {t.total_wins:<4} │ Losses: {t.total_losses:<4} │ "
              f"WR: {wr_color}{t.global_wr:>5.1f}%{Colors.END} │ ROI: {t.global_roi:>+6.1f}% │ "
              f"P&L: {pnl_color}{t.global_pnl:>+8.1f}u{Colors.END}{' '*20}║")
        
        lc = t.loss_classification
        print(f"║    Classification pertes: Malchance {lc.malchance_pct:>5.1f}% │ Erreurs {lc.erreur_pct:>5.1f}%{' '*60}║")
        print(f"{'─'*130}")
        
        # ADN COMPLET (15 vecteurs)
        print(f"║ {Colors.MAGENTA}🧬 ADN COMPLET (15 VECTEURS){Colors.END}{' '*99}║")
        print(f"║    ┌─ PSYCHE ─────────────────────┬─ TEMPORAL ────────────────────┬─ LUCK ────────────────────────┐{' '*15}║")
        print(f"║    │ Killer: {adn.killer_instinct:>6.2f}              │ Diesel: {adn.diesel_factor:>6.2f}               │ Total Luck: {adn.total_luck:>+6.1f}            │{' '*15}║")
        print(f"║    │ Panic:  {adn.panic_factor:>6.2f}              │ 1H Dom: {adn.first_half_dominance:>6.2f}               │ xG Over: {adn.xg_overperformance:>+6.1f}               │{' '*15}║")
        print(f"║    │ Mental: {adn.mental_strength:>6.2f}              │ 2H Dom: {adn.second_half_dominance:>6.2f}               │                               │{' '*15}║")
        print(f"║    ├─ CONTEXT ────────────────────┼─ TACTICAL ────────────────────┼─ PHYSICAL ────────────────────┤{' '*15}║")
        print(f"║    │ Home:   {adn.home_strength:>6}              │ Set Piece: {adn.set_piece_threat:>6.1f}%           │ Intensity: {adn.intensity:>6.2f}            │{' '*15}║")
        print(f"║    │ Away:   {adn.away_strength:>6}              │ Counter: {adn.counter_attack:>6.2f}               │ Stamina: {adn.stamina:>6.2f}              │{' '*15}║")
        print(f"║    │ BTTS:   {adn.btts_tendency:>5}%             │ Poss: {adn.possession_style:>6.2f}                  │                               │{' '*15}║")
        print(f"║    │ Style:  {adn.style[:18]:<18} │ Vert: {adn.verticality:>6.2f}                  │                               │{' '*15}║")
        print(f"║    └───────────────────────────────┴───────────────────────────────┴───────────────────────────────┘{' '*15}║")
        print(f"{'─'*130}")
        
        # MARCHÉS (22 testés)
        print(f"║ {Colors.BLUE}📈 PERFORMANCE PAR MARCHÉ (22 marchés){Colors.END}{' '*89}║")
        
        if t.markets:
            sorted_markets = sorted(t.markets.values(), key=lambda x: x.pnl, reverse=True)
            
            # Top 5 et Bottom 5
            print(f"║    {'─'*120}║")
            print(f"║    {'Marché':<15} │ {'Picks':>5} │ {'Wins':>4} │ {'WR%':>6} │ {'P&L':>8} │ {'Odds':>5} │ {'Global P&L':>10} │ {'Statut':<20} ║")
            print(f"║    {'─'*120}║")
            
            for mp in sorted_markets[:6]:
                color = Colors.GREEN if mp.pnl > 0 else Colors.RED if mp.pnl < 0 else Colors.YELLOW
                pepite = "💎 PÉPITE" if mp.is_pepite else ""
                status = f"✅ TOP" if mp.pnl > 2 else f"⚠️ MOYEN" if mp.pnl >= -1 else f"❌ ÉVITER"
                print(f"║    {mp.market:<15} │ {mp.picks:>5} │ {mp.wins:>4} │ {mp.win_rate:>5.1f}% │ "
                      f"{color}{mp.pnl:>+7.1f}u{Colors.END} │ {mp.avg_odds:>5.2f} │ {mp.global_pnl:>+9.1f}u │ {status} {pepite:<10} ║")
            
            if len(sorted_markets) > 6:
                print(f"║    {'...':<15} │ {'...':>5} │ {'...':>4} │ {'...':>6} │ {'...':>8} │ {'...':>5} │ {'...':>10} │ {'...':>20} ║")
                for mp in sorted_markets[-3:]:
                    color = Colors.GREEN if mp.pnl > 0 else Colors.RED if mp.pnl < 0 else Colors.YELLOW
                    status = f"✅ TOP" if mp.pnl > 2 else f"⚠️ MOYEN" if mp.pnl >= -1 else f"❌ ÉVITER"
                    print(f"║    {mp.market:<15} │ {mp.picks:>5} │ {mp.wins:>4} │ {mp.win_rate:>5.1f}% │ "
                          f"{color}{mp.pnl:>+7.1f}u{Colors.END} │ {mp.avg_odds:>5.2f} │ {mp.global_pnl:>+9.1f}u │ {status:<20} ║")
        
        print(f"{'─'*130}")
        
        # STRATÉGIE PERSONNALISÉE
        print(f"║ {Colors.GOLD}🎯 STRATÉGIE PERSONNALISÉE V7{Colors.END}{' '*98}║")
        if t.custom_strategy:
            cs = t.custom_strategy
            print(f"║    Nom: {Colors.BOLD}{cs.name:<100}{Colors.END}║")
            print(f"║    Raisonnement: {cs.reasoning[:100]:<100}║")
            print(f"║    Marchés FOCUS: {', '.join(cs.markets_focus[:5]) if cs.markets_focus else 'Aucun identifié':<90}║")
            print(f"║    Marchés ÉVITER: {', '.join(cs.markets_avoid[:5]) if cs.markets_avoid else 'Aucun':<89}║")
            print(f"║    WR Attendu: {cs.expected_wr:>5.1f}% │ ROI Attendu: {cs.expected_roi:>+6.1f}%{' '*75}║")
        
        print(f"{'─'*130}")
        
        # FORCES
        print(f"║ {Colors.GREEN}💪 FORCES{Colors.END}{' '*118}║")
        for s in t.strengths[:6]:
            print(f"║    {s:<123}║")
        if not t.strengths:
            print(f"║    (Aucune force identifiée){' '*98}║")
        
        # FAIBLESSES
        print(f"║ {Colors.RED}⚠️ FAIBLESSES{Colors.END}{' '*114}║")
        for w in t.weaknesses[:5]:
            print(f"║    {w:<123}║")
        if not t.weaknesses:
            print(f"║    (Aucune faiblesse identifiée){' '*94}║")
        
        # PÉPITES
        if t.pepites:
            print(f"║ {Colors.PURPLE}💎 PÉPITES (marchés négatifs global mais positifs pour cette équipe){Colors.END}{' '*60}║")
            for p in t.pepites:
                if p in t.markets:
                    mp = t.markets[p]
                    print(f"║    {p}: Cette équipe +{mp.pnl:.1f}u vs Global {mp.global_pnl:.1f}u{' '*75}║")
        
        print(f"{'═'*130}\n")
    
    def print_summary(self):
        """Affiche le résumé global V7"""
        teams_with_bets = [t for t in self.teams.values() if t.total_bets > 0]
        
        print(f"\n{'═'*140}")
        print(f"║{Colors.BOLD}{Colors.GOLD}                              🧬 QUANTUM V7 SMART QUANT INSTITUTIONAL - RÉSUMÉ ({len(self.teams)} ÉQUIPES)                                    {Colors.END}║")
        print(f"{'═'*140}")
        
        # Stats globales
        total_bets = sum(t.total_bets for t in teams_with_bets)
        total_wins = sum(t.total_wins for t in teams_with_bets)
        total_pnl = sum(t.global_pnl for t in teams_with_bets)
        global_wr = (total_wins / total_bets * 100) if total_bets > 0 else 0
        
        profitable = sum(1 for t in teams_with_bets if t.global_pnl > 0)
        losing = len(teams_with_bets) - profitable
        pepite_count = sum(len(t.pepites) for t in teams_with_bets)
        
        print(f"║ 📊 {total_bets} paris │ {total_wins}W │ {global_wr:.1f}% WR │ {total_pnl:+.1f}u P&L │ {profitable} profitables / {losing} en surveillance │ {pepite_count} pépites identifiées{' '*10}║")
        print(f"{'─'*140}")
        
        # Distribution par tier
        tiers = defaultdict(list)
        for t in teams_with_bets:
            tiers[t.tier].append(t)
        
        print(f"║ 🏆 DISTRIBUTION PAR TIER{' '*113}║")
        for tier in ['💎 ELITE', '🏆 GOLD', '✅ SILVER', '⚪ BRONZE', '⚠️ WATCH']:
            if tier in tiers:
                teams = tiers[tier]
                tier_pnl = sum(t.global_pnl for t in teams)
                tier_wr = sum(t.global_wr for t in teams) / len(teams) if teams else 0
                print(f"║    {tier:<12} │ {len(teams):>3} équipes │ {tier_wr:>5.1f}% WR │ {tier_pnl:>+8.1f}u P&L{' '*75}║")
        
        print(f"{'─'*140}")
        
        # Top 10 équipes avec leur stratégie personnalisée
        print(f"║ 🥇 TOP 10 ÉQUIPES AVEC STRATÉGIE PERSONNALISÉE{' '*90}║")
        sorted_teams = sorted(teams_with_bets, key=lambda x: x.global_pnl, reverse=True)[:10]
        
        print(f"║ {'#':<3} {'Équipe':<22} {'Tier':<12} {'Bets':>5} {'WR%':>6} {'P&L':>8} {'Stratégie Personnalisée V7':<50} ║")
        print(f"║ {'─'*135} ║")
        
        for i, t in enumerate(sorted_teams, 1):
            color = Colors.GREEN if t.global_pnl > 0 else Colors.RED
            strat_name = t.custom_strategy.name[:48] if t.custom_strategy else "N/A"
            print(f"║ {i:<3} {t.team_name[:21]:<22} {t.tier:<12} {t.total_bets:>5} {t.global_wr:>5.1f}% "
                  f"{color}{t.global_pnl:>+7.1f}u{Colors.END} {strat_name:<50} ║")
        
        print(f"{'─'*140}")
        
        # Pépites identifiées
        all_pepites = []
        for t in teams_with_bets:
            for p in t.pepites:
                if p in t.markets:
                    mp = t.markets[p]
                    all_pepites.append((t.team_name, p, mp.pnl, mp.global_pnl))
        
        if all_pepites:
            all_pepites.sort(key=lambda x: x[2], reverse=True)
            print(f"║ 💎 TOP PÉPITES (marchés négatifs global mais positifs pour l'équipe){' '*70}║")
            for team, market, pnl, global_pnl in all_pepites[:8]:
                print(f"║    {team[:20]:<22} │ {market:<12} │ Équipe: {Colors.GREEN}+{pnl:>5.1f}u{Colors.END} │ Global: {Colors.RED}{global_pnl:>+6.1f}u{Colors.END}{' '*50}║")
        
        print(f"{'═'*140}\n")
    
    def save_report(self):
        """Sauvegarde le rapport V7 complet"""
        teams_with_bets = [t for t in self.teams.values() if t.total_bets > 0]
        
        report = {
            'version': 'V7.0 Smart Quant Institutional',
            'timestamp': datetime.now().isoformat(),
            'philosophy': '1 équipe = 1 ADN unique = 1 stratégie sur mesure',
            'summary': {
                'total_teams': len(self.teams),
                'teams_with_bets': len(teams_with_bets),
                'total_bets': sum(t.total_bets for t in teams_with_bets),
                'total_pnl': round(sum(t.global_pnl for t in teams_with_bets), 2),
                'profitable_teams': sum(1 for t in teams_with_bets if t.global_pnl > 0),
                'pepites_found': sum(len(t.pepites) for t in teams_with_bets),
                'markets_analyzed': 22,
                'adn_vectors': 15
            },
            'teams': {}
        }
        
        for t in sorted(self.teams.values(), key=lambda x: x.global_pnl, reverse=True):
            adn = t.adn
            report['teams'][t.team_name] = {
                'tier': t.tier,
                'diagnostic': t.diagnostic,
                'performance': {
                    'bets': t.total_bets,
                    'wins': t.total_wins,
                    'losses': t.total_losses,
                    'win_rate': round(t.global_wr, 1),
                    'pnl': round(t.global_pnl, 1),
                    'roi': round(t.global_roi, 1)
                },
                'loss_classification': {
                    'total': t.loss_classification.total_losses,
                    'malchance': t.loss_classification.malchance,
                    'malchance_pct': round(t.loss_classification.malchance_pct, 1),
                    'erreur_pct': round(t.loss_classification.erreur_pct, 1)
                },
                'adn': {
                    'league': adn.league,
                    'style': adn.style,
                    'psyche': {
                        'killer_instinct': round(adn.killer_instinct, 2),
                        'panic_factor': round(adn.panic_factor, 2),
                        'mental_strength': round(adn.mental_strength, 2)
                    },
                    'temporal': {
                        'diesel_factor': round(adn.diesel_factor, 2),
                        'first_half': round(adn.first_half_dominance, 2),
                        'second_half': round(adn.second_half_dominance, 2)
                    },
                    'luck': {
                        'total_luck': round(adn.total_luck, 1),
                        'xg_overperformance': round(adn.xg_overperformance, 1)
                    },
                    'context': {
                        'home_strength': adn.home_strength,
                        'away_strength': adn.away_strength,
                        'btts_tendency': adn.btts_tendency
                    },
                    'tactical': {
                        'set_piece_threat': round(adn.set_piece_threat, 1),
                        'counter_attack': round(adn.counter_attack, 2),
                        'possession': round(adn.possession_style, 2),
                        'verticality': round(adn.verticality, 2)
                    }
                },
                'markets': {
                    m.market: {
                        'picks': m.picks,
                        'wins': m.wins,
                        'win_rate': round(m.win_rate, 1),
                        'pnl': round(m.pnl, 1),
                        'avg_odds': round(m.avg_odds, 2),
                        'is_pepite': m.is_pepite,
                        'global_pnl': round(m.global_pnl, 1)
                    }
                    for m in sorted(t.markets.values(), key=lambda x: x.pnl, reverse=True)
                },
                'top_markets': t.top_markets,
                'worst_markets': t.worst_markets,
                'pepites': t.pepites,
                'custom_strategy': {
                    'name': t.custom_strategy.name if t.custom_strategy else None,
                    'markets_focus': t.custom_strategy.markets_focus if t.custom_strategy else [],
                    'markets_avoid': t.custom_strategy.markets_avoid if t.custom_strategy else [],
                    'reasoning': t.custom_strategy.reasoning if t.custom_strategy else None,
                    'expected_wr': round(t.custom_strategy.expected_wr, 1) if t.custom_strategy else 0,
                    'expected_roi': round(t.custom_strategy.expected_roi, 1) if t.custom_strategy else 0
                },
                'strengths': t.strengths,
                'weaknesses': t.weaknesses,
                'recommendation': t.recommendation
            }
        
        # Sauvegarder
        filename = f"quantum_v7_smart_quant_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"{Colors.GREEN}✅ Rapport sauvegardé: {filename}{Colors.END}")
        
        with open('quantum_v7_smart_quant_latest.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"{Colors.GREEN}✅ Rapport sauvegardé: quantum_v7_smart_quant_latest.json{Colors.END}")
        
        return filename
    
    async def run(self, team_to_show: str = None, show_top: int = 0, show_all: bool = False):
        """Exécute le rapport V7 complet"""
        await self.connect()
        await self.run_analysis()
        
        # Afficher le résumé
        self.print_summary()
        
        if team_to_show:
            # Équipe spécifique
            self.print_team_fiche(team_to_show)
        elif show_all:
            # Toutes les équipes
            for t in sorted(self.teams.values(), key=lambda x: x.global_pnl, reverse=True):
                if t.total_bets > 0:
                    self.print_team_fiche(t.team_name)
        elif show_top > 0:
            # Top N équipes
            teams_sorted = sorted([t for t in self.teams.values() if t.total_bets > 0], 
                                 key=lambda x: x.global_pnl, reverse=True)[:show_top]
            for t in teams_sorted:
                self.print_team_fiche(t.team_name)
        else:
            # Par défaut: Top 3 + Bottom 3
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
    parser = argparse.ArgumentParser(description='Quantum V7 Smart Quant Institutional')
    parser.add_argument('--team', type=str, help='Analyser une équipe spécifique')
    parser.add_argument('--top', type=int, default=0, help='Afficher les N meilleures équipes')
    parser.add_argument('--all', action='store_true', help='Afficher toutes les équipes')
    args = parser.parse_args()
    
    analyzer = QuantumV7SmartQuant()
    await analyzer.run(team_to_show=args.team, show_top=args.top, show_all=args.all)


if __name__ == "__main__":
    asyncio.run(main())
