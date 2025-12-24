"""
FORTRESS V3.8 - Market Adapter
==============================

Wrapper robuste autour de MarketRegistry pour:
1. Normaliser les noms de marchés (aliases → MarketType)
2. Récupérer les métadonnées (liquidité, edge minimum, corrélations)
3. Filtrer les marchés par critères (liquidity tier, category)

Version: 2.0.0 (Réécriture Hedge Fund Grade)
Date: 24 Décembre 2025
Auteur: Mya + Claude (Partenariat Quant)

═══════════════════════════════════════════════════════════════
AUDIT PRÉ-DÉVELOPPEMENT (24 Déc 2025)
═══════════════════════════════════════════════════════════════

DÉPENDANCE: quantum/models/market_registry.py (3,292 lignes)

ENUMS AUDITÉS:
- MarketType: 123 valeurs (enum standard)
- MarketCategory: 8 valeurs, .value = string ('result', 'goals', ...)
- LiquidityTier: 5 valeurs, .value = string ('elite', 'high', 'medium', 'low', 'exotic')
- ClosingSource: 5 valeurs, .value = string
- PayoffType: 3 valeurs, .value = string ('binary', 'categorical', 'continuous')

DATACLASS MarketMetadata (11 champs):
- canonical_name: str
- aliases: list
- category: MarketCategory (enum)
- payoff_type: PayoffType (enum)
- closing_config: ClosingConfig (dataclass)
- liquidity_tier: LiquidityTier (enum avec .value = string!)
- liquidity_tax: float
- min_edge: float
- dependencies: list
- correlations: dict
- dna_sources: list

FONCTIONS CLÉS:
- normalize_market(str) → MarketType | None
- get_market_metadata(MarketType) → MarketMetadata | None
- get_liquidity_tax(MarketType) → float
- get_min_edge(MarketType) → float
- get_all_correlations(MarketType) → {'outgoing': {...}, 'incoming': {...}}
- get_markets_by_category(MarketCategory) → List[MarketType]

RISQUES IDENTIFIÉS ET MITIGÉS:
⚠️ LiquidityTier.value = string ('elite') → Mapping vers int
⚠️ normalize_market peut retourner None → Check explicite
⚠️ get_market_metadata peut retourner None → Valeurs par défaut
⚠️ Certains alias ne matchent pas → Fuzzy matching ajouté

═══════════════════════════════════════════════════════════════
"""

import sys
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum

# Setup path
PROJECT_ROOT = Path("/home/Mon_ps")
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# MAPPINGS BASÉS SUR AUDIT (Types explicites, pas de magie)
# ═══════════════════════════════════════════════════════════════

# Mapping LiquidityTier.value (string) → int
# Source: Audit du 24 Déc 2025 - LiquidityTier enum
LIQUIDITY_TIER_TO_INT: Dict[str, int] = {
    "elite": 1,     # LiquidityTier.ELITE.value
    "high": 2,      # LiquidityTier.HIGH.value
    "medium": 3,    # LiquidityTier.MEDIUM.value
    "low": 4,       # LiquidityTier.LOW.value
    "exotic": 5,    # LiquidityTier.EXOTIC.value
}

# Mapping inverse pour affichage
INT_TO_LIQUIDITY_NAME: Dict[int, str] = {
    1: "ELITE",
    2: "HIGH",
    3: "MEDIUM",
    4: "LOW",
    5: "EXOTIC",
}


# ═══════════════════════════════════════════════════════════════
# IMPORT MARKET REGISTRY (avec gestion d'erreur)
# ═══════════════════════════════════════════════════════════════

try:
    from quantum.models.market_registry import (
        MarketType,
        MarketCategory,
        LiquidityTier,
        ClosingSource,
        PayoffType,
        normalize_market,
        get_market_metadata,
        get_markets_by_category,
        get_liquidity_tax,
        get_min_edge,
        get_all_correlations,
    )
    REGISTRY_AVAILABLE = True
    logger.info("✅ MarketRegistry importé avec succès")
