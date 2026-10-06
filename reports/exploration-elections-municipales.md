# Exploration des données électorales — Municipales — Phase D3.1

**Date** : 2026-06-06
**Source** : data.gouv.fr — Données des élections agrégées (mêmes fichiers que présidentielles/législatives)
**Fichiers** : `data/exploration/general-results.parquet` (153,9 MB) et `data/exploration/candidats-results.parquet` (67,6 MB)

---

## 1. Source des fichiers Parquet

Les municipales sont dans les **mêmes fichiers** que les présidentielles et législatives. Pas de téléchargement supplémentaire nécessaire. On filtre par `id_election LIKE '%_muni_%'`.

---

## 2. Structure des colonnes

### general-results.parquet (candidats/listes)

| Colonne | Type | Vs présidentielles / législatives |
|---------|------|----------------------------------|
| `id_election` | VARCHAR | identique |
| `id_brut_miom` | VARCHAR | identique |
| `code_departement` | VARCHAR | identique |
| `code_commune` | VARCHAR | identique |
| `code_bv` | VARCHAR | identique |
| `no_panneau` | INTEGER | identique (numéro de liste) |
| `voix` | INTEGER | identique |
| `ratio_voix_inscrits` | FLOAT | identique |
| `ratio_voix_exprimes` | FLOAT | identique |
| `nuance` | VARCHAR | identique — mais couverture partielle 2026 (voir §5) |
| `sexe` | VARCHAR | identique — mais non pertinent pour les listes |
| `nom` | VARCHAR | identique — NULL pour toutes les municipales |
| `prenom` | VARCHAR | identique — NULL pour toutes les municipales |
| `liste` | VARCHAR | **MUNI uniquement** — rempli 2020_t2 (34.7% HdF), NULL autres |
| `libelle_abrege_liste` | VARCHAR | **MUNI uniquement** — rempli 2026 (100%), NULL 2008/2014/2020 |
| `libelle_etendu_liste` | VARCHAR | **MUNI uniquement** — identique à `libelle_abrege_liste` (2026) |
| `nom_tete_liste` | VARCHAR | NULL pour **tous** les scrutins muni |
| `binome` | VARCHAR | NULL pour tous les scrutins muni |

**Note `prenom_tete_liste`** : absent du schéma Parquet (colonne inexistante, contrairement à ce que le modèle D1.1 laissait supposer).

**Note `nom`/`prenom`** : la structure candidats individuels n'a pas de sens pour les listes municipales. Ces colonnes sont NULL partout.

**Note `liste` vs `libelle_abrege_liste`** : il n'y a pas de colonne unifiée "nom de liste" dans les Parquet. L'identifiant liste varie selon l'année :
- 2008/2014/2020_t1 : aucun nom de liste dans les données (NULL partout)
- 2020_t2 : `liste` remplie (nom de liste court, ex. "Lille Verte 2020 - pour changer - avec Stéphane Baly")
- 2026 : `libelle_abrege_liste` et `libelle_etendu_liste` remplies (identiques, ex. "TOUT POUR LILLE")

### candidats-results.parquet (participation)

Identique aux législatives. Colonnes clés :

| Colonne | Remarque |
|---------|----------|
| `code_circonscription` | **NULL pour tous les scrutins muni** — logique : pas de circonscription dans les municipales |
| `libelle_circonscription` | NULL |
| `libelle_commune` | Rempli |
| `code_canton`, `libelle_canton` | NULL |

---

## 3. Scrutins disponibles

8 scrutins (4 années × 2 tours) — tous présents dans les deux fichiers :

| id_election | Lignes candidats (France) | BV participation (France) |
|-------------|--------------------------|--------------------------|
| 2008_muni_t1 | 109 983 | 25 926 |
| 2008_muni_t2 | 30 545 | 11 862 |
| 2014_muni_t1 | 576 489 | 68 169 |
| 2014_muni_t2 | 115 540 | 22 480 |
| 2020_muni_t1 | 545 351 | 68 941 |
| 2020_muni_t2 | 85 622 | 19 594 |
| 2026_muni_t1 | 196 661 | 70 003 |
| 2026_muni_t2 | 51 541 | 17 398 |

