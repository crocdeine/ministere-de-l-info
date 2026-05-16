"""Tests smoke — pipeline ETL régions."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ministere_de_l_info.data_sources.geo import POPULATION_2024, fetch_regions_geojson

_CODES_METRO_ATTENDUS = frozenset(POPULATION_2024.keys())


def test_fetch_geojson_13_features() -> None:
    """L'API renvoie bien 13 régions métropolitaines après filtrage."""
    data = fetch_regions_geojson()
    assert len(data["features"]) == 13, (
        f"Attendu 13 features, obtenu {len(data['features'])}"
    )


def test_codes_insee_sont_des_strings_valides() -> None:
    """Chaque code INSEE est une str de 2 chars correspondant aux 13 régions métro."""
    data = fetch_regions_geojson()
    codes = {f["properties"]["code"] for f in data["features"]}

    assert all(isinstance(c, str) for c in codes), "Les codes doivent être des str"
    assert all(len(c) == 2 for c in codes), "Les codes régions font 2 caractères"
    assert codes == _CODES_METRO_ATTENDUS, (
        f"Codes inattendus : {codes.symmetric_difference(_CODES_METRO_ATTENDUS)}"
    )
