"""Requêtes DuckDB cachées pour les législatives HdF (Phase D1.3)."""

from __future__ import annotations

import polars as pl
import streamlit as st

from ministere_de_l_info.viz.elections_queries import DB_PATH, _open_ro  # noqa: PLC2701

_HDF_DEPTS_SQL: str = "'02', '59', '60', '62', '80'"

_LEGI_JOIN = """
    FROM resultats_candidats rc
    JOIN elections e ON e.id_election = rc.id_election
    JOIN resultats_participation rp
        ON rp.id_election      = rc.id_election
        AND rp.code_departement = rc.code_departement
        AND rp.code_commune     = rc.code_commune
        AND rp.code_bv          = rc.code_bv
    LEFT JOIN nuances_harmonisees nh ON nh.nuance = rc.nuance AND nh.annee = e.annee
    WHERE e.type_scrutin = 'legi'
"""

__all__ = [
    "DB_PATH",
    "is_legi_data_loaded",
    "get_circos_hdf_legi",
    "get_scores_hdf_legi",
    "get_participation_hdf_legi",
    "get_evolution_hdf_legi",
    "get_evolution_circo_legi",
    "get_scores_communes_circo_legi",
    "get_communes_circo_legi_geo",
    "get_participation_communes_circo_legi",
    "get_nuances_circo_legi",
    "get_circos_hdf_geo",
    "get_hdf_bounds_circo",
    "get_circo_bounds",
    "get_communes_circo_legi_list",
    "get_metrics_commune_legi",
    "get_bv_details_legi",
]


@st.cache_data(ttl=60)
def is_legi_data_loaded() -> bool:
    """Vérifie que les résultats législatifs sont chargés."""
    con = _open_ro()
    try:
        n = con.execute(
            "SELECT COUNT(*) FROM resultats_candidats WHERE id_election LIKE '%_legi_%'"
        ).fetchone()[0]
        return int(n) > 0
    finally:
        con.close()


@st.cache_data(ttl=86400)
def get_circos_hdf_legi() -> list[tuple[str, str]]:
    """Retourne [(code_circo, display_name), ...] pour les 50 circos HdF triées."""
    con = _open_ro()
    try:
        rows = con.execute("""
            SELECT DISTINCT v.code_circo, gc.nom
            FROM v_scores_circo_legi v
            LEFT JOIN geographies_circonscriptions gc ON gc.code = v.code_circo
            ORDER BY v.code_circo
        """).fetchall()
    finally:
        con.close()
    return [(code, f"{code} — {nom}" if nom else code) for code, nom in rows]


@st.cache_data(ttl=3600, show_spinner="Chargement des scores HdF…")
def get_scores_hdf_legi(annee: int, tour: int) -> pl.DataFrame:
    """Scores par (code_circo, bloc) pour la vue d'ensemble HdF."""
    con = _open_ro()
    try:
        rows = con.execute(
            "SELECT code_circo, bloc, voix FROM v_scores_circo_legi WHERE annee = ? AND tour = ?",
            [annee, tour],
        ).fetchall()
    finally:
        con.close()
    if not rows:
        return pl.DataFrame(schema={"code_circo": pl.Utf8, "bloc": pl.Utf8, "voix": pl.Int64})
    return pl.DataFrame(
        {
            "code_circo": [r[0] for r in rows],
            "bloc": [r[1] for r in rows],
            "voix": [r[2] for r in rows],
        }
    )


@st.cache_data(ttl=3600, show_spinner="Chargement de la participation HdF…")
def get_participation_hdf_legi(annee: int, tour: int) -> pl.DataFrame:
    """Participation par circo pour la vue HdF."""
    con = _open_ro()
    try:
        rows = con.execute(
            "SELECT code_circo, inscrits, votants, exprimes, taux_participation_pct "
            "FROM v_participation_circo_legi WHERE annee = ? AND tour = ?",
            [annee, tour],
        ).fetchall()
    finally:
        con.close()
    if not rows:
        return pl.DataFrame(
            schema={
                "code_circo": pl.Utf8,
                "inscrits": pl.Int64,
                "votants": pl.Int64,
                "exprimes": pl.Int64,
                "taux_participation_pct": pl.Float64,
            }
        )
    return pl.DataFrame(
        {
            "code_circo": [r[0] for r in rows],
            "inscrits": [r[1] for r in rows],
            "votants": [r[2] for r in rows],
            "exprimes": [r[3] for r in rows],
            "taux_participation_pct": [float(r[4]) if r[4] is not None else 0.0 for r in rows],
        }
    )


