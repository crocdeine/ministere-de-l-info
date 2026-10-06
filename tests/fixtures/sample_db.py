"""Reconstruction d'une base DuckDB de test depuis l'échantillon Parquet.

L'échantillon (``tests/fixtures/sample/*.parquet`` + ``manifest.json``) est un extrait
de la base réelle, généré sur le Mac par ``scripts/export_sample_db.py``. Ce module
recrée tables et vues avec les fonctions de schéma du projet, puis insère les données.

- Aucune extension n'est requise : les géométries sont stockées en WKB et relues avec
  ``ST_GeomFromWKB`` (disponible nativement depuis DuckDB 1.5). Les requêtes qui
  utilisent des fonctions de l'extension spatial doivent être marquées
  ``pytest.mark.spatial`` (ignorées si l'extension n'est pas installée).
- Tant que l'échantillon n'a pas été généré, ``exiger_echantillon()`` fait un
  ``pytest.skip`` explicite.
- Écart de schéma (colonne ou table présente dans l'échantillon mais pas créée par le
  code) : la colonne ou la table est ajoutée et un ``EcartSchemaEchantillon`` est émis.
- Échantillon antérieur à l'ADR-0011 (sans ``leg_mandats`` ni ``leg_groupes_blocs``) :
  ces tables sont dérivées de ``leg_elus`` et du référentiel du code par la migration 0008,
  comme sur une base réelle migrée.
"""

from __future__ import annotations

import importlib.util
import json
import warnings
from collections.abc import Callable
from functools import cache
from pathlib import Path
from types import ModuleType
from typing import Any

import duckdb

from ministere_de_l_info.etl.schema import create_schema
from ministere_de_l_info.etl.schema_economie import create_economie_schema, create_economie_views
from ministere_de_l_info.etl.schema_elections import create_elections_schema, create_elections_views
from ministere_de_l_info.etl.schema_legislatif import (
    create_legislatif_schema,
    create_legislatif_views,
)
from ministere_de_l_info.etl.views import create_views

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DIR = Path(__file__).resolve().parent / "sample"
MANIFEST_PATH = SAMPLE_DIR / "manifest.json"
_MIGRATIONS = ROOT / "scripts" / "migrations"

MESSAGE_ABSENT = (
    "Échantillon Parquet absent (tests/fixtures/sample/manifest.json). Le générer sur le "
    "Mac depuis la base complète : `uv run python scripts/export_sample_db.py` "
    "(voir tests/fixtures/sample/README.md)."
)


class EcartSchemaEchantillon(UserWarning):
    """L'échantillon contient une colonne ou une table que le code ne crée pas."""


def echantillon_disponible(sample_dir: Path = SAMPLE_DIR) -> bool:
    """Vrai si le manifeste et tous les Parquet qu'il déclare sont présents."""
    manifest_path = sample_dir / "manifest.json"
    if not manifest_path.is_file():
        return False
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return all((sample_dir / t["fichier"]).is_file() for t in manifest["tables"].values())


def exiger_echantillon(sample_dir: Path = SAMPLE_DIR) -> None:
    """``pytest.skip`` explicite si l'échantillon n'est pas disponible."""
    if not echantillon_disponible(sample_dir):
        import pytest

        pytest.skip(MESSAGE_ABSENT)


def charger_manifest(sample_dir: Path = SAMPLE_DIR) -> dict[str, Any]:
    """Lit le manifeste de l'échantillon."""
    return json.loads((sample_dir / "manifest.json").read_text(encoding="utf-8"))


@cache
def spatial_disponible() -> bool:
    """Vrai si l'extension spatial peut être chargée sans téléchargement."""
    con = duckdb.connect()
    try:
        con.execute("LOAD spatial")
    except duckdb.Error:
        return False
    finally:
        con.close()
    return True


def _charger_migration(nom_fichier: str) -> ModuleType:
    """Importe une migration (nom de fichier non importable : commence par un chiffre)."""
    chemin = _MIGRATIONS / nom_fichier
    spec = importlib.util.spec_from_file_location(f"_sample_{chemin.stem}", chemin)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def creer_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Crée toutes les tables du projet (fonctions de schéma + migration 0006)."""
    create_schema(con)
    create_elections_schema(con)
    _charger_migration("0006_add_municipales_schema.py")._migrate_resultats_candidats(
        con, dry_run=False
    )
    create_economie_schema(con)
    create_legislatif_schema(con)


def creer_vues(con: duckdb.DuckDBPyConnection) -> None:
    """Crée toutes les vues du projet, dans l'ordre des dépendances."""
    m0007 = _charger_migration("0007_add_municipales_views.py")
    etapes: list[Callable[[duckdb.DuckDBPyConnection], None]] = [
        create_views,
        create_elections_views,
        m0007._create_v_scores_commune_muni,
        m0007._create_v_evolution_blocs_hdf_muni,
        m0007._create_v_listes_commune_muni,
        create_economie_views,  # dépend de v_scores_commune_pres
        create_legislatif_views,
    ]
    for etape in etapes:
        etape(con)


