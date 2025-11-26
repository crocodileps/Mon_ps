"""
FULL GAIN 2.0 - Moteur de Prédiction V2 PROFESSIONNEL
Algorithme avancé avec pondérations dynamiques et détection de value
"""
import os
import math
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Confidence(Enum):
    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


class Recommendation(Enum):
    STRONG_YES = "STRONG YES"
    YES = "YES"
    LEAN_YES = "LEAN YES"
    SKIP = "SKIP"
    LEAN_NO = "LEAN NO"
    NO = "NO"
    STRONG_NO = "STRONG NO"


@dataclass
class TeamStats:
    """Stats d'une équipe"""
    name: str
    matches_played: int
    btts_pct: float
    over25_pct: float
    over15_pct: float
    over35_pct: float
    clean_sheet_pct: float
    failed_to_score_pct: float
    avg_goals_scored: float
    avg_goals_conceded: float
    # Domicile/Extérieur
    home_btts_pct: float
    away_btts_pct: float
    home_over25_pct: float
    away_over25_pct: float
    home_avg_scored: float
    away_avg_scored: float
    home_avg_conceded: float
    away_avg_conceded: float
    home_clean_sheet_pct: float
    away_clean_sheet_pct: float
    # Tendances
    last5_btts_pct: float
    last5_over25_pct: float
    last5_form_points: int
    form: str
    current_streak: str
    # Qualité
    data_quality: int


@dataclass
class H2HStats:
    """Stats Head-to-Head"""
    total_matches: int
    btts_pct: float
    over25_pct: float
    avg_total_goals: float
    team_a_wins: int
    team_b_wins: int
    draws: int


