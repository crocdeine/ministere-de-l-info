# Architecture — ministere-de-l-info

Dernière mise à jour : 2026-09-24 (état du dépôt au commit `d382354`, clôture du
chantier design system).

## Vue d'ensemble

Ministère de l'Info est une application web locale de data-visualisation politique,
électorale et territoriale française. Elle s'adresse à un utilisateur unique sur sa
machine, sans accès concurrentiel ni besoin d'API REST publique. L'ensemble de la
persistance tient dans un fichier DuckDB unique (`data/ministere.duckdb`) alimenté
par des scripts ETL Python qui interrogent des sources officielles ou publiques.

Quatre modules de données + une page d'accueil :

| Module | Périmètre chargé | ETL | UI |
|--------|------------------|-----|----|
| Géographie | France | `scripts/etl_territoires.py` | `pages/1_📍_Géographie.py` (code dans la page) |
| Élections | Hauts-de-France | `scripts/init_elections_schema.py`, `scripts/load_elections_*.py`, `scripts/migrations/` | `pages/2_🗳️_Élections.py` → `src/.../pages/elections_*.py` |
| Législatif | France | `scripts/load_legislatif.py` | `pages/3_🏛️_Législatif.py` → `src/.../pages/legislatif.py` |
| Économie | Hauts-de-France (+ contexte régional/national Eurostat) | `scripts/load_economie.py` | `pages/4_📊_Économie.py` → `src/.../pages/economie.py` |

## Stack technique

| Composant | Technologie | Version min (`pyproject.toml`) | Rôle |
|-----------|-------------|-------------|------|
| Langage | Python | 3.12 | Typage strict, syntaxe moderne |
| Gestionnaire de paquets | uv | — | Lock file reproductible, CI rapide |
| Interface web | Streamlit | ≥ 1.57 | Pages interactives, navigation `st.navigation()` |
| Base analytique | DuckDB + spatial | ≥ 1.5.2 | SQL analytique + géométries in-process |
| Traitement tabulaire | Polars | ≥ 1.40 | Traitement colonnaire (Pandas en fallback : Folium, XLSX, TSV) |
| Cartographie | Folium · streamlit-folium | ≥ 0.20 · ≥ 0.27 | Rendu Leaflet interactif |
| Géométries (ETL) | GeoPandas | ≥ 1.1 (groupe `etl`) | Traitement des GeoJSON au chargement |
| Graphiques | Plotly Express | ≥ 6.7 | Graphiques interactifs web |
| HTTP | httpx | ≥ 0.28 | Téléchargement des sources |
| Configuration | pydantic-settings | ≥ 2.14 | Variables d'environnement typées |
| Lint / format | ruff | ≥ 0.15 | Lint + format, cible py312, longueur 100 |

Groupes de dépendances : `dev` (pytest, pytest-cov, pre-commit, ruff, requests), `etl`
(geopandas, openpyxl), `ai` (anthropic, sans usage dans le code à ce jour). Jinja2 est
déclaré mais la génération de rapports PDF (LaTeX/Tectonic) n'est pas implémentée ;
`src/ministere_de_l_info/config/` et `rapports/` ne contiennent qu'un `.gitkeep`.

## Structure des modules

