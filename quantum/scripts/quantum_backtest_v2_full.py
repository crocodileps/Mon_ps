#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║          QUANTUM BACKTESTER QUANT 2.0 - VERSION COMPLÈTE                             ║
║                                                                                       ║
║  ARCHITECTURE HYBRIDE:                                                                ║
║  • 20 Scénarios Quantum (Rule Engine)                                                 ║
║  • Momentum L5 (Form, Streak, Acceleration)                                           ║
║  • Friction Matrix (Kinetic, Temporal, Psyche)                                        ║
║  • Marchés Spécifiques (Goals 2H, 75-90, 1H Over, etc.)                              ║
║                                                                                       ║
║  COMPARAISON avec stratégies existantes (CONVERGENCE_OVER_MC, etc.)                  ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

import psycopg2
import psycopg2.extras
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum
import json
import math

# ═══════════════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════════════

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

# Cotes moyennes par marché
AVG_ODDS = {
    'over_25': 1.85,
    'under_25': 2.00,
    'over_35': 2.50,
    'under_35': 1.55,
    'btts_yes': 1.75,
    'btts_no': 2.10,
    'home_win': 1.80,
    'away_win': 3.20,
    'draw': 3.50,
    # Marchés spécifiques
    'first_half_over_15': 2.20,
    'second_half_over_15': 1.70,
    'goal_75_90': 2.30,
    'team_goals_2h_over_05': 1.50,
    'home_over_05': 1.30,
    'away_over_05': 1.55,
    'home_over_15': 2.10,
    'away_over_15': 3.00,
    'corners_over_105': 1.90,
}


# ═══════════════════════════════════════════════════════════════════════════════════════
# 20 SCÉNARIOS QUANTUM
# ═══════════════════════════════════════════════════════════════════════════════════════

class ScenarioID(Enum):
    # Groupe A: Tactiques
    TOTAL_CHAOS = "TOTAL_CHAOS"
    THE_SIEGE = "THE_SIEGE"
    SNIPER_DUEL = "SNIPER_DUEL"
    ATTRITION_WAR = "ATTRITION_WAR"
    GLASS_CANNON = "GLASS_CANNON"
    # Groupe B: Temporels
    LATE_PUNISHMENT = "LATE_PUNISHMENT"
    EXPLOSIVE_START = "EXPLOSIVE_START"
    DIESEL_DUEL = "DIESEL_DUEL"
    CLUTCH_KILLER = "CLUTCH_KILLER"
    # Groupe C: Physiques
    FATIGUE_COLLAPSE = "FATIGUE_COLLAPSE"
    PRESSING_DEATH = "PRESSING_DEATH"
    PACE_EXPLOITATION = "PACE_EXPLOITATION"
    BENCH_WARFARE = "BENCH_WARFARE"
    # Groupe D: Psychologiques
    CONSERVATIVE_WALL = "CONSERVATIVE_WALL"
    KILLER_INSTINCT = "KILLER_INSTINCT"
    COLLAPSE_ALERT = "COLLAPSE_ALERT"
    NOTHING_TO_LOSE = "NOTHING_TO_LOSE"
    # Groupe E: Nemesis
    NEMESIS_TRAP = "NEMESIS_TRAP"
    PREY_HUNT = "PREY_HUNT"
    AERIAL_RAID = "AERIAL_RAID"


@dataclass
class ScenarioResult:
    """Résultat d'un scénario détecté"""
    scenario_id: str
    confidence: float
    primary_market: str
    secondary_market: str = ""
    reasoning: str = ""


