"""Visualisations cartographiques — Folium."""

from __future__ import annotations

import json
import logging

import branca.colormap as cm
import duckdb
import folium
import folium.features

logger = logging.getLogger(__name__)

_CENTRE_FRANCE = [46.5, 2.5]
_ZOOM_DEPART = 5
_SOURCE = "Source : data.geopf.fr (IGN ADMIN-EXPRESS COG) — Population INSEE 2024"

# Bornes arrondies : Corse (1) / régions moyennes (5) / grandes (5) / ARA (1) / IDF (1)
_BREAKS_POP = [0, 1_000_000, 4_000_000, 7_000_000, 10_000_000, 13_000_000]
_COLORS_YLORD5 = ["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"]

_LEGENDES: dict[str, str] = {
    "population": "Population estimée 2024",
}


def _fmt_fr(n: int) -> str:
    """Formate un entier en notation française (espace insécable comme séparateur de milliers)."""
    return f"{n:,}".replace(",", " ")


def _build_legend_html(indicateur: str) -> str:
    """Construit le HTML d'une légende custom pour la carte choroplèthe population."""
    titre = _LEGENDES.get(indicateur, indicateur.capitalize())
    breaks = _BREAKS_POP
    colors = _COLORS_YLORD5

    rows = []
    for i, color in enumerate(colors):
        lo = breaks[i]
        hi = breaks[i + 1]
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


def make_regions_choropleth(
    con: duckdb.DuckDBPyConnection,
    indicateur: str,
) -> folium.Map:
    """Construit une carte choroplèthe des régions françaises.

    Args:
        con: connexion DuckDB avec l'extension spatial chargée.
        indicateur: colonne à cartographier (ex. "population").
    """
    rows = con.execute("""
        SELECT code_insee, nom, population, ST_AsGeoJSON(geometry) AS geojson
        FROM geographies_regions
        ORDER BY nom
    """).fetchall()

    if not rows:
        raise RuntimeError(
            "Table geographies_regions vide. Lancez d'abord scripts/etl_regions.py."
        )

    # Construction du FeatureCollection avec propriétés pour le tooltip
    features = []
    for code_insee, nom, population, geojson_str in rows:
        features.append({
            "type": "Feature",
            "properties": {
                "code_insee": code_insee,
                "nom": nom,
                "population": population,
                "population_fmt": _fmt_fr(population),
            },
            "geometry": json.loads(geojson_str),
        })

    geojson_data = {"type": "FeatureCollection", "features": features}

    colormap = cm.StepColormap(
        colors=_COLORS_YLORD5,
        index=_BREAKS_POP,
        vmin=_BREAKS_POP[0],
        vmax=_BREAKS_POP[-1],
    )

    m = folium.Map(
        location=_CENTRE_FRANCE,
        zoom_start=_ZOOM_DEPART,
        tiles="CartoDB positron",
    )

    folium.GeoJson(
        geojson_data,
        style_function=lambda f: {
            "fillColor": colormap(f["properties"]["population"]),
            "fillOpacity": 0.75,
            "color": "white",
            "weight": 0.5,
        },
        highlight_function=lambda _f: {"fillOpacity": 0.92, "weight": 2},
        tooltip=folium.features.GeoJsonTooltip(
            fields=["nom", "population_fmt"],
            aliases=["Région :", "Population :"],
            style="font-family: sans-serif; font-size: 12px; padding: 6px;",
            sticky=True,
        ),
    ).add_to(m)

    # Légende HTML custom (format FR, sans D3)
    m.get_root().html.add_child(folium.Element(_build_legend_html(indicateur)))

    # Bandeau source en bas à droite
    source_html = (
        '<div style="position:fixed;bottom:12px;right:12px;z-index:1000;'
        "background:white;color:#222;padding:4px 10px;border-radius:4px;"
        'font-size:11px;color:#555;border:1px solid #ddd;pointer-events:none;">'
        f"{_SOURCE}</div>"
    )
    m.get_root().html.add_child(folium.Element(source_html))

    return m
