"""Tests smoke — ETL territorial DuckDB (scripts/etl_territoires.py).

Prérequis : lancer au moins une fois :
    uv run python scripts/etl_territoires.py --level region
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "ministere.duckdb"

_CODES_REGION_METRO = {
    "11",
    "24",
    "27",
    "28",
    "32",
    "44",
    "52",
    "53",
    "75",
    "76",
    "84",
    "93",
    "94",
}
_CODES_REGION_DROM = {"01", "02", "03", "04", "06"}
_CODES_REGION_TOUS = _CODES_REGION_METRO | _CODES_REGION_DROM


@pytest.fixture(scope="module")
def con() -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        pytest.skip("ministere.duckdb introuvable — lancer etl_territoires.py d'abord")
    c = duckdb.connect(str(DB_PATH))
    c.execute("LOAD spatial")
    yield c
    c.close()


# ── Régions ───────────────────────────────────────────────────────────────────


def test_regions_count(con: duckdb.DuckDBPyConnection) -> None:
    """13 (métro seule) ou 18 (avec DROM) régions chargées."""
    n = con.execute("SELECT COUNT(*) FROM geographies_regions").fetchone()[0]
    assert 13 <= n <= 20, f"Nombre de régions hors fourchette [13-20] : {n}"


def test_regions_codes_format(con: duckdb.DuckDBPyConnection) -> None:
    """Tous les codes région appartiennent à la liste officielle IGN."""
    codes = {
        r[0]
        for r in con.execute("SELECT code_insee FROM geographies_regions").fetchall()
    }
    inconnus = codes - _CODES_REGION_TOUS
    assert not inconnus, f"Codes région inconnus : {inconnus}"
    metro_presents = codes & _CODES_REGION_METRO
    assert len(metro_presents) == 13, (
        f"Seulement {len(metro_presents)}/13 régions métro présentes"
    )


def test_regions_geometries_valides(con: duckdb.DuckDBPyConnection) -> None:
    """Aucune géométrie simplifiée invalide (ST_IsValid)."""
    invalides = con.execute("""
        SELECT code_insee FROM geographies_regions
        WHERE geometry_simplified_national IS NOT NULL
          AND NOT ST_IsValid(geometry_simplified_national)
    """).fetchall()
    assert not invalides, (
        f"Géométries simplifiées invalides : {[r[0] for r in invalides]}"
    )


def test_regions_metadata(con: duckdb.DuckDBPyConnection) -> None:
    """Entrée geographies_regions présente dans _etl_metadata avec row_count cohérent."""
    row = con.execute(
        "SELECT row_count FROM _etl_metadata WHERE table_name = 'geographies_regions'"
    ).fetchone()
    assert row is not None, (
        "Entrée manquante dans _etl_metadata pour geographies_regions"
    )
    count_table = con.execute("SELECT COUNT(*) FROM geographies_regions").fetchone()[0]
    assert row[0] == count_table, (
        f"row_count _etl_metadata ({row[0]}) ≠ COUNT(*) table ({count_table})"
    )


# ── Départements ──────────────────────────────────────────────────────────────

_CODES_DEPT_SPOT = {"01", "2A", "2B", "75", "95", "971", "972", "973", "974", "976"}
_CODES_DEPT_ABSENTS = {"975"}  # Saint-Pierre-et-Miquelon — COM, pas dans ADMIN-EXPRESS


def test_departements_count(con: duckdb.DuckDBPyConnection) -> None:
    """Exactement 101 départements chargés (96 métro + 5 DROM)."""
    n = con.execute("SELECT COUNT(*) FROM geographies_departements").fetchone()[0]
    assert n == 101, f"Attendu exactement 101 départements, obtenu {n}"


def test_departements_codes(con: duckdb.DuckDBPyConnection) -> None:
    """Codes spot-check : présence 2A/2B/DROM, absence 975 (COM)."""
    codes = {
        r[0]
        for r in con.execute(
            "SELECT code_insee FROM geographies_departements"
        ).fetchall()
    }
    manquants = _CODES_DEPT_SPOT - codes
    assert not manquants, f"Codes attendus manquants : {manquants}"
    indesirables = _CODES_DEPT_ABSENTS & codes
    assert not indesirables, f"Codes indésirables présents : {indesirables}"


def test_departements_fk_region(con: duckdb.DuckDBPyConnection) -> None:
    """Tous les code_region référencent une région présente dans geographies_regions."""
    orphelins = con.execute("""
        SELECT DISTINCT d.code_region
        FROM geographies_departements d
        WHERE d.code_region NOT IN (SELECT code_insee FROM geographies_regions)
    """).fetchall()
    assert not orphelins, f"code_region orphelins : {[r[0] for r in orphelins]}"


def test_departements_geometries_valides(con: duckdb.DuckDBPyConnection) -> None:
    """Aucune géométrie simplifiée invalide sur les 2 niveaux."""
    for col in ("geometry_simplified_national", "geometry_simplified_departemental"):
        invalides = con.execute(f"""
            SELECT code_insee FROM geographies_departements
            WHERE {col} IS NOT NULL AND NOT ST_IsValid({col})
        """).fetchall()
        assert not invalides, (
            f"{col} — géométries invalides : {[r[0] for r in invalides]}"
        )


# ── EPCI ──────────────────────────────────────────────────────────────────────

_TYPES_EPCI_ATTENDUS = {"CC": 989, "CA": 229, "ME": 22, "CU": 14, "EPT": 11}
_TOLERANCE_TYPES = 10


def test_epci_count(con: duckdb.DuckDBPyConnection) -> None:
    """Entre 1 250 et 1 290 EPCI chargés."""
    n = con.execute("SELECT COUNT(*) FROM geographies_epci").fetchone()[0]
    assert 1250 <= n <= 1290, f"Nombre d'EPCI hors fourchette [1250-1290] : {n}"


def test_epci_siren_format(con: duckdb.DuckDBPyConnection) -> None:
    """Tous les SIREN sont exactement 9 chiffres numériques."""
    invalides = con.execute("""
        SELECT code_siren FROM geographies_epci
        WHERE length(code_siren) != 9 OR regexp_full_match(code_siren, '[^0-9]')
    """).fetchall()
    assert not invalides, f"SIREN non conformes : {[r[0] for r in invalides[:10]]}"


def test_epci_no_null_types(con: duckdb.DuckDBPyConnection) -> None:
    """Aucun type_epci NULL — toutes les valeurs 'nature' WFS sont mappées."""
    n = con.execute(
        "SELECT COUNT(*) FROM geographies_epci WHERE type_epci IS NULL"
    ).fetchone()[0]
    assert n == 0, (
        f"{n} EPCI avec type_epci NULL — une valeur 'nature' WFS non mappée est apparue"
    )


def test_epci_types_distribution(con: duckdb.DuckDBPyConnection) -> None:
    """Distribution des types EPCI cohérente avec les valeurs IGN 2026-05-17 (±10)."""
    dist = {
        r[0]: r[1]
        for r in con.execute(
            "SELECT type_epci, COUNT(*) FROM geographies_epci GROUP BY type_epci"
        ).fetchall()
    }
    for type_code, expected in _TYPES_EPCI_ATTENDUS.items():
        actual = dist.get(type_code, 0)
        assert abs(actual - expected) <= _TOLERANCE_TYPES, (
            f"type_epci={type_code!r} : attendu ≈{expected} (±{_TOLERANCE_TYPES}), obtenu {actual}"
        )


def test_epci_geometries_valides(con: duckdb.DuckDBPyConnection) -> None:
    """Aucune géométrie simplifiée invalide (ST_IsValid)."""
    invalides = con.execute("""
        SELECT code_siren FROM geographies_epci
        WHERE geometry_simplified_epci IS NOT NULL
          AND NOT ST_IsValid(geometry_simplified_epci)
    """).fetchall()
    assert not invalides, (
        f"Géométries simplifiées invalides : {[r[0] for r in invalides]}"
    )


def test_epci_metadata(con: duckdb.DuckDBPyConnection) -> None:
    """Entrée geographies_epci présente dans _etl_metadata avec row_count cohérent."""
    row = con.execute(
        "SELECT row_count FROM _etl_metadata WHERE table_name = 'geographies_epci'"
    ).fetchone()
    assert row is not None, "Entrée manquante dans _etl_metadata pour geographies_epci"
    count_table = con.execute("SELECT COUNT(*) FROM geographies_epci").fetchone()[0]
    assert row[0] == count_table, (
        f"row_count _etl_metadata ({row[0]}) ≠ COUNT(*) table ({count_table})"
    )
