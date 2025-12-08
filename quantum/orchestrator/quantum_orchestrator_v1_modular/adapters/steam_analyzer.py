"""
Steam Analyzer - Analyse des mouvements de cotes (Sharp Money Detection)

Utilise les vraies tables PostgreSQL:
- match_steam_analysis : Analyse globale par match (opening/closing odds, prob_shift)
- fg_sharp_money : Mouvements par marché (movement_pct, is_sharp_move)
- odds_history : Historique détaillé des cotes

Auteur: Mon_PS Quantum System
Version: 1.0
"""

import asyncpg
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from enum import Enum

logger = logging.getLogger("SteamAnalyzer")

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

class SteamSignal(Enum):
    """Types de signaux Steam"""
    SHARP_MONEY = "SHARP_MONEY"      # Argent professionnel (cote baisse vite)
    PUBLIC_MONEY = "PUBLIC_MONEY"    # Argent récréationnel (cote monte)
    REVERSE_LINE = "REVERSE_LINE"    # Mouvement inverse au public
    SYNDICATE = "SYNDICATE"          # Gros mouvement tardif (< 2h)
    NEUTRAL = "NEUTRAL"              # Pas de signal clair
    NO_DATA = "NO_DATA"              # Pas assez de données


class SteamTiming(Enum):
    """Timing du mouvement"""
    EARLY = "EARLY"        # > 24h avant match (news/blessure probable)
    NORMAL = "NORMAL"      # 6-24h avant (ajustement normal)
    LATE = "LATE"          # 2-6h avant (sharp money)
    SYNDICATE = "SYNDICATE"  # < 2h avant (très fiable, syndicats)


# Seuils de détection
STEAM_THRESHOLDS = {
    'significant_move_pct': 3.0,    # Mouvement > 3% = significatif
    'sharp_move_pct': 5.0,          # Mouvement > 5% = sharp money
    'extreme_move_pct': 8.0,        # Mouvement > 8% = suspect (fixing?)
    'velocity_sharp': 2.0,          # > 2%/heure = sharp
    'velocity_normal': 0.5,         # > 0.5%/heure = normal steam
}

# Bookmakers par catégorie
SHARP_BOOKMAKERS = ['pinnacle', 'betfair', 'sbobet', 'matchbook', 'asian connect']
SOFT_BOOKMAKERS = ['bet365', 'unibet', 'bwin', 'betway', 'william hill', '1xbet']


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SteamMove:
    """Un mouvement de cote détecté"""
    market: str                      # home_win, away_win, draw, over_25, btts_yes
    opening_odds: float
    current_odds: float
    closing_odds: Optional[float] = None
    movement_pct: float = 0.0
    direction: str = "STABLE"        # shortening, drifting, stable
    is_sharp: bool = False
    signal: SteamSignal = SteamSignal.NEUTRAL
    timing: SteamTiming = SteamTiming.NORMAL
    velocity: float = 0.0            # %/heure
    hours_to_kickoff: float = 0.0
    samples: int = 0
    
    @property
    def prob_shift(self) -> float:
        """Calcule le shift de probabilité implicite"""
        if self.opening_odds <= 0 or self.current_odds <= 0:
            return 0.0
        opening_prob = 1 / self.opening_odds * 100
        current_prob = 1 / self.current_odds * 100
        return current_prob - opening_prob


