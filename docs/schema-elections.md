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

**Ratios non stockés** (calculables à la volée) : `ratio_abstentions_inscrits`,
`ratio_votants_inscrits`, `ratio_blancs_votants`, `ratio_exprimes_votants`, etc.

Le Parquet source contient aussi `code_circonscription`, `libelle_commune`,
`libelle_departement`, `code_canton` — non stockés dans ce schéma (version C2a).
À ajouter en C2c si nécessaire pour les scrutins législatifs.

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

Référentiel des blocs politiques utilisés pour la visualisation.

| Colonne | Type | Description |
|---------|------|-------------|
| `bloc` | `VARCHAR` PK | Identifiant interne (`extreme_gauche`, `gauche`, `ecologistes`, `centre`, `droite`, `extreme_droite`, `divers`) |
| `libelle` | `VARCHAR` NN | Libellé affiché (`'Extrême gauche'`, `'Gauche'`, …) |
| `couleur` | `VARCHAR` NN | Couleur hexadécimale pour les cartes et graphiques |
| `ordre` | `INTEGER` NN | Position sur l'axe gauche→droite (1 à 6, 99 pour divers) |

**Blocs et couleurs** :

| Bloc | Libellé | Couleur | Ordre |
|------|---------|---------|-------|
| `extreme_gauche` | Extrême gauche | `#8B0000` | 1 |
| `gauche` | Gauche | `#E63946` | 2 |
| `ecologistes` | Écologistes | `#4CAF50` | 3 |
| `centre` | Centre | `#FFD700` | 4 |
| `droite` | Droite | `#2196F3` | 5 |
| `extreme_droite` | Extrême droite | `#1A237E` | 6 |
| `divers` | Divers / Autres | `#9E9E9E` | 99 |

Les couleurs sont indicatives et ajustables sans toucher au schéma.

---

## Table `nuances_harmonisees`

Mapping `(nuance, annee) → bloc` pour les scrutins **avec nuances** dans le Parquet.

| Colonne | Type | Description |
|---------|------|-------------|
| `nuance` | `VARCHAR` PK | Code nuance tel qu'il apparaît dans le Parquet |
| `annee` | `INTEGER` PK | Année du scrutin (même nuance peut changer de sens selon l'année) |
| `bloc` | `VARCHAR` NN | FK → `blocs_politiques.bloc` |

**Couverture initiale** : présidentielles 2002, 2007, 2012 (38 entrées).
Les scrutins de liste (legi, euro, regi, muni) seront ajoutés en C2c.

**Note** : pour les présidentielles 2002/2007/2012, les codes nuances sont des
**codes-candidats** (ex. `CHIR` = Chirac, `JOSP` = Jospin), différents des codes
partisans utilisés par les autres scrutins (ex. `RN`, `SOC`, `LR`).

---

## Table `candidats_presidentielle`

Mapping `(nom, annee) → bloc` pour les présidentielles **sans nuances** (2017 et 2022).

| Colonne | Type | Description |
|---------|------|-------------|
| `annee` | `INTEGER` PK | Année de la présidentielle |
| `nom` | `VARCHAR` PK | Nom de famille EXACT du Parquet (MAJUSCULES, ex. `'LE PEN'`) |
| `prenom` | `VARCHAR` | Prénom |
| `bloc` | `VARCHAR` NN | FK → `blocs_politiques.bloc` |
| `libelle` | `VARCHAR` | Nom complet lisible (`'Marine Le Pen'`) |

**Couverture** : 11 candidats 2017 + 12 candidats 2022 = 23 entrées.

---

## Jointure bloc pour la visualisation

Pour obtenir le bloc de chaque résultat, la requête varie selon le scrutin :

```sql
-- Scrutins avec nuances (hors présidentielles 2017/2022)
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

## Choix éditoriaux — blocs politiques

Le classement de chaque candidat ou nuance dans un bloc est une **décision éditoriale**.
Plusieurs cas sont ambigus et pourraient être classés différemment selon le prisme utilisé :

| Candidat / Nuance | Classé en | Alternative défendable |
|-------------------|-----------|----------------------|
| MÉLENCHON (2012, 2017, 2022) | `gauche` | `extreme_gauche` (FI/Front de Gauche) |
| ROUSSEL Fabien (2022) | `gauche` | `extreme_gauche` (PCF) |
| DUPONT-AIGNAN (2012, 2017, 2022) | `droite` | `extreme_droite` (Debout la France) |
| VILL / Villiers (2007) | `droite` | `extreme_droite` (MPF, souverainiste conservateur) |
| BOVE / Bové (2007) | `gauche` | `extreme_gauche` (altermondialiste) |
| LEPA / Lepage (2002) | `ecologistes` | `centre` (Cap21, libéralisme écologique) |
| ASSELINEAU (2017) | `divers` | `droite` (UPR, souverainiste) |

Ces choix sont délibérément documentés ici pour pouvoir être révisés collectivement.
Toute modification doit être discutée et tracée (commit + commentaire dans le code).
