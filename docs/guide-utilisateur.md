# Guide utilisateur — Ministère de l'Info

Ce guide s'adresse à une personne qui utilise l'application sans connaître son
fonctionnement technique. Il décrit chaque page et la façon de lire ce qu'elle affiche.

## Accéder à l'application

- **Installation Mac (OrbStack)** : après le script d'installation, l'application démarre
  toute seule ; ouvrir **http://localhost:8501** dans un navigateur.
- **Depuis les sources** : lancer `uv run streamlit run app.py`, puis ouvrir la même adresse.

La **barre latérale** (à gauche) sert à passer d'une page à l'autre : Accueil,
Géographie, Élections, Législatif, Économie. Sur certaines pages, elle contient aussi des
**paramètres** qui s'appliquent à toute la page.

### Vocabulaire commun

- **Bloc politique** : les résultats et les élus sont regroupés en 6 blocs, selon la
  nomenclature du ministère de l'Intérieur : **EXG** (extrême gauche), **GAU** (gauche),
  **DIV** (divers), **CENT** (centre), **DTE** (droite), **EXD** (extrême droite).
  Les couleurs de ces blocs sont les mêmes sur toutes les pages.
- **Classement « de l'époque »** : un parti est classé dans le bloc qui lui était
  attribué à la date de l'élection. Un même parti peut donc changer de bloc d'une
  élection à l'autre (par exemple LFI : gauche jusqu'en 2024, extrême gauche aux
  municipales 2026, selon les circulaires officielles).
- **HdF** : région Hauts-de-France (Aisne, Nord, Oise, Pas-de-Calais, Somme).

---

## Accueil

Page de départ. Quatre tuiles présentent les modules ; cliquer sur le titre d'une tuile
ouvre la page correspondante. En bas, un encadré repliable « Diagnostic technique »
affiche les versions des logiciels (utile seulement en cas de problème).

---

## Géographie

Carte interactive de France avec la population par territoire. Les paramètres sont
dans la barre latérale.

### Choisir un niveau territorial

Le menu **« Niveau territorial »** propose 6 découpages :

| Niveau | Nombre | Description |
|--------|--------|-------------|
| Régions | 18 | 13 régions métropolitaines + 5 régions d'outre-mer |
| Départements | 101 | 96 en métropole + 5 d'outre-mer (971 à 976) |
| Intercommunalités (EPCI) | ~1 265 | Communautés de communes, d'agglomération, métropoles |
| Arrondissements municipaux | 45 | Paris (20), Lyon (9), Marseille (16) |
| Circonscriptions législatives | 559 | Découpage des élections législatives |
| Communes | ~35 000 | Toutes les communes — **un département doit être choisi** |

### Choisir l'année et comparer

- **« Année de recensement (INSEE) »** : 2013, 2018 ou 2023.
- **« Comparer avec »** (régions, départements, EPCI, communes) : choisir une autre année
  pour afficher l'évolution. Le choix **« Indicateur cartographique »** permet alors de
  colorer la carte selon la population ou selon son évolution.

### Lire la carte

- Carte de population : **jaune clair** = faible population, **rouge foncé** = forte
  population. Carte d'évolution : du rouge (baisse) au vert (hausse).
- La **légende** indique les seuils. **Survoler** un territoire affiche son nom et sa valeur.
- Sous la carte, un **tableau** liste tous les territoires correspondant aux filtres, triés
  par population décroissante. Cliquer sur un en-tête de colonne le trie ; « n.d. » signale
  une donnée non disponible. Le bouton **Télécharger le tableau en CSV** l'exporte.

### Filtres

- **Département** : pour les EPCI, les circonscriptions et les communes (obligatoire
  pour les communes).
- **Région** : pour les départements et les communes.
- **Options avancées → Mode de rendu** : `auto` (défaut), `choropleth`, `contours`.

Les **arrondissements municipaux** et les **circonscriptions** s'affichent en simples
contours : aucune population n'y est associée dans la base.

---

## Élections

Résultats électoraux des **Hauts-de-France** en trois onglets. Chaque onglet a ses
propres sélecteurs, placés au-dessus de la carte.

### Onglet Présidentielles (2002-2022)

- Choisir l'**année**, le **tour**, la **zone** (21e circonscription du Nord — Valenciennes,
  20 communes ; ou Hauts-de-France entière, plus lente à afficher) et le **mode de carte** :
  - **Bloc dominant** : chaque commune prend la couleur du bloc arrivé en tête ;
  - **Score d'un bloc** : choisir un bloc, la carte montre son pourcentage par commune.
