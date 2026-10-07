# Recherche UX — expérience de la future application (web + Mac)

Date : 2026-10-07 — Rôle : chercheur UX / designer produit (lecture seule) — Décideur : Mathias

**Lu** : `docs/guide-utilisateur.md`, `reports/ux-2026-09-24.md` (non refait, seulement prolongé), `reports/brainstorm-revue-fonctionnalites-2026-10-06.md`, `reports/synthese-brainstorm-fonctionnalites-2026-10-06.md`, `docs/reprise.md`, skill `design-system-mi`, captures `docs/captures/design-v2/` (accueil, élections, législatif), maquette `origin/poc/interface-web` (`web/src/App.tsx`, `Carte.tsx`, `Evolution.tsx`, `styles.css`), code des pages Streamlit (recherche ciblée).
**Méthode** : parcours rejoués sur le code et les captures ; heuristiques de Nielsen, WCAG 2.2 AA / RGAA 4.1 ; benchmark de 6 outils (§ 7). Aucun test avec de vrais utilisateurs : les constats sont des hypothèses à valider (Q8).

## Résumé

1. La base contient désormais les élections **France entière 1999-2026** (vague B), mais l'interface reste organisée **par source et par HdF** : tuiles d'Accueil, sous-titre « Hauts-de-France », zone par défaut « 21e circonscription du Nord ». L'écart entre données et interface est le premier problème d'expérience.
2. Les trois parcours clés demandent entre 8 et 25 manipulations aujourd'hui. Avec **recherche globale → fiche territoire → URL**, ils passent à 2 ou 3 (§ 2).
3. Architecture proposée : **une barre de recherche permanente**, la **fiche territoire comme pivot**, les modules comme « explorateurs » secondaires, un fil d'Ariane géographique, et chaque vue décrite par son URL (§ 3).
4. La maquette web part sur de bonnes bases : pastilles en radios natives, `cooperativeGestures`, « n.d. » jamais à zéro, égalité en blanc. Il lui manque l'essentiel de l'accessibilité cartographique : clic sans sélection persistante, infobulle seulement à la souris, aucune alternative en tableau (§ 4).
5. Les garde-fous de neutralité existent, mais ils sont **écrits pour un développeur** : chemin `docs/adr/0010-….md` dans les légendes (capture élections). Il faut en faire un composant visible « Méthode » relié à la page Méthodologie (§ 5).
6. 24 recommandations priorisées (§ 8), dont 11 relèvent directement de la vague A. 8 questions fermées (§ 9).

---

## 1. Constats nouveaux (en plus des audits du 24/09 et du 06/10)

| # | Constat | Preuve | Gravité |
|---|---|---|---|
| N1 | L'interface annonce « Hauts-de-France uniquement » alors que la base couvre la France entière | Capture accueil (tuile 02) ; `elections_presidentielles.py:44` ; `docs/reprise.md` (base `db-2026-10-07`) | Haute |
| N2 | La légende de méthode cite un chemin de fichier (« Méthode : docs/adr/0010-revision-nuances-et-blocs.md ») | Capture élections | Haute (la garantie de neutralité devient illisible) |
| N3 | Législatif : camemberts avec étiquettes à point décimal (« 33.6% »), « SENAT » sans accent, texte foncé sur le jaune CENT, parts minuscules illisibles (DIV, EXD Sénat) | Capture législatif | Moyenne |
| N4 | Un bouton « Deploy » de Streamlit est visible en haut à droite | 3 captures | Faible (confusion, propre à Streamlit) |
| N5 | Le titre d'Accueil occupe l'écran entier à 1 280 px : la première action utile (les modules) n'apparaît qu'après défilement | Capture accueil | Moyenne |
| N6 | Maquette web : l'infobulle (`role="status"`) suit la souris ; le clic réutilise le survol au lieu de sélectionner ; le clavier n'atteint aucune commune | `Carte.tsx` (`m.on("click", …, montrer)`) | Haute pour l'accessibilité |
| N7 | Maquette web : un `aria-label` unique sur la carte, et aucun tableau équivalent | `Carte.tsx`, `App.tsx` | Haute (WCAG 1.1.1, 1.4.1) |
| N8 | Toutes les cartes Streamlit ont `returned_objects=[]` : il n'y a aucun geste de la carte vers le détail | `pages/1_📍_Géographie.py:189`, `elections_*.py`, `economie.py:340` | Moyenne (corrigé de fait par la cible web) |
| N9 | Aucune recherche par **code postal** : la base n'en contient aucun, et les utilisateurs non techniques ne connaissent pas les codes INSEE | `information_schema` sans colonne postale | Moyenne |

