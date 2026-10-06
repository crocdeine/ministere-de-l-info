"""Configuration centralisée de l'application (pydantic-settings).

Ordre de résolution de chaque paramètre (le premier trouvé l'emporte) :
1. variable d'environnement (préfixe ``MINISTERE_``, ex. ``MINISTERE_DB_PATH``) ;
2. fichier ``.env`` à la racine du projet ;
3. valeur par défaut calculée ici.

Usage :
    from ministere_de_l_info.config import get_settings
    db_path = get_settings().db_path
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_NAME_MARKER = 'name = "ministere-de-l-info"'


def _is_project_root(candidate: Path) -> bool:
    """Vrai si ``candidate`` contient le pyproject.toml de ce projet."""
    pyproject = candidate / "pyproject.toml"
    if not pyproject.is_file():
        return False
    try:
        return _PROJECT_NAME_MARKER in pyproject.read_text(encoding="utf-8")
    except OSError:
        return False


def find_project_root() -> Path:
    """Localise la racine du projet sans dépendre d'une installation éditable.

    Remonte depuis ce fichier (checkout, installation éditable, image Docker),
    puis depuis le répertoire courant (paquet installé dans site-packages mais
    lancé depuis le dépôt). À défaut, retourne le répertoire courant.
    """
    here = Path(__file__).resolve()
    cwd = Path.cwd().resolve()
    for start in (here.parent, cwd):
        for candidate in (start, *start.parents):
            if _is_project_root(candidate):
                return candidate
    return cwd


PROJECT_ROOT: Path = find_project_root()
DEFAULT_DB_PATH: Path = PROJECT_ROOT / "data" / "ministere.duckdb"


class Settings(BaseSettings):
    """Paramètres de l'application, lus depuis l'environnement."""

    model_config = SettingsConfigDict(
        env_prefix="MINISTERE_",
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    db_path: Path = Field(
        default=DEFAULT_DB_PATH,
        description="Chemin du fichier DuckDB principal (variable MINISTERE_DB_PATH).",
    )

    @field_validator("db_path")
    @classmethod
    def _normaliser_db_path(cls, value: Path) -> Path:
        """Développe ``~`` ; un chemin relatif est pris depuis la racine du projet."""
        value = value.expanduser()
        if not value.is_absolute():
            value = PROJECT_ROOT / value
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retourne l'instance unique des paramètres (mise en cache).

    Après modification de l'environnement (tests), appeler
    ``get_settings.cache_clear()``.
    """
    return Settings()
