"""Page Élections — présidentielles, législatives & municipales Hauts-de-France."""

from __future__ import annotations

import streamlit as st

from ministere_de_l_info._theme import (
    conserver_selections,
    render_donnees_indisponibles,
    render_page_header,
)
from ministere_de_l_info.pages.elections_legislatives import render as render_legi
from ministere_de_l_info.pages.elections_municipales import render as render_muni
from ministere_de_l_info.pages.elections_presidentielles import render as render_pres
from ministere_de_l_info.viz.elections_queries import DB_PATH

render_page_header(
    icon="how_to_vote", title="Élections", subtitle="Résultats électoraux Hauts-de-France"
)

if not DB_PATH.exists():
    render_donnees_indisponibles("électorales", base_absente=True)
    st.stop()

# Onglets paresseux (Streamlit ≥ 1.57) : seul l'onglet ouvert est exécuté,
# au lieu de recalculer les trois scrutins (dont la carte municipale de
# ~3 800 communes) à chaque interaction. Les sélections des onglets fermés
# sont conservées (sinon remises à zéro au retour sur l'onglet).
_PREFIXES_ONGLETS: dict[str, tuple[str, ...]] = {
    "Présidentielles": ("pres_",),
    "Législatives": ("legi_",),
    "Municipales": ("muni_",),
}
conserver_selections("elections_onglet", _PREFIXES_ONGLETS)
tab_pres, tab_legi, tab_muni = st.tabs(
    list(_PREFIXES_ONGLETS),
    key="elections_onglet",
    on_change="rerun",
)

with tab_pres:
    if tab_pres.open:
        render_pres()

with tab_legi:
    if tab_legi.open:
        render_legi()

with tab_muni:
    if tab_muni.open:
        render_muni()
