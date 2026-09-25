# 0010 — Révision des classements nuances → blocs (élections)

Date : 2026-09-24
Statut : Accepté — Révise 0005
Décideurs : Mathias (lots 1, 2, 3 et 5 du 2026-09-24) ; doctrine du lot 3 fixée par le
directeur de projet sur délégation de Mathias
Addendum 2026-09-25 : exécution du lot 2 (municipales 2008) après vérification des libellés
officiels sur les archives du ministère — complément d'exécution de la même décision, voir
(d) « Lot 2 » et (e) point 1.

> Sources de l'instruction : `reports/verification-nuances-2026-09-24.md` (questions Q1 à
> Q25), `reports/synthese-vague-1-2026-09-24.md` (§ 3). Grilles officielles relues sur
> rendu image le 2026-09-24 : INTA1931378J p. 10, IOMA2322276J p. 6-7, INTP2602966C p. 12
> (PDF dans `docs/sources-officielles/nuances/`).
> Périmètre : module Élections (présidentielles, législatives, municipales). Le module
> Législatif (correspondance groupe parlementaire → bloc) relève d'une décision séparée
> (lot 4).

## Contexte

L'ADR-0005 a fixé la règle du projet : 6 blocs officiels du ministère de l'Intérieur et
classement « officiel de l'époque ». La vérification du 2026-09-24 a établi que
plusieurs affirmations de l'ADR-0005, et plusieurs classements qui en découlent, sont
inexacts :

1. L'ADR-0005 date la première grille officielle de blocs de la circulaire IOMA2322276J
   (sénatoriales 2023). Or la circulaire **INTA1931378J** du 3 février 2020 (municipales
   2020) contient déjà, en annexe 3 (p. 10), des « grilles de regroupement des nuances
   politiques par blocs de clivages » en 6 blocs, le bloc « divers » s'y nommant `AUT`.
2. **IOMA2415630C** (législatives 2024) ne contient **aucune** grille de blocs (annexe 1 :
   liste de 24 nuances). L'index des sources indiquait le contraire.
3. La règle « Écologistes (ECO/VEC) : GAU sur tous les scrutins » contredit les trois
   grilles officielles : `ECO`/`LECO` (écologistes autres que les Verts/EELV) y sont
   `AUT` (2020), « Autres » (2023) et `DIV` (2026) ; seuls `VEC`/`LVEC` sont `GAU`.
4. Les municipales 2020 et 2026, couvertes par une grille officielle, comportaient quatre
   écarts avec elle (`LCOM`, `LUDI`, `LUD`, `LECO`) et des codes officiels sans mapping.
5. L'ADR-0005 ne disait pas comment classer un scrutin qu'aucune grille ne couvre
   (toutes les présidentielles et législatives du projet, les municipales 2008 et 2014).

## Décision

### (a) Grilles officielles de blocs

Trois circulaires, et trois seulement, contiennent une grille de blocs :

| NOR | Date | Scrutin | Localisation | Nom du bloc « divers » |
|-----|------|---------|--------------|------------------------|
| **INTA1931378J** | 3 fév. 2020 | Municipales 2020 | annexe 3, p. 10 (individuelles et listes) | `AUT` |
| IOMA2322276J | 16 août 2023 | Sénatoriales 2023 | colonne « Bloc » des annexes 1 et 2, p. 6-7 | « Autres » |
| INTP2602966C | 2 fév. 2026 | Municipales 2026 | annexe 3, p. 11 (individuelles) et p. 12 (listes) | `DIV` |

`AUT` et « Autres » sont stockés sous le code projet `DIV`. INTA2212053C (législatives
2022) et IOMA2415630C (législatives 2024) ne contiennent pas de grille de blocs. La
première grille officielle est donc celle de **2020**, et non celle de 2023. Cela remplace
la décision n° 1 (origine des blocs) et la décision n° 4 (« reconstruction avant 2023 »)
de l'ADR-0005. Le principe du classement « de l'époque » (décision n° 3) est maintenu.

### (b) Doctrine pour classer un code

1. **Une grille officielle couvre le scrutin** : elle s'applique telle quelle
   (municipales 2020 et 2026).