SCENARIO_MARKETS = {
    "TOTAL_CHAOS": {"primary": "over_35", "secondary": "btts_yes", "avoid": ["under_25"]},
    "THE_SIEGE": {"primary": "corners_over_105", "secondary": "under_25", "avoid": ["over_35"]},
    "SNIPER_DUEL": {"primary": "btts_yes", "secondary": "over_25", "avoid": ["clean_sheet"]},
    "ATTRITION_WAR": {"primary": "under_25", "secondary": "draw", "avoid": ["over_25"]},
    "GLASS_CANNON": {"primary": "away_over_15", "secondary": "btts_yes", "avoid": ["home_clean_sheet"]},
    "LATE_PUNISHMENT": {"primary": "team_goals_2h_over_05", "secondary": "goal_75_90", "avoid": []},
    "EXPLOSIVE_START": {"primary": "first_half_over_15", "secondary": "goal_0_15", "avoid": []},
    "DIESEL_DUEL": {"primary": "second_half_over_15", "secondary": "over_25", "avoid": ["first_half_over_15"]},
    "CLUTCH_KILLER": {"primary": "goal_75_90", "secondary": "home_win", "avoid": []},
    "FATIGUE_COLLAPSE": {"primary": "team_goals_2h_over_05", "secondary": "second_half_over_15", "avoid": []},
    "PRESSING_DEATH": {"primary": "home_over_15", "secondary": "home_win", "avoid": []},
    "PACE_EXPLOITATION": {"primary": "btts_yes", "secondary": "home_over_05", "avoid": ["under_25"]},
    "BENCH_WARFARE": {"primary": "second_half_over_15", "secondary": "over_25", "avoid": []},
    "CONSERVATIVE_WALL": {"primary": "under_25", "secondary": "home_clean_sheet", "avoid": ["btts_yes"]},
    "KILLER_INSTINCT": {"primary": "team_goals_2h_over_05", "secondary": "home_win", "avoid": []},
    "COLLAPSE_ALERT": {"primary": "over_25", "secondary": "away_win", "avoid": []},
    "NOTHING_TO_LOSE": {"primary": "home_over_05", "secondary": "draw", "avoid": ["away_win"]},
    "NEMESIS_TRAP": {"primary": "away_over_05", "secondary": "draw", "avoid": ["home_win"]},
    "PREY_HUNT": {"primary": "home_over_15", "secondary": "home_win", "avoid": ["away_win"]},
    "AERIAL_RAID": {"primary": "home_over_05", "secondary": "corners_over_105", "avoid": []},
}


# ═══════════════════════════════════════════════════════════════════════════════════════
# MOMENTUM L5
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class MomentumL5:
    """Momentum basé sur les 5 derniers matchs"""
    form_points: int = 0  # 0-15 (W=3, D=1, L=0)
    form_percentage: float = 0.0  # 0-100%
    goal_diff: int = 0
    streak_type: str = "NEUTRAL"  # WIN, DRAW, LOSE, NEUTRAL
    streak_length: int = 0
    acceleration: float = 0.0  # L3 vs L4-L5
    trend: str = "NEUTRAL"  # BLAZING, HOT, WARMING, NEUTRAL, COOLING, COLD, FREEZING
    
    @property
    def score(self) -> float:
        """Score composite 0-100"""
        base = self.form_percentage
        
        # Bonus streak
        if self.streak_type == "WIN":
            base += min(20, self.streak_length * 5)
        elif self.streak_type == "LOSE":
            base -= min(20, self.streak_length * 5)
        
        # Bonus acceleration
        base += self.acceleration * 10
        
        return max(0, min(100, base))
    
    @property
    def stake_multiplier(self) -> float:
        """Multiplicateur de mise basé sur le momentum"""
        if self.trend == "BLAZING":
            return 1.25
        elif self.trend == "HOT":
            return 1.15
        elif self.trend == "WARMING":
            return 1.05
        elif self.trend == "COOLING":
            return 0.90
        elif self.trend == "COLD":
            return 0.80
        elif self.trend == "FREEZING":
            return 0.65
        return 1.0


