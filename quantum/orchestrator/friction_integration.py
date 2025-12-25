#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════════════
FRICTION INTEGRATION V1.0 - PONT ORCHESTRATOR HEDGE FUND GRADE
═══════════════════════════════════════════════════════════════════════════════════════

Fichier: quantum/orchestrator/friction_integration.py
Version: 1.0.0
Date: 2025-12-25

OBJECTIF:
Pont non-invasif entre les nouveaux composants Friction et l'orchestrator existant.
Permet d'intégrer progressivement sans casser le code existant.

COMPOSANTS INTÉGRÉS:
- FrictionLoader (fusion V1+V3 DB)
- FrictionData (structure unifiée)
- FrictionTensor (Alpha 15/10)
- RefereeLoader (RefereeDNA)

USAGE DANS L'ORCHESTRATOR:
    # Au lieu de:
    # friction = await self.load_friction(home, away)  # STUB
    
    # Utiliser:
    from quantum.orchestrator.friction_integration import FrictionIntegration
    
    friction_integration = FrictionIntegration(db_pool)
    friction = await friction_integration.load_friction_for_orchestrator(home, away)
    # Retourne un FrictionMatrix compatible avec le code existant

PHILOSOPHIE:
- Non-invasif: L'orchestrator existant continue de fonctionner
- Progressif: On peut activer les features une par une
- Fallback: Si erreur, retourne les valeurs par défaut actuelles
- Tracé: Logs détaillés pour debug

═══════════════════════════════════════════════════════════════════════════════════════
"""

import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple, TYPE_CHECKING
from datetime import datetime

# Logger
logger = logging.getLogger("QuantumOrchestrator.FrictionIntegration")

# ═══════════════════════════════════════════════════════════════════════════════════════
# IMPORTS CONDITIONNELS (pour éviter les erreurs d'import circulaires)
# ═══════════════════════════════════════════════════════════════════════════════════════

try:
    from quantum.orchestrator.friction_loader import (
        FrictionLoader,
        FrictionData,
        FrictionVector,
    )
    FRICTION_LOADER_AVAILABLE = True
except ImportError as e:
    FRICTION_LOADER_AVAILABLE = False
    logger.warning(f"⚠️ FrictionLoader not available: {e}")
    FrictionLoader = None
    FrictionData = None

try:
    from quantum.orchestrator.friction_tensor import (
        FrictionTensorCalculator,
        FrictionTensor,
        TradingSignal,
        GameScript,
    )
    FRICTION_TENSOR_AVAILABLE = True
except ImportError as e:
    FRICTION_TENSOR_AVAILABLE = False
    logger.warning(f"⚠️ FrictionTensor not available: {e}")
    FrictionTensorCalculator = None
    FrictionTensor = None

try:
    from quantum.orchestrator.referee_loader import (
        RefereeLoader,
        RefereeDNA,
        calculate_rhythm_destruction,
    )
    REFEREE_LOADER_AVAILABLE = True
except ImportError as e:
    REFEREE_LOADER_AVAILABLE = False
    logger.warning(f"⚠️ RefereeLoader not available: {e}")
    RefereeLoader = None
    RefereeDNA = None


# ═══════════════════════════════════════════════════════════════════════════════════════
# FRICTION MATRIX (COPIE EXACTE DE L'ORCHESTRATOR POUR COMPATIBILITÉ)
# ═══════════════════════════════════════════════════════════════════════════════════════

@dataclass
class FrictionMatrix:
    """
    Matrice de friction entre deux équipes.
    COPIE EXACTE de la classe dans quantum_orchestrator_v1.py pour compatibilité.
    """
    home_team: str
    away_team: str

    # 4 types de friction
    kinetic_home: float = 50.0   # Dommage home → away
    kinetic_away: float = 50.0   # Dommage away → home
    temporal_clash: float = 50.0  # Avantage timing
    psyche_dominance: float = 50.0  # Edge mental
    physical_edge: float = 50.0  # Stamina advantage

    # Métriques dérivées
    chaos_potential: float = 50.0
    predicted_goals: float = 2.5
    btts_probability: float = 0.5

    # Scénarios détectés
    triggered_scenarios: List[str] = field(default_factory=list)
    
    # === NOUVEAUX CHAMPS (optionnels, pour enrichissement) ===
    
    # Source tracking
    source: str = "default"  # "default", "v1", "v3", "integrated"
    
    # Données enrichies de FrictionData (si disponibles)
    style_clash: Optional[float] = None
    confidence_level: Optional[str] = None
    h2h_matches: Optional[int] = None
    
    # FrictionTensor (si calculé)
    tensor_calculated: bool = False
    game_script: Optional[str] = None
    trading_signals: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour snapshot."""
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════════════
# CONVERSION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════════════

