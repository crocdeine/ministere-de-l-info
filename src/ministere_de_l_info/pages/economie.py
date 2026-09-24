"""Page Économie — module render() (Phase E4 + E+).

Répond aux questions éditoriales de l'ADR-0006 :
1. Les communes les plus pauvres votent-elles RN ?
2. La désindustrialisation prédit-elle le vote EXD ?
3. La part d'ouvriers/employés détermine-t-elle la couleur politique ?
4. Les communes pauvres s'abstiennent-elles ou votent-elles contestataire ?
"""

from __future__ import annotations

import json
import logging

import folium
import plotly.express as px
import polars as pl
import streamlit as st
from streamlit_folium import st_folium

from ministere_de_l_info._blocs_politiques import BLOCS_ORDERED as _BLOCS_ORDERED
from ministere_de_l_info._blocs_politiques import COULEURS_BLOCS as _COULEURS_BLOCS
from ministere_de_l_info._blocs_politiques import LIBELLES_BLOCS as _LIBELLES_BLOCS
from ministere_de_l_info._theme import (
    conserver_selections,
    render_donnees_indisponibles,
    render_page_header,
)
from ministere_de_l_info.viz.economie_queries import (
    annees_croisement_exploitables,
    get_annees_par_indicateur,
    get_annees_presidentielles,
    get_communes_industrie_hdf,
    get_contexte_hdf_vs_france,
    get_croisement_eco_elections,
    get_desindustrialisation_commune,
    get_economie_commune,
    get_evolution_hdf,
    get_evolution_rsa_hdf,
    get_indicateurs,
    get_scores_commune,
    is_base_disponible,
    is_contexte_loaded,
    is_data_loaded,
)

logger = logging.getLogger(__name__)

# Agrégats HdF : le libellé dit comment la valeur est calculée (audit I4).
_INDIC_EVOL: dict[str, str] = {
    "taux_pauvrete_moyen": "Taux de pauvreté — moyenne des communes, non pondérée (%)",
    "niveau_vie_median_communes": "Niveau de vie — médiane des médianes communales (€)",
    "tx_chomage_pondere": "Taux de chômage (RP) — pondéré par les actifs (%)",
}

# Libellés lisibles des colonnes du détail commune (au lieu des noms techniques).
_LIBELLES_COLONNES_ECO: dict[str, str] = {
    "annee": "Année",
    "taux_pauvrete": "Taux de pauvreté (%)",
    "niveau_vie_median": "Niveau de vie médian (€)",
    "tx_chomage_dec": "Taux de chômage RP (%)",
    "part_ouvriers_employes": "Part ouvriers + employés (%)",
    "part_emploi_industriel": "Part emploi industriel (%)",
    "part_logements_sociaux": "Part logements sociaux (%)",
}

# Libellé d'onglet → préfixes des clés de ses widgets (conservation des sélections)
_PREFIXES_ONGLETS: dict[str, tuple[str, ...]] = {
    "Carte des indicateurs": ("eco_indicateur", "eco_annee", "eco_drilldown"),
    "Évolution HdF": ("eco_evol_", "eco_ctx_"),
    "Économie × Élections": ("eco_crois_",),
    "Désindustrialisation": ("industrie_",),
}
_ONGLETS: list[str] = list(_PREFIXES_ONGLETS)

_FILOSOFI_INDICS = {"taux_pauvrete", "niveau_vie_median"}

_INDICATEURS_CROISEMENT: dict[str, str] = {
    "taux_pauvrete": "Taux de pauvreté (%)",
    "niveau_vie_median": "Niveau de vie médian (€)",
    "tx_chomage_dec": "Taux de chômage (RP, %)",
    "part_ouvriers_employes": "Part ouvriers + employés (%)",
    "part_emploi_industriel": "Part emploi industriel (%)",
    "part_logements_sociaux": "Part logements sociaux (%)",
}


