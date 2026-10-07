"""Chargement des européennes, régionales et départementales (vague B, 2026-10-06).

Usage :
    uv run python scripts/load_elections_autres.py [--perimetre hdf|france]
                                                   [--types euro regi dpmt]

Source : Parquet « Données des élections agrégées » (nommage inversé, gotcha n° 8).
Scrutins : européennes 1999-2024, régionales 2004-2021, départementales 2015-2021,
granularité bureau de vote. Idempotent : DELETE + INSERT par type de scrutin, sans
toucher aux autres scrutins. Les nuances de ces scrutins (vague B, décision Mathias 2026-10-07, ADR-0010)
et les listes européennes 2019 sont écrites par populate_nuances_vague_b.
Les cantonales (cant) ne sont pas chargées (hors décision du 2026-10-06).
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
from ministere_de_l_info.etl.loaders.elections_agregees import (  # noqa: E402
    PERIMETRES,
    TYPES_VAGUE_B,
    load_scrutins_listes,
)
from ministere_de_l_info.etl.schema_elections import populate_nuances_vague_b  # noqa: E402
from ministere_de_l_info.logging_config import configure_logging  # noqa: E402

configure_logging()
logger = logging.getLogger(__name__)

_PARQUET_CANDIDATS = ROOT / "data" / "exploration" / "general-results.parquet"
_PARQUET_PARTICIPATION = ROOT / "data" / "exploration" / "candidats-results.parquet"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--perimetre", choices=PERIMETRES, default="hdf")
    parser.add_argument("--types", nargs="+", choices=TYPES_VAGUE_B, default=list(TYPES_VAGUE_B))
    args = parser.parse_args()

    for p in (_PARQUET_PARTICIPATION, _PARQUET_CANDIDATS):
        if not p.exists():
            logger.error("Parquet manquant : %s", p)
            sys.exit(1)

    db_path = get_settings().db_path
    logger.info("Chargement %s (%s) → %s", "/".join(args.types), args.perimetre, db_path)
    con = open_connection(db_path)
    try:
        populate_nuances_vague_b(con)
        for type_scrutin in args.types:
            load_scrutins_listes(
                con, type_scrutin, _PARQUET_CANDIDATS, _PARQUET_PARTICIPATION, args.perimetre
            )
        n_total = con.execute("SELECT COUNT(*) FROM resultats_candidats").fetchone()
        upsert_metadata(
            con,
            "resultats_candidats",
            int(n_total[0]) if n_total else 0,
            f"données des élections agrégées (data.gouv) ; vague B {args.perimetre}",
        )
        for idel, n_bv, n_cand, n_null in con.execute("""
            SELECT e.id_election,
                   (SELECT COUNT(*) FROM resultats_participation rp
                     WHERE rp.id_election = e.id_election),
                   (SELECT COUNT(*) FROM resultats_candidats rc
                     WHERE rc.id_election = e.id_election),
                   (SELECT COUNT(*) FROM v_resultats_candidats_avec_bloc v
                     WHERE v.id_election = e.id_election AND v.bloc IS NULL)
            FROM elections e WHERE e.type_scrutin IN ('euro', 'regi', 'dpmt')
            ORDER BY 1
        """).fetchall():
            logger.info("%-14s BV %9d  lignes %10d  sans bloc %8d", idel, n_bv, n_cand, n_null)
    finally:
        con.close()


if __name__ == "__main__":
    main()
