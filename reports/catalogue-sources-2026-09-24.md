# Catalogue de référence des sources de données — au-delà de data.gouv.fr et de l'INSEE

**Date** : 2026-09-24
**Auteur** : agent « chercheur de données » (session cloud)
**Destinataire** : Mathias
**Nature** : catalogue et recommandations. Aucune donnée téléchargée, aucun code modifié, aucune décision prise.
**Documents lus avant rédaction** : `CLAUDE.md` (section « Sources de données autorisées »), `docs/data-sources.md`, `reports/rd-feuille-de-route-2026-09-24.md` (cité ci-après « rapport R&D »), `reports/ux-2026-09-24.md` (cité « rapport UX »).

---

## 0. Comment lire ce catalogue

### 0.1 Limite de vérification (à lire en premier)

Depuis ce conteneur, **aucune page source n'a pu être ouverte** :

- `curl` : `CONNECT tunnel failed, response 403` (refus de la politique du proxy) sur data.gouv.fr, cnccfp.fr, ssmsi, data.ofgl.fr, observatoire-des-territoires.gouv.fr, howtheyvote.eu, unehistoireduconflitpolitique.fr, opendata.hautsdefrance.fr, data.lillemetropole.fr, data.education.gouv.fr, conseil-constitutionnel.fr, dares.travail-emploi.gouv.fr ;
- `WebFetch` : `EGRESS_BLOCKED` sur www.data.gouv.fr, howtheyvote.eu, www.unehistoireduconflitpolitique.fr.

Conséquence : **toutes les fiches ci-dessous ont le statut « déclaré »** au sens du projet (vérifié par moteur de recherche seulement : titre, URL et extrait des résultats du 24/09/2026). Aucun en-tête de fichier n'a été lu, aucun volume n'a été mesuré. Les champs « format », « millésimes » ou « licence » marqués ⚠️ sont à confirmer lors d'une exploration classique (`reports/exploration-*.md`) sur le Mac, avant tout chargement.

### 0.2 Grille de notation

