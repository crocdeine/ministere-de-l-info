"""Contours des circonscriptions législatives — data.gouv.fr (jerome-desboeufs).

Source : dataset "contours-geographiques-des-circonscriptions-legislatives" publié par
jerome-desboeufs, contributeur individuel sur data.gouv.fr (pas une source officielle).
Ce dataset est dérivé des données officielles du Ministère de l'Intérieur (liste des
bureaux de vote associés à leur circonscription, publication élections législatives).

TODO : si le Ministère de l'Intérieur ou l'IGN publie un jour un dataset officiel avec
contours géographiques des 577 circonscriptions, migrer vers cette source et supprimer
la dépendance à jerome-desboeufs.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import httpx

from ministere_de_l_info.data_sources.geo import _batch_file_valid, _http_retry_get

logger = logging.getLogger(__name__)

_DATASET_SLUG = "contours-geographiques-des-circonscriptions-legislatives"
_DATAGOUV_API = "https://www.data.gouv.fr/api/1/datasets"
_RAW_FILENAME = "circonscriptions_legislatives.geojson"
_COUNT_MIN = 550
_COUNT_MAX = 580

# Codes département Z (usage interne du dataset source) → codes INSEE officiels.
# ZS (Saint-Pierre-et-Miquelon = 975) inclus pour complétude même si COM hors DROM.
_Z_TO_DEPT: dict[str, str] = {
    "ZA": "971",  # Guadeloupe
    "ZB": "972",  # Martinique
    "ZC": "973",  # Guyane
    "ZD": "974",  # La Réunion
    "ZM": "976",  # Mayotte
    "ZS": "975",  # Saint-Pierre-et-Miquelon
}

_CODE_RE = re.compile(r"^(\d{2,3}|2[AB])-\d{2}$")


# ── Helpers privés ────────────────────────────────────────────────────────────


def _resolve_geojson_url() -> str:
    """Résout l'URL courante du GeoJSON p10 via l'API data.gouv.fr."""
    timeout = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0)
    response = _http_retry_get(
        f"{_DATAGOUV_API}/{_DATASET_SLUG}/",
        params={},
        timeout=timeout,
    )
    resources = response.json().get("resources", [])
    for r in resources:
        if r.get("format") == "geojson" and "p10" in r.get("title", "").lower():
            url: str = r["url"]
            logger.info("URL GeoJSON p10 résolue : %s", url)
            return url
    raise RuntimeError(
        f"Aucune ressource GeoJSON p10 trouvée dans le dataset '{_DATASET_SLUG}'. "
        f"Ressources disponibles : {[r.get('title') for r in resources]}"
    )


def _download_raw(raw_dir: Path, force: bool = False) -> Path:
    """Télécharge le GeoJSON brut et retourne son Path (avec reprise disque)."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    dest = raw_dir / _RAW_FILENAME
    tmp = raw_dir / (_RAW_FILENAME + ".tmp")

    if not force and _batch_file_valid(dest):
        logger.info("Reprise disque : %s", dest.name)
        return dest

    url = _resolve_geojson_url()
    timeout = httpx.Timeout(connect=15.0, read=120.0, write=15.0, pool=15.0)
    logger.info("Téléchargement circonscriptions → %s", dest.name)
    response = _http_retry_get(url, params={}, timeout=timeout)
    tmp.write_bytes(response.content)
    tmp.rename(dest)
    logger.info("Sauvegardé : %s (%.1f MB)", dest.name, dest.stat().st_size / 1e6)
    return dest


def _normalize_code(code_circo: str, code_dept: str) -> str:
    """Normalise le code circonscription vers le format '{dept}-{num:02d}'.

    Metro  : '0104', '01'  → '01-04'
    DROM   : 'ZA01', 'ZA'  → '971-01'
    """
    if code_dept in _Z_TO_DEPT:
        dept = _Z_TO_DEPT[code_dept]
        num = int(code_circo[len(code_dept) :])
    else:
        dept = code_circo[:2]
        num = int(code_circo[2:])
    normalized = f"{dept}-{num:02d}"
    if not _CODE_RE.match(normalized):
        raise ValueError(
            f"Code normalisé invalide : {normalized!r} "
            f"(source : codeCirconscription={code_circo!r}, codeDepartement={code_dept!r})"
        )
    return normalized


# ── API publique ──────────────────────────────────────────────────────────────


def fetch_circonscriptions_legislatives(
    force: bool = False,
    raw_dir: Path | None = None,
) -> dict:
    """Télécharge et normalise le GeoJSON des circonscriptions législatives (~559).

    Paramètres
    ----------
    force:
        Si True, retélécharge même si le fichier existe sur disque.
    raw_dir:
        Répertoire de sauvegarde du brut.
        Défaut : <racine_projet>/data/raw/.

    Retourne
    --------
    dict
        FeatureCollection GeoJSON avec propriétés normalisées :
        ``{code, nom, code_departement, nom_departement}``.
        ``code`` au format ``'{dept}-{num:02d}'`` (ex. ``'01-04'``, ``'971-01'``).

    Notes
    -----
    Périmètre : 559 features = 539 métro + 20 DROM/SPM.
    Les 18 absents (Français de l'étranger, COM hors SPM) sont hors scope du projet.
    """
    if raw_dir is None:
        raw_dir = Path(__file__).resolve().parents[3] / "data" / "raw"

    path = _download_raw(raw_dir, force=force)
    raw = json.loads(path.read_text(encoding="utf-8"))

    features: list[dict] = []
    for f in raw.get("features", []):
        props = f.get("properties", {})
        code_dept = props.get("codeDepartement", "")
        code_circo = props.get("codeCirconscription", "")
        dept_insee = _Z_TO_DEPT.get(code_dept, code_dept)
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "code": _normalize_code(code_circo, code_dept),
                    "nom": props.get("nomCirconscription", ""),
                    "code_departement": dept_insee,
                    "nom_departement": props.get("nomDepartement", ""),
                },
                "geometry": f.get("geometry"),
            }
        )

    if not (_COUNT_MIN <= len(features) <= _COUNT_MAX):
        raise ValueError(
            f"Nombre de circonscriptions hors fourchette [{_COUNT_MIN}-{_COUNT_MAX}] : "
            f"{len(features)}. Dataset source possiblement corrompu — vérifier {_DATASET_SLUG!r}."
        )

    logger.info("GeoJSON normalisé : %d circonscriptions", len(features))
    return {"type": "FeatureCollection", "features": features}
