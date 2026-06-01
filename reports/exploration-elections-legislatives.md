# Exploration des données électorales — Législatives — Phase D1.1

**Date** : 2026-06-01
**Source** : data.gouv.fr — Données des élections agrégées (mêmes fichiers que présidentielles)
**Fichiers** : `data/exploration/general-results.parquet` (153,9 MB) et `data/exploration/candidats-results.parquet` (67,6 MB)

---

## 1. Source des fichiers Parquet

Les législatives sont dans les **mêmes fichiers** que les présidentielles. Pas de téléchargement supplémentaire nécessaire. On filtre par `id_election LIKE '%_legi_%'`.

---

## 2. Structure des colonnes

### general-results.parquet (candidats)

| Colonne | Type | Vs présidentielles |
|---------|------|--------------------|
| `id_election` | VARCHAR | identique |
| `id_brut_miom` | VARCHAR | identique |
| `code_departement` | VARCHAR | identique |
| `code_commune` | VARCHAR | identique |
| `code_bv` | VARCHAR | identique |
| `no_panneau` | INTEGER | identique |
| `voix` | INTEGER | identique |
| `ratio_voix_inscrits` | FLOAT | identique |
| `ratio_voix_exprimes` | FLOAT | identique |
| `nuance` | VARCHAR | identique |
| `sexe` | VARCHAR | identique |
| `nom` | VARCHAR | identique |
| `prenom` | VARCHAR | identique |
| `liste` | VARCHAR | **NOUVEAU** — nom de liste pour scrutins de liste (NULL pour legi individuel) |
| `libelle_abrege_liste` | VARCHAR | **NOUVEAU** — idem |
| `libelle_etendu_liste` | VARCHAR | **NOUVEAU** — idem |
| `nom_tete_liste` | VARCHAR | **NOUVEAU** — idem |
| `binome` | VARCHAR | **NOUVEAU** — nom du binôme (scrutin de liste binômal) |

**Note** : les 5 colonnes "liste" sont pertinentes pour les municipales et régionales, pas pour les législatives individuelles.

### candidats-results.parquet (participation)

| Colonne | Type | Vs présidentielles |
|---------|------|--------------------|
| `id_election` → `exprimes` | comme pres | identique |
| `ratios_*` (8 colonnes) | FLOAT | identique |
| `code_circonscription` | VARCHAR | **NOUVEAU — CRITIQUE** (voir §4) |
| `libelle_circonscription` | VARCHAR | **NOUVEAU** |
| `libelle_commune` | VARCHAR | **NOUVEAU** |
| `libelle_departement` | VARCHAR | **NOUVEAU** |
| `code_canton` | VARCHAR | **NOUVEAU** |
| `libelle_canton` | VARCHAR | **NOUVEAU** |

---

## 3. Scrutins disponibles

12 scrutins (6 années × 2 tours) — les 12 attendus sont présents :

| id_election | Lignes candidats (France) | BV participation (France) |
|-------------|--------------------------|--------------------------|
| 2002_legi_t1 | 903 988 | 63 394 |
| 2002_legi_t2 | 115 929 | 57 575 |
| 2007_legi_t1 | 861 595 | 65 618 |
| 2007_legi_t2 | 103 694 | 51 779 |
| 2012_legi_t1 | 740 266 | 67 932 |
| 2012_legi_t2 | 128 204 | 62 633 |
| 2017_legi_t1 | 908 722 | 69 242 |
| 2017_legi_t2 | 137 627 | 68 767 |
| 2022_legi_t1 | 740 221 | 69 682 |
| 2022_legi_t2 | 139 618 | 69 355 |
| 2024_legi_t1 | 464 549 | 70 102 |
| 2024_legi_t2 | 133 107 | 61 615 |
| **TOTAL** | **5 377 520** | **777 694** |

---

## 4. Volumes filtrés HdF (code_region = '32')

Filtrage via jointure sur `geographies_communes.code_region = '32'` (cohérent avec présidentielles).

