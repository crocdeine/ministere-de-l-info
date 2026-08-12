"""Page Législatif — module render() (Phase F3).

Composition politique, liste des élus, activité parlementaire
et évolution historique de l'Assemblée nationale et du Sénat.
"""

from __future__ import annotations

import logging

import plotly.express as px
import polars as pl
import streamlit as st

from ministere_de_l_info._theme import render_page_header
from ministere_de_l_info.viz.legislatif_queries import (
    get_activite_par_bloc,
    get_classement_activite,
    get_composition_politique,
    get_departements_disponibles,
    get_elus_actuels,
    get_evolution_composition_an,
    get_historique_legislatures_an,
    is_data_loaded,
)

logger = logging.getLogger(__name__)

_DEPTS_HDF = ("02", "59", "60", "62", "80")

_COULEURS_BLOCS: dict[str, str] = {
    "EXG": "#8B0000",
    "GAU": "#DD0000",
    "DIV": "#888888",
    "CENT": "#FFEB00",
    "DTE": "#0066CC",
    "EXD": "#0D378A",
}
_LIBELLES_BLOCS: dict[str, str] = {
    "EXG": "Extrême gauche",
    "GAU": "Gauche",
    "DIV": "Divers",
    "CENT": "Centre",
    "DTE": "Droite",
    "EXD": "Extrême droite",
}
_BLOCS_ORDERED = ["EXG", "GAU", "DIV", "CENT", "DTE", "EXD"]

_CHAMBRE_MAP: dict[str, str | None] = {
    "Toutes": None,
    "Assemblée nationale": "AN",
    "Sénat": "SENAT",
}

_INDICATEURS_ACTIVITE: dict[str, str] = {
    "score_participation": "Participation (%)",
    "score_loyaute": "Loyauté au groupe (%)",
    "score_majorite": "Proximité majorité (%)",
    "score_participation_specialite": "Participation spécialisée (%)",
}

_LEGISLATURES_PERIODES: dict[int, str] = {
    12: "2002-2007",
    13: "2007-2012",
    14: "2012-2017",
    15: "2017-2022",
    16: "2022-2024 (dissolution)",
    17: "2024-présent",
}


def _parse_dept_filter(dept_label: str) -> tuple[str, ...] | None:
    """Convertit le label du sélecteur en tuple de codes département."""
    if dept_label == "Tous (France)":
        return None
    if dept_label == "Hauts-de-France (région)":
        return _DEPTS_HDF
    code = dept_label.rsplit("(", 1)[1].rstrip(")")
    return (code,)


# ---------------------------------------------------------------------------
# Tab 1 — Composition politique
# ---------------------------------------------------------------------------


def _render_pie(chambre: str, codes_dept: tuple[str, ...] | None) -> None:
    """Camembert de composition pour une chambre."""
    df = get_composition_politique(chambre=chambre, codes_departement=codes_dept)
    if df.is_empty():
        st.info("Aucune donnée de composition disponible.")
        return

    total = df["nb_elus"].sum()
    fig = px.pie(
        df.to_pandas(),
        names="bloc_final",
        values="nb_elus",
        color="bloc_final",
        color_discrete_map=_COULEURS_BLOCS,
        category_orders={"bloc_final": _BLOCS_ORDERED},
        title=f"Composition — {chambre} ({total} élus)",
    )
    fig.update_traces(
        textposition="inside",
        textinfo="label+value+percent",
        hovertemplate="<b>%{label}</b><br>%{value} élus (%{percent})<extra></extra>",
    )
    fig.update_layout(height=400, margin={"t": 50, "b": 20})
    st.plotly_chart(fig, use_container_width=True)

    blocs_present = [b for b in _BLOCS_ORDERED if b in df["bloc_final"].to_list()]
    if blocs_present:
        cols = st.columns(len(blocs_present))
        bloc_counts = dict(zip(df["bloc_final"].to_list(), df["nb_elus"].to_list(), strict=True))
        for i, bloc in enumerate(blocs_present):
            with cols[i]:
                st.metric(_LIBELLES_BLOCS.get(bloc, bloc), bloc_counts.get(bloc, 0))


def _render_composition_tab(chambre: str | None, codes_dept: tuple[str, ...] | None) -> None:
    """Onglet Composition politique."""
    if chambre is None:
        col_an, col_senat = st.columns(2)
        with col_an:
            _render_pie("AN", codes_dept)
        with col_senat:
            _render_pie("SENAT", codes_dept)
    else:
        _render_pie(chambre, codes_dept)


