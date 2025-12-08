#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                           QUANTUM BACKTEST V2.0 - ORCHESTRATOR VALIDATION                                     ║
╠═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                                               ║
║  PHILOSOPHIE:                                                                                                 ║
║  • "Bankroll Builder" - Zone cotes 1.50-1.90 prioritaire                                                     ║
║  • Chaque équipe = ADN unique (pas de groupement par catégorie)                                              ║
║  • Edge dynamique selon zone de cotes                                                                        ║
║  • Steam comme FILTRE, pas déclencheur                                                                       ║
║                                                                                                               ║
║  USAGE:                                                                                                       ║
║      python3 quantum_backtest_v2_orchestrator.py                                                             ║
║      python3 quantum_backtest_v2_orchestrator.py --start 2025-09-01 --end 2025-12-06                        ║
║                                                                                                               ║
║  OUTPUTS:                                                                                                     ║
║      • Console: Résumé lisible                                                                               ║
║      • JSON: quantum_backtest_v2_results.json                                                                ║
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
import statistics

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

# Zone de cotes et seuils
ODDS_ZONES = {
    "BANKER": {"min": 1.40, "max": 1.70, "edge_required": 0.015, "wr_target": 0.68},
    "SWEET_SPOT": {"min": 1.70, "max": 1.90, "edge_required": 0.025, "wr_target": 0.61},
    "VALUE": {"min": 1.90, "max": 2.20, "edge_required": 0.040, "wr_target": 0.54},
    "SPECULATIVE": {"min": 2.20, "max": 10.0, "edge_required": 0.060, "wr_target": 0.50}
}

# Momentum factors
MOMENTUM_FACTORS = {
    "BLAZING": 1.25,    # WIN×4+
    "HOT": 1.10,        # WIN×3
    "NEUTRAL": 1.00,
    "COLD": 0.85,       # LOSS×2-3
    "FREEZING": 0.65    # LOSS×4+
}

# Mapping stratégie → marchés préférés
STRATEGY_TO_MARKETS = {
    "CONVERGENCE_OVER_MC": ["over_25", "btts_yes", "dc_12"],
    "QUANT_BEST_MARKET": ["dc_1x", "dc_12", "dnb_home"],
    "MONTE_CARLO_PURE": ["over_25", "btts_yes"],
    "TOTAL_CHAOS": ["over_35", "btts_yes"],
    "CONVERGENCE_UNDER_MC": ["under_25", "btts_no"],
    "BTTS_NO_PURE": ["btts_no", "under_25"],
    "DEFAULT": ["dc_12", "over_25"]
}

# BTTS Fusion weights (validés par user)
BTTS_WEIGHTS = {"tactical": 0.40, "team_xg": 0.35, "h2h": 0.25}


# ═══════════════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class TeamDNA:
    """ADN unique d'une équipe"""
    name: str
    tier: str = "EXPERIMENTAL"
    best_strategy: str = "DEFAULT"
    roi: float = 0.0
    win_rate: float = 0.0
    psyche: str = "BALANCED"
    killer_instinct: float = 1.0
    diesel_factor: float = 1.0
    style: str = "balanced"
    xg_for: float = 1.2
    xg_against: float = 1.2
    btts_rate: float = 0.50
    over25_rate: float = 0.50


@dataclass
class MatchContext:
    """Contexte complet d'un match"""
    match_id: str
    match_date: datetime
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    home_xg: float
    away_xg: float
    league: str
    home_dna: TeamDNA = None
    away_dna: TeamDNA = None
    home_momentum: str = "NEUTRAL"
    away_momentum: str = "NEUTRAL"
    friction_score: float = 50.0
    btts_prob: float = 0.50
    over25_prob: float = 0.50
    scenario: str = None
    odds: Dict[str, float] = field(default_factory=dict)
    steam_move: float = 0.0


@dataclass
class BetDecision:
    """Décision de pari"""
    match_id: str
    match_name: str
    market: str
    odds: float
    zone: str
    edge: float
    confidence: float
    decision: str  # BET, SKIP
    stake: float
    result: str = None  # WIN, LOSS, PUSH
    profit_loss: float = 0.0
    scenario: str = None
    components: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BacktestResults:
    """Résultats du backtest"""
    period_start: str
    period_end: str
    total_matches: int
    matches_with_dna: int
    total_picks: int
    wins: int
    losses: int
    pushes: int
    win_rate: float
    roi: float
    pnl: float
    by_zone: Dict[str, Dict] = field(default_factory=dict)
    by_market: Dict[str, Dict] = field(default_factory=dict)
    by_scenario: Dict[str, Dict] = field(default_factory=dict)
    by_team: Dict[str, Dict] = field(default_factory=dict)
    picks: List[Dict] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════════════
# MOMENTUM CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════════════════

