"""
THE QUANTUM SOVEREIGN V3.8 - RETRY POLICY
Gestion des retries avec exponential backoff.
Créé le: 24 Décembre 2025

Analogie: Comme un téléphone qui réessaie quand l'appel échoue.
- Tentative 1: Échec → Attendre 2 secondes
- Tentative 2: Échec → Attendre 4 secondes
- Tentative 3: Échec → Abandonner et utiliser fallback

Pourquoi exponentiel ? Pour ne pas surcharger un serveur déjà en difficulté.
"""

import logging
from typing import Callable, TypeVar, Optional, Any
from functools import wraps
import time

# Tenacity est optionnel - on fournit notre propre implémentation
try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception_type,
        before_sleep_log
    )
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False

logger = logging.getLogger("quantum_sovereign.retry")

T = TypeVar('T')


# ═══════════════════════════════════════════════════════════
# CONFIGURATION DES RETRIES
# ═══════════════════════════════════════════════════════════

class RetryConfig:
    """Configuration des politiques de retry"""

    # Claude API
    CLAUDE_MAX_ATTEMPTS = 3
    CLAUDE_MIN_WAIT_SEC = 2
    CLAUDE_MAX_WAIT_SEC = 10
    CLAUDE_TIMEOUT_SEC = 30

    # RSS/Network
    RSS_MAX_ATTEMPTS = 2
    RSS_MIN_WAIT_SEC = 1
    RSS_MAX_WAIT_SEC = 5
    RSS_TIMEOUT_SEC = 5

    # Database
    DB_MAX_ATTEMPTS = 3
    DB_MIN_WAIT_SEC = 1
    DB_MAX_WAIT_SEC = 8


# ═══════════════════════════════════════════════════════════
# EXCEPTIONS RECOVERABLE
# ═══════════════════════════════════════════════════════════

RECOVERABLE_EXCEPTIONS = (
    TimeoutError,
    ConnectionError,
    ConnectionResetError,
    ConnectionRefusedError,
    BrokenPipeError,
)


# ═══════════════════════════════════════════════════════════
# DÉCORATEURS AVEC TENACITY (si disponible)
# ═══════════════════════════════════════════════════════════

if TENACITY_AVAILABLE:

    def retry_claude(func: Callable[..., T]) -> Callable[..., T]:
        """
        Décorateur pour les appels Claude API.
        3 tentatives avec backoff exponentiel (2s → 4s → 8s)
        """
        return retry(
            stop=stop_after_attempt(RetryConfig.CLAUDE_MAX_ATTEMPTS),
            wait=wait_exponential(
                multiplier=1,
                min=RetryConfig.CLAUDE_MIN_WAIT_SEC,
                max=RetryConfig.CLAUDE_MAX_WAIT_SEC
            ),
            retry=retry_if_exception_type(RECOVERABLE_EXCEPTIONS),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True
        )(func)

    def retry_network(func: Callable[..., T]) -> Callable[..., T]:
        """
        Décorateur pour les appels réseau (RSS, etc.)
        2 tentatives avec backoff court
        """
        return retry(
            stop=stop_after_attempt(RetryConfig.RSS_MAX_ATTEMPTS),
            wait=wait_exponential(
                multiplier=1,
                min=RetryConfig.RSS_MIN_WAIT_SEC,
                max=RetryConfig.RSS_MAX_WAIT_SEC
            ),
            retry=retry_if_exception_type(RECOVERABLE_EXCEPTIONS),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True
        )(func)

    def retry_database(func: Callable[..., T]) -> Callable[..., T]:
        """
        Décorateur pour les appels base de données.
        3 tentatives avec backoff modéré
        """
        import psycopg2

        db_exceptions = RECOVERABLE_EXCEPTIONS + (
            psycopg2.OperationalError,
            psycopg2.InterfaceError,
        )

        return retry(
            stop=stop_after_attempt(RetryConfig.DB_MAX_ATTEMPTS),
            wait=wait_exponential(
                multiplier=1,
                min=RetryConfig.DB_MIN_WAIT_SEC,
                max=RetryConfig.DB_MAX_WAIT_SEC
            ),
            retry=retry_if_exception_type(db_exceptions),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True
        )(func)


# ═══════════════════════════════════════════════════════════
# IMPLÉMENTATION MANUELLE (fallback si pas tenacity)
# ═══════════════════════════════════════════════════════════

