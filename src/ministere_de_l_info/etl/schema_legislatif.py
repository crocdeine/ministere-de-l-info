"""Schéma DuckDB — tables et vues du module Législatif (Phase F2.2, ADR-0011).

Fonctions exportées
-------------------
- create_legislatif_schema(con)  : CREATE TABLE IF NOT EXISTS + migrations, idempotent
- create_legislatif_views(con)   : CREATE OR REPLACE VIEW × 5

Tables (5)
----------
- leg_elus          : identité des élus (AN et Sénat, actifs et anciens), 1 ligne par élu
- leg_mandats       : mandats élu × chambre × législature × groupe (ADR-0011)
- leg_groupes_blocs : référentiel (chambre, groupe, législature) → bloc + source_bloc
- leg_activite      : métriques d'activité par élu × date d'extraction
- leg_blocs_override: corrections manuelles de classement bloc (ex: RN en NI sénat)

Vues (5)
--------
- v_elus_actuels         : élus actifs (France entière) avec bloc_final
- v_elus_hdf_actuels     : alias de compatibilité de v_elus_actuels (nom trompeur, déprécié)
- v_mandats_legislatif   : mandats avec bloc du groupe pour la législature + override
- v_composition_legislature : effectifs par chambre × législature × bloc_final
- v_activite_par_bloc    : agrégats d'activité par bloc × chambre (actifs seulement)

Règle de bloc : ``bloc_final = COALESCE(bloc_force, bloc du groupe pour la législature)``.
Un groupe absent de leg_groupes_blocs donne bloc_final NULL (non classé), jamais DIV.

Sources
-------
- Sénat  : data.senat.fr CSV ODSEN_GENERAL (national)
- AN     : Datan / data.gouv.fr CSV (législatures 12-17, national)
"""

from __future__ import annotations

import logging

import duckdb

logger = logging.getLogger(__name__)


