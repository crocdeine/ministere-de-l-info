"""Garde d'espace disque : refuse toute écriture lourde sous le seuil (10 Go par défaut)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

ENV_SEUIL_GO = "MINISTERE_ESPACE_MIN_GO"
SEUIL_DEFAUT_GO = 10.0


def seuil_octets() -> int:
    """Seuil en octets, surchargeable par `MINISTERE_ESPACE_MIN_GO`."""
    return int(float(os.environ.get(ENV_SEUIL_GO, SEUIL_DEFAUT_GO)) * 1e9)


def verifier_espace(*dossiers: Path | str, minimum_octets: int | None = None) -> None:
    """Lève OSError si un dossier a moins que le seuil (le plus élevé de seuil/minimum) libre."""
    seuil = max(seuil_octets(), minimum_octets or 0)
    for d in dossiers:
        libre = shutil.disk_usage(d).free
        if libre < seuil:
            raise OSError(
                f"Espace disque insuffisant sur {d} : {libre / 1e9:.2f} Go libres, "
                f"seuil {seuil / 1e9:.2f} Go (variable {ENV_SEUIL_GO})"
            )
