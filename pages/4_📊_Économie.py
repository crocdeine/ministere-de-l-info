"""Page Économie — ministere-de-l-info."""

import streamlit as st

from ministere_de_l_info._theme import inject_css
from ministere_de_l_info.pages.economie import render

st.set_page_config(page_title="Économie", page_icon=":material/bar_chart:", layout="wide")
inject_css()
render()
