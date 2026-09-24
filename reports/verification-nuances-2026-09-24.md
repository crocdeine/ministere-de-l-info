# Vérification des classements nuances → blocs — dossier pour décision

**Date** : 2026-09-24
**Auteur** : agent « Recherche de données et sources » (session cloud)
**Statut** : ÉTUDE — aucun code modifié. Toutes les propositions ci-dessous attendent la validation de Mathias.
**Périmètre** : municipales 2008-2026 (`scripts/load_elections_municipales.py`), législatives et présidentielles (`src/ministere_de_l_info/etl/schema_elections.py`), module Législatif (`etl/loaders/legislatif_datan.py`, `legislatif_senat.py`).

---

## 0. Méthode et niveaux de certitude

**Sources primaires lues** (PDF archivés dans `docs/sources-officielles/nuances/`, texte extrait avec pypdf, tableaux de blocs **vérifiés sur rendu image** car l'extraction texte désordonne les cellules fusionnées) :

| NOR | Date | Scrutin | Grille de blocs ? | Localisation |
|---|---|---|---|---|
| INTA1931378J | 3 fév. 2020 | Municipales 2020 | **Oui** (annexe 3, p. 10) — 6 blocs EXG/GAU/**AUT**/CENT/DTE/EXD | Légifrance : https://www.legifrance.gouv.fr/circulaire/id/44929 |
| INTA2212053C | 7 avr. 2022 | Législatives 2022 | Non (annexe 1 = liste de 19 nuances, p. 5) | archivé |
| IOMA2322276J | 16 août 2023 | Sénatoriales 2023 | Oui (colonne « Bloc » des annexes 1 et 2, p. 6-7) | archivé |
| IOMA2415630C | 11 juin 2024 | Législatives 2024 | **Non** (annexe 1 = 24 nuances, p. 5 et 7 ; aucune colonne bloc) | archivé |
| INTP2602966C | 2 fév. 2026 | Municipales 2026 | Oui (annexe 3, p. 11 individuelles, p. 12 listes) | Légifrance : https://www.legifrance.gouv.fr/circulaire/id/45645 |

**Sources secondaires** (WebSearch uniquement : WebFetch et curl sont bloqués par le proxy pour france-politique.fr, archives-resultats-elections.interieur.gouv.fr, ideeslibres.org, polynesie-francaise.gouv.fr — non réessayé, conformément à la politique du proxy) :
- penombre.org, « Municipales sans politique » (http://www.penombre.org/Municipales-sans-politique) et france-politique.fr (https://www.france-politique.fr/elections-municipales-2008-nuances-etiquettes-listes.htm), qui reproduisent les définitions ministérielles 2008 ;
- france-politique.fr, page 2014 (https://www.france-politique.fr/elections-municipales-2014-nuances-etiquettes-listes.htm) ;
- pages officielles à consulter manuellement pour confirmation : https://www.archives-resultats-elections.interieur.gouv.fr/resultats/MN2014/nuances.php et https://www.archives-resultats-elections.interieur.gouv.fr/resultats/municipales_2008/index.php.

**Circulaires 2008 et 2014 : non trouvées.** Aucun NOR de circulaire de nuançage municipal 2008 ou 2014 n'apparaît sur Légifrance ni dans les résultats de recherche. La seule circulaire municipale 2014 identifiée (NOR INTA1405029C, « Élection et mandat des assemblées et des exécutifs municipaux et communautaires », https://www.legifrance.gouv.fr/circulaire/id/38393) ne porte pas sur les nuances. Pour 2008/2014, les libellés viennent donc des sources secondaires ci-dessus, qui citent le référentiel du ministère.

**Niveaux de certitude** :
- **Élevée** : bloc lu directement dans la grille officielle du scrutin.
- **Moyenne** : libellé d'époque établi par une source secondaire citant le ministère, et bloc reconstruit selon des grilles officielles concordantes (2020, 2023 et 2026 donnent le même bloc).
- **Faible** : les grilles officielles se contredisent, ou le classement repose sur un jugement.

---

## 1. Constats transversaux (préalables)

| # | Constat | Source | Impact |
|---|---|---|---|
| T1 | **La première grille officielle de blocs date de 2020, pas de 2023.** INTA1931378J, annexe 3 (p. 10), « Grilles de regroupement des nuances politiques par blocs de clivages », répartit déjà les nuances en 6 blocs. Seule différence : le bloc « divers » s'y appelle **AUT**. L'ADR-0005 (décision n° 1), `docs/sources-officielles/nuances/index.md` et CLAUDE.md (gotcha 11) affirment à tort que IOMA2322276J est « la première à formaliser » les blocs. | INTA1931378J p. 7 (§ 3 « Définition des clivages ») et p. 10 | Les municipales 2020 ont un **classement officiel**, pas une reconstruction. |
| T2 | **IOMA2415630C (législatives 2024) ne contient aucune grille de blocs.** L'index des sources la marque « Blocs ? Oui », ce qui est faux (l'ADR-0005 dit « ne contient pas de grille de blocs », ce qui est correct). Les blocs 2024 sont donc une reconstruction, et la grille officielle la plus proche est IOMA2322276J (2023). | IOMA2415630C p. 5-7 | Les sources citées dans `source_bloc` pour 2024 sont à corriger. |
| T3 | **UDI change de bloc d'une grille à l'autre** : CENT en 2020 (INTA1931378J p. 10), **Droite** en 2023 (IOMA2322276J p. 6 : UDI dans le bloc « Droite » ; p. 7 : LUDI « Droite »), CENT en 2026 (INTP2602966C p. 11-12). | 3 grilles | Touche UDI 2022/2024 (législatives) et les groupes UDI du module Législatif. |
| T4 | **« Écologiste » (ECO/LECO) n'est jamais classé à gauche dans les grilles officielles** : AUT en 2020 (ECO et LECO), « Autres » en 2023 (ECO, LECO), DIV en 2026 (ECO, LECO). Seul **VEC/LVEC** (EELV / Les Écologistes) est GAU. La phrase de l'ADR-0005 « Écologistes (ECO/VEC) : GAU sur tous les scrutins » contredit donc les trois grilles officielles. | INTA1931378J p. 10 ; IOMA2322276J p. 6-7 ; INTP2602966C p. 11-12 | Touche LECO 2020/2026 et ECO en législatives. |
| T5 | **CE 31/01/2020 n° 437675 ne fonde pas LDVC → CENT.** L'ordonnance **suspend** la circulaire du 10 déc. 2019 en tant qu'elle attribuait LDVC aux listes simplement soutenues par LREM/MoDem/UDI (fiche `2020-CE_decision_437675.md`, dispositif art. 1er, 2°). Le fondement correct de LDVC 2020 → CENT est INTA1931378J, annexe 3. De même, DLF → DTE est directement établi par INTA1931378J p. 10 (DLF/LDLF dans DTE), et pas seulement par la suspension CE. | CE 437675 ; INTA1931378J p. 10 | Libellés `source_bloc` à corriger. Aucun changement de bloc. |
| T6 | `2020-municipales_INTA1931378J.pdf` **est archivé**, alors que l'index le signale comme « PDF à télécharger manuellement ». | `docs/sources-officielles/nuances/` | Documentation. |

---

## 2. Municipales — codes suspects, année par année

### 2.1 LCOM (Parti communiste français)

| Code | Année | Libellé officiel | Source précise | Classement actuel | Proposé | Certitude |
|---|---|---|---|---|---|---|
| LCOM | 2008 | « Liste communiste » (référentiel 2008 : LEXG, LCOM, LUG, LSOC, LVEC, LDVG, LGC, LAUT, LREG, LCMD, LMC, LMAJ, LDVD, LFN, LEXD) | penombre.org / france-politique.fr (secondaires) ; pas de circulaire publiée | EXG | **GAU** | Moyenne (reconstruction : 2020, 2023 et 2026 classent tous LCOM en GAU) |
| LCOM | 2014 | Liste du Parti communiste français | france-politique.fr 2014 (secondaire) | EXG | **GAU** | Moyenne (même raisonnement) |
| LCOM | 2020 | « liste du Parti communiste français » | INTA1931378J p. 5 (§ 2 b) ; **annexe 3 p. 10 : LCOM → GAU** | EXG | **GAU** | **Élevée** |
| LCOM | 2026 | « Parti communiste français — Listes investies par le Parti communiste Français » | INTP2602966C annexe 2 p. 9 ; **annexe 3 p. 12 : LCOM → GAU** | EXG | **GAU** | **Élevée** |

Écart avec le reste du projet : `COM` = GAU en législatives (toutes années), Hue/Buffet = GAU en présidentielles, GDR/CR/CRCE-K = GAU dans le module Législatif, et le skill `data-viz-politique` dit LCOM = GAU. Le classement municipal EXG est le seul divergent.

### 2.2 LCMD (2008) — code mal décodé

| Code | Année | Libellé officiel | Source précise | Classement actuel | Proposé | Certitude |
|---|---|---|---|---|---|---|
| LCMD | 2008 | **« Liste centre-MoDem »** : « Liste centriste homogène ou à dominante centriste conduite par un candidat UDFD » | penombre.org « Municipales sans politique » ; france-politique.fr 2008 (secondaires reproduisant la définition ministérielle) | GAU (lu comme « Communiste et Divers ») | **CENT** | Moyenne-élevée (définition textuelle concordante dans deux sources ; confirmation possible sur archives-resultats-elections MN2008) |

L'hypothèse « Communiste et Divers » (ADR-0005, § LCMD) n'a aucune source. Le test `tests/test_elections_municipales.py:186-191` fige cette erreur (`assert row[0] == "GAU"`).

### 2.3 LMAJ (2008) — code exclu à tort

| Code | Année | Libellé officiel | Source précise | Classement actuel | Proposé | Certitude |
|---|---|---|---|---|---|---|
| LMAJ | 2008 | **« Liste majorité »** : « Liste conduite par un candidat UMP ou M-NC ou DVD ayant le soutien officiel de l'UMP » | penombre.org ; france-politique.fr 2008 | **Non inséré** (lu comme « liste sortante / majorité municipale ») | **DTE** | Moyenne-élevée |

Conséquence : en 2008 il n'existe pas de code LUMP. **Toutes les listes UMP de 2008 sont donc aujourd'hui sans bloc** (grises sur la carte, absentes des agrégats DTE). Même logique que `MAJ 2007 → DTE` en législatives (`schema_elections.py`, ligne 285). Le test `test_elections_municipales.py:170-172` fige l'exclusion.

### 2.4 LMC, LGC (2008) — ententes de part et d'autre du centre

| Code | Année | Libellé officiel | Source | Actuel | Proposé | Certitude |
|---|---|---|---|---|---|---|
| LMC | 2008 | « Liste majorité-centristes » : entente entre divers éléments de la majorité et divers éléments centristes UDFD | penombre.org ; france-politique.fr | CENT | CENT (maintien) ou DTE | Faible (alliance entre blocs ; la règle 2026, § 3.2 point 3, retient le poids dominant de la liste) |
| LGC | 2008 | « Liste gauche-centristes » : entente entre divers éléments de gauche et divers éléments centristes UDFD | idem | DIV (« trop peu pour classifier ») | GAU ou CENT (symétrie avec LMC) ; DIV ne correspond à aucune définition | Faible |

### 2.5 LUD et LUDI — codes inversés

| Code | Année | Libellé officiel | Source précise | Actuel | Proposé | Certitude |
|---|---|---|---|---|---|---|
| LUD | 2014 | Liste **Union de la droite** (UMP + au moins un autre parti de droite) | france-politique.fr 2014 (secondaire) | CENT (« Union Démocratique / UDI ») | **DTE** | Moyenne (2020, 2023 et 2026 : LUD = DTE) |
| LUD | 2020 | « liste union de la droite » : listes investies par plusieurs partis du bloc de droite, dont LR | INTA1931378J p. 6, p. 9 ; **annexe 3 p. 10 : LUD → DTE** | CENT | **DTE** | **Élevée** |
| LUD | 2026 | « Union de la droite » : listes investies par des partis du bloc de droite, dont LR | INTP2602966C p. 10 ; **annexe 3 p. 12 : LUD → DTE** | **non mappé** (bloc NULL si le code figure dans les données HdF) | **DTE** | **Élevée** |
| LUDI | 2014 | Liste **Union des démocrates et indépendants** (UDI, fondée en 2012) | france-politique.fr 2014 | DIV (« Union Divers ») | **CENT** | Moyenne (2020 et 2026 : CENT ; 2023 : Droite → voir T3) |
| LUDI | 2020 | « liste UDI » | INTA1931378J p. 5, p. 9 ; **annexe 3 p. 10 : LUDI → CENT** | DIV | **CENT** | **Élevée** |
| LUDI | 2026 | « Union des Démocrates et Indépendants — Listes investies par l'UDI » | INTP2602966C p. 9 ; **annexe 3 p. 12 : LUDI → CENT** | DIV | **CENT** | **Élevée** |

### 2.6 LECO (autre écologiste)

| Code | Année | Libellé officiel | Source précise | Actuel | Proposé | Certitude |
|---|---|---|---|---|---|---|
| LECO | 2020 | « autre liste écologiste » (UDE, AEI, Cap 21, etc., **hors EELV**) | INTA1931378J p. 5, p. 9 ; **annexe 3 p. 10 : LECO → AUT** | GAU (« EELV principalement ») | **DIV** | **Élevée** |
| LECO | 2026 | « Écologiste — listes investies ou soutenues par un ou plusieurs partis ou mouvances écologistes (hors Les Écologistes) » | INTP2602966C p. 9 ; **annexe 3 p. 12 : LECO → DIV** | GAU | **DIV** | **Élevée** |

La justification actuelle « EELV principalement » est contraire à la définition officielle : EELV a sa propre nuance LVEC.

### 2.7 Autres codes municipaux mal décodés (libellé seul, bloc correct)

| Code | Année | Libellé projet | Libellé officiel | Source |
|---|---|---|---|---|
| LUDR | 2026 | « Union Droite Républicaine » | « Union des droites pour la République » | INTP2602966C p. 10 |
| LUXD | 2026 | « Union Extrême Droite » | « Union de l'extrême droite » (au moins deux partis parmi RN, REC, UDR) | INTP2602966C p. 10 |
| LUG | 2026 | « Union de la Gauche / NFP » | Union de la gauche : au moins deux partis parmi **PCF, PS, Les Écologistes** (LFI exclue, puisqu'elle est EXG) | INTP2602966C p. 4-5, p. 9 |
| LVEC | 2026 | « Verts / EELV » | « Les Écologistes » | INTP2602966C p. 9 |
| LVEC | 2020 | « Verts / EELV » | « Europe Écologie-Les Verts » (correct) | INTA1931378J p. 9 |
| LDVC | 2020 | source « CE 437675 » | fondement : INTA1931378J annexe 3 (voir T5) | — |

---

## 3. Revue exhaustive — municipales 2026 contre INTP2602966C annexe 3 (p. 12)

Grille officielle des listes (vérifiée sur rendu image) : **EXG** = LEXG, LFI · **GAU** = LCOM, LSOC, LVEC, LUG, LDVG · **DIV** = LECO, LREG, LDIV · **CENT** = LREN, LMDM, LHOR, LUDI, LUC, LDVC · **DTE** = LLR, LUD, LDVD, LDSV · **EXD** = LUDR, LRN, LREC, LUXD, LEXD.

| Code | Projet | Officiel | Verdict |
|---|---|---|---|
| LEXG | EXG | EXG | conforme |
| LFI | EXG | EXG | conforme |
| **LCOM** | **EXG** | **GAU** | **ÉCART** |
| LSOC | GAU | GAU | conforme |
| LVEC | GAU | GAU | conforme |
| LUG | GAU | GAU | conforme |
| LDVG | GAU | GAU | conforme |
| **LECO** | **GAU** | **DIV** | **ÉCART** |
| LDIV | DIV | DIV | conforme |
| **LUDI** | **DIV** | **CENT** | **ÉCART** |
| LHOR | CENT | CENT | conforme |
| LUC | CENT | CENT | conforme |
| LDVC | CENT | CENT | conforme |
| LLR | DTE | DTE | conforme |
| LDVD | DTE | DTE | conforme |
| LUDR | EXD | EXD | conforme |
| LRN | EXD | EXD | conforme |
| LUXD | EXD | EXD | conforme |
| LEXD | EXD | EXD | conforme |
| LREN, LMDM, LUD, LDSV, LREC, LREG | non mappés | CENT, CENT, DTE, DTE, EXD, DIV | **Lacune** : à vérifier contre les nuances distinctes du Parquet HdF 2026. Si l'un de ces codes est présent, ses listes sont aujourd'hui sans bloc. |

**Bilan 2026 : 3 écarts sur 19 codes mappés, et 6 codes officiels sans mapping.**

### Revue 2020 contre INTA1931378J annexe 3 (p. 10) — hors mission stricte, mais bloc officiel disponible (T1)

Grille officielle des listes : **EXG** = LEXG · **GAU** = LCOM, LFI, LSOC, LRDG, LDVG, LUG, LVEC · **AUT** = LECO, LDIV, LREG, LGJ · **CENT** = LREM, LMDM, LUDI, LUC, LDVC · **DTE** = LLR, LUD, LDVD, LDLF · **EXD** = LRN, LEXD.

Écarts 2020 : **LCOM** (EXG → GAU), **LECO** (GAU → DIV), **LUD** (CENT → DTE), **LUDI** (DIV → CENT). Les 15 autres codes mappés sont conformes. NC et LNC ne figurent pas dans la grille officielle : leur exclusion reste cohérente. Codes officiels non mappés : LREG, LGJ, LDLF (à vérifier dans les données).

---

## 4. Revue exhaustive — législatives 2024 contre IOMA2415630C

IOMA2415630C ne fournit **aucun bloc** (T2). Contrôle en deux temps : (a) le code existe-t-il dans l'annexe 1 ? (b) quel bloc donne la grille officielle la plus proche, soit IOMA2322276J (2023, antérieure) et, pour recoupement, INTP2602966C (2026, postérieure) ?

| Code | Libellé officiel 2024 (annexe 1 p. 5/7) | Projet | 2023 (IOMA2322276J) | 2026 (INTP2602966C) | Verdict |
|---|---|---|---|---|---|
| COM | Parti communiste français | GAU | Gauche | GAU | conforme |
| DIV | Divers | DIV | Autres | DIV | conforme |
| DSV | Droite souverainiste (Debout la France…) | DTE | DLF = Droite | DTE | conforme (la justification « IOMA2415630C : souverainistes ≠ EXD » est inexacte : la circulaire 2024 ne classe rien) |
| DVC | Divers centre | CENT | Centre | CENT | conforme |
| DVD | Divers droite | DTE | Droite | DTE | conforme |
| DVG | Divers gauche | GAU | Gauche | GAU | conforme |
| **ECO** | Écologiste (« autres candidats de sensibilité écologiste », VEC étant distinct) | **GAU** | **Autres** | **DIV** | **ÉCART** : proposé DIV, certitude élevée (les deux grilles concordent) |
| ENS | Ensemble (deux partis du centre) | CENT | LENS = Centre | — | conforme |
| EXD | Extrême droite | EXD | EXD | EXD | conforme |
| EXG | Extrême gauche | EXG | EXG | EXG | conforme |
| FI | La France insoumise | GAU | **Gauche** | EXG | conforme à la règle « de l'époque » (grille antérieure = 2023) |
| HOR | Horizons | CENT | Centre | CENT | conforme |
| LR | Les Républicains | DTE | Droite | DTE | conforme |
| RDG | Parti radical de gauche | GAU | Gauche | GAU | conforme |
| REC | Reconquête ! | EXD | EXD | EXD | conforme |
| REG | Régionalistes | DIV | Autres | DIV | conforme |
| RN | Rassemblement national | EXD | EXD | EXD | conforme |
| SOC | Parti socialiste | GAU | Gauche | GAU | conforme |
| **UDI** | UDI | **CENT** | **Droite** | CENT | **À TRANCHER** (T3) : 2023 = DTE, 2026 = CENT. Certitude faible |
| UG | Union de la gauche | GAU | LUG = Gauche | LUG = GAU | conforme |
| UXD | Union de l'extrême droite (OCR p. 5 « UXO », p. 7 « UXD ») | EXD | LUXD = EXD | LUXD = EXD | conforme |
| VEC | Les Écologistes | GAU | Gauche | GAU | conforme |
| REN, MDM | Renaissance, Modem | non mappés | Centre | CENT | Lacune si présents dans les données (en pratique, candidats souvent nuancés ENS) |

**Bilan 2024 : 1 écart net (ECO), 1 cas à trancher (UDI), 2 codes officiels sans mapping (REN, MDM).**

### Contrôles complémentaires sur les autres années législatives et présidentielles (reconstruction)

| Code / candidat | Année | Projet | Grille de référence | Proposé | Certitude |
|---|---|---|---|---|---|
| ECO | 2002, 2007, 2012 | GAU | Ces années ont aussi VEC (Verts/EELV), donc ECO = écologistes non-Verts. 2020 (AUT), 2023 (Autres) et 2026 (DIV) concordent | DIV | Moyenne |
| ECO | 2017 | GAU | Pas de code VEC dans les données 2017 : EELV est nuancé ECO | GAU (maintien défendable) ou DIV | Faible |
| ECO | 2022 | GAU | INTA2212053C p. 5 : ECO **inclut** EELV (« Europe-Ecologie-Les Verts, UDE, AEI, Cap 21, Génération écologie, parti animaliste… »), mais EELV-NUPES est nuancé NUP | DIV ou GAU | Faible |
| UDI | 2017, 2022 | CENT | 2020 = CENT ; 2023 = Droite | CENT (2017, grille la plus proche = 2020) ; à trancher pour 2022 | Moyenne / faible |
| Lepage (LEPA, Cap 21) | 2002 prés. | CENT | INTA1931378J p. 8 : « Rassemblement citoyen-CAP 21 » rangé dans ECO → AUT ; INTA2212053C : Cap 21 dans ECO | DIV | Moyenne |
| CPNT (+ Saint-Josse, Nihous) | 2002, 2007 | DIV | INTA1931378J p. 8 : « Chasse, pêche, nature et tradition » dans **DVD** → DTE (reflète l'alliance avec LR postérieure à 2010) | DIV (maintien, à l'époque CPNT était autonome) ou DTE | Faible |
| PRV (Parti radical valoisien) | 2012 | DTE | 2020 : MR (Mouvement radical) → CENT ; 2026 : PR → CENT | CENT | Moyenne |
| MAJ | 2007 | DTE | cohérent avec la proposition LMAJ 2008 → DTE | conforme | — |

---

## 5. Module Législatif — correspondance groupe → bloc

### 5.1 Constat

- `legislatif_datan.py` (lignes 46-88) : dictionnaire `_GROUPE_BLOCS` **indépendant de la législature**. Clé = `groupeAbrev` de la ligne Datan, qui porte la dernière législature du député (`legislatureLast`, ligne 189). Valeur par défaut `DIV` pour tout groupe absent (ligne 194).
- `FI` (XVe, 2017-2022), `LFI-NUPES` (XVIe, 2022-2024) et `LFI-NFP` (XVIIe, 2024-) → **EXG**. C'est contraire à l'ADR-0005 (règle n° 3 et § « Cohérence interne (règle LFI) » : FI 2017, NUP 2022 et FI/UG 2024 = GAU) et au module Élections.
- Les sigles LFI changeant à chaque législature, **un dictionnaire par sigle suffit techniquement** à appliquer la règle de l'époque pour LFI. Une clé (groupe, législature) n'est nécessaire que si Mathias veut distinguer un même sigle selon la législature (UDI, NI).
- `RRDP` (XIVe, 2012-2017, radicaux de gauche alliés au PS) → DIV. Le PRG (RDG) est GAU dans toutes les grilles (2020 p. 10, 2023 p. 6, 2026 p. 11).
- Groupes probablement absents du dictionnaire, donc classés DIV par défaut (à vérifier par `SELECT DISTINCT groupe_sigle, legislature FROM leg_elus WHERE chambre='AN' AND bloc_politique='DIV'`) : `EDS` (Écologie Démocratie Solidarité, XVe), `LC` (Les Constructifs, XVe), éventuellement `C.R.` (le dictionnaire contient `CR`).

**Sénat** (`legislatif_senat.py`, lignes 42-49) : seuls 6 groupes sont mappés (CRCE-K, SER, UC, Les Indépendants, Les Républicains, NI). Le bilan de phase F (`reports/session-2026-06-22_phase-f-cloture.md`, l. 48) compte **55 sénateurs actifs en DIV**. Ce volume correspond vraisemblablement aux groupes **RDPI** (Renaissance), **GEST** (écologistes) et **RDSE**, non mappés, plus les NI. C'est une inférence d'effectifs, à confirmer en base. Les anciens sénateurs (groupes historiques CRC, SOC, UMP, UC-UDF, RDSE…) tombent aussi en DIV.

### 5.2 Table (groupe, législature) → bloc proposée

Règle : bloc de la nuance du parti dominant du groupe, selon la grille officielle la plus proche de l'élection de la législature (2020 pour 2017 ; 2023 pour 2022 et 2024). Les grilles citées sont INTA1931378J p. 10, IOMA2322276J p. 6 et INTP2602966C p. 11.

| Lég. | Période | Groupe (sigle Datan) | Actuel | Proposé | Fondement | Certitude |
|---|---|---|---|---|---|---|
| 12 | 2002-07 | UMP | DTE | DTE | LR/UMP = DTE (toutes grilles) | Élevée |
| 12 | | SOC | GAU | GAU | SOC = GAU | Élevée |
| 12 | | UDF | CENT | CENT | cohérent UDF 2002 = CENT (législatives) | Moyenne |
| 12 | | CR (Communistes et républicains) | GAU | GAU | COM = GAU | Élevée |
| 13 | 2007-12 | UMP | DTE | DTE | idem | Élevée |
| 13 | | SRC | GAU | GAU | SOC = GAU | Élevée |
| 13 | | GDR | GAU | GAU | COM = GAU | Élevée |
| 13 | | NC (Nouveau Centre) | CENT | CENT | cohérent NCE 2012 = CENT | Moyenne |
| 14 | 2012-17 | SRC / SER | GAU | GAU | | Élevée |
| 14 | | UMP / LES-REP / LR | DTE | DTE | | Élevée |
| 14 | | UDI | CENT | CENT | 2020 : UDI = CENT | Moyenne |
| 14 | | ECOLO | GAU | GAU | VEC = GAU | Élevée |
| 14 | | GDR | GAU | GAU | | Élevée |
| 14 | | **RRDP** | **DIV** | **GAU** | RDG = GAU (2020, 2023, 2026) | Moyenne |
| 15 | 2017-22 | LAREM | CENT | CENT | REM = CENT (2020) | Élevée |
| 15 | | MODEM | CENT | CENT | | Élevée |
| 15 | | UDI-AGIR / UDI_I / AGIR-E | CENT | CENT | 2020 : UDI et AGR = CENT | Élevée |
| 15 | | LR | DTE | DTE | | Élevée |
| 15 | | NG / SOC | GAU | GAU | | Élevée |
| 15 | | **FI** | **EXG** | **GAU** | 2020 p. 10 : FI/LFI = GAU ; ADR-0005 : FI 2017 = GAU | **Élevée** |
| 15 | | GDR | GAU | GAU | | Élevée |
| 15 | | LT (Libertés et Territoires) | DIV | DIV | groupe composite, sans nuance officielle | Faible |
| 15 | | EDS (si présent) | DIV (défaut) | à trancher (GAU ou CENT) | ex-LREM, sans nuance officielle | Faible |
| 16 | 2022-24 | RE / DEM / HOR | CENT | CENT | 2023 : REN, MDM, HOR = Centre | Élevée |
| 16 | | LR | DTE | DTE | | Élevée |
| 16 | | RN | EXD | EXD | | Élevée |
| 16 | | **LFI-NUPES** | **EXG** | **GAU** | 2023 p. 6 : FI = Gauche ; NUP 2022 = GAU dans le projet | **Élevée** |
| 16 | | SOC / ECOLO / GDR-NUPES | GAU | GAU | | Élevée |
| 16 | | LIOT | DIV | DIV | composite | Faible |
| 17 | 2024- | EPR / DEM / HOR | CENT | CENT | | Élevée |
| 17 | | DR | DTE | DTE | | Élevée |
| 17 | | RN | EXD | EXD | | Élevée |
| 17 | | UDR / UDDPLR | EXD | EXD | nuance UXD 2024 → EXD (2023 : LUXD = EXD) ; 2026 : UDR = EXD, validé par CE 512694 | Élevée |
| 17 | | **LFI-NFP** | **EXG** | **Option A : GAU** (grille de l'élection de 2024) / **Option B : EXG** (grille en vigueur depuis le 2 fév. 2026) | A : ADR-0005 (FI 2024 = GAU) et CE 512694 (« les blocs permettent l'agrégation d'une élection précise ») ; B : classement administratif actuel | Décision de Mathias |
| 17 | | SOC / ECOS / GDR | GAU | GAU | | Élevée |
| 17 | | LIOT | DIV | DIV | | Faible |

**Sénat — proposition**

| Groupe | Actuel | Proposé | Fondement | Certitude |
|---|---|---|---|---|
| CRCE-K | GAU | GAU | COM = GAU | Élevée |
| SER | GAU | GAU | SOC = GAU | Élevée |
| GEST (écologistes) | DIV (défaut) | **GAU** | VEC = GAU (2023 p. 6) | Élevée |
| RDPI (Renaissance) | DIV (défaut) | **CENT** | REN = Centre (2023) | Élevée |
| UC | CENT | CENT | UDI/centristes : Centre en 2020 et 2026, Droite en 2023 | Moyenne |
| Les Indépendants – République et Territoires | DTE | à trancher : CENT (groupe rattaché à Horizons, HOR = Centre en 2023 et 2026) ou DTE | composite | Faible |
| RDSE | DIV (défaut) | DIV (maintien) ou CENT | composite radical | Faible |
| Les Républicains | DTE | DTE | | Élevée |
| NI | DIV (+ 2 overrides → EXD) | inchangé | | — |

---

## 6. Cohérence transversale

### 6.1 PCF

| Module | Code | Années | Bloc actuel | Cohérent avec les grilles officielles ? |
|---|---|---|---|---|
| Présidentielles | HUE, BUFF | 2002, 2007 | GAU | oui |
| Législatives | COM | 2002-2024 | GAU | oui |
| Législatives | FG | 2012 | GAU | oui |
| **Municipales** | **LCOM** | **2008-2026** | **EXG** | **non** (2020 et 2026 officiels = GAU) |
| Municipales | LCMD | 2008 | GAU (lu comme « communiste ») | code mal décodé : centre-MoDem |
| Législatif AN | CR, GDR, GDR-NUPES | 12e-17e | GAU | oui |
| Législatif Sénat | CRCE-K | actuel | GAU | oui |
| Skill data-viz-politique | LCOM | 2026 | GAU | oui |

**Seule divergence : LCOM municipal.**

### 6.2 Écologistes

| Module | Code | Années | Bloc actuel | Grilles officielles |
|---|---|---|---|---|
| Présidentielles | MAME, VOYN, BOVE, JOLY, JADOT | 2002-2022 | GAU | Verts/EELV = VEC → GAU : cohérent |
| Présidentielles | LEPA (Cap 21) | 2002 | CENT | Cap 21 ∈ ECO → AUT/DIV (2020 p. 8 et p. 10) : **divergent** |
| Législatives | VEC | 2002, 2007, 2012, 2024 | GAU | cohérent |
| Législatives | ECO | 2002-2024 | GAU | ECO → AUT/Autres/DIV (2020, 2023, 2026) : **divergent** (sauf 2017-2022, où ECO inclut EELV : cas discutable) |
| Municipales | LVEC | 2008-2026 | GAU | cohérent |
| Municipales | LECO | 2020, 2026 | GAU | **officiellement DIV** : divergent |
| Législatif | ECOLO, ECOS | 14e, 16e, 17e | GAU | cohérent |
| Législatif Sénat | GEST | actuel | DIV (défaut) | **divergent** (devrait être GAU) |
| Skill data-viz-politique | ECO, LECO | 2026 | DIV | cohérent avec l'officiel, mais **en contradiction avec le code** |

**Double divergence** : les écologistes « autres » (ECO/LECO) sont en GAU dans le code alors qu'ils sont DIV dans l'officiel. À l'inverse, le groupe sénatorial écologiste (GEST) est en DIV alors qu'il devrait être GAU. La phrase de l'ADR-0005 « Écologistes (ECO/VEC) GAU sur tous les scrutins » est à réviser.

### 6.3 UDI / centre

- UDI : CENT partout dans le code (législatives, Législatif AN, UC au Sénat). LUDI municipal : DIV (erreur). La grille 2023 place UDI à Droite (T3). La question se pose donc pour 2022, 2024 et la XVIe législature.

### 6.4 Impact estimé

Non mesuré : la base DuckDB n'est pas disponible dans ce conteneur. Requêtes suggérées pour chiffrer avant décision :
```sql
SELECT e.annee, rc.nuance, COUNT(DISTINCT rc.code_commune) AS communes, SUM(rc.voix) AS voix
FROM resultats_candidats rc JOIN elections e USING (id_election)
WHERE e.type_scrutin='muni' AND rc.nuance IN ('LCOM','LCMD','LMAJ','LMC','LGC','LUD','LUDI','LECO',
      'LREN','LMDM','LDSV','LREC','LREG','LGJ','LDLF')
GROUP BY ALL ORDER BY ALL;
SELECT legislature, groupe_sigle, COUNT(*) FROM leg_elus
WHERE bloc_politique='DIV' GROUP BY ALL ORDER BY ALL;   -- AN et Sénat
```

### 6.5 Tests qui figent les classements actuels

- `tests/test_elections_municipales.py:111-122` : 67 entrées (le total changera si LMAJ et LUD 2026 sont ajoutés).
- `tests/test_elections_municipales.py:170-172` : LMAJ doit être absent.
- `tests/test_elections_municipales.py:186-191` : LCMD 2008 = GAU.

---

## 7. Décisions à soumettre à Mathias (questions fermées)

**Municipales**
1. Reclasser **LCOM** en **GAU** pour 2008, 2014, 2020 et 2026 (officiel pour 2020 et 2026) ? — oui / non
2. Reclasser **LUDI** en **CENT** pour 2014, 2020 et 2026 (officiel pour 2020 et 2026) ? — oui / non
3. Reclasser **LUD** en **DTE** pour 2014 et 2020, et ajouter **LUD 2026 → DTE** ? — oui / non
4. Reclasser **LECO** en **DIV** pour 2020 et 2026 (officiel) ? — oui / non
5. Reclasser **LCMD 2008** (« liste centre-MoDem ») de GAU en **CENT** ? — oui / non
6. Insérer **LMAJ 2008** (« liste majorité », UMP) avec le bloc **DTE**, en levant son exclusion ? — oui / non
7. **LGC 2008** (entente gauche-centristes) : passer de DIV à GAU ? — oui / non (si non : CENT ou maintien DIV ?)
8. **LMC 2008** (entente majorité-centristes) : maintenir CENT ? — oui / non (si non : DTE)
9. Ajouter les codes officiels 2026 et 2020 sans mapping (LREN, LMDM, LDSV, LREC, LREG, LGJ, LDLF), selon les annexes 3, **si** une requête montre qu'ils sont présents dans les données HdF ? — oui / non
10. Faire vérifier manuellement par Mathias, sur archives-resultats-elections.interieur.gouv.fr (MN2008 et MN2014), les libellés 2008/2014 établis ici par sources secondaires, avant application ? — oui / non

**Législatives et présidentielles**
11. Reclasser **ECO** en **DIV** pour 2024 (grilles 2023 et 2026 concordantes) ? — oui / non
12. Reclasser **ECO** en **DIV** pour 2002, 2007 et 2012 (années où VEC existe séparément) ? — oui / non
13. Maintenir **ECO** en **GAU** pour 2017 et 2022 (ECO englobe EELV dans ces grilles) ? — oui / non
14. **UDI 2022 et 2024** : maintenir CENT (grille 2026) plutôt que DTE (grille 2023, antérieure) ? — oui / non
15. Reclasser **Lepage 2002 (Cap 21)** de CENT en **DIV** ? — oui / non
16. Reclasser **PRV 2012** de DTE en **CENT** ? — oui / non
17. Maintenir **CPNT 2002/2007** (et Saint-Josse, Nihous) en DIV malgré la grille 2020 (CPNT dans DVD) ? — oui / non

**Module Législatif**
18. Reclasser les groupes **FI (XVe)** et **LFI-NUPES (XVIe)** en **GAU** ? — oui / non
19. Pour **LFI-NFP (XVIIe)**, retenir la grille de l'élection de 2024 (**GAU**) plutôt que la grille en vigueur depuis 2026 (EXG) ? — oui / non
20. Reclasser **RRDP (XIVe)** en **GAU** ? — oui / non
21. Mapper au Sénat **GEST → GAU** et **RDPI → CENT** ? — oui / non
22. Classer le groupe sénatorial **Les Indépendants** en CENT (rattachement Horizons) ? — oui / non (si non : maintien DTE)
23. Faire passer la correspondance groupe → bloc à une clé **(groupe, législature)** documentée dans un ADR (le module Législatif n'en a pas, cf. état des lieux § 3.6) ? — oui / non

**Documentation**
24. Réviser l'ADR-0005 (ADR de révision) pour : (a) dater la première grille de blocs à INTA1931378J (2020) ; (b) remplacer « ECO/VEC GAU sur tous les scrutins » par « VEC GAU, ECO DIV selon les grilles officielles » ; (c) corriger les définitions de LCMD et LMAJ ; (d) re-sourcer LDVC 2020 et DLF sur INTA1931378J plutôt que sur CE 437675 ? — oui / non
25. Corriger `docs/sources-officielles/nuances/index.md` (INTA1931378J archivé en PDF ; IOMA2415630C « Blocs ? Non ») et le gotcha 11 de CLAUDE.md ? — oui / non
