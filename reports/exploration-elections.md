# Exploration des données électorales agrégées — Phase C1

**Date** : 2026-05-27
**Source** : data.gouv.fr — Données des élections agrégées
**Fichiers** : `data/exploration/general-results.parquet` (153,9 MB) et `data/exploration/candidats-results.parquet` (67,6 MB)

---

## 1. Format des codes communes

Le champ `code_commune` est en **VARCHAR 5 caractères avec zéro-padding** dans les deux fichiers.

```
'01001'  ✓  département 01, commune 001
'59606'  ✓  Valenciennes
```

Compatible avec les conventions INSEE du projet — aucune conversion nécessaire.

Le champ `code_departement` est en VARCHAR sans padding (ex. `'59'`, `'2A'`, `'971'`).

---

## 2. Élections disponibles

**56 scrutins** couvrant 1999 à 2026, répartis en 7 types :

| Type | Sigle | Nb scrutins | Années |
|------|-------|-------------|--------|
| Législatives | `legi` | 12 (6×t1+t2) | 2002–2024 |
| Présidentielles | `pres` | 10 (5×t1+t2) | 2002–2022 |
| Cantonales | `cant` | 8 (4×t1+t2) | 2001–2011 |
| Régionales | `regi` | 8 (4×t1+t2) | 2004–2021 |
| Municipales | `muni` | 8 (4×t1+t2) | 2008–2026 |
| Européennes | `euro` | 6 | 1999–2024 |
| Départementales | `dpmt` | 4 (2×t1+t2) | 2015–2021 |

Format `id_election` : `YYYY_type_tN` (ex. `2022_pres_t1`).

---

## 3. Nuances politiques

### 3.1 Présence de la colonne `nuance`

La colonne `nuance` existe dans `general-results` mais est **entièrement NULL pour 5 scrutins** :

| Élection | Lignes | Nuances |
|----------|--------|---------|
| 2017_pres_t1 | 761 662 | 0 (NULL) |
| 2017_pres_t2 | 138 484 | 0 (NULL) |
| 2019_euro_t1 | 2 356 098 | 0 (NULL) |
| 2022_pres_t1 | 836 184 | 0 (NULL) |
| 2022_pres_t2 | 139 364 | 0 (NULL) |

→ Les présidentielles 2017 et 2022 ainsi que les européennes 2019 n'ont **pas de nuance** dans ce dataset. Les candidats sont identifiés uniquement par `nom`, `prenom` et `no_panneau`.

Pour les présidentielles antérieures (2002–2012), les nuances sont présentes.

### 3.2 Exemples de nuances

**2022_legi_t1** (16 nuances) :
```
DIV, DSV, DVC, DVD, DVG, DXD, DXG, ECO, ENS, LR, NUP, RDG, REC, REG, RN, UDI
```

**2024_legi_t1** (22 nuances) :
```
COM, DIV, DSV, DVC, DVD, DVG, ECO, ENS, EXD, EXG, FI, HOR, LR, RDG, REC,
REG, RN, SOC, UDI, UG, UXD, VEC
```

**Nuances les plus fréquentes (tout scrutin confondu)** :
`LDIV`, `LEXG`, `DIV`, `NC`, `LDVD`, `LDV`, `LFN`, `EXG`, `LDVG`, `SOC`

→ Les nuances varient par scrutin et par période. Une **table d'harmonisation `(nuance, année) → bloc politique`** sera indispensable pour comparer les résultats dans le temps.

---

## 4. Volumes et filtrage géographique

### 4.1 Volume global

| Fichier | Lignes | Taille |
|---------|--------|--------|
| `general-results` (candidats) | 27 524 743 | 153,9 MB |
| `candidats-results` (participation) | 3 162 440 | 67,6 MB |

### 4.2 Département 59 (Nord)

| Fichier | Lignes |
|---------|--------|
| `general-results` | 762 106 |
| `candidats-results` | 91 256 |

### 4.3 Circo 21 — département 59

La circonscription 21 du Nord représente **1 052 bureaux de vote** dans `candidats-results`.

### 4.4 Valenciennes (code_commune = '59606')

Présente dans les deux fichiers. Exemple sur `2026_muni_t2` :

`candidats-results` (participation par bureau) :
```
inscrits=1 117, votants=606, exprimes=581  (bv 1)
inscrits=1 173, votants=668, exprimes=630  (bv 2)
```

`general-results` (résultats candidat par bureau) :
```
nuance=LDVD, nom=DEGALLAIX, voix=243  (bv 1)
nuance=LDVD, nom=DEGALLAIX, voix=257  (bv 2)
```

---

## 5. Surprises et points d'attention

### 5.1 Nommage inversé des fichiers (CRITIQUE)

Le nommage des deux Parquet est **contre-intuitif** :