def calculate_momentum_l5(matches: List[Dict], team_name: str, is_home: bool) -> MomentumL5:
    """
    Calcule le momentum sur les 5 derniers matchs.
    """
    momentum = MomentumL5()
    
    if len(matches) < 5:
        return momentum
    
    # Prendre les 5 derniers matchs (triés par date DESC)
    last_5 = matches[:5]
    
    results = []
    goals_for = 0
    goals_against = 0
    
    for match in last_5:
        team_lower = team_name.lower()
        is_home_match = match['home_team'].lower() == team_lower
        
        hg = match['home_goals']
        ag = match['away_goals']
        
        if is_home_match:
            gf, ga = hg, ag
        else:
            gf, ga = ag, hg
        
        goals_for += gf
        goals_against += ga
        
        if gf > ga:
            results.append('W')
        elif gf < ga:
            results.append('L')
        else:
            results.append('D')
    
    # Form points
    for r in results:
        if r == 'W':
            momentum.form_points += 3
        elif r == 'D':
            momentum.form_points += 1
    
    momentum.form_percentage = (momentum.form_points / 15) * 100
    momentum.goal_diff = goals_for - goals_against
    
    # Streak detection
    if results[0] == results[1] == results[2]:
        momentum.streak_type = results[0]
        momentum.streak_length = 3
        if len(results) > 3 and results[3] == results[0]:
            momentum.streak_length = 4
            if len(results) > 4 and results[4] == results[0]:
                momentum.streak_length = 5
    elif results[0] == results[1]:
        momentum.streak_type = results[0]
        momentum.streak_length = 2
    else:
        momentum.streak_type = "NEUTRAL"
        momentum.streak_length = 0
    
    # Acceleration: L3 vs L4-L5
    l3_points = sum(3 if r == 'W' else 1 if r == 'D' else 0 for r in results[:3])
    l45_points = sum(3 if r == 'W' else 1 if r == 'D' else 0 for r in results[3:5]) if len(results) >= 5 else 0
    
    l3_avg = l3_points / 3
    l45_avg = l45_points / 2 if len(results) >= 5 else l3_avg
    
    momentum.acceleration = l3_avg - l45_avg
    
    # Trend
    if momentum.streak_type == "WIN" and momentum.streak_length >= 4:
        momentum.trend = "BLAZING"
    elif momentum.streak_type == "WIN" and momentum.streak_length >= 3:
        momentum.trend = "HOT"
    elif momentum.form_percentage >= 70:
        momentum.trend = "WARMING"
    elif momentum.form_percentage <= 30:
        momentum.trend = "FREEZING"
    elif momentum.streak_type == "LOSE" and momentum.streak_length >= 3:
        momentum.trend = "COLD"
    elif momentum.form_percentage <= 45:
        momentum.trend = "COOLING"
    else:
        momentum.trend = "NEUTRAL"
    
    return momentum


# ═══════════════════════════════════════════════════════════════════════════════════════
# SCENARIO DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════════════