---

## 2. Parcours clés : avant / après

### P-A « Comment a voté ma commune depuis 2002 ? »

| | Aujourd'hui (Streamlit) | Cible (app web) |
|---|---|---|
| Entrée | Accueil → Élections. L'utilisateur hors HdF apprend la limite trop tard (N1) | Champ de recherche en tête de chaque écran : « Denain » ou « 59220 » |
| Étapes | Présidentielles : zone HdF (lent) → liste « bureau de vote » → 1 année et 1 tour à la fois (×10) → Législatives : connaître sa circonscription → Municipales : ressaisir la commune (perdue au changement de scrutin) | 1. Taper, choisir dans les suggestions (« Denain — Nord, 59 ») → 2. **Fiche commune**, section « Historique électoral » : un graphique de tous les scrutins (blocs + participation), un filtre de type de scrutin, les ruptures annotées |
| Manipulations | ~20-25 | 2 |
| Frictions supprimées | Ressaisies, zone « Circo 21 » par défaut, évolution limitée à la zone, aucun nom de candidat | — |
| Garde-fou visible | Légende de bas de carte avec chemin ADR | Repères sur le graphique : « changement de grille de blocs », « seuil de nuançage », « nouveau découpage 2010 », avec un lien « Méthode » |

### P-B « Comparer deux élections »

| | Aujourd'hui | Cible |
|---|---|---|
| Possible ? | Non. On peut seulement alterner les années et mémoriser les résultats | Oui, de deux façons |
| Étapes cible | — | (a) **Sur la fiche** : « Comparer avec… » → choix d'un 2e scrutin → tableau des écarts en points par bloc, plus participation. (b) **Dans l'explorateur Élections** : mode « Écart entre deux scrutins » → carte divergente PuOr en points, échelle fixe symétrique (±30 pts) |
| Règle d'interface | — | Si les deux scrutins ne sont pas de même nature ou de même découpage, un **bandeau « Comparaison limitée »** (rouge Marianne, motif « Limite » du design system) dit pourquoi. La comparaison n'est pas bloquée (garde-fou n° 2) |
| URL | — | `/elections/ecart?a=2017_pres_t1&b=2022_pres_t1&bloc=EXD&zone=dep-59` |

### P-C « Qui est mon député et comment a-t-il été élu ? »

| | Aujourd'hui | Cible |
|---|---|---|
| Étapes | Législatif → filtre département (barre latérale) → Liste des élus → recherche du nom (il faut le connaître) → fiche cachée dans l'onglet « Activité » ; résultats de l'élection dans un autre module (Élections → Législatives → circonscription, si elle est en HdF) | Recherche « ma commune » → fiche commune, encart **« Représentée par »** : député (circonscription, groupe, bloc de la législature), sénateurs du département → clic → **fiche élu** : mandat, groupe, et **« Son élection »** (résultat T1/T2 de la circonscription, candidats nommés par voix décroissantes, participation, lien vers la fiche circonscription) |
| Manipulations | ~8-12, avec rupture de module | 2-3 |
| Cas délicats à rendre visibles | Commune partagée entre plusieurs circonscriptions (Lille, Amiens) : il faut choisir le bon député | Encart « Cette commune est répartie sur N circonscriptions » listant chacune, sans en choisir une |
| Garde-fou | Top 20 nominatif Datan (décision 8 : à remplacer) | Scores Datan en distribution avec repère de l'élu, et libellé « indicateur Datan » relié à sa méthode |

---

## 3. Architecture de l'information et navigation (app web / Tauri)

### 3.1 Arborescence proposée

