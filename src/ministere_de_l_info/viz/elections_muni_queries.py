"""Requêtes DuckDB cachées pour les municipales HdF (Phase D3.3)."""

from __future__ import annotations

import polars as pl
import streamlit as st

from ministere_de_l_info.viz.elections_queries import DB_PATH, _open_ro  # noqa: PLC2701

_HDF_DEPTS_SQL: str = "'02', '59', '60', '62', '80'"

__all__ = [
    "DB_PATH",
    "is_muni_data_loaded",
    "get_scrutins_muni",
    "get_scores_communes_muni",
    "get_communes_muni_geo",
    "get_evolution_blocs_hdf_muni",
    "get_communes_hdf_muni_list",
    "get_metrics_commune_muni",
    "get_scores_bloc_commune_muni",
    "get_listes_commune_muni",
    "get_seuil_nuancage_par_annee",
    "get_hdf_bounds_communes",
]


@st.cache_data(ttl=60)
def is_muni_data_loaded() -> bool:
    """Vérifie que les résultats municipaux sont chargés."""
    con = _open_ro()
    try:
        n = con.execute(
            "SELECT COUNT(*) FROM resultats_candidats WHERE id_election LIKE '%_muni_%'"
        ).fetchone()[0]
        return int(n) > 0
    finally:
        con.close()


@st.cache_data(ttl=86400)
def get_scrutins_muni() -> list[tuple[int, int, str]]:
    """Liste des scrutins municipaux chargés : [(annee, tour, label)], tri annee DESC, tour ASC."""
    con = _open_ro()
    try:
        rows = con.execute("""
            SELECT DISTINCT e.annee, e.tour
            FROM elections e
            WHERE e.type_scrutin = 'muni'
            ORDER BY e.annee DESC, e.tour ASC
        """).fetchall()
    finally:
        con.close()

    def _label(annee: int, tour: int) -> str:
        t = "1er" if tour == 1 else "2e"
        return f"Municipales {annee} — {t} tour"

    return [(r[0], r[1], _label(r[0], r[1])) for r in rows]


@st.cache_data(ttl=3600, show_spinner="Chargement des scores communes…")
def get_scores_communes_muni(annee: int, tour: int) -> pl.DataFrame:
    """Scores par (code_commune, bloc) depuis v_scores_commune_muni."""
    con = _open_ro()
    try:
        rows = con.execute(
            "SELECT code_commune, bloc, voix, pct_exprimes "
            "FROM v_scores_commune_muni "
            "WHERE annee = ? AND tour = ?",
            [annee, tour],
        ).fetchall()
    finally:
        con.close()
    if not rows:
        return pl.DataFrame(
            schema={
                "code_commune": pl.Utf8,
                "bloc": pl.Utf8,
                "voix": pl.Int64,
                "pct_exprimes": pl.Float64,
            }
        )
    return pl.DataFrame(
        {
            "code_commune": [r[0] for r in rows],
            "bloc": [r[1] for r in rows],
            "voix": [r[2] for r in rows],
            "pct_exprimes": [float(r[3]) if r[3] is not None else None for r in rows],
        }
    )


