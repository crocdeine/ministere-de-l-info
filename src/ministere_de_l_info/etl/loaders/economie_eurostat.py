"""Loader Eurostat SDMX — indicateurs macro HdF vs France.

Sources :
  lfst_r_lfu3rt : taux de chômage BIT par région NUTS (1999-2025)
  nama_10r_2gdp : PIB par habitant par région NUTS (2000-2024)

Format SDMX TSV Eurostat :
  - Col 0 : descripteurs séparés par virgule (freq,dims...,geo\TIME_PERIOD)
    → dernier champ après split(',') = code géographique
  - Colonnes suivantes : années avec espace trailing (ex: "2000 ")
  - Valeurs : float + flag optionnel (ex: "8.8 u", "16.1 b", ": ")
    → strip() + split()[0] → float ; ":" → NULL

Filtres appliqués (valeurs vérifiées empiriquement sur les données Eurostat) :
  Chômage : isced11=TOTAL, sex=T, age=Y15-74, unit=PC (%), geo IN ('FRE','FR')
  PIB     : unit=EUR_HAB, geo IN ('FRE','FR')

Type géographique :
  FRE → NUTS2 (région Hauts-de-France)
  FR  → NAT   (France entière)
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import httpx
import pandas as pd

from ministere_de_l_info.etl._common import upsert_metadata

logger = logging.getLogger(__name__)

_GEO_FILTER = ("FRE", "FR")

_URL_CHOMAGE = (
    "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/"
    "lfst_r_lfu3rt?format=TSV&geo=FRE&geo=FR&sinceTimePeriod=2000"
)
_URL_PIB = (
    "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/"
    "nama_10r_2gdp?format=TSV&geo=FRE&geo=FR&sinceTimePeriod=2000"
)
_CACHE_CHOMAGE = "eurostat-lfst-r-lfu3rt.tsv"
_CACHE_PIB = "eurostat-nama-10r-2gdp.tsv"


def _download_cache(url: str, dest: Path, force: bool = False) -> Path:
    """Télécharge un fichier TSV en cache local via httpx."""
    if dest.exists() and not force:
        logger.info("Cache existant : %s (--force pour re-télécharger)", dest)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Téléchargement Eurostat → %s", dest)
    r = httpx.get(url, follow_redirects=True, timeout=120.0)
    r.raise_for_status()
    dest.write_bytes(r.content)
    logger.info("Téléchargé : %.1f Ko", dest.stat().st_size / 1024)
    return dest


def _parse_value(val: str) -> float | None:
    """Convertit une valeur TSV Eurostat en float. ':' ou vide → None."""
    s = str(val).strip()
    if not s or s.startswith(":"):
        return None
    try:
        return float(s.split()[0])
    except (ValueError, IndexError):
        return None


def _geo_type(code: str) -> str:
    """Renvoie le type NUTS du code géographique."""
    if code == "FR":
        return "NAT"
    if code.startswith("FRE"):
        return "NUTS2"
    return "OTHER"


def _parse_eurostat_tsv(path: Path) -> pd.DataFrame:
    """Lit un TSV Eurostat et normalise les noms de colonnes (strip trailing spaces)."""
    df = pd.read_csv(path, sep="\t", low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    return df


def _melt_to_rows(
    df_raw: pd.DataFrame,
    col0: str,
    dims: list[str],
    annee_cols: list[str],
    indicateur: str,
    source: str,
) -> list[tuple]:
    """Assemble les dimensions + unpivot années → liste de tuples (code_geo, type_geo, annee, …)."""
    parsed = df_raw[col0].str.split(",", expand=True)
    parsed.columns = dims
    full = pd.concat([parsed, df_raw[annee_cols]], axis=1)
    full.columns = [c.strip() for c in full.columns]

    rows: list[tuple] = []
    for _, row in full.iterrows():
        geo = str(row["geo"]).strip()
        tgeo = _geo_type(geo)
        for col in annee_cols:
            try:
                annee = int(col)
            except ValueError:
                continue
            val = _parse_value(row[col])
            if val is None:
                continue
            rows.append((geo, tgeo, annee, indicateur, val, source))
    return rows


def load_economie_chomage_eurostat(
    con: duckdb.DuckDBPyConnection,
    raw_dir: Path,
    force: bool = False,
) -> None:
    """Charge le taux de chômage BIT (Eurostat lfst_r_lfu3rt) dans economie_contexte.

    Filtre : isced11=TOTAL, sex=T, age=Y15-74, unit=PC, geo IN ('FRE','FR').
    """
    cache_path = _download_cache(_URL_CHOMAGE, raw_dir / "economie" / _CACHE_CHOMAGE, force=force)
    df = _parse_eurostat_tsv(cache_path)

    col0 = df.columns[0]
    dim_str = col0.split("\\")[0]
    dims = [d.strip() for d in dim_str.split(",")]
    annee_cols = [c for c in df.columns if c != col0]

    # Reconstruire avec dimensions pour filtrer
    parsed = df[col0].str.split(",", expand=True)
    parsed.columns = dims
    full = pd.concat([parsed, df[annee_cols]], axis=1)
    full.columns = [c.strip() for c in full.columns]

    mask = (
        (full["isced11"] == "TOTAL")
        & (full["sex"] == "T")
        & (full["age"] == "Y15-74")
        & (full["unit"] == "PC")
        & (full["geo"].isin(_GEO_FILTER))
    )
    sub = full[mask].copy()
    logger.info("Chômage Eurostat — %d lignes après filtre (attendu 2 : FRE + FR)", len(sub))

    rows: list[tuple] = []
    for _, row in sub.iterrows():
        geo = str(row["geo"]).strip()
        tgeo = _geo_type(geo)
        for col in annee_cols:
            try:
                annee = int(col)
            except ValueError:
                continue
            val = _parse_value(row[col])
            if val is None:
                continue
            rows.append((geo, tgeo, annee, "tx_chomage_bit", val, "eurostat/lfst_r_lfu3rt"))

    if not rows:
        logger.warning("Aucune donnée chômage Eurostat à insérer.")
        return

    con.executemany(
        """
        INSERT INTO economie_contexte (code_geo, type_geo, annee, indicateur, valeur, source)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (code_geo, annee, indicateur) DO UPDATE SET
            valeur = excluded.valeur,
            source = excluded.source
        """,
        rows,
    )
    n = con.execute(
        "SELECT COUNT(*) FROM economie_contexte WHERE indicateur = 'tx_chomage_bit'"
    ).fetchone()[0]
    logger.info("economie_contexte — tx_chomage_bit : %d lignes.", n)
    upsert_metadata(con, "economie_contexte", n, "eurostat/lfst_r_lfu3rt")


def load_economie_pib_eurostat(
    con: duckdb.DuckDBPyConnection,
    raw_dir: Path,
    force: bool = False,
) -> None:
    """Charge le PIB par habitant (Eurostat nama_10r_2gdp) dans economie_contexte.

    Filtre : unit=EUR_HAB, geo IN ('FRE','FR').
    """
    cache_path = _download_cache(_URL_PIB, raw_dir / "economie" / _CACHE_PIB, force=force)
    df = _parse_eurostat_tsv(cache_path)

    col0 = df.columns[0]
    dim_str = col0.split("\\")[0]
    dims = [d.strip() for d in dim_str.split(",")]
    annee_cols = [c for c in df.columns if c != col0]

    parsed = df[col0].str.split(",", expand=True)
    parsed.columns = dims
    full = pd.concat([parsed, df[annee_cols]], axis=1)
    full.columns = [c.strip() for c in full.columns]

    mask = (full["unit"] == "EUR_HAB") & (full["geo"].isin(_GEO_FILTER))
    sub = full[mask].copy()
    logger.info("PIB Eurostat — %d lignes après filtre (attendu 2 : FRE + FR)", len(sub))

    rows: list[tuple] = []
    for _, row in sub.iterrows():
        geo = str(row["geo"]).strip()
        tgeo = _geo_type(geo)
        for col in annee_cols:
            try:
                annee = int(col)
            except ValueError:
                continue
            val = _parse_value(row[col])
            if val is None:
                continue
            rows.append((geo, tgeo, annee, "pib_eur_hab", val, "eurostat/nama_10r_2gdp"))

    if not rows:
        logger.warning("Aucune donnée PIB Eurostat à insérer.")
        return

    con.executemany(
        """
        INSERT INTO economie_contexte (code_geo, type_geo, annee, indicateur, valeur, source)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (code_geo, annee, indicateur) DO UPDATE SET
            valeur = excluded.valeur,
            source = excluded.source
        """,
        rows,
    )
    n = con.execute("SELECT COUNT(*) FROM economie_contexte").fetchone()[0]
    logger.info("economie_contexte — total : %d lignes.", n)
    upsert_metadata(con, "economie_contexte", n, "eurostat/lfst+nama")
