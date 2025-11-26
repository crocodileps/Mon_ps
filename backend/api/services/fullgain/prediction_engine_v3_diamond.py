"""
FULL GAIN 2.0 - Moteur V3 DIAMOND ULTIME
Algorithme professionnel niveau quant avec:
- Modèle Poisson pour probabilités exactes
- Pondération temporelle (decay)
- Momentum & Séries
- Home Advantage calibré par ligue
- Corrélation BTTS/Over
- Volatilité/Prévisibilité
- Kelly Criterion
- Combo intelligent
"""
import os
import math
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


# ============================================================
# ENUMS & DATACLASSES
# ============================================================

class Confidence(Enum):
    DIAMOND = "diamond"      # 95%+ - Très rare
    PLATINUM = "platinum"    # 85-94%
    GOLD = "gold"           # 70-84%
    SILVER = "silver"       # 55-69%
    BRONZE = "bronze"       # 40-54%
    IRON = "iron"           # <40%


class Recommendation(Enum):
    DIAMOND_PICK = "💎 DIAMOND PICK"
    STRONG_YES = "✅ STRONG YES"
    YES = "✅ YES"
    LEAN_YES = "📈 LEAN YES"
    NEUTRAL = "⚖️ NEUTRAL"
    LEAN_NO = "📉 LEAN NO"
    NO = "❌ NO"
    STRONG_NO = "❌ STRONG NO"


@dataclass
class PoissonResult:
    """Résultat du modèle Poisson"""
    home_xg: float
    away_xg: float
    total_xg: float
    btts_prob: float
    over15_prob: float
    over25_prob: float
    over35_prob: float
    under25_prob: float
    most_likely_scores: List[Tuple[str, float]]
    home_win_prob: float
    draw_prob: float
    away_win_prob: float


@dataclass
class TeamAnalysis:
    """Analyse complète d'une équipe"""
    name: str
    league: str
    matches_played: int
    
    # Stats générales
    btts_pct: float
    over25_pct: float
    clean_sheet_pct: float
    failed_to_score_pct: float
    avg_scored: float
    avg_conceded: float
    
    # Stats spécifiques (dom/ext)
    specific_btts_pct: float
    specific_over25_pct: float
    specific_avg_scored: float
    specific_avg_conceded: float
    specific_clean_sheet_pct: float
    
    # Tendances
    last5_btts_pct: float
    last5_over25_pct: float
    last5_form_points: int
    form: str
    streak: str
    
    # Avancé
    volatility: float  # Écart-type des scores
    momentum: float    # -1 à +1
    data_quality: int


@dataclass
class MatchPrediction:
    """Prédiction complète d'un match"""
    home_team: str
    away_team: str
    league: str
    
    # Poisson
    poisson: PoissonResult
    
    # Scores par marché
    btts_score: float
    over25_score: float
    over15_score: float
    over35_score: float
    
    # Confidence & Recommandation
    confidence: Confidence
    confidence_score: int
    btts_recommendation: Recommendation
    over25_recommendation: Recommendation
    
    # Value Bet
    btts_value: Dict
    over25_value: Dict
    
    # Kelly
    btts_kelly: float
    over25_kelly: float
    
    # Combo
    combo_btts_over25_prob: float
    combo_recommendation: str
    
    # Meta
    match_interest: str
    analysis_quality: str
    generated_at: str


# ============================================================
# HOME ADVANTAGE PAR LIGUE
# ============================================================

HOME_ADVANTAGE = {
    'Premier League': 1.15,      # Faible avantage
    'Ligue 1': 1.25,             # Moyen
    'Bundesliga': 1.20,          # Moyen
    'Serie A': 1.30,             # Fort
    'La Liga': 1.25,             # Moyen
    'Champions League': 1.10,    # Très faible (neutres)
    'default': 1.20
}


# ============================================================
# MOTEUR V3 DIAMOND
# ============================================================

