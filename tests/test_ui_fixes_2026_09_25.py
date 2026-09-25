"""Tests de non-régression — 3 bugs UI constatés par Mathias sur le Mac (25/09/2026).

1. Économie : `folium.Choropleth` plante (`np.isnan`) quand un indicateur est
   entièrement `None` sur un millésime (ex. chômage RP 2015/2016 sous secret
   statistique intégral) — la colonne est alors inférée `pl.Null` par Polars.
2. Élections : le widget « Zone » (et les widgets analogues des autres onglets)
   peut se désynchroniser visuellement de la donnée affichée après un
   changement d'onglet paresseux (`st.tabs(on_change="rerun")`).
3. Législatif : les scores d'activité Datan sont stockés en ratio [0, 1] et
   doivent être affichés en pourcentage (×100, 1 décimale, virgule française).
"""

from __future__ import annotations

import re
from pathlib import Path

import duckdb
import polars as pl
import pytest
import streamlit as st

from ministere_de_l_info._theme import index_persiste
from ministere_de_l_info.pages.economie import _make_choropleth
from ministere_de_l_info.viz import economie_queries as eq
from ministere_de_l_info.viz.elections_queries import format_pct_fr

ROOT = Path(__file__).resolve().parent.parent

# ── Bug 1 : Économie — indicateur entièrement None ──────────────────────────────


class TestChoroplethIndicateurEntierementNull:
    """Reproduction directe du crash `ufunc 'isnan' not supported` (sans DB)."""

    def _df_tout_secret(self) -> pl.DataFrame:
        # Reproduit exactement la forme renvoyée par `get_scores_commune` quand
        # tout un millésime est sous secret statistique (ex. RP 2015/2016).
        return pl.DataFrame(
            {
                "code_commune": ["80001", "80002"],
                "nom_commune": ["Commune A", "Commune B"],
                "valeur": pl.Series("valeur", [None, None], dtype=pl.Float64),
                "secret": [True, True],
                "geojson": [
                    '{"type":"Polygon","coordinates":[[[1,1],[2,2],[3,1],[1,1]]]}',
                    '{"type":"Polygon","coordinates":[[[4,4],[5,5],[6,4],[4,4]]]}',
                ],
            }
        )

    def test_make_choropleth_ne_leve_pas_isnan(self) -> None:
        """Avant fix : `folium.Choropleth` levait `TypeError: ufunc 'isnan'...`."""
        df = self._df_tout_secret()
        carte = _make_choropleth(df, "Taux de chômage (RP, %)")
        assert carte is not None

    def test_make_choropleth_valeur_non_typee_pl_null(self) -> None:
        """Cas encore plus dégradé : colonne `valeur` construite sans dtype
        explicite (ex. ancien code de `get_scores_commune`) → `pl.Null`."""
        df = pl.DataFrame(
            {
                "code_commune": ["80001"],
                "nom_commune": ["Commune A"],
                "valeur": [None],  # inférence Polars : pl.Null sans schema_overrides
                "secret": [True],
                "geojson": ['{"type":"Polygon","coordinates":[[[1,1],[2,2],[3,1],[1,1]]]}'],
            }
        )
        assert df.schema["valeur"] == pl.Null
        # Ne doit pas lever d'exception (contournement dans `_make_choropleth`).
        carte = _make_choropleth(df, "Indicateur")
        assert carte is not None


class TestSchemaOverridesEconomieQueries:
    """`get_scores_commune` doit toujours renvoyer `valeur` en Float64, même si
    la requête ne retourne que des lignes `NULL` (défense en profondeur, en plus
    du fix côté `_make_choropleth`)."""

    def test_dtype_reste_float64_meme_si_tout_est_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        rows = [("80001", "Commune A", None, True, "{}"), ("80002", "Commune B", None, True, "{}")]

        class FakeCursor:
            def fetchall(self) -> list[tuple]:
                return rows

        class FakeCon:
            def execute(self, *_a: object, **_k: object) -> FakeCursor:
                return FakeCursor()

            def close(self) -> None:
                pass

        monkeypatch.setattr(eq, "_open_ro", lambda: FakeCon())
        monkeypatch.setattr(eq, "_INDICATEURS_SOCIAL", frozenset())
        monkeypatch.setattr(eq, "_INDICATEURS_RP", frozenset({"tx_chomage_dec"}))
        eq.get_scores_commune.clear()
        df = eq.get_scores_commune(2015, "tx_chomage_dec")
        assert df.schema["valeur"] == pl.Float64
        assert df["valeur"].is_null().all()
        eq.get_scores_commune.clear()


# ── Bug 2 : Élections — widget/donnée désynchronisés après changement d'onglet ──


