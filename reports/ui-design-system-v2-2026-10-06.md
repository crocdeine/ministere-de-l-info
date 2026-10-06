# Design system v2 « direction éditoriale » — application sur la base J1-J4

**Date** : 2026-10-06 · **Agent** : developpeur-ui · **Périmètre** : patch `design-system-v2.patch` du skill `design-system-mi`, résolution des conflits avec J1-J4, deux écarts décidés (palette d'évolution, numéro d'ADR)

## Résumé exécutif

- Patch appliqué sur `8cb274e` (`git apply -3`) : 5 conflits résolus (CLAUDE.md, index ADR, Accueil, `_theme.py`, `custom.css`) en gardant tous les acquis J1-J4.
- ADR renommé **0014** (0007 = Législatif), révise l'ADR-0009 ; skill aligné (`SKILL.md`, `LISEZ-MOI.md`, `reference/ADR-0014.md`, `tokens.*`, `streamlit/*`).
- Palette d'évolution : **PuOr accessible (J3) conservée**, skill corrigé ; ajout au skill de `COULEUR_ND`, `COULEUR_ZERO`, échelle de score 0-100 %.
- Métriques : valeur jamais tronquée (règle J2 portée sur `stMetricValue` et son `<p>`), taille bornée à 20 % de la largeur de colonne.
- Vérifications : ruff propre, pyright 0 erreur, pytest 661 passés / 1 ignoré, couverture 78,38 % (référence 78,11 %), `tests/test_theme.py` 9/9 (7 du patch + 2 ajoutés).
- Non vérifiable sans navigateur : rendu à 390 px, effet réel du template Plotly `mdi` sous `theme="streamlit"`, lisibilité des titres géants.
- Décisions attendues : (1) valider visuellement la v2 → ADR-0014 « Accepté » ? (2) étendre la cible 44 px aux boutons radio et aux expanders (oui/non) ?
- Rapport du patch d'origine (`session-2026-10-04_design-system-v2.md`) conservé, remplacé par celui-ci.

## Conflits et résolution

