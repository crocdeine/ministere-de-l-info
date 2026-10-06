"""Visualisations cartographiques — Folium."""

from __future__ import annotations

import json
import logging
from typing import Literal

import branca.colormap as cm
import duckdb
import folium
import folium.features
import streamlit as st

from ministere_de_l_info.config import get_settings
from ministere_de_l_info.sources import LO2, mention
from ministere_de_l_info.viz._config import (
    _CENTRE_FRANCE,
    _LIBELLES_NIVEAUX,
    _NIVEAUX_SUPPORTES,
    _SOURCE,
    _TABLE_PAR_NIVEAU,
    _VUE_PAR_NIVEAU,
    _ZOOM_DEPART,
)
from ministere_de_l_info.viz._display import (
    _COULEUR_CONTOURS,
    _COULEUR_FOND_CONTOURS,
    _COULEURS_EVOLUTION5,
    _COULEURS_YLORD5,
    _SEUILS_EVOLUTION,
    COULEUR_ND,
    NOTE_CLASSES_FIXES,
    _build_legend_html,
    _fmt_fr,
    _fmt_pct,
    ajouter_html,
    bornes_fixes,
    nouvelle_carte,
)
from ministere_de_l_info.viz._queries import (
    _build_query_choropleth,
    _build_query_contours,
    _build_query_evolution,
    _fit_bounds_for_filter,
    _get_geometry_column,
    _resolve_mode,
    open_ro,
)

logger = logging.getLogger(__name__)


