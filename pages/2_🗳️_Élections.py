"""Page Élections — présidentielles & législatives Hauts-de-France."""

from __future__ import annotations

import streamlit as st

from ministere_de_l_info.pages.elections_legislatives import render as render_legi
from ministere_de_l_info.pages.elections_presidentielles import render as render_pres
from ministere_de_l_info.viz.elections_queries import DB_PATH

st.set_page_config(page_title="Élections", page_icon="🗳️", layout="wide")
st.title("🗳️ Élections")
st.caption("Résultats électoraux Hauts-de-France")

if not DB_PATH.exists():
    st.error(
        "Base de données absente. Lancez d'abord :\n\n"
        "```bash\nuv run python scripts/init_elections_schema.py\n```"
    )
    st.stop()

tab_pres, tab_legi = st.tabs(["Présidentielles", "Législatives"])

with tab_pres:
    render_pres()

with tab_legi:
    render_legi()
