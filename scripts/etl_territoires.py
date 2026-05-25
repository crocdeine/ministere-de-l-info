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
import json
import logging
import sys
import tempfile
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))  # noqa: E402

from ministere_de_l_info.data_sources.circonscriptions import (  # noqa: F401, E402
    fetch_circonscriptions_legislatives,
)
from ministere_de_l_info.data_sources.insee_populations import fetch_populations  # noqa: E402
from ministere_de_l_info.etl._common import open_connection  # noqa: E402
from ministere_de_l_info.etl.loaders import (  # noqa: E402
    load_arrondissements_municipaux,
    load_communes,
    load_departements,
    load_epci,
    load_regions,
    update_epci_departement_principal,
)
from ministere_de_l_info.etl.schema import create_schema  # noqa: E402
from ministere_de_l_info.etl.views import create_views  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

_DB_PATH = ROOT / "data" / "ministere.duckdb"


def _load_circonscriptions(con: duckdb.DuckDBPyConnection, force: bool = False) -> None:
    """Charge les 559 circonscriptions législatives dans geographies_circonscriptions.

    Source : fetch_circonscriptions_legislatives() — data.gouv.fr (jerome-desboeufs).
    Code format : '{dept}-{num:02d}' — ex: '01-04', '971-01'.
    559 features = 539 métro + 20 DROM/SPM (18 hors-scope : FE + COM absents de la source).
    Simplification : geometry_simplified_circo (0.001).
    Le GeoJSON normalisé est écrit dans un fichier temporaire pour ST_Read.
    Écrit dans _etl_metadata après succès.
    """
    raw_dir = ROOT / "data" / "raw"
    geojson = fetch_circonscriptions_legislatives(force=force, raw_dir=raw_dir)

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".geojson",
            delete=False,
            encoding="utf-8",
            dir=raw_dir,
        ) as f:
            json.dump(geojson, f, ensure_ascii=False)
            tmp_path = Path(f.name)

        con.execute("DROP TABLE IF EXISTS geographies_circonscriptions")
        con.execute("""
            CREATE TABLE geographies_circonscriptions (
                code                      VARCHAR(6) NOT NULL,
                nom                       VARCHAR,
                code_departement          VARCHAR(3),
                nom_departement           VARCHAR,
                geometry                  GEOMETRY,
                geometry_simplified_circo GEOMETRY,
                UNIQUE (code)
            )
        """)

        path_sql = str(tmp_path).replace("'", "''")
        con.execute(f"""
            INSERT INTO geographies_circonscriptions
            SELECT
                code,
                nom,
                code_departement,
                nom_departement,
                geom AS geometry,
                CASE
                    WHEN ST_IsValid(ST_Simplify(geom, 0.001)) THEN ST_Simplify(geom, 0.001)
                    ELSE geom
                END AS geometry_simplified_circo
            FROM ST_Read('{path_sql}')
        """)
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)

    count = con.execute("SELECT COUNT(*) FROM geographies_circonscriptions").fetchone()[0]
    if not (550 <= count <= 565):
        raise RuntimeError(
            f"Nombre de circonscriptions hors fourchette [550-565] : {count}. "
            "Vérifier la source ou utiliser --force pour re-télécharger."
        )
    logger.info("Chargé %d circonscriptions législatives.", count)

    con.execute("DELETE FROM _etl_metadata WHERE table_name = 'geographies_circonscriptions'")
    con.execute(
        "INSERT INTO _etl_metadata VALUES (?, NOW(), 'data.gouv.fr/jerome-desboeufs', ?)",
        ["geographies_circonscriptions", count],
    )


def _load_populations(
    con: duckdb.DuckDBPyConnection,
    millesimes: list[int],
    force: bool = False,
) -> None:
    """Charge les populations municipales INSEE pour chaque millésime.

    Source : fetch_populations(annee) — DS_POPULATIONS_HISTORIQUES Mélodi INSEE.
    Idempotence : skip si COUNT(*) WHERE annee=X > 0 et force=False.
    Avec --force : DELETE WHERE annee=X AND source='DS_POPULATIONS_HISTORIQUES' + re-INSERT.
    comptee_a_part et totale resteront NULL (PCAP absent de la source, voir TODO v2 insee_populations.py).
    Écrit dans _etl_metadata après chaque millésime chargé.
    """
    raw_dir = ROOT / "data" / "raw"

    for annee in millesimes:
        existing = con.execute(
            "SELECT COUNT(*) FROM populations WHERE annee = ?", [annee]
        ).fetchone()[0]

        if existing > 0 and not force:
            logger.info(
                "Populations %d déjà chargées (%d lignes) — ignoré (--force pour recréer).",
                annee,
                existing,
            )
            continue

        if force and existing > 0:
            con.execute(
                "DELETE FROM populations WHERE annee = ? AND source = 'DS_POPULATIONS_HISTORIQUES'",
                [annee],
            )
            logger.info("Populations %d supprimées pour re-chargement.", annee)

        df = fetch_populations(annee, force=force, raw_dir=raw_dir)

        con.register("_pop_temp", df)
        con.execute("""
            INSERT INTO populations (code_insee_commune, annee, municipale, comptee_a_part, totale, source)
            SELECT code_insee_commune, annee, municipale, comptee_a_part, totale,
                   'DS_POPULATIONS_HISTORIQUES'
            FROM _pop_temp
        """)
        con.unregister("_pop_temp")

        count = con.execute("SELECT COUNT(*) FROM populations WHERE annee = ?", [annee]).fetchone()[
            0
        ]
        logger.info("Populations %d chargées : %d communes.", annee, count)

        meta_key = f"populations_{annee}"
        con.execute("DELETE FROM _etl_metadata WHERE table_name = ?", [meta_key])
        con.execute(
            "INSERT INTO _etl_metadata VALUES (?, NOW(), 'DS_POPULATIONS_HISTORIQUES', ?)",
            [meta_key, count],
        )


# ── CLI ───────────────────────────────────────────────────────────────────────


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
        _load_circonscriptions(con, force=args.force)
        _load_populations(con, millesimes=millesimes, force=args.force)
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
            "circonscription": lambda: _load_circonscriptions(con, force=args.force),
        }
        _level_dispatch[args.level]()  # type: ignore[operator]

    con.close()
    logger.info("ETL terminé.")


if __name__ == "__main__":
    main()
