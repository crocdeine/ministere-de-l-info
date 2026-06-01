# Tableau de classement nuance × année → bloc — Législatives

**Date de préparation** : 2026-06-01 (Phase D1.2)
**Statut** : VALIDÉ 2026-06-01 — les 111 entrées sont insérées dans `nuances_harmonisees` (avec `source_bloc`)
**Source des nuances** : requête `DISTINCT nuance, annee` sur `data/exploration/general-results.parquet` (législatives uniquement)
**Référence** : ADR-0005 (§ « Application aux législatives 2002-2024 »), circulaires archivées dans `docs/sources-officielles/nuances/`

> **Note de validation** : les 12 cas ambigus ci-dessous ont été tranchés par Mathias.
> Seule modification par rapport à la proposition initiale : **PREP 2002 = GAU** (était DIV)
> — Pôle Républicain (Chevènement) classé GAU par cohérence DVG/MDC. Tous les autres
> cas sont confirmés tels que proposés. Voir le récapitulatif en fin de document.

---

## Légende blocs

| Code | Libellé | Couleur |
|------|---------|---------|
| EXG | Extrême gauche | #8B0000 |
| GAU | Gauche | #E84C61 |
| DIV | Divers / Régionalistes | #9E9E9E |
| CENT | Centre | #F5B800 |
| DTE | Droite | #3B7DD8 |
| EXD | Extrême droite | #1F3864 |

---

## Nuances par année — total 111 entrées (nuance, annee)

Les cas **⚠️ ambigus** ou non-évidents sont marqués et justifiés en détail.
Trier les corrections : répondre "OK" ou indiquer le bloc correct pour chaque ligne marquée.

---

### Législatives 2002 — 22 nuances

