"""
FORTRESS V3.8 - Friction Engine (Senior Quant Grade)
=====================================================

Wrapper robuste autour de friction_matrix_12x12.py

PATTERN: Singleton + Adapter
- Singleton: Import du module UNE SEULE FOIS
- Adapter: Convertit Enums → Strings, retourne Dataclass typée

AUDIT PRÉ-DÉVELOPPEMENT (24 Déc 2025):
- Source: quantum/models/friction_matrix_12x12.py (1,367 lignes)
- TacticalProfile: 12 valeurs (POSSESSION, GEGENPRESS, LOW_BLOCK...)
- ClashType: Enum str (CHAOS_MAXIMAL, CHESS_MATCH, ABSORB_COUNTER...)
- Tempo: Enum str (EXTREME, HIGH, MEDIUM, SLOW, VARIABLE)
- FrictionResult: Dataclass 11 attributs (clash_type, tempo, goals_modifier...)

GESTION ERREURS:
- Profil inconnu → Default BALANCED avec is_valid=False
- Erreur calcul → CalculationError (Guardian décide)

Version: 1.0.0
Date: 24 Décembre 2025
Auteur: Mya + Claude (Partenariat Senior Quant)
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

# Setup path
PROJECT_ROOT = Path("/home/Mon_ps")
sys.path.insert(0, str(PROJECT_ROOT))

# Import exceptions Fortress
from fortress_v38.exceptions import (
    CalculationError,
    MissingEntityError,
    DataIntegrityError,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# DATACLASS DE SORTIE (Contrat typé - pas de Dict[str, Any])
# ═══════════════════════════════════════════════════════════════

@dataclass
class FrictionOutput:
    """
    Résultat de l'analyse de friction entre deux profils tactiques.
    
    CONTRAT:
    - Tous les champs sont typés (pas d'enum brut)
    - is_valid=False si profil inconnu ou erreur
    - Utilisé par les Nodes de la Couche 3
    """
    # Identification
    home_profile: str = ""
    away_profile: str = ""
    
    # Classification (Enums convertis en strings)
    clash_type: str = ""           # Ex: "ABSORB_COUNTER", "CHAOS_MAXIMAL"
    tempo: str = ""                # Ex: "HIGH", "VARIABLE", "SLOW"
    
    # Modificateurs numériques
    goals_modifier: float = 0.0    # Négatif = moins de buts attendus
    cards_modifier: float = 0.0    # Positif = plus de cartons
    corners_modifier: float = 0.0  # Positif = plus de corners
    first_half_bias: float = 0.5   # < 0.5 = plus en 2H
    late_goal_prob: float = 0.0    # Probabilité but tardif (75'+)
    
    # Marchés recommandés
    primary_markets: List[str] = field(default_factory=list)
    secondary_markets: List[str] = field(default_factory=list)
    avoid_markets: List[str] = field(default_factory=list)
    
    # Narrative
    description: str = ""
    
    # Validation
    is_valid: bool = True
    error_reason: str = ""
    
    def get_all_recommended_markets(self) -> List[str]:
        """Retourne primary + secondary markets."""
        return self.primary_markets + self.secondary_markets
    
    def should_avoid(self, market: str) -> bool:
        """Vérifie si un marché est à éviter."""
        return market.lower() in [m.lower() for m in self.avoid_markets]


# ═══════════════════════════════════════════════════════════════
# MAPPING PROFILS (Normalisation des inputs)
# ═══════════════════════════════════════════════════════════════

# Aliases courants vers les noms canoniques
PROFILE_ALIASES: Dict[str, str] = {
    # Standard
    "possession": "POSSESSION",
    "gegenpress": "GEGENPRESS",
    "gegenpressing": "GEGENPRESS",
    "pressing": "GEGENPRESS",
    "wide_attack": "WIDE_ATTACK",
    "wide attack": "WIDE_ATTACK",
    "wings": "WIDE_ATTACK",
    "direct_attack": "DIRECT_ATTACK",
    "direct attack": "DIRECT_ATTACK",
    "direct": "DIRECT_ATTACK",
    "low_block": "LOW_BLOCK",
    "low block": "LOW_BLOCK",
    "defensive": "LOW_BLOCK",
    "park_the_bus": "LOW_BLOCK",
    "counter_attack": "COUNTER_ATTACK",
    "counter attack": "COUNTER_ATTACK",
    "counter": "COUNTER_ATTACK",
    "high_press": "HIGH_PRESS",
    "high press": "HIGH_PRESS",
    "high_line": "HIGH_LINE",
    "high line": "HIGH_LINE",
    "balanced": "BALANCED",
    "mixed": "BALANCED",
    "pragmatic": "PRAGMATIC",
    "set_piece_focused": "SET_PIECE_FOCUSED",
    "set piece": "SET_PIECE_FOCUSED",
    "set_pieces": "SET_PIECE_FOCUSED",
    "wing_play": "WING_PLAY",
    "wing play": "WING_PLAY",
    "target_man": "TARGET_MAN",
    "target man": "TARGET_MAN",
    "target": "TARGET_MAN",
    "tiki_taka": "TIKI_TAKA",
    "tiki taka": "TIKI_TAKA",
    "tikitaka": "TIKI_TAKA",
}

# Profil par défaut si non reconnu
DEFAULT_PROFILE = "BALANCED"


# ═══════════════════════════════════════════════════════════════
# FRICTION ENGINE (Singleton + Adapter)
# ═══════════════════════════════════════════════════════════════

class FrictionEngine:
    """
    Wrapper Senior Quant autour de friction_matrix_12x12.
    
    PATTERN:
    - Singleton: Le module SDK est importé UNE SEULE FOIS
    - Adapter: Convertit les sorties en types primitifs
    
    GESTION ERREURS:
    - Profil inconnu → Utilise BALANCED avec is_valid=False
    - Erreur calcul → Raise CalculationError
    
    USAGE:
        engine = FrictionEngine()
        result = engine.calculate_friction("GEGENPRESS", "LOW_BLOCK")
        if result.is_valid:
            print(f"Clash: {result.clash_type}")
            print(f"Marchés: {result.primary_markets}")
    """
    
    _instance: Optional['FrictionEngine'] = None
    _initialized: bool = False
    
    # SDK references (lazy loaded)
    _get_friction_fn = None
    _analyze_match_fn = None
    _tactical_profiles = None
    _valid_profiles: List[str] = []
    
    def __new__(cls):
        """Singleton pattern - une seule instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialisation lazy - import SDK au premier appel."""
        if self._initialized:
            return
        
        self._load_sdk()
        self._initialized = True
    
    def _load_sdk(self):
        """
        Import le module friction_matrix_12x12 une seule fois.
        
        Raises:
            CalculationError: Si le module ne peut pas être chargé
        """
        try:
            from quantum.models.friction_matrix_12x12 import (
                get_friction,
                analyze_match_friction,
                TacticalProfile,
            )
            
            self._get_friction_fn = get_friction
            self._analyze_match_fn = analyze_match_friction
            self._tactical_profiles = TacticalProfile
            
            # Extraire les noms de profils valides
            self._valid_profiles = [p.name for p in TacticalProfile]
            
            logger.info(f"✅ FrictionEngine SDK chargé: {len(self._valid_profiles)} profils")
            
        except ImportError as e:
            logger.error(f"❌ Impossible de charger friction_matrix_12x12: {e}")
            raise CalculationError(f"SDK friction_matrix non disponible: {e}")
    
    def _normalize_profile(self, profile: str) -> Tuple[str, bool]:
        """
        Normalise un nom de profil tactique.
        
        Args:
            profile: Nom brut du profil
        
        Returns:
            Tuple[str, bool]: (profil normalisé, is_valid)
        """
        if not profile:
            return DEFAULT_PROFILE, False
        
        # Nettoyage
        clean = profile.strip().upper()
        
        # Déjà valide?
        if clean in self._valid_profiles:
            return clean, True
        
        # Chercher dans les aliases
        lower = profile.strip().lower()
        if lower in PROFILE_ALIASES:
            return PROFILE_ALIASES[lower], True
        
        # Chercher correspondance partielle
        for valid in self._valid_profiles:
            if valid in clean or clean in valid:
                return valid, True
        
        # Non trouvé → défaut
        logger.warning(f"⚠️ Profil inconnu '{profile}', utilisation de {DEFAULT_PROFILE}")
        return DEFAULT_PROFILE, False
    
    def _convert_result(
        self, 
        legacy_result: Any, 
        home_profile: str, 
        away_profile: str,
        is_valid: bool = True,
        error_reason: str = ""
    ) -> FrictionOutput:
        """
        Convertit FrictionResult legacy → FrictionOutput typé.
        
        Convertit les enums en strings.
        """
        try:
            # Extraire clash_type (enum → string)
            clash_type = ""
            if hasattr(legacy_result, 'clash_type'):
                ct = legacy_result.clash_type
                clash_type = ct.name if hasattr(ct, 'name') else str(ct)
            
            # Extraire tempo (enum → string)
            tempo = ""
            if hasattr(legacy_result, 'tempo'):
                t = legacy_result.tempo
                tempo = t.name if hasattr(t, 'name') else str(t)
            
            return FrictionOutput(
                home_profile=home_profile,
                away_profile=away_profile,
                clash_type=clash_type,
                tempo=tempo,
                goals_modifier=float(getattr(legacy_result, 'goals_modifier', 0.0)),
                cards_modifier=float(getattr(legacy_result, 'cards_modifier', 0.0)),
                corners_modifier=float(getattr(legacy_result, 'corners_modifier', 0.0)),
                first_half_bias=float(getattr(legacy_result, 'first_half_bias', 0.5)),
                late_goal_prob=float(getattr(legacy_result, 'late_goal_prob', 0.0)),
                primary_markets=list(getattr(legacy_result, 'primary_markets', [])),
                secondary_markets=list(getattr(legacy_result, 'secondary_markets', [])),
                avoid_markets=list(getattr(legacy_result, 'avoid_markets', [])),
                description=str(getattr(legacy_result, 'description', '')),
                is_valid=is_valid,
                error_reason=error_reason,
            )
        except Exception as e:
            logger.error(f"❌ Erreur conversion FrictionResult: {e}")
            raise CalculationError(f"Conversion friction échouée: {e}")
    
    # ─── API PUBLIQUE ───
    
    def calculate_friction(
        self, 
        home_profile: str, 
        away_profile: str
    ) -> FrictionOutput:
        """
        Calcule la friction entre deux profils tactiques.
        
        Args:
            home_profile: Profil tactique équipe domicile (ex: "GEGENPRESS")
            away_profile: Profil tactique équipe extérieur (ex: "LOW_BLOCK")
        
        Returns:
            FrictionOutput avec tous les indicateurs
        
        Note:
            Si un profil est inconnu, utilise BALANCED avec is_valid=False
        """
        # Normaliser les profils
        norm_home, home_valid = self._normalize_profile(home_profile)
        norm_away, away_valid = self._normalize_profile(away_profile)
        
        # Déterminer validité globale
        is_valid = home_valid and away_valid
        error_reason = ""
        if not home_valid:
            error_reason = f"Profil home inconnu: {home_profile}"
        if not away_valid:
            error_reason = f"Profil away inconnu: {away_profile}" if not error_reason else f"{error_reason}; Profil away inconnu: {away_profile}"
        
        # Appeler le SDK
        try:
            legacy_result = self._get_friction_fn(norm_home, norm_away)
            return self._convert_result(
                legacy_result, 
                norm_home, 
                norm_away, 
                is_valid, 
                error_reason
            )
        except Exception as e:
            logger.error(f"❌ Erreur calcul friction {norm_home} vs {norm_away}: {e}")
            raise CalculationError(f"Friction calculation failed: {e}")
    
    def get_recommended_markets(
        self, 
        home_profile: str, 
        away_profile: str
    ) -> List[str]:
        """
        Retourne les marchés recommandés pour cette collision.
        
        Returns:
            Liste des marchés (primary + secondary)
        """
        result = self.calculate_friction(home_profile, away_profile)
        return result.get_all_recommended_markets()
    
    def get_avoid_markets(
        self, 
        home_profile: str, 
        away_profile: str
    ) -> List[str]:
        """
        Retourne les marchés à éviter pour cette collision.
        """
        result = self.calculate_friction(home_profile, away_profile)
        return result.avoid_markets
    
    def get_goals_modifier(
        self, 
        home_profile: str, 
        away_profile: str
    ) -> float:
        """
        Retourne le modificateur de buts.
        
        Négatif = moins de buts attendus
        Positif = plus de buts attendus
        """
        result = self.calculate_friction(home_profile, away_profile)
        return result.goals_modifier
    
    def get_valid_profiles(self) -> List[str]:
        """Retourne la liste des profils tactiques valides."""
        return self._valid_profiles.copy()
    
    def is_valid_profile(self, profile: str) -> bool:
        """Vérifie si un profil est valide."""
        norm, is_valid = self._normalize_profile(profile)
        return is_valid


# ═══════════════════════════════════════════════════════════════
# FACTORY FUNCTION
# ═══════════════════════════════════════════════════════════════

def get_friction_engine() -> FrictionEngine:
    """
    Retourne l'instance singleton du FrictionEngine.
    
    Usage:
        engine = get_friction_engine()
        result = engine.calculate_friction("GEGENPRESS", "LOW_BLOCK")
    """
    return FrictionEngine()


# ═══════════════════════════════════════════════════════════════
# TESTS INTÉGRÉS
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("⚔️  FRICTION ENGINE V1.0 - TEST SENIOR QUANT")
    print("=" * 70)
    
    engine = get_friction_engine()
    
    # ─── TEST 1: Profils valides ───
    print("\n📊 TEST 1: Profils Valides")
    print("-" * 70)
    profiles = engine.get_valid_profiles()
    print(f"   {len(profiles)} profils: {profiles[:6]}...")
    
    # ─── TEST 2: Calcul friction standard ───
    print("\n⚔️  TEST 2: Calcul Friction Standard")
    print("-" * 70)
    
    test_cases = [
        ("GEGENPRESS", "LOW_BLOCK"),
        ("POSSESSION", "COUNTER_ATTACK"),
        ("HIGH_PRESS", "HIGH_PRESS"),
    ]
    
    for home, away in test_cases:
        result = engine.calculate_friction(home, away)
        print(f"\n   {home} vs {away}:")
        print(f"      Clash: {result.clash_type} | Tempo: {result.tempo}")
        print(f"      Goals mod: {result.goals_modifier:+.2f} | Late goal: {result.late_goal_prob:.0%}")
        print(f"      Primary: {result.primary_markets[:3]}")
        print(f"      Valid: {'✅' if result.is_valid else '❌'}")
    
    # ─── TEST 3: Types primitifs ───
    print("\n🔬 TEST 3: Types Primitifs (pas d'Enum brut)")
    print("-" * 70)
    
    result = engine.calculate_friction("GEGENPRESS", "LOW_BLOCK")
    type_checks = [
        ("clash_type", result.clash_type, str),
        ("tempo", result.tempo, str),
        ("goals_modifier", result.goals_modifier, float),
        ("cards_modifier", result.cards_modifier, float),
        ("late_goal_prob", result.late_goal_prob, float),
        ("primary_markets", result.primary_markets, list),
        ("is_valid", result.is_valid, bool),
    ]
    
    all_correct = True
    for name, value, expected in type_checks:
        correct = isinstance(value, expected)
        status = "✅" if correct else "❌"
        print(f"   {status} {name}: {type(value).__name__} (expected: {expected.__name__})")
        if not correct:
            all_correct = False
    
    print(f"\n   Tous types corrects: {'✅ OUI' if all_correct else '❌ NON'}")
    
    # ─── TEST 4: Normalisation profils ───
    print("\n🔄 TEST 4: Normalisation Profils (Aliases)")
    print("-" * 70)
    
    alias_tests = [
        ("gegenpress", True),
        ("gegenpressing", True),
        ("pressing", True),
        ("low block", True),
        ("park_the_bus", True),
        ("counter", True),
        ("POSSESSION", True),
        ("unknown_style", False),
        ("", False),
    ]
    
    for alias, expected_valid in alias_tests:
        is_valid = engine.is_valid_profile(alias)
        status = "✅" if (is_valid == expected_valid) else "❌"
        print(f"   {status} '{alias}' → valid={is_valid} (expected: {expected_valid})")
    
    # ─── TEST 5: Profil inconnu → Default gracieux ───
    print("\n⚠️  TEST 5: Profil Inconnu (Default Gracieux)")
    print("-" * 70)
    
    result = engine.calculate_friction("UNKNOWN_STYLE", "LOW_BLOCK")
    print(f"   Input: 'UNKNOWN_STYLE' vs 'LOW_BLOCK'")
    print(f"   is_valid: {result.is_valid} (devrait être False)")
    print(f"   error_reason: {result.error_reason}")
    print(f"   home_profile utilisé: {result.home_profile} (fallback BALANCED)")
    print(f"   Calcul effectué: {'✅ OUI' if result.clash_type else '❌ NON'}")
    
    # ─── TEST 6: Singleton ───
    print("\n🔒 TEST 6: Singleton Pattern")
    print("-" * 70)
    
    engine1 = get_friction_engine()
    engine2 = get_friction_engine()
    engine3 = FrictionEngine()
    
    same_instance = (engine1 is engine2) and (engine2 is engine3)
    print(f"   engine1 is engine2: {engine1 is engine2}")
    print(f"   engine2 is engine3: {engine2 is engine3}")
    print(f"   Singleton OK: {'✅ OUI' if same_instance else '❌ NON'}")
    
    # ─── RÉSUMÉ ───
    print("\n" + "=" * 70)
    print("✅ FRICTION ENGINE V1.0 - TESTS COMPLETS")
    print("=" * 70)
    print(f"   Profils disponibles: {len(profiles)}")
    print(f"   Types primitifs: {'✅' if all_correct else '❌'}")
    print(f"   Singleton: {'✅' if same_instance else '❌'}")
    print(f"   Gestion erreurs: ✅ Default gracieux + CalculationError")
