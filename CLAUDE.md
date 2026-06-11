# ministere-de-l-info — Contexte projet

## Identité

Mathias (GitHub : crocdeine) développe ministere-de-l-info comme projet personnel long terme — un outil professionnel de data-visualisation pour analyses politiques et électorales. Exigence qualité élevée sur tous les modules. N'est pas un développeur professionnel mais maîtrise le pilotage de projet logiciel et la rigueur méthodologique (architecture, sources, traçabilité). Travaille en mode "supervision" avec Claude Code en CLI, via un chat web pour le cadrage stratégique.

**Workflow** : Mathias supervise via un chat Claude (web/app) où sont prises les décisions structurantes (architecture, scope, choix éditoriaux). Claude Code intervient sur le Mac mini M4 (OrbStack) pour l'exécution technique : code, tests, commits, déploiement. Claude Code ne prend pas de décisions structurantes sans validation explicite — il propose, attend, exécute. En fin de tâche significative, il rapporte avec un rapport structuré que Mathias relit en chat.

Toujours communiquer en français, ton neutre, sans blabla.

---

## Discipline de mémoire (lecture/écriture)

**En début de chaque session Claude Code** :
1. `git log --oneline -10` pour voir les commits récents
2. Lire le dernier rapport dans `reports/` pour le contexte de la dernière session
3. Si des écarts apparents existent entre ce CLAUDE.md et l'état réel du repo, le signaler à Mathias avant d'attendre les instructions

**En fin de tâche significative (commit majeur, phase terminée, décision structurante)** :
1. Proposer spontanément la mise à jour de CLAUDE.md (sections concernées)
2. Pour une phase entière qui se termine : créer ou enrichir le rapport `reports/session-YYYY-MM-DD_phase-X-recap.md`
3. Si une nouvelle décision structurante est prise : créer un ADR dans `docs/adr/`

Ces mises à jour ne sont PAS optionnelles : elles font partie du travail. Une session qui ne met pas à jour la mémoire est une session incomplète.

**Points d'arrêt obligatoires** : quand un prompt mentionne explicitement "POINT D'ARRÊT", "ATTENDRE VALIDATION", "STOP", ou équivalent, Claude Code DOIT s'arrêter et attendre la confirmation explicite de Mathias en chat web. Un test automatisé (AppTest, pytest, Streamlit headless) ne remplace pas une validation manuelle quand elle est demandée. Les deux sont complémentaires.

**Vérification CI post-push (règle obligatoire)** : après git push, identifier le run déclenché par ce push :
```bash
gh run list --limit 3 --json databaseId,headSha,conclusion,displayTitle
```
Comparer `headSha` avec `git rev-parse HEAD`. Ne jamais conclure "CI verte" sur un run antérieur.
Leçon D3.3 : run 27265331430 watché au lieu du vrai run du commit 7f21346 — échec CI non détecté pendant 2 commits.

---

## État des modules

| Module | Statut | Tag | Détail |
|--------|--------|-----|--------|
| 📍 Géographie | ✅ Terminé | v0.2 | Régions, dpts, EPCI, communes, arrondissements, circos. Population 2013/2018/2023. |
| 🗳️ Élections | ✅ Phase D complète (pres+legi+muni 2002-2026) | v0.4-elections-complet | Présidentielles 2002-2022, Législatives 2002-2024, Municipales 2008-2026, HdF. Drill-down BV. 30 scrutins, 11 vues SQL, 216 mappings nuances, méthodologie tracée (ADR-0005). |
| 🚀 Déploiement | ✅ v0.4.3 (Mac/OrbStack, testé) | — | install.sh validé sur macOS 26.4.1. Image sur ghcr.io. DB sur GitHub Release. TODO : update.sh test réel, page Paramètres UI. |
| 📊 Économie | 🔄 Phase E en cours | — | 5 rapports Antigravity, ADR-0006, 3 skills. Sources : Filosofi + RP + Sirene. 5 indicateurs. ETL en cours. |

**Dernier rapport** : `docs/adr/0006-module-economie-sources-et-schema.md` — décisions architecture module Économie (sources, indicateurs, schéma DuckDB)

---

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

---

## Décisions structurantes (ADR)

