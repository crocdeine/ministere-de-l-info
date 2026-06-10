# Architecture — ministere-de-l-info

## Vue d'ensemble

Ministère de l'Info est une application web locale de data-visualisation politique,
électorale et territoriale française. Elle s'adresse à un utilisateur unique sur sa
machine, sans accès concurrentiel ni besoin d'API REST publique. L'ensemble de la
persistance tient dans un fichier DuckDB unique (`data/ministere.duckdb`) alimenté
par un ETL Python qui interroge les sources officielles (IGN, INSEE, data.gouv.fr).

## Stack technique

| Composant | Technologie | Version min | Rôle |
|-----------|-------------|-------------|------|
| Langage | Python | 3.12 | Typage strict, syntaxe moderne |
| Gestionnaire de paquets | uv | — | Lock file reproductible, CI rapide |
| Interface web | Streamlit | ≥ 1.57 | Pages interactives sans JavaScript |
| Base analytique | DuckDB + spatial | ≥ 1.5 | SQL analytique + géométries in-process |
| Traitement tabulaire | Polars | ≥ 1.40 | Traitement colonnaire rapide |
| Cartographie | GeoPandas · Folium · streamlit-folium | — | Rendu Leaflet interactif |
| Graphiques | Plotly Express | — | Graphiques interactifs web |
| Configuration | pydantic-settings | — | Variables d'environnement typées |
| Lint / format | ruff | ≥ 0.15 | Lint + format, cible py312, longueur 100 |

## Structure des modules

```
ministere-de-l-info/
│
├── app.py                          # Point d'entrée Streamlit, configure_logging()
├── pages/
│   ├── 1_📍_Géographie.py          # Carte territoriale choroplèthe
│   ├── 2_🗳️_Élections.py           # Tabs : Présidentielles + Législatives + Municipales (D3.3)
│   │                               #   → st.tabs() ; code dans src/pages/elections_*.py
│   ├── 3_🏛️_Législatif.py          # Stub — à cadrer
│   └── 4_💶_Économie.py            # Stub — à cadrer
│
├── src/ministere_de_l_info/
│   ├── logging_config.py           # configure_logging() : LOG_LEVEL + LOG_FORMAT
│   │
│   ├── data_sources/               # Connecteurs API bas niveau
│   │   ├── geo.py                  # WFS IGN ADMIN-EXPRESS (régions, dpts, EPCI, communes…)
│   │   ├── circonscriptions.py     # data.gouv.fr — 559 circonscriptions législatives
│   │   └── insee_populations.py    # INSEE Mélodi DS_POPULATIONS_HISTORIQUES
│   │
│   ├── etl/                        # Pipeline de chargement DuckDB
│   │   ├── schema.py               # CREATE TABLE / contraintes (7 tables géo + 2 méta)
│   │   ├── schema_elections.py     # Tables + vues électorales (8 vues, 2 colonnes D1.2)
│   │   ├── views.py                # CREATE VIEW v_population_{region,dpt,epci,commune}
│   │   ├── _common.py              # open_connection(), constantes partagées
│   │   └── loaders/                # Un loader par entité géographique
│   │       ├── regions.py
│   │       ├── departements.py
│   │       ├── epci.py
│   │       ├── communes.py
│   │       ├── arrondissements_municipaux.py
│   │       ├── circonscriptions.py
│   │       └── populations.py
│   │
│   ├── pages/                      # Modules UI Streamlit (render() importés par pages/)
│   │   ├── elections_presidentielles.py  # Onglet présidentielles HdF 2002-2022 + drill-down BV (D2)
│   │   ├── elections_legislatives.py     # Onglet législatives HdF 2002-2024 + drill-down BV (D2)
│   │   └── elections_municipales.py      # Onglet municipales HdF 2008-2026, drill-down listes (D3.3)
│   │
│   └── viz/                        # Visualisation cartographique + requêtes cachées
│       ├── maps.py                 # make_choropleth() — carte géographie
│       ├── maps_elections.py       # Cartes électorales Folium (communes + circos + muni)
│       │                           #   D3.3 : make_choropleth_muni_communes_bloc_dominant
│       │                           #          (gestion communes Non classées : gris + trait pointillé)
│       ├── elections_queries.py    # Requêtes @st.cache_data — présidentielles
│       │                           #   D2 : get_communes_hdf_pres, get_metrics_commune_pres,
│       │                           #        get_bv_details_pres, _build_bv_df (helper pivot)
│       ├── elections_legi_queries.py  # Requêtes @st.cache_data — législatives
│       │                           #   D2 : get_communes_circo_legi_list, get_metrics_commune_legi,
│       │                           #        get_bv_details_legi
│       ├── elections_muni_queries.py  # Requêtes @st.cache_data — municipales (D3.3)
│       │                           #   get_scrutins_muni, get_communes_muni_geo, get_listes_commune_muni,
│       │                           #   get_metrics_commune_muni, get_evolution_blocs_hdf_muni, etc.
│       ├── _config.py              # Constantes : tables, colonnes, géométries, filtres
│       ├── _display.py             # Palettes, formatters, légende HTML
│       └── _queries.py             # Builders SQL DuckDB + helpers géométriques
│
├── scripts/
│   └── etl_territoires.py          # CLI ETL orchestrateur
│
├── tests/                          # Suite pytest (331 tests, coverage 69 %)
│   ├── test_viz_maps.py
│   ├── test_etl_territoires.py
│   ├── test_etl_smoke.py                  # Tests d'intégrité DB
│   ├── test_pages_geographie.py
│   ├── test_elections_legislatives.py     # Données legi D1.2
│   ├── test_pages_legislatives.py         # Requêtes UI legi D1.3 + BV D2
│   ├── test_elections_presidentielles.py  # Requêtes BV présidentielles D2
│   ├── test_elections_municipales.py      # Données muni D3.2 (volumes, nuances, vues)
│   ├── test_pages_municipales.py          # Requêtes UI muni D3.3 + lacune source 2008
│   ├── test_streamlit_smoke.py            # Smoke + AppTest onglets + drill-down D2 + muni D3.3
│   └── …
│
└── data/
    ├── ministere.duckdb            # Base analytique (gitignored)
    └── raw/                        # Cache GeoJSON WFS (gitignored)
```

