# 0005 — Nomenclature officielle des blocs politiques du Ministère de l'Intérieur

Date : 2026-05-29
Statut : Accepté

## Contexte

Le module Élections doit classer chaque candidat et chaque nuance par bloc politique
pour produire des visualisations comparables sur 25 ans (2002–2026). Ce classement
exige une règle stable, objectivable et vérifiable par un tiers.

La conception initiale (C2a) utilisait 7 blocs "maison" (dont un bloc "écologistes"
absent de toute classification officielle) et un classement au jugement sans traçabilité
explicite. Cela introduit une subjectivité non documentée, difficilement défendable.

## Décision

1. **Blocs officiels** : adopter exactement les 6 blocs de clivages du Ministère de
   l'Intérieur tels que définis dans la circulaire IOMA2322276J (sénatoriales 2023),
   qui est la première à formaliser ce regroupement.

   | Code | Libellé | Ordre |
   |------|---------|-------|
   | EXG | Extrême gauche | 1 |
   | GAU | Gauche | 2 |
   | DIV | Divers | 3 |
   | CENT | Centre | 4 |
   | DTE | Droite | 5 |
   | EXD | Extrême droite | 6 |

2. **Double couche** : la nuance officielle (attribuée par les préfets) est le socle
   factuel. Le bloc est la couche d'agrégation, dérivée de la nuance.

3. **Classement "officiel de l'époque"** : un parti est classé dans le bloc qui lui
   était attribué à la date du scrutin. La grille de classification évolue d'une
   circulaire à l'autre ; on n'applique jamais une grille rétroactivement.
   Exemple : LFI classé GAU en 2017, 2022 (circulaire 2023 confirme GAU) ; classé
   EXG seulement à partir de 2026 (circulaire INTP2602966C).

4. **Reconstruction sourcée avant 2023** : le regroupement officiel en blocs n'existe
   qu'à partir des sénatoriales 2023. Pour les scrutins antérieurs (présidentielles
   2002/2007/2012), le bloc est reconstruit en appliquant la logique des circulaires
   disponibles, avec une justification explicite par candidat (colonne `source_bloc`).

5. **Traçabilité** : les circulaires PDF sont archivées dans
   `docs/sources-officielles/nuances/`. Chaque entrée dans `candidats_presidentielle`
   et `nuances_harmonisees` porte une référence à la circulaire ou décision CE
   utilisée comme source.

## Alternatives considérées

| Alternative | Raison d'écarter |
|-------------|-----------------|
| **Blocs "maison" (C2a)** | Subjectifs, non reproductibles, absence de source vérifiable. Le bloc "écologistes" n'existe dans aucune classification officielle. |
| **Classement académique CEVIPOF** | Riche en nuance mais sans série homogène de 2002 à 2026. Chaque étude utilise sa propre grille. Non compatible avec un pipeline automatisé. |
| **Application rétroactive de la grille 2026** | Anachronique : classer Mélenchon 2012 en EXG parce que LFI est EXG en 2026 est une erreur d'interprétation historique. |
| **Pas de classement par bloc** | Empêche les agrégations et comparaisons temporelles qui constituent la valeur centrale du module. |

## Conséquences

**Positives :**
- Objectivité maximale : tout classement est justifiable par un texte officiel.
- Traçabilité : la source de chaque classement est conservée dans la base.
- Maintenabilité : un nouveau scrutin = une nouvelle circulaire = mise à jour de la table
  de référence sans modifier le code métier.

**À accepter :**
- On hérite des choix de l'État, parfois contestés (cf. contentieux CE sur RN et DLF).
  Ces contentieux sont eux-mêmes documentés et font partie de la traçabilité.
- Les classements changent dans le temps (FI : GAU → EXG) ; c'est une donnée historique,
  non un bug. La clé `(nuance, annee)` dans `nuances_harmonisees` en est la conséquence.
- La grille officielle exclut un bloc "écologistes" distinct : EELV/Verts sont classés
  GAU (allié de gauche historique) et Cap21/Génération Écologie en CENT ou DIV selon
  la circulaire de référence.

## Application aux législatives 2002-2024

Cette section documente l'application concrète de la décision aux scrutins législatifs
(Phase D1.2, validée le 2026-06-01).