Toute décision d'architecture non triviale est documentée dans `docs/adr/`. Ne pas contourner ces choix sans créer un ADR de révision.

| ADR | Décision | Résumé |
|-----|----------|--------|
| [0001](docs/adr/0001-duckdb-vs-postgres.md) | DuckDB ≠ PostgreSQL | Analytique in-process, pas de serveur, fichier unique. |
| [0002](docs/adr/0002-streamlit-vs-fastapi.md) | Streamlit ≠ FastAPI+JS | Pages interactives sans JavaScript, un seul langage. |
| [0003](docs/adr/0003-uv-vs-pip-poetry.md) | uv ≠ pip/poetry | Lock file reproductible, CI rapide, API moderne. |
| [0004](docs/adr/0004-polars-vs-pandas.md) | Polars > Pandas | Colonnaire, expressions paresseuses, API stricte. |
| [0005](docs/adr/0005-nuances-et-blocs-officiels.md) | Nomenclature officielle Ministère | 6 blocs officiels (EXG/GAU/DIV/CENT/DTE/EXD), classement "de l'époque", sources tracées. |
| [0006](docs/adr/0006-module-economie-sources-et-schema.md) | Module Économie — sources et schéma | Filosofi + RP + Sirene, 5 indicateurs, 2 tables, 3 vues, pièges ETL INSEE. |

---

## Conventions Python

- Format : `ruff format` (line-length 100)
- Lint : `ruff check`
- Tests : `pytest`
- Imports triés par isort (intégré à ruff)
- Pas de `print()` en code prod, utiliser `logging`
- Docstrings courtes, en français

---

## Conventions données

