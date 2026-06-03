"""Onglet Législatives — HdF 2002-2024 (Phase D1.3)."""

from __future__ import annotations

import plotly.express as px
import polars as pl
import streamlit as st
from streamlit_folium import st_folium

from ministere_de_l_info.viz.elections_legi_queries import (
    get_circo_bounds,
    get_circos_hdf_geo,
    get_circos_hdf_legi,
    get_communes_circo_legi_geo,
    get_evolution_circo_legi,
    get_evolution_hdf_legi,
    get_hdf_bounds_circo,
    get_nuances_circo_legi,
    get_participation_hdf_legi,
    get_scores_communes_circo_legi,
    get_scores_hdf_legi,
    is_legi_data_loaded,
)
from ministere_de_l_info.viz.elections_queries import get_blocs_meta
from ministere_de_l_info.viz.maps_elections import (
    make_choropleth_elections_bloc_dominant,
    make_choropleth_legi_circos_bloc_dominant,
)

_ANNEES_LEGI: list[int] = [2002, 2007, 2012, 2017, 2022, 2024]

_WARNING_ANCIEN_DECOUPAGE = (
    "⚠️ **Ancien découpage électoral.** "
    "Les circonscriptions de 2002 et 2007 utilisaient le découpage pré-Marleix (avant 2010). "
    "Les comparaisons directes avec les scrutins 2012+ ne sont pas géographiquement valides. "
    "De plus, pour ces deux scrutins, l'attribution des bureaux de vote aux circonscriptions a été "
    "reconstruite par jointure spatiale au centroïde de chaque commune. Une fraction de ~11% des inscrits "
    "HdF réside dans des communes coupées entre plusieurs circos (Lille, Amiens, etc.) — leurs résultats "
    "peuvent être imputés à la mauvaise circo."
)


def render() -> None:
    """Vue Streamlit pour les législatives HdF 2002-2024."""
    if not is_legi_data_loaded():
        st.info(
            "Données législatives non chargées. Lancez :\n\n"
            "```bash\nuv run python scripts/load_elections_legislatives.py\n```"
        )
        return

    blocs_meta = get_blocs_meta()
    couleurs: dict[str, str] = {b[0]: b[2] for b in blocs_meta}
    libelles: dict[str, str] = {b[0]: b[1] for b in blocs_meta}
    bloc_codes: list[str] = [b[0] for b in blocs_meta]

    # ── Sélecteurs ──────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        annee: int = st.selectbox(  # type: ignore[assignment]
            "Année", _ANNEES_LEGI, index=4, key="legi_annee"
        )
    with col2:
        tour: int = st.selectbox(  # type: ignore[assignment]
            "Tour", [1, 2], format_func=lambda x: "1er" if x == 1 else "2e", key="legi_tour"
        )
    with col3:
        circos = get_circos_hdf_legi()
        options = ["(toutes — vue HdF)"] + [c[1] for c in circos]
        circo_selected: str = st.selectbox(  # type: ignore[assignment]
            "Circonscription", options, index=0, key="legi_circo"
        )

    # ── Avertissement ancien découpage ──────────────────────────────────────────
    if annee in (2002, 2007):
        st.warning(_WARNING_ANCIEN_DECOUPAGE)

    # ── Dispatch vue ────────────────────────────────────────────────────────────
    if circo_selected == "(toutes — vue HdF)":
        _render_vue_hdf(annee, tour, blocs_meta, couleurs, libelles, bloc_codes)
    else:
        code_circo = next(c[0] for c in circos if c[1] == circo_selected)
        _render_vue_circo(annee, tour, code_circo, blocs_meta, couleurs, libelles, bloc_codes)


