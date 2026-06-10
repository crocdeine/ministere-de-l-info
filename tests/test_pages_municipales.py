"""Tests Python purs — requêtes SQL pour la page Municipales (D3.3).

Deux niveaux :
- Via fonctions elections_muni_queries (coverage + contrat d'interface)
- Via SQL direct DuckDB (assertions granulaires indépendantes du cache)

Prérequis : DB chargée (load_elections_municipales.py + 0007_add_municipales_views.py)
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import polars as pl
import pytest

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))

from ministere_de_l_info.viz.elections_muni_queries import (  # noqa: E402
    get_communes_hdf_muni_list,
    get_communes_muni_geo,
    get_evolution_blocs_hdf_muni,
    get_hdf_bounds_communes,
    get_listes_commune_muni,
    get_metrics_commune_muni,
    get_scores_bloc_commune_muni,
    get_scores_communes_muni,
    get_scrutins_muni,
    get_seuil_nuancage_par_annee,
)

DB_PATH = _ROOT / "data" / "ministere.duckdb"

_LILLE = "59350"
_PETITE_COMMUNE_2026 = "59001"  # Abancourt — population << 3500 hab


@pytest.fixture(scope="module")
def con() -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        pytest.skip("DB absente. Lancer load_elections_municipales.py")
    c = duckdb.connect(str(DB_PATH), read_only=True)
    n = c.execute(
        "SELECT COUNT(*) FROM resultats_participation WHERE id_election LIKE '%_muni_%'"
    ).fetchone()[0]
    if n == 0:
        pytest.skip("Municipales non chargées. Lancer load_elections_municipales.py")
    yield c
    c.close()


@pytest.fixture(scope="module")
def db_ready() -> bool:
    if not DB_PATH.exists():
        pytest.skip("DB absente")
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        n = con.execute(
            "SELECT COUNT(*) FROM resultats_participation WHERE id_election LIKE '%_muni_%'"
        ).fetchone()[0]
        if n == 0:
            pytest.skip("Municipales non chargées")
        return True
    finally:
        con.close()


# ── Tests SQL directs ─────────────────────────────────────────────────────────


class TestVuesSQL:
    """Vérifications directes sur les 3 vues créées en D3.2."""

    def test_v_scores_commune_muni_non_vide(self, con):
        n = con.execute("SELECT COUNT(*) FROM v_scores_commune_muni").fetchone()[0]
        assert n > 0

    def test_v_scores_commune_muni_bloc_null_present(self, con):
        n = con.execute("SELECT COUNT(*) FROM v_scores_commune_muni WHERE bloc IS NULL").fetchone()[
            0
        ]
        assert n > 0, "Aucune ligne avec bloc NULL — LEFT JOIN probablement rompu"

    def test_v_evolution_blocs_hdf_muni_huit_scrutins(self, con):
        n = con.execute(
            "SELECT COUNT(DISTINCT annee || '_t' || CAST(tour AS VARCHAR)) "
            "FROM v_evolution_blocs_hdf_muni"
        ).fetchone()[0]
        assert n == 8, f"Attendu 8 scrutins dans v_evolution, trouvé {n}"

    def test_v_listes_commune_muni_non_vide(self, con):
        n = con.execute("SELECT COUNT(*) FROM v_listes_commune_muni").fetchone()[0]
        assert n > 0

    def test_pct_exprimes_null_pour_bloc_null(self, con):
        """Cohérence D3.2 : pct_exprimes = NULL quand bloc = NULL."""
        n = con.execute(
            "SELECT COUNT(*) FROM v_scores_commune_muni "
            "WHERE bloc IS NULL AND pct_exprimes IS NOT NULL"
        ).fetchone()[0]
        assert n == 0, f"{n} lignes avec bloc NULL et pct non NULL — incohérence"

    def test_documentation_lacune_source_2008(self, con):
        """Documente la lacune source 2008 sur le département Nord (59).

        Ce test NE FAILLIT PAS — il documente une caractéristique persistante
        de la source data.gouv.fr pour les municipales 2008. Voir ADR-0005
        § "Limitation de la source data.gouv.fr 2008".
        """
        n_communes_59 = con.execute("""
            SELECT COUNT(DISTINCT code_commune)
            FROM resultats_candidats
            WHERE id_election = '2008_muni_t1'
            AND code_departement = '59'
        """).fetchone()[0]
        # Seules Seclin (59560) et Pérenchies (59457) sont dans le Parquet 2008
        assert n_communes_59 == 2, (
            f"Lacune source 2008 dept 59 : attendu 2, trouvé {n_communes_59}. "
            "Si ce nombre change, vérifier si data.gouv.fr a republié le fichier 2008."
        )


class TestGetScrutinsMuni:
    """get_scrutins_muni : 8 scrutins, ordre, labels."""

    def test_huit_scrutins(self, db_ready):
        scrutins = get_scrutins_muni()
        assert len(scrutins) == 8, f"Attendu 8 scrutins, trouvé {len(scrutins)}"

    def test_format_tuple(self, db_ready):
        scrutins = get_scrutins_muni()
        annee, tour, label = scrutins[0]
        assert isinstance(annee, int)
        assert tour in (1, 2)
        assert str(annee) in label

    def test_ordre_annee_desc(self, db_ready):
        scrutins = get_scrutins_muni()
        annees = [s[0] for s in scrutins]
        assert annees[0] >= annees[-1], "Le scrutin le plus récent doit être en premier"

    def test_label_lisible(self, db_ready):
        scrutins = get_scrutins_muni()
        labels = [s[2] for s in scrutins]
        assert any("Municipales 2026" in lbl for lbl in labels)
        assert any("1er tour" in lbl for lbl in labels)


class TestGetScoresCommunes2026:
    """get_scores_communes_muni : volume et colonnes."""

    def test_colonnes_presentes(self, db_ready):
        df = get_scores_communes_muni(2026, 1)
        assert {"code_commune", "bloc", "voix", "pct_exprimes"} <= set(df.columns)

    def test_volume_plausible_2026(self, db_ready):
        df = get_scores_communes_muni(2026, 1)
        n_communes = df["code_commune"].n_unique()
        assert n_communes >= 100, f"Trop peu de communes 2026 t1 : {n_communes}"

    def test_bloc_null_present_2026(self, db_ready):
        df = get_scores_communes_muni(2026, 1)
        n_null = df.filter(pl.col("bloc").is_null()).height
        assert n_null > 0, "Bloc NULL absent en 2026 — LEFT JOIN rompu"

    def test_voix_positives(self, db_ready):
        df = get_scores_communes_muni(2026, 1)
        assert (df["voix"] > 0).all()


class TestGetCommunesMuniGeo:
    """get_communes_muni_geo : toutes communes HdF préservées avec LEFT JOIN."""

    def test_toutes_communes_hdf(self, db_ready):
        df = get_communes_muni_geo(2026, 1)
        n = df.height
        assert n >= 3_700, f"Trop peu de communes : {n} (attendu ~3782)"

    def test_bloc_null_preservé(self, db_ready):
        df = get_communes_muni_geo(2026, 1)
        n_null = df.filter(pl.col("bloc_dominant").is_null()).height
        assert n_null > 0, "Aucune commune avec bloc_dominant NULL — LEFT JOIN rompu"

    def test_communes_nuancees_2026(self, db_ready):
        df = get_communes_muni_geo(2026, 1)
        n_nuancee = df.filter(pl.col("bloc_dominant").is_not_null()).height
        assert 280 <= n_nuancee <= 400, f"Communes nuancées 2026 : {n_nuancee} (attendu ~320)"

    def test_communes_nuancees_2008_peu(self, db_ready):
        df = get_communes_muni_geo(2008, 1)
        n_nuancee = df.filter(pl.col("bloc_dominant").is_not_null()).height
        assert 100 <= n_nuancee <= 200, f"Communes nuancées 2008 : {n_nuancee} (attendu ~164)"

    def test_geojson_non_null(self, db_ready):
        df = get_communes_muni_geo(2026, 1)
        n_null_geo = df.filter(pl.col("geojson").is_null()).height
        assert n_null_geo == 0, f"{n_null_geo} communes sans géométrie"


class TestGetMetricsCommune:
    """get_metrics_commune_muni : grande commune → nuancée, petite → non nuancée."""

    def test_lille_est_nuancee(self, db_ready):
        m = get_metrics_commune_muni(2026, 1, _LILLE)
        assert m["est_nuancee"] is True, "Lille doit être nuancée en 2026"
        assert m["inscrits"] > 0
        assert m["bloc_dominant"] is not None

    def test_lille_participation_coherente(self, db_ready):
        m = get_metrics_commune_muni(2026, 1, _LILLE)
        assert 0 < m["taux_participation_pct"] <= 100

    def test_petite_commune_non_nuancee_2026(self, db_ready):
        m = get_metrics_commune_muni(2026, 1, _PETITE_COMMUNE_2026)
        # Si la commune est absente du Parquet (pas de données du tout), on skip
        if m["inscrits"] == 0:
            pytest.skip(f"Commune {_PETITE_COMMUNE_2026} absente du Parquet 2026")
        assert m["est_nuancee"] is False, (
            f"La commune {_PETITE_COMMUNE_2026} ne devrait pas être nuancée en 2026 "
            f"(bloc_dominant={m['bloc_dominant']})"
        )

    def test_schema_complet(self, db_ready):
        m = get_metrics_commune_muni(2026, 1, _LILLE)
        for key in (
            "inscrits",
            "votants",
            "exprimes",
            "taux_participation_pct",
            "nb_listes",
            "est_nuancee",
            "bloc_dominant",
        ):
            assert key in m, f"Clé manquante : {key}"


class TestGetScoresBlocCommune:
    """get_scores_bloc_commune_muni : Lille doit avoir des blocs renseignés."""

    def test_lille_a_des_blocs(self, db_ready):
        df = get_scores_bloc_commune_muni(2026, 1, _LILLE)
        n_blocs = df.filter(pl.col("bloc").is_not_null()).height
        assert n_blocs >= 2, f"Lille 2026 t1 : seulement {n_blocs} blocs classés"

    def test_colonnes_presentes(self, db_ready):
        df = get_scores_bloc_commune_muni(2026, 1, _LILLE)
        assert {"bloc", "voix", "pct_exprimes"} <= set(df.columns)

    def test_ordre_voix_desc(self, db_ready):
        df = get_scores_bloc_commune_muni(2026, 1, _LILLE)
        classe = df.filter(pl.col("bloc").is_not_null())
        if classe.height >= 2:
            voix = classe["voix"].to_list()
            assert voix == sorted(voix, reverse=True), "Blocs non triés par voix DESC"


class TestGetListesCommune:
    """get_listes_commune_muni : contenu et colonnes."""

    def test_lille_2020_a_plusieurs_listes(self, db_ready):
        df = get_listes_commune_muni(2020, 1, _LILLE)
        assert df.height >= 4, f"Lille 2020 t1 : seulement {df.height} listes"

    def test_colonnes_presentes(self, db_ready):
        df = get_listes_commune_muni(2026, 1, _LILLE)
        required = {"nuance", "bloc", "voix", "rang", "label_affichage"}
        assert required <= set(df.columns)

    def test_rang_sequentiel(self, db_ready):
        df = get_listes_commune_muni(2026, 1, _LILLE)
        rangs = sorted(df["rang"].to_list())
        assert rangs == list(range(1, len(rangs) + 1))

    def test_label_affichage_non_vide(self, db_ready):
        df = get_listes_commune_muni(2026, 1, _LILLE)
        for lbl in df["label_affichage"].to_list():
            assert lbl and len(lbl) > 0, "label_affichage vide ou NULL"


class TestGetEvolutionHdfMuni:
    """get_evolution_blocs_hdf_muni : colonnes, présence de NULL, 4 années."""

    def test_colonnes(self, db_ready):
        df = get_evolution_blocs_hdf_muni()
        assert {"annee", "tour", "bloc", "voix", "pct_exprimes"} <= set(df.columns)

    def test_quatre_annees(self, db_ready):
        df = get_evolution_blocs_hdf_muni()
        annees = set(df["annee"].to_list())
        assert {2008, 2014, 2020, 2026} <= annees

    def test_bloc_null_present(self, db_ready):
        df = get_evolution_blocs_hdf_muni()
        n_null = df.filter(pl.col("bloc").is_null()).height
        assert n_null > 0, "Bloc NULL absent de v_evolution — NC/plurinominal non capturé"


class TestGetCommunesMuniList:
    """get_communes_hdf_muni_list : liste communes pour le selectbox."""

    def test_liste_non_vide_2026(self, db_ready):
        communes = get_communes_hdf_muni_list(2026, 1)
        assert len(communes) >= 100

    def test_format_tuple(self, db_ready):
        communes = get_communes_hdf_muni_list(2026, 1)
        code, nom = communes[0]
        assert len(code) == 5, f"Code INSEE invalide : {code!r}"
        assert nom and len(nom) > 0

    def test_lille_presente_2026(self, db_ready):
        communes = get_communes_hdf_muni_list(2026, 1)
        codes = [c[0] for c in communes]
        assert _LILLE in codes, "Lille (59350) absente de la liste 2026"

    def test_tri_par_nom(self, db_ready):
        communes = get_communes_hdf_muni_list(2026, 1)
        noms = [c[1] for c in communes]
        assert noms == sorted(noms), "Communes non triées par nom"


class TestSeuils:
    """get_seuil_nuancage_par_annee : valeurs statiques."""

    def test_seuil_2008(self):
        s = get_seuil_nuancage_par_annee(2008)
        assert s["seuil_hab"] == 3500
        assert s["n_communes_nuancees_hdf"] == 164

    def test_seuil_2014(self):
        s = get_seuil_nuancage_par_annee(2014)
        assert s["seuil_hab"] == 1000

    def test_seuil_2020(self):
        s = get_seuil_nuancage_par_annee(2020)
        assert s["seuil_hab"] == 3500
        assert "INTA1931378J" in s["circulaire"]

    def test_seuil_2026(self):
        s = get_seuil_nuancage_par_annee(2026)
        assert s["seuil_hab"] == 3500
        assert s["n_communes_nuancees_hdf"] == 320
        assert "INTP2602966C" in s["circulaire"]
        assert "512694" in s.get("ce_validation", "")


class TestHdfBounds:
    """get_hdf_bounds_communes : bounding box cohérente."""

    def test_bounds_plausibles(self, db_ready):
        bounds = get_hdf_bounds_communes()
        if bounds is None:
            pytest.skip("Géométries absentes")
        miny, minx = bounds[0]
        maxy, maxx = bounds[1]
        # HdF : latitude ~48.8-51.1 (Oise au sud), longitude ~1.5-4.2
        assert 48.5 <= miny <= 50.0
        assert 50.0 <= maxy <= 52.0
        assert 1.0 <= minx <= 3.0
        assert 2.5 <= maxx <= 5.0
