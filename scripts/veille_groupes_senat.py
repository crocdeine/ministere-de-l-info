"""Veille : les sénateurs élus le 27/09/2026 ont-ils reçu leur groupe sur data.senat.fr ?

Lit le fichier officiel ODSEN_GENERAL (sans rien écrire dans la base) et compte les
sénateurs actifs sans groupe. Code de sortie : 0 si tous ont un groupe (la base peut être
rechargée puis republiée, étape 6 de reports/a-faire-sur-le-mac.md), 1 sinon.

Usage : uv run python scripts/veille_groupes_senat.py
"""

from __future__ import annotations

import csv
import io
import sys

import httpx

URL = "https://data.senat.fr/data/senateurs/ODSEN_GENERAL.csv"
SANS_GROUPE = {"", "Aucun"}


def compter(texte: str) -> tuple[int, int]:
    """(sénateurs actifs, actifs sans groupe) dans le CSV ODSEN_GENERAL."""
    lignes = [ligne for ligne in texte.splitlines() if not ligne.startswith("%")]
    actifs = [r for r in csv.DictReader(io.StringIO("\n".join(lignes))) if r["État"] == "ACTIF"]
    sans = sum(1 for r in actifs if r["Groupe politique"].strip() in SANS_GROUPE)
    return len(actifs), sans


def main() -> int:
    reponse = httpx.get(URL, timeout=60, follow_redirects=True)
    reponse.raise_for_status()
    actifs, sans = compter(reponse.content.decode("cp1252"))
    maj = reponse.headers.get("last-modified", "date inconnue")
    sys.stdout.write(f"Fichier du {maj} : {actifs} sénateurs actifs, {sans} sans groupe.\n")
    return 0 if sans == 0 and actifs > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
