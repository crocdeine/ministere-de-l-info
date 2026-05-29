"""Cartes choroplèthes électorales — Folium (C3)."""

from __future__ import annotations

import json

import branca.colormap as cm
import folium
import folium.features
import polars as pl

from ministere_de_l_info.viz._display import _build_legend_html, _fmt_fr

_SOURCE_HTML: str = (
    '<div style="position:fixed;bottom:12px;right:12px;z-index:1000;background:white;'
    "color:#555;padding:4px 10px;border-radius:4px;font-size:11px;border:1px solid #ddd;"
    'pointer-events:none;">Source : data.gouv.fr — Élections agrégées</div>'
)


def _legend_blocs_html(blocs_meta: list[tuple[str, str, str, int]], titre: str) -> str:
    rows = [
        f'<div style="display:flex;align-items:center;gap:7px;margin-bottom:3px;">'
        f'<div style="width:20px;height:14px;background:{couleur};border:1px solid #bbb;'
        f'flex-shrink:0;"></div>'
        f'<span style="white-space:nowrap;">{libelle}</span>'
        f"</div>"
        for _, libelle, couleur, _ in blocs_meta
    ]
    return (
        '<div style="position:fixed;bottom:40px;left:12px;z-index:1000;'
        "background:white;color:#222;padding:10px 14px;border-radius:6px;"
        'border:1px solid #ccc;font-size:12px;font-family:sans-serif;pointer-events:none;">'
        f'<div style="font-weight:600;margin-bottom:7px;">{titre}</div>'
        + "\n".join(rows)
        + "</div>"
    )


def make_choropleth_elections_bloc_dominant(
    scores_df: pl.DataFrame,
    geo_df: pl.DataFrame,
    blocs_meta: list[tuple[str, str, str, int]],
    bounds: list[list[float]] | None,
    titre: str,
) -> folium.Map:
    """Carte bloc dominant par commune (couleur unie du bloc le plus voté)."""
    couleurs = {b[0]: b[2] for b in blocs_meta}
    libelles = {b[0]: b[1] for b in blocs_meta}

    # Bloc dominant par commune : première ligne après tri descendant
    dominant_map: dict[str, tuple[str, int]] = {}
    for row in scores_df.sort("voix", descending=True).iter_rows(named=True):
        code = row["code_commune"]
        if code not in dominant_map:
            dominant_map[code] = (row["bloc"], row["voix"])

    # Top 3 blocs par commune pour le tooltip
    top3: dict[str, list[tuple[str, int]]] = {}
    for row in scores_df.sort("voix", descending=True).iter_rows(named=True):
        code = row["code_commune"]
        lst = top3.setdefault(code, [])
        if len(lst) < 3:
            lst.append((row["bloc"], row["voix"]))

    features: list[dict] = []
    for row in geo_df.iter_rows(named=True):
        code = row["code_commune"]
        if not row["geojson"]:
            continue
        bloc_dom, voix_dom = dominant_map.get(code, (None, 0))
        couleur = couleurs.get(bloc_dom, "#cccccc") if bloc_dom else "#cccccc"
        top3_txt = " | ".join(
            f"{libelles.get(b, b)} : {_fmt_fr(float(v))}" for b, v in top3.get(code, [])
        )
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "code": code,
                    "nom": row["nom"],
                    "bloc_dominant": libelles.get(bloc_dom, "—") if bloc_dom else "—",
                    "voix_dominant": _fmt_fr(float(voix_dom)) if voix_dom else "—",
                    "top3": top3_txt or "—",
                    "_couleur": couleur,
                },
                "geometry": json.loads(row["geojson"]),
            }
        )

    m = folium.Map(location=[50.35, 3.4], zoom_start=10, tiles="CartoDB positron")
    if bounds:
        m.fit_bounds(bounds)

    folium.GeoJson(
        {"type": "FeatureCollection", "features": features},
        style_function=lambda f: {
            "fillColor": f["properties"]["_couleur"],
            "fillOpacity": 0.8,
            "color": "white",
            "weight": 0.8,
        },
        highlight_function=lambda _f: {"fillOpacity": 0.95, "weight": 2},
        tooltip=folium.features.GeoJsonTooltip(
            fields=["nom", "bloc_dominant", "voix_dominant", "top3"],
            aliases=["Commune :", "Bloc dominant :", "Voix :", "Top 3 :"],
            style="font-family: sans-serif; font-size: 12px; padding: 6px;",
            sticky=True,
        ),
    ).add_to(m)

    m.get_root().html.add_child(folium.Element(_legend_blocs_html(blocs_meta, titre)))
    m.get_root().html.add_child(folium.Element(_SOURCE_HTML))
    return m


