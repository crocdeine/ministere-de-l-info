# 0011 — Législatif : classement des groupes par législature et modèle de mandats

Date : 2026-09-24
Statut : Accepté (décision Mathias 2026-09-24, questions Q18 à Q23 de
`reports/verification-nuances-2026-09-24.md`)
Complète : ADR-0007 (points ouverts 1, 2, 3, 5, 6 et 8). Applique : ADR-0005 (règle n° 3)
et la doctrine de l'ADR-0010.

## Contexte

L'ADR-0007 a documenté a posteriori le module Législatif et relevé plusieurs défauts :

1. **Classement sans dimension temporelle** : un dictionnaire `_GROUPE_BLOCS` par loader,
   indépendant de la législature. `FI` (XVe), `LFI-NUPES` (XVIe) et `LFI-NFP` (XVIIe)
   étaient classés `EXG`, ce qui applique rétroactivement la grille de 2026 (INTP2602966C),
   contrairement à l'ADR-0005 (FI 2017, NUP 2022, FI 2024 = GAU dans le module Élections).
2. **Repli `DIV` silencieux** : tout groupe absent du dictionnaire était classé `DIV`
   (Sénat : GEST, RDPI, RDSE ; AN : RRDP, EDS…), sans avertissement (audit I8, M13).
3. **Modèle « un député = une ligne »** (audit I7) : clé `(id, chambre)`, rattachement à
   la dernière législature (`legislatureLast`). Le graphique « Composition de l'AN par
   législature » ne comptait, pour la XIIe, que les députés dont la carrière s'est
   arrêtée en 2007.
4. **Dates de fin inventées** : Sénat, `date_fin_mandat` = date du chargement ; AN,
   `date_fin_mandat` = `dateMaj` (date de mise à jour Datan).
5. **Périmètre Sénat** : ODSEN_GENERAL contient des sénateurs antérieurs à 2002 (jusqu'aux
   départements algériens) alors que le projet couvre 2002-présent.
6. **Nom de vue trompeur** : `v_elus_hdf_actuels` renvoie tous les élus actifs de France.

Le rechargement du Sénat après les sénatoriales du 27 septembre 2026 impose de corriger
ces points avant de recharger.

## Décision

### D1 — Référentiel `(chambre, groupe, législature) → bloc`