@dataclass
class MatchSteamAnalysis:
    """Analyse Steam complète d'un match"""
    match_id: str
    home_team: str
    away_team: str
    commence_time: datetime
    
    # Mouvements par marché
    movements: Dict[str, SteamMove] = field(default_factory=dict)
    
    # Analyse globale
    total_prob_shift: float = 0.0
    dominant_direction: str = "NEUTRAL"  # steam_home, steam_away, balanced
    steam_magnitude: str = "NONE"        # NONE, LIGHT, MODERATE, HEAVY, EXTREME
    classification: str = "NORMAL"       # NORMAL, MARKET_EFFICIENCY, SUSPICIOUS
    
    # Convergence multi-books
    sharp_soft_divergence: float = 0.0   # Écart Pinnacle vs Soft
    multi_book_convergence: bool = False
    
    # Timing
    timing: SteamTiming = SteamTiming.NORMAL
    hours_to_kickoff: float = 0.0
    
    # Recommandation
    validation_status: str = "PROCEED"   # PROCEED, CAUTION, BLOCK
    confidence_adjustment: int = 0       # -20 à +20
    
    def get_signal_for_market(self, market: str) -> Optional[SteamMove]:
        """Retourne le signal steam pour un marché"""
        return self.movements.get(market)
    
    def should_bet(self, our_prediction: str) -> Tuple[bool, str]:
        """
        Vérifie si on devrait parier basé sur le steam.
        
        Args:
            our_prediction: home, away, over_25, btts_yes, etc.
        
        Returns:
            (should_bet, reason)
        """
        move = self.movements.get(our_prediction) or self.movements.get(
            'home_win' if our_prediction == 'home' else
            'away_win' if our_prediction == 'away' else
            our_prediction
        )
        
        if not move:
            return True, "Pas de données steam"
        
        # CAS 1: Steam dans NOTRE direction = CONFIRMÉ
        if move.signal == SteamSignal.SHARP_MONEY:
            if move.direction == 'shortening':
                return True, f"✅ CONFIRMÉ: Sharp money détecté ({move.movement_pct:+.1f}%)"
        
        # CAS 2: Steam CONTRE nous = DANGER
        if move.signal == SteamSignal.SHARP_MONEY and move.direction == 'drifting':
            return False, f"⚠️ BLOQUÉ: Sharp money contre ({move.movement_pct:+.1f}%)"
        
        # CAS 3: Mouvement extrême = SUSPECT
        if abs(move.movement_pct) > STEAM_THRESHOLDS['extreme_move_pct']:
            return False, f"🚨 SUSPECT: Mouvement extrême ({move.movement_pct:+.1f}%)"
        
        # CAS 4: Late steam syndicate
        if move.timing == SteamTiming.SYNDICATE and move.is_sharp:
            if move.direction == 'shortening':
                return True, f"🎯 SYNDICATE: Argent tardif sur notre côté"
            else:
                return False, f"⚠️ SYNDICATE contre nous"
        
        return True, "Steam neutre"
    
    def to_dict(self) -> Dict[str, Any]:
        """Export en dict pour snapshot"""
        return {
            'match_id': self.match_id,
            'home_team': self.home_team,
            'away_team': self.away_team,
            'total_prob_shift': self.total_prob_shift,
            'dominant_direction': self.dominant_direction,
            'steam_magnitude': self.steam_magnitude,
            'classification': self.classification,
            'timing': self.timing.value,
            'hours_to_kickoff': self.hours_to_kickoff,
            'validation_status': self.validation_status,
            'confidence_adjustment': self.confidence_adjustment,
            'movements': {
                k: {
                    'opening': v.opening_odds,
                    'current': v.current_odds,
                    'movement_pct': v.movement_pct,
                    'direction': v.direction,
                    'is_sharp': v.is_sharp,
                    'signal': v.signal.value
                }
                for k, v in self.movements.items()
            }
        }


# ═══════════════════════════════════════════════════════════════════════════════
# STEAM ANALYZER
# ═══════════════════════════════════════════════════════════════════════════════

