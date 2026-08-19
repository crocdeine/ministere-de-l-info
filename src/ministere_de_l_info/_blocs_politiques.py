"""Constantes partagées pour les 6 blocs politiques officiels (ADR-0005).

Couleurs alignées sur les tokens CSS ``--nuance-*`` du design system
(``src/ministere_de_l_info/custom.css``) et sur la table DuckDB
``blocs_politiques`` (voir ``docs/schema-elections.md``). Source unique de
vérité pour éviter la divergence entre modules (constatée entre
``legislatif.py`` et ``economie.py`` avant réconciliation).
"""

from __future__ import annotations

BLOCS_ORDERED: list[str] = ["EXG", "GAU", "DIV", "CENT", "DTE", "EXD"]

COULEURS_BLOCS: dict[str, str] = {
    "EXG": "#8B0000",
    "GAU": "#E84C61",
    "DIV": "#9E9E9E",
    "CENT": "#F5B800",
    "DTE": "#3B7DD8",
    "EXD": "#1F3864",
}

LIBELLES_BLOCS: dict[str, str] = {
    "EXG": "Extrême gauche",
    "GAU": "Gauche",
    "DIV": "Divers",
    "CENT": "Centre",
    "DTE": "Droite",
    "EXD": "Extrême droite",
}
