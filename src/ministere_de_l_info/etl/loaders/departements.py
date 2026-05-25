"""Loader IGN — départements."""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from ministere_de_l_info.data_sources.geo import fetch_admin_express
from ministere_de_l_info.etl._common import upsert_metadata

logger = logging.getLogger(__name__)


def load_departements(
    con: duckdb.DuckDBPyConnection,
    raw_dir: Path,
    force: bool = False,
) -> None:
    """Charge les 101 départements (96 métro + 5 DROM) dans geographies_departements.

    Corse : codes '2A' et '2B' — VARCHAR natif.
    batch_size=50 : le WFS IGN coupe les connexions chunked sur COUNT=1000 pour ce niveau.
    Vérifie FK conceptuelle : tous les code_region doivent exister dans geographies_regions.
    Doit être appelé après load_regions().
    """
    batch_paths = list(
        fetch_admin_express("departement", dom=True, force=force, batch_size=50, raw_dir=raw_dir)
    )

    con.execute("DROP TABLE IF EXISTS geographies_departements")
    con.execute("""
        CREATE TABLE geographies_departements (
            code_insee                        VARCHAR(3) NOT NULL,
            code_region                       VARCHAR(3) NOT NULL,
            nom                               VARCHAR    NOT NULL,
            geometry                          GEOMETRY,
            geometry_simplified_national      GEOMETRY,
            geometry_simplified_departemental GEOMETRY,
            UNIQUE (code_insee)
        )
    """)

    for batch_path in batch_paths:
        path_sql = str(batch_path).replace("'", "''")
        con.execute(f"""
            INSERT INTO geographies_departements
            SELECT
                code_insee,
                code_insee_de_la_region AS code_region,
                nom_officiel            AS nom,
                geom                    AS geometry,
                CASE
                    WHEN ST_IsValid(ST_Simplify(geom, 0.01)) THEN ST_Simplify(geom, 0.01)
                    ELSE geom
                END AS geometry_simplified_national,
                CASE
                    WHEN ST_IsValid(ST_Simplify(geom, 0.001)) THEN ST_Simplify(geom, 0.001)
                    ELSE geom
                END AS geometry_simplified_departemental
            FROM ST_Read('{path_sql}')
        """)
        logger.debug("Batch inséré : %s", batch_path.name)

    count = con.execute("SELECT COUNT(*) FROM geographies_departements").fetchone()[0]
    if count != 101:
        raise RuntimeError(
            f"Nombre de départements incorrect : {count} (attendu exactement 101). "
            "Utiliser --force pour re-télécharger si des batches corrompus sont en cache."
        )

    corse = {
        r[0]
        for r in con.execute(
            "SELECT code_insee FROM geographies_departements WHERE code_insee IN ('2A', '2B')"
        ).fetchall()
    }
    if corse != {"2A", "2B"}:
        raise RuntimeError(f"Codes Corse manquants ou incorrects : trouvé {corse}")

    orphelins = con.execute("""
        SELECT DISTINCT d.code_region
        FROM geographies_departements d
        WHERE d.code_region NOT IN (SELECT code_insee FROM geographies_regions)
    """).fetchall()
    if orphelins:
        codes = [r[0] for r in orphelins]
        raise RuntimeError(
            f"FK violée : {len(codes)} code_region absent(s) de geographies_regions : {codes}. "
            "Charger les régions d'abord."
        )

    codes = [
        r[0]
        for r in con.execute(
            "SELECT code_insee FROM geographies_departements ORDER BY code_insee"
        ).fetchall()
    ]
    logger.info("Chargé %d départements (codes : %s … %s)", count, codes[0], codes[-1])

    upsert_metadata(con, "geographies_departements", count, "ADMINEXPRESS-COG.LATEST")
