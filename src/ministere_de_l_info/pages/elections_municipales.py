"""Onglet Municipales — HdF 2008-2026 (Phase D3.3)."""

from __future__ import annotations

import plotly.express as px
import polars as pl
import streamlit as st
from streamlit_folium import st_folium

from ministere_de_l_info.viz.elections_muni_queries import (
    get_communes_hdf_muni_list,
    get_communes_muni_geo,
    get_evolution_blocs_hdf_muni,
    get_hdf_bounds_communes,
    get_listes_commune_muni,
    get_metrics_commune_muni,
    get_scores_bloc_commune_muni,
    get_scrutins_muni,
    is_muni_data_loaded,
)
from ministere_de_l_info.viz.elections_queries import get_blocs_meta
from ministere_de_l_info.viz.maps_elections import make_choropleth_muni_communes_bloc_dominant

_ANNEES_MUNI: list[int] = [2008, 2014, 2020, 2026]

_WARNINGS_SEUIL: dict[int, str] = {
    2008: (
        "ℹ️ **Seuil de nuançage 2008** : 3 500 habitants. "
        "**164 communes HdF** sont nuancées dans le fichier officiel data.gouv.fr "
        "(sur ~318 communes ≥ 3 500 hab attendues).\n\n"
        "⚠️ **Limitation de la source data.gouv.fr 2008** : le fichier Parquet officiel publié "
        "par le Ministère de l'Intérieur est incomplet pour le département du Nord (59), "
        "qui n'apparaît qu'avec **2 communes** (Seclin et Pérenchies). "
        "Les grandes villes du Nord — Lille, Roubaix, Tourcoing, Valenciennes, Dunkerque — "
        "sont absentes du fichier. "
        "Cette lacune n'est pas due au seuil de nuançage mais à une extraction partielle de la source.\n\n"
        "Répartition observée HdF : Aisne 13 · Nord 2 · Oise 32 · Pas-de-Calais 102 · Somme 15.\n\n"
        "Sur la carte, les communes absentes du fichier apparaissent en gris, "
        "comme les communes < 3 500 hab non nuancées."
    ),
    2014: (
        "ℹ️ **Seuil de nuançage 2014** : 1 000 habitants. "
        "**~3 778 communes HdF** apparaissent avec nuance — "
        "seuil exceptionnellement bas pour ce scrutin uniquement. "
        "Les communes sans nuance apparaissent en gris hachuré sur la carte."
    ),
    2020: (
        "ℹ️ **Seuil de nuançage 2020** : 3 500 habitants "
        "(circulaire INTA1931378J du 3 février 2020, après décision CE 31/01/2020 n°437675 "
        "qui a annulé un seuil initial de 9 000 hab). "
        "Les ~660 communes HdF de 1 000-3 499 hab ont des résultats bruts "
        "mais pas de classement par bloc. "
        "Les communes sans nuance apparaissent en gris hachuré sur la carte."
    ),
    2026: (
        "ℹ️ **Seuil de nuançage 2026** : 3 500 habitants "
        "(circulaire INTP2602966C du 2 février 2026, validée par CE 27/02/2026 n°512694). "
        "**320 communes HdF** sont nuancées (3 500 hab et + chefs-lieux d'arrondissement). "
        "Les ~3 459 communes plus petites ont des résultats bruts sans classement politique. "
        "Les communes sans nuance apparaissent en gris hachuré sur la carte."
    ),
}

_ANNOTATION_LFI = (
    "ⓘ La nuance LFI est classée **GAUCHE** jusqu'aux européennes 2024 incluses, "
    "puis **EXTRÊME GAUCHE** à partir des municipales 2026 "
    "(circulaire INTP2602966C, validée par CE 27/02/2026 n°512694). "
    "La hausse du bloc EXG entre 2020 et 2026 reflète ce changement de classement officiel, "
    "pas une évolution électorale réelle de LFI."
)


