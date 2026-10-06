"""Injection du design system v2 « direction éditoriale » dans Streamlit.

Le CSS (`custom.css`, à côté de ce module) contient les tokens du design
system (couleurs, typographie, espacement, forme, mouvement, data-viz) et
la couche de sélecteurs Streamlit qui les applique (`data-testid="..."`).
Décision et principes : `docs/adr/0007-design-system-direction-editoriale.md`.

Les polices Google Fonts (Hanken Grotesk, IBM Plex Mono, Material Symbols
Outlined) sont chargées via une balise <link> HTML séparée : un `@import`
CSS dans un bloc injecté par `st.markdown` ne se charge pas de façon fiable.

Le module enregistre aussi un template Plotly (`mdi`) aligné sur le design
system et l'active par défaut, pour que les graphiques Plotly Express
adoptent la même typographie et les mêmes filets sans modifier chaque page.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

_CSS_PATH = Path(__file__).parent / "custom.css"

_GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Hanken+Grotesk:wght@400;500;600;700;800;900"
    "&family=IBM+Plex+Mono:wght@400;500;600"
    "&family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,300..600,0..1,-25..0"
    "&display=swap"
)

# Couleurs reprises de custom.css (Plotly ne lit pas les variables CSS).
INK = "#0a0a0a"
PAPER = "#ffffff"
GREY_600 = "#5c5c5c"
RULE_SOFT = "#d9d9d9"
BLEU_FRANCE = "#000091"
ROUGE_MARIANNE = "#e1000f"

_FONT_SANS = "Hanken Grotesk, Helvetica Neue, Helvetica, sans-serif"

PLOTLY_TEMPLATE_NAME = "mdi"

# Flèche diagonale ↘ — seul signe graphique de la marque.
_ARROW_SVG = (
    '<svg class="mdi-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="3" stroke-linecap="square" aria-hidden="true">'
    '<path d="M6 6 L18 18 M18 8 V18 H8"></path></svg>'
)


def _load_css() -> str:
    """Charge le contenu de `custom.css`.

    Volontairement non mis en cache : le fichier est relu à chaque rerun
    (coût négligeable) pour voir les modifications CSS en rechargeant
    simplement le navigateur, sans redémarrer Streamlit.
    """
    return _CSS_PATH.read_text(encoding="utf-8")


def build_plotly_template() -> go.layout.Template:
    """Construit le template Plotly du design system (fond blanc, filets encre, grotesque)."""
    axis = {
        "showgrid": True,
        "gridcolor": RULE_SOFT,
        "gridwidth": 1,
        "zeroline": False,
        "showline": True,
        "linecolor": INK,
        "linewidth": 1,
        "ticks": "outside",
        "tickcolor": INK,
        "ticklen": 4,
        "tickfont": {"family": _FONT_SANS, "size": 12, "color": INK},
        "title": {"font": {"family": _FONT_SANS, "size": 12, "color": GREY_600}},
    }
    return go.layout.Template(
        layout={
            "font": {"family": _FONT_SANS, "size": 13, "color": INK},
            "paper_bgcolor": PAPER,
            "plot_bgcolor": PAPER,
            "colorway": [BLEU_FRANCE, INK, ROUGE_MARIANNE, GREY_600, "#3b7dd8", "#f5b800"],
            "title": {
                "font": {"family": _FONT_SANS, "size": 18, "color": INK, "weight": 800},
                "x": 0,
                "xanchor": "left",
            },
            "xaxis": {**axis, "showgrid": False},
            "yaxis": {**axis, "showline": False, "ticks": ""},
            "legend": {
                "font": {"family": _FONT_SANS, "size": 12, "color": INK},
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "x": 0,
                "title": {"text": ""},
            },
            "hoverlabel": {
                "bgcolor": INK,
                "bordercolor": INK,
                "font": {"family": _FONT_SANS, "size": 13, "color": PAPER},
            },
            "margin": {"l": 8, "r": 8, "t": 48, "b": 8},
            "bargap": 0.25,
        }
    )


def register_plotly_template() -> None:
    """Enregistre le template `mdi` et en fait le défaut (idempotent)."""
    pio.templates[PLOTLY_TEMPLATE_NAME] = build_plotly_template()
    pio.templates.default = PLOTLY_TEMPLATE_NAME


def inject_css() -> None:
    """Injecte les polices et le CSS du design system dans la page courante.

    Un seul appel dans `app.py`, avant `st.navigation(...).run()` : ce code
    s'exécute à chaque interaction quelle que soit la page affichée. Active
    aussi le template Plotly du design system.
    """
    st.markdown(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous">'
        f'<link rel="stylesheet" href="{_GOOGLE_FONTS_URL}">',
        unsafe_allow_html=True,
    )
    st.markdown(f"<style>{_load_css()}</style>", unsafe_allow_html=True)
    register_plotly_template()


def render_page_header(
    icon: str,
    title: str,
    subtitle: str | None = None,
    *,
    eyebrow: str = "Ministère de l'Info",
    display: bool = False,
) -> None:
    """Affiche l'en-tête éditorial d'une page.

    Structure : sur-titre en capitales (icône Material + `eyebrow`), titre
    géant en capitales, puis sous-titre décalé à droite suivi de la flèche ↘.
    `icon` est un nom d'icône Material Symbols (ex. "account_balance").
    `display=True` agrandit encore le titre (page d'accueil).
    """
    title_class = "mdi-page-title mdi-page-title--display" if display else "mdi-page-title"
    subtitle_html = (
        f'<div class="mdi-page-subtitle"><span>{escape(subtitle)}</span>{_ARROW_SVG}</div>'
        if subtitle
        else ""
    )
    st.markdown(
        f'<header class="mdi-page-header">'
        f'<p class="mdi-eyebrow">'
        f'<span class="material-symbols-outlined" aria-hidden="true">{escape(icon)}</span>'
        f"{escape(eyebrow)}</p>"
        f'<h1 class="{title_class}">{escape(title)}</h1>'
        f"{subtitle_html}"
        f"</header>",
        unsafe_allow_html=True,
    )


def render_overline(text: str) -> None:
    """Affiche un numéro ou repère de section en chasse fixe (ex. « 01 — »)."""
    st.markdown(f'<p class="mdi-overline">{escape(text)}</p>', unsafe_allow_html=True)
