"""Tests Python purs — requêtes BV-level pour les présidentielles (D2).

Prérequis : DB chargée (init_elections_schema.py + load_elections_presidentielles.py)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ministere_de_l_info.viz.elections_queries import (  # noqa: E402
    _BLOCS_ORDERED,
    get_bv_details_pres,
    get_communes_hdf_pres,
    get_metrics_commune_pres,
)

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "ministere.duckdb"

_HDF_DEPTS = {"02", "59", "60", "62", "80"}


@pytest.fixture(scope="module")
def db_ready():
    if not DB_PATH.exists():
        pytest.skip(
            "DB absente. Lancer init_elections_schema.py + load_elections_presidentielles.py"
        )
    import duckdb

    con = duckdb.connect(str(DB_PATH), read_only=True)
    n = con.execute(
        "SELECT COUNT(*) FROM resultats_candidats WHERE id_election LIKE '%_pres_%'"
    ).fetchone()[0]
    con.close()
    if n == 0:
        pytest.skip("Présidentielles non chargées. Lancer load_elections_presidentielles.py")


class TestGetCommunesHdfPres:
    """get_communes_hdf_pres → ~3781 communes HdF pour un scrutin."""

    def test_count_2022_t1(self, db_ready):
        rows = get_communes_hdf_pres(2022, 1)
        assert len(rows) >= 3700, f"Attendu ≥ 3700 communes HdF, trouvé {len(rows)}"

    def test_format_tuple(self, db_ready):
        rows = get_communes_hdf_pres(2022, 1)
        code, nom = rows[0]
        assert isinstance(code, str) and len(code) == 5
        assert isinstance(nom, str) and len(nom) > 0

    def test_sorted_by_nom(self, db_ready):
        rows = get_communes_hdf_pres(2022, 1)
        noms = [r[1] for r in rows]
        assert noms == sorted(noms)

    def test_depts_hdf_couverts(self, db_ready):
        rows = get_communes_hdf_pres(2022, 1)
        depts = {code[:2] for code, _ in rows}
        assert _HDF_DEPTS.issubset(depts), f"Depts manquants : {_HDF_DEPTS - depts}"

    def test_lille_presente(self, db_ready):
        rows = get_communes_hdf_pres(2022, 1)
        codes = {r[0] for r in rows}
        assert "59350" in codes, "Lille (59350) absente"

    def test_annee_inconnue_retourne_vide(self, db_ready):
        rows = get_communes_hdf_pres(1900, 1)
        assert rows == []


class TestGetMetricsCommunePres:
    """get_metrics_commune_pres → métriques agrégées d'une commune."""

    def test_lille_2022_t1(self, db_ready):
        m = get_metrics_commune_pres(2022, 1, "59350")
        assert m["inscrits"] > 100_000
        assert 0.0 <= m["taux_participation_pct"] <= 100.0
        assert m["bloc_dominant"] in set(_BLOCS_ORDERED)
        assert m["votants"] <= m["inscrits"]
        assert m["exprimes"] <= m["votants"]

    def test_cles_presentes(self, db_ready):
        m = get_metrics_commune_pres(2022, 1, "59350")
        assert {
            "inscrits",
            "votants",
            "exprimes",
            "taux_participation_pct",
            "bloc_dominant",
        } == set(m)

    def test_commune_inconnue_retourne_zeros(self, db_ready):
        m = get_metrics_commune_pres(2022, 1, "99999")
        assert m["inscrits"] == 0
        assert m["votants"] == 0


class TestGetBvDetailsPres:
    """get_bv_details_pres → détail BV avec pivot des voix par bloc."""

    def test_lille_2022_t1_non_vide(self, db_ready):
        df = get_bv_details_pres(2022, 1, "59350")
        assert not df.is_empty()
        assert len(df) == 127, f"Attendu 127 BV pour Lille, trouvé {len(df)}"

    def test_colonnes_attendues(self, db_ready):
        df = get_bv_details_pres(2022, 1, "59350")
        expected = {
            "code_bv",
            "inscrits",
            "votants",
            "exprimes",
            "taux_participation_pct",
            "bloc_gagnant",
        } | {f"voix_{b}" for b in _BLOCS_ORDERED}
        assert expected.issubset(set(df.columns)), (
            f"Colonnes manquantes : {expected - set(df.columns)}"
        )

    def test_somme_inscrits_bv_egal_commune(self, db_ready):
        df = get_bv_details_pres(2022, 1, "59350")
        metrics = get_metrics_commune_pres(2022, 1, "59350")
        assert int(df["inscrits"].sum()) == metrics["inscrits"]

    def test_taux_participation_bornes(self, db_ready):
        df = get_bv_details_pres(2022, 1, "59350")
        assert (df["taux_participation_pct"] >= 0.0).all()
        assert (df["taux_participation_pct"] <= 100.0).all()

    def test_voix_blocs_non_negatifs(self, db_ready):
        df = get_bv_details_pres(2022, 1, "59350")
        for b in _BLOCS_ORDERED:
            assert (df[f"voix_{b}"] >= 0).all()

    def test_bloc_gagnant_valide(self, db_ready):
        df = get_bv_details_pres(2022, 1, "59350")
        blocs_valides = set(_BLOCS_ORDERED)
        assert set(df["bloc_gagnant"].to_list()).issubset(blocs_valides)

    def test_trie_par_code_bv(self, db_ready):
        df = get_bv_details_pres(2022, 1, "59350")
        bvs = df["code_bv"].to_list()
        assert bvs == sorted(bvs)

    def test_commune_inconnue_retourne_vide(self, db_ready):
        df = get_bv_details_pres(2022, 1, "99999")
        assert df.is_empty()
