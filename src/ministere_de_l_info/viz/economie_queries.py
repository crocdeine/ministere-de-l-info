"""Requêtes DuckDB cachées pour la page Économie (Phase E3 + E+ + E++).

Fonctions exportées
-------------------
- is_data_loaded()              : True si les 2 tables économiques contiennent des données
- is_contexte_loaded()          : True si economie_contexte contient des données
- get_annees_par_indicateur()   : dict indicateur → années disponibles (toutes sources)
- get_indicateurs()             : dict code → libellé des 8 indicateurs
- get_scores_commune()          : indicateur × commune HdF pour une année
- get_economie_commune()        : tous indicateurs pour une commune, toutes années
- get_croisement_eco_elections(): croisement économie × présidentielles (T1 ou T2)
- annees_croisement_exploitables(): années de présidentielle avec données éco en n-1
- get_annees_presidentielles()  : années de présidentielle en base
- get_evolution_hdf()           : évolution agrégée HdF (3 indicateurs Filosofi/RP)
- get_evolution_rsa_hdf()       : évolution total foyers RSA HdF (CNAF 2020-2024)
- get_contexte_hdf_vs_france()  : HdF vs France par indicateur macro (Eurostat)
- get_deserts_medicaux()        : communes HdF desert_medical=TRUE + geojson
- get_desindustrialisation_commune() : effectifs industrie HdF ou par commune 2006-2025
- get_top_communes_rsa()        : top N communes par foyers RSA pour une année
- get_communes_industrie_hdf()  : liste communes HdF avec données emploi industriel
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import polars as pl
import streamlit as st

from ministere_de_l_info.config import get_settings

DB_PATH: Path = get_settings().db_path

# Ensemble validé pour éviter les injections SQL dans les requêtes f-string
_INDICATEURS_VALIDES = frozenset(
    {
        "taux_pauvrete",
        "niveau_vie_median",
        "tx_chomage_dec",
        "part_ouvriers_employes",
        "part_emploi_industriel",
        "part_logements_sociaux",
        "nb_foyers_rsa",
        "apl_medecins",
    }
)
# Indicateurs provenant de economie_social (Phase E+) — routage alternatif
_INDICATEURS_SOCIAL = frozenset({"nb_foyers_rsa", "apl_medecins"})
# Indicateurs du Recensement (economie_rp) — lus directement dans la table RP :
# v_economie_commune part de Filosofi (2017-2021) et perd les millésimes RP 2015-2016
# (audit I5).
_INDICATEURS_RP = frozenset(
    {"tx_chomage_dec", "part_ouvriers_employes", "part_emploi_industriel", "part_logements_sociaux"}
)
# Indicateurs macro contexte (Phase E++) — economie_contexte / Eurostat
_INDICATEURS_CONTEXTE = frozenset({"tx_chomage_bit", "pib_eur_hab"})


def _open_ro() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    con.execute("LOAD spatial")
    return con


def is_base_disponible() -> bool:
    """True si le fichier DuckDB existe (non mis en cache : test de fichier immédiat)."""
    return DB_PATH.exists()


@st.cache_data(ttl=60)
def is_data_loaded() -> bool:
    """Vérifie que economie_filosofi et economie_rp contiennent des données.

    Renvoie False (au lieu de lever une exception) si la base est absente
    ou si les tables économiques n'existent pas.
    """
    if not DB_PATH.exists():
        return False
    try:
        con = _open_ro()
    except duckdb.Error:
        return False
    try:
        n_f = con.execute("SELECT COUNT(*) FROM economie_filosofi").fetchone()[0]
        n_r = con.execute("SELECT COUNT(*) FROM economie_rp").fetchone()[0]
        return int(n_f) > 0 and int(n_r) > 0
    except duckdb.Error:
        return False
    finally:
        con.close()


@st.cache_data(ttl=60)
def is_contexte_loaded() -> bool:
    """Vérifie que economie_contexte contient des données."""
    con = _open_ro()
    try:
        n = con.execute("SELECT COUNT(*) FROM economie_contexte").fetchone()[0]
        return int(n) > 0
    except duckdb.CatalogException:
        return False
    finally:
        con.close()


@st.cache_data(ttl=3600)
def get_contexte_hdf_vs_france(indicateur: str) -> pl.DataFrame:
    """Valeurs HdF et France pour un indicateur macro (v_contexte_hdf_vs_france)."""
    if indicateur not in _INDICATEURS_CONTEXTE:
        raise ValueError(f"Indicateur contexte inconnu : {indicateur}")
    con = _open_ro()
    try:
        rows = con.execute(
            "SELECT annee, valeur_hdf, valeur_france, ecart_hdf_france "
            "FROM v_contexte_hdf_vs_france "
            "WHERE indicateur = ? "
            "AND NOT (valeur_hdf IS NULL AND valeur_france IS NULL) "
            "ORDER BY annee ASC",
            [indicateur],
        ).fetchall()
    finally:
        con.close()
    if not rows:
        return pl.DataFrame(
            schema={
                "annee": pl.Int64,
                "valeur_hdf": pl.Float64,
                "valeur_france": pl.Float64,
                "ecart_hdf_france": pl.Float64,
            }
        )
    return pl.DataFrame(
        {
            "annee": [int(r[0]) for r in rows],
            "valeur_hdf": [float(r[1]) if r[1] is not None else None for r in rows],
            "valeur_france": [float(r[2]) if r[2] is not None else None for r in rows],
            "ecart_hdf_france": [float(r[3]) if r[3] is not None else None for r in rows],
        }
    )


@st.cache_data
def get_indicateurs() -> dict[str, str]:
    """Dictionnaire code → libellé des 8 indicateurs disponibles."""
    return {
        "taux_pauvrete": "Taux de pauvreté (%)",
        "niveau_vie_median": "Niveau de vie médian (€)",
        "tx_chomage_dec": "Taux de chômage (RP, %)",
        "part_ouvriers_employes": "Part ouvriers + employés (%)",
        "part_emploi_industriel": "Part emploi industriel (%)",
        "part_logements_sociaux": "Part logements sociaux (%)",
        "nb_foyers_rsa": "Allocataires RSA (nombre de foyers)",
        "apl_medecins": "Accessibilité médecins (APL)",
    }


@st.cache_data(ttl=3600, show_spinner="Chargement des données communales…")
def get_scores_commune(annee: int, indicateur: str) -> pl.DataFrame:
    """Valeur d'un indicateur par commune HdF pour une année.

    Filosofi : jointure sur economie_filosofi ; RP : jointure sur economie_rp
    (tous les millésimes RP, y compris ceux sans Filosofi — audit I5) ; secret
    statistique INSEE de la source concernée.
    nb_foyers_rsa, apl_medecins : jointure sur economie_social (secret=FALSE).
    Retourne code_commune, nom_commune, valeur, secret, geojson.
    """
    if indicateur not in _INDICATEURS_VALIDES:
        raise ValueError(f"Indicateur inconnu : {indicateur}")

    con = _open_ro()
    try:
        if indicateur in _INDICATEURS_SOCIAL:
            rows = con.execute(  # noqa: S608
                f"""
                SELECT
                    gc.code_insee                                   AS code_commune,
                    gc.nom                                          AS nom_commune,
                    s.{indicateur}                                  AS valeur,
                    FALSE                                           AS secret,
                    ST_AsGeoJSON(gc.geometry_simplified_communal)   AS geojson
                FROM geographies_communes gc
                LEFT JOIN economie_social s
                    ON gc.code_insee = s.code_commune AND s.annee = ?
                WHERE gc.code_region = '32'
                ORDER BY gc.nom
                """,
                [annee],
            ).fetchall()
        elif indicateur in _INDICATEURS_RP:
            rows = con.execute(  # noqa: S608
                f"""
                SELECT
                    gc.code_insee                                   AS code_commune,
                    gc.nom                                          AS nom_commune,
                    r.{indicateur}                                  AS valeur,
                    COALESCE(r.secret, FALSE)                       AS secret,
                    ST_AsGeoJSON(gc.geometry_simplified_communal)   AS geojson
                FROM geographies_communes gc
                LEFT JOIN economie_rp r
                    ON gc.code_insee = r.code_commune AND r.annee_millesime = ?
                WHERE gc.code_region = '32'
                ORDER BY gc.nom
                """,
                [annee],
            ).fetchall()
        else:
            rows = con.execute(  # noqa: S608
                f"""
                SELECT
                    gc.code_insee                                   AS code_commune,
                    gc.nom                                          AS nom_commune,
                    f.{indicateur}                                  AS valeur,
                    COALESCE(f.secret, FALSE)                       AS secret,
                    ST_AsGeoJSON(gc.geometry_simplified_communal)   AS geojson
                FROM geographies_communes gc
                LEFT JOIN economie_filosofi f
                    ON gc.code_insee = f.code_commune AND f.annee = ?
                WHERE gc.code_region = '32'
                ORDER BY gc.nom
                """,
                [annee],
            ).fetchall()
    finally:
        con.close()

    if not rows:
        return pl.DataFrame(
            schema={
                "code_commune": pl.Utf8,
                "nom_commune": pl.Utf8,
                "valeur": pl.Float64,
                "secret": pl.Boolean,
                "geojson": pl.Utf8,
            }
        )
    return pl.DataFrame(
        {
            "code_commune": [r[0] for r in rows],
            "nom_commune": [r[1] for r in rows],
            "valeur": [float(r[2]) if r[2] is not None else None for r in rows],
            "secret": [bool(r[3]) for r in rows],
            "geojson": [r[4] for r in rows],
        }
    )


@st.cache_data(ttl=3600)
def get_economie_commune(code_commune: str) -> pl.DataFrame:
    """Tous les indicateurs pour une commune donnée, toutes années disponibles.

    Union des années Filosofi et RP (FULL OUTER JOIN) : les millésimes RP sans
    Filosofi (2015-2016) sont conservés (audit I5).
    """
    con = _open_ro()
    try:
        rows = con.execute(
            """
            WITH f AS (SELECT * FROM economie_filosofi WHERE code_commune = ?),
                 r AS (SELECT * FROM economie_rp WHERE code_commune = ?)
            SELECT
                COALESCE(f.annee, r.annee_millesime)            AS annee,
                f.taux_pauvrete,
                f.niveau_vie_median,
                r.tx_chomage_dec,
                r.part_ouvriers_employes,
                r.part_emploi_industriel,
                r.part_logements_sociaux,
                (COALESCE(f.secret, FALSE) OR COALESCE(r.secret, FALSE)) AS secret
            FROM f
            FULL OUTER JOIN r ON f.annee = r.annee_millesime
            ORDER BY annee
            """,
            [code_commune, code_commune],
        ).fetchall()
    finally:
        con.close()

    if not rows:
        return pl.DataFrame(
            schema={
                "annee": pl.Int64,
                "taux_pauvrete": pl.Float64,
                "niveau_vie_median": pl.Float64,
                "tx_chomage_dec": pl.Float64,
                "part_ouvriers_employes": pl.Float64,
                "part_emploi_industriel": pl.Float64,
                "part_logements_sociaux": pl.Float64,
                "secret": pl.Boolean,
            }
        )
    return pl.DataFrame(
        {
            "annee": [int(r[0]) for r in rows],
            "taux_pauvrete": [float(r[1]) if r[1] is not None else None for r in rows],
            "niveau_vie_median": [float(r[2]) if r[2] is not None else None for r in rows],
            "tx_chomage_dec": [float(r[3]) if r[3] is not None else None for r in rows],
            "part_ouvriers_employes": [float(r[4]) if r[4] is not None else None for r in rows],
            "part_emploi_industriel": [float(r[5]) if r[5] is not None else None for r in rows],
            "part_logements_sociaux": [float(r[6]) if r[6] is not None else None for r in rows],
            "secret": [bool(r[7]) for r in rows],
        }
    )


@st.cache_data(ttl=3600, show_spinner="Chargement du croisement économie × élections…")
def get_croisement_eco_elections(
    annee_election: int,
    bloc: str | None = None,
    tour: int = 2,
) -> pl.DataFrame:
    """Croisement indicateurs économiques × résultats présidentiels par commune.

    Utilise v_scores_commune_pres + v_participation_commune_pres (tour choisi) pour
    calculer pct_voix, et les indicateurs économiques de l'année n-1 lus directement
    dans economie_filosofi et economie_rp (chaque source avec ses propres millésimes :
    RP 2016 disponible pour la présidentielle 2017 même sans Filosofi 2016).
    """
    if tour not in (1, 2):
        raise ValueError(f"Tour invalide : {tour}")
    con = _open_ro()
    try:
        sql = """
            SELECT
                e.code_commune,
                gc.nom                                            AS nom_commune,
                e.bloc,
                ROUND(100.0 * e.voix / NULLIF(p.exprimes, 0), 2) AS pct_voix,
                f.taux_pauvrete,
                f.niveau_vie_median,
                r.tx_chomage_dec,
                r.part_ouvriers_employes,
                r.part_emploi_industriel,
                r.part_logements_sociaux,
                r.pop_active
            FROM v_scores_commune_pres e
            LEFT JOIN v_participation_commune_pres p
                ON p.code_commune = e.code_commune
                AND p.annee = e.annee AND p.tour = e.tour
            LEFT JOIN economie_filosofi f
                ON f.code_commune = e.code_commune AND f.annee = e.annee - 1
            LEFT JOIN economie_rp r
                ON r.code_commune = e.code_commune AND r.annee_millesime = e.annee - 1
            LEFT JOIN geographies_communes gc ON gc.code_insee = e.code_commune
            WHERE e.annee = ? AND e.tour = ?
        """
        params: list = [annee_election, tour]
        if bloc is not None:
            sql += " AND e.bloc = ?"
            params.append(bloc)
        sql += " ORDER BY e.code_commune, e.bloc"
        rows = con.execute(sql, params).fetchall()  # noqa: S608
    finally:
        con.close()

    if not rows:
        return pl.DataFrame(
            schema={
                "code_commune": pl.Utf8,
                "nom_commune": pl.Utf8,
                "bloc": pl.Utf8,
                "pct_voix": pl.Float64,
                "taux_pauvrete": pl.Float64,
                "niveau_vie_median": pl.Float64,
                "tx_chomage_dec": pl.Float64,
                "part_ouvriers_employes": pl.Float64,
                "part_emploi_industriel": pl.Float64,
                "part_logements_sociaux": pl.Float64,
                "pop_active": pl.Int64,
            }
        )
    return pl.DataFrame(
        {
            "code_commune": [r[0] for r in rows],
            "nom_commune": [r[1] for r in rows],
            "bloc": [r[2] for r in rows],
            "pct_voix": [float(r[3]) if r[3] is not None else None for r in rows],
            "taux_pauvrete": [float(r[4]) if r[4] is not None else None for r in rows],
            "niveau_vie_median": [float(r[5]) if r[5] is not None else None for r in rows],
            "tx_chomage_dec": [float(r[6]) if r[6] is not None else None for r in rows],
            "part_ouvriers_employes": [float(r[7]) if r[7] is not None else None for r in rows],
            "part_emploi_industriel": [float(r[8]) if r[8] is not None else None for r in rows],
            "part_logements_sociaux": [float(r[9]) if r[9] is not None else None for r in rows],
            "pop_active": [int(r[10]) if r[10] is not None else None for r in rows],
        }
    )


_SQL_EVOLUTION_HDF = """
    WITH fil AS (
        SELECT
            annee,
            AVG(taux_pauvrete)          AS taux_pauvrete_moyen,
            MEDIAN(niveau_vie_median)   AS niveau_vie_median_communes
        FROM economie_filosofi
        GROUP BY annee
    ),
    rp AS (
        SELECT
            annee_millesime AS annee,
            SUM(tx_chomage_dec * pop_active)
                FILTER (WHERE tx_chomage_dec IS NOT NULL AND pop_active > 0)
            / NULLIF(
                SUM(pop_active) FILTER (WHERE tx_chomage_dec IS NOT NULL AND pop_active > 0),
                0
            )                           AS tx_chomage_pondere
        FROM economie_rp
        GROUP BY annee_millesime
    )
    SELECT
        COALESCE(fil.annee, rp.annee)   AS annee,
        fil.taux_pauvrete_moyen,
        fil.niveau_vie_median_communes,
        rp.tx_chomage_pondere
    FROM fil
    FULL OUTER JOIN rp ON fil.annee = rp.annee
    ORDER BY annee
