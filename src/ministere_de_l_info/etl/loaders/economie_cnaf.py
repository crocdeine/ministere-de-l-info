"""Loader CNAF — allocataires RSA par commune HdF.

Source : data.caf.fr API OpenDataSoft
URL    : https://data.caf.fr/explore/dataset/rsa_s_type_com_f/download/
Format : CSV (séparateur ';', UTF-8)

Colonnes source :
  dtreffre   : période de référence YYYYMM
  numcomdo   : code commune INSEE 5 chars
  nomcom     : nom commune
  rsa_type   : type RSA (RSA majoré, RSA non majoré…)
  indfoy_rsa : nb foyers allocataires — arrondi ×5 (secret CNAF)
  indnbp_rsa : nb personnes couvertes (non utilisé)

Secret statistique CNAF : arrondi au multiple de 5 (pas de NULL, pas de flag booléen).
Contrairement à l'INSEE, toutes les communes sont présentes.

Couverture : 2020-2024. Snapshot décembre uniquement (dtreffre se termine par '12').
Agrégation : SUM(indfoy_rsa) sur tous les rsa_type par commune × année.

taux_foyers_rsa = nb_foyers_rsa / pop_active × 100 (proxy RP).
  Disponible pour 2020-2021 (couverture RP). NULL pour 2022-2024.
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import httpx

from ministere_de_l_info.etl._common import upsert_metadata

logger = logging.getLogger(__name__)

_CNAF_URL = (
    "https://data.caf.fr/explore/dataset/rsa_s_type_com_f/download/"
    "?format=csv&timezone=Europe/Berlin&use_labels_for_header=false"
)
_CACHE_FILENAME = "cnaf-rsa-commune.csv"
_DEPTS_HDF = ("02", "59", "60", "62", "80")


def _download_cache(url: str, dest: Path, force: bool = False) -> Path:
    """Télécharge un fichier en cache local via httpx streaming."""
    if dest.exists() and not force:
        logger.info("Cache existant : %s (--force pour re-télécharger)", dest)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Téléchargement → %s", dest)
    with httpx.stream("GET", url, follow_redirects=True, timeout=300.0) as r:
        r.raise_for_status()
        with dest.open("wb") as f:
            for chunk in r.iter_bytes(chunk_size=256 * 1024):
                f.write(chunk)
    logger.info("Téléchargé : %.1f Mo", dest.stat().st_size / 1_048_576)
    return dest


def load_economie_cnaf(
    con: duckdb.DuckDBPyConnection,
    raw_dir: Path,
    force: bool = False,
    annees: list[int] | None = None,
) -> None:
    """Charge les allocataires RSA par commune HdF depuis data.caf.fr.

    Upsert ON CONFLICT (code_commune, annee) : ne touche pas aux colonnes APL/DREES.
    """
    cache_path = _download_cache(_CNAF_URL, raw_dir / "economie" / _CACHE_FILENAME, force=force)
    path_sql = str(cache_path).replace("'", "''")
    filtre_hdf = " OR ".join(f"LEFT(numcomdo, 2) = '{d}'" for d in _DEPTS_HDF)

    annee_cond = ""
    if annees:
        annees_str = ", ".join(str(a) for a in annees)
        annee_cond = f"AND LEFT(dtreffre, 4)::INTEGER IN ({annees_str})"
        logger.info("CNAF : chargement limité aux années %s.", annees_str)

    con.execute(f"""
        INSERT INTO economie_social (code_commune, annee, nb_foyers_rsa, taux_foyers_rsa)
        SELECT
            cnaf.code_commune,
            cnaf.annee,
            cnaf.nb_foyers_rsa,
            CASE
                WHEN rp.pop_active > 0
                THEN ROUND(cnaf.nb_foyers_rsa::DOUBLE / rp.pop_active * 100.0, 2)
                ELSE NULL
            END AS taux_foyers_rsa
        FROM (
            SELECT
                numcomdo::VARCHAR(5)         AS code_commune,
                LEFT(dtreffre, 4)::INTEGER   AS annee,
                SUM(indfoy_rsa::INTEGER)     AS nb_foyers_rsa
            FROM read_csv(
                '{path_sql}',
                delim=';',
                all_varchar=true,
                header=true
            )
            WHERE RIGHT(dtreffre, 2) = '12'
              AND ({filtre_hdf})
              {annee_cond}
              AND numcomdo IS NOT NULL
              AND numcomdo != ''
            GROUP BY numcomdo, LEFT(dtreffre, 4)
        ) cnaf
        LEFT JOIN economie_rp rp
            ON rp.code_commune = cnaf.code_commune
            AND rp.annee_millesime = cnaf.annee
        ON CONFLICT (code_commune, annee) DO UPDATE SET
            nb_foyers_rsa   = excluded.nb_foyers_rsa,
            taux_foyers_rsa = excluded.taux_foyers_rsa
    """)  # noqa: S608

    count_rsa = con.execute(
        "SELECT COUNT(*) FROM economie_social WHERE nb_foyers_rsa IS NOT NULL"
    ).fetchone()[0]
    logger.info("economie_social — RSA : %d communes-années.", count_rsa)

    for annee, n in con.execute(
        "SELECT annee, COUNT(*) FROM economie_social WHERE nb_foyers_rsa IS NOT NULL "
        "GROUP BY annee ORDER BY annee"
    ).fetchall():
        logger.info("  RSA %d : %d communes", annee, n)

    total = con.execute("SELECT COUNT(*) FROM economie_social").fetchone()[0]
    upsert_metadata(con, "economie_social", total, "cnaf/rsa_s_type_com_f")