def _make_desert_map(df: pl.DataFrame) -> folium.Map:
    """Carte déserts médicaux — rouge si APL < 2,5, gris sinon (choroplèthe binaire)."""
    return _make_choropleth(
        df.with_columns(
            pl.when(pl.col("valeur").is_not_null() & (pl.col("valeur") < 2.5))
            .then(pl.lit(1.0))
            .otherwise(pl.lit(None, dtype=pl.Float64))
            .alias("valeur"),
            pl.lit(False).alias("secret"),
        ),
        "Désert médical (APL < 2,5)",
    )


def _make_choropleth(df: pl.DataFrame, libelle: str) -> folium.Map:
    """Construit une carte choroplèthe Folium pour un indicateur économique.

    Les communes sans données (secret INSEE ou valeur manquante) sont affichées en gris.
    """
    m = folium.Map(location=[50.3, 2.9], zoom_start=8)

    features = []
    for row in df.iter_rows(named=True):
        if not row["geojson"]:
            continue
        try:
            geom = json.loads(row["geojson"])
        except (json.JSONDecodeError, TypeError):
            continue
        val = row["valeur"]
        is_secret = row["secret"]
        val_str = "n.d." if val is None or is_secret else f"{val:.1f}"
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "code_commune": row["code_commune"],
                    "nom": row["nom_commune"],
                    "valeur_str": val_str,
                },
                "geometry": geom,
            }
        )

    if not features:
        return m

    geo_json = {"type": "FeatureCollection", "features": features}

    # NULL pour les communes avec secret statistique → nan_fill_color gris
    data_pd = (
        df.with_columns(
            pl.when(pl.col("secret")).then(None).otherwise(pl.col("valeur")).alias("valeur_plot")
        )
        .select(["code_commune", "valeur_plot"])
        .to_pandas()
    )

    choropleth = folium.Choropleth(
        geo_data=geo_json,
        data=data_pd,
        columns=["code_commune", "valeur_plot"],
        key_on="feature.properties.code_commune",
        fill_color="YlOrRd",
        nan_fill_color="#CCCCCC",
        fill_opacity=0.75,
        line_opacity=0.2,
        legend_name=libelle,
    )
    choropleth.add_to(m)
    choropleth.geojson.add_child(
        folium.features.GeoJsonTooltip(
            fields=["nom", "valeur_str"],
            aliases=["Commune", libelle],
            localize=True,
        )
    )
    return m


