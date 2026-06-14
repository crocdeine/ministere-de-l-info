"""Requêtes DuckDB cachées pour la page Économie (Phase E3 + E+).

Fonctions exportées
-------------------
- is_data_loaded()              : True si les 2 tables économiques contiennent des données
- get_annees_par_indicateur()   : dict indicateur → années disponibles (toutes sources)
- get_indicateurs()             : dict code → libellé des 8 indicateurs
- get_scores_commune()          : indicateur × commune HdF pour une année
- get_economie_commune()        : tous indicateurs pour une commune, toutes années
- get_croisement_eco_elections(): croisement économie × présidentielles T2
- get_evolution_hdf()           : évolution agrégée HdF (3 indicateurs Filosofi/RP)
- get_evolution_rsa_hdf()       : évolution total foyers RSA HdF (CNAF 2020-2024)
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

DB_PATH: Path = Path(__file__).resolve().parents[3] / "data" / "ministere.duckdb"

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


def _open_ro() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    con.execute("LOAD spatial")
    return con


@st.cache_data(ttl=60)
def is_data_loaded() -> bool:
    """Vérifie que economie_filosofi et economie_rp contiennent des données."""
    con = _open_ro()
    try:
        n_f = con.execute("SELECT COUNT(*) FROM economie_filosofi").fetchone()[0]
        n_r = con.execute("SELECT COUNT(*) FROM economie_rp").fetchone()[0]
        return int(n_f) > 0 and int(n_r) > 0
    finally:
        con.close()


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
        "nb_foyers_rsa": "Allocataires RSA (foyers)",
        "apl_medecins": "Accessibilité médecins (APL)",
    }


@st.cache_data(ttl=3600, show_spinner="Chargement des données communales…")
def get_scores_commune(annee: int, indicateur: str) -> pl.DataFrame:
    """Valeur d'un indicateur par commune HdF pour une année.

    Filosofi/RP : jointure sur v_economie_commune (secret INSEE géré).
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
        else:
            rows = con.execute(  # noqa: S608
                f"""
                SELECT
                    gc.code_insee                                   AS code_commune,
                    gc.nom                                          AS nom_commune,
                    v.{indicateur}                                  AS valeur,
                    COALESCE(v.secret_partiel, FALSE)               AS secret,
                    ST_AsGeoJSON(gc.geometry_simplified_communal)   AS geojson
                FROM geographies_communes gc
                LEFT JOIN v_economie_commune v
                    ON gc.code_insee = v.code_commune AND v.annee = ?
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
    """Tous les indicateurs pour une commune donnée, toutes années disponibles."""
    con = _open_ro()
    try:
        rows = con.execute(
            """
            SELECT
                annee,
                taux_pauvrete,
                niveau_vie_median,
                tx_chomage_dec,
                part_ouvriers_employes,
                part_emploi_industriel,
                part_logements_sociaux,
                secret_partiel AS secret
            FROM v_economie_commune
            WHERE code_commune = ?
            ORDER BY annee
            """,
            [code_commune],
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
) -> pl.DataFrame:
    """Croisement indicateurs économiques × résultats présidentiels T2 par commune.

    Utilise v_scores_commune_pres (T2) + v_participation_commune_pres pour calculer
    pct_voix, et v_economie_commune pour les indicateurs éco de l'année n-1.
    """
    con = _open_ro()
    try:
        sql = """
            SELECT
                e.code_commune,
                gc.nom                                            AS nom_commune,
                e.bloc,
                ROUND(100.0 * e.voix / NULLIF(p.exprimes, 0), 2) AS pct_voix,
                eco.taux_pauvrete,
                eco.niveau_vie_median,
                eco.tx_chomage_dec,
                eco.part_ouvriers_employes,
                eco.part_emploi_industriel,
                eco.part_logements_sociaux,
                eco.pop_active
            FROM v_scores_commune_pres e
            LEFT JOIN v_participation_commune_pres p
                ON p.code_commune = e.code_commune
                AND p.annee = e.annee AND p.tour = e.tour
            LEFT JOIN v_economie_commune eco
                ON eco.code_commune = e.code_commune AND eco.annee = e.annee - 1
            LEFT JOIN geographies_communes gc ON gc.code_insee = e.code_commune
            WHERE e.annee = ? AND e.tour = 2
        """
        params: list = [annee_election]
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


@st.cache_data(ttl=3600)
def get_evolution_hdf() -> pl.DataFrame:
    """Évolution des indicateurs agrégés HdF par année (v_evolution_economie_hdf)."""
    con = _open_ro()
    try:
        rows = con.execute(
            "SELECT annee, taux_pauvrete_moyen, niveau_vie_median_hdf, tx_chomage_moyen "
            "FROM v_evolution_economie_hdf ORDER BY annee"
        ).fetchall()
    finally:
        con.close()

    if not rows:
        return pl.DataFrame(
            schema={
                "annee": pl.Int64,
                "taux_pauvrete_moyen": pl.Float64,
                "niveau_vie_median_hdf": pl.Float64,
                "tx_chomage_moyen": pl.Float64,
            }
        )
    return pl.DataFrame(
        {
            "annee": [int(r[0]) for r in rows],
            "taux_pauvrete_moyen": [float(r[1]) if r[1] is not None else None for r in rows],
            "niveau_vie_median_hdf": [float(r[2]) if r[2] is not None else None for r in rows],
            "tx_chomage_moyen": [float(r[3]) if r[3] is not None else None for r in rows],
        }
    )


@st.cache_data(ttl=3600)
def get_annees_par_indicateur() -> dict[str, list[int]]:
    """Années disponibles par indicateur (selon la table source)."""
    con = _open_ro()
    try:

        def _a(sql: str) -> list[int]:
            return [int(r[0]) for r in con.execute(sql).fetchall()]

        f = _a("SELECT DISTINCT annee FROM economie_filosofi ORDER BY annee")
        r = _a("SELECT DISTINCT annee_millesime FROM economie_rp ORDER BY annee_millesime")
        rsa = _a(
            "SELECT DISTINCT annee FROM economie_social WHERE nb_foyers_rsa IS NOT NULL ORDER BY annee"
        )
        apl = _a(
            "SELECT DISTINCT annee FROM economie_social WHERE apl_medecins IS NOT NULL ORDER BY annee"
        )
    finally:
        con.close()
    return {
        "taux_pauvrete": f,
        "niveau_vie_median": f,
        "tx_chomage_dec": r,
        "part_ouvriers_employes": r,
        "part_emploi_industriel": r,
        "part_logements_sociaux": r,
        "nb_foyers_rsa": rsa,
        "apl_medecins": apl,
    }


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
