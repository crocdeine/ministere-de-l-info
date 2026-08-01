"""Page d'accueil — ministere-de-l-info."""

from __future__ import annotations

import duckdb
import polars as pl
import streamlit as st

from ministere_de_l_info._theme import inject_css
from ministere_de_l_info.logging_config import configure_logging

configure_logging()

st.set_page_config(
    page_title="ministère de l'info",
    page_icon="🇫🇷",
    layout="wide",
)

inject_css()

st.title("🇫🇷 ministère de l'info")
st.caption("Application de data-visualisation politique, électorale et territoriale française")

st.divider()

st.subheader("Vérification de la stack")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Streamlit", st.__version__)

with col2:
    st.metric("DuckDB", duckdb.__version__)

with col3:
    st.metric("Polars", pl.__version__)

st.success("✅ Stack opérationnelle.")

with st.expander("Test DuckDB"):
    result = duckdb.sql("SELECT 'France' AS pays, 67_000_000 AS habitants").to_df()
    st.dataframe(result, width="stretch")

st.divider()

st.info("Utilisez le menu de navigation à gauche pour explorer les visualisations.")