**Observation 2008 vs 2014** : le saut de 109 983 → 576 489 lignes (×5,2) n'est pas dû à une différence de participation — il reflète le changement de seuil légal. En 2008, seules les communes ≥ 3 500 habitants ont eu des élections de liste proportionnelle. En 2014, le seuil a été abaissé à **1 000 habitants** (loi du 17 mai 2013). Voir §5 pour la confirmation empirique.

**Observation 2026 vs 2020** : 196 661 lignes candidats (2026_t1) vs 545 351 (2020_t1). Le nombre de BV participation est quasi identique (70 003 vs 68 941). Cela indique que la colonne `nuance` n'est pas remplie pour les petites communes en 2026 — voir §5 pour l'analyse.

---

## 4. Volumes filtrés HdF

Filtrage via jointure sur `geographies_communes.code_region = '32'` (3 782 communes HdF, cohérent avec les autres scrutins).

### Candidats (general-results)

| Scrutin | Lignes HdF | Communes HdF | Lignes / commune |
|---------|-----------|-------------|-----------------|
| 2008_muni_t1 | 4 215 | 164 | 25,7 |
| 2008_muni_t2 | 1 256 | 50 | 25,1 |
| 2014_muni_t1 | 58 214 | 3 778 | 15,4 |
| 2014_muni_t2 | 12 680 | 778 | 16,3 |
| 2020_muni_t1 | 56 090 | 3 779 | 14,8 |
| 2020_muni_t2 | 8 065 | 560 | 14,4 |
| 2026_muni_t1 | 15 366 | 3 779 | **4,1** ⚠️ |
| 2026_muni_t2 | 3 692 | 182 | 20,3 |

**Note 2026_muni_t1** : 4,1 lignes/commune est anormalement bas par rapport à 2014/2020 (~15). La raison : les petites communes ont 1 ligne par BV (1 seule liste, 1 seul BV) et aucune nuance. Les grandes communes (ex. Lille) ont 128 BV × 9 listes = 1 152 lignes, conformément à 2020.

### Participation (candidats-results)

| Scrutin | BV HdF | Communes HdF |
|---------|-------|-------------|
| 2008_muni_t1 | 1 240 | 164 |
| 2008_muni_t2 | 500 | 50 |
| 2014_muni_t1 | 6 434 | 3 778 |
| 2014_muni_t2 | 2 051 | 778 |
| 2020_muni_t1 | 6 514 | 3 779 |
| 2020_muni_t2 | 1 383 | 560 |
| 2026_muni_t1 | 6 546 | 3 779 |
| 2026_muni_t2 | 1 193 | 182 |

---

## 5. Couverture des nuances

### Taux de nuançage (France entière)

| Scrutin | Total lignes | Avec nuance | NULL nuance | % nuancé |
|---------|-------------|------------|------------|---------|
| 2008_muni_t1 | 109 983 | 109 983 | 0 | 100,0 % |
| 2008_muni_t2 | 30 545 | 30 545 | 0 | 100,0 % |
| 2014_muni_t1 | 576 489 | 576 489 | 0 | 100,0 % |
| 2014_muni_t2 | 115 540 | 115 540 | 0 | 100,0 % |
| 2020_muni_t1 | 545 351 | 545 351 | 0 | 100,0 % |
| 2020_muni_t2 | 85 622 | 85 622 | 0 | 100,0 % |
| 2026_muni_t1 | 196 661 | 147 024 | **49 637** | **74,8 %** ⚠️ |
| 2026_muni_t2 | 51 541 | 48 680 | 2 861 | 94,4 % |

### Répartition 2026 HdF : nuances vs population (2023)

| Tranche de population | Communes avec nuance | Communes sans nuance | Total |
|----------------------|---------------------|---------------------|-------|
| ≥ 3 500 hab | **318** | 0 | 318 |
| 1 000–3 499 hab | 2 | 657 | 659 |
| 500–999 hab | 0 | 758 | 758 |
| < 500 hab | 0 | 2 044 | 2 044 |
| **TOTAL HdF** | **320** | 3 459 | 3 779 |

