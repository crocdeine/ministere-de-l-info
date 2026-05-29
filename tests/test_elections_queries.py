"""Tests sanitaires des modules viz.elections_queries et viz.maps_elections (C3).

Les fonctions @st.cache_data sont appelables hors Streamlit runtime (Streamlit 1.57) :
le cache mémoire est utilisé sans spinner, ce qui est idéal pour les tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import folium
import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ministere_de_l_info.etl.schema_elections import _CIRCO21_CODES
from ministere_de_l_info.viz import elections_queries as eq
from ministere_de_l_info.viz.maps_elections import (
    _legend_blocs_html,
    make_choropleth_elections_bloc_dominant,
    make_choropleth_elections_score_bloc,
)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "ministere.duckdb"

_CIRCO21_IN: str = ", ".join(f"'{c}'" for c in _CIRCO21_CODES)

# ── Données minimales pour tester les fonctions de carte sans DB ──────────────

_MOCK_BLOCS_META: list[tuple[str, str, str, int]] = [
    ("EXG", "Extrême gauche", "#8B0000", 1),
    ("GAU", "Gauche", "#E84C61", 2),
    ("DIV", "Divers", "#9E9E9E", 3),
    ("CENT", "Centre", "#F5B800", 4),
    ("DTE", "Droite", "#3B7DD8", 5),
    ("EXD", "Extrême droite", "#1F3864", 6),
]

_POLYGON_A = (
    '{"type":"Polygon","coordinates":[[[3.5,50.3],[3.6,50.3],[3.6,50.4],[3.5,50.4],[3.5,50.3]]]}'
)
_POLYGON_B = (
    '{"type":"Polygon","coordinates":[[[3.4,50.3],[3.5,50.3],[3.5,50.4],[3.4,50.4],[3.4,50.3]]]}'
)

_MOCK_SCORES = pl.DataFrame(
    {
        "code_commune": ["59606", "59606", "59027", "59027"],
        "bloc": ["EXD", "GAU", "GAU", "DTE"],
        "voix": [1000, 800, 600, 500],
    }
)
_MOCK_PART = pl.DataFrame(
    {
        "code_commune": ["59606", "59027"],
        "inscrits": [5000, 3000],
        "votants": [3000, 2000],
        "exprimes": [2800, 1900],
        "taux_participation_pct": [60.0, 66.7],
    }
)
_MOCK_GEO = pl.DataFrame(
    {
        "code_commune": ["59606", "59027"],
        "nom": ["Valenciennes", "Aubry-du-Hainaut"],
        "geojson": [_POLYGON_A, _POLYGON_B],
    }
)


@pytest.fixture(scope="module")
def con() -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        pytest.skip("ministere.duckdb introuvable — lancer les scripts ETL d'abord")
    c = duckdb.connect(str(DB_PATH), read_only=True)
    c.execute("LOAD spatial")
    n = c.execute(
        "SELECT COUNT(*) FROM resultats_candidats WHERE id_election LIKE '%_pres_%'"
    ).fetchone()[0]
    if n == 0:
        c.close()
        pytest.skip(
            "Données présidentielles non chargées — lancer load_elections_presidentielles.py"
        )
    yield c
    c.close()


def test_blocs_meta_six_blocs(con):
    """get_blocs_meta() : exactement 6 blocs avec codes et couleurs."""
    rows = con.execute(
        "SELECT bloc, libelle, couleur, ordre FROM blocs_politiques ORDER BY ordre"
    ).fetchall()
    assert len(rows) == 6
    codes = {r[0] for r in rows}
    assert codes == {"EXG", "GAU", "DIV", "CENT", "DTE", "EXD"}
    for _, _, couleur, _ in rows:
        assert couleur.startswith("#"), f"Couleur invalide : {couleur}"


def test_scores_circo21_2022_t1_vingt_communes(con):
    """get_scores_communes(2022, 1, 'circo21') → exactement 20 communes distinctes."""
    n = con.execute(
        "SELECT COUNT(DISTINCT code_commune) FROM v_scores_circo21_pres WHERE annee = 2022 AND tour = 1"
    ).fetchone()[0]
    assert n == len(_CIRCO21_CODES), f"{n} communes trouvées, attendu {len(_CIRCO21_CODES)}"


def test_scores_circo21_voix_positives(con):
    """Somme des voix circo21 2022 t1 > 0."""
    voix = con.execute(
        "SELECT SUM(voix) FROM v_scores_circo21_pres WHERE annee = 2022 AND tour = 1"
    ).fetchone()[0]
    assert voix is not None and voix > 0


def test_scores_hdf_plus_grand_que_circo21(con):
    """HdF contient plus de communes que la circo 21 seule."""
    n_hdf = con.execute(
        "SELECT COUNT(DISTINCT code_commune) FROM v_scores_commune_pres WHERE annee = 2022 AND tour = 1"
    ).fetchone()[0]
    assert n_hdf > len(_CIRCO21_CODES)


def test_evolution_circo21_cinq_annees(con):
    """get_evolution_blocs('circo21') : 5 années distinctes pour le 1er tour."""
    annees = {
        r[0]
        for r in con.execute(
            "SELECT DISTINCT annee FROM v_evolution_blocs_circo21 WHERE tour = 1"
        ).fetchall()
    }
    assert annees == {2002, 2007, 2012, 2017, 2022}


def test_participation_coherente_circo21(con):
    """Votants ≤ inscrits et taux ∈ (0, 100) pour toutes les communes circo21 2022 t1."""
    rows = con.execute(  # noqa: S608
        f"SELECT code_commune, inscrits, votants, taux_participation_pct "
        f"FROM v_participation_commune_pres "
        f"WHERE annee = 2022 AND tour = 1 AND code_commune IN ({_CIRCO21_IN})"
    ).fetchall()
    assert rows, "Aucune donnée participation circo21 2022 t1"
    for code, inscrits, votants, taux in rows:
        assert votants <= inscrits, f"{code} : votants ({votants}) > inscrits ({inscrits})"
        assert 0 < taux < 100, f"{code} : taux hors plage : {taux}"


def test_communes_geo_circo21_vingt_geometries(con):
    """get_communes_geo('circo21') : 20 communes avec géométrie non nulle."""
    rows = con.execute(  # noqa: S608
        f"SELECT code_insee, ST_AsGeoJSON(geometry_simplified_communal) "
        f"FROM geographies_communes WHERE code_insee IN ({_CIRCO21_IN})"
    ).fetchall()
    assert len(rows) == len(_CIRCO21_CODES), (
        f"{len(rows)} géométries trouvées, attendu {len(_CIRCO21_CODES)}"
    )
    for code, geojson in rows:
        assert geojson is not None, f"Géométrie NULL pour {code}"
        assert len(geojson) > 10, f"Géométrie trop courte pour {code}"


def test_bounds_circo21_dans_nord(con):
    """Bounding box circo21 doit être dans le Nord (lat ≈ 50.2–50.5, lon ≈ 3.3–3.6)."""
    row = con.execute(  # noqa: S608
        f"SELECT MIN(ST_YMin(geometry_simplified_communal)), MIN(ST_XMin(geometry_simplified_communal)),"
        f" MAX(ST_YMax(geometry_simplified_communal)), MAX(ST_XMax(geometry_simplified_communal))"
        f" FROM geographies_communes WHERE code_insee IN ({_CIRCO21_IN})"
    ).fetchone()
    assert row and row[0] is not None
    miny, minx, maxy, maxx = row
    assert 49.0 < float(miny) < 51.0, f"Latitude min hors Nord : {miny}"
    assert 2.0 < float(minx) < 5.0, f"Longitude min hors Nord-Pas : {minx}"


# ── Tests des fonctions elections_queries (via @st.cache_data hors runtime) ──


class TestElectionsQueriesFunctions:
    """Teste elections_queries.py via ses fonctions publiques (@st.cache_data OK hors runtime)."""

    def test_is_data_loaded(self, con):  # noqa: ARG002 — fixture force le skip si DB vide
        assert eq.is_data_loaded() is True

    def test_get_blocs_meta_six_codes(self, con):  # noqa: ARG002
        blocs = eq.get_blocs_meta()
        assert len(blocs) == 6
        codes = {b[0] for b in blocs}
        assert codes == {"EXG", "GAU", "DIV", "CENT", "DTE", "EXD"}

    def test_get_scores_communes_circo21(self, con):  # noqa: ARG002
        df = eq.get_scores_communes(2022, 1, "circo21")
        assert not df.is_empty()
        assert df["code_commune"].n_unique() == len(_CIRCO21_CODES)
        assert df["voix"].sum() > 0

    def test_get_scores_communes_hdf(self, con):  # noqa: ARG002
        df = eq.get_scores_communes(2022, 1, "hdf")
        assert df["code_commune"].n_unique() > len(_CIRCO21_CODES)

    def test_get_participation_communes(self, con):  # noqa: ARG002
        df = eq.get_participation_communes(2022, 1, "circo21")
        assert not df.is_empty()
        assert set(df.columns) >= {"code_commune", "inscrits", "votants", "taux_participation_pct"}
        assert (df["votants"] <= df["inscrits"]).all()

    def test_get_evolution_blocs_circo21(self, con):  # noqa: ARG002
        df = eq.get_evolution_blocs("circo21")
        annees = set(df.filter(pl.col("tour") == 1)["annee"].to_list())
        assert annees == {2002, 2007, 2012, 2017, 2022}

    def test_get_communes_geo_circo21(self, con):  # noqa: ARG002
        df = eq.get_communes_geo("circo21")
        assert len(df) == len(_CIRCO21_CODES)
        assert df["geojson"].null_count() == 0

    def test_get_bounds_circo21_valides(self, con):  # noqa: ARG002
        bounds = eq.get_bounds("circo21")
        assert bounds is not None
        assert len(bounds) == 2
        lat_min, lon_min = bounds[0]
        lat_max, lon_max = bounds[1]
        assert lat_min < lat_max
        assert lon_min < lon_max
        assert 49.0 < lat_min < 51.0


# ── Tests des fonctions maps_elections (données mock, sans DB) ────────────────


class TestMapsFunctions:
    """Teste maps_elections.py avec des DataFrames minimaux (pas de DB requise)."""

    def test_legend_blocs_html_contient_six_blocs(self):
        html = _legend_blocs_html(_MOCK_BLOCS_META, "Test légende")
        assert "Test légende" in html
        assert "#8B0000" in html  # couleur EXG
        assert "#1F3864" in html  # couleur EXD
        assert html.count("div") > 6

    def test_make_choropleth_bloc_dominant_retourne_map(self):
        carte = make_choropleth_elections_bloc_dominant(
            _MOCK_SCORES,
            _MOCK_GEO,
            _MOCK_BLOCS_META,
            bounds=[[50.3, 3.4], [50.4, 3.6]],
            titre="Bloc dominant",
        )
        assert isinstance(carte, folium.Map)

    def test_make_choropleth_bloc_dominant_sans_bounds(self):
        carte = make_choropleth_elections_bloc_dominant(
            _MOCK_SCORES, _MOCK_GEO, _MOCK_BLOCS_META, bounds=None, titre="Test"
        )
        assert isinstance(carte, folium.Map)

    def test_make_choropleth_score_bloc_retourne_map(self):
        carte = make_choropleth_elections_score_bloc(
            _MOCK_SCORES,
            _MOCK_PART,
            _MOCK_GEO,
            bloc="EXD",
            couleur_bloc="#1F3864",
            libelle_bloc="Extrême droite",
            bounds=[[50.3, 3.4], [50.4, 3.6]],
            titre="Score EXD",
        )
        assert isinstance(carte, folium.Map)

    def test_make_choropleth_score_bloc_absent(self):
        """Bloc avec 0 voix dans le mock → la carte doit quand même se construire."""
        carte = make_choropleth_elections_score_bloc(
            _MOCK_SCORES,
            _MOCK_PART,
            _MOCK_GEO,
            bloc="EXG",  # absent des mock scores
            couleur_bloc="#8B0000",
            libelle_bloc="Extrême gauche",
            bounds=None,
            titre="Score EXG",
        )
        assert isinstance(carte, folium.Map)
