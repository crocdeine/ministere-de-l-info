"""Loader RP — emploi, chômage déclaratif et CSP par commune HdF.

Source : INSEE Recensement de la Population via dataset data.gouv.fr 67289477639527408ae687da
  "Recensement de la population communal et Filosofi depuis 2015"
  URL Parquet : voir _PARQUET_URL dans scripts/load_economie.py

Format source : long (OLAP) — colonnes : code_com, nom_commune, annee, source, clef_json, valeur
Source RP emploi : source = 'rp_actifs_emploi', millésimes 2015-2021

Convention suffixes INSEE RP :
  _c = effectif (count) — ex : actifs_15_64_ans_c = 118 248 pour Lille
  _p = effectif pondéré (also a count, different weighting) — NOT a percentage
  Les taux sont calculés ici à partir des effectifs _c et _p.

Indicateurs calculés :
  tx_chomage_dec          = chomeurs_15_64_ans_p  / actifs_15_64_ans_p * 100
  part_ouvriers_employes  = (actifs_ouvriers_15_64_ans_c + actifs_employes_15_64_ans_c)
                            / actifs_15_64_ans_c * 100
  part_emploi_industriel  = emplois_au_lieu_travail_industrie_c
                            / emplois_au_lieu_travail_c * 100
                            (emplois situés dans la commune, pas résidentiels)
  pop_active              = actifs_15_64_ans_c (effectif absolu)

Secret statistique : valeur = NULL dans le Parquet (masquée par INSEE).
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from ministere_de_l_info.etl._common import upsert_metadata

logger = logging.getLogger(__name__)

_DEPTS_HDF = ("02", "59", "60", "62", "80")


def load_economie_rp(
    con: duckdb.DuckDBPyConnection,
    raw_dir: Path,
    force: bool = False,
    millesimes: list[int] | None = None,
) -> None:
    """Charge les données RP emploi/CSP HdF dans economie_rp.

    Sources : INSEE Recensement de la Population via data.gouv.fr
    Granularité : commune × millésime (chaque millésime = moyenne 5 ans glissants)
    Filtre : Hauts-de-France (depts 02, 59, 60, 62, 80)
    Millésimes disponibles : 2015-2021 (dataset mis à jour novembre 2024)

    Taux de chômage : chômage déclaratif RP (seule source à granularité communale
    exhaustive — voir ADR-0006 pour les alternatives exclues).
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
        con.execute(f"DELETE FROM economie_rp WHERE annee_millesime IN ({annees_str})")
        logger.info("Suppression des millésimes %s avant rechargement.", annees_str)
    else:
        con.execute("DELETE FROM economie_rp")
        logger.info("Suppression de toutes les lignes RP avant rechargement.")

    con.execute(f"""
        INSERT INTO economie_rp
            (code_commune, annee_millesime, tx_chomage_dec,
             part_ouvriers_employes, part_emploi_industriel, pop_active, secret)
        SELECT
            code_com::VARCHAR(5)  AS code_commune,
            annee                 AS annee_millesime,

            -- Taux chômage déclaratif : chômeurs / actifs totaux * 100
            CASE
                WHEN MAX(CASE WHEN clef_json = 'actifs_15_64_ans_p' THEN valeur END) > 0
                THEN (
                    MAX(CASE WHEN clef_json = 'chomeurs_15_64_ans_p' THEN valeur END) /
                    MAX(CASE WHEN clef_json = 'actifs_15_64_ans_p'   THEN valeur END) * 100.0
                )::DOUBLE
                ELSE NULL
            END AS tx_chomage_dec,

            -- Part ouvriers + employés dans actifs 15-64 ans
            CASE
                WHEN MAX(CASE WHEN clef_json = 'actifs_15_64_ans_c' THEN valeur END) > 0
                THEN (
                    (
                        COALESCE(MAX(CASE WHEN clef_json = 'actifs_ouvriers_15_64_ans_c'  THEN valeur END), 0) +
                        COALESCE(MAX(CASE WHEN clef_json = 'actifs_employes_15_64_ans_c'  THEN valeur END), 0)
                    ) /
                    MAX(CASE WHEN clef_json = 'actifs_15_64_ans_c' THEN valeur END) * 100.0
                )::DOUBLE
                ELSE NULL
            END AS part_ouvriers_employes,

            -- Part emplois industriels au lieu de travail
            CASE
                WHEN MAX(CASE WHEN clef_json = 'emplois_au_lieu_travail_c' THEN valeur END) > 0
                THEN (
                    MAX(CASE WHEN clef_json = 'emplois_au_lieu_travail_industrie_c' THEN valeur END) /
                    MAX(CASE WHEN clef_json = 'emplois_au_lieu_travail_c'           THEN valeur END) * 100.0
                )::DOUBLE
                ELSE NULL
            END AS part_emploi_industriel,

            MAX(CASE WHEN clef_json = 'actifs_15_64_ans_c' THEN valeur END)::INTEGER AS pop_active,

            (MAX(CASE WHEN clef_json = 'chomeurs_15_64_ans_p' THEN valeur END) IS NULL) AS secret

        FROM read_parquet('{path_sql}')
        WHERE source = 'rp_actifs_emploi'
          AND ({filtre_hdf})
          {annees_cond}
        GROUP BY code_com, annee
        HAVING code_com IS NOT NULL
    """)

    count = con.execute("SELECT COUNT(*) FROM economie_rp").fetchone()[0]
    logger.info("economie_rp : %d lignes au total.", count)

    rows_by_year = con.execute(
        "SELECT annee_millesime, COUNT(*) FROM economie_rp GROUP BY annee_millesime ORDER BY annee_millesime"
    ).fetchall()
    for annee, n in rows_by_year:
        logger.info("  %d : %d communes", annee, n)

    millesimes_range = millesimes or list(range(2015, 2022))
    version = f"donnees-insee-olap/rp_actifs_emploi {min(millesimes_range)}-{max(millesimes_range)}"
    upsert_metadata(con, "economie_rp", count, version)