def create_legislatif_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Crée les tables du module Législatif (idempotent via IF NOT EXISTS + migrations)."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS leg_elus (
            id               VARCHAR(50) NOT NULL,
            chambre          VARCHAR(10) NOT NULL,
            legislature      INTEGER,
            nom              VARCHAR     NOT NULL,
            prenom           VARCHAR     NOT NULL,
            sexe             VARCHAR(1),
            date_naissance   DATE,
            code_departement VARCHAR(3)  NOT NULL,
            nom_departement  VARCHAR,
            region_nom       VARCHAR,
            num_circo        INTEGER,
            groupe_sigle     VARCHAR,
            groupe_nom       VARCHAR,
            bloc_politique   VARCHAR(4),
            bloc_override    BOOLEAN     DEFAULT FALSE,
            date_debut_mandat DATE,
            date_fin_mandat  DATE,
            est_actif        BOOLEAN     NOT NULL,
            profession       VARCHAR,
            source           VARCHAR(30),
            PRIMARY KEY (id, chambre)
        )
    """)

    # Migration F2.2 : ajout region_nom si table existait avant
    con.execute("ALTER TABLE leg_elus ADD COLUMN IF NOT EXISTS region_nom VARCHAR")

    con.execute("""
        CREATE TABLE IF NOT EXISTS leg_activite (
            elu_id                          VARCHAR(50) NOT NULL,
            chambre                         VARCHAR(10) NOT NULL,
            date_extraction                 DATE        NOT NULL,
            semaines_presence               INTEGER,
            commission_presences            INTEGER,
            commission_interventions        INTEGER,
            hemicycle_interventions         INTEGER,
            amendements_proposes            INTEGER,
            amendements_signes              INTEGER,
            amendements_adoptes             INTEGER,
            rapports                        INTEGER,
            propositions_ecrites            INTEGER,
            propositions_signees            INTEGER,
            questions_ecrites               INTEGER,
            questions_orales                INTEGER,
            score_participation             FLOAT,
            score_participation_specialite  FLOAT,
            score_loyaute                   FLOAT,
            score_majorite                  FLOAT,
            source                          VARCHAR(30),
            PRIMARY KEY (elu_id, chambre, date_extraction)
        )
    """)

    # Migrations F2.2 : ajout colonnes scores si table existait avant
    for col in (
        "score_participation FLOAT",
        "score_participation_specialite FLOAT",
        "score_loyaute FLOAT",
        "score_majorite FLOAT",
    ):
        con.execute(f"ALTER TABLE leg_activite ADD COLUMN IF NOT EXISTS {col}")

    con.execute("""
        CREATE TABLE IF NOT EXISTS leg_blocs_override (
            elu_id        VARCHAR(50) NOT NULL,
            chambre       VARCHAR(10) NOT NULL,
            bloc_force    VARCHAR(4)  NOT NULL,
            justification VARCHAR,
            PRIMARY KEY (elu_id, chambre)
        )
    """)

    # ADR-0011 — mandats par législature. Pas de clé primaire : la législature est NULL
    # pour le Sénat et un député peut changer de groupe en cours de législature (source
    # complète future). Clé logique : (elu_id, chambre, legislature, groupe_sigle, date_debut).
    con.execute("""
        CREATE TABLE IF NOT EXISTS leg_mandats (
            elu_id           VARCHAR(50) NOT NULL,
            chambre          VARCHAR(10) NOT NULL,
            legislature      INTEGER,
            groupe_sigle     VARCHAR,
            groupe_nom       VARCHAR,
            code_departement VARCHAR(3),
            num_circo        INTEGER,
            date_debut       DATE,
            date_fin         DATE,
            granularite      VARCHAR(30) NOT NULL,
            source           VARCHAR(30) NOT NULL
        )
    """)

    # ADR-0011 — référentiel groupe × période → bloc. Bornes NULL = toutes périodes
    # (Sénat) ; AN : intervalles de législatures toujours bornés.
    con.execute("""
        CREATE TABLE IF NOT EXISTS leg_groupes_blocs (
            chambre           VARCHAR(10) NOT NULL,
            groupe            VARCHAR     NOT NULL,
            legislature_debut INTEGER,
            legislature_fin   INTEGER,
            bloc              VARCHAR(4)  NOT NULL,
            libelle           VARCHAR,
            source_bloc       VARCHAR     NOT NULL
        )
    """)

    logger.info(
        "Schéma législatif créé : leg_elus, leg_mandats, leg_groupes_blocs, "
        "leg_activite, leg_blocs_override"
    )


def _jointure_groupe(alias_groupe: str, alias_source: str) -> str:
    """Condition de jointure (chambre, groupe, législature) → leg_groupes_blocs.

    Une législature NULL (Sénat) ne correspond qu'aux entrées non bornées.
    """
    g, s = alias_groupe, alias_source
    return (
        f"{g}.chambre = {s}.chambre AND {g}.groupe = {s}.groupe_sigle "
        f"AND ({g}.legislature_debut IS NULL OR {s}.legislature >= {g}.legislature_debut) "
        f"AND ({g}.legislature_fin IS NULL OR {s}.legislature <= {g}.legislature_fin)"
    )


def create_legislatif_views(con: duckdb.DuckDBPyConnection) -> None:
    """Crée ou remplace les vues analytiques du module Législatif."""
    con.execute(f"""
        CREATE OR REPLACE VIEW v_elus_actuels AS
        SELECT
            e.*,
            g.bloc        AS bloc_groupe,
            g.source_bloc AS source_bloc,
            COALESCE(o.bloc_force, g.bloc) AS bloc_final
        FROM leg_elus e
        LEFT JOIN leg_groupes_blocs g ON {_jointure_groupe("g", "e")}
        LEFT JOIN leg_blocs_override o
            ON e.id = o.elu_id AND e.chambre = o.chambre
        WHERE e.est_actif = TRUE
    """)

    # Alias de compatibilité : l'ancien nom laissait croire à un filtre HdF (ADR-0011).
    con.execute("CREATE OR REPLACE VIEW v_elus_hdf_actuels AS SELECT * FROM v_elus_actuels")

    con.execute(f"""
        CREATE OR REPLACE VIEW v_mandats_legislatif AS
        SELECT
            m.elu_id,
            m.chambre,
            m.legislature,
            m.groupe_sigle,
            m.groupe_nom,
            m.code_departement,
            m.num_circo,
            m.date_debut,
            m.date_fin,
            m.granularite,
            m.source,
            e.nom,
            e.prenom,
            e.est_actif,
            g.bloc        AS bloc_groupe,
            g.source_bloc AS source_bloc,
            o.bloc_force,
            COALESCE(o.bloc_force, g.bloc) AS bloc_final
        FROM leg_mandats m
        JOIN leg_elus e ON e.id = m.elu_id AND e.chambre = m.chambre
        LEFT JOIN leg_groupes_blocs g ON {_jointure_groupe("g", "m")}
        LEFT JOIN leg_blocs_override o
            ON m.elu_id = o.elu_id AND m.chambre = o.chambre
    """)

    con.execute("""
        CREATE OR REPLACE VIEW v_composition_legislature AS
        SELECT
            chambre,
            legislature,
            granularite,
            bloc_final,
            COUNT(DISTINCT elu_id) AS nb_elus
        FROM v_mandats_legislatif
        WHERE legislature IS NOT NULL
        GROUP BY chambre, legislature, granularite, bloc_final
    """)

    con.execute("""
        CREATE OR REPLACE VIEW v_activite_par_bloc AS
        SELECT
            e.bloc_final                          AS bloc,
            e.chambre,
            AVG(a.commission_presences)           AS moy_presences_commission,
            AVG(a.hemicycle_interventions)        AS moy_interventions_hemicycle,
            AVG(a.amendements_proposes)           AS moy_amendements_proposes,
            AVG(a.score_participation)            AS moy_score_participation,
            AVG(a.score_loyaute)                  AS moy_score_loyaute,
            COUNT(*)                              AS nb_elus
        FROM v_elus_actuels e
        LEFT JOIN leg_activite a
            ON e.id = a.elu_id AND e.chambre = a.chambre
        GROUP BY e.bloc_final, e.chambre
    """)

    logger.info(
        "Vues législatif créées : v_elus_actuels (+ alias v_elus_hdf_actuels), "
        "v_mandats_legislatif, v_composition_legislature, v_activite_par_bloc"
    )