2. **Aucune grille ne couvre le scrutin** : on applique la grille officielle la plus
   proche dans le temps, de préférence **antérieure** au scrutin, sinon la suivante. Condition :
   le code, ou la formation, doit désigner **la même famille politique** dans les deux
   textes. Si le sens diffère entre textes, c'est le sens du code à l'époque du scrutin
   qui prime. Exemple : en 2017 et en 2022, faute de code `VEC`, `ECO` englobe EELV.
3. **Aucune grille pertinente** : le classement reconstruit existant est maintenu, avec
   une justification dans `source_bloc`.

Grille de référence qui en découle : INTA1931378J (2020) pour tous les scrutins de 2002
à 2022 — grille antérieure la plus proche pour les scrutins de 2022, seule grille
disponible (postérieure) pour ceux de 2002 à 2017 et les municipales 2008 et 2014 ;
IOMA2322276J (2023) pour les législatives 2024.

Chaque entrée reclassée porte dans `source_bloc` la grille appliquée, la mention
`ADR-0010` et l'ancien bloc (`avant : XXX`).

### (c) Règle des écologistes (corrige l'ADR-0005)

- `VEC` / `LVEC` (Les Verts, EELV, Les Écologistes) → **GAU** sur tous les scrutins
  (grilles 2020, 2023 et 2026 concordantes).
