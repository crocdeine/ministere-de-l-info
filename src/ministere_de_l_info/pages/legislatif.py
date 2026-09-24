"""Page Législatif — module render() (Phase F3).

Composition politique, liste des élus, activité parlementaire
et évolution historique de l'Assemblée nationale et du Sénat.
"""

from __future__ import annotations

import logging

import plotly.express as px
import polars as pl
import streamlit as st

from ministere_de_l_info._blocs_politiques import BLOCS_ORDERED as _BLOCS_ORDERED
from ministere_de_l_info._blocs_politiques import COULEURS_BLOCS as _COULEURS_BLOCS
from ministere_de_l_info._blocs_politiques import LIBELLES_BLOCS as _LIBELLES_BLOCS
from ministere_de_l_info._theme import render_page_header
from ministere_de_l_info.viz.legislatif_queries import (
    BLOC_NON_CLASSE,
    get_activite_elu,
    get_activite_par_bloc,
    get_classement_activite,
    get_composition_politique,
    get_departements_disponibles,
    get_elus_actuels,
    get_evolution_composition_an,
    get_fiche_elu,
    get_historique_legislatures_an,
    is_data_loaded,
)

logger = logging.getLogger(__name__)

# Élus dont le groupe est absent du référentiel (ADR-0011) : affichés à part, jamais en DIV.
_COULEURS_BLOCS = {**_COULEURS_BLOCS, BLOC_NON_CLASSE: "#D9D9D9"}
_LIBELLES_BLOCS = {**_LIBELLES_BLOCS, BLOC_NON_CLASSE: "Non classé"}
_BLOCS_ORDERED = [*_BLOCS_ORDERED, BLOC_NON_CLASSE]

_DEPTS_HDF = ("02", "59", "60", "62", "80")

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
    st.plotly_chart(fig, width="stretch")

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
        width="stretch",
        hide_index=True,
        height=min(35 * display_df.height + 38, 600),
    )

    st.caption("Source : Sénat (data.senat.fr) + Assemblée nationale (Datan / data.gouv.fr)")


# ---------------------------------------------------------------------------
# Tab 3 — Activité parlementaire
# ---------------------------------------------------------------------------


def _render_fiche_depute(
    indicateur: str, classement_complet: pl.DataFrame, codes_dept: tuple[str, ...] | None
) -> None:
    """Recherche d'un député actif et fiche : scores Datan, rang, mandats et bloc."""
    deputes = get_elus_actuels(chambre="AN", codes_departement=codes_dept)
    if deputes.is_empty():
        return
    ids_par_libelle: dict[str, str] = {}
    for row in deputes.iter_rows(named=True):
        libelle = (
            f"{row['nom']} {row['prenom']} — {row['groupe_sigle'] or 'sans groupe'} "
            f"({row['nom_departement'] or row['code_departement']})"
        )
        if libelle in ids_par_libelle:  # homonymes : désambiguïser par l'identifiant
            libelle = f"{libelle} [{row['id']}]"
        ids_par_libelle[libelle] = row["id"]
    choix = st.selectbox(
        "Rechercher un député",
        list(ids_par_libelle.keys()),
        index=None,
        placeholder="Tapez un nom…",
        key="leg_fiche_depute",
    )
    if choix is None:
        return
    elu_id = ids_par_libelle[choix]

    scores = get_activite_elu(elu_id, "AN")
    if scores.is_empty():
        st.info("Aucun score d'activité Datan pour ce député.")
    else:
        dernier = scores.row(-1, named=True)
        cols = st.columns(len(_INDICATEURS_ACTIVITE))
        for col, (cle, libelle) in zip(cols, _INDICATEURS_ACTIVITE.items(), strict=True):
            valeur = dernier.get(cle)
            col.metric(libelle, "—" if valeur is None else f"{valeur:.0f}")
        st.caption(f"Scores Datan au {dernier['date_extraction']}.")

    rang = classement_complet.filter(pl.col("id") == elu_id)
    if not rang.is_empty():
        st.caption(
            f"Rang ({_INDICATEURS_ACTIVITE[indicateur]}) : {rang['rang'][0]} sur "
            f"{classement_complet.height} députés du périmètre sélectionné."
        )

    mandats = get_fiche_elu(elu_id, "AN")
    if not mandats.is_empty():
        st.dataframe(
            mandats.select(
                pl.col("legislature").alias("Législature"),
                pl.col("groupe_sigle").alias("Groupe"),
                pl.col("bloc_final")
                .replace_strict(_LIBELLES_BLOCS, default=pl.col("bloc_final"))
                .alias("Bloc"),
                pl.col("source_bloc").alias("Fondement du classement"),
            ).to_pandas(),
            width="stretch",
            hide_index=True,
        )


