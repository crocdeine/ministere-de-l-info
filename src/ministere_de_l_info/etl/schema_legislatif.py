"""Schéma DuckDB — tables et vues du module Législatif (Phase F2.2).

Fonctions exportées
-------------------
- create_legislatif_schema(con)  : CREATE TABLE IF NOT EXISTS + migrations, idempotent
- create_legislatif_views(con)   : CREATE OR REPLACE VIEW × 2

Tables (3)
----------
- leg_elus          : élus nationaux fusionnés (AN et Sénat, actifs et anciens)
- leg_activite      : métriques d'activité par élu × date d'extraction
- leg_blocs_override: corrections manuelles de classement bloc (ex: RN en NI sénat)

Vues (2)
--------
- v_elus_hdf_actuels   : élus actifs avec bloc_final (override ou dérivé) — filtre HdF en UI
- v_activite_par_bloc  : agrégats d'activité par bloc × chambre (actifs seulement)

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

    logger.info("Schéma législatif créé : leg_elus, leg_activite, leg_blocs_override")


def create_legislatif_views(con: duckdb.DuckDBPyConnection) -> None:
    """Crée ou remplace les vues analytiques du module Législatif."""
    con.execute("""
        CREATE OR REPLACE VIEW v_elus_hdf_actuels AS
        SELECT
            e.*,
            COALESCE(o.bloc_force, e.bloc_politique) AS bloc_final
        FROM leg_elus e
        LEFT JOIN leg_blocs_override o
            ON e.id = o.elu_id AND e.chambre = o.chambre
        WHERE e.est_actif = TRUE
    """)

    con.execute("""
        CREATE OR REPLACE VIEW v_activite_par_bloc AS
        SELECT
            COALESCE(o.bloc_force, e.bloc_politique) AS bloc,
            e.chambre,
            AVG(a.commission_presences)           AS moy_presences_commission,
            AVG(a.hemicycle_interventions)        AS moy_interventions_hemicycle,
            AVG(a.amendements_proposes)           AS moy_amendements_proposes,
            AVG(a.score_participation)            AS moy_score_participation,
            AVG(a.score_loyaute)                  AS moy_score_loyaute,
            COUNT(*)                              AS nb_elus
        FROM leg_elus e
        LEFT JOIN leg_blocs_override o
            ON e.id = o.elu_id AND e.chambre = o.chambre
        LEFT JOIN leg_activite a
            ON e.id = a.elu_id AND e.chambre = a.chambre
        WHERE e.est_actif = TRUE
        GROUP BY COALESCE(o.bloc_force, e.bloc_politique), e.chambre
    """)

    logger.info("Vues législatif créées : v_elus_hdf_actuels, v_activite_par_bloc")