def detect_scenarios(
    home_dna: Dict,
    away_dna: Dict,
    friction: Dict,
    home_momentum: MomentumL5,
    away_momentum: MomentumL5
) -> List[ScenarioResult]:
    """
    Détecte les scénarios applicables basés sur les DNA, friction et momentum.
    """
    scenarios = []
    
    # Extraire les métriques
    home_xg = home_dna.get('xg_for', 1.5)
    away_xg = away_dna.get('xg_for', 1.5)
    home_xga = home_dna.get('xg_against', 1.5)
    away_xga = away_dna.get('xg_against', 1.5)
    
    home_style = home_dna.get('style', 'balanced')
    away_style = away_dna.get('style', 'balanced')
    
    home_diesel = home_dna.get('diesel_factor', 0.5)
    away_diesel = away_dna.get('diesel_factor', 0.5)
    
    chaos_potential = friction.get('chaos_potential', 50)
    style_clash = friction.get('style_clash', 50)
    
    total_xg = home_xg + away_xg
    total_xga = home_xga + away_xga
    
    # ─────────────────────────────────────────────────────────────────────────────
    # GROUPE A: Scénarios Tactiques
    # ─────────────────────────────────────────────────────────────────────────────
    
    # TOTAL_CHAOS: Les deux attaquent bien et défendent mal
    if total_xg > 3.0 and total_xga > 3.0 and chaos_potential > 65:
        confidence = min(100, 50 + (total_xg - 3.0) * 20 + (chaos_potential - 65))
        scenarios.append(ScenarioResult(
            scenario_id="TOTAL_CHAOS",
            confidence=confidence,
            primary_market="over_35",
            secondary_market="btts_yes",
            reasoning=f"xG combiné {total_xg:.1f}, chaos {chaos_potential}"
        ))
    
    # SNIPER_DUEL: Les deux sont efficaces devant le but
    home_conversion = home_dna.get('conversion_rate', 0.3)
    away_conversion = away_dna.get('conversion_rate', 0.3)
    if home_conversion > 0.28 and away_conversion > 0.28:
        confidence = min(100, 60 + (home_conversion + away_conversion - 0.56) * 100)
        scenarios.append(ScenarioResult(
            scenario_id="SNIPER_DUEL",
            confidence=confidence,
            primary_market="btts_yes",
            secondary_market="over_25",
            reasoning=f"Conversion home {home_conversion:.0%}, away {away_conversion:.0%}"
        ))
    
    # ATTRITION_WAR: Les deux sont défensifs
    if 'defens' in home_style.lower() and 'defens' in away_style.lower():
        confidence = 70
        scenarios.append(ScenarioResult(
            scenario_id="ATTRITION_WAR",
            confidence=confidence,
            primary_market="under_25",
            secondary_market="draw",
            reasoning="Deux équipes défensives"
        ))
    
    # GLASS_CANNON: Home attaque bien mais défend mal
    if home_xg > 1.7 and home_xga > 1.6:
        confidence = min(100, 50 + (home_xg - 1.7) * 30 + (home_xga - 1.6) * 20)
        scenarios.append(ScenarioResult(
            scenario_id="GLASS_CANNON",
            confidence=confidence,
            primary_market="btts_yes",
            secondary_market="away_over_05",
            reasoning=f"Home xG {home_xg:.2f}, xGA {home_xga:.2f}"
        ))
    
    # ─────────────────────────────────────────────────────────────────────────────
    # GROUPE B: Scénarios Temporels
    # ─────────────────────────────────────────────────────────────────────────────
    
    # LATE_PUNISHMENT: Home diesel vs Away qui s'effondre tard
    if home_diesel > 0.65 and away_dna.get('late_collapse_risk', 0) > 0.3:
        confidence = min(100, 50 + (home_diesel - 0.65) * 100 + away_dna.get('late_collapse_risk', 0) * 50)
        scenarios.append(ScenarioResult(
            scenario_id="LATE_PUNISHMENT",
            confidence=confidence,
            primary_market="team_goals_2h_over_05",
            secondary_market="goal_75_90",
            reasoning=f"Home diesel {home_diesel:.0%}"
        ))
    
    # EXPLOSIVE_START: Les deux commencent fort
    home_sprinter = 1 - home_diesel
    away_sprinter = 1 - away_diesel
    if home_sprinter > 0.55 and away_sprinter > 0.55:
        confidence = min(100, 50 + (home_sprinter + away_sprinter - 1.1) * 80)
        scenarios.append(ScenarioResult(
            scenario_id="EXPLOSIVE_START",
            confidence=confidence,
            primary_market="first_half_over_15",
            secondary_market="over_25",
            reasoning=f"Sprinters combinés {home_sprinter + away_sprinter:.0%}"
        ))
    
    # DIESEL_DUEL: Les deux sont des diesels
    if home_diesel > 0.6 and away_diesel > 0.6:
        confidence = min(100, 50 + (home_diesel + away_diesel - 1.2) * 80)
        scenarios.append(ScenarioResult(
            scenario_id="DIESEL_DUEL",
            confidence=confidence,
            primary_market="second_half_over_15",
            secondary_market="over_25",
            reasoning=f"Diesels combinés {home_diesel + away_diesel:.0%}"
        ))
    
    # CLUTCH_KILLER: Home bon en fin de match + Momentum BLAZING/HOT
    if home_dna.get('clutch_factor', 0.5) > 0.7 and home_momentum.trend in ["BLAZING", "HOT"]:
        confidence = min(100, 60 + (home_dna.get('clutch_factor', 0.5) - 0.7) * 100 + 
                        (20 if home_momentum.trend == "BLAZING" else 10))
        scenarios.append(ScenarioResult(
            scenario_id="CLUTCH_KILLER",
            confidence=confidence,
            primary_market="goal_75_90",
            secondary_market="home_win",
            reasoning=f"Clutch {home_dna.get('clutch_factor', 0.5):.0%}, Momentum {home_momentum.trend}"
        ))
    
    # ─────────────────────────────────────────────────────────────────────────────
    # GROUPE D: Scénarios Psychologiques
    # ─────────────────────────────────────────────────────────────────────────────
    
    # KILLER_INSTINCT: Home a l'instinct de tueur + Momentum fort
    killer = home_dna.get('killer_instinct', 0.5)
    if killer > 0.7 and home_momentum.score > 60:
        confidence = min(100, 50 + (killer - 0.7) * 100 + (home_momentum.score - 60))
        scenarios.append(ScenarioResult(
            scenario_id="KILLER_INSTINCT",
            confidence=confidence,
            primary_market="home_over_15",
            secondary_market="home_win",
            reasoning=f"Killer instinct {killer:.0%}, Momentum {home_momentum.score:.0f}"
        ))
    
    # COLLAPSE_ALERT: Away a tendance à s'effondrer
    collapse = away_dna.get('collapse_rate', 0)
    if collapse > 0.25:
        confidence = min(100, 50 + (collapse - 0.25) * 150)
        scenarios.append(ScenarioResult(
            scenario_id="COLLAPSE_ALERT",
            confidence=confidence,
            primary_market="over_25",
            secondary_market="home_win",
            reasoning=f"Away collapse rate {collapse:.0%}"
        ))
    
    # CONSERVATIVE_WALL: Home très défensif
    if 'defens' in home_style.lower() or 'conserv' in home_style.lower():
        if home_xga < 1.2:
            confidence = min(100, 60 + (1.2 - home_xga) * 50)
            scenarios.append(ScenarioResult(
                scenario_id="CONSERVATIVE_WALL",
                confidence=confidence,
                primary_market="under_25",
                secondary_market="btts_no",
                reasoning=f"Home défensif, xGA {home_xga:.2f}"
            ))
    
    return scenarios


