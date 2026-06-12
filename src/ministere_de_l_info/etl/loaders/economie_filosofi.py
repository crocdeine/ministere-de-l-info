"""Loader Filosofi — revenus et pauvreté par commune HdF.

Source : INSEE Filosofi via dataset data.gouv.fr 67289477639527408ae687da
  "Recensement de la population communal et Filosofi depuis 2015"
  URL Parquet : voir _PARQUET_URL dans scripts/load_economie.py

Format source : long (OLAP) — colonnes : code_com, nom_commune, annee, source, clef_json, valeur
Source Filosofi : source = 'filosofi_disponible', millésimes 2017-2021

Mapping clef_json → colonnes DuckDB :
  taux_de_pauvrete  → taux_pauvrete    (%, ex: 27.0 pour 27%)
  revenu_median     → niveau_vie_median (euros, ex: 20520)
  1er_decile        → d1_niveau_vie    (euros)
  9eme_decile       → d9_niveau_vie    (euros)

Secret statistique : valeur = NULL dans le Parquet (masquée par INSEE).
  Le champ secret = TRUE si tous les indicateurs principaux sont NULL.
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from ministere_de_l_info.etl._common import upsert_metadata

logger = logging.getLogger(__name__)

_DEPTS_HDF = ("02", "59", "60", "62", "80")


def load_economie_filosofi(
    con: duckdb.DuckDBPyConnection,
    raw_dir: Path,
    force: bool = False,
    millesimes: list[int] | None = None,
) -> None:
    """Charge les données Filosofi (revenus/pauvreté) HdF dans economie_filosofi.

    Sources : INSEE Filosofi via data.gouv.fr — Dispositif Filosofi
    Granularité : commune × année
    Filtre : Hauts-de-France (depts 02, 59, 60, 62, 80)
    Millésimes disponibles : 2017-2021 (dataset mis à jour novembre 2024)
    Secret statistique : valeur NULL dans le Parquet source
    """
    parquet_path = raw_dir / "economie" / "donnees-insee-olap-hdf.parquet"
    if not parquet_path.exists():
        raise FileNotFoundError(
            f"Cache HdF introuvable : {parquet_path}\n"
            "Exécuter scripts/load_economie.py pour créer le cache."
        )

    path_sql = str(parquet_path).replace("'", "''")
    filtre_hdf = " OR ".join(f"LEFT(code_com, 2) = '{d}'" for d in _DEPTS_HDF)

    annees_cond = ""
    if millesimes:
        annees_str = ", ".join(str(m) for m in millesimes)
        annees_cond = f"AND annee IN ({annees_str})"
        con.execute(f"DELETE FROM economie_filosofi WHERE annee IN ({annees_str})")
        logger.info("Suppression des millésimes %s avant rechargement.", annees_str)
    else:
        con.execute("DELETE FROM economie_filosofi")
        logger.info("Suppression de toutes les lignes Filosofi avant rechargement.")

    con.execute(f"""
        INSERT INTO economie_filosofi
            (code_commune, annee, taux_pauvrete, niveau_vie_median,
             d1_niveau_vie, d9_niveau_vie, secret)
        SELECT
            code_com::VARCHAR(5)                                          AS code_commune,
            annee,
            MAX(CASE WHEN clef_json = 'taux_de_pauvrete' THEN valeur END)::DOUBLE  AS taux_pauvrete,
            MAX(CASE WHEN clef_json = 'revenu_median'    THEN valeur END)::DOUBLE  AS niveau_vie_median,
            MAX(CASE WHEN clef_json = '1er_decile'       THEN valeur END)::DOUBLE  AS d1_niveau_vie,
            MAX(CASE WHEN clef_json = '9eme_decile'      THEN valeur END)::DOUBLE  AS d9_niveau_vie,
            (
                MAX(CASE WHEN clef_json = 'taux_de_pauvrete' THEN valeur END) IS NULL
                AND MAX(CASE WHEN clef_json = 'revenu_median' THEN valeur END) IS NULL
            )                                                              AS secret
        FROM read_parquet('{path_sql}')
        WHERE source = 'filosofi_disponible'
          AND ({filtre_hdf})
          {annees_cond}
        GROUP BY code_com, annee
        HAVING code_com IS NOT NULL
    """)

    count = con.execute("SELECT COUNT(*) FROM economie_filosofi").fetchone()[0]
    logger.info("economie_filosofi : %d lignes au total.", count)

    rows_by_year = con.execute(
        "SELECT annee, COUNT(*) FROM economie_filosofi GROUP BY annee ORDER BY annee"
    ).fetchall()
    for annee, n in rows_by_year:
        logger.info("  %d : %d communes", annee, n)

    millesimes_range = millesimes or list(range(2017, 2022))
    version = (
        f"donnees-insee-olap/filosofi_disponible {min(millesimes_range)}-{max(millesimes_range)}"
    )
    upsert_metadata(con, "economie_filosofi", count, version)
