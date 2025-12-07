"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                    QUANTUM DNA LOADER 2.0                                             ║
║                                                                                       ║
║  Charge les 11 vecteurs DNA depuis PostgreSQL.                                       ║
║  Optimisé avec cache et lazy loading.                                                ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import logging

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DNALoader")


@dataclass
class DNACache:
    """Cache pour les DNA chargés"""
    data: Dict[str, Any]
    loaded_at: datetime
    ttl_minutes: int = 30
    
    @property
    def is_expired(self) -> bool:
        return datetime.now() > self.loaded_at + timedelta(minutes=self.ttl_minutes)


class QuantumDNALoader:
    """
    Chargeur de DNA Quantum depuis PostgreSQL.
    
    Charge les 11 vecteurs DNA:
    1. context_dna - xG 2024
    2. current_season - xG 2025/2026
    3. psyche_dna - killer_instinct, mentality
    4. nemesis_dna - verticality, keeper_status
    5. temporal_dna - diesel_factor, periods
    6. tactical_dna - formation, set_piece
    7. roster_dna - mvp_dependency, playmaker
    8. physical_dna - stamina, pressing
    9. market_dna - empirical_profile
    10. luck_dna - xpoints_delta
    11. chameleon_dna - comeback_ability
    """
    
    def __init__(self, db_pool=None):
        self.db_pool = db_pool
        self._cache: Dict[str, DNACache] = {}
        self._team_name_mapping: Dict[str, str] = {}
        
    async def get_team_dna(self, team_name: str) -> Dict[str, Any]:
        """
        Charge le DNA complet d'une équipe.
        
        Returns:
            Dict avec les 11 vecteurs DNA
        """
        # Normaliser le nom
        normalized = self._normalize_team_name(team_name)
        
        # Vérifier le cache
        cache_key = f"dna_{normalized}"
        if cache_key in self._cache and not self._cache[cache_key].is_expired:
            logger.debug(f"Cache hit for {team_name}")
            return self._cache[cache_key].data
        
        # Charger depuis la DB
        dna = await self._load_from_db(normalized)
        
        # Mettre en cache
        self._cache[cache_key] = DNACache(data=dna, loaded_at=datetime.now())
        
        return dna
    
    async def get_match_dna(self, home_team: str, away_team: str) -> Tuple[Dict, Dict, Dict]:
        """
        Charge les DNA des deux équipes + friction pré-calculée.
        
        Returns:
            (home_dna, away_dna, friction_data)
        """
        # Charger les deux DNA en parallèle
        home_dna, away_dna = await asyncio.gather(
            self.get_team_dna(home_team),
            self.get_team_dna(away_team)
        )
        
        # Charger la friction pré-calculée
        friction = await self._load_friction(home_team, away_team)
        
        return home_dna, away_dna, friction
    
    async def _load_from_db(self, team_name: str) -> Dict[str, Any]:
        """Charge le DNA depuis quantum.team_profiles"""
        
        if self.db_pool is None:
            # Mode simulation pour tests
            return self._get_simulated_dna(team_name)
        
        async with self.db_pool.acquire() as conn:
            # Charger le profil principal
            row = await conn.fetchrow("""
                SELECT 
                    team_id, team_name, league,
                    quantum_dna,
                    best_strategy, best_strategy_roi, best_strategy_wr,
                    created_at, updated_at
                FROM quantum.team_profiles
                WHERE LOWER(team_name) = LOWER($1)
                   OR LOWER(team_name) LIKE LOWER($2)
            """, team_name, f"%{team_name}%")
            
            if not row:
                logger.warning(f"Team not found: {team_name}")
                return self._get_default_dna(team_name)
            
            # Parser le quantum_dna JSON
            quantum_dna = row['quantum_dna'] if row['quantum_dna'] else {}
            if isinstance(quantum_dna, str):
                quantum_dna = json.loads(quantum_dna)
            
            # Charger les données supplémentaires des autres tables
            strategies = await self._load_strategies(conn, row['team_id'])
            temporal = await self._load_temporal(conn, row['team_id'])
            
            # Construire le DNA complet
            return self._build_complete_dna(row, quantum_dna, strategies, temporal)
    
    async def _load_strategies(self, conn, team_id: int) -> List[Dict]:
        """Charge les stratégies de l'équipe"""
        rows = await conn.fetch("""
            SELECT 
                strategy_name, condition_type, market_type,
                total_bets, wins, profit, roi, win_rate,
                avg_odds, is_best_strategy
            FROM quantum.team_strategies
            WHERE team_id = $1
            ORDER BY profit DESC
        """, team_id)
        return [dict(r) for r in rows]
    
    async def _load_temporal(self, conn, team_id: int) -> Dict:
        """Charge les patterns temporels"""
        row = await conn.fetchrow("""
            SELECT 
                diesel_factor, clutch_factor, sprinter_factor,
                best_scoring_period, worst_defensive_period,
                first_half_xg, second_half_xg,
                periods_data
            FROM quantum.temporal_patterns
            WHERE team_id = $1
        """, team_id)
        return dict(row) if row else {}
    
    async def _load_friction(self, home: str, away: str) -> Dict:
        """Charge la friction pré-calculée"""
        if self.db_pool is None:
            return self._get_simulated_friction(home, away)
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT 
                    kinetic_friction_home, kinetic_friction_away,
                    temporal_clash, psyche_dominance, physical_edge,
                    friction_score, chaos_potential,
                    style_clash, tempo_clash, mental_clash,
                    predicted_goals, predicted_winner
                FROM quantum.matchup_friction
                WHERE (LOWER(home_team) = LOWER($1) AND LOWER(away_team) = LOWER($2))
                   OR (LOWER(home_team) LIKE LOWER($3) AND LOWER(away_team) LIKE LOWER($4))
            """, home, away, f"%{home}%", f"%{away}%")
            
            return dict(row) if row else self._get_default_friction()
    
    def _build_complete_dna(self, row: Dict, quantum_dna: Dict, 
                            strategies: List[Dict], temporal: Dict) -> Dict[str, Any]:
        """Construit le DNA complet à partir des données"""
        
        return {
            # Identifiants
            "team_id": row['team_id'],
            "team_name": row['team_name'],
            "league": row['league'],
            
            # Vecteur 1: Context DNA (xG 2024)
            "context_dna": {
                "xg_for": quantum_dna.get('xg_for', 1.5),
                "xg_against": quantum_dna.get('xg_against', 1.3),
                "xg_diff": quantum_dna.get('xg_diff', 0.2),
                "style": quantum_dna.get('style', 'BALANCED'),
                "shots_per_match": quantum_dna.get('shots', 12),
                "possession": quantum_dna.get('possession', 50),
            },
            
            # Vecteur 2: Current Season (xG 2025/2026)
            "current_season": {
                "xg_for": quantum_dna.get('current_xg_for', 1.5),
                "xg_against": quantum_dna.get('current_xg_against', 1.3),
                "points": quantum_dna.get('points', 0),
                "ppg": quantum_dna.get('ppg', 1.5),
                "position": quantum_dna.get('position', 10),
                "form": quantum_dna.get('form', 'NEUTRAL'),
            },
            
            # Vecteur 3: Psyche DNA
            "psyche_dna": {
                "killer_instinct": quantum_dna.get('killer_instinct', 1.0),
                "killer_instinct_category": quantum_dna.get('killer_instinct_category', 'MEDIUM'),
                "mentality": quantum_dna.get('mentality_profile', 'BALANCED'),
                "panic_factor": quantum_dna.get('panic_factor', 0.5),
                "resilience_index": quantum_dna.get('resilience', 50),
                "collapse_rate": quantum_dna.get('collapse_rate', 0.2),
            },
            
            # Vecteur 4: Nemesis DNA
            "nemesis_dna": {
                "verticality": quantum_dna.get('verticality', 50),
                "keeper_status": quantum_dna.get('keeper_status', 'AVERAGE'),
                "keeper_overperf": quantum_dna.get('keeper_overperf', 0),
                "dominance_style": quantum_dna.get('dominance_style', 'BALANCED'),
                "pressing_intensity": quantum_dna.get('ppda', 10),
            },
            
            # Vecteur 5: Temporal DNA
            "temporal_dna": {
                "diesel_factor": temporal.get('diesel_factor', quantum_dna.get('diesel_factor', 0.5)),
                "clutch_factor": temporal.get('clutch_factor', 0.5),
                "sprinter_factor": temporal.get('sprinter_factor', 0.5),
                "best_scoring_period": temporal.get('best_scoring_period', '75-90'),
                "first_half_xg": temporal.get('first_half_xg', 0.7),
                "second_half_xg": temporal.get('second_half_xg', 0.8),
                "late_game_threat": quantum_dna.get('late_game_threat', 'MEDIUM'),
            },
            
            # Vecteur 6: Tactical DNA (dans quantum_dna)
            "tactical_dna": {
                "formation": quantum_dna.get('formation', '4-3-3'),
                "set_piece_threat": quantum_dna.get('set_piece_threat', 0.5),
                "box_ratio": quantum_dna.get('box_ratio', 0.3),
                "deep_completion": quantum_dna.get('deep_completion', 5),
                "build_up_speed": quantum_dna.get('build_up_speed', 'MEDIUM'),
            },
            
            # Vecteur 7: Roster DNA
            "roster_dna": {
                "mvp_name": quantum_dna.get('mvp_name'),
                "mvp_dependency": quantum_dna.get('mvp_dependency', 0.3),
                "playmaker": quantum_dna.get('playmaker'),
                "clinical_finisher": quantum_dna.get('clinical', 'AVERAGE'),
                "bench_impact": quantum_dna.get('bench_impact', 5),
            },
            
            # Vecteur 8: Physical DNA
            "physical_dna": {
                "stamina": quantum_dna.get('stamina', 70),
                "pressing_decay": quantum_dna.get('pressing_decay', 0.2),
                "rotation_score": quantum_dna.get('rotation', 50),
                "late_game_stamina": quantum_dna.get('late_stamina', 60),
            },
            
            # Vecteur 9: Market DNA
            "market_dna": {
                "best_strategy": row.get('best_strategy', 'UNKNOWN'),
                "best_strategy_roi": row.get('best_strategy_roi', 0),
                "best_strategy_wr": row.get('best_strategy_wr', 0),
                "empirical_profile": quantum_dna.get('empirical_profile', 'STANDARD'),
                "strategies": strategies[:5],  # Top 5 stratégies
            },
            
            # Vecteur 10: Luck DNA
            "luck_dna": {
                "xpoints": quantum_dna.get('xpoints', 0),
                "actual_points": quantum_dna.get('points', 0),
                "xpoints_delta": quantum_dna.get('xpoints_delta', 0),
                "luck_profile": quantum_dna.get('luck_profile', 'NEUTRAL'),
                "regression_direction": self._calc_regression_direction(quantum_dna),
            },
            
            # Vecteur 11: Chameleon DNA
            "chameleon_dna": {
                "comeback_ability": quantum_dna.get('comeback_ability', 50),
                "adaptability": quantum_dna.get('adaptability', 50),
                "tactical_flexibility": quantum_dna.get('flexibility', 50),
                "formations_used": quantum_dna.get('formations_used', 2),
            },
            
            # Métadonnées
            "updated_at": row.get('updated_at', datetime.now()),
            "data_quality": self._assess_data_quality(quantum_dna),
        }
    
    def _calc_regression_direction(self, dna: Dict) -> str:
        """Calcule la direction de régression attendue"""
        delta = dna.get('xpoints_delta', 0)
        if delta > 3:
            return "UP"  # Malchanceux, va remonter
        elif delta < -3:
            return "DOWN"  # Chanceux, va descendre
        return "STABLE"
    
    def _assess_data_quality(self, dna: Dict) -> float:
        """Évalue la qualité des données (0-100)"""
        required_fields = ['xg_for', 'xg_against', 'killer_instinct', 'diesel_factor']
        present = sum(1 for f in required_fields if f in dna and dna[f] is not None)
        return (present / len(required_fields)) * 100
    
    def _normalize_team_name(self, name: str) -> str:
        """Normalise le nom d'équipe"""
        return name.strip().lower()
    
    def _get_simulated_dna(self, team_name: str) -> Dict[str, Any]:
        """DNA simulé pour tests (sans DB)"""
        import random
        
        return {
            "team_id": hash(team_name) % 1000,
            "team_name": team_name,
            "league": "Simulation",
            "context_dna": {
                "xg_for": round(random.uniform(1.0, 2.5), 2),
                "xg_against": round(random.uniform(0.8, 2.0), 2),
                "style": random.choice(["ATTACKING", "DEFENSIVE", "BALANCED"]),
                "possession": random.randint(40, 65),
            },
            "current_season": {
                "xg_for": round(random.uniform(1.0, 2.5), 2),
                "points": random.randint(10, 40),
                "ppg": round(random.uniform(1.0, 2.5), 2),
                "position": random.randint(1, 20),
            },
            "psyche_dna": {
                "killer_instinct": round(random.uniform(0.5, 2.0), 2),
                "mentality": random.choice(["CONSERVATIVE", "BALANCED", "AGGRESSIVE"]),
                "collapse_rate": round(random.uniform(0.1, 0.4), 2),
                "resilience_index": random.randint(40, 80),
            },
            "nemesis_dna": {
                "verticality": random.randint(30, 80),
                "keeper_status": random.choice(["ELITE", "SOLID", "AVERAGE", "LEAKY"]),
                "pressing_intensity": round(random.uniform(6, 14), 1),
            },
            "temporal_dna": {
                "diesel_factor": round(random.uniform(0.3, 0.9), 2),
                "clutch_factor": round(random.uniform(0.3, 0.9), 2),
                "sprinter_factor": round(random.uniform(0.3, 0.9), 2),
                "best_scoring_period": random.choice(["0-15", "15-30", "60-75", "75-90"]),
            },
            "tactical_dna": {
                "formation": random.choice(["4-3-3", "4-4-2", "3-5-2", "4-2-3-1"]),
                "set_piece_threat": round(random.uniform(0.3, 0.8), 2),
            },
            "roster_dna": {
                "mvp_dependency": round(random.uniform(0.2, 0.6), 2),
                "bench_impact": round(random.uniform(3, 8), 1),
            },
            "physical_dna": {
                "pressing_decay": round(random.uniform(0.1, 0.4), 2),
                "stamina": random.randint(50, 85),
            },
            "market_dna": {
                "best_strategy": random.choice(["CONVERGENCE_OVER_MC", "QUANT_BEST_MARKET"]),
                "best_strategy_roi": round(random.uniform(-20, 100), 1),
            },
            "luck_dna": {
                "xpoints_delta": round(random.uniform(-5, 5), 1),
                "luck_profile": random.choice(["LUCKY", "NEUTRAL", "UNLUCKY"]),
                "regression_direction": random.choice(["UP", "STABLE", "DOWN"]),
            },
            "chameleon_dna": {
                "comeback_ability": random.randint(30, 80),
                "adaptability": random.randint(30, 80),
            },
            "data_quality": random.randint(60, 95),
        }
    
    def _get_simulated_friction(self, home: str, away: str) -> Dict:
        """Friction simulée pour tests"""
        import random
        return {
            "kinetic_friction_home": random.randint(30, 70),
            "kinetic_friction_away": random.randint(30, 70),
            "friction_score": random.randint(40, 80),
            "chaos_potential": random.randint(30, 90),
            "style_clash": random.randint(40, 80),
            "tempo_clash": random.randint(10, 40),
            "mental_clash": random.randint(40, 70),
            "predicted_goals": round(random.uniform(2.0, 3.5), 2),
        }
    
    def _get_default_dna(self, team_name: str) -> Dict[str, Any]:
        """DNA par défaut quand équipe non trouvée"""
        return {
            "team_name": team_name,
            "context_dna": {"xg_for": 1.3, "xg_against": 1.3},
            "psyche_dna": {"killer_instinct": 1.0, "mentality": "BALANCED"},
            "temporal_dna": {"diesel_factor": 0.5, "clutch_factor": 0.5},
            "data_quality": 0,
            "_warning": "Team not found in database",
        }
    
    def _get_default_friction(self) -> Dict:
        """Friction par défaut"""
        return {
            "friction_score": 50,
            "chaos_potential": 50,
            "predicted_goals": 2.5,
        }
    
    def clear_cache(self):
        """Vide le cache"""
        self._cache.clear()
        logger.info("Cache cleared")