_TABLES_ADR_0011 = frozenset({"leg_mandats", "leg_groupes_blocs"})


def completer_legislatif(con: duckdb.DuckDBPyConnection, tables: set[str]) -> bool:
    """Dérive leg_mandats / leg_groupes_blocs (migration 0008) si l'échantillon ne les a pas.

    Retourne True si la migration a été appliquée.
    """
    if "leg_elus" not in tables or tables >= _TABLES_ADR_0011:
        return False
    m0008 = _charger_migration("0008_legislatif_groupes_par_legislature.py")
    m0008.appliquer_migration(con)
    return True


def _quote(ident: str) -> str:
    return '"' + ident.replace('"', '""') + '"'


def _colonnes_table(con: duckdb.DuckDBPyConnection, table: str) -> set[str]:
    rows = con.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'main' AND table_name = ?",
        [table],
    ).fetchall()
    return {str(r[0]) for r in rows}


def _inserer_table(
    con: duckdb.DuckDBPyConnection, table: str, meta: dict[str, Any], sample_dir: Path
) -> None:
    fichier = str(sample_dir / meta["fichier"]).replace("'", "''")
    colonnes: list[tuple[str, str]] = [(n, t) for n, t in meta["colonnes"]]
    # Géométries stockées en WKB (BLOB) ; si un lecteur Parquet les restitue déjà en
    # GEOMETRY, elles sont reprises telles quelles.
    types_parquet = {
        str(r[0]): str(r[1])
        for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{fichier}')").fetchall()
    }
    geom = {
        n
        for n in meta.get("colonnes_geometrie", [])
        if not types_parquet.get(n, "").upper().startswith("GEOMETRY")
    }
    select = ", ".join(
        f"ST_GeomFromWKB({_quote(n)}) AS {_quote(n)}" if n in geom else _quote(n)
        for n, _ in colonnes
    )
    source = f"SELECT {select} FROM read_parquet('{fichier}')"

    existantes = _colonnes_table(con, table)
    if not existantes:
        warnings.warn(
            f"Table {table} présente dans l'échantillon mais non créée par le code : "
            "créée depuis le Parquet.",
            EcartSchemaEchantillon,
            stacklevel=3,
        )
        con.execute(f"CREATE TABLE {_quote(table)} AS {source}")
        return

    for nom, type_sql in colonnes:
        if nom not in existantes:
            warnings.warn(
                f"Colonne {table}.{nom} ({type_sql}) présente dans l'échantillon mais non "
                "créée par le code : ajoutée.",
                EcartSchemaEchantillon,
                stacklevel=3,
            )
            con.execute(f"ALTER TABLE {_quote(table)} ADD COLUMN {_quote(nom)} {type_sql}")
    con.execute(f"INSERT INTO {_quote(table)} BY NAME {source}")


def construire_base(
    db_path: Path | str = ":memory:",
    *,
    sample_dir: Path = SAMPLE_DIR,
    charger_spatial: bool = False,
) -> duckdb.DuckDBPyConnection:
    """Construit une base DuckDB depuis l'échantillon et retourne la connexion ouverte.

    ``db_path`` : ``":memory:"`` (défaut) ou fichier (pour les modules qui ouvrent la base
    par son chemin, ex. ``viz/*_queries.py`` : fermer la connexion avant de les appeler).
    Les vues présentes dans la base source mais non recréées par le code sont signalées
    par un ``EcartSchemaEchantillon``.
    """
    manifest = charger_manifest(sample_dir)
    con = duckdb.connect(str(db_path))
    try:
        if charger_spatial:
            con.execute("LOAD spatial")
        creer_schema(con)
        for table, meta in manifest["tables"].items():
            _inserer_table(con, table, meta, sample_dir)
        completer_legislatif(con, set(manifest["tables"]))
        creer_vues(con)
        vues = {
            str(r[0])
            for r in con.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_type = 'VIEW'"
            ).fetchall()
        }
        manquantes = sorted(set(manifest.get("vues_source", [])) - vues)
        if manquantes:
            warnings.warn(
                f"Vues de la base source non recréées par le code : {manquantes}",
                EcartSchemaEchantillon,
                stacklevel=2,
            )
    except Exception:
        con.close()
        raise
    return con
