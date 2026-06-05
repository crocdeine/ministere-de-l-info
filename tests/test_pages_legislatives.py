"""Tests Python purs — requêtes SQL pour la page Législatives (D1.3).

Deux niveaux :
- Via fonctions elections_legi_queries (coverage + contrat d'interface)
- Via SQL direct DuckDB (assertions granulaires indépendantes du cache)

Prérequis : DB chargée (init_elections_schema.py + load_elections_legislatives.py)
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ministere_de_l_info.viz.elections_legi_queries import (  # noqa: E402
    get_bv_details_legi,
    get_circo_bounds,
    get_circos_hdf_geo,
    get_circos_hdf_legi,
    get_communes_circo_legi_geo,
    get_communes_circo_legi_list,
    get_evolution_circo_legi,
    get_evolution_hdf_legi,
    get_hdf_bounds_circo,
    get_metrics_commune_legi,
    get_nuances_circo_legi,
    get_participation_communes_circo_legi,
    get_participation_hdf_legi,
    get_scores_communes_circo_legi,
    get_scores_hdf_legi,
    is_legi_data_loaded,
)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "ministere.duckdb"

_HDF_DEPTS_SQL = "'02', '59', '60', '62', '80'"


@pytest.fixture(scope="module")
def con() -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        pytest.skip("DB absente. Lancer init_elections_schema.py + load_elections_legislatives.py")
    c = duckdb.connect(str(DB_PATH), read_only=True)
    c.execute("LOAD spatial")
    n = c.execute(
        "SELECT COUNT(*) FROM resultats_candidats WHERE id_election LIKE '%_legi_%'"
    ).fetchone()[0]
    if n == 0:
        pytest.skip("Législatives non chargées. Lancer load_elections_legislatives.py")
    yield c
    c.close()


class TestGetCircosHdfLegi:
    """get_circos_hdf_legi → 50 circos HdF avec noms."""

    def test_count_circos(self, con):
        """Doit retourner exactement 50 circos HdF."""
        rows = con.execute("""
            SELECT DISTINCT v.code_circo
            FROM v_scores_circo_legi v
        """).fetchall()
        assert len(rows) == 50, f"Attendu 50 circos, trouvé {len(rows)}"

    def test_geo_join_donne_noms(self, con):
        """La jointure avec geographies_circonscriptions fournit des noms non-nuls."""
        rows = con.execute("""
            SELECT DISTINCT v.code_circo, gc.nom
            FROM v_scores_circo_legi v
            LEFT JOIN geographies_circonscriptions gc ON gc.code = v.code_circo
        """).fetchall()
        noms_nuls = [code for code, nom in rows if nom is None]
        assert noms_nuls == [], f"Circos sans nom géo : {noms_nuls}"

    def test_valenciennes_presente(self, con):
        """La circo 59-21 (Valenciennes) est bien dans les 50."""
        row = con.execute(
            "SELECT code_circo FROM v_scores_circo_legi WHERE code_circo = '59-21' LIMIT 1"
        ).fetchone()
        assert row is not None, "59-21 absente de v_scores_circo_legi"


class TestGetCarteHdfData:
    """get_scores_hdf_legi → vue d'ensemble avec bloc dominant par circo."""

    def test_cinquante_circos_2022_t1(self, con):
        """2022 t1 doit couvrir 50 circos."""
        n = con.execute(
            "SELECT COUNT(DISTINCT code_circo) FROM v_scores_circo_legi WHERE annee = 2022 AND tour = 1"
        ).fetchone()[0]
        assert n == 50, f"Attendu 50 circos 2022t1, trouvé {n}"

    def test_chaque_circo_a_un_bloc_dominant(self, con):
        """Chaque circo doit avoir au moins un bloc avec voix > 0."""
        rows = con.execute("""
            SELECT code_circo, MAX(voix) AS max_voix
            FROM v_scores_circo_legi
            WHERE annee = 2022 AND tour = 1
            GROUP BY code_circo
            HAVING MAX(voix) = 0 OR MAX(voix) IS NULL
        """).fetchall()
        assert rows == [], f"Circos sans voix : {rows}"

    def test_blocs_valides(self, con):
        """Tous les blocs retournés sont dans la nomenclature officielle."""
        blocs_officiels = {"EXG", "GAU", "DIV", "CENT", "DTE", "EXD"}
        rows = con.execute("SELECT DISTINCT bloc FROM v_scores_circo_legi").fetchall()
        blocs_data = {r[0] for r in rows}
        invalides = blocs_data - blocs_officiels
        assert not invalides, f"Blocs inconnus : {invalides}"


