"""Chargement des Parquet « Données des élections agrégées » (data.gouv.fr).

Partagé par les scripts `scripts/load_elections_*.py`.

Nommage inversé de la source (gotcha n° 8) :
- `general-results.parquet`   → résultats par candidat/liste → resultats_candidats
- `candidats-results.parquet` → participation par BV          → resultats_participation

Périmètre (vague B, 2026-10-06) : `hdf` (5 départements, comportement historique) ou
`france` (toutes les communes présentes dans geographies_communes). Granularité : bureau
de vote dans les deux cas (étude d'impact : reports/etl-elections-france-2026-10-06.md).
Les lignes dont la commune est absente du référentiel géographique (communes fusionnées
depuis, Français de l'étranger, collectivités du Pacifique) sont écartées, comme avant.
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from ministere_de_l_info._sql import ligne_unique
from ministere_de_l_info.etl.schema_elections import CLES_RESULTATS

logger = logging.getLogger(__name__)

PERIMETRES: tuple[str, ...] = ("hdf", "france")

# Types de scrutin chargés par load_scrutins_listes (vague B). Les cantonales (cant)
# restent hors périmètre tant que Mathias ne l'a pas décidé.
TYPES_VAGUE_B: tuple[str, ...] = ("euro", "regi", "dpmt")


def filtre_perimetre(perimetre: str, alias: str = "gc") -> str:
    """Clause SQL de périmètre sur geographies_communes (liste blanche)."""
    if perimetre == "hdf":
        return f"{alias}.code_region = '32'"
    if perimetre == "france":
        return "TRUE"
    raise ValueError(f"Périmètre inconnu : {perimetre!r} (attendu : {PERIMETRES})")


def code_departement_sql(alias: str) -> str:
    """Code département normalisé.

    La source code l'outre-mer en « ZA » (971), « ZB » (972), « ZC » (973), « ZD » (974),
    « ZM » (976), « ZS » (975) certaines années : on prend alors les 3 premiers caractères
    du code commune. Sans effet sur les Hauts-de-France.
    """
    return (
        f"CASE WHEN {alias}.code_departement LIKE 'Z%' "
        f"THEN LEFT({alias}.code_commune, 3) ELSE {alias}.code_departement END"
    )


def _ids(type_scrutin: str) -> str:
    if type_scrutin not in TYPES_VAGUE_B + ("pres", "legi", "muni", "cant"):
        raise ValueError(f"Type de scrutin inconnu : {type_scrutin!r}")
    return f"(SELECT id_election FROM elections WHERE type_scrutin = '{type_scrutin}')"


def verifier_unicite_resultats(con: duckdb.DuckDBPyConnection, ids_sql: str) -> None:
    """Lève RuntimeError si une clé logique de résultat est en double (tables sans PK).

    ids_sql : sous-requête ou liste SQL des id_election à contrôler (code interne).
    """
    for table, cles in CLES_RESULTATS.items():
        cols = ", ".join(cles)
        doublons = con.execute(
            f"SELECT {cols}, COUNT(*) AS n FROM {table} "  # noqa: S608
            f"WHERE id_election IN {ids_sql} GROUP BY {cols} HAVING COUNT(*) > 1 LIMIT 5"
        ).fetchall()
        if doublons:
            raise RuntimeError(f"Doublons de clé dans {table} : {doublons}")


def load_scrutins_listes(
    con: duckdb.DuckDBPyConnection,
    type_scrutin: str,
    parquet_candidats: Path,
    parquet_participation: Path,
    perimetre: str = "hdf",
) -> tuple[int, int]:
    """Charge un type de scrutin sans circonscription (euro, regi, dpmt). Idempotent.

    DELETE de tous les scrutins du type puis INSERT filtré par périmètre.
    - no_panneau NULL dans la source (européennes 2004 et 2009) : numéro synthétique
      ROW_NUMBER par BV, comme pour les municipales 2008 ;
    - nom : `nom` de la source, sinon `binome` (départementales), sinon
      `nom_tete_liste` (européennes 2019, dont le bloc se résout par
      candidats_presidentielle comme pour les présidentielles 2017/2022).

    Retourne (lignes participation, lignes candidats) du type après chargement.
    """
    ids = _ids(type_scrutin)
    where = filtre_perimetre(perimetre)
    con.execute(f"DELETE FROM resultats_participation WHERE id_election IN {ids}")
    con.execute(f"DELETE FROM resultats_candidats WHERE id_election IN {ids}")
    con.execute(f"""
        INSERT INTO resultats_participation
            (id_election, code_departement, code_commune, code_bv,
             inscrits, abstentions, votants, blancs, nuls, exprimes, code_circo)
        SELECT p.id_election, {code_departement_sql("p")}, p.code_commune, p.code_bv,
               p.inscrits, p.abstentions, p.votants, p.blancs, p.nuls, p.exprimes, NULL
        FROM read_parquet('{parquet_participation}') p
        JOIN geographies_communes gc ON gc.code_insee = p.code_commune
        WHERE {where} AND p.id_election IN {ids}
    """)
    con.execute(f"""
        INSERT INTO resultats_candidats
            (id_election, code_departement, code_commune, code_bv,
             no_panneau, nuance, sexe, nom, prenom, voix,
             liste, libelle_abrege_liste, libelle_etendu_liste,
             nom_tete_liste, prenom_tete_liste)
        SELECT c.id_election, {code_departement_sql("c")}, c.code_commune, c.code_bv,
               COALESCE(c.no_panneau, CAST(ROW_NUMBER() OVER (
                   PARTITION BY c.id_election, c.code_departement, c.code_commune, c.code_bv
                   ORDER BY c.nuance, c.voix DESC) AS INTEGER)),
               c.nuance, c.sexe, COALESCE(c.nom, c.binome, c.nom_tete_liste), c.prenom, c.voix,
               c.liste, c.libelle_abrege_liste, c.libelle_etendu_liste,
               c.nom_tete_liste, NULL
        FROM read_parquet('{parquet_candidats}') c
        JOIN geographies_communes gc ON gc.code_insee = c.code_commune
        WHERE {where} AND c.id_election IN {ids}
    """)
    verifier_unicite_resultats(con, ids)
    n_p = ligne_unique(
        con.execute(f"SELECT COUNT(*) FROM resultats_participation WHERE id_election IN {ids}")
    )[0]
    n_c = ligne_unique(
        con.execute(f"SELECT COUNT(*) FROM resultats_candidats WHERE id_election IN {ids}")
    )[0]
    logger.info("%s (%s) : %d BV, %d lignes candidats/listes", type_scrutin, perimetre, n_p, n_c)
    return int(n_p), int(n_c)
