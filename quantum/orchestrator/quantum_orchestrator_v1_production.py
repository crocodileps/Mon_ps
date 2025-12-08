"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║          QUANTUM ORCHESTRATOR V1.0 - PRODUCTION (VRAIES DONNÉES)                      ║
╠═══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                       ║
║  Connecté aux tables PostgreSQL :                                                     ║
║  • quantum.team_profiles (99 équipes)                                                ║
║  • quantum.team_strategies (344 stratégies)                                          ║
║  • quantum.matchup_friction (3,403 paires)                                           ║
║  • quantum.market_performance (269 entrées)                                          ║
║  • quantum.temporal_patterns (99 patterns)                                           ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

import json
import uuid
import logging
import asyncio
import asyncpg
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("QuantumOrchestrator")


# ═══════════════════════════════════════════════════════════════════════════════════════
# DATABASE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════════════

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "monps_user",
    "password": "monps_secure_password_2024",
    "database": "monps_db"
}


# ═══════════════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════════════

class ModelName(Enum):
    TEAM_STRATEGY = "team_strategy"
    QUANTUM_SCORER = "quantum_scorer"
    MATCHUP_SCORER = "matchup_scorer"
    DIXON_COLES = "dixon_coles"
    SCENARIOS = "scenarios"
    DNA_FEATURES = "dna_features"

