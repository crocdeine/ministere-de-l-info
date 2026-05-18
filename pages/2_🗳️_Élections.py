"""Page Élections — placeholder."""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Élections", page_icon="🗳️", layout="wide")
st.title("🗳️ Élections")

st.info(
    "**Module en cours de développement.**\n\n"
    "Cette section permettra d'explorer les résultats électoraux français "
    "(présidentielles, législatives, municipales, européennes) par territoire, "
    "avec cartographie des nuances politiques selon la grille officielle du "
    "Ministère de l'Intérieur."
)
st.caption("Disponibilité prévue : prochaine itération du projet.")