| Nuance | N candidats (France) | Bloc proposé | Justification | Ambiguïté |
|--------|---------------------|--------------|---------------|-----------|
| COM | 57 808 | GAU | PCF — classé GAU dans logique officielle Ministère (pas EXG, contrairement à l'usage courant) | — |
| CPNT | 48 075 | DIV | Chasse Pêche Nature Tradition — historiquement DIV pour Ministère | — |
| DIV | 75 337 | DIV | Divers — code se mappe directement à DIV | — |
| DL | 1 971 | DTE | Démocratie Libérale (Madelin) — libéral-conservateur, alliance RPR/UMP précurseur | — |
| DVD | 42 236 | DTE | Divers Droite — mapping direct | — |
| DVG | 27 229 | GAU | Divers Gauche — mapping direct | — |
| ECO | 96 691 | GAU | Écologistes / Verts divers — logique officielle Ministère : pas de bloc écolo distinct, classification GAU (cf. schema-elections.md, ADR-0005) | — |
| EXD | 13 980 | EXD | Extrême droite — code = bloc | — |
| EXG | 28 618 | EXG | Extrême gauche — code = bloc | — |
| FN | 66 362 | EXD | Front National | — |
| LCR | 46 640 | EXG | Ligue Communiste Révolutionnaire (trotskiste) | — |
| LO | 62 718 | EXG | Lutte Ouvrière | — |
| MNR | 62 571 | EXD | Mouvement National Républicain (scissionniste FN, Mégret) | — |
| MPF | 33 416 | DTE | Mouvement Pour la France (Villiers) — souverainiste conservateur, CE 31/01/2020 n°437675 conforte DTE | — |
| PREP | 41 853 | **GAU** | Pôle Républicain (proche Chevènement/MDC, souverainiste de gauche) — **validé GAU** par cohérence DVG/MDC (Chevènement classé GAU en présidentielle 2002) | ✅ validé GAU (était DIV) |
| PRG | 9 595 | GAU | Parti Radical de Gauche — allié PS | — |
| REG | 16 490 | DIV | Régionalistes — DIV par définition dans nomenclature Ministère | — |
| RPF | 7 653 | DTE | Rassemblement Pour la France (Pasqua seul, 2002) — souverainiste conservateur, même logique que MPF | **⚠️ DTE ou DIV ?** |
| SOC | 93 601 | GAU | Parti Socialiste | — |
| UDF | 23 735 | CENT | UDF (Bayrou-Giscard tradition, centrist) | — |
| UMP | 109 573 | DTE | UMP (Chirac) | — |
| VEC | 53 765 | GAU | Les Verts — DVGV → GAU selon logique officielle (idem ECO) | — |

---

### Législatives 2007 — 17 nuances

| Nuance | N candidats (France) | Bloc proposé | Justification | Ambiguïté |
|--------|---------------------|--------------|---------------|-----------|
| COM | 60 601 | GAU | PCF | — |
| CPNT | 33 358 | DIV | Chasse Pêche Nature Tradition | — |
| DIV | 89 836 | DIV | Divers | — |
| DVD | 30 799 | DTE | Divers Droite | — |
| DVG | 24 450 | GAU | Divers Gauche | — |
| ECO | 45 483 | GAU | Écologistes | — |
| EXD | 44 200 | EXD | Extrême droite | — |
| EXG | 152 899 | EXG | Extrême gauche | — |
| FN | 63 935 | EXD | Front National | — |
| MAJ | 13 575 | DTE | Majorité présidentielle (coalition UMP-alliés Sarkozy 2007) | **⚠️ DTE confirmé ?** |
| MPF | 50 810 | DTE | Mouvement Pour la France (Villiers) | — |
| RDG | 10 566 | GAU | Radical de Gauche | — |
| REG | 9 394 | DIV | Régionalistes | — |
| SOC | 103 129 | GAU | Parti Socialiste | — |
| UDFD | 60 670 | CENT | UDF Démocrate — candidats restés UDF/MoDem après la scission 2007 ; tradition centriste giscardienne | **⚠️ CENT ou DTE ?** |
| UMP | 110 843 | DTE | UMP (Sarkozy) | — |
| VEC | 60 741 | GAU | Les Verts | — |

---

### Législatives 2012 — 17 nuances

| Nuance | N candidats (France) | Bloc proposé | Justification | Ambiguïté |
|--------|---------------------|--------------|---------------|-----------|
| ALLI | 6 228 | CENT | Alliance Centriste (Jean Arthuis) — parti centrist allié UMP-NC, précurseur UDI | **⚠️ CENT ou DTE ?** |
| AUT | 41 018 | DIV | Autres — divers inclassables | — |
| CEN | 38 557 | CENT | Centre — code explicitement centrist | — |
| DVD | 85 370 | DTE | Divers Droite | — |
| DVG | 28 883 | GAU | Divers Gauche | — |
| ECO | 71 861 | GAU | Écologistes (EELV principalement) | — |
| EXD | 9 154 | EXD | Extrême droite | — |
| EXG | 124 585 | EXG | Extrême gauche | — |
| FG | 67 532 | GAU | Front de Gauche (PCF + Parti de Gauche/Mélenchon) — **GAU en 2012**, pas EXG ; LFI bascule EXG seulement en 2026 via INTP2602966C | **⚠️ GAU ou EXG ?** Critique — cf. ADR-0005 |
| FN | 74 510 | EXD | Front National | — |
| NCE | 16 647 | CENT | Nouveau Centre (Jean-Louis Borloo) — centrist, allié UMP | — |
| PRV | 12 221 | DTE | Parti Radical Valoisien — branche droite du PR, allié UMP (opposé à RDG allié PS) | — |
| RDG | 10 702 | GAU | Radical de Gauche — allié PS | — |
| REG | 10 712 | DIV | Régionalistes | — |
| SOC | 103 139 | GAU | Parti Socialiste | — |
| UMP | 108 593 | DTE | UMP (Sarkozy → Fillon) | — |
| VEC | 58 758 | GAU | Les Verts / EELV | — |

---

### Législatives 2017 — 17 nuances

| Nuance | N candidats (France) | Bloc proposé | Justification | Ambiguïté |
|--------|---------------------|--------------|---------------|-----------|
| COM | 56 954 | GAU | PCF | — |
| DIV | 151 169 | DIV | Divers | — |
| DLF | 48 237 | DTE | Debout la France (Dupont-Aignan) — CE 31/01/2020 n°437675 confirme DTE | — |
| DVD | 63 640 | DTE | Divers Droite | — |
| DVG | 41 143 | GAU | Divers Gauche | — |
| ECO | 105 641 | GAU | Écologistes (EELV) | — |
| EXD | 21 551 | EXD | Extrême droite | — |
| EXG | 78 993 | EXG | Extrême gauche | — |
| FI | 73 301 | GAU | La France Insoumise — **GAU en 2017** selon IOMA2322276J (sénatoriales 2023 confirme rétrospectivement) ; bascule EXG seulement en 2026 via INTP2602966C | **⚠️ GAU confirmé 2017 ?** |
| FN | 85 171 | EXD | Front National (devient RN en 2018, après le scrutin) | — |
| LR | 89 707 | DTE | Les Républicains | — |
| MDM | 15 501 | CENT | MoDem (Bayrou) | — |
| RDG | 7 403 | GAU | Radical de Gauche | — |
| REG | 17 772 | DIV | Régionalistes | — |
| REM | 111 583 | CENT | La République En Marche (Macron) | — |
| SOC | 57 299 | GAU | Parti Socialiste | — |
| UDI | 21 284 | CENT | Union des Démocrates Indépendants | — |

---

### Législatives 2022 — 16 nuances

Source : circulaire INTA2212053C (archivée dans `docs/sources-officielles/nuances/`)

| Nuance | N candidats (France) | Bloc proposé | Justification | Ambiguïté |
|--------|---------------------|--------------|---------------|-----------|
| DIV | 47 239 | DIV | Divers | — |
| DSV | 54 770 | DTE | Divers Souverainiste — classement officiel Ministère DTE pour les souverainistes non-EXD | **⚠️ DTE ou EXD ?** |
| DVC | 21 741 | CENT | Divers Centre — mapping direct | — |
| DVD | 34 048 | DTE | Divers Droite | — |
| DVG | 47 786 | GAU | Divers Gauche | — |
| DXD | 1 658 | EXD | Divers Extrême Droite — mapping direct (code explicite) | — |
| DXG | 85 052 | EXG | Divers Extrême Gauche — mapping direct (code explicite) | — |
| ECO | 90 234 | GAU | Écologistes (EELV, source INTA2212053C code ECO) | — |
| ENS | 115 256 | CENT | Ensemble! (coalition Macron : LREM+MoDem+Horizons) | — |
| LR | 64 381 | DTE | Les Républicains | — |
| NUP | 107 392 | GAU | NUPES (LFI+PS+PCF+EELV) — **GAU en 2022** : LFI encore GAU à cette date, bascule EXG seulement en 2026 | **⚠️ GAU ou EXG ?** Critique — cf. ADR-0005 |
| RDG | 8 356 | GAU | Radical de Gauche | — |
| REC | 66 849 | EXD | Reconquête (Zemmour) — source INTA2212053C | — |
| REG | 26 981 | DIV | Régionalistes | — |
| RN | 99 744 | EXD | Rassemblement National — CE 21/09/2023 n°488379 | — |
| UDI | 8 352 | CENT | UDI | — |

---

### Législatives 2024 — 22 nuances

Source : circulaire IOMA2415630C (archivée dans `docs/sources-officielles/nuances/`)

| Nuance | N candidats (France) | Bloc proposé | Justification | Ambiguïté |
|--------|---------------------|--------------|---------------|-----------|
| COM | 93 | GAU | PCF standalone (hors NFP) | — |
| DIV | 22 193 | DIV | Divers | — |
| DSV | 14 391 | DTE | Divers Souverainiste — même logique que 2022 | **⚠️ DTE ou EXD ?** (même question qu'en 2022) |
| DVC | 14 325 | CENT | Divers Centre | — |
| DVD | 26 966 | DTE | Divers Droite | — |
| DVG | 14 774 | GAU | Divers Gauche | — |
| ECO | 15 602 | GAU | Écologistes | — |
| ENS | 77 524 | CENT | Ensemble (Macron, rump 2024) | — |
| EXD | 2 909 | EXD | Extrême droite | — |
| EXG | 77 047 | EXG | Code EXG tel que dans la source — les candidats affiliés à des formations d'extrême gauche ; **NB** : si IOMA2415630C classe LFI comme EXG pour 2024 (à vérifier vs note ADR-0005 sur INTP2602966C), ce code couvrirait LFI | **⚠️ À CONFIRMER via IOMA2415630C** |
| FI | 229 | GAU | LFI standalone (très peu de candidats, hors NFP/EXG) — si EXG 2024 contient déjà LFI, FI est résiduel → GAU | **⚠️ GAU ou EXG ?** |
| HOR | 3 182 | CENT | Horizons (Édouard Philippe) — allié Ensemble | — |
| LR | 43 834 | DTE | LR (ceux restés hors accord Macron) | — |
| RDG | 277 | GAU | Radical de Gauche | — |
| REC | 38 686 | EXD | Reconquête | — |
| REG | 16 925 | DIV | Régionalistes | — |
| RN | 111 593 | EXD | Rassemblement National | — |
| SOC | 658 | GAU | PS standalone (hors NFP) | — |
| UDI | 4 103 | CENT | UDI | — |
| UG | 97 281 | GAU | NFP — Union de la Gauche (PS+PCF+EELV+LFI) — **GAU** si classement global de l'alliance ; mais si LFI est déjà EXG en 2024 via IOMA2415630C, alors NUP/UG serait mixte → à trancher | **⚠️ GAU ou EXG ? CRITIQUE** |
| UXD | 14 830 | EXD | Union d'extrême droite (RN + alliés 2024) | — |
| VEC | 234 | GAU | Verts standalone (hors NFP) | — |

---

## Récapitulatif des cas validés par Mathias (2026-06-01)

| # | Nuance | Année(s) | Bloc validé | Décision |
|---|--------|----------|-------------|----------|
| 1 | PREP | 2002 | **GAU** | **Modifié** (était DIV) — cohérence DVG/Chevènement |
| 2 | RPF | 2002 | DTE | Confirmé (Pasqua, souverainiste conservateur) |
| 3 | UDFD | 2007 | CENT | Confirmé (UDF rump post-MoDem) |
| 4 | MAJ | 2007 | DTE | Confirmé (majorité présidentielle Sarkozy) |
| 5 | ALLI | 2012 | CENT | Confirmé (Alliance Centriste Arthuis) |
| 6 | FG | 2012 | GAU | Confirmé (Front de Gauche — pas EXG avant 2026, ADR-0005) |
| 7 | FI | 2017 | GAU | Confirmé (cohérence présidentielle 2017) |
| 8 | DSV | 2022 + 2024 | DTE | Confirmé (circulaire 2024 : « souverainistes ≠ EXD ») |
| 9 | NUP | 2022 | GAU | Confirmé (NUPES, cohérence ADR-0005) |
| 10 | EXG | 2024 | EXG | Confirmé (IOMA2415630C : LO+NPA+POI, sans LFI) |
| 11 | FI | 2024 | GAU | Confirmé (IOMA2415630C : FI distincte d'EXG) |
| 12 | UG | 2024 | GAU | Confirmé (IOMA2415630C : UG = « Union de la gauche ») |

---

## Note sur la cohérence interne

- **FG 2012 = GAU**, **NUP 2022 = GAU**, **UG 2024 = GAU** : ces trois entrées sont cohérentes si on applique la règle "LFI bascule EXG en 2026 seulement". C'est la logique de l'ADR-0005.
- **ECO** : présent en 2002, 2007, 2012, 2017, 2022, 2024 → GAU dans tous les cas (nomenclature officielle sans bloc écolo distinct).
- **EXG / EXD** (code = bloc) : présents dans plusieurs années, toujours mappés directement.
- **RPF 2002** : distinct de **MPF** (Villiers). Pasqua a fondé RPF en 1999 séparément. Même positionnement DTE.
- **DSV** : le Ministère a classé DLF (Dupont-Aignan) en DTE et non EXD (CE 31/01/2020) ; la circulaire IOMA2415630C (2024) confirme que les souverainistes ne sont pas classés EXD → DSV = DTE en 2022 et 2024.
- **PREP 2002 = GAU** : aligné sur le classement GAU de Chevènement (MDC) en présidentielle 2002 (`nuances_harmonisees` CHEV/2002 = GAU).

---

## Insertion effectuée dans `nuances_harmonisees`

Les 111 entrées sont codées dans `_NUANCES_LEGI` de `schema_elections.py` (4-tuples
`(nuance, annee, bloc, source_bloc)`) et insérées par `populate_elections_referentiels()`
(idempotent : `DELETE` + `INSERT` complet à chaque exécution). La table contient désormais
149 entrées (38 présidentielles + 111 législatives), chacune portant sa justification
courte dans la colonne `source_bloc`.