```
ministere-de-l-info/
│
├── app.py                          # Routeur : configure_logging(), set_page_config(),
│                                   #   inject_css(), puis st.navigation([5 × st.Page]).run()
├── pages/                          # Pages enregistrées par st.Page (plus de découverte automatique)
│   ├── 0_🏠_Accueil.py              # Hub : 4 tuiles st.page_link + expander diagnostic technique
│   ├── 1_📍_Géographie.py           # Carte choroplèthe multi-niveaux (logique dans la page)
│   ├── 2_🗳️_Élections.py            # st.tabs Présidentielles / Législatives / Municipales
│   ├── 3_🏛️_Législatif.py           # Wrapper : pages.legislatif.render()
│   └── 4_📊_Économie.py             # Wrapper : pages.economie.render()
│
├── src/ministere_de_l_info/
│   ├── _theme.py                   # inject_css() (polices Google Fonts + custom.css),
│   │                               #   render_page_header(icon, title, subtitle)
│   ├── _blocs_politiques.py        # BLOCS_ORDERED, COULEURS_BLOCS, LIBELLES_BLOCS (6 blocs)
│   ├── custom.css                  # Tokens du design system + sélecteurs data-testid Streamlit
│   ├── logging_config.py           # configure_logging() : LOG_LEVEL + LOG_FORMAT
│   │
│   ├── data_sources/               # Connecteurs bas niveau (géographie)
│   │   ├── geo.py                  # WFS IGN ADMIN-EXPRESS (régions, dpts, EPCI, communes…)
│   │   ├── circonscriptions.py     # data.gouv.fr — 559 circonscriptions législatives
│   │   └── insee_populations.py    # INSEE Mélodi DS_POPULATIONS_HISTORIQUES
│   │
│   ├── etl/
│   │   ├── _common.py              # open_connection(), upsert_metadata()
│   │   ├── schema.py               # Tables géographiques + _etl_metadata + _schema_version
│   │   ├── views.py                # v_population_{region,departement,epci,commune}
│   │   ├── schema_elections.py     # Tables électorales + 8 vues (présidentielles, législatives)
│   │   ├── schema_economie.py      # 5 tables + 6 vues Économie
│   │   ├── schema_legislatif.py    # 3 tables + 2 vues Législatif
│   │   └── loaders/
│   │       ├── regions.py, departements.py, epci.py, communes.py,
│   │       │   arrondissements_municipaux.py, circonscriptions.py, populations.py
│   │       ├── _http_retry.py
│   │       ├── economie_filosofi.py    # Dataset OLAP data.gouv → economie_filosofi
│   │       ├── economie_rp.py          # Dataset OLAP data.gouv → economie_rp
│   │       ├── economie_cnaf.py        # CNAF RSA → economie_social
│   │       ├── economie_drees.py       # DREES APL → economie_social (upsert)
│   │       ├── economie_urssaf.py      # URSSAF → economie_emploi_urssaf
│   │       ├── economie_eurostat.py    # Eurostat SDMX → economie_contexte
│   │       ├── legislatif_senat.py     # data.senat.fr ODSEN_GENERAL → leg_elus
│   │       ├── legislatif_datan.py     # Datan (data.gouv.fr) → leg_elus + leg_activite
│   │       ├── legislatif_overrides.py # Corrections manuelles → leg_blocs_override
│   │       ├── legislatif_nosdeputes.py  # Source abandonnée (non appelée)
│   │       └── legislatif_clair.py       # Source abandonnée (non appelée)
│   │
│   ├── pages/                      # render() appelés par les fichiers de pages/
│   │   ├── elections_presidentielles.py  # 2002-2022, zone circo 21 ou HdF, drill-down BV
│   │   ├── elections_legislatives.py     # 2002-2024, vue HdF ou circonscription, drill-down BV
│   │   ├── elections_municipales.py      # 2008-2026, bloc dominant, drill-down listes
│   │   ├── legislatif.py                 # Filtres sidebar + 4 onglets
│   │   └── economie.py                   # 4 onglets
│   │
│   └── viz/                        # Cartes et requêtes cachées
│       ├── maps.py                 # make_choropleth() — Géographie
│       ├── maps_elections.py       # Cartes électorales Folium
│       ├── elections_queries.py    # Requêtes présidentielles (+ DB_PATH)
│       ├── elections_legi_queries.py
│       ├── elections_muni_queries.py
│       ├── legislatif_queries.py   # 10 fonctions de requêtes (rapport Phase F)
│       ├── economie_queries.py     # Requêtes Économie, liste blanche d'indicateurs
│       ├── _config.py              # Constantes : tables, colonnes, géométries, filtres
│       ├── _display.py             # Palettes choroplèthes, formatters, légende HTML
│       └── _queries.py             # Builders SQL DuckDB + helpers géométriques
│
├── scripts/
│   ├── etl_territoires.py          # ETL géographie + populations
│   ├── etl_regions.py              # Ancien ETL régions (suppression en attente)
│   ├── init_elections_schema.py    # Schéma électoral + tables de référence
│   ├── load_elections_{presidentielles,legislatives,municipales}.py
│   ├── migrations/                 # 0006 schéma municipales, 0007 vues municipales
│   ├── load_economie.py            # --source filosofi|rp|cnaf|urssaf|drees|social|eurostat|all
│   ├── load_legislatif.py          # --source senat|datan|overrides|all
│   ├── backup_db.sh, publish_db.sh, download_db.sh
│   └── com.crocdeine.ministere-info.backup.plist   # launchd (backup quotidien)
│
├── deploy/                         # Dockerfile de l'image GHCR, compose, install.sh, update.sh
├── Dockerfile, docker-compose.yml, docker-compose.prod.yml   # Build et compose locaux
├── .streamlit/config.toml          # Thème clair aligné sur le design system
├── tests/                          # Suite pytest (voir § Tests)
└── data/                           # ministere.duckdb + raw/ (caches) — non versionné
```

