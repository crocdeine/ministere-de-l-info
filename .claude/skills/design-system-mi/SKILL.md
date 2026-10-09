---
name: design-system-mi
description: Design system v2 « direction éditoriale » de ministere-de-l-info (ADR-0014) — couleurs, typographie, espacements, composants Streamlit, template Plotly, règles de rédaction. À charger pour toute tâche d'interface, de style, de page Streamlit, de graphique Plotly, de maquette HTML ou de visuel du projet.
---

# Design system Ministère de l'Info — v2 « direction éditoriale »

Grammaire swiss/éditoriale : noir et blanc, grotesque très gras en capitales,
filets d'un pixel, beaucoup de blanc. Le bleu signifie, le noir structure.
Décision : `docs/adr/0014-design-system-direction-editoriale.md`.

Fichiers de référence (dans ce dossier de skill) :

- `tokens.css` — toutes les variables CSS (source de vérité des valeurs).
- `tokens.json` — les mêmes valeurs, groupées (color, typography, spacing, shape, motion, dataviz).
- `streamlit/custom.css`, `streamlit/_theme.py`, `streamlit/config.toml` — l'implémentation Streamlit de référence.
- `reference/ADR-0014.md`, `reference/apercu-accueil.png`.

## 1. Principes (non négociables)

1. **Le chiffre est le titre.** Les nombres s'affichent en très grand corps ; chaque vue commence par ses indicateurs.
2. **Le noir structure, le bleu signifie.** Interface noir `#0a0a0a` / blanc `#ffffff`. Bleu France `#000091` = action, sélection, focus. Rouge Marianne `#e1000f` = alertes et limites UNIQUEMENT.
3. **Le blanc est un matériau.** Aucune ombre, aucun dégradé, aucun arrondi sur les surfaces. La structure vient de filets de 1 px encre.
4. **Toujours citer la source.** Chaque visualisation se termine par `st.caption("Source : …")` et ses limites.

## 2. Couleurs

| Rôle | Token | Valeur |
|---|---|---|
| Encre (texte, filets, bouton primaire) | `--ink` | `#0a0a0a` |
| Papier (fond unique) | `--paper` | `#ffffff` |
| Légendes / métadonnées | `--grey-600` | `#5c5c5c` (6,6:1) |
| Texte de légende long | `--grey-800` | `#3d3d3d` |
| Séparateur de lignes | `--rule-soft` | `#d9d9d9` |
| Zones sans donnée, survol | `--grey-100` | `#f2f2f2` |
| Action / sélection | `--bleu-france` | `#000091` |
| Alerte / limite | `--rouge-marianne` | `#e1000f` |

**Palette « Papier » (ADR-0016, application web uniquement)** : `--papier-50` `#f9f6f2` (fond de section, `--surface-section`), `--papier-100` `#f3ede5` (en-tête de module, `--surface-header`), `--papier-200` `#eee4d9` (sélection de ligne), `--sable-700` `#6a6156` (métadonnées sur papier, `--text-meta-warm`). Jamais sous une carte ou un graphique partisan (plaque blanche `--paper`). Pas de couleur par module : numérotation « 0X — ». Étiquette de méthode « Grille officielle » / « Reconstruit » sur chaque visualisation partisane.

**Data-viz — ne jamais inventer d'autres couleurs** (source unique : `_blocs_politiques.py`, `viz/_display.py`, `viz/maps_elections.py`) :

- Nuances : EXG `#8b0000` · GAU `#e84c61` · DIV `#9e9e9e` · CENT `#f5b800` · DTE `#3b7dd8` · EXD `#1f3864` (ordre gauche → droite).
- Choroplèthe population (YlOrRd 5) : `#ffffb2 #fecc5c #fd8d3c #f03b20 #bd0026`.
- Choroplèthe évolution (PuOr 5, accessible daltonisme, décision J3 — `_COULEURS_EVOLUTION5`) : `#e66101 #fdb863 #f7f7f7 #b2abd2 #5e3c99`. Jamais de rouge-vert.
- Donnée non disponible (« n.d. ») : `#5F6368` (`COULEUR_ND`), légendes `avec_nd`.
- Classe « 0 » (indicateurs où zéro est fréquent) : `#F0EDE6` (`COULEUR_ZERO`), distincte de la 1re classe et du gris n.d.
- Score d'un bloc : dégradé linéaire blanc → couleur du bloc sur une échelle **fixe 0-100 %** des exprimés (`ECHELLE_SCORE_MAX`), identique aux deux tours.

Interdit : fond gris de page, cartes blanches avec ombre, callouts à fond coloré, barre colorée à gauche, Bleu France en aplat décoratif.

## 3. Typographie

Une famille d'interface : **Hanken Grotesk** (400–900). Données : **IBM Plex Mono** (`font-variant-numeric: tabular-nums`). Spectral n'est plus utilisé.

| Rôle | Taille | Graisse | Interlignage | Approche | Casse |
|---|---|---|---|---|---|
| Display (accueil) | `clamp(56px, 11vw, 168px)` | 900 | 0,88 | −0,045 em | CAPITALES |
| Titre de page (H1) | `clamp(48px, 8vw, 120px)` | 900 | 0,88 | −0,045 em | CAPITALES |
| Titre de section (H2) | `clamp(28px, 3vw, 44px)`, filet 1 px au-dessus | 800 | 0,95 | −0,035 em | CAPITALES |
| Titre 3 | 22 px | 800 | 1,15 | 0 | CAPITALES |
| Chiffre-clé (métrique) | `clamp(36px, 3,6vw, 56px)` | 900 | 0,95 | −0,04 em | — |
| Courant | 16 px | 400 | 1,55 | 0 | phrase |
| Libellé / légende de champ | 12 px | 500 | 1,5 | +0,04 em | CAPITALES |
| Légende de source | 13 px | 400 | 1,5 | 0 | phrase, `--grey-800` |
| Données / repères « 01 — » | 13–14 px Plex Mono | 400 | — | — | — |

