# Brainstorm — Indicateurs économiques complémentaires

## Indicateurs prioritaires (À intégrer maintenant)

### 1. Allocataires des minima sociaux (RSA, AAH)
- **Nom de l'indicateur :** Part des foyers allocataires CAF percevant un minimum social, taux de couverture RSA/AAH.
- **Source et URL :** CNAF (Open Data CAF - [data.caf.fr](https://data.caf.fr/))
- **Granularité géographique :** Commune
- **Couverture temporelle :** ~2009 → 2024
- **Format :** CSV
- **Pertinence électorale :** Haute. L'ancrage de la précarité (RSA) ou du handicap (AAH) est un fort déterminant sociologique des dynamiques de vote, de l'abstention et du vote contestataire.
- **Complexité ETL :** Moyenne. Les géographies CAF épousent les codes INSEE, mais il faut gérer les fusions de communes et le secret statistique (valeurs masquées si effectif faible).
- **Verdict :** **À intégrer en priorité**

### 2. Démographie historique (Vieillissement et Déclin)
- **Nom de l'indicateur :** Évolution de la population, part des plus de 65 ans sur 20 ans.
- **Source et URL :** INSEE, Séries historiques du RP ([insee.fr](https://www.insee.fr/fr/statistiques/))
- **Granularité géographique :** Commune
- **Couverture temporelle :** 1968, 1975, ..., 1999, 2006 → 2021
- **Format :** CSV / Excel
- **Pertinence électorale :** Haute. Le déclin démographique (communes qui se vident) et le vieillissement sont clés pour analyser le clivage villes/campagnes.
- **Complexité ETL :** Faible. Séries déjà harmonisées par l'INSEE sur la géographie courante (très pratique).
- **Verdict :** **À intégrer en priorité**

### 3. Salaire net horaire moyen
- **Nom de l'indicateur :** Salaire net horaire moyen selon la catégorie socioprofessionnelle.
- **Source et URL :** INSEE (Bases tous salariés / DADS - [insee.fr](https://www.insee.fr/fr/statistiques/))
- **Granularité géographique :** Commune (pour les communes assez grandes) ou EPCI.
- **Couverture temporelle :** Longue (2000 → 2022)
- **Format :** CSV
- **Pertinence électorale :** Haute. Le niveau de salaire local (ouvrier/employé) et son évolution expliquent le sentiment de déclassement économique.
- **Complexité ETL :** Moyenne. Secret statistique fréquent pour les petites communes, nécessitant d'imputer à l'EPCI si absent.
- **Verdict :** **À intégrer en priorité**

### 4. Logements sociaux (HLM)
- **Nom de l'indicateur :** Part des résidences principales qui sont des logements sociaux.
- **Source et URL :** INSEE (RP Logement) ou Ministère de la Transition écologique (RPLS)
- **Granularité géographique :** Commune
- **Couverture temporelle :** Historique continu sur 15+ années.
- **Format :** CSV
- **Pertinence électorale :** Haute. Le vote en zone HLM / quartier prioritaire a des comportements spécifiques.
- **Complexité ETL :** Faible. Le RP est déjà manipulé, l'ajout de ces colonnes est direct.
- **Verdict :** **À intégrer en priorité**


## Indicateurs contextuels (série longue HdF vs France)

### 1. Taux de chômage localisé (au sens du BIT)
- **Nom de l'indicateur :** Taux de chômage trimestriel localisé.
- **Source et URL :** INSEE ([insee.fr/fr/statistiques/series/102759768](https://www.insee.fr/))
- **Granularité géographique :** Région, Département, Zone d'emploi
- **Couverture temporelle :** 2003 → 2024 (Trimestriel)
- **Format :** Excel / CSV
- **Pertinence électorale :** Haute. Permet de situer la région HdF par rapport à la moyenne nationale et d'observer l'impact de crises macroéconomiques sur les bassins de vote.
- **Complexité ETL :** Faible. Série homogène.
- **Verdict :** **À intégrer en priorité pour le contexte.**

### 2. PIB Régional et par habitant
- **Nom de l'indicateur :** Produit Intérieur Brut par habitant (base 100 France).
- **Source et URL :** INSEE Comptes régionaux / Eurostat NUTS2
- **Granularité géographique :** Région, Département
- **Couverture temporelle :** 2000 → 2023
- **Format :** CSV
- **Pertinence électorale :** Moyenne. Assez macro, mais donne le "pouls" du décrochage ou du rattrapage du territoire.
- **Complexité ETL :** Faible.
- **Verdict :** **À intégrer en priorité pour le contexte.**


## Indicateurs v2 (intéressants mais complexes)

### 1. Déserts médicaux (Accessibilité aux soins)
- **Pourquoi en V2 :** L'APL (Accessibilité Potentielle Localisée) mesurée par la DREES est très pertinente politiquement (sentiment d'abandon). Néanmoins, reconstruire une série propre et historique à la maille communale est chronophage à cause des changements de méthodologie.

### 2. Défaillances d'entreprises
- **Pourquoi en V2 :** Descendre sous la maille départementale exige de brasser le BODACC et la base SIRENE entreprise par entreprise. Volumétrie et complexité ETL trop élevées pour cette phase.

### 3. Prix de l'immobilier (DVF)
- **Pourquoi en V2 :** Base Demandes de Valeurs Foncières d'Etalab : très lourde (millions de transactions). Il faudrait créer un pipeline Data Engineering complexe juste pour moyenner les prix au m² par commune et par année.


## Indicateurs écartés (pourquoi)

### 1. Taux de réussite au baccalauréat
- **Pourquoi écarté :** Les données sont publiées par lycée, obligeant à créer une sectorisation complexe pour l'attribuer aux communes de résidence. Le niveau de diplôme global de la population résidente (déjà dans le RP) est un proxy plus robuste pour l'analyse électorale.

### 2. Solde migratoire annuel
- **Pourquoi écarté :** Trop de bruit statistique et complexe à consolider sans sauts de série pour de petites communes. La tendance démographique lissée (Indicateur Prioritaire 2) donne exactement l'information politique cherchée.


## Recommandations pour le schéma DuckDB

Il est recommandé d'adopter une modélisation modulaire (type étoile/flocon) plutôt que de surcharger les tables de base.

1. **Ne pas altérer `economie_filosofi` et `economie_rp` :**
   - Laisser ces tables miroiter strictement les structures de l'INSEE. Ajouter de l'information dedans complexifiera les mises à jour (ex: si l'INSEE change ses formats l'an prochain).

2. **Créer de nouvelles tables thématiques infra-régionales :**
   - `economie_social` : pour les données CNAF (taux RSA, AAH, etc.) indexées par `code_insee` et `annee`.
   - `economie_demographie` : pour les séries longues historiques (pop, >65 ans).
   - `economie_salaires` : pour les bases salariés.

3. **Créer une table dédiée aux séries macroéconomiques :**
   - `economie_contexte` :
     - *Axes :* `id_zone`, `type_zone` ('REG', 'DEP', 'ZE', 'FRA'), `annee` (ou `trimestre`).
     - *Mesures :* `taux_chomage_bit`, `pib_habitant_euros`, etc.

4. **Centraliser les jointures dans des VUES :**
   - Créer des `CREATE VIEW` qui font les `LEFT JOIN` entre la géographie des votes et les différentes tables d'économie via le `code_insee` ou les identifiants territoriaux. Cela garde le schéma de stockage propre tout en offrant une table "dénormalisée" pour l'UI.
