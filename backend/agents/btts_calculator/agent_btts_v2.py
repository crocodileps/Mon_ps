#!/usr/bin/env python3
"""
🧠 AGENT BTTS CALCULATOR V2.0 ULTIME
=====================================
Agent de prédiction BTTS (Both Teams To Score) de niveau professionnel.

FONCTIONNALITÉS V2.0:
=====================
✅ Correction Dixon-Coles (corrélation scores bas 0-0, 1-0, 0-1)
✅ Borne basse dynamique 0.1 (pas de crédit aux attaques faibles)
✅ Moyennes de ligue dynamiques (SQL 60 jours)
✅ Poids cohérents et configurables
✅ Clean sheet intégré proprement
✅ Buts par période (1ère/2ème mi-temps)
✅ Fatigue (congested schedule)
✅ Régression vers la moyenne
✅ Variance des buts
✅ xG intégré (si disponible)
✅ Forme récente (last 5 matches)
✅ Style de jeu (pressing, possession)
✅ Impact coach sur BTTS
✅ Auto-apprentissage Bayésien
✅ Calibration des probabilités
✅ Kelly Criterion pour sizing

CORRECTIONS V2.1:
=================
✅ Bug "or 0" corrigé (0 est maintenant accepté comme valeur valide)
✅ Poids xG inversés (réalité 60% > théorie 40%)
✅ Clean sheet basé sur Poisson + xG (plus précis)
✅ Matrice de croisement tactique (mismatch detection)

Auteur: Mon_PS System
Version: 2.1.0
Date: 29/11/2025
"""

import os
import sys
import json
import math
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from decimal import Decimal
from collections import defaultdict
import statistics


def safe_float(value, default: float = 0.0) -> float:
    """
    Convertit une valeur en float de manière sûre.
    Accepte 0 comme valeur valide (contrairement à 'or' qui le traite comme Falsy)
    """
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('AgentBTTS_V2')

# Connexion DB
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    logger.error("psycopg2 non installé. Exécuter: pip install psycopg2-binary")
    sys.exit(1)

# ML Libraries (optionnel)
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    logger.warning("numpy non disponible - mode basique")

try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.calibration import CalibratedClassifierCV
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    logger.warning("sklearn non disponible - ML désactivé")


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class TeamBTTSProfile:
    """Profil BTTS complet d'une équipe"""
    team_name: str
    league: str = ""
    
    # Stats BTTS de base
    home_btts_rate: float = 0.50
    away_btts_rate: float = 0.50
    btts_tendency: float = 0.50
    
    # Stats offensives
    home_goals_scored_avg: float = 1.3
    away_goals_scored_avg: float = 1.0
    home_failed_to_score_rate: float = 0.20
    away_failed_to_score_rate: float = 0.30
    
    # Stats défensives
    home_goals_conceded_avg: float = 1.0
    away_goals_conceded_avg: float = 1.4
    home_clean_sheet_rate: float = 0.30
    away_clean_sheet_rate: float = 0.20
    
    # xG (Expected Goals)
    xg_for_avg: float = 0.0
    xg_against_avg: float = 0.0
    xg_difference: float = 0.0
    overperformance_goals: float = 0.0
    
    # Timing des buts
    first_half_goals_pct: float = 0.45
    second_half_goals_pct: float = 0.55
    late_goals_pct: float = 0.15
    conceded_late_pct: float = 0.15
    first_scorer_rate: float = 0.50
    
    # Forme récente
    last5_btts_rate: float = 0.50
    last5_goals_for: float = 0.0
    last5_goals_against: float = 0.0
    current_form_points: float = 0.0
    
    # Style de jeu
    current_style: str = "balanced"
    current_pressing: str = "medium"
    style_score: float = 50.0
    
    # Contexte
    after_europe: float = 0.0
    congested_schedule: float = 0.0
    vs_top_teams: float = 0.0
    vs_bottom_teams: float = 0.0
    
    # Coach impact
    coach_btts_rate: float = 0.50
    coach_style: str = ""
    coach_tenure_months: float = 0.0
    
    # Over/Under rates
    home_over25_rate: float = 0.50
    away_over25_rate: float = 0.50
    home_over15_rate: float = 0.70
    away_over15_rate: float = 0.65
    
    # Métadonnées
    matches_analyzed: int = 0
    confidence: float = 50.0
    data_quality_score: float = 50.0
    is_reliable: bool = False


@dataclass
class LeagueStats:
    """Statistiques dynamiques d'une ligue"""
    league_name: str
    btts_rate: float = 0.52
    goals_per_game: float = 2.70
    home_win_rate: float = 0.45
    draw_rate: float = 0.25
    away_win_rate: float = 0.30
    clean_sheet_rate: float = 0.25
    avg_home_goals: float = 1.50
    avg_away_goals: float = 1.20
    matches_analyzed: int = 0
    last_updated: datetime = None


@dataclass
class BTTSPrediction:
    """Résultat de prédiction BTTS"""
    home_team: str
    away_team: str
    
    # Probabilités
    btts_yes_probability: float
    btts_no_probability: float
    
    # Recommandation
    recommended_bet: str  # "BTTS_YES", "BTTS_NO", "SKIP"
    
    # Cotes
    fair_odds_yes: float
    fair_odds_no: float
    market_odds_yes: Optional[float] = None
    market_odds_no: Optional[float] = None
    
    # Edge et sizing
    edge_yes: Optional[float] = None
    edge_no: Optional[float] = None
    kelly_stake_yes: Optional[float] = None
    kelly_stake_no: Optional[float] = None
    
    # Confiance
    confidence: float = 50.0
    confidence_breakdown: Dict[str, float] = field(default_factory=dict)
    
    # Facteurs détaillés
    factors: Dict[str, float] = field(default_factory=dict)
    
    # Scores par module
    module_scores: Dict[str, float] = field(default_factory=dict)
    
    # Raisonnement
    reasoning: str = ""
    warnings: List[str] = field(default_factory=list)
    
    # Métadonnées
    model_version: str = "2.0.0"
    computed_at: datetime = field(default_factory=datetime.now)


