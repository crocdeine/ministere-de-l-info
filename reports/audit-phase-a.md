# Audit Phase A — État du code avant consolidation

Date : 2026-05-23
Commit ref : d3d6d4b

---

## 1. État git & repo

```
Branche : main (sync avec origin/main)
État    : clean — rien à committer
Remote  : https://github.com/crocdeine/ministere-de-l-info.git
```

15 derniers commits — convention respectée (feat/fix/docs/chore/refactor/test/perf/style) :

```
d3d6d4b docs: session recap — module géographie bouclé
ccb547e Update author name in README.md
8ddb648 feat(ui): demographic evolution comparison between millesimes
910a16d feat(ui): functional millesime selector with year-aware labels and titles
5f0fb58 feat(etl): load populations millesimes 2013 and 2018 for temporal comparisons
ee7921c fix(etl): split codes_siren_des_epci multi-value to keep first SIREN (MGP)
63d5115 docs: session 2026-05-18 recap
c6c3ef3 docs: comprehensive readme and user guide
3fc8389 chore(cleanup): ruff format + gitignore + cleanup report
a28eb8e test(smoke): 62 ETL integrity tests + health report
```

Un commit ("Update author name in README.md") ne respecte pas le format Conventional Commits — message sans scope ni type normalisé. Isolé.

---

## 2. Structure du projet

```
.
├── app.py
├── CLAUDE.md
├── docker-compose.yml
├── Dockerfile
├── docs/
│   └── guide-utilisateur.md
├── notebooks/              (vide)
├── pages/
│   ├── 1_📍_Géographie.py  (332 L — seule page implémentée)
│   ├── 2_🗳️_Élections.py   (17 L — stub)
│   ├── 3_🏛️_Législatif.py  (16 L — stub)
│   └── 4_💶_Économie.py    (16 L — stub)
├── pyproject.toml
├── README.md
├── references/
│   ├── circulaires/
│   └── typographie/
├── reports/
│   ├── output/
│   ├── templates/
│   └── [fichiers de session]
├── scripts/
│   ├── etl_regions.py      (80 L)
│   └── etl_territoires.py  (999 L ⚠️)
├── src/
│   └── ministere_de_l_info/
│       ├── __init__.py     (2 L)
│       ├── data_sources/
│       │   ├── __init__.py
│       │   ├── circonscriptions.py  (171 L)
│       │   ├── geo.py               (330 L)
│       │   └── insee_populations.py (209 L)
│       └── viz/
│           ├── __init__.py
│           └── maps.py              (625 L ⚠️)
└── tests/
    ├── smoke_test_fetch_admin.py   (71 L)
    ├── test_circonscriptions.py    (73 L)
    ├── test_etl_regions.py         (32 L)
    ├── test_etl_smoke.py           (486 L)
    ├── test_etl_territoires.py     (462 L)
    ├── test_insee_populations.py   (104 L)
    ├── test_pages_geographie.py    (195 L)
    └── test_viz_maps.py            (286 L)

Total src : ~710 L  |  Total scripts : ~1080 L  |  Total tests : ~1710 L  |  Grand total : 4 508 L
```

**Violation CLAUDE.md — fichiers > 500 lignes :**
- `scripts/etl_territoires.py` : 999 L (2× la limite)
- `src/ministere_de_l_info/viz/maps.py` : 625 L

---

## 3. Quality checks

### Ruff lint (fichiers projet uniquement)
```
uv run ruff check src/ scripts/ pages/ tests/ app.py
→ All checks passed!
```

Note : `ruff check .` fait remonter 17 erreurs dans `.claude/skills/` (hors projet). À exclure via config.

### Ruff format
```
uv run ruff format --check src/ scripts/ pages/ tests/ app.py
→ 22 files already formatted
```

### Pytest
```
143 tests collectés — 143 passed — 0 failed — 0 skipped
Durée : 7.56s
```

Suites couvertes : ETL territoires, régions, circonsriptions, populations INSEE, vues SQL, maps viz, page géographie.

**Absence de mesure de couverture** — pytest-cov non configuré, aucun `.coverage` généré.

---

## 4. Couverture type hints

