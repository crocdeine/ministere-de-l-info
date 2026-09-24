# 🇫🇷 Ministère de l'Info

[![CI](https://github.com/crocdeine/ministere-de-l-info/actions/workflows/ci.yml/badge.svg)](https://github.com/crocdeine/ministere-de-l-info/actions/workflows/ci.yml)

Application de data-visualisation politique, électorale et territoriale française.

## Description

Ministère de l'Info est une application web locale conçue pour explorer les données publiques françaises : géographie administrative, démographie, élections, composition et activité du Parlement, indicateurs économiques et sociaux. Elle s'appuie exclusivement sur des sources officielles ou publiques (IGN, INSEE, ministère de l'Intérieur via data.gouv.fr, Assemblée nationale via Datan, Sénat, CNAF, DREES, URSSAF, Eurostat). L'application tourne entièrement en local, sans dépendance à un service cloud.

## Stack technique

| Composant | Technologie |
|-----------|------------|
| Langage | Python 3.12 |
| Interface web | Streamlit ≥ 1.57 (navigation `st.navigation()`) |
| Base analytique | DuckDB ≥ 1.5 + extension spatial |
| Traitement données | Polars (Pandas en fallback) |
| Cartographie | Folium · streamlit-folium (GeoPandas côté ETL) |
| Graphiques | Plotly Express |
| Gestion paquets | uv |

## Modules

| Module | Contenu | Périmètre | Statut |
|--------|---------|-----------|--------|
| 🏠 Accueil | Hub de navigation vers les 4 modules | — | ✅ |
| 📍 Géographie | Régions, départements, EPCI, communes, arrondissements municipaux, circonscriptions ; populations 2013/2018/2023 | France | ✅ |
| 🗳️ Élections | Présidentielles 2002-2022, législatives 2002-2024, municipales 2008-2026 ; cartes par bloc, évolution, drill-down jusqu'au bureau de vote | Hauts-de-France | ✅ `v0.4-elections-complet` |
| 🏛️ Législatif | Députés (législatures 12 à 17) et sénateurs : composition politique, liste des élus, scores d'activité (AN), évolution par législature | France (filtre HdF ou département) | ✅ `v0.5-economie-legislatif` |
| 📊 Économie | Revenus et pauvreté (Filosofi), chômage, CSP et logements sociaux (RP), RSA (CNAF), accès aux médecins (DREES), emploi salarié privé (URSSAF), contexte HdF vs France (Eurostat) ; croisement avec les présidentielles | Hauts-de-France | ✅ `v0.5-economie-legislatif` |

Classement politique : 6 blocs officiels du ministère de l'Intérieur (EXG, GAU, DIV,
CENT, DTE, EXD), selon la grille en vigueur à la date du scrutin — voir
[ADR-0005](docs/adr/0005-nuances-et-blocs-officiels.md).

Le chantier design system (tokens CSS, navigation `st.navigation()`, août 2026) est sur
`main` mais n'est inclus dans aucune release à ce jour.

## Données chargées

Une base DuckDB unique (`data/ministere.duckdb`, ~900 Mo, non versionnée). Volumes
indicatifs repris des rapports de clôture de phase (`reports/`).

| Module | Tables principales | Volume |
|--------|--------------------|--------|
| Géographie | `geographies_*` (6 niveaux), `populations` | 18 régions, 101 départements, 1 265 EPCI, 34 877 communes, 45 arrondissements, 559 circonscriptions ; populations de 34 858 communes |
| Élections | `resultats_participation`, `resultats_candidats`, `nuances_harmonisees`, `candidats_presidentielle`, `blocs_politiques` | 30 scrutins, 162 469 lignes participation, 1 093 836 lignes candidats, 216 nuances mappées |
| Économie | `economie_filosofi`, `economie_rp`, `economie_social`, `economie_emploi_urssaf`, `economie_contexte` | 17 582 · 26 538 · RSA 17 381 + APL 3 788 · 1 157 338 · 104 lignes |
| Législatif | `leg_elus`, `leg_activite`, `leg_blocs_override` | 4 065 élus (2 120 AN + 1 945 Sénat), 1 653 lignes d'activité, 2 overrides |

## Installation

Prérequis : Python 3.12 et [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/crocdeine/ministere-de-l-info.git
cd ministere-de-l-info
uv sync --all-groups        # le groupe "etl" (geopandas, openpyxl) sert aux scripts ETL
uv run pre-commit install
```

## Obtenir la base de données

**Option A — télécharger la base publiée** (recommandé). La release
[`v0.5-economie-legislatif`](https://github.com/crocdeine/ministere-de-l-info/releases/tag/v0.5-economie-legislatif)
contient `ministere.duckdb.gz` (~635 Mo compressés), à décompresser dans `data/`.
`scripts/download_db.sh [tag]` automatise le téléchargement (requiert `GITHUB_TOKEN`).
Sans argument, ce script prend la dernière release dont le tag commence par `db-`
(`db-2026-05`, antérieure aux modules Élections, Économie et Législatif) : passer le tag
explicitement.

**Option B — reconstruire par ETL** depuis les sources publiques :

```bash
# 1. Géographie + populations
uv run python scripts/etl_territoires.py --millesimes 2023 --yes

# 2. Élections : schéma, puis les trois types de scrutin
#    Prérequis : les deux Parquet du dataset « Données des élections agrégées »
#    (data.gouv.fr) placés manuellement dans data/exploration/
#    (general-results.parquet, candidats-results.parquet) — les scripts ne les téléchargent pas
uv run python scripts/init_elections_schema.py
uv run python scripts/load_elections_presidentielles.py
uv run python scripts/load_elections_legislatives.py
uv run python scripts/load_elections_municipales.py

# 3. Économie : Filosofi, RP, CNAF, URSSAF, DREES ; Eurostat n'est pas inclus dans "all"
uv run python scripts/load_economie.py
uv run python scripts/load_economie.py --source eurostat

# 4. Législatif : Sénat, Datan, overrides
uv run python scripts/load_legislatif.py
```

> `--yes` bypasse la confirmation interactive pour le téléchargement des ~35 000
> communes. Les modules Élections et Économie s'appuient sur les tables géographiques :
> charger la géographie en premier.

## Lancement

```bash
uv run streamlit run app.py
# → http://localhost:8501
```

`app.py` est un routeur (`st.navigation()`) : il configure l'application puis affiche
la page choisie dans la barre latérale (Accueil, Géographie, Élections, Législatif,
Économie). Mode d'emploi : [`docs/guide-utilisateur.md`](docs/guide-utilisateur.md).

## Déploiement

- **Installation utilisateur (macOS + OrbStack)** : image Docker publiée sur
  `ghcr.io/crocdeine/ministere-de-l-info`, base téléchargée depuis la release GitHub.
  Script d'installation et procédure mainteneur : [`deploy/README-deploy.md`](deploy/README-deploy.md).
- **Self-hosted depuis les sources** (Docker Compose dev/prod, backups, dépannage) :
  [`docs/deployment.md`](docs/deployment.md).

```bash
docker build -t ministere-info:latest .
docker compose -f docker-compose.prod.yml up -d
curl http://localhost:8501/_stcore/health
```

## Architecture

```
ministere-de-l-info/
├── app.py                        # Routeur st.navigation() : config, logging, CSS, 5 st.Page
├── pages/                        # Points d'entrée des pages
│   ├── 0_🏠_Accueil.py
│   ├── 1_📍_Géographie.py
│   ├── 2_🗳️_Élections.py
│   ├── 3_🏛️_Législatif.py
│   └── 4_📊_Économie.py
├── src/ministere_de_l_info/
│   ├── _theme.py                 # inject_css(), render_page_header()
│   ├── _blocs_politiques.py      # Ordre, libellés, couleurs des 6 blocs
│   ├── custom.css                # Tokens du design system + sélecteurs Streamlit
│   ├── data_sources/             # Connecteurs géographie (IGN, INSEE, circonscriptions)
│   ├── etl/                      # Schémas DuckDB (géo, élections, économie, législatif) + loaders/
│   ├── pages/                    # render() des pages Élections, Législatif, Économie
│   └── viz/                      # Cartes Folium et requêtes @st.cache_data
├── scripts/                      # ETL en ligne de commande, migrations, scripts de base (backup, publication, téléchargement)
├── deploy/                       # Dockerfile de l'image publiée, install.sh, update.sh
├── docs/                         # Architecture, sources, schéma électoral, ADR, guide utilisateur
├── reports/                      # Rapports de session et de clôture de phase
├── data/                         # Base DuckDB + caches bruts (non versionné)
└── tests/                        # Suite pytest
```

Détail : [`docs/architecture.md`](docs/architecture.md).

## Tests

```bash
uv run pytest            # 381 tests collectés ; le marqueur "slow" est exclu par défaut
uv run pytest -m slow    # 13 tests Streamlit (serveur headless et AppTest)
```

Les tests d'intégration sont ignorés (`skip`) si `data/ministere.duckdb` est absente.
Certains tests appellent les API publiques (IGN, INSEE, data.gouv.fr) et échouent sans
accès réseau.

### Pre-commit hooks

Le projet utilise pre-commit pour automatiser lint et format avant chaque commit.

```bash
uv run pre-commit install          # après clone
uv run pre-commit run --all-files  # lancement manuel
```

## Documentation

| Document | Contenu |
|----------|---------|
| [`docs/architecture.md`](docs/architecture.md) | Structure du code, flux ETL, schéma DuckDB, CI, tests |
| [`docs/data-sources.md`](docs/data-sources.md) | Toutes les sources, formats, limitations |
| [`docs/schema-elections.md`](docs/schema-elections.md) | Tables et vues électorales, pièges des Parquet |
| [`docs/guide-utilisateur.md`](docs/guide-utilisateur.md) | Utilisation de l'application, page par page |
| [`docs/deployment.md`](docs/deployment.md) | Docker, backups, publication de la base |
| [`docs/adr/`](docs/adr/README.md) | Décisions d'architecture (ADR 0001 à 0009) |
| [`docs/lessons-learned.md`](docs/lessons-learned.md) | Leçons techniques par thème |
| [`docs/sources-officielles/nuances/`](docs/sources-officielles/nuances/index.md) | Circulaires de nuançage et décisions du Conseil d'État |

## Limitations connues

| Limitation | Cause | Contournement |
|------------|-------|---------------|
| Mayotte absente des vues population | Données INSEE séparées de DS_POPULATIONS_HISTORIQUES | Chargement manuel via source alternative |
| `comptee_a_part` et `totale` NULL | PCAP non disponible dans la source actuelle | TODO v2 |
| Données circonscriptions : source non officielle | API data.gouv.fr / jerome-desboeufs | Attendre export officiel AN |
| 11 EPT du Grand Paris sans département | Champ multi-valeur WFS non filtrable | Mapping manuel à prévoir |
| Municipales 2008 : Nord quasi absent | Fichier source data.gouv.fr incomplet (2 communes du 59) | Avertissement affiché dans l'UI |
| Pas de clic sur la carte pour le détail | streamlit-folium ne renvoie pas les propriétés de l'entité | Sélection par liste déroulante |
| Législatif : pas de scores Sénat ni de votes nominatifs | Datan ne couvre que l'AN ; XML AN non parsé | — |
| Économie : croisement électoral exploitable pour 2022 uniquement | Filosofi disponible à partir de 2017 (jointure année n-1) | — |

## Crédits

- **Auteur** : Mathias
- **Sources** : IGN ADMIN-EXPRESS-COG · INSEE (Mélodi, Filosofi, RP) · ministère de l'Intérieur / data.gouv.fr · Datan · Sénat (data.senat.fr) · CNAF · DREES · URSSAF · Eurostat
- **Licence** : données publiques (Licence Ouverte / Open Licence 2.0 pour les sources publiées sur data.gouv.fr) ; les conditions de réutilisation propres à chaque autre source (Eurostat, Datan, etc.) sont à consulter chez le producteur
