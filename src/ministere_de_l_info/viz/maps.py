"""Visualisations cartographiques — Folium."""

from __future__ import annotations

import json
import logging
from typing import Literal

import branca.colormap as cm
import duckdb
import folium
import folium.features

logger = logging.getLogger(__name__)

_CENTRE_FRANCE = [46.5, 2.5]
_ZOOM_DEPART = 5
_SOURCE = "Source : data.geopf.fr (IGN ADMIN-EXPRESS COG) — Population INSEE"

_NIVEAUX_SUPPORTES: frozenset[str] = frozenset(
    {
        "region",
        "departement",
        "epci",
        "arrondissement_municipal",
        "circonscription",
        "commune",
    }
)
# Niveaux pour lesquels une vue population existe
_NIVEAUX_POPULATION: frozenset[str] = frozenset(
    {"region", "departement", "epci", "commune"}
)
# Niveaux sans agrégation population possible — contours est le comportement normal
_NIVEAUX_CONTOURS: frozenset[str] = frozenset(
    {"arrondissement_municipal", "circonscription"}
)

_TABLE_PAR_NIVEAU: dict[str, str] = {
    "region": "geographies_regions",
    "departement": "geographies_departements",
    "epci": "geographies_epci",
    "arrondissement_municipal": "geographies_arrondissements_municipaux",
    "circonscription": "geographies_circonscriptions",
    "commune": "geographies_communes",
}

_COLONNE_CODE: dict[str, str] = {
    "region": "code_insee",
    "departement": "code_insee",
    "epci": "code_siren",
    "arrondissement_municipal": "code_insee",
    "circonscription": "code",
    "commune": "code_insee",
}

# Géométrie utilisée en vue nationale (pas de filtre actif)
_GEOMETRIE_NATIONALE: dict[str, str] = {
    "region": "geometry_simplified_national",
    "departement": "geometry_simplified_national",
    "epci": "geometry_simplified_epci",
    "arrondissement_municipal": "geometry_simplified_communal",
    "circonscription": "geometry_simplified_circo",
    "commune": "geometry_simplified_communal",
}

# Géométrie plus détaillée quand un filtre géographique est actif
_GEOMETRIE_ZOOM: dict[str, str] = {
    "region": "geometry_simplified_regional",
    "departement": "geometry_simplified_departemental",
    "epci": "geometry_simplified_epci",
    "arrondissement_municipal": "geometry_simplified_communal",
    "circonscription": "geometry_simplified_circo",
    "commune": "geometry_simplified_communal",
}

_VUE_PAR_NIVEAU: dict[str, str] = {
    "region": "v_population_region",
    "departement": "v_population_departement",
    "epci": "v_population_epci",
    "commune": "v_population_commune",
}

# (colonne clé dans table géo, colonne correspondante dans la vue population)
_CLE_JOIN: dict[str, tuple[str, str]] = {
    "region": ("code_insee", "code_region"),
    "departement": ("code_insee", "code_departement"),
    "epci": ("code_siren", "code_epci"),
    "commune": ("code_insee", "code_commune"),
}

# Colonne filtre département dans chaque table géo (None = filtre non applicable)
_FILTRE_DEPARTEMENT_COL: dict[str, str | None] = {
    "region": None,
    "departement": None,
    "epci": "code_departement_principal",
    "arrondissement_municipal": None,  # ARM : code_commune_mere seulement, pas de col. dpt
    "circonscription": "code_departement",
    "commune": "code_departement",
}

# Colonne filtre région dans chaque table géo
_FILTRE_REGION_COL: dict[str, str | None] = {
    "region": None,
    "departement": "code_region",
    "epci": None,
    "arrondissement_municipal": None,
    "circonscription": None,
    "commune": "code_region",
}

_LIBELLES_NIVEAUX: dict[str, str] = {
    "region": "Région",
    "departement": "Département",
    "epci": "EPCI",
    "arrondissement_municipal": "Arrondissement municipal",
    "circonscription": "Circonscription",
    "commune": "Commune",
}