## 4. Espace et forme

- Grille de 4 px : 4 · 8 · 12 · 16 · 24 · 32 · 48 · 80 · 120 · 160.
- Entre sections : 120–160 px desktop ; marge latérale 16 px mobile, 80 px desktop.
- Rayon : **0** (surfaces, cartes, images) · **8 px** (boutons, champs, étiquettes).
- Traits : 1 px `--ink` (structure) · 1 px `--rule-soft` (lignes de tableau).
- Focus : `outline: 2px solid #000091; outline-offset: 3px` — jamais supprimé.
- Cible tactile minimale : 44 px de haut.
- Mouvement : 140–360 ms, `cubic-bezier(0.2,0,0,1)`, pas de rebond, respecter `prefers-reduced-motion` (tous les jetons de durée, dont `--duration-map-fade`, passent à 0 ms).
- Signe de marque unique : la flèche diagonale ↘ (SVG `M6 6 L18 18 M18 8 V18 H8`, trait 3, extrémités carrées).

## 5. Composants

| Composant | Règle |
|---|---|
| Bouton primaire | fond encre, texte blanc, 44 px, rayon 8, capitales 12 px graisse 600 |
| Bouton secondaire | fond blanc, contour 1 px encre |
| Survol de tout bouton | fond et contour Bleu France, texte blanc |
| Export CSV (`st.download_button`) | Bleu France plein |
| Lien fléché | capitales 14 px graisse 800, souligné 2 px, suivi de ↘ |
| Pastille de navigation | contour 1 px, rayon 8, capitales 12 px ; active = encre pleine |
| Champ / select | libellé capitales gris 12 px ; champ sans boîte, filet bas 1 px encre ; focus = filet 2 px Bleu France |
| Indicateur (`st.metric`) | pas de carte : filet encre au-dessus, libellé capitales, chiffre 900 ; écart en Plex Mono |
| Étiquette de nuance | carré 12 px de la couleur + code en capitales, contour 1 px, rayon 8 |
| Tableau | en-tête capitales 12 px sous filet encre ; corps Plex Mono ; lignes séparées par `--rule-soft` |
| Source / limite | filet encre au-dessus, libellé « SOURCE » ou « LIMITE » (carré rouge), texte 14 px `--grey-800` |
| Carte de module | visuel plein cadre sans arrondi ; dessous : « 01 — TITRE » à gauche, bouton contour à droite |
| Onglets | capitales 12 px, actif = soulignement encre 3 px |
| Sidebar | liste en capitales séparée par des filets ; page active = fond encre, texte blanc |

## 6. Streamlit — comment l'appliquer

- **Une seule injection** : `inject_css()` dans `app.py` (charge les polices par `<link>`, injecte `custom.css`, active le template Plotly `mdi`). Ne jamais appeler dans les pages.
- **En-tête de page** : `render_page_header(icon, title, subtitle=None, *, eyebrow="Ministère de l'Info", display=False)` — jamais `st.title`.
- **Repère de section** : `render_overline("01 —")`.
- **Sections** : `st.markdown("## Titre")` ou `st.subheader` → stylé automatiquement (capitales + filet).
- **Cartes** : `st.container(border=True)` → rendu automatiquement comme bloc à filet supérieur.
- **Boutons** : `type="primary"` pour l'action principale (encre) ; les autres restent en contour.
- **Graphiques** : Plotly Express hérite du template `mdi` — ne pas passer `template=`. Couleurs de blocs via `_blocs_politiques.py`. Les constantes `INK`, `PAPER`, `BLEU_FRANCE`, `ROUGE_MARIANNE`, `GREY_600`, `RULE_SOFT` de `_theme.py` servent quand Plotly a besoin d'une couleur en dur.
- **Nouveau style** : ajouter les règles dans `custom.css`, en utilisant uniquement `var(--…)` ; sélecteurs `data-testid` seulement (jamais `.st-emotion-cache-*`) ; vérifier dans le DOM réel de Streamlit 1.57.
- **Limites** : cellules de `st.dataframe` (canvas) et cartes Folium (iframe) non stylables en CSS.

## 7. Rédaction

- Français, registre administratif neutre, sans « vous » ni exclamation.
- Typographie française : espace insécable avant `: ; ? !` et dans les grands nombres (`48 213`), virgule décimale (`71,2 %`), guillemets « ».
- Libellés = groupes nominaux courts (*Année*, *Tour*, *Niveau territorial*).
- Pas d'emoji dans l'interface : numérotation « 01 — » et icônes Material Symbols.
- Aucun chiffre inventé : une valeur manquante s'écrit `[VALEUR]` dans une maquette.

## 8. Vérification avant de livrer une interface

- [ ] Aucune couleur en dur hors tokens (sauf data-viz listée ci-dessus).
- [ ] Contraste texte ≥ 4,5:1 (légendes en `--grey-600` minimum, jamais plus clair).
- [ ] Cibles cliquables ≥ 44 px, focus visible.
- [ ] Rendu correct à 390 px de large (colonnes empilées, pas de défilement horizontal).
- [ ] Source citée sous chaque visualisation.
- [ ] `uv run ruff check .` et `uv run pytest tests/test_theme.py` passent.