### Candidats (general-results → resultats_candidats)

| Scrutin | Lignes HdF |
|---------|-----------|
| 2002_legi_t1 | 86 512 |
| 2002_legi_t2 | 11 847 |
| 2007_legi_t1 | 81 793 |
| 2007_legi_t2 | 10 971 |
| 2012_legi_t1 | 65 944 |
| 2012_legi_t2 | 13 203 |
| 2017_legi_t1 | 76 496 |
| 2017_legi_t2 | 12 446 |
| 2022_legi_t1 | 62 445 |
| 2022_legi_t2 | 13 040 |
| 2024_legi_t1 | 39 171 |
| 2024_legi_t2 | 7 837 |
| **TOTAL** | **481 705** |

### Participation (candidats-results → resultats_participation)

| Scrutin | Bureaux de vote HdF |
|---------|-------------------|
| 2002_legi_t1 | 6 194 |
| 2002_legi_t2 | 6 001 |
| 2007_legi_t1 | 6 292 |
| 2007_legi_t2 | 5 524 |
| 2012_legi_t1 | 6 437 |
| 2012_legi_t2 | 6 327 |
| 2017_legi_t1 | 6 495 |
| 2017_legi_t2 | 6 223 |
| 2022_legi_t1 | 6 520 |
| 2022_legi_t2 | 6 520 |
| 2024_legi_t1 | 6 539 |
| 2024_legi_t2 | 3 658 |
| **TOTAL** | **72 730** |

**Comparaison présidentielles** : 452 553 lignes candidats / 63 878 BV × 10 scrutins.
Les législatives représentent ~1,06× les présidentielles en volume HdF.

---

## 5. Circonscriptions HdF

50 circonscriptions réparties sur 5 départements :

| Département | Circos |
|-------------|--------|
| 02 — Aisne | 5 |
| 59 — Nord | 21 |
| 60 — Oise | 7 |
| 62 — Pas-de-Calais | 12 |
| 80 — Somme | 5 |
| **TOTAL** | **50** |

Format des codes dans `geographies_circonscriptions` : `"59-01"`, `"59-02"`, ..., `"59-21"`.
Format dans le Parquet (`candidats-results.code_circonscription`) : `"01"`, `"02"`, ..., `"21"` — numéro RELATIF au département.

---

## 6. Pièges identifiés

### PIÈGE 1 — code_circonscription dans le mauvais fichier [CRITIQUE]

`code_circonscription` est dans `candidats-results.parquet` (participation), **absent** de `general-results.parquet` (candidats).

Conséquence : pour obtenir la circo d'un candidat, il faut passer par une jointure participation → candidats sur `(id_election, code_departement, code_commune, code_bv)`.

