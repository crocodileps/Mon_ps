#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                           QUANTUM BACKTEST V3.0 - ADN UNIQUE PAR ÉQUIPE                                       ║
╠═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                                               ║
║  PRINCIPE FONDAMENTAL:                                                                                        ║
║  • Chaque équipe = ADN UNIQUE (pas de groupement par catégorie/stratégie)                                    ║
║  • C'est l'ÉQUIPE qui génère le ROI, pas la stratégie seule                                                  ║
║  • weight = équipe.roi × momentum_factor                                                                     ║
║  • Marché sélectionné selon best_strategy de l'équipe la plus fiable                                         ║
║                                                                                                               ║
║  DONNÉES:                                                                                                     ║
║  • Vraies cotes depuis odds_history, odds_totals, odds_btts                                                  ║
║  • DNA depuis quantum.v_team_best_strategy + team_xg_tendencies                                              ║
║                                                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import asyncpg
import json
import argparse
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

# ═══════════════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════════════

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "monps_user",
    "password": "monps_secure_password_2024",
    "database": "monps_db"
}

# Momentum factors
MOMENTUM_FACTORS = {
    "BLAZING": 1.25,
    "HOT": 1.10,
    "NEUTRAL": 1.00,
    "COLD": 0.85,
    "FREEZING": 0.65
}

# Mapping stratégie → marchés préférés (par ordre de priorité)
STRATEGY_TO_MARKETS = {
    "CONVERGENCE_OVER_MC": ["over_25", "btts_yes", "dc_12"],
    "QUANT_BEST_MARKET": ["dc_1x", "dc_12", "over_15"],  # Zone BANKER
    "MONTE_CARLO_PURE": ["over_25", "btts_yes"],
    "TOTAL_CHAOS": ["over_35", "btts_yes", "over_25"],
    "CONVERGENCE_OVER_PURE": ["over_25", "dc_12"],
    "CONVERGENCE_UNDER_MC": ["under_25", "btts_no"],
    "MC_V2_PURE": ["over_25", "btts_yes"],
    "DEFAULT": ["dc_12", "dc_1x", "over_25"]
}

# Zone de cotes et seuils
ODDS_ZONES = {
    "BANKER": {"min": 1.20, "max": 1.60, "wr_target": 0.68},
    "SWEET_SPOT": {"min": 1.60, "max": 1.90, "wr_target": 0.61},
    "VALUE": {"min": 1.90, "max": 2.50, "wr_target": 0.54},
    "SPECULATIVE": {"min": 2.50, "max": 20.0, "wr_target": 0.45}
}


# ═══════════════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class TeamDNA:
    """ADN UNIQUE d'une équipe"""
    name: str
    tier: str = "EXPERIMENTAL"
    best_strategy: str = "DEFAULT"
    roi: float = 0.0  # ROI de l'équipe avec sa best_strategy
    win_rate: float = 0.0
    style: str = "balanced"
    psyche: str = "BALANCED"
    killer_instinct: float = 1.0
    xg_for: float = 1.2
    xg_against: float = 1.2
    btts_rate: float = 0.50
    over25_rate: float = 0.50
    # Meilleur marché validé par market_performance
    best_market: str = None
    market_picks: int = 0
    market_wr: float = 0.0
    market_pnl: float = 0.0
    bayesian_score: float = 0.0
    
    def get_preferred_markets(self) -> List[str]:
        """Retourne le meilleur marché validé, sinon fallback sur stratégie"""
        if self.best_market:
            return [self.best_market]
        return STRATEGY_TO_MARKETS.get(self.best_strategy, STRATEGY_TO_MARKETS["DEFAULT"])


@dataclass
class MatchOdds:
    """Cotes d'un match"""
    match_id: str
    # 1X2
    home_odds: float = 0.0
    draw_odds: float = 0.0
    away_odds: float = 0.0
    # Double Chance (calculé)
    dc_1x: float = 0.0  # Home or Draw
    dc_x2: float = 0.0  # Draw or Away
    dc_12: float = 0.0  # Home or Away
    # Over/Under
    over_15: float = 0.0
    over_25: float = 0.0
    over_35: float = 0.0
    under_15: float = 0.0
    under_25: float = 0.0
    under_35: float = 0.0
    # BTTS
    btts_yes: float = 0.0
    btts_no: float = 0.0
    
    def calculate_dc(self):
        """Calcule les cotes Double Chance depuis 1X2"""
        if self.home_odds > 0 and self.draw_odds > 0 and self.away_odds > 0:
            # DC = 1 / (1/odds1 + 1/odds2)
            self.dc_1x = 1 / (1/self.home_odds + 1/self.draw_odds) if self.home_odds > 0 and self.draw_odds > 0 else 0
            self.dc_x2 = 1 / (1/self.draw_odds + 1/self.away_odds) if self.draw_odds > 0 and self.away_odds > 0 else 0
            self.dc_12 = 1 / (1/self.home_odds + 1/self.away_odds) if self.home_odds > 0 and self.away_odds > 0 else 0
    
    def get_odds(self, market: str) -> float:
        """Retourne la cote pour un marché donné"""
        mapping = {
            "home": self.home_odds,
            "draw": self.draw_odds,
            "away": self.away_odds,
            "dc_1x": self.dc_1x,
            "dc_x2": self.dc_x2,
            "dc_12": self.dc_12,
            "over_15": self.over_15,
            "over_25": self.over_25,
            "over_35": self.over_35,
            "under_15": self.under_15,
            "under_25": self.under_25,
            "under_35": self.under_35,
            "btts_yes": self.btts_yes,
            "btts_no": self.btts_no
        }
        return mapping.get(market, 0.0)


