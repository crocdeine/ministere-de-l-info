# Vérification des classements restants (jalon J2) — groupes, nuances, références

**Date** : 2026-10-04
**Agent** : chercheur-donnees (lecture seule ; seul fichier écrit : ce rapport)
**Périmètre** : `leg_elus` Sénat (4 groupes sans bloc), 3 mandats AN XV sans bloc, 23 lignes
`nuances_harmonisees` 2020/2026, référence CE 437675 dans `etl/schema_elections.py`, 2 overrides Sénat.

## Résumé exécutif

- **Sénat** : `C` (Groupe communiste), `G.D.S.R.G.` (Formation des sénateurs radicaux de gauche) et `RP` (Groupe des républicains populaires) ont disparu avant 2002, et tous leurs 34 sénateurs ont quitté le Sénat en 1995 au plus tard (fiches senat.fr, **vérifié**). Proposition : `GroupeHorsPerimetre`. Pour `Écologiste` (1 sénatrice, 2012-2014), c'est le même groupe que l'entrée `ECOLO` (GAU), dont le sigle n'existe pas dans ODSEN. Proposition : alias → GAU.
- **AN XV** : 3 suppléantes ont démissionné le jour même de leur entrée en fonction. Elles n'ont **aucun groupe** (fiches AN, **vérifié**). Il n'y a rien à classer : on peut les exclure ou les garder sans bloc, avec un motif.
- **Municipales 2020/2026** : les 23 lignes concordent avec les annexes 3 (2020 p. 10, 2026 p. 12). Aucun bloc n'est en écart, seul le libellé `source_bloc` (« (D3.2) ») est à re-sourcer.
- **CE 437675** : la référence n'est pas fautive pour DLF (le CE suspend DLF → EXD), mais elle ne fonde pas le classement DTE et ne dit rien du MPF. Les bons fondements sont INTA1931378J p. 8 (MPF ∈ DVD) et p. 10 (DVD et DLF → DTE). Il y a 6 lignes à reformuler (numéros réels : 237, 243, 298, 377, 828, 897).
- **Overrides** : Hochart (59) et Szczurek (62) ont la nuance candidat **RN**, et leur liste a la nuance **LRN**. Source : la publication officielle des résultats des sénatoriales 2023 du ministère de l'Intérieur sur data.gouv (**vérifié**). Bloc EXD (IOMA2322276J).
- **Décisions attendues** : 6 questions fermées (§ 7). Aucun fichier du dépôt ni la base n'ont été modifiés.

## 1. Sénat — 4 groupes sans bloc

Source des données : `data/raw/legislatif/senat-odsen-general.csv`. Le fichier est en latin-1 avec virgule comme séparateur, et ses 18 premières lignes commencent par `%`. **En-têtes vérifiés** : Matricule, Qualité, Nom usuel, Prénom usuel, État, Date naissance, Date de décès, Groupe politique, Type d'app au grp politique, Commission permanente, Circonscription, Fonction au Bureau du Sénat, Courrier électronique, PCS INSEE, Catégorie professionnelle, Description de la profession. **Le fichier ne contient aucune date de mandat.** Les dates ci-dessous viennent des fiches individuelles senat.fr (`https://www.senat.fr/senateur/<nom>_<prenom><matricule>.html`, rubrique « Élection »), consultées le 2026-10-04.

Constat annexe : le fichier ODSEN ne contient ni `ECOLO` ni `COM`. Les entrées `ECOLO` (`legislatif_groupes.py:402-407`) et `COM` (`GroupeHorsPerimetre`, l. 545-550) ne correspondent donc à aucune ligne. Les sigles réels sont `Écologiste` et `C`.

### 1.1 `C` — « Groupe Communiste » (30 sénateurs en base)