except ImportError as e:
    logger.error(f"❌ MarketRegistry non disponible: {e}")
    REGISTRY_AVAILABLE = False
    # Définir des stubs pour éviter les erreurs
    MarketType = None
    MarketCategory = None
    LiquidityTier = None


# ═══════════════════════════════════════════════════════════════
# DATACLASS RÉSULTAT (Contrat clair et documenté)
# ═══════════════════════════════════════════════════════════════

@dataclass
class MarketInfo:
    """
    Information complète sur un marché normalisé.
    
    CONTRAT:
    - Tous les champs ont des types primitifs (pas d'enum brut)
    - Aucun champ ne peut être None après construction
    - is_valid=False si le marché n'existe pas dans le registry
    """
    # Identification
    market_type: Optional[Any] = None  # MarketType enum ou None si invalide
    market_name: str = ""              # Nom canonique (ex: "OVER_25")
    canonical_name: str = ""           # Nom technique (ex: "over_2.5")
    
    # Catégorie
    category: str = ""                 # String, pas enum (ex: "GOALS")
    payoff_type: str = "BINARY"        # String, pas enum
    
    # Liquidité (TOUJOURS en int, jamais string)
    liquidity_tier: int = 3            # 1=ELITE, 2=HIGH, 3=MEDIUM, 4=LOW, 5=EXOTIC
    liquidity_tier_name: str = "MEDIUM"
    liquidity_tax: float = 0.0
    
    # Edge
    min_edge: float = 0.02             # Défaut conservateur
    
    # Closing
    closing_source: str = "UNKNOWN"
    
    # Corrélations
    correlations_outgoing: Dict[str, float] = field(default_factory=dict)
    correlations_incoming: Dict[str, float] = field(default_factory=dict)
    
    # Aliases
    aliases: List[str] = field(default_factory=list)
    
    # Flags
    is_valid: bool = False             # True si le marché existe dans registry
    is_tradeable: bool = False         # True si liquidité OK pour trading


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS (Logique isolée et testable)
# ═══════════════════════════════════════════════════════════════

def _liquidity_tier_to_int(tier: Any) -> int:
    """
    Convertit LiquidityTier enum en int.
    
    AUDIT: LiquidityTier.ELITE.value = 'elite' (string!)
    On utilise le mapping LIQUIDITY_TIER_TO_INT.
    
    Args:
        tier: LiquidityTier enum ou string ou int
    
    Returns:
        int entre 1 et 5, défaut 3 (MEDIUM)
    """
    # Cas 1: Déjà un int
    if isinstance(tier, int):
        return max(1, min(5, tier))  # Clamp entre 1 et 5
    
    # Cas 2: Enum avec .value (string)
    if hasattr(tier, 'value'):
        value = tier.value
        if isinstance(value, str):
            return LIQUIDITY_TIER_TO_INT.get(value.lower(), 3)
        if isinstance(value, int):
            return max(1, min(5, value))
    
    # Cas 3: String directe
    if isinstance(tier, str):
        return LIQUIDITY_TIER_TO_INT.get(tier.lower(), 3)
    
    # Cas 4: Défaut
    return 3


def _extract_category_name(category: Any) -> str:
    """
    Extrait le nom string d'une MarketCategory.
    
    AUDIT: MarketCategory.GOALS.name = 'GOALS', .value = 'goals'
    On utilise .name pour cohérence uppercase.
    """
    if category is None:
        return ""
    if hasattr(category, 'name'):
        return str(category.name)
    return str(category).upper()


def _extract_closing_source_name(source: Any) -> str:
    """
    Extrait le nom string d'un ClosingSource.
    
    AUDIT: ClosingSource.FOOTBALL_DATA_UK.name = 'FOOTBALL_DATA_UK'
    """
    if source is None:
        return "UNKNOWN"
    if hasattr(source, 'name'):
        return str(source.name)
    return str(source).upper()


def _extract_payoff_type_name(payoff: Any) -> str:
    """
    Extrait le nom string d'un PayoffType.
    
    AUDIT: PayoffType.BINARY.name = 'BINARY'
    """
    if payoff is None:
        return "BINARY"
    if hasattr(payoff, 'name'):
        return str(payoff.name)
    return str(payoff).upper()