@st.cache_data(ttl=3600, show_spinner="Chargement des géométries communes…")
def get_communes_muni_geo(annee: int, tour: int) -> pl.DataFrame:
    """GeoDataFrame HdF : toutes les communes + bloc dominant (NULL si pas de nuance).

    LEFT JOIN : conserve les 3 782 communes HdF y compris sans données municipales.
    """
    con = _open_ro()
    try:
        rows = con.execute(
            f"""
            WITH scores AS (
                SELECT
                    code_commune,
                    bloc,
                    voix,
                    pct_exprimes,
                    ROW_NUMBER() OVER (PARTITION BY code_commune ORDER BY voix DESC NULLS LAST) AS rn
                FROM v_scores_commune_muni
                WHERE annee = ? AND tour = ?
            ),
            dom AS (
                SELECT code_commune, bloc AS bloc_dominant, voix AS voix_total, pct_exprimes AS pct_exprimes_dominant
                FROM scores WHERE rn = 1 AND bloc IS NOT NULL
            ),
            voix_tot AS (
                SELECT code_commune, SUM(voix) AS voix_total_all
                FROM v_scores_commune_muni WHERE annee = ? AND tour = ?
                GROUP BY code_commune
            )
            SELECT
                gc.code_insee,
                gc.nom,
                ST_AsGeoJSON(gc.geometry_simplified_communal) AS geojson,
                dom.bloc_dominant,
                COALESCE(dom.voix_total, vt.voix_total_all) AS voix_total,
                dom.pct_exprimes_dominant
            FROM geographies_communes gc
            LEFT JOIN dom ON dom.code_commune = gc.code_insee
            LEFT JOIN voix_tot vt ON vt.code_commune = gc.code_insee
            WHERE gc.code_departement IN ({_HDF_DEPTS_SQL})
            ORDER BY gc.nom
            """,
            [annee, tour, annee, tour],
        ).fetchall()
    finally:
        con.close()
    if not rows:
        return pl.DataFrame(
            schema={
                "code_commune": pl.Utf8,
                "nom": pl.Utf8,
                "geojson": pl.Utf8,
                "bloc_dominant": pl.Utf8,
                "voix_total": pl.Int64,
                "pct_exprimes_dominant": pl.Float64,
            }
        )
    return pl.DataFrame(
        {
            "code_commune": [r[0] for r in rows],
            "nom": [r[1] for r in rows],
            "geojson": [r[2] for r in rows],
            "bloc_dominant": [r[3] for r in rows],
            "voix_total": [r[4] if r[4] is not None else 0 for r in rows],
            "pct_exprimes_dominant": [float(r[5]) if r[5] is not None else None for r in rows],
        }
    )


@st.cache_data(ttl=3600)
def get_evolution_blocs_hdf_muni() -> pl.DataFrame:
    """Évolution temporelle des blocs HdF sur les scrutins municipaux."""
    con = _open_ro()
    try:
        rows = con.execute(
            "SELECT annee, tour, bloc, voix, pct_exprimes "
            "FROM v_evolution_blocs_hdf_muni "
            "ORDER BY annee ASC, tour ASC, bloc ASC NULLS LAST"
        ).fetchall()
    finally:
        con.close()
    if not rows:
        return pl.DataFrame(
            schema={
                "annee": pl.Int64,
                "tour": pl.Int64,
                "bloc": pl.Utf8,
                "voix": pl.Int64,
                "pct_exprimes": pl.Float64,
            }
        )
    return pl.DataFrame(
        {
            "annee": [r[0] for r in rows],
            "tour": [r[1] for r in rows],
            "bloc": [r[2] for r in rows],
            "voix": [r[3] for r in rows],
            "pct_exprimes": [float(r[4]) if r[4] is not None else None for r in rows],
        }
    )


@st.cache_data(ttl=3600)
def get_communes_hdf_muni_list(annee: int, tour: int) -> list[tuple[str, str]]:
    """Liste [(code_commune, nom)] des communes HdF ayant des données pour ce scrutin."""
    con = _open_ro()
    try:
        rows = con.execute(
            f"""
            SELECT DISTINCT rp.code_commune, COALESCE(gc.nom, rp.code_commune) AS nom
            FROM resultats_participation rp
            JOIN elections e ON e.id_election = rp.id_election
            LEFT JOIN geographies_communes gc ON gc.code_insee = rp.code_commune
            WHERE e.type_scrutin = 'muni' AND e.annee = ? AND e.tour = ?
              AND rp.code_departement IN ({_HDF_DEPTS_SQL})
            ORDER BY nom
            """,
            [annee, tour],
        ).fetchall()
    finally:
        con.close()
    return [(r[0], r[1]) for r in rows]