_COULEURS_YLORD5 = ["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"]
_COULEUR_CONTOURS = "#4292c6"
_COULEUR_FOND_CONTOURS = "#f7f7f7"


def _fmt_fr(n: float) -> str:
    """Formate un nombre en notation française (espace insécable comme séparateur de milliers)."""
    return f"{int(n):,}".replace(",", " ")


def _build_legend_html(titre: str, breaks: list[float], colors: list[str]) -> str:
    """Construit le HTML d'une légende discrète à fond blanc (contraste WCAG AA)."""
    rows = []
    for i, color in enumerate(colors):
        lo, hi = breaks[i], breaks[i + 1]
        if i == 0:
            label = f"&lt; {_fmt_fr(hi)}"
        elif i == len(colors) - 1:
            label = f"&ge; {_fmt_fr(lo)}"
        else:
            label = f"{_fmt_fr(lo)}&nbsp;&ndash; {_fmt_fr(hi)}"
        rows.append(
            f'<div style="display:flex;align-items:center;gap:7px;margin-bottom:3px;">'
            f'<div style="width:20px;height:14px;background:{color};'
            f'border:1px solid #bbb;flex-shrink:0;"></div>'
            f'<span style="white-space:nowrap;">{label}</span>'
            f"</div>"
        )
    rows_html = "\n".join(rows)
    return (
        '<div style="position:fixed;bottom:40px;left:12px;z-index:1000;'
        "background:white;color:#222;padding:10px 14px;border-radius:6px;"
        'border:1px solid #ccc;font-size:12px;font-family:sans-serif;pointer-events:none;">'
        f'<div style="font-weight:600;margin-bottom:7px;">{titre}</div>'
        f"{rows_html}"
        "</div>"
    )


def _compute_breaks(values: list[float], n_classes: int = 5) -> list[float]:
    """Calcule n_classes+1 bornes équidistantes depuis les valeurs observées."""
    if not values:
        return [0.0] * (n_classes + 1)
    vmin, vmax = min(values), max(values)
    if vmin == vmax:
        spread = max(abs(vmin) * 0.1, 1.0)
        vmin, vmax = vmin - spread, vmax + spread * n_classes
    step = (vmax - vmin) / n_classes
    return [vmin + i * step for i in range(n_classes + 1)]


def _get_geometry_column(niveau: str, *, zoomed: bool) -> str:
    """Retourne la colonne géométrie adaptée selon le contexte (national ou zoomé)."""
    if zoomed:
        return _GEOMETRIE_ZOOM.get(niveau, _GEOMETRIE_NATIONALE[niveau])
    return _GEOMETRIE_NATIONALE[niveau]


def _check_population_disponible(
    con: duckdb.DuckDBPyConnection, niveau: str, annee: int
) -> bool:
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