# ═══════════════════════════════════════════════════════════════════════════════════════
# ÉVALUATION DES PARIS
# ═══════════════════════════════════════════════════════════════════════════════════════

def evaluate_bet(match: Dict, market: str, team_perspective: str = "home") -> Tuple[bool, float]:
    """
    Évalue si un pari est gagnant.
    
    Args:
        match: Données du match
        market: Type de marché
        team_perspective: "home" ou "away"
    
    Returns:
        (is_winner, profit)
    """
    hg = match['home_goals']
    ag = match['away_goals']
    total = hg + ag
    
    stake = 1.0
    odds = AVG_ODDS.get(market, 2.0)
    
    is_winner = False
    
    # Marchés globaux
    if market == 'over_25':
        is_winner = total > 2.5
    elif market == 'under_25':
        is_winner = total < 2.5
    elif market == 'over_35':
        is_winner = total > 3.5
    elif market == 'under_35':
        is_winner = total < 3.5
    elif market == 'btts_yes':
        is_winner = hg > 0 and ag > 0
    elif market == 'btts_no':
        is_winner = hg == 0 or ag == 0
    elif market == 'home_win':
        is_winner = hg > ag
    elif market == 'away_win':
        is_winner = ag > hg
    elif market == 'draw':
        is_winner = hg == ag
    
    # Marchés spécifiques
    elif market == 'home_over_05':
        is_winner = hg >= 1
    elif market == 'away_over_05':
        is_winner = ag >= 1
    elif market == 'home_over_15':
        is_winner = hg >= 2
    elif market == 'away_over_15':
        is_winner = ag >= 2
    
    # Marchés temporels (approximations sans données détaillées)
    elif market == 'first_half_over_15':
        # Approximation: Si total >= 3, probable qu'il y ait eu 2+ buts en 1ère MT
        is_winner = total >= 3
    elif market == 'second_half_over_15':
        # Approximation: Si total >= 3
        is_winner = total >= 3
    elif market == 'goal_75_90':
        # Approximation: Si total >= 3
        is_winner = total >= 3
    elif market == 'team_goals_2h_over_05':
        # Équipe a marqué au moins 1
        if team_perspective == "home":
            is_winner = hg >= 1
        else:
            is_winner = ag >= 1
    
    # Corners (pas de données, skip)
    elif market == 'corners_over_105':
        is_winner = False  # Pas de données
    
    profit = stake * (odds - 1) if is_winner else -stake
    return is_winner, profit


# ═══════════════════════════════════════════════════════════════════════════════════════
# STRUCTURES DE RÉSULTATS
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class ScenarioStats:
    """Stats pour un scénario"""
    bets: int = 0
    wins: int = 0
    profit: float = 0.0
    
    @property
    def win_rate(self) -> float:
        return (self.wins / self.bets * 100) if self.bets > 0 else 0.0
    
    @property
    def roi(self) -> float:
        return (self.profit / self.bets * 100) if self.bets > 0 else 0.0


@dataclass
class TeamResultV2:
    """Résultat complet pour une équipe"""
    team_name: str
    tier: str = "UNKNOWN"
    total_matches: int = 0
    
    # Résultats par scénario
    scenario_stats: Dict[str, ScenarioStats] = field(default_factory=dict)
    
    # Meilleur scénario
    best_scenario: str = ""
    best_scenario_pnl: float = 0.0
    best_scenario_wr: float = 0.0
    best_scenario_n: int = 0


# ═══════════════════════════════════════════════════════════════════════════════════════
# BACKTESTER PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════════════