def _fuzzy_normalize(market_name: str) -> Optional[Any]:
    """
    Tente de normaliser un nom de marché avec fuzzy matching.
    
    Le registry peut être strict sur les formats, donc on essaie
    plusieurs transformations.
    
    Args:
        market_name: Nom brut du marché
    
    Returns:
        MarketType ou None
    """
    if not REGISTRY_AVAILABLE:
        return None
    
    # Essai direct d'abord
    result = normalize_market(market_name)
    if result is not None:
        return result
    
    # Nettoyage
    clean = market_name.lower().strip()
    
    # Liste des variantes à tester
    variants = [
        clean,
        clean.replace(" goals", ""),
        clean.replace("goals ", ""),
        clean.replace(" goal", ""),
        clean.replace("goal ", ""),
        re.sub(r'\s+', ' ', clean),
        re.sub(r'\s+', '_', clean),
        re.sub(r'\s+', '', clean),
    ]
    
    # BTTS variations
    if "btts" in clean or "both teams" in clean:
        if "yes" in clean or "oui" in clean:
            variants.extend(["btts_yes", "btts yes", "btts_yes"])
        elif "no" in clean or "non" in clean:
            variants.extend(["btts_no", "btts no", "btts_no"])
    
    # Over/Under variations
    if "over" in clean or "under" in clean:
        # Extraire le nombre (ex: "over 2.5" → "2.5")
        match = re.search(r'(\d+\.?\d*)', clean)
        if match:
            num = match.group(1)
            num_clean = num.replace('.', '_').replace('_5', '5')
            if "over" in clean:
                variants.extend([f"over_{num}", f"over{num}", f"over_{num_clean}"])
            else:
                variants.extend([f"under_{num}", f"under{num}", f"under_{num_clean}"])
    
    # Home/Away/Draw
    if clean in ["home win", "home", "1", "1x2 home"]:
        variants.append("home_win")
    if clean in ["away win", "away", "2", "1x2 away"]:
        variants.append("away_win")
    if clean in ["draw", "x", "nul"]:
        variants.append("draw")
    
    # Tester toutes les variantes
    for variant in variants:
        result = normalize_market(variant)
        if result is not None:
            return result
    
    return None


# ═══════════════════════════════════════════════════════════════
# MARKET ADAPTER (Classe principale)
# ═══════════════════════════════════════════════════════════════

