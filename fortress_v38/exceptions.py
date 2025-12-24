"""
FORTRESS V3.8 - Hiérarchie d'Exceptions
=======================================

Gestion des erreurs niveau Hedge Fund Grade.

PRINCIPES:
1. Hiérarchie Unifiée - Le Guardian attrape par CATÉGORIE
2. Interopérabilité - Tous les engines utilisent les mêmes exceptions
3. Separation of Concerns - Exceptions ≠ Logique métier

USAGE:
    from fortress_v38.exceptions import CalculationError, DataError
    
    try:
        result = engine.calculate()
    except CalculationError as e:
        # Erreur critique - Guardian décide (skip match, pause system)
        guardian.handle_critical(e)
    except DataError as e:
        # Erreur données - Fallback ou skip
        guardian.handle_data_issue(e)

Version: 1.0.0
Date: 24 Décembre 2025
Auteur: Mya + Claude (Partenariat Senior Quant)
"""


# ═══════════════════════════════════════════════════════════════
# BASE
# ═══════════════════════════════════════════════════════════════

class FortressError(Exception):
    """
    Classe de base pour toutes les exceptions du système The Fortress V3.8.
    
    Permet un catch global: 
        try:
            ...
        except FortressError as e:
            # Attrape TOUTE erreur Fortress
    """
    pass


# ═══════════════════════════════════════════════════════════════
# CATÉGORIE 1: DONNÉES (Couche 1 & 2)
# ═══════════════════════════════════════════════════════════════

class DataError(FortressError):
    """
    Problème avec les données entrantes.
    
    Le Guardian peut décider:
    - Utiliser un fallback (données par défaut)
    - Skip le match
    - Logger et continuer
    """
    pass


class DataIntegrityError(DataError):
    """
    Données corrompues, vides ou format invalide.
    
    Exemples:
    - JSON vide ou mal formé
    - Champs obligatoires manquants
    - Types incorrects
    """
    pass


class StaleDataError(DataError):
    """
    Données trop vieilles pour être fiables.
    
    Exemples:
    - Profils tactiques > 21 jours
    - Odds > 24h
    - Stats de saison précédente
    """
    pass


class MissingEntityError(DataError):
    """
    Équipe, joueur, ou entité introuvable dans le système.
    
    Exemples:
    - Équipe promue non encore dans la DB
    - Joueur transféré
    - Gardien non répertorié
    """
    pass


# ═══════════════════════════════════════════════════════════════
# CATÉGORIE 2: CALCULS & MOTEURS (Couche 3)
# ═══════════════════════════════════════════════════════════════

class EngineError(FortressError):
    """
    Problème lors de l'exécution d'un moteur de calcul.
    
    Le Guardian DOIT réagir:
    - Skip le match (erreur critique)
    - Pause le système si récurrent
    - Alerter l'équipe
    """
    pass


class CalculationError(EngineError):
    """
    Erreur mathématique ou logique dans un calcul.
    
    CRITIQUE - Ne jamais ignorer silencieusement!
    
    Exemples:
    - Division par zéro
    - Matrices incompatibles
    - Probabilité hors [0,1]
    - Modèle non convergent
    - Monte Carlo instable
    """
    pass


class ModelExecutionError(EngineError):
    """
    Un modèle ML a crashé ou n'a pas pu se charger.
    
    Exemples:
    - Fichier modèle corrompu
    - Dépendances manquantes
    - Out of memory
    - Timeout
    """
    pass


class ConvergenceError(EngineError):
    """
    Les modèles n'arrivent pas à un consensus.
    
    Exemples:
    - Votes trop dispersés
    - Signaux contradictoires
    - Score de convergence < seuil
    """
    pass


# ═══════════════════════════════════════════════════════════════
# CATÉGORIE 3: INFRASTRUCTURE & API (Couche 4 & 5)
# ═══════════════════════════════════════════════════════════════

class InfrastructureError(FortressError):
    """
    Problème technique d'infrastructure.
    
    Le Guardian devrait:
    - Mettre le système en pause
    - Alerter immédiatement
    - Tenter un retry avec backoff
    """
    pass


class DatabaseError(InfrastructureError):
    """
    Problème avec PostgreSQL.
    
    Exemples:
    - Connexion perdue
    - Timeout query
    - Table inexistante
    """
    pass