class MomentumCalculator:
    """Calcule le momentum L5 d'une équipe"""
    
    def __init__(self, match_history: List[Dict]):
        """match_history: liste de matchs triés par date (plus récent en premier)"""
        self.history = match_history
    
    def get_form_l5(self, team_name: str, before_date: datetime) -> Tuple[str, float, List[str]]:
        """
        Retourne (momentum_status, form_score, results_list)
        form_score = points sur 5 derniers matchs / 15
        """
        # Filtrer les matchs de cette équipe avant la date
        team_matches = []
        for m in self.history:
            if m['match_date'] >= before_date:
                continue
            if m['home_team'] == team_name or m['away_team'] == team_name:
                team_matches.append(m)
            if len(team_matches) >= 5:
                break
        
        if len(team_matches) < 3:
            return "NEUTRAL", 0.5, []
        
        results = []
        points = 0
        
        for m in team_matches[:5]:
            if m['home_team'] == team_name:
                if m['home_goals'] > m['away_goals']:
                    results.append('W')
                    points += 3
                elif m['home_goals'] == m['away_goals']:
                    results.append('D')
                    points += 1
                else:
                    results.append('L')
            else:
                if m['away_goals'] > m['home_goals']:
                    results.append('W')
                    points += 3
                elif m['away_goals'] == m['home_goals']:
                    results.append('D')
                    points += 1
                else:
                    results.append('L')
        
        form_score = points / (len(team_matches[:5]) * 3)
        
        # Déterminer le status
        wins_streak = 0
        losses_streak = 0
        for r in results:
            if r == 'W':
                wins_streak += 1
                losses_streak = 0
            elif r == 'L':
                losses_streak += 1
                wins_streak = 0
            else:
                wins_streak = 0
                losses_streak = 0
            
            if wins_streak >= 4:
                return "BLAZING", form_score, results
            if wins_streak >= 3:
                return "HOT", form_score, results
            if losses_streak >= 4:
                return "FREEZING", form_score, results
            if losses_streak >= 3:
                return "COLD", form_score, results
        
        if form_score >= 0.7:
            return "HOT", form_score, results
        elif form_score <= 0.3:
            return "COLD", form_score, results
        
        return "NEUTRAL", form_score, results


# ═══════════════════════════════════════════════════════════════════════════════════════
# SCENARIO DETECTOR (20 Scénarios)
# ═══════════════════════════════════════════════════════════════════════════════════════

class ScenarioDetector:
    """Détecte les 20 scénarios Quantum"""
    
    SCENARIOS = {
        "TOTAL_CHAOS": {"markets": ["over_35", "btts_yes"], "min_odds": 1.70},
        "SNIPER_DUEL": {"markets": ["over_25", "btts_yes"], "min_odds": 1.60},
        "LATE_PUNISHMENT": {"markets": ["over_25", "btts_yes"], "min_odds": 1.70},
        "COLD_SHOWER": {"markets": ["dc_x2", "dnb_away"], "min_odds": 1.50},
        "FORTRESS": {"markets": ["dc_1x", "home"], "min_odds": 1.30},
        "GOAL_FEST": {"markets": ["over_35", "btts_yes"], "min_odds": 1.80},
        "STALEMATE": {"markets": ["under_25", "btts_no"], "min_odds": 1.70},
        "MOMENTUM_CLASH": {"markets": ["over_25", "btts_yes"], "min_odds": 1.65},
        "DESPERATION": {"markets": ["btts_yes", "over_25"], "min_odds": 1.60},
        "TITLE_RACE": {"markets": ["under_25", "draw"], "min_odds": 1.80},
        "DIESEL_DOMINANCE": {"markets": ["over_25", "btts_yes"], "min_odds": 1.65},
        "KILLER_MODE": {"markets": ["dc_1x", "home"], "min_odds": 1.40},
        "VOLATILE_CHAOS": {"markets": ["btts_yes", "over_25"], "min_odds": 1.70},
        "CONSERVATIVE_LOCK": {"markets": ["under_25", "btts_no"], "min_odds": 1.80},
        "UNDERDOG_VALUE": {"markets": ["dc_x2", "dnb_away"], "min_odds": 1.60},
        "REVENGE_MATCH": {"markets": ["btts_yes", "over_25"], "min_odds": 1.70},
        "CLEAN_SHEET": {"markets": ["btts_no", "under_25"], "min_odds": 1.80},
        "FIRST_BLOOD": {"markets": ["over_15", "btts_yes"], "min_odds": 1.40},
        "GRIND_IT_OUT": {"markets": ["under_25", "draw"], "min_odds": 2.00},
        "EXPLOSIVE_COMBO": {"markets": ["over_25", "btts_yes"], "min_odds": 1.60}
    }
    
    @classmethod
    def detect(cls, ctx: MatchContext) -> Optional[str]:
        """Détecte le scénario basé sur le contexte du match"""
        home = ctx.home_dna
        away = ctx.away_dna
        
        if not home or not away:
            return None
        
        # 1. TOTAL_CHAOS: both offensive, high chaos potential
        if (home.style == "offensive" and away.style == "offensive" and 
            ctx.friction_score > 70):
            return "TOTAL_CHAOS"
        
        # 2. SNIPER_DUEL: both high killer instinct
        if home.killer_instinct > 1.2 and away.killer_instinct > 1.2:
            return "SNIPER_DUEL"
        
        # 3. LATE_PUNISHMENT: home diesel vs away fragile
        if home.diesel_factor > 1.3 and away.psyche == "FRAGILE":
            return "LATE_PUNISHMENT"
        
        # 4. COLD_SHOWER: favorite cold, underdog hot
        if ctx.home_momentum in ["COLD", "FREEZING"] and ctx.away_momentum in ["HOT", "BLAZING"]:
            return "COLD_SHOWER"
        
        # 5. FORTRESS: home dominant
        if home.win_rate > 0.70 and home.tier in ["GOLD", "SILVER"]:
            return "FORTRESS"
        
        # 6. GOAL_FEST: high combined xG
        if (home.xg_for + away.xg_for) > 3.2:
            return "GOAL_FEST"
        
        # 7. STALEMATE: both defensive
        if home.style in ["defensive", "balanced_def"] and away.style in ["defensive", "balanced_def"]:
            return "STALEMATE"
        
        # 8. MOMENTUM_CLASH: both on fire
        if ctx.home_momentum in ["HOT", "BLAZING"] and ctx.away_momentum in ["HOT", "BLAZING"]:
            return "MOMENTUM_CLASH"
        
        # 9. DIESEL_DOMINANCE: diesel factor high
        if home.diesel_factor > 1.25 or away.diesel_factor > 1.25:
            return "DIESEL_DOMINANCE"
        
        # 10. KILLER_MODE: one high KI vs low
        if (home.killer_instinct > 1.4 and away.killer_instinct < 0.8):
            return "KILLER_MODE"
        
        # 11. VOLATILE_CHAOS: both volatile psyche
        if home.psyche == "VOLATILE" and away.psyche == "VOLATILE":
            return "VOLATILE_CHAOS"
        
        # 12. CONSERVATIVE_LOCK: both conservative
        if home.psyche == "CONSERVATIVE" and away.psyche == "CONSERVATIVE":
            return "CONSERVATIVE_LOCK"
        
        # 13. CLEAN_SHEET: strong defense vs weak attack
        if home.xg_against < 0.9 and away.xg_for < 1.0:
            return "CLEAN_SHEET"
        
        # 14. FIRST_BLOOD: both attack-minded
        if home.style in ["offensive", "balanced_off"] and away.style in ["offensive", "balanced_off"]:
            return "FIRST_BLOOD"
        
        # Default based on friction
        if ctx.friction_score > 60:
            return "EXPLOSIVE_COMBO"
        
        return None


