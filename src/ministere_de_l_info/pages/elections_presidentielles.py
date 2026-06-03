"""Onglet Présidentielles — extrait de la page Élections (Phase C)."""

from __future__ import annotations

import plotly.express as px
import polars as pl
import streamlit as st
from streamlit_folium import st_folium

from ministere_de_l_info.viz.elections_queries import (
    DB_PATH,
    get_blocs_meta,
    get_bounds,
    get_communes_geo,
    get_evolution_blocs,
    get_participation_communes,
    get_scores_communes,
    is_data_loaded,
)
from ministere_de_l_info.viz.maps_elections import (
    make_choropleth_elections_bloc_dominant,
    make_choropleth_elections_score_bloc,
)

_ANNEES: list[int] = [2002, 2007, 2012, 2017, 2022]
_ZONES: dict[str, str] = {
    "circo21": "Circo 21 — Valenciennes (20 communes)",
    "hdf": "Hauts-de-France entière ⚠️ lent",
}
_MODES_CARTE: list[str] = ["Bloc dominant", "Score d'un bloc"]


def render() -> None:
    """Vue Streamlit pour les présidentielles HdF 2002-2022."""
    # DB path vérifiée dans l'entrée page — ici on vérifie uniquement les données
    if not DB_PATH.exists():
        st.error(
            "Base de données absente. Lancez d'abord :\n\n"
            "```bash\nuv run python scripts/init_elections_schema.py\n```"
        )
        return

    if not is_data_loaded():
        st.warning(
            "Données électorales non chargées. Lancez :\n\n"
            "```bash\nuv run python scripts/load_elections_presidentielles.py\n```"
        )
        return

    blocs_meta = get_blocs_meta()
    couleurs: dict[str, str] = {b[0]: b[2] for b in blocs_meta}
    libelles: dict[str, str] = {b[0]: b[1] for b in blocs_meta}
    bloc_codes: list[str] = [b[0] for b in blocs_meta]

    # ── Sélecteurs ──────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns([2, 1, 2, 2])
    with c1:
        annee: int = st.selectbox("Année", _ANNEES, index=len(_ANNEES) - 1, key="pres_annee")  # type: ignore[assignment]
    with c2:
        tour: int = st.radio(  # type: ignore[assignment]
            "Tour",
            [1, 2],
            format_func=lambda x: "1er" if x == 1 else "2e",
            horizontal=True,
            key="pres_tour",
        )
    with c3:
        zone: str = st.radio(  # type: ignore[assignment]
            "Zone",
            list(_ZONES),
            format_func=lambda x: _ZONES[x],
            key="pres_zone",
        )
    with c4:
        mode_carte: str = st.radio("Mode de carte", _MODES_CARTE, key="pres_mode_carte")  # type: ignore[assignment]
        bloc_sel: str = bloc_codes[3]
        if mode_carte == "Score d'un bloc":
            bloc_sel = st.selectbox(  # type: ignore[assignment]
                "Bloc",
                bloc_codes,
                format_func=lambda x: f"{x} — {libelles[x]}",
                key="pres_bloc_sel",
            )

    # ── Données ─────────────────────────────────────────────────────────────────
    scores_df = get_scores_communes(annee, tour, zone)
    part_df = get_participation_communes(annee, tour, zone)
    geo_df = get_communes_geo(zone)
    bounds = get_bounds(zone)

    if scores_df.is_empty():
        st.warning(f"Aucun résultat pour {annee} — {'1er' if tour == 1 else '2e'} tour.")
        return

    if geo_df.is_empty():
        st.error("Géométries communales absentes. Lancez d'abord l'ETL géographie.")
        return

    # ── Métriques ────────────────────────────────────────────────────────────────
    n_communes = scores_df["code_commune"].n_unique()
    inscrits_tot = int(part_df["inscrits"].sum()) if not part_df.is_empty() else 0
    taux_moy = float(part_df["taux_participation_pct"].mean()) if not part_df.is_empty() else 0.0
    bloc_zone = (
        scores_df.group_by("bloc")
        .agg(pl.sum("voix").alias("voix_total"))
        .sort("voix_total", descending=True)
        .row(0)[0]
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Communes", f"{n_communes:,}")
    m2.metric("Inscrits", f"{inscrits_tot:,}".replace(",", " "))
    m3.metric("Participation", f"{taux_moy:.1f} %")
    m4.metric("Bloc majoritaire", libelles.get(bloc_zone, "—"))

    st.caption(
        "Source : data.gouv.fr — Données des élections agrégées. "
        "Classement des blocs : nomenclature officielle Ministère de l'Intérieur "
        "(voir docs/sources-officielles/nuances/)."
    )

    # ── Carte ───────────────────────────────────────────────────────────────────
    st.subheader(f"Carte — {annee}, {'1er' if tour == 1 else '2e'} tour")

    try:
        if mode_carte == "Bloc dominant":
            carte = make_choropleth_elections_bloc_dominant(
                scores_df, geo_df, blocs_meta, bounds, "Bloc dominant"
            )
        else:
            carte = make_choropleth_elections_score_bloc(
                scores_df,
                part_df,
                geo_df,
                bloc_sel,
                couleurs[bloc_sel],
                libelles[bloc_sel],
                bounds,
                f"Score {bloc_sel}",
            )
        st_folium(carte, width="100%", height=600, returned_objects=[])
    except Exception as exc:
        st.error(f"Erreur carte : {exc}")

    # ── Évolution temporelle ─────────────────────────────────────────────────────
    st.divider()
    st.subheader("Évolution des blocs politiques sur 25 ans")

    ev_left, ev_right = st.columns([1, 3])
    with ev_left:
        tour_evol: int = st.radio(  # type: ignore[assignment]
            "Tour (évolution)",
            [1, 2],
            format_func=lambda x: "1er" if x == 1 else "2e",
            horizontal=True,
            key="pres_tour_evol",
        )
        mode_evol: str = st.radio(  # type: ignore[assignment]
            "Unité",
            ["Voix totales", "Part des exprimés (%)"],
            horizontal=False,
            key="pres_mode_evol",
        )

    ev_df = get_evolution_blocs(zone)
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
    )
    fig.update_layout(
        xaxis={"tickmode": "array", "tickvals": _ANNEES},
        legend_title_text="Bloc",
        height=380,
        margin={"t": 30, "b": 30},
    )
    fig.update_traces(hovertemplate="<b>%{x}</b><br>%{y:,.0f}<extra>%{fullData.name}</extra>")
    with ev_right:
        st.plotly_chart(fig, use_container_width=True)

    # ── Tableau détail ───────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Détail par commune")

    pivot = scores_df.pivot(
        values="voix", index="code_commune", on="bloc", aggregate_function="sum"
    ).fill_null(0)
    for b in bloc_codes:
        if b not in pivot.columns:
            pivot = pivot.with_columns(pl.lit(0).cast(pl.Int64).alias(b))

    dominant_df = (
        scores_df.sort("voix", descending=True)
        .unique("code_commune", keep="first")
        .rename({"bloc": "bloc_dominant"})
        .select(["code_commune", "bloc_dominant"])
    )

    table_df = (
        pivot.join(geo_df.select(["code_commune", "nom"]), on="code_commune", how="left")
        .join(
            part_df.select(["code_commune", "inscrits", "exprimes", "taux_participation_pct"]),
            on="code_commune",
            how="left",
        )
        .join(dominant_df, on="code_commune", how="left")
        .fill_null(0)
    )

    blocs_disponibles = sorted(
        table_df["bloc_dominant"].cast(pl.Utf8).drop_nulls().unique().to_list()
    )
    filtre_blocs = st.multiselect(
        "Filtrer par bloc dominant",
        options=blocs_disponibles,
        format_func=lambda x: f"{x} — {libelles.get(x, x)}",
        key="pres_filtre_blocs",
    )
    if filtre_blocs:
        table_df = table_df.filter(pl.col("bloc_dominant").is_in(filtre_blocs))

    col_ordre = [
        "nom",
        "inscrits",
        "exprimes",
        "taux_participation_pct",
        "bloc_dominant",
    ] + bloc_codes
    col_ordre = [c for c in col_ordre if c in table_df.columns]
    table_display = (
        table_df.select(col_ordre)
        .rename(
            {
                "nom": "Commune",
                "inscrits": "Inscrits",
                "exprimes": "Exprimés",
                "taux_participation_pct": "Particip. %",
                "bloc_dominant": "Bloc dominant",
            }
        )
        .sort("Commune")
    )

    st.dataframe(table_display, use_container_width=True, hide_index=True, height=400)

    csv_bytes = table_display.write_csv().encode("utf-8")
    st.download_button(
        "Télécharger en CSV",
        data=csv_bytes,
        file_name=f"elections_{annee}_t{tour}_{zone}.csv",
        mime="text/csv",
        key="pres_download_csv",
    )
