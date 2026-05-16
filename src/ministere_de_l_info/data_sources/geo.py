"""Sources géographiques — API geo.api.gouv.fr."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

# Estimations INSEE 2024 — population légale, 13 régions métropolitaines
POPULATION_2024: dict[str, int] = {
    "11": 12_271_000,  # Île-de-France
    "24": 2_607_000,   # Centre-Val de Loire
    "27": 2_795_000,   # Bourgogne-Franche-Comté
    "28": 3_352_000,   # Normandie
    "32": 6_018_000,   # Hauts-de-France
    "44": 5_559_000,   # Grand Est
    "52": 3_953_000,   # Pays de la Loire
    "53": 3_480_000,   # Bretagne
    "75": 6_194_000,   # Nouvelle-Aquitaine
    "76": 6_111_000,   # Occitanie
    "84": 8_106_000,   # Auvergne-Rhône-Alpes
    "93": 5_165_000,   # Provence-Alpes-Côte d'Azur
    "94": 357_000,     # Corse
}

_CODES_METRO: frozenset[str] = frozenset(POPULATION_2024.keys())

# geo.api.gouv.fr ne fournit pas de géométrie de contour pour les régions (limitation de l'API).
# On utilise le WFS IGN ADMIN-EXPRESS (data.geopf.fr), également source officielle sans auth.
# Le filtre CQL réduit la réponse aux 13 régions métro et stabilise le chunked-read.
_CODES_METRO_CQL = "','".join(sorted(_CODES_METRO))
_WFS_URL = (
    "https://data.geopf.fr/wfs/ows"
    "?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature"
    "&TYPENAMES=ADMINEXPRESS-COG.LATEST:region"
    "&OUTPUTFORMAT=application/json"
    "&SRSNAME=EPSG:4326"
    f"&CQL_FILTER=code_insee IN ('{_CODES_METRO_CQL}')"
)
_MAX_RETRIES = 3


def fetch_regions_geojson() -> dict:
    """Télécharge et filtre le GeoJSON des 13 régions métropolitaines depuis data.geopf.fr (IGN)."""
    logger.info("Téléchargement contours régions IGN ADMIN-EXPRESS")
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=httpx.Timeout(connect=15.0, read=120.0, write=15.0, pool=15.0)) as client:
                response = client.get(_WFS_URL)
            response.raise_for_status()
            data: dict = response.json()
            break
        except (httpx.RemoteProtocolError, httpx.ReadError) as exc:
            logger.warning("Tentative %d/%d échouée : %s", attempt, _MAX_RETRIES, exc)
            last_exc = exc
    else:
        raise RuntimeError(
            f"Impossible de télécharger les contours IGN après {_MAX_RETRIES} tentatives."
        ) from last_exc

    # Normalise les noms de propriétés (IGN → interface interne)
    # et filtre aux 13 régions métropolitaines
    features = []
    for f in data.get("features", []):
        props = f.get("properties", {})
        code = props.get("code_insee", "")
        if code not in _CODES_METRO:
            continue
        features.append({
            "type": "Feature",
            "properties": {
                "code": code,
                "nom": props.get("nom_officiel", ""),
            },
            "geometry": f["geometry"],
        })

    if len(features) != 13:
        raise ValueError(
            f"Attendu 13 régions métropolitaines, obtenu {len(features)}. "
            f"Vérifier les codes dans POPULATION_2024."
        )

    logger.info("GeoJSON normalisé : %d features", len(features))
    return {"type": "FeatureCollection", "features": features}
