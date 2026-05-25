"""Loader IGN — régions."""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from ministere_de_l_info.data_sources.geo import fetch_admin_express
from ministere_de_l_info.etl._common import upsert_metadata

logger = logging.getLogger(__name__)


def load_regions(
    con: duckdb.DuckDBPyConnection,
    raw_dir: Path,
    force: bool = False,
) -> None:
    """Charge les 18 régions (13 métro + 5 DROM) dans geographies_regions.

    Stratégie DROP + CREATE : casse l'ancienne table si colonne 'population' présente.
    Cache : utiliser force=True pour garantir les 18 régions si le cache contient
    une version métro seule (13 régions).
    """
    batch_paths = list(fetch_admin_express("region", dom=True, force=force, raw_dir=raw_dir))

    con.execute("DROP TABLE IF EXISTS geographies_regions")
    con.execute("""
        CREATE TABLE geographies_regions (
            code_insee                   VARCHAR(3) NOT NULL,
            nom                          VARCHAR    NOT NULL,
            geometry                     GEOMETRY,
            geometry_simplified_national GEOMETRY,
            geometry_simplified_regional GEOMETRY,
            UNIQUE (code_insee)
        )
    """)

    for batch_path in batch_paths:
        path_sql = str(batch_path).replace("'", "''")
        con.execute(f"""
            INSERT INTO geographies_regions
            SELECT
                code_insee,
                nom_officiel AS nom,
                geom AS geometry,
                CASE
                    WHEN ST_IsValid(ST_Simplify(geom, 0.01)) THEN ST_Simplify(geom, 0.01)
                    ELSE geom
                END AS geometry_simplified_national,
                CASE
                    WHEN ST_IsValid(ST_Simplify(geom, 0.005)) THEN ST_Simplify(geom, 0.005)
                    ELSE geom
                END AS geometry_simplified_regional
            FROM ST_Read('{path_sql}')
        """)
        logger.debug("Batch inséré : %s", batch_path.name)

    count = con.execute("SELECT COUNT(*) FROM geographies_regions").fetchone()[0]
    if not (13 <= count <= 20):
        raise RuntimeError(
            f"Nombre de régions hors fourchette [13-20] : {count}. "
            "Vérifier la source IGN ou utiliser --force pour re-télécharger."
        )

    codes = [
        r[0]
        for r in con.execute(
            "SELECT code_insee FROM geographies_regions ORDER BY code_insee"
        ).fetchall()
    ]
    logger.info("Chargé %d régions (codes : %s … %s)", count, codes[0], codes[-1])

    upsert_metadata(con, "geographies_regions", count, "ADMINEXPRESS-COG.LATEST")
