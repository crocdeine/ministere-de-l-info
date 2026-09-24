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

    Depuis la migration vers `st.navigation()` (app.py = routeur unique),
    un seul appel dans `app.py`, avant `st.navigation(...).run()`, suffit :
    ce code s'exécute à chaque interaction quelle que soit la page affichée.
    Les fichiers `pages/*.py` n'ont plus besoin de l'appeler individuellement.
    """
    st.markdown(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous">'
        f'<link rel="stylesheet" href="{_GOOGLE_FONTS_URL}">',
        unsafe_allow_html=True,
    )
    st.markdown(f"<style>{_load_css()}</style>", unsafe_allow_html=True)


def conserver_selections(cle_onglets: str, prefixes_par_onglet: dict[str, tuple[str, ...]]) -> None:
    """Conserve les sélections des onglets fermés (onglets paresseux).

    Avec `st.tabs(key=cle_onglets, on_change="rerun")`, les widgets d'un onglet
    fermé ne sont pas rendus : Streamlit efface alors leur état et l'utilisateur
    retrouve les valeurs par défaut en revenant sur l'onglet. Réaffecter la clé à
    elle-même avant tout widget interrompt ce nettoyage (procédé documenté par
    Streamlit, « Widget behavior »).

    `prefixes_par_onglet` associe chaque libellé d'onglet aux préfixes des clés de
    ses widgets ; l'onglet par défaut est le premier. Seules les clés des onglets
    fermés sont réaffectées : l'onglet ouvert rend ses widgets normalement (pas
    d'avertissement « default value + Session State API »). Les boutons de
    téléchargement sont exclus : leur état ne peut pas être écrit.
    """
    onglet_ouvert = st.session_state.get(cle_onglets, next(iter(prefixes_par_onglet)))
    prefixes_fermes = tuple(
        p
        for onglet, prefixes in prefixes_par_onglet.items()
        if onglet != onglet_ouvert
        for p in prefixes
    )
    if not prefixes_fermes:
        return
    for cle in list(st.session_state.keys()):
        if not isinstance(cle, str) or not cle.startswith(prefixes_fermes):
            continue
        if "download" in cle or "_dl_" in cle:
            continue
        st.session_state[cle] = st.session_state[cle]


def render_donnees_indisponibles(
    module: str,
    *,
    base_absente: bool,
    commande_dev: str | None = None,
) -> None:
    """Message commun « données indisponibles », lisible par un non-développeur.

    `base_absente=True` : le fichier DuckDB n'existe pas (ou ne s'ouvre pas).
    `base_absente=False` : la base existe mais ne contient pas les données du module.
    La consigne principale vise l'utilisateur de l'application installée
    (`install.sh` / `update.sh`) ; la commande de chargement pour les développeurs
    est repliée dans un expander.
    """
    if base_absente:
        st.warning(
            f"**Données {module} non disponibles : la base de données est introuvable.**\n\n"
            "Si vous utilisez l'application installée, lancez la mise à jour "
            "(script `update.sh`), qui télécharge la dernière base publiée. "
            "Lors d'une première installation, relancez `install.sh`.",
            icon=":material/database:",
        )
        commande = commande_dev or "./scripts/download_db.sh"
    else:
        st.warning(
            f"**Données {module} non disponibles dans la base installée.**\n\n"
            "La base de données est présente mais ne contient pas encore ces données. "
            "Lancez la mise à jour (script `update.sh`) pour récupérer la dernière "
            "base publiée.",
            icon=":material/database:",
        )
        commande = commande_dev
    if commande:
        with st.expander("Informations pour les développeurs"):
            st.caption("Depuis le dépôt de code, la commande suivante charge ces données :")
            st.code(commande, language="bash")


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
