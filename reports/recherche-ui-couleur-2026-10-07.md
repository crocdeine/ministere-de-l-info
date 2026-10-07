# Recherche UI — introduire de la couleur sans casser la direction éditoriale

Date : 2026-10-07 · Rôle : direction artistique (lecture seule, aucun fichier modifié hors ce rapport)
Entrées lues : skill `design-system-mi` (SKILL.md, tokens.css), ADR-0014, skill `data-viz-politique`, `src/ministere_de_l_info/_blocs_politiques.py`, `.streamlit/config.toml`, captures `docs/captures/design-v2/` (accueil, élections, législatif), maquette web `origin/poc/interface-web` (`web/src/styles.css`, `maquette_1440.png`, `maquette_carte.jpg`).

## Résumé (≤ 10 lignes)

1. Toute teinte franche est déjà « prise » par la politique : rouge/rose = gauche, bleu/marine = droite et extrême droite, jaune = centre, gris = divers, vert = écologistes (niveau nuance), brun/noir = connotation fasciste, violet = ancien code FN chez certains titres. **Il n'existe pas de teinte vierge** ; la couleur d'interface doit donc être *faible en saturation, cantonnée aux surfaces, et tenue hors des cartes*.
2. Recommandation : **palette A « Papier »** (neutres chauds dérivés du « gris galet » DSFR) pour les fonds de section et en-têtes, Bleu France inchangé pour l'action. Risque de neutralité quasi nul, contraste conservé (encre 18,4:1).
3. En option, **palette C « Archipel »** (sarcelle DSFR `#006a6f`, 6,38:1) comme couleur unique des **graphiques non partisans** (Économie, Géographie). Risque modéré (proximité « écologie »), à trancher par Mathias.
4. **Pas de code couleur par module** (risque de collision avec les blocs dans Élections/Législatif) ; repère de module par numéro « 0X — » et pictogramme.
5. Mode sombre faisable en tokens, mais **les cartes et graphiques partisans restent sur une plaque claire** : EXD `#1f3864` et EXG `#8b0000` tombent à 1,6–1,8:1 sur fond sombre.
6. Deux défauts existants relevés : Bleu France (action) est voisin du marine EXD dans les formulaires adjacents aux cartes ; le skill `data-viz-politique` donne des couleurs de blocs différentes de `_blocs_politiques.py`.

## 1. Constat sur l'existant

- **Captures v2** : interface strictement noir/blanc ; la seule couleur visible est celle des blocs (carte, camemberts, courbes) et le Bleu France des boutons radio sélectionnés. C'est précisément ce qui donne l'impression d'« absence de couleur » : la couleur n'apparaît que là où elle a un sens politique, ce qui est sain, mais l'interface paraît austère et les pages Économie/Géographie n'ont aucun repère chromatique.
- **Rythme** : 120–160 px entre sections. Adapté à l'Accueil éditorial, trop aéré pour une page d'analyse (capture Élections : la carte commence à ~520 px du haut sur 1000 ; maquette 1440 : 3 sections sur 2 400 px).
- **Point de vigilance actuel** : sur la capture Élections, les radios sélectionnées sont en Bleu France `#000091` juste au-dessus d'une carte dont le bloc dominant est EXD `#1f3864` (marine). ΔE76 Bleu France ↔ EXD = 63, ↔ DTE = 59 (les plus proches de toute la palette de blocs). Pas de confusion de lecture, mais une continuité chromatique « interface bleue / carte marine » à éviter autour des cartes.
- **Incohérence documentaire** : `data-viz-politique/SKILL.md` §3 indique GAU `#DD0000`, DIV `#888888`, CENT `#FFEB00`, DTE `#0066CC`, EXD `#0D378A` ; la source de vérité `_blocs_politiques.py` utilise `#E84C61`, `#9E9E9E`, `#F5B800`, `#3B7DD8`, `#1F3864`. Le skill design-system-mi est, lui, aligné. À corriger par l'outilleur (maintenance, aucune décision de fond).