## Navigation et thème

`app.py` est le seul script exécuté par Streamlit à chaque interaction. Il configure la
page (`page_title`, favicon Material `flag`, `layout="wide"`), injecte le CSS une fois,
puis déclare les pages :

| Page | Icône | URL |
|------|-------|-----|
| Accueil (défaut) | `:material/home:` | `/accueil` |
| Géographie | `:material/map:` | `/geographie` |
| Élections | `:material/how_to_vote:` | `/elections` |
| Législatif | `:material/account_balance:` | `/legislatif` |
| Économie | `:material/bar_chart:` | `/economie` |

Les fichiers de `pages/` n'appellent ni `set_page_config` ni `inject_css`. Les titres
sont rendus par `render_page_header()`. Filtres : sidebar pour les filtres qui
s'appliquent à toute la page (Géographie, Législatif), inline pour les sélecteurs
propres à un onglet (Élections, Économie). Décision : [ADR-0009](adr/0009-design-system-et-navigation.md).

## Flux ETL

```
Sources                                   ETL                               DuckDB
───────                                   ───                               ──────
data.geopf.fr (WFS IGN) ─┐
data.gouv.fr (circos)   ─┼─ data_sources/* ─ etl/loaders/* ─ etl_territoires.py ─► geographies_*, populations, v_population_*
INSEE Mélodi            ─┘

data.gouv.fr (Parquet élections) ─ load_elections_*.py ─────────────────────► resultats_*, nuances_harmonisees, v_* électorales

data.gouv.fr (OLAP Filosofi + RP) ─┐
data.caf.fr (CNAF)                 ├─ loaders/economie_* ─ load_economie.py ──► economie_*, v_* économie
DREES, open.urssaf.fr, Eurostat    ─┘

data.senat.fr, Datan (data.gouv.fr) ─ loaders/legislatif_* ─ load_legislatif.py ► leg_*, v_elus_hdf_actuels, v_activite_par_bloc

                                           ▼
                                   ministere.duckdb ──► viz/*_queries.py (@st.cache_data) ──► pages ──► navigateur
```

Les caches bruts sont stockés sous `data/raw/` (ex. `data/raw/economie/`) ; l'option
`--force` des scripts les retélécharge.

## Schéma de la base DuckDB

### Géographie

| Table | Lignes | Clé | Géométries |
|-------|--------|-----|------------|
| `geographies_regions` | 18 | `code_insee` | `geometry`, `geometry_simplified_national`, `geometry_simplified_regional` |
| `geographies_departements` | 101 | `code_insee` | `geometry`, `geometry_simplified_national`, `geometry_simplified_departemental` |
| `geographies_epci` | 1 265 | `code_siren` | `geometry`, `geometry_simplified_epci` |
| `geographies_communes` | 34 877 | `code_insee` | `geometry`, `geometry_simplified_communal` |
| `geographies_arrondissements_municipaux` | 45 | `code_insee` | `geometry`, `geometry_simplified_communal` |
| `geographies_circonscriptions` | 559 | `code` | `geometry`, `geometry_simplified_circo` |
| `populations` | 34 858 × 3 millésimes | `(code_insee_commune, annee)` | — |