```
Accueil (recherche + 4 entrées + nouveautés des données)
├── Territoire  /t/{type}/{code}        ← PIVOT
│     commune · circonscription · département · région · (EPCI plus tard)
│     sections ancrées : Résumé · Élections · Élus · Économie · Population · Sources
├── Élu         /elu/{id}               (député, sénateur)
├── Explorer
│     Élections  /elections/{scrutin}?zone=…&mode=…
│     Parlement  /parlement/{chambre}
│     Économie   /economie/{indicateur}/{annee}
│     Population /population/{niveau}/{annee}
└── Méthodologie /methode/{sujet}  + Glossaire /glossaire#{terme}
```

Principe : **on entre par un lieu ou une personne** (80 % des usages, d'après les profils P1 à P4 de l'audit du 24/09), et **on explore par un thème** (journalistes, chercheurs). Les modules actuels deviennent les explorateurs ; ils ne disparaissent pas.

### 3.2 Règles de navigation

1. **Recherche globale permanente** dans l'en-tête, raccourci `⌘K` / `/`. Elle cherche commune (nom, code postal, code INSEE), circonscription (« Nord 21 », « 59-21 »), département, élu. Suggestions groupées par type, avec le département pour lever les homonymes (« Saint-Martin — Gers, 32 »), et la population en tri secondaire. Elle fonctionne hors ligne (index local, cible Tauri).
2. **Fil d'Ariane géographique** sur la fiche : `France › Hauts-de-France › Nord › 21e circonscription › Denain`. Chaque niveau est cliquable : c'est la comparaison verticale la plus simple.
3. **Le territoire courant suit l'utilisateur** : passer de la fiche à l'explorateur Élections ouvre la carte zoomée sur ce territoire, avec la commune surlignée.
4. **URL = état complet** (territoire, scrutin, tour, mode, bloc, onglet, zoom arrondi). Un bouton « Copier le lien » affiche une confirmation (§ 6). Dans Tauri, gérer un schéma `ministere://…` ou des liens `https://` ouvrant l'app : à trancher (Q4).
5. **Onglets = sections ancrées** sur la fiche (défilement continu et sommaire collant), plutôt que de vrais onglets qui cachent l'information. Les vrais onglets restent réservés aux explorateurs.
6. **Retour arrière fiable** : chaque changement de filtre significatif crée une entrée d'historique (`pushState`), le zoom et le survol non (`replaceState`).
7. **Accueil** : la recherche est au-dessus de la ligne de flottaison. Le titre « display » est réduit à environ 50 % de sa taille actuelle (N5). Ensuite : 4 entrées, puis 3 à 5 « questions fréquentes » préréglées (A2 de la revue, formulées par blocs et sans présupposé), puis les sources avec leur date.

### 3.3 Fiche territoire (gabarit)

| Ordre | Bloc | Contenu | Données |
|---|---|---|---|
| 1 | En-tête | Nom, type, codes (INSEE, département), fil d'Ariane, « Copier le lien », « Exporter » | En base |
| 2 | Chiffres-clés | Population (millésime), inscrits du dernier scrutin, participation, bloc en tête au dernier scrutin **avec son nom de scrutin** | En base |
| 3 | Historique électoral | Graphique multi-scrutins + tableau équivalent repliable ; filtre de type de scrutin ; repères de rupture | En base |
| 4 | Représentée par | Député(s), sénateurs, maire (plus tard, RNE) | En base (sauf RNE) |
| 5 | Économie | Indicateurs avec rang et écart au département et à la région (C1) | En base (HdF) |
| 6 | Comparer | « Comparer avec… » un autre territoire ou le niveau supérieur | En base |
| 7 | Sources et méthode | Sources, licences, dates ; liens Méthodologie | `sources.py` |

Chaque bloc sans donnée affiche un **état vide explicite** (§ 4.4), au lieu de disparaître. L'utilisateur doit savoir que la donnée n'existe pas, et non croire qu'il l'a manquée.

---

## 4. Lecture des cartes et graphiques

