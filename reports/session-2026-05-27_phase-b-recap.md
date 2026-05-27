# Récap Phase B — Conteneurisation et déploiement self-hosted

Période : 2026-05-27
Branche : main
Commit final : f051dc3

## Objectif initial

Préparer le projet pour un déploiement self-hosted sur OrbStack (Mac mini) :
- Dockerfile production-grade
- Compose dev et prod séparés
- Test de déploiement réel
- Documentation déploiement complète
- Backup automatique

## 7 étapes complétées

| Étape | Objet | Commit |
|---|---|---|
| B1 | Audit Docker (reports/audit-phase-b.md) | non commité |
| B2+B3 | Fix critique pages/ + améliorations Dockerfile/compose | d7658a2 |
| B4 | docker-compose.prod.yml | dd080ca |
| B5 | Test déploiement OrbStack | (test, validation visuelle) |
| B5-fix | Pre-install spatial extension DuckDB | 89718e6 |
| B6 | docs/deployment.md (443 lignes) | 996801c |
| B7 | Backup automatique (script + plist + doc) | f051dc3 |

## Bugs critiques résolus

1. **pages/ absent du Dockerfile** : sans ce fix, l'app conteneurisée n'affichait que
   la page d'accueil. Les 4 pages multipages étaient invisibles.

2. **Extension spatial DuckDB manquante** : la page Géographie plantait au démarrage
   avec "Extension spatial not found". Cause : extension téléchargée à la demande en
   local mais pas pré-installée dans le container.

3. **uv:latest non pinné** : build non reproductible. Pinné à 0.11.16.

## Architecture finale

```
Hôte (Mac mini + OrbStack)
└── Docker
    ├── Image: ministere-info:latest (1.15 GB)
    │   - python:3.12-slim-bookworm
    │   - User non-root "app"
    │   - Spatial extension pré-installée
    │   - Code: src/, pages/, app.py
    │
    ├── Container: ministere-info
    │   - Port: 8501
    │   - Restart: unless-stopped
    │   - Healthcheck: /_stcore/health
    │   - LOG_FORMAT=json
    │   - Memory limit: 2 GB
    │
    └── Volume: ministere-info_duckdb-data
        └── /app/data/ministere.duckdb (~900 MB)
```

## Fichiers livrés

| Fichier | Rôle |
|---|---|
| `Dockerfile` | Multi-stage, uv 0.11.16, spatial pré-installée, user non-root |
| `docker-compose.yml` | Dev avec hot-reload src/, pages/, app.py |
| `docker-compose.prod.yml` | Production immutable, limite 2 GB, LOG_FORMAT=json |
| `.streamlit/config.toml` | headless=true |
| `scripts/backup_db.sh` | Backup depuis volume Docker, rotation 7 jours |
| `scripts/com.crocdeine.ministere-info.backup.plist` | launchd 3h quotidien |
| `docs/deployment.md` | 443 lignes, 8 cas troubleshooting |

## Tests de validation

| Test | Résultat |
|---|---|
| Build image | OK (3-5 min premier build, 30s ensuite avec cache) |
| Initialisation volume | OK (copie 914 MB) |
| Démarrage container | healthy en < 30s |
| Healthcheck Docker | 5 checks consécutifs, ExitCode 0 |
| Healthcheck HTTP | `/_stcore/health` → ok |
| Persistance | `down` + `up` = DB toujours présente (914 MB) |
| Restart policy | `kill -9 1` → container recréé en < 5s |
| Counts DuckDB | régions=18, communes=34877, populations=104574 |
| Test visuel (B5.7) | Page Géographie + tableau + 6 niveaux OK |
| Backup manuel | 928 MB créé en 30s, log peuplé |
| plist | `plutil -lint` → OK |

## Limitations connues

- **Logs Streamlit natifs** (Uvicorn, URLs) apparaissent en texte brut indépendamment
  de `LOG_FORMAT` — limitation interne de Streamlit, non contournable sans patcher la lib
- **scripts/etl_territoires.py** non inclus dans l'image — l'ETL s'exécute toujours sur
  l'hôte, puis la DB est copiée dans le volume
- **Extension spatial DuckDB** : ajoute ~30s au premier build (téléchargement CDN DuckDB)

## Pour la prochaine session

### Option C — Module Élections (Phase C, ~8-12h)

- Législatives 2017 + 2022 (lien direct avec `geographies_circonscriptions`)
- Multi-agents recommandés pour l'exploration (datasets, schéma, nuances politiques)
- Implémentation séquentielle
- Nouvelle page `2_🗳️_Élections.py`

### Option B8 — DB depuis GitHub Releases (~1-2h)

- Mécanisme de download au premier lancement
- Permet de cloner + déployer sans exécuter l'ETL
- Pratique pour la distribution et le backup externe

## Actions à faire manuellement par Mathias

Activer le backup automatique :

```bash
cp scripts/com.crocdeine.ministere-info.backup.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.crocdeine.ministere-info.backup.plist
launchctl list | grep ministere-info
```

Vérifier le lendemain matin que le backup s'est lancé :

```bash
cat data/backups/backup.log
ls -lh data/backups/
```
