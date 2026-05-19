"""Populations légales communales — API Mélodi INSEE (DS_POPULATIONS_HISTORIQUES).

Source : https://api.insee.fr/melodi/file/DS_POPULATIONS_HISTORIQUES/DS_POPULATIONS_HISTORIQUES_CSV_FR
Format : ZIP → CSV UTF-8, séparateur ';', format LONG (une ligne par mesure par commune par an).
Données disponibles : population municipale (PMUN) de 1968 à 2023.

⚠ Limitations connues et intentionnelles :
- Seule la population MUNICIPALE (PMUN) est disponible dans DS_POPULATIONS_HISTORIQUES.
  Les colonnes `comptee_a_part` et `totale` sont NULL volontairement — ce n'est pas un bug.
- PCAP (population comptée à part) et PTOT (totale = PMUN + PCAP) existent dans l'API
  DS_POPULATIONS_REFERENCE INSEE, mais les codes géographiques retournés ("2025-ARR-062")
  ne sont pas compatibles avec les codes INSEE communes standard. Cette intégration est
  reportée à une v2.

TODO v2 : intégrer DS_POPULATIONS_REFERENCE pour enrichir `comptee_a_part` et `totale`.
Voir https://api.insee.fr/melodi/data/DS_POPULATIONS_REFERENCE?startPeriod=2023

Note sur les mises à jour : le fichier ZIP Mélodi peut être réactualisé silencieusement
par l'INSEE. La reprise disque (`force=False`) ne détecte pas les mises à jour de contenu.
Utiliser `force=True` explicitement si une remise à jour est souhaitée après publication
d'un nouveau millésime.
"""

from __future__ import annotations

import io
import logging
import zipfile
from pathlib import Path

import httpx
import polars as pl

from ministere_de_l_info.data_sources.geo import _http_retry_get

logger = logging.getLogger(__name__)

_MELODI_URL = (
    "https://api.insee.fr/melodi/file"
    "/DS_POPULATIONS_HISTORIQUES"
    "/DS_POPULATIONS_HISTORIQUES_CSV_FR"
)
_ZIP_FILENAME = "ds_populations_historiques.zip"

# Toutes les années présentes dans la source pour PMUN communal.
_ANNEES_DISPONIBLES: frozenset[int] = frozenset(
    {
        2006,
        2007,
        2008,
        2009,
        2010,
        2011,
        2012,
        2013,
        2014,
        2015,
        2016,
        2017,
        2018,
        2019,
        2020,
        2021,
        2022,
        2023,
    }
)

# Millésimes recommandés pour les analyses comparatives : espacement ≥ 5 ans,
# comparables méthodologiquement selon recommandation INSEE (cycle quinquennal complet).
_MILLESIMES_RECOMMANDES: tuple[int, ...] = (2013, 2018, 2023)


# ── Helpers privés ────────────────────────────────────────────────────────────


def _zip_valid(path: Path) -> bool:
    """Vérifie qu'un fichier ZIP est complet et lisible par zipfile."""
    if not path.exists() or path.stat().st_size == 0:
        return False
    try:
        return zipfile.is_zipfile(path)
    except OSError:
        return False


