"""Aides DuckDB partagées."""

from __future__ import annotations

from typing import Any

import duckdb


def ligne_unique(res: duckdb.DuckDBPyConnection) -> tuple[Any, ...]:
    """Première ligne d'un résultat ``execute()`` ; lève si elle manque.

    Pour les requêtes d'agrégat (``COUNT``, ``MAX``...) qui renvoient toujours une ligne.
    """
    row = res.fetchone()
    if row is None:
        raise RuntimeError("La requête n'a renvoyé aucune ligne (agrégat attendu).")
    return row
