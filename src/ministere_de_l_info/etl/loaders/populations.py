"""Loader INSEE Mélodi — populations communales historisées."""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from ministere_de_l_info.data_sources.insee_populations import fetch_populations
from ministere_de_l_info.etl._common import upsert_metadata

logger = logging.getLogger(__name__)

_SOURCE = "DS_POPULATIONS_HISTORIQUES"


def load_populations(
    con: duckdb.DuckDBPyConnection,
    raw_dir: Path,
    millesimes: list[int],
    force: bool = False,
) -> None:
    """Charge les populations municipales INSEE pour chaque millésime.

    Idempotence : skip si COUNT(*) WHERE annee=X > 0 et force=False.
    Avec force=True : DELETE WHERE annee=X AND source=_SOURCE + re-INSERT.
    """
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
                "DELETE FROM populations WHERE annee = ? AND source = ?",
                [annee, _SOURCE],
            )
            logger.info("Populations %d supprimées pour re-chargement.", annee)

        df = fetch_populations(annee, force=force, raw_dir=raw_dir)

        con.register("_pop_temp", df)
        con.execute(f"""
            INSERT INTO populations (code_insee_commune, annee, municipale, comptee_a_part, totale, source)
            SELECT code_insee_commune, annee, municipale, comptee_a_part, totale, '{_SOURCE}'
            FROM _pop_temp
        """)
        con.unregister("_pop_temp")

        count = con.execute("SELECT COUNT(*) FROM populations WHERE annee = ?", [annee]).fetchone()[
            0
        ]
        logger.info("Populations %d chargées : %d communes.", annee, count)

        upsert_metadata(con, f"populations_{annee}", count, _SOURCE)