## Flux ETL

```
Sources externes                  ETL Python                     DuckDB
────────────────                  ──────────                     ──────

data.geopf.fr/wfs  ──WFS──►  data_sources/geo.py
                                       │
data.gouv.fr       ──JSON──►  data_sources/
                               circonscriptions.py   ──►  etl/loaders/*  ──►  geographies_*
                                       │                                        populations
api.insee.fr       ──JSON──►  data_sources/
                               insee_populations.py
                                       │
                               etl/schema.py (CREATE TABLE)
                               etl/views.py  (CREATE VIEW)   ──►  v_population_*

                                   ▼

                          scripts/etl_territoires.py  (orchestrateur CLI)

                                   ▼

                             ministere.duckdb
                                   │
                               Streamlit
                             pages/*.py  ──►  viz/maps.py  ──►  Folium  ──►  navigateur
```

## Schéma de la base DuckDB

### Tables géographiques

| Table | Lignes | Clé | Géométries |
|-------|--------|-----|------------|
| `geographies_regions` | 18 | `code_insee` | `geometry`, `geometry_simplified_national`, `geometry_simplified_regional` |
| `geographies_departements` | 101 | `code_insee` | `geometry`, `geometry_simplified_national`, `geometry_simplified_departemental` |
| `geographies_epci` | 1 265 | `code_siren` | `geometry`, `geometry_simplified_epci` |
| `geographies_communes` | 34 877 | `code_insee` | `geometry`, `geometry_simplified_communal` |
| `geographies_arrondissements_municipaux` | 45 | `code_insee` | `geometry`, `geometry_simplified_communal` |
| `geographies_circonscriptions` | 559 | `code` | `geometry`, `geometry_simplified_circo` |

### Table des populations

| Table | Lignes | Clé |
|-------|--------|-----|
| `populations` | 34 858 × N millésimes | `(code_insee_commune, annee)` |

Millésimes chargés : 2013, 2018, 2023. Colonne fiable : `population_municipale`.
`comptee_a_part` et `totale` sont NULL (PCAP absent de la source INSEE utilisée).

### Vues d'agrégation