### 4.1 Légendes
- La légende est **toujours visible à côté de la carte**, jamais dans la carte (la maquette le fait déjà ; le Folium actuel la superpose).
- La **légende sert aussi de filtre** : cliquer « EXD » sur une carte « bloc dominant » atténue les autres blocs (opacité 0,25), et un second clic rétablit. Les éléments sont de vrais boutons (`aria-pressed`).
- Les effectifs figurent dans la légende : « Extrême droite — 612 communes ». La légende devient un résumé chiffré, ce qui sert aussi d'alternative textuelle.
- Pour les étiquettes de nuance : un carré de couleur **et** le code, jamais la couleur seule (WCAG 1.4.1 ; contrastes EXD/DTE 2,8:1 et EXG/GAU 2,7:1, audit du 24/09).

### 4.2 Infobulles
- Contenu : nom, département, **valeur affichée avec sa base de calcul** (« 41,2 % des exprimés »), rang facultatif, et une ligne « n.d. : raison » si la valeur manque. Dernière ligne : « Ouvrir la fiche ↘ ».
- Survol = aperçu ; **clic = sélection persistante** (contour encre 2 px, panneau latéral). L'URL est mise à jour (`?sel=59178`). La touche Échap désélectionne.
- Au clavier, l'infobulle est **ancrée au territoire sélectionné** et non à la souris. Elle ne doit pas masquer l'élément survolé (WCAG 1.4.13 : rejetable, survolable, persistante).

### 4.3 Sélection, zoom, clavier, lecteur d'écran
- **Alternative structurée obligatoire** : sous chaque carte, un bouton « Afficher en tableau » ouvre le tableau trié des territoires affichés (mêmes couleurs dans une colonne). C'est la vraie voie d'accès clavier et lecteur d'écran. Garder la carte MapLibre `aria-hidden` ou très sobre, et ne pas chercher à rendre 35 000 polygones navigables.
- **Phrase de synthèse calculée** au-dessus de la carte, lue par les lecteurs d'écran : « 2022, 1er tour : l'extrême droite arrive en tête dans 612 des 3 789 communes affichées ; 14 communes n.d. ». Le ton est factuel, sans qualificatif (garde-fou n° 6).
- Zoom : `cooperativeGestures` (déjà présent) ; bouton « Recentrer » ; zoom automatique sur le territoire choisi par la recherche ; zoom borné à la zone.
- Raccourcis : `+`/`−`, flèches pour déplacer, `/` pour chercher. Ils sont documentés dans un panneau « Raccourcis » (`?`).
- Focus visible : `outline 2px #000091` (déjà dans `styles.css`), vérifié aussi sur les contrôles MapLibre.

### 4.4 États vides et « n.d. »
Trois états distincts, avec trois libellés :

| État | Affichage | Exemple |
|---|---|---|
| **n.d.** : donnée inexistante ou secret statistique | Gris `#5F6368`, hachuré si possible (pour ne pas dépendre de la couleur seule) ; infobulle : « n.d. — secret statistique INSEE » | Filosofi, petite commune |
| **Non classé** : la donnée existe mais n'est pas classable | Gris clair, distinct de n.d. | Municipales < 3 500 hab. |
| **Hors périmètre** : la donnée n'est pas chargée pour ce territoire | Pas de couleur, contour seul ; bandeau « Économie : Hauts-de-France uniquement pour l'instant » | Économie hors HdF |

Ne jamais afficher une section vide sans phrase. Ne jamais tracer de ligne continue à travers une rupture : la ligne s'interrompt, comme la maquette le fait déjà pour un bloc absent.

