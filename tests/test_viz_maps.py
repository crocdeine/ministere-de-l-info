"""Tests pour src/ministere_de_l_info/viz/maps.py."""

from __future__ import annotations

import logging

import duckdb
import folium
import pytest

from ministere_de_l_info.viz.maps import make_choropleth

# Polygone WGS84 minimaliste centré sur l'Île-de-France
_WKT = "POLYGON((2.0 48.0, 3.0 48.0, 3.0 49.0, 2.0 49.0, 2.0 48.0))"
_WKT2 = "POLYGON((1.0 47.0, 2.0 47.0, 2.0 48.0, 1.0 48.0, 1.0 47.0))"


def _make_db() -> duckdb.DuckDBPyConnection:
    db = duckdb.connect(":memory:")
    db.execute("INSTALL spatial; LOAD spatial;")
    return db


def _create_tables(db: duckdb.DuckDBPyConnection) -> None:
    db.execute(f"""
        CREATE TABLE geographies_regions (
            code_insee VARCHAR, nom VARCHAR,
            geometry GEOMETRY,
            geometry_simplified_national GEOMETRY,
            geometry_simplified_regional GEOMETRY
        );
        INSERT INTO geographies_regions VALUES
            ('11', 'Île-de-France',
             ST_GeomFromText('{_WKT}'), ST_GeomFromText('{_WKT}'), ST_GeomFromText('{_WKT}')),
            ('84', 'Auvergne-Rhône-Alpes',
             ST_GeomFromText('{_WKT2}'), ST_GeomFromText('{_WKT2}'), ST_GeomFromText('{_WKT2}'));
    """)
    db.execute(f"""
        CREATE TABLE geographies_departements (
            code_insee VARCHAR, code_region VARCHAR, nom VARCHAR,
            geometry GEOMETRY,
            geometry_simplified_national GEOMETRY,
            geometry_simplified_departemental GEOMETRY
        );
        INSERT INTO geographies_departements VALUES
            ('75', '11', 'Paris',
             ST_GeomFromText('{_WKT}'), ST_GeomFromText('{_WKT}'), ST_GeomFromText('{_WKT}'));
    """)
    db.execute(f"""
        CREATE TABLE geographies_epci (
            code_siren VARCHAR, nom VARCHAR, type_epci VARCHAR,
            code_departement_principal VARCHAR,
            geometry GEOMETRY,
            geometry_simplified_epci GEOMETRY
        );
        INSERT INTO geographies_epci VALUES
            ('200054781', 'Métropole du Grand Paris', 'METRO', '75',
             ST_GeomFromText('{_WKT}'), ST_GeomFromText('{_WKT}'));
    """)
    db.execute(f"""
        CREATE TABLE geographies_arrondissements_municipaux (
            code_insee VARCHAR, code_commune_mere VARCHAR, nom VARCHAR,
            geometry GEOMETRY,
            geometry_simplified_communal GEOMETRY
        );
        INSERT INTO geographies_arrondissements_municipaux VALUES
            ('75101', '75056', 'Paris 1er Arrondissement',
             ST_GeomFromText('{_WKT}'), ST_GeomFromText('{_WKT}'));
    """)
    db.execute(f"""
        CREATE TABLE geographies_circonscriptions (
            code VARCHAR, nom VARCHAR,
            code_departement VARCHAR, nom_departement VARCHAR,
            geometry GEOMETRY,
            geometry_simplified_circo GEOMETRY
        );
        INSERT INTO geographies_circonscriptions VALUES
            ('7501', 'Paris - 1re circonscription', '75', 'Paris',
             ST_GeomFromText('{_WKT}'), ST_GeomFromText('{_WKT}'));
    """)
    db.execute(f"""
        CREATE TABLE geographies_communes (
            code_insee VARCHAR, nom VARCHAR,
            code_departement VARCHAR, code_region VARCHAR, code_epci VARCHAR,
            geometry GEOMETRY,
            geometry_simplified_communal GEOMETRY
        );
        INSERT INTO geographies_communes VALUES
            ('75056', 'Paris', '75', '11', '200054781',
             ST_GeomFromText('{_WKT}'), ST_GeomFromText('{_WKT}'));
    """)
    db.execute("""
        CREATE TABLE populations (
            code_insee_commune VARCHAR, annee INTEGER,
            municipale INTEGER, comptee_a_part INTEGER, totale INTEGER,
            source VARCHAR
        );
    """)


