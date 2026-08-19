"""Page Élections — présidentielles, législatives & municipales Hauts-de-France."""

from __future__ import annotations

import streamlit as st

from ministere_de_l_info._theme import render_page_header
from ministere_de_l_info.pages.elections_legislatives import render as render_legi
from ministere_de_l_info.pages.elections_municipales import render as render_muni
from ministere_de_l_info.pages.elections_presidentielles import render as render_pres
from ministere_de_l_info.viz.elections_queries import DB_PATH

render_page_header(
    icon="how_to_vote", title="Élections", subtitle="Résultats électoraux Hauts-de-France"
)

if not DB_PATH.exists():
    st.error(
        "Base de données absente. Lancez d'abord :\n\n"
        "```bash\nuv run python scripts/init_elections_schema.py\n```"
    )
    st.stop()

tab_pres, tab_legi, tab_muni = st.tabs(["Présidentielles", "Législatives", "Municipales"])

with tab_pres:
    render_pres()

with tab_legi:
    render_legi()

with tab_muni:
    render_muni()
