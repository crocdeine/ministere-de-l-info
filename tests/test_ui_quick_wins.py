"""Tests des corrections rapides UX (vague 2) — base DuckDB en mémoire ou temporaire.

Exécutables en CI sans la base réelle ni l'extension spatial :
- participation agrégée pondérée (audit I4) ;
- tableau Géographie : filtre dans le WHERE, sans limite de 200 lignes (audit I6) ;
- Économie : millésimes RP sans Filosofi (audit I5), agrégat chômage pondéré (I4),
  croisement au 1er tour et années exploitables ;
- messages « base absente » sans trace Python (AppTest).
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import polars as pl
import pytest

from ministere_de_l_info.viz import economie_queries as eq
from ministere_de_l_info.viz._queries import get_tableau_territoires
from ministere_de_l_info.viz.elections_queries import format_pct_fr, taux_participation_agrege

ROOT = Path(__file__).resolve().parent.parent

# ── Participation pondérée ──────────────────────────────────────────────────────


class TestParticipationAgregee:
    def test_ponderation_par_inscrits(self) -> None:
        """Lille (100 000 inscrits, 50 %) et un village (80 inscrits, 90 %)."""
        df = pl.DataFrame(
            {
                "code_commune": ["59350", "59001"],
                "inscrits": [100_000, 80],
                "votants": [50_000, 72],
                "taux_participation_pct": [50.0, 90.0],
            }
        )
        taux = taux_participation_agrege(df)
        assert taux == pytest.approx(100.0 * 50_072 / 100_080)
        # L'ancienne moyenne non pondérée donnait 70 %.
        assert taux != pytest.approx(df["taux_participation_pct"].mean())

    def test_vide_renvoie_none(self) -> None:
        df = pl.DataFrame(schema={"inscrits": pl.Int64, "votants": pl.Int64})
        assert taux_participation_agrege(df) is None

    def test_lignes_incompletes_exclues(self) -> None:
        df = pl.DataFrame({"inscrits": [100, 200, None], "votants": [50, None, 10]})
        assert taux_participation_agrege(df) == pytest.approx(50.0)

    def test_zero_inscrit(self) -> None:
        df = pl.DataFrame({"inscrits": [0], "votants": [0]})
        assert taux_participation_agrege(df) is None

    def test_format_fr(self) -> None:
        assert format_pct_fr(72.44) == "72,4 %"
        assert format_pct_fr(None) == "n.d."
        assert format_pct_fr(float("nan")) == "n.d."


# ── Tableau Géographie ──────────────────────────────────────────────────────────


@pytest.fixture
def con_geo() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE geographies_departements (code_insee VARCHAR, nom VARCHAR, code_region VARCHAR)"
    )
    con.execute(
        "INSERT INTO geographies_departements VALUES "
        "('59', 'Nord', '32'), ('62', 'Pas-de-Calais', '32'), ('75', 'Paris', '11')"
    )
    con.execute(
        "CREATE TABLE v_population_departement "
        "(code_departement VARCHAR, annee INTEGER, population_municipale BIGINT)"
    )
    con.execute(
        "INSERT INTO v_population_departement VALUES "
        "('59', 2023, 2600000), ('62', 2023, 1450000), ('75', 2023, 2100000), "
        "('59', 2018, 2590000), ('75', 2018, 2150000)"
    )
    con.execute(
        "CREATE TABLE geographies_communes "
        "(code_insee VARCHAR, nom VARCHAR, code_departement VARCHAR, code_region VARCHAR)"
    )
    # 250 communes dans le 59 (dont une sans population), 3 dans le 62
    con.execute(
        "INSERT INTO geographies_communes "
        "SELECT '59' || lpad(i::VARCHAR, 3, '0'), 'Commune ' || i, '59', '32' "
        "FROM range(1, 251) t(i)"
    )
    con.execute(
        "INSERT INTO geographies_communes VALUES "
        "('62001', 'A', '62', '32'), ('62002', 'B', '62', '32'), ('62003', 'C', '62', '32')"
    )
    con.execute(
        "CREATE TABLE v_population_commune "
        "(code_commune VARCHAR, annee INTEGER, population_municipale BIGINT)"
    )
    con.execute(
        "INSERT INTO v_population_commune "
        "SELECT code_insee, 2023, 1000 FROM geographies_communes WHERE code_insee <> '59250'"
    )
    con.execute(
        "CREATE TABLE geographies_circonscriptions "
        "(code VARCHAR, nom VARCHAR, code_departement VARCHAR)"
    )
    con.execute(
        "INSERT INTO geographies_circonscriptions VALUES "
        "('5901', 'Nord 1', '59'), ('6201', 'PdC 1', '62')"
    )
    yield con
    con.close()


class TestTableauGeographie:
    def test_filtre_region_retire_les_autres_entites(self, con_geo) -> None:
        """I6 : Paris ne doit plus apparaître (avec « — ») quand on filtre la région 32."""
        df = get_tableau_territoires(con_geo, "departement", 2023, filtre_region="32")
        assert df["code"].to_list() == ["59", "62"]

    def test_sans_filtre_toutes_entites(self, con_geo) -> None:
        df = get_tableau_territoires(con_geo, "departement", 2023)
        assert df.height == 3

    def test_pas_de_limite_200(self, con_geo) -> None:
        df = get_tableau_territoires(con_geo, "commune", 2023, filtre_departement="59")
        assert df.height == 250
        assert set(df["code"].str.slice(0, 2).to_list()) == {"59"}

    def test_population_absente_reste_nulle(self, con_geo) -> None:
        """Population inconnue : NULL (affiché « n.d. »), jamais 0 ; triée en dernier."""
        df = get_tableau_territoires(con_geo, "commune", 2023, filtre_departement="59")
        derniere = df.row(-1, named=True)
        assert derniere["code"] == "59250"
        assert derniere["population"] is None

    def test_evolution_avec_annee_ref(self, con_geo) -> None:
        df = get_tableau_territoires(
            con_geo, "departement", 2023, annee_ref=2018, filtre_region="32"
        )
        nord = df.filter(pl.col("code") == "59").row(0, named=True)
        assert nord["delta_abs"] == 10000
        assert nord["delta_pct"] == pytest.approx(100.0 * 10000 / 2590000)
        pdc = df.filter(pl.col("code") == "62").row(0, named=True)
        assert pdc["delta_abs"] is None

    def test_circonscriptions_filtrees_par_departement(self, con_geo) -> None:
        df = get_tableau_territoires(con_geo, "circonscription", 2023, filtre_departement="62")
        assert df["code"].to_list() == ["6201"]
        assert df["extra"].to_list() == ["62"]

    def test_niveau_inconnu(self, con_geo) -> None:
        with pytest.raises(ValueError):
            get_tableau_territoires(con_geo, "canton", 2023)


# ── Économie ────────────────────────────────────────────────────────────────────


@pytest.fixture
def base_eco(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Base DuckDB temporaire (fichier) avec un sous-ensemble du schéma Économie/Élections."""
    chemin = tmp_path / "eco.duckdb"
    con = duckdb.connect(str(chemin))
    # Remplace ST_AsGeoJSON (extension spatial indisponible en CI)
    con.execute("CREATE MACRO ST_AsGeoJSON(g) AS CAST(g AS VARCHAR)")
    con.execute(
        "CREATE TABLE geographies_communes (code_insee VARCHAR, nom VARCHAR, "
        "code_region VARCHAR, geometry_simplified_communal VARCHAR)"
    )
    con.execute(
        "INSERT INTO geographies_communes VALUES "
        "('59350', 'Lille', '32', '{}'), ('59001', 'Village', '32', '{}')"
    )
    con.execute(
        "CREATE TABLE economie_filosofi (code_commune VARCHAR, annee INTEGER, "
        "taux_pauvrete DOUBLE, niveau_vie_median DOUBLE, secret BOOLEAN)"
    )
    con.execute(
        "INSERT INTO economie_filosofi VALUES "
        "('59350', 2021, 25.0, 20000, FALSE), ('59001', 2021, 5.0, 24000, FALSE)"
    )
    con.execute(
        "CREATE TABLE economie_rp (code_commune VARCHAR, annee_millesime INTEGER, "
        "tx_chomage_dec DOUBLE, part_ouvriers_employes DOUBLE, part_emploi_industriel DOUBLE, "
        "part_logements_sociaux DOUBLE, pop_active INTEGER, secret BOOLEAN)"
    )
    con.execute(
        "INSERT INTO economie_rp VALUES "
        "('59350', 2016, 18.0, 40.0, 10.0, 30.0, 100000, FALSE), "
        "('59001', 2016, 6.0, 60.0, 20.0, 0.0, 100, FALSE), "
        "('59350', 2021, 16.0, 38.0, 9.0, 29.0, 100000, FALSE), "
        "('59001', 2021, 8.0, 58.0, 19.0, 0.0, 100, FALSE)"
    )
    con.execute("CREATE TABLE elections (id_election VARCHAR, annee INTEGER, type_scrutin VARCHAR)")
    con.execute(
        "INSERT INTO elections VALUES "
        "('2012_pres_t1', 2012, 'pres'), ('2017_pres_t1', 2017, 'pres'), "
        "('2022_pres_t1', 2022, 'pres'), ('2022_pres_t2', 2022, 'pres'), "
        "('2024_legi_t1', 2024, 'legi')"
    )
    con.execute(
        "CREATE TABLE v_scores_commune_pres (code_commune VARCHAR, annee INTEGER, "
        "tour INTEGER, bloc VARCHAR, voix BIGINT)"
    )
    con.execute(
        "INSERT INTO v_scores_commune_pres VALUES "
        "('59350', 2022, 1, 'GAU', 400), ('59350', 2022, 1, 'EXD', 200), "
        "('59350', 2022, 2, 'CENT', 600), "
        "('59001', 2022, 1, 'EXD', 50), ('59001', 2022, 1, 'GAU', 10)"
    )
    con.execute(
        "CREATE TABLE v_participation_commune_pres (code_commune VARCHAR, annee INTEGER, "
        "tour INTEGER, exprimes BIGINT)"
    )
    con.execute(
        "INSERT INTO v_participation_commune_pres VALUES "
        "('59350', 2022, 1, 1000), ('59350', 2022, 2, 900), ('59001', 2022, 1, 100)"
    )
    con.close()

    monkeypatch.setattr(eq, "_open_ro", lambda: duckdb.connect(str(chemin), read_only=True))
    for fonction in (
        eq.get_scores_commune,
        eq.get_economie_commune,
        eq.get_croisement_eco_elections,
        eq.get_evolution_hdf,
        eq.get_annees_presidentielles,
    ):
        fonction.clear()
    return chemin


