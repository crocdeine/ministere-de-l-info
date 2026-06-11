---
name: projet-conventions
description: Conventions complètes du projet ministere-de-l-info. À charger pour toute tâche de développement dans ce projet : nouveau script ETL, nouvelle page Streamlit, nouvelle vue SQL, nouveau test, nouvelle table DuckDB, nouveau loader. Contient le schéma DuckDB existant, la structure des fichiers, les conventions de code, les règles de nommage, la roadmap module Économie.
---

# Conventions projet — ministere-de-l-info

## 1. Stack et outils (NON NÉGOCIABLES)

| Outil | Règle |
|---|---|
| Python | 3.12 strict, type hints partout |
| Gestionnaire paquets | `uv` **uniquement** — jamais pip, jamais poetry, jamais conda |
| Environnement dev | `uv sync --all-groups` |
| Exécution | `uv run <script>` — jamais `python` direct |
| Lint/format | `ruff` via pre-commit (`ruff format` + `ruff check`) |
| Tests | `pytest` avec marqueur `@pytest.mark.slow` pour les tests DB |
| Commits | Conventional Commits stricts : `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, `style:`, `perf:` |
| Branche | `main` uniquement |
| DataFrame | Polars en priorité, Pandas en fallback si Plotly l'exige |

## 2. Structure des fichiers

```
ministere-de-l-info/
│
├── app.py                              # Point d'entrée Streamlit
├── pages/
│   ├── 1_📍_Géographie.py
│   ├── 2_🗳️_Élections.py
│   ├── 3_🏛️_Législatif.py             # Stub
│   └── 4_💶_Économie.py               # Stub → À implémenter phase E
│
├── src/ministere_de_l_info/
│   ├── logging_config.py
│   ├── data_sources/                  # Connecteurs API bas niveau
│   │   ├── geo.py
│   │   ├── circonscriptions.py
│   │   └── insee_populations.py
│   ├── etl/                           # Pipeline de chargement DuckDB
│   │   ├── schema.py                  # Tables géo (7 tables + 2 méta)
│   │   ├── schema_elections.py        # Tables + vues électorales
│   │   ├── views.py                   # Vues population
│   │   ├── _common.py                 # open_connection(), constantes
│   │   └── loaders/                   # Un loader par entité géo
│   ├── pages/                         # Modules de rendu Streamlit (render())
│   │   ├── elections_presidentielles.py
│   │   ├── elections_legislatives.py
│   │   └── elections_municipales.py
│   └── viz/                           # Requêtes DuckDB + carto
│       ├── maps.py
│       ├── maps_elections.py
│       ├── elections_queries.py
│       ├── elections_legi_queries.py
│       ├── elections_muni_queries.py
│       ├── _config.py
│       ├── _display.py
│       └── _queries.py
│
├── scripts/
│   └── etl_territoires.py             # CLI ETL orchestrateur géo
├── tests/                             # 331 tests (coverage 69%)
├── data/
│   └── ministere.duckdb               # gitignored
└── docs/
    ├── architecture.md
    ├── schema-elections.md
    ├── data-sources.md
    ├── deployment.md
    └── adr/                           # 5 ADR (0001→0005)
