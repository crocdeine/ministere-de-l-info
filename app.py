"""Point d'entrée — routeur multipage (st.navigation) et coquille partagée.

Ce fichier ne contient plus de contenu de page : il configure l'app une
seule fois (page config, logging, injection CSS) puis délègue l'affichage
à la page sélectionnée via `st.navigation`. C'est ce qui permet d'associer
une icône Material Symbols à chaque entrée de la sidebar — impossible avec
la découverte automatique classique du dossier `pages/`, qui dérive l'icône
du nom de fichier (emoji uniquement).
"""

from __future__ import annotations

import streamlit as st

from ministere_de_l_info._theme import inject_css
from ministere_de_l_info.logging_config import configure_logging

configure_logging()

st.set_page_config(
    page_title="ministère de l'info",
    page_icon=":material/flag:",
    layout="wide",
)
inject_css()

pg = st.navigation(
    [
        st.Page(
            "pages/0_🏠_Accueil.py",
            title="Accueil",
            icon=":material/home:",
            url_path="accueil",
            default=True,
        ),
        st.Page(
            "pages/1_📍_Géographie.py",
            title="Géographie",
            icon=":material/map:",
            url_path="geographie",
        ),
        st.Page(
            "pages/2_🗳️_Élections.py",
            title="Élections",
            icon=":material/how_to_vote:",
            url_path="elections",
        ),
        st.Page(
            "pages/3_🏛️_Législatif.py",
            title="Législatif",
            icon=":material/account_balance:",
            url_path="legislatif",
        ),
        st.Page(
            "pages/4_📊_Économie.py",
            title="Économie",
            icon=":material/bar_chart:",
            url_path="economie",
        ),
    ]
)
pg.run()
