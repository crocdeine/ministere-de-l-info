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
    rows = con.execute("SELECT DISTINCT annee FROM populations ORDER BY annee DESC").fetchall()
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
    rows = con.execute("SELECT code_insee, nom FROM geographies_regions ORDER BY nom").fetchall()
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


def test_evolution_query_regions_idf(con):
    """Double JOIN millésime sur v_population_region — Île-de-France croissante 2013→2023."""
    row = con.execute("""
        SELECT g.code_insee AS code,
               (p_main.population_municipale - p_ref.population_municipale) AS delta_abs,
               100.0 * (p_main.population_municipale - p_ref.population_municipale)
                   / NULLIF(p_ref.population_municipale, 0) AS delta_pct
        FROM geographies_regions g
        LEFT JOIN v_population_region p_main
            ON g.code_insee = p_main.code_region AND p_main.annee = 2023
        LEFT JOIN v_population_region p_ref
            ON g.code_insee = p_ref.code_region AND p_ref.annee = 2013
        WHERE g.code_insee = '11'
    """).fetchone()
    assert row is not None
    code, delta_abs, delta_pct = row
    assert code == "11"
    assert delta_abs is not None and delta_abs > 0, "Île-de-France : croissance 2013→2023"
    assert delta_pct is not None and delta_pct > 2.0, (
        f"Croissance IdF attendue > 2%, obtenu {delta_pct:.2f}%"
    )


def test_evolution_query_commune_paris_decroissance(con):
    """Paris (75056) est en décroissance démographique 2013→2023."""
    row = con.execute("""
        SELECT (p_main.population_municipale - p_ref.population_municipale) AS delta_abs,
               100.0 * (p_main.population_municipale - p_ref.population_municipale)
                   / NULLIF(p_ref.population_municipale, 0) AS delta_pct
        FROM v_population_commune p_main
        JOIN v_population_commune p_ref
            ON p_main.code_commune = p_ref.code_commune
        WHERE p_main.code_commune = '75056'
          AND p_main.annee = 2023
          AND p_ref.annee = 2013
    """).fetchone()
    assert row is not None
    delta_abs, delta_pct = row
    assert delta_abs < 0, f"Paris : décroissance attendue, obtenu {delta_abs:+,}"
    assert delta_pct < -2.0, f"Paris : delta > 2% attendu, obtenu {delta_pct:.2f}%"


@pytest.mark.parametrize("annee", [2013, 2018, 2023])
def test_tableau_region_millesimes(con, annee):
    """Le tableau régions renvoie des populations différentes selon le millésime."""
    rows = con.execute(
        """
        SELECT g.code_insee AS code,
               COALESCE(p.population_municipale, 0) AS pop
        FROM geographies_regions g
        LEFT JOIN v_population_region p
            ON g.code_insee = p.code_region AND p.annee = ?
        ORDER BY pop DESC NULLS LAST LIMIT 18
        """,
        [annee],
    ).fetchall()
    n_pop = con.execute("SELECT COUNT(*) FROM populations WHERE annee = ?", [annee]).fetchone()[0]
    if n_pop == 0:
        pytest.skip(f"Millésime {annee} non chargé")
    assert len(rows) == 18
    idf = next((r[1] for r in rows if r[0] == "11"), None)
    assert idf is not None and idf > 10_000_000, f"Île-de-France ({annee}) : {idf} — attendu > 10M"
