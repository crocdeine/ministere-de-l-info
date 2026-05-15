---
name: data-viz-politique
description: Conventions de visualisation des données politiques et électorales françaises. Codes nuances officiels (grille 2026 Ministère de l'Intérieur, NOR INTP2602966C), palette partisane vérifiée, blocs de clivages officiels, pièges INSEE. À charger pour toute carte, graphique, tableau ou rapport portant sur élections, élus, nuances politiques ou indicateurs territoriaux français.
---

# Data-viz politique française

Source de référence : **Circulaire INTP2602966C du 2 février 2026** (Laurent Nuñez, Ministre de l'Intérieur), annexes 1, 2, 3. PDF archivé dans `references/circulaires/2026-02-02_INTP2602966C_nuances-municipales-2026.pdf`.

## 1. Grille des nuances individuelles (Annexe 1 — 26 nuances)

Pour candidats individuels, applicable aux élections municipales, communautaires, métropolitaines (Lyon), d'arrondissement (Paris/Lyon/Marseille), dans les communes ≥3 500 habitants ou chefs-lieux d'arrondissement.

| Code | Libellé officiel | Bloc | Couleur HEX |
|---|---|---|---|
| EXG | Extrême gauche | EXG | `#8B0000` |
| FI | La France insoumise | EXG | `#BB1840` |
| COM | Parti communiste français | GAU | `#DD0000` |
| SOC | Parti socialiste | GAU | `#FF8080` |
| GEN | Génération.s | GAU | `#86C232` |
| PLP | Place Publique | GAU | `#FFB3D1` |
| RDG | Parti radical de gauche | GAU | `#FFD700` |
| VEC | Les Écologistes | GAU | `#00C000` |
| DVG | Divers gauche | GAU | `#F4A6A6` |
| ECO | Écologiste (hors Les Écologistes) | DIV | `#7FB069` |
| REG | Régionalistes | DIV | `#669999` |
| ANM | Animaliste | DIV | `#A8C686` |
| DIV | Divers (inclassables) | DIV | `#888888` |
| REN | Renaissance | CENT | `#FFEB00` |
| MDM | Modem | CENT | `#FF8C00` |
| HOR | Horizons | CENT | `#3399CC` |
| PR | Parti Radical | CENT | `#E8C99B` |
| DVC | Divers centre | CENT | `#FFD9B3` |
| UDI | Union des Démocrates et Indépendants | CENT | `#00BFFF` |
| LR | Les Républicains | DTE | `#0066CC` |
| DVD | Divers droite | DTE | `#7A99CC` |
| DSV | Droite souverainiste (Debout la France, etc.) | DTE | `#1E3A8A` |
| UDR | Union des droites pour la République | EXD | `#2E2E7F` |
| RN | Rassemblement National | EXD | `#0D378A` |
| REC | Reconquête | EXD | `#1A1A6E` |
| EXD | Extrême droite (autres) | EXD | `#101050` |

## 2. Grille des nuances de listes (Annexe 2 — 25 nuances)

| Code | Libellé officiel | Bloc | Couleur HEX |
|---|---|---|---|
| LEXG | Extrême gauche | EXG | `#8B0000` |
| LFI | La France insoumise | EXG | `#BB1840` |
| LCOM | Parti communiste français | GAU | `#DD0000` |
| LSOC | Parti socialiste | GAU | `#FF8080` |
| LVEC | Les Écologistes | GAU | `#00C000` |
| LUG | Union de la gauche | GAU | `#C2185B` |
| LDVG | Divers gauche | GAU | `#F4A6A6` |
| LECO | Écologiste (hors LVEC) | DIV | `#7FB069` |
| LREG | Régionalistes | DIV | `#669999` |
| LDIV | Divers (inclassables) | DIV | `#888888` |
| LREN | Renaissance | CENT | `#FFEB00` |
| LMDM | Modem | CENT | `#FF8C00` |
| LHOR | Horizons | CENT | `#3399CC` |
| LUDI | Union des Démocrates et Indépendants | CENT | `#00BFFF` |
| LUC | Union du centre | CENT | `#FFC107` |
| LDVC | Divers centre | CENT | `#FFD9B3` |
| LLR | Les Républicains | DTE | `#0066CC` |
| LUD | Union de la droite | DTE | `#1976D2` |
| LDVD | Divers droite | DTE | `#7A99CC` |
| LDSV | Droite souverainiste | DTE | `#1E3A8A` |
| LUDR | Union des droites pour la République | EXD | `#2E2E7F` |
| LRN | Rassemblement National | EXD | `#0D378A` |
| LREC | Reconquête | EXD | `#1A1A6E` |
| LUXD | Union de l'extrême droite | EXD | `#0A1858` |
| LEXD | Extrême droite (autres) | EXD | `#101050` |

## 3. Blocs de clivages officiels (Annexe 3)

Pour les agrégations historiques et comparatives, **utiliser les 6 blocs officiels** :

| Code bloc | Libellé | Couleur HEX | Inclut (individuelles) | Inclut (listes) |
|---|---|---|---|---|
| EXG | Extrême gauche | `#8B0000` | EXG, FI | LEXG, LFI |
| GAU | Gauche | `#DD0000` | COM, SOC, GEN, PLP, RDG, VEC, DVG | LCOM, LSOC, LVEC, LUG, LDVG |
| DIV | Divers | `#888888` | ECO, REG, ANM, DIV | LECO, LREG, LDIV |
| CENT | Centre | `#FFEB00` | REN, MDM, HOR, PR, DVC, UDI | LREN, LMDM, LHOR, LUDI, LUC, LDVC |
| DTE | Droite | `#0066CC` | LR, DVD, DSV | LLR, LUD, LDVD, LDSV |
| EXD | Extrême droite | `#0D378A` | UDR, RN, REC, EXD | LUDR, LRN, LREC, LUXD, LEXD |

⚠️ Ne **JAMAIS** inventer un bloc "centre-gauche" ou "centre-droit" — la grille officielle 2026 n'en utilise pas. Si on veut une granularité plus fine, rester au niveau des nuances individuelles.

## 4. Distinction critique : étiquette vs nuance

- **Étiquette politique** : libre choix du candidat (peut être "sans étiquette" ou inexistante)
- **Nuance politique** : attribuée par l'administration (le préfet) selon un faisceau d'indices
- Les deux peuvent différer
- Toutes les viz doivent indiquer **laquelle on affiche**

## 5. Champ d'application 2026

La grille s'applique aux candidats et listes dans :
- Communes ≥ 3 500 habitants
- Communes chefs-lieux d'arrondissement (toute taille)
- Listes des élections métropolitaines de Lyon
- Listes des arrondissements de Paris, Lyon et Marseille

**Pour communes < 3 500 habitants** : pas de nuance attribuée → champ vide ou "NA" dans les datasets.

## 6. Règles de visualisation

### Cartes choroplèthes

- Convertir en `EPSG:4326` avant Folium : `gdf.to_crs(epsg=4326)`
- Simplifier les contours : `gdf.simplify(0.001)` pour national, `0.0005` pour régional
- Légende en bas-droite, titre en haut
- Footer obligatoire : `Source : Ministère de l'Intérieur via data.gouv.fr — MAJ <date>`
- Tooltip avec : nom du territoire, code INSEE, valeur formatée FR (`12 345,67`)

### Graphiques de scores

- Barres horizontales triées par score décroissant
- Couleur = nuance (HEX exact de la table)
- Pourcentages avec virgule décimale française : `52,3 %`
- Tour 1 vs tour 2 : barres groupées, tour 1 clair, tour 2 foncé

### Évolutions temporelles

- Lignes ou bandes empilées **par bloc officiel** (EXG/GAU/DIV/CENT/DTE/EXD)
- X = année, Y = % suffrages exprimés
- Annoter les ruptures : 2002, 2007, 2012, 2017, 2022, 2027

## 7. Accessibilité

- Alternative textuelle pour chaque carte (tableau dépliable)
- Contraste WCAG AA (4.5:1)
- Ne jamais coder uniquement par couleur : ajouter motifs/labels
- Sur fond sombre : augmenter luminosité de 15-20 %

## 8. Citation des sources (obligatoire)

Toute viz doit indiquer :
1. Source primaire : `Ministère de l'Intérieur via data.gouv.fr`
2. Date de mise à jour des données
3. Niveau d'agrégation (bureau de vote, commune, EPCI, département, région)
4. Pour les nuances : `Circulaire INTP2602966C du 2 février 2026`

## 9. Pièges spécifiques

- **PLM** : Paris, Lyon, Marseille votent par **arrondissement** (`75101→75120`, `69381→69389`, `13201→13216`), pas par commune-mère.
- **Communes < 3 500 hab.** : pas de nuance attribuée — exclure ou marquer "NA".
- **Outre-mer** : décalage horaire, dépouillement la veille pour présidentielles.
- **Communes nouvelles** : code INSEE change à la fusion → table de correspondance COG INSEE annuelle.
- **Procurations** : comptées dans la commune de vote, pas de résidence.
- **Fusion de listes au T2** : la nuance peut changer entre tours — réinterroger.
- **Codes nuances historiques** : changent à chaque circulaire (ex: 2022 NUP/ENS → 2026 UDR/LUXD). Pour comparaisons longue durée, agréger au niveau du bloc (EXG/GAU/DIV/CENT/DTE/EXD) et maintenir une table d'harmonisation `data/external/nuances_harmonisation.yaml` mappant `(code, année) → bloc`.

## 10. Sortie d'analyse type

Quand Claude produit une analyse électorale, le format attendu inclut :
- Le scrutin (présidentielle 2022, municipales 2026...)
- Le niveau (national, régional, communal...)
- Les nuances ou blocs en colonne
- Les pourcentages en virgule française avec %
- Le nombre d'inscrits, votants, exprimés
- La source et date
