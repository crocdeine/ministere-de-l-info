"""Page d'accueil — ministere-de-l-info."""

from __future__ import annotations

import duckdb
import polars as pl
import streamlit as st

from ministere_de_l_info._theme import inject_css, render_page_header
from ministere_de_l_info.logging_config import configure_logging

configure_logging()

st.set_page_config(
    page_title="ministère de l'info",
    page_icon=":material/flag:",
    layout="wide",
)

inject_css()

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
        "description": "Cartographie choroplèthe multi-niveaux (régions, départements, EPCI, communes) et démographie INSEE.",
    },
    {
        "page": "pages/2_🗳️_Élections.py",
        "icon": "how_to_vote",
        "label": "Élections",
        "description": "Présidentielles, législatives et municipales 2002-2026, drill-down jusqu'au bureau de vote.",
    },
    {
        "page": "pages/3_🏛️_Législatif.py",
        "icon": "account_balance",
        "label": "Législatif",
        "description": "Composition politique et activité parlementaire de l'Assemblée nationale et du Sénat.",
    },
    {
        "page": "pages/4_📊_Économie.py",
        "icon": "bar_chart",
        "label": "Économie",
        "description": "Indicateurs socio-économiques (pauvreté, chômage, désindustrialisation) croisés avec les résultats électoraux.",
    },
]

row1 = st.columns(2)
row2 = st.columns(2)
for module, col in zip(_MODULES, [*row1, *row2], strict=True):
    with col, st.container(border=True):
        st.page_link(module["page"], label=module["label"], icon=f":material/{module['icon']}:")
        st.caption(module["description"])

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
