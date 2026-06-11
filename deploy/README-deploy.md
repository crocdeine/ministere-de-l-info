# Guide de déploiement — ministere-de-l-info

## Publier une nouvelle version

1. S'assurer que les tests passent :
   ```bash
   uv run pytest -q -m "not slow"
   ```

2. Créer et pousser le tag :
   ```bash
   git tag -a v0.X-description HEAD -m "Description courte"
   git push origin v0.X-description
   ```
   → GitHub Actions build automatiquement l'image Docker multi-arch (arm64 + amd64)
   → L'image est publiée sur `ghcr.io/crocdeine/ministere-de-l-info`

3. Attacher la DB à la release (si la DB a changé) :
   ```bash
   gzip -k data/ministere.duckdb                              # crée data/ministere.duckdb.gz
   shasum -a 256 data/ministere.duckdb > data/ministere.duckdb.gz.sha256
   gh release upload v0.X-description \
     data/ministere.duckdb.gz \
     data/ministere.duckdb.gz.sha256
   ```
   Note : la DB fait ~900 Mo, la compression prend quelques minutes.

4. Vérifier la release :
   ```bash
   gh release view v0.X-description
   ```

## Première installation utilisateur

L'utilisateur exécute dans son Terminal :

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/crocdeine/ministere-de-l-info/main/deploy/install.sh)
```

Ce script :
- Installe Homebrew si absent
- Installe OrbStack (containers Docker, natif Apple Silicon)
- Crée `~/.ministere-info/` avec la configuration
- Télécharge la base de données depuis la dernière release GitHub
- Démarre l'application sur http://localhost:8501
- Configure le démarrage automatique au login macOS (LaunchAgent)

Prérequis utilisateur : macOS 13+, 4 Go libres, connexion internet.

## Mise à jour utilisateur

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/crocdeine/ministere-de-l-info/main/deploy/update.sh)
```

Ce script :
- Télécharge la nouvelle image Docker
- Compare le checksum de la DB locale avec la release — met à jour seulement si différent
- Redémarre l'application

## Commandes de diagnostic

```bash
# Voir les logs de l'application
docker logs ministere-info

# Voir l'état du container
docker ps

# Redémarrer manuellement
cd ~/.ministere-info && docker compose restart

# Arrêter
cd ~/.ministere-info && docker compose stop

# Taille de la DB
ls -lh ~/.ministere-info/data/
```

## Structure ~/.ministere-info/

```
~/.ministere-info/
├── docker-compose.yml   # Config Docker téléchargée depuis le repo
├── .env                 # Port + chemin DB (généré par install.sh)
├── start.sh             # Script de démarrage (utilisé par LaunchAgent)
├── launch.log           # Logs de démarrage automatique
├── launch-error.log     # Erreurs de démarrage automatique
└── data/
    └── ministere.duckdb # Base de données (1 Go environ)
```
