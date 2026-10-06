# Brainstorm sources — compléter l'existant et ouvrir de nouvelles fonctionnalités

**Date** : 2026-10-06 · **Auteur** : agent « chercheur de données » (Mac, réseau ouvert) · **Destinataire** : Mathias, via le directeur de projet
**Nature** : recherche et recommandations. Aucun fichier du projet modifié, rien chargé en base. Échantillons lus dans `/Volumes/le gros stockage/outils/tmp/brainstorm` (supprimés après lecture).
**Prolonge** `reports/catalogue-sources-2026-09-24.md` (cité « catalogue »), qui n'avait pu ouvrir aucune page (proxy cloud). Ici, la plupart des sources ont été **ouvertes aujourd'hui** (API data.gouv, en-têtes de fichiers lus).

## Résumé exécutif

1. Le gisement le plus rentable est **déjà téléchargé** : le Parquet des élections agrégées contient 56 scrutins nationaux (européennes 1999-2024, régionales 2004-2021, cantonales/départementales 2001-2021), dont le projet ne charge que 30, et seulement en Hauts-de-France.
2. **Alerte** : le « jeu Etalab » des circonscriptions retenu en lot F **est le jeu jerome-desboeufs déjà utilisé** (même auteur, même méthode). Le remplacement prévu est sans objet ; deux autres pistes sont décrites (§6).
3. **Alerte** : `ODSEN_GENERAL.csv` (Sénat, utilisé par l'ETL) renvoie aujourd'hui une page HTML au lieu du CSV. Le dump `export_sens.zip` fonctionne.
4. **CNCCFP** : 23 jeux sur 26 ont une licence « non spécifiée » sur data.gouv ; seuls les comptes des partis sont sous Licence Ouverte. Réutilisation possible au titre du droit commun (CRPA), à acter par Mathias.
5. Votes nominatifs : AN (`Scrutins.json`, 8 535 scrutins pour la 17e législature, vérifié) et Sénat (tables `scr`, `votsen` du dump Dosleg, vérifié).
6. INSEE Mélodi publie **Filosofi 2023 à la commune** (`DS_FILOSOFI_CC`) : source officielle directe, qui pourrait remplacer le fichier republié par un particulier.
7. SSMSI : 46 % des lignes communales non diffusées (49 % en Hauts-de-France), mesuré aujourd'hui.
8. Les fichiers de candidatures et le RNE contiennent la **date de naissance** : à exclure au chargement (minimisation, ADR-0013).
9. Aucune donnée ouverte de résultats d'**élections partielles** depuis 2016 sur data.gouv (vérifié).
10. Top 10 et questions fermées : §8 et §9.

---

## 1. Méthode et légende

- **Licence** : **V** = lue aujourd'hui dans les métadonnées officielles (champ `license` de l'API data.gouv, métadonnées OpenDataSoft, ou page licence du producteur) ; **R** = connue par recherche ou documentation du projet, non relue aujourd'hui ; **D** = déduite.
- **Statut** : **vérifié** = fichier ou API ouvert, en-têtes lus ; **déclaré** = page ou métadonnées seulement.
- **Effort** : **S** < 1 jour ; **M** 1 à 3 jours ; **L** > 3 jours (ETL + tests + UI).
- Abréviations licences data.gouv : `lov2` = Licence Ouverte 2.0 ; `fr-lo` = Licence Ouverte 1.0 ; `notspecified` = non spécifiée.

## 2. Tableau principal

