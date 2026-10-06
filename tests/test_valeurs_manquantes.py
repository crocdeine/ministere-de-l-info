"""Valeurs manquantes : NULL / « n.d. » et jamais 0 (audit I6), carte déserts à 3 états (I9)."""

from __future__ import annotations

import json

import duckdb
import polars as pl
import pytest

from ministere_de_l_info.pages import economie
from ministere_de_l_info.viz import elections_queries
from ministere_de_l_info.viz._display import fmt_nd
from ministere_de_l_info.viz.maps_elections import make_choropleth_elections_score_bloc

_GEOJSON = json.dumps(
    {"type": "Polygon", "coordinates": [[[2, 50], [3, 50], [3, 51], [2, 51], [2, 50]]]}
)


def test_fmt_nd() -> None:
    assert fmt_nd(None) == "n.d."
    assert fmt_nd(float("nan")) == "n.d."
    assert fmt_nd(None, ".1f", " %") == "n.d."
    assert fmt_nd(0) == "0"  # un vrai zéro reste affiché
    assert fmt_nd(1234) == "1 234"
    assert fmt_nd(56.78, ".1f", " %") == "56,8 %"


def test_metrics_commune_sans_participation_donne_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Commune sans ligne de participation : inscrits/votants/exprimés/taux = None, pas 0."""
    con = duckdb.connect(":memory:")
    con.execute(
        "CREATE TABLE elections (id_election VARCHAR, type_scrutin VARCHAR, annee INT, tour INT)"
    )
    con.execute(
        "CREATE TABLE resultats_participation (id_election VARCHAR, code_commune VARCHAR, "
        "inscrits INT, votants INT, exprimes INT)"
    )
    con.execute(
        "CREATE TABLE v_resultats_candidats_avec_bloc (type_scrutin VARCHAR, annee INT, "
        "tour INT, code_commune VARCHAR, bloc VARCHAR, voix INT)"
    )
    monkeypatch.setattr(elections_queries, "_open_ro", lambda: con)
    m = elections_queries.get_metrics_commune_pres.__wrapped__(  # pyright: ignore[reportAttributeAccessIssue] # stub Streamlit : CachedFunc sans __wrapped__
        2022, 1, "99999"
    )
    assert m["inscrits"] is None
    assert m["votants"] is None
    assert m["exprimes"] is None
    assert m["taux_participation_pct"] is None


def _geo(codes: list[str]) -> pl.DataFrame:
    return pl.DataFrame(
        {"code_commune": codes, "nom": [f"C{c}" for c in codes], "geojson": [_GEOJSON] * len(codes)}
    )


def test_carte_score_bloc_exprimes_absents_nd() -> None:
    scores = pl.DataFrame({"code_commune": ["A", "B"], "bloc": ["GAU", "GAU"], "voix": [10, 20]})
    part = pl.DataFrame(
        {"code_commune": ["A", "B"], "exprimes": [None, 0]}, schema_overrides={"exprimes": pl.Int64}
    )
    m = make_choropleth_elections_score_bloc(
        scores, part, _geo(["A", "B", "C"]), "GAU", "#ff0000", "Gauche", None, "t"
    )
    html = m.get_root().render()
    assert '"pct_fmt": "n.d."' in html
    assert "0.0 %" not in html and '"_pct": 0.0' not in html
    assert "n.d. (exprimés non disponibles)" in html  # légende


def test_carte_score_bloc_bloc_absent_avec_exprimes_connus_reste_zero() -> None:
    """0 voix est juste quand les exprimés sont connus et le bloc absent de la commune."""
    scores = pl.DataFrame({"code_commune": ["A"], "bloc": ["GAU"], "voix": [10]})
    part = pl.DataFrame({"code_commune": ["A", "B"], "exprimes": [100, 100]})
    m = make_choropleth_elections_score_bloc(
        scores, part, _geo(["A", "B"]), "GAU", "#ff0000", "Gauche", None, "t"
    )
    html = m.get_root().render()
    assert '"_pct": 0.0' in html


def test_etat_desert() -> None:
    assert economie._etat_desert(None) == "sans_donnee"
    assert economie._etat_desert(float("nan")) == "sans_donnee"
    assert economie._etat_desert(1.9) == "desert"
    assert economie._etat_desert(2.5) == "hors_desert"
    assert economie._etat_desert(3.4) == "hors_desert"


def test_carte_deserts_trois_etats() -> None:
    df = pl.DataFrame(
        {
            "code_commune": ["A", "B", "C", "D"],
            "nom_commune": ["Desert", "Hors", "NoData", "Secret"],
            "valeur": [1.5, 3.0, None, 2.0],
            "secret": [False, False, False, True],
            "geojson": [_GEOJSON] * 4,
        }
    )
    html = economie._make_desert_map(df).get_root().render()
    for etat in ("desert", "hors_desert", "sans_donnee"):
        assert f'"etat": "{etat}"' in html
    assert html.count('"etat": "sans_donnee"') == 2  # NULL et secret statistique
    assert "APL &lt; 2,5" in html or "APL < 2,5" in html
    assert "Sans donnée" in html


def test_detail_bv_absences_en_none() -> None:
    """Détail par bureau : participation absente et bloc introuvable restent None (pas 0 ni DIV)."""
    from ministere_de_l_info.viz.elections_queries import _build_bv_df

    df = _build_bv_df([("0001", None, None, None, None)], [])
    ligne = df.row(0, named=True)
    assert ligne["inscrits"] is None
    assert ligne["taux_participation_pct"] is None
    assert ligne["bloc_gagnant"] is None