def _render_carte_tab() -> None:
    """Onglet Carte des indicateurs — choroplèthe + drill-down commune."""
    indicateurs = get_indicateurs()
    annees_par_indic = get_annees_par_indicateur()

    c1, c2 = st.columns([2, 1])
    with c1:
        indicateur: str = st.selectbox(  # type: ignore[assignment]
            "Indicateur",
            list(indicateurs.keys()),
            format_func=lambda k: indicateurs[k],
            key="eco_indicateur",
        )
    with c2:
        annees = sorted(annees_par_indic.get(indicateur, []), reverse=True)
        if not annees:
            st.warning("Pas de données disponibles pour cet indicateur.")
            return
        annee: int = st.selectbox("Année", annees, key="eco_annee")  # type: ignore[assignment]

    libelle = indicateurs[indicateur]
    df = get_scores_commune(annee, indicateur)

    if df.is_empty():
        st.warning(f"Aucune donnée pour {libelle} — {annee}.")
        return

    n_valides = df.filter(pl.col("valeur").is_not_null() & ~pl.col("secret")).height
    n_secret = df.filter(pl.col("secret")).height
    if indicateur in _FILOSOFI_INDICS:
        source = "INSEE Filosofi"
    elif indicateur == "nb_foyers_rsa":
        source = "CNAF data.caf.fr"
    elif indicateur == "apl_medecins":
        source = "DREES data.solidarites-sante.gouv.fr"
    else:
        source = "INSEE Recensement de la Population"
    secret_info = (
        f" · {n_secret:,} sous secret statistique INSEE (gris)".replace(",", " ")
        if n_secret
        else ""
    )
    st.caption(
        f"{n_valides:,}".replace(",", " ")
        + f" communes avec données{secret_info} — Source : {source}, millésime {annee}"
    )
    if indicateur == "nb_foyers_rsa":
        st.info(
            "Cette carte montre le **nombre** de foyers allocataires du RSA, et non un taux : "
            "les communes les plus peuplées ressortent mécaniquement. "
            "Aucun dénominateur fiable (nombre de ménages de la même année) n'est "
            "disponible en base pour calculer un taux.",
            icon=":material/info:",
        )

    try:
        carte = _make_choropleth(df, libelle)
        st_folium(carte, use_container_width=True, height=540, returned_objects=[])
    except Exception as exc:
        st.error(f"Erreur carte : {exc}")
        logger.exception("Erreur choroplèthe économie")

    if indicateur == "apl_medecins":
        n_desert = df.filter(pl.col("valeur").is_not_null() & (pl.col("valeur") < 2.5)).height
        st.metric("Communes en désert médical (APL < 2,5)", n_desert)

    # ── Drill-down commune ─────────────────────────────────────────────────────
    with st.expander("Détail d'une commune"):
        communes = [
            (row["code_commune"], row["nom_commune"])
            for row in df.filter(pl.col("valeur").is_not_null()).iter_rows(named=True)
        ]
        options = ["(aucune sélection)"] + [f"{nom} ({code})" for code, nom in communes]
        sel: str = st.selectbox("Commune", options, key="eco_drilldown")  # type: ignore[assignment]

        if sel != "(aucune sélection)":
            code_sel = sel.rsplit("(", 1)[1].rstrip(")")
            nom_sel = sel.rsplit(" (", 1)[0]
            eco_df = get_economie_commune(code_sel)

            if eco_df.is_empty():
                st.warning(f"Aucune donnée pour {nom_sel}.")
                return

            st.subheader(nom_sel)
            eco_affiche = eco_df.drop("secret").rename(_LIBELLES_COLONNES_ECO)
            st.dataframe(
                eco_affiche,
                width="stretch",
                hide_index=True,
                placeholder="n.d.",
                column_config={
                    "Année": st.column_config.NumberColumn("Année", format="%d"),
                    **{
                        col: st.column_config.NumberColumn(col, format="localized")
                        for col in eco_affiche.columns
                        if col != "Année"
                    },
                },
            )
            st.caption(
                "Sources : INSEE Filosofi (pauvreté, niveau de vie) et Recensement de la "
                "Population (chômage, CSP, emploi, logements). « n.d. » : donnée non "
                "disponible ou sous secret statistique."
            )

            indic_cols = [
                "taux_pauvrete",
                "tx_chomage_dec",
                "part_ouvriers_employes",
                "part_logements_sociaux",
            ]
            indic_cols = [c for c in indic_cols if c in eco_df.columns]
            eco_long = (
                eco_df.select(["annee"] + indic_cols)
                .unpivot(index="annee", variable_name="indicateur", value_name="valeur")
                .filter(pl.col("valeur").is_not_null())
                .with_columns(pl.col("indicateur").replace(_LIBELLES_COLONNES_ECO))
            )
            if not eco_long.is_empty():
                fig = px.line(
                    eco_long.to_pandas(),
                    x="annee",
                    y="valeur",
                    color="indicateur",
                    markers=True,
                    title=f"Évolution — {nom_sel}",
                    labels={"annee": "Année", "valeur": "Valeur (%)", "indicateur": "Indicateur"},
                )
                fig.update_layout(height=340, margin={"t": 40, "b": 20})
                st.plotly_chart(fig, width="stretch")