else:

    def _retry_with_backoff(
        max_attempts: int,
        min_wait: float,
        max_wait: float,
        exceptions: tuple
    ) -> Callable:
        """
        Implémentation manuelle du retry avec exponential backoff.
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            def wrapper(*args, **kwargs) -> T:
                last_exception = None

                for attempt in range(1, max_attempts + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e

                        if attempt < max_attempts:
                            # Exponential backoff: 2^(attempt-1) * min_wait
                            wait_time = min(min_wait * (2 ** (attempt - 1)), max_wait)

                            logger.warning(
                                f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                                f"Retrying in {wait_time:.1f}s..."
                            )
                            time.sleep(wait_time)
                        else:
                            logger.error(
                                f"All {max_attempts} attempts failed for {func.__name__}: {e}"
                            )

                # Toutes les tentatives ont échoué
                raise last_exception

            return wrapper
        return decorator

    def retry_claude(func: Callable[..., T]) -> Callable[..., T]:
        """Retry pour Claude API (fallback manuel)"""
        return _retry_with_backoff(
            max_attempts=RetryConfig.CLAUDE_MAX_ATTEMPTS,
            min_wait=RetryConfig.CLAUDE_MIN_WAIT_SEC,
            max_wait=RetryConfig.CLAUDE_MAX_WAIT_SEC,
            exceptions=RECOVERABLE_EXCEPTIONS
        )(func)

    def retry_network(func: Callable[..., T]) -> Callable[..., T]:
        """Retry pour réseau (fallback manuel)"""
        return _retry_with_backoff(
            max_attempts=RetryConfig.RSS_MAX_ATTEMPTS,
            min_wait=RetryConfig.RSS_MIN_WAIT_SEC,
            max_wait=RetryConfig.RSS_MAX_WAIT_SEC,
            exceptions=RECOVERABLE_EXCEPTIONS
        )(func)

    def retry_database(func: Callable[..., T]) -> Callable[..., T]:
        """Retry pour database (fallback manuel)"""
        return _retry_with_backoff(
            max_attempts=RetryConfig.DB_MAX_ATTEMPTS,
            min_wait=RetryConfig.DB_MIN_WAIT_SEC,
            max_wait=RetryConfig.DB_MAX_WAIT_SEC,
            exceptions=RECOVERABLE_EXCEPTIONS
        )(func)


# ═══════════════════════════════════════════════════════════
# FONCTION UTILITAIRE
# ═══════════════════════════════════════════════════════════

def call_with_retry(
    func: Callable[..., T],
    *args,
    max_attempts: int = 3,
    min_wait: float = 2.0,
    max_wait: float = 10.0,
    fallback: Optional[Callable[..., T]] = None,
    **kwargs
) -> T:
    """
    Appelle une fonction avec retry et fallback optionnel.

    Args:
        func: Fonction à appeler
        *args: Arguments positionnels
        max_attempts: Nombre maximum de tentatives
        min_wait: Délai minimum entre tentatives (secondes)
        max_wait: Délai maximum entre tentatives (secondes)
        fallback: Fonction fallback si toutes tentatives échouent
        **kwargs: Arguments nommés

    Returns:
        Résultat de func ou du fallback

    Raises:
        Exception: Si échec et pas de fallback
    """
    last_exception = None

    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except RECOVERABLE_EXCEPTIONS as e:
            last_exception = e

            if attempt < max_attempts:
                wait_time = min(min_wait * (2 ** (attempt - 1)), max_wait)
                logger.warning(
                    f"Attempt {attempt}/{max_attempts} failed: {e}. "
                    f"Retrying in {wait_time:.1f}s..."
                )
                time.sleep(wait_time)

    # Toutes tentatives échouées
    if fallback is not None:
        logger.warning(f"All attempts failed, using fallback for {func.__name__}")
        return fallback(*args, **kwargs)

    raise last_exception


# ═══════════════════════════════════════════════════════════
# INFO
# ═══════════════════════════════════════════════════════════

def get_retry_info() -> dict:
    """Retourne les informations sur la configuration retry"""
    return {
        "tenacity_available": TENACITY_AVAILABLE,
        "claude": {
            "max_attempts": RetryConfig.CLAUDE_MAX_ATTEMPTS,
            "wait_range": f"{RetryConfig.CLAUDE_MIN_WAIT_SEC}s - {RetryConfig.CLAUDE_MAX_WAIT_SEC}s",
            "backoff": "exponential (2s -> 4s -> 8s)"
        },
        "network": {
            "max_attempts": RetryConfig.RSS_MAX_ATTEMPTS,
            "wait_range": f"{RetryConfig.RSS_MIN_WAIT_SEC}s - {RetryConfig.RSS_MAX_WAIT_SEC}s"
        },
        "database": {
            "max_attempts": RetryConfig.DB_MAX_ATTEMPTS,
            "wait_range": f"{RetryConfig.DB_MIN_WAIT_SEC}s - {RetryConfig.DB_MAX_WAIT_SEC}s"
        }
    }
