"""Page Géographie — carte choroplèthe multi-niveaux."""

from __future__ import annotations

import duckdb
import streamlit as st
from streamlit_folium import st_folium

from ministere_de_l_info._theme import render_donnees_indisponibles, render_page_header
from ministere_de_l_info.config import get_settings
from ministere_de_l_info.viz._queries import get_tableau_territoires
from ministere_de_l_info.viz.maps import make_choropleth

render_page_header(
    icon="map",
    title="Géographie territoriale",
    subtitle="Cartographie choroplèthe multi-niveaux et démographie INSEE.",
)

_DB_PATH = get_settings().db_path

_NIVEAU_LABELS: dict[str, str] = {
    "region": "Régions (18)",
    "departement": "Départements (101)",
    "epci": "Intercommunalités EPCI (~1 265)",
    "arrondissement_municipal": "Arrondissements municipaux (45)",
    "circonscription": "Circonscriptions législatives (559)",
    "commune": "Communes (~35 000) ⚠️",
}

_TABLE_META: dict[str, str] = {
    "region": "geographies_regions",
    "departement": "geographies_departements",
    "epci": "geographies_epci",
    "arrondissement_municipal": "geographies_arrondissements_municipaux",
    "circonscription": "geographies_circonscriptions",
    "commune": "geographies_communes",
}

# Vues population disponibles et clé de jointure
_VUE_POP: dict[str, tuple[str, str]] = {
    "region": ("v_population_region", "code_region"),
    "departement": ("v_population_departement", "code_departement"),
    "epci": ("v_population_epci", "code_epci"),
    "commune": ("v_population_commune", "code_commune"),
}

_FILTRE_DEPT_COL: dict[str, str] = {
    "epci": "code_departement_principal",
    "circonscription": "code_departement",
    "commune": "code_departement",
}

_FILTRE_REGION_COL: dict[str, str] = {
    "departement": "code_region",
    "commune": "code_region",
}


@st.cache_resource
def _get_con() -> duckdb.DuckDBPyConnection:
    """Connexion DuckDB partagée en lecture seule."""
    con = duckdb.connect(str(_DB_PATH), read_only=True)
    con.execute("LOAD spatial;")
    return con


if not _DB_PATH.exists():
    render_donnees_indisponibles(
        "géographiques",
        base_absente=True,
        commande_dev=(
            "./scripts/download_db.sh\n"
            "# ou, pour reconstruire les référentiels territoriaux :\n"
            "uv run python scripts/etl_territoires.py"
        ),
    )
    st.stop()

con = _get_con()

# ── Sidebar : paramètres ──────────────────────────────────────────────────────

with st.sidebar:
    st.header("Paramètres")

    niveau = st.selectbox(
        "Niveau territorial",
        options=list(_NIVEAU_LABELS),
        format_func=lambda x: _NIVEAU_LABELS[x],
    )

    annees_dispo = [
        r[0]
        for r in con.execute(
            "SELECT DISTINCT annee FROM populations ORDER BY annee DESC"
        ).fetchall()
    ]
    if not annees_dispo:
        st.warning("Aucune donnée population — carte en mode contours.")
        annee = 2023
    else:
        annee = st.selectbox(
            "Année de recensement (INSEE)",
            annees_dispo,
            help="Population municipale (PMUN) issue de DS_POPULATIONS_HISTORIQUES",
        )
        st.caption(
            f"📊 {len(annees_dispo)} millésime(s) disponible(s) : "
            f"{', '.join(str(a) for a in sorted(annees_dispo))}"
        )

    # Comparaison inter-millésimes (contextuelle)
    annee_ref: int | None = None
    indicateur_carte = "Population absolue"
    if len(annees_dispo) > 1 and niveau in _VUE_POP:
        annees_compare = sorted(a for a in annees_dispo if a != annee)
        annee_ref = st.selectbox(
            "Comparer avec",
            [None, *annees_compare],
            format_func=lambda x: "Aucune comparaison" if x is None else str(x),
            help="Affiche l'évolution démographique par rapport à l'année choisie",
        )
        if annee_ref is not None:
            indicateur_carte = st.radio(
                "Indicateur cartographique",
                ["Population absolue", "Évolution démographique"],
                horizontal=True,
            )

    # Filtre département (contextuel)
    filtre_departement: str | None = None
    if niveau in _FILTRE_DEPT_COL:
        depts = con.execute(
            "SELECT code_insee, nom FROM geographies_departements ORDER BY code_insee"
        ).fetchall()
        dept_labels = {d[0]: f"{d[0]} — {d[1]}" for d in depts}

        if niveau == "commune":
            st.warning("⚠️ Un département doit être sélectionné pour les communes.")
            filtre_departement = st.selectbox(
                "Département",
                options=[d[0] for d in depts],
                format_func=lambda x: dept_labels.get(x, x),
            )
        else:
            choix = st.selectbox(
                "Département (optionnel)",
                options=[None] + [d[0] for d in depts],
                format_func=lambda x: "Tous" if x is None else dept_labels.get(x, x),
            )
            filtre_departement = choix

    # Filtre région (contextuel)
    filtre_region: str | None = None
    if niveau in _FILTRE_REGION_COL:
        regions = con.execute(
            "SELECT code_insee, nom FROM geographies_regions ORDER BY nom"
        ).fetchall()
        region_labels = {r[0]: r[1] for r in regions}
        choix = st.selectbox(
            "Région (optionnelle)",
            options=[None] + [r[0] for r in regions],
            format_func=lambda x: "Toutes" if x is None else region_labels.get(x, x),
        )
        filtre_region = choix

    with st.expander("Options avancées"):
        mode = st.radio("Mode de rendu", ["auto", "choropleth", "contours"], index=0)

