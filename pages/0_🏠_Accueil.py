"""Page d'accueil — ministere-de-l-info."""

from __future__ import annotations

from datetime import datetime

import duckdb
import polars as pl
import streamlit as st

from ministere_de_l_info._theme import render_page_header
from ministere_de_l_info.config import get_settings
from ministere_de_l_info.sources import tableau_sources


@st.cache_data(ttl=3600)
def _dates_chargement() -> dict[str, datetime]:
    """Date de chargement par table (_etl_metadata) ; vide si la base est absente."""
    try:
        with duckdb.connect(str(get_settings().db_path), read_only=True) as con:
            return dict(con.execute("SELECT table_name, loaded_at FROM _etl_metadata").fetchall())
    except duckdb.Error:
        return {}


render_page_header(
    icon="flag",
    title="ministère de l'info",
    subtitle="Exploration des données politiques, électorales et territoriales françaises.",
)

st.markdown("### Modules d'analyse")

_MODULES: list[dict[str, str]] = [
    {
        "page": "pages/1_📍_Géographie.py",
        "icon": "map",
        "label": "Géographie territoriale",
        "perimetre": "France entière — recensements 2013, 2018 et 2023",
        "description": "Cartographie choroplèthe multi-niveaux (régions, départements, EPCI, communes) et démographie INSEE.",
    },
    {
        "page": "pages/2_🗳️_Élections.py",
        "icon": "how_to_vote",
        "label": "Élections",
        "perimetre": "Hauts-de-France uniquement — scrutins 2002-2026",
        "description": "Présidentielles, législatives et municipales 2002-2026, drill-down jusqu'au bureau de vote.",
    },
    {
        "page": "pages/3_🏛️_Législatif.py",
        "icon": "account_balance",
        "label": "Législatif",
        "perimetre": "France entière (filtre Hauts-de-France disponible) — depuis 2002",
        "description": "Composition politique et activité parlementaire de l'Assemblée nationale et du Sénat.",
    },
    {
        "page": "pages/4_📊_Économie.py",
        "icon": "bar_chart",
        "label": "Économie",
        "perimetre": "Hauts-de-France uniquement — 2006-2025 selon les sources",
        "description": "Indicateurs socio-économiques (pauvreté, chômage, emploi industriel) croisés avec les résultats électoraux.",
    },
]

row1 = st.columns(2)
row2 = st.columns(2)
for module, col in zip(_MODULES, [*row1, *row2], strict=True):
    with col, st.container(border=True):
        st.page_link(module["page"], label=module["label"], icon=f":material/{module['icon']}:")
        st.caption(module["description"])
        st.markdown(f"**Périmètre** : {module['perimetre']}")

st.markdown("### Sources, licences et dates")
st.caption(
    "Chaque jeu de données est réutilisé selon sa licence. « Chargées le » : date du dernier "
    "chargement dans l'outil. La base distribuée avec l'outil est placée sous licence ODbL "
    "(partage à l'identique), imposée par les données URSSAF."
)
_lignes_sources = tableau_sources(_dates_chargement())
st.dataframe(
    _lignes_sources,
    hide_index=True,
    width="stretch",
    height=36 * (len(_lignes_sources) + 1) + 3,
    column_config={
        "Lien": st.column_config.LinkColumn(width="small", display_text="ouvrir"),
    },
)

st.divider()

with st.expander("Diagnostic technique"):
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Streamlit", st.__version__)
    with col2:
        st.metric("DuckDB", duckdb.__version__)
    with col3:
        st.metric("Polars", pl.__version__)
    st.success("Stack opérationnelle.")
    result = duckdb.sql("SELECT 'France' AS pays, 67_000_000 AS habitants").to_df()
    st.dataframe(result, width="stretch")