**Conclusion** : la quasi-totalité des communes ≥ 3 500 hab ont des nuances (318/318). Les communes entre 1 000 et 3 500 hab n'en ont presque pas (2/659). **Les données 2026 sont très probablement incomplètes** : soit la nuançage des petites communes n'a pas encore été finalisé par les préfectures au moment de la publication du Parquet (hypothèse la plus probable, vu que les élections viennent juste de se dérouler), soit le Ministère a décidé de revenir au seuil 3 500 pour le nuançage statistique. À surveiller lors d'une mise à jour Parquet.

**Comparaison 2020** : en 2020, toutes les communes (y compris < 500 hab) avaient la nuance `NC` (Non Classé) — code explicite signifiant "liste sans étiquette politique". En 2026, ces communes ont nuance=NULL (code manquant, pas NC). Ce changement de convention `NC` → `NULL` est structurellement important pour le chargement.

---

## 6. Nuances distinctes par scrutin (HdF)

34 codes de nuances distincts sur l'ensemble des 4 scrutins. **Aucun n'est présent dans `nuances_harmonisees`** (table actuellement peuplée uniquement pour présidentielles et législatives).

### 2008_muni (13 codes)

| Nuance | Fréquence t1 | Signification probable | Bloc cible |
|--------|-------------|----------------------|-----------|
| LDVD | 870 | Divers droite | DTE |
| LUG | 669 | Union de la gauche (coalition) | GAU |
| LDVG | 583 | Divers gauche | GAU |
| LMAJ | 543 | Majorité sortante (gestion locale) | DIV |
| LEXG | 430 | Extrême gauche | EXG |
| LSOC | 341 | Socialiste | GAU |
| LFN | 198 | Front National | EXD |
| LCOM | 192 | Communiste | EXG |
| LCMD | 159 | Communiste / Divers gauche | EXG |
| LVEC | 109 | Verts / Écologistes | GAU |
| LAUT | 96 | Autre | DIV |
| LMC | 20 | Majorité–Centre | CENT |
| LGC | 5 | Gauche–Centre | GAU |

### 2014_muni (18 codes, dont NC)

| Nuance | Fréquence t1 | Signification probable | Bloc cible |
|--------|-------------|----------------------|-----------|
| **NC** | **45 281** | **Non Classé** — liste sans étiquette (petites communes) | *NULL* |
| LDVG | 2 287 | Divers gauche | GAU |
| LDVD | 1 871 | Divers droite | DTE |
| LFN | 1 315 | Front National | EXD |
| LUG | 1 196 | Union de la gauche | GAU |
| LDIV | 1 130 | Divers | DIV |
| LEXG | 1 095 | Extrême gauche | EXG |
| LSOC | 893 | Socialiste | GAU |
| LUD | 859 | Union des démocrates | CENT |
| LFG | 727 | Front de Gauche | GAU |
| LUMP | 557 | UMP (devenu LR en 2015) | DTE |
| LCOM | 360 | Communiste | EXG |
| LVEC | 296 | Verts / Écologistes | GAU |
| LUDI | 206 | Union Divers | DIV |
| LPG | 83 | Parti de Gauche | GAU |
| LEXD | 25 | Extrême droite | EXD |
| LUC | 22 | Union Centre | CENT |
| LMDM | 11 | Mouvement Démocrate | CENT |

### 2020_muni (21 codes, dont NC)

