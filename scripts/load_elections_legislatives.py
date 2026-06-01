"""Chargement filtré des résultats législatifs (HdF, 2002-2024).

Usage :
    uv run python scripts/load_elections_legislatives.py

Filtre :
- Région Hauts-de-France (code_region = '32'), 5 départements : 02, 59, 60, 62, 80
- Législatives uniquement : type_scrutin = 'legi' dans la table elections
- 12 scrutins : 2002, 2007, 2012, 2017, 2022, 2024 (t1 + t2)

Granularité : bureau de vote (granularité fine de la source).
Idempotent : DELETE + INSERT sur les législatives uniquement, sans toucher
aux présidentielles ni aux autres scrutins éventuellement présents.

Mapping Parquet (ATTENTION nommage inversé dans la source) :
- 'general-results.parquet'   → résultats par candidat → resultats_candidats
- 'candidats-results.parquet' → participation          → resultats_participation

Reconstruction de code_circo (clé circonscription "DPT-NN") :
- 2012 / 2017 / 2022 : direct depuis le Parquet participation
  (code_departement || '-' || LPAD(code_circonscription, 2, '0'))
- 2002 / 2007 / 2024 : code_circonscription NULL dans la source → jointure spatiale
  (centroïde de la commune ∈ polygone de circonscription, geographies_circonscriptions).
  NB : pour 2002/2007 le découpage de la source est l'ancien (pré-Marleix 2010) ;
  l'assignation au découpage actuel est une approximation (flag ancien_decoupage=TRUE).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ministere_de_l_info.etl._common import open_connection  # noqa: E402
from ministere_de_l_info.logging_config import configure_logging  # noqa: E402

configure_logging()
logger = logging.getLogger(__name__)

_DB_PATH = ROOT / "data" / "ministere.duckdb"
_PARQUET_CANDIDATS = ROOT / "data" / "exploration" / "general-results.parquet"
_PARQUET_PARTICIPATION = ROOT / "data" / "exploration" / "candidats-results.parquet"

# Départements de la région Hauts-de-France
_HDF_DEPTS = ("02", "59", "60", "62", "80")
_HDF_DEPTS_SQL = ", ".join(f"'{d}'" for d in _HDF_DEPTS)

# Filtre commun : législatives via sous-requête sur la table elections
_LEGI_FILTER = "type_scrutin = 'legi'"
_LEGI_IDS = f"(SELECT id_election FROM elections WHERE {_LEGI_FILTER})"

# Scrutins dont le code_circo doit être reconstruit par jointure spatiale
_SPATIAL_IDS = (
    "2002_legi_t1",
    "2002_legi_t2",
    "2007_legi_t1",
    "2007_legi_t2",
    "2024_legi_t1",
    "2024_legi_t2",
)
_SPATIAL_IDS_SQL = ", ".join(f"'{i}'" for i in _SPATIAL_IDS)


def _delete_legislatives(con) -> None:
    """Supprime les lignes législatives existantes (idempotence)."""
    con.execute(f"DELETE FROM resultats_participation WHERE id_election IN {_LEGI_IDS}")
    con.execute(f"DELETE FROM resultats_candidats WHERE id_election IN {_LEGI_IDS}")
    logger.info("Nettoyage idempotent : législatives supprimées avant rechargement")


def _load_participation(con) -> int:
    """Charge resultats_participation depuis candidats-results.parquet (HdF, legi).

    code_circo direct pour 2012/2017/2022 (code_circonscription présent),
    NULL pour 2002/2007/2024 (rempli ensuite par jointure spatiale).
    """
    parquet = str(_PARQUET_PARTICIPATION)
    con.execute(f"""
        INSERT INTO resultats_participation
            (id_election, code_departement, code_commune, code_bv,
             inscrits, abstentions, votants, blancs, nuls, exprimes, code_circo)
        SELECT
            p.id_election,
            p.code_departement,
            p.code_commune,
            p.code_bv,
            p.inscrits,
            p.abstentions,
            p.votants,
            p.blancs,
            p.nuls,
            p.exprimes,
            CASE
                WHEN p.code_circonscription IS NOT NULL
                THEN p.code_departement || '-' || LPAD(p.code_circonscription, 2, '0')
                ELSE NULL
            END AS code_circo
        FROM '{parquet}' p
        INNER JOIN geographies_communes gc ON gc.code_insee = p.code_commune
        WHERE gc.code_region = '32'
          AND p.id_election IN {_LEGI_IDS}
    """)
    n = con.execute(
        f"SELECT COUNT(*) FROM resultats_participation WHERE id_election IN {_LEGI_IDS}"
    ).fetchone()[0]
    logger.info("resultats_participation : %d lignes chargées", n)
    return n


def _reconstruct_code_circo_spatial(con) -> None:
    """Reconstruit code_circo par jointure spatiale (2002/2007/2024).

    Centroïde de la commune ∈ polygone de circonscription. Une commune → une circo
    (celle qui contient son centroïde). Les communes coupées entre plusieurs circos
    sont assignées à la circo de leur centroïde (approximation documentée).
    """
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE _commune_circo_hdf AS
        SELECT gc.code_insee AS code_commune, circ.code AS code_circo
        FROM geographies_communes gc
        JOIN geographies_circonscriptions circ
          ON ST_Within(ST_Centroid(gc.geometry), circ.geometry)
         AND circ.code_departement IN ({_HDF_DEPTS_SQL})
        WHERE gc.code_region = '32'
    """)
    n_map = con.execute("SELECT COUNT(*) FROM _commune_circo_hdf").fetchone()[0]
    logger.info("Table d'assignation commune→circo (centroïde) : %d communes HdF", n_map)

    con.execute(f"""
        UPDATE resultats_participation rp
        SET code_circo = m.code_circo
        FROM _commune_circo_hdf m
        WHERE rp.code_commune = m.code_commune
          AND rp.code_circo IS NULL
          AND rp.id_election IN ({_SPATIAL_IDS_SQL})
    """)
    logger.info("code_circo reconstruit par jointure spatiale (2002/2007/2024)")