def _create_views(db: duckdb.DuckDBPyConnection) -> None:
    db.execute("""
        CREATE VIEW v_population_region AS
        SELECT r.code_insee AS code_region, r.nom AS nom_region, p.annee,
               SUM(p.municipale) AS population_municipale,
               SUM(p.comptee_a_part) AS population_comptee_a_part,
               SUM(p.totale) AS population_totale
        FROM geographies_communes c
        JOIN populations p ON p.code_insee_commune = c.code_insee
        JOIN geographies_regions r ON r.code_insee = c.code_region
        GROUP BY r.code_insee, r.nom, p.annee;
    """)
    db.execute("""
        CREATE VIEW v_population_departement AS
        SELECT d.code_insee AS code_departement, d.nom AS nom_departement, p.annee,
               SUM(p.municipale) AS population_municipale,
               SUM(p.comptee_a_part) AS population_comptee_a_part,
               SUM(p.totale) AS population_totale
        FROM geographies_communes c
        JOIN populations p ON p.code_insee_commune = c.code_insee
        JOIN geographies_departements d ON d.code_insee = c.code_departement
        GROUP BY d.code_insee, d.nom, p.annee;
    """)
    db.execute("""
        CREATE VIEW v_population_epci AS
        SELECT e.code_siren AS code_epci, e.nom AS nom_epci, e.type_epci, p.annee,
               SUM(p.municipale) AS population_municipale,
               SUM(p.comptee_a_part) AS population_comptee_a_part,
               SUM(p.totale) AS population_totale
        FROM geographies_communes c
        JOIN populations p ON p.code_insee_commune = c.code_insee
        JOIN geographies_epci e ON e.code_siren = c.code_epci
        WHERE c.code_epci IS NOT NULL
        GROUP BY e.code_siren, e.nom, e.type_epci, p.annee;
    """)


def _insert_populations(db: duckdb.DuckDBPyConnection, annee: int = 2023) -> None:
    db.execute(
        "INSERT INTO populations VALUES (?, ?, ?, ?, ?, ?)",
        ["75056", annee, 2_145_906, 0, 2_145_906, "test"],
    )


@pytest.fixture
def con_no_pop():
    """Connexion avec tables géographiques mais sans données population."""
    db = _make_db()
    _create_tables(db)
    _create_views(db)
    yield db
    db.close()


@pytest.fixture
def con_full():
    """Connexion avec toutes les tables et données population pour 2023."""
    db = _make_db()
    _create_tables(db)
    _create_views(db)
    _insert_populations(db, annee=2023)
    yield db
    db.close()


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_make_choropleth_region_returns_folium_map(con_full):
    result = make_choropleth(con_full, "region")
    assert isinstance(result, folium.Map)


def test_make_choropleth_invalid_niveau(con_no_pop):
    with pytest.raises(ValueError, match="Niveau 'pays' invalide"):
        make_choropleth(con_no_pop, "pays")


def test_make_choropleth_commune_sans_filtre_dept(con_no_pop):
    with pytest.raises(ValueError, match="filtre_departement est obligatoire"):
        make_choropleth(con_no_pop, "commune")


def test_make_choropleth_fallback_contours_when_no_populations(con_no_pop, caplog):
    """mode='auto' + aucune donnée population → contours + warning logger."""
    with caplog.at_level(logging.WARNING, logger="ministere_de_l_info.viz.maps"):
        result = make_choropleth(con_no_pop, "region", mode="auto")

    assert isinstance(result, folium.Map)
    assert any(
        "fallback" in msg.lower() or "contours" in msg.lower()
        for msg in caplog.messages
    )


def test_make_choropleth_mode_choropleth_force_raises_if_no_data(con_no_pop):
    """mode='choropleth' forcé sans données → ValueError explicite."""
    with pytest.raises(ValueError, match="Aucune donnée population"):
        make_choropleth(con_no_pop, "region", mode="choropleth")


def test_make_choropleth_arm_auto_contours(con_no_pop, caplog):
    """ARM avec mode='auto' → contours sans warning (comportement normal pour ce niveau)."""
    with caplog.at_level(logging.WARNING, logger="ministere_de_l_info.viz.maps"):
        result = make_choropleth(con_no_pop, "arrondissement_municipal", mode="auto")

    assert isinstance(result, folium.Map)
    # Pas de warning : ARM en contours est le comportement attendu, pas un fallback
    assert not any("fallback" in msg.lower() for msg in caplog.messages)


def test_make_choropleth_circo_mode_choropleth_raises(con_no_pop):
    """Circonscription + mode='choropleth' forcé → ValueError."""
    with pytest.raises(ValueError, match="ne supporte pas le mode choropleth"):
        make_choropleth(con_no_pop, "circonscription", mode="choropleth")


def test_make_choropleth_mode_contours_force_no_population_needed(con_no_pop):
    """mode='contours' forcé pour un niveau population → aucune erreur, pas de choropleth."""
    result = make_choropleth(con_no_pop, "region", mode="contours")
    assert isinstance(result, folium.Map)
