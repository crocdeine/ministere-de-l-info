# Sweep élargi — sources économiques complémentaires

Cette étude recense les sources de données publiques hors INSEE pertinentes pour enrichir le modèle (contexte économique, social et territorial) dans les Hauts-de-France (HdF), à une granularité pertinente pour l'analyse politique, sur la période 2000-2024.

## Quick wins (données déjà accessibles, ETL simple)

### 1. CNAF : Foyers allocataires du RSA par commune
- **Nom du dataset** : Répartition des allocataires selon le type de RSA [Communal]
- **URL** : [https://data.caf.fr/explore/dataset/foyers-rsa-commune](https://data.caf.fr/explore/dataset/foyers-rsa-commune)
- **Organisme** : CNAF (données CAF)
- **Indicateurs** : Nombre de foyers allocataires, personnes couvertes, montants versés.
- **Granularité géographique** : Commune (données arrondies à 5).
- **Couverture temporelle** : 2020-2023+
- **Format** : CSV / API / Parquet
- **Pertinence électorale HdF** : Haute. Le RSA est un proxy direct de la très grande pauvreté (indicateur clé souvent corrélé au vote RN ou à l'abstention).
- **Complexité ETL** : Faible (format très structuré, directement requêtable en API/CSV).
- **Verdict** : Quick win

### 2. DREES : Déserts médicaux (Indicateur APL)
- **Nom du dataset** : Indicateur d'Accessibilité Potentielle Localisée (APL) aux médecins généralistes
- **URL** : [https://www.data.gouv.fr/fr/datasets/indicateur-d-accessibilite-potentielle-localisee-apl/](https://www.data.gouv.fr/fr/datasets/indicateur-d-accessibilite-potentielle-localisee-apl/)
- **Organisme** : DREES
- **Indicateurs** : APL (mesure l'accessibilité aux soins de premier recours, prend en compte l'offre et la demande).
- **Granularité géographique** : Commune.
- **Couverture temporelle** : 2015-2022+ (actualisations annuelles).
- **Format** : CSV / Excel
- **Pertinence électorale HdF** : Haute. Fort marqueur de relégation territoriale et du sentiment d'abandon, très prégnant en ruralité et péri-urbain.
- **Complexité ETL** : Faible (fichiers communaux annuels).
- **Verdict** : Quick win

## Sources V1 (à intégrer avant l'UI, effort modéré)

### 3. URSSAF / ACOSS : Dynamique de l'emploi privé
- **Nom du dataset** : Nombre d'établissements employeurs et effectifs salariés du secteur privé, par commune x APE
- **URL** : [https://open.urssaf.fr/explore/dataset/etablissements-employeurs-et-effectifs-salaries-du-secteur-prive-par-commune](https://open.urssaf.fr/explore/dataset/etablissements-employeurs-et-effectifs-salaries-du-secteur-prive-par-commune)
- **Organisme** : URSSAF / ACOSS
- **Indicateurs** : Effectifs salariés du secteur privé et nombre d'établissements.
- **Granularité géographique** : Commune croisée par code NAF/APE.
- **Couverture temporelle** : Depuis 2006 (au 31/12 de chaque année).
- **Format** : CSV / JSON
- **Pertinence électorale HdF** : Haute. Permet d'isoler la dynamique de l'emploi (destructions d'emplois vs créations, et surtout la part de l'emploi industriel ou de services).
- **Complexité ETL** : Moyenne. Nécessite une agrégation par secteur NAF pour ne pas faire exploser la volumétrie.
- **Verdict** : V1

### 4. Observatoire des Territoires : Zonages et vulnérabilité
- **Nom du dataset** : Indicateurs divers (ZRR, QPV, fragilité, bassins de vie)
- **URL** : [https://www.observatoire-des-territoires.gouv.fr/donnees-ouvertes](https://www.observatoire-des-territoires.gouv.fr/donnees-ouvertes)
- **Organisme** : ANCT (Observatoire des territoires)
- **Indicateurs** : Zonages politiques (ZRR, QPV, CRTE), indicateurs de centralité et de vulnérabilité.
- **Granularité géographique** : Commune, EPCI, Bassin de vie.
- **Couverture temporelle** : Historique variable selon les indicateurs.
- **Format** : CSV / API (fiches indicateurs téléchargeables).
- **Pertinence électorale HdF** : Haute (surtout pour catégoriser le type de commune rural/urbain/périurbain et l'effet des politiques publiques type ZRR).
- **Complexité ETL** : Moyenne (nécessite de sélectionner à la main les bons indicateurs parmi des centaines de fichiers).
- **Verdict** : V1 (sélectionner 3-4 zonages clés)

### 5. Base Permanente des Équipements (BPE)
- **Nom du dataset** : Base permanente des équipements
- **URL** : [https://www.data.gouv.fr/fr/datasets/base-permanente-des-equipements/](https://www.data.gouv.fr/fr/datasets/base-permanente-des-equipements/)
- **Organisme** : INSEE (mais diffusé en Open Data classique)
- **Indicateurs** : Présence de commerces, services publics, santé, éducation.
- **Granularité géographique** : Commune.
- **Couverture temporelle** : Séries annuelles (depuis ~2013).
- **Format** : CSV
- **Pertinence électorale HdF** : Haute (fermeture de services publics = moteur électoral).
- **Complexité ETL** : Moyenne. Besoin de faire des deltas (années N vs N-5) pour capter les *fermetures* d'équipements plutôt que juste le stock.
- **Verdict** : V1

## Sources V2 (intéressantes, ETL complexe ou granularité imparfaite)

### 6. Ministère de l'Éducation nationale : IPS
- **Nom du dataset** : Indices de position sociale (IPS) des établissements
- **URL** : [https://data.education.gouv.fr/explore/dataset/fr-en-ips_colleges](https://data.education.gouv.fr/explore/dataset/fr-en-ips_colleges)
- **Organisme** : DEPP
- **Indicateurs** : IPS (résumé du profil socio-économique des familles des élèves).
- **Granularité géographique** : Établissement (école, collège, lycée).
- **Couverture temporelle** : 2016-2022+
- **Format** : CSV
- **Pertinence électorale HdF** : Moyenne/Haute. Excellent proxy de la ségrégation sociale.
- **Complexité ETL** : Haute. Il faut agréger les données de l'établissement à la commune, ce qui est très imparfait (les élèves des communes rurales vont au collège dans la ville centre, biais d'affectation).
- **Verdict** : V2

### 7. Etalab / DGFiP : Demandes de Valeurs Foncières (DVF)
- **Nom du dataset** : Demandes de valeurs foncières géolocalisées (DVF+)
- **URL** : [https://www.data.gouv.fr/fr/datasets/demandes-de-valeurs-foncieres/](https://www.data.gouv.fr/fr/datasets/demandes-de-valeurs-foncieres/)
- **Organisme** : DGFiP / Cerema
- **Indicateurs** : Prix de vente des biens immobiliers.
- **Granularité géographique** : Parcelle / Adresse -> Commune.
- **Couverture temporelle** : 5 dernières années (roulant).
- **Format** : CSV massifs (> 10 Go par an).
- **Pertinence électorale HdF** : Moyenne. La dévalorisation immobilière est liée au vote contestataire, mais le bruit dans les données est énorme.
- **Complexité ETL** : Très haute (nettoyage lourd, outliers, taille des fichiers).
- **Verdict** : V2 (utiliser plutôt des agrégats communaux si existants).

## Sources écartées (pourquoi)

### 8. Banque de France : Surendettement
- **Organisme** : Banque de France (Portail Webstat / IFI).
- **Pourquoi écartée** : La granularité est uniquement **départementale**. C'est insuffisant pour croiser avec des résultats électoraux qui se jouent souvent au niveau du bureau de vote ou de la commune. Ne permet pas de faire la différence entre Lille et Roubaix, ou Amiens et le Vimeu.

### 9. Eurostat : Macro-économie (PIB, Taux de pauvreté NUTS 2)
- **Organisme** : Commission Européenne.
- **Pourquoi écartée** : Les données comme le taux de risque de pauvreté (ilc_li41) ou l'emploi sont produites à l'échelle NUTS 2 (Anciennes régions, ex: Picardie / Nord-Pas-de-Calais) ou NUTS 3 (Départements). Tout comme la Banque de France, l'échelle est trop macroscopique pour notre modélisation à la commune, même si utile pour une introduction ou du contexte global.

### 10. Open Data Région Hauts-de-France (Budget/Subventions)
- **Organisme** : Région HdF
- **Pourquoi écartée** : Bien que les subventions existent, il n'y a pas de standard national pour l'open data des subventions qui permettrait une intégration ETL simple, pérenne et surtout *comparable* avec le reste de la France (si le projet s'étend au-delà des HdF).

## Recommandation finale : table `economie_contexte` et nouvelles tables

Afin de ne pas surcharger les tables de base de données existantes et de respecter l'objectif V1, voici les recommandations d'architecture :

1. **Intégrer les "Quick wins" dans une table `economie_social_commune`** :
   - Ajouter le `% de foyers RSA` (CNAF) et l'`Indicateur APL` (DREES) en jointure par code INSEE.
   - Ce sont deux variables explicatives puissantes (Précarité extrême et Déserts médicaux) avec très peu de friction ETL.

2. **Créer une table spécifique `economie_emploi_urssaf`** :
   - Stocker l'évolution des effectifs salariés privés par secteur NAF.
   - Cette série longue (depuis 2006) est cruciale pour l'analyse des désindustrialisations locales (fermetures d'usines).

3. **Créer une table `territoire_zonages`** :
   - Importer les tables de l'Observatoire des Territoires : statuts QPV, ZRR (Zone de Revitalisation Rurale), classement par types de densité (rural profond, péri-urbain, etc.).
   - Cela servira de filtres majeurs dans la future UI.

L'objectif immédiat pour passer au développement de l'UI est d'ingérer la **CNAF (RSA)**, la **DREES (Santé)** et **l'URSSAF (Emploi privé)**. Les sources V2 (DVF, IPS) pourront faire l'objet de releases ultérieures si le modèle manque de pouvoir explicatif.
