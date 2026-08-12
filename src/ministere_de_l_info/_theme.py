"""Injection du design system (tokens CSS) dans l'application Streamlit.

Le CSS fusionné (`custom.css`, à côté de ce module) contient les tokens
du design system Ministère de l'Info (couleurs, typographie, spacing,
élévation, motion, data-viz) ainsi que la couche de sélecteurs Streamlit
qui les applique à l'UI (`data-testid="..."`, cf.
`reports/research-streamlit-css-selectors.md`).

Les polices Google Fonts (Spectral, Hanken Grotesk, IBM Plex Mono,
Material Symbols Outlined) sont chargées via une balise <link> HTML
séparée : un `@import` CSS placé dans un bloc injecté dynamiquement par
`st.markdown` ne garantit pas un chargement fiable côté navigateur.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

_CSS_PATH = Path(__file__).parent / "custom.css"

_GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Spectral:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400;1,500"
    "&family=Hanken+Grotesk:wght@400;500;600;700;800"
    "&family=IBM+Plex+Mono:wght@400;500;600"
    "&family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,300..600,0..1,-25..0"
    "&display=swap"
)


def _load_css() -> str:
    """Charge le contenu de `custom.css`.

    Volontairement non mis en cache (ni `lru_cache`, ni `st.cache_data`) :
    le fichier est relu à chaque rerun. Coût négligeable (~15 Ko), et ça
    permet de voir les modifications de `custom.css` en rechargeant
    simplement le navigateur, sans redémarrer le process Streamlit — un
    `lru_cache` figerait le CSS en mémoire pour toute la durée du serveur.
    """
    return _CSS_PATH.read_text(encoding="utf-8")


def inject_css() -> None:
    """Injecte les polices et le CSS du design system dans la page courante.

    À appeler une fois, en tête de script, sur chaque page Streamlit qui
    doit refléter le design system (Streamlit ré-exécute intégralement
    chaque page lors de la navigation multipage : l'injection faite dans
    `app.py` ne s'applique pas automatiquement aux fichiers `pages/*.py`).
    """
    st.markdown(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous">'
        f'<link rel="stylesheet" href="{_GOOGLE_FONTS_URL}">',
        unsafe_allow_html=True,
    )
    st.markdown(f"<style>{_load_css()}</style>", unsafe_allow_html=True)


def render_page_header(icon: str, title: str, subtitle: str | None = None) -> None:
    """Affiche un titre de page cohérent (icône Material + H1 Spectral + sous-titre).

    Remplace `st.title("🏷️ Titre")` : ni `st.title` ni `st.header` ne permettent
    d'associer une icône vectorielle *et* un sous-titre avec le même contrôle de
    mise en page. `icon` est un nom d'icône Material Symbols (ex. "account_balance"),
    cf. https://fonts.google.com/icons.
    """
    subtitle_html = f'<p class="mdi-page-subtitle">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f"""
        <div class="mdi-page-header">
          <span class="material-symbols-outlined mdi-page-icon" aria-hidden="true">{icon}</span>
          <h1>{title}</h1>
        </div>
        {subtitle_html}
        """,
        unsafe_allow_html=True,
    )
