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

# Variante pour les TRAITS et textes sur fond blanc : le jaune CENT (#F5B800) n'a que 1,8:1 de
# contraste. Seuls les traits sont assombris (3,3:1, seuil WCAG 1.4.11) ; les remplissages
# gardent COULEURS_BLOCS (choix éditorial, ADR-0009).
COULEUR_TRAIT_CENT: str = "#B38600"


def couleurs_traits(couleurs: dict[str, str]) -> dict[str, str]:
    """Couleurs de blocs pour des lignes/textes : CENT assombri, le reste inchangé."""
    return {**couleurs, "CENT": COULEUR_TRAIT_CENT}


LIBELLES_BLOCS: dict[str, str] = {
    "EXG": "Extrême gauche",
    "GAU": "Gauche",
    "DIV": "Divers",
    "CENT": "Centre",
    "DTE": "Droite",
    "EXD": "Extrême droite",
}

# Grilles officielles de blocs (ADR-0010) : seules les municipales 2020 et 2026 en ont une.
_GRILLES_OFFICIELLES: dict[tuple[str, int], str] = {
    ("muni", 2020): "INTA1931378J, annexe 3",
    ("muni", 2026): "INTP2602966C, annexe 3",
}


def methode_classement(type_scrutin: str, annee: int) -> str:
    """``officielle`` si le scrutin a une grille officielle de blocs, sinon ``reconstruit``."""
    return "officielle" if (type_scrutin, annee) in _GRILLES_OFFICIELLES else "reconstruit"


def legende_classement_blocs(type_scrutin: str, annee: int) -> str:
    """Légende honnête de l'origine du classement des blocs pour un scrutin.

    ``type_scrutin`` : ``pres``, ``legi`` ou ``muni``.
    """
    grille = _GRILLES_OFFICIELLES.get((type_scrutin, annee))
    if grille:
        # ponytail: 23 codes sur 48 (2020, 2026) restent à rattacher ligne à ligne (J2)
        return (
            f"Classement des blocs : grille officielle du ministère de l'Intérieur ({grille}), "
            "reportée par le projet ; vérification code par code en cours."
        )
    reference = "IOMA2322276J, 2023" if annee >= 2023 else "INTA1931378J, 2020"
    return (
        "Classement des blocs : reconstruction par le projet, aucune grille officielle "
        f"pour ce scrutin ; grille officielle la plus proche ({reference}) appliquée "
        "aux codes qu'elle couvre. "
        "Méthode : docs/adr/0010-revision-nuances-et-blocs.md."
    )