# ═══════════════════════════════════════════════════════════════════════════════════════
# BTTS FUSION CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════════════════

class BTTSFusion:
    """Calcule la probabilité BTTS fusionnée de 3 sources"""
    
    def __init__(self, tactical_matrix: Dict, team_xg: Dict, h2h_data: Dict):
        self.tactical = tactical_matrix  # {(home_style, away_style): btts_prob}
        self.team_xg = team_xg           # {team_name: btts_rate}
        self.h2h = h2h_data              # {(home, away): btts_rate}
    
    def calculate(self, home_team: str, away_team: str, 
                  home_style: str, away_style: str) -> Tuple[float, str, int]:
        """
        Retourne (btts_probability, confidence_level, num_sources)
        """
        sources = []
        
        # 1. Tactical matrix
        key = (home_style, away_style)
        if key in self.tactical:
            sources.append(("tactical", self.tactical[key], BTTS_WEIGHTS["tactical"]))
        
        # 2. Team xG tendencies (average of both teams)
        home_btts = self.team_xg.get(home_team, {}).get("btts_rate", 0.5)
        away_btts = self.team_xg.get(away_team, {}).get("btts_rate", 0.5)
        if home_btts > 0 and away_btts > 0:
            avg_btts = (home_btts + away_btts) / 2
            sources.append(("team_xg", avg_btts, BTTS_WEIGHTS["team_xg"]))
        
        # 3. H2H
        h2h_key = (home_team, away_team)
        if h2h_key in self.h2h:
            sources.append(("h2h", self.h2h[h2h_key], BTTS_WEIGHTS["h2h"]))
        
        if not sources:
            return 0.50, "LOW", 0
        
        # Weighted average
        total_weight = sum(s[2] for s in sources)
        btts_prob = sum(s[1] * s[2] for s in sources) / total_weight
        
        # Confidence
        if len(sources) >= 3:
            confidence = "HIGH"
        elif len(sources) == 2:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
        
        return btts_prob, confidence, len(sources)


# ═══════════════════════════════════════════════════════════════════════════════════════
# RULE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════════════