class APIError(InfrastructureError):
    """
    Erreur lors de l'appel à une API externe.
    
    Exemples:
    - Claude API timeout
    - Odds API rate limited
    - Football API down
    """
    pass


class ConfigurationError(FortressError):
    """
    Configuration manquante ou invalide.
    
    Exemples:
    - Clé API manquante
    - Fichier config introuvable
    - Variable d'environnement non définie
    """
    pass


# ═══════════════════════════════════════════════════════════════
# CATÉGORIE 4: TRADING & GOUVERNANCE (Couche 5)
# ═══════════════════════════════════════════════════════════════

class TradingError(FortressError):
    """
    Problème lié aux décisions de trading.
    
    Le Guardian DOIT arrêter le système.
    """
    pass


class RiskLimitExceeded(TradingError):
    """
    Une limite de risque a été dépassée.
    
    Exemples:
    - Drawdown > 5%
    - Exposure > 15%
    - Losing streak > 3
    """
    pass


class TrapDetected(TradingError):
    """
    Un piège de marché a été détecté.
    
    Exemples:
    - Ligne suspecte
    - Sharp money contraire
    - Mouvement de cote anormal
    """
    pass


class BlackSwanEvent(TradingError):
    """
    Événement imprévu majeur qui invalide toutes les analyses.
    
    Exemples:
    - Blessure star annoncée à chaud
    - Conditions météo extrêmes
    - Incident sur le terrain
    """
    pass


# ═══════════════════════════════════════════════════════════════
# UTILITAIRES
# ═══════════════════════════════════════════════════════════════

def get_error_category(error: FortressError) -> str:
    """
    Retourne la catégorie d'une erreur pour le logging.
    
    Args:
        error: Une exception FortressError
    
    Returns:
        str: 'DATA', 'ENGINE', 'INFRA', 'TRADING', ou 'UNKNOWN'
    """
    if isinstance(error, DataError):
        return "DATA"
    elif isinstance(error, EngineError):
        return "ENGINE"
    elif isinstance(error, InfrastructureError):
        return "INFRA"
    elif isinstance(error, TradingError):
        return "TRADING"
    elif isinstance(error, ConfigurationError):
        return "CONFIG"
    else:
        return "UNKNOWN"


def is_critical(error: FortressError) -> bool:
    """
    Détermine si une erreur est critique (nécessite arrêt système).
    
    Returns:
        True si le Guardian doit arrêter/pauser le système
    """
    critical_types = (
        CalculationError,
        ModelExecutionError,
        InfrastructureError,
        TradingError,
    )
    return isinstance(error, critical_types)


# ═══════════════════════════════════════════════════════════════
# POINT D'ENTRÉE TEST
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("🛡️  FORTRESS V3.8 - HIÉRARCHIE D'EXCEPTIONS")
    print("=" * 60)
    
    # Test hiérarchie
    print("\n📊 Test Hiérarchie:")
    
    errors = [
        DataIntegrityError("JSON vide"),
        StaleDataError("Profils > 21 jours"),
        MissingEntityError("Équipe inconnue"),
        CalculationError("Division par zéro"),
        ModelExecutionError("Modèle non chargé"),
        ConvergenceError("Consensus < 60%"),
        DatabaseError("Connexion perdue"),
        APIError("Claude timeout"),
        ConfigurationError("Clé API manquante"),
        RiskLimitExceeded("Drawdown > 5%"),
        TrapDetected("Ligne suspecte"),
        BlackSwanEvent("Blessure star"),
    ]
    
    for error in errors:
        category = get_error_category(error)
        critical = "🔴 CRITIQUE" if is_critical(error) else "🟡 WARNING"
        print(f"   {critical} [{category:6}] {type(error).__name__}: {error}")
    
    # Test catch par catégorie
    print("\n🎯 Test Catch par Catégorie:")
    
    test_error = CalculationError("Test")
    
    try:
        raise test_error
    except EngineError:
        print("   ✅ CalculationError attrapée par 'except EngineError'")
    
    try:
        raise test_error
    except FortressError:
        print("   ✅ CalculationError attrapée par 'except FortressError'")
    
    print("\n" + "=" * 60)
    print("✅ HIÉRARCHIE D'EXCEPTIONS VALIDÉE")
    print("=" * 60)
