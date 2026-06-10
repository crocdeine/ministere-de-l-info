# Tableau de classement nuance × année → bloc — Municipales (VALIDÉ)

**Date de validation** : 2026-06-09 (Phase D3.2)
**Statut** : VALIDÉ — appliqué dans `nuances_harmonisees`, 67 entrées insérées
**Source des nuances** : Parquet data.gouv.fr (HdF, scrutins 2008/2014/2020/2026, t1, nuance IS NOT NULL)
**Références ADR** : ADR-0005 §§ "Application aux municipales 2008-2026"

---

## Décisions de non-insertion (3 nuances exclues)

| Nuance | Année(s) | Motif |
|--------|----------|-------|
| `NC` | 2014, 2020 | "Non classé" administratif — catégorie résiduelle du Ministère, pas un bloc politique |
| `LMAJ` | 2008 | Indicateur de situation (liste sortante / majorité), sans idéologie assignable |
| `LNC` | 2020 | Parallèle de NC pour communes > 1 000 hab — même raisonnement que NC |

---

## 2008 — 12 nuances

| Nuance | Bloc | Source / justification |
|--------|------|------------------------|
| LMC | CENT | Majorité-Centre — sphère UDF 2008 |
| LAUT | DIV | Autre — liste inclassable |
| LGC | DIV | Gauche-Centre local — 5 occurrences HdF, trop peu pour classifier |
| LDVD | DTE | Divers Droite |
| LFN | EXD | Front National |
| LCOM | EXG | Communiste — PCF |
| LEXG | EXG | Extrême gauche |
| LCMD | GAU | Communiste et Divers — libellés Parquet NULL ; analyse contextuelle bassin minier HdF (communes ouvrières PCF-apparentés) ; cohérence avec LDVG/LSOC |
| LDVG | GAU | Divers Gauche |
| LSOC | GAU | Socialiste |
| LUG | GAU | Union de la Gauche |
| LVEC | GAU | Verts / Écologistes |

---

## 2014 — 17 nuances

| Nuance | Bloc | Source / justification |
|--------|------|------------------------|
| LMDM | CENT | Mouvement Démocrate — MoDem |
| LUC | CENT | Union Centre |
| LUD | CENT | Union Démocratique / UDI |
| LDIV | DIV | Divers |
| LUDI | DIV | Union Divers |
| LDVD | DTE | Divers Droite |
| LUMP | DTE | UMP (devenu LR en 2015) |
| LEXD | EXD | Extrême droite |
| LFN | EXD | Front National |
| LCOM | EXG | Communiste — PCF |
| LEXG | EXG | Extrême gauche |
| LDVG | GAU | Divers Gauche |
| LFG | GAU | Front de Gauche (PCF + Parti de Gauche) — GAU per ADR-0005 ; bascule EXG concerne LFI/2026 seulement |
| LPG | GAU | Parti de Gauche (Mélenchon, 2008-2016) — dans le FdG en 2014 ; GAU par cohérence avec LFG |
| LSOC | GAU | Socialiste |
| LUG | GAU | Union de la Gauche |
| LVEC | GAU | Verts / EELV |

---

## 2020 — 19 nuances

| Nuance | Bloc | Source / justification |
|--------|------|------------------------|
| LDVC | CENT | Divers Centre — investiture LREM/MoDem/UDI per CE 31/01/2020 n°437675 |
| LREM | CENT | La République En Marche |
| LUC | CENT | Union Centre |
| LUD | CENT | Union Démocratique / UDI |
| LDIV | DIV | Divers |
| LUDI | DIV | Union Divers |
| LDVD | DTE | Divers Droite |
| LLR | DTE | Les Républicains |
| LEXD | EXD | Extrême droite |
| LRN | EXD | Rassemblement National |
| LCOM | EXG | Communiste — PCF |
| LEXG | EXG | Extrême gauche |
| LDVG | GAU | Divers Gauche |
| LECO | GAU | Écologiste — EELV principalement |
| LFI | GAU | **La France Insoumise 2020 → GAU** per circulaire INTA1931378J ; bascule EXG uniquement à partir de 2026 (INTP2602966C + CE 512694) |
| LRDG | GAU | Radicaux de Gauche — allié PS |
| LSOC | GAU | Socialiste |
| LUG | GAU | Union de la Gauche |
| LVEC | GAU | Verts / EELV |

---

## 2026 — 19 nuances

| Nuance | Bloc | Source / justification |
|--------|------|------------------------|
| LDVC | CENT | Divers Centre — per INTP2602966C (2 fév. 2026) |
| LHOR | CENT | Horizons — parti Édouard Philippe |
| LUC | CENT | Union Centre |
| LDIV | DIV | Divers |
| LUDI | DIV | Union Divers |
| LDVD | DTE | Divers Droite |
| LLR | DTE | Les Républicains |
| LEXD | EXD | Extrême droite |
| LRN | EXD | Rassemblement National |
| LUDR | EXD | **Union Droite Républicaine (parti Ciotti, allié RN)** — per INTP2602966C + CE 27/02/2026 n°512694 |
| LUXD | EXD | Union Extrême Droite |
| LCOM | EXG | Communiste — PCF |
| LEXG | EXG | Extrême gauche |
| LFI | EXG | **La France Insoumise 2026 → EXG** per INTP2602966C + CE 27/02/2026 n°512694 (rejet recours LFI) |
| LDVG | GAU | Divers Gauche |
| LECO | GAU | Écologiste |
| LSOC | GAU | Socialiste |
| LUG | GAU | Union de la Gauche / NFP |
| LVEC | GAU | Verts / EELV |

---

## Récapitulatif par bloc

| Bloc | 2008 | 2014 | 2020 | 2026 | Total |
|------|------|------|------|------|-------|
| CENT | 1 | 3 | 4 | 3 | 11 |
| DIV | 2 | 2 | 2 | 2 | 8 |
| DTE | 1 | 2 | 2 | 2 | 7 |
| EXD | 1 | 2 | 2 | 4 | 9 |
| EXG | 2 | 2 | 2 | 3 | 9 |
| GAU | 5 | 6 | 7 | 5 | 23 |
| **Total** | **12** | **17** | **19** | **19** | **67** |

---

## Sources officielles utilisées

| Document | Portée |
|----------|--------|
| Circulaire INTA1931378J (3 fév. 2020) | Nuançage municipales 2020 — archivée `docs/sources-officielles/nuances/` |
| Circulaire INTP2602966C (2 fév. 2026) | Nuançage municipales 2026 — archivée |
| CE 31/01/2020 n°437675 | LDVC 2020 → CENT (investiture LREM/MoDem/UDI) |
| CE 27/02/2026 n°512694 | LFI 2026 → EXG, UDR 2026 → EXD (rejet recours) |