| Périmètre | Typé / Total | Couverture |
|---|---|---|
| `src/` | 27 / 27 | **100%** ✅ |
| `scripts/` | 14 / 14 | **100%** ✅ |
| `pages/` | 2 / 2 | **100%** ✅ |

Résultat : couverture complète sur l'ensemble du code de production. Aucune action requise.

---

## 5. Dépendances

### `pyproject.toml` (extrait)
```toml
requires-python = ">=3.12"

dependencies = [
    "anthropic>=0.102.0",      # rapport IA
    "duckdb>=1.5.2",
    "feedparser>=6.0.12",
    "folium>=0.20.0",
    "geopandas>=1.1.3",
    "httpx>=0.28.1",
    "jinja2>=3.1.6",
    "pandas>=3.0.3",
    "plotly>=6.7.0",
    "polars>=1.40.1",
    "pyarrow>=24.0.0",
    "pydantic>=2.13.4",
    "pydantic-settings>=2.14.1",
    "python-dotenv>=1.2.2",
    "requests-cache>=1.3.2",
    "streamlit>=1.57.0",
    "streamlit-folium>=0.27.2",
]

[dependency-groups]
dev = ["pytest>=9.0.3", "ruff>=0.15.13"]
```

**Absences notables en dev :**
- `pytest-cov` — pas de mesure de couverture
- `mypy` — pas de vérification statique des types (optionnel, ruff suffit pour le style)

---

## 6. Configuration ruff

**Aucune section `[tool.ruff]` dans `pyproject.toml`.** Ruff tourne avec ses défauts.

Conséquences actuelles :
- Pas d'exclusion explicite de `.claude/` → les skills contaminent `ruff check .`
- Pas de règles activées au-delà de `E` et `F` (Pyflakes + pycodestyle) par défaut
- Pas de cible Python déclarée (`target-version = "py312"`)
- Pas de `line-length` déclaré (défaut ruff = 88, CLAUDE.md cible 100)

---

## 7. CI/CD

```
.github/workflows/ : inexistant — PAS de CI
.pre-commit-config.yaml : inexistant — PAS de pre-commit
```

Aucune validation automatique à chaque push ou PR. Toute la qualité repose sur la discipline manuelle.

---

## 8. Configuration externalisée

| Fichier | État |
|---|---|
| `.env` | Présent, gitignored ✅ |
| `.env.example` | Présent, documenté ✅ |
| `.env.template` | Absent (non nécessaire) |

**Variables déclarées dans `.env.example` :**
`ANTHROPIC_API_KEY`, `INSEE_CLIENT_KEY`, `INSEE_CLIENT_SECRET`, `PISTE_CLIENT_ID`, `PISTE_CLIENT_SECRET`, `PISTE_ENV`, `BANQUE_DE_FRANCE_API_KEY`, `APP_ENV`, `LOG_LEVEL`

**URLs hardcodées dans le code source :**

| Fichier | URL | Verdict |
|---|---|---|
| `src/.../geo.py:39` | `https://data.geopf.fr/wfs/ows` | Acceptable — constante publique officielle |
| `src/.../circonscriptions.py:27` | `https://www.data.gouv.fr/api/1/datasets` | Acceptable — constante publique officielle |
| `src/.../insee_populations.py:39` | `https://api.insee.fr/melodi/file` | Acceptable — constante publique officielle |

Les 3 URLs sont des API publiques sans auth (ou auth via clé séparée dans `.env`). Aucune clé embarquée. Situation correcte.

---

## 9. Logging

| Périmètre | Situation | Verdict |
|---|---|---|
| `src/data_sources/geo.py` | `getLogger(__name__)` + appels `info/warning` | ✅ |
| `src/data_sources/circonscriptions.py` | `getLogger(__name__)` + appels `info` | ✅ |
| `src/data_sources/insee_populations.py` | `getLogger(__name__)` + appels `info` | ✅ |
| `src/viz/maps.py` | `getLogger(__name__)` + appels `warning` | ✅ |
| `scripts/etl_territoires.py` | `logging.basicConfig(INFO)` au niveau module | ✅ (CLI standalone) |
| `scripts/etl_regions.py` | `logging.basicConfig(INFO)` au niveau module | ✅ (CLI standalone) |
| `src/__init__.py` | `print("Hello from ministere-de-l-info!")` | ⚠️ print() en prod |
| `app.py` | Aucun logging configuré | ⚠️ Streamlit sans log handler |