class TestGetCircoDetailData:
    """Requêtes pour la vue détaillée d'une circo (59-21 Valenciennes)."""

    def test_nuances_59_21_2022_t1(self, con):
        """59-21 en 2022 t1 : données non vides et blocs attendus."""
        rows = con.execute("""
            SELECT rc.nuance, COALESCE(nh.bloc, 'DIV') AS bloc, SUM(rc.voix) AS voix
            FROM resultats_candidats rc
            JOIN elections e ON e.id_election = rc.id_election
            JOIN resultats_participation rp
                ON rp.id_election = rc.id_election
                AND rp.code_departement = rc.code_departement
                AND rp.code_commune = rc.code_commune
                AND rp.code_bv = rc.code_bv
            LEFT JOIN nuances_harmonisees nh ON nh.nuance = rc.nuance AND nh.annee = e.annee
            WHERE e.type_scrutin = 'legi' AND e.annee = 2022 AND e.tour = 1 AND rp.code_circo = '59-21'
            GROUP BY rc.nuance, COALESCE(nh.bloc, 'DIV')
        """).fetchall()
        blocs = {b for _, b, _ in rows}
        # Blocs politiquement présents en 59-21 2022 (validé D1.2)
        assert {"GAU", "DTE", "EXD"}.issubset(blocs), f"Blocs attendus manquants : {blocs}"
        total_voix = sum(v for _, _, v in rows)
        assert total_voix > 20_000, f"Total voix trop faible : {total_voix}"

    def test_communes_dans_circo_59_21(self, con):
        """La circo 59-21 contient ~20 communes (validé par jointure spatiale D1.2)."""
        n = con.execute("""
            SELECT COUNT(DISTINCT rp.code_commune)
            FROM resultats_participation rp
            JOIN elections e ON e.id_election = rp.id_election
            WHERE e.type_scrutin = 'legi' AND e.annee = 2022 AND e.tour = 1 AND rp.code_circo = '59-21'
        """).fetchone()[0]
        assert 15 <= n <= 25, f"Nombre de communes hors plage [15-25] : {n}"

    def test_geo_communes_circo(self, con):
        """Les communes de 59-21 ont des géométries dans geographies_communes."""
        n = con.execute("""
            SELECT COUNT(*)
            FROM geographies_communes gc
            WHERE gc.code_insee IN (
                SELECT DISTINCT rp.code_commune
                FROM resultats_participation rp
                JOIN elections e ON e.id_election = rp.id_election
                WHERE e.type_scrutin = 'legi' AND e.annee = 2022 AND e.tour = 1 AND rp.code_circo = '59-21'
            )
        """).fetchone()[0]
        assert n >= 15, f"Trop peu de communes géo : {n}"


