"""Loader RP — emploi, chômage déclaratif, CSP et logements par commune HdF.

Source : INSEE Recensement de la Population via dataset data.gouv.fr 67289477639527408ae687da
  "Recensement de la population communal et Filosofi depuis 2015"
  URL Parquet : voir _PARQUET_URL dans scripts/load_economie.py

Format source : long (OLAP) — colonnes : code_com, nom_commune, annee, source, clef_json, valeur
Sources RP : source IN ('rp_actifs_emploi', 'rp_logements'), millésimes 2015-2021

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
  part_logements_sociaux  = nb_rp_hlm_p / residences_principales_p * 100
                            (source rp_logements — HLM parmi résidences principales)
  nb_logements_sociaux    = nb_rp_hlm_p (effectif absolu HLM)
  pop_active              = actifs_15_64_ans_c (effectif absolu)

Secret statistique : valeur = NULL dans le Parquet (masquée par INSEE).
  ``secret = TRUE`` seulement si le nombre de chômeurs est NULL pour la commune alors que
  le millésime le diffuse pour d'autres communes. Si la clef est absente (ou NULL partout)
  pour un millésime entier, l'indicateur est « non diffusé » pour ce millésime : taux NULL,
  ``secret = FALSE`` et WARNING (correctif 2026-09-25 : RP 2015 et 2016 étaient marqués
  secrets à 100 %, ce qui masquait aussi les autres indicateurs RP de ces millésimes).
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from ministere_de_l_info.etl._common import upsert_metadata

logger = logging.getLogger(__name__)

_DEPTS_HDF = ("02", "59", "60", "62", "80")

# Clefs OLAP nécessaires au calcul des indicateurs (source rp_actifs_emploi / rp_logements).
CLEFS_REQUISES: dict[str, tuple[str, ...]] = {
    "tx_chomage_dec": ("chomeurs_15_64_ans_p", "actifs_15_64_ans_p"),
    "part_ouvriers_employes": (
        "actifs_15_64_ans_c",
        "actifs_ouvriers_15_64_ans_c",
        "actifs_employes_15_64_ans_c",
    ),
    "part_emploi_industriel": (
        "emplois_au_lieu_travail_c",
        "emplois_au_lieu_travail_industrie_c",
    ),
    "part_logements_sociaux": ("nb_rp_hlm_p", "residences_principales_p"),
}


def diagnostiquer_clefs(
    con: duckdb.DuckDBPyConnection, path_sql: str, filtre_sql: str
) -> dict[int, list[str]]:
    """Clefs requises sans aucune valeur non NULL, par millésime (WARNING si manquantes).

    ``filtre_sql`` : condition SQL complète (filtre HdF, éventuellement millésimes).

    Pour chaque millésime incomplet, les clefs disponibles contenant « chom » sont
    journalisées : une clef renommée par la source se repère ainsi dans le log.
    """
    clefs = sorted({c for cs in CLEFS_REQUISES.values() for c in cs})
    liste = ", ".join(f"'{c}'" for c in clefs)
    rows = con.execute(f"""
        SELECT annee, clef_json, COUNT(valeur) AS n
        FROM read_parquet('{path_sql}')
        WHERE source IN ('rp_actifs_emploi', 'rp_logements')
          AND {filtre_sql}
          AND (clef_json IN ({liste}) OR clef_json ILIKE '%chom%')
        GROUP BY annee, clef_json
    """).fetchall()
    presentes: dict[int, set[str]] = {}
    chom: dict[int, list[str]] = {}
    for annee, clef, n in rows:
        presentes.setdefault(int(annee), set())
        if n > 0:
            presentes[int(annee)].add(str(clef))
            if "chom" in str(clef):
                chom.setdefault(int(annee), []).append(str(clef))
    manquantes: dict[int, list[str]] = {}
    for annee in sorted(presentes):
        absentes = [c for c in clefs if c not in presentes[annee]]
        if not absentes:
            continue
        manquantes[annee] = absentes
        indicateurs = sorted(i for i, cs in CLEFS_REQUISES.items() if set(cs) & set(absentes))
        logger.warning(
            "RP %d : clef(s) sans valeur %s → indicateur(s) non diffusé(s) %s "
            "(NULL, non secret). Clefs « chom » disponibles : %s",
            annee,
            absentes,
            indicateurs,
            sorted(chom.get(annee, [])) or "aucune",
        )
    return manquantes


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

    diagnostiquer_clefs(con, path_sql, f"({filtre_hdf}) {annees_cond}")

    con.execute(f"""
        INSERT INTO economie_rp
            (code_commune, annee_millesime, tx_chomage_dec,
             part_ouvriers_employes, part_emploi_industriel,
             part_logements_sociaux, nb_logements_sociaux,
             pop_active, secret)
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

            -- Part logements sociaux (HLM / résidences principales)
            CASE
                WHEN MAX(CASE WHEN source = 'rp_logements' AND clef_json = 'residences_principales_p' THEN valeur END) > 0
                THEN (
                    MAX(CASE WHEN source = 'rp_logements' AND clef_json = 'nb_rp_hlm_p' THEN valeur END) /
                    MAX(CASE WHEN source = 'rp_logements' AND clef_json = 'residences_principales_p' THEN valeur END) * 100.0
                )::DOUBLE
                ELSE NULL
            END AS part_logements_sociaux,

            MAX(CASE WHEN source = 'rp_logements' AND clef_json = 'nb_rp_hlm_p' THEN valeur END)::INTEGER
                AS nb_logements_sociaux,

            MAX(CASE WHEN clef_json = 'actifs_15_64_ans_c' THEN valeur END)::INTEGER AS pop_active,

            -- Secret : valeur NULL pour la commune alors que le millésime diffuse la clef
            -- ailleurs (une clef absente du millésime entier n'est pas un secret).
            (
                MAX(CASE WHEN clef_json = 'chomeurs_15_64_ans_p' THEN valeur END) IS NULL
                AND SUM(COUNT(CASE WHEN clef_json = 'chomeurs_15_64_ans_p' THEN valeur END))
                    OVER (PARTITION BY annee) > 0
            ) AS secret

        FROM read_parquet('{path_sql}')
        WHERE source IN ('rp_actifs_emploi', 'rp_logements')
          AND ({filtre_hdf})
          {annees_cond}
        GROUP BY code_com, annee
        HAVING code_com IS NOT NULL
    """)

    count = con.execute("SELECT COUNT(*) FROM economie_rp").fetchone()[0]
    logger.info("economie_rp : %d lignes au total.", count)

    rows_by_year = con.execute(
        "SELECT annee_millesime, COUNT(*), COUNT(tx_chomage_dec), "
        "COUNT(*) FILTER (WHERE secret) FROM economie_rp "
        "GROUP BY annee_millesime ORDER BY annee_millesime"
    ).fetchall()
    for annee, n, n_chomage, n_secret in rows_by_year:
        logger.info(
            "  %d : %d communes (%d taux de chômage, %d secrets)", annee, n, n_chomage, n_secret
        )

    millesimes_range = millesimes or list(range(2015, 2022))
    version = f"donnees-insee-olap/rp_actifs_emploi+rp_logements {min(millesimes_range)}-{max(millesimes_range)}"
    upsert_metadata(con, "economie_rp", count, version)
