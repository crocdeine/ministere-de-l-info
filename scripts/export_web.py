"""Export des données de l'application web (logique : ``ministere_de_l_info.export_web``).

Usage :
    uv run python scripts/export_web.py [--db CHEMIN] [--out web/public/data]
        [--departements 80,02] [--tippecanoe CHEMIN | --sans-tuiles]

La base est ouverte en lecture seule. Sortie non commitée (``web/public/data/``).
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from ministere_de_l_info.config import get_settings
from ministere_de_l_info.export_web import exporter

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Export des données de l'application web.")
    parser.add_argument("--db", type=Path, default=get_settings().db_path)
    parser.add_argument("--out", type=Path, default=ROOT / "web" / "public" / "data")
    parser.add_argument("--departements", help="liste séparée par des virgules (échantillon)")
    parser.add_argument("--tippecanoe", default="tippecanoe", help="exécutable tippecanoe ≥ 2.17")
    parser.add_argument("--sans-tuiles", action="store_true", help="pas de communes.pmtiles")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    exporter(
        args.db,
        args.out,
        tippecanoe=None if args.sans_tuiles else args.tippecanoe,
        departements=args.departements.split(",") if args.departements else None,
    )


if __name__ == "__main__":
    main()
