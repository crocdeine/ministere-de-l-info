"""Chargement des données économiques INSEE (Filosofi + RP) pour HdF.

Usage :
    uv run python scripts/load_economie.py
    uv run python scripts/load_economie.py --force
    uv run python scripts/load_economie.py --source filosofi
    uv run python scripts/load_economie.py --source rp
    uv run python scripts/load_economie.py --millesimes 2020,2021

Sources :
    Dataset data.gouv.fr 67289477639527408ae687da :
    "Recensement de la population communal et Filosofi depuis 2015 — France métropolitaine"
    Fichier unique : donnees-insee-olap.parquet (1.73 Go national)
    Format OLAP (long) : code_com, nom_commune, annee, source, clef_json, valeur

    Indicateurs chargés :
    - Filosofi (source='filosofi_disponible') : taux_pauvrete, niveau_vie_median, déciles
    - RP emploi (source='rp_actifs_emploi')  : tx_chomage_dec, part_ouvriers_employes,
                                               part_emploi_industriel, pop_active

Stratégie cache :
    Première exécution : DuckDB httpfs télécharge le Parquet national et sauvegarde
    une version filtrée HdF (~50 Mo) dans data/raw/economie/donnees-insee-olap-hdf.parquet.
    Exécutions suivantes : lecture du cache local (--force pour re-télécharger).

Filtre :
    Hauts-de-France uniquement (depts 02, 59, 60, 62, 80)

Idempotent :
    DELETE + INSERT par source et millésime.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import duckdb  # noqa: E402

from ministere_de_l_info.etl._common import open_connection  # noqa: E402
from ministere_de_l_info.etl.loaders.economie_filosofi import load_economie_filosofi  # noqa: E402
from ministere_de_l_info.etl.loaders.economie_rp import load_economie_rp  # noqa: E402
from ministere_de_l_info.etl.schema_economie import (  # noqa: E402
    create_economie_schema,
    create_economie_views,
)
from ministere_de_l_info.logging_config import configure_logging  # noqa: E402

configure_logging()
logger = logging.getLogger(__name__)

_DB_PATH = ROOT / "data" / "ministere.duckdb"
_RAW_DIR = ROOT / "data" / "raw"
_CACHE_DIR = _RAW_DIR / "economie"
_CACHE_FILE = _CACHE_DIR / "donnees-insee-olap-hdf.parquet"

_PARQUET_URL = (
    "https://static.data.gouv.fr/resources/"
    "recensement-de-la-population-communal-et-filosofi-depuis-2015-france-metropolitaine/"
    "20241104-093439/donnees-insee-olap.parquet"
)

_DEPTS_HDF = ("02", "59", "60", "62", "80")


def _build_hdf_cache(force: bool = False, yes: bool = False) -> None:
    """Télécharge et filtre le Parquet national → cache HdF local.

    Le fichier source est 1.73 Go (national, toutes sources). DuckDB httpfs
    lit le Parquet distamment avec pushdown HdF et sauvegarde ~50 Mo en local.
    """
    if _CACHE_FILE.exists() and not force:
        logger.info("Cache HdF existant : %s (--force pour re-télécharger)", _CACHE_FILE)
        return

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if not yes:
        try:
            reponse = (
                input(
                    "\nTéléchargement Parquet INSEE (~1.73 Go, ~30-60 s).\nContinuer ? [oui/non] "
                )
                .strip()
                .lower()
            )
        except (EOFError, KeyboardInterrupt):
            logger.info("Téléchargement annulé.")
            sys.exit(0)
        if reponse != "oui":
            logger.info("Téléchargement annulé par l'utilisateur.")
            sys.exit(0)

    logger.info("Création cache HdF : %s", _CACHE_FILE)
    logger.info("URL source : %s", _PARQUET_URL)

    filtre_hdf = " OR ".join(f"LEFT(code_com, 2) = '{d}'" for d in _DEPTS_HDF)

    con_tmp = duckdb.connect(":memory:")
    con_tmp.execute("INSTALL httpfs; LOAD httpfs;")
    con_tmp.execute(f"""
        COPY (
            SELECT *
            FROM read_parquet('{_PARQUET_URL}')
            WHERE {filtre_hdf}
        ) TO '{_CACHE_FILE}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)
    con_tmp.close()

    size_mb = _CACHE_FILE.stat().st_size / 1_048_576
    logger.info("Cache HdF créé : %.1f Mo", size_mb)


