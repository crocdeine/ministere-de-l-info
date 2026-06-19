"""Utilitaire de requêtage HTTP robuste pour APIs instables (ex: API CLAIR).

Implémente :
- Retry avec backoff exponentiel sur erreurs 5xx et timeouts
- Délai minimum entre appels (rate limiting préventif)
- Cache JSON local par URL hash pour éviter de re-frapper l'API sur re-exécution
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


def fetch_with_retry(
    url: str,
    max_retries: int = 5,
    base_delay: float = 2.0,
    timeout: float = 15.0,
    params: dict | None = None,
) -> dict | list | None:
    """GET JSON avec retry exponentiel.

    Retourne None si échec après max_retries tentatives.
    base_delay * (2 ** attempt) entre chaque tentative.
    """
    for attempt in range(max_retries):
        try:
            resp = httpx.get(url, params=params, timeout=timeout, follow_redirects=True)
            if resp.status_code in (500, 502, 503, 504):
                delay = base_delay * (2**attempt)
                logger.warning(
                    "HTTP %d sur %s (tentative %d/%d) — retry dans %.1fs",
                    resp.status_code,
                    url,
                    attempt + 1,
                    max_retries,
                    delay,
                )
                time.sleep(delay)
                continue
            resp.raise_for_status()
            return resp.json()
        except httpx.TimeoutException:
            delay = base_delay * (2**attempt)
            logger.warning(
                "Timeout sur %s (tentative %d/%d) — retry dans %.1fs",
                url,
                attempt + 1,
                max_retries,
                delay,
            )
            time.sleep(delay)
        except httpx.HTTPStatusError as e:
            logger.error("Erreur HTTP non récupérable sur %s : %s", url, e)
            return None
        except Exception as e:
            logger.error("Erreur inattendue sur %s : %s", url, e)
            return None

    logger.error("Échec définitif après %d tentatives sur %s", max_retries, url)
    return None


def fetch_page_cached(
    url: str,
    cache_dir: Path,
    cache_prefix: str,
    page: int,
    params: dict | None = None,
    max_retries: int = 5,
    base_delay: float = 2.0,
    between_calls: float = 1.5,
) -> dict | list | None:
    """GET JSON avec cache disque par page.

    Si le cache existe et est lisible, le retourne directement sans frapper l'API.
    Sinon, appelle fetch_with_retry, sauvegarde le résultat, puis le retourne.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{cache_prefix}-page-{page:04d}.json"

    if cache_file.exists():
        try:
            with cache_file.open(encoding="utf-8") as f:
                data = json.load(f)
            logger.debug("Cache lu : %s", cache_file.name)
            return data
        except (json.JSONDecodeError, OSError):
            logger.warning("Cache corrompu, re-téléchargement : %s", cache_file.name)

    time.sleep(between_calls)
    data = fetch_with_retry(url, max_retries=max_retries, base_delay=base_delay, params=params)

    if data is not None:
        try:
            with cache_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            logger.debug("Cache sauvegardé : %s", cache_file.name)
        except OSError as e:
            logger.warning("Impossible de sauvegarder le cache %s : %s", cache_file.name, e)

    return data


def url_cache_key(url: str) -> str:
    """Hash SHA-1 court d'une URL pour nommer un fichier cache."""
    return hashlib.sha1(url.encode()).hexdigest()[:12]
