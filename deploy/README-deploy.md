# Guide de déploiement — ministere-de-l-info

> Sur le Mac mini de Mathias, l'application tourne désormais **en natif** (uv + LaunchAgent,
> [ADR-0012](../docs/adr/0012-execution-native-mac.md)) : scripts dans `deploy/native/`,
> procédure dans [`docs/deployment.md`](../docs/deployment.md). Ce guide couvre la
> publication des releases (image + base) et l'installation Docker (`install.sh`,
> `update.sh`), conservée en repli et pour la distribution.

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

3. Attacher la DB à la release (si la DB a changé) — toujours via le script :
   ```bash
   ./scripts/publish_db.sh v0.X-description   # crée data/ministere.duckdb.gz + .sha256
   gh release upload v0.X-description --clobber \
     data/ministere.duckdb.gz \
     data/ministere.duckdb.gz.sha256
   ```
   Note : la DB fait ~900 Mo, la compression prend quelques minutes.
   Ne pas générer l'empreinte à la main (voir « Convention d'empreinte » ci-dessous).

   Une release sans DB est possible (changement de code seul) : `install.sh` et
   `update.sh` prennent la release **la plus récente qui contient** `ministere.duckdb.gz`.

## Convention d'empreinte de la base

Une seule convention, appliquée par `scripts/publish_db.sh`, `deploy/install.sh`,
`deploy/update.sh` et `scripts/download_db.sh` :

| Élément | Contenu |
|---|---|
| `ministere.duckdb.gz` | Base compressée (`gzip -n`, archive reproductible) |
| `ministere.duckdb.gz.sha256` | SHA256 **du fichier compressé**, format `<hash>  ministere.duckdb.gz` |

Contrôle manuel dans le dossier de l'archive : `shasum -a 256 -c ministere.duckdb.gz.sha256`.
Le digest affiché par GitHub pour l'asset `.gz` (`sha256:…`) doit être identique.

**Rétrocompatibilité** : les clients lisent uniquement le premier champ du `.sha256`
(le chemin éventuel, ex. `data/ministere.duckdb.gz` dans la release v0.5, est ignoré) et
acceptent aussi une empreinte égale au SHA256 de la base **décompressée** (ancienne variante
documentée ici). Une release publiée par l'une ou l'autre méthode reste donc installable.

**État local** : `install.sh` et `update.sh` écrivent `~/.ministere-info/db-release.state`
(tag, empreinte publiée, SHA256 de l'archive et de la base). `update.sh` compare l'empreinte
publiée de la dernière release à celle de l'état : la base n'est retéléchargée que si elle a
changé, sans recalculer l'empreinte de la base locale. Sans état (installation antérieure à
ce mécanisme), `update.sh` compare au SHA256 de la base locale ; si la release utilise la
convention « archive », un unique retéléchargement a lieu, puis l'état est écrit.

La base téléchargée est vérifiée (intégrité gzip + empreinte) dans un dossier temporaire
de `~/.ministere-info/` avant de remplacer l'ancienne : en cas d'échec, la base en place
et l'état sont conservés.

Tests simulés (sans réseau ni Docker) : `bash deploy/tests/test_db_checksum.sh`.

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
- Compare l'empreinte publiée de la dernière release contenant une DB à l'état local — met à jour seulement si différente (voir « Convention d'empreinte »)
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
├── db-release.state     # Release et empreintes de la DB installée (install.sh / update.sh)
├── start.sh             # Script de démarrage (utilisé par LaunchAgent)
├── launch.log           # Logs de démarrage automatique
├── launch-error.log     # Erreurs de démarrage automatique
└── data/
    └── ministere.duckdb # Base de données (1 Go environ)
```
