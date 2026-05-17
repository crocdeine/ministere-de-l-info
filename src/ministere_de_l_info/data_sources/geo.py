"""Sources géographiques — WFS IGN ADMIN-EXPRESS COG (data.geopf.fr)."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Literal

import httpx

logger = logging.getLogger(__name__)

# Estimations INSEE 2024 — population légale, 13 régions métropolitaines.
# Conservé pour compatibilité avec les tests (import direct de POPULATION_2024).
POPULATION_2024: dict[str, int] = {
    "11": 12_271_000,  # Île-de-France
    "24": 2_607_000,  # Centre-Val de Loire
    "27": 2_795_000,  # Bourgogne-Franche-Comté
    "28": 3_352_000,  # Normandie
    "32": 6_018_000,  # Hauts-de-France
    "44": 5_559_000,  # Grand Est
    "52": 3_953_000,  # Pays de la Loire
    "53": 3_480_000,  # Bretagne
    "75": 6_194_000,  # Nouvelle-Aquitaine
    "76": 6_111_000,  # Occitanie
    "84": 8_106_000,  # Auvergne-Rhône-Alpes
    "93": 5_165_000,  # Provence-Alpes-Côte d'Azur
    "94": 357_000,  # Corse
}

_CODES_METRO: frozenset[str] = frozenset(POPULATION_2024.keys())

# ── Constantes WFS ────────────────────────────────────────────────────────────

_WFS_BASE = "https://data.geopf.fr/wfs/ows"
_WFS_COMMON: dict[str, str] = {
    "SERVICE": "WFS",
    "VERSION": "2.0.0",
    "REQUEST": "GetFeature",
    "OUTPUTFORMAT": "application/json",
    "SRSNAME": "EPSG:4326",
}

AdminLevel = Literal[
    "region", "departement", "epci", "commune", "arrondissement_municipal"
]

# Filtre CQL serveur pour dom=False (métropole uniquement), par niveau.
# Noms de champs vérifiés sur GetFeature COUNT=1 le 2026-05-16.
# epci : None car codes_insee_des_departements_membres est multi-valeur, filtre CQL inapplicable.
# arrondissement_municipal : None car Paris/Lyon/Marseille sont toujours en métropole.
_DOM_EXCLUDE_FILTER: dict[str, str | None] = {
    "region": "code_insee NOT IN ('01','02','03','04','06')",
    "departement": "code_insee NOT LIKE '97%'",
    "commune": "code_insee_du_departement NOT LIKE '97%'",
    "arrondissement_municipal": None,
    "epci": None,
}


# ── Helpers privés ────────────────────────────────────────────────────────────


def _http_retry_get(
    url: str,
    params: dict[str, str],
    timeout: httpx.Timeout,
    max_retries: int = 3,
) -> httpx.Response:
    """Requête GET avec retry et backoff exponentiel (2^n secondes)."""
    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(url, params=params)
            response.raise_for_status()
            return response
        except (
            httpx.RemoteProtocolError,
            httpx.ReadError,
            httpx.HTTPStatusError,
        ) as exc:
            logger.warning("Tentative %d/%d échouée : %s", attempt, max_retries, exc)
            last_exc = exc
            if attempt < max_retries:
                time.sleep(2**attempt)
    raise RuntimeError(
        f"Requête WFS échouée après {max_retries} tentatives : {url}"
    ) from last_exc


def _wfs_stream_batch(
    url: str,
    params: dict[str, str],
    timeout: httpx.Timeout,
    dest: Path,
    max_retries: int = 8,
) -> None:
    """Télécharge un batch WFS avec streaming chunk-by-chunk vers dest.

    Avantage vs _http_retry_get : ne bufferise pas le response complet en mémoire.
    Le WFS IGN coupe parfois les connexions HTTP chunked pour des payloads ≥50 features ;
    le streaming + backoff exponentiel (2^n jusqu'à 128s) absorbe ces coupures transitoires.
    8 retries max = ~4 min de wait total, acceptable pour un ETL one-shot.
    """
    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            with httpx.Client(timeout=timeout) as client:
                with client.stream("GET", url, params=params) as response:
                    response.raise_for_status()
                    with dest.open("wb") as fh:
                        for chunk in response.iter_bytes(chunk_size=65536):
                            fh.write(chunk)
            return
        except (
            httpx.RemoteProtocolError,
            httpx.ReadError,
            httpx.HTTPStatusError,
        ) as exc:
            logger.warning("Tentative %d/%d échouée : %s", attempt, max_retries, exc)
            last_exc = exc
            dest.unlink(missing_ok=True)
            if attempt < max_retries:
                time.sleep(2**attempt)
    raise RuntimeError(
        f"Requête WFS échouée après {max_retries} tentatives : {url}"
    ) from last_exc


def _batch_file_valid(path: Path) -> bool:
    """Vérifie qu'un fichier batch GeoJSON est complet et non corrompu."""
    if not path.exists() or path.stat().st_size == 0:
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("features") is not None
    except (json.JSONDecodeError, OSError):
        return False


def _wfs_paginate(
    typenames: str,
    raw_dir: Path,
    cql_filter: str | None = None,
    batch_size: int = 1000,
    force: bool = False,
) -> Iterator[Path]:
    """Pagine le WFS IGN et yield le Path de chaque batch GeoJSON sur disque.

    Chaque batch est écrit atomiquement (.tmp puis rename). En cas de reprise
    (force=False), les fichiers batch valides sont réutilisés depuis le disque.
    La pagination s'arrête dès qu'un batch retourne moins de batch_size features.
    """
    # Nom de fichier safe : "ADMINEXPRESS-COG.LATEST:commune" → "ADMINEXPRESS-COG.LATEST_commune"
    # cql_filter → hash sha1[:8] pour éviter les collisions dom=True vs dom=False.
    # batch_size → suffixe _bN quand != 1000 (défaut) pour éviter les collisions
    # entre des appels d'exploration (batch_size=50) et des appels ETL (batch_size=1000).
    # Sans filtre, batch_size=1000 → "..._region_batch_0000.geojson" (compat ascendante)
    # Avec filtre et/ou batch_size ≠ 1000 → suffixes ajoutés dans cet ordre.
    safe_name = typenames.replace(":", "_").replace("/", "_")
    if cql_filter:
        filter_hash = hashlib.sha1(cql_filter.encode()).hexdigest()[:8]
        safe_name = f"{safe_name}_filter_{filter_hash}"
    if batch_size != 1000:
        safe_name = f"{safe_name}_b{batch_size}"
    raw_dir.mkdir(parents=True, exist_ok=True)
    timeout = httpx.Timeout(connect=15.0, read=120.0, write=15.0, pool=15.0)

    batch_num = 0
    start_index = 0

    while True:
        batch_path = raw_dir / f"{safe_name}_batch_{batch_num:04d}.geojson"
        tmp_path = raw_dir / f"{safe_name}_batch_{batch_num:04d}.geojson.tmp"

        if not force and _batch_file_valid(batch_path):
            data = json.loads(batch_path.read_text(encoding="utf-8"))
            features = data.get("features", [])
            logger.info(
                "Batch %04d — reprise disque : %d features (%s)",
                batch_num,
                len(features),
                batch_path.name,
            )
            yield batch_path
            if len(features) < batch_size:
                break
            batch_num += 1
            start_index += batch_size
            continue

        params: dict[str, str] = {
            **_WFS_COMMON,
            "TYPENAMES": typenames,
            "COUNT": str(batch_size),
            "STARTINDEX": str(start_index),
        }
        if cql_filter:
            params["CQL_FILTER"] = cql_filter

        logger.info("Batch %04d — téléchargement STARTINDEX=%d", batch_num, start_index)
        _wfs_stream_batch(_WFS_BASE, params, timeout, tmp_path)

        try:
            data = json.loads(tmp_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            tmp_path.unlink(missing_ok=True)
            raise RuntimeError(
                f"Batch {batch_num} : JSON invalide après téléchargement — "
                "relancer avec --force"
            ) from exc

        features = data.get("features", [])

        if not features:
            tmp_path.unlink(missing_ok=True)
            logger.info(
                "Pagination WFS terminée à STARTINDEX=%d (%d batches téléchargés)",
                start_index,
                batch_num,
            )
            break

        tmp_path.rename(batch_path)
        logger.info(
            "Batch %04d — %d features → %s", batch_num, len(features), batch_path.name
        )

        yield batch_path

        if len(features) < batch_size:
            break

        batch_num += 1
        start_index += batch_size


# ── API publique ──────────────────────────────────────────────────────────────


def fetch_admin_express(
    level: AdminLevel,
    dom: bool = True,
    force: bool = False,
    batch_size: int = 1000,
    raw_dir: Path | None = None,
) -> Iterator[Path]:
    """Télécharge et pagine une couche ADMIN-EXPRESS COG depuis le WFS IGN.

    Paramètres
    ----------
    level:
        Niveau administratif parmi : region, departement, epci, commune,
        arrondissement_municipal.
    dom:
        True (défaut) — métropole + DROM (971-974, 976). Les COM ne figurent
        pas dans ADMIN-EXPRESS COG, aucun filtre n'est donc nécessaire.
        False — métropole uniquement (filtre CQL côté serveur).
        ⚠ Pour epci, dom=False est ignoré : le champ
        codes_insee_des_departements_membres est multi-valeur, le filtre
        serveur CQL n'est pas applicable. Tous les EPCI sont retournés.
    force:
        Si True, retélécharge les batches même s'ils existent sur disque.
    batch_size:
        Nombre de features par requête (COUNT WFS). Défaut : 1000.
    raw_dir:
        Répertoire de sauvegarde des batches GeoJSON.
        Défaut : <racine_projet>/data/raw/.

    Yields
    ------
    Path
        Chemin vers chaque fichier batch GeoJSON, garanti complet et valide.
    """
    if not dom and level == "epci":
        logger.warning(
            "dom=False ignoré pour le niveau 'epci' : filtre CQL inapplicable "
            "sur champ multi-valeur (codes_insee_des_departements_membres). "
            "Tous les EPCI sont retournés (~1 250, dont ~30 DROM)."
        )

    if raw_dir is None:
        raw_dir = Path(__file__).resolve().parents[3] / "data" / "raw"

    typenames = f"ADMINEXPRESS-COG.LATEST:{level}"
    cql_filter: str | None = _DOM_EXCLUDE_FILTER.get(level) if not dom else None

    return _wfs_paginate(typenames, raw_dir, cql_filter, batch_size, force)


def fetch_regions_geojson() -> dict:
    """Télécharge et filtre le GeoJSON des 13 régions métropolitaines.

    Alias conservé pour compatibilité avec tests/test_etl_regions.py.
    Utilise fetch_admin_express("region", dom=False) en interne.
    """
    logger.info("Téléchargement contours régions IGN ADMIN-EXPRESS")
    features: list[dict] = []

    for batch_path in fetch_admin_express("region", dom=False):
        data = json.loads(batch_path.read_text(encoding="utf-8"))
        for f in data.get("features", []):
            props = f.get("properties", {})
            code = props.get("code_insee", "")
            if code not in _CODES_METRO:
                continue
            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "code": code,
                        "nom": props.get("nom_officiel", ""),
                    },
                    "geometry": f["geometry"],
                }
            )

    if len(features) != 13:
        raise ValueError(
            f"Attendu 13 régions métropolitaines, obtenu {len(features)}. "
            f"Vérifier les codes dans _CODES_METRO."
        )

    logger.info("GeoJSON normalisé : %d features", len(features))
    return {"type": "FeatureCollection", "features": features}
