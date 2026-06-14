"""Loader DREES — APL médecins généralistes par commune HdF.

Source : DREES via data.solidarites-sante.gouv.fr
Format : XLSX (multi-onglets, 8 lignes de métadonnées à ignorer)

Pièges techniques documentés dans reports/verification-sources-phase-e-plus.md :
  - Format XLSX binaire → pandas.read_excel + openpyxl requis (groupe etl)
  - 8 premières lignes = métadonnées textuelles (skiprows=8)
  - Plusieurs onglets par millésime : 'APL 2022', 'APL 2023'…
    → sélection automatique du millésime le plus récent
  - Colonnes cibles : 'Code commune INSEE', 'APL aux médecins généralistes'

Seuil désert médical DREES : APL < 2.5 consultations/habitant/an.
  Référence : Lille (59350) → APL 2023 ≈ 6.1 (hors désert médical).

Upsert ON CONFLICT (code_commune, annee) :
  - Si ligne existante (CNAF déjà chargé) : met à jour apl_medecins + desert_medical
  - Si ligne absente : insère avec nb_foyers_rsa = NULL, taux_foyers_rsa = NULL
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import duckdb
import httpx
import pandas as pd

from ministere_de_l_info.etl._common import upsert_metadata

logger = logging.getLogger(__name__)

_DREES_URL = (
    "https://data.drees.solidarites-sante.gouv.fr/api/v2/catalog/datasets/"
    "530_l-accessibilite-potentielle-localisee-apl/attachments/"
    "indicateur_d_accessibilite_potentielle_localisee_apl_aux_medecins_generalistes_xlsx"
)
_CACHE_FILENAME = "drees-apl-medecins.xlsx"
_DEPTS_HDF = ("02", "59", "60", "62", "80")
_SEUIL_DESERT = 2.5


def _download_cache(url: str, dest: Path, force: bool = False) -> Path:
    """Télécharge un fichier XLSX en cache local via httpx streaming."""
    if dest.exists() and not force:
        logger.info("Cache DREES existant : %s", dest)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Téléchargement DREES APL → %s", dest)
    with httpx.stream("GET", url, follow_redirects=True, timeout=300.0) as r:
        r.raise_for_status()
        with dest.open("wb") as f:
            for chunk in r.iter_bytes(chunk_size=256 * 1024):
                f.write(chunk)
    logger.info("DREES téléchargé : %.1f Mo", dest.stat().st_size / 1_048_576)
    return dest


def _detect_apl_sheet(xlsx_path: Path) -> tuple[str, int]:
    """Détecte le dernier onglet APL disponible dans le fichier XLSX.

    Recherche les onglets contenant 'APL' et une année sur 4 chiffres.
    Retourne (nom_onglet, annee) pour le millésime le plus récent.
    """
    xl = pd.ExcelFile(str(xlsx_path))
    apl_sheets: list[tuple[str, int]] = []
    for sheet in xl.sheet_names:
        m = re.search(r"(\d{4})", sheet)
        if m and "APL" in sheet.upper():
            apl_sheets.append((sheet, int(m.group(1))))

    if not apl_sheets:
        raise ValueError(
            f"Aucun onglet APL trouvé dans {xlsx_path}. Onglets disponibles : {xl.sheet_names}"
        )

    return sorted(apl_sheets, key=lambda x: x[1])[-1]


def load_economie_drees(
    con: duckdb.DuckDBPyConnection,
    raw_dir: Path,
    force: bool = False,
) -> None:
    """Charge l'APL médecins généralistes par commune HdF depuis DREES.

    Détecte automatiquement le millésime le plus récent dans le XLSX.
    Upsert dans economie_social — ne touche pas aux colonnes RSA/CNAF.
    """
    cache_path = _download_cache(_DREES_URL, raw_dir / "economie" / _CACHE_FILENAME, force=force)

    sheet_name, annee_drees = _detect_apl_sheet(cache_path)
    logger.info("Onglet DREES sélectionné : '%s' (millésime %d)", sheet_name, annee_drees)

    raw = pd.read_excel(str(cache_path), sheet_name=sheet_name, skiprows=8, dtype=str)
    raw.columns = [str(c).strip() for c in raw.columns]

    # Identifier les colonnes code commune et APL généralistes (pas par tranche d'âge)
    col_code = next(
        (c for c in raw.columns if "code" in c.lower() and "commune" in c.lower()), None
    )
    col_apl = next(
        (
            c
            for c in raw.columns
            if "apl" in c.lower() and "médecins" in c.lower() and "ans" not in c.lower()
        ),
        None,
    )
    if col_code is None or col_apl is None:
        raise ValueError(
            f"Colonnes introuvables dans '{sheet_name}'. Colonnes disponibles : {list(raw.columns)}"
        )

    # Nettoyage et filtre HdF
    df = raw[[col_code, col_apl]].copy()
    df.columns = ["code_commune", "apl_medecins"]
    df["code_commune"] = df["code_commune"].astype(str).str.strip().str.zfill(5).str[:5]
    df = df[df["code_commune"].str[:2].isin(_DEPTS_HDF)].copy()
    df["apl_medecins"] = pd.to_numeric(df["apl_medecins"], errors="coerce")
    df = df.dropna(subset=["apl_medecins"]).copy()
    df["desert_medical"] = df["apl_medecins"] < _SEUIL_DESERT
    df["annee"] = annee_drees

    logger.info("DREES APL : %d communes HdF (millésime %d)", len(df), annee_drees)

    # Upsert via DuckDB (Arrow → DuckDB)
    import pyarrow as pa

    arrow_tbl = pa.Table.from_pandas(
        df[["code_commune", "annee", "apl_medecins", "desert_medical"]].astype(
            {"annee": "int32", "apl_medecins": "float64", "desert_medical": "bool"}
        )
    )
    con.register("_drees_stage", arrow_tbl)
    con.execute("""
        INSERT INTO economie_social (code_commune, annee, apl_medecins, desert_medical)
        SELECT code_commune, annee, apl_medecins, desert_medical
        FROM _drees_stage
        ON CONFLICT (code_commune, annee) DO UPDATE SET
            apl_medecins   = excluded.apl_medecins,
            desert_medical = excluded.desert_medical
    """)
    con.unregister("_drees_stage")

    count_apl = con.execute(
        "SELECT COUNT(*) FROM economie_social WHERE apl_medecins IS NOT NULL"
    ).fetchone()[0]
    n_deserts = con.execute(
        "SELECT COUNT(*) FROM economie_social WHERE desert_medical = TRUE"
    ).fetchone()[0]
    logger.info(
        "economie_social — APL : %d communes-années, dont %d déserts médicaux.",
        count_apl,
        n_deserts,
    )

    total = con.execute("SELECT COUNT(*) FROM economie_social").fetchone()[0]
    upsert_metadata(con, "economie_social", total, f"drees/apl-medecins-generalistes/{annee_drees}")
