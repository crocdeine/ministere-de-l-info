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
from ministere_de_l_info.etl.schema_elections import CLES_RESULTATS, ECARTS_DDL, PASSAGE_DDL
from ministere_de_l_info.perimetre import DEPTS_HDF_SQL

logger = logging.getLogger(__name__)

PERIMETRES: tuple[str, ...] = ("hdf", "france")

# Types de scrutin chargés par load_scrutins_listes (vague B). Les cantonales (cant)
# restent hors périmètre tant que Mathias ne l'a pas décidé.
TYPES_VAGUE_B: tuple[str, ...] = ("euro", "regi", "dpmt")

# Part maximale des exprimés d'un scrutin écartée hors étranger et Pacifique (« reste »)
SEUIL_ECART_RESTE_PCT: float = 3.0

# Catégorie d'une ligne de la source dont la commune est absente du référentiel :
# étranger ; collectivités d'outre-mer hors référentiel (Pacifique 98x, Saint-Martin et
# Saint-Barthélemy, codés 97123/97127 avant 2007 puis 977/978) ; reste.
_CATEGORIE_ECART_SQL = """CASE
    WHEN p.code_departement = 'ZZ' THEN 'etranger'
    WHEN p.code_commune LIKE '98%' OR p.code_commune LIKE '977%' OR p.code_commune LIKE '978%'
         OR p.code_commune IN ('97123', '97127')
         OR p.code_departement IN ('ZN', 'ZP', 'ZW', 'ZX', 'ZT', 'ZY')
        THEN 'outremer_hors_referentiel'
    ELSE 'reste' END"""


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


def preparer_rattachement(con: duckdb.DuckDBPyConnection) -> int:
    """Garantit communes_passage et code_commune_origine ; avertit si la table est vide.

    Retourne le nombre de codes anciens disponibles pour le rattachement.
    """
    con.execute(PASSAGE_DDL)
    for table in CLES_RESULTATS:
        con.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS code_commune_origine VARCHAR(5)")
    n = int(ligne_unique(con.execute("SELECT COUNT(*) FROM communes_passage"))[0])
    if n == 0:
        logger.warning(
            "communes_passage vide : les communes fusionnées seront écartées "
            "(lancer scripts/load_communes_passage.py)"
        )
    return n


def source_rattachee_sql(parquet: Path | str) -> str:
    """Sous-requête sur un Parquet de la source, communes fusionnées rattachées.

    Une commune absente du référentiel et présente dans communes_passage prend le code
    de la commune actuelle (décision Mathias 2026-10-07) ; son code d'origine est gardé
    dans code_commune_origine et préfixe son code de bureau (« 74011-0001 ») pour éviter
    toute collision avec les bureaux de la commune d'accueil. Les codes « Z* » de
    l'outre-mer sont normalisés (code_departement_sql).
    """
    return f"""(
        SELECT s.* REPLACE (
            CASE WHEN cp.code_actuel IS NULL THEN {code_departement_sql("s")}
                 ELSE g2.code_departement END AS code_departement,
            COALESCE(cp.code_actuel, s.code_commune) AS code_commune,
            CASE WHEN cp.code_actuel IS NULL THEN s.code_bv
                 ELSE s.code_commune || '-' || s.code_bv END AS code_bv
        ),
        CASE WHEN cp.code_actuel IS NOT NULL THEN s.code_commune END AS code_commune_origine,
        -- département du scrutin (avant rattachement) : clé des circonscriptions
        {code_departement_sql("s")} AS code_departement_scrutin
        FROM read_parquet('{parquet}') s
        LEFT JOIN communes_passage cp ON cp.code_ancien = s.code_commune
        LEFT JOIN geographies_communes g2 ON g2.code_insee = cp.code_actuel
    )"""


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
    preparer_rattachement(con)
    where = filtre_perimetre(perimetre)
    con.execute(f"DELETE FROM resultats_participation WHERE id_election IN {ids}")
    con.execute(f"DELETE FROM resultats_candidats WHERE id_election IN {ids}")
    con.execute(f"""
        INSERT INTO resultats_participation
            (id_election, code_departement, code_commune, code_bv,
             inscrits, abstentions, votants, blancs, nuls, exprimes, code_circo, code_commune_origine)
        SELECT p.id_election, {code_departement_sql("p")}, p.code_commune, p.code_bv,
               p.inscrits, p.abstentions, p.votants, p.blancs, p.nuls, p.exprimes, NULL,
            p.code_commune_origine
        FROM {source_rattachee_sql(parquet_participation)} p
        JOIN geographies_communes gc ON gc.code_insee = p.code_commune
        WHERE {where} AND p.id_election IN {ids}
    """)
    con.execute(f"""
        INSERT INTO resultats_candidats
            (id_election, code_departement, code_commune, code_bv,
             no_panneau, nuance, sexe, nom, prenom, voix,
             liste, libelle_abrege_liste, libelle_etendu_liste,
             nom_tete_liste, prenom_tete_liste, code_commune_origine)
        SELECT c.id_election, {code_departement_sql("c")}, c.code_commune, c.code_bv,
               COALESCE(c.no_panneau, CAST(ROW_NUMBER() OVER (
                   PARTITION BY c.id_election, c.code_departement, c.code_commune, c.code_bv
                   ORDER BY c.nuance, c.voix DESC) AS INTEGER)),
               c.nuance, c.sexe, COALESCE(c.nom, c.binome, c.nom_tete_liste), c.prenom, c.voix,
               c.liste, c.libelle_abrege_liste, c.libelle_etendu_liste,
               c.nom_tete_liste, NULL,
            c.code_commune_origine
        FROM {source_rattachee_sql(parquet_candidats)} c
        JOIN geographies_communes gc ON gc.code_insee = c.code_commune
        WHERE {where} AND c.id_election IN {ids}
    """)
    verifier_unicite_resultats(con, ids)
    controler_chargement(con, parquet_participation, ids, perimetre)
    n_p = ligne_unique(
        con.execute(f"SELECT COUNT(*) FROM resultats_participation WHERE id_election IN {ids}")
    )[0]
    n_c = ligne_unique(
        con.execute(f"SELECT COUNT(*) FROM resultats_candidats WHERE id_election IN {ids}")
    )[0]
    logger.info("%s (%s) : %d BV, %d lignes candidats/listes", type_scrutin, perimetre, n_p, n_c)
    return int(n_p), int(n_c)