@st.cache_data(ttl=3600)
def get_metrics_commune_muni(annee: int, tour: int, code_commune: str) -> dict:
    """Métriques agrégées d'une commune (inscrits/votants/taux/bloc_dominant/nb_listes/est_nuancee)."""
    con = _open_ro()
    try:
        part_row = con.execute(
            """
            SELECT SUM(rp.inscrits), SUM(rp.votants), SUM(rp.exprimes),
                   ROUND(100.0 * SUM(rp.votants) / NULLIF(SUM(rp.inscrits), 0), 2)
            FROM resultats_participation rp
            JOIN elections e ON e.id_election = rp.id_election
            WHERE e.type_scrutin = 'muni' AND e.annee = ? AND e.tour = ? AND rp.code_commune = ?
            """,
            [annee, tour, code_commune],
        ).fetchone()

        nb_listes = con.execute(
            """
            SELECT COUNT(DISTINCT rc.nuance) AS nb
            FROM resultats_candidats rc
            JOIN elections e ON e.id_election = rc.id_election
            WHERE e.type_scrutin = 'muni' AND e.annee = ? AND e.tour = ? AND rc.code_commune = ?
            """,
            [annee, tour, code_commune],
        ).fetchone()[0]

        # est_nuancee : au moins 1 nuance avec bloc mappé (excluant NC/LMAJ/LNC → bloc NULL)
        nuancee_row = con.execute(
            """
            SELECT COUNT(*) > 0
            FROM v_scores_commune_muni
            WHERE annee = ? AND tour = ? AND code_commune = ? AND bloc IS NOT NULL
            """,
            [annee, tour, code_commune],
        ).fetchone()

        bloc_row = con.execute(
            """
            SELECT bloc FROM v_scores_commune_muni
            WHERE annee = ? AND tour = ? AND code_commune = ? AND bloc IS NOT NULL
            ORDER BY voix DESC LIMIT 1
            """,
            [annee, tour, code_commune],
        ).fetchone()
    finally:
        con.close()

    return {
        "inscrits": int(part_row[0] or 0),
        "votants": int(part_row[1] or 0),
        "exprimes": int(part_row[2] or 0),
        "taux_participation_pct": float(part_row[3] or 0.0),
        "nb_listes": int(nb_listes or 0),
        "est_nuancee": bool(nuancee_row[0]) if nuancee_row else False,
        "bloc_dominant": bloc_row[0] if bloc_row else None,
    }


@st.cache_data(ttl=3600)
def get_scores_bloc_commune_muni(annee: int, tour: int, code_commune: str) -> pl.DataFrame:
    """Scores par bloc pour une commune (vue bloc du drill-down)."""
    con = _open_ro()
    try:
        rows = con.execute(
            """
            SELECT bloc, voix, pct_exprimes
            FROM v_scores_commune_muni
            WHERE annee = ? AND tour = ? AND code_commune = ?
            ORDER BY voix DESC NULLS LAST
            """,
            [annee, tour, code_commune],
        ).fetchall()
    finally:
        con.close()
    if not rows:
        return pl.DataFrame(schema={"bloc": pl.Utf8, "voix": pl.Int64, "pct_exprimes": pl.Float64})
    return pl.DataFrame(
        {
            "bloc": [r[0] for r in rows],
            "voix": [r[1] for r in rows],
            "pct_exprimes": [float(r[2]) if r[2] is not None else None for r in rows],
        }
    )


