# Inventaire des sources de données économiques — HdF

## Synthèse (tableau récapitulatif)
| Source | Indicateurs | Granularité | Temporalité | Format | Licence |
|---|---|---|---|---|---|
| **INSEE (Filosofi)** | Revenus, taux de pauvreté | Commune, IRIS | Annuelle | CSV | Licence Ouverte v2.0 |
| **INSEE (Recensement)** | Pop. active, CSP | Commune, IRIS | Annuelle | CSV | Licence Ouverte v2.0 |
| **INSEE (Sirene)** | Créations, tissu d'entreprises | Commune, Adresse | Mensuelle | CSV | Licence Ouverte v2.0 |
| **France Travail** | Demandeurs d'emploi (A, B, C) | Commune (>5000 hab), Dept | Trimestrielle | Excel / CSV | Licence Ouverte v2.0 |
| **INSEE / data.gouv.fr** | Taux de chômage (BIT) | Zone d'emploi, Dept | Trimestrielle | Excel / CSV | Licence Ouverte v2.0 |
| **Banque de France** | Conjoncture, bilans | Région | Mensuelle/Annuelle | PDF / Excel | Ouverte sous conditions |
| **INSEE** | Comptes régionaux (PIB) | Région, Département | Annuelle | Excel / CSV | Licence Ouverte v2.0 |
| **Eurostat** | PIB, emploi (NUTS) | NUTS 2 (anciennes rég.), NUTS 3 (Dept) | Annuelle | CSV / TSV | CC BY 4.0 |
| **Dares** | Marché du travail, contrats | Région, Département | Mensuelle/Trimes. | Excel / CSV | Licence Ouverte v2.0 |

## Détail par thématique

### Emploi et chômage