### 4.5 Comparaison et graphiques
- Évolution multi-scrutins : axe horizontal **temporel** (dates réelles), et non catégoriel, pour ne pas suggérer un rythme régulier. Une ligne par bloc avec étiquette directe en fin de ligne (moins d'aller-retour vers la légende).
- **Remplacer les camemberts de composition** (N3) par un **hémicycle** ou une barre empilée horizontale ordonnée EXG → EXD, avec les effectifs en chiffres (format français « 33,6 % »).
- Les petites parts sont étiquetées hors du graphique ; aucun texte sur le jaune CENT sans contraste vérifié.

---

## 5. Premier usage et pédagogie

1. **Aucun tutoriel bloquant.** Au premier lancement, un bandeau discret (rejetable, mémorisé) : « Commencez par chercher une commune, une circonscription ou un élu. » et 3 exemples cliquables.
2. **Aide contextuelle en ligne** : chaque terme de jargon (bloc, nuance, exprimés, n.d., APL, BIT, Filosofi, non-inscrit, « loyauté » Datan) est souligné en pointillé. Un clic ouvre une définition de 2 lignes et un lien vers le glossaire. On clique, on ne survole pas : le geste fonctionne au tactile et au clavier (motif « infobulle cliquable » du DSFR).
3. **Composant « Méthode »**, unique et réutilisé partout (remplace N2) : sous chaque visualisation, sur une ligne, `MÉTHODE — Classement reconstruit (grille 2020 la plus proche). En savoir plus ↘`. Le lien ouvre un **panneau latéral** Méthodologie sans quitter la vue. Trois niveaux de badge :
   - `GRILLE OFFICIELLE` (municipales 2020, 2026) ;
   - `RECONSTRUIT` (autres scrutins, ADR-0010) ;
   - `ESTIMATION` (réservé ; toute estimation doit s'afficher comme telle, garde-fou n° 3).
4. **Garde-fous rendus visibles** :
   - le bandeau « Comparaison limitée » (§ 2 P-B) ;
   - la mention « Corrélation ≠ causalité — N communes » intégrée **au titre** du nuage de points, et non en note ;
   - un registre lexical vérifié : aucun « bastion », « fief », « percée », « gagné », mais « en tête », « part des exprimés ».
5. **Page Méthodologie** organisée par question (« Comment les partis sont-ils classés en blocs ? », « Pourquoi certaines communes sont-elles grises ? », « Que vaut un score Datan ? »), et non par ADR. Chaque réponse cite la circulaire archivée (`docs/sources-officielles/`) sous une forme ouvrable : un lien vers le PDF embarqué.
6. **Date de fraîcheur** près de chaque chiffre-clé (« Population 2023 ; données chargées le 07/10/2026 »).

---

## 6. Micro-interactions et retours

| Situation | Comportement recommandé | Repère |
|---|---|---|
| Chargement initial (données, index) | Squelettes à la forme finale (chiffres-clés, rectangle de carte), pas de toupie seule ; message après 2 s : « Chargement des contours des communes… » | La maquette affiche « Chargement des données… » sur une page vide |
| Changement de filtre | La carte garde l'ancien état ; recoloration < 100 ms (la maquette le mesure déjà) ; pas d'écran blanc | `Carte.tsx` (`setFeatureState`) |
| Recherche | Suggestions dès 2 caractères, < 50 ms (index local) ; « Aucun résultat pour “xyz”. Vérifier l'orthographe ou essayer un code postal. » | — |
| Copier le lien / exporter | Toast non bloquant 3 s, `role="status"` : « Lien copié » / « CSV enregistré dans Téléchargements (Denain_historique_2002-2026.csv) » | Le nom de fichier contient le territoire et la période |
| Erreur de données | Message utilisateur d'abord (« Ces données ne sont pas disponibles dans votre version. Mettre à jour la base. »), puis détails techniques repliés ; jamais de trace Python | Audit T6 du 24/09 |
| Hors ligne (Tauri) | Le fond IGN manque : bandeau discret « Fond de carte indisponible hors connexion », les données restent affichées | Déjà prévu dans `Carte.tsx` |
| Animation | 140-360 ms, `prefers-reduced-motion` respecté ; pas d'animation sur les données (une carte qui « pousse » suggère une dynamique) | Design system § 4 |
| Confirmation | Aucune action destructrice dans l'app : pas de dialogue de confirmation nécessaire. La mise à jour de la base affiche la taille et la durée estimées avant de commencer | — |

---

## 7. Benchmark

| Outil | Ce qu'on copie | Ce qu'on évite | Source |
|---|---|---|---|
| **Datan** | Recherche unique « nom, commune/code postal » qui mène au député ; fiche député dense avec groupe et circonscription ; méthode des scores publiée | Classements et palmarès nominatifs (contraire à la décision 8) ; ton éditorial (blog, « décryptés ») | [datan.fr](https://datan.fr/), [législatives 2024](https://datan.fr/elections/legislatives-2024) |
| **Observatoire des territoires (ANCT)** | « Portraits de territoires » : chiffres-clés comparables d'un territoire donné ; « Visiothèque » pour réutiliser cartes et graphiques ailleurs (export avec source) | Multiplication des portails et applications thématiques sans point d'entrée unique | [observatoire-des-territoires.gouv.fr](https://www.observatoire-des-territoires.gouv.fr/) |
| **geo.api.gouv.fr** | Recherche de commune par nom **ou code postal**, avec la population pour classer les homonymes : modèle de l'index local | Dépendance en ligne (l'app Tauri doit fonctionner hors connexion) : embarquer l'index | [geo.api.gouv.fr/decoupage-administratif](https://geo.api.gouv.fr/decoupage-administratif) |
| **DSFR** | Composants « Fil d'Ariane », « Barre de recherche », « Infobulle » (aide contextuelle), « Alerte », « Tableau » : comportements et accessibilité déjà éprouvés (RGAA). On reprend le **comportement**, pas l'habillage (le design system v2 reste la référence visuelle) | Son apparence institutionnelle : elle ferait passer l'outil pour un site de l'État (ADR-0013 et risque d'usurpation) | [systeme-de-design.gouv.fr — composants](https://www.systeme-de-design.gouv.fr/version-courante/fr/composants) |
| **Résultats du ministère de l'Intérieur / LCP** | Hiérarchie stable région → département → commune, et accès « qui est élu dans ma circonscription » par carte et recherche | Pages sans historique ni comparaison ; accessibilité déclarée « partiellement conforme » | [resultats-elections.interieur.gouv.fr](https://www.resultats-elections.interieur.gouv.fr/), [LCP, carte 2024](https://lcp.fr/actualites/legislatives-2024-qui-a-ete-elu-depute-dans-votre-circonscription-consultez-notre-carte) |
| **Carte interactive des résultats (réutilisation data.gouv, RShiny)** | Bascule candidats ↔ nuances sur une même carte ; communes et circonscriptions superposées | Interface outil de recherche sans pédagogie ni méthode visible ; périmètre 2022+ seulement | [data.gouv.fr — réutilisation](https://www.data.gouv.fr/reuses/carte-interactive-des-resultats-des-elections) |
| **Pages résultats du Monde, de Libération, de franceinfo** | Page par commune avec URL lisible ; résultat par **candidat** d'abord, puis contexte ; chiffre en très grand (rejoint le principe n° 1 du design system) | Qualificatifs éditoriaux (« bastion », « raz-de-marée »), couleurs partisanes maison | **Non vérifié en ligne** : accès automatique refusé par ces sites le 2026-10-07 ; observation générale à confirmer à la main (Q8) |

---

## 8. Recommandations priorisées

Effort : S ≤ 1 jour, M ≤ 1 semaine, L > 1 semaine. Vague : lien avec la feuille de route (A = socle, C = analyses). Les recommandations P1 conditionnent l'architecture : il faut les poser dès la maquette.

| # | Recommandation | Prio | Effort | Vague | Décision Mathias ? |
|---|---|---|---|---|---|
| R1 | Recherche globale en en-tête (commune, code postal, circonscription, élu ; `⌘K`), index local | P1 | M | A (T3) | Code postal = nouvelle source (Q2) |
| R2 | Fiche territoire selon le gabarit § 3.3 (commune d'abord, puis circonscription) | P1 | L | A (T2) | Non (déjà décidée) |
| R3 | URL = état complet ; « Copier le lien » + toast | P1 | M | A (T1) | Schéma Tauri (Q4) |
| R4 | Fil d'Ariane géographique cliquable | P1 | S | A | Non |
| R5 | Composant « Méthode » unique + badges GRILLE OFFICIELLE / RECONSTRUIT ; supprimer les chemins `docs/adr/` affichés | P1 | S | A (T4) | Libellés des badges (Q5) |
| R6 | Page Méthodologie par questions + glossaire + termes cliquables | P1 | M | A (T4) | Non |
| R7 | Tableau équivalent sous chaque carte + phrase de synthèse calculée | P1 | M | A | Non (accessibilité) |
| R8 | Clic carte = sélection persistante dans l'URL ; infobulle conforme WCAG 1.4.13 | P1 | M | A | Non |
| R9 | Mettre l'interface en cohérence avec la base France entière (tuiles, sous-titres, zone par défaut) ; bandeau « hors périmètre » pour Économie | P1 | S | A/B | Zone par défaut (Q3) |
| R10 | Export CSV et image partout, nom de fichier explicite, source + licence + date intégrées | P1 | M | A (T5) | Non |
| R11 | Trois états vides distincts (n.d. / non classé / hors périmètre), avec hachures pour n.d. | P1 | S | A | Non |
| R12 | Historique électoral multi-scrutins avec repères de rupture | P1 | M | A (E1) | Non |
| R13 | Encart « Représentée par » + fiche élu « Son élection » (candidats nommés) | P2 | M | A→C | Ordre des candidats (Q6) |
| R14 | Comparaison de deux scrutins (fiche + carte d'écart) avec bandeau « Comparaison limitée » | P2 | M | C (E5, T7) | Échelle fixe ±30 pts (Q7) |
| R15 | Légende-filtre interactive avec effectifs | P2 | S | A | Non |
| R16 | Remplacer les camemberts par hémicycle ou barres ; format français des pourcentages | P2 | S | A | Non |
| R17 | Accueil : recherche au-dessus de la ligne de flottaison, titre display réduit, questions préréglées | P2 | S | A (A2) | Liste des questions (Q1) |
| R18 | Squelettes de chargement, messages d'erreur à deux niveaux | P2 | S | A | Non |
| R19 | Panneau des raccourcis clavier (`?`) | P3 | S | A | Non |
| R20 | Bandeau de premier lancement rejetable | P3 | S | A | Non |
| R21 | Sections ancrées et sommaire collant sur la fiche (pas d'onglets) | P2 | S | A | Non |
| R22 | En attendant la bascule : masquer « Deploy » dans Streamlit (`client.toolbarMode = "viewer"`) et corriger N3 | P3 | S | — | Non (maintenance) |
| R23 | Audit RGAA outillé (axe-core + lecteur d'écran VoiceOver) à chaque jalon de la maquette | P2 | S/jalon | A | Non |
| R24 | 5 tests utilisateurs de 30 min (1 citoyen, 2 journalistes, 1 élu, 1 chercheur) sur les 3 parcours, avec la maquette fiche | P1 | M | A | Oui (Q8) |

Ordre conseillé : **R9, R5, R22** (rapides, sur l'existant) → maquette web : **R3 + R1 + R4** (squelette de navigation) → **R2 + R12 + R7 + R8 + R11** (fiche commune) → **R24** (tests) → R6, R10, R13, puis le reste.

---

## 9. Questions fermées pour Mathias

| # | Question | Recommandation |
|---|---|---|
| Q1 | L'Accueil propose 3 à 5 « questions fréquentes » préréglées (formulées par blocs, sans présupposé) : oui / non ? | Oui, liste soumise avant publication |
| Q2 | Ajouter la base officielle des codes postaux (La Poste, data.gouv, Licence Ouverte) pour la recherche : oui / non ? | Oui (source autorisée, sans enjeu de neutralité) |
| Q3 | Zone par défaut de l'explorateur Élections : France (départements) / dernier territoire consulté / HdF ? | Dernier territoire consulté, sinon France par départements |
| Q4 | Liens partageables de l'app Mac : URL `https://` hébergée (vue publique) / schéma local `ministere://` seulement ? | Schéma local d'abord ; l'hébergement relève d'une décision séparée |
| Q5 | Badges de méthode « GRILLE OFFICIELLE » / « RECONSTRUIT » affichés sur chaque visualisation : oui / non ? | Oui |
| Q6 | Ordre des candidats dans « Son élection » : voix décroissantes / ordre des panneaux ? | Voix décroissantes (cohérent avec le ministère) |
| Q7 | Carte d'écart entre deux scrutins : échelle fixe symétrique ±30 points / ajustée aux données ? | Fixe ±30 pts (même logique que l'échelle 0-100 %) |
| Q8 | Organiser 5 tests utilisateurs sur la maquette de la fiche commune avant d'aller plus loin : oui / non ? Si oui, Mathias fournit-il les contacts ? | Oui |