def controler_chargement(
    con: duckdb.DuckDBPyConnection,
    parquet_participation: Path,
    ids_sql: str,
    perimetre: str,
    seuil_reste_pct: float = SEUIL_ECART_RESTE_PCT,
) -> None:
    """Contrôles après chargement (vague B, durcissement du 2026-10-07).

    1. Lignes de la source écartées (commune absente de geographies_communes), par
       scrutin et catégorie (rattachee, etranger, outremer_hors_referentiel, reste) : écrites dans
       elections_ecarts_chargement et journalisées (warning) ; RuntimeError si la
       catégorie « reste » dépasse seuil_reste_pct des exprimés d'un scrutin.
    2. Hors municipales, bureaux où la somme des voix diffère des exprimés : warning avec
       les 5 pires écarts (non bloquant).
    """
    filtre_perimetre(perimetre)  # valide la valeur (liste blanche)
    con.execute(ECARTS_DDL)
    con.execute(PASSAGE_DDL)
    src = f"read_parquet('{parquet_participation}')"
    perim_src = "TRUE" if perimetre == "france" else f"p.code_departement IN ({DEPTS_HDF_SQL})"
    con.execute(
        f"DELETE FROM elections_ecarts_chargement WHERE id_election IN {ids_sql} AND perimetre = ?",
        [perimetre],
    )
    con.execute(
        f"""
        INSERT INTO elections_ecarts_chargement
        WITH src AS (
            SELECT p.id_election, p.code_commune, p.exprimes,
                   gc.code_insee IS NULL OR cp.code_actuel IS NOT NULL AS ecartee,
                   CASE WHEN gc.code_insee IS NOT NULL THEN 'rattachee'
                        ELSE {_CATEGORIE_ECART_SQL} END AS categorie
            FROM {src} p
            LEFT JOIN communes_passage cp ON cp.code_ancien = p.code_commune
            LEFT JOIN geographies_communes gc
                ON gc.code_insee = COALESCE(cp.code_actuel, p.code_commune)
            WHERE p.id_election IN {ids_sql} AND {perim_src}
        ),
        tot AS (SELECT id_election, SUM(exprimes) AS t FROM src GROUP BY 1)
        SELECT s.id_election, ?, s.categorie, COUNT(DISTINCT s.code_commune), COUNT(*),
               SUM(s.exprimes), MAX(tot.t),
               ROUND(100.0 * SUM(s.exprimes) / NULLIF(MAX(tot.t), 0), 3)
        FROM src s JOIN tot USING (id_election)
        WHERE s.ecartee
        GROUP BY s.id_election, s.categorie
        """,
        [perimetre],
    )
    ecarts = con.execute(
        "SELECT id_election, categorie, nb_communes, nb_bv, exprimes, pct_exprimes "
        f"FROM elections_ecarts_chargement WHERE id_election IN {ids_sql} AND perimetre = ? "
        "ORDER BY 1, 2",
        [perimetre],
    ).fetchall()
    for idel, cat, n_com, n_bv, expr, pct in ecarts:
        logger.warning(
            "%s : %s écarté(s) — %d communes, %d BV, %d exprimés (%.3f %%)",
            idel,
            cat,
            n_com,
            n_bv,
            expr or 0,
            pct or 0.0,
        )
    trop = [(e[0], e[5]) for e in ecarts if e[1] == "reste" and (e[5] or 0) > seuil_reste_pct]
    if trop:
        raise RuntimeError(
            f"Communes absentes du référentiel au-delà de {seuil_reste_pct} % des exprimés : {trop}"
        )

    pires = con.execute(f"""
        WITH v AS (
            SELECT id_election, code_departement, code_commune, code_bv, SUM(voix) AS voix
            FROM resultats_candidats WHERE id_election IN {ids_sql}
            GROUP BY ALL
        )
        SELECT rp.id_election, rp.code_commune, rp.code_bv, rp.exprimes, v.voix,
               ABS(COALESCE(v.voix, 0) - COALESCE(rp.exprimes, 0)) AS ecart,
               COUNT(*) OVER (PARTITION BY rp.id_election) AS n_bv_ecart
        FROM resultats_participation rp
        JOIN elections e ON e.id_election = rp.id_election
        LEFT JOIN v ON v.id_election = rp.id_election
            AND v.code_departement = rp.code_departement
            AND v.code_commune = rp.code_commune AND v.code_bv = rp.code_bv
        WHERE rp.id_election IN {ids_sql} AND e.type_scrutin <> 'muni'
          AND COALESCE(v.voix, 0) <> COALESCE(rp.exprimes, 0)
        QUALIFY ROW_NUMBER() OVER (PARTITION BY rp.id_election ORDER BY ecart DESC) <= 5
        ORDER BY rp.id_election, ecart DESC
    """).fetchall()
    for idel, com, bv, expr, voix, ecart, n in pires:
        logger.warning(
            "%s : %d BV où somme des voix ≠ exprimés ; ex. %s/%s exprimés %s, voix %s (écart %d)",
            idel,
            n,
            com,
            bv,
            expr,
            voix,
            ecart,
        )
