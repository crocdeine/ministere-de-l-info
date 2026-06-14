"""Schéma DuckDB — tables et vues du module Économie.

Fonctions exportées
-------------------
- create_economie_schema(con)  : CREATE TABLE IF NOT EXISTS, idempotent
- create_economie_views(con)   : CREATE OR REPLACE VIEW × 5

Tables (4)
----------
- economie_filosofi       : INSEE Filosofi (revenus/pauvreté), millésimes 2017-2021
- economie_rp             : INSEE RP actifs-emploi (chômage, CSP, industrie), 2015-2021
- economie_social         : CNAF RSA + DREES APL par commune/an
- economie_emploi_urssaf  : URSSAF effectifs salariés privés par commune × APE × an

Vues (5)
--------
- v_economie_commune           : jointure Filosofi + RP
- v_croisement_eco_elections   : économie × présidentielles T2
- v_evolution_economie_hdf     : agrégats HdF par année
- v_economie_sociale_commune   : economie_social + nom commune
- v_desindustrialisation_commune: variation emploi industriel entre 1ère et dernière année URSSAF

Filtre géographique
-------------------
Hauts-de-France uniquement (code_departement IN ('02','59','60','62','80')).
Le chargement (scripts/load_economie.py) filtre avant insertion.
"""

from __future__ import annotations

import logging

import duckdb

logger = logging.getLogger(__name__)


