# Proposition — CLAUDE.md allégé

**Date** : 2026-09-24 — **Agent** : outilleur-claude — **Statut** : PROPOSITION, non appliquée
(CLAUDE.md hors périmètre de l'agent ; application par le directeur).

## Résumé exécutif

1. CLAUDE.md actuel : 199 lignes, 16 771 octets (≈ 4 800 tokens), injecté dans **chaque** session et **chaque** sous-agent.
2. Version proposée : 96 lignes, 5 215 octets injectés (≈ 1 500 tokens), soit **−69 %**.
3. Aucune règle supprimée : toutes les règles impératives restent (gouvernance, mémoire, points d'arrêt, CI, stack, conventions, interdits).
4. Déplacé : tableau des modules (→ `README.md` § Modules, déjà à jour), gotchas par domaine (→ 3 fichiers `.claude/rules/` à portée de chemin), sources et datasets (→ `docs/data-sources.md`).
5. Mécanismes vérifiés dans la doc officielle : `.claude/rules/` avec `paths` (chargés seulement à la lecture de fichiers correspondants) ; commentaires HTML de bloc retirés avant injection ; cible officielle « moins de 200 lignes ».
6. Prérequis avant application : compléter `docs/data-sources.md` (§ 4) — tâche du documentaliste.
7. Incohérence relevée (non tranchée) : gotcha 2 « connexion DuckDB → `@st.cache_resource` » contredit le code (question Q1).
8. Application : remplacer CLAUDE.md par le § 2, créer les 3 fichiers du § 3, commit `docs: alléger CLAUDE.md`.
9. Gain par vague de 8 agents + directeur : ≈ 9 × 3 300 = 30 000 tokens de contexte initial en moins, répétés (en lecture de cache) à chaque tour.
10. Décisions : Q1 (gotcha 2), Q2 (validation du déplacement du tableau des modules).

## 1. Diff commenté, section par section

| Section actuelle | Octets | Proposition | Justification |
|---|---:|---|---|
| Identité + Workflow + Gouvernance | 2 150 | Fusionnés, condensés (≈ 1 300) | Même contenu ; la liste des 8 agents est retirée (visible dans `.claude/agents/` et dans l'outil Agent). |
| Discipline de mémoire | 1 720 | Conservée, condensée (≈ 1 100) | Règles intactes. Début de session : lecture de `reports/README.md` + résumé exécutif au lieu du dernier rapport entier. Leçon D3.3 : renvoi à `docs/lessons-learned.md:139` (déjà présente). |
| État des modules (tableau) | 4 000 | 4 lignes + renvois | Le détail (chiffres de tests, couverture, historique design system) est de l'historique, déjà dans `README.md` § Modules et les récaps de phase. C'est la section la plus lourde et la moins utile au quotidien. |
| Stack | 600 | Une ligne compacte (≈ 330) | Contenu identique. |
| ADR (tableau) | 1 840 | Une ligne par ADR regroupée (≈ 420) | Les résumés sont dans chaque ADR ; l'index `docs/adr/` suffit. La règle « pas de contournement sans ADR de révision » reste. |
| Conventions Python / données / Git | 1 220 | Fusionnées (≈ 900) | Toutes les règles gardées, dont codes INSEE en `str`, EPSG, identifiants, pre-commit (ex-gotcha 14). |
| Gotchas 1-13 | 2 360 | → `.claude/rules/` (§ 3) | Chargés seulement quand l'agent lit des fichiers du domaine (UI, ETL, infra). Le gotcha 14 (pre-commit) reste dans Conventions. |
| Sources autorisées + datasets | 1 190 | → `docs/data-sources.md` | Utile au seul `chercheur-donnees`, dont la définition liste déjà les domaines autorisés. |
| Interdits | 505 | Conservés (≈ 450) | Identiques. |
| Pointeurs | 1 140 | Une ligne (≈ 450) | Mêmes fichiers + `reports/README.md`. |

## 2. Texte proposé pour CLAUDE.md

```markdown
# ministere-de-l-info — Contexte projet

<!-- Version allégée (proposition 2026-09-24). Détails déplacés : état des modules → README.md
et reports/README.md ; gotchas par domaine → .claude/rules/ ; sources → docs/data-sources.md.
Ce commentaire HTML n'est pas injecté dans le contexte. -->

## Identité et gouvernance

Mathias (GitHub : crocdeine) développe ministere-de-l-info, outil professionnel de
data-visualisation politique et électorale (projet personnel long terme, exigence qualité élevée).
Il n'est pas développeur professionnel mais maîtrise le pilotage et la rigueur méthodologique
(architecture, sources, traçabilité). Décisions structurantes prises en chat web ; Claude Code
exécute sur le Mac mini M4 (OrbStack) ou en session cloud.

**Gouvernance (depuis le 2026-09-24)** : Claude Code est **directeur de projet**. Mathias fixe
les orientations et tranche les décisions structurantes ; le directeur pilote le reste et délègue
à des agents spécialisés (`.claude/agents/`) lancés en parallèle.
- Les agents qui modifient des fichiers travaillent en worktree isolé et ne poussent jamais ;
  le directeur relit, vérifie, fusionne et pousse.
- Aucun agent ne tranche une décision structurante ou méthodologique (classement politique,
  architecture, périmètre, stack) : il instruit et formule des questions fermées.
- Le directeur engage sans attendre les correctifs de bugs avérés et la maintenance
  (documentation, tests, outillage) sans choix de fond.
- Chaque vague d'agents se termine par un rapport de synthèse dans `reports/`.

Toujours communiquer en français, ton neutre, sans blabla. Usage sobre du contexte : skill
`economie-tokens`.

## Discipline de mémoire

**Début de session** : `git log --oneline -10` ; lire `reports/README.md` puis le résumé
exécutif du dernier rapport ; signaler à Mathias tout écart entre ce fichier et le dépôt.

**Fin de tâche significative** (non optionnel) : proposer la mise à jour de CLAUDE.md ;
rapport `reports/` (résumé exécutif de 10 lignes en tête, ligne ajoutée à l'index) ;
ADR dans `docs/adr/` pour toute décision structurante.

**Points d'arrêt** : « POINT D'ARRÊT », « ATTENDRE VALIDATION », « STOP » ou équivalent →
s'arrêter et attendre Mathias. Un test automatisé (AppTest, pytest) ne remplace pas une
validation manuelle demandée.

**CI après push** : identifier le run du commit poussé (`headSha` = `git rev-parse HEAD`) :
`gh run list --limit 3 --json databaseId,headSha,conclusion,displayTitle` (cloud : outils
GitHub MCP). Ne jamais conclure « CI verte » sur un run antérieur (leçon D3.3,
`docs/lessons-learned.md`).

## État du projet

Modules livrés : Géographie, Élections (pres 2002-2022, legi 2002-2024, muni 2008-2026, HdF),
Économie (HdF), Législatif (national), Design system. Dernière release :
`v0.5-economie-legislatif`. Détail par module : `README.md` (§ Modules) ; historique et
chiffres : `reports/README.md`.

**Dernier rapport** : `reports/session-2026-08-19_design-system-cloture.md`

## Stack (NON NÉGOCIABLE)

Python 3.12 typé · **uv** (jamais pip/poetry/conda) · Streamlit ≥ 1.57 · DuckDB ≥ 1.5 +
spatial · **Polars** (pandas en repli) · PyArrow · GeoPandas + Folium + streamlit-folium ·
Plotly Express (pas matplotlib en web) · Pydantic + pydantic-settings · Tectonic + Jinja2
pour LaTeX (jamais TeX Live).

## Décisions structurantes (ADR)

Ne pas contourner un ADR sans ADR de révision. Index : `docs/adr/`.
0001 DuckDB · 0002 Streamlit · 0003 uv · 0004 Polars · 0005 6 blocs officiels
(EXG/GAU/DIV/CENT/DTE/EXD), classement « de l'époque » · 0006 Économie (sources, schéma) ·
0007 Législatif · 0008 Économie, sources complémentaires · 0009 Design system et navigation.

## Conventions

- Code : `ruff format` / `ruff check` (line-length 100, isort), `pytest`, `logging` (jamais
  `print()` en prod), docstrings courtes en français.
- Codes INSEE communes : **toujours `str` zéro-paddé** (`"01001"`) ; département `str`
  (`"01"`, `"2A"`, `"971"`) ; dates ISO 8601 ; UTF-8 (CSV INSEE en latin-1 + `;` à convertir).
- Géométries : EPSG:4326 pour Folium (`to_crs(epsg=4326)` avant), EPSG:2154 pour les calculs.
- Élections : `{YYYY}_{type}_t{N}` (`2022_pres_t1`) ; blocs = codes officiels (ADR-0005).
- Git : Conventional Commits stricts ; branche par feature ; `git status` avant `git add .` ;
  si pre-commit ruff reformate : `git add` puis **nouveau** commit (pas `--amend`).
- Règles par domaine (chargées à la lecture des fichiers concernés) : `.claude/rules/`.

## Ce qu'il NE FAUT JAMAIS faire

- pip, poetry, conda ; pandas si Polars suffit ; matplotlib en interface web.
- Committer `.env`, secrets, `data/raw/*`, `data/processed/*`, `*.duckdb`, fichiers > 50 Mo.
- Hardcoder une clé API (toujours `pydantic-settings`) ; géométrie en EPSG inconnu.
- `git push --force` sur main ; modifier `data/raw/` à la main.
- Décision structurante sans validation de Mathias (proposer, attendre, exécuter).

## Pointeurs

`docs/architecture.md` (code, navigation, schéma DuckDB, CI) · `docs/schema-elections.md` ·
`docs/data-sources.md` (sources autorisées, datasets, limites) · `docs/deployment.md` ·
`docs/lessons-learned.md` · `docs/guide-utilisateur.md` ·
`docs/sources-officielles/nuances/index.md` (circulaires, décisions CE) ·
`reports/README.md` (index des rapports) · skills `projet-conventions`, `data-viz-politique`.
```

## 3. Fichiers `.claude/rules/` à créer en même temps

Mécanisme (doc officielle, page *memory*, § « Path-specific rules ») : un fichier `.md` de
`.claude/rules/` avec un champ `paths` n'est chargé que lorsque Claude lit un fichier
correspondant ; sans `paths`, il est chargé à chaque session. Ces fichiers ne sont pas créés
maintenant pour éviter un doublon avec le CLAUDE.md actuel.

### `.claude/rules/streamlit-ui.md`

```markdown
---
paths:
  - "app.py"
  - "pages/**/*.py"
  - "src/ministere_de_l_info/pages/**"
  - "src/ministere_de_l_info/viz/**"
  - "src/ministere_de_l_info/_theme.py"
---

# Streamlit / DuckDB (interface)

- Streamlit relance tout le script à chaque clic : tout chargement lourd en `@st.cache_data`.
- Connexion DuckDB : voir question Q1 (texte à fixer par Mathias).
- GeoJSON national trop lourd : géométries pré-simplifiées en base (`geometry_simplified_*`)
  ou `simplify(0.001)`.
- Avant Folium : `to_crs(epsg=4326)`.
- Régions : 22 avant 2016, 13 depuis (loi NOTRe) ; préciser l'année.
```

### `.claude/rules/donnees-etl.md`

```markdown
---
paths:
  - "src/ministere_de_l_info/etl/**"
  - "src/ministere_de_l_info/data_sources/**"
  - "scripts/**/*.py"
  - "tests/**/*.py"
---

# Données et ETL

- CSV INSEE : latin-1 + séparateur `;`, à préciser à l'import.
- Code INSEE ≠ code postal (Paris : commune `75056`, arrondissements `75101`→`75120`).
- Régions : 22 avant 2016, 13 depuis (loi NOTRe) ; préciser l'année.
- Nuances : codes différents par scrutin → harmonisation `(nuance, annee) → bloc`.
- Parquet élections, nommage inversé : `general-results.parquet` = résultats candidats,
  `candidats-results.parquet` = participation. Se fier aux noms de tables DuckDB
  (`docs/data-sources.md`).
- Nuance NULL pour présidentielles 2017/2022 et européennes 2019 → `candidats_presidentielle`
  (jointure sur `nom`, `docs/schema-elections.md`).
- Listes de communes par circonscription trouvées sur le web peu fiables → valider par
  `ST_Within` sur `geographies_circonscriptions`.
- Blocs officiels seulement depuis la circulaire IOMA2322276J (2023) ; avant, reconstruction
  selon la logique officielle datée (ADR-0005).
```

### `.claude/rules/infra-docker.md`

```markdown
---
paths:
  - "Dockerfile"
  - "deploy/**"
  - "docker-compose*.yml"
  - ".github/workflows/**"
  - "scripts/*.sh"
---

# Infra Docker

- Compose dev (`docker-compose.yml`) : bind mount `./data:/app/data:ro`, base locale visible
  immédiatement. Compose prod (`docker-compose.prod.yml`) : volume nommé `duckdb-data`.
- Un volume nommé isole de l'hôte : les scripts ETL lancés sur l'hôte n'y sont pas visibles.
  Préférer les bind mounts en dev.
```

## 4. Prérequis (documentaliste, avant application)

`docs/data-sources.md` cite déjà l'URL des élections agrégées, PISTE et HATVP, mais pas :
API tabulaire data.gouv (`tabular-api.data.gouv.fr`, ≤ 100 Mo), `portail-api.insee.fr`
(Mélodi sans auth, Sirene/Métadonnées OAuth2), `geo.api.gouv.fr`, `data.geopf.fr`,
dumps AN/Sénat, Overpass, et les datasets RNE, bureaux de vote, EPCI + contours (Admin Express
COG), BANATIC. Recopier la section « Sources de données autorisées » de l'actuel CLAUDE.md
dans une section « Sources autorisées » de `docs/data-sources.md`.

## 5. Questions fermées

- **Q1** — Gotcha 2 (« Connexion DuckDB → `@st.cache_resource` ») : le code utilise
  `@st.cache_resource` uniquement dans `pages/1_📍_Géographie.py:83` ; les 5 modules
  `viz/*_queries.py` ouvrent `_open_ro()` dans des fonctions `@st.cache_data` et ferment en
  `finally` (pattern décrit dans le skill `streamlit-duckdb-patterns`). Réécrire la règle
  selon le code (A), la garder telle quelle (B), ou ouvrir un chantier d'alignement du code (C) ?
- **Q2** — Accepter que le tableau « État des modules » quitte CLAUDE.md au profit de
  `README.md` § Modules et de `reports/README.md` (oui / non, garder une version courte) ?