# ── Carte ────────────────────────────────────────────────────────────────────

_a_population = niveau in _VUE_POP and mode != "contours"
_mode_evolution = indicateur_carte == "Évolution démographique" and annee_ref is not None

if _mode_evolution:
    titre_carte = f"Évolution démographique {annee_ref} → {annee}"
elif _a_population:
    titre_carte = f"Population municipale {annee}"
else:
    titre_carte = "Contours territoriaux"

try:
    carte = make_choropleth(
        con,
        niveau=niveau,
        annee=annee,
        annee_ref=annee_ref if _mode_evolution else None,
        filtre_departement=filtre_departement,
        filtre_region=filtre_region,
        titre=titre_carte,
        mode=mode,
    )
    st_folium(carte, width="100%", height=600, returned_objects=[])
except ValueError as e:
    st.error(f"Paramètres invalides : {e}")
    st.stop()
except RuntimeError as e:
    st.warning(str(e))
    st.stop()
except Exception as e:
    st.error(f"Erreur inattendue : {e}")
    raise

# ── Métadonnée ───────────────────────────────────────────────────────────────

meta = con.execute(
    "SELECT loaded_at, source_version, row_count FROM _etl_metadata WHERE table_name = ?",
    [_TABLE_META[niveau]],
).fetchone()

if meta:
    loaded_at, source, row_count = meta
    if _mode_evolution:
        pop_info = f"Évolution {annee_ref}→{annee} (INSEE) · "
    elif _a_population:
        pop_info = f"Population municipale {annee} (INSEE) · "
    else:
        pop_info = ""
    st.caption(f"📊 {row_count:,} entités · {pop_info}Géométries : data.geopf.fr")
else:
    st.caption("⚠️ Aucune métadonnée ETL pour ce niveau.")

# ── Tableau de données ────────────────────────────────────────────────────────

st.divider()

tableau = get_tableau_territoires(
    con,
    niveau,
    annee,
    annee_ref=annee_ref if niveau in _VUE_POP else None,
    filtre_departement=filtre_departement,
    filtre_region=filtre_region,
)

col_pop = f"Population municipale {annee}"
col_evol_abs = f"Évolution {annee_ref}→{annee} (hab.)"
col_evol_pct = f"Évolution {annee_ref}→{annee} (%)"
column_config: dict[str, object] = {}

if niveau in _VUE_POP:
    renommage = {"code": "Code", "nom": "Nom", "population": col_pop}
    column_config[col_pop] = st.column_config.NumberColumn(col_pop, format="localized")
    if annee_ref is not None:
        renommage |= {"delta_abs": col_evol_abs, "delta_pct": col_evol_pct}
        column_config[col_evol_abs] = st.column_config.NumberColumn(
            col_evol_abs, format="localized"
        )
        column_config[col_evol_pct] = st.column_config.NumberColumn(col_evol_pct, format="%+.1f %%")
    df = tableau.rename(renommage)
else:
    extra_label = "Commune mère" if niveau == "arrondissement_municipal" else "Département"
    df = tableau.rename({"code": "Code", "nom": "Nom", "extra": extra_label})

st.caption(
    f"{df.height:,} entité(s) affichée(s)".replace(",", " ")
    + (" — triées par population décroissante" if niveau in _VUE_POP else "")
    + ". Cliquez sur un en-tête de colonne pour trier ; « n.d. » = donnée non disponible."
)
st.dataframe(
    df,
    width="stretch",
    hide_index=True,
    column_config=column_config,
    placeholder="n.d.",
)
st.download_button(
    "Télécharger le tableau en CSV",
    data=df.write_csv().encode("utf-8"),
    file_name=f"geographie_{niveau}_{annee}.csv",
    mime="text/csv",
    key="geo_download_csv",
)
