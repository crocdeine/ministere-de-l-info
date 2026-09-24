# R&D et veille technique — préparation de la feuille de route

**Date** : 2026-09-24
**Auteur** : agent « R&D et veille technique » (session cloud)
**Destinataire** : Mathias — arbitrage des orientations
**Nature** : document de travail. Aucune décision prise, aucun code modifié. Tout ce qui suit est une **proposition**.
**Périmètre exclu** (traité par d'autres agents) : bugs du code, classements de nuances (LCOM/LUDI/LUD/LECO, groupe FI), documentation, Docker/checksum, Docker vs natif sur Mac. Ces chantiers apparaissent ici seulement quand une piste en dépend.

---

## 0. Comment lire ce document

- **Effort** : **S** = une session de travail (quelques heures) · **M** = 2 à 4 sessions · **L** = une phase entière (plus de 4 sessions, avec ADR).
- **Priorité proposée** : **P1** = à faire dans la prochaine phase · **P2** = phase suivante · **P3** = plus tard ou seulement si besoin précis.
- **Statut des sources** :
  - ✅ **vérifié** = la page du jeu de données a été trouvée par recherche web le 24/09/2026 (titre et URL cohérents) ;
  - ⚠️ **partiel** = source trouvée mais format, millésime ou contenu exact à confirmer au moment de l'exploration ;
  - ❓ **non vérifié** = pas de confirmation en ligne.
- **Limite de la vérification** : depuis ce conteneur, l'ouverture directe des pages (WebFetch) est bloquée par le proxy (docs.streamlit.io, duckdb.org refusés). Les vérifications reposent donc sur la **recherche web** (titres, URL et extraits des résultats), pas sur la lecture intégrale des pages. Chaque piste retenue devra repasser par une phase d'exploration classique (rapport `exploration-*.md`) avant tout chargement.

---

## 1. Résumé exécutif

1. **Le projet est complet sur ses 4 modules, mais plusieurs de ses données vieillissent.** Filosofi s'arrête à 2021, le RP à 2021, la composition du Sénat date de juin 2026. Or **les sénatoriales ont lieu le 27 septembre 2026** (série 2, 178 sièges) : l'onglet Législatif sera faux dans 3 jours. Autre point : **Filosofi 2022 n'existera jamais** (INSEE, qualité insuffisante), et Filosofi 2023 (« Filosofi 2 ») **n'est pas comparable** aux millésimes précédents. Il faut une décision méthodologique sur cette rupture de série.
2. **Le clic sur la carte pour ouvrir le détail est probablement faisable sans changer d'outil.** La décision D2 (« st_folium ne renvoie pas les propriétés ») mérite une nouvelle vérification. Deux voies sont réalistes : (a) récupérer le point cliqué (`last_object_clicked`, latitude et longitude) et retrouver la commune dans DuckDB avec `ST_Contains` ; (b) utiliser `st.pydeck_chart(on_select=...)`, qui gère la sélection d'objets sur carte depuis Streamlit 1.39. Un essai court (S) suffit à trancher.
3. **La plus forte valeur analytique à faible coût vient des données déjà présentes.** Les européennes (1999-2024), les régionales et les départementales sont déjà dans le Parquet source. Des indicateurs dérivés (volatilité, abstention différentielle, cartes de bascule), une **fiche territoire** unique (commune ou circonscription : élections + économie + élus) et le croisement **député × résultats de sa circonscription** ne demandent aucune nouvelle source.
4. **Les nouvelles sources prioritaires sont vérifiées.** RNE (élus locaux), QPV 2024, BPE (équipements), votes nominatifs AN (`Scrutins.json.zip` de la 17e législature), contours des bureaux de vote (Etalab) et HATVP sont toutes publiées en open data.
5. **La pile technique a évolué depuis le verrouillage (Streamlit 1.57.0, DuckDB 1.5.2).** Streamlit est en 1.64 (15/09/2026), avec des changements cassants intermédiaires (1.61, 1.62) et le paramètre `use_container_width` déprécié (18 occurrences dans le code). DuckDB 1.5.4 est sorti et une version 2.0 est annoncée. Une montée de version contrôlée s'impose, **après** la mise en place de tests qui tournent sans la base complète.
6. **Industrialisation : le socle manquant est une petite base de test commitable.** Aujourd'hui, 342 tests sur environ 380 sont ignorés hors du Mac. Le chemin de la base est codé en dur dans 4 modules, et `pydantic-settings`, pourtant imposé par la stack, n'est utilisé nulle part. Proposition : centraliser ce chemin (S), puis produire une base échantillon d'environ 1 département HdF (M). Ce chantier conditionne la CI réelle et le travail en cloud.

**Recommandation de l'agent** : le scénario A (« Consolider ») d'abord, pendant 3 à 5 sessions, puis le scénario C (« Approfondir l'analyse »). L'extension géographique (scénario B) est la décision la plus lourde et la moins réversible : à ne trancher qu'après A.

---

## 2. Constats de veille qui changent la donne

| # | Constat | Conséquence pour le projet | Source |
|---|---|---|---|
| V1 | **Sénatoriales le 27/09/2026**, série 2, 178 sièges (Nord, Oise et Pas-de-Calais sont vraisemblablement renouvelés : à vérifier) | `leg_elus` Sénat obsolète dès le 1er octobre ; recharger le CSV data.senat.fr une fois le Sénat installé | [senatoriales2026.senat.fr](https://senatoriales2026.senat.fr/) · [Wikipédia](https://fr.wikipedia.org/wiki/%C3%89lections_s%C3%A9natoriales_fran%C3%A7aises_de_2026) · [résultats Intérieur](https://www.resultats-elections.interieur.gouv.fr/Senatoriales2026/index.html) |
| V2 | **Filosofi 2022 non produit** ; **Filosofi 2023 = nouveau dispositif « Filosofi 2 »**, non comparable à 2012-2021, **2 indicateurs seulement** au niveau communal (niveau de vie médian, taux de pauvreté). Correctif de diffusion le 06/08/2026 | Série cassée entre 2021 et 2023, trou en 2022. Il faut une règle d'affichage (rupture signalée, pas de ligne continue). Les autres indicateurs Filosofi ne sont plus mis à jour | [INSEE Filosofi 2023](https://www.insee.fr/fr/statistiques/8984752?sommaire=8984758) · [présentation Filosofi 2023](https://www.insee.fr/fr/metadonnees/source/operation/s2286/presentation) · [INSEE 2022](https://www.insee.fr/fr/statistiques/8278909) |
| V3 | **RP 2022 publié (juin 2025)**, rythme de publication N+3 ; RP 2023 attendu en juin 2026 (non vérifié) | Le projet s'arrête au RP 2021 : 1 à 2 millésimes de retard | [INSEE RP](https://www.insee.fr/fr/information/2008354) · [Évolution et structure 2022](https://www.insee.fr/fr/statistiques/8581696?sommaire=8581933) |
| V4 | **ZRR remplacées par « France Ruralités Revitalisation » (FRR)** au 1er juillet 2024, avec des communes réintégrées par arrêté ultérieur | La piste « ANCT ZRR » de la phase E est à renommer : charger FRR, pas ZRR | [AMF](https://www.amf.asso.fr/documents-france-ruralites-revitalisation-nouveau-dispositif-qui-remplacera-les-zrr-au-1er-juillet-2024/42098) · [Maire-Info](https://www.maire-info.com/ruralit%C3%A9/france-ruralites-revitalisation-(frr)-un-arr%EF%BF%BDte-confirme-la-reintegration-de-plus-de-2-000-communes-au-dispositif-article-29621) · [ecologie.gouv.fr](https://www.ecologie.gouv.fr/dossiers/france-ruralites-apporter-solutions-aux-habitants-milieu-rural/evolution-zones) |
| V5 | **QPV : nouvelle géographie 2024** (décret 2023-1314), contours et listes communes/adresses publiés | La piste QPV reste valable : prendre le millésime 2024 | [data.gouv QPV 2024](https://www.data.gouv.fr/datasets/carte-des-quartiers-prioritaires-de-la-politique-ville-2024) · [QPV communes 2024](https://www.data.gouv.fr/datasets/qpv-communes-2024) |
| V6 | **Populations de référence 2023** (le terme remplace « populations légales ») publiées avec population municipale, **comptée à part** et totale ; Mayotte traitée à part, avec un recensement exhaustif au 1er janvier 2026 (323 153 hab.) | Débloque le PCAP (colonnes `comptee_a_part` et `totale` aujourd'hui NULL) et Mayotte | [INSEE fichier d'ensemble 2023](https://www.insee.fr/fr/statistiques/8680726) · [Mayotte 2026](https://www.insee.fr/fr/statistiques/9021428) |
| V7 | **Streamlit 1.57 → 1.64** : `st.fragment(parallel=True)`, `st.pagination`, `st.App` (1.5x-1.6x) ; chargement paresseux de `st.dataframe` et rafraîchissement du cache en arrière-plan (1.61) ; `st.cache` supprimé (1.62) ; async/await, `st.echarts_chart` (1.64, 15/09/2026) | Gains réels (dataframes lourds, cache). Montée de version à faire avec des tests UI. `use_container_width` déprécié, retrait annoncé « après 2025-12-31 » : 18 occurrences dans `economie.py` et `legislatif.py` | [Notes de version 2026](https://docs.streamlit.io/develop/quick-reference/release-notes/2026) · [1.64.0](https://discuss.streamlit.io/t/version-1-64-0/122545) · [1.62.0](https://newreleases.io/project/github/streamlit/streamlit/release/1.62.0) · [dépréciation width](https://discuss.streamlit.io/t/cursorrules-for-deprecated-use-container-width/119576) |
| V8 | **DuckDB 1.5** (09/03/2026) : type `GEOMETRY` intégré au cœur, stockage WKB, statistiques de boîte englobante par groupe de lignes, requêtes spatiales plus rapides. **1.5.4** publiée le 17/06/2026 avec un aperçu de la 2.0 ; la LTS 1.4 est en fin de vie en septembre 2026 | Opportunité : cartes et filtres spatiaux plus rapides. Risque : compatibilité du format de fichier avec la 2.0, à surveiller avant toute montée (la base de 900 Mo est distribuée via GitHub Release) | [Annonce 1.5.0](https://duckdb.org/2026/03/09/announcing-duckdb-150) · [Annonce 1.5.4](https://duckdb.org/2026/06/17/announcing-duckdb-154) · [endoflife.date](https://endoflife.date/duckdb) |
| V9 | **Kaleido ≥ 1.0 (export d'images Plotly) exige Chrome** installé sur la machine | Pour les rapports PDF, exporter les graphiques Plotly impose Chrome dans l'image Docker. Alternative : matplotlib, autorisé par CLAUDE.md pour les exports de figures de rapport | [Kaleido](https://github.com/plotly/Kaleido) · [Plotly static export](https://plotly.com/python/static-image-export/) |
| V10 | **Tectonic** : la recherche web signale une version 0.17.0 (27/07/2026), **non confirmée** ; le Dockerfile racine fige 0.16.9 | Pas d'urgence : 0.16.9 suffit. Vérifier le changelog avant de monter de version | [Site Tectonic](https://tectonic-typesetting.github.io/en-US/) · [CHANGELOG](https://docs.rs/crate/tectonic/latest/source/CHANGELOG.md) |
| V11 | **ty** (vérificateur de types d'Astral, les auteurs de uv et ruff) en bêta, version 1.0 visée en 2026 | Candidat naturel pour le typage, dans l'écosystème déjà choisi (ADR-0003) ; pyright reste l'option stable | [Astral blog](https://astral.sh/blog/ty) · [InfoWorld](https://www.infoworld.com/article/4108979/python-type-checker-ty-now-in-beta.html) |

---

## 3. Inventaire des pistes fonctionnelles

Légende : « Origine » = **R** (déjà évoquée dans un rapport du projet) ou **N** (piste nouvelle).

### 3.1 Module Élections

| ID | Piste | Orig. | Valeur éditoriale et analytique | Sources | Effort | Dépendances | Risques méthodologiques | Prio |
|---|---|---|---|---|---|---|---|---|
| **EL1** | **Européennes 1999-2024 HdF** | R | Seul scrutin national à la proportionnelle intégrale : meilleure mesure du rapport de force « pur » des blocs. 2024 = scrutin déclencheur de la dissolution | ✅ déjà dans le Parquet [élections agrégées](https://www.data.gouv.fr/datasets/donnees-des-elections-agregees) (6 scrutins) | M | Corrections de nuances (autre agent) ; ADR-0005 à étendre | `nuance` NULL en 2019 (34 listes : table des listes à construire, sur le modèle de `candidats_presidentielle`) ; listes « personnalités » difficiles à classer ; un seul tour | **P1** |
| **EL2** | **Régionales 2004-2021** | R | Dimension HdF directe (conseil régional) ; 2015 = fusion Nord-Pas-de-Calais-Picardie | ✅ Parquet (8 tours) | M | EL1 (même logique de listes) ; ADR-0005 | Listes d'union régionales mal nuancées ; 2004/2010 dans l'ancienne région Picardie + Nord-Pas-de-Calais : comparaisons HdF à reconstruire (loi NOTRe) | P2 |
| **EL3** | **Départementales 2015/2021 et cantonales 2001-2011** | R | Échelon du RSA et du social, à croiser avec le module Économie | ✅ Parquet | L | Géométries des **cantons** (absentes du projet ; redécoupage 2014) | Binômes depuis 2015 ; cantonales = renouvellement par moitié, non comparable ; forte abstention | P3 |
| **EL4** | **Clic sur la carte → détail (drill-down)** | R | Principal geste des tableaux de bord électoraux ; remplace les listes déroulantes | Technique (voir §4.1) | S (essai) + M | Aucune | Aucun | **P1** |
| **EL5** | **Indicateurs dérivés** : volatilité entre scrutins, indice de nationalisation, abstention différentielle, cartes de « bascule » (commune qui change de bloc dominant), écart à la moyenne HdF | N | Forte valeur analytique sans nouvelle source ; répond à « où le vote a-t-il bougé ? » | Données en base | S-M | Classements corrigés | Choisir des formules publiées (ex. indice de Pedersen) et les documenter ; attention aux petites communes (effets de taille) | **P1** |
| **EL6** | **Contours des bureaux de vote** (cartes au bureau de vote) | N | Le drill-down BV existe en tableau ; la carte au BV montre les fractures intra-urbaines (Lille, Amiens, Roubaix) | ✅ [Contours BV (Etalab)](https://www.data.gouv.fr/datasets/proposition-de-contours-des-bureaux-de-vote) · ✅ [BV et adresses (REU)](https://www.data.gouv.fr/datasets/bureaux-de-vote-et-adresses-de-leurs-electeurs) · ✅ [Bureaux de vote 2026](https://www.data.gouv.fr/datasets/bureaux-de-vote-2026) | M | Correspondance des codes BV entre millésimes | Contours **approximatifs** (reconstruits à partir d'adresses) ; les BV changent entre scrutins : carte valable pour un seul millésime | P2 |
| **EL7** | **Liaison IRIS ↔ bureau de vote** : croiser vote et données socio-démographiques infra-communales | N | Rend le croisement économie × élections pertinent dans les grandes villes (aujourd'hui limité à la commune) | ✅ [Liaison IRIS/BV 2024](https://www.data.gouv.fr/datasets/liaison-iris-bureaux-de-vote-de-2024) ; Filosofi IRIS 2021 ⚠️ | M | EL6 conseillé | Erreur écologique (corrélation ≠ comportement individuel), déjà signalée dans l'UI ; secret statistique IRIS | P2 |
| **EL8** | **Transferts de voix** (T1 → T2, ou d'un scrutin à l'autre) par inférence écologique au bureau de vote | R/N | Très demandé éditorialement (« où sont allés les électeurs de X ? ») | Données en base (BV) ; bibliothèque [PyEI](https://github.com/mggg/ecological-inference) ✅ | L | EL5 ; dépendance lourde (PyMC) ; ADR requis | **Risque élevé** : estimations et non observations ; intervalles d'incertitude obligatoires ; sensibles aux hypothèses. À présenter comme une estimation, jamais comme un fait | P3 |
| **EL9** | **Simulations de mode de scrutin** (ex. législatives 2024 recalculées à la proportionnelle départementale ; municipales 2026 avec prime majoritaire) | N | Pédagogique ; débat actuel sur la proportionnelle | Données en base | M | EL5 | Hypothèse « comportement de vote inchangé » à afficher ; règles de calcul (plus forte moyenne, seuils) sourcées dans le Code électoral | P3 |
| **EL10** | **Participation fine** : blancs et nuls, procurations (si disponibles), abstention par âge via RP | N | L'abstention est le premier « parti » dans les HdF | Base + RP | S | — | Pas de données individuelles de participation : abstention par âge seulement par corrélation | P2 |

### 3.2 Module Géographie

| ID | Piste | Orig. | Valeur | Sources | Effort | Dépendances | Risques | Prio |
|---|---|---|---|---|---|---|---|---|
| **GE1** | **PCAP** : population comptée à part et population totale | R | Ferme une limite connue ; utile pour les seuils électoraux (1 000 / 3 500 hab.) et le financement des communes | ✅ [Populations de référence 2023](https://www.insee.fr/fr/statistiques/8680726) | S | — | Les seuils légaux se basent sur la **population municipale** : ne pas confondre dans l'UI | P2 |
| **GE2** | **Mayotte** | R | Complétude nationale | ✅ [Populations Mayotte 2026](https://www.insee.fr/fr/statistiques/9021428) | S | — | Méthode de recensement spécifique ; hors périmètre HdF (utile seulement si Géographie reste nationale) | P3 |
| **GE3** | **Zonages d'étude INSEE** : grille communale de densité, aires d'attraction des villes | N | Permet de dire « rural / périurbain / urbain » dans tous les croisements, ce qui est central dans l'analyse du vote RN | ⚠️ INSEE (zonages publiés, URL précise à confirmer) | S | — | Millésime du zonage ≠ millésime du scrutin : documenter | **P1** |
| **GE4** | **EPT du Grand Paris** (11 EPT sans département) | R | Correction de données nationale | Mapping manuel | S | — | Hors HdF | P3 |
| **GE5** | **Géométries des cantons** (post-2014) | N | Prérequis d'EL3 | ⚠️ IGN ADMIN-EXPRESS (couche canton à vérifier) | S | — | Cantons ≠ circonscriptions administratives antérieures à 2014 | P3 |

### 3.3 Module Économie

| ID | Piste | Orig. | Valeur | Sources | Effort | Dépendances | Risques | Prio |
|---|---|---|---|---|---|---|---|---|
| **EC1** | **Mise à jour des millésimes** : RP 2022 (et 2023 si publié), Filosofi 2023 (« Filosofi 2 »), CNAF 2025, URSSAF | N | Garder l'outil à jour ; municipales 2026 croisées avec des données 2021 = 5 ans d'écart | ✅ RP 2022 · ✅ Filosofi 2023 · ⚠️ vérifier que le dataset OLAP data.gouv (`67289477639527408ae687da`) a intégré les nouveaux millésimes | M | Décision sur la rupture Filosofi (§7, Q4) | **Rupture de série Filosofi** (2012-2021 ≠ 2023) et **trou 2022** ; les indicateurs Filosofi autres que médiane et pauvreté disparaissent | **P1** |
| **EC2** | **QPV 2024** (quartiers prioritaires) : filtre « commune avec QPV », part de la population en QPV | R | Territoires de la politique de la ville : croisement avec l'abstention et le vote | ✅ [Carte QPV 2024](https://www.data.gouv.fr/datasets/carte-des-quartiers-prioritaires-de-la-politique-ville-2024) · ✅ [QPV communes 2024](https://www.data.gouv.fr/datasets/qpv-communes-2024) | S-M | — | QPV 2015 ≠ QPV 2024 : comparer seulement à géographie constante | P2 |
| **EC3** | **France Ruralités Revitalisation** (ex-ZRR) | R (renommée) | Symétrique rural des QPV | ⚠️ liste officielle par arrêté (jeu data.gouv non trouvé : ❓) | S | — | Deux arrêtés successifs (réintégrations) : dater le zonage | P3 |
| **EC4** | **BPE : équipements et services** (écoles, bureaux de poste, médecins, gares, commerces) | N | Thèse de la « France des services publics qui disparaissent » × vote : question éditoriale forte, qui complète les déserts médicaux | ✅ [INSEE BPE 2025](https://www.insee.fr/fr/statistiques/8217537) · ✅ [data.gouv BPE](https://www.data.gouv.fr/datasets/base-permanente-des-equipements-1) | M | GE3 conseillé | Changements de nomenclature BPE entre millésimes ; présence ≠ accessibilité (temps de trajet) | **P2** (haut de liste) |
| **EC5** | **Sirene géolocalisé** (tissu d'entreprises, créations) | R (ADR-0006) | Complète l'URSSAF (qui couvre l'emploi salarié privé, pas le nombre d'établissements) | ✅ [Sirene géolocalisé (stat.)](https://www.data.gouv.fr/datasets/geolocalisation-des-etablissements-du-repertoire-sirene-pour-les-etudes-statistiques) · ✅ [GeoParquet 2024](https://www.data.gouv.fr/datasets/base-sirene-des-etablissements-2024-geolocalisee-geoparquet) | M-L | — | Volumétrie nationale importante (filtrer HdF) ; établissements non diffusibles ; redondance partielle avec l'URSSAF | P3 |
| **EC6** | DVF (prix immobiliers) | R (écartée en phase E) | — | — | — | — | Écartée par décision : ne pas rouvrir sans demande | — |

### 3.4 Module Législatif

| ID | Piste | Orig. | Valeur | Sources | Effort | Dépendances | Risques | Prio |
|---|---|---|---|---|---|---|---|---|
| **LG1** | **Croisement législatif × élections** : le député sortant a-t-il été réélu ? Score du député vs score de son bloc à la présidentielle dans sa circonscription ; « sur-performance personnelle » | R | Relie les deux modules existants ; spécifique au projet | Données en base (`leg_elus.num_circo` × `code_circo`) | M | Correction du mapping FI par législature (autre agent) ; attention au redécoupage 2012 | Jointure députés ↔ circonscriptions à valider (circonscriptions non officielles AN, `code_circo` reconstruit) | **P1** |
| **LG2** | **Votes nominatifs AN** (qui a voté quoi, cohésion des groupes, proximité entre groupes) | R | Très forte valeur : passer du « combien » (scores Datan) au « quoi » | ✅ AN : `Scrutins.json.zip` (17e législature) et `AMO30_tous_acteurs_tous_mandats_tous_organes_historique.json.zip` ; archives 15e et 16e ✅ [data.assemblee-nationale.fr](https://data.assemblee-nationale.fr/travaux-parlementaires/votes) ; republication ✅ [NosParlementaires 17e](https://www.data.gouv.fr/datasets/votes-et-activite-des-parlementaires-francais-17e-legislature-nosparlementaires) | L | LG3 (identifiants acteurs) ; ADR (nouvelle source, nouveau schéma) | Volumétrie (des milliers de scrutins × 577 députés) ; ne pas surinterpréter les absences (délégations de vote, vote par groupe) ; choisir scrutins solennels vs tous | **P2** |
| **LG3** | **Historique fiable des mandats** via AMO30 (acteurs, mandats, organes de l'AN) | N | Corrige la limite « législature de référence = dernière » de l'onglet Évolution historique | ✅ AN (voir LG2) | M | — | Mapping identifiants AN (`PA…`) ↔ Datan | P2 |
| **LG4** | **Rafraîchissement du Sénat après le 27/09/2026** | N | Sans cela, composition fausse dès octobre | ✅ data.senat.fr (source déjà utilisée) | S | Groupes du nouveau Sénat constitués (début octobre) | Nouveaux groupes à classer en blocs (table groupes → blocs, sans ADR à ce jour) | **P1** (daté) |
| **LG5** | **Scrutins publics du Sénat** | R | Équivalent de LG2 pour le Sénat | ⚠️ base Dosleg (scrutins depuis 2006) distribuée en **dump PostgreSQL 8.4** : [notice Dosleg](https://data.senat.fr/aide/travaux-legislatifs-base-dosleg/) | L | LG2 d'abord | Format lourd (restauration PostgreSQL ou analyse du dump SQL) ; pas de « score d'activité » officiel Sénat | P3 |
| **LG6** | **RNE : élus locaux** (maires, conseillers municipaux, communautaires, départementaux, régionaux) : âge, sexe, catégorie socio-professionnelle, parité | R (liste CLAUDE.md) | Portrait des élus des HdF ; lien municipales 2026 → maire effectivement élu | ✅ [RNE élus locaux](https://www.data.gouv.fr/datasets/donnees-du-repertoire-national-des-elus-locaux-municipaux-communautaires-epci-departementaux-regionaux) · ✅ [RNE](https://www.data.gouv.fr/datasets/repertoire-national-des-elus-1) (mise à jour trimestrielle) | M | — | Profession **déclarative** ; nuance des élus locaux ≠ nuance des listes ; données personnelles (pas d'exposition gratuite de dates de naissance) | **P2** (haut de liste) |
| **LG7** | **HATVP** : déclarations d'intérêts et de patrimoine publiées (métadonnées) | R (liste CLAUDE.md) | Transparence de la vie publique | ✅ [HATVP open data](https://www.hatvp.fr/open-data/) (`liste.csv`, mise à jour chaque nuit) | S (métadonnées) à L (contenu) | LG3 (identifiants) | **Données personnelles** : se limiter aux métadonnées publiques (date, type de déclaration, lien) ; ne pas reconstituer de patrimoines. Décision éthique à prendre | P3 |
| **LG8** | **Législatif × économie** : profil socio-économique des circonscriptions des députés | R | Portrait « qui représente qui » | Base (agrégation commune → circonscription) | M | LG1 | Communes coupées entre circonscriptions (13 cas HdF) : pondération à documenter | P2 |

### 3.5 Transversal

| ID | Piste | Orig. | Valeur | Sources | Effort | Dépendances | Risques | Prio |
|---|---|---|---|---|---|---|---|---|
| **TR1** | **Fiche territoire** (commune ou circonscription) : une page qui réunit élections, économie, élus et équipements, avec URL partageable (`st.query_params`) | N | Transforme 4 modules juxtaposés en un outil d'analyse de territoire ; point d'arrivée naturel du clic carte | Base | M | EL4 | Aucun (réutilise l'existant) | **P1** |
| **TR2** | **Rapports PDF LaTeX** (fiche commune ou circonscription, rapport de scrutin) | R | Livrable professionnel imprimable ; les dépendances Jinja2 et Tectonic et la skill `latex-rapport-fr` existent déjà sans usage | Base | M-L | TR1 (même contenu) ; image Docker avec Tectonic (autre agent) ; export des figures (voir V9) | Figures : Kaleido exige Chrome, matplotlib est plus simple pour le PDF ; charte orthotypographique DILA | P2 |
| **TR3** | **Export des données affichées** (CSV/Parquet avec mention de la source et de la licence) | N | Réutilisabilité, transparence | — | S | — | Respect de la licence Etalab : attribution dans le fichier | **P1** |
| **TR4** | **Page « Sources et méthode » générée automatiquement** à partir de `source_bloc`, des ADR et des circulaires | N | Rend visible la rigueur du projet (argument principal de crédibilité) | Base + docs | S | Corrections de nuances | — | **P1** |
| **TR5** | **Couche d'accès aux données unique** (module Python `ministere_de_l_info.data`, et non une API REST, conformément à l'ADR-0002) | N (« API interne ») | Une seule façon de lire la base : tests plus simples, pages plus courtes, réutilisation pour les PDF | — | M | QA1 | Refactorisation touchant beaucoup de fichiers : à faire sous couverture de tests | P2 |
| **TR6** | **Extension du périmètre géographique** (région voisine, puis France entière) pour Élections et Économie | R | Comparaisons HdF vs autres régions ; intérêt national | Mêmes sources (nationales) | L | QA1-QA2 ; performance des cartes (voir §4.1) | Volume de base ×5 à ×10 (ordre de grandeur non mesuré) ; Folium lent au-delà de quelques milliers de polygones ; lacunes de source ailleurs (cf. Nord 2008) à rechercher ; mapping des nuances à revalider hors HdF | Scénario B |
| **TR7** | **Veille automatique des sources** : tâche planifiée qui interroge l'API data.gouv (date de dernière modification des jeux utilisés) et signale les nouveautés | N | Évite de découvrir tard un nouveau millésime ou une panne de source (cas NosDéputés et CLAIR) | ✅ API data.gouv `/api/1/datasets/{id}` | S | — | — | P2 |
| **TR8** | **Projections démographiques** (INSEE Omphale) | N | Contexte prospectif | ❓ non vérifié | M | — | Projections ≠ prévisions ; scénarios multiples | P3 |

---

## 4. Veille technique ciblée

### 4.1 Clic sur la carte → détail : trois options

| Option | Principe | Avantages | Inconvénients | Verdict proposé |
|---|---|---|---|---|
| **A. Folium + `st_folium` (actuel)** | Activer `returned_objects=["last_object_clicked"]` (aujourd'hui `[]` partout), récupérer latitude et longitude, puis `ST_Contains(geom, point)` dans DuckDB pour identifier la commune. Ou tester `last_active_drawing`, qui peut renvoyer la *feature* GeoJSON cliquée | Aucun changement d'outil ; ne dépend pas du retour des propriétés ; robuste | Un aller-retour serveur par clic ; Folium lent sur les grandes géométries | **Essai (S) en premier** : la décision D2 a été prise sur l'hypothèse « pas de propriétés », que la voie point → `ST_Contains` contourne |
| **B. `st.pydeck_chart(on_select="rerun", selection_mode=...)`** | Sélection native Streamlit depuis la 1.39 (oct. 2024) ; renvoie les objets sélectionnés ; sélection multiple possible | Natif, rapide (WebGL), adapté à des dizaines de milliers de polygones, donc au scénario B | Changement de bibliothèque de cartes (ADR) ; fond de carte et légende à refaire ; chaque couche doit avoir un `id` | **Option cible si extension nationale** |
| **C. Plotly `choropleth_map` + `st.plotly_chart(on_select=...)`** | Même bibliothèque que les graphiques | Cohérence visuelle | Sélection documentée surtout pour les points (clic, rectangle, lasso) ; comportement sur les polygones de choroplèthe **non confirmé** | À tester seulement si A échoue |

Sources : [st.pydeck_chart](https://docs.streamlit.io/develop/api-reference/charts/st.pydeck_chart) · [Streamlit 1.39.0](https://discuss.streamlit.io/t/version-1-39-0/82615) · [issue « Selection events for maps » #8653](https://github.com/streamlit/streamlit/issues/8653) · [streamlit-folium](https://github.com/randyzwitch/streamlit-folium) · [st.plotly_chart](https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart).

### 4.2 Streamlit (verrouillé en 1.57.0, dernière version 1.64.0)

Fonctionnalités utiles pour le projet :
- **`@st.fragment`** (et `parallel=True`, mai 2026) : relancer uniquement la carte ou le tableau quand un sélecteur change, et non toute la page. Gain direct sur les pages Élections et Économie, qui rechargent tout à chaque clic.
- **`st.navigation` / `st.Page`** : déjà adoptés (design system). `st.App` offre en plus une gestion personnalisée des erreurs de script.
- **`st.query_params`** : URL partageables vers une commune (TR1).
- **Chargement paresseux de `st.dataframe`** (1.61) : utile pour la liste des 4 065 élus et les tableaux par bureau de vote.
- **Rafraîchissement du cache en arrière-plan** (1.61) : pertinent pour les requêtes lourdes.
- **`on_change="ignore"`** sur `selectbox` (1.64) : évite des relances inutiles.

Points de vigilance pour la montée de version : `st.cache` retiré en 1.62 (non utilisé dans le projet, vérifié) ; `use_column_width` retiré en 1.61 (non utilisé) ; **`use_container_width` déprécié**, 18 occurrences à remplacer par `width="stretch"` ; revérifier les sélecteurs CSS `data-testid` de `custom.css` (ils changent d'une version à l'autre : leçon du design system).

Sources : [Notes de version 2026](https://docs.streamlit.io/develop/quick-reference/release-notes/2026) · [1.64.0](https://discuss.streamlit.io/t/version-1-64-0/122545) · [1.63.0](https://discuss.streamlit.io/t/version-1-63-0/122544) · [1.62.0](https://newreleases.io/project/github/streamlit/streamlit/release/1.62.0) · [PyPI streamlit](https://pypi.org/project/streamlit/).

### 4.3 DuckDB (verrouillé en 1.5.2, dernière version 1.5.4)

- `GEOMETRY` intégré au cœur (1.5.0, 09/03/2026) et stocké en WKB ; les statistiques de boîte englobante permettent d'ignorer des blocs entiers lors d'un filtre spatial. Bénéfice direct pour l'option A du clic carte (`ST_Contains`) et pour une éventuelle extension nationale.
- Les fonctions `ST_*` restent vraisemblablement dans l'extension `spatial` (à vérifier) : le téléchargement de l'extension reste un point de fragilité en CI et en cloud (bloqué dans ce conteneur).
- **DuckDB 2.0 annoncée** : prévoir, avant toute montée, un test de réouverture de la base distribuée et documenter la procédure `EXPORT DATABASE` / `IMPORT DATABASE`.

Sources : [Annonce 1.5.0](https://duckdb.org/2026/03/09/announcing-duckdb-150) · [Annonce 1.5.4](https://duckdb.org/2026/06/17/announcing-duckdb-154) · [Spatialists](https://spatialists.ch/posts/2026/03/22-duckdb-15-with-spatial-updates/) · [endoflife.date](https://endoflife.date/duckdb).

### 4.4 Génération de PDF (Tectonic + Jinja2)

- La chaîne est prête mais **jamais utilisée** : Jinja2 et Tectonic (0.16.9 dans le Dockerfile racine, absent de l'image GHCR selon l'état des lieux), skill `latex-rapport-fr`.
- Figures : Kaleido ≥ 1.0 exige Chrome. Deux options : (1) matplotlib pour les figures de rapport (autorisé par CLAUDE.md, pas de navigateur) ; (2) Kaleido + Chrome dans l'image (+ environ 300 Mo, estimation non mesurée). **Recommandation : matplotlib** pour les PDF, Plotly pour le web.
- Cartes : exporter depuis GeoPandas + matplotlib (Lambert-93, EPSG:2154), plus propre à l'impression qu'une capture de Folium.

### 4.5 Autres outils repérés

- **PyEI** (inférence écologique) : seule bibliothèque Python sérieuse pour EL8 ; dépendances lourdes (PyMC/JAX) : groupe `uv` optionnel si retenu.
- **ty** (Astral, bêta) et **pyright** : voir QA4.
- **respx** (simulation des appels `httpx`) : voir QA3.

---

## 5. Qualité et industrialisation

| ID | Action | Pourquoi | Effort | Prio |
|---|---|---|---|---|
| **QA1** | **Centraliser la configuration** (`pydantic-settings`, variable `MINISTERE_DB_PATH`). Aujourd'hui le chemin de la base est codé en dur dans `etl/_common.py`, `viz/elections_queries.py`, `viz/economie_queries.py`, `viz/legislatif_queries.py` et répété dans 5 fichiers de test ; aucune classe `BaseSettings` n'existe alors que la stack l'impose | Prérequis pour pointer tests et application vers une base échantillon | S | **P1** |
| **QA2** | **Base de test échantillon commitable (< 5 Mo)**. Script `scripts/build_test_fixture.py` qui extrait de la base complète : 1 département HdF (Somme, 80 : taille moyenne, sans la lacune Nord 2008) ou une seule circonscription ; 2 tours par type de scrutin ; géométries très simplifiées ; sous-ensembles `leg_elus` et économie. **Format recommandé** : `EXPORT DATABASE … (FORMAT parquet)`, reconstruit en base DuckDB au démarrage des tests (`conftest.py`), plutôt qu'un fichier `.duckdb` binaire (le format de fichier peut changer avec DuckDB 2.0 ; le Parquet est stable et lisible dans un diff). Ensuite, retirer progressivement les exclusions de couverture de `pyproject.toml` | Aujourd'hui 342 tests sont ignorés hors du Mac ; la CI mesure environ 60 % au lieu d'environ 75 % ; le travail en cloud est aveugle | M | **P1** |
| **QA3** | **Tests hermétiques** : marqueur `@pytest.mark.network` (exclu par défaut) pour les tests qui appellent IGN, INSEE ou data.gouv ; réponses enregistrées avec `respx` (httpx) ou fichiers d'exemple dans `tests/fixtures/` ; un job CI **nocturne** séparé exécute les tests réseau (et sert de sonde de santé des sources, cf. TR7) | Les échecs actuels en cloud viennent du réseau, pas du code | S-M | **P1** |
| **QA4** | **Typage vérifié** : pyright en mode `basic` (stable) ou ty (Astral, bêta), d'abord **non bloquant** en CI, puis bloquant module par module (`_blocs_politiques.py`, `viz/`, `etl/`) | CLAUDE.md impose « type hints partout » mais rien ne le vérifie | S (mise en place) + M (correction) | P2 |
| **QA5** | **Contrôles de qualité des données après ETL** : assertions SQL (somme des voix = exprimés, inscrits ≥ votants, nombre de communes HdF, aucun bloc NULL hors codes documentés) dans un script `scripts/check_data.py` et un rapport | Protège la crédibilité : une erreur de données est plus grave qu'un bug d'affichage | S-M | **P1** |
| **QA6** | **CI sur toutes les branches et PR** (aujourd'hui `main` seulement) + **Dependabot/Renovate** pour être prévenu des nouvelles versions (Streamlit, DuckDB) | Sans cela, pas de CI sur les branches de travail des agents | S | P1 (à coordonner avec l'agent Docker/CI s'il existe) |
| **QA7** | **Montée de version contrôlée** Streamlit 1.57 → 1.6x et DuckDB 1.5.2 → 1.5.4 : remplacement de `use_container_width`, AppTest de toutes les pages, vérification visuelle des sélecteurs CSS | Correctifs de sécurité et nouveautés (§4.2) | S-M | P1 (après QA2) |
| **QA8** | **Tests d'interface AppTest** sur toutes les pages avec la base échantillon (aujourd'hui marqués `slow` et dépendants de la vraie base) | Détecte les régressions UI lors des montées de version | M | P2 |

---

## 6. Tableau de synthèse priorisé

| Prio | ID | Piste | Effort | Valeur |
|---|---|---|---|---|
| **P1** | LG4 | Rafraîchir le Sénat après les sénatoriales du 27/09 | S | Élevée (exactitude) |
| **P1** | QA1 | Configuration centralisée (`pydantic-settings`) | S | Élevée (socle) |
| **P1** | QA2 | Base de test échantillon (Parquet < 5 Mo) | M | Élevée (socle) |
| **P1** | QA3 | Tests hermétiques + job réseau nocturne | S-M | Moyenne |
| **P1** | QA5 | Contrôles qualité des données post-ETL | S-M | Élevée |
| **P1** | QA6 | CI sur branches + Dependabot | S | Moyenne |
| **P1** | QA7 | Montée Streamlit / DuckDB | S-M | Moyenne |
| **P1** | EL4 | Clic carte → détail (essai puis implémentation) | S + M | Élevée |
| **P1** | TR1 | Fiche territoire (commune / circonscription) | M | Très élevée |
| **P1** | EL5 | Indicateurs dérivés (volatilité, bascules, abstention différentielle) | S-M | Élevée |
| **P1** | EL1 | Européennes 1999-2024 | M | Élevée |
| **P1** | LG1 | Croisement député × résultats de circonscription | M | Élevée |
| **P1** | EC1 | Mise à jour RP 2022 / Filosofi 2023 (rupture de série) | M | Élevée |
| **P1** | GE3 | Grille de densité / aires d'attraction des villes | S | Élevée (pour les croisements) |
| **P1** | TR3 | Export CSV/Parquet des données affichées | S | Moyenne |
| **P1** | TR4 | Page « Sources et méthode » automatique | S | Élevée (crédibilité) |
| P2 | EC4 | BPE équipements × vote | M | Élevée |
| P2 | LG6 | RNE élus locaux | M | Élevée |
| P2 | LG2 | Votes nominatifs AN | L | Très élevée |
| P2 | LG3 | Historique des mandats (AMO30) | M | Moyenne |
| P2 | LG8 | Législatif × économie | M | Moyenne |
| P2 | EL2 | Régionales | M | Moyenne |
| P2 | EL6 | Contours des bureaux de vote | M | Élevée |
| P2 | EL7 | Liaison IRIS ↔ BV | M | Élevée |
| P2 | EL10 | Participation fine | S | Moyenne |
| P2 | EC2 | QPV 2024 | S-M | Moyenne |
| P2 | GE1 | PCAP | S | Faible à moyenne |
| P2 | TR2 | Rapports PDF LaTeX | M-L | Élevée |
| P2 | TR5 | Couche d'accès aux données unique | M | Moyenne (technique) |
| P2 | TR7 | Veille automatique des sources | S | Moyenne |
| P2 | QA4 | Typage (pyright ou ty) | S + M | Moyenne |
| P2 | QA8 | AppTest sur base échantillon | M | Moyenne |
| P3 | EL3 | Départementales / cantonales | L | Moyenne |
| P3 | EL8 | Transferts de voix (inférence écologique) | L | Élevée mais risquée |
| P3 | EL9 | Simulations de mode de scrutin | M | Moyenne |
| P3 | LG5 | Scrutins publics du Sénat | L | Moyenne |
| P3 | LG7 | HATVP | S-L | Moyenne (sensible) |
| P3 | EC3 | FRR (ex-ZRR) | S | Faible à moyenne |
| P3 | EC5 | Sirene géolocalisé | M-L | Faible à moyenne |
| P3 | GE2, GE4, GE5 | Mayotte, EPT, cantons | S | Faible (hors HdF) |
| P3 | TR8 | Projections démographiques | M | Faible |
| Scénario B | TR6 | Extension géographique | L | Élevée mais coûteuse |

---

## 7. Trois scénarios de feuille de route

Les durées sont exprimées en **sessions de travail** (une session = une demi-journée à une journée de supervision). Ce sont des ordres de grandeur.

### Scénario A — « Consolider » (environ 6 à 9 sessions)

Objectif : un outil exact, testable partout, à jour et à la pile technique récente, avant toute extension.

1. LG4 : Sénat post-27/09 (dès que les groupes sont constitués).
2. QA1 → QA2 → QA3 → QA6 : configuration, base échantillon, tests hermétiques, CI sur branches.
3. QA5 : contrôles de données (à lancer après les corrections de nuances de l'autre agent).
4. QA7 : montée Streamlit / DuckDB.
5. EC1 : millésimes RP 2022 et Filosofi 2023, avec la rupture affichée.
6. TR4 + TR3 : page « Sources et méthode », exports.

**Résultat** : pas de nouveauté spectaculaire, mais une base saine. Chaque piste suivante coûte moins cher et devient vérifiable en cloud. **Risque** : lassitude (peu de nouveautés visibles).

### Scénario B — « Élargir le périmètre géographique » (environ 12 à 20 sessions, après A)

Objectif : comparer les HdF au reste de la France.

1. Décision et ADR : quelle extension (région voisine témoin, par exemple Grand Est ; ou France entière d'un coup ; ou France entière au niveau département/circonscription seulement, en gardant la commune et le BV pour les HdF).
2. Passage des cartes à pydeck (option B du §4.1), sans quoi Folium ne tiendra pas 35 000 communes.
3. Rechargement ETL national, mesure de la taille de la base et du temps de chargement, revue des lacunes de source hors HdF.
4. Économie nationale (même dataset OLAP : l'ETL filtre aujourd'hui HdF).

**Résultat** : comparaisons interrégionales, audience potentielle plus large. **Risques** : taille de base (distribution par GitHub Release à revoir), performance, revalidation méthodologique sur des territoires moins connus de Mathias ; décision difficile à inverser.

### Scénario C — « Approfondir l'analyse » (environ 10 à 15 sessions, après A ou en partie en parallèle)

Objectif : faire du projet un outil d'analyse de territoire, pas seulement une collection de cartes, en restant sur les HdF.

1. EL4 + TR1 : clic carte → fiche territoire.
2. EL5 + GE3 : indicateurs dérivés et typologie urbain/rural.
3. EL1 : européennes.
4. LG1 : député × circonscription.
5. EC4 + LG6 : équipements (BPE) et élus locaux (RNE).
6. TR2 : fiche territoire en PDF (LaTeX).
7. En option, plus tard : LG2 (votes nominatifs AN), EL6/EL7 (bureaux de vote et IRIS).

**Résultat** : forte valeur éditoriale, entièrement sur les forces actuelles (méthode sourcée, HdF bien connus). **Risque** : sans A, les nouveautés s'empilent sur des tests qui ne tournent que sur le Mac.

**Recommandation de l'agent** : **A puis C**. B éventuellement plus tard, sous une forme limitée (niveau département/circonscription), ce qui donne des comparaisons nationales sans multiplier la base.

---

## 8. Arbitrages à demander à Mathias (questions fermées)

**Orientation**
1. Adoptez-vous l'enchaînement « A (consolider) puis C (approfondir) » comme feuille de route des prochaines phases ? **Oui / Non**
2. Le périmètre Élections et Économie reste-t-il limité aux Hauts-de-France pour les 6 prochains mois ? **Oui / Non**
3. Si une extension est envisagée plus tard, préférez-vous : **(a)** France entière au niveau département/circonscription seulement, **(b)** une région témoin complète, **(c)** France entière à tous les niveaux ?

**Méthodologie**

4. Filosofi : acceptez-vous d'afficher 2023 (« Filosofi 2 ») **à côté** de 2017-2021, avec une rupture de série visible (pas de ligne continue, mention explicite) ? **Oui / Non**
5. Pour les nouveaux groupes du Sénat issus du 27/09, faut-il un ADR « groupes parlementaires → blocs » avant le rechargement ? **Oui / Non**
6. Autorisez-vous des **estimations statistiques** (transferts de voix par inférence écologique), présentées comme estimations avec marges d'incertitude ? **Oui / Non / Plus tard**
7. HATVP et RNE : limitez-vous l'affichage aux métadonnées publiques non sensibles (pas de date de naissance, pas de contenu de déclarations) ? **Oui / Non**

**Technique**

8. Validez-vous l'essai (S) du clic carte avec Folium (`last_object_clicked` + `ST_Contains`) avant d'envisager pydeck ? **Oui / Non**
9. Base de test : acceptez-vous de committer un échantillon d'environ 1 département HdF exporté en Parquet (< 5 Mo, données publiques) ? **Oui / Non** ; département : **Somme (80) / autre**
10. Montée de version Streamlit 1.57 → 1.64 et DuckDB 1.5.2 → 1.5.4, une fois la base échantillon en place ? **Oui / Non**
11. Typage : **pyright** (stable) ou **ty** (Astral, bêta, même éditeur que uv et ruff) ?
12. Figures des rapports PDF : **matplotlib** (simple, sans navigateur) ou **Plotly + Kaleido** (identique au web, mais Chrome requis dans l'image) ?
13. Faut-il mettre en place une tâche planifiée hebdomadaire de veille des sources data.gouv (TR7) ? **Oui / Non**

**Premier pas concret**

14. La prochaine session peut-elle commencer par LG4 (Sénat) + QA1 (configuration centralisée), deux tâches courtes, indépendantes des autres agents ? **Oui / Non**

---

## 9. Sources consultées (recherche web du 24/09/2026)

**Données**
- [Données des élections agrégées](https://www.data.gouv.fr/datasets/donnees-des-elections-agregees) · [Élections municipales 2026, T1](https://www.data.gouv.fr/datasets/elections-municipales-2026-resultats-du-premier-tour)
- [Proposition de contours des bureaux de vote](https://www.data.gouv.fr/datasets/proposition-de-contours-des-bureaux-de-vote) · [BV et adresses](https://www.data.gouv.fr/datasets/bureaux-de-vote-et-adresses-de-leurs-electeurs) · [Liaison IRIS/BV 2024](https://www.data.gouv.fr/datasets/liaison-iris-bureaux-de-vote-de-2024) · [Bureaux de vote 2026](https://www.data.gouv.fr/datasets/bureaux-de-vote-2026)
- [RNE élus locaux](https://www.data.gouv.fr/datasets/donnees-du-repertoire-national-des-elus-locaux-municipaux-communautaires-epci-departementaux-regionaux) · [RNE](https://www.data.gouv.fr/datasets/repertoire-national-des-elus-1) · [RNE députés et sénateurs](https://www.data.gouv.fr/datasets/repertoire-national-des-elus-deputes-et-senateurs)
- [AN : votes](https://data.assemblee-nationale.fr/travaux-parlementaires/votes) · [AN : archives 15e, scrutins](https://data.assemblee-nationale.fr/archives-anterieures/archives-15e/scrutins) · [AN : archives 16e](https://data.assemblee-nationale.fr/archives-16e) · [NosParlementaires 17e](https://www.data.gouv.fr/datasets/votes-et-activite-des-parlementaires-francais-17e-legislature-nosparlementaires)
- [Datan : historique des députés](https://www.data.gouv.fr/datasets/historique-des-deputes-de-lassemblee-nationale-depuis-2002-informations-et-statistiques)
- [data.senat.fr](https://data.senat.fr/) · [Notice Dosleg](https://data.senat.fr/aide/travaux-legislatifs-base-dosleg/) · [Sénatoriales 2026](https://senatoriales2026.senat.fr/)
- [HATVP open data](https://www.hatvp.fr/open-data/) · [Format liste.csv](https://www.hatvp.fr/livraison/opendata/open-data.pdf)
- [INSEE BPE 2025](https://www.insee.fr/fr/statistiques/8217537) · [data.gouv BPE](https://www.data.gouv.fr/datasets/base-permanente-des-equipements-1)
- [QPV 2024](https://www.data.gouv.fr/datasets/carte-des-quartiers-prioritaires-de-la-politique-ville-2024) · [QPV communes 2024](https://www.data.gouv.fr/datasets/qpv-communes-2024)
- [Sirene géolocalisé (études statistiques)](https://www.data.gouv.fr/datasets/geolocalisation-des-etablissements-du-repertoire-sirene-pour-les-etudes-statistiques) · [Sirene 2024 GeoParquet](https://www.data.gouv.fr/datasets/base-sirene-des-etablissements-2024-geolocalisee-geoparquet)
- [Filosofi 2023](https://www.insee.fr/fr/statistiques/8984752?sommaire=8984758) · [Revenus 2022, non-production de Filosofi 2022](https://www.insee.fr/fr/statistiques/8278909) · [Populations de référence 2023](https://www.insee.fr/fr/statistiques/8680726) · [Mayotte 2026](https://www.insee.fr/fr/statistiques/9021428) · [Résultats du RP](https://www.insee.fr/fr/information/2008354)
- [FRR (AMF)](https://www.amf.asso.fr/documents-france-ruralites-revitalisation-nouveau-dispositif-qui-remplacera-les-zrr-au-1er-juillet-2024/42098)

**Technique**
- [Streamlit : notes de version 2026](https://docs.streamlit.io/develop/quick-reference/release-notes/2026) · [1.64.0](https://discuss.streamlit.io/t/version-1-64-0/122545) · [1.62.0](https://newreleases.io/project/github/streamlit/streamlit/release/1.62.0) · [st.pydeck_chart](https://docs.streamlit.io/develop/api-reference/charts/st.pydeck_chart) · [1.39.0 (sélection pydeck)](https://discuss.streamlit.io/t/version-1-39-0/82615) · [st.plotly_chart](https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart) · [issue #8653](https://github.com/streamlit/streamlit/issues/8653)
- [streamlit-folium](https://github.com/randyzwitch/streamlit-folium)
- [DuckDB 1.5.0](https://duckdb.org/2026/03/09/announcing-duckdb-150) · [DuckDB 1.5.4](https://duckdb.org/2026/06/17/announcing-duckdb-154) · [endoflife.date DuckDB](https://endoflife.date/duckdb)
- [Tectonic](https://tectonic-typesetting.github.io/en-US/) · [Kaleido](https://github.com/plotly/Kaleido) · [Plotly static export](https://plotly.com/python/static-image-export/)
- [ty (Astral)](https://astral.sh/blog/ty) · [PyEI](https://github.com/mggg/ecological-inference)