- La métrique **Participation** est le taux de la zone : total des votants divisé par le
  total des inscrits (chaque commune pèse selon son nombre d'inscrits).
- **Évolution des blocs sur 25 ans** : graphique par tour, en voix ou en part des
  suffrages exprimés.
- **Détail par commune** puis **Détail par bureau de vote** : choisir une commune dans la
  liste pour voir les résultats de chacun de ses bureaux.

### Onglet Législatives (2002-2024)

- Choisir l'**année**, le **tour** et la **circonscription** (ou « toutes — vue HdF »).
- Vue HdF : carte par circonscription, récapitulatif par bloc, évolution 2002-2024.
- Vue circonscription : carte, résultats par bloc, évolution, détail par nuance, puis
  détail par bureau de vote.
- Pour **2002 et 2007**, un avertissement rappelle que les circonscriptions suivaient
  l'ancien découpage (antérieur à 2010) : les comparaisons avec 2012 et après ne sont pas
  géographiquement valides, et les résultats des communes partagées entre plusieurs
  circonscriptions (Lille, Amiens…) peuvent être attribués à la mauvaise.

### Onglet Municipales (2008-2026)

- Choisir le **scrutin** (année et tour) dans la liste.
- La carte colore chaque commune selon le **bloc dominant**. Les communes **« Non
  classé »** (gris) sont celles dont les listes ne reçoivent pas de nuance politique
  officielle (communes de moins de 3 500 habitants, sauf exceptions).
- Un encadré d'information rappelle les limites propres à chaque scrutin.
- **Détail par commune** : liste nominative des listes candidates et de leurs résultats.

### Limites à connaître

- **Municipales 2008** : le fichier officiel ne contient que 2 communes du Nord (Lille,
  Roubaix, Tourcoing, etc. en sont absentes). Ce n'est pas une erreur de l'application.
- **Pas de clic sur la carte** pour ouvrir le détail : utiliser les listes déroulantes.

---

## Législatif

Composition et activité de l'**Assemblée nationale** et du **Sénat**, pour la France
entière. Les données couvrent les députés depuis 2002 et les sénateurs actuels et
anciens.

### Paramètres (barre latérale)

- **Chambre** : toutes, Assemblée nationale ou Sénat.
- **Département** : « Tous (France) », « Hauts-de-France (région) » ou un département.

Ces deux filtres s'appliquent aux quatre onglets.

### Onglets

| Onglet | Ce qu'il montre |
|--------|-----------------|
| **Composition politique** | Répartition des élus en fonction par bloc (graphique en secteurs ; deux graphiques côte à côte si « toutes » les chambres), avec le nombre d'élus par bloc |
| **Liste des élus** | Tableau des élus en fonction (nom, chambre, département, circonscription, groupe, bloc, profession), avec une recherche par nom |
| **Activité parlementaire** | Assemblée nationale uniquement : classement des 20 premiers députés selon l'indicateur choisi (participation, loyauté au groupe, proximité avec la majorité, participation spécialisée), puis moyennes par bloc |
| **Évolution historique** | Composition de l'Assemblée par législature (12e à 17e) |

### Comprendre les données

- Les **scores d'activité** sont calculés par le site Datan à partir des données de
  l'Assemblée ; il n'existe pas d'équivalent pour le Sénat dans l'application.
- Le **bloc** d'un élu est déduit de son groupe parlementaire. Quelques exceptions sont
  corrigées manuellement (par exemple des sénateurs RN siégeant parmi les non-inscrits).
- **Évolution historique** : chaque député est compté dans sa **dernière** législature ;
  le graphique est donc une approximation pour les députés réélus plusieurs fois.
- Les votes nominatifs (qui a voté quoi) ne sont pas disponibles.

---

## Économie

Indicateurs économiques et sociaux des communes des **Hauts-de-France**, en quatre
onglets.

### Onglet Carte des indicateurs

- Choisir un **indicateur** et une **année** :

| Indicateur | Source | Années |
|------------|--------|--------|
| Taux de pauvreté, niveau de vie médian | INSEE Filosofi | 2017-2021 |
| Taux de chômage (recensement), part ouvriers + employés, part emploi industriel, part logements sociaux | INSEE Recensement | 2015-2021 |
| Allocataires du RSA (nombre de foyers, pas un taux) | CNAF | 2020-2024 |
| Accessibilité aux médecins généralistes (APL) | DREES | 2023 |

- Les communes en **gris** n'ont pas de donnée (secret statistique de l'INSEE pour les
  très petites communes, ou valeur manquante).
- La carte du RSA montre un **nombre** de foyers : les communes les plus peuplées
  ressortent mécaniquement.
- **Détail d'une commune** (encadré repliable sous la carte) : choisir une commune pour
  voir tous ses indicateurs et leur évolution.

### Onglet Évolution HdF

Trois vues au choix :

