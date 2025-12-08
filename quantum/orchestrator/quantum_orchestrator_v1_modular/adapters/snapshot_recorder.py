"""
╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                    SNAPSHOT RECORDER - Boîte Noire pour Audit                         ║
╠═══════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                       ║
║  Responsabilités:                                                                     ║
║  • Sauvegarder chaque décision de pari (quantum.bet_snapshots)                       ║
║  • Enregistrer les votes de chaque modèle (quantum.model_votes)                      ║
║  • Permettre le replay/debug des décisions passées                                   ║
║  • Tracker la performance de chaque modèle                                           ║
║                                                                                       ║
║  "La confiance sans audit = arrogance"                                               ║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝
"""

import asyncpg
import json
import uuid
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

import sys
sys.path.insert(0, '/home/Mon_ps/quantum/orchestrator')
from config.settings import DB_CONFIG, TABLES

logger = logging.getLogger("SnapshotRecorder")


# ═══════════════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class ModelVoteRecord:
    """Enregistrement d'un vote de modèle"""
    model_name: str
    signal: str                     # STRONG_BUY, BUY, HOLD, SELL, SKIP
    confidence: float               # 0-100
    reasoning: str
    market: str = ""
    probability: float = 0.0
    weight: float = 1.0
    raw_data: Dict = field(default_factory=dict)
    
    @property
    def is_positive(self) -> bool:
        return self.signal in ["STRONG_BUY", "BUY"]


@dataclass
class BetSnapshotRecord:
    """
    Enregistrement complet d'une décision de pari.
    
    Permet de recréer l'état exact au moment de la décision pour:
    - Debug (comprendre pourquoi un pari a été pris/rejeté)
    - Audit (vérifier les décisions passées)
    - Amélioration (analyser les patterns gagnants/perdants)
    """
    
    # Identifiants
    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    match_id: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    
    # Équipes
    home_team: str = ""
    away_team: str = ""
    
    # DNA au moment T (snapshot complet)
    home_dna_snapshot: Dict = field(default_factory=dict)
    away_dna_snapshot: Dict = field(default_factory=dict)
    
    # Friction au moment T
    friction_snapshot: Dict = field(default_factory=dict)
    
    # Cotes au moment T
    odds_snapshot: Dict = field(default_factory=dict)
    
    # Votes des 6 modèles
    model_votes: List[ModelVoteRecord] = field(default_factory=list)
    
    # Consensus
    consensus_score: float = 0.0        # 0-100%
    consensus_count: int = 0            # X/6 modèles positifs
    conviction: str = "WEAK"            # MAXIMUM, STRONG, MODERATE, WEAK
    
    # Validation
    monte_carlo_score: float = 0.0
    monte_carlo_robustness: str = "FRAGILE"
    clv_estimate: float = 0.0
    clv_signal: str = "NO_SIGNAL"
    
    # Décision finale
    decision: str = "SKIP"              # BET ou SKIP
    market: str = ""
    odds: float = 0.0
    probability: float = 0.0
    edge: float = 0.0
    stake: float = 0.0
    expected_value: float = 0.0
    
    # Résultat (rempli après le match)
    actual_result: str = ""             # WIN, LOSS, PUSH, VOID
    profit_loss: float = 0.0
    settled_at: datetime = None
    
    def to_json(self) -> str:
        """Sérialise en JSON pour stockage"""
        data = {
            'snapshot_id': self.snapshot_id,
            'match_id': self.match_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'home_team': self.home_team,
            'away_team': self.away_team,
            'home_dna_snapshot': self.home_dna_snapshot,
            'away_dna_snapshot': self.away_dna_snapshot,
            'friction_snapshot': self.friction_snapshot,
            'odds_snapshot': self.odds_snapshot,
            'model_votes': [
                {
                    'model_name': v.model_name,
                    'signal': v.signal,
                    'confidence': v.confidence,
                    'reasoning': v.reasoning,
                    'market': v.market,
                    'probability': v.probability,
                    'weight': v.weight,
                    'raw_data': v.raw_data
                }
                for v in self.model_votes
            ],
            'consensus_score': self.consensus_score,
            'consensus_count': self.consensus_count,
            'conviction': self.conviction,
            'monte_carlo_score': self.monte_carlo_score,
            'monte_carlo_robustness': self.monte_carlo_robustness,
            'clv_estimate': self.clv_estimate,
            'clv_signal': self.clv_signal,
            'decision': self.decision,
            'market': self.market,
            'odds': self.odds,
            'probability': self.probability,
            'edge': self.edge,
            'stake': self.stake,
            'expected_value': self.expected_value,
            'actual_result': self.actual_result,
            'profit_loss': self.profit_loss,
            'settled_at': self.settled_at.isoformat() if self.settled_at else None
        }
        return json.dumps(data, default=str)