def render() -> None:
    """Vue Streamlit pour les municipales HdF 2008-2026."""
    if not is_muni_data_loaded():
        st.info(
            "Données municipales non chargées. Lancez :\n\n"
            "```bash\nuv run python scripts/load_elections_municipales.py\n"
            "uv run python scripts/migrations/0007_add_municipales_views.py\n```"
        )
        return

    st.subheader("🗳️ Municipales — Hauts-de-France")

    blocs_meta = get_blocs_meta()
    couleurs: dict[str, str] = {b[0]: b[2] for b in blocs_meta}
    libelles: dict[str, str] = {b[0]: b[1] for b in blocs_meta}
    bloc_codes: list[str] = [b[0] for b in blocs_meta]

    # Sélecteur scrutin
    scrutins = get_scrutins_muni()
    if not scrutins:
        st.warning("Aucun scrutin municipal trouvé en base.")
        return

    labels = [s[2] for s in scrutins]
    selected_label: str = st.selectbox(  # type: ignore[assignment]
        "Scrutin",
        labels,
        index=0,
        key="muni_scrutin",
    )
    annee, tour = next((s[0], s[1]) for s in scrutins if s[2] == selected_label)

    # Warning dynamique seuil nuançage
    _render_warning_seuil(annee, tour)

    # Carte HdF par bloc dominant
    _render_carte_hdf(annee, tour, blocs_meta)

    # Évolution blocs HdF
    _render_evolution_hdf(libelles, bloc_codes, couleurs)

    # Drill-down commune
    st.divider()
    st.subheader("🔍 Détail par commune")
    _render_drilldown_commune(annee, tour, libelles)


def _render_warning_seuil(annee: int, tour: int) -> None:
    msg = _WARNINGS_SEUIL.get(annee)
    if msg:
        st.info(msg)


def _render_carte_hdf(
    annee: int,
    tour: int,
    blocs_meta: list[tuple[str, str, str, int]],
) -> None:
    tour_lbl = "1er" if tour == 1 else "2e"
    st.subheader(f"Carte HdF par bloc dominant — {annee}, {tour_lbl} tour")

    geo_df = get_communes_muni_geo(annee, tour)
    bounds = get_hdf_bounds_communes()

    if geo_df.is_empty():
        st.warning(f"Aucune géométrie disponible pour {annee} — {tour_lbl} tour.")
        return

    try:
        carte = make_choropleth_muni_communes_bloc_dominant(
            geo_df, blocs_meta, bounds, "Bloc dominant"
        )
        st_folium(carte, width="100%", height=580, returned_objects=[])
    except Exception as exc:
        st.error(f"Erreur carte : {exc}")

    st.caption(
        "Source : data.gouv.fr — Données des élections agrégées. "
        "Classement des blocs : nomenclature officielle Ministère de l'Intérieur."
    )


def _render_evolution_hdf(
    libelles: dict[str, str],
    bloc_codes: list[str],
    couleurs: dict[str, str],
) -> None:
    st.divider()
    st.subheader("Évolution des blocs — HdF municipales 2008-2026")

    ev_df = get_evolution_blocs_hdf_muni()
    if ev_df.is_empty():
        st.info("Données d'évolution non disponibles.")
        return

    # Uniquement t1 pour la cohérence de la comparaison temporelle
    ev_t1 = ev_df.filter((pl.col("tour") == 1) & pl.col("bloc").is_not_null())

    if not ev_t1.is_empty():
        ev_plot = ev_t1.with_columns(pl.col("bloc").replace(libelles).alias("Bloc"))
        fig = px.line(
            ev_plot.to_pandas(),
            x="annee",
            y="voix",
            color="bloc",
            color_discrete_map=couleurs,
            category_orders={"bloc": bloc_codes},
            markers=True,
            labels={"annee": "Année", "voix": "Voix totales", "bloc": "Bloc"},
            height=360,
        )
        fig.update_layout(
            xaxis={"tickmode": "array", "tickvals": _ANNEES_MUNI},
            legend_title_text="Bloc",
            margin={"t": 30, "b": 30},
        )
        fig.update_traces(hovertemplate="<b>%{x}</b><br>%{y:,.0f}<extra>%{fullData.name}</extra>")
        st.plotly_chart(fig, width="stretch")

    st.caption(_ANNOTATION_LFI)

    # Voix non classées (bloc IS NULL)
    ev_null = ev_df.filter((pl.col("tour") == 1) & pl.col("bloc").is_null())
    if not ev_null.is_empty():
        ev_t1_total = ev_df.filter(pl.col("tour") == 1)
        totaux = ev_t1_total.group_by("annee").agg(pl.sum("voix").alias("total"))
        null_avec_total = ev_null.join(totaux, on="annee", how="left").with_columns(
            (pl.col("voix").cast(pl.Float64) * 100.0 / pl.col("total").cast(pl.Float64)).alias(
                "pct_nc"
            )
        )
        parts = []
        for row in null_avec_total.sort("annee").iter_rows(named=True):
            parts.append(f"{row['annee']} : {row['pct_nc']:.1f}%")
        st.caption("Voix non classées (communes hors seuil) — 1er tour : " + " | ".join(parts))


