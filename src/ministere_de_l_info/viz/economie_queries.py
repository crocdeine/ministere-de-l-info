"""Requêtes DuckDB cachées pour la page Économie (Phase E3).

Fonctions exportées
-------------------
- is_data_loaded()            : True si les 2 tables économiques contiennent des données
- get_annees_disponibles()    : années dans economie_filosofi
- get_indicateurs()           : dict code → libellé des 6 indicateurs
- get_scores_commune()        : indicateur × commune HdF pour une année
- get_economie_commune()      : tous indicateurs pour une commune, toutes années
- get_croisement_eco_elections(): croisement économie × présidentielles T2
- get_evolution_hdf()         : évolution agrégée HdF (3 indicateurs)
- get_stats_hdf()             : min/max/moy/med d'un indicateur pour calibrer la choroplèthe
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
    }
)


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


@st.cache_data(ttl=3600)
def get_annees_disponibles() -> list[int]:
    """Années disponibles dans economie_filosofi (2017-2021)."""
    con = _open_ro()
    try:
        rows = con.execute("SELECT DISTINCT annee FROM economie_filosofi ORDER BY annee").fetchall()
        return [int(r[0]) for r in rows]
    finally:
        con.close()


@st.cache_data
def get_indicateurs() -> dict[str, str]:
    """Dictionnaire code → libellé des 6 indicateurs disponibles."""
    return {
        "taux_pauvrete": "Taux de pauvreté (%)",
        "niveau_vie_median": "Niveau de vie médian (€)",
        "tx_chomage_dec": "Taux de chômage (RP, %)",
        "part_ouvriers_employes": "Part ouvriers + employés (%)",
        "part_emploi_industriel": "Part emploi industriel (%)",
        "part_logements_sociaux": "Part logements sociaux (%)",
    }


@st.cache_data(ttl=3600, show_spinner="Chargement des données communales…")
def get_scores_commune(annee: int, indicateur: str) -> pl.DataFrame:
    """Valeur d'un indicateur par commune HdF pour une année.

    Retourne code_commune, nom_commune, valeur, secret, geojson.
    La colonne geojson vient de geometry_simplified_communal (déjà simplifiée en DB).
    """
    if indicateur not in _INDICATEURS_VALIDES:
        raise ValueError(f"Indicateur inconnu : {indicateur}")

    con = _open_ro()
    try:
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
def get_stats_hdf(annee: int, indicateur: str) -> dict:
    """Statistiques (min/max/moy/médiane) d'un indicateur HdF pour une année.

    Utile pour calibrer les seuils de la choroplèthe.
    """
    if indicateur not in _INDICATEURS_VALIDES:
        raise ValueError(f"Indicateur inconnu : {indicateur}")

    con = _open_ro()
    try:
        row = con.execute(  # noqa: S608
            f"""
            SELECT
                MIN({indicateur})    AS vmin,
                MAX({indicateur})    AS vmax,
                AVG({indicateur})    AS vmoy,
                MEDIAN({indicateur}) AS vmed
            FROM v_economie_commune
            WHERE annee = ? AND {indicateur} IS NOT NULL
            """,
            [annee],
        ).fetchone()
    finally:
        con.close()

    if not row or row[0] is None:
        return {"min": None, "max": None, "moy": None, "med": None}
    return {
        "min": float(row[0]),
        "max": float(row[1]),
        "moy": float(row[2]),
        "med": float(row[3]),
    }