@st.cache_data(ttl=3600)
def get_listes_commune_muni(annee: int, tour: int, code_commune: str) -> pl.DataFrame:
    """Détail des listes pour une commune (vue liste du drill-down)."""
    con = _open_ro()
    try:
        rows = con.execute(
            """
            SELECT nuance, bloc, libelle_abrege_liste, libelle_etendu_liste,
                   nom_tete_liste, prenom_tete_liste, voix, pct_exprimes
            FROM v_listes_commune_muni
            WHERE annee = ? AND tour = ? AND code_commune = ?
            ORDER BY voix DESC NULLS LAST
            """,
            [annee, tour, code_commune],
        ).fetchall()
    finally:
        con.close()
    if not rows:
        return pl.DataFrame(
            schema={
                "nuance": pl.Utf8,
                "bloc": pl.Utf8,
                "libelle_abrege_liste": pl.Utf8,
                "libelle_etendu_liste": pl.Utf8,
                "nom_tete_liste": pl.Utf8,
                "prenom_tete_liste": pl.Utf8,
                "voix": pl.Int64,
                "pct_exprimes": pl.Float64,
                "rang": pl.Int32,
                "label_affichage": pl.Utf8,
            }
        )

    def _label(prenom: str | None, nom: str | None, abrege: str | None, bloc: str | None) -> str:
        tete = ""
        if prenom and nom:
            tete = f"M/Mme {prenom} {nom}"
        elif nom:
            tete = nom
        detail_parts = [p for p in [abrege, bloc] if p]
        detail = "/".join(detail_parts) if detail_parts else "—"
        return f"Liste {tete} ({detail})" if tete else f"Liste ({detail})"

    df = pl.DataFrame(
        {
            "nuance": [r[0] for r in rows],
            "bloc": [r[1] for r in rows],
            "libelle_abrege_liste": [r[2] for r in rows],
            "libelle_etendu_liste": [r[3] for r in rows],
            "nom_tete_liste": [r[4] for r in rows],
            "prenom_tete_liste": [r[5] for r in rows],
            "voix": [r[6] for r in rows],
            "pct_exprimes": [float(r[7]) if r[7] is not None else None for r in rows],
        }
    )

    labels = [_label(r[5], r[4], r[2], r[1]) for r in rows]
    return df.with_columns(
        pl.Series("rang", list(range(1, len(rows) + 1)), dtype=pl.Int32),
        pl.Series("label_affichage", labels, dtype=pl.Utf8),
    )


def get_seuil_nuancage_par_annee(annee: int) -> dict:
    """Données statiques sur le seuil de nuançage par année de scrutin."""
    _SEUILS: dict[int, dict] = {
        2008: {
            "seuil_hab": 3500,
            "circulaire": "non publiée",
            "n_communes_nuancees_hdf": 164,
        },
        2014: {
            "seuil_hab": 1000,
            "circulaire": "non publiée",
            "n_communes_nuancees_hdf": 3778,
        },
        2020: {
            "seuil_hab": 3500,
            "circulaire": "INTA1931378J",
            "n_communes_nuancees_hdf": 3779,
        },
        2026: {
            "seuil_hab": 3500,
            "circulaire": "INTP2602966C",
            "n_communes_nuancees_hdf": 320,
            "ce_validation": "CE 27/02/2026 n°512694",
        },
    }
    return _SEUILS.get(annee, {"seuil_hab": 3500, "circulaire": "—", "n_communes_nuancees_hdf": 0})


@st.cache_data(ttl=86400)
def get_hdf_bounds_communes() -> list[list[float]] | None:
    """Bounding box des communes HdF."""
    con = _open_ro()
    try:
        row = con.execute(
            f"""
            SELECT
                MIN(ST_YMin(geometry_simplified_communal)),
                MIN(ST_XMin(geometry_simplified_communal)),
                MAX(ST_YMax(geometry_simplified_communal)),
                MAX(ST_XMax(geometry_simplified_communal))
            FROM geographies_communes
            WHERE code_departement IN ({_HDF_DEPTS_SQL})
            """
        ).fetchone()
    finally:
        con.close()
    if not row or row[0] is None:
        return None
    miny, minx, maxy, maxx = row
    return [[float(miny), float(minx)], [float(maxy), float(maxx)]]