"""


def _evolution_hdf(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    """Agrégats HdF par année (requête non mise en cache, testable sur base en mémoire).

    - taux_pauvrete_moyen : moyenne NON pondérée des taux communaux (Filosofi ne
      fournit pas en base le nombre de personnes pour pondérer) ;
    - niveau_vie_median_communes : médiane des médianes communales (et non le
      niveau de vie médian régional, qui n'est pas calculable depuis les communes) ;
    - tx_chomage_pondere : taux communaux pondérés par les actifs de 15-64 ans
      (pop_active, RP), soit ≈ Σ chômeurs / Σ actifs ; tous les millésimes RP.
    """
    return (
        con.execute(_SQL_EVOLUTION_HDF)
        .pl()
        .with_columns(
            pl.col("annee").cast(pl.Int64),
            pl.col("taux_pauvrete_moyen").cast(pl.Float64),
            pl.col("niveau_vie_median_communes").cast(pl.Float64),
            pl.col("tx_chomage_pondere").cast(pl.Float64),
        )
    )


@st.cache_data(ttl=3600)
def get_evolution_hdf() -> pl.DataFrame:
    """Évolution des indicateurs agrégés HdF par année (voir `_evolution_hdf`)."""
    con = _open_ro()
    try:
        return _evolution_hdf(con)
    finally:
        con.close()


def annees_croisement_exploitables(
    annees_election: list[int], annees_indicateur: list[int]
) -> list[int]:
    """Années de présidentielle pour lesquelles l'indicateur existe en n-1 (croisement)."""
    disponibles = set(annees_indicateur)
    return sorted(a for a in annees_election if a - 1 in disponibles)


@st.cache_data(ttl=3600)
def get_annees_presidentielles() -> list[int]:
    """Années de présidentielle présentes en base (ordre croissant)."""
    con = _open_ro()
    try:
        rows = con.execute(
            "SELECT DISTINCT annee FROM elections WHERE type_scrutin = 'pres' ORDER BY annee"
        ).fetchall()
    finally:
        con.close()
    return [int(r[0]) for r in rows]


# Indicateur → (table, colonne année). Liste blanche : noms injectés dans le SQL.
_SOURCES_ANNEES: dict[str, tuple[str, str]] = {
    "taux_pauvrete": ("economie_filosofi", "annee"),
    "niveau_vie_median": ("economie_filosofi", "annee"),
    "tx_chomage_dec": ("economie_rp", "annee_millesime"),
    "part_ouvriers_employes": ("economie_rp", "annee_millesime"),
    "part_emploi_industriel": ("economie_rp", "annee_millesime"),
    "part_logements_sociaux": ("economie_rp", "annee_millesime"),
    "nb_foyers_rsa": ("economie_social", "annee"),
    "apl_medecins": ("economie_social", "annee"),
}


@st.cache_data(ttl=3600)
def get_annees_par_indicateur() -> dict[str, list[int]]:
    """Années où l'indicateur a au moins une valeur non NULL.

    Un millésime chargé mais où l'indicateur n'est pas diffusé (ex. chômage RP 2015 et
    2016 si la clef source manque) n'est pas proposé : carte vide évitée.
    """
    con = _open_ro()
    try:
        return {
            indicateur: [
                int(r[0])
                for r in con.execute(
                    f"SELECT DISTINCT {col_annee} FROM {table} "
                    f"WHERE {indicateur} IS NOT NULL ORDER BY 1"
                ).fetchall()
            ]
            for indicateur, (table, col_annee) in _SOURCES_ANNEES.items()
        }
    finally:
        con.close()


@st.cache_data(ttl=3600)
def get_evolution_rsa_hdf() -> pl.DataFrame:
    """Évolution du total foyers RSA en HdF par année (CNAF 2020-2024)."""
    con = _open_ro()
    try:
        rows = con.execute(
            "SELECT annee, SUM(nb_foyers_rsa) AS total_foyers_rsa_hdf "
            "FROM economie_social WHERE nb_foyers_rsa IS NOT NULL "
            "GROUP BY annee ORDER BY annee"
        ).fetchall()
    finally:
        con.close()
    if not rows:
        return pl.DataFrame(schema={"annee": pl.Int64, "total_foyers_rsa_hdf": pl.Int64})
    return pl.DataFrame(
        {
            "annee": [int(r[0]) for r in rows],
            "total_foyers_rsa_hdf": [int(r[1]) if r[1] is not None else None for r in rows],
        }
    )


@st.cache_data(ttl=3600)
def get_deserts_medicaux() -> pl.DataFrame:
    """Communes HdF avec desert_medical=TRUE, APL et geojson."""
    con = _open_ro()
    try:
        rows = con.execute(
            "SELECT s.code_commune, gc.nom AS nom_commune, s.apl_medecins, "
            "ST_AsGeoJSON(gc.geometry_simplified_communal) AS geojson "
            "FROM economie_social s "
            "LEFT JOIN geographies_communes gc ON gc.code_insee = s.code_commune "
            "WHERE s.desert_medical = TRUE ORDER BY s.apl_medecins ASC"
        ).fetchall()
    finally:
        con.close()
    if not rows:
        return pl.DataFrame(
            schema={
                "code_commune": pl.Utf8,
                "nom_commune": pl.Utf8,
                "apl_medecins": pl.Float64,
                "geojson": pl.Utf8,
            }
        )
    return pl.DataFrame(
        {
            "code_commune": [r[0] for r in rows],
            "nom_commune": [r[1] for r in rows],
            "apl_medecins": [float(r[2]) if r[2] is not None else None for r in rows],
            "geojson": [r[3] for r in rows],
        }
    )


@st.cache_data(ttl=3600, show_spinner="Chargement données industrie…")
def get_desindustrialisation_commune(code_commune: str | None = None) -> pl.DataFrame:
    """Effectifs salariés industrie HdF par année.

    code_commune=None : agrégé HdF (SUM). Sinon : filtré sur une commune.
    Filtre : secteur_gs LIKE '%Industrie%'.
    """
    con = _open_ro()
    try:
        if code_commune is not None:
            rows = con.execute(
                "SELECT annee, SUM(nb_salaries) AS nb_salaries, "
                "SUM(nb_etablissements) AS nb_etablissements "
                "FROM economie_emploi_urssaf "
                "WHERE secteur_gs LIKE '%Industrie%' AND code_commune = ? "
                "GROUP BY annee ORDER BY annee",
                [code_commune],
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT annee, SUM(nb_salaries) AS nb_salaries, "
                "SUM(nb_etablissements) AS nb_etablissements "
                "FROM economie_emploi_urssaf "
                "WHERE secteur_gs LIKE '%Industrie%' "
                "GROUP BY annee ORDER BY annee"
            ).fetchall()
    finally:
        con.close()
    if not rows:
        return pl.DataFrame(
            schema={"annee": pl.Int64, "nb_salaries": pl.Int64, "nb_etablissements": pl.Int64}
        )
    return pl.DataFrame(
        {
            "annee": [int(r[0]) for r in rows],
            "nb_salaries": [int(r[1]) if r[1] is not None else None for r in rows],
            "nb_etablissements": [int(r[2]) if r[2] is not None else None for r in rows],
        }
    )


@st.cache_data(ttl=3600)
def get_top_communes_rsa(annee: int, n: int = 20) -> pl.DataFrame:
    """Top N communes HdF par nombre de foyers RSA pour une année."""
    con = _open_ro()
    try:
        rows = con.execute(
            "SELECT s.code_commune, COALESCE(gc.nom, s.code_commune) AS nom_commune, "
            "s.nb_foyers_rsa "
            "FROM economie_social s "
            "LEFT JOIN geographies_communes gc ON gc.code_insee = s.code_commune "
            "WHERE s.annee = ? AND s.nb_foyers_rsa IS NOT NULL "
            "ORDER BY s.nb_foyers_rsa DESC LIMIT ?",
            [annee, n],
        ).fetchall()
    finally:
        con.close()
    if not rows:
        return pl.DataFrame(
            schema={"code_commune": pl.Utf8, "nom_commune": pl.Utf8, "nb_foyers_rsa": pl.Int64}
        )
    return pl.DataFrame(
        {
            "code_commune": [r[0] for r in rows],
            "nom_commune": [r[1] for r in rows],
            "nb_foyers_rsa": [int(r[2]) if r[2] is not None else None for r in rows],
        }
    )


@st.cache_data(ttl=3600)
def get_communes_industrie_hdf() -> list[tuple[str, str]]:
    """Communes HdF ayant des données emploi industriel (code, nom)."""
    con = _open_ro()
    try:
        rows = con.execute(
            "SELECT DISTINCT u.code_commune, COALESCE(gc.nom, u.code_commune) "
            "FROM economie_emploi_urssaf u "
            "LEFT JOIN geographies_communes gc ON gc.code_insee = u.code_commune "
            "WHERE u.secteur_gs LIKE '%Industrie%' AND u.nb_salaries > 0 "
            "ORDER BY 2"
        ).fetchall()
    finally:
        con.close()
    return [(r[0], r[1]) for r in rows] if rows else []
