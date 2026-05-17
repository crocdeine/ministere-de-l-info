"""ETL territorial complet — DuckDB + IGN ADMIN-EXPRESS + INSEE Mélodi + data.gouv.fr.

Usage
-----
    uv run python scripts/etl_territoires.py [--force] [--skip-communes]
        [--millesimes 2013,2018,2023] [--level region]

Étapes couvertes
----------------
    - Schéma DuckDB (7 tables + 2 méta) : toujours exécuté
    - Régions (18), départements (101), EPCI (~1250)
    - Communes (~35 000) — gate utilisateur, 30-60 min
    - Arrondissements municipaux (44), circonscriptions (559)
    - Populations historisées INSEE millésimes 2013 / 2018 / 2023
    - 3 vues SQL d'agrégation (v_population_region/departement/epci)

Base de données cible
---------------------
    data/ministere.duckdb  (partagée avec app.py)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import tempfile
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))  # noqa: E402

from ministere_de_l_info.data_sources.circonscriptions import (  # noqa: F401, E402
    fetch_circonscriptions_legislatives,
)
from ministere_de_l_info.data_sources.geo import fetch_admin_express  # noqa: F401, E402
from ministere_de_l_info.data_sources.insee_populations import fetch_populations  # noqa: F401, E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

_DB_PATH = ROOT / "data" / "ministere.duckdb"
_SCHEMA_VERSION = 1


# ── Connexion ─────────────────────────────────────────────────────────────────


def _open_connection(db_path: Path = _DB_PATH) -> duckdb.DuckDBPyConnection:
    """Ouvre la connexion DuckDB et charge l'extension spatial."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    con.execute("INSTALL spatial; LOAD spatial;")
    logger.debug("Connexion DuckDB ouverte : %s", db_path)
    return con


# ── Schéma ────────────────────────────────────────────────────────────────────