@dataclass
class ModelPerformanceRecord:
    """Performance d'un modèle sur une période"""
    model_name: str
    period_start: datetime
    period_end: datetime
    total_votes: int = 0
    correct_votes: int = 0
    accuracy: float = 0.0
    profit_loss: float = 0.0
    roi: float = 0.0
    accuracy_with_consensus: float = 0.0
    accuracy_against_consensus: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════════════
# SNAPSHOT RECORDER
# ═══════════════════════════════════════════════════════════════════════════════════════

class SnapshotRecorder:
    """
    Enregistreur de snapshots pour le Quantum Orchestrator.
    
    Sauvegarde chaque décision avec tout le contexte nécessaire
    pour reproduire et auditer les décisions.
    """
    
    def __init__(self, pool: asyncpg.Pool = None):
        self.pool = pool
    
    def set_pool(self, pool: asyncpg.Pool):
        """Configure le pool de connexions"""
        self.pool = pool
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # SNAPSHOT SAVING
    # ═══════════════════════════════════════════════════════════════════════════════
    
    async def save_snapshot(self, snapshot: BetSnapshotRecord) -> bool:
        """
        Sauvegarde un snapshot complet de décision.
        
        Table: quantum.bet_snapshots
        Structure: snapshot_id, match_id, home_team, away_team, snapshot_data, 
                   model_votes (JSONB), model_weights (JSONB), consensus_score, 
                   consensus_count, conviction, odds_snapshot, final_market, 
                   final_odds, final_stake, final_probability, final_edge, expected_value
        """
        if not self.pool:
            logger.warning("⚠️ SnapshotRecorder: pool non configuré")
            return False
        
        # Préparer model_votes en JSONB
        model_votes_json = json.dumps([
            {
                'model_name': v.model_name,
                'signal': v.signal,
                'confidence': v.confidence,
                'reasoning': v.reasoning,
                'market': v.market,
                'probability': v.probability
            }
            for v in snapshot.model_votes
        ])
        
        # Préparer model_weights (poids par défaut)
        model_weights_json = json.dumps({
            'team_strategy': 1.25,
            'quantum_scorer': 1.15,
            'matchup_scorer': 1.10,
            'dixon_coles': 1.00,
            'scenarios': 0.85,
            'dna_features': 1.05
        })
        
        query = f"""
            INSERT INTO {TABLES.BET_SNAPSHOTS} (
                snapshot_id, match_id, created_at,
                home_team, away_team,
                snapshot_data,
                home_dna, away_dna, friction_matrix,
                model_votes, model_weights,
                consensus_score, consensus_count, conviction,
                odds_snapshot,
                final_market, final_odds, final_stake,
                final_probability, final_edge, expected_value
            ) VALUES (
                $1, $2, $3,
                $4, $5,
                $6,
                $7, $8, $9,
                $10, $11,
                $12, $13, $14,
                $15,
                $16, $17, $18,
                $19, $20, $21
            )
            ON CONFLICT (snapshot_id) DO UPDATE SET
                snapshot_data = EXCLUDED.snapshot_data,
                model_votes = EXCLUDED.model_votes
        """
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    query,
                    uuid.UUID(snapshot.snapshot_id),
                    snapshot.match_id,
                    snapshot.created_at,
                    snapshot.home_team,
                    snapshot.away_team,
                    snapshot.to_json(),
                    json.dumps(snapshot.home_dna_snapshot),
                    json.dumps(snapshot.away_dna_snapshot),
                    json.dumps(snapshot.friction_snapshot),
                    model_votes_json,
                    model_weights_json,
                    snapshot.consensus_score / 100.0,  # Convertir en décimal 0-1
                    snapshot.consensus_count,
                    snapshot.conviction,
                    json.dumps(snapshot.odds_snapshot),
                    snapshot.market or 'none',
                    snapshot.odds or 1.0,
                    snapshot.stake or 0.0,
                    snapshot.probability or 0.5,
                    snapshot.edge or 0.0,
                    snapshot.expected_value or 0.0
                )
                
            logger.debug(f"💾 Snapshot sauvegardé: {snapshot.snapshot_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde snapshot: {e}")
            return False
    
    async def save_model_votes(
        self, 
        snapshot_id: str, 
        votes: List[ModelVoteRecord]
    ) -> bool:
        """
        Sauvegarde les votes individuels des modèles.
        
        Table: quantum.model_votes
        Structure: snapshot_id, model_name, signal, confidence, 
                   market_suggested, probability_estimate, reasoning,
                   raw_data, agreed_with_consensus, weight_used
        """
        if not self.pool:
            return False
        
        # Poids par modèle
        model_weights = {
            'team_strategy': 1.25,
            'quantum_scorer': 1.15,
            'matchup_scorer': 1.10,
            'dixon_coles': 1.00,
            'scenarios': 0.85,
            'dna_features': 1.05
        }
        
        query = f"""
            INSERT INTO {TABLES.MODEL_VOTES} (
                snapshot_id, model_name, signal, confidence,
                market_suggested, probability_estimate, reasoning,
                raw_data, agreed_with_consensus, weight_used
            ) VALUES (
                $1, $2, $3, $4,
                $5, $6, $7,
                $8, $9, $10
            )
        """
        
        try:
            async with self.pool.acquire() as conn:
                for vote in votes:
                    await conn.execute(
                        query,
                        uuid.UUID(snapshot_id),
                        vote.model_name,
                        vote.signal,
                        vote.confidence,
                        vote.market or None,
                        vote.probability or None,
                        vote.reasoning,
                        json.dumps(vote.raw_data, default=str) if vote.raw_data else None,
                        vote.is_positive,
                        model_weights.get(vote.model_name, 1.0)
                    )
            
            logger.debug(f"💾 {len(votes)} votes sauvegardés pour {snapshot_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde votes: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # RESULT SETTLEMENT
    # ═══════════════════════════════════════════════════════════════════════════════
    
    async def settle_bet(
        self, 
        snapshot_id: str, 
        result: str, 
        profit_loss: float
    ) -> bool:
        """
        Met à jour un snapshot avec le résultat réel.
        
        Args:
            snapshot_id: ID du snapshot
            result: WIN, LOSS, PUSH, VOID
            profit_loss: Profit/perte en unités
        """
        if not self.pool:
            return False
        
        query = f"""
            UPDATE {TABLES.BET_SNAPSHOTS}
            SET 
                result = $2,
                profit_loss = $3,
                settled_at = NOW()
            WHERE bet_id = $1
        """
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(query, uuid.UUID(snapshot_id), result, profit_loss)
            
            logger.info(f"✅ Bet settled: {snapshot_id} → {result} ({profit_loss:+.2f}u)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur settlement: {e}")
            return False
    
    async def update_model_votes_correctness(
        self, 
        snapshot_id: str, 
        actual_result: str
    ) -> bool:
        """
        Met à jour le champ was_correct pour chaque vote de modèle.
        
        Un vote est "correct" si:
        - Signal positif (BUY/STRONG_BUY) et résultat WIN
        - Signal négatif (SELL/SKIP) et résultat LOSS
        """
        if not self.pool:
            return False
        
        # Déterminer si les votes positifs étaient corrects
        positive_correct = actual_result == "WIN"
        
        query = f"""
            UPDATE {TABLES.MODEL_VOTES}
            SET was_correct = CASE
                WHEN signal IN ('STRONG_BUY', 'BUY') THEN $2
                WHEN signal IN ('SELL', 'STRONG_SELL', 'SKIP') THEN NOT $2
                ELSE NULL
            END
            WHERE bet_id = $1
        """
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(query, uuid.UUID(snapshot_id), positive_correct)
            return True
        except Exception as e:
            logger.error(f"❌ Erreur update votes: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # PERFORMANCE TRACKING
    # ═══════════════════════════════════════════════════════════════════════════════
    
    async def get_model_performance(
        self, 
        model_name: str,
        days_back: int = 30
    ) -> Optional[ModelPerformanceRecord]:
        """
        Calcule la performance d'un modèle sur les N derniers jours.
        """
        if not self.pool:
            return None
        
        query = f"""
            SELECT 
                COUNT(*) as total_votes,
                SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as correct_votes,
                ROUND(100.0 * SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) as accuracy
            FROM {TABLES.MODEL_VOTES}
            WHERE model_name = $1
              AND was_correct IS NOT NULL
              AND created_at > NOW() - INTERVAL '{days_back} days'
        """
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, model_name)
                
                if not row or row['total_votes'] == 0:
                    return None
                
                return ModelPerformanceRecord(
                    model_name=model_name,
                    period_start=datetime.now(),
                    period_end=datetime.now(),
                    total_votes=row['total_votes'] or 0,
                    correct_votes=row['correct_votes'] or 0,
                    accuracy=float(row['accuracy'] or 0)
                )
                
        except Exception as e:
            logger.error(f"❌ Erreur performance {model_name}: {e}")
            return None
    
    async def get_all_models_performance(
        self, 
        days_back: int = 30
    ) -> List[ModelPerformanceRecord]:
        """
        Calcule la performance de tous les modèles.
        """
        if not self.pool:
            return []
        
        query = f"""
            SELECT 
                model_name,
                COUNT(*) as total_votes,
                SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as correct_votes,
                ROUND(100.0 * SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) as accuracy
            FROM {TABLES.MODEL_VOTES}
            WHERE was_correct IS NOT NULL
              AND created_at > NOW() - INTERVAL '{days_back} days'
            GROUP BY model_name
            ORDER BY accuracy DESC
        """
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query)
                
                return [
                    ModelPerformanceRecord(
                        model_name=row['model_name'],
                        period_start=datetime.now(),
                        period_end=datetime.now(),
                        total_votes=row['total_votes'] or 0,
                        correct_votes=row['correct_votes'] or 0,
                        accuracy=float(row['accuracy'] or 0)
                    )
                    for row in rows
                ]
                
        except Exception as e:
            logger.error(f"❌ Erreur performance tous modèles: {e}")
            return []
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # SNAPSHOT RETRIEVAL (pour debug/audit)
    # ═══════════════════════════════════════════════════════════════════════════════
    
    async def get_snapshot(self, snapshot_id: str) -> Optional[Dict]:
        """Récupère un snapshot par ID"""
        if not self.pool:
            return None
        
        query = f"""
            SELECT snapshot_data
            FROM {TABLES.BET_SNAPSHOTS}
            WHERE bet_id = $1
        """
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, uuid.UUID(snapshot_id))
                
                if row and row['snapshot_data']:
                    return json.loads(row['snapshot_data'])
                return None
                
        except Exception as e:
            logger.error(f"❌ Erreur récupération snapshot: {e}")
            return None
    
    async def get_recent_snapshots(
        self, 
        limit: int = 20,
        decision_filter: str = None
    ) -> List[Dict]:
        """Récupère les snapshots récents"""
        if not self.pool:
            return []
        
        where_clause = ""
        if decision_filter:
            where_clause = f"WHERE decision = '{decision_filter}'"
        
        query = f"""
            SELECT 
                bet_id, match_id, home_team, away_team,
                market, stake, odds, decision, result, profit_loss,
                created_at
            FROM {TABLES.BET_SNAPSHOTS}
            {where_clause}
            ORDER BY created_at DESC
            LIMIT $1
        """
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, limit)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"❌ Erreur récupération snapshots: {e}")
            return []
    
    async def get_snapshots_for_match(
        self, 
        home_team: str, 
        away_team: str
    ) -> List[Dict]:
        """Récupère tous les snapshots pour un match donné"""
        if not self.pool:
            return []
        
        query = f"""
            SELECT snapshot_data, created_at, result, profit_loss
            FROM {TABLES.BET_SNAPSHOTS}
            WHERE LOWER(home_team) = LOWER($1)
              AND LOWER(away_team) = LOWER($2)
            ORDER BY created_at DESC
        """
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, home_team, away_team)
                
                results = []
                for row in rows:
                    data = json.loads(row['snapshot_data']) if row['snapshot_data'] else {}
                    data['result'] = row['result']
                    data['profit_loss'] = row['profit_loss']
                    results.append(data)
                
                return results
                
        except Exception as e:
            logger.error(f"❌ Erreur récupération snapshots match: {e}")
            return []


# ═══════════════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════════════

__all__ = [
    'SnapshotRecorder',
    'BetSnapshotRecord',
    'ModelVoteRecord',
    'ModelPerformanceRecord'
]
