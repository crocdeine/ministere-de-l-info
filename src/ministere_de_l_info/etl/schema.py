"""Schéma DuckDB — tables métier, méta et version de schéma."""

from __future__ import annotations

import logging

import duckdb

logger = logging.getLogger(__name__)

_SCHEMA_VERSION = 1


def create_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Crée les 7 tables métier, 2 tables méta et les index UNIQUE.

    Idempotent : CREATE TABLE IF NOT EXISTS partout, jamais de DROP.
    geographies_regions existante (ancien schéma, colonne 'population') sera
    remplacée par le loader régions avec DROP + CREATE — pas ici.
    Les vues sont créées par create_views() après chargement des données.
    """
    # ── Tables géographiques ──────────────────────────────────────────────────
    con.execute("""
        CREATE TABLE IF NOT EXISTS geographies_regions (
            code_insee                   VARCHAR(3) NOT NULL,
            nom                          VARCHAR    NOT NULL,
            geometry                     GEOMETRY,
            geometry_simplified_national GEOMETRY,
            geometry_simplified_regional GEOMETRY,
            UNIQUE (code_insee)
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS geographies_departements (
            code_insee                        VARCHAR(3) NOT NULL,
            nom                               VARCHAR    NOT NULL,
            code_region                       VARCHAR(3),
            geometry                          GEOMETRY,
            geometry_simplified_national      GEOMETRY,
            geometry_simplified_departemental GEOMETRY,
            UNIQUE (code_insee)
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS geographies_epci (
            code_siren                 VARCHAR(9) NOT NULL,
            nom                        VARCHAR    NOT NULL,
            type_epci                  VARCHAR(5),
            code_departement_principal VARCHAR(3),
            geometry                   GEOMETRY,
            geometry_simplified_epci   GEOMETRY,
            UNIQUE (code_siren)
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS geographies_communes (
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

    con.execute("""
        CREATE TABLE IF NOT EXISTS geographies_arrondissements_municipaux (
            code_insee                   VARCHAR(5) NOT NULL,
            code_commune_mere            VARCHAR(5) NOT NULL,
            nom                          VARCHAR    NOT NULL,
            geometry                     GEOMETRY,
            geometry_simplified_communal GEOMETRY,
            UNIQUE (code_insee)
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS geographies_circonscriptions (
            code                      VARCHAR(6) NOT NULL,
            nom                       VARCHAR,
            code_departement          VARCHAR(3),
            nom_departement           VARCHAR,
            geometry                  GEOMETRY,
            geometry_simplified_circo GEOMETRY,
            UNIQUE (code)
        )
    """)

    # ── Table populations ─────────────────────────────────────────────────────
    con.execute("""
        CREATE TABLE IF NOT EXISTS populations (
            code_insee_commune VARCHAR(5) NOT NULL,
            annee              INTEGER    NOT NULL,
            municipale         INTEGER    NOT NULL,
            comptee_a_part     INTEGER,
            totale             INTEGER,
            source             VARCHAR    NOT NULL DEFAULT 'DS_POPULATIONS_HISTORIQUES'
        )
    """)
    con.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_populations_code_annee_source
            ON populations(code_insee_commune, annee, source)
    """)

    # ── Tables méta ──────────────────────────────────────────────────────────
    con.execute("""
        CREATE TABLE IF NOT EXISTS _etl_metadata (
            table_name     VARCHAR   NOT NULL,
            loaded_at      TIMESTAMP NOT NULL,
            source_version VARCHAR,
            row_count      INTEGER   NOT NULL,
            UNIQUE (table_name)
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS _schema_version (
            version    INTEGER   NOT NULL,
            applied_at TIMESTAMP NOT NULL
        )
    """)
    con.execute(
        """
        INSERT INTO _schema_version (version, applied_at)
        SELECT ?, NOW()
        WHERE (SELECT COUNT(*) FROM _schema_version) = 0
        """,
        [_SCHEMA_VERSION],
    )

    logger.info("Schéma v%d créé/vérifié : 9 tables (7 métier + 2 méta)", _SCHEMA_VERSION)