def _create_schema(con: duckdb.DuckDBPyConnection) -> None:
    """Crée les 7 tables métier, 2 tables méta et les index UNIQUE.

    Idempotent : CREATE TABLE IF NOT EXISTS partout, jamais de DROP.
    geographies_regions existante (ancien schéma, colonne 'population') sera
    remplacée par _load_regions() avec DROP + CREATE — pas ici.
    Les vues sont créées par _create_views() après chargement des données.
    """
    # ── Tables géographiques ──────────────────────────────────────────────────
    con.execute("""
        CREATE TABLE IF NOT EXISTS geographies_regions (
            code_insee                   VARCHAR(3) NOT NULL,
            nom                          VARCHAR    NOT NULL,
            geometry                     GEOMETRY,
            geometry_simplified_national GEOMETRY,
            geometry_simplified_regional GEOMETRY,
            UNIQUE (code_insee)
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS geographies_departements (
            code_insee                        VARCHAR(3) NOT NULL,
            nom                               VARCHAR    NOT NULL,
            code_region                       VARCHAR(3),
            geometry                          GEOMETRY,
            geometry_simplified_national      GEOMETRY,
            geometry_simplified_departemental GEOMETRY,
            UNIQUE (code_insee)
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS geographies_epci (
            code_siren                 VARCHAR(9) NOT NULL,
            nom                        VARCHAR    NOT NULL,
            type_epci                  VARCHAR(5),
            code_departement_principal VARCHAR(3),
            geometry                   GEOMETRY,
            geometry_simplified_epci   GEOMETRY,
            UNIQUE (code_siren)
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS geographies_communes (
            code_insee                   VARCHAR(5) NOT NULL,
            nom                          VARCHAR    NOT NULL,
            code_departement             VARCHAR(3),
            code_region                  VARCHAR(3),
            code_epci                    VARCHAR(9),
            geometry                     GEOMETRY,
            geometry_simplified_communal GEOMETRY,
            UNIQUE (code_insee)
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS geographies_arrondissements_municipaux (
            code_insee                   VARCHAR(5) NOT NULL,
            nom                          VARCHAR    NOT NULL,
            code_commune_mere            VARCHAR(5) NOT NULL,
            code_departement             VARCHAR(3),
            geometry                     GEOMETRY,
            geometry_simplified_communal GEOMETRY,
            UNIQUE (code_insee)
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS geographies_circonscriptions (
            code                      VARCHAR(6) NOT NULL,
            nom                       VARCHAR,
            code_departement          VARCHAR(3),
            nom_departement           VARCHAR,
            geometry                  GEOMETRY,
            geometry_simplified_circo GEOMETRY,
            UNIQUE (code)
        )
    """)

    # ── Table populations ─────────────────────────────────────────────────────
    con.execute("""
        CREATE TABLE IF NOT EXISTS populations (
            code_insee_commune VARCHAR(5) NOT NULL,
            annee              INTEGER    NOT NULL,
            municipale         INTEGER    NOT NULL,
            comptee_a_part     INTEGER,
            totale             INTEGER,
            source             VARCHAR    NOT NULL DEFAULT 'DS_POPULATIONS_HISTORIQUES'
        )
    """)
    con.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_populations_code_annee_source
            ON populations(code_insee_commune, annee, source)
    """)

    # ── Tables méta ──────────────────────────────────────────────────────────
    con.execute("""
        CREATE TABLE IF NOT EXISTS _etl_metadata (
            table_name     VARCHAR   NOT NULL,
            loaded_at      TIMESTAMP NOT NULL,
            source_version VARCHAR,
            row_count      INTEGER   NOT NULL,
            UNIQUE (table_name)
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS _schema_version (
            version    INTEGER   NOT NULL,
            applied_at TIMESTAMP NOT NULL
        )
    """)
    con.execute(
        """
        INSERT INTO _schema_version (version, applied_at)
        SELECT ?, NOW()
        WHERE (SELECT COUNT(*) FROM _schema_version) = 0
        """,
        [_SCHEMA_VERSION],
    )

    logger.info(
        "Schéma v%d créé/vérifié : 9 tables (7 métier + 2 méta)", _SCHEMA_VERSION
    )


# ── Chargeurs (stubs — implémentés aux étapes 5–12) ──────────────────────────


def _load_regions(con: duckdb.DuckDBPyConnection, force: bool = False) -> None:
    """Charge les 18 régions (13 métro + 5 DROM) dans geographies_regions.

    Source : fetch_admin_express("region", dom=True) — WFS IGN ADMINEXPRESS-COG.LATEST.
    Stratégie DROP + CREATE : le schéma casse l'ancienne table (suppression colonne population).
    Simplifications : geometry_simplified_national (tol=0.01), geometry_simplified_regional (tol=0.005).
    Cache : le batch disque ne stocke pas le paramètre dom — utiliser force=True pour garantir
    les 18 régions (DROM) si le cache contient une version metro seule (13 régions).
    Écrit dans _etl_metadata après succès.
    """
    raw_dir = ROOT / "data" / "raw"
    batch_paths = list(
        fetch_admin_express("region", dom=True, force=force, raw_dir=raw_dir)
    )

    con.execute("DROP TABLE IF EXISTS geographies_regions")
    con.execute("""
        CREATE TABLE geographies_regions (
            code_insee                   VARCHAR(3) NOT NULL,
            nom                          VARCHAR    NOT NULL,
            geometry                     GEOMETRY,
            geometry_simplified_national GEOMETRY,
            geometry_simplified_regional GEOMETRY,
            UNIQUE (code_insee)
        )
    """)

    for batch_path in batch_paths:
        path_sql = str(batch_path).replace("'", "''")
        con.execute(f"""
            INSERT INTO geographies_regions
            SELECT
                code_insee,
                nom_officiel AS nom,
                geom AS geometry,
                CASE
                    WHEN ST_IsValid(ST_Simplify(geom, 0.01)) THEN ST_Simplify(geom, 0.01)
                    ELSE geom
                END AS geometry_simplified_national,
                CASE
                    WHEN ST_IsValid(ST_Simplify(geom, 0.005)) THEN ST_Simplify(geom, 0.005)
                    ELSE geom
                END AS geometry_simplified_regional
            FROM ST_Read('{path_sql}')
        """)
        logger.debug("Batch inséré : %s", batch_path.name)

    count = con.execute("SELECT COUNT(*) FROM geographies_regions").fetchone()[0]
    if not (13 <= count <= 20):
        raise RuntimeError(
            f"Nombre de régions hors fourchette [13-20] : {count}. "
            "Vérifier la source IGN ou utiliser --force pour re-télécharger."
        )

    codes = [
        r[0]
        for r in con.execute(
            "SELECT code_insee FROM geographies_regions ORDER BY code_insee"
        ).fetchall()
    ]
    logger.info("Chargé %d régions (codes : %s … %s)", count, codes[0], codes[-1])

    con.execute("DELETE FROM _etl_metadata WHERE table_name = 'geographies_regions'")
    con.execute(
        "INSERT INTO _etl_metadata VALUES (?, NOW(), 'ADMINEXPRESS-COG.LATEST', ?)",
        ["geographies_regions", count],
    )


def _load_departements(con: duckdb.DuckDBPyConnection, force: bool = False) -> None:
    """Charge les 101 départements (96 métro + 5 DROM) dans geographies_departements.

    Source : fetch_admin_express("departement", dom=True) — WFS IGN.
    Champ WFS code_region : code_insee_de_la_region (vérifié GetFeature 2026-05-17).
    Corse : codes '2A' (Corse-du-Sud) et '2B' (Haute-Corse) — VARCHAR natif.
    batch_size=50 : le WFS IGN coupe les connexions chunked sur COUNT=1000 pour ce niveau
    (géométries détaillées). 50 features/batch × 3 batches = 101 OK.
    Simplifications : geometry_simplified_national (0.01), geometry_simplified_departemental (0.001).
    Écrit dans _etl_metadata après succès.
    """
    raw_dir = ROOT / "data" / "raw"
    batch_paths = list(
        fetch_admin_express(
            "departement", dom=True, force=force, batch_size=50, raw_dir=raw_dir
        )
    )

    con.execute("DROP TABLE IF EXISTS geographies_departements")
    con.execute("""
        CREATE TABLE geographies_departements (
            code_insee                        VARCHAR(3) NOT NULL,
            code_region                       VARCHAR(3) NOT NULL,
            nom                               VARCHAR    NOT NULL,
            geometry                          GEOMETRY,
            geometry_simplified_national      GEOMETRY,
            geometry_simplified_departemental GEOMETRY,
            UNIQUE (code_insee)
        )
    """)

    for batch_path in batch_paths:
        path_sql = str(batch_path).replace("'", "''")
        con.execute(f"""
            INSERT INTO geographies_departements
            SELECT
                code_insee,
                code_insee_de_la_region AS code_region,
                nom_officiel            AS nom,
                geom                    AS geometry,
                CASE
                    WHEN ST_IsValid(ST_Simplify(geom, 0.01)) THEN ST_Simplify(geom, 0.01)
                    ELSE geom
                END AS geometry_simplified_national,
                CASE
                    WHEN ST_IsValid(ST_Simplify(geom, 0.001)) THEN ST_Simplify(geom, 0.001)
                    ELSE geom
                END AS geometry_simplified_departemental
            FROM ST_Read('{path_sql}')
        """)
        logger.debug("Batch inséré : %s", batch_path.name)

    count = con.execute("SELECT COUNT(*) FROM geographies_departements").fetchone()[0]
    if count != 101:
        raise RuntimeError(
            f"Nombre de départements incorrect : {count} (attendu exactement 101). "
            "Utiliser --force pour re-télécharger si des batches corrompus sont en cache."
        )

    # Vérification Corse
    corse = {
        r[0]
        for r in con.execute(
            "SELECT code_insee FROM geographies_departements WHERE code_insee IN ('2A', '2B')"
        ).fetchall()
    }
    if corse != {"2A", "2B"}:
        raise RuntimeError(f"Codes Corse manquants ou incorrects : trouvé {corse}")

    # Vérification FK conceptuelle : tous les code_region dans geographies_regions
    orphelins = con.execute("""
        SELECT DISTINCT d.code_region
        FROM geographies_departements d
        WHERE d.code_region NOT IN (SELECT code_insee FROM geographies_regions)
    """).fetchall()
    if orphelins:
        codes = [r[0] for r in orphelins]
        raise RuntimeError(
            f"FK violée : {len(codes)} code_region absent(s) de geographies_regions : {codes}. "
            "Charger les régions d'abord (--level region ou lancement complet)."
        )

    codes = [
        r[0]
        for r in con.execute(
            "SELECT code_insee FROM geographies_departements ORDER BY code_insee"
        ).fetchall()
    ]
    logger.info("Chargé %d départements (codes : %s … %s)", count, codes[0], codes[-1])

    con.execute(
        "DELETE FROM _etl_metadata WHERE table_name = 'geographies_departements'"
    )
    con.execute(
        "INSERT INTO _etl_metadata VALUES (?, NOW(), 'ADMINEXPRESS-COG.LATEST', ?)",
        ["geographies_departements", count],
    )


def _load_epci(con: duckdb.DuckDBPyConnection, force: bool = False) -> None:
    """Charge les ~1 250 EPCI dans geographies_epci.

    Source : fetch_admin_express("epci", dom=True) — WFS IGN.
    ⚠ dom=True ignoré côté WFS (codes_insee_des_departements_membres multi-valeurs,
    filtre CQL impossible — comportement documenté dans geo.py).
    Mapping nature → type_epci : CC/CA/ME/CU/EPT (CASE WHEN SQL, 5 valeurs connues 2026-05-17).
    code_departement_principal : NULL — dérivé post-load via UPDATE depuis geographies_communes.
    Simplification : geometry_simplified_epci (tol=0.0005).
    Écrit dans _etl_metadata après succès.
    """
    raw_dir = ROOT / "data" / "raw"
    batch_paths = list(
        fetch_admin_express(
            "epci", dom=True, force=force, batch_size=500, raw_dir=raw_dir
        )
    )

    con.execute("DROP TABLE IF EXISTS geographies_epci")
    con.execute("""
        CREATE TABLE geographies_epci (
            code_siren                 VARCHAR(9) NOT NULL,
            nom                        VARCHAR    NOT NULL,
            type_epci                  VARCHAR(5),
            code_departement_principal VARCHAR(3),
            geometry                   GEOMETRY,
            geometry_simplified_epci   GEOMETRY,
            UNIQUE (code_siren)
        )
    """)

    for batch_path in batch_paths:
        path_sql = str(batch_path).replace("'", "''")
        con.execute(f"""
            INSERT INTO geographies_epci
            SELECT
                code_siren,
                nom_officiel AS nom,
                CASE nature
                    WHEN 'Communauté de communes'          THEN 'CC'
                    WHEN 'Communauté d''agglomération'     THEN 'CA'
                    WHEN 'Métropole'                       THEN 'ME'
                    WHEN 'Communauté urbaine'              THEN 'CU'
                    WHEN 'Etablissement public territorial' THEN 'EPT'
                    ELSE NULL
                END AS type_epci,
                NULL::VARCHAR AS code_departement_principal,
                geom AS geometry,
                CASE
                    WHEN ST_IsValid(ST_Simplify(geom, 0.0005)) THEN ST_Simplify(geom, 0.0005)
                    ELSE geom
                END AS geometry_simplified_epci
            FROM ST_Read('{path_sql}')
        """)
        logger.debug("Batch inséré : %s", batch_path.name)

    count = con.execute("SELECT COUNT(*) FROM geographies_epci").fetchone()[0]
    if not (1250 <= count <= 1290):
        raise RuntimeError(
            f"Nombre d'EPCI hors fourchette [1250-1290] : {count}. "
            "Vérifier la source IGN ou utiliser --force pour re-télécharger."
        )

    # Détecter les types inconnus (nature non mappée → type_epci NULL)
    null_types = con.execute(
        "SELECT COUNT(*) FROM geographies_epci WHERE type_epci IS NULL"
    ).fetchone()[0]
    if null_types > 0:
        raise RuntimeError(
            f"{null_types} EPCI avec type_epci NULL — une nouvelle valeur 'nature' "
            "non mappée est apparue dans le WFS IGN. "
            "Ajouter la valeur manquante dans le CASE WHEN de _load_epci()."
        )

    # Vérification SIREN : tous 9 chars numériques
    mauvais_siren = con.execute("""
        SELECT code_siren FROM geographies_epci
        WHERE length(code_siren) != 9 OR regexp_full_match(code_siren, '[^0-9]')
    """).fetchall()
    if mauvais_siren:
        raise RuntimeError(
            f"SIREN non conformes (attendu 9 chiffres) : {[r[0] for r in mauvais_siren[:10]]}"
        )

    dist = con.execute(
        "SELECT type_epci, COUNT(*) FROM geographies_epci GROUP BY type_epci ORDER BY COUNT(*) DESC"
    ).fetchall()
    logger.info(
        "Chargé %d EPCI — distribution types : %s",
        count,
        ", ".join(f"{t}={n}" for t, n in dist),
    )

    con.execute("DELETE FROM _etl_metadata WHERE table_name = 'geographies_epci'")
    con.execute(
        "INSERT INTO _etl_metadata VALUES (?, NOW(), 'ADMINEXPRESS-COG.LATEST', ?)",
        ["geographies_epci", count],
    )


def _load_communes(
    con: duckdb.DuckDBPyConnection,
    force: bool = False,
    skip: bool = False,
) -> None:
    """Charge les ~35 000 communes dans geographies_communes.

    ⚠ GATE UTILISATEUR : affiche un input() avant de lancer le téléchargement
    (durée estimée 30–60 min). Sauter avec --skip-communes pour le debug.
    Reprise disque : si --force absent et batches data/raw/*commune*batch* présents, skip DL.
    Source : fetch_admin_express("commune", dom=True, batch_size=1000) — WFS IGN.
    Progress : log INFO toutes les 1 000 communes (un batch = un log).
    Simplification : geometry_simplified_communal (0.0005).
    Post-load : UPDATE geographies_epci.code_departement_principal depuis communes.
    """
    if skip:
        logger.info("Chargement communes ignoré (--skip-communes).")
        return

    print(
        "\n⚠  Chargement communes (~35 000 lignes) — durée estimée 30–60 min.\n"
        "   Utilisez --skip-communes pour ignorer cette étape.\n"
    )
    try:
        reponse = input("Continuer ? [oui/non] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        logger.info("Chargement communes annulé (entrée non-interactive ou Ctrl-C).")
        return
    if reponse != "oui":
        logger.info("Chargement communes annulé par l'utilisateur.")
        return

    raw_dir = ROOT / "data" / "raw"
    batch_paths = list(
        fetch_admin_express(
            "commune", dom=True, force=force, batch_size=1000, raw_dir=raw_dir
        )
    )

    con.execute("DROP TABLE IF EXISTS geographies_communes")
    con.execute("""
        CREATE TABLE geographies_communes (
            code_insee                   VARCHAR(5) NOT NULL,
            nom                          VARCHAR    NOT NULL,
            code_departement             VARCHAR(3),
            code_region                  VARCHAR(3),
            code_epci                    VARCHAR(9),
            geometry                     GEOMETRY,
            geometry_simplified_communal GEOMETRY,
            UNIQUE (code_insee)
        )
    """)

    for batch_path in batch_paths:
        path_sql = str(batch_path).replace("'", "''")
        con.execute(f"""
            INSERT INTO geographies_communes
            SELECT
                code_insee,
                nom_officiel              AS nom,
                code_insee_du_departement AS code_departement,
                code_insee_de_la_region   AS code_region,
                codes_siren_des_epci      AS code_epci,
                geom                      AS geometry,
                CASE
                    WHEN ST_IsValid(ST_Simplify(geom, 0.0005)) THEN ST_Simplify(geom, 0.0005)
                    ELSE geom
                END AS geometry_simplified_communal
            FROM ST_Read('{path_sql}')
        """)
        running = con.execute("SELECT COUNT(*) FROM geographies_communes").fetchone()[0]
        logger.info("Batch %s inséré — %d communes cumulées", batch_path.name, running)

    count = con.execute("SELECT COUNT(*) FROM geographies_communes").fetchone()[0]
    if not (34000 <= count <= 36000):
        raise RuntimeError(
            f"Nombre de communes hors fourchette [34000-36000] : {count}. "
            "Vérifier la source IGN ou utiliser --force pour re-télécharger."
        )
    logger.info("Chargé %d communes.", count)

    # Dériver code_departement_principal des EPCI depuis les communes
    con.execute("""
        UPDATE geographies_epci
        SET code_departement_principal = (
            SELECT c.code_departement
            FROM geographies_communes c
            WHERE c.code_epci = geographies_epci.code_siren
              AND c.code_departement IS NOT NULL
            GROUP BY c.code_departement
            ORDER BY COUNT(*) DESC
            LIMIT 1
        )
    """)
    updated = con.execute(
        "SELECT COUNT(*) FROM geographies_epci WHERE code_departement_principal IS NOT NULL"
    ).fetchone()[0]
    logger.info("code_departement_principal renseigné pour %d EPCI.", updated)

    con.execute("DELETE FROM _etl_metadata WHERE table_name = 'geographies_communes'")
    con.execute(
        "INSERT INTO _etl_metadata VALUES (?, NOW(), 'ADMINEXPRESS-COG.LATEST', ?)",
        ["geographies_communes", count],
    )


def _load_arrondissements_municipaux(
    con: duckdb.DuckDBPyConnection, force: bool = False
) -> None:
    """Charge les 45 arrondissements municipaux (Paris 20, Lyon 9, Marseille 16).

    Source : fetch_admin_express("arrondissement_municipal", dom=False) — WFS IGN.
    code_commune_mere : champ WFS code_insee_de_la_commune_de_rattach (ex: 75056).
    code_departement : LEFT(code_insee, 2) — 75, 69, 13 uniquement.
    Même tolérance de simplification que communes : geometry_simplified_communal (0.0005).
    Écrit dans _etl_metadata après succès.
    """
    raw_dir = ROOT / "data" / "raw"
    batch_paths = list(
        fetch_admin_express(
            "arrondissement_municipal", dom=False, force=force, raw_dir=raw_dir
        )
    )

    con.execute("DROP TABLE IF EXISTS geographies_arrondissements_municipaux")
    con.execute("""
        CREATE TABLE geographies_arrondissements_municipaux (
            code_insee                   VARCHAR(5) NOT NULL,
            nom                          VARCHAR    NOT NULL,
            code_commune_mere            VARCHAR(5) NOT NULL,
            code_departement             VARCHAR(3),
            geometry                     GEOMETRY,
            geometry_simplified_communal GEOMETRY,
            UNIQUE (code_insee)
        )
    """)

    for batch_path in batch_paths:
        path_sql = str(batch_path).replace("'", "''")
        con.execute(f"""
            INSERT INTO geographies_arrondissements_municipaux
            SELECT
                code_insee,
                nom_officiel                        AS nom,
                code_insee_de_la_commune_de_rattach AS code_commune_mere,
                LEFT(code_insee, 2)                 AS code_departement,
                geom                                AS geometry,
                CASE
                    WHEN ST_IsValid(ST_Simplify(geom, 0.0005)) THEN ST_Simplify(geom, 0.0005)
                    ELSE geom
                END AS geometry_simplified_communal
            FROM ST_Read('{path_sql}')
        """)

    count = con.execute(
        "SELECT COUNT(*) FROM geographies_arrondissements_municipaux"
    ).fetchone()[0]
    if not (44 <= count <= 46):
        logger.warning(
            "Nombre d'arrondissements inattendu : %d (attendu 45 = Paris 20 + Lyon 9 + Marseille 16).",
            count,
        )
    logger.info("Chargé %d arrondissements municipaux.", count)

    con.execute(
        "DELETE FROM _etl_metadata WHERE table_name = 'geographies_arrondissements_municipaux'"
    )
    con.execute(
        "INSERT INTO _etl_metadata VALUES (?, NOW(), 'ADMINEXPRESS-COG.LATEST', ?)",
        ["geographies_arrondissements_municipaux", count],
    )


def _load_circonscriptions(con: duckdb.DuckDBPyConnection, force: bool = False) -> None:
    """Charge les 559 circonscriptions législatives dans geographies_circonscriptions.

    Source : fetch_circonscriptions_legislatives() — data.gouv.fr (jerome-desboeufs).
    Code format : '{dept}-{num:02d}' — ex: '01-04', '971-01'.
    559 features = 539 métro + 20 DROM/SPM (18 hors-scope : FE + COM absents de la source).
    Simplification : geometry_simplified_circo (0.001).
    Le GeoJSON normalisé est écrit dans un fichier temporaire pour ST_Read.
    Écrit dans _etl_metadata après succès.
    """
    raw_dir = ROOT / "data" / "raw"
    geojson = fetch_circonscriptions_legislatives(force=force, raw_dir=raw_dir)

    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".geojson",
            delete=False,
            encoding="utf-8",
            dir=raw_dir,
        ) as f:
            json.dump(geojson, f, ensure_ascii=False)
            tmp_path = Path(f.name)

        con.execute("DROP TABLE IF EXISTS geographies_circonscriptions")
        con.execute("""
            CREATE TABLE geographies_circonscriptions (
                code                      VARCHAR(6) NOT NULL,
                nom                       VARCHAR,
                code_departement          VARCHAR(3),
                nom_departement           VARCHAR,
                geometry                  GEOMETRY,
                geometry_simplified_circo GEOMETRY,
                UNIQUE (code)
            )
        """)

        path_sql = str(tmp_path).replace("'", "''")
        con.execute(f"""
            INSERT INTO geographies_circonscriptions
            SELECT
                code,
                nom,
                code_departement,
                nom_departement,
                geom AS geometry,
                CASE
                    WHEN ST_IsValid(ST_Simplify(geom, 0.001)) THEN ST_Simplify(geom, 0.001)
                    ELSE geom
                END AS geometry_simplified_circo
            FROM ST_Read('{path_sql}')
        """)
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)

    count = con.execute("SELECT COUNT(*) FROM geographies_circonscriptions").fetchone()[
        0
    ]
    if not (550 <= count <= 565):
        raise RuntimeError(
            f"Nombre de circonscriptions hors fourchette [550-565] : {count}. "
            "Vérifier la source ou utiliser --force pour re-télécharger."
        )
    logger.info("Chargé %d circonscriptions législatives.", count)

    con.execute(
        "DELETE FROM _etl_metadata WHERE table_name = 'geographies_circonscriptions'"
    )
    con.execute(
        "INSERT INTO _etl_metadata VALUES (?, NOW(), 'data.gouv.fr/jerome-desboeufs', ?)",
        ["geographies_circonscriptions", count],
    )


def _load_populations(
    con: duckdb.DuckDBPyConnection,
    millesimes: list[int],
    force: bool = False,
) -> None:
    """Charge les populations municipales INSEE pour chaque millésime.

    Source : fetch_populations(annee) — DS_POPULATIONS_HISTORIQUES Mélodi INSEE.
    Idempotence : skip si COUNT(*) WHERE annee=X > 0 et force=False.
    Avec --force : DELETE WHERE annee=X AND source='DS_POPULATIONS_HISTORIQUES' + re-INSERT.
    comptee_a_part et totale resteront NULL (PCAP absent de la source, voir TODO v2 insee_populations.py).
    Écrit dans _etl_metadata après chaque millésime chargé.
    """
    raw_dir = ROOT / "data" / "raw"

    for annee in millesimes:
        existing = con.execute(
            "SELECT COUNT(*) FROM populations WHERE annee = ?", [annee]
        ).fetchone()[0]

        if existing > 0 and not force:
            logger.info(
                "Populations %d déjà chargées (%d lignes) — ignoré (--force pour recréer).",
                annee,
                existing,
            )
            continue

        if force and existing > 0:
            con.execute(
                "DELETE FROM populations WHERE annee = ? AND source = 'DS_POPULATIONS_HISTORIQUES'",
                [annee],
            )
            logger.info("Populations %d supprimées pour re-chargement.", annee)

        df = fetch_populations(annee, force=force, raw_dir=raw_dir)

        con.register("_pop_temp", df)
        con.execute("""
            INSERT INTO populations (code_insee_commune, annee, municipale, comptee_a_part, totale, source)
            SELECT code_insee_commune, annee, municipale, comptee_a_part, totale,
                   'DS_POPULATIONS_HISTORIQUES'
            FROM _pop_temp
        """)
        con.unregister("_pop_temp")

        count = con.execute(
            "SELECT COUNT(*) FROM populations WHERE annee = ?", [annee]
        ).fetchone()[0]
        logger.info("Populations %d chargées : %d communes.", annee, count)

        meta_key = f"populations_{annee}"
        con.execute("DELETE FROM _etl_metadata WHERE table_name = ?", [meta_key])
        con.execute(
            "INSERT INTO _etl_metadata VALUES (?, NOW(), 'DS_POPULATIONS_HISTORIQUES', ?)",
            [meta_key, count],
        )


# ── Vues SQL ──────────────────────────────────────────────────────────────────


def _create_views(con: duckdb.DuckDBPyConnection) -> None:
    """Crée les 3 vues d'agrégation population → territoire.

    Appelée après tous les _load_* : dépend de geographies_communes + populations.
    SUM(comptee_a_part) et SUM(totale) retournent NULL tant que PCAP absent.

    Vues :
        v_population_region     — SUM par code_region
        v_population_departement — SUM par code_departement
        v_population_epci       — SUM par code_epci (communes avec EPCI uniquement)
    """
    con.execute("""
        CREATE OR REPLACE VIEW v_population_region AS
        SELECT
            r.code_insee          AS code_region,
            r.nom                 AS nom_region,
            p.annee,
            SUM(p.municipale)         AS population_municipale,
            SUM(p.comptee_a_part)     AS population_comptee_a_part,
            SUM(p.totale)             AS population_totale
        FROM geographies_communes c
        JOIN populations p ON p.code_insee_commune = c.code_insee
        JOIN geographies_regions r ON r.code_insee = c.code_region
        GROUP BY r.code_insee, r.nom, p.annee
    """)

    con.execute("""
        CREATE OR REPLACE VIEW v_population_departement AS
        SELECT
            d.code_insee          AS code_departement,
            d.nom                 AS nom_departement,
            p.annee,
            SUM(p.municipale)         AS population_municipale,
            SUM(p.comptee_a_part)     AS population_comptee_a_part,
            SUM(p.totale)             AS population_totale
        FROM geographies_communes c
        JOIN populations p ON p.code_insee_commune = c.code_insee
        JOIN geographies_departements d ON d.code_insee = c.code_departement
        GROUP BY d.code_insee, d.nom, p.annee
    """)

    con.execute("""
        CREATE OR REPLACE VIEW v_population_epci AS
        SELECT
            e.code_siren          AS code_epci,
            e.nom                 AS nom_epci,
            e.type_epci,
            p.annee,
            SUM(p.municipale)         AS population_municipale,
            SUM(p.comptee_a_part)     AS population_comptee_a_part,
            SUM(p.totale)             AS population_totale
        FROM geographies_communes c
        JOIN populations p ON p.code_insee_commune = c.code_insee
        JOIN geographies_epci e ON e.code_siren = c.code_epci
        WHERE c.code_epci IS NOT NULL
        GROUP BY e.code_siren, e.nom, e.type_epci, p.annee
    """)

    logger.info(
        "3 vues créées : v_population_region, v_population_departement, v_population_epci."
    )


# ── CLI ───────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ETL territorial complet : IGN ADMIN-EXPRESS + INSEE populations → DuckDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemples :\n"
            "  uv run python scripts/etl_territoires.py --millesimes 2023 --skip-communes\n"
            "  uv run python scripts/etl_territoires.py --force --level departement"
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-télécharger les sources même si les fichiers locaux existent",
    )
    parser.add_argument(
        "--skip-communes",
        action="store_true",
        help="Sauter le chargement communes (~35 000 rows, 30-60 min) — pour debug",
    )
    parser.add_argument(
        "--millesimes",
        default="2013,2018,2023",
        metavar="ANNEES",
        help="Millésimes INSEE séparés par virgule (défaut: 2013,2018,2023)",
    )
    parser.add_argument(
        "--level",
        choices=[
            "region",
            "departement",
            "epci",
            "commune",
            "arrondissement_municipal",
            "circonscription",
        ],
        default=None,
        metavar="LEVEL",
        help="Charger un seul niveau géographique — debug uniquement",
    )
    args = parser.parse_args()

    try:
        millesimes = [int(m.strip()) for m in args.millesimes.split(",")]
    except ValueError:
        parser.error(
            f"--millesimes invalide : {args.millesimes!r} — attendu ex: '2013,2018,2023'"
        )

    con = _open_connection()
    _create_schema(con)

    if args.level is None:
        _load_regions(con, force=args.force)
        _load_departements(con, force=args.force)
        _load_epci(con, force=args.force)
        _load_communes(con, force=args.force, skip=args.skip_communes)
        _load_arrondissements_municipaux(con, force=args.force)
        _load_circonscriptions(con, force=args.force)
        _load_populations(con, millesimes=millesimes, force=args.force)
        _create_views(con)
    else:
        _level_dispatch: dict[str, object] = {
            "region": lambda: _load_regions(con, force=args.force),
            "departement": lambda: _load_departements(con, force=args.force),
            "epci": lambda: _load_epci(con, force=args.force),
            "commune": lambda: _load_communes(
                con, force=args.force, skip=args.skip_communes
            ),
            "arrondissement_municipal": lambda: _load_arrondissements_municipaux(
                con, force=args.force
            ),
            "circonscription": lambda: _load_circonscriptions(con, force=args.force),
        }
        _level_dispatch[args.level]()  # type: ignore[operator]

    con.close()
    logger.info("ETL terminé.")


if __name__ == "__main__":
    main()
