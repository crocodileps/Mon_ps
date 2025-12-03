#!/usr/bin/env python3
"""
🎯 CLV ORCHESTRATOR V10 - QUANT ENGINE
═══════════════════════════════════════════════════════════════════════════════

"Apprend, Simule, Évolue"

PHILOSOPHIE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ce n'est plus un simple calculateur de scores. C'est un QUANT ENGINE qui:
1. SIMULE chaque match 10,000 fois (Monte Carlo)
2. AJUSTE selon les absences et star players (Lineup Impact)
3. DÉTECTE les mouvements de sharp money (Market Dynamics)
4. APPREND de ses erreurs (Meta-Learning)

ARCHITECTURE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Monte Carlo │───▶│ Lineup Adj  │───▶│ Market Dyn  │───▶│ Meta-Learn  │
│ 10K sims    │    │ xG impact   │    │ Steam/CLV   │    │ Auto-tune   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘

TABLES UTILISÉES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• team_intelligence (675) - xG, styles, tendencies
• team_momentum (110) - forme, streaks
• team_class (231) - tier, star_players, big_game_factor
• odds_history (237K) - mouvements de cotes
• team_name_mapping (179) - résolution noms bidirectionnelle
• tactical_matrix (144) - style matchups
• referee_intelligence (21) - arbitres
• team_head_to_head (772) - H2H
• market_traps (196) - pièges
• prediction_history (NEW) - tracking des prédictions pour meta-learning

VERSION: 10.0.0
DATE: 03/12/2025
AUTHOR: Mon_PS Quant Team
"""

import os
import sys
import logging
import random
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import defaultdict
import json

import psycopg2
import psycopg2.extras

# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

DB_CONFIG = {
    'host': os.environ.get('POSTGRES_HOST', 'localhost'),
    'port': int(os.environ.get('POSTGRES_PORT', 5432)),
    'dbname': os.environ.get('POSTGRES_DB', 'monps_db'),
    'user': os.environ.get('POSTGRES_USER', 'monps_user'),
    'password': os.environ.get('POSTGRES_PASSWORD', 'monps_secure_password_2024')
}


# ═══════════════════════════════════════════════════════════════════════════════
# QUANT CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

QUANT_CONFIG = {
    # Monte Carlo
    'monte_carlo_simulations': 10000,
    'monte_carlo_confidence_level': 0.95,
    
    # Events probabilities (par match)
    'red_card_prob': 0.04,           # 4% chance carton rouge
    'injury_prob': 0.02,              # 2% chance blessure majeure
    'momentum_shift_factor': 0.15,    # Impact momentum après but
    
    # Lineup Impact
    'star_player_xg_impact': 0.20,    # Impact max d'un star player sur xG
    'fatigue_after_europe': 0.08,     # Réduction xG après match européen
    'derby_motivation_boost': 0.10,   # Boost xG pour derby
    
    # Market Dynamics
    'steam_threshold_pct': 3.0,       # Mouvement > 3% = steam
    'steam_time_window_hours': 4,     # Fenêtre pour détecter steam
    'clv_target': 0.02,               # CLV cible 2%
    
    # Meta-Learning
    'meta_learning_enabled': True,
    'min_samples_for_adjustment': 30,  # Min picks avant d'ajuster
    'weight_adjustment_factor': 0.10,  # Max 10% d'ajustement par cycle
    'learning_decay': 0.95,            # Poids récents > anciens
}

# Layer weights (ajustables par meta-learning)
LAYER_WEIGHTS = {
    'monte_carlo': 25,      # Poids fort - simulation probabiliste
    'lineup_impact': 15,    # Absences/star players
    'market_dynamics': 15,  # Steam, CLV
    'momentum': 10,
    'tactical': 10,
    'intelligence': 8,
    'class': 8,
    'referee': 8,
    'h2h': 8,
    'reality': 5,
    'profile': 5,
    'trap': -50,            # Blocking (négatif fort)
}