@st.cache_data(ttl=3600)
def get_evolution_hdf_legi() -> pl.DataFrame:
    """Évolution temporelle des blocs agrégée sur HdF (toutes circos)."""
    con = _open_ro()
    try:
        rows = con.execute(
            "SELECT annee, tour, ancien_decoupage, bloc, voix_total "
            "FROM v_evolution_blocs_hdf_legi ORDER BY annee, tour, bloc"
        ).fetchall()
    finally:
        con.close()
    if not rows:
        return pl.DataFrame(
            schema={
                "annee": pl.Int64,
                "tour": pl.Int64,
                "ancien_decoupage": pl.Boolean,
                "bloc": pl.Utf8,
                "voix_total": pl.Int64,
            }
        )
    return pl.DataFrame(
        {
            "annee": [r[0] for r in rows],
            "tour": [r[1] for r in rows],
            "ancien_decoupage": [bool(r[2]) for r in rows],
            "bloc": [r[3] for r in rows],
            "voix_total": [r[4] for r in rows],
        }
    )


@st.cache_data(ttl=3600)
def get_evolution_circo_legi(code_circo: str) -> pl.DataFrame:
    """Évolution temporelle des blocs pour une circo donnée."""
    con = _open_ro()
    try:
        rows = con.execute(
            "SELECT annee, tour, ancien_decoupage, bloc, SUM(voix) AS voix_total "
            "FROM v_scores_circo_legi WHERE code_circo = ? "
            "GROUP BY annee, tour, ancien_decoupage, bloc ORDER BY annee, tour, bloc",
            [code_circo],
        ).fetchall()
    finally:
        con.close()
    if not rows:
        return pl.DataFrame(
            schema={
                "annee": pl.Int64,
                "tour": pl.Int64,
                "ancien_decoupage": pl.Boolean,
                "bloc": pl.Utf8,
                "voix_total": pl.Int64,
            }
        )
    return pl.DataFrame(
        {
            "annee": [r[0] for r in rows],
            "tour": [r[1] for r in rows],
            "ancien_decoupage": [bool(r[2]) for r in rows],
            "bloc": [r[3] for r in rows],
            "voix_total": [r[4] for r in rows],
        }
    )


@st.cache_data(ttl=3600, show_spinner="Chargement des résultats par commune…")
def get_scores_communes_circo_legi(annee: int, tour: int, code_circo: str) -> pl.DataFrame:
    """Scores par (code_commune, bloc) pour les communes d'une circo."""
    con = _open_ro()
    try:
        rows = con.execute(  # noqa: S608
            f"SELECT rc.code_commune, COALESCE(nh.bloc, 'DIV') AS bloc, SUM(rc.voix) AS voix "
            f"{_LEGI_JOIN} AND e.annee = ? AND e.tour = ? AND rp.code_circo = ? "
            f"GROUP BY rc.code_commune, COALESCE(nh.bloc, 'DIV')",
            [annee, tour, code_circo],
        ).fetchall()
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