class TestEconomie:
    def test_carte_rp_millesime_sans_filosofi(self, base_eco) -> None:
        """I5 : RP 2016 existe sans Filosofi 2016 → la carte n'est plus vide."""
        df = eq.get_scores_commune(2016, "tx_chomage_dec")
        valeurs = dict(zip(df["code_commune"], df["valeur"], strict=True))
        assert valeurs == {"59350": 18.0, "59001": 6.0}

    def test_carte_filosofi(self, base_eco) -> None:
        df = eq.get_scores_commune(2021, "taux_pauvrete")
        assert df.filter(pl.col("code_commune") == "59350")["valeur"][0] == 25.0

    def test_detail_commune_inclut_annees_rp_seules(self, base_eco) -> None:
        df = eq.get_economie_commune("59350")
        assert df["annee"].to_list() == [2016, 2021]
        ligne_2016 = df.row(0, named=True)
        assert ligne_2016["taux_pauvrete"] is None
        assert ligne_2016["tx_chomage_dec"] == 18.0

    def test_evolution_chomage_pondere(self, base_eco) -> None:
        """Chômage pondéré par les actifs : Lille domine ; pauvreté non pondérée."""
        df = eq.get_evolution_hdf()
        assert df["annee"].to_list() == [2016, 2021]
        ligne_2021 = df.filter(pl.col("annee") == 2021).row(0, named=True)
        attendu = (16.0 * 100000 + 8.0 * 100) / 100100
        assert ligne_2021["tx_chomage_pondere"] == pytest.approx(attendu)
        assert ligne_2021["taux_pauvrete_moyen"] == pytest.approx(15.0)
        ligne_2016 = df.filter(pl.col("annee") == 2016).row(0, named=True)
        assert ligne_2016["taux_pauvrete_moyen"] is None
        assert ligne_2016["tx_chomage_pondere"] == pytest.approx(
            (18.0 * 100000 + 6.0 * 100) / 100100
        )

    def test_annees_croisement_exploitables(self) -> None:
        pres = [2002, 2007, 2012, 2017, 2022]
        assert eq.annees_croisement_exploitables(pres, [2017, 2018, 2019, 2020, 2021]) == [2022]
        assert eq.annees_croisement_exploitables(pres, list(range(2015, 2022))) == [2017, 2022]
        assert eq.annees_croisement_exploitables(pres, []) == []

    def test_annees_presidentielles(self, base_eco) -> None:
        assert eq.get_annees_presidentielles() == [2012, 2017, 2022]

    def test_croisement_premier_tour(self, base_eco) -> None:
        df = eq.get_croisement_eco_elections(2022, bloc="GAU", tour=1)
        lille = df.filter(pl.col("code_commune") == "59350").row(0, named=True)
        assert lille["pct_voix"] == pytest.approx(40.0)
        assert lille["taux_pauvrete"] == 25.0
        assert lille["tx_chomage_dec"] == 16.0

    def test_croisement_second_tour_bloc_absent(self, base_eco) -> None:
        assert eq.get_croisement_eco_elections(2022, bloc="GAU", tour=2).is_empty()
        assert eq.get_croisement_eco_elections(2022, bloc="CENT", tour=2).height == 1

    def test_croisement_tour_invalide(self, base_eco) -> None:
        with pytest.raises(ValueError):
            eq.get_croisement_eco_elections(2022, bloc="GAU", tour=3)

    def test_rsa_libelle_nombre(self) -> None:
        assert "nombre" in eq.get_indicateurs()["nb_foyers_rsa"]