# Sweet Spots calibrés
SWEET_SPOTS = {
    'btts_yes': {'min': 1.65, 'max': 1.85, 'bonus': 8},
    'btts_no': {'min': 1.90, 'max': 2.20, 'bonus': 6},
    'over_25': {'min': 1.70, 'max': 1.95, 'bonus': 8},
    'under_25': {'min': 1.85, 'max': 2.15, 'bonus': 6},
    'over_35': {'min': 2.20, 'max': 2.60, 'bonus': 5},
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class MonteCarloResult:
    """Résultat de simulation Monte Carlo"""
    n_simulations: int = 0
    
    # Probabilités calculées
    home_win_prob: float = 0.0
    draw_prob: float = 0.0
    away_win_prob: float = 0.0
    btts_prob: float = 0.0
    over_15_prob: float = 0.0
    over_25_prob: float = 0.0
    over_35_prob: float = 0.0
    
    # Distribution des scores
    score_distribution: Dict[str, int] = field(default_factory=dict)
    most_likely_score: str = "1-1"
    
    # Statistiques
    avg_total_goals: float = 0.0
    avg_home_goals: float = 0.0
    avg_away_goals: float = 0.0
    
    # Intervalles de confiance (95%)
    btts_ci_lower: float = 0.0
    btts_ci_upper: float = 0.0
    over25_ci_lower: float = 0.0
    over25_ci_upper: float = 0.0
    
    # Métriques de qualité
    simulation_variance: float = 0.0
    confidence_score: float = 0.0


@dataclass
class LineupImpact:
    """Impact des absences et compositions"""
    home_base_xg: float = 1.3
    away_base_xg: float = 1.1
    home_adjusted_xg: float = 1.3
    away_adjusted_xg: float = 1.1
    
    home_absences: List[Dict] = field(default_factory=list)
    away_absences: List[Dict] = field(default_factory=list)
    
    home_xg_adjustment: float = 0.0
    away_xg_adjustment: float = 0.0
    
    fatigue_factor_home: float = 1.0
    fatigue_factor_away: float = 1.0
    
    is_derby: bool = False
    confidence: float = 0.7


@dataclass
class MarketDynamics:
    """Dynamique du marché (steam, CLV)"""
    market_type: str = ""
    
    opening_odds: float = 0.0
    current_odds: float = 0.0
    movement_pct: float = 0.0
    
    is_steam: bool = False
    steam_direction: str = ""  # 'shortening' ou 'drifting'
    steam_magnitude: float = 0.0
    
    is_reverse_line_movement: bool = False
    
    clv_potential: float = 0.0
    sharp_money_signal: int = 0  # -1, 0, +1
    
    odds_history: List[Dict] = field(default_factory=list)
    bookmakers_consensus: float = 0.0


@dataclass 
class QuantPick:
    """Pick avec analyse Quant complète"""
    
    # Identifiants
    match_id: str = ""
    home_team: str = ""
    away_team: str = ""
    league: str = ""
    commence_time: datetime = None
    
    # Marché
    market_type: str = ""
    odds: float = 0.0
    implied_prob: float = 0.0
    
    # Monte Carlo
    mc_prob: float = 0.0
    mc_edge: float = 0.0
    mc_confidence: float = 0.0
    mc_result: MonteCarloResult = None
    
    # Lineup Impact
    lineup_impact: LineupImpact = None
    xg_adjusted_home: float = 0.0
    xg_adjusted_away: float = 0.0
    
    # Market Dynamics
    market_dynamics: MarketDynamics = None
    steam_signal: int = 0
    clv_expected: float = 0.0
    
    # Layer scores
    mc_score: int = 0
    lineup_score: int = 0
    market_score: int = 0
    momentum_score: int = 0
    tactical_score: int = 0
    intelligence_score: int = 0
    class_score: int = 0
    referee_score: int = 0
    h2h_score: int = 0
    reality_score: int = 0
    profile_score: int = 0
    sweet_spot_score: int = 0
    
    # Aggregates
    layer_score: int = 0
    quant_score: float = 0.0
    final_score: int = 0
    
    # Data quality
    data_coverage: float = 0.0
    layers_active: int = 0
    
    # Trap
    is_trap: bool = False
    trap_reason: str = ""
    
    # Kelly & Risk
    kelly_fraction: float = 0.0
    recommended_stake: float = 0.0
    risk_level: str = "medium"
    
    # Output
    recommendation: str = ""
    confidence_level: str = ""
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Meta-learning tracking
    prediction_id: str = ""
    predicted_at: datetime = None


# ═══════════════════════════════════════════════════════════════════════════════
# MONTE CARLO ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class MonteCarloEngine:
    """
    Moteur de simulation Monte Carlo
    Simule chaque match 10,000 fois avec variance réaliste
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or QUANT_CONFIG
        self.n_sims = self.config['monte_carlo_simulations']
    
    def simulate_match(self, home_xg: float, away_xg: float,
                       home_style: str = 'balanced', 
                       away_style: str = 'balanced',
                       context: Dict = None) -> MonteCarloResult:
        """
        Simule un match N fois et retourne les probabilités
        
        Paramètres:
        - home_xg, away_xg: Expected Goals ajustés
        - home_style, away_style: Styles de jeu (affectent la variance)
        - context: Données additionnelles (derby, fatigue, etc.)
        """
        
        result = MonteCarloResult(n_simulations=self.n_sims)
        
        # Ajuster variance selon les styles
        home_variance = self._get_style_variance(home_style)
        away_variance = self._get_style_variance(away_style)
        
        # Résultats des simulations
        home_wins = 0
        away_wins = 0
        draws = 0
        btts_yes = 0
        over_15 = 0
        over_25 = 0
        over_35 = 0
        
        all_home_goals = []
        all_away_goals = []
        scores = defaultdict(int)
        
        for _ in range(self.n_sims):
            # Simuler un match
            home_goals, away_goals = self._simulate_single_match(
                home_xg, away_xg, home_variance, away_variance, context
            )
            
            all_home_goals.append(home_goals)
            all_away_goals.append(away_goals)
            
            # Comptabiliser résultats
            if home_goals > away_goals:
                home_wins += 1
            elif away_goals > home_goals:
                away_wins += 1
            else:
                draws += 1
            
            if home_goals > 0 and away_goals > 0:
                btts_yes += 1
            
            total = home_goals + away_goals
            if total >= 2:
                over_15 += 1
            if total >= 3:
                over_25 += 1
            if total >= 4:
                over_35 += 1
            
            score_key = f"{home_goals}-{away_goals}"
            scores[score_key] += 1
        
        # Calculer probabilités
        result.home_win_prob = home_wins / self.n_sims
        result.draw_prob = draws / self.n_sims
        result.away_win_prob = away_wins / self.n_sims
        result.btts_prob = btts_yes / self.n_sims
        result.over_15_prob = over_15 / self.n_sims
        result.over_25_prob = over_25 / self.n_sims
        result.over_35_prob = over_35 / self.n_sims
        
        # Statistiques
        result.avg_home_goals = sum(all_home_goals) / self.n_sims
        result.avg_away_goals = sum(all_away_goals) / self.n_sims
        result.avg_total_goals = result.avg_home_goals + result.avg_away_goals
        
        # Score le plus probable
        result.score_distribution = dict(scores)
        result.most_likely_score = max(scores, key=scores.get)
        
        # Intervalles de confiance (Wilson score interval)
        result.btts_ci_lower, result.btts_ci_upper = self._wilson_ci(btts_yes, self.n_sims)
        result.over25_ci_lower, result.over25_ci_upper = self._wilson_ci(over_25, self.n_sims)
        
        # Variance et confidence
        btts_variance = result.btts_prob * (1 - result.btts_prob)
        result.simulation_variance = btts_variance
        
        # Confidence basée sur la largeur de l'IC
        ci_width = result.btts_ci_upper - result.btts_ci_lower
        result.confidence_score = max(0, 1 - (ci_width / 0.15))  # Plus IC étroit = plus confiant
        
        return result
    
    def _simulate_single_match(self, home_xg: float, away_xg: float,
                                home_var: float, away_var: float,
                                context: Dict = None) -> Tuple[int, int]:
        """
        Simule un seul match minute par minute
        
        Events possibles:
        - But (basé sur xG)
        - Carton rouge (réduit xG équipe)
        - Momentum shift (après but)
        """
        
        context = context or {}
        
        # xG par minute (90 minutes)
        home_xg_per_min = home_xg / 90
        away_xg_per_min = away_xg / 90
        
        home_goals = 0
        away_goals = 0
        home_red = False
        away_red = False
        
        # Facteur momentum (change après chaque but)
        home_momentum = 1.0
        away_momentum = 1.0
        
        for minute in range(1, 91):
            # ═══════════════════════════════════════════════════════
            # GAME STATE DYNAMICS V10.1 - Ajuster xG selon score/temps
            # ═══════════════════════════════════════════════════════
            goal_diff = home_goals - away_goals
            home_gs_factor = 1.0
            away_gs_factor = 1.0
            
            if minute >= 60:  # Dernière demi-heure
                if goal_diff >= 2:
                    home_gs_factor, away_gs_factor = 0.7, 1.4  # Home défend
                elif goal_diff == 1:
                    home_gs_factor, away_gs_factor = 0.85, 1.2
                elif goal_diff == -1:
                    home_gs_factor, away_gs_factor = 1.2, 0.85
                elif goal_diff <= -2:
                    home_gs_factor, away_gs_factor = 1.4, 0.7  # Home pousse
            
            if minute >= 75:  # 15 dernières minutes = intensité max
                if goal_diff >= 1:
                    home_gs_factor, away_gs_factor = 0.6, 1.5
                elif goal_diff <= -1:
                    home_gs_factor, away_gs_factor = 1.5, 0.6
            
            # Appliquer Game State aux xG
            adj_home_xg = home_xg_per_min * home_gs_factor
            adj_away_xg = away_xg_per_min * away_gs_factor

            # Vérifier carton rouge (rare)
            if not home_red and random.random() < self.config['red_card_prob'] / 90:
                home_red = True
                home_xg_per_min *= 0.7  # -30% après rouge
            
            if not away_red and random.random() < self.config['red_card_prob'] / 90:
                away_red = True
                away_xg_per_min *= 0.7
            
            # Calculer probabilité de but cette minute
            # Utiliser distribution Poisson modifiée avec variance
            home_prob = adj_home_xg * home_momentum * (1 + random.gauss(0, home_var))
            away_prob = adj_away_xg * away_momentum * (1 + random.gauss(0, away_var))
            
            # But domicile ?
            if random.random() < max(0, home_prob):
                home_goals += 1
                # Momentum shift
                home_momentum *= (1 + self.config['momentum_shift_factor'])
                away_momentum *= (1 - self.config['momentum_shift_factor'] * 0.5)
            
            # But extérieur ?
            if random.random() < max(0, away_prob):
                away_goals += 1
                away_momentum *= (1 + self.config['momentum_shift_factor'])
                home_momentum *= (1 - self.config['momentum_shift_factor'] * 0.5)
            
            # Decay momentum vers 1.0
            home_momentum = 1.0 + (home_momentum - 1.0) * 0.98
            away_momentum = 1.0 + (away_momentum - 1.0) * 0.98
        
        return home_goals, away_goals
    
    def _get_style_variance(self, style: str) -> float:
        """
        Retourne la variance associée à un style de jeu
        Styles offensifs = plus de variance
        """
        variance_map = {
            'gegenpressing': 0.25,
            'high_press': 0.22,
            'attacking': 0.20,
            'tiki_taka': 0.18,
            'possession': 0.15,
            'balanced': 0.15,
            'direct_play': 0.18,
            'counter_attack': 0.20,
            'defensive': 0.12,
            'low_block_counter': 0.14,
            'park_the_bus': 0.10,
        }
        return variance_map.get(style.lower(), 0.15)
    
    def _wilson_ci(self, successes: int, n: int, confidence: float = 0.95) -> Tuple[float, float]:
        """
        Calcule l'intervalle de confiance Wilson
        Plus précis que l'approximation normale pour proportions
        """
        if n == 0:
            return 0.0, 1.0
        
        z = 1.96 if confidence == 0.95 else 2.576  # 95% ou 99%
        p = successes / n
        
        denominator = 1 + z**2 / n
        center = (p + z**2 / (2*n)) / denominator
        margin = z * math.sqrt((p*(1-p) + z**2/(4*n)) / n) / denominator
        
        return max(0, center - margin), min(1, center + margin)


# ═══════════════════════════════════════════════════════════════════════════════
# LINEUP IMPACT ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class LineupImpactEngine:
    """
    Calcule l'impact des absences et compositions sur les xG
    Utilise: team_class.star_players, team_momentum.key_player_absent
    """
    
    def __init__(self, conn, config: Dict = None):
        self.conn = conn
        self.config = config or QUANT_CONFIG
    

    def _get_competition_stats(self, team_name: str, location: str, competition: str) -> Dict:
        """Stats filtrées par compétition depuis match_results"""
        if not self.conn or not competition:
            return {}
        
        try:
            import psycopg2.extras
            
            # Mapping coupes -> ligues domestiques
            league_map = {
                'league cup': '%premier%', 'carabao': '%premier%', 'fa cup': '%premier%',
                'copa del rey': '%liga%', 'dfb pokal': '%bundesliga%',
                'coppa italia': '%serie%', 'coupe de france': '%ligue 1%',
            }
            
            comp_lower = competition.lower()
            league_filter = None
            for key, val in league_map.items():
                if key in comp_lower:
                    league_filter = val
                    break
            
            if not league_filter:
                league_filter = f"%{competition}%"
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                if location == 'home':
                    cur.execute("""
                        SELECT AVG(score_home) as scored, AVG(score_away) as conceded, COUNT(*) as n
                        FROM match_results
                        WHERE LOWER(home_team) LIKE %s AND is_finished = TRUE
                          AND LOWER(league) LIKE %s
                    """, (f"%{team_name.lower()}%", league_filter))
                else:
                    cur.execute("""
                        SELECT AVG(score_away) as scored, AVG(score_home) as conceded, COUNT(*) as n
                        FROM match_results
                        WHERE LOWER(away_team) LIKE %s AND is_finished = TRUE
                          AND LOWER(league) LIKE %s
                    """, (f"%{team_name.lower()}%", league_filter))
                
                row = cur.fetchone()
                if row and row['n'] and row['n'] >= 3:
                    return {
                        'goals_scored_avg': float(row['scored']) if row['scored'] else None,
                        'goals_conceded_avg': float(row['conceded']) if row['conceded'] else None,
                        'sample_size': row['n'],
                    }
            return {}
        except Exception as e:
            return {}

    def _get_tactical_matchup(self, home_style: str, away_style: str) -> Dict:
        """
        V11 - Récupère les probabilités de matchup tactique
        
        Retourne: {btts_probability, over_25_probability, avg_goals_total, upset_probability}
        """
        if not self.conn or not home_style or not away_style:
            return {}
        
        try:
            import psycopg2.extras
            
            # Normaliser les styles
            style_map = {
                'balanced': 'balanced', 'balanced_offensive': 'attacking',
                'balanced_defensive': 'defensive', 'high_press': 'high_press',
                'pressing': 'pressing', 'gegenpressing': 'gegenpressing',
                'possession': 'possession', 'tiki_taka': 'tiki_taka',
                'counter_attack': 'counter_attack', 'low_block_counter': 'low_block_counter',
                'defensive': 'defensive', 'attacking': 'attacking',
                'direct_play': 'direct_play', 'park_the_bus': 'park_the_bus'
            }
            
            home_s = style_map.get(home_style.lower(), 'balanced')
            away_s = style_map.get(away_style.lower(), 'balanced')
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT btts_probability, over_25_probability, avg_goals_total,
                           upset_probability, win_rate_a, confidence_level
                    FROM tactical_matrix
                    WHERE style_a = %s AND style_b = %s
                """, (home_s, away_s))
                
                row = cur.fetchone()
                if row:
                    return {
                        'btts_prob': float(row['btts_probability']) if row['btts_probability'] else None,
                        'over25_prob': float(row['over_25_probability']) if row['over_25_probability'] else None,
                        'avg_goals': float(row['avg_goals_total']) if row['avg_goals_total'] else None,
                        'upset_prob': float(row['upset_probability']) if row['upset_probability'] else None,
                        'home_win_rate': float(row['win_rate_a']) if row['win_rate_a'] else None,
                        'confidence': row['confidence_level'],
                        'source': 'tactical_matrix'
                    }
            return {}
        except Exception as e:
            return {}

    def _get_vs_opponent_type_adjustment(self, team_intel: Dict, opponent_tier: str, 
                                          location: str) -> float:
        """
        V11 - Ajuste xG selon type d'adversaire (top/bottom teams)
        
        Utilise: vs_top_teams, vs_bottom_teams depuis team_intelligence
        """
        if not team_intel:
            return 0.0
        
        adjustment = 0.0
        tier_values = {'S': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1}
        opp_tier_val = tier_values.get(opponent_tier, 3)
        
        try:
            if opp_tier_val >= 4:  # Adversaire Top (S ou A)
                vs_top = team_intel.get('vs_top_teams', {})
                if isinstance(vs_top, dict):
                    # Équipe qui performe bien contre les tops = boost
                    win_rate = vs_top.get('win_rate', 30)
                    if win_rate > 40:
                        adjustment += 0.10  # Bon contre les grands
                    elif win_rate < 20:
                        adjustment -= 0.10  # Mauvais contre les grands
                        
            elif opp_tier_val <= 2:  # Adversaire Bottom (C ou D)
                vs_bottom = team_intel.get('vs_bottom_teams', {})
                if isinstance(vs_bottom, dict):
                    win_rate = vs_bottom.get('win_rate', 60)
                    if win_rate > 75:
                        adjustment += 0.15  # Écrase les petits
                    elif win_rate < 50:
                        adjustment -= 0.10  # Piégé par les petits
        except:
            pass
        
        return adjustment

    def _regress_to_mean(self, team_stat: float, sample_size: int,
                          league_avg: float = None, location: str = 'home',
                          tier_diff: int = 0) -> float:
        """
        V10.4 - Régression vers la moyenne de la ligue
        
        Formule: adjusted = (team_stat * n + league_avg * C) / (n + C)
        
        Args:
            team_stat: Statistique brute de l'équipe
            sample_size: Nombre de matchs analysés
            league_avg: Moyenne de la ligue (défaut: 1.3 home, 1.4 away pour scored)
            location: 'home' ou 'away'
        """
        # Constante de régression (poids de la moyenne ligue)
        # V10.5 - C dynamique selon tier_diff
        if tier_diff >= 2:
            C = 2   # D1 vs D2: régression faible
        elif tier_diff == 1:
            C = 5   # Légère diff: régression moyenne
        else:
            C = 10  # Même niveau: régression forte
        
        # Moyennes par défaut (top 5 ligues européennes)
        if league_avg is None:
            if location == 'home':
                league_avg = 1.55  # Moyenne buts marqués à domicile
            else:
                league_avg = 1.25  # Moyenne buts marqués à l'extérieur
        
        # Régression
        adjusted = (team_stat * sample_size + league_avg * C) / (sample_size + C)
        
        return round(adjusted, 2)

    def calculate_impact(self, home_team: str, away_team: str,
                         home_intel: Dict, away_intel: Dict,
                         home_class: Dict, away_class: Dict,
                         home_momentum: Dict, away_momentum: Dict,
                         context: Dict = None) -> LineupImpact:
        """
        Calcule l'ajustement xG basé sur les lineups
        """
        
        impact = LineupImpact()
        
        # ═══════════════════════════════════════════════════════
        # xG V10.2 - ATTAQUE + DÉFENSE ADVERSE + FILTRAGE COMPÉTITION
        # ═══════════════════════════════════════════════════════
        
        competition = context.get('competition') if context else None
        
        # HOME xG = 60% attaque home + 40% défense away
        home_attack = 1.3
        away_defense = 1.3

        # V10.5 - Calculer tier_diff AVANT régression
        home_tier = home_class.get('tier', 'B') if home_class else 'B'
        away_tier = away_class.get('tier', 'B') if away_class else 'B'
        tier_values_pre = {'S': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1}
        tier_diff_pre = abs(tier_values_pre.get(home_tier, 3) - tier_values_pre.get(away_tier, 3))

        
        # Priorité 1: Stats filtrées par compétition (si disponibles)
        home_comp_stats = {}
        away_comp_stats = {}
        if competition and self.conn:
            home_comp_stats = self._get_competition_stats(home_team, 'home', competition)
            away_comp_stats = self._get_competition_stats(away_team, 'away', competition)
            
            if home_comp_stats.get('goals_scored_avg'):
                # V10.4 - Régression vers la moyenne si sample faible
                n = home_comp_stats.get('sample_size', 5)
                home_attack = self._regress_to_mean(
                    home_comp_stats['goals_scored_avg'], n, location='home', tier_diff=tier_diff_pre
                )
            if away_comp_stats.get('goals_conceded_avg'):
                n = away_comp_stats.get('sample_size', 5)
                away_defense = self._regress_to_mean(
                    away_comp_stats['goals_conceded_avg'], n, league_avg=1.35, location='away', tier_diff=tier_diff_pre
                )
        
        # Priorité 2: Stats team_intelligence (fallback)
        if home_attack == 1.3 and home_intel:
            xg = home_intel.get('xg_for_avg')
            if xg is None or xg == 0:
                xg = home_intel.get('home_goals_scored_avg')
            home_attack = float(xg) if xg else 1.3
        
        if away_defense == 1.3 and away_intel:
            away_def = away_intel.get('away_goals_conceded_avg')
            if away_def:
                away_defense = float(away_def)
        
        impact.home_base_xg = (home_attack * 0.6) + (away_defense * 0.4)
        
        # AWAY xG = 60% attaque away + 40% défense home
        away_attack = 1.1
        home_defense = 1.1
        
        # Priorité 1: Stats filtrées par compétition
        if competition and self.conn:
            if away_comp_stats.get('goals_scored_avg'):
                n = away_comp_stats.get('sample_size', 5)
                away_attack = self._regress_to_mean(
                    away_comp_stats['goals_scored_avg'], n, location='away', tier_diff=tier_diff_pre
                )
            if home_comp_stats.get('goals_conceded_avg'):
                n = home_comp_stats.get('sample_size', 5)
                home_defense = self._regress_to_mean(
                    home_comp_stats['goals_conceded_avg'], n, league_avg=1.20, location='home', tier_diff=tier_diff_pre
                )
        
        # Priorité 2: Stats team_intelligence (fallback)
        if away_attack == 1.1 and away_intel:
            xg = away_intel.get('xg_for_avg')
            if xg is None or xg == 0:
                xg = away_intel.get('away_goals_scored_avg')
            away_attack = float(xg) if xg else 1.1
        
        if home_defense == 1.1 and home_intel:
            home_def = home_intel.get('home_goals_conceded_avg')
            if home_def:
                home_defense = float(home_def)
        
        impact.away_base_xg = (away_attack * 0.6) + (home_defense * 0.4)
        
        # ═══════════════════════════════════════════════════════
        # V10.3 - LEAGUE TIER ADJUSTMENT
        # D1 vs D2 = boost attaque D1, malus défense D2
        # ═══════════════════════════════════════════════════════
        home_tier = home_class.get('tier', 'B') if home_class else 'B'
        away_tier = away_class.get('tier', 'B') if away_class else 'B'
        
        tier_values = {'S': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1}
        home_tier_val = tier_values.get(home_tier, 3)
        away_tier_val = tier_values.get(away_tier, 3)
        tier_diff = home_tier_val - away_tier_val
        
        if tier_diff >= 2:  # Home très supérieur (ex: Liverpool vs Sunderland)
            impact.home_base_xg *= 1.25  # +25% attaque home
            impact.away_base_xg *= 0.75  # -25% attaque away
        elif tier_diff >= 1:  # Home supérieur
            impact.home_base_xg *= 1.10  # +10% attaque home
            impact.away_base_xg *= 0.90  # -10% attaque away
        elif tier_diff <= -2:  # Away très supérieur
            impact.home_base_xg *= 0.75
            impact.away_base_xg *= 1.25
        elif tier_diff <= -1:  # Away supérieur
            impact.home_base_xg *= 0.90
            impact.away_base_xg *= 1.10
        
        # ═══════════════════════════════════════════════════════
        # V11 - TEAM_CLASS EXTENDED FACTORS
        # ═══════════════════════════════════════════════════════
        
        # Home Fortress Factor (équipes dominantes à domicile)
        home_fortress = float(home_class.get('home_fortress_factor', 1.0)) if home_class else 1.0
        away_weakness = float(away_class.get('away_weakness_factor', 1.0)) if away_class else 1.0
        
        # Appliquer les facteurs
        if home_fortress > 1.0:
            impact.home_base_xg *= home_fortress  # Ex: 1.15 = +15% xG domicile
        if away_weakness > 1.0:
            impact.away_base_xg *= (2.0 - away_weakness)  # Ex: 1.10 = -10% xG extérieur
        
        # Psychological Edge (avantage mental dans les gros matchs)
        home_psych = float(home_class.get('psychological_edge', 1.0)) if home_class else 1.0
        away_psych = float(away_class.get('psychological_edge', 1.0)) if away_class else 1.0
        
        # Si différence psychologique significative
        psych_diff = home_psych - away_psych
        if psych_diff >= 0.1:
            impact.home_base_xg *= 1.05  # Avantage mental home
        elif psych_diff <= -0.1:
            impact.away_base_xg *= 1.05  # Avantage mental away
        
        # ═══════════════════════════════════════════════════════
        # V11 - TACTICAL MATCHUP (via tactical_matrix)
        # ═══════════════════════════════════════════════════════
        
        home_style = None
        away_style = None
        
        # Récupérer styles depuis team_intelligence (priorité) ou team_class
        if home_intel and home_intel.get('current_style'):
            home_style = home_intel.get('current_style')
        elif home_class and home_class.get('playing_style'):
            home_style = home_class.get('playing_style')
        
        if away_intel and away_intel.get('current_style'):
            away_style = away_intel.get('current_style')
        elif away_class and away_class.get('playing_style'):
            away_style = away_class.get('playing_style')
        
        # Stocker le matchup tactique pour usage ultérieur (probas BTTS/Over25)
        if home_style and away_style:
            tactical_data = self._get_tactical_matchup(home_style, away_style)
            if tactical_data:
                impact.tactical_matchup = tactical_data
                # Ajuster xG selon avg_goals du matchup
                if tactical_data.get('avg_goals'):
                    expected_total = tactical_data['avg_goals']
                    current_total = impact.home_base_xg + impact.away_base_xg
                    if expected_total > 0 and current_total > 0:
                        # Ajuster proportionnellement (max ±15%)
                        ratio = min(1.15, max(0.85, expected_total / current_total))
                        impact.home_base_xg *= ratio
                        impact.away_base_xg *= ratio
        
        # ═══════════════════════════════════════════════════════
        # V11 - VS TOP/BOTTOM TEAMS ADJUSTMENT
        # ═══════════════════════════════════════════════════════
        
        # Ajuster home_xg selon performance contre ce type d'adversaire
        home_vs_adj = self._get_vs_opponent_type_adjustment(home_intel, away_tier, 'home')
        away_vs_adj = self._get_vs_opponent_type_adjustment(away_intel, home_tier, 'away')
        
        impact.home_base_xg += home_vs_adj
        impact.away_base_xg += away_vs_adj
        
        # Ajustement pour absences STAR PLAYERS
        home_adj = self._calculate_absence_impact(home_class, home_momentum, 'home')
        away_adj = self._calculate_absence_impact(away_class, away_momentum, 'away')
        
        impact.home_xg_adjustment = home_adj
        impact.away_xg_adjustment = away_adj
        
        # Fatigue (après match européen)
        if context and context.get('home_played_europe_midweek'):
            impact.fatigue_factor_home = 1 - self.config['fatigue_after_europe']
            impact.home_xg_adjustment -= self.config['fatigue_after_europe']
        
        if context and context.get('away_played_europe_midweek'):
            impact.fatigue_factor_away = 1 - self.config['fatigue_after_europe']
            impact.away_xg_adjustment -= self.config['fatigue_after_europe']
        
        # Derby boost
        if context and context.get('is_derby'):
            impact.is_derby = True
            impact.home_xg_adjustment += self.config['derby_motivation_boost']
            impact.away_xg_adjustment += self.config['derby_motivation_boost']
        
        # xG ajustés finaux
        impact.home_adjusted_xg = max(0.5, impact.home_base_xg + impact.home_xg_adjustment)
        impact.away_adjusted_xg = max(0.5, impact.away_base_xg + impact.away_xg_adjustment)
        
        # Confidence
        impact.confidence = self._calculate_confidence(home_intel, away_intel, home_class, away_class)
        
        return impact
    
    def _calculate_absence_impact(self, team_class: Dict, momentum: Dict, 
                                   location: str) -> float:
        """
        Calcule l'impact des absences sur xG
        """
        adjustment = 0.0
        
        # Depuis team_momentum
        if momentum and momentum.get('key_player_absent'):
            impact = float(momentum.get('key_absence_impact', 10) or 10) / 100
            adjustment -= min(impact, self.config['star_player_xg_impact'])
        
        # Depuis team_class.star_players (si données disponibles)
        # Note: On n'a pas l'info des absences en temps réel sans API
        # Ceci serait enrichi par API-Football lineups
        
        return adjustment
    
    def _calculate_confidence(self, home_intel, away_intel, home_class, away_class) -> float:
        """Calcule la confiance dans les données lineup"""
        confidence = 0.5  # Base
        
        if home_intel and home_intel.get('is_reliable'):
            confidence += 0.15
        if away_intel and away_intel.get('is_reliable'):
            confidence += 0.15
        if home_class:
            confidence += 0.1
        if away_class:
            confidence += 0.1
        
        return min(0.95, confidence)