| Note | Signification |
|---|---|
| **A** | Producteur public officiel, méthodologie documentée, diffusion stable, licence ouverte (Licence Ouverte Etalab 2.0 ou équivalent) |
| **B** | Source sérieuse mais avec une réserve : producteur associatif ou académique, licence à conditions (partage à l'identique, citation), méthodologie propre au producteur, ou diffusion peu stable |
| **C** | Utilisable seulement en complément ou pour contrôle : licence restrictive ou absente, méthodologie non officielle, accès par extraction de pages web |

Colonnes des tableaux : **Prod.** = producteur et statut (Pub. = public officiel, Asso. = associatif, Acad. = académique, UE = institution européenne) ; **Gran.** = granularité géographique ; **Prof.** = profondeur temporelle ; **Mod.** = module du projet (GEO, ELEC, ECO, LEG, TR = transversal).

### 0.3 Sources déjà connues (non re-décrites ici)

- **Déjà intégrées** (voir `docs/data-sources.md`) : IGN ADMIN-EXPRESS-COG, INSEE Mélodi, élections agrégées (Intérieur), dataset OLAP Filosofi + RP, CNAF RSA, DREES APL, URSSAF, Eurostat (chômage et PIB régionaux), Datan, Sénat ODSEN_GENERAL.
- **Déjà identifiées par le rapport R&D** (§3, pistes EL6, EL7, GE1-GE3, EC1-EC5, LG2-LG7) : contours et adresses des bureaux de vote, liaison IRIS ↔ BV, populations de référence 2023, aires d'attraction des villes, QPV 2024, FRR (ex-ZRR), BPE, Sirene géolocalisé, votes nominatifs AN (`Scrutins.json.zip`, AMO30), Dosleg (Sénat), RNE, HATVP. Elles sont citées ici par leur identifiant de piste, sans nouvelle fiche.

---

## 1. Résumé exécutif : les 10 sources les plus prometteuses

| # | Source | Pourquoi | Module | Note |
|---|---|---|---|---|
| 1 | **CNCCFP — comptes de campagne** (data.gouv.fr, organisation CNCCFP) | Donnée absente du projet et très demandée : dépenses et recettes par candidat, apport personnel, remboursement. Couvre législatives 2022 et 2024, municipales 2020 (communes > 9 000 hab.), présidentielles, comptes des partis. Relie argent et résultat électoral par circonscription | ELEC, LEG | A |
| 2 | **Contours géographiques des circonscriptions législatives** (Etalab, dérivé des données du ministère de l'Intérieur) | Peut remplacer la source non officielle actuelle (jerome-desboeufs, limite connue de `docs/data-sources.md`) : construite par agrégation des contours de bureaux de vote rattachés à leur circonscription | GEO, ELEC, LEG | A- |
| 3 | **Conseil constitutionnel — base CONSTIT** (data.gouv.fr + DILA) | Tout le contentieux électoral AN, Sénat et présidentiel depuis 1993, inéligibilités depuis 1985, en XML. Permet de signaler les élections annulées et les inéligibilités dans les fiches élus. Cohérent avec le profil de Mathias (droit) | ELEC, LEG | A |
| 4 | **DGFiP — IRCOM** (impôt sur le revenu par collectivité) | Revenus déclarés, foyers fiscaux, part de foyers imposés **par commune, chaque année**. Série continue qui compense la rupture Filosofi 2021 → 2023 et le trou 2022 (rapport R&D, V2) | ECO | A |
| 5 | **OFGL — comptes des communes et groupements** (data.ofgl.fr) | Finances locales (dépenses, épargne, dette, investissement) par commune, 2012-2025. Donne un contenu à la « fiche commune » pour les élus (profil P4 du rapport UX) | ECO, TR | A |
| 6 | **DARES / France Travail — inscrits par commune** (trimestriel) | Seule mesure communale du chômage enregistré, infra-annuelle, catégories A, B, C par sexe et âge. **Attention : rupture 2025** (voir §4) | ECO | A (rupture) |
| 7 | **SSMSI — délinquance enregistrée par commune** (depuis 2016) | Thème central du débat politique ; base communale officielle. **Sujet sensible et secret statistique massif** (environ 48 % des lignes communales masquées) : décision d'opportunité à prendre | ECO (social) | A (usage délicat) |
| 8 | **DEPP — indices de position sociale (IPS)** des écoles et collèges | Mesure sociale fine (établissement géolocalisé), annuelle, officielle ; complète Filosofi là où le secret statistique masque les petites communes | ECO | A |
| 9 | **CDSP (Sciences Po) — élections législatives 1958-2012 et présidentielles 1965-2012** (data.gouv.fr) | Profondeur historique avant 2002 : par circonscription depuis 1958, par commune (> 9 000 hab.) pour 1986-1997. Fichiers contrôlés et nuances nettoyées par le CDSP | ELEC | A- |
| 10 | **HowTheyVote.eu — votes des eurodéputés** (GitHub `HowTheyVote/data`) | Seule source prête à l'emploi des votes nominaux du Parlement européen depuis 2019 (CSV hebdomadaire). Complète les européennes (piste EL1). **Licence ODbL** (partage à l'identique) : à arbitrer | LEG | B |

Deux sources méritent une mention hors classement : l'**Observatoire des territoires (ANCT)**, agrégateur officiel d'environ 700 indicateurs communaux utile comme raccourci (FRR, typologies), et le portrait **INSEE des circonscriptions législatives** (une centaine d'indicateurs par circonscription), qui répond directement à la piste LG8 sans agrégation commune → circonscription.

---

## 2. Catalogue par thème

### 2.1 Élections : résultats, candidats, financement, contentieux

| Source | Prod. | Licence | Format / accès | Gran. | Prof. / MAJ | Pièges connus | Mod. / valeur | URL (vérif. 24/09/2026, déclaré) | Note |
|---|---|---|---|---|---|---|---|---|---|
| **CNCCFP — comptes de campagne par scrutin** | Pub. (autorité administrative indépendante) | Licence Ouverte ⚠️ | CSV/XLSX sur data.gouv.fr ⚠️ ; publication simplifiée au JORF (ex. avis législatives 2024 : JORFTEXT000051935355) | Candidat → circonscription (législatives), liste → commune (municipales > 9 000 hab.) | Législatives 2022 et 2024, municipales 2020, présidentielles (depuis 2007 au contrôle) ; 4 879 comptes municipaux 2026 en cours d'examen (non publiés) | Municipales : seulement communes > 9 000 hab. ; comptes rejetés ou non déposés à distinguer ; identifiant candidat à rapprocher du Parquet élections par nom + circonscription | ELEC/LEG : coût du vote, apport personnel, candidats remboursés ou non | [Organisation CNCCFP](https://www.data.gouv.fr/organizations/commission-nationale-des-comptes-de-campagne-et-des-financements-politiques-cnccfp) · [Législatives 2022](https://www.data.gouv.fr/datasets/comptes-de-campagne-elections-legislatives-generales-des-12-et-19-juin-2022) · [Municipales 2020](https://www.data.gouv.fr/datasets/comptes-de-campagne-elections-municipales-generales-des-15-mars-et-28-juin-2020) · [Publication 2024 (CNCCFP)](https://cnccfp.fr/elections-legislatives-des-30-juin-et-7-juillet-2024-publication-simplifiee-des-comptes-de-campagne/) | **A** |
| **CNCCFP — comptes des partis et groupements politiques** | Pub. | Licence Ouverte ⚠️ | CSV ⚠️ | National (par parti) | Annuel | Périmètre consolidé variable selon les partis ; micro-partis nombreux | LEG : financement des partis (contexte, pas de dimension HdF) | [Comptes des partis](https://www.data.gouv.fr/datasets/comptes-des-partis-et-groupements-politiques) | **A** |
| **Contours géographiques des circonscriptions législatives** | Pub. (Etalab, à partir des données du ministère de l'Intérieur) | Licence Ouverte ⚠️ | SHP, GeoJSON ; deux niveaux de simplification (p20, p10) | Circonscription (+ liste des BV rattachés) | Découpage 2010 (en vigueur depuis 2012) | Contours reconstruits par agrégation de BV puis simplifiés (Mapshaper) : pas un tracé juridique ; valider par `ST_Within` comme le prévoit le gotcha 10 | GEO/ELEC/LEG : remplace la source non officielle actuelle ; la liste BV → circo sert aussi au contrôle des communes coupées | [Contours géographiques](https://www.data.gouv.fr/datasets/contours-geographiques-des-circonscriptions-legislatives) | **A-** |
| Table de correspondance communes/cantons → circonscriptions 2012 et 2017 | Pub. (Intérieur) ⚠️ | Licence Ouverte ⚠️ | CSV ⚠️ | Commune/canton | 2012, mise à jour 2017 | Communes coupées renvoyées au canton ; texte juridique de référence : ordonnance 2009-935 ratifiée en 2010 | GEO/LEG : contrôle croisé des 13 communes HdF coupées (rapport R&D, LG8) | [Table de correspondance](https://www.data.gouv.fr/datasets/circonscriptions-legislatives-table-de-correspondance-des-communes-et-des-cantons-pour-les-elections-legislatives-de-2012-et-sa-mise-a-jour-pour-les-elections-legislatives-2017) | **A** |
| **Candidatures aux législatives 2024** (listes officielles) | Pub. (Intérieur) | Licence Ouverte ⚠️ | CSV agrégé depuis XML | Candidat × circonscription | 2024 (autres scrutins : jeux analogues ⚠️) | Champs profession, sexe, date de naissance **non confirmés** dans l'extrait ; nuance = nuance attribuée par le Ministère | ELEC : profil des candidats (sexe, sortants) | [Candidatures législatives 2024](https://www.data.gouv.fr/datasets/candidatures-aux-elections-legislatives-2024) · [Liste 1er tour](https://www.data.gouv.fr/datasets/liste-des-candidats-aux-elections-legislatives-2024-1er-tour) | **A** |
| **Élections sénatoriales 2023 — résultats** | Pub. (Intérieur) | Licence Ouverte ⚠️ | CSV ⚠️ (tours majoritaires, scrutin proportionnel, élus) | Département | 2023 ; 2020 et 2026 sur le site d'archives | Suffrage indirect (grands électeurs) : pas comparable aux scrutins directs | LEG : piste LG4 (sénatoriales du 27/09/2026) | [Sénatoriales 2023](https://www.data.gouv.fr/datasets/elections-senatoriales-2023-resultats) | **A** |
| **CDSP — législatives 1958-2012** | Acad. (CDSP, Sciences Po / CNRS), fichiers 2002-2012 issus de l'Intérieur | Licence Ouverte ⚠️ | XLS/CSV + documentation | Circonscription ; commune > 9 000 hab. pour 1986, 1988 (T1), 1993, 1997 | 1958-2012 | Avant 1986, résultats agrégés par tendances ; nuances nettoyées par le CDSP (≠ nomenclature du Ministère, à confronter à l'ADR-0005) ; découpages 1958, 1986, 2010 | ELEC : profondeur historique avant 2002 (piste nouvelle) | [Législatives 1958-2012](https://www.data.gouv.fr/datasets/elections-legislatives-1958-2012) · [Présidentielles 1965-2012](https://www.data.gouv.fr/datasets/elections-presidentielles-1965-2012-1) | **A-** |
| **Cagé-Piketty — « Une histoire du conflit politique »** | Acad. (PSE, Sciences Po) | **Aucune licence formelle** repérée : « téléchargement libre, citation obligatoire » | Fichiers à télécharger (format ⚠️) | Commune (≈ 36 000) | Législatives et présidentielles 1848-2022, référendums 1793-2005, variables socio-économiques | Regroupements politiques des auteurs (gauche/droite/centre, « blocs » propres) **incompatibles** avec le classement officiel de l'ADR-0005 ; harmonisation communale propre ; hébergement hors site (CDN DigitalOcean) | ELEC : séries longues HdF à titre de contexte ou de contrôle, pas de source principale | [Page de téléchargement](https://www.unehistoireduconflitpolitique.fr/telecharger.html) · [Annexes méthodologiques](http://piketty.pse.ens.fr/files/CagePiketty2023Annexes.pdf) | **B-** |
| Site d'archives des résultats (ministère de l'Intérieur) | Pub. | — | Pages HTML | Commune, département | Scrutins depuis environ 2000 | Accès par pages web = extraction à déconseiller | Contrôle ponctuel des chiffres seulement | [archives-resultats-elections.interieur.gouv.fr](https://www.archives-resultats-elections.interieur.gouv.fr/resultats/senatoriales2023/index.php) | **C** (en tant que source de données) |
| **Conseil constitutionnel — CONSTIT** | Pub. | Licence Ouverte (DILA) | XML, archive annuelle + mise à jour au moins mensuelle ; aussi via Légifrance/PISTE | Décision (référence de circonscription dans le texte) | Contentieux AN, Sénat, présidentielle et référendum depuis 1993 ; inéligibilités (série D) depuis 1985 ; incompatibilités depuis 1958 | Texte intégral non structuré : circonscription et issue (rejet, annulation, inéligibilité) à extraire des métadonnées ou du texte | ELEC/LEG : signaler élections annulées, élus déclarés inéligibles | [CONSTIT (data.gouv)](https://www.data.gouv.fr/datasets/constit-les-decisions-du-conseil-constitutionnel) · [Données ouvertes du Conseil](https://www.conseil-constitutionnel.fr/donnees-ouvertes) | **A** |
| **Justice administrative — open data des décisions** | Pub. (Conseil d'État) | Licence Ouverte ⚠️ | XML | Juridiction | Conseil d'État depuis 30/09/2021, CAA depuis 31/03/2022, tribunaux administratifs depuis 30/06/2022 | Contentieux des **municipales** (juge : tribunal administratif) couvert seulement depuis 2022 : utile pour 2026, pas pour 2020 ; ArianeWeb = moteur de recherche, pas un export | ELEC : contentieux municipal 2026 (annulations) | [opendata.justice-administrative.fr (présentation)](https://www.conseil-etat.fr/decisions-de-justice/donnees-ouvertes-open-data) · [Fiche data.gouv](https://www.data.gouv.fr/datasets/open-data-du-conseil-detat) | **A-** |
| INSEE — Répertoire électoral unique (statistiques) | Pub. (INSEE) | Licence Ouverte | Tableaux INSEE | Commune (total inscrits) ; département (sexe, âge, nationalité) | Depuis 2019 ; 50,2 M d'inscrits au 11/02/2026 | Inscrits REU ≠ inscrits du Parquet (dates d'extraction) | ELEC : taux d'inscription, piste EL10 | [Corps électoral 2026](https://www.insee.fr/fr/statistiques/8888278) · [Bases en ligne REU](https://www.insee.fr/fr/metadonnees/source/serie/s1046/bases-donnees-ligne) | **A** |

### 2.2 Législatif et vie publique

| Source | Prod. | Licence | Format / accès | Gran. | Prof. / MAJ | Pièges connus | Mod. / valeur | URL | Note |
|---|---|---|---|---|---|---|---|---|---|
| data.assemblee-nationale.fr (votes, AMO, dossiers) | Pub. | **Licence Ouverte** (page dédiée du site) | XML, JSON, CSV | Député, scrutin | 12e-17e législatures selon jeux | Voir rapport R&D (LG2, LG3) | LEG | [Licence AN](https://data.assemblee-nationale.fr/licence-ouverte-open-licence) · [Votes](https://data.assemblee-nationale.fr/travaux-parlementaires/votes) | **A** |
| data.senat.fr (Dosleg, sénateurs, questions, comptes rendus) | Pub. | Licence propre du Sénat, **dérivée de la Licence Ouverte**, compatible CC-BY/ODC-BY | CSV, dump PostgreSQL (Dosleg) | Sénateur, scrutin (depuis 01/10/2006) | Voir rapport R&D (LG5) | Dump PostgreSQL 8.4 lourd | LEG | [Licence Sénat](https://data.senat.fr/licence/) · [Notice Dosleg](https://data.senat.fr/aide/travaux-legislatifs-base-dosleg/) | **A** |
| DILA — JORF, LEGI, DOLE (dossiers législatifs) | Pub. | Licence Ouverte | Dumps XML (echanges.dila.gouv.fr), aussi sur data.gouv.fr | Texte | Historique complet, mise à jour quotidienne | Volumineux ; DTD documentées | LEG : **alternative sans OAuth** à PISTE pour le JO et les dossiers législatifs | [JORF (data.gouv)](https://www.data.gouv.fr/datasets/jorf-les-donnees-de-l-edition-lois-et-decrets-du-journal-officiel) · [DOLE](https://www.data.gouv.fr/datasets/dole-les-dossiers-legislatifs) | **A** |
| HATVP — répertoire des représentants d'intérêts (lobbying) | Pub. (AAI) | Licence Ouverte (Etalab) | CSV (4 vues), JSON par représentant ; mise à jour chaque nuit | Organisation, déclaration d'activité | Depuis 01/07/2017 | Déclaratif ; lien activité ↔ texte de loi pas toujours précis | LEG : complète LG7 (déclarations d'élus) par le lobbying | [Open data répertoire](https://www.hatvp.fr/open-data-repertoire/) · [data.gouv](https://www.data.gouv.fr/datasets/donnees-du-repertoire-des-representants-dinterets-au-format-csv/) | **A** |
| Parlement européen — Open Data Portal | UE | Réutilisation autorisée ⚠️ (licence à lire) | API v2 (OpenAPI 3), 500 requêtes / 5 min | Eurodéputé, vote | Depuis 2023 (portail) ; « vote-results » limité aux votes par appel nominal | API jeune, schéma en évolution (notes de version) | LEG : source primaire des votes au PE | [Portail](https://data.europarl.europa.eu/en/home) · [API](https://data.europarl.europa.eu/en/developer-corner/opendata-api) | **A-** |
| **HowTheyVote.eu** | Asso. (projet bénévole, données compilées à partir des sources officielles du PE) | **ODbL** (partage à l'identique pour la base dérivée) | CSV hebdomadaire (release GitHub, dernière vue : 2026-09-19), API | Eurodéputé × vote | Depuis la 9e législature (2019) ; votes en commission non couverts | ODbL : obligation de republier sous ODbL une base dérivée diffusée ; dépendance à une équipe bénévole | LEG : votes des eurodéputés français/élus HdF | [Données GitHub](https://github.com/HowTheyVote/data) · [À propos](https://howtheyvote.eu/about) | **B** |
| Datan (déjà utilisé) | Asso. | Licence ouverte (déclarée par Datan) | CSV sur data.gouv.fr | Député | 2002-présent | Scores = méthodologie Datan (participation aux scrutins solennels, loyauté au groupe), à citer comme telle | LEG | [Méthode des statistiques](https://datan.fr/statistiques/aide) | **B+** |
| Regards Citoyens — NosDéputés / NosSénateurs | Asso. | **CC BY-NC-SA** sur les dumps SQL (clause non commerciale, partage à l'identique) | API, dumps SQL | Parlementaire | 2009/2011 → ; métriques AN vides depuis juin 2024 (déjà abandonné) | Licence incompatible avec une diffusion libre du projet ; service dégradé | LEG : écarté (déjà dans « sources abandonnées ») | [Doc open data](https://github.com/regardscitoyens/nosdeputes.fr/blob/master/doc/opendata.md) | **C** |
| INSEE — portraits des circonscriptions législatives | Pub. (INSEE) | Licence Ouverte | Fichiers de données + fiches | Circonscription (577) | 2022 (données de l'époque) ⚠️ | Millésime figé 2022 ; découpage 2010 | LEG/ECO : répond à LG8 sans agrégation commune → circo | [INSEE](https://www.insee.fr/fr/statistiques/6436478) · [data.gouv](https://www.data.gouv.fr/datasets/portraits-des-circonscriptions-legislatives-indicateurs-economiques-et-socio-demographiques) | **A** |

### 2.3 Économie, social, fiscalité, finances locales

| Source | Prod. | Licence | Format / accès | Gran. | Prof. / MAJ | Pièges connus | Mod. / valeur | URL | Note |
|---|---|---|---|---|---|---|---|---|---|
| **DGFiP — IRCOM** | Pub. (DGFiP) | Licence Ouverte ⚠️ | ZIP annuel (fichiers XLS/CSV ⚠️), ex. `ircom2023_revenus_2022` | Commune (région, département) | Annuel, plusieurs millésimes ⚠️ | Secret fiscal : petites communes regroupées ⚠️ ; revenus **déclarés** (≠ revenu disponible Filosofi) ; format change selon les années | ECO : série de revenus continue malgré la rupture Filosofi | [IRCOM](https://www.data.gouv.fr/datasets/limpot-sur-le-revenu-par-collectivite-territoriale-ircom) | **A** |
| **DGFiP — REI** (fiscalité directe locale) | Pub. (DGFiP ; rediffusé par OFGL et data.economie.gouv.fr) | Licence Ouverte | CSV/XLSX, depuis 1982 | Commune, EPCI | Annuel | Suppression de la taxe d'habitation sur les résidences principales (2021-2023) = rupture ; très nombreuses variables | ECO : taux de taxe foncière votés, pression fiscale locale | [REI (data.gouv)](https://www.data.gouv.fr/datasets/impots-locaux-fichier-de-recensement-des-elements-dimposition-a-la-fiscalite-directe-locale-rei-4) · [REI (OFGL)](https://data.ofgl.fr/explore/dataset/rei/) | **A** |
| **OFGL — comptes des communes** (et comptes consolidés, groupements, départements, régions) | Pub. (Observatoire des finances et de la gestion publique locales, à partir des balances DGFiP) | Licence Ouverte ⚠️ | OpenDataSoft : export CSV, API | Commune, EPCI, département, région | 2018-2025 en ligne, 2012-2017 en pièces jointes | Agrégats calculés par l'OFGL ; budgets annexes (comptes « consolidés » à préférer pour comparer) ; communes nouvelles | ECO/TR : dette, épargne, investissement par habitant pour la fiche commune | [Comptes des communes](https://data.ofgl.fr/explore/dataset/ofgl-base-communes/) · [Consolidés](https://data.ofgl.fr/explore/dataset/ofgl-base-communes-consolidee/) | **A** |
| **DARES / France Travail — inscrits par commune** | Pub. (DARES, service statistique ministériel) | Licence Ouverte ⚠️ | CSV (data.gouv, portail DARES OpenDataSoft) ; API « Marché du travail » | Commune (trimestriel) ; zone d'emploi (mensuel et trimestriel) | Plusieurs années ⚠️, trimestriel | **Rupture 2025** (inscription automatique des allocataires du RSA, nouvelles catégories F et G ; label de l'Autorité de la statistique publique suspendu pour 2025-2026) ; petites valeurs masquées ⚠️ | ECO : chômage enregistré communal, infra-annuel | [Données communales](https://data.gouv.fr/en/datasets/demandeurs-demploi-inscrits-a-france-travail-donnees-communales-trimestrielles-brutes) · [Avis ASP du 15/11/2024](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000050655620) | **A** (rupture) |
| **SSMSI — délinquance enregistrée** (bases communale, départementale, régionale) | Pub. (SSMSI, service statistique du ministère de l'Intérieur) | Licence Ouverte ⚠️ | CSV ⚠️ | Commune (lieu de commission) | Annuel depuis 2016 ; depuis mars 2026, indication de la force compétente (police/gendarmerie) | Diffusion seulement si plus de 5 faits sur 3 années successives : environ **47,9 % des lignes communales masquées** ; faits **enregistrés** ≠ délinquance réelle (plaintes, activité des services) ; zone police/gendarmerie | ECO/social : sujet politique majeur, mais risque d'interprétation élevé | [Bases SSMSI](https://www.data.gouv.fr/datasets/bases-statistiques-communale-departementale-et-regionale-de-la-delinquance-enregistree-par-la-police-et-la-gendarmerie-nationales) · [Méthode (Interstats)](https://www.bnsp.insee.fr/ark:/12148/bc6p09qp6vd.pdf) | **A** (usage délicat) |
| **DEPP — IPS des écoles et des collèges** | Pub. (DEPP, ministère de l'Éducation) | Licence Ouverte ⚠️ | OpenDataSoft (CSV, API) | Établissement (UAI géolocalisé → commune) | Écoles depuis 2022 ; collèges 2016-2021 puis depuis 2023 | **Deux séries collèges non raccordées** (2016-2021 / depuis 2023) ; écoles avec moins de 25 CM2 exclues ; public + privé sous contrat | ECO : indicateur social fin, utile en zone rurale | [IPS écoles](https://data.education.gouv.fr/explore/assets/fr-en-ips-ecoles-ap2022/) · [IPS collèges depuis 2023](https://data.education.gouv.fr/explore/assets/fr-en-ips-colleges-ap2023/) · [2016-2021](https://data.education.gouv.fr/explore/assets/fr-en-ips_colleges/) | **A** |
| **Observatoire des territoires (ANCT)** | Pub. (ANCT ; l'ex-CGET y est fondu depuis 2020) | Licence Ouverte 2.0 ⚠️ | Téléchargement par indicateur, API Géoclip | Commune, EPCI, département | Variable selon l'indicateur | **Agrégateur** : chaque indicateur reprend une source primaire (INSEE, DEPP…) ; préférer la source primaire pour la traçabilité, sauf zonages ANCT (FRR, Petites villes de demain, Action cœur de ville) dont l'ANCT est le producteur | ECO/GEO : zonages de politique publique (piste EC3) | [Données ouvertes](https://www.observatoire-des-territoires.gouv.fr/donnees_ouvertes) | **A** (zonages) / **B** (autres) |
| **Santé publique France — Odissé** (remplace Géodes) | Pub. | Licence Ouverte ⚠️ | OpenDataSoft, API | National, région, département, EPCI | Plus de 250 jeux ; lancé en avril 2025 | Géodes en fin de vie : ne pas coder contre ses URL ; peu d'indicateurs communaux | ECO/social : santé (mortalité, couverture vaccinale) au département ou EPCI | [Odissé](https://odisse.santepubliquefrance.fr/explore/) | **A** |
| Eurostat — NUTS3 (départements) | UE | CC BY 4.0 (politique de réutilisation de la Commission) ⚠️ | API SDMX (déjà utilisée) | NUTS3 = département (Nord FRE11, etc.) | PIB par département (`nama_10r_3gdp`) | Même piège de drapeaux que les jeux actuels | ECO : extension au département de la table `economie_contexte` | [nama_10r_3gdp](https://ec.europa.eu/eurostat/databrowser/view/nama_10r_3gdp/default/table?lang=en) | **A** |
| **Kohesio** (fonds européens FEDER, FSE+, par projet et bénéficiaire) | UE (Commission) | Avis juridique de la Commission (réutilisation autorisée) ⚠️ | CSV/XLSX par pays, RDF, SPARQL | Projet géolocalisé (commune ⚠️) | 2014-2020 ; 2021-2027 intégré depuis avril 2025 | Qualité dépendante des autorités de gestion (Région HdF) ; montants UE vs coût total | ECO : « l'Europe dans ma commune » (contexte des européennes) | [Kohesio](https://kohesio.ec.europa.eu/fr/) · [Services d'export](https://kohesio.ec.europa.eu/en/services) | **B+** |
| Agence Bio — surfaces, cheptels et opérateurs par commune | Pub. | Licence Ouverte ⚠️ | CSV | Commune (siège de l'exploitation) | Historique ⚠️ | Parcelles déclarées à la commune du siège, pas à la localisation réelle | Faible valeur pour les questions actuelles | [Historique par commune](https://www.data.gouv.fr/datasets/historique-detaille-des-surfaces-cheptels-et-nombre-doperateurs-par-commune) | **A** (faible priorité) |
| ADEME (data-fair) | Pub. | Licence Ouverte ⚠️ | API | Variable | Variable | — | Hors questions actuelles (transition écologique) | [Jeux ADEME](https://www.data.gouv.fr/organizations/ademe/datasets) | **A** (faible priorité) |

### 2.4 Géographie (compléments)

| Source | Prod. | Licence | Format | Gran. | Remarques | Mod. | URL | Note |
|---|---|---|---|---|---|---|---|---|
| IGN ADMIN-EXPRESS v4 — classe « canton » à contour réel | Pub. (IGN) | Licence Ouverte | WFS/GPKG | Canton (communes multi-cantonales découpées) | Nouveauté 2025 (version 4 d'ADMIN-EXPRESS) : lève le prérequis GE5 / EL3 | GEO/ELEC | [Nouveautés ADMIN-EXPRESS v4](https://geoservices.ign.fr/actualites/2025-04-adminexpress-evolution) | **A** |
| INSEE — aires d'attraction des villes 2020 et grille de densité (piste GE3) | Pub. (INSEE) | Licence Ouverte | XLSX/CSV | Commune | URL confirmée pour la piste GE3 du rapport R&D (qui la notait ⚠️) ; rétropolation 2010 disponible | GEO/ECO | [Base AAV 2020](https://www.insee.fr/fr/information/4803954) · [Rétropolation 2010](https://www.insee.fr/fr/statistiques/7615286) | **A** |

### 2.5 Sources régionales et locales Hauts-de-France

| Source | Prod. | Licence | Contenu repéré | Valeur pour le projet | URL | Note |
|---|---|---|---|---|---|---|
| Open data Région Hauts-de-France (Datahub) | Pub. (collectivité) | Licence Ouverte (à vérifier par jeu) ⚠️ | Environnement, tourisme, transports (GTFS), budget ; ancien portail `opendata.nordpasdecalais.fr` encore en ligne | Faible pour les questions électorales ; budget régional éventuel | [opendata.hautsdefrance.fr](https://opendata.hautsdefrance.fr/) | **B** |
| MEL — Métropole européenne de Lille | Pub. (collectivité) | Licence Ouverte 2.0 ou « licence particulière » selon le jeu | Mobilité, logement, déchets, limites administratives | Faible (données de gestion, périmètre MEL seulement) | [data.lillemetropole.fr](https://data.lillemetropole.fr/catalogue/search) | **B** |
| Oise Open Data (département 60) | Pub. | ⚠️ | Aménagement numérique, données départementales | Faible | [opendata.oise.fr](https://opendata.oise.fr/) | **B** |
| Académie HdF (data.hauts-de-france.education.gouv.fr) | Pub. | Licence Ouverte ⚠️ | Déclinaison régionale des jeux DEPP | Redondant avec la source nationale DEPP | [Portail académique](https://data.hauts-de-france.education.gouv.fr/) | **A** (redondant) |
| OR2S — plateforme sanitaire et sociale HdF | Asso. (observatoire régional, commandes ARS) | Non précisée ⚠️ | Diagnostics territoriaux de santé | Publications plutôt que jeux réutilisables ; à citer comme contexte | [or2s.fr](https://www.or2s.fr/) | **C** |
| Départements 02, 59, 62, 80 | — | — | Aucun portail de données pertinent identifié par la recherche | — | — | non évalué |
| CRESS HdF, Insee Hauts-de-France | — | — | Non recherchés en détail (Insee HdF publie des études, pas de jeux distincts de l'INSEE national) | — | — | non évalué |

**Constat** : l'échelon local n'apporte presque rien de spécifique pour les questions du projet. Les sources nationales, filtrées sur la région 32, restent la bonne voie.

### 2.6 Recherche et enquêtes

| Source | Prod. | Accès | Intérêt | Limite | URL | Note |
|---|---|---|---|---|---|---|
| CDSP / data.sciencespo (Dataverse) : enquêtes électorales françaises (ENEF 2022, enquête électorale 2024) | Acad. | Dépôt Dataverse ; conditions par jeu (inscription, usage recherche) ⚠️ | Comportement individuel (déclaratif) : contexte national | Pas de granularité communale ni HdF exploitable ; conditions d'usage à lire | [Entrepôt Sciences Po](https://entrepot.recherche.data.gouv.fr/dataverse/sciencespo) · [ENEF 2022](https://www.sciencespo.fr/cevipof/fr/content/lenquete-electorale-francaise-2022-enef-2022.html) | **B** (contexte seulement) |
| Baromètre de la confiance politique (CEVIPOF) | Acad. (terrain OpinionWay) | Rapports publiés ; données brutes non repérées en accès libre | Contexte national | Aucune donnée territoriale | [Baromètre](https://www.sciencespo.fr/cevipof/fr/etudes-enquetes/barometre-confiance-politique/) | **C** |

---

## 3. Sources écartées

| Source | Raison |
|---|---|
| Cerema — DV3F et Fichiers fonciers | Accès restreint aux « ayants droit » (portail dédié depuis le 01/10/2024), engagement d'usage : incompatible avec une diffusion publique |
| DVF | Déjà écartée en phase E par décision (rapport R&D, EC6) ; ne pas rouvrir sans demande |
| OCDE — statistiques régionales TL3 | TL3 = NUTS3 pour la France : **doublon d'Eurostat**, qui est déjà intégré. Licence CC BY 4.0 depuis le 01/07/2024, donc pas de risque, seulement pas de valeur ajoutée |
| ArianeWeb (Conseil d'État) | Moteur de recherche sans export en masse ; remplacé par l'open data de la justice administrative (§2.1) |
| Ministère de la Justice (SDSE, « Références statistiques Justice ») | Publications nationales ; CSV par juridiction limité à 2004-2012 ; pas de granularité communale |
| Cour des comptes et CRC | Rapports et jurisprudence en texte ; les données chiffrées de finances locales sont mieux servies par l'OFGL. Les rapports d'observations définitives des CRC pourraient servir de lien documentaire dans une fiche commune (P3) |
| CGET | Dissous dans l'ANCT (2020) : voir Observatoire des territoires |
| Géodes (Santé publique France) | Remplacé par Odissé (avril 2025) : fin de vie |
| NosDéputés / NosSénateurs (Regards Citoyens) | Licence CC BY-NC-SA, métriques AN vides depuis 2024 (déjà abandonné) |
| France-Politique (L. de Boissieu) | Site personnel de journaliste, sans licence de réutilisation : utile comme **lecture de contrôle** des nuances, pas comme source de données |
| Site d'archives des résultats du ministère de l'Intérieur (HTML) | Extraction de pages web contraire à la règle « sources officielles réutilisables » ; les mêmes données sont dans le Parquet agrégé |
| Sondages d'intentions de vote (instituts privés) | Privés, licences restrictives, pas de granularité territoriale |
| Banque des territoires | Non producteur de jeux de données propres pertinents repérés (relaye INSEE et ANCT) — non approfondi |

---

## 4. Alertes

| Type | Alerte | Conséquence |
|---|---|---|
| Rupture de série | **DARES / France Travail** : inscription automatique des allocataires du RSA (loi « pour le plein emploi ») ; création des catégories F et G ; label de l'Autorité de la statistique publique suspendu au 01/01/2025 pour 2025-2026 ([avis du 15/11/2024, JORFTEXT000050655620](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000050655620)) | Ne jamais tracer une courbe continue 2024 → 2025 ; limiter aux catégories A, B, C et signaler la rupture |
| Rupture de série | Filosofi 2021 → 2023 (et trou 2022) : voir rapport R&D, V2 | IRCOM peut servir de série de revenus continue (autre concept : revenu déclaré) |
| Rupture de série | DEPP IPS collèges : deux séries (2016-2021, depuis 2023) | Pas de comparaison directe sans note méthodologique |
| Rupture de série | REI : suppression de la taxe d'habitation sur les résidences principales (2021-2023) | Comparer seulement la taxe foncière dans le temps |
| Secret statistique | SSMSI : environ 48 % des lignes communales masquées | Carte communale trompeuse (absence de donnée ≠ absence de délits) ; préférer l'agrégation EPCI ou département |
| Fin de vie | Géodes (Santé publique France) → Odissé | Utiliser Odissé |
| Fin de vie | NosDéputés (déjà constaté) | Rien à faire |
| Licence à risque | **ODbL** (HowTheyVote) : partage à l'identique de la base dérivée si elle est diffusée (la base DuckDB est publiée en GitHub Release) | Décision de Mathias (question 4) |
| Licence à risque | **CC BY-NC-SA** (Regards Citoyens) : clause non commerciale | Déjà écarté |
| Licence à risque | **Cagé-Piketty** : pas de licence formelle, seulement une obligation de citation | Usage de contrôle seulement, sauf accord explicite |
| Couverture partielle | CNCCFP municipales : communes > 9 000 habitants seulement ; comptes municipaux 2026 pas encore publiés | Nombre de communes HdF concernées à mesurer (population municipale > 9 000) |
| Couverture partielle | Justice administrative : décisions des tribunaux administratifs seulement depuis 30/06/2022 | Contentieux municipal 2020 absent |
| **Incohérence dans la documentation du projet** | `docs/data-sources.md` décrit `FRE` comme « NUTS2 (Hauts-de-France) ». Dans la nomenclature NUTS en vigueur, **FRE est le niveau NUTS1** ; les niveaux NUTS2 sont FRE1 (Nord-Pas-de-Calais) et FRE2 (Picardie) ([Wikipédia, NUTS de France](https://en.wikipedia.org/wiki/NUTS_statistical_regions_of_France), à confirmer sur la nomenclature Eurostat) | Correction documentaire à faire par le documentaliste ; vérifier aussi que les données chargées sont bien des séries NUTS1 |
| Source non officielle en production | Circonscriptions : jeu jerome-desboeufs (déjà signalé) | Remplacement possible par le jeu Etalab (question 2) |

---

## 5. Recommandation argumentée

Dans l'esprit « consolider puis approfondir », l'ordre proposé (à valider) :

1. **Consolider (sans nouvelle thématique)** : remplacer les contours de circonscriptions par le jeu Etalab (source officielle dérivée de l'Intérieur, effort S) ; corriger la mention NUTS dans la documentation.
2. **Approfondir à fort rendement** :
   - CNCCFP législatives 2022 et 2024 : jointure simple candidat × circonscription, donnée originale et vérifiable ;
   - IRCOM : série de revenus communale continue face à la rupture Filosofi ;
   - CONSTIT : annotation « élection annulée / inéligibilité » dans les fiches élus et circonscriptions.
3. **Ensuite** : OFGL (fiche commune), DEPP IPS, DARES (avec la rupture 2025 affichée).
4. **Sur décision explicite seulement** : SSMSI (sensibilité politique, secret statistique) et votes au Parlement européen (licence ODbL).

Chaque intégration retenue passe d'abord par une exploration sur le Mac (lecture des en-têtes, encodage, séparateur, volume), puisqu'aucun fichier n'a pu être ouvert ici.

---

## 6. Questions fermées pour Mathias (5)

1. Ajoutez-vous la **CNCCFP** aux sources autorisées, avec comme première intégration les comptes des législatives 2022 et 2024 pour les circonscriptions HdF ? **Oui / Non**
2. Remplace-t-on la source de circonscriptions non officielle (jerome-desboeufs) par le jeu **Etalab « Contours géographiques des circonscriptions législatives »** après exploration comparative ? **Oui / Non**
3. Les données de **délinquance enregistrée (SSMSI)** entrent-elles dans le périmètre du projet ? **Oui, au niveau commune / Oui, au niveau EPCI-département seulement / Non**
4. Pour les licences à partage à l'identique ou sans licence formelle (HowTheyVote en ODbL, Cagé-Piketty) : **(a)** exclure ; **(b)** autoriser l'ODbL seulement, avec mention dans la base diffusée ; **(c)** décider au cas par cas avec un ADR.
5. Première source Économie hors INSEE à intégrer : **(a)** IRCOM (revenus, continuité) ; **(b)** OFGL (finances locales) ; **(c)** DARES (chômage enregistré communal) ?

---

## 7. Proposition de mise à jour de CLAUDE.md (texte prêt à coller, à valider — CLAUDE.md non modifié)

Remplace la section « Sources de données autorisées » (jusqu'à la liste « Datasets clés » exclue) :

```markdown
## Sources de données autorisées

Règle : producteur public officiel ou source documentée sous licence ouverte ; pas d'extraction de pages web.
Toute source hors de cette liste = proposition à valider par Mathias. Catalogue détaillé :
`reports/catalogue-sources-2026-09-24.md`.

**Plateformes et API (sans clé sauf mention)**
- **data.gouv.fr** : `https://www.data.gouv.fr/api/1/` ; **API Tabulaire** : `https://tabular-api.data.gouv.fr/api/` (≤100MB CSV)
- **INSEE** : `https://portail-api.insee.fr/` (Mélodi sans auth, Sirene/Métadonnées OAuth2)
- **Légifrance** : PISTE `https://api.piste.gouv.fr/` (OAuth2) ou dumps DILA (JORF, LEGI, DOLE, CONSTIT) sous Licence Ouverte
- **Géographie** : `https://geo.api.gouv.fr/`, `https://data.geopf.fr/` (IGN)
- **AN/Sénat** : data.assemblee-nationale.fr (Licence Ouverte), data.senat.fr (licence Sénat dérivée de la Licence Ouverte)
- **HATVP** : `https://www.hatvp.fr/open-data/` (déclarations, répertoire des représentants d'intérêts)
- **OSM** : Overpass `https://overpass-api.de/api/interpreter`

**Producteurs publics déjà utilisés** : CNAF (data.caf.fr), DREES, URSSAF (open.urssaf.fr), Eurostat (API SDMX), Datan (via data.gouv.fr).

**Producteurs publics validés pour exploration** (ajout proposé le 2026-09-24, sous réserve de validation) :
- CNCCFP (comptes de campagne et des partis, via data.gouv.fr)
- Conseil constitutionnel (CONSTIT) et justice administrative (opendata des décisions depuis 2021-2022)
- DGFiP (IRCOM, REI) et OFGL (`https://data.ofgl.fr/`, finances locales)
- DARES / France Travail (inscrits par commune ; rupture de série 2025)
- DEPP (`https://data.education.gouv.fr/`, IPS)
- SSMSI (délinquance enregistrée, via data.gouv.fr ; sujet sensible, décision préalable requise)
- ANCT — Observatoire des territoires (zonages FRR, PVD, ACV)
- Santé publique France — Odissé (remplace Géodes)
- Kohesio (Commission européenne, fonds FEDER/FSE+)

**Sources non publiques à licence spécifique (usage soumis à décision de Mathias)** : HowTheyVote.eu (ODbL),
Cagé-Piketty « Une histoire du conflit politique » (citation obligatoire, pas de licence formelle).

**Écartées** : Regards Citoyens (CC BY-NC-SA), Cerema DV3F/Fichiers fonciers (accès restreint), DVF (décision
phase E), OCDE régional (doublon Eurostat), pages HTML du site d'archives électorales de l'Intérieur (extraction).
```

---

## 8. Sources consultées (recherche web du 24/09/2026, pages non ouvertes)

- CNCCFP : [organisation data.gouv](https://www.data.gouv.fr/organizations/commission-nationale-des-comptes-de-campagne-et-des-financements-politiques-cnccfp) · [législatives 2022](https://www.data.gouv.fr/datasets/comptes-de-campagne-elections-legislatives-generales-des-12-et-19-juin-2022) · [municipales 2020](https://www.data.gouv.fr/datasets/comptes-de-campagne-elections-municipales-generales-des-15-mars-et-28-juin-2020) · [comptes des partis](https://www.data.gouv.fr/datasets/comptes-des-partis-et-groupements-politiques) · [publication 2024](https://cnccfp.fr/elections-legislatives-des-30-juin-et-7-juillet-2024-publication-simplifiee-des-comptes-de-campagne/) · [avis JORF 2024](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000051935355) · [municipales (CNCCFP)](https://cnccfp.fr/elections/elections-municipales/)
- Élections : [contours circonscriptions](https://www.data.gouv.fr/datasets/contours-geographiques-des-circonscriptions-legislatives) · [table de correspondance](https://www.data.gouv.fr/datasets/circonscriptions-legislatives-table-de-correspondance-des-communes-et-des-cantons-pour-les-elections-legislatives-de-2012-et-sa-mise-a-jour-pour-les-elections-legislatives-2017) · [candidatures 2024](https://www.data.gouv.fr/datasets/candidatures-aux-elections-legislatives-2024) · [sénatoriales 2023](https://www.data.gouv.fr/datasets/elections-senatoriales-2023-resultats) · [législatives 1958-2012](https://www.data.gouv.fr/datasets/elections-legislatives-1958-2012) · [présidentielles 1965-2012](https://www.data.gouv.fr/datasets/elections-presidentielles-1965-2012-1) · [Cagé-Piketty](https://www.unehistoireduconflitpolitique.fr/telecharger.html) · [annexes](http://piketty.pse.ens.fr/files/CagePiketty2023Annexes.pdf) · [archives Intérieur](https://www.archives-resultats-elections.interieur.gouv.fr/resultats/senatoriales2023/index.php) · [REU INSEE](https://www.insee.fr/fr/statistiques/8888278)
- Contentieux : [CONSTIT](https://www.data.gouv.fr/datasets/constit-les-decisions-du-conseil-constitutionnel) · [Conseil constitutionnel, données ouvertes](https://www.conseil-constitutionnel.fr/donnees-ouvertes) · [Conseil d'État, open data](https://www.conseil-etat.fr/decisions-de-justice/donnees-ouvertes-open-data) · [open data Conseil d'État (data.gouv)](https://www.data.gouv.fr/datasets/open-data-du-conseil-detat)
- Législatif : [licence AN](https://data.assemblee-nationale.fr/licence-ouverte-open-licence) · [licence Sénat](https://data.senat.fr/licence/) · [JORF](https://www.data.gouv.fr/datasets/jorf-les-donnees-de-l-edition-lois-et-decrets-du-journal-officiel) · [DOLE](https://www.data.gouv.fr/datasets/dole-les-dossiers-legislatifs) · [HATVP répertoire](https://www.hatvp.fr/open-data-repertoire/) · [PE open data](https://data.europarl.europa.eu/en/home) · [HowTheyVote data](https://github.com/HowTheyVote/data) · [HowTheyVote about](https://howtheyvote.eu/about) · [Datan méthode](https://datan.fr/statistiques/aide) · [Regards Citoyens open data](https://github.com/regardscitoyens/nosdeputes.fr/blob/master/doc/opendata.md) · [portraits circonscriptions INSEE](https://www.insee.fr/fr/statistiques/6436478)
- Économie et social : [IRCOM](https://www.data.gouv.fr/datasets/limpot-sur-le-revenu-par-collectivite-territoriale-ircom) · [REI](https://www.data.gouv.fr/datasets/impots-locaux-fichier-de-recensement-des-elements-dimposition-a-la-fiscalite-directe-locale-rei-4) · [OFGL communes](https://data.ofgl.fr/explore/dataset/ofgl-base-communes/) · [DARES communal](https://data.gouv.fr/en/datasets/demandeurs-demploi-inscrits-a-france-travail-donnees-communales-trimestrielles-brutes) · [avis ASP](https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000050655620) · [SSMSI](https://www.data.gouv.fr/datasets/bases-statistiques-communale-departementale-et-regionale-de-la-delinquance-enregistree-par-la-police-et-la-gendarmerie-nationales) · [Interstats 2024](https://www.bnsp.insee.fr/ark:/12148/bc6p09qp6vd.pdf) · [IPS écoles](https://data.education.gouv.fr/explore/assets/fr-en-ips-ecoles-ap2022/) · [IPS collèges 2023+](https://data.education.gouv.fr/explore/assets/fr-en-ips-colleges-ap2023/) · [Observatoire des territoires](https://www.observatoire-des-territoires.gouv.fr/donnees_ouvertes) · [Odissé](https://odisse.santepubliquefrance.fr/explore/) · [nama_10r_3gdp](https://ec.europa.eu/eurostat/databrowser/view/nama_10r_3gdp/default/table?lang=en) · [Kohesio](https://kohesio.ec.europa.eu/en/services) · [Agence Bio](https://www.data.gouv.fr/datasets/historique-detaille-des-surfaces-cheptels-et-nombre-doperateurs-par-commune) · [OCDE licence](https://www.oecd.org/en/about/terms-conditions.html)
- Géographie : [ADMIN-EXPRESS v4](https://geoservices.ign.fr/actualites/2025-04-adminexpress-evolution) · [AAV 2020](https://www.insee.fr/fr/information/4803954) · [NUTS de France](https://en.wikipedia.org/wiki/NUTS_statistical_regions_of_France)
- Régional : [Région HdF](https://opendata.hautsdefrance.fr/) · [MEL](https://data.lillemetropole.fr/catalogue/search) · [Oise](https://opendata.oise.fr/) · [OR2S](https://www.or2s.fr/)
- Recherche : [entrepôt Sciences Po](https://entrepot.recherche.data.gouv.fr/dataverse/sciencespo) · [ENEF 2022](https://www.sciencespo.fr/cevipof/fr/content/lenquete-electorale-francaise-2022-enef-2022.html) · [baromètre CEVIPOF](https://www.sciencespo.fr/cevipof/fr/etudes-enquetes/barometre-confiance-politique/)
- Écartées : [Cerema DV3F](https://doc-datafoncier.cerema.fr/doc/fiche_descriptive/dv3f) · [SDSE Justice](https://www.justice.gouv.fr/sites/default/files/2024-02/RSJ2023_ouvrage_complet_1.pdf) · [Cour des comptes](https://www.data.gouv.fr/organizations/cour-des-comptes/)