def create_economie_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Crée les 4 tables économiques. Idempotent (CREATE TABLE IF NOT EXISTS)."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS economie_filosofi (
            code_commune      VARCHAR(5) NOT NULL,
            annee             INTEGER    NOT NULL,
            taux_pauvrete     DOUBLE,
            niveau_vie_median DOUBLE,
            d1_niveau_vie     DOUBLE,
            d9_niveau_vie     DOUBLE,
            secret            BOOLEAN    DEFAULT FALSE,
            PRIMARY KEY (code_commune, annee)
        )
    """)
    logger.debug("Table economie_filosofi créée (ou existante).")

    con.execute("""
        CREATE TABLE IF NOT EXISTS economie_rp (
            code_commune           VARCHAR(5) NOT NULL,
            annee_millesime        INTEGER    NOT NULL,
            tx_chomage_dec         DOUBLE,
            part_ouvriers_employes DOUBLE,
            part_emploi_industriel DOUBLE,
            part_logements_sociaux DOUBLE,
            nb_logements_sociaux   INTEGER,
            pop_active             INTEGER,
            secret                 BOOLEAN    DEFAULT FALSE,
            PRIMARY KEY (code_commune, annee_millesime)
        )
    """)
    con.execute("ALTER TABLE economie_rp ADD COLUMN IF NOT EXISTS part_logements_sociaux DOUBLE")
    con.execute("ALTER TABLE economie_rp ADD COLUMN IF NOT EXISTS nb_logements_sociaux INTEGER")
    logger.debug("Table economie_rp créée (ou existante).")

    con.execute("""
        CREATE TABLE IF NOT EXISTS economie_social (
            code_commune    VARCHAR(5) NOT NULL,
            annee           INTEGER    NOT NULL,
            nb_foyers_rsa   INTEGER,
            taux_foyers_rsa DOUBLE,
            apl_medecins    DOUBLE,
            desert_medical  BOOLEAN,
            PRIMARY KEY (code_commune, annee)
        )
    """)
    logger.debug("Table economie_social créée (ou existante).")

    con.execute("""
        CREATE TABLE IF NOT EXISTS economie_emploi_urssaf (
            code_commune      VARCHAR(5) NOT NULL,
            annee             INTEGER    NOT NULL,
            secteur_gs        VARCHAR,
            code_ape          VARCHAR(5),
            nb_salaries       INTEGER,
            nb_etablissements INTEGER,
            PRIMARY KEY (code_commune, annee, code_ape)
        )
    """)
    logger.debug("Table economie_emploi_urssaf créée (ou existante).")
    logger.info("Schéma économie créé (4 tables).")


def create_economie_views(con: duckdb.DuckDBPyConnection) -> None:
    """Crée les 5 vues du module Économie.

    Dépendances :
    - v_economie_commune             : economie_filosofi + economie_rp
    - v_croisement_eco_elections     : v_economie_commune + v_scores_commune_pres
    - v_evolution_economie_hdf       : economie_filosofi + economie_rp agrégés HdF
    - v_economie_sociale_commune     : economie_social + geographies_communes
    - v_desindustrialisation_commune : economie_emploi_urssaf (industrie, min→max annee)
    """
    con.execute("""
        CREATE OR REPLACE VIEW v_economie_commune AS
        SELECT
            f.code_commune,
            f.annee,
            f.taux_pauvrete,
            f.niveau_vie_median,
            f.d1_niveau_vie,
            f.d9_niveau_vie,
            r.tx_chomage_dec,
            r.part_ouvriers_employes,
            r.part_emploi_industriel,
            r.part_logements_sociaux,
            r.nb_logements_sociaux,
            r.pop_active,
            (f.secret OR COALESCE(r.secret, FALSE)) AS secret_partiel
        FROM economie_filosofi f
        LEFT JOIN economie_rp r
            ON f.code_commune = r.code_commune
            AND f.annee = r.annee_millesime
    """)
    logger.debug("Vue v_economie_commune créée.")

    con.execute("""
        CREATE OR REPLACE VIEW v_croisement_eco_elections AS
        SELECT
            e.code_commune,
            e.annee         AS annee_election,
            e.bloc,
            e.voix,
            eco.taux_pauvrete,
            eco.tx_chomage_dec,
            eco.part_ouvriers_employes
        FROM v_scores_commune_pres e
        LEFT JOIN v_economie_commune eco
            ON e.code_commune = eco.code_commune
            AND eco.annee = e.annee - 1
            -- Jointure sur année n-1 : données éco de l'année précédant l'élection.
            -- Couverture : présidentielles 2022 → Filosofi 2021 ✓
            --              présidentielles 2017 → Filosofi 2016 → NULL (Filosofi commence 2017)
            --              présidentielles 2002/2007/2012 → NULL (hors couverture Filosofi)
            -- Le LEFT JOIN retourne NULL pour les années sans données — comportement attendu.
    """)
    logger.debug("Vue v_croisement_eco_elections créée.")

    con.execute("""
        CREATE OR REPLACE VIEW v_evolution_economie_hdf AS
        SELECT
            f.annee,
            AVG(f.taux_pauvrete)         AS taux_pauvrete_moyen,
            MEDIAN(f.niveau_vie_median)  AS niveau_vie_median_hdf,
            AVG(r.tx_chomage_dec)        AS tx_chomage_moyen
        FROM economie_filosofi f
        LEFT JOIN economie_rp r
            ON f.code_commune = r.code_commune
            AND f.annee = r.annee_millesime
        GROUP BY f.annee
        ORDER BY f.annee
    """)
    logger.debug("Vue v_evolution_economie_hdf créée.")

    con.execute("""
        CREATE OR REPLACE VIEW v_economie_sociale_commune AS
        SELECT
            s.code_commune,
            s.annee,
            gc.nom            AS nom_commune,
            s.nb_foyers_rsa,
            s.taux_foyers_rsa,
            s.apl_medecins,
            s.desert_medical
        FROM economie_social s
        LEFT JOIN geographies_communes gc ON gc.code_insee = s.code_commune
    """)
    logger.debug("Vue v_economie_sociale_commune créée.")

    con.execute("""
        CREATE OR REPLACE VIEW v_desindustrialisation_commune AS
        WITH industrie AS (
            SELECT
                code_commune,
                annee,
                SUM(COALESCE(nb_salaries, 0)) AS nb_salaries_industrie
            FROM economie_emploi_urssaf
            WHERE secteur_gs LIKE '%Industrie%'
            GROUP BY code_commune, annee
        ),
        bornes AS (
            SELECT
                code_commune,
                MIN(annee) AS annee_min,
                MAX(annee) AS annee_max
            FROM industrie
            GROUP BY code_commune
        )
        SELECT
            b.code_commune,
            gc.nom                              AS nom_commune,
            b.annee_min,
            b.annee_max,
            debut.nb_salaries_industrie         AS salaries_debut,
            fin.nb_salaries_industrie           AS salaries_fin,
            (fin.nb_salaries_industrie - debut.nb_salaries_industrie)::INTEGER AS variation_absolue,
            CASE
                WHEN debut.nb_salaries_industrie > 0
                THEN ROUND(
                    (fin.nb_salaries_industrie - debut.nb_salaries_industrie)::DOUBLE
                    / debut.nb_salaries_industrie * 100.0, 2
                )
                ELSE NULL
            END AS variation_pct
        FROM bornes b
        JOIN industrie debut
            ON debut.code_commune = b.code_commune AND debut.annee = b.annee_min
        JOIN industrie fin
            ON fin.code_commune = b.code_commune AND fin.annee = b.annee_max
        LEFT JOIN geographies_communes gc ON gc.code_insee = b.code_commune
    """)
    logger.debug("Vue v_desindustrialisation_commune créée.")
    logger.info("Vues économie créées (5 vues).")