def _render_contexte_section() -> None:
    """Contexte macro HdF vs France — données Eurostat."""
    if not is_contexte_loaded():
        st.info(
            "Données contexte non chargées. "
            "Lancer : `uv run python scripts/load_economie.py --source eurostat`"
        )
        return

    indic_ctx: str = st.selectbox(  # type: ignore[assignment]
        "Indicateur",
        ["tx_chomage_bit", "pib_eur_hab"],
        format_func=lambda k: {
            "tx_chomage_bit": "Taux de chômage BIT (%)",
            "pib_eur_hab": "PIB par habitant (€)",
        }[k],
        key="eco_ctx_indic",
    )
    df_ctx = get_contexte_hdf_vs_france(indic_ctx)
    if df_ctx.is_empty():
        st.warning("Aucune donnée disponible.")
        return

    df_long = (
        df_ctx.select(
            [
                pl.col("annee"),
                pl.col("valeur_hdf").alias("Hauts-de-France"),
                pl.col("valeur_france").alias("France"),
            ]
        )
        .unpivot(index="annee", variable_name="territoire", value_name="valeur")
        .drop_nulls("valeur")
    )

    libelle = {
        "tx_chomage_bit": "Taux de chômage BIT (%)",
        "pib_eur_hab": "PIB par habitant (€)",
    }[indic_ctx]

    fig = px.line(
        df_long.to_pandas(),
        x="annee",
        y="valeur",
        color="territoire",
        color_discrete_map={
            "Hauts-de-France": "#E63946",
            "France": "#457B9D",
        },
        markers=True,
        title=f"{libelle} — Hauts-de-France vs France (2000-2025)",
        labels={"annee": "Année", "valeur": libelle, "territoire": "Territoire"},
    )
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig, width="stretch")

    last = df_ctx.filter(pl.col("ecart_hdf_france").is_not_null()).sort("annee").tail(1)
    if not last.is_empty():
        ecart = last["ecart_hdf_france"][0]
        annee_last = last["annee"][0]
        label_ecart = "pts de %" if indic_ctx == "tx_chomage_bit" else "€"
        delta_color = "inverse" if indic_ctx == "pib_eur_hab" else "normal"
        st.metric(
            f"Écart HdF - France ({annee_last})",
            f"{ecart:+.1f} {label_ecart}",
            delta_color=delta_color,
        )

    st.caption("Source : Eurostat — lfst_r_lfu3rt / nama_10r_2gdp")


def _render_evolution_tab() -> None:
    """Onglet Évolution HdF — Filosofi/RP 2017-2021, RSA CNAF 2020-2024 ou Eurostat."""
    mode: str = st.radio(  # type: ignore[assignment]
        "Données à afficher",
        [
            "Revenus & emploi (INSEE 2017-2021)",
            "Allocataires RSA (CNAF 2020-2024)",
            "Contexte HdF vs France (Eurostat)",
        ],
        horizontal=True,
        key="eco_evol_mode",
    )

    if mode.startswith("Contexte"):
        _render_contexte_section()
        return

    if mode.startswith("Allocataires"):
        rsa_df = get_evolution_rsa_hdf()
        if rsa_df.is_empty():
            st.info("Données RSA non chargées. Lancez : `load_economie.py --source cnaf`")
            return
        fig = px.line(
            rsa_df.to_pandas(),
            x="annee",
            y="total_foyers_rsa_hdf",
            markers=True,
            title="Évolution allocataires RSA — Hauts-de-France",
            labels={"annee": "Année", "total_foyers_rsa_hdf": "Foyers RSA"},
        )
        fig.update_layout(height=420, margin={"t": 50, "b": 30})
        st.plotly_chart(fig, width="stretch")
        st.caption("Source : CNAF data.caf.fr — snapshot décembre")
        return

    evol_df = get_evolution_hdf()
    if evol_df.is_empty():
        st.warning("Aucune donnée d'évolution disponible.")
        return

    indic_evol: str = st.selectbox(  # type: ignore[assignment]
        "Indicateur",
        list(_INDIC_EVOL.keys()),
        format_func=lambda k: _INDIC_EVOL[k],
        key="eco_evol_indic",
    )
    libelle = _INDIC_EVOL[indic_evol]
    serie = evol_df.select(["annee", indic_evol]).drop_nulls(indic_evol)
    if serie.is_empty():
        st.info("Données non disponibles pour cet indicateur.")
        return
    annees = serie["annee"].to_list()
    fig = px.line(
        serie.to_pandas(),
        x="annee",
        y=indic_evol,
        markers=True,
        title=f"{libelle} — Hauts-de-France {min(annees)}-{max(annees)}",
        labels={"annee": "Année", indic_evol: libelle},
    )
    fig.update_layout(
        xaxis={"tickmode": "array", "tickvals": annees},
        height=420,
        margin={"t": 50, "b": 30},
        separators=", ",
    )
    fig.update_traces(hovertemplate="<b>%{x}</b><br>%{y:.1f}<extra></extra>")
    st.plotly_chart(fig, width="stretch")
    if indic_evol == "tx_chomage_pondere":
        methode = (
            "taux communaux pondérés par le nombre d'actifs de 15-64 ans "
            "(≈ total des chômeurs / total des actifs HdF)."
        )
    elif indic_evol == "taux_pauvrete_moyen":
        methode = (
            "moyenne simple des taux communaux (une petite commune pèse autant que Lille) ; "
            "communes sous secret statistique exclues. Ce n'est pas le taux régional officiel."
        )
    else:
        methode = (
            "médiane des niveaux de vie médians communaux ; communes sous secret statistique "
            "exclues. Ce n'est pas le niveau de vie médian régional officiel."
        )
    st.caption(
        "Source : INSEE Filosofi (taux de pauvreté, niveau de vie médian) "
        "+ Recensement de la Population (chômage déclaratif) — "
        f"Agrégation : {methode}"
    )


