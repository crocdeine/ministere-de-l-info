# Schéma électoral DuckDB

Référence des 6 tables électorales créées par `create_elections_schema()` dans
`src/ministere_de_l_info/etl/schema_elections.py`, complétées par les migrations
`scripts/migrations/0006_add_municipales_schema.py` (colonnes de liste) et
`0007_add_municipales_views.py` (vues municipales).

Mis à jour le 2026-09-24 sur la base du code (ADR-0010). Chiffres revérifiés le
2026-10-06 sur la base locale (lecture seule) : 56 scrutins au référentiel, 30 avec des
résultats chargés (10 présidentielles, 12 législatives, 8 municipales), 162 469 lignes
de participation, 1 093 836 lignes candidats, 229 entrées `nuances_harmonisees`
(117 codes distincts), 23 entrées `candidats_presidentielle`, 11 vues électorales.

Les nuances servent aussi au module Législatif : un député non inscrit est classé selon
la nuance préfectorale de son élection, convertie par `nuances_harmonisees`
(`etl/loaders/legislatif_nuances_ni.py`, voir [architecture.md](architecture.md)).

**Périmètre géographique** : paramètre `--perimetre` des scripts de chargement
(vague B, 2026-10-06) : `hdf` (défaut, code_region = `'32'`) ou `france` (toutes les
communes de `geographies_communes`), granularité bureau de vote dans les deux cas. Les
vues et requêtes « HdF » de l'interface filtrent explicitement les 5 départements
(`v_evolution_blocs_hdf_legi`, `v_evolution_blocs_hdf_muni`, `v_croisement_eco_elections`,
`viz/elections_*queries.py`). Codes département de la source « ZA », « ZB », « ZC »,
« ZD », « ZM », « ZS » (outre-mer, certaines années) normalisés en `971`…`976` au
chargement. Les communes fusionnées depuis le scrutin sont **rattachées à la commune
actuelle** (voir « Rattachement des communes fusionnées ») ; restent écartés les Français
de l'étranger et les collectivités d'outre-mer absentes du référentiel (Pacifique,
Saint-Martin, Saint-Barthélemy), comptés dans `elections_ecarts_chargement`.

**Scrutins chargés** : présidentielles, législatives, municipales (2002-2026) et, depuis
la vague B, européennes (1999-2024), régionales (2004-2021) et départementales (2015,
2021) via `scripts/load_elections_autres.py`. Cantonales (2001-2011) non chargées.
Départementales : le nom du binôme (`binome` dans la source) est stocké dans `nom`.

---

## Vue d'ensemble

```
elections (référentiel)
    ↑ FK déclarative (id_election)
resultats_participation     ← participation par bureau de vote
resultats_candidats         ← résultats par candidat par bureau de vote

blocs_politiques (référentiel)
    ↑ FK déclarative (bloc)
nuances_harmonisees         ← (nuance, année) → bloc  [scrutins avec nuance]
candidats_presidentielle    ← (nom, année)    → bloc  [présidentielles sans nuance]
```

**Jointure principale résultats** :
```sql
JOIN ON (id_election, code_departement, code_commune, code_bv)
```

---

## Table `elections`

Référentiel des 56 scrutins disponibles dans le dataset (1999–2026).

| Colonne | Type | Description |
|---------|------|-------------|
| `id_election` | `VARCHAR` PK | Identifiant unique : `{YYYY}_{type}_t{N}` — ex. `'2022_pres_t1'` |
| `type_scrutin` | `VARCHAR` NN | Code du type de scrutin : `pres`, `legi`, `euro`, `regi`, `muni`, `dpmt`, `cant` |
| `annee` | `INTEGER` NN | Année du scrutin |
| `tour` | `INTEGER` NN | Numéro de tour (1 ou 2) |
| `libelle` | `VARCHAR` NN | Libellé complet : `'Présidentielle 2022 — 1er tour'` |
| `ancien_decoupage` | `BOOLEAN` DEF FALSE | TRUE pour législatives 2002/2007 (avant redécoupage Marleix, applicable dès 2012) |

**Couverture** :

| Type | Années disponibles | Nb scrutins |
|------|--------------------|-------------|
| `pres` | 2002, 2007, 2012, 2017, 2022 | 10 |
| `legi` | 2002, 2007, 2012, 2017, 2022, 2024 | 12 |
| `euro` | 1999, 2004, 2009, 2014, 2019, 2024 | 6 |
| `regi` | 2004, 2010, 2015, 2021 | 8 |
| `muni` | 2008, 2014, 2020, 2026 | 8 |
| `dpmt` | 2015, 2021 | 4 |
| `cant` | 2001, 2004, 2008, 2011 | 8 |

