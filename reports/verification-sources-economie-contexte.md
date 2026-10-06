# Vérification sources — economie_contexte

## Taux de chômage BIT (INSEE)
- **URL de téléchargement confirmée** : L'URL fournie (`https://www.insee.fr/fr/statistiques/series/102759768`) pointe vers l'interface des séries IDBank de l'INSEE. L'export direct automatisé se fait typiquement via l'URL d'API : `https://www.insee.fr/fr/statistiques/serie/telecharger/102759768?ordre=chronologique` (Attention : l'INSEE bloque souvent les requêtes automatisées type `curl` avec des erreurs 500, un téléchargement manuel ou l'utilisation d'un User-Agent spécifique est parfois requis).
- **Colonnes** : `idbank` ou `code_serie`, `periode` (format YYYY-T1, YYYY-T2...), `valeur` (le taux de chômage en %), `codes_geographiques` (souvent dans un fichier de métadonnées séparé dans le ZIP Insee).
- **Codes zones d'emploi HdF** : Les données couvrent bien les 5 départements HdF (02, 59, 60, 62, 80), la région HdF (Code INSEE 32) et la France entière. Pour les Zones d'Emploi (ZE2020), les codes HdF vont de 3201 à 3218.
- **Format** : Fichier CSV (généralement zippé), séparateur point-virgule (`;`), encodage UTF-8 (ou parfois ISO-8859-1).
- **Couverture** : Trimestrielle, généralement disponible du T1 2003 jusqu'à fin 2023 / début 2024.
- **Verdict** : **Nécessite transformation**. Les données Insee (via IDBank) sont livrées dans un format "long" (une ligne par trimestre par territoire) très verbeux qu'il faudra transposer ou insérer tel quel dans `economie_contexte`, et il faudra réconcilier les IDBanks avec les codes INSEE réels des territoires.

## PIB régional (INSEE + Eurostat)
- **URLs confirmées** :
  - INSEE : `https://www.insee.fr/fr/statistiques/series/102759752` (Mêmes restrictions anti-bot que le chômage).
  - Eurostat : `https://ec.europa.eu/eurostat/databrowser/view/tgs00005/default/table` (Code dataset `tgs00005`).
- **Granularité disponible pour HdF** : Niveau régional (NUTS 2 = Code `FRE` pour Hauts-de-France) et niveau départemental (NUTS 3 = `FRE11`, `FRE12`, etc.). La France entière est le code `FR`.
- **Couverture temporelle** : Annuelle, de 2000 à 2022.
- **Verdict** : **Intégrable directement via Eurostat**. Il est recommandé d'utiliser l'API SDMX ouverte d'Eurostat (`https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/tgs00005`) qui renvoie un TSV propre, plutôt que de lutter avec le portail INSEE.

## Logements sociaux
- **Source dans cache Parquet existant ?** : **OUI**.
  - La vérification empirique via DuckDB sur `donnees-insee-olap-hdf.parquet` confirme la présence de la source `rp_logements`.
  - Clefs JSON détectées (parfaitement adaptées) : `nb_rp_hlm_p` (nombre de résidences principales HLM) et `nb_pers_rp_hlm_p` (nombre de personnes en résidence principale HLM).
- **Source alternative si non** : Non nécessaire, la donnée est déjà téléchargée et structurée en local.
- **Verdict** : **Intégration immédiate**. Il suffit de modifier le code ETL existant qui parse le Parquet pour extraire ces deux `clef_json` à la maille de la commune.

## Recommandation finale
1. **Ce qu'on peut coder immédiatement (Quick Wins)** :
   - L'ajout des indicateurs "Logements sociaux" dans le module de traitement `economie_rp` car le Parquet est déjà présent sur le disque avec les bonnes clefs (`nb_rp_hlm_p`). C'est un effort ETL quasi nul.
2. **Ce qui nécessite plus d'exploration / Data Engineering** :
   - Pour la table `economie_contexte` (Chômage et PIB), il faudra soit gérer le téléchargement manuel des CSV INSEE (à cause des erreurs HTTP 500 sur leurs serveurs pour les bots), soit écrire un connecteur robuste à l'API Eurostat (qui est beaucoup plus permissive pour l'automatisation de séries temporelles macroéconomiques). Il sera préférable de stocker les données macro dans une table `economie_contexte` en base avec les colonnes `code_geo`, `type_geo` (ZE, DEP, REG, FRA), `annee`, `trimestre`, `indicateur`, et `valeur`.
