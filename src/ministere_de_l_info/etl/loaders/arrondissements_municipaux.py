"""Loader IGN — arrondissements municipaux."""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from ministere_de_l_info.data_sources.geo import fetch_admin_express
from ministere_de_l_info.etl._common import upsert_metadata

logger = logging.getLogger(__name__)

_MERES_ATTENDUES = {"75056", "69123", "13055"}
_SPOT_CODES = {"75101", "75120", "69381", "69389", "13201", "13216"}


def load_arrondissements_municipaux(
    con: duckdb.DuckDBPyConnection,
    raw_dir: Path,
    force: bool = False,
) -> None:
    """Charge les 45 arrondissements municipaux (Paris 20, Lyon 9, Marseille 16).

    Les ARM ne sont PAS des communes INSEE : les communes-mères (75056, 69123, 13055)
    restent les entités juridiques.
    """
    batch_paths = list(
        fetch_admin_express(
            "arrondissement_municipal",
            dom=True,
            force=force,
            batch_size=500,
            raw_dir=raw_dir,
        )
    )

    con.execute("DROP TABLE IF EXISTS geographies_arrondissements_municipaux")
    con.execute("""
        CREATE TABLE geographies_arrondissements_municipaux (
            code_insee                   VARCHAR(5) NOT NULL,
            code_commune_mere            VARCHAR(5) NOT NULL,
            nom                          VARCHAR    NOT NULL,
            geometry                     GEOMETRY,
            geometry_simplified_communal GEOMETRY,
            UNIQUE (code_insee)
        )
    """)

    for batch_path in batch_paths:
        path_sql = str(batch_path).replace("'", "''")
        con.execute(f"""
            INSERT INTO geographies_arrondissements_municipaux
            SELECT
                code_insee,
                code_insee_de_la_commune_de_rattach AS code_commune_mere,
                nom_officiel                        AS nom,
                geom                                AS geometry,
                CASE
                    WHEN ST_IsValid(ST_Simplify(geom, 0.0005)) THEN ST_Simplify(geom, 0.0005)
                    ELSE geom
                END AS geometry_simplified_communal
            FROM ST_Read('{path_sql}')
        """)

    count = con.execute("SELECT COUNT(*) FROM geographies_arrondissements_municipaux").fetchone()[0]
    if count != 45:
        raise RuntimeError(
            f"Nombre d'arrondissements incorrect : {count} (attendu 45 = Paris 20 + Lyon 9 + Marseille 16). "
            "Utiliser --force pour re-télécharger si le cache est corrompu."
        )

    nulls = con.execute(
        "SELECT COUNT(*) FROM geographies_arrondissements_municipaux WHERE code_commune_mere IS NULL"
    ).fetchone()[0]
    if nulls > 0:
        raise RuntimeError(f"{nulls} ARM avec code_commune_mere NULL — vérifier le WFS IGN.")

    meres = {
        r[0]
        for r in con.execute(
            "SELECT DISTINCT code_commune_mere FROM geographies_arrondissements_municipaux"
        ).fetchall()
    }
    if meres != _MERES_ATTENDUES:
        raise RuntimeError(f"Communes-mères inattendues : {meres} (attendu {_MERES_ATTENDUES}).")

    presents = {
        r[0]
        for r in con.execute(
            "SELECT code_insee FROM geographies_arrondissements_municipaux "
            "WHERE code_insee IN ('75101','75120','69381','69389','13201','13216')"
        ).fetchall()
    }
    manquants = _SPOT_CODES - presents
    if manquants:
        raise RuntimeError(f"Codes ARM spot-check manquants : {manquants}.")

    logger.info(
        "Chargé %d ARM — Paris %d, Lyon %d, Marseille %d.",
        count,
        con.execute(
            "SELECT COUNT(*) FROM geographies_arrondissements_municipaux WHERE code_commune_mere = '75056'"
        ).fetchone()[0],
        con.execute(
            "SELECT COUNT(*) FROM geographies_arrondissements_municipaux WHERE code_commune_mere = '69123'"
        ).fetchone()[0],
        con.execute(
            "SELECT COUNT(*) FROM geographies_arrondissements_municipaux WHERE code_commune_mere = '13055'"
        ).fetchone()[0],
    )

    upsert_metadata(con, "geographies_arrondissements_municipaux", count, "ADMINEXPRESS-COG.LATEST")