**Problèmes :**
1. `__init__.py` contient un `print()` — vestige du scaffold uv, jamais nettoyé.
2. L'application Streamlit (`app.py`) ne configure pas le handler logging — les `logger.warning/info` des data_sources seront silencieux en prod Docker sauf si Streamlit les propage (ce qu'il ne fait pas par défaut).

---

## 10. Documentation existante

```
docs/
└── guide-utilisateur.md   (5.2 Ko — pour utilisateur final)

reports/
├── cleanup_report.md      (3.8 Ko)
├── etl_health_report.md   (4.3 Ko)
├── session-2026-05-18_recap.md
└── session-2026-05-21_recap.md

README.md (à la racine)
```

**Absent :**
- Documentation d'architecture (schéma de la base, modèle de données)
- CONTRIBUTING.md
- ADR (Architecture Decision Records)
- Docstring de module sur `src/ministere_de_l_info/`

---

## Synthèse

| Aspect | État actuel | Priorité Phase A |
|---|---|---|
| Type hints | 100% ✅ | — |
| Ruff lint | Pass ✅ | Ajouter config explicite |
| Ruff format | Pass ✅ | Maintenir |
| Tests | 143/143 pass ✅ | — |
| Coverage | Non mesuré ⚠️ | Configurer pytest-cov |
| CI GitHub Actions | Absente 🔴 | Créer |
| Pre-commit | Absent 🟡 | Créer |
| Fichiers > 500 L | 2 violations 🔴 | Décomposer |
| Logging Streamlit | Non configuré ⚠️ | Ajouter handler dans app.py |
| print() en prod | 1 occurrence ⚠️ | Supprimer (__init__.py) |
| Config ruff | Défauts silencieux 🟡 | pyproject.toml [tool.ruff] |
| .env / .env.example | Présent ✅ | — |
| Docker | Multi-stage, healthcheck ✅ | — |
| Docs architecture | Absente 🟡 | Créer schéma DB minimal |

---

## Recommandations d'ordre d'exécution (étapes A2–A6)

### A2 — Fondation qualité (30 min) — PRIORITÉ HAUTE
Configurer `[tool.ruff]` dans `pyproject.toml` :
- `target-version = "py312"`, `line-length = 100`
- `exclude = [".claude"]` (isoler les skills)
- Activer les règles `I` (isort), `UP` (pyupgrade), `B` (bugbear)

Ajouter `pytest-cov` en dev et configurer `[tool.pytest.ini_options]` avec `--cov=src`.

Supprimer le `print()` dans `src/ministere_de_l_info/__init__.py`.

### A3 — CI GitHub Actions (45 min) — PRIORITÉ HAUTE
Workflow `.github/workflows/ci.yml` déclenché sur `push` et `pull_request` :
- Job `lint` : `ruff check` + `ruff format --check`
- Job `test` : `uv run pytest --cov` avec upload du rapport coverage

### A4 — Décomposition des gros fichiers (1–2h) — PRIORITÉ HAUTE
- `scripts/etl_territoires.py` (999 L) → extraire les fonctions de chargement par entité dans des modules dédiés sous `src/ministere_de_l_info/etl/`
- `src/ministere_de_l_info/viz/maps.py` (625 L) → extraire les helpers de style/couleur et les builders de choroplèthe dans des sous-modules

### A5 — Logging centralisé (20 min) — PRIORITÉ MOYENNE
Ajouter dans `app.py` une configuration du logging avec `LOG_LEVEL` depuis l'env :
```python
import logging, os
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(levelname)s %(name)s %(message)s")
```

### A6 — Pre-commit (20 min) — PRIORITÉ BASSE
`.pre-commit-config.yaml` avec hooks ruff (lint + format). Utile localement mais redondant avec la CI — à faire après A3.

### A7 — Documentation architecture (1h) — PRIORITÉ BASSE
Schéma Mermaid du modèle DuckDB dans `docs/architecture.md`. Optionnel si la CI et les tests sont verts.