def make_choropleth(
    con: duckdb.DuckDBPyConnection,
    niveau: str,
    indicateur: str = "population_municipale",
    annee: int = 2023,
    annee_ref: int | None = None,
    filtre_departement: str | None = None,
    filtre_region: str | None = None,
    titre: str | None = None,
    palette: str = "YlOrRd",  # réservé pour extension future multi-palettes
    mode: Literal["choropleth", "contours", "auto"] = "auto",
) -> folium.Map:
    """Crée une carte choroplèthe ou de contours Folium pour un niveau territorial donné.

    Pour niveau='commune', filtre_departement est obligatoire.
    Si annee_ref est fourni (et niveau supporte la population), la carte affiche
    l'évolution démographique (%) entre annee_ref et annee avec une palette divergente orange-violet.
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

    mode_effectif = _resolve_mode(niveau, mode, con, annee, logger)
    zoomed = bool(filtre_departement or filtre_region)
    geom_col = _get_geometry_column(niveau, zoomed=zoomed)
    is_evolution = annee_ref is not None and niveau in _VUE_PAR_NIVEAU

    if mode_effectif == "choropleth":
        if annee_ref is not None and is_evolution:
            sql, params = _build_query_evolution(
                niveau,
                annee,
                annee_ref,
                geom_col,
                filtre_departement,
                filtre_region,  # type: ignore[arg-type]
            )
        else:
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
        sql, params = _build_query_contours(niveau, geom_col, filtre_departement, filtre_region)
        rows = con.execute(sql, params).fetchall()

    if not rows:
        raise RuntimeError(
            f"Table {_TABLE_PAR_NIVEAU[niveau]} vide ou inaccessible. "
            "Lancez d'abord l'ETL correspondant."
        )

    # Construction du FeatureCollection GeoJSON
    features: list[dict] = []

    if mode_effectif == "choropleth":
        if is_evolution:
            for code, nom, delta_abs, delta_pct, geojson_str in rows:
                v = float(delta_pct) if delta_pct is not None else None
                if v is None or delta_abs is None:
                    fmt = "n.d."  # population de référence absente ou nulle : pas de 0 inventé
                else:
                    icon = "↗" if v > 1.0 else ("↘" if v < -1.0 else "→")
                    abs_val = int(delta_abs)
                    abs_str = (f"+{abs_val:,}" if abs_val >= 0 else f"{abs_val:,}").replace(
                        ",", " "
                    )
                    fmt = f"{icon} {v:+.1f}% ({abs_str} hab)"
                features.append(
                    {
                        "type": "Feature",
                        "properties": {
                            "code": code,
                            "nom": nom,
                            "valeur": v,
                            "valeur_fmt": fmt,
                        },
                        "geometry": json.loads(geojson_str),
                    }
                )
        else:
            for code, nom, valeur, geojson_str in rows:
                v = float(valeur) if valeur is not None else None
                features.append(
                    {
                        "type": "Feature",
                        "properties": {
                            "code": code,
                            "nom": nom,
                            "valeur": v,
                            "valeur_fmt": "n.d." if v is None else _fmt_fr(v),
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

    m = nouvelle_carte(_CENTRE_FRANCE, _ZOOM_DEPART)

    if zoomed:
        bounds = _fit_bounds_for_filter(con, niveau, geom_col, filtre_departement, filtre_region)
        if bounds:
            m.fit_bounds(bounds)

    libelle = _LIBELLES_NIVEAUX[niveau]

    if mode_effectif == "choropleth":
        if is_evolution:
            breaks = _SEUILS_EVOLUTION
            legend_colors = _COULEURS_EVOLUTION5
            colormap = cm.StepColormap(
                colors=_COULEURS_EVOLUTION5,
                index=_SEUILS_EVOLUTION,
                vmin=_SEUILS_EVOLUTION[0],
                vmax=_SEUILS_EVOLUTION[-1],
            )
            tooltip_aliases = [
                f"{libelle} :",
                f"Évolution {annee_ref}→{annee} :",
            ]
        else:
            breaks = bornes_fixes(f"{indicateur}:{niveau}")
            legend_colors = _COULEURS_YLORD5
            colormap = cm.StepColormap(
                colors=_COULEURS_YLORD5,
                index=breaks,
                vmin=breaks[0],
                vmax=breaks[-1],
            )
            tooltip_aliases = [
                f"{libelle} :",
                f"{indicateur.replace('_', ' ').capitalize()} :",
            ]
        style_fn = lambda f, _cm=colormap: {  # noqa: E731
            "fillColor": COULEUR_ND
            if f["properties"]["valeur"] is None
            else _cm(f["properties"]["valeur"]),
            "fillOpacity": 0.75,
            "color": "white",
            "weight": 0.5,
        }
        tooltip_fields = ["nom", "valeur_fmt"]
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
            titre = (
                f"Évolution démographique {annee_ref} → {annee}"
                if is_evolution
                else f"{indicateur.replace('_', ' ').capitalize()} — {annee}"
            )
        ajouter_html(
            m,
            folium.Element(
                _build_legend_html(
                    titre,
                    breaks,
                    legend_colors,
                    fmt_fn=_fmt_pct if is_evolution else None,
                    note=None if is_evolution else NOTE_CLASSES_FIXES,
                    avec_nd=any(f["properties"]["valeur"] is None for f in features),
                )
            ),
        )

    if mode_effectif == "choropleth" and is_evolution:
        source_suffix = f" ({annee_ref}→{annee})"
    elif mode_effectif == "choropleth":
        source_suffix = f" {annee}"
    else:
        source_suffix = ""
    source = (
        f"Source : {mention('circos')} (non officiel)"
        if niveau == "circonscription"
        else f"{_SOURCE} — {LO2}"
    )
    source_txt = f"{source}{source_suffix}"
    ajouter_html(
        m,
        folium.Element(
            '<div style="position:fixed;bottom:12px;right:12px;z-index:1000;background:white;'
            f"color:#555;padding:4px 10px;border-radius:4px;font-size:11px;border:1px solid #ddd;"
            f'pointer-events:none;">{source_txt}</div>'
        ),
    )

    return m


# ponytail: Map partagée entre sessions (cache_resource, 32 entrées max) ; st_folium ne la modifie pas.
@st.cache_resource(max_entries=32, show_spinner="Construction de la carte…")
def get_carte_cache(
    niveau: str,
    annee: int,
    annee_ref: int | None,
    filtre_departement: str | None,
    filtre_region: str | None,
    titre: str,
    mode: Literal["choropleth", "contours", "auto"],
) -> folium.Map:
    """`make_choropleth` en cache (connexion courte) ; les exceptions ne sont pas mises en cache."""
    con = open_ro(get_settings().db_path)
    try:
        return make_choropleth(
            con,
            niveau=niveau,
            annee=annee,
            annee_ref=annee_ref,
            filtre_departement=filtre_departement,
            filtre_region=filtre_region,
            titre=titre,
            mode=mode,
        )
    finally:
        con.close()