class Signal(Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    SKIP = "SKIP"

class Conviction(Enum):
    MAXIMUM = "MAXIMUM"
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"

class MomentumTrend(Enum):
    BLAZING = "BLAZING"
    HOT = "HOT"
    WARMING = "WARMING"
    NEUTRAL = "NEUTRAL"
    COOLING = "COOLING"
    FREEZING = "FREEZING"

class Robustness(Enum):
    ROCK_SOLID = "ROCK_SOLID"
    ROBUST = "ROBUST"
    UNRELIABLE = "UNRELIABLE"
    FRAGILE = "FRAGILE"


# ═══════════════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class ModelVote:
    model_name: ModelName
    signal: Signal
    confidence: float
    market: Optional[str] = None
    probability: Optional[float] = None
    reasoning: str = ""
    raw_data: Dict = field(default_factory=dict)
    
    @property
    def is_positive(self) -> bool:
        return self.signal in [Signal.STRONG_BUY, Signal.BUY]
    
    @property
    def weight_multiplier(self) -> float:
        if self.confidence >= 80:
            return 1.2
        elif self.confidence >= 60:
            return 1.0
        return 0.8

@dataclass
class MonteCarloResult:
    validation_score: float = 0.0
    success_rate: float = 0.0
    robustness: Robustness = Robustness.FRAGILE
    kelly_recommendation: float = 0.0
    
    @property
    def is_valid(self) -> bool:
        # Accepter ROCK_SOLID, ROBUST, et UNRELIABLE (pas seulement les 2 premiers)
        return self.robustness in [Robustness.ROCK_SOLID, Robustness.ROBUST, Robustness.UNRELIABLE]

@dataclass
class QuantumPick:
    pick_id: str
    match_id: str
    home_team: str
    away_team: str
    market: str
    selection: str
    odds: float
    probability: float
    edge: float
    stake: float
    expected_value: float
    confidence: float
    conviction: Conviction
    consensus: str
    monte_carlo_robustness: str
    scenarios_detected: List[str]
    model_votes_summary: Dict[str, str]
    reasoning: List[str]


# ═══════════════════════════════════════════════════════════════════════════════════════
# DATABASE LOADER
# ═══════════════════════════════════════════════════════════════════════════════════════

class DatabaseLoader:
    """Charge les données depuis PostgreSQL"""
    
    def __init__(self):
        self.pool = None
    
    async def connect(self):
        """Crée le pool de connexions"""
        self.pool = await asyncpg.create_pool(**DB_CONFIG, min_size=2, max_size=10)
        logger.info("✅ Connected to PostgreSQL")
    
    async def close(self):
        """Ferme le pool"""
        if self.pool:
            await self.pool.close()
    
    async def get_team_profile(self, team_name: str) -> Optional[Dict]:
        """Charge le profil DNA d'une équipe"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT *
                FROM quantum.team_profiles
                WHERE LOWER(team_name) = LOWER($1)
            """, team_name)
            
            if row:
                return dict(row)
            return None
    
    async def get_team_strategy(self, team_name: str) -> Optional[Dict]:
        """Charge la meilleure stratégie d'une équipe"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT *
                FROM quantum.team_strategies
                WHERE LOWER(team_name) = LOWER($1)
                ORDER BY profit DESC
                LIMIT 1
            """, team_name)
            
            if row:
                return dict(row)
            return None
    
    async def get_matchup_friction(self, home_team: str, away_team: str) -> Optional[Dict]:
        """Charge la friction entre deux équipes"""
        async with self.pool.acquire() as conn:
            # Essayer dans les deux sens (team_a vs team_b)
            row = await conn.fetchrow("""
                SELECT 
                    team_a_name as home_team,
                    team_b_name as away_team,
                    friction_score,
                    chaos_potential,
                    predicted_goals,
                    predicted_btts_prob as btts_probability,
                    predicted_over25_prob as over_25_probability,
                    friction_vector,
                    style_clash_score,
                    tempo_clash_score,
                    mental_clash_score
                FROM quantum.matchup_friction
                WHERE (LOWER(team_a_name) = LOWER($1) AND LOWER(team_b_name) = LOWER($2))
                   OR (LOWER(team_a_name) = LOWER($2) AND LOWER(team_b_name) = LOWER($1))
            """, home_team, away_team)
            
            if row:
                return dict(row)
            return None
    
    async def get_temporal_pattern(self, team_name: str) -> Optional[Dict]:
        """Charge les patterns temporels d'une équipe"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT *
                FROM quantum.temporal_patterns
                WHERE LOWER(team_name) = LOWER($1)
            """, team_name)
            
            if row:
                return dict(row)
            return None
    
    async def get_market_performance(self, team_name: str, market: str = None) -> List[Dict]:
        """Charge les performances par marché"""
        async with self.pool.acquire() as conn:
            if market:
                rows = await conn.fetch("""
                    SELECT *
                    FROM quantum.market_performance
                    WHERE LOWER(team_name) = LOWER($1) AND market = $2
                """, team_name, market)
            else:
                rows = await conn.fetch("""
                    SELECT *
                    FROM quantum.market_performance
                    WHERE LOWER(team_name) = LOWER($1)
                    ORDER BY roi DESC
                """, team_name)
            
            return [dict(r) for r in rows]
    
    async def save_snapshot(self, snapshot: Dict) -> str:
        """Sauvegarde un snapshot de pari"""
        async with self.pool.acquire() as conn:
            snapshot_id = str(uuid.uuid4())
            await conn.execute("""
                INSERT INTO quantum.bet_snapshots (
                    snapshot_id, match_id, home_team, away_team,
                    snapshot_data, model_votes, model_weights,
                    consensus_score, consensus_count, conviction,
                    monte_carlo_result, odds_snapshot,
                    final_market, final_odds, final_stake,
                    final_probability, final_edge, expected_value
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
            """,
                snapshot_id,
                snapshot.get('match_id'),
                snapshot.get('home_team'),
                snapshot.get('away_team'),
                json.dumps(snapshot.get('snapshot_data', {})),
                json.dumps(snapshot.get('model_votes', {})),
                json.dumps(snapshot.get('model_weights', {})),
                snapshot.get('consensus_score', 0),
                snapshot.get('consensus_count', 0),
                snapshot.get('conviction', 'WEAK'),
                json.dumps(snapshot.get('monte_carlo', {})),
                json.dumps(snapshot.get('odds', {})),
                snapshot.get('final_market'),
                snapshot.get('final_odds', 0),
                snapshot.get('final_stake', 0),
                snapshot.get('final_probability', 0),
                snapshot.get('final_edge', 0),
                snapshot.get('expected_value', 0)
            )
            return snapshot_id


# ═══════════════════════════════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════════════════════════════

