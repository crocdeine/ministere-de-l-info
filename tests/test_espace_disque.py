"""Tests de la garde d'espace disque."""

from collections import namedtuple
from pathlib import Path

import pytest

from ministere_de_l_info import espace_disque

Usage = namedtuple("Usage", "total used free")


def _libre(monkeypatch: pytest.MonkeyPatch, octets: int) -> None:
    monkeypatch.setattr(espace_disque.shutil, "disk_usage", lambda _d: Usage(0, 0, octets))


def test_sous_le_seuil_leve(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv(espace_disque.ENV_SEUIL_GO, raising=False)
    _libre(monkeypatch, 5_000_000_000)
    with pytest.raises(OSError, match="5.00 Go libres"):
        espace_disque.verifier_espace(tmp_path)


def test_au_dessus_du_seuil_ok(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv(espace_disque.ENV_SEUIL_GO, raising=False)
    _libre(monkeypatch, 50_000_000_000)
    espace_disque.verifier_espace(tmp_path)


def test_seuil_surcharge_et_minimum(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _libre(monkeypatch, 5_000_000_000)
    monkeypatch.setenv(espace_disque.ENV_SEUIL_GO, "1")
    espace_disque.verifier_espace(tmp_path)
    with pytest.raises(OSError):
        espace_disque.verifier_espace(tmp_path, minimum_octets=8_000_000_000)