| Fichier nommé | Contenu réel |
|--------------|--------------|
| `general-results.parquet` | Résultats **par candidat** (nom, prénom, nuance, voix) |
| `candidats-results.parquet` | Résultats **de participation** (inscrits, votants, abstentions…) |

→ Dans le schéma DuckDB, renommer en `resultats_candidats` et `resultats_participation` pour éviter toute confusion.

### 5.2 Nuances absentes pour présidentielles récentes

Les présidentielles 2017 et 2022 n'ont pas de nuance. Pour filtrer par bloc politique, il faudra soit :
- Créer une table de correspondance `nom_candidat → nuance_fictive`
- Utiliser `no_panneau` comme identifiant candidat

### 5.3 Granularité différente selon le fichier

- `general-results` : une ligne = un **candidat** dans un **bureau de vote** → peut contenir plusieurs lignes par bureau
- `candidats-results` : une ligne = un **bureau de vote** → une seule ligne par bureau par élection

La jointure se fait sur `(id_election, code_departement, code_commune, code_bv)`.

### 5.4 Couverture temporelle incomplète pour certains types

- Cantonales : couverture 2001–2011 uniquement (remplacées par les départementales en 2015)
- Pas de présidentielles 2012 dans `candidats-results` à vérifier
- 2026_muni_t2 déjà présent → dataset mis à jour en temps quasi-réel

---

## 6. Recommandations de schéma DuckDB

### Tables à créer

```sql
-- Participation par bureau (ex-candidats-results)
CREATE TABLE resultats_participation (
    id_election       VARCHAR NOT NULL,
    code_departement  VARCHAR NOT NULL,
    code_commune      VARCHAR(5) NOT NULL,
    code_bv           VARCHAR NOT NULL,
    code_circonscription VARCHAR,
    inscrits          INTEGER,
    abstentions       INTEGER,
    votants           INTEGER,
    blancs            INTEGER,
    nuls              INTEGER,
    exprimes          INTEGER,
    -- ratio_* calculables à la volée → ne pas stocker
    PRIMARY KEY (id_election, code_departement, code_commune, code_bv)
);

-- Résultats par candidat (ex-general-results)
CREATE TABLE resultats_candidats (
    id_election       VARCHAR NOT NULL,
    code_departement  VARCHAR NOT NULL,
    code_commune      VARCHAR(5) NOT NULL,
    code_bv           VARCHAR NOT NULL,
    no_panneau        INTEGER NOT NULL,
    nuance            VARCHAR,    -- NULL pour pres 2017, 2022 et euro 2019
    sexe              VARCHAR(1),
    nom               VARCHAR,
    prenom            VARCHAR,
    voix              INTEGER,
    liste             VARCHAR,    -- listes uniquement (euro, regi, muni)
    nom_tete_liste    VARCHAR,
    PRIMARY KEY (id_election, code_departement, code_commune, code_bv, no_panneau)
);

-- Table de référence des élections
CREATE TABLE elections (
    id_election  VARCHAR PRIMARY KEY,
    type         VARCHAR,   -- pres, legi, euro, regi, muni, dpmt, cant
    annee        INTEGER,
    tour         INTEGER,
    libelle      VARCHAR
);

-- Table d'harmonisation des nuances (à construire manuellement)
CREATE TABLE nuances_harmonisees (
    nuance  VARCHAR,
    annee   INTEGER,
    bloc    VARCHAR,   -- gauche, centre, droite, extreme_gauche, extreme_droite, divers
    PRIMARY KEY (nuance, annee)
);
```

### Vues utiles

```sql
-- Score candidat agrégé à la commune (dépasse le bureau)
CREATE VIEW scores_commune AS
SELECT
    rc.id_election,
    rc.code_departement,
    rc.code_commune,
    rc.nuance,
    rc.nom,
    rc.no_panneau,
    SUM(rc.voix) AS voix_commune,
    SUM(rp.exprimes) AS exprimes_commune,
    ROUND(SUM(rc.voix)::FLOAT / NULLIF(SUM(rp.exprimes), 0) * 100, 2) AS pct_exprimes
FROM resultats_candidats rc
JOIN resultats_participation rp
    ON rc.id_election = rc.id_election
    AND rc.code_departement = rp.code_departement
    AND rc.code_commune = rp.code_commune
    AND rc.code_bv = rp.code_bv
GROUP BY ALL;
```

---

## 7. Prochaines étapes (Phase C2)

1. Créer les tables DuckDB dans `ministere.duckdb` (ETL electoral)
2. Charger les deux Parquet en appliquant le renommage
3. Construire la table `elections` (référentiel des 56 scrutins)
4. Construire la table `nuances_harmonisees` pour les scrutins avec nuances
5. Créer les vues `scores_commune` et `scores_circo`
6. Brancher la page Streamlit Élections sur ces tables