@dataclass
class BetDecision:
    """Décision de pari"""
    match_id: str
    match_date: str
    match_name: str
    lead_team: str  # Équipe qui "drive" la décision
    lead_team_roi: float
    lead_team_strategy: str
    market: str
    odds: float
    zone: str
    decision: str
    result: str = None
    profit_loss: float = 0.0
    home_momentum: str = "NEUTRAL"
    away_momentum: str = "NEUTRAL"


# ═══════════════════════════════════════════════════════════════════════════════════════
# MOMENTUM CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════════════════

class MomentumCalculator:
    """Calcule le momentum L5"""
    
    def __init__(self, match_history: List[Dict]):
        self.history = sorted(match_history, key=lambda x: x['match_date'], reverse=True)
    
    def get_momentum(self, team_name: str, before_date: datetime) -> Tuple[str, float]:
        """Retourne (status, form_score)"""
        team_matches = []
        for m in self.history:
            if m['match_date'] >= before_date:
                continue
            if m['home_team'] == team_name or m['away_team'] == team_name:
                team_matches.append(m)
            if len(team_matches) >= 5:
                break
        
        if len(team_matches) < 3:
            return "NEUTRAL", 0.5
        
        results = []
        for m in team_matches[:5]:
            if m['home_team'] == team_name:
                if m['home_goals'] > m['away_goals']:
                    results.append('W')
                elif m['home_goals'] == m['away_goals']:
                    results.append('D')
                else:
                    results.append('L')
            else:
                if m['away_goals'] > m['home_goals']:
                    results.append('W')
                elif m['away_goals'] == m['home_goals']:
                    results.append('D')
                else:
                    results.append('L')
        
        # Streak detection
        if results[:4] == ['W', 'W', 'W', 'W']:
            return "BLAZING", 1.0
        if results[:3] == ['W', 'W', 'W']:
            return "HOT", 0.8
        if results[:4] == ['L', 'L', 'L', 'L']:
            return "FREEZING", 0.0
        if results[:3] == ['L', 'L', 'L']:
            return "COLD", 0.2
        
        # Form score
        points = sum(3 if r == 'W' else 1 if r == 'D' else 0 for r in results)
        form = points / (len(results) * 3)
        
        if form >= 0.7:
            return "HOT", form
        elif form <= 0.3:
            return "COLD", form
        return "NEUTRAL", form


# ═══════════════════════════════════════════════════════════════════════════════════════
# RESULT EVALUATOR
# ═══════════════════════════════════════════════════════════════════════════════════════

def evaluate_result(market: str, home_goals: int, away_goals: int) -> str:
    """Évalue si le pari est gagnant"""
    total = home_goals + away_goals
    btts = home_goals > 0 and away_goals > 0
    
    results = {
        "home": "WIN" if home_goals > away_goals else "LOSS",
        "draw": "WIN" if home_goals == away_goals else "LOSS",
        "away": "WIN" if away_goals > home_goals else "LOSS",
        "dc_1x": "WIN" if home_goals >= away_goals else "LOSS",
        "dc_x2": "WIN" if away_goals >= home_goals else "LOSS",
        "dc_12": "WIN" if home_goals != away_goals else "LOSS",
        "over_15": "WIN" if total > 1 else "LOSS",
        "over_25": "WIN" if total > 2 else "LOSS",
        "over_35": "WIN" if total > 3 else "LOSS",
        "under_15": "WIN" if total < 2 else "LOSS",
        "under_25": "WIN" if total < 3 else "LOSS",
        "under_35": "WIN" if total < 4 else "LOSS",
        "btts_yes": "WIN" if btts else "LOSS",
        "btts_no": "WIN" if not btts else "LOSS",
    }
    return results.get(market, "UNKNOWN")