- **111 nuances classées** sur 6 scrutins : 2002 (22), 2007 (17), 2012 (17), 2017 (17),
  2022 (16), 2024 (22). Détail ligne par ligne et justifications :
  `reports/mapping-nuances-legislatives-validated.md`. Stockage : table
  `nuances_harmonisees`, clé `(nuance, annee)`, colonne `source_bloc`.

- **Sources** :
  - 2022 → circulaire **INTA2212053C** (avr. 2022) — liste les nuances, **sans** grille de blocs.
  - 2024 → circulaire **IOMA2415630C** (juin 2024) — crée la nuance **UG** (Union de la gauche)
    et confirme que **FI est une nuance distincte d'EXG** ; ne contient pas de grille de blocs.
  - 2002-2017 → les circulaires de nuançage **ne sont pas publiées au JO** (documents internes
    non archivables) ; le classement est **reconstruit** selon la logique officielle datée
    (cf. décision n° 3 ci-dessus) et reste révisable.

- **Cohérence interne (règle LFI)** : **FG 2012**, **FI 2017**, **NUP 2022**, **FI 2024** et
  **UG 2024** sont tous classés **GAU**. La bascule de LFI vers **EXG** n'est introduite qu'à
  partir des **municipales 2026** (circulaire **INTP2602966C**, validée par CE 27/02/2026).
  Classer ces formations en EXG avant 2026 serait une application rétroactive proscrite par
  la décision n° 3.

- **Souverainistes (DSV)** : classés **DTE** (et non EXD) en 2022 et 2024, en cohérence avec
  le traitement de DLF/Dupont-Aignan (CE 31/01/2020 n°437675) et confirmé par IOMA2415630C.

- **Écologistes (ECO/VEC)** : **GAU** sur tous les scrutins, conformément à l'absence de bloc
  écologiste distinct dans la nomenclature officielle.

- **Cas tranché manuellement** : **PREP 2002** (Pôle Républicain, Chevènement) classé **GAU**
  par cohérence avec le classement GAU de Chevènement (MDC) en présidentielle 2002.

## Application aux municipales 2008-2026

Cette section documente l'application concrète de la décision aux scrutins municipaux
(Phase D3.2, validée le 2026-06-09).

### Limitation de la source data.gouv.fr 2008

Le fichier Parquet officiel `general-results.parquet` publié par data.gouv.fr
pour les municipales 2008 est **incomplet pour le département du Nord (59)**.

Vérification effectuée le 2026-06-10 (Phase D3.3) : le fichier source contient
seulement **2 communes du 59** sur l'ensemble national — Seclin (59560) et
Pérenchies (59457). Les grandes villes habituellement nuancées (Lille, Roubaix,
Tourcoing, Valenciennes, Dunkerque) sont absentes du fichier.

Répartition par département HdF dans le Parquet 2008 :

| Département | Communes dans Parquet 2008 |
|---|---|
| 02 Aisne | 13 |
| **59 Nord** | **2** |
| 60 Oise | 32 |
| 62 Pas-de-Calais | 102 |
| 80 Somme | 15 |
| **Total HdF** | **164** |

Conséquence pour le projet : sur la carte 2008, ces communes apparaissent
en gris (comportement honnête du LEFT JOIN sur `nuances_harmonisees`).
L'UI affiche un warning explicite. Aucune correction technique possible —
la lacune est en amont.

Cette limitation n'affecte que le scrutin 2008. Les scrutins 2014, 2020 et
2026 ont une couverture complète du département Nord.

### Périmètre et seuils de nuançage

Les circulaires municipales distinguent deux régimes selon la taille de la commune :

- **Communes ≥ 3 500 hab** : scrutin de liste proportionnel à deux tours. Les préfets
  attribuent une nuance à chaque liste (= chaque valeur `no_panneau`). Ces nuances sont
  classées dans `nuances_harmonisees`.
- **Communes < 3 500 hab** (seuil INTA1931378J 2020 ; identique dans INTP2602966C 2026) :
  pas de nuançage officiel — `nuance = NULL` dans les fichiers Parquet. `voix` représente
  des suffrages *par candidat* (scrutin majoritaire plurinominal), non des suffrages *par liste*.
  Ces lignes sont chargées avec `bloc = NULL` et `pct_exprimes = NULL` dans les vues.
