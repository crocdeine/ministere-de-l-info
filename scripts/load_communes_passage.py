"""Construit communes_passage (communes fusionnées → commune actuelle) depuis l'INSEE.

Usage :
    uv run python scripts/load_communes_passage.py [--force]

Source : INSEE, COG, fichier des mouvements des communes (Licence Ouverte 2.0), mis en
cache dans data/raw/cog/. À lancer après etl_territoires.py (référentiel des communes) et
avant les loaders électoraux (décision Mathias 2026-10-07).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ministere_de_l_info.config import get_settings  # noqa: E402
from ministere_de_l_info.etl._common import open_connection, upsert_metadata  # noqa: E402
from ministere_de_l_info.etl.loaders.communes_passage import (  # noqa: E402
    MILLESIME_COG,
    construire_passage,
    telecharger_mvt,
)
from ministere_de_l_info.logging_config import configure_logging  # noqa: E402

configure_logging()
logger = logging.getLogger(__name__)


def main() -> None:
    from ministere_de_l_info.espace_disque import verifier_espace

    verifier_espace(get_settings().db_path.parent)
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--force", action="store_true", help="re-télécharger le fichier INSEE")
    args = parser.parse_args()
    csv_mvt = telecharger_mvt(ROOT / "data" / "raw", force=args.force)
    con = open_connection(get_settings().db_path)
    try:
        n = construire_passage(con, csv_mvt)
        upsert_metadata(
            con, "communes_passage", n, f"INSEE COG {MILLESIME_COG}, mouvements des communes"
        )
    finally:
        con.close()


if __name__ == "__main__":
    main()