def _download_melodi_zip(raw_dir: Path, force: bool = False) -> Path:
    """Télécharge le ZIP Mélodi DS_POPULATIONS_HISTORIQUES et retourne son Path.

    Reprise disque si le fichier existe et est valide (force=False).
    Écriture atomique : .tmp → rename.
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    dest = raw_dir / _ZIP_FILENAME
    tmp = raw_dir / (_ZIP_FILENAME + ".tmp")

    if not force and _zip_valid(dest):
        logger.info("Reprise disque : %s", dest.name)
        return dest

    timeout = httpx.Timeout(connect=15.0, read=300.0, write=15.0, pool=15.0)
    logger.info("Téléchargement DS_POPULATIONS_HISTORIQUES → %s", dest.name)
    response = _http_retry_get(_MELODI_URL, params={}, timeout=timeout)
    tmp.write_bytes(response.content)
    tmp.rename(dest)
    logger.info("Sauvegardé : %s (%.1f MB)", dest.name, dest.stat().st_size / 1e6)
    return dest


def _load_csv_from_zip(zip_path: Path) -> pl.LazyFrame:
    """Extrait et lit le CSV data depuis le ZIP, filtre sur GEO_OBJECT=COM et PMUN."""
    with zipfile.ZipFile(zip_path) as zf:
        data_name = next(
            (n for n in zf.namelist() if n.lower().endswith("_data.csv")),
            None,
        )
        if data_name is None:
            raise RuntimeError(
                f"Aucun fichier *data*.csv trouvé dans {zip_path.name}. "
                f"Contenu : {zf.namelist()}"
            )
        with zf.open(data_name) as f:
            raw_bytes = f.read()

    return (
        pl.read_csv(
            io.BytesIO(raw_bytes),
            separator=";",
            encoding="utf8",
            infer_schema_length=0,  # tout en str pour éviter les erreurs de cast
            quote_char='"',
        )
        .lazy()
        .filter((pl.col("GEO_OBJECT") == "COM") & (pl.col("POPREF_MEASURE") == "PMUN"))
    )


# ── API publique ──────────────────────────────────────────────────────────────


def fetch_populations(
    annee: int,
    force: bool = False,
    raw_dir: Path | None = None,
) -> pl.DataFrame:
    """Charge les populations municipales communales pour un millésime INSEE.

    Paramètres
    ----------
    annee:
        Millésime demandé. Doit être dans ``_ANNEES_DISPONIBLES``.
        Pour des comparaisons méthodologiquement robustes, préférer
        ``_MILLESIMES_RECOMMANDES = (2013, 2018, 2023)`` (espacement ≥ 5 ans).
    force:
        Si True, retélécharge le ZIP Mélodi même s'il existe sur disque.
        Nécessaire pour intégrer un nouveau millésime publié après le premier
        téléchargement (l'INSEE met à jour le fichier sans notification).
    raw_dir:
        Répertoire de sauvegarde du ZIP.
        Défaut : <racine_projet>/data/raw/.

    Retourne
    --------
    pl.DataFrame
        Schéma garanti :

        - ``code_insee_commune`` (Utf8) : code INSEE commune, 5 chars, zero-padded.
          Pour PLM, seules les communes-mères sont présentes (75056, 69123, 13055) —
          les arrondissements municipaux (75101-75120, 69381-69389, 13201-13216) sont
          absents de DS_POPULATIONS_HISTORIQUES.
        - ``annee`` (Int32) : millésime.
        - ``municipale`` (Int64) : population municipale (PMUN).
        - ``comptee_a_part`` (Int64, nullable) : NULL — PCAP non disponible
          dans DS_POPULATIONS_HISTORIQUES. Voir TODO v2 en tête de module.
        - ``totale`` (Int64, nullable) : NULL — non calculable sans PCAP.
          Ne pas remplacer par ``municipale`` : ce serait statistiquement trompeur.

    Lève
    ----
    ValueError
        Si ``annee`` n'est pas dans ``_ANNEES_DISPONIBLES``.
    """
    if annee not in _ANNEES_DISPONIBLES:
        raise ValueError(
            f"Millésime {annee!r} non disponible dans DS_POPULATIONS_HISTORIQUES. "
            f"Années disponibles : {sorted(_ANNEES_DISPONIBLES)}. "
            f"Millésimes recommandés : {_MILLESIMES_RECOMMANDES}."
        )

    if raw_dir is None:
        raw_dir = Path(__file__).resolve().parents[3] / "data" / "raw"

    zip_path = _download_melodi_zip(raw_dir, force=force)
    lf = _load_csv_from_zip(zip_path)

    df = (
        lf.filter(pl.col("TIME_PERIOD") == str(annee))
        .select(
            pl.col("GEO").alias("code_insee_commune"),
            pl.lit(annee).cast(pl.Int32).alias("annee"),
            pl.col("OBS_VALUE").cast(pl.Int64).alias("municipale"),
            pl.lit(None).cast(pl.Int64).alias("comptee_a_part"),
            pl.lit(None).cast(pl.Int64).alias("totale"),
        )
        .collect()
    )

    logger.info("Millésime %d : %d lignes communes chargées", annee, len(df))
    return df
