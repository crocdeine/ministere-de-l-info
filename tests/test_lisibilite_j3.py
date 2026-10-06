"""Jalon J3 « lisibilité honnête » : échelles fixes, défauts en %, palette accessible."""

from __future__ import annotations

import colorsys
import inspect
import json
import re

import polars as pl
import pytest

from ministere_de_l_info._blocs_politiques import COULEURS_BLOCS, couleurs_traits
from ministere_de_l_info.pages import (
    economie,
    elections_legislatives,
    elections_municipales,
    elections_presidentielles,
)
from ministere_de_l_info.viz import _display
from ministere_de_l_info.viz._display import BORNES_FIXES, bornes_fixes
from ministere_de_l_info.viz.economie_queries import get_indicateurs
from ministere_de_l_info.viz.maps_elections import (
    ECHELLE_SCORE_MAX,
    make_choropleth_elections_score_bloc,
)

_GEOJSON = json.dumps(
    {"type": "Polygon", "coordinates": [[[2, 50], [3, 50], [3, 51], [2, 51], [2, 50]]]}
)


def test_bornes_fixes_stables_et_ordonnees() -> None:
    for cle, bornes in BORNES_FIXES.items():
        assert len(bornes) == 6, cle
        assert bornes == sorted(bornes), cle
        assert bornes_fixes(cle) == bornes  # indépendant de toute donnée ou année
    with pytest.raises(ValueError):
        bornes_fixes("indicateur_inconnu")


def test_bornes_fixes_couvrent_indicateurs_economie_et_niveaux() -> None:
    for indic in get_indicateurs():
        assert indic in BORNES_FIXES
    for niveau in ("region", "departement", "epci", "arrondissement_municipal", "commune"):
        assert f"population_municipale:{niveau}" in BORNES_FIXES


def _df_eco(valeurs: list[float]) -> pl.DataFrame:
    n = len(valeurs)
    return pl.DataFrame(
        {
            "code_commune": [f"C{i}" for i in range(n)],
            "nom_commune": [f"N{i}" for i in range(n)],
            "valeur": valeurs,
            "secret": [False] * n,
            "geojson": [_GEOJSON] * n,
        }
    )


def test_carte_economie_memes_classes_deux_annees() -> None:
    """Deux années aux valeurs très différentes : mêmes classes, même couleur à valeur égale."""
    h1 = economie._make_choropleth(_df_eco([5.0, 12.0]), "Pauvreté", "taux_pauvrete")
    h2 = economie._make_choropleth(_df_eco([12.0, 40.0]), "Pauvreté", "taux_pauvrete")
    h1, h2 = h1.get_root().render(), h2.get_root().render()
    for h in (h1, h2):
        assert "Classes fixes, identiques pour toutes les années" in h
        assert "&lt; 10" in h and "&ge; 25" in h  # seuils 10/15/20/25 (Mathias 2026-10-06)
    # une valeur de 12 % reçoit la même couleur d'une année à l'autre
    couleur = re.search(r'"fillColor": "(#[0-9a-f]{6})"[^}]*', h1.split('"N1"')[0][-600:])
    assert couleur is None or couleur.group(1) in h2


def _geo(codes: list[str]) -> pl.DataFrame:
    return pl.DataFrame({"code_commune": codes, "nom": codes, "geojson": [_GEOJSON] * len(codes)})


def _couleurs_carte(scores: dict[str, int]) -> set[str]:
    """Ensemble des couleurs de remplissage présentes dans la carte (hors n.d.)."""
    codes = list(scores)
    df = pl.DataFrame(
        {"code_commune": codes, "bloc": ["GAU"] * len(codes), "voix": list(scores.values())}
    )
    part = pl.DataFrame({"code_commune": codes, "exprimes": [100] * len(codes)})
    m = make_choropleth_elections_score_bloc(
        df, part, _geo(codes), "GAU", "#ff0000", "Gauche", None, "t"
    )
    return set(re.findall(r'"fillColor": "(#[0-9a-fA-F]+)"', m.get_root().render()))


def test_score_bloc_echelle_fixe_independante_du_maximum() -> None:
    assert ECHELLE_SCORE_MAX == 100.0  # 0-100 % à tous les tours (Mathias 2026-10-06)
    seule = _couleurs_carte({"A": 10})
    avec_max = _couleurs_carte({"A": 10, "B": 55})
    assert seule <= avec_max  # 10 % a la même teinte quel que soit le max de la carte
    assert not any(c.lower().startswith("#ff0000") for c in seule)  # pas saturé à 10 %
    m = make_choropleth_elections_score_bloc(
        pl.DataFrame({"code_commune": ["A"], "bloc": ["GAU"], "voix": [10]}),
        pl.DataFrame({"code_commune": ["A"], "exprimes": [100]}),
        _geo(["A"]),
        "GAU",
        "#ff0000",
        "Gauche",
        None,
        "t",
    )
    assert "Échelle fixe 0-100 %" in m.get_root().render()


@pytest.mark.parametrize(
    "module",
    [elections_presidentielles, elections_legislatives, elections_municipales],
)
def test_evolution_pct_par_defaut(module) -> None:
    src = inspect.getsource(module)
    assert '["Part des exprimés (%)", "Voix totales"]' in src or (
        'modes = ["Part des exprimés (%)", "Voix totales"]' in src
    )
    assert '["Voix totales", "Part des exprimés (%)"]' not in src


def test_palette_evolution_sans_rouge_vert() -> None:
    for hexa in _display._COULEURS_EVOLUTION5:
        r, g, b = (int(hexa[i : i + 2], 16) / 255 for i in (1, 3, 5))
        h, s, _ = colorsys.rgb_to_hsv(r, g, b)
        deg = h * 360
        assert not (s > 0.4 and (deg < 15 or deg > 345)), hexa  # pas de rouge
        assert not (s > 0.25 and 75 < deg < 165), hexa  # pas de vert


def test_trait_centre_assombri_sans_toucher_aux_remplissages() -> None:
    assert COULEURS_BLOCS["CENT"] == "#F5B800"
    t = couleurs_traits(COULEURS_BLOCS)
    assert t["CENT"] != "#F5B800"
    assert {k: v for k, v in t.items() if k != "CENT"} == {
        k: v for k, v in COULEURS_BLOCS.items() if k != "CENT"
    }


def test_classe_zero_distincte() -> None:
    """Indicateurs à zéros fréquents : « 0 » a sa propre couleur et sa ligne de légende."""
    from ministere_de_l_info.viz._display import COULEUR_ZERO

    html = (
        economie._make_choropleth(
            _df_eco([0.0, 3.0]), "Logements sociaux", "part_logements_sociaux"
        )
        .get_root()
        .render()
    )
    assert COULEUR_ZERO in html and "0 (aucun)" in html and "&gt; 0 et &lt; 5" in html
    autre = economie._make_choropleth(_df_eco([0.0, 3.0]), "Pauvreté", "taux_pauvrete")
    assert "0 (aucun)" not in autre.get_root().render()
