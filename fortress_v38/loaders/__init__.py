"""
FORTRESS V38 - LOADERS
======================

Chargement des données DNA et marchés.

Modules:
- hybrid_dna_loader: Fusion JSON + PostgreSQL pour DNA équipes
- market_adapter: Normalisation et métadonnées des marchés

Version: 1.0.0
"""

# ═══════════════════════════════════════════════════════════════
# HYBRID DNA LOADER
# ═══════════════════════════════════════════════════════════════

from .hybrid_dna_loader import (
    # Dataclasses
    TeamDNA,
    GoalkeeperDNA,
    DefenseDNA,
    # Classe principale
    HybridDNALoader,
    # Factory
    get_hybrid_loader,
)

# ═══════════════════════════════════════════════════════════════
# MARKET ADAPTER
# ═══════════════════════════════════════════════════════════════

from .market_adapter import (
    # Dataclass
    MarketInfo,
    # Classe principale
    MarketAdapter,
    # Factory
    get_market_adapter,
    reset_adapter,
)

# ═══════════════════════════════════════════════════════════════
# EXPORTS PUBLICS
# ═══════════════════════════════════════════════════════════════

__all__ = [
    # DNA Loader
    "TeamDNA",
    "GoalkeeperDNA",
    "DefenseDNA",
    "HybridDNALoader",
    "get_hybrid_loader",
    # Market Adapter
    "MarketInfo",
    "MarketAdapter",
    "get_market_adapter",
    "reset_adapter",
]

__version__ = "1.0.0"
