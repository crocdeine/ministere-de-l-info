"""Test hors ligne du comptage de la veille des groupes du Sénat."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_CHEMIN = Path(__file__).resolve().parents[1] / "scripts" / "veille_groupes_senat.py"
_spec = importlib.util.spec_from_file_location("veille_groupes_senat", _CHEMIN)
assert _spec and _spec.loader
veille = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(veille)

_CSV = """% Requête : en-tête de commentaire
% suite du commentaire
Matricule,État,Groupe politique
1,ACTIF,UC
2,ACTIF,Aucun
3,ACTIF,
4,ANCIEN,Aucun
"""


def test_compte_actifs_sans_groupe() -> None:
    assert veille.compter(_CSV) == (3, 2)