class TestGetEvolutionCirco:
    """get_evolution_circo_legi → 6 scrutins pour 59-21."""

    def test_six_annees_disponibles(self, con):
        """6 années × 2 tours = 12 lignes (en termes d'annee×tour×bloc)."""
        n_annees = con.execute("""
            SELECT COUNT(DISTINCT annee)
            FROM v_scores_circo_legi
            WHERE code_circo = '59-21'
        """).fetchone()[0]
        assert n_annees == 6, f"Attendu 6 années, trouvé {n_annees}"

    def test_deux_tours_par_annee(self, con):
        """Chaque année doit avoir 2 tours de données."""
        rows = con.execute("""
            SELECT annee, COUNT(DISTINCT tour) AS n_tours
            FROM v_scores_circo_legi
            WHERE code_circo = '59-21'
            GROUP BY annee
        """).fetchall()
        for annee, n_tours in rows:
            assert n_tours == 2, f"Annee {annee} : {n_tours} tour(s) au lieu de 2"

    def test_flag_ancien_decoupage(self, con):
        """Les années 2002 et 2007 ont ancien_decoupage = TRUE."""
        rows = con.execute("""
            SELECT DISTINCT annee, ancien_decoupage
            FROM v_scores_circo_legi
            WHERE code_circo = '59-21' AND annee IN (2002, 2007)
        """).fetchall()
        for annee, flag in rows:
            assert flag is True, f"Annee {annee} : ancien_decoupage attendu TRUE, trouvé {flag}"

    def test_annees_recentes_pas_ancien_decoupage(self, con):
        """2012+ doivent avoir ancien_decoupage = FALSE."""
        rows = con.execute("""
            SELECT DISTINCT annee, ancien_decoupage
            FROM v_scores_circo_legi
            WHERE code_circo = '59-21' AND annee >= 2012
        """).fetchall()
        for annee, flag in rows:
            assert flag is False, f"Annee {annee} : ancien_decoupage attendu FALSE, trouvé {flag}"


class TestGeoCircos:
    """Géométries des circos HdF pour la carte d'ensemble."""

    def test_cinquante_circos_geo(self, con):
        """50 circos HdF dans geographies_circonscriptions."""
        n = con.execute(  # noqa: S608
            f"SELECT COUNT(*) FROM geographies_circonscriptions "
            f"WHERE code_departement IN ({_HDF_DEPTS_SQL})"
        ).fetchone()[0]
        assert n == 50, f"Attendu 50 circos HdF, trouvé {n}"

    def test_geometry_non_nulle(self, con):
        """Toutes les circos HdF ont une géométrie simplifiée."""
        n_null = con.execute(  # noqa: S608
            f"SELECT COUNT(*) FROM geographies_circonscriptions "
            f"WHERE code_departement IN ({_HDF_DEPTS_SQL}) "
            f"AND (geometry_simplified_circo IS NULL OR ST_IsEmpty(geometry_simplified_circo))"
        ).fetchone()[0]
        assert n_null == 0, f"{n_null} circos HdF sans géométrie"

    def test_bounds_hdf_plausibles(self, con):
        """Les bounds HdF sont dans la zone géographique attendue."""
        row = con.execute(  # noqa: S608
            f"SELECT MIN(ST_YMin(geometry_simplified_circo)), MIN(ST_XMin(geometry_simplified_circo)), "
            f"MAX(ST_YMax(geometry_simplified_circo)), MAX(ST_XMax(geometry_simplified_circo)) "
            f"FROM geographies_circonscriptions WHERE code_departement IN ({_HDF_DEPTS_SQL})"
        ).fetchone()
        miny, minx, maxy, maxx = row
        # bounds réels : (48.84, 1.38, 51.09, 4.26) — vérifiés sur la DB
        assert 48.0 <= miny <= 50.0, f"lat_min hors zone : {miny}"
        assert 50.5 <= maxy <= 52.0, f"lat_max hors zone : {maxy}"
        assert 0.5 <= minx <= 2.5, f"lon_min hors zone : {minx}"
        assert 3.5 <= maxx <= 5.0, f"lon_max hors zone : {maxx}"


# ── Tests via fonctions elections_legi_queries (coverage) ────────────────────


@pytest.fixture(scope="module")
def db_ready() -> bool:
    """Vérifie que la DB et les données legi sont disponibles."""
    db_path = Path(__file__).resolve().parent.parent / "data" / "ministere.duckdb"
    if not db_path.exists():
        pytest.skip("DB absente")
    return True


