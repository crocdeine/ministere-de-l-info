"""Configuration pytest partagée : marqueur spatial, fixtures de la base échantillon."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import duckdb
import pytest
from fixtures.sample_db import construire_base, exiger_echantillon, spatial_disponible


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Ignore proprement les tests ``spatial`` si l'extension n'est pas installée."""
    if spatial_disponible():
        return
    skip = pytest.mark.skip(
        reason="Extension DuckDB spatial indisponible (non installée ; les tests ne la "
        "téléchargent pas). L'installer une fois : uv run python -c "
        "\"import duckdb; duckdb.connect().install_extension('spatial')\""
    )
    for item in items:
        if item.get_closest_marker("spatial") is not None:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def echantillon_con() -> Iterator[duckdb.DuckDBPyConnection]:
    """Base en mémoire reconstruite depuis l'échantillon (skip si absent)."""
    exiger_echantillon()
    con = construire_base()
    yield con
    con.close()


@pytest.fixture(scope="session")
def echantillon_db_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Fichier DuckDB reconstruit depuis l'échantillon, pour les modules qui ouvrent
    la base par son chemin (``viz/*_queries.py``). Skip si l'échantillon est absent."""
    exiger_echantillon()
    chemin = tmp_path_factory.mktemp("echantillon") / "echantillon.duckdb"
    construire_base(chemin).close()
    return chemin
