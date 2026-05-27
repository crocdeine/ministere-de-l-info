# Déploiement self-hosted

Ce document décrit comment déployer ministere-de-l-info en mode self-hosted (OrbStack sur
Mac mini, ou tout autre hôte Docker). Pour l'usage en développement local sans Docker,
voir le README.

## Prérequis

### Matériel et système

- Hôte Docker fonctionnel (Docker Desktop, OrbStack, Colima, ou Linux natif)
- RAM : 4 GB minimum (2 GB alloués au container, 1 GB DuckDB, 1 GB système)
- Disque : 3 GB libres (image 1.15 GB + DB 900 MB + marge)
- Architecture : ARM64 (Apple Silicon) ou x86_64 — Dockerfile compatible

### Connexion réseau

- Requise au moment du `docker build` : téléchargement des dépendances Python, GDAL,
  Tectonic, et de l'extension spatial DuckDB
- Au runtime : **aucune connexion requise** une fois l'image construite et le volume initialisé

## Architecture du déploiement

```
┌─────────────────────────────────────────────────┐
│ Mac mini (hôte)                                 │
│                                                 │
│ ┌─────────────────────────────────────────────┐ │
│ │ OrbStack / Docker                           │ │
│ │                                             │ │
│ │ ┌─────────────────────────────────────────┐ │ │
│ │ │ container ministere-info                │ │ │
│ │ │   image: ministere-info:latest          │ │ │
│ │ │   port: 8501                            │ │ │
│ │ │   user: app (non-root)                  │ │ │
│ │ │   spatial extension: pré-installée      │ │ │
│ │ └───────────────────┬─────────────────────┘ │ │
│ │                     │ mount                  │ │
│ │ ┌───────────────────▼─────────────────────┐ │ │
│ │ │ volume: ministere-info_duckdb-data      │ │ │
│ │ │   /app/data/ministere.duckdb (~900 MB)  │ │ │
│ │ └─────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────┘ │
│                     │                           │
│                     ▼ http://localhost:8501     │
└─────────────────────────────────────────────────┘
```

## Premier déploiement

### 1. Build de l'image

```bash
docker build -t ministere-info:latest .
```

Durée : 3–5 min en premier build, ~30 sec ensuite (couches en cache).

### 2. Initialisation du volume avec la DB

#### Option A — DB locale existante (recommandé)

Si `data/ministere.duckdb` existe déjà sur l'hôte (ETL exécuté en local) :

```bash
# Créer le container sans démarrer (génère le volume vide)
docker compose -f docker-compose.prod.yml up --no-start

# Copier la DB locale dans le volume
docker run --rm \
  -v ministere-info_duckdb-data:/data \
  -v $(pwd)/data:/source:ro \
  alpine cp /source/ministere.duckdb /data/

# Vérifier
docker run --rm -v ministere-info_duckdb-data:/data alpine ls -lah /data
```

#### Option B — Générer la DB depuis l'hôte (premier déploiement sur machine vierge)

Si aucune DB locale n'existe, lancer l'ETL en local **avant** de copier dans le volume :

```bash
# Installer les dépendances localement
uv sync

# Lancer l'ETL (connexion internet requise)
uv run python scripts/etl_territoires.py --millesimes 2013 2018 2023 --yes

# Puis suivre Option A pour copier data/ministere.duckdb dans le volume
```

Durée : 20–40 min selon la connexion (téléchargement WFS IGN + INSEE Mélodi).

Note : `scripts/` n'est pas inclus dans l'image Docker (non nécessaire au runtime).
L'ETL s'exécute toujours sur l'hôte, jamais à l'intérieur du container.

### 3. Démarrage

```bash
docker compose -f docker-compose.prod.yml up -d
```

### 4. Vérifier la santé

```bash
# Healthcheck Docker (attendre ~30s pour le start_period)
docker inspect ministere-info --format='{{.State.Health.Status}}'
# → "healthy"

# Healthcheck applicatif
curl http://localhost:8501/_stcore/health
# → "ok"
```

L'application est accessible sur http://localhost:8501.

## Opérations courantes

### Consulter les logs

```bash
# Logs en temps réel
docker compose -f docker-compose.prod.yml logs -f

# Dernières 100 lignes
docker compose -f docker-compose.prod.yml logs --tail 100
```

Les logs Python de l'application (émis via `logging.getLogger(...)`) sont en JSON :

```json
{"ts": "2026-05-27T11:18:35.446Z", "level": "INFO", "logger": "ministere_de_l_info.viz.maps", "message": "..."}
```

Note : les messages de démarrage Streamlit (Uvicorn, URLs) passent par le logger interne
de Streamlit — ils apparaissent en texte brut indépendamment de `LOG_FORMAT`. C'est attendu.

