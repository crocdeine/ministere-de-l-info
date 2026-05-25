"""Loader data.gouv.fr — circonscriptions législatives."""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path

import duckdb

from ministere_de_l_info.data_sources.circonscriptions import fetch_circonscriptions_legislatives
from ministere_de_l_info.etl._common import upsert_metadata

logger = logging.getLogger(__name__)


def load_circonscriptions(
    con: duckdb.DuckDBPyConnection,
    raw_dir: Path,
    force: bool = False,
) -> None:
    """Charge les 559 circonscriptions législatives dans geographies_circonscriptions.

    Source : data.gouv.fr (jerome-desboeufs).
    Code format : '{dept}-{num:02d}' — ex: '01-04', '971-01'.
    Le GeoJSON normalisé est écrit dans un fichier temporaire pour ST_Read.
    """
    geojson = fetch_circonscriptions_legislatives(force=force, raw_dir=raw_dir)

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".geojson",
            delete=False,
            encoding="utf-8",
            dir=raw_dir,
        ) as f:
            json.dump(geojson, f, ensure_ascii=False)
            tmp_path = Path(f.name)

        con.execute("DROP TABLE IF EXISTS geographies_circonscriptions")
        con.execute("""
            CREATE TABLE geographies_circonscriptions (
                code                      VARCHAR(6) NOT NULL,
                nom                       VARCHAR,
                code_departement          VARCHAR(3),
                nom_departement           VARCHAR,
                geometry                  GEOMETRY,
                geometry_simplified_circo GEOMETRY,
                UNIQUE (code)
            )
        """)

        path_sql = str(tmp_path).replace("'", "''")
        con.execute(f"""
            INSERT INTO geographies_circonscriptions
            SELECT
                code,
                nom,
                code_departement,
                nom_departement,
                geom AS geometry,
                CASE
                    WHEN ST_IsValid(ST_Simplify(geom, 0.001)) THEN ST_Simplify(geom, 0.001)
                    ELSE geom
                END AS geometry_simplified_circo
            FROM ST_Read('{path_sql}')
        """)
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)

    count = con.execute("SELECT COUNT(*) FROM geographies_circonscriptions").fetchone()[0]
    if not (550 <= count <= 565):
        raise RuntimeError(
            f"Nombre de circonscriptions hors fourchette [550-565] : {count}. "
            "Vérifier la source ou utiliser --force pour re-télécharger."
        )
    logger.info("Chargé %d circonscriptions législatives.", count)

    upsert_metadata(con, "geographies_circonscriptions", count, "data.gouv.fr/jerome-desboeufs")
