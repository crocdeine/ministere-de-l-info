"""Loader IGN — communes."""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from ministere_de_l_info.data_sources.geo import fetch_admin_express
from ministere_de_l_info.etl._common import upsert_metadata

logger = logging.getLogger(__name__)


def load_communes(
    con: duckdb.DuckDBPyConnection,
    raw_dir: Path,
    force: bool = False,
    skip: bool = False,
    yes: bool = False,
) -> None:
    """Charge les ~35 000 communes dans geographies_communes.

    Gate utilisateur avant téléchargement (durée estimée 30–60 min).
    code_epci : SPLIT_PART(codes_siren_des_epci, '/', 1) — le WFS expose un champ
    multi-valeur pour les communes à cheval sur MGP + EPT (Grand Paris).
    Après chargement, appeler update_epci_departement_principal() depuis epci.py.
    """
    if skip:
        logger.info("Chargement communes ignoré (--skip-communes).")
        return

    print(
        "\n⚠  Chargement communes (~35 000 lignes) — durée estimée 30–60 min.\n"
        "   Utilisez --skip-communes pour ignorer cette étape.\n"
    )
    if yes:
        logger.info("Gate communes bypassed (--yes).")
    else:
        try:
            reponse = input("Continuer ? [oui/non] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            logger.info("Chargement communes annulé (entrée non-interactive ou Ctrl-C).")
            return
        if reponse != "oui":
            logger.info("Chargement communes annulé par l'utilisateur.")
            return

    batch_paths = list(
        fetch_admin_express("commune", dom=True, force=force, batch_size=1000, raw_dir=raw_dir)
    )

    con.execute("DROP TABLE IF EXISTS geographies_communes")
    con.execute("""
        CREATE TABLE geographies_communes (
            code_insee                   VARCHAR(5) NOT NULL,
            nom                          VARCHAR    NOT NULL,
            code_departement             VARCHAR(3),
            code_region                  VARCHAR(3),
            code_epci                    VARCHAR(9),
            geometry                     GEOMETRY,
            geometry_simplified_communal GEOMETRY,
            UNIQUE (code_insee)
        )
    """)

    for batch_path in batch_paths:
        path_sql = str(batch_path).replace("'", "''")
        con.execute(f"""
            INSERT INTO geographies_communes
            SELECT
                code_insee,
                nom_officiel              AS nom,
                code_insee_du_departement AS code_departement,
                code_insee_de_la_region   AS code_region,
                SPLIT_PART(codes_siren_des_epci, '/', 1) AS code_epci,
                geom                      AS geometry,
                CASE
                    WHEN ST_IsValid(ST_Simplify(geom, 0.0005)) THEN ST_Simplify(geom, 0.0005)
                    ELSE geom
                END AS geometry_simplified_communal
            FROM ST_Read('{path_sql}')
        """)
        running = con.execute("SELECT COUNT(*) FROM geographies_communes").fetchone()[0]
        logger.info("Batch %s inséré — %d communes cumulées", batch_path.name, running)

    count = con.execute("SELECT COUNT(*) FROM geographies_communes").fetchone()[0]
    if not (34000 <= count <= 36000):
        raise RuntimeError(
            f"Nombre de communes hors fourchette [34000-36000] : {count}. "
            "Vérifier la source IGN ou utiliser --force pour re-télécharger."
        )
    logger.info("Chargé %d communes.", count)

    upsert_metadata(con, "geographies_communes", count, "ADMINEXPRESS-COG.LATEST")