**1. Demandeurs d'emploi inscrits à France Travail (ex-Pôle emploi)**
- **Nom exact du jeu de données** : Demandeurs d'emploi inscrits en fin de mois à Pôle emploi (France Travail) par commune
- **URL directe** : [statistiques.francetravail.org](https://statistiques.francetravail.org) (Rubrique Données Locales)
- **Organisme producteur** : France Travail / Dares
- **Indicateurs disponibles** : Nombre de demandeurs d'emploi par catégorie (A, B, C), âge, sexe.
- **Granularité géographique** : Commune (uniquement pour les communes > 5 000 habitants). Pour les communes < 5 000 habitants, les données sont fournies de manière agrégée. Données exhaustives au Département et Région.
- **Granularité temporelle** : Trimestrielle.
- **Couverture temporelle** : Historique profond (souvent depuis 1996 au niveau macro, plus récent au niveau local).
- **Format de téléchargement** : Excel, CSV.
- **Licence** : Licence Ouverte (Etalab).
- **Documentation technique** : Méthodologie disponible sur le portail statistiques de France Travail.
- **Alerte (Granularité insuffisante)** : Le seuil de 5 000 habitants est très problématique pour le projet Ministère de l'Info, car les Hauts-de-France comptent une immense majorité de communes sous ce seuil (notamment dans la Somme, l'Aisne et l'Oise).

**2. Taux de chômage localisé (Insee)**
- **Nom exact du jeu de données** : Taux de chômage par zone d'emploi et département
- **URL directe** : [insee.fr (Taux de chômage localisé)](https://www.insee.fr/fr/statistiques/series/102759768)
- **Organisme producteur** : INSEE
- **Indicateurs disponibles** : Taux de chômage au sens du BIT (Bureau International du Travail).
- **Granularité géographique** : Zone d'emploi, Département, Région.
- **Granularité temporelle** : Trimestrielle.
- **Couverture temporelle** : Depuis 2003.
- **Format de téléchargement** : CSV, Excel.
- **Licence** : Licence Ouverte v2.0.
- **Alerte (Granularité insuffisante)** : Aucune donnée à l'échelle communale. La zone d'emploi est le niveau le plus fin disponible pour le taux officiel du BIT.

### Revenus et pauvreté

**3. Revenus et pauvreté des ménages (Filosofi)**
- **Nom exact du jeu de données** : Dispositif Fichier localisé social et fiscal (Filosofi)
- **URL directe** : [insee.fr (Données locales Filosofi)](https://www.insee.fr/fr/statistiques/6036907)
- **Organisme producteur** : INSEE
- **Indicateurs disponibles** : Médiane du niveau de vie, taux de pauvreté (seuil 60% du revenu médian), déciles de revenus, part des revenus sociaux.
- **Granularité géographique** : Commune, IRIS (quartiers), EPCI, Département.
- **Granularité temporelle** : Annuelle.
- **Couverture temporelle** : Données disponibles annuellement depuis 2012 (nouveau dispositif remplaçant les Revenus Fiscaux Localisés).
- **Format de téléchargement** : CSV, API Insee.
- **Licence** : Licence Ouverte v2.0.
- **Documentation technique** : [Documentation Filosofi (Insee)](https://www.insee.fr/fr/metadonnees/source/serie/s1172)
- **Alerte** : Pour respecter le secret statistique, les données des communes de moins de 50 ménages (fréquent en Picardie) sont secrétisées.

### Tissu économique (entreprises, secteurs)

**4. Base des entreprises et des établissements (Sirene)**
- **Nom exact du jeu de données** : Base Sirene des entreprises et de leurs établissements (Stock)
- **URL directe** : [data.gouv.fr (Base Sirene)](https://www.data.gouv.fr/fr/datasets/base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret/)
- **Organisme producteur** : INSEE
- **Indicateurs disponibles** : Code APE (secteur d'activité), tranche d'effectifs, catégorie juridique, date de création/fermeture.
- **Granularité géographique** : Adresse exacte (géocodable), Commune.
- **Granularité temporelle** : Mise à jour quotidienne/mensuelle.
- **Couverture temporelle** : Stock actuel des entreprises actives.
- **Format de téléchargement** : CSV, API.
- **Licence** : Licence Ouverte v2.0.
- **Documentation technique** : Spécifications complètes sur data.gouv.fr.

### Données démographiques économiques (population active, CSP)

**5. Activité, emploi, chômage (Recensement de la population)**
- **Nom exact du jeu de données** : Bases de données du recensement de la population - Thème Activité, emploi, chômage
- **URL directe** : [insee.fr (Bases de données RP)](https://www.insee.fr/fr/statistiques/7632662)
- **Organisme producteur** : INSEE
- **Indicateurs disponibles** : Population active, taux d'activité, taux de chômage (au sens déclaratif du recensement, différent du BIT), répartition par Catégorie Socioprofessionnelle (CSP).
- **Granularité géographique** : Commune, IRIS, EPCI.
- **Granularité temporelle** : Annuelle (résultats basés sur des millésimes glissants de 5 ans).
- **Couverture temporelle** : Historique profond (ex: millésimes de 2006 à aujourd'hui).
- **Format de téléchargement** : CSV, format DBF historique.
- **Licence** : Licence Ouverte v2.0.
- **Intérêt majeur** : C'est la seule source exhaustive pour obtenir un taux de chômage et des effectifs de population active pour 100% des communes, même les plus petites.

### Autres indicateurs pertinents

**6. Produit Intérieur Brut (PIB) et Comptes régionaux**
- **Nom exact du jeu de données** : Produit intérieur brut (PIB) à prix courants par région
- **URL directe** : [insee.fr (Comptes régionaux)](https://www.insee.fr/fr/statistiques/series/102759752)
- **Organisme producteur** : INSEE
- **Indicateurs disponibles** : PIB, Valeur ajoutée brute par secteur.
- **Granularité géographique** : Région (Hauts-de-France), Département.
- **Granularité temporelle** : Annuelle.
- **Couverture temporelle** : Séries longues (selon l'année de base des comptes nationaux).
- **Format de téléchargement** : Excel, CSV.
- **Licence** : Licence Ouverte v2.0.
- **Alerte (Granularité insuffisante)** : Il n'existe aucune donnée officielle de PIB à l'échelle communale ou intercommunale.

**7. Données macroéconomiques européennes (Eurostat)**
- **Nom exact du jeu de données** : Regional gross domestic product (PPS per inhabitant) by NUTS 2 regions
- **URL directe** : [ec.europa.eu/eurostat](https://ec.europa.eu/eurostat/databrowser/view/tgs00005/default/table)
- **Organisme producteur** : Eurostat
- **Indicateurs disponibles** : PIB par habitant en standard de pouvoir d'achat (SPA), emploi régional.
- **Granularité géographique** : NUTS 1 (FRE = Hauts-de-France), NUTS 2 (FRE1 = Nord-Pas-de-Calais, FRE2 = Picardie), NUTS 3 (Départements).
- **Granularité temporelle** : Annuelle.
- **Format de téléchargement** : TSV, CSV.
- **Licence** : CC BY 4.0.
- **Alerte (Granularité insuffisante)** : Le découpage NUTS s'arrête au département. Ne peut servir qu'à une comparaison macro-européenne.

## Sources écartées (pourquoi)

1. **Banque de France - Conjoncture régionale** : Les rapports de conjoncture (tendances industrielles, bilans d'entreprises) publiés par la Banque de France pour les Hauts-de-France sont très qualitatifs et intéressants sur le plan macro-économique. Toutefois, ils sont le plus souvent diffusés sous forme de rapports PDF ou de données purement régionales agrégées. Ils ne fournissent pas de jeux de données tabulaires téléchargeables à une granularité communale ou infra-départementale exploitable dans un pipeline ETL orienté "territoires" (DuckDB).
2. **Dares (marché du travail)** : Bien que fournissant des données très riches sur les politiques de l'emploi (contrats aidés, ruptures conventionnelles, formation), la granularité s'arrête généralement au département ou à la région. De plus, les données d'emploi pur font souvent doublon avec les sources de l'Insee (Estimations d'emploi) ou de France Travail.
3. **Le PIB communal** : Aucune source publique (Insee, Eurostat, data.gouv.fr) ne calcule ni ne diffuse de PIB à l'échelle communale en France. Le concept même a peu de sens statistique (problème des travailleurs navetteurs). Toute source tierce proposant du "PIB par commune" repose sur de la modélisation privée non sourçable pour ce projet.

## Points d'attention techniques

- **Triade du chômage (Piège sémantique)** : Il existe trois définitions du chômage qui donneront des chiffres différents :
    1. *Insee (BIT)* : Taux officiel pour les comparaisons internationales, mais bloqué à la zone d'emploi.
    2. *France Travail (Inscrits)* : Compte les inscrits administratifs (cat A, B, C). Mais absent pour les petites communes.
    3. *Insee (Recensement)* : Basé sur du déclaratif. C'est la **seule** source permettant un calcul de taux de chômage local à la maille de la commune.
    Il faudra faire un choix éditorial strict et le documenter dans l'UI Streamlit.
- **Changements géographiques (Code Insee)** : Les fusions de communes (communes nouvelles) impactent fortement les séries temporelles locales (Filosofi, Recensement). Il sera impératif de conserver la logique d'historisation des codes géographiques (COG) déjà en place dans le module Géographie pour joindre ces données aux polygones de la carte.
- **Le secret statistique (Filosofi)** : L'Insee masque les indicateurs de revenus pour les communes de très petite taille afin d'empêcher l'identification des personnes. Ces données manquantes apparaîtront en NULL ou `N/A` dans les CSV. Un traitement spécifique (`FILL` ou gestion des valeurs manquantes dans Polars/DuckDB) sera nécessaire.
- **Fichiers très volumineux (Sirene)** : Le stock Sirene complet pèse plusieurs gigaoctets (plus de 30 millions de lignes). L'ETL Python ne devra pas tout charger en mémoire. Il sera impératif de filtrer à la volée avec DuckDB (via le paramètre `read_csv_auto`) en utilisant une clause `WHERE code_commune LIKE '02%' OR code_commune LIKE '59%'...` avant de matérialiser les tables régionales.
- **Encodage des CSV de l'Insee** : Historiquement, l'Insee distribue la majorité de ses données locales (Filosofi, Recensement) dans des fichiers CSV délimités par des points-virgules (`;`) et encodés en **latin-1 (ISO-8859-1)**, contrairement au standard UTF-8. C'est un point de vigilance critique (gotcha n°3 du `CLAUDE.md`) lors de l'intégration dans DuckDB.
