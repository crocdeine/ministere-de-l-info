"""Tests smoke d'intégrité ETL — geographies + populations + vues.

Prérequis : lancer au moins une fois :
    uv run python scripts/etl_territoires.py --millesimes 2023 --yes

Ces tests ouvrent la DB en read_only — peuvent tourner avec Streamlit actif.
Les anomalies connues sont documentées inline et ne font PAS échouer les tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "ministere.duckdb"


@pytest.fixture(scope="module")
def con() -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        pytest.skip("ministere.duckdb introuvable — lancer etl_territoires.py d'abord")
    c = duckdb.connect(str(DB_PATH), read_only=True)
    c.execute("LOAD spatial")
    yield c
    c.close()


# ── Counts ────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "table, lo, hi",
    [
        ("geographies_regions", 13, 20),
        ("geographies_departements", 101, 101),
        ("geographies_epci", 1250, 1290),
        ("geographies_communes", 34000, 36000),
        ("geographies_arrondissements_municipaux", 44, 46),
        ("geographies_circonscriptions", 550, 570),
    ],
)
def test_count_geo_table(con, table, lo, hi):
    n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # noqa: S608
    assert lo <= n <= hi, f"{table}: {n} lignes hors fourchette [{lo}-{hi}]"


def test_count_populations_2023(con):
    n = con.execute("SELECT COUNT(*) FROM populations WHERE annee = 2023").fetchone()[0]
    assert 34000 <= n <= 36000, f"populations 2023 : {n} lignes hors fourchette"


@pytest.mark.parametrize("annee", [2013, 2018, 2023])
def test_count_populations_par_millesime(con, annee):
    """Chaque millésime chargé a entre 34 000 et 36 000 communes."""
    n = con.execute(
        "SELECT COUNT(*) FROM populations WHERE annee = ?", [annee]
    ).fetchone()[0]
    if n == 0:
        pytest.skip(f"Millésime {annee} non chargé")
    assert 34000 <= n <= 36000, (
        f"populations {annee} : {n} lignes hors fourchette [34000-36000]"
    )


@pytest.mark.parametrize(
    "annee, pop_lo, pop_hi",
    [
        (2013, 63_000_000, 67_000_000),
        (2018, 65_000_000, 68_000_000),
        (2023, 67_000_000, 70_000_000),
    ],
)
def test_populations_somme_nationale_par_millesime(con, annee, pop_lo, pop_hi):
    """Somme population municipale par millésime dans la fourchette attendue."""
    row = con.execute(
        "SELECT SUM(municipale) FROM populations WHERE annee = ?", [annee]
    ).fetchone()
    total = row[0] if row and row[0] else 0
    if total == 0:
        pytest.skip(f"Millésime {annee} non chargé")
    assert pop_lo <= total <= pop_hi, (
        f"Somme population {annee} : {total:,} hors [{pop_lo:,}-{pop_hi:,}]"
    )


# ── Doublons sur clé primaire ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "table, pk",
    [
        ("geographies_regions", "code_insee"),
        ("geographies_departements", "code_insee"),
        ("geographies_epci", "code_siren"),
        ("geographies_communes", "code_insee"),
        ("geographies_arrondissements_municipaux", "code_insee"),
        ("geographies_circonscriptions", "code"),
    ],
)
def test_no_duplicate_pk(con, table, pk):
    n = con.execute(  # noqa: S608
        f"SELECT COUNT(*) - COUNT(DISTINCT {pk}) FROM {table}"
    ).fetchone()[0]
    assert n == 0, f"{table}: {n} doublons sur {pk}"


def test_no_duplicate_populations_key(con):
    n = con.execute("""
        SELECT COUNT(*) - COUNT(DISTINCT (code_insee_commune || '|' || CAST(annee AS VARCHAR) || '|' || source))
        FROM populations
    """).fetchone()[0]
    assert n == 0, f"populations: {n} doublons sur (code_insee_commune, annee, source)"


# ── Géométries valides ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "table, geom_col",
    [
        ("geographies_regions", "geometry_simplified_national"),
        ("geographies_regions", "geometry_simplified_regional"),
        ("geographies_departements", "geometry_simplified_national"),
        ("geographies_departements", "geometry_simplified_departemental"),
        ("geographies_epci", "geometry_simplified_epci"),
        ("geographies_communes", "geometry_simplified_communal"),
        ("geographies_arrondissements_municipaux", "geometry_simplified_communal"),
        ("geographies_circonscriptions", "geometry_simplified_circo"),
    ],
)
def test_geometries_valides(con, table, geom_col):
    invalides = con.execute(  # noqa: S608
        f"SELECT COUNT(*) FROM {table}"
        f" WHERE {geom_col} IS NOT NULL AND NOT ST_IsValid({geom_col})"
    ).fetchone()[0]
    assert invalides == 0, f"{table}.{geom_col}: {invalides} géométries invalides"


@pytest.mark.parametrize(
    "table, geom_col",
    [
        ("geographies_regions", "geometry_simplified_national"),
        ("geographies_departements", "geometry_simplified_national"),
        ("geographies_epci", "geometry_simplified_epci"),
        ("geographies_communes", "geometry_simplified_communal"),
    ],
)
def test_geometries_non_null(con, table, geom_col):
    nulls = con.execute(  # noqa: S608
        f"SELECT COUNT(*) FROM {table} WHERE {geom_col} IS NULL"
    ).fetchone()[0]
    assert nulls == 0, f"{table}.{geom_col}: {nulls} géométries NULL"


# ── Bounds WGS84 ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "table, geom_col",
    [
        ("geographies_regions", "geometry_simplified_national"),
        ("geographies_departements", "geometry_simplified_national"),
        ("geographies_communes", "geometry_simplified_communal"),
    ],
)
def test_bounds_wgs84(con, table, geom_col):
    row = con.execute(  # noqa: S608
        f"SELECT MIN(ST_XMin({geom_col})), MAX(ST_XMax({geom_col})),"
        f" MIN(ST_YMin({geom_col})), MAX(ST_YMax({geom_col}))"
        f" FROM {table} WHERE {geom_col} IS NOT NULL"
    ).fetchone()
    assert row is not None
    xmin, xmax, ymin, ymax = row
    assert -180 <= xmin <= 180, f"{table}: xmin={xmin} hors [-180, 180]"
    assert -180 <= xmax <= 180, f"{table}: xmax={xmax} hors [-180, 180]"
    assert -90 <= ymin <= 90, f"{table}: ymin={ymin} hors [-90, 90]"
    assert -90 <= ymax <= 90, f"{table}: ymax={ymax} hors [-90, 90]"


# ── FK conceptuelles ──────────────────────────────────────────────────────────


def test_fk_departements_vers_regions(con):
    """Tous les code_region des départements existent dans geographies_regions."""
    orphelins = con.execute("""
        SELECT COUNT(*) FROM geographies_departements
        WHERE code_region NOT IN (SELECT code_insee FROM geographies_regions)
    """).fetchone()[0]
    assert orphelins == 0, f"{orphelins} départements avec code_region orphelin"


def test_fk_communes_vers_departements(con):
    """Quasi-aucun orphelin — 2 communes SPM (code_departement='NR') sont acceptables.

    Saint-Pierre-et-Miquelon (97501, 97502) est une COM absente des départements ADMIN-EXPRESS.
    """
    orphelins = con.execute("""
        SELECT COUNT(*) FROM geographies_communes
        WHERE code_departement NOT IN (SELECT code_insee FROM geographies_departements)
    """).fetchone()[0]
    assert orphelins <= 5, (
        f"{orphelins} communes avec code_departement orphelin (attendu ≤ 5 pour SPM)"
    )


def test_fk_communes_vers_regions(con):
    """Quasi-aucun orphelin — 2 communes SPM (code_region='NR') sont acceptables."""
    orphelins = con.execute("""
        SELECT COUNT(*) FROM geographies_communes
        WHERE code_region NOT IN (SELECT code_insee FROM geographies_regions)
    """).fetchone()[0]
    assert orphelins <= 5, (
        f"{orphelins} communes avec code_region orphelin (attendu ≤ 5 pour SPM)"
    )


def test_fk_communes_vers_epci(con):
    """Quasi-aucun orphelin EPCI — seules les communes 'NR' (hors-périmètre) sont acceptées.

    SPLIT_PART(codes_siren_des_epci, '/', 1) dans l'ETL garantit qu'on stocke un
    SIREN unique. Les 6 communes avec code_epci='NR' (COM hors ADMIN-EXPRESS) sont
    les seuls orphelins résiduels attendus.
    """
    orphelins = con.execute("""
        SELECT COUNT(*) FROM geographies_communes
        WHERE code_epci IS NOT NULL
          AND code_epci NOT IN (SELECT code_siren FROM geographies_epci)
    """).fetchone()[0]
    assert orphelins <= 10, (
        f"{orphelins} communes avec code_epci orphelin (attendu ≤ 10 — uniquement codes 'NR')"
    )


def test_fk_arm_vers_communes_meres(con):
    """Tous les ARM pointent vers Paris (75056), Lyon (69123) ou Marseille (13055)."""
    inattendus = con.execute("""
        SELECT COUNT(*) FROM geographies_arrondissements_municipaux
        WHERE code_commune_mere NOT IN ('75056', '69123', '13055')
    """).fetchone()[0]
    assert inattendus == 0, f"{inattendus} ARM avec une commune-mère inattendue"


def test_fk_populations_vers_communes(con):
    """Quasi-aucune commune avec population mais sans géographie (communes fusionnées OK)."""
    orphelins = con.execute("""
        SELECT COUNT(DISTINCT code_insee_commune) FROM populations
        WHERE annee = 2023
          AND code_insee_commune NOT IN (SELECT code_insee FROM geographies_communes)
    """).fetchone()[0]
    assert orphelins <= 50, (
        f"{orphelins} communes en populations sans géographie (attendu ≤ 50 — fusions COG)"
    )


# ── Cohérence métier ──────────────────────────────────────────────────────────


def test_regions_codes_spot(con):
    """Codes INSEE des 13 régions métropolitaines tous présents."""
    codes_metro = {
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
    codes_db = {
        r[0]
        for r in con.execute("SELECT code_insee FROM geographies_regions").fetchall()
    }
    manquants = codes_metro - codes_db
    assert not manquants, f"Régions métro manquantes : {manquants}"


def test_departements_corse(con):
    """Codes Corse-du-Sud (2A) et Haute-Corse (2B) présents."""
    codes = {
        r[0]
        for r in con.execute(
            "SELECT code_insee FROM geographies_departements WHERE code_insee IN ('2A', '2B')"
        ).fetchall()
    }
    assert codes == {"2A", "2B"}, f"Codes Corse incorrects : {codes}"


@pytest.mark.parametrize(
    "code, ville, pop_lo, pop_hi",
    [
        ("75056", "Paris", 2_000_000, 2_500_000),
        ("69123", "Lyon", 400_000, 700_000),
        ("13055", "Marseille", 700_000, 1_100_000),
    ],
)
def test_populations_plm(con, code, ville, pop_lo, pop_hi):
    """Populations 2023 de Paris, Lyon, Marseille dans les fourchettes attendues."""
    row = con.execute(
        "SELECT municipale FROM populations WHERE code_insee_commune = ? AND annee = 2023",
        [code],
    ).fetchone()
    assert row is not None, f"{ville} ({code}) absent de populations 2023"
    pop = row[0]
    assert pop_lo <= pop <= pop_hi, f"{ville}: {pop:,} hors [{pop_lo:,}-{pop_hi:,}]"


def test_populations_comptee_a_part_null(con):
    """comptee_a_part est 100% NULL — PCAP non chargé (comportement attendu)."""
    non_null = con.execute(
        "SELECT COUNT(*) FROM populations WHERE annee = 2023 AND comptee_a_part IS NOT NULL"
    ).fetchone()[0]
    assert non_null == 0, (
        f"{non_null} lignes avec comptee_a_part non NULL — PCAP inattendu chargé"
    )


def test_arm_counts_par_ville(con):
    """Paris 20 ARM, Lyon 9, Marseille 16."""
    expected = [("75056", 20), ("69123", 9), ("13055", 16)]
    for code_mere, attendu in expected:
        n = con.execute(
            "SELECT COUNT(*) FROM geographies_arrondissements_municipaux WHERE code_commune_mere = ?",
            [code_mere],
        ).fetchone()[0]
        assert n == attendu, f"ARM commune {code_mere}: {n} ≠ {attendu}"


def test_epci_types_presents(con):
    """Au moins 1 EPT (Grand Paris) et 1 ME (Métropole) parmi les EPCI."""
    types = {
        r[0]
        for r in con.execute(
            "SELECT DISTINCT type_epci FROM geographies_epci"
        ).fetchall()
    }
    assert "EPT" in types, "Aucun EPT trouvé dans geographies_epci"
    assert "ME" in types, "Aucune Métropole (ME) trouvée dans geographies_epci"


def test_epci_ept_sans_departement(con):
    """11 EPT ont code_departement_principal = NULL — anomalie WFS connue."""
    n_ept = con.execute(
        "SELECT COUNT(*) FROM geographies_epci WHERE type_epci = 'EPT'"
    ).fetchone()[0]
    n_ept_null = con.execute(
        "SELECT COUNT(*) FROM geographies_epci WHERE type_epci = 'EPT' AND code_departement_principal IS NULL"
    ).fetchone()[0]
    assert n_ept_null == n_ept, (
        f"Attendu {n_ept} EPT sans département, trouvé {n_ept_null} "
        "(les EPT du Grand Paris ont un champ multi-valeur non filtrable côté WFS)"
    )


# ── Vues d'agrégation ─────────────────────────────────────────────────────────


def test_vue_population_region_count(con):
    """v_population_region 2023 : 17 lignes (Mayotte region 06 exclue — attendu)."""
    n = con.execute(
        "SELECT COUNT(*) FROM v_population_region WHERE annee = 2023"
    ).fetchone()[0]
    assert n == 17, (
        f"v_population_region 2023 : {n} lignes (attendu 17 — Mayotte hors source INSEE)"
    )


def test_vue_population_departement_count(con):
    """v_population_departement 2023 : 100 lignes (Mayotte dpt 976 exclu — attendu)."""
    n = con.execute(
        "SELECT COUNT(*) FROM v_population_departement WHERE annee = 2023"
    ).fetchone()[0]
    assert n == 100, (
        f"v_population_departement 2023 : {n} lignes (attendu 100 — Mayotte hors source INSEE)"
    )


def test_vue_population_commune_coherente(con):
    """v_population_commune 2023 : même count que populations pour annee=2023."""
    n_pop = con.execute(
        "SELECT COUNT(*) FROM populations WHERE annee = 2023"
    ).fetchone()[0]
    n_vue = con.execute(
        "SELECT COUNT(*) FROM v_population_commune WHERE annee = 2023"
    ).fetchone()[0]
    assert n_pop == n_vue, (
        f"v_population_commune ({n_vue}) ≠ populations ({n_pop}) pour annee=2023"
    )


@pytest.mark.parametrize("annee", [2013, 2018, 2023])
def test_vue_population_commune_tous_millesimes(con, annee):
    """v_population_commune reflète fidèlement la table populations pour chaque millésime."""
    n_pop = con.execute(
        "SELECT COUNT(*) FROM populations WHERE annee = ?", [annee]
    ).fetchone()[0]
    if n_pop == 0:
        pytest.skip(f"Millésime {annee} non chargé")
    n_vue = con.execute(
        "SELECT COUNT(*) FROM v_population_commune WHERE annee = ?", [annee]
    ).fetchone()[0]
    assert n_pop == n_vue, (
        f"v_population_commune {annee} : {n_vue} lignes ≠ populations {n_pop}"
    )


def test_vue_population_region_somme_totale(con):
    """Somme population municipale régions 2023 entre 60M et 70M (hors Mayotte)."""
    total = con.execute(
        "SELECT SUM(population_municipale) FROM v_population_region WHERE annee = 2023"
    ).fetchone()[0]
    assert 60_000_000 <= total <= 70_000_000, (
        f"Somme population régions 2023 : {total:,} hors [60M-70M]"
    )


# ── Métadonnées ETL ───────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "table_name",
    [
        "geographies_regions",
        "geographies_departements",
        "geographies_epci",
        "geographies_communes",
        "geographies_arrondissements_municipaux",
        "geographies_circonscriptions",
        "populations_2023",
    ],
)
def test_etl_metadata_entree_presente(con, table_name):
    row = con.execute(
        "SELECT row_count FROM _etl_metadata WHERE table_name = ?", [table_name]
    ).fetchone()
    assert row is not None, f"_etl_metadata : entrée manquante pour {table_name!r}"


@pytest.mark.parametrize(
    "table_name, geo_table",
    [
        ("geographies_regions", "geographies_regions"),
        ("geographies_departements", "geographies_departements"),
        ("geographies_epci", "geographies_epci"),
        ("geographies_communes", "geographies_communes"),
        (
            "geographies_arrondissements_municipaux",
            "geographies_arrondissements_municipaux",
        ),
        ("geographies_circonscriptions", "geographies_circonscriptions"),
    ],
)
def test_etl_metadata_row_count_coherent(con, table_name, geo_table):
    meta = con.execute(
        "SELECT row_count FROM _etl_metadata WHERE table_name = ?", [table_name]
    ).fetchone()
    if meta is None:
        pytest.skip(f"Entrée {table_name} absente de _etl_metadata")
    count_table = con.execute(  # noqa: S608
        f"SELECT COUNT(*) FROM {geo_table}"
    ).fetchone()[0]
    assert meta[0] == count_table, (
        f"_etl_metadata.{table_name} : row_count={meta[0]} ≠ COUNT(*)={count_table}"
    )


def test_etl_metadata_populations_2023(con):
    """Entrée populations_2023 dans _etl_metadata avec row_count cohérent."""
    meta = con.execute(
        "SELECT row_count FROM _etl_metadata WHERE table_name = 'populations_2023'"
    ).fetchone()
    assert meta is not None, "_etl_metadata : entrée 'populations_2023' absente"
    count_pop = con.execute(
        "SELECT COUNT(*) FROM populations WHERE annee = 2023"
    ).fetchone()[0]
    assert meta[0] == count_pop, f"populations_2023 metadata : {meta[0]} ≠ {count_pop}"