- **Libellé** : « Groupe Communiste ». Source : https://www.senat.fr/anciens-senateurs-5eme-republique/c.html (vérifié ; 47 anciens sénateurs y sont listés, aucune date n'est donnée).
- **Période** : groupe renommé « communiste, républicain et citoyen » (CRC) après le renouvellement de septembre **1995**. Annonce d'Hélène Luc le 28 septembre, pour accueillir Paul Loridant (MDC). Sources : Wikipédia « Groupe communiste (Sénat) » (https://fr.wikipedia.org/wiki/Groupe_communiste_(S%C3%A9nat)) et en.wikipedia CRCE. Statut **déclaré** (résumé du moteur de recherche, page non ouverte en entier).
- **Mandats** (fiches senat.fr, vérifié pour les 30). La fin la plus tardive est le **1er octobre 1995** (Bangou, Fost, Garcia, Vizet). Les autres fins tombent entre 1973 et 1992 : par exemple Viron le 1er octobre 1992, Souffrin le 1er octobre 1992, Le Pors le 23 juillet 1981, Aubry le 2 octobre 1977. Aucun de ces sénateurs n'a siégé après 1995.
- **Proposition** : `GroupeHorsPerimetre("C", "Groupe communiste", "1958-1995", …)`. Option : renommer l'entrée `COM`, inutilisée, en `C`.

### 1.2 `G.D.S.R.G.` — Formation des sénateurs radicaux de gauche (2 en base)

