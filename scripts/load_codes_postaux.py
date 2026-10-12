"""Charge `codes_postaux` (La Poste, hexasmal, Licence Ouverte 2.0) dans la base.

Usage :
    uv run python scripts/load_codes_postaux.py [--db CHEMIN] [--force]

Nécessaire à la recherche par code postal de l'application web (export_web).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ministere_de_l_info.config import get_settings  # noqa: E402
from ministere_de_l_info.espace_disque import verifier_espace  # noqa: E402
from ministere_de_l_info.etl._common import open_connection, upsert_metadata  # noqa: E402
from ministere_de_l_info.etl.loaders.codes_postaux import charger, telecharger  # noqa: E402
from ministere_de_l_info.logging_config import configure_logging  # noqa: E402


def main() -> None:
    configure_logging()
    p = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    p.add_argument("--db", type=Path, default=get_settings().db_path)
    p.add_argument("--force", action="store_true", help="re-télécharger hexasmal.csv")
    a = p.parse_args()
    verifier_espace(a.db.parent)
    csv = telecharger(ROOT / "data" / "raw", force=a.force)
    con = open_connection(a.db)
    try:
        n = charger(con, csv)
        upsert_metadata(con, "codes_postaux", n, "La Poste, base officielle des codes postaux")
    finally:
        con.close()


if __name__ == "__main__":
    main()