class TestLegiFunctionsInterface:
    """Appelle les vraies fonctions pour garantir couverture + contrat d'interface."""

    def test_is_legi_data_loaded(self, db_ready):
        assert is_legi_data_loaded() is True

    def test_get_circos_hdf_legi_returns_50(self, db_ready):
        circos = get_circos_hdf_legi()
        assert len(circos) == 50
        codes = [c[0] for c in circos]
        assert "59-21" in codes
        assert all(" — " in display for _, display in circos)

    def test_get_scores_hdf_legi_schema(self, db_ready):
        df = get_scores_hdf_legi(2022, 1)
        assert isinstance(df, pl.DataFrame)
        assert {"code_circo", "bloc", "voix"}.issubset(df.columns)
        assert df["code_circo"].n_unique() == 50

    def test_get_participation_hdf_legi(self, db_ready):
        df = get_participation_hdf_legi(2022, 1)
        assert len(df) == 50
        assert df["taux_participation_pct"].min() > 0

    def test_get_evolution_hdf_legi(self, db_ready):
        df = get_evolution_hdf_legi()
        assert df["annee"].n_unique() == 6
        assert "ancien_decoupage" in df.columns

    def test_get_evolution_circo_legi_59_21(self, db_ready):
        df = get_evolution_circo_legi("59-21")
        assert df["annee"].n_unique() == 6
        old = df.filter(pl.col("annee").is_in([2002, 2007]))["ancien_decoupage"].to_list()
        assert all(old)

    def test_get_scores_communes_circo_legi(self, db_ready):
        df = get_scores_communes_circo_legi(2022, 1, "59-21")
        assert not df.is_empty()
        assert df["voix"].min() >= 0

    def test_get_communes_circo_legi_geo(self, db_ready):
        df = get_communes_circo_legi_geo(2022, 1, "59-21")
        assert 15 <= len(df) <= 25
        assert df["geojson"].null_count() == 0

    def test_get_participation_communes_circo_legi(self, db_ready):
        df = get_participation_communes_circo_legi(2022, 1, "59-21")
        assert not df.is_empty()
        assert (df["votants"] <= df["inscrits"]).all()

    def test_get_nuances_circo_legi(self, db_ready):
        df = get_nuances_circo_legi(2022, 1, "59-21")
        assert not df.is_empty()
        blocs = set(df["bloc"].to_list())
        assert {"GAU", "DTE", "EXD"}.issubset(blocs)

    def test_get_circos_hdf_geo_count(self, db_ready):
        df = get_circos_hdf_geo()
        assert len(df) == 50
        assert "geojson" in df.columns

    def test_get_hdf_bounds_circo(self, db_ready):
        bounds = get_hdf_bounds_circo()
        assert bounds is not None
        assert len(bounds) == 2
        miny, minx = bounds[0]
        assert 48.0 <= miny <= 50.0
        assert 0.5 <= minx <= 2.5

    def test_get_circo_bounds(self, db_ready):
        bounds = get_circo_bounds("59-21")
        assert bounds is not None
        miny, minx = bounds[0]
        maxy, maxx = bounds[1]
        assert miny < maxy
        assert minx < maxx

    def test_empty_result_on_unknown_circo(self, db_ready):
        """Circo inexistante retourne DataFrame vide, pas d'exception."""
        df = get_scores_communes_circo_legi(2022, 1, "99-99")
        assert df.is_empty()

    def test_empty_result_on_missing_annee(self, db_ready):
        """Année sans données retourne DataFrame vide."""
        df = get_scores_hdf_legi(1900, 1)
        assert df.is_empty()


# ── Tests BV-level (D2) ───────────────────────────────────────────────────────