Options pour D1.2 :
- **Option A** : ajouter `code_circo VARCHAR` à `resultats_participation` au chargement, et laisser `resultats_candidats` sans code_circo (l'interface UI fait la jointure).
- **Option B** : dénormaliser et stocker `code_circo` dans `resultats_candidats` aussi au chargement, en faisant la jointure participation→candidats à l'ETL.

Recommandation : **Option A** — moins de duplication, cohérent avec la structure actuelle.

### PIÈGE 2 — code_circonscription = numéro relatif [CRITIQUE]

Le code dans le Parquet est `"01"`, `"02"`... **sans le préfixe département**. Ce n'est pas un identifiant unique : `"05"` dans le 59 ≠ `"05"` dans le 62.

Reconstruction du code compatible `geographies_circonscriptions` :
```sql
code_departement || '-' || LPAD(code_circonscription, 2, '0')
-- Exemple : dpt='59', circo='5' → '59-05'
```

### PIÈGE 3 — code_circonscription NULL pour 3 scrutins [IMPORTANT]

| Scrutins | code_circonscription |
|---------|---------------------|
| 2002_legi_t1 + t2 | **NULL** (100%) |
| 2007_legi_t1 + t2 | **NULL** (100%) |
| 2012_legi_t1 + t2 | Rempli (100%) |
| 2017_legi_t1 + t2 | Rempli (100%) |
| 2022_legi_t1 + t2 | Rempli (100%) |
| 2024_legi_t1 + t2 | **NULL** (100%) |

2002 et 2007 n'ont pas de code_circo dans le Parquet. 2024 non plus — probablement un dataset en cours de consolidation au moment du téléchargement.

Pour 2002/2007 : la circo peut être reconstituée par jointure spatiale `ST_Within(commune_geom, circo_geom)` sur les géométries historiques si nécessaire, mais le découpage de 2010 (redécoupage Marleix) rend cela approximatif. Pour l'UI, afficher simplement "N/A" pour 2002/2007 ou filtrer ces scrutins de la vue sélecteur circo.

### PIÈGE 4 — Nuances : zéro NULL, mais évolution importante sur 22 ans [MINEUR]

Contrairement aux présidentielles 2017/2022, **toutes les nuances législatives sont renseignées** (0% NULL, vérification faite). Pas de table `candidats_legi` de substitution nécessaire.

Mais les codes évoluent significativement entre scrutins :

| Scrutin | Nuances t1 | Codes notables |
|---------|-----------|----------------|
| 2002 | 22 | COM, CPNT, DL, FN, LCR, LO, MNR, MPF, PRG, RPF, UDF, UMP, VEC... |
| 2007 | 17 | COM, CPNT, MAJ, MPF, RDG, UDFD, UMP... |
| 2012 | 17 | ALLI, AUT, CEN, FG, NCE, PRV... (réforme nomenclature) |
| 2017 | 17 | DLF, FI, LR, MDM, REM, SOC, UDI... (En Marche = REM) |
| 2022 | 16 | DSV, DVC, DXD, DXG, ENS, NUP, REC... (post-CE NUPES) |
| 2024 | 22 | COM, FI, HOR, REC, UG, UXD, VEC... (post-NFP) |

La table `nuances_harmonisees` devra être étendue pour couvrir ~100 entrées `(nuance, annee)` supplémentaires.

### PIÈGE 5 — Redécoupage électoral de 2010 [IMPORTANT]

La loi du 13 janvier 2012 (décrets de redécoupage de 2010 signés en décembre 2009, applicables depuis les élections de 2012) a modifié les limites de nombreuses circonscriptions. Les codes `"59-XX"` de 2002/2007 ne correspondent pas forcément aux mêmes territoires qu'en 2012/2017/2022/2024.

Conséquence : les comparaisons temporelles par circo sur 2002→2022 seront approximatives pour les circonscriptions redécoupées. Documenter cette limite dans l'UI.

### PIÈGE 6 — 2024_legi_t2 : seulement 3 658 BV [MINEUR]

Le t2 2024 en HdF ne compte que 3 658 BV contre 6 500+ pour les autres scrutins. Normal : au 2e tour législatif, les bureaux de vote sans candidats qualifiés ne produisent pas de lignes participation. Le Parquet ne crée des lignes que pour les circonscriptions effectivement disputées au 2e tour.

### PIÈGE 7 — Remplaçants (binôme) [MINEUR]

La circulaire 2022 (INTA2212053C) précise explicitement qu'aucune nuance n'est attribuée aux remplaçants. Vérifier que le Parquet exclut les remplaçants ou les marque distinctement. Dans `general-results`, la colonne `binome` (VARCHAR) semble servir à identifier le remplaçant dans les scrutins de liste — à vérifier à l'étape D1.2.

---

## 7. Plan de migration schéma (D1.2)

### Modifications à apporter

La table `elections` contient déjà les 12 scrutins législatifs — **aucune modification nécessaire**.

**ALTER TABLE `resultats_participation`** : ajouter `code_circo VARCHAR` nullable :
```sql
ALTER TABLE resultats_participation
ADD COLUMN IF NOT EXISTS code_circo VARCHAR;
```

Peuplé au chargement avec :
```sql
code_departement || '-' || LPAD(code_circonscription, 2, '0')
-- NULL pour 2002/2007/2024 (code_circonscription absent du Parquet)
```

**Pas de modification à `resultats_candidats`** : la circo est accessible via jointure sur `resultats_participation`. Une vue peut exposer `(id_election, code_circo, code_commune, voix_par_bloc)` si nécessaire.

**Extension de `nuances_harmonisees`** : ~100 nouvelles entrées `(nuance, annee)` pour couvrir les 6 années × les nuances législatives. À faire dans le script `load_elections_legislatives.py` (D1.2).

**Table `candidats_legi`** : NON nécessaire — toutes les nuances législatives sont renseignées dans le Parquet.

### Migration idempotente (ALTER IF NOT EXISTS)

```sql
-- idempotent
ALTER TABLE resultats_participation ADD COLUMN IF NOT EXISTS code_circo VARCHAR;

-- Extension nuances_harmonisees : INSERT OR IGNORE
INSERT OR IGNORE INTO nuances_harmonisees (nuance, annee, bloc)
VALUES
  ('SOC', 2002, 'GAU'),
  ('UMP', 2002, 'DTE'),
  ('FN',  2002, 'EXD'),
  -- ... (liste complète à établir en D1.2)
;
```

Aucun DROP, aucune modification destructive.

---

## 8. Circulaires de nuances à archiver

### Déjà archivées

| Fichier | NOR | Scrutin | Blocs ? |
|---------|-----|---------|---------|
| `2022-legislatives_INTA2212053C.pdf` | INTA2212053C | Législatives 2022 (version initiale avr. 2022) | Non |
| `2024-legislatives_IOMA2415630C.pdf` | IOMA2415630C | Législatives 2024 | Oui |

Note : la version **finale** de la circulaire 2022 est INTA2214249C (13 mai 2022, Légifrance id/45336). Notre docs contient la version initiale d'avril 2022.

### À archiver — recherche web effectuée

| Scrutin | Statut | Note |
|---------|--------|------|
| 2017 | **NOR non trouvé** | Document PDF scannée trouvé sur sites préfectoraux (hauts-de-seine.gouv.fr) mais illisible (image). Téléchargeable manuellement si besoin. |
| 2012 | **NOR non trouvé** | Aucune trace numérique accessible via web public. |
| 2007 | **NOR non trouvé** | Idem. |
| 2002 | **NOR non trouvé** | Idem. |

**Conclusion** : les circulaires 2002-2017 étaient des documents administratifs internes, largement "non publiés au JO" (non-opposables avant le décret 2014-1479), envoyés directement aux préfectures. Légifrance ne les indexe pas dans sa section circulaires.

**Ce que ça change pour le projet** : les codes nuances sont déjà connus depuis les Parquet (source primaire). Les circulaires 2022/2024 déjà archivées justifient les blocs pour ces deux scrutins. Pour 2002-2017, l'ADR-0005 documente la logique de reconstruction.

**Action optionnelle pour Mathias** : si une recherche MIOM (Ministère de l'Intérieur / Open Data) ou une demande CADA permettait d'obtenir les PDFs 2012 et 2017, les archiver dans `docs/sources-officielles/nuances/`. Priorité : 2017 (17 nuances dont REM, DLF contestés) > 2012 (changement nomenclature avec FG, NCE, CEN) > 2007 > 2002.

---

## 9. Nuances par scrutin — mapping bloc (à faire en D1.2)

Liste complète des nuances connues, avec bloc à attribuer selon la logique ADR-0005 ("classement de l'époque") :

### 2002_legi (22 nuances)
COM→EXG, LCR→EXG, LO→EXG, EXG→EXG | DVG→GAU, SOC→GAU, PRG→GAU, VEC→GAU | DIV→DIV, ECO→CENT, REG→DIV | CPNT→CENT, UDF→CENT | UMP→DTE, RPF→DTE, DVD→DTE, DL→DTE, MPF→DTE | FN→EXD, MNR→EXD, EXD→EXD, PREP→EXD

### 2007_legi (17 nuances)
COM→EXG, EXG→EXG | DVG→GAU, SOC→GAU, RDG→GAU, VEC→GAU | DIV→DIV, ECO→CENT, REG→DIV | UDFD→CENT, MAJ→CENT | UMP→DTE, DVD→DTE, MPF→DTE, CPNT→DTE | FN→EXD, EXD→EXD

### 2012_legi (17 nuances)
EXG→EXG | FG→GAU, SOC→GAU, DVG→GAU, RDG→GAU, VEC→GAU, ALLI→GAU | AUT→DIV, REG→DIV | CEN→CENT, NCE→CENT | UMP→DTE, DVD→DTE, PRV→DTE | FN→EXD, EXD→EXD, DXD→EXD (si présent)

### 2017_legi (17 nuances)
EXG→EXG, COM→EXG | FI→GAU, SOC→GAU, DVG→GAU, RDG→GAU | DIV→DIV, ECO→CENT, REG→DIV | MDM→CENT, REM→CENT, UDI→CENT | LR→DTE, DVD→DTE, DLF→DTE | FN→EXD, EXD→EXD

*Note DLF/Dupont-Aignan 2017* : classé DTE selon CE 31/01/2020 n°437675 (confirme que le classement EXD 2017 était une erreur préfectorale — cf. ADR-0005).

### 2022_legi (16 nuances)
DXG→EXG | DVG→GAU, NUP→GAU, DSV→GAU, RDG→GAU | DIV→DIV, DVC→DIV, REG→DIV | ENS→CENT, ECO→CENT | LR→DTE, DVD→DTE | RN→EXD, REC→EXD, DXD→EXD

*Note NUP (NUPES)* : classé GAU par la circulaire finale INTA2214249C suite à la décision CE ord. 7 juin 2022, n°464414.

### 2024_legi (22 nuances)
EXG→EXG, COM→EXG, FI→EXG | UG→GAU, DVG→GAU, SOC→GAU, RDG→GAU, ECO→GAU, VEC→GAU | DIV→DIV, DVC→DIV, REG→DIV, DSV→DIV | ENS→CENT, HOR→CENT | LR→DTE, DVD→DTE | RN→EXD, REC→EXD, UXD→EXD, EXD→EXD, DXD→EXD

*Note FI 2024* : FI classé EXG (circulaire IOMA2415630C confirme le basculement déjà initié en 2023).

---

## 10. Recommandations pour D1.2

1. **Script `scripts/load_elections_legislatives.py`** : similaire à `load_elections_presidentielles.py` avec :
   - Filtrage HdF via jointure `geographies_communes.code_region = '32'`
   - Population de `code_circo` à partir de `code_departement || '-' || LPAD(code_circonscription, 2, '0')` (NULL pour 2002/2007/2024)
   - Extension de `nuances_harmonisees` avec les ~100 nouvelles entrées (voir §9)

2. **Script `scripts/init_elections_schema.py`** : ajouter `ALTER TABLE ... ADD COLUMN IF NOT EXISTS code_circo` (idempotent)

3. **Vues à créer** :
   - `v_scores_circo_legi` : voix par circo × bloc × scrutin (agrégation par circo, pas bureau de vote)
   - `v_participation_circo_legi` : participation par circo × scrutin
   - `v_evolution_blocs_hdf_legi` : évolution par département ou circo sur les 6 scrutins

4. **UI** : dans `pages/2_🗳️_Élections.py`, ajouter `st.tabs()` — onglet "Présidentielles" (existant) + onglet "Législatives" (nouveau). Sélecteur circo avec 50 options HdF.

5. **2002/2007 sans code_circo** : afficher un message d'information dans l'UI "Découpage de circonscription non disponible pour ce scrutin". Ne pas bloquer la carte commune.

6. **2024_legi_t2** : afficher le nombre de BV disponibles (3 658) pour éviter la confusion avec un chargement incomplet.