class RuleEngine:
    """Moteur de décision hybride"""
    
    @staticmethod
    def get_odds_zone(odds: float) -> Tuple[str, Dict]:
        """Retourne la zone et ses paramètres"""
        for zone_name, params in ODDS_ZONES.items():
            if params["min"] <= odds < params["max"]:
                return zone_name, params
        return "SPECULATIVE", ODDS_ZONES["SPECULATIVE"]
    
    @staticmethod
    def calculate_effective_weight(team: TeamDNA, momentum: str) -> float:
        """DNA × Momentum dynamique"""
        # Base weight from ROI (not tier!)
        roi_weight = max(0.3, min(1.5, 0.5 + team.roi / 100))
        momentum_factor = MOMENTUM_FACTORS.get(momentum, 1.0)
        return roi_weight * momentum_factor
    
    @staticmethod
    def should_bet(confidence: float, edge: float, zone_params: Dict, 
                   steam_move: float) -> Tuple[str, float]:
        """
        Décide si on parie
        Retourne (decision, stake_multiplier)
        """
        required_edge = zone_params["edge_required"]
        
        # Haute confiance (≥75%) → On tire même si steam neutre
        if confidence >= 0.75:
            if steam_move < -8:  # Steam TRÈS opposé
                return "BET", 0.9  # Stake réduit de 10%
            return "BET", 1.0
        
        # Confiance moyenne (50-75%)
        elif 0.50 <= confidence < 0.75:
            if steam_move < -5:  # Steam opposé → SKIP
                return "SKIP", 0
            elif steam_move > 3:  # Steam confirme
                if edge >= required_edge:
                    return "BET", 1.0
            else:  # Steam neutre
                if edge >= required_edge * 1.5:  # On demande plus d'edge
                    return "BET", 0.8
            return "SKIP", 0
        
        # Faible confiance → Skip
        return "SKIP", 0
    
    @staticmethod
    def evaluate_result(market: str, home_goals: int, away_goals: int) -> str:
        """Évalue si le pari est gagnant"""
        total_goals = home_goals + away_goals
        btts = home_goals > 0 and away_goals > 0
        
        results = {
            "over_15": "WIN" if total_goals > 1 else "LOSS",
            "over_25": "WIN" if total_goals > 2 else "LOSS",
            "over_35": "WIN" if total_goals > 3 else "LOSS",
            "under_15": "WIN" if total_goals < 2 else "LOSS",
            "under_25": "WIN" if total_goals < 3 else "LOSS",
            "under_35": "WIN" if total_goals < 4 else "LOSS",
            "btts_yes": "WIN" if btts else "LOSS",
            "btts_no": "WIN" if not btts else "LOSS",
            "home": "WIN" if home_goals > away_goals else "LOSS",
            "away": "WIN" if away_goals > home_goals else "LOSS",
            "draw": "WIN" if home_goals == away_goals else "LOSS",
            "dc_1x": "WIN" if home_goals >= away_goals else "LOSS",
            "dc_x2": "WIN" if away_goals >= home_goals else "LOSS",
            "dc_12": "WIN" if home_goals != away_goals else "LOSS",
            "dnb_home": "WIN" if home_goals > away_goals else ("PUSH" if home_goals == away_goals else "LOSS"),
            "dnb_away": "WIN" if away_goals > home_goals else ("PUSH" if home_goals == away_goals else "LOSS"),
        }
        
        return results.get(market, "UNKNOWN")


# ═══════════════════════════════════════════════════════════════════════════════════════
# BACKTEST ENGINE
# ═══════════════════════════════════════════════════════════════════════════════════════