Nouvelle table `leg_groupes_blocs (chambre, groupe, legislature_debut, legislature_fin,
bloc, libelle, source_bloc)`, alimentée par `populate_groupes_blocs()` depuis le
référentiel Python `src/ministere_de_l_info/etl/legislatif_groupes.py` (source unique,
validée : blocs de l'ADR-0005, `source_bloc` obligatoire, pas de recouvrement).

- **AN** : intervalle fermé de numéros de législature, **toujours borné** (≤ 17). Un
  groupe observé dans une législature non couverte (XVIIIe après une dissolution, sigle
  réutilisé) n'est pas classé : la revue du classement est forcée.
- **Sénat** : bornes NULL (toutes périodes). Le Sénat n'a pas de législature et
  ODSEN_GENERAL ne date pas les appartenances (voir Limites).

Règle de classement : bloc de la nuance du parti dominant du groupe, selon la doctrine
de l'ADR-0010 : (1) grille officielle couvrant le scrutin ; (2) sinon grille la plus
proche dans le temps, de préférence antérieure, si le code désigne la même famille
politique ; (3) sinon classement reconstruit (ADR-0005 n° 4). Grilles retenues :

| Législature | Élection | Grille retenue |
|---|---|---|
| XIIe à XIVe | 2002, 2007, 2012 | INTA1931378J (2020), étape 2 ; étape 3 pour UDF et Nouveau Centre |
| XVe | 2017 | INTA1931378J (2020), étape 2 |
| XVIe | 2022 | INTA1931378J (2020) ; HOR absent de cette grille → IOMA2322276J (2023), étape 2 |
| XVIIe | 2024 | IOMA2322276J (2023) |

Groupes composites sans parti dominant (LT, LIOT, RDSE) : `DIV`. Non-inscrits : `DIV`,
exceptions individuelles dans `leg_blocs_override` (inchangé).

### D2 — Plus de repli `DIV`

Un groupe absent du référentiel reçoit un bloc **NULL** (« non classé ») et le chargement
émet un **WARNING** récapitulatif (`groupe (lég. N) × effectif`). L'interface l'affiche
sous « Non classé » (code d'affichage `NC`), jamais en `DIV`. Un test en mémoire échoue
si un groupe des échantillons de test n'est pas classé ; un test sur base réelle
(`tests/test_legislatif.py::test_aucun_mandat_non_classe`) fait de même sur le Mac.

### D3 — Table `leg_mandats` (élu × chambre × législature × groupe)

`leg_mandats (elu_id, chambre, legislature, groupe_sigle, groupe_nom, code_departement,
num_circo, date_debut, date_fin, granularite, source)`. Pas de clé primaire : législature
NULL au Sénat, et une source complète pourra contenir plusieurs groupes par législature.
Clé logique : `(elu_id, chambre, legislature, groupe_sigle, date_debut)`.

La colonne `granularite` décrit ce que la source permet :

| Valeur | Source | Sens |
|---|---|---|
| `derniere_legislature` | Datan | 1 mandat par député : dernière législature et groupe dans celle-ci |
| `groupe_actuel_ou_dernier` | ODSEN_GENERAL | 1 ligne par sénateur, groupe actuel (actifs) ou dernier (anciens), sans date |
| `complete` | (future) dumps AN | 1 ligne par mandat et par appartenance de groupe |

`leg_elus` reste la table d'identité (une ligne par élu et chambre) ;
`leg_elus.bloc_politique` devient un instantané calculé au chargement ; le bloc de
référence est celui des vues.

### D4 — Vues

| Vue | Rôle |
|---|---|
| `v_elus_actuels` | Élus actifs (France entière), `bloc_groupe`, `source_bloc`, `bloc_final = COALESCE(bloc_force, bloc_groupe)` |
| `v_elus_hdf_actuels` | **Alias de compatibilité** (`SELECT * FROM v_elus_actuels`), déprécié |
| `v_mandats_legislatif` | Mandats + bloc du groupe **pour la législature du mandat** + override |
| `v_composition_legislature` | Effectifs distincts par chambre × législature × granularité × bloc |
| `v_activite_par_bloc` | Recalculée sur `v_elus_actuels` |

L'UI préfère la granularité `complete` quand elle existe, sinon `derniere_legislature`,
et affiche alors « Députés par dernière législature siégée » avec un avertissement.

### D5 — Dates et périmètre du Sénat

- `date_debut_mandat` et `date_fin_mandat` : NULL quand la source ne les fournit pas
  (Sénat : jamais ; AN : fin inconnue, `dateMaj` n'est pas une fin de mandat).
- Sénat : sont écartés les anciens sénateurs **certainement** antérieurs au renouvellement
  du 29 septembre 2002 : circonscription disparue (code `XX` : Seine, Seine-et-Oise,
  départements algériens, anciens territoires, tous antérieurs à 1968) ou décès avant cette
  date (colonne « Date de décès », si présente). Option de chargement
  `--inclure-senateurs-anterieurs-2002` pour les conserver. Les autres anciens sénateurs
  sont conservés faute de date de fin de mandat (voir Limites).

### D6 — Table de correspondance retenue

AN (sigles Datan `groupeAbrev`) :

| Groupe | Législatures | Bloc | Fondement (résumé ; texte complet dans `source_bloc`) |
|---|---|---|---|
| SOC, SOC-A | 12-17 | GAU | PS = SOC → GAU (2020, 2023, 2026) |
| SRC, S.R.C. | 13-14 | GAU | PS dominant, grille 2020 (étape 2) |
| SER | 14 | GAU | PS dominant, grille 2020 (étape 2) |
| NG | 15 | GAU | PS dominant, grille 2020 |
| CR | 12 | GAU | PCF = COM → GAU, grille 2020 (étape 2) |
| GDR | 13-17 | GAU | PCF = COM → GAU |
| GDR-NUPES | 16 | GAU | PCF = COM → GAU (2020) |
| ECOLO | 14-16 | GAU | EELV = VEC → GAU |
| ECOS | 17 | GAU | VEC → GAU (2023) |
| **RRDP** | 14 | **GAU** | PRG = RDG → GAU (2020, 2023, 2026) — Q20 |
| **FI** | 15 | **GAU** | FI → GAU (2020) ; ADR-0005 — Q18 |
| **LFI-NUPES** | 16 | **GAU** | FI → GAU (2020, 2023) — Q18 |
| **LFI-NFP** | 17 | **GAU** | FI → GAU (2023, grille de l'élection de 2024) — Q19 ; la grille 2026 (INTP2602966C) classerait LFI en EXG pour les scrutins postérieurs au 2 février 2026 |
| NI | 12-17 | DIV | Non-inscrits (overrides possibles) |
| LT | 15 | DIV | Composite |
| LIOT | 16-17 | DIV | Composite |
| UDF | 12 | CENT | Reconstruction (étape 3), cohérent législatives 2002 |
| NC | 13-14 | CENT | Reconstruction (étape 3), cohérent législatives 2012 |
| UDI | 14 | CENT | UDI → CENT (2020, étape 2) |
| LC, UDI-AGIR, UDI_I, AGIR-E | 15 | CENT | UDI et AGR → CENT (2020) |
| LAREM, MODEM | 15 | CENT | REM, MDM → CENT (2020) |
| DEM | 15-17 | CENT | MDM → CENT (2020, 2023) |
| RE | 16 | CENT | REM/REN → CENT |
| HOR | 16-17 | CENT | HOR → Centre (2023, 2026) |
| EPR | 17 | CENT | REN → Centre (2023) |
| UMP | 12-14 | DTE | UMP → LR = DTE (2020, étape 2) |
| R-UMP | 14 | DTE | Scission temporaire de l'UMP |
| LES-REP | 14 | DTE | LR → DTE |
| LR | 14-16 | DTE | LR → DTE |
| DR | 17 | DTE | LR → DTE (2023) |
| RN | 16-17 | EXD | RN → EXD |
| UDR, UDDPLR | 17 | EXD | UXD → EXD (2023) ; UDR = EXD (2026, CE n° 512694) |

Sénat (colonne « Groupe politique » d'ODSEN_GENERAL) :

| Groupe | Bloc | Fondement |
|---|---|---|
| CRCE-K, CRCE, CRC | GAU | PCF dominant = COM → GAU |
| SER, SOCR, SOC | GAU | PS dominant = SOC → GAU |
| **GEST** | **GAU** | VEC → GAU (2020, 2023) — Q21 |
| ECOLO | GAU | VEC → GAU |
| **RDPI** | **CENT** | REM → CENT (2020), REN → Centre (2023) — Q21 |
| LaREM | CENT | REM → CENT (2020) |
| UC | CENT | UDI/centristes → CENT (2020, 2026) — **point ouvert** ci-dessous |
| UC-UDF | CENT | Reconstruction, cohérent AN (UDF = CENT) |
| **Les Indépendants** | **CENT** | Application de la doctrine (Q22) : groupe rattaché à Horizons (HOR → Centre, 2023 et 2026) et à Agir (AGR → CENT, 2020) ; les deux grilles applicables aux sénateurs en fonction (élus 2020 et 2023) concordent |
| RDSE | DIV | Composite (radicaux de gauche et valoisiens), sans parti dominant |
| Les Républicains, UMP | DTE | LR → DTE |
| NI | DIV | Non-inscrits ; 2 overrides EXD (sénateurs RN) |

Changements de bloc par rapport à la Phase F : FI, LFI-NUPES, LFI-NFP (EXG → GAU) ;
RRDP (DIV → GAU) ; Les Indépendants (DTE → CENT) ; GEST (DIV implicite → GAU) ;
RDPI (DIV implicite → CENT) ; groupes historiques du Sénat (DIV implicite → bloc explicite).

## Alternatives considérées

| Alternative | Raison d'écarter |
|---|---|
| **Dictionnaire par sigle seul** (les sigles LFI changent à chaque législature) | Suffit pour LFI mais pas pour un sigle réutilisé (SOC, LR, NI, UDI) ni pour une future XVIIIe : le classement s'appliquerait sans revue |
| **LFI-NFP en EXG** (grille en vigueur depuis le 2 février 2026) | Application rétroactive d'une grille postérieure à l'élection, proscrite par l'ADR-0005 n° 3 ; incohérent avec FI 2024 = GAU dans le module Élections |
| **Conserver le repli DIV avec un WARNING** | Mélange « Divers » (bloc officiel) et « non classé » ; le module Élections traite déjà les nuances sans mapping comme non classées |
| **Classement dans les loaders, stocké dans `leg_elus`** | Un changement de classement exigerait un rechargement ; la jointure dans les vues le rend effectif dès le rechargement du référentiel |
| **Charger dès maintenant les dumps AN** | Nouvelle source et nouveau parser (JSON/XML) : hors du périmètre de cette décision, à valider séparément |

## Conséquences

**Positives**
- Classement cohérent avec le module Élections pour les XVe à XVIIe législatures.
- Plus aucun classement silencieux : tout groupe nouveau (renouvellement sénatorial,
  XVIIIe législature, nouveau sigle) est signalé et apparaît « Non classé ».
- Le modèle accepte une source complète sans changement de schéma.

**Négatives / limites**
- **Datan ne fournit que la dernière législature.** Le CSV (27 colonnes, une ligne par
  député, clé `id`) contient `legislatureLast`, `groupeAbrev` (groupe dans cette
  législature), `datePriseFonction`, `nombreMandats`, `experienceDepute`, mais aucun
  historique des groupes ni des mandats antérieurs. Le graphique d'évolution reste donc
  « députés par dernière législature siégée », désormais titré et signalé comme tel.
- **Source officielle nécessaire (non chargée)** : open data de l'Assemblée nationale,
  jeu « Historique des députés, de leurs mandats et des organes » (AMO,
  data.assemblee-nationale.fr), qui contient les mandats `ASSEMBLEE` (législature, dates)
  et `GP` (appartenance aux groupes avec dates, organe du groupe et son sigle). Il
  alimenterait `leg_mandats` avec `granularite = 'complete'`. URL exacte et structure à
  vérifier au moment du chantier (accès réseau indisponible lors de la rédaction).
  Nouvelle source : ADR dédié et validation de Mathias.
- **Sénat sans datation** : ODSEN_GENERAL ne donne ni date de mandat ni historique des
  groupes. Les autres fichiers de data.senat.fr (mandats sénatoriaux, historique des
  appartenances aux groupes) permettraient un classement par renouvellement et un filtre
  exact 2002-présent ; noms et colonnes à vérifier, non chargés. Le filtre actuel des
  sénateurs antérieurs à 2002 est donc partiel : des anciens sénateurs vivants dont le
  mandat s'est achevé avant 2002 restent chargés ; leur dernier groupe (RPR, RI, etc.)
  apparaîtra en WARNING « non classé ».
- **Overrides par élu** : `leg_blocs_override` s'applique à tous les mandats d'un élu,
  sans dimension de législature. Sans effet aujourd'hui (un mandat par élu) ; à revoir
  avec la source complète.

**Réversibilité** : élevée. Modifier une ligne de `legislatif_groupes.py`, relancer
`scripts/load_legislatif.py` ou la migration 0008 (quelques secondes).

## Points ouverts (questions fermées pour Mathias)

1. **UC au Sénat** : la doctrine ADR-0010 appliquée aux sénateurs élus en 2023 donnerait
   `DTE` (IOMA2322276J place UDI à Droite), `CENT` pour les élus de 2020 et de 2026.
   Maintien de `CENT` pour tout le groupe jusqu'à la décision Q14 et à une source datée ?
   — oui / non
2. **EDS (XVe, Écologie Démocratie Solidarité)** : non classé à ce jour (bloc NULL si le
   sigle apparaît). Classer `CENT` (élus sous l'étiquette REM, grille 2020) ? — oui / non
   (si non : `GAU` ou maintien non classé)
3. **RDSE** : maintien `DIV` (composite) plutôt que `CENT` ? — oui / non
4. **Source AN complète** : instruire un ADR pour charger l'historique des mandats et des
   groupes de l'Assemblée nationale (AMO) ? — oui / non
5. **Source Sénat datée** : instruire le chargement des mandats et de l'historique des
   groupes de data.senat.fr (filtre 2002 exact, classement par renouvellement) ?
   — oui / non

## Mise en œuvre

- Code : `etl/legislatif_groupes.py` (référentiel), `etl/schema_legislatif.py` (tables,
  vues), `etl/loaders/legislatif_datan.py`, `etl/loaders/legislatif_senat.py`,
  `scripts/load_legislatif.py`, `scripts/migrations/0008_legislatif_groupes_par_legislature.py`,
  `viz/legislatif_queries.py`, `pages/legislatif.py`.
- Tests : `tests/test_legislatif_memoire.py` (hermétiques), `tests/test_legislatif.py`
  (base réelle).

### Requêtes de contrôle (base réelle, après chargement)

```sql
-- Aucun groupe non classé (doit renvoyer 0 ligne)
SELECT chambre, groupe_sigle, legislature, COUNT(*) FROM v_mandats_legislatif
WHERE bloc_groupe IS NULL GROUP BY ALL ORDER BY 4 DESC;
-- Composition du Sénat après renouvellement
SELECT groupe_sigle, bloc_final, COUNT(*) FROM v_elus_actuels
WHERE chambre = 'SENAT' GROUP BY ALL ORDER BY 3 DESC;
-- Effectifs actifs : 577 AN, 348 Sénat
SELECT chambre, COUNT(*) FROM v_elus_actuels GROUP BY 1;
-- LFI par législature : GAU partout
SELECT DISTINCT legislature, groupe_sigle, bloc_final FROM v_mandats_legislatif
WHERE groupe_sigle IN ('FI', 'LFI-NUPES', 'LFI-NFP') ORDER BY 1;
-- Dates de fin : 0 attendu
SELECT COUNT(*) FROM leg_elus WHERE date_fin_mandat IS NOT NULL;
```

## Addendum 2026-09-25 — complément d'exécution (périmètre Sénat, « sans groupe »)

Constat sur la base réelle (Mac, 2026-09-25) : `test_aucun_mandat_non_classe` échouait
(19 anciens groupes du Sénat sans bloc, 569 mandats ; 3 députés de la XVe législature sans
groupe dans Datan). Aucun élu actif n'était concerné. Pas de nouveau classement : le
référentiel groupe → bloc (D1, D6) est inchangé.

1. **Groupes sénatoriaux disparus avant le renouvellement de 2002** : liste
   `GROUPES_SENAT_ANTERIEURS_2002` de `etl/legislatif_groupes.py` (sigle normalisé : sans
   points, espaces ni tirets, `G.D.` = `GD`). Un **ancien** sénateur dont c'est le dernier
   groupe a quitté le Sénat au plus tard en septembre 2002 : il est hors périmètre et
   écarté au chargement (`leg_elus` et `leg_mandats`), comme les critères de D5 ; effectif
   par groupe journalisé en INFO. Aucun bloc ne leur est attribué. L'option
   `--inclure-senateurs-anterieurs-2002` les conserve (ils apparaissent alors « non
   classés »). Un sénateur **actif** n'est jamais écarté (sigle historique = anomalie
   signalée en WARNING).

   | Sigle | Groupe | Période (indicative) |
   |---|---|---|
   | UNR, UNR-UDT | Union pour la nouvelle République | 1959-1968 |
   | UDR | Union des démocrates pour la République | 1968-1977 |
   | RPR | Rassemblement pour la République | 1977-2002 |
   | RI | Républicains indépendants / Républicains et indépendants | 1962-1977, 1995-2002 |
   | UREI | Union des républicains et des indépendants | 1977-1995 |
   | IPAS, CNIP | Indépendants et paysans | débuts de la Ve République |
   | CRARS | Centre républicain d'action rurale et sociale | 1959-1971 |
   | GD (G.D.) | Gauche démocratique | jusqu'en 1989 (→ RDE) |
   | RDE (R.D.E.) | Rassemblement démocratique et européen | 1989-1995 (→ RDSE) |
   | RPCD | Républicains populaires et Centre démocratique | années 1960 |
   | UCDP (U.C.D.P.) | Union centriste des démocrates de progrès | 1968-années 1970 (→ UC) |
   | CD | Centre démocratique | années 1960 |
   | PDM | Progrès et démocratie moderne | années 1970 |
   | COM | Groupe communiste | jusqu'aux années 1990 (→ CRC) |

   **Cas limites traités explicitement** : RPR et RI ont siégé jusqu'au renouvellement du
   29 septembre 2002, puis se sont fondus dans le groupe UMP constitué en octobre 2002 ;
   les sénateurs réélus ou restés en fonction ont donc UMP (ou un groupe ultérieur) pour
   dernier groupe, et RPR/RI comme dernier groupe signifie un mandat achevé au plus tard
   en septembre 2002. Les groupes ayant existé après 2002 (UC, UC-UDF, RDSE, CRC, SOC,
   UMP) restent dans le périmètre et classés.

   **Source** : connaissance générale de l'historique des groupes du Sénat ; senat.fr et
   data.senat.fr étaient inaccessibles depuis la session (2026-09-25). Liste et périodes à
   confirmer sur senat.fr (pages « Les groupes politiques depuis 1959 »). Tout sigle absent
   de la liste reste signalé « non classé » (WARNING) et fait échouer le test : un groupe
   historique non listé se complète dans `GROUPES_SENAT_ANTERIEURS_2002`, un groupe
   postérieur à 2002 dans le référentiel de classement (décision Mathias).

2. **Élus « sans groupe »** : `groupeAbrev` (Datan) ou « Groupe politique » (Sénat) vide →
   `groupe_sigle` NULL, bloc NULL, INFO au chargement (effectif par législature). Statut
   distinct de « non classé » : pas de bloc inventé, exclu du contrôle de complétude mais
   compté (`test_mandats_sans_groupe_comptes` vérifie en outre qu'aucun élu actif n'est
   sans groupe).

3. **Tests** : `test_aucun_mandat_non_classe` porte sur les mandats du périmètre (groupe
   non NULL, hors groupes Sénat antérieurs à 2002) ; `test_senat_groupes_anterieurs_2002_exclus`
   vérifie qu'ils ne sont plus chargés ; tests hermétiques dans
   `tests/test_legislatif_memoire.py`.

Requêtes de contrôle (après `uv run python scripts/load_legislatif.py --source senat`) :

```sql
-- 0 ligne attendue (mandats du périmètre non classés)
SELECT chambre, groupe_sigle, legislature, COUNT(*) FROM v_mandats_legislatif
WHERE bloc_groupe IS NULL AND groupe_sigle IS NOT NULL GROUP BY ALL ORDER BY 4 DESC;
-- Mandats sans groupe (3 attendus, XVe législature, aucun actif)
SELECT chambre, legislature, est_actif, COUNT(*) FROM v_mandats_legislatif
WHERE groupe_sigle IS NULL GROUP BY ALL;
```