class ModelTeamStrategy:
    """Model A: Stratégie optimale par équipe (+1,434.6u validé)"""
    
    name = ModelName.TEAM_STRATEGY
    
    async def generate_signal(self, db: DatabaseLoader, home_team: str, away_team: str, odds: Dict) -> ModelVote:
        # Récupérer les stratégies
        home_strat = await db.get_team_strategy(home_team)
        away_strat = await db.get_team_strategy(away_team)
        
        best = None
        best_team = None
        
        if home_strat and (not away_strat or home_strat.get('profit', 0) > away_strat.get('profit', 0)):
            best = home_strat
            best_team = home_team
        elif away_strat:
            best = away_strat
            best_team = away_team
        
        if not best or best.get('profit', 0) <= 0:
            return ModelVote(
                model_name=self.name,
                signal=Signal.SKIP,
                confidence=0,
                reasoning="Aucune stratégie rentable"
            )
        
        roi = float(best.get('roi', 0) or 0)
        profit = float(best.get('profit', 0) or 0)
        strategy = best.get('strategy_name', 'unknown')
        
        # Extraire le market du nom de la stratégie ou des parameters
        params = best.get('parameters', {})
        market = params.get('market', 'over_25') if isinstance(params, dict) else 'over_25'
        
        if roi >= 50:
            signal = Signal.STRONG_BUY
            confidence = min(95, 70 + roi / 5)
        elif roi >= 20:
            signal = Signal.BUY
            confidence = 60 + roi / 3
        else:
            signal = Signal.HOLD
            confidence = 50
        
        return ModelVote(
            model_name=self.name,
            signal=signal,
            confidence=confidence,
            market=market,
            reasoning=f"{best_team}: {strategy} ROI={roi:.1f}% P&L=+{profit:.1f}u",
            raw_data=best
        )


class ModelQuantumScorer:
    """Model B: Z-Score basé sur DNA (r=+0.53)"""
    
    name = ModelName.QUANTUM_SCORER
    
    def _calculate_z_score(self, profile: Dict) -> float:
        if not profile:
            return 0.0
        
        score = 0.0
        
        # Extraire le quantum_dna JSONB
        quantum_dna = profile.get('quantum_dna', {})
        if isinstance(quantum_dna, str):
            try:
                quantum_dna = json.loads(quantum_dna)
            except:
                quantum_dna = {}
        
        psyche_dna = quantum_dna.get('psyche_dna', {})
        luck_dna = quantum_dna.get('luck_dna', {})
        market_dna = quantum_dna.get('market_dna', {})
        
        # Psyche profile
        psyche_profile = psyche_dna.get('profile', '')
        if psyche_profile == 'DEFENSIVE':
            score += 1.5  # CONSERVATIVE/DEFENSIVE = +11.73u
        elif psyche_profile == 'BALANCED':
            score += 0.5
        
        # killer_instinct: LOW is better for value
        ki = psyche_dna.get('killer_instinct', 1.0)
        if ki is not None:
            ki = float(ki)
            if ki < 1.0:  # Low killer instinct = value
                score += (1.0 - ki) * 1.5
        
        # Luck profile: UNLUCKY = regression value
        luck_profile = luck_dna.get('luck_profile', '')
        if luck_profile == 'UNLUCKY':
            score += 1.2
        elif luck_profile == 'VERY_UNLUCKY':
            score += 1.5
        
        # xpoints_delta: negative = unlucky
        xpoints = luck_dna.get('xpoints_delta', 0)
        if xpoints and float(xpoints) < -2:
            score += 0.8
        
        # ROI from profile
        roi = profile.get('roi')
        if roi and float(roi) > 30:
            score += 1.0
        elif roi and float(roi) > 15:
            score += 0.5
        
        # Win rate
        wr = profile.get('win_rate')
        if wr and float(wr) > 65:
            score += 0.8
        
        # Tier (from main profile)
        tier_scores = {"ELITE": 0.5, "GOLD": 0.3, "SILVER": 0.1, "BRONZE": 0}
        tier = profile.get('tier', 'SILVER')
        score += tier_scores.get(tier, 0)
        
        return max(-3, min(3, score - 1.5))
    
    async def generate_signal(self, db: DatabaseLoader, home_team: str, away_team: str, odds: Dict) -> ModelVote:
        home_profile = await db.get_team_profile(home_team)
        away_profile = await db.get_team_profile(away_team)
        
        home_z = self._calculate_z_score(home_profile)
        away_z = self._calculate_z_score(away_profile)
        z_edge = home_z - away_z
        
        if z_edge >= 1.5:
            signal = Signal.STRONG_BUY
            target = home_team
            confidence = min(95, 70 + z_edge * 10)
        elif z_edge >= 0.5:
            signal = Signal.BUY
            target = home_team
            confidence = 60 + z_edge * 10
        elif z_edge <= -1.5:
            signal = Signal.STRONG_BUY
            target = away_team
            confidence = min(95, 70 + abs(z_edge) * 10)
        elif z_edge <= -0.5:
            signal = Signal.BUY
            target = away_team
            confidence = 60 + abs(z_edge) * 10
        else:
            signal = Signal.HOLD
            target = None
            confidence = 40
        
        return ModelVote(
            model_name=self.name,
            signal=signal,
            confidence=confidence,
            reasoning=f"Z-Score: {home_team}={home_z:.2f} vs {away_team}={away_z:.2f} (edge={z_edge:.2f})",
            raw_data={"home_z": home_z, "away_z": away_z, "z_edge": z_edge, "target": target}
        )