| Vue | Description |
|-----|-------------|
| `v_population_region` | JOIN `communes → populations → regions` GROUP BY `(code_region, annee)` |
| `v_population_departement` | JOIN `communes → populations → departements` GROUP BY `(code_departement, annee)` |
| `v_population_epci` | JOIN `communes → populations → epci` GROUP BY `(code_epci, annee)` |
| `v_population_commune` | Agrégation directe de `populations` GROUP BY `(code_commune, annee)` |

### Tables méta

| Table | Rôle |
|-------|------|
| `_etl_metadata` | Horodatage + `row_count` par entité chargée |
| `_etl_run_log` | Journal des runs ETL (statut, durée, erreurs) |

### Anomalies connues

- **Mayotte** : absente de `v_population_*` (source INSEE séparée, à traiter en v2)
- **Saint-Pierre-et-Miquelon** : 2 communes avec `code_departement = 'NR'`
- **Grand Paris** : 135 communes avec `code_epci` multi-valeur ; 11 EPT sans `code_departement_principal`

## Patterns transverses

### Logging

Centralisé dans `logging_config.configure_logging()`, appelé au démarrage de l'app et
de l'ETL. Contrôlé par deux variables d'environnement :

| Variable | Valeurs | Défaut |
|----------|---------|--------|
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |
| `LOG_FORMAT` | `text`, `json` | `text` |

Le format `json` produit une ligne JSON par record, parseable par Loki / CloudWatch.
Chaque module déclare son propre `logger = logging.getLogger(__name__)`.

### Configuration

Les secrets et paramètres d'environnement sont lus depuis `.env` via `pydantic-settings`.
Le fichier `.env` est gitignored ; `.env.example` documente toutes les variables attendues.
Aucune clé API n'est hardcodée dans le code source.

### Tests

- Framework : `pytest` avec `pytest-cov`
- Couverture cible : ≥ 60 % (configurée dans `pyproject.toml`) — réelle à la Phase D3.2 : **78 %**
- Les fixtures DuckDB utilisent une base in-memory (`:memory:`) — aucune dépendance
  à la base de production dans les tests
- Les ETL loaders sont exclus de la couverture (réseau requis)
- 62 tests de smoke ETL + 9 tests d'intégration électoraux (C4) — total **289 tests** (D3.2)
- Tests `@pytest.mark.slow` (Streamlit headless) exclus par défaut ; lancer avec `pytest -m slow`

### CI (GitHub Actions)

Deux jobs parallèles déclenchés sur chaque push et pull request vers `main` :

| Job | Étapes |
|-----|--------|
| **Lint & Format** | `ruff check .` + `ruff format --check .` |
| **Tests & Coverage** | `pytest --cov` avec upload du rapport HTML + XML |

### Pre-commit

Installé localement via `uv run pre-commit install`. Hooks actifs avant chaque commit :

- `ruff` (lint + autofix) et `ruff-format`
- `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-toml`
- `check-merge-conflict`, `check-added-large-files` (seuil 1 MB)

Les fichiers `.claude/` (skills tiers) sont exclus du périmètre des hooks.

## Décisions structurantes

Les choix d'architecture non triviaux sont documentés sous forme d'ADR :

| ADR | Décision |
|-----|----------|
| [0001](adr/0001-duckdb-vs-postgres.md) | DuckDB plutôt que PostgreSQL |
| [0002](adr/0002-streamlit-vs-fastapi.md) | Streamlit plutôt que FastAPI + frontend JS |
| [0003](adr/0003-uv-vs-pip-poetry.md) | uv plutôt que pip / poetry |
| [0004](adr/0004-polars-vs-pandas.md) | Polars prioritaire, Pandas en fallback |
| [0005](adr/0005-nuances-et-blocs-officiels.md) | Nomenclature officielle Ministère — 6 blocs de clivages |

**Schéma DuckDB électoral** : voir [docs/schema-elections.md](schema-elections.md) — 6 tables, 8 vues d'agrégation, blocs officiels. Phase D3.2 : 5 colonnes municipales ajoutées à `resultats_candidats`, 3 vues muni (`v_scores_commune_muni`, `v_evolution_blocs_hdf_muni`, `v_listes_commune_muni`).

## Pour aller plus loin

- [docs/data-sources.md](data-sources.md) — référence des sources de données (URLs, formats, limitations)
- [docs/guide-utilisateur.md](guide-utilisateur.md) — utilisation de l'application (niveaux, filtres, FAQ)
- [README.md](../README.md) — installation, premier lancement, stack