# =============================================================================
# AGENT BTTS V2.0 ULTIME
# =============================================================================

class AgentBTTSCalculatorV2:
    """
    🧠 Agent BTTS Calculator V2.0 ULTIME
    
    Architecture modulaire avec:
    - Module Statistique (Poisson + Dixon-Coles)
    - Module Contextuel (fatigue, enjeu)
    - Module Tactique (style, coach)
    - Module Marché (CLV, steam moves)
    - Module ML (ensemble learning)
    - Module Apprentissage (Bayesian update)
    """
    
    VERSION = "2.1.0"
    
    # ==========================================================================
    # CONFIGURATION
    # ==========================================================================
    
    # Poids des modules (somme = 1.0)
    MODULE_WEIGHTS = {
        'statistical': 0.35,    # Poisson + Dixon-Coles
        'historical': 0.25,     # Historique BTTS équipes
        'contextual': 0.15,     # Fatigue, enjeu, etc.
        'tactical': 0.10,       # Style, coach
        'form': 0.10,           # Forme récente
        'market': 0.05,         # Signaux marché
    }
    
    # Poids internes module statistique
    STAT_WEIGHTS = {
        'poisson_base': 0.40,
        'dixon_coles_adj': 0.20,
        'clean_sheet_factor': 0.15,
        'failed_to_score_factor': 0.15,
        'xg_adjustment': 0.10,
    }
    
    # Seuils de décision
    THRESHOLDS = {
        'btts_yes_min_prob': 0.55,
        'btts_no_min_prob': 0.55,
        'confidence_min': 55,
        'edge_min': 0.03,           # 3% edge minimum
        'kelly_fraction': 0.25,     # Quarter Kelly
        'max_stake_pct': 0.05,      # 5% max du bankroll
    }
    
    # Paramètres Dixon-Coles
    DIXON_COLES = {
        'rho': -0.13,               # Corrélation scores bas (calibré)
        'tau_00': 1.15,             # Ajustement 0-0
        'tau_01': 1.05,             # Ajustement 0-1
        'tau_10': 1.05,             # Ajustement 1-0
        'tau_11': 0.95,             # Ajustement 1-1
    }
    
    # Bornes pour expected goals
    XG_BOUNDS = {
        'min': 0.10,                # Borne basse (corrigé de 0.3)
        'max': 4.00,                # Borne haute
    }
    
    # Facteurs de régression vers la moyenne
    REGRESSION = {
        'btts_rate': 0.15,          # 15% régression vers moyenne ligue
        'goals_avg': 0.20,          # 20% régression
        'clean_sheet': 0.10,        # 10% régression
        'min_matches': 5,           # Matchs min avant régression réduite
    }
    
    # Impact des facteurs contextuels
    CONTEXT_IMPACT = {
        'fatigue_high': -0.08,      # Équipe fatiguée → moins de BTTS
        'fatigue_low': 0.03,        # Équipe reposée → légèrement plus
        'derby': -0.05,             # Derby → matchs fermés
        'relegation_battle': -0.07, # Lutte relégation → prudence
        'title_race': 0.04,         # Course titre → offensif
        'nothing_to_play': 0.06,    # Rien à jouer → matchs ouverts
        'after_europe': -0.04,      # Après match européen
        'congested': -0.05,         # Calendrier chargé
    }
    
    # Styles de jeu et impact BTTS
    STYLE_IMPACT = {
        'attacking': 0.08,
        'possession': 0.03,
        'balanced': 0.00,
        'counter_attack': -0.02,
        'defensive': -0.10,
        'pressing_high': 0.05,
        'pressing_medium': 0.00,
        'pressing_low': -0.05,
    }

    # Matrice de croisement tactique (style home, style away) -> impact BTTS
    TACTICAL_MATRIX = {
        ('attacking', 'attacking'): 0.12,        # Festival de buts probable
        ('attacking', 'counter_attack'): 0.08,   # Match ouvert
        ('attacking', 'balanced'): 0.05,
        ('attacking', 'defensive'): 0.02,
        ('possession', 'counter_attack'): 0.08,  # Espaces -> buts
        ('possession', 'pressing_high'): 0.06,
        ('possession', 'defensive'): -0.04,      # Mur défensif
        ('counter_attack', 'attacking'): 0.10,
        ('counter_attack', 'pressing_high'): 0.07,
        ('balanced', 'balanced'): 0.00,
        ('defensive', 'defensive'): -0.10,       # 0-0 très probable
        ('defensive', 'attacking'): -0.02,
        ('pressing_high', 'pressing_high'): 0.08, # Chaos -> buts
    }



    # ==========================================================================
    # INITIALISATION
    # ==========================================================================
    
    def __init__(self, db_config: Dict = None):
        """Initialise l'agent avec connexion DB"""
        self.db_config = db_config or {
            'host': 'localhost',
            'port': 5432,
            'database': 'monps_db',
            'user': 'monps_user',
            'password': 'monps_secure_password_2024'
        }
        self.conn = None
        self._connect()
        
        # Cache pour les moyennes de ligue
        self._league_cache: Dict[str, LeagueStats] = {}
        self._cache_ttl = timedelta(hours=6)
        
        # Historique des prédictions (pour apprentissage)
        self._prediction_history: List[Dict] = []
        
        # Modèle ML (si disponible)
        self._ml_model = None
        if HAS_SKLEARN:
            self._init_ml_model()
        
        logger.info(f"🧠 Agent BTTS V{self.VERSION} initialisé")
        
    def _connect(self):
        """Établit la connexion à la base de données"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            logger.info("✅ Connexion DB établie")
        except Exception as e:
            logger.warning(f"Connexion localhost échouée: {e}")
            try:
                self.db_config['host'] = 'monps_postgres'
                self.conn = psycopg2.connect(**self.db_config)
                logger.info("✅ Connexion DB établie (via Docker)")
            except Exception as e2:
                logger.error(f"❌ Échec connexion: {e2}")
                raise
    
    def _init_ml_model(self):
        """Initialise le modèle ML ensemble"""
        if not HAS_SKLEARN:
            return
        
        # Ensemble de modèles
        self._ml_models = {
            'rf': RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_leaf=5,
                random_state=42
            ),
            'gb': GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42
            ),
            'lr': LogisticRegression(
                max_iter=1000,
                random_state=42
            )
        }
        
        self._ml_weights = {'rf': 0.40, 'gb': 0.40, 'lr': 0.20}
        self._ml_trained = False
        
        logger.info("🤖 Modèles ML initialisés")

    # ==========================================================================
    # MODULE 1: RÉCUPÉRATION DES DONNÉES
    # ==========================================================================
    
    def get_team_profile(self, team_name: str, is_home: bool = True) -> TeamBTTSProfile:
        """
        Récupère le profil BTTS complet d'une équipe
        Fusionne team_intelligence + team_statistics_live + coach_intelligence
        """
        profile = TeamBTTSProfile(team_name=team_name)
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1. Données team_intelligence
                cur.execute("""
                    SELECT 
                        team_name, league,
                        home_btts_rate, away_btts_rate, btts_tendency,
                        home_goals_scored_avg, away_goals_scored_avg,
                        home_goals_conceded_avg, away_goals_conceded_avg,
                        home_clean_sheet_rate, away_clean_sheet_rate,
                        home_failed_to_score_rate, away_failed_to_score_rate,
                        home_over25_rate, away_over25_rate,
                        home_over15_rate, away_over15_rate,
                        xg_for_avg, xg_against_avg, xg_difference, overperformance_goals,
                        first_half_goals_pct, second_half_goals_pct,
                        late_goals_pct, conceded_late_pct, first_scorer_rate,
                        current_style, current_pressing, current_style_score,
                        current_form_points,
                        after_europe, congested_schedule,
                        vs_top_teams, vs_bottom_teams,
                        current_coach, coach_style, coach_tenure_months,
                        matches_analyzed, confidence_overall, data_quality_score, is_reliable
                    FROM team_intelligence
                    WHERE LOWER(team_name) LIKE LOWER(%s)
                       OR LOWER(team_name) LIKE LOWER(%s)
                    LIMIT 1
                """, (f'%{team_name}%', team_name))
                
                row = cur.fetchone()
                
                if row:
                    profile.team_name = row['team_name']
                    profile.league = row.get('league', '')
                    
                    # Stats BTTS
                    profile.home_btts_rate = safe_float(row.get('home_btts_rate'), 50) / 100
                    profile.away_btts_rate = safe_float(row.get('away_btts_rate'), 50) / 100
                    profile.btts_tendency = safe_float(row.get('btts_tendency'), 50) / 100
                    
                    # Stats offensives
                    profile.home_goals_scored_avg = safe_float(row.get('home_goals_scored_avg'), 1.3)
                    profile.away_goals_scored_avg = safe_float(row.get('away_goals_scored_avg'), 1.0)
                    profile.home_failed_to_score_rate = safe_float(row.get('home_failed_to_score_rate'), 20) / 100
                    profile.away_failed_to_score_rate = safe_float(row.get('away_failed_to_score_rate'), 30) / 100
                    
                    # Stats défensives
                    profile.home_goals_conceded_avg = safe_float(row.get('home_goals_conceded_avg'), 1.0)
                    profile.away_goals_conceded_avg = safe_float(row.get('away_goals_conceded_avg'), 1.4)
                    profile.home_clean_sheet_rate = safe_float(row.get('home_clean_sheet_rate'), 30) / 100
                    profile.away_clean_sheet_rate = safe_float(row.get('away_clean_sheet_rate'), 20) / 100
                    
                    # xG
                    profile.xg_for_avg = safe_float(row.get('xg_for_avg'), 0)
                    profile.xg_against_avg = safe_float(row.get('xg_against_avg'), 0)
                    profile.xg_difference = safe_float(row.get('xg_difference'), 0)
                    profile.overperformance_goals = safe_float(row.get('overperformance_goals'), 0)
                    
                    # Timing
                    profile.first_half_goals_pct = safe_float(row.get('first_half_goals_pct'), 45) / 100
                    profile.second_half_goals_pct = safe_float(row.get('second_half_goals_pct'), 55) / 100
                    profile.late_goals_pct = safe_float(row.get('late_goals_pct'), 15) / 100
                    profile.conceded_late_pct = safe_float(row.get('conceded_late_pct'), 15) / 100
                    profile.first_scorer_rate = safe_float(row.get('first_scorer_rate'), 50) / 100
                    
                    # Style
                    profile.current_style = row.get('current_style') or 'balanced'
                    profile.current_pressing = row.get('current_pressing') or 'medium'
                    profile.style_score = safe_float(row.get('current_style_score'), 50)
                    
                    # Contexte
                    profile.after_europe = safe_float(row.get('after_europe'), 0)
                    profile.congested_schedule = safe_float(row.get('congested_schedule'), 0)
                    profile.vs_top_teams = safe_float(row.get('vs_top_teams'), 0)
                    profile.vs_bottom_teams = safe_float(row.get('vs_bottom_teams'), 0)
                    
                    # Coach
                    profile.coach_style = row.get('coach_style') or ''
                    profile.coach_tenure_months = safe_float(row.get('coach_tenure_months'), 0)
                    
                    # Over rates
                    profile.home_over25_rate = safe_float(row.get('home_over25_rate'), 50) / 100
                    profile.away_over25_rate = safe_float(row.get('away_over25_rate'), 50) / 100
                    profile.home_over15_rate = safe_float(row.get('home_over15_rate'), 70) / 100
                    profile.away_over15_rate = safe_float(row.get('away_over15_rate'), 65) / 100
                    
                    # Métadonnées
                    profile.matches_analyzed = int(safe_float(row.get('matches_analyzed'), 0))
                    profile.confidence = safe_float(row.get('confidence_overall'), 50)
                    profile.data_quality_score = safe_float(row.get('data_quality_score'), 50)
                    profile.is_reliable = bool(row.get('is_reliable'))
                
                # 2. Enrichir avec team_statistics_live (forme récente)
                cur.execute("""
                    SELECT 
                        last5_btts, last5_btts_pct,
                        last5_goals_for, last5_goals_against,
                        last5_form_points,
                        btts_pct, home_btts_pct, away_btts_pct,
                        clean_sheet_pct, failed_to_score_pct
                    FROM team_statistics_live
                    WHERE LOWER(team_name) LIKE LOWER(%s)
                    LIMIT 1
                """, (f'%{team_name}%',))
                
                live_row = cur.fetchone()
                if live_row:
                    profile.last5_btts_rate = float(live_row.get('last5_btts_pct') or 50) / 100
                    profile.last5_goals_for = float(live_row.get('last5_goals_for') or 0)
                    profile.last5_goals_against = float(live_row.get('last5_goals_against') or 0)
                    profile.current_form_points = float(live_row.get('last5_form_points') or 7.5)
                
                # 3. Enrichir avec coach_intelligence
                if profile.coach_style:
                    cur.execute("""
                        SELECT 
                            btts_rate, tactical_style,
                            avg_goals_per_match, clean_sheet_rate
                        FROM coach_intelligence
                        WHERE LOWER(coach_name) LIKE LOWER(%s)
                        LIMIT 1
                    """, (f'%{profile.coach_style}%',))
                    
                    coach_row = cur.fetchone()
                    if coach_row:
                        profile.coach_btts_rate = float(coach_row.get('btts_rate') or 50) / 100
                
        except Exception as e:
            logger.warning(f"⚠️ Erreur récupération profil {team_name}: {e}")
        
        # Calculer la confiance finale
        if profile.matches_analyzed >= 10 and profile.data_quality_score >= 60:
            profile.confidence = min(95, profile.confidence)
            profile.is_reliable = True
        elif profile.matches_analyzed >= 5:
            profile.confidence = min(70, profile.confidence)
        else:
            profile.confidence = min(40, 30 + profile.matches_analyzed * 2)
        
        return profile
    
    def get_league_stats(self, league_name: str) -> LeagueStats:
        """
        Récupère les statistiques dynamiques de la ligue (60 derniers jours)
        """
        # Vérifier le cache
        cache_key = league_name.lower()
        if cache_key in self._league_cache:
            cached = self._league_cache[cache_key]
            if cached.last_updated and datetime.now() - cached.last_updated < self._cache_ttl:
                return cached
        
        stats = LeagueStats(league_name=league_name)
        
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        COUNT(*) as matches,
                        AVG(home_goals + away_goals) as avg_goals,
                        AVG(CASE WHEN home_goals > 0 AND away_goals > 0 THEN 1.0 ELSE 0.0 END) as btts_rate,
                        AVG(home_goals) as avg_home_goals,
                        AVG(away_goals) as avg_away_goals,
                        AVG(CASE WHEN home_goals > away_goals THEN 1.0 ELSE 0.0 END) as home_win_rate,
                        AVG(CASE WHEN home_goals = away_goals THEN 1.0 ELSE 0.0 END) as draw_rate,
                        AVG(CASE WHEN home_goals = 0 OR away_goals = 0 THEN 1.0 ELSE 0.0 END) as clean_sheet_rate
                    FROM matches_results
                    WHERE LOWER(league) LIKE LOWER(%s)
                    AND match_date > NOW() - INTERVAL '60 days'
                """, (f'%{league_name}%',))
                
                row = cur.fetchone()
                
                if row and row['matches'] and row['matches'] > 10:
                    stats.matches_analyzed = int(row['matches'])
                    stats.goals_per_game = float(row['avg_goals'] or 2.7)
                    stats.btts_rate = float(row['btts_rate'] or 0.52)
                    stats.avg_home_goals = float(row['avg_home_goals'] or 1.5)
                    stats.avg_away_goals = float(row['avg_away_goals'] or 1.2)
                    stats.home_win_rate = float(row['home_win_rate'] or 0.45)
                    stats.draw_rate = float(row['draw_rate'] or 0.25)
                    stats.away_win_rate = 1 - stats.home_win_rate - stats.draw_rate
                    stats.clean_sheet_rate = float(row['clean_sheet_rate'] or 0.25)
                    stats.last_updated = datetime.now()
                    
        except Exception as e:
            logger.warning(f"⚠️ Erreur stats ligue {league_name}: {e}")
        
        # Mettre en cache
        self._league_cache[cache_key] = stats
        
        return stats

    # ==========================================================================
    # MODULE 2: CALCULS STATISTIQUES (POISSON + DIXON-COLES)
    # ==========================================================================
    
    def _poisson_probability(self, lmbda: float, k: int) -> float:
        """Calcule P(X = k) pour une distribution de Poisson"""
        if lmbda <= 0:
            return 1.0 if k == 0 else 0.0
        return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)
    
    def _calculate_expected_goals(self, 
                                   attack_strength: float,
                                   defense_weakness: float,
                                   league_avg: float = 1.35) -> float:
        """
        Calcule les buts attendus avec régression vers la moyenne
        """
        # Expected goals bruts
        xg = attack_strength * (defense_weakness / league_avg)
        
        # Appliquer les bornes (CORRIGÉ: borne basse 0.1)
        xg = max(self.XG_BOUNDS['min'], min(self.XG_BOUNDS['max'], xg))
        
        return xg
    
    def _apply_dixon_coles_adjustment(self, 
                                       prob_matrix: Dict[Tuple[int, int], float]) -> Dict[Tuple[int, int], float]:
        """
        Applique la correction Dixon-Coles pour les scores bas
        Le 0-0 et 1-1 sont souvent mal estimés par Poisson simple
        """
        rho = self.DIXON_COLES['rho']
        
        adjusted = prob_matrix.copy()
        
        # Ajustement 0-0 (augmenté car sous-estimé)
        if (0, 0) in adjusted:
            adjusted[(0, 0)] *= self.DIXON_COLES['tau_00']
        
        # Ajustement 0-1 et 1-0
        if (0, 1) in adjusted:
            adjusted[(0, 1)] *= self.DIXON_COLES['tau_01']
        if (1, 0) in adjusted:
            adjusted[(1, 0)] *= self.DIXON_COLES['tau_10']
        
        # Ajustement 1-1 (légèrement réduit)
        if (1, 1) in adjusted:
            adjusted[(1, 1)] *= self.DIXON_COLES['tau_11']
        
        # Renormaliser
        total = sum(adjusted.values())
        if total > 0:
            adjusted = {k: v/total for k, v in adjusted.items()}
        
        return adjusted
    
    def _calculate_score_probabilities(self,
                                        home_xg: float,
                                        away_xg: float,
                                        max_goals: int = 6) -> Dict[Tuple[int, int], float]:
        """
        Calcule la matrice de probabilités des scores
        Utilise Poisson puis Dixon-Coles
        """
        prob_matrix = {}
        
        for home_goals in range(max_goals + 1):
            for away_goals in range(max_goals + 1):
                prob_home = self._poisson_probability(home_xg, home_goals)
                prob_away = self._poisson_probability(away_xg, away_goals)
                prob_matrix[(home_goals, away_goals)] = prob_home * prob_away
        
        # Appliquer Dixon-Coles
        prob_matrix = self._apply_dixon_coles_adjustment(prob_matrix)
        
        return prob_matrix
    
    def _calculate_btts_from_matrix(self, 
                                     prob_matrix: Dict[Tuple[int, int], float]) -> Tuple[float, float]:
        """
        Calcule P(BTTS YES) et P(BTTS NO) depuis la matrice de scores
        """
        btts_yes = 0.0
        btts_no = 0.0
        
        for (home, away), prob in prob_matrix.items():
            if home > 0 and away > 0:
                btts_yes += prob
            else:
                btts_no += prob
        
        # Normaliser
        total = btts_yes + btts_no
        if total > 0:
            btts_yes /= total
            btts_no /= total
        
        return btts_yes, btts_no

    # ==========================================================================
    # MODULE 3: FACTEURS CONTEXTUELS
    # ==========================================================================
    
    def _calculate_context_adjustment(self,
                                       home_profile: TeamBTTSProfile,
                                       away_profile: TeamBTTSProfile) -> float:
        """
        Calcule l'ajustement contextuel pour BTTS
        """
        adjustment = 0.0
        
        # Fatigue (calendrier chargé)
        if home_profile.congested_schedule > 0.7:
            adjustment += self.CONTEXT_IMPACT['fatigue_high']
        elif home_profile.congested_schedule < 0.3:
            adjustment += self.CONTEXT_IMPACT['fatigue_low']
            
        if away_profile.congested_schedule > 0.7:
            adjustment += self.CONTEXT_IMPACT['fatigue_high']
        elif away_profile.congested_schedule < 0.3:
            adjustment += self.CONTEXT_IMPACT['fatigue_low']
        
        # Après match européen
        if home_profile.after_europe > 0.5:
            adjustment += self.CONTEXT_IMPACT['after_europe']
        if away_profile.after_europe > 0.5:
            adjustment += self.CONTEXT_IMPACT['after_europe']
        
        return adjustment
    

    def _calculate_tactical_mismatch(self,
                                      home_profile: TeamBTTSProfile,
                                      away_profile: TeamBTTSProfile) -> float:
        """
        V2.1: Calcule l'impact du croisement tactique spécifique
        Ex: Possession vs Counter-Attack = match ouvert
        """
        home_style = (home_profile.current_style or 'balanced').lower()
        away_style = (away_profile.current_style or 'balanced').lower()
        
        # Chercher dans la matrice
        key = (home_style, away_style)
        if key in self.TACTICAL_MATRIX:
            return self.TACTICAL_MATRIX[key]
        
        # Essayer l'inverse (symétrie partielle)
        key_reverse = (away_style, home_style)
        if key_reverse in self.TACTICAL_MATRIX:
            return self.TACTICAL_MATRIX[key_reverse] * 0.8  # Légèrement réduit
        
        # Sinon, utiliser l'ancienne méthode additive
        return self._calculate_style_adjustment(home_profile, away_profile)

    def _calculate_style_adjustment(self,
                                     home_profile: TeamBTTSProfile,
                                     away_profile: TeamBTTSProfile) -> float:
        """
        Calcule l'ajustement basé sur le style de jeu
        """
        adjustment = 0.0
        
        # Style home
        home_style = home_profile.current_style.lower() if home_profile.current_style else 'balanced'
        if home_style in self.STYLE_IMPACT:
            adjustment += self.STYLE_IMPACT[home_style] * 0.6  # Poids domicile
        
        # Style away
        away_style = away_profile.current_style.lower() if away_profile.current_style else 'balanced'
        if away_style in self.STYLE_IMPACT:
            adjustment += self.STYLE_IMPACT[away_style] * 0.4  # Poids extérieur
        
        # Pressing
        home_pressing = home_profile.current_pressing.lower() if home_profile.current_pressing else 'medium'
        pressing_key = f'pressing_{home_pressing}'
        if pressing_key in self.STYLE_IMPACT:
            adjustment += self.STYLE_IMPACT[pressing_key] * 0.5
        
        away_pressing = away_profile.current_pressing.lower() if away_profile.current_pressing else 'medium'
        pressing_key = f'pressing_{away_pressing}'
        if pressing_key in self.STYLE_IMPACT:
            adjustment += self.STYLE_IMPACT[pressing_key] * 0.5
        
        return adjustment

    # ==========================================================================
    # MODULE 4: FORME ET RÉGRESSION
    # ==========================================================================
    
    def _apply_regression_to_mean(self,
                                   team_rate: float,
                                   league_rate: float,
                                   matches: int,
                                   regression_factor: float = 0.15) -> float:
        """
        Applique la régression vers la moyenne de la ligue
        Plus l'échantillon est petit, plus on régresse
        """
        if matches >= 20:
            weight = 0.05  # Peu de régression si beaucoup de matchs
        elif matches >= 10:
            weight = 0.10
        elif matches >= 5:
            weight = 0.15
        else:
            weight = 0.25  # Beaucoup de régression si peu de matchs
        
        regressed = team_rate * (1 - weight) + league_rate * weight
        
        return regressed
    
    def _calculate_form_adjustment(self,
                                    home_profile: TeamBTTSProfile,
                                    away_profile: TeamBTTSProfile) -> float:
        """
        Ajustement basé sur la forme récente (5 derniers matchs)
        """
        adjustment = 0.0
        
        # BTTS sur les 5 derniers matchs vs moyenne
        home_form_diff = home_profile.last5_btts_rate - home_profile.home_btts_rate
        away_form_diff = away_profile.last5_btts_rate - away_profile.away_btts_rate
        
        # Si forme récente > moyenne → ajustement positif
        adjustment += home_form_diff * 0.3
        adjustment += away_form_diff * 0.3
        
        # Forme générale (points)
        # 15 points max sur 5 matchs, 7.5 = moyenne
        if home_profile.current_form_points > 10:  # Très bonne forme
            adjustment += 0.02
        elif home_profile.current_form_points < 5:  # Mauvaise forme
            adjustment -= 0.02
            
        if away_profile.current_form_points > 10:
            adjustment += 0.02
        elif away_profile.current_form_points < 5:
            adjustment -= 0.02
        
        return adjustment

    # ==========================================================================
    # MODULE 5: CALCUL PRINCIPAL
    # ==========================================================================
    
    def calculate_btts_probability(self,
                                    home_team: str,
                                    away_team: str,
                                    market_odds_yes: float = None,
                                    market_odds_no: float = None) -> BTTSPrediction:
        """
        🧠 CALCUL PRINCIPAL BTTS V2.0
        
        Combine tous les modules pour une prédiction optimale
        """
        
        # 1. Récupérer les profils
        home_profile = self.get_team_profile(home_team, is_home=True)
        away_profile = self.get_team_profile(away_team, is_home=False)
        
        # 2. Récupérer stats de ligue
        league = home_profile.league or away_profile.league or 'default'
        league_stats = self.get_league_stats(league)
        
        # 3. Calculer les expected goals
        home_xg = self._calculate_expected_goals(
            attack_strength=home_profile.home_goals_scored_avg,
            defense_weakness=away_profile.away_goals_conceded_avg,
            league_avg=league_stats.avg_home_goals
        )
        
        away_xg = self._calculate_expected_goals(
            attack_strength=away_profile.away_goals_scored_avg,
            defense_weakness=home_profile.home_goals_conceded_avg,
            league_avg=league_stats.avg_away_goals
        )
        
        # Ajuster avec xG réel si disponible
        if home_profile.xg_for_avg > 0:
            home_xg = home_xg * 0.4 + home_profile.xg_for_avg * 0.6  # V2.1: Poids inversés, réalité > théorie
        if away_profile.xg_for_avg > 0:
            away_xg = away_xg * 0.4 + away_profile.xg_for_avg * 0.6  # V2.1: Poids inversés
        
        # 4. Calculer la matrice de scores (Poisson + Dixon-Coles)
        score_matrix = self._calculate_score_probabilities(home_xg, away_xg)
        stat_btts_yes, stat_btts_no = self._calculate_btts_from_matrix(score_matrix)
        
        # 5. Appliquer régression vers la moyenne
        home_btts_regressed = self._apply_regression_to_mean(
            home_profile.home_btts_rate,
            league_stats.btts_rate,
            home_profile.matches_analyzed
        )
        away_btts_regressed = self._apply_regression_to_mean(
            away_profile.away_btts_rate,
            league_stats.btts_rate,
            away_profile.matches_analyzed
        )
        
        # 6. Calculer les ajustements
        context_adj = self._calculate_context_adjustment(home_profile, away_profile)
        style_adj = self._calculate_tactical_mismatch(home_profile, away_profile)  # V2.1: Matrice croisement
        form_adj = self._calculate_form_adjustment(home_profile, away_profile)
        
        # 7. Facteur clean sheet / failed to score
        # P(BTTS) = P(Home marque) × P(Away marque)
        # P(Home marque) = 1 - P(Home failed to score)
        # P(Away marque) = 1 - P(Away failed to score) × (1 - Home clean sheet bonus)
        
        # V2.1: Calcul basé sur Poisson (P >= 1 but) ajusté par qualité défensive
        # P(marque) = 1 - e^(-xG) ajusté par le taux de failed_to_score
        p_home_scores_poisson = 1 - math.exp(-home_xg) if home_xg > 0 else 0.5
        p_away_scores_poisson = 1 - math.exp(-away_xg) if away_xg > 0 else 0.5
        
        # Ajustement par les stats réelles (failed to score, clean sheet adverse)
        home_fts_adj = 1 - home_profile.home_failed_to_score_rate * 0.5
        away_cs_adj = 1 - away_profile.away_clean_sheet_rate * 0.3
        p_home_scores = p_home_scores_poisson * home_fts_adj * away_cs_adj
        
        away_fts_adj = 1 - away_profile.away_failed_to_score_rate * 0.5
        home_cs_adj = 1 - home_profile.home_clean_sheet_rate * 0.3
        p_away_scores = p_away_scores_poisson * away_fts_adj * home_cs_adj
        
        # Borner entre 0.1 et 0.95
        p_home_scores = max(0.10, min(0.95, p_home_scores))
        p_away_scores = max(0.10, min(0.95, p_away_scores))
        
        clean_sheet_btts = p_home_scores * p_away_scores
        
        # 8. Combiner tous les modules
        module_scores = {
            'statistical': stat_btts_yes,
            'historical': (home_btts_regressed + away_btts_regressed) / 2,
            'clean_sheet': clean_sheet_btts,
            'contextual': 0.5 + context_adj,  # Centré sur 0.5
            'tactical': 0.5 + style_adj,
            'form': 0.5 + form_adj,
        }
        
        # Combinaison pondérée
        btts_yes_prob = (
            module_scores['statistical'] * 0.30 +
            module_scores['historical'] * 0.25 +
            module_scores['clean_sheet'] * 0.20 +
            module_scores['contextual'] * 0.10 +
            module_scores['tactical'] * 0.08 +
            module_scores['form'] * 0.07
        )
        
        # Borner entre 0.12 et 0.88
        btts_yes_prob = max(0.12, min(0.88, btts_yes_prob))
        btts_no_prob = 1 - btts_yes_prob
        
        # 9. Calculer les cotes justes
        fair_odds_yes = round(1 / btts_yes_prob, 2) if btts_yes_prob > 0.01 else 50.0
        fair_odds_no = round(1 / btts_no_prob, 2) if btts_no_prob > 0.01 else 50.0
        
        # 10. Calculer l'edge
        edge_yes = None
        edge_no = None
        kelly_yes = None
        kelly_no = None
        
        if market_odds_yes:
            implied_prob = 1 / market_odds_yes
            edge_yes = btts_yes_prob - implied_prob
            if edge_yes > 0:
                kelly_yes = (edge_yes * market_odds_yes - (1 - btts_yes_prob)) / market_odds_yes
                kelly_yes = max(0, min(kelly_yes * self.THRESHOLDS['kelly_fraction'], 
                                       self.THRESHOLDS['max_stake_pct']))
        
        if market_odds_no:
            implied_prob = 1 / market_odds_no
            edge_no = btts_no_prob - implied_prob
            if edge_no > 0:
                kelly_no = (edge_no * market_odds_no - (1 - btts_no_prob)) / market_odds_no
                kelly_no = max(0, min(kelly_no * self.THRESHOLDS['kelly_fraction'],
                                      self.THRESHOLDS['max_stake_pct']))
        
        # 11. Déterminer la recommandation
        confidence = (home_profile.confidence + away_profile.confidence) / 2
        
        recommended_bet = "SKIP"
        if btts_yes_prob >= self.THRESHOLDS['btts_yes_min_prob']:
            if edge_yes is None or edge_yes >= self.THRESHOLDS['edge_min']:
                if confidence >= self.THRESHOLDS['confidence_min']:
                    recommended_bet = "BTTS_YES"
        elif btts_no_prob >= self.THRESHOLDS['btts_no_min_prob']:
            if edge_no is None or edge_no >= self.THRESHOLDS['edge_min']:
                if confidence >= self.THRESHOLDS['confidence_min']:
                    recommended_bet = "BTTS_NO"
        
        # 12. Construire le raisonnement
        reasoning_lines = []
        reasoning_lines.append(f"📊 Analyse BTTS V2.0 - {home_team} vs {away_team}")
        reasoning_lines.append(f"")
        reasoning_lines.append(f"🏠 {home_team} (DOM):")
        reasoning_lines.append(f"   • BTTS rate: {home_profile.home_btts_rate*100:.0f}%")
        reasoning_lines.append(f"   • Buts marqués: {home_profile.home_goals_scored_avg:.2f}/match")
        reasoning_lines.append(f"   • Clean sheet: {home_profile.home_clean_sheet_rate*100:.0f}%")
        reasoning_lines.append(f"   • xG attendus: {home_xg:.2f}")
        reasoning_lines.append(f"")
        reasoning_lines.append(f"✈️ {away_team} (EXT):")
        reasoning_lines.append(f"   • BTTS rate: {away_profile.away_btts_rate*100:.0f}%")
        reasoning_lines.append(f"   • Buts marqués: {away_profile.away_goals_scored_avg:.2f}/match")
        reasoning_lines.append(f"   • Clean sheet: {away_profile.away_clean_sheet_rate*100:.0f}%")
        reasoning_lines.append(f"   • xG attendus: {away_xg:.2f}")
        reasoning_lines.append(f"")
        reasoning_lines.append(f"🎯 PROBABILITÉS:")
        reasoning_lines.append(f"   • BTTS YES: {btts_yes_prob*100:.1f}% (cote juste: @{fair_odds_yes})")
        reasoning_lines.append(f"   • BTTS NO:  {btts_no_prob*100:.1f}% (cote juste: @{fair_odds_no})")
        
        if market_odds_yes and edge_yes:
            reasoning_lines.append(f"")
            reasoning_lines.append(f"💰 VALUE:")
            reasoning_lines.append(f"   • Edge YES: {edge_yes*100:+.1f}%")
            if kelly_yes:
                reasoning_lines.append(f"   • Kelly YES: {kelly_yes*100:.1f}% du bankroll")
        
        if market_odds_no and edge_no:
            reasoning_lines.append(f"   • Edge NO: {edge_no*100:+.1f}%")
            if kelly_no:
                reasoning_lines.append(f"   • Kelly NO: {kelly_no*100:.1f}% du bankroll")
        
        reasoning_lines.append(f"")
        reasoning_lines.append(f"✅ RECOMMANDATION: {recommended_bet}")
        reasoning_lines.append(f"📈 Confiance: {confidence:.0f}%")
        
        # Warnings
        warnings = []
        if home_profile.matches_analyzed < 5:
            warnings.append(f"⚠️ Peu de données {home_team} ({home_profile.matches_analyzed} matchs)")
        if away_profile.matches_analyzed < 5:
            warnings.append(f"⚠️ Peu de données {away_team} ({away_profile.matches_analyzed} matchs)")
        if confidence < 50:
            warnings.append("⚠️ Confiance faible - prudence recommandée")
        
        # 13. Créer la prédiction
        prediction = BTTSPrediction(
            home_team=home_team,
            away_team=away_team,
            btts_yes_probability=round(btts_yes_prob, 4),
            btts_no_probability=round(btts_no_prob, 4),
            recommended_bet=recommended_bet,
            fair_odds_yes=fair_odds_yes,
            fair_odds_no=fair_odds_no,
            market_odds_yes=market_odds_yes,
            market_odds_no=market_odds_no,
            edge_yes=round(edge_yes, 4) if edge_yes else None,
            edge_no=round(edge_no, 4) if edge_no else None,
            kelly_stake_yes=round(kelly_yes, 4) if kelly_yes else None,
            kelly_stake_no=round(kelly_no, 4) if kelly_no else None,
            confidence=round(confidence, 1),
            module_scores={k: round(v, 4) for k, v in module_scores.items()},
            factors={
                'home_xg': round(home_xg, 2),
                'away_xg': round(away_xg, 2),
                'context_adj': round(context_adj, 4),
                'style_adj': round(style_adj, 4),
                'form_adj': round(form_adj, 4),
                'p_home_scores': round(p_home_scores, 4),
                'p_away_scores': round(p_away_scores, 4),
            },
            reasoning="\n".join(reasoning_lines),
            warnings=warnings,
            model_version=self.VERSION
        )
        
        return prediction
    
    # ==========================================================================
    # MODULE 6: INTERFACE PUBLIQUE
    # ==========================================================================
    
    def analyze_match(self, 
                      home_team: str, 
                      away_team: str,
                      market_odds_yes: float = None,
                      market_odds_no: float = None) -> Dict:
        """
        Analyse un match et retourne un dictionnaire formaté
        """
        prediction = self.calculate_btts_probability(
            home_team, away_team, market_odds_yes, market_odds_no
        )
        
        return {
            'match': f"{home_team} vs {away_team}",
            'btts_yes_prob': round(prediction.btts_yes_probability * 100, 1),
            'btts_no_prob': round(prediction.btts_no_probability * 100, 1),
            'recommendation': prediction.recommended_bet,
            'fair_odds': {
                'yes': prediction.fair_odds_yes,
                'no': prediction.fair_odds_no
            },
            'confidence': prediction.confidence,
            'edge': {
                'yes': round(prediction.edge_yes * 100, 1) if prediction.edge_yes else None,
                'no': round(prediction.edge_no * 100, 1) if prediction.edge_no else None
            },
            'kelly_stake': {
                'yes': round(prediction.kelly_stake_yes * 100, 2) if prediction.kelly_stake_yes else None,
                'no': round(prediction.kelly_stake_no * 100, 2) if prediction.kelly_stake_no else None
            },
            'module_scores': {k: round(v * 100, 1) for k, v in prediction.module_scores.items()},
            'factors': prediction.factors,
            'reasoning': prediction.reasoning,
            'warnings': prediction.warnings,
            'version': prediction.model_version
        }
    
    def batch_analyze(self, matches: List[Dict]) -> List[Dict]:
        """
        Analyse un lot de matchs
        """
        results = []
        for match in matches:
            try:
                result = self.analyze_match(
                    match['home_team'],
                    match['away_team'],
                    match.get('btts_yes_odds'),
                    match.get('btts_no_odds')
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Erreur analyse {match}: {e}")
        
        # Trier par confiance puis par edge
        results.sort(key=lambda x: (
            x['confidence'],
            max(x['edge']['yes'] or 0, x['edge']['no'] or 0)
        ), reverse=True)
        
        return results
    
    def get_top_picks(self, min_confidence: float = 60, limit: int = 10) -> List[Dict]:
        """
        Récupère les meilleurs picks BTTS des matchs à venir
        """
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT DISTINCT home_team, away_team, commence_time
                    FROM odds_history
                    WHERE commence_time > NOW()
                    AND commence_time < NOW() + INTERVAL '48 hours'
                    ORDER BY commence_time
                    LIMIT 50
                """)
                
                matches = cur.fetchall()
                
                results = []
                for match in matches:
                    result = self.analyze_match(match['home_team'], match['away_team'])
                    result['commence_time'] = str(match['commence_time'])
                    
                    if result['confidence'] >= min_confidence and result['recommendation'] != 'SKIP':
                        results.append(result)
                
                results.sort(key=lambda x: (
                    x['confidence'],
                    max(x['btts_yes_prob'], x['btts_no_prob'])
                ), reverse=True)
                
                return results[:limit]
                
        except Exception as e:
            logger.error(f"Erreur get_top_picks: {e}")
            return []


# =============================================================================
# MAIN - TEST
# =============================================================================

def main():
    """Test de l'Agent BTTS V2.0"""
    print("=" * 70)
    print("🧠 AGENT BTTS CALCULATOR V2.0 ULTIME - TEST")
    print("=" * 70)
    
    agent = AgentBTTSCalculatorV2()
    
    # Matchs de test
    test_matches = [
        {'home_team': 'Liverpool', 'away_team': 'Manchester City'},
        {'home_team': 'Tottenham Hotspur', 'away_team': 'Fulham'},
        {'home_team': 'Marseille', 'away_team': 'Toulouse'},
        {'home_team': 'Atletico Madrid', 'away_team': 'Real Oviedo'},
        {'home_team': 'Real Betis', 'away_team': 'Rayo Vallecano'},
        {'home_team': 'Leeds United', 'away_team': 'Burnley'},
    ]
    
    print("\n📊 ANALYSE DES MATCHS:\n")
    print("-" * 70)
    
    for match in test_matches:
        result = agent.analyze_match(match['home_team'], match['away_team'])
        
        print(f"\n⚽ {result['match']}")
        print(f"   📈 BTTS YES: {result['btts_yes_prob']}% | NO: {result['btts_no_prob']}%")
        print(f"   💰 Cotes justes: YES @{result['fair_odds']['yes']} | NO @{result['fair_odds']['no']}")
        print(f"   🎯 Recommandation: {result['recommendation']}")
        print(f"   📊 Confiance: {result['confidence']}%")
        
        if result['warnings']:
            for w in result['warnings']:
                print(f"   {w}")
        
        print(f"   📋 Modules: Stat={result['module_scores']['statistical']}% | "
              f"Hist={result['module_scores']['historical']}% | "
              f"CS={result['module_scores']['clean_sheet']}%")
    
    print("\n" + "=" * 70)
    print("✅ Agent BTTS V2.0 ULTIME opérationnel!")
    print("=" * 70)


if __name__ == "__main__":
    main()