class ModelMatchupScorer:
    """Model C: Momentum + Friction (V3.4.2)"""
    
    name = ModelName.MATCHUP_SCORER
    
    async def generate_signal(self, db: DatabaseLoader, home_team: str, away_team: str, odds: Dict) -> ModelVote:
        friction = await db.get_matchup_friction(home_team, away_team)
        
        if not friction:
            return ModelVote(
                model_name=self.name,
                signal=Signal.HOLD,
                confidence=40,
                reasoning="Pas de données de friction"
            )
        
        # Analyser la friction (convertir Decimal en float)
        chaos = float(friction.get('chaos_potential') or 50)
        friction_score = float(friction.get('friction_score') or 50)
        style_clash = float(friction.get('style_clash_score') or 50)
        mental_clash = float(friction.get('mental_clash_score') or 50)
        
        # Score combiné
        combined_score = (friction_score + chaos + style_clash) / 3
        
        # Scénarios détectés via friction_vector
        friction_vector = friction.get('friction_vector', {})
        if isinstance(friction_vector, str):
            try:
                friction_vector = json.loads(friction_vector)
            except:
                friction_vector = {}
        
        # Compter les frictions élevées comme "scénarios"
        high_friction_count = sum(1 for v in friction_vector.values() if v and float(v) > 0.6)
        
        # Signal basé sur friction
        if combined_score >= 60:
            signal = Signal.STRONG_BUY
            confidence = 75 + (combined_score - 60)
        elif combined_score >= 50:
            signal = Signal.BUY
            confidence = 60 + combined_score / 5
        elif combined_score >= 40:
            signal = Signal.HOLD
            confidence = 50
        else:
            signal = Signal.SKIP
            confidence = 30
        
        return ModelVote(
            model_name=self.name,
            signal=signal,
            confidence=confidence,
            reasoning=f"Friction={friction_score:.0f}, Chaos={chaos:.0f}, Combined={combined_score:.0f}",
            raw_data={
                "friction": dict(friction),
                "combined_score": combined_score,
                "high_friction_count": high_friction_count
            }
        )


class ModelDixonColes:
    """Model D: Probabilités BTTS/Over"""
    
    name = ModelName.DIXON_COLES
    
    async def generate_signal(self, db: DatabaseLoader, home_team: str, away_team: str, odds: Dict) -> ModelVote:
        friction = await db.get_matchup_friction(home_team, away_team)
        
        if not friction:
            return ModelVote(
                model_name=self.name,
                signal=Signal.HOLD,
                confidence=40,
                reasoning="Pas de probabilités disponibles"
            )
        
        # Probabilités de la friction matrix (convertir Decimal en float)
        btts_prob = float(friction.get('btts_probability') or 0.5)
        over25_prob = float(friction.get('over_25_probability') or 0.5)
        predicted_goals = float(friction.get('predicted_goals') or 2.5)
        
        best_market = None
        best_edge = -1.0
        best_prob = 0.0
        
        # Vérifier Over 2.5
        if 'over_25' in odds and odds['over_25'] > 1 and over25_prob > 0:
            implied = 1.0 / float(odds['over_25'])
            edge = over25_prob - implied
            if edge > best_edge:
                best_edge = edge
                best_market = 'over_25'
                best_prob = over25_prob
        
        # Vérifier BTTS
        if 'btts_yes' in odds and odds['btts_yes'] > 1 and btts_prob > 0:
            implied = 1.0 / float(odds['btts_yes'])
            edge = btts_prob - implied
            if edge > best_edge:
                best_edge = edge
                best_market = 'btts_yes'
                best_prob = btts_prob
        
        if best_edge < 0.02:
            return ModelVote(
                model_name=self.name,
                signal=Signal.HOLD,
                confidence=40,
                reasoning=f"Edge insuffisant: {best_edge*100:.1f}%"
            )
        
        if best_edge >= 0.10:
            signal = Signal.STRONG_BUY
            confidence = min(90, 70 + best_edge * 200)
        elif best_edge >= 0.05:
            signal = Signal.BUY
            confidence = 60 + best_edge * 200
        else:
            signal = Signal.HOLD
            confidence = 50
        
        return ModelVote(
            model_name=self.name,
            signal=signal,
            confidence=confidence,
            market=best_market,
            probability=best_prob,
            reasoning=f"Dixon-Coles: {best_market} P={best_prob:.1%} Edge={best_edge:.1%}",
            raw_data={
                "btts_prob": btts_prob,
                "over25_prob": over25_prob,
                "predicted_goals": predicted_goals,
                "best_market": best_market,
                "best_edge": best_edge
            }
        )