| Nuance | Fréquence t1 | Signification probable | Bloc cible |
|--------|-------------|----------------------|-----------|
| **NC** | **43 074** | Non Classé | *NULL* |
| LDVG | 2 489 | Divers gauche | GAU |
| LNC | 1 787 | Nouveau Centre | CENT |
| LDVD | 1 573 | Divers droite | DTE |
| LRN | 1 268 | Rassemblement National | EXD |
| LEXG | 1 102 | Extrême gauche | EXG |
| LDIV | 1 031 | Divers | DIV |
| LDVC | 900 | Divers Centre | CENT |
| LUG | 607 | Union de la gauche | GAU |
| LVEC | 425 | Verts / Écologistes | GAU |
| LFI | 371 | La France Insoumise | GAU ¹ |
| LLR | 293 | Les Républicains | DTE |
| LUC | 293 | Union Centre | CENT |
| LCOM | 277 | Communiste | EXG |
| LECO | 198 | Écologiste | GAU |
| LSOC | 130 | Socialiste | GAU |
| LREM | 119 | La République En Marche | CENT |
| LUDI | 106 | Union Divers | DIV |
| LUD | 34 | Union des Démocrates | CENT |
| LRDG | 9 | Radicaux de Gauche | GAU |
| LEXD | 4 | Extrême droite | EXD |

¹ LFI classé **GAU** pour 2020 — bascule vers **EXG** uniquement à partir de 2026 (INTP2602966C + CE 27/02/2026).

### 2026_muni (19 codes, pas de NC)

