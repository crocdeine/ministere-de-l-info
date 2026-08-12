"""Page Législatif — ministere-de-l-info."""

import streamlit as st

from ministere_de_l_info._theme import inject_css
from ministere_de_l_info.pages.legislatif import render

st.set_page_config(page_title="Législatif", page_icon=":material/account_balance:", layout="wide")
inject_css()
render()