def _render_croisement_tab() -> None:
    """Onglet Économie × Élections — scatter plot corrélation territoriale."""
    st.markdown(
        "**Questions éditoriales** : Les communes les plus pauvres votent-elles RN ? "
        "La désindustrialisation prédit-elle le vote EXD ? "
        "La part d'ouvriers/employés détermine-t-elle la couleur politique ?"
    )

    indicateurs = _INDICATEURS_CROISEMENT
    annees_par_indic = get_annees_par_indicateur()
    annees_pres = get_annees_presidentielles()

    c1, c2, c3, c4 = st.columns([2, 1, 1, 2])
    with c1:
        indic_x: str = st.selectbox(  # type: ignore[assignment]
            "Indicateur éco (axe X)",
            list(indicateurs.keys()),
            format_func=lambda k: indicateurs[k],
            key="eco_crois_indic",
        )
    # Seules les présidentielles dont l'année n-1 est couverte par l'indicateur
    # sont proposées (audit I5 : 4 années sur 5 donnaient un écran vide).
    annees_ok = annees_croisement_exploitables(annees_pres, annees_par_indic.get(indic_x, []))
    if not annees_ok:
        st.info(
            f"Aucune présidentielle ne peut être croisée avec « {indicateurs[indic_x]} » : "
            "les données économiques de l'année précédant le scrutin ne sont pas disponibles."
        )
        return
    with c2:
        annee_election: int = st.selectbox(  # type: ignore[assignment]
            "Présidentielle",
            annees_ok,
            index=len(annees_ok) - 1,
            key="eco_crois_annee",
            help=(
                "Seules les élections dont l'année précédente est couverte par l'indicateur "
                "sont proposées (données économiques de l'année n-1)."
            ),
        )
    with c3:
        tour: int = st.radio(  # type: ignore[assignment]
            "Tour",
            [1, 2],
            format_func=lambda t: "1er" if t == 1 else "2e",
            horizontal=True,
            key="eco_crois_tour",
            help="Au 2e tour, seuls les blocs des deux finalistes ont des voix.",
        )
    with c4:
        bloc_viz: str = st.selectbox(  # type: ignore[assignment]
            "Bloc (axe Y — % des exprimés)",
            _BLOCS_ORDERED,
            index=5,
            format_func=lambda b: f"{b} — {_LIBELLES_BLOCS[b]}",
            key="eco_crois_bloc",
        )

    tour_lbl = "1er tour" if tour == 1 else "2e tour"
    crois_df = get_croisement_eco_elections(annee_election, bloc=bloc_viz, tour=tour)

    if crois_df.is_empty():
        st.info(
            f"Aucun résultat pour le bloc {_LIBELLES_BLOCS[bloc_viz]} au {tour_lbl} "
            f"de la présidentielle {annee_election}"
            + (" : ce bloc n'était pas présent au second tour." if tour == 2 else ".")
        )
        return

    scatter_df = crois_df.filter(pl.col(indic_x).is_not_null() & pl.col("pct_voix").is_not_null())

    if scatter_df.is_empty():
        st.info(f"Pas de communes avec données pour {indicateurs[indic_x]} × {bloc_viz}.")
        return

    n_communes = scatter_df.height
    libelle_x = indicateurs[indic_x]

    # Taille des bulles = actifs de 15-64 ans (RP). Communes sans effectif connu :
    # taille médiane, signalée en légende (plus de valeur arbitraire cachée).
    n_sans_pop = scatter_df.filter(pl.col("pop_active").is_null()).height
    pop_mediane = scatter_df["pop_active"].median()
    taille_defaut = int(pop_mediane) if pop_mediane is not None else 1
    scatter_pd = scatter_df.with_columns(
        pl.col("pop_active").fill_null(taille_defaut).alias("taille_bulle")
    ).to_pandas()

    fig = px.scatter(
        scatter_pd,
        x=indic_x,
        y="pct_voix",
        size="taille_bulle",
        size_max=20,
        hover_name="nom_commune",
        hover_data={indic_x: ":.1f", "pct_voix": ":.1f", "pop_active": ":,", "taille_bulle": False},
        title=(
            f"% des exprimés {bloc_viz} ({_LIBELLES_BLOCS[bloc_viz]}) "
            f"× {libelle_x} — Présidentielle {annee_election}, {tour_lbl} (HdF)"
        ),
        labels={
            indic_x: libelle_x,
            "pct_voix": f"% des exprimés {bloc_viz} ({tour_lbl})",
            "pop_active": "Actifs 15-64 ans",
        },
        color_discrete_sequence=[_COULEURS_BLOCS[bloc_viz]],
    )
    fig.update_layout(height=500, margin={"t": 60, "b": 40}, separators=", ")
    st.plotly_chart(fig, width="stretch")
    note_taille = (
        f" {n_sans_pop} commune(s) sans effectif d'actifs connu : bulle de taille médiane."
        if n_sans_pop
        else ""
    )
    st.caption(
        f"{n_communes:,}".replace(",", " ") + " communes — "
        f"Données économiques : année {annee_election - 1} "
        "(source INSEE Filosofi / Recensement de la Population) — "
        "Résultats électoraux : Ministère de l'Intérieur via data.gouv.fr. "
        f"Taille des bulles : actifs de 15-64 ans (RP).{note_taille} "
        "**Corrélation ne signifie pas causalité.**"
    )