def _render_vue_hdf(
    annee: int,
    tour: int,
    blocs_meta: list[tuple[str, str, str, int]],
    couleurs: dict[str, str],
    libelles: dict[str, str],
    bloc_codes: list[str],
) -> None:
    """Vue d'ensemble HdF — carte + métriques + tableau récapitulatif."""
    scores_df = get_scores_hdf_legi(annee, tour)
    part_df = get_participation_hdf_legi(annee, tour)
    geo_df = get_circos_hdf_geo()
    bounds = get_hdf_bounds_circo()

    if scores_df.is_empty():
        st.warning(f"Aucun résultat pour {annee} — {'1er' if tour == 1 else '2e'} tour.")
        return

    # Métriques HdF
    inscrits_tot = int(part_df["inscrits"].sum()) if not part_df.is_empty() else 0
    taux_moy = float(part_df["taux_participation_pct"].mean()) if not part_df.is_empty() else 0.0
    dominant_hdf = (
        scores_df.group_by("bloc")
        .agg(pl.sum("voix").alias("voix_total"))
        .sort("voix_total", descending=True)
        .row(0)[0]
    )
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Inscrits HdF", f"{inscrits_tot:,}".replace(",", " "))
    m2.metric("Participation moy.", f"{taux_moy:.1f} %")
    m3.metric("Bloc dominant HdF", libelles.get(dominant_hdf, dominant_hdf))
    m4.metric("Circos 1er tour", f"{scores_df['code_circo'].n_unique()}")

    st.caption(
        "Source : data.gouv.fr — Données des élections agrégées. "
        "Classement des blocs : nomenclature officielle Ministère de l'Intérieur."
    )

    # Carte choroplèthe circos
    st.subheader(f"Carte HdF par circonscription — {annee}, {'1er' if tour == 1 else '2e'} tour")
    if not geo_df.is_empty():
        try:
            carte = make_choropleth_legi_circos_bloc_dominant(
                scores_df, geo_df, blocs_meta, bounds, "Bloc dominant"
            )
            st_folium(carte, width="100%", height=550, returned_objects=[])
        except Exception as exc:
            st.error(f"Erreur carte : {exc}")

    # Tableau récapitulatif par bloc
    st.divider()
    st.subheader("Récapitulatif par bloc")

    voix_tot_hdf = int(scores_df["voix"].sum())
    dom_map = (
        scores_df.sort("voix", descending=True)
        .unique("code_circo", keep="first")
        .group_by("bloc")
        .agg(pl.count("code_circo").alias("circos_gagnees"))
    )
    recap = (
        scores_df.group_by("bloc")
        .agg(pl.sum("voix").alias("voix_total"))
        .with_columns(
            (pl.col("voix_total").cast(pl.Float64) * 100.0 / voix_tot_hdf).alias("pct_hdf")
        )
        .join(dom_map, on="bloc", how="left")
        .fill_null(0)
        .sort("voix_total", descending=True)
        .with_columns(pl.col("bloc").replace(libelles).alias("Bloc"))
        .select(["Bloc", "voix_total", "pct_hdf", "circos_gagnees"])
        .rename(
            {"voix_total": "Voix totales", "pct_hdf": "% HdF", "circos_gagnees": "Circos gagnées"}
        )
    )
    st.dataframe(
        recap.to_pandas().style.format({"Voix totales": "{:,.0f}", "% HdF": "{:.1f}"}),
        use_container_width=True,
        hide_index=True,
    )

    # Évolution temporelle HdF
    st.divider()
    st.subheader("Évolution des blocs — HdF législatives 2002-2024")
    _render_evolution_chart(
        annee,
        tour,
        libelles,
        bloc_codes,
        couleurs,
        None,
        hdf_mode=True,
    )


def _render_vue_circo(
    annee: int,
    tour: int,
    code_circo: str,
    blocs_meta: list[tuple[str, str, str, int]],
    couleurs: dict[str, str],
    libelles: dict[str, str],
    bloc_codes: list[str],
) -> None:
    """Vue détaillée d'une circonscription — carte, métriques, graphe, tableau."""
    scores_df = get_scores_communes_circo_legi(annee, tour, code_circo)
    geo_df = get_communes_circo_legi_geo(annee, tour, code_circo)
    bounds = get_circo_bounds(code_circo)
    nuances_df = get_nuances_circo_legi(annee, tour, code_circo)

    if scores_df.is_empty():
        st.warning(f"Aucun résultat pour {code_circo} — {annee} t{tour}.")
        return

    # Métriques circo
    voix_tot = int(nuances_df["voix"].sum()) if not nuances_df.is_empty() else 0
    dom_circo = (
        nuances_df.group_by("bloc")
        .agg(pl.sum("voix").alias("v"))
        .sort("v", descending=True)
        .row(0)[0]
        if not nuances_df.is_empty()
        else "—"
    )

    m1, m2, m3 = st.columns(3)
    m1.metric("Circonscription", code_circo)
    m2.metric("Voix exprimées", f"{voix_tot:,}".replace(",", " "))
    m3.metric("Bloc dominant", libelles.get(dom_circo, dom_circo))

    # Carte des communes de la circo
    st.subheader(f"Carte — {code_circo}, {annee} t{tour}")
    if not geo_df.is_empty() and not scores_df.is_empty():
        try:
            carte = make_choropleth_elections_bloc_dominant(
                scores_df, geo_df, blocs_meta, bounds, f"Blocs — {code_circo}"
            )
            st_folium(carte, width="100%", height=450, returned_objects=[])
        except Exception as exc:
            st.error(f"Erreur carte : {exc}")

    # Graphe barres par bloc
    st.divider()
    st.subheader("Résultats par bloc")
    blocs_circo = (
        nuances_df.group_by("bloc")
        .agg(pl.sum("voix").alias("voix"))
        .with_columns(
            (pl.col("voix").cast(pl.Float64) * 100.0 / max(voix_tot, 1)).alias("pct"),
            pl.col("bloc").replace(libelles).alias("Bloc"),
        )
        .sort("voix", descending=True)
    )
    fig_bar = px.bar(
        blocs_circo.to_pandas(),
        x="Bloc",
        y="voix",
        color="bloc",
        color_discrete_map=couleurs,
        category_orders={"bloc": bloc_codes},
        labels={"voix": "Voix", "Bloc": "Bloc politique"},
        text_auto=True,
        height=320,
    )
    fig_bar.update_layout(showlegend=False, margin={"t": 20, "b": 20})
    st.plotly_chart(fig_bar, use_container_width=True)

    # Évolution temporelle de la circo
    st.divider()
    st.subheader(f"Évolution des blocs — {code_circo} 2002-2024")
    _render_evolution_chart(annee, tour, libelles, bloc_codes, couleurs, code_circo, hdf_mode=False)

    # Tableau nuances
    st.divider()
    st.subheader("Détail par nuance")
    if not nuances_df.is_empty():
        table = (
            nuances_df.with_columns(
                (pl.col("voix").cast(pl.Float64) * 100.0 / max(voix_tot, 1)).alias("% exp."),
                pl.col("bloc").replace(libelles).alias("Bloc"),
            )
            .select(["nuance", "Bloc", "voix", "% exp."])
            .rename({"nuance": "Nuance", "voix": "Voix"})
        )
        st.dataframe(
            table.to_pandas().style.format({"Voix": "{:,.0f}", "% exp.": "{:.1f}"}),
            use_container_width=True,
            hide_index=True,
        )