| # | Source (producteur) | Licence | Format / volume | Granularité / période | MAJ | Fonctionnalité permise | Risques principaux | Effort | Statut |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Élections agrégées — scrutins non chargés (Intérieur / data.gouv) | lov2 **V** | Parquet 71 + 161 Mo (déjà connus) | BV ; euro 1999-2024, regi 2004-2021, cant 2001-2011, dpmt 2015-2021 | ponctuelle (maj 2026-07-07) | Élections nationales hors HdF ; européennes, régionales, départementales | Classement des nuances de ces scrutins = décision ADR-0010 ; euro 2019 sans nuance | M | vérifié |
| 2 | Votes nominatifs AN (`Scrutins.json`, Assemblée nationale) | Licence Ouverte **R** (V le 2026-10-04 ; page licence en erreur 503 aujourd'hui) | JSON zippé : 26,6 Mo (L17), 10 Mo (L16), 9 Mo (L15) | Député × scrutin ; 15e-17e législatures | quotidienne | Votes par député, comparaison avec le groupe, recherche par texte | Indicateurs de « loyauté » = choix méthodologique ; corrections de vote (`miseAuPoint`) à afficher | M | vérifié |
| 3 | CNCCFP — comptes de campagne (26 jeux) | `notspecified` **V** (sauf régionales 2021 lov2) | CSV ~1-1,5 Mo par scrutin | Candidat × circonscription ; legi 2017-2024, muni 2020, euro 2014-2024, dpmt/regi 2015-2021, séna. 2014-2023 | par scrutin | Dépenses, dons, apport personnel, décision de la Commission, coût par voix | Licence non spécifiée ; encodage mixte ; nuance en libellé libre ; codes décision sans légende dans le fichier | M | vérifié (législatives 2024) |
| 4 | CNCCFP — comptes des partis | fr-lo **V** | CSV ~0,3 Mo par exercice (≥ 2022-2024 vus) + avis JO | Parti ; annuel | annuelle (maj 2026-10-01) | Ressources des partis (dons, aide publique) | Micro-partis nombreux ; périmètres variables | S | déclaré |
| 5 | IRCOM (DGFiP) | fr-lo **V** | ZIP 18 Mo / an (XLS + XLSX communes complet) | Commune × tranche de revenu ; revenus 2021-2024 (+ série départementale 1984-2020) | annuelle (maj 2026-05-26) | Série de revenus continue (relais Filosofi), part de foyers imposés | Secret fiscal : « n.c. » ; petites communes en ligne « Total » seule ; code département sur 3 caractères (`010`) | M | vérifié |
| 6 | INSEE Mélodi — `DS_FILOSOFI_CC`, `DS_ELECTORAL`, `DS_ETAT_CIVIL_NAIS/DECES_COMMUNES`, `DS_BPE`, `DS_RP_DIPLOMES_PRINC` | Licence Ouverte **R** (métadonnées Mélodi : « Public ») | API JSON (déjà utilisée par le projet) | Commune à France ; Filosofi 2023, REU 2019-2026, naissances 2008-2025, BPE 2025, diplômes 2012-2023 | annuelle | Revenus officiels 2023 ; inscrits par sexe/âge ; dynamique démographique ; équipements ; diplômes | Secret statistique Filosofi ; rupture Filosofi 2021→2023 | S à M | déclaré (métadonnées lues) |
| 7 | Candidatures officielles (Intérieur) | lov2 **V** (legi 2007, 2012, 2022 T1, 2024 ; muni 2026 ; séna. 2026) ; `notspecified` legi 2002 et 2022 T2 ; fr-lo 2014-2017 | CSV : legi 2024 0,6 Mo ; muni 2026 145 Mo | Candidat ; 2002-2026 selon scrutin | par scrutin | Parité (sexe), professions, sortants, têtes de liste | **Date de naissance** présente : à exclure ; nationalité (muni) | S à M | vérifié |
| 8 | SSMSI — délinquance enregistrée, base communale (Intérieur) | lov2 **V** | Parquet 16 Mo, 5,2 M lignes | Commune (COG 2026) × 15 indicateurs ; 2016-2025 | annuelle (maj 2026-07-09) | Carte et évolution de la délinquance enregistrée | 46 % non diffusé ; sujet politiquement sensible ; « enregistrée » ≠ « commise » | M | vérifié |
| 9 | RNE — Répertoire national des élus (Intérieur) | lov2 **V** | 12 CSV (CM 65 Mo, maires 4 Mo…) | Élu × mandat en cours | trimestrielle (maj 2026-08-11) | Profil des élus locaux : sexe, catégorie socio-professionnelle, ancienneté | Pas de nuance politique ; instantané ; date de naissance à exclure | S | vérifié |
| 10 | Sénat — Dosleg (votes `scr` / `votsen`) et Ameli (amendements) | Licence data.sénat (reprend la Licence Ouverte) **V** | Dump PostgreSQL : Dosleg 16 Mo zippé (126 Mo SQL), Ameli 154 Mo | Sénateur × scrutin ; textes depuis 1977 | quotidienne | Votes nominatifs du Sénat ; amendements | Format PostgreSQL à convertir ; schéma peu documenté | L | vérifié (tables listées) |
| 11 | OFGL — comptes des communes | Licence Ouverte 2.0 **V** | API OpenDataSoft, 21,9 M lignes | Commune × budget × agrégat ; 2018-2025 | annuelle (maj 2026-07-29) | Fiche commune : dépenses, dette, investissement | Budgets annexes ; agrégats à choisir | M | vérifié (1 ligne lue) |
| 12 | DEPP — IPS écoles (2022→) et collèges (2023→) | lov2 / Licence Ouverte 2.0 **V** | API OpenDataSoft (collèges 21 061 lignes) | Établissement → commune | annuelle | Indice social scolaire par commune ou circonscription | Deux séries collèges (rupture 2023) ; public/privé | S | vérifié |
| 13 | Conseil constitutionnel — CONSTIT (DILA) | fr-lo **V** | XML tar.gz (dernier : 2026-10-05) | Décision ; contentieux électoral depuis 1958 | trimestrielle | Élections annulées, inéligibilités dans les fiches élus | Circonscription citée en texte libre : extraction | M | déclaré (répertoire listé) |
| 14 | Contours des bureaux de vote (data.gouv / Etalab, d'après REU INSEE) + table BV REU (INSEE) | lov2 **V** | GeoJSON 676 Mo, PMTiles 282 Mo ; table BV Parquet 3,5 Mo (68 839 BV) | BV ; REU juin 2022 | ponctuelle | Cartes au bureau de vote ; reconstruction des circonscriptions | « N'a pas vocation à faire autorité » (texte du producteur) ; millésime 2022 | L | vérifié (schéma BV) |
| 15 | HATVP — déclarations publiées | Licence Ouverte Etalab **V** (page open data) | CSV liste 3,2 Mo ; XML 79,5 Mo | Déclarant ; MAJ 2026-10-02 | continue | Mention « déclaration d'intérêts publiée » dans la fiche élu | RGPD fort ; régime des déclarations de patrimoine à vérifier | M | vérifié (liste lue) |
| 16 | Sénatoriales 2026 — candidatures et résultats (Intérieur) | lov2 **V** | CSV < 0,3 Mo | Département ; élus avec nuance | ponctuelle | Composition du Sénat après 2026 avec nuance officielle | Suffrage indirect ; 2023 en `notspecified` | S | vérifié |
| 17 | FINESS (Santé) ; France services (ANCT) ; annuaire service-public | fr-lo / lov2 / fr-lo **V** | CSV 36-48 Mo ; 1,2 Mo ; dump | Établissement géolocalisé → commune | bimestrielle / trimestrielle | Accès aux services publics et de santé | Comptage ≠ accessibilité ; BPE couvre une partie | S à M | déclaré |
| 18 | HowTheyVote.eu (votes du Parlement européen) | **ODbL V** | CSV hebdomadaire, API | Eurodéputé × vote | hebdomadaire | Votes des eurodéputés français | Association ; ODbL (compatible avec la base publiée sous ODbL) | M | déclaré |

## 3. Domaine 1 — Élections

### 3.1 Scrutins déjà présents dans le Parquet agrégé (vérifié)

Lecture à distance des deux Parquet (`general_results.parquet`, `candidats_results.parquet`, maj 2026-07-07). Liste complète des `id_election` : 56 scrutins de `1999_euro_t1` à `2026_muni_t2`.

| Famille | Scrutins présents | Chargés aujourd'hui | Nuances (`nuance` non NULL) |
|---|---|---|---|
| Européennes | 1999, 2004, 2009, 2014, 2019, 2024 | non | oui sauf **2019 (100 % NULL)** |
| Régionales | 2004, 2010, 2015, 2021 (T1, T2) | non | oui (6 à 22 codes) |
| Cantonales | 2001, 2004, 2008, 2011 | non | oui |
| Départementales | 2015, 2021 | non | oui (18 à 26 codes) |
| Pres / legi / muni | 2002-2026 | oui (HdF seulement) | déjà traité |

- **Extension nationale** : les scripts filtrent `code_region = '32'` au chargement. Retirer ce filtre multiplie le volume par 10 environ (~28 M lignes au total) : faisable en DuckDB, mais le cache de l'UI et les vues doivent suivre (effort M, sans nouvelle source).
- **Sexe des candidats** (colonne `sexe`, mesuré par scrutin) : présent pour muni 2008, pres/legi 2017-2024, muni 2020, muni 2026 T2 ; **absent** pour pres/legi 2002-2012, muni 2014, muni 2026 T1 et tous les scrutins euro/regi/cant/dpmt. Les fichiers de candidatures (§3.2) comblent une partie des trous.
- Absents du Parquet : sénatoriales, partielles, référendums (non recherchés ici).

### 3.2 Candidatures officielles (Intérieur, data.gouv)

En-têtes lus :
- Législatives 2024 T1 (`legislatives-2024-candidatures-france-entiere-tour-1-2024-06-28.csv`, UTF-8, `;`) : `Code département;…;Sexe du candidat;Nom du candidat;Prénom du candidat;Date de naissance du candidat;Code nuance;Profession;Sortant;Sexe remplaçant;…`
- Municipales 2026 T1 (145 Mo, guillemets, `;`) : `…;Code nuance de liste;Nuance de liste;Tête de liste;Ordre;Sexe;…;Nationalité;Code personnalité;CC` (nuance vide pour les petites communes).
- Sénatoriales 2026 élus : `NOMPSN;PREPSN;DATNAIPSN;SEXPSN;CODPAYS;CODPRO;CODE_NUA;CODDPT;SORTANT;CODE_PERSONNALITE;TOUR_ELECTION`.

Jeux repérés (organisation Ministère de l'intérieur) : législatives 2002, 2007, 2012 (T1+T2), 2017, 2022, 2024 ; européennes 2014 ; municipales 2014 (< 1 000 hab.), 2020 (élus T1), 2026 (T1, T2) ; sénatoriales 2017, 2026. Le Ministère publie aussi pour 2026 les **sortants** et le **nombre de sièges**.

Fonctionnalités : parité par bloc et par scrutin, part des sortants réélus, profession des candidats (catégories officielles). **RGPD** : ne charger ni la date de naissance ni le nom des remplaçants sans besoin ; une tranche d'âge calculée au chargement suffit.

### 3.3 Sénatoriales

- 2026 : résultats (élus, T1, T2) et candidatures en `lov2` (V), publiés le 2026-09-27.
- 2023 : `notspecified` (V). 2020 et 2017 : data.senat.fr (pages dédiées).
- Fonction : compléter `leg_elus` (Sénat) avec la **nuance officielle** d'élection (aujourd'hui tirée du groupe).

### 3.4 Partielles

Recherche dans l'organisation « Ministère de l'intérieur » (6 jeux « partielle ») : derniers résultats publiés en **2016**. Depuis, résultats seulement sur le site d'archives (HTML) → extraction écartée (règle du catalogue). Les élus de partielles restent identifiables par les données AMO de l'AN (autorisées le 2026-10-06). Pas de source de nuances ouverte.

## 4. Domaines 2 et 3 — Élus et activité parlementaire

- **RNE** (V) : 12 fichiers, mandats en cours seulement. En-tête maires : `…;Code de la commune;…;Nom de l'élu;Prénom de l'élu;Code sexe;Date de naissance;Code de la catégorie socio-professionnelle;…;Date de début du mandat;Date de début de la fonction`. **Aucune nuance politique.** Usage : profil sociologique des élus locaux (sexe, CSP, ancienneté). Historique : non fourni par ce jeu.
- **AN `Scrutins.json`** (vérifié, L17 = 8 535 fichiers JSON, maj du jour). Chaque scrutin : `dateScrutin`, `typeVote` (SPO, solennel…), `sort`, `titre`, `ventilationVotes` par groupe puis `decompteNominatif` (`pours`, `contres`, `abstentions`, `nonVotants`, avec `acteurRef` = identifiant PA déjà présent dans AMO et `parDelegation`), `miseAuPoint` (corrections de vote). Amendements L17 : 310 Mo zippé (volumineux). Dossiers législatifs : 10,7 Mo.
- **Sénat** : dump Dosleg (16 Mo zippé, 126 Mo SQL PostgreSQL 8.4, maj 2026-10-06) avec les tables `scr` (scrutins : `scrdat`, `scrpou`, `scrcon`…), `votsen` (vote de chaque sénateur), `posvot`. Ameli (amendements) : 154 Mo zippé. Licence data.senat.fr lue : « Elle reprend les termes de la « licence ouverte » proposée par data.gouv.fr ».
- **HATVP** (V : « Ces documents sont publiés sous la licence ouverte Etalab ») : `liste.csv` (13 065 lignes) colonnes `civilite;prenom;nom;classement;type_mandat;qualite;type_document;departement;date_publication;date_depot;nom_fichier;url_dossier;open_data;statut_publication;id_origine;url_photo`. Types `di`/`dia` (intérêts) et `dsp` (patrimoine) présents pour députés et sénateurs. **Recommandation** : n'afficher qu'un lien vers la déclaration publiée et la date ; ne pas charger le contenu des déclarations de patrimoine sans analyse juridique (régime de publicité propre aux parlementaires — **R**, à vérifier dans le code électoral avant tout usage).
- **Parlement européen** : HowTheyVote.eu sous **ODbL** (V, page « About »). Compatible avec la base publiée sous ODbL, mais source associative : décision au cas par cas (lot F).

## 5. Domaine 4 — Financement politique (CNCCFP)

- Organisation `commission-nationale-des-comptes-de-campagne-et-des-financements-politiques-cnccfp` (id `534fff63a3a7292c64a77d67`) : **26 jeux**. Licences lues : comptes des partis `fr-lo` ; régionales 2021 `lov2` ; tableau législatives 2012 `fr-lo` ; **tous les autres `notspecified`**.
- Fichier législatives 2024 (`Comptes_campagne_legislatives_2024.csv`, 1,1 Mo, maj 2025-07-29) : latin-1 mais **accents partiellement en UTF-8** (« mise Ã  disposition » dans les en-têtes), `;`, CRLF, 6 lignes vides en tête, **4 010 candidats**. Colonnes : `candidat;nom;scrutin;circonscription;département;code département;nuance;dépenses totales déclarées;` + 22 postes de dépenses (déclaré puis retenu), `recettes totales déclarées;dons déclarés;apport déclaré;concours déclarés;…;apport personnel déclaré;solde déclaré;…;emprunts bancaires…;dévolution;FT;RFE;decision`.
- Codes `decision` observés : A 1 836, AR 1 020, DD 813, ARM 120, R 85, AD 57, HD 35, ARR 18, ARRR 12, AM 9, ARRRM 5. **Légende absente du fichier** : à reprendre de l'avis publié au JO ou à demander à la CNCCFP (ne pas deviner).
- `nuance` est un libellé (« Les Républicains », « Union de la gauche »…), pas un code : jointure avec `resultats_candidats` par département + circonscription + nom.
- Fonctionnalités : dépenses par bloc et par voix, part de l'apport personnel, comptes rejetés (lien avec CONSTIT pour les inéligibilités).
- Licence : en l'absence de licence, la réutilisation des informations publiques reste libre sous conditions (CRPA, art. L. 322-1 : ne pas altérer, ne pas dénaturer, citer source et date) — **R**, à acter par Mathias.

## 6. Domaine 6 — Géographie

- **Circonscriptions** : le jeu `contours-geographiques-des-circonscriptions-legislatives` (id `666b1890fcffad38a387aeba`) est publié par `jerome-desboeufs`. Sa description : « agrégation des contours des bureaux de vote composant une circonscription », à partir de sa propre « Liste des bureaux de vote associés à leur circonscription législative (jeu de données produit sous ma responsabilité, dérivé des données du Ministère de l'Intérieur) » et de la « Proposition de contours des bureaux de vote » (data.gouv). C'est **le jeu déjà en base**. Le « jeu Etalab » du catalogue du 24/09 n'existe pas en tant que tel. Alternatives :
  - (a) **INSEE « Circonscriptions législatives — Fond cartographique »** (portraits des circonscriptions, paru le 04/05/2022, page ouverte) : producteur officiel, mais la description elle-même le dit simplifié (« à défaut d'être précis », selon jerome-desboeufs) ;
  - (b) reconstruire dans le projet à partir des contours de BV data.gouv + la colonne `code_circonscription` du Parquet élections 2024 (traçable, mais méthode du projet, effort L) ;
  - (c) garder le jeu actuel avec la mention « auteur particulier » déjà affichée.
- **Bureaux de vote** : table INSEE `table-bv-reu.parquet` (68 839 BV) avec `id_brut_miom`, la même clé que le Parquet élections → jointure directe vérifiée sur le schéma. Contours data.gouv : GeoJSON 676 Mo (trop lourd tel quel, filtrer HdF), PMTiles 282 Mo (millésime REU 2022-06-01). Avertissement du producteur : « n'a pas vocation à faire autorité ».
- **Cantons** : la classe « canton » d'ADMIN-EXPRESS v4 (catalogue §2.4) reste la piste pour cartographier les départementales (non revérifiée aujourd'hui).

## 7. Domaine 5 — Territoires et société

- **IRCOM** : zip `ircom_2025_revenus_2024` = 124 fichiers (départemental, régional, national XLS) + `ircom_communes_complet_revenus_2024.xlsx` (85 609 lignes, 13 colonnes). En-têtes sur 2 lignes après 3 lignes de titre ; colonnes `Dép.` (3 caractères : `010`, `590`), `Commune` (3 caractères) → code INSEE = 2 premiers caractères du département + commune (à vérifier pour Corse et DOM) ; `Revenu fiscal de référence par tranche`, `Nombre de foyers fiscaux`, `Impôt net`, `Nombre de foyers fiscaux imposés`, salaires, retraites. Montants en milliers d'euros. Secret : valeurs `n.c.` (ex. 22 498 cellules dans une colonne). Millésimes sur data.gouv : revenus 2021 à 2024 en zip, plus série départementale 1984-2020.
- **SSMSI** (Parquet `donnee-comm-data.gouv-parquet-2025-geographie2026-produit-le2026-06-25.parquet`) : colonnes `CODGEO_2026, annee, indicateur, unite_de_compte, nombre, taux_pour_mille, est_diffuse, insee_pop, …, complement_info_nombre, complement_info_taux`. 2016-2025, 15 indicateurs, 5 238 000 lignes. `est_diffuse = 'ndiff'` : 46,3 % (France), 49 % (HdF). Les colonnes `complement_info_*` donnent une valeur de substitution pour les lignes non diffusées (méthode à lire dans la documentation PDF avant usage). Conforme à la décision lot F (commune), mais la carte doit afficher « n.d. » et non zéro (règle J3).
- **Mélodi** (catalogue lu : 147 jeux). Nouveaux jeux utiles : `DS_FILOSOFI_CC` (Filosofi 2023, niveau commune disponible, maj 2026-08-06), `DS_ELECTORAL` (« Caractéristiques du corps électoral », 2019-04-14 → 2026-03-15, commune), `DS_ETAT_CIVIL_NAIS_COMMUNES` / `DECES` (2008-2025), `DS_BPE` (2025), `DS_RP_DIPLOMES_PRINC` (2012-2023). Mélodi est déjà utilisé par le projet : faible effort d'intégration.
- **OFGL** (`ofgl-base-communes`, « Comptes des communes 2018-2025 », Licence Ouverte v2.0, 21,9 M lignes, maj 2026-07-29) : une ligne = commune × budget × agrégat. Filtrer `type_de_budget = 'Budget principal'` et une liste fermée d'agrégats.
- **DEPP IPS** : collèges 2023→ (21 061 lignes, champs `code_insee_de_la_commune`, `secteur`, `ips`) ; écoles 2022→. Licence Ouverte 2.0 (V).
- **Santé et services** : FINESS géolocalisé (fr-lo, 48 Mo, maj 2026-05-12), France services ANCT (lov2, maj du jour), annuaire service-public (fr-lo). Le BPE couvre déjà une partie de ces comptages.
- **DARES / France Travail par commune** : non retrouvé aujourd'hui par l'API data.gouv sous l'organisation DARES (recherches infructueuses) ; reste au statut du catalogue (déclaré, rupture 2025).

## 8. Les 10 sources les plus utiles (classement)

| Rang | Source | Licence | Effort | Fonctionnalité | Raison du rang |
|---|---|---|---|---|---|
| 1 | Élections agrégées : scrutins non chargés + national | lov2 V | M | Européennes, régionales, départementales ; France entière | Déjà téléchargé, même schéma, même ETL |
| 2 | AN `Scrutins.json` (L15-L17) | Licence Ouverte R | M | Votes nominatifs des députés | Comble la limite connue du module Législatif ; clé `acteurRef` déjà en base (AMO) |
| 3 | CNCCFP comptes de campagne + partis | notspecified V (partis fr-lo V) | M | Argent et résultats par circonscription | Donnée absente ; décision lot F déjà favorable |
| 4 | INSEE Mélodi (Filosofi 2023, corps électoral, état civil, BPE, diplômes) | Licence Ouverte R | S-M | Revenus 2023 officiels ; inscrits par sexe/âge ; démographie | API déjà intégrée ; remplace un intermédiaire non officiel |
| 5 | IRCOM | fr-lo V | M | Série annuelle des revenus déclarés | Décision lot F (première source Économie) |
| 6 | Candidatures officielles | lov2 V (majorité) | S-M | Parité, sortants, professions | Petits fichiers ; comble le `sexe` NULL |
| 7 | SSMSI communal | lov2 V | M | Délinquance enregistrée 2016-2025 | Décision lot F ; secret à traiter |
| 8 | RNE | lov2 V | S | Profil des élus locaux | Officiel, trimestriel, simple |
| 9 | Sénat Dosleg (votes) | Licence Sénat V | L | Votes nominatifs du Sénat | Symétrie AN/Sénat ; format PostgreSQL coûteux |
| 10 | OFGL comptes des communes | Licence Ouverte 2.0 V | M | Fiche commune : finances locales | Officiel, API stable, 2018-2025 |

Suivent : DEPP IPS (S), CONSTIT (M), contours BV + table REU (L), sénatoriales 2026 (S), HATVP (M, RGPD).

## 9. Sources à écarter (ajouts au catalogue §3)

| Source | Raison |
|---|---|
| « Contours Etalab » des circonscriptions comme source distincte | N'existe pas : c'est le jeu jerome-desboeufs déjà en base |
| Contours de circonscriptions « Ressourcerie datalocale » (2020, `notspecified`) et Mapotempo (2017, ODbL) | Anciens, licence absente ou ODbL, producteur non officiel |
| Jeu « Scrutins publics AN, Sénat, PE agrégés et thématisés » (`frederic-magnin`, lov2) | Particulier, thématisation = choix éditorial ; préférer les sources AN et Sénat |
| « Proposition de contours des BV selon la méthode de l'INSEE » (`cedric-rossi`) | Particulier, doublon du jeu data.gouv |
| Résultats des partielles depuis 2016 (site d'archives HTML) | Extraction de pages web ; pas de jeu ouvert |
| Contenu des déclarations de patrimoine HATVP | Risque juridique et RGPD non instruit |
| Temps de parole Arcom (lov2, legi et euro 2024) | Licence correcte, mais hors périmètre territorial ; à garder en réserve |

## 10. Alertes

| Type | Alerte | Action proposée |
|---|---|---|
| Bug potentiel ETL | `https://data.senat.fr/data/senateurs/ODSEN_GENERAL.csv` (et `.json`, `ODSEN_HISTOGROUPES.csv`) renvoie une page HTML « data_export_configurator » de 4 932 octets, en `Content-Type: text/csv`, le 2026-10-06 | Vérifier que l'ETL refuse un fichier non CSV ; `export_sens.zip` répond (dump SQL) |
| Décision lot F | Remplacement des circonscriptions « par le jeu Etalab » sans objet | Question 2 |
| Licence | CNCCFP `notspecified` | Question 1 |
| RGPD | Date de naissance dans candidatures, RNE, sénatoriales | Exclure à l'import (déjà la règle ADR-0013) |
| Documentation | `docs/data-sources.md` : sénateurs via `ODSEN_GENERAL.csv` ; page licence AN en 503 aujourd'hui | Revérifier plus tard |
| Encodage | CNCCFP : latin-1 + fragments UTF-8 | Lecture en octets puis correction ciblée |

## 11. Questions fermées pour Mathias

1. CNCCFP : accepter la réutilisation des jeux sans licence déclarée, au titre du droit commun de réutilisation (CRPA), avec mention source + date ? (oui / non)
2. Circonscriptions : puisque le « jeu Etalab » est le jeu actuel, choisir (a) fond INSEE 2022 officiel mais simplifié, (b) reconstruction projet depuis les contours de BV, ou (c) statu quo avec mention de l'auteur ?
3. Élargir le chargement électoral à la **France entière** (même source, volume × 10) ? (oui / non)
4. Charger européennes, régionales et départementales, sachant que le classement de leurs nuances en blocs devra suivre l'ADR-0010 (nouvelle validation des correspondances) ? (oui / non)
5. Remplacer le fichier Filosofi republié par un particulier par `DS_FILOSOFI_CC` de Mélodi (officiel, 2023) ? (oui / non)
6. Votes nominatifs : AN seulement d'abord (effort M), ou AN + Sénat ensemble (effort L) ?
7. HATVP : se limiter à un lien vers la déclaration publiée et sa date (sans contenu) ? (oui / non)

## 12. Sources consultées (2026-10-06)

- API data.gouv : `https://www.data.gouv.fr/api/1/datasets/{slug}/` pour `donnees-des-elections-agregees` (6481e741d4cf002ec0efec9d), `repertoire-national-des-elus-1` (5c34c4d1634f4173183a64f1), `proposition-de-contours-des-bureaux-de-vote` (649db7717013c57353de997a), `bureaux-de-vote-et-adresses-de-leurs-electeurs` (649998d50f6f27459dc6cf5b), `contours-geographiques-des-circonscriptions-legislatives` (666b1890fcffad38a387aeba), `elections-legislatives-generales-des-30-juin-et-7-juillet-2024` (6888e3794b617d420f807630), `comptes-des-partis-et-groupements-politiques` (53699158a3a729239d203c2f), `limpot-sur-le-revenu-par-collectivite-territoriale-ircom` (536998cba3a729239d20505e), SSMSI (621df2954fa5a3b5a023e23c), IPS écoles (64265b6135b0c18d57538672), CONSTIT (53ca2ec3a3a7294a1ddd784d), candidatures legi 2024 (6673035f5d85cb3beb43769d), muni 2026 (69a24d41280ad1aa5193e487), sénatoriales 2026 (6ab9abea8ebfc5bc472f3924, 6aa4644c63519c97bb2e366a), sénatoriales 2023 (651559bbf0ed2c8d9e50db43), FINESS (53699569a3a729239d2046eb), France services (62503e25bc0f6370f4a651ce), REI (6657c57abbefc8869c7c6364).
- Parquet élections : `https://data-pipeline-open.s3.sbg.io.cloud.ovh.net/elections/general_results.parquet` et `candidats_results.parquet` (lecture à distance DuckDB).
- AN : `https://data.assemblee-nationale.fr/static/openData/repository/{15,16,17}/loi/scrutins/…`, `…/17/loi/amendements_div_legis/Amendements.json.zip`, `…/17/loi/dossiers_legislatifs/Dossiers_Legislatifs.json.zip`.
- Sénat : `https://data.senat.fr/licence/`, `/dosleg/`, `/ameli/`, `/les-senateurs/`, `/data/dosleg/dosleg.zip`, `/data/ameli/ameli.zip`.
- HATVP : `https://www.hatvp.fr/open-data/`, `https://www.hatvp.fr/livraison/opendata/liste.csv`, `https://www.hatvp.fr/livraison/merge/declarations.xml`.
- INSEE : `https://api.insee.fr/melodi/catalog/ids` et `/catalog/{id}` ; `https://www.insee.fr/fr/statistiques/6441661?sommaire=6436478`.
- OFGL : `https://data.ofgl.fr/api/explore/v2.1/catalog/datasets/ofgl-base-communes`. DEPP : `https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/fr-en-ips-colleges-ap2023`.
- DILA : `https://echanges.dila.gouv.fr/OPENDATA/CONSTIT/`. HowTheyVote : `https://howtheyvote.eu/about`.