class TestGetCommunesCircoLegiList:
    """get_communes_circo_legi_list → communes d'une circo pour un scrutin."""

    def test_count_communes_59_21_2022(self, db_ready):
        rows = get_communes_circo_legi_list(2022, 1, "59-21")
        assert len(rows) == 20, f"Attendu 20 communes pour 59-21, trouvé {len(rows)}"

    def test_format_tuple(self, db_ready):
        rows = get_communes_circo_legi_list(2022, 1, "59-21")
        code, nom = rows[0]
        assert isinstance(code, str) and len(code) == 5
        assert isinstance(nom, str) and len(nom) > 0

    def test_sorted_by_nom(self, db_ready):
        rows = get_communes_circo_legi_list(2022, 1, "59-21")
        noms = [r[1] for r in rows]
        assert noms == sorted(noms)

    def test_valenciennes_presente(self, db_ready):
        rows = get_communes_circo_legi_list(2022, 1, "59-21")
        codes = [r[0] for r in rows]
        assert "59606" in codes, "Valenciennes (59606) absente de 59-21"

    def test_circo_inconnue_retourne_vide(self, db_ready):
        rows = get_communes_circo_legi_list(2022, 1, "99-99")
        assert rows == []


class TestGetMetricsCommuneLegi:
    """get_metrics_commune_legi → métriques agrégées d'une commune."""

    def test_valenciennes_2022_t1(self, db_ready):
        m = get_metrics_commune_legi(2022, 1, "59606")
        assert m["inscrits"] > 20000
        assert 0.0 <= m["taux_participation_pct"] <= 100.0
        assert m["bloc_dominant"] in {"EXG", "GAU", "DIV", "CENT", "DTE", "EXD"}
        assert m["votants"] <= m["inscrits"]

    def test_commune_inconnue_retourne_zeros(self, db_ready):
        m = get_metrics_commune_legi(2022, 1, "99999")
        assert m["inscrits"] == 0
        assert m["votants"] == 0


class TestGetBvDetailsLegi:
    """get_bv_details_legi → détail BV avec pivot des voix par bloc."""

    _BLOCS = ["EXG", "GAU", "DIV", "CENT", "DTE", "EXD"]

    def test_valenciennes_2022_t1_non_vide(self, db_ready):
        df = get_bv_details_legi(2022, 1, "59606")
        assert not df.is_empty()
        assert len(df) == 23, f"Attendu 23 BV pour Valenciennes, trouvé {len(df)}"

    def test_colonnes_attendues(self, db_ready):
        df = get_bv_details_legi(2022, 1, "59606")
        expected = {
            "code_bv",
            "inscrits",
            "votants",
            "exprimes",
            "taux_participation_pct",
            "bloc_gagnant",
        } | {f"voix_{b}" for b in self._BLOCS}
        assert expected.issubset(set(df.columns)), (
            f"Colonnes manquantes : {expected - set(df.columns)}"
        )

    def test_somme_inscrits_bv_egal_commune(self, db_ready):
        df = get_bv_details_legi(2022, 1, "59606")
        metrics = get_metrics_commune_legi(2022, 1, "59606")
        assert int(df["inscrits"].sum()) == metrics["inscrits"]

    def test_taux_participation_bornes(self, db_ready):
        df = get_bv_details_legi(2022, 1, "59606")
        assert (df["taux_participation_pct"] >= 0.0).all()
        assert (df["taux_participation_pct"] <= 100.0).all()

    def test_voix_blocs_non_negatifs(self, db_ready):
        df = get_bv_details_legi(2022, 1, "59606")
        for b in self._BLOCS:
            assert (df[f"voix_{b}"] >= 0).all()

    def test_bloc_gagnant_valide(self, db_ready):
        df = get_bv_details_legi(2022, 1, "59606")
        blocs_valides = set(self._BLOCS)
        assert set(df["bloc_gagnant"].to_list()).issubset(blocs_valides)

    def test_commune_inconnue_retourne_vide(self, db_ready):
        df = get_bv_details_legi(2022, 1, "99999")
        assert df.is_empty()
