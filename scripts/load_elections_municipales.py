"""Chargement filtré des résultats municipaux (HdF, 2008-2026).

Usage :
    uv run python scripts/load_elections_municipales.py

Filtre :
- Région Hauts-de-France (code_region = '32'), 5 départements : 02, 59, 60, 62, 80
- Municipales uniquement : type_scrutin = 'muni' dans la table elections
- 8 scrutins : 2008, 2014, 2020, 2026 (t1 + t2)

Granularité : bureau de vote (granularité fine de la source).
Idempotent : DELETE + INSERT sur les municipales uniquement, sans toucher
aux présidentielles, législatives ni autres scrutins.

Mapping Parquet (ATTENTION nommage inversé dans la source) :
- 'general-results.parquet'   → résultats par liste → resultats_candidats
- 'candidats-results.parquet' → participation       → resultats_participation

Spécificités municipales :
- Pas de code_circo (NULL pour tous les BV)
- nom/prenom = NULL (scrutin de liste, pas de candidat individuel)
- prenom_tete_liste absent du Parquet → NULL
- Colonnes liste/libelle_abrege_liste/libelle_etendu_liste/nom_tete_liste : lecture directe
- 2020_muni_t2 : date 28 juin 2020 (reporté COVID, pas 22 mars)
- 2008 : 164 communes HdF nuancées (seuil ≥ 3 500 hab — normal, pas un bug)
- 2026 : ~320 communes HdF nuancées (seuil ≥ 3 500 hab), ~3 459 avec nuance NULL

Nuances harmonisées (liste _NUANCES_MUNI définie dans etl/schema_elections.py) :
- Remplacement ciblé (DELETE années muni + INSERT, populate_nuances_municipales) :
  une correction de bloc dans le code est appliquée à la relance du loader
- 77 entrées insérées (2008 : 12, 2014 : 17, 2020 : 23, 2026 : 25), ADR-0010
- 2020 / 2026 : grilles officielles de blocs (INTA1931378J, INTP2602966C, annexes 3)
- SANS mapping (bloc NULL, UI : Non classé / Liste sortante) : NC, LMAJ, LNC
- LFI 2020 = GAU ; LFI 2026 = EXG (bascule structurante INTP2602966C + CE 512694)
- LCMD 2008 = GAU (classement D3.2 conservé, vérification en attente — ADR-0010)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ministere_de_l_info.config import get_settings  # noqa: E402
from ministere_de_l_info.etl._common import open_connection  # noqa: E402
from ministere_de_l_info.etl.schema_elections import (  # noqa: E402
    _NUANCES_MUNI,
    populate_nuances_municipales,
)
from ministere_de_l_info.logging_config import configure_logging  # noqa: E402

configure_logging()
logger = logging.getLogger(__name__)

_DB_PATH = get_settings().db_path
_PARQUET_CANDIDATS = ROOT / "data" / "exploration" / "general-results.parquet"
_PARQUET_PARTICIPATION = ROOT / "data" / "exploration" / "candidats-results.parquet"

_MUNI_FILTER = "type_scrutin = 'muni'"
_MUNI_IDS = f"(SELECT id_election FROM elections WHERE {_MUNI_FILTER})"

# 77 nuances municipales : source unique dans etl/schema_elections.py (correctif C2, ADR-0010)
assert len(_NUANCES_MUNI) == 77, f"_NUANCES_MUNI : {len(_NUANCES_MUNI)} entrées (attendu 77)"


def _delete_municipales(con) -> None:
    """Supprime les lignes municipales existantes (idempotence)."""
    con.execute(f"DELETE FROM resultats_participation WHERE id_election IN {_MUNI_IDS}")
    con.execute(f"DELETE FROM resultats_candidats WHERE id_election IN {_MUNI_IDS}")
    logger.info("Nettoyage idempotent : municipales supprimées avant rechargement")


def _load_participation(con) -> int:
    """Charge resultats_participation depuis candidats-results.parquet (HdF, muni).

    code_circo = NULL pour toutes les municipales (pas de circonscription).
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
            NULL AS code_circo
        FROM '{parquet}' p
        INNER JOIN geographies_communes gc ON gc.code_insee = p.code_commune
        WHERE gc.code_region = '32'
          AND p.id_election IN {_MUNI_IDS}
    """)
    n = con.execute(
        f"SELECT COUNT(*) FROM resultats_participation WHERE id_election IN {_MUNI_IDS}"
    ).fetchone()[0]
    logger.info("resultats_participation : %d lignes chargées (muni HdF)", n)
    return n


def _load_candidats(con) -> int:
    """Charge resultats_candidats depuis general-results.parquet (HdF, muni).

    Colonnes spécifiques muni :
    - liste, libelle_abrege_liste, libelle_etendu_liste, nom_tete_liste : lecture directe Parquet
    - prenom_tete_liste : absent du Parquet → NULL
    - nom, prenom : NULL (scrutin de liste, pas de candidat individuel)

    Cas 2008 : no_panneau = NULL pour toutes les lignes dans le Parquet source.
    Résolution : ROW_NUMBER() OVER (PARTITION BY id_election, dpt, commune, bv
    ORDER BY nuance, voix DESC) comme numéro synthétique.
    Ces numéros sont arbitraires mais stables au sein d'un rechargement donné.
    """
    parquet = str(_PARQUET_CANDIDATS)
    con.execute(f"""
        INSERT INTO resultats_candidats
            (id_election, code_departement, code_commune, code_bv,
             no_panneau, nuance, sexe, nom, prenom, voix,
             liste, libelle_abrege_liste, libelle_etendu_liste,
             nom_tete_liste, prenom_tete_liste)
        SELECT
            c.id_election,
            c.code_departement,
            c.code_commune,
            c.code_bv,
            COALESCE(
                c.no_panneau,
                CAST(ROW_NUMBER() OVER (
                    PARTITION BY c.id_election, c.code_departement, c.code_commune, c.code_bv
                    ORDER BY c.nuance, c.voix DESC
                ) AS INTEGER)
            ) AS no_panneau,
            c.nuance,
            c.sexe,
            NULL AS nom,
            NULL AS prenom,
            c.voix,
            c.liste,
            c.libelle_abrege_liste,
            c.libelle_etendu_liste,
            c.nom_tete_liste,
            NULL AS prenom_tete_liste
        FROM '{parquet}' c
        INNER JOIN geographies_communes gc ON gc.code_insee = c.code_commune
        WHERE gc.code_region = '32'
          AND c.id_election IN {_MUNI_IDS}
    """)
    n = con.execute(
        f"SELECT COUNT(*) FROM resultats_candidats WHERE id_election IN {_MUNI_IDS}"
    ).fetchone()[0]
    logger.info("resultats_candidats : %d lignes chargées (muni HdF)", n)
    return n


def _print_summary(con) -> None:
    """Affiche volumes par scrutin + vérifications clés."""
    rows = con.execute("""
        SELECT
            e.id_election,
            (SELECT COUNT(*) FROM resultats_participation rp WHERE rp.id_election = e.id_election) AS n_bv,
            (SELECT COUNT(DISTINCT rp.code_commune) FROM resultats_participation rp
              WHERE rp.id_election = e.id_election) AS n_communes,
            (SELECT COUNT(*) FROM resultats_candidats rc WHERE rc.id_election = e.id_election) AS n_listes
        FROM elections e
        WHERE e.type_scrutin = 'muni'
        ORDER BY e.id_election
    """).fetchall()

    print("\n── Résumé par scrutin (municipales HdF) ──────────────────────────────────")
    print(f"  {'id_election':<17s} {'BV':>7s} {'communes':>9s} {'listes':>8s}")
    for idel, n_bv, n_com, n_list in rows:
        print(f"  {idel:<17s} {n_bv:>7,} {n_com:>9,} {n_list:>8,}")
    print("──────────────────────────────────────────────────────────────────────────")

    # Vérification LFI bascule
    lfi_rows = con.execute(
        "SELECT nuance, annee, bloc FROM nuances_harmonisees WHERE nuance='LFI' ORDER BY annee"
    ).fetchall()
    print("\n── Vérification LFI bascule ──────────────────────────────────────────────")
    for r in lfi_rows:
        print(f"  LFI {r[1]} → {r[2]}")
    print("──────────────────────────────────────────────────────────────────────────")

    # Vérification codes sans mapping
    absent_ok = []
    for code in ("NC", "LMAJ", "LNC"):
        n = con.execute(
            "SELECT COUNT(*) FROM nuances_harmonisees WHERE nuance = ? AND annee IN (2008,2014,2020,2026)",
            [code],
        ).fetchone()[0]
        absent_ok.append((code, n))
    print("\n── Codes sans mapping (attendu 0 entrée) ─────────────────────────────────")
    for code, n in absent_ok:
        status = "✓ absent" if n == 0 else f"✗ ERREUR {n} entrées"
        print(f"  {code:<6s} : {status}")
    print("──────────────────────────────────────────────────────────────────────────")

    # Total nuances_harmonisees
    n_total = con.execute("SELECT COUNT(*) FROM nuances_harmonisees").fetchone()[0]
    n_muni = con.execute(
        "SELECT COUNT(*) FROM nuances_harmonisees WHERE annee IN (2008,2014,2020,2026)"
    ).fetchone()[0]
    print(f"\n  nuances_harmonisees total : {n_total} (dont {n_muni} municipales)")


def main() -> None:
    for p in (_PARQUET_PARTICIPATION, _PARQUET_CANDIDATS):
        if not p.exists():
            logger.error("Parquet manquant : %s", p)
            sys.exit(1)

    logger.info("Chargement municipales HdF → %s", _DB_PATH)
    con = open_connection(_DB_PATH)
    try:
        _delete_municipales(con)
        populate_nuances_municipales(con)
        _load_participation(con)
        _load_candidats(con)
        _print_summary(con)
        print("\nChargement municipales terminé.")
    finally:
        con.close()


if __name__ == "__main__":
    main()
