# Schéma électoral DuckDB

Référence des 6 tables électorales créées par `create_elections_schema()` dans
`src/ministere_de_l_info/etl/schema_elections.py`.

**Périmètre géographique** : Hauts-de-France uniquement (code_region = `'32'`).
Le filtrage est appliqué au chargement des résultats (C2b), pas dans ce schéma.

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

| Colonne | Type | Description |
|---------|------|-------------|
| `id_election` | `VARCHAR` PK | FK → `elections.id_election` |
| `code_departement` | `VARCHAR` PK | Code département sans zéro-padding (`'59'`, `'2A'`) |
| `code_commune` | `VARCHAR` PK | Code INSEE commune, 5 chars zéro-paddé (`'59606'`) |
| `code_bv` | `VARCHAR` PK | Identifiant du bureau de vote |
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

| Colonne | Type | Description |
|---------|------|-------------|
| `id_election` | `VARCHAR` PK | FK → `elections.id_election` |
| `code_departement` | `VARCHAR` PK | Code département |
| `code_commune` | `VARCHAR` PK | Code INSEE commune 5 chars |
| `code_bv` | `VARCHAR` PK | Identifiant du bureau de vote |
| `no_panneau` | `INTEGER` PK | Numéro de panneau (ordre alphabétique du candidat) |
| `nuance` | `VARCHAR` | Code politique — NULL pour pres 2017/2022 et euro 2019 |
| `sexe` | `VARCHAR` | Sexe déclaré du candidat |
| `nom` | `VARCHAR` | Nom de famille MAJUSCULES (tel que dans le Parquet) |
| `prenom` | `VARCHAR` | Prénom |
| `voix` | `INTEGER` | Nombre de voix obtenues dans ce bureau |

**Colonnes de liste non stockées** (scrutins de liste : euro, regi, muni) :
`liste`, `libelle_abrege_liste`, `libelle_etendu_liste`, `nom_tete_liste`, `binome`.
Ces colonnes seront ajoutées en version C2c lors de l'extension aux autres scrutins.

---

## Table `blocs_politiques`

Référentiel des **6 blocs de clivages officiels** du Ministère de l'Intérieur.

**Origine** : circulaire IOMA2322276J du 16 août 2023 (sénatoriales 2023), première
circulaire à formaliser ce regroupement. Pour les scrutins antérieurs à 2023, les blocs
sont reconstruits selon la logique officielle, avec classement "de l'époque"
(voir [ADR-0005](adr/0005-nuances-et-blocs-officiels.md) et
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

**Note** : la grille officielle ne comporte pas de bloc "écologistes" distinct.
Les formations écologistes sont classées selon leur position sur l'axe gauche-droite
(EELV/Verts → `GAU` ; écologie centriste type Cap21 → `CENT`).

---

## Table `nuances_harmonisees`

Mapping `(nuance, annee) → bloc` pour les scrutins **avec nuances** dans le Parquet.

| Colonne | Type | Description |
|---------|------|-------------|
| `nuance` | `VARCHAR` PK | Code nuance tel qu'il apparaît dans le Parquet |
| `annee` | `INTEGER` PK | Année du scrutin (même nuance peut changer de sens selon l'année) |
| `bloc` | `VARCHAR` NN | FK → `blocs_politiques.bloc` |
| `source_bloc` | `VARCHAR` | Justification courte du classement (1 ligne, modèle `candidats_presidentielle`) |

**Couverture** : **149 entrées** = 38 présidentielles (codes-candidats 2002/2007/2012)
+ **111 législatives** (codes partisans, 2002-2024). Détail et validation des nuances
législatives : `reports/mapping-nuances-legislatives-validated.md`, méthodologie en
ADR-0005 (§ « Application aux législatives 2002-2024 »).

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

**Couverture** : 11 candidats 2017 + 12 candidats 2022 = 23 entrées.

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

## Classements — blocs politiques

Le classement de chaque candidat ou nuance dans un bloc repose sur la **nomenclature
officielle du Ministère de l'Intérieur**, avec le principe du "classement de l'époque" :
un parti est classé dans le bloc qui lui était attribué à la date du scrutin.

Voir [ADR-0005](adr/0005-nuances-et-blocs-officiels.md) pour le raisonnement complet
et [l'index des circulaires](sources-officielles/nuances/index.md) pour les sources.

**Cas notables documentés** :

| Candidat / Nuance | Bloc retenu | Justification |
|-------------------|-------------|---------------|
| MÉLENCHON (2012, 2017, 2022) | `GAU` | LFI classé GAU par circulaire IOMA2322276J (2023) ; bascule EXG seulement avec INTP2602966C (2026) |
| ROUSSEL Fabien (2022) | `GAU` | PCF = nuance gauche dans logique officielle |
| DUPONT-AIGNAN (2012, 2017, 2022) | `DTE` | DLR/DLF = souverainiste gaulliste droite ; CE 31/01/2020 n°437675 suspend classement EXD |
| de VILLIERS (2007) | `DTE` | MPF = nuance DVDR (divers droite) dans logiques de l'époque |
| BOVÉ (2007) | `GAU` | Écologie de gauche ; nuances Verts classées GAU dans logique officielle |
| LEPAGE (2002) | `CENT` | Cap21 = écologie centriste libérale ; pas de bloc écolo officiel |
| MAMÈRE (2002), VOYNET (2007), JOLY (2012) | `GAU` | Verts/EELV = allié PS, nuances classées GAU |
| ASSELINEAU (2017) | `DIV` | UPR = souverainiste inclassable, nuance DIVC |

Toute modification doit être tracée (commit motivé + mise à jour de `source_bloc`).

---

## Vues d'agrégation (C2b)

Cinq vues créées par `create_elections_views()` dans `schema_elections.py`,
appelée par `scripts/init_elections_schema.py`. Idempotentes (`CREATE OR REPLACE`).

### `v_resultats_candidats_avec_bloc`

Résultats au bureau de vote avec le **bloc politique résolu** pour chaque candidat.
Couvre les présidentielles 2002–2022 (et tout autre scrutin chargé ultérieurement).

Résolution du bloc via `COALESCE(nh.bloc, cp.bloc)` :
- 2002/2007/2012 : jointure `nuances_harmonisees` sur `(nuance, annee)`
- 2017/2022 : jointure `candidats_presidentielle` sur `(nom, annee)` (nuance NULL)

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

---

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
