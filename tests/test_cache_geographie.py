"""Lectures mises en cache de la page Géographie, sur l'échantillon de base (hermétique)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import folium
import pytest

from ministere_de_l_info.viz import _queries, maps


@pytest.fixture
def sur_echantillon(echantillon_db_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fait pointer les lectures cachées vers l'échantillon et vide les caches."""
    reglages = SimpleNamespace(db_path=echantillon_db_path)
    monkeypatch.setattr(_queries, "get_settings", lambda: reglages)
    monkeypatch.setattr(maps, "get_settings", lambda: reglages)
    for f in (
        _queries.get_annees_population,
        _queries.get_referentiel_geo,
        _queries.get_meta_etl,
        _queries.get_tableau_territoires_cache,
        maps.get_carte_cache,
    ):
        f.clear()


def test_lectures_cachees(sur_echantillon: None) -> None:
    annees = _queries.get_annees_population()
    assert annees and annees == sorted(annees, reverse=True)
    deps = _queries.get_referentiel_geo("departement")
    assert ("80", "Somme") in deps
    assert _queries.get_meta_etl("table_inexistante") is None
    tableau = _queries.get_tableau_territoires_cache("departement", annees[0])
    assert tableau.height > 0


@pytest.mark.spatial
def test_carte_en_cache(sur_echantillon: None) -> None:
    annee = _queries.get_annees_population()[0]
    carte = maps.get_carte_cache("departement", annee, None, None, None, "Départements", "auto")
    assert isinstance(carte, folium.Map)
