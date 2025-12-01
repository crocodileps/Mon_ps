"""
Agent PATRON Diamond+ V3.0
==========================
Meta-Analyste Professionnel avec:
- Intégration moteur V3 Diamond (Poisson, xG, Momentum)
- Marchés BTTS et Over 2.5 (Full Gain 2.0)
- Scoring unifié multi-marchés
- Logging pour CLV tracking
- Rétrocompatibilité avec système existant
"""
import os
import sys
import math
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import logging

# Coach Intelligence Integration
import sys
sys.path.insert(0, "/app/agents")
try:
    from coach_impact import CoachImpactCalculator
    COACH_IMPACT_ENABLED = True
except ImportError:
    COACH_IMPACT_ENABLED = False

logger = logging.getLogger(__name__)

# Ajouter le path pour les services fullgain
sys.path.append('/app/api/services/fullgain')


class MarketType(Enum):
    MATCH_WINNER = "1X2"
    BTTS = "btts"
    OVER_25 = "over25"
    OVER_15 = "over15"
    OVER_35 = "over35"


class Confidence(Enum):
    DIAMOND = "diamond"      # 90%+
    PLATINUM = "platinum"    # 75-89%
    GOLD = "gold"           # 60-74%
    SILVER = "silver"       # 45-59%
    BRONZE = "bronze"       # 30-44%
    IRON = "iron"           # <30%


class Recommendation(Enum):
    DIAMOND_PICK = "💎 DIAMOND PICK"
    STRONG_BET = "✅ STRONG BET"
    GOOD_VALUE = "📈 GOOD VALUE"
    LEAN = "📊 LEAN"
    SKIP = "⏭️ SKIP"
    AVOID = "❌ AVOID"


@dataclass
class MarketPrediction:
    """Prédiction pour un marché spécifique"""
    market: MarketType
    score: float
    probability: float
    recommendation: Recommendation
    confidence: Confidence
    value_rating: str
    kelly_pct: float
    factors: Dict
    reasoning: str


@dataclass
class MatchAnalysis:
    """Analyse complète d'un match"""
    match_id: str
    home_team: str
    away_team: str
    league: str
    
    # Scores par marché
    match_winner: Optional[MarketPrediction]
    btts: Optional[MarketPrediction]
    over25: Optional[MarketPrediction]
    
    # Meta
    patron_score: float
    patron_recommendation: str
    confidence: Confidence
    match_interest: str
    
    # Poisson
    home_xg: float
    away_xg: float
    most_likely_scores: List[Tuple[str, float]]
    
    # Agents classiques
    agents_summary: Dict
    
    generated_at: str


