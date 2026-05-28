"""Initialise le schéma électoral dans data/ministere.duckdb.

Usage
-----
    uv run python scripts/init_elections_schema.py

Crée les 6 tables électorales (idempotent) et remplit les 4 référentiels :
- blocs_politiques (7 blocs avec couleurs)
- elections (56 scrutins 1999-2026)
- nuances_harmonisees (présidentielles 2002/2007/2012 avec nuances)
- candidats_presidentielle (présidentielles 2017/2022 sans nuances)

Les tables de résultats (resultats_participation, resultats_candidats) sont créées
vides. Le chargement des Parquet se fait en C2b (scripts/load_elections.py).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))  # noqa: E402

from ministere_de_l_info.etl._common import open_connection  # noqa: E402
from ministere_de_l_info.etl.schema_elections import (  # noqa: E402
    create_elections_schema,
    populate_elections_referentiels,
)
from ministere_de_l_info.logging_config import configure_logging  # noqa: E402

configure_logging()
logger = logging.getLogger(__name__)

_DB_PATH = ROOT / "data" / "ministere.duckdb"


def main() -> None:
    logger.info("Initialisation du schéma électoral → %s", _DB_PATH)
    con = open_connection(_DB_PATH)

    create_elections_schema(con)
    populate_elections_referentiels(con)

    # ── Résumé ────────────────────────────────────────────────────────────
    tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
    logger.info("Tables dans la DB : %s", tables)

    counts: dict[str, int] = {}
    for tbl in (
        "blocs_politiques",
        "elections",
        "nuances_harmonisees",
        "candidats_presidentielle",
        "resultats_participation",
        "resultats_candidats",
    ):
        n = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]  # noqa: S608
        counts[tbl] = n

    print("\n── Résumé des référentiels ───────────────────────────────────")
    for tbl, n in counts.items():
        print(f"  {tbl:<35s} {n:>6,} lignes")
    print("─────────────────────────────────────────────────────────────")
    print("Schéma électoral initialisé. Chargement données → C2b.")

    con.close()


if __name__ == "__main__":
    main()
