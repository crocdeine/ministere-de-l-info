# Audit Phase B — État du Docker avant consolidation

Date : 2026-05-27
Commit ref : 588e990

---

## 1. Fichiers Docker existants

### Dockerfile (93 lignes)

```
Stage 1 (builder) : python:3.12-slim-bookworm
  - uv installé depuis ghcr.io/astral-sh/uv:latest
  - apt-get : build-essential + libgdal-dev (build uniquement)
  - COPY pyproject.toml uv.lock → uv sync --frozen --no-install-project --no-dev
  - COPY src/ README.md app.py → uv sync --frozen --no-dev

Stage 2 (runtime) : python:3.12-slim-bookworm
  - apt-get : libgdal32 + curl + ca-certificates
  - Tectonic 0.16.9 (binaire statique, multi-arch aarch64/x86_64)
  - useradd app:app (uid/gid 1000)
  - COPY --from=builder --chown=app:app /app /app
  - ENV PATH, PYTHONUNBUFFERED, PYTHONDONTWRITEBYTECODE, STREAMLIT_*
  - Streamlit credentials.toml (skip email prompt)
  - USER app
  - EXPOSE 8501
  - HEALTHCHECK curl /_stcore/health (30s/10s/10s/3)
  - CMD streamlit run app.py
```

### docker-compose.yml (28 lignes)

```
service app :
  build: . / image: ministere-de-l-info:dev
  ports: 8501:8501
  volumes:
    - ./src:/app/src            (bind, hot reload)
    - ./app.py:/app/app.py      (bind, hot reload)
    - ./.streamlit:/app/.streamlit (bind)
    - duckdb-data:/app/data     (named volume)
    - ./references:/app/references:ro (bind, lecture seule)
  env_file: .env
  environment: STREAMLIT_SERVER_RUN_ON_SAVE=true
  restart: unless-stopped

volumes:
  duckdb-data: driver local
```

### .dockerignore (51 lignes)

Exclusions : `.git`, `__pycache__`, `.venv`, `.pytest_cache`, `.ruff_cache`,
`.coverage`, `htmlcov`, `.vscode`, `.DS_Store`, `.env`, `docs`, `notebooks`,
`*.ipynb`, `data/`, `.claude`, `*.aux`, `*.log`, `*.out`.

---

## 2. Analyse Dockerfile

| Aspect | État actuel | Verdict |
|---|---|---|
| Multi-stage | Oui (builder + runtime) | ✅ |
| Base image builder | `python:3.12-slim-bookworm` | ✅ |
| Base image runtime | `python:3.12-slim-bookworm` | ✅ |
| Package manager | uv (COPY depuis image officielle) | ✅ |
| Version uv | `:latest` (non pinie) | ⚠️ voir point 2 |
| Cache layers | `pyproject.toml + uv.lock` copiés avant `src/` | ✅ |
| UV_LINK_MODE | Non défini → warning hardlink au build | ⚠️ voir point 4 |
| User non-root | `app:app` uid/gid 1000 | ✅ |
| Healthcheck | curl `/_stcore/health`, 30s/10s/10s/3 | ✅ |
| Tectonic | 0.16.9, multi-arch (aarch64 + x86_64) | ✅ |
| `pages/` copiés | **Absent** du Dockerfile | ❌ voir point 1 |
| Streamlit headless | `false` dans .streamlit/config.toml | ⚠️ voir point 5 |
| scripts/ dans l'image | Non (non nécessaire au runtime) | ✅ |
| docs/ dans l'image | Non (.dockerignore) | ✅ |

---

## 3. Analyse docker-compose.yml