# ---------------------------------------------------------------------------
# Tab 2 — Liste des élus
# ---------------------------------------------------------------------------


def _render_elus_tab(chambre: str | None, codes_dept: tuple[str, ...] | None) -> None:
    """Onglet Liste des élus — tableau filtrable."""
    recherche = st.text_input("Rechercher un élu", key="leg_recherche_elu")

    df = get_elus_actuels(chambre=chambre, codes_departement=codes_dept)
    if df.is_empty():
        st.info("Aucun élu trouvé avec ces filtres.")
        return

    if recherche:
        q = recherche.lower()
        df = df.filter(
            pl.col("nom").str.to_lowercase().str.contains(q, literal=True)
            | pl.col("prenom").str.to_lowercase().str.contains(q, literal=True)
        )
        if df.is_empty():
            st.info(f"Aucun résultat pour « {recherche} ».")
            return

    st.caption(f"{df.height} élus affichés")

    display_df = df.select(
        [
            pl.col("nom"),
            pl.col("prenom"),
            pl.col("chambre"),
            pl.col("code_departement").alias("dept"),
            pl.col("nom_departement"),
            pl.col("num_circo").alias("circo"),
            pl.col("groupe_sigle").alias("groupe"),
            pl.col("bloc_final").alias("bloc"),
            pl.col("profession"),
        ]
    )

    st.dataframe(
        display_df.to_pandas(),
        use_container_width=True,
        hide_index=True,
        height=min(35 * display_df.height + 38, 600),
    )

    st.caption("Source : Sénat (data.senat.fr) + Assemblée nationale (Datan / data.gouv.fr)")


# ---------------------------------------------------------------------------
# Tab 3 — Activité parlementaire
# ---------------------------------------------------------------------------


def _render_activite_tab(chambre: str | None, codes_dept: tuple[str, ...] | None) -> None:
    """Onglet Activité parlementaire — classement + moyennes par bloc."""
    if chambre == "SENAT":
        st.info(
            "Scores d'activité non disponibles pour le Sénat actuellement "
            "(source Datan = Assemblée nationale uniquement)."
        )
        return

    if chambre is None:
        st.info(
            "Sélectionnez « Assemblée nationale » pour afficher les scores d'activité. "
            "Les données Datan ne couvrent que l'AN."
        )
        return

    indicateur: str = st.selectbox(  # type: ignore[assignment]
        "Indicateur",
        list(_INDICATEURS_ACTIVITE.keys()),
        format_func=lambda k: _INDICATEURS_ACTIVITE[k],
        key="leg_indicateur_activite",
    )

    st.subheader(f"Top 20 — {_INDICATEURS_ACTIVITE[indicateur]}")
    classement = get_classement_activite(
        chambre="AN",
        indicateur=indicateur,
        codes_departement=codes_dept,
    )

    if classement.is_empty():
        st.info("Aucun score disponible.")
    else:
        classement_pd = classement.with_columns(
            (pl.col("nom") + " " + pl.col("prenom")).alias("elu"),
        ).to_pandas()

        fig = px.bar(
            classement_pd,
            y="elu",
            x=indicateur,
            color="bloc_final",
            color_discrete_map=_COULEURS_BLOCS,
            orientation="h",
            title=f"Classement — {_INDICATEURS_ACTIVITE[indicateur]}",
            labels={
                indicateur: _INDICATEURS_ACTIVITE[indicateur],
                "elu": "Député",
                "bloc_final": "Bloc",
            },
        )
        fig.update_layout(
            height=max(500, 25 * classement.height),
            margin={"t": 50, "b": 30, "l": 200},
            yaxis={"categoryorder": "total ascending"},
        )
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Tableau détaillé"):
            st.dataframe(classement.to_pandas(), use_container_width=True, hide_index=True)

    st.subheader("Activité moyenne par bloc politique")
    bloc_df = get_activite_par_bloc(codes_departement=codes_dept)

    if bloc_df.is_empty():
        st.info("Aucune donnée d'activité par bloc.")
    else:
        bloc_order = {b: i for i, b in enumerate(_BLOCS_ORDERED)}
        bloc_pd = bloc_df.to_pandas()
        bloc_pd["_order"] = bloc_pd["bloc"].map(
            lambda b: bloc_order.get(b, 99)  # noqa: B023
        )
        bloc_pd = bloc_pd.sort_values("_order").drop(columns="_order")

        fig_bloc = px.bar(
            bloc_pd,
            x="bloc",
            y="moy_participation",
            color="bloc",
            color_discrete_map=_COULEURS_BLOCS,
            title="Participation moyenne par bloc",
            labels={"bloc": "Bloc politique", "moy_participation": "Score moyen (%)"},
            text="nb_elus",
        )
        fig_bloc.update_traces(texttemplate="%{text} élus", textposition="outside")
        fig_bloc.update_layout(height=420, margin={"t": 50, "b": 30}, showlegend=False)
        st.plotly_chart(fig_bloc, use_container_width=True)

        st.dataframe(bloc_pd, use_container_width=True, hide_index=True)

    st.caption("Source : Datan (data.gouv.fr) — scores calculés par Datan.fr")