Millésimes de population : 2013, 2018, 2023. Colonne fiable : `population_municipale`
(`comptee_a_part` et `totale` NULL). Vues : `v_population_region`,
`v_population_departement`, `v_population_epci`, `v_population_commune`.

Tables méta : `_etl_metadata` (horodatage, version de source, `row_count` par table),
`_schema_version`.

### Élections

Détail complet : [schema-elections.md](schema-elections.md). Tables `elections`,
`resultats_participation`, `resultats_candidats`, `blocs_politiques`,
`nuances_harmonisees`, `candidats_presidentielle`. Onze vues : 8 créées par
`schema_elections.py` (`v_resultats_candidats_avec_bloc`, `v_scores_circo21_pres`,
`v_evolution_blocs_circo21`, `v_scores_commune_pres`, `v_participation_commune_pres`,
`v_scores_circo_legi`, `v_participation_circo_legi`, `v_evolution_blocs_hdf_legi`) et 3
par la migration `0007` (`v_scores_commune_muni`, `v_evolution_blocs_hdf_muni`,
`v_listes_commune_muni`). Volumes (rapport Phase D) : 30 scrutins, 162 469 lignes de
participation, 1 093 836 lignes candidats, 216 mappings de nuances.

### Économie

Définie dans `etl/schema_economie.py` (ADR-0006 et ADR-0008). Filtre HdF au chargement.

| Table | Clé | Contenu | Volume (rapports E, E+, E++) |
|-------|-----|---------|--------|
| `economie_filosofi` | `(code_commune, annee)` | Taux de pauvreté, niveau de vie médian, D1, D9, `secret` | 17 582 (2017-2021) |
| `economie_rp` | `(code_commune, annee_millesime)` | Chômage déclaratif, part ouvriers/employés, part emploi industriel, logements sociaux, `pop_active`, `secret` | 26 538 (2015-2021) |
| `economie_social` | `(code_commune, annee)` | Foyers RSA, taux RSA, APL médecins, `desert_medical` | RSA 17 381 (2020-2024) ; APL 3 788 (2023) |
| `economie_emploi_urssaf` | `(code_commune, annee, code_ape)` | Salariés et établissements par grand secteur et APE | 1 157 338 (2006-2025) |
| `economie_contexte` | `(code_geo, annee, indicateur)` | Chômage BIT, PIB/hab, `FRE` et `FR` | 104 |

Vues : `v_economie_commune`, `v_croisement_eco_elections` (économie de l'année n-1 ×
présidentielles), `v_evolution_economie_hdf`, `v_economie_sociale_commune`,
`v_desindustrialisation_commune`, `v_contexte_hdf_vs_france`.

### Législatif

Défini dans `etl/schema_legislatif.py` (ADR-0007). Chargé pour la France entière.

| Table | Clé | Contenu | Volume (rapport F) |
|-------|-----|---------|--------|
| `leg_elus` | `(id, chambre)` | Identité, département, groupe, `bloc_politique`, `est_actif`, profession, source | 4 065 (2 120 AN + 1 945 Sénat) |
| `leg_activite` | `(elu_id, chambre, date_extraction)` | Compteurs et scores Datan (AN uniquement) | 1 653 |
| `leg_blocs_override` | `(elu_id, chambre)` | Bloc forcé + justification | 2 |

Vues : `v_elus_hdf_actuels` (élus actifs, `bloc_final` = override sinon bloc dérivé —
nationale malgré son nom), `v_activite_par_bloc`.

### Anomalies connues

- **Mayotte** : absente de `v_population_*` (source INSEE séparée).
- **Saint-Pierre-et-Miquelon** : 2 communes avec `code_departement = 'NR'`.
- **Grand Paris** : 135 communes avec `code_epci` multi-valeur ; 11 EPT sans `code_departement_principal`.
- **Municipales 2008** : Nord quasi absent du fichier source (2 communes).
- **Législatif** : `region_nom` NULL pour les députés ; sénateurs de circonscriptions historiques codés `XX`.

## Patterns transverses