def _render_drilldown_commune(annee: int, tour: int, libelles: dict[str, str]) -> None:
    communes = get_communes_hdf_muni_list(annee, tour)
    if not communes:
        st.info("Aucune commune disponible pour ce scrutin.")
        return

    options = ["(aucune sélection)"] + [f"{nom} ({code})" for code, nom in communes]
    selected: str = st.selectbox(  # type: ignore[assignment]
        "Commune",
        options,
        index=0,
        key=f"muni_drilldown_{annee}_{tour}",
        help="Choisir une commune pour afficher le détail des listes.",
    )

    if selected == "(aucune sélection)":
        return

    code_commune = selected.rsplit("(", 1)[1].rstrip(")")
    nom_commune = selected.rsplit(" (", 1)[0]

    metrics = get_metrics_commune_muni(annee, tour, code_commune)
    st.caption(f"Commune sélectionnée : **{nom_commune}** ({code_commune})")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Inscrits", f"{metrics['inscrits']:,}".replace(",", " "))
    m2.metric("Votants", f"{metrics['votants']:,}".replace(",", " "))
    m3.metric("Participation", f"{metrics['taux_participation_pct']:.1f} %")
    if metrics["est_nuancee"] and metrics["bloc_dominant"]:
        m4.metric("Bloc dominant", libelles.get(metrics["bloc_dominant"], "—"))
    else:
        m4.metric("Bloc dominant", "Non classé")

    if not metrics["est_nuancee"]:
        st.warning(
            f"ℹ️ **{nom_commune}** est une commune **non nuancée** pour ce scrutin "
            f"(population < seuil de nuançage). Les listes sont affichées ci-dessous "
            "mais sans classement politique par bloc."
        )

    # Vue par bloc
    st.markdown("##### Répartition par bloc politique")
    if metrics["est_nuancee"]:
        bloc_df = get_scores_bloc_commune_muni(annee, tour, code_commune)
        bloc_classee = bloc_df.filter(pl.col("bloc").is_not_null())
        if not bloc_classee.is_empty():
            table_bloc = (
                bloc_classee.with_columns(
                    pl.col("bloc").replace(libelles).alias("Bloc"),
                    pl.col("pct_exprimes").fill_null(0.0),
                )
                .select(["Bloc", "voix", "pct_exprimes"])
                .rename({"voix": "Voix", "pct_exprimes": "% exprimés"})
            )
            st.dataframe(
                table_bloc.to_pandas().style.format({"Voix": "{:,.0f}", "% exprimés": "{:.2f}"}),
                width="stretch",
                hide_index=True,
            )
        else:
            st.caption("Aucune donnée de bloc disponible.")
    else:
        st.caption("Vue bloc indisponible — commune non nuancée.")

    # Vue par liste
    st.markdown("##### Détail des listes")
    listes_df = get_listes_commune_muni(annee, tour, code_commune)

    if listes_df.is_empty():
        st.warning(f"Aucune liste trouvée pour {nom_commune}.")
    else:
        table_listes = (
            listes_df.with_columns(
                pl.col("bloc").fill_null("—").alias("Bloc"),
                pl.col("nuance").fill_null("—").alias("Nuance"),
                pl.col("nom_tete_liste").fill_null("—").alias("Nom tête de liste"),
                pl.col("prenom_tete_liste").fill_null("").alias("Prénom"),
                pl.col("libelle_abrege_liste").fill_null("—").alias("Libellé abrégé"),
                pl.col("pct_exprimes").fill_null(0.0),
            )
            .select(
                [
                    "rang",
                    "Nuance",
                    "Bloc",
                    "Libellé abrégé",
                    "Nom tête de liste",
                    "voix",
                    "pct_exprimes",
                ]
            )
            .rename({"rang": "Rang", "voix": "Voix", "pct_exprimes": "% exprimés"})
        )
        st.dataframe(
            table_listes.to_pandas().style.format({"Voix": "{:,.0f}", "% exprimés": "{:.2f}"}),
            width="stretch",
            hide_index=True,
        )

        csv_data = listes_df.write_csv().encode("utf-8-sig")
        st.download_button(
            f"Télécharger les listes de {nom_commune} en CSV",
            data=csv_data,
            file_name=f"listes_muni_{annee}_t{tour}_{code_commune}.csv",
            mime="text/csv",
            key=f"muni_dl_listes_{annee}_{tour}_{code_commune}",
        )
