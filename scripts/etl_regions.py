"""ETL : téléchargement et chargement des contours régions dans DuckDB."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))  # noqa: E402

from ministere_de_l_info.data_sources.geo import POPULATION_2024, fetch_regions_geojson  # noqa: E402, I001

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

RAW_PATH = ROOT / "data" / "raw" / "regions_2024.geojson"
DB_PATH = ROOT / "data" / "ministere.duckdb"


def download_if_needed(force: bool) -> None:
    """Télécharge le GeoJSON si absent ou si --force est passé."""
    if RAW_PATH.exists() and not force:
        logger.info("Fichier existant — skip téléchargement (--force pour forcer)")
        return
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = fetch_regions_geojson()
    RAW_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Sauvegardé : %s", RAW_PATH)


def load_into_duckdb() -> None:
    """Charge le GeoJSON dans DuckDB, table geographies_regions (idempotent)."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    con.execute("INSTALL spatial; LOAD spatial;")

    # Clause VALUES pour la population — données internes, pas de risque d'injection
    pop_values = ", ".join(f"('{code}', {pop})" for code, pop in POPULATION_2024.items())
    geojson_path = str(RAW_PATH).replace("'", "''")  # échappement SQL du chemin

    con.execute(f"""
        CREATE OR REPLACE TABLE geographies_regions AS
        SELECT
            CAST(src.code AS VARCHAR) AS code_insee,
            src.nom,
            CAST(pop.population AS INTEGER) AS population,
            ST_Simplify(src.geom, 0.001) AS geometry
        FROM ST_Read('{geojson_path}') AS src
        JOIN (VALUES {pop_values}) AS pop(code, population)
          ON CAST(src.code AS VARCHAR) = pop.code
    """)

    count = con.execute("SELECT COUNT(*) FROM geographies_regions").fetchone()[0]
    logger.info("Table geographies_regions : %d lignes chargées", count)
    con.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="ETL contours des régions françaises")
    parser.add_argument("--force", action="store_true", help="Forcer le re-téléchargement")
    args = parser.parse_args()

    download_if_needed(args.force)
    load_into_duckdb()
    logger.info("ETL terminé avec succès")


if __name__ == "__main__":
    main()
