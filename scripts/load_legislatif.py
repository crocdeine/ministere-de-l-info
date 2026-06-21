"""Chargement des données législatives (Sénat national + AN national via Datan).

Usage :
    uv run python scripts/load_legislatif.py
    uv run python scripts/load_legislatif.py --source senat
    uv run python scripts/load_legislatif.py --source datan
    uv run python scripts/load_legislatif.py --source overrides
    uv run python scripts/load_legislatif.py --force

Sources et tables DuckDB :
  senat     → leg_elus (chambre=SENAT, France entière, ODSEN_GENERAL.csv)
  datan     → leg_elus + leg_activite (chambre=AN, législatures 12-17, national)
  overrides → leg_blocs_override (corrections manuelles de blocs)
  all       → senat + datan + overrides

Idempotent : chaque loader fait DELETE+INSERT par source.

Sources dépréciées (non incluses dans 'all') :
  nosdeputes : figé depuis juin 2024, endpoint /synthese renvoie {}
  clair      : API hors service (HTTP 500 sur tous endpoints)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ministere_de_l_info.etl._common import open_connection  # noqa: E402
from ministere_de_l_info.etl.loaders.legislatif_datan import load_legislatif_datan  # noqa: E402
from ministere_de_l_info.etl.loaders.legislatif_overrides import load_overrides  # noqa: E402
from ministere_de_l_info.etl.loaders.legislatif_senat import load_legislatif_senat  # noqa: E402
from ministere_de_l_info.etl.schema_legislatif import (  # noqa: E402
    create_legislatif_schema,
    create_legislatif_views,
)
from ministere_de_l_info.logging_config import configure_logging  # noqa: E402

_DB_PATH = ROOT / "data" / "ministere.duckdb"
_RAW_DIR = ROOT / "data" / "raw"

configure_logging()
logger = logging.getLogger(__name__)


def _print_summary(con) -> None:  # type: ignore[no-untyped-def]
    print("\n=== Résumé leg_elus ===")
    rows = con.execute(
        "SELECT chambre, source, est_actif, COUNT(*) FROM leg_elus "
        "GROUP BY chambre, source, est_actif ORDER BY chambre, source, est_actif"
    ).fetchall()
    for r in rows:
        actif_str = "actif" if r[2] else "ancien"
        print(f"  {r[0]:6} | {r[1]:14} | {actif_str:6} : {r[3]} élus")

    n_act = con.execute("SELECT COUNT(*) FROM leg_activite").fetchone()[0]
    print(f"  leg_activite : {n_act} métriques")

    n_ov = con.execute("SELECT COUNT(*) FROM leg_blocs_override").fetchone()[0]
    print(f"  leg_blocs_override : {n_ov} overrides")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chargement données législatives")
    parser.add_argument(
        "--source",
        choices=["senat", "datan", "overrides", "all"],
        default="all",
        help="Source à charger (défaut : all)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-télécharger les caches existants",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    logger.info("Connexion DuckDB : %s", _DB_PATH)
    con = open_connection(_DB_PATH)
    try:
        create_legislatif_schema(con)
        create_legislatif_views(con)

        if args.source in ("senat", "all"):
            logger.info("=== Chargement Sénat (ODSEN_GENERAL.csv, France entière) ===")
            load_legislatif_senat(con, _RAW_DIR, force=args.force)

        if args.source in ("datan", "all"):
            logger.info("=== Chargement Datan (AN, législatures 12-17, national) ===")
            load_legislatif_datan(con, _RAW_DIR, force=args.force)

        if args.source in ("overrides", "all"):
            logger.info("=== Application des overrides blocs ===")
            load_overrides(con)

        _print_summary(con)
        print("\nChargement législatif terminé.")
    finally:
        con.close()


if __name__ == "__main__":
    main()
