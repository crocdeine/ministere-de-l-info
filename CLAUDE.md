# ministere-de-l-info — Contexte projet

## Vue d'ensemble

Application web locale de data-visualisation politique, électorale, économique et territoriale française.
Utilisateur : Lucas, étudiant BTS NDRC, **débutant en développement**.

Toujours communiquer en français, ton neutre, sans blabla. Co-rédiger plutôt que conseiller.

## Stack technique (NON NÉGOCIABLE)

- **Python 3.12** strict, type hints partout
- **uv** pour la gestion des paquets (jamais pip, jamais poetry)
- **Streamlit** ≥1.57 (framework web)
- **DuckDB** ≥1.5 + extension spatial (base analytique principale)
- **Polars** prioritaire, Pandas en fallback seulement
- **PyArrow** pour Parquet
- **GeoPandas + Folium + streamlit-folium** pour la carto
- **Plotly Express** pour les graphiques (pas matplotlib en web)
- **Pydantic + pydantic-settings** pour la config
- **Tectonic** pour LaTeX (jamais TeX Live)
- **Jinja2** pour le templating LaTeX

## Conventions Python

- Format : `ruff format` (line-length 100)
- Lint : `ruff check`
- Tests : `pytest`
- Imports triés par isort (intégré à ruff)
- Pas de `print()` en code prod, utiliser `logging`
- Docstrings courtes, en français

## Conventions données

- Codes INSEE communes : TOUJOURS en `str` avec zéro padding (5 caractères : `"01001"`, pas `1001`)
- Codes département : `str` 2 ou 3 caractères (`"01"`, `"2A"`, `"971"`)
- Dates : ISO 8601 (`YYYY-MM-DD`)
- Encodage : UTF-8 strict (les CSV INSEE sont souvent en latin-1 avec `;` — convertir à l'import)
- Géométries : EPSG:4326 (WGS84) pour Folium, EPSG:2154 (Lambert-93) pour calculs métriques
- Avant Folium : TOUJOURS `gdf.to_crs(epsg=4326)`

## Conventions Git

- Conventional Commits stricts : `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, `style:`, `perf:`
- Branche par feature, PR squash-merge
- JAMAIS commit `.env`, `data/raw/*`, `data/processed/*`, `*.duckdb`, fichiers >50MB
- Toujours `git status` avant `git add .`

## Sources de données autorisées

- **data.gouv.fr** : `https://www.data.gouv.fr/api/1/` (sans clé pour lecture)
- **API Tabulaire** : `https://tabular-api.data.gouv.fr/api/` (≤100MB CSV)
- **INSEE** : `https://portail-api.insee.fr/` (Melodi sans auth, Sirene/Métadonnées OAuth2)
- **Légifrance** : via PISTE `https://api.piste.gouv.fr/` (OAuth2, accepter CGU)
- **Géographie** : `https://geo.api.gouv.fr/` (sans auth), `https://data.geopf.fr/` (IGN)
- **AN/Sénat** : dumps XML/JSON (data.assemblee-nationale.fr, data.senat.fr)
- **HATVP** : dumps `https://www.hatvp.fr/open-data/`
- **OSM** : Overpass `https://overpass-api.de/api/interpreter`

## Datasets clés (URLs vérifiées)

- Élections agrégées : `https://www.data.gouv.fr/datasets/donnees-des-elections-agregees/`
- RNE (élus) : `https://www.data.gouv.fr/datasets/repertoire-national-des-elus-1/`
- Bureaux de vote : `https://www.data.gouv.fr/datasets/bureaux-de-vote-et-adresses-de-leurs-electeurs/`
- EPCI + contours : `https://www.data.gouv.fr/datasets/communes-cantons-et-epci-2025-admin-express-cog-plus-ign/`
- BANATIC : `https://www.data.gouv.fr/datasets/base-nationale-sur-les-intercommunalites/`

## Pièges à éviter absolument

1. Streamlit relance tout le script à chaque clic → mettre tout chargement lourd dans `@st.cache_data`
2. Connexion DuckDB → `@st.cache_resource` (pas `cache_data`)
3. CSV INSEE = latin-1 + séparateur `;` → toujours préciser à l'import
4. Code INSEE ≠ code postal (Paris commune = `75056`, arrondissements = `75101→75120`)
5. GeoJSON national entier = trop lourd → `gdf.simplify(0.001)` ou pré-simplifier
6. Régions : 22 avant 2016, 13 depuis (loi NOTRe). Préciser l'année.
7. Nuances politiques : codes différents par scrutin → table d'harmonisation `(code, année) → bloc`

## Workflow Claude Code

- **TOUJOURS plan mode** (Shift+Tab) avant toute tâche complexe
- Demander validation utilisateur avant d'écrire le code
- Sub-agents : `data-loader` sur Haiku, viz/analyse sur Sonnet
- Commits atomiques, un commit = une intention
- Tests minimaux mais présents (au moins un test smoke par module)

## Ce qu'il NE FAUT JAMAIS faire

- ❌ Utiliser pip, poetry, conda
- ❌ Commit secrets, `.env`, fichiers >50MB
- ❌ Utiliser pandas si polars suffit
- ❌ Utiliser matplotlib en interface web (sauf export figure rapport)
- ❌ Stocker des géométries en EPSG inconnu
- ❌ Hardcoder une clé API (toujours via `pydantic-settings`)
- ❌ `git push --force` sur main
- ❌ Modifier `data/raw/` manuellement