def _load_candidats(con) -> int:
    """Charge resultats_candidats depuis general-results.parquet (HdF, legi)."""
    parquet = str(_PARQUET_CANDIDATS)
    con.execute(f"""
        INSERT INTO resultats_candidats
            (id_election, code_departement, code_commune, code_bv,
             no_panneau, nuance, sexe, nom, prenom, voix)
        SELECT
            c.id_election,
            c.code_departement,
            c.code_commune,
            c.code_bv,
            c.no_panneau,
            c.nuance,
            c.sexe,
            c.nom,
            c.prenom,
            c.voix
        FROM '{parquet}' c
        INNER JOIN geographies_communes gc ON gc.code_insee = c.code_commune
        WHERE gc.code_region = '32'
          AND c.id_election IN {_LEGI_IDS}
    """)
    n = con.execute(
        f"SELECT COUNT(*) FROM resultats_candidats WHERE id_election IN {_LEGI_IDS}"
    ).fetchone()[0]
    logger.info("resultats_candidats : %d lignes chargées", n)
    return n


def _print_summary(con) -> None:
    """Affiche volumes + couverture code_circo par scrutin."""
    rows = con.execute("""
        SELECT
            e.id_election,
            e.ancien_decoupage,
            (SELECT COUNT(*) FROM resultats_participation rp WHERE rp.id_election = e.id_election) AS n_bv,
            (SELECT COUNT(*) FROM resultats_participation rp
              WHERE rp.id_election = e.id_election AND rp.code_circo IS NOT NULL) AS n_circo_ok,
            (SELECT COUNT(DISTINCT rp.code_circo) FROM resultats_participation rp
              WHERE rp.id_election = e.id_election) AS n_circo_distinct,
            (SELECT COUNT(*) FROM resultats_candidats rc WHERE rc.id_election = e.id_election) AS n_cand
        FROM elections e
        WHERE e.type_scrutin = 'legi'
        ORDER BY e.id_election
    """).fetchall()

    print("\n── Résumé par scrutin (législatives HdF) ─────────────────────────────────")
    print(
        f"  {'id_election':<15s} {'anc.':>4s} {'BV':>7s} {'circo_ok%':>10s} {'n_circo':>8s} {'cand':>8s}"
    )
    for r in rows:
        idel, anc, n_bv, n_ok, n_dist, n_cand = r
        pct = (100.0 * n_ok / n_bv) if n_bv else 0.0
        flag = "oui" if anc else "—"
        print(f"  {idel:<15s} {flag:>4s} {n_bv:>7,} {pct:>9.1f}% {n_dist:>8,} {n_cand:>8,}")
    print("──────────────────────────────────────────────────────────────────────────")

    # Communes coupées : BV d'une même commune répartis sur >1 circo (mesure réelle
    # sur les scrutins à code_circonscription natif 2012/2017/2022).
    coupees = con.execute("""
        WITH par_commune AS (
            SELECT id_election, code_commune, COUNT(DISTINCT code_circo) AS n_circo
            FROM resultats_participation
            WHERE id_election IN ('2012_legi_t1','2017_legi_t1','2022_legi_t1')
              AND code_circo IS NOT NULL
            GROUP BY id_election, code_commune
        )
        SELECT id_election,
               SUM(CASE WHEN n_circo > 1 THEN 1 ELSE 0 END) AS communes_coupees,
               COUNT(*) AS communes_total
        FROM par_commune GROUP BY id_election ORDER BY id_election
    """).fetchall()
    print("\n── Communes coupées entre circos (source native, t1) ─────────────────────")
    for idel, coup, tot in coupees:
        print(f"  {idel:<15s} {coup:>4,} / {tot:,} communes réparties sur >1 circo")
    print("──────────────────────────────────────────────────────────────────────────")


def main() -> None:
    for p in (_PARQUET_PARTICIPATION, _PARQUET_CANDIDATS):
        if not p.exists():
            logger.error("Parquet manquant : %s", p)
            sys.exit(1)

    logger.info("Chargement législatives HdF → %s", _DB_PATH)
    con = open_connection(_DB_PATH)
    try:
        _delete_legislatives(con)
        _load_participation(con)
        _reconstruct_code_circo_spatial(con)
        _load_candidats(con)
        _print_summary(con)
        print("Chargement législatives terminé.")
    finally:
        con.close()


if __name__ == "__main__":
    main()
