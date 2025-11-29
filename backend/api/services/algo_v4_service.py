"""
🧠 ALGO V4 - DATA-DRIVEN BETTING SERVICE
══════════════════════════════════════════════════════════════════════════════

Service d'analyse basé sur les données historiques RÉELLES.
Corrige les erreurs de l'algo V3 en utilisant:
- tracking_clv_picks (historique profits/pertes)
- team_intelligence (stats équipes)
- scorer_intelligence (buteurs)
- market_patterns (patterns profitables)

VERSION: 4.0.0
DATE: 29/11/2025
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DB_CONFIG = {
    "host": "monps_postgres",
    "port": 5432,
    "dbname": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024"
}

# Marchés à ÉVITER (profit négatif historique)
MARKETS_TO_AVOID = {
    "dc_12": -5.64,
    "btts_yes": -10.11,
    "over_35": -8.59,
    "away": -53.93,
    "draw": -1.09
}

# Marchés RENTABLES (profit positif historique)
PROFITABLE_MARKETS = {
    "dc_1x": {"profit": 17.46, "win_rate": 86.4},
    "btts_no": {"profit": 20.15, "win_rate": 49.4},
    "home": {"profit": 10.78, "win_rate": 58.4},
    "over_25": {"profit": 4.65, "win_rate": 62.3},
    "under_35": {"profit": 2.06, "win_rate": 67.6}
}


@dataclass
class TeamStats:
    """Stats d'une équipe depuis team_intelligence"""
    team_name: str
    home_btts_rate: float = 0
    home_over25_rate: float = 0
    home_win_rate: float = 0
    home_draw_rate: float = 0
    home_goals_avg: float = 0
    away_btts_rate: float = 0
    away_over25_rate: float = 0
    away_win_rate: float = 0
    away_draw_rate: float = 0
    away_goals_avg: float = 0


@dataclass
class ScorerStats:
    """Stats d'un buteur"""
    player_name: str
    team: str
    season_goals: int
    goals_per_match: float
    is_penalty_taker: bool


@dataclass
class MarketValidation:
    """Validation d'un marché basée sur l'historique"""
    market_type: str
    is_profitable: bool
    profit_units: float
    win_rate: float
    recommendation: str
    reason: str


@dataclass
class PickAnalysis:
    """Analyse complète d'un pick"""
    match_name: str
    home_team: str
    away_team: str
    market_type: str
    original_market: str
    odds: float
    score: int
    recommendation: str
    confidence: str
    reasons: List[str]
    warnings: List[str]
    team_stats: Dict
    scorers: List[Dict]
    historical_validation: Dict