class ModelScenarios:
    """Model E: Scénarios détectés"""
    
    name = ModelName.SCENARIOS
    
    async def generate_signal(self, db: DatabaseLoader, home_team: str, away_team: str, odds: Dict) -> ModelVote:
        friction = await db.get_matchup_friction(home_team, away_team)
        
        scenarios = []
        if friction:
            raw_scenarios = friction.get('scenarios_triggered', [])
            if isinstance(raw_scenarios, str):
                try:
                    scenarios = json.loads(raw_scenarios) if raw_scenarios else []
                except:
                    scenarios = []
            else:
                scenarios = raw_scenarios or []
        
        if not scenarios:
            return ModelVote(
                model_name=self.name,
                signal=Signal.HOLD,
                confidence=40,
                reasoning="Aucun scénario détecté"
            )
        
        # Marchés suggérés par scénario
        scenario_markets = {
            "SNIPER_DUEL": "btts_yes",
            "LATE_PUNISHMENT": "over_25",
            "TOTAL_CHAOS": "over_35",
            "CONSERVATIVE_WALL": "under_25",
            "DIESEL_DUEL": "over_25",
            "GLASS_CANNON": "btts_yes"
        }
        
        n_scenarios = len(scenarios)
        
        if n_scenarios >= 3:
            signal = Signal.STRONG_BUY
            confidence = 80
        elif n_scenarios >= 2:
            signal = Signal.BUY
            confidence = 70
        elif n_scenarios >= 1:
            signal = Signal.HOLD
            confidence = 55
        else:
            signal = Signal.SKIP
            confidence = 30
        
        # Trouver le marché suggéré
        market = None
        for s in scenarios:
            if s in scenario_markets:
                market = scenario_markets[s]
                break
        
        return ModelVote(
            model_name=self.name,
            signal=signal,
            confidence=confidence,
            market=market,
            reasoning=f"Scénarios: {scenarios}",
            raw_data={"scenarios": scenarios, "count": n_scenarios}
        )


class ModelDNAFeatures:
    """Model F: 11 vecteurs DNA"""
    
    name = ModelName.DNA_FEATURES
    
    async def generate_signal(self, db: DatabaseLoader, home_team: str, away_team: str, odds: Dict) -> ModelVote:
        home_profile = await db.get_team_profile(home_team)
        away_profile = await db.get_team_profile(away_team)
        
        signals = []
        total_bonus = 0
        
        for profile, team in [(home_profile, home_team), (away_profile, away_team)]:
            if not profile:
                continue
            
            # Extraire quantum_dna JSONB
            quantum_dna = profile.get('quantum_dna', {})
            if isinstance(quantum_dna, str):
                try:
                    quantum_dna = json.loads(quantum_dna)
                except:
                    quantum_dna = {}
            
            psyche_dna = quantum_dna.get('psyche_dna', {})
            luck_dna = quantum_dna.get('luck_dna', {})
            market_dna = quantum_dna.get('market_dna', {})
            
            # Psyche profile DEFENSIVE = value
            psyche_profile = psyche_dna.get('profile', '')
            if psyche_profile == 'DEFENSIVE':
                signals.append(f"{team}: DEFENSIVE profile (+8u)")
                total_bonus += 8
            
            # Low killer_instinct = value
            ki = psyche_dna.get('killer_instinct')
            if ki and float(ki) < 0.8:
                signals.append(f"{team}: Low killer instinct (+5u)")
                total_bonus += 5
            
            # UNLUCKY = regression value
            luck_profile = luck_dna.get('luck_profile', '')
            if luck_profile in ['UNLUCKY', 'VERY_UNLUCKY']:
                signals.append(f"{team}: {luck_profile} regression (+6u)")
                total_bonus += 6
            
            # Negative xpoints_delta = value
            xpoints = luck_dna.get('xpoints_delta')
            if xpoints and float(xpoints) < -2:
                signals.append(f"{team}: xPoints debt {xpoints} (+4u)")
                total_bonus += 4
            
            # High comeback mentality
            comeback = psyche_dna.get('comeback_mentality')
            if comeback and float(comeback) > 2.0:
                signals.append(f"{team}: High comeback ({comeback}) (+3u)")
                total_bonus += 3
            
            # ROI positif de l'équipe
            roi = profile.get('roi')
            if roi and float(roi) > 30:
                signals.append(f"{team}: High ROI {roi}% (+5u)")
                total_bonus += 5
            elif roi and float(roi) > 15:
                signals.append(f"{team}: Good ROI {roi}% (+3u)")
                total_bonus += 3
            
            # Win rate élevé
            wr = profile.get('win_rate')
            if wr and float(wr) > 65:
                signals.append(f"{team}: High WR {wr}% (+4u)")
                total_bonus += 4
        
        if not signals:
            return ModelVote(
                model_name=self.name,
                signal=Signal.HOLD,
                confidence=40,
                reasoning="Pas de signaux DNA forts"
            )
        
        if total_bonus >= 15:
            signal = Signal.STRONG_BUY
            confidence = min(90, 60 + total_bonus)
        elif total_bonus >= 8:
            signal = Signal.BUY
            confidence = 55 + total_bonus
        else:
            signal = Signal.HOLD
            confidence = 45
        
        return ModelVote(
            model_name=self.name,
            signal=signal,
            confidence=confidence,
            reasoning=f"DNA signals: {signals}, Total bonus: +{total_bonus:.1f}u",
            raw_data={"signals": signals, "total_bonus": total_bonus}
        )