def _render_activite_tab(chambre: str | None, codes_dept: tuple[str, ...] | None) -> None:
    """Onglet Activité parlementaire — fiche député, classement, moyennes par bloc."""
    if chambre == "SENAT":
        st.info(
            "Scores d'activité non disponibles pour le Sénat actuellement "
            "(source Datan = Assemblée nationale uniquement)."
        )
        return

    if chambre is None:
        st.caption(
            "Scores d'activité disponibles pour l'Assemblée nationale uniquement "
            "(source Datan) : affichage des députés."
        )

    indicateur: str = st.selectbox(  # type: ignore[assignment]
        "Indicateur",
        list(_INDICATEURS_ACTIVITE.keys()),
        format_func=lambda k: _INDICATEURS_ACTIVITE[k],
        key="leg_indicateur_activite",
    )

    classement_complet = get_classement_activite(
        chambre="AN",
        indicateur=indicateur,
        codes_departement=codes_dept,
        n=None,
    )

    st.subheader("Fiche d'un député")
    _render_fiche_depute(indicateur, classement_complet, codes_dept)

    st.subheader(f"Top 20 — {_INDICATEURS_ACTIVITE[indicateur]}")
    classement = classement_complet.head(20)

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
        st.plotly_chart(fig, width="stretch")

        with st.expander(f"Classement complet ({classement_complet.height} députés)"):
            st.dataframe(
                classement_complet.select(
                    pl.col("rang").alias("Rang"),
                    pl.col("nom").alias("Nom"),
                    pl.col("prenom").alias("Prénom"),
                    pl.col("groupe_sigle").alias("Groupe"),
                    pl.col("bloc_final").alias("Bloc"),
                    pl.col("code_departement").alias("Dépt"),
                    pl.col(indicateur).alias(_INDICATEURS_ACTIVITE[indicateur]),
                ).to_pandas(),
                width="stretch",
                hide_index=True,
            )

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
        st.plotly_chart(fig_bloc, width="stretch")

        st.dataframe(bloc_pd, width="stretch", hide_index=True)

    st.caption("Source : Datan (data.gouv.fr) — scores calculés par Datan.fr")


# ---------------------------------------------------------------------------
# Tab 4 — Évolution historique
# ---------------------------------------------------------------------------


def _render_evolution_tab(chambre: str | None, codes_dept: tuple[str, ...] | None) -> None:
    """Onglet Évolution historique — AN par législature, bloc selon la législature."""
    if chambre == "SENAT":
        st.info(
            "Le Sénat n'a pas de législatures et la source ne date pas les appartenances "
            "aux groupes : évolution disponible pour l'Assemblée nationale uniquement."
        )
        return

    evol_df = get_evolution_composition_an(codes_departement=codes_dept)
    if evol_df.is_empty():
        st.info("Aucune donnée d'évolution disponible pour ce périmètre.")
        return

    partielle = evol_df["granularite"][0] != "complete"
    if partielle:
        titre = "Députés par dernière législature siégée (2002-présent)"
        st.warning(
            "Source Datan : chaque député n'est compté qu'une fois, dans sa **dernière** "
            "législature. Ce graphique ne montre donc pas la composition de chaque "
            "législature (un député élu de 2002 à 2024 n'apparaît qu'en 17e). "
            "Le bloc est celui de son groupe **dans cette législature** (ADR-0011)."
        )
    else:
        titre = "Composition de l'Assemblée nationale par législature (2002-présent)"

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
        title=titre,
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
    st.plotly_chart(fig, width="stretch")

    hist_df = get_historique_legislatures_an(codes_departement=codes_dept)
    if not hist_df.is_empty():
        with st.expander("Détail par législature"):
            hist_pd = hist_df.drop("granularite").to_pandas()
            hist_pd["période"] = hist_pd["legislature"].map(
                lambda leg: _LEGISLATURES_PERIODES.get(leg, "")
            )
            st.dataframe(hist_pd, width="stretch", hide_index=True)

    st.caption(
        "Source : Datan (data.gouv.fr). Classement des groupes par législature selon la "
        "grille officielle en vigueur à l'élection (ADR-0005, ADR-0011) : LFI est classée "
        "à gauche pour les 15e, 16e et 17e législatures. "
        "La 16e législature a été écourtée par la dissolution de juin 2024."
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

    with st.sidebar:
        st.header("Paramètres")

        chambre_label: str = st.selectbox(  # type: ignore[assignment]
            "Chambre",
            list(_CHAMBRE_MAP.keys()),
            key="leg_chambre",
        )
        chambre = _CHAMBRE_MAP[chambre_label]

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
        _render_evolution_tab(chambre, codes_dept)