def get_zone(odds: float) -> str:
    """Retourne la zone de cotes"""
    for zone, params in ODDS_ZONES.items():
        if params["min"] <= odds < params["max"]:
            return zone
    return "SPECULATIVE"


# ═══════════════════════════════════════════════════════════════════════════════════════
# BACKTEST ENGINE V3
# ═══════════════════════════════════════════════════════════════════════════════════════

class QuantumBacktestV3:
    """Moteur de backtest - ADN unique par équipe"""
    
    def __init__(self):
        self.pool = None
        self.team_dna: Dict[str, TeamDNA] = {}
        self.match_odds: Dict[str, MatchOdds] = {}
        self.match_history: List[Dict] = []
        self.momentum_calc: MomentumCalculator = None
        self.decisions: List[BetDecision] = []
        self.name_mapping: Dict[str, str] = {}  # historical -> quantum
        self.name_mapping_reverse: Dict[str, str] = {}  # quantum -> historical
    
    async def connect(self):
        self.pool = await asyncpg.create_pool(**DB_CONFIG, min_size=2, max_size=5)
        print("✅ Connexion PostgreSQL établie")
    
    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            print("🔌 Connexion fermée")
    
    async def load_team_dna(self):
        """Charge l'ADN UNIQUE de chaque équipe"""
        async with self.pool.acquire() as conn:
            print("📊 Chargement ADN équipes (quantum.v_team_best_strategy)...")
            
            rows = await conn.fetch("""
                SELECT 
                    v.team_name, 
                    v.tier, 
                    v.current_style,
                    v.team_wr as win_rate,
                    v.best_strategy,
                    v.strategy_wr,
                    COALESCE(s.roi, 0) as roi,
                    p.quantum_dna->'psyche_dna'->>'profile' as psyche,
                    (p.quantum_dna->'psyche_dna'->>'killer_instinct')::float as killer_instinct
                FROM quantum.v_team_best_strategy v
                JOIN quantum.team_profiles p ON v.team_name = p.team_name
                LEFT JOIN quantum.team_strategies s ON s.team_name = v.team_name AND s.is_best_strategy = true
            """)
            
            for r in rows:
                self.team_dna[r['team_name']] = TeamDNA(
                    name=r['team_name'],
                    tier=r['tier'] or "EXPERIMENTAL",
                    best_strategy=r['best_strategy'] or "DEFAULT",
                    roi=float(r['roi'] or 0),
                    win_rate=float(r['win_rate'] or 0) / 100,
                    style=r['current_style'] or "balanced",
                    psyche=r['psyche'] or "BALANCED",
                    killer_instinct=float(r['killer_instinct'] or 1.0)
                )
            
            print(f"   → {len(self.team_dna)} équipes avec ADN unique")
            
            # Enrichir avec xG
            print("📊 Enrichissement avec team_xg_tendencies...")
            xg_rows = await conn.fetch("""
                SELECT team_name, avg_xg_for, avg_xg_against, btts_xg_rate, over25_xg_rate
                FROM team_xg_tendencies
            """)
            
            for r in xg_rows:
                if r['team_name'] in self.team_dna:
                    dna = self.team_dna[r['team_name']]
                    dna.xg_for = float(r['avg_xg_for'] or 1.2)
                    dna.xg_against = float(r['avg_xg_against'] or 1.2)
                    dna.btts_rate = float(r['btts_xg_rate'] or 0.5)
                    dna.over25_rate = float(r['over25_xg_rate'] or 0.5)
            
            print(f"   → xG enrichi")
            
            # Charger le MEILLEUR MARCHÉ par équipe depuis market_performance
            print("📊 Chargement meilleur marché par équipe...")
            market_rows = await conn.fetch("""
                SELECT DISTINCT ON (team_name) 
                    team_name, market_type as best_market, total_picks, win_rate, total_pnl,
                    (total_pnl / 100.0) * LN(total_picks + 1) as bayesian_score
                FROM quantum.market_performance 
                WHERE total_picks >= 3 AND total_pnl > 0
                ORDER BY team_name, total_pnl DESC
            """)
            
            for r in market_rows:
                if r['team_name'] in self.team_dna:
                    dna = self.team_dna[r['team_name']]
                    dna.best_market = r['best_market']
                    dna.market_picks = r['total_picks']
                    dna.market_wr = float(r['win_rate'] or 0)
                    dna.market_pnl = float(r['total_pnl'] or 0)
                    dna.bayesian_score = float(r['bayesian_score'] or 0)
            
            print(f"   → {len(market_rows)} équipes avec meilleur marché")
            
            # Charger le mapping inversé (historical_name -> quantum_name) pour tracking_clv_picks
            print("📊 Chargement mapping noms équipes...")
            mapping_rows = await conn.fetch("""
                SELECT quantum_name, historical_name FROM quantum.team_name_mapping
            """)
            self.name_mapping = {}  # historical -> quantum
            self.name_mapping_reverse = {}  # quantum -> historical
            for r in mapping_rows:
                self.name_mapping[r['historical_name']] = r['quantum_name']
                self.name_mapping_reverse[r['quantum_name']] = r['historical_name']
            print(f"   → {len(self.name_mapping)} mappings chargés")
    
    async def load_matches(self, start_date: str, end_date: str):
        """Charge les matchs depuis tracking_clv_picks (source principale avec cotes intégrées)"""
        async with self.pool.acquire() as conn:
            print("📊 Chargement matchs depuis tracking_clv_picks...")
            
            # Charger tous les picks résolus avec leurs cotes et résultats
            rows = await conn.fetch("""
                SELECT DISTINCT ON (home_team, away_team, DATE(commence_time), market_type)
                    home_team, away_team, commence_time,
                    market_type, odds_taken, is_winner, profit_loss,
                    score_home, score_away
                FROM tracking_clv_picks
                WHERE is_resolved = true
                  AND home_team IS NOT NULL 
                  AND away_team IS NOT NULL
                  AND commence_time >= $1 
                  AND commence_time <= $2
                ORDER BY home_team, away_team, DATE(commence_time), market_type, created_at DESC
            """, datetime.strptime(start_date, "%Y-%m-%d"),
                datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1))
            
            # Grouper par match unique
            matches_dict = {}
            for r in rows:
                match_key = (r['home_team'], r['away_team'], r['commence_time'].date())
                if match_key not in matches_dict:
                    matches_dict[match_key] = {
                        'match_id': f"{r['home_team']}_{r['away_team']}_{r['commence_time'].date()}",
                        'home_team': r['home_team'],
                        'away_team': r['away_team'],
                        'match_date': r['commence_time'],
                        'home_goals': r['score_home'],
                        'away_goals': r['score_away'],
                        'markets': {}
                    }
                # Stocker les cotes par marché
                market = r['market_type']
                matches_dict[match_key]['markets'][market] = {
                    'odds': float(r['odds_taken'] or 0),
                    'is_winner': r['is_winner'],
                    'profit_loss': float(r['profit_loss'] or 0)
                }
            
            self.match_history = list(matches_dict.values())
            print(f"   → {len(self.match_history)} matchs uniques avec cotes intégrées")
            
            # Créer les MatchOdds depuis les données
            for match in self.match_history:
                match_key = f"{match['home_team']}_{match['away_team']}_{match['match_date']}"
                odds = MatchOdds(match_id=match_key)
                
                markets = match['markets']
                if 'home' in markets:
                    odds.home_odds = markets['home']['odds']
                if 'draw' in markets:
                    odds.draw_odds = markets['draw']['odds']
                if 'away' in markets:
                    odds.away_odds = markets['away']['odds']
                if 'dc_1x' in markets:
                    odds.dc_1x = markets['dc_1x']['odds']
                if 'dc_x2' in markets:
                    odds.dc_x2 = markets['dc_x2']['odds']
                if 'dc_12' in markets:
                    odds.dc_12 = markets['dc_12']['odds']
                if 'over_15' in markets:
                    odds.over_15 = markets['over_15']['odds']
                if 'over_25' in markets:
                    odds.over_25 = markets['over_25']['odds']
                if 'over_35' in markets:
                    odds.over_35 = markets['over_35']['odds']
                if 'under_15' in markets:
                    odds.under_15 = markets['under_15']['odds']
                if 'under_25' in markets:
                    odds.under_25 = markets['under_25']['odds']
                if 'under_35' in markets:
                    odds.under_35 = markets['under_35']['odds']
                if 'btts_yes' in markets:
                    odds.btts_yes = markets['btts_yes']['odds']
                if 'btts_no' in markets:
                    odds.btts_no = markets['btts_no']['odds']
                
                # Calculer DC si manquant
                if odds.dc_1x == 0 and odds.home_odds > 0 and odds.draw_odds > 0:
                    odds.calculate_dc()
                
                self.match_odds[match_key] = odds
    
    def select_bet(self, match: Dict, home_dna: TeamDNA, away_dna: TeamDNA,
                   home_momentum: str, away_momentum: str, odds: MatchOdds) -> Optional[BetDecision]:
        """
        Sélectionne le pari selon l'ADN UNIQUE de chaque équipe.
        Utilise le MEILLEUR MARCHÉ validé par market_performance.
        Applique le Bayesian Score pour éviter les "One Hit Wonders".
        """
        
        # Calculer le poids effectif avec Bayesian Score
        # PRINCIPE: weight = bayesian_score × momentum_factor (ou ROI si pas de bayesian)
        home_base = home_dna.bayesian_score if home_dna and home_dna.bayesian_score > 0 else (home_dna.roi / 100 if home_dna else 0)
        away_base = away_dna.bayesian_score if away_dna and away_dna.bayesian_score > 0 else (away_dna.roi / 100 if away_dna else 0)
        
        home_weight = home_base * MOMENTUM_FACTORS.get(home_momentum, 1.0) if home_dna else 0
        away_weight = away_base * MOMENTUM_FACTORS.get(away_momentum, 1.0) if away_dna else 0
        
        # Filtre Bayesian: minimum 0.01 pour éviter les "One Hit Wonders"
        if home_weight < 0.01 and away_weight < 0.01:
            return None
        
        # ═══════════════════════════════════════════════════════════════════
        # CLASH RESOLVER: Gérer les conflits Home vs Away
        # ═══════════════════════════════════════════════════════════════════
        
        home_market = home_dna.best_market if home_dna and home_dna.best_market else None
        away_market = away_dna.best_market if away_dna and away_dna.best_market else None
        
        selected_market = None
        lead_team = None
        decision_type = "SINGLE"
        
        # CAS 1: Les deux ont des marchés validés
        if home_market and away_market:
            # Vérifier compatibilité
            over_markets = ['over_15', 'over_25', 'over_35', 'btts_yes']
            under_markets = ['under_15', 'under_25', 'under_35', 'btts_no']
            
            home_is_over = home_market in over_markets
            away_is_over = away_market in over_markets
            home_is_under = home_market in under_markets
            away_is_under = away_market in under_markets
            
            # SYNERGIE OVER: Les deux veulent des buts
            if home_is_over and away_is_over:
                decision_type = "SYNERGY_OVER"
                selected_market = "over_25"  # Marché commun
                lead_team = home_dna if home_weight >= away_weight else away_dna
                
            # SYNERGIE UNDER: Les deux ferment
            elif home_is_under and away_is_under:
                decision_type = "SYNERGY_UNDER"
                selected_market = "under_25"
                lead_team = home_dna if home_weight >= away_weight else away_dna
                
            # CONFLIT: Over vs Under
            elif (home_is_over and away_is_under) or (home_is_under and away_is_over):
                # Le plus fort gagne seulement si dominance > 2x
                if home_weight > away_weight * 2:
                    decision_type = "DOMINANCE_HOME"
                    selected_market = home_market
                    lead_team = home_dna
                elif away_weight > home_weight * 2:
                    decision_type = "DOMINANCE_AWAY"
                    selected_market = away_market
                    lead_team = away_dna
                else:
                    # SKIP: Tactical Deadlock
                    return None
            
            # Autres cas: Le plus fort décide
            else:
                if home_weight >= away_weight:
                    selected_market = home_market
                    lead_team = home_dna
                else:
                    selected_market = away_market
                    lead_team = away_dna
        
        # CAS 2: Une seule équipe a un marché validé
        elif home_market:
            selected_market = home_market
            lead_team = home_dna
        elif away_market:
            selected_market = away_market
            lead_team = away_dna
        
        # CAS 3: Aucun marché validé - utiliser fallback stratégie
        else:
            if home_weight >= away_weight and home_dna:
                lead_team = home_dna
            elif away_dna:
                lead_team = away_dna
            else:
                return None
            
            # Fallback sur stratégie
            preferred = lead_team.get_preferred_markets()
            for m in preferred:
                if odds.get_odds(m) >= 1.20:
                    selected_market = m
                    break
        
        if not selected_market or not lead_team:
            return None
        
        # Normaliser le nom du marché (over25 → over_25)
        market_normalized = selected_market.replace("over25", "over_25").replace("under25", "under_25")
        market_normalized = market_normalized.replace("over15", "over_15").replace("under15", "under_15")
        market_normalized = market_normalized.replace("over35", "over_35").replace("under35", "under_35")
        
        # Récupérer les cotes
        selected_odds = odds.get_odds(market_normalized)
        
        # Filtrer: cotes entre 1.20 et 3.50
        if selected_odds < 1.20 or selected_odds > 3.50:
            return None
        
        zone = get_zone(selected_odds)
        
        return BetDecision(
            match_id=match['match_id'],
            match_date=str(match['match_date']),
            match_name=f"{match['home_team']} vs {match['away_team']}",
            lead_team=lead_team.name,
            lead_team_roi=lead_team.roi,
            lead_team_strategy=f"{lead_team.best_strategy} ({decision_type})",
            market=market_normalized,
            odds=selected_odds,
            zone=zone,
            decision="BET",
            home_momentum=home_momentum,
            away_momentum=away_momentum
        )
    
    def get_team_dna(self, team_name: str) -> Optional[TeamDNA]:
        """Trouve le TeamDNA avec mapping de noms"""
        # Essayer le nom direct
        if team_name in self.team_dna:
            return self.team_dna[team_name]
        # Essayer via mapping (historical -> quantum)
        if team_name in self.name_mapping:
            quantum_name = self.name_mapping[team_name]
            if quantum_name in self.team_dna:
                return self.team_dna[quantum_name]
        return None
    
    async def run(self, start_date: str, end_date: str):
        """Exécute le backtest"""
        print(f"\n{'='*80}")
        print(f"🚀 QUANTUM BACKTEST V3.0 - ADN UNIQUE PAR ÉQUIPE")
        print(f"   Période: {start_date} → {end_date}")
        print(f"{'='*80}\n")
        
        await self.load_team_dna()
        await self.load_matches(start_date, end_date)
        
        print(f"\n📊 Analyse de {len(self.match_history)} matchs...\n")
        
        matches_analyzed = 0
        matches_with_dna = 0
        
        for match in self.match_history:
            matches_analyzed += 1
            
            home_team = match['home_team']
            away_team = match['away_team']
            
            home_dna = self.get_team_dna(home_team)
            away_dna = self.get_team_dna(away_team)
            
            # Au moins une équipe doit avoir un ADN
            if not home_dna and not away_dna:
                continue
            
            matches_with_dna += 1
            
            # Récupérer les cotes
            match_key = f"{home_team}_{away_team}_{match['match_date']}"
            odds = self.match_odds.get(match_key)
            if not odds:
                continue
            
            # Calculer momentum (simplifié - basé sur les matchs précédents)
            home_momentum = "NEUTRAL"
            away_momentum = "NEUTRAL"
            
            # Décision de pari
            bet = self.select_bet(match, home_dna, away_dna, home_momentum, away_momentum, odds)
            
            if bet:
                # Utiliser les résultats réels de tracking_clv_picks
                markets = match.get('markets', {})
                if bet.market in markets:
                    market_data = markets[bet.market]
                    bet.result = "WIN" if market_data['is_winner'] else "LOSS"
                    bet.profit_loss = market_data['profit_loss']
                else:
                    # Fallback: évaluer le résultat manuellement
                    if match['home_goals'] is not None and match['away_goals'] is not None:
                        bet.result = evaluate_result(bet.market, match['home_goals'], match['away_goals'])
                        if bet.result == "WIN":
                            bet.profit_loss = (bet.odds - 1) * 1.0
                        elif bet.result == "LOSS":
                            bet.profit_loss = -1.0
                        else:
                            bet.profit_loss = 0
                    else:
                        continue  # Skip si pas de résultat
                
                self.decisions.append(bet)
        
        print(f"   → {matches_analyzed} matchs analysés")
        print(f"   → {matches_with_dna} avec ADN")
        print(f"   → {len(self.decisions)} paris générés")
        
        return self._generate_report(start_date, end_date, matches_analyzed, matches_with_dna)
    
    def _generate_report(self, start_date: str, end_date: str, 
                         total_matches: int, matches_with_dna: int) -> Dict:
        """Génère le rapport de résultats"""
        decisions = self.decisions
        
        if not decisions:
            return {
                "summary": {
                    "period": f"{start_date} → {end_date}",
                    "total_matches": total_matches,
                    "matches_with_dna": matches_with_dna,
                    "total_picks": 0,
                    "wins": 0,
                    "losses": 0,
                    "win_rate": 0,
                    "roi": 0,
                    "pnl": 0
                },
                "by_zone": {},
                "by_market": {},
                "by_strategy": {},
                "by_team": {},
                "error": "Aucun pari généré - vérifier les cotes disponibles"
            }
        
        wins = sum(1 for d in decisions if d.result == "WIN")
        losses = sum(1 for d in decisions if d.result == "LOSS")
        total_pnl = sum(d.profit_loss for d in decisions)
        total_stake = len(decisions)  # 1u par pari
        
        win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0
        roi = (total_pnl / total_stake * 100) if total_stake > 0 else 0
        
        # Par zone
        by_zone = defaultdict(lambda: {"picks": 0, "wins": 0, "pnl": 0.0})
        for d in decisions:
            by_zone[d.zone]["picks"] += 1
            if d.result == "WIN":
                by_zone[d.zone]["wins"] += 1
            by_zone[d.zone]["pnl"] += d.profit_loss
        
        # Par marché
        by_market = defaultdict(lambda: {"picks": 0, "wins": 0, "pnl": 0.0})
        for d in decisions:
            by_market[d.market]["picks"] += 1
            if d.result == "WIN":
                by_market[d.market]["wins"] += 1
            by_market[d.market]["pnl"] += d.profit_loss
        
        # Par stratégie (de l'équipe lead)
        by_strategy = defaultdict(lambda: {"picks": 0, "wins": 0, "pnl": 0.0})
        for d in decisions:
            by_strategy[d.lead_team_strategy]["picks"] += 1
            if d.result == "WIN":
                by_strategy[d.lead_team_strategy]["wins"] += 1
            by_strategy[d.lead_team_strategy]["pnl"] += d.profit_loss
        
        # Par équipe lead - enrichi avec strategy, style, best_market
        by_team = defaultdict(lambda: {"picks": 0, "wins": 0, "pnl": 0.0, "roi": 0.0, 
                                        "strategy": "N/A", "style": "N/A", "best_market": "N/A"})
        for d in decisions:
            by_team[d.lead_team]["picks"] += 1
            by_team[d.lead_team]["roi"] = d.lead_team_roi
            # Extraire strategy clean (sans le type de décision)
            strat_parts = d.lead_team_strategy.split(" (")
            by_team[d.lead_team]["strategy"] = strat_parts[0] if strat_parts else "N/A"
            if d.result == "WIN":
                by_team[d.lead_team]["wins"] += 1
            by_team[d.lead_team]["pnl"] += d.profit_loss
            # Ajouter style et best_market depuis team_dna
            if d.lead_team in self.team_dna:
                dna = self.team_dna[d.lead_team]
                by_team[d.lead_team]["style"] = dna.style[:6] if dna.style else "N/A"
                by_team[d.lead_team]["best_market"] = dna.best_market if dna.best_market else "N/A"
        
        report = {
            "summary": {
                "period": f"{start_date} → {end_date}",
                "total_matches": total_matches,
                "matches_with_dna": matches_with_dna,
                "total_picks": len(decisions),
                "wins": wins,
                "losses": losses,
                "win_rate": round(win_rate * 100, 1),
                "roi": round(roi, 1),
                "pnl": round(total_pnl, 2)
            },
            "by_zone": {k: {**v, "wr": round(v["wins"]/v["picks"]*100, 1) if v["picks"] > 0 else 0} 
                        for k, v in by_zone.items()},
            "by_market": {k: {**v, "wr": round(v["wins"]/v["picks"]*100, 1) if v["picks"] > 0 else 0} 
                         for k, v in sorted(by_market.items(), key=lambda x: x[1]["pnl"], reverse=True)},
            "by_strategy": {k: {**v, "wr": round(v["wins"]/v["picks"]*100, 1) if v["picks"] > 0 else 0} 
                           for k, v in sorted(by_strategy.items(), key=lambda x: x[1]["pnl"], reverse=True)},
            "by_team": dict(sorted(by_team.items(), key=lambda x: x[1]["pnl"], reverse=True)[:30])
        }
        
        return report
    
    def print_report(self, report: Dict):
        """Affiche le rapport"""
        s = report["summary"]
        
        print(f"""
{'='*80}
📊 QUANTUM BACKTEST V3.0 - RÉSULTATS (ADN UNIQUE)
{'='*80}

┌──────────────────────────────────────────────────────────────────┐
│ Période: {s['period']}
│ Matchs: {s['total_matches']} total | {s['matches_with_dna']} avec ADN
├──────────────────────────────────────────────────────────────────┤
│ 📈 PERFORMANCE GLOBALE
│ ──────────────────────────────────────────────────────────────────
│ Picks: {s['total_picks']} | Wins: {s['wins']} | Losses: {s['losses']}
│ Win Rate: {s['win_rate']}%
│ ROI: {s['roi']:+.1f}%
│ P&L: {s['pnl']:+.2f}u
└──────────────────────────────────────────────────────────────────┘
""")
        
        print("┌──────────────────────────────────────────────────────────────────┐")
        print("│ 📊 PAR ZONE DE COTES")
        print("├──────────────────────────────────────────────────────────────────┤")
        for zone, stats in sorted(report["by_zone"].items()):
            target = ODDS_ZONES.get(zone, {}).get("wr_target", 0.5) * 100
            status = "✅" if stats["wr"] >= target else "❌"
            print(f"│ {status} {zone:15} | {stats['picks']:3} picks | {stats['wr']:5.1f}% WR | {stats['pnl']:+7.2f}u")
        print("└──────────────────────────────────────────────────────────────────┘\n")
        
        print("┌──────────────────────────────────────────────────────────────────┐")
        print("│ 📊 PAR MARCHÉ")
        print("├──────────────────────────────────────────────────────────────────┤")
        for market, stats in list(report["by_market"].items())[:10]:
            status = "✅" if stats["pnl"] > 0 else "❌"
            print(f"│ {status} {market:15} | {stats['picks']:3} picks | {stats['wr']:5.1f}% WR | {stats['pnl']:+7.2f}u")
        print("└──────────────────────────────────────────────────────────────────┘\n")
        
        print("┌──────────────────────────────────────────────────────────────────┐")
        print("│ 📊 PAR STRATÉGIE (de l'équipe lead)")
        print("├──────────────────────────────────────────────────────────────────┤")
        for strat, stats in report["by_strategy"].items():
            status = "✅" if stats["pnl"] > 0 else "❌"
            print(f"│ {status} {strat:30} | {stats['picks']:3} picks | {stats['wr']:5.1f}% WR | {stats['pnl']:+7.2f}u")
        print("└──────────────────────────────────────────────────────────────────┘\n")
        
        # ═══════════════════════════════════════════════════════════════════
        # NOUVEAU: Tableau détaillé par équipe style Hedge Fund
        # ═══════════════════════════════════════════════════════════════════
        print("╔" + "═"*120 + "╗")
        print("║" + " 🏆 ANALYSE DÉTAILLÉE PAR ÉQUIPE - ADN UNIQUE".center(120) + "║")
        print("╠" + "═"*120 + "╣")
        print("║ {:22} │ {:20} │ {:6} │ {:4} │ {:4} │ {:4} │ {:7} │ {:8} │ {:6} │ {:15} ║".format(
            "Équipe", "Best Strategy", "Style", "P", "W", "L", "WR%", "P&L", "ROI%", "Best Market"
        ))
        print("╠" + "═"*120 + "╣")
        
        # Trier par P&L décroissant
        sorted_teams = sorted(report["by_team"].items(), key=lambda x: x[1]["pnl"], reverse=True)
        
        for team, stats in sorted_teams[:25]:
            picks = stats["picks"]
            wins = stats["wins"]
            losses = picks - wins
            wr = stats["wins"] / picks * 100 if picks > 0 else 0
            pnl = stats["pnl"]
            roi_hist = stats.get("roi", 0)
            strategy = stats.get("strategy", "N/A")[:20]
            style = stats.get("style", "N/A")[:6]
            best_market = stats.get("best_market", "N/A")[:15]
            
            # Status emoji basé sur performance
            if wr >= 70:
                status = "🏆"
            elif wr >= 55:
                status = "✅"
            elif wr >= 45:
                status = "⚠️"
            else:
                status = "❌"
            
            print("║ {} {:20} │ {:20} │ {:6} │ {:4} │ {:4} │ {:4} │ {:6.1f}% │ {:+7.2f}u │ {:5.0f}% │ {:15} ║".format(
                status, team[:20], strategy, style, picks, wins, losses, wr, pnl, roi_hist, best_market
            ))
        
        print("╚" + "═"*120 + "╝")
        
        # ═══════════════════════════════════════════════════════════════════
        # Résumé des pépites et des dangers
        # ═══════════════════════════════════════════════════════════════════
        print("\n┌──────────────────────────────────────────────────────────────────┐")
        print("│ 💎 PÉPITES (100% WR avec P&L > 0.5u)")
        print("├──────────────────────────────────────────────────────────────────┤")
        pepites = [(t, s) for t, s in sorted_teams if s["wins"] == s["picks"] and s["pnl"] > 0.5]
        for team, stats in pepites[:10]:
            print(f"│ 💎 {team:25} | {stats['picks']}p | {stats['pnl']:+.2f}u")
        if not pepites:
            print("│ Aucune pépite trouvée")
        print("└──────────────────────────────────────────────────────────────────┘")
        
        print("\n┌──────────────────────────────────────────────────────────────────┐")
        print("│ ⚠️ DANGER (0% WR ou P&L < -1u)")
        print("├──────────────────────────────────────────────────────────────────┤")
        dangers = [(t, s) for t, s in sorted_teams if s["wins"] == 0 or s["pnl"] < -1]
        for team, stats in dangers[:10]:
            wr = stats["wins"] / stats["picks"] * 100 if stats["picks"] > 0 else 0
            print(f"│ ⚠️ {team:25} | {stats['picks']}p | {wr:.0f}% WR | {stats['pnl']:+.2f}u")
        if not dangers:
            print("│ Aucun danger trouvé")
        print("└──────────────────────────────────────────────────────────────────┘")
    
    def save_report(self, report: Dict, filename: str):
        """Sauvegarde le rapport en JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n✅ Rapport sauvegardé: {filename}")


# ═══════════════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════════════

async def main():
    parser = argparse.ArgumentParser(description="Quantum Backtest V3.0 - ADN Unique")
    parser.add_argument("--start", default="2025-09-01")
    parser.add_argument("--end", default="2025-12-06")
    parser.add_argument("--output", default="quantum_backtest_v3_results.json")
    args = parser.parse_args()
    
    engine = QuantumBacktestV3()
    
    try:
        await engine.connect()
        report = await engine.run(args.start, args.end)
        engine.print_report(report)
        engine.save_report(report, args.output)
    finally:
        await engine.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