class PatronDiamondV3:
    """
    Agent PATRON Diamond+ V3.0
    
    Combine:
    - Agents existants (A, B, C, D)
    - Moteur V3 Diamond (Poisson, xG, Momentum)
    - Scoring V2 validé (paradoxe confiance, home advantage)
    - Marchés BTTS et Over 2.5
    """
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'monps_postgres'),
            'port': 5432,
            'database': os.getenv('DB_NAME', 'monps_db'),
            'user': os.getenv('DB_USER', 'monps_user'),
            'password': os.getenv('DB_PASSWORD', 'monps_secure_password_2024')
        }
        
        # Charger le moteur Diamond si disponible
        self.diamond_engine = None
        try:
            from prediction_engine_v3_diamond import PredictionEngineDiamond
            self.diamond_engine = PredictionEngineDiamond()
            logger.info("✅ Moteur Diamond V3 chargé")
        except Exception as e:
            logger.warning(f"⚠️ Moteur Diamond non disponible: {e}")
        
        # Poids des facteurs (validés sur données réelles)
        self.weights = {
            'poisson': 0.30,      # Modèle Poisson
            'stats_global': 0.20, # Stats globales équipe
            'stats_form': 0.15,   # Forme récente L5
            'h2h': 0.15,          # Head-to-Head
            'agents_classic': 0.20 # Agents existants A,B,C
        }
        
        # Scoring V2 validé (basé sur 60 matchs réels)
        self.outcome_bonuses = {
            'home': 15,   # 62.5% WR historique
            'away': -10,  # 14.0% WR
            'draw': -20   # 4.5% WR
        }
    
    def _get_conn(self):
        return psycopg2.connect(**self.db_config)
    
    def _safe_float(self, value, default: float = 0.0) -> float:
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
        """Probabilité Poisson P(X=k)"""
        if lam <= 0:
            return 1.0 if k == 0 else 0.0
        return (lam ** k) * math.exp(-lam) / math.factorial(k)
    
    def calculate_poisson_probabilities(self, home_xg: float, away_xg: float) -> Dict:
        """Calcule toutes les probabilités via Poisson"""
        max_goals = 7
        btts = over15 = over25 = over35 = 0
        home_win = draw = away_win = 0
        score_probs = {}
        
        for h in range(max_goals + 1):
            for a in range(max_goals + 1):
                prob = self._poisson_prob(home_xg, h) * self._poisson_prob(away_xg, a)
                score_probs[f"{h}-{a}"] = prob
                
                if h > a: home_win += prob
                elif h == a: draw += prob
                else: away_win += prob
                
                if h > 0 and a > 0: btts += prob
                total = h + a
                if total > 1: over15 += prob
                if total > 2: over25 += prob
                if total > 3: over35 += prob
        
        sorted_scores = sorted(score_probs.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'btts_prob': round(btts * 100, 1),
            'over15_prob': round(over15 * 100, 1),
            'over25_prob': round(over25 * 100, 1),
            'over35_prob': round(over35 * 100, 1),
            'home_win_prob': round(home_win * 100, 1),
            'draw_prob': round(draw * 100, 1),
            'away_win_prob': round(away_win * 100, 1),
            'most_likely_scores': [(s, round(p * 100, 1)) for s, p in sorted_scores]
        }
    
    # ============================================================
    # RÉCUPÉRATION DONNÉES
    # ============================================================
    
    def get_team_stats(self, team_name: str) -> Optional[Dict]:
        """Récupère les stats d'une équipe depuis team_statistics_live"""
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cur.execute("""
                SELECT * FROM team_statistics_live 
                WHERE team_name = %s OR team_name ILIKE %s
            """, (team_name, f"%{team_name.split()[0]}%"))
            row = cur.fetchone()
            return dict(row) if row else None
        except:
            return None
        finally:
            cur.close()
            conn.close()
    
    def get_h2h_stats(self, team_a: str, team_b: str) -> Optional[Dict]:
        """Récupère les stats H2H"""
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Essayer les deux ordres
            for t1, t2 in [(team_a, team_b), (team_b, team_a)]:
                cur.execute("""
                    SELECT * FROM team_head_to_head 
                    WHERE team_a ILIKE %s AND team_b ILIKE %s
                """, (f"%{t1.split()[0]}%", f"%{t2.split()[0]}%"))
                row = cur.fetchone()
                if row:
                    return dict(row)
            
            # Essayer avec noms triés
            t1, t2 = sorted([team_a, team_b])
            cur.execute("""
                SELECT * FROM team_head_to_head 
                WHERE team_a = %s AND team_b = %s
            """, (t1, t2))
            row = cur.fetchone()
            return dict(row) if row else None
        except:
            return None
        finally:
            cur.close()
            conn.close()
    
    def get_match_odds(self, match_id: str) -> Dict:
        """Récupère les cotes du match"""
        conn = self._get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cur.execute("""
                SELECT 
                    bookmaker,
                    home_odds, away_odds, draw_odds,
                    collected_at
                FROM odds_history 
                WHERE match_id = %s
                ORDER BY collected_at DESC
            """, (match_id,))
            
            rows = cur.fetchall()
            
            if not rows:
                return {}
            
            home_odds = [float(r['home_odds']) for r in rows if r['home_odds']]
            away_odds = [float(r['away_odds']) for r in rows if r['away_odds']]
            draw_odds = [float(r['draw_odds']) for r in rows if r['draw_odds']]
            
            return {
                'home': {
                    'best': max(home_odds) if home_odds else 0,
                    'avg': sum(home_odds)/len(home_odds) if home_odds else 0,
                    'worst': min(home_odds) if home_odds else 0
                },
                'away': {
                    'best': max(away_odds) if away_odds else 0,
                    'avg': sum(away_odds)/len(away_odds) if away_odds else 0,
                    'worst': min(away_odds) if away_odds else 0
                },
                'draw': {
                    'best': max(draw_odds) if draw_odds else 0,
                    'avg': sum(draw_odds)/len(draw_odds) if draw_odds else 0,
                    'worst': min(draw_odds) if draw_odds else 0
                },
                'bookmaker_count': len(set(r['bookmaker'] for r in rows))
            }
        except Exception as e:
            logger.error(f"Erreur get_match_odds: {e}")
            return {}
        finally:
            cur.close()
            conn.close()
    
    # ============================================================
    # CALCUL XG
    # ============================================================
    
    def calculate_expected_goals(self, home_team: str, away_team: str) -> Tuple[float, float]:
        """
        Calcule les Expected Goals avec Coach Intelligence
        """
        home_stats = self.get_team_stats(home_team)
        away_stats = self.get_team_stats(away_team)
        
        # Valeurs par défaut
        base_home_xg = 1.5
        base_away_xg = 1.2
        
        if home_stats:
            home_scored = self._safe_float(home_stats.get('home_avg_scored'), 1.5)
            away_conceded = self._safe_float(away_stats.get('away_avg_conceded'), 1.5) if away_stats else 1.5
            base_home_xg = (home_scored + away_conceded) / 2 * 1.15
        
        if away_stats:
            away_scored = self._safe_float(away_stats.get('away_avg_scored'), 1.2)
            home_conceded = self._safe_float(home_stats.get('home_avg_conceded'), 1.2) if home_stats else 1.2
            base_away_xg = (away_scored + home_conceded) / 2 / 1.15
        
        # 🧠 Coach Intelligence Integration
        home_xg = base_home_xg
        away_xg = base_away_xg
        home_coach = {'style': 'unknown'}
        away_coach = {'style': 'unknown'}
        
        if COACH_IMPACT_ENABLED:
            try:
                coach_calc = CoachImpactCalculator()
                home_coach = coach_calc.get_coach_factors(home_team)
                away_coach = coach_calc.get_coach_factors(away_team)
                
                # Appliquer multiplicateurs tactiques
                home_xg = base_home_xg * home_coach['att'] * away_coach['def']
                away_xg = base_away_xg * away_coach['att'] * home_coach['def']
                
                if home_coach['style'] != 'unknown' or away_coach['style'] != 'unknown':
                    logger.info(f"🧠 PATRON COACH: {home_team}({home_coach['style']}) xG {base_home_xg:.2f}->{home_xg:.2f} | {away_team}({away_coach['style']}) xG {base_away_xg:.2f}->{away_xg:.2f}")
            except Exception as e:
                logger.debug(f"Coach impact: {e}")
        
        # Clamp dynamique
        max_home = 4.5 if 'offensive' in str(home_coach.get('style', '')) else 4.0
        max_away = 4.0 if 'offensive' in str(away_coach.get('style', '')) else 3.5
        home_xg = max(0.5, min(max_home, home_xg))
        away_xg = max(0.3, min(max_away, away_xg))
        
        return home_xg, away_xg

    # ============================================================
    # ANALYSE BTTS
    # ============================================================
    
    def analyze_btts(self, home_team: str, away_team: str, 
                     poisson_probs: Dict, odds_btts: float = None) -> MarketPrediction:
        """Analyse le marché BTTS"""
        home_stats = self.get_team_stats(home_team)
        away_stats = self.get_team_stats(away_team)
        h2h = self.get_h2h_stats(home_team, away_team)
        
        factors = {}
        score = 50  # Base
        
        # 1. Poisson probability (30%)
        poisson_btts = poisson_probs.get('btts_prob', 50)
        factors['poisson'] = poisson_btts
        score += (poisson_btts - 50) * 0.30
        
        # 2. Stats globales équipes (20%)
        if home_stats and away_stats:
            home_btts = self._safe_float(home_stats.get('btts_pct'), 50)
            away_btts = self._safe_float(away_stats.get('btts_pct'), 50)
            global_btts = (home_btts + away_btts) / 2
            factors['stats_global'] = global_btts
            score += (global_btts - 50) * 0.20
        
        # 3. Forme récente L5 (15%)
        if home_stats and away_stats:
            home_l5 = self._safe_float(home_stats.get('last5_btts_pct'), 50)
            away_l5 = self._safe_float(away_stats.get('last5_btts_pct'), 50)
            l5_btts = (home_l5 + away_l5) / 2
            factors['form_l5'] = l5_btts
            score += (l5_btts - 50) * 0.15
        
        # 4. H2H (15%)
        if h2h:
            h2h_btts = self._safe_float(h2h.get('btts_pct'), 50)
            factors['h2h'] = h2h_btts
            score += (h2h_btts - 50) * 0.15
        
        # 5. Pénalités défensives
        if home_stats and away_stats:
            home_cs = self._safe_float(home_stats.get('home_clean_sheet_pct'), 25)
            away_cs = self._safe_float(away_stats.get('away_clean_sheet_pct'), 20)
            cs_penalty = (home_cs + away_cs) / 4
            factors['clean_sheet_penalty'] = cs_penalty
            score -= cs_penalty * 0.5
        
        # Clamp
        score = max(0, min(100, score))
        
        # Confidence
        data_quality = 0
        if home_stats: data_quality += 30
        if away_stats: data_quality += 30
        if h2h: data_quality += 20
        data_quality += 20  # Poisson always available
        
        confidence = self._score_to_confidence(data_quality)
        
        # Recommendation
        recommendation = self._get_recommendation(score, confidence)
        
        # Value rating
        value_rating = "N/A"
        kelly = 0
        if odds_btts and odds_btts > 1:
            implied = 100 / odds_btts
            edge = score - implied
            if edge >= 15:
                value_rating = "💎 DIAMOND VALUE"
            elif edge >= 10:
                value_rating = "🔥 STRONG VALUE"
            elif edge >= 5:
                value_rating = "✅ VALUE"
            elif edge >= 0:
                value_rating = "⚖️ FAIR"
            else:
                value_rating = "❌ AVOID"
            
            # Kelly
            if edge > 0:
                p = score / 100
                b = odds_btts - 1
                kelly = max(0, min(10, ((b * p - (1-p)) / b) * 25))
        
        # Reasoning
        if score >= 70:
            reasoning = f"BTTS fortement probable ({score:.0f}%). Poisson: {poisson_btts:.0f}%, équipes offensives."
        elif score >= 55:
            reasoning = f"BTTS probable ({score:.0f}%). Tendance positive, données cohérentes."
        elif score >= 45:
            reasoning = f"BTTS incertain ({score:.0f}%). Équilibre entre les facteurs."
        else:
            reasoning = f"BTTS peu probable ({score:.0f}%). Équipes défensives ou clean sheets fréquents."
        
        return MarketPrediction(
            market=MarketType.BTTS,
            score=round(score, 1),
            probability=poisson_btts,
            recommendation=recommendation,
            confidence=confidence,
            value_rating=value_rating,
            kelly_pct=round(kelly, 2),
            factors=factors,
            reasoning=reasoning
        )
    
    # ============================================================
    # ANALYSE OVER 2.5
    # ============================================================
    
    def analyze_over25(self, home_team: str, away_team: str,
                       poisson_probs: Dict, total_xg: float,
                       odds_over25: float = None) -> MarketPrediction:
        """Analyse le marché Over 2.5"""
        home_stats = self.get_team_stats(home_team)
        away_stats = self.get_team_stats(away_team)
        h2h = self.get_h2h_stats(home_team, away_team)
        
        factors = {}
        score = 50
        
        # 1. Poisson (35%)
        poisson_over = poisson_probs.get('over25_prob', 50)
        factors['poisson'] = poisson_over
        score += (poisson_over - 50) * 0.35
        
        # 2. xG total (20%)
        xg_factor = min(100, max(0, (total_xg - 2.5) * 40 + 50))
        factors['xg'] = round(xg_factor, 1)
        score += (xg_factor - 50) * 0.20
        
        # 3. Stats globales (15%)
        if home_stats and away_stats:
            home_over = self._safe_float(home_stats.get('over_25_pct'), 50)
            away_over = self._safe_float(away_stats.get('over_25_pct'), 50)
            global_over = (home_over + away_over) / 2
            factors['stats_global'] = global_over
            score += (global_over - 50) * 0.15
        
        # 4. Forme L5 (15%)
        if home_stats and away_stats:
            home_l5 = self._safe_float(home_stats.get('last5_over25_pct'), 50)
            away_l5 = self._safe_float(away_stats.get('last5_over25_pct'), 50)
            l5_over = (home_l5 + away_l5) / 2
            factors['form_l5'] = l5_over
            score += (l5_over - 50) * 0.15
        
        # 5. H2H (15%)
        if h2h:
            h2h_over = self._safe_float(h2h.get('over_25_pct'), 50)
            factors['h2h'] = h2h_over
            score += (h2h_over - 50) * 0.15
        
        score = max(0, min(100, score))
        
        # Confidence
        data_quality = 20  # Poisson base
        if home_stats: data_quality += 25
        if away_stats: data_quality += 25
        if h2h: data_quality += 15
        if total_xg > 0: data_quality += 15
        
        confidence = self._score_to_confidence(data_quality)
        recommendation = self._get_recommendation(score, confidence)
        
        # Value
        value_rating = "N/A"
        kelly = 0
        if odds_over25 and odds_over25 > 1:
            implied = 100 / odds_over25
            edge = score - implied
            if edge >= 15:
                value_rating = "💎 DIAMOND VALUE"
            elif edge >= 10:
                value_rating = "🔥 STRONG VALUE"
            elif edge >= 5:
                value_rating = "✅ VALUE"
            elif edge >= 0:
                value_rating = "⚖️ FAIR"
            else:
                value_rating = "❌ AVOID"
            
            if edge > 0:
                p = score / 100
                b = odds_over25 - 1
                kelly = max(0, min(10, ((b * p - (1-p)) / b) * 25))
        
        # Reasoning
        if score >= 70:
            reasoning = f"Over 2.5 très probable ({score:.0f}%). xG: {total_xg:.2f}, équipes offensives."
        elif score >= 55:
            reasoning = f"Over 2.5 probable ({score:.0f}%). xG correct ({total_xg:.2f}), tendance positive."
        elif score >= 45:
            reasoning = f"Over 2.5 incertain ({score:.0f}%). Match équilibré."
        else:
            reasoning = f"Under 2.5 plus probable ({score:.0f}%). xG faible ({total_xg:.2f}) ou équipes défensives."
        
        return MarketPrediction(
            market=MarketType.OVER_25,
            score=round(score, 1),
            probability=poisson_over,
            recommendation=recommendation,
            confidence=confidence,
            value_rating=value_rating,
            kelly_pct=round(kelly, 2),
            factors=factors,
            reasoning=reasoning
        )
    
    # ============================================================
    # HELPERS
    # ============================================================
    
    def _score_to_confidence(self, score: float) -> Confidence:
        if score >= 90:
            return Confidence.DIAMOND
        elif score >= 75:
            return Confidence.PLATINUM
        elif score >= 60:
            return Confidence.GOLD
        elif score >= 45:
            return Confidence.SILVER
        elif score >= 30:
            return Confidence.BRONZE
        else:
            return Confidence.IRON
    
    def _get_recommendation(self, score: float, confidence: Confidence) -> Recommendation:
        if score >= 80 and confidence in [Confidence.DIAMOND, Confidence.PLATINUM]:
            return Recommendation.DIAMOND_PICK
        elif score >= 70 and confidence in [Confidence.DIAMOND, Confidence.PLATINUM, Confidence.GOLD]:
            return Recommendation.STRONG_BET
        elif score >= 60:
            return Recommendation.GOOD_VALUE
        elif score >= 50:
            return Recommendation.LEAN
        elif score >= 40:
            return Recommendation.SKIP
        else:
            return Recommendation.AVOID
    
    def _confidence_emoji(self, confidence: Confidence) -> str:
        mapping = {
            Confidence.DIAMOND: "💎",
            Confidence.PLATINUM: "🏆",
            Confidence.GOLD: "🥇",
            Confidence.SILVER: "🥈",
            Confidence.BRONZE: "🥉",
            Confidence.IRON: "⚫"
        }
        return mapping.get(confidence, "⚫")
    
    # ============================================================
    # ANALYSE COMPLÈTE
    # ============================================================
    
    def analyze_match_full(self, match_id: str, home_team: str, away_team: str,
                           agents_analysis: List[Dict] = None,
                           odds_btts: float = None, odds_over25: float = None) -> Dict:
        """
        Analyse complète d'un match avec tous les marchés
        
        Args:
            match_id: ID du match
            home_team: Équipe domicile
            away_team: Équipe extérieur
            agents_analysis: Résultats des agents classiques (A, B, C, D)
            odds_btts: Cote BTTS Yes
            odds_over25: Cote Over 2.5
        
        Returns:
            Analyse complète multi-marchés
        """
        # 1. Calculer xG
        home_xg, away_xg = self.calculate_expected_goals(home_team, away_team)
        total_xg = home_xg + away_xg
        
        # 2. Probabilités Poisson
        poisson = self.calculate_poisson_probabilities(home_xg, away_xg)
        
        # 3. Analyse BTTS
        btts_analysis = self.analyze_btts(home_team, away_team, poisson, odds_btts)
        
        # 4. Analyse Over 2.5
        over25_analysis = self.analyze_over25(home_team, away_team, poisson, total_xg, odds_over25)
        
        # 5. Score Patron global (combiné)
        agents_score = 50
        if agents_analysis:
            valid_scores = [a.get('confidence', 0) for a in agents_analysis if a.get('confidence')]
            if valid_scores:
                agents_score = sum(valid_scores) / len(valid_scores)
        
        patron_score = (
            btts_analysis.score * 0.30 +
            over25_analysis.score * 0.30 +
            agents_score * 0.40
        )
        
        # 6. Confidence globale
        confidence = self._score_to_confidence(
            (btts_analysis.confidence.value == 'diamond') * 30 +
            (btts_analysis.confidence.value in ['diamond', 'platinum']) * 20 +
            (over25_analysis.confidence.value == 'diamond') * 30 +
            (over25_analysis.confidence.value in ['diamond', 'platinum']) * 20
        )
        
        # 7. Match Interest
        max_score = max(btts_analysis.score, over25_analysis.score)
        if max_score >= 75:
            match_interest = "💎 DIAMOND MATCH"
        elif max_score >= 65:
            match_interest = "🔥 HIGH INTEREST"
        elif max_score >= 55:
            match_interest = "📈 MEDIUM INTEREST"
        else:
            match_interest = "📊 LOW INTEREST"
        
        # 8. Recommandation Patron
        if patron_score >= 70:
            patron_rec = "STRONG OPPORTUNITY"
        elif patron_score >= 55:
            patron_rec = "MODERATE OPPORTUNITY"
        elif patron_score >= 45:
            patron_rec = "MONITOR"
        else:
            patron_rec = "PASS"
        
        return {
            'match_id': match_id,
            'home_team': home_team,
            'away_team': away_team,
            
            # Poisson
            'poisson': {
                'home_xg': round(home_xg, 2),
                'away_xg': round(away_xg, 2),
                'total_xg': round(total_xg, 2),
                'btts_prob': poisson['btts_prob'],
                'over25_prob': poisson['over25_prob'],
                'over15_prob': poisson['over15_prob'],
                'over35_prob': poisson['over35_prob'],
                '1x2': {
                    'home': poisson['home_win_prob'],
                    'draw': poisson['draw_prob'],
                    'away': poisson['away_win_prob']
                },
                'most_likely_scores': poisson['most_likely_scores']
            },
            
            # Marchés
            'btts': {
                'score': btts_analysis.score,
                'probability': btts_analysis.probability,
                'recommendation': btts_analysis.recommendation.value,
                'confidence': btts_analysis.confidence.value,
                'confidence_emoji': self._confidence_emoji(btts_analysis.confidence),
                'value_rating': btts_analysis.value_rating,
                'kelly_pct': btts_analysis.kelly_pct,
                'factors': btts_analysis.factors,
                'reasoning': btts_analysis.reasoning
            },
            
            'over25': {
                'score': over25_analysis.score,
                'probability': over25_analysis.probability,
                'recommendation': over25_analysis.recommendation.value,
                'expected_goals': total_xg,
                'confidence': over25_analysis.confidence.value,
                'confidence_emoji': self._confidence_emoji(over25_analysis.confidence),
                'value_rating': over25_analysis.value_rating,
                'kelly_pct': over25_analysis.kelly_pct,
                'factors': over25_analysis.factors,
                'reasoning': over25_analysis.reasoning
            },
            
            # Patron
            'patron': {
                'score': round(patron_score, 1),
                'recommendation': patron_rec,
                'confidence': confidence.value,
                'confidence_emoji': self._confidence_emoji(confidence),
                'match_interest': match_interest
            },
            
            # Agents classiques
            'agents_summary': {
                'count': len(agents_analysis) if agents_analysis else 0,
                'avg_confidence': round(agents_score, 1)
            },
            
            'generated_at': datetime.now().isoformat()
        }
    
    # ============================================================
    # LOGGING POUR CLV TRACKING
    # ============================================================
    
    def log_prediction(self, match_id: str, home_team: str, away_team: str,
                       market: str, prediction: Dict):
        """
        Log une prédiction pour validation future (CLV tracking)
        """
        conn = self._get_conn()
        cur = conn.cursor()
        
        try:
            # Créer la table si elle n'existe pas
            cur.execute("""
                CREATE TABLE IF NOT EXISTS market_predictions (
                    id SERIAL PRIMARY KEY,
                    match_id VARCHAR(255),
                    home_team VARCHAR(255),
                    away_team VARCHAR(255),
                    market VARCHAR(50),
                    predicted_score DECIMAL(5,2),
                    predicted_probability DECIMAL(5,2),
                    recommendation VARCHAR(100),
                    confidence VARCHAR(50),
                    value_rating VARCHAR(50),
                    kelly_pct DECIMAL(5,2),
                    factors JSONB,
                    reasoning TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    -- Pour résolution
                    actual_result BOOLEAN,
                    is_win BOOLEAN,
                    resolved_at TIMESTAMP,
                    status VARCHAR(20) DEFAULT 'pending'
                )
            """)
            
            cur.execute("""
                INSERT INTO market_predictions 
                (match_id, home_team, away_team, market, predicted_score, 
                 predicted_probability, recommendation, confidence, value_rating,
                 kelly_pct, factors, reasoning)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                match_id, home_team, away_team, market,
                prediction.get('score'),
                prediction.get('probability'),
                prediction.get('recommendation'),
                prediction.get('confidence'),
                prediction.get('value_rating'),
                prediction.get('kelly_pct'),
                json.dumps(prediction.get('factors', {})),
                prediction.get('reasoning')
            ))
            
            conn.commit()
            logger.info(f"✅ Prédiction loggée: {match_id} - {market}")
        except Exception as e:
            logger.error(f"❌ Erreur log prediction: {e}")
            conn.rollback()
        finally:
            cur.close()
            conn.close()


# ============================================================
# INSTANCE GLOBALE
# ============================================================

_patron_instance = None

def get_patron_diamond():
    """Retourne l'instance singleton du Patron Diamond V3"""
    global _patron_instance
    if _patron_instance is None:
        _patron_instance = PatronDiamondV3()
    return _patron_instance
