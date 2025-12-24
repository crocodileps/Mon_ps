"""
Ghost Scraper - Anti-Cloudflare avec curl_cffi
═══════════════════════════════════════════════════════════════════════════
Utilise curl_cffi pour imiter l'empreinte TLS de Chrome.
Pour Cloudflare, les requêtes sont indiscernables d'un vrai navigateur.
═══════════════════════════════════════════════════════════════════════════

AUTEUR: Mon_PS Team
DATE: 2025-12-24
VERSION: 1.0.0
"""
import time
import random
import logging
import hashlib
from typing import Optional, Dict
from pathlib import Path

from curl_cffi import requests as cf_requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from .config import ScraperConfig, DEFAULT_CONFIG

# Configuration du logging
logger = logging.getLogger("GhostScraper")


class CloudflareBlockError(Exception):
    """Erreur levée quand Cloudflare bloque la requête."""
    pass


class GhostScraper:
    """
    Scraper anti-Cloudflare utilisant curl_cffi.

    Caractéristiques:
    - Imite l'empreinte TLS de Chrome 110
    - Délais aléatoires avec volatilité humaine
    - Retry automatique avec backoff exponentiel
    - Hash check pour éviter re-parsing inutile

    Usage:
        scraper = GhostScraper()
        html = scraper.fetch_page("https://fbref.com/...")
    """

    def __init__(self, config: ScraperConfig = None):
        self.config = config or DEFAULT_CONFIG
        self._hash_cache: Dict[str, str] = {}
        self._cache_file = Path("/home/Mon_ps/data/cache/scraper_hashes.json")
        self._load_hash_cache()

    def _load_hash_cache(self) -> None:
        """Charge le cache des hashes depuis le fichier."""
        try:
            if self._cache_file.exists():
                import json
                with open(self._cache_file, 'r') as f:
                    self._hash_cache = json.load(f)
                logger.debug(f"Hash cache loaded: {len(self._hash_cache)} entries")
        except Exception as e:
            logger.warning(f"Could not load hash cache: {e}")
            self._hash_cache = {}

    def _save_hash_cache(self) -> None:
        """Sauvegarde le cache des hashes."""
        try:
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)
            import json
            with open(self._cache_file, 'w') as f:
                json.dump(self._hash_cache, f)
        except Exception as e:
            logger.warning(f"Could not save hash cache: {e}")

    def _get_random_delay(self) -> float:
        """
        Génère un délai aléatoire avec volatilité humaine.

        La plupart du temps 15-45s, parfois une "pause café"
        pour casser les patterns robotiques.
        """
        base_delay = random.uniform(
            self.config.MIN_DELAY,
            self.config.MAX_DELAY
        )
        volatility = random.choice(self.config.VOLATILITY_MULTIPLIERS)
        return base_delay * volatility

    def _compute_hash(self, content: str) -> str:
        """Calcule le hash MD5 du contenu."""
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def page_has_changed(self, url: str, new_html: str) -> bool:
        """
        Vérifie si la page a changé depuis le dernier scrape.

        Retourne True si la page a changé ou si c'est un nouveau scrape.
        """
        new_hash = self._compute_hash(new_html)
        old_hash = self._hash_cache.get(url)

        if old_hash and new_hash == old_hash:
            logger.info(f"⏭️ Page unchanged, skipping parse: {url}")
            return False

        self._hash_cache[url] = new_hash
        self._save_hash_cache()
        return True

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=60, max=300),
        retry=retry_if_exception_type(CloudflareBlockError)
    )
    def fetch_page(self, url: str, skip_delay: bool = False) -> Optional[str]:
        """
        Récupère une page en imitant parfaitement Chrome.

        Args:
            url: URL à récupérer
            skip_delay: Si True, ne pas attendre avant la requête

        Returns:
            HTML de la page ou None si erreur non-récupérable

        Raises:
            CloudflareBlockError: Si bloqué par Cloudflare (retry automatique)
        """
        # Délai humanisé avant la requête
        if not skip_delay:
            delay = self._get_random_delay()
            logger.info(f"😴 Sleeping {delay:.1f}s before fetching...")
            time.sleep(delay)

        logger.info(f"🌐 Fetching: {url}")

        try:
            # L'appel magique via curl_cffi
            response = cf_requests.get(
                url,
                impersonate=self.config.IMPERSONATE,
                timeout=self.config.REQUEST_TIMEOUT,
                allow_redirects=True
            )

            # Vérification statuts bloqués
            if response.status_code in self.config.BLOCKED_STATUS_CODES:
                logger.warning(
                    f"🚨 Blocked by Cloudflare ({response.status_code})"
                )
                raise CloudflareBlockError(
                    f"Status {response.status_code}"
                )

            # Vérification challenge JS
            if self.config.CLOUDFLARE_CHALLENGE_TEXT in response.text:
                logger.warning("🚨 JS Challenge detected")
                raise CloudflareBlockError("JS Challenge")

            # Vérification succès
            if response.status_code != 200:
                logger.error(f"❌ HTTP Error {response.status_code}")
                return None

            logger.info(
                f"✅ Success: {len(response.content)} bytes"
            )
            return response.text

        except CloudflareBlockError:
            # Laisse tenacity gérer le retry
            raise
        except Exception as e:
            logger.error(f"❌ Network Error: {e}")
            return None

    def fetch_with_change_detection(
        self,
        url: str
    ) -> Optional[str]:
        """
        Récupère une page et vérifie si elle a changé.

        Retourne le HTML seulement si la page a changé,
        sinon retourne None (page déjà traitée).
        """
        html = self.fetch_page(url)

        if html is None:
            return None

        if not self.page_has_changed(url, html):
            return None

        return html


# === EXEMPLE D'UTILISATION ===
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    scraper = GhostScraper()

    # Test sur une page simple
    test_url = "https://httpbin.org/headers"
    result = scraper.fetch_page(test_url)

    if result:
        print("✅ Ghost Scraper opérationnel!")
        print(f"Response preview: {result[:200]}...")
    else:
        print("❌ Échec du test")
