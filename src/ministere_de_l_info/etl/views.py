"""Vues SQL d'agrégation population → territoire."""

from __future__ import annotations

import logging

import duckdb

logger = logging.getLogger(__name__)


def create_views(con: duckdb.DuckDBPyConnection) -> None:
    """Crée les 4 vues d'agrégation population → territoire.

    Appelée après tous les loaders : dépend de geographies_communes + populations.
    SUM(comptee_a_part) et SUM(totale) retournent NULL tant que PCAP absent.

    Vues :
        v_population_commune     — alias direct populations (1 ligne/commune/an)
        v_population_region      — SUM par code_region
        v_population_departement — SUM par code_departement
        v_population_epci        — SUM par code_epci (communes avec EPCI uniquement)
    """
    con.execute("""
        CREATE OR REPLACE VIEW v_population_commune AS
        SELECT
            code_insee_commune AS code_commune,
            annee,
            SUM(municipale)         AS population_municipale,
            SUM(comptee_a_part)     AS population_comptee_a_part,
            SUM(totale)             AS population_totale
        FROM populations
        GROUP BY code_insee_commune, annee
    """)

    con.execute("""
        CREATE OR REPLACE VIEW v_population_region AS
        SELECT
            r.code_insee          AS code_region,
            r.nom                 AS nom_region,
            p.annee,
            SUM(p.municipale)         AS population_municipale,
            SUM(p.comptee_a_part)     AS population_comptee_a_part,
            SUM(p.totale)             AS population_totale
        FROM geographies_communes c
        JOIN populations p ON p.code_insee_commune = c.code_insee
        JOIN geographies_regions r ON r.code_insee = c.code_region
        GROUP BY r.code_insee, r.nom, p.annee
    """)

    con.execute("""
        CREATE OR REPLACE VIEW v_population_departement AS
        SELECT
            d.code_insee          AS code_departement,
            d.nom                 AS nom_departement,
            p.annee,
            SUM(p.municipale)         AS population_municipale,
            SUM(p.comptee_a_part)     AS population_comptee_a_part,
            SUM(p.totale)             AS population_totale
        FROM geographies_communes c
        JOIN populations p ON p.code_insee_commune = c.code_insee
        JOIN geographies_departements d ON d.code_insee = c.code_departement
        GROUP BY d.code_insee, d.nom, p.annee
    """)

    con.execute("""
        CREATE OR REPLACE VIEW v_population_epci AS
        SELECT
            e.code_siren          AS code_epci,
            e.nom                 AS nom_epci,
            e.type_epci,
            p.annee,
            SUM(p.municipale)         AS population_municipale,
            SUM(p.comptee_a_part)     AS population_comptee_a_part,
            SUM(p.totale)             AS population_totale
        FROM geographies_communes c
        JOIN populations p ON p.code_insee_commune = c.code_insee
        JOIN geographies_epci e ON e.code_siren = c.code_epci
        WHERE c.code_epci IS NOT NULL
        GROUP BY e.code_siren, e.nom, e.type_epci, p.annee
    """)

    logger.info(
        "4 vues créées : v_population_commune, v_population_region, "
        "v_population_departement, v_population_epci."
    )