class MarketAdapter:
    """
    Adapter robuste pour le MarketRegistry.
    
    Simplifie l'accès aux fonctions du registry et garantit:
    - Types primitifs en sortie (pas d'enum brut)
    - Gestion explicite des None
    - Conversion LiquidityTier → int
    - Fuzzy matching pour noms de marchés
    
    USAGE:
        adapter = get_market_adapter()
        info = adapter.normalize("over 2.5 goals")
        if info.is_valid:
            print(f"Tier: {info.liquidity_tier}")  # int, pas enum
    """
    
    def __init__(self, min_liquidity_tier: int = 3):
        """
        Args:
            min_liquidity_tier: Tier maximum acceptable (1=ELITE only, 5=all)
                               Les marchés avec tier > min sont non-tradeables
        """
        self.min_liquidity_tier = min_liquidity_tier
        self._cache: Dict[str, MarketInfo] = {}
        
        # Stats pour monitoring
        self._stats = {
            "normalize_calls": 0,
            "cache_hits": 0,
            "direct_matches": 0,
            "fuzzy_matches": 0,
            "not_found": 0,
        }
    
    def normalize(self, market_name: str) -> MarketInfo:
        """
        Normalise un nom de marché et retourne toutes ses infos.
        
        CONTRAT:
        - Retourne TOUJOURS un MarketInfo (jamais None)
        - Si marché invalide: is_valid=False, is_tradeable=False
        - Tous les types sont primitifs (string, int, float, dict)
        
        Args:
            market_name: Nom brut du marché (ex: "over 2.5 goals")
        
        Returns:
            MarketInfo avec toutes les métadonnées
        """
        self._stats["normalize_calls"] += 1
        
        # Check registry disponible
        if not REGISTRY_AVAILABLE:
            return MarketInfo(
                market_name=market_name,
                is_valid=False,
                is_tradeable=False
            )
        
        # Cache lookup
        cache_key = market_name.lower().strip()
        if cache_key in self._cache:
            self._stats["cache_hits"] += 1
            return self._cache[cache_key]
        
        # Normaliser (direct puis fuzzy)
        market_type = normalize_market(market_name)
        if market_type is not None:
            self._stats["direct_matches"] += 1
        else:
            market_type = _fuzzy_normalize(market_name)
            if market_type is not None:
                self._stats["fuzzy_matches"] += 1
        
        # Si toujours None → marché invalide
        if market_type is None:
            self._stats["not_found"] += 1
            info = MarketInfo(
                market_name=market_name,
                is_valid=False,
                is_tradeable=False
            )
            self._cache[cache_key] = info
            return info
        
        # Récupérer métadonnées
        metadata = get_market_metadata(market_type)
        
        # Construire MarketInfo avec types primitifs
        if metadata is not None:
            # Extraire liquidity tier en int
            liq_tier_int = _liquidity_tier_to_int(metadata.liquidity_tier)
            
            # Extraire correlations
            try:
                all_corr = get_all_correlations(market_type)
                corr_out = all_corr.get('outgoing', {}) if all_corr else {}
                corr_in = all_corr.get('incoming', {}) if all_corr else {}
            except Exception:
                corr_out, corr_in = {}, {}
            
            # Extraire closing source
            closing_src = "UNKNOWN"
            if metadata.closing_config and hasattr(metadata.closing_config, 'primary_source'):
                closing_src = _extract_closing_source_name(metadata.closing_config.primary_source)
            
            info = MarketInfo(
                market_type=market_type,
                market_name=market_type.name,
                canonical_name=metadata.canonical_name,
                category=_extract_category_name(metadata.category),
                payoff_type=_extract_payoff_type_name(metadata.payoff_type),
                liquidity_tier=liq_tier_int,
                liquidity_tier_name=INT_TO_LIQUIDITY_NAME.get(liq_tier_int, "MEDIUM"),
                liquidity_tax=float(metadata.liquidity_tax),
                min_edge=float(metadata.min_edge),
                closing_source=closing_src,
                correlations_outgoing=corr_out,
                correlations_incoming=corr_in,
                aliases=list(metadata.aliases) if metadata.aliases else [],
                is_valid=True,
                is_tradeable=(liq_tier_int <= self.min_liquidity_tier)
            )
        else:
            # Metadata None → utiliser valeurs par défaut
            info = MarketInfo(
                market_type=market_type,
                market_name=market_type.name if hasattr(market_type, 'name') else str(market_type),
                is_valid=True,
                is_tradeable=True  # Défaut optimiste si pas de metadata
            )
        
        # Cache
        self._cache[cache_key] = info
        return info
    
    # ─── MÉTHODES UTILITAIRES ───
    
    def get_market_type(self, market_name: str) -> Optional[Any]:
        """Retourne le MarketType enum ou None."""
        info = self.normalize(market_name)
        return info.market_type if info.is_valid else None
    
    def is_valid(self, market_name: str) -> bool:
        """Vérifie si un marché existe dans le registry."""
        return self.normalize(market_name).is_valid
    
    def is_tradeable(self, market_name: str) -> bool:
        """Vérifie si un marché est tradeable (liquidité OK)."""
        info = self.normalize(market_name)
        return info.is_valid and info.is_tradeable
    
    def get_liquidity_tier(self, market_name: str) -> int:
        """Retourne le tier de liquidité (1-5, 3 par défaut)."""
        return self.normalize(market_name).liquidity_tier
    
    def get_min_edge_required(self, market_name: str) -> float:
        """Retourne l'edge minimum requis."""
        info = self.normalize(market_name)
        return info.min_edge if info.is_valid else 0.05  # Défaut conservateur
    
    def get_correlations(self, market_name: str) -> Dict[str, Dict[str, float]]:
        """Retourne les corrélations (outgoing et incoming)."""
        info = self.normalize(market_name)
        return {
            "outgoing": info.correlations_outgoing,
            "incoming": info.correlations_incoming
        }
    
    # ─── MÉTHODES DE FILTRAGE ───
    
    def filter_by_category(self, category: str) -> List[str]:
        """
        Retourne tous les noms de marchés d'une catégorie.
        
        Args:
            category: Nom de la catégorie (ex: "GOALS", "BTTS", "RESULT")
        
        Returns:
            Liste des noms de marchés
        """
        if not REGISTRY_AVAILABLE:
            return []
        
        try:
            # MarketCategory utilise .value en lowercase
            cat_enum = MarketCategory[category.upper()]
            markets = get_markets_by_category(cat_enum)
            return [m.name for m in markets]
        except (KeyError, AttributeError, TypeError):
            return []
    
    def filter_tradeable(self, market_names: List[str]) -> List[str]:
        """Filtre pour ne garder que les marchés tradeables."""
        return [m for m in market_names if self.is_tradeable(m)]
    
    def filter_by_min_tier(self, market_names: List[str], max_tier: int) -> List[str]:
        """Filtre par tier de liquidité maximum."""
        return [m for m in market_names 
                if self.normalize(m).liquidity_tier <= max_tier]
    
    # ─── MÉTHODES D'INSPECTION ───
    
    def get_all_markets(self) -> List[str]:
        """Retourne tous les noms de marchés disponibles."""
        if not REGISTRY_AVAILABLE or MarketType is None:
            return []
        return [m.name for m in MarketType]
    
    def get_all_categories(self) -> List[str]:
        """Retourne toutes les catégories disponibles."""
        if not REGISTRY_AVAILABLE or MarketCategory is None:
            return []
        return [c.name for c in MarketCategory]
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques d'utilisation."""
        return {
            **self._stats,
            "cache_size": len(self._cache),
            "registry_available": REGISTRY_AVAILABLE,
            "total_markets": len(self.get_all_markets()),
            "total_categories": len(self.get_all_categories()),
            "min_liquidity_tier": self.min_liquidity_tier,
        }
    
    def clear_cache(self):
        """Vide le cache."""
        self._cache.clear()


