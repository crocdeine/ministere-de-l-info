# Maquette de l'interface web — Élections, présidentielles, Hauts-de-France

Date : 2026-10-06 · Agent : developpeur-ui · Périmètre : une page web statique (Vite + React +
TypeScript, MapLibre, Observable Plot) alimentée par un export DuckDB en lecture seule.

## Résumé exécutif

- La maquette fonctionne : carte des 3 782 communes, 2 modes, 4 chiffres-clés, évolution 2002-2022, sources et légendes de classement sous chaque visualisation, rendu correct à 1 440 et 390 px.
- Fluidité : changement d'année ou de mode = 15-22 ms jusqu'à l'image suivante (Streamlit : rerun + requêtes 1,2 s + carte Folium 0,7 s + 5,7 Mo de HTML renvoyés au navigateur).
- Chargement initial local : page interactive < 0,25 s (données lues et décodées en 40-70 ms).
- Poids : JS 1,52 Mo (432 Ko gzip) + worker MapLibre 0,51 Mo (145 Ko gzip) ; données 5,2 Mo (géométrie 3,64 Mo, < 5 Mo ; 1,5 Mo gzip au total).
- Branche `poc/interface-web` (2 commits, non poussée). ruff propre, pyright 0 erreur, `tsc --noEmit` strict 0 erreur, `npm run build` sans erreur, pytest 302 réussis (couverture 66,23 % sans base), `npm audit` 0 vulnérabilité.
- Limites principales : pas de tableau par commune ni de détail par bureau de vote, carte non consultable au clavier, export « tout précalculé » qui ne passera pas à l'échelle des bureaux de vote.
- Effort estimé pour porter les 5 pages : 4 à 6 semaines de travail agent, plus la relecture de Mathias.
- Décisions attendues : Q1 modèle de données (fichiers statiques ou moteur embarqué), Q2 règle d'égalité du bloc dominant, Q3 échelle de l'axe des ordonnées, Q4 poursuite vers Tauri.
- Suite proposée : validation visuelle par Mathias (`npm run dev`), puis ADR révisant l'ADR-0002.

## 1. Livrables

| Fichier | Rôle |
|---|---|
| `scripts/export_web.py` | Export lecture seule → `web/public/data/` (4 fichiers) ; agrégations en SQL |
| `tests/test_export_web.py` | Test sur l'échantillon (Somme, 2012/2022) : alignement des codes, somme voix = exprimés, parts ≈ 100 %, sources, légendes, couleurs |
| `web/` | Application Vite + React + TS (`src/App.tsx`, `Carte.tsx`, `Evolution.tsx`, `donnees.ts`, `styles.css`) |
| `web/README.md` | Commandes et architecture |
| `.gitignore` | `web/node_modules/`, `web/dist/`, `web/public/data/` |

Dépendances (justification) :

- `react`, `react-dom` : stack décidée.
- `maplibre-gl` ^6.12 : carte ; la 5.x a une alerte critique (XSS, GHSA-jrc7-96c5-q579), d'où la 6.x.
- `@observablehq/plot` : graphique (stack décidée).
- `@fontsource/hanken-grotesk` et `@fontsource/ibm-plex-mono` : polices embarquées, sous-ensemble latin uniquement (183 Ko) ; elles évitent un appel à Google Fonts (contrainte « aucun réseau hors IGN », hors ligne sous Tauri).
- Dépendances de développement : `vite`, `@vitejs/plugin-react`, `typescript` 5.9 (la 7.x est le portage natif, trop récent), `@types/react*`, `@types/geojson` (types seuls, déjà tirés par MapLibre).

## 2. Ce qui marche

