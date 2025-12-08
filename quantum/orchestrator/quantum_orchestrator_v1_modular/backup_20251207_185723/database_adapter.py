"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                    DATABASE ADAPTER - PostgreSQL Connection                           ║
╠═══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                       ║
║  Responsabilités:                                                                     ║
║  • Connexion pool PostgreSQL (asyncpg)                                               ║
║  • Chargement des 11 vecteurs DNA                                                    ║
║  • Chargement des stratégies d'équipe                                                ║
║  • Chargement de la friction matrix                                                  ║
║  • Mapping des noms d'équipes                                                        ║
║                                                                                       ║
║  NE CONNAÎT PAS: La logique des modèles, le consensus, les décisions                ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import asyncpg
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

import sys
sys.path.insert(0, '/home/Mon_ps/quantum/orchestrator')
from config.settings import DB_CONFIG, TABLES

logger = logging.getLogger("DatabaseAdapter")


# ═══════════════════════════════════════════════════════════════════════════════════════
# DATA CLASSES - Structures de données DNA
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class MarketDNA:
    """Vecteur 1: Market DNA (+20% ROI)"""
    best_strategy: str = ""
    best_strategy_roi: float = 0.0
    best_strategy_wr: float = 0.0
    best_strategy_n: int = 0
    best_strategy_profit: float = 0.0
    profitable_strategies: int = 0
    total_strategies_tested: int = 0
    empirical_profile: Dict = field(default_factory=dict)


@dataclass
class ContextDNA:
    """Vecteur 2: Context DNA (+12% ROI)"""
    home_strength: float = 50.0
    away_strength: float = 50.0
    home_wr: float = 50.0
    away_wr: float = 50.0
    home_beast: bool = False
    differential: float = 0.0


@dataclass
class RiskDNA:
    """Vecteur 3: Risk DNA (+5% ROI)"""
    variance: float = 0.5
    offensive_variance: float = 0.5
    stake_modifier: float = 1.0
    max_stake_tier: str = "MEDIUM"
    kelly_fraction: float = 0.25


@dataclass  
class TemporalDNA:
    """Vecteur 4: Temporal DNA (+25% ROI) ⭐"""
    diesel_factor: float = 0.5
    sprinter_factor: float = 0.5
    clutch_factor: float = 0.5
    best_scoring_period: str = ""
    late_game_killer: bool = False
    periods: Dict[str, float] = field(default_factory=dict)


@dataclass
class NemesisDNA:
    """Vecteur 5: Nemesis DNA (+35% ROI) ⭐⭐"""
    style_primary: str = ""
    verticality: float = 0.5
    weaknesses: List[Dict] = field(default_factory=list)
    prey_teams: List[str] = field(default_factory=list)
    nemesis_teams: List[str] = field(default_factory=list)


@dataclass
class PsycheDNA:
    """Vecteur 6: Psyche DNA (+15% ROI)"""
    profile: str = "BALANCED"           # DEFENSIVE = +11.73u!
    mentality: str = "BALANCED"
    killer_instinct: float = 1.0        # LOW > HIGH (contre-intuitif!)
    resilience_index: float = 0.5
    collapse_rate: float = 0.0
    panic_factor: float = 1.0
    comeback_mentality: float = 1.0
    lead_protection: float = 1.0
    drawing_performance: float = 1.0


@dataclass
class SentimentDNA:
    """Vecteur 7: Sentiment DNA (+8% ROI)"""
    public_team: bool = False
    brand_premium: float = 0.0
    avg_clv: float = 0.0
    positive_clv_rate: float = 0.0


@dataclass
class RosterDNA:
    """Vecteur 8: Roster DNA (+10% ROI)"""
    mvp_name: str = ""
    mvp_dependency: float = 0.0
    mvp_xg_chain: float = 0.0
    key_playmaker: str = ""
    bench_impact: float = 0.0
    keeper_status: str = "NORMAL"       # LEAKY = value!
    squad_depth: float = 0.5
    total_team_xg: float = 0.0
    top3_dependency: float = 0.0