| Nuance | Fréquence t1 HdF | Signification | Bloc cible |
|--------|-----------------|---------------|-----------|
| LDVG | 1 650 | Divers gauche | GAU |
| LDVD | 1 589 | Divers droite | DTE |
| LEXG | 1 116 | Extrême gauche | EXG |
| LRN | 1 104 | Rassemblement National | EXD |
| LDVC | 1 004 | Divers Centre | CENT |
| LUG | 896 | Union de la Gauche (NFP) | GAU |
| LDIV | 861 | Divers | DIV |
| **LFI** | **702** | **La France Insoumise — EXG depuis INTP2602966C** | **EXG** ² |
| LVEC | 245 | Verts / Écologistes | GAU |
| LUC | 181 | Union Centre | CENT |
| LLR | 150 | Les Républicains | DTE |
| LSOC | 139 | Socialiste | GAU |
| LEXD | 138 | Extrême droite | EXD |
| LCOM | 129 | Communiste | EXG |
| LUXD | 60 | Union Extrême Droite (UDR + alliés) | EXD |
| LUDI | 43 | Union Divers | DIV |
| LUDR | 24 | Union Droite Républicaine (UDR Ciotti) | EXD ³ |
| LECO | 8 | Écologiste | GAU |
| LHOR | 4 | Horizons (parti d'Édouard Philippe) | CENT |

² LFI → **EXG** confirmé par CE 27 fév. 2026, applicable à compter des municipales 2026.
³ LUDR = nouveau code 2026, parti de Nicolas Ciotti, allié RN — **EXD** selon INTP2602966C.

---

## 7. Plan de migration schéma (D3.2)

### Option A — Extension de `resultats_candidats`

Ajouter `libelle_liste VARCHAR` et accepter la redondance par BV :

```sql
ALTER TABLE resultats_candidats ADD COLUMN IF NOT EXISTS libelle_liste VARCHAR;
```

Peuplé à partir de `COALESCE(libelle_abrege_liste, liste)` au chargement selon l'année.

**Avantage** : pas de nouvelle table, jointure directe. **Inconvénient** : redondance (même libellé pour tous les BV d'une liste dans une commune).

### Option B — Table `listes_municipales` (recommandée)

```sql
CREATE TABLE IF NOT EXISTS listes_municipales (
    id_election       VARCHAR NOT NULL,
    code_commune      VARCHAR NOT NULL,
    no_panneau        INTEGER NOT NULL,
    nuance            VARCHAR,
    libelle_liste     VARCHAR,
    PRIMARY KEY (id_election, code_commune, no_panneau)
);
```

Agrégée 1 ligne par (scrutin, commune, liste) — sans BV. Peuplée par `GROUP BY` sur general-results au chargement.

**Avantage** : propre, sans redondance. Le tableau UI "résultats par liste" peut requêter cette table directement. **Inconvénient** : une jointure supplémentaire pour les analyses BV × libellé.

### Recommandation : **Option B**

Pour les municipales, l'unité significative pour l'UI est la **liste** (pas le candidat individuel). Une table dédiée est plus cohérente avec le scrutin de liste. La table `resultats_candidats` garde son rôle BV-level, et `listes_municipales` porte les métadonnées liste.

### Vues à créer (analogues aux vues legi)

- `v_scores_commune_muni` : voix par (code_commune, bloc, annee, tour) — vue agrégée
- `v_participation_commune_muni` : participation par commune × scrutin
- `v_evolution_blocs_hdf_muni` : évolution temporelle HdF

### Extension `nuances_harmonisees`

34 nouvelles entrées `(nuance, annee, bloc)` à créer, avec sémantique datée :
- LFI : `(LFI, 2020, GAU)` et `(LFI, 2026, EXG)` — deux entrées pour la bascule
- NC : recommandation de ne pas mapper (laisser bloc=NULL signifiant "non classé")
- LMAJ : idem (liste de gestion locale, non classifiable)

---

## 8. Sources officielles

| Scrutin | Circulaire connue | NOR | Statut |
|---------|------------------|-----|--------|
| 2026 | **INTP2602966C** — Municipales 2026 (2 fév. 2026) | INTP2602966C | ✅ **Archivée** dans `docs/sources-officielles/nuances/` |
| 2020 | Circulaire MIOM nuançage muni 2020 | INTA2003088C (probable) | ❓ À vérifier Légifrance |
| 2014 | Circulaire MIOM nuançage muni 2014 | NOR inconnu | ❓ À investiguer |
| 2008 | Circulaire MIOM nuançage muni 2008 | NOR inconnu | ❓ À investiguer |

**Note 2026** : circulaire déjà archivée, décision CE 27/02/2026 archivée dans l'index. LFI → EXG et LUDR → EXD validés juridiquement.

**Note 2020** : le NOR INTA2003088C est une hypothèse (format standard MIOM + année). Légifrance conserve les circulaires depuis le décret 2014-1479. L'existence d'un PDF public est probable.

**Note 2014 et 2008** : circulaires antérieures au décret 2014-1479, potentiellement non publiées publiquement. Même situation que pour les législatives 2002-2012.

---

## 9. Pièges identifiés

### PIÈGE 1 — 2026 nuances incomplètes [CRITIQUE]

Les données 2026 n'ont des nuances que pour les communes ≥ 3 500 hab (318 communes sur 3 779 HdF). Deux hypothèses :
- **H1 (plus probable)** : le Parquet a été mis à disposition avant la finalisation du nuançage pour les petites communes. À re-télécharger après consolidation (délai habituel : 1–3 mois après le scrutin).
- **H2** : le Ministère a décidé de ne plus nuancer les communes < 3 500 hab pour les municipales.

**Action** : ne pas charger les données 2026 comme "définitives". Marquer ce scrutin comme `donnees_provisoires = TRUE` dans la table `elections`. Prévoir une re-importation.

### PIÈGE 2 — NC ≠ NULL : changement de convention 2020→2026 [IMPORTANT]

En 2008/2014/2020, les listes sans étiquette politique ont le code nuance `NC` (Non Classé). En 2026, les mêmes situations ont nuance=`NULL`. Ce changement de convention nécessite une gestion explicite dans les requêtes : `WHERE nuance IS NOT NULL AND nuance != 'NC'` pour filtrer les listes non politiques.

### PIÈGE 3 — Colonnes "liste" incohérentes entre scrutins [IMPORTANT]

Il n'y a pas de colonne unifiée "nom de liste" :
- 2008/2014/2020_t1 : aucun nom de liste disponible dans le Parquet
- 2020_t2 : colonne `liste` remplie
- 2026 : colonnes `libelle_abrege_liste` et `libelle_etendu_liste` remplies

Le chargement devra mapper : `COALESCE(libelle_abrege_liste, liste, NULL) AS libelle_liste` selon l'année.

### PIÈGE 4 — LMAJ (Majorité en place) [MINEUR]

`LMAJ` est un code spécifique aux municipales : "liste de la majorité sortante" (présent en 2008 uniquement dans ce dataset). Ce n'est pas une nuance politique classifiable. À traiter comme `NC` : ne pas mapper en bloc, ou mapper `DIV` avec une note.

### PIÈGE 5 — Communes nouvelles (7 codes affectés) [MINEUR]

| Code | Situation | Impact |
|------|-----------|--------|
| 60070 | Absent en 2026 (absorbé ?) | Série temporelle 2014/2020 interrompue |
| 62600 | Absent en 2026 | Idem |
| 80491 | Absent en 2026 | Idem |
| 02198 | Nouveau en 2020 | Commune nouvelle créée entre 2014 et 2020 |
| 60588 | Nouveau en 2026 | Commune nouvelle créée entre 2020 et 2026 |
| 62216 | Nouveau en 2026 | Idem |
| 62659 | Nouveau en 2026 | Idem |

Impact faible : 7 communes sur 3 782. Les jointures sur code_commune restent valides pour les 3 772 communes présentes dans les 3 scrutins 2014/2020/2026.

### PIÈGE 6 — `nom`/`prenom` NULL pour toutes les muni [MINEUR]

Contrairement aux présidentielles, la structure "candidat individuel" n'existe pas dans les municipales de liste. Les colonnes `nom`/`prenom` sont NULL. L'identifiant d'une liste est `(id_election, code_commune, no_panneau)`.

### PIÈGE 7 — LFI bascule EXG en 2026 [DÉCISION STRUCTURANTE]

La circulaire INTP2602966C et la décision CE 27/02/2026 ont validé le classement LFI en extrême gauche pour les scrutins à partir de 2026. Pour 2020, LFI reste classé GAU. La table `nuances_harmonisees` devra avoir **deux entrées** pour LFI :
- `(LFI, 2020, GAU)`
- `(LFI, 2026, EXG)`

Cette double entrée est cohérente avec le principe de classement "de l'époque" de l'ADR-0005.

### PIÈGE 8 — LUDR (nouveau code 2026) à documenter [IMPORTANT]

`LUDR` (Union Droite Républicaine) = parti de Nicolas Ciotti, allié du RN. Classé **EXD** par INTP2602966C et validé CE 27/02/2026 avec LUDR/UXD. Code inexistant avant 2026.

---

## 10. Recommandations pour D3.2 (chargement)

1. **Re-télécharger les Parquet avant D3.2** : les données 2026 sont probablement en cours de consolidation (nuances manquantes pour communes < 3 500 hab). Vérifier la date de mise à jour sur data.gouv.fr.

2. **Nouveau script `scripts/load_elections_municipales.py`** :
   - Filtrage HdF via `geographies_communes.code_region = '32'`
   - Gestion des colonnes liste : `COALESCE(libelle_abrege_liste, liste)` selon l'année
   - Marquage `donnees_provisoires` pour 2026

3. **`ALTER TABLE elections`** : ajouter `donnees_provisoires BOOLEAN DEFAULT FALSE` pour signaler les scrutins dont les données sont partielles.

4. **Table `listes_municipales`** (Option B recommandée) : agrégation 1 ligne / (scrutin, commune, liste) — sans BV.

5. **Extension `nuances_harmonisees`** :
   - 34 nouvelles entrées muni (voir §6)
   - Traitement spécial NC : `bloc = NULL` (non classifiable)
   - LMAJ : idem ou `bloc = 'DIV'` selon décision Mathias
   - LFI double entrée : 2020→GAU, 2026→EXG

6. **Seuil 2008 à documenter dans l'UI** : afficher une note "Seules les communes > 3 500 habitants (164 communes HdF) ont des données pour les élections de 2008" dans la section municipales.

7. **Circulaires manquantes** : rechercher INTA2003088C (2020) sur Légifrance. Si trouvée, archiver dans `docs/sources-officielles/nuances/`. Pour 2008/2014, même démarche que pour les législatives historiques (ADR-0005 § reconstruction logique).

8. **Ne pas bloquer D3.2 sur les nuances 2026** : les 318 communes HdF ≥ 3 500 avec nuances représentent l'essentiel de l'intérêt politique (Lille, Valenciennes, Amiens, Douai, Lens, Calais...). Le reste peut attendre la mise à jour du Parquet.