### Accès à la base depuis l'UI

- Connexions DuckDB en lecture seule (`read_only=True`). Géographie utilise une
  connexion `@st.cache_resource` ; les modules `viz/*_queries.py` ouvrent/ferment une
  connexion par fonction et mettent le résultat en `@st.cache_data` (TTL 3600 s pour
  Économie).
- Paramètres SQL passés par `?` ; les noms de colonnes dynamiques sont validés contre
  une liste blanche (`frozenset`) avant interpolation (Économie, Législatif).
- Chaque page vérifie la présence des données et affiche la commande ETL à lancer si
  elles manquent.

### Logging

Centralisé dans `logging_config.configure_logging()`, appelé par `app.py` et par
chaque script ETL.

| Variable | Valeurs | Défaut |
|----------|---------|--------|
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |
| `LOG_FORMAT` | `text`, `json` | `text` |

Chaque module déclare `logger = logging.getLogger(__name__)`.

### Configuration

Les secrets et paramètres d'environnement sont lus depuis `.env` (gitignored) ;
`.env.example` documente les variables attendues. Aucune clé API n'est hardcodée.

`ministere_de_l_info.config` (pydantic-settings) centralise les paramètres :
`get_settings().db_path` donne le chemin de la base, lu depuis `MINISTERE_DB_PATH`
(environnement puis `.env`), par défaut `<racine du projet>/data/ministere.duckdb`.
La racine est trouvée en remontant jusqu'au `pyproject.toml` du projet (pas de
dépendance à une installation éditable). ETL, requêtes, pages et scripts l'utilisent.

### Tests

- Framework : `pytest` + `pytest-cov`, seuil `--cov-fail-under=38` dans `pyproject.toml`
  (39,8 % mesurés le 2026-09-24 sans réseau, sans base ni extension spatial).
- 442 tests collectés (2026-09-24), dont 13 marqués `slow` (Streamlit headless et AppTest)
  et 16 marqués `network`, exclus par défaut : `uv run pytest` en sélectionne 413 ;
  `uv run pytest -m slow` lance les tests `slow`.
- Les tests d'intégration ouvrent `data/ministere.duckdb` en lecture seule et sont
  ignorés (`pytest.skip`) si la base est absente — c'est le cas en CI.
- Les tests qui appellent des API réelles (IGN, INSEE Mélodi, data.gouv.fr) portent le
  marqueur `network` et sont exclus par défaut (`-m "not slow and not network"`) ;
  `uv run pytest -m network --no-cov` les lance.
- Les tests qui exigent l'extension DuckDB `spatial` portent le marqueur `spatial` et
  sont ignorés proprement si elle n'est pas installée (`tests/conftest.py`).
- Base échantillon : `scripts/export_sample_db.py` (sur le Mac) exporte la Somme (80)
  en Parquet dans `tests/fixtures/sample/` ; `tests/fixtures/sample_db.py` reconstruit
  une base avec les fonctions de schéma du projet (fixtures `echantillon_con`,
  `echantillon_db_path`). Sans Parquet, les tests concernés sont ignorés.
- Exclus de la couverture (`[tool.coverage.run] omit`) : loaders ETL, `schema.py`,
  `schema_economie.py`, `schema_legislatif.py`, `views.py`, `_common.py`, les modules
  de pages Élections/Économie/Législatif et `elections_muni_queries.py`,
  `economie_queries.py`, `legislatif_queries.py`.
- Couverture : ~60 % en CI (sans base) ; 75,34 % mesurés avec la base locale en Phase E
  (rapport 2026-06-12), valeur reprise à l'identique dans le rapport Phase F.

| Fichier | Périmètre |
|---------|-----------|
| `test_etl_territoires.py`, `test_etl_smoke.py`, `test_etl_regions.py`, `test_fetch_admin_express.py` | ETL géographie, intégrité de la base |
| `test_insee_populations.py`, `test_circonscriptions.py` | Connecteurs INSEE et circonscriptions |
| `test_viz_maps.py`, `test_pages_geographie.py` | Carte Géographie |
| `test_elections_*.py`, `test_pages_legislatives.py`, `test_pages_municipales.py` | Données, vues et requêtes électorales |
| `test_economie.py` | Module Économie |
| `test_legislatif.py` | Module Législatif |
| `test_streamlit_smoke.py` | Démarrage de `app.py` (santé HTTP) + AppTest sur la page Élections (`slow`) |
| `test_config.py`, `test_sample_db.py` | Configuration centralisée, base échantillon et son export |

