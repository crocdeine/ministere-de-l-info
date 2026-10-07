"""Périmètre géographique de référence : les 5 départements des Hauts-de-France.

Source unique (vague B, 2026-10-07) pour les loaders, les vues et les requêtes de
l'interface. La région se filtre aussi par code_region = '32'.
"""

from __future__ import annotations

DEPTS_HDF: tuple[str, ...] = ("02", "59", "60", "62", "80")
# Liste SQL littérale (constante interne, pas de donnée utilisateur)
DEPTS_HDF_SQL: str = ", ".join(f"'{d}'" for d in DEPTS_HDF)