class SteamAnalyzer:
    """
    Analyseur de Steam (mouvements de cotes) professionnel.
    
    Utilise:
    - match_steam_analysis : Données pré-calculées
    - fg_sharp_money : Mouvements par marché
    - odds_history : Calculs en temps réel
    """
    
    def __init__(self, pool: asyncpg.Pool = None):
        self.pool = pool
    
    def set_pool(self, pool: asyncpg.Pool):
        """Configure le pool de connexions"""
        self.pool = pool
        logger.info("✅ SteamAnalyzer connecté à PostgreSQL")
    
    def _decimal_to_float(self, value: Any) -> float:
        """Convertit Decimal en float"""
        if value is None:
            return 0.0
        if isinstance(value, Decimal):
            return float(value)
        return float(value)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ANALYSE DEPUIS match_steam_analysis
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def get_match_steam_from_table(
        self, 
        match_id: str
    ) -> Optional[MatchSteamAnalysis]:
        """
        Charge l'analyse steam depuis la table match_steam_analysis.
        """
        if not self.pool:
            return None
        
        query = """
            SELECT 
                match_id, home_team, away_team, commence_time, league,
                opening_home_odds, opening_draw_odds, opening_away_odds,
                closing_home_odds, closing_draw_odds, closing_away_odds,
                opening_home_prob, opening_away_prob,
                closing_home_prob, closing_away_prob,
                prob_shift_total, steam_direction, steam_magnitude,
                classification, is_excluded_from_training, exclusion_reason,
                snapshots_count, first_snapshot_at, last_snapshot_at
            FROM match_steam_analysis
            WHERE match_id = $1
        """
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, match_id)
                
                if not row:
                    return None
                
                analysis = MatchSteamAnalysis(
                    match_id=row['match_id'],
                    home_team=row['home_team'] or '',
                    away_team=row['away_team'] or '',
                    commence_time=row['commence_time'] or datetime.now()
                )
                
                # Calculer le timing
                if row['commence_time']:
                    hours_to_kick = (row['commence_time'] - datetime.now()).total_seconds() / 3600
                    analysis.hours_to_kickoff = max(0, hours_to_kick)
                    
                    if hours_to_kick < 2:
                        analysis.timing = SteamTiming.SYNDICATE
                    elif hours_to_kick < 6:
                        analysis.timing = SteamTiming.LATE
                    elif hours_to_kick < 24:
                        analysis.timing = SteamTiming.NORMAL
                    else:
                        analysis.timing = SteamTiming.EARLY
                
                # Extraire les mouvements
                opening_home = self._decimal_to_float(row['opening_home_odds'])
                closing_home = self._decimal_to_float(row['closing_home_odds'])
                opening_away = self._decimal_to_float(row['opening_away_odds'])
                closing_away = self._decimal_to_float(row['closing_away_odds'])
                opening_draw = self._decimal_to_float(row['opening_draw_odds'])
                closing_draw = self._decimal_to_float(row['closing_draw_odds'])
                
                # Mouvement Home
                if opening_home > 0:
                    move_pct = ((closing_home - opening_home) / opening_home) * 100 if closing_home else 0
                    analysis.movements['home_win'] = SteamMove(
                        market='home_win',
                        opening_odds=opening_home,
                        current_odds=closing_home or opening_home,
                        closing_odds=closing_home,
                        movement_pct=move_pct,
                        direction='shortening' if move_pct < -1 else ('drifting' if move_pct > 1 else 'stable'),
                        is_sharp=abs(move_pct) > STEAM_THRESHOLDS['sharp_move_pct'],
                        signal=self._classify_signal(move_pct),
                        samples=row['snapshots_count'] or 1
                    )
                
                # Mouvement Away
                if opening_away > 0:
                    move_pct = ((closing_away - opening_away) / opening_away) * 100 if closing_away else 0
                    analysis.movements['away_win'] = SteamMove(
                        market='away_win',
                        opening_odds=opening_away,
                        current_odds=closing_away or opening_away,
                        closing_odds=closing_away,
                        movement_pct=move_pct,
                        direction='shortening' if move_pct < -1 else ('drifting' if move_pct > 1 else 'stable'),
                        is_sharp=abs(move_pct) > STEAM_THRESHOLDS['sharp_move_pct'],
                        signal=self._classify_signal(move_pct),
                        samples=row['snapshots_count'] or 1
                    )
                
                # Mouvement Draw
                if opening_draw > 0:
                    move_pct = ((closing_draw - opening_draw) / opening_draw) * 100 if closing_draw else 0
                    analysis.movements['draw'] = SteamMove(
                        market='draw',
                        opening_odds=opening_draw,
                        current_odds=closing_draw or opening_draw,
                        closing_odds=closing_draw,
                        movement_pct=move_pct,
                        direction='shortening' if move_pct < -1 else ('drifting' if move_pct > 1 else 'stable'),
                        is_sharp=abs(move_pct) > STEAM_THRESHOLDS['sharp_move_pct'],
                        signal=self._classify_signal(move_pct),
                        samples=row['snapshots_count'] or 1
                    )
                
                # Données globales
                analysis.total_prob_shift = self._decimal_to_float(row['prob_shift_total'])
                analysis.dominant_direction = row['steam_direction'] or 'NEUTRAL'
                analysis.steam_magnitude = row['steam_magnitude'] or 'NONE'
                analysis.classification = row['classification'] or 'NORMAL'
                
                # Ajustement de confiance basé sur le steam
                if analysis.classification == 'SUSPICIOUS':
                    analysis.confidence_adjustment = -15
                    analysis.validation_status = 'CAUTION'
                elif analysis.steam_magnitude == 'HEAVY':
                    analysis.confidence_adjustment = -10
                    analysis.validation_status = 'CAUTION'
                elif analysis.steam_magnitude == 'EXTREME':
                    analysis.confidence_adjustment = -20
                    analysis.validation_status = 'BLOCK'
                
                return analysis
                
        except Exception as e:
            logger.error(f"❌ Erreur chargement match_steam_analysis: {e}")
            return None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ANALYSE DEPUIS fg_sharp_money
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def get_sharp_money_moves(
        self, 
        match_id: str
    ) -> Dict[str, SteamMove]:
        """
        Charge les mouvements sharp depuis fg_sharp_money.
        """
        if not self.pool:
            return {}
        
        query = """
            SELECT 
                market_type, opening_odds, current_odds, closing_odds,
                movement_pct, movement_direction, is_sharp_move,
                our_odds, we_got_value, detected_at
            FROM fg_sharp_money
            WHERE match_id = $1
        """
        
        movements = {}
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, match_id)
                
                for row in rows:
                    market = row['market_type']
                    move_pct = self._decimal_to_float(row['movement_pct'])
                    
                    movements[market] = SteamMove(
                        market=market,
                        opening_odds=self._decimal_to_float(row['opening_odds']),
                        current_odds=self._decimal_to_float(row['current_odds']),
                        closing_odds=self._decimal_to_float(row['closing_odds']),
                        movement_pct=move_pct,
                        direction=row['movement_direction'] or 'stable',
                        is_sharp=row['is_sharp_move'] or False,
                        signal=SteamSignal.SHARP_MONEY if row['is_sharp_move'] else SteamSignal.NEUTRAL
                    )
                
                return movements
                
        except Exception as e:
            logger.error(f"❌ Erreur chargement fg_sharp_money: {e}")
            return {}
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ANALYSE EN TEMPS RÉEL DEPUIS odds_history
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def analyze_live_steam(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        hours_back: int = 48
    ) -> MatchSteamAnalysis:
        """
        Analyse les mouvements de cotes en temps réel depuis odds_history.
        """
        analysis = MatchSteamAnalysis(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            commence_time=datetime.now()
        )
        
        if not self.pool:
            return analysis
        
        # Charger l'historique des cotes
        query = """
            SELECT 
                bookmaker, home_odds, draw_odds, away_odds, 
                collected_at, commence_time
            FROM odds_history
            WHERE match_id = $1
              AND collected_at > NOW() - INTERVAL '%s hours'
            ORDER BY collected_at ASC
        """ % hours_back
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, match_id)
                
                if len(rows) < 2:
                    return analysis
                
                # Extraire commence_time
                if rows[0]['commence_time']:
                    analysis.commence_time = rows[0]['commence_time']
                    hours_to_kick = (analysis.commence_time - datetime.now()).total_seconds() / 3600
                    analysis.hours_to_kickoff = max(0, hours_to_kick)
                
                # Séparer par bookmaker type
                sharp_snapshots = [r for r in rows if any(sb in r['bookmaker'].lower() for sb in SHARP_BOOKMAKERS)]
                soft_snapshots = [r for r in rows if any(sb in r['bookmaker'].lower() for sb in SOFT_BOOKMAKERS)]
                
                # Analyser les mouvements 1X2
                for market, column in [('home_win', 'home_odds'), ('draw', 'draw_odds'), ('away_win', 'away_odds')]:
                    move = await self._analyze_market_movement(rows, column, market)
                    if move:
                        analysis.movements[market] = move
                
                # Calculer divergence sharp/soft
                if sharp_snapshots and soft_snapshots:
                    sharp_home = self._decimal_to_float(sharp_snapshots[-1]['home_odds'])
                    soft_home = self._decimal_to_float(soft_snapshots[-1]['home_odds'])
                    if sharp_home > 0 and soft_home > 0:
                        analysis.sharp_soft_divergence = ((1/soft_home) - (1/sharp_home)) * 100
                
                # Déterminer direction dominante
                home_move = analysis.movements.get('home_win')
                away_move = analysis.movements.get('away_win')
                
                if home_move and away_move:
                    if home_move.prob_shift > 3 and away_move.prob_shift < -3:
                        analysis.dominant_direction = 'steam_home'
                    elif away_move.prob_shift > 3 and home_move.prob_shift < -3:
                        analysis.dominant_direction = 'steam_away'
                    else:
                        analysis.dominant_direction = 'balanced'
                
                # Calculer magnitude globale
                total_shift = sum(abs(m.prob_shift) for m in analysis.movements.values())
                analysis.total_prob_shift = total_shift
                
                if total_shift < 3:
                    analysis.steam_magnitude = 'NONE'
                elif total_shift < 6:
                    analysis.steam_magnitude = 'LIGHT'
                elif total_shift < 10:
                    analysis.steam_magnitude = 'MODERATE'
                elif total_shift < 15:
                    analysis.steam_magnitude = 'HEAVY'
                else:
                    analysis.steam_magnitude = 'EXTREME'
                    analysis.classification = 'SUSPICIOUS'
                
                return analysis
                
        except Exception as e:
            logger.error(f"❌ Erreur analyse live steam: {e}")
            return analysis
    
    async def _analyze_market_movement(
        self,
        rows: List[asyncpg.Record],
        column: str,
        market: str
    ) -> Optional[SteamMove]:
        """Analyse le mouvement d'un marché spécifique"""
        
        valid_rows = [r for r in rows if r[column] and self._decimal_to_float(r[column]) > 0]
        
        if len(valid_rows) < 2:
            return None
        
        opening = self._decimal_to_float(valid_rows[0][column])
        current = self._decimal_to_float(valid_rows[-1][column])
        
        if opening <= 0:
            return None
        
        movement_pct = ((current - opening) / opening) * 100
        
        # Calculer la vélocité
        time_span = (valid_rows[-1]['collected_at'] - valid_rows[0]['collected_at']).total_seconds() / 3600
        velocity = abs(movement_pct) / time_span if time_span > 0 else 0
        
        # Déterminer la direction
        if movement_pct < -1:
            direction = 'shortening'
        elif movement_pct > 1:
            direction = 'drifting'
        else:
            direction = 'stable'
        
        # Classifier le signal
        signal = self._classify_signal(movement_pct, velocity)
        
        return SteamMove(
            market=market,
            opening_odds=opening,
            current_odds=current,
            movement_pct=movement_pct,
            direction=direction,
            is_sharp=abs(movement_pct) > STEAM_THRESHOLDS['sharp_move_pct'],
            signal=signal,
            velocity=velocity,
            samples=len(valid_rows)
        )
    
    def _classify_signal(
        self, 
        movement_pct: float, 
        velocity: float = 0
    ) -> SteamSignal:
        """Classifie le type de signal steam"""
        
        abs_move = abs(movement_pct)
        
        if abs_move < STEAM_THRESHOLDS['significant_move_pct']:
            return SteamSignal.NEUTRAL
        
        # Mouvement extrême = suspect
        if abs_move > STEAM_THRESHOLDS['extreme_move_pct']:
            return SteamSignal.SHARP_MONEY  # Ou SUSPICIOUS selon contexte
        
        # Vélocité élevée = sharp
        if velocity > STEAM_THRESHOLDS['velocity_sharp']:
            return SteamSignal.SHARP_MONEY
        
        # Mouvement significatif mais lent = public
        if abs_move > STEAM_THRESHOLDS['significant_move_pct']:
            if movement_pct < 0:
                return SteamSignal.SHARP_MONEY  # Cote baisse
            else:
                return SteamSignal.PUBLIC_MONEY  # Cote monte
        
        return SteamSignal.NEUTRAL
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ANALYSE COMPLÈTE (combine toutes les sources)
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def get_full_analysis(
        self,
        match_id: str,
        home_team: str,
        away_team: str
    ) -> MatchSteamAnalysis:
        """
        Analyse complète combinant toutes les sources de données.
        
        Priorité:
        1. match_steam_analysis (données pré-calculées)
        2. fg_sharp_money (mouvements par marché)
        3. odds_history (calcul temps réel)
        """
        
        # 1. Essayer match_steam_analysis
        analysis = await self.get_match_steam_from_table(match_id)
        
        if analysis:
            logger.debug(f"📊 Steam depuis match_steam_analysis: {analysis.steam_magnitude}")
            
            # Enrichir avec fg_sharp_money
            sharp_moves = await self.get_sharp_money_moves(match_id)
            for market, move in sharp_moves.items():
                if market not in analysis.movements:
                    analysis.movements[market] = move
            
            return analysis
        
        # 2. Sinon, calcul temps réel
        analysis = await self.analyze_live_steam(match_id, home_team, away_team)
        
        # 3. Enrichir avec fg_sharp_money
        sharp_moves = await self.get_sharp_money_moves(match_id)
        for market, move in sharp_moves.items():
            if market not in analysis.movements or move.is_sharp:
                analysis.movements[market] = move
        
        return analysis
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VALIDATION DE PARI
    # ═══════════════════════════════════════════════════════════════════════════
    
    async def validate_bet(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        our_market: str,
        our_confidence: int
    ) -> Dict[str, Any]:
        """
        Valide un pari en utilisant l'analyse steam.
        
        Args:
            match_id: ID du match
            home_team: Équipe domicile
            away_team: Équipe extérieur
            our_market: Notre marché (over_25, btts_yes, home_win, etc.)
            our_confidence: Notre confiance (0-100)
        
        Returns:
            {
                'validated': bool,
                'adjusted_confidence': int,
                'reason': str,
                'action': str,  # PROCEED, PROCEED_BOOSTED, CAUTION, BLOCK
                'steam_data': MatchSteamAnalysis
            }
        """
        analysis = await self.get_full_analysis(match_id, home_team, away_team)
        
        should_bet, reason = analysis.should_bet(our_market)
        
        adjusted = our_confidence + analysis.confidence_adjustment
        adjusted = max(0, min(100, adjusted))
        
        if not should_bet:
            action = 'BLOCK'
        elif analysis.validation_status == 'BLOCK':
            action = 'BLOCK'
        elif analysis.validation_status == 'CAUTION':
            action = 'CAUTION'
        elif analysis.confidence_adjustment > 0:
            action = 'PROCEED_BOOSTED'
        else:
            action = 'PROCEED'
        
        return {
            'validated': should_bet and action != 'BLOCK',
            'adjusted_confidence': adjusted,
            'reason': reason,
            'action': action,
            'steam_data': analysis
        }


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    'SteamAnalyzer',
    'SteamMove',
    'MatchSteamAnalysis',
    'SteamSignal',
    'SteamTiming'
]