@dataclass
class PhysicalDNA:
    """Vecteur 9: Physical DNA (+12% ROI)"""
    pressing_decay: float = 0.0
    late_game_threat: str = "NORMAL"
    intensity_60_plus: float = 0.5
    recovery_rate: float = 0.5


@dataclass
class LuckDNA:
    """Vecteur 10: Luck DNA (+8% ROI) ✨"""
    xpoints: float = 0.0
    actual_points: float = 0.0
    xpoints_delta: float = 0.0
    luck_profile: str = "NEUTRAL"       # UNLUCKY = value!
    regression_direction: str = "NEUTRAL"
    regression_magnitude: float = 0.0
    total_luck: float = 0.0
    finishing_luck: float = 0.0
    defensive_luck: float = 0.0
    ppg_vs_expected: float = 0.0


@dataclass
class ChameleonDNA:
    """Vecteur 11: Chameleon DNA (+10% ROI) ✨"""
    adaptability_index: float = 0.5
    comeback_ability: float = 0.5
    comeback_rate: float = 0.0
    tactical_flexibility: float = 0.5
    formations_used: int = 1
    halftime_adjustment_success: float = 0.5


@dataclass
class TeamDNA:
    """Structure complète des 11 vecteurs DNA"""
    team_name: str
    team_id: int = 0
    league: str = ""
    tier: str = "SILVER"
    
    # Statistiques globales
    total_matches: int = 0
    total_bets: int = 0
    total_wins: int = 0
    total_pnl: float = 0.0
    roi: float = 0.0
    win_rate: float = 0.0
    
    # Les 11 vecteurs DNA
    market_dna: MarketDNA = field(default_factory=MarketDNA)
    context_dna: ContextDNA = field(default_factory=ContextDNA)
    risk_dna: RiskDNA = field(default_factory=RiskDNA)
    temporal_dna: TemporalDNA = field(default_factory=TemporalDNA)
    nemesis_dna: NemesisDNA = field(default_factory=NemesisDNA)
    psyche_dna: PsycheDNA = field(default_factory=PsycheDNA)
    sentiment_dna: SentimentDNA = field(default_factory=SentimentDNA)
    roster_dna: RosterDNA = field(default_factory=RosterDNA)
    physical_dna: PhysicalDNA = field(default_factory=PhysicalDNA)
    luck_dna: LuckDNA = field(default_factory=LuckDNA)
    chameleon_dna: ChameleonDNA = field(default_factory=ChameleonDNA)


@dataclass
class TeamStrategy:
    """Stratégie d'équipe avec performance"""
    team_name: str
    strategy_name: str
    is_best: bool = False
    bets: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    profit: float = 0.0
    roi: float = 0.0
    parameters: Dict = field(default_factory=dict)


@dataclass
class MatchupFriction:
    """Données de friction entre deux équipes"""
    team_a: str
    team_b: str
    friction_score: float = 50.0
    style_clash_score: float = 50.0
    tempo_clash_score: float = 50.0
    mental_clash_score: float = 50.0
    chaos_potential: float = 50.0
    predicted_goals: float = 2.5
    predicted_btts_prob: float = 0.5
    predicted_over25_prob: float = 0.5
    predicted_winner: str = ""
    h2h_matches: int = 0
    h2h_avg_goals: float = 0.0
    friction_vector: Dict = field(default_factory=dict)
    confidence_level: str = "low"


# ═══════════════════════════════════════════════════════════════════════════════════════
# DATABASE ADAPTER
# ═══════════════════════════════════════════════════════════════════════════════════════

