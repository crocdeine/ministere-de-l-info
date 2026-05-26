"""Constructeurs de requêtes SQL DuckDB et helpers géométriques pour maps.py."""

from __future__ import annotations

from typing import Literal

import duckdb

from ministere_de_l_info.viz._config import (
    _CLE_JOIN,
    _COLONNE_CODE,
    _FILTRE_DEPARTEMENT_COL,
    _FILTRE_REGION_COL,
    _GEOMETRIE_NATIONALE,
    _GEOMETRIE_ZOOM,
    _NIVEAUX_CONTOURS,
    _NIVEAUX_POPULATION,
    _TABLE_PAR_NIVEAU,
    _VUE_PAR_NIVEAU,
)


def _get_geometry_column(niveau: str, *, zoomed: bool) -> str:
    """Retourne la colonne géométrie adaptée selon le contexte (national ou zoomé)."""
    if zoomed:
        return _GEOMETRIE_ZOOM.get(niveau, _GEOMETRIE_NATIONALE[niveau])
    return _GEOMETRIE_NATIONALE[niveau]


def _check_population_disponible(con: duckdb.DuckDBPyConnection, niveau: str, annee: int) -> bool:
    """Retourne True si la vue population contient des données pour l'année demandée."""
    vue = _VUE_PAR_NIVEAU.get(niveau)
    if vue is None:
        return False
    count = con.execute(
        f"SELECT COUNT(*) FROM {vue} WHERE annee = ?",  # noqa: S608
        [annee],
    ).fetchone()[0]
    return int(count) > 0


def _resolve_mode(
    niveau: str,
    mode: Literal["choropleth", "contours", "auto"],
    con: duckdb.DuckDBPyConnection,
    annee: int,
    logger,  # type: ignore[type-arg]
) -> Literal["choropleth", "contours"]:
    """Détermine le mode effectif (choropleth ou contours) selon le niveau et les données."""
    if mode == "contours":
        return "contours"

    if mode == "choropleth":
        if niveau in _NIVEAUX_CONTOURS:
            raise ValueError(
                f"Le niveau '{niveau}' ne supporte pas le mode choropleth "
                "(aucune donnée de population disponible pour ce découpage). "
                "Utilisez mode='contours' ou mode='auto'."
            )
        if not _check_population_disponible(con, niveau, annee):
            raise ValueError(
                f"Aucune donnée population pour niveau='{niveau}', annee={annee}. "
                "Chargez d'abord les données via l'ETL, ou utilisez mode='auto'."
            )
        return "choropleth"

    # mode == "auto"
    if niveau in _NIVEAUX_CONTOURS:
        return "contours"
    if niveau in _NIVEAUX_POPULATION:
        if not _check_population_disponible(con, niveau, annee):
            logger.warning(
                "Aucune donnée population pour niveau='%s', annee=%d — "
                "carte en mode contours (fallback auto, chargez l'ETL communes).",
                niveau,
                annee,
            )
            return "contours"
        return "choropleth"
    return "contours"


def _build_query_choropleth(
    niveau: str,
    indicateur: str,
    annee: int,
    geom_col: str,
    filtre_departement: str | None,
    filtre_region: str | None,
) -> tuple[str, list]:
    """Construit la requête choropleth avec JOIN population. Retourne (sql, params)."""
    table = _TABLE_PAR_NIVEAU[niveau]
    vue = _VUE_PAR_NIVEAU[niveau]
    col_geo, col_vue = _CLE_JOIN[niveau]

    params: list = [annee]
    where = ["p.annee = ?"]

    dept_col = _FILTRE_DEPARTEMENT_COL[niveau]
    if filtre_departement and dept_col:
        where.append(f"g.{dept_col} = ?")
        params.append(filtre_departement)

    region_col = _FILTRE_REGION_COL[niveau]
    if filtre_region and region_col:
        where.append(f"g.{region_col} = ?")
        params.append(filtre_region)

    sql = (  # noqa: S608
        f"SELECT g.{col_geo} AS code, g.nom, p.{indicateur} AS valeur,"
        f" ST_AsGeoJSON(g.{geom_col}) AS geojson"
        f" FROM {table} g"
        f" JOIN {vue} p ON g.{col_geo} = p.{col_vue}"
        f" WHERE {' AND '.join(where)}"
        f" ORDER BY g.nom"
    )
    return sql, params


