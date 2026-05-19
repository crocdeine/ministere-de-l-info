# 🇫🇷 Ministère de l'Info

Application de data-visualisation politique, électorale et territoriale française.

## Description

Ministère de l'Info est une application web locale conçue pour explorer les données publiques françaises : géographie administrative, démographie, élections, textes législatifs et indicateurs économiques. Elle s'adresse à toute personne souhaitant analyser et visualiser les territoires français — de la région à la circonscription législative — à partir de sources officielles (IGN, INSEE, data.gouv.fr). L'application tourne entièrement en local sans dépendance à un service cloud.

## Stack technique

| Composant | Technologie |
|-----------|------------|
| Langage | Python 3.12 |
| Interface web | Streamlit ≥ 1.57 |
| Base analytique | DuckDB ≥ 1.5 + extension spatial |
| Traitement données | Polars |
| Cartographie | GeoPandas · Folium · streamlit-folium |
| Graphiques | Plotly Express |
| Gestion paquets | uv |

## Données chargées

| Niveau | Source | Entités |
|--------|--------|---------|
| Régions | IGN ADMIN-EXPRESS-COG | 18 (13 métro + 5 DROM) |
| Départements | IGN ADMIN-EXPRESS-COG | 101 |
| EPCI | IGN ADMIN-EXPRESS-COG | 1 265 |
| Communes | IGN ADMIN-EXPRESS-COG | 34 877 |
| Arrondissements municipaux | IGN ADMIN-EXPRESS-COG | 45 |
| Circonscriptions législatives | data.gouv.fr | 559 |
| Populations communales | INSEE Mélodi | 34 858 communes · millésimes 2013, 2018, 2023 |

## Installation

```bash
git clone https://github.com/crocdeine/ministere-de-l-info.git
cd ministere-de-l-info
uv sync
```

## Premier lancement

```bash
# 1. Charger les données (durée : 5-15 min selon connexion)
uv run python scripts/etl_territoires.py --millesimes 2023 --yes

# 2. Lancer l'application
uv run streamlit run app.py
# → http://localhost:8501
```

> **Note** : le flag `--yes` bypasse la confirmation interactive pour le téléchargement des ~35 000 communes.

## Architecture

```
ministere-de-l-info/
├── app.py                    # Point d'entrée Streamlit
├── pages/                    # Pages multi-niveaux
│   └── 1_📍_Géographie.py   # Carte territoriale choroplèthe
├── src/ministere_de_l_info/
│   ├── data_sources/         # Connecteurs API (IGN, INSEE, data.gouv.fr)
│   └── viz/                  # make_choropleth() et helpers carto
├── scripts/
│   └── etl_territoires.py    # ETL complet : 6 niveaux géo + populations
├── data/
│   ├── ministere.duckdb      # Base analytique (non versionné)
│   └── raw/                  # Cache GeoJSON WFS (non versionné)
└── tests/                    # Tests pytest
```

## Fonctionnalités actuelles

- **Carte territoriale multi-niveaux** : région, département, EPCI, commune, arrondissement municipal, circonscription législative
- **Choroplèthe population** : par millésime (2013, 2018, 2023), palette jaune → rouge
- **Filtres contextuels** : par département et/ou région selon le niveau sélectionné
- **Mode contours** : pour les niveaux sans données population (arrondissements municipaux, circonscriptions)

## Modules à venir

- 🗳️ **Élections** — résultats présidentielles, législatives, municipales par bureau de vote
- 🏛️ **Législatif** — suivi des textes JORF, votes, amendements
- 💶 **Économie** — séries macroéconomiques BDF, données entreprises Sirene
- 👥 **Élus** — Répertoire National des Élus (RNE), HATVP, mandats

## Tests

```bash
uv run pytest -v
```

## Limitations connues

| Limitation | Cause | Contournement |
|------------|-------|---------------|
| Mayotte absente des vues population | Données INSEE séparées de DS_POPULATIONS_HISTORIQUES | Chargement manuel via source alternative |
| `comptee_a_part` et `totale` NULL | PCAP non disponible dans la source actuelle | TODO v2 |
| Données circonscriptions : source non officielle | API data.gouv.fr / jerome-desboeufs | Attendre export officiel AN |
| 11 EPT du Grand Paris sans département | Champ multi-valeur WFS non filtrable | Mapping manuel à prévoir |

## Crédits

- **Auteur** : Mathias
- **Sources** : IGN ADMIN-EXPRESS-COG · INSEE Mélodi · data.gouv.fr · geo.api.gouv.fr
- **Licence** : données publiques françaises (Licence Ouverte / Open Licence 2.0)