---

## Table `resultats_participation`

Données de participation électorale par bureau de vote. Correspond au fichier source
`candidats-results.parquet` (nommage trompeur — voir [PIÈGE 1](#pieges-connus)).

**Pas de clé primaire** (décision Mathias 2026-10-07, migration 0009) : les colonnes
marquées « clé » forment une clé logique (NOT NULL) sans index ; l'index pesait ~1,1 Go en
France entière. L'unicité est contrôlée par les loaders (`verifier_unicite_resultats`,
erreur si doublon).

| Colonne | Type | Description |
|---------|------|-------------|
| `id_election` | `VARCHAR` clé | FK → `elections.id_election` |
| `code_departement` | `VARCHAR` clé | Code département sans zéro-padding (`'59'`, `'2A'`) |
| `code_commune` | `VARCHAR` clé | Code INSEE commune, 5 chars zéro-paddé (`'59606'`) |
| `code_bv` | `VARCHAR` clé | Identifiant du bureau de vote |
| `inscrits` | `INTEGER` | Inscrits sur les listes électorales |
| `abstentions` | `INTEGER` | Abstentions |
| `votants` | `INTEGER` | Votants (inscrits – abstentions) |
| `blancs` | `INTEGER` | Bulletins blancs |
| `nuls` | `INTEGER` | Bulletins nuls |
| `exprimes` | `INTEGER` | Suffrages exprimés (votants – blancs – nuls) |
| `code_circo` | `VARCHAR` nullable | Code circonscription `"DPT-NN"` (ex. `"59-05"`). Renseigné pour legi 2012/2017/2022 depuis le Parquet source ; reconstruit par jointure spatiale pour 2002/2007/2024. NULL si reconstruction impossible. |

**Ratios non stockés** (calculables à la volée) : `ratio_abstentions_inscrits`,
`ratio_votants_inscrits`, `ratio_blancs_votants`, `ratio_exprimes_votants`, etc.

---

## Table `resultats_candidats`

Résultats par candidat, par bureau de vote. Correspond au fichier source
`general-results.parquet` (nommage trompeur — voir [PIÈGE 1](#pieges-connus)).
Même règle de clé logique sans index que `resultats_participation`.

| Colonne | Type | Description |
|---------|------|-------------|
| `id_election` | `VARCHAR` clé | FK → `elections.id_election` |
| `code_departement` | `VARCHAR` clé | Code département |
| `code_commune` | `VARCHAR` clé | Code INSEE commune 5 chars |
| `code_bv` | `VARCHAR` clé | Identifiant du bureau de vote |
| `no_panneau` | `INTEGER` clé | Numéro de panneau (ordre alphabétique du candidat) |
| `nuance` | `VARCHAR` | Code politique — NULL pour pres 2017/2022 et euro 2019 |
| `sexe` | `VARCHAR` | Sexe déclaré du candidat |
| `nom` | `VARCHAR` | Nom de famille MAJUSCULES (tel que dans le Parquet) |
| `prenom` | `VARCHAR` | Prénom |
| `voix` | `INTEGER` | Nombre de voix obtenues dans ce bureau |

**Colonnes de liste** (ajoutées par la migration 0006, renseignées pour les municipales) :

| Colonne | Type | Description |
|---------|------|-------------|
| `liste` | `VARCHAR` | Identifiant de liste du Parquet |
| `libelle_abrege_liste` | `VARCHAR` | Libellé court de la liste |
| `libelle_etendu_liste` | `VARCHAR` | Libellé long de la liste |
| `nom_tete_liste` | `VARCHAR` | Nom de la tête de liste |
| `prenom_tete_liste` | `VARCHAR` | Toujours NULL (absent du Parquet) |

Municipales : `nom` et `prenom` sont NULL (scrutin de liste). En 2008, `no_panneau` est
synthétique (`ROW_NUMBER()` par bureau, ADR-0005) et n'identifie pas une liste d'un
bureau à l'autre.

---

## Table `blocs_politiques`

Référentiel des **6 blocs de clivages officiels** du Ministère de l'Intérieur.

**Origine** : la première grille officielle de blocs est l'annexe 3 de la circulaire
INTA1931378J du 3 février 2020 (municipales 2020), où le bloc « divers » s'appelle
`AUT`. Suivent IOMA2322276J (sénatoriales 2023, « Autres ») et INTP2602966C
(municipales 2026, `DIV`). Pour un scrutin sans grille, la doctrine de
l'[ADR-0010](adr/0010-revision-nuances-et-blocs.md) s'applique : grille la plus proche
dans le temps (antérieure de préférence) si le code y désigne la même famille
politique, sinon classement reconstruit justifié (voir aussi
[ADR-0005](adr/0005-nuances-et-blocs-officiels.md) et
[index des circulaires archivées](sources-officielles/nuances/index.md)).

| Colonne | Type | Description |
|---------|------|-------------|
| `bloc` | `VARCHAR` PK | Code officiel du Ministère : `EXG`, `GAU`, `DIV`, `CENT`, `DTE`, `EXD` |
| `libelle` | `VARCHAR` NN | Libellé affiché (`'Extrême gauche'`, `'Gauche'`, …) |
| `couleur` | `VARCHAR` NN | Couleur hexadécimale pour les cartes et graphiques |
| `ordre` | `INTEGER` NN | Position sur l'axe gauche→droite (1 à 6) |

**Blocs et couleurs** :

| Code | Libellé | Couleur | Ordre |
|------|---------|---------|-------|
| `EXG` | Extrême gauche | `#8B0000` | 1 |
| `GAU` | Gauche | `#E84C61` | 2 |
| `DIV` | Divers | `#9E9E9E` | 3 |
| `CENT` | Centre | `#F5B800` | 4 |
| `DTE` | Droite | `#3B7DD8` | 5 |
| `EXD` | Extrême droite | `#1F3864` | 6 |

Les couleurs sont indicatives et ajustables sans toucher au schéma.

**Note** : les grilles officielles ne comportent pas de bloc "écologistes" distinct.
Règle (ADR-0010) : `VEC`/`LVEC` (Verts, EELV, Les Écologistes) → `GAU` sur tous les
scrutins ; `ECO`/`LECO` (autres écologistes, dont Cap 21) → `DIV`, comme dans les grilles
2020, 2023 et 2026, sauf pour les législatives 2017 et 2022 où le code `ECO` englobe EELV
(pas de code `VEC`) et reste `GAU`.

---

## Table `nuances_harmonisees`

Mapping `(nuance, annee) → bloc` pour les scrutins **avec nuances** dans le Parquet.

| Colonne | Type | Description |
|---------|------|-------------|
| `nuance` | `VARCHAR` PK | Code nuance tel qu'il apparaît dans le Parquet |
| `annee` | `INTEGER` PK | Année du scrutin (même nuance peut changer de sens selon l'année) |
| `bloc` | `VARCHAR` NN | FK → `blocs_politiques.bloc` |
| `source_bloc` | `VARCHAR` | Justification courte du classement (1 ligne, modèle `candidats_presidentielle`) |

**Couverture** : **384 entrées**, source unique `schema_elections.py` (listes
`_NUANCES_PRES`, `_NUANCES_LEGI`, `_NUANCES_MUNI`, `_NUANCES_EURO_REGI_DPMT`) :

| Jeu | Années | Entrées |
|-----|--------|---------|
| Présidentielles (codes-candidats) | 2002 (16), 2007 (12), 2012 (10) | 38 |
| Législatives (codes partisans) | 2002 (22), 2007 (17), 2012 (17), 2017 (17), 2022 (16), 2024 (22) | 111 |
| Municipales (codes de liste) | 2008 (15), 2014 (17), 2020 (23), 2026 (25) | 80 |
| Européennes, régionales, départementales (vague B, décision Mathias 2026-10-07) | euro 1999 (13), 2004 euro+regi (16), euro 2009 (12), regi 2010 (13), regi 2015 (20), regi 2021 (22), dpmt 2015 (19), dpmt 2021 (26), euro 2024 (14) | 155 |

Vague B : les européennes 2014 utilisent les codes des municipales 2014 (même année,
même sens) ; les codes de liste 2004 sont communs aux européennes et aux régionales.
Cas tranchés par Mathias le 2026-10-07 (addendum « vague B » de l'ADR-0010) : `LDR` 2004
→ DTE, `LUCD` / `BC-UCD` 2021 → DTE, `BC-UCG` 2021 → DIV, `LECO` / `BC-ECO` 2021 → GAU
(EELV inclus), unions 100 % gauche → GAU. Seuls codes sans bloc : résidus `LPC`, `LDD`,
`LDV` des européennes 2009 (11 voix ; `_CODES_VAGUE_B_NON_CLASSES`).
`populate_nuances_vague_b()` écrit ces entrées par `INSERT OR REPLACE` ciblé.

Les listes municipales 2020 et 2026 reprennent intégralement les codes de liste des
grilles officielles (INTA1931378J et INTP2602966C, annexes 3) ; celles de 2008 et 2014,
les listes officielles de nuances publiées sur les archives du ministère (vérifiées le
2026-09-25, `docs/sources-officielles/nuances/2008-*` et `2014-*`). Codes municipaux
volontairement **non insérés** (bloc NULL dans les vues) : `NC` (2014, 2020), `LNC`
(2020). `LMAJ` (2008) est mappé `DTE` depuis l'addendum de l'ADR-0010 (2026-09-25).

Chargement : `populate_elections_referentiels()` réécrit les trois jeux ;
`populate_nuances_municipales()` (appelée par `scripts/load_elections_municipales.py`)
remplace les seules années municipales (`DELETE` ciblé + `INSERT`, transaction). Un
garde-fou refuse l'écriture si une année municipale est partagée avec pres/legi : la clé
ne contient pas `type_scrutin` (audit M5, point ouvert de l'ADR-0010).

Détail et validation : `reports/mapping-nuances-legislatives-validated.md`,
`reports/mapping-nuances-municipales-validated.md`, ADR-0005 (§ « Application… ») et
ADR-0010 (reclassements du 2026-09-24).

**Note** : pour les présidentielles 2002/2007/2012, les codes nuances sont des
**codes-candidats** (ex. `CHIR` = Chirac, `JOSP` = Jospin), différents des codes
partisans utilisés par les autres scrutins (ex. `RN`, `SOC`, `LR`). La clé
`(nuance, annee)` évite toute collision entre ces deux conventions (aucun chevauchement
observé sur 2002/2007/2012).

---

## Table `candidats_presidentielle`

Mapping `(nom, annee) → bloc` pour les présidentielles **sans nuances** (2017 et 2022).
Chaque entrée porte le parti d'appartenance et la justification sourcée du classement.

| Colonne | Type | Description |
|---------|------|-------------|
| `annee` | `INTEGER` PK | Année de la présidentielle |
| `nom` | `VARCHAR` PK | Nom de famille EXACT du Parquet (MAJUSCULES, ex. `'LE PEN'`) |
| `prenom` | `VARCHAR` | Prénom |
| `parti` | `VARCHAR` | Parti / formation politique à la date du scrutin |
| `bloc` | `VARCHAR` NN | Code officiel FK → `blocs_politiques.bloc` (ex. `'EXD'`) |
| `libelle` | `VARCHAR` | Nom complet lisible (`'Marine Le Pen'`) |
| `source_bloc` | `VARCHAR` | Justification datée du classement (circulaire ou décision CE) |

**Couverture** : 11 candidats 2017 + 12 candidats 2022 = 23 entrées, plus 34 listes
**européennes 2019** (nuance NULL dans la source, même mécanisme ; décision Mathias
2026-10-07) :
pour ce scrutin, `resultats_candidats.nom` reçoit `nom_tete_liste` de la source
(ex. `'BARDELLA Jordan'`) et la clé `nom` de cette table a le même format. Toutes les
listes sont classées (Philippot → EXD, Vauclin → DIV).

---

## Jointure bloc pour la visualisation

En pratique, utiliser directement la vue `v_resultats_candidats_avec_bloc` (C2b)
qui résout le bloc via `COALESCE(nh.bloc, cp.bloc)` en un seul SELECT.

Pour référence, la logique manuelle équivalente :

```sql
-- Scrutins avec nuances (2002/2007/2012)
SELECT rc.*, nh.bloc
FROM resultats_candidats rc
JOIN nuances_harmonisees nh
    ON nh.nuance = rc.nuance AND nh.annee = CAST(SPLIT_PART(rc.id_election, '_', 1) AS INT)

-- Présidentielles 2017 / 2022 (nuances NULL)
SELECT rc.*, cp.bloc
FROM resultats_candidats rc
JOIN candidats_presidentielle cp
    ON cp.nom = rc.nom AND cp.annee = CAST(SPLIT_PART(rc.id_election, '_', 1) AS INT)
WHERE rc.id_election IN ('2017_pres_t1','2017_pres_t2','2022_pres_t1','2022_pres_t2')
```

---

## Pièges connus {#pieges-connus}

### PIÈGE 1 — Nommage inversé des fichiers sources

| Fichier Parquet | Contenu réel |
|-----------------|-------------|
| `general-results.parquet` | Résultats par **candidat** → `resultats_candidats` |
| `candidats-results.parquet` | Données de **participation** → `resultats_participation` |

### PIÈGE 2 — Nuances NULL pour certains scrutins

Présidentielles 2017/2022 et européennes 2019 : colonne `nuance` = NULL dans le Parquet.
Utiliser `candidats_presidentielle` pour la résolution de bloc (présidentielles uniquement).

### PIÈGE 3 — Nature des codes nuances pour les présidentielles

Dans les présidentielles 2002/2007/2012, les nuances sont des **abréviations du nom du
candidat** (`CHIR`, `JOSP`, `SARK`), pas des codes partisans comme dans les autres scrutins
(`RN`, `SOC`, `LR`). La table `nuances_harmonisees` gère les deux conventions.

### PIÈGE 4 — Évolution des nuances dans le temps

La même nuance peut désigner des formations différentes selon l'année. La clé primaire
`(nuance, annee)` dans `nuances_harmonisees` est intentionnelle : `DVG` en 2002 ≠ `DVG` en
2022. Ne jamais joindre sur `nuance` seul sans filtrer sur `annee`.

---

### PIÈGE 5 — Municipales 2026 : nuance NULL

49 637 lignes candidats des municipales 2026 (communes sous le seuil de nuançage,
3 500 habitants) ont une nuance NULL dans la source : elles restent « Non classé »
(bloc NULL), comme `NC` et `LNC`. Ce n'est pas une erreur de chargement.

## Rattachement des communes fusionnées (décision Mathias 2026-10-07)

Table **`communes_passage`** (`code_ancien` PK, `code_actuel`, `date_effet`,
`type_evenement`), construite par `scripts/load_communes_passage.py` depuis le fichier
des mouvements des communes du COG INSEE 2026 (Licence Ouverte 2.0) : arêtes des
fusions (MOD 31-34), changements de code (41) et de département (50), arête la plus
récente par code, chaîne suivie jusqu'à un code de `geographies_communes`
(4 234 codes anciens). Les loaders lisent la source via `source_rattachee_sql()` :

- `code_commune` = commune actuelle ; **`code_commune_origine`** (nouvelle colonne des
  deux tables de résultats) = code d'origine, NULL si inchangé ;
- `code_bv` préfixé du code d'origine (`74011-0001`) : pas de collision avec les bureaux
  de la commune d'accueil ;
- `code_departement` = département de la commune actuelle ; la clé de circonscription
  (législatives 2012-2022) reste construite sur le département **du scrutin**.

Limites : géographie actuelle (une commune absorbée est comptée dans sa commune
d'accueil, y compris aux municipales, où ses listes restent distinctes dans
`v_listes_commune_muni` mais s'additionnent dans `v_scores_commune_muni`) ; scissions
(créations, rétablissements : 999 événements) recensées mais jamais réparties ; une
commune (code 26383 / 02899) reste non rattachée (≤ 184 exprimés par scrutin).
Effet mesuré : exprimés HdF en hausse de 0,06 % (2024) à 1,2 % (euro 1999) ; bilan
France = total de la source (écart 0,000 %).

## Contrôles de chargement (vague B, 2026-10-07)

Exécutés par `controler_chargement()` (`etl/loaders/elections_agregees.py`) à la fin de
chaque loader :

- **Unicité** des clés logiques des tables de résultats (`verifier_unicite_resultats`) :
  `RuntimeError` en cas de doublon.
- **Lignes écartées** (commune de la source absente de `geographies_communes`), par
  scrutin et catégorie (`rattachee` : commune fusionnée rattachée, pour traçabilité ;
  `etranger` : département `ZZ` ; `outremer_hors_referentiel` : communes `98…`, `977`,
  `978`, `97123`, `97127`, départements `ZN`, `ZP`, `ZW`, `ZX`, `ZT`, `ZY` ; `reste`) : écrites dans la table **`elections_ecarts_chargement`** (`id_election`,
  `perimetre`, `categorie`, `nb_communes`, `nb_bv`, `exprimes`, `exprimes_total`,
  `pct_exprimes`), journalisées en warning ; `RuntimeError` si `reste` dépasse
  `SEUIL_ECART_RESTE_PCT` (3 %) des exprimés d'un scrutin.
- **Somme des voix = exprimés** par bureau (hors municipales, dont les communes
  plurinominales additionnent des voix de candidats) : warning avec les 5 pires écarts,
  non bloquant. Mesure France (2026-10-07) : 1 BV en 2009_euro_t1 (écart 180 voix,
  scrutin à `no_panneau` NULL dans la source), 5 BV en 2024_legi_t1 et 1 en 2024_legi_t2
  (écarts ≤ 2 voix) ; 0 ailleurs.

## Classements — blocs politiques

Le classement de chaque candidat ou nuance dans un bloc repose sur la **nomenclature
officielle du Ministère de l'Intérieur**, avec le principe du "classement de l'époque" :
un parti est classé dans le bloc qui lui était attribué à la date du scrutin.

Voir [ADR-0005](adr/0005-nuances-et-blocs-officiels.md) pour le raisonnement complet
et [l'index des circulaires](sources-officielles/nuances/index.md) pour les sources.

**Cas notables documentés** :

| Candidat / Nuance | Bloc retenu | Justification |
|-------------------|-------------|---------------|
| MÉLENCHON (2012, 2017, 2022) | `GAU` | FI → GAU dans les grilles 2020 (INTA1931378J) et 2023 (IOMA2322276J) ; bascule EXG seulement avec INTP2602966C (2026) |
| ROUSSEL Fabien (2022) | `GAU` | PCF : COM/LCOM → GAU dans toutes les grilles officielles |
| DUPONT-AIGNAN (2012, 2017, 2022) | `DTE` | DLF → DTE dans la grille 2020 (INTA1931378J) ; CE 31/01/2020 n°437675 suspend le classement EXD |
| de VILLIERS (2007) | `DTE` | MPF = nuance DVDR (divers droite) dans logiques de l'époque |
| BOVÉ (2007) | `GAU` | Écologie de gauche ; nuances Verts classées GAU dans logique officielle |
| LEPAGE (2002) | `DIV` | Cap 21 rangé dans ECO → AUT (= DIV) par la grille 2020 (ADR-0010 ; avant : CENT) |
| MAMÈRE (2002), VOYNET (2007), JOLY (2012) | `GAU` | Verts/EELV = VEC → GAU dans toutes les grilles |
| SAINT-JOSSE (2002), NIHOUS (2007), CPNT (legi 2002, 2007) | `DIV` | CPNT autonome à l'époque ; son rangement dans DVD (grille 2020) reflète l'association à l'UMP/LR après 2010 (ADR-0010) |
| ASSELINEAU (2017) | `DIV` | UPR = souverainiste inclassable, nuance DIVC |
| ECO (legi 2002, 2007, 2012, 2024) | `DIV` | Écologistes hors Verts/EELV (VEC distinct) ; grilles 2020/2023 : ECO → AUT/Autres (ADR-0010) |
| ECO (legi 2017, 2022) | `GAU` | ECO englobe EELV (pas de code VEC) : sens différent de la grille 2020 (ADR-0010) |
| UDI (legi 2024) | `DTE` | Grille antérieure la plus proche IOMA2322276J (2023) : UDI → Droite (ADR-0010) |
| UDI (legi 2017, 2022) | `CENT` | Grille la plus proche INTA1931378J (2020) : UDI → CENT |
| PRV (legi 2012) | `CENT` | Mouvement radical (successeur du PRV) → CENT en 2020 (ADR-0010 ; avant : DTE) |
| LCOM (muni 2008-2026) | `GAU` | Grilles 2020 et 2026 ; 2008/2014 par la grille 2020 (ADR-0010 ; avant : EXG) |
| LUDI / LUD / LECO (muni) | `CENT` / `DTE` / `DIV` | Grilles 2020 et 2026 (ADR-0010) |
| LCMD (muni 2008) | `CENT` | « Liste centre-MoDem » (archives du ministère) ; grille 2020 : LMDM → CENT (ADR-0010 lot 2 ; avant : GAU) |
| LMAJ (muni 2008) | `DTE` | « Liste de la majorité » (UMP/NC) ; grille 2020 : LLR/LUD → DTE (ADR-0010 lot 2 ; avant : exclu) |
| LGC / LMC (muni 2008) | `DIV` / `CENT` | Ententes gauche-centristes et majorité-centristes sans équivalent dans les grilles : règle 3, maintien (ADR-0010 lot 2) |
| LREG / LEXD (muni 2008) | `DIV` / `EXD` | Codes officiels 2008 ajoutés ; grille 2020 : LREG → AUT, LEXD → EXD (ADR-0010 lot 2) |

Toute modification doit être tracée (commit motivé + mise à jour de `source_bloc`).

---

## Vues d'agrégation

**11 vues**, toutes idempotentes (`CREATE OR REPLACE VIEW`) :

| Vue | Créée par | Scrutin | Grain |
|-----|-----------|---------|-------|
| `v_resultats_candidats_avec_bloc` | `create_elections_views()` | tous | BV × candidat |
| `v_scores_commune_pres` | `create_elections_views()` | pres | commune × bloc |
| `v_participation_commune_pres` | `create_elections_views()` | pres | commune |
| `v_scores_circo21_pres` | `create_elections_views()` | pres | commune (circo 59-21) × bloc |
| `v_evolution_blocs_circo21` | `create_elections_views()` | pres | année × tour × bloc |
| `v_scores_circo_legi` | `create_elections_views()` | legi | circonscription × bloc |
| `v_participation_circo_legi` | `create_elections_views()` | legi | circonscription |
| `v_evolution_blocs_hdf_legi` | `create_elections_views()` | legi | année × tour × bloc |
| `v_scores_commune_muni` | migration 0007 | muni | commune × bloc |
| `v_evolution_blocs_hdf_muni` | migration 0007 | muni | année × tour × bloc |
| `v_listes_commune_muni` | migration 0007 | muni | commune × liste |

`create_elections_views()` est appelée par `scripts/init_elections_schema.py` ; les vues
municipales par `uv run python scripts/migrations/0007_add_municipales_views.py`.

**Résolution du bloc selon le scrutin** (conséquence visible des reclassements) :
- présidentielles : `COALESCE(nh.bloc, cp.bloc)` ; bloc NULL si le code est absent ;
- législatives : `COALESCE(nh.bloc, 'DIV')` — une nuance absente du référentiel tombe
  en `DIV` (le test `test_elections_legislatives.py` vérifie qu'aucune n'est absente) ;
- municipales : `LEFT JOIN` sans repli — bloc NULL (« Non classé ») pour `NC`, `LNC`
  et les communes sans nuance ; `pct_exprimes` est alors NULL.

### `v_resultats_candidats_avec_bloc`

Résultats au bureau de vote avec le **bloc politique résolu** pour chaque candidat,
tous scrutins chargés (colonne `type_scrutin`).

Résolution du bloc via `COALESCE(nh.bloc, cp.bloc)` :
- scrutins avec nuance : jointure `nuances_harmonisees` sur `(nuance, annee)`
- présidentielles 2017/2022 : jointure `candidats_presidentielle` sur `(nom, annee)` (nuance NULL)

| Colonne | Description |
|---------|-------------|
| `id_election`, `type_scrutin`, `annee`, `tour` | Identifiants du scrutin |
| `code_departement`, `code_commune`, `code_bv` | Localisation géographique |
| `no_panneau`, `nom`, `prenom`, `nuance` | Identification du candidat |
| `voix` | Suffrages exprimés pour ce candidat dans ce bureau |
| `bloc` | Code officiel résolu (`EXG`, `GAU`, `DIV`, `CENT`, `DTE`, `EXD`) |

### `v_scores_commune_pres`

Voix **agrégées à la commune** par bloc, pour les présidentielles uniquement.

```sql
SELECT bloc, voix FROM v_scores_commune_pres
WHERE code_commune = '59606' AND annee = 2022 AND tour = 1
ORDER BY voix DESC
```

### `v_participation_commune_pres`

Participation **agrégée à la commune**, présidentielles uniquement.
Inclut `taux_participation_pct` calculé à la volée (`ROUND(100 × votants / inscrits, 2)`).

### `v_scores_circo21_pres`

Sous-ensemble de `v_scores_commune_pres` filtré sur les **20 communes de la
21e circonscription du Nord** (Valenciennes). Codes INSEE validés par jointure
spatiale sur `geographies_circonscriptions` (code `'59-21'`).

Communes : Aubry-du-Hainaut, Bellaing, Condé-sur-l'Escaut, Crespin, Curgies,
Estreux, Marly, Onnaing, Petite-Forêt, Préseau, Quarouble, Quiévrechain,
Rombies-et-Marchipont, Saint-Aybert, Saint-Saulve, Saultain, Sebourg,
Thivencelle, Valenciennes, Wallers.

### `v_evolution_blocs_circo21`

Évolution temporelle des blocs dans la circo 21, agrégée sur les 20 communes.

```sql
SELECT annee, bloc, voix_total FROM v_evolution_blocs_circo21
WHERE tour = 1 ORDER BY annee, voix_total DESC
```

Exemple de résultat (1er tour) :

| Année | Bloc dominant | Voix |
|-------|--------------|------|
| 2002 | GAU | 16 994 |
| 2007 | DTE | 20 268 |
| 2012 | GAU | 25 234 |
| 2017 | EXD | 18 311 |
| 2022 | EXD | 21 637 |

(Valeurs relevées avant l'ADR-0010 ; le reclassement de Lepage 2002 de CENT en DIV
modifie la ventilation 2002 sans changer le bloc dominant.)

### `v_scores_circo_legi`, `v_participation_circo_legi`, `v_evolution_blocs_hdf_legi`

Législatives : voix par `(id_election, annee, tour, ancien_decoupage, code_circo, bloc)`,
participation par circonscription (`taux_participation_pct`), puis agrégat HdF par
`(annee, tour, ancien_decoupage, bloc)`, borné aux 5 départements HdF. Seuls les bureaux
dont `code_circo` est renseigné sont comptés. `ancien_decoupage` = TRUE pour 2002/2007
(avant le redécoupage de 2010). Pour 2002, 2007 et 2024 (`code_circo` absent de la
source), la circonscription est reconstruite : circonscription du département de la
commune la plus proche de son centroïde (correctif vague B ; avant, un centroïde pouvait
tomber dans une circonscription d'un département voisin). Une commune coupée entre
plusieurs circonscriptions (Paris, Marseille…) est entièrement affectée à une seule :
**limite acceptée** par Mathias le 2026-10-07 (législatives 2024 en France entière : 529
circonscriptions représentées sur 559). L'interface la signale pour 2002/2007
(`_WARNING_ANCIEN_DECOUPAGE`, pages/elections_legislatives.py) ; pas encore pour 2024.

### `v_scores_commune_muni`

Municipales : `(annee, tour, code_commune, bloc)` → `voix`, `pct_exprimes`
(voix / exprimés de la commune, NULL si bloc NULL).

### `v_evolution_blocs_hdf_muni`

Municipales, agrégat HdF (filtre explicite sur les 5 départements) : `(annee, tour, bloc)` → `voix`, `pct_exprimes`
(voix / exprimés HdF, NULL si bloc NULL).

### `v_listes_commune_muni`

Détail liste par liste (drill-down) : une ligne par `(annee, tour, code_commune,
no_panneau)` avec nuance, bloc, libellés, tête de liste, voix, `pct_exprimes`. En 2008,
`no_panneau` est NULL et la liste est identifiée par ses descripteurs (correctif C1).

---

## Tables économiques

Déplacé : le schéma économique (5 tables, 6 vues) est documenté dans
[`docs/architecture.md`](architecture.md), l'[ADR-0006](adr/0006-module-economie-sources-et-schema.md)
et l'[ADR-0008](adr/0008-economie-sources-complementaires.md) ; source de vérité :
`src/ministere_de_l_info/etl/schema_economie.py`. L'ancienne section ci-dessous est
conservée pour mémoire et n'est **plus à jour** (millésimes et colonnes).

<details>
<summary>Ancienne section (Phase E, non maintenue)</summary>

## Tables économiques (Phase E — ADR-0006)

Deux tables séparées par source, structure large cohérente avec les tables
électorales. Voir `docs/adr/0006-module-economie-sources-et-schema.md`.

### `economie_filosofi`

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `code_commune` | `VARCHAR(5)` | PK, NOT NULL | Code INSEE commune (zéro-paddé) |
| `annee` | `INTEGER` | PK, NOT NULL | Millésime de la donnée Filosofi |
| `taux_pauvrete` | `DOUBLE` | nullable | % ménages sous 60% revenu médian national |
| `niveau_vie_median` | `DOUBLE` | nullable | Niveau de vie médian en euros |
| `d1_niveau_vie` | `DOUBLE` | nullable | 1er décile du niveau de vie |
| `d9_niveau_vie` | `DOUBLE` | nullable | 9e décile du niveau de vie |
| `secret` | `BOOLEAN` | DEFAULT FALSE | TRUE si données masquées (commune < 50 ménages) |

**Couverture** : communes HdF (~3 782), millésimes 2012→2022 annuels.
**Piège** : `nullstr=['s', 'nd']` obligatoire à l'import CSV/Parquet INSEE.

### `economie_rp`

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `code_commune` | `VARCHAR(5)` | PK, NOT NULL | Code INSEE commune (zéro-paddé) |
| `annee_millesime` | `INTEGER` | PK, NOT NULL | Ex: 2020 = recensement sur 2016-2020 |
| `tx_chomage_dec` | `DOUBLE` | nullable | Taux de chômage déclaratif RP (seule source communale) |
| `part_ouvriers_employes` | `DOUBLE` | nullable | % ouvriers + employés dans la population active |
| `part_emploi_industriel` | `DOUBLE` | nullable | % emplois secteur industriel (NAF division C) |
| `pop_active` | `INTEGER` | nullable | Population active totale |
| `secret` | `BOOLEAN` | DEFAULT FALSE | TRUE si données masquées |

**Couverture** : communes HdF, millésimes glissants 5 ans depuis 2006.
**Attention** : taux de chômage déclaratif ≠ taux BIT (différence méthodologique).

### Vues économiques

| Vue | Grain | Description |
|---|---|---|
| `v_economie_commune` | Commune × an | Fusion Filosofi + RP, indicateurs bruts |
| `v_croisement_eco_elections` | Commune × élection | Croisement `v_scores_commune_pres` + éco (n-1) |
| `v_evolution_economie_hdf` | An | Agrégats régionaux (moyennes HdF) |

</details>