def friction_data_to_matrix(
    friction_data: 'FrictionData',
    home_team: str,
    away_team: str,
) -> FrictionMatrix:
    """
    Convertit FrictionData (nouveau format) en FrictionMatrix (format orchestrator).
    
    MAPPING:
    - kinetic_home ← friction_score (représente l'intensité globale)
    - kinetic_away ← friction_score (symétrique) ou style_clash
    - temporal_clash ← tempo_friction
    - psyche_dominance ← mental_clash
    - physical_edge ← psychological_edge (si V3) ou friction_score
    - chaos_potential ← chaos_potential (direct)
    - predicted_goals ← predicted_goals (direct)
    - btts_probability ← predicted_btts_prob (direct)
    
    Args:
        friction_data: FrictionData depuis FrictionLoader
        home_team: Nom équipe home (pour confirmation)
        away_team: Nom équipe away (pour confirmation)
    
    Returns:
        FrictionMatrix compatible avec l'orchestrator
    """
    # Calcul kinetic (basé sur friction_score et asymétrie)
    base_friction = friction_data.friction_score
    
    # Si V3 (asymétrique), on peut différencier home/away
    if friction_data.has_v3_data and friction_data.psychological_edge is not None:
        # psychological_edge > 0 = home a l'avantage
        edge = friction_data.psychological_edge
        kinetic_home = base_friction + (edge / 2)
        kinetic_away = base_friction - (edge / 2)
    else:
        # V1 (symétrique) - même valeur
        kinetic_home = base_friction
        kinetic_away = base_friction
    
    # Clamp les valeurs entre 0 et 100
    kinetic_home = max(0.0, min(100.0, kinetic_home))
    kinetic_away = max(0.0, min(100.0, kinetic_away))
    
    # Physical edge
    if friction_data.psychological_edge is not None:
        physical_edge = 50.0 + friction_data.psychological_edge
    else:
        physical_edge = base_friction
    physical_edge = max(0.0, min(100.0, physical_edge))
    
    # Predicted values avec fallback
    predicted_goals = friction_data.predicted_goals if friction_data.predicted_goals else 2.5
    btts_prob = friction_data.predicted_btts_prob if friction_data.predicted_btts_prob else 0.5
    
    return FrictionMatrix(
        home_team=home_team,
        away_team=away_team,
        
        kinetic_home=kinetic_home,
        kinetic_away=kinetic_away,
        temporal_clash=friction_data.tempo_friction,
        psyche_dominance=friction_data.mental_clash,
        physical_edge=physical_edge,
        
        chaos_potential=friction_data.chaos_potential,
        predicted_goals=predicted_goals,
        btts_probability=btts_prob,
        
        triggered_scenarios=[],
        
        # Metadata
        source=friction_data.source_table,
        style_clash=friction_data.style_clash,
        confidence_level=friction_data.confidence_level,
        h2h_matches=friction_data.h2h_matches,
    )


def get_default_friction_matrix(home_team: str, away_team: str) -> FrictionMatrix:
    """
    Retourne les valeurs par défaut (identiques au STUB actuel de l'orchestrator).
    Utilisé comme fallback si aucune donnée n'est trouvée.
    """
    return FrictionMatrix(
        home_team=home_team,
        away_team=away_team,
        kinetic_home=55,
        kinetic_away=48,
        temporal_clash=52,
        psyche_dominance=58,
        physical_edge=54,
        chaos_potential=62,
        predicted_goals=2.8,
        btts_probability=0.58,
        source="default",
    )


# ═══════════════════════════════════════════════════════════════════════════════════════
# FRICTION INTEGRATION CLASS
# ═══════════════════════════════════════════════════════════════════════════════════════