class PredictionEngineV2:
    """
    Moteur de Prédiction V2 - Qualité Professionnelle
    
    Améliorations:
    - Pondérations dynamiques selon fiabilité
    - Plus de facteurs (clean sheets, FTS, avg goals)
    - Confidence score multi-critères
    - Value Bet detection avec cotes
    - Recommandations graduées
    """
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', '127.0.0.1'),
            'port': 5432,
            'database': os.getenv('DB_NAME', 'monps_db'),
            'user': os.getenv('DB_USER', 'monps_user'),
            'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
        }
    
    def _get_conn(self):
        return psycopg2.connect(**self.db_config)
    
    def _safe_float(self, value, default: float = 50.0) -> float:
        """Convertit en float avec valeur par défaut"""
        if value is None:
            return default
        try:
            return float(value)
        except:
            return default
    
    def get_team_stats(self, team_name: str) -> Optional[TeamStats]:
        """Récupère les stats complètes d'une équipe"""
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cur.execute("""
                SELECT * FROM team_statistics_live 
                WHERE team_name = %s
            """, (team_name,))
            row = cur.fetchone()
            
            if not row:
                return None
            
            return TeamStats(
                name=row['team_name'],
                matches_played=row.get('matches_played', 0),
                btts_pct=self._safe_float(row.get('btts_pct')),
                over25_pct=self._safe_float(row.get('over_25_pct')),
                over15_pct=self._safe_float(row.get('over_15_pct'), 75),
                over35_pct=self._safe_float(row.get('over_35_pct'), 30),
                clean_sheet_pct=self._safe_float(row.get('clean_sheet_pct'), 25),
                failed_to_score_pct=self._safe_float(row.get('failed_to_score_pct'), 25),
                avg_goals_scored=self._safe_float(row.get('avg_goals_scored'), 1.3),
                avg_goals_conceded=self._safe_float(row.get('avg_goals_conceded'), 1.3),
                home_btts_pct=self._safe_float(row.get('home_btts_pct')),
                away_btts_pct=self._safe_float(row.get('away_btts_pct')),
                home_over25_pct=self._safe_float(row.get('home_over25_pct')),
                away_over25_pct=self._safe_float(row.get('away_over25_pct')),
                home_avg_scored=self._safe_float(row.get('home_avg_scored'), 1.5),
                away_avg_scored=self._safe_float(row.get('away_avg_scored'), 1.1),
                home_avg_conceded=self._safe_float(row.get('home_avg_conceded'), 1.1),
                away_avg_conceded=self._safe_float(row.get('away_avg_conceded'), 1.5),
                home_clean_sheet_pct=self._safe_float(row.get('home_clean_sheet_pct'), 30),
                away_clean_sheet_pct=self._safe_float(row.get('away_clean_sheet_pct'), 20),
                last5_btts_pct=self._safe_float(row.get('last5_btts_pct')),
                last5_over25_pct=self._safe_float(row.get('last5_over25_pct')),
                last5_form_points=row.get('last5_form_points', 0) or 0,
                form=row.get('form', ''),
                current_streak=row.get('current_streak', ''),
                data_quality=row.get('data_quality_score', 50) or 50
            )
        finally:
            cur.close()
            conn.close()
    
    def get_h2h(self, team_a: str, team_b: str) -> Optional[H2HStats]:
        """Récupère le H2H entre deux équipes"""
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            t1, t2 = sorted([team_a, team_b])
            cur.execute("""
                SELECT * FROM team_head_to_head 
                WHERE team_a = %s AND team_b = %s
            """, (t1, t2))
            row = cur.fetchone()
            
            if not row:
                return None
            
            return H2HStats(
                total_matches=row.get('total_matches', 0),
                btts_pct=self._safe_float(row.get('btts_pct')),
                over25_pct=self._safe_float(row.get('over_25_pct')),
                avg_total_goals=self._safe_float(row.get('avg_total_goals'), 2.5),
                team_a_wins=row.get('team_a_wins', 0),
                team_b_wins=row.get('team_b_wins', 0),
                draws=row.get('draws', 0)
            )
        finally:
            cur.close()
            conn.close()
    
    def _calculate_dynamic_weights(self, home: TeamStats, away: TeamStats, h2h: Optional[H2HStats]) -> Dict:
        """
        Calcule les pondérations dynamiques selon la fiabilité des données
        Plus de matchs = plus de poids
        """
        # Base weights
        weights = {
            'home_global': 0.12,
            'away_global': 0.12,
            'home_specific': 0.15,  # home_btts_home ou away_btts_away
            'away_specific': 0.15,
            'home_trend': 0.10,
            'away_trend': 0.10,
            'h2h': 0.16,
            'goals_factor': 0.10,  # Nouveau: basé sur avg goals
        }
        
        # Ajuster selon la qualité des données
        home_reliability = min(home.matches_played / 15, 1.0)  # Max à 15 matchs
        away_reliability = min(away.matches_played / 15, 1.0)
        
        # Si peu de matchs, réduire le poids et redistribuer
        if home.matches_played < 5:
            weights['home_global'] *= 0.5
            weights['home_specific'] *= 0.5
            weights['home_trend'] *= 0.3
        
        if away.matches_played < 5:
            weights['away_global'] *= 0.5
            weights['away_specific'] *= 0.5
            weights['away_trend'] *= 0.3
        
        # H2H: ajuster selon le nombre de confrontations
        if h2h:
            if h2h.total_matches >= 5:
                weights['h2h'] = 0.20  # Plus de poids si beaucoup de H2H
            elif h2h.total_matches >= 3:
                weights['h2h'] = 0.16
            else:
                weights['h2h'] = 0.10
        else:
            weights['h2h'] = 0.0  # Pas de H2H disponible
        
        # Normaliser pour que la somme = 1
        total = sum(weights.values())
        return {k: v / total for k, v in weights.items()}
    
    def calculate_btts_score(self, home_team: str, away_team: str) -> Dict:
        """
        Calcule le score BTTS avec algorithme avancé
        
        Facteurs:
        1. BTTS% global des deux équipes
        2. BTTS% spécifique (domicile/extérieur)
        3. Tendances récentes (L5)
        4. H2H
        5. Clean Sheets (facteur négatif)
        6. Failed to Score (facteur négatif)
        """
        home = self.get_team_stats(home_team)
        away = self.get_team_stats(away_team)
        h2h = self.get_h2h(home_team, away_team)
        
        if not home or not away:
            return {
                'score': None, 
                'confidence': Confidence.VERY_LOW.value,
                'recommendation': Recommendation.SKIP.value,
                'error': 'Stats manquantes'
            }
        
        weights = self._calculate_dynamic_weights(home, away, h2h)
        
        # Calculer les facteurs
        factors = {}
        
        # 1. BTTS global
        factors['home_global'] = home.btts_pct
        factors['away_global'] = away.btts_pct
        
        # 2. BTTS spécifique (home à domicile, away à l'extérieur)
        factors['home_specific'] = home.home_btts_pct
        factors['away_specific'] = away.away_btts_pct
        
        # 3. Tendances récentes
        factors['home_trend'] = home.last5_btts_pct
        factors['away_trend'] = away.last5_btts_pct
        
        # 4. H2H
        factors['h2h'] = h2h.btts_pct if h2h else (factors['home_global'] + factors['away_global']) / 2
        
        # 5. Goals factor - probabilité que les deux marquent basée sur avg goals
        # P(home scores) ≈ 1 - e^(-avg_scored)
        # P(away scores) ≈ 1 - e^(-avg_scored)
        p_home_scores = 1 - math.exp(-home.home_avg_scored)
        p_away_scores = 1 - math.exp(-away.away_avg_scored)
        factors['goals_factor'] = (p_home_scores * p_away_scores) * 100
        
        # 6. Ajustement négatif: Clean Sheets et FTS
        # Si une équipe garde souvent sa cage inviolée, BTTS moins probable
        clean_sheet_penalty = (home.home_clean_sheet_pct + away.away_clean_sheet_pct) / 4
        fts_penalty = (home.failed_to_score_pct + away.failed_to_score_pct) / 4
        
        # Score brut
        raw_score = sum(factors[k] * weights[k] for k in weights.keys() if k in factors)
        
        # Appliquer les pénalités
        score = raw_score - clean_sheet_penalty - fts_penalty
        score = max(0, min(100, score))  # Clamp entre 0 et 100
        
        # Confidence multi-critères
        confidence = self._calculate_confidence(home, away, h2h)
        
        # Recommendation graduée
        recommendation = self._get_recommendation(score, confidence)
        
        return {
            'score': round(score, 1),
            'raw_score': round(raw_score, 1),
            'confidence': confidence.value,
            'confidence_score': self._confidence_to_score(confidence),
            'recommendation': recommendation.value,
            'factors': {
                'home_btts_global': round(factors['home_global'], 1),
                'away_btts_global': round(factors['away_global'], 1),
                'home_btts_home': round(factors['home_specific'], 1),
                'away_btts_away': round(factors['away_specific'], 1),
                'home_last5_btts': round(factors['home_trend'], 1),
                'away_last5_btts': round(factors['away_trend'], 1),
                'h2h_btts': round(factors['h2h'], 1),
                'goals_probability': round(factors['goals_factor'], 1),
                'clean_sheet_penalty': round(clean_sheet_penalty, 1),
                'fts_penalty': round(fts_penalty, 1),
            },
            'weights': {k: round(v, 3) for k, v in weights.items()},
            'home_analysis': {
                'team': home.name,
                'matches': home.matches_played,
                'btts_pct': home.btts_pct,
                'home_btts_pct': home.home_btts_pct,
                'last5_btts_pct': home.last5_btts_pct,
                'clean_sheet_pct': home.clean_sheet_pct,
                'avg_scored': home.home_avg_scored,
                'form': home.form,
                'streak': home.current_streak,
                'data_quality': home.data_quality
            },
            'away_analysis': {
                'team': away.name,
                'matches': away.matches_played,
                'btts_pct': away.btts_pct,
                'away_btts_pct': away.away_btts_pct,
                'last5_btts_pct': away.last5_btts_pct,
                'clean_sheet_pct': away.clean_sheet_pct,
                'avg_scored': away.away_avg_scored,
                'form': away.form,
                'streak': away.current_streak,
                'data_quality': away.data_quality
            },
            'h2h_analysis': {
                'available': h2h is not None,
                'total_matches': h2h.total_matches if h2h else 0,
                'btts_pct': h2h.btts_pct if h2h else None,
                'avg_goals': h2h.avg_total_goals if h2h else None
            }
        }
    
    def calculate_over25_score(self, home_team: str, away_team: str) -> Dict:
        """
        Calcule le score Over 2.5 avec algorithme avancé
        
        Facteurs:
        1. Over 2.5% global des deux équipes
        2. Over 2.5% spécifique (domicile/extérieur)
        3. Tendances récentes (L5)
        4. H2H
        5. Moyenne de buts attendus (Poisson-like)
        """
        home = self.get_team_stats(home_team)
        away = self.get_team_stats(away_team)
        h2h = self.get_h2h(home_team, away_team)
        
        if not home or not away:
            return {
                'score': None,
                'confidence': Confidence.VERY_LOW.value,
                'recommendation': Recommendation.SKIP.value,
                'error': 'Stats manquantes'
            }
        
        weights = self._calculate_dynamic_weights(home, away, h2h)
        
        factors = {}
        
        # 1. Over 2.5 global
        factors['home_global'] = home.over25_pct
        factors['away_global'] = away.over25_pct
        
        # 2. Over 2.5 spécifique
        factors['home_specific'] = home.home_over25_pct
        factors['away_specific'] = away.away_over25_pct
        
        # 3. Tendances
        factors['home_trend'] = home.last5_over25_pct
        factors['away_trend'] = away.last5_over25_pct
        
        # 4. H2H
        factors['h2h'] = h2h.over25_pct if h2h else (factors['home_global'] + factors['away_global']) / 2
        
        # 5. Expected Goals factor
        # Buts attendus = home_avg_scored + away_avg_scored (simplifié)
        expected_goals = home.home_avg_scored + away.away_avg_scored
        # P(total > 2.5) approximé par une fonction sigmoid
        factors['goals_factor'] = 100 / (1 + math.exp(-(expected_goals - 2.5) * 2))
        
        # Score
        score = sum(factors[k] * weights[k] for k in weights.keys() if k in factors)
        score = max(0, min(100, score))
        
        confidence = self._calculate_confidence(home, away, h2h)
        recommendation = self._get_recommendation(score, confidence, is_over=True)
        
        return {
            'score': round(score, 1),
            'confidence': confidence.value,
            'confidence_score': self._confidence_to_score(confidence),
            'recommendation': recommendation.value,
            'expected_goals': round(expected_goals, 2),
            'factors': {
                'home_over25_global': round(factors['home_global'], 1),
                'away_over25_global': round(factors['away_global'], 1),
                'home_over25_home': round(factors['home_specific'], 1),
                'away_over25_away': round(factors['away_specific'], 1),
                'home_last5_over25': round(factors['home_trend'], 1),
                'away_last5_over25': round(factors['away_trend'], 1),
                'h2h_over25': round(factors['h2h'], 1),
                'goals_probability': round(factors['goals_factor'], 1),
            }
        }
    
    def _calculate_confidence(self, home: TeamStats, away: TeamStats, h2h: Optional[H2HStats]) -> Confidence:
        """
        Calcule le niveau de confiance basé sur plusieurs critères:
        - Nombre de matchs des deux équipes
        - Data Quality Score
        - Disponibilité du H2H
        - Cohérence des données (variance)
        """
        score = 0
        
        # Matchs joués (max 30 points)
        matches_score = min((home.matches_played + away.matches_played) / 30 * 30, 30)
        score += matches_score
        
        # Data Quality (max 30 points)
        dq_score = (home.data_quality + away.data_quality) / 200 * 30
        score += dq_score
        
        # H2H disponible (max 20 points)
        if h2h and h2h.total_matches >= 3:
            score += 20
        elif h2h and h2h.total_matches >= 1:
            score += 10
        
        # Cohérence tendances vs global (max 20 points)
        home_coherence = 100 - abs(home.btts_pct - home.last5_btts_pct)
        away_coherence = 100 - abs(away.btts_pct - away.last5_btts_pct)
        coherence_score = (home_coherence + away_coherence) / 200 * 20
        score += coherence_score
        
        # Mapper le score à un niveau
        if score >= 80:
            return Confidence.VERY_HIGH
        elif score >= 65:
            return Confidence.HIGH
        elif score >= 50:
            return Confidence.MEDIUM
        elif score >= 35:
            return Confidence.LOW
        else:
            return Confidence.VERY_LOW
    
    def _confidence_to_score(self, conf: Confidence) -> int:
        """Convertit confidence en score numérique"""
        mapping = {
            Confidence.VERY_HIGH: 95,
            Confidence.HIGH: 80,
            Confidence.MEDIUM: 60,
            Confidence.LOW: 40,
            Confidence.VERY_LOW: 20
        }
        return mapping.get(conf, 50)
    
    def _get_recommendation(self, score: float, confidence: Confidence, is_over: bool = False) -> Recommendation:
        """
        Génère une recommandation graduée basée sur score et confidence
        """
        yes_label = "OVER 2.5" if is_over else "BTTS YES"
        no_label = "UNDER 2.5" if is_over else "BTTS NO"
        
        # Confidence faible = toujours SKIP sauf scores extrêmes
        if confidence in [Confidence.VERY_LOW, Confidence.LOW]:
            if score >= 80:
                return Recommendation.LEAN_YES
            elif score <= 20:
                return Recommendation.LEAN_NO
            else:
                return Recommendation.SKIP
        
        # Confidence medium+
        if score >= 75:
            return Recommendation.STRONG_YES if confidence == Confidence.VERY_HIGH else Recommendation.YES
        elif score >= 65:
            return Recommendation.YES if confidence in [Confidence.VERY_HIGH, Confidence.HIGH] else Recommendation.LEAN_YES
        elif score >= 55:
            return Recommendation.LEAN_YES
        elif score >= 45:
            return Recommendation.SKIP
        elif score >= 35:
            return Recommendation.LEAN_NO
        elif score >= 25:
            return Recommendation.NO if confidence in [Confidence.VERY_HIGH, Confidence.HIGH] else Recommendation.LEAN_NO
        else:
            return Recommendation.STRONG_NO if confidence == Confidence.VERY_HIGH else Recommendation.NO
    
    def calculate_value_bet(self, score: float, odds: float, market_type: str = "btts") -> Dict:
        """
        Détecte si c'est un Value Bet
        
        Value = (Probabilité implicite du score) vs (Probabilité implicite des cotes)
        """
        if not odds or odds <= 1:
            return {'is_value': False, 'reason': 'Cotes invalides'}
        
        # Notre probabilité estimée
        our_prob = score / 100
        
        # Probabilité implicite des cotes (sans marge)
        implied_prob = 1 / odds
        
        # Edge = notre prob - implied prob
        edge = our_prob - implied_prob
        
        # Expected Value
        ev = (our_prob * (odds - 1)) - (1 - our_prob)
        
        return {
            'is_value': edge > 0.05,  # Value si edge > 5%
            'our_probability': round(our_prob * 100, 1),
            'implied_probability': round(implied_prob * 100, 1),
            'edge': round(edge * 100, 2),
            'expected_value': round(ev * 100, 2),
            'odds': odds,
            'rating': 'STRONG VALUE' if edge > 0.15 else 'VALUE' if edge > 0.05 else 'FAIR' if edge > -0.05 else 'AVOID'
        }
    
    def predict_match(self, home_team: str, away_team: str, 
                      odds_btts_yes: float = None, odds_over25: float = None) -> Dict:
        """
        Prédiction complète pour un match avec analyse Value Bet
        """
        btts = self.calculate_btts_score(home_team, away_team)
        over25 = self.calculate_over25_score(home_team, away_team)
        
        result = {
            'home_team': home_team,
            'away_team': away_team,
            'btts': btts,
            'over25': over25,
            'generated_at': datetime.now().isoformat()
        }
        
        # Value Bet analysis si cotes fournies
        if odds_btts_yes and btts.get('score'):
            result['btts_value'] = self.calculate_value_bet(btts['score'], odds_btts_yes, 'btts')
        
        if odds_over25 and over25.get('score'):
            result['over25_value'] = self.calculate_value_bet(over25['score'], odds_over25, 'over25')
        
        # Score global du match
        if btts.get('score') and over25.get('score'):
            result['match_interest'] = self._calculate_match_interest(btts, over25)
        
        return result
    
    def _calculate_match_interest(self, btts: Dict, over25: Dict) -> Dict:
        """
        Calcule l'intérêt global du match pour les paris
        """
        btts_score = btts.get('score', 50)
        over25_score = over25.get('score', 50)
        
        # Un match est intéressant si au moins un marché a un score extrême
        max_deviation = max(abs(btts_score - 50), abs(over25_score - 50))
        
        # Combiner les recommandations
        strong_signals = 0
        if btts.get('recommendation') in ['STRONG YES', 'STRONG NO', 'YES', 'NO']:
            strong_signals += 1
        if over25.get('recommendation') in ['STRONG YES', 'STRONG NO', 'YES', 'NO']:
            strong_signals += 1
        
        return {
            'score': round((btts_score + over25_score) / 2, 1),
            'deviation': round(max_deviation, 1),
            'strong_signals': strong_signals,
            'rating': 'HIGH INTEREST' if max_deviation >= 20 and strong_signals >= 1 else 
                     'MEDIUM INTEREST' if max_deviation >= 10 else 'LOW INTEREST'
        }