- **Revenus & emploi (INSEE)** : agrégats régionaux calculés depuis les communes. Le taux
  de chômage est pondéré par le nombre d'actifs (≈ chômeurs / actifs de la région,
  2015-2021) ; le taux de pauvreté est une moyenne simple des communes et le niveau de
  vie une médiane des médianes communales (2017-2021) : ce ne sont pas les valeurs
  régionales officielles de l'INSEE ;
- **Allocataires RSA (CNAF 2020-2024)** ;
- **Contexte HdF vs France (Eurostat)** : taux de chômage au sens du BIT et PIB par
  habitant, région comparée à la France, avec l'écart de la dernière année.

### Onglet Économie × Élections

Nuage de points : chaque point est une commune. Axe horizontal = un indicateur
économique ; axe vertical = le pourcentage des suffrages exprimés d'un bloc au **1er ou
au 2e tour** de la présidentielle choisie. La taille du point dépend du nombre d'actifs
de 15 à 64 ans.

- Les données économiques utilisées sont celles de l'**année précédant l'élection**. Seules
  les présidentielles pour lesquelles ces données existent sont proposées : 2022 pour
  tous les indicateurs, et aussi 2017 pour les indicateurs du recensement (chômage,
  catégories socioprofessionnelles, emploi industriel, logements sociaux).
- Au 2e tour, seuls les blocs des deux finalistes ont des voix.
- **Une corrélation n'est pas une causalité** : le graphique montre une tendance
  territoriale, pas une explication du vote.

### Onglet Désindustrialisation

- **Emploi industriel 2006-2025** : effectifs salariés du secteur privé dans l'industrie
  en Hauts-de-France (source URSSAF). Les bandes grisées signalent la crise de 2008-2010
  et la période 2020-2021.
- **Détail d'une commune** : même courbe pour une commune.
- **Déserts médicaux** : carte des communes où l'accessibilité aux médecins généralistes
  est inférieure à 2,5 consultations par habitant et par an (seuil DREES), en rouge.

---

## Comprendre les sources

| Domaine | Source |
|---------|--------|
| Contours des territoires | IGN — ADMIN-EXPRESS-COG ([data.geopf.fr](https://data.geopf.fr)) |
| Populations | INSEE — populations légales (population municipale) |
| Résultats électoraux | Ministère de l'Intérieur, publiés sur data.gouv.fr |
| Classement politique | Circulaires de nuançage du ministère de l'Intérieur (voir `docs/sources-officielles/nuances/`) |
| Députés | Datan (data.gouv.fr) |
| Sénateurs | Sénat (data.senat.fr) |
| Économie | INSEE (Filosofi, Recensement), CNAF, DREES, URSSAF, Eurostat |

### Codes INSEE vs codes postaux

Le code INSEE d'une commune ≠ son code postal :

| Ville | Code INSEE | Code postal |
|-------|------------|-------------|
| Paris (commune entière) | 75056 | 75001 à 75020 |
| Lyon | 69123 | 69001 à 69009 |
| Marseille | 13055 | 13001 à 13016 |

Les **arrondissements** de Paris ont leurs propres codes : 75101 (1er) → 75120 (20e).

---

## FAQ

**Q : Pourquoi Mayotte n'apparaît pas dans les cartes de population ?**

R : Les populations de Mayotte sont publiées par l'INSEE dans une source différente de
celle chargée. Les contours de Mayotte sont présents, sans population associée.

---

**Q : Pourquoi certains EPCI n'ont pas de département affiché dans le tableau ?**

R : Les 11 Établissements Publics Territoriaux (EPT) du Grand Paris couvrent plusieurs
départements à la fois : il n'est pas possible de leur associer un département unique.

---

**Q : Pourquoi les pages Élections et Économie ne montrent que les Hauts-de-France ?**

R : C'est le périmètre choisi pour ces deux modules. Le module Législatif et la page
Géographie couvrent la France entière.

---

**Q : La carte des communes ou la vue « Hauts-de-France entière » est longue à charger, c'est normal ?**

R : Oui. Plusieurs centaines de contours de communes sont dessinés. Le premier affichage
prend quelques secondes ; les suivants sont plus rapides dans la même session.

---

**Q : Une page affiche « Données non chargées » ou « Base de données absente ».**

R : La base locale ne contient pas encore les données de ce module. La commande à lancer
est affichée sur la page ; en installation Mac, relancer le script de mise à jour ou
réinstaller la base (voir `deploy/README-deploy.md`).

---

**Q : Comment relancer le chargement des données géographiques ?**

R : Arrêter l'application (Ctrl+C dans le terminal), puis :

```bash
uv run python scripts/etl_territoires.py --millesimes 2023 --yes --force
```

Le flag `--force` retélécharge toutes les sources depuis zéro. Pour les autres modules,
voir la section « Obtenir la base de données » du [README](../README.md).