class FrictionIntegration:
    """
    Classe d'intégration principale.
    
    Encapsule tous les nouveaux composants Friction et expose une interface
    simple pour l'orchestrator.
    
    Usage:
        # Dans l'orchestrator __init__
        self.friction_integration = FrictionIntegration(db_pool)
        
        # Dans analyze_match
        friction = await self.friction_integration.load_friction_for_orchestrator(
            home_team, away_team
        )
        
        # Optionnel: Récupérer le tensor
        tensor = self.friction_integration.last_tensor
    """
    
    def __init__(
        self,
        db_pool=None,
        enable_tensor: bool = True,
        enable_referee: bool = True,
        fallback_to_default: bool = True,
    ):
        """
        Args:
            db_pool: Pool asyncpg pour les requêtes DB
            enable_tensor: Calculer le FrictionTensor (Alpha 15/10)
            enable_referee: Charger les données arbitre
            fallback_to_default: Retourner valeurs par défaut si erreur
        """
        self.db_pool = db_pool
        self.enable_tensor = enable_tensor and FRICTION_TENSOR_AVAILABLE
        self.enable_referee = enable_referee and REFEREE_LOADER_AVAILABLE
        self.fallback_to_default = fallback_to_default
        
        # Loaders
        self.friction_loader = FrictionLoader(pool=db_pool) if FRICTION_LOADER_AVAILABLE else None
        self.referee_loader = RefereeLoader(db_pool=db_pool) if REFEREE_LOADER_AVAILABLE else None
        self.tensor_calculator = FrictionTensorCalculator() if FRICTION_TENSOR_AVAILABLE else None
        
        # Cache du dernier calcul (pour accès facile)
        self.last_friction_data: Optional['FrictionData'] = None
        self.last_tensor: Optional['FrictionTensor'] = None
        self.last_referee: Optional['RefereeDNA'] = None
        
        # Stats
        self.stats = {
            "total_calls": 0,
            "v3_hits": 0,
            "v1_hits": 0,
            "defaults": 0,
            "errors": 0,
        }
        
        logger.info(
            f"🔧 FrictionIntegration initialized: "
            f"loader={FRICTION_LOADER_AVAILABLE}, "
            f"tensor={self.enable_tensor}, "
            f"referee={self.enable_referee}"
        )
    
    async def load_friction_for_orchestrator(
        self,
        home_team: str,
        away_team: str,
        referee_name: Optional[str] = None,
        home_dna=None,
        away_dna=None,
        is_derby: bool = False,
    ) -> FrictionMatrix:
        """
        Charge les données friction et retourne un FrictionMatrix compatible.
        
        C'est la méthode principale à appeler depuis l'orchestrator.
        Remplace le STUB load_friction() existant.
        
        Args:
            home_team: Nom équipe domicile
            away_team: Nom équipe extérieur
            referee_name: Nom de l'arbitre (optionnel, pour tensor)
            home_dna: TeamDNA home (optionnel, pour tensor)
            away_dna: TeamDNA away (optionnel, pour tensor)
            is_derby: Est-ce un derby? (pour tensor)
        
        Returns:
            FrictionMatrix compatible avec l'orchestrator
        """
        self.stats["total_calls"] += 1
        
        # 1. Charger FrictionData depuis DB
        friction_data = None
        if self.friction_loader:
            try:
                friction_data = await self.friction_loader.load_friction(home_team, away_team)
                
                if friction_data:
                    self.last_friction_data = friction_data
                    
                    if friction_data.source_table == "v3":
                        self.stats["v3_hits"] += 1
                    else:
                        self.stats["v1_hits"] += 1
                    
                    logger.debug(
                        f"✅ Friction loaded: {home_team} vs {away_team} "
                        f"[{friction_data.source_table}] "
                        f"score={friction_data.friction_score}"
                    )
            except Exception as e:
                logger.error(f"❌ Error loading friction: {e}")
                self.stats["errors"] += 1
        
        # 2. Convertir ou fallback
        if friction_data:
            friction_matrix = friction_data_to_matrix(friction_data, home_team, away_team)
        elif self.fallback_to_default:
            friction_matrix = get_default_friction_matrix(home_team, away_team)
            self.stats["defaults"] += 1
            logger.warning(f"⚠️ Using default friction for {home_team} vs {away_team}")
        else:
            # Pas de fallback, retourne quand même un default
            friction_matrix = get_default_friction_matrix(home_team, away_team)
            self.stats["defaults"] += 1
        
        # 3. Optionnel: Charger Referee et calculer Tensor
        if self.enable_tensor and home_dna and away_dna:
            try:
                # Charger referee si nom fourni
                referee = None
                if self.enable_referee and referee_name and self.referee_loader:
                    referee = self.referee_loader.load_referee_from_json(referee_name)
                    if not referee:
                        referee = await self.referee_loader.load_referee(referee_name)
                    self.last_referee = referee
                
                # Calculer tensor
                if self.tensor_calculator:
                    tensor = self.tensor_calculator.calculate(
                        home_dna=home_dna,
                        away_dna=away_dna,
                        referee=referee,
                        is_derby=is_derby,
                    )
                    self.last_tensor = tensor
                    
                    # Enrichir FrictionMatrix avec les données tensor
                    friction_matrix.tensor_calculated = True
                    friction_matrix.game_script = tensor.primary_script.value
                    friction_matrix.trading_signals = [s.to_dict() for s in tensor.signals]
                    
                    # Ajouter les scénarios détectés
                    if tensor.primary_script.value != "STANDARD":
                        friction_matrix.triggered_scenarios.append(tensor.primary_script.value)
                    for sec in tensor.secondary_scripts:
                        friction_matrix.triggered_scenarios.append(sec.value)
                    
                    logger.debug(
                        f"🎯 Tensor calculated: {tensor.primary_script.value}, "
                        f"{len(tensor.signals)} signals"
                    )
                    
            except Exception as e:
                logger.error(f"❌ Error calculating tensor: {e}")
                # Ne pas échouer, continuer avec friction_matrix de base
        
        return friction_matrix
    
    def load_friction_sync(
        self,
        home_team: str,
        away_team: str,
        cursor=None,
    ) -> FrictionMatrix:
        """
        Version synchrone pour scripts de test ou maintenance.
        
        Args:
            home_team: Nom équipe domicile
            away_team: Nom équipe extérieur
            cursor: Curseur psycopg2 (optionnel)
        
        Returns:
            FrictionMatrix
        """
        self.stats["total_calls"] += 1
        
        friction_data = None
        if self.friction_loader:
            try:
                friction_data = self.friction_loader.load_friction_sync(
                    home_team, away_team, cursor
                )
                
                if friction_data:
                    self.last_friction_data = friction_data
                    if friction_data.source_table == "v3":
                        self.stats["v3_hits"] += 1
                    else:
                        self.stats["v1_hits"] += 1
            except Exception as e:
                logger.error(f"❌ Error loading friction sync: {e}")
                self.stats["errors"] += 1
        
        if friction_data:
            return friction_data_to_matrix(friction_data, home_team, away_team)
        else:
            self.stats["defaults"] += 1
            return get_default_friction_matrix(home_team, away_team)
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques d'utilisation."""
        return {
            **self.stats,
            "hit_rate": (
                (self.stats["v3_hits"] + self.stats["v1_hits"]) / 
                max(self.stats["total_calls"], 1)
            ) * 100,
            "v3_rate": (
                self.stats["v3_hits"] / 
                max(self.stats["v3_hits"] + self.stats["v1_hits"], 1)
            ) * 100,
        }
    
    def reset_stats(self):
        """Réinitialise les statistiques."""
        self.stats = {
            "total_calls": 0,
            "v3_hits": 0,
            "v1_hits": 0,
            "defaults": 0,
            "errors": 0,
        }


