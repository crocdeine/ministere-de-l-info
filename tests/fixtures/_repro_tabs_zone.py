"""Script minimal pour AppTest : reproduit le bloc de sélecteurs Présidentielles
(annee/tour/zone/mode_carte) sous onglets paresseux, avec les VRAIS helpers du
projet (`conserver_selections`, `index_persiste`) — cf. `test_ui_fixes_2026_09_25.py`.
"""

import streamlit as st

from ministere_de_l_info._theme import conserver_selections, index_persiste

_ANNEES = [2002, 2007, 2012, 2017, 2022]
_ZONES = {
    "circo21": "21e circonscription du Nord — Valenciennes (20 communes)",
    "hdf": "Hauts-de-France entière (chargement plus long)",
}
_MODES_CARTE = ["Bloc dominant", "Score d'un bloc"]
_BLOCS = ["EXG", "GAU", "DIV", "CENT", "DTE", "EXD"]

_PREFIXES = {
    "Présidentielles": ("pres_",),
    "Législatives": ("legi_",),
    "Municipales": ("muni_",),
}
conserver_selections("onglet", _PREFIXES)
tab_pres, tab_legi, tab_muni = st.tabs(list(_PREFIXES), key="onglet", on_change="rerun")

with tab_pres:
    if tab_pres.open:
        c1, c2, c3, c4 = st.columns([2, 1, 2, 2])
        with c1:
            annee = st.selectbox(
                "Année",
                _ANNEES,
                index=index_persiste("pres_annee", _ANNEES, len(_ANNEES) - 1),
                key="pres_annee",
            )
        with c2:
            tour = st.radio(
                "Tour", [1, 2], index=index_persiste("pres_tour", [1, 2]), key="pres_tour"
            )
        with c3:
            zone = st.radio(
                "Zone",
                list(_ZONES),
                index=index_persiste("pres_zone", list(_ZONES)),
                format_func=lambda x: _ZONES[x],
                key="pres_zone",
            )
        with c4:
            mode_carte = st.radio(
                "Mode de carte",
                _MODES_CARTE,
                index=index_persiste("pres_mode_carte", _MODES_CARTE),
                key="pres_mode_carte",
            )
            if mode_carte == "Score d'un bloc":
                st.selectbox(
                    "Bloc",
                    _BLOCS,
                    index=index_persiste("pres_bloc_sel", _BLOCS, 3),
                    key="pres_bloc_sel",
                )
        st.write(f"ZONE_UTILISEE={zone}")

with tab_legi:
    if tab_legi.open:
        st.selectbox("Année (legi)", [2017, 2022], key="legi_annee")
        st.write("onglet legi")

with tab_muni:
    if tab_muni.open:
        st.write("onglet muni")