### CI (GitHub Actions)

`ci.yml` — déclenché sur push vers `main` et `claude/**` et sur pull request vers
`main` ; un seul run actif par ref (`concurrency`, annulation du précédent) :

| Job | Étapes |
|-----|--------|
| **Lint & Format** | `ruff check .` + `ruff format --check .` |
| **Tests & Coverage** | `uv sync --frozen --group etl`, extension `spatial` installée (cache `~/.duckdb/extensions`), `pytest` avec rapport de couverture en artefact |
| **Typage** | `uvx pyright@1.1.408` en mode `basic`, non bloquant (`continue-on-error`) |

`docker-publish.yml` — construit et publie l'image multi-architecture sur GHCR à chaque
tag `v*`, à partir de `deploy/Dockerfile`.

### Pre-commit

Hooks : `ruff` (`--fix`), `ruff-format`, `trailing-whitespace`, `end-of-file-fixer`,
`check-yaml`, `check-toml`, `check-merge-conflict`, `check-added-large-files`
(1 000 Ko, PDF exclus). Le dossier `.claude/` est exclu.

## Décisions structurantes

| ADR | Décision |
|-----|----------|
| [0001](adr/0001-duckdb-vs-postgres.md) | DuckDB plutôt que PostgreSQL |
| [0002](adr/0002-streamlit-vs-fastapi.md) | Streamlit plutôt que FastAPI + frontend JS |
| [0003](adr/0003-uv-vs-pip-poetry.md) | uv plutôt que pip / poetry |
| [0004](adr/0004-polars-vs-pandas.md) | Polars prioritaire, Pandas en fallback |
| [0005](adr/0005-nuances-et-blocs-officiels.md) | Nomenclature officielle Ministère — 6 blocs de clivages |
| [0006](adr/0006-module-economie-sources-et-schema.md) | Module Économie — sources, indicateurs, schéma |
| [0007](adr/0007-module-legislatif-perimetre-et-sources.md) | Module Législatif — périmètre national, Datan + data.senat.fr |
| [0008](adr/0008-economie-sources-complementaires.md) | Économie — sources complémentaires CNAF, DREES, URSSAF, Eurostat |
| [0009](adr/0009-design-system-et-navigation.md) | Design system et navigation `st.navigation()` |

## Déploiement

L'app est distribuée sous forme d'image Docker publiée sur GitHub Container Registry
(`ghcr.io/crocdeine/ministere-de-l-info`), construite par `docker-publish.yml` à partir
de `deploy/Dockerfile` à chaque tag `v*`, multi-architecture (arm64 + amd64).
La base est distribuée séparément, en asset de release GitHub (`ministere.duckdb.gz`
+ `.sha256`). Dernière release : `v0.5-economie-legislatif` (2026-06-28), antérieure au
chantier design system.

Deux Dockerfiles coexistent : `Dockerfile` à la racine (compose local dev/prod) et
`deploy/Dockerfile` (image publiée) ; ils ne sont pas identiques (voir
`reports/session-2026-09-24_etat-des-lieux.md` § 3.4).

Installation utilisateur (macOS 13+, OrbStack) :
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/crocdeine/ministere-de-l-info/main/deploy/install.sh)
```

Guides : `deploy/README-deploy.md` (mainteneur, installation, mise à jour) et
[deployment.md](deployment.md) (compose, backups, dépannage).

## Pour aller plus loin

- [data-sources.md](data-sources.md) — sources de données (URLs, formats, limitations)
- [guide-utilisateur.md](guide-utilisateur.md) — utilisation de l'application
- [lessons-learned.md](lessons-learned.md) — leçons techniques
- [README.md](../README.md) — installation, premier lancement