### Arrêt et redémarrage

```bash
# Arrêt propre (préserve le volume)
docker compose -f docker-compose.prod.yml down

# Redémarrage sans rebuild
docker compose -f docker-compose.prod.yml up -d
```

### Mise à jour de l'application

Après un `git pull` qui apporte des modifications de code :

```bash
git pull
docker build -t ministere-info:latest .
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

Le volume DB est préservé pendant la mise à jour.

### Rafraîchissement des données

Pour récupérer les nouveaux millésimes INSEE ou les MAJ IGN :

```bash
# 1. Arrêter le container (DuckDB n'accepte qu'un writer à la fois)
docker compose -f docker-compose.prod.yml down

# 2. Lancer l'ETL sur l'hôte
uv run python scripts/etl_territoires.py --millesimes 2013 2018 2023 --yes --force

# 3. Recalibrer le volume
docker run --rm \
  -v ministere-info_duckdb-data:/data \
  -v $(pwd)/data:/source:ro \
  alpine cp /source/ministere.duckdb /data/

# 4. Redémarrer
docker compose -f docker-compose.prod.yml up -d
```

`--force` force le re-téléchargement même si les fichiers cache existent.

### Backups

#### Backup automatique (recommandé)

Un script `scripts/backup_db.sh` gère les sauvegardes quotidiennes avec rotation 7 jours.

Activer le backup automatique via launchd (macOS) :

```bash
# Copier le plist dans LaunchAgents
cp scripts/com.crocdeine.ministere-info.backup.plist ~/Library/LaunchAgents/

# Activer
launchctl load ~/Library/LaunchAgents/com.crocdeine.ministere-info.backup.plist

# Vérifier qu'il est chargé
launchctl list | grep ministere-info
```

Le backup s'exécute automatiquement chaque jour à 3h00. Logs dans `data/backups/`.

#### Backup manuel

```bash
./scripts/backup_db.sh
```

#### Restauration depuis une sauvegarde

```bash
docker compose -f docker-compose.prod.yml down

docker run --rm \
  -v ministere-info_duckdb-data:/data \
  -v $(pwd)/data/backups:/backup:ro \
  alpine cp /backup/ministere-2026-05-27_0300.duckdb /data/ministere.duckdb

docker compose -f docker-compose.prod.yml up -d
```

Remplacer le nom du fichier par le backup souhaité (voir `ls data/backups/`).

#### Désactiver le backup automatique

```bash
launchctl unload ~/Library/LaunchAgents/com.crocdeine.ministere-info.backup.plist
rm ~/Library/LaunchAgents/com.crocdeine.ministere-info.backup.plist
```

#### Surveiller les backups

```bash
# Voir le log des backups
tail -f data/backups/backup.log