- Codes INSEE communes : TOUJOURS en `str` avec zéro padding (5 caractères : `"01001"`, pas `1001`)
- Codes département : `str` 2 ou 3 caractères (`"01"`, `"2A"`, `"971"`)
- Dates : ISO 8601 (`YYYY-MM-DD`)
- Encodage : UTF-8 strict (les CSV INSEE sont souvent en latin-1 avec `;` — convertir à l'import)
- Géométries : EPSG:4326 (WGS84) pour Folium, EPSG:2154 (Lambert-93) pour calculs métriques
- Avant Folium : TOUJOURS `gdf.to_crs(epsg=4326)`
- Identifiants élections : `{YYYY}_{type}_t{N}` — ex. `2022_pres_t1`, `2024_legi_t2`
- Blocs politiques : codes 3-4 caractères issus des circulaires officielles (voir ADR-0005)

---

## Conventions Git

- Conventional Commits stricts : `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, `style:`, `perf:`
- Branche par feature, PR squash-merge
- JAMAIS commit `.env`, `data/raw/*`, `data/processed/*`, `*.duckdb`, fichiers >50MB
- Toujours `git status` avant `git add .`

---

## Gotchas critiques

### Streamlit / DuckDB
1. Streamlit relance tout le script à chaque clic → mettre tout chargement lourd dans `@st.cache_data`
2. Connexion DuckDB → `@st.cache_resource` (pas `cache_data`)
3. CSV INSEE = latin-1 + séparateur `;` → toujours préciser à l'import
4. Code INSEE ≠ code postal (Paris commune = `75056`, arrondissements = `75101→75120`)
5. GeoJSON national entier = trop lourd → `gdf.simplify(0.001)` ou pré-simplifier
6. Régions : 22 avant 2016, 13 depuis (loi NOTRe 2015). Préciser l'année.
7. Nuances politiques : codes différents par scrutin → table d'harmonisation `(nuance, annee) → bloc`

### Données électorales (data.gouv.fr Parquet)
8. **Nommage Parquet inversé** : `general-results.parquet` = résultats candidats ; `candidats-results.parquet` = participation. Ne pas se fier aux noms de fichiers, utiliser les noms de tables DuckDB. (→ `docs/data-sources.md`)
9. **Nuances NULL** : colonne `nuance` = NULL pour présidentielles 2017/2022 et européennes 2019. Résolution via table `candidats_presidentielle` (jointure sur `nom`). (→ `docs/schema-elections.md`)
10. **Codes circo sur le web peu fiables** : les listes de communes par circonscription trouvées sur le web sont souvent erronées. Toujours valider par jointure spatiale `ST_Within` sur `geographies_circonscriptions`.
11. **Blocs officiels depuis 2023 seulement** : le regroupement en blocs de clivages n'existe officiellement que depuis la circulaire IOMA2322276J (sénatoriales 2023). Pour les scrutins antérieurs, reconstruction selon logique officielle datée (voir ADR-0005).

### Infra Docker
12. **Dev vs prod** : le compose dev (`docker-compose.yml`) monte `./data:/app/data:ro` (bind mount — DB locale visible immédiatement). Le compose prod (`docker-compose.prod.yml`) utilise un named volume (`duckdb-data`). Ne pas confondre les deux.
13. **Named volumes isolent du host** : si on revient à un named volume, les scripts ETL écrits sur l'hôte ne sont pas visibles dans le container. Préférer bind mounts en dev.

### Workflow Claude Code
14. **Pre-commit ruff reformate les fichiers** : après un échec pre-commit pour reformatage, les fichiers sont modifiés par le hook. Il faut les re-stager (`git add`) avant de relancer le commit — `--amend` ne suffit pas, créer un nouveau commit.

---

## Sources de données autorisées

- **data.gouv.fr** : `https://www.data.gouv.fr/api/1/` (sans clé pour lecture)
- **API Tabulaire** : `https://tabular-api.data.gouv.fr/api/` (≤100MB CSV)
- **INSEE** : `https://portail-api.insee.fr/` (Mélodi sans auth, Sirene/Métadonnées OAuth2)
- **Légifrance** : via PISTE `https://api.piste.gouv.fr/` (OAuth2, accepter CGU)
- **Géographie** : `https://geo.api.gouv.fr/` (sans auth), `https://data.geopf.fr/` (IGN)
- **AN/Sénat** : dumps XML/JSON (data.assemblee-nationale.fr, data.senat.fr)
- **HATVP** : dumps `https://www.hatvp.fr/open-data/`
- **OSM** : Overpass `https://overpass-api.de/api/interpreter`

**Datasets clés (URLs vérifiées)** :

- Élections agrégées : `https://www.data.gouv.fr/datasets/donnees-des-elections-agregees/`
- RNE (élus) : `https://www.data.gouv.fr/datasets/repertoire-national-des-elus-1/`
- Bureaux de vote : `https://www.data.gouv.fr/datasets/bureaux-de-vote-et-adresses-de-leurs-electeurs/`
- EPCI + contours : `https://www.data.gouv.fr/datasets/communes-cantons-et-epci-2025-admin-express-cog-plus-ign/`
- BANATIC : `https://www.data.gouv.fr/datasets/base-nationale-sur-les-intercommunalites/`

---

## Ce qu'il NE FAUT JAMAIS faire

- ❌ Utiliser pip, poetry, conda
- ❌ Commit secrets, `.env`, fichiers >50MB
- ❌ Utiliser pandas si polars suffit
- ❌ Utiliser matplotlib en interface web (sauf export figure rapport)
- ❌ Stocker des géométries en EPSG inconnu
- ❌ Hardcoder une clé API (toujours via `pydantic-settings`)
- ❌ `git push --force` sur main
- ❌ Modifier `data/raw/` manuellement
- ❌ Décision structurante sans validation Mathias (proposer, attendre, puis exécuter)

---

## Pointeurs vers la documentation

| Fichier | Ce qu'on y trouve |
|---------|-------------------|
| `docs/architecture.md` | Structure du code, flux ETL géographie, schéma DuckDB géo, CI, tests |
| `docs/schema-elections.md` | 6 tables électorales, 5 vues, 4 pièges Parquet, classements blocs détaillés |
| `docs/data-sources.md` | Toutes les sources (IGN, INSEE, circos, Parquet élections), formats, limitations |
| `docs/deployment.md` | Docker dev/prod, backups launchd, DB GitHub Releases, troubleshooting |
| `docs/adr/` | 5 ADR — décisions d'architecture non réversibles sans consensus |
| `docs/sources-officielles/nuances/index.md` | 4 circulaires Ministère archivées + 3 décisions Conseil d'État |
| `docs/lessons-learned.md` | Leçons techniques consolidées par thème (data, infra, workflow) |
| `reports/` | Récaps chronologiques par phase (A, B, C...) — historique complet |