def make_choropleth(
    con: duckdb.DuckDBPyConnection,
    niveau: str,
    indicateur: str = "population_municipale",
    annee: int = 2023,
    filtre_departement: str | None = None,
    filtre_region: str | None = None,
    titre: str | None = None,
    palette: str = "YlOrRd",  # réservé pour extension future multi-palettes
    mode: Literal["choropleth", "contours", "auto"] = "auto",
) -> folium.Map:
    """Crée une carte choroplèthe ou de contours Folium pour un niveau territorial donné.

    Pour niveau='commune', filtre_departement est obligatoire.
    mode='auto' bascule automatiquement en contours si les données population sont absentes.
    """
    if niveau not in _NIVEAUX_SUPPORTES:
        raise ValueError(
            f"Niveau '{niveau}' invalide. Niveaux supportés : {sorted(_NIVEAUX_SUPPORTES)}"
        )
    if niveau == "commune" and not filtre_departement:
        raise ValueError(
            "Pour niveau='commune', filtre_departement est obligatoire "
            "(~35 000 communes satureraient le navigateur)."
        )

    mode_effectif = _resolve_mode(niveau, mode, con, annee)
    zoomed = bool(filtre_departement or filtre_region)
    geom_col = _get_geometry_column(niveau, zoomed=zoomed)

    if mode_effectif == "choropleth":
        sql, params = _build_query_choropleth(
            niveau, indicateur, annee, geom_col, filtre_departement, filtre_region
        )
        rows = con.execute(sql, params).fetchall()
        if not rows:
            logger.warning(
                "Requête choropleth vide pour niveau='%s' malgré vue non vide — fallback contours.",
                niveau,
            )
            mode_effectif = "contours"

    if mode_effectif == "contours":
        sql, params = _build_query_contours(
            niveau, geom_col, filtre_departement, filtre_region
        )
        rows = con.execute(sql, params).fetchall()

    if not rows:
        raise RuntimeError(
            f"Table {_TABLE_PAR_NIVEAU[niveau]} vide ou inaccessible. "
            "Lancez d'abord l'ETL correspondant."
        )

    # Construction du FeatureCollection GeoJSON
    features: list[dict] = []
    values: list[float] = []

    if mode_effectif == "choropleth":
        for code, nom, valeur, geojson_str in rows:
            v = float(valeur) if valeur is not None else 0.0
            values.append(v)
            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "code": code,
                        "nom": nom,
                        "valeur": v,
                        "valeur_fmt": _fmt_fr(v),
                    },
                    "geometry": json.loads(geojson_str),
                }
            )
    else:
        for code, nom, geojson_str in rows:
            features.append(
                {
                    "type": "Feature",
                    "properties": {"code": code, "nom": nom},
                    "geometry": json.loads(geojson_str),
                }
            )

    geojson_data = {"type": "FeatureCollection", "features": features}

    m = folium.Map(
        location=_CENTRE_FRANCE, zoom_start=_ZOOM_DEPART, tiles="CartoDB positron"
    )

    if zoomed:
        bounds = _fit_bounds_for_filter(
            con, niveau, geom_col, filtre_departement, filtre_region
        )
        if bounds:
            m.fit_bounds(bounds)

    libelle = _LIBELLES_NIVEAUX[niveau]

    if mode_effectif == "choropleth":
        breaks = _compute_breaks(values)
        colormap = cm.StepColormap(
            colors=_COULEURS_YLORD5,
            index=breaks,
            vmin=breaks[0],
            vmax=breaks[-1],
        )
        style_fn = lambda f, _cm=colormap: {  # noqa: E731
            "fillColor": _cm(f["properties"]["valeur"]),
            "fillOpacity": 0.75,
            "color": "white",
            "weight": 0.5,
        }
        tooltip_fields = ["nom", "valeur_fmt"]
        tooltip_aliases = [
            f"{libelle} :",
            f"{indicateur.replace('_', ' ').capitalize()} :",
        ]
    else:
        style_fn = lambda _f: {  # noqa: E731
            "fillColor": _COULEUR_FOND_CONTOURS,
            "fillOpacity": 0.4,
            "color": _COULEUR_CONTOURS,
            "weight": 1.0,
        }
        tooltip_fields = ["nom", "code"]
        tooltip_aliases = [f"{libelle} :", "Code :"]

    folium.GeoJson(
        geojson_data,
        style_function=style_fn,
        highlight_function=lambda _f: {"fillOpacity": 0.9, "weight": 2},
        tooltip=folium.features.GeoJsonTooltip(
            fields=tooltip_fields,
            aliases=tooltip_aliases,
            style="font-family: sans-serif; font-size: 12px; padding: 6px;",
            sticky=True,
        ),
    ).add_to(m)

    if mode_effectif == "choropleth":
        if titre is None:
            titre = f"{indicateur.replace('_', ' ').capitalize()} — {annee}"
        m.get_root().html.add_child(
            folium.Element(_build_legend_html(titre, breaks, _COULEURS_YLORD5))
        )

    source_txt = f"{_SOURCE}{' ' + str(annee) if mode_effectif == 'choropleth' else ''}"
    m.get_root().html.add_child(
        folium.Element(
            '<div style="position:fixed;bottom:12px;right:12px;z-index:1000;background:white;'
            f"color:#555;padding:4px 10px;border-radius:4px;font-size:11px;border:1px solid #ddd;"
            f'pointer-events:none;">{source_txt}</div>'
        )
    )

    return m
