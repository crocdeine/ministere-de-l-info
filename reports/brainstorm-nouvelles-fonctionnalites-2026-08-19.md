# Brainstorm — Nouvelles sources, benchmark outils, croisements inexploités

**Date** : 2026-08-19
**Nature** : brainstorm de cadrage, aucune implémentation. Décisions à valider par Mathias.
**Méthode** : recherches web réelles (WebSearch/WebFetch) le 2026-08-19, croisées avec l'état du repo (`CLAUDE.md`, `docs/data-sources.md`, `docs/schema-elections.md`, `reports/exploration-legislatif-sources.md`, `reports/exploration-legislatif-national-datagouv.md`).

**Note de méthode** : deux rapports d'exploration existants (`exploration-legislatif-sources.md`, `exploration-legislatif-national-datagouv.md`, session Phase F) avaient déjà investigué une partie de l'axe 1 côté Législatif (AN, Sénat, NosDéputés). Ce brainstorm reprend leurs conclusions sans les refaire, et les complète sur HATVP, Eurostat, OSM, RNE, PISTE.

---

## Axe 1 — Nouvelles sources de données ouvertes françaises

### Tableau de synthèse

| Source | Apport pour le projet | Difficulté d'intégration | Statut |
|---|---|---|---|
| HATVP open-data (déclarations patrimoine/intérêts) | Transparence patrimoniale des élus, module "Élus" enrichi | Moyenne | Jamais explorée dans le repo |
| Scrutins publics AN (votes nominatifs) | Comble la limitation connue "XML brut non parsé" — vote par vote, cohésion de groupe | Moyenne à haute | Déjà investiguée (Phase F), non implémentée |
| data.senat.fr — Dosleg / Ameli (au-delà du CSV élus) | Scores d'activité Sénat (actuellement absents, limitation connue) | Haute | Non explorée pour l'activité (le CSV élus l'est) |
| Eurostat — indicateurs additionnels | Pauvreté régionale NUTS2, comparaison UE plus fine | Faible à moyenne | Pipeline Eurostat déjà en place (economie_contexte) |
| INSEE — BPE (Base Permanente des Équipements) | Écoles, santé, commerces — affine les déserts médicaux et la géographie | Moyenne | Non utilisée |
| INSEE Sirene | Créations/fermetures d'établissements en continu | Moyenne (OAuth2) | "Prévue" dans CLAUDE.md, jamais commencée |
| PISTE / Légifrance (LEGI, DOLE, JORF) | Suivi du parcours législatif complet, lien texte↔vote | Haute | "Prévue" dans CLAUDE.md, jamais commencée |
| RNE — élus locaux (data.gouv.fr) | Élus municipaux/départementaux/régionaux/EPCI en exercice, cumul de mandats | Faible à moyenne | "Prévue" dans CLAUDE.md, jamais commencée |
| OSM/Overpass — bureaux de vote géolocalisés | Carto fine des BV, mais couverture participative inégale | Faible (technique) / risque qualité | Jamais explorée |
| OSM/Overpass — équipements publics | Enrichit géographie et déserts médicaux | Faible / risque qualité | Jamais explorée |
| data.gouv.fr — élus municipaux sortants 2026 | Base directe pour croisement réélection | Faible | Jamais explorée |

### Détail par source

#### HATVP open-data (déclarations de patrimoine et d'intérêts)

URL : [hatvp.fr/open-data](https://www.hatvp.fr/open-data/). Deux flux publics sous licence ouverte Etalab :
- [`liste.csv`](https://www.hatvp.fr/livraison/opendata/liste.csv) — liste des déclarations et appréciations publiées
- [`declarations.xml`](https://www.hatvp.fr/livraison/merge/declarations.xml) — contenu structuré de toutes les déclarations publiées en open data

Une [notice technique](https://www.hatvp.fr/wordpress/wp-content/uploads/2017/07/notice-open-data.pdf) et un schéma XLSX de structure XML sont fournis. Les données sont aussi répliquées sur data.gouv.fr (organisation HATVP).

**Apport** : déclarations de patrimoine et d'intérêts en début/fin de mandat pour les responsables publics (parlementaires, exécutifs locaux au-dessus d'un seuil, ministres). Permettrait un onglet "transparence" dans le module Législatif ou un nouveau module "Élus", avec ventilation du patrimoine par type d'actif et évolution entre déclarations.

**Difficulté** : moyenne. Le format XML global est volumineux (toutes les déclarations, tous mandats confondus) et il n'existe pas de clé stable directe vers les identifiants AN/Sénat déjà utilisés dans `leg_elus` — un rapprochement nom + circonscription + date sera nécessaire, avec les mêmes risques d'homonymie que rencontrés sur les nuances électorales. Sujet éditorialement sensible (données patrimoniales nominatives) : à cadrer avec Mathias avant tout développement (portée, présentation, disclaimers).

#### Scrutins publics de l'Assemblée nationale — votes nominatifs

URL : [data.assemblee-nationale.fr/travaux-parlementaires/votes](https://data.assemblee-nationale.fr/travaux-parlementaires/votes), fichier `Scrutins.xml.zip` / `Scrutins.json.zip` par législature (archives 15e, 16e, 17e disponibles séparément).

**Apport** : position de vote individuelle de chaque député sur chaque scrutin solennel/public — la donnée brute qui manque aujourd'hui derrière les scores agrégés Datan. Débloquerait : taux de dissidence réel par député, cohésion de groupe calculée en interne (au lieu de dépendre des scores pré-calculés Datan), recherche "comment mon député a-t-il voté sur tel texte".

**Difficulté** : moyenne à haute — confirmée par le rapport `reports/exploration-legislatif-national-datagouv.md` (session Phase F) : *"il n'existe actuellement aucune source agrégée ou tabulaire simple (CSV) décrivant qui a voté quoi"*. Il faut télécharger et parser les ZIP XML/JSON bruts par législature, normaliser les codes Pour/Contre/Abstention/Absent, et les rattacher aux `leg_elus`. Faisabilité technique confirmée (format documenté), mais volume et complexité de modélisation réels (chaque scrutin a une structure imbriquée acteurs/groupes/mandats).

#### data.senat.fr — au-delà du CSV déjà utilisé

Le module Législatif utilise déjà le CSV officiel des sénateurs. Deux bases supplémentaires existent :
- [DOSLEG](https://data.senat.fr/dosleg/) — dossiers législatifs depuis octobre 1977
- [AMELI](https://data.senat.fr/ameli/) — amendements déposés en commission (depuis oct. 2010) et en séance (depuis oct. 2001)

Distribution en deux formes : dump complet PostgreSQL 8.4, ou extraits CSV par texte (à la pièce, pas d'agrégat global téléchargeable en un clic).

**Apport** : permettrait de construire un équivalent des scores d'activité Datan pour le Sénat (actuellement absent — limitation documentée dans CLAUDE.md : *"pas de scores Sénat, Datan = AN uniquement"*).

**Difficulté** : haute. Le dump PostgreSQL complet est le seul moyen d'obtenir une vue exhaustive sans parcourir texte par texte ; format PostgreSQL 8.4 à importer/convertir avant chargement DuckDB. Pas d'API REST légère comme NosDéputés côté AN.

#### Eurostat — indicateurs additionnels

Le pipeline `economie_contexte` (Phase E++) charge déjà chômage BIT et PIB/habitant par NUTS2. Pistes non exploitées identifiées : taux de risque de pauvreté régional (at-risk-of-poverty rate, niveau NUTS2), indicateurs de Gini régionaux, dépenses publiques par région. Existe aussi un [découpage NUTS-2 des régions européennes sur data.gouv.fr](https://www.data.gouv.fr/datasets/decoupage-nuts-2-des-regions-europeennes) pour la cartographie comparative.

**Apport** : enrichir la comparaison HdF vs France déjà en place avec d'autres dimensions socio-économiques européennes, sans changement d'architecture (même pipeline).

**Difficulté** : faible à moyenne — le connecteur Eurostat existe déjà, il s'agit d'ajouter des séries.

#### INSEE — Base Permanente des Équipements (BPE)

Non explorée jusqu'ici. Recense la localisation des équipements et services (écoles, santé, commerces, services publics) à l'échelle communale/infra-communale.

**Apport** : affinerait la détection des déserts médicaux (actuellement basée sur DREES/CNAF) avec une dimension "accès aux équipements" plus large que le seul secteur médical, et enrichirait le module Géographie.

**Difficulté** : moyenne — format INSEE standard (probablement CSV/Parquet), mais nouveau jeu de données à cadrer et fusionner avec le référentiel communal existant.

#### INSEE Sirene

Toujours listée en "sources prévues (modules futurs)" dans `docs/data-sources.md` mais jamais commencée.

**Apport** : suivi des créations/fermetures d'établissements en continu (complément dynamique aux données URSSAF/Filosofi déjà statiques et à millésime annuel), utile pour affiner la Désindustrialisation.

**Difficulté** : moyenne — nécessite OAuth2 (`portail-api.insee.fr`), déjà anticipé dans le projet (`.env.example` prévu pour ce cas).

#### PISTE / Légifrance (LEGI, DOLE, JORF)

URL : [legifrance.gouv.fr/contenu/pied-de-page/open-data-et-api](https://www.legifrance.gouv.fr/contenu/pied-de-page/open-data-et-api). Bases DILA : LEGI (codes/lois consolidés), DOLE (dossiers législatifs), JORF, etc. Accès API stable depuis avril 2023 via portail PISTE (OAuth2, inscription + acceptation CGU). Alternative : jeux CSV/JSON bruts de ces mêmes bases sur data.gouv.fr ([LEGI](https://www.data.gouv.fr/datasets/legi-codes-lois-et-reglements-consolides), [DOLE](https://www.data.gouv.fr/datasets/dole-les-dossiers-legislatifs)) sans passer par l'API.

**Apport** : suivi du parcours d'un texte de loi (dépôt → commission → séance → promulgation), possibilité de relier un texte à ses votes nominatifs (si la source précédente est intégrée) — équivalent interne d'une fonctionnalité "vie d'une loi" (voir benchmark LaFabriqueDeLaLoi ci-dessous).

**Difficulté** : haute. DTD complexes, volumes importants, et la valeur réelle du texte de loi seul est limitée sans le croiser aux votes — projet à mener après (et non avant) l'intégration des scrutins nominatifs.

#### RNE — Répertoire national des élus locaux

URL type : [data.gouv.fr — Données du RNE : Municipaux, Communautaires (EPCI), Départementaux, Régionaux](https://www.data.gouv.fr/datasets/donnees-du-repertoire-national-des-elus-locaux-municipaux-communautaires-epci-departementaux-regionaux). Mise à jour trimestrielle, alimenté par les préfectures. Existe aussi un dataset RNE séparé pour [députés et sénateurs](https://www.data.gouv.fr/datasets/repertoire-national-des-elus-deputes-et-senateurs).

**Apport** : le projet a aujourd'hui les *résultats* des élections municipales (module Élections) mais pas la liste des *élus en exercice* (maires, conseillers municipaux/départementaux/régionaux/EPCI actuels), ni les cumuls de mandats. Le RNE comble ce trou et permettrait un croisement direct avec le module Législatif (élu national qui est aussi élu local).

**Difficulté** : faible à moyenne — CSV direct data.gouv.fr, mais volumineux (plusieurs centaines de milliers de lignes au national ; filtrage HdF réduirait fortement le volume, cohérent avec le filtrage déjà pratiqué en Élections/Économie).

#### OSM/Overpass — bureaux de vote et équipements publics

Tag officiel [`amenity=polling_station`](https://wiki.openstreetmap.org/wiki/FR:Tag:amenity=polling_station). Overpass a une instance française : `overpass.openstreetmap.fr/api/interpreter`.

**Apport** : géolocalisation fine des bureaux de vote (complément visuel au drill-down BV existant) et, plus largement, équipements publics (écoles, gendarmeries, mairies, centres de santé) pour enrichir la carto et les croisements avec les déserts médicaux/services publics.

**Difficulté** : techniquement faible (API simple, pas d'auth), mais couverture participative très inégale selon les communes en France — fil de discussion OSM-talk-fr identifié confirmant que le tagging des bureaux de vote n'est pas systématique. À valider empiriquement sur un échantillon HdF avant tout engagement, car un jeu de données incomplet donnerait une fausse impression d'exhaustivité sur une carte.

#### data.gouv.fr — élus municipaux sortants 2026

Dataset repéré : [Elections municipales 2026 — Maires et conseillers municipaux sortants](https://www.data.gouv.fr/datasets/elections-municipales-2026-maires-et-conseillers-municipaux-sortants). Non vérifié en détail (existence confirmée par le titre du jeu, contenu exact à valider).

**Apport potentiel** : base directe pour un croisement "sortant réélu ou non" côté municipales, en complément du RNE.

**Difficulté** : à évaluer — source repérée mais pas encore inspectée.

---

## Axe 2 — Benchmark d'outils existants

| Outil | Fonctionnalités transposables | Pourquoi |
|---|---|---|
| NosDéputés.fr / NosSénateurs.fr (Regards Citoyens) | Fiche élu synthétique avec score de présence en commission/hémicycle ; accès données par simple suffixe `/xml`, `/json`, `/csv` | Le module Législatif a déjà des scores Datan (participation, loyauté, majorité) mais pas de mesure de présence physique en commission — NosDéputés le propose |
| Datan.fr (déjà source utilisée) | Indicateurs relatifs : cohésion interne de groupe, proximité vis-à-vis de la majorité, taux de féminisation, âge moyen ; fonctionnalité "le·la député·e explique son vote" | À vérifier si tous ces champs Datan sont déjà exploités dans l'UI actuelle (4 onglets) — certains (cohésion groupe, féminisation, âge moyen) semblent absents des indicateurs listés au CLAUDE.md |
| LaFabriqueDeLaLoi.fr (Regards Citoyens) | Timeline visuelle du parcours d'un texte, intensité de couleur = taux d'amendement par article, zoom multi-niveaux (vue macro → article → amendement) | Fonctionnalité forte mais coûteuse : suppose l'intégration DOLE + votes nominatifs (axe 1) en amont. Rendu D3.js dans l'original — à repenser en Plotly/Streamlit pur (ADR-0002 interdit le JS custom) |
| HATVP (portail) | Recherche par nom, présentation structurée d'une déclaration (patrimoine ventilé par catégorie d'actif) | Simple lien vers la fiche HATVP officielle depuis une fiche élu serait un premier pas à faible coût, avant d'envisager l'ingestion complète des données |
| Cartes électorales Le Monde / France Info / France Télévisions | Carte communale zoomable avec bascule tour 1/tour 2, recherche par commune/adresse, mode comparaison entre deux scrutins ("swing map") | Le module Élections a déjà un drill-down BV mais pas de recherche directe par nom de commune, ni de mode "évolution" généralisé (seule la vue `v_evolution_blocs_circo21`, limitée à une circonscription, existe) |
| FiveThirtyEight | Agrégation de sondages pondérée, simulateurs interactifs ("swing-o-matic") | Moins pertinent en l'état — le projet travaille sur des résultats définitifs, pas des sondages ; à ne considérer que si un module "sondages" est envisagé un jour |
| ProPublica Represent (Congress) | Comparaison côte-à-côte de deux élus, mise en avant des "votes surprenants" (qui s'écartent du parti) | Directement transposable une fois les votes nominatifs AN intégrés (axe 1) : détecter et afficher les votes dissidents d'un député HdF |
| TheyWorkForYou (UK, mySociety) | Traduction en langage clair du sens d'un vote ("a voté pour limiter X"), alertes par mot-clé/élu, page dédiée "comment il/elle a voté" | Bonne inspiration éditoriale pour rendre les votes nominatifs lisibles à un public non spécialiste, plutôt qu'un simple Pour/Contre brut |
| Ballotpedia | Page "carrière électorale" d'un candidat : historique de tous les scrutins auxquels il/elle a participé, victoires/défaites cumulées | Le projet a des données par scrutin mais pas de vue transversale "carrière" d'un candidat à travers plusieurs élections — fonctionnalité à envisager une fois un identifiant candidat stabilisé inter-scrutins |

**Remarque méthodologique** : plusieurs de ces outils (NosDéputés, LaFabriqueDeLaLoi) sont eux-mêmes des projets Regards Citoyens — cohérent avec le fait que ce collectif est déjà cité en source potentielle dans `docs/data-sources.md`. Le rapport `exploration-legislatif-sources.md` a déjà testé leur API et noté NosDéputés comme robuste, NosSénateurs comme instable (erreurs 500 fréquentes) — donc à ne pas retenir comme source de données, seulement comme inspiration fonctionnelle côté NosDéputés.

---

## Axe 3 — Croisements de données inexploités entre modules existants

Le module Économie fait déjà un croisement économie×élections (`v_croisement_eco_elections`). Autres croisements identifiés, sans nouvelle source obligatoire pour les trois premiers :

| Croisement | Question posée | Sources nécessaires | Nouveauté |
|---|---|---|---|
| Législatif × Élections | Un député sortant est-il réélu ? Quel est le taux de renouvellement par circonscription/législature ? | Données déjà en base (`leg_elus` + `resultats_candidats`) | Jointure interne, pas de nouvelle source |
| Élections × Élections (temporel, généralisé) | Volatilité électorale par commune/circo entre deux scrutins successifs (au-delà de la seule circo 21 actuellement câblée) | Données déjà en base | Généraliser `v_evolution_blocs_circo21` à toutes les circos HdF |
| Législatif × Économie | Le score de loyauté/majorité d'un député varie-t-il selon la situation économique (pauvreté, chômage, désindustrialisation) de sa circonscription ? | Données déjà en base (`leg_activite` + `economie_*`) | Jointure interne, pas de nouvelle source |
| Géographie × Économie (approfondi) | Accès aux équipements (écoles, santé) vs indicateurs de pauvreté, au-delà des seuls déserts médicaux | BPE INSEE (axe 1) | Nécessite nouvelle source |
| Législatif × RNE | Cumul de mandats : quels élus nationaux détiennent aussi un mandat local ? Carte des "cumulards" par territoire | RNE élus locaux (axe 1) | Nécessite nouvelle source |
| Législatif × HATVP | Profil patrimonial des élus vs indicateurs économiques de leur circonscription | HATVP (axe 1) | Nécessite nouvelle source, sujet sensible à cadrer |
| Élections × RNE | Sortant municipal réélu ou non (comblerait le même besoin que "élus municipaux sortants 2026" en axe 1) | RNE ou dataset dédié (axe 1) | Nécessite nouvelle source |

Les deux premiers croisements (réélection des sortants, volatilité électorale généralisée) sont réalisables **immédiatement avec les données déjà en base**, sans travail ETL supplémentaire — ce sont les candidats naturels pour une itération rapide.

---

## 3 pistes qui se démarquent

### 1. Votes nominatifs de l'Assemblée nationale (axe 1)

Comble une limitation documentée et déjà identifiée deux fois dans l'historique du projet (`CLAUDE.md`, `reports/exploration-legislatif-national-datagouv.md`). C'est la donnée qui débloque le plus de valeur en cascade : cohésion de groupe calculée en interne, détection de votes dissidents (façon ProPublica Represent), lecture en langage clair (façon TheyWorkForYou), et prérequis pour toute fonctionnalité "vie d'une loi" façon LaFabriqueDeLaLoi. Difficulté réelle mais bornée : format XML/JSON documenté, législature par législature, infra `leg_*` déjà en place pour recevoir une table `leg_votes`.

### 2. Croisement Législatif × Élections — sortant réélu ou non (axe 3)

Le meilleur rapport effort/valeur du brainstorm : aucune nouvelle source, juste une jointure entre `leg_elus` et les résultats électoraux déjà en base. Réponse à une question éditoriale forte ("qui a gagné, qui a perdu, qui a résisté") et généralisable à la volatilité électorale par circonscription (actuellement câblée sur la seule circo 21).

### 3. RNE — élus locaux et cumul de mandats (axe 1 + axe 3)

Comble un angle mort structurel : le projet a les *résultats* des scrutins municipaux/départementaux/régionaux mais pas les *élus en exercice*, ni les cumuls de mandats local/national. Source déjà anticipée dans `docs/data-sources.md` ("sources prévues"), format CSV simple, filtrage HdF cohérent avec la pratique déjà en place sur Élections et Économie. Ouvre un croisement inédit avec le module Législatif (cumul de mandats).

---

## Sources citées

- [HATVP — Open Data](https://www.hatvp.fr/open-data/)
- [HATVP — notice open data (PDF)](https://www.hatvp.fr/wordpress/wp-content/uploads/2017/07/notice-open-data.pdf)
- [data.assemblee-nationale.fr — Votes](https://data.assemblee-nationale.fr/travaux-parlementaires/votes)
- [data.senat.fr — DOSLEG](https://data.senat.fr/dosleg/)
- [data.senat.fr — AMELI](https://data.senat.fr/ameli/)
- [data.gouv.fr — RNE élus locaux](https://www.data.gouv.fr/datasets/donnees-du-repertoire-national-des-elus-locaux-municipaux-communautaires-epci-departementaux-regionaux)
- [data.gouv.fr — RNE députés et sénateurs](https://www.data.gouv.fr/datasets/repertoire-national-des-elus-deputes-et-senateurs)
- [data.gouv.fr — Élections municipales 2026, maires et conseillers sortants](https://www.data.gouv.fr/datasets/elections-municipales-2026-maires-et-conseillers-municipaux-sortants)
- [data.gouv.fr — Découpage NUTS-2 des régions européennes](https://www.data.gouv.fr/datasets/decoupage-nuts-2-des-regions-europeennes)
- [OpenStreetMap Wiki — FR:Tag:amenity=polling_station](https://wiki.openstreetmap.org/wiki/FR:Tag:amenity=polling_station)
- [OpenStreetMap Wiki — FR:Overpass API](https://wiki.openstreetmap.org/wiki/FR:Overpass_API)
- [Légifrance — Open data et API](https://www.legifrance.gouv.fr/contenu/pied-de-page/open-data-et-api)
- [data.gouv.fr — LEGI](https://www.data.gouv.fr/datasets/legi-codes-lois-et-reglements-consolides)
- [data.gouv.fr — DOLE](https://www.data.gouv.fr/datasets/dole-les-dossiers-legislatifs)
- [GitHub regardscitoyens/nosdeputes.fr — doc API](https://github.com/regardscitoyens/nosdeputes.fr/blob/master/doc/api.md)
- [Regards Citoyens — La Fabrique de la Loi](https://www.regardscitoyens.org/la-fabrique-de-la-loi/)
- [La Fabrique de la Loi — Visualizing the data](https://blog.lafabriquedelaloi.fr/visualizing-the-law-factory-data/)
- [Datan.fr](https://datan.fr/) et [Datan — statistiques expliquées](https://datan.fr/statistiques/aide)
- [TheyWorkForYou](https://www.theyworkforyou.com/) — [Open Data's Impact, étude de cas](https://odimpact.org/case-united-kingdoms-theyworkforyou.html)
- Rapports internes déjà existants : `reports/exploration-legislatif-sources.md`, `reports/exploration-legislatif-national-datagouv.md`

**Sources non vérifiées en profondeur, à confirmer avant tout engagement** : dataset data.gouv.fr "Elections municipales 2026 — maires et conseillers sortants" (existence confirmée par le titre uniquement) ; couverture réelle du tag `amenity=polling_station` sur le territoire HdF (à échantillonner) ; API CLAIR / Eutyn (agrégateurs tiers AN+Sénat mentionnés dans `exploration-legislatif-sources.md` mais non testés en détail).
