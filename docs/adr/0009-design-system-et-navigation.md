# 0009 — Design system et navigation `st.navigation()` / `st.Page()`

Date : 2026-09-24
Statut : Accepté (rédigé a posteriori le 2026-09-24)
Décideurs : Mathias (supervision)

> ADR rétroactif : il documente des décisions prises et appliquées pendant le chantier
> design system (août 2026, commits `05b6a53`, `1ead952`, `d382354`), sans ADR à
> l'époque. Sources : code (`app.py`, `pages/`, `src/ministere_de_l_info/_theme.py`,
> `_blocs_politiques.py`, `custom.css`, `.streamlit/config.toml`) et rapports
> `reports/brainstorm-ui-ux-design-system.md`,
> `reports/session-2026-08-19_design-system-cloture.md`.

## Contexte

Après les phases E et F, l'interface présentait des incohérences entre pages : titres
préfixés d'emoji, `st.set_page_config` absent sur certaines pages, filtres placés
différemment, palettes de blocs politiques divergentes (`legislatif.py` et
`economie.py` avaient chacun leur copie, ex. GAU `#DD0000` au lieu de `#E84C61`),
page d'accueil réduite à un écran de diagnostic technique.

Un design system (« Claude Design », fourni en ZIP le 2026-07-30) définissait des
tokens CSS : Bleu France `#000091`, Rouge Marianne `#E1000F`, polices Spectral / Hanken
Grotesk / IBM Plex Mono, espacements, élévations, durées d'animation, palette data-viz
dont les couleurs des 6 blocs (`--nuance-*`).

Contrainte technique : avec la découverte automatique du dossier `pages/`, l'icône de
la sidebar est dérivée du nom de fichier (emoji uniquement) ; une icône vectorielle
dans la navigation impose l'API `st.navigation()` / `st.Page()`.

## Décision

### D1 — Tokens CSS injectés depuis un fichier unique

`src/ministere_de_l_info/custom.css` fusionne les tokens du design system et une couche
de sélecteurs Streamlit (`data-testid`). Il est injecté par
`_theme.py::inject_css()`, qui charge aussi les polices Google Fonts (Spectral,
Hanken Grotesk, IBM Plex Mono, Material Symbols Outlined) par une balise `<link>` —
pas par `@import`, dont le chargement n'est pas fiable dans un bloc injecté.
Le thème natif Streamlit (`.streamlit/config.toml`) est aligné : `base = "light"`,
`primaryColor = "#000091"`.

### D2 — `app.py` devient un routeur `st.navigation()`

`app.py` ne contient plus de contenu : il appelle une fois `configure_logging()`,
`st.set_page_config()` et `inject_css()`, puis déclare cinq `st.Page` et exécute la
page choisie.

| Fichier | Titre | Icône Material | URL |
|---|---|---|---|
| `pages/0_🏠_Accueil.py` | Accueil (par défaut) | `home` | `/accueil` |
| `pages/1_📍_Géographie.py` | Géographie | `map` | `/geographie` |
| `pages/2_🗳️_Élections.py` | Élections | `how_to_vote` | `/elections` |
| `pages/3_🏛️_Législatif.py` | Législatif | `account_balance` | `/legislatif` |
| `pages/4_📊_Économie.py` | Économie | `bar_chart` | `/economie` |

Les pages n'appellent plus ni `set_page_config` ni `inject_css`. Chaque page affiche son
titre via `_theme.py::render_page_header(icon, title, subtitle)`.

### D3 — Accueil = hub de navigation

L'ancien contenu d'`app.py` est déplacé dans `pages/0_🏠_Accueil.py` : quatre tuiles
(`st.page_link` dans `st.container(border=True)`) vers les modules ; le diagnostic
technique est relégué dans un `st.expander`.

### D4 — Convention de filtres

Sidebar = filtres qui structurent toute la page ; inline = sélecteurs propres à un
onglet (décision actée le 2026-08-01). Application : Géographie et Législatif
(Chambre, Département) en sidebar ; Élections et Économie sans filtre global,
sélecteurs inline par onglet.

### D5 — Couleurs des blocs politiques

`src/ministere_de_l_info/_blocs_politiques.py` porte l'ordre, les libellés et les
couleurs des 6 blocs, alignés sur les tokens `--nuance-*` et sur les valeurs insérées
dans la table `blocs_politiques` (`etl/schema_elections.py`). Les pages Législatif et
Économie l'importent au lieu de définir leurs propres constantes.

## Alternatives considérées

| Alternative | Raison d'écarter |
|---|---|
| **Conserver la découverte automatique `pages/`** | Icônes de sidebar limitées aux emojis du nom de fichier |
| **`@import` des polices dans le CSS** | Chargement non garanti dans un bloc injecté par `st.markdown` |
| **Thème uniquement par CSS (sans `config.toml`)** | Les composants qui lisent le thème interne de Streamlit (dataframe, Plotly `theme="streamlit"`, widgets natifs) restaient sombres tant que `base = "dark"` |
| **Composants DSFR (dsfr-chart)** | Composants Vue, non intégrables tels quels dans Streamlit ; seuls le vocabulaire et les principes de mise en page sont repris |
| **Framework front dédié** | Contraire à l'ADR-0002 (Streamlit, un seul langage) |

## Conséquences

**Positives**
- Configuration et injection CSS centralisées (un seul point d'entrée).
- Icônes vectorielles dans la sidebar, URLs courtes sans emoji ni accent.
- Palette des blocs identique entre modules.

**Négatives**
- Les URLs de pages ont changé (sans enjeu selon le rapport de clôture : pas
  d'utilisateurs externes avec favoris).
- `custom.css` dépend de `data-testid` internes à Streamlit (vérifiés sur la
  version 1.57.0) : une montée de version de Streamlit peut casser des sélecteurs.
- Le routeur `app.py` n'est couvert que par un smoke test serveur
  (`tests/test_streamlit_smoke.py`, marqueur `slow`, contrôle de santé HTTP) ; les tests
  AppTest ciblent directement les fichiers de `pages/`, sans passer par la navigation.

**Réversibilité** : moyenne. Revenir à la découverte automatique supposerait de
réintroduire `set_page_config`/`inject_css` dans chaque page.

## Points ouverts

Signalés sans être tranchés.

1. **« Source unique » des couleurs** : les couleurs des blocs existent en trois
   copies synchronisées à la main — tokens `--nuance-*` de `custom.css`,
   `_blocs_politiques.py`, et valeurs insérées dans `blocs_politiques` par
   `schema_elections.py` (lues par les pages Élections via la base). Aucun test ne
   vérifie leur égalité.
2. **Nom de fichier des pages** : les emojis restent dans les noms de fichier de
   `pages/` alors qu'ils ne servent plus à la navigation.
3. **Pas de release incluant le chantier** : la dernière image publiée
   (`v0.5-economie-legislatif`, 2026-06-28) est antérieure au design system.
4. **Page Géographie** : son message « base absente » renvoie à
   `scripts/etl_regions.py` (script en attente de suppression) plutôt qu'à
   `scripts/etl_territoires.py`.
5. **Couleurs hors design system** : la page Économie utilise encore des couleurs
   codées en dur pour la comparaison HdF / France (`#E63946`, `#457B9D`) et la
   palette Folium `YlOrRd`.
