"""
FORTRESS V3.8 - Configuration Centralisée
==========================================

Ce fichier centralise TOUS les chemins et configurations.
NE PAS modifier les chemins sans vérification préalable.

Version: 1.0.0
Date: 24 Décembre 2025
Auteur: Mya + Claude (Partenariat Quant)
"""

from pathlib import Path
from typing import Dict, Any
import os

# ═══════════════════════════════════════════════════════════════
# CHEMINS RACINE
# ═══════════════════════════════════════════════════════════════

PROJECT_ROOT = Path("/home/Mon_ps")
FORTRESS_ROOT = PROJECT_ROOT / "fortress_v38"

# ═══════════════════════════════════════════════════════════════
# COMPOSANTS SDK (Existants - NE PAS RECRÉER)
# ═══════════════════════════════════════════════════════════════

# Orchestrateurs
QUANTUM_ORCHESTRATOR_V1 = PROJECT_ROOT / "quantum/orchestrator/quantum_orchestrator_v1.py"
QUANTUM_ORCHESTRATOR_V2 = PROJECT_ROOT / "quantum_core/orchestrator/quantum_orchestrator_v2.py"

# Modèles Quantitatifs
FRICTION_MATRIX_12X12 = PROJECT_ROOT / "quantum/models/friction_matrix_12x12.py"
MARKET_REGISTRY = PROJECT_ROOT / "quantum/models/market_registry.py"

# Loaders
UNIFIED_LOADER = PROJECT_ROOT / "quantum/loaders/unified_loader.py"

# Chess Engines
CHESS_ENGINE_V2 = PROJECT_ROOT / "agents/chess_engine_v2/chess_engine_v2_complete.py"
CHESS_ENGINE_V25_CLASSIFIER = PROJECT_ROOT / "backend/quantum/chess_engine_v25/learning/profile_classifier.py"

# ═══════════════════════════════════════════════════════════════
# DONNÉES JSON
# ═══════════════════════════════════════════════════════════════

DATA_ROOT = PROJECT_ROOT / "data"
DATA_QUANTUM_V2 = DATA_ROOT / "quantum_v2"

# DNA Files
TEAM_DNA_UNIFIED = DATA_QUANTUM_V2 / "team_dna_unified_v2.json"
PLAYER_DNA_UNIFIED = DATA_QUANTUM_V2 / "player_dna_unified.json"
REFEREE_DNA_UNIFIED = DATA_QUANTUM_V2 / "referee_dna_unified.json"
MICROSTRATEGY_DNA = DATA_QUANTUM_V2 / "microstrategy_dna.json"

# Goalkeeper DNA
GOALKEEPER_DNA_DIR = DATA_ROOT / "goalkeeper_dna"
GOALKEEPER_DNA_V44 = GOALKEEPER_DNA_DIR / "goalkeeper_dna_v4_4_final.json"
GOALKEEPER_TIMING_DNA = GOALKEEPER_DNA_DIR / "goalkeeper_timing_dna_v1.json"

# Defense DNA
DEFENSE_DNA_DIR = DATA_ROOT / "defense_dna"
DEFENSE_DNA_V51 = DEFENSE_DNA_DIR / "team_defense_dna_v5_1_corrected.json"

# ═══════════════════════════════════════════════════════════════
# POSTGRESQL CONFIGURATION
# ═══════════════════════════════════════════════════════════════

POSTGRES_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "monps_db",
    "user": "monps_user",
    "password": "monps_secure_password_2024",
    "container_name": "monps_postgres"
}

# Connection string pour SQLAlchemy
POSTGRES_URI = (
    f"postgresql://{POSTGRES_CONFIG['user']}:{POSTGRES_CONFIG['password']}"
    f"@{POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['database']}"
)

# ═══════════════════════════════════════════════════════════════
# SCHÉMAS POSTGRESQL
# ═══════════════════════════════════════════════════════════════

POSTGRES_SCHEMAS = {
    "quantum": "quantum",      # Tables DNA, friction, strategies
    "public": "public",        # Tables intelligence, odds
}