# Lister les backups actuels
ls -lh data/backups/*.duckdb
```

Les fichiers de backup (~900 MB chacun) sont gitignorés — ne pas les versionner.

## Monitoring

### Santé du container

```bash
# Statut + healthcheck
docker compose -f docker-compose.prod.yml ps

# Détails healthcheck (5 derniers checks)
docker inspect ministere-info --format='{{json .State.Health}}' | python3 -m json.tool

# Restart count
docker inspect ministere-info --format='{{.RestartCount}}'
```

### Ressources

```bash
# CPU / RAM en temps réel
docker stats ministere-info --no-stream

# Espace disque des volumes
docker system df -v | grep ministere
```

## Troubleshooting

### Erreur : Extension "spatial" not found

```
_duckdb.IOException: IO Error: Extension "spatial.duckdb_extension" not found
```

Cause : l'image a été construite sans pré-installer l'extension spatial (antérieure au
commit `89718e6`). Vérifier que le Dockerfile contient après `USER app` :

```dockerfile
RUN python -c "import duckdb; con = duckdb.connect(':memory:'); con.execute('INSTALL spatial')"
```

Fix : rebuild complet sans cache.

```bash
docker build --no-cache -t ministere-info:latest .
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

### Le container ne devient pas healthy

Symptôme : `docker inspect` affiche `Status: unhealthy` ou `starting` qui ne passe
jamais en `healthy`.

Diagnostics :

```bash
# Logs complets
docker compose -f docker-compose.prod.yml logs --tail 50

# Healthcheck direct
docker exec ministere-info curl -fsS http://localhost:8501/_stcore/health

# Process Streamlit
docker exec ministere-info ps aux
```

Causes fréquentes :

- Streamlit n'a pas fini son démarrage (peut prendre 15–20 s ; le `start_period: 30s`
  couvre normalement)
- Erreur Python au démarrage : voir les logs
- Port 8501 occupé sur l'hôte : `lsof -i :8501`

### Page Géographie affiche "Aucune donnée"

Symptôme : la carte est en mode contours, le tableau est vide.

Cause : la DB DuckDB est vide ou la table `populations` n'est pas chargée.

Vérification :

```bash
docker exec ministere-info python -c "
import duckdb
con = duckdb.connect('/app/data/ministere.duckdb', read_only=True)
con.execute('LOAD spatial')
for t in ['geographies_regions', 'geographies_communes', 'populations']:
    n = con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
    print(f'{t}: {n}')
"
```

Attendu : `régions=18`, `communes=34877`, `populations≥34858`.

Si les counts sont à 0 : la DB n'est pas chargée. Lancer l'ETL (voir
« Rafraîchissement des données »).

### Le container redémarre en boucle

Symptôme : `docker inspect ministere-info --format='{{.RestartCount}}'` augmente
rapidement.

Cause : erreur Python fatale au démarrage. La restart policy `unless-stopped` relance
automatiquement.

Diagnostic :

```bash
docker compose -f docker-compose.prod.yml logs --tail 50
```

Pour stopper la boucle pendant le debug :

```bash
docker compose -f docker-compose.prod.yml stop
# analyser les logs, corriger
docker compose -f docker-compose.prod.yml up -d
```

### Performance dégradée

Symptôme : l'app rame, les cartes mettent plus de 5 secondes à charger.

Diagnostics :

```bash
# Saturation CPU/RAM
docker stats ministere-info --no-stream

# Limite mémoire configurée
docker inspect ministere-info --format='{{.HostConfig.Memory}}'
```

Pour augmenter la limite mémoire, modifier `deploy.resources.limits.memory` dans
`docker-compose.prod.yml`, puis redéployer.

### `.env` absent au démarrage

Symptôme : `docker compose up` échoue avec `service "ministere" has neither an image
nor a build context`.

Cause : `.env` est référencé par `env_file` dans le compose mais n'existe pas.

Fix :

```bash
cp .env.example .env
# Éditer .env avec les vraies valeurs si nécessaire
docker compose -f docker-compose.prod.yml up -d
```

### Pages Streamlit invisibles (page d'accueil uniquement)

Symptôme : seule la page d'accueil apparaît, les sous-pages Géographie / Élections /
Législatif / Économie sont absentes du menu.

Cause : l'image a été construite sans `COPY pages ./pages` dans le Dockerfile (antérieure
au commit `d7658a2`).

Fix : rebuild avec le Dockerfile à jour.

```bash
docker build -t ministere-info:latest .
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

### DB absente après redémarrage

Symptôme : le container repart mais `ls -lh /app/data/` est vide.

Cause : le volume a été supprimé avec `docker compose down -v` (le flag `-v` supprime
les volumes).

Fix : recréer le volume en suivant la section « Initialisation du volume avec la DB ».
Ne jamais utiliser `docker compose down -v` sur ce projet — toujours `down` seul.

## Rollback

Si une mise à jour casse l'application :

```bash
# Identifier le commit précédent
git log --oneline -10

# Revenir à un commit antérieur
git checkout <hash>
docker build -t ministere-info:latest .
docker compose -f docker-compose.prod.yml up -d --force-recreate
```

Le volume DB est préservé pendant le rollback.

## Annexes

### Variables d'environnement

Voir `.env.example` à la racine du projet. Valeurs importantes en production :

| Variable | Valeur prod | Description |
|----------|-------------|-------------|
| `LOG_LEVEL` | `INFO` | Niveau de log racine |
| `LOG_FORMAT` | `json` | Format des logs (surchargé par le compose prod) |
| `APP_ENV` | `production` | Environnement applicatif |
| `STREAMLIT_SERVER_RUN_ON_SAVE` | `false` | Hot-reload désactivé en prod |

### Volumes Docker

| Volume | Contenu | Persistance |
|--------|---------|-------------|
| `ministere-info_duckdb-data` | DuckDB principale (~900 MB) | Critique — backupez |

### Commandes utiles condensées

```bash
# Démarrer
docker compose -f docker-compose.prod.yml up -d

# Arrêter (sans supprimer le volume)
docker compose -f docker-compose.prod.yml down

# Logs temps réel
docker compose -f docker-compose.prod.yml logs -f

# Shell dans le container
docker exec -it ministere-info bash

# Inspect healthcheck
docker inspect ministere-info --format='{{.State.Health.Status}}'

# Stats CPU/RAM
docker stats ministere-info --no-stream

# Rebuild + redémarrer
docker build -t ministere-info:latest . \
  && docker compose -f docker-compose.prod.yml up -d --force-recreate
```
