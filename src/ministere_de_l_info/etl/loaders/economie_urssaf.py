"""Loader URSSAF — effectifs salariés privés par commune × APE HdF.

Source : open.urssaf.fr API OpenDataSoft
URL    : https://open.urssaf.fr/explore/dataset/
         etablissements-et-effectifs-salaries-au-niveau-commune-x-ape-last/download/
Format : CSV (séparateur ';', UTF-8, format WIDE)

Colonnes source (identifiées par reports/verification-sources-phase-e-plus.md) :
  code_commune                : VARCHAR(5)
  code_ape                    : VARCHAR(5) — code APE à 5 caractères (ex: '2511Z')
  grand_secteur_d_activite    : libellé secteur (ex: 'GS1 Industrie')
  effectifs_salaries_YYYY     : nb salariés pour l'année YYYY (2006-2025)
  nombre_d_etablissements_YYYY: nb établissements pour l'année YYYY (2006-2025)

Stratégie ETL :
  1. Téléchargement national → cache local (~100-200 Mo CSV)
  2. Lecture filtrée HdF avec DuckDB → Polars (~100-150k lignes)
  3. Détection dynamique des colonnes annuelles (regex)
  4. melt() effectifs + établissements → format long
  5. Jointure + INSERT INTO economie_emploi_urssaf (upsert)

Volume HdF estimé : ~130k lignes × 20 ans = ~2.6M lignes après unpivot.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import duckdb
import httpx
import polars as pl

from ministere_de_l_info.etl._common import upsert_metadata

logger = logging.getLogger(__name__)

_URSSAF_URL = (
    "https://open.urssaf.fr/explore/dataset/"
    "etablissements-et-effectifs-salaries-au-niveau-commune-x-ape-last/download/"
    "?format=csv&timezone=Europe/Berlin&use_labels_for_header=false"
)
_CACHE_FILENAME = "urssaf-commune-ape.csv"
_DEPTS_HDF = ("02", "59", "60", "62", "80")


def _download_cache(url: str, dest: Path, force: bool = False) -> Path:
    """Télécharge un fichier CSV en cache local via httpx streaming."""
    if dest.exists() and not force:
        logger.info("Cache existant : %s (--force pour re-télécharger)", dest)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Téléchargement URSSAF → %s (fichier national ~100-200 Mo)", dest)
    with httpx.stream("GET", url, follow_redirects=True, timeout=600.0) as r:
        r.raise_for_status()
        with dest.open("wb") as f:
            for chunk in r.iter_bytes(chunk_size=256 * 1024):
                f.write(chunk)
    logger.info("URSSAF téléchargé : %.1f Mo", dest.stat().st_size / 1_048_576)
    return dest


def _detect_year_columns(cols: list[str]) -> tuple[list[str], list[str]]:
    """Détecte les colonnes d'effectifs et d'établissements par regex."""
    eff = sorted(c for c in cols if re.match(r"effectifs_salaries_\d{4}$", c))
    etab = sorted(c for c in cols if re.match(r"nombre_d_etablissements_\d{4}$", c))
    return eff, etab


def load_economie_urssaf(
    con: duckdb.DuckDBPyConnection,
    raw_dir: Path,
    force: bool = False,
    secteurs: list[str] | None = None,
) -> None:
    """Charge les effectifs salariés privés par commune×APE depuis URSSAF.

    secteurs : liste de valeurs grand_secteur_d_activite à conserver (None = tous).
    Le rechargement complet supprime toutes les données avant insertion.
    """
    cache_path = _download_cache(_URSSAF_URL, raw_dir / "economie" / _CACHE_FILENAME, force=force)
    path_sql = str(cache_path).replace("'", "''")
    filtre_hdf = " OR ".join(f"LEFT(code_commune, 2) = '{d}'" for d in _DEPTS_HDF)

    # 1. Lire le CSV filtré HdF dans Polars (~150k lignes)
    logger.info("Lecture CSV URSSAF filtré HdF…")
    raw_df = con.execute(f"""
        SELECT *
        FROM read_csv('{path_sql}', delim=';', header=true, all_varchar=true)
        WHERE ({filtre_hdf})
    """).pl()  # noqa: S608

    if raw_df.is_empty():
        logger.warning("Aucune ligne HdF dans le fichier URSSAF — vérifier le filtre.")
        return

    logger.info("URSSAF HdF brut : %d lignes × %d colonnes.", raw_df.height, raw_df.width)

    if secteurs:
        raw_df = raw_df.filter(pl.col("grand_secteur_d_activite").is_in(secteurs))
        logger.info("Après filtre secteurs %s : %d lignes.", secteurs, raw_df.height)

    # 2. Détecter les colonnes d'effectifs et d'établissements
    eff_cols, etab_cols = _detect_year_columns(raw_df.columns)
    if not eff_cols:
        raise ValueError(
            f"Aucune colonne effectifs_salaries_YYYY dans {cache_path}. "
            f"Colonnes disponibles : {raw_df.columns[:10]}…"
        )
    logger.info(
        "URSSAF : %d années (%s→%s).",
        len(eff_cols),
        eff_cols[0][-4:],
        eff_cols[-1][-4:],
    )

    _ID_COLS = ["code_commune", "code_ape", "grand_secteur_d_activite"]

    # 3. Unpivot effectifs → long
    eff_long = (
        raw_df.select(_ID_COLS + eff_cols)
        .melt(
            id_vars=_ID_COLS,
            value_vars=eff_cols,
            variable_name="annee_col",
            value_name="nb_salaries",
        )
        .with_columns(
            pl.col("annee_col")
            .str.replace("effectifs_salaries_", "")
            .cast(pl.Int32)
            .alias("annee"),
            pl.col("nb_salaries").cast(pl.Int32, strict=False),
        )
        .drop("annee_col")
    )

    # 4. Unpivot établissements → long
    etab_long = (
        raw_df.select(_ID_COLS + etab_cols)
        .melt(
            id_vars=_ID_COLS,
            value_vars=etab_cols,
            variable_name="annee_col",
            value_name="nb_etablissements",
        )
        .with_columns(
            pl.col("annee_col")
            .str.replace("nombre_d_etablissements_", "")
            .cast(pl.Int32)
            .alias("annee"),
            pl.col("nb_etablissements").cast(pl.Int32, strict=False),
        )
        .drop("annee_col")
    )

    # 5. Jointure effectifs + établissements
    result_df = (
        eff_long.join(
            etab_long.select(_ID_COLS + ["annee", "nb_etablissements"]),
            on=_ID_COLS + ["annee"],
            how="left",
        )
        .rename({"grand_secteur_d_activite": "secteur_gs"})
        .with_columns(
            pl.col("code_commune").str.zfill(5),
            pl.col("code_ape").str.slice(0, 5),
        )
        .filter(pl.col("nb_salaries").is_not_null() | pl.col("nb_etablissements").is_not_null())
        .select(
            ["code_commune", "annee", "secteur_gs", "code_ape", "nb_salaries", "nb_etablissements"]
        )
    )

    logger.info("URSSAF après unpivot : %d lignes à insérer.", result_df.height)

    # 6. Suppression + insertion (rechargement idempotent)
    if not secteurs:
        con.execute("DELETE FROM economie_emploi_urssaf")
        logger.info("Suppression complète de economie_emploi_urssaf avant rechargement.")

    con.register("_urssaf_stage", result_df.to_arrow())
    con.execute("""
        INSERT INTO economie_emploi_urssaf
        SELECT code_commune, annee, secteur_gs, code_ape, nb_salaries, nb_etablissements
        FROM _urssaf_stage
        ON CONFLICT (code_commune, annee, code_ape) DO UPDATE SET
            secteur_gs        = excluded.secteur_gs,
            nb_salaries       = excluded.nb_salaries,
            nb_etablissements = excluded.nb_etablissements
    """)
    con.unregister("_urssaf_stage")

    count = con.execute("SELECT COUNT(*) FROM economie_emploi_urssaf").fetchone()[0]
    logger.info("economie_emploi_urssaf : %d lignes.", count)

    years = con.execute("SELECT MIN(annee), MAX(annee) FROM economie_emploi_urssaf").fetchone()
    version = f"urssaf/commune-ape {years[0]}-{years[1]}"
    upsert_metadata(con, "economie_emploi_urssaf", count, version)
