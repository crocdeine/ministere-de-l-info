# Outillage Claude Code — équipe d'agents, skills, hook cloud

**Date** : 2026-09-24
**Agent** : outilleur Claude Code (session cloud, worktree isolé)
**Périmètre** : `.claude/` uniquement (aucune modification de `src/`, `pages/`, `scripts/`, `docs/`)
**Base** : `d382354` (HEAD de `main`) + rapport `session-2026-09-24_etat-des-lieux.md`

---

## 1. Équipe de sous-agents (`.claude/agents/`)

Format vérifié sur la documentation officielle (https://code.claude.com/docs/en/sub-agents) :
frontmatter YAML en première ligne (`name`, `description` obligatoires ; `tools`, `skills`,
`color` optionnels), puis prompt système en Markdown. Pas de champ `model` : les agents héritent
du modèle de la session. Chaque définition fait moins de 50 lignes et rappelle les règles critiques
(uv, codes INSEE en `str`, Polars, pas de décision structurante sans Mathias, Conventional Commits,
rapport dans `reports/`).

| Agent | Rôle | Outils | Skills préchargés |
|---|---|---|---|
| `verificateur-code` | Audit de bugs, lecture seule, ruff + pytest | Read, Grep, Glob, Bash | — |
| `chercheur-donnees` | Sources officielles, circulaires, traçabilité juridique | + WebFetch, WebSearch, Write | — |
| `documentaliste` | docs/, README, ADR, rapports, cohérence doc ↔ code | + Edit, Write | — |
| `architecte-restructuration` | Refactor, dette, arborescence (plan → validation → exécution) | + Edit, Write | — |
| `ingenieur-etl` | Loaders, schémas, vues, migrations | + Edit, Write | `projet-conventions`, `insee-duckdb-loader` |
| `developpeur-ui` | Streamlit, design system, Folium, Plotly | + Edit, Write | `streamlit-duckdb-patterns` |
| `ingenieur-infra` | Docker, CI, scripts de déploiement | + Edit, Write, WebFetch | — |
| `outilleur-claude` | Agents, skills, hooks, settings | + Edit, Write, WebFetch | — |

**Utilisation**
- Le directeur de projet délègue par nom : « utilise l'agent `ingenieur-etl` pour… ».
- En CLI : `/agents` liste et édite les agents du projet.
- Le `verificateur-code` n'a pas `Edit`/`Write` : il ne peut rien modifier par construction.
  Ses rapports sont écrits par l'appelant.
- Aucun agent n'a l'outil `Agent` : pas de sous-délégation en cascade.

## 2. Skills mis à jour (`.claude/skills/`)

Tous les faits cités ont été vérifiés dans le code (`etl/schema*.py`, `etl/views.py`,
`scripts/migrations/`, `viz/*_queries.py`, `pages/`, loaders).

### `projet-conventions` (réécrit)
- Noms de tables réels : `geographies_*` (clé `code_insee`), `populations`, `nuances_harmonisees`,
  `blocs_politiques`, `candidats_presidentielle`, `elections`, tables `economie_*` et `leg_*`.
  Supprimés : `communes`, `departements`, `nuances_blocs`, `economie_rp_csp`, `economie_sirene`…
- Liste complète des vues : 4 population, 11 élections (8 dans `schema_elections.py` + 3
  municipales dans la migration 0007), 6 économie, 2 législatif.
- Arborescence réelle : `app.py` routeur `st.navigation`, `pages/4_📊_Économie.py`,
  `_theme.py`, `_blocs_politiques.py`, loaders économie/législatif, `deploy/`.
- Feuille de route Économie retirée (réalisée).
- « Branche `main` uniquement » remplacé par la règle de CLAUDE.md, avec mention de l'écart
  constaté (pas de PR dans l'historique, décision ouverte).
- Marqueur `slow` corrigé : il désigne les tests qui lancent un processus Streamlit, pas les tests
  de base (ceux-ci font `pytest.skip` si la base est absente).
- « Proposer avant chaque commit » remplacé par les points d'arrêt réels de CLAUDE.md ;
  vérification CI adaptée au cloud (outils GitHub MCP, `gh` absent).

### `streamlit-duckdb-patterns` (corrigé)
- Connexion : le pattern réel est `_open_ro()` (read-only + `LOAD spatial`) ouvert dans une
  fonction `@st.cache_data` et fermé dans `finally` ; `@st.cache_resource` seulement dans Géographie.
- Cartes : géométries pré-simplifiées en base + `ST_AsGeoJSON`, table `geographies_communes`,
  clé `code_insee`, filtre `code_region = '32'` (l'ancien exemple interrogeait `communes.geom`).
- Page type : plus de `st.set_page_config` dans les pages (centralisé dans `app.py`), import
  `ministere_de_l_info.pages...` (et non `src.ministere_de_l_info...`), `render_page_header()`.
- Indicateurs réels (`tx_chomage_dec`, `part_ouvriers_employes`…) au lieu de clés inexistantes.
- Croisement économie × élections : décrit tel qu'implémenté (scatter Plotly).

### `insee-duckdb-loader` (corrigé)
- Sources réellement chargées : Parquet OLAP data.gouv (Filosofi 2017-2021, RP 2015-2021) via
  cache HdF, CNAF, DREES, URSSAF, Eurostat. Sirene et BPE signalés comme non utilisés.
- Erreur technique corrigée : `read_parquet(..., nullstr=...)` n'existe pas (`nullstr` = `read_csv`).
- Colonnes réelles (`d1_niveau_vie`, non `niveau_vie_d1`) ; pivot `clef_json` documenté.
- Pattern idempotent réel (`DELETE` + `INSERT`, `upsert_metadata`) au lieu de `CREATE OR REPLACE TABLE`.
- Encodage : latin-1 + `;` rappelé (CLAUDE.md) ; `chardet` retiré (non déclaré dans `pyproject.toml`).
- Tableau des définitions du chômage relié aux colonnes du projet.

### `data-viz-politique`
Non modifié, conformément à la consigne (classements en cours d'instruction).

### Constats factuels relevés au passage (non corrigés, hors périmètre)
- La vue `v_elus_hdf_actuels` ne filtre pas les Hauts-de-France : elle renvoie tous les élus actifs.
  Son nom est trompeur (à signaler à l'agent ETL/documentation).
- La vue `v_croisement_eco_elections` n'est utilisée nulle part (l'UI refait la jointure dans
  `get_croisement_eco_elections()`).
- Constante des départements HdF dupliquée dans chaque loader économie et dans `viz/elections_queries.py`.

## 3. Hook SessionStart pour le cloud

Fichiers : `.claude/settings.json`, `.claude/hooks/session-start.sh` (exécutable).

- Déclenché au démarrage et à la reprise (`matcher: "startup|resume"`), timeout 600 s, synchrone.
- Sort immédiatement si `CLAUDE_CODE_REMOTE` ≠ `true` : **aucun effet sur le Mac**.
- En cloud : `uv sync --frozen --group etl` (mêmes dépendances que la CI, groupe `dev` inclus par
  défaut). Idempotent, silencieux en cas de succès ; en cas d'échec, sortie d'uv sur stderr sans
  bloquer la session (exit 0).

**Tests effectués (conteneur cloud)**

| Test | Résultat |
|---|---|
| `bash -n` (syntaxe) | OK |
| `python3 -m json.tool .claude/settings.json` | OK |
| `CLAUDE_CODE_REMOTE=false` | rc 0, aucun `.venv` créé |
| `CLAUDE_CODE_REMOTE=true` (1er passage) | rc 0, aucune sortie, `.venv` créé (0,16 s, cache uv) |
| Relance | « Audited 87 packages » : idempotent |
| `uv run ruff check app.py` | OK |
| `uv run pytest tests/test_elections_queries.py` | 5 passés, 16 ignorés (base absente) |
| `uv run pytest tests/test_viz_maps.py` | erreurs de setup : extension DuckDB `spatial` bloquée par le proxy (HTTP 403), limite connue |

`shellcheck` n'est pas installé dans le conteneur : non exécuté.
Mode synchrone : la session attend la fin de l'installation (quelques secondes avec cache,
jusqu'à ~1 min à froid). Passage en asynchrone possible si le démarrage paraît lent.
Le hook ne s'applique aux futures sessions cloud qu'une fois fusionné dans la branche par défaut.

## 4. Recommandations (non installées — décision de Mathias)

| Proposition | Gain attendu | Réserve |
|---|---|---|
| **Hook de permissions / `permissions.allow`** dans `settings.json` pour `uv run pytest`, `uv run ruff`, `git status/diff/log` | Moins d'interruptions pour les agents | À cadrer : liste blanche stricte, jamais `git push` |
| **Plugin officiel `security-guidance`** (anthropics/claude-plugins-official) | Revue automatique des diffs : injection SQL via f-string, secrets en dur | Hooks sur chaque édition et à l'arrêt : coût en temps, à tester sur une branche |
| **Plugin LSP Python (Pyright)** du dépôt officiel | Détection des erreurs de type pendant l'édition (type hints obligatoires) | Pyright n'est pas dans la stack : alternative, ajouter `mypy`/`pyright` en CI (décision) |
| **Serveur MCP DuckDB** (ex. `mcp-server-motherduck` en mode fichier local, lecture seule) sur le Mac | Les agents interrogent directement `data/ministere.duckdb` pour vérifier des chiffres | Mac uniquement (pas de base en cloud) ; forcer `read_only` |
| **Serveur MCP data.gouv.fr** (serveur officiel annoncé par data.gouv.fr, à vérifier) | Recherche et métadonnées de datasets pour `chercheur-donnees` | Disponibilité et hébergement à vérifier ; le proxy cloud peut le bloquer |
| **Context7 (MCP)** | Documentation à jour Streamlit ≥ 1.57, Polars, DuckDB 1.5 | Service tiers, requêtes sortantes |
| **Commandes `/debut-session` et `/fin-session`** dans `.claude/commands/` | Automatiser la discipline de mémoire de CLAUDE.md (git log, dernier rapport, proposition de mise à jour) | Faible coût, à rédiger après validation |
| **Hook `Stop` léger** : rappel si des fichiers `src/` ont changé sans rapport dans `reports/` | Renforce la règle « session sans mémoire = incomplète » | Risque de bruit ; commencer par une simple commande |

Non recommandés : plugins de scraping (Bright Data…) — contraires à la règle « sources officielles
uniquement » ; plugins d'analytique SaaS (BigQuery, Snowflake…) — hors stack.

## 5. Suites possibles
- Faire relire les agents par Mathias (ton, périmètres, outils).
- Mettre à jour la section « Pointeurs » de CLAUDE.md pour citer `.claude/agents/` et le hook
  (à faire par le documentaliste, après validation).
