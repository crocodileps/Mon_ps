"""
Module Anti-Ban pour scraping intelligent
Hedge Fund Grade - Respectueux et robuste
"""
import time
import random
import logging
from typing import Optional
from functools import wraps

# Configuration
MIN_DELAY = 2.0  # Secondes minimum entre requêtes
MAX_DELAY = 5.0  # Secondes maximum
MAX_REQUESTS_PER_HOUR = 100
RETRY_MAX = 3
BACKOFF_FACTOR = 2.0

# Pool de User-Agents (navigateurs réels 2024-2025)
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter intelligent avec tracking"""

    def __init__(self, min_delay: float = MIN_DELAY, max_delay: float = MAX_DELAY,
                 max_per_hour: int = MAX_REQUESTS_PER_HOUR):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_per_hour = max_per_hour
        self.last_request_time = 0
        self.requests_this_hour = 0
        self.hour_start = time.time()
        self.total_requests = 0

    def wait(self):
        """Attendre le délai approprié avant la prochaine requête"""
        # Reset compteur horaire si nécessaire
        if time.time() - self.hour_start > 3600:
            logger.info(f"Hourly reset - Previous hour: {self.requests_this_hour} requests")
            self.requests_this_hour = 0
            self.hour_start = time.time()

        # Vérifier limite horaire
        if self.requests_this_hour >= self.max_per_hour:
            wait_time = 3600 - (time.time() - self.hour_start)
            logger.warning(f"Rate limit reached ({self.max_per_hour}/hour). Waiting {wait_time:.0f}s...")
            time.sleep(wait_time + 60)  # +1 minute de marge
            self.requests_this_hour = 0
            self.hour_start = time.time()

        # Délai aléatoire entre requêtes
        elapsed = time.time() - self.last_request_time
        delay = random.uniform(self.min_delay, self.max_delay)

        if elapsed < delay:
            sleep_time = delay - elapsed
            time.sleep(sleep_time)

        self.last_request_time = time.time()
        self.requests_this_hour += 1
        self.total_requests += 1

    def get_stats(self) -> dict:
        """Retourne les stats de rate limiting"""
        return {
            'requests_this_hour': self.requests_this_hour,
            'max_per_hour': self.max_per_hour,
            'remaining': self.max_per_hour - self.requests_this_hour,
            'total_requests': self.total_requests
        }


def get_random_user_agent() -> str:
    """Retourne un User-Agent aléatoire"""
    return random.choice(USER_AGENTS)


def get_headers(referer: str = None, ajax: bool = False) -> dict:
    """
    Génère des headers réalistes

    Args:
        referer: URL de référence (pour paraître naturel)
        ajax: True si requête AJAX (ajoute X-Requested-With)
    """
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }

    if referer:
        headers['Referer'] = referer

    if ajax:
        headers['X-Requested-With'] = 'XMLHttpRequest'
        headers['Accept'] = 'application/json, text/javascript, */*; q=0.01'
        headers['Sec-Fetch-Dest'] = 'empty'
        headers['Sec-Fetch-Mode'] = 'cors'

    return headers


def retry_with_backoff(max_retries: int = RETRY_MAX, backoff_factor: float = BACKOFF_FACTOR):
    """Decorator pour retry avec backoff exponentiel"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = backoff_factor ** attempt
                        logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in {wait_time:.1f}s...")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"All {max_retries} attempts failed for {func.__name__}")
            raise last_exception
        return wrapper
    return decorator


class ScraperSession:
    """Session de scraping avec gestion anti-ban intégrée"""

    def __init__(self, base_url: str = "https://www.betexplorer.com"):
        import requests
        self.base_url = base_url
        self.session = requests.Session()
        self.rate_limiter = RateLimiter()

        # Initialiser avec une première requête pour obtenir les cookies
        self._init_session()

    def _init_session(self):
        """Initialise la session avec les cookies du site"""
        try:
            self.rate_limiter.wait()
            resp = self.session.get(
                self.base_url,
                headers=get_headers(),
                timeout=15
            )
            logger.info(f"Session initialized - Cookies: {list(self.session.cookies.keys())}")
        except Exception as e:
            logger.warning(f"Session init warning: {e}")

    @retry_with_backoff()
    def get(self, url: str, ajax: bool = False, referer: str = None) -> 'requests.Response':
        """
        GET request avec rate limiting et retry

        Args:
            url: URL complète ou relative (sera préfixée avec base_url)
            ajax: True si requête AJAX
            referer: URL de référence
        """
        self.rate_limiter.wait()

        full_url = url if url.startswith('http') else f"{self.base_url}{url}"
        headers = get_headers(referer=referer or self.base_url, ajax=ajax)

        resp = self.session.get(full_url, headers=headers, timeout=15)
        resp.raise_for_status()

        return resp

    def get_stats(self) -> dict:
        """Retourne les stats de la session"""
        return self.rate_limiter.get_stats()


# Instance globale du rate limiter (pour usage simple)
rate_limiter = RateLimiter()


if __name__ == "__main__":
    print("=== Anti-Ban Module Test ===\n")

    print(f"1. User-Agent rotation ({len(USER_AGENTS)} agents):")
    for i in range(3):
        print(f"   {get_random_user_agent()[:60]}...")

    print(f"\n2. Rate limiter config:")
    print(f"   Min delay: {MIN_DELAY}s")
    print(f"   Max delay: {MAX_DELAY}s")
    print(f"   Max requests/hour: {MAX_REQUESTS_PER_HOUR}")

    print(f"\n3. Headers (normal):")
    h = get_headers()
    for k, v in list(h.items())[:3]:
        print(f"   {k}: {v[:50]}...")

    print(f"\n4. Headers (AJAX):")
    h = get_headers(ajax=True)
    print(f"   X-Requested-With: {h.get('X-Requested-With', 'N/A')}")
    print(f"   Accept: {h.get('Accept', 'N/A')[:50]}...")

    print(f"\n5. Rate limiter stats: {rate_limiter.get_stats()}")

    print("\n=== Module Ready ===")