- **En-tête** : sur-titre, repère « 01 — Élections », titre géant en capitales, sous-titre décalé et flèche ↘, conforme au skill.
- **Sélecteurs** : Année, Tour et Mode sous forme de boutons radio natifs présentés en pastilles. Clavier (flèches) et lecteurs d'écran fonctionnent sans code ; cibles de 44 px ; focus Bleu France 2 px, décalé de 3 px. Le sélecteur de bloc (mode score) est un `select` natif.
- **Carte** : géométrie chargée une seule fois, puis recoloration par `feature-state` (aucun rechargement de géométrie). Mode bloc dominant : couleurs `_blocs_politiques.py`. Mode score : dégradé blanc → couleur du bloc, échelle **fixe 0-100 %** annoncée dans la légende. Une donnée absente apparaît en gris `#5F6368` avec la mention « n.d. », jamais 0. L'infobulle (survol ou toucher) donne la commune, le code INSEE, le bloc dominant ou le score, et la participation. Une égalité est signalée.
- **Fond Plan IGN facultatif** : les communes font partie du style initial et s'affichent même si les tuiles IGN échouent (constaté : en mode « temps virtuel » de Chrome, l'événement `load` ne venait jamais ; la première version, qui en dépendait, n'affichait aucune commune).
- **Chiffres-clés** : calculés en SQL à l'export. Participation = Σ votants / Σ inscrits, comme `taux_participation_agrege`. Valeurs 2022 T1 identiques à la page Streamlit : 3 781 communes, 4 252 742 inscrits, 73,1 %, Extrême droite.
- **Évolution** : part des exprimés de la région par bloc, pour le tour sélectionné ; couleurs de trait `couleurs_traits` (CENT assombri). Un bloc sans candidat à un tour donne une ligne interrompue, pas un 0 inventé, et c'est indiqué.
- **Sources** : sous chaque visualisation, producteur, jeu de données et licence (registre `sources.py`), plus la légende `legende_classement_blocs("pres", année)`. Pour 2002-2022, c'est « reconstruction par le projet… ». Fond : « © IGN — Plan IGN ».
- **Neutralité** : libellés de blocs uniquement, aucun nom de candidat ni de parti, aucune donnée personnelle.
- **Responsive** : à 390 px, une colonne, pas de défilement horizontal (`scrollWidth` = 390), titre sur une ligne (9,5vw).

## 3. Mesures

Mesures prises dans Chrome 154 sans interface, piloté par le protocole DevTools, cache désactivé, sur `vite preview` (build de production, local, sans compression).

