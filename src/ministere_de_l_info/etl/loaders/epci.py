"""Loader IGN — EPCI."""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from ministere_de_l_info.data_sources.geo import fetch_admin_express
from ministere_de_l_info.etl._common import upsert_metadata

logger = logging.getLogger(__name__)


def load_epci(
    con: duckdb.DuckDBPyConnection,
    raw_dir: Path,
    force: bool = False,
) -> None:
    """Charge les ~1 250 EPCI dans geographies_epci.

    dom=True ignoré côté WFS (codes_insee_des_departements_membres multi-valeurs,
    filtre CQL impossible).
    code_departement_principal : NULL à ce stade — dérivé via
    update_epci_departement_principal() après load_communes().
    """
    batch_paths = list(
        fetch_admin_express("epci", dom=True, force=force, batch_size=500, raw_dir=raw_dir)
    )

    con.execute("DROP TABLE IF EXISTS geographies_epci")
    con.execute("""
        CREATE TABLE geographies_epci (
            code_siren                 VARCHAR(9) NOT NULL,
            nom                        VARCHAR    NOT NULL,
            type_epci                  VARCHAR(5),
            code_departement_principal VARCHAR(3),
            geometry                   GEOMETRY,
            geometry_simplified_epci   GEOMETRY,
            UNIQUE (code_siren)
        )
    """)

    for batch_path in batch_paths:
        path_sql = str(batch_path).replace("'", "''")
        con.execute(f"""
            INSERT INTO geographies_epci
            SELECT
                code_siren,
                nom_officiel AS nom,
                CASE nature
                    WHEN 'Communauté de communes'          THEN 'CC'
                    WHEN 'Communauté d''agglomération'     THEN 'CA'
                    WHEN 'Métropole'                       THEN 'ME'
                    WHEN 'Communauté urbaine'              THEN 'CU'
                    WHEN 'Etablissement public territorial' THEN 'EPT'
                    ELSE NULL
                END AS type_epci,
                NULL::VARCHAR AS code_departement_principal,
                geom AS geometry,
                CASE
                    WHEN ST_IsValid(ST_Simplify(geom, 0.0005)) THEN ST_Simplify(geom, 0.0005)
                    ELSE geom
                END AS geometry_simplified_epci
            FROM ST_Read('{path_sql}')
        """)
        logger.debug("Batch inséré : %s", batch_path.name)

    count = con.execute("SELECT COUNT(*) FROM geographies_epci").fetchone()[0]
    if not (1250 <= count <= 1290):
        raise RuntimeError(
            f"Nombre d'EPCI hors fourchette [1250-1290] : {count}. "
            "Vérifier la source IGN ou utiliser --force pour re-télécharger."
        )

    null_types = con.execute(
        "SELECT COUNT(*) FROM geographies_epci WHERE type_epci IS NULL"
    ).fetchone()[0]
    if null_types > 0:
        raise RuntimeError(
            f"{null_types} EPCI avec type_epci NULL — une nouvelle valeur 'nature' "
            "non mappée est apparue dans le WFS IGN. "
            "Ajouter la valeur manquante dans le CASE WHEN de load_epci()."
        )

    mauvais_siren = con.execute("""
        SELECT code_siren FROM geographies_epci
        WHERE length(code_siren) != 9 OR regexp_full_match(code_siren, '[^0-9]')
    """).fetchall()
    if mauvais_siren:
        raise RuntimeError(
            f"SIREN non conformes (attendu 9 chiffres) : {[r[0] for r in mauvais_siren[:10]]}"
        )

    dist = con.execute(
        "SELECT type_epci, COUNT(*) FROM geographies_epci GROUP BY type_epci ORDER BY COUNT(*) DESC"
    ).fetchall()
    logger.info(
        "Chargé %d EPCI — distribution types : %s",
        count,
        ", ".join(f"{t}={n}" for t, n in dist),
    )

    upsert_metadata(con, "geographies_epci", count, "ADMINEXPRESS-COG.LATEST")


def update_epci_departement_principal(con: duckdb.DuckDBPyConnection) -> None:
    """Dérive code_departement_principal des EPCI depuis geographies_communes.

    Doit être appelé après load_epci() ET load_communes().
    Stratégie : département le plus fréquent parmi les communes membres de l'EPCI.
    """
    con.execute("""
        UPDATE geographies_epci
        SET code_departement_principal = (
            SELECT c.code_departement
            FROM geographies_communes c
            WHERE c.code_epci = geographies_epci.code_siren
              AND c.code_departement IS NOT NULL
            GROUP BY c.code_departement
            ORDER BY COUNT(*) DESC
            LIMIT 1
        )
    """)
    updated = con.execute(
        "SELECT COUNT(*) FROM geographies_epci WHERE code_departement_principal IS NOT NULL"
    ).fetchone()[0]
    logger.info("code_departement_principal renseigné pour %d EPCI.", updated)