class TestIndexPersiste:
    def test_valeur_presente_retourne_son_index(self) -> None:
        st.session_state["pres_zone"] = "hdf"
        assert index_persiste("pres_zone", ["circo21", "hdf"]) == 1

    def test_valeur_absente_retourne_defaut(self) -> None:
        if "cle_absente" in st.session_state:
            del st.session_state["cle_absente"]
        assert index_persiste("cle_absente", ["a", "b"], defaut=0) == 0
        assert index_persiste("cle_absente", ["a", "b"], defaut=1) == 1

    def test_valeur_hors_options_retourne_defaut(self) -> None:
        st.session_state["pres_drilldown_commune"] = "Ancienne commune (00000)"
        assert (
            index_persiste("pres_drilldown_commune", ["(aucune sélection)", "Lille (59350)"], 0)
            == 0
        )


class TestConserverSelectionsEtIndexCoherents:
    """Reproduction fidèle du bloc de sélecteurs Présidentielles (annee/tour/zone/
    mode_carte) sous onglets paresseux (`st.tabs(on_change="rerun")`) : le widget
    « Zone » doit rester cohérent avec la donnée affichée après un aller-retour
    entre onglets."""

    _SCRIPT = ROOT / "tests" / "fixtures" / "_repro_tabs_zone.py"

    def test_zone_widget_et_donnee_coherents_apres_switch(self) -> None:
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(self._SCRIPT), default_timeout=30)
        at.run()
        assert not at.exception

        r = next(r for r in at.radio if r.key == "pres_zone")
        r.set_value("hdf").run()
        assert not at.exception
        assert at.session_state["pres_zone"] == "hdf"
        assert any(m.value == "ZONE_UTILISEE=hdf" for m in at.markdown)

        # Changement d'onglet (Législatives), puis retour sur Présidentielles.
        at.session_state["onglet"] = "Législatives"
        at.run()
        assert not at.exception

        at.session_state["onglet"] = "Présidentielles"
        at.run()
        assert not at.exception

        radio_zone = next(r for r in at.radio if r.key == "pres_zone")
        assert radio_zone.value == "hdf", (
            "Le widget Zone doit rester sur 'hdf' après un aller-retour d'onglet "
            "(sinon désynchronisation widget/donnée constatée par Mathias)."
        )
        assert any(m.value == "ZONE_UTILISEE=hdf" for m in at.markdown), (
            "La donnée affichée doit rester cohérente avec le widget Zone."
        )


# ── Bug 3 : Législatif — scores Datan affichés en pourcentage ──────────────────


class TestScoresDatanEnPourcentage:
    def test_format_pct_fr_echelle_ratio(self) -> None:
        """Un score Datan de 0,523 (ratio) doit s'afficher « 52,3 % »."""
        valeur_ratio = 0.523
        assert format_pct_fr(valeur_ratio * 100) == "52,3 %"

    def test_format_pct_fr_none(self) -> None:
        assert format_pct_fr(None) == "n.d."

    def test_echantillon_reel_scores_en_ratio(self, echantillon_db_path: Path) -> None:
        """Confirme l'échelle réellement stockée en base (échantillon Mac) :
        les scores Datan sont bien des ratios [0, 1], pas des pourcentages."""
        con = duckdb.connect(str(echantillon_db_path), read_only=True)
        try:
            row = con.execute(
                "SELECT min(score_participation), max(score_participation) FROM leg_activite"
            ).fetchone()
        finally:
            con.close()
        assert row is not None
        mini, maxi = row
        if mini is None:
            pytest.skip("Aucun score_participation dans l'échantillon.")
        assert 0.0 <= mini <= 1.0
        assert 0.0 <= maxi <= 1.0

    def test_page_fiche_depute_affiche_pourcentage(
        self, echantillon_db_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AppTest : la fiche d'un député affiche des métriques en `XX,X %`
        (jamais un ratio brut du type `0.88`)."""
        from streamlit.testing.v1 import AppTest

        from ministere_de_l_info.viz import legislatif_queries

        monkeypatch.setattr(legislatif_queries, "DB_PATH", echantillon_db_path)

        def _page() -> None:
            from ministere_de_l_info.pages.legislatif import render

            render()

        at = AppTest.from_function(_page, default_timeout=60).run()
        assert not at.exception, at.exception

        fiche = at.selectbox(key="leg_fiche_depute")
        if not fiche.options:
            pytest.skip("Aucun député dans l'échantillon.")
        fiche.select_index(0).run()
        assert not at.exception, at.exception

        libelles_datan = {
            "Participation (%)",
            "Loyauté au groupe (%)",
            "Proximité majorité (%)",
            "Participation spécialisée (%)",
        }
        metrics = [
            m for m in at.metric if m.label in libelles_datan and m.value not in ("n.d.", "—")
        ]
        if not metrics:
            pytest.skip("Aucun score d'activité pour ce député dans l'échantillon.")
        for m in metrics:
            assert re.fullmatch(r"-?\d+,\d %", m.value), (
                f"Métrique Datan pas au format pourcentage français : {m.label}={m.value!r}"
            )
            valeur_num = float(m.value.replace(",", ".").replace(" %", ""))
            assert -100.0 <= valeur_num <= 100.0, (
                f"Valeur hors plage pourcentage plausible : {m.label}={m.value!r} "
                "(ratio [0,1] non converti ?)"
            )