| Mesure | Valeur |
|---|---|
| Build `web/dist/assets` | JS 1 522 985 o (431 684 gzip) ; worker 510 980 o (144 655 gzip) ; CSS 94 763 o (13 369 gzip) ; polices 183 252 o |
| Données | `communes.geojson` 3 644 028 o (1 089 877 gzip) ; `resultats.json` 1 122 131 o (398 655 gzip) ; `evolution.json` 1 952 o ; `meta.json` 2 783 o |
| Géométrie | `geometry_simplified_communal` + `ST_ReducePrecision(1e-5)` (~1 m) : 4,67 → 3,64 Mo, sans effet visible |
| Export | 11 s (dont ouverture de la base) |
| Chargement initial (1 440 px) | DOMContentLoaded 68 ms ; toutes ressources hors tuiles < 150 ms ; données lues + décodées 41 ms |
| Chargement initial (390 px) | DOMContentLoaded 104 ms ; ressources < 220 ms ; données 68 ms |
| Changement d'année (6 changements successifs) | 15-22 ms du clic à l'image suivante de la carte (`performance.now()`, journalisé en console) |
| Équivalent Streamlit (2022 T1, région) | requêtes 1,24 s + construction Folium et HTML 0,70 s = 5,7 Mo de HTML par rerun (hors cache ; avec cache, ~0,7 s + transfert et analyse de l'iframe) |

Impression qualitative : le changement d'année est instantané, sans clignotement, et la carte garde le zoom et la position. Sous Streamlit, chaque clic relance le script, reconstruit l'iframe Folium et réinitialise le zoom.

## 4. Limites (honnêtes)

1. **Périmètre réduit** par rapport à la page Streamlit : pas de tableau par commune, pas d'export CSV, pas de détail par bureau de vote, pas de zone « 21e circonscription », pas d'unité « voix totales » sur l'évolution.
2. **Accessibilité de la carte** : les valeurs par commune ne sont lisibles qu'au survol ou au toucher. Il faut un tableau ou une recherche de commune pour l'accès au clavier (Streamlit l'a via `st.dataframe`). Le contraste des polygones n'a pas été mesuré (couleurs de blocs inchangées).
3. **Modèle de données** : export intégral précalculé. Il convient aux communes (1,1 Mo pour 10 scrutins). Au niveau des bureaux de vote, il faudrait des fichiers par commune chargés à la demande, ou un moteur embarqué (voir Q1).
4. **Égalités** : 508 couples commune × scrutin ont deux blocs à égalité en tête. La maquette prend le premier bloc dans l'ordre gauche → droite et le signale (infobulle, légende). Streamlit en prend un arbitrairement, sans le dire (voir Q2).
5. **Ordonnées du graphique** : axe partant de 0 et ajusté au maximum (≈ 41 % au 1er tour), comme Plotly sous Streamlit. Ce n'est pas l'échelle fixe 0-100 % décidée pour les cartes (voir Q3).
6. **Mesures** : prises en local, sans compression HTTP. Une seule machine. Aucune mesure sur un Mac ancien ni dans Tauri.
7. Les mesures de temps passent par `console.info` (à retirer en production).
8. `npm install` signale `fsevents` (scripts d'installation non approuvés) : sans effet sur le build.
9. Le test d'export n'est exécuté que si l'extension DuckDB spatial est installée (marqueur `spatial`, comme les autres tests géométriques).

## 5. Comparaison avec la page Streamlit équivalente

| Critère | Streamlit (actuel) | Maquette web |
|---|---|---|
| Réactivité au changement d'année | 1-2 s, rechargement de l'iframe, zoom perdu | ~20 ms, zoom conservé |
| Fidélité au design system | CSS injecté sur les `data-testid`, iframe Folium et canevas `st.dataframe` non stylables | Maîtrise complète (tokens importés tels quels) |
| Fonctionnalités | Complètes (tableau, CSV, bureaux de vote, zones) | Partielles (carte, chiffres, évolution) |
| Coût de développement | Faible, Python seul | Plus élevé : deux langages, un export à maintenir |
| Distribution | Serveur Python requis | Fichiers statiques, compatibles Tauri |
| Accès aux données | Requêtes SQL à la volée | Fichiers précalculés (ou moteur embarqué, à décider) |

## 6. Effort estimé pour porter les autres pages

Estimation en jours de travail agent, hors relecture. Hypothèse : fichiers statiques + chargement à la demande.

| Lot | Contenu | Estimation |
|---|---|---|
| Socle commun | Navigation (5 pages), composants tableau, CSV et légende, tests de bout en bout, CI npm | 3-5 j |
| Élections complètes | Présidentielles (tableau, bureaux de vote), législatives (circonscriptions), municipales | 5-7 j |
| Géographie | 6 niveaux, population, évolutions (palette PuOr) | 2-3 j |
| Économie | 4 onglets, 10 indicateurs, classes fixes, nuage économie × élections | 5-7 j |
| Législatif | Filtres, listes d'élus, activité, historique | 3-5 j |
| Accueil, sources, guide | Tuiles, tableau des sources | 1-2 j |
| Tauri | Empaquetage, signature, mise à jour de la base | 2-4 j |
| **Total** | | **21-33 j (4 à 6 semaines)** |

## 7. Prochaines étapes

1. Validation visuelle par Mathias (`npm run dev`) : `AppTest` et les captures sans interface ne la remplacent pas.
2. ADR « interface web » révisant l'ADR-0002 (stack, modèle de données, publication restreinte).
3. Tauri : prototype d'empaquetage de cette page (fichiers statiques + données dans le paquet ; CSP limitée à `data.geopf.fr`).
4. Publication restreinte : à instruire (hébergement statique protégé ou distribution de l'application seule), décision Mathias.
5. Portage page par page, en commençant par le socle commun.

## 8. Décisions à soumettre (questions fermées)

- **Q1** — Modèle de données de production : (a) fichiers JSON précalculés par l'export Python, chargés à la demande ; ou (b) moteur DuckDB embarqué (WASM, ou processus Python dans Tauri) qui interroge la base à la volée ?
- **Q2** — Égalité de voix entre blocs en tête : (a) premier bloc dans l'ordre gauche → droite, égalité signalée (maquette) ; ou (b) couleur neutre « égalité » distincte ?
- **Q3** — Axe des ordonnées du graphique d'évolution : (a) de 0 au maximum observé (actuel) ; ou (b) échelle fixe 0-100 %, comme les cartes ?
- **Q4** — Suite : (a) poursuivre avec un prototype Tauri de cette page ; ou (b) porter d'abord une deuxième page pour confirmer l'effort ?

## 9. Commandes de vérification

```bash
uv run python scripts/export_web.py
uv run ruff check --output-format concise .          # All checks passed
uvx pyright@1.1.408                                   # 0 errors
PYTHONPATH=src uv run pytest -q                       # 302 passed, 363 skipped, couverture 66,23 %
cd web && npm install && npm run build                # tsc strict 0 erreur, build OK
npm audit                                             # 0 vulnerabilities
```
