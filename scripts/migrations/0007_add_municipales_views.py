"""Migration 0007 — Création des 3 vues d'agrégation municipales.

Vues créées (CREATE OR REPLACE, idempotent) :
- v_scores_commune_muni  : voix par (annee, tour, commune, bloc)
- v_evolution_blocs_hdf_muni : agrégation HdF par scrutin × bloc
- v_listes_commune_muni  : détail liste par liste (clé drill-down D3.3)

Toutes les vues utilisent LEFT JOIN sur nuances_harmonisees : les nuances sans
mapping (NC, LMAJ, LNC) produisent bloc = NULL, agrégées sous "Non classé" dans
l'UI. pct_exprimes calculé sur le total exprimés de la commune ou du HdF selon
la vue, via jointure sur resultats_participation.

Usage :
    uv run python scripts/migrations/0007_add_municipales_views.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ministere_de_l_info.etl._common import open_connection  # noqa: E402
from ministere_de_l_info.logging_config import configure_logging  # noqa: E402

configure_logging()
logger = logging.getLogger(__name__)

_DB_PATH = ROOT / "data" / "ministere.duckdb"


def _create_v_scores_commune_muni(con) -> None:
    """Voix agrégés par bloc et commune — 1 ligne par (annee, tour, commune, bloc).

    bloc = NULL pour les nuances sans mapping (NC, LMAJ, LNC, nuance=NULL).
    pct_exprimes = NULL quand bloc IS NULL : les communes plurinominales (< 1000 hab)
    ont une sémantique voix candidat (non additive), ce qui rendrait le % faux.
    Pour les blocs nommés (scrutin de liste ≥ seuil), pct = voix / exprimes_commune.
    """
    con.execute("""
        CREATE OR REPLACE VIEW v_scores_commune_muni AS
        WITH exprimes_commune AS (
            SELECT rp.id_election, rp.code_commune, SUM(rp.exprimes) AS exprimes
            FROM resultats_participation rp
            JOIN elections e ON e.id_election = rp.id_election
            WHERE e.type_scrutin = 'muni'
            GROUP BY rp.id_election, rp.code_commune
        )
        SELECT
            e.annee,
            e.tour,
            rc.code_commune,
            nh.bloc,
            SUM(rc.voix)                                                          AS voix,
            CASE WHEN nh.bloc IS NOT NULL
                 THEN ROUND(100.0 * SUM(rc.voix) / NULLIF(MAX(ex.exprimes), 0), 2)
                 ELSE NULL END                                                    AS pct_exprimes
        FROM resultats_candidats rc
        JOIN elections e
            ON e.id_election = rc.id_election
        LEFT JOIN nuances_harmonisees nh
            ON nh.nuance = rc.nuance AND nh.annee = e.annee
        JOIN exprimes_commune ex
            ON ex.id_election = rc.id_election AND ex.code_commune = rc.code_commune
        WHERE e.type_scrutin = 'muni'
        GROUP BY e.annee, e.tour, rc.code_commune, nh.bloc
    """)
    logger.info("Vue v_scores_commune_muni créée/mise à jour")


def _create_v_evolution_blocs_hdf_muni(con) -> None:
    """Évolution temporelle des blocs sur l'ensemble HdF.

    1 ligne par (annee, tour, bloc). voix = SUM(rc.voix) par bloc.
    pct_exprimes = voix_bloc / exprimes_HdF * 100, SEULEMENT pour les blocs nommés.
    Pour bloc=NULL (NC/plurinominal), pct_exprimes=NULL : les communes < 1000 hab
    ont un scrutin plurinominal (voix candidat ≠ voix liste), ce qui rend le %
    non comparable avec les blocs politiques des communes ≥ seuil.
    """
    con.execute("""
        CREATE OR REPLACE VIEW v_evolution_blocs_hdf_muni AS
        WITH exprimes_hdf AS (
            SELECT rp.id_election, SUM(rp.exprimes) AS exprimes
            FROM resultats_participation rp
            JOIN elections e ON e.id_election = rp.id_election
            WHERE e.type_scrutin = 'muni'
            GROUP BY rp.id_election
        ),
        blocs_hdf AS (
            SELECT
                e.id_election,
                e.annee,
                e.tour,
                nh.bloc,
                SUM(rc.voix) AS voix
            FROM resultats_candidats rc
            JOIN elections e
                ON e.id_election = rc.id_election
            LEFT JOIN nuances_harmonisees nh
                ON nh.nuance = rc.nuance AND nh.annee = e.annee
            WHERE e.type_scrutin = 'muni'
            GROUP BY e.id_election, e.annee, e.tour, nh.bloc
        )
        SELECT
            bh.annee,
            bh.tour,
            bh.bloc,
            bh.voix,
            CASE WHEN bh.bloc IS NOT NULL
                 THEN ROUND(100.0 * bh.voix / NULLIF(ex.exprimes, 0), 2)
                 ELSE NULL END AS pct_exprimes
        FROM blocs_hdf bh
        JOIN exprimes_hdf ex ON ex.id_election = bh.id_election
        ORDER BY bh.annee, bh.tour, bh.bloc
    """)
    logger.info("Vue v_evolution_blocs_hdf_muni créée/mise à jour")


def _create_v_listes_commune_muni(con) -> None:
    """Détail liste par liste par commune — clé pour le drill-down D3.3.

    1 ligne par (annee, tour, commune, nuance). Conserve les métadonnées liste
    (libelle_abrege_liste, libelle_etendu_liste, nom_tete_liste, prenom_tete_liste).
    bloc = NULL pour nuances sans mapping (NC, LMAJ, LNC).
    pct_exprimes = voix_liste / exprimes_commune * 100.
    """
    con.execute("""
        CREATE OR REPLACE VIEW v_listes_commune_muni AS
        WITH exprimes_commune AS (
            SELECT rp.id_election, rp.code_commune, SUM(rp.exprimes) AS exprimes
            FROM resultats_participation rp
            JOIN elections e ON e.id_election = rp.id_election
            WHERE e.type_scrutin = 'muni'
            GROUP BY rp.id_election, rp.code_commune
        )
        SELECT
            e.annee,
            e.tour,
            rc.code_commune,
            rc.nuance,
            nh.bloc,
            MAX(rc.libelle_abrege_liste) AS libelle_abrege_liste,
            MAX(rc.libelle_etendu_liste) AS libelle_etendu_liste,
            MAX(rc.nom_tete_liste)       AS nom_tete_liste,
            MAX(rc.prenom_tete_liste)    AS prenom_tete_liste,
            SUM(rc.voix)                 AS voix,
            CASE WHEN nh.bloc IS NOT NULL
                 THEN ROUND(100.0 * SUM(rc.voix) / NULLIF(MAX(ex.exprimes), 0), 2)
                 ELSE NULL END           AS pct_exprimes
        FROM resultats_candidats rc
        JOIN elections e
            ON e.id_election = rc.id_election
        LEFT JOIN nuances_harmonisees nh
            ON nh.nuance = rc.nuance AND nh.annee = e.annee
        JOIN exprimes_commune ex
            ON ex.id_election = rc.id_election AND ex.code_commune = rc.code_commune
        WHERE e.type_scrutin = 'muni'
        GROUP BY e.annee, e.tour, rc.code_commune, rc.nuance, nh.bloc
    """)
    logger.info("Vue v_listes_commune_muni créée/mise à jour")


def main() -> None:
    if not _DB_PATH.exists():
        logger.error("Base introuvable : %s", _DB_PATH)
        sys.exit(1)

    logger.info("Migration 0007 → %s", _DB_PATH)
    con = open_connection(_DB_PATH)
    try:
        _create_v_scores_commune_muni(con)
        _create_v_evolution_blocs_hdf_muni(con)
        _create_v_listes_commune_muni(con)

        # Vérification rapide : les 3 vues retournent des lignes
        checks = [
            ("v_scores_commune_muni", "SELECT COUNT(*) FROM v_scores_commune_muni"),
            ("v_evolution_blocs_hdf_muni", "SELECT COUNT(*) FROM v_evolution_blocs_hdf_muni"),
            ("v_listes_commune_muni", "SELECT COUNT(*) FROM v_listes_commune_muni"),
        ]
        print("\n── Migration 0007 — vérification vues ────────────────────────────────────")
        for name, sql in checks:
            n = con.execute(sql).fetchone()[0]
            status = "✓" if n > 0 else "✗ VIDE"
            print(f"  {name:<35s} {n:>8,} lignes  {status}")
        print("──────────────────────────────────────────────────────────────────────────\n")
        print("Migration 0007 appliquée.")

    finally:
        con.close()


if __name__ == "__main__":
    main()