| Fichier | Résolution |
|---|---|
| `CLAUDE.md` | Tableau des modules J1-J4 conservé ; ligne Design system passée en « v2 en validation visuelle » (ADR-0014, PuOr maintenue) ; dernier rapport = ce rapport ; ADR 0014 ajouté à la table ; « 14 ADR ». |
| `docs/adr/README.md` | Index J1-J4 conservé ; 0009 « révisé par 0014 » ; ajout de 0013 (manquait à l'index) et 0014 « Proposé — révise 0009 ». |
| `pages/0_🏠_Accueil.py` | En-tête display, eyebrow « Accueil », modules numérotés « 01 — » (patch) **+** champ « Périmètre » de chaque module, tableau « Sources, licences et dates » (`tableau_sources`, `_dates_chargement`) passé en titre de section H2 (capitales + filet). La ligne « Sources : IGN, INSEE… » du patch est retirée : redondante avec le tableau. |
| `_theme.py` | Version v2 (polices sans Spectral, template Plotly `mdi`, `render_page_header` à eyebrow/display échappé, `render_overline`) **+** fonctions J1-J4 conservées : `conserver_selections`, `index_persiste`, `render_donnees_indisponibles`. |
| `custom.css` | Version v2 (identique à `streamlit/custom.css` du skill) **+** portages J1-J4 : règle anti-ellipse des valeurs de métrique, commentaire Plan IGN de `--map-tile-bg`, `--choro-evo-*` en PuOr, nouveaux tokens `--choro-nd` / `--choro-zero`. Libellé de métrique en encre (contraste 19,8:1, supérieur au gris J2). |

Inchangés (vérifiés) : « n.d. », légendes de classement par scrutin, mentions de licence, `nouvelle_carte` (Plan IGN), classes fixes et classe « 0 », `COULEUR_ND`, légendes `avec_nd` : aucun fichier `viz/` ni `pages/` métier n'est touché.

## Écarts appliqués

1. **Palette d'évolution** : `--choro-evo-1..5` = `#e66101 #fdb863 #f7f7f7 #b2abd2 #5e3c99` (= `_COULEURS_EVOLUTION5`) dans `custom.css`, `tokens.css`, `tokens.json`, `streamlit/custom.css` ; `SKILL.md` §2 réécrit (« accessible daltonisme, décision J3 », plus n.d. `#5F6368`, classe zéro `#F0EDE6`, score de bloc blanc → couleur sur 0-100 %). Test `test_tokens_evolution_alignes_sur_palette_accessible` : bloque toute divergence code ↔ skill.
2. **ADR 0014** : fichier renommé, titre, liens, mention de la révision de l'ADR-0009 et des deux écarts ; références « ADR-0007 » du design system remplacées dans le skill, `_theme.py`, `custom.css`, `tests/test_theme.py`. Les références à l'ADR-0007 Législatif sont intactes.

## Métriques longues

`[data-testid="stMetric"]` reçoit `container-type: inline-size` ; la valeur prend `min(clamp(2.25rem, 3.6vw, 3.5rem), 20cqi)` ; `stMetricValue` et ses descendants (dont le `<p>` qui porte l'ellipse de Streamlit) : `white-space: normal`, `overflow: visible`, `text-overflow: unset`, `overflow-wrap: break-word`. Test `test_css_metrique_jamais_tronquee`.

## Ce qui change à l'écran

- **Toutes les pages** : fond blanc ; sidebar en liste capitales séparée par des filets, page active en noir plein ; en-tête = sur-titre « MINISTÈRE DE L'INFO » + icône, titre géant en capitales, sous-titre suivi de la flèche ↘ ; H2 en capitales avec filet ; onglets en capitales soulignés en noir ; champs soulignés ; boutons contour noir, survol Bleu France, export CSV en Bleu France ; alertes sans fond coloré ; graphiques Plotly en Hanken Grotesk, fond blanc, info-bulle noire, légende horizontale en haut.
- **Accueil** : titre display « MINISTÈRE DE L'INFO », modules « 01 — » à « 04 — » sans carte ombrée (filet au-dessus), périmètre, tableau des sources sous un H2.
- **Géographie** : titre « GÉOGRAPHIE TERRITORIALE » sur deux lignes probables ; carte Folium inchangée (iframe).
- **Élections** : métriques (participation, bloc en tête) en très grand corps ; légendes et cartes inchangées.
- **Législatif** : rangée de 6 métriques — vérifier « Extrême droite » / « Extrême gauche » (retour à la ligne attendu, pas d'ellipse) ; filtres de sidebar soulignés.
- **Économie** : métriques et graphiques au nouveau template ; cartes inchangées.

## À regarder (Mathias)

1. Législatif, onglet Composition : 6 métriques, valeurs longues entières.
2. Graphiques Plotly : `st.plotly_chart` garde `theme="streamlit"` par défaut, qui peut recouvrir une partie du template `mdi` (police, couleurs d'axes) — à constater à l'œil.
3. Titres géants des pages et largeur 390 px (pas de défilement horizontal).
4. Contraste : légendes `--grey-600` 6,7:1, captions `--grey-800` 10,9:1, Rouge Marianne 5,0:1 sur blanc — conformes ≥ 4,5:1.
5. Cibles 44 px : boutons, liens de page, sidebar, onglets, champs texte ; **pas** les boutons radio, cases, expanders (question 2).

## Vérifications

- `ruff format` (1 fichier reformaté : Accueil) ; `ruff check` : propre.
- `uvx pyright@1.1.408` : 0 erreur (test du patch corrigé : accès au layout du template via `to_plotly_json()`).
- `pytest -q -m "not slow and not network"` avec base (lien `data` temporaire, retiré) : 661 passés, 1 ignoré, couverture 78,38 %.
- Couleurs en dur hors tokens dans la couche Streamlit de `custom.css` : aucune.