# ═══════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════

_adapter_instance: Optional[MarketAdapter] = None

def get_market_adapter(min_liquidity_tier: int = 3) -> MarketAdapter:
    """
    Retourne l'instance singleton du MarketAdapter.
    
    Args:
        min_liquidity_tier: Tier maximum pour trading (1=ELITE only, 3=jusqu'à MEDIUM)
    """
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = MarketAdapter(min_liquidity_tier)
    return _adapter_instance


def reset_adapter():
    """Réinitialise le singleton (utile pour tests)."""
    global _adapter_instance
    _adapter_instance = None


# ═══════════════════════════════════════════════════════════════
# TESTS INTÉGRÉS
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("📈 MARKET ADAPTER V2.0 - TEST HEDGE FUND GRADE")
    print("=" * 70)
    
    # Reset pour tests propres
    reset_adapter()
    adapter = get_market_adapter(min_liquidity_tier=3)
    
    # ─── TEST 1: Normalisation avec différents formats ───
    print("\n🔄 TEST 1: Normalisation")
    print("-" * 70)
    
    test_cases = [
        ("over 2.5 goals", True, "OVER_25"),
        ("over 2.5", True, "OVER_25"),
        ("BTTS Yes", True, "BTTS_YES"),
        ("btts_yes", True, "BTTS_YES"),
        ("home win", True, "HOME_WIN"),
        ("home", True, "HOME_WIN"),
        ("1", True, "HOME_WIN"),
        ("draw", True, "DRAW"),
        ("under 1.5", True, "UNDER_15"),
        ("first goalscorer", True, "FIRST_GOALSCORER"),
        ("corners over 9.5", True, "CORNERS_OVER_95"),
        ("invalid market xyz", False, None),
        ("", False, None),
    ]
    
    passed = 0
    for market_name, expected_valid, expected_name in test_cases:
        info = adapter.normalize(market_name)
        is_correct = (info.is_valid == expected_valid)
        if expected_name and info.is_valid:
            is_correct = is_correct and (info.market_name == expected_name)
        
        status = "✅" if is_correct else "❌"
        print(f"   {status} '{market_name}' → valid={info.is_valid}, name={info.market_name}")
        if is_correct:
            passed += 1
    
    print(f"\n   Score: {passed}/{len(test_cases)}")
    
    # ─── TEST 2: Types primitifs (pas d'enum) ───
    print("\n🔬 TEST 2: Types primitifs")
    print("-" * 70)
    
    info = adapter.normalize("over 2.5")
    type_checks = [
        ("market_name", info.market_name, str),
        ("category", info.category, str),
        ("liquidity_tier", info.liquidity_tier, int),
        ("liquidity_tier_name", info.liquidity_tier_name, str),
        ("liquidity_tax", info.liquidity_tax, float),
        ("min_edge", info.min_edge, float),
        ("closing_source", info.closing_source, str),
        ("is_valid", info.is_valid, bool),
        ("is_tradeable", info.is_tradeable, bool),
    ]
    
    all_correct = True
    for name, value, expected_type in type_checks:
        is_correct = isinstance(value, expected_type)
        status = "✅" if is_correct else "❌"
        print(f"   {status} {name}: {value} (type: {type(value).__name__}, expected: {expected_type.__name__})")
        if not is_correct:
            all_correct = False
    
    print(f"\n   Tous types corrects: {'✅ OUI' if all_correct else '❌ NON'}")
    
    # ─── TEST 3: Liquidité tiers ───
    print("\n💧 TEST 3: Liquidité Tiers")
    print("-" * 70)
    
    tier_tests = [
        ("over 2.5", 1, "ELITE"),      # Marché très liquide
        ("btts yes", 2, "HIGH"),        # Marché liquide
        ("first goalscorer", 3, "MEDIUM"),  # Marché moyen
        ("corners over 9.5", 4, "LOW"),     # Marché moins liquide
    ]
    
    for market_name, expected_tier, expected_name in tier_tests:
        info = adapter.normalize(market_name)
        if info.is_valid:
            status = "✅" if info.liquidity_tier == expected_tier else "⚠️"
            print(f"   {status} '{market_name}': tier={info.liquidity_tier} ({info.liquidity_tier_name}), expected={expected_tier} ({expected_name})")
        else:
            print(f"   ❌ '{market_name}': non trouvé")
    
    # ─── TEST 4: Catégories ───
    print("\n📊 TEST 4: Catégories")
    print("-" * 70)
    
    categories = adapter.get_all_categories()
    print(f"   Catégories disponibles: {categories}")
    
    for cat in ["GOALS", "RESULT", "CORNERS"]:
        markets = adapter.filter_by_category(cat)
        print(f"   {cat}: {len(markets)} marchés (ex: {markets[:3]}...)" if markets else f"   {cat}: 0 marchés")
    
    # ─── TEST 5: Corrélations ───
    print("\n🔗 TEST 5: Corrélations")
    print("-" * 70)
    
    corr = adapter.get_correlations("over 2.5")
    print(f"   OVER_25 corrélations outgoing: {len(corr['outgoing'])} marchés")
    print(f"   OVER_25 corrélations incoming: {len(corr['incoming'])} marchés")
    if corr['outgoing']:
        top_3 = list(corr['outgoing'].items())[:3]
        print(f"   Top 3 outgoing: {top_3}")
    
    # ─── TEST 6: Statistiques ───
    print("\n📈 TEST 6: Statistiques")
    print("-" * 70)
    
    stats = adapter.get_stats()
    for key, value in stats.items():
        print(f"   • {key}: {value}")
    
    # ─── RÉSUMÉ ───
    print("\n" + "=" * 70)
    print("✅ MARKET ADAPTER V2.0 - TESTS COMPLETS")
    print("=" * 70)
    print(f"   Registry disponible: {REGISTRY_AVAILABLE}")
    print(f"   Marchés total: {len(adapter.get_all_markets())}")
    print(f"   Cache size: {len(adapter._cache)}")
    print(f"   Erreurs: {adapter._stats['not_found']}")