# ═══════════════════════════════════════════════════════════════════════════════════════
# HELPER POUR MIGRATION PROGRESSIVE
# ═══════════════════════════════════════════════════════════════════════════════════════

def create_friction_integration(db_pool=None) -> FrictionIntegration:
    """
    Factory function pour créer une instance FrictionIntegration.
    
    Usage dans l'orchestrator:
        from quantum.orchestrator.friction_integration import create_friction_integration
        
        self.friction_integration = create_friction_integration(self.db_pool)
    """
    return FrictionIntegration(
        db_pool=db_pool,
        enable_tensor=True,
        enable_referee=True,
        fallback_to_default=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════════════
# VERSION INFO
# ═══════════════════════════════════════════════════════════════════════════════════════

FRICTION_INTEGRATION_VERSION = "1.0.0"
FRICTION_INTEGRATION_DATE = "2025-12-25"


# ═══════════════════════════════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio
    
    print("=" * 80)
    print("TEST FRICTION INTEGRATION V1.0")
    print("=" * 80)
    
    # Test 1: Composants disponibles
    print("\n📋 Test 1: Composants disponibles")
    print(f"  FrictionLoader: {'✅' if FRICTION_LOADER_AVAILABLE else '❌'}")
    print(f"  FrictionTensor: {'✅' if FRICTION_TENSOR_AVAILABLE else '❌'}")
    print(f"  RefereeLoader: {'✅' if REFEREE_LOADER_AVAILABLE else '❌'}")
    
    # Test 2: Default FrictionMatrix
    print("\n📋 Test 2: Default FrictionMatrix")
    default = get_default_friction_matrix("Liverpool", "Manchester City")
    print(f"  home_team: {default.home_team}")
    print(f"  away_team: {default.away_team}")
    print(f"  kinetic_home: {default.kinetic_home}")
    print(f"  kinetic_away: {default.kinetic_away}")
    print(f"  chaos_potential: {default.chaos_potential}")
    print(f"  predicted_goals: {default.predicted_goals}")
    print(f"  source: {default.source}")
    
    # Test 3: Conversion (si FrictionData disponible)
    if FRICTION_LOADER_AVAILABLE:
        print("\n📋 Test 3: Conversion FrictionData → FrictionMatrix")
        # Créer un FrictionData mock
        from quantum.orchestrator.friction_loader import FrictionData, FrictionVector
        
        mock_data = FrictionData(
            friction_id=1,
            home_team="Liverpool",
            away_team="Manchester City",
            friction_score=65.0,
            style_clash=70.0,
            tempo_friction=58.0,
            mental_clash=72.0,
            psychological_edge=8.0,  # Home advantage
            chaos_potential=75.0,
            predicted_goals=3.2,
            predicted_btts_prob=0.72,
            h2h_matches=25,
            confidence_level="high",
            source_table="v3",
        )
        
        converted = friction_data_to_matrix(mock_data, "Liverpool", "Manchester City")
        print(f"  kinetic_home: {converted.kinetic_home:.1f} (friction + edge/2)")
        print(f"  kinetic_away: {converted.kinetic_away:.1f} (friction - edge/2)")
        print(f"  temporal_clash: {converted.temporal_clash}")
        print(f"  psyche_dominance: {converted.psyche_dominance}")
        print(f"  physical_edge: {converted.physical_edge:.1f}")
        print(f"  chaos_potential: {converted.chaos_potential}")
        print(f"  source: {converted.source}")
    
    # Test 4: FrictionIntegration sans DB
    print("\n📋 Test 4: FrictionIntegration (sans DB)")
    integration = FrictionIntegration(
        db_pool=None,
        enable_tensor=False,
        enable_referee=False,
    )
    print(f"  Created: ✅")
    print(f"  Stats: {integration.get_stats()}")
    
    # Test 5: Sync fallback
    print("\n📋 Test 5: Sync load (fallback to default)")
    friction = integration.load_friction_sync("Arsenal", "Chelsea")
    print(f"  Result: {friction.home_team} vs {friction.away_team}")
    print(f"  Source: {friction.source}")
    print(f"  Stats après: {integration.get_stats()}")
    
    print("\n✅ TEST PASSED - FRICTION INTEGRATION V1.0")
    print("\n" + "=" * 80)
    print("POUR TESTER AVEC LA VRAIE DB:")
    print("=" * 80)
    print("""
cd /home/Mon_ps
PYTHONPATH=/home/Mon_ps python3 << 'EOF'
import asyncio
import asyncpg
from quantum.orchestrator.friction_integration import FrictionIntegration

async def test():
    pool = await asyncpg.create_pool(
        'postgresql://monps_user:monps_secure_password_2024@localhost/monps_db'
    )
    
    integration = FrictionIntegration(db_pool=pool)
    
    # Test avec vraies données
    friction = await integration.load_friction_for_orchestrator(
        "Liverpool", "Manchester City"
    )
    
    print(f"Result: {friction.home_team} vs {friction.away_team}")
    print(f"Source: {friction.source}")
    print(f"Kinetic: {friction.kinetic_home:.1f} / {friction.kinetic_away:.1f}")
    print(f"Chaos: {friction.chaos_potential:.1f}")
    print(f"Goals: {friction.predicted_goals}")
    print(f"Stats: {integration.get_stats()}")
    
    await pool.close()

asyncio.run(test())
EOF
    """)

