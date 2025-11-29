"""
🏎️ PRO SCORE V3.1 - Service de Calcul Professionnel
══════════════════════════════════════════════════════════════════════════════

ARCHITECTURE PROFESSIONNELLE:
- Connection Pool PostgreSQL (évite crash sur charge)
- Pondération DYNAMIQUE selon league_tier et data_quality
- Matchup buteurs avec ratios mathématiques
- Divergence ML = Signal, pas bruit
- Cache LRU pour performance
- Logs structurés

FORMULE NON-LINÉAIRE:
    SCORE_PRO = BASE_SCORE × K_RISK × K_TREND
    
    Où:
    - BASE_SCORE = S_DATA×w1 + S_VALUE×w2 + S_PATTERN×w3 + S_ML×w4
    - K_RISK = Multiplicateur de pénalité (0.0 à 1.05)
    - K_TREND = Multiplicateur mouvement de cotes (0.85 à 1.05)

AUTEUR: Mon_PS / FERRARI Intelligence
VERSION: 3.1.0
DATE: 29/11/2025
"""

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from functools import lru_cache
import json
import structlog
import hashlib

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DB_CONFIG = {
    "host": "monps_postgres",
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

# Logger structuré
logger = structlog.get_logger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONNECTION POOL SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

class DatabasePool:
    """
    Singleton pour gérer le pool de connexions PostgreSQL
    Évite le crash sur 100+ requêtes simultanées
    """
    _instance = None
    _pool = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_pool()
        return cls._instance
    
    def _initialize_pool(self):
        """Initialise le pool avec min=2, max=20 connexions"""
        try:
            self._pool = psycopg2.pool.SimpleConnectionPool(
                minconn=2,
                maxconn=20,
                **DB_CONFIG
            )
            logger.info("database_pool_initialized", min=2, max=20)
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error("database_pool_error", error=str(error))
            raise
    
    def get_connection(self):
        """Obtient une connexion du pool"""
        if self._pool is None:
            self._initialize_pool()
        return self._pool.getconn()
    
    def release_connection(self, conn):
        """Remet la connexion dans le pool"""
        if self._pool and conn:
            self._pool.putconn(conn)
    
    def close_all(self):
        """Ferme toutes les connexions"""
        if self._pool:
            self._pool.closeall()
            logger.info("database_pool_closed")


# Instance globale du pool
db_pool = DatabasePool()


# ═══════════════════════════════════════════════════════════════════════════════
# PRO SCORE V3.1 CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════════

class ProScoreV3Calculator:
    """
    Calculateur de Score Pro V3.1
    
    Formule: BASE_SCORE × K_RISK × K_TREND
    
    Utilise 100% des données FERRARI Intelligence:
    - team_intelligence (83 colonnes)
    - scorer_intelligence (153 colonnes)
    - market_patterns (24 colonnes)
    - patterns_correlations (16 colonnes)
    """
    
    # Cache pour éviter requêtes répétées
    _team_cache: Dict[str, Dict] = {}
    _cache_ttl: datetime = None
    _CACHE_DURATION = timedelta(minutes=30)
    
    def __init__(self):
        """Initialisation sans connexion (utilise le pool)"""
        self._check_cache_validity()
    
    def _check_cache_validity(self):
        """Invalide le cache si trop vieux"""
        if self._cache_ttl is None or datetime.now() > self._cache_ttl:
            ProScoreV3Calculator._team_cache = {}
            ProScoreV3Calculator._cache_ttl = datetime.now() + self._CACHE_DURATION
            logger.debug("cache_invalidated")
    
    def _get_db_connection(self):
        """Obtient une connexion du pool"""
        return db_pool.get_connection()
    
    def _release_db_connection(self, conn):
        """Remet la connexion dans le pool"""
        db_pool.release_connection(conn)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MÉTHODE PRINCIPALE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def calculate_match_score(self, home_team: str, away_team: str,
                               match_data: Dict) -> Dict:
        """
        Calcule le score PRO complet pour un match
        
        Args:
            home_team: Nom équipe domicile
            away_team: Nom équipe extérieur
            match_data: Données du match (xG, cotes, sweet_spot, etc.)
        
        Returns:
            Dict avec score, breakdown, alerts, recommendations
        """
        logger.info("calculating_match_score", 
                   home=home_team, away=away_team)
        
        # 1. Récupérer données équipes (avec cache)
        home_intel = self._get_team_intelligence(home_team)
        away_intel = self._get_team_intelligence(away_team)
        
        # 2. Récupérer buteurs
        home_scorers = self._get_team_scorers(home_team)
        away_scorers = self._get_team_scorers(away_team)
        
        # 3. Récupérer patterns applicables
        patterns = self._get_applicable_patterns(home_team, away_team, match_data)
        
        # 4. Déterminer les poids DYNAMIQUES selon la qualité des données
        league_tier = home_intel.get('league_tier', 2)
        data_quality = home_intel.get('data_quality_score', 50)
        weights = self._get_dynamic_weights(league_tier, data_quality)
        
        logger.debug("dynamic_weights", 
                    league_tier=league_tier, 
                    data_quality=data_quality,
                    weights=weights)
        
        # 5. Calculer les 4 composantes du BASE_SCORE
        s_data = self._calculate_s_data(home_intel, away_intel, match_data)
        s_value = self._calculate_s_value(match_data)
        s_pattern = self._calculate_s_pattern(patterns)
        s_ml, ml_signal = self._calculate_s_ml(match_data)
        
        # 6. Calculer BASE_SCORE avec poids dynamiques
        base_score = (
            s_data * weights['data'] +
            s_value * weights['value'] +
            s_pattern * weights['pattern'] +
            s_ml * weights['ml']
        )
        
        # 7. Calculer K_RISK (multiplicateur de pénalité)
        k_risk, risk_factors = self._calculate_k_risk(
            home_intel, away_intel, home_scorers, away_scorers, match_data
        )
        
        # 8. Calculer K_TREND (mouvement de cotes)
        k_trend, trend_info = self._calculate_k_trend(match_data)
        
        # 9. SCORE FINAL (cap à 99 - le 100 n'existe pas)
        final_score = min(base_score * k_risk * k_trend, 99)
        
        # 10. Détecter divergences
        divergences = self._detect_divergences(
            s_data, s_value, s_pattern, s_ml, ml_signal, match_data
        )
        
        # 11. Analyser volatilité des patterns
        volatility_warnings = []
        for p in patterns:
            vol = VolatilityAnalyzer.analyze_pattern_volatility(p)
            if vol['is_high_volatility']:
                volatility_warnings.append(vol)
        
        # 12. Générer recommandations
        recommendations = self._generate_recommendations(
            final_score, patterns, home_intel, away_intel,
            home_scorers, away_scorers, divergences, volatility_warnings
        )
        
        # 13. Analyser buteurs pour ce match
        scorer_analysis = self._analyze_scorers_matchup(
            home_scorers, away_scorers, home_intel, away_intel
        )
        
        # 14. Tactical matchup
        tactical_analysis = self._analyze_tactical_matchup(home_intel, away_intel)
        
        result = {
            "match": f"{home_team} vs {away_team}",
            "final_score": round(final_score, 1),
            "tier": self._get_tier(final_score),
            "tier_emoji": self._get_tier_emoji(final_score),
            "base_score": round(base_score, 1),
            "k_risk": round(k_risk, 2),
            "k_trend": round(k_trend, 2),
            "weights_used": weights,
            "breakdown": {
                "s_data": round(s_data, 1),
                "s_data_label": "Stats & xG",
                "s_value": round(s_value, 1),
                "s_value_label": "Value & CLV",
                "s_pattern": round(s_pattern, 1),
                "s_pattern_label": "Patterns FERRARI",
                "s_ml": round(s_ml, 1),
                "s_ml_label": "Consensus Agents"
            },
            "risk_factors": risk_factors,
            "risk_level": self._get_risk_level(k_risk),
            "trend_info": trend_info,
            "ml_signal": ml_signal,
            "divergences": divergences,
            "volatility_warnings": volatility_warnings,
            "patterns_applicable": patterns,
            "recommendations": recommendations,
            "scorer_analysis": scorer_analysis,
            "tactical_analysis": tactical_analysis,
            "team_intelligence": {
                "home": self._summarize_team(home_intel),
                "away": self._summarize_team(away_intel)
            },
            "calculated_at": datetime.now().isoformat()
        }
        
        logger.info("score_calculated",
                   match=f"{home_team} vs {away_team}",
                   score=final_score,
                   tier=result['tier'],
                   k_risk=k_risk,
                   k_trend=k_trend)
        
        return result
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RÉCUPÉRATION DES DONNÉES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _get_team_intelligence(self, team_name: str) -> Dict:
        """
        Récupère TOUTES les données d'une équipe
        Utilise cache LRU pour performance
        """
        # Check cache
        cache_key = team_name.lower().strip()
        if cache_key in self._team_cache:
            logger.debug("team_cache_hit", team=team_name)
            return self._team_cache[cache_key]
        
        conn = self._get_db_connection()
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Recherche flexible (nom exact ou partiel)
            cur.execute("""
                SELECT * FROM team_intelligence 
                WHERE LOWER(team_name) = LOWER(%s)
                OR LOWER(team_name_normalized) = LOWER(%s)
                OR team_name ILIKE %s
                OR team_name_normalized ILIKE %s
                ORDER BY 
                    CASE WHEN LOWER(team_name) = LOWER(%s) THEN 0 ELSE 1 END
                LIMIT 1
            """, (team_name, team_name, f"%{team_name}%", f"%{team_name}%", team_name))
            
            result = cur.fetchone()
            cur.close()
            
            data = dict(result) if result else {}
            
            # Mise en cache
            if data:
                self._team_cache[cache_key] = data
                logger.debug("team_cached", team=team_name)
            
            return data
            
        except Exception as e:
            logger.error("get_team_error", team=team_name, error=str(e))
            return {}
        finally:
            self._release_db_connection(conn)
    
    def _get_team_scorers(self, team_name: str) -> List[Dict]:
        """
        Récupère les buteurs d'une équipe avec TOUTES leurs 153 colonnes
        """
        conn = self._get_db_connection()
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT * FROM scorer_intelligence 
                WHERE current_team ILIKE %s
                AND season_goals > 0
                AND is_injured = false
                AND is_suspended = false
                ORDER BY season_goals DESC, goals_per_match DESC
                LIMIT 5
            """, (f"%{team_name}%",))
            
            results = cur.fetchall()
            cur.close()
            
            return [dict(r) for r in results]
            
        except Exception as e:
            logger.error("get_scorers_error", team=team_name, error=str(e))
            return []
        finally:
            self._release_db_connection(conn)
    
    def _get_applicable_patterns(self, home: str, away: str,
                                  match_data: Dict) -> List[Dict]:
        """
        Trouve les patterns applicables à ce match
        """
        conn = self._get_db_connection()
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            league = match_data.get('league', '')
            day_of_week = datetime.now().weekday()
            is_weekend = day_of_week in [4, 5, 6]  # Vendredi-Dimanche
            
            cur.execute("""
                SELECT * FROM market_patterns 
                WHERE (league IS NULL OR league ILIKE %s OR league = 'ALL')
                AND (day_of_week IS NULL OR day_of_week = %s)
                AND (is_weekend IS NULL OR is_weekend = %s)
                AND sample_size >= 30
                ORDER BY 
                    CASE WHEN is_profitable THEN 0 ELSE 1 END,
                    roi DESC
                LIMIT 15
            """, (f"%{league}%", day_of_week, is_weekend))
            
            results = cur.fetchall()
            cur.close()
            
            return [dict(r) for r in results]
            
        except Exception as e:
            logger.error("get_patterns_error", error=str(e))
            return []
        finally:
            self._release_db_connection(conn)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PONDÉRATION DYNAMIQUE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _get_dynamic_weights(self, league_tier: int, data_quality: int) -> Dict[str, float]:
        """
        Poids DYNAMIQUES selon la fiabilité des données
        
        - Top 5 ligues (tier 1) avec bonnes données → xG fiable, plus de poids sur data
        - Petites ligues (tier 3+) → données pourries, movement de cote = roi
        
        Args:
            league_tier: 1 = Top 5, 2 = Top 10-15, 3+ = petites ligues
            data_quality: 0-100 score de qualité des données
        """
        
        if league_tier == 1 and data_quality >= 70:
            # Top 5 ligues, bonnes données → xG très fiable
            return {
                "data": 0.35,    # xG fiable
                "value": 0.25,   # CLV important
                "pattern": 0.25, # Patterns historiques
                "ml": 0.15      # ML support
            }
        
        elif league_tier == 1 and data_quality >= 50:
            # Top 5 ligues, données moyennes
            return {
                "data": 0.30,
                "value": 0.28,
                "pattern": 0.25,
                "ml": 0.17
            }
        
        elif league_tier <= 2 and data_quality >= 50:
            # Ligues moyennes (France L2, Championship, etc.)
            return {
                "data": 0.25,
                "value": 0.30,   # Value plus importante
                "pattern": 0.25,
                "ml": 0.20
            }
        
        elif league_tier <= 2:
            # Ligues moyennes, données faibles
            return {
                "data": 0.20,
                "value": 0.32,
                "pattern": 0.23,
                "ml": 0.25      # ML compense données faibles
            }
        
        else:
            # Petites ligues (3ème divisions, etc.) → données peu fiables
            # Le mouvement de cote et ML sont rois
            return {
                "data": 0.15,   # Données peu fiables
                "value": 0.35,  # Mouvement de cote = info clé
                "pattern": 0.20,
                "ml": 0.30      # ML capture les anomalies
            }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CALCUL DES COMPOSANTES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _calculate_s_data(self, home: Dict, away: Dict,
                          match_data: Dict) -> float:
        """
        S_DATA - Score basé sur les statistiques réelles
        
        Utilise:
        - xG (expected goals)
        - Forme récente
        - Style de jeu
        - Performance dom/ext
        - Timing des buts
        """
        if not home or not away:
            return 50.0
        
        # ═══ xG ANALYSIS (40%) ═══
        home_xg_for = float(home.get('xg_for_avg') or 1.5)
        home_xg_against = float(home.get('xg_against_avg') or 1.3)
        away_xg_for = float(away.get('xg_for_avg') or 1.3)
        away_xg_against = float(away.get('xg_against_avg') or 1.5)
        
        # xG attendu pour ce match
        expected_home_xg = (home_xg_for + away_xg_against) / 2
        expected_away_xg = (away_xg_for + home_xg_against) / 2
        
        # Avantage xG domicile
        xg_advantage = expected_home_xg - expected_away_xg
        xg_score = 50 + (xg_advantage * 15)  # -3 to +3 → 5-95
        xg_score = max(5, min(95, xg_score))
        
        # ═══ FORM ANALYSIS (25%) ═══
        home_form_points = home.get('current_form_points') or 5
        away_form_points = away.get('current_form_points') or 5
        
        # Forme sur 10 (5 matchs × 2 points max moyenne)
        form_advantage = (home_form_points - away_form_points) / 10
        form_score = 50 + (form_advantage * 30)
        form_score = max(10, min(90, form_score))
        
        # ═══ HOME/AWAY STRENGTH (20%) ═══
        home_strength = float(home.get('home_strength') or 50)
        away_weakness = 100 - float(away.get('away_strength') or 50)
        
        strength_score = (home_strength + away_weakness) / 2
        
        # ═══ STYLE MATCHUP (15%) ═══
        home_style = home.get('current_style', 'balanced')
        away_style = away.get('current_style', 'balanced')
        style_score = self._analyze_style_matchup(home_style, away_style)
        
        # ═══ SCORE FINAL S_DATA ═══
        s_data = (
            xg_score * 0.40 +
            form_score * 0.25 +
            strength_score * 0.20 +
            style_score * 0.15
        )
        
        return max(0, min(100, s_data))
    
    def _calculate_s_value(self, match_data: Dict) -> float:
        """
        S_VALUE - Score basé sur la value de la cote
        
        Utilise:
        - CLV Edge (%)
        - Sweet Spot Score
        - Écart proba implicite vs calculée
        """
        edge_pct = float(match_data.get('edge_pct') or 0)
        sweet_spot_score = float(match_data.get('sweet_spot_score') or 50)
        implied_prob = float(match_data.get('implied_prob') or 50)
        calculated_prob = float(match_data.get('calculated_prob') or 50)
        
        # Edge contribue fortement (10% edge = très bon)
        edge_score = 50 + (edge_pct * 4)  # 10% edge → 90 score
        edge_score = max(0, min(100, edge_score))
        
        # Écart probabilités
        prob_edge = calculated_prob - implied_prob
        prob_score = 50 + (prob_edge * 2)
        prob_score = max(0, min(100, prob_score))
        
        # Combinaison
        s_value = (
            edge_score * 0.45 +
            sweet_spot_score * 0.35 +
            prob_score * 0.20
        )
        
        return max(0, min(100, s_value))
    
    def _calculate_s_pattern(self, patterns: List[Dict]) -> float:
        """
        S_PATTERN - Score basé sur les patterns historiques FERRARI
        
        Pondération par:
        - Win rate du pattern
        - ROI historique
        - Sample size (fiabilité)
        - Confidence score
        """
        if not patterns:
            return 50.0
        
        total_weight = 0
        weighted_score = 0
        
        for p in patterns:
            win_rate = float(p.get('win_rate') or 50)
            roi = float(p.get('roi') or 0)
            sample = int(p.get('sample_size') or 10)
            confidence = int(p.get('confidence_score') or 50)
            is_profitable = p.get('is_profitable', False)
            
            # Score du pattern
            # Win rate contribue 50%, ROI 30%, confidence 20%
            roi_normalized = min(max(roi + 50, 0), 100)  # -50% to +50% → 0-100
            
            pattern_score = (
                win_rate * 0.50 +
                roi_normalized * 0.30 +
                confidence * 0.20
            )
            
            # Bonus si profitable
            if is_profitable:
                pattern_score = min(pattern_score * 1.1, 100)
            
            # Pondération par fiabilité (sample size)
            # 30 samples = 1x, 100 samples = 2x, 200+ = 2.5x
            reliability_weight = min(sample / 50, 2.5)
            
            weighted_score += pattern_score * reliability_weight
            total_weight += reliability_weight
        
        if total_weight > 0:
            return weighted_score / total_weight
        return 50.0
    
    def _calculate_s_ml(self, match_data: Dict) -> Tuple[float, Dict]:
        """
        S_ML - Score basé sur le consensus des agents ML
        
        AMÉLIORATION: La divergence d'un seul agent peut être un SIGNAL
        pas du bruit. On le flag pour analyse humaine.
        """
        # Récupérer scores des agents
        agent_a = float(match_data.get('agent_a_score') or 50)
        agent_b = float(match_data.get('agent_b_score') or 50)
        agent_c = float(match_data.get('agent_c_score') or 50)
        agent_d = float(match_data.get('agent_d_score') or 50)
        
        scores = [agent_a, agent_b, agent_c, agent_d]
        avg = sum(scores) / len(scores)
        
        # Calcul écart-type
        variance = sum((x - avg) ** 2 for x in scores) / len(scores)
        std_dev = variance ** 0.5
        
        # Détecter outliers (agent très différent des autres)
        outliers = []
        for i, s in enumerate(scores):
            if abs(s - avg) > 25:  # Plus de 25 points d'écart
                agent_name = ['A-Anomaly', 'B-Spread', 'C-Pattern', 'D-Backtest'][i]
                outliers.append({
                    "agent": agent_name,
                    "score": s,
                    "deviation": round(s - avg, 1)
                })
        
        # ═══ ANALYSE DES DIVERGENCES ═══
        
        if len(outliers) == 1:
            # Un seul agent diverge fortement = SIGNAL POTENTIEL
            # Pas de pénalité, mais flag pour analyse humaine
            other_avg = (sum(scores) - outliers[0]['score']) / 3
            
            signal = {
                "type": "SINGLE_AGENT_DIVERGENCE",
                "status": "SIGNAL",
                "outlier_agent": outliers[0]['agent'],
                "outlier_score": outliers[0]['score'],
                "others_average": round(other_avg, 1),
                "insight": f"L'agent {outliers[0]['agent']} a détecté quelque chose "
                          f"({outliers[0]['score']:.0f}) vs autres ({other_avg:.0f}). "
                          f"Potentielle info privilégiée - analyse manuelle recommandée."
            }
            
            # On retourne la moyenne sans pénalité
            return avg, signal
        
        elif len(outliers) > 1 or std_dev > 20:
            # Désaccord général = INCERTITUDE
            signal = {
                "type": "GENERAL_DISAGREEMENT",
                "status": "WARNING",
                "std_dev": round(std_dev, 1),
                "scores": {
                    "A-Anomaly": agent_a,
                    "B-Spread": agent_b,
                    "C-Pattern": agent_c,
                    "D-Backtest": agent_d
                },
                "insight": f"Désaccord entre agents (σ={std_dev:.1f}). "
                          f"Incertitude élevée - prudence recommandée."
            }
            
            # Pénalité de 10% sur la moyenne
            return avg * 0.90, signal
        
        else:
            # CONSENSUS = Bonus
            consensus_strength = max(0, 20 - std_dev)
            
            signal = {
                "type": "CONSENSUS",
                "status": "STRONG",
                "std_dev": round(std_dev, 1),
                "consensus_strength": round(consensus_strength, 1),
                "scores": {
                    "A-Anomaly": agent_a,
                    "B-Spread": agent_b,
                    "C-Pattern": agent_c,
                    "D-Backtest": agent_d
                },
                "insight": f"Fort consensus entre agents (σ={std_dev:.1f}). "
                          f"Signal fiable."
            }
            
            return min(avg + consensus_strength * 0.5, 100), signal
    
    # ═══════════════════════════════════════════════════════════════════════════
    # K_RISK - MULTIPLICATEUR DE PÉNALITÉ
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _calculate_k_risk(self, home: Dict, away: Dict,
                          home_scorers: List, away_scorers: List,
                          match_data: Dict) -> Tuple[float, List[Dict]]:
        """
        K_RISK - Multiplicateur de risque (0.0 à 1.05)
        
        C'EST ICI QUE LES "VETOS" S'APPLIQUENT
        Un seul facteur critique peut tuer le score
        """
        k = 1.0
        factors = []
        
        # ═══════════════════════════════════════════════════════════════════════
        # BLACKLIST (k = 0) - Match à éviter absolument
        # ═══════════════════════════════════════════════════════════════════════
        
        if match_data.get('is_suspicious') or match_data.get('is_fixed'):
            return 0.0, [{
                "type": "BLACKLIST",
                "severity": "CRITICAL",
                "icon": "💀",
                "reason": "Match suspect ou liquidité trop faible",
                "k_impact": 0.0,
                "action": "NE PAS PARIER"
            }]
        
        # ═══════════════════════════════════════════════════════════════════════
        # CRITIQUE (k = 0.50-0.60) - Conditions très défavorables
        # ═══════════════════════════════════════════════════════════════════════
        
        if match_data.get('is_b_team'):
            k = min(k, 0.50)
            factors.append({
                "type": "CRITICAL",
                "severity": "HIGH",
                "icon": "🔴",
                "reason": "Équipe B alignée (rotation majeure)",
                "k_impact": 0.50,
                "action": "SKIP recommandé"
            })
        
        if match_data.get('is_dead_rubber'):
            k = min(k, 0.55)
            factors.append({
                "type": "CRITICAL",
                "severity": "HIGH",
                "icon": "🔴",
                "reason": "Match sans enjeu (Dead Rubber)",
                "k_impact": 0.55,
                "action": "Motivation douteuse"
            })
        
        if match_data.get('internal_crisis'):
            k = min(k, 0.60)
            factors.append({
                "type": "CRITICAL",
                "severity": "HIGH",
                "icon": "🔴",
                "reason": "Crise interne (vestiaire, coach)",
                "k_impact": 0.60,
                "action": "Instabilité élevée"
            })
        
        # ═══════════════════════════════════════════════════════════════════════
        # SÉVÈRE (k = 0.70-0.80) - Impact significatif
        # ═══════════════════════════════════════════════════════════════════════
        
        # Vérifier si star player absent
        for scorer in home_scorers[:2]:  # Top 2 buteurs
            if scorer.get('is_injured') or scorer.get('is_suspended'):
                player_name = scorer.get('player_name', 'Joueur clé')
                goals = scorer.get('season_goals', 0)
                
                k = min(k, 0.70)
                factors.append({
                    "type": "SEVERE",
                    "severity": "HIGH",
                    "icon": "🟠",
                    "reason": f"Star absente: {player_name} ({goals} buts)",
                    "k_impact": 0.70,
                    "action": "Impact offensif majeur"
                })
                break  # Un seul suffit
        
        # Post-Europe fatigue
        after_europe = home.get('after_europe', {})
        if isinstance(after_europe, str):
            try:
                after_europe = json.loads(after_europe) if after_europe else {}
            except:
                after_europe = {}
        
        days_since_europe = after_europe.get('last_match_days', 10)
        if days_since_europe < 4:
            k = min(k, 0.75)
            factors.append({
                "type": "SEVERE",
                "severity": "MEDIUM",
                "icon": "🟠",
                "reason": f"Match après Coupe d'Europe ({days_since_europe} jours)",
                "k_impact": 0.75,
                "action": "Fatigue et rotation probables"
            })
        
        # ═══════════════════════════════════════════════════════════════════════
        # MODÉRÉ (k = 0.85-0.95) - Impact à considérer
        # ═══════════════════════════════════════════════════════════════════════
        
        # Calendrier chargé
        congested = home.get('congested_schedule', {})
        if isinstance(congested, str):
            try:
                congested = json.loads(congested) if congested else {}
            except:
                congested = {}
        
        matches_14d = congested.get('matches_last_14_days', 0)
        if matches_14d > 4:
            k = min(k, 0.88)
            factors.append({
                "type": "MODERATE",
                "severity": "MEDIUM",
                "icon": "🟡",
                "reason": f"Calendrier chargé ({matches_14d} matchs en 14j)",
                "k_impact": 0.88,
                "action": "Fatigue accumulée"
            })
        
        # Data quality faible
        data_quality = home.get('data_quality_score', 50)
        if data_quality < 40:
            k = min(k, 0.92)
            factors.append({
                "type": "MODERATE",
                "severity": "LOW",
                "icon": "🟡",
                "reason": f"Données peu fiables (qualité: {data_quality}/100)",
                "k_impact": 0.92,
                "action": "Analyse incertaine"
            })
        
        # Météo extrême
        if match_data.get('weather_extreme'):
            k = min(k, 0.93)
            factors.append({
                "type": "MODERATE",
                "severity": "LOW",
                "icon": "🟡",
                "reason": "Conditions météo extrêmes",
                "k_impact": 0.93,
                "action": "Peut affecter le jeu"
            })
        
        # ═══════════════════════════════════════════════════════════════════════
        # BONUS (k > 1.0) - Conditions favorables
        # ═══════════════════════════════════════════════════════════════════════
        
        # Match à enjeu avec équipe en forme
        current_form = home.get('current_form', 'neutral')
        if match_data.get('high_stakes') and current_form in ['excellent', 'good']:
            k = min(k * 1.05, 1.05)
            factors.append({
                "type": "BONUS",
                "severity": "POSITIVE",
                "icon": "🟢",
                "reason": "Match à enjeu + forme excellente",
                "k_impact": 1.05,
                "action": "Motivation maximale"
            })
        
        # Retour de star player
        if match_data.get('star_return'):
            k = min(k * 1.03, 1.05)
            factors.append({
                "type": "BONUS",
                "severity": "POSITIVE",
                "icon": "��",
                "reason": "Retour d'un joueur clé",
                "k_impact": 1.03,
                "action": "Boost offensif"
            })
        
        # Si aucun facteur, tout est normal
        if not factors:
            factors.append({
                "type": "NORMAL",
                "severity": "NEUTRAL",
                "icon": "⚪",
                "reason": "Aucun facteur de risque détecté",
                "k_impact": 1.0,
                "action": "Conditions standards"
            })
        
        return k, factors
    
    # ═══════════════════════════════════════════════════════════════════════════
    # K_TREND - MOUVEMENT DE COTES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _calculate_k_trend(self, match_data: Dict) -> Tuple[float, Dict]:
        """
        K_TREND - Multiplicateur basé sur mouvement de cotes
        
        - Cote qui baisse = Smart money te suit
        - Cote qui monte = Info cachée probable
        """
        odds_movement = match_data.get('odds_movement', 'stable')
        odds_change_pct = float(match_data.get('odds_change_pct') or 0)
        
        if odds_movement == 'dropping_fast' or odds_change_pct < -5:
            return 1.05, {
                "direction": "STEAM",
                "icon": "📈",
                "change_pct": odds_change_pct,
                "signal": "L'argent intelligent te suit - Steam Move détecté",
                "confidence": "HIGH"
            }
        
        elif odds_movement == 'dropping_slow' or (-5 <= odds_change_pct < -2):
            return 1.02, {
                "direction": "POSITIVE",
                "icon": "📈",
                "change_pct": odds_change_pct,
                "signal": "Cote en baisse légère - tendance favorable",
                "confidence": "MEDIUM"
            }
        
        elif odds_movement == 'stable' or (-2 <= odds_change_pct <= 2):
            return 1.00, {
                "direction": "NEUTRAL",
                "icon": "➡️",
                "change_pct": odds_change_pct,
                "signal": "Cote stable - marché équilibré",
                "confidence": "NEUTRAL"
            }
        
        elif odds_movement == 'drifting_slow' or (2 < odds_change_pct <= 5):
            return 0.92, {
                "direction": "WARNING",
                "icon": "📉",
                "change_pct": odds_change_pct,
                "signal": "Cote monte légèrement - prudence",
                "confidence": "LOW"
            }
        
        elif odds_movement == 'drifting_fast' or odds_change_pct > 5:
            return 0.85, {
                "direction": "DANGER",
                "icon": "⚠️",
                "change_pct": odds_change_pct,
                "signal": "Cote monte fortement - info cachée probable!",
                "confidence": "VERY_LOW"
            }
        
        return 1.0, {
            "direction": "UNKNOWN",
            "icon": "❓",
            "signal": "Mouvement de cote inconnu",
            "confidence": "UNKNOWN"
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DÉTECTION DES DIVERGENCES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _detect_divergences(self, s_data: float, s_value: float,
                            s_pattern: float, s_ml: float,
                            ml_signal: Dict, match_data: Dict) -> List[Dict]:
        """
        Détecte les divergences entre sources
        
        C'EST SOUVENT LÀ QU'EST L'ARGENT!
        Quand les sources ne sont pas d'accord, il y a potentiellement
        une opportunité de trading.
        """
        divergences = []
        
        # ═══ xG vs Pattern ═══
        if abs(s_data - s_pattern) > 25:
            severity = "HIGH" if abs(s_data - s_pattern) > 40 else "MEDIUM"
            
            if s_data > s_pattern:
                insight = "Les stats récentes (xG) sont meilleures que l'historique. " \
                         "Amélioration récente ou anomalie?"
            else:
                insight = "L'historique (patterns) est meilleur que les stats récentes. " \
                         "Régression vers la moyenne possible."
            
            divergences.append({
                "type": "DATA_VS_PATTERN",
                "icon": "⚡",
                "severity": severity,
                "s_data": round(s_data, 1),
                "s_pattern": round(s_pattern, 1),
                "gap": round(abs(s_data - s_pattern), 1),
                "description": f"xG suggère {s_data:.0f}/100 mais patterns historiques {s_pattern:.0f}/100",
                "insight": insight,
                "action": "Analyse humaine requise - potentiel value contrarian"
            })
        
        # ═══ Value vs Data ═══
        if abs(s_value - s_data) > 30:
            if s_value > s_data:
                insight = "Le marché voit plus de value que les stats ne suggèrent. " \
                         "Soit le marché a tort, soit il y a une info cachée."
            else:
                insight = "Les stats sont meilleures que ce que le marché price. " \
                         "Potentielle value betting."
            
            divergences.append({
                "type": "VALUE_VS_DATA",
                "icon": "💰",
                "severity": "MEDIUM",
                "s_value": round(s_value, 1),
                "s_data": round(s_data, 1),
                "gap": round(abs(s_value - s_data), 1),
                "description": f"Value {s_value:.0f}/100 vs Stats {s_data:.0f}/100",
                "insight": insight,
                "action": "Vérifier si edge réel ou piège"
            })
        
        # ═══ ML Divergence (déjà calculée) ═══
        if ml_signal.get('type') == 'SINGLE_AGENT_DIVERGENCE':
            divergences.append({
                "type": "ML_SINGLE_AGENT",
                "icon": "🤖",
                "severity": "HIGH",
                "agent": ml_signal.get('outlier_agent'),
                "agent_score": ml_signal.get('outlier_score'),
                "others_avg": ml_signal.get('others_average'),
                "description": ml_signal.get('insight'),
                "insight": "Un agent a peut-être capté une info privilégiée",
                "action": "Investiguer ce que l'agent a détecté"
            })
        
        # ═══ Full Gain vs FERRARI ═══
        full_gain_score = float(match_data.get('full_gain_score') or 50)
        ferrari_score = (s_pattern + s_data) / 2
        
        if abs(full_gain_score - ferrari_score) > 25:
            divergences.append({
                "type": "FULLGAIN_VS_FERRARI",
                "icon": "🏎️",
                "severity": "MEDIUM",
                "full_gain": round(full_gain_score, 1),
                "ferrari": round(ferrari_score, 1),
                "gap": round(abs(full_gain_score - ferrari_score), 1),
                "description": f"Full Gain dit {full_gain_score:.0f} vs FERRARI dit {ferrari_score:.0f}",
                "insight": "Les deux systèmes ne sont pas d'accord",
                "action": "Priorité au système avec plus de contexte"
            })
        
        return divergences
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ANALYSE DES BUTEURS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _analyze_scorers_matchup(self, home_scorers: List, away_scorers: List,
                                  home_intel: Dict, away_intel: Dict) -> Dict:
        """
        Analyse détaillée des buteurs vs défense adverse
        
        Utilise des RATIOS MATHÉMATIQUES au lieu de +20 arbitraires
        """
        analysis = {"home": [], "away": []}
        
        # ═══ Analyse buteurs domicile vs défense extérieure ═══
        away_defense = self._get_defense_profile(away_intel)
        
        for scorer in home_scorers[:3]:
            matchup = self._calculate_scorer_matchup(scorer, away_defense, is_home=True)
            analysis["home"].append(matchup)
        
        # ═══ Analyse buteurs extérieurs vs défense domicile ═══
        home_defense = self._get_defense_profile(home_intel)
        
        for scorer in away_scorers[:3]:
            matchup = self._calculate_scorer_matchup(scorer, home_defense, is_home=False)
            analysis["away"].append(matchup)
        
        return analysis
    
    def _get_defense_profile(self, team_intel: Dict) -> Dict:
        """Extrait le profil défensif d'une équipe"""
        if not team_intel:
            return {
                "goals_conceded_avg": 1.5,
                "clean_sheet_rate": 0.20,
                "headers_conceded_pct": 0.15,
                "penalties_conceded_rate": 0.10,
                "weakness_tags": []
            }
        
        # Estimation du % de buts concédés sur headers
        # (normalement calculé à partir des données détaillées)
        goals_conceded = float(team_intel.get('away_goals_conceded_avg') or 
                              team_intel.get('home_goals_conceded_avg') or 1.5)
        
        clean_sheet = float(team_intel.get('away_clean_sheet_rate') or 
                           team_intel.get('home_clean_sheet_rate') or 20) / 100
        
        # Tags de faiblesse (depuis les données)
        tags = team_intel.get('tags', [])
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except:
                tags = []
        
        weakness_tags = [t for t in tags if 'weak' in str(t).lower() or 
                        'vulnerable' in str(t).lower()]
        
        # Estimation headers concédés (si équipe concède beaucoup, 
        # probablement faible sur les coups de pied arrêtés)
        headers_pct = 0.15 + (0.05 if goals_conceded > 1.8 else 0)
        
        return {
            "goals_conceded_avg": goals_conceded,
            "clean_sheet_rate": clean_sheet,
            "headers_conceded_pct": headers_pct,
            "penalties_conceded_rate": 0.10,
            "weakness_tags": weakness_tags,
            "is_weak_defense": goals_conceded > 1.7
        }
    
    def _calculate_scorer_matchup(self, scorer: Dict, defense: Dict,
                                   is_home: bool) -> Dict:
        """
        Calcule le matchup d'un buteur vs une défense
        Utilise des RATIOS MATHÉMATIQUES
        """
        player_name = scorer.get('player_name', 'Unknown')
        season_goals = int(scorer.get('season_goals') or 0)
        goals_per_match = float(scorer.get('goals_per_match') or 0)
        
        # Stats du buteur
        goals_header = int(scorer.get('goals_header') or 0)
        goals_penalty = int(scorer.get('goals_penalty') or 0)
        anytime_prob = float(scorer.get('anytime_scorer_prob') or 0)
        
        # Home/Away specific
        if is_home:
            specific_prob = float(scorer.get('home_anytime_prob') or anytime_prob)
            specific_goals = float(scorer.get('home_goals_per_match') or goals_per_match)
        else:
            specific_prob = float(scorer.get('away_anytime_prob') or anytime_prob)
            specific_goals = float(scorer.get('away_goals_per_match') or goals_per_match)
        
        # ═══ CALCUL DES RATIOS MATHÉMATIQUES ═══
        
        matchup_score = 50
        matchup_notes = []
        matchup_tags = []
        
        # 1. RATIO AÉRIEN
        if season_goals > 0:
            header_rate = goals_header / season_goals
            defense_aerial_weakness = defense.get('headers_conceded_pct', 0.15)
            
            # Ratio: Si buteur marque 30% de tête et défense concède 20% sur headers
            # Ratio = 0.30 / 0.20 = 1.5 (avantage)
            if header_rate > 0.10 and defense_aerial_weakness > 0:
                aerial_ratio = header_rate / max(defense_aerial_weakness, 0.05)
                aerial_bonus = min((aerial_ratio - 1) * 25, 20)  # Cap à +20
                
                if aerial_ratio > 1.2:
                    matchup_score += aerial_bonus
                    matchup_notes.append(f"🎯 Fort de la tête ({header_rate*100:.0f}%) vs défense faible aérienne")
                    matchup_tags.append("AERIAL_ADVANTAGE")
        
        # 2. PENALTY TAKER vs Défense qui concède des penalties
        if scorer.get('is_penalty_taker'):
            matchup_score += 10
            matchup_notes.append("⚽ Tireur de penalty attitré")
            matchup_tags.append("PENALTY_TAKER")
            
            if defense.get('is_weak_defense'):
                matchup_score += 5
                matchup_notes.append("+ Défense qui concède des fautes")
        
        # 3. FORME RÉCENTE
        if scorer.get('is_hot_streak'):
            matchup_score += 15
            matchup_notes.append("🔥 En série de buts (hot streak)")
            matchup_tags.append("HOT_STREAK")
        elif scorer.get('is_cold_streak'):
            matchup_score -= 15
            matchup_notes.append("❄️ En panne de buts (cold streak)")
            matchup_tags.append("COLD_STREAK")
        
        # 4. GOALS vs TYPE D'OPPOSITION
        scoring_rate_vs_weak = float(scorer.get('scoring_rate_vs_bottom') or 0)
        if defense.get('is_weak_defense') and scoring_rate_vs_weak > goals_per_match:
            ratio = scoring_rate_vs_weak / max(goals_per_match, 0.01)
            if ratio > 1.2:
                matchup_score += 10
                matchup_notes.append(f"📈 Score plus vs défenses faibles ({scoring_rate_vs_weak:.2f}/m)")
                matchup_tags.append("WEAK_DEFENSE_HUNTER")
        
        # 5. PÉRIODE FAVORITE
        favorite_period = scorer.get('favorite_scoring_period')
        if favorite_period:
            matchup_notes.append(f"⏰ Marque souvent en {favorite_period}")
        
        # Cap le score
        matchup_score = max(0, min(100, matchup_score))
        
        return {
            "player_name": player_name,
            "season_goals": season_goals,
            "goals_per_match": round(goals_per_match, 2),
            "specific_goals_per_match": round(specific_goals, 2),
            "anytime_prob": round(specific_prob or anytime_prob, 1),
            "matchup_score": round(matchup_score),
            "matchup_notes": matchup_notes,
            "matchup_tags": matchup_tags,
            "is_penalty_taker": scorer.get('is_penalty_taker', False),
            "is_hot_streak": scorer.get('is_hot_streak', False),
            "goals_header": goals_header,
            "defense_weakness": "Weak" if defense.get('is_weak_defense') else "Solid"
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ANALYSE TACTIQUE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _analyze_tactical_matchup(self, home: Dict, away: Dict) -> Dict:
        """Analyse du matchup tactique entre les deux équipes"""
        if not home or not away:
            return {"available": False}
        
        home_style = home.get('current_style', 'balanced')
        away_style = away.get('current_style', 'balanced')
        home_pressing = home.get('current_pressing', 'medium')
        away_pressing = away.get('current_pressing', 'medium')
        
        # Coach info
        home_coach = home.get('current_coach', 'Unknown')
        away_coach = away.get('current_coach', 'Unknown')
        home_coach_style = home.get('coach_style', 'balanced')
        
        # Matchup analysis
        style_matchup = self._analyze_style_matchup(home_style, away_style)
        
        insights = []
        market_implications = []
        
        # Pressing high vs low block
        if home_pressing == 'high' and away_pressing == 'low':
            insights.append("🎮 Pressing haut vs bloc bas - match potentiellement fermé")
            market_implications.append({"market": "Under 2.5", "impact": "POSITIVE"})
        
        # Possession vs Counter
        if 'possession' in home_style.lower() and 'counter' in away_style.lower():
            insights.append("⚽ Possession vs Contre - Attention aux contres rapides")
            market_implications.append({"market": "BTTS", "impact": "POSITIVE"})
        
        # Deux équipes offensives
        home_goals_tendency = int(home.get('goals_tendency') or 50)
        away_goals_tendency = int(away.get('goals_tendency') or 50)
        
        if home_goals_tendency > 60 and away_goals_tendency > 60:
            insights.append("🔥 Deux équipes à tendance offensive - match ouvert attendu")
            market_implications.append({"market": "Over 2.5", "impact": "VERY_POSITIVE"})
        
        # Deux équipes défensives
        if home_goals_tendency < 40 and away_goals_tendency < 40:
            insights.append("🛡️ Deux équipes défensives - peu de buts attendus")
            market_implications.append({"market": "Under 2.5", "impact": "VERY_POSITIVE"})
        
        return {
            "available": True,
            "home_style": home_style,
            "away_style": away_style,
            "home_pressing": home_pressing,
            "away_pressing": away_pressing,
            "home_coach": home_coach,
            "away_coach": away_coach,
            "style_matchup_score": style_matchup,
            "insights": insights,
            "market_implications": market_implications
        }
    
    def _analyze_style_matchup(self, home_style: str, away_style: str) -> float:
        """
        Analyse compatibilité des styles de jeu
        Retourne un score 0-100 représentant l'avantage domicile
        """
        home_style = home_style.lower() if home_style else 'balanced'
        away_style = away_style.lower() if away_style else 'balanced'
        
        # Matrice de matchup
        matchups = {
            # (home, away): score (>50 = avantage home)
            ("possession", "counter"): 45,      # Possession vulnérable au contre
            ("possession", "defensive"): 40,    # Bus parking dur à percer
            ("possession", "possession"): 55,   # Match ouvert, léger avantage dom
            ("possession", "balanced"): 52,
            
            ("counter", "possession"): 60,      # Contre-attaque vs possession = avantage
            ("counter", "counter"): 50,
            ("counter", "defensive"): 48,
            ("counter", "balanced"): 52,
            
            ("direct", "defensive"): 55,        # Jeu direct peut surprendre
            ("direct", "possession"): 58,
            ("direct", "counter"): 50,
            ("direct", "balanced"): 53,
            
            ("defensive", "possession"): 45,    # Défensif à domicile pas top
            ("defensive", "counter"): 48,
            ("defensive", "defensive"): 50,     # Match fermé
            ("defensive", "balanced"): 47,
            
            ("balanced", "balanced"): 55,       # Léger avantage domicile
            ("balanced", "possession"): 53,
            ("balanced", "counter"): 52,
            ("balanced", "defensive"): 55,
        }
        
        return matchups.get((home_style, away_style), 50)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RECOMMANDATIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _generate_recommendations(self, score: float, patterns: List,
                                   home: Dict, away: Dict,
                                   home_scorers: List, away_scorers: List,
                                   divergences: List,
                                   volatility_warnings: List) -> List[Dict]:
        """Génère les recommandations basées sur toutes les données"""
        recs = []
        tier = self._get_tier(score)
        
        # ═══ RECOMMANDATION PRINCIPALE ═══
        if tier == "ELITE":
            recs.append({
                "type": "MAIN",
                "priority": 1,
                "icon": "🏆",
                "action": "STRONG BET",
                "stake": "2-3% bankroll",
                "confidence": "TRÈS HAUTE",
                "reason": f"Score PRO {score:.0f}/100 - Toutes les conditions sont réunies"
            })
        elif tier == "DIAMOND":
            recs.append({
                "type": "MAIN",
                "priority": 1,
                "icon": "💎",
                "action": "BET",
                "stake": "1.5-2% bankroll",
                "confidence": "HAUTE",
                "reason": f"Score PRO {score:.0f}/100 - Excellente opportunité"
            })
        elif tier == "STRONG":
            recs.append({
                "type": "MAIN",
                "priority": 1,
                "icon": "⚡",
                "action": "CONSIDER",
                "stake": "1-1.5% bankroll",
                "confidence": "MOYENNE",
                "reason": f"Score PRO {score:.0f}/100 - Bon potentiel avec prudence"
            })
        elif tier == "STANDARD":
            recs.append({
                "type": "MAIN",
                "priority": 1,
                "icon": "✅",
                "action": "SMALL BET",
                "stake": "0.5-1% bankroll",
                "confidence": "MODÉRÉE",
                "reason": f"Score PRO {score:.0f}/100 - Acceptable mais pas idéal"
            })
        else:  # SKIP
            recs.append({
                "type": "MAIN",
                "priority": 1,
                "icon": "⚠️",
                "action": "SKIP",
                "stake": "0%",
                "confidence": "BASSE",
                "reason": f"Score PRO {score:.0f}/100 - Conditions insuffisantes"
            })
        
        # ═══ RECOMMANDATIONS PATTERNS ═══
        for p in patterns[:3]:
            if p.get('is_profitable') and float(p.get('roi', 0)) > 5:
                recs.append({
                    "type": "PATTERN",
                    "priority": 2,
                    "icon": "🏎️",
                    "market": p.get('market_type'),
                    "pattern_name": p.get('pattern_name'),
                    "win_rate": f"{p.get('win_rate')}%",
                    "roi": f"+{p.get('roi')}%",
                    "sample": p.get('sample_size'),
                    "action": p.get('recommendation', 'CONSIDER')
                })
        
        # ═══ RECOMMANDATIONS BUTEURS ═══
        for scorer in home_scorers[:2]:
            prob = float(scorer.get('anytime_scorer_prob') or 0)
            if prob > 35:
                recs.append({
                    "type": "SCORER",
                    "priority": 3,
                    "icon": "⚽",
                    "player": scorer.get('player_name'),
                    "market": "Anytime Scorer",
                    "probability": f"{prob:.0f}%",
                    "goals_season": scorer.get('season_goals'),
                    "insight": self._get_scorer_quick_insight(scorer)
                })
        
        # ═══ ALERTES VOLATILITÉ ═══
        for vol in volatility_warnings:
            recs.append({
                "type": "VOLATILITY_WARNING",
                "priority": 0,  # Haute priorité
                "icon": "⚠️",
                "action": "ATTENTION",
                "pattern": vol.get('pattern_name', 'Pattern'),
                "warning": vol.get('warning_message'),
                "max_stake": f"{vol.get('max_stake_recommended', 0.25)}%"
            })
        
        # ═══ ALERTES DIVERGENCE ═══
        for div in divergences:
            if div.get('severity') == 'HIGH':
                recs.append({
                    "type": "DIVERGENCE_ALERT",
                    "priority": 0,
                    "icon": "⚡",
                    "action": "ANALYSE MANUELLE",
                    "description": div.get('description'),
                    "insight": div.get('insight'),
                    "action_required": div.get('action')
                })
        
        # Trier par priorité
        recs.sort(key=lambda x: x.get('priority', 5))
        
        return recs
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _get_tier(self, score: float) -> str:
        """Détermine le tier basé sur le score"""
        if score >= 90:
            return "ELITE"
        elif score >= 80:
            return "DIAMOND"
        elif score >= 70:
            return "STRONG"
        elif score >= 60:
            return "STANDARD"
        else:
            return "SKIP"
    
    def _get_tier_emoji(self, score: float) -> str:
        """Emoji pour le tier"""
        tier = self._get_tier(score)
        emojis = {
            "ELITE": "🏆",
            "DIAMOND": "💎",
            "STRONG": "⚡",
            "STANDARD": "✅",
            "SKIP": "⚠️"
        }
        return emojis.get(tier, "❓")
    
    def _get_risk_level(self, k_risk: float) -> str:
        """Niveau de risque basé sur K_RISK"""
        if k_risk >= 1.0:
            return "LOW"
        elif k_risk >= 0.85:
            return "MEDIUM"
        elif k_risk >= 0.70:
            return "HIGH"
        else:
            return "CRITICAL"
    
    def _summarize_team(self, intel: Dict) -> Dict:
        """Résumé des stats équipe pour le frontend"""
        if not intel:
            return {"available": False}
        
        return {
            "available": True,
            "name": intel.get('team_name', 'Unknown'),
            "league": intel.get('league'),
            "style": intel.get('current_style', 'balanced'),
            "pressing": intel.get('current_pressing', 'medium'),
            "form": intel.get('current_form', 'neutral'),
            "form_points": intel.get('current_form_points'),
            "home_win_rate": intel.get('home_win_rate'),
            "home_btts_rate": intel.get('home_btts_rate'),
            "home_over25_rate": intel.get('home_over25_rate'),
            "home_clean_sheet": intel.get('home_clean_sheet_rate'),
            "away_win_rate": intel.get('away_win_rate'),
            "away_btts_rate": intel.get('away_btts_rate'),
            "away_over25_rate": intel.get('away_over25_rate'),
            "xg_for": intel.get('xg_for_avg'),
            "xg_against": intel.get('xg_against_avg'),
            "xg_difference": intel.get('xg_difference'),
            "late_goals_pct": intel.get('late_goals_pct'),
            "comeback_rate": intel.get('comeback_rate'),
            "first_scorer_rate": intel.get('first_scorer_rate'),
            "coach": intel.get('current_coach'),
            "coach_style": intel.get('coach_style'),
            "goals_tendency": intel.get('goals_tendency'),
            "btts_tendency": intel.get('btts_tendency'),
            "tags": intel.get('tags', []),
            "data_quality": intel.get('data_quality_score', 50),
            "confidence": intel.get('confidence_overall', 50)
        }
    
    def _get_scorer_quick_insight(self, scorer: Dict) -> str:
        """Génère un insight rapide pour un buteur"""
        insights = []
        
        if scorer.get('is_hot_streak'):
            insights.append("🔥 Hot")
        if scorer.get('is_penalty_taker'):
            insights.append("⚽ Pen")
        if float(scorer.get('goals_per_match', 0) or 0) > 0.8:
            insights.append("💎 Prolific")
        if int(scorer.get('goals_header', 0) or 0) > 3:
            insights.append("🎯 Header")
        if scorer.get('is_cold_streak'):
            insights.append("❄️ Cold")
        
        return " | ".join(insights) if insights else "Standard"


# ═══════════════════════════════════════════════════════════════════════════════
# VOLATILITY ANALYZER
# ═══════════════════════════════════════════════════════════════════════════════

class VolatilityAnalyzer:
    """
    Analyse la volatilité des paris
    Détecte les pièges haute variance comme le "0-0 à +100% ROI"
    """
    
    @staticmethod
    def analyze_pattern_volatility(pattern: Dict) -> Dict:
        """
        Analyse la volatilité d'un pattern
        
        IMPORTANT: Un ROI de +100% avec 13% win rate = HAUTE VOLATILITÉ
        L'utilisateur va perdre 87% du temps avant de voir le profit
        """
        win_rate = float(pattern.get('win_rate') or 50)
        roi = float(pattern.get('roi') or 0)
        sample = int(pattern.get('sample_size') or 10)
        pattern_name = pattern.get('pattern_name', 'Unknown')
        
        # Calcul de la variance
        # Formule: Plus le win rate est bas et le ROI haut, plus la variance est élevée
        loss_rate = 100 - win_rate
        
        # Nombre de paris nécessaires pour convergence (règle statistique)
        # Environ 1/(win_rate/100)² pour avoir une confiance raisonnable
        if win_rate > 0:
            bets_to_converge = int(min(10000 / (win_rate ** 1.5), 2000))
        else:
            bets_to_converge = 9999
        
        # Score de variance (0-100, plus c'est haut plus c'est volatile)
        variance_score = (loss_rate * abs(roi) / 100) if roi > 0 else loss_rate * 0.5
        variance_score = min(variance_score, 100)
        
        # Seuils de haute volatilité
        is_high_volatility = (
            (win_rate < 25 and roi > 20) or     # Bas win rate + ROI positif
            (win_rate < 15) or                    # Très bas win rate
            (variance_score > 60)                 # Score variance élevé
        )
        
        is_extreme_volatility = (
            (win_rate < 15 and roi > 50) or
            (variance_score > 80)
        )
        
        if is_extreme_volatility:
            return {
                "pattern_name": pattern_name,
                "is_high_volatility": True,
                "warning_level": "EXTREME",
                "icon": "💀",
                "win_rate": win_rate,
                "roi": roi,
                "variance_score": round(variance_score, 1),
                "required_bets_to_converge": bets_to_converge,
                "max_stake_recommended": 0.10,
                "warning_message": f"�� VOLATILITÉ EXTRÊME: {pattern_name}\n"
                                   f"• Tu perdras {loss_rate:.0f}% du temps\n"
                                   f"• Il faut ~{bets_to_converge} paris pour voir le profit\n"
                                   f"• Stake MAX: 0.10% bankroll\n"
                                   f"• RÉSERVÉ AUX PROFESSIONNELS avec gros bankroll"
            }
        
        elif is_high_volatility:
            return {
                "pattern_name": pattern_name,
                "is_high_volatility": True,
                "warning_level": "HIGH",
                "icon": "⚠️",
                "win_rate": win_rate,
                "roi": roi,
                "variance_score": round(variance_score, 1),
                "required_bets_to_converge": bets_to_converge,
                "max_stake_recommended": 0.25,
                "warning_message": f"⚠️ HAUTE VOLATILITÉ: {pattern_name}\n"
                                   f"• Tu perdras {loss_rate:.0f}% du temps\n"
                                   f"• Il faut ~{bets_to_converge} paris pour voir le profit\n"
                                   f"• Stake MAX: 0.25% bankroll\n"
                                   f"• Es-tu prêt à perdre 10+ fois de suite?"
            }
        
        return {
            "pattern_name": pattern_name,
            "is_high_volatility": False,
            "warning_level": "LOW",
            "icon": "✅",
            "win_rate": win_rate,
            "roi": roi,
            "variance_score": round(variance_score, 1)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CORRELATION CHECKER
# ═══════════════════════════════════════════════════════════════════════════════

class CorrelationChecker:
    """
    Vérifie les corrélations entre picks
    Évite les combos à haute corrélation qui multiplient le risque
    """
    
    def check_picks_correlation(self, picks: List[Dict]) -> Dict:
        """
        Analyse la corrélation entre plusieurs picks
        
        Args:
            picks: Liste de picks avec {match, league, market, team}
        
        Returns:
            Analyse de corrélation avec warnings
        """
        if len(picks) < 2:
            return {
                "correlation_pct": 0,
                "warning": None,
                "safe_for_combo": True
            }
        
        # ═══ Grouper par ligue ═══
        leagues = {}
        for pick in picks:
            league = pick.get('league', 'unknown')
            if league not in leagues:
                leagues[league] = []
            leagues[league].append(pick)
        
        # ═══ Grouper par marché ═══
        markets = {}
        for pick in picks:
            market = pick.get('market', 'unknown')
            if market not in markets:
                markets[market] = []
            markets[market].append(pick)
        
        # ═══ Calcul corrélation ═══
        max_same_league = max(len(v) for v in leagues.values()) if leagues else 0
        max_same_market = max(len(v) for v in markets.values()) if markets else 0
        
        correlation = 0
        details = []
        
        # Même ligue = +15% par pick supplémentaire
        if max_same_league > 1:
            league_correlation = (max_same_league - 1) * 15
            correlation += league_correlation
            details.append(f"{max_same_league} picks même ligue (+{league_correlation}%)")
        
        # Même marché = +10% par pick supplémentaire
        if max_same_market > 1:
            market_correlation = (max_same_market - 1) * 10
            correlation += market_correlation
            details.append(f"{max_same_market} picks même marché (+{market_correlation}%)")
        
        # Même journée = +5% base (déjà implicite dans combo)
        correlation += 5
        
        # ═══ Déterminer le warning ═══
        warning = None
        safe_for_combo = True
        
        if correlation > 50:
            warning = {
                "level": "CRITICAL",
                "icon": "🔴",
                "message": f"Corrélation CRITIQUE ({correlation}%). "
                          f"Ces picks vont probablement gagner ou perdre ensemble. "
                          f"Combo très risqué!",
                "details": details
            }
            safe_for_combo = False
        
        elif correlation > 35:
            warning = {
                "level": "HIGH",
                "icon": "🟠",
                "message": f"Corrélation ÉLEVÉE ({correlation}%). "
                          f"Risque amplifié si un pick perd.",
                "details": details
            }
            safe_for_combo = False
        
        elif correlation > 20:
            warning = {
                "level": "MEDIUM",
                "icon": "🟡",
                "message": f"Corrélation modérée ({correlation}%). "
                          f"Acceptable mais attention.",
                "details": details
            }
        
        return {
            "correlation_pct": correlation,
            "same_league_max": max_same_league,
            "same_market_max": max_same_market,
            "details": details,
            "warning": warning,
            "safe_for_combo": safe_for_combo,
            "recommendation": self._get_diversification_tip(leagues, markets)
        }
    
    def _get_diversification_tip(self, leagues: Dict, markets: Dict) -> str:
        """Conseils de diversification"""
        tips = []
        
        if len(leagues) < 3 and sum(len(v) for v in leagues.values()) >= 3:
            tips.append("Ajoute des picks d'autres ligues")
        
        over_under_count = sum(1 for m in markets.keys() 
                              if 'over' in m.lower() or 'under' in m.lower())
        if over_under_count > 2:
            tips.append("Trop de Over/Under - diversifie les marchés")
        
        if not tips:
            return "Diversification acceptable"
        
        return " | ".join(tips)


# ═══════════════════════════════════════════════════════════════════════════════
# COMBO BUILDER INTELLIGENT
# ═══════════════════════════════════════════════════════════════════════════════

class ComboBuilder:
    """
    Construit des combos intelligents avec faible corrélation
    """
    
    def __init__(self):
        self.correlation_checker = CorrelationChecker()
    
    def build_safe_combo(self, available_picks: List[Dict], 
                         target_odds: float = 3.0,
                         max_picks: int = 3) -> List[Dict]:
        """
        Construit un combo sûr avec corrélation minimale
        
        Args:
            available_picks: Picks disponibles triés par score
            target_odds: Cote cible du combo
            max_picks: Nombre max de picks
        """
        if not available_picks:
            return []
        
        # Trier par score décroissant
        sorted_picks = sorted(available_picks, 
                             key=lambda x: x.get('score', 0), 
                             reverse=True)
        
        selected = []
        used_leagues = set()
        used_markets = set()
        cumulative_odds = 1.0
        
        for pick in sorted_picks:
            if len(selected) >= max_picks:
                break
            
            if cumulative_odds >= target_odds * 1.5:  # Déjà assez de cote
                break
            
            league = pick.get('league', '')
            market = pick.get('market', '')
            odds = float(pick.get('odds', 1.5) or 1.5)
            
            # Vérifier corrélation
            # Préférer ligues et marchés différents
            league_penalty = 1 if league in used_leagues else 0
            market_penalty = 1 if market in used_markets else 0
            
            if league_penalty + market_penalty <= 1:  # Max 1 duplication
                selected.append(pick)
                used_leagues.add(league)
                used_markets.add(market)
                cumulative_odds *= odds
        
        # Vérifier corrélation finale
        correlation = self.correlation_checker.check_picks_correlation(selected)
        
        return {
            "picks": selected,
            "total_odds": round(cumulative_odds, 2),
            "correlation": correlation,
            "is_safe": correlation.get('safe_for_combo', False)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    'ProScoreV3Calculator',
    'VolatilityAnalyzer',
    'CorrelationChecker',
    'ComboBuilder',
    'DatabasePool',
    'db_pool'
]



# ═══════════════════════════════════════════════════════════════════════════════
# SWEET SPOTS INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

class SweetSpotIntegration:
    """
    Intègre les Sweet Spots (tracking_clv_picks) dans le calcul Pro Score
    2,868 picks disponibles avec 643 aujourd'hui!
    """
    
    def get_match_sweet_spots(self, home_team: str, away_team: str) -> List[Dict]:
        """
        Récupère les Sweet Spots pour un match donné
        """
        conn = db_pool.get_connection()
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT 
                    market_type,
                    prediction,
                    odds_taken,
                    clv_percentage,
                    diamond_score,
                    value_rating,
                    kelly_pct,
                    probability,
                    recommendation,
                    factors
                FROM tracking_clv_picks
                WHERE (home_team ILIKE %s OR match_name ILIKE %s)
                AND (away_team ILIKE %s OR match_name ILIKE %s)
                AND commence_time >= NOW()
                ORDER BY diamond_score DESC
            """, (f"%{home_team}%", f"%{home_team}%", f"%{away_team}%", f"%{away_team}%"))
            
            results = cur.fetchall()
            cur.close()
            return [dict(r) for r in results]
        except Exception as e:
            logger.error("get_sweet_spots_error", error=str(e))
            return []
        finally:
            db_pool.release_connection(conn)
    
    def get_today_elite_picks(self, min_score: int = 90) -> List[Dict]:
        """
        Récupère tous les picks ELITE du jour (69 picks score=100!)
        """
        conn = db_pool.get_connection()
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT 
                    match_name,
                    home_team,
                    away_team,
                    league,
                    market_type,
                    prediction,
                    odds_taken,
                    clv_percentage,
                    diamond_score,
                    value_rating,
                    kelly_pct,
                    probability,
                    recommendation,
                    commence_time
                FROM tracking_clv_picks
                WHERE DATE(commence_time) = CURRENT_DATE
                AND diamond_score >= %s
                ORDER BY diamond_score DESC, commence_time ASC
            """, (min_score,))
            
            results = cur.fetchall()
            cur.close()
            return [dict(r) for r in results]
        except Exception as e:
            logger.error("get_elite_picks_error", error=str(e))
            return []
        finally:
            db_pool.release_connection(conn)
    
    def get_today_stats(self) -> Dict:
        """
        Statistiques des Sweet Spots du jour
        """
        conn = db_pool.get_connection()
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN diamond_score >= 100 THEN 1 END) as elite_100,
                    COUNT(CASE WHEN diamond_score >= 90 THEN 1 END) as elite_90,
                    COUNT(CASE WHEN diamond_score >= 80 THEN 1 END) as diamond_plus,
                    AVG(diamond_score) as avg_score,
                    AVG(clv_percentage) as avg_edge
                FROM tracking_clv_picks
                WHERE DATE(commence_time) = CURRENT_DATE
            """)
            
            result = cur.fetchone()
            cur.close()
            return dict(result) if result else {}
        except Exception as e:
            logger.error("get_today_stats_error", error=str(e))
            return {}
        finally:
            db_pool.release_connection(conn)
    
    def calculate_sweet_spot_boost(self, sweet_spots: List[Dict]) -> Tuple[float, Dict]:
        """
        Calcule le boost basé sur les Sweet Spots
        
        Returns:
            - boost: Multiplicateur (1.0 à 1.15)
            - info: Détails sur les Sweet Spots
        """
        if not sweet_spots:
            return 1.0, {"found": False, "count": 0}
        
        # Compter les picks par qualité
        elite_count = sum(1 for s in sweet_spots if (s.get('diamond_score') or 0) >= 90)
        diamond_count = sum(1 for s in sweet_spots if (s.get('diamond_score') or 0) >= 80)
        
        # Moyenne des scores
        avg_score = sum(s.get('diamond_score') or 0 for s in sweet_spots) / len(sweet_spots)
        
        # Calcul du boost
        boost = 1.0
        if elite_count >= 2:
            boost = 1.15  # Multiple ELITE picks
        elif elite_count == 1:
            boost = 1.10  # Un ELITE pick
        elif diamond_count >= 2:
            boost = 1.08  # Multiple DIAMOND
        elif diamond_count == 1:
            boost = 1.05  # Un DIAMOND
        elif avg_score >= 70:
            boost = 1.03  # Bons picks
        
        return boost, {
            "found": True,
            "count": len(sweet_spots),
            "elite_count": elite_count,
            "diamond_count": diamond_count,
            "avg_score": round(avg_score, 1),
            "boost_applied": boost,
            "top_picks": sweet_spots[:3] if sweet_spots else []
        }