# ── Onglets paresseux : conservation des sélections ────────────────────────────


def _script_onglets() -> None:
    import streamlit as st

    from ministere_de_l_info._theme import conserver_selections

    conserver_selections("onglet", {"A": ("a_",), "B": ("b_",)})
    ta, tb = st.tabs(["A", "B"], key="onglet", on_change="rerun")
    with ta:
        if ta.open:
            st.selectbox("Choix A", ["x", "y", "z"], index=0, key="a_sel")
    with tb:
        if tb.open:
            st.write("onglet B")


class TestOngletsParesseux:
    def test_selection_conservee_apres_changement_onglet(self) -> None:
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_function(_script_onglets)
        at.run()
        at.selectbox(key="a_sel").set_value("y").run()
        # AppTest ne modélise pas l'état des onglets : on le fixe via la clé.
        at.session_state["onglet"] = "B"
        at.run()
        assert not at.selectbox  # onglet A non exécuté
        at.session_state["onglet"] = "A"
        at.run()
        assert not at.exception
        assert at.selectbox(key="a_sel").value == "y"


# ── Messages « base absente » (AppTest, sans base) ──────────────────────────────


def _textes(at) -> str:  # noqa: ANN001
    blocs = [w.value for w in at.warning] + [e.value for e in at.error]
    return "\n".join(str(b) for b in blocs)