# ═══════════════════════════════════════════════════════════════════════════════════════
# CONSENSUS ENGINE
# ═══════════════════════════════════════════════════════════════════════════════════════

class WeightedConsensusEngine:
    BASE_WEIGHTS = {
        ModelName.TEAM_STRATEGY: 1.25,
        ModelName.QUANTUM_SCORER: 1.15,
        ModelName.MATCHUP_SCORER: 1.10,
        ModelName.DIXON_COLES: 1.0,
        ModelName.SCENARIOS: 0.85,
        ModelName.DNA_FEATURES: 1.05
    }
    
    CONSENSUS_THRESHOLD = 0.50  # 50% du poids (au lieu de 60%)
    MIN_POSITIVE_VOTES = 3      # Minimum 3/6 votes positifs
    
    def evaluate(self, votes: List[ModelVote]) -> Tuple[bool, float, Conviction, int, Dict]:
        total_weight = 0
        positive_weight = 0
        vote_details = {}
        
        for vote in votes:
            weight = self.BASE_WEIGHTS.get(vote.model_name, 1.0) * vote.weight_multiplier
            total_weight += weight
            
            if vote.is_positive:
                positive_weight += weight
            
            vote_details[vote.model_name.value] = {
                "signal": vote.signal.value,
                "confidence": vote.confidence,
                "weight": weight
            }
        
        consensus_score = positive_weight / total_weight if total_weight > 0 else 0
        consensus_count = sum(1 for v in votes if v.is_positive)
        
        if consensus_count == 6:
            conviction = Conviction.MAXIMUM
        elif consensus_count >= 5:
            conviction = Conviction.STRONG
        elif consensus_count >= 4:
            conviction = Conviction.MODERATE
        else:
            conviction = Conviction.WEAK
        
        consensus_reached = consensus_score >= self.CONSENSUS_THRESHOLD and consensus_count >= self.MIN_POSITIVE_VOTES
        
        return consensus_reached, consensus_score, conviction, consensus_count, vote_details


# ═══════════════════════════════════════════════════════════════════════════════════════
# MONTE CARLO VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════════════

class MonteCarloValidator:
    def __init__(self, n_simulations: int = 5000):
        self.n_simulations = n_simulations
    
    def validate(self, probability: float, edge: float, confidence: float) -> MonteCarloResult:
        successes = 0
        scores = []
        
        for _ in range(self.n_simulations):
            noise = np.random.uniform(-0.15, 0.15)
            noisy_prob = probability * (1 + noise)
            noisy_edge = edge * (1 + noise)
            noisy_conf = confidence * (1 + noise)
            
            # Score sur 100 (pas sur 1)
            score = (noisy_prob * 40 + noisy_edge * 100 * 30 + noisy_conf * 30)
            scores.append(score)
            
            # Seuil: score >= 45 (réaliste) et edge positif
            if score >= 45 and noisy_edge > 0.02:
                successes += 1
        
        success_rate = successes / self.n_simulations
        validation_score = np.mean(scores)
        std_dev = np.std(scores)
        
        if success_rate >= 0.70 and std_dev < 15:
            robustness = Robustness.ROCK_SOLID
        elif success_rate >= 0.55 and std_dev < 20:
            robustness = Robustness.ROBUST
        elif success_rate >= 0.40:
            robustness = Robustness.UNRELIABLE
        else:
            robustness = Robustness.FRAGILE
        
        kelly = max(0, min(0.25, (edge * probability) / (1 - probability))) if probability < 1 else 0
        
        return MonteCarloResult(
            validation_score=validation_score,
            success_rate=success_rate,
            robustness=robustness,
            kelly_recommendation=kelly
        )


