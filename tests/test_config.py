"""Tests de la configuration centralisée (ministere_de_l_info.config)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from ministere_de_l_info import config
from ministere_de_l_info.config import DEFAULT_DB_PATH, PROJECT_ROOT, Settings, get_settings


@pytest.fixture(autouse=True)
def _reset_cache() -> Iterator[None]:
    """Vide le cache de get_settings() avant et après chaque test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_project_root_contient_pyproject() -> None:
    assert (PROJECT_ROOT / "pyproject.toml").is_file()
    assert (PROJECT_ROOT / "src" / "ministere_de_l_info").is_dir()


def test_defaut_sous_data(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MINISTERE_DB_PATH", raising=False)
    s = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
    assert s.db_path == DEFAULT_DB_PATH
    assert s.db_path == PROJECT_ROOT / "data" / "ministere.duckdb"


def test_variable_absolue(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cible = tmp_path / "autre.duckdb"
    monkeypatch.setenv("MINISTERE_DB_PATH", str(cible))
    assert get_settings().db_path == cible


def test_variable_relative_resolue_depuis_racine(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MINISTERE_DB_PATH", "data/test.duckdb")
    assert get_settings().db_path == PROJECT_ROOT / "data" / "test.duckdb"


def test_tilde_developpe(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("MINISTERE_DB_PATH", "~/base.duckdb")
    assert get_settings().db_path == tmp_path / "base.duckdb"


def test_variable_vide_ignoree(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MINISTERE_DB_PATH", "")
    s = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
    assert s.db_path == DEFAULT_DB_PATH


def test_get_settings_en_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MINISTERE_DB_PATH", raising=False)
    assert get_settings() is get_settings()


def test_find_project_root_repli_cwd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Hors dépôt (fichier et cwd), la racine retombe sur le répertoire courant."""
    faux_module = tmp_path / "site-packages" / "ministere_de_l_info" / "config.py"
    faux_module.parent.mkdir(parents=True)
    faux_module.touch()
    monkeypatch.setattr(config, "__file__", str(faux_module))
    monkeypatch.chdir(tmp_path)
    assert config.find_project_root() == tmp_path.resolve()


def test_find_project_root_depuis_cwd(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Paquet non éditable (site-packages) lancé depuis le dépôt : racine trouvée via cwd."""
    faux_module = tmp_path / "venv" / "ministere_de_l_info" / "config.py"
    faux_module.parent.mkdir(parents=True)
    faux_module.touch()
    monkeypatch.setattr(config, "__file__", str(faux_module))
    monkeypatch.chdir(PROJECT_ROOT / "tests")
    assert config.find_project_root() == PROJECT_ROOT