- `ECO` / `LECO` (autres écologistes : UDE, AEI, Cap 21, Génération écologie…) → **DIV**
  selon les grilles, **sauf** pour les législatives 2017 et 2022, où `ECO` englobe EELV
  (pas de code `VEC` ; INTA2212053C annexe 1 cite « Europe-Ecologie-Les Verts » sous
  `ECO`). Ce sens diffère de celui de la grille 2020, donc le classement `GAU` est
  maintenu (règle 2, sens de l'époque).
- Candidats présidentiels : Mamère, Voynet, Bové, Joly, Jadot (Verts/EELV) → GAU ;
  Lepage (Cap 21) → DIV.

### (d) Reclassements appliqués

**Changements de bloc (18)**

| Code | Scrutin | Année | Avant | Après | Source | Règle |
|------|---------|-------|-------|-------|--------|-------|
| LCOM | muni | 2008 | EXG | GAU | INTA1931378J annexe 3 (grille la plus proche) | 2 — lot 1 |
| LCOM | muni | 2014 | EXG | GAU | INTA1931378J annexe 3 (grille la plus proche) | 2 — lot 1 |
| LCOM | muni | 2020 | EXG | GAU | INTA1931378J annexe 3 | 1 — lot 1 |
| LCOM | muni | 2026 | EXG | GAU | INTP2602966C annexe 3 | 1 — lot 1 |
| LUDI | muni | 2014 | DIV | CENT | INTA1931378J annexe 3 (grille la plus proche) | 2 — lot 1 |
| LUDI | muni | 2020 | DIV | CENT | INTA1931378J annexe 3 | 1 — lot 1 |
| LUDI | muni | 2026 | DIV | CENT | INTP2602966C annexe 3 | 1 — lot 1 |
| LUD | muni | 2014 | CENT | DTE | INTA1931378J annexe 3 (grille la plus proche) | 2 — lot 1 |
| LUD | muni | 2020 | CENT | DTE | INTA1931378J annexe 3 | 1 — lot 1 |
| LECO | muni | 2020 | GAU | DIV | INTA1931378J annexe 3 (`AUT`) | 1 — lot 1 |
| LECO | muni | 2026 | GAU | DIV | INTP2602966C annexe 3 | 1 — lot 1 |
| ECO | legi | 2002 | GAU | DIV | INTA1931378J (ECO hors EELV → AUT) ; VEC distinct en 2002 | 2 — lot 3 |
| ECO | legi | 2007 | GAU | DIV | idem ; VEC distinct en 2007 | 2 — lot 3 |
| ECO | legi | 2012 | GAU | DIV | idem ; VEC distinct en 2012 | 2 — lot 3 |
| ECO | legi | 2024 | GAU | DIV | IOMA2322276J (ECO → Autres), même définition qu'en 2024 ; INTP2602966C concorde | 2 — lot 3 |
| UDI | legi | 2024 | CENT | DTE | IOMA2322276J annexe 1 (UDI → Droite), grille antérieure la plus proche | 2 — lot 3 |
| PRV | legi | 2012 | DTE | CENT | INTA1931378J : Mouvement radical (MR, successeur du PRV) → CENT ; INTP2602966C : PR → CENT | 2 — lot 3 |
| LEPA (Lepage) | pres | 2002 | CENT | DIV | INTA1931378J : « Rassemblement citoyen-CAP 21 » rangé dans ECO → AUT | 2 — lot 3 |

**Codes ajoutés (10, lot 1 — Q9)** : codes de liste des grilles officielles jusque-là
sans mapping. Ils sont sans effet s'ils n'apparaissent pas dans les données HdF ; s'ils
y apparaissent, leurs listes obtiennent un bloc au lieu de « Non classé ».

| Code | Année | Bloc | Source |
|------|-------|------|--------|
| LREG | 2020 | DIV | INTA1931378J annexe 3 (`AUT`) |
| LGJ | 2020 | DIV | INTA1931378J annexe 3 (`AUT`) |
| LMDM | 2020 | CENT | INTA1931378J annexe 3 |
| LDLF | 2020 | DTE | INTA1931378J annexe 3 |
| LUD | 2026 | DTE | INTP2602966C annexe 3 |
| LREN | 2026 | CENT | INTP2602966C annexe 3 |
| LMDM | 2026 | CENT | INTP2602966C annexe 3 |
| LDSV | 2026 | DTE | INTP2602966C annexe 3 |
| LREC | 2026 | EXD | INTP2602966C annexe 3 |
| LREG | 2026 | DIV | INTP2602966C annexe 3 |

Les listes municipales 2020 (23 codes) et 2026 (25 codes) sont désormais identiques aux
grilles officielles des listes, code pour code et bloc pour bloc
(`tests/test_elections_nuances_adr0010.py`). Les grilles de nuances individuelles (COM,
SOC… pour les candidats des petites communes) n'ont pas été ajoutées au référentiel
municipal : les données HdF chargées n'en font pas usage à la connaissance du projet
(à contrôler, voir Conséquences).

**Classements examinés et maintenus (lot 3)** — `source_bloc` réécrit :

| Code | Scrutin | Année | Bloc | Motif |
|------|---------|-------|------|-------|
| ECO | legi | 2017 | GAU | ECO englobe EELV (pas de code VEC) ; sens différent de la grille 2020 → sens de l'époque (règle 2) |
| ECO | legi | 2022 | GAU | idem (INTA2212053C annexe 1) ; certitude faible, voir points ouverts |
| UDI | legi | 2017 | CENT | INTA1931378J (2020) : UDI → CENT, grille la plus proche |
| UDI | legi | 2022 | CENT | INTA1931378J (2020) : UDI → CENT, grille antérieure la plus proche |
| CPNT | legi | 2002, 2007 | DIV | La grille 2020 range CPNT dans DVD du fait de son association à l'UMP/LR à partir de 2010. En 2002 et 2007, CPNT avait une nuance propre et se présentait de façon autonome, contre la droite parlementaire : ce n'est pas la même position politique, donc la règle 2 ne s'applique pas. Règle 3 : maintien |
| SAIN (Saint-Josse) | pres | 2002 | DIV | idem CPNT |
| NIHO (Nihous) | pres | 2007 | DIV | idem CPNT |

**Corrections de justification sans changement de bloc** : `LDVC 2020` (fondement :
INTA1931378J annexe 3 ; l'ordonnance CE n° 437675 a *suspendu* l'attribution de LDVC aux
listes simplement soutenues), `DSV 2024` (IOMA2415630C ne classe rien : IOMA2322276J
DLF → Droite, INTP2602966C DSV → DTE), `VEC 2002`, Jadot 2022 (`candidats_presidentielle`),
libellés officiels 2026 de `LUDR`, `LUXD`, `LUG`, `LVEC`.

**Lot 2 — municipales 2008 (addendum 2026-09-25)** : appliqué après vérification des
libellés officiels sur archives-resultats-elections.interieur.gouv.fr (pages « nuances »
MN2008 et MN2014, texte archivé dans
`docs/sources-officielles/nuances/2008-municipales_nuances_archives-interieur.md` et
`2014-municipales_nuances_archives-interieur.md` ; instruction :
`reports/verification-nuances-mac-2008-2014.md`).

| Code | Année | Libellé officiel | Avant | Après | Règle |
|------|-------|------------------|-------|-------|-------|
| LCMD | 2008 | Liste centre-MoDem | GAU | **CENT** | 2 — grille 2020 LMDM → CENT, même formation |
| LMAJ | 2008 | Liste de la majorité | exclu (NULL) | **DTE** | 2 — grille 2020 LLR/LUD → DTE, même famille (UMP/NC) ; cohérent avec `MAJ 2007 → DTE` |
| LGC | 2008 | Liste gauche-centristes | DIV | DIV (maintenu) | 3 — entente sans équivalent dans les grilles (voir ci-dessous) |
| LMC | 2008 | Liste majorité-centristes | CENT | CENT (maintenu) | 3 — idem |
| LREG | 2008 | Liste régionaliste | absent | **DIV** (ajout) | 2 — grille 2020 LREG → AUT |
| LEXD | 2008 | Liste d'extrême droite | absent | **EXD** (ajout) | 2 — grille 2020 LEXD → EXD |

`LGC` : la vérification proposait CENT par symétrie avec `LMC`. La doctrine (b) ne le
permet pas : aucune grille officielle ne contient de code d'entente gauche-centre, donc la
règle 2 (même famille dans la grille) est inapplicable et la règle 3 maintient le
classement reconstruit existant (DIV). Le même raisonnement maintient `LMC` en CENT. Poids
HdF négligeable (une commune chacun). `LREG` et `LEXD` complètent le référentiel officiel
2008 (15 codes, identique à la liste des archives) ; absents des données HdF, ils sont
sans effet (cohérence avec Q9). Le `source_bloc` de chaque code 2008 et 2014 cite désormais
« libellé officiel archives ministère (vérif. 2026-09-25) » ; les libellés 2014 confirment
les reclassements `LCOM`, `LUD`, `LUDI` du lot 1. `NC` et `LNC` restent exclus.

Volumes après révision (addendum 2026-09-25) : `nuances_harmonisees` = 229 entrées
(38 présidentielles, 111 législatives, 80 municipales : 15 en 2008, 17 en 2014, 23 en 2020,
25 en 2026) ; `candidats_presidentielle` = 23 entrées (inchangé). Avant l'addendum :
226 entrées, dont 77 municipales (12 en 2008).

### (e) Points ouverts

1. ~~**LCMD, LMAJ, LGC, LMC (municipales 2008)**~~ — **résolu le 2026-09-25** : libellés
   officiels vérifiés sur archives-resultats-elections.interieur.gouv.fr (MN2008).
   LCMD GAU → CENT ; LMAJ exclu → DTE (43 communes, 114 281 voix HdF au 1er tour) ;
   LGC (DIV) et LMC (CENT) maintenus par la règle 3 ; ajout de LREG → DIV et
   LEXD → EXD. Détail en (d), « Lot 2 ».
2. **Clé `(nuance, annee)` sans `type_scrutin`** (audit M5) : la clé ne distingue pas
   deux scrutins de la même année. Un garde-fou (`_verifier_nuances_municipales`)
   interdit aujourd'hui qu'une année municipale soit partagée avec pres/legi. L'ajout de
   `type_scrutin` à la clé est un changement de schéma, à traiter plus tard (décision
   séparée).
3. **ECO 2022** : le code englobe EELV dans le texte, mais les candidats EELV de 2022
   étaient pour la plupart nuancés `NUP`. Les `ECO` restants sont donc peut-être surtout
   des écologistes hors EELV. Le maintien en GAU est à confirmer au vu de la composition
   réelle (libellés des candidats `ECO` 2022 en HdF).
4. **UDI** : DTE en 2024 (grille 2023), mais CENT en 2017, 2022 et dans les municipales
   (grilles 2020 et 2026). Cette alternance vient des grilles officielles elle-mêmes. Le
   module Législatif, qui classe les groupes UDI en CENT, relève du lot 4.
5. ~~**Libellés 2008/2014 établis par des sources secondaires**~~ — **résolu le
   2026-09-25** : les libellés officiels MN2014 confirment LCOM (PCF), LUD (Union de la
   Droite) et LUDI (UDI). Seules les définitions longues (« conduite par un candidat
   UMP… ») restent de source secondaire : les archives ne publient que les libellés courts.

## Alternatives considérées

| Alternative | Raison d'écarter |
|-------------|------------------|
| Conserver les classements D3.2 et D1.2 | Contraires aux grilles officielles pour 2020 et 2026 : violation directe de la règle de l'ADR-0005 |
| Appliquer la grille 2026 à tous les scrutins | Anachronique (LFI → EXG avant 2026), proscrit par la décision n° 3 de l'ADR-0005 |
| Toujours la grille postérieure la plus proche (2026 pour UDI 2024) | Classerait un scrutin selon un texte qui n'existait pas encore alors qu'un texte antérieur existe |
| Appliquer la grille sans condition de même famille | Classerait ECO 2017/2022 (qui englobe EELV) comme les « autres écologistes » de 2020, et CPNT 2002/2007 (autonome) comme un associé de LR |

## Conséquences

**Effets visibles en UI** (après relance ETL) :
- Municipales : les listes PCF passent d'Extrême gauche à Gauche (2008-2026) ; les listes
  UDI passent de Divers à Centre ; les listes d'union de la droite passent de Centre à Droite ;
  les « autres écologistes » passent de Gauche à Divers (2020, 2026).
- Législatives : les « autres écologistes » passent de Gauche à Divers (2002, 2007, 2012,
  2024) ; l'UDI passe à Droite en 2024 ; le PRV passe à Centre en 2012.
- Présidentielle 2002 : Lepage passe de Centre à Divers.

**Tests** : `tests/test_elections_nuances_adr0010.py` (hermétique, en mémoire) vérifie
les grilles 2020 et 2026, chaque reclassement et sa trace dans `source_bloc`, le maintien
(addendum : les référentiels 2008 et 2014 identiques aux listes officielles des archives,
source citée pour chaque code) et la résolution dans `v_resultats_candidats_avec_bloc`.
`tests/test_elections_municipales.py` et `tests/test_elections_regressions_memoire.py`
sont alignés sur 80 entrées municipales.

**Relance nécessaire** (Mac, base réelle) :
1. `uv run python scripts/init_elections_schema.py` (référentiels complets) ;
2. `uv run python scripts/load_elections_municipales.py` (ou seulement
   `populate_nuances_municipales`) ;
3. `uv run python scripts/migrations/0007_add_municipales_views.py` ;
4. contrôle de présence des codes ajoutés :
   `SELECT e.annee, rc.nuance, COUNT(*) FROM resultats_candidats rc JOIN elections e USING (id_election) WHERE e.type_scrutin = 'muni' AND rc.nuance IN ('LREG','LGJ','LMDM','LDLF','LUD','LREN','LDSV','LREC') GROUP BY ALL ORDER BY ALL;`
5. contrôle du lot 2 (addendum 2026-09-25) :
   `SELECT id_election, nuance, bloc, COUNT(DISTINCT code_commune) AS communes, SUM(voix) AS voix FROM v_resultats_candidats_avec_bloc WHERE id_election LIKE '2008_muni_%' AND nuance IN ('LCMD','LMAJ','LGC','LMC','LREG','LEXD') GROUP BY ALL ORDER BY ALL;`
   attendu au 1er tour : LMAJ → DTE (43 communes, 114 281 voix), LCMD → CENT (6 ; 13 610),
   LGC → DIV (1 ; 660), LMC → CENT (1 ; 2 737).

**Réversibilité** : chaque classement est une ligne de `schema_elections.py` ; l'ancien
bloc est conservé dans `source_bloc` (`avant : …`).
