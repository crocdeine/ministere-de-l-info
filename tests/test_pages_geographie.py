"""Tests de la logique métier de pages/1_📍_Géographie.py.

On ne teste pas l'UI Streamlit (impossible sans serveur), mais les requêtes SQL
et la logique de configuration des filtres qui sous-tendent la page.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

_DB_PATH = Path(__file__).parent.parent / "data" / "ministere.duckdb"


@pytest.fixture(scope="module")
def con():
    """Connexion read_only sur la vraie base — skip si absente."""
    if not _DB_PATH.exists():
        pytest.skip("Base de données absente — ETL non lancé.")
    db = duckdb.connect(str(_DB_PATH), read_only=True)
    db.execute("LOAD spatial;")
    yield db
    db.close()


# ── Connexion & accès de base ──────────────────────────────────────────────────


def test_connection_read_only(con):
    """La connexion read_only s'ouvre et répond."""
    result = con.execute("SELECT 1 AS ok").fetchone()
    assert result[0] == 1


def test_populations_query(con):
    """La requête des millésimes disponibles renvoie une liste (vide ou non)."""
    rows = con.execute(
        "SELECT DISTINCT annee FROM populations ORDER BY annee DESC"
    ).fetchall()
    assert isinstance(rows, list)


def test_departements_query(con):
    """La requête du sélecteur département renvoie 101 lignes."""
    rows = con.execute(
        "SELECT code_insee, nom FROM geographies_departements ORDER BY code_insee"
    ).fetchall()
    assert len(rows) == 101
    codes = [r[0] for r in rows]
    assert "75" in codes
    assert "2A" in codes
    assert "971" in codes


def test_regions_query(con):
    """La requête du sélecteur région renvoie 18 lignes (13 métro + 5 DROM)."""
    rows = con.execute(
        "SELECT code_insee, nom FROM geographies_regions ORDER BY nom"
    ).fetchall()
    assert len(rows) == 18


def test_etl_metadata_query(con):
    """La table _etl_metadata contient des entrées pour les tables principales."""
    tables_avec_meta = {
        r[0] for r in con.execute("SELECT table_name FROM _etl_metadata").fetchall()
    }
    for expected in [
        "geographies_regions",
        "geographies_departements",
        "geographies_epci",
    ]:
        assert expected in tables_avec_meta, f"{expected} absent de _etl_metadata"


# ── Requêtes tableau de données ────────────────────────────────────────────────


def test_tableau_region_query(con):
    """Le tableau régions via v_population_region ne plante pas (peut être vide)."""
    rows = con.execute("""
        SELECT g.code_insee AS code, g.nom,
               COALESCE(p.population_municipale, 0) AS pop
        FROM geographies_regions g
        LEFT JOIN v_population_region p
          ON g.code_insee = p.code_region AND p.annee = 2023
        ORDER BY pop DESC NULLS LAST LIMIT 200
    """).fetchall()
    assert len(rows) == 18
    assert rows[0][0] is not None  # code présent


def test_tableau_arm_query(con):
    """Le tableau ARM (sans population) renvoie 45 lignes."""
    rows = con.execute("""
        SELECT code_insee, nom, code_commune_mere
        FROM geographies_arrondissements_municipaux
        ORDER BY code_insee LIMIT 200
    """).fetchall()
    assert len(rows) == 45


def test_tableau_circo_query(con):
    """Le tableau circonscriptions renvoie 559 lignes."""
    rows = con.execute("""
        SELECT code, nom, code_departement
        FROM geographies_circonscriptions
        ORDER BY code LIMIT 600
    """).fetchall()
    assert len(rows) == 559


def test_tableau_departement_filtre_region(con):
    """Filtre région sur les départements renvoie un sous-ensemble cohérent."""
    rows = con.execute("""
        SELECT g.code_insee, g.nom
        FROM geographies_departements g
        WHERE g.code_region = '11'
        ORDER BY g.code_insee
    """).fetchall()
    # Île-de-France a 8 départements
    assert len(rows) == 8
    assert all(r[0] in ("75", "77", "78", "91", "92", "93", "94", "95") for r in rows)