```

**Règle placement** : jamais de fichier de travail ou test à la racine. Respecter : `src/`, `tests/`, `scripts/`, `docs/`.

## 3. Schéma DuckDB existant

### Tables géographiques (module Géographie — v0.2)

```sql
communes           -- code_commune VARCHAR(5), nom, dep, reg, geom
departements       -- code_dep VARCHAR(3), nom, code_reg, geom
regions            -- code_reg VARCHAR(3), nom, geom
epci               -- code_epci, nom, type, geom
arrondissements_municipaux
circonscriptions   -- 559 circos législatives
populations        -- code_commune, annee, pop (2013/2018/2023)
```

### Tables électorales (module Élections — v0.4)

```sql
resultats_participation   -- (pres + legi + muni) : inscrits, votants, exprimés
resultats_candidats       -- (pres + legi + muni) : candidats, nuances, voix
nuances_blocs             -- 216 mappings nuance → bloc officiel
```

### Vues électorales existantes

```sql
v_scores_commune_pres      -- scores par commune, présidentielles
v_evolution_blocs_hdf_pres -- évolution blocs EXG/GAU/DIV/CENT/DTE/EXD, pres
v_scores_commune_legi      -- scores par commune, législatives
v_scores_commune_muni      -- scores par commune, municipales
v_evolution_blocs_hdf_muni -- évolution blocs, muni
-- + 6 autres vues (voir docs/schema-elections.md)
```

### Tables économiques à créer (Phase E)

```sql
economie_filosofi       -- revenus/pauvreté par commune/an
economie_rp_csp         -- CSP + taux activité/chômage (déclaratif RP)
economie_rp_diplome     -- niveau diplôme par commune/an
economie_sirene         -- tissu entreprises agrégé par commune
v_economie_commune      -- vue agrégée multi-sources (à concevoir)
```

## 4. Conventions de nommage DuckDB

```
Tables  : snake_case, pluriel — resultats_candidats, economie_filosofi
Vues    : préfixe v_ + thème + grain — v_scores_commune_pres, v_economie_commune
Colonnes: snake_case — code_commune, annee, taux_pauvrete
```

Colonnes standards obligatoires :
- `code_commune` : `VARCHAR(5)` — JAMAIS INTEGER
- `annee` : `INTEGER`
- `code_dep` : `VARCHAR(3)`

## 5. Conventions Python

```python
# Longueur de ligne : 100 caractères (ruff)
# Docstrings : courtes, en français
# Pas de print() en code prod → logging

import logging
logger = logging.getLogger(__name__)
logger.info("Message explicite")  # pas print()

# Codes department HdF (constante partagée dans _common.py ou _config.py)
DEPTS_HDF = ("02", "59", "60", "62", "80")
```

## 6. Blocs politiques officiels

6 blocs **officiels** uniquement (ADR-0005, circulaire IOMA2322276J) :

| Code | Libellé |
|---|---|
| `EXG` | Extrême gauche |
| `GAU` | Gauche |
| `DIV` | Divers |
| `CENT` | Centre |
| `DTE` | Droite |
| `EXD` | Extrême droite |

Ne jamais inventer `centre-gauche`, `centre-droit`, `populaire`, etc.

## 7. Points d'arrêt obligatoires (règles CLAUDE.md)

1. **Avant chaque commit** : proposer, attendre validation Mathias
2. **Vérification CI post-push** : après `git push`, exécuter :
   ```bash
   gh run list --limit 3 --json databaseId,headSha,conclusion,displayTitle
   git rev-parse HEAD
   # Comparer headSha — ne jamais conclure "CI verte" sur un run antérieur
   ```
3. **Validation UI** : AppTest ne remplace pas la validation visuelle quand Mathias la demande
4. **Décisions structurantes** : proposer → attendre → créer ADR si validé

## 8. Gotchas techniques fréquents

- **Pre-commit ruff** : le hook reformate les fichiers → toujours `git add` après échec pre-commit, puis nouveau commit (pas `--amend`)
- **DuckDB connexion** : `@st.cache_resource` pour la connexion, `@st.cache_data` pour les DataFrames
- **Streamlit rerun** : tout le script est ré-exécuté à chaque clic → tout chargement lourd doit être dans `@st.cache_data`
- **Géométries** : EPSG:4326 pour Folium, EPSG:2154 (Lambert-93) pour calculs métriques
- **Parquet elections inversé** : `general-results.parquet` = résultats candidats ; `candidats-results.parquet` = participation (voir docs/data-sources.md)

## 9. Roadmap module Économie (Phase E)

Fichiers à créer dans l'ordre :

```
1. scripts/load_economie.py              # ETL INSEE → DuckDB (Filosofi + RP)
2. src/ministere_de_l_info/etl/schema_economie.py  # CREATE TABLE economie_*
3. src/ministere_de_l_info/viz/economie_queries.py # Requêtes @st.cache_data
4. src/ministere_de_l_info/pages/economie.py       # Module render()
5. pages/4_💶_Économie.py               # Page Streamlit (remplace stub)
6. tests/test_economie.py               # Tests d'intégration
```

## 10. Commandes courantes

```bash
uv sync --all-groups          # Installer l'environnement complet
uv run pytest tests/ -x       # Tests en mode fail-fast
uv run pytest tests/ -k "not slow"  # Tests sans DB
uv run streamlit run app.py   # Lancer l'app
git log --oneline -5          # Vérifier état repo
gh run list --limit 3         # Vérifier CI
```