def _build_query_evolution(
    niveau: str,
    annee: int,
    annee_ref: int,
    geom_col: str,
    filtre_departement: str | None,
    filtre_region: str | None,
) -> tuple[str, list]:
    """Requête évolution démographique — double JOIN sur la même vue (p_main / p_ref).

    Retourne delta_abs (habitants) et delta_pct (%) entre annee_ref et annee.
    """
    table = _TABLE_PAR_NIVEAU[niveau]
    vue = _VUE_PAR_NIVEAU[niveau]
    col_geo, col_vue = _CLE_JOIN[niveau]

    params: list = [annee, annee_ref]
    where: list[str] = []

    dept_col = _FILTRE_DEPARTEMENT_COL[niveau]
    if filtre_departement and dept_col:
        where.append(f"g.{dept_col} = ?")
        params.append(filtre_departement)

    region_col = _FILTRE_REGION_COL[niveau]
    if filtre_region and region_col:
        where.append(f"g.{region_col} = ?")
        params.append(filtre_region)

    where_sql = f" WHERE {' AND '.join(where)}" if where else ""

    sql = (  # noqa: S608
        f"SELECT g.{col_geo} AS code, g.nom,"
        f" (p_main.population_municipale - p_ref.population_municipale) AS delta_abs,"
        f" 100.0 * (p_main.population_municipale - p_ref.population_municipale)"
        f" / NULLIF(p_ref.population_municipale, 0) AS delta_pct,"
        f" ST_AsGeoJSON(g.{geom_col}) AS geojson"
        f" FROM {table} g"
        f" JOIN {vue} p_main ON g.{col_geo} = p_main.{col_vue} AND p_main.annee = ?"
        f" JOIN {vue} p_ref ON g.{col_geo} = p_ref.{col_vue} AND p_ref.annee = ?"
        f"{where_sql}"
        f" ORDER BY g.nom"
    )
    return sql, params


def _build_query_contours(
    niveau: str,
    geom_col: str,
    filtre_departement: str | None,
    filtre_region: str | None,
) -> tuple[str, list]:
    """Construit la requête contours sans population. Retourne (sql, params)."""
    table = _TABLE_PAR_NIVEAU[niveau]
    code_col = _COLONNE_CODE[niveau]

    params: list = []
    where: list[str] = []

    dept_col = _FILTRE_DEPARTEMENT_COL[niveau]
    if filtre_departement and dept_col:
        where.append(f"{dept_col} = ?")
        params.append(filtre_departement)

    region_col = _FILTRE_REGION_COL[niveau]
    if filtre_region and region_col:
        where.append(f"{region_col} = ?")
        params.append(filtre_region)

    where_sql = f" WHERE {' AND '.join(where)}" if where else ""
    sql = (  # noqa: S608
        f"SELECT {code_col} AS code, nom, ST_AsGeoJSON({geom_col}) AS geojson"
        f" FROM {table}{where_sql}"
        f" ORDER BY nom"
    )
    return sql, params


def _fit_bounds_for_filter(
    con: duckdb.DuckDBPyConnection,
    niveau: str,
    geom_col: str,
    filtre_departement: str | None,
    filtre_region: str | None,
) -> list[list[float]] | None:
    """Calcule [[lat_min, lon_min], [lat_max, lon_max]] depuis les géométries filtrées."""
    table = _TABLE_PAR_NIVEAU[niveau]
    params: list = []
    where: list[str] = []

    dept_col = _FILTRE_DEPARTEMENT_COL[niveau]
    if filtre_departement and dept_col:
        where.append(f"{dept_col} = ?")
        params.append(filtre_departement)

    region_col = _FILTRE_REGION_COL[niveau]
    if filtre_region and region_col:
        where.append(f"{region_col} = ?")
        params.append(filtre_region)

    where_sql = f" WHERE {' AND '.join(where)}" if where else ""
    row = con.execute(  # noqa: S608
        f"SELECT MIN(ST_YMin({geom_col})), MIN(ST_XMin({geom_col})),"
        f" MAX(ST_YMax({geom_col})), MAX(ST_XMax({geom_col}))"
        f" FROM {table}{where_sql}",
        params,
    ).fetchone()

    if not row or row[0] is None:
        return None
    miny, minx, maxy, maxx = row
    return [[float(miny), float(minx)], [float(maxy), float(maxx)]]
