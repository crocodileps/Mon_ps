"""
TRACKING CLV 2.0 - CLV Calculator AVANCÉ
Calcul professionnel du Closing Line Value avec analyses multi-dimensionnelles
"""
import structlog
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import math
import asyncpg

logger = structlog.get_logger()


class LineMovement(str, Enum):
    """Type de mouvement de ligne"""
    STEAM = "steam"          # Mouvement rapide (sharp money)
    DRIFT = "drift"          # Mouvement lent
    STABLE = "stable"        # Peu de mouvement
    REVERSE = "reverse"      # Mouvement puis retour


@dataclass
class CLVResult:
    """Résultat complet d'un calcul CLV"""
    clv_raw: float                    # CLV brut
    clv_no_vig: float                 # CLV ajusté sans vig
    clv_weighted: float               # CLV pondéré par Kelly
    edge_captured: float              # Edge réellement capturé
    beat_closing: bool                # A-t-on battu la closing line?
    line_movement: LineMovement       # Type de mouvement
    movement_pct: float               # % de mouvement
    timing_score: float               # Score de timing (0-100)
    value_captured_pct: float         # % de valeur capturée vs disponible
    is_sharp_side: bool               # Sommes-nous du côté sharp?


class CLVCalculator:
    """
    Calculateur CLV professionnel.
    
    Métriques calculées:
    - CLV brut: (odds_pick / odds_close - 1) × 100
    - CLV no-vig: Ajusté pour éliminer la marge bookmaker
    - CLV pondéré: Pondéré par le Kelly % du pick
    - Edge capturé: Différence réelle vs probabilité marché
    - Timing score: Qualité du moment de prise
    - Sharp detection: Détection si on est du côté sharp
    """
    
    # Marge moyenne par type de marché
    MARKET_MARGINS = {
        "over_15": 0.045,
        "under_15": 0.045,
        "over_25": 0.042,
        "under_25": 0.042,
        "over_35": 0.048,
        "under_35": 0.048,
        "btts_yes": 0.050,
        "btts_no": 0.050,
        "dc_1x": 0.038,
        "dc_x2": 0.038,
        "dc_12": 0.038,
        "dnb_home": 0.040,
        "dnb_away": 0.040,
    }
    
    # Seuils pour classification des mouvements
    STEAM_THRESHOLD = 5.0      # % mouvement pour steam
    DRIFT_THRESHOLD = 2.0      # % mouvement pour drift
    SHARP_CLV_THRESHOLD = 2.0  # CLV% considéré comme sharp
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    # ========================================================
    # CALCULS CLV FONDAMENTAUX
    # ========================================================
    
    def calculate_clv_raw(
        self, 
        odds_at_pick: float, 
        odds_closing: float
    ) -> Optional[float]:
        """
        CLV brut standard.
        
        Formula: (odds_pick / odds_close - 1) × 100
        
        Interprétation:
        - CLV > 0: On a pris une meilleure cote que le marché efficient
        - CLV < 0: On a pris une moins bonne cote
        - CLV > 2%: Excellent (sharp bettor niveau)
        - CLV > 1%: Très bon
        - CLV > 0%: Bon
        """
        if not odds_closing or odds_closing <= 1:
            return None
        
        clv = ((odds_at_pick / odds_closing) - 1) * 100
        return round(clv, 3)
    
    def calculate_clv_no_vig(
        self,
        odds_at_pick: float,
        odds_closing: float,
        odds_opposite_closing: float,
        market_type: str
    ) -> Optional[float]:
        """
        CLV ajusté pour éliminer la marge du bookmaker.
        
        Plus précis car compare aux vraies probabilités.
        """
        if not odds_closing or odds_closing <= 1:
            return None
        if not odds_opposite_closing or odds_opposite_closing <= 1:
            # Fallback sur CLV brut si pas d'opposé
            return self.calculate_clv_raw(odds_at_pick, odds_closing)
        
        # Calculer les probabilités vraies (sans vig)
        implied_prob = 1 / odds_closing
        implied_prob_opp = 1 / odds_opposite_closing
        total_implied = implied_prob + implied_prob_opp
        
        # Probabilité vraie (ajustée)
        true_prob = implied_prob / total_implied
        true_odds_closing = 1 / true_prob
        
        # CLV vs cotes vraies
        clv = ((odds_at_pick / true_odds_closing) - 1) * 100
        return round(clv, 3)
    
    def calculate_clv_weighted(
        self,
        clv_raw: float,
        kelly_pct: float,
        max_kelly: float = 10.0
    ) -> float:
        """
        CLV pondéré par le Kelly %.
        
        Un CLV sur un pick avec Kelly 8% vaut plus qu'un CLV
        sur un pick avec Kelly 1%.
        """
        if kelly_pct is None or kelly_pct <= 0:
            return clv_raw
        
        # Normaliser le Kelly (0-1)
        kelly_normalized = min(kelly_pct, max_kelly) / max_kelly
        
        # Pondération: CLV × (1 + kelly_factor)
        # Un Kelly de 10% double l'importance du CLV
        weight = 1 + kelly_normalized
        
        return round(clv_raw * weight, 3)
    
    # ========================================================
    # ANALYSE DES MOUVEMENTS DE LIGNE
    # ========================================================
    
    def analyze_line_movement(
        self,
        odds_opening: float,
        odds_at_pick: float,
        odds_closing: float
    ) -> Tuple[LineMovement, float]:
        """
        Analyse le type de mouvement de la ligne.
        
        Returns:
            Tuple (type de mouvement, % de mouvement total)
        """
        if not all([odds_opening, odds_at_pick, odds_closing]):
            return LineMovement.STABLE, 0.0
        
        # Mouvement total opening -> closing
        total_movement = ((odds_closing / odds_opening) - 1) * 100
        abs_movement = abs(total_movement)
        
        # Mouvement après notre pick
        post_pick_movement = ((odds_closing / odds_at_pick) - 1) * 100
        
        # Classification
        if abs_movement >= self.STEAM_THRESHOLD:
            # Mouvement significatif
            if abs(post_pick_movement) >= self.STEAM_THRESHOLD * 0.7:
                # Le mouvement a continué après notre pick
                movement_type = LineMovement.STEAM
            else:
                # Le mouvement s'est arrêté après notre pick
                movement_type = LineMovement.DRIFT
        elif abs_movement >= self.DRIFT_THRESHOLD:
            movement_type = LineMovement.DRIFT
        else:
            movement_type = LineMovement.STABLE
        
        # Vérifier si reverse (mouvement puis retour)
        if odds_opening and odds_at_pick and odds_closing:
            # Direction opening -> pick
            dir1 = 1 if odds_at_pick > odds_opening else -1
            # Direction pick -> closing
            dir2 = 1 if odds_closing > odds_at_pick else -1
            
            if dir1 != dir2 and abs_movement < self.DRIFT_THRESHOLD:
                movement_type = LineMovement.REVERSE
        
        return movement_type, round(total_movement, 2)
    
    def is_sharp_side(
        self,
        clv: float,
        line_movement: LineMovement,
        movement_pct: float
    ) -> bool:
        """
        Détermine si on était du côté "sharp" (professionnel).
        
        Indicateurs:
        - CLV positif significatif
        - La ligne a bougé dans notre direction après notre pick
        """
        # CLV positif = on a capturé de la valeur
        if clv >= self.SHARP_CLV_THRESHOLD:
            return True
        
        # Steam dans notre direction = sharp money nous a suivis
        if line_movement == LineMovement.STEAM and movement_pct < 0:
            # Odds ont baissé après nous = sharp side
            return True
        
        return False
    
    def calculate_timing_score(
        self,
        hours_before_match: float,
        clv: float,
        line_movement: LineMovement
    ) -> float:
        """
        Score de timing (0-100).
        
        Évalue la qualité du moment de prise:
        - Trop tôt: Risque de mouvement défavorable
        - Trop tard: Moins de valeur disponible
        - Optimal: 6-24h avant le match pour la plupart des marchés
        """
        score = 50.0  # Base
        
        # Bonus/malus CLV
        if clv > 0:
            score += min(clv * 5, 25)  # Max +25 pour CLV
        else:
            score += max(clv * 3, -15)  # Max -15 pour CLV négatif
        
        # Bonus timing optimal
        if hours_before_match:
            if 6 <= hours_before_match <= 24:
                score += 15  # Fenêtre optimale
            elif 2 <= hours_before_match < 6:
                score += 10  # Bon timing
            elif 24 < hours_before_match <= 48:
                score += 5   # Acceptable
            elif hours_before_match > 48:
                score -= 5   # Trop tôt
            else:
                score -= 10  # Trop tard
        
        # Bonus si on a capturé le steam
        if line_movement == LineMovement.STEAM and clv > 0:
            score += 10
        
        return round(max(0, min(100, score)), 1)
    
    def calculate_value_captured(
        self,
        edge_predicted: float,
        clv: float
    ) -> float:
        """
        Pourcentage de la valeur prédite effectivement capturée.
        
        Si on prédit 5% d'edge et qu'on capture 3% CLV,
        on a capturé 60% de la valeur disponible.
        """
        if not edge_predicted or edge_predicted <= 0:
            return 0.0
        
        if clv is None:
            return 0.0
        
        captured = (clv / edge_predicted) * 100
        return round(max(0, min(200, captured)), 1)  # Cap à 200%
    
    # ========================================================
    # CALCUL COMPLET
    # ========================================================
    
    async def calculate_full_clv(
        self,
        odds_at_pick: float,
        odds_closing: float,
        odds_opening: Optional[float] = None,
        odds_opposite_closing: Optional[float] = None,
        market_type: str = "over_25",
        kelly_pct: Optional[float] = None,
        edge_predicted: Optional[float] = None,
        hours_before_match: Optional[float] = None
    ) -> CLVResult:
        """
        Calcul complet du CLV avec toutes les métriques.
        """
        # CLV brut
        clv_raw = self.calculate_clv_raw(odds_at_pick, odds_closing) or 0.0
        
        # CLV sans vig
        clv_no_vig = self.calculate_clv_no_vig(
            odds_at_pick, odds_closing, odds_opposite_closing, market_type
        ) or clv_raw
        
        # CLV pondéré
        clv_weighted = self.calculate_clv_weighted(clv_raw, kelly_pct)
        
        # Analyse mouvement
        line_movement, movement_pct = self.analyze_line_movement(
            odds_opening or odds_at_pick,
            odds_at_pick,
            odds_closing
        )
        
        # Sharp side?
        is_sharp = self.is_sharp_side(clv_raw, line_movement, movement_pct)
        
        # Timing score
        timing_score = self.calculate_timing_score(
            hours_before_match or 12,
            clv_raw,
            line_movement
        )
        
        # Valeur capturée
        value_captured = self.calculate_value_captured(edge_predicted, clv_raw)
        
        # Edge capturé (basé sur CLV no-vig)
        edge_captured = clv_no_vig
        
        return CLVResult(
            clv_raw=clv_raw,
            clv_no_vig=clv_no_vig,
            clv_weighted=clv_weighted,
            edge_captured=edge_captured,
            beat_closing=odds_at_pick > odds_closing,
            line_movement=line_movement,
            movement_pct=movement_pct,
            timing_score=timing_score,
            value_captured_pct=value_captured,
            is_sharp_side=is_sharp
        )
    
    # ========================================================
    # OPÉRATIONS BASE DE DONNÉES
    # ========================================================
    
    async def save_closing_odds(
        self,
        match_id: str,
        market_type: str,
        odds_closing: float,
        odds_opposite_closing: Optional[float] = None,
        bookmaker: str = "pinnacle"
    ):
        """Sauvegarde les cotes de fermeture"""
        async with self.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO fg_odds_snapshots (
                    match_id, market_type,
                    odds_pinnacle, odds_average,
                    snapshot_type, hours_before_match
                ) VALUES ($1, $2, $3, $4, 'closing', 0)
                ON CONFLICT (match_id, market_type, snapshot_type) DO UPDATE SET
                    odds_pinnacle = EXCLUDED.odds_pinnacle,
                    odds_average = EXCLUDED.odds_average,
                    collected_at = NOW()
            """, match_id, market_type, odds_closing, odds_opposite_closing)
            
            logger.info(
                "closing_odds_saved",
                match_id=match_id,
                market_type=market_type,
                odds=odds_closing
            )
    
    async def calculate_and_update_clv_for_match(
        self, 
        match_id: str
    ) -> Dict[str, CLVResult]:
        """
        Calcule et met à jour le CLV pour tous les picks d'un match.
        """
        results = {}
        
        async with self.db.acquire() as conn:
            # Récupérer les données
            rows = await conn.fetch("""
                SELECT 
                    p.id as prediction_id,
                    p.market_type,
                    p.odds_at_analysis,
                    p.kelly_pct,
                    p.edge_pct,
                    p.created_at,
                    a.commence_time,
                    os_analysis.odds_pinnacle as odds_opening,
                    cs.odds_pinnacle as odds_closing,
                    cs.odds_average as odds_opposite_closing
                FROM fg_market_predictions p
                JOIN fg_analyses a ON p.analysis_id = a.analysis_id
                LEFT JOIN fg_odds_snapshots os_analysis ON 
                    p.match_id = os_analysis.match_id 
                    AND p.market_type = os_analysis.market_type
                    AND os_analysis.snapshot_type = 'analysis'
                LEFT JOIN fg_odds_snapshots cs ON 
                    p.match_id = cs.match_id 
                    AND p.market_type = cs.market_type
                    AND cs.snapshot_type = 'closing'
                WHERE p.match_id = $1
            """, match_id)
            
            for row in rows:
                if not row['odds_at_analysis'] or not row['odds_closing']:
                    continue
                
                # Calculer heures avant match
                hours_before = None
                if row['created_at'] and row['commence_time']:
                    delta = row['commence_time'] - row['created_at']
                    hours_before = delta.total_seconds() / 3600
                
                # Calcul complet
                clv_result = await self.calculate_full_clv(
                    odds_at_pick=float(row['odds_at_analysis']),
                    odds_closing=float(row['odds_closing']),
                    odds_opening=float(row['odds_opening']) if row['odds_opening'] else None,
                    odds_opposite_closing=float(row['odds_opposite_closing']) if row['odds_opposite_closing'] else None,
                    market_type=row['market_type'],
                    kelly_pct=float(row['kelly_pct']) if row['kelly_pct'] else None,
                    edge_predicted=float(row['edge_pct']) if row['edge_pct'] else None,
                    hours_before_match=hours_before
                )
                
                # Mettre à jour la base
                await conn.execute("""
                    UPDATE fg_pick_outcomes
                    SET 
                        odds_closing = $1,
                        clv_pct = $2,
                        clv_edge = $3,
                        beat_closing = $4,
                        was_value_bet = $5,
                        hours_before_match = $6,
                        line_movement_direction = $7,
                        odds_movement = $8,
                        edge_captured = $9
                    WHERE prediction_id = $10
                """, 
                    row['odds_closing'],
                    clv_result.clv_raw,
                    clv_result.clv_no_vig,
                    clv_result.beat_closing,
                    clv_result.clv_raw > 0,
                    hours_before,
                    clv_result.line_movement.value,
                    clv_result.movement_pct,
                    clv_result.edge_captured,
                    row['prediction_id']
                )
                
                results[row['market_type']] = clv_result
                
                logger.debug(
                    "clv_calculated",
                    market=row['market_type'],
                    clv_raw=clv_result.clv_raw,
                    clv_no_vig=clv_result.clv_no_vig,
                    beat_closing=clv_result.beat_closing,
                    is_sharp=clv_result.is_sharp_side
                )
        
        return results
    
    # ========================================================
    # STATISTIQUES AVANCÉES
    # ========================================================
    
    async def get_clv_stats(self, days: int = 30) -> Dict[str, Any]:
        """Statistiques CLV globales"""
        async with self.db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_picks,
                    ROUND(AVG(clv_pct)::numeric, 3) as avg_clv,
                    ROUND(STDDEV(clv_pct)::numeric, 3) as std_clv,
                    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY clv_pct)::numeric, 3) as median_clv,
                    ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY clv_pct)::numeric, 3) as q1_clv,
                    ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY clv_pct)::numeric, 3) as q3_clv,
                    MIN(clv_pct) as min_clv,
                    MAX(clv_pct) as max_clv,
                    SUM(CASE WHEN clv_pct > 0 THEN 1 ELSE 0 END) as positive_count,
                    SUM(CASE WHEN clv_pct > 2 THEN 1 ELSE 0 END) as sharp_count,
                    ROUND(
                        SUM(CASE WHEN clv_pct > 0 THEN 1 ELSE 0 END)::numeric / 
                        NULLIF(COUNT(*), 0) * 100, 
                        1
                    ) as positive_rate,
                    ROUND(SUM(clv_pct)::numeric, 2) as total_clv_edge,
                    SUM(CASE WHEN beat_closing THEN 1 ELSE 0 END) as beat_closing_count,
                    ROUND(
                        SUM(CASE WHEN beat_closing THEN 1 ELSE 0 END)::numeric / 
                        NULLIF(COUNT(*), 0) * 100, 
                        1
                    ) as beat_closing_rate
                FROM fg_pick_outcomes
                WHERE clv_pct IS NOT NULL
                AND resolved_at >= CURRENT_DATE - INTERVAL '%s days'
            """ % days)
            
            result = dict(row) if row else {}
            
            # Ajouter le Sharpe du CLV
            if result.get('avg_clv') and result.get('std_clv') and result['std_clv'] > 0:
                result['clv_sharpe'] = round(result['avg_clv'] / result['std_clv'], 3)
            
            return result
    
    async def get_clv_by_market(self) -> List[Dict[str, Any]]:
        """CLV détaillé par marché"""
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    market_type,
                    COUNT(*) as total_picks,
                    ROUND(AVG(clv_pct)::numeric, 3) as avg_clv,
                    ROUND(STDDEV(clv_pct)::numeric, 3) as std_clv,
                    ROUND(AVG(clv_edge)::numeric, 3) as avg_clv_no_vig,
                    ROUND(
                        SUM(CASE WHEN clv_pct > 0 THEN 1 ELSE 0 END)::numeric / 
                        NULLIF(COUNT(*), 0) * 100, 
                        1
                    ) as positive_rate,
                    ROUND(
                        SUM(CASE WHEN beat_closing THEN 1 ELSE 0 END)::numeric / 
                        NULLIF(COUNT(*), 0) * 100, 
                        1
                    ) as beat_closing_rate,
                    ROUND(AVG(edge_captured)::numeric, 3) as avg_edge_captured,
                    ROUND(AVG(hours_before_match)::numeric, 1) as avg_hours_before
                FROM fg_pick_outcomes
                WHERE clv_pct IS NOT NULL
                GROUP BY market_type
                ORDER BY avg_clv DESC NULLS LAST
            """)
            
            return [dict(row) for row in rows]
    
    async def get_clv_by_timing(self) -> List[Dict[str, Any]]:
        """CLV par fenêtre de timing"""
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    CASE
                        WHEN hours_before_match >= 48 THEN '48h+'
                        WHEN hours_before_match >= 24 THEN '24-48h'
                        WHEN hours_before_match >= 12 THEN '12-24h'
                        WHEN hours_before_match >= 6 THEN '6-12h'
                        WHEN hours_before_match >= 2 THEN '2-6h'
                        ELSE '< 2h'
                    END as timing_window,
                    COUNT(*) as total_picks,
                    ROUND(AVG(clv_pct)::numeric, 3) as avg_clv,
                    ROUND(
                        SUM(CASE WHEN beat_closing THEN 1 ELSE 0 END)::numeric / 
                        NULLIF(COUNT(*), 0) * 100, 
                        1
                    ) as beat_closing_rate,
                    ROUND(AVG(edge_captured)::numeric, 3) as avg_edge_captured
                FROM fg_pick_outcomes
                WHERE clv_pct IS NOT NULL
                AND hours_before_match IS NOT NULL
                GROUP BY 1
                ORDER BY 
                    CASE 
                        WHEN hours_before_match >= 48 THEN 1
                        WHEN hours_before_match >= 24 THEN 2
                        WHEN hours_before_match >= 12 THEN 3
                        WHEN hours_before_match >= 6 THEN 4
                        WHEN hours_before_match >= 2 THEN 5
                        ELSE 6
                    END
            """)
            
            return [dict(row) for row in rows]
    
    async def get_clv_by_value_rating(self) -> List[Dict[str, Any]]:
        """CLV par value rating"""
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    p.value_rating,
                    COUNT(*) as total_picks,
                    ROUND(AVG(o.clv_pct)::numeric, 3) as avg_clv,
                    ROUND(
                        SUM(CASE WHEN o.beat_closing THEN 1 ELSE 0 END)::numeric / 
                        NULLIF(COUNT(*), 0) * 100, 
                        1
                    ) as beat_closing_rate,
                    ROUND(AVG(o.profit_loss)::numeric, 3) as avg_profit
                FROM fg_market_predictions p
                JOIN fg_pick_outcomes o ON p.id = o.prediction_id
                WHERE o.clv_pct IS NOT NULL
                AND p.value_rating IS NOT NULL
                GROUP BY p.value_rating
                ORDER BY avg_clv DESC NULLS LAST
            """)
            
            return [dict(row) for row in rows]
    
    async def detect_sharp_moves(
        self, 
        min_movement_pct: float = 5.0,
        hours_lookback: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Détecte les mouvements sharp récents.
        Utile pour identifier où la smart money va.
        """
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    sm.match_id,
                    sm.market_type,
                    a.home_team,
                    a.away_team,
                    sm.opening_odds,
                    sm.current_odds,
                    sm.movement_pct,
                    sm.movement_direction,
                    p.odds_at_analysis as our_odds,
                    CASE 
                        WHEN p.odds_at_analysis > sm.current_odds 
                        THEN 'We got better odds ✅'
                        ELSE 'Missed the move ❌'
                    END as our_position,
                    sm.detected_at
                FROM fg_sharp_money sm
                JOIN fg_analyses a ON sm.match_id = a.match_id
                LEFT JOIN fg_market_predictions p ON 
                    sm.match_id = p.match_id 
                    AND sm.market_type = p.market_type
                WHERE ABS(sm.movement_pct) >= $1
                AND sm.detected_at >= NOW() - INTERVAL '%s hours'
                ORDER BY ABS(sm.movement_pct) DESC
            """ % hours_lookback, min_movement_pct)
            
            return [dict(row) for row in rows]
