"""Application Streamlit — ministere-de-l-info (test de stack)."""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import geopandas as gpd
import polars as pl
import streamlit as st
from streamlit_folium import st_folium

from ministere_de_l_info.viz.maps import make_regions_choropleth

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).parent / "data" / "ministere.duckdb"

st.set_page_config(
    page_title="ministère de l'info",
    page_icon="🇫🇷",
    layout="wide",
)

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

st.success("✅ Stack opérationnelle. Prochaine étape : import des premières données.")

# Mini-test DuckDB
with st.expander("Test DuckDB"):
    result = duckdb.sql("SELECT 'France' AS pays, 67_000_000 AS habitants").to_df()
    st.dataframe(result, width='stretch')

# Mini-test GeoPandas
with st.expander("Test GeoPandas"):
    st.write(f"GeoPandas version : {gpd.__version__}")
    st.write("GeoPandas est prêt à charger des contours communaux, départementaux et régionaux.")

st.divider()

# ── Carte des régions ─────────────────────────────────────────────────────────

st.header("Carte des régions")


@st.cache_resource
def get_db_connection() -> duckdb.DuckDBPyConnection:
    """Connexion DuckDB partagée — singleton par session Streamlit."""
    con = duckdb.connect(str(_DB_PATH))
    con.execute("INSTALL spatial; LOAD spatial;")
    return con


def _table_regions_existe(con: duckdb.DuckDBPyConnection) -> bool:
    count = con.execute("""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_name = 'geographies_regions'
    """).fetchone()[0]
    return count > 0


if not _DB_PATH.exists():
    st.warning(
        "Base de données absente. Lancez d'abord :\n\n"
        "```bash\npython scripts/etl_regions.py\n```"
    )
else:
    con = get_db_connection()

    if not _table_regions_existe(con):
        st.warning(
            "Table `geographies_regions` absente. Lancez d'abord :\n\n"
            "```bash\npython scripts/etl_regions.py\n```"
        )
    else:
        indicateur = st.selectbox(
            "Indicateur",
            ["population"],
            format_func=lambda x: x.capitalize(),
        )

        carte = make_regions_choropleth(con, indicateur)
        st_folium(carte, width="100%", height=550, returned_objects=[])

        # ── Tableau de données ───────────────────────────────────────────────
        rows = con.execute("""
            SELECT code_insee, nom, population
            FROM geographies_regions
            ORDER BY population DESC
        """).fetchall()

        df_display = pl.DataFrame(
            {
                "Région": [r[1] for r in rows],
                "Code INSEE": [r[0] for r in rows],
                "Population 2024": [
                    f"{r[2]:,}".replace(",", " ") for r in rows
                ],
            }
        )
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        st.caption(
            "Source : data.geopf.fr (IGN ADMIN-EXPRESS COG) — Population INSEE 2024"
        )
