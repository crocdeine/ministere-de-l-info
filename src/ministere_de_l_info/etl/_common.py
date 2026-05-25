"""Utilitaires partagés pour les loaders ETL."""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)

_DB_PATH_DEFAULT = Path(__file__).resolve().parents[3] / "data" / "ministere.duckdb"


def open_connection(db_path: Path = _DB_PATH_DEFAULT) -> duckdb.DuckDBPyConnection:
    """Ouvre la connexion DuckDB et charge l'extension spatial."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    con.execute("INSTALL spatial; LOAD spatial;")
    logger.debug("Connexion DuckDB ouverte : %s", db_path)
    return con


def upsert_metadata(
    con: duckdb.DuckDBPyConnection,
    table_name: str,
    row_count: int,
    source_version: str,
) -> None:
    """Insère ou remplace une entrée dans _etl_metadata."""
    con.execute("DELETE FROM _etl_metadata WHERE table_name = ?", [table_name])
    con.execute(
        "INSERT INTO _etl_metadata VALUES (?, NOW(), ?, ?)",
        [table_name, source_version, row_count],
    )
