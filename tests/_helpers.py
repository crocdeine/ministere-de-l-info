"""Aides partagées par les tests."""

from __future__ import annotations

from typing import Any

import duckdb


def ligne(res: duckdb.DuckDBPyConnection) -> tuple[Any, ...]:
    """Première ligne d'un résultat ``execute()`` ; échoue explicitement si elle manque."""
    row = res.fetchone()
    assert row is not None, "la requête n'a renvoyé aucune ligne"
    return row