- **Libellé exact** (senat.fr, https://www.senat.fr/anciens-senateurs-5eme-republique/gdsrg.html, vérifié) : « Formation des Sénateurs Radicaux de Gauche rattachée administrativement au groupe de la Gauche Démocratique ».
- **Période** : Wikipédia (https://fr.wikipedia.org/wiki/Gauche_d%C3%A9mocratique_(S%C3%A9nat)) : « Entre 1977 et 1986, les élus du Mouvement des radicaux de gauche (MRG) prennent une autonomie en se regroupant au sein de la Formation des sénateurs Radicaux de gauche… ». Ce passage n'a pas de référence. Un extrait de recherche indique au contraire « until 1984 ». Statut **déclaré** ; la divergence 1984/1986 est sans effet.
- **Mandats** (vérifié) : Billères (65), du 22 septembre 1974 au 2 octobre 1983 ; Caillavet (47), du 11 juin 1967 au 2 octobre 1983.
- **Proposition** : `GroupeHorsPerimetre("GDSRG", …, "années 1970-1980", …)`.

### 1.3 `RP` — Groupe des républicains populaires (2 en base)

- **Libellé** : « Groupe des Républicains Populaires ». Source : https://www.senat.fr/anciens-senateurs-5eme-republique/rp.html (vérifié).
- **Période** : de 1959 à 1965, puis renommé RPCD (1965-1968). Source : Wikipédia « Groupe républicain populaire (chambre haute) » (https://fr.wikipedia.org/wiki/Groupe_r%C3%A9publicain_populaire_(chambre_haute)), statut **déclaré**. L'entrée RPCD existe déjà dans `GroupeHorsPerimetre`.
- **Mandats** (vérifié) : Chazalon (42), du 26 avril 1959 au 13 décembre 1962 ; Favre (74), du 10 mars 1966 au 1er octobre 1968.
- **Proposition** : `GroupeHorsPerimetre("RP", "Républicains populaires", "1959-1965", …)`.

### 1.4 `Écologiste` (1 en base) — comparaison avec `ECOLO`

- **Sénatrice** : Kalliopi Ango Ela (Français établis hors de France), matricule 12040W. Fiche senat.fr (vérifiée) : « Membre du Groupe écologiste ». Elle est devenue sénatrice le 22 juillet 2012, en remplacement d'Hélène Conway-Mouret, et son mandat a pris fin le 2 mai 2014.
- **Groupe** : groupe écologiste constitué le 11 janvier 2012 et disparu en juin 2017. Source : Wikipédia « Groupe écologiste (Sénat) » (https://fr.wikipedia.org/wiki/Groupe_%C3%A9cologiste_(S%C3%A9nat)), statut **déclaré**. C'est exactement le groupe décrit par l'entrée `ECOLO` (« Écologiste (2012-2017) » → GAU, `EELV = VEC → GAU : {_G2020} ; {_PROCHE}`).
- **Proposition** : classer comme `ECOLO` (GAU). La méthode est au choix :
  - renommer le sigle `ECOLO` en `Écologiste` ;
  - ajouter un alias.

  Ce cas est distinct de T4 (ECO/LECO = DIV) : le groupe était adossé à EELV, donc VEC.

## 2. AN législature XV — 3 mandats sans bloc

Les fiches AN (`https://www.assemblee-nationale.fr/dyn/deputes/<id>`) ont été vérifiées le 2026-10-04. Dans le fichier Datan (`datan-deputes-historique.csv`), ces trois mandats ont `groupe` et `groupeAbrev` vides, et `experienceDepute` = « 0 jours ».

| id | Élue | Circo | Début (Datan) | Fin (AN) | Motif (AN) |
|---|---|---|---|---|---|
| PA720134 | Elisabeth Marquet | 49-3 | 2020-08-01 | 1er août 2020 | « Démission » |
| PA720888 | Sarah Taillebois | 94-9 | 2020-06-24 | 24 juin 2020 | « Démission » |
| PA721032 | Carine Sinaï-Bossou | 973-1 | 2021-08-02 | 2 août 2021 | « Démission avant entrée en fonction » |

**Constat** : aucun groupe n'a existé pour ces mandats, et la doctrine ADR-0011 (bloc du groupe) ne s'applique pas. La base a aussi `date_fin_mandat` NULL, alors que l'AN donne une fin le jour même : c'est une lacune de la source Datan.

**Proposition** : ne pas inventer de bloc. Deux options :
- (a) exclure ces mandats de durée nulle de `v_mandats_legislatif` ;
- (b) les conserver avec `bloc_final` NULL et un motif explicite (« aucun groupe — mandat démissionné le jour de l'entrée en fonction »), et renseigner `date_fin` depuis l'AN.

Il n'est pas proposé de les classer NI/DIV, car ils n'ont jamais été inscrits.

## 3. Municipales 2020 et 2026 — 23 lignes à source non officielle

Les grilles ont été lues dans les PDF archivés (texte extrait avec pypdf ; rendu image impossible ici, poppler absent). Elles recoupent la lecture « vérifiée sur rendu image » de `reports/verification-nuances-2026-09-24.md` (l. 120 et 149).

- **2020, INTA1931378J annexe 3 p. 10** (listes) : EXG = LEXG ; GAU = LCOM, LFI, LSOC, LRDG, LDVG, LUG, LVEC ; **AUT** = LECO, LDIV, LREG, LGJ ; CENT = LREM, LMDM, LUDI, LUC, LDVC ; DTE = LLR, LUD, LDVD, LDLF ; EXD = LRN, LEXD.
- **2026, INTP2602966C annexe 3 p. 12** (listes) : EXG = LEXG, LFI ; GAU = LCOM, LSOC, LVEC, LUG, LDVG ; DIV = LECO, LREG, LDIV ; CENT = LREN, LMDM, LHOR, LUDI, LUC, LDVC ; DTE = LLR, LUD, LDVD, LDSV ; EXD = LUDR, LRN, LREC, LUXD, LEXD.

| Code | Année | Bloc stocké | Bloc officiel (page) | Concordance |
|---|---|---|---|---|
| LDIV | 2020 | DIV | AUT (p. 10) | conforme (AUT = DIV, ADR-0010) |
| LDVD | 2020 | DTE | DTE (p. 10) | conforme |
| LDVG | 2020 | GAU | GAU (p. 10) | conforme |
| LEXD | 2020 | EXD | EXD (p. 10) | conforme |
| LEXG | 2020 | EXG | EXG (p. 10) | conforme |
| LLR | 2020 | DTE | DTE (p. 10) | conforme |
| LRDG | 2020 | GAU | GAU (p. 10) | conforme |
| LREM | 2020 | CENT | CENT (p. 10) | conforme |
| LRN | 2020 | EXD | EXD (p. 10) | conforme |
| LSOC | 2020 | GAU | GAU (p. 10) | conforme |
| LUC | 2020 | CENT | CENT (p. 10) | conforme |
| LUG | 2020 | GAU | GAU (p. 10) | conforme |
| LVEC | 2020 | GAU | GAU (p. 10) | conforme |
| LDIV | 2026 | DIV | DIV (p. 12) | conforme |
| LDVD | 2026 | DTE | DTE (p. 12) | conforme |
| LDVG | 2026 | GAU | GAU (p. 12) | conforme |
| LEXD | 2026 | EXD | EXD (p. 12) | conforme |
| LEXG | 2026 | EXG | EXG (p. 12) | conforme |
| LHOR | 2026 | CENT | CENT (p. 12) | conforme |
| LLR | 2026 | DTE | DTE (p. 12) | conforme |
| LRN | 2026 | EXD | EXD (p. 12) | conforme |
| LSOC | 2026 | GAU | GAU (p. 12) | conforme |
| LUC | 2026 | CENT | CENT (p. 12) | conforme |

**Écarts de bloc : aucun.** Le correctif est purement documentaire : remplacer « (D3.2) » par `_SRC_2020` (`"INTA1931378J annexe 3 p. 10"`) ou `_SRC_2026` (`"INTP2602966C annexe 3 p. 12"`). Ces constantes sont définies dans `schema_elections.py:515-516`. Pour LDIV 2020, ajouter « bloc AUT = DIV ».

## 4. Référence CE 31/01/2020 n° 437675

Le dispositif de l'ordonnance (fiche `docs/sources-officielles/nuances/2020-CE_decision_437675.md`, art. 1er, 3°) suspend la circulaire du 10 décembre 2019 « en tant qu'elle […] Classe "Liste Debout la France" (DLF) dans le bloc "extrême droite" ». Il n'établit pas de classement positif et ne mentionne pas le MPF.

Les fondements positifs se trouvent dans INTA1931378J (vérifié par extraction texte) :
- **p. 8**, annexe 1 : la nuance DVD (« Divers droite ») couvre « Les centristes; Mouvement pour la France; Parti chrétien démocrate; … » ;
- **p. 8** : nuance distincte « DLF Debout la France » ;
- **p. 10**, annexe 3 : DTE = LR, DVD, DLF (et LDVD, LDLF pour les listes).

IOMA2322276J p. 6 place DLF dans la rangée qui suit « LR … Droite ». La cellule est fusionnée, donc ce point est **déduit** (rendu image à confirmer).

Les numéros de ligne cités dans la mission (778, 847) sont décalés : les occurrences réelles sont aux lignes 237, 243, 298, 377, 658 (LDVC, déjà corrigée) et 828, 897.

| Ligne | Texte actuel (fin) | Texte de remplacement proposé |
|---|---|---|
| 237 | `de Villiers – MPF (DVDR) → DTE (CE 31/01/2020 n°437675)` | `de Villiers – MPF (DVDR) → DTE (INTA1931378J p. 8 : MPF ∈ DVD ; p. 10 : DVD → DTE)` |
| 243 | `Dupont-Aignan – DLR (DVDR) → DTE (CE 31/01/2020 n°437675)` | `Dupont-Aignan – DLR (devenu DLF) → DTE (INTA1931378J p. 10 : DLF → DTE)` |
| 298 | `MPF (Villiers) souverainiste conservateur → DTE (CE 31/01/2020 n°437675)` | `MPF (Villiers) → DTE (INTA1931378J p. 8 : MPF ∈ DVD ; p. 10 : DVD → DTE)` |
| 377 | `Debout la France (Dupont-Aignan) → DTE (CE 31/01/2020 n°437675)` | `Debout la France → DTE (INTA1931378J p. 10 ; CE n° 437675 a suspendu DLF → EXD)` |
| 828 | `Nuance DVDR — CE 31/01/2020 n°437675 conforte DTE` | `Nuance DVDR — DLF → DTE : INTA1931378J p. 10 (CE n° 437675 a suspendu DLF → EXD)` |
| 897 | idem (2022) | idem 828 |

Ces chaînes ne sont pas des f-strings, car les lignes 237-377 précèdent la définition de `_SRC_2020` (l. 515). Ruff ignore E501 (`pyproject.toml:119`) et le formateur ne coupe pas les chaînes. Si une ligne dépasse 100 caractères, l'éclater en tuple multiligne, comme à la l. 298.

## 5. Overrides Sénat — nuance préfectorale

**Source** : « Elections sénatoriales 2023 - Résultats », producteur Ministère de l'Intérieur.
- Jeu de données : data.gouv dataset `651559bbf0ed2c8d9e50db43` ;
- Fichier : https://static.data.gouv.fr/resources/elections-senatoriales-2023-resultats/20230928-104908/senatoriales-2023-resultats-publication.xlsx (XLSX, 64 832 octets) ;
- Licence affichée par l'API : `notspecified` ;
- Consulté le 2026-10-04. Le fichier a été téléchargé dans le scratchpad uniquement et ouvert (**vérifié**).

| elu_id | Sénateur | Feuille « Liste des élus » | Feuille « PROP » (liste) |
|---|---|---|---|
| 21085M | Joshua Hochart (59) | ligne 75 : `CODE NUANCE` = **RN**, « élu T1 » | ligne 13 : `LRN`, « Au service des communes pour défendre le Nord », 433 voix, 1 siège |
| 21069M | Christopher Szczurek (62) | ligne 87 : `CODE NUANCE` = **RN**, « élu T1 » | ligne 15 : `LRN`, « Au service des communes pour défendre le Pas-de-Calais », 557 voix, 1 siège |

**Justification de remplacement proposée** : « Nuance RN attribuée par le ministère de l'Intérieur (liste LRN), résultats officiels des sénatoriales 2023, data.gouv 651559bbf0ed2c8d9e50db43 ; RN/LRN → Extrême droite : IOMA2322276J annexes 1-2 (p. 6-7) ; groupe NI au Sénat ».

Les numéros de ligne correspondent à la position dans le classeur ; la ligne 1 est l'en-tête.

## 6. Limites

- PDF : texte extrait sans rendu image (poppler absent). Les grilles 2020/2026 concordent avec la lecture sur image du rapport du 2026-09-24. La lecture DLF de 2023 reste déduite.
- Les dates d'existence des groupes (Wikipédia) sont **déclarées**. Les dates de mandat (senat.fr, AN) sont **vérifiées**.
- `R.I.A.S.` (4) et `MRP` (1) figurent dans ODSEN sans entrée `GroupeHorsPerimetre`. Ils sont absents de la base (filtrés par la date de décès), mais seraient à ajouter par cohérence.

## 7. Questions fermées pour Mathias

1. Ajouter `C`, `GDSRG` et `RP` à `GROUPES_SENAT_ANTERIEURS_2002` (tous les mandats se sont terminés au plus tard en 1995) ? — oui / non
2. Remplacer l'entrée inutilisée `COM` par `C` (plutôt qu'ajouter une entrée) ? — oui / non
3. Classer le sigle ODSEN `Écologiste` comme `ECOLO` (GAU) en renommant le sigle de l'entrée ? — oui / non (sinon : alias)
4. Pour les 3 mandats AN de durée nulle, choisir l'option (a) : les exclure de `v_mandats_legislatif` ? — oui / non (non = option b : bloc NULL avec motif et `date_fin` issue de l'AN)
5. Re-sourcer les 23 lignes « (D3.2) » sur `_SRC_2020` / `_SRC_2026`, sans changer aucun bloc ? — oui / non
6. Appliquer les 6 libellés de remplacement du § 4 et la justification d'override du § 5 ? — oui / non

Sources : senat.fr (pages des groupes `c.html`, `gdsrg.html`, `rp.html`, et fiches individuelles), assemblee-nationale.fr (fiches PA720134, PA720888, PA721032), data.gouv.fr (dataset 651559bbf0ed2c8d9e50db43), Wikipédia (Gauche démocratique (Sénat), Groupe écologiste (Sénat), Groupe communiste (Sénat), Groupe républicain populaire (chambre haute)), PDF archivés INTA1931378J, IOMA2322276J et INTP2602966C.
