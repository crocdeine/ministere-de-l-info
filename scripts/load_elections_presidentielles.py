"""Chargement filtré des résultats présidentiels (HdF, 2002-2022).

Usage :
    uv run python scripts/load_elections_presidentielles.py

Filtre :
- Région Hauts-de-France (code_region = '32'), 5 départements : 02, 59, 60, 62, 80 ;
  `--perimetre france` : toutes les communes de geographies_communes (vague B)
- Présidentielles uniquement : type_scrutin = 'pres' dans la table elections
- Années 2002, 2007, 2012, 2017, 2022 (t1 + t2)

Granularité : bureau de vote (granularité fine de la source).
Idempotent : DELETE + INSERT sur les présidentielles uniquement, sans toucher
aux autres scrutins éventuellement présents dans la DB.

Mapping Parquet (ATTENTION nommage inversé dans la source) :
- 'general-results.parquet'   → résultats par candidat → resultats_candidats
- 'candidats-results.parquet' → participation          → resultats_participation
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ministere_de_l_info.config import get_settings  # noqa: E402
from ministere_de_l_info.etl._common import open_connection  # noqa: E402
from ministere_de_l_info.etl.loaders.elections_agregees import (  # noqa: E402
    PERIMETRES,
    code_departement_sql,
    controler_chargement,
    filtre_perimetre,
    preparer_rattachement,
    source_rattachee_sql,
    transaction,
    verifier_unicite_resultats,
)
from ministere_de_l_info.logging_config import configure_logging  # noqa: E402

configure_logging()
logger = logging.getLogger(__name__)

_DB_PATH = get_settings().db_path
_PARQUET_CANDIDATS = ROOT / "data" / "exploration" / "general-results.parquet"
_PARQUET_PARTICIPATION = ROOT / "data" / "exploration" / "candidats-results.parquet"

# Filtre commun : présidentielles HdF via sous-requête sur la table elections
_PRES_FILTER = "type_scrutin = 'pres'"


def _delete_presidentielles(con) -> None:
    """Supprime les lignes présidentielles existantes (idempotence)."""
    con.execute(
        "DELETE FROM resultats_participation WHERE id_election IN "
        "(SELECT id_election FROM elections WHERE type_scrutin = 'pres')"
    )
    con.execute(
        "DELETE FROM resultats_candidats WHERE id_election IN "
        "(SELECT id_election FROM elections WHERE type_scrutin = 'pres')"
    )
    logger.info("Nettoyage idempotent : présidentielles supprimées avant rechargement")


def _load_participation(con, perimetre: str) -> int:
    """Charge resultats_participation depuis candidats-results.parquet (HdF, pres)."""
    parquet = str(_PARQUET_PARTICIPATION)
    con.execute(f"""
        INSERT INTO resultats_participation
            (id_election, code_departement, code_commune, code_bv,
             inscrits, abstentions, votants, blancs, nuls, exprimes, code_commune_origine)
        SELECT
            p.id_election,
            {code_departement_sql("p")},
            p.code_commune,
            p.code_bv,
            p.inscrits,
            p.abstentions,
            p.votants,
            p.blancs,
            p.nuls,
            p.exprimes,
            p.code_commune_origine
        FROM {source_rattachee_sql(parquet)} p
        INNER JOIN geographies_communes gc ON gc.code_insee = p.code_commune
        WHERE {filtre_perimetre(perimetre)}
          AND p.id_election IN (SELECT id_election FROM elections WHERE {_PRES_FILTER})
    """)
    n = con.execute(
        "SELECT COUNT(*) FROM resultats_participation WHERE id_election IN "
        f"(SELECT id_election FROM elections WHERE {_PRES_FILTER})"
    ).fetchone()[0]
    logger.info("resultats_participation : %d lignes chargées", n)
    return n


def _load_candidats(con, perimetre: str) -> int:
    """Charge resultats_candidats depuis general-results.parquet (HdF, pres)."""
    parquet = str(_PARQUET_CANDIDATS)
    con.execute(f"""
        INSERT INTO resultats_candidats
            (id_election, code_departement, code_commune, code_bv,
             no_panneau, nuance, sexe, nom, prenom, voix, code_commune_origine)
        SELECT
            c.id_election,
            {code_departement_sql("c")},
            c.code_commune,
            c.code_bv,
            c.no_panneau,
            c.nuance,
            c.sexe,
            c.nom,
            c.prenom,
            c.voix,
            c.code_commune_origine
        FROM {source_rattachee_sql(parquet)} c
        INNER JOIN geographies_communes gc ON gc.code_insee = c.code_commune
        WHERE {filtre_perimetre(perimetre)}
          AND c.id_election IN (SELECT id_election FROM elections WHERE {_PRES_FILTER})
    """)
    n = con.execute(
        "SELECT COUNT(*) FROM resultats_candidats WHERE id_election IN "
        f"(SELECT id_election FROM elections WHERE {_PRES_FILTER})"
    ).fetchone()[0]
    logger.info("resultats_candidats : %d lignes chargées", n)
    return n


def _print_summary(con) -> None:
    """Affiche le récapitulatif par scrutin (sous-requêtes pour éviter le produit cartésien)."""
    rows = con.execute("""
        SELECT
            e.id_election,
            (SELECT COUNT(*) FROM resultats_participation rp WHERE rp.id_election = e.id_election) AS n_bureaux,
            (SELECT COUNT(*) FROM resultats_candidats    rc WHERE rc.id_election = e.id_election) AS n_lignes_cand
        FROM elections e
        WHERE e.type_scrutin = 'pres'
        ORDER BY e.id_election
    """).fetchall()

    print("\n── Résumé par scrutin ────────────────────────────────────────")
    print(f"  {'id_election':<20s} {'bureaux':>8s}  {'lignes_cand':>12s}")
    for r in rows:
        print(f"  {r[0]:<20s} {r[1]:>8,}  {r[2]:>12,}")
    print("──────────────────────────────────────────────────────────────")


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument(
        "--perimetre",
        choices=PERIMETRES,
        default="hdf",
        help="hdf (défaut, 5 départements) ou france (toutes les communes)",
    )
    args = parser.parse_args()
    for p in (_PARQUET_PARTICIPATION, _PARQUET_CANDIDATS):
        if not p.exists():
            logger.error("Parquet manquant : %s — lancer d'abord l'exploration C1.", p)
            sys.exit(1)

    logger.info("Chargement présidentielles HdF → %s", _DB_PATH)
    con = open_connection(_DB_PATH)
    try:
        preparer_rattachement(con, args.perimetre)
        with transaction(con):
            _delete_presidentielles(con)
            _load_participation(con, args.perimetre)
            _load_candidats(con, args.perimetre)
            verifier_unicite_resultats(
                con, "(SELECT id_election FROM elections WHERE type_scrutin = 'pres')"
            )
            controler_chargement(
                con,
                _PARQUET_PARTICIPATION,
                "(SELECT id_election FROM elections WHERE type_scrutin = 'pres')",
                args.perimetre,
            )
        _print_summary(con)
        print("Chargement présidentielles terminé. Étape suivante → C2b vues.")
    finally:
        con.close()


if __name__ == "__main__":
    main()