# ═══════════════════════════════════════════════════════════════════════════════
# MARKET DYNAMICS ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class MarketDynamicsEngine:
    """
    Analyse les mouvements de cotes et détecte le sharp money
    Utilise: odds_history (237K lignes)
    """
    
    def __init__(self, conn, config: Dict = None):
        self.conn = conn
        self.config = config or QUANT_CONFIG
    
    def analyze_market(self, match_id: str, market_type: str,
                       current_odds: float) -> MarketDynamics:
        """
        Analyse complète de la dynamique du marché
        """
        
        dynamics = MarketDynamics(market_type=market_type, current_odds=current_odds)
        
        # Récupérer historique des cotes
        odds_history = self._get_odds_history(match_id)
        
        if not odds_history:
            return dynamics
        
        dynamics.odds_history = odds_history
        
        # Mapper market_type vers colonne odds_history
        odds_column = self._map_market_to_column(market_type)
        
        if not odds_column:
            return dynamics
        
        # Extraire les cotes pertinentes
        relevant_odds = []
        for record in odds_history:
            odds_value = record.get(odds_column)
            if odds_value and odds_value > 1:
                relevant_odds.append({
                    'odds': float(odds_value),
                    'timestamp': record.get('collected_at'),
                    'bookmaker': record.get('bookmaker')
                })
        
        if not relevant_odds:
            return dynamics
        
        # Trier par timestamp
        relevant_odds.sort(key=lambda x: x['timestamp'] if x['timestamp'] else datetime.min)
        
        # Opening et current
        dynamics.opening_odds = relevant_odds[0]['odds']
        dynamics.current_odds = relevant_odds[-1]['odds']
        
        # Mouvement total
        if dynamics.opening_odds > 0:
            dynamics.movement_pct = ((dynamics.current_odds - dynamics.opening_odds) 
                                      / dynamics.opening_odds * 100)
        
        # Détecter Steam (mouvement rapide récent)
        dynamics.is_steam, dynamics.steam_direction, dynamics.steam_magnitude = \
            self._detect_steam(relevant_odds)
        
        # CLV potentiel
        if dynamics.steam_direction == 'shortening':
            dynamics.clv_potential = dynamics.opening_odds - dynamics.current_odds
        
        # Signal sharp money
        dynamics.sharp_money_signal = self._calculate_sharp_signal(dynamics)
        
        # Consensus bookmakers
        dynamics.bookmakers_consensus = self._calculate_consensus(odds_history, odds_column)
        
        return dynamics
    
    def _get_odds_history(self, match_id: str) -> List[Dict]:
        """Récupère l'historique des cotes pour un match"""
        if not self.conn:
            return []
        
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT 
                        match_id, bookmaker,
                        home_odds, draw_odds, away_odds,
                        collected_at
                    FROM odds_history
                    WHERE match_id = %s
                    ORDER BY collected_at ASC
                """, (match_id,))
                
                return [dict(r) for r in cur.fetchall()]
                
        except Exception as e:
            logger.debug(f"Odds history error: {e}")
            return []
    
    def _map_market_to_column(self, market_type: str) -> Optional[str]:
        """Mappe un type de marché vers la colonne odds_history"""
        mapping = {
            'home': 'home_odds',
            'away': 'away_odds',
            'draw': 'draw_odds',
            # Note: BTTS et O/U ne sont pas dans odds_history actuel
            # Il faudrait une autre table ou enrichir
        }
        return mapping.get(market_type.lower())
    
    def _detect_steam(self, odds_list: List[Dict]) -> Tuple[bool, str, float]:
        """
        Détecte un mouvement steam (sharp money)
        Steam = mouvement > 3% en < 4h
        """
        if len(odds_list) < 2:
            return False, "", 0.0
        
        now = datetime.now()
        window = timedelta(hours=self.config['steam_time_window_hours'])
        
        # Filtrer les cotes récentes
        recent = [o for o in odds_list 
                  if o['timestamp'] and now - o['timestamp'] < window]
        
        if len(recent) < 2:
            return False, "", 0.0
        
        first_recent = recent[0]['odds']
        last_recent = recent[-1]['odds']
        
        movement_pct = (last_recent - first_recent) / first_recent * 100

        # ═══════════════════════════════════════════════════════
        # SPREAD/LIQUIDITÉ V10.1 - Pondérer par liquidité du marché
        # ═══════════════════════════════════════════════════════
        steam_importance = 1.0
        last_record = recent[-1] if recent else {}
        h_odds = last_record.get('home_odds')
        d_odds = last_record.get('draw_odds')
        a_odds = last_record.get('away_odds')
        
        if h_odds and d_odds and a_odds:
            try:
                spread = (1/float(h_odds) + 1/float(d_odds) + 1/float(a_odds)) - 1
                if spread < 0.03:
                    steam_importance = 1.5  # Très liquide = signal fort
                elif spread < 0.05:
                    steam_importance = 1.0  # Normal
                elif spread < 0.07:
                    steam_importance = 0.7  # Peu liquide
                else:
                    steam_importance = 0.3  # Illiquide = ignorer
            except:
                pass
        
        # Ajuster le seuil par liquidité
        adjusted_threshold = self.config['steam_threshold_pct'] / steam_importance
        movement_pct_adj = abs(movement_pct) * steam_importance

        
        if abs(movement_pct) >= adjusted_threshold:
            direction = 'shortening' if movement_pct < 0 else 'drifting'
            return True, direction, abs(movement_pct)
        
        return False, "", 0.0
    
    def _calculate_sharp_signal(self, dynamics: MarketDynamics) -> int:
        """
        Calcule le signal sharp money
        +1 = sharp avec nous (shortening)
        -1 = sharp contre nous (drifting)
        0 = neutre
        """
        if not dynamics.is_steam:
            return 0
        
        if dynamics.steam_direction == 'shortening':
            return 1  # Cote baisse = sharp bet sur ce marché
        elif dynamics.steam_direction == 'drifting':
            return -1  # Cote monte = sharp contre
        
        return 0
    
    def _calculate_consensus(self, odds_history: List[Dict], 
                              odds_column: str) -> float:
        """
        Calcule le consensus entre bookmakers
        Faible variance = fort consensus
        """
        if not odds_history or not odds_column:
            return 0.5
        
        # Prendre les dernières cotes de chaque bookmaker
        latest_by_bookie = {}
        for record in odds_history:
            bookie = record.get('bookmaker')
            odds = record.get(odds_column)
            if bookie and odds:
                latest_by_bookie[bookie] = float(odds)
        
        if len(latest_by_bookie) < 2:
            return 0.5
        
        odds_values = list(latest_by_bookie.values())
        mean_odds = sum(odds_values) / len(odds_values)
        variance = sum((o - mean_odds)**2 for o in odds_values) / len(odds_values)
        
        # Normaliser: faible variance = consensus élevé
        consensus = max(0, 1 - (variance / 0.5))
        
        return consensus


# ═══════════════════════════════════════════════════════════════════════════════
# META-LEARNING ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class MetaLearningEngine:
    """
    Apprend des erreurs passées et ajuste les poids
    Tracking des prédictions + auto-tuning
    """
    
    def __init__(self, conn, config: Dict = None):
        self.conn = conn
        self.config = config or QUANT_CONFIG
        self.layer_performance = {}
        
        self._ensure_tracking_table()
        self._load_historical_performance()
    
    def _ensure_tracking_table(self):
        """Crée la table de tracking si elle n'existe pas"""
        if not self.conn:
            return
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS prediction_tracking (
                        id SERIAL PRIMARY KEY,
                        prediction_id VARCHAR(64) UNIQUE,
                        match_id VARCHAR(64),
                        market_type VARCHAR(32),
                        predicted_prob NUMERIC(5,4),
                        odds_at_prediction NUMERIC(6,3),
                        mc_prob NUMERIC(5,4),
                        layer_score INTEGER,
                        quant_score NUMERIC(8,2),
                        final_recommendation VARCHAR(32),
                        
                        -- Résultat
                        actual_result VARCHAR(16),  -- 'win', 'lose', 'push'
                        is_correct BOOLEAN,
                        profit_loss NUMERIC(8,4),
                        clv_captured NUMERIC(6,4),
                        
                        -- Layer contributions (pour analyse)
                        mc_score INTEGER,
                        lineup_score INTEGER,
                        market_score INTEGER,
                        momentum_score INTEGER,
                        tactical_score INTEGER,
                        
                        -- Timestamps
                        predicted_at TIMESTAMP DEFAULT NOW(),
                        settled_at TIMESTAMP,
                        
                        -- Meta
                        model_version VARCHAR(16) DEFAULT 'v10'
                    )
                """)
                
                # Index pour performance
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_pred_tracking_settled 
                    ON prediction_tracking(is_correct, settled_at)
                """)
                
                self.conn.commit()
                logger.info("✅ Table prediction_tracking prête")
                
        except Exception as e:
            logger.warning(f"⚠️ Meta-learning table error: {e}")
            self.conn.rollback()
    
    def _load_historical_performance(self):
        """Charge les performances historiques des layers"""
        if not self.conn:
            return
        
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                # Performance par layer sur les 30 derniers jours
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as wins,
                        AVG(CASE WHEN mc_score > 0 AND is_correct THEN 1 
                                 WHEN mc_score > 0 THEN 0 END) as mc_accuracy,
                        AVG(CASE WHEN momentum_score > 0 AND is_correct THEN 1 
                                 WHEN momentum_score > 0 THEN 0 END) as momentum_accuracy
                    FROM prediction_tracking
                    WHERE settled_at > NOW() - INTERVAL '30 days'
                      AND is_correct IS NOT NULL
                """)
                
                row = cur.fetchone()
                if row and row['total'] > 0:
                    self.layer_performance = {
                        'total_predictions': row['total'],
                        'win_rate': row['wins'] / row['total'] if row['total'] > 0 else 0,
                        'mc_accuracy': float(row['mc_accuracy'] or 0),
                        'momentum_accuracy': float(row['momentum_accuracy'] or 0),
                    }
                    logger.info(f"✅ Historique chargé: {row['total']} prédictions, {self.layer_performance['win_rate']*100:.1f}% win rate")
                    
        except Exception as e:
            logger.debug(f"Historical performance error: {e}")
    
    def record_prediction(self, pick: QuantPick):
        """Enregistre une prédiction pour tracking"""
        if not self.conn or not self.config['meta_learning_enabled']:
            return
        
        try:
            import hashlib
            prediction_id = hashlib.md5(
                f"{pick.match_id}_{pick.market_type}_{datetime.now().isoformat()}".encode()
            ).hexdigest()[:16]
            
            pick.prediction_id = prediction_id
            pick.predicted_at = datetime.now()
            
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO prediction_tracking (
                        prediction_id, match_id, market_type,
                        predicted_prob, odds_at_prediction, mc_prob,
                        layer_score, quant_score, final_recommendation,
                        mc_score, lineup_score, market_score,
                        momentum_score, tactical_score
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (prediction_id) DO NOTHING
                """, (
                    prediction_id, pick.match_id, pick.market_type,
                    pick.mc_prob, pick.odds, pick.mc_prob,
                    pick.layer_score, pick.quant_score, pick.recommendation,
                    pick.mc_score, pick.lineup_score, pick.market_score,
                    pick.momentum_score, pick.tactical_score
                ))
                self.conn.commit()
                
        except Exception as e:
            logger.debug(f"Record prediction error: {e}")
            self.conn.rollback()
    
    def get_adjusted_weights(self) -> Dict[str, float]:
        """
        Retourne les poids ajustés selon les performances
        Layers qui performent bien = poids augmenté
        """
        adjusted = dict(LAYER_WEIGHTS)
        
        if not self.layer_performance or self.layer_performance.get('total_predictions', 0) < 30:
            return adjusted
        
        # Ajuster MC si accuracy différente de la baseline
        mc_accuracy = self.layer_performance.get('mc_accuracy', 0.5)
        if mc_accuracy > 0.55:
            adjusted['monte_carlo'] = int(LAYER_WEIGHTS['monte_carlo'] * 1.1)
        elif mc_accuracy < 0.45:
            adjusted['monte_carlo'] = int(LAYER_WEIGHTS['monte_carlo'] * 0.9)
        
        # Ajuster momentum
        mom_accuracy = self.layer_performance.get('momentum_accuracy', 0.5)
        if mom_accuracy > 0.55:
            adjusted['momentum'] = int(LAYER_WEIGHTS['momentum'] * 1.1)
        elif mom_accuracy < 0.45:
            adjusted['momentum'] = int(LAYER_WEIGHTS['momentum'] * 0.9)
        
        return adjusted
    
    def analyze_errors(self) -> Dict:
        """
        Analyse les erreurs récentes pour amélioration
        """
        if not self.conn:
            return {}
        
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT 
                        market_type,
                        COUNT(*) as total,
                        SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) as wins,
                        AVG(quant_score) as avg_score,
                        AVG(mc_prob) as avg_mc_prob
                    FROM prediction_tracking
                    WHERE settled_at > NOW() - INTERVAL '7 days'
                      AND is_correct IS NOT NULL
                    GROUP BY market_type
                    ORDER BY total DESC
                """)
                
                analysis = {}
                for row in cur.fetchall():
                    market = row['market_type']
                    win_rate = row['wins'] / row['total'] if row['total'] > 0 else 0
                    analysis[market] = {
                        'total': row['total'],
                        'win_rate': win_rate,
                        'avg_score': float(row['avg_score'] or 0),
                        'needs_improvement': win_rate < 0.45
                    }
                
                return analysis
                
        except Exception as e:
            logger.debug(f"Error analysis error: {e}")
            return {}


# Suite dans la partie 2...

# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR V10 QUANT ENGINE - PARTIE 2
# ═══════════════════════════════════════════════════════════════════════════════


class OrchestratorV10Quant:
    """
    Orchestrator V10 - Quant Engine
    "Apprend, Simule, Évolue"
    """
    
    def __init__(self):
        self.conn = None
        self.ml_model = None
        self.ml_scaler = None
        
        # Caches
        self._name_cache = {}
        self._source_to_canonical = {}
        self._canonical_to_sources = {}
        self._context_cache = {}
        
        # Engines
        self.monte_carlo = None
        self.lineup_engine = None
        self.market_engine = None
        self.meta_learning = None
        
        # Stats
        self.stats = {
            'analyzed': 0,
            'mc_simulations_total': 0,
            'steam_detected': 0,
            'traps_blocked': 0,
            'high_confidence': 0,
            'low_confidence': 0,
            'final_picks': 0,
        }
        
        # Initialize
        self._connect_db()
        self._load_name_mappings()
        self._init_engines()
        self._load_ml_model()
        
        logger.info("🎯 Orchestrator V10 Quant Engine initialisé")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # INITIALIZATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _connect_db(self):
        """Connexion base de données"""
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            logger.info("✅ Connexion DB établie")
        except Exception as e:
            logger.error(f"❌ Erreur DB: {e}")
            self.conn = None
    
    def _init_engines(self):
        """Initialise les sous-moteurs"""
        self.monte_carlo = MonteCarloEngine(QUANT_CONFIG)
        self.lineup_engine = LineupImpactEngine(self.conn, QUANT_CONFIG)
        self.market_engine = MarketDynamicsEngine(self.conn, QUANT_CONFIG)
        self.meta_learning = MetaLearningEngine(self.conn, QUANT_CONFIG)
        
        logger.info("✅ Engines initialisés (MC, Lineup, Market, MetaLearning)")
    
    def _load_ml_model(self):
        """Charge le modèle ML"""
        try:
            import joblib
            
            paths = [
                "/home/Mon_ps/backend/ml/models/best_model.joblib",
                "/home/Mon_ps/ml_smart_quant/models/best_model.joblib",
            ]
            
            for path in paths:
                if os.path.exists(path):
                    self.ml_model = joblib.load(path)
                    logger.info(f"✅ ML chargé: {path}")
                    break
                    
        except Exception as e:
            logger.warning(f"⚠️ ML non chargé: {e}")
    
    def _load_name_mappings(self):
        """
        V10 FIX - Charge les mappings BIDIRECTIONNELS
        source_name → canonical ET canonical → [sources]
        """
        if not self.conn:
            return
        
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT source_name, canonical_name, normalized_name
                    FROM team_name_mapping
                """)
                
                for row in cur.fetchall():
                    source = row['source_name']
                    canonical = row['canonical_name']
                    
                    # Source → Canonical
                    self._source_to_canonical[source.lower()] = canonical
                    
                    # Canonical → Sources (liste)
                    canon_key = canonical.lower()
                    if canon_key not in self._canonical_to_sources:
                        self._canonical_to_sources[canon_key] = set()
                    self._canonical_to_sources[canon_key].add(source)
                    self._canonical_to_sources[canon_key].add(canonical)
                
                total = len(self._source_to_canonical) + len(self._canonical_to_sources)
                logger.info(f"✅ {total} mappings bidirectionnels chargés")
                
        except Exception as e:
            logger.warning(f"⚠️ Mappings error: {e}")
    
    def _resolve_team_name(self, team_name: str) -> List[str]:
        """
        V10 FIX - Résolution bidirectionnelle des noms
        
        Entrée: "Liverpool"
        Sortie: ["Liverpool", "liverpool", "Liverpool FC", "liverpool fc", ...]
        """
        name_lower = team_name.lower().strip()
        variants = set([team_name, name_lower])
        
        # 1. Si c'est un source_name → ajouter canonical
        if name_lower in self._source_to_canonical:
            canonical = self._source_to_canonical[name_lower]
            variants.add(canonical)
            variants.add(canonical.lower())
        
        # 2. Si c'est un canonical → ajouter tous les sources
        if name_lower in self._canonical_to_sources:
            for source in self._canonical_to_sources[name_lower]:
                variants.add(source)
                variants.add(source.lower())
        
        # 3. Ajouter/retirer " FC" automatiquement
        if name_lower.endswith(' fc'):
            without_fc = name_lower[:-3].strip()
            variants.add(without_fc)
            variants.add(without_fc.title())
        else:
            variants.add(name_lower + ' fc')
            variants.add(team_name + ' FC')
        
        # 4. Variantes courantes
        common = {
            'man city': ['manchester city', 'manchester city fc'],
            'man utd': ['manchester united', 'manchester united fc'],
            'spurs': ['tottenham', 'tottenham hotspur fc'],
        }
        for short, fulls in common.items():
            if name_lower == short or name_lower in [f.lower() for f in fulls]:
                variants.update(fulls)
                variants.add(short)
        
        return list(variants)
    
    def _build_name_where(self, column: str, team_name: str) -> Tuple[str, List[str]]:
        """Construit clause WHERE pour recherche de nom"""
        variants = self._resolve_team_name(team_name)
        
        conditions = []
        params = []
        
        for v in variants[:10]:
            conditions.append(f"LOWER({column}) = %s")
            params.append(v.lower())
        
        where_clause = f"({' OR '.join(conditions)})"
        return where_clause, params
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DATA FETCHERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _get_team_intelligence(self, team_name: str) -> Optional[Dict]:
        """Récupère team_intelligence (utilise "Liverpool" sans FC)"""
        if not self.conn:
            return None
        
        try:
            where, params = self._build_name_where('team_name', team_name)
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(f"""
                    SELECT 
                        team_name, current_style, current_pressing,
                        home_strength, away_strength,
                        home_btts_rate, away_btts_rate,
                        home_over25_rate, away_over25_rate,
                        home_goals_scored_avg, away_goals_scored_avg,
                        home_goals_conceded_avg, away_goals_conceded_avg,
                        btts_tendency, goals_tendency, clean_sheet_tendency,
                        xg_for_avg, xg_against_avg,
                        confidence_overall, is_reliable
                    FROM team_intelligence
                    WHERE {where}
                    LIMIT 1
                """, params)
                
                row = cur.fetchone()
                return dict(row) if row else None
                
        except Exception as e:
            logger.debug(f"Intelligence error: {e}")
            return None
    

    def _get_competition_adjusted_stats(self, team_name: str, location: str, competition: str = None) -> Dict:
        """
        V10.2 - Calcule les stats depuis match_results filtré par type de compétition
        
        Args:
            team_name: Nom de l'équipe
            location: 'home' ou 'away'
            competition: Type de compétition (ex: 'Premier League', 'La Liga', 'League Cup')
        
        Returns:
            Dict avec goals_scored_avg, goals_conceded_avg ajustés
        """
        if not self.conn or not competition:
            return {}
        
        try:
            # Déterminer le type de compétition (ligue domestique vs coupe)
            competition_lower = competition.lower()
            
            # Mapping vers ligues domestiques
            domestic_leagues = {
                'premier league': ['premier league', 'epl'],
                'la liga': ['la liga', 'laliga'],
                'bundesliga': ['bundesliga'],
                'serie a': ['serie a'],
                'ligue 1': ['ligue 1'],
                'league cup': ['premier league', 'epl'],  # Utiliser stats PL pour coupes anglaises
                'fa cup': ['premier league', 'epl'],
                'carabao cup': ['premier league', 'epl'],
                'copa del rey': ['la liga'],
                'dfb pokal': ['bundesliga'],
                'coppa italia': ['serie a'],
                'coupe de france': ['ligue 1'],
            }
            
            # Trouver les ligues à utiliser
            league_filters = None
            for key, values in domestic_leagues.items():
                if key in competition_lower:
                    league_filters = values
                    break
            
            if not league_filters:
                # Par défaut, utiliser la compétition telle quelle
                league_filters = [competition_lower]
            
            # Construire la requête
            where, params = self._build_name_where(
                'home_team' if location == 'home' else 'away_team', 
                team_name
            )
            
            # Filtres de ligue
            league_conditions = " OR ".join([f"LOWER(league) LIKE %s" for _ in league_filters])
            league_params = [f"%{lf}%" for lf in league_filters]
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                if location == 'home':
                    cur.execute(f"""
                        SELECT 
                            AVG(score_home) as goals_scored_avg,
                            AVG(score_away) as goals_conceded_avg,
                            COUNT(*) as matches
                        FROM match_results
                        WHERE {where}
                          AND is_finished = TRUE
                          AND ({league_conditions})
                    """, params + league_params)
                else:
                    cur.execute(f"""
                        SELECT 
                            AVG(score_away) as goals_scored_avg,
                            AVG(score_home) as goals_conceded_avg,
                            COUNT(*) as matches
                        FROM match_results
                        WHERE {where}
                          AND is_finished = TRUE
                          AND ({league_conditions})
                    """, params + league_params)
                
                row = cur.fetchone()
                if row and row['matches'] and row['matches'] >= 3:
                    return {
                        'goals_scored_avg': float(row['goals_scored_avg']) if row['goals_scored_avg'] else None,
                        'goals_conceded_avg': float(row['goals_conceded_avg']) if row['goals_conceded_avg'] else None,
                        'matches': row['matches'],
                        'source': 'competition_filtered'
                    }
            
            return {}
            
        except Exception as e:
            logger.debug(f"Competition stats error: {e}")
            return {}

    def _get_team_momentum(self, team_name: str) -> Optional[Dict]:
        """Récupère team_momentum (utilise "Liverpool FC" avec FC)"""
        if not self.conn:
            return None
        
        try:
            where, params = self._build_name_where('team_name', team_name)
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(f"""
                    SELECT 
                        team_name, momentum_score,
                        goals_scored_last_5, goals_conceded_last_5,
                        last_5_results, current_streak, home_streak,
                        key_player_absent, absent_players
                    FROM team_momentum
                    WHERE {where}
                    LIMIT 1
                """, params)
                
                row = cur.fetchone()
                return dict(row) if row else None
                
        except Exception as e:
            logger.debug(f"Momentum error: {e}")
            return None
    
    def _get_team_class(self, team_name: str) -> Optional[Dict]:
        """Récupère team_class"""
        if not self.conn:
            return None
        
        try:
            where, params = self._build_name_where('team_name', team_name)
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(f"""
                    SELECT 
                        team_name, tier, league,
                        historical_strength, squad_value_millions,
                        star_players, big_game_factor,
                        home_fortress_factor, away_weakness_factor,
                        psychological_edge, playing_style
                    FROM team_class
                    WHERE {where}
                    LIMIT 1
                """, params)
                
                row = cur.fetchone()
                return dict(row) if row else None
                
        except Exception as e:
            logger.debug(f"Class error: {e}")
            return None
    
    def _get_tactical_match(self, style_a: str, style_b: str) -> Optional[Dict]:
        """Récupère tactical_matrix"""
        if not self.conn:
            return None
        
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT 
                        style_a, style_b,
                        btts_probability, over_25_probability,
                        avg_goals_total, sample_size, confidence_level
                    FROM tactical_matrix
                    WHERE LOWER(style_a) = %s AND LOWER(style_b) = %s
                    LIMIT 1
                """, (style_a.lower(), style_b.lower()))
                
                row = cur.fetchone()
                if row:
                    return dict(row)
                
                # Fallback balanced
                cur.execute("""
                    SELECT * FROM tactical_matrix
                    WHERE style_a = 'balanced' AND style_b = 'balanced'
                    LIMIT 1
                """)
                row = cur.fetchone()
                return dict(row) if row else None
                
        except Exception as e:
            logger.debug(f"Tactical error: {e}")
            return None
    
    def _get_referee_data(self, referee_name: str, league: str) -> Optional[Dict]:
        """Récupère referee_intelligence"""
        if not self.conn:
            return None
        
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                if referee_name:
                    cur.execute("""
                        SELECT 
                            referee_name, league, strictness_level,
                            avg_goals_per_game, under_over_tendency,
                            home_bias_factor, penalty_frequency
                        FROM referee_intelligence
                        WHERE LOWER(referee_name) LIKE %s
                        LIMIT 1
                    """, (f"%{referee_name.lower()}%",))
                    
                    row = cur.fetchone()
                    if row:
                        return dict(row)
                
                # Fallback moyenne ligue
                if league:
                    cur.execute("""
                        SELECT 
                            'League Average' as referee_name,
                            AVG(avg_goals_per_game) as avg_goals_per_game,
                            'neutral' as under_over_tendency
                        FROM referee_intelligence
                        WHERE LOWER(league) LIKE %s
                    """, (f"%{league.lower()}%",))
                    
                    row = cur.fetchone()
                    if row and row['avg_goals_per_game']:
                        return dict(row)
                
                return None
                
        except Exception as e:
            logger.debug(f"Referee error: {e}")
            return None
    
    def _get_h2h_data(self, home_team: str, away_team: str) -> Optional[Dict]:
        """Récupère team_head_to_head"""
        if not self.conn:
            return None
        
        try:
            home_vars = self._resolve_team_name(home_team)
            away_vars = self._resolve_team_name(away_team)
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                for hv in home_vars[:5]:
                    for av in away_vars[:5]:
                        cur.execute("""
                            SELECT 
                                team_a, team_b, total_matches,
                                team_a_wins, team_b_wins, draws,
                                btts_pct, over_25_pct, avg_total_goals
                            FROM team_head_to_head
                            WHERE (LOWER(team_a) = %s AND LOWER(team_b) = %s)
                               OR (LOWER(team_a) = %s AND LOWER(team_b) = %s)
                            LIMIT 1
                        """, (hv.lower(), av.lower(), av.lower(), hv.lower()))
                        
                        row = cur.fetchone()
                        if row:
                            return dict(row)
                
                return None
                
        except Exception as e:
            logger.debug(f"H2H error: {e}")
            return None
    
    def _get_team_traps(self, team_name: str) -> List[Dict]:
        """Récupère market_traps actifs"""
        if not self.conn:
            return []
        
        try:
            where, params = self._build_name_where('team_name', team_name)
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(f"""
                    SELECT 
                        team_name, market_type, alert_level,
                        alert_reason, alternative_market
                    FROM market_traps
                    WHERE {where}
                      AND is_active = TRUE
                      AND alert_level IN ('TRAP', 'DANGER', 'CAUTION')
                """, params)
                
                return [dict(r) for r in cur.fetchall()]
                
        except Exception as e:
            logger.debug(f"Traps error: {e}")
            return []
    
    def _get_team_profile(self, team_name: str, location: str) -> Optional[Dict]:
        """Récupère team_market_profiles"""
        if not self.conn:
            return None
        
        try:
            where, params = self._build_name_where('team_name', team_name)
            params.append(location)
            
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(f"""
                    SELECT 
                        team_name, location, best_market,
                        win_rate, profit, composite_score
                    FROM team_market_profiles
                    WHERE {where} AND location = %s
                    LIMIT 1
                """, params)
                
                row = cur.fetchone()
                return dict(row) if row else None
                
        except Exception as e:
            logger.debug(f"Profile error: {e}")
            return None
    
    def _get_reality_check(self, match_id: str) -> Optional[Dict]:
        """Récupère reality_check_results"""
        if not self.conn or not match_id:
            return None
        
        try:
            with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT 
                        match_id, reality_score, convergence_status,
                        class_score, star_player_score
                    FROM reality_check_results
                    WHERE match_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (match_id,))
                
                row = cur.fetchone()
                return dict(row) if row else None
                
        except Exception as e:
            logger.debug(f"Reality error: {e}")
            return None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PREFETCH CONTEXT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _prefetch_context(self, home_team: str, away_team: str,
                          match_id: str, league: str,
                          referee_name: str = None) -> Dict:
        """Précharge toutes les données du match"""
        
        cache_key = f"{home_team}_{away_team}_{match_id}"
        if cache_key in self._context_cache:
            return self._context_cache[cache_key]
        
        context = {
            'home_intelligence': self._get_team_intelligence(home_team),
            'away_intelligence': self._get_team_intelligence(away_team),
            'home_momentum': self._get_team_momentum(home_team),
            'away_momentum': self._get_team_momentum(away_team),
            'home_class': self._get_team_class(home_team),
            'away_class': self._get_team_class(away_team),
            'referee': self._get_referee_data(referee_name, league),
            'h2h': self._get_h2h_data(home_team, away_team),
            'reality': self._get_reality_check(match_id),
            'home_profile': self._get_team_profile(home_team, 'home'),
            'away_profile': self._get_team_profile(away_team, 'away'),
            'home_traps': self._get_team_traps(home_team),
            'away_traps': self._get_team_traps(away_team),
        }
        
        # Styles
        home_style = 'balanced'
        away_style = 'balanced'
        
        if context['home_intelligence']:
            home_style = context['home_intelligence'].get('current_style', 'balanced') or 'balanced'
        elif context['home_class']:
            home_style = context['home_class'].get('playing_style', 'balanced') or 'balanced'
            
        if context['away_intelligence']:
            away_style = context['away_intelligence'].get('current_style', 'balanced') or 'balanced'
        elif context['away_class']:
            away_style = context['away_class'].get('playing_style', 'balanced') or 'balanced'
        
        context['home_style'] = home_style
        context['away_style'] = away_style
        context['tactical'] = self._get_tactical_match(home_style, away_style)
        
        self._context_cache[cache_key] = context
        return context
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SCORE CALCULATIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _calculate_mc_score(self, pick: QuantPick, mc_result: MonteCarloResult) -> int:
        """Score basé sur Monte Carlo"""
        
        market = pick.market_type.lower()
        
        # Mapper marché vers probabilité MC
        if 'btts_yes' in market:
            mc_prob = mc_result.btts_prob
        elif 'btts_no' in market:
            mc_prob = 1 - mc_result.btts_prob
        elif 'over_25' in market:
            mc_prob = mc_result.over_25_prob
        elif 'under_25' in market:
            mc_prob = 1 - mc_result.over_25_prob
        elif 'over_35' in market:
            mc_prob = mc_result.over_35_prob
        elif 'over_15' in market:
            mc_prob = mc_result.over_15_prob
        elif 'home' in market:
            mc_prob = mc_result.home_win_prob
        elif 'away' in market:
            mc_prob = mc_result.away_win_prob
        elif 'draw' in market:
            mc_prob = mc_result.draw_prob
        else:
            mc_prob = 0.5
        
        pick.mc_prob = mc_prob
        pick.mc_edge = mc_prob - pick.implied_prob
        pick.mc_confidence = mc_result.confidence_score
        
        # SMART HYBRID SCORING 2.0
        # Score continu: Edge 5% = 10pts, Edge 10% = 20pts
        base_score = pick.mc_edge * 200
        confidence_factor = mc_result.confidence_score
        
        # Sweet Spot bonus (3-8% = +25%), Suspect penalty (>15% = -20%)
        if 0.03 <= pick.mc_edge <= 0.08:
            sweet_spot = 1.25
        elif pick.mc_edge > 0.15:
            sweet_spot = 0.8
        else:
            sweet_spot = 1.0
        
        score = int(base_score * confidence_factor * sweet_spot)
        
        return max(-LAYER_WEIGHTS['monte_carlo'], min(LAYER_WEIGHTS['monte_carlo'], score))
    
    def _calculate_lineup_score(self, pick: QuantPick, lineup: LineupImpact) -> int:
        """Score basé sur Lineup Impact"""
        
        score = 0
        market = pick.market_type.lower()
        
        total_adj = lineup.home_xg_adjustment + lineup.away_xg_adjustment
        
        if 'btts_yes' in market or 'over' in market:
            # Plus de xG = bon pour BTTS/Over
            if total_adj > 0.15:
                score = 12
            elif total_adj > 0.05:
                score = 6
            elif total_adj < -0.15:
                score = -8
        
        elif 'btts_no' in market or 'under' in market:
            # Moins de xG = bon pour Under
            if total_adj < -0.15:
                score = 10
            elif total_adj < -0.05:
                score = 5
            elif total_adj > 0.15:
                score = -6
        
        # Derby boost
        if lineup.is_derby:
            if 'btts_yes' in market or 'over' in market:
                score += 4
        
        return max(-LAYER_WEIGHTS['lineup_impact'], min(LAYER_WEIGHTS['lineup_impact'], score))
    
    def _calculate_market_score(self, pick: QuantPick, dynamics: MarketDynamics) -> int:
        """Score basé sur Market Dynamics (Steam, CLV)"""
        
        score = 0
        
        if dynamics.is_steam:
            self.stats['steam_detected'] += 1
            
            if dynamics.steam_direction == 'shortening':
                score = 12  # Sharp money avec nous
                pick.reasons.append(f"🔥 Steam détecté ({dynamics.steam_magnitude:.1f}%)")
            else:
                score = -8  # Sharp contre
                pick.warnings.append(f"⚠️ Steam contre ({dynamics.steam_magnitude:.1f}%)")
        
        # CLV potential
        if dynamics.clv_potential > 0.05:
            score += 5
        
        # Consensus bookmakers
        if dynamics.bookmakers_consensus > 0.8:
            score += 3
        
        pick.steam_signal = dynamics.sharp_money_signal
        pick.clv_expected = dynamics.clv_potential
        
        return max(-LAYER_WEIGHTS['market_dynamics'], min(LAYER_WEIGHTS['market_dynamics'], score))
    
    def _calculate_momentum_score(self, pick: QuantPick, context: Dict) -> int:
        """Score basé sur momentum"""
        score = 0
        
        home_mom = context.get('home_momentum')
        away_mom = context.get('away_momentum')
        
        if not home_mom and not away_mom:
            return 0
        
        home_score = home_mom.get('momentum_score', 50) if home_mom else 50
        away_score = away_mom.get('momentum_score', 50) if away_mom else 50
        
        market = pick.market_type.lower()
        
        if 'btts_yes' in market or 'over' in market:
            if home_score >= 70 and away_score >= 70:
                score = 10
                pick.reasons.append(f"🔥 Momentum élevé: {home_score}/{away_score}")
            elif home_score >= 60 and away_score >= 60:
                score = 6
        
        elif 'btts_no' in market or 'under' in market:
            if home_score <= 40 or away_score <= 40:
                score = 8
        
        return max(-LAYER_WEIGHTS['momentum'], min(LAYER_WEIGHTS['momentum'], score))
    
    def _calculate_tactical_score(self, pick: QuantPick, context: Dict) -> int:
        """Score basé sur tactical_matrix"""
        score = 0
        
        tactical = context.get('tactical')
        if not tactical:
            return 0
        
        market = pick.market_type.lower()
        
        btts_prob = float(tactical.get('btts_probability', 50) or 50)
        over25_prob = float(tactical.get('over_25_probability', 50) or 50)
        sample = tactical.get('sample_size', 0) or 0
        
        conf_mult = 1.0 if sample >= 10 else 0.6
        
        if 'btts_yes' in market:
            if btts_prob >= 50:
                score = int(8 * conf_mult)
        elif 'btts_no' in market:
            if btts_prob <= 45:
                score = int(8 * conf_mult)
        elif 'over_25' in market:
            if over25_prob >= 50:
                score = int(8 * conf_mult)
        elif 'under_25' in market:
            if over25_prob <= 45:
                score = int(8 * conf_mult)
        
        return max(-LAYER_WEIGHTS['tactical'], min(LAYER_WEIGHTS['tactical'], score))
    
    def _calculate_intelligence_score(self, pick: QuantPick, context: Dict) -> int:
        """Score basé sur team_intelligence tendencies"""
        score = 0
        
        home_intel = context.get('home_intelligence')
        away_intel = context.get('away_intelligence')
        
        if not home_intel and not away_intel:
            return 0
        
        market = pick.market_type.lower()
        
        home_btts = float(home_intel.get('btts_tendency', 50) or 50) if home_intel else 50
        away_btts = float(away_intel.get('btts_tendency', 50) or 50) if away_intel else 50
        avg_btts = (home_btts + away_btts) / 2
        
        home_goals = float(home_intel.get('goals_tendency', 50) or 50) if home_intel else 50
        away_goals = float(away_intel.get('goals_tendency', 50) or 50) if away_intel else 50
        avg_goals = (home_goals + away_goals) / 2
        
        if 'btts_yes' in market:
            if avg_btts >= 65:
                score = 8
            elif avg_btts >= 50:
                score = 4
        elif 'btts_no' in market:
            if avg_btts <= 40:
                score = 8
        elif 'over' in market:
            if avg_goals >= 65:
                score = 8
            elif avg_goals >= 50:
                score = 4
        elif 'under' in market:
            if avg_goals <= 40:
                score = 8
        
        return max(-LAYER_WEIGHTS['intelligence'], min(LAYER_WEIGHTS['intelligence'], score))
    
    def _calculate_class_score(self, pick: QuantPick, context: Dict) -> int:
        """Score basé sur team_class"""
        score = 0
        
        home_class = context.get('home_class')
        away_class = context.get('away_class')
        
        if not home_class and not away_class:
            return 0
        
        tier_values = {'A': 4, 'B': 3, 'C': 2, 'D': 1}
        
        home_tier = home_class.get('tier', 'C') if home_class else 'C'
        away_tier = away_class.get('tier', 'C') if away_class else 'C'
        
        tier_diff = abs(tier_values.get(home_tier, 2) - tier_values.get(away_tier, 2))
        
        market = pick.market_type.lower()
        
        if 'btts_yes' in market or 'over' in market:
            if tier_diff == 0:
                score = 6  # Match équilibré
        elif 'btts_no' in market or 'under' in market:
            if tier_diff >= 2:
                score = 5  # Domination
        
        return max(-LAYER_WEIGHTS['class'], min(LAYER_WEIGHTS['class'], score))
    
    def _calculate_referee_score(self, pick: QuantPick, context: Dict) -> int:
        """Score basé sur referee_intelligence"""
        score = 0
        
        ref = context.get('referee')
        if not ref:
            return 0
        
        market = pick.market_type.lower()
        
        avg_goals = float(ref.get('avg_goals_per_game', 2.5) or 2.5)
        tendency = ref.get('under_over_tendency', 'neutral')
        
        if 'btts_yes' in market or 'over' in market:
            if tendency == 'over':
                score = 7
                pick.reasons.append(f"⚖️ Arbitre pro-over ({avg_goals:.2f} buts)")
            elif avg_goals >= 2.8:
                score = 4
        elif 'btts_no' in market or 'under' in market:
            if tendency == 'under':
                score = 7
        
        return max(-LAYER_WEIGHTS['referee'], min(LAYER_WEIGHTS['referee'], score))
    
    def _calculate_h2h_score(self, pick: QuantPick, context: Dict) -> int:
        """Score basé sur H2H"""
        score = 0
        
        h2h = context.get('h2h')
        if not h2h:
            return 0
        
        total = h2h.get('total_matches', 0) or 0
        if total < 2:
            return 0
        
        market = pick.market_type.lower()
        
        btts_pct = float(h2h.get('btts_pct', 50) or 50)
        over25_pct = float(h2h.get('over_25_pct', 50) or 50)
        
        conf = 1.0 if total >= 5 else 0.6
        
        if 'btts_yes' in market:
            if btts_pct >= 70:
                score = int(8 * conf)
                pick.reasons.append(f"📜 H2H BTTS: {btts_pct:.0f}%")
        elif 'btts_no' in market:
            if btts_pct <= 35:
                score = int(8 * conf)
        elif 'over_25' in market:
            if over25_pct >= 70:
                score = int(8 * conf)
        elif 'under_25' in market:
            if over25_pct <= 35:
                score = int(8 * conf)
        
        return max(-LAYER_WEIGHTS['h2h'], min(LAYER_WEIGHTS['h2h'], score))
    
    def _calculate_reality_score(self, pick: QuantPick, context: Dict) -> int:
        """Score basé sur Reality Check"""
        score = 0
        
        reality = context.get('reality')
        if not reality:
            return 0
        
        convergence = reality.get('convergence_status', '')
        
        if convergence == 'strong_convergence':
            score = 5
        elif convergence == 'divergence':
            score = -3
            pick.warnings.append("⚠️ Divergence Reality Check")
        
        return max(-LAYER_WEIGHTS['reality'], min(LAYER_WEIGHTS['reality'], score))
    
    def _calculate_profile_score(self, pick: QuantPick, context: Dict) -> int:
        """Score basé sur team_market_profiles"""
        score = 0
        
        home_prof = context.get('home_profile')
        away_prof = context.get('away_profile')
        
        if not home_prof and not away_prof:
            return 0
        
        market = pick.market_type.lower()
        
        home_best = home_prof.get('best_market', '').lower() if home_prof else ''
        away_best = away_prof.get('best_market', '').lower() if away_prof else ''
        
        if home_best == market and away_best == market:
            score = 5
            pick.reasons.append(f"🎯 Consensus profil")
        elif home_best == market or away_best == market:
            score = 2
        
        return max(-LAYER_WEIGHTS['profile'], min(LAYER_WEIGHTS['profile'], score))
    
    def _check_trap(self, pick: QuantPick, context: Dict) -> bool:
        """Vérifie si le pick est bloqué par un trap"""
        home_traps = context.get('home_traps', [])
        away_traps = context.get('away_traps', [])
        
        market = pick.market_type.lower()
        
        for trap in home_traps + away_traps:
            if trap.get('market_type', '').lower() == market:
                pick.is_trap = True
                pick.trap_reason = trap.get('alert_reason', 'Trap détecté')
                self.stats['traps_blocked'] += 1
                return True
        
        return False
    
    def _calculate_sweet_spot(self, pick: QuantPick) -> int:
        """Bonus sweet spot"""
        market = pick.market_type.lower()
        
        if market in SWEET_SPOTS:
            spot = SWEET_SPOTS[market]
            if spot['min'] <= pick.odds <= spot['max']:
                return spot['bonus']
        
        return 0
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DATA COVERAGE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _calculate_data_coverage(self, pick: QuantPick, context: Dict) -> Tuple[float, int]:
        """Calcule le pourcentage de layers actifs"""
        layers = 0
        total = 10
        
        if pick.mc_score != 0: layers += 1
        if pick.lineup_score != 0: layers += 1
        if pick.market_score != 0: layers += 1
        if pick.momentum_score != 0 or context.get('home_momentum'): layers += 1
        if pick.tactical_score != 0 or context.get('tactical'): layers += 1
        if pick.intelligence_score != 0 or context.get('home_intelligence'): layers += 1
        if pick.class_score != 0 or context.get('home_class'): layers += 1
        if pick.referee_score != 0 or context.get('referee'): layers += 1
        if pick.h2h_score != 0 or context.get('h2h'): layers += 1
        if pick.reality_score != 0 or context.get('reality'): layers += 1
        
        return layers / total, layers
    
    # ═══════════════════════════════════════════════════════════════════════════
    # KELLY & RECOMMENDATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _calculate_kelly(self, pick: QuantPick) -> float:
        """Kelly Criterion"""
        if pick.odds <= 1 or pick.mc_edge <= 0:
            return 0.0
        
        win_prob = pick.mc_prob
        b = pick.odds - 1
        q = 1 - win_prob
        
        kelly = (b * win_prob - q) / b
        
        # Kelly fractionné (25%)
        return max(0, min(kelly * 0.25, 0.10))
    
    def _get_recommendation(self, pick: QuantPick) -> str:
        """Génère la recommandation"""
        score = pick.final_score
        coverage = pick.data_coverage
        
        suffix = " ⚠️Low Data" if coverage < 0.4 else ""
        
        if pick.is_trap:
            return f"🚫 BLOCKED: {pick.trap_reason}"
        
        # ═══════════════════════════════════════════════════════
        # NOUVEAUX SEUILS HYBRIDES V2.0
        # Plus granulaires, favorise Volume + EV positive
        # ═══════════════════════════════════════════════════════
        
        if score >= 75 and coverage >= 0.6:
            pick.confidence_level = "ELITE"
            return f"💎 ELITE VALUE{suffix}"
        elif score >= 60:
            pick.confidence_level = "TRÈS HAUTE"
            return f"🟢🟢 STRONG BET{suffix}"
        elif score >= 45:
            pick.confidence_level = "HAUTE"
            return f"🟢 GOOD BET{suffix}"
        elif score >= 30:
            pick.confidence_level = "MOYENNE"
            return f"🟡 VALUE LEAN{suffix}"
        elif score >= 18:
            pick.confidence_level = "BASSE"
            return f"⚪ WATCH{suffix}"
        else:
            pick.confidence_level = "TRÈS BASSE"
            return f"🔴 SKIP{suffix}"

# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR V10 QUANT ENGINE - PARTIE 3 (MAIN ANALYSIS)
# ═══════════════════════════════════════════════════════════════════════════════

    # ═══════════════════════════════════════════════════════════════════════════
    # MAIN ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def analyze_match(self, match_data: Dict, referee_name: str = None) -> List[QuantPick]:
        """
        Analyse complète d'un match avec Quant Engine
        
        Pipeline:
        1. Prefetch context DB
        2. Monte Carlo simulation (10K)
        3. Lineup Impact calculation
        4. Market Dynamics analysis
        5. Layer scores calculation
        6. Final Quant Score
        7. Meta-learning tracking
        """
        picks = []
        
        home_team = match_data.get('home_team', '')
        away_team = match_data.get('away_team', '')
        match_id = match_data.get('match_id', '')
        league = match_data.get('league', '')
        odds = match_data.get('odds', {})
        
        # 1. Prefetch context
        context = self._prefetch_context(home_team, away_team, match_id, league, referee_name)
        
        # 2. Lineup Impact (calcule xG ajustés)
        lineup_impact = self.lineup_engine.calculate_impact(
            home_team, away_team,
            context.get('home_intelligence'),
            context.get('away_intelligence'),
            context.get('home_class'),
            context.get('away_class'),
            context.get('home_momentum'),
            context.get('away_momentum'),
            match_data  # Pour derby detection etc.
        )
        
        # 3. Monte Carlo simulation
        mc_result = self.monte_carlo.simulate_match(
            lineup_impact.home_adjusted_xg,
            lineup_impact.away_adjusted_xg,
            context.get('home_style', 'balanced'),
            context.get('away_style', 'balanced'),
            match_data
        )
        
        self.stats['mc_simulations_total'] += self.monte_carlo.n_sims
        
        # Marchés à analyser
        markets = [
            ('btts_yes', odds.get('btts_yes')),
            ('btts_no', odds.get('btts_no')),
            ('over_25', odds.get('over_25')),
            ('under_25', odds.get('under_25')),
            ('over_35', odds.get('over_35')),
            ('over_15', odds.get('over_15')),
            ('home', odds.get('home')),
            ('away', odds.get('away')),
            ('draw', odds.get('draw')),
        ]
        
        for market_type, market_odds in markets:
            if not market_odds or market_odds <= 1:
                continue
            
            pick = QuantPick(
                match_id=match_id,
                home_team=home_team,
                away_team=away_team,
                league=league,
                market_type=market_type,
                odds=market_odds,
                implied_prob=1 / market_odds,
            )
            
            pick.mc_result = mc_result
            pick.lineup_impact = lineup_impact
            pick.xg_adjusted_home = lineup_impact.home_adjusted_xg
            pick.xg_adjusted_away = lineup_impact.away_adjusted_xg
            
            # Check trap first
            if self._check_trap(pick, context):
                pick.final_score = 0
                pick.recommendation = self._get_recommendation(pick)
                picks.append(pick)
                self.stats['analyzed'] += 1
                continue
            
            # 4. Market Dynamics
            market_dynamics = self.market_engine.analyze_market(
                match_id, market_type, market_odds
            )
            pick.market_dynamics = market_dynamics
            
            # 5. Calculate all scores
            pick.mc_score = self._calculate_mc_score(pick, mc_result)
            pick.lineup_score = self._calculate_lineup_score(pick, lineup_impact)
            pick.market_score = self._calculate_market_score(pick, market_dynamics)
            pick.momentum_score = self._calculate_momentum_score(pick, context)
            pick.tactical_score = self._calculate_tactical_score(pick, context)
            pick.intelligence_score = self._calculate_intelligence_score(pick, context)
            pick.class_score = self._calculate_class_score(pick, context)
            pick.referee_score = self._calculate_referee_score(pick, context)
            pick.h2h_score = self._calculate_h2h_score(pick, context)
            pick.reality_score = self._calculate_reality_score(pick, context)
            pick.profile_score = self._calculate_profile_score(pick, context)
            pick.sweet_spot_score = self._calculate_sweet_spot(pick)
            
            # 6. Aggregate scores
            pick.layer_score = (
                pick.mc_score +
                pick.lineup_score +
                pick.market_score +
                pick.momentum_score +
                pick.tactical_score +
                pick.intelligence_score +
                pick.class_score +
                pick.referee_score +
                pick.h2h_score +
                pick.reality_score +
                pick.profile_score +
                pick.sweet_spot_score
            )
            
            # Quant Score (pondéré par MC confidence)
            pick.quant_score = pick.layer_score * (0.7 + 0.3 * pick.mc_confidence)
            pick.final_score = int(pick.quant_score)
            
            # Data coverage
            pick.data_coverage, pick.layers_active = self._calculate_data_coverage(pick, context)
            
            if pick.data_coverage >= 0.5:
                self.stats['high_confidence'] += 1
            else:
                self.stats['low_confidence'] += 1
            
            # Kelly
            pick.kelly_fraction = self._calculate_kelly(pick)
            
            # Recommendation
            pick.recommendation = self._get_recommendation(pick)
            
            # 7. Meta-learning tracking
            if QUANT_CONFIG['meta_learning_enabled'] and pick.final_score >= 50:
                self.meta_learning.record_prediction(pick)
            
            picks.append(pick)
            self.stats['analyzed'] += 1
        
        return picks
    
    def filter_best_picks(self, picks: List[QuantPick], max_picks: int = 5) -> List[QuantPick]:
        """Filtre et trie les meilleurs picks"""
        valid = [p for p in picks if not p.is_trap and p.final_score > 0]
        
        # Trier par score puis par couverture
        valid.sort(key=lambda p: (p.final_score, p.data_coverage, p.mc_confidence), reverse=True)
        
        self.stats['final_picks'] = min(len(valid), max_picks)
        
        return valid[:max_picks]
    
    def print_summary(self):
        """Affiche résumé"""
        print("\n" + "="*70)
        print("📊 ORCHESTRATOR V10 QUANT ENGINE - RÉSUMÉ")
        print("="*70)
        for key, value in self.stats.items():
            label = key.replace('_', ' ').title()
            print(f"   {label:<35} {value}")
        print("="*70)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("="*70)
    print("🎯 ORCHESTRATOR V10 - QUANT ENGINE")
    print("="*70)
    print('"Apprend, Simule, Évolue"')
    print("="*70)
    print()
    print("🔬 COMPOSANTS:")
    print("   • Monte Carlo Engine    - 10,000 simulations/match")
    print("   • Lineup Impact Engine  - xG ajustés selon absences")
    print("   • Market Dynamics       - Steam detection, CLV")
    print("   • Meta-Learning         - Auto-tune des poids")
    print()
    print("📊 SOURCES DE DONNÉES:")
    print("   • team_intelligence     - xG, tendencies, styles")
    print("   • team_momentum         - forme, streaks")
    print("   • team_class            - tier, star_players")
    print("   • odds_history (237K)   - mouvements de cotes")
    print("   • tactical_matrix       - style matchups")
    print("   • referee_intelligence  - arbitres")
    print("   • team_head_to_head     - H2H")
    print("   • market_traps          - pièges")
    print("="*70)
    
    orchestrator = OrchestratorV10Quant()
    
    # Test match
    test_match = {
        'match_id': 'test_liverpool_city_v10',
        'home_team': 'Liverpool',
        'away_team': 'Manchester City',
        'league': 'Premier League',
        'odds': {
            'home': 2.80,
            'draw': 3.40,
            'away': 2.50,
            'btts_yes': 1.65,
            'btts_no': 2.10,
            'over_25': 1.70,
            'under_25': 2.05,
            'over_35': 2.40,
        }
    }
    
    print(f"\n📌 Test: {test_match['home_team']} vs {test_match['away_team']}")
    print("-"*70)
    
    picks = orchestrator.analyze_match(test_match, referee_name="Michael Oliver")
    best_picks = orchestrator.filter_best_picks(picks, max_picks=5)
    
    print(f"\n🎯 TOP {len(best_picks)} PICKS (Quant Analysis):")
    print("-"*70)
    
    for i, pick in enumerate(best_picks, 1):
        ss = "⭐" if pick.sweet_spot_score > 0 else ""
        cov_icon = "🟢" if pick.data_coverage >= 0.5 else "🟡" if pick.data_coverage >= 0.4 else "🔴"
        
        print(f"\n#{i} {pick.market_type.upper()} @ {pick.odds} {ss}")
        print(f"   Quant Score: {pick.final_score} | Layer: {pick.layer_score}")
        print(f"   📊 Coverage: {cov_icon} {pick.data_coverage*100:.0f}% ({pick.layers_active}/10 layers)")
        print()
        print(f"   🎲 Monte Carlo ({orchestrator.monte_carlo.n_sims} sims):")
        print(f"      Prob: {pick.mc_prob*100:.1f}% | Edge: {pick.mc_edge*100:+.1f}% | Conf: {pick.mc_confidence*100:.0f}%")
        print(f"      xG ajustés: {pick.xg_adjusted_home:.2f} vs {pick.xg_adjusted_away:.2f}")
        print()
        print(f"   📈 Scores:")
        print(f"      MC={pick.mc_score} | Lineup={pick.lineup_score} | Market={pick.market_score}")
        print(f"      Mom={pick.momentum_score} | Tac={pick.tactical_score} | Intel={pick.intelligence_score}")
        print(f"      Class={pick.class_score} | Ref={pick.referee_score} | H2H={pick.h2h_score}")
        print(f"      Reality={pick.reality_score} | Profile={pick.profile_score} | SS={pick.sweet_spot_score}")
        print()
        print(f"   💰 Kelly: {pick.kelly_fraction:.2f}%")
        print(f"   ➜ {pick.recommendation}")
        
        if pick.reasons:
            for reason in pick.reasons[:3]:
                print(f"      {reason}")
        if pick.warnings:
            for warning in pick.warnings[:2]:
                print(f"      {warning}")
    
    orchestrator.print_summary()
    
    # Afficher distribution Monte Carlo pour le premier pick
    if best_picks and best_picks[0].mc_result:
        print("\n📊 Distribution des scores (Monte Carlo):")
        mc = best_picks[0].mc_result
        top_scores = sorted(mc.score_distribution.items(), 
                           key=lambda x: x[1], reverse=True)[:5]
        for score, count in top_scores:
            pct = count / mc.n_simulations * 100
            bar = "█" * int(pct / 2)
            print(f"   {score}: {bar} {pct:.1f}%")
    
    print("\n✅ Orchestrator V10 Quant Engine prêt!")


if __name__ == "__main__":
    main()

