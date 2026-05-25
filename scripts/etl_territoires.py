"""ETL territorial complet — DuckDB + IGN ADMIN-EXPRESS + INSEE Mélodi + data.gouv.fr.

Usage
-----
    uv run python scripts/etl_territoires.py [--force] [--skip-communes]
        [--millesimes 2013,2018,2023] [--level region]

Étapes couvertes
----------------
    - Schéma DuckDB (7 tables + 2 méta) : toujours exécuté
    - Régions (18), départements (101), EPCI (~1250)
    - Communes (~35 000) — gate utilisateur, 30-60 min
    - Arrondissements municipaux (44), circonscriptions (559)
    - Populations historisées INSEE millésimes 2013 / 2018 / 2023
    - 3 vues SQL d'agrégation (v_population_region/departement/epci)

Base de données cible
---------------------
    data/ministere.duckdb  (partagée avec app.py)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))  # noqa: E402
from ministere_de_l_info.etl._common import open_connection  # noqa: E402
from ministere_de_l_info.etl.loaders import (  # noqa: E402
    load_arrondissements_municipaux,
    load_circonscriptions,
    load_communes,
    load_departements,
    load_epci,
    load_populations,
    load_regions,
    update_epci_departement_principal,
)
from ministere_de_l_info.etl.schema import create_schema  # noqa: E402
from ministere_de_l_info.etl.views import create_views  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

_DB_PATH = ROOT / "data" / "ministere.duckdb"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ETL territorial complet : IGN ADMIN-EXPRESS + INSEE populations → DuckDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemples :\n"
            "  uv run python scripts/etl_territoires.py --millesimes 2023 --skip-communes\n"
            "  uv run python scripts/etl_territoires.py --force --level departement"
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-télécharger les sources même si les fichiers locaux existent",
    )
    parser.add_argument(
        "--skip-communes",
        action="store_true",
        help="Sauter le chargement communes (~35 000 rows, 30-60 min) — pour debug",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Bypass le gate input() du chargement communes (utile pour nohup/CI)",
    )
    parser.add_argument(
        "--millesimes",
        default="2013,2018,2023",
        metavar="ANNEES",
        help="Millésimes INSEE séparés par virgule (défaut: 2013,2018,2023)",
    )
    parser.add_argument(
        "--level",
        choices=[
            "region",
            "departement",
            "epci",
            "commune",
            "arrondissement_municipal",
            "circonscription",
        ],
        default=None,
        metavar="LEVEL",
        help="Charger un seul niveau géographique — debug uniquement",
    )
    args = parser.parse_args()

    try:
        millesimes = [int(m.strip()) for m in args.millesimes.split(",")]
    except ValueError:
        parser.error(f"--millesimes invalide : {args.millesimes!r} — attendu ex: '2013,2018,2023'")

    con = open_connection(_DB_PATH)
    create_schema(con)
    raw_dir = ROOT / "data" / "raw"

    if args.level is None:
        load_regions(con, raw_dir, force=args.force)
        load_departements(con, raw_dir, force=args.force)
        load_epci(con, raw_dir, force=args.force)
        load_communes(con, raw_dir, force=args.force, skip=args.skip_communes, yes=args.yes)
        update_epci_departement_principal(con)
        load_arrondissements_municipaux(con, raw_dir, force=args.force)
        load_circonscriptions(con, raw_dir, force=args.force)
        load_populations(con, raw_dir, millesimes=millesimes, force=args.force)
        create_views(con)
    else:
        _level_dispatch: dict[str, object] = {
            "region": lambda: load_regions(con, raw_dir, force=args.force),
            "departement": lambda: load_departements(con, raw_dir, force=args.force),
            "epci": lambda: load_epci(con, raw_dir, force=args.force),
            "commune": lambda: load_communes(
                con, raw_dir, force=args.force, skip=args.skip_communes, yes=args.yes
            ),
            "arrondissement_municipal": lambda: load_arrondissements_municipaux(
                con, raw_dir, force=args.force
            ),
            "circonscription": lambda: load_circonscriptions(con, raw_dir, force=args.force),
        }
        _level_dispatch[args.level]()  # type: ignore[operator]

    con.close()
    logger.info("ETL terminé.")


if __name__ == "__main__":
    main()