@st.cache_data(ttl=3600, show_spinner="Chargement des géométries…")
def get_communes_circo_legi_geo(annee: int, tour: int, code_circo: str) -> pl.DataFrame:
    """Géométries des communes d'une circo pour un scrutin donné."""
    con = _open_ro()
    try:
        rows = con.execute(
            """
            SELECT gc.code_insee, gc.nom, ST_AsGeoJSON(gc.geometry_simplified_communal) AS geojson
            FROM geographies_communes gc
            WHERE gc.code_insee IN (
                SELECT DISTINCT rp.code_commune
                FROM resultats_participation rp
                JOIN elections e ON e.id_election = rp.id_election
                WHERE e.type_scrutin = 'legi' AND e.annee = ? AND e.tour = ? AND rp.code_circo = ?
            )
            ORDER BY gc.nom
            """,
            [annee, tour, code_circo],
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
def get_participation_communes_circo_legi(annee: int, tour: int, code_circo: str) -> pl.DataFrame:
    """Participation par commune pour une circo donnée."""
    con = _open_ro()
    try:
        rows = con.execute(
            """
            SELECT rp.code_commune,
                   SUM(rp.inscrits) AS inscrits, SUM(rp.votants) AS votants,
                   SUM(rp.exprimes) AS exprimes,
                   ROUND(100.0 * SUM(rp.votants) / NULLIF(SUM(rp.inscrits), 0), 2) AS taux_participation_pct
            FROM resultats_participation rp
            JOIN elections e ON e.id_election = rp.id_election
            WHERE e.type_scrutin = 'legi' AND e.annee = ? AND e.tour = ? AND rp.code_circo = ?
            GROUP BY rp.code_commune
            """,
            [annee, tour, code_circo],
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
def get_nuances_circo_legi(annee: int, tour: int, code_circo: str) -> pl.DataFrame:
    """Résultats par nuance pour une circo (tableau détaillé)."""
    con = _open_ro()
    try:
        rows = con.execute(  # noqa: S608
            f"SELECT rc.nuance, COALESCE(nh.bloc, 'DIV') AS bloc, SUM(rc.voix) AS voix "
            f"{_LEGI_JOIN} AND e.annee = ? AND e.tour = ? AND rp.code_circo = ? "
            f"GROUP BY rc.nuance, COALESCE(nh.bloc, 'DIV') ORDER BY voix DESC",
            [annee, tour, code_circo],
        ).fetchall()
    finally:
        con.close()
    if not rows:
        return pl.DataFrame(schema={"nuance": pl.Utf8, "bloc": pl.Utf8, "voix": pl.Int64})
    return pl.DataFrame(
        {"nuance": [r[0] for r in rows], "bloc": [r[1] for r in rows], "voix": [r[2] for r in rows]}
    )


@st.cache_data(ttl=86400, show_spinner="Chargement des géométries circos…")
def get_circos_hdf_geo() -> pl.DataFrame:
    """Géométries des 50 circonscriptions HdF."""
    con = _open_ro()
    try:
        rows = con.execute(  # noqa: S608
            f"SELECT code, nom, ST_AsGeoJSON(geometry_simplified_circo) AS geojson "
            f"FROM geographies_circonscriptions "
            f"WHERE code_departement IN ({_HDF_DEPTS_SQL}) ORDER BY code"
        ).fetchall()
    finally:
        con.close()
    if not rows:
        return pl.DataFrame(schema={"code_circo": pl.Utf8, "nom": pl.Utf8, "geojson": pl.Utf8})
    return pl.DataFrame(
        {
            "code_circo": [r[0] for r in rows],
            "nom": [r[1] for r in rows],
            "geojson": [r[2] for r in rows],
        }
    )


@st.cache_data(ttl=86400)
def get_hdf_bounds_circo() -> list[list[float]] | None:
    """Bounding box des 50 circos HdF."""
    con = _open_ro()
    try:
        row = con.execute(  # noqa: S608
            f"SELECT MIN(ST_YMin(geometry_simplified_circo)), MIN(ST_XMin(geometry_simplified_circo)), "
            f"MAX(ST_YMax(geometry_simplified_circo)), MAX(ST_XMax(geometry_simplified_circo)) "
            f"FROM geographies_circonscriptions WHERE code_departement IN ({_HDF_DEPTS_SQL})"
        ).fetchone()
    finally:
        con.close()
    if not row or row[0] is None:
        return None
    miny, minx, maxy, maxx = row
    return [[float(miny), float(minx)], [float(maxy), float(maxx)]]


@st.cache_data(ttl=3600)
def get_communes_circo_legi_list(annee: int, tour: int, code_circo: str) -> list[tuple[str, str]]:
    """Liste [(code_commune, nom)] des communes d'une circo pour ce scrutin. Triées par nom."""
    con = _open_ro()
    try:
        rows = con.execute(
            """
            SELECT DISTINCT rp.code_commune, COALESCE(gc.nom, rp.code_commune) AS nom
            FROM resultats_participation rp
            JOIN elections e ON e.id_election = rp.id_election
            LEFT JOIN geographies_communes gc ON gc.code_insee = rp.code_commune
            WHERE e.type_scrutin = 'legi' AND e.annee = ? AND e.tour = ? AND rp.code_circo = ?
            ORDER BY nom
            """,
            [annee, tour, code_circo],
        ).fetchall()
    finally:
        con.close()
    return [(r[0], r[1]) for r in rows]


@st.cache_data(ttl=3600)
def get_metrics_commune_legi(annee: int, tour: int, code_commune: str) -> dict:
    """Métriques agrégées d'une commune (inscrits/votants/taux/bloc_dominant) — législatives."""
    con = _open_ro()
    try:
        row = con.execute(
            """
            SELECT SUM(rp.inscrits), SUM(rp.votants), SUM(rp.exprimes),
                   ROUND(100.0 * SUM(rp.votants) / NULLIF(SUM(rp.inscrits), 0), 2)
            FROM resultats_participation rp
            JOIN elections e ON e.id_election = rp.id_election
            WHERE e.type_scrutin = 'legi' AND e.annee = ? AND e.tour = ? AND rp.code_commune = ?
            """,
            [annee, tour, code_commune],
        ).fetchone()
        bloc_row = con.execute(
            """
            SELECT bloc FROM v_resultats_candidats_avec_bloc
            WHERE type_scrutin = 'legi' AND annee = ? AND tour = ? AND code_commune = ?
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


@st.cache_data(ttl=3600)
def get_bv_details_legi(annee: int, tour: int, code_commune: str) -> pl.DataFrame:
    """Détail par BV : participation + voix par bloc (pivot wide) — législatives."""
    from ministere_de_l_info.viz.elections_queries import _build_bv_df  # noqa: PLC0415

    con = _open_ro()
    try:
        part_rows = con.execute(
            """
            SELECT rp.code_bv, rp.inscrits, rp.votants, rp.exprimes,
                   ROUND(100.0 * rp.votants / NULLIF(rp.inscrits, 0), 2)
            FROM resultats_participation rp
            JOIN elections e ON e.id_election = rp.id_election
            WHERE e.type_scrutin = 'legi' AND e.annee = ? AND e.tour = ? AND rp.code_commune = ?
            ORDER BY rp.code_bv
            """,
            [annee, tour, code_commune],
        ).fetchall()
        voix_rows = con.execute(
            """
            SELECT code_bv, bloc, SUM(voix) AS voix
            FROM v_resultats_candidats_avec_bloc
            WHERE type_scrutin = 'legi' AND annee = ? AND tour = ? AND code_commune = ?
            GROUP BY code_bv, bloc
            """,
            [annee, tour, code_commune],
        ).fetchall()
    finally:
        con.close()
    return _build_bv_df(part_rows, voix_rows)


@st.cache_data(ttl=86400)
def get_circo_bounds(code_circo: str) -> list[list[float]] | None:
    """Bounding box d'une circo."""
    con = _open_ro()
    try:
        row = con.execute(
            "SELECT ST_YMin(geometry_simplified_circo), ST_XMin(geometry_simplified_circo), "
            "ST_YMax(geometry_simplified_circo), ST_XMax(geometry_simplified_circo) "
            "FROM geographies_circonscriptions WHERE code = ?",
            [code_circo],
        ).fetchone()
    finally:
        con.close()
    if not row or row[0] is None:
        return None
    miny, minx, maxy, maxx = row
    return [[float(miny), float(minx)], [float(maxy), float(maxx)]]