def _render_industrie_tab() -> None:
    """Onglet Désindustrialisation — emploi GS1 Industrie + déserts médicaux."""
    st.subheader("Emploi industriel (GS1) — Hauts-de-France 2006-2025")
    hdf_df = get_desindustrialisation_commune()
    if hdf_df.is_empty():
        st.info("Données URSSAF non chargées. Lancez : `load_economie.py --source urssaf`")
    else:
        annees_ind = hdf_df["annee"].to_list()
        fig = px.line(
            hdf_df.to_pandas(),
            x="annee",
            y="nb_salaries",
            markers=True,
            title=f"Effectifs salariés secteur Industrie — HdF {min(annees_ind)}-{max(annees_ind)}",
            labels={"annee": "Année", "nb_salaries": "Salariés industrie"},
        )
        fig.add_vrect(
            x0=2008,
            x1=2010,
            fillcolor="grey",
            opacity=0.15,
            line_width=0,
            annotation_text="Crise financière 2008-2010",
            annotation_position="top left",
        )
        fig.add_vrect(
            x0=2020,
            x1=2021,
            fillcolor="#4488ff",
            opacity=0.12,
            line_width=0,
            annotation_text="Crise sanitaire 2020-2021",
            annotation_position="top left",
        )
        fig.update_layout(height=400, margin={"t": 50, "b": 30})
        st.plotly_chart(fig, width="stretch")
        st.caption("Source : URSSAF / ACOSS — open.urssaf.fr")

    st.subheader("Détail d'une commune")
    communes_ind = get_communes_industrie_hdf()
    if not communes_ind:
        st.info("Données URSSAF non chargées.")
    else:
        opts = ["(aucune sélection)"] + [f"{nom} ({code})" for code, nom in communes_ind]
        sel: str = st.selectbox("Commune", opts, key="industrie_commune")  # type: ignore[assignment]
        if sel != "(aucune sélection)":
            code_ind = sel.rsplit("(", 1)[1].rstrip(")")
            nom_ind = sel.rsplit(" (", 1)[0]
            ts_df = get_desindustrialisation_commune(code_ind)
            if ts_df.is_empty():
                st.info(f"Pas de données industrie pour {nom_ind}.")
            else:
                fig2 = px.line(
                    ts_df.to_pandas(),
                    x="annee",
                    y="nb_salaries",
                    markers=True,
                    title=f"Emploi industriel — {nom_ind}",
                    labels={"annee": "Année", "nb_salaries": "Salariés"},
                )
                fig2.update_layout(height=340, margin={"t": 40, "b": 20})
                st.plotly_chart(fig2, width="stretch")

    annees_apl = get_annees_par_indicateur().get("apl_medecins", [])
    millesime_apl = f" — Millésime {max(annees_apl)}" if annees_apl else ""
    st.subheader(f"Déserts médicaux HdF (APL < 2,5){millesime_apl}")
    if not annees_apl:
        st.info("Données DREES APL non chargées. Lancez : `load_economie.py --source drees`")
    else:
        apl_df = get_scores_commune(max(annees_apl), "apl_medecins")
        if not apl_df.is_empty():
            n_total = apl_df.filter(pl.col("valeur").is_not_null()).height
            n_desert = apl_df.filter(
                pl.col("valeur").is_not_null() & (pl.col("valeur") < 2.5)
            ).height
            st.metric("Communes désert médical / avec données APL", f"{n_desert} / {n_total}")
            try:
                st_folium(
                    _make_desert_map(apl_df),
                    use_container_width=True,
                    height=500,
                    returned_objects=[],
                )
            except Exception as exc:
                st.error(f"Erreur carte déserts médicaux : {exc}")
                logger.exception("Erreur carte déserts médicaux")
            st.caption(
                "Rouge : APL < 2,5 consult./hab./an (seuil officiel DREES). "
                "Source : DREES data.solidarites-sante.gouv.fr"
            )


def render() -> None:
    """Point d'entrée de la page Économie — ministere-de-l-info."""
    render_page_header(icon="bar_chart", title="Économie", subtitle="Hauts-de-France")

    if not is_base_disponible() or not is_data_loaded():
        render_donnees_indisponibles(
            "économiques",
            base_absente=not is_base_disponible(),
            commande_dev="uv run python scripts/load_economie.py",
        )
        return

    # Onglets paresseux (Streamlit ≥ 1.57) : seul l'onglet ouvert est calculé,
    # au lieu de reconstruire les 2 cartes de ~3 800 communes à chaque interaction.
    # Les sélections des onglets fermés sont conservées (sinon remises à zéro).
    conserver_selections("eco_onglet", _PREFIXES_ONGLETS)
    tab_carte, tab_evolution, tab_croisement, tab_industrie = st.tabs(
        _ONGLETS, key="eco_onglet", on_change="rerun"
    )

    with tab_carte:
        if tab_carte.open:
            _render_carte_tab()
    with tab_evolution:
        if tab_evolution.open:
            _render_evolution_tab()
    with tab_croisement:
        if tab_croisement.open:
            _render_croisement_tab()
    with tab_industrie:
        if tab_industrie.open:
            _render_industrie_tab()
