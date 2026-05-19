# Rapport d'intégrité ETL — ministere-de-l-info
Date : 2026-05-19

## Tables géographiques

| Table | Count | Géométries valides | Géométries NULL | Statut |
|-------|-------|--------------------|-----------------|--------|
| geographies_regions | 18 | 18/18 | 0 | ✅ |
| geographies_departements | 101 | 101/101 | 0 | ✅ |
| geographies_epci | 1 265 | 1 265/1 265 | 0 | ✅ |
| geographies_communes | 34 877 | 34 877/34 877 | 0 | ✅ |
| geographies_arrondissements_municipaux | 45 | 45/45 | 0 | ✅ |
| geographies_circonscriptions | 559 | 559/559 | 0 | ✅ |

## Cohérence FK conceptuelles

| Relation | Orphelins | Statut | Note |
|----------|-----------|--------|------|
| departements → regions | 0 | ✅ | |
| communes → departements | 2 | ⚠️ attendu | SPM (97501, 97502) — code_departement='NR' |
| communes → regions | 2 | ⚠️ attendu | SPM (97501, 97502) — code_region='NR' |
| communes → epci (non-NULL) | 135 | ⚠️ attendu | Grand Paris : codes_siren multi-valeur WFS |
| arm → communes_meres | 0 | ✅ | |
| populations 2023 → communes | 19 | ✅ | Communes fusionnées COG (≤ 50 accepté) |

## Populations 2023

| Commune | Code | Population municipale | Fourchette attendue | Statut |
|---------|------|-----------------------|---------------------|--------|
| Paris | 75056 | 2 103 778 | 2.0M – 2.5M | ✅ |
| Lyon | 69123 | 519 127 | 0.4M – 0.7M | ✅ |
| Marseille | 13055 | 886 040 | 0.7M – 1.1M | ✅ |
| Somme nationale (17 régions) | — | 68 094 280 | 60M – 70M | ✅ |

## Vues d'agrégation

| Vue | Lignes 2023 | Attendu | Statut |
|-----|-------------|---------|--------|
| v_population_commune | 34 858 | = COUNT(populations 2023) | ✅ |
| v_population_region | 17 | 17 (Mayotte exclue) | ✅ attendu |
| v_population_departement | 100 | 100 (Mayotte exclue) | ✅ attendu |
| v_population_epci | 1 249 | ~1 249 | ✅ |

## Métadonnées _etl_metadata

| Entrée | row_count | COUNT(*) réel | Statut |
|--------|-----------|---------------|--------|
| geographies_regions | 18 | 18 | ✅ |
| geographies_departements | 101 | 101 | ✅ |
| geographies_epci | 1 265 | 1 265 | ✅ |
| geographies_communes | 34 877 | 34 877 | ✅ |
| geographies_arrondissements_municipaux | 45 | 45 | ✅ |
| geographies_circonscriptions | 559 | 559 | ✅ |
| populations_2023 | 34 858 | 34 858 | ✅ |

## Anomalies connues (non critiques)

### 1. Mayotte absente des vues population
**Impact :** `v_population_region` : 17/18 régions · `v_population_departement` : 100/101
**Cause :** `DS_POPULATIONS_HISTORIQUES` (source INSEE utilisée) ne couvre pas Mayotte —
les données démographiques mahoraises sont publiées séparément par l'INSEE.
**Action :** chargement via source alternative à planifier en v2.

### 2. Saint-Pierre-et-Miquelon dans les communes
**Impact :** 2 communes (97501, 97502) avec `code_departement='NR'` et `code_region='NR'`
**Cause :** SPM est une Collectivité d'Outre-Mer (COM), non couverte par les départements
ADMIN-EXPRESS. Le WFS IGN retourne ces communes avec le code 'NR' (Non Renseigné).
**Action :** filtrage optionnel à la carte — non bloquant.

### 3. Communes du Grand Paris avec code_epci multi-valeur
**Impact :** 135 communes avec `code_epci` de la forme `"200054781/200058014"`
**Cause :** le champ WFS `codes_siren_des_epci` est multi-valeur pour les communes
appartenant à la fois à la Métropole du Grand Paris (MGP, SIREN 200054781) et à un EPT.
L'ETL stocke la valeur brute sans parser le premier SIREN.
**Action :** parsage du premier SIREN dans `_load_communes()` — correctif ETL v2.

### 4. 11 EPT du Grand Paris sans code_departement_principal
**Impact :** `code_departement_principal = NULL` pour les 11 EPT
**Cause :** la dérivation post-load via `UPDATE geographies_epci SET code_departement_principal = (SELECT...)`
ne peut pas résoudre les communes à code_epci multi-valeur (anomalie 3 ci-dessus).
**Action :** dépend du correctif anomalie 3.

### 5. `comptee_a_part` et `totale` : 100% NULL
**Impact :** colonnes inutilisables pour l'instant
**Cause :** PCAP (Population Comptée À Part) absent de `DS_POPULATIONS_HISTORIQUES`.
Seule `population_municipale` est fiable.
**Action :** chargement PCAP séparé en v2.

## Résumé tests smoke

62 tests pytest · 62 passent · 0 échecs · durée : ~1s
Fichier : `tests/test_etl_smoke.py`