class PredictionEngineDiamond:
    """
    Moteur V3 DIAMOND - Niveau Quantitatif Professionnel
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
        if value is None:
            return default
        try:
            return float(value)
        except:
            return default
    
    # ============================================================
    # MODÈLE POISSON
    # ============================================================
    
    def _poisson_prob(self, lam: float, k: int) -> float:
        """Probabilité Poisson P(X=k) = (λ^k * e^-λ) / k!"""
        if lam <= 0:
            return 1.0 if k == 0 else 0.0
        return (lam ** k) * math.exp(-lam) / math.factorial(k)
    
    def calculate_poisson(self, home_xg: float, away_xg: float, max_goals: int = 7) -> PoissonResult:
        """
        Calcule toutes les probabilités via le modèle Poisson
        """
        # Matrice des scores
        score_probs = {}
        home_win = draw = away_win = 0
        btts = over15 = over25 = over35 = 0
        
        for h in range(max_goals + 1):
            for a in range(max_goals + 1):
                prob = self._poisson_prob(home_xg, h) * self._poisson_prob(away_xg, a)
                score_probs[f"{h}-{a}"] = prob
                
                # Résultats
                if h > a:
                    home_win += prob
                elif h == a:
                    draw += prob
                else:
                    away_win += prob
                
                # BTTS
                if h > 0 and a > 0:
                    btts += prob
                
                # Over/Under
                total = h + a
                if total > 1:
                    over15 += prob
                if total > 2:
                    over25 += prob
                if total > 3:
                    over35 += prob
        
        # Top 5 scores les plus probables
        sorted_scores = sorted(score_probs.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return PoissonResult(
            home_xg=round(home_xg, 2),
            away_xg=round(away_xg, 2),
            total_xg=round(home_xg + away_xg, 2),
            btts_prob=round(btts * 100, 1),
            over15_prob=round(over15 * 100, 1),
            over25_prob=round(over25 * 100, 1),
            over35_prob=round(over35 * 100, 1),
            under25_prob=round((1 - over25) * 100, 1),
            most_likely_scores=[(s, round(p * 100, 1)) for s, p in sorted_scores],
            home_win_prob=round(home_win * 100, 1),
            draw_prob=round(draw * 100, 1),
            away_win_prob=round(away_win * 100, 1)
        )
    
    # ============================================================
    # MOMENTUM & SÉRIES
    # ============================================================
    
    def _calculate_momentum(self, form: str, streak: str) -> float:
        """
        Calcule le momentum (-1 à +1)
        W = +0.2, D = 0, L = -0.2
        Bonus série: +0.1 par match en série
        """
        if not form:
            return 0.0
        
        momentum = 0.0
        
        # Pondération temporelle (plus récent = plus important)
        weights = [0.35, 0.25, 0.20, 0.12, 0.08]  # L5
        
        for i, char in enumerate(form[:5]):
            if i < len(weights):
                if char == 'W':
                    momentum += weights[i]
                elif char == 'L':
                    momentum -= weights[i]
        
        # Bonus série
        if streak:
            try:
                streak_type = streak[0]
                streak_len = int(streak[1:]) if len(streak) > 1 else 1
                bonus = min(streak_len * 0.05, 0.2)
                
                if streak_type == 'W':
                    momentum += bonus
                elif streak_type == 'L':
                    momentum -= bonus
            except:
                pass
        
        return max(-1, min(1, momentum))
    
    # ============================================================
    # VOLATILITÉ
    # ============================================================
    
    def _calculate_volatility(self, team_name: str) -> float:
        """
        Calcule la volatilité (écart-type des scores)
        Équipe volatile = imprévisible
        """
        conn = self._get_conn()
        cur = conn.cursor()
        
        try:
            cur.execute("""
                SELECT 
                    STDDEV(CASE WHEN home_team = %s THEN score_home + score_away
                                WHEN away_team = %s THEN score_home + score_away END) as vol
                FROM match_results
                WHERE (home_team = %s OR away_team = %s) 
                AND is_finished = true AND score_home IS NOT NULL
            """, (team_name, team_name, team_name, team_name))
            
            row = cur.fetchone()
            return float(row[0]) if row and row[0] else 1.0
        except:
            return 1.0
        finally:
            cur.close()
            conn.close()
    
    # ============================================================
    # TEAM ANALYSIS
    # ============================================================
    
    def get_team_analysis(self, team_name: str, is_home: bool = True) -> Optional[TeamAnalysis]:
        """Analyse complète d'une équipe"""
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cur.execute("SELECT * FROM team_statistics_live WHERE team_name = %s", (team_name,))
            row = cur.fetchone()
            
            if not row:
                return None
            
            # Calculer momentum
            momentum = self._calculate_momentum(
                row.get('form', ''), 
                row.get('current_streak', '')
            )
            
            # Calculer volatilité
            volatility = self._calculate_volatility(team_name)
            
            # Stats spécifiques selon domicile/extérieur
            if is_home:
                specific_btts = self._safe_float(row.get('home_btts_pct'))
                specific_over25 = self._safe_float(row.get('home_over25_pct'))
                specific_scored = self._safe_float(row.get('home_avg_scored'), 1.5)
                specific_conceded = self._safe_float(row.get('home_avg_conceded'), 1.0)
                specific_cs = self._safe_float(row.get('home_clean_sheet_pct'), 30)
            else:
                specific_btts = self._safe_float(row.get('away_btts_pct'))
                specific_over25 = self._safe_float(row.get('away_over25_pct'))
                specific_scored = self._safe_float(row.get('away_avg_scored'), 1.1)
                specific_conceded = self._safe_float(row.get('away_avg_conceded'), 1.5)
                specific_cs = self._safe_float(row.get('away_clean_sheet_pct'), 20)
            
            return TeamAnalysis(
                name=row['team_name'],
                league=row.get('league', 'Unknown'),
                matches_played=row.get('matches_played', 0),
                btts_pct=self._safe_float(row.get('btts_pct')),
                over25_pct=self._safe_float(row.get('over_25_pct')),
                clean_sheet_pct=self._safe_float(row.get('clean_sheet_pct'), 25),
                failed_to_score_pct=self._safe_float(row.get('failed_to_score_pct'), 20),
                avg_scored=self._safe_float(row.get('avg_goals_scored'), 1.3),
                avg_conceded=self._safe_float(row.get('avg_goals_conceded'), 1.3),
                specific_btts_pct=specific_btts,
                specific_over25_pct=specific_over25,
                specific_avg_scored=specific_scored,
                specific_avg_conceded=specific_conceded,
                specific_clean_sheet_pct=specific_cs,
                last5_btts_pct=self._safe_float(row.get('last5_btts_pct')),
                last5_over25_pct=self._safe_float(row.get('last5_over25_pct')),
                last5_form_points=row.get('last5_form_points', 0) or 0,
                form=row.get('form', ''),
                streak=row.get('current_streak', ''),
                volatility=volatility,
                momentum=momentum,
                data_quality=row.get('data_quality_score', 50) or 50
            )
        finally:
            cur.close()
            conn.close()
    
    def get_h2h_stats(self, team_a: str, team_b: str) -> Optional[Dict]:
        """Récupère les stats H2H"""
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            t1, t2 = sorted([team_a, team_b])
            cur.execute("""
                SELECT * FROM team_head_to_head 
                WHERE team_a = %s AND team_b = %s
            """, (t1, t2))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            cur.close()
            conn.close()
    
    # ============================================================
    # EXPECTED GOALS (xG) AVANCÉ
    # ============================================================
    
    def calculate_expected_goals(self, home: TeamAnalysis, away: TeamAnalysis, league: str) -> Tuple[float, float]:
        """
        Calcule les Expected Goals avec:
        - Stats offensives/défensives
        - Home advantage calibré par ligue
        - Momentum
        - Pondération temporelle
        """
        # Home advantage
        ha_factor = HOME_ADVANTAGE.get(league, HOME_ADVANTAGE['default'])
        
        # xG Home = (home_attack + away_defense) / 2 * home_advantage * momentum
        home_attack = (home.specific_avg_scored * 0.6 + home.avg_scored * 0.4)
        away_defense = (away.specific_avg_conceded * 0.6 + away.avg_conceded * 0.4)
        
        home_xg = ((home_attack + away_defense) / 2) * ha_factor
        
        # Ajustement momentum
        home_xg *= (1 + home.momentum * 0.15)
        
        # xG Away = (away_attack + home_defense) / 2 / home_advantage * momentum
        away_attack = (away.specific_avg_scored * 0.6 + away.avg_scored * 0.4)
        home_defense = (home.specific_avg_conceded * 0.6 + home.avg_conceded * 0.4)
        
        away_xg = ((away_attack + home_defense) / 2) / ha_factor
        away_xg *= (1 + away.momentum * 0.15)
        
        # Clamp
        home_xg = max(0.3, min(4.0, home_xg))
        away_xg = max(0.2, min(3.5, away_xg))
        
        return home_xg, away_xg
    
    # ============================================================
    # SCORE BTTS DIAMOND
    # ============================================================
    
    def calculate_btts_score(self, home: TeamAnalysis, away: TeamAnalysis, 
                             h2h: Optional[Dict], poisson: PoissonResult) -> Dict:
        """
        Score BTTS avec algorithme Diamond:
        - Poisson probability (poids fort)
        - Stats historiques
        - Tendances récentes
        - H2H
        - Pénalités défensives
        - Momentum
        """
        # Facteurs avec pondérations dynamiques
        factors = {}
        weights = {}
        
        # 1. Poisson (35%)
        factors['poisson'] = poisson.btts_prob
        weights['poisson'] = 0.35
        
        # 2. Stats globales (15%)
        factors['global'] = (home.btts_pct + away.btts_pct) / 2
        weights['global'] = 0.15
        
        # 3. Stats spécifiques dom/ext (20%)
        factors['specific'] = (home.specific_btts_pct + away.specific_btts_pct) / 2
        weights['specific'] = 0.20
        
        # 4. Tendances L5 (15%)
        factors['trends'] = (home.last5_btts_pct + away.last5_btts_pct) / 2
        weights['trends'] = 0.15
        
        # 5. H2H (15% si disponible)
        if h2h and h2h.get('total_matches', 0) >= 2:
            factors['h2h'] = self._safe_float(h2h.get('btts_pct'))
            weights['h2h'] = 0.15
            # Réduire autres poids
            for k in ['global', 'specific', 'trends']:
                weights[k] *= 0.85
        
        # Score brut
        raw_score = sum(factors[k] * weights[k] for k in factors) / sum(weights.values())
        
        # Pénalités
        cs_penalty = (home.specific_clean_sheet_pct + away.specific_clean_sheet_pct) / 4
        fts_penalty = (home.failed_to_score_pct + away.failed_to_score_pct) / 4
        
        # Bonus momentum (équipes offensives en forme)
        momentum_bonus = (home.momentum + away.momentum) * 5 if (home.momentum > 0 and away.momentum > 0) else 0
        
        # Score final
        score = raw_score - cs_penalty - fts_penalty + momentum_bonus
        score = max(0, min(100, score))
        
        return {
            'score': round(score, 1),
            'raw_score': round(raw_score, 1),
            'poisson_prob': poisson.btts_prob,
            'factors': {k: round(v, 1) for k, v in factors.items()},
            'weights': weights,
            'penalties': {
                'clean_sheet': round(cs_penalty, 1),
                'failed_to_score': round(fts_penalty, 1)
            },
            'momentum_bonus': round(momentum_bonus, 1)
        }
    
    # ============================================================
    # SCORE OVER 2.5 DIAMOND
    # ============================================================
    
    def calculate_over25_score(self, home: TeamAnalysis, away: TeamAnalysis,
                                h2h: Optional[Dict], poisson: PoissonResult) -> Dict:
        """Score Over 2.5 Diamond"""
        factors = {}
        weights = {}
        
        # 1. Poisson (40% - très fiable pour Over)
        factors['poisson'] = poisson.over25_prob
        weights['poisson'] = 0.40
        
        # 2. Stats globales (15%)
        factors['global'] = (home.over25_pct + away.over25_pct) / 2
        weights['global'] = 0.15
        
        # 3. Stats spécifiques (20%)
        factors['specific'] = (home.specific_over25_pct + away.specific_over25_pct) / 2
        weights['specific'] = 0.20
        
        # 4. Tendances (10%)
        factors['trends'] = (home.last5_over25_pct + away.last5_over25_pct) / 2
        weights['trends'] = 0.10
        
        # 5. H2H (15%)
        if h2h and h2h.get('total_matches', 0) >= 2:
            factors['h2h'] = self._safe_float(h2h.get('over_25_pct'))
            weights['h2h'] = 0.15
            for k in ['global', 'specific']:
                weights[k] *= 0.85
        
        # Score
        raw_score = sum(factors[k] * weights[k] for k in factors) / sum(weights.values())
        
        # Bonus volatilité (équipes imprévisibles = plus de buts)
        volatility_bonus = ((home.volatility + away.volatility) / 2 - 1) * 5
        volatility_bonus = max(-5, min(10, volatility_bonus))
        
        score = raw_score + volatility_bonus
        score = max(0, min(100, score))
        
        return {
            'score': round(score, 1),
            'raw_score': round(raw_score, 1),
            'poisson_prob': poisson.over25_prob,
            'expected_goals': poisson.total_xg,
            'factors': {k: round(v, 1) for k, v in factors.items()},
            'volatility_bonus': round(volatility_bonus, 1)
        }
    
    # ============================================================
    # KELLY CRITERION
    # ============================================================
    
    def calculate_kelly(self, prob: float, odds: float, fraction: float = 0.25) -> float:
        """
        Kelly Criterion: f* = (bp - q) / b
        où b = odds - 1, p = prob, q = 1 - p
        
        fraction: Kelly fractionnaire (0.25 = 1/4 Kelly, plus conservateur)
        """
        if not odds or odds <= 1 or prob <= 0:
            return 0.0
        
        p = prob / 100
        b = odds - 1
        q = 1 - p
        
        kelly = (b * p - q) / b
        
        # Kelly fractionnaire
        kelly *= fraction
        
        # Clamp entre 0 et 10% du bankroll
        return max(0, min(0.10, kelly))
    
    # ============================================================
    # CONFIDENCE DIAMOND
    # ============================================================
    
    def calculate_confidence(self, home: TeamAnalysis, away: TeamAnalysis, 
                            h2h: Optional[Dict], poisson: PoissonResult) -> Tuple[Confidence, int]:
        """
        Confidence multi-critères niveau Diamond
        """
        score = 0
        max_score = 100
        
        # 1. Nombre de matchs (25 pts max)
        matches = home.matches_played + away.matches_played
        score += min(matches / 30 * 25, 25)
        
        # 2. Data Quality (20 pts max)
        dq = (home.data_quality + away.data_quality) / 2
        score += dq / 100 * 20
        
        # 3. H2H disponible (15 pts max)
        if h2h:
            h2h_matches = h2h.get('total_matches', 0)
            score += min(h2h_matches / 5 * 15, 15)
        
        # 4. Cohérence stats vs tendances (15 pts max)
        home_coh = 100 - abs(home.btts_pct - home.last5_btts_pct)
        away_coh = 100 - abs(away.btts_pct - away.last5_btts_pct)
        score += ((home_coh + away_coh) / 2) / 100 * 15
        
        # 5. Volatilité faible = plus prévisible (15 pts max)
        avg_vol = (home.volatility + away.volatility) / 2
        vol_score = max(0, 15 - avg_vol * 5)
        score += vol_score
        
        # 6. Poisson cohérent avec stats (10 pts max)
        btts_diff = abs(poisson.btts_prob - (home.btts_pct + away.btts_pct) / 2)
        score += max(0, 10 - btts_diff / 5)
        
        # Mapper
        conf_score = int(score)
        
        if conf_score >= 85:
            return Confidence.DIAMOND, conf_score
        elif conf_score >= 70:
            return Confidence.PLATINUM, conf_score
        elif conf_score >= 55:
            return Confidence.GOLD, conf_score
        elif conf_score >= 40:
            return Confidence.SILVER, conf_score
        elif conf_score >= 25:
            return Confidence.BRONZE, conf_score
        else:
            return Confidence.IRON, conf_score
    
    # ============================================================
    # RECOMMENDATION DIAMOND
    # ============================================================
    
    def get_recommendation(self, score: float, confidence: Confidence, 
                          poisson_prob: float) -> Recommendation:
        """Recommandation graduée niveau Diamond"""
        
        # Diamond pick: score > 75 + confidence Diamond + Poisson > 70
        if score >= 75 and confidence == Confidence.DIAMOND and poisson_prob >= 70:
            return Recommendation.DIAMOND_PICK
        
        # Strong Yes: score > 70 + confidence élevée
        if score >= 70 and confidence in [Confidence.DIAMOND, Confidence.PLATINUM]:
            return Recommendation.STRONG_YES
        
        # Yes
        if score >= 65 and confidence in [Confidence.DIAMOND, Confidence.PLATINUM, Confidence.GOLD]:
            return Recommendation.YES
        
        # Lean Yes
        if score >= 55:
            return Recommendation.LEAN_YES
        
        # Neutral
        if score >= 45:
            return Recommendation.NEUTRAL
        
        # Lean No
        if score >= 35:
            return Recommendation.LEAN_NO
        
        # No
        if score >= 25 and confidence in [Confidence.DIAMOND, Confidence.PLATINUM, Confidence.GOLD]:
            return Recommendation.NO
        
        # Strong No
        if score < 25 and confidence in [Confidence.DIAMOND, Confidence.PLATINUM]:
            return Recommendation.STRONG_NO
        
        return Recommendation.LEAN_NO
    
    # ============================================================
    # VALUE BET DIAMOND
    # ============================================================
    
    def calculate_value_bet(self, prob: float, odds: float) -> Dict:
        """Value Bet avec rating Diamond"""
        if not odds or odds <= 1:
            return {'is_value': False, 'rating': 'N/A'}
        
        our_prob = prob / 100
        implied_prob = 1 / odds
        edge = our_prob - implied_prob
        ev = (our_prob * (odds - 1)) - (1 - our_prob)
        
        # Rating
        if edge >= 0.20:
            rating = "💎 DIAMOND VALUE"
        elif edge >= 0.15:
            rating = "🔥 STRONG VALUE"
        elif edge >= 0.10:
            rating = "✅ VALUE"
        elif edge >= 0.05:
            rating = "📈 SLIGHT VALUE"
        elif edge >= 0:
            rating = "⚖️ FAIR"
        elif edge >= -0.05:
            rating = "📉 SLIGHT -EV"
        else:
            rating = "❌ AVOID"
        
        return {
            'is_value': edge >= 0.05,
            'our_probability': round(our_prob * 100, 1),
            'implied_probability': round(implied_prob * 100, 1),
            'edge': round(edge * 100, 2),
            'expected_value': round(ev * 100, 2),
            'rating': rating
        }
    
    # ============================================================
    # COMBO INTELLIGENT
    # ============================================================
    
    def calculate_combo_prob(self, btts_prob: float, over25_prob: float, 
                            correlation: float = 0.6) -> Dict:
        """
        Probabilité combo BTTS + Over 2.5
        Ces marchés sont positivement corrélés (si BTTS, souvent Over)
        """
        # Probabilité indépendante
        p_independent = (btts_prob / 100) * (over25_prob / 100)
        
        # Ajuster pour corrélation positive
        # Si corrélation = 0.6, les événements sont liés
        p_adjusted = p_independent * (1 + correlation * 0.3)
        p_adjusted = min(p_adjusted, min(btts_prob, over25_prob) / 100)
        
        return {
            'btts_prob': btts_prob,
            'over25_prob': over25_prob,
            'combo_prob_independent': round(p_independent * 100, 1),
            'combo_prob_adjusted': round(p_adjusted * 100, 1),
            'correlation': correlation,
            'recommendation': 'COMBO INTERESSANT' if p_adjusted >= 0.35 else 'COMBO RISQUÉ'
        }
    
    # ============================================================
    # PRÉDICTION COMPLÈTE
    # ============================================================
    
    def predict_match(self, home_team: str, away_team: str,
                      odds_btts_yes: float = None, odds_over25: float = None) -> Dict:
        """
        Prédiction complète niveau Diamond
        """
        # Récupérer les analyses
        home = self.get_team_analysis(home_team, is_home=True)
        away = self.get_team_analysis(away_team, is_home=False)
        
        if not home or not away:
            return {'error': 'Équipe non trouvée', 'home': home_team, 'away': away_team}
        
        h2h = self.get_h2h_stats(home_team, away_team)
        
        # Déterminer la ligue
        league = home.league or away.league or 'default'
        
        # Calculer xG
        home_xg, away_xg = self.calculate_expected_goals(home, away, league)
        
        # Modèle Poisson
        poisson = self.calculate_poisson(home_xg, away_xg)
        
        # Scores BTTS et Over
        btts_data = self.calculate_btts_score(home, away, h2h, poisson)
        over25_data = self.calculate_over25_score(home, away, h2h, poisson)
        
        # Confidence
        confidence, conf_score = self.calculate_confidence(home, away, h2h, poisson)
        
        # Recommendations
        btts_rec = self.get_recommendation(btts_data['score'], confidence, poisson.btts_prob)
        over25_rec = self.get_recommendation(over25_data['score'], confidence, poisson.over25_prob)
        
        # Value Bets
        btts_value = self.calculate_value_bet(btts_data['score'], odds_btts_yes) if odds_btts_yes else {}
        over25_value = self.calculate_value_bet(over25_data['score'], odds_over25) if odds_over25 else {}
        
        # Kelly
        btts_kelly = self.calculate_kelly(btts_data['score'], odds_btts_yes) if odds_btts_yes else 0
        over25_kelly = self.calculate_kelly(over25_data['score'], odds_over25) if odds_over25 else 0
        
        # Combo
        combo = self.calculate_combo_prob(poisson.btts_prob, poisson.over25_prob)
        
        # Match Interest
        max_score = max(btts_data['score'], over25_data['score'])
        if max_score >= 75 and confidence in [Confidence.DIAMOND, Confidence.PLATINUM]:
            interest = "💎 DIAMOND MATCH"
        elif max_score >= 65:
            interest = "🔥 HIGH INTEREST"
        elif max_score >= 55:
            interest = "📈 MEDIUM INTEREST"
        else:
            interest = "📊 LOW INTEREST"
        
        return {
            'match': {
                'home_team': home_team,
                'away_team': away_team,
                'league': league
            },
            'poisson': {
                'home_xg': poisson.home_xg,
                'away_xg': poisson.away_xg,
                'total_xg': poisson.total_xg,
                'btts_prob': poisson.btts_prob,
                'over25_prob': poisson.over25_prob,
                'over15_prob': poisson.over15_prob,
                'over35_prob': poisson.over35_prob,
                'most_likely_scores': poisson.most_likely_scores,
                '1x2': {
                    'home': poisson.home_win_prob,
                    'draw': poisson.draw_prob,
                    'away': poisson.away_win_prob
                }
            },
            'btts': {
                'score': btts_data['score'],
                'recommendation': btts_rec.value,
                'factors': btts_data['factors'],
                'penalties': btts_data['penalties'],
                'momentum_bonus': btts_data['momentum_bonus']
            },
            'over25': {
                'score': over25_data['score'],
                'recommendation': over25_rec.value,
                'expected_goals': over25_data['expected_goals'],
                'factors': over25_data['factors'],
                'volatility_bonus': over25_data['volatility_bonus']
            },
            'confidence': {
                'level': confidence.value,
                'score': conf_score,
                'emoji': '💎' if confidence == Confidence.DIAMOND else 
                         '🏆' if confidence == Confidence.PLATINUM else
                         '🥇' if confidence == Confidence.GOLD else
                         '🥈' if confidence == Confidence.SILVER else
                         '🥉' if confidence == Confidence.BRONZE else '⚫'
            },
            'value_bet': {
                'btts': btts_value,
                'over25': over25_value
            },
            'kelly': {
                'btts': round(btts_kelly * 100, 2),
                'over25': round(over25_kelly * 100, 2)
            },
            'combo': combo,
            'home_analysis': {
                'team': home.name,
                'matches': home.matches_played,
                'btts_pct': home.btts_pct,
                'over25_pct': home.over25_pct,
                'form': home.form,
                'momentum': round(home.momentum, 2),
                'volatility': round(home.volatility, 2)
            },
            'away_analysis': {
                'team': away.name,
                'matches': away.matches_played,
                'btts_pct': away.btts_pct,
                'over25_pct': away.over25_pct,
                'form': away.form,
                'momentum': round(away.momentum, 2),
                'volatility': round(away.volatility, 2)
            },
            'h2h': {
                'available': h2h is not None,
                'matches': h2h.get('total_matches', 0) if h2h else 0,
                'btts_pct': h2h.get('btts_pct') if h2h else None,
                'over25_pct': h2h.get('over_25_pct') if h2h else None,
                'avg_goals': h2h.get('avg_total_goals') if h2h else None
            },
            'match_interest': interest,
            'generated_at': datetime.now().isoformat()
        }
