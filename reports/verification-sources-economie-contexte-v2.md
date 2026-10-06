# Vérification sources economie_contexte (v2)

## Chômage BIT série longue
- URL testée : `https://www.insee.fr/fr/statistiques/serie/telecharger/102759768` a été testée avec `curl` et `requests`. Le serveur retourne soit une erreur 500, soit une page HTML anti-bot (script Matomo) empêchant tout téléchargement automatisé direct.
- Alternative trouvée :
  - `data.gouv.fr` : La recherche pour le taux de chômage par zone d'emploi ne retourne aucun jeu de données direct.
  - BDM INSEE : L'URL `https://bdm.insee.fr/bdm2/choixCriteres?codeGroupe=1690` retourne une erreur HTTP 404 (Introuvable).
  - Eurostat : L'API SDMX (`lfst_r_lfu3rt`) fonctionne parfaitement sans authentification.
- Format : Fichier TSV propre. Les colonnes de description sont fusionnées dans la première colonne : `freq,isced11,sex,age,unit,geo\TIME_PERIOD`, suivies des années en colonnes.
- Couverture HdF : Oui, les codes géographiques NUTS sont bien présents. `FRE` pour les Hauts-de-France et `FR` pour la France. La couverture temporelle s'étend de 1999 à 2025.
- Verdict : Intégrable directement via Eurostat. Un téléchargement automatisé depuis l'INSEE nécessiterait un scraper lourd (Selenium) ou un téléchargement manuel.

## PIB régional (Eurostat)
- URL API testée : `https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/tgs00005?geo=FRE&geo=FR&format=TSV`
  - Résultat : Erreur HTTP 404. L'API retourne `<faultstring>ERR_NOT_FOUND_2: DATA_SET:TGS00005 is not available for dissemination.</faultstring>`. Ce jeu de données a probablement été déprécié.
- Alternative trouvée : Le jeu de données Eurostat de remplacement valide pour le PIB régional est `nama_10r_2gdp` (ou `nama_10r_3gdp`). (Aucun export CSV probant et direct trouvé via l'API de data.gouv.fr).
- Format TSV : L'API retourne bien un TSV avec les colonnes `freq,unit,geo\TIME_PERIOD`.
- Codes géo HdF/France : Le code pour la France est `FR` et pour les Hauts-de-France `FRE`.
- Couverture temporelle : Les années sont disponibles de 2000 à 2024.
- Verdict : Intégrable directement en remplaçant l'identifiant du jeu de données par le nouveau (`nama_10r_2gdp`).

## Recommandation finale
Il est recommandé d'utiliser l'API SDMX d'Eurostat pour les deux indicateurs, car elle garantit un accès programmatique direct au format TSV, sans blocage ni nécessité de maintien d'un scraper complexe.

**Source 1 (Chômage BIT) :**
URL : `https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/lfst_r_lfu3rt?format=TSV`

**Source 2 (PIB Régional) :**
URL : `https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/nama_10r_2gdp?format=TSV`

**Code Python minimal pour télécharger (avec Pandas) :**
```python
import pandas as pd
import io
import requests

def download_eurostat_tsv(dataset_code):
    # L'API Eurostat permet l'export TSV direct
    url = f"https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/{dataset_code}?format=TSV"
    response = requests.get(url)
    response.raise_for_status()

    # Le format TSV d'Eurostat utilise des tabulations
    # La première colonne contient plusieurs descripteurs séparés par des virgules
    df = pd.read_csv(io.StringIO(response.text), sep='\t')
    return df

# Extraction des données
df_chomage = download_eurostat_tsv("lfst_r_lfu3rt")
df_pib = download_eurostat_tsv("nama_10r_2gdp")

print(df_pib.head())
```
