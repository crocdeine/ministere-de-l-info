"""Requêtes DuckDB cachées pour la page Élections (C3)."""

from __future__ import annotations

from pathlib import Path

import duckdb
import polars as pl
import streamlit as st

from ministere_de_l_info.etl.schema_elections import _CIRCO21_CODES

DB_PATH: Path = Path(__file__).resolve().parents[3] / "data" / "ministere.duckdb"

_CIRCO21_SQL: str = ", ".join(f"'{c}'" for c in _CIRCO21_CODES)


def _open_ro() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    con.execute("LOAD spatial")
    return con


@st.cache_data(ttl=60)
def is_data_loaded() -> bool:
    """Vérifie que les résultats présidentiels sont chargés."""
    con = _open_ro()
    try:
        n = con.execute(
            "SELECT COUNT(*) FROM resultats_candidats WHERE id_election LIKE '%_pres_%'"
        ).fetchone()[0]
        return int(n) > 0
    finally:
        con.close()


@st.cache_data(ttl=3600)
def get_blocs_meta() -> list[tuple[str, str, str, int]]:
    """Retourne [(bloc, libelle, couleur, ordre), ...] par ordre gauche→droite."""
    con = _open_ro()
    try:
        return con.execute(
            "SELECT bloc, libelle, couleur, ordre FROM blocs_politiques ORDER BY ordre"
        ).fetchall()
    finally:
        con.close()


@st.cache_data(ttl=3600, show_spinner="Chargement des résultats…")
def get_scores_communes(annee: int, tour: int, zone: str) -> pl.DataFrame:
    """Score par commune et par bloc (voix). zone : 'circo21' | 'hdf'."""
    con = _open_ro()
    try:
        if zone == "circo21":
            sql = (
                "SELECT code_commune, bloc, voix "
                "FROM v_scores_circo21_pres WHERE annee = ? AND tour = ?"
            )
        else:
            sql = (
                "SELECT code_commune, bloc, voix "
                "FROM v_scores_commune_pres WHERE annee = ? AND tour = ?"
            )
        rows = con.execute(sql, [annee, tour]).fetchall()
    finally:
        con.close()
    if not rows:
        return pl.DataFrame(schema={"code_commune": pl.Utf8, "bloc": pl.Utf8, "voix": pl.Int64})
    return pl.DataFrame(
        {
            "code_commune": [r[0] for r in rows],
            "bloc": [r[1] for r in rows],
            "voix": [r[2] for r in rows],
        }
    )


@st.cache_data(ttl=3600, show_spinner="Chargement de la participation…")
def get_participation_communes(annee: int, tour: int, zone: str) -> pl.DataFrame:
    """Participation par commune. zone : 'circo21' | 'hdf'."""
    con = _open_ro()
    try:
        where_zone = f"AND code_commune IN ({_CIRCO21_SQL})" if zone == "circo21" else ""
        rows = con.execute(  # noqa: S608
            f"SELECT code_commune, inscrits, votants, exprimes, taux_participation_pct "
            f"FROM v_participation_commune_pres WHERE annee = ? AND tour = ? {where_zone}",
            [annee, tour],
        ).fetchall()
    finally:
        con.close()
    if not rows:
        return pl.DataFrame(
            schema={
                "code_commune": pl.Utf8,
                "inscrits": pl.Int64,
                "votants": pl.Int64,
                "exprimes": pl.Int64,
                "taux_participation_pct": pl.Float64,
            }
        )
    return pl.DataFrame(
        {
            "code_commune": [r[0] for r in rows],
            "inscrits": [r[1] for r in rows],
            "votants": [r[2] for r in rows],
            "exprimes": [r[3] for r in rows],
            "taux_participation_pct": [float(r[4]) if r[4] is not None else 0.0 for r in rows],
        }
    )


@st.cache_data(ttl=3600)
def get_evolution_blocs(zone: str) -> pl.DataFrame:
    """Voix par annee/tour/bloc pour le graphe d'évolution. zone : 'circo21' | 'hdf'."""
    con = _open_ro()
    try:
        if zone == "circo21":
            rows = con.execute(
                "SELECT annee, tour, bloc, voix_total "
                "FROM v_evolution_blocs_circo21 ORDER BY annee, tour, bloc"
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT annee, tour, bloc, SUM(voix) AS voix_total "
                "FROM v_scores_commune_pres GROUP BY annee, tour, bloc ORDER BY annee, tour, bloc"
            ).fetchall()
    finally:
        con.close()
    if not rows:
        return pl.DataFrame(
            schema={
                "annee": pl.Int64,
                "tour": pl.Int64,
                "bloc": pl.Utf8,
                "voix_total": pl.Int64,
            }
        )
    return pl.DataFrame(
        {
            "annee": [r[0] for r in rows],
            "tour": [r[1] for r in rows],
            "bloc": [r[2] for r in rows],
            "voix_total": [r[3] for r in rows],
        }
    )


@st.cache_data(ttl=3600, show_spinner="Chargement des géométries…")
def get_communes_geo(zone: str) -> pl.DataFrame:
    """Géométries communales (GeoJSON). zone : 'circo21' | 'hdf'."""
    con = _open_ro()
    try:
        where = f"code_insee IN ({_CIRCO21_SQL})" if zone == "circo21" else "code_region = '32'"
        rows = con.execute(  # noqa: S608
            f"SELECT code_insee, nom, ST_AsGeoJSON(geometry_simplified_communal) "
            f"FROM geographies_communes WHERE {where} ORDER BY nom"
        ).fetchall()
    finally:
        con.close()
    if not rows:
        return pl.DataFrame(schema={"code_commune": pl.Utf8, "nom": pl.Utf8, "geojson": pl.Utf8})
    return pl.DataFrame(
        {
            "code_commune": [r[0] for r in rows],
            "nom": [r[1] for r in rows],
            "geojson": [r[2] for r in rows],
        }
    )


@st.cache_data(ttl=3600)
def get_bounds(zone: str) -> list[list[float]] | None:
    """Bounding box [[lat_min, lon_min], [lat_max, lon_max]] pour la zone."""
    con = _open_ro()
    try:
        where = f"code_insee IN ({_CIRCO21_SQL})" if zone == "circo21" else "code_region = '32'"
        row = con.execute(  # noqa: S608
            f"SELECT MIN(ST_YMin(geometry_simplified_communal)), MIN(ST_XMin(geometry_simplified_communal)),"
            f" MAX(ST_YMax(geometry_simplified_communal)), MAX(ST_XMax(geometry_simplified_communal))"
            f" FROM geographies_communes WHERE {where}"
        ).fetchone()
    finally:
        con.close()
    if not row or row[0] is None:
        return None
    miny, minx, maxy, maxx = row
    return [[float(miny), float(minx)], [float(maxy), float(maxx)]]