class DatabaseAdapter:
    """
    Adaptateur PostgreSQL pour le Quantum Orchestrator.
    
    Charge les données depuis les tables quantum.* et public.*
    et les convertit en dataclasses Python utilisables par les modèles.
    """
    
    def __init__(self, config: 'DatabaseConfig' = None):
        self.config = config or DB_CONFIG
        self.pool: Optional[asyncpg.Pool] = None
        self._team_name_cache: Dict[str, str] = {}
    
    async def connect(self) -> None:
        """Établit la connexion pool PostgreSQL"""
        try:
            self.pool = await asyncpg.create_pool(**self.config.asyncpg_params)
            logger.info("✅ DatabaseAdapter connecté à PostgreSQL")
        except Exception as e:
            logger.error(f"❌ Erreur connexion PostgreSQL: {e}")
            raise
    
    async def close(self) -> None:
        """Ferme le pool de connexions"""
        if self.pool:
            await self.pool.close()
            logger.info("🔌 DatabaseAdapter déconnecté")
    
    def _decimal_to_float(self, value: Any) -> float:
        """Convertit Decimal en float de manière sécurisée"""
        if value is None:
            return 0.0
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
        return 0.0
    
    def _parse_jsonb(self, value: Any) -> Dict:
        """Parse JSONB de manière sécurisée"""
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except:
                return {}
        return {}
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEAM DNA LOADING
    # ═══════════════════════════════════════════════════════════════════════════════
    
    async def get_team_dna(self, team_name: str) -> Optional[TeamDNA]:
        """
        Charge les 11 vecteurs DNA complets d'une équipe.
        
        Source: quantum.team_profiles.quantum_dna (JSONB)
        """
        if not self.pool:
            raise RuntimeError("DatabaseAdapter non connecté")
        
        query = f"""
            SELECT 
                id, team_name, tier,
                total_matches, total_bets, total_wins, total_losses,
                win_rate, total_pnl, roi,
                quantum_dna
            FROM {TABLES.TEAM_PROFILES}
            WHERE LOWER(team_name) = LOWER($1)
               OR LOWER(team_name_normalized) = LOWER($1)
            LIMIT 1
        """
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, team_name)
                
                if not row:
                    logger.warning(f"⚠️ Équipe non trouvée: {team_name}")
                    return None
                
                return self._parse_team_dna(dict(row))
                
        except Exception as e:
            logger.error(f"❌ Erreur chargement DNA {team_name}: {e}")
            return None
    
    def _parse_team_dna(self, row: Dict) -> TeamDNA:
        """Parse une row PostgreSQL en TeamDNA complet"""
        
        # Extraire quantum_dna JSONB
        quantum_dna = self._parse_jsonb(row.get('quantum_dna', {}))
        
        # Créer l'objet TeamDNA
        dna = TeamDNA(
            team_name=row.get('team_name', ''),
            team_id=row.get('id', 0),
            league=quantum_dna.get('league', ''),
            tier=row.get('tier', 'SILVER'),
            total_matches=row.get('total_matches', 0) or 0,
            total_bets=row.get('total_bets', 0) or 0,
            total_wins=row.get('total_wins', 0) or 0,
            total_pnl=self._decimal_to_float(row.get('total_pnl')),
            roi=self._decimal_to_float(row.get('roi')),
            win_rate=self._decimal_to_float(row.get('win_rate'))
        )
        
        # Parse chaque vecteur DNA
        dna.market_dna = self._parse_market_dna(quantum_dna.get('market_dna', {}))
        dna.context_dna = self._parse_context_dna(quantum_dna.get('context_dna', {}))
        dna.risk_dna = self._parse_risk_dna(quantum_dna.get('risk_dna', {}))
        dna.temporal_dna = self._parse_temporal_dna(quantum_dna.get('temporal_dna', {}))
        dna.nemesis_dna = self._parse_nemesis_dna(quantum_dna.get('nemesis_dna', {}))
        dna.psyche_dna = self._parse_psyche_dna(quantum_dna.get('psyche_dna', {}))
        dna.sentiment_dna = self._parse_sentiment_dna(quantum_dna.get('sentiment_dna', {}))
        dna.roster_dna = self._parse_roster_dna(quantum_dna.get('roster_dna', {}))
        dna.physical_dna = self._parse_physical_dna(quantum_dna.get('physical_dna', {}))
        dna.luck_dna = self._parse_luck_dna(quantum_dna.get('luck_dna', {}))
        dna.chameleon_dna = self._parse_chameleon_dna(quantum_dna.get('chameleon_dna', {}))
        
        return dna
    
    def _parse_market_dna(self, data: Dict) -> MarketDNA:
        """Parse Market DNA"""
        empirical = data.get('empirical_profile', {})
        return MarketDNA(
            best_strategy=data.get('best_strategy', ''),
            best_strategy_roi=self._decimal_to_float(empirical.get('avg_edge', 0)),
            best_strategy_wr=0.0,
            best_strategy_n=empirical.get('sample_size', 0) or 0,
            best_strategy_profit=0.0,
            profitable_strategies=data.get('profitable_strategies', 0) or 0,
            total_strategies_tested=data.get('total_strategies_tested', 0) or 0,
            empirical_profile=empirical
        )
    
    def _parse_context_dna(self, data: Dict) -> ContextDNA:
        """Parse Context DNA"""
        return ContextDNA(
            home_strength=self._decimal_to_float(data.get('home_strength', 50)),
            away_strength=self._decimal_to_float(data.get('away_strength', 50)),
            home_wr=self._decimal_to_float(data.get('home_wr', 50)),
            away_wr=self._decimal_to_float(data.get('away_wr', 50)),
            home_beast=data.get('home_beast', False) or False,
            differential=self._decimal_to_float(data.get('differential', 0))
        )
    
    def _parse_risk_dna(self, data: Dict) -> RiskDNA:
        """Parse Risk DNA"""
        return RiskDNA(
            variance=self._decimal_to_float(data.get('variance', 0.5)),
            offensive_variance=self._decimal_to_float(data.get('offensive_variance', 0.5)),
            stake_modifier=self._decimal_to_float(data.get('stake_modifier', 1.0)),
            max_stake_tier=data.get('max_stake_tier', 'MEDIUM') or 'MEDIUM',
            kelly_fraction=self._decimal_to_float(data.get('kelly_fraction', 0.25))
        )
    
    def _parse_temporal_dna(self, data: Dict) -> TemporalDNA:
        """Parse Temporal DNA"""
        return TemporalDNA(
            diesel_factor=self._decimal_to_float(data.get('diesel_factor', 0.5)),
            sprinter_factor=self._decimal_to_float(data.get('sprinter_factor', 0.5)),
            clutch_factor=self._decimal_to_float(data.get('clutch_factor', 0.5)),
            best_scoring_period=data.get('best_scoring_period', '') or '',
            late_game_killer=data.get('late_game_killer', False) or False,
            periods=data.get('periods', {}) or {}
        )
    
    def _parse_nemesis_dna(self, data: Dict) -> NemesisDNA:
        """Parse Nemesis DNA"""
        return NemesisDNA(
            style_primary=data.get('style_primary', '') or '',
            verticality=self._decimal_to_float(data.get('verticality', 0.5)),
            weaknesses=data.get('weaknesses', []) or [],
            prey_teams=data.get('prey_teams', []) or [],
            nemesis_teams=data.get('nemesis_teams', []) or []
        )
    
    def _parse_psyche_dna(self, data: Dict) -> PsycheDNA:
        """Parse Psyche DNA"""
        return PsycheDNA(
            profile=data.get('profile', 'BALANCED') or 'BALANCED',
            mentality=data.get('mentality', 'BALANCED') or 'BALANCED',
            killer_instinct=self._decimal_to_float(data.get('killer_instinct', 1.0)),
            resilience_index=self._decimal_to_float(data.get('resilience_index', 0.5)),
            collapse_rate=self._decimal_to_float(data.get('collapse_rate', 0)),
            panic_factor=self._decimal_to_float(data.get('panic_factor', 1.0)),
            comeback_mentality=self._decimal_to_float(data.get('comeback_mentality', 1.0)),
            lead_protection=self._decimal_to_float(data.get('lead_protection', 1.0)),
            drawing_performance=self._decimal_to_float(data.get('drawing_performance', 1.0))
        )
    
    def _parse_sentiment_dna(self, data: Dict) -> SentimentDNA:
        """Parse Sentiment DNA"""
        return SentimentDNA(
            public_team=data.get('public_team', False) or False,
            brand_premium=self._decimal_to_float(data.get('brand_premium', 0)),
            avg_clv=self._decimal_to_float(data.get('avg_clv', 0)),
            positive_clv_rate=self._decimal_to_float(data.get('positive_clv_rate', 0))
        )
    
    def _parse_roster_dna(self, data: Dict) -> RosterDNA:
        """Parse Roster DNA"""
        mvp = data.get('mvp', {}) or {}
        playmaker = data.get('key_playmaker', {}) or {}
        return RosterDNA(
            mvp_name=mvp.get('name', '') or '',
            mvp_dependency=self._decimal_to_float(mvp.get('dependency_score', 0)),
            mvp_xg_chain=self._decimal_to_float(mvp.get('xg_chain', 0)),
            key_playmaker=playmaker.get('name', '') or '',
            bench_impact=self._decimal_to_float(data.get('bench_impact', 0)),
            keeper_status=data.get('keeper_status', 'NORMAL') or 'NORMAL',
            squad_depth=self._decimal_to_float(data.get('squad_depth', 0.5)),
            total_team_xg=self._decimal_to_float(data.get('total_team_xg', 0)),
            top3_dependency=self._decimal_to_float(data.get('top3_dependency', 0))
        )
    
    def _parse_physical_dna(self, data: Dict) -> PhysicalDNA:
        """Parse Physical DNA"""
        return PhysicalDNA(
            pressing_decay=self._decimal_to_float(data.get('pressing_decay', 0)),
            late_game_threat=data.get('late_game_threat', 'NORMAL') or 'NORMAL',
            intensity_60_plus=self._decimal_to_float(data.get('intensity_60_plus', 0.5)),
            recovery_rate=self._decimal_to_float(data.get('recovery_rate', 0.5))
        )
    
    def _parse_luck_dna(self, data: Dict) -> LuckDNA:
        """Parse Luck DNA"""
        return LuckDNA(
            xpoints=self._decimal_to_float(data.get('xpoints', 0)),
            actual_points=self._decimal_to_float(data.get('actual_points', 0)),
            xpoints_delta=self._decimal_to_float(data.get('xpoints_delta', 0)),
            luck_profile=data.get('luck_profile', 'NEUTRAL') or 'NEUTRAL',
            regression_direction=data.get('regression_direction', 'NEUTRAL') or 'NEUTRAL',
            regression_magnitude=self._decimal_to_float(data.get('regression_magnitude', 0)),
            total_luck=self._decimal_to_float(data.get('total_luck', 0)),
            finishing_luck=self._decimal_to_float(data.get('finishing_luck', 0)),
            defensive_luck=self._decimal_to_float(data.get('defensive_luck', 0)),
            ppg_vs_expected=self._decimal_to_float(data.get('ppg_vs_expected', 0))
        )
    
    def _parse_chameleon_dna(self, data: Dict) -> ChameleonDNA:
        """Parse Chameleon DNA"""
        return ChameleonDNA(
            adaptability_index=self._decimal_to_float(data.get('adaptability_index', 0.5)),
            comeback_ability=self._decimal_to_float(data.get('comeback_ability', 0.5)),
            comeback_rate=self._decimal_to_float(data.get('comeback_rate', 0)),
            tactical_flexibility=self._decimal_to_float(data.get('tactical_flexibility', 0.5)),
            formations_used=data.get('formations_used', 1) or 1,
            halftime_adjustment_success=self._decimal_to_float(data.get('halftime_adjustment_success', 0.5))
        )
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEAM STRATEGY LOADING
    # ═══════════════════════════════════════════════════════════════════════════════
    
    async def get_team_strategy(self, team_name: str) -> Optional[TeamStrategy]:
        """
        Charge la meilleure stratégie d'une équipe.
        
        Source: quantum.team_strategies (is_best_strategy = true)
        """
        if not self.pool:
            raise RuntimeError("DatabaseAdapter non connecté")
        
        query = f"""
            SELECT 
                team_name, strategy_name, is_best_strategy,
                bets, wins, losses, win_rate, profit, roi, parameters
            FROM {TABLES.TEAM_STRATEGIES}
            WHERE LOWER(team_name) = LOWER($1)
            ORDER BY profit DESC
            LIMIT 1
        """
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, team_name)
                
                if not row:
                    return None
                
                return TeamStrategy(
                    team_name=row['team_name'],
                    strategy_name=row['strategy_name'],
                    is_best=row['is_best_strategy'] or False,
                    bets=row['bets'] or 0,
                    wins=row['wins'] or 0,
                    losses=row['losses'] or 0,
                    win_rate=self._decimal_to_float(row['win_rate']),
                    profit=self._decimal_to_float(row['profit']),
                    roi=self._decimal_to_float(row['roi']),
                    parameters=self._parse_jsonb(row['parameters'])
                )
                
        except Exception as e:
            logger.error(f"❌ Erreur chargement stratégie {team_name}: {e}")
            return None
    
    async def get_all_team_strategies(self, team_name: str) -> List[TeamStrategy]:
        """Charge toutes les stratégies d'une équipe"""
        if not self.pool:
            raise RuntimeError("DatabaseAdapter non connecté")
        
        query = f"""
            SELECT 
                team_name, strategy_name, is_best_strategy,
                bets, wins, losses, win_rate, profit, roi, parameters
            FROM {TABLES.TEAM_STRATEGIES}
            WHERE LOWER(team_name) = LOWER($1)
            ORDER BY profit DESC
        """
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, team_name)
                
                return [
                    TeamStrategy(
                        team_name=row['team_name'],
                        strategy_name=row['strategy_name'],
                        is_best=row['is_best_strategy'] or False,
                        bets=row['bets'] or 0,
                        wins=row['wins'] or 0,
                        losses=row['losses'] or 0,
                        win_rate=self._decimal_to_float(row['win_rate']),
                        profit=self._decimal_to_float(row['profit']),
                        roi=self._decimal_to_float(row['roi']),
                        parameters=self._parse_jsonb(row['parameters'])
                    )
                    for row in rows
                ]
                
        except Exception as e:
            logger.error(f"❌ Erreur chargement stratégies {team_name}: {e}")
            return []
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # MATCHUP FRICTION LOADING
    # ═══════════════════════════════════════════════════════════════════════════════
    
    async def get_matchup_friction(self, team_a: str, team_b: str) -> Optional[MatchupFriction]:
        """
        Charge la friction entre deux équipes (bidirectionnel).
        
        Source: quantum.matchup_friction
        """
        if not self.pool:
            raise RuntimeError("DatabaseAdapter non connecté")
        
        # Recherche bidirectionnelle
        query = f"""
            SELECT 
                team_a_name, team_b_name,
                friction_score, style_clash_score, tempo_clash_score, mental_clash_score,
                chaos_potential, predicted_goals, predicted_btts_prob, predicted_over25_prob,
                predicted_winner, h2h_matches, h2h_avg_goals, friction_vector, confidence_level
            FROM {TABLES.MATCHUP_FRICTION}
            WHERE (LOWER(team_a_name) = LOWER($1) AND LOWER(team_b_name) = LOWER($2))
               OR (LOWER(team_a_name) = LOWER($2) AND LOWER(team_b_name) = LOWER($1))
            LIMIT 1
        """
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, team_a, team_b)
                
                if not row:
                    logger.debug(f"⚠️ Pas de friction pour {team_a} vs {team_b}")
                    return None
                
                return MatchupFriction(
                    team_a=row['team_a_name'],
                    team_b=row['team_b_name'],
                    friction_score=self._decimal_to_float(row['friction_score']),
                    style_clash_score=self._decimal_to_float(row['style_clash_score']),
                    tempo_clash_score=self._decimal_to_float(row['tempo_clash_score']),
                    mental_clash_score=self._decimal_to_float(row['mental_clash_score']),
                    chaos_potential=self._decimal_to_float(row['chaos_potential']),
                    predicted_goals=self._decimal_to_float(row['predicted_goals']),
                    predicted_btts_prob=self._decimal_to_float(row['predicted_btts_prob']),
                    predicted_over25_prob=self._decimal_to_float(row['predicted_over25_prob']),
                    predicted_winner=row['predicted_winner'] or '',
                    h2h_matches=row['h2h_matches'] or 0,
                    h2h_avg_goals=self._decimal_to_float(row['h2h_avg_goals']),
                    friction_vector=self._parse_jsonb(row['friction_vector']),
                    confidence_level=row['confidence_level'] or 'low'
                )
                
        except Exception as e:
            logger.error(f"❌ Erreur chargement friction {team_a} vs {team_b}: {e}")
            return None
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEAM NAME MAPPING
    # ═══════════════════════════════════════════════════════════════════════════════
    
    async def normalize_team_name(self, team_name: str) -> str:
        """
        Normalise un nom d'équipe vers le nom canonique.
        
        Source: public.team_name_mapping
        """
        # Check cache first
        if team_name in self._team_name_cache:
            return self._team_name_cache[team_name]
        
        if not self.pool:
            return team_name
        
        query = f"""
            SELECT canonical_name 
            FROM {TABLES.TEAM_NAME_MAPPING}
            WHERE LOWER(source_name) = LOWER($1)
            LIMIT 1
        """
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, team_name)
                
                if row:
                    canonical = row['canonical_name']
                    self._team_name_cache[team_name] = canonical
                    return canonical
                
                # Si pas trouvé, garder le nom original
                self._team_name_cache[team_name] = team_name
                return team_name
                
        except Exception as e:
            logger.warning(f"⚠️ Erreur mapping nom {team_name}: {e}")
            return team_name
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # UTILITY METHODS
    # ═══════════════════════════════════════════════════════════════════════════════
    
    async def get_team_list(self) -> List[str]:
        """Retourne la liste de toutes les équipes dans quantum.team_profiles"""
        if not self.pool:
            raise RuntimeError("DatabaseAdapter non connecté")
        
        query = f"SELECT team_name FROM {TABLES.TEAM_PROFILES} ORDER BY team_name"
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query)
                return [row['team_name'] for row in rows]
        except Exception as e:
            logger.error(f"❌ Erreur liste équipes: {e}")
            return []
    
    async def team_exists(self, team_name: str) -> bool:
        """Vérifie si une équipe existe dans la base"""
        if not self.pool:
            return False
        
        query = f"""
            SELECT 1 FROM {TABLES.TEAM_PROFILES}
            WHERE LOWER(team_name) = LOWER($1)
               OR LOWER(team_name_normalized) = LOWER($1)
            LIMIT 1
        """
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, team_name)
                return row is not None
        except:
            return False


# ═══════════════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════════════

__all__ = [
    'DatabaseAdapter',
    'TeamDNA',
    'TeamStrategy',
    'MatchupFriction',
    'MarketDNA',
    'ContextDNA',
    'RiskDNA',
    'TemporalDNA',
    'NemesisDNA',
    'PsycheDNA',
    'SentimentDNA',
    'RosterDNA',
    'PhysicalDNA',
    'LuckDNA',
    'ChameleonDNA'
]
