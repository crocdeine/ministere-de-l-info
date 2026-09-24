"""Tests réseau de fetch_admin_express (IGN WFS) : pagination et reprise disque.

Ex-``smoke_test_fetch_admin.py`` (jamais collecté par pytest à cause de son nom).
Renommé pour être collecté sous le marqueur ``network`` (exclu par défaut, lancé par
``pytest -m network``). Les téléchargements vont dans un répertoire temporaire : le
cache ``data/raw/`` de l'ETL n'est plus écrasé par ``force=True``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from ministere_de_l_info.data_sources.geo import _batch_file_valid, fetch_admin_express

pytestmark = pytest.mark.network

_LOGGER_GEO = "ministere_de_l_info.data_sources.geo"


@pytest.fixture(scope="module")
def telechargement(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, list[Path]]:
    """Premier téléchargement (force=True) dans un cache isolé : (répertoire, batches)."""
    d = tmp_path_factory.mktemp("admin_express_raw")
    return d, list(fetch_admin_express("departement", dom=True, force=True, raw_dir=d))


def test_departement_download(telechargement: tuple[Path, list[Path]]) -> None:
    """Téléchargement : pagination, batches valides, nombre de départements plausible."""
    _, paths = telechargement
    assert len(paths) >= 1, f"Aucun batch produit, obtenu : {paths}"

    total_features = 0
    for p in paths:
        assert p.exists(), f"Fichier batch manquant : {p}"
        assert _batch_file_valid(p), f"Batch invalide : {p}"
        total_features += len(json.loads(p.read_text(encoding="utf-8"))["features"])

    assert 96 <= total_features <= 110, (
        f"Nombre de départements inattendu : {total_features} (attendu 96-110)"
    )


def test_departement_reprise(
    telechargement: tuple[Path, list[Path]], caplog: pytest.LogCaptureFixture
) -> None:
    """Second appel force=False : les batches sont relus depuis le disque."""
    raw_dir, _ = telechargement
    with caplog.at_level(logging.INFO, logger=_LOGGER_GEO):
        paths = list(fetch_admin_express("departement", dom=True, force=False, raw_dir=raw_dir))

    assert len(paths) >= 1, "Aucun batch retourné en mode reprise"
    assert any("reprise disque" in m for m in caplog.messages), (
        "Aucun log 'reprise disque' détecté : le cache disque n'a pas été utilisé"
    )