- **Seuil historique 2008** : la circulaire de nuançage 2008 utilisait un seuil de 3 500 hab.
  En pratique, seules 164 communes HdF apparaissent dans le Parquet 2008 (les grandes
  communes), confirmant que seule la strate ≥ 3 500 hab était nuancée.

**Exception chefs-lieux d'arrondissement** : la circulaire INTP2602966C prévoit que
certains chefs-lieux d'arrondissement de taille < 3 500 hab reçoivent malgré tout un
nuançage. En HdF 2026, ~2 communes inférieures au seuil apparaissent avec une nuance
dans le Parquet. Ces lignes sont traitées normalement (nuance → bloc via
`nuances_harmonisees`) sans correction manuelle.

### Clé technique : `no_panneau` synthétique pour 2008

Les fichiers Parquet du scrutin 2008 ont `no_panneau = NULL` pour la totalité des
109 983 lignes. Cette colonne étant partie de la clé primaire `(id_election, code_departement,
code_commune, code_bv, no_panneau)` avec contrainte NOT NULL, l'insertion échouerait.

**Décision** : synthétiser `no_panneau` par `ROW_NUMBER()` fenêtré sur
`(id_election, code_departement, code_commune, code_bv)`, trié par `(nuance, voix DESC)`.
L'ordre est stable *au sein d'une même exécution* du loader mais **non reproductible**
d'une exécution à l'autre si le Parquet ou l'ordre d'arrivée change.

Conséquence : `no_panneau` en 2008 est un identifiant de chargement, pas un identifiant
métier. Il ne doit pas être utilisé comme référence externe (jointures entre sessions,
URLs de drill-down). Les vues d'agrégation groupent par `nuance`, pas par `no_panneau`,
ce qui annule ce problème pour les usages analytiques.

### 67 entrées dans `nuances_harmonisees` (et non 69)

Proposition initiale : 69 nuances. Corrections validées :

| Code | Décision | Justification |
|------|----------|---------------|
| `NC` (2014, 2020) | **Non inséré** | NC = "Non classé" administratif, catégorie résiduelle du Ministère. Attribuer un bloc introduirait un classement éditorial non étayé. |
| `LMAJ` (2008) | **Non inséré** | LMAJ = sortie de la liste mayorale sortante, indicateur de situation (non réélu / majorité), pas d'idéologie stable à attribuer. |
| `LNC` (2020) | **Non inséré** | Parallèle de NC pour les listes aux communes > 1 000 hab. Même raisonnement que NC. |

Total retenu : **67 entrées** réparties sur 4 annees : 12 (2008), 17 (2014), 19 (2020), 19 (2026).

### Décisions de classement notables

**LCMD 2008 → GAU** : les libellés de liste sont NULL dans le Parquet 2008 pour ce code.
L'analyse contextuelle (présence exclusive dans le bassin minier et les villes ouvrières
du Nord-Pas-de-Calais, nomenclature "Communiste et Divers") conduit à classer GAU.
Décision conservatrice — les 12 communes concernées en 2008 t1 correspondent au réseau
PCF/apparentés actif sur ce territoire.

**LDVC 2020 → CENT** (CE 31/01/2020 n°437675) : le Conseil d'État a confirmé dans cette
décision que LDVC (Divers Centre) correspond aux investitures LREM/MoDem/UDI aux
municipales 2020. Source : `docs/sources-officielles/nuances/2020-CE_decision_437675.md`.

**LFI 2020 → GAU, LFI 2026 → EXG** (bascule INTP2602966C + CE 27/02/2026 n°512694) :
conformément à la règle n° 3 (classement "officiel de l'époque"), LFI est GAU jusqu'en
2024 inclus et EXG seulement à partir des municipales 2026. La circulaire INTP2602966C
et la décision CE n°512694 introduisent explicitement ce changement. Cette bascule est
documentée et testée (voir `tests/test_elections_municipales.py::TestLFIBascule`).

**LUDR 2026 → EXD** : code nouveau introduit par INTP2602966C pour les listes
"Union Droite Républicaine" (allié RN/parti Ciotti). Classé EXD conformément à la grille.

## Réversibilité

Un classement = une ligne dans une table de référence (`candidats_presidentielle` ou
`nuances_harmonisees`). Il est modifiable sans toucher aux données brutes ni à la
logique de chargement. Toute modification doit être accompagnée d'une mise à jour de
la colonne `source_bloc` et d'un commit motivé.