class TestBaseAbsente:
    @pytest.fixture(autouse=True)
    def _base_absente(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        absente = tmp_path / "absente.duckdb"
        monkeypatch.setattr(eq, "DB_PATH", absente)
        eq.is_data_loaded.clear()
        from ministere_de_l_info.viz import elections_queries

        monkeypatch.setattr(elections_queries, "DB_PATH", absente)

    def test_economie_sans_trace(self) -> None:
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(ROOT / "pages" / "4_📊_Économie.py"), default_timeout=30)
        at.run()
        assert not at.exception
        assert "base de données est introuvable" in _textes(at)
        assert "update.sh" in _textes(at)

    def test_elections_sans_trace(self) -> None:
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(ROOT / "pages" / "2_🗳️_Élections.py"), default_timeout=30)
        at.run()
        assert not at.exception
        assert "base de données est introuvable" in _textes(at)

    def test_geographie_sans_script_obsolete(self) -> None:
        from streamlit.testing.v1 import AppTest

        if (ROOT / "data" / "ministere.duckdb").exists():
            pytest.skip("Base présente : le message d'absence ne s'affiche pas.")
        at = AppTest.from_file(str(ROOT / "pages" / "1_📍_Géographie.py"), default_timeout=30)
        at.run()
        assert not at.exception
        textes = _textes(at)
        assert "base de données est introuvable" in textes
        codes = "\n".join(c.value for c in at.code)
        assert "etl_regions.py" not in codes + textes
