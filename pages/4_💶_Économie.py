"""Page Économie — placeholder."""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Économie", page_icon="💶", layout="wide")
st.title("💶 Économie")

st.info(
    "**Module en cours de développement.**\n\n"
    "Cette section permettra d'explorer les indicateurs économiques territoriaux : "
    "revenus médians, taux de chômage, densité d'entreprises — "
    "données INSEE (Filosofi, DADS, SIRENE) croisées avec les découpages géographiques."
)
st.caption("Disponibilité prévue : prochaine itération du projet.")