class AlgoV4Service:
    """Service principal ALGO V4"""
    
    def __init__(self):
        self.conn = None
        
    def get_connection(self):
        """Obtenir connexion DB"""
        if not self.conn or self.conn.closed:
            self.conn = psycopg2.connect(**DB_CONFIG)
        return self.conn
    
    def close(self):
        """Fermer connexion"""
        if self.conn:
            self.conn.close()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DONNÉES ÉQUIPES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_team_stats(self, team_name: str) -> Optional[TeamStats]:
        """Récupérer les stats d'une équipe"""
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        team_name,
                        COALESCE(home_btts_rate, 0) as home_btts_rate,
                        COALESCE(home_over25_rate, 0) as home_over25_rate,
                        COALESCE(home_win_rate, 0) as home_win_rate,
                        COALESCE(home_draw_rate, 0) as home_draw_rate,
                        COALESCE(home_goals_scored_avg, 0) as home_goals_avg,
                        COALESCE(away_btts_rate, 0) as away_btts_rate,
                        COALESCE(away_over25_rate, 0) as away_over25_rate,
                        COALESCE(away_win_rate, 0) as away_win_rate,
                        COALESCE(away_draw_rate, 0) as away_draw_rate,
                        COALESCE(away_goals_scored_avg, 0) as away_goals_avg
                    FROM team_intelligence
                    WHERE team_name ILIKE %s
                    LIMIT 1
                """, (f"%{team_name}%",))
                
                row = cur.fetchone()
                if row:
                    return TeamStats(**row)
                return None
        except Exception as e:
            logger.error(f"Error getting team stats: {e}")
            return None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DONNÉES BUTEURS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_team_scorers(self, team_name: str) -> List[ScorerStats]:
        """Récupérer les buteurs d'une équipe"""
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        player_name,
                        current_team as team,
                        COALESCE(season_goals, 0) as season_goals,
                        COALESCE(goals_per_match, 0) as goals_per_match,
                        COALESCE(is_penalty_taker, false) as is_penalty_taker
                    FROM scorer_intelligence
                    WHERE current_team ILIKE %s
                    AND season_goals >= 2
                    ORDER BY goals_per_match DESC
                    LIMIT 5
                """, (f"%{team_name}%",))
                
                rows = cur.fetchall()
                return [ScorerStats(**row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting scorers: {e}")
            return []
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VALIDATION HISTORIQUE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def validate_market(self, market_type: str) -> MarketValidation:
        """Valider un marché basé sur l'historique"""
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        market_type,
                        COUNT(*) as total,
                        SUM(CASE WHEN is_winner THEN 1 ELSE 0 END) as wins,
                        ROUND(100.0 * SUM(CASE WHEN is_winner THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 1) as win_rate,
                        ROUND(SUM(CASE WHEN is_winner THEN odds_taken - 1 ELSE -1 END)::numeric, 2) as profit
                    FROM tracking_clv_picks 
                    WHERE is_resolved = true AND market_type = %s
                    GROUP BY market_type
                """, (market_type,))
                
                row = cur.fetchone()
                
                if row:
                    profit = float(row['profit'] or 0)
                    win_rate = float(row['win_rate'] or 0)
                    is_profitable = profit > 0
                    
                    if profit > 10:
                        recommendation = "STRONG_BET"
                        reason = f"Historique excellent: +{profit} units"
                    elif profit > 0:
                        recommendation = "VALUE_BET"
                        reason = f"Historique positif: +{profit} units"
                    elif profit > -5:
                        recommendation = "CAUTION"
                        reason = f"Historique légèrement négatif: {profit} units"
                    else:
                        recommendation = "AVOID"
                        reason = f"Historique très négatif: {profit} units"
                    
                    return MarketValidation(
                        market_type=market_type,
                        is_profitable=is_profitable,
                        profit_units=profit,
                        win_rate=win_rate,
                        recommendation=recommendation,
                        reason=reason
                    )
                else:
                    return MarketValidation(
                        market_type=market_type,
                        is_profitable=False,
                        profit_units=0,
                        win_rate=0,
                        recommendation="UNKNOWN",
                        reason="Pas assez de données historiques"
                    )
        except Exception as e:
            logger.error(f"Error validating market: {e}")
            return MarketValidation(
                market_type=market_type,
                is_profitable=False,
                profit_units=0,
                win_rate=0,
                recommendation="ERROR",
                reason=str(e)
            )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RÈGLES ALGO V4
    # ═══════════════════════════════════════════════════════════════════════════
    
    def apply_rule_1_dc12_to_dc1x(self, market: str, home_stats: TeamStats) -> Tuple[str, str]:
        """RÈGLE 1: Remplacer DC_12 par DC_1X si draw_rate > 20%"""
        if market == "dc_12" and home_stats and home_stats.home_draw_rate > 20:
            return "dc_1x", f"DC_12→DC_1X (draw_rate {home_stats.home_draw_rate}% > 20%)"
        return market, ""
    
    def apply_rule_2_btts_validation(self, home_stats: TeamStats, away_stats: TeamStats, odds: float) -> Dict:
        """RÈGLE 2: BTTS basé sur team_intelligence"""
        if not home_stats or not away_stats:
            return {"valid": False, "reason": "Stats manquantes"}
        
        btts_prob = (home_stats.home_btts_rate + away_stats.away_btts_rate) / 2
        
        if btts_prob > 55 and odds >= 1.70:
            return {"valid": True, "recommendation": "STRONG_BET", "btts_prob": btts_prob}
        elif btts_prob > 50 and odds >= 1.90:
            return {"valid": True, "recommendation": "VALUE_BET", "btts_prob": btts_prob}
        elif btts_prob < 40:
            return {"valid": False, "recommendation": "AVOID", "reason": f"BTTS prob trop basse: {btts_prob}%"}
        else:
            return {"valid": True, "recommendation": "CAUTION", "btts_prob": btts_prob}
    
    def apply_rule_3_scorers_boost(self, home_scorers: List[ScorerStats], away_scorers: List[ScorerStats]) -> Dict:
        """RÈGLE 3: Boost BTTS si buteurs en forme"""
        all_scorers = home_scorers + away_scorers
        top_scorers = [s for s in all_scorers if s.goals_per_match > 0.5]
        
        if len(top_scorers) >= 2:
            return {"boost": 1.20, "reason": f"{len(top_scorers)} buteurs > 0.5 goals/match"}
        elif len(top_scorers) == 1:
            return {"boost": 1.10, "reason": f"1 buteur en forme: {top_scorers[0].player_name}"}
        else:
            return {"boost": 1.0, "reason": "Pas de buteur dominant"}
    
    def apply_rule_4_historical_validation(self, market_type: str) -> MarketValidation:
        """RÈGLE 4: Validation historique obligatoire"""
        return self.validate_market(market_type)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ANALYSE COMPLÈTE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def analyze_pick(self, home_team: str, away_team: str, market_type: str, odds: float, original_score: int = 0) -> PickAnalysis:
        """Analyse complète d'un pick avec toutes les règles V4"""
        
        reasons = []
        warnings = []
        
        # Récupérer les données
        home_stats = self.get_team_stats(home_team)
        away_stats = self.get_team_stats(away_team)
        home_scorers = self.get_team_scorers(home_team)
        away_scorers = self.get_team_scorers(away_team)
        
        # RÈGLE 1: DC_12 → DC_1X
        new_market, rule1_reason = self.apply_rule_1_dc12_to_dc1x(market_type, home_stats)
        if rule1_reason:
            warnings.append(f"⚠️ RÈGLE 1: {rule1_reason}")
            market_type = new_market
        
        # RÈGLE 2: Validation BTTS
        if "btts" in market_type.lower():
            btts_validation = self.apply_rule_2_btts_validation(home_stats, away_stats, odds)
            if btts_validation.get("valid"):
                reasons.append(f"✅ BTTS prob: {btts_validation.get('btts_prob', 0):.1f}%")
            else:
                warnings.append(f"⚠️ {btts_validation.get('reason', 'BTTS non validé')}")
        
        # RÈGLE 3: Boost buteurs
        scorer_boost = self.apply_rule_3_scorers_boost(home_scorers, away_scorers)
        if scorer_boost["boost"] > 1:
            reasons.append(f"🔥 {scorer_boost['reason']}")
        
        # RÈGLE 4: Validation historique
        historical = self.apply_rule_4_historical_validation(market_type)
        if historical.is_profitable:
            reasons.append(f"📊 {historical.reason}")
        else:
            warnings.append(f"⚠️ {historical.reason}")
        
        # Calculer la recommandation finale
        if historical.recommendation == "AVOID":
            final_recommendation = "❌ AVOID"
            confidence = "LOW"
        elif len(warnings) > 2:
            final_recommendation = "⚠️ CAUTION"
            confidence = "MEDIUM"
        elif historical.recommendation == "STRONG_BET" and len(reasons) >= 2:
            final_recommendation = "🏆 STRONG_BET"
            confidence = "HIGH"
        elif historical.is_profitable:
            final_recommendation = "✅ VALUE_BET"
            confidence = "MEDIUM-HIGH"
        else:
            final_recommendation = "📊 NEUTRAL"
            confidence = "MEDIUM"
        
        # Ajuster le score
        adjusted_score = original_score
        adjusted_score = int(adjusted_score * scorer_boost["boost"])
        if not historical.is_profitable:
            adjusted_score = int(adjusted_score * 0.7)  # Pénalité
        
        return PickAnalysis(
            match_name=f"{home_team} vs {away_team}",
            home_team=home_team,
            away_team=away_team,
            market_type=market_type,
            original_market=market_type,
            odds=odds,
            score=min(adjusted_score, 100),
            recommendation=final_recommendation,
            confidence=confidence,
            reasons=reasons,
            warnings=warnings,
            team_stats={
                "home": home_stats.__dict__ if home_stats else {},
                "away": away_stats.__dict__ if away_stats else {}
            },
            scorers=[s.__dict__ for s in home_scorers + away_scorers],
            historical_validation=historical.__dict__
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ANALYSE BATCH
    # ═══════════════════════════════════════════════════════════════════════════
    
    def analyze_today_picks(self) -> List[Dict]:
        """Analyser tous les picks du jour avec ALGO V4"""
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT DISTINCT
                        home_team,
                        away_team,
                        market_type,
                        odds_taken as odds,
                        diamond_score as score,
                        commence_time
                    FROM tracking_clv_picks
                    WHERE commence_time > NOW()
                    AND commence_time < NOW() + INTERVAL '24 hours'
                    AND diamond_score >= 80
                    ORDER BY diamond_score DESC
                    LIMIT 50
                """)
                
                picks = cur.fetchall()
                
                analyses = []
                for pick in picks:
                    analysis = self.analyze_pick(
                        home_team=pick['home_team'],
                        away_team=pick['away_team'],
                        market_type=pick['market_type'],
                        odds=float(pick['odds'] or 1.5),
                        original_score=int(pick['score'] or 50)
                    )
                    analyses.append({
                        "match": analysis.match_name,
                        "market": analysis.market_type,
                        "odds": analysis.odds,
                        "score": analysis.score,
                        "recommendation": analysis.recommendation,
                        "confidence": analysis.confidence,
                        "reasons": analysis.reasons,
                        "warnings": analysis.warnings,
                        "commence_time": pick['commence_time'].isoformat() if pick['commence_time'] else None
                    })
                
                # Trier par score ajusté
                analyses.sort(key=lambda x: x['score'], reverse=True)
                
                return analyses
                
        except Exception as e:
            logger.error(f"Error analyzing today picks: {e}")
            return []
    
    def get_recommended_bets(self) -> Dict:
        """Obtenir les paris recommandés avec ALGO V4"""
        analyses = self.analyze_today_picks()
        
        strong_bets = [a for a in analyses if "STRONG" in a['recommendation']]
        value_bets = [a for a in analyses if "VALUE" in a['recommendation']]
        caution_bets = [a for a in analyses if "CAUTION" in a['recommendation']]
        avoid_bets = [a for a in analyses if "AVOID" in a['recommendation']]
        
        return {
            "timestamp": datetime.now().isoformat(),
            "version": "ALGO V4.0",
            "summary": {
                "total_analyzed": len(analyses),
                "strong_bets": len(strong_bets),
                "value_bets": len(value_bets),
                "caution": len(caution_bets),
                "avoid": len(avoid_bets)
            },
            "strong_bets": strong_bets[:10],
            "value_bets": value_bets[:10],
            "caution_bets": caution_bets[:5],
            "avoid_bets": avoid_bets[:5]
        }


# Instance globale
algo_v4 = AlgoV4Service()
