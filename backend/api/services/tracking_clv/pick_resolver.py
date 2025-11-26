"""
TRACKING CLV 2.0 - Pick Resolver AVANCÉ
Résolution automatique des paris avec analyses post-match
"""
import structlog
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import asyncpg
import httpx

logger = structlog.get_logger()


@dataclass
class ResolutionResult:
    """Résultat de résolution d'un pick"""
    prediction_id: int
    market_type: str
    outcome: str                    # win, loss, push, void
    profit_loss: float              # En unités (stake = 1)
    roi_pct: float                  # ROI sur ce pick
    odds_used: float
    was_correct_prediction: bool    # Notre prédiction était-elle juste?
    score_accuracy: float           # Proximité score prédit vs réel (0-100)
    confidence_validated: bool      # La confiance était-elle justifiée?


@dataclass
class MatchResolutionSummary:
    """Résumé de résolution d'un match"""
    match_id: str
    home_team: str
    away_team: str
    final_score: str
    total_markets: int
    wins: int
    losses: int
    pushes: int
    total_profit: float
    best_pick: Optional[str]
    worst_pick: Optional[str]
    clv_summary: Dict[str, float]


class PickResolver:
    """
    Résolveur de picks professionnel.
    
    Fonctionnalités:
    - Résolution automatique des 13 marchés
    - Calcul P&L avec gestion des push
    - Analyse de précision des prédictions
    - Mise à jour des stats agrégées
    - Détection des patterns de succès/échec
    """
    
    # Mapping des marchés vers leurs conditions de win
    MARKET_RESOLUTION_RULES = {
        "over_15": lambda h, a: h + a > 1.5,
        "under_15": lambda h, a: h + a < 1.5,
        "over_25": lambda h, a: h + a > 2.5,
        "under_25": lambda h, a: h + a < 2.5,
        "over_35": lambda h, a: h + a > 3.5,
        "under_35": lambda h, a: h + a < 3.5,
        "btts_yes": lambda h, a: h > 0 and a > 0,
        "btts_no": lambda h, a: h == 0 or a == 0,
        "dc_1x": lambda h, a, r: r in ("home", "draw"),
        "dc_x2": lambda h, a, r: r in ("draw", "away"),
        "dc_12": lambda h, a, r: r in ("home", "away"),
        "dnb_home": lambda h, a, r: "home" if r == "home" else ("push" if r == "draw" else "loss"),
        "dnb_away": lambda h, a, r: "away" if r == "away" else ("push" if r == "draw" else "loss"),
    }
    
    def __init__(self, db_pool: asyncpg.Pool, api_football_key: str = None):
        self.db = db_pool
        self.api_key = api_football_key
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    # ========================================================
    # RÉSOLUTION D'UN MARCHÉ
    # ========================================================
    
    def resolve_market(
        self,
        market_type: str,
        home_score: int,
        away_score: int
    ) -> str:
        """
        Résout un marché et retourne le résultat.
        
        Returns:
            'win', 'loss', 'push', ou 'void'
        """
        total_goals = home_score + away_score
        
        # Déterminer le résultat 1X2
        if home_score > away_score:
            result_1x2 = "home"
        elif away_score > home_score:
            result_1x2 = "away"
        else:
            result_1x2 = "draw"
        
        # Résolution selon le type de marché
        if market_type == "over_15":
            return "win" if total_goals > 1 else "loss"
        elif market_type == "under_15":
            return "win" if total_goals < 2 else "loss"
        elif market_type == "over_25":
            return "win" if total_goals > 2 else "loss"
        elif market_type == "under_25":
            return "win" if total_goals < 3 else "loss"
        elif market_type == "over_35":
            return "win" if total_goals > 3 else "loss"
        elif market_type == "under_35":
            return "win" if total_goals < 4 else "loss"
        elif market_type == "btts_yes":
            return "win" if (home_score > 0 and away_score > 0) else "loss"
        elif market_type == "btts_no":
            return "win" if (home_score == 0 or away_score == 0) else "loss"
        elif market_type == "dc_1x":
            return "win" if result_1x2 in ("home", "draw") else "loss"
        elif market_type == "dc_x2":
            return "win" if result_1x2 in ("draw", "away") else "loss"
        elif market_type == "dc_12":
            return "win" if result_1x2 in ("home", "away") else "loss"
        elif market_type == "dnb_home":
            if result_1x2 == "home":
                return "win"
            elif result_1x2 == "draw":
                return "push"
            else:
                return "loss"
        elif market_type == "dnb_away":
            if result_1x2 == "away":
                return "win"
            elif result_1x2 == "draw":
                return "push"
            else:
                return "loss"
        else:
            return "void"
    
    def calculate_profit_loss(
        self,
        outcome: str,
        odds: float,
        stake: float = 1.0
    ) -> Tuple[float, float]:
        """
        Calcule le profit/loss et le ROI.
        
        Returns:
            Tuple (profit_loss, roi_pct)
        """
        if outcome == "win":
            profit = (odds - 1) * stake
            roi = (odds - 1) * 100
        elif outcome == "loss":
            profit = -stake
            roi = -100
        elif outcome == "push":
            profit = 0
            roi = 0
        else:  # void
            profit = 0
            roi = 0
        
        return round(profit, 4), round(roi, 2)
    
    def calculate_score_accuracy(
        self,
        predicted_prob: float,
        outcome: str
    ) -> float:
        """
        Calcule la précision du score prédit.
        
        Si on prédit 80% et c'est win → accuracy = 80
        Si on prédit 80% et c'est loss → accuracy = 20
        """
        if outcome == "win":
            return predicted_prob
        elif outcome == "loss":
            return 100 - predicted_prob
        else:
            return 50  # Push = neutre
    
    def validate_confidence(
        self,
        confidence: str,
        outcome: str,
        predicted_prob: float
    ) -> bool:
        """
        Vérifie si la confiance était justifiée.
        
        HIGH + win avec prob > 70 → validé
        LOW + loss → validé (on savait que c'était risqué)
        """
        if outcome == "push":
            return True
        
        if confidence == "HIGH":
            return outcome == "win" and predicted_prob >= 65
        elif confidence == "MEDIUM":
            return outcome == "win" and predicted_prob >= 50
        elif confidence == "LOW":
            # LOW confidence validée si loss (on s'y attendait)
            return outcome == "loss" or predicted_prob < 50
        
        return False
    
    # ========================================================
    # RÉSOLUTION COMPLÈTE D'UN MATCH
    # ========================================================
    
    async def resolve_match(
        self,
        match_id: str,
        home_score: int,
        away_score: int,
        ht_home_score: Optional[int] = None,
        ht_away_score: Optional[int] = None
    ) -> MatchResolutionSummary:
        """
        Résout tous les picks d'un match.
        """
        async with self.db.acquire() as conn:
            async with conn.transaction():
                # 1. Récupérer l'analyse et les prédictions
                analysis = await conn.fetchrow("""
                    SELECT * FROM fg_analyses WHERE match_id = $1
                """, match_id)
                
                if not analysis:
                    raise ValueError(f"Analysis not found for match {match_id}")
                
                predictions = await conn.fetch("""
                    SELECT * FROM fg_market_predictions 
                    WHERE match_id = $1
                    ORDER BY score DESC
                """, match_id)
                
                # 2. Déterminer le résultat 1X2
                if home_score > away_score:
                    result_1x2 = "home"
                elif away_score > home_score:
                    result_1x2 = "away"
                else:
                    result_1x2 = "draw"
                
                # 3. Insérer le résultat du match
                await conn.execute("""
                    INSERT INTO fg_match_results (
                        match_id, analysis_id, home_score, away_score,
                        ht_home_score, ht_away_score, result_1x2
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (match_id) DO UPDATE SET
                        home_score = EXCLUDED.home_score,
                        away_score = EXCLUDED.away_score,
                        resolved_at = NOW()
                """,
                    match_id,
                    analysis['analysis_id'],
                    home_score,
                    away_score,
                    ht_home_score,
                    ht_away_score,
                    result_1x2
                )
                
                # 4. Résoudre chaque marché
                results: List[ResolutionResult] = []
                
                for pred in predictions:
                    outcome = self.resolve_market(
                        pred['market_type'],
                        home_score,
                        away_score
                    )
                    
                    odds = float(pred['odds_at_analysis']) if pred['odds_at_analysis'] else 1.9
                    profit_loss, roi_pct = self.calculate_profit_loss(outcome, odds)
                    
                    score_accuracy = self.calculate_score_accuracy(
                        float(pred['probability']),
                        outcome
                    )
                    
                    confidence_validated = self.validate_confidence(
                        pred['confidence'],
                        outcome,
                        float(pred['probability'])
                    )
                    
                    # Insérer le résultat du pick
                    await conn.execute("""
                        INSERT INTO fg_pick_outcomes (
                            prediction_id, match_id, market_type,
                            predicted_score, predicted_probability,
                            predicted_confidence, predicted_value_rating,
                            predicted_kelly, odds_at_prediction,
                            outcome, actual_value, profit_loss, roi_pct
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7, $8, $9,
                            $10, $11, $12, $13
                        )
                        ON CONFLICT (prediction_id) DO UPDATE SET
                            outcome = EXCLUDED.outcome,
                            profit_loss = EXCLUDED.profit_loss,
                            roi_pct = EXCLUDED.roi_pct,
                            resolved_at = NOW()
                    """,
                        pred['id'],
                        match_id,
                        pred['market_type'],
                        pred['score'],
                        pred['probability'],
                        pred['confidence'],
                        pred['value_rating'],
                        pred['kelly_pct'],
                        pred['odds_at_analysis'],
                        outcome,
                        outcome == "win",
                        profit_loss,
                        roi_pct
                    )
                    
                    results.append(ResolutionResult(
                        prediction_id=pred['id'],
                        market_type=pred['market_type'],
                        outcome=outcome,
                        profit_loss=profit_loss,
                        roi_pct=roi_pct,
                        odds_used=odds,
                        was_correct_prediction=outcome == "win",
                        score_accuracy=score_accuracy,
                        confidence_validated=confidence_validated
                    ))
                
                # 5. Mettre à jour le statut de l'analyse
                await conn.execute("""
                    UPDATE fg_analyses 
                    SET status = 'completed', updated_at = NOW()
                    WHERE match_id = $1
                """, match_id)
                
                # 6. Calculer le résumé
                wins = sum(1 for r in results if r.outcome == "win")
                losses = sum(1 for r in results if r.outcome == "loss")
                pushes = sum(1 for r in results if r.outcome == "push")
                total_profit = sum(r.profit_loss for r in results)
                
                best_pick = max(results, key=lambda r: r.profit_loss).market_type if results else None
                worst_pick = min(results, key=lambda r: r.profit_loss).market_type if results else None
                
                logger.info(
                    "match_resolved",
                    match_id=match_id,
                    score=f"{home_score}-{away_score}",
                    wins=wins,
                    losses=losses,
                    profit=total_profit
                )
                
                return MatchResolutionSummary(
                    match_id=match_id,
                    home_team=analysis['home_team'],
                    away_team=analysis['away_team'],
                    final_score=f"{home_score}-{away_score}",
                    total_markets=len(results),
                    wins=wins,
                    losses=losses,
                    pushes=pushes,
                    total_profit=round(total_profit, 2),
                    best_pick=best_pick,
                    worst_pick=worst_pick,
                    clv_summary={}  # Sera rempli par CLVCalculator
                )
    
    # ========================================================
    # RÉCUPÉRATION AUTOMATIQUE DES RÉSULTATS
    # ========================================================
    
    async def fetch_match_result_from_api(
        self,
        fixture_id: int
    ) -> Optional[Dict[str, int]]:
        """
        Récupère le résultat d'un match depuis API-Football.
        """
        if not self.api_key:
            logger.warning("API-Football key not configured")
            return None
        
        try:
            response = await self.http_client.get(
                "https://api-football-v1.p.rapidapi.com/v3/fixtures",
                params={"id": fixture_id},
                headers={
                    "X-RapidAPI-Key": self.api_key,
                    "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
                }
            )
            
            data = response.json()
            
            if data.get("results", 0) > 0:
                fixture = data["response"][0]
                goals = fixture.get("goals", {})
                score = fixture.get("score", {})
                
                return {
                    "home_score": goals.get("home", 0),
                    "away_score": goals.get("away", 0),
                    "ht_home_score": score.get("halftime", {}).get("home"),
                    "ht_away_score": score.get("halftime", {}).get("away"),
                    "status": fixture.get("fixture", {}).get("status", {}).get("short")
                }
        except Exception as e:
            logger.error("api_football_error", error=str(e))
        
        return None
    
    async def auto_resolve_pending_matches(self) -> List[MatchResolutionSummary]:
        """
        Résout automatiquement tous les matchs terminés.
        Appelé par un cron job.
        """
        resolved = []
        
        async with self.db.acquire() as conn:
            # Récupérer les analyses en attente dont le match est terminé
            pending = await conn.fetch("""
                SELECT 
                    a.match_id,
                    a.home_team,
                    a.away_team,
                    a.commence_time
                FROM fg_analyses a
                WHERE a.status = 'pending'
                AND a.commence_time < NOW() - INTERVAL '2 hours'
                ORDER BY a.commence_time ASC
                LIMIT 50
            """)
            
            for match in pending:
                try:
                    # Essayer de récupérer le résultat
                    # (ici on pourrait parser le match_id pour extraire fixture_id)
                    # Pour l'instant, on log juste
                    logger.info(
                        "pending_match_for_resolution",
                        match_id=match['match_id'],
                        teams=f"{match['home_team']} vs {match['away_team']}"
                    )
                except Exception as e:
                    logger.error(
                        "resolution_error",
                        match_id=match['match_id'],
                        error=str(e)
                    )
        
        return resolved
    
    # ========================================================
    # ANALYSES POST-RÉSOLUTION
    # ========================================================
    
    async def analyze_resolution_patterns(
        self,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyse les patterns de succès/échec après résolution.
        """
        async with self.db.acquire() as conn:
            # Pattern par score prédit
            score_patterns = await conn.fetch("""
                SELECT
                    CASE
                        WHEN predicted_score >= 90 THEN '90-100'
                        WHEN predicted_score >= 80 THEN '80-89'
                        WHEN predicted_score >= 70 THEN '70-79'
                        WHEN predicted_score >= 60 THEN '60-69'
                        ELSE '< 60'
                    END as score_range,
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
                    ROUND(
                        SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END)::numeric /
                        NULLIF(COUNT(*), 0) * 100, 1
                    ) as win_rate,
                    ROUND(SUM(profit_loss)::numeric, 2) as profit
                FROM fg_pick_outcomes
                WHERE resolved_at >= CURRENT_DATE - INTERVAL '%s days'
                AND outcome IN ('win', 'loss')
                GROUP BY 1
                ORDER BY 1 DESC
            """ % days)
            
            # Pattern par confiance
            confidence_patterns = await conn.fetch("""
                SELECT
                    predicted_confidence,
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
                    ROUND(
                        SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END)::numeric /
                        NULLIF(COUNT(*), 0) * 100, 1
                    ) as win_rate,
                    ROUND(SUM(profit_loss)::numeric, 2) as profit
                FROM fg_pick_outcomes
                WHERE resolved_at >= CURRENT_DATE - INTERVAL '%s days'
                AND outcome IN ('win', 'loss')
                GROUP BY 1
                ORDER BY win_rate DESC NULLS LAST
            """ % days)
            
            # Pattern par value rating
            value_patterns = await conn.fetch("""
                SELECT
                    predicted_value_rating,
                    COUNT(*) as total,
                    SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
                    ROUND(
                        SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END)::numeric /
                        NULLIF(COUNT(*), 0) * 100, 1
                    ) as win_rate,
                    ROUND(SUM(profit_loss)::numeric, 2) as profit,
                    ROUND(AVG(clv_pct)::numeric, 2) as avg_clv
                FROM fg_pick_outcomes
                WHERE resolved_at >= CURRENT_DATE - INTERVAL '%s days'
                AND outcome IN ('win', 'loss')
                AND predicted_value_rating IS NOT NULL
                GROUP BY 1
                ORDER BY profit DESC NULLS LAST
            """ % days)
            
            return {
                "by_score": [dict(r) for r in score_patterns],
                "by_confidence": [dict(r) for r in confidence_patterns],
                "by_value_rating": [dict(r) for r in value_patterns]
            }
    
    async def get_streaks_by_market(self) -> List[Dict[str, Any]]:
        """
        Récupère les séries en cours par marché.
        """
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                WITH recent_outcomes AS (
                    SELECT 
                        market_type,
                        outcome,
                        resolved_at,
                        ROW_NUMBER() OVER (
                            PARTITION BY market_type 
                            ORDER BY resolved_at DESC
                        ) as rn
                    FROM fg_pick_outcomes
                    WHERE outcome IN ('win', 'loss')
                ),
                current_streak AS (
                    SELECT 
                        market_type,
                        outcome as streak_type,
                        COUNT(*) as streak_length
                    FROM (
                        SELECT 
                            market_type,
                            outcome,
                            rn - ROW_NUMBER() OVER (
                                PARTITION BY market_type, outcome 
                                ORDER BY rn
                            ) as grp
                        FROM recent_outcomes
                        WHERE rn <= 20
                    ) sub
                    WHERE grp = 0
                    GROUP BY market_type, outcome
                )
                SELECT 
                    market_type,
                    streak_type,
                    streak_length,
                    CASE 
                        WHEN streak_type = 'win' AND streak_length >= 5 
                        THEN '🔥 HOT'
                        WHEN streak_type = 'loss' AND streak_length >= 5 
                        THEN '❄️ COLD'
                        ELSE '➡️ NORMAL'
                    END as status
                FROM current_streak
                ORDER BY streak_length DESC
            """)
            
            return [dict(row) for row in rows]