## 2. Références et ce qu'on en retient

| Référence | Ce qu'elle fait | Ce qu'on retient |
|---|---|---|
| **DSFR** (système de design de l'État) — palette relevée dans `@gouvfr/dsfr` `dist/core/core.min.css` et `dist/scheme/scheme.min.css` (jsDelivr) | Couleurs fonctionnelles (Bleu France, Rouge Marianne) + 17 « couleurs illustratives » (tilleul-verveine, archipel, écume, gris galet, café crème, glycine…) déclinées en rampes 975/950/925/850 et variantes « sun/moon » pour clair/sombre ; thème sombre par jeu de tokens (`#161616` fond, `#cecece` texte, Bleu France → `#8585f6`, Rouge → `#f95c5e`). | Réutiliser des teintes **déjà publiques et justifiées** plutôt qu'en inventer ; reprendre la logique « une valeur claire / une valeur sombre par token ». Les rampes 975/950 (`#f9f6f2`, `#f3ede5`) servent de fonds, pas d'aplats vifs. |
| **Financial Times** | Fond saumon `#fff1e5` (papier historique) qui porte l'identité ; graphiques sur ce fond. Visual Vocabulary : choix du graphique par fonction (écart, classement, évolution, part, spatial…). | La couleur d'identité peut être **la surface** plutôt qu'un accent. Une teinte chaude et désaturée est politiquement muette. |
| **The Economist** | Rouge `#e3120b` utilisé comme **filet et petit rectangle**, jamais en aplat ; marine pour les actions ; séries de graphiques bleu `#006ba2`, cyan `#3ebcd2`, vert `#379a8b`, jaune `#ebb434` ; axe Y à droite. | Exactement notre grammaire : une couleur d'identité en **filet/repère**, pas en fond. Leur palette de séries montre qu'un sarcelle/vert d'eau sert de couleur « donnée neutre » dans la presse économique. |
| **Le Monde / presse française** (Slate, 2014 et 2015) | Débat documenté sur la couleur du FN : marine (L'Express, France TV), violet (Le Figaro), noir (Libération), brun ou marine selon support (Le Monde). | Confirme que **noir, brun, violet et marine ont tous une charge politique** en France. D'où : pas de violet/brun/marine en accent d'interface ; le noir n'est acceptable que parce qu'il est la *structure* (texte, filets), jamais un aplat porteur de sens à côté d'une carte. |
| **Datawrapper**, « party colors » | Recense les codes partisans par pays. | Les teintes « libres » diffèrent selon le pays ; en France il ne reste que les neutres chauds et, avec réserve, le sarcelle. |
| **INSEE** (site et publications) | Mise en page sobre, couleur réservée aux graphiques ; non vérifié en détail dans cette passe. | Pas de reprise directe ; référence d'institution statistique pour le ton, pas pour la palette. |

Sources : DSFR, paquet npm `@gouvfr/dsfr` (https://cdn.jsdelivr.net/npm/@gouvfr/dsfr/dist/core/core.min.css, consulté le 2026-10-07 ; le site systeme-de-design.gouv.fr a renvoyé 403) ; FT Visual Vocabulary https://github.com/Financial-Times/chart-doctor/blob/main/visual-vocabulary/README.md et https://data.europa.eu/apps/data-visualisation-guide/visual-vocabulary ; The Economist (analyse de design tierce) https://www.shadcn.io/design/economist et https://designcompass.org/en/2025/07/02/the-economist/ ; Slate https://www.slate.fr/france/85293/noir-marron-bleu-couleur-front-national-cartes et https://www.slate.fr/story/111151/couleur-front-national-cartes-regionales ; Datawrapper https://www.datawrapper.de/blog/partycolors. Les valeurs FT/Economist proviennent de sources secondaires : à considérer comme indicatives.

## 3. Méthode de calcul

Ratios WCAG 2.x (luminance relative, (L1+0,05)/(L2+0,05)), calculés par script local. Seuils : texte courant 4,5:1, grand texte et éléments graphiques 3:1. Distance aux blocs : ΔE CIE76 en Lab (indicatif : surestime les écarts dans les bleus). Blocs de référence : `_blocs_politiques.py`.

## 4. Propositions de palette

### Palette A — « Papier » (recommandée)

Idée : la couleur entre par **les surfaces**, en neutres chauds (gris galet / café crème DSFR) ; aucune teinte nouvelle n'est porteuse de sens. Bleu France et Rouge Marianne inchangés.

```css
:root {
  /* Surfaces chaudes — fonds de section, en-têtes de module, encadrés « méthode » */
  --papier-50:  #f9f6f2; /* DSFR beige-gris-galet-975 — fond de section */
  --papier-100: #f3ede5; /* DSFR beige-gris-galet-950 — en-tête de module, ligne survolée */
  --papier-200: #eee4d9; /* DSFR beige-gris-galet-925 — sélection de ligne de tableau */
  --sable-700:  #6a6156; /* DSFR beige-gris-galet-sun-407 — métadonnées sur fond papier */

  /* Alias sémantiques */
  --surface-section: var(--papier-50);
  --surface-header:  var(--papier-100);
  --text-meta-warm:  var(--sable-700);
}
```

| Couple | Ratio | Verdict |
|---|---|---|
| encre `#0a0a0a` / `#f9f6f2` | 18,38:1 | AAA |
| encre / `#f3ede5` | 17,02:1 | AAA |
| `--grey-600` `#5c5c5c` / `#f9f6f2` | 6,21:1 | AA |
| `--grey-600` / `#f3ede5` | 5,75:1 | AA |
| `#6a6156` / blanc · / `#f9f6f2` | 6,07:1 · 5,64:1 | AA |
| Bleu France `#000091` / `#f3ede5` | 12,82:1 | AAA |

Règle : **jamais de fond papier sous une carte ou un graphique partisan** (CENT `#f5b800` passe de 1,79:1 sur blanc à 1,66:1 sur papier, DIV de 2,68 à 2,49 ; les deux sont déjà sous 3:1 sur blanc).

### Palette B — « Bleu France étendu »

Idée : utiliser la rampe Bleu France déjà présente dans `tokens.css` (`--blue-50/100/200`) pour les fonds d'état et les en-têtes.

```css
:root {
  --etat-selection-bg: var(--blue-50);  /* #f0f0fe */
  --etat-actif-bg:     var(--blue-100); /* #e3e3fd */
  --etat-actif-trait:  var(--blue-200); /* #cacafb */
  --entete-inverse:    var(--blue-900); /* #00006b, texte blanc */
}
```

| Couple | Ratio |
|---|---|
| encre / `#f0f0fe` | 17,54:1 |
| `#5c5c5c` / `#f0f0fe` | 5,92:1 |
| `#000091` / `#e3e3fd` | 11,83:1 |
| blanc / `#00006b` | 17,32:1 |

Risque : **élevé pour la neutralité**. Le bleu est le code de la droite (DTE `#3b7dd8`) et de l'extrême droite (EXD `#1f3864`) ; un en-tête bleu sur la page Élections ou Législatif crée un écho chromatique avec ces blocs. Acceptable uniquement en **état d'interaction** (sélection, focus, ligne active), ce qui est déjà le rôle du Bleu France. Non recommandé en surface.

### Palette C — « Archipel » (option, données non partisanes)

Idée : une seule teinte d'accent **pour les graphiques non partisans** (Économie, population, participation), reprise du DSFR `green-archipel` ; l'interface reste noir/blanc ou palette A.

```css
:root {
  --archipel-700: #006a6f; /* DSFR green-archipel-sun-391 — série unique, traits, texte d'accent */
  --archipel-800: #00585c; /* survol, texte sur fond clair */
  --archipel-50:  #eef6f6; /* bande de mise en évidence (période, territoire de référence) */
  --dataviz-neutre-1: var(--archipel-700);
  --dataviz-neutre-2: #767676; /* série de comparaison (= --grey-500, 4,54:1) */
}
```

| Couple | Ratio |
|---|---|
| `#006a6f` / blanc (trait ou texte) | 6,38:1 |
| blanc / `#006a6f` (étiquette inversée) | 6,38:1 |
| `#00585c` / blanc | 8,23:1 |
| encre / `#eef6f6` | 18,05:1 |
| `#006a6f` / `#eef6f6` | 5,82:1 |
| `#009099` (DSFR main) / blanc | 3,85:1 — graphique seulement, pas de texte |

Distance aux blocs (ΔE76) : EXG 91, GAU 92, CENT 104, DTE 55, EXD 39, DIV 36. Lecture : distinct des blocs colorés, mais **proche en clarté de DIV et EXD** — ne jamais l'employer dans une vue qui montre aussi des blocs. Risque : association « écologie » (nuances VEC `#00C000`, ECO `#7FB069`) ; la teinte sarcelle (≈ 183°) reste éloignée du vert franc (≈ 120°), mais le risque n'est pas nul.

Hors périmètre de cette option mais à signaler : la choroplèthe population YlOrRd (jaune → rouge) emprunte les teintes CENT et GAU/EXG. Si Mathias veut un jour une cohérence « non partisan = sarcelle », une rampe séquentielle sarcelle pourrait la remplacer ; c'est un changement de palette de données, donc une décision structurante (ADR-0014 dit « palettes data inchangées »).

## 5. Code couleur par module

| | Avantages | Risques |
|---|---|---|
| Une teinte par module (ex. Géographie vert, Élections bleu, Économie orange, Législatif violet) | Repérage rapide, Accueil plus vivant. | **Élections et Législatif affichent des blocs** : toute teinte saturée y entre en collision (bleu = DTE/EXD, rouge/rose = GAU, jaune/orange = CENT/MDM, violet = ancien code FN, vert = écologistes). Une teinte « attribuée » à Élections serait lue comme une couleur politique. Quatre couleurs de plus à maintenir en clair et sombre. |
| Variante faible : neutres chauds différents par module (`#f9f6f2`, `#f4f6fe`…) | Peu risquée. | Différences quasi imperceptibles ; bénéfice faible. |
| **Recommandé** : identité de module par numéro « 01 — » … « 04 — » + pictogramme Material Symbols + en-tête sur `--surface-header` (palette A) identique pour tous | Zéro risque de neutralité, déjà dans la grammaire. | Moins de « couleur » perçue. |

## 6. Mode sombre (tokens)

Principe : **l'interface s'inverse, les données ne s'inversent pas.** Les cartes et graphiques partisans sont posés sur une « plaque » claire (`--paper` fixe) même en sombre, car les couleurs de blocs, validées sur blanc, deviennent illisibles sur fond sombre et les modifier changerait leur sens.

```css
:root[data-theme="dark"] {
  --ink:            #ededed;
  --paper:          #141414;
  --rule:           #ededed;
  --rule-soft:      #3a3a3a;
  --grey-100:       #1f1f1f; /* surfaces enfoncées */
  --grey-600:       #a3a3a3; /* métadonnées */
  --grey-800:       #cecece; /* légendes longues (DSFR text-default sombre) */
  --bleu-france:    #8585f6; /* DSFR blue-france moon-625 */
  --rouge-marianne: #f95c5e; /* DSFR red-marianne moon-625 */
  --papier-50:      #1e1c1a; /* palette A, si retenue */
  --archipel-700:   #34bab5; /* DSFR archipel moon-716, si palette C retenue */
  --plaque-donnees: #ffffff; /* fond FIXE sous cartes et graphiques partisans */
}
```

| Couple (fond `#141414`) | Ratio |
|---|---|
| `#ededed` texte | 15,74:1 |
| `#a3a3a3` métadonnées | 7,30:1 (6,53:1 sur `#1f1f1f`) |
| `#8585f6` action | 5,86:1 ; texte `#141414` sur bouton `#8585f6` : 5,86:1 |
| `#f95c5e` alerte | 5,90:1 |
| `#34bab5` archipel | 7,75:1 |
| **Blocs sur fond sombre** : EXD `#1f3864` 1,59:1 · EXG `#8b0000` 1,84:1 · DTE 4,48:1 · GAU 4,95:1 · n.d. `#5f6368` 3,05:1 | → justifie la plaque claire |

À noter : Streamlit a son propre thème (`.streamlit/config.toml`, `base = "light"`) et les cartes Folium sont en iframe ; un mode sombre complet n'est réaliste que dans la future interface React/MapLibre/Tauri (où `prefers-color-scheme` suit macOS). Coût Streamlit : élevé pour un rendu partiel.

## 7. Hiérarchie typographique et rythme

- **Deux régimes d'espacement** : « éditorial » (Accueil, en-têtes de page : 120–160 px, inchangé) et « analyse » (à l'intérieur d'une page de module : 48 px entre sections, 24 px entre bloc de filtres et métriques). Proposition de tokens : `--gap-section-analyse: var(--space-12)` ; `--gap-section` reste 120 px pour l'éditorial.
- **H1 de module réduit sur les pages d'analyse** : `clamp(40px, 6vw, 88px)` au lieu de 48→120 px ; le display 168 px reste à l'Accueil. Gain ≈ 150 px au-dessus de la ligne de flottaison sur 1440 × 900.
- **Chiffre-clé** : conserver 900 ; ajouter sous chaque métrique une ligne de contexte en 13 px `--grey-600` (déjà fait dans la maquette web : « Total des votants divisé par le total des inscrits ») — à généraliser.
- **Densité des tableaux** : lignes à 36 px en lecture, 44 px seulement si interactives (cible tactile).

## 8. Iconographie et illustrations de données

- **Sparklines** dans les métriques (évolution d'un indicateur sur la série) : trait 1,5 px encre (ou `--archipel-700` si palette C), dernier point marqué d'un carré 4 px, aucune aire colorée. Pour un indicateur électoral par bloc, sparkline **dans la couleur du bloc** (cohérent avec la légende) et jamais d'accent d'interface.
- **Barre de répartition 100 %** des six blocs (8 px de haut, ordre gauche → droite, séparateurs blancs 1 px) sous la métrique « Bloc majoritaire » : apporte de la couleur *signifiante* et rappelle les autres blocs, ce qui évite qu'un seul bloc occupe visuellement l'en-tête.
- **Pictogrammes** : Material Symbols en trait (« outlined »), 20 px, encre ; jamais colorés. Pas d'illustration figurative (personnages, hémicycle stylisé coloré) : risque d'interprétation.
- **Égalité / absence** : le gris n.d. `#5F6368` et la couleur neutre d'égalité de la maquette web restent hors palette d'accent.

## 9. Ce qui ne doit surtout pas changer

1. Les couleurs de blocs et de nuances (`_blocs_politiques.py`) et les palettes de données validées (PuOr évolution, YlOrRd population, n.d., classe zéro, échelle de score 0-100 %).
2. Aucune couleur d'interface **à l'intérieur ou au contact** d'une carte, d'une légende ou d'un graphique partisan (sélection de commune : contour encre 2 px, pas Bleu France).
3. Bleu France = action seule ; Rouge Marianne = alertes seules, en carré + texte, jamais en aplat (proximité GAU/EXG : ΔE 33–37).
4. Pas d'ombre, pas d'arrondi de surface, filets 1 px, Hanken Grotesk 900 en capitales.
5. Ordre gauche → droite des blocs partout ; aucune couleur dérivée pour « mettre en avant » un bloc.
6. Source citée sous chaque visualisation.

## 10. Maquettes décrites

**M1 — Page Élections, palette A.** Bandeau d'en-tête plein cadre `--papier-100` (hauteur ≈ 280 px) contenant eyebrow, H1 « ÉLECTIONS » 88 px, sous-titre ; filets et onglets en encre. Filtres sur fond blanc. Rangée de métriques sur fond blanc, filet encre au-dessus ; sous « Bloc majoritaire », barre de répartition 100 % des six blocs. Carte sur blanc, encadrée d'un filet 1 px encre, légende sur blanc. Encadré « Source / méthode » sur `--papier-50`. Aucune teinte nouvelle ne touche la carte.

**M2 — Page Économie, palette A + C.** Même bandeau papier. Métriques avec sparkline sarcelle `#006a6f` (série 2015-2021), valeur courante en encre 900. Graphique d'évolution HdF : série du territoire en sarcelle 2 px, moyenne France en `#767676` 1,5 px tirets, bande de période `#eef6f6`. Onglet « Économie × Élections » : **bascule sur les couleurs de blocs, sarcelle absent** de la vue.

**M3 — Accueil.** Inchangé en typographie ; les quatre tuiles de module sur `--papier-50` avec numéro « 0X — » en Plex Mono et pictogramme encre ; survol = filet supérieur 3 px Bleu France (état d'interaction, pas identité de module).

**M4 — Mode sombre (React/Tauri).** Fond `#141414`, texte `#ededed`, filets clairs ; la zone carte + légende est une plaque blanche à bords francs (sans arrondi), comme une feuille posée ; graphiques partisans idem.

## 11. Risques de neutralité (synthèse)

| Risque | Gravité | Parade |
|---|---|---|
| Bleu d'interface lu comme « droite » près d'une carte | Moyenne (existe déjà) | Bleu France réservé aux contrôles hors zone carte ; sélection sur carte en encre |
| Rouge d'alerte lu comme « gauche » | Faible | Carré 12 px + libellé, jamais d'aplat ; pas d'alerte dans une légende |
| Accent sarcelle lu comme « écologie » | Faible à moyenne | Jamais dans une vue partisane ; option soumise à Mathias |
| Couleur de module attribuée à Élections/Législatif | Élevée | Ne pas faire de code couleur par module |
| Brun, violet, marine, noir en aplat | Élevée (connotations documentées) | Exclus de toute proposition |
| Mode sombre modifiant les couleurs de blocs | Élevée (change le sens) | Plaque claire fixe sous les données |
| Fond teinté réduisant la lisibilité de CENT/DIV | Moyenne | Cartes et graphiques partisans toujours sur blanc |

## 12. Questions fermées pour Mathias

1. Adopter la palette A « Papier » (fonds de section et en-têtes en neutres chauds DSFR) ? oui / non
2. Adopter la palette C « Archipel » (sarcelle `#006a6f`) comme couleur unique des graphiques non partisans ? oui / non
3. Renoncer au code couleur par module au profit du numéro + pictogramme ? oui / non
4. Mode sombre : le prévoir uniquement pour l'interface React/Tauri (pas Streamlit), avec plaque claire sous les données ? oui / non
5. Introduire un second régime d'espacement « analyse » (48 px entre sections, H1 de module à 88 px max) dans les pages de module ? oui / non
6. Ajouter la barre de répartition 100 % des blocs sous la métrique « Bloc majoritaire » ? oui / non
7. Ouvrir une réflexion (ADR distinct) sur le remplacement de YlOrRd par une rampe non partisane pour la population ? oui / non

Si 1, 2 ou 5 sont acceptés : ADR révisant l'ADR-0014 (ajout de tokens, palettes de blocs inchangées), puis mise à jour de `tokens.css`, `tokens.json`, `custom.css`, `SKILL.md`.

Maintenance sans décision, à engager par le directeur : aligner le §3 de `data-viz-politique/SKILL.md` sur `_blocs_politiques.py`.