# ---------------------------------------------------------------------------
# Tab 4 — Évolution historique
# ---------------------------------------------------------------------------


def _render_evolution_tab() -> None:
    """Onglet Évolution historique — composition AN par législature."""
    evol_df = get_evolution_composition_an()
    if evol_df.is_empty():
        st.info("Aucune donnée d'évolution disponible.")
        return

    evol_pd = evol_df.to_pandas()
    evol_pd["legislature_label"] = evol_pd["legislature"].map(
        lambda leg: f"{leg}e ({_LEGISLATURES_PERIODES.get(leg, '')})"
    )

    leg_order = sorted(evol_pd["legislature"].unique())
    label_order = [f"{leg}e ({_LEGISLATURES_PERIODES.get(leg, '')})" for leg in leg_order]

    fig = px.bar(
        evol_pd,
        x="legislature_label",
        y="nb_elus",
        color="bloc_final",
        color_discrete_map=_COULEURS_BLOCS,
        category_orders={
            "bloc_final": _BLOCS_ORDERED,
            "legislature_label": label_order,
        },
        title="Composition de l'Assemblée nationale par législature (2002-présent)",
        labels={
            "legislature_label": "Législature",
            "nb_elus": "Nombre de députés",
            "bloc_final": "Bloc",
        },
    )
    fig.update_layout(
        height=500,
        margin={"t": 60, "b": 40},
        barmode="stack",
        xaxis_tickangle=-30,
    )
    st.plotly_chart(fig, use_container_width=True)

    hist_df = get_historique_legislatures_an()
    if not hist_df.is_empty():
        with st.expander("Détail par législature"):
            hist_pd = hist_df.to_pandas()
            hist_pd["période"] = hist_pd["legislature"].map(
                lambda leg: _LEGISLATURES_PERIODES.get(leg, "")
            )
            st.dataframe(hist_pd, use_container_width=True, hide_index=True)

    st.caption(
        "Source : Datan (data.gouv.fr). "
        "Chaque député est compté dans sa législature de référence (dernière). "
        "Note : la 16e législature a été écourtée par la dissolution de juin 2024."
    )


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------


def render() -> None:
    """Point d'entrée de la page Législatif."""
    if not is_data_loaded():
        st.warning("Données législatives non chargées. Lancez :")
        st.code("uv run python scripts/load_legislatif.py")
        return

    render_page_header(
        icon="account_balance",
        title="Législatif",
        subtitle="Assemblée nationale & Sénat",
    )

    col_chambre, col_dept = st.columns(2)
    with col_chambre:
        chambre_label: str = st.selectbox(  # type: ignore[assignment]
            "Chambre",
            list(_CHAMBRE_MAP.keys()),
            key="leg_chambre",
        )
    chambre = _CHAMBRE_MAP[chambre_label]

    with col_dept:
        depts_df = get_departements_disponibles()
        dept_options = ["Tous (France)", "Hauts-de-France (région)"]
        if not depts_df.is_empty():
            dept_options += [
                f"{row['nom_departement']} ({row['code_departement']})"
                for row in depts_df.iter_rows(named=True)
            ]
        dept_label: str = st.selectbox(  # type: ignore[assignment]
            "Département",
            dept_options,
            key="leg_dept",
        )
    codes_dept = _parse_dept_filter(dept_label)

    tab_composition, tab_elus, tab_activite, tab_evolution = st.tabs(
        [
            "📊 Composition politique",
            "👥 Liste des élus",
            "🏆 Activité parlementaire",
            "📈 Évolution historique",
        ]
    )

    with tab_composition:
        _render_composition_tab(chambre, codes_dept)
    with tab_elus:
        _render_elus_tab(chambre, codes_dept)
    with tab_activite:
        _render_activite_tab(chambre, codes_dept)
    with tab_evolution:
        _render_evolution_tab()