class QuantumBacktesterV2:
    """
    Backtester QUANT 2.0 avec:
    - 20 Scénarios
    - Momentum L5
    - Friction Matrix
    - Marchés spécifiques
    """
    
    def __init__(self):
        self.conn = None
        self.team_dna: Dict[str, Dict] = {}
        self.friction_matrix: Dict[str, Dict] = {}
        self.results: Dict[str, TeamResultV2] = {}
        self.global_scenario_stats: Dict[str, ScenarioStats] = {}
        
        # Initialiser stats globales par scénario
        for scenario_id in ScenarioID:
            self.global_scenario_stats[scenario_id.value] = ScenarioStats()
    
    def connect(self):
        """Connexion DB"""
        self.conn = psycopg2.connect(**DB_CONFIG)
        print("✅ Connecté à PostgreSQL")
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def load_team_dna(self):
        """Charge les DNA des équipes"""
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            cur.execute("""
                SELECT team_name, tier, quantum_dna
                FROM quantum.team_profiles
            """)
            for row in cur.fetchall():
                team = row['team_name'].lower()
                dna = row['quantum_dna'] or {}
                if isinstance(dna, str):
                    dna = json.loads(dna)
                
                # Extraire les métriques clés
                self.team_dna[team] = {
                    'tier': row['tier'] or 'UNKNOWN',
                    'style': dna.get('tactical_dna', {}).get('style', 'balanced'),
                    'xg_for': dna.get('current_season', {}).get('xg', 1.5),
                    'xg_against': dna.get('current_season', {}).get('xga', 1.5),
                    'diesel_factor': dna.get('temporal_dna', {}).get('diesel_factor', 0.5),
                    'killer_instinct': dna.get('psyche_dna', {}).get('killer_instinct', 0.5),
                    'clutch_factor': dna.get('temporal_dna', {}).get('clutch_factor', 0.5),
                    'collapse_rate': dna.get('psyche_dna', {}).get('collapse_rate', 0),
                    'late_collapse_risk': dna.get('temporal_dna', {}).get('late_collapse_risk', 0),
                    'conversion_rate': dna.get('nemesis_dna', {}).get('conversion_rate', 0.3),
                }
            print(f"✅ {len(self.team_dna)} équipes DNA chargées")
        finally:
            cur.close()
    
    def load_friction_matrix(self):
        """Charge la matrice de friction"""
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            cur.execute("""
                SELECT team_a_name, team_b_name, chaos_potential, style_clash_score as style_clash, tempo_clash_score as tempo_clash, predicted_goals
                FROM quantum.matchup_friction
            """)
            for row in cur.fetchall():
                key = f"{row['team_a_name'].lower()}_{row['team_b_name'].lower()}"
                self.friction_matrix[key] = {
                    'chaos_potential': row['chaos_potential'] or 50,
                    'style_clash': row['style_clash'] or 50,
                    'tempo_clash': row['tempo_clash'] or 50,
                    'predicted_goals': row['predicted_goals'] or 2.5,
                }
            print(f"✅ {len(self.friction_matrix)} paires friction chargées")
        except Exception as e:
            print(f"⚠️ Friction matrix: {e}")
        finally:
            cur.close()
    
    def get_friction(self, home: str, away: str) -> Dict:
        """Récupère la friction entre deux équipes"""
        key = f"{home.lower()}_{away.lower()}"
        if key in self.friction_matrix:
            return self.friction_matrix[key]
        
        # Essayer l'inverse
        key_rev = f"{away.lower()}_{home.lower()}"
        if key_rev in self.friction_matrix:
            return self.friction_matrix[key_rev]
        
        # Par défaut
        return {'chaos_potential': 50, 'style_clash': 50, 'tempo_clash': 50, 'predicted_goals': 2.5}
    
    def load_team_matches(self, team_name: str, limit: int = 50) -> List[Dict]:
        """Charge les matchs d'une équipe"""
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        team_lower = team_name.lower()
        
        try:
            cur.execute("""
                SELECT DISTINCT ON (DATE(match_date), home_team, away_team)
                    match_date, home_team, away_team, home_goals, away_goals, league
                FROM matches_results
                WHERE (LOWER(home_team) = %s OR LOWER(away_team) = %s)
                  AND home_goals IS NOT NULL
                ORDER BY DATE(match_date), home_team, away_team, match_date DESC
                LIMIT %s
            """, (team_lower, team_lower, limit))
            
            matches = []
            for row in cur.fetchall():
                matches.append({
                    'date': row['match_date'],
                    'home_team': row['home_team'],
                    'away_team': row['away_team'],
                    'home_goals': row['home_goals'] or 0,
                    'away_goals': row['away_goals'] or 0,
                    'league': row['league'],
                })
            return matches
        finally:
            cur.close()
    
    def analyze_team(self, team_name: str, limit: int = 50) -> TeamResultV2:
        """Analyse une équipe avec les 20 scénarios + Momentum"""
        result = TeamResultV2(team_name=team_name)
        
        team_lower = team_name.lower()
        dna = self.team_dna.get(team_lower, {})
        result.tier = dna.get('tier', 'UNKNOWN')
        
        # Charger les matchs
        matches = self.load_team_matches(team_name, limit)
        result.total_matches = len(matches)
        
        if len(matches) < 5:
            return result
        
        # Initialiser stats par scénario
        for scenario_id in ScenarioID:
            result.scenario_stats[scenario_id.value] = ScenarioStats()
        
        # Analyser chaque match
        for i, match in enumerate(matches):
            is_home = match['home_team'].lower() == team_lower
            
            opponent = match['away_team'] if is_home else match['home_team']
            opponent_dna = self.team_dna.get(opponent.lower(), {})
            
            # Calculer Momentum sur les matchs PRÉCÉDENTS (pas le match actuel)
            previous_matches = matches[i+1:i+6] if i+1 < len(matches) else []
            momentum = calculate_momentum_l5(previous_matches, team_name, is_home)
            opp_momentum = calculate_momentum_l5(previous_matches, opponent, not is_home)
            
            # Récupérer friction
            if is_home:
                friction = self.get_friction(team_name, opponent)
                home_dna, away_dna = dna, opponent_dna
                home_mom, away_mom = momentum, opp_momentum
            else:
                friction = self.get_friction(opponent, team_name)
                home_dna, away_dna = opponent_dna, dna
                home_mom, away_mom = opp_momentum, momentum
            
            # Détecter les scénarios
            scenarios = detect_scenarios(home_dna, away_dna, friction, home_mom, away_mom)
            
            # Évaluer chaque scénario détecté
            for scenario in scenarios:
                if scenario.confidence < 50:  # Seuil minimum
                    continue
                
                market = scenario.primary_market
                team_perspective = "home" if is_home else "away"
                
                is_win, profit = evaluate_bet(match, market, team_perspective)
                
                # Mettre à jour stats équipe
                stats = result.scenario_stats[scenario.scenario_id]
                stats.bets += 1
                stats.profit += profit
                if is_win:
                    stats.wins += 1
                
                # Mettre à jour stats globales
                global_stats = self.global_scenario_stats[scenario.scenario_id]
                global_stats.bets += 1
                global_stats.profit += profit
                if is_win:
                    global_stats.wins += 1
        
        # Trouver le meilleur scénario pour cette équipe
        best_pnl = -999
        for scenario_id, stats in result.scenario_stats.items():
            if stats.bets >= 3 and stats.profit > best_pnl:
                best_pnl = stats.profit
                result.best_scenario = scenario_id
                result.best_scenario_pnl = stats.profit
                result.best_scenario_wr = stats.win_rate
                result.best_scenario_n = stats.bets
        
        return result
    
    def run_backtest(self, limit_per_team: int = 50):
        """Lance le backtest complet"""
        print()
        print("=" * 100)
        print("🧬 QUANTUM BACKTESTER V2.0 - 20 SCÉNARIOS + MOMENTUM L5 + FRICTION")
        print("=" * 100)
        print()
        
        # Charger les données
        self.load_team_dna()
        self.load_friction_matrix()
        
        # Récupérer les équipes
        teams = list(self.team_dna.keys())
        total = len(teams)
        print(f"🏟️ Équipes à analyser: {total}")
        print()
        
        for i, team in enumerate(teams):
            print(f"\r[{i+1}/{total}] {team:30}", end="", flush=True)
            result = self.analyze_team(team, limit_per_team)
            if result.total_matches >= 5:
                self.results[team] = result
        
        print("\n")
        print("✅ Backtest terminé!")
        print(f"   {len(self.results)} équipes analysées")
    
    def print_report(self):
        """Affiche le rapport"""
        print()
        print("=" * 130)
        print("🏆 RAPPORT SCÉNARIOS QUANTUM - ANALYSE PAR ÉQUIPE")
        print("=" * 130)
        print()
        
        # Trier par P&L du meilleur scénario
        sorted_results = sorted(
            [(t, r) for t, r in self.results.items() if r.best_scenario],
            key=lambda x: x[1].best_scenario_pnl,
            reverse=True
        )
        
        print(f"{'#':>3}  {'Équipe':28} {'Best Scénario':20} {'Tier':12} "
              f"{'N':>4} {'W':>4} {'WR':>6} {'P&L':>10}")
        print("-" * 100)
        
        for rank, (team, res) in enumerate(sorted_results[:40], 1):
            if res.best_scenario_pnl >= 10:
                icon = "💎"
            elif res.best_scenario_pnl >= 5:
                icon = "🏆"
            elif res.best_scenario_pnl >= 0:
                icon = "✅"
            else:
                icon = "❌"
            
            stats = res.scenario_stats.get(res.best_scenario)
            wins = stats.wins if stats else 0
            
            print(f"{icon}{rank:>2}  {team:28} {res.best_scenario:20} {res.tier:12} "
                  f"{res.best_scenario_n:>4} {wins:>4} {res.best_scenario_wr:>5.1f}% "
                  f"{res.best_scenario_pnl:>+9.1f}u")
        
        # Résumé global par scénario
        print()
        print("=" * 100)
        print("📊 PERFORMANCE GLOBALE PAR SCÉNARIO")
        print("=" * 100)
        
        sorted_scenarios = sorted(
            self.global_scenario_stats.items(),
            key=lambda x: x[1].profit,
            reverse=True
        )
        
        print(f"{'Scénario':25} {'Bets':>6} {'Wins':>6} {'WR':>7} {'P&L':>10} {'ROI':>8}")
        print("-" * 70)
        
        for scenario_id, stats in sorted_scenarios:
            if stats.bets > 0:
                print(f"{scenario_id:25} {stats.bets:>6} {stats.wins:>6} "
                      f"{stats.win_rate:>6.1f}% {stats.profit:>+9.1f}u {stats.roi:>+7.1f}%")
        
        print()
    
    def compare_with_existing(self):
        """Compare avec les stratégies existantes"""
        print()
        print("=" * 100)
        print("🔬 COMPARAISON: Scénarios Quantum vs Stratégies Existantes")
        print("=" * 100)
        print()
        
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            cur.execute("""
                SELECT strategy_name, 
                       COUNT(*) as teams,
                       SUM(profit) as total_pnl,
                       AVG(win_rate) as avg_wr,
                       SUM(bets) as total_bets
                FROM quantum.team_strategies
                GROUP BY strategy_name
                ORDER BY total_pnl DESC
            """)
            
            print("📈 STRATÉGIES EXISTANTES (team_strategies):")
            print("-" * 80)
            print(f"{'Stratégie':25} {'Équipes':>8} {'Bets':>8} {'WR':>7} {'P&L':>10}")
            print("-" * 80)
            
            for row in cur.fetchall():
                print(f"{row['strategy_name']:25} {row['teams']:>8} {row['total_bets']:>8} "
                      f"{row['avg_wr']:>6.1f}% {row['total_pnl']:>+9.1f}u")
            
            print()
            print("📊 SCÉNARIOS QUANTUM (ce backtest):")
            print("-" * 80)
            
            total_bets = sum(s.bets for s in self.global_scenario_stats.values())
            total_wins = sum(s.wins for s in self.global_scenario_stats.values())
            total_pnl = sum(s.profit for s in self.global_scenario_stats.values())
            avg_wr = (total_wins / total_bets * 100) if total_bets > 0 else 0
            
            print(f"{'TOTAL 20 SCÉNARIOS':25} {len(self.results):>8} {total_bets:>8} "
                  f"{avg_wr:>6.1f}% {total_pnl:>+9.1f}u")
            
        finally:
            cur.close()


# ═══════════════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════════════

def main():
    print()
    print("╔═══════════════════════════════════════════════════════════════════════════════════════╗")
    print("║     QUANTUM BACKTESTER V2.0 - 20 SCÉNARIOS + MOMENTUM L5 + FRICTION                  ║")
    print("╚═══════════════════════════════════════════════════════════════════════════════════════╝")
    print()
    
    backtester = QuantumBacktesterV2()
    
    try:
        backtester.connect()
        backtester.run_backtest(limit_per_team=50)
        backtester.print_report()
        backtester.compare_with_existing()
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
    finally:
        backtester.close()


if __name__ == "__main__":
    main()