# ═══════════════════════════════════════════════════════════════════════════════════════
# QUANTUM ORCHESTRATOR PRODUCTION
# ═══════════════════════════════════════════════════════════════════════════════════════

class QuantumOrchestratorProduction:
    """
    Orchestrateur connecté aux vraies données PostgreSQL
    """
    
    def __init__(self):
        self.db = DatabaseLoader()
        self.models = [
            ModelTeamStrategy(),
            ModelQuantumScorer(),
            ModelMatchupScorer(),
            ModelDixonColes(),
            ModelScenarios(),
            ModelDNAFeatures()
        ]
        self.consensus_engine = WeightedConsensusEngine()
        self.mc_validator = MonteCarloValidator()
    
    async def connect(self):
        await self.db.connect()
        logger.info("🚀 Quantum Orchestrator V1.0 Production initialized")
    
    async def close(self):
        await self.db.close()
    
    async def analyze_match(
        self,
        home_team: str,
        away_team: str,
        match_id: str,
        odds: Dict[str, float]
    ) -> Optional[QuantumPick]:
        """Analyse un match avec les vraies données"""
        
        logger.info(f"📊 Analyzing: {home_team} vs {away_team}")
        
        # Générer les votes des 6 modèles
        votes: List[ModelVote] = []
        for model in self.models:
            try:
                vote = await model.generate_signal(self.db, home_team, away_team, odds)
                votes.append(vote)
                emoji = "✅" if vote.is_positive else "⬜"
                logger.info(f"  {emoji} {model.name.value}: {vote.signal.value} ({vote.confidence:.0f}%) - {vote.reasoning[:60]}")
            except Exception as e:
                logger.error(f"  ❌ {model.name.value}: Error - {e}")
                votes.append(ModelVote(
                    model_name=model.name,
                    signal=Signal.HOLD,
                    confidence=0,
                    reasoning=f"Error: {e}"
                ))
        
        # Évaluer le consensus
        consensus_reached, consensus_score, conviction, consensus_count, vote_details = \
            self.consensus_engine.evaluate(votes)
        
        logger.info(f"📈 Consensus: {consensus_score:.1%} ({consensus_count}/6) - {conviction.value}")
        
        if not consensus_reached:
            logger.info(f"⏭️ SKIP - Consensus insuffisant")
            return None
        
        # Trouver le meilleur marché
        market_votes = {}
        for vote in votes:
            if vote.market and vote.is_positive:
                market_votes[vote.market] = market_votes.get(vote.market, 0) + 1
        
        best_market = max(market_votes, key=market_votes.get) if market_votes else "over_25"
        final_odds = odds.get(best_market, 1.90)
        
        # Calculer probabilité et edge
        avg_confidence = np.mean([v.confidence for v in votes])
        
        # Chercher la probabilité dans les votes Dixon-Coles
        dixon_vote = next((v for v in votes if v.model_name == ModelName.DIXON_COLES), None)
        if dixon_vote and dixon_vote.raw_data.get('best_market') == best_market:
            probability = dixon_vote.raw_data.get(f"{best_market.replace('_', '')}_prob", 0.55)
        else:
            # Estimation basée sur les votes
            probability = 0.50 + (consensus_score - 0.5) * 0.3
        
        edge = probability - (1 / final_odds) if final_odds > 1 else 0
        
        # Monte Carlo validation
        mc_result = self.mc_validator.validate(probability, edge, avg_confidence / 100)
        
        logger.info(f"🎰 Monte Carlo: {mc_result.robustness.value} (success={mc_result.success_rate:.1%})")
        
        if not mc_result.is_valid:
            logger.info(f"⏭️ SKIP - Monte Carlo rejected: {mc_result.robustness.value}")
            return None
        
        # Calculer le stake
        base_stake = mc_result.kelly_recommendation * 100  # En unités
        
        # Modifiers
        conviction_mult = {Conviction.MAXIMUM: 1.3, Conviction.STRONG: 1.15, Conviction.MODERATE: 1.0}
        stake = base_stake * conviction_mult.get(conviction, 1.0)
        stake = max(0.5, min(5.0, round(stake * 2) / 2))  # Clamp et arrondi
        
        expected_value = stake * edge
        
        # Scénarios détectés
        scenario_vote = next((v for v in votes if v.model_name == ModelName.SCENARIOS), None)
        scenarios = scenario_vote.raw_data.get('scenarios', []) if scenario_vote else []
        
        # Créer le pick
        pick = QuantumPick(
            pick_id=str(uuid.uuid4()),
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            market=best_market,
            selection=best_market.replace("_", " ").title(),
            odds=final_odds,
            probability=probability,
            edge=edge * 100,
            stake=stake,
            expected_value=expected_value,
            confidence=avg_confidence,
            conviction=conviction,
            consensus=f"{consensus_count}/6 models agree",
            monte_carlo_robustness=mc_result.robustness.value,
            scenarios_detected=scenarios,
            model_votes_summary={v.model_name.value: v.signal.value for v in votes},
            reasoning=[
                f"Consensus: {consensus_score:.1%} ({conviction.value})",
                f"Monte Carlo: {mc_result.robustness.value} ({mc_result.success_rate:.1%})",
                f"Market: {best_market} @ {final_odds:.2f}",
                f"Probability: {probability:.1%} | Edge: {edge*100:.1f}%",
                f"Stake: {stake:.1f}u | EV: {expected_value:.2f}u"
            ]
        )
        
        # Sauvegarder le snapshot
        try:
            snapshot_id = await self.db.save_snapshot({
                'match_id': match_id,
                'home_team': home_team,
                'away_team': away_team,
                'snapshot_data': {'pick': asdict(pick)},
                'model_votes': vote_details,
                'model_weights': {k.value: v for k, v in self.consensus_engine.BASE_WEIGHTS.items()},
                'consensus_score': consensus_score,
                'consensus_count': consensus_count,
                'conviction': conviction.value,
                'monte_carlo': asdict(mc_result),
                'odds': odds,
                'final_market': best_market,
                'final_odds': final_odds,
                'final_stake': stake,
                'final_probability': probability,
                'final_edge': edge,
                'expected_value': expected_value
            })
            logger.info(f"💾 Snapshot saved: {snapshot_id[:8]}...")
        except Exception as e:
            logger.warning(f"⚠️ Snapshot save failed: {e}")
        
        return pick