def _render_evolution_chart(
    annee: int,
    tour: int,
    libelles: dict[str, str],
    bloc_codes: list[str],
    couleurs: dict[str, str],
    code_circo: str | None,
    hdf_mode: bool,
) -> None:
    """Graphe d'évolution temporelle (HdF ou circo), avec zone grisée 2002/2007."""
    ev_left, ev_right = st.columns([1, 3])
    with ev_left:
        tour_evol: int = st.radio(  # type: ignore[assignment]
            "Tour (évolution)",
            [1, 2],
            format_func=lambda x: "1er" if x == 1 else "2e",
            horizontal=True,
            key=f"legi_tour_evol_{'hdf' if hdf_mode else code_circo}",
        )
        mode_evol: str = st.radio(  # type: ignore[assignment]
            "Unité",
            ["Voix totales", "Part des exprimés (%)"],
            key=f"legi_mode_evol_{'hdf' if hdf_mode else code_circo}",
        )

    ev_df = get_evolution_hdf_legi() if hdf_mode else get_evolution_circo_legi(code_circo)  # type: ignore[arg-type]

    if ev_df.is_empty():
        st.info("Données d'évolution non disponibles.")
        return

    ev_t = ev_df.filter(pl.col("tour") == tour_evol)

    if mode_evol == "Part des exprimés (%)":
        totaux = ev_t.group_by("annee").agg(pl.sum("voix_total").alias("total"))
        ev_plot = ev_t.join(totaux, on="annee").with_columns(
            (
                pl.col("voix_total").cast(pl.Float64) * 100.0 / pl.col("total").cast(pl.Float64)
            ).alias("pct")
        )
        y_col, y_label = "pct", "Part des exprimés (%)"
    else:
        ev_plot = ev_t
        y_col, y_label = "voix_total", "Voix totales"

    fig = px.line(
        ev_plot.to_pandas(),
        x="annee",
        y=y_col,
        color="bloc",
        color_discrete_map=couleurs,
        category_orders={"bloc": bloc_codes},
        markers=True,
        labels={"annee": "Année", y_col: y_label, "bloc": "Bloc"},
        height=380,
    )
    # Zone grisée pour l'ancien découpage (2002-2007)
    fig.add_vrect(
        x0=2001,
        x1=2007.5,
        fillcolor="lightgray",
        opacity=0.25,
        line_width=0,
        annotation_text="Ancien découpage",
        annotation_position="top left",
        annotation_font_size=10,
    )
    fig.update_layout(
        xaxis={"tickmode": "array", "tickvals": _ANNEES_LEGI},
        legend_title_text="Bloc",
        margin={"t": 30, "b": 30},
    )
    fig.update_traces(hovertemplate="<b>%{x}</b><br>%{y:,.0f}<extra>%{fullData.name}</extra>")
    with ev_right:
        st.plotly_chart(fig, use_container_width=True)