class QuantumBacktestEngine:
    """Moteur principal du backtest"""
    
    def __init__(self):
        self.pool = None
        self.team_profiles: Dict[str, TeamDNA] = {}
        self.tactical_matrix: Dict = {}
        self.team_xg_tendencies: Dict = {}
        self.h2h_data: Dict = {}
        self.match_history: List[Dict] = []
        self.momentum_calc: MomentumCalculator = None
        self.btts_fusion: BTTSFusion = None
        self.decisions: List[BetDecision] = []
    
    async def connect(self):
        """Connexion à la base de données"""
        self.pool = await asyncpg.create_pool(**DB_CONFIG, min_size=2, max_size=5)
        print("✅ Connexion PostgreSQL établie")
    
    async def disconnect(self):
        """Déconnexion"""
        if self.pool:
            await self.pool.close()
            print("🔌 Connexion fermée")
    
    async def load_data(self, start_date: str, end_date: str):
        """Charge toutes les données nécessaires"""
        async with self.pool.acquire() as conn:
            # 1. Team profiles + best strategy (depuis la vue)
            print("📊 Chargement quantum.v_team_best_strategy...")
            rows = await conn.fetch("""
                SELECT 
                    v.team_name, 
                    v.tier, 
                    v.current_style,
                    v.team_pnl,
                    v.team_wr as win_rate,
                    v.best_strategy,
                    v.strategy_pnl,
                    v.strategy_wr,
                    p.quantum_dna->'psyche_dna'->>'profile' as psyche,
                    (p.quantum_dna->'psyche_dna'->>'killer_instinct')::float as killer_instinct,
                    (p.quantum_dna->'psyche_dna'->>'panic_factor')::float as panic_factor,
                    p.quantum_dna->'luck_dna'->>'rating' as luck_rating,
                    p.roi
                FROM quantum.v_team_best_strategy v
                JOIN quantum.team_profiles p ON v.team_name = p.team_name
            """)
            for r in rows:
                self.team_profiles[r['team_name']] = TeamDNA(
                    name=r['team_name'],
                    tier=r['tier'] or "EXPERIMENTAL",
                    best_strategy=r['best_strategy'] or "DEFAULT",
                    roi=float(r['roi'] or 0),
                    win_rate=float(r['win_rate'] or 0) / 100,  # Convertir % en décimal
                    psyche=r['psyche'] or "BALANCED",
                    killer_instinct=float(r['killer_instinct'] or 1.0),
                    diesel_factor=1.0 / float(r['panic_factor'] or 1.0) if r['panic_factor'] else 1.0,  # Inverse du panic
                    style=r['current_style'] or "balanced",
                    xg_for=1.2,  # Sera enrichi depuis team_xg_tendencies
                    xg_against=1.2
                )
            print(f"   → {len(self.team_profiles)} équipes chargées")
            
            # 2. Tactical matrix
            print("📊 Chargement tactical_matrix...")
            rows = await conn.fetch("""
                SELECT style_a, style_b, btts_probability, over_25_probability
                FROM tactical_matrix
            """)
            for r in rows:
                key = (r['style_a'], r['style_b'])
                self.tactical_matrix[key] = float(r['btts_probability'] or 0.5)
            print(f"   → {len(self.tactical_matrix)} combinaisons chargées")
            
            # 3. Team xG tendencies
            print("📊 Chargement team_xg_tendencies...")
            rows = await conn.fetch("""
                SELECT team_name, btts_xg_rate, over25_xg_rate, avg_xg_for, avg_xg_against
                FROM team_xg_tendencies
            """)
            for r in rows:
                self.team_xg_tendencies[r['team_name']] = {
                    "btts_rate": float(r['btts_xg_rate'] or 0.5),
                    "over25_rate": float(r['over25_xg_rate'] or 0.5),
                    "xg_for": float(r['avg_xg_for'] or 1.2),
                    "xg_against": float(r['avg_xg_against'] or 1.2)
                }
                # Enrichir le DNA avec xG si équipe existe
                if r['team_name'] in self.team_profiles:
                    self.team_profiles[r['team_name']].xg_for = float(r['avg_xg_for'] or 1.2)
                    self.team_profiles[r['team_name']].xg_against = float(r['avg_xg_against'] or 1.2)
                    self.team_profiles[r['team_name']].btts_rate = float(r['btts_xg_rate'] or 0.5)
                    self.team_profiles[r['team_name']].over25_rate = float(r['over25_xg_rate'] or 0.5)
            print(f"   → {len(self.team_xg_tendencies)} équipes xG chargées")
            
            # 4. Match history (pour calcul momentum)
            print("📊 Chargement historique matchs...")
            rows = await conn.fetch("""
                SELECT match_id, match_date, home_team, away_team, 
                       home_goals, away_goals, home_xg, away_xg, league
                FROM match_xg_stats
                WHERE match_date >= $1 AND match_date <= $2
                ORDER BY match_date DESC
            """, datetime.strptime(start_date, "%Y-%m-%d"), 
                datetime.strptime(end_date, "%Y-%m-%d"))
            
            self.match_history = [dict(r) for r in rows]
            print(f"   → {len(self.match_history)} matchs chargés")
            
            # 5. H2H data (calcul depuis match_xg_stats)
            print("📊 Calcul données H2H...")
            h2h_rows = await conn.fetch("""
                SELECT home_team, away_team,
                       AVG(CASE WHEN home_goals > 0 AND away_goals > 0 THEN 1.0 ELSE 0.0 END) as btts_rate,
                       COUNT(*) as matches
                FROM match_xg_stats
                GROUP BY home_team, away_team
                HAVING COUNT(*) >= 2
            """)
            for r in h2h_rows:
                self.h2h_data[(r['home_team'], r['away_team'])] = float(r['btts_rate'])
            print(f"   → {len(self.h2h_data)} confrontations H2H")
        
        # Initialiser les calculateurs
        self.momentum_calc = MomentumCalculator(self.match_history)
        self.btts_fusion = BTTSFusion(self.tactical_matrix, self.team_xg_tendencies, self.h2h_data)
    
    def select_best_market(self, ctx: MatchContext, scenario: str) -> Tuple[str, float, float]:
        """
        Sélectionne le meilleur marché pour ce match
        Retourne (market, odds, implied_prob)
        """
        # 1. D'abord selon le scénario si détecté
        if scenario and scenario in ScenarioDetector.SCENARIOS:
            preferred_markets = ScenarioDetector.SCENARIOS[scenario]["markets"]
        # 2. Sinon selon la stratégie de l'équipe home
        elif ctx.home_dna and ctx.home_dna.best_strategy in STRATEGY_TO_MARKETS:
            preferred_markets = STRATEGY_TO_MARKETS[ctx.home_dna.best_strategy]
        else:
            preferred_markets = STRATEGY_TO_MARKETS["DEFAULT"]
        
        # Chercher le premier marché disponible avec cotes dans la zone cible
        for market in preferred_markets:
            if market in ctx.odds and ctx.odds[market] > 1.30:
                odds = ctx.odds[market]
                implied_prob = 1 / odds
                return market, odds, implied_prob
        
        # Fallback sur over_25 ou dc_12
        for fallback in ["over_25", "dc_12", "btts_yes"]:
            if fallback in ctx.odds and ctx.odds[fallback] > 1.30:
                return fallback, ctx.odds[fallback], 1 / ctx.odds[fallback]
        
        return None, 0, 0
    
    def calculate_model_probability(self, ctx: MatchContext, market: str) -> float:
        """Calcule la probabilité selon notre modèle pour un marché donné"""
        home = ctx.home_dna
        away = ctx.away_dna
        
        if not home or not away:
            return 0.5
        
        # BTTS markets
        if market in ["btts_yes", "btts_no"]:
            btts_prob = ctx.btts_prob
            if market == "btts_no":
                return 1 - btts_prob
            return btts_prob
        
        # Over/Under markets
        if market.startswith("over_"):
            threshold = float(market.split("_")[1]) / 10
            # Simple model: combined xG vs threshold
            combined_xg = home.xg_for + away.xg_for
            if threshold == 2.5:
                return ctx.over25_prob
            elif threshold == 1.5:
                return min(0.85, ctx.over25_prob + 0.15)
            elif threshold == 3.5:
                return max(0.25, ctx.over25_prob - 0.20)
        
        if market.startswith("under_"):
            threshold = float(market.split("_")[1]) / 10
            if threshold == 2.5:
                return 1 - ctx.over25_prob
            elif threshold == 1.5:
                return 1 - min(0.85, ctx.over25_prob + 0.15)
            elif threshold == 3.5:
                return 1 - max(0.25, ctx.over25_prob - 0.20)
        
        # 1X2 and DC markets
        # Simplified model based on tier and momentum
        home_strength = 0.45  # Base home advantage
        
        # Adjust for DNA
        if home.tier == "GOLD":
            home_strength += 0.10
        elif home.tier == "SILVER":
            home_strength += 0.05
        
        # Adjust for momentum
        home_strength *= MOMENTUM_FACTORS.get(ctx.home_momentum, 1.0)
        away_strength = (1 - home_strength - 0.25) * MOMENTUM_FACTORS.get(ctx.away_momentum, 1.0)
        draw_prob = 0.25
        
        # Normalize
        total = home_strength + away_strength + draw_prob
        home_prob = home_strength / total
        away_prob = away_strength / total
        draw_prob = draw_prob / total
        
        if market == "home":
            return home_prob
        elif market == "away":
            return away_prob
        elif market == "draw":
            return draw_prob
        elif market == "dc_1x":
            return home_prob + draw_prob
        elif market == "dc_x2":
            return away_prob + draw_prob
        elif market == "dc_12":
            return home_prob + away_prob
        elif market == "dnb_home":
            return home_prob / (home_prob + away_prob)
        elif market == "dnb_away":
            return away_prob / (home_prob + away_prob)
        
        return 0.5
    
    async def run_backtest(self, start_date: str, end_date: str) -> BacktestResults:
        """Exécute le backtest complet"""
        print(f"\n{'='*80}")
        print(f"🚀 QUANTUM BACKTEST V2.0 - {start_date} à {end_date}")
        print(f"{'='*80}\n")
        
        # Load data
        await self.load_data(start_date, end_date)
        
        # Stats
        total_matches = len(self.match_history)
        matches_with_dna = 0
        decisions = []
        
        # Process each match
        print(f"\n📊 Analyse de {total_matches} matchs...\n")
        
        for i, match in enumerate(self.match_history):
            home_team = match['home_team']
            away_team = match['away_team']
            
            # Get DNA for both teams
            home_dna = self.team_profiles.get(home_team)
            away_dna = self.team_profiles.get(away_team)
            
            # Skip if no DNA for at least one team
            if not home_dna and not away_dna:
                continue
            
            matches_with_dna += 1
            
            # Build context
            ctx = MatchContext(
                match_id=match['match_id'],
                match_date=match['match_date'],
                home_team=home_team,
                away_team=away_team,
                home_goals=match['home_goals'],
                away_goals=match['away_goals'],
                home_xg=float(match['home_xg'] or 0),
                away_xg=float(match['away_xg'] or 0),
                league=match['league'] or "",
                home_dna=home_dna,
                away_dna=away_dna
            )
            
            # Calculate momentum
            ctx.home_momentum, _, _ = self.momentum_calc.get_form_l5(home_team, match['match_date'])
            ctx.away_momentum, _, _ = self.momentum_calc.get_form_l5(away_team, match['match_date'])
            
            # Calculate friction
            if home_dna and away_dna:
                # Simple friction based on style mismatch and killer instinct
                style_clash = 1 if home_dna.style != away_dna.style else 0.8
                ki_sum = home_dna.killer_instinct + away_dna.killer_instinct
                ctx.friction_score = 40 + (ki_sum * 10) + (style_clash * 10)
            
            # Calculate BTTS probability
            home_style = home_dna.style if home_dna else "balanced"
            away_style = away_dna.style if away_dna else "balanced"
            ctx.btts_prob, _, _ = self.btts_fusion.calculate(home_team, away_team, home_style, away_style)
            
            # Calculate Over 2.5 probability
            combined_xg = (home_dna.xg_for if home_dna else 1.2) + (away_dna.xg_for if away_dna else 1.2)
            ctx.over25_prob = min(0.85, combined_xg / 4.0)  # Normalize xG to probability
            
            # Simulate odds (from match data or typical values)
            ctx.odds = {
                "over_25": 1.85,
                "under_25": 2.00,
                "over_15": 1.35,
                "over_35": 2.80,
                "btts_yes": 1.75,
                "btts_no": 2.05,
                "dc_1x": 1.40,
                "dc_x2": 1.55,
                "dc_12": 1.30,
                "home": 2.20,
                "away": 3.00,
                "draw": 3.30
            }
            
            # Detect scenario
            ctx.scenario = ScenarioDetector.detect(ctx)
            
            # Select best market
            market, odds, implied_prob = self.select_best_market(ctx, ctx.scenario)
            
            if not market:
                continue
            
            # Calculate model probability
            model_prob = self.calculate_model_probability(ctx, market)
            edge = model_prob - implied_prob
            
            # Get zone
            zone, zone_params = RuleEngine.get_odds_zone(odds)
            
            # Calculate confidence
            home_weight = RuleEngine.calculate_effective_weight(home_dna, ctx.home_momentum) if home_dna else 0.5
            away_weight = RuleEngine.calculate_effective_weight(away_dna, ctx.away_momentum) if away_dna else 0.5
            
            # Confidence based on DNA weights, scenario match, and edge
            base_confidence = (home_weight + away_weight) / 2
            scenario_bonus = 0.10 if ctx.scenario else 0
            edge_bonus = min(0.15, edge * 2) if edge > 0 else 0
            confidence = min(0.95, base_confidence + scenario_bonus + edge_bonus)
            
            # Steam move (simulated - would come from odds_history in production)
            ctx.steam_move = 0  # Neutral for backtest
            
            # Decision
            decision, stake_mult = RuleEngine.should_bet(confidence, edge, zone_params, ctx.steam_move)
            
            if decision == "BET":
                # Evaluate result
                result = RuleEngine.evaluate_result(market, match['home_goals'], match['away_goals'])
                
                # Calculate P&L
                stake = 1.0 * stake_mult
                if result == "WIN":
                    pnl = (odds - 1) * stake
                elif result == "LOSS":
                    pnl = -stake
                else:  # PUSH
                    pnl = 0
                
                bet = BetDecision(
                    match_id=match['match_id'],
                    match_name=f"{home_team} vs {away_team}",
                    market=market,
                    odds=odds,
                    zone=zone,
                    edge=edge,
                    confidence=confidence,
                    decision=decision,
                    stake=stake,
                    result=result,
                    profit_loss=pnl,
                    scenario=ctx.scenario,
                    components={
                        "home_momentum": ctx.home_momentum,
                        "away_momentum": ctx.away_momentum,
                        "btts_prob": ctx.btts_prob,
                        "over25_prob": ctx.over25_prob,
                        "friction": ctx.friction_score,
                        "model_prob": model_prob,
                        "implied_prob": implied_prob
                    }
                )
                decisions.append(bet)
        
        self.decisions = decisions
        
        # Calculate results
        return self._calculate_results(start_date, end_date, total_matches, matches_with_dna)
    
    def _calculate_results(self, start_date: str, end_date: str, 
                           total_matches: int, matches_with_dna: int) -> BacktestResults:
        """Calcule les statistiques finales"""
        decisions = self.decisions
        
        if not decisions:
            return BacktestResults(
                period_start=start_date,
                period_end=end_date,
                total_matches=total_matches,
                matches_with_dna=matches_with_dna,
                total_picks=0, wins=0, losses=0, pushes=0,
                win_rate=0, roi=0, pnl=0
            )
        
        wins = sum(1 for d in decisions if d.result == "WIN")
        losses = sum(1 for d in decisions if d.result == "LOSS")
        pushes = sum(1 for d in decisions if d.result == "PUSH")
        total_picks = len(decisions)
        
        total_stake = sum(d.stake for d in decisions)
        total_pnl = sum(d.profit_loss for d in decisions)
        
        win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0
        roi = (total_pnl / total_stake * 100) if total_stake > 0 else 0
        
        # By zone
        by_zone = defaultdict(lambda: {"picks": 0, "wins": 0, "pnl": 0})
        for d in decisions:
            by_zone[d.zone]["picks"] += 1
            if d.result == "WIN":
                by_zone[d.zone]["wins"] += 1
            by_zone[d.zone]["pnl"] += d.profit_loss
        
        for zone in by_zone:
            by_zone[zone]["wr"] = by_zone[zone]["wins"] / by_zone[zone]["picks"] if by_zone[zone]["picks"] > 0 else 0
        
        # By market
        by_market = defaultdict(lambda: {"picks": 0, "wins": 0, "pnl": 0})
        for d in decisions:
            by_market[d.market]["picks"] += 1
            if d.result == "WIN":
                by_market[d.market]["wins"] += 1
            by_market[d.market]["pnl"] += d.profit_loss
        
        for market in by_market:
            by_market[market]["wr"] = by_market[market]["wins"] / by_market[market]["picks"] if by_market[market]["picks"] > 0 else 0
        
        # By scenario
        by_scenario = defaultdict(lambda: {"picks": 0, "wins": 0, "pnl": 0})
        for d in decisions:
            scenario = d.scenario or "NO_SCENARIO"
            by_scenario[scenario]["picks"] += 1
            if d.result == "WIN":
                by_scenario[scenario]["wins"] += 1
            by_scenario[scenario]["pnl"] += d.profit_loss
        
        for sc in by_scenario:
            by_scenario[sc]["wr"] = by_scenario[sc]["wins"] / by_scenario[sc]["picks"] if by_scenario[sc]["picks"] > 0 else 0
        
        # By team (équipe impliquée)
        by_team = defaultdict(lambda: {"picks": 0, "wins": 0, "pnl": 0})
        for d in decisions:
            teams = d.match_name.split(" vs ")
            for team in teams:
                team = team.strip()
                by_team[team]["picks"] += 1
                if d.result == "WIN":
                    by_team[team]["wins"] += 1
                by_team[team]["pnl"] += d.profit_loss / 2  # Split between teams
        
        for team in by_team:
            by_team[team]["wr"] = by_team[team]["wins"] / by_team[team]["picks"] if by_team[team]["picks"] > 0 else 0
        
        return BacktestResults(
            period_start=start_date,
            period_end=end_date,
            total_matches=total_matches,
            matches_with_dna=matches_with_dna,
            total_picks=total_picks,
            wins=wins,
            losses=losses,
            pushes=pushes,
            win_rate=win_rate,
            roi=roi,
            pnl=total_pnl,
            by_zone=dict(by_zone),
            by_market=dict(by_market),
            by_scenario=dict(by_scenario),
            by_team=dict(by_team),
            picks=[asdict(d) for d in decisions]
        )
    
    def print_results(self, results: BacktestResults):
        """Affiche les résultats en console"""
        print("\n" + "="*80)
        print("📊 QUANTUM BACKTEST V2.0 - RÉSULTATS")
        print("="*80)
        
        print(f"""
┌──────────────────────────────────────────────────────────────────┐
│ Période: {results.period_start} → {results.period_end}
│ Total matchs: {results.total_matches} | Avec DNA: {results.matches_with_dna}
├──────────────────────────────────────────────────────────────────┤
│ 📈 PERFORMANCE GLOBALE
│ ──────────────────────────────────────────────────────────────────
│ Total picks: {results.total_picks}
│ Wins: {results.wins} | Losses: {results.losses} | Push: {results.pushes}
│ Win Rate: {results.win_rate*100:.1f}%
│ ROI: {results.roi:+.1f}%
│ P&L: {results.pnl:+.2f}u
└──────────────────────────────────────────────────────────────────┘
""")
        
        # Par zone
        print("┌──────────────────────────────────────────────────────────────────┐")
        print("│ 📊 PAR ZONE DE COTES")
        print("├──────────────────────────────────────────────────────────────────┤")
        for zone, stats in sorted(results.by_zone.items()):
            wr_target = ODDS_ZONES.get(zone, {}).get("wr_target", 0.50) * 100
            status = "✅" if stats["wr"] >= wr_target/100 else "❌"
            print(f"│ {status} {zone:15} | {stats['picks']:3} picks | {stats['wr']*100:5.1f}% WR | {stats['pnl']:+7.2f}u")
        print("└──────────────────────────────────────────────────────────────────┘")
        
        # Par marché (top 10)
        print("\n┌──────────────────────────────────────────────────────────────────┐")
        print("│ 📊 PAR MARCHÉ (Top 10)")
        print("├──────────────────────────────────────────────────────────────────┤")
        sorted_markets = sorted(results.by_market.items(), key=lambda x: x[1]["pnl"], reverse=True)[:10]
        for market, stats in sorted_markets:
            status = "✅" if stats["wr"] >= 0.55 else "❌"
            print(f"│ {status} {market:15} | {stats['picks']:3} picks | {stats['wr']*100:5.1f}% WR | {stats['pnl']:+7.2f}u")
        print("└──────────────────────────────────────────────────────────────────┘")
        
        # Par scénario (top 10)
        print("\n┌──────────────────────────────────────────────────────────────────┐")
        print("│ 📊 PAR SCÉNARIO (Top 10)")
        print("├──────────────────────────────────────────────────────────────────┤")
        sorted_scenarios = sorted(results.by_scenario.items(), key=lambda x: x[1]["pnl"], reverse=True)[:10]
        for scenario, stats in sorted_scenarios:
            status = "✅" if stats["wr"] >= 0.55 else "⚠️"
            print(f"│ {status} {scenario:20} | {stats['picks']:3} picks | {stats['wr']*100:5.1f}% WR | {stats['pnl']:+7.2f}u")
        print("└──────────────────────────────────────────────────────────────────┘")
        
        # Top équipes
        print("\n┌──────────────────────────────────────────────────────────────────┐")
        print("│ 🏆 TOP 10 ÉQUIPES (P&L)")
        print("├──────────────────────────────────────────────────────────────────┤")
        sorted_teams = sorted(results.by_team.items(), key=lambda x: x[1]["pnl"], reverse=True)[:10]
        for team, stats in sorted_teams:
            status = "🏆" if stats["wr"] >= 0.65 else "✅" if stats["wr"] >= 0.55 else "⚠️"
            print(f"│ {status} {team:25} | {stats['picks']:3} picks | {stats['wr']*100:5.1f}% WR | {stats['pnl']:+7.2f}u")
        print("└──────────────────────────────────────────────────────────────────┘")
    
    def save_results(self, results: BacktestResults, filename: str):
        """Sauvegarde les résultats en JSON"""
        output = {
            "metadata": {
                "period_start": results.period_start,
                "period_end": results.period_end,
                "total_matches": results.total_matches,
                "matches_with_dna": results.matches_with_dna,
                "generated_at": datetime.now().isoformat()
            },
            "summary": {
                "total_picks": results.total_picks,
                "wins": results.wins,
                "losses": results.losses,
                "pushes": results.pushes,
                "win_rate": round(results.win_rate, 4),
                "roi": round(results.roi, 2),
                "pnl": round(results.pnl, 2)
            },
            "by_zone": results.by_zone,
            "by_market": results.by_market,
            "by_scenario": results.by_scenario,
            "by_team": {k: v for k, v in sorted(results.by_team.items(), key=lambda x: x[1]["pnl"], reverse=True)[:50]},
            "picks": results.picks
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n✅ Résultats sauvegardés: {filename}")


# ═══════════════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════════════

async def main():
    parser = argparse.ArgumentParser(description="Quantum Backtest V2.0")
    parser.add_argument("--start", type=str, default="2025-09-01", help="Date de début (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, default="2025-12-06", help="Date de fin (YYYY-MM-DD)")
    parser.add_argument("--output", type=str, default="quantum_backtest_v2_results.json", help="Fichier de sortie")
    
    args = parser.parse_args()
    
    engine = QuantumBacktestEngine()
    
    try:
        await engine.connect()
        results = await engine.run_backtest(args.start, args.end)
        engine.print_results(results)
        engine.save_results(results, args.output)
    finally:
        await engine.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
