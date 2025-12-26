"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    FORTRESS V38 - MODELS PACKAGE                              ║
║                    Modèles Pydantic + 12 Vecteurs DNA                         ║
║                    Version: 2.0 - Hedge Fund Grade                            ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Philosophie: "LES DONNÉES DICTENT LE PROFIL, PAS LA RÉPUTATION"

Contenu:
- odds.py: Modèles Pydantic pour les cotes (MatchOdds, OddsMovement)
- dataclasses_v2.py: 12 vecteurs DNA + TeamDNA (168 métriques)
"""

# ═══════════════════════════════════════════════════════════════════════════════
# MODÈLES PYDANTIC - ODDS (EXISTANT)
# ═══════════════════════════════════════════════════════════════════════════════

from .odds import (
    MatchOdds,
    OddsMovement,
    create_match_odds_from_dict,
)

# ═══════════════════════════════════════════════════════════════════════════════
# 12 VECTEURS DNA - DATACLASSES V2 (NOUVEAU)
# ═══════════════════════════════════════════════════════════════════════════════

from .dataclasses_v2 import (
    # Vecteur 1: MarketDNA (+20% ROI)
    MarketDNA,
    # Vecteur 2: ContextDNA (+12% ROI)
    ContextDNA,
    # Vecteur 3: RiskDNA (+5% ROI)
    RiskDNA,
    # Vecteur 4: TemporalDNA (+25% ROI) ⭐
    TemporalDNA,
    # Vecteur 5: NemesisDNA
    NemesisDNA,
    # Vecteur 6: PsycheDNA
    PsycheDNA,
    # Vecteur 7: SentimentDNA
    SentimentDNA,
    # Vecteur 8: RosterDNA
    RosterDNA,
    # Vecteur 9: PhysicalDNA
    PhysicalDNA,
    # Vecteur 10: LuckDNA
    LuckDNA,
    # Vecteur 11: ChameleonDNA
    ChameleonDNA,
    # Vecteur 12: MicroStrategyDNA (+15-25% ROI)
    MicroStrategyDNA,
    # Structure principale
    TeamDNA,
    # Profil gardien Senior Quant
    GoalkeeperProfileFBA,
    # Constantes
    DATACLASSES_VERSION,
    DATACLASSES_PHILOSOPHY,
    TOTAL_METRICS,
    GENERIC_FIELDS,
)

# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Odds (existant)
    "MatchOdds",
    "OddsMovement",
    "create_match_odds_from_dict",
    # 12 vecteurs DNA (nouveau)
    "MarketDNA",
    "ContextDNA",
    "RiskDNA",
    "TemporalDNA",
    "NemesisDNA",
    "PsycheDNA",
    "SentimentDNA",
    "RosterDNA",
    "PhysicalDNA",
    "LuckDNA",
    "ChameleonDNA",
    "MicroStrategyDNA",
    # Structures
    "TeamDNA",
    "GoalkeeperProfileFBA",
    # Constantes
    "DATACLASSES_VERSION",
    "DATACLASSES_PHILOSOPHY",
    "TOTAL_METRICS",
    "GENERIC_FIELDS",
]