def _print_summary(con: duckdb.DuckDBPyConnection) -> None:
    """Affiche les volumes par table et millésime."""
    print("\n── economie_filosofi ─────────────────────────────────────────────────────")
    rows = con.execute(
        "SELECT annee, COUNT(*) AS n_communes FROM economie_filosofi GROUP BY annee ORDER BY annee"
    ).fetchall()
    if rows:
        print(f"  {'annee':>6s} {'communes':>10s}")
        for annee, n in rows:
            print(f"  {annee:>6d} {n:>10,}")
        total_f = sum(n for _, n in rows)
        print(f"  {'TOTAL':>6s} {total_f:>10,}")
    else:
        print("  (vide)")

    print("\n── economie_rp ───────────────────────────────────────────────────────────")
    rows = con.execute(
        "SELECT annee_millesime, COUNT(*) AS n_communes FROM economie_rp "
        "GROUP BY annee_millesime ORDER BY annee_millesime"
    ).fetchall()
    if rows:
        print(f"  {'millesime':>9s} {'communes':>10s}")
        for annee, n in rows:
            print(f"  {annee:>9d} {n:>10,}")
        total_r = sum(n for _, n in rows)
        print(f"  {'TOTAL':>9s} {total_r:>10,}")
    else:
        print("  (vide)")

    # Vérification Lille (59350) — valeurs de référence connues
    print("\n── Vérification Lille (59350), 2021 ──────────────────────────────────────")
    row_f = con.execute(
        "SELECT taux_pauvrete, niveau_vie_median, d1_niveau_vie, d9_niveau_vie "
        "FROM economie_filosofi WHERE code_commune = '59350' AND annee = 2021"
    ).fetchone()
    if row_f:
        tp, nvm, d1, d9 = row_f
        print(f"  Filosofi  taux_pauvrete={tp:.1f}%  niv_vie_median={nvm:.0f}€")
        print(f"            D1={d1:.0f}€  D9={d9:.0f}€")
    else:
        print("  Filosofi  (absent — millésime 2021 non chargé ?)")

    row_r = con.execute(
        "SELECT tx_chomage_dec, part_ouvriers_employes, part_emploi_industriel, "
        "part_logements_sociaux, nb_logements_sociaux, pop_active "
        "FROM economie_rp WHERE code_commune = '59350' AND annee_millesime = 2021"
    ).fetchone()
    if row_r:
        tc, po, pi, pls, nls, pa = row_r
        print(
            f"  RP        tx_chomage={tc:.1f}%  ouvriers_emp={po:.1f}%  "
            f"industrie={pi:.1f}%  pop_active={pa:,}"
        )
        pls_str = f"{pls:.1f}%" if pls is not None else "NULL"
        nls_str = f"{nls:,}" if nls is not None else "NULL"
        print(f"            log_sociaux={pls_str}  nb_hlm={nls_str}")
    else:
        print("  RP        (absent — millésime 2021 non chargé ?)")
    print("──────────────────────────────────────────────────────────────────────────")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Chargement données économiques INSEE → DuckDB (HdF)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-télécharger le cache HdF même s'il existe déjà",
    )
    parser.add_argument(
        "--source",
        choices=["filosofi", "rp", "all"],
        default="all",
        help="Source à charger : filosofi | rp | all (défaut : all)",
    )
    parser.add_argument(
        "--millesimes",
        type=str,
        default=None,
        help="Années séparées par virgule, ex: 2020,2021,2022",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Bypass confirmation pour le téléchargement initial",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    millesimes: list[int] | None = None
    if args.millesimes:
        millesimes = [int(m.strip()) for m in args.millesimes.split(",")]
        logger.info("Millésimes ciblés : %s", millesimes)

    _build_hdf_cache(force=args.force, yes=args.yes)

    logger.info("Connexion DuckDB : %s", _DB_PATH)
    con = open_connection(_DB_PATH)
    try:
        create_economie_schema(con)
        create_economie_views(con)

        if args.source in ("filosofi", "all"):
            logger.info("=== Chargement Filosofi ===")
            load_economie_filosofi(con, _RAW_DIR, force=args.force, millesimes=millesimes)

        if args.source in ("rp", "all"):
            logger.info("=== Chargement RP emploi ===")
            load_economie_rp(con, _RAW_DIR, force=args.force, millesimes=millesimes)

        _print_summary(con)
        print("\nChargement économie terminé.")
    finally:
        con.close()


if __name__ == "__main__":
    main()