# ═══════════════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════════════

async def main():
    """Test de l'orchestrateur production"""
    
    orchestrator = QuantumOrchestratorProduction()
    
    try:
        await orchestrator.connect()
        
        # Test avec un match réel
        odds = {
            "home_win": 1.45,
            "draw": 4.50,
            "away_win": 6.50,
            "over_25": 1.72,
            "under_25": 2.10,
            "btts_yes": 1.85,
            "btts_no": 1.95,
            "over_35": 2.40
        }
        
        # Test avec des équipes de ta base
        test_matches = [
            ("Barcelona", "Athletic Club"),
            ("Real Madrid", "Getafe"),
            ("Liverpool", "Manchester City"),
            ("Celta Vigo", "Sevilla"),
            ("Monaco", "Lyon")
        ]
        
        picks = []
        for home, away in test_matches:
            pick = await orchestrator.analyze_match(home, away, f"test_{home}_{away}", odds)
            if pick:
                picks.append(pick)
            print("-" * 80)
        
        # Résumé
        print("\n" + "=" * 80)
        print("📊 QUANTUM PICKS SUMMARY")
        print("=" * 80)
        
        if picks:
            for pick in picks:
                print(f"\n✅ {pick.home_team} vs {pick.away_team}")
                print(f"   Market: {pick.market} @ {pick.odds:.2f}")
                print(f"   Edge: {pick.edge:.1f}% | Stake: {pick.stake:.1f}u | EV: {pick.expected_value:.2f}u")
                print(f"   Conviction: {pick.conviction.value} | MC: {pick.monte_carlo_robustness}")
        else:
            print("\n⚠️ Aucun pick généré (données manquantes ou consensus insuffisant)")
        
    finally:
        await orchestrator.close()


if __name__ == "__main__":
    asyncio.run(main())