# Tables critiques
POSTGRES_TABLES = {
    # Quantum schema
    "team_quantum_dna_v3": "quantum.team_quantum_dna_v3",
    "quantum_friction_matrix_v3": "quantum.quantum_friction_matrix_v3",
    "quantum_strategies_v3": "quantum.quantum_strategies_v3",
    
    # Public schema
    "team_intelligence": "public.team_intelligence",
    "coach_intelligence": "public.coach_intelligence",
    "scorer_intelligence": "public.scorer_intelligence",
    "odds_history": "public.odds_history",
    "team_market_profiles": "public.team_market_profiles",
}

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION FORTRESS
# ═══════════════════════════════════════════════════════════════

FORTRESS_CONFIG = {
    "version": "3.8.0",
    "mode": "SHADOW",  # SHADOW = dry run, LIVE = real bets
    "model_version": "v3.8",
    
    # Limites système
    "daily_budget_usd": 5.0,      # Budget Claude API
    "max_drawdown_pct": 5.0,      # Drawdown max avant stop
    "max_losing_streak": 3,       # Pertes consécutives avant pause
    "max_exposure_pct": 15.0,     # Exposure max portefeuille
    
    # Seuils de décision
    "min_convergence_score": 60,  # Score convergence minimum
    "min_edge_pct": 2.0,          # Edge minimum pour bet
    "min_liquidity_tier": 3,      # Tier liquidité minimum
    
    # Monte Carlo
    "monte_carlo_sims": 5000,     # Nombre simulations
    "noise_level": 0.15,          # Niveau bruit simulations
}

# ═══════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════

def verify_paths() -> Dict[str, bool]:
    """Vérifie que tous les chemins critiques existent."""
    paths_to_check = {
        "QUANTUM_ORCHESTRATOR_V1": QUANTUM_ORCHESTRATOR_V1,
        "QUANTUM_ORCHESTRATOR_V2": QUANTUM_ORCHESTRATOR_V2,
        "FRICTION_MATRIX_12X12": FRICTION_MATRIX_12X12,
        "MARKET_REGISTRY": MARKET_REGISTRY,
        "UNIFIED_LOADER": UNIFIED_LOADER,
        "CHESS_ENGINE_V2": CHESS_ENGINE_V2,
        "CHESS_ENGINE_V25_CLASSIFIER": CHESS_ENGINE_V25_CLASSIFIER,
        "DATA_QUANTUM_V2": DATA_QUANTUM_V2,
        "GOALKEEPER_DNA_V44": GOALKEEPER_DNA_V44,
        "DEFENSE_DNA_V51": DEFENSE_DNA_V51,
    }
    
    results = {}
    for name, path in paths_to_check.items():
        results[name] = path.exists()
    
    return results


def get_postgres_connection():
    """Retourne une connexion PostgreSQL."""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=POSTGRES_CONFIG["host"],
            port=POSTGRES_CONFIG["port"],
            database=POSTGRES_CONFIG["database"],
            user=POSTGRES_CONFIG["user"],
            password=POSTGRES_CONFIG["password"]
        )
        return conn
    except Exception as e:
        print(f"❌ Erreur connexion PostgreSQL: {e}")
        return None


def print_config_status():
    """Affiche le status de la configuration."""
    print("=" * 60)
    print("🏰 FORTRESS V3.8 - STATUS CONFIGURATION")
    print("=" * 60)
    
    print("\n📁 CHEMINS:")
    for name, exists in verify_paths().items():
        status = "✅" if exists else "❌"
        print(f"   {status} {name}")
    
    print(f"\n🔧 MODE: {FORTRESS_CONFIG['mode']}")
    print(f"📊 VERSION: {FORTRESS_CONFIG['version']}")
    
    # Test PostgreSQL
    conn = get_postgres_connection()
    if conn:
        print("🐘 PostgreSQL: ✅ CONNECTÉ")
        conn.close()
    else:
        print("🐘 PostgreSQL: ❌ NON CONNECTÉ")
    
    print("=" * 60)


# ═══════════════════════════════════════════════════════════════
# POINT D'ENTRÉE TEST
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print_config_status()
