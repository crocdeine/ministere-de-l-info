"""Tests de conformité : mentions de sources, légendes des blocs, minimisation RGPD."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import duckdb
import pytest

from ministere_de_l_info._blocs_politiques import legende_classement_blocs
from ministere_de_l_info.etl.schema_legislatif import create_legislatif_schema
from ministere_de_l_info.sources import ODBL, SOURCES, mention, tableau_sources
from ministere_de_l_info.viz._display import nouvelle_carte


@pytest.mark.parametrize(("type_scrutin", "annee"), [("muni", 2020), ("muni", 2026)])
def test_legende_grille_officielle(type_scrutin: str, annee: int) -> None:
    texte = legende_classement_blocs(type_scrutin, annee)
    assert "grille officielle du ministère" in texte
    assert "reconstruction" not in texte


@pytest.mark.parametrize(
    ("type_scrutin", "annee", "reference"),
    [
        ("pres", 2002, "INTA1931378J"),
        ("pres", 2022, "INTA1931378J"),
        ("legi", 2017, "INTA1931378J"),
        ("legi", 2024, "IOMA2322276J"),
        ("muni", 2014, "INTA1931378J"),
    ],
)
def test_legende_reconstruction(type_scrutin: str, annee: int, reference: str) -> None:
    texte = legende_classement_blocs(type_scrutin, annee)
    assert "reconstruction" in texte
    assert reference in texte
    assert "grille officielle du ministère" not in texte


def test_toutes_les_sources_ont_licence_et_lien() -> None:
    for cle, source in SOURCES.items():
        assert source.licence, cle
        assert source.url.startswith("https://"), cle
        assert source.licence in mention(cle)


def test_urssaf_sous_odbl() -> None:
    assert SOURCES["urssaf"].licence == ODBL


def test_tableau_sources_date_la_plus_recente() -> None:
    chargements = {
        "economie_filosofi": datetime(2026, 6, 12),
        "economie_rp": datetime(2026, 6, 13),
    }
    lignes = {ligne["Producteur"]: ligne for ligne in tableau_sources(chargements)}
    assert len(lignes) == len(SOURCES)
    assert lignes[SOURCES["insee_filosofi_rp"].producteur]["Chargées le"] == "13/06/2026"
    assert lignes[SOURCES["elections"].producteur]["Chargées le"] == "non tracé"


def test_fond_de_carte_sans_carto() -> None:
    html = nouvelle_carte([50.0, 3.0], 8).get_root().render()
    assert "data.geopf.fr" in html
    assert "cartocdn" not in html


def test_date_naissance_retiree_de_leg_elus() -> None:
    con = duckdb.connect()
    con.execute("CREATE TABLE leg_elus (id VARCHAR, chambre VARCHAR, date_naissance DATE)")
    create_legislatif_schema(con)  # migration idempotente sur une base existante
    colonnes = [r[0] for r in con.execute("DESCRIBE leg_elus").fetchall()]
    assert "date_naissance" not in colonnes


def test_aucune_carte_hors_fond_ign() -> None:
    """Toute carte passe par nouvelle_carte() (fond Plan IGN, ADR-0013)."""
    racine = Path(__file__).resolve().parents[1]
    fichiers = [*(racine / "src").rglob("*.py"), *(racine / "pages").rglob("*.py")]
    fautifs = [
        str(f.relative_to(racine))
        for f in fichiers
        if "folium.Map(" in f.read_text(encoding="utf-8") and f.name != "_display.py"
    ]
    assert fautifs == []


def test_commune_municipales_memorisee_entre_scrutins(monkeypatch: pytest.MonkeyPatch) -> None:
    """La commune choisie est présélectionnée dans un autre scrutin où elle existe."""
    from ministere_de_l_info.pages import elections_municipales as em

    monkeypatch.setattr(em.st, "session_state", {"muni_commune_code": "80021"})
    assert em._index_commune_memorisee([("80001", "Abbeville"), ("80021", "Amiens")]) == 2
    assert em._index_commune_memorisee([("80001", "Abbeville")]) == 0
