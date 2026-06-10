# Tableau de classement nuance × année → bloc — Municipales

**Date de préparation** : 2026-06-06 (Phase D3.1.2)
**Statut** : PROPOSITION — en attente de validation Mathias ligne par ligne
**Source des nuances** : `DISTINCT nuance, annee` sur `data/exploration/general-results.parquet`
  (HdF uniquement, t1, nuance IS NOT NULL)
**Référence** :
  - ADR-0005 (§ « classement de l'époque »)
  - Circulaire INTA1931378J (3 fév. 2020, municipales 2020)
  - Circulaire INTP2602966C (2 fév. 2026, municipales 2026) — archivée
  - CE 31/01/2020 n°437675 (DLF ≠ EXD ; LDVC ≠ sans investiture)
  - CE 27/02/2026 n°512694 (LFI → EXG ; UDR → EXD en 2026)

---

## Légende blocs

| Code | Libellé | Couleur |
|------|---------|---------|
| EXG | Extrême gauche | #8B0000 |
| GAU | Gauche | #E84C61 |
| DIV | Divers / Non classé politique | #9E9E9E |
| CENT | Centre | #F5B800 |
| DTE | Droite | #3B7DD8 |
| EXD | Extrême droite | #1F3864 |

---

## Codes SANS mapping (à exclure de `nuances_harmonisees`)

| Code | Fréquence HdF (tous scrutins t1) | Raison |
|------|----------------------------------|--------|
| **NC** | 88 355 (2014) + 43 074 (2020) = 131 429 | "Non Classé" — indication administrative, pas un bloc idéologique. L'UI affichera "Non classé" pour ces lignes. |
| **LMAJ** | 543 (2008) | "Majorité sortante" — indique le statut de sortant, pas l'orientation idéologique. Voir §Q1 ci-dessous. |

> **Q1 — À valider par Mathias** : LMAJ (543 occurrences 2008) → laisser **sans mapping** (bloc NULL, UI : "Liste sortante") ou mapper **DIV** ? Les deux sont défendables. Recommandation : NULL (même traitement que NC).

---

## Nuances par année — total 71 entrées (nuance, annee)

Les cas **⚠️ ambigus** sont marqués et justifiés. Les cases "Bloc proposé" sans ⚠️ sont considérées non-ambiguës.

---

### Municipales 2008 — 13 nuances

| Nuance | N HdF t1 | Bloc proposé | Justification | Ambiguïté |
|--------|---------|--------------|---------------|-----------|
| LAUT | 96 | DIV | "Autre" — liste inclassable | — |
| LCMD | 159 | EXG | Communiste et Divers — probable code PCF/municipaux communistes HdF (bassin minier) | **⚠️ Q2 — EXG ou GAU ?** |
| LCOM | 192 | EXG | Communiste — PCF | — |
| LDVD | 870 | DTE | Divers Droite | — |
| LDVG | 583 | GAU | Divers Gauche | — |
| LEXG | 430 | EXG | Extrême gauche — code explicite | — |
| LFN | 198 | EXD | Front National | — |
| LGC | 5 | DIV | "Gauche-Centre" ou "Gauche Citoyenne" — 5 occurrences, trop peu pour classifier ; probablement liste locale non affiliée | **⚠️ Q3 — DIV ou GAU ?** |
| LMAJ | 543 | *SANS MAPPING* | Majorité sortante — voir §Q1 | **⚠️ Q1** |
| LMC | 20 | CENT | "Majorité-Centre" — liste locale centriste (UDF-sphère en 2008) | **⚠️ Q4 — CENT ou DIV ?** |
| LSOC | 341 | GAU | Socialiste | — |
| LUG | 669 | GAU | Union de la Gauche (coalition locale PS+alliés) | — |
| LVEC | 109 | GAU | Verts / Écologistes | — |

---

### Municipales 2014 — 17 nuances + NC

| Nuance | N HdF t1 | Bloc proposé | Justification | Ambiguïté |
|--------|---------|--------------|---------------|-----------|
| LCOM | 360 | EXG | Communiste — PCF | — |
| LDIV | 1 130 | DIV | Divers | — |
| LDVD | 1 871 | DTE | Divers Droite | — |
| LDVG | 2 287 | GAU | Divers Gauche | — |
| LEXD | 25 | EXD | Extrême droite — code explicite | — |
| LEXG | 1 095 | EXG | Extrême gauche — code explicite | — |
| LFG | 727 | GAU | Front de Gauche (coalition PCF + Parti de Gauche, 2012-2016) — **GAU en 2014** per ADR-0005 ; FG n'est pas EXG avant la bascule LFI 2026 | **⚠️ Q5 — GAU ou EXG ?** critique |
| LFN | 1 315 | EXD | Front National | — |
| LMDM | 11 | CENT | Mouvement Démocrate (MoDem, Bayrou) | — |
| LPG | 83 | GAU | Parti de Gauche (Mélenchon, 2008-2016) — précurseur de LFI ; en 2014 encore dans le Front de Gauche → **GAU** par cohérence avec LFG | **⚠️ Q6 — GAU ou EXG ?** |
| LSOC | 893 | GAU | Socialiste | — |
| LUC | 22 | CENT | Union Centre | — |
| LUD | 859 | CENT | Union Démocratique (UDI ou assimilés) | — |
| LUDI | 206 | DIV | Union Divers — coalition locale sans coloration claire | — |
| LUG | 1 196 | GAU | Union de la Gauche (coalition PS+PCF+Verts locaux) | — |
| LUMP | 557 | DTE | UMP (devenu LR en 2015) | — |
| LVEC | 296 | GAU | Verts / EELV | — |
| NC | 45 281 | *SANS MAPPING* | Non Classé | — |

---

### Municipales 2020 — 21 nuances + NC

| Nuance | N HdF t1 | Bloc proposé | Justification | Ambiguïté |
|--------|---------|--------------|---------------|-----------|
| LCOM | 277 | EXG | Communiste — PCF | — |
| LDIV | 1 031 | DIV | Divers | — |
| LDVC | 900 | CENT | Divers Centre — attribué avec investiture officielle (post-CE 31/01/2020 n°437675 qui corrige l'attribution automatique) | **⚠️ Q7 — CENT confirmé ?** |
| LDVD | 1 573 | DTE | Divers Droite | — |
| LDVG | 2 489 | GAU | Divers Gauche | — |
| LECO | 198 | GAU | Écologiste — EELV principalement | — |
| LEXD | 4 | EXD | Extrême droite — code explicite | — |
| LEXG | 1 102 | EXG | Extrême gauche — code explicite | — |
| LFI | 371 | **GAU** | La France Insoumise **en 2020** — classé gauche per INTA1931378J ; la bascule EXG n'intervient qu'en 2026 (INTP2602966C + CE 27/02/2026 n°512694) | **⚠️ Q8 — GAU 2020 confirmé ?** critique |
| LLR | 293 | DTE | Les Républicains | — |
| LNC | 1 787 | CENT | Vraisemblablement "Nouveau Centre" (Jean-Louis Borloo / UDI sphere) — maintenu comme code post-absorption dans UDI | **⚠️ Q9 — CENT ou DIV ?** critique |
| LRDG | 9 | GAU | Radicaux de Gauche — allié PS | — |
| LREM | 119 | CENT | La République En Marche (Macron) | — |
| LRN | 1 268 | EXD | Rassemblement National | — |
| LSOC | 130 | GAU | Socialiste | — |
| LUC | 293 | CENT | Union Centre | — |
| LUD | 34 | CENT | Union Démocratique (UDI) | — |
| LUDI | 106 | DIV | Union Divers | — |
| LUG | 607 | GAU | Union de la Gauche | — |
| LVEC | 425 | GAU | Verts / EELV | — |
| NC | 43 074 | *SANS MAPPING* | Non Classé | — |

---

### Municipales 2026 — 19 nuances (pas de NC)

| Nuance | N HdF t1 | Bloc proposé | Justification | Ambiguïté |
|--------|---------|--------------|---------------|-----------|
| LCOM | 129 | EXG | Communiste — PCF | — |
| LDIV | 861 | DIV | Divers | — |
| LDVC | 1 004 | CENT | Divers Centre — seuil 3 500 hab confirmé (CE 27/02/2026 n°512694) ; attribution avec investiture officielle | — |
| LDVD | 1 589 | DTE | Divers Droite | — |
| LDVG | 1 650 | GAU | Divers Gauche | — |
| LECO | 8 | GAU | Écologiste | — |
| LEXD | 138 | EXD | Extrême droite — code explicite | — |
| LEXG | 1 116 | EXG | Extrême gauche — code explicite | — |
| LFI | 702 | **EXG** | La France Insoumise **en 2026** — bascule EXG validée par INTP2602966C (2 fév. 2026) et CE 27/02/2026 n°512694 (rejet recours LFI). Investitures séparées du bloc gauche en 2026. | **⚠️ Q8 — EXG 2026 confirmé ?** (bascule de GAU 2020) |
| LHOR | 4 | CENT | Horizons (parti d'Édouard Philippe) — centrist, fondé 2021 | — |
| LLR | 150 | DTE | Les Républicains | — |
| LRN | 1 104 | EXD | Rassemblement National | — |
| LSOC | 139 | GAU | Socialiste | — |
| LUC | 181 | CENT | Union Centre | — |
| LUDI | 43 | DIV | Union Divers | — |
| LUDR | 24 | **EXD** | Union Droite Républicaine (parti de Nicolas Ciotti, allié RN) — **nouveau code 2026**, classé EXD par INTP2602966C, validé CE 27/02/2026 n°512694 | **⚠️ Q10 — EXD confirmé ?** nouveau code |
| LUG | 896 | GAU | Union de la Gauche (coalition NFP) | — |
| LUXD | 60 | EXD | Union Extrême Droite — code explicite | — |
| LVEC | 245 | GAU | Verts / EELV | — |

---

## Récapitulatif des cas nécessitant validation Mathias

| # | Code | Année | Bloc proposé | Alternative | Enjeu |
|---|------|-------|--------------|-------------|-------|
| Q1 | LMAJ | 2008 | NULL (sans mapping) | DIV | 543 listes "sortantes" non classifiables idéologiquement |
| Q2 | LCMD | 2008 | EXG | GAU | 159 listes — probable PCF/municipal communiste HdF |
| Q3 | LGC | 2008 | DIV | GAU | 5 listes — très peu de données, classement incertain |
| Q4 | LMC | 2008 | CENT | DIV | 20 listes — "Majorité-Centre", UDF-sphère probable |
| Q5 | LFG | 2014 | GAU | EXG | **727 listes** — Front de Gauche (PCF + PG) ; ADR-0005 dit GAU avant 2026 |
| Q6 | LPG | 2014 | GAU | EXG | 83 listes — Parti de Gauche (Mélenchon) ; cohérence avec LFG |
| Q7 | LDVC | 2020 | CENT | DIV | **900 listes** — post-CE 437675 ; LDVC = investiture officielle LREM/MoDem → CENT |
| Q8 | LFI | 2020→GAU, 2026→EXG | double entrée | — | **371+702 listes** — bascule critique ; cohérent avec sources officielles |
| Q9 | LNC | 2020 | CENT | DIV | **1 787 listes** — "Nouveau Centre" (UDI-sphère) ou "Liste Non Classée" ? |
| Q10 | LUDR | 2026 | EXD | — | 24 listes — nouveau code, validé CE 512694 |

---

## Note sur la cohérence interne

- **LFI double entrée** : `(LFI, 2020, GAU)` et `(LFI, 2026, EXG)` — bascule conforme au principe ADR-0005 "classement de l'époque" et aux sources officielles. **Point le plus critique du mapping.**
- **LFG (2014) = GAU** : le Front de Gauche (PCF + PG) n'est pas EXG en 2014. La bascule EXG concerne LFI/Mélenchon à partir de 2026 spécifiquement. FG reste GAU par cohérence avec le mapping législatif 2012.
- **LDVC (2020) = CENT** : malgré la suspension partielle par CE 437675 (attribution automatique annulée), les LDVC effectivement attribués post-correction sont valides → CENT.
- **NC (2014, 2020)** : non inséré dans `nuances_harmonisees`. L'UI traitera ces lignes comme "Non classé" (bloc NULL). Représente 88 % des communes HdF en 2014 et 95 % en 2020 (petites communes sans investiture de parti).
- **LMAJ (2008)** : non inséré (si Mathias confirme Q1). Représente 13 % des listes HdF 2008.

---

## Pour insérer dans `nuances_harmonisees` (après validation)

Format : `(nuance, annee, bloc, source_bloc)`

```sql
-- 2008 (après validation Q1-Q4)
INSERT OR IGNORE INTO nuances_harmonisees (nuance, annee, bloc, source_bloc) VALUES
  ('LAUT',  2008, 'DIV', 'Autre — liste inclassable (D3.2)'),
  ('LCMD',  2008, 'EXG', 'Communiste et Divers — PCF municipal HdF (D3.2, Q2 validé)'),
  ('LCOM',  2008, 'EXG', 'Communiste — PCF (D3.2)'),
  ('LDVD',  2008, 'DTE', 'Divers Droite (D3.2)'),
  ('LDVG',  2008, 'GAU', 'Divers Gauche (D3.2)'),
  ('LEXG',  2008, 'EXG', 'Extrême gauche (D3.2)'),
  ('LFN',   2008, 'EXD', 'Front National (D3.2)'),
  ('LGC',   2008, 'DIV', 'Gauche-Centre local — trop peu pour classifier (D3.2, Q3 validé)'),
  ('LMC',   2008, 'CENT','Majorité-Centre — UDF sphère 2008 (D3.2, Q4 validé)'),
  ('LSOC',  2008, 'GAU', 'Socialiste (D3.2)'),
  ('LUG',   2008, 'GAU', 'Union de la Gauche (D3.2)'),
  ('LVEC',  2008, 'GAU', 'Verts / Écologistes (D3.2)'),
  -- LMAJ non inséré (voir Q1)

-- 2014
  ('LCOM',  2014, 'EXG', 'Communiste — PCF (D3.2)'),
  ('LDIV',  2014, 'DIV', 'Divers (D3.2)'),
  ('LDVD',  2014, 'DTE', 'Divers Droite (D3.2)'),
  ('LDVG',  2014, 'GAU', 'Divers Gauche (D3.2)'),
  ('LEXD',  2014, 'EXD', 'Extrême droite (D3.2)'),
  ('LEXG',  2014, 'EXG', 'Extrême gauche (D3.2)'),
  ('LFG',   2014, 'GAU', 'Front de Gauche 2012-2016 — GAU per ADR-0005 (D3.2, Q5 validé)'),
  ('LFN',   2014, 'EXD', 'Front National (D3.2)'),
  ('LMDM',  2014, 'CENT','MoDem (D3.2)'),
  ('LPG',   2014, 'GAU', 'Parti de Gauche — Front de Gauche sphere (D3.2, Q6 validé)'),
  ('LSOC',  2014, 'GAU', 'Socialiste (D3.2)'),
  ('LUC',   2014, 'CENT','Union Centre (D3.2)'),
  ('LUD',   2014, 'CENT','Union Démocratique / UDI (D3.2)'),
  ('LUDI',  2014, 'DIV', 'Union Divers (D3.2)'),
  ('LUG',   2014, 'GAU', 'Union de la Gauche (D3.2)'),
  ('LUMP',  2014, 'DTE', 'UMP (D3.2)'),
  ('LVEC',  2014, 'GAU', 'Verts / EELV (D3.2)'),
  -- NC non inséré

-- 2020
  ('LCOM',  2020, 'EXG', 'Communiste — PCF (D3.2)'),
  ('LDIV',  2020, 'DIV', 'Divers (D3.2)'),
  ('LDVC',  2020, 'CENT','Divers Centre — investiture officielle LREM/MoDem/UDI per CE 31/01/2020 n°437675 (D3.2, Q7 validé)'),
  ('LDVD',  2020, 'DTE', 'Divers Droite (D3.2)'),
  ('LDVG',  2020, 'GAU', 'Divers Gauche (D3.2)'),
  ('LECO',  2020, 'GAU', 'Écologiste — EELV (D3.2)'),
  ('LEXD',  2020, 'EXD', 'Extrême droite (D3.2)'),
  ('LEXG',  2020, 'EXG', 'Extrême gauche (D3.2)'),
  ('LFI',   2020, 'GAU', 'La France Insoumise 2020 — GAU per INTA1931378J ; bascule EXG uniquement en 2026 (D3.2, Q8 validé)'),
  ('LLR',   2020, 'DTE', 'Les Républicains (D3.2)'),
  ('LNC',   2020, 'CENT','Nouveau Centre / UDI sphère (D3.2, Q9 validé)'),
  ('LRDG',  2020, 'GAU', 'Radicaux de Gauche — allié PS (D3.2)'),
  ('LREM',  2020, 'CENT','La République En Marche (D3.2)'),
  ('LRN',   2020, 'EXD', 'Rassemblement National (D3.2)'),
  ('LSOC',  2020, 'GAU', 'Socialiste (D3.2)'),
  ('LUC',   2020, 'CENT','Union Centre (D3.2)'),
  ('LUD',   2020, 'CENT','Union Démocratique / UDI (D3.2)'),
  ('LUDI',  2020, 'DIV', 'Union Divers (D3.2)'),
  ('LUG',   2020, 'GAU', 'Union de la Gauche (D3.2)'),
  ('LVEC',  2020, 'GAU', 'Verts / EELV (D3.2)'),
  -- NC non inséré

-- 2026
  ('LCOM',  2026, 'EXG', 'Communiste — PCF (D3.2)'),
  ('LDIV',  2026, 'DIV', 'Divers (D3.2)'),
  ('LDVC',  2026, 'CENT','Divers Centre — per INTP2602966C 2026 (D3.2)'),
  ('LDVD',  2026, 'DTE', 'Divers Droite (D3.2)'),
  ('LDVG',  2026, 'GAU', 'Divers Gauche (D3.2)'),
  ('LECO',  2026, 'GAU', 'Écologiste (D3.2)'),
  ('LEXD',  2026, 'EXD', 'Extrême droite (D3.2)'),
  ('LEXG',  2026, 'EXG', 'Extrême gauche (D3.2)'),
  ('LFI',   2026, 'EXG', 'La France Insoumise 2026 — EXG per INTP2602966C + CE 27/02/2026 n°512694 (D3.2, Q8 validé)'),
  ('LHOR',  2026, 'CENT','Horizons — parti centriste Édouard Philippe (D3.2)'),
  ('LLR',   2026, 'DTE', 'Les Républicains (D3.2)'),
  ('LRN',   2026, 'EXD', 'Rassemblement National (D3.2)'),
  ('LSOC',  2026, 'GAU', 'Socialiste (D3.2)'),
  ('LUC',   2026, 'CENT','Union Centre (D3.2)'),
  ('LUDI',  2026, 'DIV', 'Union Divers (D3.2)'),
  ('LUDR',  2026, 'EXD', 'Union Droite Républicaine (Ciotti/RN allié) — per INTP2602966C + CE 27/02/2026 n°512694 (D3.2, Q10 validé)'),
  ('LUG',   2026, 'GAU', 'Union de la Gauche / NFP (D3.2)'),
  ('LUXD',  2026, 'EXD', 'Union Extrême Droite (D3.2)'),
  ('LVEC',  2026, 'GAU', 'Verts / EELV (D3.2)');
```

Après validation : ce bloc SQL sera intégré dans `scripts/load_elections_municipales.py`.
Total entrées prévues : **69** (71 − NC×2 − LMAJ×1, si Q1 confirme NULL pour LMAJ).