| Aspect | État actuel | Verdict |
|---|---|---|
| Volumes `data/` | Named volume `duckdb-data` → `/app/data` | ✅ |
| `data/raw/` | Inclus dans `duckdb-data` (volume unique) | ✅ |
| Variables env | `env_file: .env` | ✅ |
| `.env.example` | Présent, documenté, 7 variables | ✅ |
| Restart policy | `unless-stopped` | ✅ |
| Ports | `8501:8501` | ✅ |
| Hot reload src/ | `./src:/app/src` bind mount | ✅ |
| Hot reload pages/ | **Absent** du compose | ❌ voir point 1 |
| LOG_FORMAT | Hérite de `.env` (`text` par défaut) | ⚠️ voir point 6 |
| Profil production | **Absent** (un seul compose, tout en dev mode) | ⚠️ voir point 3 |
| Network | Réseau `default` (pas d'isolation explicite) | ✅ acceptable |

---

## 4. Test de build

Build exécuté localement le 2026-05-27.

```
$ docker build -t ministere-info:test .
→ Build réussi (toutes les étapes vertes)
→ Tectonic 0.16.9 installé et vérifié
→ Streamlit 1.57.0 exécutable
→ Utilisateur : app (non-root confirmé via whoami)
→ Healthcheck : configuré (CMD-SHELL curl, interval 30s, timeout 10s)

$ docker images | grep ministere-info
ministere-info:test   1.15 GB
```

**Répartition des couches (docker history) :**

| Couche | Taille | Origine |
|---|---|---|
| COPY --from=builder /app | 817 MB | venv complet (GeoPandas, Polars, DuckDB spatial, Streamlit…) |
| apt-get libgdal32 + curl | 160 MB | dépendances runtime GDAL |
| Tectonic binary | 25 MB | binaire statique compilé en Rust |
| Base python:3.12-slim | ~130 MB | base Debian slim |

La taille de 1.15 GB est attendue compte tenu de GeoPandas + GDAL + Polars + DuckDB + Tectonic.
Réduction possible uniquement en retirant Tectonic (~25 MB) ou en passant sur une image GDAL dédiée — hors scope Phase B.

---

## 5. Points critiques à régler en Phase B

### Point 1 — CRITIQUE : `pages/` absent du Dockerfile et du compose

Le Dockerfile copie `src/`, `app.py`, `README.md` mais **pas `pages/`**.
Le compose monte `./src` et `./app.py` en hot reload mais **pas `./pages`**.

Conséquence : en conteneur, Streamlit ne trouve que `app.py` (page d'accueil).
Les sous-pages Géographie, Élections, Législatif, Économie sont invisibles.

Correction requise dans le Dockerfile :
```dockerfile
COPY pages ./pages   # à ajouter après COPY app.py ./
```

Correction requise dans le compose (hot reload dev) :
```yaml
- ./pages:/app/pages
```

### Point 2 — MOYEN : version uv non pinie

```dockerfile
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
```

`:latest` signifie qu'un `docker build` sans cache peut récupérer une version différente
d'uv entre deux builds et introduire des comportements non reproductibles.

Correction : remplacer `:latest` par la version courante figée, ex. `:0.7.8`.

### Point 3 — MOYEN : pas de profil production

Le compose actuel est orienté développement (bind mounts `src/` et `app.py` pour le
hot reload). En production sur OrbStack, le code devrait venir de l'image, pas du host.

Il manque soit :
- Un `docker-compose.prod.yml` (override qui retire les bind mounts dev et force `LOG_FORMAT=json`)
- Soit un profile Compose (`--profile dev` / `--profile prod`)

### Point 4 — MINEUR : UV_LINK_MODE absent dans le builder

Le build affiche :
```
warning: Failed to hardlink files; falling back to full copy.
  If this is intentional, set `export UV_LINK_MODE=copy` [...]
```

Correction : ajouter dans le stage builder :
```dockerfile
ENV UV_LINK_MODE=copy
```

### Point 5 — MINEUR : `headless = false` dans `.streamlit/config.toml`

```toml
[server]
headless = false
```

Avec `headless = false`, Streamlit tente d'ouvrir un navigateur depuis le conteneur
(échoue silencieusement, génère un avertissement). En contexte Docker, `headless = true`
est la valeur correcte. Le Dockerfile compense partiellement avec
`STREAMLIT_SERVER_ADDRESS=0.0.0.0` mais la propriété `headless` doit être `true` dans
le config.toml monté en volume.

### Point 6 — INFO : LOG_FORMAT non surchargé dans le compose

Le `.env.example` définit `LOG_FORMAT=text`. Pour les logs Docker (OrbStack, `docker logs`,
agrégateur Loki), le format JSON est préférable et déjà supporté (A5 Phase A).

Le compose pourrait surcharger via `environment:` :
```yaml
environment:
  - LOG_FORMAT=json
```
Cela ne bloque pas le déploiement mais représente une opportunité d'amélioration facile.

---

## 6. Estimation effort Phase B Docker

| Tâche | Durée |
|---|---|
| Fix point 1 : COPY pages/ + volume compose | 10 min |
| Fix point 2 : pin uv version | 5 min |
| Fix point 3 : docker-compose.prod.yml | 20 min |
| Fix point 4 : UV_LINK_MODE | 5 min |
| Fix point 5 : headless = true | 5 min |
| Fix point 6 : LOG_FORMAT=json dans compose | 5 min |
| Test rebuild + docker compose up + smoke test | 30 min |

**Total estimé : ~1h20**
