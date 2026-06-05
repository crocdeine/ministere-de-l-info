"""Requêtes DuckDB cachées pour la page Élections (présidentielles C3, législatives D1.3)."""

from __future__ import annotations

from pathlib import Path

import duckdb
import polars as pl
import streamlit as st

from ministere_de_l_info.etl.schema_elections import _CIRCO21_CODES

DB_PATH: Path = Path(__file__).resolve().parents[3] / "data" / "ministere.duckdb"

_CIRCO21_SQL: str = ", ".join(f"'{c}'" for c in _CIRCO21_CODES)
_HDF_DEPTS_SQL: str = "'02', '59', '60', '62', '80'"
_BLOCS_ORDERED: list[str] = ["EXG", "GAU", "DIV", "CENT", "DTE", "EXD"]


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
def get_communes_hdf_pres(annee: int, tour: int) -> list[tuple[str, str]]:
    """Liste [(code_commune, nom)] des communes HdF ayant des données pour ce scrutin."""
    con = _open_ro()
    try:
        rows = con.execute(  # noqa: S608
            f"""
            SELECT DISTINCT rp.code_commune, COALESCE(gc.nom, rp.code_commune) AS nom
            FROM resultats_participation rp
            JOIN elections e ON e.id_election = rp.id_election
            LEFT JOIN geographies_communes gc ON gc.code_insee = rp.code_commune
            WHERE e.type_scrutin = 'pres' AND e.annee = ? AND e.tour = ?
              AND rp.code_departement IN ({_HDF_DEPTS_SQL})
            ORDER BY nom
            """,
            [annee, tour],
        ).fetchall()
    finally:
        con.close()
    return [(r[0], r[1]) for r in rows]


@st.cache_data(ttl=3600)
def get_metrics_commune_pres(annee: int, tour: int, code_commune: str) -> dict:
    """Métriques agrégées d'une commune (inscrits/votants/taux/bloc_dominant)."""
    con = _open_ro()
    try:
        row = con.execute(
            """
            SELECT SUM(rp.inscrits), SUM(rp.votants), SUM(rp.exprimes),
                   ROUND(100.0 * SUM(rp.votants) / NULLIF(SUM(rp.inscrits), 0), 2)
            FROM resultats_participation rp
            JOIN elections e ON e.id_election = rp.id_election
            WHERE e.type_scrutin = 'pres' AND e.annee = ? AND e.tour = ? AND rp.code_commune = ?
            """,
            [annee, tour, code_commune],
        ).fetchone()
        bloc_row = con.execute(
            """
            SELECT bloc FROM v_resultats_candidats_avec_bloc
            WHERE type_scrutin = 'pres' AND annee = ? AND tour = ? AND code_commune = ?
            GROUP BY bloc ORDER BY SUM(voix) DESC LIMIT 1
            """,
            [annee, tour, code_commune],
        ).fetchone()
    finally:
        con.close()
    return {
        "inscrits": int(row[0] or 0),
        "votants": int(row[1] or 0),
        "exprimes": int(row[2] or 0),
        "taux_participation_pct": float(row[3] or 0.0),
        "bloc_dominant": bloc_row[0] if bloc_row else "DIV",
    }


def _build_bv_df(part_rows: list, voix_rows: list) -> pl.DataFrame:
    """Construit le DataFrame BV avec pivot des voix par bloc."""
    _empty_schema: dict = {
        "code_bv": pl.Utf8,
        "inscrits": pl.Int64,
        "votants": pl.Int64,
        "exprimes": pl.Int64,
        "taux_participation_pct": pl.Float64,
        "bloc_gagnant": pl.Utf8,
        **{f"voix_{b}": pl.Int64 for b in _BLOCS_ORDERED},
    }
    if not part_rows:
        return pl.DataFrame(schema=_empty_schema)

    part_df = pl.DataFrame(
        {
            "code_bv": [r[0] for r in part_rows],
            "inscrits": [int(r[1] or 0) for r in part_rows],
            "votants": [int(r[2] or 0) for r in part_rows],
            "exprimes": [int(r[3] or 0) for r in part_rows],
            "taux_participation_pct": [float(r[4] or 0.0) for r in part_rows],
        }
    )
    if not voix_rows:
        result = part_df.with_columns(pl.lit("DIV").alias("bloc_gagnant"))
        for b in _BLOCS_ORDERED:
            result = result.with_columns(pl.lit(0).cast(pl.Int64).alias(f"voix_{b}"))
        return result.sort("code_bv")

    voix_df = pl.DataFrame(
        {
            "code_bv": [r[0] for r in voix_rows],
            "bloc": [r[1] for r in voix_rows],
            "voix": [int(r[2] or 0) for r in voix_rows],
        }
    )
    bloc_gagnant_df = (
        voix_df.sort("voix", descending=True)
        .unique("code_bv", keep="first")
        .rename({"bloc": "bloc_gagnant"})
        .select(["code_bv", "bloc_gagnant"])
    )
    pivot = voix_df.pivot(
        values="voix", index="code_bv", on="bloc", aggregate_function="sum"
    ).fill_null(0)
    for b in _BLOCS_ORDERED:
        if b not in pivot.columns:
            pivot = pivot.with_columns(pl.lit(0).cast(pl.Int64).alias(b))
    pivot = pivot.rename({b: f"voix_{b}" for b in _BLOCS_ORDERED if b in pivot.columns})

    return (
        part_df.join(bloc_gagnant_df, on="code_bv", how="left")
        .join(pivot, on="code_bv", how="left")
        .with_columns([pl.col(f"voix_{b}").fill_null(0) for b in _BLOCS_ORDERED])
        .with_columns(pl.col("bloc_gagnant").fill_null("DIV"))
        .sort("code_bv")
    )


@st.cache_data(ttl=3600)
def get_bv_details_pres(annee: int, tour: int, code_commune: str) -> pl.DataFrame:
    """Détail par BV : participation + voix par bloc (pivot wide) pour une commune."""
    con = _open_ro()
    try:
        part_rows = con.execute(
            """
            SELECT rp.code_bv, rp.inscrits, rp.votants, rp.exprimes,
                   ROUND(100.0 * rp.votants / NULLIF(rp.inscrits, 0), 2)
            FROM resultats_participation rp
            JOIN elections e ON e.id_election = rp.id_election
            WHERE e.type_scrutin = 'pres' AND e.annee = ? AND e.tour = ? AND rp.code_commune = ?
            ORDER BY rp.code_bv
            """,
            [annee, tour, code_commune],
        ).fetchall()
        voix_rows = con.execute(
            """
            SELECT code_bv, bloc, SUM(voix) AS voix
            FROM v_resultats_candidats_avec_bloc
            WHERE type_scrutin = 'pres' AND annee = ? AND tour = ? AND code_commune = ?
            GROUP BY code_bv, bloc
            """,
            [annee, tour, code_commune],
        ).fetchall()
    finally:
        con.close()
    return _build_bv_df(part_rows, voix_rows)


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
