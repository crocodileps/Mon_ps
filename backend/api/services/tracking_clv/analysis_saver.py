"""
TRACKING CLV 2.0 - Analysis Saver
Sauvegarde automatique des analyses Full Gain
"""
import structlog
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
import asyncpg

from .models import (
    AnalysisCreate, 
    AnalysisResponse, 
    MarketPredictionCreate,
    MarketType
)

logger = structlog.get_logger()


class AnalysisSaver:
    """
    Sauvegarde automatiquement chaque analyse Full Gain.
    - 1 entrée fg_analyses par match
    - 13 entrées fg_market_predictions par match
    - Snapshot odds au moment de l'analyse
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        
    async def save_analysis(self, analysis: AnalysisCreate) -> AnalysisResponse:
        """
        Sauvegarde une analyse complète avec ses 13 prédictions de marchés.
        """
        async with self.db.acquire() as conn:
            async with conn.transaction():
                # 1. Insérer l'analyse principale
                analysis_id = await self._insert_analysis(conn, analysis)
                
                # 2. Insérer les 13 prédictions
                await self._insert_predictions(conn, analysis_id, analysis.match_id, analysis.predictions)
                
                # 3. Calculer et stocker le top pick
                top_pick = self._get_top_pick(analysis.predictions)
                if top_pick:
                    await conn.execute("""
                        UPDATE fg_analyses 
                        SET top_pick_market = $1, top_pick_score = $2
                        WHERE analysis_id = $3
                    """, top_pick.market_type.value, top_pick.score, analysis_id)
                
                # 4. Sauvegarder les odds snapshots
                await self._save_odds_snapshots(conn, analysis.match_id, analysis.predictions)
                
                logger.info(
                    "analysis_saved",
                    analysis_id=str(analysis_id),
                    match_id=analysis.match_id,
                    predictions_count=len(analysis.predictions)
                )
                
                return AnalysisResponse(
                    analysis_id=analysis_id,
                    match_id=analysis.match_id,
                    home_team=analysis.home_team,
                    away_team=analysis.away_team,
                    predictions_count=len(analysis.predictions),
                    top_pick_market=top_pick.market_type.value if top_pick else None,
                    top_pick_score=top_pick.score if top_pick else None,
                    created_at=datetime.now()
                )
    
    async def _insert_analysis(self, conn: asyncpg.Connection, analysis: AnalysisCreate) -> UUID:
        """Insère l'analyse principale et retourne l'UUID"""
        row = await conn.fetchrow("""
            INSERT INTO fg_analyses (
                match_id, home_team, away_team, league, commence_time,
                xg_home, xg_away, xg_total,
                home_form, away_form, h2h_data,
                llm_narrative, llm_verdict, llm_confidence,
                season, matchday, is_derby, importance,
                status
            ) VALUES (
                $1, $2, $3, $4, $5,
                $6, $7, $8,
                $9, $10, $11,
                $12, $13, $14,
                $15, $16, $17, $18,
                'pending'
            )
            ON CONFLICT (match_id) DO UPDATE SET
                xg_home = EXCLUDED.xg_home,
                xg_away = EXCLUDED.xg_away,
                xg_total = EXCLUDED.xg_total,
                llm_narrative = EXCLUDED.llm_narrative,
                llm_verdict = EXCLUDED.llm_verdict,
                updated_at = NOW()
            RETURNING analysis_id
        """,
            analysis.match_id,
            analysis.home_team,
            analysis.away_team,
            analysis.league,
            analysis.commence_time,
            analysis.xg_home,
            analysis.xg_away,
            analysis.xg_total,
            analysis.home_form,
            analysis.away_form,
            analysis.h2h_data,
            analysis.llm_narrative,
            analysis.llm_verdict,
            analysis.llm_confidence,
            analysis.season,
            analysis.matchday,
            analysis.is_derby,
            analysis.importance
        )
        return row['analysis_id']
    
    async def _insert_predictions(
        self, 
        conn: asyncpg.Connection, 
        analysis_id: UUID, 
        match_id: str,
        predictions: List[MarketPredictionCreate]
    ):
        """Insère les 13 prédictions de marchés"""
        # Calculer les rangs
        sorted_preds = sorted(predictions, key=lambda p: p.score, reverse=True)
        ranks = {p.market_type: i + 1 for i, p in enumerate(sorted_preds)}
        
        for pred in predictions:
            rank = ranks[pred.market_type]
            is_top3 = rank <= 3
            
            await conn.execute("""
                INSERT INTO fg_market_predictions (
                    analysis_id, match_id,
                    market_type, market_label, selection,
                    score, probability, confidence, recommendation,
                    value_rating, kelly_pct, edge_pct,
                    odds_at_analysis, bookmaker_analysis, implied_prob_market,
                    poisson_prob, market_prob, edge_vs_market, ev_expected,
                    factors, reasoning,
                    rank_in_match, is_top3
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9,
                    $10, $11, $12, $13, $14, $15, $16, $17, $18, $19,
                    $20, $21, $22, $23
                )
                ON CONFLICT (analysis_id, market_type) DO UPDATE SET
                    score = EXCLUDED.score,
                    probability = EXCLUDED.probability,
                    kelly_pct = EXCLUDED.kelly_pct,
                    odds_at_analysis = EXCLUDED.odds_at_analysis,
                    created_at = NOW()
            """,
                analysis_id,
                match_id,
                pred.market_type.value,
                pred.market_label,
                pred.selection,
                pred.score,
                pred.probability,
                pred.confidence.value,
                pred.recommendation.value,
                pred.value_rating.value if pred.value_rating else None,
                pred.kelly_pct,
                pred.edge_pct,
                pred.odds_at_analysis,
                pred.bookmaker_analysis,
                pred.implied_prob_market,
                pred.poisson_prob,
                pred.market_prob,
                pred.edge_vs_market,
                pred.ev_expected,
                pred.factors,
                pred.reasoning,
                rank,
                is_top3
            )
        
        # Mettre à jour le compteur de prédictions
        await conn.execute("""
            UPDATE fg_market_stats 
            SET total_predictions = total_predictions + 1
            WHERE market_type = ANY($1)
        """, [p.market_type.value for p in predictions])
    
    async def _save_odds_snapshots(
        self, 
        conn: asyncpg.Connection, 
        match_id: str,
        predictions: List[MarketPredictionCreate]
    ):
        """Sauvegarde les snapshots d'odds au moment de l'analyse"""
        for pred in predictions:
            if pred.odds_at_analysis:
                await conn.execute("""
                    INSERT INTO fg_odds_snapshots (
                        match_id, market_type,
                        odds_pinnacle, odds_best, best_bookmaker,
                        snapshot_type, hours_before_match
                    ) VALUES ($1, $2, $3, $4, $5, 'analysis', NULL)
                    ON CONFLICT (match_id, market_type, snapshot_type) DO UPDATE SET
                        odds_pinnacle = EXCLUDED.odds_pinnacle,
                        collected_at = NOW()
                """,
                    match_id,
                    pred.market_type.value,
                    pred.odds_at_analysis,
                    pred.odds_at_analysis,
                    pred.bookmaker_analysis
                )
    
    def _get_top_pick(self, predictions: List[MarketPredictionCreate]) -> Optional[MarketPredictionCreate]:
        """Retourne le top pick (score le plus élevé)"""
        if not predictions:
            return None
        return max(predictions, key=lambda p: p.score)
    
    async def get_analysis_by_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Récupère une analyse par match_id"""
        async with self.db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM fg_analyses WHERE match_id = $1
            """, match_id)
            return dict(row) if row else None
    
    async def get_pending_analyses(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Récupère les analyses en attente de résolution"""
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM fg_analyses 
                WHERE status = 'pending'
                AND commence_time < NOW()
                ORDER BY commence_time ASC
                LIMIT $1
            """, limit)
            return [dict(row) for row in rows]