def make_choropleth_elections_score_bloc(
    scores_df: pl.DataFrame,
    participation_df: pl.DataFrame,
    geo_df: pl.DataFrame,
    bloc: str,
    couleur_bloc: str,
    libelle_bloc: str,
    bounds: list[list[float]] | None,
    titre: str,
) -> folium.Map:
    """Carte score d'un bloc spécifique (dégradé blanc → couleur selon % exprimés)."""
    bloc_scores = scores_df.filter(pl.col("bloc") == bloc)
    merged = bloc_scores.join(
        participation_df.select(["code_commune", "exprimes"]), on="code_commune", how="left"
    ).with_columns(
        pl.when(pl.col("exprimes") > 0)
        .then(pl.col("voix").cast(pl.Float64) * 100.0 / pl.col("exprimes").cast(pl.Float64))
        .otherwise(0.0)
        .alias("pct")
    )
    pct_map: dict[str, tuple[int, float]] = {
        r[0]: (r[1], float(r[2]))
        for r in merged.select(["code_commune", "voix", "pct"]).iter_rows()
    }

    max_val = max((v[1] for v in pct_map.values()), default=30.0)
    max_val = max(max_val, 1.0)
    colormap = cm.LinearColormap(colors=["#ffffff", couleur_bloc], vmin=0.0, vmax=max_val)

    features: list[dict] = []
    for row in geo_df.iter_rows(named=True):
        code = row["code_commune"]
        if not row["geojson"]:
            continue
        voix, pct = pct_map.get(code, (0, 0.0))
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "code": code,
                    "nom": row["nom"],
                    "pct_fmt": f"{pct:.1f} %",
                    "voix_fmt": _fmt_fr(float(voix)),
                    "_pct": pct,
                },
                "geometry": json.loads(row["geojson"]),
            }
        )

    m = folium.Map(location=[50.35, 3.4], zoom_start=10, tiles="CartoDB positron")
    if bounds:
        m.fit_bounds(bounds)

    folium.GeoJson(
        {"type": "FeatureCollection", "features": features},
        style_function=lambda f, _cm=colormap: {
            "fillColor": _cm(f["properties"]["_pct"]),
            "fillOpacity": 0.85,
            "color": "white",
            "weight": 0.8,
        },
        highlight_function=lambda _f: {"fillOpacity": 0.95, "weight": 2},
        tooltip=folium.features.GeoJsonTooltip(
            fields=["nom", "pct_fmt", "voix_fmt"],
            aliases=["Commune :", f"{libelle_bloc} (% expr.) :", "Voix :"],
            style="font-family: sans-serif; font-size: 12px; padding: 6px;",
            sticky=True,
        ),
    ).add_to(m)

    n = 5
    step = max_val / n
    breaks = [i * step for i in range(n + 1)]
    legend_colors = [colormap((i + 0.5) * step)[:7] for i in range(n)]
    m.get_root().html.add_child(
        folium.Element(
            _build_legend_html(
                f"{titre} (% exprimés)",
                breaks,
                legend_colors,
                fmt_fn=lambda x: f"{x:.0f}%",
            )
        )
    )
    m.get_root().html.add_child(folium.Element(_SOURCE_HTML))
    return m
