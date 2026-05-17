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


# ── Arrondissements municipaux ────────────────────────────────────────────────

_ARM_SPOT_CODES = {"75101", "75120", "69381", "69389", "13201", "13216"}
_ARM_COMMUNES_MERES = {"75056", "69123", "13055"}
_ARM_COUNTS = {"75056": 20, "69123": 9, "13055": 16}


@pytest.fixture(scope="module")
def arm_skip(con: duckdb.DuckDBPyConnection) -> None:
    """Passe les tests ARM si la table n'a pas encore été chargée."""
    try:
        con.execute("SELECT 1 FROM geographies_arrondissements_municipaux LIMIT 1")
    except Exception:
        pytest.skip(
            "geographies_arrondissements_municipaux introuvable — "
            "lancer etl_territoires.py --level arrondissement_municipal d'abord"
        )


def test_arm_count(con: duckdb.DuckDBPyConnection, arm_skip: None) -> None:
    """Exactement 45 ARM chargés (Paris 20 + Lyon 9 + Marseille 16)."""
    n = con.execute(
        "SELECT COUNT(*) FROM geographies_arrondissements_municipaux"
    ).fetchone()[0]
    assert n == 45, f"Attendu exactement 45 ARM, obtenu {n}"


def test_arm_counts_par_ville(con: duckdb.DuckDBPyConnection, arm_skip: None) -> None:
    """20 Paris, 9 Lyon, 16 Marseille."""
    dist = {
        r[0]: r[1]
        for r in con.execute("""
            SELECT code_commune_mere, COUNT(*)
            FROM geographies_arrondissements_municipaux
            GROUP BY code_commune_mere
        """).fetchall()
    }
    for mere, expected in _ARM_COUNTS.items():
        assert dist.get(mere) == expected, (
            f"Commune-mère {mere} : attendu {expected} ARM, obtenu {dist.get(mere)}"
        )


def test_arm_codes_spot(con: duckdb.DuckDBPyConnection, arm_skip: None) -> None:
    """Présence des codes limites : 75101, 75120, 69381, 69389, 13201, 13216."""
    presents = {
        r[0]
        for r in con.execute("""
            SELECT code_insee FROM geographies_arrondissements_municipaux
            WHERE code_insee IN ('75101','75120','69381','69389','13201','13216')
        """).fetchall()
    }
    manquants = _ARM_SPOT_CODES - presents
    assert not manquants, f"Codes ARM manquants : {manquants}"


def test_arm_communes_meres(con: duckdb.DuckDBPyConnection, arm_skip: None) -> None:
    """Exactement 3 communes-mères distinctes : 75056, 69123, 13055."""
    meres = {
        r[0]
        for r in con.execute(
            "SELECT DISTINCT code_commune_mere FROM geographies_arrondissements_municipaux"
        ).fetchall()
    }
    assert meres == _ARM_COMMUNES_MERES, (
        f"Communes-mères inattendues : {meres} (attendu {_ARM_COMMUNES_MERES})"
    )


def test_arm_no_null_commune_mere(
    con: duckdb.DuckDBPyConnection, arm_skip: None
) -> None:
    """Aucun code_commune_mere NULL."""
    n = con.execute(
        "SELECT COUNT(*) FROM geographies_arrondissements_municipaux WHERE code_commune_mere IS NULL"
    ).fetchone()[0]
    assert n == 0, f"{n} ARM avec code_commune_mere NULL"


def test_arm_geometries_valides(con: duckdb.DuckDBPyConnection, arm_skip: None) -> None:
    """Aucune géométrie simplifiée invalide (ST_IsValid)."""
    invalides = con.execute("""
        SELECT code_insee FROM geographies_arrondissements_municipaux
        WHERE geometry_simplified_communal IS NOT NULL
          AND NOT ST_IsValid(geometry_simplified_communal)
    """).fetchall()
    assert not invalides, f"Géométries ARM invalides : {[r[0] for r in invalides]}"


def test_arm_metadata(con: duckdb.DuckDBPyConnection, arm_skip: None) -> None:
    """Entrée _etl_metadata présente avec row_count == 45."""
    row = con.execute(
        "SELECT row_count FROM _etl_metadata "
        "WHERE table_name = 'geographies_arrondissements_municipaux'"
    ).fetchone()
    assert row is not None, (
        "Entrée manquante dans _etl_metadata pour geographies_arrondissements_municipaux"
    )
    assert row[0] == 45, f"row_count _etl_metadata ({row[0]}) ≠ 45"


# ── Populations ───────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def pop_skip(con: duckdb.DuckDBPyConnection) -> None:
    """Passe les tests populations si le millésime 2023 n'a pas encore été chargé."""
    n = con.execute("SELECT COUNT(*) FROM populations WHERE annee = 2023").fetchone()[0]
    if n == 0:
        pytest.skip(
            "populations 2023 introuvables — "
            "lancer etl_territoires.py --millesimes 2023 --skip-communes d'abord"
        )


def test_populations_count(con: duckdb.DuckDBPyConnection, pop_skip: None) -> None:
    """Au moins 34 000 communes chargées pour le millésime 2023."""
    n = con.execute("SELECT COUNT(*) FROM populations WHERE annee = 2023").fetchone()[0]
    assert n >= 34000, f"Populations 2023 : {n} lignes (attendu ≥ 34 000)"


def test_populations_plm(con: duckdb.DuckDBPyConnection, pop_skip: None) -> None:
    """Paris, Lyon, Marseille présents avec population municipale > 0."""
    rows = {
        r[0]: r[1]
        for r in con.execute("""
            SELECT code_insee_commune, municipale
            FROM populations
            WHERE code_insee_commune IN ('75056', '69123', '13055') AND annee = 2023
        """).fetchall()
    }
    assert "75056" in rows, "Paris (75056) absent des populations 2023"
    assert "69123" in rows, "Lyon (69123) absent des populations 2023"
    assert "13055" in rows, "Marseille (13055) absent des populations 2023"
    for code, pop in rows.items():
        assert pop > 0, f"Population municipale nulle pour {code}"


def test_populations_nulls(con: duckdb.DuckDBPyConnection, pop_skip: None) -> None:
    """comptee_a_part et totale sont 100 % NULL (PCAP absent de DS_POPULATIONS_HISTORIQUES)."""
    non_null_ca = con.execute(
        "SELECT COUNT(*) FROM populations WHERE annee = 2023 AND comptee_a_part IS NOT NULL"
    ).fetchone()[0]
    non_null_tot = con.execute(
        "SELECT COUNT(*) FROM populations WHERE annee = 2023 AND totale IS NOT NULL"
    ).fetchone()[0]
    assert non_null_ca == 0, (
        f"{non_null_ca} lignes avec comptee_a_part non NULL — PCAP ne devrait pas être chargé"
    )
    assert non_null_tot == 0, (
        f"{non_null_tot} lignes avec totale non NULL — totale dépend de PCAP absent"
    )


def test_populations_metadata(con: duckdb.DuckDBPyConnection, pop_skip: None) -> None:
    """Entrée populations_2023 présente dans _etl_metadata avec row_count cohérent."""
    row = con.execute(
        "SELECT row_count FROM _etl_metadata WHERE table_name = 'populations_2023'"
    ).fetchone()
    assert row is not None, "Entrée manquante dans _etl_metadata pour populations_2023"
    count_table = con.execute(
        "SELECT COUNT(*) FROM populations WHERE annee = 2023"
    ).fetchone()[0]
    assert row[0] == count_table, (
        f"row_count _etl_metadata ({row[0]}) ≠ COUNT(*) table ({count_table})"
    )
